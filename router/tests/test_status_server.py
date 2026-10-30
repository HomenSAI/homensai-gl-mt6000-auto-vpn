"""Resident status answers: same JSON as agent.py, root-only socket, strict allowlist, automatic fallback.

The page polls 'status' every ~10 s. These tests pin that the memory path answers exactly what the
per-call RPC answers, recomputes on every control change, never serves an old snapshot, falls back to
agent.py for anything unusual, and that the light client never imports the application.
"""
import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'files'
LIB = ROOT / 'usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
import agent
import auto_live
import status_client
import status_server
import test_pair_manual_directions as fixture

PLUGIN = ROOT / 'usr/libexec/rpcd/homensai-vpn'
ACL = ROOT / 'usr/share/rpcd/acl.d/luci-app-homensai-vpn.json'
APPLICATION = {path.stem for path in LIB.glob('*.py')}
# sha256 of `agent.py list` at f493528 (before the status server); the rpcd signature must not move.
LIST_SHA256 = 'cd51fc9250b2ac89a40c2e56f0ffd0b386d3e7073ad53995a3b22dffea0f9321'


def plugin_text():
    """The packaged plugin: build_ipk.py stores text files with LF whatever the checkout uses."""
    return PLUGIN.read_text(encoding='utf-8').replace('\r\n', '\n')


def served(reply):
    """Parse an OK reply and return (answer without the serving fields, serving fields)."""
    value = json.loads(reply)
    return value, {key: value.pop(key) for key in ('served_from', 'served_age')}


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class Counting:
    def __init__(self, value=None):
        self.calls, self.value, self.error = 0, value, None

    def __call__(self, load):
        self.calls += 1
        if self.error is not None:
            raise self.error
        status = load({'missing': True})
        return dict(self.value or {'answer': 'memory', 'calls': self.calls}, monitor=status)


class ServerCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime, self.persist = self.root / 'run', self.root / 'save'
        self.runtime.mkdir(mode=0o700)
        self.persist.mkdir()
        self.config = self.root / 'homensai_vpn'
        self.config.write_text('config main\n')
        self.clock = Clock()
        self.status, self.events, self.history = Counting(), Counting({'events': []}), Counting({'history': 1})
        self.live_calls = []

    def live(self, load):
        self.live_calls.append(load({}))
        return {'live': True, 'time': 5}

    def server(self, start=True, **kwargs):
        server = status_server.StatusServer(
            self.runtime, self.persist, {'status': self.status, 'events': self.events, 'history': self.history},
            self.live, agent.read_json, configs=(str(self.config),), clock=self.clock, **kwargs)
        if start:
            server.start()
        self.addCleanup(server.close)
        return server

    def ask(self, server, method='status', request=b'{}'):
        return status_client.ask(method, request, str(server.path), timeout=10)


class Lifecycle(ServerCase):
    def test_socket_is_root_only_and_removed_on_stop(self):
        server = self.server()
        row = os.lstat(str(server.path))
        self.assertTrue(stat.S_ISSOCK(row.st_mode))
        self.assertEqual(stat.S_IMODE(row.st_mode), 0o600)
        self.assertEqual([p.name for p in self.runtime.iterdir()], ['status.sock'], 'no temporary socket is left')
        server.close()
        self.assertFalse(server.path.exists())
        self.assertIsNone(self.ask(server), 'a stopped server makes the client fall back')

    def test_stale_socket_of_a_killed_monitor_is_replaced(self):
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(str(self.runtime / 'status.sock'))
        stale.close()
        self.assertIsNone(self.ask(SimpleNamespace(path=self.runtime / 'status.sock')), 'stale socket: fallback')
        server = self.server()
        self.assertIsNotNone(self.ask(server))

    def test_monitor_stop_flag_removes_the_socket_without_waiting_for_the_pass(self):
        stopping = [False]
        server = self.server(stopping=lambda: stopping[0])
        stopping[0] = True
        pause = threading.Event()
        for _ in range(50):
            if not server.path.exists():
                break
            pause.wait(0.1)
        self.assertFalse(server.path.exists())
        self.assertEqual(server.answer('status', b'{}'), status_server.FALLBACK)

    def test_serve_owns_the_socket_only_while_the_monitor_runs(self):
        seen = []

        def loop():
            row = os.lstat(str(self.runtime / 'status.sock'))
            seen.append((stat.S_ISSOCK(row.st_mode), stat.S_IMODE(row.st_mode)))

        with patch.object(agent, 'RUNTIME', self.runtime), patch.object(agent, 'PERSIST', self.persist), \
                patch.object(agent, 'monitor_loop', side_effect=loop):
            agent.serve()
        self.assertEqual(seen, [(True, 0o600)])
        self.assertFalse((self.runtime / 'status.sock').exists())

    def test_server_failure_never_stops_monitoring(self):
        with patch.object(agent, 'RUNTIME', self.runtime), patch.object(agent, 'PERSIST', self.persist), \
                patch('status_server.StatusServer.start', side_effect=OSError('no unix sockets')), \
                patch.object(agent, 'monitor_loop') as loop:
            agent.serve()
        loop.assert_called_once()


class Requests(ServerCase):
    def test_only_argument_free_read_methods_are_served(self):
        server = self.server()
        for method in ('status', 'events', 'history', 'auto_live'):
            for request in (b'', b'{}', b' {} ', b'{"ubus_rpc_session":"SESSION"}'):
                with self.subTest(method=method, request=request):
                    self.assertIsNotNone(self.ask(server, method, request))
        for method in ('inventory', 'scan', 'native_start', 'native_stop', 'manual_switch', 'pair_manual',
                       'statistics', 'speed_live', 'list', '', 'status\x00', 'STATUS', '../status'):
            with self.subTest(method=method):
                self.assertEqual(server.answer(method, b'{}'), status_server.FALLBACK)
                self.assertIsNone(status_client.ask(method, b'{}', str(server.path)))

    def test_malformed_or_extra_input_falls_back_to_agent_codes(self):
        server = self.server()
        for request in (b'{"x":1}', b'[]', b'{', b'{"a":1,"a":1}', b'{"n":NaN}', b'x' * 70000, b'\xff'):
            with self.subTest(request=request[:20]):
                self.assertEqual(server.answer('status', request), status_server.FALLBACK)
        self.assertEqual(self.status.calls, 0, 'nothing is computed for a refused request')

    def test_raw_protocol_violations_get_fallback(self):
        server = self.server()
        for raw in (b'status', b'', b'status\n' + b'x' * (status_server.REQUEST_LIMIT + 10)):
            with self.subTest(raw=raw[:20]):
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.settimeout(5)
                connection.connect(str(server.path))
                try:
                    connection.sendall(raw)
                    connection.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                reply = b''
                while True:
                    try:
                        chunk = connection.recv(4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    reply += chunk
                connection.close()
                self.assertIn(reply, (status_server.FALLBACK, b''))

    def test_compute_failure_falls_back_and_is_not_cached(self):
        server = self.server()
        self.status.error = ValueError('SYSTEM-001')
        self.assertEqual(server.answer('status', b'{}'), status_server.FALLBACK)
        self.status.error = None
        self.clock.now += 0.5
        self.assertTrue(server.answer('status', b'{}').startswith(status_server.OK))

    def test_without_a_computing_thread_the_request_falls_back_at_once(self):
        server = self.server(start=False)
        self.assertEqual(server.answer('status', b'{}'), status_server.FALLBACK)
        self.assertEqual(self.status.calls, 0)

    def test_reply_is_one_json_line_with_serving_facts(self):
        server = self.server()
        reply = self.ask(server)
        self.assertTrue(reply.endswith(b'}\n'))
        self.assertEqual(reply.count(b'\n'), 1)
        value, facts = served(reply)
        self.assertEqual(facts['served_from'], 'memory')
        self.assertGreaterEqual(facts['served_age'], 0)
        self.assertEqual(value['answer'], 'memory')
        self.assertEqual(status_server.splice(b'{}', 1.0), b'{"served_from":"memory","served_age":1.0}')


class Writer(ServerCase):
    """The owner's manual click is answered in the running monitor by the same function agent.py calls."""
    def test_click_is_answered_once_by_the_resident_function(self):
        calls = []
        server = self.server(writers={'pair_manual': lambda arguments: calls.append(arguments) or {'accepted': True, 'queued': True}})
        body = self.ask(server, 'pair_manual', b'{"direction":"reserve","control_revision":"' + b'a' * 32 + b'"}')
        self.assertEqual(json.loads(body), {'accepted': True, 'queued': True})
        self.assertEqual(calls, [{'direction': 'reserve', 'control_revision': 'a' * 32}])

    def test_a_failure_after_the_call_is_never_repeated_through_agent(self):
        def broken(arguments):
            raise RuntimeError('after queueing')
        server = self.server(writers={'pair_manual': broken})
        reply = server.answer('pair_manual', b'{"direction":"reserve"}')
        self.assertTrue(reply.startswith(status_server.OK), 'answered here: agent.py would queue a second click')
        self.assertEqual(json.loads(reply[3:])['blockers'], ['PAIR-MANUAL-REQUEST-UNCONFIRMED'])
        server = self.server(writers={'native_stop': broken})
        self.assertEqual(json.loads(server.answer('native_stop', b'{}')[3:])['code'], 'RPC-UNCONFIRMED')

    def test_malformed_click_and_unknown_writers_go_to_agent(self):
        server = self.server(writers={'pair_manual': lambda arguments: {'accepted': True}, 'setup_system': lambda arguments: {}})
        self.assertEqual(server.answer('pair_manual', b'{'), status_server.FALLBACK)
        self.assertEqual(server.answer('setup_system', b'{}'), status_server.FALLBACK, 'only the listed buttons')
        server.close()
        self.assertEqual(server.answer('pair_manual', b'{}'), status_server.FALLBACK, 'stopping monitor: agent.py')


class Freshness(ServerCase):
    def first(self, server):
        value, _ = served(self.ask(server))
        self.assertEqual(self.status.calls, 1)
        return value

    def test_repeated_polls_are_answered_from_memory(self):
        server = self.server()
        self.first(server)
        for step in range(5):
            self.clock.now += 0.9   # closer than a poll period: no prefetch is scheduled in this test
            value, facts = served(self.ask(server))
            self.assertAlmostEqual(facts['served_age'], 0.9 * (step + 1), places=3)
        self.assertEqual(self.status.calls, 1, 'no recomputation while nothing changed')

    def test_an_old_snapshot_is_never_served(self):
        server = self.server()
        self.first(server)
        self.clock.now += status_server.MAX_SERVE_AGE + 0.5
        value, facts = served(self.ask(server))
        self.assertEqual(self.status.calls, 2)
        self.assertEqual(facts['served_age'], 0)

    def test_every_control_change_recomputes_before_answering(self):
        server = self.server()
        self.first(server)
        changes = [
            lambda: agent.atomic_json(self.runtime / 'auto-control-revision.json', {'revision': 'b' * 32}),
            lambda: agent.atomic_json(self.runtime / 'pair-manual-control.json', {'state': 'QUEUED'}),
            lambda: agent.atomic_json(self.persist / 'native-stop.json', {'requested': 1}),
            lambda: agent.atomic_json(self.persist / 'native-transaction.json', {'schema': 1}),
            lambda: (self.runtime / 'scan.request').write_text('{}'),
            lambda: self.config.write_text('config main\n\toption enabled 1\n'),
            lambda: (self.runtime / 'scan.request').unlink(),
        ]
        for number, change in enumerate(changes, start=2):
            change()
            self.clock.now += 0.1
            served(self.ask(server))
            self.assertEqual(self.status.calls, number)

    def test_native_state_change_recomputes_but_a_new_tick_time_does_not(self):
        native = self.runtime / 'native-status.json'
        agent.atomic_json(native, {'state': 'OBSERVING', 'time': 1, 'channel_path': {'confirmed': True, 'checked_at': 1}})
        server = self.server()
        self.first(server)
        agent.atomic_json(native, {'state': 'OBSERVING', 'time': 2, 'channel_path': {'confirmed': True, 'checked_at': 2}})
        self.clock.now += 0.1
        served(self.ask(server))
        self.assertEqual(self.status.calls, 1, 'a controller tick with the same state is an observation')
        for row in ({'state': 'APPLYING', 'time': 3}, {'state': 'APPLYING', 'time': 4, 'blockers': ['X']},
                    {'state': 'APPLYING', 'time': 5, 'blockers': ['X'], 'channel_path': {'confirmed': False}}):
            agent.atomic_json(native, row)
            self.clock.now += 0.1
            served(self.ask(server))
        self.assertEqual(self.status.calls, 4)

    def test_observation_files_wait_for_the_poll_schedule(self):
        server = self.server()
        self.first(server)
        agent.atomic_json(self.runtime / 'status.json', {'time': 2, 'profiles': []})
        agent.atomic_json(self.persist / 'checkpoint.json', {'a': 1})
        self.clock.now += 0.1
        served(self.ask(server))
        self.assertEqual(self.status.calls, 1)

    def test_own_caches_never_trigger_recomputation(self):
        server = self.server()
        self.first(server)
        for name in status_server.SELF_WRITTEN:
            agent.atomic_json(self.runtime / name, {'cache': 1})
        self.clock.now += 0.1
        served(self.ask(server))
        self.assertEqual(self.status.calls, 1)

    def test_monitor_status_is_parsed_once_per_version_and_handed_out_as_a_copy(self):
        agent.atomic_json(self.runtime / 'status.json', {'time': 1, 'profiles': [{'id': 'a'}]})
        server = self.server(start=False)
        with patch.object(agent, 'read_json', wraps=agent.read_json) as read:
            server.read_json = read
            first = server.load_monitor({})
            first['profiles'].append('mutated')
            second = server.load_monitor({})
            self.assertEqual(second, {'time': 1, 'profiles': [{'id': 'a'}]})
            self.assertEqual(read.call_count, 1)
            agent.atomic_json(self.runtime / 'status.json', {'time': 2})
            self.assertEqual(server.load_monitor({}), {'time': 2})
            self.assertEqual(read.call_count, 2)
        (self.runtime / 'status.json').unlink()
        self.assertEqual(server.load_monitor({'default': 1}), {'default': 1})

    def test_symlinked_monitor_status_is_refused(self):
        target = self.root / 'elsewhere.json'
        target.write_text('{"time":1}')
        (self.runtime / 'status.json').symlink_to(target)
        server = self.server(start=False)
        with self.assertRaises(ValueError):
            server.load_monitor({})

    def test_auto_live_is_computed_per_request_from_the_shared_parse(self):
        agent.atomic_json(self.runtime / 'status.json', {'time': 9})
        server = self.server()
        for _ in range(3):
            value, facts = served(self.ask(server, 'auto_live'))
            self.assertEqual(value, {'live': True, 'time': 5})
        self.assertEqual(self.live_calls, [{'time': 9}] * 3)


class Prefetch(ServerCase):
    def test_one_computation_per_poll_ready_before_the_next_poll(self):
        server = self.server(start=False)
        server.compute('status')
        self.assertTrue(server.answer('status', b'{}').startswith(status_server.OK))
        self.clock.now += 10
        self.assertTrue(server.answer('status', b'{}').startswith(status_server.OK))
        self.assertEqual(self.status.calls, 1)
        self.assertAlmostEqual(server._period['status'], 10)
        self.clock.now += 8.5
        self.assertIsNone(server._choose(), 'too early')
        self.clock.now += 0.5
        self.assertEqual(server._choose(), 'status')
        server.compute('status')
        self.clock.now += 0.5
        self.assertIsNone(server._choose(), 'already prepared for this poll')
        self.clock.now += 0.5
        value, facts = served(server.answer('status', b'{}')[3:])
        self.assertEqual(facts['served_age'], 1.0)
        self.assertEqual(self.status.calls, 2)

    def test_no_background_work_without_polls(self):
        server = self.server(start=False)
        self.assertIsNone(server._choose())
        server.compute('status')
        server.answer('status', b'{}')
        self.clock.now += status_server.DEMAND_WINDOW + 1
        agent.atomic_json(self.runtime / 'auto-control.json', {'mode': 'off'})
        self.assertIsNone(server._choose())

    def test_control_change_is_prepared_before_the_next_poll(self):
        server = self.server(start=False)
        server.compute('status')
        server.answer('status', b'{}')
        agent.atomic_json(self.runtime / 'auto-control.json', {'mode': 'on'})
        self.clock.now += 1
        self.assertIsNone(server._choose(), 'never more often than MIN_REFRESH')
        self.clock.now += status_server.MIN_REFRESH
        self.assertEqual(server._choose(), 'status')


class SameAnswerAsAgent(unittest.TestCase):
    """The real builders on the deterministic pair fixture: memory answers equal agent.py answers."""

    def setUp(self):
        self.case = fixture.PairManualDirections()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.kernel_applied = True
        for target, value in (('speed_test.public_status', {'results': []}), ('retention_settings.configured_days', 7)):
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def legacy(self, method):
        output = io.StringIO()
        with patch.object(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(b'{}'))), redirect_stdout(output):
            agent.rpc(method)
        return json.loads(output.getvalue())

    def test_status_events_history_and_auto_live_match_the_per_call_rpc(self):
        manual = __import__('pair_manual')
        manual.request('primary', self.case.revision)
        server = status_server.StatusServer(
            self.case.runtime, self.case.persist,
            {'status': agent.status_reply, 'events': agent.events_reply, 'history': agent.history_reply},
            auto_live.snapshot, agent.read_json, configs=()).start()
        self.addCleanup(server.close)
        for method in ('status', 'events', 'history', 'auto_live'):
            with self.subTest(method=method):
                expected = self.legacy(method)
                reply = status_client.ask(method, b'{}', str(server.path))
                self.assertIsNotNone(reply)
                value, facts = served(reply)
                self.assertEqual(facts['served_from'], 'memory')
                self.assertEqual(value, expected)
        status, _ = served(status_client.ask('status', b'{}', str(server.path)))
        self.assertEqual(status['manual_switch']['state'], 'QUEUED')
        self.assertIn('channel_path', status)
        self.assertIn('history_split', status)


class Client(unittest.TestCase):
    def test_client_imports_only_the_standard_socket_tools(self):
        tree = ast.parse((LIB / 'status_client.py').read_text(encoding='utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or '').split('.')[0])
        self.assertEqual(imported, {'_socket', 'os', 'sys', 'time', 'subprocess'})
        self.assertFalse(imported & APPLICATION)

    def run_client(self, socket_path, agent_path, method='status', request=b'{}'):
        """Run the client as rpcd would (python3 -I -S) and report its output and loaded modules."""
        code = ('import importlib.util,sys\n'
                'spec=importlib.util.spec_from_file_location("light",%r)\n'
                'light=importlib.util.module_from_spec(spec);spec.loader.exec_module(light)\n'
                'code=light.main([%r],path=%r,python=sys.executable,agent=%r)\n'
                'sys.stderr.write(" ".join(sorted(sys.modules)))\n'
                'raise SystemExit(code)\n') % (str(LIB / 'status_client.py'), method, socket_path, agent_path)
        return subprocess.run([sys.executable, '-I', '-S', '-c', code], input=request, capture_output=True, timeout=30)

    def fake_agent(self, directory):
        path = Path(directory) / 'fake_agent.py'
        path.write_text('import json,sys\n'
                        'print(json.dumps({"argv":sys.argv[1:],"stdin":sys.stdin.buffer.read().decode()}))\n'
                        'raise SystemExit(3)\n')
        return str(path)

    def test_served_poll_loads_no_application_module(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / 'run'
            runtime.mkdir(mode=0o700)
            server = status_server.StatusServer(runtime, Path(directory), {
                'status': lambda load: {'answer': 'memory'}, 'events': lambda load: {'events': []},
                'history': lambda load: {'time': 1}}, lambda load: {'live': True}, agent.read_json, configs=()).start()
            self.addCleanup(server.close)
            result = self.run_client(str(server.path), self.fake_agent(directory))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(served(result.stdout)[0], {'answer': 'memory'})
            modules = set(result.stderr.decode().split())
            self.assertFalse(modules & APPLICATION, sorted(modules & APPLICATION))
            self.assertNotIn('json', modules, 'the client copies bytes; it does not even parse them')
            self.assertNotIn('socket', modules, 'the C module only: socket.py would load enum and selectors')

    def test_missing_or_stale_socket_runs_agent_with_the_same_request(self):
        with tempfile.TemporaryDirectory() as directory:
            stale = Path(directory) / 'stale.sock'
            holder = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            holder.bind(str(stale))
            holder.close()
            for path in (str(Path(directory) / 'missing.sock'), str(stale)):
                with self.subTest(path=path):
                    result = self.run_client(path, self.fake_agent(directory), request=b'{"ubus_rpc_session":"S"}\n')
                    self.assertEqual(result.returncode, 3, 'agent.py exit status is kept')
                    self.assertEqual(json.loads(result.stdout), {'argv': ['call', 'status'],
                                                                 'stdin': '{"ubus_rpc_session":"S"}\n'})


class Plugin(unittest.TestCase):
    """The rpcd executable: a POSIX sh dispatcher, run here with the test paths substituted."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = self.root / 'run'
        self.runtime.mkdir(mode=0o700)
        self.socket = self.runtime / 'status.sock'
        fake = self.root / 'agent.py'
        fake.write_text('import json,sys\n'
                        'print(json.dumps({"agent":sys.argv[1:],"stdin":sys.stdin.buffer.read().decode()}))\n')
        client = self.root / 'status_client.py'
        client.write_text((LIB / 'status_client.py').read_text(encoding='utf-8')
                          .replace("'/var/run/homensai-vpn/status.sock'", repr(str(self.socket)))
                          .replace("'/usr/bin/python3'", repr(sys.executable))
                          .replace("'/usr/lib/homensai-vpn/agent.py'", repr(str(fake))))
        self.plugin = self.root / 'plugin'
        self.plugin.write_text(plugin_text()
                               .replace('/usr/lib/homensai-vpn/status_client.py', str(client))
                               .replace('/usr/lib/homensai-vpn/agent.py', str(fake))
                               .replace('/var/run/homensai-vpn/status.sock', str(self.socket))
                               .replace('/usr/bin/python3', sys.executable))

    def run_plugin(self, *arguments, request=b''):
        result = subprocess.run(['sh', str(self.plugin)] + list(arguments), input=request,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def start(self):
        server = status_server.StatusServer(self.runtime, self.root, {
            'status': lambda load: {'answer': 'memory'}, 'events': lambda load: {'events': []},
            'history': lambda load: {'time': 1}}, lambda load: {'live': True}, agent.read_json, configs=()).start()
        self.addCleanup(server.close)
        return server

    def test_plugin_is_posix_sh_and_keeps_the_agent_entry(self):
        text = plugin_text()
        self.assertTrue(text.startswith('#!/bin/sh\n'))
        self.assertTrue(text.rstrip().endswith('exec /usr/bin/python3 /usr/lib/homensai-vpn/agent.py "$@"'))
        self.assertIn('python3 -I -S /usr/lib/homensai-vpn/status_client.py', text)
        subprocess.run(['sh', '-n', str(self.plugin)], check=True)

    def test_list_and_write_methods_always_use_agent(self):
        self.start()
        self.assertEqual(self.run_plugin('list'), {'agent': ['list'], 'stdin': ''})
        for method in ('native_start', 'scan', 'inventory', 'statistics', 'speed_live'):
            with self.subTest(method=method):
                self.assertEqual(self.run_plugin('call', method, request=b'{"control_revision":"x"}'),
                                 {'agent': ['call', method], 'stdin': '{"control_revision":"x"}'})

    def test_read_methods_come_from_memory_and_fall_back_when_the_monitor_is_down(self):
        self.assertEqual(self.run_plugin('call', 'status', request=b'{}'), {'agent': ['call', 'status'], 'stdin': '{}'})
        server = self.start()
        value, facts = served(json.dumps(self.run_plugin('call', 'status', request=b'{}')))
        self.assertEqual((value, facts['served_from']), ({'answer': 'memory'}, 'memory'))
        self.assertEqual(self.run_plugin('call', 'status', request=b'{"extra":1}'),
                         {'agent': ['call', 'status'], 'stdin': '{"extra":1}'}, 'arguments: agent.py decides')
        self.assertEqual(self.run_plugin('call', 'auto_live', request=b'{}')['live'], True)
        server.close()
        self.assertEqual(self.run_plugin('call', 'history', request=b'{}'), {'agent': ['call', 'history'], 'stdin': '{}'})


class Signature(unittest.TestCase):
    def test_rpc_list_and_acl_are_unchanged(self):
        output = io.StringIO()
        with redirect_stdout(output):
            agent.rpc('list')
        self.assertEqual(hashlib.sha256(output.getvalue().encode()).hexdigest(), LIST_SHA256)
        acl = json.loads(ACL.read_text())['luci-app-homensai-vpn']
        read = set(acl['read']['ubus']['homensai-vpn'])
        write = set(acl['write']['ubus']['homensai-vpn'])
        self.assertLessEqual(status_server.METHODS, read)
        self.assertFalse(status_server.METHODS & write, 'the read path serves read-ACL methods only')
        self.assertEqual(status_server.WRITERS, {'pair_manual', 'native_start', 'native_stop', 'fault_start', 'fault_cancel',
                                                 'setup_probe', 'setup_response'})
        self.assertLessEqual(status_server.WRITERS, write, 'the button methods keep their write ACL in rpcd')
        self.assertEqual(set(agent.CONTROL_METHODS) | {'pair_manual'}, status_server.WRITERS)
        self.assertEqual(set(status_client.METHODS), status_server.METHODS | status_server.WRITERS)


if __name__ == '__main__':
    unittest.main()
