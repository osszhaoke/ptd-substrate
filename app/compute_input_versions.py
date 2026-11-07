"""Task-owned input leases. No worker wiring, global cache, SQL or upper lock.

Capture/revalidation require the caller's input Owner (A, and A -> D for
CardSetup). Only in-process append/atomic-replacement writers are supported;
metadata is a version check, not proof against external in-place modification.
Capture performs metadata/open operations only. Reading and parsing are outside
those locks. A successful EOF is NOT a successfully parsed record boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import stat
import threading
from types import MappingProxyType

from sqlite_util import assert_inside
from h1_common import H1Error


class InputCapacity(ValueError):
    pass


class StaleInput(ValueError):
    pass


@dataclass(frozen=True)
class ProjectionLimits:
    max_bytes: int = 1024 * 1024
    max_nodes: int = 100000
    max_keys: int = 20000
    max_depth: int = 64


def _thaw(value, memo):
    if type(value) not in (MappingProxyType, tuple):
        return value
    key = id(value)
    if key in memo:
        return memo[key]
    out = {} if type(value) is MappingProxyType else []
    memo[key] = out
    if type(value) is MappingProxyType:
        out.update((k, _thaw(v, memo)) for k, v in value.items())
    else:
        out.extend(_thaw(v, memo) for v in value)
    return out


@dataclass(frozen=True)
class PrivateValue:
    value: object

    def copy(self):
        """A new mutable JSON projection, preserving aliases within this copy."""
        return _thaw(self.value, {})


def private_value(value, *, limits=ProjectionLimits()):
    """Bounded private JSON graph; exact builtins only, no instance/config reads."""
    if any(type(n) is not int or n < 1 for n in
           (limits.max_bytes, limits.max_nodes, limits.max_keys, limits.max_depth)):
        raise ValueError('INPUT_VERSION_LIMITS')
    memo, active = {}, set()
    used_bytes = nodes = keys = 0

    def visit(item, depth):
        nonlocal used_bytes, nodes, keys
        nodes += 1
        if nodes > limits.max_nodes or depth > limits.max_depth:
            raise InputCapacity('INPUT_VERSION_CAPACITY')
        kind = type(item)
        if kind in (dict, list):
            identity = id(item)
            if identity in active:
                raise ValueError('INPUT_VERSION_CYCLE')
            if identity in memo:
                return memo[identity]
            active.add(identity)
            if kind is dict:
                keys += len(item)
                if keys > limits.max_keys:
                    raise InputCapacity('INPUT_VERSION_CAPACITY')
                out = {}
                for key, child in item.items():
                    if type(key) is not str:
                        raise ValueError('INPUT_VERSION_TYPE')
                    visit(key, depth + 1)
                    out[key] = visit(child, depth + 1)
                frozen = MappingProxyType(out)
            else:
                frozen = tuple(visit(child, depth + 1) for child in item)
            active.remove(identity)
            memo[identity] = frozen
            return frozen
        if item is None or kind in (str, bool, int, float):
            if kind is float and not math.isfinite(item):
                raise ValueError('INPUT_VERSION_TYPE')
            used_bytes += len(item.encode('utf-8')) if kind is str else len(str(item))
            if used_bytes > limits.max_bytes:
                raise InputCapacity('INPUT_VERSION_CAPACITY')
            return item
        raise ValueError('INPUT_VERSION_TYPE')

    try:
        return PrivateValue(visit(value, 0))
    finally:
        # Never retain source objects or memo on success or exception.
        active.clear()
        memo.clear()


def _signature(info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise H1Error('PATH_OUTSIDE_INSTANCE', 'input is not a single-linked regular file')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_nlink)


def _root_identity(root):
    info = Path(root).stat()
    if not stat.S_ISDIR(info.st_mode):
        raise H1Error('PATH_OUTSIDE_INSTANCE', 'instance root is not a directory')
    return (info.st_dev, info.st_ino)


@dataclass(frozen=True)
class FileVersion:
    root: str
    path: str
    root_identity: tuple
    signature: tuple | None

    def require_current(self):
        """Caller must hold the same Owner(s) as capture, through later use."""
        assert_inside(Path(self.root), Path(self.path))
        try:
            root_identity = _root_identity(self.root)
            try:
                current = _signature(Path(self.path).stat())
            except FileNotFoundError:
                current = None
        except FileNotFoundError as exc:
            raise StaleInput('INPUT_VERSION_STALE') from exc
        if root_identity != self.root_identity or current != self.signature:
            raise StaleInput('INPUT_VERSION_STALE')


class FileLease:
    """Creating thread owns this one-shot FD, including closure after errors."""
    def __init__(self, fd, version, context=None):
        self._fd, self.version, self.context = fd, version, context
        self._thread = threading.get_ident()
        self.closed = False

    def _own(self):
        if threading.get_ident() != self._thread:
            raise RuntimeError('INPUT_LEASE_THREAD')

    def close(self):
        self._own()
        if not self.closed:
            self.closed = True
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None

    def __enter__(self):
        self._own()
        if self.closed:
            raise RuntimeError('INPUT_LEASE_CLOSED')
        return self

    def __exit__(self, *args):
        self.close()

    def read_text(self, *, block_size=65536):
        self._own()
        if self.closed:
            raise RuntimeError('INPUT_LEASE_CLOSED')
        try:
            if type(block_size) is not int or not 1 <= block_size <= 1024 * 1024:
                raise ValueError('INPUT_VERSION_BLOCK_SIZE')
            remaining = self.version.signature[2] if self.version.signature else 0
            chunks = []
            while remaining:
                chunk = os.read(self._fd, min(block_size, remaining))
                if not chunk:
                    raise StaleInput('INPUT_PREFIX_SHORT')
                chunks.append(chunk)
                remaining -= len(chunk)
            # Match Path.read_text universal-newline conversion before the old
            # parser; decode the entire prefix before folding any JSON rows.
            return b''.join(chunks).decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
        finally:
            self.close()


def capture_prefix(root, path, *, byte_limit, context=None):
    """Read-only short capture. Caller supplies the explicit per-task bound."""
    if type(byte_limit) is not int or byte_limit < 1:
        raise ValueError('INPUT_VERSION_BYTE_LIMIT')
    root = Path(os.path.abspath(root))
    path = Path(os.path.abspath(path))
    assert_inside(root, path)
    root_id = _root_identity(root)
    fd = None
    try:
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return FileLease(None, FileVersion(str(root), str(path), root_id, None), context)
        signature = _signature(os.fstat(fd))
        assert_inside(root, path)
        if signature != _signature(path.stat()):
            raise StaleInput('INPUT_VERSION_STALE')
        if signature[2] > byte_limit:
            raise InputCapacity('INPUT_VERSION_CAPACITY')
        return FileLease(fd, FileVersion(str(root), str(path), root_id, signature), context)
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise


@dataclass(frozen=True)
class FileInput:
    version: FileVersion
    data: PrivateValue

    @property
    def value(self):
        return self.data.value

    def copy(self):
        return self.data.copy()
