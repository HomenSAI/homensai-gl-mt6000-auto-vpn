"""The 10 s status reply carries no long event lists; the separate 'history' call returns them."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent


class Split(unittest.TestCase):
    def test_lists_move_out_and_the_rest_stays(self):
        status={'native_history':{'events':[1,2],'totals':{'a':1}},'accounting':{'quality':{'q':1},'activity':{'x':1},'reliability':{'events':[3],'route_history':{'r':1}}}}
        moved=agent.split_history(status)
        self.assertEqual(moved,{'native_history.events':[1,2],'accounting.quality':{'q':1},'accounting.reliability.events':[3]})
        self.assertEqual(status['native_history'],{'totals':{'a':1}});self.assertEqual(status['accounting']['activity'],{'x':1})
        self.assertEqual(status['accounting']['reliability'],{'route_history':{'r':1}})
        self.assertEqual(status['history_split'],['accounting.quality','accounting.reliability.events','native_history.events'])

    def test_missing_parts_are_harmless(self):
        status={'accounting':None};self.assertEqual(agent.split_history(status),{});self.assertEqual(status['history_split'],[])


if __name__=='__main__':unittest.main()
