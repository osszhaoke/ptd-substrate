"""Own the local Vision executable shared by OCR, PDF page counts and previews."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

_build_guard = threading.Lock()


def binary(source, directory):
    # This lock is independent of the application lock. No callbacks take A here.
    with _build_guard:
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
