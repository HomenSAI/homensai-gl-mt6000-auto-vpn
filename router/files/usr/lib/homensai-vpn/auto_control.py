# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Serialized UI intent; only the supervisor writes network state.

Resume keeps the existing nonce, certified policy and bounded deadline.
Intent lives in RAM: a UI start never enables unattended reboot startup.
"""
from contextlib import contextmanager
import fcntl
import os
import math
import re
import time
import uuid
from agent import RUNTIME, PERSIST, atomic_json, read_json


def normalize_request_source(value):
    return value if isinstance(value,str) and value in ('manual','test','programmatic') else 'unknown'


def action_context(runtime=None,persist=None,now=None):
    """Read-only, allowlisted audit context. Never locks, enables or certifies Auto."""
    runtime=runtime or RUNTIME;persist=persist or PERSIST;now=time.time() if now is None else now
    candidates=[]
    for path,stamp,action in ((runtime/'auto-control.json','time','start'),(runtime/'pair-auto-control.json','time','start'),(persist/'native-stop.json','requested','stop')):
        try:row=read_json(path,{})
        except (OSError,ValueError,TypeError):continue
        if not isinstance(row,dict):continue
        if action=='start' and row.get('mode')!='on':
            if path.name=='pair-auto-control.json' and row.get('mode')=='off':action='stop'
            else:continue
        epoch=row.get(stamp)
        if type(epoch) not in (int,float) or not 0<epoch<=now or not math.isfinite(epoch):continue
        candidates.append({'control_action':action,'control_source':normalize_request_source(row.get('request_source')),'control_time':epoch})
    return max(candidates,key=lambda row:row['control_time']) if candidates else {}


def manual_action_source(runtime,value,now):
    # Audit only: match the active dispatcher request to this transition's pair.
    for filename in ('pair-manual-control.json','manual-control.json'):
        try:row=read_json(runtime/filename,{})
        except (OSError,ValueError,TypeError):continue
        if not isinstance(row,dict) or row.get('state') not in ('CLAIMED','APPLYING','WAIT-CLIENT'):continue
        updated=row.get('updated',row.get('updated_at'))
        if type(updated) not in (int,float) or not now-90<=updated<=now:continue
        pair=row.get('selection') if filename=='pair-manual-control.json' else {'source':row.get('source_id'),'target':row.get('target_id')}
        if isinstance(pair,dict) and all(isinstance(value.get(k),str) and pair.get(k)==value[k] for k in ('source','target')):
            return normalize_request_source(row.get('request_source'))
    return 'unknown'


def valid_stop(record):
    if not isinstance(record,dict):return False
    if not record:return True
    epoch=record.get('requested')
    try:
        if type(epoch) not in (int,float) or not math.isfinite(epoch) or epoch<=0:return False
    except OverflowError:return False
    if 'all_trials' in record and type(record['all_trials']) is not bool:return False
    if 'control_revision_failed' in record and type(record['control_revision_failed']) is not bool:return False
    return record.get('all_trials') is True or isinstance(record.get('trial'),str) and bool(record['trial'])


def revision_locked(directory, rotate=False):
    """Public freshness marker in RAM. Caller owns this directory's control lock."""
    path=directory/'auto-control-revision.json'
    try:record=read_json(path,{})
    except (OSError,ValueError):record={}
    revision=record.get('revision') if isinstance(record,dict) and set(record)=={'revision'} else None
    if rotate or not isinstance(revision,str) or not re.fullmatch(r'[a-f0-9]{32}',revision):
        revision=uuid.uuid4().hex
        atomic_json(path,{'revision':revision})
    return revision


def current_revision(runtime=None, rotate=False):
    runtime=runtime or RUNTIME
    with control_lock(runtime):return revision_locked(runtime,rotate)


@contextmanager


def control_lock(directory=None):
    directory = directory or RUNTIME
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise ValueError('invalid control directory')
    fd = os.open(str(directory/'auto-control.lock'), os.O_CREAT|os.O_RDWR|getattr(os,'O_NOFOLLOW',0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def readiness(settings, certificate, consumed, selection, blockers, now):
    from native_switch import deadline, Refused
    reasons = list(blockers)
    if any(not isinstance(row,dict) for row in (settings,certificate,consumed)):
        return sorted(set(reasons+['START-STATE-UNVERIFIED']))
    try:until = deadline(settings.get('native_until'))
    except Refused as error:
        until=0;reasons.append(str(error))
    if not now < until <= now + 14400:
        reasons.append('BOUNDED-DEADLINE-REQUIRED')
    if settings.get('native_session_loss') != '1':
        reasons.append('SESSION-LOSS-NOT-ACCEPTED')
    if not settings.get('native_trial') or consumed.get('trial') != settings['native_trial']:
        reasons.append('LAN-TRIAL-REQUIRED')
    count=consumed.get('count',0)
    if type(count) is not int or not 0<=count<3:
        reasons.append('TRIAL-ATTEMPT-LIMIT')
    certified_until=certificate.get('until',0)
    from native_proof import matches
    if not isinstance(selection,dict) or not all(isinstance(selection.get(k),dict) for k in ('source','target')) or not all((
        certificate.get('hash') == selection.get('hash'),
        certificate.get('source') == selection.get('source', {}).get('id'),
        certificate.get('target') == selection.get('target', {}).get('id'),
        certificate.get('direction') == selection.get('direction'),
        type(certified_until) in (int,float) and math.isfinite(certified_until) and certified_until >= until,
        certificate.get('settings_hash') == selection.get('settings_hash'),
        matches(certificate,selection),
    )):
        reasons.append('LAN-TRIAL-REQUIRED')
    return sorted(set(reasons))


def effective_intent(settings, stopped, request, now):
    """Malformed, stale/future or different-trial intents cannot enable anything."""
    from native_switch import deadline, Refused
    if any(not isinstance(row, dict) for row in (settings, stopped, request)):
        return False, True
    if not valid_stop(stopped):return False, True
    if stopped.get('control_revision_failed') is True:return False, True
    enabled = settings.get('native_enabled') == '1'
    # An emergency Stop with unknown settings stops the current config-enabled
    # trial too. Only a later explicit UI Start can supersede its durable epoch.
    epoch = stopped.get('requested', 0)
    if stopped.get('all_trials') is True:
        stamp = request.get('time')
        # Only a well-formed later Start for this exact bounded trial can
        # override a global Stop. Malformed records never bypass the latch.
        if not (type(epoch) in (int, float) and math.isfinite(epoch) and epoch > 0
                and request.get('mode') == 'on' and type(stamp) in (int, float)
                and math.isfinite(stamp) and epoch < stamp <= now
                and isinstance(request.get('trial'), str) and request['trial']
                and request['trial'] == settings.get('native_trial')):
            return False, True
    stop_latched = bool(stopped and stopped.get('trial') == settings.get('native_trial'))
    if stop_latched and not (type(epoch) in (int,float) and math.isfinite(epoch) and epoch>0):
        return False, True
    if not request or request.get('trial') != settings.get('native_trial'):
        return enabled, stop_latched
    try:until=deadline(settings.get('native_until'))
    except Refused:return False, True
    valid = (request.get('trial') == settings.get('native_trial')
             and type(request.get('until')) in (int,float) and math.isfinite(request['until'])
             and request['until'] == until
             and type(request.get('time')) in (int, float)
             and math.isfinite(request['time'])
             and 0 < request['time'] <= now
             and request.get('mode') in ('on','off'))
    if not valid:
        return False, True
    if request['mode'] == 'off' or now >= request['until']:
        return False, True
    if stopped.get('trial') == request['trial'] and stopped.get('requested',0) >= request['time']:
        return False, True
    return True, False


def trial_readiness(settings,consumed,selection,blockers,trial,now):
    """A private explicit calibration intent, never a certificate or Auto resume."""
    import hmac,ipaddress
    from native_switch import deadline,Refused
    reasons=list(blockers)
    if (not isinstance(settings,dict)or not isinstance(consumed,dict)or not isinstance(selection,dict)
            or any(not isinstance(selection.get(k),dict)for k in('source','target'))):return sorted(set(reasons+['START-STATE-UNVERIFIED']))
    configured=settings.get('native_trial')
    if (not isinstance(trial,str)or not re.fullmatch('[a-f0-9]{32}',trial)
            or not isinstance(configured,str)or not re.fullmatch('[a-f0-9]{32}',configured)or not hmac.compare_digest(trial,configured)):
        reasons.append('LAN-TRIAL-REQUIRED')
    if consumed.get('trial')==trial:reasons.append('LAN-TRIAL-REQUIRED')
    try:until=deadline(settings.get('native_until'))
    except Refused:until=0
    count=consumed.get('count',0)
    if 'until'in consumed and type(consumed['until'])in(int,float)and math.isfinite(consumed['until'])and consumed['until']!=until and now<until<=now+14400:count=0
    if type(count)is not int or not 0<=count<3:reasons.append('TRIAL-ATTEMPT-LIMIT')
    if not now<until<=now+14400:reasons.append('BOUNDED-DEADLINE-REQUIRED')
    if settings.get('native_session_loss')!='1':reasons.append('SESSION-LOSS-NOT-ACCEPTED')
    if settings.get('native_enabled')!='0':reasons.append('START-STATE-UNVERIFIED')
    try:
        value=settings.get('native_baseline_exit')
        if type(value)is not str or not ipaddress.IPv4Address(value).is_global:raise ValueError()
    except (ValueError,TypeError):reasons.append('LAN-TRIAL-REQUIRED')
    return sorted(set(reasons))


def start(control_revision=None,trial_nonce=None,request_source=None):
    from native_switch import Linux, journal_read, deadline, Refused
    arrived=time.time()
    source='test' if trial_nonce is not None else normalize_request_source(request_source)
    if not isinstance(control_revision,str) or not re.fullmatch(r'[a-f0-9]{32}',control_revision):
        return {'accepted':False,'blockers':['CONTROL-REVISION-STALE']}
    with control_lock():
        if control_revision!=revision_locked(RUNTIME):
            return {'accepted':False,'blockers':['CONTROL-REVISION-STALE']}
        from speed_pause import public as pause_status
        if pause_status().get('active'):return {'accepted':False,'blockers':['SPEED-BUSY']}
    # Read-only diagnostics may be slow. They must not hold the lock needed by
    # Stop; a Stop received during preflight invalidates this pending Start.
    backend = Linux()
    try:
        policy = backend.policy()
        settings = policy['settings']
        if not isinstance(settings,dict):raise ValueError('invalid settings')
        phase=journal_read().get('phase')
    except Refused:return {'accepted':False,'blockers':['JOURNAL-INTEGRITY-FAILED']}
    except (OSError,ValueError,TypeError,KeyError):return {'accepted':False,'blockers':['START-STATE-UNVERIFIED']}
    if phase in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING','RELEASE-PENDING'):
        return {'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']}
    from preparation_control import auto_blocker,auto_prepare
    preparation_reason=auto_blocker()
    if preparation_reason:return {'accepted':False,'blockers':[preparation_reason]}
    # The Auto button sets up what it needs by itself; the owner does nothing else.
    if trial_nonce is None:
        prepared=auto_prepare(settings,control_revision)
        if prepared.get('code'):return {'accepted':False,'blockers':[prepared['code']],'prepared':prepared.get('repaired',[])}
    from pair_auto import MODE, request as pair_request
    if trial_nonce is None and settings.get('pair_auto_mode')==MODE:
        reply=pair_request(control_revision,request_source=source)
        # Owner decision 31.10.2026: the owner's own Start is remembered on flash, so Auto comes back after a power cut
        if source=='manual' and isinstance(reply,dict) and reply.get('accepted') and not reply.get('already_requested'):
            try:
                from boot_resume import remember
                remember()
            except (OSError,ValueError):pass
        return reply
    blockers, selection = backend.diagnostic()
    try:
        consumed=read_json(PERSIST/'native-attempts.json',{})
        reasons = (readiness(settings, read_json(PERSIST/'native-certificate.json',{}),consumed,selection,blockers,time.time())
                   if trial_nonce is None else trial_readiness(settings,consumed,selection,blockers,trial_nonce,time.time()))
    except (OSError,ValueError,TypeError):return {'accepted':False,'blockers':['START-STATE-UNVERIFIED']}
    if reasons:return {'accepted':False,'blockers':reasons}
    with control_lock():
        if control_revision!=revision_locked(RUNTIME):
            return {'accepted':False,'blockers':['CONTROL-REVISION-STALE']}
        # A damaged journal is a refusal with a code, never a traceback.
        try:phase=journal_read().get('phase')
        except Refused:return {'accepted':False,'blockers':['JOURNAL-INTEGRITY-FAILED']}
        if phase in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING','RELEASE-PENDING'):
            return {'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']}
        try:
            old = read_json(RUNTIME/'auto-control.json',{})
            stopped = read_json(PERSIST/'native-stop.json',{})
            if not isinstance(old,dict) or not isinstance(stopped,dict):raise ValueError('invalid intent')
            current_policy=backend.policy()
            current=current_policy['settings']
            if not isinstance(current,dict):raise ValueError('invalid settings')
        except (OSError,ValueError,TypeError,KeyError):return {'accepted':False,'blockers':['START-STATE-UNVERIFIED']}
        epoch=stopped.get('requested',0)
        if not valid_stop(stopped):
            return {'accepted':False,'blockers':['START-STATE-UNVERIFIED']}
        if stopped.get('control_revision_failed') is True:
            return {'accepted':False,'blockers':['CONTROL-REVISION-STALE']}
        if epoch>=arrived:
            return {'accepted':False,'blockers':['STOP-SUPERSEDED-START']}
        if current_policy!=policy:
            return {'accepted':False,'blockers':['START-CONFIG-CHANGED']}
        now = time.time()
        if not arrived<=now<deadline(settings.get('native_until')):
            return {'accepted':False,'blockers':['BOUNDED-DEADLINE-REQUIRED']}
        if old.get('mode') == 'on' and old.get('trial')==settings.get('native_trial') and effective_intent(settings,stopped,old,now) == (True,False):
            return {'accepted':True,'queued':True,'already_requested':True}
        if type(old.get('time')) in (int,float) and old['time']>arrived:
            return {'accepted':False,'blockers':['STOP-SUPERSEDED-START']}
        atomic_json(RUNTIME/'auto-control.json',{'mode':'on','time':now,'request_source':source,
                    'trial':settings['native_trial'],'until':deadline(settings.get('native_until'))})
        return {'accepted':True,'queued':True}


def stop(runtime=None,persist=None,request_source=None):
    runtime=runtime or RUNTIME
    persist=persist or PERSIST
    from agent import command
    import json
    import subprocess
    # Stop must never depend on reading the router settings: if they cannot be read, the trial named by
    # the current start request is latched (an in-flight switch stops on any newer stop latch anyway).
    unverified=False
    try:
        internal=json.loads(command(['/usr/bin/lua','/usr/lib/homensai-vpn/native_policy.lua']))
        trial=internal.get('settings',{}).get('native_trial')
        if trial is not None and not isinstance(trial,str):raise ValueError('invalid trial')
    except (OSError,ValueError,AttributeError,RecursionError,subprocess.SubprocessError):
        trial=None;unverified=True
    with control_lock(runtime):
        revision_error=None
        try:revision_locked(runtime,rotate=True)
        except (OSError,ValueError) as error:revision_error=error
        if (runtime/'pair-auto-control.json').exists():
            # Same serialized Stop cancels preparation and all later hops.
            marker=read_json(runtime/'auto-control-revision.json',{}).get('revision','unverified')
            atomic_json(runtime/'pair-auto-control.json',{'mode':'off','revision':marker,'time':time.time(),'request_source':normalize_request_source(request_source)})
        # The stopped pair no longer consumes its queue. Cancel the exact
        # pending command now; a corrupt result file must never prevent Stop.
        try:
            from pair_manual import terminalize_pending_locked
            terminalize_pending_locked('CANCELLED','CONTROL-REVISION-STALE',runtime=runtime)
        except (OSError,ValueError,TypeError,KeyError):
            pass
        try:request=read_json(runtime/'auto-control.json',{})
        except (OSError,ValueError):request={}
        if not isinstance(request,dict):request={}
        if unverified:trial=request.get('trial')
        # The settings were read before the lock; a start request for another trial since then gets the global latch.
        changed=not unverified and request.get('trial') is not None and request.get('trial')!=trial
        # One durable write targets the current trial, including an in-flight worker.
        try:old=read_json(persist/'native-stop.json',{})
        except (OSError,ValueError):old={}
        if not isinstance(old,dict):old={}
        extra={'settings_unverified':True} if unverified else {}
        previous = old.get('requested')
        requested = request.get('time',0)
        if type(requested) not in (int,float) or not math.isfinite(requested):requested=float('inf')
        needs_global = unverified or not trial or changed
        if (revision_error is None and not old.get('control_revision_failed')
                and old and type(previous) in (int, float) and math.isfinite(previous) and previous > 0
                and (old.get('all_trials') is True or not needs_global and old.get('trial') == trial)
                and previous >= requested):
            return dict({'queued':True,'already_requested':True},**extra)
        floor=previous if type(previous) in (int,float) and math.isfinite(previous) else 0
        record = {'requested':max(time.time(),floor),'trial':trial,'request_source':normalize_request_source(request_source)}
        if revision_error is not None:record['control_revision_failed']=True
        if needs_global or revision_error is not None:
            record['all_trials'] = True
        atomic_json(persist/'native-stop.json',record)
        if revision_error is not None:raise revision_error
        return dict({'queued':True},**extra)


def return_request(runtime=None):
    """Operator asks to leave a held/committed reserve; the supervisor answers with the source health check."""
    runtime=runtime or RUNTIME
    from native_switch import journal_read, Refused
    with control_lock(runtime):
        try:journal=journal_read()
        except (Refused,OSError,ValueError):return {'accepted':False,'code':'JOURNAL-UNVERIFIED'}
        if journal.get('phase') not in ('HELD-ON-RESERVE','COMMITTED'):
            return {'accepted':False,'code':'RETURN-NOT-APPLICABLE'}
        atomic_json(runtime/'native-return.json',{'time':time.time(),'tx':journal.get('tx')})
        return {'accepted':True,'queued':True}


def public_status():
    valid=True
    def record(path):
        nonlocal valid
        try:row=read_json(path,{})
        except (OSError,ValueError):row=None
        if not isinstance(row,dict):valid=False;return {}
        return row
    def stamp(row,key):
        nonlocal valid
        value=row.get(key,0)
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            valid=False;return 0
        return value
    request=record(RUNTIME/'auto-control.json')
    stopped=record(PERSIST/'native-stop.json')
    requested=stamp(request,'time');stop=stamp(stopped,'requested');until=stamp(request,'until')
    mode=request.get('mode','off')
    if mode not in ('on','off'):valid=False
    if stop>=requested:mode='off'
    result=record(RUNTIME/'native-return-result.json')
    return_result=None
    if result:
        request_stamp=stamp(result,'request');result_stamp=stamp(result,'time');code=result.get('code')
        if type(result.get('ok')) is not bool or code is not None and (not isinstance(code,str) or not re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',code)):
            valid=False
        else:return_result={'request':request_stamp,'ok':result['ok'],'code':code,'time':result_stamp}
    try:revision=current_revision()
    except (OSError,ValueError):revision=None
    if stopped.get('control_revision_failed') is True:revision=None
    from pair_auto import intent as pair_intent, public_phase
    try:pair=pair_intent()
    except (OSError,ValueError):pair=None
    if pair and valid and pair.get('revision')==revision and pair.get('time',0)>stop:
        mode=pair['mode'];requested=max(requested,pair['time']);until=0
    # Why the last Start did not take effect: the refusal code, so the page can always name it.
    failure=None
    code_rx=re.compile(r'[A-Z][A-Z0-9_-]{0,95}')
    try:
        if pair and valid and pair.get('mode')=='off' and pair.get('revision')==revision and isinstance(pair.get('failure_code'),str) and code_rx.fullmatch(pair['failure_code']):
            failure={'code':pair['failure_code'],'time':pair['time'] if type(pair.get('time')) in (int,float) and math.isfinite(pair['time']) else 0}
        else:
            from pair_auto import read_state as pair_state
            held=pair_state()
            if valid and held.get('phase')=='HELD' and isinstance(held.get('recovery_error'),str) and code_rx.fullmatch(held['recovery_error']):
                failure={'code':held['recovery_error'],'time':held.get('started',0) if type(held.get('started')) in (int,float) and math.isfinite(held['started']) else 0}
    except (OSError,ValueError,KeyError,TypeError):failure=None
    context=action_context()
    origin=context.get('control_source','unknown') if valid and context.get('control_time')==max(requested,stop) else 'unknown'
    return {'requested':mode if valid else 'unknown','requested_at':max(requested,stop),
            'request_source':origin,'request_action':('start' if mode=='on' else 'stop' if mode=='off' else None) if valid else None,
            'activation_source':origin if mode=='on' else 'unknown',
            'pair_phase':public_phase(),'failure':failure,
            'control_revision':revision,
            'until':until,'reboot_autostart':False,'return_result':return_result}
