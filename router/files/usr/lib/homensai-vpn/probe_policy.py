"""Owner-selected probe level (1-5) and the optional automatic boost.

Level 1 probes rarely (least router load, slowest failure detection), level 5
probes as often as the monitor allows. The boost temporarily switches to the
fastest cadence while a selected channel fails, so a reliable pair is checked
rarely and a real failure is still confirmed quickly. Every level choice and
boost episode is recorded with its reason, result and code.
"""
import json
import math
import time

# level: (health check interval s, ping/website interval s)
LEVELS={1:(60,300),2:(30,120),3:(20,60),4:(15,45),5:(10,30)}
DEFAULT_LEVEL=5  # legacy installations keep their previous fixed cadence
BOOST_INTERVAL=10;BOOST_MEASURE=30;BOOST_HOLD=600
CONFIRM_FAILURES=3  # same count the pair controller needs for a failure streak
HISTORY_LIMIT=500
TRANSITIONS=('ARMED','APPLYING','WAIT-CLIENT','RESTORING','COMMITTED')
HISTORY_NAME='probe-history.json';STATE_NAME='probe-boost.json'


def _int(value,low,high):
    if isinstance(value,str) and value.isdigit():value=int(value)
    return value if type(value) is int and low<=value<=high else None


def level(settings):
    chosen=_int(settings.get('probe_level'),1,5)
    if chosen:return chosen
    interval=_int(settings.get('interval'),10,300) or 10
    for number in (5,4,3,2):
        if interval<=LEVELS[number][0]:return number
    return 1


def boost_enabled(settings):
    return settings.get('probe_boost') not in (False,'0')


def measure_interval(settings):
    return _int(settings.get('measure_interval'),30,300) or LEVELS[level(settings)][1]


def measure_valid_for(interval):
    """A ping/website result stays current for 1.5 cadences plus the probe budget."""
    return int(interval*3//2+15)


RESPONSE_METRICS={'icmp-1.1.1.1':'1.1.1.1','icmp-8.8.8.8':'8.8.8.8','icmp-9.9.9.9':'9.9.9.9','websites':None}
DEFAULT_RESPONSE='icmp-1.1.1.1'  # ping: light on the router, best for comparing the two channels


def response_metric(settings):
    value=settings.get('response_metric') if isinstance(settings,dict) else None
    return value if value in RESPONSE_METRICS else DEFAULT_RESPONSE


def failing(row):
    return (row.get('code') is not None or row.get('dns_ok') is False
            or not isinstance(row.get('https_success'),int) or row['https_success']<2)


class Booster:
    def __init__(self,runtime,persist,atomic_json,read_json):
        self.runtime=runtime;self.persist=persist;self.atomic_json=atomic_json;self.read_json=read_json
        try:state=read_json(runtime/STATE_NAME,{})
        except (OSError,ValueError):state={}
        self.state=state if isinstance(state,dict) and isinstance(state.get('active'),bool) else {'active':False}

    def active(self):return self.state.get('active') is True

    def interval(self,settings):
        normal=_int(settings.get('interval'),10,300) or 10
        return min(normal,BOOST_INTERVAL) if self.active() else normal

    def measure(self,settings):
        normal=measure_interval(settings)
        return min(normal,BOOST_MEASURE) if self.active() else normal

    def _history(self):
        try:rows=self.read_json(self.persist/HISTORY_NAME,[])
        except (OSError,ValueError):rows=[]
        return [row for row in rows if isinstance(row,dict) and type(row.get('sequence')) is int] if isinstance(rows,list) else []

    def record(self,row,now):
        rows=self._history()
        row=dict(row,time=now,sequence=(rows[-1]['sequence']+1) if rows else 1)
        rows=(rows+[row])[-HISTORY_LIMIT:]
        try:self.atomic_json(self.persist/HISTORY_NAME,rows)
        except (OSError,ValueError):pass
        return row

    def observe(self,settings,rows,pair,native_state,now=None):
        """One decision per monitor pass; returns the history rows it recorded."""
        now=time.time() if now is None else now
        recorded=[]
        chosen=level(settings);enabled=boost_enabled(settings)
        interval=_int(settings.get('interval'),10,300) or 10;measure=measure_interval(settings)
        current=[chosen,interval,measure,enabled]
        if self.state.get('level')!=current:
            recorded.append(self.record({'kind':'level','level':chosen,'interval':interval,'measure_interval':measure,
                                         'boost_enabled':enabled,'result':'applied','code':None},now))
            self.state['level']=current
        selected={pair.get('source'):'source',pair.get('target'):'target'} if isinstance(pair,dict) else {}
        bad=[row for row in rows if isinstance(row,dict) and row.get('id') in selected and row.get('id') is not None and failing(row)]
        if self.active():
            if native_state in TRANSITIONS:self.state['switched']=True
            if bad:
                self.state.update(until=now+BOOST_HOLD,failures=int(self.state.get('failures',0))+1,
                                  last_code=bad[0].get('code') or ('DNS-001' if bad[0].get('dns_ok') is False else 'VPN-003'))
            if not enabled or now>=self.state.get('until',0):
                result='switched' if self.state.get('switched') else 'failure-confirmed' if self.state.get('failures',0)>=CONFIRM_FAILURES else 'false-alarm'
                if not enabled:result='disabled'
                trigger=self.state.get('trigger') or {}
                recorded.append(self.record({'kind':'boost-end','level':chosen,'interval':interval,'measure_interval':measure,
                    'boost_enabled':enabled,'profile':trigger.get('profile'),'role':trigger.get('role'),
                    'code':self.state.get('last_code') or trigger.get('code'),'result':result,
                    'failures':int(self.state.get('failures',0)),'duration':round(max(0,now-self.state.get('started',now))),
                    'boost_interval':BOOST_INTERVAL},now))
                self.state={'active':False,'level':current}
        elif enabled and bad:
            row=bad[0];code=row.get('code') or ('DNS-001' if row.get('dns_ok') is False else 'VPN-003')
            trigger={'profile':row.get('id'),'role':selected.get(row.get('id')),'code':code}
            self.state.update(active=True,started=now,until=now+BOOST_HOLD,failures=1,switched=native_state in TRANSITIONS,
                              trigger=trigger,last_code=code)
            recorded.append(self.record({'kind':'boost-start','level':chosen,'interval':interval,'measure_interval':measure,
                'boost_enabled':True,'profile':trigger['profile'],'role':trigger['role'],'code':code,'result':'started',
                'boost_interval':BOOST_INTERVAL},now))
        try:self.atomic_json(self.runtime/STATE_NAME,self.state)
        except (OSError,ValueError):pass
        return recorded

    def public(self,settings,now=None):
        now=time.time() if now is None else now
        chosen=level(settings);trigger=self.state.get('trigger') or {}
        return {'level':chosen,'interval':_int(settings.get('interval'),10,300) or 10,'measure_interval':measure_interval(settings),
                'boost_enabled':boost_enabled(settings),'boost_active':self.active(),
                'boost_until':self.state.get('until') if self.active() else None,
                'boost_trigger':trigger if self.active() else None,
                'effective_interval':self.interval(settings),'effective_measure_interval':self.measure(settings),
                'boost_interval':BOOST_INTERVAL,'boost_hold':BOOST_HOLD,'levels':{str(k):list(v) for k,v in LEVELS.items()}}


def history_page(directory,arguments,read_json,now=None):
    """Statistics page for the probe-decision table, same cursor contract as other kinds."""
    now=time.time() if now is None else now
    try:rows=read_json(directory/HISTORY_NAME,[])
    except (OSError,ValueError):rows=[]
    rows=[row for row in rows if isinstance(row,dict) and type(row.get('sequence')) is int and isinstance(row.get('time'),(int,float))
          and math.isfinite(row['time'])] if isinstance(rows,list) else []
    last=rows[-1]['sequence'] if rows else 0
    until=arguments['until'] or last
    if until>last or arguments['after']>until:raise ValueError('STATISTICS-CURSOR')
    selected=[row for row in rows if arguments['after']<row['sequence']<=until][:100]
    more=len([row for row in rows if arguments['after']<row['sequence']<=until])>len(selected)
    return {'kind':'probe','until':until,'events':selected,'next_after':selected[-1]['sequence'] if selected else arguments['after'],
            'has_more':more,'summary':{'sequence':last,'rows':len(rows)},'as_of':now,
            'scope':'owner probe-level choices and automatic boost episodes recorded by the router'}
