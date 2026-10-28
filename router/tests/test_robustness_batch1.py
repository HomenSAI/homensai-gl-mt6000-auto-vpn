"""Batch 1 of the project review: data safety of the statistics reset, clock steps and transient errors."""
from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,stats_reset,pair_auto
from latency_history import LatencyHistory
from native_history import History


def history_with_attempts(folder):
    history=History(folder,detail_days=7)
    data={'sequence':3,'events':[],'months':{'2026-10':{'attempts':3}},'days':{},'last_key':None,'last_time':900.0,'timezone':'Europe/Berlin',
          'counter_version':2,'totals':{'attempts':3},'counted':{}}
    agent.atomic_json(history.path,history.envelope(data))
    return history


class ResetDataSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.persist=Path(self.temp.name)
        p=patch('retention_settings.configured_days',return_value=7);p.start();self.addCleanup(p.stop)

    def test_failed_archive_leaves_history_on_disk_untouched(self):
        history=history_with_attempts(self.persist);before=history.path.read_bytes()
        def writer(path,value):
            if 'stats-archive' in str(path):raise OSError('No space left on device')
            agent.atomic_json(path,value)
        with patch('speed_test.load_history',return_value={'results':[]}):
            _,_,result=stats_reset.apply({'scope':'all','nonce':'b'*32},agent.Accounting(),LatencyHistory(),1000,writer,persist=self.persist)
        self.assertFalse(result['done'])
        self.assertEqual(history.path.read_bytes(),before,'archive first: nothing on disk is reset when the archive fails')

    def test_corrupt_speed_history_is_a_coded_failure_not_a_crash(self):
        from speed_test import SpeedError
        history=history_with_attempts(self.persist);before=history.path.read_bytes()
        with patch('speed_test.load_history',side_effect=SpeedError('SPEED-HISTORY-CORRUPT')):
            _,_,result=stats_reset.apply({'scope':'all','nonce':'c'*32},agent.Accounting(),LatencyHistory(),1000,agent.atomic_json,persist=self.persist)
        self.assertFalse(result['done']);self.assertEqual(result['code'],'SPEED-HISTORY-CORRUPT')
        self.assertEqual(history.path.read_bytes(),before)

    def test_archive_total_size_is_bounded(self):
        with patch.object(stats_reset,'ARCHIVE_BYTES',3000):
            for index in range(5):stats_reset.archive(self.persist,'latency',{'pad':'x'*1000,'n':index},1000+index,agent.atomic_json)
        saved=sorted((self.persist/'stats-archive').glob('*.json'))
        self.assertLessEqual(sum(p.stat().st_size for p in saved),3000+1200);self.assertTrue(saved[-1].name.startswith('1004-'))


class ClockSteps(unittest.TestCase):
    def test_history_accepts_a_clock_stepped_backwards(self):
        with tempfile.TemporaryDirectory() as d,patch('retention_settings.configured_days',return_value=7):
            history=history_with_attempts(Path(d))
            self.assertTrue(history.record({'state':'OBSERVING','blockers':[]},now=500.0),'an earlier wall clock must not stop recording')
            self.assertEqual(history.load()['last_time'],900.0,'order is kept: time never goes backwards in the history')

    def test_budget_counts_a_future_attempt_as_now(self):
        events,permitted=pair_auto.budget([2000.0],1000.0,900,3)
        self.assertEqual(events,[1000.0]);self.assertTrue(permitted)


class TransientErrors(unittest.TestCase):
    def test_held_session_that_ran_resumes(self):
        state={'phase':'HELD','ran':True,'recovery_error':'PAIR-SYSTEM-001'}
        with patch.object(pair_auto,'save') as save:
            pair_auto.resume_running(state)
        self.assertEqual(state['phase'],'RUNNING');self.assertNotIn('recovery_error',state);save.assert_called_once()

    def test_held_start_that_never_ran_is_not_resumed(self):
        state={'phase':'HELD','recovery_error':'PAIR-SYSTEM-001'}
        with patch.object(pair_auto,'save') as save:
            pair_auto.resume_running(state)
        self.assertEqual(state['phase'],'HELD');save.assert_not_called()


class UniqueTemporaryFiles(unittest.TestCase):
    def test_history_writer_leaves_no_shared_pending_file(self):
        with tempfile.TemporaryDirectory() as d,patch('retention_settings.configured_days',return_value=7):
            history=history_with_attempts(Path(d));history.record({'state':'OBSERVING','blockers':[]},now=1000.0)
            names=sorted(p.name for p in Path(d).iterdir())
            self.assertFalse([n for n in names if n.endswith('.pending')],names)


if __name__=='__main__':unittest.main()
