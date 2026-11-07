"""Offline-capable evidence accounting; never starts or resumes a deletion.

No route is registered here. The local P2 provider owns confirmation and the
execute entry. This adapter only consumes committed, immutable Oura tombstones.
"""
from contextlib import closing
import json

import evidence_ledger as ledger
import oura_raw as raw
from h1_common import H1Error


def _completed(root, instance_id):
    after = 0
    through = None
    while True:
        c = raw.read_raw(root)
        if c is None:
            return
        with closing(c):
            c.execute('BEGIN')
            if through is None:
                through = c.execute('SELECT coalesce(max(rowid),0) FROM erasure').fetchone()[0]
            row = c.execute('SELECT e.rowid,e.erasure_id,e.request_id,e.scope,e.preview_digest,e.started_at,'
                         'd.ended_at,d.bodies_deleted,d.bytes_freed,d.status '
                         'FROM erasure e JOIN erasure_end d USING(erasure_id) '
                         'WHERE e.rowid>? AND e.rowid<=? ORDER BY e.rowid LIMIT 1', (after,through)).fetchone()
        if row is None:
            return
        after, eid, request, encoded, preview, started, ended, files, size, status = row
        scope = json.loads(encoded)
        if status != 'COMPLETE':
            continue
        if (scope.get('instance_id') != instance_id or ledger.digest(scope) != preview or
                files != len(scope['bodies']) or size != sum(x[1] for x in scope['bodies'])):
            raise H1Error('EVIDENCE_TOMBSTONE_INVALID', '')
        end = dict(erasure_id=eid, ended_at=ended, bodies_deleted=files,
                   bytes_freed=size, status=status)
        counts = dict(files=files, registered_bytes=size, sources=[
            dict(files=s['bodies_deleted'], registered_bytes=s['bytes_freed'],
                 missing=s['missing_count']) for s in scope['sources']])
        if scope.get('archives'):
            counts['archives'] = dict(files=len(scope['archives']),
                                     registered_bytes=sum(x['bytes'] for x in scope['archives']))
        yield dict(erasure_id=eid, request_id=request, preview_digest=preview,
                   started_at=started,
                   tombstone_digest=ledger.digest(dict(scope=scope, result=end)),
                   counts=counts,
                   occurred_at=ended)


def reconcile(root, instance_id, *, repair=False):
    """Pure read by default. Repair only missing events, never original actions.

    A durable confirmation must match instance/request/preview exactly. Legacy
    COMPLETE records are counted without inventing SELF. No implicit projection.
    """
    ledger._instance(instance_id)
    report = dict(completed=0, with_event=0, missing_event=0,
                  missing_without_confirmation=0, repaired=0)
    # Immutable rows remain valid after their read snapshot closes. One item
    # at a time bounds memory, while no raw transaction spans a ledger write.
    iterator = _completed(root, instance_id)
    try:
        for item in iterator:
            report['completed'] += 1
            eid = item['erasure_id']
            existing = ledger.get_event(root, instance_id, eid)
            if existing:
                expected = dict(tombstone=item['tombstone_digest'], preview_digest=item['preview_digest'])
                if existing['digests'] != expected or existing['counts'] != item['counts']:
                    raise H1Error('EVIDENCE_EVENT_CONFLICT', '')
                report['with_event'] += 1
                continue
            started = item.pop('started_at')
            proof = ledger.confirmation(root, instance_id, item['request_id'], item['preview_digest'], before=started)
            if not proof:
                report['missing_without_confirmation'] += 1
                report['missing_event'] += 1
            elif repair:
                ledger.append_completed(root, instance_id=instance_id, **item)
                report['with_event'] += 1
                report['repaired'] += 1
            else:
                report['missing_event'] += 1
    finally:
        iterator.close()
    return report


def policy_check(root):
    """Read-only path inventory; unknown stores fail visibly, never auto-delete.

    Only managed Oura/evidence areas are enumerated. Other formal/personal
    stores and external backups remain outside this scanner's authority.
    """
    from pathlib import Path
    from fnmatch import fnmatchcase
    from sqlite_util import assert_inside
    policy = json.loads((Path(__file__).with_name('erasure_policy.json')).read_text())
    rules = policy['stores']
    matched, unknown = [], []
    for area in ('startorch/oura_raw','startorch/evidence'):
        directory = Path(root)/area
        assert_inside(root,directory)
        if not directory.exists():
            continue
        for path in sorted(directory.rglob('*')):
            assert_inside(root,path)
            if path.is_dir():
                continue
            relative = path.relative_to(root).as_posix()
            actions = {r['action'] for r in rules if fnmatchcase(relative,r['path'])}
            if not actions:
                unknown.append(relative)
            else:
                matched.append(dict(path=relative,actions=sorted(actions)))
    return dict(schema=policy['schema'],managed_areas_only=True,
                outside_control=['system_or_external_backups'],matched=matched,
                unregistered=unknown,ok=not unknown)
