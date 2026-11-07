"""Phone lifecycle P. Startup A -> P; runtime A -> R -> P -> V only.

SQL delegates never acquire P. Standalone, unpublished stores retain their
caller's serialization contract. A phone Authority requires a bound store.
"""
from contextlib import nullcontext
from functools import wraps
import threading


def bind(app):
    with getattr(app, "lock", nullcontext()):
        lock = getattr(app, "_phone_lifecycle_lock", None)
        if lock is None:
            lock = app._phone_lifecycle_lock = threading.RLock()
        for inst in app.instances.values():
            store = getattr(inst, "cluster", None)
            if store is None:
                continue
            previous = getattr(store, "_phone_lifecycle_lock", lock)
            if previous is not lock:
                raise RuntimeError("phone lifecycle binding mismatch")
            store._phone_lifecycle_lock = lock
        return lock


def bound(app, store):
    lock = getattr(app, "_phone_lifecycle_lock", None)
    if lock is None or getattr(store, "_phone_lifecycle_lock", None) is not lock:
        raise RuntimeError("phone lifecycle binding mismatch")
    return lock


def guard(store):
    return getattr(store, "_phone_lifecycle_lock", None) or nullcontext()


def serialized(function):
    @wraps(function)
    def call(store, *args, **kwargs):
        with guard(store):
            return function(store, *args, **kwargs)
    return call


def revoke(app, inst, key, gid, now):
    # Called under A; report callback remains outside this P interval.
    with bound(app, inst.cluster):
        grant = inst.cluster.revoke(gid, now)
        if grant["card"] == "SOMALOOP_TAIL":
            app.phone_tail.revoked(key, grant["id"])
        return grant
