"""Local Oura UI boundary and provider; no task/agent or general SQL eraser.

U owns preview/claim/intent/deletion. Short A checks pin the selected instance.
No filesystem work holds A; response delivery is outside both locks.
"""
from contextlib import closing
import json
import os
import re
import sqlite3
import uuid

import erasure_confirmation as confirmation
import erasure_service as service
import evidence_ledger as ledger
import oura
import oura_erase as erase
import oura_raw as raw
from h1_common import H1Error
from instance_services import SourceReader, oura_disconnect
from source_registry import SourceRegistry

PREFIX = '/api/oura/raw/erase/'


def _fail(code):
    raise H1Error(code, '')


def _options(include_archives, revoke):
    if type(include_archives) is not bool or type(revoke) is not bool:
        _fail('OURA_ERASE_BODY_INVALID')


class _Sources(SourceRegistry):
    """Compatibility name for the shared source-registration writer."""


def _client(inst):
    return oura.client_for(inst.app, inst.ctx.instance_id)


def _revoke_available(inst):
    try:
        return bool(_client(inst).connected())
    except Exception:  # noqa: BLE001 - an unreadable store never offers revocation
        return False


def _revoke(inst):
    """Remote first, then the existing local disconnect. Any failure deletes nothing."""
    client = _client(inst)
    if not client.connected():
        _fail('ERASURE_REMOTE_REVOKE_UNAVAILABLE')
    try:
        client.revoke_remote()  # Network under U only; global A is not held.
    except (H1Error, OSError, ValueError):
        _fail('ERASURE_REMOTE_REVOKE_FAILED')
    oura_disconnect(inst.app, inst, _client, _Sources)  # U -> binding gate -> A.


def _binding(inst, scope_digest, request_id, include_archives, revoke, session):
    return confirmation.Binding(inst.ctx.instance_id, 'oura', scope_digest, scope_digest,
                                request_id, include_archives, revoke, session)


def _scope(inst, include_archives, revoke):
    scope, _ = erase._snapshot(inst)
    archives = erase._archive_inventory(inst.ctx.root)
    scope.update(archives=archives if include_archives else [],
                 options=dict(include_archives=include_archives, revoke=revoke))
    return scope, ledger.digest(scope), archives


def _row(inst, *, request_id=None, erasure_id=None):
    c = raw.read_raw(inst.ctx.root)
    if c is None:
        return None
    with closing(c):
        if request_id is not None:
            row = c.execute('SELECT erasure_id,request_id,scope,preview_digest,started_at '
                            'FROM erasure WHERE request_id=?', (request_id,)).fetchone()
        else:
            row = c.execute('SELECT erasure_id,request_id,scope,preview_digest,started_at '
                            'FROM erasure WHERE erasure_id=?', (erasure_id,)).fetchone()
        if row is None:
            return None
        end = c.execute('SELECT * FROM erasure_end WHERE erasure_id=?', (row[0],)).fetchone()
    return dict(erasure_id=row[0],request_id=row[1],scope=json.loads(row[2]),
                preview_digest=row[3],started_at=row[4],end=erase._result(end) if end else None)


def _proof(inst, row):
    if (row['scope'].get('instance_id') != inst.ctx.instance_id or
            ledger.digest(row['scope']) != row['preview_digest'] or not ledger.confirmation(
                inst.ctx.root, inst.ctx.instance_id, row['request_id'],
                row['preview_digest'], before=row['started_at'])):
        _fail('ERASURE_ORIGINAL_CONFIRMATION_REQUIRED')


def _recoverable(inst, erasure_id):
    try:
        _proof(inst, _row(inst,erasure_id=erasure_id))
        return True
    except (H1Error,OSError,sqlite3.Error):
        return False


def _identity(inst):
    app = inst.app
    with app.lock:
        if app.inst(inst.spec['key']) is not inst:
            _fail('ERASURE_INSTANCE_CHANGED')
        import input_guard
        input_guard.require_writable(inst)


class OuraProvider:
    provider_id = 'oura'

    def preview(self, inst, *, session, include_archives=False, revoke=False):
        _options(include_archives, revoke)
        with erase._held(inst):
            _identity(inst)
            erase._ensure_upgraded(inst.ctx.root)
            pending = erase._pending(inst.ctx.root)
            if pending:
                eid, encoded, started = pending[0]
                return dict(pending_erasure=dict(erasure_id=eid,started_at=started,
                            files=len(json.loads(encoded)['bodies']),resumable=_recoverable(inst,eid)))
            available = _revoke_available(inst)
            if revoke and not available:
                _fail('ERASURE_REMOTE_REVOKE_UNAVAILABLE')
            scope, digest, archives = _scope(inst, include_archives, revoke)
            request = str(uuid.uuid4())
            token = confirmation.owner(inst.app)[1].issue(_binding(
                inst,digest,request,include_archives,revoke,session))
            return dict(request_id=request,preview_digest=digest,confirmation_token=token,
                        files=len(scope['bodies']),bytes=sum(x[1] for x in scope['bodies']),
                        date_from=scope['date_from'],date_to=scope['date_to'],
                        missing_sources=sum(bool(s['missing_count'] or s.get('index_unreadable'))
                                            for s in scope['sources']),
                        archives=dict(backups=sum('backup-' in x['name'] and not x['name'].endswith(
                            ('-wal','-shm','-journal')) for x in archives),
                            quarantines=sum('quarantine-' in x['name'] and not x['name'].endswith(
                            ('-wal','-shm','-journal')) for x in archives),bytes=sum(x['bytes'] for x in archives)),
                        include_archives=include_archives,revoke=revoke,revoke_available=available)

    def execute(self, inst, *, session, request_id, preview_digest, include_archives,
                revoke, confirmation_token, checked, word):
        _options(include_archives, revoke)
        binding = _binding(inst,preview_digest,request_id,include_archives,revoke,session)
        with erase._held(inst):
            _identity(inst)
            # Duplicate execute never bypasses the one-shot claim. Query/resume
            # are separate operations on the original immutable request.
            proof = confirmation.owner(inst.app)[1].claim(
                confirmation_token,binding,checked=checked,word=word)
            scope, digest, _ = _scope(inst,include_archives,revoke)
            if digest != preview_digest:
                _fail('OURA_ERASE_PREVIEW_CHANGED')
            if revoke:
                _revoke(inst)  # Before confirmation evidence and intent: a failure leaves nothing.
            ledger.record_confirmation(inst.ctx.root,inst.ctx.instance_id,request_id,digest,proof)
            erase._execute_scope(inst,scope,digest,request_id)
            return self._receipt(inst,_row(inst,request_id=request_id),repair=True)

    def resume(self, inst, erasure_id):
        ledger._identifier(erasure_id,'[0-9a-f]{32}')
        with erase._held(inst):
            _identity(inst)
            row = _row(inst,erasure_id=erasure_id)
            if row is None:
                _fail('OURA_ERASE_NOT_FOUND')
            _proof(inst,row)
            if row['end'] is None:
                erase._complete(inst.ctx.root,erasure_id,row['scope'])
            return self._receipt(inst,_row(inst,erasure_id=erasure_id),repair=True)

    def status(self, inst, request_id):
        """Pure query: never initializes, deletes, repairs, or replays authority."""
        ledger._uuid(request_id)
        row = _row(inst,request_id=request_id)
        if row is None:
            return dict(status='NOT_STARTED',request_id=request_id)
        return self._receipt(inst,row,repair=False)

    def _receipt(self, inst, row, *, repair):
        if row['end'] is None:
            return dict(status='PENDING',erasure_id=row['erasure_id'])
        delayed = False
        if repair:
            try:
                service.reconcile(inst.ctx.root,inst.ctx.instance_id,repair=True)
                ledger.export_projection(inst.ctx.root)
            except (H1Error,OSError,sqlite3.Error):
                delayed = True  # Committed deletion is never falsely reported as undone.
        try:
            event = ledger.get_event(inst.ctx.root,inst.ctx.instance_id,row['erasure_id'])
        except (H1Error,OSError,sqlite3.Error):
            event, delayed = None, True
        return dict(row['end'],event_id=event['event_id'] if event else None,
                    evidence_pending=delayed or event is None,
                    archives_deleted=len(row['scope'].get('archives',[])),
                    revoked=bool(row['scope'].get('options',{}).get('revoke')),
                    missing_sources=sum(bool(s['missing_count'] or s.get('index_unreadable'))
                                        for s in row['scope']['sources']))

    def inspect(self, inst):
        pending = erase._pending(inst.ctx.root)
        result = dict(pending_erasure=({'erasure_id':pending[0][0],
                      'resumable':_recoverable(inst,pending[0][0])} if pending else None),
                      has_erased_sources=self.has_erased_sources(inst),receipt=None)
        c = raw.read_raw(inst.ctx.root)
        if c is not None and not pending:
            with closing(c):
                latest = c.execute('SELECT e.erasure_id FROM erasure e JOIN erasure_end d '
                                   'USING(erasure_id) ORDER BY e.rowid DESC LIMIT 1').fetchone()
            if latest and _recoverable(inst,latest[0]):
                result['receipt'] = self._receipt(inst,_row(inst,erasure_id=latest[0]),repair=False)
        elif c is not None:
            c.close()
        return result

    def source(self, inst, source_ref):
        # Only persisted daily-admission references prove the exact formal source.
        # Legacy OURA:<day/id> references have no exact link: never guess.
        match = re.fullmatch(r'DEVICE_DAY:([0-9a-f]{64})#[A-Za-z0-9_]+', source_ref or '')
        if not match:
            return dict(originals_erased=False,verified=False)
        c = raw.read_raw(inst.ctx.root)
        if c is None:
            return dict(originals_erased=False,verified=False)
        with closing(c):
            c.execute('BEGIN')
            erased,_ = raw.erased_through(c)
            rows = c.execute('SELECT f.body_sha256,f.rowid FROM admission a '
                             'LEFT JOIN record r ON r.collection=a.collection AND r.vendor_id=a.vendor_id '
                             'AND r.payload_sha256=a.payload_sha256 LEFT JOIN fetch f ON f.fetch_id=r.first_fetch_id '
                             'WHERE a.receipt_digest=?',(match[1],)).fetchall()
        return dict(originals_erased=bool(rows) and all(r[1] is not None and
                    r[1] <= erased.get(r[0],0) for r in rows),verified=bool(rows))

    def has_erased_sources(self, inst):
        """Bounded response: disclose only existence, never raw/vendor identifiers."""
        c = raw.read_raw(inst.ctx.root)
        if c is None:
            return False
        with closing(c):
            c.execute('BEGIN')
            erased,_ = raw.erased_through(c)
            rows = c.execute('SELECT f.body_sha256,f.rowid FROM admission a '
                             'JOIN record r ON r.collection=a.collection AND r.vendor_id=a.vendor_id '
                             'AND r.payload_sha256=a.payload_sha256 JOIN fetch f ON f.fetch_id=r.first_fetch_id')
            return any(r[1] <= erased.get(r[0],0) for r in rows)


PROVIDERS = {'oura': OuraProvider()}


def endpoint(handler, app, path):
    if not path.startswith(PREFIX):
        return False
    import input_guard
    import phone_tail
    if not phone_tail.local_control_allowed(handler) or not handler.headers.get('Origin'):
        handler._json(403,{'error':'LOCAL_CONTROL_REQUIRED'})
        return True
    try:
        size = int(handler.headers.get('Content-Length','0'))
        if not 0 < size <= 8192:
            _fail('OURA_ERASE_BODY_INVALID')
        body = input_guard.json_object(handler.rfile.read(size))
        action = path[len(PREFIX):]
        fields = {'preview':({'key'},{'key','include_archives','revoke'}),
                  'execute':({'key','request_id','preview_digest','include_archives','revoke',
                              'confirmation_token','checked','word'},),
                  'resume':({'key','erasure_id'},),'status':({'key','request_id'},),'cancel':({'key'},),'inspect':({'key'},),'source':({'key','source_ref'},)}
        if action not in fields:
            handler._json(404,{'error':'NOT_FOUND'})
            return True
        if set(body) not in fields[action] or not isinstance(body['key'],str):
            _fail('OURA_ERASE_BODY_INVALID')
        session, cookie = (None,None) if action == 'source' else confirmation.session(
            app,handler.headers,create=action in ('preview','inspect'))
        with app.lock:
            inst = app.inst(body['key'])
            input_guard.require_writable(inst)
        provider = PROVIDERS['oura']
        if action == 'inspect':
            result = provider.inspect(inst)
        elif action == 'source':
            if not isinstance(body['source_ref'],str) or len(body['source_ref'])>256:
                _fail('OURA_ERASE_BODY_INVALID')
            result = provider.source(inst,body['source_ref'])
        elif action == 'preview':
            result = provider.preview(inst,session=session,include_archives=body.get('include_archives',False),
                                      revoke=body.get('revoke',False))
        elif action == 'execute':
            result = provider.execute(inst,session=session,**{k:v for k,v in body.items() if k!='key'})
        elif action == 'resume':
            result = provider.resume(inst,body['erasure_id'])
        elif action == 'status':
            result = provider.status(inst,body['request_id'])
        else:
            confirmation.owner(app)[1].cancel_session(session)
            result = dict(ok=True)
        if cookie:
            handler._send(200,json.dumps(result,ensure_ascii=False).encode(),
                          'application/json; charset=utf-8',(('Set-Cookie',cookie),))
        else:
            handler._json(200,result)
    except H1Error as exc:
        handler._json(409,{'error':exc.code})
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):
        handler._json(400,{'error':'OURA_ERASE_FAILED'})
    return True
