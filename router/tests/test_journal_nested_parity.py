"""F-39 (07.11.2026): shared nested-journal cases (journal_nested_cases.json). Their verdicts are the Python reader's;
tests/lua/test_journal_nested.lua runs the same cases through lua/journal.lua, and the embedded lifecycle guard must
agree as well, so parity is checked, not assumed."""
import copy
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import native_switch  # noqa: E402

CASES=json.loads((HERE/'journal_nested_cases.json').read_text(encoding='utf-8'))['cases']


class SharedNestedCases(unittest.TestCase):
    def test_verdicts_are_the_python_readers(self):
        self.assertGreaterEqual(len(CASES),40)
        for case in CASES:
            with self.subTest(case=case['name']):
                try:native_switch.validate_journal(copy.deepcopy(case['journal']));accepted=True
                except native_switch.Refused:accepted=False
                self.assertIs(accepted,case['accept'])

    def test_the_lifecycle_guard_agrees(self):
        import lifecycle_guard
        for case in CASES:
            with self.subTest(case=case['name']):
                self.assertIs(lifecycle_guard.valid_journal(copy.deepcopy(case['journal'])),case['accept'])


if __name__=='__main__':unittest.main()
