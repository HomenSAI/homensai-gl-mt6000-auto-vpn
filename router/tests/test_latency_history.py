import copy,json
from pathlib import Path
import tempfile,unittest,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from latency_history import LatencyHistory,MAX_ROWS,MAX_BYTES,DAY,WEEK

def snapshot(now=120,source=20,target=40,**changes):
    rows=[{'id':'wireguard:peer_1','time':now,'code':None,'dns_ok':True,'https_success':2,'vendor_state':'SETTLED','rtt_ms':source},
          {'id':'openvpn:1_1','time':now,'code':None,'dns_ok':True,'https_success':2,'vendor_state':'SETTLED','rtt_ms':target}]
    return dict(profiles=rows,native_failover={'time':now,'state':'OBSERVING','source':rows[0]['id'],'target':rows[1]['id'],'mode':'continuous-pair','proof_scope':'router-probed-ipv4','readiness_verified':True},**changes)

class LatencyHistoryTests(unittest.TestCase):
    def test_unique_samples_aggregate_and_failures_are_gaps_not_zero(self):
        h=LatencyHistory();s=snapshot();h.observe(s,{},120);h.observe(s,{},121)
        self.assertEqual(h.public()['rows'][0][1:5],[20,40,1,1])
        h.observe(snapshot(130,40,60),{},130);self.assertEqual(h.public()['rows'][0][1:5],[30,50,2,2])
        s=snapshot(180);s['profiles'][0]['code']='DNS-001';s['profiles'][1]['vendor_state']='CHANGING';h.observe(s,{},180)
        self.assertEqual(h.public()['rows'][-1][1:5],[None,None,0,0])

    def test_stale_future_unknown_and_bad_values_are_not_successes(self):
        for value in [float('nan'),float('inf'),-1,600001,True]:
            h=LatencyHistory();h.observe(snapshot(120,value,value),{},120);self.assertEqual(h.public()['rows'][0][1:3],[None,None])
        for time in [0,200]:
            h=LatencyHistory();h.observe(snapshot(time),{'plan_source':'wireguard:peer_1','plan_target':'openvpn:1_1'},120);self.assertEqual(h.public()['rows'][0][1:3],[None,None])

    def test_retention_is_bounded_and_never_backfills_history(self):
        h=LatencyHistory()
        for stamp in range(120,100000,60):h.observe(snapshot(stamp),{},stamp)
        self.assertLessEqual(len(h.data['rows']),MAX_ROWS)
        self.assertTrue(all(r[0]>=99960-WEEK for r in h.data['rows']))
        prior=copy.deepcopy(h.data);h.observe(snapshot(30),{},30);self.assertEqual(h.data,prior)
        self.assertLess(len(json.dumps(h.data).encode()),MAX_BYTES)

    def test_changed_pair_does_not_inherit_another_profiles_line(self):
        h=LatencyHistory();h.observe(snapshot(),{},120)
        s=snapshot(180);s['profiles'][0]['id']='wireguard:peer_2';s['native_failover']['source']='wireguard:peer_2';h.observe(s,{},180)
        self.assertEqual(h.public()['pair'][0],'wireguard:peer_2');self.assertEqual(len(h.public()['rows']),1)
        self.assertEqual(h.public()['rows'][0][0],180)

    def test_stale_controller_cannot_override_the_new_saved_pair_or_claim_selection(self):
        h=LatencyHistory();s=snapshot();s['native_failover']['time']=1
        s['profiles'][0]['id']='wireguard:peer_9'
        h.observe(s,{'plan_source':'wireguard:peer_9','plan_target':'openvpn:1_1'},120)
        self.assertEqual(h.public()['pair'],['wireguard:peer_9','openvpn:1_1']);self.assertEqual(h.public()['rows'][0][5],'unknown')

    def test_roundtrip_does_not_store_server_addresses_and_corruption_is_retained(self):
        h=LatencyHistory();s=snapshot();s['profiles'][0]['server_endpoint']={'host':'198.51.100.1'};h.observe(s,{},120)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'history.json';h.save(path,lambda p,d:p.write_text(json.dumps(d)),130)
            self.assertNotIn('198.51.100.1',path.read_text());restored=LatencyHistory.load(path);self.assertEqual(restored.public(),h.public())
            tampered=json.loads(path.read_text());tampered['data']['rows'][0][1]=999;path.write_text(json.dumps(tampered));self.assertEqual(LatencyHistory.load(path).notice,'LATENCY-HISTORY-UNAVAILABLE','valid-looking corrupted values fail checksum')
            path.write_text('{broken');bad=LatencyHistory.load(path);self.assertEqual(bad.notice,'LATENCY-HISTORY-UNAVAILABLE')
            with self.assertRaises(ValueError):bad.save(path,lambda p,d:p.write_text(json.dumps(d)),140)
            self.assertEqual(path.read_text(),'{broken')

    def week_fixture(self,now=900000):
        h=LatencyHistory();h.observe(snapshot(now),{'history_days':7},now)
        key=h.data['current']
        h.data['rows']=[[stamp,599999.9,599999.8,120,120,'unknown',key] for stamp in range(now-WEEK,now+1,60)]
        return LatencyHistory(h.data)

    def test_seven_days_boundary_save_load_and_public_reply_budget(self):
        h=self.week_fixture();self.assertEqual(len(h.data['rows']),10081)
        h.observe(snapshot(900060),{'history_days':7},900060)
        self.assertEqual(h.data['rows'][0][0],900060-WEEK)
        self.assertEqual(h.public()['rows_count'],10081)
        self.assertEqual(len(h.public()['rows']),1441)
        self.assertEqual(len(json.loads(h.public()['rows_json'])),10081)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'week.json';h.save(path,lambda p,d:p.write_text(json.dumps(d,separators=(',',':'))),900060)
            self.assertLess(path.stat().st_size,MAX_BYTES)
            restored=LatencyHistory.load(path);self.assertIsNone(restored.notice)
            self.assertEqual(restored.public(),h.public())
        from agent import trim_status_reply
        status={'latency_history':h.public(),'samples':[{'value':'x'*800} for _ in range(1000)],'events':[{'value':'y'*300} for _ in range(1000)]}
        trimmed=trim_status_reply(status)
        self.assertLessEqual(len(json.dumps(trimmed,ensure_ascii=True).encode()),900000)
        self.assertEqual(len(json.loads(trimmed['latency_history']['rows_json'])),10081)
        self.assertLess(len(trimmed['latency_history']['rows_json']),850000)

    def test_configured_day_limit_prunes_and_expansion_does_not_backfill(self):
        h=self.week_fixture();h.observe(snapshot(900060),{'history_days':1},900060)
        self.assertEqual(h.public()['retention_seconds'],DAY)
        self.assertLessEqual(len(h.data['rows']),1441)
        earliest=h.data['rows'][0][0]
        h.observe(snapshot(900120),{'history_days':7},900120)
        self.assertEqual(h.public()['retention_seconds'],WEEK)
        self.assertEqual(h.data['rows'][0][0],earliest,'deleted older rows are not reconstructed')

    def test_retention_prunes_even_without_a_valid_pair(self):
        h=self.week_fixture();h.observe({'profiles':[]},{'history_days':1},900000+2*DAY)
        self.assertEqual(h.data['rows'],[]);self.assertIsNone(h.data['current'])
        self.assertEqual(LatencyHistory(h.data).public()['rows'],[])

    def test_storage_error_is_reported_not_silently_successful(self):
        h=LatencyHistory();h.observe(snapshot(),{},120)
        def broken(*args):raise OSError('simulated disk full')
        with self.assertRaises(OSError):h.save(Path('unused'),broken,130)
        self.assertIsNone(h.data['saved'])

if __name__=='__main__':unittest.main()
