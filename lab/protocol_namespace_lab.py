"""Isolated x86 OpenWrt protocol lab; no GL.iNet or host-network adapter.

Four real local tunnels and synthetic TLS/DNS endpoints. Keys remain in guest
RAM/tmp. A separate simple lab selector is NOT the application's native adapter.
"""
import sys as _boot_sys
_boot_sys.stderr.write('LABBOOT:PYTHON\n');_boot_sys.stderr.flush()
try:
 import faulthandler as _boot_trace
 _boot_trace.dump_traceback_later(20,repeat=False)
except ImportError:_boot_trace=None
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import random
import re
import secrets
import shlex
import shutil
import signal
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import uuid

print('LABBOOT:IMPORTS',file=sys.stderr,flush=True)
NETWORK_TIMEOUT=3  # Match agent.bound_socket; do not retry away failed samples.
VIP='203.0.113.10'
PROFILES=('wga','wgb','ova','ovb')
SCOPE='isolated x86 real protocol transport/selector; not GL.iNet native cascade acceptance'

def dns_reply(query):
    if len(query)<17 or struct.unpack('!H',query[4:6])[0]!=1:raise ValueError('DNS-QUESTION')
    offset=12
    while True:
        if offset>=len(query):raise ValueError('DNS-BOUNDS')
        size=query[offset];offset+=1
        if size==0:break
        if size>63 or offset+size>len(query):raise ValueError('DNS-LABEL')
        offset+=size
    if offset+4!=len(query) or query[offset:offset+4]!=b'\x00\x01\x00\x01':raise ValueError('DNS-TYPE')
    return query[:2]+b'\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00'+query[12:]+b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x1e\x00\x04'+socket.inet_aton(VIP)

def require_guest():
    text=Path('/etc/openwrt_release').read_text()
    if "DISTRIB_TARGET='x86/64'" not in text or "DISTRIB_RELEASE='21.02.7'" not in text or not Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file():
        raise RuntimeError('ISOLATED-X86-MARKER-REQUIRED')

def serve(args):
    import http.server
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            nonce=self.path.partition('?nonce=')[2]
            body=json.dumps({'profile':args.profile,'nonce':nonce}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*unused):pass
    class Server(http.server.ThreadingHTTPServer):
        address_family=socket.AF_INET6
        def server_bind(self):
            self.socket.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,0)
            super().server_bind()
    server=Server(('::',443),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(args.cert,args.key)
    server.socket=context.wrap_socket(server.socket,server_side=True)
    def dns():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.bind((VIP,53))
            while True:
                data,peer=sock.recvfrom(4096)
                try:sock.sendto(dns_reply(data),peer)
                except ValueError:pass
    threading.Thread(target=dns,daemon=True).start();Path(args.cert).parent.joinpath('ready-'+args.profile).write_text('TLS-DNS-ENDPOINT-READY');server.serve_forever()

def probe(args):
    def bound(kind):
        s=socket.socket(socket.AF_INET,kind);s.settimeout(args.timeout)
        if args.device:s.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,args.device.encode()+b'\0')
        if args.mark:s.setsockopt(socket.SOL_SOCKET,socket.SO_MARK,args.mark)
        return s
    print('LABPROBE:START',file=sys.stderr,flush=True)
    result={'dns':False,'https':False,'profile':None,'error':None,'phase':'DNS'};start=time.monotonic()
    try:
        tx=secrets.randbelow(65536);question=b'\x03vpn\x03lab\x04test\x00\x00\x01\x00\x01'
        query=struct.pack('!HHHHHH',tx,0x100,1,0,0,0)+question
        print('LABPROBE:DNS',file=sys.stderr,flush=True)
        with bound(socket.SOCK_DGRAM) as sock:
            sock.sendto(query,(VIP,53));reply,peer=sock.recvfrom(4096)
        if peer[0]!=VIP or reply!=dns_reply(query):raise ValueError('DNS-REPLY')
        result['dns']=True;nonce=uuid.uuid4().hex
        result['phase']='TCP';print('LABPROBE:TCP',file=sys.stderr,flush=True)
        with bound(socket.SOCK_STREAM) as raw:
            raw.connect((VIP,443))
            result['phase']='TLS';print('LABPROBE:TLS',file=sys.stderr,flush=True)
            with ssl.create_default_context(cafile=args.cert).wrap_socket(raw,server_hostname='vpn.lab.test') as tls:
                result['phase']='HTTP';print('LABPROBE:HTTP',file=sys.stderr,flush=True)
                tls.sendall(('GET /?nonce='+nonce+' HTTP/1.0\r\nHost: vpn.lab.test\r\n\r\n').encode());data=b''
                while len(data)<16384:
                    block=tls.recv(min(4096,16384-len(data)))
                    if not block:break
                    data+=block
        header,body=data.split(b'\r\n\r\n',1);row=json.loads(body)
        if b' 200 ' not in header.split(b'\r\n',1)[0] or row.get('nonce')!=nonce or row.get('profile') not in PROFILES:raise ValueError('HTTPS-IDENTITY')
        result.update(https=True,profile=row['profile'],phase='DONE')
    except (OSError,ValueError) as error:result['error']=('HTTPS-' if result['dns'] else 'DNS-')+type(error).__name__
    result['elapsed_ms']=round((time.monotonic()-start)*1000,2)
    print(json.dumps(result));return 0

class Lab:
    def __init__(self,root,duration):
        self.root=root;self.duration=duration;self.created=[];self.children=[];self.rows=[];self.counts={};self.cycles=0;self.started=time.monotonic();self.stop=False;self.root_unchanged=None;self.cleanup_confirmed=False
        self.source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();self.prefix='h7'+uuid.uuid4().hex[:5];self.client=self.prefix+'c';self.uplink=self.prefix+'u';self.names={p:self.prefix+str(i) for i,p in enumerate(PROFILES)}
        self.devices=dict(zip(PROFILES,('wg0','wg1','ovpn0','ovpn1')));self.tables={p:101+i for i,p in enumerate(PROFILES)}
        self.underlay={p:'10.254.77.'+str(v) for p,v in zip(PROFILES,(20,21,30,31))};self.ovpn={};self.selected=None
    def cmd(self,args,input=None,check=True,timeout=15):
        try:r=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
        except subprocess.TimeoutExpired as failure:
            detail=(failure.stderr or b'').decode(errors='replace')[-6000:]
            self.write('last-timeout.json',json.dumps({'command_prefix':args[:5] if args[:3]==['ip','netns','exec'] else args[:1],'timeout_seconds':timeout,'stderr':detail,'loadavg':Path('/proc/loadavg').read_text().strip() if Path('/proc/loadavg').exists() else None}))
            stage=re.findall(r'(?:LABPROBE|LABBOOT):([A-Z]+)',detail)
            raise RuntimeError('HELPER-PROCESS-DEADLINE:'+(stage[-1] if stage else 'UNCLASSIFIED'))
        if check and r.returncode:raise RuntimeError('LAB-COMMAND-FAILED:'+args[0]+':'+str(r.returncode)+':'+r.stderr.decode(errors='replace')[:180])
        return r
    def ns(self,name,args,**kw):return self.cmd(['ip','netns','exec',name]+args,**kw)
    def write(self,name,data):
        path=self.root/name;path.write_text(data);path.chmod(0o600);return str(path)
    def addns(self,name):
        self.cmd(['ip','netns','add',name]);self.created.append(name)
        self.cmd(['ip','-n',name,'link','set','lo','up'])
        for key in ('all','default'):self.ns(name,['sysctl','-w','net.ipv6.conf.'+key+'.disable_ipv6=0'])
    def process(self,name,args):
        log=(self.root/('process-'+str(len(self.children))+'.log')).open('ab')
        child=subprocess.Popen(['ip','netns','exec',name]+args,stdout=log,stderr=log,start_new_session=True);log.close();self.children.append(child);return child
    def snapshot(self):
        return hashlib.sha256(self.cmd(['ip','-4','route','show','table','all']).stdout+self.cmd(['ip','-4','rule','show']).stdout+self.cmd(['uci','export','network']).stdout+self.cmd(['uci','export','firewall']).stdout).hexdigest()
    def check(self,name,condition,detail=None):
        state='PASS' if condition else 'FAIL'
        if name.startswith('root-network-unchanged'):self.root_unchanged=bool(condition)
        self.counts[state]=self.counts.get(state,0)+1
        self.rows.append({'time':time.time(),'check':name,'result':state,'detail':detail if detail is not None else (getattr(self,'last_probe',None) if not condition else None)});self.rows=self.rows[-200:];self.status('RUNNING')
        if not condition:raise AssertionError(name)
    def status(self,state,error=None):
        row={'state':state,'scope':SCOPE,'elapsed_seconds':round(time.monotonic()-self.started,2),'duration_seconds':self.duration,'cycles':self.cycles,'counts':self.counts,'recent':self.rows,'error':error,'source_sha256':self.source_sha,'physical_router_access':False,'root_namespace_network_changed':None if self.root_unchanged is None else not self.root_unchanged,'cleanup_confirmed':self.cleanup_confirmed}
        path=self.root/'status.tmp';path.write_text(json.dumps(row,indent=2));os.replace(str(path),str(self.root/'status.json'))
    def route(self,profile):
        self.cmd(['ip','-n',self.client,'route','replace',VIP+'/32','dev',self.devices[profile]]);self.selected=profile
    def measure(self,profile=None,timeout=NETWORK_TIMEOUT):
        args=[sys.executable,__file__,'--mode','probe','--cert',str(self.root/'cert.pem'),'--timeout',str(timeout)]
        if profile:args+=['--device',self.devices[profile],'--mark',str(self.tables[profile])]
        result=self.ns(self.client,args,timeout=timeout*2+30)
        row=json.loads(result.stdout)
        self.last_probe={'expected_profile':profile or self.selected,'bound':bool(profile),'sample':row,'socket_timeout_seconds':timeout,'time':time.time()}
        path=self.root/'probe-observations.jsonl'
        if path.exists() and path.stat().st_size>4*1024*1024:raise RuntimeError('LAB-PROBE-LOG-BOUND')
        with path.open('a') as stream:stream.write(json.dumps(self.last_probe)+'\n')
        path.chmod(0o600)
        return row
    def wait(self,profile,seconds=30):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            r=self.measure(profile)
            if r['https'] and r['profile']==profile:return True
            time.sleep(.5)
        return False
    def nft(self,script):
        # OpenWrt /dev/stdin can be absent: use a private, bounded owned file.
        path=Path(self.write('rules-'+uuid.uuid4().hex+'.nft',script))
        try:
            self.ns(self.client,['nft','-c','-f',str(path)])
            self.ns(self.client,['nft','-f',str(path)])
        finally:path.unlink()
    def setup(self):
        self.baseline=self.snapshot();self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.cmd(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(self.root/'key.pem'),'-out',str(self.root/'cert.pem'),'-days','1','-subj','/CN=vpn.lab.test','-addext','subjectAltName=DNS:vpn.lab.test'],timeout=45)
        self.addns(self.uplink);self.cmd(['ip','-n',self.uplink,'link','add','br0','type','bridge']);self.cmd(['ip','-n',self.uplink,'link','set','br0','up'])
        for i,name in enumerate([self.client]+[self.names[p] for p in PROFILES]):
            self.addns(name);a=self.prefix+'a'+str(i);b=self.prefix+'b'+str(i)
            self.cmd(['ip','link','add',a,'type','veth','peer','name',b]);self.cmd(['ip','link','set',a,'netns',self.uplink]);self.cmd(['ip','link','set',b,'netns',name])
            self.cmd(['ip','-n',self.uplink,'link','set',a,'master','br0']);self.cmd(['ip','-n',self.uplink,'link','set',a,'up']);self.cmd(['ip','-n',name,'link','set',b,'name','underlay']);self.cmd(['ip','-n',name,'link','set','underlay','up'])
            address='10.254.77.10' if i==0 else self.underlay[PROFILES[i-1]]
            self.cmd(['ip','-n',name,'addr','add',address+'/24','dev','underlay']);self.cmd(['ip','-n',name,'-6','addr','add','fd77::'+str(10+i)+'/64','dev','underlay'])
        for i,p in enumerate(PROFILES):
            server=self.names[p];dev=self.devices[p];subnet='10.253.'+str(i+1)+'.'
            self.cmd(['ip','-n',server,'addr','add',VIP+'/32','dev','lo'])
            if p.startswith('wg'):
                ckey=self.cmd(['wg','genkey']).stdout;skey=self.cmd(['wg','genkey']).stdout
                cpub=self.cmd(['wg','pubkey'],input=ckey).stdout.strip().decode();spub=self.cmd(['wg','pubkey'],input=skey).stdout.strip().decode()
                cpath=self.write(p+'-client.key',ckey.decode());spath=self.write(p+'-server.key',skey.decode())
                for nsname in (self.client,server):self.cmd(['ip','-n',nsname,'link','add',dev,'type','wireguard'])
                self.ns(self.client,['wg','set',dev,'private-key',cpath,'listen-port',str(51820+i),'peer',spub,'allowed-ips',VIP+'/32','endpoint',self.underlay[p]+':51820','persistent-keepalive','1'])
                self.ns(server,['wg','set',dev,'private-key',spath,'listen-port','51820','peer',cpub,'allowed-ips',subnet+'2/32'])
                for nsname,last in ((self.client,'2'),(server,'1')):
                    self.cmd(['ip','-n',nsname,'addr','add',subnet+last+'/30','dev',dev]);self.cmd(['ip','-n',nsname,'link','set',dev,'up'])
            else:
                key=str(self.root/(p+'.secret'));self.cmd(['openvpn','--genkey','secret',key])
                shared=['openvpn','--dev',dev,'--dev-type','tun','--proto','udp','--secret',key,'--cipher','AES-256-CBC','--auth','SHA256','--ping','1','--ping-restart','8','--persist-tun','--persist-key','--verb','1']
                self.ovpn[p]=(shared+['--local',self.underlay[p],'--port','1194','--ifconfig',subnet+'1',subnet+'2'],None)
                server_child=self.process(server,self.ovpn[p][0]);self.ovpn[p]=(self.ovpn[p][0],server_child)
                self.process(self.client,shared+['--local','10.254.77.10','--lport',str(1200+i),'--remote',self.underlay[p],'1194','--ifconfig',subnet+'2',subnet+'1'])
                end=time.monotonic()+20
                while time.monotonic()<end:
                    if self.cmd(['ip','-n',self.client,'link','show',dev],check=False).returncode==0:break
                    time.sleep(.3)
                else:raise RuntimeError('OPENVPN-TUN-NOT-READY')
            self.cmd(['ip','-n',self.client,'rule','add','priority',str(100+i),'fwmark',str(self.tables[p]),'lookup',str(self.tables[p])])
            self.cmd(['ip','-n',self.client,'route','replace','table',str(self.tables[p]),VIP+'/32','dev',dev])
            self.process(server,[sys.executable,__file__,'--mode','serve','--profile',p,'--cert',str(self.root/'cert.pem'),'--key',str(self.root/'key.pem')])
        # Slow emulator endpoint bootstrap is separate from real network-health deadlines.
        until=time.monotonic()+60
        while not all((self.root/('ready-'+p)).is_file() for p in PROFILES):
            if time.monotonic()>until:raise RuntimeError('LAB-ENDPOINT-BOOTSTRAP-DEADLINE')
            time.sleep(.2)
        self.route('wga')
        for p in PROFILES:self.check('real-'+p+'-bound-DNS-TLS-ready',self.wait(p))
        self.nft('table inet hs_lab_guard { chain lab_output { type filter hook output priority -300; policy accept; meta nfproto ipv6 counter drop; ip daddr '+VIP+' oifname != { "wg0", "wg1", "ovpn0", "ovpn1" } counter drop; }; chain track_output { type filter hook output priority 0; policy accept; ct state { new, established, related } counter; }; }\n')
        self.check('root-network-unchanged-after-setup',self.snapshot()==self.baseline)
    def faults(self):
        self.route('wga');self.check('selected-wga',self.measure()['profile']=='wga')
        self.cmd(['ip','-n',self.names['wga'],'link','set','wg0','down'])
        try:
            self.check('failed-primary-DNS-TLS-refused',not self.measure('wga')['https'])
            self.check('same-protocol-reserve-healthy',self.measure('wgb')['profile']=='wgb');self.route('wgb');self.check('same-protocol-route-switch',self.measure()['profile']=='wgb')
            self.route('ova');self.check('cross-protocol-route-switch',self.measure()['profile']=='ova')
        finally:self.cmd(['ip','-n',self.names['wga'],'link','set','wg0','up'])
        self.check('restored-primary-bound-healthy',self.wait('wga'));self.route('wga');self.check('actual-return-and-rollback',self.measure()['profile']=='wga')
        self.nft('table inet hs_lab_fault { chain lab_output { type filter hook output priority -310; policy accept; ip daddr '+VIP+' udp dport 53 oifname "wg0" drop; }; }\n')
        try:
            failed=self.measure('wga');self.check('DNS-failure-distinct',not failed['dns'] and failed['error'].startswith('DNS-'))
            self.check('DNS-fault-reserve-unaffected',self.measure('ovb')['https'])
        finally:self.ns(self.client,['nft','delete','table','inet','hs_lab_fault'])
        self.cmd(['ip','-n',self.client,'route','replace',VIP+'/32','via',self.underlay['wga'],'dev','underlay'])
        try:self.check('kill-switch-blocks-direct-underlay',not self.measure()['https'])
        finally:self.route('wga')
        conn=self.ns(self.client,['conntrack','-L','-p','tcp','--dport','443'],check=False)
        self.check('real-conntrack-TCP-observed',conn.returncode==0 and b'tcp ' in conn.stdout)
        self.ns(self.client,['conntrack','-D','-p','tcp','-s','10.253.1.2','-d',VIP,'--dport','443'],check=False)
        udp=self.ns(self.client,['conntrack','-L','-p','udp'],check=False)
        self.check('scoped-TCP-cleanup-keeps-UDP',udp.returncode==0 and b'udp ' in udp.stdout)
        for p in PROFILES:
            self.route(p);self.check('selection-'+p,self.measure()['profile']==p)
        self.route('wga');self.check('root-network-unchanged-after-faults',self.snapshot()==self.baseline)
    def soak(self):
        rng=random.Random(20261016);end=self.started+self.duration
        while time.monotonic()<end and not self.stop and not (self.root/'STOP').exists():
            if self.cycles and self.cycles%25==0:self.faults()
            p=rng.choice(PROFILES);self.route(p);self.check('soak-selected-'+p,self.measure()['profile']==p)
            standby=rng.choice([x for x in PROFILES if x!=p]);self.check('soak-parallel-reserve-'+standby,self.measure(standby)['profile']==standby)
            self.cycles+=1;self.status('RUNNING')
            time.sleep(min(5,max(0,end-time.monotonic())))
    def cleanup(self):
        for child in self.children:
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        for child in self.children:
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
        for name in reversed(self.created):self.cmd(['ip','netns','delete',name],check=False)
        for p in self.root.glob('*.key'):p.unlink()
        for p in self.root.glob('*.secret'):p.unlink()
        if (self.root/'key.pem').exists():(self.root/'key.pem').unlink()
        remaining=self.cmd(['ip','netns','list']).stdout.decode()
        if any(name in remaining.split() for name in self.created):raise RuntimeError('LAB-NAMESPACE-CLEANUP-UNVERIFIED')
        if any(child.poll() is None for child in self.children):raise RuntimeError('LAB-PROCESS-CLEANUP-UNVERIFIED')
        self.cleanup_confirmed=True
    def run(self):
        state='FAIL';error=None
        try:self.setup();self.faults();self.soak();state='STOPPED' if self.stop or (self.root/'STOP').exists() else 'PASS'
        except Exception as failure:error=type(failure).__name__+':'+str(failure)[:120]
        finally:
            try:self.cleanup()
            except Exception as failure:state='FAIL';error='CLEANUP-'+type(failure).__name__
            if hasattr(self,'baseline'):
                self.root_unchanged=self.snapshot()==self.baseline
                if not self.root_unchanged:state='FAIL';error='ROOT-NETWORK-CHANGED'
            self.status(state,error)
        print(json.dumps({'state':state,'error':error,'counts':self.counts,'cycles':self.cycles,'scope':SCOPE}));return 0 if state=='PASS' else 1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=('run','serve','probe'),default='run');parser.add_argument('--profile');parser.add_argument('--cert');parser.add_argument('--key');parser.add_argument('--device');parser.add_argument('--mark',type=int,default=0);parser.add_argument('--timeout',type=float,default=NETWORK_TIMEOUT);parser.add_argument('--duration',type=int,default=0);parser.add_argument('--root',default='/tmp/homensai-protocol-lab')
    args=parser.parse_args();print('LABBOOT:ARGS',file=sys.stderr,flush=True);
    if _boot_trace:_boot_trace.cancel_dump_traceback_later()
    require_guest();os.umask(0o077)
    if args.mode=='serve':serve(args);return 0
    if args.mode=='probe':return probe(args)
    if not 0<=args.duration<=10800 or not re.fullmatch('/tmp/homensai-protocol-lab(?:-[a-z0-9]+)?',args.root):raise ValueError('LAB-BOUNDS')
    root=Path(args.root)
    if root.exists():raise ValueError('LAB-DIRECTORY-EXISTS')
    lab=Lab(root,args.duration)
    signal.signal(signal.SIGTERM,lambda *unused:setattr(lab,'stop',True));signal.signal(signal.SIGINT,lambda *unused:setattr(lab,'stop',True))
    return lab.run()
if __name__=='__main__':raise SystemExit(main())
