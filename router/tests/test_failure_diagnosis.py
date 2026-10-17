import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from failure_diagnosis import diagnose
class DiagnosisTests(unittest.TestCase):
 def status(self,code=None):return {'time':100,'profiles':[{'id':'a','interface':'wg1','time':100,'code':code,'dns_ok':True,'https_success':2}]}
 def test_down_requires_fresh_link_proof(self):
  s=self.status();s['uplink_observation']={'state':'DOWN','time':100};self.assertTrue(diagnose(s,'a',101)['suppress_switch']);self.assertFalse(diagnose(s,'a',300)['suppress_switch'])
 def test_link_up_never_confirms_vpn(self):
  s=self.status('VPN-003');s['uplink_observation']={'state':'LINK-UP','time':100};self.assertEqual(diagnose(s,'a',101)['code'],'HTTPS-FAILED')
 def test_distinct_causes(self):
  for code,expected in [('DNS-001','DNS-FAILED'),('ROUTE-001','ROUTE-MISMATCH'),('CHECK-001','PATH-UNVERIFIED'),('VPN-001','TUNNEL-DISCONNECTED')]:self.assertEqual(diagnose(self.status(code),'a',101)['code'],expected)
 def test_stale_or_future_is_not_current_failure(self):
  self.assertEqual(diagnose(self.status('DNS-001'),'a',90)['code'],'OBSERVATION-STALE')
 def test_no_evidence_does_not_claim_down(self):self.assertFalse(diagnose(self.status(),'other',101)['suppress_switch'])
if __name__=='__main__':unittest.main()
