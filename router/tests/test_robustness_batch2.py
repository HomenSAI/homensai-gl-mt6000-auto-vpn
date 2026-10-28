"""Batch 2 of the project review: router load and Stop never waiting on a settings read."""
from pathlib import Path
import fcntl,os,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,native_history
from native_history import History


class HistoryCache(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.persist=self.root/'persist';self.cache=self.root/'run'/'native-history-public.json'
        p=patch('retention_settings.configured_days',return_value=7);p.start();self.addCleanup(p.stop)
        History(self.persist).record({'state':'OBSERVING'},now=1000)

    def test_unchanged_history_is_parsed_once(self):
        first=native_history.read_public(self.persist,cache=self.cache)
        with patch.object(History,'public',side_effect=AssertionError('parsed again')):
            self.assertEqual(native_history.read_public(self.persist,cache=self.cache),first,'unchanged files reuse the cached result')

    def test_any_write_invalidates_the_cache(self):
        native_history.read_public(self.persist,cache=self.cache)
        History(self.persist).record({'state':'COMMITTED','source':'a','target':'b'},now=1010)
        fresh=native_history.read_public(self.persist,cache=self.cache)
        self.assertEqual(fresh['sequence'],2,'a new event is visible at once')

    def test_broken_cache_costs_only_a_full_read(self):
        self.cache.parent.mkdir(parents=True);self.cache.write_text('{not json')
        self.assertEqual(native_history.read_public(self.persist,cache=self.cache)['sequence'],1)

    def test_cache_symlink_is_not_followed(self):
        self.cache.parent.mkdir(parents=True);target=self.root/'elsewhere.json';target.write_text('{"key":[],"value":{"sequence":99}}')
        os.symlink(str(target),str(self.cache))
        self.assertEqual(native_history.read_public(self.persist,cache=self.cache)['sequence'],1)


class StopOutsideLock(unittest.TestCase):
    def setUp(self):
        import auto_control as control
        self.control=control
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)

    def test_settings_are_read_before_the_control_lock(self):
        lock=self.path/'auto-control.lock'
        def command(_):
            fd=os.open(str(lock),os.O_CREAT|os.O_RDWR,0o600)
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)  # raises if Stop held the lock during the settings read
            finally:os.close(fd)
            return '{"settings":{"native_trial":"nonce"}}'
        with patch.object(agent,'command',side_effect=command):
            self.assertTrue(self.control.stop(runtime=self.path,persist=self.path)['queued'])
        self.assertEqual(agent.read_json(self.path/'native-stop.json')['trial'],'nonce')

    def test_start_for_another_trial_since_the_read_latches_all_trials(self):
        agent.atomic_json(self.path/'auto-control.json',{'mode':'on','time':1.0,'trial':'newer'})
        with patch.object(agent,'command',return_value='{"settings":{"native_trial":"nonce"}}'):
            self.control.stop(runtime=self.path,persist=self.path)
        self.assertTrue(agent.read_json(self.path/'native-stop.json').get('all_trials'))


if __name__=='__main__':
    unittest.main()
