"""Large-packet (MTU black hole) check of the monitor probe: mtu_check.py and its use by agent.probe and Auto.

Router finding 02.11.2026 (MT3000, matrix phase 2, primary-mtu = nft `oifname @devs meta length > 1300 drop`): the
HTTPS/DNS probes passed, Auto never left the primary and large transfers hung. Shared cases with the Lua twin:
tests/mtu_check_cases.json (tests/lua/test_mtu_check.lua).
"""
import json
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import failover_plan  # noqa: E402
import failure_diagnosis  # noqa: E402
import mtu_check  # noqa: E402
from icmp_ping import checksum  # noqa: E402
import vendor_observation  # noqa: E402

CASES=json.loads((HERE/'mtu_check_cases.json').read_text(encoding='utf-8'))
BINDING={'code':None,'device':'wgclient1','mark':4096,'table':'1001','ifindex':12}
PROFILE={'id':'wireguard:peer_1','interface':'wgclient1'}


class SharedCases(unittest.TestCase):
    def test_classify(self):
        request=CASES['classify_request'];payload=bytes.fromhex(request['payload_hex'])
        for case in CASES['classify']:
            got=mtu_check.classify(bytes.fromhex(case['data_hex']),request['identifier'],request['sequence'],payload,request['target'])
            self.assertEqual(got,case['expect'],case['name'])

    def test_parse_mtu_and_probe_size(self):
        for text,expect in CASES['parse_mtu']:self.assertEqual(mtu_check.parse_mtu(text),expect,repr(text))
        for mtu,expect in CASES['probe_size']:self.assertEqual(mtu_check.probe_size(mtu),expect,repr(mtu))

    def test_verdict(self):
        for case in CASES['verdict']:
            rows=[dict(row,target=target) for row,target in zip(case['rows'],mtu_check.TARGETS)]
            self.assertEqual(mtu_check.verdict(rows),case['expect'],case['name'])

    def test_schedule(self):
        for case in CASES['schedule']:
            schedule=mtu_check.Schedule()
            for op,name,now,value in case['steps']:
                if op=='due':self.assertEqual(schedule.due(name,now),value,case['name']+' @'+str(now))
                else:schedule.record(name,value,now)

    def test_apply_and_sanitize(self):
        for case in CASES['apply']:
            result=mtu_check.apply(dict(case['result']),case['check'])
            self.assertEqual(result['code'],case['code'],case['name'])
            if case['check'] is None:self.assertNotIn('mtu_check',result)
            else:self.assertEqual(result['mtu_check'],case['check'])
        for value,expect in CASES['sanitize']:self.assertEqual(mtu_check.sanitize(value),expect,repr(value))


def counter(start=0):
    state={'n':start}
    def random(n):
        out=bytes((state['n']+i)%256 for i in range(n));state['n']+=n;return out
    return random


class FakeNetwork:
    """A raw ICMP socket whose replies follow a path: drop above `limit` bytes, truncate replies, answer PMTU."""

    def __init__(self,limit=None,truncate=None,answer=True,pmtu=None,refuse=False):
        self.limit=limit;self.truncate=truncate;self.answer=answer;self.pmtu=pmtu;self.refuse=refuse
        self.sent=[];self.inbox=[];self.options={}

    def __call__(self,family,kind,proto):
        assert (family,kind,proto)==(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP)
        return self

    def __enter__(self):return self
    def __exit__(self,*args):return False
    def setsockopt(self,level,name,value):self.options[name]=value
    def settimeout(self,value):pass

    def sendto(self,packet,address):
        if self.refuse:raise OSError(101,'Network is unreachable')
        target=address[0];self.sent.append((target,len(packet)+20))
        if not self.answer:return
        size=len(packet)+20
        if self.pmtu is not None and size>self.pmtu:
            quote=struct.pack('!BBHHHBBH4s4s',0x45,0,size,1,0,64,1,0,socket.inet_aton('10.2.0.2'),socket.inet_aton(target))+packet[:8]
            body=struct.pack('!BBHHH',3,4,0,0,self.pmtu)+quote
            body=body[:2]+struct.pack('!H',checksum(body))+body[4:]
            self.inbox.append(self.ip('10.2.0.1',body));return
        if self.limit is not None and size>self.limit:return
        payload=packet[8:]
        if self.truncate is not None:payload=payload[:self.truncate]
        echo=struct.pack('!BBHHH',0,0,0,*struct.unpack('!HH',packet[4:8]))+payload
        echo=echo[:2]+struct.pack('!H',checksum(echo))+echo[4:]
        self.inbox.append(self.ip(target,echo))

    @staticmethod
    def ip(source,body):
        return struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(body),1,0,64,1,0,socket.inet_aton(source),socket.inet_aton('10.2.0.2'))+body

    def recvfrom(self,size):
        if not self.inbox:raise socket.timeout()
        return self.inbox.pop(0)[:size],('0.0.0.0',0)


def measured(network,size=1350):
    with patch.object(mtu_check.socket,'socket',network):
        return mtu_check.verdict(mtu_check.measure(BINDING,size,random=counter()))


class Measurement(unittest.TestCase):
    def test_plan_sends_one_small_and_two_large_per_target_with_valid_checksums(self):
        probes=mtu_check.plan(1350,counter())
        self.assertEqual([(p['target'],p['kind'],len(p['packet'])+20) for p in probes],
                         [('1.1.1.1','small',64),('1.1.1.1','large',1350),('1.1.1.1','large',1350),
                          ('9.9.9.9','small',64),('9.9.9.9','large',1350),('9.9.9.9','large',1350)])
        for p in probes:self.assertEqual(checksum(p['packet']),0);self.assertTrue(p['payload'].startswith(mtu_check.MAGIC))

    def test_the_router_finding_is_a_black_hole(self):
        # matrix phase 2 primary-mtu: `meta length > 1300 drop` on a WireGuard tunnel of MTU 1350
        self.assertEqual(measured(FakeNetwork(limit=1300)),'black-hole')

    def test_healthy_paths_pass(self):
        self.assertEqual(measured(FakeNetwork()),'ok')
        self.assertEqual(measured(FakeNetwork(),size=1500),'ok')  # OpenVPN tun MTU 1500
        self.assertEqual(measured(FakeNetwork(truncate=64)),'ok')  # truncated replies (8.8.8.8 style)
        self.assertEqual(measured(FakeNetwork(pmtu=1280)),'ok')  # PMTU discovery answers: no black hole

    def test_filtered_icmp_is_inconclusive_and_send_errors_raise(self):
        self.assertEqual(measured(FakeNetwork(answer=False)),'inconclusive')
        with self.assertRaises(OSError):measured(FakeNetwork(refuse=True))

    def test_socket_is_bound_to_the_tunnel_and_marked(self):
        network=FakeNetwork();measured(network)
        self.assertEqual(network.options[getattr(socket,'SO_BINDTODEVICE',25)],b'wgclient1\0')
        self.assertEqual(network.options[getattr(socket,'SO_MARK',36)],4096)
        self.assertEqual(sorted({target for target,_ in network.sent}),['1.1.1.1','9.9.9.9'])

    def test_run_is_rate_limited_and_rechecks_a_black_hole_every_probe(self):
        schedule=mtu_check.Schedule();calls=[]
        def measurer(binding,size):
            calls.append(size);return [{'target':t,'small':'echo','large':[None,None]} for t in mtu_check.TARGETS]
        run=lambda now,**kw:mtu_check.run(schedule,'wireguard:peer_1',BINDING,now,mtu_reader=lambda d:1350,measurer=kw.get('measurer',measurer))
        self.assertEqual(run(0),{'state':'black-hole','size':1350})
        self.assertEqual(run(10),{'state':'black-hole','size':1350})
        healthy=lambda b,s:[{'target':t,'small':'echo','large':['echo','echo']} for t in mtu_check.TARGETS]
        self.assertEqual(run(20,measurer=healthy),{'state':'ok','size':1350})
        self.assertIsNone(run(30));self.assertIsNone(run(319))
        self.assertEqual(run(320,measurer=healthy)['state'],'ok')
        self.assertEqual(calls,[1350,1350])

    def test_run_skips_without_schedule_binding_or_mtu_and_reports_socket_errors(self):
        schedule=mtu_check.Schedule()
        self.assertIsNone(mtu_check.run(None,'x',BINDING,0,mtu_reader=lambda d:1350,measurer=lambda b,s:[]))
        self.assertIsNone(mtu_check.run(schedule,'x',dict(BINDING,mark=0),0,mtu_reader=lambda d:1350,measurer=lambda b,s:[]))
        self.assertIsNone(mtu_check.run(schedule,'x',BINDING,0,mtu_reader=lambda d:None,measurer=lambda b,s:[]))
        self.assertIsNone(mtu_check.run(schedule,'x',BINDING,0,mtu_reader=lambda d:500,measurer=lambda b,s:[]))
        def broken(binding,size):raise OSError('ENETDOWN')
        self.assertEqual(mtu_check.run(schedule,'x',BINDING,0,mtu_reader=lambda d:1350,measurer=broken),{'state':'unavailable','size':1350})


def healthy_trace(device,mark,target):return 20.0


class ProbeIntegration(unittest.TestCase):
    def probe(self,check,https=healthy_trace,dns=True,after=None):
        bindings=[BINDING,after or BINDING]
        with patch.object(agent,'route_binding',side_effect=lambda logical:bindings.pop(0)),\
                patch.object(agent,'https_probe',side_effect=https),patch.object(agent,'dns_probe',return_value=dns),\
                patch('mtu_check.run',return_value=check),patch('server_endpoint.observe',return_value=None),\
                patch.object(agent,'MTU_SCHEDULE',mtu_check.Schedule()):
            return agent.probe(PROFILE)

    def test_monitor_probe_turns_a_black_hole_into_vpn_mtu(self):
        result=self.probe({'state':'black-hole','size':1350})
        self.assertEqual(result['code'],'VPN-MTU');self.assertEqual(result['https_success'],3);self.assertIs(result['dns_ok'],True)
        self.assertEqual(result['mtu_check'],{'state':'black-hole','size':1350})

    def test_other_verdicts_and_other_failures_keep_their_codes(self):
        for state in ('ok','inconclusive','unavailable'):
            self.assertIsNone(self.probe({'state':state,'size':1350})['code'],state)
        self.assertEqual(self.probe({'state':'black-hole','size':1350},dns=False)['code'],'DNS-001')
        self.assertEqual(self.probe({'state':'black-hole','size':1350},https=lambda d,m,t:None)['code'],'VPN-003')
        self.assertNotIn('mtu_check',self.probe(None))

    def test_identity_change_drops_the_check(self):
        result=self.probe({'state':'black-hole','size':1350},after=dict(BINDING,ifindex=13))
        self.assertEqual(result['code'],'VENDOR-IDENTITY-CHANGED');self.assertNotIn('mtu_check',result)

    def test_live_probes_outside_the_monitor_never_run_the_check(self):
        # a process that never ran monitor_loop (native_switch, lua_bridge) keeps the module default None
        self.assertIn('\nMTU_SCHEDULE=None\n',Path(agent.__file__).read_text(encoding='utf-8'))
        with patch.object(agent,'MTU_SCHEDULE',None),patch.object(agent,'route_binding',return_value=BINDING),patch.object(agent,'https_probe',side_effect=healthy_trace),\
                patch.object(agent,'dns_probe',return_value=True),patch('mtu_check.run') as run,patch('server_endpoint.observe',return_value=None):
            result=agent.probe(PROFILE)
        run.assert_not_called();self.assertIsNone(result['code']);self.assertNotIn('mtu_check',result)

    def test_status_rows_keep_only_a_valid_check(self):
        self.assertIn('mtu_check',vendor_observation.MEASUREMENT_FIELDS);self.assertIn('mtu_check',vendor_observation.HEALTH)


def sample(identifier,stamp,code,https=3):
    return {'id':identifier,'time':stamp,'code':code,'dns_ok':True,'https_success':https}


class AutoDecisions(unittest.TestCase):
    def test_vpn_mtu_is_a_failure_streak_and_never_a_ready_target(self):
        now=1000.0
        primary=[sample('p',now-30*i,'VPN-MTU') for i in range(3)]
        self.assertTrue(failover_plan.streak(primary,'p',3,now,90,False))
        self.assertFalse(failover_plan.streak(primary,'p',1,now,90,True))
        reserve=[sample('r',now-30*i,None) for i in range(3)]
        self.assertTrue(failover_plan.streak(reserve,'r',3,now,90,True))

    def test_a_single_mtu_failure_between_good_samples_is_no_streak(self):
        now=1000.0
        samples=[sample('p',now,'VPN-MTU'),sample('p',now-30,None),sample('p',now-60,'VPN-MTU')]
        self.assertFalse(failover_plan.streak(samples,'p',2,now,90,False))

    def test_diagnosis_allows_the_switch(self):
        self.assertIn('VPN-MTU',failure_diagnosis.PROBE_FAILURES);self.assertIn('VPN-MTU',failure_diagnosis.UNSTABLE_CODES)
        status={'time':1000.0,'profiles':[{'id':'p','interface':'wgclient1','time':1000.0,'code':'VPN-MTU','vendor_state':'SETTLED',
                                           'dns_ok':True,'https_success':3}]}
        result=failure_diagnosis.diagnose(status,'p',1000.0,{'interval':10})
        self.assertEqual((result['code'],result['suppress_switch']),('LARGE-PACKETS-FAILED',False))


if __name__=='__main__':
    unittest.main()
