"""Single-flight measurement requests; completion is tied to a published snapshot."""
import contextlib
import fcntl
import math
import os
import re
import time
import uuid
from pathlib import Path

@contextlib.contextmanager
def locked(root):
    root=Path(root);root.mkdir(mode=0o700,parents=True,exist_ok=True)
    if root.is_symlink():raise ValueError('SCAN-STORAGE')
    fd=os.open(str(root/'scan.lock'),os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX);yield root
    finally:os.close(fd)

def public(root,read,now=None):
    now=time.time() if now is None else now
    row=read(Path(root)/'scan.state',{})
    if not isinstance(row,dict) or not re.fullmatch('[a-f0-9]{32}',str(row.get('request_id',''))):return {'state':'IDLE'}
    if row.get('state') not in ('QUEUED','RUNNING','COMPLETED','FAILED') or type(row.get('requested_at')) not in (int,float) or not math.isfinite(row['requested_at']):return {'state':'FAILED','code':'SCAN-STATE-CORRUPT'}
    row={k:row[k] for k in ('request_id','state','requested_at','started_at','finished_at','code','measurement_request_id','measured_at','checked','failed') if k in row}
    if row.get('state') in ('QUEUED','RUNNING') and (now<row.get('requested_at',now) or now-row.get('requested_at',0)>300):
        row.update(state='FAILED',code='SCAN-DEADLINE-EXCEEDED')
    return row

def enqueue(root,read,write,now=None):
    now=time.time() if now is None else now
    with locked(root) as root:
        current=public(root,read,now)
        if current.get('state') in ('QUEUED','RUNNING'):
            return dict(current,queued=True,duplicate=True)
        row={'request_id':uuid.uuid4().hex,'state':'QUEUED','requested_at':now}
        write(root/'scan.state',row)
        write(root/'scan.request',{'request_id':row['request_id']})
        return dict(row,queued=True,duplicate=False)

def begin(root,read,write,now=None):
    now=time.time() if now is None else now
    with locked(root) as root:
        row=public(root,read,now)
        if row.get('state')!='QUEUED':
            path=root/'scan.request'
            if path.exists() and not path.is_symlink():path.unlink()
            return None
        row.update(state='RUNNING',started_at=now);write(root/'scan.state',row)
        path=root/'scan.request'
        if path.exists() and not path.is_symlink():path.unlink()
        return row['request_id']

def finish(root,read,write,identifier,code=None,now=None,snapshot=None):
    if not identifier:return
    with locked(root) as root:
        row=public(root,read,now)
        if row.get('request_id')!=identifier or row.get('state')!='RUNNING':return False
        stamp=time.time() if now is None else now
        if stamp<row['requested_at'] or stamp-row['requested_at']>300:code='SCAN-DEADLINE-EXCEEDED'
        if not code:
            if not isinstance(snapshot,dict) or snapshot.get('measurement_request_id')!=identifier or snapshot.get('time',0)<row['requested_at']:raise ValueError('SCAN-SNAPSHOT-MISMATCH')
            profiles=[p for p in snapshot.get('profiles',[]) if p.get('interface') and isinstance(p.get('time'),(int,float)) and p['time']>=row['started_at']]
            row.update(measurement_request_id=identifier,measured_at=snapshot['time'],checked=len(profiles),failed=sum(p.get('code') is not None or p.get('dns_ok') is not True or p.get('https_success',0)<2 for p in profiles))
        row.update(state='FAILED' if code else 'COMPLETED',finished_at=time.time() if now is None else now)
        if code:row['code']=code
        write(root/'scan.state',row)
