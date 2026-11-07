"""The Kalman point-PASS count is never presented as a result (paired-bootstrap re-analysis, 07.11.2026).

Paired bootstrap of the 96 registered Kalman hypotheses (private science follow-up, item 60): of the 66 point-PASS,
51 are supported at the old alpha allocation (53 at the IUT level); 9 delay non-inferiority claims (L30, L40, RAMP) are not
supported; 6 (CREEP) are degenerate at the horizon; the method stays CRITERIA_FAIL (no cell is at least 15 % faster).
Current documentation must not state "66 PASS" as a result; dated historical records and releases/*.md are not checked."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ['README.md', 'README.ru.md', 'docs/PRINCIPLES-SCIENCE.en.md', 'docs/PRINCIPLES-SCIENCE.ru.md',
           'docs/HOW-IT-WORKS.en.md', 'docs/HOW-IT-WORKS.ru.md', 'docs/CURRENT-STATUS.md', 'docs/CONTROL-AND-SETUP.md',
           'docs/ROADMAP.md', 'docs/BUILTIN-HELP.en.md', 'docs/BUILTIN-HELP.ru.md', 'docs/ERROR_CODES.md',
           'router/analytics_panel.inc.js', 'router/help_panel.inc.js', 'router/learn_scenes.inc.js']
FORBIDDEN = [
    re.compile(r'(?i)\b66\s*(?:/\s*96\s*)?(?:hypothes[ie]s\s+)?PASS(?:ES|ED)?\b'),
    re.compile(r'(?i)\b66 (?:of|out of) 96\b'),
    re.compile(r'(?i)\b66 из 96\b'),
    re.compile(r'(?i)(?:kalman|калман)[^\n]{0,120}\b66\b[^\n]{0,40}(?:pass|passed|подтвержд|прошл)'),
]
REQUIRED_EN = ['of the 66 point-PASS, 51 are supported at the old α allocation (53 at the IUT level)',
               '9 delay non-inferiority claims (L30, L40, RAMP) are not supported',
               '6 (CREEP) are degenerate at the horizon', 'CRITERIA_FAIL']
REQUIRED_RU = ['из 66 точечных PASS 51 подтверждены при прежнем распределении α (53 на уровне IUT)',
               '9 утверждений о неухудшении задержки (L30, L40, RAMP) не подтверждены',
               '6 (CREEP) вырождены на горизонте', 'CRITERIA_FAIL']


class KalmanWording(unittest.TestCase):
    def test_current_docs_never_present_66_pass_as_a_result(self):
        for rel in CURRENT:
            path = ROOT / rel
            if not path.exists():
                continue
            text = path.read_text(encoding='utf-8')
            for pattern in FORBIDDEN:
                self.assertIsNone(pattern.search(text), '%s: %s' % (rel, pattern.pattern))

    def test_principles_carry_the_corrected_counts(self):
        for rel, required in (('docs/PRINCIPLES-SCIENCE.en.md', REQUIRED_EN), ('docs/PRINCIPLES-SCIENCE.ru.md', REQUIRED_RU)):
            text = (ROOT / rel).read_text(encoding='utf-8')
            for phrase in required:
                self.assertIn(phrase, text, '%s: %s' % (rel, phrase))

    def test_the_forbidden_patterns_catch_the_old_claims(self):
        for sample in ('Kalman: 66 PASS', '66/96 PASS', '66 of 96 hypotheses', '66 из 96 гипотез', 'Калман: 66 прошли'):
            self.assertTrue(any(p.search(sample) for p in FORBIDDEN), sample)
        self.assertFalse(any(p.search('of the 66 point-PASS, 51 are supported') for p in FORBIDDEN))


if __name__ == '__main__':
    unittest.main()
