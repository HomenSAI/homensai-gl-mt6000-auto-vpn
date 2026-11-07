"""Formal model of the Auto supervisor (03.11.2026, private/math/formal/model.py): each counterexample trace of K2,
K3, K4, K5 and K9 replayed on the Python supervisor. Each test fails on integ/alpha7 (0215164a) and passes with the
fix. K1 tail: test_held_start_handover.py. Lua twin: tests/lua/test_formal_fixes.lua.
"""
from contextlib import contextmanager
import json
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
import native_switch as native
import pair_auto as pair
import test_boot_held as held
import test_failure_matrix as matrix


class LoopReached(BaseException):
    """serve() reached its loop: the recovery is over."""


class GuardRouter(held.Router):
    """The boot-held router with the kernel's view of the guard: the full block releases itself after 90 s."""
    def __init__(self,rename=None):
        super().__init__(rename)
        self.clock=[1000.0];self.full_until=None;self.lapses=[];self.full=0
    def guard(self,devices=None,control_revision=None):
        super().guard(devices,control_revision)
        if devices is None:self.full_until=self.clock[0]+90;self.full+=1
        else:self.full_until=None
    def unguard(self):super().unguard();self.full_until=None
    def guard_exists(self):return self.guarded is not None
    def check(self,where):
        if self.guarded is None or self.guarded=='full' and self.clock[0]>=self.full_until:self.lapses.append(where)


class Fixture(held.Fixture):
    def setUp(self):
        super().setUp()
        self.b.__class__=GuardRouter
        self.b.clock=[1000.0];self.b.full_until=None;self.b.lapses=[];self.b.full=0
        self.uptime=[40.0]
        pair.handover_log_reset();getattr(pair,'outside_guard_reset',lambda:None)()
        self.addCleanup(pair.outside_guard_reset)  # module state: a hold left by a test must not reach the next test module
        self.stack.enter_context(patch.object(pair,'_uptime',side_effect=lambda:self.uptime[0]))
        self.stack.enter_context(patch.object(pair,'interface_up',side_effect=lambda name:self.b.up.get(name,False)))

    def cut(self):
        """A second power cut: RAM files lost, tunnels down, no guard."""
        for name in (pair.HANDOVER_FILE,'auto-control-revision.json',boot_resume.SUPERVISOR,'pair-revive.json','pair-auto-control.json'):
            try:(self.dir/name).unlink()
            except OSError:pass
        for name in self.b.up:self.b.up[name]=False
        self.b.guarded=None;self.b.full_until=None
        pair.handover_log_reset();getattr(pair,'outside_guard_reset',lambda:None)();pair._skip_logged.clear()
        native.STOP=False

    def serve(self):native.STOP=False;native.serve()

    def tick(self):return pair.tick(self.b,self.b.data['settings'],auto_control.current_revision())


class HeldPair(Fixture):
    """The pair's own held journal (pair_transition), as test_boot_held.VariantD."""
    def setUp(self):
        super().setUp()
        import pair_policy
        self.policy=pair_policy
        self.primary_ok=False
        sel=self.b.selection
        journal=native.journal_read()
        ctx=pair_policy.transition(sel,self.before,'target')
        journal.update(pair_transition=ctx,after=pair_policy.desired_order(ctx,self.before,'target'))
        if self.PHASE=='COMMITTED':journal.pop('manual_request_id',None);journal['reason']=None
        native.journal_write(journal);self.b.current=journal['after'][:];self.held=journal
        state=pair.read_state();state['policy_roles']=pair_policy.proof(sel);pair.save(state)
        source,target=sel['source']['id'],sel['target']['id']
        def health(identifier):
            if identifier==target:return self.b.up[self.b.iface[target]]
            return self.primary_ok and self.b.up[self.b.iface[source]]
        self.b.health=health
        self.b.recovery_ready=lambda identifier,settings:health(identifier) is True
        self.b.attest_policy=lambda selection=None:{'verified':self.b.current==self.held['after'] or self.b.current==self.before,
            'role':pair_policy.role(pair_policy.proof(sel),self.b.current),'kernel_fingerprint':'f'*64,'order':self.b.current[:],
            'policy_hash':self.b.fingerprint,'time':time.time()}


class TraceT4(HeldPair):
    def test_a_journal_in_progress_of_another_policy_is_still_an_outside_change(self):
        """T4 lets a finished journal pass (tests/test_trace_fixes.py), never one in progress."""
        state=pair.read_state();state['policy_hash']='f'*64;pair.save(state)
        with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-POLICY-CHANGE'):pair.cleanup(self.b,pair.read_state())
        self.assertEqual(pair.read_state()['phase'],state['phase'],'nothing written')
        self.assertEqual(native.journal_read()['phase'],self.held['phase'])

    def wait_state(self,reason='SOURCE-NOT-VERIFIED'):
        state=pair.read_state();state['phase']='HELD';pair.save(state)
        journal=native.journal_read();journal['reason']=reason;native.journal_write(journal)
        for name in self.b.up:self.b.up[name]=True

    def waits(self):
        journal=native.journal_read()
        return pair.reserve_waits(self.b,pair.read_state(),journal,self.policy.metadata(journal))

    def test_the_wait_writes_nothing_only_while_nothing_would_change(self):
        self.wait_state();(self.dir/pair.HANDOVER_FILE).write_text('{"state":"refused"}')
        self.assertIs(self.waits(),True)
        self.wait_state('OPERATOR-MANUAL');self.assertIs(self.waits(),False,'another reason: the journal is written once')
        self.wait_state();self.primary_ok=True;self.assertIs(self.waits(),False,'the primary is ready: the return')

    def test_an_open_handover_gets_its_full_pass(self):
        self.wait_state()
        self.assertIs(self.waits(),False,'the boot resume will press Start: boot_handover has to run')
        self.uptime[0]=2000
        self.assertIs(self.waits(),True,'the window is over')


class K3(HeldPair):
    def test_power_cut_inside_the_handover_window_restores_the_vpn_only_guard(self):
        self.serve()
        self.assertIn('handover',pair.read_state());self.assertEqual(self.b.guarded,'vpn-only')
        self.cut()
        self.serve()
        state=pair.read_state()
        self.assertEqual(state['phase'],'STOPPED');self.assertIn('handover',state)
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE');self.assertEqual(self.b.current,self.held['after'])
        self.assertEqual(self.b.guarded,'vpn-only','K3: no guard until the handover was released (up to 600 s) before the fix')
        self.assertEqual(self.ifup,['ovpnclient1','wgclient1','ovpnclient1','wgclient1'],'the handed-over clients were started for the guard')

    def test_a_changed_order_is_left_to_the_loop(self):
        state=pair.read_state();state['phase']='STOPPED';pair.save(state)
        self.b.current=self.before[:]
        for name in self.b.up:self.b.up[name]=True
        self.serve()
        self.assertIsNone(self.b.guarded)


class K4(HeldPair):
    def slow(self):
        """quiet waits its whole bound, ifup -w 20 s; every step ends with the kernel's view of the guard."""
        def quiet(seconds,revision=None):self.b.clock[0]+=seconds;self.b.check('quiet %d'%seconds)
        def ifup(argv,revision,timeout=20):
            native.require_control_revision(revision)
            self.ifup.append(argv[2]);self.b.up[argv[2]]=True;self.b.clock[0]+=20;self.b.check('ifup '+argv[2])
        self.stack.enter_context(patch.object(pair,'quiet',side_effect=quiet))
        self.stack.enter_context(patch.object(native,'forward_dispatch',side_effect=ifup))

    def begin(self):
        selection=dict(self.b.selection,process_bindings=None)
        with patch.object(pair,'preflight',return_value=selection),patch('pair_interfaces.selection',return_value=dict(self.INTERFACES)),\
             patch.object(pair,'require_running'),patch.object(pair,'client_down',side_effect=lambda n:not self.b.up[n]):
            return pair.begin(self.b,self.b.data['settings'],{'id':'c'*32,'revision':auto_control.current_revision()})

    def test_start_with_both_clients_down_never_lets_the_block_lapse(self):
        journal=dict(self.held,phase='ROLLED-BACK',restored_order=self.before);native.journal_write(journal);self.b.current=self.before[:]
        state=pair.read_state();state['phase']='STOPPED';pair.save(state)
        self.slow()
        state=self.begin()
        self.assertEqual(state['phase'],'RUNNING');self.assertCountEqual(self.ifup,['wgclient1','ovpnclient1'])
        self.assertEqual(self.b.lapses,[],'K4: the 90 s block expired during the client start before the fix')
        self.assertEqual(self.b.guarded,'vpn-only');self.assertGreaterEqual(self.b.full,4)

    def test_start_after_a_handover_keeps_vpn_only(self):
        self.serve()
        self.assertIn('handover',pair.read_state())
        self.b.up[self.b.iface[self.b.selection['source']['id']]]=False  # the primary client still connecting: begin() starts it
        native.STOP=False
        self.assertTrue(self.start()['accepted'])
        self.slow();self.b.full=0
        self.begin()
        journal=native.journal_read()
        self.assertEqual((journal['phase'],journal['reason']),('COMMITTED','BOOT-RESERVE-ADOPTED'))
        self.assertEqual(self.b.lapses,[])
        self.assertEqual(self.b.full,0,'VPN-only throughout: never downgraded to the self-releasing block')


class K2(HeldPair):
    PHASE='COMMITTED'

    def setUp(self):
        super().setUp()
        # primary_stable 30 s explicitly (the default is 120 s since the 03.11.2026 tuning, integ/alpha8)
        self.b.data['settings']['recovery_primary_stable']='30'
        # wave 3: the damping has its own limit (default 2); 3 keeps this fixture's single doubling
        self.b.data['settings']['recovery_flap_limit']='3'
        self.stable=[40]
        source=self.b.selection['source']['id']
        health=self.b.health
        def ready(identifier,settings):
            need=int(settings.get('recovery_primary_stable',30) or 30)
            if identifier==source:return self.b.up[self.b.iface[source]] and self.stable[0]>=need
            return health(identifier) is True
        self.b.recovery_ready=ready
        now=time.time()
        agent.atomic_json(self.dir/'pair-auto-budget.json',{'events':[now-300,now-200,now-100]})
        # the return itself (rollback.py) is not under test here: the decision to return is
        def rollback(backend,journal,reason,restore_order=None):
            order=list(restore_order or journal['before'])
            journal.update(phase='ROLLED-BACK',reason=reason,restored_order=order);native.journal_write(journal);self.b.current=order
        self.stack.enter_context(patch.object(native,'rollback',side_effect=rollback))
        self.assertEqual(pair.ledger_hold(self.b.data['settings'],now),60)

    def today(self):agent.atomic_json(self.dir/pair.HANDOVER_FILE,{'state':'refused'})

    def serve(self):
        """The recovery only: serve() ends at its first loop pass, before the service-stop path finishes the journal."""
        native.STOP=False
        with patch('speed_pause.gate',side_effect=LoopReached),self.assertRaises(LoopReached):native.serve()

    def test_recovery_cleanup_keeps_the_damped_hold(self):
        self.today()
        self.serve()
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE','K2: returned without return_hold before the fix')
        self.assertEqual(self.b.current,self.held['after']);self.assertEqual(pair.read_state()['phase'],'HELD')
        self.stable[0]=61
        self.tick()
        self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK');self.assertEqual(self.b.current,self.before)

    def test_owner_stop_or_failing_reserve_return_without_the_hold(self):
        for case in ('stop','reserve'):
            with self.subTest(case=case):
                self.tearDown();self.setUp();self.today()
                if case=='stop':native.stop_latch(None)
                if case=='reserve':
                    health=self.b.health;target=self.b.selection['target']['id']
                    self.b.health=lambda identifier:False if identifier==target else health(identifier)
                self.serve()
                self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')

    def test_handover_check_counts_the_primary_proven_only_after_the_hold(self):
        self.serve()
        self.assertIn('handover',pair.read_state(),'PRIMARY-PROVEN with primary_stable before the fix')
        self.assertEqual(native.journal_read()['phase'],'COMMITTED')


class K5(unittest.TestCase):
    setUp=matrix.Matrix.setUp
    spawn=matrix.Matrix.spawn
    confirm=matrix.Matrix.confirm
    state=matrix.Matrix.state

    def test_stop_after_the_last_revision_check_never_precedes_the_commit(self):
        events=[];flags={'armed':False,'checks':0,'locked':0,'pending':False}
        def stop():
            events.append('stop')
            agent.atomic_json(native.RUNTIME/'auto-control-revision.json',{'revision':'9'*32})
        real_assert=native.assert_selection
        def assert_selection(backend,selection):
            if native.journal_read().get('phase')=='WAIT-CLIENT':flags.update(armed=True,checks=0)
            return real_assert(backend,selection)
        real_check=native.require_control_revision
        def require(expected):
            real_check(expected)
            if flags['armed']:
                flags['checks']+=1
                if flags['checks']==2:
                    flags['armed']=False
                    if flags['locked']:flags['pending']=True  # Stop rotates the revision under the control lock
                    else:stop()
        real_lock=auto_control.control_lock
        @contextmanager
        def lock(directory=None):
            with real_lock(directory):
                flags['locked']+=1
                try:yield
                finally:flags['locked']-=1
            if flags['pending'] and not flags['locked']:flags['pending']=False;stop()
        real_write=native.journal_write
        def write(value):
            if value.get('phase')=='COMMITTED' and native.journal_read().get('phase')!='COMMITTED':events.append('commit')
            return real_write(value)
        process=MagicMock(pid=123,returncode=0);self.spawn(process,self.confirm)
        self.stack.enter_context(patch.object(native,'trace',return_value='9.9.9.9'))
        with patch.object(native,'assert_selection',side_effect=assert_selection),patch.object(native,'require_control_revision',side_effect=require),\
             patch.object(auto_control,'control_lock',side_effect=lock),patch.object(native,'journal_write',side_effect=write):
            try:native.attempt(self.b,self.b.selection,time.time()+120,False,control_revision=auto_control.current_revision())
            except native.Refused:pass
        self.assertEqual(events,['commit','stop'],'COMMITTED-AFTER-STOP before the fix')


class OutsideChange(Fixture):
    """Auto ran on the primary (journal ROLLED-BACK), then the owner changed the VPN clients in the GL panel."""
    def setUp(self):
        super().setUp()
        journal=native.journal_read();journal.update(phase='ROLLED-BACK',restored_order=self.before);journal.pop('manual_request_id',None)
        native.journal_write(journal);self.b.current=self.before[:]
        state=pair.read_state();state.update(phase='HELD',recovery_error='PAIR-EXTERNAL-NETWORK-CHANGE');pair.save(state)
        self.stack.enter_context(patch.object(pair,'normalized_network',return_value='c'*64))


class K9(OutsideChange):
    """Owner decision 03.11.2026: a session HELD by an outside GL change keeps the VPN-only guard after a power cut."""

    def test_power_cut_after_a_gl_edit_keeps_the_guard(self):
        self.serve()
        state=pair.read_state()
        self.assertEqual((state['phase'],state['recovery_error']),('HELD','PAIR-EXTERNAL-NETWORK-CHANGE'))
        self.assertEqual(self.b.guarded,'full','K9: no guard after the power cut before the fix; no tunnel up: no internet')
        calls=len(self.b.calls)
        self.tick()
        self.assertEqual(len(self.b.calls),calls,'not re-armed on every pass')
        with patch.object(pair.time,'monotonic',return_value=time.monotonic()+pair.OUTSIDE_REARM):self.tick()
        self.assertEqual(len(self.b.calls),calls+1,'re-armed before the 90 s self-release')
        self.assertEqual(self.b.calls[-1],('guard',None))
        self.b.up['ovpnclient1']=True
        self.tick()
        self.assertEqual(self.b.guarded,'vpn-only','LAN only through the VPN tunnel that is up')

    def test_owner_stop_releases_the_guard(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertEqual(self.b.guarded,'vpn-only')
        native.stop_latch(None)
        self.tick()
        self.assertIsNone(self.b.guarded,'Stop releases as before')
        self.tick();self.assertIsNone(self.b.guarded)
        self.cut();self.serve()
        self.assertIsNone(self.b.guarded,'and a later power cut does not guard again')

    def test_owner_stop_ends_the_hold_stopped(self):
        """T4-A (owner rule 07.11.2026, T4A-NOTE.md): the Stop ends STOPPED, not HELD with the readopt code; it adopts
        nothing, so a spent adoption budget never keeps the hold and the Stop spends none of it."""
        self.b.up['ovpnclient1']=True
        self.serve()
        now=time.time()
        agent.atomic_json(agent.RUNTIME/'pair-readopt.json',{'events':[now-3,now-2,now-1]})
        held_id=pair.read_state()['id']
        native.stop_latch(None)
        self.tick()
        state=pair.read_state()
        self.assertEqual((state['id'],state['phase'],state.get('recovery_error'),state['owned']),(held_id,'STOPPED',None,[]))
        resolution=state['operator_resolution']
        self.assertEqual((resolution['adopted_by'],resolution['trigger'],resolution['outside_change']['decision'],
                          resolution['outside_change']['why']),('owner-stop','PAIR-EXTERNAL-NETWORK-CHANGE','STOP','OWNER-STOP'))
        self.assertIn('-stop-',resolution['archive'])
        self.assertTrue((agent.PERSIST/'session-recovery'/resolution['archive']).exists())
        self.assertEqual(len(agent.read_json(agent.RUNTIME/'pair-readopt.json',{})['events']),3,'the Stop spends no adoption')
        self.assertIsNone(self.b.guarded)
        self.tick()
        self.assertEqual(pair.read_state(),state,'a later pass leaves the stopped record alone')

    def test_no_stop_no_end(self):
        """Without the owner's Stop the hold stays HELD (end_hold_on_stop refuses, nothing written)."""
        self.b.up['ovpnclient1']=True
        self.serve()
        before=pair.read_state()
        self.assertFalse(pair.end_hold_on_stop(before))
        self.assertEqual(pair.read_state(),before)

    def test_start_takes_the_hand_over_path(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertEqual(self.b.guarded,'vpn-only')
        native.STOP=False
        reply=auto_control.start(control_revision=auto_control.current_revision(),request_source='manual')
        self.assertTrue(reply.get('accepted'),reply)
        state=pair.read_state()
        self.assertEqual((state['phase'],state['operator_resolution']['trigger']),('STOPPED','PAIR-EXTERNAL-NETWORK-CHANGE'))
        self.assertEqual(pair.intent()['mode'],'on')

    slow=K4.slow
    begin=K4.begin

    def test_the_start_that_ends_the_hold_keeps_vpn_only_while_the_clients_start(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertEqual(self.b.guarded,'vpn-only')
        native.STOP=False
        reply=auto_control.start(control_revision=auto_control.current_revision(),request_source='manual')
        self.assertTrue(reply.get('accepted'),reply)
        self.slow();self.b.full=0
        state=self.begin()
        self.assertEqual(state['phase'],'RUNNING')
        self.assertEqual(self.b.lapses,[])
        self.assertEqual(self.b.full,0,'K4: never downgraded to the self-releasing full block')
        self.assertIsNone(pair._outside_guard.get('mode'),'the hold is over')

    def test_an_older_stop_latch_is_not_the_stop_of_a_later_session(self):
        state=pair.read_state()
        try:(agent.PERSIST/boot_resume.MARKER).unlink()
        except OSError:pass
        started=state.get('started') or time.time()
        state['started']=started;pair.save(state)
        self.assertFalse(pair.owner_stopped(state),'no latch')
        agent.atomic_json(agent.PERSIST/'native-stop.json',{'requested':started-100})
        self.assertFalse(pair.owner_stopped(state),'a Stop before this session started')
        self.assertTrue(pair.owner_stopped(None),'no start known: the latch is the Stop')
        agent.atomic_json(agent.PERSIST/'native-stop.json',{'requested':started+1})
        self.assertTrue(pair.owner_stopped(state),'a Stop after this session started')
        agent.atomic_json(agent.PERSIST/boot_resume.MARKER,{'enabled':True,'time':started+2})
        self.assertFalse(pair.owner_stopped(state),'the owner Started again after it')
        (agent.PERSIST/'native-stop.json').write_text('{damaged')
        self.assertFalse(pair.owner_stopped(state),'a damaged latch is not a Stop')

    def test_a_held_journal_or_other_code_is_not_this_hold(self):
        journal=native.journal_read();journal['phase']='HELD-ON-RESERVE';native.journal_write(journal)
        self.assertFalse(pair.outside_hold(self.b))
        journal['phase']='ROLLED-BACK';native.journal_write(journal)
        state=pair.read_state();state['recovery_error']='UNSAFE-GUARD-DEVICE';pair.save(state)
        self.assertFalse(pair.outside_hold(self.b))


class K11(OutsideChange):
    """The owner's Start hands the outside-change hold over (release_session, under the control lock) while a cleanup
    pass of the supervisor already read the HELD record: the stale pass must not write STOPPING over the hand-over."""
    def test_a_cleanup_pass_in_flight_never_overwrites_the_start_hand_over(self):
        pair.stop_locked(auto_control.current_revision())  # Auto off: the tick cleans the HELD session up
        import pair_interfaces
        real=pair_interfaces.state
        raced=[]
        def interfaces(state):
            if not raced:  # the first step of cleanup(): the owner's Start hands the session over right now
                raced.append(None);raced[0]=pair.release_session(pair.read_state(),'PAIR-EXTERNAL-NETWORK-CHANGE')
            return real(state)
        with patch('pair_interfaces.state',side_effect=interfaces):self.tick()
        self.assertEqual(raced,[True])
        state=pair.read_state()
        self.assertEqual(state['phase'],'STOPPED','K11: the stale cleanup wrote STOPPING over the hand-over (then HELD again)')
        self.assertEqual(state['operator_resolution']['trigger'],'PAIR-EXTERNAL-NETWORK-CHANGE')
        self.tick()
        self.assertEqual(pair.read_state()['phase'],'STOPPED','a later pass leaves the handed-over record alone')

    def test_a_failure_marks_the_record_held_only_under_the_control_lock(self):
        """The same race on the failure path (an error before the STOPPING write, e.g. PAIR-EXTERNAL-POLICY-CHANGE):
        publish_failure reads the record and writes HELD; the read and the write run under the control lock of the
        hand-over, so a HELD from an older read never lands over its STOPPED."""
        real_lock=auto_control.control_lock
        seen={'inside':False,'writes':[]}
        @contextmanager
        def lock(directory=None):
            with real_lock(directory):
                outer,seen['inside']=seen['inside'],True
                try:yield
                finally:seen['inside']=outer
        real_save=pair.save
        def save(state):
            seen['writes'].append((state.get('phase'),seen['inside']));return real_save(state)
        with patch.object(auto_control,'control_lock',side_effect=lock),patch.object(pair,'save',side_effect=save):
            pair.publish_failure('PAIR-EXTERNAL-POLICY-CHANGE')
        self.assertEqual(seen['writes'],[('HELD',True)],'K11: HELD written outside the control lock')
        self.assertEqual(pair.read_state()['recovery_error'],'PAIR-EXTERNAL-POLICY-CHANGE')
        self.assertTrue(pair.release_session(pair.read_state(),'PAIR-EXTERNAL-POLICY-CHANGE'))
        pair.publish_failure('PAIR-RECOVERY-REQUIRED')
        self.assertEqual(pair.read_state()['phase'],'STOPPED','a failure after the hand-over leaves its record alone')


class Review0411(OutsideChange):
    """Independent review 04.11.2026, findings 3, 4 and 5 on the outside-change hold (K9)."""

    def writes(self):
        real=pair.save;log=[]
        def save(state):log.append(state.get('phase'));return real(state)
        return log,patch.object(pair,'save',side_effect=save)

    def setUp(self):
        super().setUp()
        self.b.data['settings']['terms_version']=agent.TERMS_VERSION  # the owner's Start hands the hold over (release_for_start)

    def test_finding3_a_stable_hold_writes_nothing_on_its_passes(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        path=pair.paths()[1];before=path.stat();journal=native.JOURNAL.stat()
        log,mock=self.writes()
        with mock:
            for _ in range(5):self.tick()
        self.assertEqual(native.JOURNAL.stat().st_mtime_ns,journal.st_mtime_ns,'the journal is a key file too')
        self.assertEqual(log,[],'STOPPING then HELD on every pass (about 2 s) before the fix: flash writes, and the Lua '
                                'supervisor started python3 restore-autostart each time (its key holds this file)')
        after=path.stat()
        self.assertEqual((after.st_ino,after.st_size,after.st_mtime_ns),(before.st_ino,before.st_size,before.st_mtime_ns))
        state=pair.read_state()
        self.assertEqual((state['phase'],state['recovery_error']),('HELD','PAIR-EXTERNAL-NETWORK-CHANGE'))
        self.assertEqual(self.b.guarded,'vpn-only','the K9 guard stays')
        # another outside change is written once; the change undone (the GL configuration put back) ends the hold as before
        with patch.object(pair,'normalized_network',return_value=held.IDENTITY),patch.object(pair,'changed',return_value=True):self.tick()
        self.assertEqual(pair.read_state()['recovery_error'],'PAIR-EXTERNAL-CONFIG-CHANGE')
        with patch.object(pair,'normalized_network',return_value=held.IDENTITY):self.tick()
        self.assertEqual(pair.read_state()['phase'],'STOPPED')

    def test_finding4_a_start_refused_after_the_hand_over_leaves_no_guard(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertEqual(self.b.guarded,'vpn-only')
        native.STOP=False
        with patch('preparation_control.auto_prepare',return_value={'code':'PREPARATION-RESTART-REQUIRED','repaired':[]}):
            reply=auto_control.start(control_revision=auto_control.current_revision(),request_source='manual')
        self.assertEqual(reply.get('blockers'),['PREPARATION-RESTART-REQUIRED'])
        state=pair.read_state()
        self.assertEqual((state['phase'],state['owned'],state['operator_resolution']['trigger']),('STOPPED',[],'PAIR-EXTERNAL-NETWORK-CHANGE'))
        self.assertIsNone(self.b.guarded,'the VPN-only guard of the retired session stayed with nothing running before the fix')
        native.stop_latch(None);self.tick();self.assertIsNone(self.b.guarded)

    def test_finding4_the_owner_stop_releases_the_guard_of_a_handed_over_session(self):
        # the Start ended between its hand-over and its request (no refusal path ran): the owner's Stop releases the guard
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertIsNone(pair.release_for_start(auto_control.current_revision(),self.b.data['settings'],time.time()))
        self.assertEqual(pair.read_state()['phase'],'STOPPED')
        self.b.current=self.before[::-1]  # the owner moved the GL rules too: the journal path (restored order) keeps its guard
        self.tick();self.assertEqual(self.b.guarded,'vpn-only','until Start or Stop (K9)')
        native.stop_latch(None);self.tick()
        self.assertIsNone(self.b.guarded,'kept for good before the fix: no internet on the LAN while the tunnels are down')
        calls=len(self.b.calls);self.tick();self.tick()
        self.assertEqual(len(self.b.calls),calls,'looked at once, not on every idle pass')

    def test_finding4_only_the_guard_of_a_handed_over_record_is_released(self):
        self.b.up['ovpnclient1']=True
        self.serve()
        self.assertEqual(self.b.guarded,'vpn-only')
        native.stop_latch(None)
        resolution={'reason':'AUTOMATIC-EXTERNAL-CHANGE-READOPT','time':1.0}
        state=dict(pair.read_state(),phase='STOPPED',owned=[])
        for name,fields in (('no hand-over',{}),('another resolution',{'operator_resolution':dict(resolution,reason='OTHER')}),
                            ('kept clients',{'operator_resolution':resolution,'kept':['wgclient1'],'kept_flags':{'wgclient1':'0'},'kept_at':5.0}),
                            ('a handover',{'operator_resolution':resolution,'handover':{'tx':'d'*32,'order':state['order'],'policy_hash':state['policy_hash'],'at':5.0}})):
            with self.subTest(name):
                pair.outside_guard_reset();pair.save(dict(state,**fields))  # on disk: the check under the lock reads the record
                self.assertFalse(pair.release_orphan_guard(self.b))
                self.assertEqual(self.b.guarded,'vpn-only')
        state['operator_resolution']=resolution;pair.save(state)
        for name,patcher in (('Auto requested',patch.object(pair,'intent',return_value={'mode':'on'})),
                             ('a held journal',patch.object(native,'journal_read',return_value={'phase':'HELD-ON-RESERVE'}))):
            with self.subTest(name),patcher:
                pair.outside_guard_reset()
                self.assertFalse(pair.release_orphan_guard(self.b))
                self.assertEqual(self.b.guarded,'vpn-only')
        pair.outside_guard_reset()
        self.assertTrue(pair.release_orphan_guard(self.b));self.assertIsNone(self.b.guarded)

    def test_finding5_a_hold_with_nothing_owned_keeps_the_guard_until_start_or_stop(self):
        state=pair.read_state();state['owned']=[];pair.save(state)
        self.b.up['ovpnclient1']=True
        self.serve()
        state=pair.read_state()
        self.assertEqual((state['phase'],state.get('recovery_error')),('HELD','PAIR-EXTERNAL-NETWORK-CHANGE'),'K9: STOPPED, unguarded before the fix')
        self.assertEqual(self.b.guarded,'vpn-only')
        self.tick();self.assertEqual(self.b.guarded,'vpn-only')
        native.stop_latch(None);self.tick()
        self.assertEqual(pair.read_state()['phase'],'STOPPED','the owner Stop ends the hold: the app owns nothing to stop')
        self.assertIsNone(self.b.guarded)

    def test_finding5_the_same_for_a_changed_client_configuration(self):
        state=pair.read_state();state.update(owned=[],recovery_error='PAIR-EXTERNAL-CONFIG-CHANGE');pair.save(state)
        self.b.up['ovpnclient1']=True
        with patch.object(pair,'normalized_network',return_value=held.IDENTITY),patch.object(pair,'changed',return_value=True):
            self.serve()
            self.assertEqual((pair.read_state()['phase'],self.b.guarded),('HELD','vpn-only'))
        with patch.object(pair,'normalized_network',return_value=held.IDENTITY):self.tick()
        self.assertEqual(pair.read_state()['phase'],'STOPPED','the change undone: the cleanup finishes')

    def test_finding5_the_cleanup_checks_again_when_the_precheck_does_not_decide(self):
        # e.g. a journal this very cleanup finishes first (COMMITTED -> ROLLED-BACK): the read-only precheck stays out
        state=pair.read_state();state['owned']=[];pair.save(state)
        with patch.object(pair,'held_unchanged',return_value=None):
            with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-NETWORK-CHANGE'):pair.cleanup(self.b,pair.read_state())
        self.assertEqual(pair.read_state()['phase'],'STOPPING','never STOPPED (and unguarded) over the outside change')
        self.assertNotIn(('unguard',),self.b.calls)


del Fixture,HeldPair,OutsideChange  # base classes only (no tests of their own)


if __name__=='__main__':
    unittest.main()
