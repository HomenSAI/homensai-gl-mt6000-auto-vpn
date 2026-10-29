"""Owner probe level 1-5 and the automatic boost: cadence, episodes and the decision log."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import probe_policy as P
import setup_config


def write(path,value):path.write_text(json.dumps(value))
def read(path,default=None):
    try:return json.loads(path.read_text())
    except FileNotFoundError:return default


def row(id,code=None,dns=True,https=2):return {'id':id,'code':code,'dns_ok':dns,'https_success':https}
PAIR={'source':'wg','target':'ovpn'}


class Levels(unittest.TestCase):
    def test_explicit_level_wins_and_legacy_interval_maps_to_a_level(self):
        self.assertEqual(P.level({'probe_level':'2','interval':10}),2)
        for interval,expected in ((10,5),(15,4),(20,3),(30,2),(60,1),(300,1)):
            self.assertEqual(P.level({'interval':interval}),expected)
        self.assertEqual(P.level({'probe_level':'9','interval':10}),5)

    def test_measure_interval_and_validity(self):
        self.assertEqual(P.measure_interval({'probe_level':1}),300)
        self.assertEqual(P.measure_interval({'probe_level':1,'measure_interval':'120'}),120)
        self.assertEqual(P.measure_valid_for(30),60);self.assertEqual(P.measure_valid_for(300),465)

    def test_boost_defaults_on_and_can_be_off(self):
        self.assertTrue(P.boost_enabled({}));self.assertFalse(P.boost_enabled({'probe_boost':False}))


class Boost(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.runtime=Path(temporary.name)/'run';self.persist=Path(temporary.name)/'etc';self.runtime.mkdir();self.persist.mkdir()
        self.settings={'probe_level':1,'probe_boost':True,'interval':60,'measure_interval':300}
        self.booster=P.Booster(self.runtime,self.persist,write,read)

    def history(self):return read(self.persist/P.HISTORY_NAME,[])

    def test_first_pass_records_the_chosen_level_with_its_cadence(self):
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',1000)
        rows=self.history();self.assertEqual([r['kind'] for r in rows],['level'])
        self.assertEqual((rows[0]['level'],rows[0]['interval'],rows[0]['measure_interval'],rows[0]['boost_enabled']),(1,60,300,True))
        self.booster.observe(self.settings,[row('wg')],PAIR,'OBSERVING',1060);self.assertEqual(len(self.history()),1)

    def test_failure_boosts_to_ten_seconds_and_a_recovery_is_a_false_alarm(self):
        self.booster.observe(self.settings,[row('wg',code='VPN-003',https=0)],PAIR,'OBSERVING',1000)
        self.assertTrue(self.booster.active());self.assertEqual(self.booster.interval(self.settings),10);self.assertEqual(self.booster.measure(self.settings),30)
        start=self.history()[-1];self.assertEqual((start['kind'],start['role'],start['code']),('boost-start','source','VPN-003'))
        self.booster.observe(self.settings,[row('wg')],PAIR,'OBSERVING',1010)
        self.booster.observe(self.settings,[row('wg')],PAIR,'OBSERVING',1000+P.BOOST_HOLD)
        self.assertFalse(self.booster.active());self.assertEqual(self.booster.interval(self.settings),60)
        end=self.history()[-1];self.assertEqual((end['kind'],end['result'],end['failures'],end['code']),('boost-end','false-alarm',1,'VPN-003'))

    def test_repeated_failures_extend_the_episode_and_are_confirmed(self):
        for t in (1000,1010,1020):self.booster.observe(self.settings,[row('ovpn',dns=False)],PAIR,'OBSERVING',t)
        self.booster.observe(self.settings,[row('ovpn')],PAIR,'OBSERVING',1020+P.BOOST_HOLD-1);self.assertTrue(self.booster.active())
        self.booster.observe(self.settings,[row('ovpn')],PAIR,'OBSERVING',1020+P.BOOST_HOLD)
        end=self.history()[-1];self.assertEqual((end['result'],end['failures'],end['role'],end['code']),('failure-confirmed',3,'target','DNS-001'))

    def test_a_switch_during_the_episode_is_recorded(self):
        self.booster.observe(self.settings,[row('wg',code='VPN-001')],PAIR,'OBSERVING',1000)
        self.booster.observe(self.settings,[row('wg',code='VPN-001')],PAIR,'APPLYING',1010)
        self.booster.observe(self.settings,[row('wg')],PAIR,'OBSERVING',1010+P.BOOST_HOLD)
        self.assertEqual(self.history()[-1]['result'],'switched')

    def test_boost_off_never_boosts_and_turning_it_off_ends_an_episode(self):
        self.booster.observe(self.settings,[row('wg',code='VPN-003')],PAIR,'OBSERVING',1000);self.assertTrue(self.booster.active())
        off=dict(self.settings,probe_boost=False)
        self.booster.observe(off,[row('wg',code='VPN-003')],PAIR,'OBSERVING',1010)
        self.assertFalse(self.booster.active());self.assertEqual(self.history()[-1]['result'],'disabled')
        self.booster.observe(off,[row('wg',code='VPN-003')],PAIR,'OBSERVING',1020);self.assertFalse(self.booster.active())

    def test_channels_outside_the_pair_never_boost(self):
        self.booster.observe(self.settings,[row('other',code='VPN-003')],PAIR,'OBSERVING',1000);self.assertFalse(self.booster.active())

    def test_state_survives_a_monitor_restart_and_history_is_bounded(self):
        self.booster.observe(self.settings,[row('wg',code='VPN-003')],PAIR,'OBSERVING',1000)
        again=P.Booster(self.runtime,self.persist,write,read);self.assertTrue(again.active())
        write(self.persist/P.HISTORY_NAME,[{'sequence':i,'time':i,'kind':'level'} for i in range(1,P.HISTORY_LIMIT+1)])
        again.record({'kind':'level'},5000);rows=self.history()
        self.assertEqual(len(rows),P.HISTORY_LIMIT);self.assertEqual(rows[-1]['sequence'],P.HISTORY_LIMIT+1)

    def test_history_page_uses_the_statistics_cursor_contract(self):
        for t in (1000,1010):self.booster.observe(self.settings,[row('wg',code='VPN-003')],PAIR,'OBSERVING',t)
        page=P.history_page(self.persist,{'kind':'probe','after':0,'until':0},read,2000)
        self.assertEqual([r['kind'] for r in page['events']],['level','boost-start']);self.assertEqual(page['next_after'],2)
        with self.assertRaises(ValueError):P.history_page(self.persist,{'kind':'probe','after':5,'until':2},read,2000)


class Save(unittest.TestCase):
    def test_payload_sets_level_boost_and_both_intervals(self):
        self.assertEqual(setup_config.probe_payload({'level':3,'boost':True})['main'],
                         {'probe_level':'3','probe_boost':'1','interval':'20','measure_interval':'60'})
        self.assertEqual(setup_config.probe_payload({'level':1,'boost':False})['main']['probe_boost'],'0')

    def test_invalid_requests_are_refused_with_codes(self):
        for bad,code in (({'level':3},'PROBE-SETTINGS-FIELDS'),({'level':3,'boost':'1'},'PROBE-SETTINGS-FIELDS'),
                         ({'level':0,'boost':True},'PROBE-SETTINGS-RANGE'),({'level':'3','boost':True},'PROBE-SETTINGS-RANGE'),
                         ({'level':3,'boost':True,'x':1},'PROBE-SETTINGS-FIELDS')):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,code):setup_config.probe_payload(bad)


if __name__=='__main__':unittest.main()


class ResponseMetric(unittest.TestCase):
    def test_ping_is_the_default_and_only_offered_metrics_are_accepted(self):
        self.assertEqual(P.response_metric({}),'icmp-1.1.1.1')
        for metric in ('icmp-8.8.8.8','icmp-9.9.9.9','websites'):self.assertEqual(P.response_metric({'response_metric':metric}),metric)
        self.assertEqual(P.response_metric({'response_metric':'icmp-10.0.0.1'}),'icmp-1.1.1.1')
        self.assertEqual(setup_config.response_payload({'metric':'websites'})['main'],{'response_metric':'websites'})
        for bad in ({},{'metric':'icmp-10.0.0.1'},{'metric':'websites','x':1}):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'RESPONSE-METRIC-INVALID'):setup_config.response_payload(bad)
