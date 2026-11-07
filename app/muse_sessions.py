"""Private Muse session assets; no device, H1, SQL, or clinical interpretation.

An immutable request commit is the only formal visibility point. Review bundles
and cancelled candidates are retained; recovery always queries the original ID.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid


COMPONENT = Path(__file__).absolute().parent / "integrations" / "muse-atom-0.1.0"
COMPONENT_SUMS = "306ecf90ce7c553102cf936dcba6d7f3feab008d0f78c4c99b65ff3d7bbd8137"
SCHEMA = "ptds-muse-asset/1"
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_FILES = 13
FILES = frozenset({"manifest.json", "initial.json", "request.json", "events.jsonl",
                   "SHA256SUMS", "eeg.csv", "imu.csv", "optical.csv", "supervisor.json",
                   "worker.stdout.log", "worker.stderr.log", "cancel.request", "brainflow.log"})
REQUIRED = frozenset({"manifest.json", "initial.json", "request.json", "events.jsonl",
                      "SHA256SUMS", "eeg.csv", "imu.csv", "optical.csv", "supervisor.json"})
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
REVIEW_ID = re.compile(r"MR-[a-f0-9]{32}\Z")
ASSET_ID = re.compile(r"MUSE-[a-f0-9]{32}\Z")


class MuseError(Exception):
    def __init__(self, code, detail):
        super().__init__(str(detail))
        self.code, self.detail = code, detail


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out
    def constant(value):
        raise ValueError("nonfinite JSON value")
    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError) as exc:
        raise MuseError("INVALID_JSON", "Strict UTF-8 JSON required") from exc


def _safe_path(path):
    path = Path(path)
    if ".." in path.parts or not path.is_absolute():
        raise MuseError("UNSAFE_PATH", "Absolute paths without traversal required")
    for item in (path, *path.parents):
        if item.is_symlink():
            raise MuseError("UNSAFE_PATH", "Symbolic links are not accepted")
    return path


def _read(path, limit=MAX_FILE):
    _safe_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise MuseError("UNSAFE_PATH", "Cannot safely open asset file") from exc
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise MuseError("UNSAFE_PATH", "Regular, singly-linked files required")
        if info.st_size > limit:
            raise MuseError("UPLOAD_TOO_LARGE", "File exceeds the allowed size")
        data = handle.read(limit + 1)
        if len(data) > limit:
            raise MuseError("UPLOAD_TOO_LARGE", "File exceeds the allowed size")
        return data


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _private_dir(path):
    path = _safe_path(path)
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise MuseError("UNSAFE_PATH", "Muse asset directories must be private (0700)")


def _new_file(path, data):
    _safe_path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _publish(path, value):
    """Caller holds the shared lock. A rename publishes already-fsynced bytes."""
    if path.exists() or path.is_symlink():
        raise MuseError("COMMIT_CONFLICT", "An immutable record already exists")
    pending = path.with_name(".pending-" + uuid.uuid4().hex)
    _new_file(pending, _canonical(value))
    os.rename(pending, path)
    _sync_dir(path.parent)


def _component_check():
    try:
        sums = _read(COMPONENT / "RELEASE_SHA256SUMS")
        if _sha(sums) != COMPONENT_SUMS:
            raise MuseError("COMPONENT_CHANGED", "Pinned component manifest differs")
        expected_files = {"RELEASE_SHA256SUMS"}
        expected_dirs = set()
        for line in sums.decode("ascii").splitlines():
            digest, name = line.split("  ", 1)
            rel = Path(name)
            if rel.is_absolute() or ".." in rel.parts or _sha(_read(COMPONENT / rel)) != digest:
                raise MuseError("COMPONENT_CHANGED", "Pinned component file differs")
            expected_files.add(name)
            expected_dirs.update(str(p) for p in rel.parents if str(p) != ".")
        actual_files, actual_dirs = set(), set()
        for base, directories, names in os.walk(COMPONENT, followlinks=False):
            for name in directories:
                path = _safe_path(Path(base) / name)
                actual_dirs.add(str(path.relative_to(COMPONENT)))
            for name in names:
                path = _safe_path(Path(base) / name)
                actual_files.add(str(path.relative_to(COMPONENT)))
        if actual_files != expected_files or actual_dirs != expected_dirs:
            raise MuseError("COMPONENT_CHANGED", "Unpinned component files, directories, or bytecode caches are forbidden")
    except (OSError, UnicodeError, ValueError) as exc:
        raise MuseError("COMPONENT_UNAVAILABLE", "Pinned Muse component is unavailable") from exc


def _command(command, bundle, *extra):
    if command not in {"verify", "inspect", "replay"}:
        raise MuseError("COMMAND_FORBIDDEN", "Only offline read commands are permitted")
    _component_check()
    argv = [sys.executable, "-X", "utf8", "-E", "-s", "-S", "-B",
            str(COMPONENT / "run.py"), command, str(_safe_path(bundle)), *extra]
    try:
        run = subprocess.run(argv, cwd=COMPONENT,
                             env={"PATH": os.defpath, "LANG": "C", "LC_ALL": "C"},
                             capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MuseError("COMPONENT_FAILED", "Offline component command did not complete") from exc
    if len(run.stdout) > 2 * MAX_TOTAL:
        raise MuseError("COMPONENT_FAILED", "Component response exceeds the allowed size")
    result = _json(run.stdout)
    if not isinstance(result, dict) or result.get("schema_version") != "muse-command-result/1" or result.get("command") != command:
        raise MuseError("COMPONENT_FAILED", "Unexpected component response")
    if run.returncode != 0 or result.get("ok") is not True:
        raise MuseError("BUNDLE_REJECTED", {"command": command, "error": result.get("error"),
                                           "result": result.get("result")})
    if not isinstance(result.get("result"), dict):
        raise MuseError("COMPONENT_FAILED", "Expected an object result from the component")
    return result["result"]


class Store:
    def __init__(self, inst):
        self.inst = inst
        self.root = _safe_path(Path(inst.ctx.root).absolute()) / "startorch" / "muse"
        self.instance_id = inst.ctx.instance_id

    def _policy(self, nature=None):
        spec = self.inst.spec
        if (spec.get("replay", False) if isinstance(spec, dict) else getattr(spec, "replay", False)):
            raise MuseError("READ_ONLY", "Replay instances cannot prepare or save sessions")
        if nature is not None and nature not in self.inst.ctx.accept:
            raise MuseError("NATURE_NOT_ACCEPTED", "This instance does not accept the source data nature")

    @contextmanager
    def _lock(self):
        _safe_path(self.root.parent)
        self.root.parent.mkdir(mode=0o700, exist_ok=True)
        _private_dir(self.root)
        for child in ("reviews", "requests", "terminals"):
            _private_dir(self.root / child)
        _sync_dir(self.root)
        _sync_dir(self.root.parent)
        _sync_dir(self.root.parent.parent)
        lock_path = self.root / "write.lock"
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise MuseError("UNSAFE_PATH", "Invalid store lock")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _inventory(self, bundle):
        _safe_path(bundle)
        names = {item.name for item in bundle.iterdir()}
        if not REQUIRED <= names or names - FILES or len(names) > MAX_FILES:
            raise MuseError("BUNDLE_FILES_INVALID", "Unexpected or missing direct session files")
        inventory, size = {}, 0
        for name in sorted(names):
            data = _read(bundle / name)
            size += len(data)
            if size > MAX_TOTAL:
                raise MuseError("UPLOAD_TOO_LARGE", "Session exceeds 32 MiB")
            inventory[name] = {"bytes": len(data), "sha256": _sha(data)}
        return inventory

    def _verify(self, bundle):
        manifest = _json(_read(bundle / "manifest.json"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != "muse-session/1":
            raise MuseError("SCHEMA_UNSUPPORTED", "Only muse-session/1 is accepted")
        request = manifest.get("request")
        if not isinstance(request, dict) or request.get("schema_version") != "muse-capture-request/1":
            raise MuseError("BUNDLE_REJECTED", "A typed source capture request is required")
        fields = ("session_id", "request_id", "profile", "mode", "data_nature")
        if any(not isinstance(request.get(key), str) for key in fields):
            raise MuseError("BUNDLE_REJECTED", "Invalid source request field types")
        if not re.fullmatch(r"[a-f0-9]{32}", request["session_id"]) or not ID.fullmatch(request["request_id"]) or request["profile"] != "muse-s-athena":
            raise MuseError("SOURCE_ID_INVALID", "The source request must identify one Muse S Athena session")
        if request["mode"] not in {"fixture", "real"} or request["data_nature"] != {"fixture": "SYNTHETIC", "real": "REAL"}[request["mode"]]:
            raise MuseError("NATURE_INVALID", "Source mode and explicit data nature differ")
        if type(request.get("duration_seconds")) is not int or not 30 <= request["duration_seconds"] <= 120:
            raise MuseError("BUNDLE_REJECTED", "Source duration must be an integer from 30 to 120 seconds")
        if not isinstance(manifest.get("runtime"), dict) or not isinstance(manifest.get("streams"), dict):
            raise MuseError("BUNDLE_REJECTED", "Runtime and streams must be objects")
        source_request = _json(_read(bundle / "request.json"))
        if request != source_request:
            raise MuseError("SOURCE_ID_INVALID", "Manifest and source request must identify one session")
        verified = _command("verify", bundle)
        continuous = request.get("operation_context", {}).get("profile") == "ptds-continuous-muse/1"
        inspected = {"status": manifest.get("status")} if continuous else _command("inspect", bundle)
        if verified.get("manifest") != manifest:
            raise MuseError("BUNDLE_REJECTED", "Verified manifest differs from the source snapshot")
        expected_status = "PARTIAL" if continuous else "CAPTURED_PENDING_REVIEW"
        if manifest.get("status") != expected_status or inspected.get("status") != expected_status:
            raise MuseError("SESSION_INCOMPLETE", "Only complete sessions may enter review")
        supervisor = _json(_read(bundle / "supervisor.json"))
        if continuous:
            runtime = manifest["runtime"]
            if (not isinstance(supervisor, dict) or supervisor.get("status") != "CHUNK_SEALED"
                    or supervisor.get("manifest_sha256") != _sha(_read(bundle / "manifest.json"))
                    or runtime.get("segment_sealed") is not True
                    or not re.fullmatch(r"[a-f0-9]{64}", str(runtime.get("authorization_sha256", "")))
                    or runtime.get("authorization_sha256") != request["operation_context"].get("authorization_sha256")
                    or set(manifest["streams"]) != {"eeg", "imu", "optical"}
                    or any(manifest.get("lifecycle", {}).get(k) != "OK" for k in ("prepare", "start"))
                    or not any(s.get("samples", 0) > 0 for s in manifest["streams"].values())):
                raise MuseError("SUPERVISOR_INCOMPLETE", "Continuous segment seal is required")
        elif not isinstance(supervisor, dict) or supervisor.get("status") != "WORKER_EXITED" or type(supervisor.get("exit_code")) is not int or supervisor["exit_code"] != 0 or not isinstance(supervisor.get("ended_at"), str) or not supervisor["ended_at"] or supervisor.get("cleanup_errors") or supervisor.get("interrupted") or supervisor.get("terminate_sent") or supervisor.get("kill_sent"):
            raise MuseError("SUPERVISOR_INCOMPLETE", "A clean final WORKER_EXITED/0 record is required")
        nature = request.get("data_nature")
        if nature not in {"SYNTHETIC", "REAL"}:
            raise MuseError("NATURE_INVALID", "Explicit source data nature is required")
        return manifest, {"capture_status": inspected["status"], "supervisor_status": supervisor["status"],
                          "source_request_id": request["request_id"], "mode": request["mode"],
                          "requested_duration_seconds": request["duration_seconds"],
                          "fixture_only": manifest.get("runtime", {}).get("fixture_only", False),
                          "continuous_segment": continuous,
                          "source_started_at": manifest.get("started_at"), "source_ended_at": manifest.get("ended_at"),
                          "bundle_integrity": "VERIFIED", "device_operations": "NOT_RUN",
                          "professional_or_medical_validation": "NOT_RUN"}

    def _load_review(self, review_id):
        if not isinstance(review_id, str) or not REVIEW_ID.fullmatch(review_id):
            raise MuseError("REVIEW_NOT_FOUND", "Review does not belong to this instance")
        path = self.root / "reviews" / review_id
        try:
            record = _json(_read(path / "review.json"))
        except FileNotFoundError as exc:
            raise MuseError("REVIEW_NOT_FOUND", "Review does not belong to this instance") from exc
        if not isinstance(record, dict) or record.get("instance_id") != self.instance_id or record.get("review_id") != review_id or record.get("schema_version") != SCHEMA:
            raise MuseError("REVIEW_NOT_FOUND", "Review does not belong to this instance")
        sha = record.get("review_sha256")
        body = {key: value for key, value in record.items() if key != "review_sha256"}
        if sha != _sha(_canonical(body)) or self._inventory(path / "bundle") != record.get("files"):
            raise MuseError("REVIEW_CHANGED", "Immutable review bytes have changed")
        return record

    def _commits(self):
        records = []
        for path in sorted((self.root / "requests").iterdir()):
            if path.name.startswith(".pending-"):
                continue
            if not re.fullmatch(r"[a-f0-9]{64}\.json", path.name):
                raise MuseError("STORE_INVALID", "Unexpected commit file")
            record = _json(_read(path))
            if record.get("schema_version") != SCHEMA or record.get("instance_id") != self.instance_id or path.stem != _sha(record["receipt"]["request_id"].encode()):
                raise MuseError("STORE_INVALID", "Commit binding differs")
            records.append(record)
        return records

    def _view(self, record, commits=None):
        commits = self._commits() if commits is None else commits
        own = next((c for c in commits if c["receipt"]["review_id"] == record["review_id"]), None)
        cancelled = self._cancelled(record)
        status = "SAVED" if own else "CANCELLED" if cancelled else "READY"
        result = {key: record[key] for key in ("review_id", "review_sha256", "session_id", "data_nature", "manifest", "summary")}
        result.update(status=status, streams=record["manifest"]["streams"])
        if own:
            result["receipt"] = own["receipt"]
        return result

    def _cancelled(self, record):
        path = self.root / "terminals" / (record["review_id"] + ".json")
        try:
            terminal = _json(_read(path))
        except FileNotFoundError:
            return False
        expected = {"schema_version": SCHEMA, "instance_id": self.instance_id,
                    "review_id": record["review_id"], "review_sha256": record["review_sha256"], "status": "CANCELLED"}
        if not isinstance(terminal, dict) or any(terminal.get(k) != v for k, v in expected.items()):
            raise MuseError("STORE_INVALID", "Cancelled review binding differs")
        return True

    def prepare(self, files):
        self._policy()
        if not isinstance(files, dict) or not REQUIRED <= files.keys() or files.keys() - FILES or len(files) > MAX_FILES:
            raise MuseError("BUNDLE_FILES_INVALID", "Upload only the direct session files")
        if any(not isinstance(name, str) or not isinstance(data, bytes) for name, data in files.items()):
            raise MuseError("BUNDLE_FILES_INVALID", "File names and byte content required")
        if any(len(data) > MAX_FILE for data in files.values()) or sum(map(len, files.values())) > MAX_TOTAL:
            raise MuseError("UPLOAD_TOO_LARGE", "Limit is 16 MiB per file and 32 MiB per session")
        with self._lock():
            review_id = "MR-" + uuid.uuid4().hex
            directory = self.root / "reviews" / review_id
            _private_dir(directory)
            bundle = directory / "bundle"
            _private_dir(bundle)
            for name, data in files.items():
                _new_file(bundle / name, data)
            _sync_dir(bundle)
            inventory = self._inventory(bundle)
            manifest, summary = self._verify(bundle)
            nature = manifest["request"]["data_nature"]
            self._policy(nature)
            record = {"schema_version": SCHEMA, "instance_id": self.instance_id,
                      "component": "muse-atom", "component_version": "0.1.0", "component_sha256": COMPONENT_SUMS,
                      "review_id": review_id, "prepared_at": self.inst.now(), "files": inventory,
                      "bundle_sha256": _sha(_canonical(inventory)), "manifest": manifest, "summary": summary,
                      "session_id": manifest["request"]["session_id"], "data_nature": nature}
            record["review_sha256"] = _sha(_canonical(record))
            _publish(directory / "review.json", record)
            _sync_dir(directory.parent)
            return self._view(record)

    def review(self, review_id):
        with self._lock():
            return self._view(self._load_review(review_id))

    def _request_path(self, request_id):
        if not isinstance(request_id, str) or not ID.fullmatch(request_id):
            raise MuseError("REQUEST_ID_INVALID", "Use 1–80 safe request-ID characters")
        return self.root / "requests" / (_sha(request_id.encode()) + ".json")

    def save(self, review_id, request_id, review_sha256):
        target = self._request_path(request_id)
        with self._lock():
            commits = self._commits()
            prior = next((c for c in commits if c["receipt"]["request_id"] == request_id), None)
            if prior:
                receipt = prior["receipt"]
                if (receipt["review_id"], receipt["review_sha256"]) != (review_id, review_sha256):
                    raise MuseError("REQUEST_CONFLICT", "Request ID is bound to different review content")
                return receipt
            record = self._load_review(review_id)
            if record["review_sha256"] != review_sha256:
                raise MuseError("REVIEW_CHANGED", "Save must bind the reviewed snapshot hash")
            self._policy(record["data_nature"])
            if self._cancelled(record):
                raise MuseError("REVIEW_CANCELLED", "Cancelled review cannot be saved")
            self._verify(self.root / "reviews" / review_id / "bundle")
            previous = next((c for c in commits if c["receipt"]["session_id"] == record["session_id"]), None)
            if previous and previous["bundle_sha256"] != record["bundle_sha256"]:
                raise MuseError("SESSION_CONFLICT", "Source session ID already has different bytes")
            asset_id = previous["receipt"]["asset_id"] if previous else "MUSE-" + uuid.uuid4().hex
            receipt = {"asset_id": asset_id, "request_id": request_id, "review_id": review_id,
                       "review_sha256": review_sha256, "session_id": record["session_id"],
                       "data_nature": record["data_nature"], "saved_at": previous["receipt"]["saved_at"] if previous else self.inst.now(),
                       "outcome": "ALREADY_SAVED" if previous else "SAVED"}
            commit = {"schema_version": SCHEMA, "instance_id": self.instance_id,
                      "receipt": receipt, "bundle_sha256": record["bundle_sha256"],
                      "asset_review_id": previous["asset_review_id"] if previous else review_id}
            _publish(target, commit)
            return receipt

    def cancel(self, review_id):
        self._policy()
        with self._lock():
            record = self._load_review(review_id)
            view = self._view(record)
            if view["status"] == "READY":
                _publish(self.root / "terminals" / (review_id + ".json"),
                         {"schema_version": SCHEMA, "instance_id": self.instance_id,
                          "review_id": review_id, "review_sha256": record["review_sha256"],
                          "status": "CANCELLED", "cancelled_at": self.inst.now()})
                view["status"] = "CANCELLED"
            return view

    def request(self, request_id):
        self._request_path(request_id)
        with self._lock():
            record = next((c for c in self._commits() if c["receipt"]["request_id"] == request_id), None)
            return {"status": "SAVED", "receipt": record["receipt"]} if record else {"status": "UNKNOWN", "request_id": request_id}

    def list(self):
        with self._lock():
            return sorted((c["receipt"] for c in self._commits() if c["receipt"]["outcome"] == "SAVED"),
                          key=lambda receipt: (datetime.fromisoformat(receipt["saved_at"]).timestamp(), receipt["asset_id"]), reverse=True)

    def _asset(self, asset_id):
        if not isinstance(asset_id, str) or not ASSET_ID.fullmatch(asset_id):
            raise MuseError("ASSET_NOT_FOUND", "Session does not belong to this instance")
        commit = next((c for c in self._commits() if c["receipt"]["asset_id"] == asset_id and c["receipt"]["outcome"] == "SAVED"), None)
        if not commit:
            raise MuseError("ASSET_NOT_FOUND", "Session does not belong to this instance")
        record = self._load_review(commit["asset_review_id"])
        if record["bundle_sha256"] != commit["bundle_sha256"] or record["review_sha256"] != commit["receipt"]["review_sha256"]:
            raise MuseError("REVIEW_CHANGED", "Saved session bytes differ from the commit")
        return commit, record

    def detail(self, asset_id):
        with self._lock():
            commit, record = self._asset(asset_id)
            return {"receipt": commit["receipt"], "manifest": record["manifest"],
                    "streams": record["manifest"]["streams"], "summary": record["summary"]}

    def replay(self, asset_id, stream, offset=0, limit=20):
        if stream not in {"eeg", "imu", "optical"} or type(offset) is not int or offset < 0 or type(limit) is not int or not 0 <= limit <= 200:
            raise MuseError("REPLAY_RANGE_INVALID", "Select one stream, offset ≥ 0, and limit 0–200")
        with self._lock():
            _, record = self._asset(asset_id)
            result = _command("replay", self.root / "reviews" / record["review_id"] / "bundle",
                              "--stream", stream, "--offset", str(offset), "--limit", str(limit))
            return dict(result, asset_id=asset_id)

    def status(self):
        try:
            _component_check()
            available, error = True, None
        except MuseError as exc:
            available, error = False, exc.code
        return {"component": "muse-atom", "version": "0.1.0", "available": available,
                "error": error, "schema_version": SCHEMA, "component_sha256": COMPONENT_SUMS,
                "supported_streams": ["eeg", "imu", "optical"], "max_total_bytes": MAX_TOTAL,
                "max_file_bytes": MAX_FILE, "max_files": MAX_FILES, "max_replay_rows": 200,
                "capture_supported": False, "device_operations": "NOT_RUN", "real_capture": "NOT_RUN",
                "clinical_validation": "NOT_RUN"}
