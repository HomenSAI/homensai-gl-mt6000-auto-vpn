"""forward_resume.py (03.11.2026), Python line. Lua counterpart: tests/lua/test_forward_resume.lua.

MT3000 2.1.0-alpha5: the Auto process was SIGKILLed in the middle of an automatic switch to the reserve (APPLYING)
while the primary stayed down; the recovery rolled back onto the dead primary, tore the pair down and rebuilt it, then
switched again: 128 s without internet on the LAN (normal failover ~20 s). Here the real attempt() runs (its apply
child in this process) on the boot-held fixture router and is killed at a chosen point: nothing durable is written
after it, like SIGKILL. Then serve() recovers and the monitor's restart resume presses Start.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import agent
import auto_control
import boot_resume
import forward_resume as fr
import native_switch as native
import pair_auto as pair
import pair_policy
from test_boot_held import Fixture, Router

CASES=json.loads((Path(__file__).resolve().parent/'forward_resume_cases.json').read_text(encoding='utf8'))
NORMAL_BUDGET=20  # the normal automatic failover on the MT3000: ~20 s from the outage to traffic on the reserve


class Killed(BaseException):
    """SIGKILL of the supervisor: never caught by the code under test."""


class LoopReached(BaseException):
    """serve() reached its loop: the recovery is over (the test reads the state there)."""


class Decide(unittest.TestCase):
    def test_every_shared_case_gives_the_same_code_as_in_lua(self):
        self.assertGreaterEqual(len(CASES['cases']),30)
        for case in CASES['cases']:
            with self.subTest(case=case['name']):
                journal=json.loads(json.dumps(CASES['journal']))
                journal.update(case.get('set',{}))
                for key in case.get('unset',[]):journal.pop(key,None)
                facts=dict(CASES['facts'],**case.get('facts',{}))
                self.assertEqual(fr.decide(journal,facts),case['expect'])

    def test_the_live_probes_run_only_when_every_cheaper_check_passed(self):
        probed=[]
        journal=dict(CASES['journal'])
        facts=dict(CASES['facts'],wanted=False,source_health=lambda:probed.append(1) or False,reserve_health=lambda:probed.append(1) or True)
        self.assertEqual(fr.decide(journal,facts),'OWNER-STOP');self.assertEqual(probed,[])
        facts['wanted']=True
        self.assertIsNone(fr.decide(journal,facts));self.assertEqual(len(probed),2)


class ForwardRouter(Router):
    """The boot-held router with a kernel graph: both clients up (a kill, not a boot), the primary failing."""
    def __init__(self,rename=None):
        super().__init__(rename)
        self.up={name:True for name in self.up}
        self.kernel=self.current[:]
        self.hooks={}
        self.health_of={self.selection['source']['id']:False}
        self.selection['vendor_identity']=self.selection.get('vendor_identity') or 'e'*64
        self.selection['proof_scope']='router-probed-ipv4'
    def hook(self,name):
        fn=self.hooks.pop(name,None)
        if fn:fn()
    def health(self,identifier):return self.health_of.get(identifier,True)
    def guard_exists(self):return self.guarded is not None
    def recovery_ready(self,identifier,settings):return self.health(identifier) is True
    def kernel_fingerprint(self):return hashlib.sha256(','.join(self.kernel).encode()).hexdigest()
    def attest_policy(self,selection=None):
        try:role=pair_policy.role(pair_policy.proof(self.selection),self.kernel)
        except (ValueError,TypeError,KeyError):role=None
        return {'verified':role is not None and self.kernel==self.current,'role':role,'kernel_fingerprint':self.kernel_fingerprint(),
                'order':self.kernel[:],'policy_hash':self.fingerprint,'time':time.time()}
    def reorder(self,order,before_write=None,write_command=None):
        self.hook('reorder')
        self.calls.append(('reorder',list(order)))
        # the forward writers (child, resume) pass write_command only; the rollback's recorded steps stay as before
        if write_command and before_write is None:write_command(['uci','reorder','route_policy'])
        self.current=list(order)
    def apply(self,write_command=None):
        self.hook('apply')
        self.calls.append(('apply',))
        if write_command:write_command(['iptables-restore'])
        self.hook('apply-write')
        self.kernel=self.current[:]
        self.hook('applied')


class Crash(Fixture):
    POINT='applied'

    def setUp(self):
        super().setUp()
        self.b=ForwardRouter(self.RENAME)
        self.stack.enter_context(patch.object(native,'Linux',return_value=self.b))
        self.stack.enter_context(patch.object(native.os,'killpg'))
        ids=iter('%032x'%n for n in range(1,1000))  # distinct supervisor tokens and transaction ids
        self.stack.enter_context(patch.object(native.uuid,'uuid4',side_effect=lambda:MagicMock(hex=next(ids))))
        self.uptime=[5000.0]  # a kill long after the boot
        self.stack.enter_context(patch.object(pair,'_uptime',side_effect=lambda:self.uptime[0]))
        for name in ('assess','prepare','ready','recovery_prefix'):self.stack.enter_context(patch('rtp_boot.'+name))
        self.stack.enter_context(patch('rollback_recovery.vendor_settled'))
        self.stack.enter_context(patch.object(native,'trace',side_effect=lambda profile:self.exits[profile['id']]))
        self.exits={self.b.selection['source']['id']:'198.51.100.1',self.b.selection['target']['id']:'203.0.113.5'}
        self.stack.enter_context(patch.object(native,'probe',side_effect=self.probe))
        self.probe_hook=None
        dispatch=native.forward_dispatch
        def forward(args,revision,timeout=5):
            if args[0] in ('uci','iptables-restore','/usr/bin/rtp2.sh'):
                native.require_control_revision(revision);return b''
            return dispatch(args,revision,timeout)
        self.stack.enter_context(patch.object(native,'forward_dispatch',side_effect=forward))
        ubus=native.command
        def command(args,timeout=5):
            if args[0] in ('uci','iptables-restore','/usr/bin/rtp2.sh'):return b''
            return ubus(args,timeout=timeout)
        self.stack.enter_context(patch.object(native,'command',side_effect=command))
        self.stack.enter_context(patch('speed_pause.gate',side_effect=self.loop_reached))
        self.frozen=False
        record=native.record_attempt_failure
        def record_failure(*a,**k):
            if self.frozen:raise Killed()
            return record(*a,**k)
        self.stack.enter_context(patch.object(native,'record_attempt_failure',side_effect=record_failure))
        # the running pair session of the continuous mode (RAM kept: a kill, not a boot)
        sel=self.b.selection
        self.b.data['settings']['native_trial']='a'*32  # pair.configure_lease: the session id is the lease nonce
        self.revision=auto_control.current_revision()
        agent.atomic_json(self.dir/'pair-auto-control.json',{'mode':'on','revision':self.revision,'time':time.time(),'id':'a'*32,'request_source':'manual'})
        native.JOURNAL.unlink()
        state=pair.read_state();state.update(revision=self.revision,order=self.before,policy_hash=self.b.fingerprint,
                                             policy_roles=pair_policy.proof(sel),process_bindings=sel.get('process_bindings'))
        pair.save(state)
        boot_resume.write_token(self.dir);self.old_token=boot_resume.token(self.dir)
        self.crash(self.POINT)

    def probe(self,profile):
        if self.probe_hook:
            hook,self.probe_hook=self.probe_hook,None
            hook()
        return {'code':None,'dns_ok':True,'https_success':2}

    def loop_reached(self,name):raise LoopReached()

    def kill(self):
        self.frozen=True;raise Killed()

    def crash(self,point,manual=False):
        if point=='wait-client':self.probe_hook=self.kill
        else:self.b.hooks[point]=self.kill
        def wait(timeout=None):
            native.child(native.journal_read()['tx'])
            if point=='child-done':self.kill()
            return 0
        process=MagicMock(pid=os.getpid(),returncode=0);process.wait.side_effect=wait;process.poll.return_value=0
        kwargs=dict(probe_evidence={'source_streak_met':True,'reserve_streak_met':True,'required_failures':3,'required_successes':2},
                    control_revision=self.revision,pair_session_order=self.before)
        if manual:kwargs=dict(control_revision=self.revision,pair_session_order=self.before,manual_request_id='ab'*16,request_source='manual',pair_destination='target')
        with patch.object(native.subprocess,'Popen',return_value=process),self.assertRaises(Killed):
            native.attempt(self.b,self.b.selection,time.time()+180,False,**kwargs)
        self.frozen=False;self.b.hooks.clear();self.probe_hook=None
        self.started=native.journal_read()['started']

    def serve(self):
        native.STOP=False
        self.rollbacks=[]
        rollback=native.rollback
        def spy(backend,journal,reason,*a,**k):
            self.rollbacks.append(reason);return rollback(backend,journal,reason,*a,**k)
        with patch.object(native,'rollback',side_effect=spy):
            try:native.serve()
            except LoopReached:pass

    def lan_on_reserve(self):
        try:role=pair_policy.role(pair_policy.proof(self.b.selection),self.b.kernel)
        except ValueError:return False
        return role=='target' and self.b.guarded=='vpn-only'

    def refused_for(self,code):return 'SUPERVISOR-FORWARD: rollback (%s)'%code in self.lines

    def begin(self):
        selection=dict(self.b.selection)
        with patch.object(pair,'preflight',return_value=selection),patch('pair_interfaces.selection',return_value=dict(self.INTERFACES)),\
             patch.object(pair,'require_running'),patch.object(pair,'client_down',side_effect=lambda n:not self.b.up[n]):
            return pair.begin(self.b,self.b.data['settings'],{'id':'c'*32,'revision':auto_control.current_revision()})


class EndToEnd(Crash):
    POINT='applied'  # the MT3000 evidence: the kernel already on the reserve, the supervisor killed while verifying

    def test_killed_while_verifying_the_restart_finishes_forward_and_auto_adopts_the_reserve(self):
        journal=native.journal_read()
        self.assertEqual(journal['phase'],'APPLYING');self.assertEqual(self.b.kernel,journal['after'])
        self.assertFalse(self.lan_on_reserve(),'the LAN is blocked (full guard) while the process is dead')
        restart=time.time()
        self.b.calls.clear()
        confirming=[]  # while the restarted supervisor confirms (WAIT-CLIENT), the LAN already goes out through the reserve
        self.probe_hook=lambda:confirming.append(self.lan_on_reserve())
        self.serve()
        self.assertEqual(confirming,[True],'VPN-only guard and the reserve kernel before the confirmation')
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('COMMITTED',fr.REASON))
        self.assertEqual((journal['forward_resumed']['from_phase'],journal['forward_resumed']['kernel']),('APPLYING','reserve'))
        self.assertEqual(self.rollbacks,[],'no rollback')
        self.assertNotIn(('apply',),self.b.calls,'no kernel write: the reserve graph was proven and kept')
        self.assertTrue(self.lan_on_reserve(),'traffic on the reserve, VPN-only guard')
        self.assertLessEqual(journal['confirmed']-restart,NORMAL_BUDGET)
        self.assertEqual(self.ifdown,[],'no pair teardown');self.assertEqual(self.ifup,[],'no pair rebuild')
        state=pair.read_state()
        self.assertEqual(state['phase'],'STOPPED');self.assertEqual(state['handover']['tx'],journal['tx'])
        self.assertEqual(pair.intent()['mode'],'off','the restarted supervisor never resumes Auto by itself')
        self.assertIn('SUPERVISOR-FORWARD-RESUMED: %s committed on the reserve'%journal['tx'],self.lines)
        # the monitor sees the new supervisor token and presses the owner's Start; the new session adopts the reserve
        boot_resume.watch(self.dir,self.dir,sleep=lambda s:None,handled=self.old_token,rounds=1)
        self.assertEqual(pair.intent()['mode'],'on',json.loads((self.dir/boot_resume.STATE).read_text()))
        state=self.begin()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('COMMITTED','BOOT-RESERVE-ADOPTED'))
        self.assertEqual(journal['boot_adopted']['from_reason'],fr.REASON)
        self.assertEqual(self.ifup,[],'the kept clients adopted, no second ifup');self.assertTrue(self.lan_on_reserve())

    def test_the_finished_switch_ends_the_primary_flows_once_and_a_failing_reset_never_undoes_it(self):
        resets=[]
        def flow_reset(old_id,new_id):
            resets.append((old_id,new_id));raise RuntimeError('conntrack exploded')
        self.b.flow_reset=flow_reset
        self.serve()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('COMMITTED',fr.REASON))
        self.assertEqual(resets,[(journal['source'],journal['target'])])
        self.assertEqual(native.reset_old_flows(self.b,journal,'target'),'FLOW-RESET-FAILED')
        self.assertTrue(self.lan_on_reserve())

    def test_control_without_forward_resume_rolls_back_onto_the_dead_primary_and_tears_the_pair_down(self):
        with patch.object(fr,'attempt',return_value=(False,'DISABLED')):self.serve()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('ROLLED-BACK','SUPERVISOR-RECOVERY'))
        self.assertEqual(self.b.kernel,self.before,'the LAN back on the failed primary');self.assertFalse(self.lan_on_reserve())
        self.assertEqual(sorted(self.ifdown),['ovpnclient1','wgclient1'],'both clients stopped')


class ChildDone(Crash):
    POINT='child-done'
    def test_apply_child_finished_parent_killed_finishes_forward(self):
        self.serve()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason'],journal['forward_resumed']['kernel']),('COMMITTED',fr.REASON,'reserve'))
        self.assertEqual(self.rollbacks,[]);self.assertTrue(self.lan_on_reserve())


class BeforeReorder(Crash):
    POINT='reorder'
    def test_killed_before_any_write_redoes_the_switch_forward(self):
        self.assertEqual(self.b.current,self.before)
        self.serve()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason'],journal['forward_resumed']['kernel']),('COMMITTED',fr.REASON,'untouched'))
        self.assertTrue(journal['rtp_dispatched']);self.assertTrue(journal['forward_policy_touched'])
        self.assertEqual(self.rollbacks,[]);self.assertTrue(self.lan_on_reserve())


class AfterReorder(Crash):
    POINT='apply-write'  # the kernel writer dispatched (journal rtp_dispatched) but the kernel not yet changed
    def test_killed_between_uci_and_kernel_redoes_the_kernel_write(self):
        journal=native.journal_read()
        self.assertTrue(journal['rtp_dispatched']);self.assertEqual(self.b.current,journal['after']);self.assertEqual(self.b.kernel,self.before)
        self.serve()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason'],journal['forward_resumed']['kernel']),('COMMITTED',fr.REASON,'untouched'))
        self.assertEqual(self.rollbacks,[]);self.assertTrue(self.lan_on_reserve())


class WaitClient(Crash):
    POINT='wait-client'
    def test_killed_while_confirming_finishes_forward(self):
        self.assertEqual(native.journal_read()['phase'],'WAIT-CLIENT')
        self.serve()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason'],journal['forward_resumed']['from_phase']),('COMMITTED',fr.REASON,'WAIT-CLIENT'))
        self.assertEqual(self.rollbacks,[]);self.assertTrue(self.lan_on_reserve())


class Unsafe(Crash):
    """Every unproven state rolls back exactly as before (SUPERVISOR-RECOVERY), for the named reason."""

    def rolled_back(self,code,resumed_before=False):
        self.serve()
        journal=native.journal_read()
        self.assertEqual(self.rollbacks[:1],['SUPERVISOR-RECOVERY'],'the old rollback ran')
        if not resumed_before:self.assertNotIn('forward_resumed',journal)
        self.assertNotEqual((journal['phase'],journal.get('reason')),('COMMITTED',fr.REASON))
        self.assertTrue(self.refused_for(code),'refused for %s: %s'%(code,[l for l in self.lines if 'SUPERVISOR-FORWARD' in l]))
        return journal

    def test_reserve_not_healthy(self):
        self.b.health_of[self.b.selection['target']['id']]=False;self.rolled_back('RESERVE-NOT-HEALTHY')

    def test_primary_came_back(self):
        self.b.health_of[self.b.selection['source']['id']]=True;self.rolled_back('SOURCE-NOT-FAILED')

    def test_primary_unknown(self):
        self.b.health_of[self.b.selection['source']['id']]=None;self.rolled_back('SOURCE-NOT-FAILED')

    def test_owner_stop_while_dead(self):
        native.stop_latch(None);self.rolled_back('OWNER-STOP')

    def test_no_owner_marker(self):
        (self.dir/boot_resume.MARKER).unlink();self.rolled_back('OWNER-STOP')

    def test_transaction_nearly_over(self):
        journal=native.journal_read();journal.update(deadline=time.time()+10);native.journal_write(journal)
        self.rolled_back('EXPIRED')

    def test_power_cut_ram_gone(self):
        for name in ('native-apply-progress.json','native-lease.json'):(self.dir/name).unlink()
        self.rolled_back('OTHER-BOOT')

    def test_reserve_rebuilt_new_generation(self):
        self.b.selection=dict(self.b.selection,target=dict(self.b.selection['target'],vendor_generation='3'*32))
        self.rolled_back('IDENTITY')

    def test_pair_session_changed(self):
        state=pair.read_state();state['id']='2'*32;pair.save(state);self.rolled_back('PAIR-SESSION')

    def test_foreign_kernel_graph_is_never_written_forward(self):
        self.b.kernel=self.b.kernel+['x']
        with self.assertRaises(native.Refused):self.serve()  # the old rollback refuses an unknown graph, as before
        self.assertNotIn('forward_resumed',native.journal_read());self.assertTrue(self.refused_for('KERNEL'))
        self.assertEqual(self.rollbacks[:1],['SUPERVISOR-RECOVERY'])

    def test_foreign_uci_order_is_never_resumed(self):
        self.b.current=self.b.current+['x'];self.b.fingerprint='c'*64
        with self.assertRaises(native.Refused):self.serve()  # the old rollback refuses a foreign policy, as before
        self.assertNotIn('forward_resumed',native.journal_read());self.assertTrue(self.refused_for('ORDER'))

    def test_no_double_action_killed_again_during_the_resume(self):
        self.probe_hook=self.kill
        native.STOP=False
        with self.assertRaises(Killed):native.serve()
        self.frozen=False
        journal=native.journal_read()
        self.assertEqual(journal['phase'],'WAIT-CLIENT');self.assertEqual(journal['forward_resumed']['from_phase'],'APPLYING')
        pair.handover_log_reset()
        journal=self.rolled_back('ALREADY-RESUMED',resumed_before=True)
        self.assertEqual((journal['phase'],journal['reason']),('ROLLED-BACK','SUPERVISOR-RECOVERY'));self.assertEqual(self.b.kernel,self.before)

    def test_owner_stop_during_the_resume_wins(self):
        self.probe_hook=lambda:native.stop_latch(None)
        journal=self.rolled_back('CLIENT-STOP',resumed_before=True)
        self.assertEqual((journal['phase'],journal['reason']),('ROLLED-BACK','SUPERVISOR-RECOVERY'))
        self.assertEqual(journal['forward_resumed']['from_phase'],'APPLYING');self.assertEqual(self.b.kernel,self.before)
        self.assertEqual(pair.intent()['mode'],'off')


class UnsafeUntouched(Crash):
    POINT='reorder'  # the kernel still the recorded pre-switch graph: only the order check stands
    def test_foreign_order_with_the_same_policy_hash_is_never_written_forward(self):
        foreign=[self.b.current[-1]]+self.b.current[:-1]
        self.assertNotIn(foreign,(self.before,native.journal_read()['after']))
        self.b.current=foreign[:]
        try:self.serve()
        except native.Refused:pass  # the old path refuses or abandons a foreign order, as before
        self.assertNotIn('forward_resumed',native.journal_read());self.assertTrue(self.refused_for('ORDER'))
        self.assertEqual(self.b.current,foreign,'nothing written forward')


class UnsafeManual(Crash):
    POINT='reorder'
    def crash(self,point,manual=False):return super().crash(point,manual=True)
    def test_interrupted_manual_switch_rolls_back(self):
        self.serve()
        journal=native.journal_read()
        self.assertEqual(self.rollbacks[:1],['SUPERVISOR-RECOVERY']);self.assertNotIn('forward_resumed',journal)
        self.assertTrue(self.refused_for('NOT-AUTOMATIC'))


class HandoverRelease(Crash):
    def test_a_failed_restart_resume_releases_the_handover_and_the_reserve_keeps_the_traffic(self):
        self.serve()
        self.assertIn('handover',pair.read_state())
        agent.atomic_json(self.dir/boot_resume.STATE,{'state':'FAILED','supervisor':boot_resume.token(self.dir)})
        self.assertTrue(pair.tick(self.b,self.b.data['settings'],auto_control.current_revision()))
        state=pair.read_state()
        self.assertNotIn('handover',state);self.assertEqual(state['phase'],'HELD')
        self.assertEqual(native.journal_read()['phase'],'COMMITTED');self.assertTrue(self.lan_on_reserve())

    def test_the_handover_outlives_the_boot_window_and_the_one_per_boot_marker(self):
        agent.atomic_json(self.dir/pair.HANDOVER_FILE,{'state':'handed','tx':'9'*32})
        self.serve()
        self.assertEqual(pair.read_state()['handover']['tx'],native.journal_read()['tx'])


if __name__=='__main__':
    unittest.main()
