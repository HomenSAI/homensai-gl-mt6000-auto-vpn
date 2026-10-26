# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""Optional bounded HTTPS goodput test. No route, VPN or firewall writes.

Cloudflare's public download/upload API is used without its JS engine or logging
API. Every socket is bound to the selected VPN device and mark. DNS resolution
also travels through that VPN using a fixed-address TLS resolver.
"""
from concurrent.futures import ThreadPoolExecutor
import http.client
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import signal
import ssl
import subprocess
import sys
import threading
import time
import uuid

from agent import RUNTIME, PERSIST, atomic_json, read_json, checksum, inventory, route_binding, bound_socket, command
from auto_control import control_lock

HOST='speed.cloudflare.com'
JOB=RUNTIME/'speed-job.json'
CANCEL=RUNTIME/'speed-cancel.json'
HISTORY=PERSIST/'speed-history.json'
LEDGER=PERSIST/'speed-quota.json'
MIB=1024*1024


class SpeedError(Exception):

    def __init__(self,code):
        self.code=code
        super().__init__(code)


def option_int(settings,key,default,low,high):
    value=settings.get(key,default)
    try:value=int(value)
    except (TypeError,ValueError):raise SpeedError('SPEED-CONFIG')
    if not low<=value<=high:raise SpeedError('SPEED-CONFIG')
    return value


def settings(data=None):
    values=(data or inventory()).get('settings',{})
    keys=('speed_enabled','speed_auto_new','speed_budget_mib','speed_duration','speed_streams','speed_daily_mib','speed_busy_mbps')
    return {key:('1' if values.get(key) is True else '0' if values.get(key) is False else values.get(key,'')) for key in keys}


def value_int(values,key,default,low,high):
    copy=dict(values)
    if not copy.get(key):copy[key]=default
    return option_int(copy,key,default,low,high)


def load_history():
    found=False
    for path in (HISTORY,HISTORY.with_name('speed-history.backup.json')):
        try:
            item=read_json(path)
            if item is None:continue
            found=True;data=item['data']
            if item.get('schema')!=1 or item.get('sha256')!=checksum(data):continue
            if not isinstance(data.get('results'),list) or len(data['results'])>500:continue
            if any(not isinstance(row,dict) or not isinstance(row.get('time'),(int,float)) or not math.isfinite(row['time']) for row in data['results']):continue
            from retention_settings import configured_days
            period=configured_days();data['results']=[row for row in data['results'] if row['time']>=time.time()-period*86400]
            data['retention_days']=period
            return data
        except (OSError,ValueError,KeyError,TypeError):found=True
    if found:raise SpeedError('SPEED-HISTORY-CORRUPT')
    from retention_settings import configured_days
    return {'results':[],'retention_days':configured_days()}


def append_history(rows):
    data=load_history();cutoff=time.time()-data['retention_days']*86400
    kept=[row for row in data['results']+rows if row.get('time',0)>=cutoff]
    data['history_truncated']=data.get('history_truncated',0)+max(0,len(kept)-500)
    data['results']=kept[-500:]
    old=read_json(HISTORY)
    if old and old.get('sha256')==checksum(old.get('data')):
        atomic_json(HISTORY.with_name('speed-history.backup.json'),old)
    atomic_json(HISTORY,{'schema':1,'data':data,'sha256':checksum(data)})


def prune_history():
    """Age cleanup also runs without a new speed test; never spends test quota."""
    if not HISTORY.exists() and not HISTORY.with_name('speed-history.backup.json').exists():return
    with control_lock():
        data=load_history();current=read_json(HISTORY,{})
        if current.get('data')==data:return
        envelope={'schema':1,'data':data,'sha256':checksum(data)}
        atomic_json(HISTORY.with_name('speed-history.backup.json'),envelope)
        atomic_json(HISTORY,envelope)


def reserve_quota(amount,daily_limit,now):
    day=time.strftime('%Y-%m-%d',time.localtime(now))
    envelope=read_json(LEDGER)
    days={}
    if envelope:
        days=envelope.get('data',{})
        if not isinstance(days,dict) or any(not isinstance(k,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',k) or type(v) is not int or v<0 for k,v in days.items()) or envelope.get('sha256')!=checksum(days):raise SpeedError('SPEED-QUOTA-CORRUPT')
    if days.get(day,0)+amount>daily_limit:raise SpeedError('SPEED-DAILY-LIMIT')
    days[day]=days.get(day,0)+amount
    days={key:days[key] for key in sorted(days)[-7:]}
    atomic_json(LEDGER,{'data':days,'sha256':checksum(days)})
    return days[day]


def validate_request(arguments,profiles):
    if set(arguments)!={'profiles','budget_mib','duration','streams'}:raise SpeedError('SPEED-REQUEST')
    ids=arguments['profiles']
    if not isinstance(ids,list) or not 1<=len(ids)<=8 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):
        raise SpeedError('SPEED-PROFILES')
    known={p['id'] for p in profiles}
    if any(i not in known for i in ids):raise SpeedError('SPEED-PROFILES')
    for key,low,high in (('budget_mib',1,32),('duration',2,15),('streams',1,4)):
        if type(arguments[key]) is not int or not low<=arguments[key]<=high:raise SpeedError('SPEED-REQUEST')
    return dict(arguments)


def verify_route(binding,address):
    if not ipaddress.IPv4Address(address).is_global:raise SpeedError('SPEED-ADDRESS')
    answer=json.loads(command(['ip','-4','-j','route','get',address,'mark',str(binding['mark'])]))
    if len(answer)!=1 or answer[0].get('dev')!=binding['device'] or str(answer[0].get('table','main'))!=binding['table']:
        raise SpeedError('SPEED-ROUTE-UNVERIFIED')


def connect(binding,address,hostname,deadline):
    verify_route(binding,address)
    raw=bound_socket(binding['device'],binding['mark'])
    try:
        raw.settimeout(max(.1,min(3,deadline-time.monotonic())))
        raw.connect((address,443))
        return ssl.create_default_context().wrap_socket(raw,server_hostname=hostname)
    except BaseException:
        raw.close();raise


def resolve_endpoint(binding,deadline):
    with connect(binding,'8.8.8.8','dns.google',deadline) as sock:
        sock.sendall(b'GET /resolve?name=speed.cloudflare.com&type=A HTTP/1.1\r\nHost: dns.google\r\nConnection: close\r\n\r\n')
        response=http.client.HTTPResponse(sock);response.begin();body=response.read(32769)
        if response.status!=200 or len(body)>32768:raise SpeedError('SPEED-DNS')
    data=json.loads(body)
    if not isinstance(data,dict) or data.get('Status')!=0 or not isinstance(data.get('Answer'),list) or len(data['Answer'])>32:raise SpeedError('SPEED-DNS')
    for row in data['Answer']:
        if not isinstance(row,dict) or row.get('type')!=1:continue
        try:address=ipaddress.IPv4Address(row.get('data',''))
        except (ValueError,TypeError):continue
        if address.is_global:
            verify_route(binding,str(address));return str(address)
    raise SpeedError('SPEED-DNS')


class Budget:

    def __init__(self,amount):
        self.remaining=amount;self.lock=threading.Lock()

    def take(self,maximum):
        with self.lock:
            amount=min(maximum,self.remaining);self.remaining-=amount;return amount


def request(binding,address,direction,amount,deadline,cancelled,progress=None):
    with connect(binding,address,HOST,deadline) as sock:
        path='/__up' if direction=='upload' else '/__down?bytes='+str(amount)
        method='POST' if direction=='upload' else 'GET'
        headers='%s %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\nCache-Control: no-cache\r\n' % (method,path,HOST)
        if direction=='upload':headers+='Content-Type: application/octet-stream\r\nContent-Length: '+str(amount)+'\r\n'
        sock.sendall((headers+'\r\n').encode('ascii'))
        sent=0
        while direction=='upload' and sent<amount:
            if cancelled() or time.monotonic()>=deadline:raise SpeedError('SPEED-CANCELLED')
            block=b'\0'*min(65536,amount-sent);sock.sendall(block);sent+=len(block)
            if progress:progress(len(block))
        response=http.client.HTTPResponse(sock);response.begin()
        if response.status!=200:raise SpeedError('SPEED-HTTP')
        received=0
        if direction=='upload':
            if len(response.read(8193))>8192:raise SpeedError('SPEED-RESPONSE-LIMIT')
            return sent
        while received<amount:
            if cancelled() or time.monotonic()>=deadline:raise SpeedError('SPEED-CANCELLED')
            block=response.read(min(65536,amount-received))
            if not block:raise SpeedError('SPEED-SHORT-RESPONSE')
            received+=len(block)
            if progress:progress(len(block))
        return received


def stage(binding,address,direction,budget,duration,streams,cancelled,transport=None,progress=None):
    transport=transport or request
    quota=Budget(budget);started=time.monotonic();deadline=started+duration
    sample_lock=threading.Lock();observed=0;last_bytes=0;last_at=started
    def report(amount=0,final=False):
        nonlocal observed,last_bytes,last_at
        with sample_lock:
            observed+=amount;now=time.monotonic();elapsed=now-last_at
            if progress and observed>last_bytes and elapsed>0 and (final or elapsed>=.5):
                progress((observed-last_bytes)*8/elapsed/1e6,observed,now-started)
                last_bytes=observed;last_at=now

    def stream():
        total=0
        while time.monotonic()<deadline and not cancelled():
            amount=quota.take(MIB)
            if not amount:break
            try:
                total+=transport(binding,address,direction,amount,deadline,cancelled,progress=report) if progress else transport(binding,address,direction,amount,deadline,cancelled)
            except (SpeedError,OSError) as error:
                # An elapsed measurement window is normal. Retain only fully
                # completed HTTP payloads; real cancellation still wins below.
                if time.monotonic()>=deadline and not cancelled()and (
                        isinstance(error,OSError)or error.code=='SPEED-CANCELLED'):break
                raise
        return total
    with ThreadPoolExecutor(max_workers=streams) as pool:
        futures=[pool.submit(stream) for _ in range(streams)]
        total=sum(future.result() for future in futures)
    elapsed=time.monotonic()-started
    if cancelled():raise SpeedError('SPEED-CANCELLED')
    if total<=0 or elapsed<=0:raise SpeedError('SPEED-NO-SAMPLE')
    report(final=True)
    return {'payload_bytes':total,'seconds':round(elapsed,3),'mbps':round(total*8/elapsed/1e6,3)}


def measure(profile,options,cancelled,live=None):
    row={'id':profile['id'],'name':profile['name'],'protocol':profile['protocol'],'channel':profile.get('channel','default'),'time':time.time(),
         'endpoint':HOST,'method':'bounded-HTTPS-payload-goodput','scope':'router-originated-IPv4',
         'payload_budget_bytes':options['budget_mib']*MIB,'overhead_in_budget':False}
    if live:live.phase(profile['id'],'resolving')
    if not profile.get('interface'):
        if live:live.finish(profile['id'],'SPEED-PROFILE-INACTIVE')
        return dict(row,code='SPEED-PROFILE-INACTIVE')
    try:
        binding=route_binding(profile['interface'])
        if binding.get('code'):raise SpeedError('SPEED-ROUTE-UNVERIFIED')
        address=resolve_endpoint(binding,time.monotonic()+6)
        if live:live.phase(profile['id'],'latency')
        latencies=[]
        for _ in range(3):
            start=time.monotonic();request(binding,address,'download',0,start+3,cancelled);latencies.append((time.monotonic()-start)*1000)
        row['latency_ms']=round(sorted(latencies)[1],1)
        budget=options['budget_mib']*MIB;down=budget*3//4
        for direction,amount in (('download',down),('upload',budget-down)):
            if live:live.phase(profile['id'],direction)
            callback=(lambda mbps,total,elapsed:live.sample(profile['id'],direction,mbps,total)) if live else None
            row[direction]=stage(binding,address,direction,amount,options['duration'],options['streams'],cancelled,progress=callback)
        if live:live.finish(profile['id'])
        return dict(row,code=None)
    except SpeedError as error:
        if live:live.finish(profile['id'],error.code)
        return dict(row,code=error.code)
    except (OSError,ValueError,KeyError,http.client.HTTPException,subprocess.SubprocessError):
        if live:live.finish(profile['id'],'SPEED-NETWORK')
        return dict(row,code='SPEED-NETWORK')


def worker_alive(job):
    pid=job.get('pid');tx=job.get('tx','')
    if type(pid) is not int or pid<1 or not re.fullmatch(r'[a-f0-9]{32}',tx):return False
    try:
        expected=str(Path(__file__).resolve()).encode()+b'\0run\0'+tx.encode()+b'\0'
        return expected in Path('/proc',str(pid),'cmdline').read_bytes()
    except OSError:return False


def active_job():
    job=read_json(JOB,{})
    if job.get('state')=='FAILED' and job.get('code')=='SPEED-WORKER-TIMEOUT':return worker_alive(job)
    if job.get('state') not in ('QUEUED','RUNNING'):return False
    if worker_alive(job):return True
    return job.get('state')=='QUEUED' and time.time()-job.get('started',0)<10


def publish_job(job):
    with control_lock():
        current=read_json(JOB,{})
        if current.get('tx')!=job.get('tx'):return False
        if current.get('state') in ('FAILED','DONE','CANCELLED') and current.get('state')!=job.get('state'):return False
        atomic_json(JOB,job);return True


def expire_worker():
    """Terminate only a proven own worker after its monotonic deadline + grace."""
    initial=read_json(JOB,{})
    if initial.get('state') not in ('QUEUED','RUNNING'):return
    with control_lock():
        job=read_json(JOB,{})
        if job.get('state') not in ('QUEUED','RUNNING') or not worker_alive(job):return
        if time.monotonic()<=job.get('monotonic_deadline',float('inf'))+15:return
        # Exact script/nonce match above prevents signalling a reused/unrelated PID.
        try:os.kill(job['pid'],signal.SIGTERM)
        except ProcessLookupError:pass
        atomic_json(JOB,dict(job,state='FAILED',finished=time.time(),code='SPEED-WORKER-TIMEOUT'))


def start(arguments,automatic=False):
    with control_lock():
        data=inventory();values=settings(data)
        if values.get('speed_enabled')!='1':return {'accepted':False,'code':'SPEED-DISABLED'}
        if automatic and values.get('speed_auto_new')!='1':return {'accepted':False,'code':'SPEED-AUTO-DISABLED'}
        try:options=validate_request(arguments,data['profiles'])
        except SpeedError as error:return {'accepted':False,'code':error.code}
        if options['budget_mib']>value_int(values,'speed_budget_mib',8,1,32) or options['duration']>value_int(values,'speed_duration',5,2,15) or options['streams']>value_int(values,'speed_streams',2,1,4):
            return {'accepted':False,'code':'SPEED-CONFIG-LIMIT'}
        now=time.time()
        old=read_json(JOB,{})
        if now<1704067200:return {'accepted':False,'code':'SPEED-CLOCK-UNSET'}
        if old.get('started',0)>now+5:return {'accepted':False,'code':'SPEED-CLOCK-BACKWARD'}
        if active_job():return {'accepted':False,'code':'SPEED-BUSY'}
        from speed_pause import public as pause_status
        if pause_status().get('active'):return {'accepted':False,'code':'SPEED-PAUSE-BUSY'}
        if now-old.get('started',0)<(300 if automatic else 60):return {'accepted':False,'code':'SPEED-COOLDOWN'}
        native=read_json(RUNTIME/'native-status.json',{})
        if native.get('state') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):return {'accepted':False,'code':'SPEED-SWITCH-IN-PROGRESS'}
        # CPU admission is measured by the worker after the two quiet-window
        # acknowledgements. The minute load average still contains our own work.
        traffic=read_json(RUNTIME/'speed-traffic.json',{})
        if not isinstance(traffic.get('rate_bps'),(int,float)) or not 0<=time.monotonic()-traffic.get('monotonic',0)<=90:
            return {'accepted':False,'code':'SPEED-TRAFFIC-UNKNOWN'}
        if traffic['rate_bps']>value_int(values,'speed_busy_mbps',2,1,1000)*1e6:
            return {'accepted':False,'code':'SPEED-TRAFFIC-BUSY'}
        quota=options['budget_mib']*MIB*len(options['profiles'])
        daily=value_int(values,'speed_daily_mib',128,1,1024)*MIB
        try:used=reserve_quota(quota,daily,now)
        except SpeedError as error:return {'accepted':False,'code':error.code}
        tx=uuid.uuid4().hex
        duration=35+min(300,len(options['profiles'])*(2*options['duration']+15))
        job=dict(options,state='QUEUED',tx=tx,started=now,deadline=now+duration,monotonic_deadline=time.monotonic()+duration,
                 quota_reserved_bytes=quota,daily_reserved_bytes=used,automatic=automatic)
        atomic_json(JOB,job)
        try:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'run',tx],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            # Child progress uses the same lock; parent PID publication cannot overwrite it.
            job['pid']=process.pid;atomic_json(JOB,job)
            return {'accepted':True,'queued':True,'run_id':tx,'payload_budget_bytes':quota}
        except (OSError,subprocess.SubprocessError):
            atomic_json(JOB,dict(job,state='FAILED',code='SPEED-WORKER-START'))
            return {'accepted':False,'code':'SPEED-WORKER-START'}


def cancel():
    with control_lock():
        job=read_json(JOB,{})
        if not active_job():return {'queued':False,'code':'SPEED-NOT-RUNNING'}
        atomic_json(CANCEL,{'tx':job['tx'],'time':time.time()})
        return {'queued':True}


def observe_traffic(rows,scope='vpn'):
    """Sample unique VPN device counters in RAM; counter resets remain unknown."""
    from agent import SAFE
    path=RUNTIME/'speed-traffic.json';old=read_json(path,{})
    counters={};now=time.monotonic()
    for row in rows:
        device=row.get('device')
        if not isinstance(device,str) or not SAFE.fullmatch(device) or len(device)>15 or device in counters:continue
        try:
            root=Path('/sys/class/net')/device/'statistics'
            counters[device]=int((root/'rx_bytes').read_text())+int((root/'tx_bytes').read_text())
        except (OSError,ValueError):continue
    elapsed=now-old.get('monotonic',now);previous=old.get('counters',{})
    valid=bool(counters) and set(counters)==set(previous) and 0<elapsed<=90 and all(counters[k]>=previous[k] for k in counters)
    rate=8*sum(counters[k]-previous[k] for k in counters)/elapsed if valid else None
    atomic_json(path,{'monotonic':now,'counters':counters,'rate_bps':rate,'scope':scope})


def automatic_new(rows,previous):
    """First observation is baseline; busy tests stay pending without reconnecting."""
    active={row['id'] for row in rows if row.get('interface')}
    values=settings()
    if previous is None or values.get('speed_enabled')!='1' or values.get('speed_auto_new')!='1':return active
    path=RUNTIME/'speed-auto-pending.json'
    pending=set(read_json(path,{}).get('profiles',[]))&active
    pending|=active-previous
    selected=sorted(pending)[:8]
    if selected:
        args={'profiles':selected,'budget_mib':value_int(values,'speed_budget_mib',8,1,32),
              'duration':value_int(values,'speed_duration',5,2,15),'streams':value_int(values,'speed_streams',2,1,4)}
        result=start(args,automatic=True)
        if result.get('accepted'):pending-=set(selected)
        atomic_json(path,{'profiles':sorted(pending)[:32],'last_code':result.get('code')})
    return active


class LiveProgress:
    """Measured payload rates in RAM only, bounded and bound to one job/profile."""
    def __init__(self,job):
        self.job=job;self.lock=threading.Lock();self.starts={}
        job['live']=[{'id':identifier,'phase':'waiting','samples':[]} for identifier in job['profiles']]

    def phase(self,identifier,phase):
        with self.lock:
            row=next(r for r in self.job['live'] if r['id']==identifier)
            self.starts.setdefault(identifier,time.monotonic())
            row.update(phase=phase,updated=time.time());self.job['current_profile']=identifier
            publish_job(self.job)

    def sample(self,identifier,direction,mbps,total):
        with self.lock:
            if not math.isfinite(mbps) or not 0<=mbps<=10000000:return
            row=next(r for r in self.job['live'] if r['id']==identifier)
            elapsed=round(time.monotonic()-self.starts[identifier],3)
            row['samples']=(row['samples']+[[elapsed,round(mbps,3) if direction=='download' else None,round(mbps,3) if direction=='upload' else None]])[-128:]
            row.update(updated=time.time());row[direction+'_mbps']=round(mbps,3);row[direction+'_bytes']=total
            publish_job(self.job)

    def finish(self,identifier,code=None):
        with self.lock:
            row=next(r for r in self.job['live'] if r['id']==identifier)
            row.update(phase='cancelled' if code=='SPEED-CANCELLED' else 'failed' if code else 'done',code=code,updated=time.time())
            publish_job(self.job)


def public_live(job=None):
    """Read-only lightweight snapshot; never probes, reserves quota or loads flash history."""
    job=read_json(JOB,{}) if job is None else job
    if not isinstance(job,dict):return {'state':'IDLE','profiles':[],'server_time':time.time()}
    tx=job.get('tx');ids=job.get('profiles',[])
    if not isinstance(tx,str) or not re.fullmatch(r'[a-f0-9]{32}',tx) or not isinstance(ids,list) or not 1<=len(ids)<=8 or len(set(i for i in ids if isinstance(i,str)))!=len(ids) or any(not isinstance(i,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,96}',i) for i in ids):return {'state':'IDLE','profiles':[],'server_time':time.time()}
    result={'run_id':tx,'state':job.get('state') if job.get('state') in ('QUEUED','RUNNING','DONE','FAILED','CANCELLED') else 'FAILED','profiles':[],'server_time':time.time()}
    if result['state']=='RUNNING' and not worker_alive(job):result.update(state='FAILED',code='SPEED-WORKER-LOST')
    if result['state']=='QUEUED' and not worker_alive(job) and (type(job.get('started')) not in (int,float) or not math.isfinite(job['started']) or time.time()-job['started']>=10):result.update(state='FAILED',code='SPEED-WORKER-LOST')
    def number(v,limit):return type(v) in (int,float) and math.isfinite(v) and 0<=v<=limit
    for raw in (job.get('live',[]) if isinstance(job.get('live'),list) else [])[:8]:
        if not isinstance(raw,dict) or raw.get('id') not in ids or any(r['id']==raw['id'] for r in result['profiles']):continue
        row={'id':raw['id'],'phase':raw.get('phase') if raw.get('phase') in ('waiting','resolving','latency','download','upload','done','failed','cancelled') else 'failed','samples':[]}
        samples=raw.get('samples',[])
        if isinstance(samples,list) and len(samples)<=128:
            previous=-1
            for point in samples:
                if not isinstance(point,list) or len(point)!=3 or not number(point[0],300) or point[0]<previous or any(v is not None and not number(v,10000000) for v in point[1:]) or sum(v is not None for v in point[1:])!=1:continue
                row['samples'].append(point);previous=point[0]
        for key in ('download_mbps','upload_mbps'):
            if number(raw.get(key),10000000):row[key]=raw[key]
        if number(raw.get('updated'),4102444800):row['updated']=raw['updated']
        if isinstance(raw.get('code'),str) and re.fullmatch(r'SPEED-[A-Z0-9-]{1,64}',raw['code']):row['code']=raw['code']
        result['profiles'].append(row)
    if isinstance(job.get('code'),str) and re.fullmatch(r'SPEED-[A-Z0-9-]{1,64}',job['code']):result['code']=job['code']
    if job.get('preparation')in('pausing','testing'):result['preparation']=job['preparation']
    return result


def public_status():
    expire_worker()
    job=read_json(JOB,{})
    result={key:job[key] for key in ('state','started','finished','code','profiles','payload_budget_bytes','quota_reserved_bytes','daily_reserved_bytes','completed','automatic','preparation','cpu_percent_after_pause') if key in job}
    if job.get('state') in ('QUEUED','RUNNING') and not active_job():result.update(state='FAILED',code='SPEED-WORKER-LOST')
    result['live']=public_live(job)
    try:result.update(load_history())
    except SpeedError as error:result.update(results=[],history_error=error.code)
    return result


def run(tx):
    from native_switch import configure_timezone
    configure_timezone()
    if not re.fullmatch(r'[a-f0-9]{32}',tx):return
    job=read_json(JOB,{})
    if job.get('tx')!=tx or job.get('state')!='QUEUED':return

    quiet_acquired=False
    def cancelled():
        from speed_pause import interrupted
        return (read_json(CANCEL,{}).get('tx')==tx or time.monotonic()>=job['monotonic_deadline']
                or read_json(JOB,{}).get('tx')!=tx or quiet_acquired and interrupted(tx))
    job.update(pid=os.getpid(),completed=0,preparation='pausing')
    if not publish_job(job):return
    rows=[];live=LiveProgress(job)
    publish_job(job)
    try:
        from speed_pause import acquire, cpu_usage, PauseError
        acquire(job);quiet_acquired=True
        usage=cpu_usage();job['cpu_percent_after_pause']=usage
        if cancelled():raise SpeedError('SPEED-CANCELLED')
        if usage>75:raise SpeedError('SPEED-CPU-BUSY')
        job.update(state='RUNNING',preparation='testing');publish_job(job)
        for identifier in job['profiles']:
            if cancelled():break
            data=inventory();profile=next((p for p in data['profiles'] if p['id']==identifier),None)
            custom=next((s for s in data.get('servers',[]) if s.get('profile')==identifier),{})
            if profile:profile=dict(profile,name=custom.get('name') or profile['name'],channel=custom.get('channel') or 'default')
            if not profile:raise SpeedError('SPEED-PROFILES-CHANGED')
            rows.append(measure(profile,job,cancelled,live));job['completed']=len(rows);publish_job(job)
        if rows:
            with control_lock():append_history(rows)
        job.update(state='CANCELLED' if cancelled() else 'DONE',finished=time.time(),
                   code='SPEED-CANCELLED' if cancelled() else 'SPEED-COMPLETE')
        publish_job(job)
    except (SpeedError,OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        code=error.code if isinstance(error,SpeedError) else str(error)if isinstance(error,PauseError)else 'SPEED-SYSTEM'
        publish_job(dict(job,state='FAILED',finished=time.time(),code=code))
    finally:
        # Withdrawal grants no new Start: original intent is never overwritten.
        # The monitor resumes first; Auto waits for its post-test observation.
        from speed_pause import release
        release(tx)


if __name__=='__main__' and len(sys.argv)==3 and sys.argv[1]=='run':
    run(sys.argv[2])
