"""Fast checks of the formal-model CI gate logic (tools/formal/ci_check.py). The model itself runs in qa/run_offline_ci.py."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

FORMAL = Path(__file__).resolve().parents[1] / 'formal'
spec = importlib.util.spec_from_file_location('formal_ci_check', FORMAL / 'ci_check.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

EXPECTED = {'variant': 'fix', 'fixed': [], 'known': {
    'TRANSITION:RETURN-BEFORE-HOLD:cl-rec': {'status': 'xfail', 'k': 'K2', 'note': 'x'},
    'LEAK:begin-instant': {'status': 'accepted', 'note': 'by design'},
    'EF-START': {'status': 'accepted', 'note': 'K7', 'profiles': ['faults']},
}}


class Signatures(unittest.TestCase):
    def test_family_names_are_stable_ids(self):
        self.assertEqual(ci.canon_family('begin-instant (between the STARTING write and guard(), no I/O wait)'), 'begin-instant')
        self.assertEqual(ci.canon_family('K3 HELD-ON-RESERVE without guard'), 'k3-held-on-reserve-without-guard')
        self.assertEqual(ci.canon_family('other running'), 'other-running')

    def test_signatures_of_a_result(self):
        result = {'leak_families': {'recovery-window (x)': 5}, 'invariants': {'INCONSISTENT': 2}, 'transition': {'COMMITTED-AFTER-STOP': 3},
                  'ef_stuck': 4, 'liveness_failover': {'bad': 0}, 'liveness_stop_primary_up': {'not_clean': 0},
                  'liveness_stop_primary_down': {'not_clean': 7}}
        self.assertEqual(ci.signatures(result), {'LEAK:recovery-window': 5, 'INCONSISTENT': 2, 'TRANSITION:COMMITTED-AFTER-STOP': 3,
                                                 'EF-START': 4, 'LIVENESS:stop-primary-down': 7})


class Judge(unittest.TestCase):
    def test_green_when_exactly_as_expected(self):
        obs = {'faults': {'TRANSITION:RETURN-BEFORE-HOLD:cl-rec': 3, 'LEAK:begin-instant': 9, 'EF-START': 5}}
        new, xpass, notes = ci.judge(EXPECTED, obs)
        self.assertEqual((new, xpass), ([], []))
        self.assertEqual(len(notes), 3)

    def test_new_violation_is_red(self):
        new, xpass, _ = ci.judge(EXPECTED, {'held': {'TRANSITION:RETURN-BEFORE-HOLD:cl-rec': 1, 'LEAK:running': 4}})
        self.assertEqual(len(new), 1)
        self.assertIn('LEAK:running', new[0])
        self.assertEqual(xpass, [])

    def test_fixed_k_that_comes_back_is_red(self):
        # the K2 entry was deleted when K2 was fixed; if the violation returns it is "new"
        exp = json.loads(json.dumps(EXPECTED))
        del exp['known']['TRANSITION:RETURN-BEFORE-HOLD:cl-rec']
        new, _, _ = ci.judge(exp, {'held': {'TRANSITION:RETURN-BEFORE-HOLD:cl-rec': 3}})
        self.assertEqual(len(new), 1)

    def test_xfail_that_disappears_is_red_xpass(self):
        new, xpass, _ = ci.judge(EXPECTED, {'held': {'LEAK:begin-instant': 1}})
        self.assertEqual(new, [])
        self.assertEqual(len(xpass), 1)
        self.assertIn('K2', xpass[0])

    def test_xpass_check_can_be_skipped_for_a_subset_of_profiles(self):
        new, xpass, _ = ci.judge(EXPECTED, {'held': {'LEAK:begin-instant': 1}}, check_xpass=False)
        self.assertEqual((new, xpass), ([], []))

    def test_profile_scoped_acceptance(self):
        new, _, _ = ci.judge(EXPECTED, {'server': {'EF-START': 1, 'TRANSITION:RETURN-BEFORE-HOLD:cl-rec': 1}})
        self.assertEqual(len(new), 1)
        self.assertIn('listed only for faults', new[0])


class Validation(unittest.TestCase):
    def _load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'e.json'
            p.write_text(json.dumps(data), encoding='utf-8')
            return ci.load_expected(p)

    def test_committed_expected_file_is_valid(self):
        data = ci.load_expected(FORMAL / 'expected.json')
        self.assertEqual(data['variant'], 'fix')
        # 04.11.2026: every K fix of the model is in the code (integ/alpha8), so no xfail is left; a new real finding
        # adds one with its K number (load_expected checks that)
        # 07.11.2026: F32 (outside change held by risk) and T4A (the owner's Stop ends the hold STOPPED) are in the code too
        self.assertEqual(sorted(data['fixed']), sorted(['K1T', 'K2', 'K3', 'K4', 'K5', 'K9', 'K11', 'K12', 'F32', 'T4A']))
        self.assertTrue(all(e['status'] in ('xfail', 'accepted') for e in data['known'].values()))

    def test_xfail_needs_a_k_number(self):
        with self.assertRaises(ValueError):
            self._load({'variant': 'fix', 'fixed': [], 'known': {'X': {'status': 'xfail'}}})

    def test_entry_of_a_fixed_k_must_be_deleted(self):
        with self.assertRaises(ValueError):
            self._load({'variant': 'fix', 'fixed': ['K2'], 'known': {'X': {'status': 'xfail', 'k': 'K2'}}})

    def test_profiles_exist(self):
        for name, entry in ci.load_expected(FORMAL / 'expected.json')['known'].items():
            for p in entry.get('profiles', []):
                self.assertIn(p, ci.PROFILES, name)


if __name__ == '__main__':
    unittest.main()
