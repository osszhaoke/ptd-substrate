"""Local gene assets. The instance directory lock serializes upload, recovery and erasure."""
import fcntl
import hashlib
import io
import time
import uuid
import gene_profile
from instance_services import GeneReader
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from contextlib import closing, contextmanager

import gene_db
import gene_targets
import input_guard
from h1_common import H1Error
from sqlite_util import assert_inside


@contextmanager
def directory_lock(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def check(root, path):
    assert_inside(root, path)
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise H1Error("PATH_OUTSIDE_INSTANCE", "")
    return path


def replace_contents(root, path, write):
    """A fixed private scratch name permits recovery without sweeping unrelated files."""
    check(root, path)
    scratch = check(root, path.with_name("." + path.name + ".gene-rewrite"))
    scratch.unlink(missing_ok=True)
    with os.fdopen(os.open(scratch, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        write(output)
        output.flush()
        os.fsync(output.fileno())
    os.replace(scratch, path)
    sync_directory(path.parent)


def filter_lines(root, path, transform):
    check(root, path)
    if not path.exists():
        return
    def write(out):
        with path.open("rb") as stream:
            for line in stream:
                result = transform(line)
                if result is not None:
                    out.write(result)
    replace_contents(root, path, write)


def validated_nature(inst, value):
    input_guard.require_writable(inst)
    kind = input_guard.nature(value, default=None)
    if inst.app.inst(inst.spec['key']) is not inst or inst.spec['id'] != inst.ctx.instance_id:
        raise H1Error("INSTANCE_UNKNOWN","")
    if kind not in inst.ctx.accept:
        raise H1Error("NATURE_NOT_ACCEPTED", "")
    return kind


def database_paths(store):
    root = store.inst.ctx.root
    return [check(root, Path(str(store.db_path) + suffix)) for suffix in ("", "-journal", "-wal", "-shm")]


def pending(store):
    return check(store.inst.ctx.root, store.dir / ".erase-pending.json")


def stored_path(store, receipt):
    name = receipt["stored_as"]
    sha = receipt["sha256"]
    if not re.fullmatch("[0-9a-f]{64}", sha) or Path(name).name != name or not name.startswith(sha[:16] + "_"):
        raise H1Error("PATH_OUTSIDE_INSTANCE", "")
    return check(store.inst.ctx.root, store.dir / name)


def receipts(store):
    ledger = check(store.inst.ctx.root, store.ledger)
    if not ledger.exists():
        return []
    with ledger.open("rb") as src:
        return [json.loads(line) for line in src if line.strip()]


def erase_rows(store, sha):
    paths = database_paths(store)
    db = paths[0]
    if not db.exists():
        if any(p.exists() for p in paths[1:]):
            raise H1Error("GENE_STORE_INCOMPLETE", "")
        return
    root = store.inst.ctx.root
    with closing(sqlite3.connect(db.as_uri() + "?mode=rw", uri=True)) as conn:
        # This dedicated derivative uses SQLite's rollback journal. Do not unlink a live WAL.
        if conn.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
            raise H1Error("GENE_STORE_INCOMPLETE", "")
        conn.execute("PRAGMA secure_delete=ON")
        # Historical sharing logs keep requested/matched locus IDs, not source file IDs.
        # Keep a locus still supported by another file; drop only target-exclusive details.
        def prune(line):
            record = json.loads(line)
            def keep(locus):
                sql = ("SELECT DISTINCT f.file_sha FROM genotype g JOIN gene_file f USING(file_id) "
                       "WHERE g.rsid=? COLLATE NOCASE")
                sources = {row[0] for row in conn.execute(sql, (locus,))}
                return sources != {sha}
            changed = False
            for key in ("rsids","found"):
                if isinstance(record.get(key), list):
                    remaining = [locus for locus in record[key] if keep(locus)]
                    if remaining != record[key]:
                        record[key] = remaining
                        changed = True
            if not changed:
                return line
            return (json.dumps(record,ensure_ascii=False)+"\n").encode() if record.get("found") or record.get("rsids") else None
        filter_lines(root, root / "cluster/gene_reads.jsonl", prune)
        with conn:
            conn.execute("DELETE FROM genotype WHERE file_id IN (SELECT file_id FROM gene_file WHERE file_sha=?)", (sha,))
            conn.execute("DELETE FROM gene_file WHERE file_sha=?", (sha,))
        empty = not conn.execute("SELECT 1 FROM gene_file LIMIT 1").fetchone()
    if empty:
        if any(p.exists() for p in paths[1:]):
            raise H1Error("GENE_STORE_INCOMPLETE", "")
        db.unlink()
        sync_directory(store.dir)


def verified_originals(store, sha):
    if not isinstance(sha,str) or not re.fullmatch("[0-9a-f]{64}", sha):
        raise H1Error("GENE_FILE_INVALID", "")
    root = store.inst.ctx.root
    rows = receipts(store)
    owned = [stored_path(store, r) for r in rows if r["sha256"] == sha]
    if any(stored_path(store, r) in owned for r in rows if r["sha256"] != sha):
        raise H1Error("GENE_FILE_CONFLICT", "")
    if any(r["sha256"] != sha and r["sha256"].startswith(sha[:16]) for r in rows):
        raise H1Error("GENE_FILE_CONFLICT", "")
    # Include complete, unreceipted originals left by interruption after promotion.
    for entry in store.dir.glob(sha[:16] + "_*"):
        if entry in owned or entry.name.endswith(".profile.json"):
            continue
        check(root, entry)
        with entry.open("rb") as data:
            if hashlib.file_digest(data,"sha256").hexdigest() == sha:
                owned.append(entry)
    for original in set(owned):
        if original.exists():
            with original.open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest() != sha:
                    raise H1Error("GENE_FILE_CONFLICT", "")
        check(root, original.with_name(original.name + ".profile.json"))
    return owned


def finish_erase(store, sha):
    root = store.inst.ctx.root
    owned = verified_originals(store, sha)
    erase_rows(store, sha)
    for original in set(owned):
        original.unlink(missing_ok=True)
        original.with_name(original.name + ".profile.json").unlink(missing_ok=True)
    def remove_json(field):
        return lambda line: None if json.loads(line).get(field) == sha else line
    filter_lines(root, store.dir / "coverage_runs.jsonl", remove_json("file_sha"))
    # The old application log recorded only a short digest. Ambiguous legacy rows stay
    # intact until the owner can establish provenance, rather than editing another file.
    app = store.inst.app
    identity = store.inst.ctx.instance_id.encode()
    with directory_lock(app.root):
        def remove_log(line):
            fields = line.rstrip(b"\n").split(b"\t")
            return None if fields[1:4] == [b"gene_stored",identity,sha[:16].encode()] else line
        filter_lines(app.root, app.logfile, remove_log)
    filter_lines(root, store.ledger, remove_json("sha256"))
    sync_directory(store.dir)
    pending(store).unlink()
    sync_directory(store.dir)


@contextmanager
def session(store):
    root = store.inst.ctx.root
    with directory_lock(root):
        marker = pending(store)
        if marker.exists():
            finish_erase(store, json.loads(marker.read_bytes())["sha256"])
        yield


def erase(store, sha):
    input_guard.require_writable(store.inst)
    if not isinstance(sha,str) or not re.fullmatch("[0-9a-f]{64}", sha):
        raise H1Error("GENE_FILE_INVALID","")
    with session(store):
        rows = receipts(store)
        if not any(r["sha256"] == sha for r in rows):
            return {"removed": False}
        if any(r["sha256"] != sha and r["sha256"].startswith(sha[:16]) for r in rows):
            raise H1Error("GENE_FILE_CONFLICT", "")
        verified_originals(store, sha)
        database_paths(store)
        replace_contents(store.inst.ctx.root, pending(store), lambda fh: fh.write(json.dumps({"sha256":sha}).encode()))
        finish_erase(store, sha)
        return {"removed": True}


def read(store, path, query):
    with session(store):
        database_paths(store)
        if path == "/api/gene":
            return store.list()
        if path == "/api/gene/db":
            stats = gene_db.stats(store.db_path)
            if hasattr(store.inst.app, "trial"):
                stats.pop("path", None)
            return stats
        if path == "/api/gene/coverage":
            profiles = {r["sha256"]: r.get("profile") or {} for r in store.list()}
            result = gene_targets.assess(store.db_path, profiles)
            result["runs"] = gene_targets.record_runs(check(store.inst.ctx.root, store.dir / "coverage_runs.jsonl"), result, store.inst.now())
            if hasattr(store.inst.app, "trial"):
                # The personal registry also carries research references and effect annotations.
                # The partner wire is a positive projection of file coverage only.
                return {"files": [{"file_name": f["file_name"], "rows_total": f["rows_total"],
                                   "valid_genotypes": f["valid_genotypes"],
                                   "matrix": [{k: row.get(k) for k in ("rsid","chromosome","position","direct_observation_status")}
                                              for row in f["matrix"]]} for f in result["files"]]}
            return result
        term = query.get("q","").strip()
        match = re.fullmatch(r"(?:chr)?([0-9]{1,2}|[XYxy]|MT|mt|M)\s*[:：]\s*(\d+)", term)
        if match:
            rows = gene_db.lookup(store.db_path, chrom=match[1], pos=int(match[2]))
        elif re.fullmatch(r"(?i)(rs|i)\d+", term):
            rows = gene_db.lookup(store.db_path, rsid=term)
        else:
            raise H1Error("QUERY_FORMAT","rs 号（如 rs4988235）或 染色体:位置（如 2:136608646）")
        return {"q":term,"rows":rows}


class GeneStore(GeneReader):
    """基因纳管写入器：原样存进实例目录，记 SHA-256、大小、时间、来源和文件的资产属性（格式、行数、位点数……），
    给回执。边收边写边算指纹，大文件不整份进内存。不解读、不使用、不进星轨。"""

    def list(self):
        database_paths(self)
        for receipt in receipts(self):
            path = stored_path(self, receipt)
            check(self.inst.ctx.root, path.with_name(path.name + ".profile.json"))
        return super().list()

    def write(self, name: str, data: bytes, nature=None) -> dict:
        import io
        return self.write_stream(name, io.BytesIO(data), len(data), nature)

    def write_stream(self, name: str, stream, length: int, nature=None) -> dict:
        input_guard.require_writable(self.inst)
        if length > input_guard.limit(self.inst.app.config, "gene_bytes"):
            raise H1Error("FILE_TOO_LARGE", "")
        if length <= 0:
            raise H1Error("FILE_EMPTY", "")
        nature = validated_nature(self.inst, nature)
        with session(self):
            database_paths(self)
            check(self.inst.ctx.root, self.ledger)
            return self._store(name, stream, length, nature)

    def _store(self, name, stream, length, nature):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / f".incoming-{uuid.uuid4().hex}"
        digest, got = hashlib.sha256(), 0
        try:
            with open(tmp, "xb") as handle:
                while got < length:
                    chunk = stream.read(min(1 << 20, length - got))
                    if not chunk:
                        break
                    digest.update(chunk)
                    handle.write(chunk)
                    got += len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if got != length:
                raise H1Error("UPLOAD_INCOMPLETE", f"{got}/{length}")
            sha = digest.hexdigest()
            safe = "".join(c for c in Path(name).name if c.isalnum() or c in "._-")[:80] or "file"
            target = self.dir / f"{sha[:16]}_{safe}"
            check(self.inst.ctx.root, target)
            duplicate = target.exists()
            if duplicate:
                with target.open("rb") as existing:
                    if hashlib.file_digest(existing, "sha256").hexdigest() != sha:
                        raise H1Error("GENE_FILE_CONFLICT", "")
            if duplicate:
                tmp.unlink()
            else:
                os.link(tmp, target)  # 只新建不覆盖
                tmp.unlink()
        except BaseException:
            if tmp.exists():
                tmp.unlink()
            raise
        try:
            prof = gene_profile.profile(target)
        except Exception as exc:  # noqa: BLE001 — 认不出也照样纳管，如实写"未能读取属性"
            prof = {"version": gene_profile.VERSION, "format": "未能读取属性", "format_code": "PROFILE_FAILED",
                    "error": type(exc).__name__}
        receipt = {"receipt_id": "G-" + uuid.uuid4().hex[:12], "file_name": name, "stored_as": target.name,
                   "sha256": sha, "nature": nature, "bytes": got, "received_at": self.inst.now(),
                   "outcome": "DUPLICATE" if duplicate else "STORED", "profile": prof}
        receipt["db"] = self.load(receipt)
        with open(self.ledger, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.inst.app.log("gene_store_complete", self.inst.ctx.instance_id)
        sync_directory(self.dir)
        return receipt


    def load(self, receipt: dict) -> dict:
        """写进统一的位点库（同一指纹只写一次）；失败不影响纳管本身，如实记在回执里。"""
        try:
            database_paths(self)
            path = stored_path(self, receipt)
            return gene_db.load(self.db_path, path, receipt, self.inst.now())
        except Exception as exc:  # noqa: BLE001
            return {"status": "LOAD_FAILED", "rows": 0, "why": type(exc).__name__}

    def catch_up(self) -> int:
        """补齐旧回执：没记属性的补算属性（另存一份 .profile.json，回执原文不改），没进位点库的补写进去。
        上传到一半进程被结束留下的临时文件（没有回执，一小时以上没动）删掉。"""
        done, seen = 0, set()
        for tmp in self.dir.glob(".incoming-*") if self.dir.exists() else []:
            if time.time() - tmp.stat().st_mtime > 3600:
                tmp.unlink()
        for rec in self.list():
            if rec["sha256"] in seen or not (self.dir / rec["stored_as"]).exists():
                continue
            seen.add(rec["sha256"])
            if not rec.get("profile"):
                rec["profile"] = gene_profile.profile(self.dir / rec["stored_as"])
                (self.dir / (rec["stored_as"] + ".profile.json")).write_text(
                    json.dumps(rec["profile"], ensure_ascii=False), "utf-8")
                done += 1
            if self.load(rec)["status"] == "LOADED":
                done += 1
        return done
