"""LAN DNS through both tunnels at once (lua/dns_dual.lua, the same behaviour). Owner option, default OFF:
    uci set homensai_vpn.main.dns_dual='1'; uci commit homensai_vpn

GL 4.11 (firmware audit, /usr/bin/setup_instance): every VPN instance runs its own dnsmasq, `dhcp.<instance>` with
conf-dir /tmp/dnsmasq.d.<instance> holding `mark=<mark>` (wgclientN 0x1000.., port 2053+100N; ovpnclientN 0xa000..,
port 4053+100N). That mark is set on every upstream socket and `ip rule fwmark <mark>/0xf000 lookup <table>` sends it
into the tunnel; the table also has a blackhole, so a down tunnel never falls back to the WAN. The GL module dns_mark
(dns_mark.py) redirects LAN DNS to the instance of the ACTIVE tunnel. With a lossy or dead active tunnel every LAN
lookup waits for that one tunnel.

While Auto runs (the supervisor's verified pass, backend dns_mark_follow) each instance of the pair gets one snippet in
its own conf-dir:
    all-servers
    server=<upstream of the OTHER tunnel>@<other tunnel device>
dnsmasq then sends every upstream query through its own tunnel (the GL mark, unchanged) AND through the other tunnel,
and answers with the first reply. `@device` is SO_BINDTODEVICE: the kernel sends such a socket only through that device
(a missing route is "on link" via the device; a missing device fails the bind) - never via the WAN. Only `all-servers`
and `server=<IPv4>[#port]@<wgclientN|ovpnclientN>` lines are ever written.
  * the other tunnel's upstreams: the `server=` lines of its generated /var/etc/dnsmasq.conf.<instance> plus, unless
    `no-resolv`, the nameservers of its resolv-file (GL's own values, any provider). None now (tunnel down, file
    emptied): the servers this program installed last (no restart because a tunnel is down);
  * a changed snippet: written atomically, `dnsmasq --test` on the instance config, `/etc/init.d/dnsmasq restart
    <instance>`, procd must report it running; the active instance (the dns_mark mark) is restarted last. A failure
    restores the previous snippet (none: GL's own config), code DNS-DUAL-UNVERIFIED, and the same text is not retried
    by this process;
  * fewer than two GL instances recognised (other firmware, instance not running): nothing changes,
    code DNS-DUAL-UNAVAILABLE;
  * off(): option off, Auto stopped (backend unguard), package removal (prerm): every snippet is removed and its
    instance restarted - GL's own configuration again. /tmp is RAM: a reboot removes the snippets too.
"""
import json
import os
import re
import subprocess

FILE='homensai-dns-dual.conf'
CONF='/var/etc/dnsmasq.conf.'
CONFDIR='/tmp/dnsmasq.d.'
INIT='/etc/init.d/dnsmasq'
DNSMASQ='/usr/sbin/dnsmasq'
SETTINGS='/etc/config/homensai_vpn'
UNAVAILABLE='DNS-DUAL-UNAVAILABLE'
UNVERIFIED='DNS-DUAL-UNVERIFIED'
MAX_SERVERS=4
MAX_TEXT=16384
NAMES=['wgclient%d'%i for i in range(1,6)]+['ovpnclient%d'%i for i in range(1,6)]
HEADER='# HomenS.AI Auto VPN: LAN DNS through both tunnels (dns_dual). Generated; removed when Auto stops.'
MEMO={}  # instance -> snippet text whose install failed in this process (not retried until the text changes)

WS=' \t\n\r\f\v'
_ENABLED=re.compile(r"^[ \t\n\r\f\v]*option[ \t\n\r\f\v]+dns_dual[ \t\n\r\f\v]+'?1'?[ \t\n\r\f\v]*$")
_NAME=re.compile(r'(?:wgclient|ovpnclient)[1-5]')
_MARK=re.compile(r'0x[0-9a-f]{1,8}')
_NAMESERVER=re.compile(r'^[ \t\n\r\f\v]*nameserver[ \t\n\r\f\v]+([^ \t\n\r\f\v]+)[ \t\n\r\f\v]*$')
_RESOLV=re.compile(r'/tmp/[A-Za-z0-9._/-]+')
_SNIPPET=re.compile(r'server=([0-9.#]+)@([a-z0-9]+)')


def enabled(text):
    """Text of /etc/config/homensai_vpn: only an explicit `option dns_dual '1'` turns it on."""
    if not isinstance(text,str):return False
    return any(_ENABLED.match(line) for line in text.split('\n'))


def valid_name(name):return isinstance(name,str) and _NAME.fullmatch(name) is not None


def instance_of(mark):
    """'0x1000' -> 'wgclient1', '0xb000' -> 'ovpnclient2' (GL setup_instance: 0x1000+0x1000*(N-1), 0xa000+...)."""
    if not isinstance(mark,str) or _MARK.fullmatch(mark) is None:return None
    n=int(mark[2:],16)
    if n%4096:return None
    h=n//4096
    if 1<=h<=5:return 'wgclient%d'%h
    if 10<=h<=14:return 'ovpnclient%d'%(h-9)
    return None


def _octet(t):
    if re.fullmatch(r'[0-9]{1,3}',t) is None or (len(t)>1 and t[0]=='0'):return None
    n=int(t)
    return None if n>255 else n


def valid_server(entry):
    """'103.86.99.100' / '10.8.0.1#5353': a routable unicast IPv4 address, optional port; no names, no IPv6, no
    loopback/link-local/multicast (a local DNS proxy of the router cannot be reached through a tunnel)."""
    if not isinstance(entry,str) or len(entry)>21:return False
    match=re.fullmatch(r'([0-9.]+)#([0-9]+)',entry)
    ip,port=(match.group(1),match.group(2)) if match else (entry,None)
    parts=re.fullmatch(r'([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)',ip)
    if parts is None:return False
    a,b,c,d=(_octet(x) for x in parts.groups())
    if None in (a,b,c,d):return False
    if a==0 or a==127 or a>=224 or (a==169 and b==254):return False
    if port is not None:
        if len(port)>5 or port[0]=='0':return False
        if not 1<=int(port)<=65535:return False
    return True


def _safe_resolv(path):
    return isinstance(path,str) and len(path)<=128 and _RESOLV.fullmatch(path) is not None and '..' not in path


def servers_of(config,read):
    """The upstreams of an instance from its generated /var/etc/dnsmasq.conf.<instance> (`server=` lines, then the
    resolv-file nameservers unless `no-resolv`), valid ones only, each once, at most 4."""
    out=[]
    def add(s):
        if len(out)<MAX_SERVERS and valid_server(s) and s not in out:out.append(s)
    if not isinstance(config,str):return out
    noresolv,resolv=False,None
    for raw in config.split('\n'):
        line=raw.strip(WS)
        if line=='no-resolv':noresolv=True
        if line.startswith('server='):add(line[7:])
        if line.startswith('resolv-file='):resolv=line[12:]
    if not noresolv and _safe_resolv(resolv):
        try:text=read(resolv)
        except Exception:text=None
        if isinstance(text,str):
            for raw in text.split('\n'):
                match=_NAMESERVER.match(raw)
                if match:add(match.group(1))
    return out


def confdir_of(config):
    """The conf-dir of a generated instance config (without a ',*.conf' filter), or None."""
    if not isinstance(config,str):return None
    found=None
    for raw in config.split('\n'):
        line=raw.strip(WS)
        if line.startswith('conf-dir='):found=line[9:].split(',',1)[0]
    return found


def mark_matches(text,mark):
    """Text of <conf-dir>/mark is GL's `mark=0x1000` for exactly this mark."""
    if not isinstance(text,str) or not isinstance(mark,str) or _MARK.fullmatch(mark) is None:return False
    match=re.fullmatch(r'mark=0[xX]([0-9a-fA-F]{1,8})',text.strip(WS))
    return match is not None and int(match.group(1),16)==int(mark[2:],16)


def snippet(peers):
    """The conf-dir file for one instance; peers = [{'device','servers'}]; None when there is no server."""
    lines=[HEADER,'all-servers']
    for p in peers:
        for s in p['servers']:lines.append('server='+s+'@'+p['device'])
    if len(lines)==2:return None
    return '\n'.join(lines)+'\n'


def parse_snippet(text):
    """{device: [servers]}: what this program installed (the sticky servers of a down tunnel)."""
    out={}
    if not isinstance(text,str):return out
    for raw in text.split('\n'):
        match=_SNIPPET.fullmatch(raw.strip(WS))
        if match and valid_server(match.group(1)) and valid_name(match.group(2)):
            entries=out.setdefault(match.group(2),[])
            if match.group(1) not in entries and len(entries)<MAX_SERVERS:entries.append(match.group(1))
    return out


def marks_from_chains(chains,fields):
    """The marks of every TUNNEL<id>_ROUTE_POLICY jump of ROUTE_POLICY, in order."""
    out=[]
    if not isinstance(chains,dict) or not isinstance(chains.get('ROUTE_POLICY'),list):return out
    for tokens in chains['ROUTE_POLICY']:
        try:target=fields(tokens).get('-j')
        except Exception:continue
        if not isinstance(target,str) or re.fullmatch(r'TUNNEL[0-9]+_ROUTE_POLICY',target) is None:continue
        for rule in chains.get(target) or []:
            try:entry=fields(rule)
            except Exception:continue
            if entry.get('-j')=='MARK' and isinstance(entry.get('--set-xmark'),str):
                match=re.fullmatch(r'([0-9]+)/[0-9]+',entry['--set-xmark'])
                n=int(match.group(1)) if match else 0
                if 0<n<=0x7fffffff:
                    mark='0x%x'%n
                    if mark not in out:out.append(mark)
                break
    return out


# file and command access; tests pass read / write / remove / run
def _default_read(path):
    try:
        with open(path,'rb') as stream:data=stream.read(MAX_TEXT+1)
    except OSError:return None
    if len(data)>MAX_TEXT:return None
    try:return data.decode('utf8')
    except UnicodeError:return None


def _default_write(path,text):
    tmp=os.path.join(os.path.dirname(path),'.'+FILE+'.tmp')
    try:
        with open(tmp,'w',encoding='utf8') as stream:stream.write(text)
        os.rename(tmp,path)
    except OSError:
        try:os.unlink(tmp)
        except OSError:pass
        raise


def _default_remove(path):
    try:os.unlink(path)
    except FileNotFoundError:pass
    if os.path.lexists(path):raise OSError('dns_dual: remove')


def _default_run(argv,timeout):
    try:
        result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=timeout)
    except (OSError,subprocess.SubprocessError):return 255,''
    return result.returncode,result.stdout.decode('utf8','replace')


class _Access:
    def __init__(self,read=None,write=None,remove=None,run=None):
        self.read=read or _default_read;self.write=write or _default_write
        self.remove=remove or _default_remove;self.run_=run or _default_run
    def safe_read(self,path):
        try:text=self.read(path)
        except Exception:return None
        return text if isinstance(text,str) else None
    def run(self,argv,timeout):
        try:rc,out=self.run_(argv,timeout)
        except Exception:return 255,''
        return (rc if isinstance(rc,int) and not isinstance(rc,bool) else 255),(out if isinstance(out,str) else '')


def _running(io,name):
    """procd reports the instance running (`ubus call service list {"name":"dnsmasq"}`)."""
    rc,out=io.run(['ubus','call','service','list','{"name":"dnsmasq"}'],5)
    if rc!=0:return False
    try:value=json.loads(out)
    except ValueError:return False
    service=value.get('dnsmasq') if isinstance(value,dict) else None
    instances=service.get('instances') if isinstance(service,dict) else None
    instance=instances.get(name) if isinstance(instances,dict) else None
    return isinstance(instance,dict) and instance.get('running') is True


def _apply(io,x,want,result):
    """Bring one instance's snippet to `want` (None: none); x['current'] follows what is on disk."""
    if x['current']==want:return
    if want is not None and MEMO.get(x['name'])==want:
        result['code']=UNVERIFIED;return
    path=x['dir']+'/'+FILE
    previous=x['current']
    def put(text):
        if text is None:io.remove(path)
        else:io.write(path,text)
    try:put(want);ok=True
    except Exception:ok=False
    restarted=False
    if ok and want is not None:ok=io.run([DNSMASQ,'--test','-C',CONF+x['name']],10)[0]==0
    if ok:
        restarted=True
        # an installed snippet must come up running; a removal only restarts (the instance may be gone with the pair)
        ok=io.run([INIT,'restart',x['name']],30)[0]==0 and (want is None or _running(io,x['name']))
    if ok:
        x['current']=want;MEMO.pop(x['name'],None);result['changed']+=1
        return
    result['code']=UNVERIFIED
    if want is None:
        x['current']=io.safe_read(path);return
    # back to what the instance ran before (GL's own configuration when nothing was installed)
    MEMO[x['name']]=want
    try:put(previous)
    except Exception:pass
    if restarted:io.run([INIT,'restart',x['name']],30)
    x['current']=io.safe_read(path)


def _row(x,peers=None):
    return {'instance':x['name'],'mark':x.get('mark'),'installed':x['current'] is not None,'peers':peers or []}


def failed():
    """The result of a sync that could not run to its end (an unexpected error)."""
    return {'enabled':None,'code':UNVERIFIED,'changed':0,'instances':[]}


def sync(marks,active=None,read=None,write=None,remove=None,run=None):
    """Every recognised GL instance of the pair gets the other tunnels' upstreams. active: the mark LAN DNS uses now
    (dns_mark), restarted last."""
    io=_Access(read,write,remove,run)
    result={'enabled':True,'code':None,'changed':0,'instances':[]}
    usable,seen=[],set()
    for mark in marks if isinstance(marks,list) else []:
        name=instance_of(mark)
        if name and name not in seen:
            seen.add(name)
            directory=CONFDIR+name
            conf=io.safe_read(CONF+name)
            if confdir_of(conf)==directory and mark_matches(io.safe_read(directory+'/mark'),mark):
                usable.append({'name':name,'mark':mark,'conf':conf,'dir':directory,'current':io.safe_read(directory+'/'+FILE)})
    if len(usable)<2:
        result['code']=UNAVAILABLE;return result
    servers={}
    for p in usable:
        found=servers_of(p['conf'],io.safe_read)
        if not found:
            for x in usable:
                got=parse_snippet(x['current']).get(p['name']) if x is not p else None
                if got:found=got;break
        servers[p['name']]=found
    order=[x for x in usable if x['mark']!=active]+[x for x in usable if x['mark']==active]
    rows={}
    for x in order:
        peers=[{'device':p['name'],'servers':list(servers[p['name']])} for p in usable if p is not x and servers[p['name']]]
        _apply(io,x,snippet(peers),result)
        rows[x['name']]=_row(x,peers)
    result['instances']=[rows[x['name']] for x in usable]
    return result


def off(read=None,write=None,remove=None,run=None):
    """No snippet anywhere (option off, Auto stopped, package removal)."""
    io=_Access(read,write,remove,run)
    result={'enabled':False,'code':None,'changed':0,'instances':[]}
    MEMO.clear()  # the next start tries every text again
    for name in NAMES:
        directory=CONFDIR+name
        current=io.safe_read(directory+'/'+FILE)
        if current is not None:
            x={'name':name,'dir':directory,'current':current}
            _apply(io,x,None,result)
            result['instances'].append(_row(x))
    return result


def follow(chains,fields,active=None,settings=SETTINGS,read=None,write=None,remove=None,run=None):
    """The supervisor's verified pass. The owner option decides; off removes leftovers."""
    io=_Access(read,write,remove,run)
    if not enabled(io.safe_read(settings)):return off(read,write,remove,run)
    return sync(marks_from_chains(chains,fields),active,read,write,remove,run)


def summary(result):
    """One log line (DNS-DUAL-SYNC)."""
    rows=result.get('instances') if isinstance(result,dict) and isinstance(result.get('instances'),list) else []
    parts=[str(r.get('instance'))+('+' if r.get('installed') else '-') for r in rows]
    code=result.get('code') if isinstance(result,dict) else None
    return ('DNS-DUAL-SYNC: enabled %s changed %s code %s instances %s'
            %('true' if isinstance(result,dict) and result.get('enabled') is True else 'false',
              result.get('changed') if isinstance(result,dict) else None,code or 'none',','.join(parts) or 'none'))
