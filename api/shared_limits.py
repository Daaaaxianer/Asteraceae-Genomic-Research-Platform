"""Single-host, process-shared limits without an extra service or database.

Rate records are atomically updated under OS locks. Download slots hold OS
locks until the response closes; worker death releases them automatically.
The state directory must be on a local filesystem shared by all workers.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time

from django.conf import settings

try:
    import fcntl
except ImportError:  # Windows development checkouts
    fcntl = None
    import msvcrt


def _state_dir():
    project = hashlib.sha256(str(settings.BASE_DIR).encode()).hexdigest()[:16]
    path = Path(getattr(settings, 'AGRP_API_STATE_DIR',
                        Path(tempfile.gettempdir()) / ('agrp-api-' + project)))
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or (hasattr(os, 'getuid') and path.stat().st_uid != os.getuid()):
        raise OSError('API limit directory has an unexpected owner')
    return path


def _lock(handle, blocking):
    if fcntl is not None:
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(handle.fileno(), flags)
    else:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b'\0')
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK, 1)


def consume_rate(key, maximum, window):
    """Return (allowed, retry_after), sharing a sliding window across workers."""
    digest = hashlib.sha256(key.encode()).hexdigest()
    root = _state_dir()
    # A fixed number of state/lock files bounds inode use for rate records.
    shard = root / ('rate-' + digest[:2])
    with open(str(shard) + '.lock', 'a+b') as lock:
        _lock(lock, True)
        now = time.time()
        try:
            with open(str(shard) + '.json', encoding='utf-8') as source:
                records = json.load(source)
        except (FileNotFoundError, ValueError):
            records = {}
        records = {name: record for name, record in records.items() if record[0] > now}
        history = [stamp for stamp in records.get(digest, [0, []])[1] if stamp > now - window]
        if len(history) >= maximum:
            return False, max(1, math.ceil(window - (now - history[0])))
        if digest not in records and len(records) >= 256:
            return False, window
        history.append(now)
        records[digest] = [now + window, history]
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root,
                                             prefix='rate-write-', delete=False) as target:
                temporary = target.name
                json.dump(records, target, separators=(',', ':'))
            os.replace(temporary, str(shard) + '.json')
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
    return True, None


def acquire_slot(key, maximum):
    """Return an open lock lease, or None when every slot is occupied."""
    digest = hashlib.sha256(key.encode()).hexdigest()
    root = _state_dir()
    for index in range(maximum):
        handle = open(root / ('slot-' + digest + '-' + str(index)), 'a+b')
        try:
            _lock(handle, False)
            return handle
        except (BlockingIOError, PermissionError):
            handle.close()
        except OSError:
            handle.close()
            raise
    return None
