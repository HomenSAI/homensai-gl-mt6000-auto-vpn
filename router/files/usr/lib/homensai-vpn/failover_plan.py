"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
Read-only planning. This module contains no route/VPN/firewall write commands.
"""
import math

FAILURES = {'VPN-001', 'VPN-003', 'DNS-001'}
BLOCKERS = ['GL-ADAPTER-UNVERIFIED', 'WORKER-COORDINATION-UNVERIFIED',
            'LAN-PATH-UNVERIFIED', 'DNS-POLICY-UNVERIFIED', 'KILLSWITCH-UNVERIFIED',
            'IPV6-POLICY-UNVERIFIED', 'WATCHDOG-UNVERIFIED', 'SCOPED-CONNTRACK-UNVERIFIED']


def streak(samples, identifier, count, now, max_age, good):
    points = [s for s in samples if s.get('id') == identifier and isinstance(s.get('time'),(int,float))
              and math.isfinite(s['time']) and 0 <= now-s['time'] <= max_age*count]
    points.sort(key=lambda s:s['time'],reverse=True)
    unique=[];seen=set()
    for point in points:
        if point['time'] not in seen:
            unique.append(point);seen.add(point['time'])
    points=unique[:count]
    if len(points)<count or now-points[0]['time']>max_age:
        return False
    for index,point in enumerate(points):
        if index and points[index-1]['time']-point['time']>max_age:
            return False
        if good:
            if point.get('code') is not None or point.get('dns_ok') is not True or point.get('https_success',0)<2:
                return False
        elif point.get('code') not in FAILURES:
            return False
    return True


def plan(status, settings, now):
    source=settings.get('plan_source','');target=settings.get('plan_target','')
    result={'mode':'dry-run','applied':False,'native_apply':False,'ready_to_apply':False,
            'source':source,'target':target,'recommendation':None,'blockers':list(BLOCKERS),
            'requires_session_interruption':True,'direct_wan_fallback':False}
    from failure_diagnosis import diagnose
    diagnosis=diagnose(status,source,now)
    result['diagnosis']=diagnosis
    if not settings.get('plan_enabled'):
        return dict(result,state='DISABLED')
    if diagnosis.get('suppress_switch'):return dict(result,state='UPLINK-DOWN')
    profiles={p['id']:p for p in status.get('profiles',[])}
    if not source or not target or source==target or source not in profiles or target not in profiles:
        return dict(result,state='PLAN-CONFIG')
    age=max(10,min(900,settings.get('interval',30)*3))
    source_row,target_row=profiles[source],profiles[target]
    if not target_row.get('interface'):
        return dict(result,state='TARGET-INACTIVE')
    samples=status.get('samples',[])
    from recovery_settings import normalized
    recovery=normalized(settings)
    if not streak(samples,target,recovery['successes'],now,age,True):
        return dict(result,state='TARGET-NOT-READY')
    if not streak(samples,source,recovery['failures'],now,age,False):
        return dict(result,state='OBSERVE')
    result.update(state='SWITCH-RECOMMENDED',recommendation={'target':target,
                  'reason':'THREE-CONFIRMED-FAILURES' if recovery['failures']==3 else 'CONFIGURED-FAILURE-STREAK', 'required_failures':recovery['failures'],'required_successes':recovery['successes'],'cross_protocol':source_row.get('protocol')!=target_row.get('protocol')},
                  steps=['capture-scoped-state','coordinate-workers','arm-independent-rollback-watchdog',
                         'persist-intent','protect-scoped-traffic-keep-management',
                         'apply-with-generation-check','invalidate-only-scoped-conntrack',
                         'verify-client-v4-v6-dns-killswitch-management-special-rules',
                         'commit-or-rollback','release-verified-traffic'])
    return result
