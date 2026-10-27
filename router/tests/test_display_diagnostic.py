"""The polled status reuses a short-lived diagnostic; actions never do."""
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,manual_control


class DisplayDiagnostic(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        p=patch.object(agent,'RUNTIME',Path(self.temp.name));p.start();self.addCleanup(p.stop)

    def test_reuses_for_fifteen_seconds_then_refreshes(self):
        backend=Mock();backend.diagnostic.side_effect=[(['A'],{'hash':'1'}),(['B'],{'hash':'2'})]
        self.assertEqual(manual_control.display_diagnostic(backend,1000),(['A'],{'hash':'1'}))
        self.assertEqual(manual_control.display_diagnostic(backend,1014),(['A'],{'hash':'1'}))
        self.assertEqual(manual_control.display_diagnostic(backend,1015),(['B'],{'hash':'2'}))
        self.assertEqual(backend.diagnostic.call_count,2)

    def test_future_or_damaged_cache_is_ignored(self):
        backend=Mock();backend.diagnostic.return_value=([],None)
        agent.atomic_json(Path(self.temp.name)/'display-diagnostic.json',{'time':5000,'blockers':['X'],'selection':None})
        self.assertEqual(manual_control.display_diagnostic(backend,1000),([],None))
        (Path(self.temp.name)/'display-diagnostic.json').write_text('{bad')
        self.assertEqual(manual_control.display_diagnostic(backend,1000),([],None))


if __name__=='__main__':unittest.main()
