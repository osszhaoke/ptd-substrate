"""Committed device-check input without populating the historical read cache.

This is an internal projection for device_watch.check, not a vitals response.
SQLite still scans latest revisions; Python retains only one timestamp per
registered metric. Values, series and Obs objects are never decoded or cached.
"""
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic

from cards import open_startrack
from h1_common import H1Error, InstanceContext
from startrack_import import import_cursor
from time_freshness import PresentationClock
from vitals import _when_in_zone as _when


_PERIODIC_CHUNK_ROWS = 256
_PERIODIC_CHUNK_SECONDS = 0.050


def _rows(conn, query, seq, periodic):
    if not periodic:
        yield from conn.execute(query, (seq, seq))
        return
    last = None
    while True:
        page_query = query
        params = [seq, seq]
        if last is not None:
            page_query += " AND h.observation_id>?"
            params.append(last)
        page_query += " ORDER BY h.observation_id LIMIT ?"
        params.append(_PERIODIC_CHUNK_ROWS)
        # Include execute in the soft deadline. Always consume at least one
        # row before checking it, so a slow execute cannot prevent progress.
        # Close the statement before Python time conversion or yielding rows.
        started = monotonic()
        page = []
        with closing(conn.execute(page_query, params)) as cursor:
            for _ in range(_PERIODIC_CHUNK_ROWS):
                row = cursor.fetchone()
                if row is None:
                    break
                page.append(row)
                if monotonic() - started >= _PERIODIC_CHUNK_SECONDS:
                    break
        if not page:
            return
        last = page[-1][0]  # Advance even when all rows are retracted/unknown.
        yield from page


@dataclass(frozen=True)
class WatchSnapshot:
    """One read's committed prefix, not a retained cache or notification state."""
    owner: object
    ctx: InstanceContext
    database_identity: tuple
    cursor: tuple
    families: tuple
    dictionary_version: str
    now: datetime
    zone: object


def _database_identity(ctx):
    stat = ctx.startrack_db.stat()
    return stat.st_dev, stat.st_ino


def capture(inst):
    """Caller holds app.lock. Close this connection before doing unlocked work."""
    ctx = inst.ctx
    dictionary = inst.app.registry.current
    clock = PresentationClock(datetime.fromisoformat(inst.now()), ctx.tz)
    with closing(open_startrack(ctx)) as conn:
        return WatchSnapshot(inst, ctx, _database_identity(ctx), import_cursor(conn),
                             tuple((code, item.family) for code, item in dictionary.codes.items()),
                             dictionary.version, clock.now, clock.zone)


def read(inst, snapshot=None):
    """Without snapshot, caller owns app.lock (the existing manual/API path).

    A periodic caller captures under the lock, then reads the immutable prefix
    outside it. Never reacquire app.lock while this SQLite connection is open.
    The checker still reads its settings/clock after this function returns.

    Latest revision is chosen within the committed prefix BEFORE checking its
    status. Time selection and ties exactly follow vitals_state per code; the
    unchanged checker subsequently combines codes by dictionary family.
    """
    if snapshot is None:
        ctx = inst.ctx
        families = {code: item.family for code, item in inst.app.registry.current.codes.items()}
        clock = PresentationClock(datetime.fromisoformat(inst.now()), ctx.tz)
        now, zone = clock.now, clock.zone
    else:
        ctx = snapshot.ctx
        if (snapshot.owner is not inst or ctx.root != inst.ctx.root or ctx.instance_id != inst.ctx.instance_id
                or _database_identity(ctx) != snapshot.database_identity):
            raise H1Error("BACKGROUND_READ_INCONSISTENT", "巡检读取实例已变化")
        families = dict(snapshot.families)
        now, zone = snapshot.now, snapshot.zone
    today = now.astimezone(zone).date().isoformat()
    latest = {}
    with closing(open_startrack(ctx)) as conn:
        seq = import_cursor(conn)[1] if snapshot is None else snapshot.cursor[1]
        query = (
            "SELECT h.observation_id,h.revision,h.status,"
            "json_extract(h.payload,'$.observation_id'),"
            "json_extract(h.payload,'$.revision'),json_extract(h.payload,'$.status'),"
            "json_extract(h.payload,'$.code'),json_extract(h.payload,'$.temporal.role'),"
            "json_extract(h.payload,'$.temporal.observed_at'),"
            "json_extract(h.payload,'$.temporal.observed_date') "
            "FROM h1_inbox h WHERE h.source_seq<=? AND NOT EXISTS "
            "(SELECT 1 FROM h1_inbox n WHERE n.observation_id=h.observation_id "
            "AND n.revision>h.revision AND n.source_seq<=?)")
        rows = _rows(conn, query, seq, snapshot is not None)
        for oid, rev, status, pid, prev, pstatus, code, role, at, day in rows:
            if (oid, rev, status) != (pid, prev, pstatus):
                raise H1Error("BACKGROUND_READ_INCONSISTENT", "读取版本与正式记录不一致")
            if status != "ACTIVE" or code not in families:
                continue
            instant, day = _when({"temporal": {
                "role": role, "observed_at": at, "observed_date": day}}, zone)
            if (instant > now if instant is not None else day is not None and day > today):
                continue
            key = (instant.astimezone(timezone.utc).isoformat() if instant else (day or ""), oid)
            if code not in latest or key > latest[code][0]:
                latest[code] = (key, instant.isoformat() if instant else None, day)
    if snapshot is not None and _database_identity(ctx) != snapshot.database_identity:
        raise H1Error("BACKGROUND_READ_INCONSISTENT", "巡检读取实例已变化")
    # Keep UNKNOWN presence and all registered families, irrespective of display
    # retention, card bindings or acquisition source_kind. check owns those rules.
    return {"items": [{"family": families[code],
                       "observed_at": latest[code][1], "observed_date": latest[code][2]}
                      for code in sorted(latest, key=lambda c: (families[c], c))]}
