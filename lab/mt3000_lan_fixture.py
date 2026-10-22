"""Owned router-hosted LAN fixture. Not an external client or native certificate.

No effect on import. Hardware entry requires the source-bound stdin launcher,
the exact dedicated board, an independently armed guardian and explicit scope.
Windows/primary-router state is never touched. Runtime artifacts stay in /tmp.
"""
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time


class Refused(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise Refused(code)


def proc(pid):
    try:
        tail=Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()
        return dict(pid=pid,start=tail[19],pgid=int(tail[2]),state=tail[0])
    except (OSError,ValueError,IndexError):
        return None


def alive(record):
    current=proc(record['pid'])
    return bool(current and all(current[k]==record[k] for k in ('pid','start','pgid')) and current['state'] not in ('Z','X'))


def atomic(path,value):
    pending=path.with_suffix('.pending')
    fd=os.open(str(pending),os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(value,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
    os.replace(pending,path)


def command(args,timeout=3):
    result=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=timeout)
    require(len(result.stdout)<=65536,'FIXTURE-OUTPUT-LIMIT')
    require(result.returncode==0,'FIXTURE-COMMAND-FAILED')
    return result.stdout


def link(name):
    rows=json.loads(command(['ip','-j','link','show','dev',name]))
    require(isinstance(rows,list) and len(rows)==1,'FIXTURE-LINK-UNKNOWN')
    row=rows[0]
    return {k:row.get(k) for k in ('ifindex','ifname','address','master','link_index','link_netnsid')}


def fixture_plan(nonce,bridge,lan_address,pool,reserved,leased):
    require(isinstance(nonce,str) and re.fullmatch('[a-f0-9]{12}',nonce),'FIXTURE-NONCE')
    require(bridge.get('ifname')=='br-lan' and type(bridge.get('ifindex')) is int and bridge['ifindex']>0,'FIXTURE-BRIDGE')
    mac=bridge.get('address','')
    require(re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',mac) is not None and int(mac[:2],16)%2==0,'FIXTURE-BRIDGE-MAC')
    host_mac='fe:ff:ff:'+':'.join(nonce[i:i+2] for i in (0,2,4))
    peer_mac='fe:fe:ff:'+':'.join(nonce[i:i+2] for i in (6,8,10))
    require(mac<min(host_mac,peer_mac),'FIXTURE-BRIDGE-MAC-ORDER')
    require(lan_address=='192.168.11.1/24','FIXTURE-LAN-LAYOUT')
    require(type(pool) is tuple and len(pool)==2 and all(type(v) is int for v in pool),'FIXTURE-DHCP-UNKNOWN')
    require(0<=pool[0]<=254 and 1<=pool[1]<=255 and pool[0]+pool[1]<=256,'FIXTURE-DHCP-UNKNOWN')
    require(not pool[0]<=250<pool[0]+pool[1],'FIXTURE-IP-IN-DHCP-POOL')
    address='192.168.11.250'
    require(address not in reserved and address not in leased,'FIXTURE-IP-IN-USE')
    return dict(nonce=nonce,namespace='hvlan-'+nonce[:8],host='hvh'+nonce[:10],peer='hvn'+nonce[:10],
                host_mac=host_mac,peer_mac=peer_mac,address=address,prefix=24,gateway='192.168.11.1',bridge=bridge)


def arp_clear(address,bridge_mac):
    """RFC5227-style probe without assigning an address or changing LAN settings."""
    source=bytes.fromhex(bridge_mac.replace(':',''));target=socket.inet_aton(address)
    packet=b'\xff'*6+source+struct.pack('!H',0x806)+struct.pack('!HHBBH',1,0x800,6,4,1)+source+b'\0'*4+b'\0'*6+target
    with socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x806)) as sock:
        sock.bind(('br-lan',0));sock.settimeout(.2)
        end=time.monotonic()+1.2;next_send=0
        while time.monotonic()<end:
            if time.monotonic()>=next_send:
                sock.send(packet);next_send=time.monotonic()+.4
            try:data=sock.recv(2048)
            except socket.timeout:continue
            if len(data)>=42 and data[12:14]==b'\x08\x06' and data[22:28]!=source:
                require(data[28:32]!=target and not(data[28:32]==b'\0'*4 and data[38:42]==target),'FIXTURE-ARP-CONFLICT')


def preflight():
    require(os.geteuid()==0,'FIXTURE-ROOT-REQUIRED')
    require(Path('/tmp/sysinfo/board_name').read_text().strip()=='glinet,mt3000-snand','FIXTURE-BOARD')
    require(Path('/etc/glversion').read_text().strip()=='4.11.0','FIXTURE-FIRMWARE')
    bridge=link('br-lan')
    addresses=json.loads(command(['ip','-4','-j','addr','show','dev','br-lan']))
    values=[str(a.get('local'))+'/'+str(a.get('prefixlen')) for r in addresses for a in r.get('addr_info',[])]
    require(values==['192.168.11.1/24'],'FIXTURE-LAN-LAYOUT')
    script="local c=require('uci').cursor();local j=require('cjson');local r={};c:foreach('dhcp','host',function(s)if s.ip then r[#r+1]=s.ip end end);print(j.encode({start=c:get('dhcp','lan','start'),limit=c:get('dhcp','lan','limit'),reserved=r}))"
    dhcp=json.loads(command(['lua','-e',script]));pool=(int(dhcp['start']),int(dhcp['limit']))
    reserved=dhcp['reserved'];require(isinstance(reserved,(dict,list)),'FIXTURE-DHCP-UNKNOWN')
    leased=[]
    p=Path('/tmp/dhcp.leases')
    if p.exists():
        for line in p.read_text().splitlines():
            parts=line.split();require(len(parts)>=3,'FIXTURE-LEASE-UNKNOWN');leased.append(parts[2])
    plan=fixture_plan(secrets.token_hex(6),bridge,values[0],pool,reserved,leased)
    require(not json.loads(command(['ip','-j','neigh','show','to',plan['address'],'dev','br-lan'])),'FIXTURE-NEIGHBOR-PRESENT')
    arp_clear(plan['address'],bridge['address'])
    command(['ip','netns','list'])
    return plan


ACTIVE=Path('/tmp/homensai-lan-fixture-active.json')


def bridge_unchanged(plan):
    current=link('br-lan')
    require(all(current[k]==plan['bridge'][k] for k in ('ifindex','address')),'FIXTURE-MANAGEMENT-DRIFT')


def setup(work,plan):
    namespace=plan['namespace'];host=plan['host'];peer=plan['peer']
    require(not Path('/sys/class/net',host).exists() and not Path('/sys/class/net',peer).exists(),'FIXTURE-NAME-CONFLICT')
    require(not Path('/var/run/netns',namespace).exists(),'FIXTURE-NAMESPACE-CONFLICT')
    command(['ip','netns','add',namespace])
    plan['namespace_inode']=Path('/var/run/netns',namespace).stat().st_ino;atomic(work/'plan.json',plan)
    command(['ip','link','add',host,'address',plan['host_mac'],'type','veth','peer','name',peer,'address',plan['peer_mac']])
    plan['host_index']=link(host)['ifindex'];plan['peer_index']=link(peer)['ifindex'];atomic(work/'plan.json',plan)
    command(['ip','link','set',peer,'netns',namespace])
    command(['ip','link','set',host,'master','br-lan'])
    command(['ip','link','set',host,'up'])
    command(['ip','netns','exec',namespace,'ip','link','set','lo','up'])
    command(['ip','netns','exec',namespace,'ip','addr','add',plan['address']+'/24','dev',peer])
    command(['ip','netns','exec',namespace,'ip','link','set',peer,'up'])
    command(['ip','netns','exec',namespace,'ip','route','add','default','via',plan['gateway'],'dev',peer])
    bridge_unchanged(plan)
    command(['ip','netns','exec',namespace,'ping','-c','1','-W','2',plan['gateway']])
    atomic(work/'plan.json',plan)


def cleanup(work,plan):
    # Delete only an exact newly-created veth. Never use a prefix/process-name kill.
    host=Path('/sys/class/net',plan['host'])
    if host.exists():
        actual=link(plan['host'])
        require(actual['address']==plan['host_mac'] and actual['ifindex']==plan.get('host_index'),'FIXTURE-CLEANUP-LINK-IDENTITY')
        command(['ip','link','del','dev',plan['host']])
    path=Path('/var/run/netns',plan['namespace'])
    if path.exists():
        require(path.stat().st_ino==plan.get('namespace_inode'),'FIXTURE-CLEANUP-NAMESPACE-IDENTITY')
        end=time.monotonic()+8
        pids=command(['ip','netns','pids',plan['namespace']]).split()
        while pids and time.monotonic()<end:
            time.sleep(.2);pids=command(['ip','netns','pids',plan['namespace']]).split()
        require(not pids,'FIXTURE-CLIENT-STILL-RUNNING')
        command(['ip','netns','del',plan['namespace']])
    neighbors=json.loads(command(['ip','-j','neigh','show','to',plan['address'],'dev','br-lan']))
    if neighbors:
        require(len(neighbors)==1 and neighbors[0].get('lladdr')==plan['peer_mac'],'FIXTURE-NEIGHBOR-IDENTITY-CHANGED')
        command(['ip','neigh','del',plan['address'],'dev','br-lan'])
    bridge_unchanged(plan)
    require(not host.exists() and not path.exists(),'FIXTURE-CLEANUP-UNCONFIRMED')
    if ACTIVE.exists():
        active=json.loads(ACTIVE.read_text())
        if active.get('work')==str(work) and active.get('nonce')==plan['nonce']:ACTIVE.unlink()
    return dict(cleanup='PASS',bridge_mac_preserved=True,namespace_removed=True,veth_removed=True)


def guardian(work,nonce):
    metadata=work.lstat()
    require(work.parent==Path('/tmp') and work.name.startswith('homensai-lan-fixture-') and work.resolve()==work
            and stat.S_ISDIR(metadata.st_mode) and metadata.st_uid==0 and stat.S_IMODE(metadata.st_mode)==0o700,'FIXTURE-WORK-IDENTITY')
    manifest=json.loads((work/'manifest.json').read_text());require(manifest['nonce']==nonce,'FIXTURE-MANIFEST')
    require(manifest['boot']==Path('/proc/sys/kernel/random/boot_id').read_text(),'FIXTURE-BOOT')
    lock=os.open(str(work/'guardian.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=json.loads((work/'plan.json').read_text());ready=False;error=None
    try:
        require(not ACTIVE.exists(),'FIXTURE-ACTIVE-CONFLICT')
        setup(work,plan);record=dict(work=str(work),run_id=manifest['run_id'],nonce=nonce,guardian=proc(os.getpid()),owner=manifest['owner'],namespace=plan['namespace'],peer=plan['peer'],address=plan['address'],namespace_inode=plan['namespace_inode'],deadline=manifest['deadline'],scope='router-hosted-LAN-forwarding-not-external-client')
        atomic(ACTIVE,record);atomic(work/'ready.json',record);ready=True
        while time.monotonic()<manifest['deadline'] and alive(manifest['owner']) and not(work/'stop').exists():
            bridge_unchanged(plan);time.sleep(.5)
    except BaseException as exc:
        error=str(exc) if isinstance(exc,Refused) else 'FIXTURE-UNCONFIRMED'
    finally:
        try:result=cleanup(work,plan)
        except Exception as exc:result=dict(cleanup='HOLD',code=str(exc) if isinstance(exc,Refused) else 'FIXTURE-CLEANUP-UNCONFIRMED')
        result.update(ready=ready,reason=error or 'LEASE-OR-STOP-ENDED',scope='router-hosted-LAN-forwarding-not-external-client')
        atomic(work/'result.json',result);os.close(lock)


def parent(seconds):
    require(30<=seconds<=21600,'FIXTURE-DURATION')
    require(not ACTIVE.exists(),'FIXTURE-ACTIVE-CONFLICT')
    source=globals().get('_FIXTURE_SOURCE');require(isinstance(source,str) and len(source)<=65536,'FIXTURE-SOURCE-NOT-BOUND')
    run_id=globals().get('_FIXTURE_RUN_ID') or secrets.token_hex(16)
    require(isinstance(run_id,str) and re.fullmatch('[a-f0-9]{32}',run_id),'FIXTURE-RUN-IDENTITY')
    plan=preflight();work=Path(tempfile.mkdtemp(prefix='homensai-lan-fixture-',dir='/tmp'));work.chmod(0o700)
    script=work/'worker.py';script.write_text(source,encoding='utf8');script.chmod(0o600)
    atomic(work/'plan.json',plan)
    manifest=dict(nonce=plan['nonce'],run_id=run_id,owner=proc(os.getpid()),boot=Path('/proc/sys/kernel/random/boot_id').read_text(),deadline=time.monotonic()+seconds,source_sha256=hashlib.sha256(source.encode()).hexdigest())
    atomic(work/'manifest.json',manifest)
    child=subprocess.Popen([sys.executable,str(script),'--guardian',str(work),plan['nonce']],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True)
    end=time.monotonic()+8
    while time.monotonic()<end and not(work/'ready.json').exists() and not(work/'result.json').exists():time.sleep(.1)
    if(work/'ready.json').exists():print(json.dumps(dict(event='FIXTURE-READY',**json.loads((work/'ready.json').read_text()))),flush=True)
    else:(work/'stop').touch();raise Refused('FIXTURE-NOT-READY')
    try:
        while time.monotonic()<manifest['deadline'] and child.poll() is None and not(work/'stop').exists():time.sleep(.5)
    finally:(work/'stop').touch(mode=0o600,exist_ok=True)
    try:child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        owned=json.loads((work/'ready.json').read_text())['guardian']
        require(owned['pid']==child.pid and alive(owned),'FIXTURE-GUARDIAN-IDENTITY-CHANGED')
        os.kill(child.pid,signal.SIGTERM)
        try:child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            require(alive(owned),'FIXTURE-GUARDIAN-IDENTITY-CHANGED')
            os.kill(child.pid,signal.SIGKILL);child.wait(timeout=2)
    if not(work/'result.json').exists():
        # The independent guardian died. Only this still-live owning parent may
        # recover its persisted exact link/namespace identities, never broad names.
        require(not alive(json.loads((work/'ready.json').read_text())['guardian']),'FIXTURE-GUARDIAN-STILL-ALIVE')
        try:result=cleanup(work,json.loads((work/'plan.json').read_text()))
        except Exception as error:result=dict(cleanup='HOLD',code=str(error) if isinstance(error,Refused) else 'FIXTURE-PARENT-CLEANUP-UNCONFIRMED')
        result.update(parent_recovery=True,scope='router-hosted-LAN-forwarding-not-external-client');atomic(work/'result.json',result)
    result=json.loads((work/'result.json').read_text());print(json.dumps(dict(event='FIXTURE-RESULT',**result)),flush=True)
    return 0 if result['cleanup']=='PASS' else 2


if __name__=='__main__':
    try:
        if len(sys.argv)==2 and sys.argv[1]=='--preflight':print(json.dumps(preflight(),sort_keys=True));raise SystemExit(0)
        if len(sys.argv)==4 and sys.argv[1]=='--guardian':guardian(Path(sys.argv[2]),sys.argv[3]);raise SystemExit(0)
        if len(sys.argv)==3 and sys.argv[1]=='--hold':raise SystemExit(parent(int(sys.argv[2])))
        raise Refused('FIXTURE-EXPLICIT-SCOPE-REQUIRED')
    except Refused as error:
        print(json.dumps(dict(event='FIXTURE-REFUSED',code=str(error))),flush=True);raise SystemExit(2)
