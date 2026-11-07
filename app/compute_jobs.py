"""Recoverable hints for saved-data computation; formal H1 history stays authoritative.

Lock order: app.lock -> condition. Never acquire app.lock while holding condition.
The existing calculation remains serialized; this module separates save acknowledgement,
not the calculation's consistency boundary. No health values are stored in job state.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import threading
import uuid

from h1_common import H1Error
from sqlite_util import assert_inside
from startorch_outbox import open_startorch
from cards import open_startrack, save_delivery_scope
from startrack_import import import_pending

ENABLED = True
_LOCAL = threading.local()
STATES = {"PENDING", "RUNNING", "DONE", "FAILED"}


@contextmanager
def selected(inst, mode):
    if mode not in (None, "background-v1"):
        raise H1Error("COMPUTE_MODE_INVALID", "")
    previous = getattr(_LOCAL, "instance", None)
    _LOCAL.instance = inst if mode and ENABLED and getattr(inst.app, "compute_jobs", None) else None
    try:
        yield
    finally:
        _LOCAL.instance = previous


def pending_after_save(inst):
    """Called after export, inside the save lock. None selects legacy synchronous work."""
    if getattr(_LOCAL, "instance", None) is not inst:
        return None
    track = open_startrack(inst.ctx)
    try:
        imported = import_pending(track, inst.ctx, inst.app.registry, imported_at=inst.now())
        if imported.error or imported.pending_commits:
            return None  # original sync produces its existing, truthful error response
    finally:
        track.close()
    try:
        return inst.app.compute_jobs.enqueue(inst)
    except Exception as exc:
        inst.app.log("compute_enqueue_failed", type(exc).__name__)
        return None  # data already saved: finish through the existing synchronous path


def source_seq(inst):
    conn = open_startorch(inst.ctx)
    try:
        return conn.execute("SELECT COALESCE(MAX(seq_to),0) FROM h1_commit").fetchone()[0]
    finally:
        conn.close()


def state_path(inst):
    path = inst.ctx.root / "startrack" / "compute-state.json"
    assert_inside(inst.ctx.root, path)
    return path


def load(inst):
    path = state_path(inst)
    if not path.exists():
        return None
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        data = f.read(8193)
    if len(data) > 8192:
        raise ValueError("COMPUTE_STATE_INVALID")
    d = json.loads(data)
    if (d.get("schema") != "ptds-compute-state/1" or d.get("instance_id") != inst.ctx.instance_id
            or d.get("state") not in STATES or type(d.get("generation")) is not int
            or d["generation"] < 1 or type(d.get("source_seq")) is not int or d["source_seq"] < 0):
        raise ValueError("COMPUTE_STATE_INVALID")
    return d


def persist(inst, state):
    path = state_path(inst)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert_inside(inst.ctx.root, path)
    tmp = path.with_name(".compute-" + uuid.uuid4().hex + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
            f.flush()
            os.fsync(f.fileno())
        assert_inside(inst.ctx.root, path)
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if tmp.exists():
            tmp.unlink()


class Manager:
    def __init__(self, app):
        self.app = app
        self.condition = threading.Condition()
        self.states = {}
        self.pending = {}  # one latest hint per instance, never a health-record cache
        self._tickets = {}
        self._next_ticket = 0
        self.stopping = False
        self.thread = None
        for key, inst in app.instances.items():
            try:
                state = load(inst)
            except Exception as exc:
                app.log("compute_restore_failed", type(exc).__name__)
                state = {"schema": "ptds-compute-state/1", "instance_id": inst.ctx.instance_id,
                         "generation": 0, "source_seq": 0, "state": "FAILED",
                         "error": "COMPUTE_STATE_UNAVAILABLE", "at": inst.now()}
            if state:
                self.states[key] = dict(state)
                if state["state"] in ("PENDING", "RUNNING"):
                    self.pending[key] = state["generation"]
                    self._next_ticket += 1
                    self._tickets[key] = self._next_ticket

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._loop, daemon=True, name="PTDS-compute-jobs")
            self.thread.start()

    def stop(self):
        with self.condition:
            self.stopping = True
            self.condition.notify_all()

    def status(self, key):
        with self.condition:
            state = self.states.get(key)
            return dict(state) if state else {"state": "IDLE", "instance_id": self.app.inst(key).ctx.instance_id}

    def enqueue(self, inst, *, retry=False):
        # Caller holds app.lock, serializing source generation with computation and mutation.
        key = inst.spec["key"]
        previous = load(inst)  # refuse to replace an invalid/unbound state file
        seq = source_seq(inst)
        generation = (previous or {}).get("generation", 0) + (0 if retry and previous else 1)
        state = {"schema": "ptds-compute-state/1", "instance_id": inst.ctx.instance_id,
                 "generation": generation, "source_seq": seq, "state": "PENDING",
                 "error": None, "at": inst.now()}
        persist(inst, state)
        with self.condition:
            self.states[key] = dict(state)
            self.pending[key] = generation
            self._next_ticket += 1
            self._tickets[key] = self._next_ticket
            self.condition.notify_all()
        return {"ok": True, "state": "PENDING", "generation": generation, "at": state["at"]}

    def current_ticket(self, key, ticket):
        with self.condition:
            return self._tickets.get(key) == ticket

    def _publish(self, key, inst, state, *, ticket=None):
        with self.condition:
            if (self.states[key]["generation"] != state["generation"]
                    or ticket is not None and self._tickets.get(key) != ticket):
                return
        persist(inst, state)
        with self.condition:
            if (self.states[key]["generation"] == state["generation"]
                    and (ticket is None or self._tickets.get(key) == ticket)):
                self.states[key] = dict(state)

    def run_one(self, key):
        """Also used by deterministic synthetic tests; computes the latest locked prefix."""
        inst = self.app.inst(key)
        with save_delivery_scope(True, lambda exc: self.app.log("delivery_failed", type(exc).__name__)):
            with self.app.lock:
                with self.condition:
                    generation = self.pending.pop(key, None)
                    if generation is None:
                        return
                    state = dict(self.states[key])
                try:
                    state.update(state="RUNNING", at=inst.now())
                    self._publish(key, inst, state)
                    # Original lock protects definitions, grants, inputs and publication together.
                    inst.export(repair=True)
                    result = inst.sync_track("SAVE_BACKGROUND")
                    state.update(state="DONE" if result.get("ok") and not result.get("custom_error") else "FAILED",
                                 error=None if result.get("ok") and not result.get("custom_error") else "COMPUTE_FAILED",
                                 source_seq=source_seq(inst), at=inst.now())
                    self._publish(key, inst, state)
                except Exception as exc:
                    self.app.log("compute_failed", type(exc).__name__)
                    state.update(state="FAILED", error="COMPUTE_FAILED", at=inst.now())
                    try:
                        self._publish(key, inst, state)
                    except Exception as persist_error:
                        self.app.log("compute_state_failed", type(persist_error).__name__)
                        with self.condition:
                            if self.states[key]["generation"] == generation:
                                self.states[key] = dict(state, error="COMPUTE_STATE_UNAVAILABLE")

    def _loop(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.stopping or self.pending)
                if self.stopping:
                    return
                key = next(iter(self.pending))
            self.run_one(key)
