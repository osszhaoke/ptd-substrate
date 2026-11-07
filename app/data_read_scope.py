"""Request-owned current-data read cut. Capture/publish use A; scans use no A.

Close every read transaction before reacquiring A. Otherwise a saving thread
holding A while committing can wait for this reader, forming SQL -> A deadlock.
No worker, credentials, persistent cache or new lock is owned here.
"""
from contextlib import ExitStack
from copy import deepcopy
import io
import os
import stat
from types import SimpleNamespace

import data_read
import data_read_http
import bridge
import instance_services
import data_read_cache
from h1_common import H1Error
from read_view import read_connection
from sqlite_util import assert_inside
from startrack_import import import_cursor


class Changed(Exception):
    """Internal retry signal; the public error remains DATA_VIEW_CHANGED."""


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink, info.st_mode)


def file_identity(root, path):
    assert_inside(root, path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise H1Error('PATH_OUTSIDE_INSTANCE', 'source is not a single regular file')
    return _identity(info)


class Prefix:
    """One regular source fd with a fixed byte extent, never a credential path."""
    def __init__(self, root, path, stack):
        self.path = path
        self.token = file_identity(root, path)
        self.fd = None
        if self.token is not None:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            stack.callback(os.close, fd)
            self.fd = fd
            if _identity(os.fstat(fd)) != self.token or file_identity(root, path) != self.token:
                raise Changed()

    def text(self):
        if self.fd is None:
            return ''
        # Read precisely the captured prefix. Do not follow an atomic replacement.
        parts, remaining = [], self.token[2]
        while remaining:
            block = os.read(self.fd, min(remaining, 65536))
            if not block:
                raise Changed()
            parts.append(block); remaining -= len(block)
        if _identity(os.fstat(self.fd)) != self.token:
            raise Changed()
        return b''.join(parts).decode('utf-8')


class Capture:
    """Created under A; read and close outside A; validate/publish under A."""
    def __init__(self, app, q, gene_reader):
        self.stack = ExitStack()
        self.closed = False
        try:
            self.app, self.key = app, q['key']
            self.owner = app.inst(self.key)
            owner = self.owner
            self.ctx, self.dictionary = owner.ctx, app.registry.current
            stores = getattr(app, 'main_stores', None)
            if stores is not None and stores.snapshot(self.ctx, 'track').paused:
                raise Changed()
            self.nature = owner.nature
            self.policy = deepcopy(owner.spec.get('archived_streams'))
            self.groups = dict(data_read._GROUPS)
            self.root = str(self.ctx.root.resolve())
            self.gene_reader = gene_reader(owner)
            self.gene = self.gene_reader.asset_capture(lambda root, path: Prefix(root, path, self.stack))
            nature = owner.nature or ('REAL' if 'REAL' in owner.ctx.accept else 'SYNTHETIC')
            self.bridge = app.bridge(owner) if nature == 'REAL' else None
            self.receipt = self.bridge.receipt_capture(lambda root, path: Prefix(root, path, self.stack)) if self.bridge else None
            self.conn = self.stack.enter_context(read_connection(data_read.open_startrack, self.ctx))
            # BEGIN alone is deferred: this SELECT actually pins the SQLite cut.
            self.cursor = import_cursor(self.conn)
            self.db = data_read._stat(self.ctx.startrack_db)
            self.cache_before = getattr(owner, '_data_read_pages', None)
            registry = SimpleNamespace(current=SimpleNamespace(version=self.dictionary.version, codes=dict(self.dictionary.codes)))
            self.inst = SimpleNamespace(ctx=self.ctx, nature=self.nature,
                spec={'archived_streams':deepcopy(self.policy)}, app=SimpleNamespace(registry=registry),
                _data_read_connection=self.conn, _data_read_identity=id(owner),
                _data_read_dictionary_identity=id(self.dictionary), _data_read_db=self.db,
                _data_read_groups=self.groups, _data_read_root=self.root)
            data_read_cache.capture(owner, self.inst)
        except BaseException:
            self.close()
            raise

    def extras(self, q):
        # Capture creates metadata handles under A; source parsing is lazy here.
        return data_read_http._prepare_sources(self.inst, q,
            lambda: bridge._read_document(self.receipt.text)["receipts"],
            lambda: instance_services._asset_rows(io.StringIO(self.gene.text(), newline=None)))

    def close(self):
        try:
            self.stack.close()
        finally:
            self.closed = True

    def valid(self):
        assert self.closed, 'READ_TRANSACTION_STILL_OPEN'
        app, owner = self.app, self.owner
        if (app.inst(self.key) is not owner or owner.ctx != self.ctx or owner.nature != self.nature
                or app.registry.current is not self.dictionary
                or owner.spec.get('archived_streams') != self.policy or data_read._GROUPS != self.groups
                or str(owner.ctx.root.resolve()) != self.root):
            return False
        if self.gene_reader.asset_capture(file_identity) != self.gene.token:
            return False
        if self.bridge and self.bridge.receipt_capture(file_identity) != self.receipt.token:
            return False
        db = data_read._stat(self.ctx.startrack_db)
        if (db[:2] if db else None) != (self.db[:2] if self.db else None):
            return False
        with read_connection(data_read.open_startrack, self.ctx) as conn:
            return import_cursor(conn) == self.cursor

    def publish_cache(self):
        # Cache is optional. A later publisher owns its bytes; never overwrite it.
        if getattr(self.owner, '_data_read_pages', None) is self.cache_before:
            state = getattr(self.inst, '_data_read_pages', None)
            if state is not None:
                self.owner._data_read_pages = (state[0], dict(state[1]))
