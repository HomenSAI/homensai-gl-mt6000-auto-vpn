import copy,sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_proof as p
from auto_control import trial_readiness,readiness

class Tests(unittest.TestCase):
    def test_old_proof_is_external_and_hosted_cannot_be_promoted(self):
        self.assertTrue(p.matches({},{}));self.assertTrue(p.matches({'proof_scope':p.HOSTED},{'proof_scope':p.HOSTED}))
        self.assertFalse(p.matches({'proof_scope':p.HOSTED},{}));self.assertFalse(p.matches({}, {'proof_scope':p.HOSTED}))
        for bad in(None,False,'unknown',[]):self.assertFalse(p.matches({'proof_scope':bad},{'proof_scope':bad}))
    def test_scope_request_is_explicit_and_bounded(self):
        self.assertEqual(p.requested({}),p.EXTERNAL)
        for bad in(None,[],{'native_proof_scope':'unknown'},{'native_proof_scope':True}):
            with self.assertRaises(ValueError):p.requested(bad)
    def values(self):
        return {'native_trial':'a'*32,'native_enabled':'0','native_until':'2030-01-01T00:00:00+00:00','native_session_loss':'1','native_baseline_exit':'9.9.9.9'}
    def test_trial_requires_private_fresh_nonce_and_no_prior_attempt(self):
        s=self.values();now=1893455990.;sel={'source':{},'target':{}}
        self.assertEqual(trial_readiness(s,{},sel,[],'a'*32,now),[])
        for nonce in('b'*32,None,'ä'*32):self.assertIn('LAN-TRIAL-REQUIRED',trial_readiness(s,{},sel,[],nonce,now))
        self.assertIn('LAN-TRIAL-REQUIRED',trial_readiness(s,{'trial':'a'*32},sel,[],'a'*32,now))
        self.assertIn('TRIAL-ATTEMPT-LIMIT',trial_readiness(s,{'count':3},sel,[],'a'*32,now))
        self.assertEqual(trial_readiness(s,{'count':3,'until':now-1,'trial':'b'*32},sel,[],'a'*32,now),[])
    def test_trial_never_removes_deadline_consent_profile_or_blocker_guards(self):
        sel={'source':{},'target':{}};now=1893455990.
        for change,code in(({'native_session_loss':'0'},'SESSION-LOSS-NOT-ACCEPTED'),({'native_until':'bad'},'BOUNDED-DEADLINE-REQUIRED'),({'native_baseline_exit':'127.0.0.1'},'LAN-TRIAL-REQUIRED'),({'native_enabled':'1'},'START-STATE-UNVERIFIED')):
            s=self.values();s.update(change);self.assertIn(code,trial_readiness(s,{},sel,[],'a'*32,now))
        self.assertIn('TERMS-NOT-ACCEPTED',trial_readiness(self.values(),{},sel,['TERMS-NOT-ACCEPTED'],'a'*32,now))
        self.assertIn('START-STATE-UNVERIFIED',trial_readiness(self.values(),{},None,[],'a'*32,now))

if __name__=='__main__':unittest.main()
