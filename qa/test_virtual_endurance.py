import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'lab/endurance_state.py'
spec=importlib.util.spec_from_file_location('endurance_state',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class EnduranceVerdicts(unittest.TestCase):
    def test_explicit_disposable_container_name_rejects_cli_options_and_paths(self):
        self.assertEqual(m.container_name('homensai-vpn-recovery-20261020'),'homensai-vpn-recovery-20261020')
        for value in ('--help','../original','',None,'bad name','x'*129):
            with self.subTest(value=value),self.assertRaises(ValueError):m.container_name(value)
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

class HostSleepAndLostProducer(unittest.TestCase):
    def test_host_sleep_or_clock_jump_is_a_gap_even_when_monotonic_did_not_advance(self):
        self.assertFalse(m.slept((1000,50),(1060,110),60))        # normal sample
        self.assertFalse(m.slept((1000,50),(1085,134),60))        # slow but consistent
        self.assertTrue(m.slept((1000,50),(1000+3600,50+60),60))  # slept an hour, monotonic ignored it
        self.assertTrue(m.slept((1000,50),(900,110),60))          # wall clock stepped back
        self.assertTrue(m.slept((1000,50),(1000+300,50+300),60))  # consistent but far beyond the interval

    def test_lost_producer_needs_consecutive_dead_polls_and_never_passes(self):
        self.assertFalse(m.producer_lost([False,False]))
        self.assertFalse(m.producer_lost([False,False,True]))
        self.assertTrue(m.producer_lost([True,False,False,False]))
        self.assertEqual(m.verdict(100,43200,1,0,0,60),'RUNNING')

    def test_liveness_never_signals_and_rejects_bad_pids(self):
        import os
        self.assertTrue(m.pid_alive(os.getpid()))
        for bad in (0,-1,None,'1',2**31,True.__class__):self.assertFalse(m.pid_alive(bad))
        self.assertTrue(m.pid_alive(os.getpid()))  # still running: the check did not terminate it


if __name__=='__main__':unittest.main()
