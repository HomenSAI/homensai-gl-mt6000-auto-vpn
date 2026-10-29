"""Average confirmed switch time for the page countdown: bounded, persistent, never raises."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import switch_timing as t


class SwitchTiming(unittest.TestCase):
    def test_average_follows_recent_switches(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(t.read(d))
            t.record(d,40,1.0);self.assertEqual(t.read(d)['avg_seconds'],40)
            t.record(d,20,2.0);self.assertEqual(t.read(d),{'avg_seconds':34.0,'count':2,'last_seconds':20,'updated':2.0})

    def test_impossible_values_and_damage_are_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in (0,-3,601,float('nan'),'10',None):self.assertIsNone(t.record(d,bad))
            self.assertIsNone(t.read(d))
            (Path(d)/t.NAME).write_text('{broken');self.assertIsNone(t.read(d))
            self.assertEqual(t.record(d,30)['count'],1)


if __name__=='__main__':unittest.main()
