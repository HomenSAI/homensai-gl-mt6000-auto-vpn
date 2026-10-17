"""Read-only evidence classification. Link-up is never Internet proof."""
import math

def fresh(stamp,now,age=90):
    return type(stamp) in (int,float) and math.isfinite(stamp) and 0<=now-stamp<=age

def diagnose(status,source,now):
    result={'code':'OBSERVATION-UNKNOWN','suppress_switch':False,'scope':'router probes; LAN confirmation separate'}
    if status.get('error') or not fresh(status.get('time'),now):return dict(result,code='OBSERVATION-STALE')
    uplink=status.get('uplink_observation',{})
    if uplink.get('state')=='DOWN' and fresh(uplink.get('time'),now):
        return dict(result,code='UPLINK-LINK-DOWN',suppress_switch=True,next_action='Restore configured uplink; do not cycle VPN reserves.')
    row=next((p for p in status.get('profiles',[]) if p.get('id')==source),None)
    if not row:return result
    if not row.get('interface'):return dict(result,code='TUNNEL-DISCONNECTED')
    if not fresh(row.get('time'),now):return dict(result,code='OBSERVATION-STALE')
    code=row.get('code')
    if code=='ROUTE-001':return dict(result,code='ROUTE-MISMATCH')
    if code in ('CHECK-001','CHECK-LIMIT'):return dict(result,code='PATH-UNVERIFIED')
    if code=='VPN-001':return dict(result,code='TUNNEL-DISCONNECTED')
    if code=='DNS-001':return dict(result,code='DNS-FAILED')
    if code=='VPN-003':return dict(result,code='HTTPS-FAILED')
    if code is None and row.get('dns_ok') is True and row.get('https_success',0)>=2:return dict(result,code='VPN-PROBE-HEALTHY')
    return result

def explain(status,settings,now):
    from failover_plan import streak
    source=settings.get('plan_source','');target=settings.get('plan_target','')
    from recovery_settings import normalized
    recovery=normalized(settings);age=max(30,min(900,settings.get('interval',30)*3))
    return dict(diagnosis=diagnose(status,source,now),source=source,target=target,
                required_failures=recovery['failures'],required_successes=recovery['successes'],
                source_failure_streak_met=streak(status.get('samples',[]),source,recovery['failures'],now,age,False),
                reserve_success_streak_met=streak(status.get('samples',[]),target,recovery['successes'],now,age,True),
                hierarchy='same-channel-server, same-protocol-channel, other-vpn-protocol',
                selection_policy='operator-priority; no automatic latency rewrite',
                confirmation='LAN DNS/HTTPS/exit proof required; router-only evidence insufficient')
