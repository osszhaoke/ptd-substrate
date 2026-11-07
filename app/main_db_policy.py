"""Lifecycle of the two per-instance main databases. No other store uses this policy."""
from contextlib import closing, ExitStack
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import tempfile
import threading

from cards import open_startrack
from h1_common import H1Error, load_instance
from sqlite_util import KnownJournalMismatch, assert_inside
from startorch_outbox import open_startorch

MIB = 1024 * 1024


@dataclass(frozen=True)
class Pressure:
    state: str
    outstanding: int | None
    paused: bool


def pressure(row, page_size, previous=False):
    if (not row or len(row) != 3 or any(type(n) is not int for n in row)
            or row[0] not in (0, 1) or not 0 <= row[2] <= row[1]
            or type(page_size) is not int or page_size <= 0):
        return Pressure('UNKNOWN', None, previous)
    outstanding = (row[1] - row[2]) * page_size
    paused = outstanding >= 256 * MIB or (previous and outstanding >= 64 * MIB)
    state = 'PAUSED' if paused else 'WARNING' if outstanding >= 64 * MIB else 'OK'
    return Pressure(state, outstanding, paused)


def truncate_drained(conn):
    """Private maintenance primitive. Caller has stopped admissions and drained owners."""
    if conn.in_transaction:
        raise RuntimeError('checkpoint inside transaction')
    row = conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    if row != (0, 0, 0):
        raise sqlite3.OperationalError('checkpoint did not drain')


def backup_main(ctx, opener, folder):
    """Owner-only SQLite backup; publish a completed file in its own private directory."""
    folder = Path(folder)
    assert_inside(ctx.root, folder)
    folder.mkdir(mode=0o700, exist_ok=True)
    directory = Path(tempfile.mkdtemp(dir=folder, prefix='main-snapshot-'))
    working, final = directory / 'working.db', directory / 'snapshot.db'
    fd = os.open(working, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(opener(ctx)) as src, closing(sqlite3.connect(working, isolation_level=None)) as target:
            src.backup(target)
            if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise sqlite3.DatabaseError('backup integrity check failed')
            truncate_drained(target)
        assert_inside(ctx.root, working)
        with working.open('rb') as handle:
            os.fsync(handle.fileno())
        os.replace(working, final)
        for parent in (directory, folder):
            fd = os.open(parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return final
    finally:
        for suffix in ('', '-wal', '-shm', '-journal'):
            Path(str(working) + suffix).unlink(missing_ok=True)
        if not final.exists():
            directory.rmdir()


class Stores:
    """One serving application's owner. No SQL is performed under the observation lock."""
    def __init__(self, app, specs, factory):
        self.instances = {}
        self.rejected = set()
        self._keep = ExitStack()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._observed = {}
        self._thread = None
        self._log = app.log
        try:
            for spec in specs:
                root = app.root / spec['id']
                assert_inside(app.root, root)
                assert_inside(app.root, root / 'instance.json')
                if root.exists():
                    ctx = load_instance(root)
                    old = False
                    for opener in (open_startorch, open_startrack):
                        try:
                            opener(ctx).close()
                        except KnownJournalMismatch:
                            old = True
                    if old:
                        self.rejected.update((spec['id'], spec['key']))
                        continue
                inst = factory(app, spec)
                self.instances[spec['key']] = inst
                # SQLite may otherwise create its shared scratch files on an Oura
                # read-only open. Keep the writer-initialized scratch alive.
                self._keep.enter_context(closing(open_startorch(inst.ctx)))
                self._keep.enter_context(closing(open_startrack(inst.ctx)))
            for inst in self.instances.values():
                inst.startup()
        except BaseException:
            self._keep.close()
            raise

    def resolve(self, live, key):
        if key in live:
            return live[key]
        for inst in live.values():
            if inst.ctx.instance_id == key:
                return inst
        if key in self.rejected:
            raise KnownJournalMismatch('DB_JOURNAL_MODE_MISMATCH', 'DB_JOURNAL_MODE_MISMATCH')
        raise H1Error('INSTANCE_UNKNOWN', str(key))

    def snapshot(self, ctx, which):
        with self._lock:
            return self._observed.get((ctx.root, which), Pressure('UNKNOWN', None, False))

    def once(self):
        for inst in tuple(self.instances.values()):
            for which, opener in (('torch', open_startorch), ('track', open_startrack)):
                ctx = inst.ctx
                prior = self.snapshot(ctx, which)
                try:
                    with closing(opener(ctx)) as conn:
                        if conn.in_transaction:
                            raise RuntimeError('checkpoint inside transaction')
                        row = conn.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
                        size = conn.execute('PRAGMA page_size').fetchone()[0]
                        observation = pressure(row, size, prior.paused)
                except (OSError, sqlite3.Error, H1Error):
                    observation = Pressure('UNKNOWN', None, prior.paused)
                with self._lock:
                    self._observed[ctx.root, which] = observation
                if observation.state != prior.state or observation.state == 'UNKNOWN':
                    self._log('main_wal_' + observation.state.lower(), ctx.instance_id, which)

    def _maintain(self):
        while not self._stop.wait(60):
            self.once()

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(target=self._maintain, name='PTDS-main-wal', daemon=True)
            self._thread.start()

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self._keep.close()

