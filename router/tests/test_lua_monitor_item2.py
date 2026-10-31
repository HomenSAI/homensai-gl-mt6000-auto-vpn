"""Lua monitor items 2/3 (2.0.0-lua-alpha4) against the Python readers and writers.

* Files the Lua monitor writes are accepted by the Python code that reads them on a rollback to the Python line:
  ping-response-history.json (PingResponseHistory.load, same public view), probe-history.json and
  probe-boost.json (probe_policy.Booster: same public answer), native-history.json written by history.lua
  (native_history.History: same public view), checkpoint.json (checkpoint_schema + checksum).
* setup_probe/setup_response/setup_stats: the Lua payloads are the UCI keys/values of setup_config/stats_mode
  for valid input and the same refusal codes for invalid input.
* The status reply carries the page fields with the Python key sets.
* The rpcd dispatcher: the Lua path (request/reply RAM files through `ubus call homensai-vpn-lua rpc`), the
  fallback to agent.py with the same request bytes, the old path when the Lua monitor is not running.
* The init script starts lua/monitor.lua only with option lua_monitor '1'.
Runs where lua5.1 exists (homensai-vpn-python39:local); the shell tests need a POSIX sh."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

LUA = shutil.which('lua5.1')
TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[0]/'files/usr/lib/homensai-vpn'
FIXTURE = TESTS/'lua/monitor_fixture.lua'
PLUGIN = TESTS.parents[0]/'files/usr/libexec/rpcd/homensai-vpn'
INIT = TESTS.parents[0]/'files/etc/init.d/homensai-vpn'
sys.path.insert(0, str(ROOT))


def lua(*args):
    return subprocess.run([LUA, str(FIXTURE), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True, timeout=120).stdout.decode()


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaFilesForPython(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(tempfile.mkdtemp())
        output = lua('item2', str(cls.directory))
        assert output.strip() == 'ok', output
        cls.meta = json.loads((cls.directory/'meta.json').read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def read(self, name):
        return json.loads((self.directory/name).read_text())

    def test_ping_history_file_loads_in_python_with_the_same_public_view(self):
        from ping_response_history import PingResponseHistory
        history = PingResponseHistory.load(self.directory/'ping-response-history.json')
        self.assertIsNone(history.notice, 'checksum and schema accepted')
        self.assertEqual(len(history.data['rows']), 2)
        self.assertEqual(history.public(self.meta['now']), self.read('ping_public.json'))
        # and Python can save it again (validate passes)
        target = self.directory/'resaved.json'
        from agent import atomic_json
        history.save(target, atomic_json, self.meta['now'])
        self.assertIsNone(PingResponseHistory.load(target).notice)

    def test_probe_policy_files_and_public_answer_match_python_booster(self):
        import probe_policy
        from agent import atomic_json, read_json
        persist = self.directory/'persist'; runtime = self.directory/'runtime'
        persist.mkdir(exist_ok=True); runtime.mkdir(exist_ok=True)
        shutil.copy(self.directory/'probe-history.json', persist/'probe-history.json')
        shutil.copy(self.directory/'probe-boost.json', runtime/'probe-boost.json')
        booster = probe_policy.Booster(runtime, persist, atomic_json, read_json)
        rows = booster._history()
        self.assertEqual([row['kind'] for row in rows], ['level', 'boost-start', 'boost-end'])
        self.assertEqual([row['sequence'] for row in rows], [1, 2, 3])
        self.assertEqual(rows[2]['result'], 'false-alarm')
        settings = self.meta['settings']
        self.assertEqual(booster.public(settings, self.meta['now']), self.read('booster_public.json'))
        page = probe_policy.history_page(persist, {'after': 0, 'until': 0}, read_json, self.meta['now'])
        self.assertEqual(page['summary'], {'sequence': 3, 'rows': 3})

    def test_native_history_written_by_lua_is_read_by_python_with_the_same_public_view(self):
        import native_history
        history = native_history.History(self.directory, detail_days=7)
        public = history.public(now=self.meta['now'])
        self.assertEqual(public, self.read('native_history_public.json'))
        self.assertEqual(public['sequence'], 2)

    def test_checkpoint_and_switch_timing(self):
        import checkpoint_schema
        from agent import read_json, checksum
        envelope = read_json(self.directory/'checkpoint.json')
        data = checkpoint_schema.validate(envelope)
        self.assertEqual(envelope['sha256'], checksum(data))
        import switch_timing
        reply = self.read('status_reply.json')
        self.assertEqual(reply['switch_timing'], switch_timing.read(self.directory))

    def test_status_reply_carries_the_page_fields_with_python_key_sets(self):
        reply = self.read('status_reply.json')
        status = self.read('status.json')
        for key in ('switch_timing', 'auto_control', 'manual_switch', 'manual_switch_control', 'channel_path', 'probe_policy',
                    'stats_mode', 'native_history', 'website_response_history', 'speed_pause', 'speed_tests', 'server_time',
                    'lua_backend', 'response_metric', 'stats_reset'):
            self.assertIn(key, reply, key)
        self.assertEqual(set(reply['auto_control']), {'requested', 'requested_at', 'request_source', 'request_action', 'activation_source',
                                                     'pair_phase', 'failure', 'control_revision', 'until', 'reboot_autostart', 'return_result'})
        import probe_policy
        from agent import atomic_json, read_json
        empty = self.directory/'empty'; empty.mkdir(exist_ok=True)
        python_keys = set(probe_policy.Booster(empty, empty, atomic_json, read_json).public({}, 0))
        self.assertEqual(set(reply['probe_policy']), python_keys)
        self.assertEqual(reply['stats_mode']['mode'], 'diagnostic')
        self.assertEqual(reply['website_response_history']['metric'], 'icmp-rtt-ms')
        self.assertNotIn('events', reply['native_history'], 'history split out like agent.status_reply')
        self.assertIn('native_history.events', reply['history_split'])
        # computed by the Lua monitor (lua/page_controls.lua, pair_manual.controls shape), no bridge placeholder
        self.assertEqual(reply['manual_switch_control'], {'available': False, 'mode': 'continuous-pair',
                                                          'time': reply['manual_switch_control']['time']})
        self.assertFalse(reply['manual_switch_control']['available'])
        self.assertEqual(reply['scan'], {'state': 'IDLE'})
        self.assertEqual(status['lua_backend']['so_mark'], False)
        self.assertEqual(status['lua_backend']['monitor'], 'lua')
        self.assertEqual(status['profiles'][0]['exit_country'], 'DE')


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class VendorObserverMatchesPython(unittest.TestCase):
    """vendor.lua against vendor_observation.VendorObserver on the same snapshots (uuid4 made deterministic)."""
    @staticmethod
    def profile(identifier, section, interface, group='1'):
        protocol = identifier.split(':')[0]
        return {'id': identifier, 'section': section, 'protocol': protocol, 'name': section, 'interface': interface,
                'vendor_tunnel_id': protocol+':'+interface if interface else None, 'vendor_profile_group_id': protocol+':'+group,
                'administrative_state': 'enabled'}

    @staticmethod
    def measured(identifier, now, code=None, ifindex=20, device='wgclient'):
        return {'id': identifier, 'time': now, 'code': code, 'scope': 'router-originated', 'lan_path_verified': False, 'device': device,
                'mark': 4096, 'table': '53', 'ifindex': ifindex, 'https_success': 3, 'dns_ok': True, 'rtt_ms': 12.5,
                'exit_ip': '93.184.216.34', 'exit_country': 'DE', 'administrative_state': 'enabled',
                'probe_checks': [{'target': 'one.one.one.one', 'result': 'ok', 'http_status': 200, 'elapsed_ms': 40.5},
                                 {'target': 'evil', 'result': 'ok'}, {'target': 'dns.google', 'result': 'weird'}]}

    def test_same_groups_events_and_rows(self):
        import vendor_observation
        from unittest.mock import patch
        settings = {'plan_source': 'wireguard:peer_7', 'plan_target': 'wireguard:peer_8',
                    'plan_source_tunnel': 'wireguard:wgclient', 'plan_target_tunnel': 'wireguard:wgclient2'}
        base = {'profiles': [self.profile('wireguard:peer_7', 'peer_7', 'wgclient'), self.profile('wireguard:peer_8', 'peer_8', 'wgclient2'),
                             self.profile('openvpn:1_2', '1_2', None)], 'settings': settings}
        swapped = {'profiles': [self.profile('wireguard:peer_9', 'peer_9', 'wgclient'), self.profile('wireguard:peer_8', 'peer_8', 'wgclient2')],
                   'settings': settings}
        dup = {'profiles': [self.profile('wireguard:peer_7', 'peer_7', 'wgclient'), self.profile('wireguard:peer_7', 'peer_7', 'wgclient2')],
               'settings': settings}
        m = self.measured
        steps = [
            {'before': base, 'after': base, 'now': 1000.5, 'measured': [m('wireguard:peer_7', 1000.5), m('wireguard:peer_8', 1000.5, device='wgclient2', ifindex=21)]},
            {'before': base, 'after': base, 'now': 1010.5, 'measured': [m('wireguard:peer_7', 1010.5), m('wireguard:peer_8', 1010.5, device='wgclient2', ifindex=21)]},
            {'before': base, 'after': base, 'now': 1020.5, 'measured': [m('wireguard:peer_7', 1020.5, ifindex=22), m('wireguard:peer_8', 1020.5, code='VENDOR-IDENTITY-CHANGED')]},
            {'before': base, 'after': swapped, 'now': 1030.5, 'measured': [m('wireguard:peer_7', 1030.5)]},
            {'before': swapped, 'after': swapped, 'now': 1040.5, 'measured': [m('wireguard:peer_9', 1040.5), {'id': 'bad id!', 'time': 1}]},
            {'before': dup, 'after': dup, 'now': 1050.5, 'measured': [m('wireguard:peer_7', 1050.5)]},
            {'before': base, 'after': base, 'now': 900.5, 'measured': [m('wireguard:peer_7', 900.5)]},
        ]
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        path = folder/'scenario.json'
        path.write_text(json.dumps({'steps': steps}))
        actual = json.loads(lua('vendor', str(path)))
        counter = iter(range(1, 1000))

        class Fake:
            def __init__(self):
                self.hex = '%032x' % next(counter)
        observer = vendor_observation.VendorObserver()
        with patch.object(vendor_observation.uuid, 'uuid4', Fake):
            expected = [list(observer.observe(step['before'], step['after'], step['measured'], step['now'])) for step in steps]
        expected = json.loads(json.dumps(expected))
        self.assertEqual(len(actual), len(expected))
        for index, (lua_step, python_step) in enumerate(zip(actual, expected)):
            with self.subTest(step=index):
                for row in lua_step[1]:
                    if 'exit_country' in row:
                        self.assertEqual(row.pop('exit_country'), 'DE', 'kept next to exit_ip (Lua addition)')
                self.assertEqual(lua_step[0], python_step[0])
                self.assertEqual(lua_step[1], python_step[1])


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class SetupPayloadsMatchSetupConfig(unittest.TestCase):
    CASES = {
        'setup_probe': ['{"level":1,"boost":false}', '{"level":2,"boost":true}', '{"level":3,"boost":false}', '{"level":4,"boost":true}',
                        '{"level":5,"boost":false}', '{"level":0,"boost":true}', '{"level":6,"boost":true}', '{"level":3.0,"boost":true}',
                        '{"level":"3","boost":true}', '{"level":3,"boost":1}', '{"level":3}', '{"boost":true}', '{"level":3,"boost":true,"x":1}', '{}'],
        'setup_response': ['{"metric":"icmp-1.1.1.1"}', '{"metric":"icmp-8.8.8.8","compare":true}', '{"metric":"icmp-9.9.9.9","fast_switch":false}',
                           '{"metric":"websites","compare":false,"fast_switch":true}', '{"metric":"icmp-1.1.1.2"}', '{"metric":"websites","compare":1}',
                           '{"metric":"websites","x":true}', '{"compare":true}', '{}', '{"metric":5}',
                           # owner ping interval (10..300 s, step 10): the same keys, values and refusal codes
                           '{"metric":"icmp-1.1.1.1","ping_interval":10}', '{"metric":"icmp-1.1.1.1","ping_interval":60}',
                           '{"metric":"websites","compare":true,"fast_switch":false,"ping_interval":300}',
                           '{"metric":"icmp-8.8.8.8","ping_interval":5}', '{"metric":"icmp-8.8.8.8","ping_interval":0}',
                           '{"metric":"icmp-8.8.8.8","ping_interval":15}', '{"metric":"icmp-8.8.8.8","ping_interval":310}',
                           '{"metric":"icmp-8.8.8.8","ping_interval":-10}', '{"metric":"icmp-8.8.8.8","ping_interval":60.0}',
                           '{"metric":"icmp-8.8.8.8","ping_interval":"60"}', '{"metric":"icmp-8.8.8.8","ping_interval":true}',
                           '{"metric":"icmp-8.8.8.8","ping_interval":null}', '{"metric":"icmp-8.8.8.8","ping_interval":[60]}',
                           '{"metric":"bad","ping_interval":5}', '{"ping_interval":60}',
                           '{"metric":"icmp-8.8.8.8","compare":1,"ping_interval":5}'],
        'setup_stats': ['{"mode":"work"}', '{"mode":"diagnostic","hours":24}', '{"mode":"diagnostic","hours":72}', '{"mode":"diagnostic","hours":168}',
                        '{"mode":"diagnostic","hours":336}', '{"mode":"diagnostic","hours":48}', '{"mode":"diagnostic","hours":24.0}',
                        '{"mode":"diagnostic"}', '{"mode":"work","hours":24}', '{"mode":"x"}', '{}'],
    }
    NOW = 1761825600.7

    def python(self, method, arguments):
        import setup_config
        import stats_mode
        try:
            if method == 'setup_probe':
                return 'OK', setup_config.probe_payload(arguments)['main']
            if method == 'setup_response':
                return 'OK', setup_config.response_payload(arguments)['main']
            return 'OK', stats_mode.payload(arguments, self.NOW)['main']
        except ValueError as error:
            return 'ERR', str(error)

    def test_same_keys_values_and_codes(self):
        for method, cases in self.CASES.items():
            for text in cases:
                with self.subTest(method=method, request=text):
                    kind, expected = self.python(method, json.loads(text))
                    actual = lua('setup', method, text, repr(self.NOW)).strip()
                    if kind == 'OK':
                        self.assertTrue(actual.startswith('OK '), actual)
                        self.assertEqual(json.loads(actual[3:]), expected)
                    else:
                        self.assertEqual(actual, 'ERR '+expected)

    def test_lua_writer_allows_exactly_the_keys_setup_save_lua_allows(self):
        text = (ROOT/'setup_save.lua').read_text()
        lua_setup = (ROOT/'lua/setup.lua').read_text()
        for key in ('response_metric', 'response_compare', 'fast_switch', 'stats_mode', 'stats_until', 'probe_level', 'probe_boost',
                    'interval', 'measure_interval', 'ping_interval'):
            self.assertIn(key+'=true', text, key)
            self.assertIn(key+'=true', lua_setup, key)


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh'), 'POSIX shell required')
class Dispatcher(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.runtime = self.root/'run'; self.runtime.mkdir()
        self.bin = self.root/'bin'; self.bin.mkdir()
        agent = self.bin/'agent.py'
        agent.write_text('import json,sys\nprint(json.dumps({"agent":sys.argv[1:],"stdin":sys.stdin.read()}))\n')
        ubus = self.bin/'ubus'
        # fake ubus: records its arguments; behaviour from $QA_UBUS: ok (writes the reply file), fallback, missing, timeout
        ubus.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$QA_LOG"\nmsg=$6\n'
                        'req=$(printf "%s" "$msg" | sed -n \'s/.*"request_file":"\\([^"]*\\)".*/\\1/p\')\n'
                        'out=$(printf "%s" "$msg" | sed -n \'s/.*"reply_file":"\\([^"]*\\)".*/\\1/p\')\n'
                        'case "$QA_UBUS" in\n'
                        ' ok) printf \'{"lua":true,"request":%s}\' "$(cat "$req")" > "$out"; printf \'{\\n\\t"ok": true\\n}\\n\';;\n'
                        ' fallback) printf \'{\\n\\t"fallback": true\\n}\\n\';;\n'
                        ' missing) exit 4;;\n'
                        ' timeout) exit 7;;\n'
                        'esac\n')
        ubus.chmod(ubus.stat().st_mode | stat.S_IEXEC)
        if not os.access(str(ubus), os.X_OK):
            # The offline CI sandbox mounts its tmpfs noexec: the fake ubus can never run there.
            self.skipTest('temporary directory is mounted noexec')
        self.log = self.root/'ubus.log'
        self.plugin = self.root/'plugin'
        self.plugin.write_text(PLUGIN.read_text().replace('\r\n', '\n')
                               .replace('/var/run/homensai-vpn', str(self.runtime))
                               .replace('/usr/lib/homensai-vpn/agent.py', str(agent))
                               .replace('/usr/bin/python3', sys.executable))

    def run_plugin(self, *arguments, request=b'', mode='ok', ready=True):
        marker = self.runtime/'lua-monitor.ready'
        if ready:marker.write_text('{}')
        elif marker.exists():marker.unlink()
        env = dict(os.environ, PATH=str(self.bin)+':'+os.environ.get('PATH', ''), QA_UBUS=mode, QA_LOG=str(self.log))
        result = subprocess.run(['sh', str(self.plugin)]+list(arguments), input=request, capture_output=True, timeout=30, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def leftovers(self):
        return sorted(p.name for p in self.runtime.iterdir() if p.name.startswith('rpc-'))

    def test_lua_answers_reads_and_setup_through_ram_files(self):
        for method in ('status', 'events', 'history', 'auto_live', 'inventory', 'setup_probe', 'setup_response', 'setup_stats', 'pair_manual',
                       'native_start', 'native_stop', 'fault_start', 'fault_cancel'):
            with self.subTest(method=method):
                reply = self.run_plugin('call', method, request=b'{"level":3,"boost":true}')
                self.assertEqual(reply, {'lua': True, 'request': {'level': 3, 'boost': True}})
        calls = self.log.read_text().splitlines()
        self.assertTrue(all(line.startswith('-t 15 call homensai-vpn-lua rpc {"method":"') for line in calls), calls)
        self.assertEqual(self.leftovers(), [], 'request and reply files removed')

    def test_fallback_and_missing_object_go_to_agent_with_the_same_bytes(self):
        for mode in ('fallback', 'missing'):
            with self.subTest(mode=mode):
                reply = self.run_plugin('call', 'setup_stats', request=b'{"mode":"work"}', mode=mode)
                self.assertEqual(reply, {'agent': ['call', 'setup_stats'], 'stdin': '{"mode":"work"}'})
        reply = self.run_plugin('call', 'status', request=b'{}', mode='timeout')
        self.assertEqual(reply['agent'], ['call', 'status'], 'a read falls back on any failure')
        self.assertEqual(self.leftovers(), [])

    def test_a_setup_write_with_an_unclear_lua_outcome_is_reported_unconfirmed(self):
        reply = self.run_plugin('call', 'setup_probe', request=b'{"level":3,"boost":true}', mode='timeout')
        self.assertEqual(reply, {'saved': False, 'code': 'SETUP-SAVE-UNCONFIRMED'})

    def test_buttons_fall_back_to_agent_with_the_same_bytes(self):
        # plan item 4: Start/Stop/failure test - a FALLBACK, a missing object or an unclear Lua outcome is answered
        # by agent.py with the request bytes the page sent (a repeated Start finds its own intent, Stop latches again)
        for method in ('native_start', 'native_stop', 'fault_start', 'fault_cancel'):
            for mode in ('fallback', 'missing', 'timeout'):
                with self.subTest(method=method, mode=mode):
                    reply = self.run_plugin('call', method, request=b'{"request_source":"manual"}', mode=mode)
                    self.assertEqual(reply, {'agent': ['call', method], 'stdin': '{"request_source":"manual"}'})
        self.assertEqual(self.leftovers(), [])

    def test_buttons_without_the_lua_monitor_use_the_python_socket_or_agent(self):
        for method in ('native_start', 'native_stop', 'fault_start', 'fault_cancel', 'pair_manual'):
            with self.subTest(method=method):
                self.assertEqual(self.run_plugin('call', method, request=b'{}', ready=False)['agent'], ['call', method])
        self.assertFalse(self.log.exists(), 'ubus is not called without the readiness marker')
        text = PLUGIN.read_text()
        self.assertEqual(text.count('status_client.py'), 1, 'one Python socket path for every listed method')

    def test_python_methods_and_a_stopped_lua_monitor_keep_the_old_paths(self):
        for method in ('native_return', 'native_confirm', 'native_trial_start', 'setup_monitor', 'statistics', 'terms_accept'):
            with self.subTest(method=method):
                self.assertEqual(self.run_plugin('call', method, request=b'{"a":1}')['agent'], ['call', method])
        self.assertEqual(self.run_plugin('call', 'status', request=b'{}', ready=False)['agent'], ['call', 'status'])
        self.assertEqual(self.run_plugin('list', ready=True)['agent'], ['list'])
        self.assertFalse(self.log.exists(), 'ubus never called for these')


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh'), 'POSIX procd harness required')
class InitSwitch(unittest.TestCase):
    def commands(self, lua_monitor=None, lua_file=True):
        script = INIT.read_text().replace('\r\n', '\n')
        if not lua_file:
            script = script.replace('/usr/lib/homensai-vpn/lua/monitor.lua ]', '/nonexistent/monitor.lua ]')
        else:
            script = script.replace('[ -f /usr/lib/homensai-vpn/lua/monitor.lua ]', '[ -f /bin/sh ]')
        script = script.replace('rm -f /var/run/homensai-vpn/lua-monitor.ready', ':')
        stubs = '''
chmod() { :; }
config_load() { CONFIG_main_monitor_only=1; if [ -n "$QA_LUA" ]; then CONFIG_main_lua_monitor=$QA_LUA; fi; }
config_get_bool() { eval "$1=1"; }
procd_open_instance() { printf 'OPEN %s\\n' "$1"; }
procd_set_param() { printf 'PARAM %s\\n' "$*"; }
procd_close_instance() { :; }
start_service
'''
        result = subprocess.run(['sh', '-s'], input=script+'\n'+stubs, text=True, capture_output=True, timeout=5,
                                env=dict(os.environ, QA_LUA='' if lua_monitor is None else lua_monitor))
        self.assertEqual(result.returncode, 0, result.stderr)
        return [line[6:] for line in result.stdout.splitlines() if line.startswith('PARAM command')]

    def test_default_off_keeps_python(self):
        for value in (None, '0', '', 'yes', '2'):
            with self.subTest(value=value):
                self.assertEqual(self.commands(value), ['command /usr/bin/python3 /usr/lib/homensai-vpn/agent.py daemon'])

    def test_one_starts_the_lua_monitor_only_when_installed(self):
        self.assertEqual(self.commands('1'), ['command /usr/bin/lua /usr/lib/homensai-vpn/lua/monitor.lua daemon'])
        self.assertEqual(self.commands('1', lua_file=False), ['command /usr/bin/python3 /usr/lib/homensai-vpn/agent.py daemon'])

    def test_stop_saves_the_lua_monitor_first(self):
        text = INIT.read_text()
        self.assertIn('ubus -t 10 call homensai-vpn-lua shutdown', text)


if __name__ == '__main__':
    unittest.main()
