"""Regression (alpha81 overnight test): a pair-mode fault start must not take the control lock twice."""
import sys,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import auto_control,fault_control as fault


class LockReentry(unittest.TestCase):
    def test_claim_under_lock_reads_the_revision_without_locking_again(self):
        held=[]
        @contextmanager
        def lock(*args):
            if held:raise AssertionError('control lock taken twice: flock is not re-entrant, this deadlocks')
            held.append(1)
            try:yield
            finally:held.pop()
        intent={'nonce':'a'*32,'phase':'ARMED','monotonic_until':float('inf'),'control_settings':{'pair_auto_mode':'router-probed-ipv4'}}
        with patch.object(fault,'control_lock',lock),patch.object(auto_control,'control_lock',lock),\
             patch.object(fault,'require_revision'),patch.object(fault,'load',return_value=intent),\
             patch.object(fault,'read_json',return_value={}),patch.object(auto_control,'revision_locked',return_value='r'*32) as direct,\
             patch('pair_manual.active',return_value=True),patch('pair_auto.read_state',return_value={}),patch('pair_auto.intent',return_value={}):
            with fault.control_lock():self.assertEqual(fault.claim_locked('a'*32,'r'*32),intent)
            direct.assert_called_once()


if __name__=='__main__':unittest.main()
