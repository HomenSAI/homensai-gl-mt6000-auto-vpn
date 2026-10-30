"""Passive suspicion: synthetic counters/handshakes, dense confirmation scheduling, and no switch without proof."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import failover_plan
import probe_policy as P
import suspicion as S


def write(path,value):path.write_text(json.dumps(value))
def read(path,default=None):
    try:return json.loads(path.read_text())
    except FileNotFoundError:return default


def row(id,code=None,dns=True,https=2):return {'id':id,'code':code,'dns_ok':dns,'https_success':https}
PAIR={'source':'wg','target':'ovpn'}
WG={'id':'wg','role':'source','device':'wgclient1','protocol':'wireguard'}
OVPN={'id':'ovpn','role':'target','device':'ovpnclient1','protocol':'openvpn'}


class Counters:
    """Synthetic /sys/class/net counters; a missing device raises like sysfs does."""
    def __init__(self):self.devices={}
    def set(self,device,ifindex=7,**values):
        current=self.devices.setdefault(device,{'ifindex':ifindex,**{k:0 for k in S.COUNTERS}})
        current['ifindex']=ifindex;current.update(values)
    def add(self,device,**delta):
        for key,value in delta.items():self.devices[device][key]+=value
    def remove(self,device):self.devices.pop(device,None)
    def __call__(self,device):
        if device not in self.devices:raise FileNotFoundError(device)
        return dict(self.devices[device])


class Handshakes:
    def __init__(self,value):self.value=value;self.calls=[]
    def __call__(self,device):self.calls.append(device);return self.value


class Watcher(unittest.TestCase):
    def setUp(self):
        self.counters=Counters();self.handshakes=Handshakes(0)
        self.watcher=S.SuspicionWatcher(self.counters,self.handshakes)
        self.wall=100000

    def poll(self,now):return self.watcher.poll(now,self.wall+now)

    def test_channels_are_the_two_auto_roles_with_a_safe_device(self):
        rows=[dict(row('wg'),role='source',device='wgclient1',protocol='wireguard'),
              dict(row('ovpn'),role='target',device='ovpnclient1',protocol='openvpn'),
              dict(row('x'),role='unknown',device='wgclient2',protocol='wireguard'),
              dict(row('y'),role='source',device='bad device;rm',protocol='openvpn'),
              dict(row('z'),role='target',code='VPN-001')]
        self.assertEqual(S.channels(rows),[WG,OVPN])
        self.assertEqual(S.channels(None),[])

    def test_sending_into_silence_for_six_seconds_is_suspect_and_not_earlier(self):
        self.counters.set('ovpnclient1',rx_packets=50,rx_bytes=5000,tx_packets=40,tx_bytes=4000)
        self.watcher.configure([OVPN])
        self.assertEqual(self.poll(0),[])  # first look: baseline only
        for now in (2,4):
            self.counters.add('ovpnclient1',tx_packets=2,tx_bytes=150)
            self.assertEqual(self.poll(now),[],now)
        self.counters.add('ovpnclient1',tx_packets=2,tx_bytes=150)
        found=self.poll(6)
        self.assertEqual(len(found),1);item=found[0]
        self.assertEqual((item['profile'],item['role'],item['reason']),('ovpn','target','rx-stall'))
        self.assertEqual(item['evidence'],{'stalled_s':6,'tx_packets':6})
        self.assertEqual(self.handshakes.calls,[],'OpenVPN never runs wg show')

    def test_two_way_traffic_and_idle_channels_are_never_suspect(self):
        self.counters.set('ovpnclient1');self.counters.set('wgclient1')
        self.watcher.configure([WG,OVPN]);self.poll(0)
        for now in range(2,120,2):
            self.counters.add('ovpnclient1',tx_packets=10,tx_bytes=900,rx_packets=12,rx_bytes=9000)  # healthy traffic
            self.assertEqual(self.poll(now),[],now)  # wgclient1 idle: no tx, no suspicion, no wg show
        self.assertEqual(self.handshakes.calls,[])

    def test_a_few_empty_keepalives_are_not_traffic(self):
        self.counters.set('wgclient1');self.watcher.configure([WG]);self.handshakes.value=self.wall  # fresh handshake
        self.poll(0)
        for now in (25,50,75):
            self.counters.add('wgclient1',tx_packets=1,tx_bytes=32)
            self.assertEqual(self.poll(now),[])

    def test_counter_reset_or_new_interface_restarts_the_evidence(self):
        self.counters.set('ovpnclient1',tx_packets=100,tx_bytes=10000)
        self.watcher.configure([OVPN]);self.poll(0)
        self.counters.add('ovpnclient1',tx_packets=5,tx_bytes=600);self.poll(4)
        self.counters.set('ovpnclient1',ifindex=9,tx_packets=1,tx_bytes=100)  # reconnect: new ifindex, counters from zero
        self.assertEqual(self.poll(6),[])
        self.counters.add('ovpnclient1',tx_packets=5,tx_bytes=600)
        self.assertEqual(self.poll(10),[],'only 4 s of evidence on the new interface')
        self.counters.add('ovpnclient1',tx_packets=1,tx_bytes=100)
        self.assertEqual([i['reason'] for i in self.poll(12)],['rx-stall'])

    def test_a_vanished_tunnel_interface_is_suspect_once(self):
        self.counters.set('wgclient1');self.watcher.configure([WG]);self.poll(0)
        self.counters.remove('wgclient1')
        self.assertEqual([i['reason'] for i in self.poll(2)],['link-missing'])
        self.assertEqual(self.poll(4),[])
        self.watcher.configure([dict(WG,device='never-seen')])
        self.assertEqual(self.poll(6),[],'a device never observed is not evidence')

    def test_stale_wireguard_handshake_while_sending_is_suspect_and_wg_show_is_rate_limited(self):
        self.counters.set('wgclient1',rx_packets=10,rx_bytes=1000);self.watcher.configure([WG]);self.poll(0)
        self.handshakes.value=self.wall-400  # older than REJECT_AFTER_TIME
        # Dead keypair: packets are queued/dropped, not sent; rx is flat but tx_packets does not grow either.
        self.counters.add('wgclient1',tx_dropped=1);self.assertEqual(self.poll(2),[])
        self.assertEqual(self.handshakes.calls,[],'activity must be older than the handshake settle time')
        self.counters.add('wgclient1',tx_dropped=1)
        found=self.poll(8)
        self.assertEqual([(i['reason'],i['evidence']['handshake_age_s']) for i in found],[('wg-handshake-stale',408)])
        self.assertEqual(len(self.handshakes.calls),1)
        for now in (10,12,14,16):self.poll(now)
        self.assertEqual(len(self.handshakes.calls),1,'one wg show per channel per 9 s')
        self.poll(17);self.assertEqual(len(self.handshakes.calls),2)
        self.handshakes.value=0  # never handshaken while sending is just as suspect
        self.assertEqual([i['reason'] for i in self.poll(26)],['wg-handshake-stale'])

    def test_fresh_handshake_is_not_suspect(self):
        self.counters.set('wgclient1');self.watcher.configure([WG]);self.poll(0)
        self.handshakes.value=self.wall
        self.counters.add('wgclient1',tx_dropped=1);self.poll(1)
        self.assertEqual(self.poll(8),[]);self.assertEqual(len(self.handshakes.calls),1)

    def test_global_wg_show_spacing_across_channels(self):
        second=dict(WG,id='ovpn',role='target',device='wgclient2')
        for device in ('wgclient1','wgclient2'):self.counters.set(device)
        self.watcher.configure([WG,second]);self.handshakes.value=self.wall;self.poll(0)
        for device in ('wgclient1','wgclient2'):self.counters.add(device,tx_dropped=1)
        self.poll(1);self.poll(8)
        self.assertEqual(self.handshakes.calls,['wgclient1'],'at most one wg show per 3 s')
        self.poll(11);self.assertEqual(self.handshakes.calls,['wgclient1','wgclient2'])

    def test_primary_is_reported_first_and_poll_spacing(self):
        for device in ('wgclient1','ovpnclient1'):self.counters.set(device)
        self.watcher.configure([OVPN,WG]);self.poll(0)
        for device in ('wgclient1','ovpnclient1'):self.counters.add(device,tx_packets=9,tx_bytes=900)
        self.assertEqual([i['role'] for i in self.poll(7)],['source','target'])
        self.assertFalse(self.watcher.due(8));self.assertTrue(self.watcher.due(9))


class Dense(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.runtime=Path(temporary.name)/'run';self.persist=Path(temporary.name)/'etc';self.runtime.mkdir();self.persist.mkdir()
        self.settings={'probe_level':1,'probe_boost':True,'interval':60,'measure_interval':300}
        self.booster=P.Booster(self.runtime,self.persist,write,read)
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',900)

    def history(self,kind=None):
        rows=read(self.persist/P.HISTORY_NAME,[])
        return [r for r in rows if kind is None or r['kind']==kind]

    def stall(self,profile='wg',role='source'):
        return [{'profile':profile,'role':role,'reason':'rx-stall','evidence':{'stalled_s':7,'tx_packets':12}}]

    def test_suspicion_densifies_checks_at_every_level_without_being_a_failure(self):
        for number,(normal,_) in P.LEVELS.items():
            with self.subTest(level=number):
                booster=P.Booster(self.runtime,self.persist,write,read);booster.state={'active':False}
                settings={'probe_level':number,'interval':normal}
                self.assertEqual(booster.interval(settings,1000),normal)
                self.assertTrue(booster.suspect(settings,self.stall(),PAIR,'OBSERVING',1000))
                self.assertEqual(booster.interval(settings,1000),P.DENSE_INTERVAL)
                self.assertFalse(booster.active(),'a suspicion never starts the failure boost')
        start=self.history('suspicion-start')[-1]
        self.assertEqual((start['role'],start['reason'],start['result'],start['code'],start['dense_interval']),('source','rx-stall','started',None,4))
        self.assertEqual(start['evidence'],{'stalled_s':7,'tx_packets':12})

    def test_confirmation_runs_densely_for_both_channels_until_three_failures_and_a_proven_reserve(self):
        self.assertTrue(self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1000))
        t=1000
        for index in range(2):
            t+=4;self.booster.observe(self.settings,[row('wg',code='VPN-003',https=0),row('ovpn')],PAIR,'OBSERVING',t)
            self.assertEqual(self.booster.interval(self.settings,t),P.DENSE_INTERVAL,'still dense after %d failures'%(index+1))
        t+=4;self.booster.observe(self.settings,[row('wg',code='VPN-003',https=0),row('ovpn')],PAIR,'OBSERVING',t)
        end=self.history('suspicion-end')[-1]
        self.assertEqual((end['result'],end['failures'],end['checks'],end['reserve_good'],end['code'],end['duration']),
                         ('failure-confirmed',3,3,3,'VPN-003',12))
        self.assertIsNone(self.booster.dense(t))
        self.assertTrue(self.booster.active());self.assertEqual(self.booster.interval(self.settings,t),P.BOOST_INTERVAL,'the boost keeps watching')

    def test_unproven_reserve_keeps_the_dense_cadence(self):
        self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1000)
        for t in (1004,1008,1012):self.booster.observe(self.settings,[row('wg',code='VPN-003'),row('ovpn',code='VPN-003')],PAIR,'OBSERVING',t)
        self.assertIsNotNone(self.booster.dense(1012))
        for t in (1016,1020):self.booster.observe(self.settings,[row('wg',code='VPN-003'),row('ovpn')],PAIR,'OBSERVING',t)
        self.assertEqual(self.history('suspicion-end')[-1]['result'],'failure-confirmed')

    def test_false_alarm_ends_after_two_good_checks_and_backs_off(self):
        self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1000)
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',1004)
        self.assertIsNotNone(self.booster.dense(1004))
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',1008)
        end=self.history('suspicion-end')[-1];self.assertEqual((end['result'],end['rest'],end['code']),('false-alarm',30,None))
        self.assertEqual(self.booster.interval(self.settings,1008),60)
        self.assertFalse(self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1020),'resting')
        self.assertTrue(self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1038))
        for t in (1042,1046):self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',t)
        self.assertEqual(self.history('suspicion-end')[-1]['rest'],60,'repeated false alarms back off')
        self.assertTrue(self.booster.suspect(self.settings,self.stall('ovpn','target'),PAIR,'OBSERVING',1050),'the other channel is not resting')

    def test_refusals(self):
        for state in ('STOPPED','ARMED','APPLYING',None):
            self.assertFalse(self.booster.suspect(self.settings,self.stall(),PAIR,state,1000),state)
        self.assertFalse(self.booster.suspect(self.settings,self.stall('other','source'),PAIR,'OBSERVING',1000))
        self.assertFalse(self.booster.suspect(self.settings,[{'profile':'wg','reason':'made-up'}],PAIR,'OBSERVING',1000))
        self.assertFalse(self.booster.suspect(self.settings,self.stall(),None,'OBSERVING',1000))
        self.assertEqual(self.history('suspicion-start'),[])
        self.assertTrue(self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1000))
        self.assertFalse(self.booster.suspect(self.settings,self.stall('ovpn','target'),PAIR,'OBSERVING',1001),'one episode at a time')

    def test_a_channel_already_proven_failed_is_left_to_the_boost(self):
        for t in (1000,1010,1020):self.booster.observe(self.settings,[row('wg',code='VPN-001'),row('ovpn')],PAIR,'OBSERVING',t)
        self.assertFalse(self.booster.suspect(self.settings,self.stall(),PAIR,'COMMITTED',1025))
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'COMMITTED',1030)
        self.assertTrue(self.booster.suspect(self.settings,self.stall(),PAIR,'COMMITTED',1031))

    def test_switch_cancel_and_expiry_end_the_episode(self):
        self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1000)
        self.booster.observe(self.settings,[row('wg',code='VPN-003'),row('ovpn')],PAIR,'APPLYING',1004)
        self.assertEqual(self.history('suspicion-end')[-1]['result'],'switched')
        self.booster.suspect(self.settings,self.stall('ovpn','target'),PAIR,'COMMITTED',1100)
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'STOPPED',1104)
        self.assertEqual(self.history('suspicion-end')[-1]['result'],'cancelled')
        self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1200)
        t=1200
        while self.booster.dense(t):
            t+=4;self.booster.observe(self.settings,[row('wg',code='VPN-003' if t%8 else None),row('ovpn')],PAIR,'OBSERVING',t)
            self.assertLessEqual(t,1200+P.DENSE_MAX+P.DENSE_INTERVAL)
        self.assertEqual(self.history('suspicion-end')[-1]['result'],'expired')

    def test_a_stuck_episode_cannot_keep_the_router_busy(self):
        self.booster.suspect(self.settings,self.stall(),PAIR,'OBSERVING',1000)
        # No observe() at all (every monitor pass failed): the cadence still falls back by itself.
        self.assertEqual(self.booster.interval(self.settings,1000+P.DENSE_MAX+P.DENSE_INTERVAL+1),60)
        self.booster.observe(self.settings,[],PAIR,'OBSERVING',1000+P.DENSE_MAX+P.DENSE_INTERVAL+1)
        self.assertEqual(self.history('suspicion-end')[-1]['result'],'expired')

    def test_episode_and_rest_survive_a_boost_end_and_a_restart(self):
        self.booster.observe(self.settings,[row('wg',code='VPN-003'),row('ovpn')],PAIR,'OBSERVING',1000)
        self.assertTrue(self.booster.active())
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',1010)
        self.assertTrue(self.booster.suspect(self.settings,self.stall('ovpn','target'),PAIR,'OBSERVING',1000+P.BOOST_HOLD-2))
        self.booster.observe(self.settings,[row('wg'),row('ovpn')],PAIR,'OBSERVING',1000+P.BOOST_HOLD)  # boost ends here
        self.assertFalse(self.booster.active());self.assertIsNotNone(self.booster.dense(1000+P.BOOST_HOLD))
        again=P.Booster(self.runtime,self.persist,write,read)
        self.assertEqual(again.dense(1000+P.BOOST_HOLD)['profile'],'ovpn')
        self.assertEqual(again.public(self.settings,1000+P.BOOST_HOLD)['suspicion']['reason'],'rx-stall')
        self.assertEqual(again.public(self.settings,1000+P.BOOST_HOLD)['effective_interval'],P.DENSE_INTERVAL)


class NoSwitchWithoutProof(unittest.TestCase):
    """Auto (pair_auto.tick) switches only on failover_plan.streak of full-check samples; a suspicion adds none."""
    MAX_AGE=180  # observation_freshness.valid_for at level 1

    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        runtime=Path(temporary.name)/'run';persist=Path(temporary.name)/'etc';runtime.mkdir();persist.mkdir()
        self.booster=P.Booster(runtime,persist,write,read)
        self.settings={'probe_level':1,'interval':60}

    @staticmethod
    def sample(id,t,code=None):
        return {'id':id,'time':t,'code':code,'dns_ok':code is None,'https_success':2 if code is None else 0}

    def decide(self,samples,now):
        failed=failover_plan.streak(samples,'wg',P.CONFIRM_FAILURES,now,self.MAX_AGE,False)
        healthy=failover_plan.streak(samples,'ovpn',2,now,self.MAX_AGE,True)
        return failed and healthy

    def test_a_suspicion_alone_or_with_fewer_than_three_failed_checks_never_switches(self):
        samples=[self.sample('wg',900),self.sample('ovpn',900),self.sample('wg',960),self.sample('ovpn',960)]
        stall=[{'profile':'wg','role':'source','reason':'rx-stall','evidence':{}}]
        self.assertTrue(self.booster.suspect(self.settings,stall,PAIR,'OBSERVING',1000))
        self.assertFalse(self.decide(samples,1000),'suspicion alone')
        for index,t in enumerate((1000,1008,1016)):
            samples+= [self.sample('wg',t,'VPN-003'),self.sample('ovpn',t)]
            self.booster.observe(self.settings,[row('wg',code='VPN-003'),row('ovpn')],PAIR,'OBSERVING',t)
            self.assertEqual(self.decide(samples,t+1),index==2,'after %d failed full checks'%(index+1))

    def test_a_good_check_inside_the_dense_run_breaks_the_streak(self):
        samples=[]
        for t,code in ((1000,'VPN-003'),(1004,'VPN-003'),(1008,None),(1012,'VPN-003'),(1016,'VPN-003')):
            samples+=[self.sample('wg',t,code),self.sample('ovpn',t)]
        self.assertFalse(self.decide(samples,1017))


if __name__=='__main__':unittest.main()
