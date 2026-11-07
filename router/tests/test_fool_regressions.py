"""Regressions found by qa/fool_backend.py (the clueless-grandfather test)."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import rpc_input
import rpc_throttle
import setup_config as setup


class Fool(unittest.TestCase):
    def test_names_reject_invisible_and_formatting_characters(self):
        for name in ('\x7f', '‮evil', '​zero', ' x', '\x85', '   ', '\ud800', '﻿', '￾', '\U000e0041'):
            with self.assertRaisesRegex(ValueError, 'SETUP-NAME', msg=repr(name)):setup.label(name)
        for name in ('Server 1', 'Café', 'Сервер', '\U0001F600 fast'):
            self.assertEqual(name, setup.label(name))

    def test_integers_reject_bool_float_text_and_huge(self):
        for value in (True, 5.0, '30', 10**30, -1, None, [30], {'a': 1}):
            with self.assertRaisesRegex(ValueError, 'SETUP-RANGE'):setup.integer(value, 10, 300)

    def test_cli_wrapper_prints_only_diagnostic_codes(self):
        cases = [(b'x'*70000, 'RPC-INPUT-SIZE'), (b'{"a":1,"a":2}', 'RPC-DUPLICATE-FIELD'), (b'{"a":1e999}', 'RPC-NONFINITE-NUMBER'),
                 (b'{"a":', 'RPC-INPUT-INVALID'), (b'\xff\xfe', 'RPC-INPUT-INVALID'), (b'[]', 'RPC-INPUT-OBJECT'), (b'['*60000, 'RPC-INPUT-COMPLEXITY'),
                 (b'{"a":1}', 'RPC-UNEXPECTED-ARGS')]
        for body, code in cases:
            out = io.StringIO()
            fake = type('S', (), {'buffer': io.BytesIO(body)})()
            with patch.object(sys, 'stdin', fake), patch('sys.stdout', out):
                self.assertEqual(1, agent.call('scan'))
            self.assertEqual({'error': code}, json.loads(out.getvalue()), body[:20])
        out = io.StringIO()
        with patch.object(sys, 'stdin', type('S', (), {'buffer': io.BytesIO(b'')})()), patch('sys.stdout', out):
            self.assertEqual(1, agent.call('no_such_method'))
        self.assertEqual({'error': 'RPC-UNKNOWN-METHOD'}, json.loads(out.getvalue()))

    def test_malformed_argument_shapes_give_codes_never_tracebacks(self):
        # review R3-02: {"metric":[]} raised TypeError (a list is not a dictionary key) and the RPC process died
        import recovery_settings
        import stats_mode
        bad_values = ([], {}, 5, None, True, 1.5, -1, 'x'*70000, [[1]], {'a': []})
        cases = {
            setup.telegram_payload: {'token':'','chat':'@abcdef','enabled':False,'interval':10,'schedule':'daily','hour':1,'weekly':False,'monthly':False},
            setup.speed_payload: {'enabled':False,'auto_new':False,'budget_mib':1,'duration':2,'streams':1,'daily_mib':1,'busy_mbps':1},
            setup.monitor_payload: {'interval':10,'checkpoint':300,'probe_limit':1,'planning_enabled':False,'live_log_limit':1,'history_days':1},
            setup.probe_payload: {'level':1,'boost':False},
            setup.response_payload: {'metric':'websites','compare':False,'fast_switch':False,'ping_interval':10,'server_pick':False,'server_pick_model':'simple'},
            setup.detector_payload: {'probe_spread':True,'retry_backoff':'fixed','reserve_probe_interval':20},
            recovery_settings.payload: dict(recovery_settings.DEFAULTS),
            stats_mode.payload: {'mode':'diagnostic','hours':24},
        }
        for function, good in cases.items():
            for key in good:
                for bad in bad_values:
                    arguments = dict(good); arguments[key] = bad
                    with self.subTest(function=function.__qualname__, key=key, bad=repr(bad)[:12]):
                        try:function(arguments)
                        except ValueError:pass
        with self.assertRaisesRegex(ValueError, 'RESPONSE-METRIC-INVALID'):setup.response_payload({'metric': []})
        with self.assertRaisesRegex(ValueError, 'RESPONSE-METRIC-INVALID'):setup.response_payload({'metric': 'websites', 'server_pick_model': ['simple']})

    def test_rpc_entry_answers_json_for_malformed_shapes(self):
        out = io.StringIO()
        with patch.object(sys, 'stdin', type('S', (), {'buffer': io.BytesIO(b'{"metric":[]}')})()), patch('sys.stdout', out):
            self.assertEqual(0, agent.call('setup_response'))
        self.assertEqual({'saved': False, 'code': 'RESPONSE-METRIC-INVALID'}, json.loads(out.getvalue()))
        # R4-06 (night2 N3-regress 6): the same exception out of an input validator (a *_payload function, rpc_input) is
        # the caller's problem; out of a handler or stored state it is a system failure with one sanitized log line
        for kind, text in ((TypeError, 'unhashable'), (KeyError, 'telegram'), (AttributeError, 'x'), (IndexError, 'y')):
            out, err = io.StringIO(), io.StringIO()
            def telegram_payload(arguments, kind=kind, text=text):raise kind(text)
            def broken(method, validator=telegram_payload):validator({})
            with patch.object(agent, 'rpc', broken), patch('sys.stdout', out), patch('sys.stderr', err):
                self.assertEqual(1, agent.call('setup_onboarding'))
            self.assertEqual({'error': 'RPC-INPUT-INVALID'}, json.loads(out.getvalue()))
            self.assertEqual('', err.getvalue())
            out, err = io.StringIO(), io.StringIO()
            def handler(method, kind=kind, text=text):raise kind(text)
            with patch.object(agent, 'rpc', handler), patch('sys.stdout', out), patch('sys.stderr', err):
                self.assertEqual(1, agent.call('setup_onboarding'))
            self.assertEqual({'error': 'SYSTEM-001'}, json.loads(out.getvalue()), 'a handler failure is not the caller\'s input')
            self.assertRegex(err.getvalue(), r'^RPC-SYSTEM-FAILURE %s at test_fool_regressions\.py:\d+ in handler\n$' % kind.__name__)
            self.assertNotIn('unhashable', err.getvalue());self.assertNotIn('telegram', err.getvalue())

    def test_malformed_stored_status_snapshot_is_a_system_failure_not_caller_input(self):
        # the reviewers' probe: a valid empty status request over a status.json that holds a list raises AttributeError in status_reply
        out, err = io.StringIO(), io.StringIO()
        real_read_json = agent.read_json
        def read_json(path, default=None):
            return [] if str(path).endswith('status.json') else real_read_json(path, default)
        with patch.object(agent, 'read_json', read_json), patch.object(sys, 'stdin', type('S', (), {'buffer': io.BytesIO(b'{}')})()), \
                patch('sys.stdout', out), patch('sys.stderr', err):
            self.assertEqual(1, agent.call('status'))
        self.assertEqual({'error': 'SYSTEM-001'}, json.loads(out.getvalue()))
        self.assertRegex(err.getvalue(), r'^RPC-SYSTEM-FAILURE AttributeError at agent\.py:\d+ in status_reply\n$')

    def test_non_code_messages_never_leak(self):
        self.assertEqual('SYSTEM-001', agent.rpc_error_code(ValueError('/etc/homensai-vpn/secret failed')))
        self.assertEqual('SYSTEM-001', agent.rpc_error_code(OSError('/etc/shadow')))
        self.assertEqual('RPC-CONFIRM-ADDRESS', agent.rpc_error_code(ValueError('RPC-CONFIRM-ADDRESS')))

    def test_throttle_spaces_repeats_and_does_not_block_other_keys(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(rpc_throttle, 'RUNTIME', Path(directory)):
            self.assertTrue(rpc_throttle.allow('a', 2, now=100.0))
            self.assertFalse(rpc_throttle.allow('a', 2, now=101.0))
            self.assertTrue(rpc_throttle.allow('b', 2, now=101.0))
            self.assertTrue(rpc_throttle.allow('a', 2, now=102.5))
            self.assertTrue(rpc_throttle.allow('a', 2, now=50.0), 'a clock that went backwards must not lock the user out')

    def test_throttle_fails_open_when_storage_is_unavailable(self):
        with patch.object(rpc_throttle, 'RUNTIME', Path('/proc/definitely/not/writable')):
            self.assertTrue(rpc_throttle.allow('a', 2))

    def test_decode_request_passes_only_own_codes(self):
        with self.assertRaisesRegex(ValueError, '^RPC-INPUT-INVALID$'):rpc_input.decode_request(b'{"password": oops')


if __name__ == '__main__':
    unittest.main()
