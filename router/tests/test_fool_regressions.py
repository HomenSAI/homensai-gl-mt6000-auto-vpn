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
                 (b'{"a":', 'RPC-INPUT-INVALID'), (b'\xff\xfe', 'RPC-INPUT-INVALID'), (b'[]', 'RPC-INPUT-OBJECT'), (b'['*60000, 'RPC-INPUT-DEPTH'),
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
