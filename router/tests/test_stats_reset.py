"""Owner reset of charts and statistics: bounded request, archive first, then counting from zero."""
from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,stats_reset
from latency_history import LatencyHistory


class StatsReset(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'run').mkdir();(self.root/'persist').mkdir()
        p=patch('rpc_throttle.allow',return_value=True);p.start();self.addCleanup(p.stop)

    def queue(self,scope,now=1000):
        return stats_reset.request({'scope':scope},runtime=self.root/'run',now=now)

    def test_request_is_bounded_and_consumed_once(self):
        self.assertEqual(stats_reset.request({'scope':'everything'},runtime=self.root/'run')['code'],'STATS-RESET-FIELDS')
        self.assertEqual(stats_reset.request({'scope':'latency','x':1},runtime=self.root/'run')['code'],'STATS-RESET-FIELDS')
        queued=self.queue('latency');self.assertTrue(queued['queued'])
        value=stats_reset.pending(self.root/'run');self.assertEqual(value['scope'],'latency');self.assertEqual(value['nonce'],queued['nonce'])
        self.assertIsNone(stats_reset.pending(self.root/'run'),'a request is applied once')

    def test_rate_limited_request_is_refused(self):
        with patch('rpc_throttle.allow',return_value=False):
            self.assertEqual(self.queue('latency')['code'],'RPC-RATE-LIMIT')

    def test_latency_quality_and_traffic_are_archived_then_cleared(self):
        accounting=agent.Accounting({'months':{'2026-10':{'rx':5,'tx':6,'seconds':1,'boundary_estimated':False}},'quality':{'a':{'buckets':{},'last':None}},'activity':{'a':{}}})
        latency=LatencyHistory();latency.data['seen']={'wireguard:peer_1':900.0}
        self.queue('quality');value=stats_reset.pending(self.root/'run')
        accounting,latency,result=stats_reset.apply(value,accounting,latency,1000,agent.atomic_json,persist=self.root/'persist')
        self.assertTrue(result['done']);self.assertEqual(accounting.quality,{});self.assertEqual(accounting.activity,{})
        self.assertEqual(accounting.months['2026-10']['rx'],5,'only the chosen statistics are reset')
        self.assertEqual(latency.data['seen'],{'wireguard:peer_1':900.0})
        saved=json.loads((self.root/'persist'/'stats-archive'/result['archive']).read_text(encoding='utf8'))
        self.assertEqual(saved['sha256'],stats_reset.checksum(saved['data']));self.assertIn('a',saved['data']['quality']['quality'])
        for scope,now in (('traffic',1001),('latency',1002)):
            self.queue(scope,now);accounting,latency,result=stats_reset.apply(stats_reset.pending(self.root/'run'),accounting,latency,now,agent.atomic_json,persist=self.root/'persist')
            self.assertTrue(result['done'],result)
        self.assertEqual(accounting.months,{});self.assertEqual(latency.data['seen'],{})

    def test_archive_keeps_newest_only(self):
        for index in range(stats_reset.ARCHIVE_KEEP+3):
            stats_reset.archive(self.root/'persist','latency',{'n':index},1000+index,agent.atomic_json)
        names=sorted(p.name for p in (self.root/'persist'/'stats-archive').glob('*.json'))
        self.assertEqual(len(names),stats_reset.ARCHIVE_KEEP);self.assertEqual(names[-1],'%d-latency.json'%(1000+stats_reset.ARCHIVE_KEEP+2))

    def test_failed_archive_changes_nothing(self):
        accounting=agent.Accounting({'quality':{'a':{'buckets':{},'last':None}}});latency=LatencyHistory()
        self.queue('quality');value=stats_reset.pending(self.root/'run')
        def broken(path,value):raise OSError('disk full')
        accounting,latency,result=stats_reset.apply(value,accounting,latency,1000,broken,persist=self.root/'persist')
        self.assertFalse(result['done']);self.assertEqual(result['code'],'STATS-RESET-FAILED');self.assertIn('a',accounting.quality)

    def test_samples_reset_archives_then_empties_the_monitor_list(self):
        samples=[{'id':'wireguard:peer_1','time':990.0,'code':None,'rtt_ms':40.0},{'id':'openvpn:1_1','time':995.0,'code':'VPN-001','rtt_ms':None}]
        accounting=agent.Accounting({'quality':{'a':{'buckets':{},'last':None}}})
        self.queue('samples');value=stats_reset.pending(self.root/'run')
        accounting,latency,result=stats_reset.apply(value,accounting,LatencyHistory(),1000,agent.atomic_json,persist=self.root/'persist',samples=samples)
        self.assertTrue(result['done'],result);self.assertEqual(samples,[],'the monitor list itself is emptied')
        self.assertIn('a',accounting.quality,'other statistics are untouched')
        saved=json.loads((self.root/'persist'/'stats-archive'/result['archive']).read_text(encoding='utf8'))
        self.assertEqual(result['archive'],'1000-samples.json');self.assertEqual(saved['data'],{'samples':[{'id':'wireguard:peer_1','time':990.0,'code':None,'rtt_ms':40.0},{'id':'openvpn:1_1','time':995.0,'code':'VPN-001','rtt_ms':None}]})
        self.assertEqual(saved['sha256'],stats_reset.checksum(saved['data']))

    def test_fault_history_reset_archives_then_empties_it_under_the_control_lock(self):
        rows=[{'time':900.5,'code':'FAULT-CLEANED','profiles':['wireguard:peer_1'],'scope':'channel','duration':150}]
        path=self.root/'persist'/'fault-history.json';agent.atomic_json(path,{'data':rows,'sha256':stats_reset.checksum(rows)})
        self.queue('faults');value=stats_reset.pending(self.root/'run')
        accounting,latency,result=stats_reset.apply(value,agent.Accounting(),LatencyHistory(),1000,agent.atomic_json,persist=self.root/'persist',runtime=self.root/'run')
        self.assertTrue(result['done'],result)
        self.assertEqual(json.loads(path.read_text(encoding='utf8')),{'data':[],'sha256':stats_reset.checksum([])})
        self.assertTrue((self.root/'run'/'auto-control.lock').exists(),'taken under the lock fault_control.event writes under')
        saved=json.loads((self.root/'persist'/'stats-archive'/result['archive']).read_text(encoding='utf8'))
        self.assertEqual(saved['data'],{'faults':rows})
        # no history yet: nothing to lose, an empty archive and an empty file
        path.unlink();self.queue('faults',1001)
        accounting,latency,result=stats_reset.apply(stats_reset.pending(self.root/'run'),accounting,latency,1001,agent.atomic_json,persist=self.root/'persist',runtime=self.root/'run')
        self.assertTrue(result['done'],result);self.assertEqual(json.loads(path.read_text(encoding='utf8'))['data'],[])
        # a damaged history is refused with its code and kept as evidence
        path.write_text('{"data":[1],"sha256":"x"}',encoding='utf8');self.queue('faults',1002)
        accounting,latency,result=stats_reset.apply(stats_reset.pending(self.root/'run'),accounting,latency,1002,agent.atomic_json,persist=self.root/'persist',runtime=self.root/'run')
        self.assertEqual((result['done'],result['code']),(False,'FAULT-HISTORY-CORRUPT'))
        self.assertEqual(path.read_text(encoding='utf8'),'{"data":[1],"sha256":"x"}')

    def test_all_keeps_samples_and_fault_history(self):
        self.assertEqual(set(stats_reset.SCOPES)-{'samples','faults'},{'latency','auto','traffic','quality','speed','ranking','all'})
        samples=[{'id':'x','time':999.0}]
        path=self.root/'persist'/'fault-history.json';rows=[{'time':1.0,'code':'FAULT-CLEANED'}];agent.atomic_json(path,{'data':rows,'sha256':stats_reset.checksum(rows)})
        with patch('retention_settings.configured_days',return_value=7),patch('speed_test.load_history',return_value={'results':[]}),\
             patch.object(stats_reset,'reset_speed_history',return_value={}),patch.object(stats_reset,'reset_native_history',return_value={}),\
             patch('native_history.History.load',return_value={}):
            accounting,latency,result=stats_reset.apply({'scope':'all','nonce':'a'*32},agent.Accounting(),LatencyHistory(),1000,agent.atomic_json,persist=self.root/'persist',samples=samples)
        self.assertTrue(result['done'],result);self.assertEqual(len(samples),1);self.assertEqual(json.loads(path.read_text(encoding='utf8'))['data'],rows)

    def test_auto_reset_keeps_running_attempt_metadata(self):
        from native_history import History
        history=History(self.root/'persist',detail_days=7)
        data={'sequence':3,'events':[],'months':{'2026-10':{'attempts':3}},'days':{},'last_key':None,'last_time':900.0,'timezone':'Europe/Berlin',
              'counter_version':2,'totals':{'attempts':3},'counted':{},'active_attempt':{'id':3,'episode':2,'source':'wireguard:peer_1','target':'openvpn:1_1','terminal':False}}
        agent.atomic_json(history.path,history.envelope(data))
        with patch('retention_settings.configured_days',return_value=7):
            accounting,latency,result=stats_reset.apply({'scope':'auto','nonce':'a'*32},agent.Accounting(),LatencyHistory(),1000,agent.atomic_json,persist=self.root/'persist')
            self.assertTrue(result['done'],result)
            after=History(self.root/'persist',detail_days=7).load()
        self.assertEqual(after['totals'],{});self.assertEqual(after['months'],{});self.assertEqual(after['sequence'],3)
        self.assertEqual(after['active_attempt']['id'],3,'a running attempt still correlates after the reset')
        self.assertTrue(accounting.reliability.critical,'the reset is saved at once')


if __name__=='__main__':unittest.main()
