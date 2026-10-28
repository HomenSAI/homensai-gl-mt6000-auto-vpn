"""Optional website display measurement cannot change the existing health quorum."""
from contextlib import ExitStack
from pathlib import Path
import sys,tempfile,time,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,website_response as web


class WebsiteIntegration(unittest.TestCase):
    def iteration(self,fail,history_fail=False):
        profile={'id':'wireguard:peer_1','section':'peer_1','name':'Example','protocol':'wireguard','interface':'wgclient1',
                 'administrative_state':'enabled','vendor_tunnel_id':'wireguard:wgclient1'}
        data={'profiles':[profile],'servers':[],'wan_interfaces':[],'settings':{'interval':30,'checkpoint':900,'probe_limit':2,'plan_enabled':False}}
        measured=dict(id=profile['id'],time=time.time(),device='wgclient1',mark=4096,table='1001',ifindex=7,
                      code=None,dns_ok=True,https_success=3,rtt_ms=1400,administrative_state='enabled')
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            root=Path(directory)
            for name,value in [('RUNTIME',root),('PERSIST',root),('STOP',False)]:stack.enter_context(patch.object(agent,name,value))
            stack.enter_context(patch('auto_control.RUNTIME',root));stack.enter_context(patch('auto_control.PERSIST',root))
            stack.enter_context(patch.object(agent,'inventory',return_value=data));stack.enter_context(patch.object(agent,'probe',return_value=measured))
            stack.enter_context(patch.object(agent,'restore',return_value=(agent.Accounting(),None)))
            stack.enter_context(patch.object(agent,'sample_counters'));stack.enter_context(patch.object(agent,'sample_wan_counters',return_value=[]))
            stack.enter_context(patch.object(agent,'checkpoint'));stack.enter_context(patch('icmp_ping.PingSampler'))
            stack.enter_context(patch('telegram_report.deliver',return_value=({'enabled':False},{},False)))
            stack.enter_context(patch('system_readiness.snapshot',return_value={}))
            stack.enter_context(patch('speed_test.observe_traffic'));stack.enter_context(patch('speed_test.automatic_new',return_value=set()))
            stack.enter_context(patch('speed_test.active_job',return_value=False));stack.enter_context(patch('speed_test.cancel'))
            sampler=stack.enter_context(patch.object(web,'WebsiteSampler')).return_value
            if history_fail:stack.enter_context(patch('website_response_history.WebsiteResponseHistory.observe',side_effect=ValueError('PRIVATE_SENTINEL')))
            def applied(rows,pair,now):
                rows[0]['website_response']=web.public(rows[0],'ok',None,now,[{'id':t[0],'url':'https://'+t[1]+t[2],'state':'ok','code':None,'elapsed_ms':ms} for t,ms in zip(web.TARGETS,(100,200,300))])
            sampler.apply.side_effect=OSError('PRIVATE_SENTINEL') if fail else applied
            stack.enter_context(patch.object(agent.time,'sleep',side_effect=lambda _:setattr(agent,'STOP',True)))
            agent.serve();sampler.apply.assert_called_once();sampler.close.assert_called_once()
            status=agent.read_json(root/'status.json');self.assertNotIn('error',status);self.assertNotIn('PRIVATE',str(status))
            self.assertEqual(status['profiles'][0]['rtt_ms'],1400);self.assertEqual(status['profiles'][0]['https_success'],3)
            self.assertTrue(status['profiles'][0]['dns_ok']);self.assertIsNone(status['profiles'][0]['code'])
            self.assertEqual(status['website_response_history']['metric'],web.METRIC)
            if history_fail:self.assertEqual(status['website_response_history']['notice'],'WEBSITE-HISTORY-UNAVAILABLE')
            return status['profiles'][0]['website_response']

    def test_failed_new_sampler_is_separate_from_health_and_old_rtt(self):
        value=self.iteration(True);self.assertEqual(value['code'],'WEBSITE-UNAVAILABLE');self.assertIsNone(value['avg_ms'])

    def test_new_three_site_mean_is_published_without_relabeling_the_old_measurement(self):
        value=self.iteration(False);self.assertEqual(value['avg_ms'],200);self.assertEqual(value['successes'],3)

    def test_optional_history_failure_does_not_discard_valid_health_or_new_measurement(self):
        self.assertEqual(self.iteration(False,True)['avg_ms'],200)

    def test_two_checkpoints_preserve_corrupt_new_history_bytes_and_protection_notice(self):
        from website_response_history import WebsiteResponseHistory
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'website-response-history.json';raw=b'{broken original evidence\n';path.write_bytes(raw)
            history=WebsiteResponseHistory.load(path);self.assertEqual(history.notice,'WEBSITE-HISTORY-UNAVAILABLE')
            with patch.object(agent,'PERSIST',root):
                agent.checkpoint(agent.Accounting(),website_response=history)
                agent.checkpoint(agent.Accounting(),website_response=history)
            self.assertEqual(path.read_bytes(),raw);self.assertEqual(history.notice,'WEBSITE-HISTORY-UNAVAILABLE')


if __name__=='__main__':unittest.main()
