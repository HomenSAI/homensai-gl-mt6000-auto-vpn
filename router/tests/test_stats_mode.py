"""Statistics mode: work (default on the router) keeps only what switching needs; diagnostics are bounded in time."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,native_switch as n,stats_mode as s
from native_history import History,_WRITER_CACHE

NOW=1793400000.0


class Mode(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);self.root=Path(folder.name)
        self.config=self.root/'homensai_vpn';s._CACHE.update(key=None,options={})

    def write(self,mode=None,until=None):
        text="config main 'main'\n\toption enabled '1'\n"
        if mode:text+="\toption stats_mode '%s'\n"%mode
        if until is not None:text+="\toption stats_until '%s'\n"%until
        self.config.write_text(text)

    def test_installed_router_defaults_to_work(self):
        self.write()
        self.assertFalse(s.diagnostic(NOW,self.config))
        self.assertEqual(s.public(NOW,self.config)['mode'],'work')

    def test_without_package_config_everything_is_recorded_as_before(self):
        self.assertTrue(s.diagnostic(NOW,self.root/'missing'))

    def test_diagnostics_are_bounded_and_end_by_themselves(self):
        self.write('diagnostic',int(NOW+3600))
        self.assertTrue(s.diagnostic(NOW,self.config))
        self.assertEqual(s.public(NOW,self.config)['remaining'],3600)
        self.assertFalse(s.diagnostic(NOW+3601,self.config),'the window closed')
        self.write('diagnostic',int(NOW+13*86400))
        self.assertTrue(s.diagnostic(NOW,self.config),'two weeks are allowed')
        self.write('diagnostic',int(NOW+15*86400))
        self.assertFalse(s.diagnostic(NOW,self.config),'never longer than 2 weeks')
        self.write('diagnostic','x')
        self.assertFalse(s.diagnostic(NOW,self.config))

    def test_payload_accepts_only_work_or_bounded_diagnostics(self):
        self.assertEqual(s.payload({'mode':'work'},NOW),{'main':{'stats_mode':'work','stats_until':'0'},'servers':[]})
        for hours in (24,72,168,336):
            self.assertEqual(s.payload({'mode':'diagnostic','hours':hours},NOW)['main'],{'stats_mode':'diagnostic','stats_until':str(int(NOW+hours*3600))})
        for bad in ({},{'mode':'x'},{'mode':'work','hours':1},{'mode':'diagnostic'},{'mode':'diagnostic','hours':1},
                    {'mode':'diagnostic','hours':True},{'mode':'diagnostic','hours':24,'x':1}):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'STATS-SETTINGS-FIELDS'):s.payload(bad,NOW)

    def test_switch_events_always_go_to_the_flash_history(self):
        self.write()
        with patch.object(s,'CONFIG',self.config):
            self.assertEqual(s.history_target('run','save',NOW),('save',10000))
            self.write('diagnostic',int(NOW+60));self.assertEqual(s.history_target('run','save',NOW),('save',10000))


class Publish(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup);root=Path(folder.name)
        self.run_dir=root/'run';self.save_dir=root/'save';self.run_dir.mkdir();self.save_dir.mkdir()
        self.config=root/'homensai_vpn';self.config.write_text("config main 'main'\n");s._CACHE.update(key=None,options={})
        self.addCleanup(_WRITER_CACHE.clear)
        for target,name,value in ((n,'RUNTIME',self.run_dir),(n,'PERSIST',self.save_dir),(agent,'RUNTIME',self.run_dir),(agent,'PERSIST',self.save_dir),
                                  (n,'STATE',self.run_dir/'native-status.json'),(s,'CONFIG',self.config)):
            p=patch.object(target,name,value);p.start();self.addCleanup(p.stop)

    def test_work_mode_writes_switch_events_to_flash_and_keeps_no_resident_copy(self):
        for i in range(6):n.publish({'state':'ARMED' if i%2 else 'OBSERVING','reason':'PAIR-WATCHING','source':'wireguard:peer_1','target':'openvpn:1_2'})
        self.assertTrue((self.save_dir/'native-history.json').exists(),'switch events are written to flash (owner decision)')
        self.assertFalse((self.run_dir/'native-history.json').exists())
        self.assertEqual(_WRITER_CACHE,{},'work mode: read, shown and released, no resident copy')
        self.assertEqual(agent.native_history_public()['retained_events'],6)

    def test_diagnostics_keep_the_resident_copy_for_faster_writing(self):
        self.config.write_text("config main 'main'\n\toption stats_mode 'diagnostic'\n\toption stats_until '%d'\n"%(int(__import__('time').time())+3600))
        n.publish({'state':'ARMED','reason':'PAIR-WATCHING','source':'wireguard:peer_1','target':'openvpn:1_2'})
        self.assertTrue((self.save_dir/'native-history.json').exists())
        self.assertIn(str(self.save_dir/'native-history.json'),_WRITER_CACHE)


class WorkModeHistory(unittest.TestCase):
    def test_finished_measurement_reaches_the_page_without_recording(self):
        calls=[]
        class Empty:
            def public(self,now):calls.append(now);return {'rows':[]}
        wrapped=agent.WorkModeHistory(Empty())
        wrapped.observe({'profiles':[]},{},1)
        self.assertEqual(wrapped.public(5),{'rows':[]});self.assertEqual(calls,[5])


if __name__=='__main__':unittest.main()
