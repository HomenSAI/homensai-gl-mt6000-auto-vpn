"""Read-only evidence classification. Link-up is never Internet proof."""
import math
import re

TUNNEL=re.compile(r'^(openvpn|wireguard):([A-Za-z0-9_.-]{1,64})$')
GENERATION=re.compile(r'^[a-f0-9]{32}$')

def finite(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False

def fresh(stamp,now,age=90):
    return finite(now) and now>=0 and finite(stamp) and stamp>=0 and 0<=now-stamp<=age

def tunnel_identity(profile):
    from vendor_observation import tunnel_identity as configured_tunnel
    return configured_tunnel(profile)

def profile_identity(profile):
    tunnel=tunnel_identity(profile)
    generation=profile.get('vendor_generation') if isinstance(profile,dict) else None
    if not tunnel or not isinstance(generation,str) or not GENERATION.fullmatch(generation):return None
    return {key:profile.get(key) for key in ('id','protocol','interface','vendor_tunnel_id','vendor_generation')}

def scoped_samples(samples,profile):
    """A rebound generation cannot borrow the former binding's health history."""
    identity=profile_identity(profile)
    if not identity or not isinstance(samples,list):return []
    changed=profile.get('vendor_changed_at')
    if not finite(changed):return []
    points=[point for point in samples if isinstance(point,dict) and point.get('id')==identity['id']
            and finite(point.get('time')) and point['time']>=changed
            and all(point.get(key)==identity[key] for key in ('interface','vendor_tunnel_id','vendor_generation'))]
    seen={}
    for point in points:
        health=tuple(point.get(key) for key in ('code','dns_ok','https_success'));stamp=point['time']
        if stamp in seen and seen[stamp]!=health:return []
        seen[stamp]=health
    return points

def resolve_pair(status,settings,now,max_age=90,settle_seconds=60):
    """Resolve durable tunnel anchors, never provider grouping or editable labels.

    Stable configuration is not proof of vendor retry exhaustion or permission
    for an application route action. Legacy inference requires an exact binding.
    """
    coordination={'version':1,'time':now if finite(now) else None,'state':'UNKNOWN',
        'code':'VENDOR-IDENTITY-UNKNOWN','source_tunnel':None,'target_tunnel':None,
        'transition':None,'vendor_reason':'UNOBSERVED','can_apply':False,
        'vendor_attempts_exhausted':None,'vendor_settle_seconds':settle_seconds,
        'settle_until':None,'scope':'application planning gate; current configured tunnel identity only'}
    result={'source':None,'target':None,'coordination':coordination}
    def refuse(code,state='UNKNOWN'):
        coordination.update(code=code,state=state);return result
    if not finite(max_age) or not 0<max_age<=900 or not finite(settle_seconds) or not 30<=settle_seconds<=600:return result
    if not isinstance(status,dict) or not isinstance(settings,dict):return refuse('OBSERVATION-STALE')
    if status.get('error') or not fresh(status.get('time'),now,max_age):return refuse('OBSERVATION-STALE')
    rows=status.get('profiles')
    if not isinstance(rows,list) or len(rows)>400 or any(not isinstance(row,dict) for row in rows):return result
    identifiers=[row.get('id') for row in rows]
    if any(not isinstance(value,str) or not value for value in identifiers) or len(set(identifiers))!=len(identifiers):return result
    by_id={row['id']:row for row in rows};anchors=[]
    for role in ('source','target'):
        anchor=settings.get('plan_'+role+'_tunnel')
        if anchor in (None,''):
            selected=settings.get('plan_'+role)
            anchor=tunnel_identity(by_id.get(selected)) if isinstance(selected,str) else None
        if not isinstance(anchor,str) or not TUNNEL.fullmatch(anchor):return result
        coordination[role+'_tunnel']=anchor;anchors.append(anchor)
    if anchors[0]==anchors[1]:return refuse('VENDOR-SAME-TUNNEL','HOLD')
    coordination['transition']='channel' if anchors[0].split(':',1)[0]==anchors[1].split(':',1)[0] else 'protocol'
    observation=status.get('vendor_observation')
    if (not isinstance(observation,dict) or type(observation.get('version')) is not int
            or observation['version']!=1 or not fresh(observation.get('time'),now,max_age)
            or not isinstance(observation.get('groups'),list)):return result
    groups=observation['groups']
    if len(groups)>400:return result
    if any(not isinstance(group,dict) for group in groups):return result
    group_ids=[group.get('id') for group in groups]
    if any(not isinstance(value,str) for value in group_ids) or len(set(group_ids))!=len(group_ids):return result
    by_tunnel={group['id']:group for group in groups};settle_until=0
    for role,anchor in zip(('source','target'),anchors):
        group=by_tunnel.get(anchor)
        if not group or not fresh(group.get('time'),now,max_age):return result
        if group.get('state')=='PENDING':return refuse('VENDOR-SETTLING','HOLD')
        if group.get('state')!='SETTLED':return result
        identifier=group.get('current_profile');active=group.get('active_profiles')
        if not isinstance(identifier,str) or active!=[identifier] or group.get('protocol')!=anchor.split(':',1)[0]:return result
        row=by_id.get(identifier);identity=profile_identity(row)
        if not identity or identity['vendor_tunnel_id']!=anchor:return refuse('PROFILE-IDENTITY-CHANGED')
        if identity['vendor_generation']!=group.get('generation'):return refuse('PROFILE-IDENTITY-CHANGED')
        if row.get('vendor_state')=='PENDING':return refuse('VENDOR-SETTLING','HOLD')
        if row.get('vendor_state')!='SETTLED':return result
        if not fresh(row.get('time'),now,max_age):return refuse('OBSERVATION-STALE')
        changed=group.get('changed_at')
        if (not finite(changed) or not 0<=changed<=now or row.get('vendor_changed_at')!=changed
                or type(group.get('stable_samples')) is not int or group['stable_samples']<2):return result
        settle_until=max(settle_until,changed+settle_seconds);result[role]=row
    coordination['settle_until']=settle_until
    if now<settle_until:return refuse('VENDOR-SETTLING','HOLD')
    uplink=status.get('uplink_observation')
    if isinstance(uplink,dict) and uplink.get('state')=='DOWN' and fresh(uplink.get('time'),now,max_age):
        return refuse('UPLINK-LINK-DOWN','HOLD')
    coordination.update(state='READY',code='CROSS-TUNNEL-READY');return result

def diagnose(status,source,now):
    result={'code':'OBSERVATION-UNKNOWN','suppress_switch':True,'scope':'current profile router probes; channel retry exhaustion and LAN confirmation unverified'}
    if not isinstance(status,dict) or status.get('error') or not fresh(status.get('time'),now):return dict(result,code='OBSERVATION-STALE')
    uplink=status.get('uplink_observation',{})
    if isinstance(uplink,dict) and uplink.get('state')=='DOWN' and fresh(uplink.get('time'),now):
        return dict(result,code='UPLINK-LINK-DOWN',suppress_switch=True,next_action='Restore configured uplink; do not cycle VPN reserves.')
    profiles=status.get('profiles',[])
    if not isinstance(profiles,list):return result
    rows=[p for p in profiles if isinstance(p,dict) and p.get('id')==source]
    if len(rows)!=1:return result
    row=rows[0]
    if not row.get('interface'):return dict(result,code='TUNNEL-DISCONNECTED')
    if not fresh(row.get('time'),now):return dict(result,code='OBSERVATION-STALE')
    code=row.get('code')
    if code=='VENDOR-IDENTITY-CHANGED':return dict(result,code='PROFILE-IDENTITY-CHANGED')
    if row.get('vendor_state')=='PENDING':return dict(result,code='VENDOR-SETTLING')
    if row.get('vendor_state')=='UNKNOWN':return dict(result,code='VENDOR-IDENTITY-UNKNOWN')
    if code=='ROUTE-001':return dict(result,code='ROUTE-MISMATCH')
    if code in ('CHECK-001','CHECK-LIMIT'):return dict(result,code='PATH-UNVERIFIED')
    if code=='VPN-001':return dict(result,code='TUNNEL-DISCONNECTED',suppress_switch=False)
    if code=='DNS-001':return dict(result,code='DNS-FAILED',suppress_switch=False)
    if code=='VPN-003':return dict(result,code='HTTPS-FAILED',suppress_switch=False)
    successes=row.get('https_success')
    if code is None and row.get('dns_ok') is True and type(successes) is int and successes>=2:return dict(result,code='VPN-PROBE-HEALTHY',suppress_switch=False)
    return result

def explain(status,settings,now):
    from failover_plan import streak
    if not isinstance(settings,dict):settings={}
    from recovery_settings import normalized
    recovery=normalized(settings);interval=settings.get('interval',10)
    valid_interval=type(interval) is int and 10<=interval<=300
    age=max(30,min(900,interval*3)) if valid_interval else 90
    pair=resolve_pair(status,settings,now,age,max(30,min(600,interval*2)) if valid_interval else 60)
    source=pair['source'];target=pair['target'];ready=valid_interval and pair['coordination']['state']=='READY'
    return dict(diagnosis=diagnose(status,source['id'] if source else settings.get('plan_source',''),now),
                source=source['id'] if source else settings.get('plan_source',''),
                target=target['id'] if target else settings.get('plan_target',''),coordination=pair['coordination'],
                required_failures=recovery['failures'],required_successes=recovery['successes'],
                source_failure_streak_met=ready and streak(status.get('samples',[]),source['id'],recovery['failures'],now,age,False,source),
                reserve_success_streak_met=ready and streak(status.get('samples',[]),target['id'],recovery['successes'],now,age,True,target),
                hierarchy='vendor-owned servers; same-protocol tunnel, other-vpn-protocol',
                selection_policy='operator-priority; no automatic latency rewrite',
                confirmation='LAN DNS/HTTPS/exit proof required; router-only evidence insufficient')
