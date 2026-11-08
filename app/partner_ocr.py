"""One private OCR review per server. Only a committed save may publish its original."""
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import subprocess
import time

import input_guard
import recognize
from h1_common import H1Error
from sqlite_util import assert_inside
from startorch_outbox import open_startorch

UPLOAD = "/api/torch/recognize"
CONFIRM = "/api/torch/ocr/confirm"
CANCEL = "/api/torch/ocr/cancel"
MAX_BYTES = 64 * 1024**2
REVIEW_SECONDS = 30 * 60
TOKEN = re.compile(r"[a-f0-9]{32}")
FILES = {"intent.json", "record.json", "intent.new"} | {"source" + ext for ext in recognize.ORIGINAL_EXT}


def fail(code):
    raise H1Error(code, "")


def write_private(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_EXCL | os.O_CREAT | os.O_NOFOLLOW, 0o600), "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def acquire(inst, create):
    folder = inst.ctx.root / "startorch" / ".partner-ocr-review"
    assert_inside(inst.ctx.root, folder)
    if create:
        folder.mkdir(mode=0o700, exist_ok=True)
    elif not folder.exists():
        return None
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            fail("OCR_STAGE_UNSAFE")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    return folder, fd


def verified_files(inst, folder):
    files = list(folder.iterdir())
    for path in files:
        assert_inside(inst.ctx.root, path)
        if path.name not in FILES or not path.is_file():
            fail("OCR_STAGE_UNSAFE")
    return files


def committed(inst, request_id):
    with closing(open_startorch(inst.ctx)) as db:
        return db.execute("SELECT 1 FROM save_request WHERE request_id=?", (request_id,)).fetchone() is not None


def _identity(path):
    st = path.stat(follow_symlinks=False)
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _sidecar_evidence(page_record, record, page):
    from evidence_navigation import ocr_page_matches
    return ocr_page_matches(page_record, record, page)


def _page_paths(inst, sha):
    import evidence_navigation
    original = Path("startorch/originals")
    pattern = sha[:16] + ".p*.recognition.json"
    matches = evidence_navigation._metadata_files(inst, original, pattern)
    return [(int(m[1]), inst.ctx.root / rel) for rel in matches
            if (m := re.fullmatch(re.escape(sha[:16]) + r"\.p([1-9][0-9]*)\.recognition\.json", rel.name))]


def _check_pages(inst, sha, record, known=None):
    """Bind the directory membership and identities of graph-visible page records."""
    dest = inst.ctx.root / "startorch" / "originals"
    def directory_stamp():
        try:
            return _identity(dest)
        except FileNotFoundError:
            return None
    stamp = directory_stamp()
    if known is not None and stamp == known["directory"]:
        for name, identity in known["files"].items():
            path = dest / name
            assert_inside(inst.ctx.root, path)
            if _identity(path) != identity:
                fail("OCR_ORIGINAL_CONFLICT")
        return known
    # Re-enumerate only if directory membership changed. The hot save path
    # normally checks file identities without reading any OCR metadata under A.
    paths = _page_paths(inst, sha)
    current = {}
    for page, path in paths:
        assert_inside(inst.ctx.root, path)
        mark = _identity(path)
        current[path.name] = mark
        if known is None:
            import evidence_navigation
            candidate = evidence_navigation._json(inst, path.relative_to(inst.ctx.root))
            if not _sidecar_evidence(candidate, record, page) or _identity(path) != mark:
                fail("OCR_ORIGINAL_CONFLICT")
    if (known is not None and current != known["files"]) or directory_stamp() != stamp:
        fail("OCR_ORIGINAL_CONFLICT")
    return {"directory": stamp, "files": current}


def _published_path(inst, path, sha, is_original):
    if is_original and path.exists() and path.lstat().st_nlink == 2:
        from evidence_navigation import _registered_file
        _registered_file(inst, path.relative_to(inst.ctx.root), {"kind":"OCR", "sha256":sha})
    else:
        assert_inside(inst.ctx.root, path)


def published_state(inst, sha, ext, record, previous=None):
    """Hash existing bytes away from A; check only stable identity at commit."""
    dest = inst.ctx.root / "startorch" / "originals"
    pages = _check_pages(inst, sha, record, previous["pages"] if previous is not None else None)
    result = {"pages": pages if previous is None else previous["pages"]}
    for suffix in (ext, ".recognition.json"):
        path = dest / (sha[:16] + suffix)
        _published_path(inst, path, sha, suffix == ext)
        try:
            st = path.stat(follow_symlinks=False)
        except FileNotFoundError:
            result[suffix] = None
            continue
        mark = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        result[suffix] = mark
        if previous is not None:
            continue
        if suffix == ext:
            with path.open("rb") as fp:
                valid = hashlib.file_digest(fp, "sha256").hexdigest() == sha
        else:
            old_bytes = path.read_bytes()
            result["prior_metadata_sha"] = hashlib.sha256(old_bytes).hexdigest()
            old = json.loads(old_bytes)
            # The graph uses the original OCR lines as well as the parsed
            # values. Only upload time and the selected display filename can
            # differ between two recognitions of the identical original.
            incidental = {"name", "recognized_at"}
            old_evidence = {k: v for k, v in old.items() if k not in incidental}
            new_evidence = {k: v for k, v in record.items() if k not in incidental}
            valid = old_evidence == new_evidence
        if not valid:
            fail("OCR_ORIGINAL_CONFLICT")
    if previous is not None and "prior_metadata_sha" in previous:
        result["prior_metadata_sha"] = previous["prior_metadata_sha"]
    if previous is not None and result != previous:
        fail("OCR_ORIGINAL_CONFLICT")
    return result


def finish(inst, folder, verified=None):
    """On restart publish only when the authoritative SQLite transaction exists."""
    files = verified_files(inst, folder)
    intent = folder / "intent.json"
    if intent in files:
        marker = json.loads(intent.read_bytes())
        if not TOKEN.fullmatch(marker["token"]) or marker["instance"] != inst.ctx.instance_id:
            fail("OCR_STAGE_UNSAFE")
        if committed(inst, "OCR-" + marker["token"]):
            sha, ext = marker["sha"], marker["ext"]
            if not re.fullmatch(r"[a-f0-9]{64}", sha) or ext not in recognize.ORIGINAL_EXT:
                fail("OCR_STAGE_UNSAFE")
            dest = inst.ctx.root / "startorch" / "originals"
            assert_inside(inst.ctx.root, dest)
            dest.mkdir(mode=0o700, exist_ok=True)
            # The intent authenticates the OCR sidecar independently from the image.
            # Validate both destinations before publishing either. A conflicting
            # sidecar with the same image digest must leave the intent intact.
            meta_sha = marker.get("metadata_sha")
            prior_sha = marker.get("prior_metadata_sha")
            if not isinstance(meta_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", meta_sha):
                fail("OCR_STAGE_UNSAFE")
            if prior_sha is not None and (not isinstance(prior_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", prior_sha)):
                fail("OCR_STAGE_UNSAFE")
            moves = []
            for source, suffix, expected in [("source" + ext, ext, sha), ("record.json", ".recognition.json", meta_sha)]:
                final = dest / (sha[:16] + suffix)
                _published_path(inst, final, sha, suffix == ext)
                exists = final.exists()
                if exists and verified is not None and verified.get(suffix) == _identity(final):
                    continue
                # The live holder already checked the staged file; startup has
                # no live holder and independently verifies its bytes.
                if exists or verified is None:
                    actual_path = final if exists else folder / source
                    with actual_path.open("rb") as fp:
                        digest = hashlib.file_digest(fp, "sha256").hexdigest()
                    allowed = {expected, prior_sha} if exists and suffix == ".recognition.json" else {expected}
                    if digest not in allowed:
                        fail("OCR_ORIGINAL_CONFLICT")
                if not exists:
                    moves.append((folder / source, final))
            if verified is not None:
                _check_pages(inst, sha, None, verified["pages"])
            elif _page_paths(inst, sha):
                authority = folder / "record.json"
                if not authority.exists():
                    authority = dest / (sha[:16] + ".recognition.json")
                assert_inside(inst.ctx.root, authority)
                data = authority.read_bytes()
                acceptable = {meta_sha} if authority.parent == folder else {meta_sha, prior_sha}
                if hashlib.sha256(data).hexdigest() not in acceptable:
                    fail("OCR_ORIGINAL_CONFLICT")
                _check_pages(inst, sha, json.loads(data))
            for src, final in moves:
                os.replace(src, final)
                sync_dir(dest)
            # Drop the marker only after both published entries are durable.
    for path in files:
        if path != intent:
            path.unlink(missing_ok=True)
    intent.unlink(missing_ok=True)
    sync_dir(folder)


@dataclass
class Draft:
    inst: object
    token: str
    folder: Path
    fd: int
    working: bool = True
    cancelled: bool = False
    until: float = 0
    metadata_sha: str = ""
    record: dict = field(default_factory=dict)
    confirmed: dict = field(default_factory=dict)
    published: dict = field(default_factory=dict)
    timer: object = None


class Reviews:
    def __init__(self, app):
        self.app = app
        self.lock = threading.RLock()
        self.active = None
        for inst in app.instances.values():
            try:
                lease = acquire(inst, False)
            except BlockingIOError:
                continue  # Another live process still owns this private stage.
            if lease:
                folder, fd = lease
                try:
                    finish(inst, folder)
                finally:
                    os.close(fd)

    def drop(self, draft):
        if draft.timer:
            draft.timer.cancel()
        try:
            finish(draft.inst, draft.folder, draft.published)
        finally:
            os.close(draft.fd)
            self.active = None

    def cancel(self, inst, token):
        with self.lock:
            d = self.active
            if d and d.inst is inst and d.token == token:
                d.cancelled = True
                if d.working:
                    # Vision may still be returning. Remove the private filename now;
                    # this lease cannot be reused until the old worker unwinds.
                    for path in verified_files(inst, d.folder):
                        path.unlink()
                else:
                    self.drop(d)

    def close(self):
        with self.lock:
            if self.active:
                self.cancel(self.active.inst, self.active.token)

    def upload(self, handler, inst, name, token):
        if not isinstance(token, str) or not TOKEN.fullmatch(token):
            fail("OCR_DRAFT_INVALID")
        ext = Path(name).suffix.lower()
        if ext not in recognize.ORIGINAL_EXT:
            fail("OCR_FORMAT_UNSUPPORTED")
        input_guard.require_writable(inst)
        maximum = min(input_guard.limit(self.app.config, "recognize_bytes"), MAX_BYTES)
        input_guard.content_length(handler.headers, maximum)
        media = handler.headers.get_all("Content-Type", [])
        if len(media) != 1 or media[0].strip().lower() != "application/octet-stream":
            raise input_guard.RequestError("OCR_FORMAT_UNSUPPORTED", 415)
        with self.lock:
            if self.active:
                fail("OCR_REVIEW_BUSY")
            try:
                folder, fd = acquire(inst, True)
            except BlockingIOError:
                fail("OCR_REVIEW_BUSY")
            try:
                finish(inst, folder)
                if committed(inst, "OCR-" + token):
                    fail("OCR_DRAFT_INVALID")
            except BaseException:
                os.close(fd)
                raise
            d = self.active = Draft(inst, token, folder, fd)
        try:
            with input_guard.request_body(handler, UPLOAD, self.app.config, maximum=maximum) as size:
                if not size:
                    fail("FILE_EMPTY")
                data = handler.rfile.read()
            sha = hashlib.sha256(data).hexdigest()
            path = folder / ("source" + ext)
            with self.lock:
                if d.cancelled:
                    fail("OCR_DRAFT_EXPIRED")
                write_private(path, data)
            del data
            record = recognize.recognize_file(path, sha, self.app.registry, None)
            record.update(name=Path(name).name, sha256=sha, original=sha[:16] + ext, nature=inst.nature, recognized_at=inst.now())
            d.published = published_state(inst, sha, ext, record)
            with self.lock:
                if d.cancelled:
                    fail("OCR_DRAFT_EXPIRED")
                encoded = json.dumps(record, ensure_ascii=False).encode()
                d.metadata_sha = hashlib.sha256(encoded).hexdigest()
                write_private(folder / "record.json", encoded)
                sync_dir(folder)
                for row in record["rows"]:
                    row["raw_line"] = record["source_lines"][row["line"] - 1]
                d.record = record
                d.working = False
                d.until = time.monotonic() + REVIEW_SECONDS
                d.timer = threading.Timer(REVIEW_SECONDS, self.expire, args=(d,))
                d.timer.daemon = True
                d.timer.start()
            result = {k:v for k,v in record.items() if k not in ("source_lines", "original")}
            result.update(draft=token)
            return result
        except BaseException:
            with self.lock:
                if self.active is d:
                    self.drop(d)
            raise

    def expire(self, draft):
        with self.lock:
            if self.active is draft:
                self.cancel(draft.inst, draft.token)

    def current(self, inst, token):
        d = self.active
        if not d or d.working or d.cancelled or d.inst is not inst or d.token != token:
            fail("OCR_DRAFT_EXPIRED")
        if time.monotonic() >= d.until:
            self.drop(d)
            fail("OCR_DRAFT_EXPIRED")
        return d

    def confirm(self, inst, body):
        with self.lock:
            d = self.current(inst, body.get("draft"))
            ref = body.get("source_ref")
            row = next((r for r in d.record["rows"] if r["ref"] == ref), None)
            if row is None or not row.get("box") or body.get("code") != row["code"]:
                fail("OCR_ROW_INVALID")
            # Release A keeps the original numeral and unit intact. Re-enter any
            # correction via manual entry instead of assigning it a false OCR source.
            if any(body.get(k) != row.get(k) for k in ("value", "unit", "cmp")) or any(k in body and body[k] != row[k] for k in ("page","line","box")):
                fail("OCR_ROW_CHANGED")
            if not row.get("value") or not row.get("unit"):
                fail("OCR_ROW_INVALID")
            d.confirmed[ref] = {k:body.get(k) for k in ("code","value","unit","cmp","source_ref")}
            return {"confirmed": ref}

    @contextmanager
    def saving(self, inst, body):
        rows = body.get("rows", [])
        token = body.get("draft")
        if body.get("method") != "ocr":
            if token or str(body.get("request_id","")).startswith("OCR-") or any(
                isinstance(r,dict) and str(r.get("source_ref","")).startswith("OCR:") for r in rows):
                fail("OCR_ROW_INVALID")
            yield
            return
        with self.lock:
            d = self.current(inst, token)
            if body.get("request_id") != "OCR-"+token or body.get("time_confirmed") is not True or not rows:
                fail("OCR_CONFIRM_REQUIRED")
            source_rows = {row["ref"]: row for row in d.record["rows"]}
            selected_keys = {}
            for r in rows:
                if not isinstance(r,dict) or not isinstance(r.get("source_ref"),str):
                    fail("OCR_CONFIRM_REQUIRED")
                ref = r["source_ref"]
                if ref in selected_keys or ref not in d.confirmed or d.confirmed[ref] != {k:r.get(k) for k in d.confirmed[ref]} or r.get("comparator"):
                    fail("OCR_CONFIRM_REQUIRED")
                source = source_rows[ref]
                if any(k in r and r[k] != source[k] for k in ("page","line","box")):
                    fail("OCR_CONFIRM_REQUIRED")
                # Same metric and date may occur on separate original lines. The
                # key comes from the reviewed source, never from a posted key.
                selected_keys[ref] = f"OCR|{d.record['sha256']}|p{source['page']}l{source['line']}"
            marker = {"token":token,"sha":d.record["sha256"],"ext":Path(d.record["original"]).suffix,"instance":inst.ctx.instance_id}
            marker.update(metadata_sha=d.metadata_sha, prior_metadata_sha=d.published.get("prior_metadata_sha"))
            published_state(inst, marker["sha"], marker["ext"], d.record, d.published)
            write_private(d.folder/"intent.new",json.dumps(marker).encode())
            os.replace(d.folder/"intent.new", d.folder/"intent.json")
            sync_dir(d.folder)
            try:
                yield selected_keys
            finally:
                self.drop(d)


def upload_http(handler, app, query):
    inst = app.inst(query["key"][0])
    token = handler.headers.get("X-PTDS-Draft")
    try:
        result = app.ocr_reviews.upload(handler,inst,query.get("name",[""])[0],token)
        try:
            # The generic response writer swallows disconnects. This response owns
            # an uncommitted draft and must dispose of it if transport fails.
            data = json.dumps(result, ensure_ascii=False).encode()
            handler.connection.settimeout(handler.response_timeout)
            handler.send_response(200)
            handler.send_header("Content-Type","application/json; charset=utf-8")
            handler.send_header("Content-Length",str(len(data)))
            handler.send_header("Cache-Control","no-store")
            handler.end_headers()
            handler.wfile.write(data)
        except (ConnectionError, TimeoutError):
            app.ocr_reviews.cancel(inst,token)
            handler.close_connection = True
    except input_guard.RequestError as exc:
        handler.close_connection = True
        handler._json(exc.status, {"error":exc.code})
    except (H1Error, RuntimeError) as exc:
        handler.close_connection = True
        code = exc.code if isinstance(exc,H1Error) else (str(exc) if str(exc) in {"OCR_FAILED","OCR_ENGINE_UNAVAILABLE","OCR_UNSUPPORTED"} else "OCR_FAILED")
        handler._json(400, {"error":code if re.fullmatch(r"[A-Z_]+",code) else "OCR_FAILED"})
    except (OSError, ValueError, subprocess.SubprocessError):
        handler.close_connection = True
        handler._json(400, {"error":"OCR_FAILED"})


def reviewed_save(save):
    from functools import wraps
    @wraps(save)
    def wrapped(inst, body):
        with inst.app.ocr_reviews.saving(inst, body) as keys:
            return save(inst, body, ocr_keys=keys)
    return wrapped
