"""Plan item 7 (2.0.0-lua line): lua/speed_pause.lua, lua/speed.lua and lua/telegram.lua against the Python modules.

Every case runs twice on the same input files: once through speed_pause.py / speed_test.py / telegram_report.py /
report_calendar.py / telegram_state.py (clocks, /proc, uuid and the sender patched), once through the Lua fixture
(tests/lua/speedtg_fixture.lua). The return values, the error codes and the resulting files must be identical,
compared as sorted JSON text so an int never passes for a float.
No network: the Telegram sender and curl are fakes; no real token or chat id is used anywhere.
Runs where lua5.1 exists (homensai-vpn-python39:local)."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

LUA = shutil.which('lua5.1')
TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[0]/'files/usr/lib/homensai-vpn'
FIXTURE = TESTS/'lua/speedtg_fixture.lua'
sys.path.insert(0, str(ROOT))
TZ = 'CET-1CEST,M3.5.0,M10.5.0/3'
os.environ['TZ'] = TZ
time.tzset()

import agent  # noqa: E402
import auto_control  # noqa: E402
import speed_pause as pause  # noqa: E402
import speed_test as speed  # noqa: E402
import telegram_report as report  # noqa: E402
import report_calendar  # noqa: E402
import telegram_state  # noqa: E402

REV = 'c'*32
TX = 'a'*32
NOW = 1761825600.5      # Thu 30 Oct 2025 13:00:00.5 CET
CTX = {}
WORKER_PY = '/usr/bin/python3|'+str((ROOT/'speed_test.py').resolve())+'|run|'
WORKER_LUA = '/usr/bin/lua|/usr/lib/homensai-vpn/lua/speed.lua|run|'


class FakePath(type(Path())):
    """/proc/<pid>/cmdline and /sys/class/net counters from the case context; everything else is the real file."""
    def read_bytes(self):
        text = str(self)
        if text.startswith('/proc/') and text.endswith('/cmdline'):
            line = CTX.get('cmdlines', {}).get(text.split('/')[2])
            if line is None:
                raise FileNotFoundError(text)
            return line.replace('|', '\0').encode()
        return super().read_bytes()

    def read_text(self, *args, **kwargs):
        text = str(self)
        if text.startswith('/sys/class/net/'):
            device, name = text.split('/')[4], text.split('/')[-1]
            row = CTX.get('counters', {}).get(device)
            if row is None:
                raise FileNotFoundError(text)
            return '%d\n' % row[0 if name == 'rx_bytes' else 1]
        return super().read_text(*args, **kwargs)


def canonical(value):
    return json.dumps(value, sort_keys=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@contextmanager
def nolock(*_args, **_kwargs):
    yield


class Uuid:
    def __init__(self, value):
        self.hex = value


def identity(pid):
    if type(pid) is not int or pid < 1:
        raise pause.PauseError('SPEED-PAUSE-UNVERIFIED')
    start = CTX.get('starts', {}).get(str(pid))
    if start is None:
        raise FileNotFoundError(pid)
    return {'pid': pid, 'start': start}


def python_run(case):
    """One case through the Python modules; same shape as the Lua fixture's answer."""
    global CTX
    CTX = case.get('context', {})
    directory = Path(case['dir'])
    kills, spawned, sent = [], [], []
    ctx = CTX

    def popen(argv, **_kwargs):
        spawned.append(argv[-1])
        return type('Child', (), {'pid': ctx['spawn_pid']})()

    def send(config, text):
        sent.append(text)
        failure = ctx.get('send_error')
        if failure:
            if 'http' in failure:
                raise report.rejection(failure['http'], failure.get('retry_after', 300))
            raise report.DeliveryError(failure['code'], failure.get('uncertain', False), failure.get('retry_after', 300))

    def config():
        if ctx.get('config') is None:
            raise ValueError('TELEGRAM-CONFIG')
        return ctx['config']

    with ExitStack() as stack:
        enter = stack.enter_context
        for module, name, value in ((pause, 'RUNTIME', directory), (speed, 'RUNTIME', directory), (speed, 'PERSIST', directory),
                                    (speed, 'JOB', directory/'speed-job.json'), (speed, 'CANCEL', directory/'speed-cancel.json'),
                                    (speed, 'HISTORY', directory/'speed-history.json'), (speed, 'LEDGER', directory/'speed-quota.json'),
                                    (agent, 'RUNTIME', directory), (auto_control, 'RUNTIME', directory),
                                    (pause, 'Path', FakePath), (speed, 'Path', FakePath),
                                    (pause, 'control_lock', nolock), (speed, 'control_lock', nolock), (auto_control, 'control_lock', nolock)):
            enter(patch.object(module, name, value))
        enter(patch.object(pause, 'boot', return_value=ctx.get('boot', 'test-boot')))
        enter(patch.object(pause, 'identity', side_effect=identity))
        enter(patch.object(pause, 'revision_locked', return_value=ctx.get('revision')))
        enter(patch.object(pause.os, 'getpid', return_value=ctx.get('pid', 1)))
        enter(patch.object(pause.os, 'kill', side_effect=lambda pid, sig: kills.append([pid, int(sig)])))
        enter(patch('time.monotonic', return_value=ctx.get('clock', 0)))
        enter(patch('time.time', return_value=ctx.get('wall', NOW)))
        enter(patch('time.sleep', return_value=None))
        enter(patch.object(speed, 'inventory', return_value=ctx.get('inventory')))
        enter(patch('retention_settings.configured_days', return_value=ctx.get('retention_days', 7)))
        enter(patch.object(speed.uuid, 'uuid4', return_value=Uuid(ctx.get('uuid', 'b'*32))))
        enter(patch.object(speed.subprocess, 'Popen', side_effect=popen))
        enter(patch('pair_auto.read_state', return_value=ctx.get('pair_state', {})))
        enter(patch('pair_auto.intent', return_value=ctx.get('pair_intent', {})))
        enter(patch.object(report, 'config_snapshot', side_effect=config))
        enter(patch.object(report, 'send_message', side_effect=send))
        enter(patch('rpc_throttle.allow', return_value=ctx.get('allow', True)))
        enter(patch.object(report.uuid, 'uuid4', return_value=Uuid(ctx.get('uuid', 'b'*32))))
        op, a = case['op'], case.get('args', [])
        items = (lambda value: None if value is None else tuple(value))
        try:
            if op == 'gate':
                result = pause.gate(a[0], quiescent=lambda: a[1] is True)
            elif op == 'public':
                result = pause.public()
            elif op == 'load':
                result = pause.load()
            elif op == 'participants':
                with patch.object(pause.subprocess, 'run', return_value=type('R', (), {'stdout': json.dumps(ctx['services']).encode()})()):
                    result = pause.participants()
            elif op == 'interrupted':
                result = pause.interrupted(a[0])
            elif op == 'release':
                result = pause.release(a[0])
            elif op == 'cpu_parse':
                with patch.object(pause, 'Path', lambda *_: type('P', (), {'read_text': lambda self: a[0]})()):
                    result = pause.cpu_snapshot()
            elif op == 'speed_start':
                result = speed.start(a[0], automatic=a[1] is True)
            elif op == 'speed_cancel':
                result = speed.cancel()
            elif op == 'active_job':
                result = speed.active_job()
            elif op == 'public_live':
                result = speed.public_live()
            elif op == 'public_status':
                result = speed.public_status()
            elif op == 'append_history':
                result = speed.append_history(a[0])
            elif op == 'load_history':
                result = speed.load_history()
            elif op == 'prune_history':
                result = speed.prune_history()
            elif op == 'reserve_quota':
                result = speed.reserve_quota(a[0], a[1], a[2])
            elif op == 'validate_request':
                result = speed.validate_request(a[0], a[1])
            elif op == 'observe_traffic':
                result = speed.observe_traffic(a[0], a[1])
            elif op == 'automatic_new':
                with patch.object(speed, 'settings', return_value=speed.settings(ctx['inventory'])):
                    active = speed.automatic_new(a[0], None if a[1] is None else set(a[1]))
                result = sorted(active)
            elif op == 'is_global':
                import ipaddress
                result = ipaddress.IPv4Address(a[0]).is_global
            elif op == 'format_report':
                result = report.format_report(a[0], a[1], a[2], items(a[3]))
            elif op == 'format_period':
                result = report_calendar.format_period(a[0], a[1], a[2], items(a[3]))
            elif op == 'delta_lines':
                result = report.delta_lines(a[0], a[1], a[2])
            elif op == 'prepare':
                result = list(report_calendar.prepare(a[0], a[1], a[2]))
            elif op == 'limited_text':
                result = report_calendar.limited_text(a[0], a[1])
            elif op == 'valid':
                result = telegram_state.valid(a[0])
            elif op == 'parse_items':
                from telegram_items import parse
                result = list(parse(a[0]))
            elif op == 'deliver':
                public, state, delivered = report.deliver(a[0], a[1], a[2])
                result = [public, state, delivered, sent]
            elif op == 'send_test':
                result = [report.send_test(), sent]
            elif op == 'retry_unknown':
                result = report.retry_unknown()
            elif op == 'load_state':
                result = list(telegram_state.load(directory))
            elif op == 'save_state':
                result = telegram_state.save(a[0], directory)
            else:
                raise AssertionError(op)
            error = None
        except (pause.PauseError, speed.SpeedError, report.DeliveryError, ValueError, KeyError, TypeError, OSError) as failure:
            result = None
            error = getattr(failure, 'code', None) or (str(failure) if isinstance(failure, ValueError) and str(failure).isupper() else 'ERROR')
    files = {}
    for name in case.get('files', []):
        path = directory/name
        files[name] = json.loads(path.read_text()) if path.exists() else None
    return {'result': result, 'error': error, 'files': files, 'kills': kills, 'spawned': spawned}


def lua_run(cases):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as stream:
        json.dump(cases, stream)
    try:
        output = subprocess.run([LUA, str(FIXTURE), stream.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, timeout=300, env=dict(os.environ, TZ=TZ)).stdout
    finally:
        os.unlink(stream.name)
    return json.loads(output)


def normalise_error(value):
    if value is None:
        return None
    return value if value.isupper() and not value.startswith('LUA:') else 'ERROR'


class Differential(unittest.TestCase):
    """Base: build cases (initial files written to a Python and a Lua directory), run both, compare."""
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp());self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cases = []

    def case(self, op, args=(), context=None, files=None, initial=None, label=None):
        index = len(self.cases)
        dirs = []
        for side in ('py', 'lua'):
            directory = self.tmp/('%03d-%s' % (index, side));directory.mkdir()
            for name, value in (initial or {}).items():
                (directory/name).write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
            dirs.append(str(directory))
        self.cases.append({'op': op, 'args': list(args), 'context': context or {}, 'files': list(files or []),
                           'dirs': dirs, 'label': label or op})

    def compare(self):
        lua_cases = [dict(case, dir=case['dirs'][1]) for case in self.cases]
        lua = lua_run(lua_cases)
        for case, lua_result in zip(self.cases, lua):
            py = python_run(dict(case, dir=case['dirs'][0]))
            with self.subTest(case['label']):
                self.assertEqual(normalise_error(lua_result['error']), normalise_error(py['error']), 'error code')
                if py['error'] is None:
                    self.assertEqual(canonical(self.adjust(case, lua_result['result'])), canonical(self.adjust(case, py['result'])), 'result')
                self.assertEqual(canonical(lua_result['files']), canonical(py['files']), 'files')
                self.assertEqual(lua_result['kills'], py['kills'], 'signals')
                self.assertEqual(len(lua_result['spawned']), len(py['spawned']), 'workers started')
        return lua

    def adjust(self, case, value):
        return value


# ----------------------------------------------------------------------------------------------------------------------
# speed pause
# ----------------------------------------------------------------------------------------------------------------------
INTENT_FILES = {'pair-auto-control.json': b'{"mode":"on","revision":"' + REV.encode() + b'","time":1761825000.25}',
                'auto-control.json': b'{"mode":"on"}'}


def fingerprints(files):
    return {name: (sha(files[name]) if name in files else None) for name in pause.INTENTS}


def pause_row(**changes):
    row = {'schema': 1, 'tx': TX, 'boot': 'test-boot', 'worker': {'pid': 43, 'start': 430},
           'owners': {'auto': {'pid': 41, 'start': 410}, 'monitor': {'pid': 42, 'start': 420}}, 'acks': {},
           'revision': REV, 'intents': fingerprints(INTENT_FILES), 'phase': 'PAUSING', 'deadline': 1060.5, 'auto_was_on': True}
    row.update(changes)
    return row


def pause_files(row, **extra):
    files = dict(INTENT_FILES)
    files['auto-control-revision.json'] = {'revision': REV}
    files['speed-pause.json'] = row
    files.update(extra)
    return files


def pause_context(**changes):
    context = {'clock': 1000.25, 'wall': NOW, 'boot': 'test-boot', 'pid': 42, 'starts': {'41': 410, '42': 420, '43': 430},
               'cmdlines': {'43': WORKER_LUA+TX+'|'}, 'revision': REV}
    context.update(changes)
    return context


PAUSE_FILES = ['speed-pause.json', 'speed-cancel.json']


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class SpeedPauseMatchesPython(Differential):
    def test_gate_public_load_interrupted_release(self):
        ack = {'owner': {'pid': 42, 'start': 420}, 'time': 999.5}
        self.case('gate', ['monitor', False], pause_context(), PAUSE_FILES, pause_files(pause_row()), 'monitor busy: no ack')
        self.case('gate', ['monitor', False], pause_context(), PAUSE_FILES, pause_files(pause_row(acks={'monitor': ack})), 'busy withdraws ack')
        self.case('gate', ['monitor', True], pause_context(), PAUSE_FILES, pause_files(pause_row()), 'monitor acks')
        self.case('gate', ['auto', True], pause_context(pid=41), PAUSE_FILES, pause_files(pause_row(acks={'monitor': ack})), 'auto acks')
        self.case('gate', ['auto', True], pause_context(pid=99, starts={'41': 410, '42': 420, '43': 430, '99': 990}), PAUSE_FILES,
                  pause_files(pause_row()), 'not the owner')
        changed = pause_files(pause_row());changed['pair-auto-control.json'] = b'{"mode":"off"}'
        self.case('gate', ['auto', True], pause_context(pid=41), PAUSE_FILES, changed, 'new command supersedes, worker up')
        self.case('gate', ['auto', True], pause_context(pid=41, starts={'41': 410, '42': 420}), PAUSE_FILES, changed, 'superseded, worker gone')
        job = {'tx': TX, 'pid': 43, 'state': 'RUNNING'}
        self.case('gate', ['auto', True], pause_context(pid=41, clock=1070.0), PAUSE_FILES,
                  pause_files(pause_row(), **{'speed-job.json': job}), 'deadline: own Lua worker signalled')
        self.case('gate', ['auto', True], pause_context(pid=41, clock=1070.0, cmdlines={'43': WORKER_PY+TX+'|'}), PAUSE_FILES,
                  pause_files(pause_row(), **{'speed-job.json': job}), 'deadline: own Python worker signalled')
        self.case('gate', ['auto', True], pause_context(pid=41, clock=1070.0, cmdlines={'43': '/bin/sh|other|'}), PAUSE_FILES,
                  pause_files(pause_row(), **{'speed-job.json': job}), 'deadline: unproven worker resumes')
        resuming = pause_row(phase='RESUMING', resume_time=NOW-1, resume_deadline=1010.0)
        self.case('gate', ['monitor', True], pause_context(), PAUSE_FILES, pause_files(resuming), 'resuming: monitor first')
        self.case('gate', ['monitor', True], pause_context(starts={'42': 420, '43': 430}), PAUSE_FILES, pause_files(resuming), 'resuming: no auto')
        fresh = {'time': NOW, 'profiles': [{'administrative_state': 'enabled', 'time': NOW}, {'administrative_state': 'disabled'}]}
        stale = {'time': NOW, 'profiles': [{'administrative_state': 'enabled', 'time': NOW-30}]}
        self.case('gate', ['auto', True], pause_context(pid=41), PAUSE_FILES, pause_files(resuming, **{'status.json': fresh}), 'resuming: auto after fresh pass')
        self.case('gate', ['auto', True], pause_context(pid=41), PAUSE_FILES, pause_files(resuming, **{'status.json': stale}), 'resuming: auto waits')
        self.case('gate', ['auto', True], pause_context(pid=41, clock=1011.0), PAUSE_FILES, pause_files(resuming, **{'status.json': stale}), 'resuming: deadline')
        self.case('gate', ['auto', True], pause_context(pid=41), PAUSE_FILES, pause_files(resuming, **{'status.json': {'time': None}}), 'resuming: bad status')
        for label, row in (('schema', pause_row(schema=2)), ('boot', pause_row(boot='other')), ('role', pause_row(owners={'speed': {'pid': 41, 'start': 410}})),
                           ('ack owner', pause_row(acks={'auto': {'owner': {'pid': 41, 'start': 1}, 'time': 1.0}})),
                           ('deadline', pause_row(deadline=2000.0)), ('worker float', pause_row(worker={'pid': 43.0, 'start': 430})),
                           ('intents', pause_row(intents={'auto-control.json': None})), ('tx', pause_row(tx='xyz')),
                           ('resume fields', pause_row(phase='RESUMING')), ('phase', pause_row(phase='DONE'))):
            self.case('gate', ['auto', True], pause_context(pid=41), PAUSE_FILES, pause_files(row), 'invalid '+label)
            self.case('load', [], pause_context(), [], pause_files(row), 'load invalid '+label)
            self.case('public', [], pause_context(), [], pause_files(row), 'public invalid '+label)
        both = {'auto': {'owner': {'pid': 41, 'start': 410}, 'time': 999.0}, 'monitor': ack}
        self.case('public', [], pause_context(), [], pause_files(pause_row(acks=both, phase='PAUSED')), 'public paused')
        self.case('public', [], pause_context(), [], pause_files(pause_row(acks=both, phase='RESUMING', resume_time=NOW, resume_deadline=1020.0)), 'public resuming')
        self.case('public', [], pause_context(clock=1061.0), [], pause_files(pause_row(acks=both)), 'public expired')
        self.case('public', [], pause_context(), [], {}, 'public none')
        self.case('load', [], pause_context(), [], pause_files(pause_row(acks=both)), 'load valid')
        self.case('interrupted', [TX], pause_context(), [], pause_files(pause_row()), 'interrupted no')
        self.case('interrupted', [TX], pause_context(), [], pause_files(pause_row(), **{'speed-cancel.json': {'tx': TX}}), 'interrupted cancel')
        self.case('interrupted', [TX], pause_context(starts={'42': 420, '43': 430}), [], pause_files(pause_row()), 'interrupted owner gone')
        self.case('interrupted', [TX], pause_context(clock=1061.0), [], pause_files(pause_row()), 'interrupted deadline')
        self.case('release', [TX], pause_context(), PAUSE_FILES, pause_files(pause_row()), 'release resumes')
        self.case('release', [TX], pause_context(starts={'43': 430}), PAUSE_FILES, pause_files(pause_row()), 'release removes')
        self.case('cpu_parse', ['cpu  10 20 30 40 50 60 70 80 0 0\ncpu0 1 2 3 4 5 6 7 8\n'], pause_context(), [], {}, 'cpu ok')
        self.case('cpu_parse', ['cpu  10 20 30\n'], pause_context(), [], {}, 'cpu short')
        self.compare()

    def test_participants_accept_the_lua_daemons_and_refuse_anything_else(self):
        services = {'homensai-vpn': {'instances': {'monitor': {'running': True, 'pid': 42}, 'native': {'running': True, 'pid': 41}}}}
        for label, cmdlines in (('lua both', {'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|daemon|',
                                               '41': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/auto.lua|daemon|'}),
                                ('python both', {'42': '/usr/bin/python3|/usr/lib/homensai-vpn/agent.py|daemon|',
                                                 '41': '/usr/bin/python3|/usr/lib/homensai-vpn/native_switch.py|daemon|'}),
                                ('lua monitor python auto', {'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|daemon|',
                                                             '41': '/usr/bin/python3|/usr/lib/homensai-vpn/native_switch.py|daemon|'}),
                                ('roles swapped', {'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/auto.lua|daemon|',
                                                   '41': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|daemon|'}),
                                ('not a daemon', {'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|compare|',
                                                  '41': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/auto.lua|daemon|'}),
                                ('prefix only', {'42': '/usr/bin/lua|/tmp/usr/lib/homensai-vpn/lua/monitor.lua|daemon|',
                                                 '41': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/auto.lua|daemon|'})):
            self.case('participants', [], pause_context(cmdlines=cmdlines, services=services), [], {}, label)
        stopped = {'homensai-vpn': {'instances': {'monitor': {'running': True, 'pid': 42}, 'native': {'running': False}}}}
        self.case('participants', [], pause_context(cmdlines={'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|daemon|'}, services=stopped), [], {}, 'auto stopped')
        lua = self.compare()
        self.assertEqual(lua[0]['result'], {'auto': {'pid': 41, 'start': 410}, 'monitor': {'pid': 42, 'start': 420}})
        self.assertEqual(lua[3]['error'], 'SPEED-PAUSE-UNVERIFIED')

    def test_participants_of_hv_core_own_both_roles_in_the_monitor_process(self):
        # Lua plan item 8: `monitor` runs hv_core.lua daemon (monitor + Auto), `native` only stands by
        services = {'homensai-vpn': {'instances': {'monitor': {'running': True, 'pid': 42}, 'native': {'running': True, 'pid': 41}}}}
        core = '/usr/bin/lua|/usr/lib/homensai-vpn/lua/hv_core.lua|daemon|'
        standby = '/usr/bin/lua|/usr/lib/homensai-vpn/lua/hv_core.lua|standby|'
        for label, cmdlines in (('hv-core', {'42': core, '41': standby}),
                                ('hv-core fallen back', {'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|daemon|',
                                                         '41': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/auto.lua|daemon|'}),
                                ('standby without hv-core', {'42': '/usr/bin/lua|/usr/lib/homensai-vpn/lua/monitor.lua|daemon|', '41': standby}),
                                ('hv-core as native', {'42': core, '41': core})):
            self.case('participants', [], pause_context(cmdlines=cmdlines, services=services), [], {}, label)
        stopped = {'homensai-vpn': {'instances': {'monitor': {'running': False}, 'native': {'running': True, 'pid': 41}}}}
        self.case('participants', [], pause_context(cmdlines={'41': standby}, services=stopped), [], {}, 'hv-core down')
        lua = self.compare()
        self.assertEqual(lua[0]['result'], {'auto': {'pid': 42, 'start': 420}, 'monitor': {'pid': 42, 'start': 420}})
        self.assertEqual(lua[1]['result'], {'auto': {'pid': 41, 'start': 410}, 'monitor': {'pid': 42, 'start': 420}})
        for index in (2, 3, 4):
            self.assertEqual(lua[index]['error'], 'SPEED-PAUSE-UNVERIFIED')


# ----------------------------------------------------------------------------------------------------------------------
# speed test
# ----------------------------------------------------------------------------------------------------------------------
PROFILES = [{'id': 'wireguard:peer_1', 'name': 'Vienna', 'protocol': 'wireguard', 'interface': 'wgclient1'},
            {'id': 'openvpn:1_2', 'name': 'Paris', 'protocol': 'openvpn', 'interface': None}]
SETTINGS = {'speed_enabled': True, 'speed_auto_new': True, 'speed_budget_mib': 8, 'speed_duration': 5, 'speed_streams': 2,
            'speed_daily_mib': 128, 'speed_busy_mbps': 2}
INVENTORY = {'profiles': PROFILES, 'servers': [], 'settings': SETTINGS}
REQUEST = {'profiles': ['wireguard:peer_1'], 'budget_mib': 8, 'duration': 5, 'streams': 2}
TRAFFIC = {'monotonic': 990.5, 'rate_bps': 1000.5, 'counters': {}, 'scope': 'vpn'}
SPEED_FILES = ['speed-job.json', 'speed-quota.json', 'speed-cancel.json', 'speed-history.json', 'speed-history.backup.json',
               'speed-traffic.json', 'speed-auto-pending.json']


def speed_context(**changes):
    context = {'clock': 1000.25, 'wall': NOW, 'boot': 'test-boot', 'pid': 42, 'starts': {'43': 430}, 'cmdlines': {'43': WORKER_LUA+TX+'|'},
               'inventory': INVENTORY, 'spawn_pid': 777, 'uuid': 'd'*32, 'retention_days': 7, 'revision': REV}
    context.update(changes)
    return context


def envelope(data):
    return {'schema': 1, 'data': data, 'sha256': agent.checksum(data)}


def history_row(stamp, ident='wireguard:peer_1', code=None):
    return {'id': ident, 'name': 'Vienna', 'protocol': 'wireguard', 'channel': 'default', 'time': stamp, 'endpoint': speed.HOST,
            'method': 'bounded-HTTPS-payload-goodput', 'scope': 'router-originated-IPv4', 'payload_budget_bytes': 8*speed.MIB,
            'overhead_in_budget': False, 'code': code, 'latency_ms': 23.4,
            'download': {'payload_bytes': 6291456, 'seconds': 2.5, 'mbps': 20.133}, 'upload': {'payload_bytes': 2097152, 'seconds': 1.25, 'mbps': 13.422}}


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class SpeedTestMatchesPython(Differential):
    def adjust(self, case, value):
        # the reply's server_time is the patched wall clock on both sides
        return value

    def test_validation_quota_and_history(self):
        known = [{'id': 'a'}]
        good = {'profiles': ['a'], 'budget_mib': 8, 'duration': 5, 'streams': 2}
        for label, update in (('good', {}), ('dup', {'profiles': ['a', 'a']}), ('unknown', {'profiles': ['x']}), ('streams', {'streams': 5}),
                              ('bool', {'budget_mib': True}), ('float', {'duration': 5.0}), ('empty', {'profiles': []}),
                              ('extra', {'extra': 1}), ('nine', {'profiles': ['a']*9})):
            self.case('validate_request', [dict(good, **update), known], speed_context(), [], {}, 'validate '+label)
        self.case('reserve_quota', [8*speed.MIB, 128*speed.MIB, NOW], speed_context(), ['speed-quota.json'], {}, 'quota fresh')
        days = {'2025-10-%02d' % n: 1024 for n in range(20, 30)}
        self.case('reserve_quota', [8*speed.MIB, 128*speed.MIB, NOW], speed_context(), ['speed-quota.json'],
                  {'speed-quota.json': {'data': days, 'sha256': agent.checksum(days)}}, 'quota keeps 7 days')
        full = {'2025-10-30': 127*speed.MIB}
        self.case('reserve_quota', [8*speed.MIB, 128*speed.MIB, NOW], speed_context(), ['speed-quota.json'],
                  {'speed-quota.json': {'data': full, 'sha256': agent.checksum(full)}}, 'quota daily limit')
        self.case('reserve_quota', [1, 10, NOW], speed_context(), ['speed-quota.json'],
                  {'speed-quota.json': {'data': {'bad': 'value'}, 'sha256': 'wrong'}}, 'quota corrupt')
        rows = [history_row(NOW-100), history_row(NOW-50, code='SPEED-NETWORK')]
        self.case('append_history', [rows], speed_context(), ['speed-history.json', 'speed-history.backup.json'], {}, 'history first')
        old = {'results': [history_row(NOW-9*86400), history_row(NOW-3600)], 'retention_days': 7}
        self.case('append_history', [rows], speed_context(), ['speed-history.json', 'speed-history.backup.json'],
                  {'speed-history.json': envelope(old)}, 'history append and age')
        self.case('load_history', [], speed_context(), [], {'speed-history.json': b'corrupt', 'speed-history.backup.json': envelope(old)}, 'history backup')
        self.case('load_history', [], speed_context(), [], {'speed-history.json': b'corrupt'}, 'history corrupt')
        self.case('load_history', [], speed_context(retention_days=1), [], {'speed-history.json': envelope(old)}, 'history retention 1 day')
        self.case('prune_history', [], speed_context(retention_days=1), ['speed-history.json', 'speed-history.backup.json'],
                  {'speed-history.json': envelope(old)}, 'prune')
        self.case('prune_history', [], speed_context(), ['speed-history.json', 'speed-history.backup.json'], {}, 'prune nothing')
        many = {'results': [history_row(NOW-1000+i) for i in range(499)], 'retention_days': 7, 'history_truncated': 2}
        self.case('append_history', [rows], speed_context(), ['speed-history.json'], {'speed-history.json': envelope(many)}, 'history cap 500')
        self.compare()

    def test_start_cancel_and_views(self):
        traffic = {'speed-traffic.json': TRAFFIC}
        disabled = dict(INVENTORY, settings=dict(SETTINGS, speed_enabled=False))
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES, traffic, 'start ok')
        self.case('speed_start', [REQUEST, False], speed_context(inventory=disabled), SPEED_FILES, traffic, 'disabled')
        self.case('speed_start', [REQUEST, True], speed_context(inventory=dict(INVENTORY, settings=dict(SETTINGS, speed_auto_new=False))), SPEED_FILES, traffic, 'auto disabled')
        self.case('speed_start', [dict(REQUEST, budget_mib=16), False], speed_context(), SPEED_FILES, traffic, 'config limit')
        self.case('speed_start', [dict(REQUEST, budget_mib=16), False], speed_context(inventory=dict(INVENTORY, settings=dict(SETTINGS, speed_budget_mib='x'))), SPEED_FILES, traffic, 'config error')
        self.case('speed_start', [dict(REQUEST, streams=9), False], speed_context(), SPEED_FILES, traffic, 'request')
        self.case('speed_start', [REQUEST, False], speed_context(wall=1000.5), SPEED_FILES, traffic, 'clock unset')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES, dict(traffic, **{'speed-job.json': {'started': NOW+60}}), 'clock backward')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES,
                  dict(traffic, **{'speed-job.json': {'state': 'RUNNING', 'tx': TX, 'pid': 43, 'started': NOW-200}}), 'busy')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES,
                  dict(traffic, **{'speed-job.json': {'state': 'DONE', 'tx': TX, 'started': NOW-30}}), 'cooldown')
        self.case('speed_start', [REQUEST, True], speed_context(), SPEED_FILES,
                  dict(traffic, **{'speed-job.json': {'state': 'DONE', 'tx': TX, 'started': NOW-200}}), 'automatic cooldown')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES, dict(traffic, **{'native-status.json': {'state': 'APPLYING'}}), 'switching')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES, {}, 'traffic unknown')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES, {'speed-traffic.json': dict(TRAFFIC, rate_bps=None)}, 'traffic none')
        self.case('speed_start', [REQUEST, False], speed_context(clock=1200.0), SPEED_FILES, traffic, 'traffic stale')
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES, {'speed-traffic.json': dict(TRAFFIC, rate_bps=3e6)}, 'traffic busy')
        full = {'2025-10-30': 127*speed.MIB}
        self.case('speed_start', [REQUEST, False], speed_context(), SPEED_FILES,
                  dict(traffic, **{'speed-quota.json': {'data': full, 'sha256': agent.checksum(full)}}), 'daily limit')
        paused = pause_files(pause_row(acks={}), **traffic)
        self.case('speed_start', [REQUEST, False], speed_context(starts={'41': 410, '42': 420, '43': 430}), SPEED_FILES, paused, 'pause busy')
        running = {'state': 'RUNNING', 'tx': TX, 'pid': 43, 'started': NOW-20}
        self.case('speed_cancel', [], speed_context(), SPEED_FILES, {'speed-job.json': running}, 'cancel running')
        self.case('speed_cancel', [], speed_context(starts={}), SPEED_FILES, {'speed-job.json': running}, 'cancel lost worker')
        self.case('speed_cancel', [], speed_context(), SPEED_FILES, {}, 'cancel idle')
        for label, job, ctx in (('queued young', {'state': 'QUEUED', 'tx': TX, 'started': NOW-5}, {'cmdlines': {}}),
                                ('queued old', {'state': 'QUEUED', 'tx': TX, 'started': NOW-50}, {'cmdlines': {}}),
                                ('timeout alive', {'state': 'FAILED', 'code': 'SPEED-WORKER-TIMEOUT', 'tx': TX, 'pid': 43}, {}),
                                ('done', {'state': 'DONE', 'tx': TX, 'pid': 43}, {})):
            self.case('active_job', [], speed_context(**ctx), [], {'speed-job.json': job}, 'active '+label)
        live = [{'id': 'wireguard:peer_1', 'phase': 'download', 'samples': [[0.5, 12.5, None], [1.0, None, 3.25], [0.75, 1.0, None], [1.5, 1.0, 2.0], [2.0, 20000000.0, None], 'x'],
                 'download_mbps': 12.5, 'updated': NOW, 'code': 'SPEED-NETWORK', 'download_bytes': 100},
                {'id': 'other', 'phase': 'done', 'samples': []}, {'id': 'wireguard:peer_1', 'phase': 'bogus', 'samples': []}]
        job = {'state': 'RUNNING', 'tx': TX, 'pid': 43, 'started': NOW-20, 'profiles': ['wireguard:peer_1'], 'live': live,
               'preparation': 'testing', 'code': 'SPEED-X', 'completed': 0, 'monotonic_deadline': 2000.0}
        self.case('public_live', [], speed_context(), [], {'speed-job.json': job}, 'live running')
        self.case('public_live', [], speed_context(cmdlines={}), [], {'speed-job.json': job}, 'live lost')
        self.case('public_live', [], speed_context(), [], {'speed-job.json': dict(job, profiles=['bad id!'])}, 'live idle')
        self.case('public_live', [], speed_context(), [], {}, 'live none')
        history = {'speed-history.json': envelope({'results': [history_row(NOW-100)], 'retention_days': 7})}
        self.case('public_status', [], speed_context(), ['speed-job.json'], dict(history, **{'speed-job.json': job}), 'status running')
        self.case('public_status', [], speed_context(clock=2020.0), ['speed-job.json'], dict(history, **{'speed-job.json': job}), 'status expired worker')
        self.case('public_status', [], speed_context(), ['speed-job.json'], {'speed-job.json': dict(job, state='DONE', finished=NOW-5), 'speed-history.json': b'corrupt'}, 'status corrupt history')
        self.compare()

    def test_monitor_side_traffic_and_automatic_tests(self):
        rows = [{'device': 'wgclient1'}, {'device': 'wgclient1'}, {'device': 'bad dev'}, {'device': 'wgclient2'}, {'id': 'x'}]
        counters = {'wgclient1': [1000, 2000], 'wgclient2': [500, 600]}
        self.case('observe_traffic', [rows, 'vpn'], speed_context(counters=counters), ['speed-traffic.json'], {}, 'traffic first')
        before = {'monotonic': 990.25, 'counters': {'wgclient1': 1000, 'wgclient2': 100}, 'rate_bps': None, 'scope': 'vpn'}
        self.case('observe_traffic', [rows, 'vpn'], speed_context(counters=counters), ['speed-traffic.json'], {'speed-traffic.json': before}, 'traffic rate')
        self.case('observe_traffic', [rows, 'wan'], speed_context(counters=counters, clock=1100.0), ['speed-traffic.json'], {'speed-traffic.json': before}, 'traffic gap')
        reset = dict(before, counters={'wgclient1': 99999, 'wgclient2': 100})
        self.case('observe_traffic', [rows, 'vpn'], speed_context(counters=counters), ['speed-traffic.json'], {'speed-traffic.json': reset}, 'traffic reset')
        monitored = [{'id': 'wireguard:peer_1', 'interface': 'wgclient1'}, {'id': 'openvpn:1_2', 'interface': None}]
        traffic = {'speed-traffic.json': TRAFFIC}
        self.case('automatic_new', [monitored, None], speed_context(), SPEED_FILES, traffic, 'baseline')
        self.case('automatic_new', [monitored, []], speed_context(), SPEED_FILES, traffic, 'new profile starts')
        self.case('automatic_new', [monitored, []], speed_context(), SPEED_FILES, {}, 'new profile stays pending')
        self.case('automatic_new', [monitored, ['wireguard:peer_1']], speed_context(), SPEED_FILES,
                  dict(traffic, **{'speed-auto-pending.json': {'profiles': ['wireguard:peer_1', 'gone'], 'last_code': 'SPEED-TRAFFIC-BUSY'}}), 'pending retried')
        for address in ('104.16.248.249', '10.1.2.3', '100.64.0.1', '192.0.0.9', '8.8.8.8', '224.0.0.1', '255.255.255.255', '0.1.2.3', '172.31.9.9', '198.19.0.1'):
            self.case('is_global', [address], speed_context(), [], {}, 'global '+address)
        self.compare()


# ----------------------------------------------------------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------------------------------------------------------
MONTH = '2025-10'
STATUS = {
    'time': NOW-12.25,
    'profiles': [{'id': 'wireguard:peer_1', 'name': 'Wien Ä', 'protocol': 'wireguard', 'interface': 'wgclient1', 'role': 'source', 'code': None, 'rtt_ms': 123.4},
                 {'id': 'openvpn:1_2', 'name': 'Paris', 'protocol': 'openvpn', 'interface': 'ovpnclient2', 'role': 'target', 'code': 'VPN-003', 'rtt_ms': None},
                 {'id': 'wireguard:peer_3', 'name': 'Lyon', 'protocol': 'wireguard', 'interface': 'wgclient3', 'role': 'unknown', 'code': 'DNS-001'},
                 {'id': 'wireguard:peer_4', 'name': 'Off', 'protocol': 'wireguard', 'interface': None}],
    'events': [{'time': NOW-7200, 'profile': 'wireguard:peer_1', 'role': 'source', 'code': 'VPN-001'},
               {'time': NOW-1800, 'profile': 'openvpn:1_2', 'role': 'target', 'code': 'VPN-003'},
               {'time': NOW-60, 'profile': 'wireguard:peer_3', 'role': 'unknown'},
               {'time': NOW-30, 'code': 'STORAGE-001'}, {'time': NOW-20, 'profile': None, 'code': 'OK'}],
    'accounting': {'gaps': 3, 'months': {MONTH: {'rx': 123456789, 'tx': 987654321}, '2025-09': {'rx': 5, 'tx': 6}},
                   'days': {'2025-10-29': {'rx': 1000000000, 'tx': 500000000, 'observed': True, 'gaps': 1},
                            '2025-10-28': {'rx': 1, 'tx': 2, 'observed': False}, '2025-10-26': {'rx': 3000000, 'tx': 4000000, 'observed': True, 'gaps': 0},
                            '2025-09-30': {'rx': 7, 'tx': 8, 'observed': True}},
                   'activity': {'openvpn:1_2': {'name': 'Paris', 'days': {'2025-10-29': {'up': 3600, 'down': 7200, 'unknown': 0, 'connections': 2, 'failures': 1}}},
                                'wireguard:peer_1': {'name': 'Wien Ä', 'days': {'2025-10-29': {'up': 86000.5, 'down': 0, 'unknown': 400, 'connections': 5, 'failures': 0},
                                                                                 '2025-10-27': {'up': 100, 'down': 0, 'unknown': 0, 'connections': 1, 'failures': 0}}},
                                'wireguard:peer_3': {'days': {'2025-10-29': {'up': 10, 'down': 0, 'unknown': 0, 'connections': 0, 'failures': 0}}}},
                   'retention': {'activity_days_dropped': 1},
                   'wan': {'months': {MONTH: {'rx': 5000000000, 'tx': 250000000}}, 'days': {'2025-10-29': {'rx': 9, 'tx': 1, 'observed': True, 'gaps': 2}}}},
    'native_failover': {'state': 'COMMITTED', 'alarm': 'PAIR-RECOVERY-REQUIRED', 'tx': 'PRIVATE'},
    'native_history': {'events': [{'time': NOW-600, 'state': 'COMMITTED', 'codes': ['CLIENT-CONFIRMED', 'bad code!'], 'trial': True},
                                  {'time': NOW-300, 'state': 'bad state', 'codes': []}],
                       'months': {MONTH: {'attempts': 4, 'trials_passed': 2, 'committed': 3, 'rollbacks': 1}},
                       'days': {'2025-10-29': {'attempts': 2, 'committed': 1, 'automatic_attempts': 1, 'automatic_committed': 1, 'server_switches': 1},
                                '2025-10-01': {'attempts': 1, 'rollbacks': 1}},
                       'daily_since': NOW-3*86400}}
CONFIG = {'telegram_enabled': '1', 'telegram_token': '123456:synthetic-not-a-token', 'telegram_chat': '-100123', 'telegram_interval': '60',
          'telegram_schedule': 'interval', 'telegram_hour': '7', 'telegram_weekly': '', 'telegram_monthly': '', 'telegram_items': ''}
STATE_FILES = ['telegram-state.json', 'telegram-state.backup.json', 'telegram-test.json', 'telegram-retry.json']


def telegram_context(**changes):
    context = {'clock': 1000.25, 'wall': NOW, 'config': CONFIG, 'uuid': 'e'*32}
    context.update(changes)
    return context


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class TelegramMatchesPython(Differential):
    def test_report_text(self):
        for items in (None, [], ['servers'], ['events', 'traffic'], ['controller', 'controller_events', 'controller_totals', 'gaps', 'delta']):
            self.case('format_report', [STATUS, 60, NOW, items], telegram_context(), [], {}, 'report %s' % items)
        self.case('format_report', [STATUS, 5, NOW, None], telegram_context(), [], {}, 'report 5 min')
        self.case('format_report', [{}, 60, NOW, None], telegram_context(), [], {}, 'report empty')
        self.case('format_report', [{'native_failover': {'state': 'bad value'}, 'native_history': {'error': 'HISTORY-001'}}, 60, NOW, None], telegram_context(), [], {}, 'report bad history')
        many = dict(STATUS, events=[{'time': NOW-i, 'profile': 'p%d' % i, 'code': 'VPN-00%d' % (i % 3)} for i in range(40)])
        self.case('format_report', [many, 60, NOW, ['events']], telegram_context(), [], {}, 'report 20 events')
        long = dict(STATUS, profiles=[dict(STATUS['profiles'][0], name='Сервер 😀 %d ' % i * 3) for i in range(80)])
        self.case('format_report', [long, 60, NOW, ['servers']], telegram_context(), [], {}, 'report cut at 4000')
        winter = 1767225600.25  # 1 Jan 2026 01:00 CET
        self.case('format_report', [STATUS, 60, winter, None], telegram_context(), [], {}, 'report winter')
        for kind, start, end in (('daily', 1761692400, 1761778800), ('weekly', 1761001200, 1761606000), ('monthly', 1759269600, 1761951600)):
            for items in (None, ['servers'], ['traffic', 'gaps']):
                job = {'kind': kind, 'key': kind+':x', 'start': start, 'end': end}
                self.case('format_period', [STATUS, job, NOW, items], telegram_context(), [], {}, 'period %s %s' % (kind, items))
        self.case('format_period', [{}, {'kind': 'daily', 'key': 'daily:x', 'start': 1761692400, 'end': 1761778800}, NOW, None], telegram_context(), [], {}, 'period empty')
        servers = {'accounting': {'activity': {'p%02d' % i: {'name': 'S%d' % i, 'days': {'2025-10-29': {'up': 10*i, 'down': (i % 3)*60, 'unknown': 0, 'connections': i, 'failures': 0}}} for i in range(12)}}}
        self.case('format_period', [servers, {'kind': 'daily', 'key': 'daily:x', 'start': 1761692400, 'end': 1761778800}, NOW, ['servers']], telegram_context(), [], {}, 'period 12 servers')
        snapshot = {'time': NOW-86400*3, 'vpn': {MONTH: 1000000000, '2025-09': 6}, 'wan': {MONTH: 1}}
        for label, saved in (('no snapshot', {}), ('delta', {'snapshot': snapshot}), ('discontinuity', {'snapshot': dict(snapshot, vpn={MONTH: 5e12})}),
                             ('old months', {'snapshot': dict(snapshot, vpn={'2025-01': 5})}), ('empty wan', {'snapshot': dict(snapshot, wan={})})):
            self.case('delta_lines', [STATUS, saved, NOW], telegram_context(), [], {}, 'delta '+label)
        text = 'Ж'*3990 + '😀'*20
        for units in (4000, 3995, 10):
            self.case('limited_text', [text, units], telegram_context(), [], {}, 'limited %d' % units)
        self.case('limited_text', ['short', 4000], telegram_context(), [], {}, 'limited short')
        for value in (None, '', 'none', 'servers,gaps,bogus', 'delta'):
            self.case('parse_items', [value], telegram_context(), [], {}, 'items %r' % value)
        self.compare()

    def test_calendar(self):
        instants = [NOW, NOW-6*3600, 1761526800.5, 1761523200.75, 1759276800.5, 1759270000.5, 1774746000.5, 1774738800.5, 1767225600.25]
        for now in instants:
            for options in ({}, {'telegram_schedule': 'daily', 'telegram_hour': '7'}, {'telegram_schedule': 'daily', 'telegram_hour': '23', 'telegram_weekly': '0', 'telegram_monthly': '0'},
                            {'telegram_interval': '5'}, {'telegram_interval': '99999', 'telegram_hour': '0'}):
                self.case('prepare', [options, {}, now], telegram_context(), [], {}, 'prepare %s %s' % (now, options))
        started = {'calendar_started': {'daily': NOW-10*86400, 'weekly': NOW-30*86400, 'monthly': NOW-90*86400}, 'sent': NOW-30,
                   'period_keys': {'weekly': 'weekly:2025-10-20'}, 'uncertain': {'monthly:2025-09-01': NOW-100}}
        self.case('prepare', [{'telegram_schedule': 'daily'}, started, NOW], telegram_context(), [], {}, 'prepare catch up')
        self.case('prepare', [{}, {'sent': NOW-4000}, NOW], telegram_context(), [], {}, 'prepare interval due')
        for bad in ({'telegram_schedule': 'weekly'}, {'telegram_hour': '24'}, {'telegram_interval': 'x'}):
            self.case('prepare', [bad, {}, NOW], telegram_context(), [], {}, 'prepare bad %s' % bad)
        self.compare()

    def test_state_validation_and_files(self):
        good = {'sent': NOW, 'attempt': NOW, 'calendar_started': {'daily': NOW}, 'period_keys': {'interval': 'interval:1', 'daily': 'daily:2025-10-29'},
                'uncertain': {'weekly:2025-10-20': NOW}, 'config_fingerprint': 'f'*64, 'last_code': 'TELEGRAM-DELIVERED',
                'snapshot': {'time': NOW, 'wan': {MONTH: 5}, 'vpn': {}}, 'retry_nonce': 'a'*32, 'retry_after': 300, 'confirmed_reports': 2}
        for label, value in (('good', good), ('empty', {}), ('extra key', dict(good, token='x')), ('negative', dict(good, sent=-1)),
                             ('period key', dict(good, period_keys={'daily': 'weekly:1'})), ('started key', dict(good, calendar_started={'interval': 1})),
                             ('uncertain key', dict(good, uncertain={'daily:x': 1})), ('fingerprint', dict(good, config_fingerprint='XYZ')),
                             ('code', dict(good, last_code='OTHER')), ('snapshot month', dict(good, snapshot={'wan': {'2026-1': 1}})),
                             ('snapshot key', dict(good, snapshot={'x': 1})), ('list', [])):
            self.case('valid', [value], telegram_context(), [], {}, 'valid '+label)
        self.case('load_state', [], telegram_context(), [], {'telegram-state.json': envelope(good)}, 'load good')
        self.case('load_state', [], telegram_context(), [], {'telegram-state.json': b'corrupt', 'telegram-state.backup.json': envelope(good)}, 'load backup')
        self.case('load_state', [], telegram_context(), [], {'telegram-state.json': good}, 'load legacy')
        self.case('load_state', [], telegram_context(), [], {'telegram-state.json': envelope(dict(good, token='x'))}, 'load corrupt')
        self.case('load_state', [], telegram_context(), [], {}, 'load none')
        self.case('save_state', [good], telegram_context(), STATE_FILES, {'telegram-state.json': envelope({'sent': 1})}, 'save with backup')
        self.case('save_state', [dict(good, token='x')], telegram_context(), STATE_FILES, {}, 'save invalid')
        self.compare()

    def test_delivery_rounds(self):
        due = {'sent': NOW-4000.5}
        self.case('deliver', [STATUS, due, NOW], telegram_context(config=dict(CONFIG, telegram_enabled='0')), STATE_FILES, {}, 'disabled')
        self.case('deliver', [STATUS, due, NOW], telegram_context(config=None), STATE_FILES, {}, 'config unreadable')
        self.case('deliver', [STATUS, due, NOW], telegram_context(config=dict(CONFIG, telegram_chat='@x')), STATE_FILES, {}, 'chat invalid')
        self.case('deliver', [STATUS, {'token': 1}, NOW], telegram_context(), STATE_FILES, {}, 'state corrupt')
        self.case('deliver', [STATUS, due, NOW], telegram_context(), STATE_FILES, {}, 'interval sent')
        self.case('deliver', [STATUS, due, NOW], telegram_context(config=dict(CONFIG, telegram_items='servers,delta')), STATE_FILES, {}, 'interval with delta')
        self.case('deliver', [STATUS, {'sent': NOW-100}, NOW], telegram_context(), STATE_FILES, {}, 'not due')
        self.case('deliver', [STATUS, {'sent': NOW+100}, NOW], telegram_context(), STATE_FILES, {}, 'clock backward')
        self.case('deliver', [STATUS, dict(due, attempt=NOW-10, retry_after=300, last_code='TELEGRAM-RATE-LIMIT'), NOW], telegram_context(), STATE_FILES, {}, 'retry wait')
        self.case('deliver', [STATUS, due, NOW], telegram_context(send_error={'http': 429, 'retry_after': 5000}), STATE_FILES, {}, 'rate limited')
        self.case('deliver', [STATUS, due, NOW], telegram_context(send_error={'code': 'TELEGRAM-DELIVERY-UNKNOWN', 'uncertain': True}), STATE_FILES, {}, 'uncertain')
        uncertain = dict(due, uncertain={'interval:%d' % (NOW//3600): NOW-50}, config_fingerprint=hashlib.sha256(b'-100123').hexdigest())
        self.case('deliver', [STATUS, uncertain, NOW], telegram_context(), STATE_FILES, {}, 'uncertain kept')
        self.case('deliver', [STATUS, uncertain, NOW], telegram_context(), STATE_FILES, {'telegram-retry.json': {'id': 'r'*32, 'time': NOW-5}}, 'retry request')
        self.case('deliver', [STATUS, dict(due, config_fingerprint='0'*64, confirmed_reports=7), NOW], telegram_context(), STATE_FILES, {}, 'new chat resets')
        calendar = {'sent': NOW-30, 'calendar_started': {'daily': NOW-10*86400, 'weekly': NOW-30*86400, 'monthly': NOW-90*86400}}
        self.case('deliver', [STATUS, calendar, NOW], telegram_context(config=dict(CONFIG, telegram_schedule='daily')), STATE_FILES, {}, 'calendar catch up')
        self.case('deliver', [STATUS, calendar, NOW], telegram_context(config=dict(CONFIG, telegram_schedule='daily'), send_error={'http': 403}), STATE_FILES, {}, 'calendar refused')
        self.case('send_test', [], telegram_context(), STATE_FILES, {}, 'test delivered')
        self.case('send_test', [], telegram_context(send_error={'http': 401}), STATE_FILES, {}, 'test token rejected')
        self.case('send_test', [], telegram_context(), STATE_FILES, {'telegram-test.json': {'attempt': NOW-10}}, 'test rate limit')
        self.case('send_test', [], telegram_context(config=None), STATE_FILES, {}, 'test config')
        self.case('retry_unknown', [], telegram_context(), STATE_FILES, {}, 'retry queued')
        self.case('retry_unknown', [], telegram_context(allow=False), STATE_FILES, {}, 'retry throttled')
        self.compare()


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class TelegramResponseClassification(unittest.TestCase):
    """telegram.classify(curl exit, HTTP status, body) against send_message() over urllib on the same answers."""
    def python(self, response=None, error=None):
        import socket
        import ssl
        import urllib.error

        class Response:
            def __init__(self, body):self.body = body
            def __enter__(self):return self
            def __exit__(self, *args):return False
            def read(self, limit):return self.body[:limit]
        config = {'telegram_token': '1:synthetic', 'telegram_chat': '123'}
        side = {'http': lambda code: urllib.error.HTTPError('u', code, 'x', {}, None),
                'cert': lambda _: urllib.error.URLError(ssl.SSLCertVerificationError()),
                'dns': lambda _: urllib.error.URLError(socket.gaierror()),
                'refused': lambda _: urllib.error.URLError(ConnectionRefusedError())}
        with patch.object(report.urllib.request, 'urlopen', side_effect=side[error[0]](error[1]) if error else None,
                          return_value=None if error else Response(response)):
            try:
                report.send_message(config, 'text')
                return 'ok'
            except report.DeliveryError as failure:
                return [failure.code, failure.uncertain, failure.retry_after]

    def test_same_codes(self):
        rows = [((0, 200, '{"ok":true,"result":{}}'), dict(response=b'{"ok":true,"result":{}}')),
                ((0, 200, '{"ok":false,"error_code":429,"parameters":{"retry_after":4000}}'), dict(response=b'{"ok":false,"error_code":429,"parameters":{"retry_after":4000}}')),
                ((0, 200, '{"ok":false,"error_code":400}'), dict(response=b'{"ok":false,"error_code":400}')),
                ((0, 200, '{"ok":false,"error_code":500}'), dict(response=b'{"ok":false,"error_code":500}')),
                ((0, 200, '[1]'), dict(response=b'[1]')), ((0, 200, 'not json'), dict(response=b'not json')),
                ((0, 401, ''), dict(error=('http', 401))), ((0, 403, ''), dict(error=('http', 403))), ((0, 502, ''), dict(error=('http', 502))),
                ((60, None, None), dict(error=('cert', None))), ((6, None, None), dict(error=('dns', None))), ((7, None, None), dict(error=('refused', None)))]
        cases = [{'op': 'classify', 'args': [list(lua_args)[0], lua_args[1], lua_args[2]], 'context': {}, 'files': [], 'dir': tempfile.gettempdir()}
                 for lua_args, _ in rows]
        lua = lua_run(cases)
        for (lua_args, python_args), answer in zip(rows, lua):
            with self.subTest(lua_args):
                self.assertEqual(answer['result'], self.python(**python_args))



LUA_SUPERVISOR = r"""
package.path=arg[1]..'/?.lua;'..package.path
local runtime=arg[2]
local canon=require('canon');canon.configure({runtime=runtime})
local mio=require('monitor_io');mio.configure({RUNTIME=runtime,PERSIST=runtime})
local pause=require('speed_pause')
local d=pause.router({runtime=runtime,persist=runtime})
print('ready');io.stdout:flush()
local seen={}
for i=1,300 do
  local quiet=pause.gate(d,'auto')
  seen[#seen+1]=quiet and 'q' or '.'
  if i>3 and not mio.exists(runtime..'/speed-pause.json') then break end
  d.sleep(0.1)
end
print(table.concat(seen))
"""


def uptime():
    with open('/proc/uptime') as stream:
        return float(stream.read().split()[0])


@unittest.skipUnless(LUA and shutil.which('flock'), 'Lua 5.1 and flock(1) needed; use homensai-vpn-python39:local')
class RealProcessInterop(unittest.TestCase):
    """The known bug of the Lua line: the Python speed worker's quiet window under lua_auto=1.
    A real Lua process runs speed_pause.gate('auto') with the router deps (real /proc identity, boot id, flock control
    lock, sha256sum) on a temporary RUNTIME; the real Python acquire() waits for its acknowledgement and release()
    hands the window back. time.monotonic is read from /proc/uptime here, the clock the Lua line uses (on the router
    both clocks are the same; a PC that has slept would make them differ)."""
    def test_python_worker_is_acknowledged_by_the_lua_supervisor(self):
        runtime = Path(tempfile.mkdtemp(prefix='hvspeed'))
        self.addCleanup(shutil.rmtree, runtime, True)
        os.chmod(runtime, 0o700)
        (runtime/'auto-control-revision.json').write_text(json.dumps({'revision': REV}))
        (runtime/'pair-auto-control.json').write_bytes(INTENT_FILES['pair-auto-control.json'])
        (runtime/'native-status.json').write_text(json.dumps({'state': 'OBSERVING'}))
        script = runtime/'supervisor.lua'
        script.write_text(LUA_SUPERVISOR)
        child = subprocess.Popen([LUA, str(script), str(ROOT/'lua'), str(runtime)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: child.poll() is None and child.kill())
        self.assertEqual(child.stdout.readline().strip(), b'ready')
        owner = pause.identity(child.pid)
        with ExitStack() as stack:
            for module in (pause, auto_control, agent):
                stack.enter_context(patch.object(module, 'RUNTIME', runtime))
            stack.enter_context(patch.object(pause, 'participants', return_value={'auto': owner}))
            stack.enter_context(patch.object(pause.time, 'monotonic', side_effect=uptime))
            stack.enter_context(patch('pair_auto.read_state', return_value={}))
            stack.enter_context(patch('pair_auto.intent', return_value={'mode': 'on', 'revision': REV, 'time': 1.0}))
            job = {'tx': TX, 'monotonic_deadline': uptime()+60}
            started = time.time()
            pause.acquire(job)
            row = pause.load()
            self.assertEqual(row['phase'], 'PAUSED')
            self.assertEqual(row['acks']['auto']['owner'], owner)
            self.assertLess(time.time()-started, 10)
            self.assertTrue(pause.public()['auto_paused'])
            pause.release(TX)
        output, errors = child.communicate(timeout=60)
        self.assertEqual(child.returncode, 0, errors)
        self.assertIn('q', output.decode())
        self.assertTrue(output.decode().strip().endswith('.'), 'the supervisor resumed once the window ended')
        self.assertFalse((runtime/'speed-pause.json').exists(), 'the Lua supervisor removed the finished window (no monitor owner)')


from test_lua_monitor_item2 import Dispatcher as _Dispatcher  # noqa: E402


class SpeedTelegramDispatcher(_Dispatcher):
    """rpcd dispatcher: speed_start/speed_cancel/speed_live/telegram_retry to the Lua monitor (agent.py on fallback or
    without the Lua monitor), telegram_test to the Lua CLI sender in its own process (agent.py when it prints nothing)."""
    def setUp(self):
        super().setUp()
        sender = self.bin/'telegram-cli'
        sender.write_text('#!/bin/sh\nprintf "%s\n" "$*" >> "$QA_LOG.cli"\n[ -n "$QA_CLI" ] && printf "%s\n" "$QA_CLI"\ncat >/dev/null\nexit 0\n')
        sender.chmod(sender.stat().st_mode | stat.S_IEXEC)
        text = self.plugin.read_text()
        self.assertIn('/usr/bin/lua /usr/lib/homensai-vpn/lua/telegram.lua', text)
        self.plugin.write_text(text.replace('[ -f /usr/lib/homensai-vpn/lua/telegram.lua ]', '[ -f %s ]' % sender)
                               .replace('/usr/bin/lua /usr/lib/homensai-vpn/lua/telegram.lua', str(sender)))

    def test_speed_and_retry_go_to_the_lua_monitor(self):
        for method in ('speed_start', 'speed_cancel', 'speed_live', 'telegram_retry'):
            with self.subTest(method=method):
                self.assertEqual(self.run_plugin('call', method, request=b'{}'), {'lua': True, 'request': {}})
        reply = self.run_plugin('call', 'speed_start', request=b'{"profiles":["a"]}', mode='fallback')
        self.assertEqual(reply, {'agent': ['call', 'speed_start'], 'stdin': '{"profiles":["a"]}'})
        self.assertEqual(self.run_plugin('call', 'speed_cancel', request=b'{}', mode='timeout')['agent'], ['call', 'speed_cancel'])
        self.assertEqual(self.leftovers(), [])

    def test_without_the_lua_monitor_speed_calls_go_to_agent_not_the_status_client(self):
        socket_path = self.runtime/'status.sock'
        socket_path.write_text('')  # a status.sock path exists: the old light client must still not take these calls
        for method in ('speed_start', 'speed_live', 'telegram_retry', 'telegram_test'):
            with self.subTest(method=method):
                self.assertEqual(self.run_plugin('call', method, request=b'{}', ready=False)['agent'], ['call', method])

    def test_telegram_test_uses_the_lua_sender_process_and_falls_back_when_it_prints_nothing(self):
        os.environ['QA_CLI'] = '{"code":"TELEGRAM-TEST-DELIVERED","delivered":true}'
        try:
            self.assertEqual(self.run_plugin('call', 'telegram_test', request=b'{}'), {'code': 'TELEGRAM-TEST-DELIVERED', 'delivered': True})
            os.environ['QA_CLI'] = ''
            self.assertEqual(self.run_plugin('call', 'telegram_test', request=b'{}')['agent'], ['call', 'telegram_test'])
        finally:
            os.environ.pop('QA_CLI', None)
        self.assertEqual((Path(str(self.log)+'.cli')).read_text().splitlines(), ['call telegram_test', 'call telegram_test'])
        self.assertFalse(self.log.exists(), 'the monitor object is not used for the delivery test')
        self.assertEqual(self.leftovers(), [])


if __name__ == '__main__':
    unittest.main()
