"""Instance-local presentation time; never changes admitted records or history."""
from datetime import datetime, time, timedelta
import heapq

from h1_common import check_tz, parse_date, parse_instant


class PresentationClock:
    """Validate the zone and aware clock once for a complete projection."""

    def __init__(self, now, tz):
        self.zone = check_tz(tz)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('presentation clock must be timezone-aware')
        self.now = now
        self.today = now.astimezone(self.zone).date()

    def activation(self, temporal):
        if temporal.get('role') == 'INSTANT':
            return parse_instant(temporal['observed_at'])
        if temporal.get('role') == 'DAY':
            return datetime.combine(parse_date(temporal['observed_date']), time(), self.zone)
        return None

    def fresh(self, window, instant=None, day=None):
        if window is None:
            return None
        if instant is not None:
            return timedelta(0) <= self.now - instant <= window
        if day is not None:
            return 0 <= (self.today - parse_date(day)).days <= max(1, window.days)
        return False


class ActivationIndex:
    """Parsed row times plus a bounded future heap; rollback never reparses rows.

    Each update replaces one identifier. Stale heap entries are lazy-removed,
    with compaction bounded by the number of active timed observations.
    """

    def __init__(self, previous=None):
        self.times = dict(previous.times) if previous else {}
        self.heap = list(previous.heap) if previous else []
        self.at = previous.at if previous else None

    def update(self, oid, at):
        if at is None:
            self.times.pop(oid, None)
        else:
            self.times[oid] = at
            if self.at is None or at > self.at:
                heapq.heappush(self.heap, (at, oid))
        if len(self.heap) > max(32, 2 * len(self.times)):
            self._rebuild()

    def _rebuild(self):
        self.heap = [(at, oid) for oid, at in self.times.items()
                     if self.at is None or at > self.at]
        heapq.heapify(self.heap)

    def next(self, now):
        if self.at is not None and now < self.at:
            self.at = now
            self._rebuild()
        self.at = now
        while self.heap:
            at, oid = self.heap[0]
            if at > now and self.times.get(oid) == at:
                return at
            heapq.heappop(self.heap)
        return None


def local_today(now, tz):
    return PresentationClock(now, tz).today


def activation(temporal, tz):
    # Preserve the standalone helper's unknown/instant behavior.
    if temporal.get('role') == 'INSTANT':
        return parse_instant(temporal['observed_at'])
    if temporal.get('role') == 'DAY':
        return datetime.combine(parse_date(temporal['observed_date']), time(), check_tz(tz))
    return None


def eligible(temporal, now, tz):
    clock = PresentationClock(now, tz)
    at = clock.activation(temporal)
    return at is None or at <= now


def fresh(*, now, tz, window, instant=None, day=None):
    return PresentationClock(now, tz).fresh(window, instant, day)


def next_activation(payloads, now, tz):
    """Standalone compatibility helper; cached views use their decoded index."""
    clock = PresentationClock(now, tz)
    future = (clock.activation(p['temporal']) for p in payloads)
    return min((at for at in future if at is not None and at > now), default=None)
