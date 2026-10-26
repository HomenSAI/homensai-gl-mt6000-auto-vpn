import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import MagicMock,patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent


class Tests(unittest.TestCase):
    def test_http_505_is_endpoint_incompatibility_without_failing_two_valid_https_results(self):
        binding={'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':4}
        def response(*args):
            row=MagicMock();target=agent.EXIT_CONTEXT.probe_detail['target']
            row.status=505 if target=='dns.quad9.net'else 200
            row.read.return_value=(b'ip=93.184.216.34\nhttp=http/1.1\n'if target=='one.one.one.one'else b'{"Status":0,"Answer":[{}]}')
            if row.status==505:row.read.side_effect=AssertionError('do not download unsupported protocol error pages')
            return row
        with patch.object(agent,'route_binding',return_value=binding),patch.object(agent,'bound_socket'),patch.object(agent.ssl,'create_default_context'),patch.object(agent.http.client,'HTTPResponse',side_effect=response),patch.object(agent,'dns_probe',return_value=True):
            row=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
        self.assertIsNone(row['code']);self.assertEqual(row['https_success'],2)
        details={r['target']:r for r in row['probe_checks']}
        self.assertEqual(details['dns.quad9.net']['http_status'],505)
        self.assertEqual(details['dns.quad9.net']['result'],'http-unsupported')
        self.assertEqual(details['dns.google']['result'],'ok')

    def test_partial_dns_success_keeps_per_target_timeout_without_error_text_or_secrets(self):
        binding={'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':4}
        def probe(device,mark,target):
            if target[1]=='one.one.one.one':return 42
            raise socket.timeout('PRIVATE-DETAIL-MUST-NOT-LEAK')
        with patch.object(agent,'route_binding',return_value=binding),patch.object(agent,'https_probe',side_effect=probe),patch.object(agent,'dns_probe',return_value=True):
            row=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
        self.assertEqual(row['code'],'VPN-003');self.assertTrue(row['dns_ok']);self.assertEqual(row['https_success'],1)
        self.assertEqual([r['result']for r in row['probe_checks']],['ok','timeout','timeout'])
        self.assertNotIn('PRIVATE-DETAIL',json.dumps(row))

    def test_route_epoch_change_discards_endpoint_results_for_the_previous_binding(self):
        before={'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':4}
        with patch.object(agent,'route_binding',side_effect=[before,dict(before,ifindex=5)]),patch.object(agent,'https_probe',return_value=20),patch.object(agent,'dns_probe',return_value=True):
            row=agent.probe({'id':'wireguard:peer_1','interface':'wgclient1'})
        self.assertEqual(row['code'],'VENDOR-IDENTITY-CHANGED')
        self.assertNotIn('https_success',row);self.assertNotIn('probe_checks',row)


if __name__=='__main__':unittest.main()
