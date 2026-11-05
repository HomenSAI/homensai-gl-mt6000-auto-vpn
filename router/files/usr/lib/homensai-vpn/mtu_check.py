"""HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE. Large-packet check of a VPN channel.

Router finding 02.11.2026 (MT3000, matrix phase 2, primary-mtu): every packet longer than 1300 bytes sent into
the primary tunnel was dropped (an MTU black hole). The HTTPS/DNS probes send only small requests, so Auto saw a
healthy primary and never left it while large LAN transfers hung.

One check sends through the tunnel device (SO_BINDTODEVICE and the tunnel's fwmark, as icmp_ping.py) to each of
TARGETS one small echo request and LARGE_COUNT large ones whose IP length is the tunnel device MTU (at most 1500),
so the router never fragments them. Verdict (shared cases: tests/mtu_check_cases.json, twin lua/mtu_check.lua):

  ok            a large echo came back (a truncated reply counts: the request crossed the tunnel), or a router on
                the path answered "fragmentation needed" for it (path MTU discovery works, no black hole);
  black-hole    no large echo of any target came back while a small echo of the same check did;
  inconclusive  no small echo came back either (ICMP filtered, or the tunnel is down: HTTPS/DNS decide);
  unavailable   the check could not be sent (socket error).

A send the router's own firewall refuses (EPERM/EACCES: an nft/iptables OUTPUT drop answers the sender so) is a lost
echo, not a socket error. Router finding 03.11.2026 (MT3000, 2.1.0-alpha7, primary-mtu-long): `oifname wgclient1
meta length > 1300 drop` refused the large sends with EPERM, every check became 'unavailable', VPN-MTU never appeared.

Only black-hole changes the health: an otherwise healthy probe result gets the code VPN-MTU (a failure for the
Auto streaks, so Auto prefers the other tunnel when it passes; a reserve with VPN-MTU is not a ready target).
Rate: a channel is checked on its first monitor probe, then every INTERVAL seconds; after a black-hole verdict on
every probe until a check passes again, so each VPN-MTU sample is its own fresh measurement (never a cached code)
and the recovery is seen at once. Between checks run() hands back the channel's last reading (state, size and the
measurement time), so every status row carries mtu_check, not only the one pass in INTERVAL that measured (router
finding 03.11.2026: the field was missing from almost every status.json). A remembered reading is never black-hole
(a black hole is checked again on every probe), so VPN-MTU always comes from a fresh measurement.
The monitor is the only caller (one shared source of the reading); Auto's live
probes (native_switch/lua_bridge processes) never set agent.MTU_SCHEDULE and do not run it.
"""
import errno
import os
import socket
import struct
import time
from pathlib import Path
from threading import Lock

from icmp_ping import binding_valid, checksum

CODE='VPN-MTU'
TARGETS=('1.1.1.1','9.9.9.9')
INTERVAL=300       # seconds between checks of a channel that passed
TIMEOUT=1.5        # one wait for all echoes of a check
LARGE_COUNT=2      # large echoes per target: one lost large packet is not a black hole
SMALL_SIZE=64      # IP length of the small echo
MIN_SIZE=576       # IPv4 minimum reassembly size: a smaller device MTU is not checked
MAX_SIZE=1500
HEADER=28          # IPv4 (20) + ICMP echo (8)
MAGIC=b'HV-MTU\0\0'
STATES=('ok','black-hole','inconclusive','unavailable')
LIMIT=32           # remembered channels
SEPARATOR='\x1f'
TIME_MAX=2**53-1   # the published measurement time (whole seconds)
REFUSED=(errno.EPERM,errno.EACCES)  # a send refused by the router's own firewall: the echo is lost
SYS_NET=Path('/sys/class/net')


def parse_mtu(text):
    """The sysfs mtu text -> int, or None (unreadable or not plain decimal digits)."""
    if not isinstance(text,str):return None
    text=text.strip()
    if not text.isdigit() or not text.isascii() or len(text)>5:return None
    return int(text)


def probe_size(mtu):
    """IP length of a large echo: the device MTU capped at 1500; None below 576 or unknown."""
    if type(mtu) is not int or mtu<MIN_SIZE:return None
    return min(mtu,MAX_SIZE)


def request(identifier,sequence,payload):
    head=struct.pack('!BBHHH',8,0,0,identifier,sequence)
    return struct.pack('!BBHHH',8,0,checksum(head+payload),identifier,sequence)+payload


def plan(size,random=os.urandom):
    """Echo requests of one check, in sending order: per target one small, then LARGE_COUNT large."""
    probes=[]
    for target in TARGETS:
        for kind,length in (('small',SMALL_SIZE),)+(('large',size),)*LARGE_COUNT:
            identifier,sequence=struct.unpack('!HH',random(4))
            payload=MAGIC+random(length-HEADER-len(MAGIC))
            probes.append({'target':target,'kind':kind,'identifier':identifier,'sequence':sequence,'payload':payload,
                           'packet':request(identifier,sequence,payload)})
    return probes


def classify(data,identifier,sequence,payload,target):
    """'echo' (our reply from the target, full or truncated), 'pmtu' (fragmentation needed for our request) or None."""
    if not isinstance(data,(bytes,bytearray)) or len(data)<28 or data[0]>>4!=4:return None
    header=(data[0]&15)*4
    if header<20 or len(data)<header+8 or data[9]!=1:return None
    length=struct.unpack('!H',data[2:4])[0]
    if length<header+8 or length>len(data) or struct.unpack('!H',data[6:8])[0]&0xbfff:return None
    message=bytes(data[header:length])
    if checksum(message)!=0:return None
    kind,code,_,echo_id,echo_seq=struct.unpack('!BBHHH',message[:8])
    if kind==0 and code==0:
        body=message[8:]
        if (socket.inet_ntoa(bytes(data[12:16]))==target and echo_id==identifier and echo_seq==sequence
                and len(body)<=len(payload) and payload[:len(body)]==body):return 'echo'
        return None
    if kind==3 and code==4:
        inner=message[8:]
        if len(inner)<28 or inner[0]>>4!=4:return None
        inner_header=(inner[0]&15)*4
        if inner_header<20 or len(inner)<inner_header+8 or inner[9]!=1:return None
        if socket.inet_ntoa(inner[16:20])!=target:return None
        inner_kind,_,_,echo_id,echo_seq=struct.unpack('!BBHHH',inner[inner_header:inner_header+8])
        if inner_kind==8 and echo_id==identifier and echo_seq==sequence:return 'pmtu'
    return None


def group(probes,outcomes):
    """Per target: {'target', 'small': outcome, 'large': [outcomes]} (outcome 'echo' | 'pmtu' | None)."""
    rows=[]
    for target in TARGETS:
        row={'target':target,'small':None,'large':[]}
        for probe,outcome in zip(probes,outcomes):
            if probe['target']!=target:continue
            if probe['kind']=='small':row['small']=outcome
            else:row['large'].append(outcome)
        rows.append(row)
    return rows


def verdict(rows):
    if any(outcome in ('echo','pmtu') for row in rows for outcome in row['large']):return 'ok'
    if any(row['small']=='echo' for row in rows):return 'black-hole'
    return 'inconclusive'


def key(profile_id,binding):
    return SEPARATOR.join((str(profile_id),str(binding.get('device')),str(binding.get('ifindex'))))


class Schedule:
    """Per channel (profile id, device, ifindex): when the next check is due. Memory only."""

    def __init__(self,interval=INTERVAL):
        self.interval=interval;self.lock=Lock();self.state={}

    def due(self,name,now):
        with self.lock:
            row=self.state.get(name)
            return row is None or row['suspect'] or not 0<=now-row['time']<self.interval

    def reading(self,name):
        """The channel's last check {'state','size'[,'time']} (a copy), or None."""
        with self.lock:
            row=self.state.get(name)
            if row is None or row.get('size') is None:return None
            check={'state':row['state'],'size':row['size']}
            if row.get('wall') is not None:check['time']=row['wall']
            return check

    def record(self,name,state,now,size=None,wall=None):
        """now: the monotonic clock of the pace; wall: the measurement time (whole seconds)."""
        with self.lock:
            previous=self.state.get(name)
            # A black hole stays suspected until a check passes: an inconclusive check in between keeps the pace.
            suspect=state=='black-hole' or state!='ok' and previous is not None and previous['suspect']
            self.state[name]={'time':now,'state':state,'suspect':suspect,'size':size,'wall':wall}
            while len(self.state)>LIMIT:
                oldest=min(self.state,key=lambda item:(self.state[item]['time'],item))
                del self.state[oldest]


def read_mtu(device):
    try:return parse_mtu((SYS_NET/device/'mtu').read_text())
    except (OSError,ValueError):return None


def measure(binding,size,clock=time.monotonic,random=os.urandom):
    """All echoes of one check through one bound, marked raw socket; per-target outcomes."""
    probes=plan(size,random);outcomes=[None]*len(probes)
    with socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP) as sock:
        # A failure of either binding refuses the check (unavailable); no unbound retry exists.
        sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_BINDTODEVICE',25),binding['device'].encode('ascii')+b'\0')
        sock.setsockopt(socket.SOL_SOCKET,getattr(socket,'SO_MARK',36),binding['mark'])
        deadline=clock()+TIMEOUT
        for probe in probes:
            try:sock.sendto(probe['packet'],(probe['target'],0))
            except OSError as error:
                if error.errno not in REFUSED:raise  # refused by our own firewall: this echo is lost
        while None in outcomes:
            left=deadline-clock()
            if left<=0:break
            sock.settimeout(left)
            try:data,_=sock.recvfrom(4096)
            except socket.timeout:break
            for index,probe in enumerate(probes):
                if outcomes[index] is None:
                    outcome=classify(data,probe['identifier'],probe['sequence'],probe['payload'],probe['target'])
                    if outcome:outcomes[index]=outcome;break
    return group(probes,outcomes)


def run(schedule,profile_id,binding,now=None,mtu_reader=None,measurer=None,wall=None):
    """The check of one monitor probe: a fresh measurement when due, else the channel's last reading; None without
    a schedule, a valid binding or a readable MTU, and before the first reading."""
    if schedule is None or not binding_valid(binding):return None
    name=key(profile_id,binding);now=time.monotonic() if now is None else now
    if not schedule.due(name,now):return schedule.reading(name)
    size=probe_size((mtu_reader or read_mtu)(binding['device']))
    if size is None:return None
    wall=int(time.time()) if wall is None else wall
    try:state=verdict((measurer or measure)(binding,size))
    except (OSError,ValueError):state='unavailable'
    schedule.record(name,state,now,size,wall)
    return schedule.reading(name)


def apply(result,check):
    """Attach the check; a black hole fails an otherwise healthy probe with VPN-MTU."""
    if check is None:return result
    result['mtu_check']={key:check[key] for key in ('state','size','time') if key in check}
    if result.get('code') is None and check.get('state')=='black-hole':result['code']=CODE
    return result


def sanitize(value):
    """The published mtu_check of a status row (vendor_observation), or None."""
    if (not isinstance(value,dict) or value.get('state') not in STATES or type(value.get('size')) is not int
            or not MIN_SIZE<=value['size']<=MAX_SIZE):return None
    check={'state':value['state'],'size':value['size']}
    stamp=value.get('time')  # optional; an invalid one is dropped alone
    if type(stamp) is int and 0<=stamp<=TIME_MAX:check['time']=stamp
    return check
