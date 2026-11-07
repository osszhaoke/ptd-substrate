"""Inspect and recover journal copies; archive operations are restricted to /1."""
from contextlib import closing
import json
import os
from pathlib import Path

import oura_raw_upgrade as up
from sqlite_util import assert_inside

SIDECARS = ('-journal', '-wal', '-shm')
RECOVERY = 'raw.db.recovery-tmp'


def members(root, path):
    return [p for p in (up._safe(root, Path(str(path) + s)) for s in SIDECARS) if p.exists()]


def area(root, old):
    directory = old.parent / RECOVERY
    assert_inside(root, directory)
    if directory.exists() and not directory.is_dir():
        up.fail('OURA_RAW_PATH_UNSAFE')
    return directory


def clean(root, old):
    """Only our fixed names; never recursive, never remove unrelated files."""
    directory = area(root, old)
    if not directory.exists():
        return
    for name in ('raw.db', 'schema.db', 'swap.json') + tuple('raw.db' + s for s in SIDECARS):
        p = up._safe(root, directory / name)
        if p.exists(): p.unlink()
    up._fsync_dir(directory)


def recover(root, old, sidecars):
    if any(p.name.endswith(('-wal', '-shm')) for p in sidecars):
        up.fail('OURA_RAW_UPGRADE_WAL_PRESENT')
    directory = area(root, old)
    directory.mkdir(mode=0o700, exist_ok=True)
    source = directory / 'raw.db'
    up._copy_bytes(root, old, source)
    for p in sidecars:
        up._copy_bytes(root, p, directory / p.name)
    # SQLite performs its own rollback. No caller SQL writes the recovery copy.
    with closing(up.connect(source)) as c:
        c.execute('SELECT schema_id,ddl_sha256 FROM schema_meta').fetchall()
    # A non-hot journal can remain. Only SQLite/schema/integrity decide usability.
    up.version(root, source)
    with up.readonly(root, source) as c:
        if c.execute('PRAGMA source.integrity_check').fetchall() != [('ok',)]:
            up.fail('OURA_RAW_RECOVERY_INTEGRITY')
    return source


def original_version(root, old):
    """Inspect only metadata on a separate base-file copy after recovery fails.

    This does not claim its business rows are recovered. If strict /1 schema
    cannot be proven, the caller must preserve the originals and fail closed.
    """
    directory = area(root, old)
    directory.mkdir(mode=0o700, exist_ok=True)
    probe = directory / 'schema.db'
    up._copy_bytes(root, old, probe)
    return up.version(root, probe)


def archive(root, old, sidecars, kind, *, move=False):
    target = up._unique(old.parent, kind)
    # Base name is also the group id. Matching suffixes remain adjacent.
    for p in [old] + sidecars:
        dest = Path(str(target) + p.name[len(old.name):])
        if move:
            up._safe(root, p); assert_inside(root, dest)
            if dest.exists(): up.fail('OURA_RAW_ARCHIVE_CONFLICT')
            os.rename(p, dest)
            up._fsync_dir(old.parent)
        else:
            up._copy_bytes(root, p, dest)
    return target


def replace(root, old, tmp, sidecars, backup, *, published):
    if not sidecars:
        os.replace(tmp, old); published(); up._fsync_dir(old.parent)
        return
    # Persist a recovery record BEFORE detaching the old journal. A process
    # exit in this short multi-file window restores it before the next open.
    directory = area(root, old); directory.mkdir(mode=0o700, exist_ok=True)
    marker = directory / 'swap.json'
    record = {'old':up.file_digest(root, old), 'new':up.file_digest(root, tmp),
              'backup':backup.name, 'sidecars':{p.name:up.file_digest(root,p) for p in sidecars}}
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(record, f); f.flush(); os.fsync(f.fileno())
    up._fsync_dir(directory)
    for p in sidecars: p.unlink()
    up._fsync_dir(old.parent)
    up._checkpoint('journals_detached')
    os.replace(tmp, old); published(); up._fsync_dir(old.parent)
    marker.unlink(); up._fsync_dir(directory)


def resume_swap(root, old):
    marker = up._safe(root, area(root, old) / 'swap.json')
    if not marker.exists(): return
    fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f: record = json.load(f)
    current = up.file_digest(root, old)
    if current not in (record['old'], record['new']):
        up.fail('OURA_RAW_RECOVERY_CONFLICT')
    backup = record['backup']
    if not backup.startswith('raw.db.v1-backup-') or Path(backup).name != backup:
        up.fail('OURA_RAW_RECOVERY_CONFLICT')
    for name, digest in record['sidecars'].items():
        if name not in tuple('raw.db' + s for s in SIDECARS): up.fail('OURA_RAW_RECOVERY_CONFLICT')
        p = up._safe(root, old.parent / name)
        if current == record['old']:
            source = old.parent / (backup + name[len(old.name):])
            if up.file_digest(root, source) != digest: up.fail('OURA_RAW_RECOVERY_CONFLICT')
            if not p.exists(): up._copy_bytes(root, source, p)
            elif up.file_digest(root, p) != digest: up.fail('OURA_RAW_RECOVERY_CONFLICT')
        elif p.exists():
            if up.file_digest(root, p) != digest: up.fail('OURA_RAW_RECOVERY_CONFLICT')
            p.unlink()
    up._fsync_dir(old.parent)
    marker.unlink(); up._fsync_dir(marker.parent)
