"""Display-only retirement of old stream observations; no ledger mutations."""
from datetime import datetime
from types import SimpleNamespace


def display_read(read, policy):
    if not policy:
        return read
    allowed = {'DEVICE_SOMALOOP'}
    cutoffs = {}
    for source, cutoff in policy.items():
        if source not in allowed:
            raise ValueError('DISPLAY_RETENTION_SOURCE_INVALID')
        moment = datetime.fromisoformat(cutoff)
        if moment.tzinfo is None:
            raise ValueError('DISPLAY_RETENTION_TIME_INVALID')
        cutoffs[source] = moment
    def visible(p):
        cutoff = cutoffs.get(p.get('source_kind'))
        t = p.get('temporal', {})
        if cutoff is None or t.get('role') != 'INSTANT':
            return True
        moment = datetime.fromisoformat(t['observed_at'].replace('Z', '+00:00'))
        return moment >= cutoff
    payloads = {oid: p for oid, p in read.payloads.items() if visible(p)}
    from cards import _obs
    return SimpleNamespace(payloads=payloads, observations=[_obs(payloads[oid], read.tz) for oid in sorted(payloads)], tz=read.tz)
