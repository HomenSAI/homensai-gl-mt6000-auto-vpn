"""Deterministic synthetic network days for the network advisor tests (netjournal + advisor).

A day is a list of events of the primary (P) or the reserve (R):
  ('out', start_s, duration_s)          P outage (every check fails)
  ('loss', start_s, duration_s, pct)    P loses pct % of the checks (evenly spread, deterministic)
  ('rout', start_s, duration_s)         R outage while it carries the traffic (Auto is on the reserve meanwhile)
The monitor checks both tunnels every 10 s and every 4 s while the primary is failing (the dense pass). The route
follows a simple Auto: away 25 s into a primary outage, back 150 s after its end.
"""
import math

PRIMARY='wireguard:peer_1'
RESERVE='openvpn:1_2'
PAIR={'source':PRIMARY,'target':RESERVE}
BASE=1793318400.0      # 2026-10-28 00:00 UTC (a Wednesday); the tests use offset 0 unless stated


def health(fail):
    return ({'code':'VPN-003','dns_ok':True,'https_success':0} if fail else {'code':None,'dns_ok':True,'https_success':3})


def failing(events,who,t):
    for e in events:
        if e[0]=='out' and who=='P' and e[1]<=t<e[1]+e[2]:return True
        if e[0]=='rout' and who=='R' and e[1]<=t<e[1]+e[2]:return True
        if e[0]=='loss' and who=='P' and e[1]<=t<e[1]+e[2]:
            k=int((t-e[1])//10)
            if math.floor((k+1)*e[3]/100.0)>math.floor(k*e[3]/100.0):return True
    return False


def route(events,t):
    for e in events:
        if e[0]=='out' and e[2]>=25 and e[1]+25<=t<e[1]+e[2]+150:return 'target'
        if e[0]=='rout' and e[1]<=t<e[1]+e[2]+60:return 'target'
    return 'source'


def day_passes(day_start,events,step=10.0):
    """[(now, samples, route)] of one day; a dense extra check 4 s after every failed primary check."""
    out=[]
    t=0.0
    while t<86400:
        samples=[]
        for who,identifier in (('P',PRIMARY),('R',RESERVE)):
            fail=failing(events,who,t)
            s=dict(health(fail),id=identifier,time=day_start+t+(0.0 if who=='P' else 0.5),rtt_ms=None if fail else 40+int(t//3600),dense=False)
            samples.append(s)
            if who=='P' and fail:
                for extra in (4.0,):
                    f2=failing(events,'P',t+extra)
                    samples.append(dict(health(f2),id=identifier,time=day_start+t+extra,rtt_ms=None if f2 else 40,dense=True))
        out.append((day_start+t+8.0,samples,route(events,t)))
        t+=step
    return out


def build(days_events,offset=0,base=BASE):
    """A journal filled by netjournal.observe from the passes of the given days (list of event lists)."""
    import netjournal as J
    journal=J.new()
    for i,events in enumerate(days_events):
        for now,samples,kind in day_passes(base+i*86400-offset,events):
            J.observe(journal,samples,PAIR,kind,now,offset)
    # one pass of the next day completes the last day
    J.observe(journal,[],PAIR,'source',base+len(days_events)*86400-offset+1,offset)
    return journal


SCENARIOS={
    # quiet network: a couple of short blips a day
    'quiet':[[('out',3600*h,6)] for h in (2,9)],
    # long outages and heavy loss: leave fast
    'long':[('out',3600*h+600,120) for h in (1,5,9,13,17,21)]+[('loss',3600*h,1200,40) for h in (3,15)],
    # 20-30 s blips: the calm end saves unnecessary switches
    'blips':[('out',3600*h+1800,22+(h%3)*3) for h in range(0,24,2)],
    # flaps 60/120 x 4 twice a day and a failing reserve
    'flappy':[('out',7200+180*k,60) for k in range(4)]+[('out',50000+180*k,60) for k in range(4)]+[('rout',30000,200)],
}


def scenario_days(name,days=7):
    events=SCENARIOS[name]
    if name=='quiet':return [[e for day in events for e in day]]*days
    return [list(events) for _ in range(days)]
