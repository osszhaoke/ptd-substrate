"""Configured receiving targets. Pure resolution; callers retain ownership of A."""
from h1_common import H1Error

ERRORS = {'garmin': 'GARMIN_TARGET_MISMATCH', 'qkeer': 'QKEER_TARGET_MISMATCH',
          'somaloop_agent': 'SOMALOOP_TARGET_MISMATCH', 'oura': 'OURA_AUTHORIZATION_CHANGED'}


def configured_key(app, provider):
    config = getattr(app, 'config', {})
    values = config.get('oura' if provider == 'oura' else 'device_targets') or {}
    value = values.get('instance_key' if provider == 'oura' else provider) if isinstance(values, dict) else None
    return value if isinstance(value, str) and value else None


def resolve(app, provider, requested_key=None):
    key = configured_key(app, provider)
    inst = getattr(app, 'instances', {}).get(key) if key is not None else None
    if (inst is None or requested_key != key or getattr(inst, 'spec', {}).get('key') != key
            or not getattr(getattr(inst, 'ctx', None), 'instance_id', None)):
        raise H1Error(ERRORS[provider], '')
    return inst


def require(inst, provider, body):
    app = getattr(inst, 'app', None)
    selected = resolve(app, provider, body.get('key'))
    if selected is not inst:
        raise H1Error(ERRORS[provider], '')
    return selected


# One binding owner per host. Acquire G before A; never wait for G while A is
# held. The initialisation lock only publishes G and does no I/O or callbacks.
import threading
from dataclasses import dataclass
_INIT = threading.Lock()


def binding_gate(app):
    with _INIT:
        if not hasattr(app, '_oura_binding_gate'):
            app._oura_binding_gate = threading.RLock()
        return app._oura_binding_gate


@dataclass(frozen=True)
class OuraBinding:
    key: str
    instance_id: str
    instance: object
    generation: object


def capture_oura(app, key, *, advance=False):
    """A-owned capture; a new authorization invalidates all older states."""
    inst = resolve(app, 'oura', key)
    if advance or not hasattr(app, '_oura_binding_generation'):
        app._oura_binding_generation = object()
    inst._oura_authorization_generation = app._oura_binding_generation  # Alias for existing disconnect observers.
    return OuraBinding(key, inst.ctx.instance_id, inst, app._oura_binding_generation)


def validate_oura(app, binding):
    """A-owned check, without fallback, I/O or mutation."""
    inst = resolve(app, 'oura', binding.key)
    if (inst is not binding.instance or inst.ctx.instance_id != binding.instance_id
            or getattr(app, '_oura_binding_generation', None) is not binding.generation):
        raise H1Error('OURA_AUTHORIZATION_CHANGED', '')
    return inst


def invalidate_oura(app, inst):
    """G -> A owner calls this before any fallible disconnect I/O."""
    app._oura_binding_generation = object()
    inst._oura_authorization_generation = app._oura_binding_generation


def bound_client(binding, client_factory):
    client = client_factory(binding.instance)
    if client.account != binding.instance_id:
        raise H1Error('OURA_AUTHORIZATION_CHANGED', '')
    return client
