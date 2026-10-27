"""Bounded recovery policy settings. No unattended reboot enablement."""
import hashlib
import json

DEFAULTS={'failures':3,'successes':2,'cooldown':60,'min_dwell':60,'return_policy':'healthy_primary','primary_successes':2,'primary_stable':30,'attempt_limit':3,'attempt_window':15}
RANGES={'failures':(3,10),'successes':(2,10),'cooldown':(60,1800),'min_dwell':(60,3600),'primary_successes':(2,10),'primary_stable':(30,600),'attempt_limit':(1,10),'attempt_window':(1,15)}


def normalized(settings):
    result={}
    for key,default in DEFAULTS.items():
        value=settings.get('recovery_'+key,default)
        if key=='return_policy':result[key]=value if value in ('healthy_primary','hold_reserve') else default
        elif key in ('attempt_limit','attempt_window'):
            # Malformed/out-of-range input cannot silently relax the default limit.
            import re
            if type(value)is int:number=value
            elif isinstance(value,str) and re.fullmatch('[0-9]{1,3}',value):number=int(value)
            else:number=default
            lo,hi=RANGES[key];result[key]=number if lo<=number<=hi else default
        else:
            try:number=int(value)
            except (ValueError,TypeError):number=default
            lo,hi=RANGES[key];result[key]=max(lo,min(hi,number))
    return result


def payload(arguments):
    # Older installed pages send the original seven fields. Missing optional
    # fields are left untouched, never silently reset when an old page saves.
    required=set(DEFAULTS)-{'attempt_limit','attempt_window'}
    optional={'attempt_limit','attempt_window','interval'}
    if not isinstance(arguments,dict) or not required<=set(arguments) or set(arguments)-required-optional:
        raise ValueError('RECOVERY-FIELDS')
    for key,(low,high) in RANGES.items():
        if key in arguments and (type(arguments[key]) is not int or not low<=arguments[key]<=high):raise ValueError('RECOVERY-RANGE')
    if 'interval' in arguments and (type(arguments['interval']) is not int or not 10<=arguments['interval']<=300):raise ValueError('RECOVERY-RANGE')
    if arguments['return_policy'] not in ('healthy_primary','hold_reserve'):raise ValueError('RECOVERY-RETURN-POLICY')
    main={'recovery_'+key:str(value) for key,value in arguments.items() if key!='interval'}
    if 'interval' in arguments:main['interval']=str(arguments['interval'])
    return {'main':main,'servers':[]}


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
