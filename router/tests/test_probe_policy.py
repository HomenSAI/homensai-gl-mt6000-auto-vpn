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
        off=dict(self.settings,probe_boost=False,probe_level=3)  # levels 1-2 force the boost; 3-5 let the owner turn it off
        self.booster.observe(off,[row('wg',code='VPN-003')],PAIR,'OBSERVING',1010)
        self.assertFalse(self.booster.active());self.assertEqual(self.history()[-1]['result'],'disabled')
        self.booster.observe(off,[row('wg',code='VPN-003')],PAIR,'OBSERVING',1020);self.assertFalse(self.booster.active())

    def test_a_failure_while_auto_is_not_watching_never_boosts(self):
        for state in ('STOPPED','ARMED','APPLYING','BLOCKED',None):
            self.booster.observe(self.settings,[row('wg',code='VPN-001')],PAIR,state,1000);self.assertFalse(self.booster.active(),state)

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
        self.assertEqual(setup_config.probe_payload({'level':3,'boost':False})['main']['probe_boost'],'0')
        for low in (1,2):self.assertEqual(setup_config.probe_payload({'level':low,'boost':False})['main']['probe_boost'],'1','levels 1-2 always boost')
        from probe_policy import boost_enabled
        self.assertTrue(boost_enabled({'probe_level':'1','probe_boost':'0'}));self.assertFalse(boost_enabled({'probe_level':'4','probe_boost':'0'}))

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
        for bad in ({},{'metric':'icmp-10.0.0.1'},{'metric':'websites','x':1},{'metric':'websites','fast_switch':'0'},{'metric':'websites','fast_switch':0},{'fast_switch':True}):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'RESPONSE-METRIC-INVALID'):setup_config.response_payload(bad)

    def test_fast_switch_owner_option_is_saved_as_one_or_zero(self):
        self.assertEqual(setup_config.response_payload({'metric':'websites','compare':False,'fast_switch':False})['main'],
                         {'response_metric':'websites','response_compare':'0','fast_switch':'0'})
        self.assertEqual(setup_config.response_payload({'metric':'icmp-1.1.1.1','fast_switch':True})['main'],
                         {'response_metric':'icmp-1.1.1.1','fast_switch':'1'})
        self.assertNotIn('fast_switch',setup_config.response_payload({'metric':'websites','compare':True})['main'])


class PingInterval(unittest.TestCase):
    """Owner ping cadence (option ping_interval), separate from the probe level: 10 s .. 5 min, step 10 s, default 60."""
    def test_default_range_and_step(self):
        self.assertEqual(P.ping_interval({}),60)
        for raw,expected in ((10,10),('10',10),(300,300),('300',300),(120,120),('60',60),
                             (5,60),(0,60),(310,60),(15,60),('15',60),('1e2',60),(60.0,60),(True,60),(None,60),('',60),('abc',60),(-10,60)):
            with self.subTest(raw=raw):self.assertEqual(P.ping_interval({'ping_interval':raw}),expected)
        self.assertEqual(P.ping_interval(None),60)
        self.assertEqual(P.ping_interval({'probe_level':5,'measure_interval':30}),60,'the probe level no longer sets the ping cadence')

    def test_freshness_window_scales_with_the_effective_spacing(self):
        # 1.5 x max(ping interval, normal check interval) + 15 s probe budget, never below the former 45 s.
        for settings,expected in (({'ping_interval':10,'interval':10},45),({'ping_interval':20,'interval':10},45),
                                  ({'ping_interval':30,'interval':10},60),({},105),({'ping_interval':60,'interval':60},105),
                                  ({'ping_interval':10,'interval':60},105),({'ping_interval':300,'interval':10},465),
                                  ({'ping_interval':120,'interval':30},195)):
            with self.subTest(settings=settings):self.assertEqual(P.ping_valid_for(settings),expected)
        self.assertLessEqual(max(P.ping_valid_for({'ping_interval':n,'interval':i}) for n in range(10,301,10) for i in (10,60,300)),465,
                             'within the 465 s bound of the histories and the page')

    def test_public_policy_reports_the_ping_cadence(self):
        with tempfile.TemporaryDirectory() as folder:
            booster=P.Booster(Path(folder),Path(folder),write,read)
            public=booster.public({'probe_level':1,'interval':60,'ping_interval':'20'},1000)
        self.assertEqual((public['ping_interval'],public['effective_ping_interval'],public['ping_valid_for']),(20,60,105))
        self.assertEqual(public['measure_interval'],300,'the website cadence still follows the level')

    def test_save_payload_validates_the_interval(self):
        self.assertEqual(setup_config.response_payload({'metric':'icmp-1.1.1.1','ping_interval':10})['main'],
                         {'response_metric':'icmp-1.1.1.1','ping_interval':'10'})
        self.assertEqual(setup_config.response_payload({'metric':'websites','compare':False,'fast_switch':True,'ping_interval':300})['main'],
                         {'response_metric':'websites','response_compare':'0','fast_switch':'1','ping_interval':'300'})
        self.assertNotIn('ping_interval',setup_config.response_payload({'metric':'websites'})['main'])
        for bad in (0,5,15,301,310,-10,60.0,'60',True,None,[60]):
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'^PING-INTERVAL-INVALID$'):
                setup_config.response_payload({'metric':'icmp-1.1.1.1','ping_interval':bad})
        with self.assertRaisesRegex(ValueError,'RESPONSE-METRIC-INVALID'):setup_config.response_payload({'metric':'x','ping_interval':5})


class BoostBounds(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.runtime=Path(temporary.name)/'run';self.persist=Path(temporary.name)/'etc';self.runtime.mkdir();self.persist.mkdir()
        self.settings={'probe_level':1,'probe_boost':True,'interval':60,'measure_interval':300}
        self.booster=P.Booster(self.runtime,self.persist,write,read)

    def test_a_primary_that_stays_down_cannot_extend_the_episode_forever(self):
        t=1000
        while t<1000+6*P.BOOST_HOLD:
            self.booster.observe(self.settings,[row('wg',code='VPN-001')],PAIR,'OBSERVING',t);t+=10
        self.assertFalse(self.booster.active(),'bounded to two holds, then one hold of rest, even though the primary never recovers')
        rows=read(self.persist/P.HISTORY_NAME)
        self.assertEqual(sum(r['kind']=='boost-start' for r in rows),1,'a channel that never recovers opens one episode only')
        self.assertEqual([r['result'] for r in rows if r['kind']=='boost-end'][-1],'failure-confirmed')

    def test_target_change_clears_the_ping_cache(self):
        import icmp_ping
        sampler=icmp_ping.PingSampler(lambda:{},lambda i:{},paused=lambda:False)
        sampler.cache={'k':{'target':'1.1.1.1'}};sampler.configure(30,'1.1.1.1');self.assertEqual(sampler.cache,{'k':{'target':'1.1.1.1'}})
        sampler.configure(30,'9.9.9.9');self.assertEqual(sampler.cache,{});self.assertEqual(sampler.target,'9.9.9.9')
