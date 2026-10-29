"""Independent-review failures replayed through the actual native/pair protocol."""
import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,native_switch as n,pair_auto as pair,pair_manual as manual
import test_pair_manual_directions as fixture
NOW=fixture.NOW;SOURCE=fixture.SOURCE;TARGET=fixture.TARGET


class ReviewRegressions(unittest.TestCase):
    enterContext=fixture.PairManualDirections.enterContext
    def setUp(self):fixture.PairManualDirections.setUp(self)
    reorder=fixture.PairManualDirections.reorder
    apply=fixture.PairManualDirections.apply
    process=fixture.PairManualDirections.process
    kernel_proof=fixture.PairManualDirections.kernel_proof
    request=fixture.PairManualDirections.request
    allow_next=fixture.PairManualDirections.allow_next

    def tick(self):
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}),patch('failover_plan.streak',return_value=True),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}):
            return pair.tick(self.backend,self.settings,self.revision)

    def test_foreign_graph_before_child_never_reaches_rtp_or_blind_rollback(self):
        foreign=[False];process=self.process
        self.backend.attest_policy.side_effect=lambda selection=None: {'verified':False,'repairable_missing':False,'kernel_fingerprint':'f'*64} if foreign[0] else self.kernel_proof(selection)
        def spawn(*args,**kwargs):
            child=process(*args,**kwargs);wait=child.wait.side_effect
            def changed(**kwargs):foreign[0]=True;return wait(**kwargs)
            child.wait.side_effect=changed;return child
        self.spawn.side_effect=spawn
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertTrue(foreign[0]);self.backend.apply.assert_not_called()
        self.assertFalse(n.journal_read()['rtp_dispatched']);self.assertEqual(self.current,['t','s'])

    def test_foreign_graph_after_uci_reorder_is_preserved_and_only_own_order_is_restored(self):
        foreign=[False];reorder=self.reorder
        self.backend.kernel_fingerprint.side_effect=lambda:'f'*64 if foreign[0] else self.kernel_proof()['kernel_fingerprint']
        def changed(order,**kwargs):
            reorder(order,**kwargs)
            if kwargs.get('write_command') is not None:foreign[0]=True
        self.backend.reorder.side_effect=changed
        dispatched=[]
        def apply(write_command=None):
            # Like the real apply(): the vendor rebuild is always a fenced write.
            write_command(['/usr/bin/rtp2.sh','not_reload_network'],timeout=n.RTP_TIMEOUT);dispatched.append(True)
        self.backend.apply.side_effect=apply
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertEqual(dispatched,[])
        self.assertTrue(foreign[0]);self.assertEqual(self.current,['t','s']);self.assertFalse(n.journal_read()['rtp_dispatched'])

    def test_automatic_predispatch_diagnostic_refusal_does_not_charge_budget(self):
        self.current=['s','t'];self.state['order']=list(self.current);pair.save(self.state);self.kernel_applied=True
        calls=[0]
        def diagnostic():
            calls[0]+=1
            if calls[0]>=3:return ['PROFILE-IDENTITY-CHANGED'],None
            return [],dict(copy.deepcopy(self.selection),order=list(self.current))
        self.backend.diagnostic.side_effect=diagnostic
        self.tick()
        self.spawn.assert_not_called();self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_busy_committed_tick_cannot_claim_kernel_or_readiness_without_attestation(self):
        self.request('reserve');manual.request('resume',self.revision);manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.backend.diagnostic.side_effect=lambda:(['VENDOR-WORKER-BUSY'],None)
        self.backend.attest_policy.reset_mock();self.tick()
        value=self.publish.call_args.args[0]
        self.assertEqual(value['state'],'BLOCKED');self.assertIs(value['kernel_policy_verified'],False);self.assertIs(value['readiness_verified'],False)
        self.backend.attest_policy.assert_not_called()

    def test_same_reserve_hold_resume_returns_after_stability_without_inventing_a_journal(self):
        self.kernel_applied=True;self.request('reserve');self.assertEqual(n.journal_read(),{})
        self.assertTrue(manual.request('resume',self.revision)['accepted']);manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.tick();self.spawn.assert_not_called();self.assertEqual(n.journal_read(),{})
        with patch('pair_manual.time.time',return_value=NOW+61):self.tick()
        self.assertEqual(self.current,['s','t']);self.assertEqual(n.journal_read()['before'],['t','s']);self.assertEqual(n.journal_read()['after'],['s','t'])
        self.assertEqual(n.journal_read()['pair_transition']['destination_role'],'source');self.spawn.assert_called_once()

    def test_primary_manual_is_not_original_restoration_when_session_started_on_reserve(self):
        self.request('primary')
        self.assertEqual(self.current,['s','t']);self.assertEqual(pair.read_state()['order'],['t','s'])
        self.assertIs(self.publish.call_args.args[0]['original_restored'],False)

    def test_foreign_graph_during_restore_ordering_never_reaches_restore_rtp(self):
        self.kernel_applied=True;self.request('primary');before=self.backend.apply.call_count
        foreign=[False];reorder=self.reorder
        self.backend.kernel_fingerprint.side_effect=lambda:'f'*64 if foreign[0] else self.kernel_proof()['kernel_fingerprint']
        def changed(order,**kwargs):
            reorder(order,**kwargs)
            if kwargs.get('before_write') is not None:foreign[0]=True
        self.backend.reorder.side_effect=changed
        journal=n.journal_read()
        with self.assertRaisesRegex(n.Refused,'KERNEL-POLICY-UNVERIFIED'):
            n.rollback(self.backend,journal,'PAIR-STOPPED',restore_order=self.state['order'])
        self.assertTrue(foreign[0]);self.assertEqual(self.backend.apply.call_count,before)
        self.assertEqual(n.journal_read()['phase'],'RESTORING')


if __name__=='__main__':unittest.main()
