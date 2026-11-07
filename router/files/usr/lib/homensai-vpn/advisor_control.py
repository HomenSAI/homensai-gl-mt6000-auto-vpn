"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
advisor_control.py: the owner's and the nightly job's way to change the master-slider settings (2.1.0-alpha9).

RPC (agent.rpc -> reply):
  advisor           read: the status field network_advisor (mode, window, current position, the recommendation,
                    the journal summary, the last change) + the curve + the change log
  advisor_apply     {} the recommended position, or {'t': 0..1} a position the owner chose («привязать к ползунку»)
  advisor_settings  {'mode': 'auto'|'advice'|'manual', 'window': 1|7|30} and, for mode 'manual' only, optionally
                    {'theta', 'dur_b', 'pg'}: the owner's own detector values (the slider detaches: «Пользовательская»);
                    optionally {'fast': bool}: the fast segment -0.2 <= t < 0 (the advisor may recommend it) and
                    {'turbo': bool, 'turbo_ack': TURBO_ACK}: the expert opt-in of t <= -0.3 (never by the advisor).
                    Off moves a position beyond the new limit back to it, in the same write.
CLI: advisor_control.py auto-apply   (the Lua nightly job: one auto step from runtime/advisor.json)

Every change goes through setup_save.lua (the single writer of the application's UCI options) under the control
lock, only within the safety rules (advisor.safety: bounds, P(G) >= theta, rescue <= primary_stable, ride-out <
leave time), never during an outage or a switch (advisor.calm_codes on fresh files), and is logged with its reason:
<persist>/advisor-changes.json (the last MAX_CHANGES) and a syslog line ADVISOR-APPLIED. The options it writes are
read by Auto at every decision (backend.policy / inventory.lua); the pair Auto does not compare a settings hash, so
no Stop is needed (unlike the setup wizard, which edits the whole recovery block).
"""
import json
import math
import os
import subprocess
import time
from pathlib import Path

import advisor as A
import netjournal as J

WRITER=['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua']
# The owner's explicit words of the turbo opt-in «минимум простоя, допускаю до ~8 лишних уходов в сутки»
# (~8: the owner's exploratory estimate of 05.11.2026, wider than the simulator's 4.7 at -0.7, not yet measured on a router)
TURBO_ACK='minimum-downtime-up-to-8-extra-switches-a-day'


def control_lock():
    from auto_control import control_lock as lock
    return lock()


def allow(name,seconds):
    from rpc_throttle import allow as throttle
    return throttle(name,seconds)


def refuse(code):
    return {'saved':False,'code':code}


def paths():
    from agent import RUNTIME,PERSIST
    return str(RUNTIME),str(PERSIST)


def read_json(path,default=None):
    try:value=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default
    return value


def manual_pending(runtime):
    """The state of an owner click still waiting for the supervisor (pair or legacy record), or None."""
    for name,pending in (('pair-manual-control.json',('QUEUED','CLAIMED')),('manual-control.json',('QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'))):
        row=read_json(runtime+'/'+name,{})
        if isinstance(row,dict) and row.get('state') in pending:return row['state']
    return None


def calm_now(runtime,now):
    """The calm record of advisor.calm_codes from fresh files: open outages of the journal, the observed route, the
    native state, the transaction phase and an owner click in flight."""
    from route_history import observed_route
    status=read_json(runtime+'/status.json',{})
    today=read_json(runtime+'/'+J.TODAY_NAME,{})
    st=today.get('st') if isinstance(today,dict) else None
    opened=sorted(st['open']) if isinstance(st,dict) and isinstance(st.get('open'),dict) else []
    native=read_json(runtime+'/native-status.json',{})
    calm={'open':opened,'route':observed_route(status,now) if isinstance(status,dict) else 'unknown',
          'native':native.get('state') if isinstance(native,dict) else None,'phase':None,'manual':manual_pending(runtime)}
    try:
        from native_switch import journal_read
        calm['phase']=(journal_read() or {}).get('phase')
    except Exception:  # an unreadable transaction journal is no evidence of calm
        calm['phase']='RESTORING'
    return calm


def changes(persist):
    return A.changes(persist)


def write_changes(persist,rows):
    from agent import atomic_json
    atomic_json(Path(persist)/A.CHANGES_NAME,{'v':1,'changes':rows[-A.MAX_CHANGES:]})


def save(payload):
    try:
        result=subprocess.run(WRITER,input=json.dumps(payload,ensure_ascii=True).encode(),stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL,timeout=10)
    except (OSError,subprocess.SubprocessError):return 'SETUP-SAVE-UNCONFIRMED'
    if result.returncode or result.stdout.strip()!=b'OK':return 'SETUP-SAVE-FAILED'
    return None


def log(line):
    try:subprocess.run(['logger','-t','homensai-vpn',line],timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except (OSError,subprocess.SubprocessError):pass


def settings_now():
    from agent import inventory
    data=inventory()
    settings=data.get('settings') if isinstance(data,dict) else None
    if not isinstance(settings,dict):raise ValueError('ADVISOR-SETTINGS-UNAVAILABLE')
    return settings


def text_number(x):
    return ('%.2f'%x).rstrip('0').rstrip('.') if x%1 else str(int(x))


def slider_options(point,t,settings):
    """The options of a slider position; the fast detectors are written ('0' = off) only when on, or to turn them off."""
    main={'hmm_theta':text_number(point['theta']),'hmm_dur_b':text_number(point['dur_b']),'return_pg':text_number(point['pg']),
          'recovery_primary_stable':str(point['primary_stable']),'recovery_rescue_stable':str(point['rescue_stable']),
          'slider_t':text_number(t)}
    main.update(detector_options(point.get('cons_f'),point.get('beat_k'),settings))
    return main


def detector_options(cons,beats,settings):
    main={}
    if cons is not None or settings.get('hmm_or_failures') is not None:main['hmm_or_failures']=str(cons or 0)
    if beats is not None or settings.get('turbo_beats') is not None:main['turbo_beats']=str(beats or 0)
    return main


def apply(t,source,result=None,now=None,deps=None):
    """Set the slider to t (rounded to 0.01): its settings + slider_t, at the step of the fast segment for t < 0 (the
    limit is A.t_floor: 0 unless the owner enabled it). source 'owner' or 'auto'."""
    deps=deps or {}
    now=time.time() if now is None else now
    runtime,persist=deps.get('paths',paths)()
    with (deps.get('lock') or control_lock)():
        settings=deps.get('settings',settings_now)()
        curve=A.load_curve()
        cur=A.current(settings,curve)
        if cur['failure_model']=='consecutive':return refuse('ADVISOR-MODEL-CONSECUTIVE')
        rows=changes(persist)
        if source=='auto':
            step=A.auto_step(curve,result,settings,rows,deps.get('calm',calm_now)(runtime,now),now)
            if not step['apply'] or step['t']!=t:return refuse(step['code'] or 'ADVISOR-AUTO-STALE')
        if type(t) not in (int,float) or isinstance(t,bool) or not math.isfinite(t) or not A.MIN_T<=t<=1:return refuse('ADVISOR-RANGE')
        t=A.round2(t)
        point=A.interpolate(curve,t)
        t=point['t']
        if t<A.t_floor(settings):return refuse('ADVISOR-FAST-OFF')
        unsafe=A.safety(point)
        if unsafe:return refuse(unsafe[0])
        busy=A.calm_codes(deps.get('calm',calm_now)(runtime,now))
        if busy:return refuse(busy[0])
        if not (deps.get('allow') or allow)('advisor',2):return refuse('RPC-RATE-LIMIT')
        main=slider_options(point,t,settings)
        failed=deps.get('save',save)({'main':main,'servers':[]})
        if failed:return refuse(failed)
        record={'time':float(now),'source':source,'from':cur['slider_t'] if cur['attached'] else None,'from_label':cur['label'],
                'to':t,'params':dict({k:point[k] for k in ('theta','dur_b','pg','primary_stable','rescue_stable')},
                                     **{k:point[k] for k in ('cons_f','beat_k') if point.get(k) is not None}),
                'reason_ru':(result or {}).get('reason_ru') if source=='auto' else 'Положение выбрано владельцем.',
                'reason_en':(result or {}).get('reason_en') if source=='auto' else 'Position chosen by the owner.'}
        deps.get('write_changes',write_changes)(persist,rows+[record])
        deps.get('log',log)('ADVISOR-APPLIED: slider %s -> %s (%s) theta %s dur_B %s P(G) %s primary_stable %s rescue_stable %s or_failures %s beats %s'
                            %('-' if record['from'] is None else text_number(record['from']),text_number(t),source,main['hmm_theta'],
                              main['hmm_dur_b'],main['return_pg'],main['recovery_primary_stable'],main['recovery_rescue_stable'],
                              main.get('hmm_or_failures','-'),main.get('turbo_beats','-')))
    return {'saved':True,'t':t,'code':None,'params':record['params']}


def apply_auto(t,result):
    """advisor.run in the Python fallback: one auto step."""
    try:return apply(t,'auto',result)
    except (OSError,ValueError) as error:return refuse(str(error) if str(error).startswith('ADVISOR-') else 'ADVISOR-APPLY-FAILED')


def manual(arguments,now=None,deps=None):
    """The owner's own detector values (mode manual): hmm_theta / hmm_dur_b / return_pg, the slider detached."""
    deps=deps or {}
    now=time.time() if now is None else now
    runtime,persist=deps.get('paths',paths)()
    values={}
    for key,(low,high) in (('theta',A.SAFE['theta']),('dur_b',A.SAFE['dur_b']),('pg',A.SAFE['pg'])):
        v=arguments.get(key)
        if type(v) not in (int,float) or isinstance(v,bool) or not math.isfinite(v) or not low<=v<=high:return refuse('ADVISOR-RANGE')
        values[key]=float(v)
    values['theta']=A.round2(values['theta']);values['pg']=A.round2(values['pg']);values['dur_b']=A.round_step(values['dur_b'],0.5)
    with (deps.get('lock') or control_lock)():
        settings=deps.get('settings',settings_now)()
        cur=A.current(settings,A.load_curve())
        params=dict(values,primary_stable=cur['primary_stable'],rescue_stable=cur['rescue_stable'])
        unsafe=A.safety(params)
        if unsafe:return refuse(unsafe[0])
        busy=A.calm_codes(deps.get('calm',calm_now)(runtime,now))
        if busy:return refuse(busy[0])
        if not (deps.get('allow') or allow)('advisor',2):return refuse('RPC-RATE-LIMIT')
        main={'advisor_mode':'manual','hmm_theta':text_number(values['theta']),'hmm_dur_b':text_number(values['dur_b']),
              'return_pg':text_number(values['pg'])}
        main.update(detector_options(None,None,settings))  # own values: no hidden detector of the slider stays on
        # uci delete of an absent option is no success: only a set position is removed
        failed=deps.get('save',save)({'main':main,'servers':[],'delete':['slider_t'] if settings.get('slider_t') is not None else []})
        if failed:return refuse(failed)
        rows=changes(persist)
        record={'time':float(now),'source':'owner-manual','from':cur['slider_t'] if cur['attached'] else None,'from_label':cur['label'],
                'to':None,'params':params,'reason_ru':'Значения заданы владельцем вручную.','reason_en':'Values set by the owner.'}
        deps.get('write_changes',write_changes)(persist,rows+[record])
        deps.get('log',log)('ADVISOR-APPLIED: custom theta %s dur_B %s P(G) %s (owner)'%(main['hmm_theta'],main['hmm_dur_b'],main['return_pg']))
    return {'saved':True,'code':None,'params':params}


def segment_options(arguments,settings,curve,calm):
    """The owner's switches of the fast end -> (options, code). Enabling changes nothing by itself (a position is a
    separate choice); turning a segment off takes its detectors away and moves a position beyond the new limit, which
    happens only in a calm moment. Turbo implies the fast segment; it needs the explicit words TURBO_ACK."""
    from channel_model import turbo_on
    fast=A.fast_enabled(settings);turbo=turbo_on(settings)
    if 'fast' in arguments:
        if type(arguments['fast']) is not bool:return None,'ADVISOR-RANGE'
        fast=arguments['fast']
    if 'turbo' in arguments:
        if type(arguments['turbo']) is not bool:return None,'ADVISOR-RANGE'
        turbo=arguments['turbo']
        if turbo and arguments.get('turbo_ack')!=TURBO_ACK:return None,'ADVISOR-TURBO-ACK'
    if turbo and not fast:
        if 'fast' in arguments:return None,'ADVISOR-FIELDS'
        fast=True
    main={'slider_fast':'1' if fast else '0','slider_turbo':'1' if turbo else '0'}
    new=dict(settings,slider_fast=fast,slider_turbo=turbo)
    t=A.slider_t(settings);floor=A.t_floor(new)
    moved=t is not None and t<floor
    drops=(not fast and settings.get('hmm_or_failures') is not None) or (not turbo and settings.get('turbo_beats') is not None)
    if moved or drops:
        busy=A.calm_codes(calm)
        if busy:return None,busy[0]
    if moved:
        point=A.interpolate(curve,floor)
        main.update(slider_options(point,point['t'],settings))
    else:
        if not fast and settings.get('hmm_or_failures') is not None:main['hmm_or_failures']='0'
        if not turbo and settings.get('turbo_beats') is not None:main['turbo_beats']='0'
    return main,None


def settings_reply(arguments,deps=None):
    deps=deps or {}
    if not isinstance(arguments,dict) or not {'mode','window'}<=set(arguments)<={'mode','window','theta','dur_b','pg','fast','turbo','turbo_ack'}:
        return refuse('ADVISOR-FIELDS')
    mode,window=arguments['mode'],arguments['window']
    if mode not in A.MODES or type(window) is not int or window not in A.WINDOWS:return refuse('ADVISOR-RANGE')
    numeric={'theta','dur_b','pg'}&set(arguments)
    if numeric and (mode!='manual' or numeric!={'theta','dur_b','pg'}):return refuse('ADVISOR-FIELDS')
    if 'turbo_ack' in arguments and 'turbo' not in arguments:return refuse('ADVISOR-FIELDS')
    if numeric:
        result=manual(arguments,deps=deps)
        if not result['saved']:return result
    with (deps.get('lock') or control_lock)():
        if not numeric and not (deps.get('allow') or allow)('advisor-settings',2):return refuse('RPC-RATE-LIMIT')
        main={'advisor_mode':mode,'advisor_window':str(window)}
        if {'fast','turbo'}&set(arguments):
            runtime,_=deps.get('paths',paths)()
            settings=deps.get('settings',settings_now)()
            options,code=segment_options(arguments,settings,A.load_curve(),deps.get('calm',calm_now)(runtime,time.time()))
            if code:return refuse(code)
            main.update(options)
        failed=deps.get('save',save)({'main':main,'servers':[]})
    if failed:return refuse(failed)
    return {'saved':True,'code':None,'mode':mode,'window':window}


def read_reply(deps=None):
    deps=deps or {}
    runtime,persist=deps.get('paths',paths)()
    settings=deps.get('settings',settings_now)()
    curve=A.load_curve()
    journal=J.load(A.read_text(runtime+'/'+J.DAYS_NAME),A.read_text(runtime+'/'+J.TODAY_NAME),A.read_text(persist+'/'+J.FLASH_NAME))
    now=deps.get('now',time.time)()
    offset=time.localtime(now).tm_gmtoff
    result=read_json(runtime+'/'+A.RESULT_NAME)
    rows=changes(persist)
    w=A.window(settings)
    status=A.public_status(settings,curve,result if isinstance(result,dict) else None,
                           A.summary(journal['days'],journal['cur'],J.day_index(now,offset),w),rows)
    return dict(status,curve=A.public_curve(curve),changes=rows)


def reply(method,arguments):
    if method=='advisor':
        if arguments:raise ValueError('RPC-UNEXPECTED-ARGS')
        return read_reply()
    if method=='advisor_apply':
        if not isinstance(arguments,dict) or not set(arguments)<={'t'}:return refuse('ADVISOR-FIELDS')
        if 't' in arguments:return apply(arguments['t'],'owner')
        runtime,_=paths()
        result=read_json(runtime+'/'+A.RESULT_NAME)
        if not isinstance(result,dict) or result.get('state')!='shift' or type(result.get('t')) not in (int,float):
            return refuse('ADVISOR-NO-RECOMMENDATION')
        return apply(result['t'],'owner')
    if method=='advisor_settings':return settings_reply(arguments)
    raise ValueError('RPC-UNKNOWN-METHOD')


def main(argv):
    if len(argv)==2 and argv[1]=='auto-apply':
        runtime,_=paths()
        result=read_json(runtime+'/'+A.RESULT_NAME)
        step=result.get('auto') if isinstance(result,dict) else None
        if not isinstance(step,dict) or step.get('apply') is not True or type(step.get('t')) not in (int,float):
            print(json.dumps(refuse('ADVISOR-NO-SHIFT')));return 0
        print(json.dumps(apply_auto(step['t'],result)));return 0
    raise SystemExit('usage: advisor_control.py auto-apply')


if __name__=='__main__':
    import sys
    sys.exit(main(sys.argv))
