"""Regression tests for the six independently reproduced 20 October defects."""
from contextlib import ExitStack
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import native_switch as native
import lifecycle_guard as lifecycle


class Hardening(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.directory=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for name,value in {'RUNTIME':self.directory,'PERSIST':self.directory,'JOURNAL':self.directory/'journal','STATE':self.directory/'state'}.items():
            self.stack.enter_context(patch.object(native,name,value))

    def test_missing_journal_is_distinct_from_invalid_existing_json(self):
        self.assertEqual(native.journal_read(),{})
        for raw in ('null','false','0','[]','""','{}','{"schema":1}'):
            native.JOURNAL.write_text(raw)
            with self.subTest(raw=raw),self.assertRaises(native.Refused):native.journal_read()

    def test_journal_types_phase_and_numbers_are_validated(self):
        base={'phase':'ROLLED-BACK','hash':'a'*64,'before':['a','b'],'after':['b','a']}
        for edit in ({'before':[{}]}, {'after':'ab'}, {'phase':'UNKNOWN'}, {'hash':'bad'}, {'deadline':float('nan')}, {'before':True}):
            row=dict(base,**edit)
            # Model a damaged but checksum-consistent envelope, bypassing the writer.
            agent.atomic_json(native.JOURNAL,{'schema':1,'data':row,'sha256':native.digest(row)}) if not edit.get('deadline') else native.JOURNAL.write_text(json.dumps({'schema':1,'data':row,'sha256':native.digest(row)}))
            with self.subTest(edit=edit),self.assertRaises(native.Refused):native.journal_read()

    def test_timer_spawn_failure_refuses_before_any_guard_installation(self):
        backend=native.Linux()
        with patch.object(backend,'guard_exists',return_value=False),patch.object(native.subprocess,'run',return_value=MagicMock(returncode=0)) as run,patch.object(native.subprocess,'Popen',side_effect=OSError('process limit')):
            with self.assertRaisesRegex(native.Refused,'GUARD-RELEASE-ARM-FAILED'):backend.guard()
            self.assertEqual(run.call_count,1)
            self.assertIn('-c',run.call_args.args[0])

    def test_full_guard_has_kernel_expiry_as_well_as_independent_cleanup(self):
        backend=native.Linux();scripts=[]
        def run(args,**kwargs):scripts.append(Path(args[-1]).read_text());return MagicMock(returncode=0)
        with patch.object(backend,'guard_exists',side_effect=[False,True]),patch.object(native.subprocess,'run',side_effect=run),patch.object(native.subprocess,'Popen'):
            backend.guard()
        self.assertIn('flags timeout',scripts[-1]);self.assertIn('"br-lan" timeout 90s',scripts[-1])
        self.assertRegex(scripts[-1],r'iifname @blocked_lan_[a-f0-9]{8} drop')

    def test_old_cleanup_cannot_delete_a_new_guard_table(self):
        with patch.object(native.subprocess,'Popen') as spawn:
            native.Linux().schedule_release('0123abcd')
        script=spawn.call_args.args[0][2]
        self.assertIn('delete element inet '+native.TABLE+' blocked_lan_0123abcd',script)
        self.assertNotIn('delete table',script);self.assertNotIn('nft list',script)

    def test_stop_unknown_policy_without_ui_intent_is_durable_and_global(self):
        with patch.object(agent,'command',side_effect=OSError('unreadable')):
            reply=auto_control.stop(runtime=self.directory,persist=self.directory)
        self.assertTrue(reply['queued']);self.assertNotIn('already_requested',reply)
        stopped=agent.read_json(self.directory/'native-stop.json')
        self.assertTrue(stopped['all_trials'])
        self.assertEqual(auto_control.effective_intent({'native_enabled':'1','native_trial':'legacy'},stopped,{},time.time()),(False,True))
        with patch.object(agent,'command',side_effect=OSError('unreadable')),patch.object(auto_control,'atomic_json') as write:
            self.assertTrue(auto_control.stop(runtime=self.directory,persist=self.directory)['already_requested'])
            self.assertEqual([call.args[0].name for call in write.call_args_list],['auto-control-revision.json'])

    def test_explicit_later_start_can_supersede_emergency_stop(self):
        settings={'native_enabled':'0','native_trial':'new','native_until':'1000'}
        stopped={'all_trials':True,'requested':100}
        request={'mode':'on','trial':'new','time':101,'until':1000}
        self.assertEqual(auto_control.effective_intent(settings,stopped,request,102),(True,False))

    def test_unknown_policy_upgrades_stale_trial_stop_to_global_epoch(self):
        agent.atomic_json(self.directory/'auto-control.json',{'trial':'old','mode':'on','time':90,'until':1000})
        agent.atomic_json(self.directory/'native-stop.json',{'trial':'old','requested':100})
        settings={'native_enabled':'1','native_trial':'new','native_until':'1000'}
        with patch.object(agent,'command',side_effect=OSError('policy unavailable')):
            reply=auto_control.stop(runtime=self.directory,persist=self.directory)
        self.assertTrue(reply['queued']);self.assertNotIn('already_requested',reply)
        stopped=agent.read_json(self.directory/'native-stop.json')
        self.assertTrue(stopped['all_trials'])
        self.assertEqual(auto_control.effective_intent(settings,stopped,agent.read_json(self.directory/'auto-control.json'),time.time()),(False,True))

    def test_malformed_trial_stop_epoch_fails_closed_without_crashing(self):
        settings={'native_enabled':'1','native_trial':'current','native_until':'1000'}
        request={'trial':'current','mode':'on','time':101,'until':1000}
        for epoch in ('bad',None,True,[],{},float('nan'),float('inf'),0,-1):
            with self.subTest(epoch=epoch):
                self.assertEqual(auto_control.effective_intent(settings,{'trial':'current','requested':epoch},request,102),(False,True))

    def test_public_stop_state_survives_corrupt_records_without_claiming_off(self):
        with patch.object(auto_control,'RUNTIME',self.directory),patch.object(auto_control,'PERSIST',self.directory):
            for raw in ('null','[]','{"requested":"bad"}','{"requested":NaN}','{'):
                (self.directory/'native-stop.json').write_text(raw)
                with self.subTest(raw=raw):
                    state=auto_control.public_status()
                    self.assertEqual(state['requested'],'unknown')
                    json.dumps(state,allow_nan=False)
            (self.directory/'native-stop.json').write_text('{}')
            (self.directory/'native-return-result.json').write_text('{"ok":true,"code":{"private":"value"}}')
            self.assertIsNone(auto_control.public_status()['return_result'])

    def test_existing_corrupt_alarm_marker_never_repeats_full_block(self):
        marker=self.directory/'journal-alarm'
        backend=MagicMock()
        for raw in ('null','false','[]','{}','{"first_block":false}','{'):
            marker.write_text(raw)
            with self.subTest(raw=raw),patch.object(native,'JOURNAL_ALARM',marker),patch.object(native,'Linux',return_value=backend),patch.object(native,'journal_read',side_effect=native.Refused('JOURNAL-INTEGRITY-FAILED')),patch.object(native,'give_up') as alarm:
                native.serve()
                backend.guard.assert_not_called();alarm.assert_called_once_with(backend,{},'JOURNAL-INTEGRITY-FAILED')

    def test_corrupt_requests_cannot_override_global_stop_or_break_stop(self):
        settings={'native_enabled':'1','native_trial':'current','native_until':'1000'}
        stopped={'all_trials':True,'requested':100}
        for request in ([],None,{'time':'new'}, {'time':float('nan')}, {'time':101},
                        {'mode':'on','time':101,'trial':'other','until':1000}):
            with self.subTest(request=request):
                self.assertEqual(auto_control.effective_intent(settings,stopped,request,102),(False,True))
        for raw in ('null','[]','{"time":"bad"}','{"time":true}','{"time":NaN}','{'):
            (self.directory/'auto-control.json').write_text(raw)
            (self.directory/'native-stop.json').write_text('null')
            with self.subTest(raw=raw),patch.object(agent,'command',side_effect=OSError('unreadable')):
                self.assertTrue(auto_control.stop(runtime=self.directory,persist=self.directory)['queued'])
                self.assertTrue(agent.read_json(self.directory/'native-stop.json')['all_trials'])

    def test_active_journal_requires_complete_safe_recovery_identity(self):
        base={'phase':'COMMITTED','hash':'a'*64,'before':['a','b'],'after':['b','a'],
              'tx':'current','source':'wireguard:a','target':'openvpn:b','trial_nonce':'test',
              'started':10,'deadline':100,'pid':12,'trial':False}
        native.journal_write(base)
        self.assertEqual(native.journal_read()['tx'],'current')
        changes=[{'pid':True},{'pid':-1},{'pid':'12'},{'rollback_failures':'bad'},
                 {'rollback_failures':3},{'trial':'false'},{'source':{}},{'target':base['source']},
                 {'deadline':9},{'after':['a','a']}]
        changes.extend({name:None} for name in ('tx','source','target','trial_nonce','started','deadline'))
        for edit in changes:
            row=dict(base,**edit)
            agent.atomic_json(native.JOURNAL,{'schema':1,'data':row,'sha256':native.digest(row)})
            with self.subTest(edit=edit),self.assertRaises(native.Refused):native.journal_read()
        agent.atomic_json(native.JOURNAL,{'schema':True,'data':base,'sha256':native.digest(base)})
        with self.assertRaises(native.Refused):native.journal_read()

    def test_release_pending_restart_only_retries_cleanup_and_blocks_lifecycle(self):
        journal={'phase':'RELEASE-PENDING','before':['a','b'],'after':['b','a'],'hash':'a'*64,
                 'reason':'EXTERNAL-POLICY-CHANGE','abandoned':True}
        native.journal_write(journal)
        self.assertIsNotNone(lifecycle.assess({}, {'state':'BLOCKED'},journal,{},{}))
        backend=MagicMock()
        with patch.object(native,'Linux',return_value=backend),patch.object(native,'STOP',True),patch.object(native,'publish') as publish,patch.object(native,'clear_native_options',return_value=True):
            backend.unguard.side_effect=native.Refused('GUARD-QUERY-FAILED')
            with self.assertRaisesRegex(native.Refused,'GUARD-RELEASE-UNCONFIRMED'):native.serve()
            self.assertEqual(native.journal_read()['phase'],'RELEASE-PENDING')
            self.assertEqual(publish.call_args.args[0]['state'],'BLOCKED')
            backend.unguard.side_effect=None
            native.serve()
            self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
            self.assertEqual(publish.call_args.args[0]['state'],'STOPPED')
        backend.apply.assert_not_called();backend.reorder.assert_not_called();backend.guard.assert_not_called()

    def test_lifecycle_refuses_empty_existing_and_unhashable_journals(self):
        root=self.directory/'root';target=root/'etc/homensai-vpn/native-transaction.json'
        target.parent.mkdir(parents=True)
        for raw in ('{}','null','[]','false'):
            target.write_text(raw)
            with self.subTest(raw=raw),self.assertRaises(ValueError):lifecycle.snapshot(root)
        row={'phase':'ROLLED-BACK','before':[{},{}],'after':[{},{}],'hash':'a'*64}
        target.write_text(json.dumps({'schema':1,'data':row,'sha256':native.digest(row)}))
        with self.assertRaises(ValueError):lifecycle.snapshot(root)

    def test_failed_release_stays_pending_and_is_retried_without_route_writes(self):
        backend=MagicMock();backend.unguard.side_effect=native.Refused('GUARD-QUERY-FAILED')
        journal={'phase':'COMMITTED','before':['a','b'],'after':['b','a'],'hash':'a'*64,'trial_nonce':'t'}
        with patch.object(native,'clear_native_options',return_value=True),patch.object(native,'publish') as publish:
            with self.assertRaisesRegex(native.Refused,'GUARD-RELEASE-UNCONFIRMED'):native.abandon(backend,journal,'EXTERNAL-POLICY-CHANGE')
            self.assertEqual(native.journal_read()['phase'],'RELEASE-PENDING')
            self.assertEqual(publish.call_args.args[0]['state'],'BLOCKED')
            backend.unguard.side_effect=None
            native.abandon(backend,journal,'EXTERNAL-POLICY-CHANGE')
            self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        backend.apply.assert_not_called();backend.reorder.assert_not_called()

    def test_unguard_verifies_removal(self):
        backend=native.Linux()
        with patch.object(backend,'guard_exists',side_effect=[True,True]),patch.object(native,'command'):
            with self.assertRaisesRegex(native.Refused,'GUARD-RELEASE-UNCONFIRMED'):backend.unguard()

    def test_old_missing_future_and_expired_return_requests_never_roll_back(self):
        backend=MagicMock();journal={'phase':'COMMITTED','tx':'current','started':50}
        requests=[({'tx':'old','time':99},'RETURN-TRANSACTION-MISMATCH'),({'time':99},'RETURN-TRANSACTION-MISMATCH'),({'tx':'current','time':101},'RETURN-REQUEST-EXPIRED'),({'tx':'current','time':1},'RETURN-REQUEST-EXPIRED')]
        for request,code in requests:
            with self.subTest(request=request),patch.object(native.time,'time',return_value=100),patch.object(native,'operator_return') as action:
                self.assertTrue(native.handle_return(backend,journal,request,0)[0]);action.assert_not_called()
                self.assertEqual(agent.read_json(native.return_result_path())['code'],code)

    def test_slow_continuous_http_body_obeys_total_deadline(self):
        left,right=socket.socketpair()
        body=b'ip=8.8.8.8\nhttp=h2\n'
        header=b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'
        class Bound:
            def connect(self,address):pass
            def settimeout(self,value):left.settimeout(value)
            def close(self):left.close()
        def drip():
            try:
                right.sendall(header)
                for byte in body:right.sendall(bytes([byte]));time.sleep(.025)
            except OSError:pass
            finally:right.close()
        worker=threading.Thread(target=drip);worker.start()
        context=MagicMock();context.wrap_socket.return_value=left
        started=time.monotonic()
        try:
            with patch.object(agent,'HTTP_SECONDS',.15),patch.object(agent,'bound_socket',return_value=Bound()),patch.object(agent.ssl,'create_default_context',return_value=context):
                with self.assertRaises(socket.timeout):agent.https_probe('test',1,agent.TARGETS[0])
            self.assertLess(time.monotonic()-started,1)
        finally:left.close();worker.join(2)


if __name__=='__main__':unittest.main()
