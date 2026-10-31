"""Plan item 4: the Start / Stop / failure-test cancel buttons answered by the Lua monitor
(lua/control_request.lua). The same request on the same files gives the same reply and the same files as the
Python handlers (agent.control_reply -> auto_control.start/stop, pair_auto.request, fault_control.cancel), and
every file written by Lua is accepted by the Python readers/validators."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
LIB = HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0, str(LIB))
LUA = shutil.which('lua5.1') or shutil.which('lua')

REV = 'a'*32
TRIAL = 'd'*32
PAIR = 'c'*32
MODE = 'router-probed-ipv4'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def read(path):
    return json.loads(path.read_text())


@unittest.skipUnless(LUA, 'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaControlRequest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.lua_dir = self.root/'lua'
        self.py_dir = self.root/'py'
        for base in (self.lua_dir, self.py_dir):
            (base/'run').mkdir(parents=True)
            (base/'etc').mkdir(parents=True)

    def both(self, name, value):
        for base in (self.lua_dir, self.py_dir):
            write(base/name, value)

    def lua(self, action, arguments, policy=None):
        env = dict(os.environ, QA_ARGS=json.dumps(arguments), QA_NOW=repr(time.time()))
        command = [LUA, str(HERE/'lua/test_control_request.lua'), '--dir', str(self.lua_dir), action]
        if policy is not None:
            command.append(json.dumps(policy))
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, env=env)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        return json.loads(result.stdout)

    def python(self, method, arguments, extra=()):
        import agent
        import auto_control
        import fault_control
        base = self.py_dir
        patches = [patch.object(agent, 'RUNTIME', base/'run'), patch.object(agent, 'PERSIST', base/'etc'),
                   patch.object(auto_control, 'RUNTIME', base/'run'), patch.object(auto_control, 'PERSIST', base/'etc'),
                   patch.object(fault_control, 'RUNTIME', base/'run'), patch.object(fault_control, 'PERSIST', base/'etc')]
        patches.extend(extra)
        for item in patches:
            item.start()
        try:
            return agent.control_reply(method, arguments)
        finally:
            for item in reversed(patches):
                item.stop()

    def test_lua_suite(self):
        result = subprocess.run([LUA, str(HERE/'lua/test_control_request.lua')], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=120)
        self.assertEqual(result.returncode, 0, (result.stdout+result.stderr).decode(errors='replace'))
        self.assertIn(b'tests OK', result.stdout)

    def test_start_matches_python_and_the_intent_is_valid(self):
        import agent
        import native_switch
        import preparation_control
        import speed_pause
        import pair_auto
        self.both('run/auto-control-revision.json', {'revision': REV})
        policy = {'settings': {'pair_auto_mode': MODE, 'native_trial': TRIAL}, 'sections': {}}
        arguments = {'control_revision': REV, 'request_source': 'manual'}
        lua_reply = self.lua('start', arguments, policy)
        backend = MagicMock()
        backend.policy.return_value = policy
        py_reply = self.python('native_start', arguments, [
            patch.object(native_switch, 'Linux', return_value=backend),
            patch.object(native_switch, 'journal_read', return_value={}),
            patch.object(preparation_control, 'auto_blocker', return_value=None),
            patch.object(preparation_control, 'auto_prepare', return_value={'repaired': [], 'code': None}),
            patch.object(speed_pause, 'public', return_value={'active': False})])
        self.assertEqual(lua_reply, py_reply)
        lua_row, py_row = read(self.lua_dir/'run/pair-auto-control.json'), read(self.py_dir/'run/pair-auto-control.json')
        self.assertEqual(set(lua_row), set(py_row))
        for key in ('mode', 'revision', 'request_source'):
            self.assertEqual(lua_row[key], py_row[key], key)
        self.assertIsInstance(lua_row['time'], float)
        self.assertRegex(lua_row['id'], '^[a-f0-9]{32}$')
        with patch.object(agent, 'RUNTIME', self.lua_dir/'run'), patch.object(agent, 'PERSIST', self.lua_dir/'etc'):
            self.assertEqual(pair_auto.intent(), lua_row)
            self.assertEqual(pair_auto.public_intent(), lua_row)
        # a repeated click: both answer already_requested
        again = self.lua('start', arguments, policy)
        self.assertEqual(again, {'accepted': True, 'queued': True, 'already_requested': True})
        # a stale revision: the same refusal, nothing written
        stale = dict(arguments, control_revision='b'*32)
        self.assertEqual(self.lua('start', stale, policy), {'accepted': False, 'blockers': ['CONTROL-REVISION-STALE']})

    def stop_world(self, now):
        self.both('run/auto-control-revision.json', {'revision': REV})
        self.both('run/pair-auto-control.json', {'mode': 'on', 'revision': REV, 'time': now-100, 'id': PAIR, 'request_source': 'manual'})
        self.both('run/pair-manual-control.json', {'id': 'f'*32, 'pair': PAIR, 'revision': REV, 'direction': 'reserve', 'state': 'QUEUED',
                                                   'requested': now-1, 'updated': now-1, 'selection': {'tx': None}, 'code': None,
                                                   'request_source': 'manual'})

    def test_stop_matches_python_and_every_file_is_valid(self):
        import agent
        import auto_control
        import pair_manual
        import pair_auto
        now = time.time()
        self.stop_world(now)
        policy = {'settings': {'native_trial': TRIAL}, 'sections': {}}
        arguments = {'request_source': 'manual'}
        lua_reply = self.lua('stop', arguments, policy)
        py_reply = self.python('native_stop', arguments, [patch.object(agent, 'command', return_value=json.dumps(policy).encode())])
        self.assertEqual(lua_reply, py_reply)
        self.assertEqual(lua_reply, {'queued': True})
        lua_stop, py_stop = read(self.lua_dir/'etc/native-stop.json'), read(self.py_dir/'etc/native-stop.json')
        self.assertEqual(set(lua_stop), set(py_stop))
        self.assertEqual({k: v for k, v in lua_stop.items() if k != 'requested'}, {k: v for k, v in py_stop.items() if k != 'requested'})
        self.assertTrue(auto_control.valid_stop(lua_stop))
        self.assertIsInstance(lua_stop['requested'], float)
        settings = {'native_trial': TRIAL, 'native_enabled': '1'}
        self.assertEqual(auto_control.effective_intent(settings, lua_stop, {}, time.time()+1), (True, True))
        lua_revision = read(self.lua_dir/'run/auto-control-revision.json')
        self.assertEqual(set(lua_revision), {'revision'})
        self.assertNotEqual(lua_revision['revision'], REV)
        lua_pair = read(self.lua_dir/'run/pair-auto-control.json')
        self.assertEqual(lua_pair['mode'], 'off')
        self.assertEqual(lua_pair['revision'], lua_revision['revision'])
        self.assertEqual(lua_pair['request_source'], 'manual')
        lua_click, py_click = read(self.lua_dir/'run/pair-manual-control.json'), read(self.py_dir/'run/pair-manual-control.json')
        self.assertTrue(pair_manual.valid(lua_click))
        self.assertEqual(lua_click['state'], 'CANCELLED')
        self.assertEqual(lua_click['code'], 'CONTROL-REVISION-STALE')
        self.assertEqual({k: v for k, v in lua_click.items() if k != 'updated'}, {k: v for k, v in py_click.items() if k != 'updated'})
        with patch.object(agent, 'RUNTIME', self.lua_dir/'run'), patch.object(agent, 'PERSIST', self.lua_dir/'etc'):
            self.assertEqual(pair_auto.intent()['mode'], 'off')
            self.assertIsNone(pair_auto.public_intent())
        # a second Stop: the same trial is already latched in both
        again_lua = self.lua('stop', {}, policy)
        again_py = self.python('native_stop', {}, [patch.object(agent, 'command', return_value=json.dumps(policy).encode())])
        self.assertEqual(again_lua, again_py)
        self.assertEqual(again_lua, {'queued': True, 'already_requested': True})

    def test_stop_with_unreadable_settings_matches_python(self):
        import agent
        import subprocess as sp
        now = time.time()
        self.stop_world(now)
        self.both('run/auto-control.json', {'mode': 'on', 'trial': TRIAL, 'time': now-50, 'until': now+1000})
        lua_reply = self.lua('stop', {})
        py_reply = self.python('native_stop', {}, [patch.object(agent, 'command', side_effect=sp.CalledProcessError(1, 'lua'))])
        self.assertEqual(lua_reply, py_reply)
        self.assertEqual(lua_reply, {'queued': True, 'settings_unverified': True})
        lua_stop, py_stop = read(self.lua_dir/'etc/native-stop.json'), read(self.py_dir/'etc/native-stop.json')
        self.assertEqual({k: v for k, v in lua_stop.items() if k != 'requested'}, {k: v for k, v in py_stop.items() if k != 'requested'})
        self.assertEqual(lua_stop['trial'], TRIAL)
        self.assertTrue(lua_stop['all_trials'])

    def test_fault_cancel_matches_python_and_the_history_checksum_is_python_s(self):
        import fault_control
        now = time.time()
        data = {'nonce': 'e'*32, 'phase': 'ACTIVE', 'started': now-20, 'until': now+100, 'monotonic_until': time.monotonic()+100,
                'profiles': ['wireguard:peer_1'], 'devices': ['wgclient1'], 'scope': 'channel', 'duration': 120, 'control_revision': REV,
                'pair_mode': True, 'fault_role': 'source', 'control_settings': {'native_trial': None, 'pair_auto_mode': MODE}}
        history = [{'time': now-3600.25, 'code': 'FAULT-TRANSITION-CONFIRMED', 'profiles': ['wireguard:peer_1'], 'scope': 'channel', 'duration': 60}]
        envelope = {'data': data, 'sha256': fault_control.checksum(data)}
        self.both('run/fault-intent.json', envelope)
        self.both('etc/fault-history.json', {'data': history, 'sha256': fault_control.checksum(history)})
        self.both('run/auto-control-revision.json', {'revision': REV})
        lua_reply = self.lua('cancel', {})
        py_reply = self.python('fault_cancel', {}, [patch.object(fault_control.Nft, 'contents', return_value=None)])
        self.assertEqual(lua_reply, py_reply)
        self.assertEqual(lua_reply['code'], 'FAULT-CANCELLED')
        self.assertEqual(read(self.lua_dir/'run/fault-cancel.json'), read(self.py_dir/'run/fault-cancel.json'))
        lua_result, py_result = read(self.lua_dir/'run/fault-result.json'), read(self.py_dir/'run/fault-result.json')
        self.assertEqual({k: v for k, v in lua_result.items() if k != 'time'}, {k: v for k, v in py_result.items() if k != 'time'})
        with patch.object(fault_control, 'PERSIST', self.lua_dir/'etc'):
            rows = fault_control.history()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], history[0], 'earlier rows are kept byte-exact (floats included)')
        py_rows = read(self.py_dir/'etc/fault-history.json')['data']
        self.assertEqual({k: v for k, v in rows[1].items() if k != 'time'}, {k: v for k, v in py_rows[1].items() if k != 'time'})
        # nothing left: the same refusal
        (self.lua_dir/'run/fault-intent.json').unlink()
        self.assertEqual(self.lua('cancel', {}), {'queued': False, 'code': 'FAULT-NOT-ACTIVE'})


if __name__ == '__main__':
    unittest.main()
