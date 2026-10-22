"""Corrupt progress must block new trials without disabling journal recovery."""
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import native_switch as native
from test_native_switch import Backend


class NativeProgressTests(unittest.TestCase):
    def test_missing_is_initial_state_but_null_list_empty_and_malformed_are_not(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'progress'
            for kind in ('attempts','return'):
                self.assertEqual(native.progress_read(path,kind),{})
                for raw in ('null','[]','"text"','{}','{broken','NaN'):
                    with self.subTest(kind=kind,raw=raw):
                        path.write_text(raw)
                        with self.assertRaisesRegex(native.Refused,'NATIVE-PROGRESS-UNVERIFIED'):
                            native.progress_read(path,kind)
                        self.assertEqual(path.read_text(),raw)
                        path.unlink()

    def test_attempt_budget_requires_integer_count_and_finite_timestamps(self):
        valid={'until':2000,'count':1,'trial':'test','time':1000}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'attempts'
            for key,value in (('count','1'),('count',True),('count',-1),('count',4),
                    ('until',float('nan')),('time',float('inf')),('time',True),('trial',[])):
                with self.subTest(key=key,value=value):
                    path.write_text(json.dumps(dict(valid,**{key:value})))
                    with self.assertRaisesRegex(native.Refused,'NATIVE-PROGRESS-UNVERIFIED'):
                        native.progress_read(path,'attempts')
            # Clock rollback must not silently reset a valid consumed budget.
            path.write_text(json.dumps(dict(valid,time=5000)))
            self.assertEqual(native.progress_read(path,'attempts')['count'],1)

    def test_return_watermark_has_typed_acknowledgement_without_clock_reset(self):
        valid={'request':5000,'ok':False,'code':'RETURN-REQUEST-EXPIRED','time':1000}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'result';path.write_text(json.dumps(valid))
            self.assertEqual(native.progress_read(path,'return'),valid)
            for key,value in (('request',True),('request',0),('ok','false'),
                              ('time',float('nan')),('code',{'private':'value'})):
                with self.subTest(key=key,value=value):
                    path.write_text(json.dumps(dict(valid,**{key:value})))
                    with self.assertRaisesRegex(native.Refused,'NATIVE-PROGRESS-UNVERIFIED'):
                        native.progress_read(path,'return')

    def run_corrupt(self,kind='attempts',raw='[]',mode=None):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory);backend=Backend();backend.candidates=lambda:[];now=time.time()
            until=now-10 if mode=='expiry' else now+100
            backend.data['settings'].update(native_enabled='1',native_until=str(until),native_session_loss='1')
            for key,path in {'RUNTIME':root,'PERSIST':root,'JOURNAL':root/'journal',
                    'STATE':root/'state','CERT':root/'cert','ATTEMPTS':root/'attempts',
                    'PREPARE':root/'prepare','JOURNAL_ALARM':root/'alarm'}.items():
                stack.enter_context(patch.object(native,key,path))
                if key in ('RUNTIME','PERSIST'):stack.enter_context(patch.object(agent,key,path))
            stack.enter_context(patch.object(native,'STOP',False))
            journal={'phase':'ROLLED-BACK','before':backend.current[:],
                     'after':list(reversed(backend.current)),'hash':backend.fingerprint}
            if mode in ('pending','return','committed-expiry'):
                journal.update(phase='ARMED' if mode=='pending' else 'HELD-ON-RESERVE' if mode=='return' else 'COMMITTED',
                    tx='c'*32,source=backend.profiles[0]['id'],target=backend.profiles[1]['id'],
                    trial_nonce='test',started=now-120,deadline=now-30)
                if mode!='pending':backend.current=journal['after'][:]
            if mode=='committed-expiry':backend.data['settings']['native_until']=str(now-10)
            native.journal_write(journal)
            path=native.ATTEMPTS if kind=='attempts' else native.return_result_path()
            path.write_text(raw)
            if mode=='stop':native.atomic_json(root/'native-stop.json',{'requested':now,'trial':'test'})
            if mode=='return':native.atomic_json(native.return_request_path(),{'time':now,'tx':journal['tx']})
            published=[]
            def publish(value):published.append(value);native.STOP=True
            stack.enter_context(patch.object(native,'Linux',return_value=backend))
            stack.enter_context(patch.object(native,'publish',side_effect=publish))
            stack.enter_context(patch.object(native.time,'sleep'))
            stack.enter_context(patch.object(native,'clear_native_options',return_value=True))
            attempt=stack.enter_context(patch.object(native,'attempt'))
            native.serve()
            attempt.assert_not_called()
            final=native.journal_read()
            if mode not in ('return','committed-expiry'):
                self.assertFalse(any(call[0] in ('apply','reorder') for call in backend.calls))
            if mode is None:self.assertEqual(backend.calls,[])
            if mode!='return' or kind!='return':self.assertEqual(path.read_text(),raw,'never erase untrusted progress')
            return published,final,backend.calls

    def test_enabled_supervisor_reports_blocked_without_forward_writes_or_crash_loop(self):
        for kind in ('attempts','return'):
            for raw in ('null','[]','{"until":2000,"count":"three","trial":"test","time":1000}',
                        '{"until":NaN,"count":1,"trial":"test","time":1000}'):
                with self.subTest(kind=kind,raw=raw):
                    published,unused,calls=self.run_corrupt(kind,raw)
                    self.assertEqual(published[0]['state'],'BLOCKED')
                    self.assertIn('NATIVE-PROGRESS-UNVERIFIED',published[0]['blockers'])

    def test_stop_and_expiry_remain_serviceable_with_corrupt_progress(self):
        stopped,unused,calls=self.run_corrupt(mode='stop')
        self.assertEqual(stopped[0]['state'],'STOPPED')
        self.assertIn('NATIVE-PROGRESS-UNVERIFIED',stopped[0]['blockers'])
        self.assertIn(('unguard',),calls)
        expired,unused,calls=self.run_corrupt(mode='expiry')
        self.assertEqual(expired[0]['state'],'EXPIRED');self.assertIn(('unguard',),calls)

    def test_trusted_pending_journal_recovers_before_progress_refusal(self):
        published,journal,unused=self.run_corrupt(mode='pending')
        self.assertEqual(journal['phase'],'ROLLED-BACK')
        self.assertEqual(journal['reason'],'SUPERVISOR-RECOVERY')
        self.assertIn('NATIVE-PROGRESS-UNVERIFIED',published[0]['blockers'])

    def test_explicit_return_and_committed_expiry_do_not_depend_on_progress_ack(self):
        returned,journal,calls=self.run_corrupt(kind='return',mode='return')
        self.assertEqual(returned[0]['reason'],'OPERATOR-RETURN')
        self.assertEqual(journal['phase'],'ROLLED-BACK');self.assertIn(('apply',),calls)
        expired,journal,calls=self.run_corrupt(mode='committed-expiry')
        self.assertEqual(journal['phase'],'ROLLED-BACK')
        self.assertTrue(any(row.get('state')=='ROLLED-BACK' for row in expired))


if __name__=='__main__':unittest.main()
