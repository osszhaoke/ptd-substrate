"""Local product responses: finish business locks before writing to a socket.

This does not alter transaction boundaries, response bodies or authorization.
Only immutable response bytes are retained until the route has returned.
"""
from http.server import BaseHTTPRequestHandler
import gzip


def accepts_gzip(value):
    """Honor an explicit gzip quality, including gzip;q=0 over a wildcard."""
    qualities = {}
    for part in value.lower().split(","):
        fields = part.strip().split(";")
        quality = 1.0
        for field in fields[1:]:
            if field.strip().startswith("q="):
                try:
                    quality = float(field.strip()[2:])
                except ValueError:
                    quality = 0.0
        qualities[fields[0].strip()] = quality if 0 <= quality <= 1 else 0.0
    return qualities.get("gzip", qualities.get("*", 0)) > 0


class DeferredResponseHandler(BaseHTTPRequestHandler):
    response_timeout = 5.0

    def dispatch_response(self, route):
        self._pending_response = None
        self._defer_response = True
        try:
            route()
            reply = self._pending_response
        finally:
            self._defer_response = False
            self._pending_response = None
        # All route context managers (including nested locks/body guards) exited.
        if reply is not None:
            self._write_response(*reply)

    def _send(self, status, body, kind="application/json; charset=utf-8", headers=()):
        reply = (status, body, kind, tuple(headers))
        if getattr(self, "_defer_response", False):
            self._pending_response = reply
        else:
            self._write_response(*reply)

    def _write_response(self, status, body, kind, headers):
        # CPU work and socket writes both occur after the business lock exits.
        # Only local product JSON/HTML; downloads and independent phone gateways
        # keep their existing transport. Uncompressed clients remain supported.
        if (status == 200 and len(body) >= 16384 and
                kind.split(";", 1)[0] in ("application/json", "text/html") and
                not any(k.lower() == "content-encoding" for k, _ in headers)):
            vary = [v for k, v in headers if k.lower() == "vary"]
            headers = tuple((k, v) for k, v in headers if k.lower() != "vary")
            headers += (("Vary", ", ".join(vary + ["Accept-Encoding"])),)
            if accepts_gzip(self.headers.get("Accept-Encoding", "")):
                body = gzip.compress(body, compresslevel=1, mtime=0)
                headers += (("Content-Encoding", "gzip"),)
        previous_timeout = self.connection.gettimeout()
        try:
            self.connection.settimeout(self.response_timeout)
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionError, TimeoutError):
            # Delivery failure does not roll back a committed write or retry it.
            self.close_connection = True
        finally:
            self.connection.settimeout(previous_timeout)
