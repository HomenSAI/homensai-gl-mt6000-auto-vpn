"""Interrupted multi-move rollback with actual Linux order/hash and Lua UCI.

The third generic rule makes the selected pair nonadjacent. UCI delta state
is modelled separately from commit, and the compiled mark graph stays intact
until the simulated vendor compiler runs.
"""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,pair_policy
import pair_manual as manual
from failure_diagnosis import profile_identity
import test_pair_manual_bound_context as platform


class WorkerKilled(BaseException):pass


@unittest.skipUnless(platform.LUA,'Actual Lua 5.1 runtime required')
class RestoreOrderSteps(unittest.TestCase):
    def setUp(self):
        self.case=platform.BoundManualContext();self.case.setUp();self.addCleanup(self.case.doCleanups)
        case=self.case
        case.enter(patch.object(platform,'PRELUDE',platform.PRELUDE.replace(
            'function c:changes()return {}end','function c:changes()return FIXTURE.pending or {}end')))
        case.data['sections'].insert(-1,{'.name':'middle','.type':'rule','enabled':'1','killswitch':'1',
                                        'via':'wgclient2','mark':'0x2000','tunnel_id':'7777'})
        case.mangle=case.mangle.replace(':TUNNEL4192_ROUTE_POLICY - [0:0]',
            ':TUNNEL4192_ROUTE_POLICY - [0:0]\n:TUNNEL7777_ROUTE_POLICY - [0:0]')
        case.mangle=case.mangle.replace('COMMIT',
            '-A TUNNEL7777_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x2000/0xf000\n'
            '-A TUNNEL7777_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP\nCOMMIT')
        case.ip_rules.append({'priority':6000,'src':'all','fwmark':'0x2000','fwmask':'0xf000','table':'1002'})
        case.compiled=copy.deepcopy(case.data['sections'])
        original_write=case.write
        def write(args):
            result=original_write(args)
            if args[:2]==['uci','reorder']:case.data['pending']={'route_policy':{'reorder':True}}
            elif args[:3]==['uci','commit','route_policy']:case.data.pop('pending',None)
            return result
        case.enter(patch.object(case,'write',side_effect=write))
        base_diagnostic=case.diagnostic_method()
        def diagnostic(backend):
            blockers,selection=base_diagnostic(backend)
            selection['vendor_identity']=n.digest({role:{'profile':profile_identity(selection[role]),
                'kernel':selection[role]['kernel_binding']} for role in ('source','target')})
            return blockers,selection
        case.enter(patch.object(n.Linux,'diagnostic',diagnostic))
        self.guard=case.enter(patch.object(n.Linux,'guard_exists',return_value=True))
        case.enter(patch.object(pair,'configs',return_value={}))
        self.backend=n.Linux();self.backend.use_process_bindings(case.bindings)
        blockers,case.selection=self.backend.diagnostic();self.assertEqual(blockers,[])
        identity=pair_policy.proof(case.selection)
        self.before=list(case.selection['order'])
        self.target=pair_policy.desired_order(identity,self.before,'target')
        case.state.update(order=self.target,policy_hash=case.selection['hash'],policy_roles=identity)
        pair.save(case.state)
        case.journal.update(before=self.target,after=self.before,hash=case.selection['hash'],
            vendor_identity=case.selection['vendor_identity'],vendor_profiles={role:profile_identity(case.selection[role]) for role in ('source','target')},
            pair_transition=pair_policy.transition(dict(case.selection,order=self.target),self.target,'source'))
        n.journal_write(case.journal)
        self.assertTrue(self.backend.attest_policy()['verified'])
        self.fingerprint=self.backend.kernel_fingerprint()
        self.ledger={'events':[platform.NOW-40]}
        agent.atomic_json(case.persist/'pair-auto-budget.json',self.ledger)

    def interrupted(self,after_moves=1):
        command=self.case.command;moves=[]
        def killed(args,timeout=5):
            result=command(args,timeout)
            if args[:2]==['uci','reorder']:
                moves.append(list(args))
                if len(moves)==after_moves:raise WorkerKilled()
            return result
        with patch.object(n,'command',side_effect=killed),self.assertRaises(WorkerKilled):
            n.rollback(self.backend,n.journal_read(),'PAIR-STOPPED',restore_order=self.target)
        self.assertEqual(n.journal_read()['phase'],'RESTORING')
        self.assertEqual(self.backend.kernel_fingerprint(),self.fingerprint)
        self.assertEqual(len(moves),after_moves)
        self.assertTrue(self.case.data.get('pending'))
        self.revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.revision)
        self.case.commands.clear()

    def refuse_retry(self):
        before=n.JOURNAL.read_bytes();order=self.backend.order();kernel=self.backend.kernel_fingerprint()
        ledger=agent.read_json(self.case.persist/'pair-auto-budget.json')
        with self.assertRaises(n.Refused):n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.case.commands,[])
        self.assertEqual(n.JOURNAL.read_bytes(),before)
        self.assertEqual(self.backend.order(),order);self.assertEqual(self.backend.kernel_fingerprint(),kernel)
        self.assertEqual(agent.read_json(self.case.persist/'pair-auto-budget.json'),ledger)

    def test_restart_resumes_only_remaining_move_after_first_move_crash(self):
        self.interrupted()
        live=self.backend.order()[0]
        self.assertNotIn(live,(self.before,self.target))
        self.assertFalse(self.backend.attest_policy()['verified'])
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.backend.order()[0],self.target)
        self.assertTrue(self.backend.attest_policy()['verified'])
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')
        self.assertEqual(n.journal_read()['restored_order'],self.target)
        self.assertEqual(pair.intent()['mode'],'off')
        self.assertEqual(sum(args[:2]==['uci','reorder'] for args in self.case.commands),1)
        self.assertEqual(sum(args[:3]==['uci','commit','route_policy'] for args in self.case.commands),1)
        self.assertEqual(sum(args[0]=='/usr/bin/rtp2.sh' for args in self.case.commands),1)
        self.assertFalse(self.case.data.get('pending'))
        self.assertEqual(agent.read_json(self.case.persist/'pair-auto-budget.json'),self.ledger)

    def test_last_move_crash_commits_owned_delta_before_applying(self):
        self.interrupted(after_moves=2)
        self.assertEqual(self.backend.order()[0],self.target)
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.case.commands[0],['uci','commit','route_policy'])
        self.assertFalse(any(args[:2]==['uci','reorder'] for args in self.case.commands))
        self.assertTrue(self.backend.attest_policy()['verified'])
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')

    def test_checkpoint_is_durable_before_first_move_and_crash_before_write_recovers(self):
        command=self.case.command
        def killed(args,timeout=5):
            if args[:2]==['uci','reorder']:
                saved=n.journal_read();step=saved['restore_order_step']
                self.assertEqual(step['before'],self.backend.order()[0])
                self.assertEqual(saved['restore_kernel_fingerprint'],self.fingerprint)
                self.assertTrue(saved['restore_before_verified']);raise WorkerKilled()
            return command(args,timeout)
        with patch.object(n,'command',side_effect=killed),self.assertRaises(WorkerKilled):
            n.rollback(self.backend,n.journal_read(),'PAIR-STOPPED',restore_order=self.target)
        self.assertEqual(self.backend.order()[0],self.before);self.assertEqual(self.case.commands,[])
        revision=auto_control.current_revision(rotate=True);pair.stop_locked(revision)
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertTrue(self.backend.attest_policy()['verified'])

    def test_crash_after_commit_retries_only_proven_commit_and_finishes(self):
        command=self.case.command
        def killed(args,timeout=5):
            result=command(args,timeout)
            if args==['uci','commit','route_policy']:raise WorkerKilled()
            return result
        with patch.object(n,'command',side_effect=killed),self.assertRaises(WorkerKilled):
            n.rollback(self.backend,n.journal_read(),'PAIR-STOPPED',restore_order=self.target)
        self.assertEqual(n.journal_read()['restore_order_step']['kind'],'commit')
        self.assertFalse(self.case.data.get('pending'))
        revision=auto_control.current_revision(rotate=True);pair.stop_locked(revision);self.case.commands.clear()
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.case.commands[0],['uci','commit','route_policy'])
        self.assertFalse(any(args[:2]==['uci','reorder'] for args in self.case.commands))
        self.assertEqual(sum(args[0]=='/usr/bin/rtp2.sh' for args in self.case.commands),1)
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertEqual(pair.intent()['mode'],'off')

    def test_malformed_or_noncanonical_step_cannot_replace_readable_journal(self):
        self.interrupted();original=n.journal_read();before=n.JOURNAL.read_bytes();valid=original['restore_order_step']
        invalid=[None,{},dict(valid,version=True),dict(valid,version=2),dict(valid,kind='apply'),
                 dict(valid,index=True),dict(valid,index=-1),dict(valid,index=400),dict(valid,section='middle'),
                 dict(valid,after=valid['before']),dict(valid,before=valid['after']),dict(valid,extra=True),
                 {'version':1,'kind':'commit','before':valid['after'],'after':valid['after']}]
        for step in invalid:
            with self.subTest(step=step),self.assertRaisesRegex(n.Refused,'JOURNAL-INTEGRITY-FAILED'):
                n.journal_write(dict(original,restore_order_step=step))
            self.assertEqual(n.JOURNAL.read_bytes(),before)
        self.assertEqual(self.case.commands,[])

    def test_missing_legacy_step_does_not_authorize_intermediate_order(self):
        self.interrupted();row=n.journal_read();row.pop('restore_order_step');n.journal_write(row)
        self.refuse_retry();self.assertNotIn('restore_order_step',n.journal_read())

    def test_step_without_original_verified_fingerprint_is_invalid(self):
        self.interrupted();original=n.journal_read();before=n.JOURNAL.read_bytes()
        for mode in ('missing-fingerprint','unverified','foreign-before'):
            row=copy.deepcopy(original)
            if mode=='missing-fingerprint':row.pop('restore_kernel_fingerprint')
            elif mode=='unverified':row['restore_before_verified']=False
            else:row['restore_before_order']=row['restore_order_step']['after']
            with self.subTest(mode=mode),self.assertRaisesRegex(n.Refused,'JOURNAL-INTEGRITY-FAILED'):n.journal_write(row)
            self.assertEqual(n.JOURNAL.read_bytes(),before)

    def test_later_unrecorded_order_is_not_authorized_by_old_step(self):
        self.interrupted();rows={n.section_id(row,self.case.bindings):row for row in self.case.data['sections']}
        self.case.data['sections']=[rows[key] for key in self.target]
        self.refuse_retry()

    def test_rewound_verified_order_outside_latest_step_still_refuses(self):
        self.interrupted(after_moves=2);rows={n.section_id(row,self.case.bindings):row for row in self.case.data['sections']}
        self.case.data['sections']=[rows[key] for key in self.before]
        self.assertTrue(self.backend.attest_policy()['verified']);self.refuse_retry()

    def test_foreign_non_order_uci_change_refuses_without_commit(self):
        self.interrupted();self.case.data['sections'][3]['foreign_option']='1'
        self.refuse_retry()

    def test_foreign_kernel_rule_mask_or_order_refuses_before_remaining_move(self):
        self.interrupted();rules=copy.deepcopy(self.case.ip_rules)
        for mode in ('mask','order'):
            self.case.ip_rules=copy.deepcopy(rules)
            if mode=='mask':self.case.ip_rules[-1]['fwmask']='0xff00'
            else:self.case.ip_rules[-1]['priority']=3000
            with self.subTest(mode=mode):self.refuse_retry()

    def test_failed_next_step_checkpoint_never_executes_that_move(self):
        self.interrupted();original=n.journal_read();before=n.JOURNAL.read_bytes();write=n.journal_write
        def failed(row):
            if row.get('restore_order_step')!=original['restore_order_step']:raise OSError('checkpoint failed')
            return write(row)
        with patch.object(n,'journal_write',side_effect=failed),self.assertRaises(OSError):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(n.JOURNAL.read_bytes(),before);self.assertEqual(self.case.commands,[])
        self.assertEqual(self.backend.order()[0],original['restore_order_step']['after'])

    def test_failed_commit_checkpoint_leaves_last_move_recoverable(self):
        self.interrupted();write=n.journal_write
        def failed(row):
            if row.get('restore_order_step',{}).get('kind')=='commit':raise OSError('checkpoint failed')
            return write(row)
        with patch.object(n,'journal_write',side_effect=failed),self.assertRaises(OSError):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(len(self.case.commands),1);self.assertEqual(self.case.commands[0][:2],['uci','reorder'])
        self.assertEqual(n.journal_read()['restore_order_step']['kind'],'reorder')
        self.assertEqual(self.backend.order()[0],self.target);self.assertTrue(self.case.data.get('pending'))
        self.case.commands.clear();n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.case.commands[0],['uci','commit','route_policy'])
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')

    def test_stop_guard_or_journal_change_after_checkpoint_fences_the_write(self):
        self.interrupted();original=n.journal_read();write=n.journal_write
        original_state=pair.read_state();original_intent=pair.intent()
        for mode in ('revision','guard','journal','policy'):
            n.journal_write(copy.deepcopy(original));self.guard.return_value=True
            agent.atomic_json(self.case.runtime/'auto-control-revision.json',{'revision':self.revision})
            pair.save(copy.deepcopy(original_state));agent.atomic_json(pair.paths()[0],copy.deepcopy(original_intent))
            for row in self.case.data['sections']:row.pop('foreign_option',None)
            changed=[False]
            def raced(row):
                result=write(row)
                if not changed[0] and row.get('restore_order_step')!=original['restore_order_step']:
                    changed[0]=True
                    if mode=='revision':auto_control.current_revision(rotate=True)
                    elif mode=='guard':self.guard.return_value=False
                    elif mode=='journal':write(dict(row,tx='f'*32))
                    else:self.case.data['sections'][3]['foreign_option']='1'
                return result
            with self.subTest(mode=mode),patch.object(n,'journal_write',side_effect=raced),self.assertRaises(n.Refused):
                n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
            self.assertTrue(changed[0]);self.assertEqual(self.case.commands,[])
            self.assertEqual(self.backend.kernel_fingerprint(),self.fingerprint)
            self.assertEqual(n.journal_read()['phase'],'RESTORING')

    def failed_forward(self):
        writer=self.case.write;failed=[False]
        def fail_rtp(args):
            if args[0]=='/usr/bin/rtp2.sh' and not failed[0]:
                failed[0]=True;raise n.Refused('VENDOR-APPLY-FAILED')
            return writer(args)
        agent.atomic_json(self.case.persist/'pair-auto-budget.json',{'events':[]})
        self.assertTrue(manual.request('reserve',self.case.revision)['accepted'])
        with patch.object(self.case,'write',side_effect=fail_rtp):
            manual.consume(self.backend,pair.read_state(),self.case.data['settings'],self.case.revision)
        self.assertTrue(failed[0]);saved=n.journal_read()
        self.assertEqual(saved['phase'],'APPLYING');self.assertTrue(saved['rtp_dispatched'])
        self.assertTrue(saved['kernel_before_verified']);self.assertEqual(saved['kernel_before_fingerprint'],self.fingerprint)
        self.assertEqual(self.backend.order()[0],saved['after']);self.assertEqual(self.backend.kernel_fingerprint(),self.fingerprint)
        self.assertFalse(self.backend.attest_policy()['verified'])
        self.revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.revision)
        self.case.commands.clear();return saved

    def test_failed_forward_rtp_reuses_original_verified_proof_after_stop(self):
        saved=self.failed_forward();ledger=agent.read_json(self.case.persist/'pair-auto-budget.json')
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')
        self.assertEqual(self.backend.order()[0],saved['before']);self.assertTrue(self.backend.attest_policy()['verified'])
        fields=n.pair_event_fields(n.journal_read(),completed=True,outcome='restored',restoring=True)
        self.assertEqual(fields['from_role'],'source');self.assertEqual(fields['destination_role'],'source')
        self.assertFalse(fields['route_changed']);self.assertEqual(pair.intent()['mode'],'off')
        self.assertEqual(agent.read_json(self.case.persist/'pair-auto-budget.json'),ledger)

    def interrupted_forward_recovery(self,after_moves):
        original=self.failed_forward();moves=[];writer=self.case.write;write=n.journal_write
        def killed(args):
            result=writer(args)
            if args[:2]==['uci','reorder']:
                moves.append(args)
                if len(moves)==after_moves:raise WorkerKilled()
            return result
        def checkpoint(row):
            result=write(row)
            if after_moves==0 and row.get('restore_proof_source')=='forward':raise WorkerKilled()
            return result
        with patch.object(self.case,'write',side_effect=killed),patch.object(n,'journal_write',side_effect=checkpoint),self.assertRaises(WorkerKilled):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(len(moves),after_moves);saved=n.journal_read()
        self.assertEqual(saved['phase'],'RESTORING');self.assertEqual(saved['restore_proof_source'],'forward')
        self.assertEqual(saved['restore_order_origin'],original['after']);self.assertEqual(saved['restore_before_order'],original['before'])
        self.assertEqual(saved['restore_kernel_fingerprint'],original['kernel_before_fingerprint'])
        self.assertEqual(self.backend.kernel_fingerprint(),self.fingerprint)
        self.case.commands.clear();return original

    def test_forward_promotion_crash_before_first_write_resumes_exact_plan(self):
        original=self.interrupted_forward_recovery(0)
        self.assertEqual(self.backend.order()[0],original['after'])
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.backend.order()[0],original['before'])
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertTrue(self.backend.attest_policy()['verified'])
        self.assertEqual(sum(args[:2]==['uci','reorder'] for args in self.case.commands),2)

    def test_forward_recovery_last_move_crash_keeps_checkpoint_even_when_kernel_verified(self):
        original=self.interrupted_forward_recovery(2);ledger=agent.read_json(self.case.persist/'pair-auto-budget.json')
        self.assertEqual(self.backend.order()[0],original['before']);self.assertTrue(self.backend.attest_policy()['verified'])
        self.assertTrue(self.case.data.get('pending'))
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(self.case.commands[0],['uci','commit','route_policy'])
        self.assertFalse(any(args[:2]==['uci','reorder'] for args in self.case.commands))
        self.assertFalse(self.case.data.get('pending'));self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK')
        self.assertTrue(self.backend.attest_policy()['verified']);self.assertEqual(pair.intent()['mode'],'off')
        fields=n.pair_event_fields(n.journal_read(),completed=True,outcome='restored',restoring=True)
        self.assertEqual(fields['from_role'],'source');self.assertEqual(fields['destination_role'],'source');self.assertFalse(fields['route_changed'])
        self.assertEqual(agent.read_json(self.case.persist/'pair-auto-budget.json'),ledger)

    def test_missing_changed_or_unverified_forward_proof_never_promotes(self):
        original=self.failed_forward()
        variants=[dict(original,kernel_before_verified=False),dict(original,kernel_before_fingerprint='f'*64),
                  dict(original,forward_policy_touched=False),dict(original,confirmed=platform.NOW),
                  dict(original,kernel_confirmed=platform.NOW),dict(original,phase='COMMITTED'),
                  dict(original,restore_before_order=original['before'])]
        missing=copy.deepcopy(original);missing.pop('kernel_before_fingerprint');variants.append(missing)
        missing=copy.deepcopy(original);missing.pop('rtp_dispatched');variants.append(missing)
        for index,row in enumerate(variants):
            n.journal_write(row)
            with self.subTest(variant=index):self.refuse_retry()
            self.assertNotIn('restore_proof_source',n.journal_read())

    def test_promoted_proof_origin_and_original_flags_cannot_be_replaced(self):
        self.interrupted_forward_recovery(0);original=n.journal_read();before=n.JOURNAL.read_bytes()
        variants=[dict(original,restore_proof_source='legacy'),dict(original,restore_order_origin=original['before']),
                  dict(original,restore_before_order=original['after']),dict(original,restore_target_order=original['after']),
                  dict(original,kernel_before_verified=False),dict(original,restore_before_verified=False),
                  dict(original,rtp_dispatched=False),dict(original,forward_policy_touched=False),
                  dict(original,confirmed=platform.NOW),dict(original,kernel_confirmed=platform.NOW),
                  dict(original,kernel_before_fingerprint='f'*64)]
        for key in ('restore_proof_source','restore_order_origin','restore_order_step','kernel_before_fingerprint'):
            missing=copy.deepcopy(original);missing.pop(key);variants.append(missing)
        for index,row in enumerate(variants):
            with self.subTest(variant=index),self.assertRaises(n.Refused):n.journal_write(row)
            self.assertEqual(n.JOURNAL.read_bytes(),before)
        self.assertEqual(self.case.commands,[])

    def test_forward_proof_never_promotes_with_on_intent_missing_guard_or_changed_binding(self):
        self.failed_forward();original_intent=pair.intent();profiles=copy.deepcopy(self.case.profiles)
        for mode in ('on','guard','binding','foreign-kernel'):
            agent.atomic_json(pair.paths()[0],dict(original_intent,mode='on' if mode=='on' else 'off'))
            self.guard.return_value=mode!='guard';self.case.profiles=copy.deepcopy(profiles)
            mangle=self.case.mangle
            if mode=='binding':self.case.profiles[0]['vendor_generation']='f'*32
            if mode=='foreign-kernel':self.case.mangle=mangle.replace('--set-xmark 0x1000/0xf000','--set-xmark 0x3000/0xf000')
            with self.subTest(mode=mode):self.refuse_retry()
            self.case.mangle=mangle
            self.assertNotIn('restore_proof_source',n.journal_read())

    def test_forward_promotion_refuses_protected_firewall_or_credential_drift(self):
        # A partially rewritten vendor firewall (e.g. one gl_vpn_rules forwarding
        # missing after an interrupted rtp2.sh) is not provably ours: no promotion.
        self.failed_forward();state=pair.read_state()
        for name in ('firewall','wireguard'):
            pair.save(dict(state,protected={name:'a'*64}))
            with self.subTest(config=name),patch.object(pair,'configs',return_value={name:'b'*64}),\
                    patch.object(pair,'firewall_bytes',return_value=b"config forwarding 'foreign'\n"):
                self.refuse_retry()
            self.assertNotIn('restore_proof_source',n.journal_read())
        pair.save(state)

    def test_failed_forward_promotion_write_changes_neither_policy_nor_journal(self):
        self.failed_forward();before=n.JOURNAL.read_bytes();write=n.journal_write
        def failed(row):
            if row.get('restore_proof_source')=='forward':raise OSError('checkpoint failed')
            return write(row)
        with patch.object(n,'journal_write',side_effect=failed),self.assertRaises(OSError):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(n.JOURNAL.read_bytes(),before);self.assertEqual(self.case.commands,[])

    def test_stop_during_forward_double_read_prevents_promotion(self):
        self.failed_forward();diagnostic=self.backend.diagnostic;count=[0]
        def stopped():
            result=diagnostic();count[0]+=1
            if count[0]==3:auto_control.current_revision(rotate=True)
            return result
        with patch.object(self.backend,'diagnostic',side_effect=stopped):self.refuse_retry()
        self.assertGreaterEqual(count[0],3);self.assertNotIn('restore_proof_source',n.journal_read())

    def test_completed_restore_crash_uses_fresh_actual_target_attestation(self):
        self.interrupted();dispatch=n.forward_dispatch
        def killed(args,revision,timeout=5):
            result=dispatch(args,revision,timeout)
            if args[0]=='/usr/bin/rtp2.sh':raise WorkerKilled()
            return result
        with patch.object(n,'forward_dispatch',side_effect=killed),self.assertRaises(WorkerKilled):
            n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertTrue(n.journal_read()['restore_rtp_dispatched']);self.assertTrue(self.backend.attest_policy()['verified'])
        self.assertEqual(n.journal_read()['phase'],'RESTORING');self.case.commands.clear()
        n.rollback(self.backend,n.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(n.journal_read()['phase'],'ROLLED-BACK');self.assertTrue(self.backend.attest_policy()['verified'])


if __name__=='__main__':unittest.main()
