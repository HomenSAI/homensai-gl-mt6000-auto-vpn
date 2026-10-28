"""Bounded cooperative quiet window. Never writes Auto intent or service settings."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time

from agent import RUNTIME, atomic_json, read_json
from auto_control import control_lock, revision_locked

ROLES={'monitor':'agent.py','auto':'native_switch.py'}
INTENTS=('pair-auto-control.json','auto-control.json','pair-manual-control.json',
         'manual-control.json','native-return.json')


class PauseError(ValueError):
    pass


def path():return RUNTIME/'speed-pause.json'


def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def identity(pid):
    if type(pid)is not int or pid<1:raise PauseError('SPEED-PAUSE-UNVERIFIED')
    raw=Path('/proc',str(pid),'stat').read_text();tail=raw[raw.rindex(')')+2:].split()
    if tail[0]in('Z','X'):raise PauseError('SPEED-PAUSE-UNVERIFIED')
    return {'pid':pid,'start':int(tail[19])}


def alive(owner):
    try:return identity(owner['pid'])==owner
    except(OSError,ValueError,KeyError,IndexError):return False


def participants():
    reply=subprocess.run(['ubus','-t','5','call','service','list','{"name":"homensai-vpn"}'],
                         capture_output=True,timeout=7,check=True)
    rows=json.loads(reply.stdout)['homensai-vpn']['instances'];result={}
    for role,name in ROLES.items():
        row=rows.get('native'if role=='auto'else role,{})
        if row.get('running')is not True:continue
        owner=identity(row['pid'])
        command=Path('/proc',str(owner['pid']),'cmdline').read_bytes().split(b'\0')
        if ('/usr/lib/homensai-vpn/'+name).encode()not in command or b'daemon'not in command:
            raise PauseError('SPEED-PAUSE-UNVERIFIED')
        result[role]=owner
    return result


def fingerprints():
    result={}
    for name in INTENTS:
        p=RUNTIME/name
        if p.is_symlink():raise PauseError('SPEED-PAUSE-UNVERIFIED')
        result[name]=hashlib.sha256(p.read_bytes()).hexdigest()if p.exists()else None
    return result


def load():
    p=path()
    if not p.exists():return None
    if p.is_symlink()or p.stat().st_size>8192:raise PauseError('SPEED-PAUSE-UNVERIFIED')
    row=read_json(p,{})
    if (not isinstance(row,dict)or row.get('schema')!=1 or row.get('boot')!=boot()
            or not isinstance(row.get('tx'),str)or not re.fullmatch('[a-f0-9]{32}',row['tx'])
            or row.get('phase')not in('PAUSING','PAUSED','RESUMING')
            or type(row.get('deadline'))not in(int,float)or not math.isfinite(row['deadline'])
            or row['deadline']>time.monotonic()+360 or type(row.get('auto_was_on'))is not bool
            or not isinstance(row.get('owners'),dict)or set(row['owners'])-set(ROLES)
            or not isinstance(row.get('acks'),dict)
            or not isinstance(row.get('revision'),str)or not re.fullmatch('[a-f0-9]{32}',row['revision'])
            or not isinstance(row.get('intents'),dict)or set(row['intents'])!=set(INTENTS)
            or any(v is not None and (not isinstance(v,str)or not re.fullmatch('[a-f0-9]{64}',v))for v in row['intents'].values())
            or set(row['acks'])-set(row['owners'])
            or any(not isinstance(v,dict)or v.get('owner')!=row['owners'][k]
                   or type(v.get('time'))not in(int,float)or not math.isfinite(v['time'])
                   for k,v in row['acks'].items())
            or any(not isinstance(v,dict)or set(v)!={'pid','start'}or
                   any(type(v[k])is not int or v[k]<1 for k in v)
                   for v in [row.get('worker')]+list(row['owners'].values()))
            or row['phase']=='RESUMING'and any(type(row.get(k))not in(int,float)or
                   not math.isfinite(row[k])for k in('resume_time','resume_deadline'))):
        raise PauseError('SPEED-PAUSE-UNVERIFIED')
    return row


def unchanged(row):
    return (read_json(RUNTIME/'auto-control-revision.json',{}).get('revision')==row['revision']
            and fingerprints()==row['intents'])


def begin_resume(row):
    if row['phase']!='RESUMING':
        row.update(phase='RESUMING',resume_time=time.time(),resume_deadline=time.monotonic()+25)
        atomic_json(path(),row)


def acquire(job):
    with control_lock(RUNTIME):
        if path().exists():
            previous=load()
            if (previous and previous['phase']=='RESUMING'and not alive(previous['worker'])
                    and (time.monotonic()>previous['resume_deadline']or
                         not any(alive(v)for v in previous['owners'].values()))):path().unlink()
            else:raise PauseError('SPEED-PAUSE-BUSY')
        native=read_json(RUNTIME/'native-status.json',{})
        if native.get('state')in('ARMED','APPLYING','WAIT-CLIENT','RESTORING','RELEASE-PENDING'):
            raise PauseError('SPEED-SWITCH-IN-PROGRESS')
        from pair_auto import read_state, intent
        pair=read_state();request=intent()
        if request.get('mode')=='on'and native.get('state')not in('OBSERVING','COMMITTED'):
            raise PauseError('SPEED-SWITCH-IN-PROGRESS')
        if pair.get('phase')in('STARTING','STOPPING','HELD')or pair.get('phase')=='RUNNING'and request.get('mode')!='on':
            raise PauseError('SPEED-SWITCH-IN-PROGRESS')
        if request.get('mode')!='on'and native.get('state')in('OBSERVING','COMMITTED','DEGRADED-ON-RESERVE'):
            raise PauseError('SPEED-PAUSE-MODE')
        for name in('manual-control.json','pair-manual-control.json'):
            pending=read_json(RUNTIME/name,{})
            if pending.get('state')in('QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'):
                raise PauseError('SPEED-SWITCH-IN-PROGRESS')
        owners=participants()
        row=dict(schema=1,tx=job['tx'],boot=boot(),worker=identity(os.getpid()),owners=owners,acks={},
                 revision=revision_locked(RUNTIME),intents=fingerprints(),phase='PAUSING',
                 deadline=job['monotonic_deadline'],auto_was_on=request.get('mode')=='on')
        atomic_json(path(),row)
    end=time.monotonic()+25
    while time.monotonic()<end:
        if interrupted(job['tx']):raise PauseError('SPEED-CANCELLED')
        with control_lock(RUNTIME):
            current=load()
            if not current or current['tx']!=job['tx']:raise PauseError('SPEED-PAUSE-LOST')
            if all(current['acks'].get(role,{}).get('owner')==owner and
                   0<=time.monotonic()-current['acks'][role].get('time',0)<=3
                   for role,owner in owners.items()):
                current['phase']='PAUSED';atomic_json(path(),current);return
        time.sleep(.2)
    raise PauseError('SPEED-PAUSE-TIMEOUT')


def interrupted(tx):
    row=load()
    if not row or row['tx']!=tx or row['phase']=='RESUMING':return True
    if read_json(RUNTIME/'speed-cancel.json',{}).get('tx')==tx:return True
    if time.monotonic()>=row['deadline']or not unchanged(row):return True
    return any(not alive(owner)for owner in row['owners'].values())


def release(tx):
    with control_lock(RUNTIME):
        row=load()
        if row and row['tx']==tx:
            if not any(alive(v)for v in row['owners'].values()):path().unlink()
            else:begin_resume(row)


def gate(role,quiescent=lambda:True):
    """Called at a loop boundary, outside any network transaction/control lock."""
    if not path().exists():return False
    try:
        with control_lock(RUNTIME):
            row=load()
            if not row:return False
            worker_up=alive(row['worker'])
            if time.monotonic()>=row['deadline']and worker_up:
                from speed_test import worker_alive
                job=read_json(RUNTIME/'speed-job.json',{})
                if job.get('tx')==row['tx']and job.get('pid')==row['worker']['pid']and worker_alive(job):
                    os.kill(row['worker']['pid'],signal.SIGTERM)
                    if unchanged(row):return True
                else:
                    worker_up=False;begin_resume(row)
            if not unchanged(row):
                # A new human command supersedes the quiet window immediately.
                atomic_json(RUNTIME/'speed-cancel.json',{'tx':row['tx'],'time':time.time()})
                begin_resume(row)
                if not worker_up:path().unlink()
                return False
            current=identity(os.getpid())
            if row['owners'].get(role)!=current:return False
            if not worker_up:begin_resume(row)
            if row['phase']=='RESUMING':
                if role=='monitor':
                    if 'auto'not in row['owners']or not alive(row['owners']['auto']):path().unlink()
                    return False
                status=read_json(RUNTIME/'status.json',{})
                ready=('monitor'not in row['owners']or status.get('time',0)>=row['resume_time']
                       and all(type(p.get('time'))in(int,float)and p['time']>=row['resume_time']for p in status.get('profiles',[])
                               if p.get('administrative_state')=='enabled'))
                if ready or time.monotonic()>=row['resume_deadline']:
                    path().unlink();return False
                return True
            # The monitor may have bounded asynchronous probe sockets still in flight.
            # Check under the same lock that grants the quiet-window acknowledgement.
            try:ready=quiescent() is True
            except Exception:ready=False
            if not ready:
                if role in row['acks']:
                    row['acks'].pop(role);atomic_json(path(),row)
                return True
            row['acks'][role]={'owner':current,'time':time.monotonic()};atomic_json(path(),row)
            return True
    except(OSError,ValueError,KeyError,TypeError,IndexError):
        return False  # An unreadable pause can never disable normal Auto/Stop.


def public():
    try:
        row=load()
        if not row:return {'active':False}
        active=unchanged(row)and(time.monotonic()<row['deadline']or row['phase']=='RESUMING')
        return {'active':active,'phase':row['phase'],'auto_paused':active and 'auto'in row['acks'],
                'monitor_paused':active and row['phase']!='RESUMING'and 'monitor'in row['acks']}
    except(OSError,ValueError,KeyError,TypeError):return {'active':False}


def cpu_snapshot():
    try:
        fields=Path('/proc/stat').read_text().splitlines()[0].split()
        if fields[0]!='cpu'or len(fields)<9:raise ValueError()
        values=[int(v)for v in fields[1:9]]
        if any(v<0 for v in values):raise ValueError()
        return values
    except(OSError,ValueError,IndexError):raise PauseError('SPEED-CPU-UNKNOWN') from None


def cpu_usage():
    before=cpu_snapshot();time.sleep(1);after=cpu_snapshot()
    delta=[b-a for a,b in zip(before,after)];total=sum(delta)
    if total<=0 or any(v<0 for v in delta):raise PauseError('SPEED-CPU-UNKNOWN')
    return round(100*(total-delta[3]-delta[4])/total,1)
