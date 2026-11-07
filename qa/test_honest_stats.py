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

    def test_two_sided_coverage_subtracts_lower_tail_at_rank_one(self):
        # review F-57: 1..6, q = 0.5, 95 %: interval [X(1), X(6)], coverage P(1 <= B <= 5) = 1 - 2/64 = 62/64
        s = hs.quantile_summary(range(1, 7), q=0.5)
        low, high, cover = s['ci']
        self.assertEqual((low, high), (1.0, 6.0))
        self.assertEqual(cover, 62 / 64)                 # 0.96875, not 63/64 = 0.984375

    def test_nonfinite_observations_do_not_count(self):
        # review F-58: 58 finite samples plus NaN must stay n = 58 and not honest; infinities are excluded the same way
        finite = [float(i) for i in range(1, 59)]
        for extra in ([float('nan')], [float('inf')], [float('-inf')], [float('nan'), float('inf')]):
            s = hs.quantile_summary(finite + extra)
            self.assertEqual(s['n'], 58)
            self.assertFalse(s['honest'])
            self.assertIsNone(s['upper'])
            self.assertEqual(s['max'], 58.0)
        self.assertEqual(hs.quantile_summary([float('nan')])['n'], 0)

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


class WilsonInterval(unittest.TestCase):
    """Reference examples of docs/PRINCIPLES-SCIENCE.en.md section 2.3 (z = 1.959964), recomputed independently."""

    def test_reference_examples(self):
        lo, hi = hs.wilson_interval(3, 3)
        self.assertAlmostEqual(lo, 0.4385, places=3)   # 43.85 %: the guide rounds it down to "about 43.8"
        self.assertEqual(hi, 1.0)
        lo, hi = hs.wilson_interval(59, 59)
        self.assertAlmostEqual(lo, 0.9389, places=3)   # 93.89 %: shown rounded down as 93.8 %
        self.assertEqual(hi, 1.0)
        lo, hi = hs.wilson_interval(0, 10)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.2775, places=3)   # about 27.8 %

    def test_matches_the_closed_form_and_the_history_examples(self):
        self.assertAlmostEqual(hs.wilson_interval(55, 61)[0], 0.8016, places=3)
        self.assertAlmostEqual(hs.wilson_interval(55, 61)[1], 0.9541, places=3)
        self.assertAlmostEqual(hs.wilson_interval(0, 5)[1], 0.4345, places=3)
        self.assertAlmostEqual(hs.wilson_interval(61, 61)[0], 0.9408, places=3)

    def test_properties(self):
        for n in range(1, 40):
            for k in range(n + 1):
                lo, hi = hs.wilson_interval(k, n)
                self.assertTrue(0.0 <= lo <= k / n <= hi <= 1.0, (k, n))
        self.assertLess(hs.wilson_interval(3, 3)[0], hs.wilson_interval(59, 59)[0])   # more data, a narrower interval
        w10, w100 = hs.wilson_interval(5, 10), hs.wilson_interval(50, 100)
        self.assertGreater(w10[1] - w10[0], w100[1] - w100[0])

    def test_undefined_input_gives_nothing(self):
        for k, n in ((0, 0), (1, 0), (4, 3), (-1, 3), (True, 3), (1.5, 3), (1, None)):
            self.assertIsNone(hs.wilson_interval(k, n), (k, n))
            self.assertEqual(hs.format_wilson(k, n), '')

    def test_text(self):
        self.assertEqual(hs.format_wilson(3, 3, 'en'), '43.8–100 %')   # 43.85 rounded down, never up
        self.assertEqual(hs.format_wilson(0, 10, 'en'), '0–27.8 %')
        self.assertEqual(hs.format_wilson(59, 59, 'ru'), '93,8–100 %')
        self.assertEqual(hs.format_wilson(55, 61, 'en'), '80.1–95.5 %')   # 80.155 down, 95.414 up
        self.assertEqual(hs.format_wilson(0, 5, 'en'), '0–43.5 %')        # 43.448 up

    def test_printed_interval_always_contains_the_computed_one(self):
        """Conservative display: printed lower <= computed lower and printed upper >= computed upper, within 0.1 point."""
        for n in range(1, 160):
            for k in range(n + 1):
                lo, hi = hs.wilson_interval(k, n)
                a, b = (float(t) for t in hs.format_wilson(k, n, 'en')[:-2].split('–'))
                self.assertLessEqual(a, round(100 * lo, 6), (k, n))
                self.assertGreaterEqual(b, round(100 * hi, 6), (k, n))
                self.assertLess(100 * lo - a, 0.1 + 1e-9, (k, n))
                self.assertLess(b - 100 * hi, 0.1 + 1e-9, (k, n))


class Wording(unittest.TestCase):
    def test_honest_and_dishonest_text(self):
        self.assertEqual(hs.format_p95(12.34, 80), 'P95≈12.3 (n=80, оценка)')
        self.assertEqual(hs.format_p95(12.34, 59), 'P95≈12.3 (n=59, оценка)')
        self.assertEqual(hs.format_p95(12.34, 59, 'en'), 'P95≈12.3 (n=59, estimate)')
        self.assertTrue(hs.format_p95(12.34, 58).startswith('P95≈12.3 (n=58'))
        self.assertEqual(hs.format_p95(1.9, 4, 'ru'), 'P95≈1.9 (n=4, мало данных: нужно ≥ 59)')
        self.assertEqual(hs.format_p95(1.9, 4, 'en'), 'P95≈1.9 (n=4, too few: needs ≥59)')
        self.assertIn('≥ 47 %', hs.format_max_claim(1.9, 4, 'ru'))
        self.assertIn('95 %', hs.format_max_claim(1.9, 4, 'ru'))
        self.assertIn('≥ 47 % of cases', hs.format_max_claim(1.9, 4, 'en'))

    def test_cell_text(self):
        self.assertEqual(hs.cell_text(4, 1.6, 1.9, 1.9), '4 / 1.6 / ≈1.9 / 1.9 (≥47 %)')
        self.assertEqual(hs.cell_text(59, 1.6, 2.4, 3.1), '59 / 1.6 / ≈2.4 / 3.1')
        self.assertEqual(hs.cell_text(58, 1.6, 2.4, 3.1), '58 / 1.6 / ≈2.4 / 3.1 (≥94 %)')

    def test_cell_text_threshold_follows_confidence(self):
        # review F-60: at 99 % confidence 59 samples are too few (min_n = 90), so the cell must warn
        self.assertEqual(hs.min_n(hs.Q, 0.99), 90)
        self.assertTrue(hs.cell_text(59, 1.6, 2.4, 3.1, conf=0.99).startswith('59 / 1.6 / ≈2.4 / 3.1 (≥'))
        self.assertTrue(hs.cell_text(89, 1.6, 2.4, 3.1, conf=0.99).startswith('89 / 1.6 / ≈2.4'))
        self.assertEqual(hs.cell_text(90, 1.6, 2.4, 3.1, conf=0.99), '90 / 1.6 / ≈2.4 / 3.1')
        self.assertEqual(hs.cell_text(59, 1.6, 2.4, 3.1), '59 / 1.6 / ≈2.4 / 3.1')   # 95 % unchanged


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

    def test_success_proportions_carry_the_wilson_interval(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import build_test_history as th
        page = th.build()[0]
        self.assertIn('Wilson interval', page)
        self.assertIn('интервал Вильсона', page)
        self.assertIn('Success 59 of 59: 95 % Wilson interval 93.8–100 %', th.wilson_title(59, 59))
        self.assertEqual(th.wilson_short(3, 3), ' · 43.8–100 %')
        self.assertEqual(th.wilson_title(0, 0), '')
        self.assertEqual(th.wilson_short(0, 0), '')

    def test_history_page_calls_the_p95_an_estimate_and_names_the_separate_bound(self):
        # review F-59: X(ceil(0.95 n)) is never presented as the 95 % upper bound; the bound is a separate order statistic
        sys.path.insert(0, str(ROOT / 'scripts'))
        import build_test_history as th
        page = th.build()[0]
        self.assertNotIn('is a 95 %-confidence upper bound only when', page)
        self.assertNotIn('надёжен как верхняя граница', page)
        self.assertIn('The P95 shown is an empirical estimate', page)
        self.assertIn('Показанный P95 — эмпирическая оценка', page)
        self.assertIn('computed separately', page)
        self.assertEqual(hs.upper_rank(59), 59)          # at n = 59 the bound is the maximum, the shown P95 is X(57)
        self.assertEqual(hs.quantile_summary(range(1, 60))['rank'], 57)
        self.assertIsNone(hs.upper_rank(58))
        self.assertEqual(hs.upper_rank(200), 196)
        self.assertEqual(hs.format_upper(59, 3.1, 'en'), '95 %-confidence upper bound of the P95: 3.1 (the maximum)')
        self.assertEqual(hs.format_upper(200, 3.1, 'en'), '95 %-confidence upper bound of the P95: X(196) of 200')
        self.assertIn('нужно n ≥ 59', hs.format_upper(58, 3.1, 'ru'))
        honest = {'n': 59, 'median': 1.0, 'p95': 2.0, 'max': 3.0}
        cell = th.fmt_metric_html(honest)
        self.assertIn('an estimate', cell)
        self.assertIn('upper bound of the P95: 3.0 (the maximum)', cell)

    def test_missing_maximum_stays_unknown_and_claims_no_bound(self):
        # review R3-04: the median (1) was put in place of a missing maximum and claimed as the bound of a P95 of 2
        sys.path.insert(0, str(ROOT / 'scripts'))
        import build_test_history as th
        cell = th.fmt_metric_html({'n': 59, 'median': 1, 'p95': 2})
        self.assertNotIn(': 1 (', cell)
        self.assertNotIn('(the maximum)', cell)
        self.assertNotIn('(максимум)', cell)
        self.assertTrue(cell.endswith('/ —'), cell)
        small = th.fmt_metric_html({'n': 10, 'median': 1, 'p95': 2})
        self.assertNotIn('max 1', small)
        self.assertNotIn('≥', small.split('</span>', 1)[1])

    def test_text_cell_keeps_a_missing_p95_or_maximum_unknown(self):
        # the text version (fmt_metric) still put the median in place of a missing P95/maximum after R3-04
        sys.path.insert(0, str(ROOT / 'scripts'))
        import build_test_history as th
        self.assertEqual(th.fmt_metric({'n': 59, 'median': 1, 'p95': 2}), '59 / 1 / 2 / —')
        self.assertEqual(th.fmt_metric({'n': 5, 'median': 1, 'max': 3}), '5 / 1 / — / 3')
        self.assertEqual(th.fmt_metric({'n': 5, 'median': 1, 'p95': None, 'max': None}), '5 / 1 / — / —')
        self.assertEqual(th.fmt_metric({'n': 5, 'median': 1, 'p95': 2, 'max': 3}), '5 / 1 / 2 / 3')
        self.assertEqual(th.fmt_metric_html({'n': 5, 'median': 1}), '5 / 1 / — / —')


if __name__ == '__main__':
    unittest.main()
