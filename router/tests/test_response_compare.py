"""Owner option "measure all methods": per-method hourly comparison for the Auto pair, display only."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,icmp_ping,setup_config
from response_compare import ResponseCompare,enabled

NOW=180000
PAIR={'source':'wireguard:peer_1','target':'openvpn:1_2'}


def row(identifier,interface,ping=None,extra=None,site=None,stamp=NOW):
    base={'id':identifier,'interface':interface,'vendor_tunnel_id':'x:'+interface,'vendor_generation':'a'*32,'time':stamp}
    def sample(target,rtt):
        return dict(icmp_ping.public(base,'ok' if rtt is not None else 'failed',None,stamp,rtt,target),valid_for=60)
    if ping is not None:base['ping']=sample('1.1.1.1',ping)
    if extra:base['ping_compare']={t:sample(t,v) for t,v in extra.items()}
    if site is not None:base['website_response']={'state':'ok','avg_ms':site,'time':stamp,'valid_for':60,'interface':interface}
    return base


class CompareTests(unittest.TestCase):
    def status(self,stamp=NOW,**kw):
        return {'profiles':[row(PAIR['source'],'wgclient1',stamp=stamp,**kw),row(PAIR['target'],'ovpnclient2',ping=140.0,stamp=stamp),
                            row('wireguard:other','wgclient9',ping=5.0,stamp=stamp)]}

    def test_every_method_is_kept_per_channel_and_only_for_the_pair(self):
        h=ResponseCompare();h.observe(self.status(ping=30.0,extra={'8.8.8.8':40.0,'9.9.9.9':None},site=400.0),PAIR,NOW)
        p=h.public(NOW)
        self.assertEqual(p['methods'],['icmp-1.1.1.1','icmp-8.8.8.8','icmp-9.9.9.9','websites'])
        self.assertEqual(p['profiles'][PAIR['source']]['icmp-8.8.8.8'],{'avg_ms':40.0,'ok':1,'failed':0})
        self.assertEqual(p['profiles'][PAIR['source']]['icmp-9.9.9.9'],{'avg_ms':None,'ok':0,'failed':1})
        self.assertEqual(p['profiles'][PAIR['source']]['websites']['avg_ms'],400.0)
        self.assertNotIn('wireguard:other',p['profiles'])

    def test_same_sample_counts_once_and_old_hours_expire(self):
        h=ResponseCompare();s=self.status(ping=30.0)
        h.observe(s,PAIR,NOW);h.observe(s,PAIR,NOW+5)
        self.assertEqual(h.public(NOW)['profiles'][PAIR['source']]['icmp-1.1.1.1']['ok'],1)
        h.observe(self.status(stamp=NOW+8*86400,ping=20.0),PAIR,NOW+8*86400)
        self.assertEqual(h.public(NOW+8*86400)['profiles'][PAIR['source']]['icmp-1.1.1.1'],{'avg_ms':20.0,'ok':1,'failed':0})

    def test_save_load_clear(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'c.json';h=ResponseCompare();h.observe(self.status(ping=30.0),PAIR,NOW);h.save(path,agent.atomic_json,NOW)
            self.assertEqual(ResponseCompare.load(path).public(NOW)['profiles'],h.public(NOW)['profiles'])
            path.write_text('{broken');self.assertEqual(ResponseCompare.load(path).notice,'RESPONSE-COMPARE-UNAVAILABLE')
        h.clear();self.assertEqual(h.public(NOW)['methods'],[])

    def test_compare_sampler_never_touches_the_chosen_ping(self):
        sampler=icmp_ping.PingSampler(lambda:{},lambda name:{},compare=True);sampler.configure(30,'8.8.8.8')
        r={'id':'wireguard:other'};sampler.apply([r],PAIR,NOW)
        self.assertNotIn('ping',r);self.assertNotIn('ping_compare',r)
        r={'id':PAIR['source']};sampler.apply([r],PAIR,NOW)
        self.assertNotIn('ping',r);self.assertIn('8.8.8.8',r['ping_compare'])

    def test_setting_is_strict_and_optional(self):
        self.assertTrue(enabled({'response_compare':True}));self.assertFalse(enabled({'response_compare':'1'}))
        self.assertEqual(setup_config.response_payload({'metric':'icmp-1.1.1.1','compare':True})['main'],{'response_metric':'icmp-1.1.1.1','response_compare':'1'})
        self.assertEqual(setup_config.response_payload({'metric':'websites'})['main'],{'response_metric':'websites'})
        for bad in ({'metric':'icmp-1.1.1.1','compare':1},{'metric':'icmp-1.1.1.1','compare':True,'x':1}):
            with self.assertRaises(ValueError):setup_config.response_payload(bad)


if __name__=='__main__':unittest.main()
