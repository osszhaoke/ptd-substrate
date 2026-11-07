"""Internal preview evidence storage, not an authorization or erasure entry point.

record_confirmation is a trusted P2 adapter boundary, not proof of a click.
The local P2 provider first consumes its one-shot confirmation credential.
Test callers use explicitly simulated confirmations and fictional data only.
Hash chains detect changes relative to a trusted anchor, not whole-store rollback.
"""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid

from h1_common import H1Error
from sqlite_util import assert_inside, connect, transaction

SCHEMA = 'ptds-evidence-event/0.1-preview'
STORE_SCHEMA = 'ptds-evidence-ledger/0.1-preview'
_TABLES = (
    'CREATE TABLE schema_meta (schema_id TEXT NOT NULL, ddl_sha256 TEXT NOT NULL)',
    '''CREATE TABLE confirmation (
       confirmation_id TEXT PRIMARY KEY, instance_id TEXT NOT NULL,
       request_id TEXT NOT NULL, preview_digest TEXT NOT NULL, confirmed_at TEXT NOT NULL,
       UNIQUE(instance_id, request_id))''',
    '''CREATE TABLE event (
       seq INTEGER PRIMARY KEY, event_id TEXT NOT NULL UNIQUE,
       instance_id TEXT NOT NULL, erasure_id TEXT NOT NULL,
       confirmation_id TEXT NOT NULL REFERENCES confirmation,
       payload TEXT NOT NULL, event_hash TEXT NOT NULL,
       UNIQUE(instance_id, erasure_id))''',
)
_GUARDS = tuple(
    f"CREATE TRIGGER {table}_no_{op.lower()} BEFORE {op} ON {table} "
    "BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END"
    for table in ('schema_meta', 'confirmation', 'event') for op in ('UPDATE', 'DELETE'))
_DDL = _TABLES + _GUARDS


def _fail(code):
    raise H1Error(code, '')


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def _identifier(value, pattern):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        _fail('EVIDENCE_IDENTIFIER_INVALID')
    return value


def _instance(value):
    return _identifier(value, r'[A-Za-z0-9_-]{1,128}')


def _uuid(value):
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        _fail('EVIDENCE_IDENTIFIER_INVALID')
    return value


def _objects(c, schema):
    return frozenset(c.execute('SELECT type,name,tbl_name,sql FROM ' + schema +
                              ".sqlite_master WHERE name NOT LIKE 'sqlite_%'"))


@lru_cache(maxsize=1)
def _expected():
    with closing(connect(':memory:')) as c:
        for sql in _DDL:
            c.execute(sql)
        return _objects(c, 'main')


def _validate(c, schema):
    if _objects(c, schema) != _expected():
        _fail('EVIDENCE_SCHEMA_MISMATCH')
    rows = c.execute('SELECT schema_id,ddl_sha256 FROM ' + schema + '.schema_meta').fetchall()
    if rows != [(STORE_SCHEMA, digest(_DDL))]:
        _fail('EVIDENCE_SCHEMA_MISMATCH')


def _path(root):
    path = Path(root) / 'startorch/evidence/ledger.db'
    # Check sidecars as well: SQLite must never follow an external journal.
    for suffix in ('', '-journal', '-wal', '-shm'):
        assert_inside(root, Path(str(path) + suffix))
    if path.exists() and not path.is_file():
        _fail('EVIDENCE_PATH_UNSAFE')
    return path


@contextmanager
def _write(root):
    path = _path(root)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _path(root)
    # SQLite must not create a temporarily world-readable file under umask 000.
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    _path(root)
    with closing(connect(path)) as c:
        with transaction(c):
            # Serialize first-open too; executescript would implicitly commit.
            if not _objects(c, 'main'):
                for sql in _DDL:
                    c.execute(sql)
                c.execute('INSERT INTO schema_meta VALUES (?,?)', (STORE_SCHEMA, digest(_DDL)))
            _validate(c, 'main')
            yield c


@contextmanager
def _read(root):
    path = _path(root)
    if not path.exists():
        yield None
        return
    # Narrow read-only connection: uri=True explicitly enables mode=ro on
    # ATTACH even when SQLite was compiled without its USE_URI default.
    # No writes use this connection; shared sqlite_util stays unchanged.
    with closing(sqlite3.connect(':memory:', uri=True, isolation_level=None)) as c:
        c.execute('ATTACH DATABASE ? AS source', (path.absolute().as_uri() + '?mode=ro',))
        c.execute('PRAGMA query_only=ON')
        c.execute('BEGIN')
        _validate(c, 'source')
        yield c


def record_confirmation(root, instance_id, request_id, preview_digest, confirmation_id):
    """Persist an already verified P2 confirmation; never authorizes execution.

    P2 must call BEFORE original intent and only after atomic credential claim.
    Recovery may reuse this reference for accounting, never for another delete.
    """
    _instance(instance_id); _uuid(request_id); _uuid(confirmation_id)
    _identifier(preview_digest, '[0-9a-f]{64}')
    with _write(root) as c:
        row = c.execute('SELECT confirmation_id,preview_digest FROM confirmation '
                        'WHERE instance_id=? AND request_id=?', (instance_id, request_id)).fetchone()
        if row:
            if row != (confirmation_id, preview_digest):
                _fail('EVIDENCE_CONFIRMATION_CONFLICT')
            return confirmation_id
        c.execute('INSERT INTO confirmation VALUES (?,?,?,?,?)',
                  (confirmation_id, instance_id, request_id, preview_digest,
                   datetime.now(timezone.utc).isoformat()))
    return confirmation_id


def confirmation(root, instance_id, request_id, preview_digest, *, before=None):
    with _read(root) as c:
        if c is None:
            return None
        row = c.execute('SELECT confirmation_id,confirmed_at FROM source.confirmation WHERE '
                        'instance_id=? AND request_id=? AND preview_digest=?',
                        (instance_id, request_id, preview_digest)).fetchone()
        if row and before is not None:
            confirmed = datetime.fromisoformat(row[1])
            started = datetime.fromisoformat(before)
            if confirmed.tzinfo is None or started.tzinfo is None or confirmed > started:
                return None
        return row[0] if row else None


def get_event(root, instance_id, erasure_id):
    with _read(root) as c:
        if c is None:
            return None
        row = c.execute('SELECT payload FROM source.event WHERE instance_id=? AND erasure_id=?',
                        (instance_id, erasure_id)).fetchone()
        return json.loads(row[0]) if row else None


def append_completed(root, instance_id, erasure_id, request_id, preview_digest,
                     tombstone_digest, counts, occurred_at):
    """Storage adapter; the service must validate an immutable COMPLETE first."""
    _instance(instance_id); _identifier(erasure_id, '[0-9a-f]{32}'); _uuid(request_id)
    for value in (preview_digest, tombstone_digest):
        _identifier(value, '[0-9a-f]{64}')
    if set(counts) not in ({'files', 'registered_bytes', 'sources'},
                          {'files', 'registered_bytes', 'sources', 'archives'}):
        _fail('EVIDENCE_COUNTS_INVALID')
    if any(type(counts[k]) is not int or counts[k] < 0 for k in ('files', 'registered_bytes')):
        _fail('EVIDENCE_COUNTS_INVALID')
    if not isinstance(counts['sources'], list):
        _fail('EVIDENCE_COUNTS_INVALID')
    for row in counts['sources']:
        if not isinstance(row, dict) or set(row) != {'files', 'registered_bytes', 'missing'} or any(
                type(v) is not int or v < 0 for v in row.values()):
            _fail('EVIDENCE_COUNTS_INVALID')
    if 'archives' in counts:
        archived = counts['archives']
        if (not isinstance(archived, dict) or set(archived) != {'files','registered_bytes'} or
                any(type(v) is not int or v < 0 for v in archived.values())):
            _fail('EVIDENCE_COUNTS_INVALID')
    try:
        instant = datetime.fromisoformat(occurred_at)
        if instant.utcoffset() != timezone.utc.utcoffset(instant):
            raise ValueError()
    except (TypeError, ValueError, AttributeError):
        _fail('EVIDENCE_TIME_INVALID')
    fields = dict(schema=SCHEMA, app='startorch', type='ERASURE_COMPLETED',
                  occurred_at=occurred_at, instance_id=instance_id, actor='SELF',
                  subject=dict(kind='oura_raw_layer', erasure_id=erasure_id),
                  digests=dict(tombstone=tombstone_digest, preview_digest=preview_digest), counts=counts)
    with _write(root) as c:
        proof = c.execute('SELECT confirmation_id FROM confirmation WHERE instance_id=? '
                          'AND request_id=? AND preview_digest=?',
                          (instance_id, request_id, preview_digest)).fetchone()
        if not proof:
            _fail('EVIDENCE_SELF_CONFIRMATION_REQUIRED')
        row = c.execute('SELECT payload,confirmation_id FROM event WHERE instance_id=? AND erasure_id=?',
                        (instance_id, erasure_id)).fetchone()
        if row:
            event = json.loads(row[0])
            if {k: event[k] for k in fields} != fields or row[1] != proof[0]:
                _fail('EVIDENCE_EVENT_CONFLICT')
            return event
        last = c.execute('SELECT event_hash FROM event ORDER BY seq DESC LIMIT 1').fetchone()
        event = dict(fields, event_id=str(uuid.uuid4()), prev_hash=last[0] if last else None)
        c.execute('INSERT INTO event(event_id,instance_id,erasure_id,confirmation_id,payload,event_hash) '
                  'VALUES (?,?,?,?,?,?)', (event['event_id'], instance_id, erasure_id, proof[0],
                                         encoded(event).decode(), digest(event)))
        return event


def _verified(c):
    previous = None
    if c is not None:
        for payload, stored in c.execute('SELECT payload,event_hash FROM source.event ORDER BY seq'):
            event = json.loads(payload)
            if event['prev_hash'] != previous or digest(event) != stored:
                _fail('EVIDENCE_CHAIN_INVALID')
            yield event, stored
            previous = stored


def verify(root):
    count, last = 0, None
    with _read(root) as c:
        for _, last in _verified(c):
            count += 1
    return dict(events=count, last_hash=last)


def export_projection(root):
    """Explicit atomic export of one read snapshot; never source of authority."""
    path = _path(root).parent / 'events.jsonl'
    assert_inside(root, path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name('.projection-' + uuid.uuid4().hex)
    count, last = 0, None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as out, _read(root) as c:
            for event, last in _verified(c):
                out.write(encoded(event) + b'\n'); count += 1
            out.flush(); os.fsync(out.fileno())
        assert_inside(root, path)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(events=count, last_hash=last)
