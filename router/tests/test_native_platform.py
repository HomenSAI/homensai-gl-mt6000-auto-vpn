import copy,hashlib,sys,types,unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import native_platform as p
import mt3000_manual_platform as candidate

class Tests(unittest.TestCase):
    def setUp(self):
        self.board={'board_name':'glinet,mt3000-snand','model':'GL.iNet GL-MT3000','kernel':'5.4.211','release':{'target':'mediatek/mt7981'}}
        self.data={'firewall_include':{'path':'/usr/bin/rtp2.sh','type':'script','reload':'0'}}
    def assess(self,board=None,data=None,busy=0,source=b'audited',zones=None):
        with ExitStack()as s:
            s.enter_context(patch.object(p.os,'uname',return_value=types.SimpleNamespace(machine='aarch64')))
            s.enter_context(patch.object(p,'PINS',{'/stock':hashlib.sha256(b'audited').hexdigest()}))
            s.enter_context(patch.object(candidate,'_read',return_value=source))
            s.enter_context(patch.object(candidate,'_zones',return_value=zones if zones is not None else {'lan','wan','wgclient1','ovpnclient1'}))
            s.enter_context(patch.object(candidate,'_workers',return_value={'busy':busy,'verified':True}))
            s.enter_context(patch.object(Path,'exists',return_value=False));s.enter_context(patch.object(Path,'is_symlink',return_value=False))
            return p.assess(self.board if board is None else board,self.data if data is None else data)
    def test_exact_actual_profile_allows_only_after_all_facts_match(self):self.assertEqual(self.assess(),[])
    def test_selected_second_zone_is_required_without_falling_back_to_unused_first(self):
        data=dict(self.data,settings={'plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient2'})
        self.assertEqual(self.assess(data=data,zones={'lan','wan','wgclient1','ovpnclient2'}),[])
        self.assertIn('FW3-SELECTED-ZONE-UNVERIFIED',self.assess(data=data))
    def test_unknown_board_and_incomplete_mt3000_facts_block(self):
        self.assertEqual(self.assess({'board_name':'other'}),['UNSUPPORTED-BOARD'])
        for field,value in(('kernel','6.6'),('release',None),('model','GL-MT6000')):
            b=copy.deepcopy(self.board);b[field]=value;self.assertIn('MT3000-FIRMWARE-UNVERIFIED',self.assess(b))
    def test_wrong_include_and_changed_stock_source_block(self):
        for k,v in(('path','/tmp/other'),('reload','1'),('type','nftables')):
            d=copy.deepcopy(self.data);d['firewall_include'][k]=v;self.assertIn('FW3-INCLUDE-CONTRACT-UNVERIFIED',self.assess(data=d))
        self.assertIn('VENDOR-CODE-CHANGED',self.assess(source=b'changed'))
        self.assertIn('VENDOR-WORKER-BUSY',self.assess(busy=1))
    def test_mt6000_keeps_its_existing_common_guards(self):self.assertEqual(p.assess({'board_name':'glinet,gl-mt6000'},{}),[])
    def wait(self,values,seconds=8):
        clock=[0.];seen=[]
        def sample(end):
            seen.append(clock[0]);return {'busy':values.pop(0)if len(values)>1 else values[0],'verified':True}
        with patch.object(Path,'exists',return_value=False),patch.object(Path,'is_symlink',return_value=False):
            p.wait_quiet(seconds,lambda:clock[0],lambda n:clock.__setitem__(0,clock[0]+n),sample)
        return clock[0],seen
    def test_post_apply_wait_requires_continuous_quiet_after_real_work(self):
        elapsed,seen=self.wait([2,1,0,0,1,0]);self.assertGreaterEqual(elapsed,6);self.assertGreaterEqual(len(seen),8)
    def test_post_apply_stall_and_excessive_work_refuse(self):
        for values in([1],[17],[True]):
            with self.assertRaises(ValueError):self.wait(values,4)

    def test_transient_unverified_read_resets_quiet_streak_without_extending_deadline(self):
        tick=[0.];calls=[0]
        def sample(end):
            calls[0]+=1
            if calls[0] in (2,5):raise ValueError('process read unverified')
            return {'busy':0,'verified':True}
        with patch.object(Path,'exists',return_value=False),patch.object(Path,'is_symlink',return_value=False):
            p.wait_quiet(12,lambda:tick[0],lambda n:tick.__setitem__(0,tick[0]+n),sample)
        self.assertGreaterEqual(tick[0],6);self.assertLess(tick[0],12)

    def test_persistently_unverified_worker_never_counts_as_quiet(self):
        tick=[0.]
        with patch.object(Path,'exists',return_value=False),patch.object(Path,'is_symlink',return_value=False):
            with self.assertRaisesRegex(ValueError,'VENDOR-WORKER-QUIET-UNVERIFIED'):
                p.wait_quiet(4,lambda:tick[0],lambda n:tick.__setitem__(0,tick[0]+n),lambda end:(_ for _ in ()).throw(ValueError('unverified')))
        self.assertEqual(tick[0],4)

if __name__=='__main__':unittest.main()
