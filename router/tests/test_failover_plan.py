import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from failover_plan import plan
from vendor_fixture import attach


class PlanTests(unittest.TestCase):
    def setup_status(self):
        now=1000
        samples=[{'id':'openvpn:1_1','time':now-d,'code':'VPN-003'} for d in (0,30,60)]
        samples += [{'id':'wireguard:peer_2','time':now-d,'code':None,'dns_ok':True,'https_success':2} for d in (0,30)]
        status={'profiles':[{'id':'openvpn:1_1','protocol':'openvpn','interface':'ovpnclient1','code':'VPN-003'},
                            {'id':'wireguard:peer_2','protocol':'wireguard','interface':'wgclient1'}],'samples':samples}
        attach(status,now)
        settings={'plan_enabled':True,'plan_source':'openvpn:1_1','plan_target':'wireguard:peer_2','interval':30}
        return status,settings,now

    def test_recommendation_never_claims_native_readiness(self):
        result=plan(*self.setup_status())
        self.assertEqual(result['state'],'SWITCH-RECOMMENDED')
        self.assertTrue(result['recommendation']['cross_protocol'])
        self.assertFalse(result['applied']);self.assertFalse(result['ready_to_apply'])
        self.assertIn('WORKER-COORDINATION-UNVERIFIED',result['blockers'])

    def test_stale_future_duplicate_unknown_and_unready_observations(self):
        for mode in ('stale','future','duplicate','unknown','dns','quorum'):
            with self.subTest(mode=mode):
                status,settings,now=self.setup_status()
                if mode=='stale':now+=500
                if mode=='future':status['samples'][0]['time']=now+1
                if mode=='duplicate':status['samples'][0]['time']=status['samples'][1]['time']
                if mode=='unknown':status['samples'][0]['code']='CHECK-001'
                if mode=='dns':status['samples'][-1]['dns_ok']=False
                if mode=='quorum':status['samples'][-1]['https_success']=1
                self.assertIsNone(plan(status,settings,now)['recommendation'])

    def test_disabled_and_inactive_target(self):
        status,settings,now=self.setup_status();settings['plan_enabled']=False
        self.assertEqual(plan(status,settings,now)['state'],'DISABLED')
        settings['plan_enabled']=True;status['profiles'][1]['interface']=None
        self.assertEqual(plan(status,settings,now)['state'],'VENDOR-IDENTITY-UNKNOWN')
