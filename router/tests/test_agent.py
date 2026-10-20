import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT/'files/usr/lib/homensai-vpn/agent.py'
sys.path.insert(0, str(AGENT.parent))
spec = importlib.util.spec_from_file_location('native_agent', AGENT)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_tz = os.environ.get('TZ')
        os.environ['TZ'] = 'CET-1CEST,M3.5.0,M10.5.0/3'
        __import__("timezone_compat").refresh_timezone()

    @classmethod
    def tearDownClass(cls):
        if cls.old_tz is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = cls.old_tz
        __import__("timezone_compat").refresh_timezone()

    def test_python38_syntax(self):
        ast.parse(AGENT.read_text(), feature_version=8)

    def test_atomic_storage_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'state.json'
            agent.atomic_json(p, {'safe': 1})
            self.assertEqual(agent.read_json(p), {'safe': 1})
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            self.assertFalse(p.with_name('state.json.pending').exists())

    def test_storage_rejects_final_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p, target = Path(d)/'state', Path(d)/'target'
            target.write_text('original');p.symlink_to(target)
            with self.assertRaises(ValueError):agent.atomic_json(p, {})
            self.assertEqual(target.read_text(), 'original')

    def test_storage_rejects_pending_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'target';target.write_text('original')
            p = Path(d)/'state.json'
            p.with_name('state.json.pending').symlink_to(target)
            with self.assertRaises(OSError):agent.atomic_json(p, {})
            self.assertEqual(target.read_text(), 'original')

    def test_counter_delta_and_reset(self):
        a = agent.Accounting()
        a.sample('wgclient1', 1, 100, 50, 1791970000)
        a.sample('wgclient1', 1, 300, 100, 1791970030)
        a.sample('wgclient1', 1, 1, 1, 1791970060)
        self.assertEqual(sum(v['rx'] for v in a.months.values()), 200)
        self.assertEqual(a.gaps, 1)

    def test_counter_ifindex_change_is_gap(self):
        a = agent.Accounting();a.sample('wgclient1',1,10,10,1791970000)
        a.sample('wgclient1',2,200,100,1791970030)
        self.assertEqual(a.months,{})
        self.assertEqual(a.gaps,1)

    def test_unobserved_time_is_not_counted(self):
        a = agent.Accounting();a.sample('wgclient1',1,10,10,1791970000)
        a.sample('wgclient1',1,200,100,1791970500)
        self.assertEqual(a.months,{})
        self.assertEqual(a.gaps,1)

    def test_month_boundary_and_dst(self):
        boundary=time.mktime((2026,11,1,0,0,0,0,0,-1))
        a=agent.Accounting();a.sample('wgclient1',1,0,0,boundary-10)
        a.sample('wgclient1',1,200,100,boundary+10)
        self.assertEqual(a.months['2026-10']['rx'],100)
        self.assertEqual(a.months['2026-11']['rx'],100)
        self.assertEqual(time.strftime('%z',time.localtime(boundary)),'+0100')

    def test_quality_unknown_does_not_become_server_failure(self):
        a=agent.Accounting()
        for code in ('CHECK-001','SYSTEM-001','ROUTE-001'):
            a.observe({'id':'openvpn:1_2','time':1791970000,'code':code})
        row=list(a.quality['openvpn:1_2']['buckets'].values())[0]
        self.assertEqual(row['n'],0);self.assertEqual(row['unknown'],3)

    def test_quality_and_totals_survive_checkpoint(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)):
            a=agent.Accounting();a.observe({'id':'wireguard:peer_1','time':1791970000,'code':None,'rtt_ms':41})
            agent.checkpoint(a);restored,error=agent.restore()
            self.assertIsNone(error)
            self.assertEqual(restored.quality,a.quality)
            self.assertEqual(restored.previous,{})
            self.assertEqual(restored.gaps,1)

    def test_corrupt_checkpoint_recovers_previous(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)):
            a=agent.Accounting();agent.checkpoint(a);a.gaps=4;agent.checkpoint(a)
            (Path(d)/'checkpoint.json').write_text('broken')
            restored,error=agent.restore()
            self.assertEqual(error,'STORAGE-RECOVERED')
            self.assertEqual(restored.gaps,1)

    def test_both_corrupt_checkpoints_are_reported(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)):
            for name in ('checkpoint.json','checkpoint.backup.json'):(Path(d)/name).write_text('broken')
            a,error=agent.restore();self.assertEqual(error,'STORAGE-001');self.assertEqual(a.months,{})

    def test_dns_validation_rejects_wrong_id_and_truncation(self):
        packet=struct.pack('!2sHHHHH',b'ab',0x8180,1,1,0,0)
        self.assertTrue(agent.valid_dns(packet,b'ab'))
        self.assertFalse(agent.valid_dns(packet,b'cd'))
        self.assertFalse(agent.valid_dns(packet[:8],b'ab'))
        self.assertFalse(agent.valid_dns(struct.pack('!2sHHHHH',b'ab',0x8380,1,1,0,0),b'ab'))

    def test_socket_is_marked_and_bound_before_use(self):
        fake=MagicMock()
        with patch.object(agent.socket,'socket',return_value=fake):
            agent.bound_socket('wgclient1',4096)
        fake.setsockopt.assert_any_call(socket.SOL_SOCKET,agent.SO_BINDTODEVICE,b'wgclient1\0')
        fake.setsockopt.assert_any_call(socket.SOL_SOCKET,agent.SO_MARK,4096)

    def test_binding_refuses_invalid_interface_and_zero_mark(self):
        for interface,mark in (('../bad',1),('wgclient1',0),('x'*20,1)):
            with self.assertRaises(ValueError):agent.bound_socket(interface,mark)

    def test_unbound_profile_is_not_connected_for_testing(self):
        with patch.object(agent,'command') as cmd:
            p=agent.probe({'id':'wireguard:peer_1','interface':None})
            self.assertEqual(p['code'],'PROFILE-INACTIVE');cmd.assert_not_called()

    def test_route_mismatch_prevents_network_probes(self):
        with patch.object(agent,'route_binding',return_value={'code':'ROUTE-001'}),patch.object(agent,'https_probe') as https:
            p=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
            self.assertEqual(p['code'],'ROUTE-001');https.assert_not_called()

    def test_https_quorum_and_dns_classification(self):
        binding={'code':None,'device':'wgclient1','mark':4096,'table':'1001'}
        with patch.object(agent,'route_binding',return_value=binding),patch.object(agent,'https_probe',side_effect=[20,30,None]),patch.object(agent,'dns_probe',return_value=False):
            result=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
            self.assertEqual(result['code'],'DNS-001');self.assertEqual(result['rtt_ms'],25)
            self.assertFalse(result['lan_path_verified'])

    def test_exit_address_is_kept_only_for_healthy_global_ipv4(self):
        binding={'code':None,'device':'wgclient1','mark':4096,'table':'1001'}
        def trace(device,mark,target):
            agent.remember_exit(device,b'fl=1\nip=93.184.216.34\nhttp=http/2\n');return 20.0
        with patch.object(agent,'route_binding',return_value=binding),patch.object(agent,'https_probe',side_effect=trace),patch.object(agent,'dns_probe',return_value=True):
            result=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
        self.assertEqual(result['exit_ip'],'93.184.216.34');self.assertEqual(agent.EXIT_SEEN,{})
        for body in (b'ip=10.0.0.2\n',b'ip=::1\n',b'ip=not-an-ip\n',b'x=1\n'):
            agent.remember_exit('wgclient1',body);self.assertEqual(agent.EXIT_SEEN,{})
        with patch.object(agent,'route_binding',return_value=binding),patch.object(agent,'https_probe',side_effect=trace),patch.object(agent,'dns_probe',return_value=False):
            failed=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
        self.assertNotIn('exit_ip',failed);agent.EXIT_SEEN.clear()

    def test_package_version_comes_from_the_control_file_and_is_never_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            control=Path(d)/'c'
            control.write_text('Package: homensai-auto-vpn\nVersion: 0.8.0-alpha7-1\nArchitecture: all\n')
            self.assertEqual(agent.package_version(control),'0.8.0-alpha7-1')
            for text in ('Version: <b>x</b>\n','Version: '+'1'*60+'\n','Package: x\n'):
                control.write_text(text);self.assertIsNone(agent.package_version(control))
            self.assertIsNone(agent.package_version(Path(d)/'missing'))
            control.write_bytes(b'x'*9000);self.assertIsNone(agent.package_version(control))

    def test_rpc_list_and_acl_include_operator_return(self):
        self.assertIn('native_return',(ROOT/'files/usr/share/rpcd/acl.d/luci-app-homensai-vpn.json').read_text())
        out=io.StringIO()
        with contextlib.redirect_stdout(out):agent.rpc('list')
        self.assertIn('native_return',json.loads(out.getvalue()))

    def test_no_route_evidence_is_not_internet_health(self):
        outputs=[{'up':True,'l3_device':'wgclient1'},[{'dev':'wgclient1','dst':'default','table':1001}],[]]
        with patch.object(agent,'command',side_effect=[json.dumps(v).encode() for v in outputs]):
            self.assertEqual(agent.route_binding('wgclient1')['code'],'CHECK-001')

    def test_rpc_cannot_execute_commands(self):
        incoming=types.SimpleNamespace(buffer=io.BytesIO(b'{"command":"anything"}'))
        with patch.object(sys,'stdin',incoming):
            with self.assertRaises(ValueError):agent.rpc('scan')

    def test_rpc_accepts_framework_session_without_echo(self):
        output=io.StringIO()
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)),patch.object(sys,'stdin',types.SimpleNamespace(buffer=io.BytesIO(b'{"ubus_rpc_session":"SESSION_SENTINEL"}'))),contextlib.redirect_stdout(output):
            agent.rpc('scan')
        self.assertIn('queued',output.getvalue())
        self.assertNotIn('SESSION_SENTINEL',output.getvalue())

    def test_rpc_scan_only_creates_fixed_request(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'RUNTIME',Path(d)),patch.object(sys,'stdin',types.SimpleNamespace(buffer=io.BytesIO(b'{}'))),contextlib.redirect_stdout(io.StringIO()):
            agent.rpc('scan');self.assertTrue((Path(d)/'scan.request').exists())

    def test_one_daemon_iteration_publishes_real_mode(self):
        with tempfile.TemporaryDirectory() as d:
            runtime,persist=Path(d)/'run',Path(d)/'persist'
            inv={'profiles':[{'id':'wireguard:peer_1','name':'Test','protocol':'wireguard','interface':'wgclient1','vendor_tunnel_id':'wireguard:wgclient1'}],'servers':[], 'settings':{'interval':30,'checkpoint':900,'probe_limit':16}}
            result={'id':'wireguard:peer_1','time':time.time(),'code':None,'device':'wgclient1','rtt_ms':32}
            real_write=agent.atomic_json
            def write(path,value):
                real_write(path,value)
                if path.name=='status.json':agent.STOP=True
            agent.STOP=False
            with patch('auto_control.RUNTIME',runtime),patch('auto_control.PERSIST',persist),patch.object(agent,'RUNTIME',runtime),patch.object(agent,'PERSIST',persist),patch.object(agent,'inventory',return_value=inv),patch.object(agent,'probe',return_value=result),patch.object(agent,'sample_counters'),patch.object(agent,'atomic_json',side_effect=write):
                agent.serve()
            status=json.loads((runtime/'status.json').read_text())
            self.assertEqual(status['mode'],'monitor')
            self.assertFalse(status['capabilities']['native_apply'])
            self.assertFalse(status['failover_plan']['applied'])
            self.assertEqual(status['failover_plan']['mode'],'dry-run')
            self.assertEqual(status['profiles'][0]['rtt_ms'],32)
            agent.STOP=False


if __name__=='__main__':unittest.main()
