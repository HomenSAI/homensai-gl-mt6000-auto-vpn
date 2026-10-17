import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'lab/endurance_state.py'
spec=importlib.util.spec_from_file_location('endurance_state',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class EnduranceVerdicts(unittest.TestCase):
    def test_running_stopped_failures_gaps_and_incomplete_samples_never_pass(self):
        self.assertEqual(m.verdict(43199,43200,720,0,0,60),'RUNNING')
        for samples,failures,gaps in [(720,1,0),(720,0,1),(10,0,0)]:self.assertEqual(m.verdict(43200,43200,samples,failures,gaps,60),'FAIL')
        self.assertEqual(m.verdict(43200,43200,720,0,0,60,True),'STOPPED')
        self.assertEqual(m.verdict(43200,43200,720,0,0,60),'PASS')
    def test_version_staleness_auto_or_changed_code_is_failure(self):
        expected={'version':'v','code_hashes':{'a':'b'}};sample={'version':'v','code_hashes':{'a':'b'},'age':1,'error':None,'monitor_instances':1,'auto_off':True,'protected':'p','own_config':'c'}
        self.assertEqual(m.sample_errors(sample,expected,sample),[])
        for key,value in [('age',91),('age',-1),('auto_off',False),('version','old'),('code_hashes',{}),('monitor_instances',2),('protected','changed')]:
            row=dict(sample);row[key]=value;self.assertTrue(m.sample_errors(row,expected,sample))
