"""Partner-only startup policy. One frozen owner; no account or network operations.

This distribution layer rejects before business dispatch. It never grants device
access, replaces source provenance or changes the underlying input limits.
"""
from dataclasses import dataclass
import io
from http.server import ThreadingHTTPServer
import socket
import vision_runtime
import partner_ocr
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import input_guard
from h1_common import H1Error

PERSONAL_KEYS = frozenset(('LIVE_REAL', 'LIVE', 'ELDER'))
PERSONAL_IDS = frozenset(('live-real', 'elder', 'live-replay'))
PROVIDERS = ('garmin', 'qkeer', 'somaloop_agent')
PUBLIC_GET = frozenset(('/', '/index.html', '/favicon.ico', '/api/health', '/api/dict', '/api/starling/state', '/api/device-links'))
TARGET_GET = frozenset(('/api/gene', '/api/gene/db', '/api/gene/lookup', '/api/gene/coverage', '/api/state', '/api/state/refresh', '/api/home', '/api/sources', '/api/data/read',
    '/api/torch/engine', '/api/torch/versions', '/api/torch/original', '/api/graph/document',
    '/api/graph/observation', '/api/graph/related', '/api/graph/kg', '/api/graph/read', '/api/graph', '/api/graph/trace',
    '/api/pillbox/status', '/api/compute/status'))
TARGET_POST = frozenset((partner_ocr.UPLOAD, partner_ocr.CONFIRM, partner_ocr.CANCEL, '/api/gene', '/api/gene/delete', '/api/torch/table', '/api/torch/save', '/api/torch/correct', '/api/torch/retract', '/api/data/read', '/api/pillbox/scan', '/api/pillbox/find'))
OURA_POST = frozenset(('/api/oura/sync', '/api/oura/disconnect', '/api/device-links/action'))
NOT_FOUND = {'error': 'NOT_FOUND'}


def fail():
    raise H1Error('INSTANCE_UNKNOWN', '')


def validate_specs(config, root):
    if 'instances' not in config or not isinstance(config['instances'], list):
        fail()
    keys, ids, roots = set(), set(), set()
    root = Path(root)
    if root.is_symlink():
        fail()
    for spec in config['instances']:
        if not isinstance(spec, dict):
            fail()
        key, identity = spec.get('key'), spec.get('id')
        if (not isinstance(key, str) or not key or key in PERSONAL_KEYS or key in keys
                or not isinstance(identity, str) or not identity or identity in PERSONAL_IDS
                or identity.endswith('-wal-20261106') or identity in ids
                or identity in ('.', '..') or '/' in identity or '\\' in identity):
            fail()
        directory = root / identity
        if directory.is_symlink() or str(directory.resolve()) in roots:
            fail()
        keys.add(key); ids.add(identity); roots.add(str(directory.resolve()))
    return frozenset(keys)


@dataclass(frozen=True)
class Policy:
    target: str | None
    available: frozenset
    oura: bool
    callback: str

    @classmethod
    def build(cls, config, root):
        keys = validate_specs(config, root)
        # Installer disables these. Fail closed if a manually edited template enables them.
        if config.get('band_bridge', False) is not False or (config.get('starling') or {}).get('enabled') is not False:
            fail()
        # These flags have effects at startup even if every corresponding HTTP route is denied.
        for name in ('state_report_phone', 'device_daily'):
            setting = config.get(name, {})
            if not isinstance(setting, dict) or setting.get('enabled', False) is not False:
                fail()
        if config.get('macos_notify', False) is not False:
            fail()
        oura_config = config.get('oura') or {}
        if not isinstance(oura_config, dict):
            fail()
        address = urlsplit(oura_config.get('redirect_uri') or '')
        extra_listener = address.hostname in ('localhost', '127.0.0.1', '::1') and address.port and address.port != config.get('port',8780)
        if not keys and extra_listener:
            fail()
        if not keys:
            return cls(None, keys, False, '/oauth/oura/callback')
        targets = config.get('device_targets')
        if not isinstance(targets, dict) or set(targets) != set(PROVIDERS):
            fail()
        values = tuple(targets[p] for p in PROVIDERS)
        if any(not isinstance(v, str) or v not in keys for v in values) or len(set(values)) != 1:
            fail()
        target = values[0]
        oura = config.get('oura') or {}
        if not isinstance(oura, dict):
            fail()
        ready = bool(oura) and oura.get('instance_key') == target
        if extra_listener and not ready:
            fail()
        callback = urlsplit(oura.get('redirect_uri') or '/oauth/oura/callback').path
        if not callback.startswith('/') or callback in PUBLIC_GET | TARGET_GET or callback.startswith('/api/'):
            fail()
        return cls(target, keys, ready, callback)

    def specs(self, config):
        # Explicitly supplied instances remain registered; request admission and
        # visible cards use the selected target. Installer emits only that target.
        return list(config['instances'])

    def instances(self, app):
        return {self.target: app.instances[self.target]} if self.target in app.instances else {}

    def selected(self, value):
        return self.target is not None and isinstance(value, str) and value == self.target

    def may_poll(self, inst):
        return self.oura and self.selected(inst.spec.get('key'))

    def path_allowed(self, method, path):
        if path.startswith('/api/gene') and method not in ('GET','POST'):
            return False
        if method == 'GET':
            return path in PUBLIC_GET | TARGET_GET or (self.oura and path in ('/oauth/oura/start', self.callback))
        return path in TARGET_POST or (self.oura and path in OURA_POST)

    def ui_capabilities(self):
        reads = PUBLIC_GET | (TARGET_GET if self.target else frozenset())
        writes = TARGET_POST if self.target else frozenset()
        if self.oura:
            reads |= {'/oauth/oura/start', self.callback}
            writes |= OURA_POST
        return {'GET': sorted(reads), 'POST': sorted(writes), 'oura': self.oura}

    def request_allowed(self, method, path, query, body=None):
        if not self.path_allowed(method, path):
            return False
        values = query.get('key', [])
        if len(values) > 1 or (values and not self.selected(values[0])):
            return False
        if path.startswith('/api/gene') and (len(values) != 1 or 'instance_id' in query or len(query.get('nature', [])) > 1):
            return False
        if path in ('/api/graph/kg', partner_ocr.UPLOAD, partner_ocr.CONFIRM, partner_ocr.CANCEL) and ('instance_id' in query or len(values) != 1):
            return False
        if path == self.callback and method == 'GET':
            return self.oura
        if method == 'GET' and path in PUBLIC_GET:
            return not values or self.selected(values[0])
        body = body or {}
        if path in ('/api/torch/correct', '/api/torch/retract'):
            if 'instance_id' in query or ('key' not in body and not values):
                return False
        selected_fields = [body[n] for n in ('key', 'instance_key') if n in body]
        if any(not self.selected(v) for v in selected_fields):
            return False
        if 'instance_id' in body:
            return False  # No published CSV/Oura request contract requires a second target ID.
        if not values and not selected_fields:
            return False
        if path == '/api/device-links/action':
            return self.oura and body.get('id') == 'oura' and body.get('action') == 'retry'
        return True


class PartnerHTTPServer(ThreadingHTTPServer):
    """Let the kernel queue connections while the application returns busy receipts."""
    request_queue_size = socket.SOMAXCONN


def install(handler_class, app):
    """Wrap each request once, before the existing route and A lock are entered."""
    policy = app.trial
    original_get, original_post = handler_class.do_GET, handler_class.do_POST

    def get(handler):
        url = urlsplit(handler.path)
        query = parse_qs(url.query, keep_blank_values=True)
        if not policy.request_allowed('GET', url.path, query):
            return handler._json(404, NOT_FOUND)
        return original_get(handler)

    def post(handler):
        url = urlsplit(handler.path)
        if not policy.path_allowed('POST', url.path):
            handler.close_connection = True
            return handler._json(404, NOT_FOUND)
        # Do not read a body before the existing local-browser header check.
        if handler.headers.get('X-PTDS') != '1':
            return original_post(handler)
        if url.path == partner_ocr.UPLOAD:
            query = parse_qs(url.query, keep_blank_values=True)
            if not policy.request_allowed('POST', url.path, query):
                handler.close_connection = True
                return handler._json(404, NOT_FOUND)
            return partner_ocr.upload_http(handler, app, query)
        if url.path == '/api/gene':
            # A raw upload is target-checked before any body read. The normal handler owns
            # the byte limit, per-instance nature admission and streaming deadline.
            if not policy.request_allowed('POST', url.path, parse_qs(url.query, keep_blank_values=True)):
                handler.close_connection = True
                return handler._json(404, NOT_FOUND)
            return original_post(handler)
        original = handler.rfile
        try:
            with input_guard.request_body(handler, url.path, app.config):
                raw = handler.rfile.read()
            data = input_guard.json_object(raw) if url.path != '/api/torch/table' else {}
            query = parse_qs(url.query, keep_blank_values=True)
            if not policy.request_allowed('POST', url.path, query, data):
                return handler._json(404, NOT_FOUND)
            if url.path in (partner_ocr.CONFIRM, partner_ocr.CANCEL):
                inst = app.inst(query['key'][0])
                if url.path == partner_ocr.CANCEL:
                    app.ocr_reviews.cancel(inst, data.get('draft'))
                    return handler._json(200, {'cancelled': True})
                return handler._json(200, app.ocr_reviews.confirm(inst, data))
            handler.rfile = io.BytesIO(raw)
            return original_post(handler)
        except input_guard.RequestError as exc:
            handler.close_connection = True
            return handler._json(exc.status, {'error': exc.code})
        except H1Error as exc:
            handler.close_connection = True
            return handler._json(400, {'error': exc.code, 'detail': exc.detail})
        finally:
            handler.rfile = original
    handler_class.do_GET, handler_class.do_POST = vision_runtime.partner_request(get), vision_runtime.partner_request(post)
    return handler_class


def check_data_policy(ctx, spec):
    """Configuration must describe the actual space. Installing cannot widen its policy."""
    accepted = spec.get('accept')
    if not isinstance(accepted, list) or len(accepted) != len(ctx.accept) or set(accepted) != set(ctx.accept):
        raise H1Error('INSTANCE_POLICY_MISMATCH', 'Selected data types differ from this data space')
