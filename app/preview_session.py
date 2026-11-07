"""Registered original and evidence ZIP reads. A owns capture, invalidation and publication."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat
import sys
import tempfile
import threading

import evidence_navigation
import evidence_pack
from h1_common import H1Error
import recognize


COPY_BYTES = 64 * 1024**2
_copy_slot = threading.Lock()  # Shared by all instances in this process, never waited on under A.
_TYPES = {"png":"image/png", "jpg":"image/jpeg", "jpeg":"image/jpeg", "pdf":"application/pdf",
          "heic":"image/heic", "tif":"image/tiff", "tiff":"image/tiff", "webp":"image/webp"}


class UnsafePath(OSError):
    """A protected directory or file failed its local identity rules."""


def _changed():
    return H1Error("DATA_VIEW_CHANGED", "数据已更新，请重新读取当前筛选")


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _view(root, relative, pack):
    path = root
    for part in (None, *relative.parts):
        if part is not None:
            path = path / part
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise UnsafePath("unsafe path")
        if path != root / relative and not stat.S_ISDIR(info.st_mode):
            raise UnsafePath("unsafe directory")
    if not stat.S_ISREG(info.st_mode) or (pack and info.st_nlink != 1):
        raise UnsafePath("unsafe file")
    return _identity(info)


def _open_relative(root, relative):
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    if os.open not in os.supports_dir_fd or not hasattr(os, 'O_DIRECTORY'):
        # Some wrappers also hide supports_dir_fd. Both path and opened-file identity
        # are checked before any read. Prefer the component-wise open on POSIX.
        if os.name != "posix":
            return os.open(root / relative, flags | getattr(os, "O_NOFOLLOW", 0))
    dflags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open(root, dflags)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, dflags, dir_fd=parent)
            os.close(parent)
            parent = child
        return os.open(relative.name, flags | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)


def _pack_boundary(configured_root):
    # Resolve only the trusted configured root. Never resolve a child link.
    try:
        root = Path(configured_root).resolve(strict=True)
    except RuntimeError:
        raise UnsafePath("unsafe configured root") from None
    stamps = []
    for folder in (root, root / "evidence"):
        item = folder.lstat()
        if not stat.S_ISDIR(item.st_mode) or getattr(item, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise UnsafePath("unsafe evidence directory")
        stamps.append((item.st_dev, item.st_ino))
    return root, tuple(stamps)


class Session:
    def __init__(self, app, root, relative, resolve, pack):
        self.app, self.root, self.relative, self.resolve = app, root, relative, resolve
        self.pack = pack
        self.generation = 0
        self.path, self.registration, checked = resolve()
        self.boundary = _pack_boundary(root) if pack else None
        physical_root = self.boundary[0] if pack else root
        self.initial = _view(physical_root, relative, pack)
        if checked is not None and _identity(checked) != self.initial:
            raise _changed()
        fd = _open_relative(physical_root, relative)
        try:
            if _identity(os.fstat(fd)) != self.initial or (pack and _pack_boundary(root) != self.boundary):
                raise _changed()
            self.file = os.fdopen(fd, "rb")
        except BaseException:
            os.close(fd)
            raise

    def valid_at_publish(self):
        # Caller holds A; bytes have been collected and the source FD has been closed.
        try:
            path, registration, checked = self.resolve()
            return (self.generation == 0 and (path, registration) == (self.path, self.registration)
                    and (checked is None or _identity(checked) == self.initial)
                    and (not self.pack or _pack_boundary(self.root) == self.boundary)
                    and _view(self.boundary[0] if self.pack else self.root, self.relative, self.pack) == self.initial)
        except (H1Error, OSError):
            return False


def invalidate(app, path):
    """Called at intent approval, under A. Currently exercised only by the test eraser."""
    with app.lock:
        for session in getattr(app, "_preview_sessions", ()):
            if session.path == path:
                session.generation += 1


@contextmanager
def _session(app, q, pack):
    with app.lock:
        if pack:
            name = q.get("name", "")
            if not evidence_pack.NAME_RE.fullmatch(name):
                raise FileNotFoundError()
            root = app.root
            relative = Path("evidence") / name
            def resolve():
                return root / relative, name, None
        else:
            inst = app.inst(q["key"])
            name = q.get("name", "")
            def resolve():
                return evidence_navigation.original_reference(inst, name)
            root = Path(inst.ctx.root)
            # resolve validates name, registry and the registered OCR hardlink pair.
            relative = Path("startorch/originals") / name
        # The generator writes the complete evidence archive under A. Open and fstat
        # here under that SAME lock. Moving generation out requires atomic publication.
        try:
            node = Session(app, root, relative, resolve, pack)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                raise UnsafePath() from None
            raise
        if not hasattr(app, "_preview_sessions"):
            app._preview_sessions = set()
        app._preview_sessions.add(node)
    try:
        yield node
    finally:
        try:
            node.file.close()
        finally:
            with app.lock:
                app._preview_sessions.discard(node)


@contextmanager
def _preview_directory(*, create):
    import fcntl
    folder = Path(tempfile.gettempdir()) / f"ptds-vision-preview-{os.getuid()}"
    if create:
        folder.mkdir(mode=0o700, exist_ok=True)
    owner = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(owner)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise UnsafePath("unsafe preview directory")
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield folder, owner
    finally:
        os.close(owner)


def _remove_stale(owner):
    try:
        stale = os.stat("source.pdf", dir_fd=owner, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(stale.st_mode) or stale.st_nlink != 1 or stale.st_uid != os.getuid():
        raise UnsafePath("unsafe leftover")
    os.unlink("source.pdf", dir_fd=owner)
    return True


def clean_preview_on_startup():
    """Reclaim only this user's abandoned copy. A live owner keeps its lease."""
    if sys.platform != "darwin":
        return False
    try:
        with _preview_directory(create=False) as (_, owner):
            return _remove_stale(owner)
    except (FileNotFoundError, BlockingIOError, UnsafePath):
        return False
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR, errno.EACCES, errno.EPERM):
            return False
        raise


@contextmanager
def _private_pdf(file, size):
    if sys.platform != "darwin" or size > COPY_BYTES or not _copy_slot.acquire(False):
        raise RuntimeError("ORIGINAL_PREVIEW_UNAVAILABLE")
    try:
        with _preview_directory(create=True) as (folder, owner):
            _remove_stale(owner)
            name = "source.pdf"
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=owner)
            try:
                with os.fdopen(fd, "wb") as dest:
                    remaining = size
                    while remaining:
                        chunk = file.read(min(1024**2, remaining))
                        if not chunk:
                            raise _changed()
                        dest.write(chunk)
                        remaining -= len(chunk)
                    if file.read(1):
                        raise _changed()
                yield folder / name
            finally:
                os.unlink(name, dir_fd=owner)
    finally:
        _copy_slot.release()


def _render(node, value):
    page = int(value)
    if node.path.suffix.lower() != ".pdf" or not 1 <= page <= 100000:
        raise ValueError("ORIGINAL_PREVIEW_PAGE")
    with _private_pdf(node.file, node.initial[2]) as copy:
        return recognize.preview_pdf(copy, page)


def download(handler, app, q, *, pack):
    try:
        with _session(app, q, pack) as node:
            with node.file:
                if not pack and "preview_page" in q:
                    try:
                        body = _render(node, q["preview_page"])
                    except (ValueError, RuntimeError, OSError):
                        return handler._json(422, {"error": "ORIGINAL_PREVIEW_UNAVAILABLE"})
                    kind = "image/png"
                else:
                    body = node.file.read()
                    kind = "application/zip" if pack else _TYPES.get(node.path.suffix[1:], "application/octet-stream")
                if _identity(os.fstat(node.file.fileno())) != node.initial:
                    raise _changed()
            with app.lock:
                if not node.valid_at_publish():
                    raise _changed()
    except UnsafePath:
        if pack:
            return handler._json(404, {"error": "PACK_NOT_FOUND"})
        raise H1Error("ORIGINAL_PATH_INVALID", "原件路径无法安全读取") from None
    except FileNotFoundError:
        if pack:
            return handler._json(404, {"error": "PACK_NOT_FOUND"})
        raise _changed() from None
    except OSError:
        # Preserve the legacy raw I/O failure and PDF preview's narrower 422 boundary.
        if not pack and "preview_page" in q:
            return handler._json(422, {"error": "ORIGINAL_PREVIEW_UNAVAILABLE"})
        raise
    if pack:
        return handler._send(200, body, kind, (("Content-Disposition", f'attachment; filename="{node.path.name}"'),))
    return handler._send(200, body, kind)
