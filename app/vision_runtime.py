"""Own the local Vision executable shared by OCR, PDF page counts and previews."""
from contextvars import ContextVar
from functools import wraps
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import select
import signal
import struct
import sys
import tempfile
import time
import threading

_build_guard = threading.Lock()


_partner_request = ContextVar("partner_vision", default=False)
_verified = None


def is_partner_request():
    return _partner_request.get()


def partner_request(call):
    @wraps(call)
    def run(*args, **kwargs):
        token = _partner_request.set(True)
        try:
            return call(*args, **kwargs)
        finally:
            _partner_request.reset(token)
    return run


def _safe_entry(path, directory=False):
    meta = path.lstat()
    kind_ok = stat.S_ISDIR(meta.st_mode) if directory else stat.S_ISREG(meta.st_mode)
    if (not kind_ok or meta.st_uid != os.getuid() or meta.st_mode & 0o022
            or (not directory and meta.st_nlink != 1)):
        raise RuntimeError("OCR_ENGINE_UNAVAILABLE")


def execution_env():
    if not is_partner_request():
        return None
    env = {key: os.environ[key] for key in ("HOME", "TMPDIR") if key in os.environ}
    env["PATH"] = "/usr/bin:/bin"
    return env


def _compiled_partner_binary(source, directory):
    """Trust a build from this process only. One entry, independent of report volume."""
    global _verified
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    _safe_entry(directory, directory=True)
    cache = directory / "partner-vision"
    cache.mkdir(mode=0o700, exist_ok=True)
    _safe_entry(cache, directory=True)
    if cache.lstat().st_mode & 0o077:
        raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
    target = cache / "ocr_vision"
    source_bytes = source.read_bytes()
    key = (os.getpid(), cache.resolve(), hashlib.sha256(source_bytes).digest())
    if os.path.lexists(target):
        _safe_entry(target)
        if _verified is not None and _verified[0] == key:
            if hashlib.sha256(target.read_bytes()).digest() == _verified[1]:
                return target
            raise RuntimeError("OCR_ENGINE_UNAVAILABLE")

    compiler = shutil.which("swiftc")
    if not compiler or Path(compiler).resolve() != Path("/usr/bin/swiftc").resolve():
        raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
    if Path(tempfile.gettempdir()).resolve().is_relative_to(directory.resolve()):
        raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
    # Establish trust outside the writable executable cache. The retained
    # identity comes from the compiler output before it goes into that cache.
    with tempfile.TemporaryDirectory(prefix="ptds-vision-build-") as scratch:
        input_path = Path(scratch) / "reader.swift"
        output_path = Path(scratch) / "reader"
        input_path.write_bytes(source_bytes)
        try:
            subprocess.run(["/usr/bin/swiftc", "-O", str(input_path), "-o", str(output_path)],
                           capture_output=True, check=True, timeout=300, env=execution_env())
            _safe_entry(output_path)
            program = output_path.read_bytes()
            digest = hashlib.sha256(program).digest()
            code_id = _code_directory_id(program)
            with tempfile.NamedTemporaryFile(dir=cache, prefix=".publish-", delete=False) as published:
                try:
                    published.write(program)
                    published.flush()
                    os.fchmod(published.fileno(), 0o700)
                    os.replace(published.name, target)
                finally:
                    Path(published.name).unlink(missing_ok=True)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("OCR_ENGINE_UNAVAILABLE") from exc
    _verified = (key, digest, code_id, program)
    return target


def binary(source, directory):
    # This lock is independent of the application lock. No callbacks take A here.
    with _build_guard:
        if is_partner_request():
            return _compiled_partner_binary(source, directory)
        directory.mkdir(parents=True, exist_ok=True)
        tag = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
        target = directory / f"ocr_vision-{tag}"
        if target.is_file():
            return target
        if not shutil.which("swiftc"):
            raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
        # Compile away from the published name. Concurrent processes never see
        # a partial executable, even though the compiler owner is process-local.
        with tempfile.TemporaryDirectory(prefix=".vision-build-", dir=directory) as work:
            staged = Path(work) / "ocr_vision"
            try:
                subprocess.run(["swiftc", "-O", str(source), "-o", str(staged)],
                               check=True, capture_output=True, timeout=300)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                (directory / "ocr_vision-build-error.log").write_bytes(exc.stderr or b"timeout")
                older = [path for path in directory.glob("ocr_vision-*")
                         if not path.name.endswith(".log") and path.is_file()]
                if not older:
                    raise RuntimeError("OCR_ENGINE_UNAVAILABLE") from exc
                return max(older, key=lambda path: path.stat().st_mtime)
            os.replace(staged, target)
        return target

def _code_directory_id(program):
    """Read the primary SHA-256 CodeDirectory of a thin, native compiler output."""
    unavailable = RuntimeError("OCR_ENGINE_UNAVAILABLE")
    if program[:4] != b"\xcf\xfa\xed\xfe" or len(program) < 32:
        raise unavailable
    commands, length = struct.unpack_from("<II", program, 16)
    offset, end = 32, 32 + length
    if end > len(program) or commands > length // 8:
        raise unavailable
    for _ in range(commands):
        if offset + 8 > end:
            raise unavailable
        cmd, size = struct.unpack_from("<II", program, offset)
        if size < 8 or offset + size > end:
            raise unavailable
        if cmd == 0x1d and size >= 16:  # LC_CODE_SIGNATURE
            start, count = struct.unpack_from("<II", program, offset + 8)
            blob = memoryview(program)[start:start+count]
            if len(blob) != count or count < 12:
                raise unavailable
            magic, length, entries = struct.unpack_from(">III", blob)
            if magic != 0xfade0cc0 or length > count or 12 + 8*entries > length:
                raise unavailable
            for i in range(entries):
                slot, begin = struct.unpack_from(">II", blob, 12 + 8*i)
                if slot != 0:
                    continue
                if begin + 44 > length:
                    raise unavailable
                magic, block_size = struct.unpack_from(">II", blob, begin)
                if (magic != 0xfade0c02 or block_size < 44 or begin + block_size > length
                        or bytes(blob[begin+36:begin+38]) != b"\x20\x02"):
                    raise unavailable
                return hashlib.sha256(blob[begin:begin+block_size]).digest()[:20]
        offset += size
    raise unavailable


def _spawn_suspended(path, args, env, write_fd):
    """macOS spawn.h: start stopped at exec, close all undesignated descriptors."""
    lib = ctypes.CDLL(None, use_errno=True)
    attr, actions, pid = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_int()
    ref = ctypes.byref
    def checked(result):
        if result:
            raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
    checked(lib.posix_spawnattr_init(ref(attr)))
    try:
        checked(lib.posix_spawnattr_setflags(ref(attr), 0x0080 | 0x4000))
        checked(lib.posix_spawn_file_actions_init(ref(actions)))
        try:
            checked(lib.posix_spawn_file_actions_addopen(ref(actions), 0, b"/dev/null", os.O_RDONLY, 0))
            checked(lib.posix_spawn_file_actions_adddup2(ref(actions), write_fd, 1))
            checked(lib.posix_spawn_file_actions_addopen(ref(actions), 2, b"/dev/null", os.O_WRONLY, 0))
            def vector(items):
                return (ctypes.c_char_p * (len(items)+1))(*[os.fsencode(x) for x in items], None)
            argv = [str(path), *args]
            sys.audit("subprocess.Popen", str(path), argv, None, env)
            checked(lib.posix_spawn(ref(pid), os.fsencode(path), ref(actions), ref(attr), vector(argv),
                                    vector([k+"="+v for k,v in env.items()])))
        finally:
            lib.posix_spawn_file_actions_destroy(ref(actions))
    finally:
        lib.posix_spawnattr_destroy(ref(attr))
    return pid.value


def _kernel_identity(pid):
    # <sys/codesign.h>: CS_OPS_CDHASH requests the identity of the loaded task,
    # not the signature of the file currently reachable under a pathname.
    identity = ctypes.create_string_buffer(20)
    library = ctypes.CDLL(None, use_errno=True)
    flags = ctypes.c_uint32()
    if library.csops(pid, 0, ctypes.byref(flags), ctypes.sizeof(flags)) != 0 or not (flags.value & 1):
        raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
    result = library.csops(pid, 5, identity, len(identity))
    if result != 0:
        raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
    return identity.raw


def verified_run(source, directory, args, timeout):
    if sys.platform != "darwin":
        raise RuntimeError("OCR_UNSUPPORTED")
    with _build_guard:
        _compiled_partner_binary(source, directory)
        expected, image = _verified[2:]
    # A writer of the executable cache must never be able to change the image
    # presented to exec. Materialize the compiler-owned bytes outside the cache.
    with tempfile.TemporaryDirectory(prefix="ptds-vision-run-") as scratch:
        path = Path(scratch) / "reader"
        path.write_bytes(image)
        path.chmod(0o500)
        # Vision uses a regular executable path for framework discovery.
        # The kernel identity check below binds the running child before resume.
        return _run_identified(path, expected, args, timeout)


def _run_identified(path, expected, args, timeout):
    read_fd, write_fd = os.pipe()
    pid = None
    deadline = time.monotonic() + timeout
    try:
        try:
            pid = _spawn_suspended(path, args, execution_env(), write_fd)
        finally:
            os.close(write_fd)
        if _kernel_identity(pid) != expected:
            raise RuntimeError("OCR_ENGINE_UNAVAILABLE")
        os.kill(pid, signal.SIGCONT)
        chunks = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([read_fd], [], [], remaining)[0]:
                raise subprocess.TimeoutExpired(str(path), timeout)
            part = os.read(read_fd, 65536)
            if not part:
                break
            chunks.append(part)
        while True:
            waited, status = os.waitpid(pid, os.WNOHANG)
            if waited:
                pid = None
                return subprocess.CompletedProcess([str(path), *args], os.waitstatus_to_exitcode(status), b"".join(chunks), b"")
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(str(path), timeout)
            time.sleep(0.01)
    finally:
        os.close(read_fd)
        if pid is not None:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
