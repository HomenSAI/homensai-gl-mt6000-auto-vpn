"""MIT. Bounded persistent native transition history; no keys, tokens or exit IPs."""
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time

CODE=re.compile(r'^[A-Z0-9_-]{1,96}$')
PROFILE=re.compile(r'^(?:openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$')
METRICS=('attempts','committed','manual_attempts','manual_committed','trials_passed','rollbacks','returns','blocked_episodes','automatic_attempts','automatic_committed','server_switches','channel_switches','protocol_switches','rate_limited_episodes')
WEEK=7*86400


def transition_destination(value):
    role=('source' if value.get('state') in ('RESTORING','ROLLED-BACK') or value.get('state')=='STOPPED' and value.get('reason')=='OPERATOR-RETURN' else
          'target' if value.get('state') in ('APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE') else None)
    identifier=value.get(role) if role else None
    return role,identifier if isinstance(identifier,str) and PROFILE.fullmatch(identifier) else None


def clean_transition_latency(raw,value,now):
    """A saved observation at this event, never a lookup of today's ping."""
    role,identifier=transition_destination(value)
    if not identifier or not isinstance(raw,dict) or raw.get('profile')!=identifier or raw.get('metric')!='https-rtt-ms':return None
    stamp=raw.get('time');delay=raw.get('rtt_ms');interface=raw.get('interface');generation=raw.get('generation')
    if (type(stamp) not in (int,float) or not now-90<=stamp<=now+5
            or type(delay) not in (int,float) or not 0<=delay<=600000
            or not isinstance(interface,str) or not re.fullmatch(r'(?:wgclient|ovpnclient)[0-9]{1,4}',interface)
            or identifier.startswith('wireguard:')!=interface.startswith('wgclient')
            or not isinstance(generation,str) or not re.fullmatch('[a-f0-9]{32}',generation)):return None
    return {'profile':identifier,'metric':'https-rtt-ms','time':stamp,'rtt_ms':delay,'interface':interface,'generation':generation}


def capture_transition_latency(value,status,binding,now):
    role,identifier=transition_destination(value)
    if not identifier or not isinstance(status,dict) or not isinstance(binding,dict) or binding.get('id')!=identifier:return None
    stamp=status.get('time')
    if status.get('error') or status.get('rpc_error') or type(stamp) not in (int,float) or not now-90<=stamp<=now+5:return None
    rows=status.get('profiles',[])
    if not isinstance(rows,list):return None
    matched=[p for p in rows if isinstance(p,dict) and p.get('id')==identifier]
    if len(matched)!=1:return None
    p=matched[0]
    if (p.get('code') is not None or p.get('dns_ok') is not True or type(p.get('https_success')) is not int or p['https_success']<2
            or p.get('vendor_state')!='SETTLED' or p.get('protocol') not in ('wireguard','openvpn')
            or p.get('vendor_tunnel_id')!=p.get('protocol')+':'+str(p.get('interface'))
            or any(p.get(k)!=binding.get(k) for k in ('id','protocol','interface','vendor_tunnel_id','vendor_generation'))):return None
    return clean_transition_latency({'profile':identifier,'metric':'https-rtt-ms','time':p.get('time'),'rtt_ms':p.get('rtt_ms'),
        'interface':p.get('interface'),'generation':p.get('vendor_generation')},value,now)


class HistoryError(ValueError):
    pass


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def atomic(path,value):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():raise HistoryError('HISTORY-PATH')
    # A unique temporary name per writer: two writers can never truncate each other's file.
    fd,pending=tempfile.mkstemp(dir=str(path.parent),prefix='.'+path.name+'.',suffix='.pending')
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(encoded(value));stream.flush();os.fsync(stream.fileno())
        os.replace(pending,str(path))
    except BaseException:
        with contextlib.suppress(OSError):os.unlink(pending)
        raise
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


class History:
    RETENTION_BYTES=2*1024*1024
    def __init__(self,directory,limit=10000,detail_days=None):
        from retention_settings import configured_days
        self.detail_days=configured_days() if detail_days is None else detail_days
        if type(self.detail_days) is not int or not 1<=self.detail_days<=7:raise HistoryError("HISTORY-RETENTION")
        if type(limit) is not int or not 1<=limit<=10000:raise HistoryError('HISTORY-LIMIT')
        self.path=Path(directory)/'native-history.json'
        self.backup=self.path.with_name('native-history.backup.json')
        self.limit=limit
        self.restored=False
    def load(self):
        found=False
        for index,path in enumerate((self.path,self.backup)):
            try:
                if path.is_symlink():raise HistoryError('HISTORY-PATH')
                if not path.exists():continue
                found=True
                if path.stat().st_size>2300*1024:raise HistoryError('HISTORY-SIZE')
                envelope=json.loads(path.read_text(encoding='utf8'));data=envelope['data']
                if envelope.get('schema')!=1 or hashlib.sha256(encoded(data)).hexdigest()!=envelope.get('sha256'):raise HistoryError('HISTORY-CHECKSUM')
                if not isinstance(data.get('events'),list) or not isinstance(data.get('months'),dict) or type(data.get('sequence')) is not int or not 0<=data['sequence']<2**53:raise HistoryError('HISTORY-SCHEMA')
                for name,fields in (('active_attempt',{'id','episode','source','target','terminal'}),('retry_episode',{'id','source','trial','closed'})):
                    metadata=data.get(name,{})
                    if metadata=={}:continue
                    if not isinstance(metadata,dict) or set(metadata)!=fields:raise HistoryError('HISTORY-METADATA')
                    for key in ('id','episode'):
                        if key in fields and (type(metadata[key]) is not int or not 1<=metadata[key]<=data['sequence']):raise HistoryError('HISTORY-METADATA')
                    for key in ('source','target'):
                        identifier=metadata.get(key)
                        if identifier is not None and (not isinstance(identifier,str) or not PROFILE.fullmatch(identifier)):raise HistoryError('HISTORY-METADATA')
                    for key in ('terminal','trial','closed'):
                        if key in fields and type(metadata[key]) is not bool:raise HistoryError('HISTORY-METADATA')
                if len(data['events'])>10000 or len(data['months'])>1200 or not isinstance(data.get('days',{}),dict) or len(data.get('days',{}))>400:raise HistoryError('HISTORY-BOUNDS')
                if data.get('counter_version')==2:
                    for name in ('totals','counted'):
                        values=data.get(name)
                        if not isinstance(values,dict) or any(key not in METRICS or type(value) is not int or not 0<=value<2**53 for key,value in values.items()):raise HistoryError('HISTORY-COUNTERS')
                    for row in data['events']:
                        if 'counted_metrics' in row and (not isinstance(row['counted_metrics'],list) or len(row['counted_metrics'])>len(METRICS) or any(key not in METRICS for key in row['counted_metrics'])):raise HistoryError('HISTORY-COUNTERS')
                self.restored=bool(index);return data
            except (OSError,ValueError,KeyError,TypeError):continue
        if found:raise HistoryError('HISTORY-CORRUPT')
        return {'sequence':0,'events':[],'months':{},'last_key':None,'last_time':None,'timezone':'Europe/Berlin'}
    def envelope(self,data):
        return {'schema':1,'data':data,'sha256':hashlib.sha256(encoded(data)).hexdigest()}
    def correlate(self,data,item):
        """Public sequential IDs, never auth sessions or acknowledgement nonces.

        Episodes group retries on one source until a confirmed commit/trial end.
        This describes controller evidence, not independently measured LAN outages.
        """
        active=dict(data.get('active_attempt') or {})
        episode=dict(data.get('retry_episode') or {})
        prepare=item['state']=='ARMED' and 'TRIAL-PASSED' not in item['codes']
        starting=prepare or item['state']=='APPLYING'
        prior=data['events'][-1]['state'] if data['events'] else None
        if starting and (not active or active.get('terminal') or
                         prior not in ('ARMED','APPLYING') or
                         active.get('source')!=item.get('source') or
                         active.get('target')!=item.get('target')):
            sequence=data['sequence']+1
            if not episode or episode.get('closed') or episode.get('source')!=item.get('source') or episode.get('trial')!=item['trial']:
                episode=dict(id=sequence,source=item.get('source'),trial=item['trial'],closed=False)
            active=dict(id=sequence,episode=episode['id'],source=item.get('source'),
                        target=item.get('target'),terminal=False)
        if active and all(not item.get(k) or item[k]==active.get(k) for k in ('source','target')):
            item['attempt_id']=active['id'];item['retry_episode_id']=active['episode']
            if item['state'] in ('COMMITTED','ROLLED-BACK','BLOCKED','STOPPED','EXPIRED','STOPPED-ON-RESERVE') or 'TRIAL-PASSED' in item['codes']:
                active['terminal']=True
            if item['state']=='COMMITTED' or 'TRIAL-PASSED' in item['codes']:
                episode['closed']=True
        return active,episode
    def counters(self,data,item):
        """Count confirmed transactions once, not repeated status publications."""
        state=item['state'];identity=item.get('attempt_id',item['sequence']);recorded=[]
        seen=data.setdefault('counted',{})
        month=time.strftime('%Y-%m',time.localtime(item['time']))
        day=time.strftime('%Y-%m-%d',time.localtime(item['time']))
        def add(metric,unique=None):
            if unique is not None:
                if unique<=seen.get(metric,0):return
                seen[metric]=unique
            for total in (data.setdefault('totals',{}),data['months'].setdefault(month,{}),data.setdefault('days',{}).setdefault(day,{})):
                total[metric]=total.get(metric,0)+1
            recorded.append(metric)
        if state=='APPLYING':
            add('attempts',identity)
            if item.get('manual'):add('manual_attempts',identity)
            elif not item['trial']:add('automatic_attempts',identity)
        if state=='COMMITTED':
            new=identity>seen.get('committed',0)
            add('committed',identity)
            if new and not item['trial']:
                add('manual_committed' if item.get('manual') else 'automatic_committed',identity)
                kind=item.get('transition_kind')
                if kind in ('server','channel','protocol'):add(kind+'_switches',identity)
        if state=='ARMED' and 'TRIAL-PASSED' in item['codes']:add('trials_passed',identity)
        if state=='ROLLED-BACK':
            add('rollbacks',identity)
            if item.get('original_restored') is True and ('PRIMARY-STABLY-RECOVERED' in item['codes'] or item.get('manual')):add('returns',identity)
        prior=data.get('counted_state')
        if state=='BLOCKED' and prior!='BLOCKED':add('blocked_episodes')
        if 'PAIR-RATE-LIMIT' in item['codes'] and data.get('counted_reason')!='PAIR-RATE-LIMIT':add('rate_limited_episodes')
        data['counted_state']=state
        data['counted_reason']='PAIR-RATE-LIMIT' if 'PAIR-RATE-LIMIT' in item['codes'] else None
        return recorded

    def migrate(self,data):
        if data.get('counter_version')==2:return
        events=data['events']
        complete=not data['sequence'] or bool(events) and len(events)==data['sequence'] and all(row.get('sequence')==i+1 for i,row in enumerate(events))
        data['legacy_months']=json.loads(encoded(data['months']))
        data['counter_version']=2;data['counted']={};data['totals']={}
        data['returns_since']=time.time()
        data['counter_accuracy']='complete retained event replay' if complete else 'legacy partial counters; deduplicated from upgrade'
        if complete:
            data['months']={};data['days']={}
            for item in events:item['counted_metrics']=self.counters(data,item)
        else:
            for totals in data['months'].values():
                for key,value in totals.items():
                    if key in METRICS and type(value) is int and value>=0:data['totals'][key]=data['totals'].get(key,0)+value
            # Seed deduplication without recounting any existing aggregate.
            replay={'months':{},'days':{}}
            for item in events:self.counters(replay,item)
            for key in ('counted','counted_state','counted_reason'):
                if key in replay:data[key]=replay[key]

    def prune(self,data,now):
        data['events']=[row for row in data['events'] if now-self.detail_days*86400<=row['time']<=now]
        for retired in sorted(data['months'])[:-1200]:del data['months'][retired]
        cutoff=time.strftime('%Y-%m-%d',time.localtime(max(0,now-self.detail_days*86400)))
        for retired in list(data.get('days',{})):
            if retired<cutoff:del data['days'][retired]
    @contextlib.contextmanager
    def locked(self):
        """One lock for every writer of the history (supervisor transitions and the owner's statistics reset)."""
        self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        lock=self.path.with_name('native-history.lock')
        if lock.is_symlink():raise HistoryError('HISTORY-PATH')
        fd=os.open(str(lock),os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)
    def record(self,value,now=None):
        with self.locked():return self._record(value,now)
    def _record(self,value,now=None):
        now=time.time() if now is None else now
        if type(now) not in (int,float) or not math.isfinite(now) or now<0:raise HistoryError('HISTORY-CLOCK')
        data=self.load()
        legacy=data.get('counter_version')!=2
        self.migrate(data)
        if data['last_time'] is not None and now<data['last_time']:now=data['last_time']
        state=value.get('state','UNKNOWN')
        if not isinstance(state,str) or not CODE.fullmatch(state):raise HistoryError('HISTORY-STATE')
        codes=value.get('blockers',[])[:16]
        if value.get('reason'):codes=list(codes)+[value['reason']]
        codes=sorted({c for c in codes if isinstance(c,str) and CODE.fullmatch(c)})
        item={'state':state,'codes':codes,'trial':value.get('trial') is True}
        if value.get('transition_source') in ('manual','automatic','test','programmatic','unknown'):item['transition_source']=value['transition_source']
        control_time=value.get('control_time')
        if (value.get('control_action') in ('start','stop') and value.get('control_source') in ('manual','test','programmatic','unknown')
                and type(control_time) in (int,float) and 0<control_time<=now and math.isfinite(control_time)):
            item.update({key:value[key] for key in ('control_action','control_source','control_time')})
        if value.get('manual') is True or 'OPERATOR-MANUAL' in codes:item['manual']=True
        if type(value.get('original_restored')) is bool:item['original_restored']=value['original_restored']
        scope=value.get('proof_scope','external-lan')
        if scope not in('external-lan','router-hosted-ipv4','router-probed-ipv4'):raise HistoryError('HISTORY-SCOPE')
        if 'proof_scope'in value:item['proof_scope']=scope
        for key in ('source','target'):
            identifier=value.get(key)
            if isinstance(identifier,str) and PROFILE.fullmatch(identifier):item[key]=identifier
        latency=clean_transition_latency(value.get('latency'),value,now)
        if latency is not None:item['latency']=latency
        kind=value.get('transition_kind')
        if kind in ('server','channel','protocol'):item['transition_kind']=kind
        raw=value.get('probe_evidence')
        if isinstance(raw,dict):
            evidence={}
            for name in ('source_streak_met','reserve_streak_met'):
                if type(raw.get(name)) is bool:evidence[name]=raw[name]
            for name,low in (('required_failures',3),('required_successes',2)):
                if type(raw.get(name)) is int and low<=raw[name]<=10:evidence[name]=raw[name]
            if evidence:item['probe_evidence']=evidence
        phases=value.get('phase_evidence')
        if isinstance(phases,list):
            clean=[]
            for row in phases[-32:]:
                if not isinstance(row,dict):continue
                phase=row.get('phase');stamp=row.get('time')
                if isinstance(phase,str) and CODE.fullmatch(phase) and type(stamp) in (int,float) and math.isfinite(stamp) and 0<=stamp<=now and (not clean or stamp>=clean[-1]['time']):
                    clean.append({'phase':phase,'time':stamp})
            if clean:item['phase_evidence']=clean
        active,episode=self.correlate(data,item)
        # A new RTT sample alone is not a controller transition or flash event.
        key=hashlib.sha256(encoded({k:v for k,v in item.items() if k!='latency'})).hexdigest()
        if key==data['last_key']:
            original_count=(len(data['events']),len(data.get('days',{})));self.prune(data,now)
            if legacy or (len(data['events']),len(data.get('days',{})))!=original_count:
                atomic(self.backup,self.envelope(json.loads(encoded(data))))
                atomic(self.path,self.envelope(data))
            if data.get('daily_since') is None:
                old=self.envelope(json.loads(encoded(data)));data['daily_since']=now;data['days']={}
                atomic(self.backup,old);atomic(self.path,self.envelope(data))
            return False
        old=self.envelope(json.loads(encoded(data)))
        if data['sequence']>=2**53-1:raise HistoryError('HISTORY-SEQUENCE-LIMIT')
        data['active_attempt']=active;data['retry_episode']=episode
        item.update(time=now,sequence=data['sequence']+1)
        data['sequence']+=1;data['last_key']=key;data['last_time']=now
        retained=data['events']+[item]
        data['detail_budget_dropped']=data.get('detail_budget_dropped',0)+sum(row['time']>=now-self.detail_days*86400 for row in retained[:-self.limit])
        data['events']=retained[-self.limit:]
        month=time.strftime('%Y-%m',time.localtime(now));day=time.strftime('%Y-%m-%d',time.localtime(now))
        if data.get('daily_since') is None:data['daily_since']=now
        daily=data.setdefault('days',{})
        item['counted_metrics']=self.counters(data,item)
        for totals in (data['totals'],data['months'].setdefault(month,{}),daily.setdefault(day,{})):
            for metric in METRICS:totals.setdefault(metric,0)
        self.prune(data,now)
        # New phase evidence must not make our own next read exceed its bound.
        # Keep aggregate counters; trim only oldest detailed event observations.
        while len(data['events'])>1 and len(encoded(data))>self.RETENTION_BYTES:
            del data['events'][0]
            data['detail_budget_dropped']=data.get('detail_budget_dropped',0)+1
        if len(encoded(data))>self.RETENTION_BYTES:raise HistoryError('HISTORY-SIZE')
        atomic(self.backup,old);atomic(self.path,self.envelope(data))
        return True
    def public(self,data=None,now=None):
        data=self.load() if data is None else json.loads(encoded(data))
        self.migrate(data);self.prune(data,now if now is not None else data['last_time'] if data['last_time'] is not None else time.time())
        weekly=({key:sum(key in row.get('counted_metrics',[]) for row in data['events']) for key in METRICS}
                if all('counted_metrics' in row for row in data['events']) and not data.get('detail_budget_dropped') else None)
        return {'available':self.path.exists() or self.backup.exists(),'restored_from_backup':self.restored,
                'timezone':data['timezone'],'sequence':data['sequence'],'events':data['events'][-100:],
                'totals':data.get('totals',{}),'counter_accuracy':data.get('counter_accuracy'),
                'returns_since':data.get('returns_since'),
                'weekly':weekly,'weekly_detail_complete':not data['events'] or data['events'][-1]['sequence']-data['events'][0]['sequence']+1==len(data['events']),
                'detail_days':self.detail_days,'retained_events':len(data['events']),
                'detail_budget_dropped':data.get('detail_budget_dropped',0),
                'months':data['months'],'days':data.get('days',{}),'daily_since':data.get('daily_since'),'event_history_truncated':data['sequence']>min(100,len(data['events'])),'scope':'controller transitions; not LAN availability or router power-loss proof'}


def read_public(directory,cache=None):
    """Public history. With a cache path (RAM), the parsed result is reused while both history files are unchanged.

    The key is each file's inode, size and mtime (every write replaces the file, so the inode changes), the retention
    setting and the hour, so pruning by age still happens. A missing or unreadable cache only costs one full read."""
    try:
        history=History(directory);now=time.time()
        key=[history.detail_days,int(now//3600)]
        for path in (history.path,history.backup):
            try:info=os.lstat(str(path));key.append([info.st_ino,info.st_size,info.st_mtime_ns])
            except FileNotFoundError:key.append(None)
        if cache is not None:
            try:
                cache=Path(cache)
                if not cache.is_symlink():
                    cached=json.loads(cache.read_text(encoding='utf8'))
                    if isinstance(cached,dict) and cached.get('key')==key and isinstance(cached.get('value'),dict):return cached['value']
            except (OSError,ValueError):pass
        value=history.public(now=now)
        if cache is not None:
            with contextlib.suppress(OSError,ValueError,HistoryError):atomic(cache,{'key':key,'value':value})
        return value
    except (OSError,ValueError,KeyError,TypeError):return {'available':False,'error':'HISTORY-001'}
