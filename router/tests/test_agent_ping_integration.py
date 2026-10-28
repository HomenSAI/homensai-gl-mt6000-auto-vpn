"""Optional Ping infrastructure failures must not change monitor health or Auto data."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import icmp_ping


class PingIntegrationTests(unittest.TestCase):
    def test_failed_optional_sampler_does_not_fail_the_monitor_pass(self):
        profile=dict(id='wireguard:peer_1',section='peer_1',name='Example',protocol='wireguard',interface='wgclient1',
                     administrative_state='enabled',vendor_tunnel_id='wireguard:wgclient1')
        data={'profiles':[profile],'servers':[],'wan_interfaces':[],
              'settings':{'interval':30,'checkpoint':900,'probe_limit':2,'plan_enabled':False}}
        measured=dict(id=profile['id'],time=time.time(),device='wgclient1',mark=4096,table='1001',ifindex=7,
                      code=None,dns_ok=True,https_success=3,rtt_ms=25,administrative_state='enabled')
        with tempfile.TemporaryDirectory()as directory,ExitStack()as stack:
            root=Path(directory)
            for name,value in [('RUNTIME',root),('PERSIST',root),('STOP',False)]:stack.enter_context(patch.object(agent,name,value))
            stack.enter_context(patch('auto_control.RUNTIME',root));stack.enter_context(patch('auto_control.PERSIST',root))
            stack.enter_context(patch.object(agent,'inventory',return_value=data))
            stack.enter_context(patch('website_response.WebsiteSampler'))
            stack.enter_context(patch.object(agent,'probe',return_value=measured))
            stack.enter_context(patch.object(agent,'restore',return_value=(agent.Accounting(),None)))
            stack.enter_context(patch.object(agent,'sample_counters'));stack.enter_context(patch.object(agent,'sample_wan_counters',return_value=[]))
            stack.enter_context(patch.object(agent,'checkpoint'))
            stack.enter_context(patch('telegram_report.deliver',return_value=({'enabled':False},{},False)))
            stack.enter_context(patch('system_readiness.snapshot',return_value={}))
            stack.enter_context(patch('speed_test.observe_traffic'));stack.enter_context(patch('speed_test.automatic_new',return_value=set()))
            stack.enter_context(patch('speed_test.active_job',return_value=False));stack.enter_context(patch('speed_test.cancel'))
            sampler=stack.enter_context(patch.object(icmp_ping,'PingSampler')).return_value
            sampler.apply.side_effect=OSError('PRIVATE_SENTINEL')
            def finish(_):agent.STOP=True
            stack.enter_context(patch.object(agent.time,'sleep',side_effect=finish))
            agent.serve();sampler.apply.assert_called_once();sampler.close.assert_called_once()
            status=agent.read_json(root/'status.json')
            self.assertNotIn('error',status);row=status['profiles'][0]
            self.assertIsNone(row['code']);self.assertTrue(row['dns_ok']);self.assertEqual(row['https_success'],3);self.assertEqual(row['rtt_ms'],25)
            self.assertEqual(row['ping']['code'],'PING-UNAVAILABLE');self.assertIsNone(row['ping']['rtt_ms'])
            self.assertNotIn('PRIVATE',str(status))


if __name__=='__main__':unittest.main()
