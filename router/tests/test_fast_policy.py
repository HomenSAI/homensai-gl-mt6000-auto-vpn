"""Fast switch: the committed route_policy order goes to the kernel in one atomic restore; anything odd falls back."""
import subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import fast_policy as f
import native_switch as n

UCI="""route_policy.gl_process_vpn=rule_process
route_policy.gl_process_vpn.from='20000'
route_policy.gl_process_vpn.tunnel_id='10100'
route_policy.gl_process_vpn.enabled='1'
route_policy.gl_process_vpn.via='ovpnclient2'
route_policy.gl_process_vpn.mark='0xb000'
route_policy.@rule[0].tunnel_id='4192'
route_policy.@rule[0].mark='0xb000'
route_policy.@rule[1].tunnel_id='5841'
route_policy.@rule[1].mark='0x1000'
"""
MANGLE="""*mangle
-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000
-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN
-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY
-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY
-A TUNNEL10100_LOCAL_POLICY -m comment --comment "TUNNEL10100 rule for set mark" -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000
-A TUNNEL10100_LOCAL_POLICY -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j VPN_LOCAL_POLICY_DROP
-A TUNNEL4192_ROUTE_POLICY -m comment --comment "TUNNEL4192 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000
-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000
COMMIT
"""


class Plan(unittest.TestCase):
    def test_reorders_jumps_and_local_mark_in_one_payload(self):
        order,local,mark=f.uci_rules(UCI)
        self.assertEqual((order,local,mark),(['4192','5841'],'10100','0xb000'))
        payload,old,changed=f.plan(MANGLE,order,local,mark)
        self.assertTrue(changed);self.assertEqual(old,'5841')
        lines=payload.splitlines()
        self.assertEqual(lines[:2],['*mangle',':ROUTE_POLICY - [0:0]'])
        jumps=[l.split('-j ')[-1] for l in lines if l.startswith('-A ROUTE_POLICY') and 'TUNNEL' in l]
        self.assertEqual(jumps,['TUNNEL4192_ROUTE_POLICY','TUNNEL5841_ROUTE_POLICY'])
        self.assertIn('--set-xmark 0xb000/0xf000',[l for l in lines if 'TUNNEL10100 rule' in l][0])
        self.assertEqual(lines[-1],'COMMIT');self.assertEqual(f.mark_of(MANGLE,old),'0x1000')

    def test_already_applied_changes_nothing(self):
        payload,old,changed=f.plan(MANGLE,['5841','4192'],'10100','0x1000');self.assertFalse(changed)

    def test_anything_unexpected_falls_back(self):
        for bad_mangle in (MANGLE.replace('-j TUNNEL4192_ROUTE_POLICY\n','-j TUNNEL9999_ROUTE_POLICY\n'),
                           MANGLE.replace('-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY\n',''),
                           MANGLE.replace('--set-xmark 0x1000/0xf000\n-A TUNNEL10100_LOCAL_POLICY -m connmark','--set-xmark 0x1000/0xffff\n-A TUNNEL10100_LOCAL_POLICY -m connmark')):
            with self.assertRaises(f.Unsupported):f.plan(bad_mangle,['4192','5841'],'10100','0xb000')
        for bad_uci in (UCI.replace("@rule[1].tunnel_id='5841'","@rule[1].tunnel_id='4192'"),UCI.replace("gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='bad'"),
                        UCI+"route_policy.@rule[2].tunnel_id='7'\n"):
            with self.assertRaises(f.Unsupported):f.uci_rules(bad_uci)


class Apply(unittest.TestCase):
    def setUp(self):
        import tempfile;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        p=patch.object(n,'RUNTIME',Path(self.tmp.name));p.start();self.addCleanup(p.stop)

    def backend(self):
        return n.Linux.__new__(n.Linux)

    def test_fast_path_restores_once_verifies_and_drops_old_flows(self):
        state={'mangle':MANGLE};writes=[]
        commands=[]
        def command(args,timeout=5):
            if args[:2]==['uci','show']:return UCI.encode()
            if args[0]=='iptables-save':return state['mangle'].encode()
            if args[0]=='conntrack':commands.append('conntrack');raise subprocess.CalledProcessError(1,args)
            raise AssertionError(args)
        def write(args,timeout=5):
            writes.append(args[0])
            if args[0]=='iptables-restore':
                payload=open(args[2]).read();order=[l for l in payload.splitlines() if l.startswith('-A ')]
                state['mangle']=MANGLE.replace('-j TUNNEL5841_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
                    '-j TUNNEL4192_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY').replace(
                    'gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000','gid-owner 20000 -j MARK --set-xmark 0xb000/0xf000')
                return b''
            raise AssertionError('only the kernel restore goes through the fenced writer: '+args[0])
        with patch.object(n,'command',side_effect=command):
            result=self.backend().apply_fast(write)
        self.assertEqual(writes,['iptables-restore']);self.assertEqual(commands,['conntrack']);self.assertTrue(result['used']);self.assertTrue(result['changed'])

    def test_kernel_not_changed_by_restore_is_refused(self):
        def command(args,timeout=5):return UCI.encode() if args[:2]==['uci','show'] else MANGLE.encode()
        with patch.object(n,'command',side_effect=command),self.assertRaises(n.Refused):
            self.backend().apply_fast(lambda args,timeout=5:b'')

    def test_owner_can_turn_it_off(self):
        cfg=Path(self.tmp.name)/'homensai_vpn'
        with patch.object(n,'FAST_SWITCH_CONFIG',cfg):
            self.assertFalse(n.fast_switch_enabled(),'no package config: never')
            cfg.write_text("config main 'main'\n    option enabled '1'\n");self.assertTrue(n.fast_switch_enabled())
            cfg.write_text("config main 'main'\n    option fast_switch '0'\n");self.assertFalse(n.fast_switch_enabled())

if __name__=='__main__':unittest.main()
