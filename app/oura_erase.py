"""Entire-layer Oura erasure. No formal storage, UI, compute or global lock.

The immutable scope pins a fetch prefix and registered content hashes. A pending
intent is resumed under the same pull guard before any future pull.
"""
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import re
import stat
import uuid

import oura_raw as raw
import oura_sync
import oura_raw_upgrade as upgrade
from h1_common import H1Error
from sqlite_util import assert_inside, transaction


def _fail(code):
    raise H1Error(code, '')


def _guard(inst):
    # Compatibility for existing internal callers; ownership lives in sync.
    return oura_sync.pull_guard(inst)


@contextmanager
def _held(inst):
    guard = _guard(inst)
    if not guard.acquire(False):
        _fail('OURA_ERASE_PULL_RUNNING')
    try:
        with upgrade.ownership(inst.ctx.root, guard):
            yield
    finally:
        guard.release()


def _file_size(root, digest):
    path = raw._body_path(root, digest)
    assert_inside(root, path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
            _fail('OURA_ERASE_PATH_UNSAFE')
        return s.st_size
    finally:
        os.close(fd)


def _ensure_upgraded(root):
    # Empty preview stays read-only; only /1 invokes the approved write upgrade.
    path = Path(root) / 'startorch/oura_raw/raw.db'
    assert_inside(root, path)
    if path.exists():
        import oura_raw_recovery
        if oura_raw_recovery.members(root, path):
            with closing(raw.open_raw(root)): pass
        else:
            upgrade.prepare(root)


def _snapshot(inst):
    root = Path(inst.ctx.root)
    _ensure_upgraded(root)
    c = raw.read_raw(root)
    scope = {'kind':'ALL', 'instance_id':inst.ctx.instance_id, 'fetch_through':0, 'bodies':[], 'date_from':None, 'date_to':None, 'sources':[]}
    sources = upgrade.archived_sources(root)
    erased, archive_erased = {}, {}
    if c is not None:
        with closing(c):
            _, pending = raw.erasure_state(c)
            if pending: _fail('OURA_ERASE_PENDING')
            erased, archive_erased = raw.erased_through(c)
            scope['fetch_through'] = c.execute('SELECT coalesce(max(rowid),0) FROM fetch').fetchone()[0]
            first, last = c.execute('SELECT min(day),max(day) FROM record').fetchone()
            files = c.execute('SELECT body_sha256,max(rowid) FROM fetch WHERE body_sha256 IS NOT NULL GROUP BY body_sha256 ORDER BY body_sha256').fetchall()
            sources.insert(0, dict(name='raw.db', sha256=None, fetch_through=scope['fetch_through'], date_from=first, date_to=last, files=files))
    bodies = {}
    for source in sources:
        deleted, missing = [], []
        source_erased = source.pop('erased', {})
        for digest, latest in source.pop('files'):
            size = _file_size(root, digest)
            if size is None:
                boundary = (erased.get(digest, 0) if source['name'] == 'raw.db' else
                            max(source_erased.get(digest,0), archive_erased.get(((source['name'], source['sha256']), digest), 0)))
                if latest > boundary: missing.append(digest)
            else:
                bodies[digest] = size; deleted.append([digest, size])
        source.update(bodies=deleted, bodies_deleted=len(deleted), bytes_freed=sum(x[1] for x in deleted),
                      missing_hashes=missing, missing_count=len(missing))
        scope['sources'].append(source)
    scope['bodies'] = sorted(bodies.items())
    starts = [s['date_from'] for s in sources if s['date_from']]
    ends = [s['date_to'] for s in sources if s['date_to']]
    scope['date_from'] = min(starts) if starts else None
    scope['date_to'] = max(ends) if ends else None
    return scope, raw._sha(raw._json(scope))


def _pending(root):
    c = raw.read_raw(root)
    if c is None: return []
    with closing(c):
        return c.execute("SELECT e.erasure_id,e.scope,e.started_at FROM erasure e LEFT JOIN erasure_end d USING(erasure_id) WHERE d.erasure_id IS NULL ORDER BY e.rowid").fetchall()


def preview(inst):
    guard = _guard(inst)
    if not guard.acquire(False):
        return {'pull_running':True, 'preview_digest':None, 'files':None, 'bytes':None, 'date_from':None, 'date_to':None}
    try:
        with upgrade.ownership(inst.ctx.root, guard):
            _ensure_upgraded(inst.ctx.root)
            pending = _pending(inst.ctx.root)
            if pending:
                eid, encoded, started = pending[0]; scope = json.loads(encoded)
                return {'pending_erasure':{'erasure_id':eid, 'started_at':started,
                        'files':len(scope['bodies']), 'bytes':sum(x[1] for x in scope['bodies'])}}
            scope, digest = _snapshot(inst)
        return {'pull_running':False, 'preview_digest':digest, 'files':len(scope['bodies']),
                'bytes':sum(x[1] for x in scope['bodies']), 'date_from':scope['date_from'], 'date_to':scope['date_to']}
    finally:
        guard.release()


def _unlink(root, digest):
    """Open through a no-follow directory FD; missing registered files resume."""
    path = raw._body_path(root, digest)
    assert_inside(root, path)
    try:
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                _fail('OURA_ERASE_PATH_UNSAFE')
            current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (st.st_dev, st.st_ino) or not stat.S_ISREG(current.st_mode):
                _fail('OURA_ERASE_PATH_UNSAFE')
            os.unlink(path.name, dir_fd=directory)
            os.fsync(directory)
        finally:
            os.close(fd)
    finally:
        os.close(directory)


def _result(row):
    return dict(zip(('erasure_id','ended_at','bodies_deleted','bytes_freed','status'), row))


def execute(inst, preview_digest, request_id):
    # UUID-only identifier: callers cannot persist arbitrary messages/secrets.
    try:
        if str(uuid.UUID(request_id)) != request_id:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        _fail('OURA_ERASE_REQUEST_INVALID')
    if not isinstance(preview_digest, str) or not re.fullmatch('[0-9a-f]{64}', preview_digest):
        _fail('OURA_ERASE_DIGEST_INVALID')
    root = Path(inst.ctx.root)
    with _held(inst):
        _ensure_upgraded(root)
        existing = None
        c = raw.read_raw(root)
        if c is not None:
            with closing(c):
                existing = c.execute('SELECT erasure_id,scope,preview_digest FROM erasure WHERE request_id=?', (request_id,)).fetchone()
                if existing:
                    if existing[2] != preview_digest:
                        _fail('OURA_ERASE_REQUEST_CONFLICT')
                    end = c.execute('SELECT * FROM erasure_end WHERE erasure_id=?', (existing[0],)).fetchone()
                    if end:
                        return _result(end)
        if existing:
            erasure_id, encoded, _ = existing
            scope = json.loads(encoded)
        else:
            scope, digest = _snapshot(inst)
            if digest != preview_digest:
                _fail('OURA_ERASE_PREVIEW_CHANGED')
            erasure_id = uuid.uuid4().hex
            with closing(raw.open_raw(root)) as c:
                with transaction(c):
                    c.execute('INSERT INTO erasure VALUES (?,?,?,?,?)',
                              (erasure_id, request_id, raw._json(scope).decode(), raw._now(), preview_digest))
        return _complete(root, erasure_id, scope)


def _execute_scope(inst, scope, digest, request_id):
    upgrade.require_owner(inst.ctx.root)
    root = inst.ctx.root
    erasure_id = uuid.uuid4().hex
    with closing(raw.open_raw(root)) as c:
        with transaction(c):
            c.execute('INSERT INTO erasure VALUES (?,?,?,?,?)',
                      (erasure_id, request_id, raw._json(scope).decode(), raw._now(), digest))
    return _complete(root, erasure_id, scope)


def _archive_inventory(root):
    files = []
    for path in upgrade.archives(root):
        for suffix in ('', '-journal', '-wal', '-shm'):
            member = Path(str(path) + suffix)
            assert_inside(root, member)
            if member.exists():
                upgrade._safe(root, member)
                files.append(dict(name=member.name, sha256=upgrade.file_digest(root, member),
                                  bytes=member.stat().st_size))
    return files


def _unlink_archive(root, item):
    name = item['name']
    if (Path(name).name != name or not name.startswith(
            ('raw.db.v1-backup-', 'raw.db.v1-quarantine-', 'raw.db.v2-quarantine-'))):
        _fail('OURA_ERASE_PATH_UNSAFE')
    path = Path(root)/'startorch/oura_raw'/name
    assert_inside(root, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return
        try:
            import hashlib
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                _fail('OURA_ERASE_PATH_UNSAFE')
            h = hashlib.sha256()
            while chunk := os.read(fd, 1024*1024):
                h.update(chunk)
            if st.st_size != item['bytes'] or h.hexdigest() != item['sha256']:
                _fail('OURA_ERASE_PREVIEW_CHANGED')
            current = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (st.st_dev, st.st_ino):
                _fail('OURA_ERASE_PATH_UNSAFE')
            os.unlink(name, dir_fd=directory)
            os.fsync(directory)
        finally:
            os.close(fd)
    finally:
        os.close(directory)


def _complete(root, erasure_id, scope):
    # Intention is durable and no SQL transaction spans filesystem deletion.
    for digest, size in scope['bodies']:
        _unlink(root, digest)
    for item in scope.get('archives', []):
        _unlink_archive(root, item)
    row = (erasure_id, raw._now(), len(scope['bodies']), sum(x[1] for x in scope['bodies']), 'COMPLETE')
    with closing(raw.open_raw(root)) as c:
        with transaction(c):
            c.execute('INSERT INTO erasure_end VALUES (?,?,?,?,?)', row)
    return _result(row)


def resume(inst, erasure_id):
    if not isinstance(erasure_id, str) or not re.fullmatch('[0-9a-f]{32}', erasure_id):
        _fail('OURA_ERASE_ID_INVALID')
    root = Path(inst.ctx.root)
    with _held(inst):
        _ensure_upgraded(root)
        c = raw.read_raw(root)
        if c is None: _fail('OURA_ERASE_NOT_FOUND')
        with closing(c):
            row = c.execute('SELECT scope FROM erasure WHERE erasure_id=?', (erasure_id,)).fetchone()
            if row is None: _fail('OURA_ERASE_NOT_FOUND')
            if c.execute('SELECT 1 FROM erasure_end WHERE erasure_id=?', (erasure_id,)).fetchone():
                _fail('OURA_ERASE_ALREADY_COMPLETE')
        return _complete(root, erasure_id, json.loads(row[0]))


def resume_pending(inst):
    """Called by the pull owner; never acquires a second lock or skips errors."""
    root = Path(inst.ctx.root)
    upgrade.require_owner(root)
    _ensure_upgraded(root)
    for eid, encoded, _ in _pending(root):
        _complete(root, eid, json.loads(encoded))


def endpoint(handler, app, path):
    from erasure_providers import endpoint as dispatch
    return dispatch(handler, app, path)


def asset(handler, path):
    if path != '/assets/oura_erasure.js':
        return False
    handler._send(200, (Path(__file__).parent/'web/oura_erasure.js').read_bytes(),
                  'application/javascript; charset=utf-8')
    return True
