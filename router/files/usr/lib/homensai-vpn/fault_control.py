"""Bounded operator fault injection. Kernel set timeout is the independent safety net.

Only a certified observing native trial can request a fault. VPN services, keys,
Kill Switch, INPUT and management routes are not changed. Private RAM nonce
binds the watchdog and table ownership; it is never returned by public status.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid
from agent import RUNTIME,PERSIST,atomic_json,read_json,inventory,route_binding,checksum
from auto_control import control_lock

TABLE='homensai_vpn_fault'
MARKER='homensai-owned-fault-'
SAFE=re.compile(r'^[A-Za-z0-9_]{1,15}$')

class FaultError(Exception):
    pass


def history():
    envelope=read_json(PERSIST/'fault-history.json',{})
    if not envelope:return []
    data=envelope.get('data')
    if not isinstance(data,list) or len(data)>100 or envelope.get('sha256')!=checksum(data):raise FaultError('FAULT-HISTORY-CORRUPT')
    return data


def event(code,intent):
    # Called under the own control lock; independent from the native history writer.
    try:
        rows=history();rows.append({'time':time.time(),'code':code,'profiles':intent.get('profiles',[])[:8],'scope':intent.get('scope','profile'),'duration':intent.get('duration')})
        rows=rows[-100:];atomic_json(PERSIST/'fault-history.json',{'data':rows,'sha256':checksum(rows)})
        return None
    except (FaultError,OSError,ValueError):return 'FAULT-HISTORY-UNAVAILABLE'


def load():
    envelope=read_json(RUNTIME/'fault-intent.json',{})
    if not envelope:return {}
    data=envelope.get('data')
    if not isinstance(data,dict) or envelope.get('sha256')!=checksum(data):raise FaultError('FAULT-STATE-CORRUPT')
    if not re.fullmatch(r'[a-f0-9]{32}',str(data.get('nonce',''))):raise FaultError('FAULT-STATE-CORRUPT')
    return data


def store(data):atomic_json(RUNTIME/'fault-intent.json',{'data':data,'sha256':checksum(data)})


def script(devices,duration,nonce):
    if not devices or len(devices)>8 or any(not isinstance(d,str) or not SAFE.fullmatch(d) for d in devices) or type(duration) is not int or not 1<=duration<=180 or not re.fullmatch(r'[a-f0-9]{32}',nonce):raise FaultError('FAULT-UNSAFE-SCOPE')
    elements=', '.join('"'+d+'" timeout '+str(duration)+'s' for d in sorted(set(devices)))
    return ('table inet '+TABLE+' {\n set fault_devs {\n type ifname; flags timeout; timeout '+str(duration)+'s; elements = { '+elements+' };\n }\n'
            ' chain fault_out {\n type filter hook output priority -305; policy accept;\n meta nfproto ipv4 oifname @fault_devs counter drop comment "'+MARKER+nonce+'";\n }\n'
            ' chain fault_fwd {\n type filter hook forward priority -305; policy accept;\n meta nfproto ipv4 iifname "br-lan" oifname @fault_devs counter drop comment "'+MARKER+nonce+'";\n }\n}\n')



class Nft:
    def contents(self):
        result=subprocess.run(['nft','list','table','inet',TABLE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        if result.returncode==0:return result.stdout.decode(errors='replace')
        if result.returncode==1:return None
        raise FaultError('FAULT-NFT-QUERY-FAILED')
    def apply(self,devices,duration,nonce):
        if self.contents() is not None:raise FaultError('FAULT-TABLE-ALREADY-EXISTS')
        value=script(devices,duration,nonce)
        RUNTIME.mkdir(mode=0o700,parents=True,exist_ok=True)
        descriptor,name=tempfile.mkstemp(prefix='fault-',suffix='.nft',dir=str(RUNTIME))
        try:
            with os.fdopen(descriptor,'w') as stream:stream.write(value)
            for args in (['nft','-c','-f',name],['nft','-f',name]):
                result=subprocess.run(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                if result.returncode:raise FaultError('FAULT-TIMEOUT-RULE-FAILED')
        finally:Path(name).unlink()
        text=self.contents()
        if not text or MARKER+nonce not in text:raise FaultError('FAULT-APPLY-UNCONFIRMED')
    def cleanup(self,nonce):
        text=self.contents()
        if text is None:return True
        if MARKER+nonce not in text:raise FaultError('FAULT-FOREIGN-TABLE')
        result=subprocess.run(['nft','delete','table','inet',TABLE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        if result.returncode or self.contents() is not None:raise FaultError('FAULT-CLEANUP-UNCONFIRMED')
        return True


def eligibility(arguments,data,status,native,settings,selection,blockers,now):
    if set(arguments)!={'profile','scope','duration'} or not isinstance(arguments['profile'],str) or arguments['scope'] not in ('profile','channel') or type(arguments['duration']) is not int or not 30<=arguments['duration']<=180:raise FaultError('FAULT-FIELDS')
    if blockers:raise FaultError('FAULT-NATIVE-PREREQUISITES')
    if native.get('state')!='OBSERVING' or native.get('certified') is not True or not 0<=now-native.get('time',0)<=30 or not 0<=now-status.get('time',0)<=90:raise FaultError('FAULT-CERTIFIED-AUTO-REQUIRED')
    if settings.get('native_session_loss')!='1':raise FaultError('FAULT-SESSION-CONSENT-REQUIRED')
    from native_switch import deadline
    if deadline(settings.get('native_until'))<now+arguments['duration']+90:raise FaultError('FAULT-WINDOW-TOO-SHORT')
    if not selection or arguments['profile']!=selection['source']['id']:raise FaultError('FAULT-NOT-CURRENT-SOURCE')
    profiles={p['id']:p for p in status.get('profiles',[])}
    source=profiles.get(arguments['profile']);target=profiles.get(selection['target']['id'])
    def healthy(p):return p and p.get('interface') and p.get('code') is None and p.get('dns_ok') is True and p.get('https_success',0)>=2 and 0<=now-p.get('time',0)<=90
    if not healthy(source) or not healthy(target):raise FaultError('FAULT-HEALTHY-RESERVE-REQUIRED')
    rows=[source] if arguments['scope']=='profile' else [p for p in profiles.values() if p.get('interface') and p.get('channel','default')==source.get('channel','default')]
    if not 1<=len(rows)<=8 or target['id'] in {row['id'] for row in rows}:raise FaultError('FAULT-WOULD-REMOVE-RESERVE')
    return rows


def start(arguments):
    from native_switch import Linux
    with control_lock():
        old=load();engine=Nft();now=time.time();mono=time.monotonic()
        if old:
            result=read_json(RUNTIME/'fault-result.json',{})
            if result.get('nonce')!=old['nonce'] or result.get('cleaned') is not True:
                if mono<old.get('monotonic_until',mono+1):return {'accepted':False,'code':'FAULT-ALREADY-ACTIVE'}
                engine.cleanup(old['nonce'])
        data=inventory();status=read_json(RUNTIME/'status.json',{});native=read_json(RUNTIME/'native-status.json',{})
        backend=Linux();blockers,selection=backend.diagnostic();settings=backend.policy()['settings']
        rows=eligibility(arguments,data,status,native,settings,selection,blockers,now)
        devices=[]
        for row in rows:
            bound=route_binding(row['interface']);device=bound.get('device','')
            if bound.get('code') or not device.startswith(('wg','tun','ovpn','tap')) or not SAFE.fullmatch(device):raise FaultError('FAULT-PATH-UNVERIFIED')
            devices.append(device)
        nonce=uuid.uuid4().hex;duration=arguments['duration']
        intent={'nonce':nonce,'phase':'ARMED','started':now,'until':now+duration,'monotonic_until':mono+duration,'devices':sorted(set(devices)),'profiles':[p['id'] for p in rows],'scope':arguments['scope'],'duration':duration}
        store(intent)
        worker=subprocess.Popen([sys.executable,__file__,'worker',nonce],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        ready=False;end=time.monotonic()+5
        while time.monotonic()<end and worker.poll() is None:
            value=read_json(RUNTIME/'fault-ready.json',{})
            if value.get('nonce')==nonce and value.get('pid')==worker.pid:ready=True;break
            time.sleep(.05)
        if not ready:atomic_json(RUNTIME/'fault-cancel.json',{'nonce':nonce});return {'accepted':False,'code':'FAULT-WATCHDOG-NOT-READY'}
        try:engine.apply(devices,duration,nonce)
        except BaseException:
            atomic_json(RUNTIME/'fault-cancel.json',{'nonce':nonce})
            try:engine.cleanup(nonce)
            except (FaultError,OSError,subprocess.SubprocessError):pass
            raise
        intent.update(phase='ACTIVE');store(intent)
        history_error=event('FAULT-ACTIVE',intent)
        return {'accepted':True,'code':'FAULT-ACTIVE','until':intent['until'],'profiles':intent['profiles'],'kernel_timeout':True,'history_error':history_error,'scope':'IPv4 probe/forward traffic only; VPN process remains up'}


def cancel():
    with control_lock():
        value=load()
        if not value:return {'queued':False,'code':'FAULT-NOT-ACTIVE'}
        atomic_json(RUNTIME/'fault-cancel.json',{'nonce':value['nonce']})
        Nft().cleanup(value['nonce'])
        atomic_json(RUNTIME/'fault-result.json',{'nonce':value['nonce'],'cleaned':True,'code':'FAULT-CANCELLED','time':time.time()})
        history_error=event('FAULT-CANCELLED',value)
        return {'queued':True,'cleaned':True,'code':'FAULT-CANCELLED','history_error':history_error}


def public_status():
    try:
        try:rows=history();history_error=None
        except (FaultError,OSError,ValueError):rows=[];history_error='FAULT-HISTORY-UNAVAILABLE'
        base={'history':rows,'history_error':history_error}
        value=load()
        if not value:return dict(base,state='IDLE')
        result=read_json(RUNTIME/'fault-result.json',{})
        if result.get('nonce')==value['nonce']:return dict(base,**{k:result[k] for k in ('cleaned','code','time') if k in result})
        remaining=max(0,int(value['monotonic_until']-time.monotonic()))
        return dict(base,state=value['phase'] if remaining else 'TIMEOUT-ELAPSED',until=value['until'],remaining_seconds=remaining,profiles=value['profiles'],scope=value['scope'],kernel_timeout=True)
    except (FaultError,OSError,ValueError):return {'state':'UNKNOWN','code':'FAULT-STATE-UNVERIFIED'}


def worker(nonce):
    if not re.fullmatch(r'[a-f0-9]{32}',nonce):raise FaultError('FAULT-WORKER-INVALID')
    value=load()
    if not value or value['nonce']!=nonce:raise FaultError('FAULT-WORKER-STALE')
    atomic_json(RUNTIME/'fault-ready.json',{'nonce':nonce,'pid':os.getpid()})
    while time.monotonic()<value['monotonic_until']:
        if read_json(RUNTIME/'fault-cancel.json',{}).get('nonce')==nonce:break
        time.sleep(.25)
    with control_lock():
        current=load()
        if not current or current['nonce']!=nonce:return
        try:Nft().cleanup(nonce);result={'cleaned':True,'code':'FAULT-CLEANED'}
        except (FaultError,OSError,subprocess.SubprocessError):result={'cleaned':False,'code':'FAULT-CLEANUP-UNCONFIRMED'}
        event(result['code'],current)
        atomic_json(RUNTIME/'fault-result.json',dict(result,nonce=nonce,time=time.time()))

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='worker':worker(sys.argv[2])
    else:raise SystemExit('fixed worker invocation required')
