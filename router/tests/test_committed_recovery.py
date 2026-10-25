from pathlib import Path
import sys
import unittest
import copy
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from native_switch import committed_recovery_decision as decide
from vendor_fixture import attach

class CommittedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.backend=MagicMock();self.backend.health.return_value=True;self.backend.recovery_ready.return_value=False
        self.journal={'source':'openvpn:a','target':'wireguard:b','confirmed':900}
        self.samples=[{'id':'wireguard:b','time':stamp,'code':'DNS-001'} for stamp in (940,970,990)]
        self.status=attach({'profiles':[{'id':'openvpn:a','interface':'vpn1','protocol':'openvpn'},
                                      {'id':'wireguard:b','interface':'vpn2','protocol':'wireguard','code':'DNS-001'}],
                            'samples':self.samples})
    def decide(self,settings,samples,now):
        status=copy.deepcopy(self.status);status['time']=now;status['vendor_observation']['time']=now
        for row in status['profiles']:row['time']=now
        for group in status['vendor_observation']['groups']:group['time']=now
        return decide(self.backend,self.journal,settings,samples,now,status)
    def test_confirmed_reserve_failure_is_reported(self):
        self.backend.health.return_value=False
        self.assertEqual(self.decide({},self.samples,1000)['reason'],'RESERVE-FAILED')
    def test_stale_failure_cannot_declare_live_reserve_down(self):
        self.backend.health.return_value=False
        self.assertEqual(self.decide({},self.samples,2000)['action'],'OBSERVE')
        self.backend.health.assert_not_called()
    def test_monitor_failure_is_rechecked_live(self):
        self.assertEqual(self.decide({},self.samples,1000)['action'],'OBSERVE')
        self.backend.health.assert_called_once_with('wireguard:b')
    def test_emergency_return_requires_verified_primary(self):
        self.backend.recovery_ready.return_value=True
        self.assertEqual(self.decide({},self.samples,1000)['reason'],'RESERVE-FAILED-PRIMARY-VERIFIED')
    def test_normal_return_waits_for_dwell_and_primary_verification(self):
        self.backend.recovery_ready.return_value=True
        self.assertEqual(self.decide({},[],1000)['action'],'OBSERVE')
        self.assertEqual(self.decide({},[],1100)['reason'],'PRIMARY-STABLY-RECOVERED')
    def test_operator_hold_never_forces_primary_return(self):
        self.backend.recovery_ready.return_value=True;self.backend.health.return_value=False
        result=self.decide({'recovery_return_policy':'hold_reserve'},self.samples,1000)
        self.assertEqual(result['action'],'HOLD');self.backend.recovery_ready.assert_not_called()
    def test_explicit_bounded_fault_tests_return_even_during_reserve_hold(self):
        self.backend.recovery_ready.return_value=True
        with patch('fault_control.testing_profile',return_value=True):
            self.assertEqual(self.decide({'recovery_return_policy':'hold_reserve'},self.samples,1000)['action'],'RESTORE-PRIMARY')
            self.assertEqual(self.decide({'recovery_return_policy':'hold_reserve'},[],1000)['action'],'OBSERVE','test cannot bypass failure evidence')
        self.backend.recovery_ready.return_value=False;self.backend.health.return_value=False
        with patch('fault_control.testing_profile',return_value=True):
            self.assertEqual(self.decide({'recovery_return_policy':'hold_reserve'},self.samples,1000)['action'],'HOLD','test cannot bypass healthy primary verification')
    def test_unknown_live_health_is_explicit(self):
        self.backend.health.return_value=None
        self.assertEqual(self.decide({},self.samples,1000)['reason'],'RESERVE-HEALTH-UNKNOWN')

if __name__=='__main__':unittest.main()
