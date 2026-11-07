"""Disposable two-slot cache, owned by an Instance under the caller's app lock.

Only serialized aggregate data is retained, never a Connection or signed cursor.
MAX_BYTES bounds retained JSON bytes, not transient computation or Python RSS.
"""
import json

MAX_BYTES = 1024 * 1024


def slots(inst, version):
    state = getattr(inst, '_data_read_pages', None)
    if state is None or state[0] != version:
        state = (version, {})
        inst._data_read_pages = state
    return state[1]


def get(inst, version, slot):
    raw = slots(inst, version).get(slot)
    return json.loads(raw) if raw is not None else None


def put(inst, version, slot, value):
    entries = slots(inst, version)
    try:
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError):
        return  # Optional cache must not alter the original response contract.
    if len(raw) + sum(len(v) for k, v in entries.items() if k != slot) > MAX_BYTES:
        entries.clear()
        return
    entries[slot] = raw


def capture(owner, private):
    """Called under A; copy only the bounded immutable JSON-byte references."""
    state = getattr(owner, '_data_read_pages', None)
    if state is not None:
        private._data_read_pages = (state[0], dict(state[1]))
