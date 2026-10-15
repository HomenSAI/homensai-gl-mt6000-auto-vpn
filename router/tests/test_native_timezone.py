import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as native

class TimezoneCompatibility(unittest.TestCase):
    def test_python_tzset(self):
        with patch.object(native.time,'tzset',create=True) as tz:
            native.configure_timezone()
            tz.assert_called_once_with()
    def test_router_python_without_tzset(self):
        libc=MagicMock()
        with patch.object(native.time,'tzset',None,create=True), patch('ctypes.CDLL',return_value=libc):
            native.configure_timezone()
            libc.tzset.assert_called_once_with()
    def test_libc_failure_is_not_silently_ignored(self):
        with patch.object(native.time,'tzset',None,create=True), patch('ctypes.CDLL',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError): native.configure_timezone()

class KernelRingFreshness(unittest.TestCase):
    def test_rollover_preserves_unique_tail_marker(self):
        self.assertEqual(native.appended_hook_state('[1] old\n[2] marker\n','[2] marker\n[3] value=0, hook is disabled now!\n'),'disabled')
    def test_unchanged_ring_does_not_reuse_old_state(self):
        value='[2] value=0, hook is disabled now!\n'
        self.assertEqual(native.appended_hook_state(value,value),'unknown')
    def test_missing_or_ambiguous_marker_refuses(self):
        self.assertEqual(native.appended_hook_state('[1] absent\n','[2] value=0, hook is disabled now!\n'),'unknown')
        self.assertEqual(native.appended_hook_state('[1] repeated\n','[1] repeated\n[1] repeated\n[2] value=0, hook is disabled now!\n'),'unknown')
