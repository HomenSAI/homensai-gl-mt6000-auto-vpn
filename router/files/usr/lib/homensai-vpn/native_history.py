"""MIT. Bounded persistent native transition history; no keys, tokens or exit IPs."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

CODE=re.compile(r'^[A-Z0-9_-]{1,96}$')
PROFILE=re.compile(r'^(?:openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$')


class HistoryError(ValueError):
    pass


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def atomic(path,value):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():raise HistoryError('HISTORY-PATH')
    pending=path.with_name(path.name+'.pending')
    fd=os.open(str(pending),os.O_WRONLY|os.O_CREAT|os.O_TRUNC|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(encoded(value));stream.flush();os.fsync(stream.fileno())
    os.replace(str(pending),str(path))
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


class History:
    RETENTION_BYTES=400*1024
    def __init__(self,directory,limit=500):
        if type(limit) is not int or not 1<=limit<=500:raise HistoryError('HISTORY-LIMIT')
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
                if path.stat().st_size>512*1024:raise HistoryError('HISTORY-SIZE')
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
                if len(data['events'])>500 or len(data['months'])>18 or not isinstance(data.get('days',{}),dict) or len(data.get('days',{}))>400:raise HistoryError('HISTORY-BOUNDS')
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
    def record(self,value,now=None):
        now=time.time() if now is None else now
        if type(now) not in (int,float) or not math.isfinite(now) or now<0:raise HistoryError('HISTORY-CLOCK')
        data=self.load()
        if data['last_time'] is not None and now<data['last_time']:raise HistoryError('HISTORY-CLOCK-BACKWARD')
        state=value.get('state','UNKNOWN')
        if not isinstance(state,str) or not CODE.fullmatch(state):raise HistoryError('HISTORY-STATE')
        codes=value.get('blockers',[])[:16]
        if value.get('reason'):codes=list(codes)+[value['reason']]
        codes=sorted({c for c in codes if isinstance(c,str) and CODE.fullmatch(c)})
        item={'state':state,'codes':codes,'trial':value.get('trial') is True}
        scope=value.get('proof_scope','external-lan')
        if scope not in('external-lan','router-hosted-ipv4','router-probed-ipv4'):raise HistoryError('HISTORY-SCOPE')
        if 'proof_scope'in value:item['proof_scope']=scope
        for key in ('source','target'):
            identifier=value.get(key)
            if isinstance(identifier,str) and PROFILE.fullmatch(identifier):item[key]=identifier
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
        key=hashlib.sha256(encoded(item)).hexdigest()
        if key==data['last_key']:
            if data.get('daily_since') is None:
                old=self.envelope(json.loads(encoded(data)));data['daily_since']=now;data['days']={}
                atomic(self.backup,old);atomic(self.path,self.envelope(data))
            return False
        old=self.envelope(json.loads(encoded(data)))
        if data['sequence']>=2**53-1:raise HistoryError('HISTORY-SEQUENCE-LIMIT')
        data['active_attempt']=active;data['retry_episode']=episode
        item.update(time=now,sequence=data['sequence']+1)
        data['sequence']+=1;data['last_key']=key;data['last_time']=now
        data['events']=(data['events']+[item])[-self.limit:]
        month=time.strftime('%Y-%m',time.localtime(now));day=time.strftime('%Y-%m-%d',time.localtime(now))
        if data.get('daily_since') is None:data['daily_since']=now
        daily=data.setdefault('days',{})
        metrics=('attempts','committed','trials_passed','rollbacks','blocked_episodes','automatic_attempts','automatic_committed','server_switches','channel_switches','protocol_switches')
        for totals in (data['months'].setdefault(month,{}),daily.setdefault(day,{})):
            for metric in metrics:totals.setdefault(metric,0)
            if state=='APPLYING':
                totals['attempts']+=1
                if not item['trial']:totals['automatic_attempts']+=1
            if state=='COMMITTED':
                totals['committed']+=1
                if not item['trial']:
                    totals['automatic_committed']+=1
                    if kind in ('server','channel','protocol'):totals[kind+'_switches']+=1
            if state=='ARMED' and 'TRIAL-PASSED' in codes:totals['trials_passed']+=1
            if state=='ROLLED-BACK':totals['rollbacks']+=1
            if state=='BLOCKED':totals['blocked_episodes']+=1
        for retired in sorted(data['months'])[:-18]:del data['months'][retired]
        for retired in sorted(daily)[:-400]:del daily[retired]
        # New phase evidence must not make our own next read exceed its bound.
        # Keep aggregate counters; trim only oldest detailed event observations.
        while len(data['events'])>1 and len(encoded(data))>self.RETENTION_BYTES:
            del data['events'][0]
        if len(encoded(data))>self.RETENTION_BYTES:raise HistoryError('HISTORY-SIZE')
        atomic(self.backup,old);atomic(self.path,self.envelope(data))
        return True
    def public(self):
        data=self.load()
        return {'available':self.path.exists() or self.backup.exists(),'restored_from_backup':self.restored,
                'timezone':data['timezone'],'sequence':data['sequence'],'events':data['events'][-100:],
                'months':data['months'],'days':data.get('days',{}),'daily_since':data.get('daily_since'),'event_history_truncated':data['sequence']>min(100,len(data['events'])),'scope':'controller transitions; not LAN availability or router power-loss proof'}


def read_public(directory):
    try:return History(directory).public()
    except (OSError,ValueError,KeyError,TypeError):return {'available':False,'error':'HISTORY-001'}
