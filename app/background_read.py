"""Incremental, bounded read views for homepage refreshes.

The formal stores remain authoritative.  This cache neither saves observations
nor authorizes access.  All active observations remain available to the existing
calculations; only newly imported revisions are decoded after the first read.
The caller supplies the homepage builder, keeping rule implementations shared.
"""
from __future__ import annotations

from read_view import read_connection

from collections import OrderedDict
from contextlib import closing, nullcontext
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import time

from startorch_outbox import open_startorch
from cards import _obs, open_startrack
from h1_common import H1Error, parse_instant, strict_loads
from startrack_import import import_cursor
from vitals import FRESH_WINDOW
from time_freshness import fresh, local_today, next_activation, PresentationClock, ActivationIndex

CACHE_TTL = 900
MAX_INSTANCES = 4
MAX_INSTANCE_ROWS = 150_000
MAX_TOTAL_ROWS = 250_000
# These measure original UTF-8 payload bytes, not Python heap consumption.
MAX_INSTANCE_PAYLOAD_BYTES = 128 * 1024 * 1024
MAX_TOTAL_PAYLOAD_BYTES = 256 * 1024 * 1024
_LOCK = threading.RLock()
_CACHE = OrderedDict()
_CLEANUP_TIMER = None
_CLEANUP_AT = None
_CLEANUP_TOKEN = None


@dataclass
class _View:
    tz: str
    identity: tuple
    source_seq: int
    payloads: dict = field(default_factory=dict)
    revisions: dict = field(default_factory=dict)
    objects: dict = field(default_factory=dict)
    sizes: dict = field(default_factory=dict)
    projection: dict | None = None
    version: str | None = None
    projection_at: datetime | None = None
    activates_at: datetime | None = None
    expires_at: float = 0
    _observations: list | None = None
    activation_index: ActivationIndex = field(default_factory=ActivationIndex)

    @property
    def observations(self):
        if self._observations is None:
            self._observations = [self.objects[oid] for oid in sorted(self.objects)]
        return self._observations

    @property
    def payload_bytes(self):
        return sum(self.sizes.values())


def _expire(token=None):
    global _CLEANUP_TIMER, _CLEANUP_AT, _CLEANUP_TOKEN
    with _LOCK:
        if token is not None and token is not _CLEANUP_TOKEN:
            return  # a cancelled timer cannot clear a later timer's identity
        if _CLEANUP_TIMER is not None:
            _CLEANUP_TIMER.cancel()
        _CLEANUP_TIMER = _CLEANUP_AT = _CLEANUP_TOKEN = None
        now = time.monotonic()
        for key in list(_CACHE):
            if _CACHE[key].expires_at <= now:
                del _CACHE[key]
        _schedule_locked()


def _schedule_locked():
    """At most one cleanup timer, including when LRU entries are replaced."""
    global _CLEANUP_TIMER, _CLEANUP_AT, _CLEANUP_TOKEN
    if not _CACHE:
        if _CLEANUP_TIMER is not None:
            _CLEANUP_TIMER.cancel()
        _CLEANUP_TIMER = _CLEANUP_AT = _CLEANUP_TOKEN = None
        return
    deadline = min(view.expires_at for view in _CACHE.values())
    if _CLEANUP_TIMER is not None and _CLEANUP_AT <= deadline:
        return
    if _CLEANUP_TIMER is not None:
        _CLEANUP_TIMER.cancel()
    _CLEANUP_AT = deadline
    _CLEANUP_TOKEN = object()
    _CLEANUP_TIMER = threading.Timer(max(.01, deadline - time.monotonic()), _expire,
                                   args=(_CLEANUP_TOKEN,))
    _CLEANUP_TIMER.daemon = True
    _CLEANUP_TIMER.start()


def _remember(key, view):
    with _LOCK:
        _CACHE.pop(key, None)
        if (len(view.revisions) <= MAX_INSTANCE_ROWS and
                view.payload_bytes <= MAX_INSTANCE_PAYLOAD_BYTES):
            view.expires_at = time.monotonic() + CACHE_TTL
            _CACHE[key] = view
        while _CACHE and (len(_CACHE) > MAX_INSTANCES or
                          sum(len(v.revisions) for v in _CACHE.values()) > MAX_TOTAL_ROWS or
                          sum(v.payload_bytes for v in _CACHE.values()) > MAX_TOTAL_PAYLOAD_BYTES):
            _CACHE.popitem(last=False)
        _schedule_locked()


def _cached(key):
    with _LOCK:
        view = _CACHE.get(key)
        if view is not None and view.expires_at <= time.monotonic():
            del _CACHE[key]
            return None
        return view


def clear_cache():
    """Release only disposable read views, never formal data or settings."""
    with _LOCK:
        _CACHE.clear()
        _schedule_locked()


def _stat(path):
    try:
        stat = Path(path).stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns
    except FileNotFoundError:
        return None


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _freshen(projection, now, tz):
    """Clock-dependent presentation must age even without a new database row."""
    for field in ("vitals", "vitals_all"):
        vitals = projection.get(field)
        if vitals is not None:
            vitals["computed_at"] = now.isoformat(timespec="seconds")
            for item in vitals.get("items", []):
                window = FRESH_WINDOW.get(item.get("family"))
                item["fresh"] = fresh(now=now, tz=tz, window=window,
                                      instant=parse_instant(item['observed_at']) if item.get('observed_at') else None,
                                      day=item.get('observed_date'))
    # Other band fields use the latest observed night, not the wall clock.
    from band_cards import FRESH_S
    for item in (projection.get("band_cards") or {}).get("spot", []):
        item["fresh"] = bool(item.get("at") and
                             0 <= (now - parse_instant(item["at"])).total_seconds() <= FRESH_S)


class BackgroundRead:
    """One reader per Instance; bounded module cache never crosses identities."""

    def __init__(self, inst):
        self.inst = inst
        self._lock = threading.RLock()
        # A unique object avoids Python id reuse after an Instance is collected.
        self._key = object()
        self._stats = {"full_loads": 0, "incremental_loads": 0, "decoded_rows": 0,
                       "reused_builds": 0, "builds": 0, "active_rows": 0,
                       "source_seq": 0, "last_decoded_rows": 0}

    def _app_lock(self):
        return getattr(self.inst.app, "lock", None) or nullcontext()

    def _metadata(self, conn, *, split_versions=False, torch=None):
        inst, ctx = self.inst, self.inst.ctx
        dbstat = _stat(ctx.startrack_db)
        identity = (id(inst), str(ctx.root.resolve()), ctx.instance_id, ctx.tz,
                    dbstat[:2] if dbstat else None)
        cursor = import_cursor(conn)
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        # All formal track tables are append-only. max(rowid) is a bounded
        # metadata read and catches acknowledgements/settings with text PKs too.
        marks = [(name, conn.execute('SELECT coalesce(max(rowid),0) FROM "' +
                                    name.replace('"', '""') + '"').fetchone()[0]) for name in tables]
        root = ctx.root
        paths = [root / "instance.json", root / "profile.jsonl",
                 root / "startrack/card_setup.jsonl", root / "startrack/device_events.jsonl",
                 root / "startorch/sources.json", root / "startorch/patient_rules.jsonl",
                 root / "cluster/phone_sessions.jsonl",
                 root / "cluster/report_phone_events.jsonl", root / "cluster/gene_reads.jsonl",
                 ctx.exchange_dir]
        # Version hints retain dev/inode/size/mtime/ctime; this method does not
        # open file contents. Projection inputs are separately captured by
        # read_bundle, including on cache hits; that capture cost remains.
        cluster = root / "cluster/cluster.db"
        paths.extend([cluster, Path(str(cluster) + "-wal")])
        def torch_mark(connection):
            return connection.execute(
                "SELECT (SELECT coalesce(max(commit_id),0) FROM h1_commit),"
                "(SELECT coalesce(max(id),0) FROM h1_export_log)").fetchone()
        if torch is None:
            with read_connection(open_startorch, ctx) as owned:
                highwater = torch_mark(owned)
        else:
            highwater = torch_mark(torch)
        torch_identity = _stat(ctx.startorch_db)
        store_mark = (torch_identity[:2] if torch_identity else None, highwater)
        files = [(str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                  _stat(path))
                 for path in paths]
        registry = inst.app.registry.current
        public = {"spec": inst.spec, "last_sync": inst.last_sync,
                  "context": [ctx.display_name, ctx.kind, ctx.accept],
                  "dictionary": [registry.version, id(registry)],
                  "rulepack": inst.app.rulepack, "dynamic": inst.app.dynamic,
                  "product": getattr(inst.app, "product_config", None),
                  "model_name": getattr(getattr(inst.app, "llm", None), "model_name", ""),
                  "sjia": inst.sjia, "nature": inst.nature}
        version = _digest([identity, cursor, marks, store_mark, files, public])
        if split_versions:
            # The public token retains its existing full dependency set. Only
            # the private home template excludes the volatile sync status.
            content = dict(public)
            content.pop("last_sync")
            return identity, cursor[1], (version, _digest([identity, cursor, marks, store_mark, files, content]))
        return identity, cursor[1], version

    def version(self):
        """Metadata-only change token. It conveys no authorization."""
        with self._app_lock(), self._lock, read_connection(open_startrack, self.inst.ctx) as conn:
            return self._metadata(conn)[2]

    def _load(self, conn, identity, source_seq):
        old = _cached(self._key)
        cold = old is None or old.identity != identity or old.source_seq > source_seq
        if not cold and old.source_seq == source_seq:
            self._stats["last_decoded_rows"] = 0
            return old
        if cold:
            view = _View(self.inst.ctx.tz, identity, source_seq)
            rows = conn.execute(
                "SELECT h.observation_id,h.revision,h.status,h.payload FROM h1_inbox h "
                "WHERE h.source_seq<=? AND NOT EXISTS (SELECT 1 FROM h1_inbox n "
                "WHERE n.observation_id=h.observation_id AND n.revision>h.revision AND n.source_seq<=?) "
                "ORDER BY h.source_seq", (source_seq, source_seq))
            self._stats["full_loads"] += 1
        else:
            # Copy only mappings, not payloads or parsed Obs objects: an already
            # returned view keeps its own version during concurrent appends.
            view = _View(old.tz, identity, source_seq, dict(old.payloads), dict(old.revisions),
                         dict(old.objects), dict(old.sizes),
                         activation_index=ActivationIndex(old.activation_index))
            rows = conn.execute(
                "SELECT observation_id,revision,status,payload FROM h1_inbox "
                "WHERE source_seq>? AND source_seq<=? ORDER BY source_seq", (old.source_seq, source_seq))
            self._stats["incremental_loads"] += 1
        decoded = 0
        clock = PresentationClock(datetime.now(timezone.utc), view.tz)
        if view.activation_index.at is None:
            view.activation_index.at = clock.now
        for oid, revision, status, raw in rows:
            if revision <= view.revisions.get(oid, -1):
                continue
            payload = strict_loads(raw)
            decoded += 1
            if payload["observation_id"] != oid or payload["revision"] != revision or payload["status"] != status:
                raise H1Error("BACKGROUND_READ_INCONSISTENT", "读取版本与正式记录不一致")
            view.revisions[oid] = revision
            if status != "ACTIVE":
                view.payloads.pop(oid, None)
                view.objects.pop(oid, None)
                view.sizes.pop(oid, None)
                view.activation_index.update(oid, None)
                continue
            view.payloads[oid] = payload
            obs = view.objects[oid] = _obs(payload, view.tz)
            view.activation_index.update(oid, obs.instant if obs.instant is not None
                                         else clock.activation(payload["temporal"]))
            view.sizes[oid] = len(raw.encode("utf-8"))
        self._stats.update(active_rows=len(view.payloads), source_seq=source_seq, last_decoded_rows=decoded)
        self._stats["decoded_rows"] += decoded
        return view

    def read(self):
        """Complete current observation view, suitable for existing rules."""
        with self._app_lock(), self._lock, read_connection(open_startrack, self.inst.ctx) as conn:
            identity, source_seq, _ = self._metadata(conn)
            view = self._load(conn, identity, source_seq)
            _remember(self._key, view)
            return view

    def _fits_sync_cache(self, conn, identity, source_seq):
        """Preflight individual capacity without decoding or building Obs objects.

        Withdrawn identifiers still occupy revisions. Payload bytes count only
        the latest ACTIVE revision, exactly as _load/_remember do. Total/LRU
        budgets deliberately do not select a fallback: that is a separate policy.
        """
        capacity_key = (identity, source_seq, MAX_INSTANCE_ROWS, MAX_INSTANCE_PAYLOAD_BYTES)
        if getattr(self, '_sync_capacity_fit', None) == capacity_key:
            # Eviction removes a view, not the capacity of this exact committed
            # version. This contains no observations or authorization result.
            return True
        # An exact positive fact cannot authorize a newer cursor. A small
        # aggregate may be advanced using committed revision metadata below;
        # it holds no observation payloads or authorization results.
        aggregate = getattr(self, '_sync_capacity_aggregate', None)
        self._sync_capacity_fit = None
        self._sync_capacity_aggregate = None
        overflow = getattr(self, '_sync_row_overflow', None)
        if overflow is not None:
            previous_identity, previous_seq, previous_limit = overflow
            if identity != previous_identity or source_seq < previous_seq:
                self._sync_row_overflow = None
            elif previous_limit == MAX_INSTANCE_ROWS:
                # h1_inbox is append-only: even withdrawn identifiers remain.
                # Further commits cannot make an already oversize identifier
                # set fit. This is a capacity fact, not a retained data view.
                return False
        old = _cached(self._key)
        if old is not None and old.identity == identity and old.source_seq <= source_seq:
            count, size = len(old.revisions), old.payload_bytes
            if old.source_seq != source_seq:
                latest = {}
                for oid, rev, status, nbytes in conn.execute(
                        "SELECT observation_id,revision,status,length(CAST(payload AS BLOB)) "
                        "FROM h1_inbox WHERE source_seq>? AND source_seq<=? ORDER BY source_seq",
                        (old.source_seq, source_seq)):
                    previous = latest.get(oid)
                    if rev > (previous[0] if previous else old.revisions.get(oid, -1)):
                        latest[oid] = (rev, nbytes if status == 'ACTIVE' else 0)
                for oid, (_, nbytes) in latest.items():
                    count += int(oid not in old.revisions)
                    size += nbytes - old.sizes.get(oid, 0)
        elif (aggregate is not None and aggregate[0][0] == identity and
              aggregate[0][2:] == capacity_key[2:] and aggregate[0][1] < source_seq):
            previous_seq = aggregate[0][1]
            count, size = aggregate[1:]
            latest = {}
            for oid, rev, status, nbytes in conn.execute(
                    "SELECT observation_id,revision,status,length(CAST(payload AS BLOB)) "
                    "FROM h1_inbox WHERE source_seq>? AND source_seq<=? ORDER BY source_seq",
                    (previous_seq, source_seq)):
                previous = latest.get(oid)
                if previous is None or rev > previous[0]:
                    latest[oid] = (rev, nbytes if status == 'ACTIVE' else 0)
            for oid, (rev, nbytes) in latest.items():
                # The existing (observation_id, revision) PK bounds this lookup
                # to one affected identifier. Withdrawn identifiers still count;
                # only their latest ACTIVE payload contributes bytes.
                previous = conn.execute(
                    "SELECT revision,status,length(CAST(payload AS BLOB)) FROM h1_inbox "
                    "WHERE observation_id=? AND source_seq<=? ORDER BY revision DESC LIMIT 1",
                    (oid, previous_seq)).fetchone()
                if previous is None:
                    count += 1
                    size += nbytes
                elif rev > previous[0]:
                    size += nbytes - (previous[2] if previous[1] == 'ACTIVE' else 0)
        else:
            # Stop once the row budget is exceeded; avoid an expensive payload
            # query in the common oversize case. The cursor bounds partial H1
            # imports to the successfully committed prefix.
            count = conn.execute(
                "SELECT count(*) FROM (SELECT observation_id FROM h1_inbox "
                "WHERE source_seq<=? GROUP BY observation_id LIMIT ?)",
                (source_seq, MAX_INSTANCE_ROWS + 1)).fetchone()[0]
            if count > MAX_INSTANCE_ROWS:
                self._sync_row_overflow = (identity, source_seq, MAX_INSTANCE_ROWS)
                return False
            size = conn.execute(
                "SELECT coalesce(sum(length(CAST(h.payload AS BLOB))),0) FROM h1_inbox h "
                "WHERE h.source_seq<=? AND h.status='ACTIVE' AND NOT EXISTS "
                "(SELECT 1 FROM h1_inbox n WHERE n.observation_id=h.observation_id "
                "AND n.revision>h.revision AND n.source_seq<=?)",
                (source_seq, source_seq)).fetchone()[0]
        if count > MAX_INSTANCE_ROWS:
            self._sync_row_overflow = (identity, source_seq, MAX_INSTANCE_ROWS)
            return False
        fits = size <= MAX_INSTANCE_PAYLOAD_BYTES
        if fits:
            self._sync_capacity_fit = capacity_key
            self._sync_capacity_aggregate = (capacity_key, count, size)
        return fits

    def read_for_sync(self, fallback):
        """Use the incremental input only when this view can be retained.

        The caller owns the original uncached reader. No exception is converted
        to a capacity miss; failures still take the existing recovery path.
        """
        with self._app_lock(), self._lock, read_connection(open_startrack, self.inst.ctx) as conn:
            identity, source_seq, _ = self._metadata(conn)
            if not self._fits_sync_cache(conn, identity, source_seq):
                # Match _remember for an oversize replacement, without first
                # allocating that disposable replacement. Other entries stay put.
                with _LOCK:
                    _CACHE.pop(self._key, None)
                    _schedule_locked()
                return fallback()
            view = self._load(conn, identity, source_seq)
            _remember(self._key, view)
            return view

    def snapshot(self, builder, *, now=None, scoped=False):
        """Build only on changes; refresh time-dependent flags on every read."""
        now = now or datetime.now(timezone.utc)
        local_today(now, self.inst.ctx.tz)
        from read_bundle import capture
        with self._app_lock(), capture(self.inst, self) as bundle, self._lock:
            identity, source_seq, (version, content_version) = bundle.metadata
            view = self._load(bundle.track, identity, source_seq)
            clock_changed = (view.projection_at is not None and now < view.projection_at or
                             view.activates_at is not None and now >= view.activates_at)
            if view.projection is None or view.version != content_version or clock_changed:
                # Publishing follows successful construction only. A failed
                # builder never makes a new version appear authoritative.
                built = builder(view, bundle) if scoped else builder(view)
                if not isinstance(built, dict):
                    raise TypeError("homepage builder must return a dictionary")
                view.projection = deepcopy(dict(built) if scoped else built)
                view.version = content_version
                view.projection_at = now
                view.activates_at = view.activation_index.next(now)
                self._stats["builds"] += 1
            else:
                self._stats["reused_builds"] += 1
            _remember(self._key, view)
            result = deepcopy(view.projection)
            # Same app lock as the captured version; never mutate the cached
            # template or share nested status objects with the caller.
            if isinstance(result.get("h1"), dict) and "last_sync" in result["h1"]:
                result["h1"]["last_sync"] = deepcopy(self.inst.last_sync)
            result.update(_scope="home", _read_version=version)
            _freshen(result, now, view.tz)
            if scoped:
                from read_bundle import Snapshot
                result = Snapshot(result).bind(bundle)
            return result

    def stats(self):
        with self._lock:
            out = dict(self._stats)
            cached = _cached(self._key)
            out["cached"] = cached is not None
            out["payload_bytes"] = cached.payload_bytes if cached else 0
            return out
