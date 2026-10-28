"""Real pair decisions must use current policy and the configured scan cadence."""
import copy
import json
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import native_switch as native
import pair_auto as pair
import pair_manual as manual
import test_pair_manual_directions as fixture
from vendor_fixture import attach

RECOVERY_READY=native.Linux.recovery_ready
LINUX=native.Linux


class Decisions(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PairManualDirections()
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        case=self.case
        case.current=['s','t'];case.kernel_order=list(case.current);case.kernel_applied=True
        case.state.update(order=list(case.current),ran=True)
        pair.save(case.state)
        for role in ('source','target'):
            case.selection[role]['vendor_changed_at']=fixture.NOW-10000
            case.settings['plan_'+role]=case.selection[role]['id']
            case.settings['plan_'+role+'_tunnel']=case.selection[role]['vendor_tunnel_id']
        case.settings['interval']=10
        # OS/vendor inputs are synthetic; decisions, scoped samples, recovery
        # readiness, child transaction, journal and control fencing are real.
        case.backend.recovery_ready.side_effect=lambda identifier,settings:RECOVERY_READY(case.backend,identifier,settings)
        self.stack.enter_context(patch.object(pair,'network',return_value=[]))
        self.stack.enter_context(patch.object(pair,'configs',return_value={}))
        self.attempt=self.stack.enter_context(patch.object(native,'attempt',wraps=native.attempt))

    def status(self,now,age=0,failed=True):
        case=self.case;stamp=now-age
        rows=[copy.deepcopy(case.selection[role]) for role in ('source','target')]
        rows[0].update(code='VPN-003' if failed else None,dns_ok=True,https_success=0 if failed else 2)
        rows[1].update(code=None,dns_ok=True,https_success=2)
        samples=[dict(id=row['id'],time=stamp-i*30,code=row['code'],dns_ok=row['dns_ok'],https_success=row['https_success'])
                 for row in rows for i in range(3)]
        status=attach(dict(profiles=rows,samples=samples),stamp)
        for row in status['profiles']:row['vendor_changed_at']=fixture.NOW-10000
        for group in status['vendor_observation']['groups']:group['changed_at']=fixture.NOW-10000
        agent.atomic_json(case.runtime/'status.json',status)
        return status

    def tick(self,now):
        with patch.object(native.time,'time',return_value=now):
            self.assertTrue(pair.tick(self.case.backend,self.case.settings,self.case.revision))

    def test_verified_failback_finishes_one_decision_without_second_attempt(self):
        case=self.case;now=fixture.NOW
        self.status(now);self.tick(now)
        self.assertEqual(native.journal_read()['phase'],'COMMITTED')
        self.assertEqual(case.current,['t','s']);self.assertEqual(self.attempt.call_count,1)
        budget=agent.read_json(case.persist/'pair-auto-budget.json')
        self.status(now+10,failed=False);self.tick(now+10)
        self.assertEqual(case.current,['t','s'],'minimum dwell still holds the reserve')
        applied=case.backend.apply.call_count
        self.status(now+71,failed=False);self.tick(now+71)
        self.assertEqual(case.current,['s','t'],case.publish.call_args.args[0])
        self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        self.assertEqual(self.attempt.call_count,1,'restored primary cannot dispatch another pair_return')
        self.assertEqual(case.backend.apply.call_count,applied+1)
        self.assertEqual(agent.read_json(case.persist/'pair-auto-budget.json'),budget)
        self.assertEqual(pair.read_state()['phase'],'RUNNING')
        self.assertEqual(pair.read_state()['selected_policy']['role'],'source')
        final=case.publish.call_args.args[0]
        self.assertEqual(final['state'],'ROLLED-BACK');self.assertTrue(final['kernel_proof']['verified'])
        self.assertEqual(final['kernel_proof']['role'],'source')
        self.tick(now+72)
        self.assertEqual(case.publish.call_args.args[0]['state'],'OBSERVING')
        self.assertEqual(pair.read_state()['phase'],'RUNNING')
        self.assertEqual(self.attempt.call_count,1)
        self.assertEqual(case.backend.apply.call_count,applied+1)
        self.assertEqual(agent.read_json(case.persist/'pair-auto-budget.json'),budget)

    def test_auto_uses_age_100_failure_and_healthy_reserve_with_interval_300(self):
        self.case.settings['interval']='300'
        original=self.status(fixture.NOW,age=100)
        self.tick(fixture.NOW)
        self.assertEqual(native.journal_read().get('phase'),'COMMITTED',self.case.publish.call_args.args[0])
        self.assertEqual(self.case.current,['t','s']);self.assertEqual(self.attempt.call_count,1)
        self.assertEqual(agent.read_json(self.case.runtime/'status.json'),original)

    def test_primary_fails_fresh_return_check_without_another_attempt_in_same_tick(self):
        case=self.case;now=fixture.NOW
        self.status(now);self.tick(now)
        self.status(now+10,failed=False);self.tick(now+10)
        applied=case.backend.apply.call_count;budget=agent.read_json(case.persist/'pair-auto-budget.json')
        self.status(now+71,failed=False)
        # The decision sees a healthy primary; finish_committed's independent
        # bound health check then observes its failure. Keep the real decisions.
        case.backend.health.side_effect=[True,False,True]
        self.tick(now+71)
        self.assertEqual(native.journal_read()['phase'],'HELD-ON-RESERVE')
        self.assertEqual(case.current,['t','s']);self.assertEqual(self.attempt.call_count,1)
        self.assertEqual(case.backend.apply.call_count,applied)
        self.assertEqual(agent.read_json(case.persist/'pair-auto-budget.json'),budget)
        final=case.publish.call_args.args[0]
        self.assertEqual(final['state'],'DEGRADED-ON-RESERVE');self.assertEqual(final['reason'],'SOURCE-NOT-VERIFIED')

    def test_lost_final_kernel_attestation_cannot_publish_successful_return(self):
        case=self.case;now=fixture.NOW
        self.status(now);self.tick(now)
        self.status(now+71,failed=False)
        proof=case.kernel_proof
        def changed_after_restore(selection=None):
            value=proof(selection)
            if native.journal_read().get('phase')=='ROLLED-BACK':value['verified']=False
            return value
        case.backend.attest_policy.side_effect=changed_after_restore
        self.tick(now+71)
        self.assertEqual(self.attempt.call_count,1)
        self.assertEqual(pair.read_state()['phase'],'HELD')
        final=case.publish.call_args.args[0]
        self.assertEqual(final['state'],'BLOCKED');self.assertEqual(final['blockers'],['ROLLBACK-UNVERIFIED'])

    def test_long_cadence_expires_after_900_seconds(self):
        self.case.settings['interval']='300';self.status(fixture.NOW,age=901);self.tick(fixture.NOW)
        self.attempt.assert_not_called();self.assertEqual(self.case.current,['s','t'])
        self.assertEqual(self.case.publish.call_args.args[0]['reason'],'OBSERVATION-STALE')

    def test_short_cadence_rejects_age_31_and_future_health(self):
        for age in (31,-1):
            with self.subTest(age=age):
                self.status(fixture.NOW,age=age);self.tick(fixture.NOW)
                self.attempt.assert_not_called();self.assertEqual(self.case.current,['s','t'])
                self.assertEqual(self.case.publish.call_args.args[0]['reason'],'OBSERVATION-STALE')

    def test_plan_and_explanation_agree_with_configured_health_age(self):
        from failover_plan import plan
        from failure_diagnosis import explain
        self.case.settings.update(interval=300,plan_enabled=True)
        status=self.status(fixture.NOW,age=100)
        self.assertEqual(plan(status,self.case.settings,fixture.NOW)['state'],'SWITCH-RECOMMENDED')
        explained=explain(status,self.case.settings,fixture.NOW)
        self.assertFalse(explained['diagnosis']['suppress_switch'])
        self.assertTrue(explained['source_failure_streak_met']);self.assertTrue(explained['reserve_success_streak_met'])
        self.case.settings['interval']=10
        self.assertEqual(plan(status,self.case.settings,fixture.NOW)['state'],'OBSERVATION-STALE')
        self.assertTrue(explain(status,self.case.settings,fixture.NOW)['diagnosis']['suppress_switch'])

    def test_legacy_manual_hold_releases_when_selected_channel_has_valid_failure_streak(self):
        case=self.case;case.settings['interval']='300'
        case.current=['t','s'];case.kernel_order=list(case.current)
        state=pair.read_state();state['manual_hold']='target';pair.save(state)
        journal=dict(phase='COMMITTED',confirmed=fixture.NOW-200,source=fixture.SOURCE,target=fixture.TARGET,
                     before=['s','t'],after=['t','s'],hash=case.fingerprint)
        status=self.status(fixture.NOW,age=100,failed=False)
        for row in status['profiles']+status['samples']:
            if row['id']==fixture.TARGET:row.update(code='VPN-003',https_success=0)
        self.assertFalse(manual.held_reserve(case.backend,state,journal,case.settings,status))
        self.assertNotIn('manual_hold',pair.read_state())
        self.attempt.assert_not_called();case.backend.apply.assert_not_called()

    def test_native_supervisor_passes_configured_cadence_into_its_decision(self):
        case=self.case;settings=case.settings
        settings.update(interval='300',native_enabled='1',native_session_loss='1')
        state=pair.read_state();state['phase']='STOPPED';pair.save(state)
        pair.paths()[0].unlink()
        self.status(fixture.NOW,age=100)
        for name in ('ATTEMPTS','PREPARE','JOURNAL_ALARM'):
            self.stack.enter_context(patch.object(native,name,case.persist/(name.lower()+'.json')))
        self.stack.enter_context(patch.object(native,'PROOF_SCOPE',native.PROOF_SCOPE))
        self.stack.enter_context(patch.object(native.time,'sleep'))
        agent.atomic_json(native.ATTEMPTS,dict(until=fixture.NOW+180,count=0,trial=settings['native_trial'],time=fixture.NOW-200))
        certificate=dict(hash=case.selection['hash'],source=fixture.SOURCE,target=fixture.TARGET,
            direction=case.selection['direction'],until=fixture.NOW+180,settings_hash=case.selection['settings_hash'],
            vendor_identity=case.selection['vendor_identity'],proof_scope=pair.MODE)
        agent.atomic_json(native.CERT,certificate)
        def finish(*args,**kwargs):native.STOP=True
        self.attempt.side_effect=finish
        case.publish.side_effect=finish
        native.serve()
        self.attempt.assert_called_once()
        self.assertIs(self.attempt.call_args.args[3],False,'exercise certified Auto, not a forced trial')
        evidence=self.attempt.call_args.kwargs['probe_evidence']
        self.assertTrue(evidence['source_streak_met']);self.assertTrue(evidence['reserve_streak_met'])

    def test_malformed_cadence_still_fails_actual_linux_diagnostic_before_forward(self):
        from test_native_switch import Backend
        platform=Backend();router=LINUX();read=native.read_json
        status=attach(dict(profiles=copy.deepcopy(platform.profiles),samples=[]),fixture.NOW)
        with patch.object(router,'policy',return_value=platform.data), \
                patch.object(router,'acceleration',return_value={'loaded':[],'hnat_runtime':'disabled'}), \
                patch.object(native,'inventory',return_value={'profiles':platform.profiles,'servers':[]}), \
                patch.object(native,'read_json',side_effect=lambda path,default=None:status if Path(path).name=='status.json' else read(path,default)), \
                patch.object(native,'command',return_value=json.dumps({'board_name':'glinet,gl-mt6000'}).encode()):
            self.case.backend.diagnostic.side_effect=router.diagnostic
            for interval in ('bad',None,[],{},float('nan'),float('inf')):
                with self.subTest(interval=interval):
                    platform.data['settings']['interval']=interval
                    self.case.settings['interval']=interval
                    self.tick(fixture.NOW)
                    self.assertIn('OBSERVATION-STALE',self.case.publish.call_args.args[0]['blockers'])
                    self.attempt.assert_not_called();self.case.backend.apply.assert_not_called()


class DiagnosisCadence(unittest.TestCase):
    def status(self,age):
        return dict(time=1000-age,observation_valid_for=900,profiles=[dict(id='source',interface='wgclient1',
            time=1000-age,code='VPN-003',dns_ok=True,https_success=0)])

    def test_cached_cadence_and_explicit_settings_have_the_same_boundaries(self):
        from failure_diagnosis import diagnose
        self.assertFalse(diagnose(self.status(100),'source',1000)['suppress_switch'])
        for interval,age,blocked in ((300,900,False),(300,901,True),(10,30,False),(10,31,True),(300,-1,True)):
            with self.subTest(interval=interval,age=age):
                status=self.status(age);original=copy.deepcopy(status)
                self.assertIs(diagnose(status,'source',1000,{'interval':interval})['suppress_switch'],blocked)
                self.assertEqual(status,original)

    def test_invalid_interval_does_not_inherit_a_longer_cached_ttl(self):
        from failure_diagnosis import diagnose
        for interval in (None,'bad',True,False,0,9,301,300.0,[],{},'9999'):
            with self.subTest(interval=interval):
                self.assertTrue(diagnose(self.status(91),'source',1000,{'interval':interval})['suppress_switch'])
                self.assertFalse(diagnose(self.status(90),'source',1000,{'interval':interval})['suppress_switch'])
        for stamp in (1001,True,None,float('nan')):
            status=self.status(0);status['profiles'][0]['time']=stamp
            self.assertTrue(diagnose(status,'source',1000,{'interval':300})['suppress_switch'])


if __name__=='__main__':unittest.main()
