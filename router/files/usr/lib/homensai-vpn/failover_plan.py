"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
Read-only planning. This module contains no route/VPN/firewall write commands.
"""
import math

FAILURES = {'VPN-001', 'VPN-003', 'DNS-001'}
BLOCKERS = ['GL-ADAPTER-UNVERIFIED', 'WORKER-COORDINATION-UNVERIFIED',
            'LAN-PATH-UNVERIFIED', 'DNS-POLICY-UNVERIFIED', 'KILLSWITCH-UNVERIFIED',
            'IPV6-POLICY-UNVERIFIED', 'WATCHDOG-UNVERIFIED', 'SCOPED-CONNTRACK-UNVERIFIED']


def streak(samples, identifier, count, now, max_age, good, profile=None):
    from failure_diagnosis import finite,scoped_samples
    if (not isinstance(samples,list) or type(count) is not int or not 1<=count<=10
            or not finite(now) or not finite(max_age) or max_age<=0):return False
    if profile is not None:samples=scoped_samples(samples,profile)
    points = [s for s in samples if isinstance(s,dict) and s.get('id') == identifier
              and finite(s.get('time')) and 0 <= now-s['time'] <= max_age*count]
    points.sort(key=lambda s:s['time'],reverse=True)
    unique=[];seen={}
    for point in points:
        stamp=point['time'];health=tuple(point.get(key) for key in ('code','dns_ok','https_success'))
        if stamp in seen and seen[stamp]!=health:return False
        if stamp not in seen:unique.append(point);seen[stamp]=health
    points=unique[:count]
    if len(points)<count or now-points[0]['time']>max_age:
        return False
    for index,point in enumerate(points):
        if index and points[index-1]['time']-point['time']>max_age:
            return False
        if good:
            if point.get('code') is not None or point.get('dns_ok') is not True or type(point.get('https_success')) is not int or point['https_success']<2:
                return False
        elif not isinstance(point.get('code'),str) or point['code'] not in FAILURES:
            return False
    return True


def plan(status, settings, now):
    if not isinstance(settings,dict):settings={}
    source=settings.get('plan_source','');target=settings.get('plan_target','')
    result={'mode':'dry-run','applied':False,'native_apply':False,'ready_to_apply':False,
            'source':source,'target':target,'recommendation':None,'blockers':list(BLOCKERS),
            'requires_session_interruption':True,'direct_wan_fallback':False}
    from failure_diagnosis import diagnose,resolve_pair
    interval=settings.get('interval',10)
    valid_interval=type(interval) is int and 10<=interval<=300
    age=max(30,min(900,interval*3)) if valid_interval else 90
    settle=max(30,min(600,interval*2)) if valid_interval else 60
    pair=resolve_pair(status,settings,now,age,settle)
    result.update(configured_source=source,configured_target=target,coordination=pair['coordination'])
    source_row=pair['source'];target_row=pair['target']
    if source_row:result['source']=source=source_row['id']
    if target_row:result['target']=target=target_row['id']
    diagnosis=diagnose(status,source,now)
    result['diagnosis']=diagnosis
    if settings.get('plan_enabled') is not True:
        return dict(result,state='DISABLED')
    if not valid_interval:return dict(result,state='PLAN-CONFIG')
    if pair['coordination']['state']!='READY':return dict(result,state=pair['coordination']['code'])
    if diagnosis.get('suppress_switch'):return dict(result,state=diagnosis['code'])
    samples=status.get('samples',[])
    from recovery_settings import normalized
    recovery=normalized(settings)
    if not streak(samples,target,recovery['successes'],now,age,True,target_row):
        return dict(result,state='TARGET-NOT-READY')
    if not streak(samples,source,recovery['failures'],now,age,False,source_row):
        return dict(result,state='OBSERVE')
    result.update(state='SWITCH-RECOMMENDED',recommendation={'target':target,
                  'reason':'CURRENT-PROFILE-FAILURE-STREAK', 'required_failures':recovery['failures'],'required_successes':recovery['successes'],'cross_protocol':source_row.get('protocol')!=target_row.get('protocol'),
                  'transition':pair['coordination']['transition'],'scope':'current profile probes; vendor retry exhaustion unobserved'},
                  steps=['capture-scoped-state','coordinate-workers','arm-independent-rollback-watchdog',
                         'persist-intent','protect-scoped-traffic-keep-management',
                         'apply-with-generation-check','invalidate-only-scoped-conntrack',
                         'verify-client-v4-v6-dns-killswitch-management-special-rules',
                         'commit-or-rollback','release-verified-traffic'])
    return result
