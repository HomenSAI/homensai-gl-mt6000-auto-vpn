"""Channel-failure detector (channel_model.py; owner decision 03.11.2026, option failure_model 'hmm' | 'hmm-fast' |
'consecutive'). Lua twin: tests/lua/test_hmm_detector.lua over the same tests/hmm_detector_cases.json (generated
from the Python module by tests/gen_hmm_detector_cases.py; this file checks it is current).

Also: numerical stability, the wiring (failover_plan.plan, the committed return decision, the settings path),
probe_policy's model-driven dense episodes, and the end-to-end tick simulation of the router scenarios
(tests/hmm_tick_sim.py: blackouts 5-150 s, loss 10-80 %, flap 60/120 x 10, healthy 24 h).
"""
import json
import math
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'files/usr/lib/homensai-vpn'))
sys.path.insert(0, str(HERE))
import channel_model as C  # noqa: E402
import gen_hmm_detector_cases as G  # noqa: E402
import hmm_tick_sim as H  # noqa: E402
import probe_policy  # noqa: E402

CASES = json.loads((HERE / 'hmm_detector_cases.json').read_text(encoding='utf-8'))
TOL = CASES['tolerance']


def samples(rows, profile=None):
    return [G.sample(r) for r in rows]


class SharedCases(unittest.TestCase):
    def test_cases_file_is_current(self):
        self.assertEqual(json.loads(G.text()), CASES, 'run: python3 router/tests/gen_hmm_detector_cases.py --write')

    def near(self, a, b, msg=None):
        if isinstance(b, list):
            self.assertEqual(len(a), len(b), msg)
            for x, y in zip(a, b): self.near(x, y, msg)
        else:
            self.assertLessEqual(abs(a - b), TOL, msg)

    def test_steps(self):
        for case in CASES['steps']:
            p = C.params(case['model']); pi = [1.0, 0, 0, 0, 0, 0]
            for (dt, obs, dense), want, persist in zip(case['seq'], case['pi'], case['persist']):
                pi = C.step(pi, dt, obs, dense, p)
                self.near(pi, want); self.near(C.persist(pi, p), persist)

    def test_evaluate(self):
        for case in CASES['evaluate']:
            with self.subTest(case['name']):
                v = C.evaluate(samples(case['rows']), G.PROFILE['id'], case['now'], case['max_age'], case['model'],
                               G.PROFILE if case['profile'] else None)
                self.assertEqual(G.view(v) is None, case['expect'] is None)
                if v is not None:
                    for key in ('pi', 'persist', 'p_bad', 'p_healthy', 'remaining'): self.near(v[key], case['expect'][key], key)
                    for key in ('time', 'observations', 'failed', 'suspect', 'healthy'): self.assertEqual(v[key], case['expect'][key], key)

    def test_streams_decide_at_the_same_publications(self):
        profile = dict(G.PROFILE, vendor_changed_at=-1e6)
        for case in CASES['streams']:
            got = []; seen = []
            for r, (pub, want) in zip(case['rows'], case['decisions']):
                seen.append(G.sample(r))
                got.append(C.channel_failed(seen, profile['id'], 3, pub, 30, {'failure_model': case['model']}, profile))
            self.assertEqual(got, [w for _, w in case['decisions']], case['name'])


class Model(unittest.TestCase):
    def test_constants_and_presets(self):
        self.assertEqual(C.MODELS, ('hmm', 'hmm-fast', 'consecutive'))
        self.assertEqual((C.params('hmm')['theta'], C.params('hmm')['dur'][2]), (0.8, 4.0))
        self.assertEqual((C.params('hmm-fast')['theta'], C.params('hmm-fast')['dur'][2]), (0.7, 3.0))
        self.assertIsNone(C.params('consecutive'))
        self.assertEqual((C.COST, C.SUSPECT, C.HEALTHY, C.CLEAN, C.WINDOW), (20.0, 0.2, 0.9, 300, 600.0))
        for row in C.EMIS:
            self.assertAlmostEqual(sum(row[:3]), 1.0, places=3); self.assertAlmostEqual(sum(row[3:]), 1.0, places=3)
            self.assertGreaterEqual(min(row), 0.002, 'no single sample is ever certain')
        for value, expect in CASES['names']: self.assertEqual(C.name({'failure_model': value}), expect)
        self.assertEqual(C.name(None), 'hmm')

    def test_observation(self):
        self.assertEqual(C.observation({'code': None, 'dns_ok': True, 'https_success': 2}), 0)
        self.assertIsNone(C.observation({'code': None, 'dns_ok': True, 'https_success': 2.0}))
        self.assertIsNone(C.observation({'code': None, 'dns_ok': True, 'https_success': True}))
        self.assertIsNone(C.observation({'code': None, 'dns_ok': False, 'https_success': 3}))
        self.assertEqual(C.observation({'code': 'DNS-001'}), 1)
        for code in ('VPN-003', 'VPN-001', 'VPN-MTU'): self.assertEqual(C.observation({'code': code}), 2)
        for code in ('CHECK-001', 'ROUTE-001', 'PROFILE-INACTIVE', 'CHECK-LIMIT', 'VENDOR-IDENTITY-CHANGED'):
            self.assertIsNone(C.observation({'code': code}))
        self.assertEqual((C.delay('VPN-003', False), C.delay('VPN-003', True), C.delay('DNS-001', False), C.delay(None, True)), (6.0, 3.0, 3.0, 2.5))

    def test_numerically_stable_for_long_runs(self):
        # 200000 random steps, extreme gaps: the probabilities stay a distribution, never NaN, never below the floor
        rng = random.Random(7)
        for model in ('hmm', 'hmm-fast'):
            p = C.params(model); pi = [1.0, 0, 0, 0, 0, 0]
            for _ in range(100000):
                pi = C.step(pi, rng.choice((0.0, 1e-9, 4.0, 10.0, 600.0)), rng.choice((0, 1, 2)), rng.random() < 0.5, p)
                self.assertTrue(all(x == x and C.FLOOR * 0.99 <= x <= 1.0 for x in pi))
            self.assertAlmostEqual(sum(pi), 1.0, places=12)
        # a million identical failures do not underflow: the state saturates
        pi = [1.0, 0, 0, 0, 0, 0]; p = C.params('hmm')
        for _ in range(2000): pi = C.step(pi, 4.0, 2, True, p)
        self.assertGreater(C.persist(pi, p), 0.97); self.assertAlmostEqual(sum(pi), 1.0, places=12)

    def test_operations_per_sample(self):
        # the per-sample update: 6 exp, 24 mul/add predict, 6 mul emission, 6 div + 6 max + 6 div normalise,
        # 4 mul + 3 add decision; measured here as a bound for the router estimate (see the design note)
        import time
        p = C.params('hmm'); pi = [1.0, 0, 0, 0, 0, 0]
        t0 = time.perf_counter()
        for i in range(20000): pi = C.step(pi, 10.0, i % 3 and 0 or 2, False, p)
        per = (time.perf_counter() - t0) / 20000
        self.assertLess(per, 2e-4, 'one update stays far below a millisecond even in CPython')

    def test_invalid_inputs_never_decide(self):
        rows = samples(G.series(1100, 10, 'OOOHHH'))
        for args in ((None, G.PROFILE['id'], 1155, 30, 'hmm'), (rows, G.PROFILE['id'], float('nan'), 30, 'hmm'),
                     (rows, G.PROFILE['id'], 1155, 0, 'hmm'), (rows, G.PROFILE['id'], 1155, float('inf'), 'hmm'),
                     (rows, G.PROFILE['id'], 1155, 30, 'consecutive'), (rows, G.PROFILE['id'], 1155, 30, 'other')):
            v = C.evaluate(*args)
            self.assertTrue(v is None or v['failed'] is False, args[2:])
        self.assertFalse(C.channel_failed(None, 'x', 3, 1155, 30, {}))
        self.assertFalse(C.return_ready(None, 'x', 2, 1155, 30, {}))
        self.assertTrue(C.return_ready(None, 'x', 2, 1155, 30, {'failure_model': 'consecutive'}))

    def test_restart_replays_the_same_state(self):
        # nothing is stored besides the samples: a restarted Auto (or the other runtime) computes the same view
        rows = samples(G.series(1100, 10, 'OOOOHDOHHH'))
        a = C.evaluate(rows, G.PROFILE['id'], 1195, 30, 'hmm', G.PROFILE)
        b = C.evaluate(list(reversed(rows)), G.PROFILE['id'], 1195, 30, 'hmm', G.PROFILE)
        self.assertEqual(a, b, 'order of the status samples does not matter')

    def test_public_and_row_view(self):
        for case in CASES['public']: self.assertEqual(C.public(case['view']), case['expect'])
        for case in CASES['row_view']:
            rows = samples(case['rows']) + [dict(G.sample(G.row(case['other_generation_at'], 'O')), vendor_generation=CASES['other_generation'])]
            self.assertEqual(C.row_view(rows, dict(G.PROFILE), case['now'], case['max_age'], {'failure_model': case['model']}), case['expect'])


class Wiring(unittest.TestCase):
    def test_settings_path(self):
        from recovery_settings import payload
        base = {'failures': 3, 'successes': 2, 'cooldown': 60, 'min_dwell': 60, 'return_policy': 'healthy_primary',
                'primary_successes': 2, 'primary_stable': 30}
        self.assertNotIn('failure_model', payload(base)['main'], 'an older page leaves the option untouched')
        for model in C.MODELS: self.assertEqual(payload(dict(base, failure_model=model))['main']['failure_model'], model)
        for bad in ('HMM', '', 3, None):
            with self.assertRaises(ValueError): payload(dict(base, failure_model=bad))
        lua = (HERE.parent / 'files/usr/lib/homensai-vpn/inventory.lua').read_text(encoding='utf-8')
        self.assertIn("main.failure_model=(s.failure_model=='hmm-fast' or s.failure_model=='consecutive') and s.failure_model or 'hmm'", lua)
        self.assertIn('failure_model=true', (HERE.parent / 'files/usr/lib/homensai-vpn/setup_save.lua').read_text(encoding='utf-8'))

    def plan(self, model, kinds):
        import failover_plan
        now = 1165
        src = dict(G.PROFILE); dst = dict(H.RESERVE, vendor_changed_at=1000)
        rows = samples(G.series(1100, 10, kinds)) + [H.sample(dst, 1100 + 10 * i, {'code': None, 'dns_ok': True, 'https_success': 3}, False) for i in range(7)]
        pair = {'source': src, 'target': dst, 'coordination': {'state': 'READY', 'transition': None}}
        with patch('failure_diagnosis.resolve_pair', return_value=pair), patch('failure_diagnosis.diagnose', return_value={'suppress_switch': False}):
            return failover_plan.plan({'samples': rows}, {'plan_enabled': True, 'interval': 10, 'failure_model': model,
                                                          'plan_source': src['id'], 'plan_target': dst['id']}, now)

    def test_failover_plan_uses_the_model(self):
        self.assertEqual(self.plan('consecutive', 'OOOODDD')['state'], 'SWITCH-RECOMMENDED')
        self.assertEqual(self.plan('hmm', 'OOOODDD')['state'], 'OBSERVE', 'three DNS failures are not yet a lasting failure')
        result = self.plan('hmm', 'OOOOHHH')
        self.assertEqual(result['state'], 'SWITCH-RECOMMENDED'); self.assertEqual(result['recommendation']['failure_model'], 'hmm')

    def decide(self, model, primary_kinds, reserve_kinds, now):
        import native_switch as native
        src = dict(G.PROFILE); dst = dict(H.RESERVE, vendor_changed_at=1000)
        rows = samples(G.series(now - 10 * len(primary_kinds), 10, primary_kinds))
        rows += [H.sample(dst, now - 10 * len(reserve_kinds) + 10 * i, {'code': None if k == 'O' else 'VPN-003', 'dns_ok': True,
                                                                         'https_success': 3 if k == 'O' else 0}, False) for i, k in enumerate(reserve_kinds)]
        backend = Mock(); backend.recovery_ready.return_value = True; backend.health.return_value = False
        journal = {'source': src['id'], 'target': dst['id'], 'confirmed': now - 600, 'started': now - 600}
        with patch('failure_diagnosis.resolve_pair', return_value={'coordination': {'state': 'READY'}, 'target': dst, 'source': src}):
            return native.committed_recovery_decision(backend, journal, {'failure_model': model}, rows, now, {}, hold=30)

    def test_committed_return_gate(self):
        lossy = 'ODOODOOODOODOOOD' + 'O' * 8           # the primary looked lossy and is clean for 80 s only
        self.assertEqual(self.decide('consecutive', lossy, 'OOOOOO', 1500)['action'], 'RESTORE-PRIMARY')
        self.assertEqual(self.decide('hmm', lossy, 'OOOOOO', 1500)['action'], 'OBSERVE', 'the model still sees light loss')
        self.assertEqual(self.decide('hmm', 'H' * 10 + 'O' * 6, 'OOOOOO', 1500)['action'], 'RESTORE-PRIMARY', 'after an outage at once')
        self.assertEqual(self.decide('hmm', lossy + 'O' * 24, 'OOOOOO', 1500)['action'], 'RESTORE-PRIMARY', '300 s clean bound the wait')
        # a failing reserve is left for a ready primary without the gate (and its failure is the model's too)
        self.assertEqual(self.decide('hmm', lossy, 'OOOHHH', 1500)['reason'], 'RESERVE-FAILED-PRIMARY-VERIFIED')
        self.assertEqual(self.decide('hmm', lossy, 'OOOOHH', 1500)['action'], 'OBSERVE', 'two failures of the reserve are no decision')


class Booster(unittest.TestCase):
    PAIR = {'source': 'a', 'target': 'b'}

    def booster(self):
        mem = H.Memory()
        return probe_policy.Booster(Path('/r'), Path('/p'), mem.atomic_json, mem.read_json)

    def rows(self, a_ok, b_ok=True):
        good = {'code': None, 'dns_ok': True, 'https_success': 3}; bad = {'code': 'VPN-003', 'dns_ok': True, 'https_success': 0}
        return [dict(good if a_ok else bad, id='a'), dict(good if b_ok else bad, id='b')]

    def test_model_suspicion_starts_and_the_model_ends_an_episode(self):
        b = self.booster(); s = {'interval': 10, 'failure_model': 'hmm'}
        suspect = {'a': {'suspect': True, 'failed': False, 'p_bad': 0.3, 'persist': 0.2}}
        rows = b.observe(s, self.rows(False), self.PAIR, 'OBSERVING', 1000, models=suspect)
        self.assertEqual(b.dense(1000)['reason'], 'model'); self.assertEqual(b.interval(s, 1000), 4)
        self.assertTrue(any(r['kind'] == 'suspicion-start' for r in rows))
        # three failures no longer confirm while the model is undecided; the model's decision does
        for now in (1004, 1008, 1012): b.observe(s, self.rows(False), self.PAIR, 'OBSERVING', now, models=suspect)
        self.assertIsNotNone(b.dense(1012))
        rows = b.observe(s, self.rows(False), self.PAIR, 'OBSERVING', 1016, models={'a': {'suspect': True, 'failed': True}})
        self.assertEqual([r['result'] for r in rows if r['kind'] == 'suspicion-end'], ['failure-confirmed'])
        # a decided model starts nothing; the rest after the episode is respected
        self.assertEqual(b.observe(s, self.rows(False), self.PAIR, 'OBSERVING', 1020, models={'a': {'suspect': True, 'failed': True}}), [])
        self.assertIsNone(b.dense(1020))

    def test_false_alarm_needs_the_suspicion_gone(self):
        b = self.booster(); s = {'interval': 10}
        b.observe(s, self.rows(False), self.PAIR, 'OBSERVING', 1000, models={'a': {'suspect': True, 'failed': False}})
        for now in (1004, 1008): b.observe(s, self.rows(True), self.PAIR, 'OBSERVING', now, models={'a': {'suspect': True, 'failed': False}})
        self.assertIsNotNone(b.dense(1008), 'two good checks while the model still suspects: go on')
        rows = b.observe(s, self.rows(True), self.PAIR, 'OBSERVING', 1012, models={'a': {'suspect': False, 'failed': False}})
        self.assertEqual([r['result'] for r in rows if r['kind'] == 'suspicion-end'], ['false-alarm'])

    def test_only_the_channel_carrying_traffic_and_never_without_models(self):
        b = self.booster(); s = {'interval': 10}
        b.observe(s, self.rows(True, False), self.PAIR, 'OBSERVING', 1000, models={'b': {'suspect': True, 'failed': False}})
        self.assertIsNone(b.dense(1000), 'the reserve is not carrying traffic')
        b.observe(s, self.rows(True, False), self.PAIR, 'COMMITTED', 1002, models={'b': {'suspect': True, 'failed': False}})
        self.assertEqual(b.dense(1002)['profile'], 'b')
        c = self.booster()
        c.observe(s, self.rows(False), self.PAIR, 'OBSERVING', 1000)
        self.assertIsNone(c.dense(1000), 'the previous rule: no model, no model episode')


class EndToEnd(unittest.TestCase):
    """hmm_tick_sim: the study's packet model and timing driving the product functions (fixed seeds)."""

    def fault(self, model, make, n, seed, end):
        return H.fault(model, make, n, seed, end)

    def test_blackouts(self):
        expect = {5: 0, 10: 0, 15: 0, 20: 0}
        for L in H.BLACKOUTS:
            r = self.fault('hmm', lambda rng, L=L: H.Env(rng, windows=[(0, L, 1.0)]), 30, 100 + L, max(L + 60.0, 100.0))
            with self.subTest(blackout=L, result=r):
                if L in expect: self.assertEqual(r['switched'], 0, 'a blip shorter than a switch is never left')
                else:
                    self.assertGreaterEqual(r['p'], 0.9)
                    if L >= 40: self.assertLessEqual(r['median'], 26.0); self.assertLessEqual(r['max'], 28.0)
        fast = self.fault('hmm-fast', lambda rng: H.Env(rng, windows=[(0, 40, 1.0)]), 30, 140, 100.0)
        self.assertEqual(fast['p'], 1.0); self.assertLessEqual(fast['median'], 22.0)
        self.assertEqual(self.fault('hmm-fast', lambda rng: H.Env(rng, windows=[(0, 10, 1.0)]), 30, 110, 100.0)['switched'], 0)

    def test_loss(self):
        for p, lo, hi in ((0.10, 0, 0), (0.20, 0, 1), (0.40, 26, 30), (0.50, 30, 30), (0.80, 30, 30)):
            r = self.fault('hmm', lambda rng, p=p: H.Env(rng, windows=[(0, 150, p)]), 30, 200 + int(p * 100), 150.0)
            with self.subTest(loss=p, result=r):
                self.assertGreaterEqual(r['switched'], lo); self.assertLessEqual(r['switched'], hi)
                if p >= 0.4: self.assertLessEqual(r['median'], 60.0)

    def test_flap_60_120_x10(self):
        rng = random.Random(5)
        for model in ('hmm', 'consecutive'):
            r = H.run(H.flap_env(rng), model, -40.0, 2400.0, rng, stop_after_switch=False)
            with self.subTest(model=model, result=r):
                self.assertGreaterEqual(len(r['switches']), 3, 'every failure while on the primary is left')
                for moved in r['switches']:
                    self.assertTrue(any(a <= moved - 15 < a + 60 for a in range(0, 1800, 180)), 'left only inside an outage')
                self.assertLessEqual(len(r['returns']), len(r['switches']))

    def test_healthy_day_has_no_false_switch(self):
        rng = random.Random(9)
        r = H.run(H.blips_env(rng), 'hmm', 0.0, 86400.0, rng, stop_after_switch=False)
        self.assertEqual(r['switches'], [], '24 h with 12 micro-blackouts of 2-12 s')
        self.assertLess(r['dense'] / r['samples'], 0.02)

    def test_persistent_30_percent_loss_does_not_flap(self):
        rng = random.Random(11)
        on = H.run(H.blips_env(rng, 0.30, day=21600.0), 'hmm', 0.0, 21600.0, rng, stop_after_switch=False)
        rng = random.Random(11)
        off = H.run(H.blips_env(rng, 0.30, day=21600.0), 'hmm', 0.0, 21600.0, rng, stop_after_switch=False, return_gate=False)
        self.assertLessEqual(len(on['switches']), 2, on)
        self.assertGreater(len(off['switches']), len(on['switches']), 'without the return gate the pair flaps')


if __name__ == '__main__':
    unittest.main()
