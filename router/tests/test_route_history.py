import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from route_history import RouteHistory,observed_route,DAY
from reliability import Reliability


class Tests(unittest.TestCase):
    def test_intervals_survive_reload_and_coalesce_without_invented_past(self):
        r=RouteHistory();r.observe('source',100);self.assertEqual(r.data['segments'],[])
        r.observe('source',110);r=RouteHistory(r.export());r.observe('target',120);r.observe('target',130)
        self.assertEqual(r.data['segments'],[{'start':100,'end':120,'kind':'source'},{'start':120,'end':130,'kind':'target'}])

    def test_gap_and_clock_reversal_never_fabricate_a_healthy_route(self):
        r=RouteHistory();r.observe('source',100);r.observe('source',110);r.observe('source',300)
        self.assertEqual(r.data['segments'][-1],{'start':110,'end':300,'kind':'unknown'})
        before=r.export();r.observe('target',200);self.assertEqual(r.export(),before)

    def test_rolls_over_after_24h_and_is_part_of_durable_accounting(self):
        r=Reliability();r.routes.observe('source',100);r.routes.observe('target',110)
        r=Reliability(r.export());r.routes.observe('target',DAY+120)
        self.assertEqual(r.routes.data['segments'][0]['start'],120)
        self.assertEqual(r.public()['route_history'],r.routes.export())

    def test_route_requires_current_selected_profile_and_health(self):
        from channel_path import from_kernel
        row={'id':'wireguard:peer_1','time':100,'code':None,'dns_ok':True,'https_success':2}
        native={'time':100,'state':'OBSERVING','source':row['id'],'target':'openvpn:1_1','mode':'continuous-pair','readiness_verified':True}
        native['channel_path']=from_kernel({'verified':True,'role':'source','profile_id':row['id'],'time':100},row['id'],native['target'],100)
        status={'native_failover':native,'profiles':[row]}
        self.assertEqual(observed_route(status,110),'source')
        row['code']='VPN-003';self.assertEqual(observed_route(status,110),'source')
        status['profiles'].append({'id':native['target'],'time':100,'code':'VPN-003'})
        self.assertEqual(observed_route(status,110),'down')
        status['profiles'].pop();row['code']=None
        self.assertEqual(observed_route(status,200),'unknown')
        native['state']='RESTORING';self.assertEqual(observed_route(status,110),'switching')
        native['state']='BLOCKED';self.assertEqual(observed_route(status,110),'blocked')

    def test_new_interval_and_failure_facts_use_event_time_kernel_role_not_phase(self):
        from channel_path import from_kernel
        source='wireguard:peer_1';target='openvpn:1_1'
        native={'time':100,'state':'OBSERVING','source':source,'target':target,'mode':'continuous-pair','readiness_verified':True}
        native['channel_path']=from_kernel({'verified':True,'role':'target','profile_id':target,'time':100},source,target,100)
        status={'native_failover':native,'profiles':[{'id':key,'time':100,'code':None,'dns_ok':True,'https_success':2} for key in (source,target)]}
        self.assertEqual(observed_route(status,100),'target')
        history=RouteHistory();history.observe(observed_route(status,100),100)
        incidents=Reliability();incidents.event(source,'FAILURE',100,code='VPN-003');incidents.event_context(source,100,native,None)
        self.assertEqual(incidents.data['events'][-1]['selected'],'target')
        native.update(state='COMMITTED',time=106)
        native['channel_path']=from_kernel({'verified':True,'role':'source','profile_id':source,'time':106},source,target,106)
        self.assertEqual(observed_route(status,106),'source');history.observe(observed_route(status,106),106)
        self.assertEqual(RouteHistory(history.export()).data['segments'][0]['kind'],'target')
        self.assertEqual(Reliability(incidents.export()).data['events'][0]['selected'],'target')
        native.pop('channel_path');self.assertEqual(observed_route(status,106),'unknown')
        incidents.event(target,'FAILURE',106,code='VPN-003');incidents.event_context(target,106,native,None)
        self.assertEqual(incidents.data['events'][-1]['selected'],'unknown')

    def test_corrupt_route_state_is_not_trusted(self):
        r=RouteHistory();r.observe('source',100);data=r.export();data['last']['kind']='bad'
        with self.assertRaises(ValueError):RouteHistory(data)


if __name__=='__main__':unittest.main()
