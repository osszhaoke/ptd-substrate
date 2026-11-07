"""Generic, empty-payload Web Push. No report, reading or card name leaves here.

RFC 8030/8292; OpenSSL is already a PTDS dependency. TLS validates the provider
hostname while connecting to a validated public address (no second DNS lookup).
No redirects, cookies, proxy environment variables, response bodies or logs.
"""
from __future__ import annotations

import base64
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import time
from urllib.parse import urlsplit


HOSTS = {"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"}


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def decoded(value, size):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("PUSH_SUBSCRIPTION_INVALID")
    result = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if len(result) != size:
        raise ValueError("PUSH_SUBSCRIPTION_INVALID")
    return result


def validate_subscription(subscription):
    if not isinstance(subscription, dict) or set(subscription) - {"endpoint", "keys", "expirationTime"}:
        raise ValueError("PUSH_SUBSCRIPTION_INVALID")
    endpoint = subscription.get("endpoint")
    if not isinstance(endpoint, str) or len(endpoint) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in endpoint):
        raise ValueError("PUSH_ENDPOINT_INVALID")
    u = urlsplit(endpoint)
    if (u.scheme != "https" or u.hostname not in HOSTS or u.netloc != u.hostname
            or u.username or u.password or u.fragment or not u.path.startswith("/")):
        raise ValueError("PUSH_ENDPOINT_INVALID")
    keys = subscription.get("keys")
    if not isinstance(keys, dict) or set(keys) != {"p256dh", "auth"}:
        raise ValueError("PUSH_SUBSCRIPTION_INVALID")
    if decoded(keys["p256dh"], 65)[0] != 4:
        raise ValueError("PUSH_SUBSCRIPTION_INVALID")
    decoded(keys["auth"], 16)
    # Keys are validated but unused: the body is empty, never unencrypted health data.
    return {"endpoint": endpoint, "keys": dict(keys)}


def _openssl(*args, data=None):
    p = subprocess.run(["openssl", *args], input=data, capture_output=True, timeout=5)
    if p.returncode:
        raise ValueError("PUSH_KEY_INVALID")
    return p.stdout


def _raw_signature(der):
    # OpenSSL ECDSA DER: SEQUENCE of two positive INTEGERs, exactly P-256.
    if len(der) < 8 or der[0] != 0x30 or der[1] != len(der) - 2:
        raise ValueError("PUSH_SIGNATURE_INVALID")
    off, out = 2, []
    for _ in range(2):
        if off + 2 > len(der) or der[off] != 2:
            raise ValueError("PUSH_SIGNATURE_INVALID")
        n = der[off + 1]; val = der[off + 2:off + 2 + n]; off += 2 + n
        if not val or val[0] & 128 or len(val.lstrip(b"\0")) > 32:
            raise ValueError("PUSH_SIGNATURE_INVALID")
        out.append(val.lstrip(b"\0").rjust(32, b"\0"))
    if off != len(der):
        raise ValueError("PUSH_SIGNATURE_INVALID")
    return b"".join(out)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, 443, timeout=5, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


class Transport:
    validate_subscription = staticmethod(validate_subscription)

    def __init__(self, config=None):
        self.config = config or {}
        self.public_key = None
        self.key = None
        self.subject = None
        # No file reads/key generation/network when disabled or unconfigured.
        if self.config.get("enabled") is not True:
            return
        try:
            key = Path(self.config["private_key_path"])
            subject = self.config["subject"]
            if (not key.is_absolute() or key.is_symlink() or not key.is_file()
                    or key.stat().st_mode & 0o077 or not isinstance(subject, str)
                    or not re.fullmatch(r"(?:mailto:[^\s@]+@[^\s@]+|https://[^\s]+)", subject)):
                raise ValueError("PUSH_KEY_INVALID")
            public = _openssl("pkey", "-in", str(key), "-pubout", "-outform", "DER")
            # DER SubjectPublicKeyInfo header for id-ecPublicKey + prime256v1.
            prefix = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200")
            if len(public) != len(prefix) + 65 or not public.startswith(prefix) or public[len(prefix)] != 4:
                raise ValueError("PUSH_KEY_INVALID")
            self.key, self.subject, self.public_key = key, subject, b64(public[len(prefix):])
        except (OSError, KeyError, ValueError, subprocess.SubprocessError):
            # Safe status; never expose path, key, provider endpoint or stderr.
            pass

    def authorization(self, endpoint, now=None):
        if self.public_key is None:
            raise ValueError("PUSH_NOT_CONFIGURED")
        header = b64(b'{"typ":"JWT","alg":"ES256"}')
        u = urlsplit(endpoint)
        claims = b64(json.dumps({"aud": "https://" + u.hostname, "exp": int(now or time.time()) + 3600,
                                 "sub": self.subject}, separators=(",", ":")).encode())
        message = (header + "." + claims).encode()
        signature = _raw_signature(_openssl("dgst", "-sha256", "-sign", str(self.key), data=message))
        return "vapid t=" + message.decode() + "." + b64(signature) + ", k=" + self.public_key

    def send(self, subscription):
        if self.public_key is None:
            return {"state": "setup_required"}
        try:
            item = validate_subscription(subscription)
            u = urlsplit(item["endpoint"])
            # No environment proxies; pin a numeric globally routable address.
            from phone_tail import resolve_addresses
            addresses = resolve_addresses(u.hostname, 443)
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
                return {"state": "rejected"}
            auth = self.authorization(item["endpoint"])
            conn = _PinnedHTTPS(u.hostname, sorted(addresses)[0])
            try:
                conn.request("POST", u.path + ("?" + u.query if u.query else ""), b"", {
                    "Authorization": auth, "TTL": "0", "Urgency": "normal",
                    "Topic": "ptds-state-report", "Content-Length": "0"})
                response = conn.getresponse()
                status = response.status
                # 201/202 is provider acceptance, never device-delivered/read.
                state = "accepted" if status in (201, 202) else "expired" if status in (404, 410) else "rejected"
                return {"state": state, "status": status}
            finally:
                conn.close()
        except (OSError, ValueError, subprocess.SubprocessError, http.client.HTTPException):
            # An ambiguous transport failure is not automatically retried.
            return {"state": "unknown"}
