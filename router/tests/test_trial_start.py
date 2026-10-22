import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import auto_control as a
import native_switch as n
from agent import atomic_json,read_json

class Tests(unittest.TestCase):
    def test_fresh_private_trial_can_supersede_stop_without_erasing_it_or_claiming_certificate(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);runtime=root/'ram';persist=root/'persist';persist.mkdir();now=1893455990.
            settings={'native_trial':'a'*32,'native_enabled':'0','native_until':'2030-01-01T00:00:00+00:00','native_session_loss':'1','native_baseline_exit':'9.9.9.9'}
            stopped={'all_trials':True,'requested':now-5};atomic_json(persist/'native-stop.json',stopped)
            selection={'source':{'id':'wireguard:peer_1'},'target':{'id':'openvpn:1_1'},'hash':'b'*64}
            with patch.object(a,'RUNTIME',runtime),patch.object(a,'PERSIST',persist),patch.object(a.time,'time',return_value=now),patch.object(n,'journal_read',return_value={}),patch.object(n,'Linux')as factory:
                factory.return_value.policy.return_value={'settings':settings};factory.return_value.diagnostic.return_value=([],selection)
                revision=a.current_revision()
                self.assertFalse(a.start(revision)['accepted'])
                self.assertFalse(a.start(revision,trial_nonce='b'*32)['accepted'])
                result=a.start(revision,trial_nonce='a'*32);self.assertTrue(result['accepted'])
                request=read_json(runtime/'auto-control.json',{})
                self.assertEqual(a.effective_intent(settings,stopped,request,now),(True,False))
                self.assertEqual(read_json(persist/'native-stop.json',{}),stopped)
                self.assertFalse((persist/'native-certificate.json').exists());self.assertEqual(settings['native_enabled'],'0')

    def test_stop_during_calibration_preflight_invalidates_the_pending_intent(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);runtime=root/'ram';persist=root/'persist';persist.mkdir();now=1893455990.
            settings={'native_trial':'a'*32,'native_enabled':'0','native_until':'2030-01-01T00:00:00+00:00','native_session_loss':'1','native_baseline_exit':'9.9.9.9'}
            with patch.object(a,'RUNTIME',runtime),patch.object(a,'PERSIST',persist),patch.object(a.time,'time',return_value=now),patch.object(n,'journal_read',return_value={}),patch.object(n,'Linux')as factory:
                factory.return_value.policy.return_value={'settings':settings}
                def diagnostic():
                    a.current_revision(rotate=True);atomic_json(persist/'native-stop.json',{'all_trials':True,'requested':now})
                    return [],{'source':{},'target':{}}
                factory.return_value.diagnostic.side_effect=diagnostic
                revision=a.current_revision();result=a.start(revision,trial_nonce='a'*32)
                self.assertFalse(result['accepted']);self.assertIn('CONTROL-REVISION-STALE',result['blockers'])
                self.assertFalse((runtime/'auto-control.json').exists())

if __name__=='__main__':unittest.main()
