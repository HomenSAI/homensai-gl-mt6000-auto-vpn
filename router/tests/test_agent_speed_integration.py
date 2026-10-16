from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import speed_test
import telegram_report


class AgentIntegrationTests(unittest.TestCase):
    def test_main_monitor_feeds_wan_traffic_to_optional_speed_guard(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            path=Path(directory);data={'profiles':[{'id':'wireguard:peer_1','name':'Example','interface':'wgclient1','protocol':'wireguard'}],
                'servers':[],'wan_interfaces':['wan'],'settings':{'interval':30,'checkpoint':900,'probe_limit':16,'plan_enabled':False}}
            for name,value in [('RUNTIME',path),('PERSIST',path),('STOP',False)]:stack.enter_context(patch.object(agent,name,value))
            stack.enter_context(patch.object(agent,'inventory',return_value=data))
            stack.enter_context(patch.object(agent,'restore',return_value=(agent.Accounting(),None)))
            stack.enter_context(patch.object(agent,'probe',return_value={'id':'wireguard:peer_1','time':1792000000,'code':None,'device':'wgclient1','dns_ok':True,'https_success':3,'rtt_ms':30}))
            stack.enter_context(patch.object(agent,'sample_counters'))
            wan=stack.enter_context(patch.object(agent,'sample_wan_counters',return_value=[{'device':'eth1'}]))
            stack.enter_context(patch.object(agent,'checkpoint'))
            stack.enter_context(patch.object(telegram_report,'deliver',return_value=({'enabled':False},{},False)))
            observe=stack.enter_context(patch.object(speed_test,'observe_traffic'))
            stack.enter_context(patch.object(speed_test,'automatic_new',return_value={'wireguard:peer_1'}))
            stack.enter_context(patch.object(speed_test,'active_job',return_value=False))
            stack.enter_context(patch.object(speed_test,'cancel'))
            def stop(_):agent.STOP=True
            stack.enter_context(patch.object(agent.time,'sleep',side_effect=stop))
            agent.serve()
            wan.assert_called_once()
            observe.assert_called_once_with([{'device':'eth1'}],scope='wan')
            state=agent.read_json(path/'status.json')
            self.assertFalse(any(e.get('code')=='SPEED-MONITOR-UNAVAILABLE' for e in state['events']))


if __name__=='__main__':unittest.main()
