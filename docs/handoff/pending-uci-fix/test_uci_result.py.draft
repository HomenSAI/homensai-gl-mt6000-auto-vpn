from pathlib import Path
import sys
import types
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from uci_result import failure_code


class UciResultTests(unittest.TestCase):
    def test_fixed_staging_codes_are_visible_but_arbitrary_output_is_not(self):
        for code in ('SETUP-PENDING-DELTA','SETUP-DELTA-UNVERIFIED'):
            self.assertEqual(failure_code(types.SimpleNamespace(stdout=code.encode()),'FAILED'),code)
        self.assertEqual(failure_code(types.SimpleNamespace(stdout=b'PRIVATE_SENTINEL'),'FAILED'),'FAILED')


if __name__=='__main__':unittest.main()
