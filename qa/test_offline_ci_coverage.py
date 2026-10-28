"""Offline selection must not import lab device scripts or count skipped Lua as run."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from run_offline_ci import lab_exclusions,unittest_counts


class OfflineCoverageTests(unittest.TestCase):
    def test_unittest_skips_are_separate_from_executed_cases(self):
        self.assertEqual(unittest_counts(SimpleNamespace(stderr='Ran 13 tests in 0.1s\nOK (skipped=13)')),(13,13))
        self.assertEqual(unittest_counts(SimpleNamespace(stderr='Ran 1 test in 0.1s\nOK')),(1,0))
        with self.assertRaisesRegex(RuntimeError,'CI-TEST-COUNT-MISSING'):
            unittest_counts(SimpleNamespace(stderr='OK'))

    def test_lab_device_script_is_explicitly_excluded_without_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'lab').mkdir()
            (root/'lab/openwrt_boot_check.py').write_text('raise RuntimeError("must never import")')
            (root/'lab/test_startup_work.py').write_text('')
            self.assertEqual(lab_exclusions(root),['lab/openwrt_boot_check.py'])

    def test_new_lab_test_requires_offline_safety_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'lab').mkdir()
            (root/'lab/test_new_router.py').write_text('')
            with self.assertRaisesRegex(RuntimeError,'CI-LAB-TEST-UNREVIEWED: test_new_router.py'):
                lab_exclusions(root)


if __name__=='__main__':unittest.main()
