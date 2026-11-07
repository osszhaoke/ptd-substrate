"""Request-owned read inputs. No new writer, lock, cache or public field.

A remains held by the caller. A -> P -> D precedes all SQL; P/D are
released after pinning/copying, before cache B and expensive projection.
Track content and its metadata share a transaction even for writers outside A.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass
import json
import bioage, device_watch, phone_lifecycle
from cards import open_startrack
from startorch_outbox import open_startorch
from read_view import read_connection


class Snapshot(dict):
    """Private request provenance is not part of JSON or business permission."""
    def bind(self, bundle):
        # A deferred display error is re-raised, not reconstructed as data.
        auxiliary = bundle.authorization[-1]
        memo = {id(auxiliary): auxiliary} if isinstance(auxiliary, Exception) else None
        self._authorization_capture = deepcopy(bundle.authorization, memo)
        self._source_bytes = bundle.source_bytes
        return self


def source_view(snapshot, fallback):
    raw = getattr(snapshot, '_source_bytes', None)
    return fallback() if raw is None else json.loads(raw.decode('utf-8'))


@dataclass(frozen=True)
class ReadBundle:
    track: object
    torch: object
    metadata: tuple
    profile: dict
    setup: dict
    events: device_watch.EventPrefix
    settings: device_watch.EventPrefix
    source_bytes: bytes
    authorization: tuple


@contextmanager
def capture(inst, reader, *, track_factory=open_startrack, torch_factory=open_startorch):
    # Existing file writers are A-owned, except device events (D) and phone (P).
    # The SQL transactions outlive P/D, never the enclosing A or this request.
    with ExitStack() as connections:
        with phone_lifecycle.guard(inst.cluster), device_watch.capture_inputs(inst.ctx.root, inst.spec['cards']) as inputs:
            setup, events, settings = inputs
            authorization = inst.cluster.capture_authorization_locked()
            track = connections.enter_context(read_connection(track_factory, inst.ctx))
            torch = connections.enter_context(read_connection(torch_factory, inst.ctx))
            metadata = reader._metadata(track, split_versions=True, torch=torch)
            profile = bioage.load_profile(inst.ctx.root)
            path = inst.ctx.root / 'startorch/sources.json'
            source_bytes = path.read_bytes() if path.exists() else b'{}'
            bundle = ReadBundle(track, torch, metadata, profile, setup, events,
                                settings, source_bytes, authorization)
        yield bundle


def overlay(snapshot, result):
    """Retain private provenance when the existing volatile layer copies a dict."""
    if result is snapshot or not isinstance(snapshot, Snapshot):
        return result
    result = Snapshot(result)
    result._authorization_capture = snapshot._authorization_capture
    result._source_bytes = snapshot._source_bytes
    return result
