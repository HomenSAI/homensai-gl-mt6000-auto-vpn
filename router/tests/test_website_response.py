"""Bounded marked website requests, strict coverage and a nonblocking cache."""
import copy,socket,ssl,struct,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import website_response as W
from test_icmp_ping import row,inventory,binding,QueuedThread


def name(host):return b''.join(bytes([len(x)])+x.encode() for x in host.split('.'))+b'\0'
def response(host='www.example.com',address='93.184.216.34',identifier=7):
    return struct.pack('!HHHHHH',identifier,0x8180,1,1,0,0)+name(host)+b'\0\1\0\1'+b'\xc0\x0c'+struct.pack('!HHIH',1,1,60,4)+socket.inet_aton(address)
def result(target,ms=100,state='ok'):
    key,host,path,_=target
    return {'id':key,'url':'https://'+host+path,'state':state,'elapsed_ms':ms if state=='ok' else None,'code':None if state=='ok' else 'WEBSITE-TIMEOUT'}


class ImmediatePool:
    def __init__(self,**kwargs):pass
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def map(self,fn,items):return map(fn,items)


class TimedSocket:
    def __init__(self,clock,chunks=None):
        self.clock=clock;self.chunks=list(chunks or [b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n',b'\r\n'])
        self.options=[];self.timeouts=[];self.sent=[];self.closed=False
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):self.closed=True
    def setsockopt(self,*args):self.options.append(args)
    def settimeout(self,value):self.timeouts.append(value)
    def connect(self,address):self.address=address;self.clock[0]+=.02
    def sendall(self,data):self.sent.append(data);self.clock[0]+=.04
    def recv(self,size):
        self.clock[0]+=.05
        return self.chunks.pop(0) if self.chunks else b''


class DNSAndSocket(unittest.TestCase):
    def test_dns_answer_checks_id_question_public_address_and_truncation(self):
        self.assertEqual(W.dns_answer(response(),7,'www.example.com'),'93.184.216.34')
        for wire,identifier,host in ((response(),8,'www.example.com'),(response(),7,'wrong.example.com'),
                                     (response(address='192.168.1.1'),7,'www.example.com'),(response()[:-1],7,'www.example.com')):
            with self.subTest(wire=wire),self.assertRaises(W.WebsiteError):W.dns_answer(wire,identifier,host)
        truncated=bytearray(response());truncated[2]|=2
        with self.assertRaises(W.WebsiteError):W.dns_answer(bytes(truncated),7,'www.example.com')

    def test_dns_cname_chain_is_followed_but_unrelated_answers_and_compression_loops_refuse(self):
        host='www.example.com';alias='edge.example.net'
        wire=struct.pack('!HHHHHH',7,0x8180,1,2,0,0)+name(host)+b'\0\1\0\1'
        wire+=b'\xc0\x0c'+struct.pack('!HHIH',5,1,60,len(name(alias)))+name(alias)
        wire+=name(alias)+struct.pack('!HHIH',1,1,60,4)+socket.inet_aton('93.184.216.34')
        self.assertEqual(W.dns_answer(wire,7,host),'93.184.216.34')
        with self.assertRaises(W.WebsiteError):W.dns_answer(response('unrelated.example.net'),7,host)
        with self.assertRaises(W.WebsiteError):W.dns_name(b'\xc0\0',0)

    def test_socket_binds_device_and_mark_without_retry_when_binding_fails(self):
        sock=TimedSocket([0])
        with patch.object(W.socket,'socket',return_value=sock) as factory:
            self.assertIs(W.bound_socket(binding(row())),sock)
        factory.assert_called_once_with(socket.AF_INET,socket.SOCK_STREAM)
        self.assertEqual(sock.options,[(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),b'wgclient1\0'),
                                       (socket.SOL_SOCKET,getattr(socket,'SO_MARK',36),4096)])
        sock.setsockopt=Mock(side_effect=PermissionError('PRIVATE_SENTINEL'))
        with patch.object(W.socket,'socket',return_value=sock) as factory,self.assertRaises(PermissionError):W.bound_socket(binding(row()),True)
        factory.assert_called_once();self.assertTrue(sock.closed)

    def test_dns_uses_only_marked_connected_explicit_resolver(self):
        sock=TimedSocket([10]);sent=[]
        sock.send=lambda data:sent.append(data)
        def recv(size):
            identifier=struct.unpack('!H',sent[0][:2])[0]
            return response('www.example.com',identifier=identifier)
        sock.recv=recv
        with patch.object(W,'bound_socket',return_value=sock),patch.object(W.time,'monotonic',return_value=10):
            self.assertEqual(W.resolve(binding(row()),'www.example.com',16),'93.184.216.34')
        self.assertEqual(sock.address,(W.RESOLVER,53));self.assertEqual(len(sent),1)


class RequestTiming(unittest.TestCase):
    def measured(self,chunks=None,context_error=None):
        clock=[10.];sock=TimedSocket(clock,chunks);context=Mock()
        def resolve(*args):clock[0]+=.01;return '93.184.216.34'
        def wrap(raw,server_hostname):
            self.assertEqual(server_hostname,W.TARGETS[1][1]);clock[0]+=.03
            if context_error:raise context_error
            return raw
        context.wrap_socket.side_effect=wrap
        with patch.object(W,'resolve',side_effect=resolve),patch.object(W,'bound_socket',return_value=sock),patch.object(W.time,'monotonic',side_effect=lambda:clock[0]):
            value=W.measure_site(binding(row()),W.TARGETS[1],context)
        return value,sock

    def test_monotonic_clock_includes_dns_tcp_tls_send_and_complete_headers(self):
        value,sock=self.measured()
        self.assertEqual(value['elapsed_ms'],200.0);self.assertEqual(value['state'],'ok');self.assertEqual(value['http_status'],200)
        self.assertIn(b'GET /cdn-cgi/trace HTTP/1.1',sock.sent[0]);self.assertIn(W.USER_AGENT.encode(),sock.sent[0])
        self.assertTrue(all(0<t<=W.HOST_SECONDS for t in sock.timeouts))  # one site budget, no 3 s per-operation cap

    def test_tls_failure_redirect_wrong_status_and_oversized_headers_never_become_zero_samples(self):
        value,_=self.measured(context_error=ssl.SSLError('PRIVATE_SENTINEL'))
        self.assertEqual(value['code'],'WEBSITE-TLS-FAILED');self.assertIsNone(value['http_status']);self.assertIsNone(value['elapsed_ms']);self.assertNotIn('PRIVATE',str(value))
        for chunks in ([b'HTTP/1.1 302 Found\r\nLocation: https://elsewhere/\r\n\r\n'],[b'HTTP/1.1 500 Fail\r\n\r\n'],[b'x'*4096]*4):
            value,_=self.measured(chunks)
            self.assertEqual(value['code'],'WEBSITE-HTTP-FAILED');self.assertIsNone(value['elapsed_ms'])

    def test_absolute_total_deadline_rejects_slow_header_drip(self):
        clock=[0.];sock=TimedSocket(clock,[b'x']*100)
        context=Mock();context.wrap_socket.return_value=sock
        def recv(size):clock[0]+=2;return b'x'
        sock.recv=recv
        with patch.object(W,'resolve',return_value='93.184.216.34'),patch.object(W,'bound_socket',return_value=sock),patch.object(W.time,'monotonic',side_effect=lambda:clock[0]):
            value=W.measure_site(binding(row()),W.TARGETS[1],context)
        self.assertEqual(value['code'],'WEBSITE-TIMEOUT');self.assertIsNone(value['elapsed_ms']);self.assertLessEqual(clock[0],6.1)


class CoverageAndSampler(unittest.TestCase):
    def sampler(self):return W.WebsiteSampler(lambda:inventory(row()),lambda _:binding(row()))

    def test_new_metric_rounding_is_half_up_for_current_and_weighted_period_values(self):
        self.assertEqual(W.round_ms(10.25),10.3);self.assertEqual(W.round_ms(10.35),10.4)
        self.assertEqual(W.mean_ms([10.2,10.3,10.4]),10.3)
        self.assertEqual(W.mean_from_tenths(205,2),10.3)
        self.assertIsNone(W.mean_from_tenths(0,0))
        for value in (True,float('nan'),-1,6001):
            with self.assertRaises(ValueError):W.round_ms(value)

    def test_mean_is_arithmetic_only_for_three_valid_successes(self):
        values=[result(target,ms) for target,ms in zip(W.TARGETS,(50,100,300))]
        good=W.public(row(),'ok',None,1000,values);self.assertEqual(good['avg_ms'],150);self.assertEqual(good['successes'],3)
        values[2]=result(W.TARGETS[2],state='failed')
        partial=W.public(row(),'partial','WEBSITE-PARTIAL',1000,values)
        self.assertIsNone(partial['avg_ms']);self.assertEqual(partial['successes'],2);self.assertEqual(partial['attempted'],3)

    def test_duplicate_sites_wrong_urls_or_invalid_numbers_never_fake_three_site_coverage(self):
        original=[result(target,100) for target in W.TARGETS]
        for mutate in (lambda rows:rows.__setitem__(2,copy.deepcopy(rows[0])),lambda rows:rows[2].update(url='https://unconfigured.example/'),
                       lambda rows:rows[2].update(elapsed_ms=True),lambda rows:rows[2].update(elapsed_ms=float('nan'))):
            rows=copy.deepcopy(original);mutate(rows);value=W.public(row(),'ok',None,1000,rows)
            self.assertIsNone(value['avg_ms']);self.assertNotEqual(value['state'],'ok')

    def test_sampler_before_after_binding_checks_discard_even_three_successes(self):
        sampler=self.sampler();sampler.context=Mock();sampler.binding_reader=Mock(side_effect=[binding(row()),dict(binding(row()),ifindex=99)])
        with patch.object(W,'ThreadPoolExecutor',ImmediatePool),patch.object(W,'measure_site',side_effect=lambda b,t,c:result(t)):
            value=sampler.measure(row())
        self.assertEqual(value['code'],'WEBSITE-IDENTITY-CHANGED');self.assertIsNone(value['avg_ms'])

    def test_reused_tls_context_is_created_outside_measured_requests(self):
        sampler=self.sampler();clock=[10.];starts=[];context=Mock()
        def create():clock[0]+=100;return context
        def measured(b,t,c):starts.append(clock[0]);return result(t,100)
        with patch.object(W.ssl,'create_default_context',side_effect=create) as create_context,patch.object(W,'ThreadPoolExecutor',ImmediatePool), \
                patch.object(W,'measure_site',side_effect=measured),patch.object(W.time,'monotonic',side_effect=lambda:clock[0]):
            first=sampler.measure(row());second=sampler.measure(row())
        create_context.assert_called_once();self.assertEqual(starts,[110]*6)
        self.assertEqual(first['avg_ms'],100);self.assertEqual(second['avg_ms'],100)

    def test_apply_does_not_wait_spawn_duplicates_or_modify_health(self):
        sampler=self.sampler();profile=row();before=copy.deepcopy(profile);QueuedThread.instances=[]
        with patch.object(W,'Thread',QueuedThread),patch.object(W.time,'monotonic',return_value=100),patch.object(sampler,'measure') as measure:
            sampler.apply([profile],{'source':profile['id']},1000);sampler.apply([profile],{'source':profile['id']},1000)
            measure.assert_not_called();self.assertEqual(len(QueuedThread.instances),1)
        self.assertEqual({k:v for k,v in profile.items() if k!='website_response'},before)
        self.assertEqual(profile['website_response']['state'],'checking')

    def test_cache_generation_expiry_and_logical_channel_rate_limit(self):
        sampler=self.sampler();profile=row();key=W.signature(profile)
        sampler.cache[key]=W.public(profile,'ok',None,1000,[result(t) for t in W.TARGETS]);sampler.attempts[profile['vendor_tunnel_id']]=100
        with patch.object(W,'Thread',QueuedThread),patch.object(W.time,'monotonic',return_value=110):
            sampler.apply([profile],{'source':profile['id']},1010);self.assertEqual(profile['website_response']['avg_ms'],100)
            profile['time']=1046;sampler.apply([profile],{'source':profile['id']},1046);self.assertEqual(profile['website_response']['state'],'stale')
            changed=row(vendor_generation='b'*32,time=1010);sampler.apply([changed],{'source':changed['id']},1010)
            self.assertEqual(changed['website_response']['state'],'checking');self.assertNotIn(key,sampler.cache)
        self.assertIsNone(sampler.worker)

    def test_shutdown_pause_disabled_or_old_rows_never_dispatch(self):
        for profile in (row(administrative_state='disabled'),row(time=900)):
            sampler=self.sampler()
            with patch.object(W,'Thread') as thread:sampler.apply([profile],{'source':profile['id']},1000);thread.assert_not_called()
        sampler=self.sampler();sampler.close()
        with patch.object(W,'measure_site') as request:
            value=sampler.measure(row());request.assert_not_called();self.assertEqual(value['state'],'unavailable')


if __name__=='__main__':unittest.main()
