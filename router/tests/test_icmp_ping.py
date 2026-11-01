"""ICMP packets, exact channel fencing and non-blocking cache; no real network."""
import copy
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import icmp_ping as P


def row(**changes):
    value=dict(id='wireguard:peer_1',protocol='wireguard',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',
               vendor_generation='a'*32,vendor_state='SETTLED',administrative_state='enabled',time=1000,
               device='wgclient1',mark=4096,table='1001',ifindex=7,code=None,dns_ok=True,https_success=3,rtt_ms=40)
    value.update(changes);return value


def inventory(profile):
    return {'profiles':[dict(profile)],'servers':[],
            'settings':{'plan_source_tunnel':profile['vendor_tunnel_id'],'plan_source':profile['id']}}


def binding(profile):return dict({key:profile[key]for key in P.BINDING},code=None)


def reply(identifier,sequence,payload,source=P.TARGET):
    icmp=struct.pack('!BBHHH',0,0,0,identifier,sequence)+payload
    icmp=struct.pack('!BBHHH',0,0,P.checksum(icmp),identifier,sequence)+payload
    header=struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(icmp),1,0,64,1,0,socket.inet_aton(source),socket.inet_aton('10.0.0.2'))
    return header+icmp


class PacketSocket:
    def __init__(self):self.options=[];self.sent=[];self.timeouts=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def setsockopt(self,*args):self.options.append(args)
    def settimeout(self,value):self.timeouts.append(value)
    def connect(self,address):self.address=address
    def send(self,packet):self.sent.append(packet);return len(packet)
    def recvfrom(self,limit):
        packet=self.sent[0];_,_,_,identifier,sequence=struct.unpack('!BBHHH',packet[:8])
        return reply(identifier,sequence,packet[8:]),(P.TARGET,0)


class QueuedThread:
    instances=[]
    def __init__(self,**kwargs):self.kwargs=kwargs;self.started=False;self.instances.append(self)
    def start(self):self.started=True
    def run(self):self.kwargs['target'](*self.kwargs['args'])


class IcmpPacketTests(unittest.TestCase):
    def test_actual_socket_is_raw_bound_and_marked_before_one_echo(self):
        fake=PacketSocket()
        with patch.object(P.socket,'socket',return_value=fake)as factory:
            value=P.echo(binding(row()))
        factory.assert_called_once_with(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP)
        self.assertGreaterEqual(value,0);self.assertLessEqual(value,1000)
        self.assertEqual(fake.options,[(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),b'wgclient1\0'),
                                       (socket.SOL_SOCKET,getattr(socket,'SO_MARK',36),4096)])
        self.assertEqual(fake.address,(P.TARGET,0));self.assertEqual(len(fake.sent),1)
        self.assertEqual(P.checksum(fake.sent[0]),0);self.assertTrue(all(0<t<=P.TIMEOUT for t in fake.timeouts))

    def test_reply_requires_matching_ip_type_code_id_sequence_nonce_checksum_and_lengths(self):
        packet=reply(11,22,b'exact-payload')
        self.assertTrue(P.valid_reply(packet,11,22,b'exact-payload'))
        for data,identifier,sequence,payload in [(packet,12,22,b'exact-payload'),(packet,11,23,b'exact-payload'),
                (packet,11,22,b'other-payload'),(reply(11,22,b'exact-payload','9.9.9.9'),11,22,b'exact-payload'),
                (packet[:-1],11,22,b'exact-payload')]:
            self.assertFalse(P.valid_reply(data,identifier,sequence,payload))
        for offset,value in ((0,0x65),(0,0x44),(2,255),(6,0x20),(6,0x80),(9,17),(20,8),(21,1),(22,255),(28,255)):
            corrupted=bytearray(packet);corrupted[offset]=value
            self.assertFalse(P.valid_reply(bytes(corrupted),11,22,b'exact-payload'),(offset,value))

    def test_binding_failure_never_sends_or_retries_unmarked(self):
        fake=PacketSocket();fake.setsockopt=lambda *args:(_ for _ in()).throw(PermissionError('private detail'))
        with patch.object(P.socket,'socket',return_value=fake)as factory:
            with self.assertRaises(PermissionError):P.echo(binding(row()))
        self.assertEqual(factory.call_count,1);self.assertEqual(fake.sent,[])

    def test_absolute_deadline_and_noise_limit_are_bounded(self):
        fake=PacketSocket()
        with patch.object(P.socket,'socket',return_value=fake),patch.object(P.time,'monotonic',side_effect=[10,12]):
            with self.assertRaises(socket.timeout):P.echo(binding(row()))
        self.assertEqual(fake.sent,[],'deadline elapsed before send')
        fake=PacketSocket();fake.recvfrom=lambda count:(b'noise',(P.TARGET,0))
        with patch.object(P.socket,'socket',return_value=fake):
            with self.assertRaises(socket.timeout):P.echo(binding(row()))
        self.assertEqual(len(fake.sent),1)


class PingSamplerTests(unittest.TestCase):
    def sampler(self,profile=None):
        profile=profile or row()
        return P.PingSampler(lambda:inventory(profile),lambda _:binding(profile))

    def test_success_has_separate_icmp_metric_and_verified_identity(self):
        profile=row();sampler=self.sampler(profile)
        with patch.object(P,'echo',return_value=12.5),patch.object(P.time,'time',return_value=1001):result=sampler.measure(profile)
        self.assertEqual(result,P.public(profile,'ok',None,1001,12.5))

    def test_timeout_does_not_change_https_or_vpn_health(self):
        profile=row(code='DNS-001',dns_ok=False);original=copy.deepcopy(profile);sampler=self.sampler(profile)
        with patch.object(P,'echo',side_effect=socket.timeout()):result=sampler.measure(profile)
        self.assertEqual(result['state'],'failed');self.assertEqual(result['code'],'PING-FAILED');self.assertIsNone(result['rtt_ms'])
        self.assertEqual(profile,original)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100):
            sampler.cache[P.signature(profile)]=result;sampler.apply([profile],{'source':profile['id']},result['time'])
        self.assertEqual({k:v for k,v in profile.items()if k not in('ping','ping_last')},original)
        self.assertIsNone(profile['ping_last'],'a timeout is never a last ping value')

    def test_socket_error_is_named_without_private_exception(self):
        with patch.object(P,'echo',side_effect=PermissionError('PRIVATE_SENTINEL')):result=self.sampler().measure(row())
        self.assertEqual(result['code'],'PING-UNAVAILABLE');self.assertNotIn('PRIVATE',str(result))

    def test_nonfinite_boolean_or_overbudget_latency_never_reaches_json(self):
        for value in (True,float('nan'),float('inf'),-1,1001):
            with patch.object(P,'echo',return_value=value):result=self.sampler().measure(row())
            self.assertEqual(result['code'],'PING-UNAVAILABLE');self.assertIsNone(result['rtt_ms'])

    def test_disabled_or_replaced_profile_never_sends(self):
        for change,state in (({'administrative_state':'disabled'},'inactive'),({'id':'wireguard:peer_2'},'unavailable')):
            sampler=self.sampler(row(**change))
            with patch.object(P,'echo')as echo:
                result=sampler.measure(row());echo.assert_not_called()
            self.assertEqual(result['state'],state)
        data=inventory(row());data['servers']=[{'profile':row()['id'],'enabled':False}]
        sampler=P.PingSampler(lambda:data,lambda _:binding(row()))
        with patch.object(P,'echo')as echo:sampler.measure(row());echo.assert_not_called()

    def test_binding_change_before_or_after_echo_discards_ms(self):
        for before in (True,False):
            good=binding(row());bad=dict(good,ifindex=8)
            sampler=P.PingSampler(lambda:inventory(row()),lambda _:good)
            sampler.binding_reader=unittest.mock.Mock(side_effect=[bad]if before else[good,bad])
            with patch.object(P,'echo',return_value=10)as echo:result=sampler.measure(row())
            self.assertEqual(result['code'],'PING-IDENTITY-CHANGED');self.assertIsNone(result['rtt_ms'])
            self.assertEqual(echo.call_count,0 if before else 1)

    def test_profile_replacement_after_success_or_timeout_discards_the_old_identity(self):
        for outcome in (10,socket.timeout()):
            sampler=self.sampler();sampler.inventory_reader=unittest.mock.Mock(side_effect=[inventory(row()),inventory(row(id='wireguard:peer_2'))])
            with patch.object(P,'echo',side_effect=outcome if isinstance(outcome,Exception)else None,return_value=outcome):result=sampler.measure(row())
            self.assertEqual(result['code'],'PING-IDENTITY-CHANGED');self.assertIsNone(result['rtt_ms'])

    def test_apply_never_waits_and_only_one_worker_for_two_selected_channels(self):
        QueuedThread.instances=[];profiles=[row(),row(id='openvpn:1_1',protocol='openvpn',interface='ovpnclient2',device='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2')]
        sampler=self.sampler()
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100),patch.object(sampler,'measure')as measure:
            sampler.apply(profiles,{'source':profiles[0]['id'],'target':profiles[1]['id']},1000)
            measure.assert_not_called();self.assertEqual(len(QueuedThread.instances),1);self.assertEqual(len(sampler.jobs),2)
            sampler.apply(profiles,{'source':profiles[0]['id'],'target':profiles[1]['id']},1001)
            self.assertEqual(len(QueuedThread.instances),1,'no duplicate or queued worker')
        self.assertTrue(all(p['ping']['state']=='checking'for p in profiles))

    def test_finished_worker_cannot_resample_channel_before_its_interval(self):
        QueuedThread.instances=[];profile=row();sampler=self.sampler();sampler.configure(30)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100):
            sampler.apply([profile],{'source':profile['id']},1000)
        with patch.object(sampler,'measure',return_value=P.public(profile,'ok',None,1001,12)):QueuedThread.instances[0].run()
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=127.9):
            sampler.apply([profile],{'source':profile['id']},1029)
        self.assertEqual(len(QueuedThread.instances),1,'never earlier than interval - SLACK')
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=128):
            sampler.apply([profile],{'source':profile['id']},1030)
        self.assertEqual(len(QueuedThread.instances),2)

    def test_owner_interval_default_valid_for_and_slack(self):
        sampler=self.sampler()
        self.assertEqual((sampler.interval,P.INTERVAL),(60,60),'default once a minute')
        sampler.configure(10);self.assertEqual(sampler.valid_for,45,'never below the former 45 s window')
        sampler.configure(300);self.assertEqual(sampler.valid_for,465)
        sampler.configure(10,None,105);self.assertEqual((sampler.interval,sampler.valid_for),(10,105),'valid_for from probe_policy.ping_valid_for')
        # 10 s chosen, passes every 10 s: an echo sent 0.4 s after its pass is still due at the next pass.
        QueuedThread.instances=[];profile=row();sampler=self.sampler();sampler.configure(10)
        sampler.attempts[profile['vendor_tunnel_id']]=100.4
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=110):
            sampler.apply([profile],{'source':profile['id']},1000)
        self.assertEqual(len(QueuedThread.instances),1)

    def test_last_ping_reading_is_kept_per_channel_and_only_from_real_answers(self):
        QueuedThread.instances=[];profile=row();sampler=self.sampler();sampler.configure(30)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100):
            sampler.apply([profile],{'source':profile['id']},1000)
        self.assertIsNone(profile['ping_last'],'never measured: null')
        with patch.object(sampler,'measure',return_value=P.public(profile,'ok',None,1001,42.5)):QueuedThread.instances[0].run()
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=140):
            sampler.apply([profile],{'source':profile['id']},1040)
        self.assertEqual(profile['ping_last'],{'rtt_ms':42.5,'time':1001,'target':'1.1.1.1'})
        # A timeout keeps the last real answer; a stale or rebinding channel and a deselected one keep it too.
        with patch.object(sampler,'measure',return_value=P.public(profile,'failed','PING-FAILED',1041)):QueuedThread.instances[1].run()
        other=row(id='openvpn:1_1',protocol='openvpn',interface='ovpnclient2',device='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2')
        stale=row(time=500)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=150):
            sampler.apply([stale,other],{'source':other['id']},1050)
        self.assertEqual(stale['ping_last']['rtt_ms'],42.5);self.assertEqual(stale['ping']['code'],'PING-NOT-SELECTED')
        self.assertIsNone(other['ping_last'])
        # A channel no longer listed is forgotten; a comparison sampler never writes the shared reading.
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=160):sampler.apply([other],{},1060)
        self.assertEqual(sampler.last,{})
        compare=P.PingSampler(lambda:inventory(row()),lambda _:binding(row()),compare=True);fresh=row()
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100):compare.apply([fresh],{'source':fresh['id']},1000)
        self.assertNotIn('ping_last',fresh)
        self.assertIsNone(P.last_reading(P.public(profile,'stale','PING-DATA-STALE',1000,12)))
        sampler.close();self.assertEqual(sampler.last,{})

    def test_rate_limit_records_actual_packet_send_after_batch_delay(self):
        sampler=self.sampler();profile=row();sampler.attempts[profile['vendor_tunnel_id']]=100
        def delayed(binding,before_send):
            with patch.object(P.time,'monotonic',return_value=120):before_send()
            return 10
        with patch.object(P,'echo',side_effect=delayed):sampler.measure(profile)
        self.assertEqual(sampler.attempts[profile['vendor_tunnel_id']],120)

    def test_disabled_unknown_nonselected_or_stale_measurement_does_not_launch(self):
        for profile,pair,code in [(row(administrative_state='disabled'),{'source':row()['id']},'PING-INACTIVE'),
                (row(administrative_state='unknown'),{'source':row()['id']},'PING-UNAVAILABLE'),
                (row(),{},'PING-NOT-SELECTED'),(row(time=900),{'source':row()['id']},'PING-DATA-STALE')]:
            with patch.object(P,'Thread')as thread:self.sampler(profile).apply([profile],pair,1000);thread.assert_not_called()
            self.assertEqual(profile['ping']['code'],code)

    def test_cache_fresh_stale_future_and_minimum_interval(self):
        sampler=self.sampler();profile=row();key=P.signature(profile);sampler.cache[key]=P.public(profile,'ok',None,1000,12)
        sampler.attempts[profile['vendor_tunnel_id']]=100
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=110):
            sampler.apply([profile],{'source':profile['id']},1010);self.assertEqual(profile['ping']['rtt_ms'],12);self.assertFalse(sampler.jobs)
            profile['time']=1046;sampler.apply([profile],{'source':profile['id']},1046)
            self.assertEqual(profile['ping']['state'],'stale');self.assertEqual(profile['ping']['rtt_ms'],12)  # the last value stays visible (owner rule)
            profile['time']=990;sampler.apply([profile],{'source':profile['id']},990);self.assertEqual(profile['ping']['state'],'stale')

    def test_completed_old_generation_cannot_reenter_cache(self):
        sampler=self.sampler();old=row();key=P.signature(old)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100):sampler.apply([old],{'source':old['id']},1000)
        new=row(vendor_generation='b'*32)
        with patch.object(P,'Thread',QueuedThread):sampler.apply([new],{'source':new['id']},1000)
        with patch.object(sampler,'measure',return_value=P.public(old,'ok',None,1000,10)):sampler._run(key,old)
        self.assertNotIn(key,sampler.cache);self.assertEqual(new['ping']['state'],'checking')

    def test_disabled_gap_and_rebind_do_not_bypass_per_channel_packet_limit(self):
        QueuedThread.instances=[];profile=row();sampler=self.sampler();sampler.configure(30)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=100):sampler.apply([profile],{'source':profile['id']},1000)
        with patch.object(sampler,'measure',return_value=P.public(profile,'ok',None,1001,10)):QueuedThread.instances[0].run()
        disabled=row(administrative_state='disabled')
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=105):sampler.apply([disabled],{'source':profile['id']},1005)
        changed=row(vendor_generation='b'*32,time=1010)
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=110):sampler.apply([changed],{'source':changed['id']},1010)
        self.assertEqual(len(QueuedThread.instances),1,'same logical tunnel is still rate limited after rebind')
        with patch.object(P,'Thread',QueuedThread),patch.object(P.time,'monotonic',return_value=130):sampler.apply([changed],{'source':changed['id']},1030)
        self.assertEqual(len(QueuedThread.instances),2)

    def test_pause_and_shutdown_do_not_launch_or_wait(self):
        sampler=P.PingSampler(lambda:inventory(row()),lambda _:binding(row()),paused=lambda:True)
        with patch.object(P,'Thread')as thread:sampler.apply([row()],{'source':row()['id']},1000);thread.assert_not_called()
        with patch.object(P,'echo')as echo:sampler.measure(row());echo.assert_not_called()
        sampler.close();self.assertTrue(sampler.closed)


if __name__=='__main__':unittest.main()
