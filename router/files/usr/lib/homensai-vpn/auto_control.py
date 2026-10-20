# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
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
from agent import RUNTIME, PERSIST, atomic_json, read_json


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
    from native_switch import deadline
    reasons = list(blockers)
    until = deadline(settings.get('native_until'))
    if not now < until <= now + 14400:
        reasons.append('BOUNDED-DEADLINE-REQUIRED')
    if settings.get('native_session_loss') != '1':
        reasons.append('SESSION-LOSS-NOT-ACCEPTED')
    if not settings.get('native_trial') or consumed.get('trial') != settings['native_trial']:
        reasons.append('LAN-TRIAL-REQUIRED')
    if consumed.get('count', 0) >= 3:
        reasons.append('TRIAL-ATTEMPT-LIMIT')
    if not selection or not all((
        certificate.get('hash') == selection.get('hash'),
        certificate.get('source') == selection.get('source', {}).get('id'),
        certificate.get('target') == selection.get('target', {}).get('id'),
        certificate.get('direction') == selection.get('direction'),
        certificate.get('until', 0) >= until,
        certificate.get('settings_hash') == selection.get('settings_hash'),
    )):
        reasons.append('LAN-TRIAL-REQUIRED')
    return sorted(set(reasons))


def effective_intent(settings, stopped, request, now):
    """Malformed, stale/future or different-trial intents cannot enable anything."""
    from native_switch import deadline
    if any(not isinstance(row, dict) for row in (settings, stopped, request)):
        return False, True
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
    valid = (request.get('trial') == settings.get('native_trial')
             and request.get('until') == deadline(settings.get('native_until'))
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


def start():
    from native_switch import Linux, journal_read, deadline, Refused
    with control_lock():
        backend = Linux()
        settings = backend.policy()['settings']
        blockers, selection = backend.diagnostic()
        # A damaged journal is a refusal with a code, never a traceback.
        try:phase=journal_read().get('phase')
        except Refused:return {'accepted':False,'blockers':['JOURNAL-INTEGRITY-FAILED']}
        if phase in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING','RELEASE-PENDING'):
            return {'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']}
        now = time.time()
        reasons = readiness(settings, read_json(PERSIST/'native-certificate.json',{}),
                            read_json(PERSIST/'native-attempts.json',{}), selection, blockers, now)
        if reasons:
            return {'accepted':False,'blockers':reasons}
        old = read_json(RUNTIME/'auto-control.json',{})
        stopped = read_json(PERSIST/'native-stop.json',{})
        if old.get('mode') == 'on' and effective_intent(settings,stopped,old,now) == (True,False):
            return {'accepted':True,'queued':True,'already_requested':True}
        atomic_json(RUNTIME/'auto-control.json',{'mode':'on','time':now,
                    'trial':settings['native_trial'],'until':deadline(settings.get('native_until'))})
        return {'accepted':True,'queued':True}


def stop(runtime=None,persist=None):
    runtime=runtime or RUNTIME
    persist=persist or PERSIST
    from agent import command
    import json
    import subprocess
    with control_lock(runtime):
        try:request=read_json(runtime/'auto-control.json',{})
        except (OSError,ValueError):request={}
        if not isinstance(request,dict):request={}
        # Stop must never depend on reading the router settings: if they cannot be read, the trial named by
        # the current start request is latched (an in-flight switch stops on any newer stop latch anyway).
        unverified=False
        try:
            internal=json.loads(command(['/usr/bin/lua','/usr/lib/homensai-vpn/native_policy.lua']))
            trial=internal.get('settings',{}).get('native_trial')
        except (OSError,ValueError,AttributeError,subprocess.SubprocessError):
            trial=request.get('trial');unverified=True
        # One durable write targets the current trial, including an in-flight worker.
        try:old=read_json(persist/'native-stop.json',{})
        except (OSError,ValueError):old={}
        if not isinstance(old,dict):old={}
        extra={'settings_unverified':True} if unverified else {}
        previous = old.get('requested')
        requested = request.get('time',0)
        if type(requested) not in (int,float) or not math.isfinite(requested):requested=float('inf')
        needs_global = unverified or not trial
        if (old and type(previous) in (int, float) and math.isfinite(previous) and previous > 0
                and (old.get('all_trials') is True or not needs_global and old.get('trial') == trial)
                and previous >= requested):
            return dict({'queued':True,'already_requested':True},**extra)
        record = {'requested':time.time(),'trial':trial}
        if needs_global:
            record['all_trials'] = True
        atomic_json(persist/'native-stop.json',record)
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
    return {'requested':mode if valid else 'unknown','requested_at':max(requested,stop),
            'until':until,'reboot_autostart':False,'return_result':return_result}
