import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import server_endpoint as endpoint

class EndpointTest(unittest.TestCase):
    def test_address_rejects_credentials_unknown_and_local_control_sockets(self):
        self.assertEqual(endpoint.address('198.51.100.8:1194'),('198.51.100.8',1194))
        self.assertEqual(endpoint.address('[2001:db8::1]:51820'),('2001:db8::1',51820))
        for value in ['(none)','host.example:443','user:secret@198.51.100.1:443','127.0.0.1:7505','0.0.0.0:0','198.51.100.1:65536','https://198.51.100.1:443']:
            with self.assertRaises(ValueError):endpoint.address(value)

    def test_only_owned_established_socket_is_exposed(self):
        text='header\n0: 00000000:0000 086433C6:04AA 01 0 0 0 0 0 55\n1: 00000000:0000 096433C6:01BB 01 0 0 0 0 0 99\n2: 00000000:0000 0A6433C6:01BB 02 0 0 0 0 0 55\n'
        self.assertEqual(endpoint.socket_peers(text,{'55'},'tcp'),{('198.51.100.8',1194,'tcp')})
        self.assertEqual(endpoint.socket_peers(text,{'missing'},'tcp'),set())

    def test_epoch_ignores_normal_cpu_counters_and_rejects_truncation(self):
        fields=['S']+['0']*18+['12345']+['0']*8
        before='123 (openvpn) '+' '.join(fields)
        fields[11]='99'
        self.assertEqual(endpoint.process_epoch(before),endpoint.process_epoch('123 (openvpn) '+' '.join(fields)))
        for value in ['','123 (openvpn) S','no closing parenthesis']:
            with self.assertRaises(ValueError):endpoint.process_epoch(value)

    def test_wireguard_single_peer_interface_epoch_and_ambiguity(self):
        profile={'id':'wireguard:peer_1','protocol':'wireguard','interface':'wgclient1'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'sys/class/net/wgclient1/ifindex';path.parent.mkdir(parents=True);path.write_text('7\n')
            found=endpoint.observe(profile,100,root,lambda _:b'public-key-not-exported\t198.51.100.2:51820\n')
            self.assertEqual(found['host'],'198.51.100.2');self.assertNotIn('key',json.dumps(found))
            self.assertEqual(found['profile'],profile['id']);self.assertEqual(found['source'],'live-kernel-peer')
            self.assertIsNone(endpoint.observe(profile,100,root,lambda _:b'a\t198.51.100.2:51820\nb\t198.51.100.3:51820\n'))
            def changed(_):path.write_text('8\n');return b'a\t198.51.100.2:51820\n'
            self.assertIsNone(endpoint.observe(profile,100,root,changed))

    def test_untrusted_identity_and_missing_evidence_never_runs_command(self):
        for interface in ['wgclient1; reboot','eth0','../../etc/shadow','wgclient100000']:
            runner=mock.Mock();self.assertIsNone(endpoint.observe({'id':'wireguard:peer_1','protocol':'wireguard','interface':interface},100,runner=runner));runner.assert_not_called()
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(endpoint.observe({'id':'openvpn:1_1','protocol':'openvpn','interface':'ovpnclient1'},100,Path(root)))

if __name__=='__main__':unittest.main()
