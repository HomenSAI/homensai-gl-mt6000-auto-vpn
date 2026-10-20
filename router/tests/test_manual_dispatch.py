"""Certified one-shot supervisor dispatch; all device operations are mocked."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import native_switch as native
import manual_control as manual
import manual_dispatch as dispatch


class ManualDispatchTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.runtime=root/'run';self.runtime.mkdir();self.persist=root/'etc';self.persist.mkdir()
        for module,key,value in ((agent,'RUNTIME',self.runtime),(agent,'PERSIST',self.persist),
                                 (native,'ATTEMPTS',self.persist/'native-attempts.json'),
                                 (native,'CERT',self.persist/'native-certificate.json')):
            self.stack.enter_context(patch.object(module,key,value))
        self.settings={'native_until':str(time.time()+100),'native_trial':'trial'}
        self.record={'request_id':'a'*32,'direction':'reserve','control_revision':'b'*32,
            'selection_hash':'c'*64,'settings_hash':'d'*64,'vendor_identity':'e'*64,
            'source_id':'openvpn:1','target_id':'wireguard:2','trial':'trial',
            'until':float(self.settings['native_until']),'transaction_id':'f'*32,'requested_at':time.time()}
        self.selection={'hash':'c'*64,'settings_hash':'d'*64,'vendor_identity':'e'*64,
            'source':{'id':'openvpn:1'},'target':{'id':'wireguard:2'}}
        self.backend=MagicMock();self.backend.policy.return_value={'settings':self.settings}
        self.backend.diagnostic.return_value=([],self.selection)
        self.claim=self.stack.enter_context(patch.object(manual,'claim_pending',return_value=(self.record,None)))
        self.result=self.stack.enter_context(patch.object(manual,'publish_result'))
        self.stack.enter_context(patch.object(native,'require_control_revision'))
        self.stack.enter_context(patch.object(native,'progress_read',return_value={'count':1}))
        self.stack.enter_context(patch('auto_control.readiness',return_value=[]))
        self.stack.enter_context(patch('auto_control.effective_intent',return_value=(False,False)))
        agent.atomic_json(native.CERT,{'vendor_identity':'e'*64})
        self.journal=self.stack.enter_context(patch.object(native,'journal_read',return_value={}))
        self.attempt=self.stack.enter_context(patch.object(native,'attempt'))

    def consume(self):return dispatch.consume(self.backend,self.settings,'b'*32,{})

    def test_no_queued_request_does_not_dispatch(self):
        self.claim.return_value=(None,None)
        self.assertFalse(self.consume());self.attempt.assert_not_called()

    def test_changed_identity_or_platform_blocker_prevents_forward(self):
        self.backend.diagnostic.return_value=(['UNSUPPORTED-BOARD'],self.selection)
        self.assertTrue(self.consume());self.attempt.assert_not_called()
        self.assertEqual(self.result.call_args.kwargs['code'],'UNSUPPORTED-BOARD')

    def test_changed_selection_after_claim_prevents_forward(self):
        self.selection['vendor_identity']='0'*64
        self.consume();self.attempt.assert_not_called()
        self.assertEqual(self.result.call_args.kwargs['code'],'MANUAL-CONFIG-CHANGED')

    def test_shared_attempt_budget_consumed_before_real_attempt(self):
        def fail(*a,**kw):
            self.assertEqual(agent.read_json(native.ATTEMPTS)['count'],2)
            raise native.Refused('CLIENT-CONFIRMATION-TIMEOUT')
        self.attempt.side_effect=fail
        self.consume()
        self.assertEqual(self.result.call_args.kwargs['code'],'CLIENT-CONFIRMATION-TIMEOUT')
        self.assertFalse((self.runtime/'auto-control.json').exists())

    def test_only_confirmed_owned_held_transaction_completes(self):
        final={'manual_request_id':'a'*32,'phase':'HELD-ON-RESERVE','confirmed':time.time(),
               'after':['b','a'],'hash':'c'*64,'tx':'f'*32,'source':'openvpn:1',
               'target':'wireguard:2','vendor_identity':'e'*64,'started':self.record['requested_at']}
        self.journal.side_effect=[{},final];self.backend.order.return_value=(['b','a'],'c'*64)
        self.consume()
        self.assertEqual(self.result.call_args.args,('a'*32,'COMPLETED'))
        self.assertEqual(self.result.call_args.kwargs['tx'],'f'*32)
        self.assertEqual(self.attempt.call_args.kwargs['manual_request_id'],'a'*32)
        self.assertFalse((self.runtime/'auto-control.json').exists())

    def test_successful_process_without_confirmed_journal_is_not_completion(self):
        self.consume()
        self.assertEqual(self.result.call_args.kwargs['code'],'MANUAL-COMPLETION-UNVERIFIED')

    def test_primary_cannot_return_another_transaction(self):
        self.record['direction']='primary';self.journal.return_value={'tx':'0'*32}
        self.consume();self.attempt.assert_not_called()
        self.assertEqual(self.result.call_args.kwargs['code'],'RETURN-TRANSACTION-MISMATCH')

    def test_primary_reports_completion_only_after_verified_return(self):
        self.record['direction']='primary'
        before={'tx':'f'*32,'phase':'HELD-ON-RESERVE'}
        restored={'tx':'f'*32,'phase':'ROLLED-BACK','source':'openvpn:1','target':'wireguard:2',
                  'before':['a','b'],'hash':'hash'}
        self.journal.side_effect=[before,restored]
        self.backend.order.return_value=(['a','b'],'hash')
        result_path=self.runtime/'native-return-result.json'
        agent.atomic_json(result_path,{'ok':True,'code':'RETURNED',
            'request':self.record['requested_at'],'time':time.time()})
        with patch.object(native,'handle_return',return_value=(True,time.time())),patch.object(native,'return_result_path',return_value=result_path):
            self.consume()
        self.attempt.assert_not_called();self.assertEqual(self.result.call_args.args,('a'*32,'COMPLETED'))

    def test_stale_return_ok_or_unrestored_order_is_not_completion(self):
        self.record['direction']='primary'
        self.journal.return_value={'tx':'f'*32,'phase':'ROLLED-BACK',
            'source':'openvpn:1','target':'wireguard:2','before':['a','b'],'hash':'hash'}
        result_path=self.runtime/'native-return-result.json'
        for result,order in [({'ok':True},(['a','b'],'hash')),
                ({'ok':True,'code':'RETURNED','request':self.record['requested_at']-1,
                  'time':time.time()},(['a','b'],'hash')),
                ({'ok':True,'code':'RETURNED','request':self.record['requested_at'],
                  'time':time.time()},(['b','a'],'hash'))]:
            with self.subTest(result=result,order=order):
                agent.atomic_json(result_path,result);self.backend.order.return_value=order
                with patch.object(native,'handle_return',return_value=(True,time.time())),patch.object(native,'return_result_path',return_value=result_path):
                    self.consume()
                self.assertEqual(self.result.call_args.kwargs['code'],'RETURN-UNCONFIRMED')

    def test_corrupt_certificate_after_claim_refuses_without_crashing(self):
        agent.atomic_json(native.CERT,[])
        self.consume();self.attempt.assert_not_called()
        self.assertEqual(self.result.call_args.kwargs['code'],'LAN-TRIAL-REQUIRED')

    def test_arbitrary_refusal_text_never_becomes_public_result(self):
        self.backend.diagnostic.side_effect=native.Refused('PRIVATE raw secret')
        self.consume();self.attempt.assert_not_called()
        self.assertEqual(self.result.call_args.kwargs['code'],'MANUAL-RESULT-UNCONFIRMED')

    def test_crash_recovery_requires_bound_confirmed_journal_and_never_replays(self):
        full=dict(self.record,schema=1,state='APPLYING',updated_at=time.time(),code=None)
        self.assertTrue(manual.valid_record(full))
        agent.atomic_json(self.runtime/'manual-control.json',full)
        journal={'manual_request_id':'a'*32,'phase':'HELD-ON-RESERVE','confirmed':time.time(),
            'started':self.record['requested_at'],'source':'openvpn:1','target':'wireguard:2',
            'hash':'c'*64,'vendor_identity':'e'*64,'after':['b','a'],'tx':'f'*32}
        self.journal.return_value=journal;self.backend.order.return_value=(['b','a'],'c'*64)
        dispatch.recover_pending(self.backend)
        self.assertEqual(self.result.call_args.args,('a'*32,'COMPLETED'))
        self.attempt.assert_not_called()
        for field,value in [('vendor_identity','0'*64),('source','other'),('phase','COMMITTED'),
                            ('started',self.record['requested_at']-1)]:
            with self.subTest(field=field):
                self.journal.return_value=dict(journal,**{field:value})
                dispatch.recover_pending(self.backend)
                self.assertEqual(self.result.call_args.args,('a'*32,'UNCONFIRMED'))
                self.attempt.assert_not_called()


if __name__=='__main__':unittest.main()
