"""The empirical P95 is never called a 95 % upper bound (science follow-up 59, 07.11.2026).

Facts checked exactly (Fraction arithmetic of scripts/honest_stats.py):
  * the sample P95 X_(ceil(0.95 n)) covers the true P95 in only 35-57 % of cases for every 59 <= n <= 300;
  * the 95 % upper bound is a different order statistic X_(s): the maximum for 59 <= n <= 92, X_(n-1) for 93 <= n <= 123,
    X_(99) at n = 100, X_(292) at n = 300;
and the current documentation / page sources no longer use wording that presents the sample P95 as a bound."""
import os
import re
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('HONEST_STATS_DIR') or str(ROOT / 'scripts'))
import honest_stats as hs  # noqa: E402

Q95 = Fraction(95, 100)


def coverage_of_rank(n, rank):
    """P(X_(rank) >= true P95) = P(Binomial(n, 0.95) <= rank - 1), exact."""
    return hs.binom_cdf(rank - 1, n, Q95)


class EmpiricalP95IsNotABound(unittest.TestCase):
    def test_sample_p95_coverage_stays_between_35_and_57_percent(self):
        values = {n: coverage_of_rank(n, hs._rank(n, 0.95)) for n in range(59, 301)}
        self.assertTrue(all(Fraction(35, 100) < c < Fraction(58, 100) for c in values.values()))
        self.assertAlmostEqual(float(values[59]), 0.5711, places=4)
        self.assertAlmostEqual(float(values[60]), 0.3527, places=4)
        self.assertAlmostEqual(float(values[100]), 0.3840, places=4)
        self.assertAlmostEqual(float(values[300]), 0.4319, places=4)
        self.assertEqual(min(values, key=values.get), 60)

    def test_upper_bound_ranks(self):
        for n in range(59, 93):
            self.assertEqual(hs.upper_rank(n), n, n)
        for n in range(93, 124):
            self.assertEqual(hs.upper_rank(n), n - 1, n)
        self.assertEqual(hs.upper_rank(124), 122)
        self.assertEqual(hs.upper_rank(100), 99)
        self.assertEqual(hs.upper_rank(300), 292)
        self.assertIsNone(hs.upper_rank(58))
        for n in (59, 60, 61, 100, 300):
            s = hs.upper_rank(n)
            self.assertGreaterEqual(coverage_of_rank(n, s), Fraction(95, 100))
            self.assertLess(coverage_of_rank(n, s - 1), Fraction(95, 100))
            self.assertGreater(s, hs._rank(n, 0.95), 'the bound is a higher rank than the empirical P95')

    def test_format_p95_never_says_bound(self):
        for n in (10, 59, 60, 100, 300):
            for lang in hs.LANGS:
                text = hs.format_p95(1.0, n, lang)
                self.assertNotRegex(text, r'(?i)bound|границ|guarant|гарант')


FORBIDDEN = [
    re.compile(r'(?i)honest P95'),
    re.compile(r'(?i)honest-P95 (?:recovery|panel)'),
    re.compile(r'(?i)честн\w* P95'),
    re.compile(r'(?i)P95 is a guaranteed'),
    re.compile(r'(?i)named P95 only'),
    re.compile(r'call a value "P95" only'),
    re.compile(r'называет значение «P95», только'),
    re.compile(r'«P95» только при n'),
]
CURRENT = ['README.md', 'README.ru.md', 'docs/PRINCIPLES-SCIENCE.en.md', 'docs/PRINCIPLES-SCIENCE.ru.md',
           'docs/HOW-IT-WORKS.en.md', 'docs/HOW-IT-WORKS.ru.md', 'docs/CURRENT-STATUS.md', 'docs/CONTROL-AND-SETUP.md',
           'docs/ROADMAP.md', 'docs/BUILTIN-HELP.en.md', 'docs/BUILTIN-HELP.ru.md', 'router/analytics_panel.inc.js',
           'router/help_panel.inc.js', 'router/learn_scenes.inc.js', 'scripts/honest_stats.py']


class CurrentWording(unittest.TestCase):
    def test_no_wording_presents_the_sample_p95_as_a_bound(self):
        for rel in CURRENT:
            text = (ROOT / rel).read_text(encoding='utf-8')
            for pattern in FORBIDDEN:
                self.assertIsNone(pattern.search(text), '%s: %s' % (rel, pattern.pattern))

    def test_principles_name_the_bound_ranks_and_autocorrelation(self):
        en = (ROOT / 'docs/PRINCIPLES-SCIENCE.en.md').read_text(encoding='utf-8')
        ru = (ROOT / 'docs/PRINCIPLES-SCIENCE.ru.md').read_text(encoding='utf-8')
        self.assertIn('between 35 % and 57 %', en)
        self.assertIn('между 35 % и 57 %', ru)
        for text in (en, ru):
            self.assertIn('X_(292)', text)
            self.assertIn('59 ≤ n ≤ 92', text)
        self.assertIn('autocorrelated', en)
        self.assertIn('автокоррелированы', ru)


if __name__ == '__main__':
    unittest.main()
