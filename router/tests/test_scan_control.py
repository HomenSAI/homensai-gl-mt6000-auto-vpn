import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import scan_control as scan
from agent import atomic_json,read_json
class ScanTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def enqueue(self,now=100):return scan.enqueue(self.root,read_json,atomic_json,now)
 def test_single_flight_keeps_identity(self):
  a=self.enqueue();b=self.enqueue(101);self.assertEqual(a['request_id'],b['request_id']);self.assertTrue(b['duplicate'])
 def test_queued_is_not_complete(self):
  self.enqueue();self.assertEqual(scan.public(self.root,read_json,101)['state'],'QUEUED')
 def test_publish_required_and_result_survives_background_round(self):
  a=self.enqueue();i=scan.begin(self.root,read_json,atomic_json,101)
  with self.assertRaises(ValueError):scan.finish(self.root,read_json,atomic_json,i,now=102,snapshot={'measurement_request_id':'old','time':102})
  scan.finish(self.root,read_json,atomic_json,i,now=103,snapshot={'measurement_request_id':i,'time':102,'profiles':[{'interface':'wg1','time':102,'dns_ok':True,'https_success':2,'code':None}]})
  row=scan.public(self.root,read_json,500);self.assertEqual(row['state'],'COMPLETED');self.assertEqual(row['checked'],1);self.assertEqual(row['failed'],0)
  self.assertNotEqual(self.enqueue(501)['request_id'],i)
 def test_stopped_service_expires_not_success(self):
  self.enqueue();self.assertEqual(scan.public(self.root,read_json,401)['state'],'FAILED')
 def test_clock_regression_expires(self):
  self.enqueue();self.assertEqual(scan.public(self.root,read_json,99)['state'],'FAILED')
 def test_failed_measurement_remains_failed(self):
  self.enqueue();i=scan.begin(self.root,read_json,atomic_json,101);scan.finish(self.root,read_json,atomic_json,i,'SCAN-MEASUREMENT-FAILED',102);self.assertEqual(scan.public(self.root,read_json,103)['state'],'FAILED')
 def test_empty_and_failed_profiles_not_false_success(self):
  self.enqueue();i=scan.begin(self.root,read_json,atomic_json,101);scan.finish(self.root,read_json,atomic_json,i,now=103,snapshot={'measurement_request_id':i,'time':102,'profiles':[{'interface':'wg1','time':102,'code':'DNS-001'}]});self.assertEqual(scan.public(self.root,read_json,103)['failed'],1)
 def test_symlink_storage_refused(self):
  (self.root/'scan.lock').symlink_to(self.root/'outside')
  with self.assertRaises(OSError):self.enqueue()
 def test_corrupt_state_is_not_a_daemon_exception(self):
  atomic_json(self.root/'scan.state',{'request_id':'a'*32,'state':'RUNNING','requested_at':'bad'})
  self.assertEqual(scan.public(self.root,read_json,101)['code'],'SCAN-STATE-CORRUPT')
  self.assertIsNone(scan.begin(self.root,read_json,atomic_json,101))
 def test_concurrent_requests_coalesce(self):
  from concurrent.futures import ThreadPoolExecutor
  with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(lambda _:self.enqueue(),range(8)))
  self.assertEqual(len({r['request_id'] for r in rows}),1)
 def test_late_finish_cannot_complete_replacement(self):
  self.enqueue();old=scan.begin(self.root,read_json,atomic_json,101);new=self.enqueue(402)
  self.assertFalse(scan.finish(self.root,read_json,atomic_json,old,now=403,snapshot={}))
  self.assertEqual(scan.public(self.root,read_json,403)['request_id'],new['request_id'])
  self.assertEqual(scan.public(self.root,read_json,403)['state'],'QUEUED')
 def test_expired_request_does_not_create_busy_loop(self):
  self.enqueue();self.assertIsNone(scan.begin(self.root,read_json,atomic_json,401));self.assertFalse((self.root/'scan.request').exists())
 def test_overdue_completion_is_failure(self):
  self.enqueue();i=scan.begin(self.root,read_json,atomic_json,101);scan.finish(self.root,read_json,atomic_json,i,now=401,snapshot={})
  self.assertEqual(scan.public(self.root,read_json,402)['state'],'FAILED')
if __name__=='__main__':unittest.main()
