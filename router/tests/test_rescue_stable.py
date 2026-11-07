"""rescue_stable: a reserve that failed while carrying hands the traffic back after a short primary stability.

Offline GA/annealing study 03.11.2026 (private/math/evolution, REPORT.ru.md): committed_recovery_decision returned
from a FAILED reserve only after the full primary_stable (native_switch.py, the alpha6 notes said "at once"), and
finish_committed then asked recovery_ready with the same full primary_stable again. Now the failed reserve is left
after min(primary_stable, rescue_stable) seconds (default 10 s, owner range 0..60 s, 0 = the old rule); the default
primary_stable moves 30 -> 120 s only together with it (docs/architecture/RESCUE-STABLE-2026-11-03.ru.md).
Lua twin: tests/lua/test_rescue_stable.lua (rescue_stable_cases.json, the same decisions).
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import native_switch as native  # noqa: E402
import recovery_settings  # noqa: E402
from recovery_settings import normalized, payload, rescue_settings, stable_seconds, RESCUE_REASON  # noqa: E402

CASES=json.loads((HERE/'rescue_stable_cases.json').read_text(encoding='utf-8'))
PRIMARY='wireguard:peer_2002';RESERVE='openvpn:40354_2016'


def fake_backend(ready_upto,reserve_health=True):
    backend=Mock();asked=[]
    def ready(identifier,settings):
        seconds=stable_seconds(settings);asked.append(seconds);return seconds<=ready_upto
    backend.recovery_ready.side_effect=ready
    if reserve_health=='unknown':reserve_health=None
    backend.health.side_effect=lambda identifier:True if identifier==PRIMARY else reserve_health
    return backend,asked


def decide(case,model_asked=None):
    """The reserve's failure comes from the case for every failure model (native.streak for 'consecutive',
    channel_model.channel_failed for the HMM modes); channel_model.return_ready answers model_ready (default true)."""
    backend,asked=fake_backend(case['ready_upto'],case.get('reserve_health',True))
    journal={'source':PRIMARY,'target':RESERVE,'confirmed':900}
    model_asked=[] if model_asked is None else model_asked
    def model_ready(*args,**kwargs):
        model_asked.append(args[1]);return case.get('model_ready',True)
    with patch('failure_diagnosis.resolve_pair',return_value={'coordination':{'state':'READY'},'target':{'id':RESERVE},'source':{'id':PRIMARY}}), \
         patch('fault_control.testing_profile',return_value=False), \
         patch.object(native,'streak',return_value=case['reserve_failed']), \
         patch('channel_model.channel_failed',return_value=case['reserve_failed']), \
         patch('channel_model.return_ready',side_effect=model_ready):
        result=native.committed_recovery_decision(backend,journal,dict(case['settings']),[],case.get('now',1000),{},hold=case.get('hold'))
    return result,asked


class SharedCases(unittest.TestCase):
    def test_normalized(self):
        for case in CASES['normalized']:
            with self.subTest(case['name']):
                policy=normalized(case['settings'])
                self.assertEqual((policy['primary_stable'],policy['rescue_stable']),(case['primary_stable'],case['rescue_stable']))

    def test_stable_seconds(self):
        for case in CASES['stable_seconds']:
            with self.subTest(case['name']):self.assertEqual(stable_seconds(case['settings']),case['seconds'])

    def test_committed_recovery_decisions(self):
        for case in CASES['decisions']:
            with self.subTest(case['name']):
                result,asked=decide(case)
                self.assertEqual((result['action'],result['reason']),(case['action'],case['reason']))
                self.assertEqual(asked[-1] if asked else None,case['asked'])

    def test_return_rule(self):
        """recovery_settings.return_rule == pair.return_rule (Lua): the settings recovery_ready gets and the model gate."""
        from recovery_settings import return_rule
        for case in CASES['return_rule']:
            with self.subTest(case['name']):
                settings=dict(case['settings'])
                ready,gate=return_rule(settings,case['reserve'],case.get('hold'))
                self.assertEqual((stable_seconds(ready),gate),(case['seconds'],case['gate']))
                self.assertEqual(settings,case['settings'],'the owner settings are never changed')
        with self.assertRaisesRegex(ValueError,'return_rule'):return_rule({},'healthy')

    def test_combined_rescue_and_failure_model(self):
        """healthy / failed reserve x hmm / hmm-fast / consecutive: the HMM return gate holds a planned return only;
        a dead reserve is left after the rescue stability whatever the model says."""
        for case in CASES['combined']:
            with self.subTest(case['name']):
                consulted=[]
                result,asked=decide(case,consulted)
                self.assertEqual((result['action'],result['reason']),(case['action'],case['reason']))
                self.assertEqual(asked[-1] if asked else None,case['asked'])
                self.assertEqual(bool(consulted),case['model_asked'])
                if consulted:self.assertEqual(consulted,[PRIMARY],'the gate looks at the primary')

    def test_source_ready(self):
        for case in CASES['source_ready']:
            with self.subTest(case['name']):
                backend,asked=fake_backend(case['ready_upto'])
                self.assertIs(native.source_ready(backend,{'source':PRIMARY},dict(case['settings']),case['reason']),case['ready'])
                self.assertEqual(asked,[case['asked']])


class Units(unittest.TestCase):
    def test_rescue_settings_is_a_copy_with_the_transient_marker(self):
        settings={'recovery_primary_stable':'300'}
        marked=rescue_settings(settings)
        self.assertEqual(marked,{'recovery_primary_stable':'300','rescue_return':True});self.assertEqual(settings,{'recovery_primary_stable':'300'})
        self.assertEqual(RESCUE_REASON,'RESERVE-FAILED-PRIMARY-VERIFIED')
        self.assertNotIn('rescue_return',normalized(marked),'never part of the settings fingerprint')

    def test_setting_saved_optional_and_bounded(self):
        base={'failures':3,'successes':2,'cooldown':60,'min_dwell':60,'return_policy':'healthy_primary','primary_successes':2,'primary_stable':120}
        self.assertNotIn('recovery_rescue_stable',payload(base)['main'],'an older page that does not send it leaves it untouched')
        self.assertEqual(payload(dict(base,rescue_stable=0))['main']['recovery_rescue_stable'],'0')
        self.assertEqual(payload(dict(base,rescue_stable=60))['main']['recovery_rescue_stable'],'60')
        for bad in (61,-1,'10',10.0,True):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'RECOVERY-RANGE'):payload(dict(base,rescue_stable=bad))
        self.assertEqual(recovery_settings.DEFAULTS['primary_stable'],120)
        self.assertEqual(recovery_settings.RANGES['rescue_stable'],(0,60))

    def test_real_recovery_ready_asks_stable_success_for_the_rescue_seconds(self):
        # Linux.recovery_ready over two good samples 10 s apart: enough for the rescue (10 s), not for primary_stable (120 s)
        import failure_diagnosis
        samples=[{'id':'primary','time':985,'code':None,'dns_ok':True,'https_success':2},
                 {'id':'primary','time':995,'code':None,'dns_ok':True,'https_success':2}]
        pair={'coordination':{'state':'READY'},'source':{'id':'primary'},'target':None}
        with patch.object(native,'read_json',return_value={'samples':samples}), \
             patch.object(native.time,'time',return_value=1000), \
             patch.object(failure_diagnosis,'resolve_pair',return_value=pair), \
             patch.object(failure_diagnosis,'scoped_samples',return_value=samples), \
             patch.object(native.Linux,'health',return_value=True):
            self.assertFalse(native.Linux().recovery_ready('primary',{'interval':10}))
            self.assertTrue(native.Linux().recovery_ready('primary',rescue_settings({'interval':10})))
            self.assertFalse(native.Linux().recovery_ready('primary',rescue_settings({'interval':10,'recovery_rescue_stable':'0'})))
            self.assertFalse(native.Linux().recovery_ready('primary',rescue_settings({'interval':10,'recovery_rescue_stable':'11'})))

    def test_finish_committed_after_a_rescue_decision_does_not_hold_on_the_failed_reserve(self):
        """The decision and finish_committed's own source_ready must ask the same (short) stability."""
        backend,asked=fake_backend(10)
        backend.order.return_value=(['b','a'],'h'*64)
        backend.policy.return_value={'settings':{}}
        journal={'source':PRIMARY,'target':RESERVE,'before':['a','b'],'after':['b','a'],'hash':'h'*64,'phase':'COMMITTED'}
        with patch.object(native,'bind_policy_context'),patch('pair_policy.metadata',return_value=None), \
             patch.object(native,'rollback') as rollback,patch.object(native,'journal_write'),patch.object(native,'publish'):
            self.assertTrue(native.finish_committed(backend,dict(journal),RESCUE_REASON))
            rollback.assert_called_once()
            self.assertEqual(asked,[10])
            asked.clear()
            self.assertFalse(native.finish_committed(backend,dict(journal),'PRIMARY-STABLY-RECOVERED'))
            self.assertEqual(asked,[120])


class HoldReserveRescue(unittest.TestCase):
    """Owner decision 07.11.2026 (F-80): hold_reserve holds a WORKING reserve only. A reserve proven failed by a fresh
    probe is rescued to a verified primary (rescue_stable) through the same guarded path; unknown health stays a hold."""
    JOURNAL={'source':PRIMARY,'target':RESERVE,'before':['a','b'],'after':['b','a'],'hash':'h'*64,'phase':'COMMITTED'}

    def finish(self,reserve_health,ready_upto=10,reason=RESCUE_REASON):
        backend,asked=fake_backend(ready_upto,reserve_health)
        backend.order.return_value=(['b','a'],'h'*64)
        backend.policy.return_value={'settings':{'recovery_return_policy':'hold_reserve'}}
        journal=dict(self.JOURNAL)
        with patch.object(native,'bind_policy_context'),patch('pair_policy.metadata',return_value=None), \
             patch.object(native,'rollback') as rollback,patch.object(native,'journal_write'),patch.object(native,'publish'):
            returned=native.finish_committed(backend,journal,reason)
        return returned,journal,asked,rollback

    def test_proven_failed_reserve_is_rescued_to_the_verified_primary(self):
        returned,journal,asked,rollback=self.finish(False)
        self.assertTrue(returned);rollback.assert_called_once();self.assertEqual(asked,[10],'the rescue stability, not primary_stable')

    def test_proven_failed_reserve_waits_for_the_rescue_stability(self):
        returned,journal,asked,rollback=self.finish(False,ready_upto=9)
        self.assertFalse(returned);rollback.assert_not_called()
        self.assertEqual((journal['phase'],journal['reason'],journal['reserve_healthy']),('HELD-ON-RESERVE','SOURCE-NOT-VERIFIED',False))

    def test_unknown_reserve_health_stays_a_hold(self):
        returned,journal,asked,rollback=self.finish('unknown')
        self.assertFalse(returned);rollback.assert_not_called();self.assertEqual(asked,[],'the primary is not asked')
        self.assertEqual((journal['phase'],journal['reason'],journal['reserve_healthy']),('HELD-ON-RESERVE','OPERATOR-HOLD-RESERVE',False))

    def test_working_reserve_is_held_unchanged(self):
        returned,journal,asked,rollback=self.finish(True,ready_upto=600,reason='PRIMARY-STABLY-RECOVERED')
        self.assertFalse(returned);rollback.assert_not_called();self.assertEqual(asked,[])
        self.assertEqual((journal['phase'],journal['reason'],journal['reserve_healthy']),('HELD-ON-RESERVE','OPERATOR-HOLD-RESERVE',True))

    def test_pair_journal_hold_lets_only_the_rescue_reason_through(self):
        """pair_hold_reason (finish_committed of a continuous-pair journal): hold_reserve still holds a planned return;
        the rescue decided by committed_recovery_decision (RESCUE_REASON) returns."""
        from recovery_settings import normalized
        backend,asked=fake_backend(600)
        journal={'source':PRIMARY,'target':RESERVE,'before':['a','b'],'after':['b','a'],'hash':'h'*64}
        context={'primary_order':['a','b'],'session_order':['a','b']}
        recovery=normalized({'recovery_return_policy':'hold_reserve'})
        with patch('pair_policy.role',return_value='source'):
            self.assertEqual(native.pair_hold_reason(backend,journal,['b','a'],context,'PRIMARY-STABLY-RECOVERED',['a','b'],{},recovery),'SOURCE-NOT-VERIFIED')
            self.assertIsNone(native.pair_hold_reason(backend,journal,['b','a'],context,RESCUE_REASON,['a','b'],{},recovery))
            self.assertEqual(asked[-1],10,'the rescue return is proven with rescue_stable')
            backend,asked=fake_backend(9)
            self.assertEqual(native.pair_hold_reason(backend,journal,['b','a'],context,RESCUE_REASON,['a','b'],{},recovery),'SOURCE-NOT-VERIFIED','a primary not yet stable holds')

    def test_rescue_is_bounded_by_the_attempt_budget_not_the_return_hold(self):
        """The rescue ignores the return_hold ledger (rescue_stable_cases 'ignores the damped return_hold'); the next
        failover is charged against the attempt budget, so ping-pong is bounded by attempt_limit per attempt_window."""
        from pair_auto import budget
        from recovery_settings import normalized
        recovery=normalized({'recovery_return_policy':'hold_reserve'})
        self.assertEqual((recovery['attempt_limit'],recovery['attempt_window'],recovery['cooldown']),(3,15,60))
        events=[1000,1100,1200]
        kept,allowed=budget(events,1300,recovery['attempt_window']*60,recovery['attempt_limit'])
        self.assertFalse(allowed,'three failovers in the window: the next forward switch is not dispatched')
        kept,allowed=budget(events,1000+15*60+1,recovery['attempt_window']*60,recovery['attempt_limit'])
        self.assertTrue(allowed,'the window passes: the budget opens again')


if __name__=='__main__':unittest.main()
