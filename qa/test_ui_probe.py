"""Fail-closed acceptance and readiness regressions for the local browser persona harness."""
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent/'ui-probe'
spec=importlib.util.spec_from_file_location('fool_check',HERE/'fool_check.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


class PersonaAcceptance(unittest.TestCase):
    def clean(self):
        return dict(persona=1,kind='numbers',steps=1,interactionStarted=True,appAlive=True,attribution=True,footer=True,errors=[],calls=[],callCount=0,nodesStart=100,nodesEnd=100,maxLag=0)

    def test_every_reported_failure_affects_exit_verdict(self):
        self.assertTrue(checker.failed(checker.summarise([])))
        self.assertFalse(checker.failed(checker.summarise([self.clean()])))
        changes=[dict(error='TIMEOUT'),dict(fatal='TOP failure'),dict(errors=['TYPE defect']),dict(appAlive=False),dict(attribution=False),dict(footer=False),dict(steps=0),dict(interactionStarted=False),dict(readinessFailed='final'),dict(callCount=151),dict(maxLag=1501),dict(nodesEnd=301),dict(docOverflow=1),dict(calls=[dict(m='setup_monitor',p=['interval'],a=[0])])]
        for change in changes:
            with self.subTest(change=change):
                row=self.clean();row.update(change)
                self.assertTrue(checker.failed(checker.summarise([row])))

    def test_cli_reports_nonzero_for_failure(self):
        for passed in (True,False):
            row=self.clean();row['appAlive']=passed
            result=subprocess.run([sys.executable,str(HERE/'fool_check.py'),'-'],input=json.dumps([row]),capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0 if passed else 1,result.stdout+result.stderr)

    @unittest.skipUnless(shutil.which('node'),'Browser readiness contract requires Node; covered in the full UI runtime')
    def test_browser_readiness_contract(self):
        result=subprocess.run(['node',str(HERE/'test_fool_readiness.js')],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
