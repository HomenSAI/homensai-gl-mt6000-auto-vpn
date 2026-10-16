from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as native


class LeaseTests(unittest.TestCase):
    def test_wall_clock_rollback_cannot_extend_elapsed_lease(self):
        with tempfile.TemporaryDirectory() as path,patch.object(native,'RUNTIME',Path(path)):
            settings={'native_trial':'test'}
            end,error=native.monotonic_lease(settings,2000,wall=1000,mono=100)
            self.assertEqual((end,error),(1100,None))
            end,error=native.monotonic_lease(settings,2000,wall=500,mono=200)
            self.assertEqual((end,error),(1100,None))

    def test_corrupt_lease_cannot_silently_rearm(self):
        with tempfile.TemporaryDirectory() as path,patch.object(native,'RUNTIME',Path(path)):
            (Path(path)/'native-lease.json').write_text('broken')
            end,error=native.monotonic_lease({'native_trial':'test'},2000,1000,100)
            self.assertEqual(end,0);self.assertEqual(error,'LEASE-INTEGRITY-FAILED')

    def test_monotonic_reset_is_not_accepted_as_same_boot(self):
        with tempfile.TemporaryDirectory() as path,patch.object(native,'RUNTIME',Path(path)):
            native.monotonic_lease({'native_trial':'test'},2000,1000,100)
            end,error=native.monotonic_lease({'native_trial':'test'},2000,1100,50)
            self.assertEqual(end,0);self.assertEqual(error,'LEASE-INTEGRITY-FAILED')

    def test_pending_confirmation_expires_despite_backward_wall_clock(self):
        journal={'deadline':2000,'monotonic_deadline':190}
        self.assertTrue(native.transaction_expired(journal,wall=500,mono=191))
        self.assertFalse(native.transaction_expired(journal,wall=500,mono=180))

    def test_new_explicit_trial_gets_its_own_bounded_window(self):
        with tempfile.TemporaryDirectory() as path,patch.object(native,'RUNTIME',Path(path)):
            native.monotonic_lease({'native_trial':'first'},2000,1000,100)
            end,error=native.monotonic_lease({'native_trial':'second'},3000,2000,200)
            self.assertEqual((end,error),(1200,None))
