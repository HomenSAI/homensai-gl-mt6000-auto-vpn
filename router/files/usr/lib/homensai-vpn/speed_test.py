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


def request(binding,address,direction,amount,deadline,cancelled):
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
        return received


def stage(binding,address,direction,budget,duration,streams,cancelled,transport=request):
    quota=Budget(budget);started=time.monotonic();deadline=started+duration

    def stream():
        total=0
        while time.monotonic()<deadline and not cancelled():
            amount=quota.take(MIB)
            if not amount:break
            total+=transport(binding,address,direction,amount,deadline,cancelled)
        return total
    with ThreadPoolExecutor(max_workers=streams) as pool:
        futures=[pool.submit(stream) for _ in range(streams)]
        total=sum(future.result() for future in futures)
    elapsed=time.monotonic()-started
    if cancelled():raise SpeedError('SPEED-CANCELLED')
    if total<=0 or elapsed<=0:raise SpeedError('SPEED-NO-SAMPLE')
    return {'payload_bytes':total,'seconds':round(elapsed,3),'mbps':round(total*8/elapsed/1e6,3)}


def measure(profile,options,cancelled):
    row={'id':profile['id'],'name':profile['name'],'protocol':profile['protocol'],'channel':profile.get('channel','default'),'time':time.time(),
         'endpoint':HOST,'method':'bounded-HTTPS-payload-goodput','scope':'router-originated-IPv4',
         'payload_budget_bytes':options['budget_mib']*MIB,'overhead_in_budget':False}
    if not profile.get('interface'):return dict(row,code='SPEED-PROFILE-INACTIVE')
    try:
        binding=route_binding(profile['interface'])
        if binding.get('code'):return dict(row,code='SPEED-ROUTE-UNVERIFIED')
        address=resolve_endpoint(binding,time.monotonic()+6)
        latencies=[]
        for _ in range(3):
            start=time.monotonic();request(binding,address,'download',0,start+3,cancelled);latencies.append((time.monotonic()-start)*1000)
        row['latency_ms']=round(sorted(latencies)[1],1)
        budget=options['budget_mib']*MIB;down=budget*3//4
        row['download']=stage(binding,address,'download',down,options['duration'],options['streams'],cancelled)
        row['upload']=stage(binding,address,'upload',budget-down,options['duration'],options['streams'],cancelled)
        return dict(row,code=None)
    except SpeedError as error:return dict(row,code=error.code)
    except (OSError,ValueError,KeyError,http.client.HTTPException,subprocess.SubprocessError):return dict(row,code='SPEED-NETWORK')


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
        if now-old.get('started',0)<(300 if automatic else 60):return {'accepted':False,'code':'SPEED-COOLDOWN'}
        native=read_json(RUNTIME/'native-status.json',{})
        if native.get('state') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):return {'accepted':False,'code':'SPEED-SWITCH-IN-PROGRESS'}
        if os.getloadavg()[0]>max(1,os.cpu_count() or 1)*.75:return {'accepted':False,'code':'SPEED-CPU-BUSY'}
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
        duration=min(300,len(options['profiles'])*(2*options['duration']+15))
        job=dict(options,state='QUEUED',tx=tx,started=now,deadline=now+duration,monotonic_deadline=time.monotonic()+duration,
                 quota_reserved_bytes=quota,daily_reserved_bytes=used,automatic=automatic)
        atomic_json(JOB,job)
        try:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'run',tx],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            # Child progress uses the same lock; parent PID publication cannot overwrite it.
            job['pid']=process.pid;atomic_json(JOB,job)
            return {'accepted':True,'queued':True,'payload_budget_bytes':quota}
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


def public_status():
    expire_worker()
    job=read_json(JOB,{})
    result={key:job[key] for key in ('state','started','finished','code','profiles','payload_budget_bytes','quota_reserved_bytes','daily_reserved_bytes','completed','automatic') if key in job}
    if job.get('state') in ('QUEUED','RUNNING') and not active_job():result.update(state='FAILED',code='SPEED-WORKER-LOST')
    try:result.update(load_history())
    except SpeedError as error:result.update(results=[],history_error=error.code)
    return result


def run(tx):
    from native_switch import configure_timezone
    configure_timezone()
    if not re.fullmatch(r'[a-f0-9]{32}',tx):return
    job=read_json(JOB,{})
    if job.get('tx')!=tx or job.get('state')!='QUEUED':return

    def cancelled():
        return (read_json(CANCEL,{}).get('tx')==tx or time.monotonic()>=job['monotonic_deadline'] or read_json(JOB,{}).get('tx')!=tx)
    job.update(state='RUNNING',pid=os.getpid(),completed=0)
    if not publish_job(job):return
    rows=[]
    try:
        for identifier in job['profiles']:
            if cancelled():break
            data=inventory();profile=next((p for p in data['profiles'] if p['id']==identifier),None)
            custom=next((s for s in data.get('servers',[]) if s.get('profile')==identifier),{})
            if profile:profile=dict(profile,name=custom.get('name') or profile['name'],channel=custom.get('channel') or 'default')
            if not profile:raise SpeedError('SPEED-PROFILES-CHANGED')
            rows.append(measure(profile,job,cancelled));job['completed']=len(rows);publish_job(job)
        if rows:
            with control_lock():append_history(rows)
        job.update(state='CANCELLED' if cancelled() else 'DONE',finished=time.time(),
                   code='SPEED-CANCELLED' if cancelled() else 'SPEED-COMPLETE')
        publish_job(job)
    except (SpeedError,OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        code=error.code if isinstance(error,SpeedError) else 'SPEED-SYSTEM'
        publish_job(dict(job,state='FAILED',finished=time.time(),code=code))


if __name__=='__main__' and len(sys.argv)==3 and sys.argv[1]=='run':
    run(sys.argv[2])
