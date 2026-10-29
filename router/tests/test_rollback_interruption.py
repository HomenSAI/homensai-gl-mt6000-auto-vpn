"""Interrupted own UCI/RTP restoration, strict proof reuse and refusal cases."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import auto_control
import native_switch as native
import pair_auto as pair
import test_pair_manual_directions as fixture


class InterruptedRollback(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PairManualDirections();self.case.setUp();self.addCleanup(self.case.doCleanups)
        case=self.case;case.kernel_applied=True;case.backend.guard_exists.return_value=True
        for role,device,mark,table,index in (('source','wgclient1',4096,'1001',10),('target','tun0',40960,'1011',11)):
            case.selection[role]['kernel_binding']={'code':None,'device':device,'mark':mark,'table':table,'ifindex':index}
        from failure_diagnosis import profile_identity
        case.selection['vendor_identity']=native.digest({role:{'profile':profile_identity(case.selection[role]),'kernel':case.selection[role]['kernel_binding']}
                                                        for role in ('source','target')})
        case.enterContext(patch.object(pair,'network',return_value=[]));case.enterContext(patch.object(pair,'configs',return_value={}))
        self.journal=case.request('primary')

    def fail_before_rtp(self):
        case=self.case
        case.backend.apply.side_effect=native.Refused('VENDOR-APPLY-FAILED')
        with self.assertRaisesRegex(native.Refused,'VENDOR-APPLY-FAILED'):
            native.rollback(case.backend,self.journal,'PAIR-STOPPED',restore_order=case.state['order'])
        self.assertEqual(case.current,['t','s']);self.assertEqual(case.kernel_order,['s','t'])
        self.assertEqual(native.journal_read()['phase'],'RESTORING')
        self.recovery_revision=auto_control.current_revision(rotate=True);pair.stop_locked(self.recovery_revision)
        case.backend.apply.reset_mock();case.backend.reorder.reset_mock()
        case.backend.apply.side_effect=case.apply

    def refuse_retry(self):
        before=native.JOURNAL.read_bytes()
        with self.assertRaises(native.Refused):
            native.rollback(self.case.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
        self.case.backend.apply.assert_not_called();self.case.backend.reorder.assert_not_called()
        self.assertEqual(native.JOURNAL.read_bytes(),before)

    def test_retry_restores_same_owned_kernel_after_apply_failed_before_rtp(self):
        self.fail_before_rtp();case=self.case
        budget=(case.persist/'pair-auto-budget.json').read_bytes()
        calls=[]
        def dispatch(args,revision,timeout=5):
            native.require_control_revision(revision);calls.append((args,revision));return b''
        def apply(**kwargs):
            kwargs['write_command'](['/usr/bin/rtp2.sh','not_reload_network'],timeout=45)
            case.apply(**kwargs)
        case.backend.apply.side_effect=apply
        with patch.object(native,'forward_dispatch',side_effect=dispatch):
            native.rollback(case.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
        result=native.journal_read()
        self.assertEqual(result['phase'],'ROLLED-BACK');self.assertEqual(result['restored_order'],case.state['order'])
        self.assertTrue(case.kernel_proof()['verified']);self.assertEqual(case.kernel_order,case.state['order'])
        self.assertEqual(calls,[(['/usr/bin/rtp2.sh','not_reload_network'],self.recovery_revision)])
        self.assertEqual(pair.intent()['mode'],'off');self.assertEqual((case.persist/'pair-auto-budget.json').read_bytes(),budget)

    def test_durable_proof_precedes_every_restore_order_write(self):
        case=self.case;reorder=case.reorder
        def checked(order,**kwargs):
            saved=native.journal_read()
            self.assertEqual(saved['phase'],'RESTORING');self.assertEqual(saved['restore_before_order'],['s','t'])
            self.assertEqual(saved['restore_target_order'],['t','s'])
            self.assertEqual(saved['restore_kernel_fingerprint'],case.kernel_proof()['kernel_fingerprint'])
            return reorder(order,**kwargs)
        case.backend.reorder.side_effect=checked
        native.rollback(case.backend,self.journal,'PAIR-STOPPED',restore_order=case.state['order'])

    def test_failed_checkpoint_write_does_not_touch_policy_or_kernel(self):
        case=self.case;case.backend.apply.reset_mock();case.backend.reorder.reset_mock()
        before=native.JOURNAL.read_bytes();write=native.journal_write
        def failed(row):
            if row.get('phase')=='RESTORING':raise OSError('simulated storage failure')
            return write(row)
        with patch.object(native,'journal_write',side_effect=failed),self.assertRaises(OSError):
            native.rollback(case.backend,self.journal,'PAIR-STOPPED',restore_order=case.state['order'])
        self.assertEqual(native.JOURNAL.read_bytes(),before)
        case.backend.apply.assert_not_called();case.backend.reorder.assert_not_called()

    def test_missing_legacy_or_unverified_checkpoint_is_never_reconstructed(self):
        self.fail_before_rtp();saved=native.journal_read()
        for mode in ('missing','unverified'):
            row=copy.deepcopy(saved)
            if mode=='missing':row.pop('restore_kernel_fingerprint')
            else:row['restore_before_verified']=False
            native.journal_write(row)
            with self.subTest(mode=mode):self.refuse_retry()

    def test_malformed_checkpoint_cannot_replace_last_readable_journal(self):
        self.fail_before_rtp();before=native.JOURNAL.read_bytes()
        for value in (None,True,[],{},'x'*64,'f'*63):
            row=native.journal_read();row['restore_kernel_fingerprint']=value
            with self.subTest(value=value),self.assertRaisesRegex(native.Refused,'JOURNAL-INTEGRITY-FAILED'):
                native.journal_write(row)
            self.assertEqual(native.JOURNAL.read_bytes(),before)

    def test_lost_owned_guard_refuses_without_recreating_it(self):
        self.fail_before_rtp();self.case.backend.guard_exists.return_value=False
        self.case.backend.guard.reset_mock();self.refuse_retry();self.case.backend.guard.assert_not_called()

    def test_changed_kernel_fingerprint_never_reaches_restore_apply(self):
        self.fail_before_rtp();self.case.backend.kernel_fingerprint.side_effect=lambda:'f'*64
        self.refuse_retry()

    def test_changed_vendor_identity_or_profile_epoch_refuses(self):
        self.fail_before_rtp();case=self.case
        original=copy.deepcopy(case.selection)
        for change in ('identity','source-generation','target-generation'):
            case.selection=copy.deepcopy(original)
            if change=='identity':case.selection['vendor_identity']='f'*64
            else:case.selection[change.split('-')[0]]['vendor_generation']='f'*32
            with self.subTest(change=change):self.refuse_retry()

    def test_missing_or_changed_route_bindings_on_either_tunnel_refuse(self):
        self.fail_before_rtp();case=self.case;original=copy.deepcopy(case.selection)
        for role in ('source','target'):
            for change in ('missing','route-error','no-ifindex','no-mark','changed-mark','changed-table','changed-device'):
                case.selection=copy.deepcopy(original)
                if change=='missing':case.selection[role].pop('kernel_binding')
                elif change=='route-error':case.selection[role]['kernel_binding']['code']='ROUTE-001'
                elif change=='no-ifindex':case.selection[role]['kernel_binding']['ifindex']=None
                elif change=='no-mark':case.selection[role]['kernel_binding']['mark']=0
                elif change=='changed-mark':case.selection[role]['kernel_binding']['mark']=8192
                elif change=='changed-table':case.selection[role]['kernel_binding']['table']='8888'
                else:case.selection[role]['kernel_binding']['device']='eth0'
                with self.subTest(role=role,change=change):self.refuse_retry()

    def test_live_diagnostic_failure_blocks_even_unchanged_mangle_and_rules(self):
        self.fail_before_rtp();self.case.backend.diagnostic.side_effect=lambda:(['PROFILE-IDENTITY-CHANGED'],None)
        self.refuse_retry()

    def test_actual_route_binding_rejects_missing_default_and_wrong_marked_path(self):
        self.fail_before_rtp();case=self.case;diagnostic=case.backend.diagnostic.side_effect
        devices={'wgclient1':('wgclient1',4096,'1001',10),'ovpnclient1':('tun0',40960,'1011',11)}
        bad=[None,None];read_text=Path.read_text
        def command(args):
            if args[0]=='ubus':
                logical=args[2].split('.')[-1]
                return json.dumps({'up':True,'l3_device':devices[logical][0]}).encode()
            if args[:5]==['ip','-4','-j','route','show']:
                return json.dumps([{'dev':device,'dst':'default','table':table}
                                   for logical,(device,mark,table,index) in devices.items()
                                   if not (bad==[logical,'missing-default'])]).encode()
            if args[:5]==['ip','-4','-j','rule','show']:
                return json.dumps([{'fwmark':hex(mark),'table':table} for device,mark,table,index in devices.values()]).encode()
            if args[:5]==['ip','-4','-j','route','get']:
                logical=next(key for key,value in devices.items() if value[1]==int(args[-1]))
                device,mark,table,index=devices[logical]
                return json.dumps([{'dev':'eth0' if bad==[logical,'wrong-marked-path'] else device,'table':table}]).encode()
            raise AssertionError(args)
        def ifindex(path,*args,**kwargs):
            for device,mark,table,index in devices.values():
                if str(path)=='/sys/class/net/'+device+'/ifindex':return str(index)
            return read_text(path,*args,**kwargs)
        def fresh_diagnostic():
            blockers,selection=diagnostic()
            for role in ('source','target'):
                selection[role]['kernel_binding']=agent.route_binding(selection[role]['interface'])
            return blockers,selection
        case.backend.diagnostic.side_effect=fresh_diagnostic
        with patch.object(agent,'command',side_effect=command),patch.object(Path,'read_text',ifindex):
            for logical in devices:
                for failure in ('missing-default','wrong-marked-path'):
                    bad[:]=[logical,failure]
                    with self.subTest(logical=logical,failure=failure):self.refuse_retry()

    def test_wrong_pair_id_or_owning_revision_refuses(self):
        self.fail_before_rtp();original=pair.read_state()
        for key in ('id','revision'):
            state=copy.deepcopy(original);state[key]='f'*32;pair.save(state)
            with self.subTest(key=key):self.refuse_retry()

    def test_newer_transaction_cannot_be_overwritten_by_stale_recovery(self):
        self.fail_before_rtp();old=native.journal_read();replacement=copy.deepcopy(old)
        replacement['tx']='f'*32;native.journal_write(replacement);before=native.JOURNAL.read_bytes()
        with self.assertRaises(native.Refused):native.rollback(self.case.backend,old,'SUPERVISOR-RECOVERY')
        self.assertEqual(native.JOURNAL.read_bytes(),before);self.case.backend.apply.assert_not_called()

    def test_stop_during_live_revalidation_fences_restore_dispatch(self):
        self.fail_before_rtp();diagnostic=self.case.backend.diagnostic.side_effect
        def stopped():
            result=diagnostic();auto_control.current_revision(rotate=True);return result
        self.case.backend.diagnostic.side_effect=stopped
        self.refuse_retry()

    def test_on_intent_never_authorizes_recovery_reapply(self):
        self.fail_before_rtp();state=pair.read_state()
        agent.atomic_json(pair.paths()[0],{'mode':'on','id':state['id'],'revision':self.recovery_revision,'time':fixture.NOW})
        self.refuse_retry()

    def test_successful_command_without_restored_kernel_does_not_close_journal(self):
        self.fail_before_rtp();self.case.backend.apply.side_effect=None
        with self.assertRaisesRegex(native.Refused,'ROLLBACK-UNVERIFIED'):
            native.rollback(self.case.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(native.journal_read()['phase'],'RESTORING')
        self.assertEqual(pair.intent()['mode'],'off')

    def test_already_restored_kernel_still_requires_final_attestation(self):
        self.fail_before_rtp();self.case.kernel_order=list(self.case.current)
        native.rollback(self.case.backend,native.journal_read(),'SUPERVISOR-RECOVERY')
        self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        self.assertTrue(self.case.kernel_proof()['verified'])


if __name__=='__main__':unittest.main()
