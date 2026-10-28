"""Actual native transaction protocol in both configured pair directions."""
import copy,hashlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,pair_manual as manual,pair_policy
import test_pair_manual as fixture
from vendor_fixture import stamp

REAL_JOURNAL_READ=n.journal_read
NOW=fixture.NOW;SOURCE=fixture.SOURCE;TARGET=fixture.TARGET


class PairManualDirections(unittest.TestCase):
    enterContext=fixture.Tests.enterContext
    def setUp(self):
        fixture.Tests.setUp(self)
        self.current=['t','s'];self.fingerprint='c'*64
        self.selection.update(source_rule='s',target_rule='t',direction='first',generic_rules=['s','t'],
                              order=list(self.current),proof_scope=pair.MODE,process_bindings=None)
        stamp(self.selection['source'].update(interface='wgclient1') or self.selection['source'],NOW)
        stamp(self.selection['target'].update(interface='ovpnclient1') or self.selection['target'],NOW)
        self.state.update(order=list(self.current),owned=[],process_bindings=None,policy_roles=pair_policy.proof(self.selection))
        self.state['network_identity']=pair.normalized_network([])
        pair.save(self.state)
        self.settings.update(native_trial='a'*32,native_until=str(NOW+180),native_proof_scope=pair.MODE)
        self.enterContext(patch.object(n,'journal_read',side_effect=REAL_JOURNAL_READ))
        self.enterContext(patch.object(n,'CERT',self.persist/'native-certificate.json'))
        self.backend.diagnostic.side_effect=lambda:([],dict(copy.deepcopy(self.selection),order=list(self.current)))
        self.backend.order.side_effect=lambda:(list(self.current),self.fingerprint)
        self.backend.reorder.side_effect=self.reorder
        self.kernel_applied=False
        self.kernel_order=None
        self.backend.apply.side_effect=self.apply
        self.backend.attest_policy.side_effect=self.kernel_proof
        self.backend.kernel_fingerprint.side_effect=lambda:self.kernel_proof()['kernel_fingerprint']
        self.backend.devices.return_value=['wgclient1','tun0']
        self.backend.recovery_ready.return_value=True
        self.enterContext(patch.object(pair,'configure_lease',return_value=NOW+180))
        self.enterContext(patch.object(n,'monotonic_lease',return_value=(n.time.monotonic()+180,None)))
        self.enterContext(patch.object(n,'trace',return_value='9.9.9.9'))
        self.probe=self.enterContext(patch.object(n,'probe',return_value={'code':None,'dns_ok':True,'https_success':2}))
        self.enterContext(patch.object(n.os,'killpg'))
        self.enterContext(patch.object(n,'clear_native_options',return_value=True))
        self.enterContext(patch.object(n,'STOP',False))
        self.enterContext(patch('rtp_boot.assess',return_value={'safe':True,'ready':True,'kernel_verified':False}))
        self.enterContext(patch('rtp_boot.prepare',return_value={'prepared':True,'changed':False,'kernel_verified':False}))
        self.enterContext(patch('rtp_boot.ready',return_value=True))
        self.spawn=self.enterContext(patch.object(n.subprocess,'Popen',side_effect=self.process))
        self.worker_error=None

    def reorder(self,order,**kwargs):
        if kwargs.get('before_write') is not None:kwargs['before_write']()
        elif kwargs.get('write_command') is not None:n.require_control_revision(self.revision)
        if self.kernel_applied and self.kernel_order is None:self.kernel_order=list(self.current)
        self.current=list(order)

    def apply(self,**kwargs):
        journal=n.journal_read()
        if journal.get('phase')=='APPLYING':
            journal['rtp_dispatched']=True;n.journal_write(journal)
        self.kernel_applied=True;self.kernel_order=list(self.current)

    def kernel_proof(self,selection=None):
        actual=self.kernel_order if self.kernel_order is not None else self.current
        current=pair_policy.role(self.state['policy_roles'],actual)
        fingerprint=hashlib.sha256(repr((self.kernel_applied,actual if self.kernel_applied else None)).encode()).hexdigest()
        return {'verified':self.kernel_applied and actual==self.current,'repairable_missing':not self.kernel_applied,'role':current,'profile_id':SOURCE if current=='source' else TARGET,
                'order':list(self.current),'policy_hash':self.fingerprint,'time':n.time.time(),'kernel_fingerprint':fingerprint}

    def process(self,*args,**kwargs):
        process=Mock(pid=os.getpid(),returncode=0)
        def wait(**kwargs):
            if process.returncode:return
            try:n.child(args[0][-1])
            except n.Refused as error:self.worker_error=error;process.returncode=1
        process.wait.side_effect=wait
        return process

    def request(self,direction):
        answer=manual.request(direction,self.revision)
        self.assertTrue(answer['accepted'],answer)
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED',manual.public())
        return n.journal_read()

    def allow_next(self):
        (self.persist/'pair-auto-budget.json').unlink(missing_ok=True)

    def test_initial_reserve_first_primary_then_reserve_uses_actual_before_after(self):
        first=self.request('primary')
        self.assertEqual(first['before'],['t','s']);self.assertEqual(first['after'],['s','t'])
        self.assertEqual(first['pair_transition']['destination_role'],'source')
        self.assertEqual(first['pair_transition']['session_order'],['t','s'])
        self.assertEqual(pair.read_state()['manual_hold'],'source')
        self.allow_next();second=self.request('reserve')
        self.assertEqual(second['before'],['s','t']);self.assertEqual(second['after'],['t','s'])
        self.assertEqual(second['pair_transition']['destination_role'],'target')
        self.assertEqual(pair.read_state()['manual_hold'],'target')
        self.assertEqual(self.spawn.call_count,2);self.assertEqual(self.backend.apply.call_count,2)
        self.assertEqual(pair.intent()['mode'],'on')

    def test_reserve_already_first_reapplies_and_verifies_instead_of_fabricating_switch(self):
        journal=self.request('reserve')
        self.assertEqual(journal['before'],['t','s']);self.assertEqual(journal['after'],['t','s'])
        self.assertEqual(journal['pair_transition']['primary_order'],['s','t'])
        self.backend.apply.assert_called_once();self.spawn.assert_called_once()
        self.assertTrue(journal['confirmed']);self.assertEqual(pair.read_state()['manual_hold'],'target')

    def test_successful_same_order_activation_stops_through_verified_normal_restoration(self):
        self.assertTrue(pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{}))
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')
        self.assertTrue(n.journal_read()['activation_reapply'])
        self.assertEqual(n.journal_read()['kernel_confirmed'],NOW)
        revision=auto_control.current_revision(rotate=True);pair.stop_locked(revision)
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}), \
                patch('activation_recovery.finalize',side_effect=AssertionError('successful activation is not a failed missing baseline')):
            self.assertTrue(pair.cleanup(self.backend,pair.read_state()))
        self.assertEqual(pair.read_state()['phase'],'STOPPED');self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')
        self.assertTrue(self.kernel_proof()['verified']);self.assertEqual(self.current,['t','s'])

    def test_already_kernel_verified_selection_has_hold_without_fake_journal_or_budget_charge(self):
        self.kernel_applied=True
        events=[NOW-30,NOW-20,NOW-10]
        agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':events})
        answer=manual.request('reserve',self.revision);self.assertTrue(answer['accepted'],answer)
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED');self.assertEqual(manual.public()['code'],'MANUAL-ALREADY-SELECTED')
        self.spawn.assert_not_called();self.backend.apply.assert_not_called();self.assertEqual(n.journal_read(),{})
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],events)
        self.assertEqual(pair.read_state()['manual_hold'],'target');self.assertEqual(pair.read_state()['manual_selection']['role'],'target')

    def test_failed_predispatch_proof_never_consumes_attempt_budget(self):
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        self.backend.diagnostic.side_effect=lambda:([],dict(copy.deepcopy(self.selection),order=list(self.current),vendor_identity='f'*64))
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.spawn.assert_not_called()
        self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_worker_spawn_failure_is_not_charged_and_leaves_a_closed_honest_journal(self):
        self.spawn.side_effect=OSError('simulated worker creation failure')
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'UNCONFIRMED')
        self.assertFalse((self.persist/'pair-auto-budget.json').exists())
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertEqual(n.journal_read()['before'],['t','s'])
        self.assertEqual(self.current,['t','s']);self.assertNotIn('manual_hold',pair.read_state())

    def test_missing_kernel_after_apply_cannot_commit_or_select_a_green_channel(self):
        self.backend.apply.side_effect=None
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertNotEqual(manual.public()['state'],'COMPLETED');self.assertNotIn('manual_hold',pair.read_state())
        self.assertNotIn(n.journal_read().get('phase'),('COMMITTED','HELD-ON-RESERVE'))

    def test_legacy_forward_order_guard_is_not_relaxed(self):
        with self.assertRaisesRegex(n.Refused,'SOURCE-ORDER-MISMATCH'):
            n.attempt(self.backend,dict(self.selection,order=['t','s']),NOW+180,False,control_revision=self.revision)
        self.spawn.assert_not_called()

    def test_stop_before_apply_prevents_every_forward_write(self):
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        auto_control.current_revision(rotate=True)
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'CANCELLED');self.backend.reorder.assert_not_called();self.spawn.assert_not_called()

    def test_stop_after_apply_restores_real_previous_order_and_never_saves_hold(self):
        self.backend.apply.side_effect=lambda **kwargs:auto_control.current_revision(rotate=True)
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['state'],'CANCELLED');self.assertNotIn('manual_hold',pair.read_state())
        self.assertEqual(self.current,['t','s'])

    def test_failed_new_transition_rolls_back_its_real_before_not_session_original(self):
        self.request('primary');self.allow_next()
        self.backend.apply.side_effect=[n.Refused('VENDOR-APPLY-FAILED'),None]
        answer=manual.request('reserve',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        journal=n.journal_read()
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertEqual(self.current,['s','t'])
        self.assertEqual(journal['before'],['s','t']);self.assertEqual(journal['restored_order'],['s','t'])
        self.assertEqual(pair.read_state()['manual_hold'],'source')

    def test_stop_cleanup_restores_original_session_order_after_multiple_manual_changes(self):
        self.request('primary');self.allow_next();self.request('reserve');self.allow_next();self.request('primary')
        self.assertEqual(self.current,['s','t'])
        self.assertTrue(pair.cleanup(self.backend,pair.read_state()))
        self.assertEqual(self.current,['t','s']);self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.assertEqual(n.journal_read()['before'],['t','s'])
        self.assertEqual(n.journal_read()['restored_order'],['t','s'])

    def test_primary_hold_and_resume_keep_roles_and_do_not_restore_initial_reserve_by_accident(self):
        journal=self.request('primary')
        resolved={'coordination':{'state':'READY'},'source':self.selection['source'],'target':self.selection['target']}
        with patch('failure_diagnosis.resolve_pair',return_value=resolved),patch('failover_plan.streak',return_value=False):
            self.assertTrue(manual.held_reserve(self.backend,pair.read_state(),journal,self.settings,{}))
        self.assertEqual(self.publish.call_args.args[0]['reason'],'PAIR-MANUAL-HOLD-PRIMARY')
        applied=self.backend.apply.call_count
        self.assertTrue(manual.request('resume',self.revision)['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertNotIn('manual_hold',pair.read_state())
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}), \
                patch('failover_plan.streak',return_value=False),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}):
            pair.tick(self.backend,self.settings,self.revision)
        self.assertEqual(self.current,['s','t']);self.assertEqual(self.backend.apply.call_count,applied)

    def test_reserve_hold_resume_uses_explicit_primary_order_even_when_no_order_changed_at_start(self):
        self.request('reserve')
        self.assertTrue(manual.request('resume',self.revision)['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}), \
                patch.object(n,'committed_recovery_decision',return_value={'action':'RESTORE-PRIMARY','reason':'PRIMARY-STABLY-RECOVERED'}), \
                patch('failover_plan.streak',return_value=False),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}):
            pair.tick(self.backend,self.settings,self.revision)
        self.assertEqual(self.current,['s','t']);self.assertNotIn('manual_hold',pair.read_state())
        self.assertEqual(n.journal_read()['before'],['t','s']);self.assertEqual(n.journal_read()['restored_order'],['s','t'])

    def test_actual_kernel_drift_during_manual_hold_never_publishes_a_verified_hold(self):
        self.kernel_applied=True
        answer=manual.request('reserve',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.kernel_applied=False
        self.assertFalse(manual.held_reserve(self.backend,pair.read_state(),{},self.settings,{}))
        self.assertEqual(self.spawn.call_count,0)

    def test_unknown_session_or_policy_change_never_dispatches(self):
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        self.fingerprint='f'*64
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['code'],'MANUAL-CONFIG-CHANGED');self.spawn.assert_not_called()

    def test_unhealthy_primary_cannot_be_selected_by_reverse_manual_path(self):
        self.backend.health.return_value=False
        answer=manual.request('primary',self.revision);self.assertTrue(answer['accepted'])
        manual.consume(self.backend,pair.read_state(),self.settings,self.revision)
        self.assertEqual(manual.public()['code'],'SOURCE-NOT-HEALTHY');self.spawn.assert_not_called()
        self.assertFalse((self.persist/'pair-auto-budget.json').exists())

    def test_return_target_recovery_records_destination_separately_from_original_before(self):
        journal=self.request('reserve')
        self.assertEqual(journal['before'],journal['after'])
        self.assertTrue(n.finish_committed(self.backend,journal,'PRIMARY-STABLY-RECOVERED'))
        self.assertEqual(self.current,['s','t'])
        self.assertEqual(journal['before'],['t','s']);self.assertEqual(journal['restored_order'],['s','t'])

    def test_supervisor_reapplies_wholly_absent_policy_once_without_changing_configured_order(self):
        self.assertTrue(pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{}))
        journal=n.journal_read()
        self.assertTrue(journal['activation_reapply']);self.assertEqual(journal['before'],['t','s']);self.assertEqual(journal['after'],['t','s'])
        self.assertEqual(self.current,['t','s']);self.assertEqual(journal['pair_transition']['destination_role'],'target')
        self.assertNotIn('confirmed',journal);self.assertEqual(journal['kernel_confirmed'],NOW)
        self.probe.assert_not_called()
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],[NOW])
        self.assertFalse(pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,journal))
        self.spawn.assert_called_once()

    def test_never_verified_primary_down_does_not_block_healthy_reserve_failover(self):
        self.current=['s','t'];self.state['order']=list(self.current);pair.save(self.state)
        self.selection['source']['kernel_binding']={'code':'VPN-001'}
        self.probe.side_effect=lambda profile:{'code':'VPN-001','dns_ok':False,'https_success':0} if profile['id']==SOURCE else {'code':None,'dns_ok':True,'https_success':2}
        self.assertTrue(pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{}))
        self.assertEqual(self.current,['s','t']);self.probe.assert_not_called()
        with patch('pair_manual.time.time',return_value=NOW+61),patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}), \
                patch('failover_plan.streak',return_value=True),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}):
            self.assertTrue(pair.tick(self.backend,self.settings,self.revision))
        self.assertEqual(self.current,['t','s']);self.assertEqual(n.journal_read()['phase'],'COMMITTED')
        self.assertEqual(self.probe.call_args.args[0]['id'],TARGET)

    def test_supervisor_reapply_requires_live_on_intent(self):
        pair.stop_locked(self.revision)
        with self.assertRaisesRegex(n.Refused,'CLIENT-STOP'):
            pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{})
        self.spawn.assert_not_called();self.backend.apply.assert_not_called()

    def test_supervisor_reapply_never_overwrites_foreign_rules_or_resets_budget(self):
        self.backend.attest_policy.side_effect=lambda *args:{'verified':False,'repairable_missing':False}
        self.assertTrue(pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{}))
        self.spawn.assert_not_called();self.assertFalse((self.persist/'pair-auto-budget.json').exists())
        self.backend.attest_policy.side_effect=self.kernel_proof
        events=[NOW-30,NOW-20,NOW-10];agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':events})
        self.assertTrue(pair.reapply_missing_policy(self.backend,pair.read_state(),self.settings,self.revision,{}))
        self.spawn.assert_not_called();self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],events)


if __name__=='__main__':unittest.main()
