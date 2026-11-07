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

Failure model (channel_model.py, option failure_model 'hmm'/'hmm-fast'; the monitor passes its per-channel view
as `models`): the model's suspicion (P(bad) >= 0.2 while it has not decided) of the channel carrying traffic also
starts an episode (reason 'model', same rest and doubling); an episode then runs until the model decided
('failure-confirmed'), until DENSE_GOOD good checks with the suspicion gone ('false-alarm'), a switch or DENSE_MAX
(study REPORT.ru.md 6.5). Without `models` (or with 'consecutive') the rules above are unchanged.
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
# Firmware wait (owner decision 01.11.2026, variant A): while the firmware rebuilds a tunnel of the Auto pair the
# vendor gate (failure_diagnosis.resolve_pair) needs two equal observations and a settle period after the last
# change. At probe level 1 the second observation came a whole interval later. While a pair tunnel is PENDING or
# inside its settle period, or Auto waits only for the firmware, passes run every WAIT_INTERVAL seconds; the gate
# rules are unchanged. At most WAIT_MAX seconds per wait, so a firmware that rebuilds forever does not keep it.
WAIT_INTERVAL=10;WAIT_MAX=600
WAIT_BLOCKERS=('VENDOR-SETTLING','PROFILE-IDENTITY-CHANGED','VENDOR-WORKER-BUSY','OBSERVATION-STALE')
# Dense confirmation after a passive suspicion. Start-to-start spacing of full checks:
# three failed checks still span at least 2*DENSE_INTERVAL seconds of real outage.
DENSE_INTERVAL=4;DENSE_MAX=60;DENSE_GOOD=2
TURBO_DENSE=3      # the expert opt-in only (dense_interval)
SUSPICION_REST=30  # per channel after an episode; doubles after each false alarm up to BOOST_HOLD
# 'wg-rekey' (wg_events.py) and 'wan-ok-tunnel-down' (wan_diag.py hasten): GL-SENSORS-2026-11-04, dense checks only
# 'cusum-loss' (cusum.py, heartbeat of the Lua monitor): dense checks only, see REST_BYPASS
SUSPICION_REASONS=('rx-stall','wg-handshake-stale','link-missing','wg-rekey','wan-ok-tunnel-down','cusum-loss')
# CUSUM-TRIGGER-2026-11-04.ru.md: at persistent partial loss an episode ends as a false alarm, the rest doubles 30 -> 600 s
# and the dense checks stop exactly when they are needed. These reasons pass a running rest, bounded by what the dense
# checks found (nothing else stops them on an ICMP-limited channel): state cusum_at {profile: {'at': end of the last such
# episode, 'clean': such episodes in a row in which no check failed}}. A failed dense check clears 'clean'; with
# clean <= CUSUM_FREE there is no gap, then CUSUM_GAP*2^(clean-CUSUM_FREE-1) seconds, at most CUSUM_GAP_MAX.
REST_BYPASS=('cusum-loss',)
CUSUM_FREE=2;CUSUM_GAP=60;CUSUM_GAP_MAX=600
CARRIED=('dense','suspicion_rest','streaks','cusum_at')  # survive the end of a boost episode


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


def dense_interval(settings):
    """DENSE_INTERVAL, or TURBO_DENSE with the expert opt-in (channel_model.heartbeat_k)."""
    from channel_model import heartbeat_k
    return TURBO_DENSE if heartbeat_k(settings) is not None else DENSE_INTERVAL


def wake_row(settings,rows,pair,now):
    """L1, event-driven wake (FAST-SWITCH-2026-11-04.ru.md): the row the monitor leaves in RAM right after it published a
    failed sample of an Auto channel, or None. Only a hint that a tick is worth running now: the tick reads and proves
    everything itself. Option auto_event_wake '0' turns it off (the 2 s tick stays)."""
    if isinstance(settings,dict) and settings.get('auto_event_wake') in (False,'0'):return None
    if not isinstance(pair,dict) or not isinstance(rows,list):return None
    ids=[pair.get(role) for role in ('source','target') if isinstance(pair.get(role),str)]
    for row in rows:
        if isinstance(row,dict) and row.get('id') in ids and failing(row):return {'reason':'sample','time':float(now),'id':row['id']}
    return None


def failing(row):
    return (row.get('code') is not None or row.get('dns_ok') is False
            or not isinstance(row.get('https_success'),int) or row['https_success']<2)


def cusum_gap(clean):
    """Seconds a REST_BYPASS reason waits after the end of the last such episode."""
    return 0 if clean<=CUSUM_FREE else min(CUSUM_GAP*2**(clean-CUSUM_FREE-1),CUSUM_GAP_MAX)


def firmware_wait(settings,observation,pair,native,now):
    """A tunnel of the Auto pair is PENDING or inside its settle period, or Auto waits only for the firmware."""
    from observation_freshness import settle_for
    if isinstance(native,dict):
        state=native.get('state');blockers=native.get('blockers')
        if state=='ARMED':return True
        if (state=='BLOCKED' and isinstance(blockers,list) and blockers
                and all(isinstance(x,str) and x in WAIT_BLOCKERS for x in blockers)):return True
    ids=set()
    if isinstance(pair,dict):
        for role in ('source','target'):
            if isinstance(pair.get(role),str):ids.add(pair[role])
    groups=observation.get('groups') if isinstance(observation,dict) else None
    if not ids or not isinstance(groups,list):return False
    settle=settle_for(settings)
    for group in groups:
        if not isinstance(group,dict) or group.get('current_profile') not in ids:continue
        if group.get('state')=='PENDING':return True
        changed=group.get('changed_at')
        if (group.get('state')=='SETTLED' and type(changed) in (int,float) and not isinstance(changed,bool)
                and 0<=now-changed<settle):return True
    return False


class Booster:
    def __init__(self,runtime,persist,atomic_json,read_json):
        self.runtime=runtime;self.persist=persist;self.atomic_json=atomic_json;self.read_json=read_json
        try:state=read_json(runtime/STATE_NAME,{})
        except (OSError,ValueError):state={}
        self.state=state if isinstance(state,dict) and isinstance(state.get('active'),bool) else {'active':False}

    def active(self):return self.state.get('active') is True

    def waiting(self,now=None):
        """True while a firmware wait (see WAIT_INTERVAL) runs and is younger than WAIT_MAX."""
        now=time.time() if now is None else now
        since=getattr(self,'wait_since',None)
        return since is not None and 0<=now-since<=WAIT_MAX

    def note_wait(self,settings,observation,pair,native,now=None):
        """Start, keep or end the firmware wait from this pass's vendor observation and Auto state (memory only)."""
        now=time.time() if now is None else now
        if firmware_wait(settings,observation,pair,native,now):
            if getattr(self,'wait_since',None) is None or now<self.wait_since:self.wait_since=now
        else:self.wait_since=None
        return self.waiting(now)

    def dense(self,now=None):
        """The running dense-confirmation episode, or None (also once it outlived its bound)."""
        now=time.time() if now is None else now
        episode=self.state.get('dense')
        if not isinstance(episode,dict) or type(episode.get('until')) not in (int,float):return None
        return episode if now<=episode['until']+DENSE_INTERVAL else None

    def interval(self,settings,now=None):
        normal=_int(settings.get('interval'),10,300) or 10
        if self.dense(now):return min(normal,dense_interval(settings))
        if self.waiting(now):return min(normal,WAIT_INTERVAL)
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

    def observe(self,settings,rows,pair,native_state,now=None,models=None):
        """One decision per monitor pass; returns the history rows it recorded.
        models: {profile id: channel_model.public view} of the pair channels (HMM modes), or None."""
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
        models=models if isinstance(models,dict) else None
        recorded.extend(self._dense_observe(settings,rows,pair,native_state,now,models))
        recorded.extend(self._model_suspect(settings,pair,native_state,now,models))
        try:self.atomic_json(self.runtime/STATE_NAME,self.state)
        except (OSError,ValueError):pass
        return recorded

    def _row(self,settings,kind,episode,now,**fields):
        return self.record(dict({'kind':kind,'level':level(settings),'interval':_int(settings.get('interval'),10,300) or 10,
            'measure_interval':measure_interval(settings),'boost_enabled':boost_enabled(settings),
            'profile':episode.get('profile'),'role':episode.get('role'),'reason':episode.get('reason'),
            'dense_interval':dense_interval(settings)},**fields),now)

    def suspect(self,settings,suspicions,pair,native_state,now=None,models=None):
        """A passive suspicion asks for an immediate full check and dense confirmation.

        Returns True when a new episode started (the caller then starts a full pass at once).
        It never records a failure and never changes what Auto needs to switch.
        models: as in observe(); a REST_BYPASS reason adds nothing once the failure model decided.
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
            bypass=item['reason'] in REST_BYPASS
            if bypass:
                view=models.get(profile) if isinstance(models,dict) else None
                if isinstance(view,dict) and view.get('failed') is True:continue
                last=self._forced(profile)
                bypass=now>=last['at']+cusum_gap(last['clean']) or now<last['at']
            if now<held.get('until',0) and not bypass:continue
            # Already proven failed by full checks: a suspicion adds nothing; the boost keeps watching it.
            if int((streaks.get(profile) or {}).get('failures',0))>=CONFIRM_FAILURES:continue
            evidence={k:v for k,v in (item.get('evidence') or {}).items() if k in ('stalled_s','tx_packets','handshake_age_s','losses','cause','event')}
            episode={'profile':profile,'role':roles[profile],'reason':item['reason'],'evidence':evidence,
                     'started':now,'until':now+DENSE_MAX,'native_state':native_state,
                     'checks':0,'failures':0,'good':0,'reserve_good':0,'last_code':None}
            self.state['dense']=episode
            if item['reason'] in REST_BYPASS:self._note_forced(profile,at=now,ids=roles)
            self._row(settings,'suspicion-start',episode,now,evidence=evidence,code=None,result='started')
            try:self.atomic_json(self.runtime/STATE_NAME,self.state)
            except (OSError,ValueError):pass
            return True
        return False

    def _forced(self,profile):
        """The channel's record of REST_BYPASS episodes (a damaged one counts as none)."""
        forced=self.state.get('cusum_at');record=forced.get(profile) if isinstance(forced,dict) else None
        at=record.get('at') if isinstance(record,dict) else None;clean=record.get('clean') if isinstance(record,dict) else None
        if type(at) not in (int,float) or type(clean) is not int or clean<0:return {'at':-math.inf,'clean':0}
        return {'at':at,'clean':clean}

    def _note_forced(self,profile,at=None,clean=None,ids=None):
        forced=self.state.get('cusum_at') if isinstance(self.state.get('cusum_at'),dict) else {}
        kept={key:value for key,value in forced.items() if ids is None or key in ids}
        last=self._forced(profile)
        kept[profile]={'at':last['at'] if at is None else at,'clean':last['clean'] if clean is None else clean}
        self.state['cusum_at']=kept

    def _model_suspect(self,settings,pair,native_state,now,models):
        """The failure model's suspicion of the channel carrying traffic starts a dense episode (reason 'model')."""
        if models is None or self.dense(now) or native_state not in WATCHING or not isinstance(pair,dict):return []
        role='source' if native_state=='OBSERVING' else 'target'
        profile=pair.get(role);view=models.get(profile)
        if profile is None or not isinstance(view,dict) or view.get('suspect') is not True or view.get('failed') is True:return []
        rest=self.state.get('suspicion_rest') if isinstance(self.state.get('suspicion_rest'),dict) else {}
        held=rest.get(profile) if isinstance(rest.get(profile),dict) else {}
        if now<held.get('until',0):return []
        evidence={'p_bad':view.get('p_bad'),'persist':view.get('persist')}
        episode={'profile':profile,'role':role,'reason':'model','evidence':evidence,'started':now,'until':now+DENSE_MAX,
                 'native_state':native_state,'checks':0,'failures':0,'good':0,'reserve_good':0,'last_code':None}
        self.state['dense']=episode
        return [self._row(settings,'suspicion-start',episode,now,evidence=evidence,code=None,result='started')]

    def _dense_observe(self,settings,rows,pair,native_state,now,models=None):
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
                episode['failures']+=1;episode['good']=0;episode['bad']=True
                episode['last_code']=row.get('code') or ('DNS-001' if row.get('dns_ok') is False else 'VPN-003')
                if self._forced(suspect)['clean']:self._note_forced(suspect,clean=0)
            else:
                episode['good']+=1;episode['failures']=0
        if other is not None:episode['reserve_good']=0 if failing(other) else episode['reserve_good']+1
        switched=native_state in TRANSITIONS or (native_state!=episode.get('native_state')
                                                 and native_state in ('COMMITTED','DEGRADED-ON-RESERVE'))
        result=None
        view=models.get(suspect) if models is not None else None
        if isinstance(view,dict):
            # the failure model decides the episode (it decides the switch too)
            decided=view.get('failed') is True
            if switched:result='switched'
            elif episode['good']>=DENSE_GOOD and view.get('suspect') is not True:result='false-alarm'
            elif decided and (reserve is None or episode['reserve_good']>=DENSE_GOOD):result='failure-confirmed'
            elif native_state not in WATCHING:result='cancelled'
            elif now>=episode.get('until',0):result='failure-confirmed' if decided else 'expired'
        elif switched:result='switched'
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
        if episode.get('reason') in REST_BYPASS:
            self._note_forced(suspect,at=now,clean=self._forced(suspect)['clean']+(0 if episode.get('bad') else 1))
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
                             if self.dense(now) else None),'dense_interval':dense_interval(settings),
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
