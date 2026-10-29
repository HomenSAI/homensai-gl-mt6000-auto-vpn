"""ICMP ping history: the latency chart and statistics keep working while ping is the response metric."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,icmp_ping
from ping_response_history import PingResponseHistory
from website_response_history import WebsiteResponseHistory

NOW=180000
SETTINGS={'plan_source':'wireguard:peer_1','plan_target':'openvpn:1_2'}


def snapshot(stamp=NOW,source=35.74,target=None):
    rows=[]
    for identifier,protocol,interface,rtt in ((SETTINGS['plan_source'],'wireguard','wgclient1',source),
                                              (SETTINGS['plan_target'],'openvpn','ovpnclient2',target)):
        row={'id':identifier,'protocol':protocol,'interface':interface,'vendor_tunnel_id':protocol+':'+interface,
             'vendor_generation':'a'*32,'vendor_state':'SETTLED','time':stamp,'code':None}
        row['ping']=icmp_ping.public(row,'ok' if rtt is not None else 'failed',None if rtt is not None else 'PING-FAILED',stamp,rtt)
        rows.append(row)
    return {'time':stamp,'profiles':rows,'native_failover':{}}


class PingHistoryTests(unittest.TestCase):
    def test_reply_is_a_point_and_lost_echo_is_a_gap_with_coverage(self):
        h=PingResponseHistory();h.observe(snapshot(),SETTINGS,NOW)
        public=h.public(NOW)
        self.assertEqual((public['metric'],public['target_set'],public['row_encoding']),('icmp-rtt-ms','icmp-echo','sum-tenths'))
        self.assertEqual(public['rows'][0][1:5],[357,None,1,0])
        self.assertEqual(public['coverage_rows'][0][1:],[3,0,3,3,0,1])
        self.assertEqual(public['pair'],[SETTINGS['plan_source'],SETTINGS['plan_target']])

    def test_same_echo_is_counted_once_and_a_new_echo_is_added(self):
        h=PingResponseHistory();h.observe(snapshot(),SETTINGS,NOW);h.observe(snapshot(),SETTINGS,NOW+5)
        h.observe(snapshot(NOW+10,source=45.74),SETTINGS,NOW+10)
        self.assertEqual(h.public(NOW+10)['rows'][0][1:5],[814,None,2,0])

    def test_stale_or_foreign_samples_are_ignored(self):
        h=PingResponseHistory();s=snapshot();s['profiles'][0]['ping']['interface']='wgclient9'
        h.observe(s,SETTINGS,NOW);h.observe(snapshot(NOW-500),SETTINGS,NOW)
        self.assertEqual(h.public(NOW)['rows'][0][3:5],[0,0]);self.assertEqual(h.public(NOW)['coverage_rows'][0][1:],[0,0,0,3,0,1])

    def test_save_load_and_website_file_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ping.json';h=PingResponseHistory();h.observe(snapshot(),SETTINGS,NOW);h.save(path,agent.atomic_json,NOW)
            self.assertEqual(PingResponseHistory.load(path).public(NOW)['rows'],h.public(NOW)['rows'])
            other=Path(directory)/'web.json';WebsiteResponseHistory().save(other,agent.atomic_json,NOW)
            self.assertEqual(PingResponseHistory.load(other).notice,'PING-HISTORY-UNAVAILABLE')

    def test_reset_clears_the_chart(self):
        h=PingResponseHistory();h.observe(snapshot(),SETTINGS,NOW);h.clear(NOW)
        self.assertEqual(h.public(NOW)['rows'],[])


if __name__=='__main__':unittest.main()
