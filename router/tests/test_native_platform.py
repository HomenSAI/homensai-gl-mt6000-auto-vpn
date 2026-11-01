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


class FileCache(unittest.TestCase):
    """TODO-PERF 4.1 on real files: a change between passes is always seen; nothing is reused across a change."""
    def setUp(self):
        import tempfile
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'fw3.state';p.forget_derived()
        self.addCleanup(p.forget_derived)
    def write(self,text,age=100):
        import os,time
        self.path.write_text(text);stamp=time.time()-age;os.utime(self.path,(stamp,stamp))
    def zones(self,later=10):
        # the wall clock `later` seconds on: the file's ctime (set now by utime) is then old enough to be trusted
        import time
        now=time.time()
        with patch.object(p,'FW3_STATE',str(self.path)),patch.object(p.time,'time',return_value=now+later):return p.fw3_zones()
    def test_unchanged_old_file_is_parsed_once_and_a_rewrite_is_seen(self):
        good=''.join(line+chr(10) for line in ('package fw3_state','config defaults','config zone',"option name 'lan'",'config zone',
                                                 "option name 'wan'",'config zone',"option name 'wgclient1'"))
        self.write(good)
        calls=[]
        real=candidate._zones
        with patch.object(candidate,'_zones',side_effect=lambda text:calls.append(1) or real(text)):
            self.assertEqual(self.zones(),{'lan','wan','wgclient1'});self.zones();self.zones()
            self.assertEqual(len(calls),1)
            # same size, the old mtime restored: the ctime still moves (it cannot be set back)
            import os,time
            before=os.lstat(self.path)
            time.sleep(1.1)
            self.path.write_text(good.replace('wgclient1','wgclient2'));os.utime(self.path,ns=(before.st_atime_ns,before.st_mtime_ns))
            self.assertEqual(os.lstat(self.path).st_size,before.st_size)
            self.assertEqual(self.zones(),{'lan','wan','wgclient2'})
            self.assertEqual(len(calls),2)
    def test_young_file_is_read_every_time(self):
        good=''.join(line+chr(10) for line in ('package fw3_state','config defaults','config zone',"option name 'lan'",'config zone',"option name 'wan'"))
        self.write(good,age=0)
        self.assertEqual(self.zones(later=0),{'lan','wan'})
        self.path.write_text(good.replace("'wan'","'wax'"))  # same second, same size
        with self.assertRaises(ValueError):self.zones(later=0)  # no wan zone: the new text was parsed
    def test_failed_parse_and_missing_file_leave_no_entry(self):
        self.write('not fw3')
        for _ in range(2):
            with self.assertRaises(ValueError):self.zones()
        self.path.unlink()
        with self.assertRaises(ValueError):self.zones()
    def test_sha_file_follows_the_file(self):
        self.write('one');first=p.sha_file(str(self.path),262144)
        self.assertEqual(first,hashlib.sha256(b'one').hexdigest())
        self.write('two',age=50);self.assertEqual(p.sha_file(str(self.path),262144),hashlib.sha256(b'two').hexdigest())


if __name__=='__main__':unittest.main()
