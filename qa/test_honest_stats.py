"""Exact-value and simulation checks for scripts/honest_stats.py (the 59-sample rule) and its use on the history page."""
import os
import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('HONEST_STATS_DIR') or str(ROOT / 'scripts'))  # the mutation check points this at a mutant
import honest_stats as hs  # noqa: E402


class ExactBinomial(unittest.TestCase):
    def test_known_cdf_values(self):
        self.assertEqual(hs.binom_cdf(3, 10, Fraction(1, 2)), Fraction(176, 1024))
        self.assertEqual(hs.binom_cdf(0, 5, 0.95), Fraction(1, 20) ** 5)
        self.assertEqual(hs.binom_cdf(-1, 5, 0.5), 0)
        self.assertEqual(hs.binom_cdf(5, 5, 0.5), 1)
        # P(B <= 1), B ~ Bin(10, 1/2) = 11/1024
        self.assertEqual(hs.binom_cdf(1, 10, 0.5), Fraction(11, 1024))

    def test_the_59_sample_rule_is_exact(self):
        self.assertEqual(hs.MIN_N, 59)
        self.assertGreater(Fraction(19, 20) ** 58, Fraction(1, 20))
        self.assertLess(Fraction(19, 20) ** 59, Fraction(1, 20))
        self.assertEqual(hs.min_n(0.95, 0.95), 59)
        self.assertEqual(hs.min_n(0.5, 0.95), 5)      # median: 0.5**5 = 0.031 < 0.05, 0.5**4 = 0.0625 is not
        self.assertEqual(hs.min_n(0.99, 0.95), 299)   # the classic "rule of 300"
        self.assertEqual(hs.min_n(0.95, 0.99), 90)    # 0.95**90 = 0.0099 < 0.01

    def test_min_n_boundary_is_inclusive(self):
        # q**n == 1 - conf exactly: 0.5**4 = 1/16 -> four samples are enough (a strict comparison would need five)
        self.assertEqual(hs.min_n(0.5, Fraction(15, 16)), 4)

    def test_ci_ranks_match_a_plain_reference(self):
        def reference(n, q, conf):
            q, conf = Fraction(str(q)), Fraction(str(conf))
            half = (1 - conf) / 2
            pmf = [Fraction(__import__('math').comb(n, i)) * q ** i * (1 - q) ** (n - i) for i in range(n + 1)]
            low = high = None
            for r in range(1, n + 1):
                if sum(pmf[:r]) <= half:
                    low = r
            for s in range(n, 0, -1):
                if sum(pmf[:s]) >= 1 - half:
                    high = s
            return low, high
        for n in list(range(5, 41)) + [59, 72, 100]:
            for q in (0.5, 0.9, 0.95):
                vals = [float(i) for i in range(1, n + 1)]
                low, high, _c = hs.quantile_summary(vals, q=q)['ci']
                want = reference(n, q, 0.95)
                self.assertEqual((low, high), tuple(None if w is None else float(w) for w in want), (n, q))

    def test_max_confidence_and_coverage(self):
        self.assertAlmostEqual(hs.max_confidence(1), 0.05, places=12)
        self.assertAlmostEqual(hs.max_confidence(4), 1 - 0.95 ** 4, places=12)      # 0.1855
        self.assertAlmostEqual(hs.max_confidence(59), 1 - 0.95 ** 59, places=12)    # 0.9515 >= 0.95
        self.assertGreaterEqual(hs.max_confidence(59), 0.95)
        self.assertLess(hs.max_confidence(58), 0.95)
        self.assertAlmostEqual(hs.max_coverage(1), 0.05, places=12)
        self.assertAlmostEqual(hs.max_coverage(4), 0.05 ** 0.25, places=12)         # 0.4729
        self.assertEqual([hs.coverage_percent(n) for n in (1, 4, 14, 20, 58, 59, 100)], [5, 47, 80, 86, 94, 95, 97])
        # coverage and confidence are the same fact: at n = 59 the maximum covers the P95 with >= 95 % confidence
        self.assertGreaterEqual(hs.max_coverage(59), 0.95)
        self.assertLess(hs.max_coverage(58), 0.95)

    def test_median_ci_matches_the_textbook_interval(self):
        # n = 10, q = 0.5, 95 %: [X(2), X(9)], coverage 0.9785
        s = hs.quantile_summary(range(1, 11), q=0.5)
        low, high, cover = s['ci']
        self.assertEqual((low, high), (2.0, 9.0))
        self.assertAlmostEqual(cover, 1 - 2 * 0.0107421875, places=9)
        self.assertEqual(s['value'], 5.0)

    def test_p95_summary_bounds(self):
        s = hs.quantile_summary(range(1, 60))
        self.assertTrue(s['honest'])
        self.assertEqual((s['n'], s['value'], s['max'], s['rank']), (59, 57.0, 59.0, 57))
        self.assertEqual(s['upper'], 59.0)            # the maximum is the 95 % upper bound exactly from n = 59
        self.assertEqual(hs.quantile_summary(range(1, 59))['upper'], None)
        self.assertFalse(hs.quantile_summary(range(1, 59))['honest'])
        # two-sided 95 % needs more: q**n <= 0.025 -> n = 72
        self.assertIsNone(hs.quantile_summary(range(1, 72))['ci'][1])
        self.assertEqual(hs.quantile_summary(range(1, 73))['ci'][1], 72.0)

    def test_small_sample_p95_is_the_maximum(self):
        for n in range(1, 20):
            s = hs.quantile_summary([float(i) for i in range(n)])
            self.assertEqual(s['value'], s['max'])
        self.assertEqual(hs.quantile_summary(list(range(20)))['rank'], 19)    # n = 20: second largest
        self.assertEqual(hs.quantile_summary(list(range(21)))['rank'], 20)
        self.assertEqual(hs.quantile_summary([])['value'], None)
        self.assertEqual(hs.quantile_summary([True, 'x', None])['n'], 0)

    def test_ci_coverage_by_simulation(self):
        # distribution-free: lognormal samples, true P90 known; the two-sided 95 % interval must cover it >= ~95 %
        rng = random.Random(20261103)
        from math import exp
        true_q90 = exp(1.2815515655446004)
        n, trials, hit = 100, 1500, 0
        for _ in range(trials):
            s = hs.quantile_summary([rng.lognormvariate(0, 1) for _ in range(n)], q=0.9)
            low, high, _c = s['ci']
            hit += (low <= true_q90 <= high)
        self.assertGreaterEqual(hit / trials, 0.93)
        # the maximum of 14 samples covers >= 0.05**(1/14) of the distribution in >= 95 % of trials
        p = hs.max_coverage(14)
        ok = sum(1 for _ in range(4000) if max(rng.random() for _ in range(14)) >= p)
        self.assertGreaterEqual(ok / 4000, 0.93)
        self.assertLessEqual(ok / 4000, 0.97)


class Wording(unittest.TestCase):
    def test_honest_and_dishonest_text(self):
        self.assertEqual(hs.format_p95(12.34, 80), 'P95=12.3 (n=80)')
        self.assertEqual(hs.format_p95(12.34, 59), 'P95=12.3 (n=59)')
        self.assertTrue(hs.format_p95(12.34, 58).startswith('P95≈12.3 (n=58'))
        self.assertEqual(hs.format_p95(1.9, 4, 'ru'), 'P95≈1.9 (n=4, мало данных: нужно ≥ 59)')
        self.assertEqual(hs.format_p95(1.9, 4, 'en'), 'P95≈1.9 (n=4, too few: needs ≥59)')
        self.assertIn('≥ 47 %', hs.format_max_claim(1.9, 4, 'ru'))
        self.assertIn('95 %', hs.format_max_claim(1.9, 4, 'ru'))
        self.assertIn('≥ 47 % of cases', hs.format_max_claim(1.9, 4, 'en'))

    def test_cell_text(self):
        self.assertEqual(hs.cell_text(4, 1.6, 1.9, 1.9), '4 / 1.6 / ≈1.9 / 1.9 (≥47 %)')
        self.assertEqual(hs.cell_text(59, 1.6, 2.4, 3.1), '59 / 1.6 / 2.4 / 3.1')
        self.assertEqual(hs.cell_text(58, 1.6, 2.4, 3.1), '58 / 1.6 / ≈2.4 / 3.1 (≥94 %)')


class HistoryPage(unittest.TestCase):
    def test_every_p95_in_the_published_history_is_marked(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import build_test_history as th
        data = th.build()[2]
        page = th.build()[0]
        total = marked = honest = 0
        for r in data['results']:
            for m in (r.get('metrics') or {}).values():
                if m.get('p95') is not None:
                    total += 1
                    honest += m.get('n', 0) >= hs.MIN_N
        for c in data['charts']:
            for s in c['series']:
                for p in s['points']:
                    if p.get('p95') is not None:
                        total += 1
                        honest += p['n'] >= hs.MIN_N
        self.assertGreater(total, 0)
        self.assertEqual(th.p95_counts(data), (total, total - honest))
        self.assertIn('class="p95w"', page)
        self.assertIn('мало данных: нужно', page)
        self.assertIn('too few: needs', page)


if __name__ == '__main__':
    unittest.main()
