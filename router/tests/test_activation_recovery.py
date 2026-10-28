"""Actual failed native activation, exact-baseline archival and no-RTP lifecycle recovery."""
import copy,hashlib,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,activation_recovery as recovery
import test_pair_manual_directions as fixture


class ActivationRecovery(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PairManualDirections();self.case.setUp();self.addCleanup(self.case.doCleanups)
        c=self.case
        def failed(**kwargs):
            row=n.journal_read();row['rtp_dispatched']=True
            if row.get('phase')=='RESTORING':row['restore_rtp_dispatched']=True
            n.journal_write(row)
            raise n.Refused('VENDOR-WORKER-QUIET-UNVERIFIED')
        c.backend.apply.side_effect=failed
        with self.assertRaises(n.Refused):pair.reapply_missing_policy(c.backend,pair.read_state(),c.settings,c.revision,{})
        self.assertEqual(n.journal_read()['phase'],'RESTORING')
        state=pair.read_state();state['phase']='STOPPED';pair.save(state)
        self.revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.revision)
        c.backend.guard_exists.return_value=False
        for mock in (c.backend.apply,c.backend.reorder,c.backend.guard,c.backend.unguard,c.spawn,c.publish):mock.reset_mock()
        self.raw=n.JOURNAL.read_bytes();self.state_raw=pair.paths()[1].read_bytes()
        self.case.enterContext(patch.object(recovery,'platform_checked',return_value=None))
        self.case.enterContext(patch.object(pair,'network',return_value=[]))
        self.case.enterContext(patch.object(pair,'configs',return_value={}))
        self.quiet=self.case.enterContext(patch('native_platform.wait_quiet',return_value=None))

    def archives(self):return list((self.case.persist/'session-recovery').glob('failed-activation-*.json'))
    def untouched(self):
        self.assertEqual(n.JOURNAL.read_bytes(),self.raw);self.case.backend.apply.assert_not_called();self.case.backend.reorder.assert_not_called();self.case.publish.assert_not_called()

    def test_exact_own_failed_missing_baseline_is_archived_and_closed_without_kernel_or_success_claim(self):
        budget=self.case.persist/'pair-auto-budget.json';old_budget=budget.read_bytes()
        answer=recovery.finalize(self.case.backend)
        self.assertEqual(answer['result'],'FINALIZED_UNCHANGED');self.assertFalse(answer['kernel_verified'])
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertTrue(n.journal_read()['failed_activation_unchanged'])
        self.assertEqual(self.archives()[0].read_bytes(),self.raw);self.assertEqual(answer['journal_sha256'],hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(pair.paths()[1].read_bytes(),self.state_raw);self.assertEqual(budget.read_bytes(),old_budget)
        self.case.backend.apply.assert_not_called();self.case.backend.reorder.assert_not_called();self.case.backend.unguard.assert_not_called();self.case.publish.assert_not_called()
        after=n.JOURNAL.read_bytes();again=recovery.finalize(self.case.backend)
        self.assertEqual(again['result'],'ALREADY_FINALIZED');self.assertEqual(n.JOURNAL.read_bytes(),after);self.assertEqual(len(self.archives()),1)

    def test_read_only_check_has_no_archive_or_journal_mutation(self):
        self.assertEqual(recovery.finalize(self.case.backend,check_only=True)['result'],'READY_UNCHANGED')
        self.untouched();self.assertEqual(self.archives(),[])

    def test_on_intent_or_live_guard_refuses_without_writes(self):
        agent.atomic_json(pair.paths()[0],{'mode':'on','id':'a'*32,'revision':self.revision,'time':fixture.NOW})
        with self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
        self.untouched();self.assertEqual(self.archives(),[])
        pair.stop_locked(self.revision);self.case.backend.guard_exists.return_value=True
        with self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
        self.untouched()

    def test_foreign_bound_hash_or_changed_kernel_is_never_adopted(self):
        self.case.fingerprint='f'*64
        with self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
        self.untouched();self.case.fingerprint='c'*64
        self.case.backend.attest_policy.side_effect=lambda *args:{'verified':False,'repairable_missing':True,'kernel_fingerprint':'f'*64}
        with self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
        self.untouched();self.assertEqual(self.archives(),[])

    def test_now_verified_or_foreign_partial_kernel_does_not_satisfy_original_missing_baseline(self):
        for proof in ({'verified':True,'repairable_missing':False},{'verified':False,'repairable_missing':False}):
            self.case.backend.attest_policy.side_effect=lambda *args,proof=proof:proof
            with self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
            self.untouched()

    def test_foreign_identity_process_bindings_or_owned_clients_refuse(self):
        original=pair.read_state()
        for mutate in (lambda s:s['policy_roles'].update(source_id='wireguard:peer_999'),
                       lambda s:s.update(process_bindings={'wgclient1':4096,'ovpnclient1':40960}),
                       lambda s:s.update(owned=['wgclient1'])):
            state=copy.deepcopy(original);mutate(state);pair.save(state)
            with self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
            self.untouched()
        pair.save(original)

    def test_passed_old_snapshot_cannot_overwrite_replacement_before_capture(self):
        old=n.journal_read();new=copy.deepcopy(old);new['failure_code']='PAIR-RECOVERY-REQUIRED';n.journal_write(new)
        current=n.JOURNAL.read_bytes()
        with self.assertRaises(n.Refused):recovery.finalize(self.case.backend,journal=old)
        self.assertEqual(n.JOURNAL.read_bytes(),current);self.assertEqual(self.archives(),[])

    def test_journal_or_state_change_during_expensive_facts_refuses_before_archive(self):
        original=recovery.facts;calls=[0]
        def changed(*args,**kwargs):
            result=original(*args,**kwargs);calls[0]+=1
            if calls[0]==1:
                row=n.journal_read();row['failure_code']='PAIR-RECOVERY-REQUIRED';n.journal_write(row)
            return result
        with patch.object(recovery,'facts',side_effect=changed),self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
        self.assertEqual(n.journal_read()['failure_code'],'PAIR-RECOVERY-REQUIRED');self.assertEqual(self.archives(),[])

    def test_change_after_archive_preserves_newer_journal_and_failed_archive(self):
        original=recovery.facts;calls=[0]
        def changed(*args,**kwargs):
            result=original(*args,**kwargs);calls[0]+=1
            if calls[0]==3:
                row=n.journal_read();row['failure_code']='PAIR-RECOVERY-REQUIRED';n.journal_write(row)
            return result
        with patch.object(recovery,'facts',side_effect=changed),self.assertRaises(n.Refused):recovery.finalize(self.case.backend)
        self.assertEqual(n.journal_read()['phase'],'RESTORING');self.assertEqual(n.journal_read()['failure_code'],'PAIR-RECOVERY-REQUIRED')
        self.assertEqual(self.archives()[0].read_bytes(),self.raw);self.case.backend.apply.assert_not_called()

    def test_normal_stop_closes_exact_failed_activation_then_unguards_without_rtp(self):
        state=pair.read_state();state['phase']='HELD';pair.save(state)
        self.assertTrue(pair.cleanup(self.case.backend,pair.read_state()))
        self.assertEqual(pair.read_state()['phase'],'STOPPED');self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')
        self.assertEqual(len(self.archives()),1);self.case.backend.apply.assert_not_called();self.case.backend.unguard.assert_called_once()

    def test_expensive_live_checks_never_run_under_control_lock(self):
        from contextlib import contextmanager
        original=auto_control.control_lock;held=[False];proof=self.case.backend.attest_policy.side_effect
        @contextmanager
        def lock(*args,**kwargs):
            with original(*args,**kwargs):
                held[0]=True
                try:yield
                finally:held[0]=False
        def checked(*args,**kwargs):self.assertFalse(held[0]);return proof(*args,**kwargs)
        self.case.backend.attest_policy.side_effect=checked
        self.quiet.side_effect=lambda seconds:self.assertFalse(held[0])
        with patch.object(auto_control,'control_lock',side_effect=lock):self.assertEqual(recovery.finalize(self.case.backend)['result'],'FINALIZED_UNCHANGED')


if __name__=='__main__':unittest.main()
