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

# A primary the vendor keeps rebuilding (MT3000 soak 31.10.2026: netifd set wgclient1 up again every ~2 min
# after REKEY-GIVEUP / endpoint "Try again") gets a new vendor generation on every re-setup, so VENDOR-SETTLING
# and PROFILE-IDENTITY-CHANGED never ended and its generation-scoped failure streak restarted each time: Auto
# stayed BLOCKED with a healthy reserve. Short windows keep that safety meaning; a source observed only
# unhealthy for a whole bounded window is unstable and no longer blocks a verified reserve.
SOURCE_UNSTABLE='PAIR-SOURCE-UNSTABLE'
UNSTABLE_CODES=frozenset({'VPN-001','VPN-003','DNS-001','ROUTE-001','CHECK-001','VENDOR-IDENTITY-CHANGED','VENDOR-IDENTITY-UNKNOWN'})
PROBE_FAILURES=frozenset({'VPN-001','VPN-003','DNS-001'})

def flap_window(settle_seconds):
    """Three vendor settle periods, never shorter than 120 s nor longer than 900 s."""
    if not finite(settle_seconds):return None
    return min(900,max(120,3*int(settle_seconds)))

def source_unstable(samples,row,anchor,now,max_age,window):
    """The configured source tunnel was observed only unhealthy, continuously, for the whole window.

    Samples of every vendor generation of the same tunnel count (a rebuild does not reset this evidence):
    at least three observations, at least one real probe failure, no gap longer than max_age, the newest
    fresh, the oldest at least window old, no healthy or unverified (CHECK-LIMIT/None) observation.
    """
    if (not isinstance(samples,list) or not isinstance(row,dict) or not isinstance(anchor,str)
            or not finite(now) or not finite(max_age) or max_age<=0 or not finite(window) or window<=0):return False
    identifier=row.get('id');interface=row.get('interface')
    if not isinstance(identifier,str) or not isinstance(interface,str):return False
    seen={}
    for point in samples:
        if (not isinstance(point,dict) or point.get('id')!=identifier or point.get('interface')!=interface
                or point.get('vendor_tunnel_id')!=anchor or not finite(point.get('time'))
                or not 0<=now-point['time']<=window+max_age):continue
        code=point.get('code');stamp=point['time']
        if stamp in seen and seen[stamp]!=code:return False
        seen[stamp]=code
    stamps=sorted(seen,reverse=True)
    if len(stamps)<3 or now-stamps[0]>max_age or now-stamps[-1]<window:return False
    for index,stamp in enumerate(stamps):
        if index and stamps[index-1]-stamp>max_age:return False
        if not isinstance(seen[stamp],str) or seen[stamp] not in UNSTABLE_CODES:return False
    return any(seen[stamp] in PROBE_FAILURES for stamp in stamps)

def unstable_source(status,group,by_id,anchor,now,max_age,window):
    """The source row when its tunnel group is unstable (see source_unstable), else None."""
    identifier=group.get('current_profile')
    if (not isinstance(identifier,str) or group.get('active_profiles')!=[identifier]
            or group.get('protocol')!=anchor.split(':',1)[0]):return None
    row=by_id.get(identifier)
    if tunnel_identity(row)!=anchor or not fresh(row.get('time'),now,max_age):return None
    return row if source_unstable(status.get('samples'),row,anchor,now,max_age,window) else None

def resolve_pair(status,settings,now,max_age=90,settle_seconds=60,source_window=None):
    """Resolve durable tunnel anchors, never provider grouping or editable labels.

    Stable configuration is not proof of vendor retry exhaustion or permission
    for an application route action. Legacy inference requires an exact binding.
    source_window (the Auto diagnostic only): a source still settling or rebound, but observed only
    unhealthy for that whole window, no longer blocks a verified reserve (PAIR-SOURCE-UNSTABLE).
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
    by_tunnel={group['id']:group for group in groups};settle_until=0;unstable=None
    if source_window is not None and (not finite(source_window) or source_window<=0):source_window=None
    for role,anchor in zip(('source','target'),anchors):
        group=by_tunnel.get(anchor)
        if not group or not fresh(group.get('time'),now,max_age):return result
        # Only the source, only for the Auto diagnostic, only after the whole bounded window.
        tolerant=role=='source' and source_window is not None
        if group.get('state')=='PENDING':
            unstable=unstable_source(status,group,by_id,anchor,now,max_age,source_window) if tolerant else None
            if unstable is None:return refuse('VENDOR-SETTLING','HOLD')
            continue
        if group.get('state')!='SETTLED':return result
        identifier=group.get('current_profile');active=group.get('active_profiles')
        if not isinstance(identifier,str) or active!=[identifier] or group.get('protocol')!=anchor.split(':',1)[0]:return result
        row=by_id.get(identifier);identity=profile_identity(row)
        if not identity or identity['vendor_tunnel_id']!=anchor or identity['vendor_generation']!=group.get('generation'):
            unstable=unstable_source(status,group,by_id,anchor,now,max_age,source_window) if tolerant else None
            if unstable is None:return refuse('PROFILE-IDENTITY-CHANGED')
            continue
        if row.get('vendor_state')=='PENDING':
            unstable=unstable_source(status,group,by_id,anchor,now,max_age,source_window) if tolerant else None
            if unstable is None:return refuse('VENDOR-SETTLING','HOLD')
            continue
        if row.get('vendor_state')!='SETTLED':return result
        if not fresh(row.get('time'),now,max_age):return refuse('OBSERVATION-STALE')
        changed=group.get('changed_at')
        if (not finite(changed) or not 0<=changed<=now or row.get('vendor_changed_at')!=changed
                or type(group.get('stable_samples')) is not int or group['stable_samples']<2):return result
        if tolerant and now<changed+settle_seconds:
            unstable=unstable_source(status,group,by_id,anchor,now,max_age,source_window)
            if unstable is not None:continue
        settle_until=max(settle_until,changed+settle_seconds);result[role]=row
    coordination['settle_until']=settle_until
    if now<settle_until:return refuse('VENDOR-SETTLING','HOLD')
    uplink=status.get('uplink_observation')
    if isinstance(uplink,dict) and uplink.get('state')=='DOWN' and fresh(uplink.get('time'),now,max_age):
        return refuse('UPLINK-LINK-DOWN','HOLD')
    if unstable is not None:
        result['source']=unstable
        coordination.update(state='READY',code=SOURCE_UNSTABLE);return result
    coordination.update(state='READY',code='CROSS-TUNNEL-READY');return result

def diagnose(status,source,now,settings=None):
    from observation_freshness import valid_for,cached
    age=valid_for(settings) if settings is not None else cached(status)
    result={'code':'OBSERVATION-UNKNOWN','suppress_switch':True,'scope':'current profile router probes; channel retry exhaustion and LAN confirmation unverified'}
    if not isinstance(status,dict) or status.get('error') or not fresh(status.get('time'),now,age):return dict(result,code='OBSERVATION-STALE')
    uplink=status.get('uplink_observation',{})
    if isinstance(uplink,dict) and uplink.get('state')=='DOWN' and fresh(uplink.get('time'),now,age):
        return dict(result,code='UPLINK-LINK-DOWN',suppress_switch=True,next_action='Restore configured uplink; do not cycle VPN reserves.')
    profiles=status.get('profiles',[])
    if not isinstance(profiles,list):return result
    rows=[p for p in profiles if isinstance(p,dict) and p.get('id')==source]
    if len(rows)!=1:return result
    row=rows[0]
    if not row.get('interface'):return dict(result,code='TUNNEL-DISCONNECTED')
    if not fresh(row.get('time'),now,age):return dict(result,code='OBSERVATION-STALE')
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
    from observation_freshness import valid_for,settle_for
    age=valid_for(settings)
    pair=resolve_pair(status,settings,now,age,settle_for(settings))
    source=pair['source'];target=pair['target'];ready=valid_interval and pair['coordination']['state']=='READY'
    return dict(diagnosis=diagnose(status,source['id'] if source else settings.get('plan_source',''),now,settings),
                source=source['id'] if source else settings.get('plan_source',''),
                target=target['id'] if target else settings.get('plan_target',''),coordination=pair['coordination'],
                required_failures=recovery['failures'],required_successes=recovery['successes'],
                source_failure_streak_met=ready and streak(status.get('samples',[]),source['id'],recovery['failures'],now,age,False,source),
                reserve_success_streak_met=ready and streak(status.get('samples',[]),target['id'],recovery['successes'],now,age,True,target),
                hierarchy='vendor-owned servers; same-protocol tunnel, other-vpn-protocol',
                selection_policy='operator-priority; no automatic latency rewrite',
                confirmation='LAN DNS/HTTPS/exit proof required; router-only evidence insufficient')
