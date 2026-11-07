"""Bounded recovery policy settings. No unattended reboot enablement."""
import hashlib
import json

# primary_stable 120 s (was 30) and rescue_stable 10 s: offline GA/annealing study 03.11.2026 (private/math/evolution,
# docs/architecture/RESCUE-STABLE-2026-11-03.ru.md). The longer stability is safe only together with rescue_stable:
# when the reserve that carries the traffic has failed itself, the primary is taken back after rescue_stable seconds
# of stability instead of the full primary_stable (0 = the old rule: the full primary_stable).
# flap_*: the damping of the return (pair_auto.return_hold; study private/math/wave3, docs/architecture/WAVE3-PRODUCT-2026-11-04.ru.md).
# They stand apart from attempt_limit/attempt_window on purpose: those two stay the rate limit of manual switches and of
# the kernel-policy repair (pair_auto.budget); 2 per 60 min there would refuse the repair for up to an hour.
DEFAULTS={'failures':3,'successes':2,'cooldown':60,'min_dwell':60,'return_policy':'healthy_primary','primary_successes':2,'primary_stable':120,'attempt_limit':3,'attempt_window':15,'rescue_stable':10,
          'flap_model':'double','flap_limit':2,'flap_window':60,'flap_halflife':1800,'flap_suppress':1500,'flap_reuse':500}
FLAP_MODELS=('double','halflife')
FLAP_FIELDS=('flap_model','flap_limit','flap_window','flap_halflife','flap_suppress','flap_reuse')
FAILURE_MODELS=('hmm','hmm-fast','consecutive')  # channel_model.MODELS (option failure_model)
RANGES={'failures':(2,10),'successes':(2,10),'cooldown':(60,1800),'min_dwell':(60,3600),'primary_successes':(2,10),'primary_stable':(30,600),'attempt_limit':(1,10),'attempt_window':(1,15),'rescue_stable':(0,60),
        'flap_limit':(1,10),'flap_window':(1,120),'flap_halflife':(600,3600),'flap_suppress':(1000,3000),'flap_reuse':(200,1000)}
# The committed-return reason of a reserve that failed while carrying (native_switch.committed_recovery_decision).
RESCUE_REASON='RESERVE-FAILED-PRIMARY-VERIFIED'


def normalized(settings):
    result={}
    for key,default in DEFAULTS.items():
        value=settings.get('recovery_'+key,default)
        if key=='return_policy':result[key]=value if value in ('healthy_primary','hold_reserve') else default
        elif key=='flap_model':result[key]=value if value in FLAP_MODELS else default
        elif key in ('attempt_limit','attempt_window','flap_limit','flap_window'):
            # Malformed/out-of-range input cannot silently relax the default limit.
            import re
            if type(value)is int:number=value
            elif isinstance(value,str) and re.fullmatch('[0-9]{1,3}',value):number=int(value)
            else:number=default
            lo,hi=RANGES[key];result[key]=number if lo<=number<=hi else default
        else:
            # Review F-46 (06.11.2026): one grammar with lua/pair.lua recovery_normalized: a whole number or a decimal
            # string (blanks and a sign allowed); '3_0', 30.5, True and the like take the default, never int()'s reading.
            # R2-03: at most 9 digits (a longer string is nobody's setting, and int() may refuse it on a Python with a
            # conversion limit); a conversion error takes the default too.
            import re
            if type(value) is int:number=value
            elif isinstance(value,str) and re.fullmatch(r'\s*[+-]?[0-9]{1,9}\s*',value):
                try:number=int(value)
                except ValueError:number=default
            else:number=default
            lo,hi=RANGES[key];result[key]=max(lo,min(hi,number))
    return result


def payload(arguments):
    # Older installed pages send the original seven fields. Missing optional
    # fields are left untouched, never silently reset when an old page saves.
    required=set(DEFAULTS)-{'attempt_limit','attempt_window','rescue_stable'}-set(FLAP_FIELDS)
    optional={'attempt_limit','attempt_window','rescue_stable','interval','failure_model'}|set(FLAP_FIELDS)
    if not isinstance(arguments,dict) or not required<=set(arguments) or set(arguments)-required-optional:
        raise ValueError('RECOVERY-FIELDS')
    for key,(low,high) in RANGES.items():
        if key in arguments and (type(arguments[key]) is not int or not low<=arguments[key]<=high):raise ValueError('RECOVERY-RANGE')
    if 'interval' in arguments and (type(arguments['interval']) is not int or not 10<=arguments['interval']<=300):raise ValueError('RECOVERY-RANGE')
    if arguments['return_policy'] not in ('healthy_primary','hold_reserve'):raise ValueError('RECOVERY-RETURN-POLICY')
    if 'flap_model' in arguments and arguments['flap_model'] not in FLAP_MODELS:raise ValueError('RECOVERY-RANGE')
    # channel_model.MODELS; the option has no recovery_ prefix (option failure_model)
    if 'failure_model' in arguments and arguments['failure_model'] not in FAILURE_MODELS:raise ValueError('RECOVERY-RANGE')
    main={'recovery_'+key:str(value) for key,value in arguments.items() if key not in ('interval','failure_model')}
    if 'interval' in arguments:main['interval']=str(arguments['interval'])
    if 'failure_model' in arguments:main['failure_model']=arguments['failure_model']
    return {'main':main,'servers':[]}


def rescue_settings(settings):
    """Settings for recovery_ready when the reserve carrying the traffic has failed: the primary is proven with
    stable_seconds() = min(primary_stable, rescue_stable) seconds of stability (rescue_stable 0 = primary_stable).
    The marker is a transient boolean, never a UCI option. Lua twin: pair.rescue_settings."""
    return dict(settings,rescue_return=True)


def stable_seconds(settings,policy=None):
    """Seconds of primary stability recovery_ready requires (Lua twin: pair.stable_seconds)."""
    policy=policy or normalized(settings)
    if isinstance(settings,dict) and settings.get('rescue_return') is True and policy['rescue_stable']>0:
        return min(policy['primary_stable'],policy['rescue_stable'])
    return policy['primary_stable']


RETURN_RESERVE=('failed','planned','unknown')


def return_rule(settings,reserve,hold=None):
    """The one return rule of both deciders - pair_auto.tick (kernel on the reserve) and
    native_switch.committed_recovery_decision (COMMITTED journal); Lua twin: pair.return_rule.
    reserve: 'failed'  the reserve carrying the traffic failed itself (failure model / streak) - the rescue:
                       recovery_ready over min(primary_stable, rescue_stable) s (rescue_settings) and NO model gate:
                       the HMM return gate (channel_model.return_ready) never delays leaving a dead reserve;
             'planned' a return from a reserve that did not fail - max(primary_stable, hold) s (hold: the flap-damping
                       pair_auto.return_hold) AND, in the HMM modes ('hmm', 'hmm-fast'), channel_model.return_ready;
             'unknown' neither proven (pair tick only: the reserve's success streak is not met and it has not failed) -
                       primary_stable, no model gate (the rule before the HMM detector).
    -> (settings for recovery_ready, model_gate)."""
    if reserve=='failed':return rescue_settings(settings),False
    if reserve=='planned':
        from channel_model import name
        policy=normalized(settings)
        ready=dict(settings,recovery_primary_stable=hold) if hold is not None and hold>policy['primary_stable'] else settings
        return ready,name(settings)!='consecutive'
    if reserve=='unknown':return settings,False
    raise ValueError('return_rule: unknown reserve state')


def fingerprint(settings):
    return hashlib.sha256(json.dumps(normalized(settings),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def stable_success(samples,identifier,count,seconds,now,max_age=90):
    """Consecutive fresh observations spanning a stable interval, not ICMP alone."""
    import math
    points={point['time']:point for point in samples if point.get('id')==identifier
            and type(point.get('time')) in (int,float) and math.isfinite(point['time'])
            and 0<=now-point['time']<=seconds+max_age*count}
    previous=None;good=[]
    for stamp in sorted(points,reverse=True):
        point=points[stamp]
        if previous is None and now-stamp>max_age:return False
        if previous is not None and previous-stamp>max_age:break
        if point.get('code') is not None or point.get('dns_ok') is not True or point.get('https_success',0)<2:break
        good.append(stamp);previous=stamp
        if len(good)>=count and good[0]-good[-1]>=seconds:return True
    return False
