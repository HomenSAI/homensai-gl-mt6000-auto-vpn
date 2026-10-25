import copy,json,sys,tempfile,unittest
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,setup_config,retention_settings,speed_test,statistics_export
from native_history import History
from reliability import Reliability
BASE=1792750000
class RetentionSettingsTests(unittest.TestCase):
 def test_configured_days_uses_bounded_cache_and_falls_back_on_invalid_config(self):
  with patch.object(retention_settings,'_cached',None),patch.object(retention_settings.time,'monotonic',side_effect=[10,12,16]),patch.object(retention_settings.subprocess,'run',side_effect=[MagicMock(returncode=0,stdout=b'2\n'),MagicMock(returncode=0,stdout=b'999\n')]) as read:
   self.assertEqual(retention_settings.configured_days(),2);self.assertEqual(retention_settings.configured_days(),2)
   self.assertEqual(retention_settings.configured_days(),7);self.assertEqual(read.call_count,2)
 def test_exact_monitor_ranges_and_legacy_payload_preservation(self):
  legacy=dict(interval=30,checkpoint=900,probe_limit=2,planning_enabled=False)
  self.assertNotIn('history_days',setup_config.monitor_payload(legacy)['main'])
  for limit in (1,100,1500,2000):
   for days in (1,2,7):
    main=setup_config.monitor_payload(dict(legacy,live_log_limit=limit,history_days=days))['main']
    self.assertEqual(main['live_log_limit'],str(limit));self.assertEqual(main['history_days'],str(days))
  for field,value in [('live_log_limit',0),('live_log_limit',2001),('live_log_limit',True),('live_log_limit',1.5),('history_days',0),('history_days',8),('history_days',False),('history_days','2')]:
   with self.subTest(field=field,value=value),self.assertRaises(ValueError):setup_config.monitor_payload(dict(legacy,**{field:value}))
 def test_incident_prune_preserves_monthly_and_lifetime_totals(self):
  r=Reliability();row=lambda stamp,code:dict(id='wireguard:peer_1',time=stamp,code=code,dns_ok=code is None,https_success=2 if code is None else 0)
  r.observe(row(BASE,'VPN-003'));r.observe(row(BASE+10,None));totals=copy.deepcopy(r.data['totals']);months=copy.deepcopy(r.data['months'])
  r.detail_days=1;r.prune(BASE+2*86400)
  self.assertEqual(r.data['events'],[]);self.assertEqual(r.data['totals'],totals);self.assertEqual(r.data['months'],months);self.assertEqual(r.public()['detail_days'],1)
 def test_controller_retention_is_persisted_and_not_resurrected_by_increasing_period(self):
  with tempfile.TemporaryDirectory() as d:
   h=History(d,detail_days=7);h.record({'state':'APPLYING','source':'wireguard:peer_1','target':'openvpn:1_1'},BASE);h.record({'state':'COMMITTED','source':'wireguard:peer_1','target':'openvpn:1_1'},BASE+1)
   totals=copy.deepcopy(h.load()['totals']);h=History(d,detail_days=1)
   h.record({'state':'COMMITTED','source':'wireguard:peer_1','target':'openvpn:1_1'},BASE+2*86400)
   self.assertEqual(h.load()['events'],[]);self.assertEqual(h.load()['totals'],totals)
   self.assertEqual(History(d,detail_days=7).load()['events'],[])
   self.assertEqual(json.loads(h.backup.read_text())['data']['events'],[])
   with patch.object(retention_settings,'configured_days',return_value=1):
    result=statistics_export.page(Path(d),dict(kind='controller',after=0,until=0),now=BASE+2*86400)
   self.assertEqual(result['detail_days'],1);self.assertEqual(result['events'],[])
 def test_accounting_prunes_detail_but_keeps_month_totals(self):
  a=agent.Accounting();a.months={'2026-10':{'rx':123}};a.quality={'old':{'last':{'time':BASE-2*86400},'buckets':{}},'new':{'last':{'time':BASE},'buckets':{str(int((BASE-2*86400)//3600)): {},str(int(BASE//3600)):{}}}}
  a.apply_detail_retention(1,BASE)
  self.assertNotIn('old',a.quality);self.assertEqual(len(a.quality['new']['buckets']),1);self.assertEqual(a.months['2026-10']['rx'],123)
 def test_speed_retention_cleans_primary_and_backup_without_a_test_or_quota_write(self):
  with tempfile.TemporaryDirectory() as d,patch.object(speed_test,'HISTORY',Path(d)/'speed-history.json'),patch.object(speed_test,'control_lock',return_value=nullcontext()),patch.object(retention_settings,'configured_days',return_value=1),patch.object(speed_test.time,'time',return_value=BASE):
   data={'results':[{'time':BASE-2*86400},{'time':BASE-20}],'retention_days':7}
   agent.atomic_json(speed_test.HISTORY,{'schema':1,'data':data,'sha256':agent.checksum(data)})
   speed_test.prune_history()
   for path in (speed_test.HISTORY,speed_test.HISTORY.with_name('speed-history.backup.json')):
    saved=json.loads(path.read_text())['data'];self.assertEqual(len(saved['results']),1);self.assertEqual(saved['retention_days'],1)
   self.assertEqual(len(list(Path(d).iterdir())),2,'no quota/job files are created')
if __name__=='__main__':unittest.main()
