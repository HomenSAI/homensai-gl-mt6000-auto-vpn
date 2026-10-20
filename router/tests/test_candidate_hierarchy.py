from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from candidate_hierarchy import rank_candidates
from vendor_fixture import attach

class HierarchyTests(unittest.TestCase):
    def fixture(self):
        ids={name:proto+':'+name for name,proto in [('a','openvpn'),('b','openvpn'),('c','openvpn'),('d','wireguard')]}
        profiles=[{'id':ids[name],'interface':'vpn'+name,'protocol':proto} for name,proto in [('a','openvpn'),('b','openvpn'),('c','openvpn'),('d','wireguard')]]
        metadata=[{'profile':ids[name],'channel':channel,'priority':priority,'enabled':True} for name,channel,priority in [('a','main',1),('b','main',99),('c','reserve',1),('d','main',1)]]
        samples=[{'id':ids[name],'time':stamp,'code':None,'dns_ok':True,'https_success':2} for name in 'bcd' for stamp in (970,990)]
        status=attach({'profiles':profiles,'samples':samples})
        return profiles,metadata,samples,status['vendor_observation']

    def test_hierarchy_before_priority(self):
        p,m,s,o=self.fixture();rows=rank_candidates(p,m,s,'openvpn:a',1000,observation=o)
        self.assertEqual([r['id'].split(':')[-1] for r in rows],list('cbd'))
        self.assertEqual([r['transition'] for r in rows],['channel','channel','protocol'])

    def test_256_health_binding_metadata_combinations(self):
        for mask in range(256):
            with self.subTest(mask=mask):
                p,m,s,o=self.fixture()
                for i,name in enumerate('bcd'):
                    if mask&(1<<i):
                        for point in s:
                            if point['id'].split(':')[-1]==name:point['code']='DNS-001'
                    if mask&(1<<(i+3)):p[i+1]['interface']=None
                if mask&64:m[1]['enabled']=False
                if mask&128:p[3]['protocol']='wifi'
                rows=rank_candidates(p,m,s,'openvpn:a',1000,observation=o)
                expected=[name for name in 'cbd' if not(mask&(1<<'bcd'.index(name)) or mask&(1<<('bcd'.index(name)+3)) or (name=='b' and mask&64) or (name=='d' and mask&128))]
                self.assertEqual([r['id'].split(':')[-1] for r in rows],expected)
                self.assertTrue(all(r['mode']=='recommendation-only' for r in rows))

    def test_stale_samples_cannot_recommend(self):
        p,m,s,o=self.fixture();self.assertEqual(rank_candidates(p,m,s,'openvpn:a',2000,observation=o),[])
