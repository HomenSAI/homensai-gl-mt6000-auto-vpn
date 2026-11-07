# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Package maintenance marker (plan item 54, audit findings F-16/F-17).

The package hooks (lifecycle_guard.py, embedded in prerm/preinst/postinst) write PERSIST/maintenance.json under the
control lock BEFORE they assess the state, and remove it when the package operation ends (postinst before the service
starts again, any refusal at once). While the marker is active a Start, a manual switch, the failure test and the speed
test are refused with MAINTENANCE-IN-PROGRESS and the supervisor begins no new session: a Start that wins the lock
before the marker is seen by the guard (Auto requested: the guard refuses), a Start after it is refused here. Stop is
never refused, and nothing here blocks a running recovery or rollback.

The marker lives on flash so that a power cut in the middle of an upgrade is seen at the next boot, but it can never
block for ever: it is active only within the same boot (boot_id) and for at most LIMIT seconds of uptime after it was
written (each guard run writes it again). Anything else (another boot, too old, unreadable) is stale: it blocks
nothing, the page shows MAINTENANCE-INTERRUPTED, and the service start (init.d) moves it into upgrade-result.json and
removes it. Lua twin: lua/maintenance.lua (the same rules, router/tests/maintenance_cases.json).
"""
import json
import math
import os
import re
import sys
import time
from pathlib import Path

PERSIST = Path('/etc/homensai-vpn')
PROC = Path('/proc')
MARKER = 'maintenance.json'
RESULT = 'upgrade-result.json'
LIMIT = 900        # seconds of uptime a marker stays active after its last write (the longest step: stop, 300 s)
SKEW = 60          # wall-clock fallback only (no boot id): a marker this far in the future still counts
ACTIONS = ('install', 'upgrade', 'remove')
ACTIVE = 'MAINTENANCE-IN-PROGRESS'
STALE = 'MAINTENANCE-INTERRUPTED'
BOOT_RX = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def _number(value):
    try:return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:return False


def _boot(value):
    return value if isinstance(value, str) and BOOT_RX.fullmatch(value) else None


def classify(marker, boot, uptime, now):
    """marker: the decoded file, None when absent, False when unreadable. boot: this boot's id or None; uptime: seconds
    since boot or None; now: wall clock. Returns the public view {state: none|active|stale, ...}."""
    if marker is None:return {'state': 'none'}
    if not isinstance(marker, dict) or marker.get('action') not in ACTIONS:
        return {'state': 'stale', 'code': STALE, 'action': None, 'since': None, 'reason': 'invalid'}
    since = marker.get('time') if _number(marker.get('time')) else None
    view = {'action': marker['action'], 'since': since}
    marked, current = _boot(marker.get('boot_id')), _boot(boot)
    if marked and current:
        if marked != current:return dict(view, state='stale', code=STALE, reason='reboot')
        if _number(marker.get('uptime')) and _number(uptime):
            age = uptime - marker['uptime']
            if 0 <= age <= LIMIT:return dict(view, state='active', code=ACTIVE)
            return dict(view, state='stale', code=STALE, reason='timeout' if age > LIMIT else 'invalid')
    # No usable boot id or uptime: the wall clock bounds it (a jump of the clock can only make it stale sooner).
    if since is not None and _number(now):
        age = now - since
        if -SKEW <= age <= LIMIT:return dict(view, state='active', code=ACTIVE)
        return dict(view, state='stale', code=STALE, reason='timeout')
    return dict(view, state='stale', code=STALE, reason='invalid')


def read_marker(persist):
    """The decoded marker, None when absent, False when unreadable. IR-06 (integration review 07.11.2026): a symlink or
    any non-regular file in its place is unreadable (stale 'invalid', never followed; clear_stale removes the link
    itself) - the Lua twin now does the same (maintenance_cases.json "files")."""
    path = Path(persist) / MARKER
    try:
        if path.is_symlink():return False
        if not path.exists():return None
        if not path.is_file() or path.stat().st_size > 4096:return False
        return json.loads(path.read_text(encoding='utf8'))
    except (OSError, ValueError, UnicodeDecodeError, RecursionError):
        return False


def boot_id(proc=None):
    try:return _boot((Path(proc or PROC) / 'sys/kernel/random/boot_id').read_text(encoding='ascii').strip())
    except (OSError, ValueError, UnicodeDecodeError):return None


def uptime(proc=None):
    try:
        value = float((Path(proc or PROC) / 'uptime').read_text(encoding='ascii').split()[0])
        return value if _number(value) else None
    except (OSError, ValueError, IndexError, UnicodeDecodeError):return None


def current(persist=None, proc=None, now=None):
    return classify(read_marker(persist or PERSIST), boot_id(proc), uptime(proc), time.time() if now is None else now)


def blocker(persist=None, proc=None, now=None):
    """MAINTENANCE-IN-PROGRESS while a package operation runs, else None. Never raises."""
    try:return ACTIVE if current(persist, proc, now)['state'] == 'active' else None
    except (OSError, ValueError, TypeError, KeyError):return None


def public(persist=None, proc=None, now=None):
    """status.maintenance: None without a marker, else {state, code, action, since[, reason]}."""
    try:view = current(persist, proc, now)
    except (OSError, ValueError, TypeError, KeyError):return None
    return None if view['state'] == 'none' else view


def clear_stale(persist=None, proc=None, now=None):
    """Service start: a stale marker becomes upgrade-result.json (MAINTENANCE-INTERRUPTED, shown on the page until the
    next successful installation) and is removed. An active marker is left alone. Returns the record or None."""
    persist = Path(persist or PERSIST)
    now = time.time() if now is None else now
    view = current(persist, proc, now)
    if view['state'] != 'stale':return None
    record = {'code': STALE, 'reason': view['reason'], 'action': view['action'] or '', 'from': '', 'to': '',
              'since': view['since'], 'time': now}
    temporary = persist / ('.' + RESULT + '.new')
    with open(str(temporary), 'w', encoding='utf8') as stream:
        stream.write(json.dumps(record, sort_keys=True))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temporary), str(persist / RESULT))
    os.unlink(str(persist / MARKER))
    return record


if __name__ == '__main__':
    if sys.argv[1:] == ['clear-stale']:
        try:cleared = clear_stale()
        except OSError:
            print('MAINTENANCE-CLEAR-FAILED', file=sys.stderr);raise SystemExit(1)
        if cleared:print(STALE + ' ' + cleared['reason'] + ' ' + cleared['action'])
        raise SystemExit(0)
    raise SystemExit('usage: maintenance.py clear-stale')
