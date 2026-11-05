# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""The best server inside a channel (2.1.0, docs/architecture/SERVER-PICK-DESIGN-2026-11-02.ru.md).

Python counterpart of lua/server_pick.lua - the same reading, ranking, file order, switch steps and published block
(shared cases: router/tests/server_pick_cases.json). Pure logic over an injected `io`; the monitor runs job() off its
loop (agent.py: a thread, Lua: a child process) at most every MEASURE_EVERY seconds and right after a channel failure.

GL firmware facts (MT3000, GL 4.x, read 02.11.2026): every VPN tunnel is a route_policy rule (tunnel_id, via_type, via,
group_id, peer_id | client_id, profiles='/etc/vpn_profiles.d/profile<tunnel_id>'). The profiles file holds one candidate
per line, `[proto:]<group>_<id>`. /usr/bin/tunnel-switch.sh takes the NEXT line after the current one, round robin,
without looking at ping. So:
  * measure  OpenVPN: TCP connect time to the first reachable `remote` (ICMP is closed on some servers);
             WireGuard: busybox ping of `end_point` (a name may move to another machine; ping resolves it);
             from the router itself through the WAN, without raising a tunnel. Not LAN traffic: no leak rule applies;
  * order    the best live server is put right after the current line, so the firmware's own round robin takes it
             next (no switch of ours); written atomically and only when the text changes;
  * switch   an IDLE (not carrying) failed tunnel gets the best server the way tunnel-switch.sh does it (uci + ifdown/
             ifup of that interface only). Refused while the tunnel carries traffic, while the firmware's own switch
             holds its lock, with Auto off or with the owner switch `server_pick` off (default off until the router
             check). Hysteresis: a working server is replaced only by one >= 20 % faster; <= CHANGES per hour per tunnel.
  * stage 2  (MT3000 02.11.2026: a change made outside the pair cost the working channel a 7 s LAN stall and a pair
             readopt) the job never switches itself any more: it writes the hand-off CHANGE and the Auto supervisor
             (pair_auto.server_* / lua/pair.lua) changes the idle reserve inside its own lock, re-binds its session
             (rebind()), waits for the tunnel (CONNECT_WAIT), verifies it through the tunnel and rolls back on failure.
  * stage 3  the same for the FAILED PRIMARY while the traffic is on the reserve after an automatic switch (journal
             COMMITTED): rebind(role='source') re-binds the open journal too, so the normal return brings the traffic
             back to the primary on its new server; WireGuard mirrors GL's update_provider_config (PROVIDER_SCRIPT).
Every measurement and switch is gated by the owner switch; with it off the block lists the candidates only.
"""
import json
import math
import re

PICKED='SERVER-PICKED'
FAILED='SERVER-PICK-FAILED'
WAITING='SERVER-PICK-WAITING-VENDOR'
LIMIT='SERVER-PICK-LIMIT'
CARRYING='SERVER-PICK-CARRYING'
OFF='SERVER-PICK-OFF'
REQUESTED='SERVER-PICK-REQUESTED'
DEFERRED='SERVER-PICK-DEFERRED'
CHANGING='SERVER-CHANGING'  # the Auto status reason while its own server change waits for the tunnel (stage 2)
CODES=(PICKED,FAILED,WAITING,LIMIT,CARRYING,OFF,REQUESTED,DEFERRED)
EVENT_CODES=(PICKED,FAILED,WAITING,LIMIT)
MEASURE_EVERY=600
RETRY_CARRYING=20  # s between rounds while a failed channel still carries the traffic
CHANGES=4
WINDOW=3600
TCP_TIMEOUT=1.5
TCP_ATTEMPTS=4
TCP_SAMPLES=3
PING=['ping','-c','3','-W','1','-w','5']
PING_SECONDS=8
EXEC_SECONDS=20
MAX_TUNNELS=8
MAX_CANDIDATES=32
MAX_MEASURED=12
MAX_ENDPOINTS=8
MAX_TEXT=262144
RESULT='server-pick.json'
STATE='server-pick-state.json'
CHANGE='server-pick-change.json'  # the monitor job's hand-off to the Auto supervisor (stage 2)
EVENT='server-pick-event.json'    # the supervisor's last outcome, read by both monitors as history events
REQUEST_AGE=900
CONNECT_WAIT=60
SETTLE_WAIT=90
LOCKS=('/var/run/tunnel-switch-tid-%d.lock','/var/run/tunnel-switch-network-switch.lock')
TEXT={PICKED:'server of the channel changed',FAILED:'server change of the channel failed',
      WAITING:'the firmware is switching this channel itself; waiting',LIMIT:'server change limit reached (4 per hour)',
      CARRYING:'the channel carries traffic; its server is never changed',OFF:'server pick is off',
      REQUESTED:'server change handed to Auto',DEFERRED:'Auto is not ready for a server change; waiting'}

_CONFIG=re.compile(r'[a-z_]{1,32}')
_SECTION=re.compile(r'[A-Za-z0-9_@\[\]-]{1,64}')
_OPTION=re.compile(r'[A-Za-z0-9_]{1,64}')
_NAME=re.compile(r'[A-Za-z0-9_]{1,32}')
_DIGITS=re.compile(r'[0-9]{1,9}')
_LINE=re.compile(r'(?:([a-z]{1,16}):)?([0-9]{1,9})_([0-9]{1,9})')
_PROFILES=re.compile(r'/etc/vpn_profiles\.d/profile[0-9]{1,9}')
_IFACE={'openvpn':re.compile(r'ovpnclient[0-9]{1,4}'),'wireguard':re.compile(r'wgclient[0-9]{1,4}')}
_HOST=re.compile(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}')
_ENDPOINT=re.compile(r'([A-Za-z0-9][A-Za-z0-9.-]{0,252})[: ]([0-9]{1,5})')
_HOSTNAME=re.compile(r'(?=.{3,253}$)[A-Za-z0-9][A-Za-z0-9-]{0,62}(\.[A-Za-z0-9][A-Za-z0-9-]{0,62}){1,6}')
_LOCATION=re.compile(r'[^\x00-\x1f\x7f\ufffd]+')
_PING_HEAD=re.compile(r'PING [^ ]+ \(([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\)')
_PING_RTT=re.compile(r'= ([0-9]{1,6}(?:\.[0-9]{1,6})?)/([0-9]{1,6}(?:\.[0-9]{1,6})?)/')
_MARK=re.compile(r'0[xX]([0-9a-fA-F]{1,8})')


def location(value):
    """A shown server location: printable, at most 64 bytes of UTF-8 (the same byte rule in Lua), else None."""
    return value if isinstance(value,str) and _LOCATION.fullmatch(value) and len(value.encode('utf-8'))<=64 else None


def digits(value):return value if isinstance(value,str) and _DIGITS.fullmatch(value) else None


def whole_ms(value):
    """Milliseconds as a whole number (the same rounding in Lua), None when not a sane reading."""
    if isinstance(value,bool) or not isinstance(value,(int,float)) or value!=value or not 0<=value<=60000:return None
    return int(math.floor(value+0.5))


def uci_values(raw):
    """The value part of a `uci show` line -> list of strings ('a' 'b', 'it'\\''s', bare words), None when broken."""
    out=[];token=None;i=0;n=len(raw)
    while i<n:
        c=raw[i]
        if c=="'":
            end=raw.find("'",i+1)
            if end<0:return None
            token=(token or '')+raw[i+1:end];i=end+1
        elif raw[i:i+2]=="\\'":token=(token or '')+"'";i+=2
        elif c in ' \t':
            if token is not None:out.append(token);token=None
            i+=1
        else:token=(token or '')+c;i+=1
    if token is not None:out.append(token)
    return out


def parse_uci(text):
    """`uci show` text (several configs) -> {config: {section: {'.type': type, option: str | [str]}}}."""
    out={}
    if not isinstance(text,str) or len(text)>MAX_TEXT:return out
    for line in text.split('\n'):
        key,eq,raw=line.partition('=')
        if not eq:continue
        parts=key.split('.')
        if not 2<=len(parts)<=3 or not _CONFIG.fullmatch(parts[0]) or not _SECTION.fullmatch(parts[1]):continue
        values=uci_values(raw)
        if not values:continue
        section=out.setdefault(parts[0],{}).setdefault(parts[1],{})
        if len(parts)==2:section['.type']=values[0]
        elif _OPTION.fullmatch(parts[2]):section[parts[2]]=values[0] if len(values)==1 else values
    return out


def parse_mark(value):
    match=_MARK.fullmatch(value) if isinstance(value,str) else None
    return int(match.group(1),16) if match else None


def tunnels(uci):
    """route_policy rules with a tunnel id, a protocol and a profiles file, by tunnel id."""
    rows=[]
    for name,s in (uci.get('route_policy') or {}).items():
        protocol=s.get('via_type');tunnel=digits(s.get('tunnel_id'));path=s.get('profiles')
        if protocol not in _IFACE or tunnel is None or not isinstance(path,str) or not _PROFILES.fullmatch(path):continue
        via=s.get('via')
        rows.append({'section':name,'tunnel_id':int(tunnel),'protocol':protocol,
                     'interface':via if isinstance(via,str) and _IFACE[protocol].fullmatch(via) else None,
                     'group_id':digits(s.get('group_id')),'current_id':digits(s.get('client_id' if protocol=='openvpn' else 'peer_id')),
                     'profiles':path,'mark':parse_mark(s.get('mark'))})
    rows.sort(key=lambda row:(row['tunnel_id'],row['section']))
    return rows[:MAX_TUNNELS]


def parse_profiles(text):
    """Candidate lines of a profiles file -> [{'profile','group_id','profile_id'}]; blank, # and foreign lines skipped."""
    out=[];seen=set()
    if not isinstance(text,str) or len(text)>MAX_TEXT:return out
    for line in text.split('\n'):
        s=line.strip(' \t\r')
        match=_LINE.fullmatch(s)
        if not match or s in seen:continue
        seen.add(s);out.append({'profile':s,'group_id':match.group(2),'profile_id':match.group(3)})
        if len(out)>=MAX_CANDIDATES:break
    return out


def endpoints(protocol,section):
    raw=section.get('remote' if protocol=='openvpn' else 'end_point') if isinstance(section,dict) else None
    out=[]
    for value in ([raw] if isinstance(raw,str) else raw if isinstance(raw,list) else []):
        match=_ENDPOINT.fullmatch(value) if isinstance(value,str) else None
        if match and 1<=int(match.group(2))<=65535 and len(out)<MAX_ENDPOINTS:out.append({'host':match.group(1),'port':int(match.group(2))})
    # Provider peers (NordVPN via GL) keep no end_point in uci; their name is the server host name (MT3000, 02.11.2026).
    name=section.get('name') if isinstance(section,dict) and protocol=='wireguard' and not out else None
    if isinstance(name,str) and _HOSTNAME.fullmatch(name):out.append({'host':name,'port':51820})
    return out


def _filled(value):
    return isinstance(value,str) and value.strip(' \t')!='' or isinstance(value,list) and any(_filled(x) for x in value)


def switchable(protocol,section,uci):
    """A candidate this supervisor may change to. OpenVPN: yes (its client section is the whole config). WireGuard: only
    a peer whose uci holds what GL's netifd wgclient.sh builds the tunnel from: a host:port end_point, the public key
    and allowed_ips on the peer, the private key and an address on the peer or its group_<group_id> (the fallback
    wgclient.sh reads). MT3000 02.11.2026: NordVPN peer_2000 held metadata only (GL's gen_nordvpn_peer_config writes
    just name/host_id/location); GL's update_provider_config fills such a peer from api.nordvpn.com at switch time
    (firmware audit: update_nordvpn_config -> set_nord_peer_config when private_key is empty), but that needs the
    provider API and a token at that moment and its result is not reported - so such a peer is measured (its name is
    the server host) and shown, never handed over as the best."""
    if protocol=='openvpn':return True
    if not isinstance(section,dict):return False
    raw=section.get('end_point')
    if not any(isinstance(v,str) and _ENDPOINT.fullmatch(v) and 1<=int(_ENDPOINT.fullmatch(v).group(2))<=65535
               for v in ([raw] if isinstance(raw,str) else raw if isinstance(raw,list) else [])):return False
    gid=digits(section.get('group_id'))
    group=(uci.get('wireguard') or {}).get('group_'+gid) if gid and isinstance(uci,dict) else None
    group=group if isinstance(group,dict) else {}
    def either(key):return _filled(section.get(key)) or _filled(group.get(key))
    return (_filled(section.get('public_key')) and _filled(section.get('allowed_ips')) and either('private_key')
            and (either('address_v4') or either('address_v6')))


def candidates(tunnel,profiles_text,uci):
    """The tunnel's candidates with their server data: profile, config name, location, endpoints, current, switchable."""
    rows=[]
    for entry in parse_profiles(profiles_text):
        if tunnel['protocol']=='openvpn':
            config=entry['group_id']+'_'+entry['profile_id'];section=(uci.get('ovpnclient') or {}).get(config)
        else:
            config='peer_'+entry['profile_id'];section=(uci.get('wireguard') or {}).get(config)
        rows.append(dict(entry,config=config,location=location(section.get('location')) if isinstance(section,dict) else None,
                         endpoints=endpoints(tunnel['protocol'],section),switchable=switchable(tunnel['protocol'],section,uci),
                         current=entry['profile_id']==tunnel['current_id'] and (tunnel['group_id'] is None or entry['group_id']==tunnel['group_id'])))
    return rows


def parse_ping(text):
    """busybox/iputils ping output -> {'address','avg_ms'} (avg None when nothing came back)."""
    out={'address':None,'avg_ms':None}
    if not isinstance(text,str) or len(text)>65536:return out
    for line in text.split('\n'):
        head=_PING_HEAD.match(line)
        if head and out['address'] is None:out['address']=head.group(1)
        rtt=_PING_RTT.search(line)
        if rtt and ('round-trip' in line or 'rtt' in line):out['avg_ms']=whole_ms(float(rtt.group(2)))
    return out


def ping_argv(host,device=None):
    return PING+(['-I',device] if device else [])+[host]


def measure(protocol,row,io,device=None):
    """-> {'alive','latency_ms','address'}; OpenVPN the fastest of TCP_SAMPLES connects (at most TCP_ATTEMPTS tries),
    WireGuard one ping run. One connect varied 59-191 ms on the MT3000 (02.11.2026), too noisy for a 20 % margin."""
    eps=row['endpoints']
    if not eps:return {'alive':False,'latency_ms':None,'address':None,'samples':[]}
    if protocol=='openvpn':
        best=None;samples=[]
        for attempt in range(TCP_ATTEMPTS):
            ep=eps[attempt%len(eps)]
            try:ms=whole_ms(io['tcp'](ep['host'],ep['port'],TCP_TIMEOUT,device))
            except Exception:ms=None
            if ms is not None:
                samples.append(ms)
                if best is None or ms<best[0]:best=(ms,ep['host'])
                if len(samples)>=TCP_SAMPLES:break
        if best:return {'alive':True,'latency_ms':best[0],'address':best[1],'samples':samples}
        return {'alive':False,'latency_ms':None,'address':None,'samples':[]}
    try:_,text=io['exec'](ping_argv(eps[0]['host'],device),PING_SECONDS)
    except Exception:text=None
    parsed=parse_ping(text)
    return {'alive':parsed['avg_ms'] is not None,'latency_ms':parsed['avg_ms'],'address':parsed['address'],
            'samples':[parsed['avg_ms']] if parsed['avg_ms'] is not None else []}


def rank(rows):
    """Live first, then by latency, then the file order (stable); not measured rows (alive None) after dead ones."""
    def key(item):
        index,row=item
        alive=row.get('alive')
        return (0 if alive is True else 1 if alive is False else 2,row['latency_ms'] if row.get('latency_ms') is not None else 60001,index)
    return [row for _,row in sorted(enumerate(rows),key=key)]


def decide(ranked):
    """The candidate to change to, or None: the best live one when the current one is dead or unknown, otherwise only
    when it is >= 20 % faster (best*5 <= current*4: whole numbers, the same in Lua). A row with switchable False (a
    WireGuard peer without its connection data) is never the one to change to."""
    best=next((row for row in ranked if row.get('alive') is True and row.get('switchable') is not False),None)
    current=next((row for row in ranked if row.get('current')),None)
    if best is None or best is current:return None
    if current is None or current.get('alive') is not True:return best
    return best if best['latency_ms']*5<=current['latency_ms']*4 else None


def plan_profiles_order(text,current,ranked):
    """The profiles file text with the best live non-current candidate right after the current line (the firmware's
    round robin then takes it next); the other lines keep their order. Unchanged text when nothing is to move."""
    if not isinstance(text,str):return text
    target=next((row['profile'] for row in ranked if row.get('alive') is True and row['profile']!=current),None)
    if target is None or current is None:return text
    lines=text.split('\n')
    stripped=[line.strip(' \t\r') for line in lines]
    order=[i for i,s in enumerate(stripped) if _LINE.fullmatch(s)]
    at=[i for i in order if stripped[i]==current];to=[i for i in order if stripped[i]==target]
    if len(at)!=1 or len(to)!=1:return text
    if order[(order.index(at[0])+1)%len(order)]==to[0]:return text
    moved=lines[to[0]]
    rest=[line for i,line in enumerate(lines) if i!=to[0]]
    place=at[0] if to[0]<at[0] else at[0]+1
    return '\n'.join(rest[:place]+[moved]+rest[place:])


def changes_left(history,tunnel_id,now):
    times=(history or {}).get(str(tunnel_id))
    times=[t for t in (times if isinstance(times,list) else []) if isinstance(t,(int,float)) and not isinstance(t,bool) and now-WINDOW<t<=now+5]
    return CHANGES-len(times),times


def vendor_busy(tunnel_id,io):
    """The firmware's own tunnel-switch.sh holds its lock (a live pid inside one of its lock files)."""
    for pattern in LOCKS:
        path=pattern%tunnel_id if '%d' in pattern else pattern
        try:text=io['read'](path)
        except Exception:text=None
        pid=digits(text.strip()) if isinstance(text,str) else None
        if pid and int(pid)>1:
            try:
                if io['alive'](int(pid)):return True
            except Exception:return True
    return False


# Stage 3 (WireGuard): GL's tunnel-switch.sh switch_tunnel() calls update_provider_config <group> <peer> <iface> after
# `uci commit network` and before ifdown/ifup (read 12.10.2026 in the MT3000 firmware audit, usr/bin/tunnel-switch.sh
# lines 499-518 and 593-597). What the gl-session RPC rewrites is not documented; the step is mirrored exactly (the
# same case list, the same JSON, its result ignored like the script ignores it) and the supervisor re-records the
# protected `wireguard` digest after it (pair_auto.server_rebind). Not mirrored: the script's removal of its own
# connection state file (<state_dir>/<iface>_state); it only feeds the firmware's own failover confirmation, which a
# prepared router does not run, and the stage-2 router check passed without it. $1 group, $2 peer, $3 interface:
# digits and an interface name checked by switch_plan(), never interpolated into the script text.
# No single quote in it (the JSON in double quotes, as tunnel-switch.sh writes it): the Lua runtime's sys.exec quotes
# every argument in single quotes and refuses one that holds a quote - MT3000 02.11.2026 23:36 (alpha5): the step
# raised there, the change of wgclient1 stopped after the uci commits, and its rollback stopped at the same step.
PROVIDER_SCRIPT=(r'n=$(uci -q get wireguard.group_$1.group_name);case "$n" in '
                 r'Hideme|ExpressVPN) [ -n "$3" ] && ubus call gl-session call "{\"module\":\"wg_client\",\"func\":\"update_provider_config\",'
                 r'\"params\":{\"group_id\":$1,\"peer_id\":$2,\"instance\":\"$3\",\"update_all\":false}}";; '
                 r'PIA|IPVanish|NordVPN|PureVPN|XVPN) ubus call gl-session call "{\"module\":\"wg_client\",\"func\":\"update_provider_config\",'
                 r'\"params\":{\"group_id\":$1,\"peer_id\":$2,\"update_all\":false}}";; '
                 r'esac;exit 0')


def switch_plan(tunnel,target,enabled,auto_on,carrying,busy,left=CHANGES):
    """-> {'code': None | refusal, 'steps': [argv]}: tunnel-switch.sh's own writes for one idle interface."""
    def refuse(code):return {'code':code,'steps':[]}
    if enabled is not True or auto_on is not True:return refuse(OFF)
    if carrying is not False:return refuse(CARRYING)
    if busy:return refuse(WAITING)
    if left<=0:return refuse(LIMIT)
    section,iface,group,profile=tunnel.get('section'),tunnel.get('interface'),(target or {}).get('group_id'),(target or {}).get('profile_id')
    if not (isinstance(section,str) and _NAME.fullmatch(section) and isinstance(iface,str) and _IFACE[tunnel['protocol']].fullmatch(iface)
            and digits(group) and digits(profile)):return refuse(FAILED)
    rule='route_policy.'+section
    own,other,config=('client_id','peer_id',group+'_'+profile) if tunnel['protocol']=='openvpn' else ('peer_id','client_id','peer_'+profile)
    steps=[['uci','set',rule+'.'+own+'='+profile],['uci','-q','delete',rule+'.'+other],
           ['uci','set',rule+'.group_id='+group],['uci','set','network.'+iface+'.config='+config],
           ['uci','set','network.'+iface+'.disabled=0'],['uci','commit','route_policy'],['uci','commit','network']]
    if tunnel['protocol']=='wireguard':steps.append(['sh','-c',PROVIDER_SCRIPT,'update_provider_config',group,profile,iface])
    return {'code':None,'steps':steps+[['ifdown',iface],['ifup',iface]]}


def run_plan(plan,io,enabled):
    """Runs the steps of a switch_plan -> {'code', 'changed', 'committed', 'touched'}. Only behind the owner switch:
    refuses (OFF) unless enabled is exactly True. changed: a step may have written something (one that succeeded, or a
    failed one other than a uci command - uci writes nothing when it fails); committed: `uci commit network` succeeded;
    touched: ifdown/ifup of the interface was started. A failure with changed False left the router as it was."""
    out={'code':None,'changed':False,'committed':False,'touched':False}
    if enabled is not True:return dict(out,code=OFF)
    if plan.get('code') is not None or not plan.get('steps'):return dict(out,code=plan.get('code') or FAILED)
    for argv in plan['steps']:
        if argv[0] in ('ifdown','ifup'):out['touched']=True
        try:rc,_=io['exec'](argv,EXEC_SECONDS)
        except Exception:rc=None
        if rc is None or rc!=0 and '-q' not in argv:  # `uci -q delete` of an absent option is not a failure
            if argv[0]!='uci':out['changed']=True
            return dict(out,code=FAILED)
        out['changed']=True
        if argv==['uci','commit','network']:out['committed']=True
    return dict(out,code=PICKED)


def execute(plan,io,enabled):
    """run_plan's code only."""
    return run_plan(plan,io,enabled)['code']


NOT_CHANGED='not changed'


def rollback_note(undone,first,back):
    """The log note of a failed change that wrote something (first) and was rolled back (back: the outcome of the
    rollback's server_apply). 'rolled back': every rollback step ran and the session follows; or the previous server
    is back in uci (both commits) with the session re-bound while the failed change never restarted the interface, so
    the tunnel still runs the previous server. 'rollback failed' only when the previous server could not be restored."""
    if undone is True:return 'rolled back'
    if (isinstance(first,dict) and first.get('touched') is False and isinstance(back,dict) and back.get('committed') is True
            and back.get('rebound') is True):return 'rolled back (the tunnel was not restarted)'
    return 'rollback failed'


# ---- stage 2: the Auto supervisor's side (pair_auto.py / lua/pair.lua) -------------------------------------------
def profile_id(protocol,group,profile):
    """The pair profile id of a server line (inventory.lua): openvpn:<group>_<id>, wireguard:peer_<id>."""
    if not digits(group) or not digits(profile) or protocol not in _IFACE:return None
    return 'openvpn:'+group+'_'+profile if protocol=='openvpn' else 'wireguard:peer_'+profile


def _stamp(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)


def request_valid(row,now):
    """A hand-off of the monitor job that the supervisor may act on: complete, consistent and at most REQUEST_AGE old."""
    if not isinstance(row,dict) or not _stamp(row.get('time')) or not _stamp(now) or not 0<=now-row['time']<=REQUEST_AGE:return False
    protocol=row.get('protocol');iface=row.get('interface');section=row.get('section');tunnel=row.get('tunnel_id')
    if protocol not in _IFACE or not isinstance(iface,str) or not _IFACE[protocol].fullmatch(iface):return False
    if not isinstance(section,str) or not _NAME.fullmatch(section) or isinstance(tunnel,bool) or not isinstance(tunnel,int):return False
    if not digits(row.get('group_id')) or not digits(row.get('profile_id')):return False
    for key in ('from','to'):
        if not isinstance(row.get(key),str) or not _LINE.fullmatch(row[key]):return False
    match=_LINE.fullmatch(row['to'])
    return match.group(2)==row['group_id'] and match.group(3)==row['profile_id'] and row['from']!=row['to']


def claim(io,row,now):
    """The live tunnel of a valid hand-off: {'tunnel','target','previous'} or None (stale: its server or rule moved).
    Read again from uci here: the supervisor never trusts the RAM file for what it writes."""
    if not request_valid(row,now):return None
    try:rc,out=io['exec'](['uci','-q','-X','show','route_policy'],EXEC_SECONDS)
    except Exception:return None
    if rc!=0 or not isinstance(out,str):return None
    for tunnel in tunnels(parse_uci(out)):
        if (tunnel['tunnel_id']!=row['tunnel_id'] or tunnel['section']!=row['section'] or tunnel['protocol']!=row['protocol']
                or tunnel['interface']!=row['interface']):continue
        group,current=tunnel['group_id'],tunnel['current_id']
        match=_LINE.fullmatch(row['from'])
        if group is None or current is None or match.group(2)!=group or match.group(3)!=current:return None
        return {'tunnel':tunnel,'target':{'group_id':row['group_id'],'profile_id':row['profile_id']},
                'previous':{'group_id':group,'profile_id':current}}
    return None


def network_config(protocol,group,profile):
    """network.<iface>.config of a server (tunnel-switch.sh build_config_name): <group>_<id> for OpenVPN, peer_<id>."""
    if not digits(group) or not digits(profile) or protocol not in _IFACE:return None
    return group+'_'+profile if protocol=='openvpn' else 'peer_'+profile


def live_server(io,tunnel):
    """(group_id, profile_id) the route_policy rule of this tunnel names now, or None (unreadable, gone or moved).
    The crash/power-cut recovery of a server change compares it with the recorded `from` and `to`."""
    try:rc,out=io['exec'](['uci','-q','-X','show','route_policy'],EXEC_SECONDS)
    except Exception:return None
    if rc!=0 or not isinstance(out,str) or not isinstance(tunnel,dict):return None
    for row in tunnels(parse_uci(out)):
        if (row['tunnel_id']==tunnel.get('tunnel_id') and row['section']==tunnel.get('section') and row['protocol']==tunnel.get('protocol')
                and row['interface']==tunnel.get('interface')):
            return (row['group_id'],row['current_id']) if row['group_id'] is not None and row['current_id'] is not None else None
    return None


def gate(c):
    """The supervisor's refusal of one hand-off, or None. Keys of c: enabled, phase (session), journal_phase,
    journal_manual, kernel_verified, kernel_role, interface (requested), source_interface, target_interface,
    manual_hold, pending, anchored (the requested tunnel bound by its tunnel id, not by a profile id), busy, left.
    Never the carrying tunnel. Stage 2: the idle reserve while the kernel proves the traffic on the primary and the pair
    rests (journal empty or ROLLED-BACK). Stage 3: the failed primary while the kernel proves the traffic on the reserve
    after a completed automatic switch (journal COMMITTED, not a manual one). Never during a transition, a manual hold
    or another pending change. The role of the tunnel a passed gate changes: role_of(c)."""
    if c.get('enabled') is not True:return OFF
    role=c.get('kernel_role') if c.get('kernel_verified') is True and c.get('kernel_role') in ('source','target') else None
    if role is None or c.get('interface')==c.get(role+'_interface'):return CARRYING  # an unknown route is carrying (stage 1)
    if (c.get('phase')!='RUNNING' or role_of(c) is None or c.get('manual_hold') is not None or c.get('pending') is True
            or c.get('anchored') is not True):return DEFERRED
    if c.get('busy') is True:return WAITING
    left=c.get('left')
    if isinstance(left,bool) or not isinstance(left,int) or left<=0:return LIMIT
    return None


def role_of(c):
    """The pair role of the requested idle tunnel the gate may change, or None: 'target' (stage 2, the traffic on the
    primary, the pair at rest) or 'source' (stage 3, the traffic on the reserve after a COMMITTED automatic switch)."""
    if c.get('kernel_verified') is not True:return None
    if (c.get('kernel_role')=='source' and c.get('interface')==c.get('target_interface')
            and c.get('journal_phase') in (None,'ROLLED-BACK')):return 'target'
    if (c.get('kernel_role')=='target' and c.get('interface')==c.get('source_interface')
            and c.get('journal_phase')=='COMMITTED' and c.get('journal_manual') is not True):return 'source'
    return None


_RENAMED=('before','after','restored_order','restore_target_order','restore_before_order','restore_order_origin')


def rebind(state,journal,order,hash_,profile,role='target'):
    """The session after its own server change of one idle tunnel: (state, journal or None). An anonymous rule's id is
    the digest of its options (client_id/peer_id/group_id among them), so the changed tunnel's rule gets a new id and
    the policy hash changes. Only that rule may have moved in the live order, compared with the order the session
    expects live: the session order (role 'target', stage 2: the traffic on the primary) or the session order with the
    two pair rules swapped (role 'source', stage 3: the traffic on the reserve, the COMMITTED journal's `after`). The
    session order, policy hash, roles (<role>_rule, generic_rules, <role>_id = profile) and the remembered selected
    policy follow it.
    Stage 2: a finished ROLLED-BACK journal is renamed the same way so the cleanup's session check holds; its profile
    ids stay (they name the servers of that finished transaction).
    Stage 3: the open COMMITTED journal is the one the return to the primary restores, so everything the return and
    its rollback compare follows: before/after (and any restore order), the pair context (source_rule, generic_rules,
    session_order, primary_order, source_id), the journal's source id, vendor_profiles.source.id (its vendor generation
    stays until the monitor observes the new profile: pair_auto.server_settled) and the hash. The result must satisfy
    the session check (pair_policy.state_order_matches: the live order is the journal's after, the same hash, session
    order and roles). Idempotent: a journal already re-bound (a crash between the journal and the session write - the
    journal is written first) is accepted as it is.
    ValueError(FAILED) for anything else - the change is then not explainable and the normal checks treat it as external."""
    import copy
    old=state.get('order') if isinstance(state,dict) else None
    roles=state.get('policy_roles') if isinstance(state,dict) else None
    if (role not in ('source','target') or not isinstance(old,list) or not isinstance(order,list) or len(old)!=len(order)
            or len(set(order))!=len(order) or any(not isinstance(x,str) for x in old+order) or not isinstance(roles,dict)
            or not isinstance(profile,str) or not isinstance(hash_,str) or not re.fullmatch('[a-f0-9]{64}',hash_)):raise ValueError(FAILED)
    expected=list(old)
    if role=='source':
        context=journal.get('pair_transition') if isinstance(journal,dict) else None
        pair=(roles.get('source_rule'),roles.get('target_rule'))
        if (not isinstance(context,dict) or journal.get('phase')!='COMMITTED' or any(x not in old for x in pair)
                or journal.get('source') not in (roles.get('source_id'),profile) or context.get('source_id') not in (roles.get('source_id'),profile)
                or pair[1] not in order):
            raise ValueError(FAILED)
        # the two pair rules stand live as the reserve rule (its id does not change in stage 3) says: the session order
        # is the order at Start and may already be the reserve-first one (MT3000 02.11.2026, OpenVPN primary: the
        # always-swapped expectation refused a correct change - SERVER-PICK-FAILED, rollback failed)
        a,b=old.index(pair[0]),old.index(pair[1])
        if old[order.index(pair[1])]!=pair[1]:expected[a],expected[b]=expected[b],expected[a]
    moved=[i for i in range(len(expected)) if expected[i]!=order[i]]
    if len(moved)>1 or moved and expected[moved[0]]!=roles.get(role+'_rule'):raise ValueError(FAILED)
    names={expected[i]:order[i] for i in moved}
    def name(x):return names.get(x,x)
    def rename(values):return [name(x) for x in values]
    value=copy.deepcopy(state);previous_hash=value.get('policy_hash')
    value['order']=rename(old);value['policy_hash']=hash_
    value['policy_roles']=dict(roles,**{role+'_rule':name(roles[role+'_rule']),'generic_rules':sorted(rename(roles.get('generic_rules') or [])),
                                        role+'_id':profile})
    if isinstance(value.get('selected_policy'),dict) and isinstance(value['selected_policy'].get('order'),list):
        value['selected_policy']=dict(value['selected_policy'],order=rename(value['selected_policy']['order']),hash=hash_)
    if not isinstance(journal,dict) or journal.get('phase')!=('COMMITTED' if role=='source' else 'ROLLED-BACK'):return value,None
    renamed=copy.deepcopy(journal)
    for key in _RENAMED:
        if isinstance(renamed.get(key),list):renamed[key]=rename(renamed[key])
    step=renamed.get('restore_order_step')
    if isinstance(step,dict):
        for key in ('before','after'):
            if isinstance(step.get(key),list):step[key]=rename(step[key])
    context=renamed.get('pair_transition')
    if isinstance(context,dict):
        for key in ('source_rule','target_rule'):
            if isinstance(context.get(key),str):context[key]=name(context[key])
        if isinstance(context.get('generic_rules'),list):context['generic_rules']=sorted(rename(context['generic_rules']))
        for key in ('session_order','primary_order'):
            if isinstance(context.get(key),list):context[key]=rename(context[key])
    if renamed.get('hash')==previous_hash:renamed['hash']=hash_
    if role=='source':
        context['source_id']=profile;renamed['source']=profile
        proofs=renamed.get('vendor_profiles')
        if isinstance(proofs,dict) and isinstance(proofs.get('source'),dict):proofs['source']['id']=profile
        if (renamed.get('after')!=order or renamed.get('hash')!=hash_ or context.get('session_order')!=value['order']
                or any(context.get(key)!=item for key,item in value['policy_roles'].items())):raise ValueError(FAILED)
    return value,renamed


def record(io,tunnel_id,now,change=None,count=True,taken=None):
    """The supervisor's change of one tunnel: counted in the rate-limit history (count), shown (change), and the time of
    the hand-off it took (taken: a hand-off is acted on once, also after a rollback) (STATE)."""
    try:state=json.loads(io['read'](io['runtime']+'/'+STATE) or '{}')
    except Exception:state={}
    if not isinstance(state,dict):state={}
    history=state.get('changes') if isinstance(state.get('changes'),dict) else {}
    last=state.get('last') if isinstance(state.get('last'),dict) else {}
    _,times=changes_left(history,tunnel_id,now)
    history[str(tunnel_id)]=times+[now] if count else times
    if change is not None:last[str(tunnel_id)]=change
    value={'changes':history,'last':last}
    if taken is None:taken=state.get('taken') if _stamp(state.get('taken')) else None
    if taken is not None:value['taken']=taken
    try:return io['write'](io['runtime']+'/'+STATE,json.dumps(value,sort_keys=True,separators=(',',':'))) is True
    except Exception:return False


def event(io,code,tunnel,now,change=None,request=None,note=None):
    """One outcome of the supervisor: the history event file (EVENT, both monitors read it) and the system log line.
    The same refusal of the same hand-off is published once."""
    try:previous=json.loads(io['read'](io['runtime']+'/'+EVENT) or 'null')
    except Exception:previous=None
    rows=previous.get('tunnels') if isinstance(previous,dict) else None
    if (request is not None and isinstance(previous,dict) and previous.get('request')==request and isinstance(rows,list) and len(rows)==1
            and isinstance(rows[0],dict) and rows[0].get('code')==code):return False
    value={'time':now,'request':request,'tunnels':[{'tunnel_id':tunnel['tunnel_id'],'code':code}]}
    try:io['write'](io['runtime']+'/'+EVENT,json.dumps(value,sort_keys=True,separators=(',',':')))
    except Exception:pass
    if io.get('log'):
        try:io['log'](log_line(code,tunnel,change)+('; '+note if note else ''))
        except Exception:pass
    return True


def public_row(row):
    return {'profile':row['profile'],'location':row['location'],'latency_ms':row.get('latency_ms'),'alive':row.get('alive')}


# ---- the Bayesian pick (owner setting server_pick_model 'bayes'; 'simple' = the 20 % rule above) ------------------
# Offline study: private/math/bayes-pick (simulator + REPORT.ru.md). With lognormal measurement noise sigma~0.39 (one
# TCP connect 59-191 ms, MT3000 02.11.2026) the 20 % rule on one round's reading changes between equal servers ~39
# times a day while a channel stays failed. Here every server keeps a posterior instead of one round's reading:
#   latency      log RTT ~ Normal(mu, s^2), conjugate Normal-Inverse-Gamma on every sample (each TCP connect, or the
#                WireGuard ping average), prior s^2 ~ IG(PRIOR_A, PRIOR_B) (prior noise sigma 0.4); the marginal
#                posterior of mu is a Student t, used through its mean and variance (PRIOR_B + SS/2) / (n (PRIOR_A + n/2 - 1));
#   availability Beta(ok + 1, bad + 1) of the rounds the server answered / did not answer;
#   decay        all evidence (n, SS, ok, bad) fades with HALF_LIFE, so a server that changed is re-learned (1 h:
#                chosen on separate tuning seeds; 6 h needed ~6 h to leave a degrading server);
#   decision     a working current server is replaced only when z = (mu_cur - mu_cand - ln(1/(1-MARGIN))) /
#                sqrt(var_cur + var_cand) >= Z_CHANGE (P(candidate at least MARGIN % faster) >= 0.95 under the normal
#                approximation; MARGIN 0: the 95 % test itself is the hysteresis - a 5 % margin halved the useless
#                changes again but doubled the time to find a 10 % better server), the candidate answered this round, is switchable and its availability mean is
#                >= AVAILABLE. A dead current server is replaced at once by the best live one, exactly as the simple rule.
#                The rate limit, the carrying-tunnel refusal and the hand-off to the Auto supervisor are unchanged;
#   probes       a deterministic UCB bandit: every round measures the current server, servers never measured or not
#                measured for STALE seconds, and those that could plausibly be the best (mu - Z_PLAUSIBLE sd <= the
#                lowest mu + Z_PLAUSIBLE sd of the servers alive last time). A dead current server measures all the rest
#                in the same round. Never more probes than the simple rule (the same TCP_SAMPLES per measured server).
# The model is a RAM file (MODEL) of whole numbers (fixed point, the same text in Lua), written by the monitor job only.
MODEL='server-pick-model.json'
MODELS=('simple','bayes')
HALF_LIFE=3600
PRIOR_A=2
PRIOR_B_E4=1600   # PRIOR_B=0.16: the prior mean of the noise variance, sigma 0.4
MARGIN_PCT=0
Z_CHANGE_E3=1645
Z_PLAUSIBLE_E3=2000
STALE=3600
AVAILABLE_PCT=80
MODEL_MAX=64
MODEL_AGE=604800
LN2=0.6931471805599453
_MODEL_KEY=re.compile(r'[0-9]{1,9}:(?:[a-z]{1,16}:)?[0-9]{1,9}_[0-9]{1,9}')
_MODEL_LIMITS=(2**31-1,10**8,200000,10**9,10**8,10**8,1)  # t, n*1000, mu*1e4, SS*1e4, ok*1000, bad*1000, alive


def model_name(value):
    """The owner setting server_pick_model: 'bayes' or 'simple' (anything else is the simple rule)."""
    return 'bayes' if value=='bayes' else 'simple'


def _q(value,scale):return int(math.floor(value*scale+0.5))


def model_key(tunnel_id,profile):return '%d:%s'%(tunnel_id,profile)


def model_entry(raw):
    """A stored entry [t, n*1000, mu*1e4, SS*1e4, ok*1000, bad*1000, alive] checked, else None."""
    if not isinstance(raw,list) or len(raw)!=7:return None
    for value,high in zip(raw,_MODEL_LIMITS):
        if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=high:return None
    return raw


def model_read(io):
    """{key: entry} of the MODEL file; broken entries (and a broken file) are left out."""
    try:value=json.loads(io['read'](io['runtime']+'/'+MODEL) or '{}')
    except Exception:value={}
    rows=value.get('servers') if isinstance(value,dict) else None
    out={}
    for key,raw in (rows.items() if isinstance(rows,dict) else []):
        entry=model_entry(raw)
        if isinstance(key,str) and _MODEL_KEY.fullmatch(key) and entry is not None:out[key]=entry
    return out


def model_text(model,now):
    """The MODEL file text: entries not older than MODEL_AGE, at most MODEL_MAX (the newest; ties by key)."""
    keep=sorted(((-e[0],k) for k,e in model.items() if now-e[0]<=MODEL_AGE))[:MODEL_MAX]
    return json.dumps({'servers':{k:model[k] for _,k in keep},'version':1},sort_keys=True,separators=(',',':'))


def model_state(entry,now):
    """The decayed evidence of an entry at `now` (floats), or None."""
    if entry is None:return None
    t,n,mu,ss,ok,bad,alive=entry
    f=math.exp(-max(0,now-t)*LN2/HALF_LIFE)
    return {'t':t,'n':n/1000*f,'mu':mu/10000,'ss':ss/10000*f,'ok':ok/1000*f,'bad':bad/1000*f,'alive':alive==1}


def model_update(entry,now,samples):
    """The entry after one round: samples (ms) of a server that answered, or None/[] for one that did not."""
    s=model_state(entry,now) or {'n':0.0,'mu':0.0,'ss':0.0,'ok':0.0,'bad':0.0}
    n,mu,ss,ok,bad=s['n'],s['mu'],s['ss'],s['ok'],s['bad']
    xs=[math.log(max(1,x)) for x in samples or []]
    if xs:
        k=len(xs);total=0.0
        for x in xs:total+=x
        mean=total/k;inner=0.0
        for x in xs:inner+=(x-mean)*(x-mean)
        m=n+k;d=mean-mu
        mu=mu+k*d/m;ss=ss+inner+n*k*d*d/m;n=m;ok+=1;alive=1
    else:bad+=1;alive=0
    return [int(now),min(_q(n,1000),10**8),min(max(_q(mu,10000),0),200000),min(_q(ss,10000),10**9),min(_q(ok,1000),10**8),min(_q(bad,1000),10**8),alive]


def posterior(state):
    """(mu, variance of mu) of a decayed state, None with less than one sample of evidence."""
    if state is None or state['n']<1:return None
    n=state['n']
    return state['mu'],(PRIOR_B_E4/10000+state['ss']/2)/(n*(PRIOR_A+n/2-1))


def availability(state):
    """Beta(ok+1, bad+1) mean, percent (float)."""
    return 100*((state['ok'] if state else 0)+1)/((state['ok']+state['bad'] if state else 0)+2)


def probe_plan(rows,states,now):
    """Which rows (by index, at most MAX_MEASURED) this round measures: the current one, unknown and stale ones, and
    the plausible best (mu - z sd <= the lowest mu + z sd among the servers alive last time). states: per row."""
    z=Z_PLAUSIBLE_E3/1000;posts=[posterior(s) for s in states]
    upper=None
    for s,p in zip(states,posts):
        if p is not None and s['alive']:
            u=p[0]+z*math.sqrt(p[1])
            if upper is None or u<upper:upper=u
    plan=[]
    for i,row in enumerate(rows):
        if i>=MAX_MEASURED:plan.append(False);continue
        s,p=states[i],posts[i]
        plan.append(bool(row.get('current') or p is None or now-s['t']>=STALE or upper is None or p[0]-z*math.sqrt(p[1])<=upper))
    return plan


def decide_bayes(rows,states):
    """The candidate to change to, or None. rows: this round (alive True/False measured, None not measured);
    states: the decayed model per row after this round's update. Dead/unknown current: the live switchable candidate
    with the lowest posterior mu (as the simple rule's 'best live one'). Working current: the candidate with the
    lowest posterior mu among those with z >= Z_CHANGE (ties: file order): measured this round, live, switchable, with
    availability >= AVAILABLE_PCT."""
    current=None;eligible=[]
    for i,row in enumerate(rows):
        p=posterior(states[i])
        if row.get('current'):current=(row,p)
        elif row.get('alive') is True and row.get('switchable') is not False and p is not None:eligible.append((row,p,states[i]))
    if not eligible:return None
    if current is None or current[0].get('alive') is not True or current[1] is None:
        best=None
        for row,p,_ in eligible:
            if best is None or p[0]<best[1][0]:best=(row,p)
        return best[0]
    margin=-math.log(1-MARGIN_PCT/100);mu,var=current[1];best=None
    for row,p,s in eligible:
        if availability(s)<AVAILABLE_PCT:continue
        z=(mu-p[0]-margin)/math.sqrt(var+p[1])
        if z>=Z_CHANGE_E3/1000 and (best is None or p[0]<best[1]):best=(row,p[0])
    return best[0] if best else None


def bayes_round(tunnel,rows,model,io,device,now):
    """Measure the rows the bandit picks (and all of them when the current server does not answer), update the model
    (in place) and give every row its published reading: alive (this round, else the last known), latency_ms (the
    posterior median exp(mu), whole ms). -> (target or None, probes) - probes: the measured servers."""
    keys=[model_key(tunnel['tunnel_id'],row['profile']) for row in rows]
    states=[model_state(model.get(k),now) for k in keys]
    plan=probe_plan(rows,states,now)
    measured=[False]*len(rows)
    def run(i):
        m=measure(tunnel['protocol'],rows[i],io,device)
        rows[i].update(alive=m['alive'],latency_ms=m['latency_ms'],address=m['address'])
        model[keys[i]]=model_update(model.get(keys[i]),now,m.get('samples') if m['alive'] else None)
        states[i]=model_state(model[keys[i]],now);measured[i]=True
    for i in range(len(rows)):
        if plan[i]:run(i)
        else:rows[i].update(alive=None,latency_ms=None,address=None)
    if any(row.get('current') and measured[i] and rows[i]['alive'] is not True for i,row in enumerate(rows)):
        for i in range(min(len(rows),MAX_MEASURED)):
            if not measured[i]:run(i)
    target=decide_bayes(rows,states)
    for i,row in enumerate(rows):
        p=posterior(states[i])
        if not measured[i] and states[i] is not None:row['alive']=states[i]['alive']
        if row.get('alive') is True and p is not None:row['latency_ms']=whole_ms(math.exp(p[0]))
    return target,sum(measured)


def job(io,request,now):
    """One round: read, (measure, order, switch when enabled), write the published block; returns it.
    request: {'enabled': bool, 'auto_on': bool, 'failed': [interface], 'model': 'simple' | 'bayes' (absent: simple)}.
    The Bayesian model (bayes_round) only changes which servers are measured, the published readings and the choice
    of the target; everything after the choice (carrying, limit, vendor lock, hand-off) is the same."""
    request=request if isinstance(request,dict) else {}
    enabled=request.get('enabled') is True;auto_on=request.get('auto_on') is True
    bayes=enabled and model_name(request.get('model'))=='bayes'
    model=model_read(io) if bayes else None
    failed=[x for x in request.get('failed') or [] if isinstance(x,str)]
    text=''
    for config in ('route_policy','ovpnclient','wireguard'):
        try:rc,out=io['exec'](['uci','-q','-X','show',config],EXEC_SECONDS)
        except Exception:rc,out=1,''
        if rc==0 and isinstance(out,str):text+=out+'\n'
    uci=parse_uci(text)
    try:state=json.loads(io['read'](io['runtime']+'/'+STATE) or '{}')
    except Exception:state={}
    if not isinstance(state,dict):state={}
    history=state.get('changes') if isinstance(state.get('changes'),dict) else {}
    last=state.get('last') if isinstance(state.get('last'),dict) else {}
    device=io['wan']() if enabled and io.get('wan') else None
    active=None;active_read=False
    result={'time':now,'enabled':enabled,'tunnels':[]}
    for tunnel in tunnels(uci):
        try:profiles=io['read'](tunnel['profiles'])
        except Exception:profiles=None
        rows=candidates(tunnel,profiles,uci)
        current=next((row['profile'] for row in rows if row['current']),None)
        code=None;ordered=False;target=None
        if bayes:target,_=bayes_round(tunnel,rows,model,io,device,now)
        else:
            for index,row in enumerate(rows):
                if enabled and index<MAX_MEASURED:row.update(measure(tunnel['protocol'],row,io,device))
                else:row.update(alive=None,latency_ms=None,address=None)
        ranked=rank(rows)
        best=next((row['profile'] for row in ranked if row.get('alive') is True),None)
        if enabled and profiles is not None:
            planned=plan_profiles_order(profiles,current,ranked)
            if planned!=profiles:
                try:ordered=io['write'](tunnel['profiles'],planned) is True
                except Exception:ordered=False
        if not bayes:target=decide(ranked)
        if enabled and target is not None and tunnel['interface'] in failed:
            if not active_read:
                active_read=True
                try:active=io['active_mark']()
                except Exception:active=None
            carrying=active is None or tunnel['mark'] is None or tunnel['mark']==active
            left,times=changes_left(history,tunnel['tunnel_id'],now)
            plan=switch_plan(tunnel,target,enabled,auto_on,carrying,vendor_busy(tunnel['tunnel_id'],io),left)
            code=plan['code']
            if code is None:
                # Stage 2: only the Auto supervisor changes a server (inside its lock, without a pair readopt).
                old=next((row for row in rows if row['current']),None)
                request={'time':now,'tunnel_id':tunnel['tunnel_id'],'protocol':tunnel['protocol'],'interface':tunnel['interface'],
                         'section':tunnel['section'],'from':current,'to':target['profile'],'group_id':target['group_id'],
                         'profile_id':target['profile_id'],'from_ms':old.get('latency_ms') if old else None,
                         'to_ms':target.get('latency_ms'),'from_location':old['location'] if old else None,'to_location':target['location']}
                try:wrote=io['write'](io['runtime']+'/'+CHANGE,json.dumps(request,sort_keys=True,separators=(',',':'))) is True
                except Exception:wrote=False
                code=REQUESTED if wrote else FAILED
            if code in EVENT_CODES and io.get('log'):
                try:io['log'](log_line(code,tunnel,None))
                except Exception:pass
        result['tunnels'].append({'tunnel_id':tunnel['tunnel_id'],'protocol':tunnel['protocol'],'interface':tunnel['interface'],
            'current':current,'best':best,'ordered':ordered,'code':code,'last_change':last.get(str(tunnel['tunnel_id'])),
            'candidates':[public_row(row) for row in rows]})
    if bayes:
        try:io['write'](io['runtime']+'/'+MODEL,model_text(model,now))
        except Exception:pass
    try:io['write'](io['runtime']+'/'+RESULT,json.dumps(result,sort_keys=True,separators=(',',':')))
    except Exception:pass
    return result


def log_line(code,tunnel,change):
    line='%s: %s (tunnel %d %s)'%(code,TEXT[code],tunnel['tunnel_id'],tunnel['protocol'])
    if change:
        line+=': %s -> %s, %s -> %s ms'%(change.get('from_location') or change.get('from') or '?',change.get('to_location') or change.get('to') or '?',
                                         '?' if change.get('from_ms') is None else change['from_ms'],'?' if change.get('to_ms') is None else change['to_ms'])
    return line


# ---- the monitor's side ------------------------------------------------------------------------------------------
def failed_interfaces(profiles):
    """Interfaces of channels whose last check failed (not inactive, not skipped by the check limit)."""
    out=[]
    for row in profiles if isinstance(profiles,list) else []:
        if not isinstance(row,dict):continue
        code=row.get('code');iface=row.get('interface')
        if isinstance(code,str) and code not in ('PROFILE-INACTIVE','CHECK-LIMIT') and isinstance(iface,str) and iface not in out:out.append(iface)
    return sorted(out)


def due(last_start,previous_failed,failed,clock):
    """A new round is due: never ran, MEASURE_EVERY seconds passed, or a channel failed that was not failed before."""
    if last_start is None or clock-last_start>=MEASURE_EVERY:return True
    return any(iface not in (previous_failed or []) for iface in failed)


def carrying_retry(picked,previous_failed,retried,last_start,clock):
    """{'failed','retried'}: previous_failed without the channels the last round skipped because they still carried the
    traffic, once RETRY_CARRYING seconds passed, and at most once per failure (retried; the caller drops a channel from it
    when the channel recovers). The round a failure starts often runs before Auto has moved the traffic to the reserve
    (MT3000 02.11.2026, SERVER-PICK-CARRYING and no server change); a channel that keeps carrying (reserve down, hold)
    gets no further rounds before MEASURE_EVERY."""
    failed=list(previous_failed or []);done=list(retried or [])
    if last_start is None or clock-last_start<RETRY_CARRYING or not isinstance(picked,dict):return {'failed':failed,'retried':done}
    skipped={row.get('interface') for row in picked.get('tunnels') or [] if isinstance(row,dict) and row.get('code')==CARRYING}
    again=[iface for iface in failed if iface in skipped and iface not in done]
    return {'failed':[iface for iface in failed if iface not in again],'retried':done+again}


def project(value):
    """The checked copy of server-pick.json for the status (both monitors), or None."""
    if not isinstance(value,dict) or type(value.get('enabled')) is not bool or not isinstance(value.get('tunnels'),list):return None
    stamp=value.get('time')
    if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or stamp!=stamp or stamp<0:return None
    out=[]
    for row in value['tunnels'][:MAX_TUNNELS]:
        if not isinstance(row,dict) or row.get('protocol') not in _IFACE or not isinstance(row.get('candidates'),list):return None
        candidates_out=[]
        for c in row['candidates'][:MAX_CANDIDATES]:
            if not isinstance(c,dict) or not isinstance(c.get('profile'),str) or not _LINE.fullmatch(c['profile']):return None
            ms=c.get('latency_ms');alive=c.get('alive')
            if ms is not None and whole_ms(ms)!=ms or alive is not None and type(alive) is not bool:return None
            candidates_out.append({'profile':c['profile'],'location':location(c.get('location')),
                                   'latency_ms':ms,'alive':alive})
        iface=row.get('interface')
        change=project_change(row.get('last_change'))
        if change is False:return None
        out.append({'tunnel_id':row.get('tunnel_id') if isinstance(row.get('tunnel_id'),int) and not isinstance(row.get('tunnel_id'),bool) else None,
                    'protocol':row['protocol'],'interface':iface if isinstance(iface,str) and _IFACE[row['protocol']].fullmatch(iface) else None,
                    'current':row.get('current') if isinstance(row.get('current'),str) and _LINE.fullmatch(row['current']) else None,
                    'best':row.get('best') if isinstance(row.get('best'),str) and _LINE.fullmatch(row['best']) else None,
                    'ordered':row.get('ordered') is True,'code':row.get('code') if row.get('code') in CODES else None,
                    'last_change':change,
                    'candidates':candidates_out})
    return {'time':stamp,'enabled':value['enabled'],'tunnels':out}


def project_change(change):
    """A last_change record checked field by field: None (no change yet), False (malformed) or the copy."""
    if change is None:return None
    if not isinstance(change,dict) or isinstance(change.get('time'),bool) or not isinstance(change.get('time'),(int,float)):return False
    out={'time':change['time']}
    for key in ('from','to'):
        value=change.get(key)
        if value is not None and not (isinstance(value,str) and _LINE.fullmatch(value)):return False
        out[key]=value
    for key in ('from_ms','to_ms'):
        value=change.get(key)
        if value is not None and whole_ms(value)!=value:return False
        out[key]=value
    for key in ('from_location','to_location'):out[key]=location(change.get(key))
    return out


def events(result,seen):
    """History events of a finished round newer than `seen` (one per tunnel with an event code)."""
    if not isinstance(result,dict) or not isinstance(result.get('time'),(int,float)) or (seen is not None and result['time']<=seen):return []
    return [{'time':result['time'],'code':row['code'],'tunnel_id':row.get('tunnel_id')}
            for row in result.get('tunnels') or [] if isinstance(row,dict) and row.get('code') in EVENT_CODES]


# ---- the router's io (Python runtime) ----------------------------------------------------------------------------
def pick_uplink(rows):
    """`network.interface dump` rows -> the device of the up non-VPN interface with the lowest-metric default route."""
    best=None
    for row in rows if isinstance(rows,list) else []:
        if not isinstance(row,dict) or row.get('up') is not True:continue
        name,device=row.get('interface'),row.get('l3_device')
        if not isinstance(name,str) or re.match(r'(wgclient|ovpnclient|wgserver|ovpnserver|lan|loopback)',name):continue
        if not isinstance(device,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,15}',device):continue
        for route in row.get('route') if isinstance(row.get('route'),list) else []:
            if isinstance(route,dict) and route.get('target')=='0.0.0.0' and route.get('mask')==0:
                metric=route.get('metric') if type(route.get('metric')) is int else 0
                if best is None or metric<best[0]:best=(metric,device)
    return best[1] if best else None


def router_io(runtime='/var/run/homensai-vpn'):
    import os
    import socket
    import subprocess
    import time
    def read(path):
        try:
            with open(path,'rb') as stream:return stream.read(MAX_TEXT).decode('utf-8','replace')
        except OSError:return None
    def write(path,text):
        directory,name=os.path.split(path)
        pending=os.path.join(directory,'.'+name+'.pending')
        try:
            with open(pending,'w',encoding='utf-8') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
            os.chmod(pending,0o644 if path.startswith('/etc/vpn_profiles.d/') else 0o600)
            os.replace(pending,path);return True
        except OSError:
            try:os.unlink(pending)
            except OSError:pass
            return False
    def run(argv,seconds):
        try:
            done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=seconds)
            return done.returncode,done.stdout[:MAX_TEXT].decode('utf-8','replace')
        except (OSError,subprocess.SubprocessError):return 255,''
    def tcp(host,port,timeout,device):
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            if device:sock.setsockopt(socket.SOL_SOCKET,25,device.encode()+b'\0')  # SO_BINDTODEVICE
            sock.settimeout(timeout);started=time.monotonic()
            sock.connect((host,port))
            return (time.monotonic()-started)*1000
        except OSError:return None
        finally:sock.close()
    def alive(pid):return os.path.exists('/proc/%d'%pid)
    def wan():
        # The uplink that holds the default route: wan, or wwan when the router is a Wi-Fi repeater (MT3000, 02.11.2026).
        rc,out=run(['ubus','call','network.interface','dump'],5)
        try:rows=json.loads(out).get('interface') if rc==0 else None
        except (ValueError,AttributeError):rows=None
        return pick_uplink(rows)
    def active_mark():
        from kernel_policy import parse_mangle,fields
        from dns_mark import active_from_chains
        rc,out=run(['iptables-save','-t','mangle'],10)
        mark=active_from_chains(parse_mangle(out),fields) if rc==0 else None
        return parse_mark(mark)
    def log(line):run(['logger','-t','homensai-vpn',line],5)
    return {'runtime':runtime,'read':read,'write':write,'exec':run,'tcp':tcp,'alive':alive,'wan':wan,'active_mark':active_mark,'log':log}
