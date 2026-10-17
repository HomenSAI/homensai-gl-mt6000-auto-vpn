import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from auto_control import readiness
import auto_control as control
import native_switch as native
import agent
import tempfile
import time
from unittest.mock import patch, MagicMock


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.settings = {'native_until': '2000', 'native_trial': 'nonce', 'native_session_loss': '1'}
        self.selection = {'hash':'h', 'source':{'id':'a'}, 'target':{'id':'b'}, 'direction':'forward'}
        self.cert = {'hash':'h', 'source':'a', 'target':'b', 'direction':'forward', 'until':2000}
        self.consumed = {'trial':'nonce', 'count':1}

    def check(self, blockers=None):
        return readiness(self.settings, self.cert, self.consumed, self.selection, blockers or [], 1000)

    def test_matching_certification_can_resume(self):
        self.assertEqual(self.check(), [])

    def test_expired_window_cannot_be_extended(self):
        self.settings['native_until']='999'
        self.assertIn('BOUNDED-DEADLINE-REQUIRED', self.check())

    def test_new_nonce_cannot_force_an_uncertified_trial(self):
        self.settings['native_trial']='new'
        self.assertIn('LAN-TRIAL-REQUIRED', self.check())

    def test_changed_profile_or_policy_requires_new_trial(self):
        for key in ('hash','source','target','direction'):
            original=self.cert[key];self.cert[key]='changed'
            self.assertIn('LAN-TRIAL-REQUIRED', self.check())
            self.cert[key]=original

    def test_prerequisite_and_session_loss_are_enforced(self):
        self.settings['native_session_loss']='0'
        self.assertIn('SESSION-LOSS-NOT-ACCEPTED',self.check())
        self.assertIn('UNSUPPORTED-BOARD',self.check(['UNSUPPORTED-BOARD']))

    def test_attempt_limit_is_not_reset(self):
        self.consumed['count']=3
        self.assertIn('TRIAL-ATTEMPT-LIMIT',self.check())

    def test_newer_stop_wins_and_older_stop_can_be_resumed(self):
        request={'mode':'on','trial':'nonce','until':2000,'time':900}
        self.assertEqual(control.effective_intent(self.settings,{'trial':'nonce','requested':950},request,1000),(False,True))
        self.assertEqual(control.effective_intent(self.settings,{'trial':'nonce','requested':800},request,1000),(True,False))

    def test_future_intent_and_expired_window_never_enable(self):
        request={'mode':'on','trial':'nonce','until':2000,'time':1100}
        self.assertEqual(control.effective_intent(self.settings,{},request,1000),(False,True))
        request['time']=900
        self.assertEqual(control.effective_intent(self.settings,{},request,2001),(False,True))

    def test_old_ui_request_does_not_block_new_explicit_trial(self):
        self.settings['native_enabled']='1'
        request={'mode':'off','trial':'old','until':2000,'time':900}
        self.assertEqual(control.effective_intent(self.settings,{},request,1000),(True,False))

    def test_mismatched_deadline_never_enables(self):
        request={'mode':'on','trial':'nonce','until':2500,'time':900}
        self.assertEqual(control.effective_intent(self.settings,{},request,1000),(False,True))


class AtomicRequestTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)
        for name in ('RUNTIME','PERSIST'):
            item=patch.object(control,name,self.path);item.start();self.addCleanup(item.stop)
        self.now=time.time();self.until=self.now+120
        self.settings={'native_trial':'nonce','native_until':str(self.until),'native_session_loss':'1','native_enabled':'0'}
        self.selection={'hash':'h','source':{'id':'a'},'target':{'id':'b'},'direction':'first'}
        self.backend=MagicMock();self.backend.policy.return_value={'settings':self.settings}
        self.backend.diagnostic.return_value=([],self.selection)
        for target,value in ((patch.object(native,'Linux',return_value=self.backend),None),(patch.object(native,'journal_read',return_value={'phase':'ROLLED-BACK'}),None)):
            target.start();self.addCleanup(target.stop)
        agent.atomic_json(self.path/'native-certificate.json',{'hash':'h','source':'a','target':'b','direction':'first','until':self.until})
        agent.atomic_json(self.path/'native-attempts.json',{'trial':'nonce','count':1})

    def test_start_is_one_atomic_intent_without_uci_or_network_write(self):
        with patch.object(agent,'command') as command:
            self.assertTrue(control.start()['accepted'])
            command.assert_not_called()
        value=agent.read_json(self.path/'auto-control.json')
        self.assertEqual(value['trial'],'nonce');self.assertEqual(value['until'],self.until)
        self.assertEqual(self.settings['native_enabled'],'0')
        self.assertTrue(control.start()['already_requested'])

    def test_failed_write_leaves_no_enabled_intent(self):
        with patch.object(control,'atomic_json',side_effect=OSError('simulated storage failure')):
            with self.assertRaises(OSError):control.start()
        self.assertFalse((self.path/'auto-control.json').exists())
        self.assertEqual(self.settings['native_enabled'],'0')

    def test_stop_overrides_start_and_repeated_stop_does_not_write_again(self):
        control.start()
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):
            self.assertTrue(control.stop()['queued'])
            with patch.object(control,'atomic_json') as write:
                self.assertTrue(control.stop()['already_requested']);write.assert_not_called()
        self.assertEqual(control.public_status()['requested'],'off')

    def test_expired_certificate_and_active_transaction_refuse_start(self):
        agent.atomic_json(self.path/'native-certificate.json',{})
        self.assertFalse(control.start()['accepted'])
        with patch.object(native,'journal_read',return_value={'phase':'WAIT-CLIENT'}):
            self.assertEqual(control.start()['blockers'],['TRANSACTION-IN-PROGRESS'])

    def test_return_request_only_when_reserve_is_held_or_committed(self):
        for phase in ('HELD-ON-RESERVE','COMMITTED'):
            with patch.object(native,'journal_read',return_value={'phase':phase,'tx':'t'}):
                self.assertEqual(control.return_request(self.path),{'accepted':True,'queued':True})
                self.assertEqual(agent.read_json(self.path/'native-return.json')['tx'],'t')
        (self.path/'native-return.json').unlink()
        for phase in ('ROLLED-BACK','WAIT-CLIENT',None):
            with patch.object(native,'journal_read',return_value={'phase':phase}):
                self.assertEqual(control.return_request(self.path)['code'],'RETURN-NOT-APPLICABLE')
        self.assertFalse((self.path/'native-return.json').exists())
        with patch.object(native,'journal_read',side_effect=native.Refused('JOURNAL-INTEGRITY-FAILED')):
            self.assertEqual(control.return_request(self.path)['code'],'JOURNAL-UNVERIFIED')

    def test_public_status_exposes_only_the_return_answer(self):
        agent.atomic_json(self.path/'native-return-result.json',{'request':5.0,'ok':False,'code':'SOURCE-NOT-HEALTHY','time':6.0,'secret':'x'})
        answer=control.public_status()['return_result']
        self.assertEqual(answer,{'request':5.0,'ok':False,'code':'SOURCE-NOT-HEALTHY','time':6.0})


if __name__ == '__main__':
    unittest.main()
