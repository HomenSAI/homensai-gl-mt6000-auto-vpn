"""Owner-selected probe level (1-5) and the optional automatic boost.

Level 1 probes rarely (least router load, slowest failure detection), level 5
probes as often as the monitor allows. The boost temporarily switches to the
fastest cadence while a selected channel fails, so a reliable pair is checked
rarely and a real failure is still confirmed quickly. Every level choice and
boost episode is recorded with its reason, result and code.

A passive suspicion (suspicion.SuspicionWatcher: a channel sends but receives
nothing, a dead WireGuard handshake, a vanished tunnel interface) starts a
dense episode at every level: an immediate full check, then full checks every
DENSE_INTERVAL seconds for both Auto channels until the suspect channel passes
again, fails CONFIRM_FAILURES times while the reserve is proven, Auto switches,
or DENSE_MAX passes. A suspicion is never a failure: Auto still switches only on
its own unchanged streak of full checks.
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
WATCHING=('OBSERVING','COMMITTED','DEGRADED-ON-RESERVE')  # Auto is watching: a failure here is real evidence
HISTORY_NAME='probe-history.json';STATE_NAME='probe-boost.json'
# Dense confirmation after a passive suspicion. Start-to-start spacing of full checks:
# three failed checks still span at least 2*DENSE_INTERVAL seconds of real outage.
DENSE_INTERVAL=4;DENSE_MAX=60;DENSE_GOOD=2
SUSPICION_REST=30  # per channel after an episode; doubles after each false alarm up to BOOST_HOLD
SUSPICION_REASONS=('rx-stall','wg-handshake-stale','link-missing')
CARRIED=('dense','suspicion_rest','streaks')  # survive the end of a boost episode


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


FORCED_BOOST_LEVELS=(1,2)  # overnight test 30 Oct 2026: level 1 without boost never confirmed a 3-minute failure


def boost_enabled(settings):
    if level(settings) in FORCED_BOOST_LEVELS:return True
    return settings.get('probe_boost') not in (False,'0')


def measure_interval(settings):
    return _int(settings.get('measure_interval'),30,300) or LEVELS[level(settings)][1]


def measure_valid_for(interval):
    """A ping/website result stays current for 1.5 cadences plus the probe budget."""
    return int(interval*3//2+15)


# Owner ping cadence (option ping_interval, seconds), separate from the probe level since 2.0.0-alpha14.
# 10 s .. 5 min in steps of 10 s; missing or invalid -> once a minute. The website check keeps measure_interval.
PING_INTERVAL_DEFAULT=60;PING_INTERVAL_MIN=10;PING_INTERVAL_MAX=300;PING_INTERVAL_STEP=10
PING_VALID_FLOOR=45  # the former fixed freshness window (30 s cadence x 1.5)


def ping_interval(settings):
    value=_int(settings.get('ping_interval'),PING_INTERVAL_MIN,PING_INTERVAL_MAX) if isinstance(settings,dict) else None
    return value if value is not None and value%PING_INTERVAL_STEP==0 else PING_INTERVAL_DEFAULT


def ping_valid_for(settings):
    """How long one ping answer stays current.

    An echo is only sent from a monitor pass, so answers are spaced by the owner interval or by the
    normal channel-check interval, whichever is longer. One answer stays current for 1.5 of that spacing
    plus the 15 s probe budget (the pass that sends the next echo may run late), never below the former
    fixed 45 s window. Highest value: 300 s -> 465 s, the bound the histories and the page accept.
    """
    spacing=max(ping_interval(settings),_int(settings.get('interval'),10,300) or 10)
    return max(PING_VALID_FLOOR,measure_valid_for(spacing))


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

    def dense(self,now=None):
        """The running dense-confirmation episode, or None (also once it outlived its bound)."""
        now=time.time() if now is None else now
        episode=self.state.get('dense')
        if not isinstance(episode,dict) or type(episode.get('until')) not in (int,float):return None
        return episode if now<=episode['until']+DENSE_INTERVAL else None

    def interval(self,settings,now=None):
        normal=_int(settings.get('interval'),10,300) or 10
        if self.dense(now):return min(normal,DENSE_INTERVAL)
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
        if self.state.get('rest_profile') and any(isinstance(r,dict) and r.get('id')==self.state['rest_profile'] and not failing(r) for r in rows):self.state.pop('rest_profile',None)
        if self.active():
            if native_state in TRANSITIONS:self.state['switched']=True
            if bad:
                failures=int(self.state.get('failures',0))+1;started=self.state.get('started',now)
                done=self.state.get('switched') or failures>CONFIRM_FAILURES  # the confirming failure still extends once
                self.state.update(failures=failures,last_code=bad[0].get('code') or ('DNS-001' if bad[0].get('dns_ok') is False else 'VPN-003'),
                                  until=self.state.get('until',0) if done else min(now+BOOST_HOLD,started+2*BOOST_HOLD))
            if not enabled or now>=self.state.get('until',0):
                result='switched' if self.state.get('switched') else 'failure-confirmed' if self.state.get('failures',0)>=CONFIRM_FAILURES else 'false-alarm'
                if not enabled:result='disabled'
                trigger=self.state.get('trigger') or {}
                recorded.append(self.record({'kind':'boost-end','level':chosen,'interval':interval,'measure_interval':measure,
                    'boost_enabled':enabled,'profile':trigger.get('profile'),'role':trigger.get('role'),
                    'code':self.state.get('last_code') or trigger.get('code'),'result':result,
                    'failures':int(self.state.get('failures',0)),'duration':round(max(0,now-self.state.get('started',now))),
                    'boost_interval':BOOST_INTERVAL},now))
                # No new episode for one hold, and none for the same channel until it passed a check again.
                carried={key:self.state[key] for key in CARRIED if key in self.state}
                self.state=dict(carried,active=False,level=current,rest_until=now+BOOST_HOLD,rest_profile=trigger.get('profile'))
        elif enabled and bad and native_state in WATCHING and now>=self.state.get('rest_until',0) and bad[0].get('id')!=self.state.get('rest_profile'):
            row=bad[0];code=row.get('code') or ('DNS-001' if row.get('dns_ok') is False else 'VPN-003')
            trigger={'profile':row.get('id'),'role':selected.get(row.get('id')),'code':code}
            self.state.update(active=True,started=now,until=now+BOOST_HOLD,failures=1,switched=native_state in TRANSITIONS,
                              trigger=trigger,last_code=code)
            recorded.append(self.record({'kind':'boost-start','level':chosen,'interval':interval,'measure_interval':measure,
                'boost_enabled':True,'profile':trigger['profile'],'role':trigger['role'],'code':code,'result':'started',
                'boost_interval':BOOST_INTERVAL},now))
        recorded.extend(self._dense_observe(settings,rows,pair,native_state,now))
        try:self.atomic_json(self.runtime/STATE_NAME,self.state)
        except (OSError,ValueError):pass
        return recorded

    def _row(self,settings,kind,episode,now,**fields):
        return self.record(dict({'kind':kind,'level':level(settings),'interval':_int(settings.get('interval'),10,300) or 10,
            'measure_interval':measure_interval(settings),'boost_enabled':boost_enabled(settings),
            'profile':episode.get('profile'),'role':episode.get('role'),'reason':episode.get('reason'),
            'dense_interval':DENSE_INTERVAL},**fields),now)

    def suspect(self,settings,suspicions,pair,native_state,now=None):
        """A passive suspicion asks for an immediate full check and dense confirmation.

        Returns True when a new episode started (the caller then starts a full pass at once).
        It never records a failure and never changes what Auto needs to switch.
        """
        now=time.time() if now is None else now
        if self.dense(now) or native_state not in WATCHING or not isinstance(pair,dict):return False
        roles={pair.get('source'):'source',pair.get('target'):'target'}
        rest=self.state.get('suspicion_rest') if isinstance(self.state.get('suspicion_rest'),dict) else {}
        streaks=self.state.get('streaks') if isinstance(self.state.get('streaks'),dict) else {}
        for item in suspicions if isinstance(suspicions,list) else []:
            if not isinstance(item,dict) or item.get('reason') not in SUSPICION_REASONS:continue
            profile=item.get('profile')
            if profile is None or profile not in roles:continue
            held=rest.get(profile) if isinstance(rest.get(profile),dict) else {}
            if now<held.get('until',0):continue
            # Already proven failed by full checks: a suspicion adds nothing; the boost keeps watching it.
            if int((streaks.get(profile) or {}).get('failures',0))>=CONFIRM_FAILURES:continue
            evidence={k:v for k,v in (item.get('evidence') or {}).items() if k in ('stalled_s','tx_packets','handshake_age_s')}
            episode={'profile':profile,'role':roles[profile],'reason':item['reason'],'evidence':evidence,
                     'started':now,'until':now+DENSE_MAX,'native_state':native_state,
                     'checks':0,'failures':0,'good':0,'reserve_good':0,'last_code':None}
            self.state['dense']=episode
            self._row(settings,'suspicion-start',episode,now,evidence=evidence,code=None,result='started')
            try:self.atomic_json(self.runtime/STATE_NAME,self.state)
            except (OSError,ValueError):pass
            return True
        return False

    def _dense_observe(self,settings,rows,pair,native_state,now):
        recorded=[]
        streaks=self.state.get('streaks') if isinstance(self.state.get('streaks'),dict) else {}
        ids=[pair.get('source'),pair.get('target')] if isinstance(pair,dict) else []
        for row in rows:
            if isinstance(row,dict) and row.get('id') is not None and row.get('id') in ids:
                previous=streaks.get(row['id']) if isinstance(streaks.get(row['id']),dict) else {}
                streaks[row['id']]={'failures':int(previous.get('failures',0))+1 if failing(row) else 0,'time':now}
        self.state['streaks']={key:value for key,value in streaks.items() if key in ids}
        episode=self.state.get('dense')
        if not isinstance(episode,dict):return recorded
        if not self.dense(now):episode['until']=now  # outlived its bound (monitor passes failed): close it now
        suspect=episode.get('profile');reserve=next((i for i in ids if i is not None and i!=suspect),None)
        row=next((r for r in rows if isinstance(r,dict) and r.get('id')==suspect),None)
        other=next((r for r in rows if isinstance(r,dict) and reserve is not None and r.get('id')==reserve),None)
        for key in ('checks','failures','good','reserve_good'):episode[key]=int(episode.get(key) or 0)
        if row is not None:
            episode['checks']+=1
            if failing(row):
                episode['failures']+=1;episode['good']=0
                episode['last_code']=row.get('code') or ('DNS-001' if row.get('dns_ok') is False else 'VPN-003')
            else:
                episode['good']+=1;episode['failures']=0
        if other is not None:episode['reserve_good']=0 if failing(other) else episode['reserve_good']+1
        switched=native_state in TRANSITIONS or (native_state!=episode.get('native_state')
                                                 and native_state in ('COMMITTED','DEGRADED-ON-RESERVE'))
        result=None
        if switched:result='switched'
        elif episode['good']>=DENSE_GOOD:result='false-alarm'
        elif episode['failures']>=CONFIRM_FAILURES and (reserve is None or episode['reserve_good']>=DENSE_GOOD):result='failure-confirmed'
        elif native_state not in WATCHING:result='cancelled'
        elif now>=episode.get('until',0):result='failure-confirmed' if episode['failures']>=CONFIRM_FAILURES else 'expired'
        if result is None:return recorded
        rest=self.state.get('suspicion_rest') if isinstance(self.state.get('suspicion_rest'),dict) else {}
        held=rest.get(suspect) if isinstance(rest.get(suspect),dict) else {}
        alarms=int(held.get('false_alarms',0))+1 if result=='false-alarm' else 0
        pause=min(SUSPICION_REST*2**max(0,alarms-1),BOOST_HOLD)
        rest[suspect]={'until':now+pause,'false_alarms':alarms}
        self.state['suspicion_rest']={key:value for key,value in rest.items() if key in ids}
        self.state.pop('dense',None)
        recorded.append(self._row(settings,'suspicion-end',episode,now,result=result,code=episode.get('last_code'),
            checks=episode['checks'],failures=episode['failures'],reserve_good=episode['reserve_good'],
            duration=round(max(0,now-episode.get('started',now))),rest=pause))
        return recorded

    def public(self,settings,now=None):
        now=time.time() if now is None else now
        chosen=level(settings);trigger=self.state.get('trigger') or {}
        return {'level':chosen,'interval':_int(settings.get('interval'),10,300) or 10,'measure_interval':measure_interval(settings),
                'boost_enabled':boost_enabled(settings),'boost_active':self.active(),
                'boost_until':self.state.get('until') if self.active() else None,
                'boost_trigger':trigger if self.active() else None,
                'effective_interval':self.interval(settings,now),'effective_measure_interval':self.measure(settings),
                'ping_interval':ping_interval(settings),'ping_valid_for':ping_valid_for(settings),
                'effective_ping_interval':max(ping_interval(settings),self.interval(settings,now)),
                'suspicion':({k:self.dense(now).get(k) for k in ('profile','role','reason','started','until')}
                             if self.dense(now) else None),'dense_interval':DENSE_INTERVAL,
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
            'scope':'owner probe-level choices, automatic boost and suspicion episodes recorded by the router'}
