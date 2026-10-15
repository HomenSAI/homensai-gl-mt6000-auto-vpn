from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_switch as native


class SupervisorTests(unittest.TestCase):
    def run_once(self,expired=False,mode=None):
        with tempfile.TemporaryDirectory() as d,ExitStack() as stack:
            directory=Path(d)
            for name,value in {'RUNTIME':directory,'PERSIST':directory,'JOURNAL':directory/'journal','STATE':directory/'status','CERT':directory/'cert','ATTEMPTS':directory/'attempts','PREPARE':directory/'prepare','STOP':False}.items():
                stack.enter_context(patch.object(native,name,value))
            backend=MagicMock()
            until=time.time()+(-10 if expired else 100)
            backend.policy.return_value={'settings':{'native_enabled':'1','native_trial':'test','native_until':str(until),'native_session_loss':'1'}}
            backend.diagnostic.return_value=([],None)
            backend.order.return_value=(['a','b'],'a'*64)
            native.journal_write({'phase':'ROLLED-BACK','before':['a','b'],'after':['b','a'],'hash':'a'*64})
            if not expired and not mode:native.atomic_json(directory/'native-stop.json',{'requested':time.time(),'trial':'test'})
            if mode:
                selection={'source':{'id':'openvpn:1_1'},'target':{'id':'wireguard:peer_2'},'hash':'a'*64,'direction':'first'}
                backend.diagnostic.return_value=([],selection)
                native.atomic_json(native.ATTEMPTS,{'until':until,'count':3 if mode=='limit' else 0,'trial':'test','time':time.time()-10})
                native.atomic_json(native.CERT,{'hash':'a'*64,'source':'openvpn:1_1','target':'wireguard:peer_2','direction':'first','until':until})
                now=time.time();samples=[{'id':'openvpn:1_1','time':now-i*30,'code':'VPN-003'} for i in range(3)]+[{'id':'wireguard:peer_2','time':now-i*30,'code':None,'dns_ok':True,'https_success':3} for i in range(2)]
                native.atomic_json(directory/'status.json',{'samples':samples})
            published=[]
            def publish(value):published.append(value);native.STOP=True
            stack.enter_context(patch.object(native,'Linux',return_value=backend))
            stack.enter_context(patch.object(native,'publish',side_effect=publish))
            stack.enter_context(patch.object(native.time,'sleep'))
            native.serve()
            if mode:backend.unguard.assert_not_called()
            else:backend.unguard.assert_called_once()
            backend.apply.assert_not_called();backend.reorder.assert_not_called()
            return published

    def test_stop_latch_removes_only_owned_guard_after_verified_restore(self):
        self.assertEqual(self.run_once()[0]['state'],'STOPPED')

    def test_attempt_limit_blocks_before_new_worker(self):
        self.assertEqual(self.run_once(mode='limit')[0]['blockers'],['TRIAL-ATTEMPT-LIMIT'])

    def test_cooldown_observes_even_when_failure_and_reserve_streaks_pass(self):
        value=self.run_once(mode='cooldown')[0]
        self.assertEqual(value['state'],'OBSERVING');self.assertTrue(value['certified']);self.assertTrue(value['source_failures']);self.assertTrue(value['reserve_healthy'])

    def test_expiry_is_explicit_and_does_not_start_a_new_attempt(self):
        self.assertEqual(self.run_once(expired=True)[0]['state'],'EXPIRED')


if __name__=='__main__':unittest.main()
