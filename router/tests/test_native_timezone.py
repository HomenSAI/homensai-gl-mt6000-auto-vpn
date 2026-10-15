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
