"""Three ordinary HTTPS responses through one selected VPN, independent of health.

Fresh marked DNS, TCP, authenticated TLS and complete HTTP headers are timed.
Only three successes produce the arithmetic headline mean. No browser contents,
redirect following, system DNS, unbound retry or synchronous monitor wait.
"""
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import math
import os
import re
import socket
import ssl
import struct
import time
from threading import Lock,Thread
from icmp_ping import binding_valid,signature,inventory_identity,operator_disabled,BINDING,IDENTITY
from probe_deadline import remaining

METRIC='websites-https-mean-ms-v1'
TARGET_SET='google-cloudflare-wikipedia-v1'
DEFINITION='DNS + TCP + TLS + complete HTTP headers; fresh connection; router-originated'
INTERVAL=30
VALID_FOR=45
HOST_SECONDS=6
MAX_MS=6000
MAX_HEADERS=16384
RESOLVER='9.9.9.9'
USER_AGENT='HomenSAI-AutoVPN/0.9.1 (+https://homensai.com)'
TARGETS=(('google','www.google.com','/generate_204',204),
         ('cloudflare','www.cloudflare.com','/cdn-cgi/trace',200),
         ('wikipedia','www.wikipedia.org','/',200))


class WebsiteError(ValueError):pass


def round_ms(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=MAX_MS:raise ValueError('WEBSITE-VALUE')
    return math.floor(value*10+.5)/10


def mean_from_tenths(total_tenths,count):
    if type(total_tenths) is not int or type(count) is not int or total_tenths<0 or count<0 or total_tenths>MAX_MS*10*count:raise ValueError('WEBSITE-VALUE')
    if count==0:return None
    return ((2*total_tenths+count)//(2*count))/10


def mean_ms(values):
    tenths=[int(math.floor(round_ms(value)*10+.5)) for value in values]
    return mean_from_tenths(sum(tenths),len(tenths))


def bound_socket(binding,udp=False):
    if not binding_valid(binding):raise WebsiteError('WEBSITE-IDENTITY-CHANGED')
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if udp else socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),binding['device'].encode('ascii')+b'\0')
        sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_MARK',36),binding['mark'])
        return sock
    except BaseException:sock.close();raise


def dns_name(packet,offset):
    labels=[];seen=set();next_offset=None
    for _ in range(32):
        if offset>=len(packet) or offset in seen:raise WebsiteError('WEBSITE-DNS-FAILED')
        seen.add(offset);length=packet[offset];offset+=1
        if length&0xc0==0xc0:
            if offset>=len(packet):raise WebsiteError('WEBSITE-DNS-FAILED')
            if next_offset is None:next_offset=offset+1
            offset=((length&63)<<8)|packet[offset];continue
        if length&0xc0 or length>63 or offset+length>len(packet):raise WebsiteError('WEBSITE-DNS-FAILED')
        if not length:return '.'.join(labels),next_offset if next_offset is not None else offset
        try:label=packet[offset:offset+length].decode('ascii').lower()
        except UnicodeError:raise WebsiteError('WEBSITE-DNS-FAILED') from None
        if not re.fullmatch('[a-z0-9_-]{1,63}',label):raise WebsiteError('WEBSITE-DNS-FAILED')
        labels.append(label);offset+=length
    raise WebsiteError('WEBSITE-DNS-FAILED')


def dns_answer(packet,identifier,hostname):
    if len(packet)<12:raise WebsiteError('WEBSITE-DNS-FAILED')
    token,flags,questions,answers,_,_=struct.unpack('!HHHHHH',packet[:12])
    if token!=identifier or flags&0x8000==0 or flags&0x7a0f or questions!=1 or not 1<=answers<=64:raise WebsiteError('WEBSITE-DNS-FAILED')
    name,offset=dns_name(packet,12)
    if name!=hostname or offset+4>len(packet) or packet[offset:offset+4]!=b'\0\1\0\1':raise WebsiteError('WEBSITE-DNS-FAILED')
    offset+=4;records={};aliases={}
    for _ in range(answers):
        name,offset=dns_name(packet,offset)
        if offset+10>len(packet):raise WebsiteError('WEBSITE-DNS-FAILED')
        kind,group,_,length=struct.unpack('!HHIH',packet[offset:offset+10]);offset+=10;end=offset+length
        if end>len(packet):raise WebsiteError('WEBSITE-DNS-FAILED')
        if group==1 and kind==1:
            if length!=4:raise WebsiteError('WEBSITE-DNS-FAILED')
            address=ipaddress.IPv4Address(packet[offset:end])
            if address.is_global and not address.is_multicast:records.setdefault(name,[]).append(str(address))
        elif group==1 and kind==5:
            alias,consumed=dns_name(packet,offset)
            if consumed!=end or name in aliases and aliases[name]!=alias:raise WebsiteError('WEBSITE-DNS-FAILED')
            aliases[name]=alias
        offset=end
    current=hostname;seen=set()
    for _ in range(9):
        if current in seen:break
        seen.add(current)
        if current in records and current not in aliases:return records[current][0]
        if current not in aliases:break
        current=aliases[current]
    raise WebsiteError('WEBSITE-DNS-FAILED')


def resolve(binding,hostname,deadline):
    identifier=struct.unpack('!H',os.urandom(2))[0]
    question=b''.join(bytes([len(label)])+label.encode('ascii') for label in hostname.split('.'))+b'\0\0\1\0\1'
    packet=struct.pack('!HHHHHH',identifier,0x100,1,0,0,0)+question
    with bound_socket(binding,udp=True) as sock:
        sock.settimeout(remaining(deadline));sock.connect((RESOLVER,53));sock.send(packet)
        sock.settimeout(remaining(deadline));answer=sock.recv(4096);remaining(deadline)
    return dns_answer(answer,identifier,hostname)


def measure_site(binding,target,context):
    identifier,hostname,path,expected=target
    result={'id':identifier,'url':'https://'+hostname+path,'state':'failed','elapsed_ms':None,'http_status':None,'code':'WEBSITE-RESPONSE-FAILED'}
    began=time.monotonic();deadline=began+HOST_SECONDS
    try:
        address=resolve(binding,hostname,deadline)
        with bound_socket(binding) as raw:
            raw.settimeout(remaining(deadline));raw.connect((address,443));raw.settimeout(remaining(deadline))
            with context.wrap_socket(raw,server_hostname=hostname) as sock:
                sock.settimeout(remaining(deadline))
                request=('GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: %s\r\nAccept: text/html,text/plain,*/*\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n'%(path,hostname,USER_AGENT)).encode('ascii')
                sock.sendall(request);headers=b''
                while b'\r\n\r\n' not in headers:
                    left=MAX_HEADERS-len(headers)
                    if left<=0:raise WebsiteError('WEBSITE-HTTP-FAILED')
                    sock.settimeout(remaining(deadline));chunk=sock.recv(min(4096,left));remaining(deadline)
                    if not chunk:raise WebsiteError('WEBSITE-HTTP-FAILED')
                    headers+=chunk
                block=headers.split(b'\r\n\r\n',1)[0];lines=block.split(b'\r\n')
                status=re.fullmatch(rb'HTTP/1\.[01] ([0-9]{3})(?: [^\r\n]*)?',lines[0])
                if status:result['http_status']=int(status[1])
                if not status or result['http_status']!=expected:raise WebsiteError('WEBSITE-HTTP-FAILED')
                if any(not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+:[^\x00\r\n]*",line) for line in lines[1:]):raise WebsiteError('WEBSITE-HTTP-FAILED')
                remaining(deadline);elapsed=(time.monotonic()-began)*1000
                if not 0<=elapsed<=MAX_MS:raise socket.timeout()
                result.update(state='ok',elapsed_ms=round_ms(elapsed),code=None)
    except socket.timeout:result['code']='WEBSITE-TIMEOUT'
    except ssl.SSLError:result['code']='WEBSITE-TLS-FAILED'
    except WebsiteError as error:result['code']=str(error) if str(error) in ('WEBSITE-DNS-FAILED','WEBSITE-HTTP-FAILED','WEBSITE-IDENTITY-CHANGED') else 'WEBSITE-UNAVAILABLE'
    except (OSError,ValueError,TypeError):result.update(state='unavailable',code='WEBSITE-UNAVAILABLE')
    return result


def public(row,state='checking',code='WEBSITE-CHECK-PENDING',stamp=None,results=None):
    results=[dict(result) for result in results] if results else []
    for result in results:
        value=result.get('elapsed_ms')
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=MAX_MS):
            result.update(elapsed_ms=None,state='unavailable',code='WEBSITE-UNAVAILABLE')
    expected={target[0]:'https://'+target[1]+target[2] for target in TARGETS};seen=set();values=[]
    for result in results:
        key=result.get('id')
        if (key in expected and key not in seen and result.get('url')==expected[key] and result.get('state')=='ok'
                and type(result.get('elapsed_ms')) in (int,float) and math.isfinite(result['elapsed_ms']) and 0<=result['elapsed_ms']<=MAX_MS):
            seen.add(key);values.append(result['elapsed_ms'])
    success=len(values)
    if state=='ok' and (success!=3 or len(results)!=3):
        state='partial' if success else 'failed';code='WEBSITE-PARTIAL' if success else 'WEBSITE-RESPONSE-FAILED'
    return {'metric':METRIC,'target_set':TARGET_SET,'definition':DEFINITION,'state':state,'code':code,
            'avg_ms':mean_ms(values) if success==3 and state=='ok' else None,'time':stamp,'valid_for':VALID_FOR,
            'successes':success,'attempted':3,'results':results,'interface':row.get('interface'),
            'vendor_tunnel_id':row.get('vendor_tunnel_id'),'generation':row.get('vendor_generation')}


class WebsiteSampler:
    def __init__(self,inventory_reader,binding_reader,paused=lambda:False):
        self.inventory_reader=inventory_reader;self.binding_reader=binding_reader;self.paused=paused
        self.lock=Lock();self.cache={};self.current=set();self.attempts={};self.worker=None;self.closed=False;self.context=None

    def measure(self,row):
        try:
            if self.closed or self.paused():return public(row,'unavailable','WEBSITE-UNAVAILABLE',time.time())
            data=self.inventory_reader()
            if not inventory_identity(data,row):return public(row,'inactive' if operator_disabled(data,row) else 'unavailable','WEBSITE-IDENTITY-CHANGED',time.time())
            before=self.binding_reader(row['interface'])
            if not binding_valid(before) or any(before.get(key)!=row.get(key) for key in BINDING):return public(row,'unavailable','WEBSITE-IDENTITY-CHANGED',time.time())
            if self.context is None:self.context=ssl.create_default_context()
            # Context/CA setup is reused outside every measured request, like a browser's TLS configuration.
            with self.lock:
                if self.closed or self.paused():return public(row,'unavailable','WEBSITE-UNAVAILABLE',time.time())
                self.attempts[row['vendor_tunnel_id']]=time.monotonic()
            with ThreadPoolExecutor(max_workers=3) as pool:
                results=list(pool.map(lambda target:measure_site(before,target,self.context),TARGETS))
            after=self.binding_reader(row['interface'])
            if not binding_valid(after) or any(after.get(key)!=before.get(key) for key in BINDING) or not inventory_identity(self.inventory_reader(),row):return public(row,'unavailable','WEBSITE-IDENTITY-CHANGED',time.time())
            count=sum(r['state']=='ok' for r in results);state='ok' if count==3 else 'partial' if count else 'failed'
            return public(row,state,None if count==3 else 'WEBSITE-PARTIAL' if count else 'WEBSITE-RESPONSE-FAILED',time.time(),results)
        except Exception:return public(row,'unavailable','WEBSITE-UNAVAILABLE',time.time())

    def run_batch(self,batch):
        try:
            for key,row in batch:
                result=self.measure(row)
                with self.lock:
                    if not self.closed and key in self.current:self.cache[key]=result
        finally:
            with self.lock:self.worker=None

    def apply(self,rows,pair,now):
        selected={pair.get('source'),pair.get('target')}-{None};batch=[];thread=None
        eligible={signature(row) for row in rows if row.get('id') in selected and signature(row) is not None
                  and type(row.get('time')) in (int,float) and math.isfinite(row['time']) and -5<=now-row['time']<=VALID_FOR}
        with self.lock:
            self.current=eligible;self.cache={key:value for key,value in self.cache.items() if key in eligible}
            mono=time.monotonic();live={row.get('vendor_tunnel_id') for row in rows if row.get('id') in selected}
            self.attempts={key:value for key,value in self.attempts.items() if key in live or mono-value<INTERVAL}
            for row in rows:
                key=signature(row)
                if row.get('id') not in selected:row['website_response']=public(row,'inactive','WEBSITE-NOT-SELECTED');continue
                if key not in eligible:row['website_response']=public(row,'unavailable','WEBSITE-IDENTITY-CHANGED');continue
                result=self.cache.get(key);row['website_response']=dict(result) if result else public(row)
                if result and (type(result.get('time')) not in (int,float) or not math.isfinite(result['time']) or not -5<=now-result['time']<=VALID_FOR):row['website_response']=public(row,'stale','WEBSITE-DATA-STALE',result.get('time'))
                if not self.closed and not self.paused() and self.worker is None and len(batch)<2 and mono-self.attempts.get(row['vendor_tunnel_id'],float('-inf'))>=INTERVAL:
                    self.attempts[row['vendor_tunnel_id']]=mono
                    batch.append((key,{name:row.get(name) for name in IDENTITY+BINDING+('administrative_state','vendor_state')}))
            if batch:thread=Thread(target=self.run_batch,args=(batch,),name='website-response',daemon=True);self.worker=thread
        if thread is not None:
            try:thread.start()
            except Exception:
                with self.lock:
                    self.worker=None
                    for key,row in batch:self.cache[key]=public(row,'unavailable','WEBSITE-UNAVAILABLE',now)

    def idle(self):
        with self.lock:return self.worker is None

    def close(self):
        with self.lock:self.closed=True;self.current.clear();self.cache.clear()
