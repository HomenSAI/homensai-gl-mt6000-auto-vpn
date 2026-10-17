import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('evidence',Path(__file__).resolve().parents[1]/'lab/protocol_evidence_collector.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class EvidenceTests(unittest.TestCase):
    def event(self,i,name='soak-selected-wga'):return {'time':float(i),'check':name,'result':'PASS'}
    def row(self,total,events):return {'counts':{'PASS':total},'recent':events}
    def test_repeated_overlapping_snapshots_do_not_double_count(self):
        value=module.Evidence();value.observe(self.row(2,[self.event(1),self.event(2)]));value.observe(self.row(3,[self.event(2),self.event(3)]));value.observe(self.row(3,[self.event(2),self.event(3)]))
        self.assertEqual(value.selected['wga'],3);self.assertEqual(value.missing,0)
    def test_retention_gap_is_reported_not_invented(self):
        value=module.Evidence();value.observe(self.row(3,[self.event(2),self.event(3)]));self.assertEqual(value.missing,1);self.assertEqual(value.selected['wga'],2)
    def test_reset_or_malformed_events_refuse(self):
        value=module.Evidence();value.observe(self.row(1,[self.event(1)]))
        with self.assertRaises(ValueError):value.observe(self.row(0,[]))
        with self.assertRaises(ValueError):module.Evidence().observe(self.row(1,[{'time':float('nan'),'check':'x','result':'PASS'}]))
    def test_unknown_boolean_negative_and_fractional_counters_refuse(self):
        for counts in ({'PASS':True},{'PASS':-1},{'PASS':1.5},{'other':1}):
            with self.subTest(counts=counts),self.assertRaises(ValueError):module.Evidence().observe({'counts':counts,'recent':[]})
    def test_reserve_proof_is_separate_from_selected_traffic(self):
        value=module.Evidence();value.observe(self.row(2,[self.event(1,'soak-parallel-reserve-ova'),self.event(2,'soak-selected-wgb')]))
        self.assertEqual(value.standby['ova'],1);self.assertEqual(value.selected['wgb'],1);self.assertEqual(value.selected['ova'],0)
if __name__=='__main__':unittest.main()
