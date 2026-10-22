"""Ordinary unmarked client sockets in the owned netns; no activation/certificate."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import struct
import subprocess
import sys
import time


def require(value):
    if not value:raise ValueError('HOSTED-CLIENT-UNCONFIRMED')


def trace_address(body):
    require(isinstance(body,bytes) and len(body)<=32768)
    rows=body.decode('ascii').splitlines()
    values=[row[3:].strip() for row in rows if row.startswith('ip=')]
    require(len(values)==1 and any(row.startswith('http=') for row in rows))
    value=ipaddress.IPv4Address(values[0]);require(value.is_global)
    return str(value)


def valid_dns(raw,token,question):
    if not 12+len(question)<=len(raw)<=4096:return False
    got,flags,qd,an,_,_=struct.unpack('!2sHHHHH',raw[:12])
    if not(got==token and flags&0x8000 and not flags&0x7a0f and qd==1 and 0<an<=64 and raw[12:12+len(question)]==question):return False
    offset=12+len(question);found=False
    try:
        for _ in range(an):
            for _ in range(128):
                size=raw[offset]
                if size==0:offset+=1;break
                if size&0xc0==0xc0:
                    target=((size&0x3f)<<8)|raw[offset+1]
                    if target>=offset:return False
                    offset+=2;break
                if size&0xc0 or offset+size+1>=len(raw):return False
                offset+=size+1
            else:return False
            typ,cls,ttl,size=struct.unpack('!HHIH',raw[offset:offset+10]);offset+=10
            if offset+size>len(raw):return False
            found=found or (typ==1 and cls==1 and size==4);offset+=size
    except (IndexError,struct.error):return False
    return found


def topology(request):
    require(set(request)=={'nonce','namespace_inode','root_namespace_inode','interface','source','gateway','peer_mac'})
    require(type(request['nonce']) is str and re.fullmatch('[a-f0-9]{12}',request['nonce']))
    require(type(request['namespace_inode']) is int and request['namespace_inode']>0 and request['namespace_inode']!=request['root_namespace_inode'])
    require(type(request['root_namespace_inode']) is int and request['root_namespace_inode']==Path('/proc/1/ns/net').stat().st_ino)
    require(Path('/proc/self/ns/net').stat().st_ino==request['namespace_inode'])
    active=json.loads(Path('/tmp/homensai-lan-fixture-active.json').read_text())
    require(active['nonce']==request['nonce'] and active['namespace_inode']==request['namespace_inode'] and time.monotonic()<active['deadline'])
    require(request['interface']=='hvn'+request['nonce'][:10] and request['source']=='192.168.11.250' and request['gateway']=='192.168.11.1')
    interface=request['interface'];index=socket.if_nametoindex(interface);require(index>0)
    rows=json.loads(subprocess.check_output(['ip','-j','link','show','dev',interface],stderr=subprocess.DEVNULL,timeout=2))
    require(len(rows)==1 and rows[0]['ifindex']==index and rows[0]['address']==request['peer_mac'])
    routes=json.loads(subprocess.check_output(['ip','-4','-j','route','get','1.1.1.1'],stderr=subprocess.DEVNULL,timeout=2))
    require(len(routes)==1 and routes[0].get('dev')==interface and routes[0].get('gateway')==request['gateway']
            and routes[0].get('prefsrc',routes[0].get('src'))==request['source'])
    return index


def measure(request):
    result=dict(performed=False,scope='router-hosted-LAN-forwarding',external_lan_verified=False,
                native_certificate=False,router_hosted_forwarding_verified=False)
    try:
        index=topology(request);started=time.monotonic();end=started+6
        sys.path.insert(0,'/usr/lib/homensai-vpn')
        from probe_deadline import remaining,DeadlineSocket
        def bound(udp=False):
            s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM if udp else socket.SOCK_STREAM)
            try:
                s.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),request['interface'].encode()+b'\0')
                s.bind((request['source'],0));require(s.getsockopt(socket.SOL_SOCKET,36)==0)
                s.settimeout(remaining(end));return s
            except BaseException:s.close();raise
        def dns():
            token=os.urandom(2);question=b'\x07example\x03com\0'+struct.pack('!HH',1,1)
            packet=struct.pack('!2sHHHHH',token,0x100,1,0,0,0)+question
            with bound(True) as s:
                s.connect((request['gateway'],53));s.send(packet);raw=s.recv(4096)
                require(s.getsockname()[0]==request['source']);return valid_dns(raw,token,question)
        def https(address):
            raw=bound()
            try:
                raw.connect((address,443));raw.settimeout(remaining(end))
                with ssl.create_default_context().wrap_socket(raw,server_hostname='one.one.one.one') as s:
                    require(s.getsockname()[0]==request['source']);s.settimeout(remaining(end))
                    s.sendall(b'GET /cdn-cgi/trace HTTP/1.1\r\nHost: one.one.one.one\r\nConnection: close\r\n\r\n')
                    response=http.client.HTTPResponse(DeadlineSocket(s,end));response.begin();body=response.read(32769);remaining(end)
                    require(response.status==200);return trace_address(body)
            finally:raw.close()
        results={};errors={}
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs={'dns':pool.submit(dns),'https1':pool.submit(https,'1.1.1.1'),'https2':pool.submit(https,'1.0.0.1')}
            for key,job in jobs.items():
                try:results[key]=job.result()
                except Exception as error:results[key]=None;errors[key]={'type':type(error).__name__,'errno':getattr(error,'errno',None)}
        ended=time.monotonic();require(ended<end and topology(request)==index)
        passed=results['dns'] is True and results['https1'] and results['https1']==results['https2']
        result.update(performed=True,dns_ok=results['dns'] is True,https_success=sum(bool(results[k])for k in ('https1','https2')),
                      router_hosted_forwarding_verified=bool(passed),errors=errors,started=started,ended=ended,
                      namespace_inode=request['namespace_inode'],ifindex=index,nonce=request['nonce'])
        if passed:
            result['exit_sha256']=hashlib.sha256(results['https1'].encode()).hexdigest()
    except Exception as error:
        result['code']='HOSTED-CLIENT-UNCONFIRMED';result['error_type']=type(error).__name__
    return result


if __name__=='__main__':
    value=measure(globals().get('_PROBE_REQUEST',{}));print(json.dumps(value,sort_keys=True));raise SystemExit(0 if value.get('performed') else 2)
