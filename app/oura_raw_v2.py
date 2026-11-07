"""Confirmed /2 corruption policy; invoked only for sidecar recovery.

Original archive bytes are never opened for write. Copies used to inspect an
archive are disposable, and cannot repair or hide errors in the archived file.
"""
from contextlib import closing, contextmanager
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import tempfile

import oura_raw_upgrade as up
import oura_raw_recovery as recovery

MARKER = 'raw.db.v2-replacement.json'
NEW = 'raw.db.v2-replacement'


def identity(conn, schema='main'):
    from oura_raw import DDL, SCHEMA_ID
    try:
        return conn.execute('SELECT schema_id,ddl_sha256 FROM '+schema+'.schema_meta').fetchall() == [(SCHEMA_ID, hashlib.sha256(DDL.encode()).hexdigest())]
    except sqlite3.DatabaseError:
        return False


def healthy(conn, schema='main'):
    try:
        return conn.execute('PRAGMA '+schema+'.integrity_check').fetchall() == [('ok',)]
    except sqlite3.DatabaseError:
        return False


def pending(conn, schema='main'):
    return conn.execute('SELECT e.* FROM '+schema+'.erasure e LEFT JOIN '+schema+'.erasure_end d USING(erasure_id) WHERE d.erasure_id IS NULL ORDER BY e.rowid').fetchall()


def resume(root, old):
    """Publish a prepared replacement, also after a process exit between renames."""
    marker = up._safe(root, old.parent / MARKER)
    if not marker.exists(): return
    up.require_owner(root)
    with open(marker) as f: job = json.load(f)
    name = job['archive']
    if Path(name).name != name or not name.startswith('raw.db.v2-quarantine-'):
        up.fail('OURA_RAW_RECOVERY_CONFLICT')
    tmp = up._safe(root, old.parent / NEW)
    for suffix, digest in job['members'].items():
        if suffix not in ('',)+recovery.SIDECARS: up.fail('OURA_RAW_RECOVERY_CONFLICT')
        src = up._safe(root, Path(str(old)+suffix)); dst = up._safe(root, old.parent/(name+suffix))
        if dst.exists():
            if up.file_digest(root,dst) != digest: up.fail('OURA_RAW_RECOVERY_CONFLICT')
        else:
            if up.file_digest(root,src) != digest: up.fail('OURA_RAW_RECOVERY_CONFLICT')
            os.rename(src,dst); up._fsync_dir(old.parent)
    if tmp.exists():
        if up.file_digest(root,tmp) != job['new_sha256'] or old.exists(): up.fail('OURA_RAW_RECOVERY_CONFLICT')
        os.replace(tmp,old); up._fsync_dir(old.parent)
    elif not old.exists() or up.file_digest(root,old) != job['new_sha256']:
        up.fail('OURA_RAW_RECOVERY_CONFLICT')
    marker.unlink(); up._fsync_dir(old.parent)


def quarantine(root, old, intent_rows):
    """Caller proved /2 and failed integrity; only intent rows cross the boundary."""
    from oura_raw import DDL, SCHEMA_ID
    up.require_owner(root)
    tmp = old.parent / NEW
    up._discard_tmp(root,tmp)
    with closing(up.open_db(tmp,SCHEMA_ID,DDL,root=root)) as c:
        os.chmod(tmp,0o600)
        with up.transaction(c):
            c.executemany('INSERT INTO erasure VALUES (?,?,?,?,?)',intent_rows)
    with open(tmp,'rb') as f: os.fsync(f.fileno())
    group = up._unique(old.parent,'quarantine',version=2)
    members = [old]+recovery.members(root,old)
    job = dict(archive=group.name,new_sha256=up.file_digest(root,tmp),
               members={p.name[len(old.name):]:up.file_digest(root,p) for p in members})
    marker = up._safe(root,old.parent/MARKER)
    fd = os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(job,f);f.flush();os.fsync(f.fileno())
    up._fsync_dir(old.parent)
    up._checkpoint('v2_replacement_ready')
    resume(root,old)
    logging.getLogger(__name__).warning('OURA_RAW_V2_CORRUPT_QUARANTINED')


def from_recovered_copy(root, old):
    """Return True only after confirmed corrupt /2 was durably replaced."""
    source = up._safe(root,recovery.area(root,old)/'raw.db')
    if not source.exists(): return False
    try:
        c = up.read_connection(root,source)
    except (sqlite3.DatabaseError,up.H1Error):
        return False
    with closing(c):
        if not identity(c,'source') or healthy(c,'source'): return False
        try: rows = pending(c,'source')
        except sqlite3.DatabaseError: rows = []
    quarantine(root,old,rows)
    return True


def check_connection(root, path, conn):
    """Owns/cleans the connection if integrity fails; unknown is never renamed."""
    if healthy(conn): return conn
    known = identity(conn)
    try: rows = pending(conn) if known else []
    except sqlite3.DatabaseError: rows = []
    finally: conn.close()
    if not known: up.fail('OURA_RAW_RECOVERY_UNKNOWN')
    quarantine(root,path,rows)
    from oura_raw import DDL, SCHEMA_ID
    return up.open_db(path,SCHEMA_ID,DDL,root=root)


@contextmanager
def archive_view(root, path):
    """Read an immutable archive, recovering only an isolated disposable copy."""
    members = recovery.members(root,path)
    if not members:
        with up.readonly(root,path) as c: yield c
        return
    with tempfile.TemporaryDirectory(prefix='oura-archive-view-') as temporary:
        directory = Path(temporary).resolve()
        for src in [path]+members:
            up._safe(root,src)
            dst = directory/('raw.db'+src.name[len(path.name):])
            fd = os.open(src,os.O_RDONLY|os.O_NOFOLLOW)
            out = os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'rb') as inp,os.fdopen(out,'wb') as f:
                while data:=inp.read(1024*1024): f.write(data)
        with closing(up.connect(directory/'raw.db')) as c:
            c.execute('SELECT schema_id,ddl_sha256 FROM schema_meta').fetchall()
        # Integrity may be bad: callers enumerate each readable table and
        # explicitly report failures. Never claim a damaged archive is repaired.
        with up.readonly(directory,directory/'raw.db') as c: yield c
