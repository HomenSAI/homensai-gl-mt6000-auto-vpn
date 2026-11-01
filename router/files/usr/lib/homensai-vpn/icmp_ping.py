"""Optional ICMP latency for the two selected channels; never a health decision.

One daemon worker, at most two packets in a pass, one per channel per owner ping
interval (option ping_interval: 10 s .. 5 min, default 1 min; probe_policy.ping_interval).
The monitor publishes cached results without waiting for the worker. Every row also
carries ping_last: the last successful answer of that channel with its time, kept in
RAM, so the page can show "42 ms (12 s ago)" instead of a dash once a ping existed. No shell
ping, DNS lookup, flash writes, route changes or fallback to an unbound socket.
"""
import math
import os
import re
import socket
import struct
import subprocess
import time
from threading import Lock, Thread

TARGET='1.1.1.1'
INTERVAL=60  # default owner cadence (probe_policy.PING_INTERVAL_DEFAULT)
VALID_FOR=45  # floor of the freshness window; the monitor configures the real one (probe_policy.ping_valid_for)
SLACK=2  # a due echo may go up to 2 s early: pass jitter must not turn a 10 s choice into 20 s
TIMEOUT=1.0
DEVICE=re.compile(r'^[A-Za-z0-9_.:-]{1,15}$')
LOGICAL=re.compile(r'^[A-Za-z0-9_.-]{1,64}$')
GENERATION=re.compile(r'^[a-f0-9]{32}$')
BINDING=('device','mark','table','ifindex')
IDENTITY=('id','protocol','interface','vendor_tunnel_id','vendor_generation')


def checksum(data):
    if len(data)%2:data+=b'\0'
    total=sum(struct.unpack('!%dH'%(len(data)//2),data))
    while total>>16:total=(total&0xffff)+(total>>16)
    return (~total)&0xffff


def valid_reply(data,identifier,sequence,payload,target=None):
    """Raw IPv4 ICMP echo reply, with the exact random per-request payload."""
    if len(data)<28 or data[0]>>4!=4:return False
    header=(data[0]&15)*4
    if header<20 or header>60 or len(data)<header+8 or data[9]!=socket.IPPROTO_ICMP:return False
    length=struct.unpack('!H',data[2:4])[0]
    if length!=header+8+len(payload) or length>len(data) or struct.unpack('!H',data[6:8])[0]&0xbfff:return False
    if socket.inet_ntoa(data[12:16])!=(target or TARGET):return False
    echo=data[header:length]
    kind,code,_,echo_id,echo_seq=struct.unpack('!BBHHH',echo[:8])
    return (kind==0 and code==0 and echo_id==identifier and echo_seq==sequence
            and echo[8:]==payload and checksum(echo)==0)


def binding_valid(binding):
    return (isinstance(binding,dict) and not binding.get('code')
            and isinstance(binding.get('device'),str) and DEVICE.fullmatch(binding['device']) is not None
            and type(binding.get('mark'))is int and 0<binding['mark']<=0xffffffff
            and type(binding.get('ifindex'))is int and binding['ifindex']>0
            and isinstance(binding.get('table'),str) and binding['table'].isdigit())


def echo(binding,before_send=None,target=None):
    target=target or TARGET
    """A single marked/bound echo. The network deadline is monotonic and absolute."""
    if not binding_valid(binding):raise ValueError('PING-IDENTITY-CHANGED')
    identifier,sequence=struct.unpack('!HH',os.urandom(4));payload=b'HV-PING\0'+os.urandom(16)
    packet=struct.pack('!BBHHH',8,0,0,identifier,sequence)+payload
    packet=struct.pack('!BBHHH',8,0,checksum(packet),identifier,sequence)+payload
    with socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP) as sock:
        # A failure of either binding refuses the check; no unmarked retry exists.
        sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),binding['device'].encode('ascii')+b'\0')
        sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_MARK',36),binding['mark'])
        began=time.monotonic();deadline=began+TIMEOUT
        sock.settimeout(TIMEOUT);sock.connect((target,0))
        left=deadline-time.monotonic()
        if left<=0:raise socket.timeout()
        if before_send is not None:before_send()
        sent_at=time.monotonic()
        if sent_at>=deadline:raise socket.timeout()
        sock.settimeout(deadline-sent_at);sock.send(packet)
        for _ in range(32):
            left=deadline-time.monotonic()
            if left<=0:raise socket.timeout()
            sock.settimeout(left);data,peer=sock.recvfrom(256)
            if peer[0]==target and valid_reply(data,identifier,sequence,payload,target):
                finished=time.monotonic();elapsed=finished-sent_at
                if finished>deadline or not 0<=elapsed<=TIMEOUT:raise socket.timeout()
                return round(elapsed*1000,1)
        raise socket.timeout()


def inventory_identity(data,row):
    """Current selected profile, including operator-disabled monitoring entries."""
    if not isinstance(data,dict):return False
    settings=data.get('settings',{})
    if not isinstance(settings,dict):return False
    anchors={settings.get('plan_'+side+'_tunnel') for side in ('source','target')}
    if row.get('vendor_tunnel_id') not in anchors:return False
    profiles=data.get('profiles',[]);servers=data.get('servers',[])
    if not isinstance(profiles,list)or not isinstance(servers,list):return False
    matches=[p for p in profiles if isinstance(p,dict)and p.get('id')==row.get('id')]
    if len(matches)!=1:return False
    profile=matches[0]
    if profile.get('administrative_state')!='enabled':return False
    if any(isinstance(server,dict)and server.get('profile')==row.get('id')and server.get('enabled')is False for server in servers):return False
    return all(profile.get(key)==row.get(key)for key in IDENTITY if key!='vendor_generation')


def operator_disabled(data,row):
    if not isinstance(data,dict):return False
    profiles=data.get('profiles',[]);servers=data.get('servers',[])
    return (isinstance(profiles,list)and any(isinstance(p,dict)and p.get('id')==row.get('id')
                and p.get('administrative_state')=='disabled'for p in profiles)
            or isinstance(servers,list)and any(isinstance(p,dict)and p.get('profile')==row.get('id')
                and p.get('enabled')is False for p in servers))


def signature(row):
    if (not binding_valid({key:row.get(key)for key in BINDING})or row.get('administrative_state')!='enabled' or row.get('vendor_state')!='SETTLED'
            or row.get('protocol')not in('openvpn','wireguard')or not isinstance(row.get('id'),str)
            or not row['id'].startswith(row['protocol']+':')or len(row['id'])>96
            or not isinstance(row.get('interface'),str)or not LOGICAL.fullmatch(row['interface'])
            or not isinstance(row.get('vendor_generation'),str)or not GENERATION.fullmatch(row['vendor_generation'])
            or row.get('vendor_tunnel_id')!=str(row.get('protocol'))+':'+str(row.get('interface'))):return None
    return tuple(row.get(key)for key in IDENTITY+BINDING)


def public(row,state,code,stamp=None,rtt=None,target=None):
    return {'metric':'icmp-rtt-ms','target':target or TARGET,'state':state,'code':code,'time':stamp,'rtt_ms':rtt,
            'valid_for':VALID_FOR,'interface':row.get('interface'),'vendor_tunnel_id':row.get('vendor_tunnel_id'),
            'generation':row.get('vendor_generation')}


def last_reading(result):
    """The shared last-ping reading of one answer: only a real reply (state ok, finite RTT) counts."""
    if (not isinstance(result,dict) or result.get('state')!='ok' or type(result.get('rtt_ms'))not in(int,float)
            or not math.isfinite(result['rtt_ms']) or type(result.get('time'))not in(int,float) or not math.isfinite(result['time'])):return None
    return {'rtt_ms':result['rtt_ms'],'time':result['time'],'target':result.get('target') or TARGET}


class PingSampler:
    def __init__(self,inventory_reader,binding_reader,paused=lambda:False,compare=False):
        self.inventory_reader=inventory_reader;self.binding_reader=binding_reader;self.paused=paused;self.compare=compare
        self.lock=Lock();self.cache={};self.jobs={};self.attempts={};self.current=set();self.closed=False;self.worker=None
        self.interval=INTERVAL;self.valid_for=VALID_FOR;self.target=TARGET;self.last={}

    def configure(self,interval,target=None,valid_for=None):
        """Owner ping cadence; valid_for from probe_policy.ping_valid_for (default 1.5 cadences + probe budget)."""
        with self.lock:
            self.interval=interval;self.valid_for=valid_for if valid_for else max(VALID_FOR,int(interval*3//2+15))
            if target and target!=self.target:self.target=target;self.cache={}

    def measure(self,row):
        if self.closed or self.paused():return public(row,'unavailable','PING-UNAVAILABLE',time.time())
        try:
            current=self.inventory_reader()
            if not inventory_identity(current,row):
                if operator_disabled(current,row):return public(row,'inactive','PING-INACTIVE',time.time())
                return public(row,'unavailable','PING-IDENTITY-CHANGED',time.time())
            before=self.binding_reader(row['interface'])
            if not binding_valid(before)or any(before.get(key)!=row.get(key)for key in BINDING):
                return public(row,'unavailable','PING-IDENTITY-CHANGED',time.time())
            if self.closed or self.paused():return public(row,'unavailable','PING-UNAVAILABLE',time.time())
            state,code,rtt='ok',None,None
            try:
                target=self.target;rtt=echo(before,before_send=lambda:self._record_send(row),**({'target':target} if target!=TARGET else {}))
                if type(rtt)not in(int,float)or not math.isfinite(rtt)or not 0<=rtt<=TIMEOUT*1000:raise ValueError('invalid ICMP RTT')
            except socket.timeout:state,code='failed','PING-FAILED'
            except (OSError,ValueError):state,code,rtt='unavailable','PING-UNAVAILABLE',None
            measured_at=time.time()
            after=self.binding_reader(row['interface'])
            if (not binding_valid(after)or any(after.get(key)!=before.get(key)for key in BINDING)
                    or not inventory_identity(self.inventory_reader(),row)):
                return public(row,'unavailable','PING-IDENTITY-CHANGED',time.time())
            return public(row,state,code,measured_at,rtt,target)
        except socket.timeout:return public(row,'failed','PING-FAILED',time.time())
        except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError):
            return public(row,'unavailable','PING-UNAVAILABLE',time.time())

    def _record_send(self,row):
        # A batch's second channel may start later: throttle from its actual send,
        # not from when the monitor queued the whole batch.
        with self.lock:
            if self.closed or self.paused():raise OSError('PING-UNAVAILABLE')
            self.attempts[row['vendor_tunnel_id']]=time.monotonic()

    def _run(self,key,row):
        try:result=self.measure(row)
        except Exception:result=public(row,'unavailable','PING-UNAVAILABLE',time.time())
        if isinstance(result,dict) and 'valid_for' in result:result['valid_for']=self.valid_for;result['target']=self.target
        with self.lock:
            if not self.closed and key in self.current:self.cache[key]=result
            if not self.closed and last_reading(result) is not None:self.last[row['id']]=last_reading(result)
            self.jobs.pop(key,None)

    def _run_batch(self,batch):
        try:
            for key,row in batch:self._run(key,row)
        finally:
            with self.lock:
                self.worker=None
                for key,_ in batch:self.jobs.pop(key,None)

    def apply(self,rows,pair,now):
        """Decorate only nested ping; never modify the original channel health."""
        selected={pair.get('source'),pair.get('target')}-{None}
        eligible={signature(row) for row in rows if row.get('id')in selected and signature(row)is not None
                  and type(row.get('time'))in(int,float)and math.isfinite(row['time'])and -5<=now-row['time']<=self.valid_for}
        batch=[];thread=None
        with self.lock:
            self.current=eligible
            self.cache={key:value for key,value in self.cache.items()if key in eligible}
            # Packet rate belongs to the logical channel, even across a new server/generation
            # or a brief disabled/stale observation. Otherwise rebinds could bypass the limit.
            live={row.get('vendor_tunnel_id')for row in rows if row.get('id')in selected}
            monotonic_now=time.monotonic()
            self.attempts={key:value for key,value in self.attempts.items()if key in live or monotonic_now-value<self.interval}
            if not self.compare:
                # The last answer belongs to the channel (profile id); kept only for channels still listed.
                listed={row.get('id')for row in rows}
                self.last={key:value for key,value in self.last.items()if key in listed}
                for row in rows:row['ping_last']=dict(self.last[row['id']])if row.get('id')in self.last else None
            for row in rows:
                if row.get('id')not in selected:
                    if not self.compare:row['ping']=public(row,'inactive','PING-NOT-SELECTED')
                    continue
                key=signature(row)
                if key is None:
                    state='inactive'if row.get('administrative_state')=='disabled'or not row.get('interface')else'unavailable'
                    self._put(row,public(row,state,'PING-INACTIVE'if state=='inactive'else'PING-UNAVAILABLE'));continue
                if key not in eligible:
                    self._put(row,public(row,'stale','PING-DATA-STALE'));continue
                value=self.cache.get(key)
                self._put(row,dict(value,valid_for=self.valid_for)if value else public(row,'checking','PING-CHECK-PENDING'))
                if value and (type(value.get('time'))not in(int,float)or not math.isfinite(value['time'])or not -5<=now-value['time']<=self.valid_for):
                    self._put(row,public(row,'stale','PING-DATA-STALE',value.get('time'),value.get('rtt_ms'),value.get('target')))
                if (not self.closed and not self.paused() and self.worker is None and key not in self.jobs and len(batch)<2
                        and monotonic_now-self.attempts.get(row['vendor_tunnel_id'],float('-inf'))>=self.interval-SLACK):
                    snapshot={name:row.get(name)for name in IDENTITY+BINDING+('administrative_state','vendor_state')}
                    self.attempts[row['vendor_tunnel_id']]=monotonic_now;batch.append((key,snapshot))
            if batch:
                thread=Thread(target=self._run_batch,args=(batch,),name='icmp-ping',daemon=True)
                self.worker=thread
                for key,_ in batch:self.jobs[key]=thread
        if thread is not None:
            try:thread.start()
            except Exception:
                with self.lock:
                    self.worker=None
                    for key,row in batch:self.jobs.pop(key,None);self.cache[key]=public(row,'unavailable','PING-UNAVAILABLE',now)

    def _put(self,row,value):
        if not self.compare:row['ping']=value
        else:
            extra=row.get('ping_compare') if isinstance(row.get('ping_compare'),dict) else {}
            extra[self.target]=value;row['ping_compare']=extra

    def idle(self):
        with self.lock:return self.worker is None

    def close(self):
        with self.lock:self.closed=True;self.current.clear();self.cache.clear();self.last.clear()
