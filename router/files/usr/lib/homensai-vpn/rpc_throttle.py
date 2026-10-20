"""Minimum spacing between repeated writing RPCs (flash wear, duplicate messages); RAM state only.

A rejected call never consumes the slot. If the RAM state cannot be read or written the call is allowed:
this guard protects against a confused double-click, it is not a security boundary.
"""
import fcntl
import json
import os
import time
from pathlib import Path

RUNTIME = Path('/var/run/homensai-vpn')


def allow(key, interval, now=None):
    """True and records the call when at least `interval` seconds passed since the last allowed call of `key`."""
    now = time.time() if now is None else now
    try:
        RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
        if RUNTIME.is_symlink():
            return True
        fd = os.open(str(RUNTIME/'rpc-throttle.lock'), os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            path = RUNTIME/'rpc-throttle.json'
            try:
                rows = json.loads(path.read_text(encoding='utf-8')) if path.exists() and not path.is_symlink() and path.stat().st_size < 65536 else {}
            except (OSError, ValueError):
                rows = {}
            if not isinstance(rows, dict):
                rows = {}
            last = rows.get(key)
            if type(last) in (int, float) and 0 <= now - last < interval:
                return False
            rows = {k: v for k, v in rows.items() if type(v) in (int, float) and 0 <= now - v < 3600}
            rows[key] = now
            pending = path.with_name(path.name + '.pending')
            pending.write_text(json.dumps(rows), encoding='utf-8')
            os.replace(str(pending), str(path))
            return True
        finally:
            os.close(fd)
    except (OSError, ValueError):
        return True
