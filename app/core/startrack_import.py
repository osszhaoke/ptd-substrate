"""星轨 side of H1: import commit packages from the exchange dir into startrack.db (reference).

Invariants:
- 星轨 never opens 星炬's database and never writes into the exchange dir (read-only there).
- One package = one 星炬 commit, imported all-or-nothing in one transaction, strictly in
  commit order (commit_id = cursor + 1, seq_from = last seq_to + 1).
- Any problem with a package (file, line, or row) rejects the whole package, writes one
  h1_sync_error row, and STOPS: later commits wait, the cursor does not move. There is no
  row-level quarantine: 星炬 validates with the same pinned contract before saving, so a bad row
  means version skew, a bug, or tampering, and must not be half-accepted.
- Every line's payload digest is recomputed; nothing is skipped on trust.
- A commit may have repair copies (h1-c<id>.r<k>.*). The first copy that validates is used;
  two valid copies with different content is COMMIT_AMBIGUOUS.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from h1_common import (LINE_KEYS, MANIFEST_KEYS, MANIFEST_NAME_RE, MANIFEST_SCHEMA, MAX_INT, PAYLOAD_SCHEMA,
                       SHA256_RE, DictionaryRegistry, H1Error, InstanceContext, canonical_bytes, canonical_json,
                       data_file_name, sha256_hex, strict_loads, validate_payload)
from sqlite_util import append_only_ddl, transaction

H1_DDL = """
CREATE TABLE h1_inbox (
  observation_id  TEXT NOT NULL,
  revision        INTEGER NOT NULL,
  source_seq      INTEGER NOT NULL UNIQUE,
  commit_id       INTEGER NOT NULL,
  status          TEXT NOT NULL,
  code            TEXT NOT NULL,
  payload         TEXT NOT NULL,
  payload_sha256  TEXT NOT NULL,
  imported_at     TEXT NOT NULL,
  PRIMARY KEY (observation_id, revision)
);
CREATE TABLE h1_import_log (
  commit_id       INTEGER PRIMARY KEY,
  manifest_file   TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  seq_from        INTEGER NOT NULL,
  seq_to          INTEGER NOT NULL,
  count           INTEGER NOT NULL,
  inserted        INTEGER NOT NULL,
  imported_at     TEXT NOT NULL,
  CHECK (inserted = count AND count = seq_to - seq_from + 1)
);
CREATE TABLE h1_sync_error (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  manifest_file TEXT NOT NULL,
  code          TEXT NOT NULL,
  detail        TEXT NOT NULL,
  occurred_at   TEXT NOT NULL
);
""" + append_only_ddl(["h1_inbox", "h1_import_log", "h1_sync_error"])


class BatchError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


@dataclass
class ImportSummary:
    commits_imported: int = 0
    inserted: int = 0
    cursor: int = 0
    pending_commits: int = 0
    error: dict | None = None


def import_cursor(conn) -> tuple:
    """(last imported commit_id, its seq_to). Derived from the log, never stored separately."""
    row = conn.execute("SELECT commit_id, seq_to FROM h1_import_log ORDER BY commit_id DESC LIMIT 1").fetchone()
    return (row[0], row[1]) if row else (0, 0)


def list_packages(exchange_dir: Path) -> dict:
    """commit_id -> [(repair, manifest_path)] sorted by repair."""
    if not exchange_dir.is_dir():
        raise BatchError("EXCHANGE_DIR_MISSING", "")
    found = {}
    for path in exchange_dir.iterdir():
        match = MANIFEST_NAME_RE.fullmatch(path.name)
        if match and path.is_file():
            found.setdefault(int(match.group(1)), []).append((int(match.group(2) or 0), path))
    return {commit: sorted(copies) for commit, copies in found.items()}


def _parse_manifest(raw: bytes, commit_id: int, repair: int, ctx: InstanceContext) -> dict:
    try:
        manifest = strict_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise BatchError("MANIFEST_INVALID", "not strict JSON") from None
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise BatchError("MANIFEST_INVALID", "keys")
    if raw != canonical_bytes(manifest) + b"\n":
        raise BatchError("MANIFEST_INVALID", "not canonical")
    if manifest["schema"] != MANIFEST_SCHEMA or manifest["payload_schema"] != PAYLOAD_SCHEMA:
        raise BatchError("SCHEMA_UNSUPPORTED", "manifest or payload schema")
    if manifest["instance_id"] != ctx.instance_id:
        raise BatchError("INSTANCE_MISMATCH", "manifest belongs to another instance")
    ints = [manifest[k] for k in ("commit_id", "seq_from", "seq_to", "count")]
    if any(type(v) is not int or not 1 <= v <= MAX_INT for v in ints) or manifest["commit_id"] != commit_id \
            or manifest["seq_to"] < manifest["seq_from"]:
        raise BatchError("MANIFEST_INVALID", "commit or range fields")
    if manifest["count"] != manifest["seq_to"] - manifest["seq_from"] + 1:
        raise BatchError("COUNT_MISMATCH", "count != seq_to - seq_from + 1")
    if manifest["file"] != data_file_name(commit_id, repair) or not isinstance(manifest["file_sha256"], str) \
            or not SHA256_RE.fullmatch(manifest["file_sha256"]):
        raise BatchError("MANIFEST_INVALID", "file name or digest field")
    return manifest


def _parse_lines(data: bytes, manifest: dict) -> list:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise BatchError("LINE_INVALID", "data file is not UTF-8") from None
    if not text.endswith("\n"):
        raise BatchError("LINE_INVALID", "missing final newline")
    raw_lines = text[:-1].split("\n")
    if len(raw_lines) != manifest["count"]:
        raise BatchError("COUNT_MISMATCH", "line count differs from manifest count")
    lines = []
    for index, raw in enumerate(raw_lines):
        try:
            obj = strict_loads(raw)
            ok = isinstance(obj, dict) and set(obj) == LINE_KEYS and canonical_json(obj) == raw
            canonical_json(obj).encode("utf-8")
        except (ValueError, TypeError, UnicodeError):
            ok = False
        if not ok:
            raise BatchError("LINE_INVALID", f"line {index + 1}")
        if type(obj["seq"]) is not int or obj["seq"] != manifest["seq_from"] + index:
            raise BatchError("SEQ_NOT_CONTIGUOUS", f"line {index + 1}")
        if not isinstance(obj["payload_sha256"], str) or not SHA256_RE.fullmatch(obj["payload_sha256"]):
            raise BatchError("LINE_INVALID", f"line {index + 1}: payload_sha256")
        if sha256_hex(canonical_bytes(obj["payload"])) != obj["payload_sha256"]:
            raise BatchError("ROW_DIGEST_MISMATCH", f"seq {obj['seq']}")
        lines.append(obj)
    return lines


def _check_rows(conn, ctx, registry, lines: list) -> None:
    """Row checks are batch-level. Revisions must continue each observation's accepted chain."""
    next_revision = {}
    for obj in lines:
        payload, seq = obj["payload"], obj["seq"]
        version = payload.get("dictionary_version") if isinstance(payload, dict) else None
        if isinstance(version, str) and version not in registry.versions:
            raise BatchError("DICTIONARY_VERSION_UNKNOWN", f"seq {seq}")
        try:
            validate_payload(payload, registry, ctx)
        except H1Error as exc:
            raise BatchError("ROW_INVALID", f"seq {seq}: {exc.code}") from None
        oid = payload["observation_id"]
        if oid not in next_revision:
            known = conn.execute("SELECT MAX(revision) FROM h1_inbox WHERE observation_id = ?", (oid,)).fetchone()[0]
            next_revision[oid] = (known or 0) + 1
        if payload["revision"] < next_revision[oid]:
            raise BatchError("REVISION_CONFLICT", f"seq {seq}")
        if payload["revision"] > next_revision[oid]:
            raise BatchError("REVISION_GAP", f"seq {seq}")
        next_revision[oid] += 1


def _load_copy(conn, ctx, registry, commit_id: int, repair: int, path: Path, last_seq: int) -> tuple:
    raw = path.read_bytes()
    manifest = _parse_manifest(raw, commit_id, repair, ctx)
    if manifest["seq_from"] != last_seq + 1:
        raise BatchError("SEQ_GAP", f"expected seq {last_seq + 1}, package starts at {manifest['seq_from']}")
    data_path = path.parent / manifest["file"]
    if not data_path.is_file():
        raise BatchError("FILE_MISSING", manifest["file"])
    data = data_path.read_bytes()
    if sha256_hex(data) != manifest["file_sha256"]:
        raise BatchError("FILE_DIGEST_MISMATCH", manifest["file"])
    lines = _parse_lines(data, manifest)
    _check_rows(conn, ctx, registry, lines)
    return manifest, lines, sha256_hex(raw), sha256_hex(data)


def _import_commit(conn, ctx, registry, commit_id: int, copies: list, imported_at: str) -> int:
    with transaction(conn):  # write lock first, then read cursor: two importers cannot interleave
        cursor, last_seq = import_cursor(conn)
        if commit_id != cursor + 1:
            return 0
        valid, errors = [], []
        for repair, path in copies:
            try:
                valid.append((path,) + _load_copy(conn, ctx, registry, commit_id, repair, path, last_seq))
            except BatchError as exc:
                errors.append(exc)
        if not valid:
            raise errors[0]
        if len({v[4] for v in valid}) > 1:
            raise BatchError("COMMIT_AMBIGUOUS", f"commit {commit_id}: valid copies differ")
        path, manifest, lines, manifest_sha, _ = valid[0]
        for obj in lines:
            p = obj["payload"]
            conn.execute(
                "INSERT INTO h1_inbox (observation_id, revision, source_seq, commit_id, status, code, payload, "
                "payload_sha256, imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (p["observation_id"], p["revision"], obj["seq"], commit_id, p["status"], p["code"],
                 canonical_json(p), obj["payload_sha256"], imported_at))
        conn.execute(
            "INSERT INTO h1_import_log (commit_id, manifest_file, manifest_sha256, seq_from, seq_to, count, inserted, "
            "imported_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (commit_id, path.name, manifest_sha, manifest["seq_from"], manifest["seq_to"], manifest["count"],
             len(lines), imported_at))
        return len(lines)


def _log_error(conn, name: str, code: str, detail: str, at: str) -> dict:
    conn.execute("INSERT INTO h1_sync_error (manifest_file, code, detail, occurred_at) VALUES (?, ?, ?, ?)",
                 (name, code, detail, at))
    return {"file": name, "code": code, "detail": detail}


def import_pending(conn, ctx: InstanceContext, registry: DictionaryRegistry, *, imported_at: str) -> ImportSummary:
    summary = ImportSummary()
    try:
        packages = list_packages(ctx.exchange_dir)
    except BatchError as exc:
        summary.error = _log_error(conn, "-", exc.code, exc.detail, imported_at)
        return summary
    while True:
        cursor, _ = import_cursor(conn)
        nxt = cursor + 1
        if nxt not in packages:
            if any(commit > nxt for commit in packages):
                summary.error = _log_error(conn, "-", "COMMIT_GAP", f"commit {nxt} missing", imported_at)
            break
        name = packages[nxt][0][1].name
        try:
            inserted = _import_commit(conn, ctx, registry, nxt, packages[nxt], imported_at)
        except BatchError as exc:
            summary.error = _log_error(conn, name, exc.code, exc.detail, imported_at)
            break
        except Exception as exc:  # noqa: BLE001 - anything unexpected still becomes a visible, stable record
            summary.error = _log_error(conn, name, "INTERNAL_ERROR", type(exc).__name__, imported_at)
            break
        summary.commits_imported += 1
        summary.inserted += inserted
    summary.cursor = import_cursor(conn)[0]
    summary.pending_commits = sum(1 for commit in packages if commit > summary.cursor)
    return summary


def h1_status(conn, ctx: InstanceContext) -> dict:
    """For the 星轨 UI. pending_commits > 0 means: results may not reflect the latest 星炬 saves."""
    cursor, last_seq = import_cursor(conn)
    try:
        pending = sum(1 for commit in list_packages(ctx.exchange_dir) if commit > cursor)
    except BatchError:
        pending = -1  # exchange dir missing: unknown, treated as outdated
    last_error = conn.execute(
        "SELECT manifest_file, code, detail, occurred_at FROM h1_sync_error ORDER BY id DESC LIMIT 1").fetchone()
    last_import = conn.execute("SELECT imported_at FROM h1_import_log ORDER BY commit_id DESC LIMIT 1").fetchone()
    return {"cursor_commit": cursor, "cursor_seq": last_seq,
            "inbox_rows": conn.execute("SELECT count(*) FROM h1_inbox").fetchone()[0],
            "pending_commits": pending, "outdated": pending != 0,
            "last_import_at": last_import[0] if last_import else None,
            "last_error": dict(zip(("file", "code", "detail", "at"), last_error)) if last_error else None}
