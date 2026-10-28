"""Closed activation evidence belongs to its original Auto session only."""
import copy,sys,unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair
import test_pair_manual_directions as fixture


class ActivationEpoch(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PairManualDirections();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(pair,'network',return_value=[]))
        self.stack.enter_context(patch.object(pair,'configs',return_value={}))
        self.stack.enter_context(patch('failover_plan.streak',return_value=False))
        self.stack.enter_context(patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}))
        self.assertTrue(pair.reapply_missing_policy(self.case.backend,pair.read_state(),self.case.settings,self.case.revision,{}))
        self.original=n.journal_read();self.assertEqual(self.original['phase'],'ROLLED-BACK')
        self.assertTrue(self.original['activation_reapply']);self.assertEqual(self.original['trial_nonce'],pair.read_state()['id'])
        self.case.publish.reset_mock()

    def new_epoch(self,change_id=True,change_revision=True):
        state=pair.read_state()
        if change_id:state['id']='d'*32
        if change_revision:state['revision']=auto_control.current_revision(rotate=True)
        state.pop('selected_policy',None);pair.save(state)
        agent.atomic_json(pair.paths()[0],{'mode':'on','id':state['id'],'revision':state['revision'],'time':fixture.NOW})
        self.case.revision=state['revision']
        # A real configure_lease writes this new pair id before any later dispatch.
        self.case.settings['native_trial']=state['id']

    def test_stale_closed_activation_new_start_uses_fresh_target_and_returns_after_existing_dwell(self):
        self.new_epoch();before=n.JOURNAL.read_bytes();budget=self.case.persist/'pair-auto-budget.json'
        self.assertEqual(agent.read_json(budget)['events'],[fixture.NOW])
        with patch.object(n,'committed_recovery_decision',side_effect=AssertionError('old activation must not supply current profile generations')):
            self.assertTrue(pair.tick(self.case.backend,self.case.settings,self.case.revision))
            self.assertEqual(self.case.publish.call_args.args[0]['state'],'OBSERVING')
            self.assertEqual(self.case.publish.call_args.args[0]['kernel_proof']['role'],'target')
            self.assertTrue(self.case.publish.call_args.args[0]['kernel_policy_verified'])
            self.assertEqual(n.JOURNAL.read_bytes(),before)
            with patch('pair_auto.time.time',return_value=fixture.NOW+61):
                self.assertTrue(pair.tick(self.case.backend,self.case.settings,self.case.revision))
        self.assertEqual(self.case.current,['s','t']);self.assertEqual(agent.read_json(budget)['events'],[fixture.NOW,fixture.NOW+61])
        self.assertEqual(self.case.spawn.call_count,2)

    def test_either_nonce_or_revision_mismatch_alone_excludes_closed_activation(self):
        for change_id,change_revision in ((True,False),(False,True)):
            with self.subTest(change_id=change_id,change_revision=change_revision):
                state=pair.read_state();state.update(id='a'*32,revision=self.original['control_revision']);pair.save(state)
                self.new_epoch(change_id,change_revision)
                with patch.object(n,'committed_recovery_decision',side_effect=AssertionError('epoch mismatch')):
                    pair.tick(self.case.backend,self.case.settings,self.case.revision)
                self.assertEqual(self.case.publish.call_args.args[0]['state'],'OBSERVING')

    def test_current_session_closed_bootstrap_keeps_strict_recovery_decision_and_old_proofs(self):
        with patch.object(n,'committed_recovery_decision',return_value={'action':'HOLD','reason':'RESERVE-IDENTITY-UNKNOWN'}) as decision:
            pair.tick(self.case.backend,self.case.settings,self.case.revision)
        decision.assert_called_once();self.assertEqual(decision.call_args.args[1]['vendor_profiles'],self.original['vendor_profiles'])
        self.assertEqual(self.case.publish.call_args.args[0]['state'],'DEGRADED-ON-RESERVE')

    def test_committed_and_held_paths_are_not_retired_by_terminal_epoch_gate(self):
        for phase in ('COMMITTED','HELD-ON-RESERVE'):
            with self.subTest(phase=phase):
                journal=copy.deepcopy(self.original);journal.update(phase=phase,control_revision='f'*32);journal.pop('activation_reapply')
                n.journal_write(journal)
                with patch.object(n,'committed_recovery_decision',return_value={'action':'OBSERVE','reason':'CLIENT-CONFIRMED'}) as decision:
                    pair.tick(self.case.backend,self.case.settings,self.case.revision)
                decision.assert_called_once();self.assertEqual(self.case.publish.call_args.args[0]['state'],'COMMITTED')


if __name__=='__main__':unittest.main()
