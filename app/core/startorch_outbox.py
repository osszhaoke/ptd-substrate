"""星炬 side of H1: formal save + transactional outbox + one export package per commit (reference).

Invariants:
- One reviewed save ("核对 → 保存") = one commit = one export package (jsonl + manifest).
  A commit is never split across packages, so 星轨 can never compute half of a lab report.
- The outbox rows and the commit row are written in the SAME transaction as the formal save.
  append_observations() runs inside the caller's transaction (e.g. the existing
  GovernanceStore.transaction()); save_batch() is a convenience wrapper that opens one.
- Request ledger: same request_id + same content returns the stored result (idempotent);
  same request_id + different content is REQUEST_CONFLICT. Every request is recorded, including
  requests that changed nothing (operation trail separate from data revisions).
- A new revision only when content_digest changes.
- The exporter only ever creates files (link-based, no clobber). If an existing file differs
  (corruption), it writes a repair copy h1-c<id>.r<k>.* instead of overwriting.
- 星炬 never opens 星轨's database.
"""
from __future__ import annotations

try:
    import fcntl  # macOS / Linux
except ImportError:  # Windows（队友测试版）：用 msvcrt 锁文件的第一个字节
    fcntl = None
    import msvcrt
import os
import secrets
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from h1_common import (MAX_INT, DictionaryRegistry, H1Error, InstanceContext, build_payload, canonical_bytes,
                       canonical_json, content_digest, encode_export, make_observation_id, sha256_hex,
                       strict_loads, validate_payload)
from sqlite_util import append_only_ddl, assert_inside, open_main_db, transaction

SCHEMA_ID = "startorch-slice/0.2"
DDL = """
CREATE TABLE formal_observation (
  observation_id TEXT NOT NULL,
  revision       INTEGER NOT NULL CHECK (revision >= 1),
  unique_key     TEXT NOT NULL,
  content_digest TEXT NOT NULL,
  payload        TEXT NOT NULL,
  saved_at       TEXT NOT NULL,
  PRIMARY KEY (observation_id, revision)
);
CREATE TABLE h1_commit (
  commit_id    INTEGER PRIMARY KEY CHECK (commit_id >= 1),
  request_id   TEXT NOT NULL UNIQUE,
  batch_id     TEXT NOT NULL,
  seq_from     INTEGER NOT NULL,
  seq_to       INTEGER NOT NULL,
  count        INTEGER NOT NULL CHECK (count = seq_to - seq_from + 1),
  committed_at TEXT NOT NULL
);
CREATE TABLE h1_outbox (
  seq            INTEGER PRIMARY KEY CHECK (seq >= 1),
  commit_id      INTEGER NOT NULL REFERENCES h1_commit (commit_id),
  observation_id TEXT NOT NULL,
  revision       INTEGER NOT NULL,
  payload        TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  UNIQUE (observation_id, revision)
);
CREATE TABLE save_request (
  request_id     TEXT PRIMARY KEY,
  request_digest TEXT NOT NULL,
  result         TEXT NOT NULL,
  commit_id      INTEGER REFERENCES h1_commit (commit_id),
  saved_at       TEXT NOT NULL
);
CREATE TABLE h1_export_log (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  commit_id       INTEGER NOT NULL REFERENCES h1_commit (commit_id),
  data_file       TEXT NOT NULL,
  file_sha256     TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  outcome         TEXT NOT NULL CHECK (outcome IN ('WRITTEN', 'EXISTS_SAME', 'REPAIRED')),
  exported_at     TEXT NOT NULL
);
""" + append_only_ddl(["formal_observation", "h1_commit", "h1_outbox", "save_request", "h1_export_log"])


@dataclass(frozen=True)
class ObservationInput:
    unique_key: str
    code: str
    value_raw: str
    comparator: str | None
    unit_raw: str | None
    temporal: dict
    source_kind: str
    source_ref: str
    trust_tier: str


@dataclass(frozen=True)
class SaveResult:
    outcome: str          # CREATED | REVISED | UNCHANGED | RETRACTED
    observation_id: str
    revision: int
    seq: int | None       # outbox seq; None when nothing was written


def read_startorch(root):
    """Read an existing main store without granting write authority."""
    path = Path(root) / 'startorch/startorch.db'
    return open_main_db(path, SCHEMA_ID, DDL, root=root, readonly=True)


def open_startorch(ctx: InstanceContext, *, create=False):
    return open_main_db(ctx.startorch_db, SCHEMA_ID, DDL, root=ctx.root, create=create)


def _latest(conn, observation_id: str):
    return conn.execute(
        "SELECT revision, unique_key, content_digest, payload FROM formal_observation "
        "WHERE observation_id = ? ORDER BY revision DESC LIMIT 1", (observation_id,)).fetchone()


def _replay_or_conflict(conn, request_id: str, request_digest: str):
    row = conn.execute("SELECT request_digest, result FROM save_request WHERE request_id = ?",
                       (request_id,)).fetchone()
    if row is None:
        return None
    if row[0] != request_digest:
        raise H1Error("REQUEST_CONFLICT", "same request_id, different content")
    return [SaveResult(*r) for r in strict_loads(row[1])]


def _commit(conn, staged: list, *, batch_id: str, request_id: str, request_digest: str, saved_at: str) -> list:
    """staged: [(SaveResult-without-seq, payload | None, unique_key)]. Caller holds the transaction."""
    new = [(r, p, k) for r, p, k in staged if p is not None]
    commit_id, results = None, []
    if new:
        seq_from = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM h1_outbox").fetchone()[0]
        commit_id = conn.execute("SELECT COALESCE(MAX(commit_id), 0) + 1 FROM h1_commit").fetchone()[0]
        if seq_from + len(new) - 1 > MAX_INT or commit_id > MAX_INT:
            raise H1Error("OUTBOX_FULL", "")
        conn.execute("INSERT INTO h1_commit (commit_id, request_id, batch_id, seq_from, seq_to, count, committed_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (commit_id, request_id, batch_id, seq_from, seq_from + len(new) - 1, len(new), saved_at))
    seq = None if not new else seq_from
    for result, payload, unique_key in staged:
        if payload is None:
            results.append(result)
            continue
        text = canonical_json(payload)
        conn.execute(
            "INSERT INTO formal_observation (observation_id, revision, unique_key, content_digest, payload, saved_at) "
            "VALUES (?, ?, ?, ?, ?, ?)", (payload["observation_id"], payload["revision"], unique_key,
                                          payload["content_digest"], text, saved_at))
        conn.execute(
            "INSERT INTO h1_outbox (seq, commit_id, observation_id, revision, payload, payload_sha256) "
            "VALUES (?, ?, ?, ?, ?, ?)", (seq, commit_id, payload["observation_id"], payload["revision"], text,
                                          sha256_hex(text.encode("utf-8"))))
        results.append(SaveResult(result.outcome, result.observation_id, result.revision, seq))
        seq += 1
    conn.execute("INSERT INTO save_request (request_id, request_digest, result, commit_id, saved_at) "
                 "VALUES (?, ?, ?, ?, ?)", (request_id, request_digest,
                                            canonical_json([list(asdict(r).values()) for r in results]),
                                            commit_id, saved_at))
    return results


def append_observations(conn, ctx: InstanceContext, registry: DictionaryRegistry, items, *, batch_id: str,
                        request_id: str, saved_at: str) -> list:
    """Runs INSIDE the caller's write transaction (BEGIN IMMEDIATE). Never commits by itself."""
    if not conn.in_transaction:
        raise H1Error("TRANSACTION_REQUIRED", "call inside the formal save transaction")
    request_digest = sha256_hex(canonical_bytes({"batch_id": batch_id,
                                                 "items": [asdict(item) for item in items]}))
    replay = _replay_or_conflict(conn, request_id, request_digest)
    if replay is not None:
        return replay
    keys = [item.unique_key for item in items]
    if len(set(keys)) != len(keys):
        raise H1Error("DUPLICATE_KEY_IN_BATCH", "")
    staged = []
    for index, item in enumerate(items):
        try:
            observation_id = make_observation_id(ctx.instance_id, item.unique_key)
            latest = _latest(conn, observation_id)
            if latest is not None and latest[1] != item.unique_key:
                raise H1Error("OBSERVATION_ID_COLLISION", "")
            payload = build_payload(
                registry, ctx, observation_id=observation_id, revision=(latest[0] + 1) if latest else 1,
                status="ACTIVE", code=item.code, value_raw=item.value_raw, comparator=item.comparator,
                unit_raw=item.unit_raw, temporal=item.temporal, source_kind=item.source_kind,
                source_ref=item.source_ref, trust_tier=item.trust_tier, batch_id=batch_id,
                request_id=request_id, saved_at=saved_at)
        except H1Error as exc:
            raise H1Error(exc.code, f"row {index}: {exc.detail}") from None
        if latest is not None and latest[2] == payload["content_digest"]:
            staged.append((SaveResult("UNCHANGED", observation_id, latest[0], None), None, item.unique_key))
        else:
            outcome = "REVISED" if latest else "CREATED"
            staged.append((SaveResult(outcome, observation_id, payload["revision"], None), payload, item.unique_key))
    return _commit(conn, staged, batch_id=batch_id, request_id=request_id, request_digest=request_digest,
                   saved_at=saved_at)


def save_batch(conn, ctx: InstanceContext, registry: DictionaryRegistry, items, *, batch_id: str,
               request_id: str, saved_at: str) -> list:
    """Convenience wrapper: one transaction, one commit. Any invalid row rejects the whole batch."""
    with transaction(conn):
        return append_observations(conn, ctx, registry, items, batch_id=batch_id, request_id=request_id,
                                   saved_at=saved_at)


def retract_observation(conn, ctx: InstanceContext, registry: DictionaryRegistry, observation_id: str,
                        *, batch_id: str, request_id: str, saved_at: str) -> SaveResult:
    """Retraction = a new revision with status RETRACTED (content copied, nothing deleted)."""
    with transaction(conn):
        request_digest = sha256_hex(canonical_bytes({"batch_id": batch_id, "retract": observation_id}))
        replay = _replay_or_conflict(conn, request_id, request_digest)
        if replay is not None:
            return replay[0]
        latest = _latest(conn, observation_id)
        if latest is None:
            raise H1Error("OBSERVATION_NOT_FOUND", "")
        previous = strict_loads(latest[3])
        if previous["status"] == "RETRACTED":
            staged = [(SaveResult("UNCHANGED", observation_id, latest[0], None), None, latest[1])]
        else:
            payload = dict(previous, status="RETRACTED", revision=latest[0] + 1, batch_id=batch_id,
                           request_id=request_id, saved_at=saved_at)
            payload["content_digest"] = content_digest(payload)
            validate_payload(payload, registry, ctx)
            staged = [(SaveResult("RETRACTED", observation_id, payload["revision"], None), payload, latest[1])]
        return _commit(conn, staged, batch_id=batch_id, request_id=request_id, request_digest=request_digest,
                       saved_at=saved_at)[0]


# ----------------------------------------------------------------------------- export

@contextmanager
def _export_lock(exchange_dir: Path):
    """One exporter at a time per instance, even if two 星炬 processes are running."""
    with open(exchange_dir / ".h1-export.lock", "a+b") as handle:
        if fcntl is None:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)  # 拿不到会重试约 10 秒再报错
        else:
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is None:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def write_new(path: Path, data: bytes) -> str:
    """Create-only publish: unique tmp + fsync + hard link (fails if the name exists) + dir fsync.

    Returns WRITTEN, EXISTS_SAME, or CONFLICT. Never replaces an existing file.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    with open(tmp, "xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(tmp, path)
        outcome = "WRITTEN"
    except FileExistsError:
        outcome = "EXISTS_SAME" if path.read_bytes() == data else "CONFLICT"
    finally:
        os.unlink(tmp)  # our own temporary file, never a published one
    if os.name != "nt":  # Windows 不能把目录当文件打开来 fsync；NTFS 的目录项由文件系统日志保证
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    return outcome


def _publish_commit(conn, ctx: InstanceContext, commit_id: int, exported_at: str) -> dict:
    rows = conn.execute("SELECT seq, payload, payload_sha256 FROM h1_outbox WHERE commit_id = ? ORDER BY seq",
                        (commit_id,)).fetchall()
    for repair in range(0, 1000):
        data_name, data, manifest_name, manifest = encode_export(ctx.instance_id, commit_id, rows, repair)
        first = write_new(ctx.exchange_dir / data_name, data)
        if first == "CONFLICT":
            continue  # a damaged or foreign file holds this name: try the next repair name
        second = write_new(ctx.exchange_dir / manifest_name, manifest)
        if second == "CONFLICT":
            continue
        if repair:
            outcome = "REPAIRED"
        else:
            outcome = "EXISTS_SAME" if (first, second) == ("EXISTS_SAME", "EXISTS_SAME") else "WRITTEN"
        if outcome == "EXISTS_SAME":
            # 启动时的复核（产品负责人 2026-10-14）：文件原样在、和上次记下的完全一样，就不再追加一行，交接记录不随重启变多；旧行不动
            last = conn.execute("SELECT data_file, file_sha256, manifest_sha256 FROM h1_export_log WHERE commit_id = ? "
                                "ORDER BY id DESC LIMIT 1", (commit_id,)).fetchone()
            if last == (data_name, sha256_hex(data), sha256_hex(manifest)):
                return {"commit_id": commit_id, "file": data_name, "outcome": outcome}
        conn.execute("INSERT INTO h1_export_log (commit_id, data_file, file_sha256, manifest_sha256, outcome, "
                     "exported_at) VALUES (?, ?, ?, ?, ?, ?)",
                     (commit_id, data_name, sha256_hex(data), sha256_hex(manifest), outcome, exported_at))
        return {"commit_id": commit_id, "file": data_name, "outcome": outcome}
    raise H1Error("EXPORT_CONFLICT", f"commit {commit_id}: no free repair name")


def export_pending(conn, ctx: InstanceContext, *, exported_at: str) -> list:
    """Publishes every commit not yet exported. Call after every save commit and at startup."""
    assert_inside(ctx.root, ctx.exchange_dir)
    with _export_lock(ctx.exchange_dir):
        pending = [r[0] for r in conn.execute(
            "SELECT commit_id FROM h1_commit WHERE commit_id NOT IN (SELECT commit_id FROM h1_export_log) "
            "ORDER BY commit_id")]
        return [_publish_commit(conn, ctx, commit_id, exported_at) for commit_id in pending]


def repair_exports(conn, ctx: InstanceContext, *, exported_at: str) -> list:
    """Re-checks every commit; a commit whose published bytes were damaged gets a repair copy."""
    assert_inside(ctx.root, ctx.exchange_dir)
    with _export_lock(ctx.exchange_dir):
        commits = [r[0] for r in conn.execute("SELECT commit_id FROM h1_commit ORDER BY commit_id")]
        return [_publish_commit(conn, ctx, commit_id, exported_at) for commit_id in commits]


def export_status(conn) -> dict:
    """For the 星炬 UI: how far the commits and the exporter are."""
    commits = conn.execute("SELECT COALESCE(MAX(commit_id), 0) FROM h1_commit").fetchone()[0]
    exported = conn.execute("SELECT COUNT(DISTINCT commit_id) FROM h1_export_log").fetchone()[0]
    return {"commits": commits, "exported": exported, "pending": commits - exported}
