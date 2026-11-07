"""Private worker metadata only. Never stores credentials, addresses or readings."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid


def load(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('UNSAFE_STATE')
    return json.loads(path.read_text()) if path.exists() else {}


def save(path, state):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('UNSAFE_STATE')
    temp = path.with_name('.recovery-' + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(state, out, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def network_key():
    """Detect route/DNS/interface changes at the next existing scheduled run."""
    parts = []
    for cmd in (['/usr/sbin/scutil', '--nwi'], ['/usr/sbin/scutil', '--dns']):
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=3)
            if result.returncode:
                return 'unavailable'
            parts.append(result.stdout)
        except (OSError, subprocess.TimeoutExpired):
            return 'unavailable'
    return hashlib.sha256(b'\n'.join(parts)).hexdigest()


def revision(path):
    stat = Path(path).stat()
    return str(stat.st_mtime_ns) + ':' + str(stat.st_size)


def due(state, network, now, credential_revision=None):
    changed_credentials = (credential_revision is not None and
                           credential_revision != state.get('credential_revision'))
    if state.get('status') == 'NEEDS_REAUTH':
        return changed_credentials
    # A network change must not defeat provider rate limits.
    if state.get('retry_category') == 'rate_limit':
        return now >= state.get('next_attempt', 0)
    changed_network = network != 'unavailable' and network != state.get('network')
    return changed_network or changed_credentials or now >= state.get('next_attempt', 0)


def failure(state, code, now, network, *, interval=300, auth=False, rate=False,
            credential_revision=None, max_delay=1800):
    count = min(8, state.get('failures', 0) + 1) if state.get('network') == network else 1
    delay = 1800 if rate else min(max_delay, interval * 2 ** (count - 1))
    return dict(state, status='NEEDS_REAUTH' if auth else 'RETRY_WAIT', last_error=code,
                failures=count, next_attempt=now + delay, network=network,
                retry_category='auth' if auth else 'rate_limit' if rate else 'network_or_service',
                credential_revision=credential_revision)


def success(state, at, network, credential_revision=None):
    return dict(state, status='CONNECTED', last_success=at, last_error=None,
                failures=0, next_attempt=0, retry_category=None, network=network,
                credential_revision=credential_revision)


def manual_retry(state, now):
    """A user retry clears network backoff, never pause, revocation or rate limits."""
    if state.get('paused') or state.get('status') in ('PAUSED', 'NEEDS_REAUTH', 'REVOKED'):
        raise ValueError('DEVICE_ACTION_REQUIRED')
    if state.get('retry_category') == 'auth' or 'REVOK' in str(state.get('last_error', '')).upper():
        raise ValueError('DEVICE_ACTION_REQUIRED')
    if state.get('retry_category') == 'rate_limit' and now < state.get('next_attempt', 0):
        raise ValueError('DEVICE_RATE_LIMITED')
    if now - state.get('manual_retry_at', float('-inf')) < 15:
        raise ValueError('DEVICE_RETRY_BUSY')
    return dict(state, next_attempt=0, manual_retry_at=now)
