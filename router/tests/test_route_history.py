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
        row={'id':'a','time':100,'code':None,'dns_ok':True,'https_success':2}
        native={'time':100,'state':'OBSERVING','source':'a','mode':'continuous-pair','readiness_verified':True}
        status={'native_failover':native,'profiles':[row]}
        self.assertEqual(observed_route(status,110),'source')
        row['code']='VPN-003';self.assertEqual(observed_route(status,110),'source')
        native['target']='b';status['profiles'].append({'id':'b','time':100,'code':'VPN-003'})
        self.assertEqual(observed_route(status,110),'down')
        status['profiles'].pop();row['code']=None
        self.assertEqual(observed_route(status,200),'unknown')
        native['state']='RESTORING';self.assertEqual(observed_route(status,110),'switching')
        native['state']='BLOCKED';self.assertEqual(observed_route(status,110),'blocked')

    def test_corrupt_route_state_is_not_trusted(self):
        r=RouteHistory();r.observe('source',100);data=r.export();data['last']['kind']='bad'
        with self.assertRaises(ValueError):RouteHistory(data)


if __name__=='__main__':unittest.main()
