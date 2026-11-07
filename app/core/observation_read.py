"""One request's read-only observation view; never cached across requests.

Latest revision and insertion order follow the existing readers exactly. The
sorted observation view is shared only by consumers which already used that
order. No stored history, source fields or rule outputs are changed.
"""
from h1_common import strict_loads


class ObservationRead:
    def __init__(self, conn, tz):
        self.tz = tz
        newest = {}
        for oid, rev, payload in conn.execute("SELECT observation_id, revision, payload FROM h1_inbox"):
            if oid not in newest or rev > newest[oid][0]:
                newest[oid] = (rev, payload)
        self.payloads = {}
        # Retain first-seen order and revision/tie selection, but release each
        # encoded payload as it is decoded instead of keeping two full copies.
        for oid in list(newest):
            _, raw = newest.pop(oid)
            payload = strict_loads(raw)
            if payload["status"] == "ACTIVE":
                self.payloads[oid] = payload
        self._observations = None

    @property
    def observations(self):
        if self._observations is None:
            from cards import _obs
            self._observations = [_obs(self.payloads[oid], self.tz) for oid in sorted(self.payloads)]
        return self._observations
