"""Append-only Oura originals. Only the per-instance pull owner writes here.

No credentials, request headers, absolute paths, or minute-heart-rate pages are
accepted. Readers never initialize a store or repair its contents.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from urllib.parse import unquote
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from h1_common import H1Error
from sqlite_util import append_only_ddl, assert_inside, open_db, transaction
from startorch_outbox import read_startorch

SCHEMA_ID = 'ptds-oura-raw/2'
TABLES = ('pull', 'pull_end', 'fetch', 'record', 'admission')
ERASURE_TABLES = ('erasure', 'erasure_end')
COLLECTIONS = frozenset(('daily_readiness', 'daily_sleep', 'daily_activity', 'daily_spo2', 'sleep', 'workout'))
DDL = '''
CREATE TABLE pull (
 pull_id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, policy TEXT NOT NULL,
 window_from TEXT NOT NULL, window_to TEXT NOT NULL, started_at TEXT NOT NULL, client TEXT NOT NULL);
CREATE TABLE pull_end (
 pull_id TEXT PRIMARY KEY REFERENCES pull, ended_at TEXT NOT NULL,
 outcome TEXT NOT NULL, fetches INTEGER NOT NULL, records INTEGER NOT NULL, error_code TEXT);
CREATE TABLE fetch (
 fetch_id TEXT PRIMARY KEY, pull_id TEXT NOT NULL REFERENCES pull, seq INTEGER NOT NULL,
 collection TEXT NOT NULL, params TEXT NOT NULL, requested_at TEXT NOT NULL,
 http_status INTEGER, outcome TEXT NOT NULL, error_code TEXT, body_sha256 TEXT, body_bytes INTEGER);
CREATE TABLE record (
 collection TEXT NOT NULL, vendor_id TEXT NOT NULL, day TEXT, payload_sha256 TEXT NOT NULL,
 first_fetch_id TEXT NOT NULL REFERENCES fetch, first_seen_at TEXT NOT NULL,
 PRIMARY KEY (collection, vendor_id, payload_sha256));
CREATE TABLE admission (
 receipt_digest TEXT NOT NULL, day TEXT NOT NULL, collection TEXT NOT NULL, vendor_id TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL, linked_at TEXT NOT NULL,
 PRIMARY KEY (receipt_digest, collection, vendor_id));
CREATE TABLE erasure (
 erasure_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE, scope TEXT NOT NULL,
 started_at TEXT NOT NULL, preview_digest TEXT NOT NULL);
CREATE TABLE erasure_end (
 erasure_id TEXT PRIMARY KEY REFERENCES erasure, ended_at TEXT NOT NULL,
 bodies_deleted INTEGER NOT NULL, bytes_freed INTEGER NOT NULL, status TEXT NOT NULL);
''' + append_only_ddl(TABLES + ERASURE_TABLES)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _fail(code='OURA_RAW_WRITE_FAILED'):
    raise H1Error(code, '')


def _directory(root, path):
    assert_inside(root, path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert_inside(root, path)


def _read_file(root, path):
    assert_inside(root, path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
            _fail('OURA_RAW_PATH_UNSAFE')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            return f.read()
    finally:
        os.close(fd)


def _body_path(root, digest):
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        _fail('OURA_RAW_HASH_INVALID')
    return Path(root) / 'startorch/oura_raw/bodies' / digest[:2] / (digest + '.json')


def write_body(root, raw):
    digest = _sha(raw)
    path = _body_path(root, digest)
    _directory(root, path.parent)
    assert_inside(root, path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if _sha(_read_file(root, path)) != digest:
            _fail('OURA_RAW_BODY_CORRUPT')
    else:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    return digest


def open_raw(root):
    directory = Path(root) / 'startorch/oura_raw'
    _directory(root, directory)
    import oura_raw_upgrade
    import oura_raw_recovery, oura_raw_v2
    had_sidecars = bool(oura_raw_recovery.members(root, directory / 'raw.db'))
    oura_raw_upgrade.prepare(root)
    conn = open_db(directory / 'raw.db', SCHEMA_ID, DDL, root=root)
    os.chmod(directory / 'raw.db', 0o600)
    if had_sidecars:
        conn = oura_raw_v2.check_connection(root, directory / 'raw.db', conn)
    return conn


def read_raw(root):
    path = Path(root) / 'startorch/oura_raw/raw.db'
    assert_inside(root, path)
    if not path.exists():
        return None
    if not path.is_file():
        _fail('OURA_RAW_PATH_UNSAFE')
    import oura_raw_upgrade
    conn = oura_raw_upgrade.read_connection(root, path)
    try:
        if oura_raw_upgrade.connection_version(conn) == 1:
            _fail('OURA_RAW_UPGRADE_PENDING')
        import oura_raw_recovery, oura_raw_v2
        if oura_raw_recovery.members(root, path) and not oura_raw_v2.healthy(conn, 'source'):
            _fail('OURA_RAW_RECOVERY_CORRUPT')
        return conn
    except BaseException:
        conn.close(); raise


def erasure_state(conn):
    """Completed prefix and pending count; tombstones contain metadata only."""
    cutoff, pending = 0, 0
    for scope, status in conn.execute("SELECT e.scope,d.status FROM erasure e LEFT JOIN erasure_end d USING(erasure_id)"):
        if status == 'COMPLETE':
            cutoff = max(cutoff, json.loads(scope)['fetch_through'])
        else:
            pending += 1
    return cutoff, pending


def erased_through(conn):
    """Per-body boundaries: missing/unreadable inputs were NEVER erased."""
    current, archived = {}, {}
    for (encoded,) in conn.execute("SELECT scope FROM erasure JOIN erasure_end USING(erasure_id) WHERE status='COMPLETE'"):
        scope = json.loads(encoded)
        sources = scope.get('sources', [])
        primary = next((x for x in sources if x['name'] == 'raw.db'), None)
        bodies = primary['bodies'] if primary is not None else scope['bodies']
        for digest, _ in bodies:
            current[digest] = max(current.get(digest, 0), scope['fetch_through'])
        for source in sources:
            key = (source['name'], source.get('sha256'))
            for digest, _ in source.get('bodies', []):
                boundary = (key, digest)
                archived[boundary] = max(archived.get(boundary, 0), source['fetch_through'])
    return current, archived


def _no_credentials(value, secrets):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in {'authorization', 'access_token', 'refresh_token', 'client_secret', 'password'}:
                _fail('OURA_RAW_CREDENTIAL_ECHO')
            _no_credentials(item, secrets)
    elif isinstance(value, list):
        for item in value: _no_credentials(item, secrets)
    elif isinstance(value, str):
        if any(secret and secret in unquote(value) for secret in secrets):
            _fail('OURA_RAW_CREDENTIAL_ECHO')


def _formal_lookup(root, request_id):
    """Private child entry: the SQLite read-only shared-memory mapping must be fresh."""
    with closing(read_startorch(root)) as formal:
        formal.execute('BEGIN')
        if request_id is not None:
            row = formal.execute('SELECT saved_at FROM save_request WHERE request_id=?', (request_id,)).fetchone()
            return row[0] if row else None
        saved, admitted = {}, {}
        for key, when, results in formal.execute(
                "SELECT request_id,saved_at,result FROM save_request WHERE request_id LIKE 'DEVICE-DAY-%'"):
            saved[key] = when
            observations = []
            for _, observation_id, revision, _ in json.loads(results):
                row = formal.execute('SELECT payload FROM formal_observation WHERE observation_id=? AND revision=?',
                                     (observation_id, revision)).fetchone()
                if row:
                    item = json.loads(row[0])
                    if item.get('source_kind') == 'DEVICE_OURA' and item['temporal'].get('role') == 'DAY':
                        observations.append((item['code'],item['value_raw'],item['unit_raw'],item['temporal']['observed_date']))
            admitted[key] = sorted(observations)
        return saved, admitted


def _formal_child():
    import sys
    root, request_id = json.load(sys.stdin)
    try:
        result = _formal_lookup(Path(root), request_id)
    except H1Error as exc:
        answer = dict(error=exc.code, detail=exc.detail)
    else:
        answer = dict(result=result)
    json.dump(answer, sys.stdout, ensure_ascii=True)


def _formal_read(root, request_id=None):
    """Two fixed queries over a private pipe. No shell, persistent worker or data-bearing logs."""
    import subprocess
    import sys
    app = Path(__file__).resolve().parent
    bootstrap = ("import sys;sys.path[:0]=sys.argv[1:3];"
                 "from oura_raw import _formal_child;_formal_child()")
    child = subprocess.run([sys.executable,'-B','-c',bootstrap,str(app),str(app/'core')],
                           input=json.dumps([str(root),request_id]),text=True,
                           stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=600,check=False)
    if child.returncode:
        raise OSError('main database read unavailable')
    answer = json.loads(child.stdout)
    if 'error' in answer:
        raise H1Error(answer['error'],answer['detail'])
    return answer['result']


def _saved_at(root, request_id):
    path = Path(root)/'startorch/startorch.db'
    assert_inside(root, path)
    return _formal_read(root, request_id) if path.is_file() else None


def _identity(collection, row):
    day = row.get('day')
    return str(row.get('id') or (collection + ':' + str(day or ''))), day


def _items(rows, tz):
    import oura
    return sorted((i.code, i.value_raw, i.unit_raw, i.temporal.get('observed_date'))
                  for i in oura.map_oura(rows, tz) if i.temporal.get('role') == 'DAY')


class Recorder:
    """One pull; synchronous page persistence and a latched write error.

    An optional collection's caller may catch H1Error. The latch ensures that
    this never turns a raw-write failure into permission to admit partial data.
    """
    def __init__(self, root, instance_id, policy, since, until, *, now=_now):
        self.root, self.now = Path(root), now
        self.pull_id = uuid.uuid4().hex
        self.fetches = self.records = 0
        self.failure = None
        self.rows = {}
        self.selected = {}
        try:
            self.conn = open_raw(root)
            if erasure_state(self.conn)[1]:
                _fail('OURA_RAW_ERASURE_PENDING')
            self.fetch_floor = 0
            if not self.conn.execute('SELECT 1 FROM fetch LIMIT 1').fetchone():
                self.fetch_floor = max((json.loads(r[0])['fetch_through'] for r in self.conn.execute('SELECT scope FROM erasure')),default=0)
            with transaction(self.conn):
                self.conn.execute('INSERT INTO pull VALUES (?,?,?,?,?,?,?)',
                    (self.pull_id, instance_id, policy, str(since), str(until), now(), 'ptds-oura/1'))
        except Exception:
            if hasattr(self, 'conn'): self.conn.close()
            _fail()

    def on_page(self, collection, params, raw, status, requested_at, error_code=None, *, secrets=()):
        if collection == 'heartrate':
            return
        self.assert_ok()
        try:
            if collection not in COLLECTIONS or set(params) - {'start_date', 'end_date', 'start_datetime', 'end_datetime', 'next_token'}:
                _fail('OURA_RAW_REQUEST_INVALID')
            # The caller passes no headers or URL. A credential echoed by a
            # provider is rejected, never redacted into a purported original.
            candidate = (raw or b'') + _json(params)
            if any(secret and secret.encode() in candidate for secret in secrets):
                _fail('OURA_RAW_CREDENTIAL_ECHO')
            fetch_id = uuid.uuid4().hex
            decode_error = None
            try:
                payload = json.loads(raw) if raw else {}
                _no_credentials(payload, secrets)
                _no_credentials(params, secrets)
                data = payload.get('data') or []
                if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
                    raise ValueError('shape')
            except (ValueError, AttributeError):
                data, decode_error = [], 'OURA_RAW_RESPONSE_INVALID'
            digest = write_body(self.root, raw) if raw is not None else None
            with transaction(self.conn):
                self.conn.execute('INSERT INTO fetch (rowid,fetch_id,pull_id,seq,collection,params,requested_at,http_status,outcome,error_code,body_sha256,body_bytes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (self.fetch_floor + 1 if self.fetch_floor and not self.fetches else None, fetch_id, self.pull_id, self.fetches + 1, collection, _json(params).decode(), requested_at,
                     status, 'ERROR' if error_code or decode_error else 'OK', error_code or decode_error, digest, len(raw) if raw is not None else None))
                for row in data:
                    vendor_id, day = _identity(collection, row)
                    self.conn.execute('INSERT OR IGNORE INTO record VALUES (?,?,?,?,?,?)',
                        (collection, vendor_id, day, _sha(_json(row)), fetch_id, self.now()))
            self.fetches += 1; self.records += len(data)
            self.rows.setdefault(collection, []).extend(data)
            if decode_error:
                _fail(decode_error)
        except Exception as exc:
            self.failure = exc.code if isinstance(exc, H1Error) else 'OURA_RAW_WRITE_FAILED'
            _fail(self.failure)

    def assert_ok(self):
        if self.failure:
            _fail(self.failure)

    def prepare(self, got, tz):
        """Bind only records contributing to the existing daily projection.

        Never approximate an ambiguous same-id/multiple-version projection:
        the specified admission key cannot represent it, so fail before save.
        """
        import oura
        self.assert_ok()
        wanted = {}
        for item in got['items']:
            if item.temporal.get('role') == 'DAY':
                wanted.setdefault(item.temporal['observed_date'], []).append((item.code, item.value_raw, item.unit_raw, item.temporal['observed_date']))
        for day, expected in wanted.items():
            groups = {}
            for collection, rows in self.rows.items():
                if collection not in got['collections']:
                    continue  # failed optional collection must not contribute
                candidates = [r for r in rows if r.get('day') == day]
                if collection == 'sleep' and candidates:
                    candidates = [max(candidates, key=lambda r:(r.get('type') == 'long_sleep', r.get('total_sleep_duration') or 0))]
                seen, chosen = set(), []
                for row in reversed(candidates):
                    codes = {i.code for i in oura.map_oura({collection:[row]}, tz)}
                    if codes - seen:
                        chosen.append(row)
                    seen.update(codes)
                if chosen: groups[collection] = list(reversed(chosen))
            if _items(groups, tz) != sorted(expected):
                _fail('OURA_RAW_PROJECTION_MISMATCH')
            refs = {}
            for collection, rows in groups.items():
                for row in rows:
                    vendor_id, _ = _identity(collection, row); digest = _sha(_json(row))
                    key = (collection, vendor_id)
                    if key in refs and refs[key] != digest:
                        _fail('OURA_RAW_AMBIGUOUS_RECORD')
                    refs[key] = digest
            self.selected[day] = refs

    def link(self, receipt):
        """Called after formal save, outside the global lock. Never overwrites."""
        try:
            if receipt.get('duplicate'):
                # A previously complete receipt cannot gain another admission.
                # Keep the original payload even when later vendor bytes differ.
                selected = self.selected.get(receipt['day'], {})
                if selected and all(self.conn.execute(
                        'SELECT 1 FROM admission WHERE receipt_digest=? AND collection=? AND vendor_id=?',
                        (receipt['content_digest'], collection, vendor_id)).fetchone()
                        for collection, vendor_id in selected):
                    return
                first = self.conn.execute('SELECT min(started_at) FROM pull').fetchone()[0]
                saved_at = _saved_at(self.root, receipt['request_id'])
                # A newly fetched equal payload is NOT the original of an
                # older admission. Never retroactively manufacture provenance.
                if saved_at and datetime.fromisoformat(saved_at) < datetime.fromisoformat(first):
                    return
            with transaction(self.conn):
                for (collection, vendor_id), payload in self.selected.get(receipt['day'], {}).items():
                    self.conn.execute('INSERT OR IGNORE INTO admission VALUES (?,?,?,?,?,?)',
                        (receipt['content_digest'], receipt['day'], collection, vendor_id, payload, self.now()))
        except Exception:
            _fail('OURA_RAW_LINK_FAILED')

    def finish(self, outcome, code=None):
        try:
            with transaction(self.conn):
                self.conn.execute('INSERT INTO pull_end VALUES (?,?,?,?,?,?)',
                    (self.pull_id, self.now(), outcome, self.fetches, self.records, code))
        finally:
            self.conn.close()


def counts(root):
    """Evidence-pack projection: counts only, no original content or ids."""
    try:
        conn = read_raw(root)
    except H1Error as exc:
        if exc.code not in ('OURA_RAW_UPGRADE_PENDING', 'OURA_RAW_RECOVERY_PENDING', 'OURA_RAW_RECOVERY_CORRUPT'): raise
        key = {'OURA_RAW_UPGRADE_PENDING':'upgrade_pending','OURA_RAW_RECOVERY_PENDING':'recovery_pending','OURA_RAW_RECOVERY_CORRUPT':'recovery_corrupt'}[exc.code]
        return dict.fromkeys(TABLES + ERASURE_TABLES, 0) | {key:True}
    if conn is None:
        return {t:0 for t in TABLES + ERASURE_TABLES}
    with closing(conn):
        return {t:conn.execute('SELECT count(*) FROM ' + t).fetchone()[0] for t in TABLES + ERASURE_TABLES}


def check(root):
    """Read-only replay against immutable daily summaries and save receipts.

    Old/gap classification uses the formal save_request.saved_at, never mtime.
    Missing proof of age is a gap. Historical rows are not backfilled here.
    """
    import device_daily
    root = Path(root)
    result = dict(consistent=0, inconsistent=0, before_raw_layer=0, gaps=0, upstream_revisions=0,
                  orphan_bodies=0, bad_bodies=0, missing_vendor_id=0, unfinished_pulls=0,
                  erased=0, erased_admissions=0, erased_results=0, unfinished_erasures=0)
    import oura_raw_upgrade as upgrade
    result.update(upgrade_pending=False, recovery_pending=False, recovery_corrupt=False, erasure_intent_errors=0, archived_libraries=len(upgrade.archives(root)),
                  quarantined_libraries=sum('quarantine-' in p.name for p in upgrade.archives(root)),
                  quarantine_groups=sum('quarantine-' in p.name for p in upgrade.archives(root)), archive_index_errors=0)
    try:
        conn = read_raw(root)
    except H1Error as exc:
        if exc.code not in ('OURA_RAW_UPGRADE_PENDING', 'OURA_RAW_RECOVERY_PENDING', 'OURA_RAW_RECOVERY_CORRUPT'): raise
        result[{'OURA_RAW_UPGRADE_PENDING':'upgrade_pending','OURA_RAW_RECOVERY_PENDING':'recovery_pending','OURA_RAW_RECOVERY_CORRUPT':'recovery_corrupt'}[exc.code]] = True
        return result
    references, payloads, first = {}, {}, None
    if conn is not None:
        with closing(conn):
            first = conn.execute('SELECT min(started_at) FROM pull').fetchone()[0]
            result['unfinished_pulls'] = conn.execute('SELECT count(*) FROM pull p LEFT JOIN pull_end e USING(pull_id) WHERE e.pull_id IS NULL').fetchone()[0]
            result['upstream_revisions'] = conn.execute('SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM record GROUP BY collection,vendor_id)').fetchone()[0]
            result['missing_vendor_id'] = conn.execute("SELECT count(*) FROM record WHERE vendor_id=collection || ':' || coalesce(day,'')").fetchone()[0]
            _, result['unfinished_erasures'] = erasure_state(conn)
            erased, archive_erased = erased_through(conn)
            indexed = set()
            for digest, latest in conn.execute('SELECT body_sha256,max(rowid) FROM fetch WHERE body_sha256 IS NOT NULL GROUP BY body_sha256'):
                indexed.add(digest)
                if latest <= erased.get(digest, 0):
                    result['erased'] += 1
                    continue
                try:
                    raw = _read_file(root, _body_path(root, digest))
                    if _sha(raw) != digest: raise ValueError('hash')
                    payloads[digest] = json.loads(raw)
                except (OSError, ValueError, H1Error):
                    result['bad_bodies'] += 1
            archived = upgrade.archived_sources(root)
            result['archive_index_errors'] = sum(bool(x.get('index_unreadable')) for x in archived)
            result['erasure_intent_errors'] = sum(bool(x.get('erasure_intents_unreadable')) for x in archived)
            for source in archived:
                for digest, latest in source['files']:
                    if digest in indexed: continue
                    indexed.add(digest)
                    if latest <= max(source['erased'].get(digest,0), archive_erased.get(((source['name'], source['sha256']), digest), 0)):
                        result['erased'] += 1
                    else:
                        try:
                            if _sha(_read_file(root, _body_path(root, digest))) != digest: raise ValueError('hash')
                        except (OSError, ValueError, H1Error): result['bad_bodies'] += 1
            directory = root/'startorch/oura_raw/bodies'
            assert_inside(root, directory)
            if directory.exists():
                for prefix in directory.iterdir():
                    assert_inside(root, prefix)
                    if prefix.is_dir():
                        for p in prefix.iterdir():
                            assert_inside(root, p)
                            if p.is_file() and p.stem not in indexed: result['orphan_bodies'] += 1
            for receipt, collection, vendor, payload, body, fetch_row in conn.execute('''
                SELECT a.receipt_digest,a.collection,a.vendor_id,a.payload_sha256,f.body_sha256,f.rowid
                FROM admission a LEFT JOIN record r ON r.collection=a.collection AND r.vendor_id=a.vendor_id AND r.payload_sha256=a.payload_sha256
                LEFT JOIN fetch f ON f.fetch_id=r.first_fetch_id ORDER BY a.rowid'''):
                groups = references.setdefault(receipt, {})
                if fetch_row is not None and fetch_row <= erased.get(body, 0):
                    result['erased_admissions'] += 1
                    groups.setdefault('_erased', []).append({})
                    continue
                row = next((r for r in payloads.get(body, {}).get('data', []) if _sha(_json(r)) == payload and _identity(collection,r)[0] == vendor), None)
                if row is None:
                    groups.setdefault('_bad', []).append({})
                else:
                    groups.setdefault(collection, []).append(row)
    # Resolve each saved result's exact revision, not today's latest revision.
    saved, admitted = {}, {}
    path = root/'startorch/startorch.db'
    assert_inside(root, path)
    if path.is_file():
        saved, rows = _formal_read(root)
        admitted = {key: [tuple(row) for row in values] for key, values in rows.items()}
    directory = root/'startorch/device_daily/receipts'
    assert_inside(root, directory)
    if directory.exists():
        for p in sorted(directory.glob('*.json')):
            receipt = json.loads(_read_file(root, p))
            if receipt.get('source_kind') != 'DEVICE_OURA': continue
            digest = receipt.get('content_digest'); groups = references.get(digest)
            if groups and '_bad' in groups:
                result['inconsistent'] += 1
                continue
            if groups and '_erased' in groups:
                result['erased_results'] += 1
                continue
            if not groups:
                when = saved.get(receipt.get('request_id'))
                is_old = conn is None or (first and when and datetime.fromisoformat(when) < datetime.fromisoformat(first))
                result['before_raw_layer' if is_old else 'gaps'] += 1
                continue
            try:
                if not re.fullmatch('[0-9a-f]{64}', digest or ''): raise ValueError('digest')
                summary = json.loads(_read_file(root, root/'startorch/device_daily/summaries'/(digest+'.json')))
                expected = sorted((i['code'], i['value_raw'], i['unit_raw'], summary['day']) for i in summary['items'])
                equal = ('_bad' not in groups and device_daily.body_digest(summary) == digest
                         and _items(groups, summary['timezone']) == expected
                         and admitted.get(receipt['request_id']) == expected)
                result['consistent' if equal else 'inconsistent'] += 1
            except (OSError, ValueError, H1Error, KeyError, TypeError):
                result['inconsistent'] += 1
    return result
