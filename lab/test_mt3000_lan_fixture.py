"""No namespace/router commands: verify scope, conflicts and cleanup identities."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import mt3000_lan_fixture as F


class Tests(unittest.TestCase):
    def plan(self,**changes):
        args=dict(nonce='0123456789ab',bridge={'ifname':'br-lan','ifindex':7,'address':'94:83:c4:11:22:33'},
                  lan_address='192.168.11.1/24',pool=(100,150),reserved=[],leased=[])
        args.update(changes)
        return F.fixture_plan(**args)

    def test_plan_is_exact_dedicated_lan_and_high_mac_does_not_replace_bridge(self):
        p=self.plan()
        self.assertLessEqual(len(p['host']),15);self.assertLessEqual(len(p['peer']),15)
        self.assertGreater(p['host_mac'],p['bridge']['address']);self.assertGreater(p['peer_mac'],p['bridge']['address'])
        self.assertEqual(p['address'],'192.168.11.250');self.assertEqual(p['namespace'],'hvlan-01234567')

    def test_different_router_lan_never_becomes_target(self):
        for value in ('192.168.8.1/24','192.168.11.1/16','192.168.11.2/24'):
            with self.assertRaisesRegex(F.Refused,'FIXTURE-LAN-LAYOUT'):self.plan(lan_address=value)

    def test_existing_reserved_leased_or_pool_address_refuses(self):
        for change in ({'reserved':['192.168.11.250']},{'leased':['192.168.11.250']},{'pool':(200,55)}):
            with self.assertRaises(F.Refused):self.plan(**change)

    def test_unknown_or_malformed_dhcp_is_not_assumed_free(self):
        for value in ((-1,1),(1,0),(True,1),(100,200),[],(1,)):
            with self.assertRaises(F.Refused):self.plan(pool=value)

    def test_unknown_or_larger_bridge_mac_refuses(self):
        for mac in ('', 'xx:xx:xx:xx:xx:xx','ff:ff:ff:ff:ff:ff','fe:ff:ff:ff:ff:ff'):
            with self.assertRaises(F.Refused):self.plan(bridge={'ifname':'br-lan','ifindex':7,'address':mac})

    def test_unsafe_names_and_nonce_refuse_before_commands(self):
        for nonce in ('../bad','; reboot','0'*11,'0'*13,None,True):
            with self.assertRaises(F.Refused):self.plan(nonce=nonce)
        with self.assertRaises(F.Refused):self.plan(bridge={'ifname':'eth0','ifindex':7,'address':'94:83:c4:11:22:33'})

    def test_replaced_host_interface_is_never_deleted(self):
        p=self.plan();p.update(host_index=12,namespace_inode=99)
        class FakePath:
            def __init__(self,*args):self.name=args[-1]
            def exists(self):return self.name==p['host']
        with patch.object(F,'Path',FakePath),patch.object(F,'link',return_value={'ifindex':13,'address':p['host_mac']}),patch.object(F,'command') as cmd:
            with self.assertRaisesRegex(F.Refused,'CLEANUP-LINK-IDENTITY'):F.cleanup(Path('/tmp/unused'),p)
            cmd.assert_not_called()

    def test_replaced_namespace_is_never_deleted(self):
        p=self.plan();p.update(host_index=12,namespace_inode=99)
        class FakePath:
            def __init__(self,*args):self.name=args[-1]
            def exists(self):return self.name==p['namespace']
            def stat(self):return SimpleNamespace(st_ino=100)
        with patch.object(F,'Path',FakePath),patch.object(F,'command') as cmd:
            with self.assertRaisesRegex(F.Refused,'CLEANUP-NAMESPACE-IDENTITY'):F.cleanup(Path('/tmp/unused'),p)
            cmd.assert_not_called()

    def test_bridge_identity_uses_both_index_and_mac(self):
        p=self.plan()
        for change in ({'ifindex':8},{'address':'94:83:c4:11:22:34'}):
            current=dict(p['bridge'],**change)
            with patch.object(F,'link',return_value=current):
                with self.assertRaisesRegex(F.Refused,'MANAGEMENT-DRIFT'):F.bridge_unchanged(p)

    def test_pid_reuse_is_not_alive_and_zombie_is_terminal(self):
        record=dict(pid=42,start='100',pgid=42,state='S')
        for change in ({'start':'101'},{'pgid':43},{'state':'Z'}):
            with patch.object(F,'proc',return_value=dict(record,**change)):self.assertFalse(F.alive(record))
        with patch.object(F,'proc',return_value=record):self.assertTrue(F.alive(record))


if __name__=='__main__':unittest.main()
