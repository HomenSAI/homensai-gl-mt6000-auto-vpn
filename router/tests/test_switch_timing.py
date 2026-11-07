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
            for bad in (0,-3,601,600.001,float('nan'),float('inf'),True,'10',None):self.assertIsNone(t.record(d,bad))
            self.assertIsNone(t.read(d))
            (Path(d)/t.NAME).write_text('{broken');self.assertIsNone(t.read(d))
            self.assertEqual(t.record(d,30)['count'],1)

    def test_subsecond_and_upper_boundaries(self):
        # review F-51: finite 0 < d <= 600 is accepted (fast swaps finish below one second), precision is kept
        for value in (0.76,0.999,1,600):
            with tempfile.TemporaryDirectory() as d:
                stored=t.record(d,value,5.0)
                self.assertIsNotNone(stored,value);self.assertEqual(stored['avg_seconds'],value)
                self.assertEqual(t.read(d)['avg_seconds'],value);self.assertEqual(t.read(d)['last_seconds'],value)
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(t.record(d,600.001));self.assertIsNone(t.read(d))

    def test_average_keeps_the_unrounded_accumulator(self):
        # review F-52: A1 = s1, An = 0.7*A(n-1) + 0.3*sn on the stored value; rounding only for display
        with tempfile.TemporaryDirectory() as d:
            for value in (1,1.2,1):t.record(d,value,1.0)
            import json
            self.assertEqual(json.loads((Path(d)/t.NAME).read_text())['avg_seconds'],(1*0.7+1.2*0.3)*0.7+1*0.3)   # 1.042
            self.assertEqual(t.read(d)['avg_seconds'],1.042)   # the old rounding fed back gave 1.07
            self.assertEqual(t.read(d)['count'],3)


if __name__=='__main__':unittest.main()
