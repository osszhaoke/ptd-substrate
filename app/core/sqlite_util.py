"""SQLite helpers used by both sides (not part of the H1 contract; copy freely).

Rules enforced here:
- Every table is append-only: BEFORE UPDATE / BEFORE DELETE triggers abort.
- recursive_triggers is ON, otherwise INSERT OR REPLACE would delete rows without firing the
  delete trigger. This is a per-connection setting, so ALL access must go through connect():
  a test forbids sqlite3.connect anywhere else. The triggers guard against our own code, not
  against an arbitrary same-user SQL client (out of the threat model).
- A database is bound to exactly one DDL, checked against the ACTUAL schema objects in
  sqlite_master (tables, indexes, triggers), not only against a recorded digest. A schema
  change this week means a NEW instance, never a migration.
- Database files must resolve inside their instance directory: no symlink escapes, no hard links.
"""
from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from h1_common import H1Error, sha256_hex


def append_only_ddl(tables) -> str:
    parts = []
    for table in tables:
        parts.append(
            f"CREATE TRIGGER {table}_no_update BEFORE UPDATE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\n"
            f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} "
            f"BEGIN SELECT RAISE(ABORT, 'APPEND_ONLY'); END;\n")
    return "".join(parts)


def assert_inside(root: Path, path: Path) -> None:
    """path must lie under root, no component below root may be a symlink, no hard-linked file.

    root itself may be a symlink (e.g. the instances folder on another volume).
    """
    root_abs, target = Path(os.path.abspath(root)), Path(os.path.abspath(path))
    if root_abs != target and root_abs not in target.parents:
        raise H1Error("PATH_OUTSIDE_INSTANCE", "path is not under the instance directory")
    probe = root_abs
    for part in target.relative_to(root_abs).parts:
        probe = probe / part
        if probe.is_symlink():
            raise H1Error("PATH_OUTSIDE_INSTANCE", "symlink in instance path")
    try:
        info = target.stat() if target == root_abs else target.lstat()
    except FileNotFoundError:
        return  # A not-yet-created or removed SQLite sidecar is allowed.
    if stat.S_ISLNK(info.st_mode):
        raise H1Error("PATH_OUTSIDE_INSTANCE", "symlink in instance path")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise H1Error("PATH_OUTSIDE_INSTANCE", "hard-linked file")


def connect(path: Path) -> sqlite3.Connection:
    if isinstance(path, _ExistingMain):
        conn = sqlite3.connect(path.absolute().as_uri() + '?mode=rw', uri=True, isolation_level=None)
    else:
        conn = sqlite3.connect(str(path), isolation_level=None)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA recursive_triggers = ON")
        return conn
    except BaseException:
        conn.close()
        raise


@contextmanager
def transaction(conn: sqlite3.Connection):
    """BEGIN IMMEDIATE takes the write lock up front, so read-then-write logic is serialized."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException as failure:
        # COMMIT can fail while the transaction is still active. Do not let
        # later status/error writes observe or join that uncommitted work.
        try:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
        except BaseException as cleanup_error:
            # A connection with uncertain cleanup must not be reused. Keep
            # the original failure and any cleanup failure in the error chain.
            try:
                conn.close()
            except BaseException as close_error:
                raise failure from close_error
            raise failure from cleanup_error
        raise


def _schema_objects(conn) -> set:
    return set(conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall())


def open_db(path: Path, schema_id: str, ddl: str, *, root: Path) -> sqlite3.Connection:
    """Opens (or creates) a database inside `root`, bound to (schema_id, ddl)."""
    assert_inside(root, path)
    ddl_sha = sha256_hex(ddl.encode("utf-8"))
    meta = ("CREATE TABLE schema_meta (schema_id TEXT NOT NULL, ddl_sha256 TEXT NOT NULL);\n"
            + append_only_ddl(["schema_meta"]))
    reference = sqlite3.connect(":memory:")
    reference.executescript(ddl + meta)
    expected = _schema_objects(reference)
    reference.close()
    conn = connect(path)
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_meta'").fetchone():
            row = conn.execute("SELECT schema_id, ddl_sha256 FROM schema_meta").fetchone()
            if row != (schema_id, ddl_sha) or _schema_objects(conn) != expected:
                raise H1Error("DB_SCHEMA_MISMATCH", "create a new instance instead of migrating")
            return conn
        if conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]:
            raise H1Error("DB_NOT_EMPTY", "existing database without schema_meta")
        conn.executescript("BEGIN IMMEDIATE;\n" + ddl + meta
                           + f"INSERT INTO schema_meta VALUES ('{schema_id}', '{ddl_sha}');\nCOMMIT;\n")
        return conn
    except BaseException:
        conn.close()
        raise

class _ExistingMain(type(Path())):
    """Keep the physical path available to connection instrumentation; prohibit implicit creation."""


class KnownJournalMismatch(H1Error):
    """Only raised after the complete expected main schema has been verified."""


def _main_nodes(root, path):
    for suffix in ('', '-wal', '-shm', '-journal'):
        node = Path(str(path) + suffix)
        assert_inside(root, node)
        try:
            info = node.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise H1Error('PATH_OUTSIDE_INSTANCE', 'unsafe database file')
    if not path.exists() and any(os.path.lexists(str(path) + s) for s in ('-journal','-wal','-shm')):
        raise H1Error('DB_SCHEMA_MISMATCH', 'orphan database sidecar')


@lru_cache(maxsize=2)
def _main_schema(schema_id, ddl):
    meta = ("CREATE TABLE schema_meta (schema_id TEXT NOT NULL, ddl_sha256 TEXT NOT NULL);\n"
            + append_only_ddl(["schema_meta"]))
    ref = sqlite3.connect(':memory:')
    try:
        ref.executescript(ddl + meta)
        return frozenset(_schema_objects(ref)), meta, sha256_hex(ddl.encode())
    finally:
        ref.close()


def open_main_db(path, schema_id, ddl, *, root, create=False, readonly=False):
    """Two main stores only; create is a one-time initialization capability."""
    path = Path(path)
    _main_nodes(root, path)
    expected, meta, digest = _main_schema(schema_id, ddl)
    if create:
        if readonly:
            raise ValueError('read-only main database creation')
        fd = os.open(path, os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | os.O_WRONLY, 0o600)
        os.close(fd)
    before = path.stat()
    # Do not open/close a raw descriptor on a live SQLite file: that can
    # release process-owned POSIX locks. SQLite handles all file opens.
    legacy_journal = not create and Path(str(path) + '-journal').exists()
    if readonly or legacy_journal:
        # Allow observation only when WAL access won't need to create scratch files.
        # A closed/checkpointed WAL needs a stable, offline view or an explicitly owned
        # writer to supply the two sidecars. Never set immutable on a live main DB.
        if not legacy_journal and not all(Path(str(path) + suffix).is_file() for suffix in ('-shm', '-wal')):
            raise OSError('read-only WAL scratch unavailable')
        uri = path.absolute().as_uri() + '?mode=ro&readonly_shm=1'
        conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    else:
        conn = connect(_ExistingMain(path))
    try:
        if not os.path.samestat(before, path.stat()):
            raise H1Error('PATH_OUTSIDE_INSTANCE','database replaced while opening')
        if create:
            if conn.execute('PRAGMA journal_mode=WAL').fetchone() != ('wal',):
                raise H1Error('DB_JOURNAL_MODE_MISMATCH','DB_JOURNAL_MODE_MISMATCH')
            conn.executescript('BEGIN IMMEDIATE;\n' + ddl + meta
                               + f"INSERT INTO schema_meta VALUES ('{schema_id}', '{digest}');\nCOMMIT;")
        if _schema_objects(conn) != expected or conn.execute(
                'SELECT schema_id,ddl_sha256 FROM schema_meta LIMIT 2').fetchall() != [(schema_id, digest)]:
            raise H1Error('DB_SCHEMA_MISMATCH','create a new instance instead of migrating')
        if conn.execute('PRAGMA journal_mode').fetchone() != ('wal',):
            raise KnownJournalMismatch('DB_JOURNAL_MODE_MISMATCH','DB_JOURNAL_MODE_MISMATCH')
        if legacy_journal and not readonly:
            raise H1Error('DB_SCHEMA_MISMATCH', 'unexpected rollback journal on WAL database')
        if readonly:
            conn.execute('PRAGMA query_only=ON')
        else:
            conn.execute('PRAGMA synchronous=FULL')
            conn.execute('PRAGMA wal_autocheckpoint=1000')
            conn.execute('PRAGMA journal_size_limit=4194304')
        _main_nodes(root, path)
        return conn
    except BaseException:
        conn.close()
        raise

