"""Read-only SQLite snapshots and detached HTTP JSON; no schema or authority."""
from contextlib import contextmanager
from copy import deepcopy
import json
from http_response import DeferredResponseHandler


@contextmanager
def read_connection(factory, ctx):
    """Own one connection and one read snapshot; reject writes on every build."""
    conn = factory(ctx)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


class _JSON:
    def __init__(self, value):
        # The caller still owns its business lock. Never encode a shared view
        # after unlocking, even when nested dicts are subsequently mutated.
        self.value = deepcopy(value)

    def encode(self):
        return json.dumps(self.value, ensure_ascii=False).encode("utf-8")


class ReadResponseHandler(DeferredResponseHandler):
    def _json(self, status, obj):
        body = _JSON(obj)
        self._send(status, body if getattr(self, "_defer_response", False) else body.encode())

    def _write_response(self, status, body, kind, headers):
        if isinstance(body, _JSON):
            body = body.encode()
        return super()._write_response(status, body, kind, headers)
