"""Small admission boundaries shared by the existing local product adapters.

No storage or public wire changes. Limits are deployment settings, not medical rules.
"""
from __future__ import annotations

import json
import math
import re
import socket
import time
from contextlib import contextmanager

from h1_common import H1Error

MISSING = object()
DEFAULT_LIMITS = {
    "json_bytes": 8 * 1024**2,
    "table_bytes": 64 * 1024**2,
    "recognize_bytes": 64 * 1024**2,
    "gene_bytes": 512 * 1024**2,
    "batch_bytes": 4 * 1024**3,
    "idle_seconds": 10,
    "json_seconds": 30,
    "upload_seconds": 300,
}


class RequestError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


def limit(config, name):
    value = (config.get("request_limits") or {}).get(name, DEFAULT_LIMITS[name])
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise H1Error("REQUEST_LIMIT_INVALID", name)
    if name.endswith("bytes") and int(value) != value:
        raise H1Error("REQUEST_LIMIT_INVALID", name)
    return value


def nature(value=MISSING, *, default):
    value = default if value is MISSING else value
    if not isinstance(value, str) or value not in ("SYNTHETIC", "REAL"):
        raise H1Error("NATURE_INVALID", "数据性质必须为 SYNTHETIC 或 REAL")
    return value


def require_writable(inst):
    if getattr(inst, "spec", {}).get("replay"):
        raise H1Error("REPLAY_INSTANCE", "回放实例不接收新的数据或原件")


def json_object(raw):
    try:
        value = json.loads(raw or b"{}", parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise RequestError("BODY_INVALID") from None
    if not isinstance(value, dict):
        raise RequestError("BODY_INVALID")
    return value


def content_length(headers, maximum):
    if headers.get_all("Transfer-Encoding"):
        raise RequestError("TRANSFER_ENCODING_UNSUPPORTED")
    values = headers.get_all("Content-Length", [])
    if len(values) > 1 or (values and not re.fullmatch(r"[0-9]{1,20}", values[0])):
        raise RequestError("BODY_LENGTH_INVALID")
    size = int(values[0]) if values else 0
    if size > maximum:
        raise RequestError("BODY_TOO_LARGE", 413)
    return size


class DeadlineReader:
    """Bound each socket read AND the complete body, including slow trickles."""
    def __init__(self, stream, connection, size, idle, total):
        self.stream, self.connection, self.remaining = stream, connection, size
        self.idle, self.deadline = idle, time.monotonic() + total

    def read(self, size=-1):
        size = self.remaining if size is None or size < 0 else min(size, self.remaining)
        chunks, left = [], size
        while left:
            remaining_time = self.deadline - time.monotonic()
            if remaining_time <= 0:
                raise RequestError("BODY_TIMEOUT", 408)
            self.connection.settimeout(min(self.idle, remaining_time))
            try:
                part = self.stream.read1(min(left, 65536))
            except (socket.timeout, TimeoutError):
                raise RequestError("BODY_TIMEOUT", 408) from None
            if not part:
                raise RequestError("BODY_INCOMPLETE")
            left -= len(part)
            self.remaining -= len(part)
            chunks.append(part)
        return b"".join(chunks)

    def __getattr__(self, name):
        return getattr(self.stream, name)


@contextmanager
def request_body(handler, path, config, *, maximum=None):
    raw_routes = {"/api/gene": "gene_bytes", "/api/batch/add": "batch_bytes",
                  "/api/torch/table": "table_bytes", "/api/torch/recognize": "recognize_bytes"}
    maximum = maximum if maximum is not None else limit(config, raw_routes.get(path, "json_bytes"))
    # Preserve the existing dedicated control/session ceilings.
    if path.startswith("/api/muse/"):
        maximum = 48 * 1024**2
    elif path.startswith("/api/phone-tail/") or path == "/api/desktop-tail/open":
        maximum = 8192
    elif path == "/api/starling/baseline":
        maximum = 32768
    size = content_length(handler.headers, maximum)
    original, timeout = handler.rfile, handler.connection.gettimeout()
    reader = DeadlineReader(original, handler.connection, size, limit(config, "idle_seconds"),
                            limit(config, "upload_seconds" if path in raw_routes else "json_seconds"))
    handler.rfile = reader
    try:
        yield size
    finally:
        if reader.remaining:
            handler.close_connection = True
        handler.rfile = original
        handler.connection.settimeout(timeout)


def log_field(value):
    # Retain TSV layout; no user field may create another line or column.
    return "".join(f"\\u{ord(c):04x}" if ord(c) < 32 or ord(c) == 127 or c in "\u2028\u2029" else c
                   for c in str(value))
