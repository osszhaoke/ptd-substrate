"""One-off Oura /1 to /2 copy-and-replace. No global lock or formal storage."""
from contextlib import closing, contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import stat
import sqlite3
import uuid

from h1_common import H1Error
from sqlite_util import append_only_ddl, assert_inside, connect, open_db, transaction

DDL_V1 = "\nCREATE TABLE pull (\n pull_id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, policy TEXT NOT NULL,\n window_from TEXT NOT NULL, window_to TEXT NOT NULL, started_at TEXT NOT NULL, client TEXT NOT NULL);\nCREATE TABLE pull_end (\n pull_id TEXT PRIMARY KEY REFERENCES pull, ended_at TEXT NOT NULL,\n outcome TEXT NOT NULL, fetches INTEGER NOT NULL, records INTEGER NOT NULL, error_code TEXT);\nCREATE TABLE fetch (\n fetch_id TEXT PRIMARY KEY, pull_id TEXT NOT NULL REFERENCES pull, seq INTEGER NOT NULL,\n collection TEXT NOT NULL, params TEXT NOT NULL, requested_at TEXT NOT NULL,\n http_status INTEGER, outcome TEXT NOT NULL, error_code TEXT, body_sha256 TEXT, body_bytes INTEGER);\nCREATE TABLE record (\n collection TEXT NOT NULL, vendor_id TEXT NOT NULL, day TEXT, payload_sha256 TEXT NOT NULL,\n first_fetch_id TEXT NOT NULL REFERENCES fetch, first_seen_at TEXT NOT NULL,\n PRIMARY KEY (collection, vendor_id, payload_sha256));\nCREATE TABLE admission (\n receipt_digest TEXT NOT NULL, day TEXT NOT NULL, collection TEXT NOT NULL, vendor_id TEXT NOT NULL,\n payload_sha256 TEXT NOT NULL, linked_at TEXT NOT NULL,\n PRIMARY KEY (receipt_digest, collection, vendor_id));\nCREATE TRIGGER pull_no_update BEFORE UPDATE ON pull BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER pull_no_delete BEFORE DELETE ON pull BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER pull_end_no_update BEFORE UPDATE ON pull_end BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER pull_end_no_delete BEFORE DELETE ON pull_end BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER fetch_no_update BEFORE UPDATE ON fetch BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER fetch_no_delete BEFORE DELETE ON fetch BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER record_no_update BEFORE UPDATE ON record BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER record_no_delete BEFORE DELETE ON record BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER admission_no_update BEFORE UPDATE ON admission BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\nCREATE TRIGGER admission_no_delete BEFORE DELETE ON admission BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\n"
DDL_V1_SHA256 = '0383e3f47798566a589e815f36330538aa1b89c69461933f493c9fa507f401ab'
_OWNER = ContextVar('oura_upgrade_owner', default=None)
TABLES = ('pull', 'pull_end', 'fetch', 'record', 'admission')


def fail(code='DB_SCHEMA_MISMATCH'):
    raise H1Error(code, '')


@contextmanager
def ownership(root, guard):
    """Only the existing pull/erase acquisition site installs this marker."""
    token = _OWNER.set((os.path.abspath(root), guard) if root is not None else None)
    try:
        yield
    finally:
        _OWNER.reset(token)


def require_owner(root):
    owner = _OWNER.get()
    if not owner or owner[0] != os.path.abspath(root) or not owner[1].locked():
        fail('OURA_RAW_GUARD_REQUIRED')


def _safe(root, path):
    assert_inside(root, path)
    if path.exists():
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                fail('OURA_RAW_PATH_UNSAFE')
        finally:
            os.close(fd)
    return path


def read_connection(root, path):
    """The file is attached mode=ro; even SQLite journal recovery cannot write it."""
    _safe(root, path)
    conn = connect(':memory:')
    try:
        conn.execute('ATTACH DATABASE ? AS source', (Path(path).absolute().as_uri() + '?mode=ro',))
        conn.execute('PRAGMA query_only=ON')
        return conn
    except BaseException as exc:
        conn.close()
        if getattr(exc, 'sqlite_errorcode', None) == sqlite3.SQLITE_READONLY_ROLLBACK:
            fail('OURA_RAW_RECOVERY_PENDING')
        raise


@contextmanager
def readonly(root, path):
    with closing(read_connection(root, path)) as conn:
        yield conn


def _objects(conn, schema):
    return set(conn.execute('SELECT type,name,tbl_name,sql FROM ' + schema + ".sqlite_master WHERE name NOT LIKE 'sqlite_%'"))


def _expected(ddl):
    with closing(connect(':memory:')) as c:
        c.executescript(ddl + 'CREATE TABLE schema_meta (schema_id TEXT NOT NULL, ddl_sha256 TEXT NOT NULL);\n' + append_only_ddl(['schema_meta']))
        return _objects(c, 'main')


def connection_version(conn):
    """Strict objects and metadata; never infer a version from a filename."""
    from oura_raw import DDL, SCHEMA_ID
    try:
        rows = conn.execute('SELECT schema_id,ddl_sha256 FROM source.schema_meta').fetchall()
        objects = _objects(conn, 'source')
    except sqlite3.DatabaseError as exc:
        if getattr(exc, 'sqlite_errorcode', None) == sqlite3.SQLITE_READONLY_ROLLBACK:
            fail('OURA_RAW_RECOVERY_PENDING')
        fail()
    for v, sid, ddl in ((1, 'ptds-oura-raw/1', DDL_V1), (2, SCHEMA_ID, DDL)):
        if rows == [(sid, hashlib.sha256(ddl.encode()).hexdigest())] and objects == _expected(ddl):
            return v
    fail()


def version(root, path):
    with readonly(root, path) as conn:
        return connection_version(conn)


def _fsync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _unique(directory, kind, *, version=1):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    return directory / ('raw.db.v' + str(version) + '-' + kind + '-' + stamp + '-' + uuid.uuid4().hex)


def _copy_bytes(root, old, target):
    _safe(root, old); assert_inside(root, target)
    src = os.open(old, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        dest = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(dest, 'wb') as out, os.fdopen(src, 'rb', closefd=False) as inp:
            while chunk := inp.read(1024 * 1024):
                out.write(chunk)
            out.flush(); os.fsync(out.fileno())
    finally:
        os.close(src)
    _fsync_dir(target.parent)


def _discard_tmp(root, path):
    # Only our fixed scratch database; never bodies, backup or quarantine files.
    _safe(root, path)
    if path.exists():
        path.unlink(); _fsync_dir(path.parent)
    for suffix in ('-journal', '-wal', '-shm'):
        p = Path(str(path) + suffix); _safe(root, p)
        if p.exists():
            p.unlink(); _fsync_dir(p.parent)


def table_digest(conn, schema, table):
    info = conn.execute('PRAGMA ' + schema + '.table_info(' + table + ')').fetchall()
    pk = [x[1] for x in sorted(info, key=lambda x:x[5]) if x[5]]
    digest = hashlib.sha256(); count = 0
    for row in conn.execute('SELECT * FROM ' + schema + '.' + table + ' ORDER BY ' + ','.join(pk)):
        digest.update(json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode()); digest.update(b'\n'); count += 1
    return count, digest.hexdigest()


def _verify(conn):
    for table in TABLES:
        if table_digest(conn, 'main', table) != table_digest(conn, 'source', table):
            fail('OURA_RAW_UPGRADE_VERIFY_FAILED')
    for schema in ('main', 'source'):
        if conn.execute('PRAGMA ' + schema + '.integrity_check').fetchall() != [('ok',)]:
            fail('OURA_RAW_UPGRADE_INTEGRITY_FAILED')


def _checkpoint(name):
    """Test injection point; no production side effect."""


def prepare(root):
    """Called only by open_raw; /1 failures preserve the old file then rebuild."""
    from oura_raw import DDL, SCHEMA_ID
    import oura_raw_recovery as recovery
    directory = Path(root) / 'startorch/oura_raw'; old = _safe(root, directory / 'raw.db')
    import oura_raw_v2
    oura_raw_v2.resume(root, old)
    if not old.exists(): return
    # Resolve an interrupted sidecar detach before any SQLite access.
    marker = recovery.area(root, old) / 'swap.json'
    if marker.exists():
        require_owner(root); recovery.resume_swap(root, old)
    sidecars = recovery.members(root, old)
    if not sidecars and version(root, old) == 2: return
    require_owner(root)
    recovery.clean(root, old)
    tmp = directory / 'raw.db.upgrade-tmp'
    _discard_tmp(root, tmp)
    replaced = False
    def published():
        nonlocal replaced
        replaced = True
    try:
        source = recovery.recover(root, old, sidecars) if sidecars else old
        if version(root, source) == 2:
            # Return the ORIGINAL file to open_db. Only SQLite may recover it.
            return
        with closing(open_db(tmp, SCHEMA_ID, DDL, root=root)) as c:
            os.chmod(tmp, 0o600)
            c.execute('ATTACH DATABASE ? AS source', (source.absolute().as_uri() + '?mode=ro',))
            with transaction(c):
                for table in TABLES:
                    cols = ','.join(x[1] for x in c.execute('PRAGMA source.table_info(' + table + ')'))
                    c.execute('INSERT INTO main.' + table + ' (rowid,' + cols + ') SELECT rowid,' + cols + ' FROM source.' + table + ' ORDER BY rowid')
            _checkpoint('copied')
            _verify(c); _checkpoint('verified')
        backup = recovery.archive(root, old, sidecars, 'backup')
        _checkpoint('backed_up')
        with open(tmp, 'rb') as f:
            os.fsync(f.fileno())
        recovery.replace(root, old, tmp, sidecars, backup, published=published)
        _checkpoint('replaced')
    except Exception as exc:
        if replaced:
            raise  # Never quarantine the newly published /2 as if it were /1.
        recovery.resume_swap(root, old)
        # Failed recovery is not proof of /1. Strictly check an untouched-byte
        # schema copy before any archive rename; /2 and unknown stay in place.
        original = recovery.original_version(root, old)
        if original == 2:
            if isinstance(exc, sqlite3.DatabaseError) or (isinstance(exc, H1Error) and
                    exc.code in ('DB_SCHEMA_MISMATCH', 'OURA_RAW_RECOVERY_INTEGRITY', 'OURA_RAW_RECOVERY_PENDING')):
                if sidecars and oura_raw_v2.from_recovered_copy(root, old): return
                return  # open_raw checks the original recovered /2 connection before handing it out.
            raise  # Keep path/policy/internal failures closed; never rename /2.
        if original != 1:
            raise
        recovery.archive(root, old, recovery.members(root, old), 'quarantine', move=True)
        _discard_tmp(root, tmp)
        with closing(open_db(old, SCHEMA_ID, DDL, root=root)):
            os.chmod(old, 0o600)
        _fsync_dir(directory)
        logging.getLogger(__name__).warning('OURA_RAW_UPGRADE_QUARANTINED')


def archives(root):
    directory = Path(root) / 'startorch/oura_raw'
    assert_inside(root, directory)
    if not directory.exists():
        return []
    return [_safe(root, p) for p in sorted(directory.iterdir())
            if p.name.startswith(('raw.db.v1-backup-', 'raw.db.v1-quarantine-', 'raw.db.v2-quarantine-'))
            and not p.name.endswith(('-journal', '-wal', '-shm'))]


def file_digest(root, path):
    _safe(root, path)
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def archived_sources(root):
    """Readable indexes and internal tombstones; no archive bytes are modified."""
    import oura_raw_v2 as v2
    from oura_raw import erased_through
    result = []
    for path in archives(root):
        item = dict(name=path.name, sha256=file_digest(root, path), fetch_through=0,
                    date_from=None, date_to=None, files=[], erased={})
        try:
            with v2.archive_view(root, path) as c:
                version_number = connection_version(c)
                item['schema_id'] = 'ptds-oura-raw/' + str(version_number)
                try:
                    item['files'] = c.execute('SELECT body_sha256,max(rowid) FROM source.fetch WHERE body_sha256 IS NOT NULL GROUP BY body_sha256 ORDER BY body_sha256').fetchall()
                    item['fetch_through'] = c.execute('SELECT coalesce(max(rowid),0) FROM source.fetch').fetchone()[0]
                except sqlite3.DatabaseError: item['index_unreadable'] = True
                try: item['date_from'], item['date_to'] = c.execute('SELECT min(day),max(day) FROM source.record').fetchone()
                except sqlite3.DatabaseError: item['index_unreadable'] = True
                if version_number == 2:
                    try:
                        item['erased'] = erased_through(c)[0]
                        # An intent copied to the new current library keeps its ID
                        # and scope. Completion there also covers this old source.
                        intents = {row[0]:row for row in v2.pending(c,'source')}
                        current = Path(root)/'startorch/oura_raw/raw.db'
                        if intents and current.exists():
                            with readonly(root,current) as live:
                                for row in live.execute("SELECT e.* FROM source.erasure e JOIN source.erasure_end d USING(erasure_id) WHERE d.status='COMPLETE'"):
                                    if intents.get(row[0]) == row:
                                        scope = json.loads(row[2])
                                        for digest, _ in scope['bodies']:
                                            item['erased'][digest] = max(item['erased'].get(digest,0),scope['fetch_through'])
                    except (sqlite3.DatabaseError,H1Error):
                        item['index_unreadable'] = True; item['erasure_intents_unreadable'] = True
        except Exception:
            item['index_unreadable'] = True
            if path.name.startswith('raw.db.v2-quarantine-'): item['erasure_intents_unreadable'] = True
        result.append(item)
    return result


def archived_cutoffs(conn):
    result = {}
    for (encoded,) in conn.execute("SELECT scope FROM erasure JOIN erasure_end USING(erasure_id) WHERE status='COMPLETE'"):
        for source in json.loads(encoded).get('sources', []):
            key = (source['name'], source.get('sha256'))
            result[key] = max(result.get(key, 0), source['fetch_through'])
    return result
