"""Shared local-only daily-worker protocol; no provider credentials or raw archives."""
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import sys
import uuid
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))
BASE = "http://127.0.0.1:8780"


class DailyWorkerError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DailyWorkerError("LOCAL_REDIRECT_REFUSED")


def local_call(path, body=None):
    if not path.startswith("/api/") or "\n" in path:
        raise DailyWorkerError("LOCAL_PATH_INVALID")
    headers = {"X-PTDS": "1", "Origin": BASE}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, headers=headers,
                                     method="POST" if body is not None else "GET")
    with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=90) as reply:
        if reply.status != 200:
            raise DailyWorkerError("LOCAL_HTTP_FAILED")
        return json.load(reply)


def get_policy(key):
    value = local_call("/api/device-policy?" + urllib.parse.urlencode({"key": key}))
    if not isinstance(value, dict) or type(value.get("enabled")) is not bool:
        raise DailyWorkerError("DAILY_POLICY_INVALID")
    if value["enabled"]:
        if value.get("mode") != "daily" or value.get("schema") != "ptds-device-day/1":
            raise DailyWorkerError("DAILY_POLICY_UNSUPPORTED")
        date.fromisoformat(value["cutover_day"])
        ZoneInfo(value["timezone"])
    return value


def closed_days(state, policy, now, limit=56):
    """Independent daily checkpoint; never borrow the old raw-history cursor."""
    if now.tzinfo is None:
        raise DailyWorkerError("DAILY_TIMEZONE_REQUIRED")
    today = now.astimezone(ZoneInfo(policy["timezone"])).date()
    if state.get("daily_scanned_on") == today.isoformat():
        return [], True
    first = date.fromisoformat(policy["cutover_day"])
    last = state.get("daily_completed_day")
    if last:
        completed = date.fromisoformat(last)
        if completed >= today:
            raise DailyWorkerError("DAILY_CLOCK_BEFORE_CHECKPOINT")
        first = max(first, completed - timedelta(days=2))
    out = []
    while first < today and len(out) < limit:
        out.append(first.isoformat())
        first += timedelta(days=1)
    return out, first >= today


def _digest(body):
    from device_daily import body_digest
    return body_digest(body)


def _confirm(receipt, body):
    if (not isinstance(receipt, dict) or receipt.get("schema") != "ptds-device-day-receipt/1"
            or receipt.get("ok") is not True
            or receipt.get("instance_key") != body["key"]
            or any(receipt.get(k) != body[k] for k in ("source_kind", "day", "device_key"))
            or receipt.get("content_digest") != _digest(body)):
        raise DailyWorkerError("DAILY_RECEIPT_MISMATCH")
    return receipt


def _pending_path(path):
    path = Path(path)
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise DailyWorkerError("DAILY_UNSAFE_PENDING_PATH")
    return path


def recover_pending(path, *, admit=local_call, key=None, source_kind=None, device_key=None):
    """Recover only the exact compact request, not legacy per-sample requests."""
    path = _pending_path(path)
    if not path.exists():
        return None
    body = json.loads(path.read_text())
    if ((key is not None and body.get("key") != key) or
            (source_kind is not None and body.get("source_kind") != source_kind) or
            (device_key is not None and body.get("device_key") != device_key)):
        raise DailyWorkerError("DAILY_PENDING_TARGET_MISMATCH")
    receipt = _confirm(admit("/api/device/daily/admit", body), body)
    path.unlink()
    return receipt


def submit_day(body, path, *, admit=local_call):
    path = _pending_path(path)
    if path.exists():
        pending = json.loads(path.read_text())
        receipt = recover_pending(path, admit=admit, key=body["key"], source_kind=body["source_kind"], device_key=body["device_key"])
        if _digest(pending) == _digest(body):
            return receipt
    # This is one compact day summary. No high-frequency array is written.
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    if len(encoded) > 64 * 1024:
        raise DailyWorkerError("DAILY_PENDING_TOO_LARGE")
    tmp = path.with_name("." + path.name + "-" + uuid.uuid4().hex + ".tmp")
    _pending_path(tmp)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        tmp.unlink(missing_ok=True)
    return recover_pending(path, admit=admit, key=body["key"], source_kind=body["source_kind"], device_key=body["device_key"])
