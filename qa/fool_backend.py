#!/usr/bin/env python3
"""The clueless-grandfather test for the router backend (offline, stdlib only, deterministic).

Fifty personas (10 behaviours x 5 seeds) type absurd things into every user-reachable RPC method of
router/files/usr/lib/homensai-vpn/agent.py. Side effects are mocked: subprocess, the UCI writer and the
runtime/persist directories (a temp dir). Nothing real is touched, no network, no router.

Every call is classified:
  ACCEPTED  the method said yes; the request must be valid by an independent oracle written here, and the
            values handed to the UCI writer must lie inside the documented bounds
  REJECTED  a clean diagnostic code matching ^[A-Z][A-Z0-9_-]{0,95}$ (also: the CLI wrapper's {"error": code})
  BAD       traceback, hang over 2 s, accepted invalid value, bool/float as int, NaN/Infinity, over-long text,
            unclean/missing code, or rapid repeats that spawn unbounded work (writer runs, processes, files)

Needs Linux (fcntl): run through scripts/test-local.ps1 (see qa/test_fool_backend.py) or any Linux python3.
Usage: python3 qa/fool_backend.py [--json report.json] [--verbose]
"""
import argparse
import collections
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unicodedata
from unittest import mock

LIB = Path(os.environ.get('FOOL_LIB') or Path(__file__).resolve().parents[1]/'router/files/usr/lib/homensai-vpn')
CODE = re.compile(r'^[A-Z][A-Z0-9_-]{0,95}$')
HANG_SECONDS = 2.0
MEMORY_LIMIT = 80*1024*1024
TRIAL = 'ab'*16
TX = 'cd'*16
PROFILES = ['wg_a', 'wg_b', 'ovpn_c']

# ---- documented bounds (name -> (min, max)); the writer payload is checked against these -------------------------
BOUNDS = {
    'interval': (10, 300), 'native_duration': (1, 240), 'priority': (1, 1000),
    'telegram_interval': (5, 10080), 'telegram_hour': (0, 23),
    'speed_budget_mib': (1, 32), 'speed_duration': (2, 15), 'speed_streams': (1, 4),
    'speed_daily_mib': (1, 1024), 'speed_busy_mbps': (1, 1000),
    'checkpoint': (300, 3600), 'probe_limit': (1, 16),
    'recovery_failures': (3, 10), 'recovery_successes': (2, 10), 'recovery_cooldown': (60, 1800),
    'recovery_min_dwell': (60, 3600), 'recovery_primary_successes': (2, 10), 'recovery_primary_stable': (30, 600),
}
FLAGS = {'native_session_loss', 'setup_complete', 'telegram_enabled', 'telegram_weekly', 'telegram_monthly',
         'speed_enabled', 'speed_auto_new', 'plan_enabled', 'enabled'}
TEXT_KEYS = {'name', 'channel', 'plan_source', 'plan_target', 'profile', 'section', 'telegram_chat', 'telegram_token',
             'telegram_schedule', 'telegram_items', 'recovery_return_policy', 'terms_version', 'terms_time'}


def sane_text(value):
    return (isinstance(value, str) and 1 <= len(value) <= 64 and value.strip() != ''
            and not any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Co', 'Cn', 'Zl', 'Zp') for c in value))


def is_int(value, low, high):
    return type(value) is int and low <= value <= high


def is_bool(value):
    return type(value) is bool


# ---- oracles: independent statement of "this request is valid" -----------------------------------------------------
def v_system(a):
    if not isinstance(a, dict) or set(a) != {'source', 'target', 'interval', 'duration', 'session_loss', 'servers'}:
        return False
    if not (isinstance(a['source'], str) and isinstance(a['target'], str) and a['source'] in PROFILES
            and a['target'] in PROFILES and a['source'] != a['target']):
        return False
    if not (is_bool(a['session_loss']) and is_int(a['interval'], 10, 300) and is_int(a['duration'], 1, 240)):
        return False
    rows = a['servers']
    if not isinstance(rows, list) or len(rows) > 400:
        return False
    seen = set();enabled = set()
    for r in rows:
        if not isinstance(r, dict) or set(r) != {'profile', 'name', 'channel', 'priority', 'enabled'}:
            return False
        if not (isinstance(r['profile'], str) and r['profile'] in PROFILES and r['profile'] not in seen and is_bool(r['enabled'])):
            return False
        if not (sane_text(r['name']) and sane_text(r['channel']) and is_int(r['priority'], 1, 1000)):
            return False
        seen.add(r['profile'])
        if r['enabled']:
            enabled.add(r['profile'])
    return a['source'] in enabled and a['target'] in enabled


ITEM_IDS = ('servers', 'events', 'traffic', 'delta', 'controller', 'controller_events', 'controller_totals', 'gaps')


def v_telegram(a):
    if not isinstance(a, dict) or not {'token', 'chat', 'enabled', 'interval'} <= set(a):
        return False
    if set(a)-{'token', 'chat', 'enabled', 'interval', 'schedule', 'hour', 'weekly', 'monthly', 'items'}:
        return False
    if not is_bool(a['enabled']) or not is_int(a['interval'], 5, 10080):
        return False
    t = a['token']
    if not isinstance(t, str) or (t and not re.fullmatch(r'[0-9]{6,15}:[A-Za-z0-9_-]{30,100}', t)):
        return False
    if not isinstance(a['chat'], str) or not re.fullmatch(r'(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})', a['chat']):
        return False
    if 'schedule' in a and a['schedule'] not in ('interval', 'daily'):
        return False
    if 'hour' in a and not is_int(a['hour'], 0, 23):
        return False
    for f in ('weekly', 'monthly'):
        if f in a and not is_bool(a[f]):
            return False
    if 'items' in a:
        i = a['items']
        if not isinstance(i, str) or len(i) > 200:
            return False
        if i != 'none':
            parts = i.split(',')
            if any(p not in ITEM_IDS for p in parts) or len(set(parts)) != len(parts):
                return False
    return True


def v_speed_cfg(a):
    f = {'enabled', 'auto_new', 'budget_mib', 'duration', 'streams', 'daily_mib', 'busy_mbps'}
    if not isinstance(a, dict) or set(a) != f or not is_bool(a['enabled']) or not is_bool(a['auto_new']):
        return False
    return (is_int(a['budget_mib'], 1, 32) and is_int(a['duration'], 2, 15) and is_int(a['streams'], 1, 4)
            and is_int(a['daily_mib'], 1, 1024) and is_int(a['busy_mbps'], 1, 1000) and a['budget_mib'] <= a['daily_mib'])


def v_monitor_cfg(a):
    return (isinstance(a, dict) and set(a) == {'interval', 'checkpoint', 'probe_limit', 'planning_enabled'}
            and is_bool(a['planning_enabled']) and is_int(a['interval'], 10, 300)
            and is_int(a['checkpoint'], 300, 3600) and is_int(a['probe_limit'], 1, 16))


RECOVERY = {'failures': (3, 10), 'successes': (2, 10), 'cooldown': (60, 1800), 'min_dwell': (60, 3600),
            'primary_successes': (2, 10), 'primary_stable': (30, 600)}


def v_recovery(a):
    if not isinstance(a, dict) or set(a) != set(RECOVERY)|{'return_policy'}:
        return False
    return all(is_int(a[k], *r) for k, r in RECOVERY.items()) and a['return_policy'] in ('healthy_primary', 'hold_reserve')


def v_terms(a):
    return isinstance(a, dict) and set(a) == {'version'} and a['version'] == '1'


def v_empty(a):
    return a == {}


def v_ordered(a, with_revision):
    f = {'ordered', 'revision'} if with_revision else {'ordered'}
    if not isinstance(a, dict) or set(a) != f:
        return False
    o = a['ordered']
    if not isinstance(o, list) or not 1 <= len(o) <= 400 or any(not isinstance(x, str) for x in o) or len(set(o)) != len(o):
        return False
    if any(x not in PROFILES for x in o):
        return False
    return not with_revision or (isinstance(a['revision'], str) and a['revision'] == STATE['revision'])


def v_fault(a):
    return (isinstance(a, dict) and set(a) == {'profile', 'scope', 'duration'} and isinstance(a['profile'], str)
            and a['scope'] in ('profile', 'channel') and is_int(a['duration'], 30, 180))


def v_speed_start(a):
    return (isinstance(a, dict) and set(a) == {'profiles', 'budget_mib', 'duration', 'streams'}
            and isinstance(a['profiles'], list) and 1 <= len(a['profiles']) <= 8
            and all(isinstance(p, str) and p in PROFILES for p in a['profiles']) and len(set(a['profiles'])) == len(a['profiles'])
            and is_int(a['budget_mib'], 1, 32) and is_int(a['duration'], 2, 15) and is_int(a['streams'], 1, 4))


def v_confirm(a):
    return (isinstance(a, dict) and set(a) == {'tx', 'exit_ipv4', 'dns_ok', 'https_ok', 'trial'}
            and a['tx'] == TX and a['exit_ipv4'] == '8.8.8.8' and a['dns_ok'] is True and a['https_ok'] is True
            and a['trial'] == TRIAL)


def v_monitor_control(a):
    return isinstance(a, dict) and set(a) == {'enabled'} and is_bool(a['enabled'])


STATE = {'revision': ''}


def good_system():
    return {'source': 'wg_a', 'target': 'wg_b', 'interval': 30, 'duration': 10, 'session_loss': False,
            'servers': [{'profile': p, 'name': 'Server '+p, 'channel': 'Main', 'priority': i+1, 'enabled': True}
                        for i, p in enumerate(PROFILES)]}


def good_telegram():
    return {'token': '123456789:'+'A'*35, 'chat': '-1001234567890', 'enabled': True, 'interval': 60,
            'schedule': 'daily', 'hour': 8, 'weekly': False, 'monthly': True, 'items': 'servers,events'}


# method -> (good-args factory, oracle, kind). kind: 'write' (needs success detection), 'noargs', 'plain'
SPECS = {
    'setup_system': (good_system, v_system),
    'setup_telegram': (good_telegram, v_telegram),
    'setup_speed': (lambda: {'enabled': True, 'auto_new': False, 'budget_mib': 8, 'duration': 5, 'streams': 2, 'daily_mib': 128, 'busy_mbps': 2}, v_speed_cfg),
    'setup_monitor': (lambda: {'interval': 30, 'checkpoint': 600, 'probe_limit': 8, 'planning_enabled': True}, v_monitor_cfg),
    'setup_recovery': (lambda: {'failures': 3, 'successes': 2, 'cooldown': 180, 'min_dwell': 180, 'return_policy': 'healthy_primary', 'primary_successes': 3, 'primary_stable': 60}, v_recovery),
    'terms_accept': (lambda: {'version': '1'}, v_terms),
    'telegram_forget': (dict, v_empty),
    'priority_preview': (lambda: {'ordered': ['wg_b', 'wg_a']}, lambda a: v_ordered(a, False)),
    'priority_apply': (lambda: {'ordered': ['wg_b', 'wg_a'], 'revision': STATE['revision']}, lambda a: v_ordered(a, True)),
    'fault_start': (lambda: {'profile': 'wg_a', 'scope': 'profile', 'duration': 60}, v_fault),
    'fault_cancel': (dict, v_empty),
    'speed_start': (lambda: {'profiles': ['wg_a'], 'budget_mib': 4, 'duration': 3, 'streams': 1}, v_speed_start),
    'speed_cancel': (dict, v_empty),
    'monitor_control': (lambda: {'enabled': True}, v_monitor_control),
    'native_start': (dict, v_empty), 'native_stop': (dict, v_empty), 'native_return': (dict, v_empty),
    'native_confirm': (lambda: {'tx': TX, 'exit_ipv4': '8.8.8.8', 'dns_ok': True, 'https_ok': True, 'trial': TRIAL}, v_confirm),
    'telegram_test': (dict, v_empty), 'telegram_retry': (dict, v_empty), 'setup_check': (dict, v_empty),
    'scan': (dict, v_empty), 'status': (dict, v_empty), 'events': (dict, v_empty), 'inventory': (dict, v_empty),
}
NOARGS = {m for m, (_, o) in SPECS.items() if o is v_empty}
# Methods whose acceptance cannot be reached in this mocked fixture (they need a certified live router state);
# their validation still runs and a rejection of a valid request is a clean code, not a defect.
SAFE_SUCCESS_FLAGS = ('accepted', 'saved', 'queued', 'delivered', 'cleaned')

# ---- hostile values -----------------------------------------------------------------------------------------------
class Raw:
    """Literal JSON text for values json.dumps cannot or will not write."""
    def __init__(self, text):
        self.text = text


def hostile_pool(behaviour, rng):
    big = [134744072, 16909060, 10**30, 2**63, 2**31, 2**53+1, 99999999999, 10**400, -(10**30), 4294967296]
    neg = [-1, -5, -2**31, -(10**9), 0, -0, 1-2, -999999]
    flt = [1.5, 0.1, 5.0, 30.0, 10.0, 1e308, -1e308, 1e-9, 3.14159, 29.999999, 300.00001, float(rng.randint(1, 300))]
    strs = ['30', 'abc', '', ' ', '１２', '0x10', '1e3', 'NaN', 'Infinity', '-1', '30 ', 'true', 'null', '٣٠', '30;reboot']
    empties = [None, '', [], {}, ' ', 0, False]
    nonfinite = [Raw('1e999'), Raw('-1e999'), Raw('NaN'), Raw('Infinity'), Raw('-Infinity'), Raw('1E400'), Raw('1e-999')]
    longs = ['A'*65, 'A'*1000, 'A'*65536, 'ж'*65, '9'*5000, '@'+'a'*5000, 'x'*70000, '1'*400]
    uni = ['bad\nname', 'tab\there', 'nul\x00byte', '\x7f', '\x1b[31mred', '‮evil', '​zero', ' line',
           '\U0001F600'*5, 'café', 'é'*20, '\ud800', '￾', '\x85', '../../etc/passwd', "'; rm -rf /; '",
           '$(touch x)', '`id`', '<script>alert(1)</script>', '%s%n%x', '{{7*7}}', 'Ａ'*10, '\U000e0041hidden', '   ', '﻿']
    types = [True, False, [], [1, 2], {}, {'a': 1}, None, [None], [[]], 'str', 1.0, [{'x': 1}], {'__proto__': 1}, [True]]
    pools = {
        0: big, 1: neg, 2: flt, 3: strs, 4: empties, 5: nonfinite, 6: longs, 7: uni, 8: types,
        9: big+neg+flt+strs+empties+longs+uni+types,
    }
    return pools[behaviour]


def paths(value, prefix=()):
    """All mutable leaf positions of a nested args structure."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from paths(v, prefix+(k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from paths(v, prefix+(i,))
    else:
        yield prefix


def set_path(root, path, new):
    cur = root
    for part in path[:-1]:
        cur = cur[part]
    cur[path[-1]] = new


def encode(args):
    """Body bytes; Raw placeholders become literal JSON text."""
    holders = []

    def walk(v):
        if isinstance(v, Raw):
            holders.append(v.text);return '@@RAW%d@@' % (len(holders)-1)
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v
    text = json.dumps(walk(args), allow_nan=True)
    for i, literal in enumerate(holders):
        text = text.replace('"@@RAW%d@@"' % i, literal)
    return text.encode('utf-8', 'replace')


GARBAGE = [b'', b'   ', b'null', b'[]', b'"x"', b'12', b'{', b'{"a":', b'\xff\xfe\x00{}', b'\xef\xbb\xbf{}', b'{"a":1,"a":2}',
           b'[' * 100000, b'{"a":' * 2000 + b'1' + b'}' * 2000, b'{"x":"' + b'A' * 70000 + b'"}', b'\x00' * 100,
           b'{"a":[' + b','.join([b'1'] * 12000) + b']}', b'{"ubus_rpc_session":"s","x":1}', b'{"a":NaN}', b'{"a":Infinity}',
           b'{"a":"\\ud800"}', b'{"a":1e999}', b"{'a':1}", b'{"a":1}garbage', b'\n\n{"a":1}\n']

# ---- environment --------------------------------------------------------------------------------------------------
class Fixture:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='fool-backend-'))
        self.run_dir = self.tmp/'run';self.persist = self.tmp/'persist'
        self.run_dir.mkdir();self.persist.mkdir()
        self.writer_payloads = []
        self.popen_calls = 0
        self.run_calls = collections.Counter()
        self.other_calls = []
        sys.path.insert(0, str(LIB))
        import agent
        import auto_control, configuration_guard, fault_control, lifecycle_guard, monitor_control
        import native_switch, priority_config, recovery_settings, rpc_input, rpc_throttle
        import scan_control, setup_config, speed_test, telegram_report, uci_result
        self.agent = agent
        self.mods = [m for m in list(sys.modules.values()) if getattr(m, '__file__', None) and str(LIB) in str(m.__file__)]
        self.names = {m.__name__ for m in self.mods}
        for m in self.mods:
            if hasattr(m, 'RUNTIME'):
                m.RUNTIME = self.run_dir
            if hasattr(m, 'PERSIST'):
                m.PERSIST = self.persist
        speed_test.JOB = self.run_dir/'speed-job.json';speed_test.CANCEL = self.run_dir/'speed-cancel.json'
        speed_test.HISTORY = self.persist/'speed-history.json';speed_test.LEDGER = self.persist/'speed-quota.json'
        native_switch.JOURNAL = self.persist/'native-transaction.json'
        self.patches = []
        self.reset_state()

    def inventory(self):
        profiles = [{'id': p, 'name': 'Profile '+p, 'protocol': 'wireguard', 'interface': p} for p in PROFILES]
        return {'profiles': profiles, 'servers': [], 'native_candidates': [], 'wan_interfaces': [],
                'settings': {'speed_enabled': '1', 'speed_budget_mib': '32', 'speed_duration': '15', 'speed_streams': '4',
                             'speed_daily_mib': '1024', 'speed_busy_mbps': '1000', 'speed_auto_new': '0'}}

    def fake_run(self, args, *a, **kw):
        self.run_calls[Path(str(args[0])).name if args else '?'] += 1
        text = ' '.join(map(str, args))
        if 'setup_save.lua' in text and 'HOMENSAI_SETUP_TEST_ROOT' in (kw.get('env') or {}):
            return subprocess.CompletedProcess(args, 0, b'OK\n', b'')   # the isolated synthetic self-test, no router write
        if 'uci' in text and 'telegram_token' in text:
            return subprocess.CompletedProcess(args, 0, b'123456:ABCdef_stored\n', b'')
        if 'setup_save.lua' in text:
            payload = json.loads(kw['input'].decode())
            self.writer_payloads.append(payload)
            return subprocess.CompletedProcess(args, 0, b'OK\n', b'')
        if 'telegram_private.lua' in text:
            raise OSError('no telegram in the fixture')
        return subprocess.CompletedProcess(args, 0, b'', b'')

    def fake_popen(self, args, *a, **kw):
        self.popen_calls += 1
        proc = mock.Mock();proc.pid = 4000000+self.popen_calls;proc.poll.return_value = None
        return proc

    def fake_command(self, args, timeout=5):
        text = ' '.join(map(str, args))
        if 'native_policy.lua' in text:
            return json.dumps({'settings': {'native_trial': TRIAL}}).encode()
        if 'inventory.lua' in text:
            return json.dumps(self.inventory()).encode()
        return b'[]'

    def reset_state(self):
        for p in list(self.run_dir.iterdir())+list(self.persist.iterdir()):
            p.unlink() if p.is_file() else None
        self.arm_native(False)
        rows, revision = __import__('priority_config').proposed(self.inventory(), ['wg_b', 'wg_a'])
        STATE['revision'] = revision
        (self.run_dir/'speed-traffic.json').write_text(json.dumps({'monotonic': time.monotonic(), 'rate_bps': 0, 'counters': {}}))

    def arm_native(self, pending):
        """A pending client confirmation exists only while native_confirm is exercised; otherwise no native state."""
        a = self.agent
        now = time.time()
        for path in (self.run_dir/'native-status.json', self.persist/'native-transaction.json', self.run_dir/'native-confirm.json'):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
        if not pending:
            return
        a.atomic_json(self.run_dir/'native-status.json', {'state': 'WAIT-CLIENT', 'tx': TX, 'expected_exit': '8.8.8.8', 'deadline': now+3600})
        data = {'phase': 'WAIT-CLIENT', 'tx': TX, 'expected_exit': '8.8.8.8', 'deadline': now+3600, 'before': ['a'], 'after': ['a']}
        import native_switch
        a.atomic_json(self.persist/'native-transaction.json', {'schema': 1, 'data': data, 'sha256': a.checksum(data)})

    def reset_throttle(self, method=''):
        for n in ('rpc-throttle.json', 'speed-job.json'):
            with contextlib.suppress(FileNotFoundError):
                (self.run_dir/n).unlink()
        with contextlib.suppress(FileNotFoundError):
            (self.persist/'speed-quota.json').unlink()
        self.arm_native(method == 'native_confirm')

    def file_count(self):
        return sum(len(f) for _, _, f in os.walk(self.tmp))

    def __enter__(self):
        a = self.agent
        fake_inv = self.inventory
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch('subprocess.run', side_effect=self.fake_run))
        stack.enter_context(mock.patch('subprocess.Popen', side_effect=self.fake_popen))
        stack.enter_context(mock.patch('subprocess.check_output', side_effect=lambda *a, **k: b''))
        for m in self.mods:
            if hasattr(m, 'inventory'):
                stack.enter_context(mock.patch.object(m, 'inventory', fake_inv))
            if hasattr(m, 'command'):
                stack.enter_context(mock.patch.object(m, 'command', self.fake_command))
        import native_switch
        fake_linux = mock.Mock()
        fake_linux.return_value.policy.return_value = {'settings': {'native_trial': TRIAL}}
        fake_linux.return_value.diagnostic.return_value = (['VENDOR-WORKER-BUSY'], None)
        stack.enter_context(mock.patch.object(native_switch, 'Linux', fake_linux))
        stack.enter_context(mock.patch('os.getloadavg', return_value=(0.0, 0.0, 0.0)))
        self.stack = stack
        return self

    def __exit__(self, *exc):
        self.stack.close()
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class Hang(Exception):
    pass


def invoke(fx, method, body):
    """Run the CLI wrapper exactly as `agent.py call <method>` does. Returns (status, parsed_stdout|None, raw, exception|None, seconds)."""
    out = io.StringIO()
    fake_stdin = mock.Mock();fake_stdin.buffer = io.BytesIO(body)

    def alarm(*_):
        raise Hang()
    old = signal.signal(signal.SIGALRM, alarm);signal.setitimer(signal.ITIMER_REAL, 5.0)
    started = time.process_time();error = None;status = None
    try:
        with mock.patch.object(sys, 'stdin', fake_stdin), contextlib.redirect_stdout(out):
            status = fx.agent.call(method)
    except BaseException as exc:  # noqa: BLE001 - anything that escapes the wrapper is a finding
        error = exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0);signal.signal(signal.SIGALRM, old)
    # CPU seconds: fsync stalls of the Docker disk are not the program's fault; a true hang is cut off by the 5 s wall alarm.
    seconds = time.process_time()-started
    raw = out.getvalue()
    parsed = None
    try:
        parsed = json.loads(raw.strip().splitlines()[-1]) if raw.strip() else None
    except ValueError:
        parsed = None
    return status, parsed, raw, error, seconds


def codes_of(result):
    found = []
    if isinstance(result, dict):
        for key in ('code', 'error'):
            if key in result:
                found.append(result[key])
        for item in result.get('blockers', []) if isinstance(result.get('blockers'), list) else []:
            found.append(item)
    return found


def succeeded(method, result, status):
    if not isinstance(result, dict) or 'error' in result:
        return False
    if method in ('status', 'events', 'inventory'):
        return True
    if method == 'setup_check':
        return result.get('passed') is True
    return any(result.get(k) is True for k in SAFE_SUCCESS_FLAGS)


def check_payload(payload):
    problems = []
    for section in [payload.get('main', {})]+payload.get('servers', []):
        for key, value in section.items():
            if not isinstance(value, str):
                problems.append('non-string writer value %s' % key);continue
            if key in BOUNDS:
                if not re.fullmatch(r'[0-9]{1,6}', value) or not BOUNDS[key][0] <= int(value) <= BOUNDS[key][1]:
                    problems.append('out-of-bounds %s=%r' % (key, value))
            elif key in FLAGS:
                if value not in ('0', '1'):
                    problems.append('flag %s=%r' % (key, value))
            elif key in ('name', 'channel') and not sane_text(value):
                problems.append('unsane %s=%r' % (key, value[:30]))
            elif key == 'enabled' and value not in ('0', '1'):
                problems.append('flag enabled=%r' % value)
            elif len(value) > 200:
                problems.append('over-long %s (%d)' % (key, len(value)))
    return problems


def make_requests(method, behaviour, rng, count):
    """Yield (body_bytes, args_or_None). args is None for garbage bodies (which are always invalid)."""
    good_factory, oracle = SPECS[method]
    pool = hostile_pool(behaviour, rng)
    for n in range(count):
        if behaviour in (4, 5, 6) and n % 4 == 3:
            body = rng.choice(GARBAGE)
            blank = body.replace(b'\xef\xbb\xbf', b'').strip() in (b'', b'{}')
            yield body, ('EMPTY-BODY' if blank else None)
            continue
        args = good_factory()
        if n % 5 == 0 and behaviour != 9:
            yield encode(args), args   # a valid request in the mix proves valid input still works
            continue
        if method in NOARGS:
            args = {'x': rng.choice(pool)} if rng.random() < .7 else {}
            yield encode(args), args
            continue
        leaves = list(paths(args)) or [()]
        for _ in range(rng.randint(1, 3)):
            leaf = rng.choice(leaves)
            if not leaf:
                break
            roll = rng.random()
            if roll < .12:
                # drop a field
                parent = args
                for part in leaf[:-1]:
                    parent = parent[part]
                if isinstance(parent, dict):
                    parent.pop(leaf[-1], None)
            elif roll < .2:
                args['extra_'+str(rng.randint(0, 9))] = rng.choice(pool)
            else:
                with contextlib.suppress(KeyError, IndexError, TypeError):
                    set_path(args, leaf, rng.choice(pool))
        if behaviour == 8 and rng.random() < .3:
            # a whole structure of the wrong type
            args = rng.choice([[], [args], 'text', 7, None, True, {'a': [args]}])
        if behaviour == 1 and method in ('priority_preview', 'priority_apply') and rng.random() < .5:
            args['ordered'] = ['wg_a']*rng.randint(2, 500) if isinstance(args, dict) else args
        yield encode(args), (args if isinstance(args, dict) else {'__non_object__': True})


def sweep_requests(method, behaviour, seed, rng):
    """Systematic sweep: every leaf of a valid request gets one hostile value (offset by the seed)."""
    good_factory, _ = SPECS[method]
    pool = hostile_pool(behaviour, rng)
    leaves = list(paths(good_factory()))
    for index, leaf in enumerate(leaves):
        args = good_factory()
        value = pool[(index*5+seed*(len(pool)//5+1)) % len(pool)]
        with contextlib.suppress(KeyError, IndexError, TypeError):
            set_path(args, leaf, value)
        yield encode(args), args


def oracle_valid(method, args):
    if args == 'EMPTY-BODY':
        return method in NOARGS
    if args is None or '__non_object__' in (args if isinstance(args, dict) else {}):
        return False
    try:
        return SPECS[method][1](args)
    except Exception:  # an oracle must never decide by exception
        return False


# ---- one persona --------------------------------------------------------------------------------------------------
BEHAVIOURS = ['huge numbers', 'negative and zero', 'floats', 'strings in numeric fields', 'empty and missing',
              'NaN / 1e999 / garbage bodies', 'very long strings', 'unicode, emoji, control chars',
              'wrong types and lists', 'rapid repeats (mixed)']


def persona(fx, behaviour, seed, tally, bad, per_method_calls=8, verbose=False):
    rng = random.Random(behaviour*1000+seed)
    tracemalloc.start()
    rapid = behaviour == 9
    for method in SPECS:
        count = 40 if rapid else per_method_calls
        before = (len(fx.writer_payloads), fx.popen_calls, fx.file_count())
        started = time.perf_counter()
        if not rapid:
            fx.reset_throttle(method)
        stream = list(make_requests(method, behaviour, rng, count))
        if not rapid and method not in NOARGS:
            stream += list(sweep_requests(method, behaviour, seed, rng))
        for body, args in stream:
            if not rapid:
                fx.reset_throttle(method)
            valid = oracle_valid(method, args)
            status, result, raw, error, seconds = invoke(fx, method, body)
            where = '%s b%d s%d' % (method, behaviour, seed)
            key = (method,)

            def flag(kind, detail):
                tally[key]['BAD'] += 1
                bad.append((kind, method, behaviour, seed, detail, body[:120]))
            if error is not None:
                flag('HANG' if isinstance(error, Hang) else 'EXCEPTION', '%s: %s' % (type(error).__name__, str(error)[:100]));continue
            if seconds > HANG_SECONDS:
                flag('SLOW', '%.2fs' % seconds);continue
            if result is None:
                flag('NO-JSON-OUTPUT', raw[:80]);continue
            codes = codes_of(result)
            if any(not isinstance(c, str) or not CODE.fullmatch(c) for c in codes):
                flag('UNCLEAN-CODE', repr(codes)[:100]);continue
            if '"Traceback' in raw or 'Traceback (most recent' in raw:
                flag('TRACEBACK', raw[:80]);continue
            ok = succeeded(method, result, status)
            if ok and not valid:
                flag('ACCEPTED-INVALID', json.dumps(result)[:100]);continue
            if ok and fx.writer_payloads:
                problems = check_payload(fx.writer_payloads[-1])
                if problems:
                    flag('BAD-STORED-VALUE', '; '.join(problems[:3]));continue
            if not ok and not codes:
                flag('REJECTED-WITHOUT-CODE', json.dumps(result)[:100]);continue
            if not ok and valid and method in ('setup_system', 'setup_speed', 'setup_monitor', 'setup_recovery', 'terms_accept', 'monitor_control', 'priority_apply', 'native_confirm', 'priority_preview', 'setup_telegram') and not rapid:
                flag('VALID-REQUEST-REFUSED', json.dumps(result)[:100]);continue
            tally[key]['ACCEPTED' if ok else 'REJECTED'] += 1
            if verbose:
                print(where, 'ACCEPTED' if ok else 'REJECTED', codes)
        if rapid:
            writes = len(fx.writer_payloads)-before[0];procs = fx.popen_calls-before[1]
            files = fx.file_count()-before[2];elapsed = time.perf_counter()-started
            allowed = max(2, int(elapsed/2)+2)
            key = (method,)
            if writes > allowed:
                tally[key]['BAD'] += 1;bad.append(('UNBOUNDED-WRITES', method, behaviour, seed, '%d flash writes in %.1fs' % (writes, elapsed), b''))
            if procs > 3:
                tally[key]['BAD'] += 1;bad.append(('UNBOUNDED-PROCESSES', method, behaviour, seed, '%d processes' % procs, b''))
            if files > 12:
                tally[key]['BAD'] += 1;bad.append(('UNBOUNDED-FILES', method, behaviour, seed, '%d new files' % files, b''))
    # Hostile method names (the CLI takes any string): always a clean refusal, never a traceback or a path/command effect.
    for name in ('bogus', '', 'setup_system;reboot', '../../etc/passwd', 'STATUS', 'x'*5000, 's\u00e9tup', 'status\n', '__class__', 'list '):
        for body in (b'', b'{"a":1}'):
            status, result, raw, error, seconds = invoke(fx, name, body)
            key = ('(unknown method)',)
            code = codes_of(result)
            if error is not None or result is None or not code or any(not CODE.fullmatch(str(c)) for c in code) or succeeded(name, result, status):
                tally[key]['BAD'] += 1
                bad.append(('UNKNOWN-METHOD', repr(name[:30]), behaviour, seed, repr(error or raw[:80]), body))
            else:
                tally[key]['REJECTED'] += 1
    current, peak = tracemalloc.get_traced_memory();tracemalloc.stop()
    if peak > MEMORY_LIMIT:
        bad.append(('MEMORY', '*', behaviour, seed, '%d MiB peak' % (peak >> 20), b''))
        tally[('*',)]['BAD'] += 1


def run_all(verbose=False, per_method_calls=8):
    tally = collections.defaultdict(collections.Counter);bad = []
    with Fixture() as fx:
        for behaviour in range(10):
            for seed in range(5):
                fx.reset_state()
                persona(fx, behaviour, seed, tally, bad, per_method_calls, verbose)
    return tally, bad


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json');parser.add_argument('--verbose', action='store_true');parser.add_argument('--calls', type=int, default=8)
    options = parser.parse_args()
    tally, bad = run_all(options.verbose, options.calls)
    print('%-18s %9s %9s %5s' % ('method', 'ACCEPTED', 'REJECTED', 'BAD'))
    total = collections.Counter()
    for (method,), c in sorted(tally.items()):
        print('%-18s %9d %9d %5d' % (method, c['ACCEPTED'], c['REJECTED'], c['BAD']));total.update(c)
    print('%-18s %9d %9d %5d' % ('TOTAL', total['ACCEPTED'], total['REJECTED'], total['BAD']))
    seen = {}
    for kind, method, b, s, detail, body in bad:
        seen.setdefault((kind, method, detail[:60]), (b, s, detail, body))
    for (kind, method, _), (b, s, detail, body) in sorted(seen.items())[:60]:
        print('BAD %s %s persona b%d/s%d: %s | input %r' % (kind, method, b, s, detail, body))
    if options.json:
        Path(options.json).write_text(json.dumps({'tally': {m[0]: dict(c) for m, c in tally.items()}, 'bad': len(bad)}, indent=1))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
