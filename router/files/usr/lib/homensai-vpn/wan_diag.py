# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""WAN down versus tunnel down: a small Bayesian fault diagnosis (docs/architecture/GL-SENSORS-2026-11-04.ru.md, item 1).

Hypotheses (one world shared by both Auto channels):
  N       everything works
  TUNNEL  the primary tunnel (its server or the path to it) is down, the reserve works
  SERVER  the primary tunnel is up (fresh WireGuard keypair) but nothing passes beyond its server
  BOTH    both VPN channels are down while the WAN itself works (provider-wide or two failures)
  WAN     the router's own uplink is down (cable, Wi-Fi repeater, captive portal, ISP)
  DNS     DNS fails through both channels while HTTPS works
Evidence (each one optional; 'unknown' or absent = no factor at all):
  underlay  own ICMP echo through the WAN device, outside the tunnels ('ok' | 'fail'), see Underlay
  link      the configured WAN-zone link state (status.uplink_observation: 'up' | 'down'); link up is no Internet proof
  kmwan     the GL multi-WAN verdict read from /proc/gl-kmwan/config ('online' | 'offline')
  portal    the GL repeater reports a captive portal ('yes' | 'no')
  primary   the newest fresh full probe of the primary ('ok' | 'bad' | 'dns')
  reserve   the same for the reserve
  wg        the newest WireGuard kernel event of the primary device within WG_WINDOW ('giveup' | 'timeout' | 'created')
Safety rules on top of the posterior (never from the posterior alone):
  hold    only when the WAN is proven down: P(WAN) >= HOLD_P AND hard WAN evidence (underlay fail, link down or kmwan
          offline) AND the primary failing AND the reserve not healthy. Switching to the other VPN cannot help then;
          Auto keeps its attempt budget, cooldown and dwell (failure_diagnosis.diagnose returns WAN-DOWN).
  hasten  only when the WAN is proven up (underlay ok or kmwan online) AND the primary failing AND the reserve
          healthy AND P(WAN) <= HASTEN_WAN_MAX: the monitor starts the dense confirmation of the primary at once (one
          failed probe is weak evidence against a healthy world, so this only asks for more probes, never a switch).
  Without WAN evidence both stay false: the previous behaviour, exactly.
Pure functions, no I/O. Lua twin: lua/wan_diag.lua (shared cases router/tests/gl_sensors_cases.json).
"""
import math

HYPOTHESES=('N','TUNNEL','SERVER','BOTH','WAN','DNS')
# Prior: a healthy world almost always; WAN outages are the most frequent fault on a Wi-Fi-uplinked MT3000.
PRIOR=(0.968,0.012,0.004,0.004,0.010,0.002)
#                         N      TUNNEL  SERVER  BOTH    WAN     DNS
LIKELIHOOD={
    'underlay':{'ok':  (0.98,  0.98,   0.98,   0.97,   0.02,   0.97),
                'fail':(0.02,  0.02,   0.02,   0.03,   0.98,   0.03)},
    'link':    {'up':  (0.999, 0.999,  0.999,  0.999,  0.4,    0.999),
                'down':(0.001, 0.001,  0.001,  0.001,  0.6,    0.001)},
    'kmwan':   {'online': (0.99, 0.99, 0.99,   0.99,   0.1,    0.99),
                'offline':(0.01, 0.01, 0.01,   0.01,   0.9,    0.01)},
    'portal':  {'yes': (0.001, 0.001,  0.001,  0.001,  0.3,    0.001),
                'no':  (0.999, 0.999,  0.999,  0.999,  0.7,    0.999)},
    'primary': {'ok':  (0.97,  0.03,   0.03,   0.03,   0.01,   0.05),
                'bad': (0.02,  0.95,   0.9,    0.95,   0.97,   0.1),
                'dns': (0.01,  0.02,   0.07,   0.02,   0.02,   0.85)},
    'reserve': {'ok':  (0.97,  0.95,   0.95,   0.03,   0.01,   0.05),
                'bad': (0.02,  0.03,   0.03,   0.95,   0.97,   0.1),
                'dns': (0.01,  0.02,   0.02,   0.02,   0.02,   0.85)},
    'wg':      {'giveup': (0.001, 0.3,  0.01,   0.3,    0.3,    0.001),
                'timeout':(0.01,  0.4,  0.02,   0.4,    0.4,    0.01),
                'created':(0.05,  0.01, 0.3,    0.01,   0.01,   0.05)},
}
ORDER=('underlay','link','kmwan','portal','primary','reserve','wg')
HOLD_P=0.95
HASTEN_WAN_MAX=0.01  # hasten: the WAN is ruled out (posterior), the reserve answers, the primary just failed
CONFIDENT=0.8
CODES={'TUNNEL':'DIAG-TUNNEL-DOWN','SERVER':'DIAG-VPN-SERVER','BOTH':'DIAG-VPN-BOTH-DOWN','WAN':'DIAG-WAN-SUSPECT',
       'DNS':'DIAG-DNS-FAILED'}
HOLD_CODE='WAN-DOWN'
RECOVER_CODE='WAN-RECOVERING'
UNSURE_CODE='DIAG-UNSURE'
OPTION='wan_sensor'
GRACE_OPTION='wan_recover_grace'
GRACE_DEFAULT=30
GRACE_MAX=120
BAD_CODES=frozenset(('VPN-001','VPN-003','VPN-MTU'))
WG_WINDOW=120  # seconds: an older WireGuard event says nothing about now


def posterior(evidence):
    """P(H | evidence) for every hypothesis, in HYPOTHESES order; renormalised after every factor."""
    p=list(PRIOR)
    evidence=evidence if isinstance(evidence,dict) else {}
    for key in ORDER:
        row=LIKELIHOOD[key].get(evidence.get(key)) if isinstance(evidence.get(key),str) else None
        if row is None:continue
        p=[p[i]*row[i] for i in range(len(p))]
        total=0.0
        for value in p:total=total+value
        p=[value/total for value in p]
    return p


def permille(value):
    return int(math.floor(value*1000+0.5))


def diagnose(evidence,enabled=True):
    """The verdict, its confidence (per mille), the hold/hasten flags and the published code."""
    evidence=evidence if isinstance(evidence,dict) else {}
    p=posterior(evidence)
    best=0
    for index in range(1,len(p)):
        if p[index]>p[best]:best=index
    verdict=HYPOTHESES[best]
    get=lambda key:evidence.get(key) if isinstance(evidence.get(key),str) else None
    wan_proof=get('underlay')=='fail' or get('link')=='down' or get('kmwan')=='offline'
    up_proof=get('underlay')=='ok' or get('kmwan')=='online'
    hold=bool(enabled) and p[4]>=HOLD_P and wan_proof and get('primary')=='bad' and get('reserve')!='ok'
    hasten=bool(enabled) and not hold and up_proof and get('primary')=='bad' and get('reserve')=='ok' and p[4]<=HASTEN_WAN_MAX
    if hold:code=HOLD_CODE
    elif p[best]<CONFIDENT:code=UNSURE_CODE
    else:code=CODES.get(verdict)
    return {'verdict':verdict,'confidence':permille(p[best]),'hold':hold,'hasten':hasten,'code':code,
            'posterior':{name:permille(p[i]) for i,name in enumerate(HYPOTHESES)},'wan_proof':wan_proof,'up_proof':up_proof}


def channel_state(row,now,age):
    """'ok' | 'bad' | 'dns' | 'unknown' from one published probe row (agent.probe codes)."""
    if not isinstance(row,dict):return 'unknown'
    stamp=row.get('time')
    if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<=now-stamp<=age:return 'unknown'
    code=row.get('code')
    if code in BAD_CODES:return 'bad'
    if code=='DNS-001':return 'dns'
    successes=row.get('https_success')
    if code is None and row.get('dns_ok') is True and type(successes) is int and successes>=2:return 'ok'
    return 'unknown'


def evidence(rows,pair,now,age,uplink=None,underlay=None,kmwan=None,portal=None,wg=None):
    """The evidence dict from the published rows of one pass and the sensors (each value or None)."""
    by_id={}
    for row in rows if isinstance(rows,list) else []:
        if isinstance(row,dict) and isinstance(row.get('id'),str):by_id[row['id']]=row
    pair=pair if isinstance(pair,dict) else {}
    found={'primary':channel_state(by_id.get(pair.get('source')),now,age),
           'reserve':channel_state(by_id.get(pair.get('target')),now,age)}
    if isinstance(uplink,dict):
        stamp=uplink.get('time')
        if type(stamp) in (int,float) and math.isfinite(stamp) and 0<=now-stamp<=age:
            found['link']={'DOWN':'down','LINK-UP':'up'}.get(uplink.get('state'),'unknown')
    for key,value,allowed in (('underlay',underlay,('ok','fail')),('kmwan',kmwan,('online','offline')),
                              ('portal',portal,('yes','no')),('wg',wg,('giveup','timeout','created'))):
        if value in allowed:found[key]=value
    return found


def kmwan_verdict(text):
    """/proc/gl-kmwan/config: GL's own LED daemon reads 'online' in it (usr/bin/gl_led:72). The exact format is not
    published: only an explicit word counts; anything else is unknown."""
    if not isinstance(text,str) or not text:return None
    lowered=text.lower()
    if 'online' in lowered:return 'online'
    if 'offline' in lowered:return 'offline'
    return None


def portal_verdict(value):
    """`ubus call repeater status` decoded: portal true/false (gl_led:73-78)."""
    if not isinstance(value,dict):return None
    if value.get('portal') is True:return 'yes'
    if value.get('portal') is False:return 'no'
    return None


def grace_seconds(settings):
    value=settings.get(GRACE_OPTION) if isinstance(settings,dict) else None
    if type(value) is int and 0<=value<=GRACE_MAX:return value
    return GRACE_DEFAULT


def enabled(settings):
    return not (isinstance(settings,dict) and settings.get(OPTION) is False)


class Underlay:
    """Own ICMP echo through the WAN device (SO_BINDTODEVICE, no tunnel), low rate.

    A failure only counts after this device answered at least once (calibrated): a firewall or provider that never
    lets the echo through stays 'unknown', never 'fail'. 'fail' needs FAIL_N failures in a row over at least two
    targets; 'ok' a reply within OK_AGE seconds and no failure since; older than STALE: unknown.
    """
    TARGETS=('1.1.1.1','8.8.8.8','9.9.9.9','208.67.222.222')  # GL kmwan/glconfig track_ip (etc/config/kmwan)
    FAIL_N=3
    OK_AGE=30
    STALE=60
    IDLE=10    # seconds between echoes while both channels look healthy
    ALERT=2    # while a channel is failing or the WAN is suspected

    def __init__(self):
        self.device=None;self.reset()

    def reset(self):
        self.calibrated=False;self.fails=0;self.fail_targets=[];self.last_ok=None;self.last_at=None;self.sent=0

    def bind(self,device):
        if device!=self.device:
            self.device=device;self.reset()

    def target(self):
        return self.TARGETS[self.sent%len(self.TARGETS)]

    def due(self,now,alert):
        if self.device is None:return False
        return self.last_at is None or now-self.last_at>=(self.ALERT if alert else self.IDLE)

    def record(self,ok,target,now):
        self.last_at=now;self.sent+=1
        if ok:
            self.calibrated=True;self.fails=0;self.fail_targets=[];self.last_ok=now
        else:
            self.fails+=1
            if target not in self.fail_targets:self.fail_targets.append(target)

    def state(self,now):
        if self.device is None or self.last_at is None or now-self.last_at>self.STALE or now<self.last_at:return None
        if self.calibrated and self.fails>=self.FAIL_N and len(self.fail_targets)>=2:return 'fail'
        if self.fails==0 and self.last_ok is not None and 0<=now-self.last_ok<=self.OK_AGE:return 'ok'
        return None

    def public(self,now):
        return {'device':self.device,'state':self.state(now) or 'unknown','calibrated':self.calibrated,'fails':self.fails,
                'age_s':None if self.last_at is None else int(math.floor(max(0,now-self.last_at)))}


class Tracker:
    """Hold while the WAN is proven down; after it comes back, WAN-RECOVERING until the primary has a healthy sample
    newer than the return or `grace` seconds passed (a reserve that recovers a few seconds earlier than the primary
    is no reason to switch). restored=True once, on the pass the WAN came back (the monitor starts a pass now)."""

    def __init__(self):
        self.down_since=None;self.up_at=None

    def update(self,diagnosis,now,primary_ok_at,grace):
        restored=False
        if diagnosis.get('hold'):
            if self.down_since is None:self.down_since=now
            self.up_at=None
            return {'hold':True,'recovering':False,'restored':False,'code':HOLD_CODE,'down_since':self.down_since,'up_at':None}
        if self.down_since is not None:
            self.down_since=None;self.up_at=now;restored=True
        recovering=False
        if self.up_at is not None:
            healthy_after=type(primary_ok_at) in (int,float) and primary_ok_at>self.up_at
            if grace>0 and 0<=now-self.up_at<grace and not healthy_after:recovering=True
            else:self.up_at=None
        return {'hold':recovering,'recovering':recovering,'restored':restored,
                'code':RECOVER_CODE if recovering else diagnosis.get('code'),'down_since':None,'up_at':self.up_at}
