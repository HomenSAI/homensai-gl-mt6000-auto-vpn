"""Corrupt state, replay and overlapping UI intent regressions; local files only."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control as control
import lifecycle_guard as lifecycle
import native_switch as native
import probe_deadline


class AdversarialState(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for module,names in ((native,('RUNTIME','PERSIST')),(control,('RUNTIME','PERSIST')),(agent,('RUNTIME','PERSIST'))):
            for name in names:self.stack.enter_context(patch.object(module,name,self.root))
        self.stack.enter_context(patch.object(native,'JOURNAL',self.root/'journal'))

    def test_shared_reader_rejects_ambiguous_nonfinite_and_deep_real_files(self):
        path=self.root/'state'
        bad=['{"requested":1,"requested":2}','{"x":NaN}','{"x":Infinity}',
             '{"x":-Infinity}','{"x":1e999}','{"x":'+('9'*400)+'}',
             '{"x":'+('['*70)+'0'+(']'*70)+'}',
             '{"x":'+('['*2000)+'0'+(']'*2000)+'}']
        for raw in bad:
            path.write_text(raw)
            with self.subTest(raw=raw[:50]),self.assertRaises(ValueError):agent.read_json(path)

    def test_shared_reader_preserves_missing_default_and_finite_legacy_values(self):
        missing=object();path=self.root/'state'
        self.assertIs(agent.read_json(path,missing),missing)
        value={'counter':2**64,'negative':-5,'fraction':1.25,'items':[None,False,{}]}
        path.write_text(json.dumps(value));self.assertEqual(agent.read_json(path,missing),value)
        path.write_text('null');self.assertIsNone(agent.read_json(path,missing))

    def test_deep_or_duplicate_journal_is_a_coded_integrity_refusal(self):
        for raw in ('['*2000+'0'+']'*2000,'{"schema":1,"schema":2}'):
            native.JOURNAL.write_text(raw)
            with self.subTest(raw=raw[:30]),self.assertRaisesRegex(native.Refused,'JOURNAL-INTEGRITY-FAILED'):
                native.journal_read()

    def test_standalone_lifecycle_reader_rejects_same_bad_state(self):
        path=self.root/'state'
        for raw in ('{"state":"STOPPED","state":"DISABLED"}','{"time":NaN}',
                    '{"time":1e999}','{"time":'+('9'*400)+'}',
                    '{"x":'+'['*2000+'0'+']'*2000+'}'):
            path.write_text(raw)
            with self.subTest(raw=raw[:40]),self.assertRaises(ValueError):lifecycle.read_dict(path)

    def test_lifecycle_wrong_state_type_is_a_refusal_even_with_stop_ack(self):
        intent={'mode':'on','trial':'t','time':1};stopped={'trial':'t','requested':2}
        for state in ([],{},True,1,None):
            with self.subTest(state=state):
                self.assertIsNotNone(lifecycle.assess({}, {'state':state,'time':3},{},intent,stopped))
        self.assertFalse(lifecycle.finite(10**400))

    def test_falsey_or_scalar_existing_lease_cannot_rearm_elapsed_window(self):
        path=self.root/'native-lease.json'
        for raw in ('null','false','0','[]','{}','"old"'):
            path.write_text(raw)
            with self.subTest(raw=raw):
                self.assertEqual(native.monotonic_lease({'native_trial':'same'},2000,500,200),
                                 (0,'LEASE-INTEGRITY-FAILED'))
                self.assertEqual(path.read_text(),raw)

    def test_boolean_lease_timestamps_cannot_rearm_or_validate_a_window(self):
        for field in ('monotonic_start','monotonic_until'):
            row={'identity':native.digest({'trial':'same','until':2000}),
                 'monotonic_start':0,'monotonic_until':100}
            row[field]=True
            agent.atomic_json(self.root/'native-lease.json',{'data':row,'sha256':native.digest(row)})
            with self.subTest(field=field):
                self.assertEqual(native.monotonic_lease({'native_trial':'same'},2000,1000,100),
                                 (0,'LEASE-INTEGRITY-FAILED'))

    def test_rejected_future_return_cannot_poison_the_next_real_return(self):
        backend=MagicMock();journal={'phase':'COMMITTED','tx':'current','started':50}
        with patch.object(native.time,'time',return_value=100),patch.object(native,'operator_return',return_value='SOURCE-NOT-HEALTHY') as action:
            handled,watermark=native.handle_return(backend,journal,{'tx':'current','time':10000},0)
            self.assertTrue(handled);action.assert_not_called()
            # The same corrupt record remains deduplicated across observations.
            self.assertEqual(native.handle_return(backend,journal,{'tx':'current','time':10000},watermark),(False,watermark))
            self.assertTrue(native.handle_return(backend,journal,{'tx':'current','time':99},watermark)[0])
            action.assert_called_once()
            self.assertEqual(agent.read_json(native.return_result_path())['code'],'SOURCE-NOT-HEALTHY')

    def test_terminal_recovery_unknown_policy_and_failed_config_clear_is_global(self):
        backend=MagicMock();backend.policy.side_effect=OSError('unreadable')
        with patch.object(native,'STOP',True),patch.object(native,'clear_native_options',return_value=False),patch.object(native,'publish'):
            native.give_up(backend,{},'JOURNAL-INTEGRITY-FAILED')
        stopped=agent.read_json(self.root/'native-stop.json')
        self.assertTrue(stopped['all_trials'])
        self.assertEqual(control.effective_intent({'native_enabled':'1','native_trial':'new'},stopped,{},time.time()),(False,True))

    def test_terminal_recovery_uses_ui_lock_and_never_moves_stop_epoch_backwards(self):
        agent.atomic_json(self.root/'native-stop.json',{'requested':200,'trial':'old'})
        from contextlib import contextmanager
        entered=[]
        @contextmanager
        def lock(directory):
            entered.append(directory);yield
        with patch.object(control,'control_lock',side_effect=lock),patch.object(native.time,'time',return_value=100):
            native.stop_latch('current')
        self.assertEqual(entered,[self.root])
        self.assertEqual(agent.read_json(self.root/'native-stop.json'),{'requested':200,'trial':'current','all_trials':True})

    def test_malformed_stop_scope_cannot_silently_enable_a_different_trial(self):
        settings={'native_enabled':'1','native_trial':'new'}
        for stopped in ({'requested':100},{'requested':100,'trial':[]},
                        {'requested':100,'trial':'old','all_trials':'true'}):
            with self.subTest(stopped=stopped):
                self.assertEqual(control.effective_intent(settings,stopped,{},102),(False,True))

    def test_nonfinite_wrong_type_and_negative_deadlines_are_coded_refusals(self):
        for value in ([],{},True,'bad','NaN','Infinity','1e999',float('nan'),float('inf'),-1,10**400):
            with self.subTest(value=str(value)[:40]),self.assertRaises(native.Refused):native.deadline(value)
        self.assertEqual(native.deadline(None),0)
        self.assertEqual(native.deadline('2026-10-15T14:00:00+02:00'),native.deadline('2026-10-15T12:00:00Z'))

    def test_probe_adapter_refuses_unbounded_or_invalid_deadlines(self):
        for value in (None,True,'123',float('nan'),float('inf'),-float('inf'),10**400):
            with self.subTest(value=str(value)[:40]),self.assertRaises(socket.timeout):probe_deadline.remaining(value)

    def prepare_start(self):
        now=time.time();until=now+120
        settings={'native_trial':'nonce','native_until':str(until),'native_session_loss':'1','native_enabled':'0'}
        selection={'hash':'h','source':{'id':'a'},'target':{'id':'b'},'direction':'first'}
        backend=MagicMock();backend.policy.return_value={'settings':settings}
        backend.diagnostic.return_value=([],selection)
        self.stack.enter_context(patch.object(native,'Linux',return_value=backend))
        self.stack.enter_context(patch.object(native,'journal_read',return_value={}))
        agent.atomic_json(self.root/'native-certificate.json',dict(hash='h',source='a',target='b',direction='first',until=until))
        agent.atomic_json(self.root/'native-attempts.json',{'trial':'nonce','count':1})
        self.revision=control.current_revision()
        return backend,settings,selection

    def test_stop_finishes_during_start_preflight_and_cancels_stale_completion(self):
        backend,settings,selection=self.prepare_start()
        entered=threading.Event();release=threading.Event();stopped=threading.Event();results={}
        def diagnostic():
            entered.set()
            if not release.wait(3):raise AssertionError('test preflight release deadline')
            return [],selection
        def start():
            try:results['start']=control.start(self.revision)
            except BaseException as error:results['start_error']=type(error).__name__
        def stop():
            try:results['stop']=control.stop()
            except BaseException as error:results['stop_error']=type(error).__name__
            finally:stopped.set()
        backend.diagnostic.side_effect=diagnostic
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):
            first=threading.Thread(target=start);first.start();second=None
            try:
                self.assertTrue(entered.wait(2))
                second=threading.Thread(target=stop);second.start()
                stop_was_prompt=stopped.wait(.5)
            finally:
                release.set();first.join(4)
                if second is not None:second.join(4)
            self.assertFalse(first.is_alive());self.assertFalse(second.is_alive())
            self.assertTrue(stop_was_prompt,'Stop waited behind read-only Start diagnostics')
        self.assertNotIn('start_error',results);self.assertNotIn('stop_error',results)
        self.assertEqual(results['start'],{'accepted':False,'blockers':['CONTROL-REVISION-STALE']})
        self.assertTrue(results['stop']['queued'])
        self.assertFalse((self.root/'auto-control.json').exists())

    def test_settings_or_journal_drift_during_start_preflight_never_writes(self):
        backend,settings,selection=self.prepare_start()
        backend.policy.side_effect=[{'settings':settings},{'settings':dict(settings,native_trial='new')}]
        self.assertEqual(control.start(self.revision),{'accepted':False,'blockers':['START-CONFIG-CHANGED']})
        self.assertFalse((self.root/'auto-control.json').exists())
        backend.policy.side_effect=[{'settings':settings,'sections':['before']},
                                    {'settings':settings,'sections':['changed']}]
        self.assertEqual(control.start(self.revision),{'accepted':False,'blockers':['START-CONFIG-CHANGED']})
        self.assertFalse((self.root/'auto-control.json').exists())
        backend.policy.side_effect=None
        with patch.object(native,'journal_read',side_effect=[{}, {'phase':'WAIT-CLIENT'}]):
            self.assertEqual(control.start(self.revision),{'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']})
        self.assertFalse((self.root/'auto-control.json').exists())

    def test_corrupt_certificate_attempts_or_stop_refuse_start_without_traceback(self):
        self.prepare_start()
        for name,raw in (('native-certificate.json','[]'),('native-attempts.json','{"count":"three"}'),('native-stop.json','[]')):
            path=self.root/name;saved=path.read_bytes() if path.exists() else None
            path.write_text(raw)
            try:
                with self.subTest(name=name):self.assertFalse(control.start(self.revision)['accepted'])
                self.assertFalse((self.root/'auto-control.json').exists())
            finally:
                if saved is None:path.unlink()
                else:path.write_bytes(saved)

    def test_missing_malformed_or_old_control_revision_never_starts(self):
        self.prepare_start()
        for revision in (None,'',True,[],{},'A'*32,'a'*31,'b'*32):
            with self.subTest(revision=revision):
                self.assertEqual(control.start(revision),{'accepted':False,'blockers':['CONTROL-REVISION-STALE']})
        self.assertFalse((self.root/'auto-control.json').exists())

    def test_delayed_start_arriving_after_stop_is_refused_from_every_session(self):
        self.prepare_start()
        first_browser_revision=control.public_status()['control_revision']
        second_browser_revision=control.public_status()['control_revision']
        self.assertEqual(first_browser_revision,second_browser_revision)
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):
            self.assertTrue(control.stop()['queued'])
        for old_revision in (first_browser_revision,second_browser_revision):
            self.assertEqual(control.start(old_revision),{'accepted':False,'blockers':['CONTROL-REVISION-STALE']})
        self.assertFalse((self.root/'auto-control.json').exists())
        self.assertTrue(control.start(control.current_revision())['accepted'])

    def test_repeated_stop_rotates_ram_revision_without_rewriting_flash_latch(self):
        self.prepare_start()
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):
            control.stop();pending_revision=control.current_revision()
            before=(self.root/'native-stop.json').read_bytes()
            with patch.object(control,'atomic_json',wraps=agent.atomic_json) as write:
                self.assertTrue(control.stop()['already_requested'])
            self.assertEqual((self.root/'native-stop.json').read_bytes(),before)
            self.assertEqual([call.args[0].name for call in write.call_args_list],['auto-control-revision.json'])
        self.assertNotEqual(control.current_revision(),pending_revision)
        self.assertEqual(control.start(pending_revision),{'accepted':False,'blockers':['CONTROL-REVISION-STALE']})

    def test_concurrent_stops_rotate_independently_and_dedupe_durable_write(self):
        self.prepare_start();old_revision=self.revision;results=[]
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'),patch.object(control,'atomic_json',wraps=agent.atomic_json) as write:
            workers=[threading.Thread(target=lambda:results.append(control.stop())) for _ in range(2)]
            for worker in workers:worker.start()
            for worker in workers:worker.join(3)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            self.assertEqual(len(results),2);self.assertTrue(all(row['queued'] for row in results))
            paths=[call.args[0].name for call in write.call_args_list]
            self.assertEqual(paths.count('auto-control-revision.json'),2)
            self.assertEqual(paths.count('native-stop.json'),1)
        self.assertNotEqual(control.current_revision(),old_revision)
        self.assertFalse(control.start(old_revision)['accepted'])

    def test_runtime_reset_or_supervisor_restart_invalidates_old_revision(self):
        self.prepare_start();old=self.revision
        (self.root/'auto-control-revision.json').unlink()
        refreshed=control.public_status()['control_revision'];self.assertNotEqual(refreshed,old)
        self.assertFalse(control.start(old)['accepted'])
        with patch.object(native,'Linux',return_value=MagicMock()),patch.object(native,'STOP',True):native.serve()
        self.assertNotEqual(control.current_revision(),refreshed)
        self.assertFalse(control.start(refreshed)['accepted'])

    def test_revision_storage_failure_still_latches_stop_and_blocks_old_start(self):
        self.prepare_start()
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'),patch.object(control,'revision_locked',side_effect=OSError('RAM full')):
            with self.assertRaises(OSError):control.stop()
        stopped=agent.read_json(self.root/'native-stop.json');self.assertTrue(stopped['control_revision_failed'])
        self.assertIsNone(control.public_status()['control_revision'])
        self.assertEqual(control.start(self.revision),{'accepted':False,'blockers':['CONTROL-REVISION-STALE']})
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):
            self.assertTrue(control.stop()['queued'])
        self.assertNotIn('control_revision_failed',agent.read_json(self.root/'native-stop.json'))
        self.assertRegex(control.public_status()['control_revision'],r'^[a-f0-9]{32}$')

    def test_supervisor_revision_storage_failure_cannot_skip_durable_global_stop(self):
        self.prepare_start();backend=MagicMock();backend.policy.return_value={'settings':{'native_trial':'nonce'}}
        with patch.object(native,'Linux',return_value=backend),patch.object(native,'STOP',True),patch.object(native,'clear_native_options',return_value=False),patch.object(native,'publish') as publish,patch.object(control,'revision_locked',side_effect=OSError('RAM full')):
            native.serve()
        stopped=agent.read_json(self.root/'native-stop.json')
        self.assertTrue(stopped['all_trials']);self.assertTrue(stopped['control_revision_failed'])
        self.assertEqual(publish.call_args.args[0]['alarm'],'CONTROL-REVISION-STALE')
        backend.apply.assert_not_called();backend.reorder.assert_not_called();backend.guard.assert_not_called()

    def test_status_rpc_overlays_live_revision_and_start_rpc_requires_exact_field(self):
        self.prepare_start();before=self.revision
        agent.atomic_json(self.root/'status.json',{'version':agent.VERSION,'auto_control':{'control_revision':before}})
        with patch.object(agent,'command',return_value=b'{"settings":{"native_trial":"nonce"}}'):control.stop()
        after=control.current_revision();self.assertNotEqual(before,after)
        output=io.StringIO()
        with patch.object(agent,'RUNTIME',self.root),patch.object(agent,'PERSIST',self.root),patch.object(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'{}'))),redirect_stdout(output):
            agent.rpc('status')
        self.assertEqual(json.loads(output.getvalue())['auto_control']['control_revision'],after)
        self.assertEqual(agent.read_json(self.root/'status.json')['auto_control']['control_revision'],before)
        for arguments in ({},{'control_revision':after,'extra':True},{'control_revision':after}):
            output=io.StringIO()
            with patch.object(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(arguments).encode()))),patch.object(control,'start',return_value={'accepted':True,'queued':True}) as start,redirect_stdout(output):
                agent.rpc('native_start')
            if set(arguments)=={'control_revision'}:start.assert_called_once_with(after)
            else:
                start.assert_not_called();self.assertEqual(json.loads(output.getvalue())['blockers'],['CONTROL-REVISION-STALE'])


if __name__=='__main__':unittest.main()
