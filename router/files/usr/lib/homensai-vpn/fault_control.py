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
from contextlib import contextmanager, nullcontext
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
    def apply(self,devices,duration,nonce,commit_guard=None):
        if self.contents() is not None:raise FaultError('FAULT-TABLE-ALREADY-EXISTS')
        value=script(devices,duration,nonce)
        RUNTIME.mkdir(mode=0o700,parents=True,exist_ok=True)
        descriptor,name=tempfile.mkstemp(prefix='fault-',suffix='.nft',dir=str(RUNTIME))
        try:
            with os.fdopen(descriptor,'w') as stream:stream.write(value)
            result=subprocess.run(['nft','-c','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            if result.returncode:raise FaultError('FAULT-TIMEOUT-RULE-FAILED')
            # Slow queries/preflight run outside the control lock. The only
            # mutating command dispatch and nonce/Stop check share its lock.
            with commit_guard() if commit_guard else nullcontext():
                process=subprocess.Popen(['nft','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            wait_nft(process)
        finally:Path(name).unlink()
        text=self.contents()
        if not text or MARKER+nonce not in text:raise FaultError('FAULT-APPLY-UNCONFIRMED')
    def cleanup(self,nonce,claim_nonce=None):
        text=self.contents()
        if text is None:return True
        if MARKER+nonce not in text:raise FaultError('FAULT-FOREIGN-TABLE')
        with control_lock():
            current=load()
            # The contents query was outside the lock. A private claim check
            # fences deletion against a later generation's table installation.
            if (not current or current.get('nonce')!=(claim_nonce or nonce)
                    or claim_nonce and (current.get('phase')!='PREPARING' or current.get('cleanup_nonce')!=nonce)):
                raise FaultError('FAULT-CLAIM-STALE')
            process=subprocess.Popen(['nft','delete','table','inet',TABLE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        wait_nft(process)
        if self.contents() is not None:raise FaultError('FAULT-CLEANUP-UNCONFIRMED')
        return True


def wait_nft(process):
    """Only the private child is waited/killed; no wait holds Stop's lock."""
    try:code=process.wait(timeout=5)
    except BaseException:
        try:process.kill()
        except ProcessLookupError:pass
        try:process.wait(timeout=1)
        except subprocess.TimeoutExpired:raise FaultError('FAULT-COMMAND-UNCONFIRMED') from None
        raise FaultError('FAULT-COMMAND-UNCONFIRMED') from None
    if code:raise FaultError('FAULT-TIMEOUT-RULE-FAILED')


def eligibility(arguments,data,status,native,settings,selection,blockers,now,certificate=None):
    from failure_diagnosis import finite
    if (not all(isinstance(value,dict) for value in (arguments,data,status,native,settings)) or not finite(now)
            or not finite(native.get('time')) or not finite(status.get('time'))):raise FaultError('FAULT-IDENTITY-UNVERIFIED')
    if set(arguments)!={'profile','scope','duration'} or not isinstance(arguments['profile'],str) or arguments['scope'] not in ('profile','channel') or type(arguments['duration']) is not int or not 30<=arguments['duration']<=180:raise FaultError('FAULT-FIELDS')
    if blockers:raise FaultError('FAULT-NATIVE-PREREQUISITES')
    if native.get('state')!='OBSERVING' or native.get('certified') is not True or not 0<=now-native.get('time',0)<=30 or not 0<=now-status.get('time',0)<=90:raise FaultError('FAULT-CERTIFIED-AUTO-REQUIRED')
    if settings.get('native_session_loss')!='1':raise FaultError('FAULT-SESSION-CONSENT-REQUIRED')
    from native_switch import deadline,Refused
    try:until=deadline(settings.get('native_until'))
    except Refused:raise FaultError('FAULT-WINDOW-TOO-SHORT') from None
    if until<now+arguments['duration']+90:raise FaultError('FAULT-WINDOW-TOO-SHORT')
    if not selection or arguments['profile']!=selection['source']['id']:raise FaultError('FAULT-NOT-CURRENT-SOURCE')
    from failure_diagnosis import resolve_pair,profile_identity,finite
    from vendor_observation import current_bindings,tunnel_identity
    try:interval=int(settings.get('interval',30))
    except (ValueError,TypeError,OverflowError):raise FaultError('FAULT-IDENTITY-UNVERIFIED') from None
    if not 10<=interval<=300:raise FaultError('FAULT-IDENTITY-UNVERIFIED')
    pair=resolve_pair(status,settings,now,max(30,min(900,interval*3)),max(30,min(600,interval*2)))
    if pair['coordination']['state']!='READY':raise FaultError('FAULT-IDENTITY-UNVERIFIED')
    bindings=current_bindings(data.get('profiles',[]))
    for role in ('source','target'):
        measured=pair[role];chosen=selection[role];tunnel=tunnel_identity(measured)
        if (not profile_identity(measured) or profile_identity(measured)!=profile_identity(chosen)
                or not tunnel or tunnel not in bindings or bindings[tunnel]['id']!=measured['id']):
            raise FaultError('FAULT-IDENTITY-UNVERIFIED')
    if (native.get('source')!=selection['source']['id'] or native.get('target')!=selection['target']['id']
            or native.get('vendor_identity')!=selection.get('vendor_identity')):
        raise FaultError('FAULT-CERTIFICATE-STALE')
    identity=selection.get('vendor_identity')
    from native_proof import matches
    if (not isinstance(identity,str) or not re.fullmatch(r'[a-f0-9]{64}',identity) or not isinstance(certificate,dict)
            or not matches(certificate,selection) or not matches(native,selection)
            or certificate.get('vendor_identity')!=identity
            or any(certificate.get(key)!=selection.get(key) for key in ('hash','direction','settings_hash'))
            or certificate.get('source')!=selection['source']['id'] or certificate.get('target')!=selection['target']['id']
            or not finite(certificate.get('until')) or certificate['until']<until):
        raise FaultError('FAULT-CERTIFICATE-STALE')
    profiles={p['id']:p for p in status.get('profiles',[])}
    source=profiles.get(arguments['profile']);target=profiles.get(selection['target']['id'])
    def healthy(p):return (isinstance(p,dict) and p.get('interface') and p.get('code') is None
        and p.get('dns_ok') is True and type(p.get('https_success')) is int and p['https_success']>=2
        and finite(p.get('time')) and 0<=now-p['time']<=90)
    if not healthy(source) or not healthy(target):raise FaultError('FAULT-HEALTHY-RESERVE-REQUIRED')
    # Both legacy API scopes select the current tunnel's IPv4 path. An nft
    # oifname rule cannot isolate one provider server inside that tunnel.
    rows=[p for p in profiles.values() if tunnel_identity(p)==tunnel_identity(source)]
    if not 1<=len(rows)<=8 or target['id'] in {row['id'] for row in rows}:raise FaultError('FAULT-WOULD-REMOVE-RESERVE')
    return rows


def require_revision(expected):
    value=read_json(RUNTIME/'auto-control-revision.json',{})
    if (not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{32}',expected) or not isinstance(value,dict)
            or set(value)!={'revision'} or value['revision']!=expected):raise FaultError('FAULT-CONTROL-CHANGED')


def require_auto_on(settings):
    from auto_control import effective_intent
    active,stopped=effective_intent(settings,read_json(PERSIST/'native-stop.json',{}),
                                    read_json(RUNTIME/'auto-control.json',{}),time.time())
    if not active or stopped:raise FaultError('FAULT-CERTIFIED-AUTO-REQUIRED')


def claim_locked(nonce,revision):
    require_revision(revision)
    value=load()
    result=read_json(RUNTIME/'fault-result.json',{})
    cancelled=read_json(RUNTIME/'fault-cancel.json',{})
    if (not value or value.get('nonce')!=nonce or value.get('phase') not in ('PREPARING','ARMED')
            or time.monotonic()>=value.get('monotonic_until',0)
            or isinstance(result,dict) and result.get('nonce')==nonce
            or isinstance(cancelled,dict) and cancelled.get('nonce')==nonce):raise FaultError('FAULT-CLAIM-STALE')
    if value.get('phase')=='ARMED':require_auto_on(value.get('control_settings',{}))
    return value


def verify_bindings(intent):
    """Read-only checks outside the Stop lock; never retarget an active fault."""
    from failure_diagnosis import profile_identity
    from vendor_observation import current_bindings
    require_revision(intent.get('control_revision'))
    require_auto_on(intent.get('control_settings',{}))
    expected=intent.get('vendor_profiles');kernels=intent.get('kernel_bindings')
    if not isinstance(expected,dict) or not isinstance(kernels,dict):raise FaultError('FAULT-IDENTITY-GONE')
    bindings=current_bindings(inventory().get('profiles',[]))
    for role in ('source','target'):
        identity=expected.get(role)
        if not isinstance(identity,dict):raise FaultError('FAULT-IDENTITY-GONE')
        current=bindings.get(identity.get('vendor_tunnel_id'))
        if not current or any(current.get(key)!=identity.get(key) for key in ('id','protocol','interface','vendor_tunnel_id')):
            raise FaultError('FAULT-IDENTITY-GONE')
        live=route_binding(current['interface'])
        if live.get('code') or any(live.get(key)!=kernels.get(role,{}).get(key) for key in ('device','mark','table','ifindex')):
            raise FaultError('FAULT-IDENTITY-GONE')
    require_revision(intent.get('control_revision'))


def failed_claim(nonce,engine,code):
    # Cleanup uses the original private nonce and never a replacement's devices.
    with control_lock():
        current=load()
        if not current or current.get('nonce')!=nonce:return
        atomic_json(RUNTIME/'fault-cancel.json',{'nonce':nonce})
    try:cleaned=engine.cleanup(nonce) is True and code!='FAULT-COMMAND-UNCONFIRMED'
    except (FaultError,OSError,subprocess.SubprocessError):cleaned=False
    with control_lock():
        current=load()
        if current and current.get('nonce')==nonce:
            atomic_json(RUNTIME/'fault-result.json',{'nonce':nonce,'cleaned':cleaned,'code':code,'time':time.time()})


def start(arguments):
    from native_switch import Linux,Refused
    from failure_diagnosis import profile_identity
    nonce=uuid.uuid4().hex;engine=Nft();now=time.time();mono=time.monotonic()
    # Reserve only private RAM metadata. Slow reads and watchdog readiness do
    # not hold the lock needed by Stop or cancellation.
    with control_lock():
        marker=read_json(RUNTIME/'auto-control-revision.json',{})
        revision=marker.get('revision') if isinstance(marker,dict) and set(marker)=={'revision'} else None
        require_revision(revision)
        old=load();result=read_json(RUNTIME/'fault-result.json',{})
        old_cleaned=bool(old and isinstance(result,dict) and result.get('nonce')==old['nonce'] and result.get('cleaned') is True)
        if old and not old_cleaned and mono<old.get('monotonic_until',mono+1):return {'accepted':False,'code':'FAULT-ALREADY-ACTIVE'}
        intent={'nonce':nonce,'phase':'PREPARING','started':now,'until':now+120,'monotonic_until':mono+120,
                'profiles':[],'devices':[],'scope':'channel','duration':0,'control_revision':revision}
        if old and not old_cleaned:intent['cleanup_nonce']=old['nonce']
        store(intent)
    try:
        if old and not old_cleaned:engine.cleanup(old['nonce'],claim_nonce=nonce)
        data=inventory();status=read_json(RUNTIME/'status.json',{});native=read_json(RUNTIME/'native-status.json',{})
        backend=Linux();blockers,selection=backend.diagnostic();settings=backend.policy()['settings']
        require_auto_on(settings)
        rows=eligibility(arguments,data,status,native,settings,selection,blockers,time.time(),
                         read_json(PERSIST/'native-certificate.json',{}))
        kernels={}
        for role in ('source','target'):
            row=selection[role];bound=route_binding(row['interface']);device=bound.get('device','')
            if (bound.get('code') or not device.startswith(('wg','tun','ovpn','tap')) or not SAFE.fullmatch(device)
                    or any(bound.get(key)!=row.get('kernel_binding',{}).get(key) for key in ('device','mark','table','ifindex'))):
                raise FaultError('FAULT-PATH-UNVERIFIED')
            kernels[role]={key:bound.get(key) for key in ('device','mark','table','ifindex')}
        if kernels['source']['device']==kernels['target']['device']:raise FaultError('FAULT-WOULD-REMOVE-RESERVE')
        duration=arguments['duration'];now=time.time();mono=time.monotonic()
        with control_lock():
            claim_locked(nonce,revision)
            intent.update(phase='ARMED',started=now,until=now+duration,monotonic_until=mono+duration,
                profiles=[p['id'] for p in rows],devices=[kernels['source']['device']],scope=arguments['scope'],duration=duration,
                vendor_identity=selection['vendor_identity'],vendor_profiles={role:profile_identity(selection[role]) for role in ('source','target')},
                kernel_bindings=kernels,control_settings={key:settings.get(key) for key in ('native_enabled','native_trial','native_until')})
            store(intent)
        worker=subprocess.Popen([sys.executable,__file__,'worker',nonce],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        ready=False;end=time.monotonic()+5
        while time.monotonic()<end and worker.poll() is None:
            value=read_json(RUNTIME/'fault-ready.json',{})
            if value.get('nonce')==nonce and value.get('pid')==worker.pid:ready=True;break
            require_revision(revision);time.sleep(.05)
        if not ready:raise FaultError('FAULT-WATCHDOG-NOT-READY')
        @contextmanager
        def commit_guard():
            require_revision(revision)
            live_blockers,live_selection=backend.diagnostic()
            live_data=inventory();live_settings=backend.policy()['settings']
            require_auto_on(live_settings)
            eligibility(arguments,live_data,read_json(RUNTIME/'status.json',{}),read_json(RUNTIME/'native-status.json',{}),
                        live_settings,live_selection,live_blockers,time.time(),read_json(PERSIST/'native-certificate.json',{}))
            if live_selection.get('vendor_identity')!=intent['vendor_identity']:raise FaultError('FAULT-IDENTITY-GONE')
            verify_bindings(intent)
            with control_lock():
                claim_locked(nonce,revision)
                yield  # only nft process dispatch, never its wait, is inside
        engine.apply(intent['devices'],duration,nonce,commit_guard=commit_guard)
        with control_lock():
            claim_locked(nonce,revision)
            intent.update(phase='ACTIVE');store(intent)
            history_error=event('FAULT-ACTIVE',intent)
        return {'accepted':True,'code':'FAULT-ACTIVE','until':intent['until'],'profiles':intent['profiles'],
                'kernel_timeout':True,'history_error':history_error,'scope':'current tunnel IPv4 path; VPN process remains up'}
    except BaseException as error:
        code=str(error) if isinstance(error,FaultError) else 'FAULT-START-UNCONFIRMED'
        failed_claim(nonce,engine,code)
        if isinstance(error,Refused):raise FaultError('FAULT-IDENTITY-UNVERIFIED') from None
        raise


def cancel():
    with control_lock():
        value=load()
        if not value:return {'queued':False,'code':'FAULT-NOT-ACTIVE'}
        atomic_json(RUNTIME/'fault-cancel.json',{'nonce':value['nonce']})
    Nft().cleanup(value['nonce'])
    with control_lock():
        current=load()
        if not current or current.get('nonce')!=value['nonce']:return {'queued':True,'cleaned':True,'code':'FAULT-CANCELLED'}
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
    reason='FAULT-CLEANED';next_identity=0
    while time.monotonic()<value['monotonic_until']:
        if read_json(RUNTIME/'fault-cancel.json',{}).get('nonce')==nonce:break
        try:
            require_revision(value.get('control_revision'))
            if time.monotonic()>=next_identity:
                verify_bindings(value);next_identity=time.monotonic()+2
        except FaultError as error:
            reason=str(error);break
        except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
            reason='FAULT-IDENTITY-GONE';break
        time.sleep(.25)
    # Queries/identity reads and the post-delete verification never hold Stop's
    # lock. Nft.cleanup fences just its bounded mutation against new claims.
    try:Nft().cleanup(nonce);result={'cleaned':True,'code':reason}
    except (FaultError,OSError,subprocess.SubprocessError):result={'cleaned':False,'code':'FAULT-CLEANUP-UNCONFIRMED'}
    with control_lock():
        current=load()
        if not current or current['nonce']!=nonce:return
        event(result['code'],current)
        atomic_json(RUNTIME/'fault-result.json',dict(result,nonce=nonce,time=time.time()))

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='worker':worker(sys.argv[2])
    else:raise SystemExit('fixed worker invocation required')
