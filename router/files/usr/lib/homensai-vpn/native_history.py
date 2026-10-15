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
    def __init__(self,directory,limit=500):
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
                if not isinstance(data.get('events'),list) or not isinstance(data.get('months'),dict) or not isinstance(data.get('sequence'),int):raise HistoryError('HISTORY-SCHEMA')
                if len(data['events'])>500 or len(data['months'])>18:raise HistoryError('HISTORY-BOUNDS')
                self.restored=bool(index);return data
            except (OSError,ValueError,KeyError,TypeError):continue
        if found:raise HistoryError('HISTORY-CORRUPT')
        return {'sequence':0,'events':[],'months':{},'last_key':None,'last_time':None,'timezone':'Europe/Berlin'}
    def envelope(self,data):
        return {'schema':1,'data':data,'sha256':hashlib.sha256(encoded(data)).hexdigest()}
    def record(self,value,now=None):
        now=time.time() if now is None else now
        if not isinstance(now,(int,float)) or not math.isfinite(now):raise HistoryError('HISTORY-CLOCK')
        data=self.load()
        if data['last_time'] is not None and now<data['last_time']:raise HistoryError('HISTORY-CLOCK-BACKWARD')
        state=value.get('state','UNKNOWN')
        if not isinstance(state,str) or not CODE.fullmatch(state):raise HistoryError('HISTORY-STATE')
        codes=value.get('blockers',[])[:16]
        if value.get('reason'):codes=list(codes)+[value['reason']]
        codes=sorted({c for c in codes if isinstance(c,str) and CODE.fullmatch(c)})
        item={'state':state,'codes':codes,'trial':value.get('trial') is True}
        for key in ('source','target'):
            identifier=value.get(key)
            if isinstance(identifier,str) and PROFILE.fullmatch(identifier):item[key]=identifier
        key=hashlib.sha256(encoded(item)).hexdigest()
        if key==data['last_key']:return False
        old=self.envelope(json.loads(encoded(data)))
        item.update(time=now,sequence=data['sequence']+1)
        data['sequence']+=1;data['last_key']=key;data['last_time']=now
        data['events']=(data['events']+[item])[-self.limit:]
        month=time.strftime('%Y-%m',time.localtime(now))
        totals=data['months'].setdefault(month,{'attempts':0,'committed':0,'trials_passed':0,'rollbacks':0,'blocked_episodes':0})
        if state=='APPLYING':totals['attempts']+=1
        if state=='COMMITTED':totals['committed']+=1
        if state=='ARMED' and 'TRIAL-PASSED' in codes:totals['trials_passed']+=1
        if state=='ROLLED-BACK':totals['rollbacks']+=1
        if state=='BLOCKED':totals['blocked_episodes']+=1
        for retired in sorted(data['months'])[:-18]:del data['months'][retired]
        atomic(self.backup,old);atomic(self.path,self.envelope(data))
        return True
    def public(self):
        data=self.load()
        return {'available':self.path.exists() or self.backup.exists(),'restored_from_backup':self.restored,
                'timezone':data['timezone'],'sequence':data['sequence'],'events':data['events'][-100:],
                'months':data['months'],'scope':'controller transitions; not LAN availability or router power-loss proof'}


def read_public(directory):
    try:return History(directory).public()
    except (OSError,ValueError,KeyError,TypeError):return {'available':False,'error':'HISTORY-001'}
