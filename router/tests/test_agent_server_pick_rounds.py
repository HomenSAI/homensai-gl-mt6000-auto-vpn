"""Server pick rounds of the Python monitor (agent.monitor_loop): a channel that recovered and fails again within the
10-minute round interval starts a new round (MT3000 02.11.2026: the second failure of the reserve within 10 min started
no round - the failed set was remembered from the last round start). Lua twin: tests/lua/test_monitor_pass.lua."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import icmp_ping  # noqa: E402


class ServerPickRounds(unittest.TestCase):
    def run_passes(self,failing,clocks=None,code=None):
        """One monitor pass per entry of `failing` (True: the channel's check fails). -> the `failed` list of each round.
        clocks: the monotonic clock of each pass (else the real one); code: each round writes server-pick.json with this
        code for every failed channel (else no result file)."""
        profile=dict(id='wireguard:peer_1',section='peer_1',name='Example',protocol='wireguard',interface='wgclient1',
                     administrative_state='enabled',vendor_tunnel_id='wireguard:wgclient1')
        data={'profiles':[profile],'servers':[],'wan_interfaces':[],
              'settings':{'interval':30,'checkpoint':900,'probe_limit':2,'plan_enabled':False}}
        passes=[0];rounds=[]
        def probe(*args,**kwargs):
            bad=failing[min(passes[0],len(failing)-1)]
            return dict(id=profile['id'],time=time.time(),device='wgclient1',mark=4096,table='1001',ifindex=7,administrative_state='enabled',
                        code='VPN-001' if bad else None,dns_ok=not bad,https_success=0 if bad else 3,rtt_ms=None if bad else 25)
        def job(io,request,now):
            rounds.append(list(request['failed']))
            if code:real_write(agent.RUNTIME/'server-pick.json',{'time':now,'enabled':True,'tunnels':[
                {'protocol':'wireguard','interface':iface,'code':code,'candidates':[]} for iface in request['failed']]})
        class Clock:  # agent's own `time`: the pass sets the monotonic clock, the rest is the real module
            def __getattr__(self,name):return getattr(time,name)
            def monotonic(self):return clocks[min(passes[0],len(clocks)-1)] if clocks else time.monotonic()
        real_write=agent.atomic_json
        def write(path,value):
            real_write(path,value)
            if Path(path).name=='status.json':
                passes[0]+=1
                for thread in threading.enumerate():
                    if thread.name=='server-pick':thread.join(5)
                if passes[0]>=len(failing):agent.STOP=True
        with tempfile.TemporaryDirectory()as directory,ExitStack()as stack:
            root=Path(directory)
            for name,value in [('RUNTIME',root),('PERSIST',root),('STOP',False)]:stack.enter_context(patch.object(agent,name,value))
            stack.enter_context(patch('auto_control.RUNTIME',root));stack.enter_context(patch('auto_control.PERSIST',root))
            stack.enter_context(patch.object(agent,'time',Clock()))
            stack.enter_context(patch.object(agent,'inventory',return_value=data))
            stack.enter_context(patch('website_response.WebsiteSampler'))
            stack.enter_context(patch.object(icmp_ping,'PingSampler'))
            stack.enter_context(patch.object(agent,'probe',side_effect=probe))
            stack.enter_context(patch.object(agent,'restore',return_value=(agent.Accounting(),None)))
            stack.enter_context(patch.object(agent,'sample_counters'));stack.enter_context(patch.object(agent,'sample_wan_counters',return_value=[]))
            stack.enter_context(patch.object(agent,'checkpoint'))
            stack.enter_context(patch.object(agent,'monitor_poll_interval',return_value=0))  # the passes follow each other at once
            stack.enter_context(patch('telegram_report.deliver',return_value=({'enabled':False},{},False)))
            stack.enter_context(patch('system_readiness.snapshot',return_value={}))
            stack.enter_context(patch('server_pick.job',side_effect=job))
            stack.enter_context(patch('speed_test.observe_traffic'));stack.enter_context(patch('speed_test.automatic_new',return_value=set()))
            stack.enter_context(patch('speed_test.active_job',return_value=False));stack.enter_context(patch('speed_test.cancel'))
            stack.enter_context(patch.object(agent,'atomic_json',side_effect=write))
            try:agent.monitor_loop()
            finally:agent.STOP=False
        return rounds,passes[0]

    def test_a_channel_that_recovered_and_fails_again_starts_a_new_round(self):
        rounds,passes=self.run_passes([False,True,True,False,True])
        self.assertEqual(passes,5)
        self.assertEqual(rounds,[[],['wgclient1'],['wgclient1']],
                         'the first pass, the first failure, and the second failure after the recovery (all within 10 min)')

    def test_a_channel_that_stays_failed_starts_no_new_round(self):
        rounds,_=self.run_passes([False,True,True,True])
        self.assertEqual(rounds,[[],['wgclient1']])

    # MT3000 02.11.2026: the round a failure starts runs before Auto moved the traffic (SERVER-PICK-CARRYING), so the
    # failed channel gets another round once RETRY_CARRYING (20 s) passed; the passes run at 1000, 1010, 1029, 1030 s
    def test_a_failed_channel_that_still_carried_gets_another_round_after_20_s(self):
        rounds,passes=self.run_passes([False,True,True,True],clocks=[1000,1010,1029,1030],code='SERVER-PICK-CARRYING')
        self.assertEqual(passes,4)
        self.assertEqual(rounds,[[],['wgclient1'],['wgclient1']],'no round 19 s after the failure round, another one at 20 s')

    def test_a_carrying_round_is_not_retried_before_20_s(self):
        rounds,_=self.run_passes([False,True,True,True],clocks=[1000,1010,1020,1029],code='SERVER-PICK-CARRYING')
        self.assertEqual(rounds,[[],['wgclient1']])

    def test_a_round_with_another_code_is_not_retried(self):
        rounds,_=self.run_passes([False,True,True,True],clocks=[1000,1010,1029,1060],code='SERVER-PICK-LIMIT')
        self.assertEqual(rounds,[[],['wgclient1']])

    # review 02.11.2026: a channel that keeps carrying (reserve down, hold) got a round every 20 s; one retry per failure
    def test_the_carrying_retry_happens_once_per_failure(self):
        rounds,passes=self.run_passes([False,True,True,True,True,True],clocks=[1000,1010,1030,1050,1070,1090],code='SERVER-PICK-CARRYING')
        self.assertEqual(passes,6)
        self.assertEqual(rounds,[[],['wgclient1'],['wgclient1']],'the retry round said CARRYING again: no further round before 10 min')

    def test_a_channel_that_recovered_and_fails_again_gets_a_fresh_retry(self):
        rounds,_=self.run_passes([False,True,True,False,True,True],clocks=[1000,1010,1030,1040,1050,1070],code='SERVER-PICK-CARRYING')
        self.assertEqual(rounds,[[],['wgclient1'],['wgclient1'],['wgclient1'],['wgclient1']],
                         'failure, its retry, the new failure after the recovery, and its own retry')


if __name__=='__main__':unittest.main()
