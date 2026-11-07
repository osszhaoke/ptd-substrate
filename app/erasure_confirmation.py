"""Internal ephemeral credential owner; no route, deletion or SELF evidence.

The same-origin local UI adapter may issue/claim these credentials after
verifying its session and actual click. Checkbox/word are necessary checks, not
proof of a human event. HTTP erasure claims this component before recording durable confirmation.
Restart intentionally loses all authority; accounting cannot recreate tokens.
"""
from dataclasses import dataclass
import re
import secrets
import threading
import time
import uuid

from h1_common import H1Error

TTL_SECONDS = 300
MAX_PENDING = 128  # Engineering memory guard, not a business retention period.


def _fail(code):
    raise H1Error(code, '')


@dataclass(frozen=True)
class Binding:
    instance_id: str
    provider: str
    scope_digest: str
    preview_digest: str
    request_id: str
    include_archives: bool
    revoke: bool
    local_session: str

    def __post_init__(self):
        if (not isinstance(self.instance_id, str) or
                not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', self.instance_id) or
                self.provider != 'oura' or type(self.include_archives) is not bool or
                type(self.revoke) is not bool or not isinstance(self.local_session, str) or
                not 32 <= len(self.local_session) <= 256):
            _fail('ERASURE_BINDING_INVALID')
        for value in (self.scope_digest, self.preview_digest):
            if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
                _fail('ERASURE_BINDING_INVALID')
        try:
            if str(uuid.UUID(self.request_id)) != self.request_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            _fail('ERASURE_BINDING_INVALID')


class ConfirmationStore:
    """One owner/lock; no filesystem, database or network operations."""

    def __init__(self, *, clock=time.monotonic, capacity=MAX_PENDING):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError('capacity must be positive')
        self._clock, self._capacity = clock, capacity
        self._pending = {}
        self._lock = threading.Lock()

    def issue(self, binding):
        if not isinstance(binding, Binding):
            _fail('ERASURE_BINDING_INVALID')
        with self._lock:
            now = self._clock()
            self._pending = {k:v for k,v in self._pending.items() if now < v[1]}
            if len(self._pending) >= self._capacity:
                _fail('ERASURE_CONFIRMATIONS_FULL')
            token = secrets.token_urlsafe(32)
            while token in self._pending:
                token = secrets.token_urlsafe(32)
            self._pending[token] = binding, now + TTL_SECONDS
            return token

    def claim(self, token, binding, *, checked, word):
        """Trusted adapter only; invalid attempts also consume this credential."""
        if not isinstance(token, str) or not isinstance(binding, Binding):
            _fail('ERASURE_CONFIRMATION_INVALID')
        with self._lock:
            value = self._pending.pop(token, None)
            if value is None:
                _fail('ERASURE_CONFIRMATION_INVALID')
            original, deadline = value
            if self._clock() >= deadline:
                _fail('ERASURE_CONFIRMATION_EXPIRED')
            if original != binding:
                _fail('ERASURE_PREVIEW_CHANGED')
            if checked is not True or word != '擦除':
                _fail('ERASURE_CONFIRMATION_REQUIRED')
            return str(uuid.uuid4())  # A reference, not durable confirmation yet.

    def cancel_session(self, local_session):
        with self._lock:
            self._pending = {k:v for k,v in self._pending.items()
                             if v[0].local_session != local_session}


_OWNER_LOCK = threading.Lock()
COOKIE = 'ptds_erasure_session'


def owner(app):
    with _OWNER_LOCK:
        if not hasattr(app, '_erasure_authority'):
            app._erasure_authority = (secrets.token_bytes(32), ConfirmationStore())
        return app._erasure_authority


def session(app, headers, *, create=False):
    import hashlib
    import hmac
    from http.cookies import SimpleCookie
    secret, store = owner(app)
    cookie = SimpleCookie()
    try:
        cookie.load(headers.get('Cookie', ''))
        value = cookie[COOKIE].value if COOKIE in cookie else ''
    except Exception:
        value = ''
    name, _, signature = value.partition('.')
    valid = bool(re.fullmatch('[0-9a-f]{64}', name)) and hmac.compare_digest(
        signature, hmac.new(secret, name.encode(), hashlib.sha256).hexdigest())
    if valid:
        return value, None
    if not create:
        _fail('ERASURE_LOCAL_SESSION_REQUIRED')
    name = secrets.token_hex(32)
    value = name + '.' + hmac.new(secret, name.encode(), hashlib.sha256).hexdigest()
    return value, COOKIE+'='+value+'; Path=/api/oura/raw/erase/; HttpOnly; SameSite=Strict'
