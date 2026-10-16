from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import timezone_compat as tz

class TimezoneCompatibilityTests(unittest.TestCase):
    def test_full_python_native_refresh(self):
        with patch.object(tz.time,'tzset',create=True) as native:tz.refresh_timezone();native.assert_called_once_with()
    def test_minimal_openwrt_libc_refresh(self):
        libc=MagicMock()
        with patch.object(tz.time,'tzset',None,create=True),patch('ctypes.CDLL',return_value=libc):tz.refresh_timezone()
        libc.tzset.assert_called_once_with();self.assertEqual(libc.tzset.argtypes,[]);self.assertIsNone(libc.tzset.restype)
