# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""Serialized UI intent; only the supervisor writes network state.

Resume keeps the existing nonce, certified policy and bounded deadline.
Intent lives in RAM: a UI start never enables unattended reboot startup.
"""
from contextlib import contextmanager
import fcntl
import os
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
    enabled = settings.get('native_enabled') == '1'
    stop_latched = bool(stopped and stopped.get('trial') == settings.get('native_trial'))
    if not request or request.get('trial') != settings.get('native_trial'):
        return enabled, stop_latched
    valid = (request.get('trial') == settings.get('native_trial')
             and request.get('until') == deadline(settings.get('native_until'))
             and isinstance(request.get('time'), (int, float))
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
    from native_switch import Linux, journal_read, deadline
    with control_lock():
        backend = Linux()
        settings = backend.policy()['settings']
        blockers, selection = backend.diagnostic()
        if journal_read().get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING'):
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
    with control_lock(runtime):
        internal=json.loads(command(['/usr/bin/lua','/usr/lib/homensai-vpn/native_policy.lua']))
        settings=internal.get('settings',{})
        # One durable write targets the current trial, including an in-flight worker.
        old=read_json(persist/'native-stop.json',{})
        request=read_json(runtime/'auto-control.json',{})
        if old.get('trial') == settings.get('native_trial') and old.get('requested',0) >= request.get('time',0):
            return {'queued':True,'already_requested':True}
        atomic_json(persist/'native-stop.json',{'requested':time.time(),'trial':settings.get('native_trial')})
        return {'queued':True}


def public_status():
    request=read_json(RUNTIME/'auto-control.json',{})
    stopped=read_json(PERSIST/'native-stop.json',{})
    mode=request.get('mode','off')
    if stopped.get('requested',0) >= request.get('time',0):mode='off'
    return {'requested':mode,'requested_at':max(request.get('time',0),stopped.get('requested',0)),
            'until':request.get('until',0),'reboot_autostart':False}
