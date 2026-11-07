"""Offline selection must not import lab device scripts or count skipped Lua as run."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import json

from run_offline_ci import lab_exclusions,tlc_crosscheck,unittest_counts


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


class TlcCrosscheckReceiptTests(unittest.TestCase):
    def write(self,data):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        path=Path(directory.name)/'tlc.json';path.write_text(json.dumps(data),encoding='utf-8');return path

    def test_not_handed_in_is_recorded_not_hidden(self):
        self.assertEqual(tlc_crosscheck(None)['status'],'NOT-RUN')

    def test_skipped_is_recorded_and_does_not_fail(self):
        result=tlc_crosscheck(self.write({'status':'SKIPPED','reason':'image missing','seconds':0,'configs':{},'problems':[]}))
        self.assertEqual((result['status'],result['reason'],result['states']),('SKIPPED','image missing',{}))

    def test_pass_records_the_state_counts(self):
        result=tlc_crosscheck(self.write({'status':'PASS','seconds':88.5,'configs':{'held-allfix':{'tlc_states':123144}}}))
        self.assertEqual((result['status'],result['seconds'],result['states']),('PASS',88.5,{'held-allfix':123144}))

    def test_fail_is_red_with_the_reason(self):
        with self.assertRaisesRegex(RuntimeError,'CI-TLC-CROSSCHECK-FAILED: held-allfix: states differ'):
            tlc_crosscheck(self.write({'status':'FAIL','problems':['held-allfix: states differ: TLC 1, model.py 2']}))

    def test_unknown_status_is_red(self):
        with self.assertRaisesRegex(RuntimeError,'CI-TLC-CROSSCHECK-STATUS'):
            tlc_crosscheck(self.write({'status':'MAYBE'}))


if __name__=='__main__':unittest.main()
