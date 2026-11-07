"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
netjournal.py: the network-behaviour journal of the Auto pair (2.1.0-alpha9, owner design 04.11.2026).

Lua twin: lua/netjournal.lua (tests/advisor_cases.json, generated from this module by tests/gen_advisor_cases.py;
both runtimes produce the same records). Design note: docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md.

Single writer: the monitor (monitor.lua, or agent.monitor_loop in the Python fallback) calls observe() once per pass
with the samples of that pass; the advisor (advisor.py / lua/advisor.lua) only reads. Compact integers only.

One day = {'d': local day number, 'sw': failovers, 'rt': returns, 'us': unnecessary failovers,
           'ch': {tunnel id: tunnel record}}; tunnel record =
  'r'  role 0 primary (pair source) / 1 reserve (pair target)
  'n'  observations, 'f' failed observations (channel_model.observation: D or H)
  'lp' 288 five-minute slots, shorts*16384 + fails*128 + total (total <= 127): loss per 5 min and the number of
       short outages (<= SHORT s, mostly one failed check: loss, not an outage) that began in the slot
  'rs' / 'rn'  24 hours: sum of RTT ms of healthy samples / their count (RTT by hour of the day)
  'oh' outage-duration histogram, Fibonacci bins EDGES (bin i: EDGES[i] <= d < EDGES[i+1])
  'o'  natural outages [start second of the day, duration s, flags] flat: at most MAX_OUTAGES, of them at most
       MAX_SHORT short ones (heavy loss makes hundreds); 'ox' counts the rest (still in 'oh' and 'lp')
       flags: 1 the tunnel carried the traffic when the outage began, 2 it was the reserve
Natural duration of an outage (the tunnel's own failure, whatever Auto did meanwhile): the middle between the span
of its failed samples (lower bound) and the span between the healthy samples around it (upper bound), >= 1 s.

Unnecessary failover (reported, the advisor's cost replays the outages instead): a failover less than FLAP_RETURN s
after a return (flap), a failover without any failed sample of the primary in the last FALSE_LOOKBACK s (false), or
one whose primary outage ended less than COST s after it (the switch did not pay for itself).

Files: RAM <runtime>/netjournal-days.json (completed days, rewritten at the day change) and
<runtime>/netjournal-today.json (the current day + the open state, at most once a minute); flash
<persist>/netjournal.json (completed days) at most once a day - at the first pass of a new day (flash wear). After a
reboot the RAM files are empty and the flash copy is loaded; the part of the day before a power cut is lost.
"""
import json
import math

from channel_model import observation

VERSION=1
DAY=86400
SLOT=300
SLOTS=288
HOURS=24
RETENTION=30          # days kept (completed days, by day number)
EDGES=(1,2,3,5,8,13,21,34,55,89,144,233,377,610,987)
MAX_OUTAGES=100       # natural durations kept per tunnel and day; beyond them only the histogram ('ox' counts)
MAX_SHORT=60          # ... of them short ones (<= SHORT s)
SHORT=15
SHORTS=16384
MAX_TUNNELS=4
PACK=128
TOTAL_CAP=127
STALE=120             # a healthy sample older than this before the first failure bounds nothing (monitor gap)
FLAP_RETURN=600
FALSE_LOOKBACK=60
COST=20
RAM_SPACING=60        # seconds between two writes of the today file
DAYS_NAME='netjournal-days.json'
TODAY_NAME='netjournal-today.json'
FLASH_NAME='netjournal.json'


def floor(x):return int(math.floor(x))


def day_index(now,offset):
    return floor((now+offset)/DAY)


def new_day(day):
    return {'d':day,'sw':0,'rt':0,'us':0,'ch':{}}


def new_tunnel(role):
    return {'r':role,'n':0,'f':0,'lp':[0]*SLOTS,'rs':[0]*HOURS,'rn':[0]*HOURS,'oh':[0]*len(EDGES),'o':[],'ox':0}


def new():
    return {'v':VERSION,'days':[],'cur':None,'st':new_state(),'flash_day':None}


def new_state():
    return {'open':{},'ok':{},'fail':{},'route':None,'ret':None,'fo':None}


def number(v):
    return v if type(v) in (int,float) and math.isfinite(v) else None


def bin_of(d):
    index=0
    for i,edge in enumerate(EDGES):
        if d>=edge:index=i
    return index


def unpack(value):
    """(short outages, failed checks, checks) of one 'lp' slot."""
    return value//SHORTS,(value%SHORTS)//PACK,value%PACK


def _close(rec,o,ok_time,day,offset):
    start,prev,last,flags=o
    lower=last-start;upper=ok_time-prev
    d=max(1,floor((lower+upper)/2+0.5))
    second=floor(start+offset-day*DAY)
    rec['oh'][bin_of(d)]+=1
    if d<=SHORT:
        slot=min(SLOTS-1,max(0,floor(second/SLOT)))
        if rec['lp'][slot]//SHORTS<TOTAL_CAP:rec['lp'][slot]+=SHORTS
    if len(rec['o'])<3*(MAX_SHORT if d<=SHORT else MAX_OUTAGES):rec['o'].extend([second,d,flags])
    else:rec['ox']+=1
    return start,d


def observe(journal,samples,pair,route,now,offset):
    """One monitor pass. samples: the samples this pass added; pair: {'source','target'} ids; route: the observed
    route kind (route_history.observed_route). Returns 'rolled' when a day was completed (days file and flash due)."""
    rolled=False
    day=day_index(now,offset)
    cur=journal['cur']
    if cur is None or cur['d']<day:
        if cur is not None:
            journal['days'].append(cur);rolled=True
        journal['days']=[d for d in journal['days'] if d['d']>=day-RETENTION][-RETENTION:]
        cur=journal['cur']=new_day(day)
    day=cur['d']   # a clock that went back stays on the current day
    st=journal['st']
    source=pair.get('source') if isinstance(pair,dict) else None
    target=pair.get('target') if isinstance(pair,dict) else None
    roles={}
    if isinstance(source,str) and source:roles[source]=0
    if isinstance(target,str) and target and target!=source:roles[target]=1
    for key in ('open','ok','fail'):
        for identifier in [k for k in st[key] if k not in roles]:del st[key][identifier]
    carrying=source if route=='source' else target if route=='target' else None
    points=[s for s in samples if isinstance(s,dict) and s.get('id') in roles and number(s.get('time')) is not None]
    points.sort(key=lambda s:s['time'])
    for s in points:
        identifier=s['id'];obs=observation(s)
        if obs is None:continue
        rec=cur['ch'].get(identifier)
        if rec is None:
            if len(cur['ch'])>=MAX_TUNNELS:continue
            rec=cur['ch'][identifier]=new_tunnel(roles[identifier])
        rec['r']=roles[identifier]
        t=s['time'];second=t+offset-day*DAY
        slot=min(SLOTS-1,max(0,floor(second/SLOT)));hour=min(HOURS-1,max(0,floor(second/3600)))
        shorts,fails,total=unpack(rec['lp'][slot])
        if total<TOTAL_CAP:
            total+=1
            if obs>0:fails+=1
        rec['lp'][slot]=shorts*SHORTS+fails*PACK+total
        rec['n']+=1
        if obs==0:
            rtt=number(s.get('rtt_ms'))
            if rtt is not None and 0<=rtt<=60000:
                rec['rs'][hour]+=floor(rtt+0.5);rec['rn'][hour]+=1
            o=st['open'].pop(identifier,None)
            if o is not None:
                start,d=_close(rec,o,t,day,offset)
                fo=st['fo']
                if identifier==source and fo is not None and fo['us']==0 and start<=fo['t'] and start+d-fo['t']<COST:
                    cur['us']+=1;fo['us']=1
            st['ok'][identifier]=t
        else:
            rec['f']+=1
            st['fail'][identifier]=t
            o=st['open'].get(identifier)
            if o is None:
                prev=st['ok'].get(identifier)
                if prev is None or prev>t or t-prev>STALE:prev=t
                st['open'][identifier]=[t,prev,t,(1 if identifier==carrying else 0)+(2 if roles[identifier]==1 else 0)]
            else:o[2]=t
    if route in ('source','target'):
        last=st['route']
        if last=='source' and route=='target':
            cur['sw']+=1;us=0
            failed=st['fail'].get(source)
            if st['ret'] is not None and now-st['ret']<FLAP_RETURN:us=1
            elif source not in st['open'] and (failed is None or now-failed>FALSE_LOOKBACK):us=1
            cur['us']+=us;st['fo']={'t':now,'us':us}
        elif last=='target' and route=='source':
            cur['rt']+=1;st['ret']=now;st['fo']=None
        st['route']=route
    return rolled


def open_outages(journal):
    """Tunnel ids with an outage in progress (the advisor never changes settings during one)."""
    return sorted(journal['st']['open'])


def flash_due(journal,now,offset):
    """True when the completed days should reach flash now: at most once per local day."""
    return bool(journal['days']) and journal.get('flash_day')!=day_index(now,offset)


def encode(value):
    return json.dumps(value,ensure_ascii=True,separators=(',',':'),sort_keys=True)


def days_text(journal):
    return encode({'v':VERSION,'days':journal['days']})


def today_text(journal):
    return encode({'v':VERSION,'cur':journal['cur'],'st':journal['st'],'flash_day':journal.get('flash_day')})


def flash_text(journal,now,offset):
    return encode({'v':VERSION,'days':journal['days'],'saved_day':day_index(now,offset)})


def _valid_day(d):
    return (isinstance(d,dict) and type(d.get('d')) is int and isinstance(d.get('ch'),dict)
            and all(type(d.get(k)) is int for k in ('sw','rt','us'))
            and all(isinstance(r,dict) and isinstance(r.get('lp'),list) and len(r['lp'])==SLOTS
                    and isinstance(r.get('o'),list) and isinstance(r.get('oh'),list) and len(r['oh'])==len(EDGES)
                    and isinstance(r.get('rs'),list) and len(r['rs'])==HOURS and isinstance(r.get('rn'),list) and len(r['rn'])==HOURS
                    for r in d['ch'].values()))


def load(days_raw,today_raw,flash_raw):
    """The journal from the RAM files (texts or None); without the RAM days file, the flash copy. Damaged parts are
    dropped (a fresh journal), never trusted."""
    journal=new()
    def parse(raw):
        try:value=json.loads(raw) if isinstance(raw,str) else None
        except ValueError:return None
        return value if isinstance(value,dict) and value.get('v')==VERSION else None
    days=parse(days_raw);source='ram'
    if days is None:
        days=parse(flash_raw);source='flash'
        if days is not None and type(days.get('saved_day')) is int:journal['flash_day']=days['saved_day']
    if days is not None and isinstance(days.get('days'),list):
        journal['days']=sorted([d for d in days['days'] if _valid_day(d)],key=lambda d:d['d'])[-RETENTION:]
    today=parse(today_raw)
    if today is not None and source=='ram':
        if _valid_day(today.get('cur')):journal['cur']=today['cur']
        st=today.get('st')
        if isinstance(st,dict) and all(isinstance(st.get(k),dict) for k in ('open','ok','fail')):journal['st']=st
        if type(today.get('flash_day')) is int:journal['flash_day']=today['flash_day']
    return journal


class Writer:
    """The monitor's side: observe + the RAM/flash write policy. io: read(path)->text|None,
    write_ram(path,text), write_flash(path,text)."""
    def __init__(self,io,runtime,persist):
        self.io=io;self.runtime=runtime;self.persist=persist
        self.journal=load(io.read(runtime+'/'+DAYS_NAME),io.read(runtime+'/'+TODAY_NAME),io.read(persist+'/'+FLASH_NAME))
        self.today_at=None;self.flash_writes=0
        if io.read(runtime+'/'+DAYS_NAME) is None:io.write_ram(runtime+'/'+DAYS_NAME,days_text(self.journal))

    def pass_(self,samples,pair,route,now,offset,clock):
        rolled=observe(self.journal,samples,pair,route,now,offset)
        if rolled:self.io.write_ram(self.runtime+'/'+DAYS_NAME,days_text(self.journal))
        if flash_due(self.journal,now,offset):
            self.journal['flash_day']=day_index(now,offset)
            self.io.write_flash(self.persist+'/'+FLASH_NAME,flash_text(self.journal,now,offset));self.flash_writes+=1
            rolled=True
        if rolled or self.today_at is None or clock-self.today_at>=RAM_SPACING:
            self.io.write_ram(self.runtime+'/'+TODAY_NAME,today_text(self.journal));self.today_at=clock
        return rolled
