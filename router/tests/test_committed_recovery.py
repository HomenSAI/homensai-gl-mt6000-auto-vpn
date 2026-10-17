from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from native_switch import committed_recovery_decision as decide

class CommittedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.backend=MagicMock();self.backend.health.return_value=True;self.backend.recovery_ready.return_value=False
        self.journal={'source':'a','target':'b','confirmed':900}
        self.samples=[{'id':'b','time':stamp,'code':'DNS-001'} for stamp in (940,970,990)]
    def test_confirmed_reserve_failure_is_reported(self):
        self.backend.health.return_value=False
        self.assertEqual(decide(self.backend,self.journal,{},self.samples,1000)['reason'],'RESERVE-FAILED')
    def test_stale_failure_cannot_declare_live_reserve_down(self):
        self.backend.health.return_value=False
        self.assertEqual(decide(self.backend,self.journal,{},self.samples,2000)['action'],'OBSERVE')
        self.backend.health.assert_not_called()
    def test_monitor_failure_is_rechecked_live(self):
        self.assertEqual(decide(self.backend,self.journal,{},self.samples,1000)['action'],'OBSERVE')
        self.backend.health.assert_called_once_with('b')
    def test_emergency_return_requires_verified_primary(self):
        self.backend.recovery_ready.return_value=True
        self.assertEqual(decide(self.backend,self.journal,{},self.samples,1000)['reason'],'RESERVE-FAILED-PRIMARY-VERIFIED')
    def test_normal_return_waits_for_dwell_and_primary_verification(self):
        self.backend.recovery_ready.return_value=True
        self.assertEqual(decide(self.backend,self.journal,{},[],1000)['action'],'OBSERVE')
        self.assertEqual(decide(self.backend,self.journal,{},[],1100)['reason'],'PRIMARY-STABLY-RECOVERED')
    def test_operator_hold_never_forces_primary_return(self):
        self.backend.recovery_ready.return_value=True;self.backend.health.return_value=False
        result=decide(self.backend,self.journal,{'recovery_return_policy':'hold_reserve'},self.samples,1000)
        self.assertEqual(result['action'],'HOLD');self.backend.recovery_ready.assert_not_called()
    def test_unknown_live_health_is_explicit(self):
        self.backend.health.return_value=None
        self.assertEqual(decide(self.backend,self.journal,{},self.samples,1000)['reason'],'RESERVE-HEALTH-UNKNOWN')

if __name__=='__main__':unittest.main()
