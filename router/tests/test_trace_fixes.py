# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Findings of the trace conformance run (tools/formal/trace_check.py, 04.11.2026; docs/architecture/FORMAL-FIXES-2026-11-03.ru.md).

The scenario tests replay the seeded traces on the real supervisors of BOTH runtimes (router/tests/trace_driver.py and
router/tests/lua/trace_driver.lua) and read the abstract state back. Each fails before its fix. The Lua twins of the unit
tests: tests/lua/test_control_request.lua and tests/lua/test_formal_fixes.lua.
"""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
sys.path.insert(0,str(HERE))
import agent
import auto_control
import boot_resume
import native_switch as native
import pair_auto as pair
import pair_policy
import rollback_recovery
import trace_driver

LUA=shutil.which('lua5.1')


def run_both(events):
    """{runtime: steps}: one scenario on both supervisors (Python only when lua5.1 is absent)."""
    try:traces=trace_driver.run([{'name':'scenario','events':events.split()}])
    finally:  # module state of the supervisor: never left for the next test file
        pair.handover_log_reset();pair.outside_guard_reset();pair._skip_logged.clear();pair.LATE_ABORTS.clear();native.STOP=False
    if traces[0].get('driver_error'):raise AssertionError(traces[0]['driver_error'])
    out={'python':traces[0]['steps']}
    if LUA:
        with tempfile.TemporaryDirectory(prefix='trace-fixes-') as work:
            src,dst=Path(work)/'in.json',Path(work)/'out.json'
            src.write_text(json.dumps([{'name':'scenario','events':events.split()}]),encoding='utf-8')
            proc=subprocess.run([LUA,'trace_driver.lua',str(src),str(dst)],cwd=str(HERE/'lua'),capture_output=True,text=True,
                                env=dict(os.environ,HOMENSAI_TEST_RUNTIME=work),timeout=120)
            if proc.returncode:raise AssertionError(proc.stdout+proc.stderr)
            trace=json.loads(dst.read_text(encoding='utf-8'))[0]
            if trace.get('driver_error'):raise AssertionError(trace['driver_error'])
            out['lua']=trace['steps']
    return out


def last(steps,event):
    return [row for row in steps if row['event']==event][-1]


class StopLatch(unittest.TestCase):
    """T1, the file level: the latch against auto-resume.json with the pair mode's empty auto-control.json."""
    TRIAL='c'*32

    def setUp(self):
        self.dir=Path(tempfile.mkdtemp(prefix='stop-latch-'))
        self.addCleanup(shutil.rmtree,self.dir,True)
        self.runtime,self.persist=self.dir/'run',self.dir/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        self.now=[1793420000.0]
        self.policy=lambda *a,**k:json.dumps({'settings':{'native_trial':self.TRIAL}}).encode()

    def stop(self):
        with patch('agent.command',side_effect=self.policy),patch.object(time,'time',side_effect=lambda:self.now[0]):
            return auto_control.stop(runtime=self.runtime,persist=self.persist,request_source='manual')

    def latch(self):
        return json.loads((self.persist/'native-stop.json').read_text())

    def owner_start(self,at=None):
        self.now[0]+=10
        boot_resume.remember(self.persist,self.now[0] if at is None else at)

    def test_a_stop_after_a_later_start_refreshes_the_latch(self):
        self.owner_start();self.assertEqual(self.stop(),{'queued':True})
        self.owner_start();self.assertTrue(boot_resume.wanted(self.persist)[0])
        reply=self.stop()
        self.assertNotIn('already_requested',reply,'the second Stop of a pair session compared with auto-control.json (time 0)')
        self.assertEqual(boot_resume.wanted(self.persist),(False,'AUTO-RESUME-STOPPED'))

    def test_a_global_latch_is_refreshed_too_and_stays_global(self):
        self.owner_start()
        (self.persist/'native-stop.json').write_text(json.dumps({'requested':self.now[0]-5,'trial':'a'*32,'all_trials':True}))
        reply=self.stop()
        self.assertNotIn('already_requested',reply)
        self.assertEqual(boot_resume.wanted(self.persist),(False,'AUTO-RESUME-STOPPED'))
        self.assertIs(self.latch().get('all_trials'),True,'a refreshed latch never narrows a global one')

    def test_a_repeated_stop_writes_nothing(self):
        self.owner_start();self.stop();first=(self.persist/'native-stop.json').read_text()
        self.now[0]+=30
        self.assertEqual(self.stop(),{'queued':True,'already_requested':True})
        self.assertEqual((self.persist/'native-stop.json').read_text(),first)

    def test_a_wall_clock_behind_the_marker_still_ends_resume(self):
        # no RTC: the boot clock stands behind a marker written before the power cut
        at=self.now[0]+3600
        self.owner_start(at=at)
        self.stop()
        self.assertEqual(self.latch()['requested'],at)
        self.assertEqual(boot_resume.wanted(self.persist),(False,'AUTO-RESUME-STOPPED'))

    def test_a_give_up_latch_with_the_clock_behind_the_marker_wins_too(self):
        self.owner_start(at=self.now[0]+3600)
        with patch.object(native,'PERSIST',self.persist),patch.object(native,'RUNTIME',self.runtime),patch('boot_resume.PERSIST',self.persist,create=True),\
             patch.object(time,'time',side_effect=lambda:self.now[0]),patch('auto_control.RUNTIME',self.runtime):
            native.stop_latch(self.TRIAL)
        self.assertEqual(boot_resume.wanted(self.persist),(False,'AUTO-RESUME-STOPPED'))

    def test_a_damaged_marker_never_prevents_the_stop(self):
        self.stop()
        (self.persist/boot_resume.MARKER).write_text('{broken')
        self.assertEqual(boot_resume.marker_time(self.persist),float('inf'))
        before=self.latch()['requested']
        self.now[0]+=5
        self.assertEqual(self.stop(),{'queued':True},'an unreadable marker: the latch is written')
        self.assertEqual(self.latch()['requested'],self.now[0],'and it keeps a real time')
        self.assertGreater(self.latch()['requested'],before)

    def test_the_marker_is_written_under_the_control_lock(self):
        """A marker written after the lock could land behind a Stop that came in between and outlive it."""
        held=[]

        def remember():
            fd=os.open(str(self.runtime/'auto-control.lock'),os.O_RDWR)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                held.append(False)
            except BlockingIOError:
                held.append(True)
            finally:os.close(fd)
        with patch.object(auto_control,'RUNTIME',self.runtime),patch.object(agent,'RUNTIME',self.runtime),\
             patch.object(pair,'paths',return_value=(self.runtime/'pair-auto-control.json',self.runtime/'pair-auto-state.json')),\
             patch('speed_pause.public',return_value={}),patch.object(boot_resume,'remember',side_effect=remember):
            revision=auto_control.current_revision()
            self.assertTrue(pair.request(revision,request_source='manual')['accepted'])
            (self.runtime/'pair-auto-control.json').unlink()
            self.assertTrue(pair.request(revision,request_source='programmatic')['accepted'])
        self.assertEqual(held,[True],'one marker, the manual Start only, inside the lock')


class ReservePolicy(unittest.TestCase):
    """T3, the pass level: only the one blocker of a lost reserve, only with the traffic on a settled reserve journal."""
    def setUp(self):
        self.backend=MagicMock()
        self.state={'id':'a'*32,'phase':'RUNNING','policy_roles':{'source_id':'s','target_id':'t'},'order':['r1','r2'],'policy_hash':'h'}
        self.stack=[patch.object(pair,'intent',return_value={'mode':'on','revision':'r','id':'a'*32}),patch.object(native,'publish')]
        self.publish=[item.start() for item in self.stack][1]
        for item in self.stack:self.addCleanup(item.stop)

    def reapply(self,journal,blockers=('RESERVE-NOT-CONNECTED',),match=True):
        self.backend.diagnostic.return_value=(list(blockers),None)
        with patch('pair_policy.state_order_matches',return_value=match):
            return pair.reapply_missing_policy(self.backend,self.state,{},'r',journal)

    def test_a_lost_reserve_goes_on_to_the_committed_decision(self):
        for phase in ('COMMITTED','HELD-ON-RESERVE'):
            self.assertIs(self.reapply({'phase':phase}),False,phase)
        self.publish.assert_not_called()

    def test_a_lost_reserve_keeps_the_outside_change_check(self):
        with self.assertRaisesRegex(ValueError,'PAIR-EXTERNAL-POLICY-CHANGE'):self.reapply({'phase':'COMMITTED'},match=False)

    def test_any_other_case_still_blocks(self):
        self.assertIs(self.reapply({'phase':'COMMITTED'},('RESERVE-NOT-CONNECTED','VENDOR-WORKER-BUSY')),True,'another blocker too')
        self.assertIs(self.reapply({'phase':'COMMITTED'},('VENDOR-SETTLING',)),True,'another blocker')
        self.assertIs(self.reapply({'phase':'ROLLED-BACK'}),True,'the traffic is on the primary: nothing to return')
        self.assertIs(self.reapply({}),True,'no journal')
        self.assertEqual(self.publish.call_count,4)

    def test_settled_ends_its_wait_on_the_tolerated_blocker_only(self):
        backend=MagicMock()
        clock=[0.0]
        sleeps=[]
        backend.diagnostic.return_value=(['RESERVE-NOT-CONNECTED'],None)
        run=lambda tolerated:rollback_recovery.settled(backend,clock=lambda:clock[0],sleep=lambda s:(sleeps.append(s),clock.__setitem__(0,clock[0]+s)),tolerated=tolerated)
        self.assertEqual(run('RESERVE-NOT-CONNECTED'),(['RESERVE-NOT-CONNECTED'],None));self.assertEqual(sleeps,[],'no LAN block for the whole wait')
        run(None);self.assertTrue(sleeps,'without it the wait is as before')
        sleeps.clear();clock[0]=0.0
        backend.diagnostic.return_value=(['RESERVE-NOT-CONNECTED','VENDOR-WORKER-BUSY'],None)
        run('RESERVE-NOT-CONNECTED');self.assertTrue(sleeps,'not with another blocker')


class Rollback(unittest.TestCase):
    """T3: the proof of a return; T2: the reload of the branch without rtp_dispatched."""
    def test_the_reserve_is_tolerated_only_for_a_return_to_the_primary(self):
        for index,expected in ((0,'source'),(1,'target')):
            before,after=['r1','r2','g'],['r2','r1','g']
            seen={}

            def settled(backend,tolerated=None,**k):
                seen['tolerated']=tolerated
                return ['RESERVE-NOT-CONNECTED'],None
            rows=(before,after)
            context={'source_rule':'r1','target_rule':'r2','direction':'first','generic_rules':['r1','r2'],'source_id':'s','target_id':'t','destination_role':'target',
                     'before_policy_role':'source','session_order':rows[index],'primary_order':before}
            journal={'pair_transition':context,'phase':'COMMITTED','before':before,'after':after,'source':'s','target':'t','hash':'h','tx':'x'}
            backend=MagicMock()
            order=[after if index==0 else before]
            backend.order.side_effect=lambda:(order[0],'h')
            backend.reorder.side_effect=lambda value,**k:order.__setitem__(0,value)
            backend.attest_policy.return_value={'verified':True,'role':'target' if index==0 else 'source','kernel_fingerprint':'f'*64,'order':order[0]}
            backend.kernel_fingerprint.return_value='f'*64
            backend.devices.return_value=['wgclient1']
            with patch.object(rollback_recovery,'settled',side_effect=settled),patch.object(rollback_recovery,'vendor_settled'),\
                 patch.object(rollback_recovery,'vendor_rebuild_applies',return_value=False),patch.object(pair_policy,'metadata',return_value=context),\
                 patch.object(pair_policy,'validate',side_effect=lambda value,order:value),\
                 patch.object(native,'journal_write'),patch.object(native,'publish'),patch.object(native,'bind_policy_context'),patch.object(native,'note_phase'),\
                 patch.object(native,'reset_old_flows'),patch('switch_timing.record'):
                if expected=='source':
                    backend.attest_policy.side_effect=[{'verified':True,'role':'target','kernel_fingerprint':'f'*64,'order':after},
                                                       {'verified':True,'role':'source','kernel_fingerprint':'f'*64,'order':before}]
                    native.rollback(backend,journal,'PRIMARY-STABLY-RECOVERED',restore_order=before)
                    self.assertEqual(journal['phase'],'ROLLED-BACK')
                else:
                    with self.assertRaisesRegex(native.Refused,'ROLLBACK-UNVERIFIED'):
                        native.rollback(backend,journal,'PAIR-STOPPED',restore_order=after)
            self.assertEqual(seen['tolerated'],'RESERVE-NOT-CONNECTED' if expected=='source' else None)

    def test_a_failed_reload_keeps_the_journal_rolled_back(self):
        """Best effort, as lua/rollback.lua: the attestation of the loop blocks, the journal is not left open."""
        before,after=['r1','r2'],['r2','r1']
        journal={'pair_transition':{},'rtp_dispatched':False,'phase':'APPLYING','before':before,'after':after,'hash':'h','source':'s','target':'t',
                 'kernel_before_fingerprint':'a'*64}
        backend=MagicMock()
        order=[after]
        backend.order.side_effect=lambda:(order[0],'h')
        backend.reorder.side_effect=lambda value:order.__setitem__(0,value)
        backend.kernel_fingerprint.return_value='b'*64
        backend.apply.side_effect=native.Refused('RTP-BOOT-PRECONDITION-UNVERIFIED')
        backend.devices.return_value=['wgclient1']
        with patch.object(native,'journal_write'),patch.object(native,'publish'),patch.object(native,'bind_policy_context'),patch.object(native,'pair_event_fields',return_value={}):
            native.rollback(backend,journal,'SUPERVISOR-RECOVERY')
        backend.apply.assert_called_once_with()
        self.assertEqual(journal['phase'],'ROLLED-BACK');self.assertIs(journal['kernel_policy_verified'],False)
        backend.apply.reset_mock();journal.update(phase='APPLYING');order[0]=after
        with patch.object(native,'journal_write'),patch.object(native,'publish'),patch.object(native,'bind_policy_context'),patch.object(native,'pair_event_fields',return_value={}):
            native.rollback(backend,journal,'TRANSACTION-FAILED')
        backend.apply.assert_not_called()  # a running pass wrote no kernel: a changed graph there is foreign and stays
        for fingerprint,calls in (('a'*64,0),):
            backend.apply.reset_mock();backend.apply.side_effect=None;backend.kernel_fingerprint.return_value=fingerprint
            journal.update(phase='APPLYING');order[0]=after
            with patch.object(native,'journal_write'),patch.object(native,'publish'),patch.object(native,'bind_policy_context'),patch.object(native,'pair_event_fields',return_value={}):
                native.rollback(backend,journal,'SUPERVISOR-RECOVERY')
            self.assertEqual(backend.apply.call_count,calls,'the kernel is the one before our move: no rebuild')


class Scenarios(unittest.TestCase):
    def test_t1_a_second_stop_keeps_auto_off_after_a_power_cut(self):
        runs=run_both('tick start tick tick stop tick tick start tick tick stop tick tick power resume tick tick')
        for runtime,steps in runs.items():
            with self.subTest(runtime):
                stops=[row['reply'] for row in steps if row['event']=='stop']
                self.assertEqual(stops,['queued','queued'],'the second Stop answered already_requested')
                self.assertIs(last(steps,'stop')['obs']['marker'],False)
                self.assertEqual(last(steps,'resume')['reply'],'SKIPPED')
                final=steps[-1]['obs']
                self.assertEqual((final['intent'],final['sess']),('off','STOPPED'),'Auto came back against the owner\'s last Stop')

    def test_t2_a_power_cut_between_uci_and_rtp_moves_the_kernel_back(self):
        for runtime,steps in run_both('tick start tick tick p_down p_down power@5 tick tick').items():
            with self.subTest(runtime):
                final=steps[-1]['obs']
                self.assertEqual((final['jr'],final['uci'],final['kern']),('RB','P','P'),'ROLLED-BACK with the kernel on the reserve')

    def test_t3_a_stop_on_a_lost_reserve_ends_on_the_primary(self):
        for runtime,steps in run_both('tick start tick tick p_down tick tick stop tick r_lost p_up wait_long tick tick tick').items():
            with self.subTest(runtime):
                self.assertFalse([row for row in steps if row['end']=='GIVEUP'],'ROLLBACK-GIVEN-UP with the kernel on the primary')
                final=steps[-1]['obs']
                self.assertEqual((final['jr'],final['uci'],final['kern'],final['sess'],final['guard']),('RB','P','P','STOPPED','none'))

    def test_t3_a_running_session_leaves_a_lost_reserve_for_a_healthy_primary(self):
        for runtime,steps in run_both('tick start tick tick p_down tick tick r_lost tick p_up wait_long tick tick').items():
            with self.subTest(runtime):
                self.assertEqual(steps[-1]['obs']['jr'],'RB','no return while the primary is alive until the reserve is back')
                self.assertEqual((steps[-1]['obs']['kern'],steps[-1]['obs']['sess'],steps[-1]['obs']['guard']),('P','RUNNING','vpn'))

    def test_t4_a_stop_on_a_dead_primary_writes_no_file_while_it_waits(self):
        for runtime,steps in run_both('tick start tick tick p_down tick tick stop tick tick tick tick p_up wait_long tick tick').items():
            with self.subTest(runtime):
                ticks=[row for row in steps if row['event']=='tick']
                waits=[row['n_writes'] for row in ticks[-5:-2]]
                self.assertEqual([row['obs']['jr'] for row in ticks[-5:-2]],['HOR']*3)
                self.assertEqual(waits,[1,1,1],'STOPPING, the journal and HELD on every pass (the 1 left is the guard, RAM)')
                final=steps[-1]['obs']
                self.assertEqual((final['jr'],final['kern'],final['sess'],final['guard']),('RB','P','STOPPED','none'),'the return still comes')

    def test_t4_a_stop_after_an_outside_change_ends_stopped(self):
        events='tick start tick tick p_down tick tick p_up wait_long tick tick gl_pol tick tick start tick tick tick stop tick tick'
        for runtime,steps in run_both(events).items():
            with self.subTest(runtime):
                self.assertEqual(last(steps,'stop')['obs']['jr'],'RB','the finished journal of the policy before')
                final=steps[-1]['obs']
                self.assertEqual((final['sess'],final['guard'],final['readopt_code']),('STOPPED','none',False))

    def test_t4_a_an_outside_hold_ends_only_by_stop_then_start(self):
        """Owner rule 07.11.2026 (T4A-NOTE.md): a HELD outside change stays held through a Start while Auto is on; the Stop
        ends STOPPED (not a readopt: the budget is untouched) and the next Start runs a new session on the new policy."""
        events='tick start tick tick gl_pol tick tick start tick tick stop tick tick start tick tick tick'
        for runtime,steps in run_both(events).items():
            with self.subTest(runtime):
                starts=[i for i,row in enumerate(steps) if row['event']=='start']
                self.assertEqual((steps[starts[1]]['obs']['sess'],steps[starts[1]]['obs']['readopt_code']),('HELD',True),
                                 'a Start while Auto is on never ends the hold')
                after_stop=steps[[i for i,row in enumerate(steps) if row['event']=='stop'][-1]+2]['obs']
                self.assertEqual((after_stop['sess'],after_stop['guard'],after_stop['readopt_code'],after_stop['readopt']),('STOPPED','none',False,0))
                self.assertEqual(steps[starts[2]]['reply'],'accepted')
                final=steps[-1]['obs']
                self.assertEqual((final['sess'],final['guard'],final['readopt_code'],final['intent']),('RUNNING','vpn',False,'on'))


if __name__=='__main__':
    unittest.main()
