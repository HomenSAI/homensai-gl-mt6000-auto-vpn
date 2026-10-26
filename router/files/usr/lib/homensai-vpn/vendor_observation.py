"""Read-only configured tunnel identity observations; never a vendor worker API.

Provider profile groups and operator-editable channel labels are metadata, not
routing channels. Only an exact protocol + network logical interface binding
identifies a tunnel. Stable snapshots cannot explain why a provider changed a
profile or prove that its worker exhausted retries.
"""
import math
import re
import uuid

SAFE=re.compile(r'^[A-Za-z0-9_.:-]{1,96}$')
TUNNEL=re.compile(r'^(openvpn|wireguard):[A-Za-z0-9_.-]{1,64}$')
PROFILE_GROUP=re.compile(r'^(openvpn|wireguard):[0-9]{1,20}$')
HEALTH=('https_success','dns_ok','rtt_ms','exit_ip','server_endpoint','probe_checks')
MEASUREMENT_FIELDS=('id','time','code','scope','lan_path_verified','device','mark','table','ifindex',
                    'https_success','dns_ok','rtt_ms','exit_ip','server_endpoint','probe_checks')


def probe_checks(value):
    """Bounded public endpoint facts, never arbitrary measurement metadata."""
    result=[];seen=set()
    for row in value[:3]if isinstance(value,list)else []:
        if not isinstance(row,dict):continue
        target=row.get('target');outcome=row.get('result')
        if (not isinstance(target,str)or target not in('one.one.one.one','dns.google','dns.quad9.net')
                or target in seen or outcome not in('ok','http-unsupported','http-error','timeout',
                    'tls-error','transport-error','invalid-response','unknown')):continue
        seen.add(target);clean={'target':target,'result':outcome}
        status=row.get('http_status');elapsed=row.get('elapsed_ms')
        if type(status)is int and 100<=status<=599:clean['http_status']=status
        if type(elapsed)in(int,float)and 0<=elapsed<=60000 and math.isfinite(elapsed):clean['elapsed_ms']=elapsed
        result.append(clean)
    return result


def tunnel_identity(profile):
    if not isinstance(profile,dict):return None
    protocol=profile.get('protocol');logical=profile.get('interface');claimed=profile.get('vendor_tunnel_id');identifier=profile.get('id')
    if (protocol not in ('openvpn','wireguard') or not isinstance(logical,str)
            or not isinstance(claimed,str) or not TUNNEL.fullmatch(claimed) or claimed!=protocol+':'+logical
            or not isinstance(identifier,str) or not SAFE.fullmatch(identifier) or not identifier.startswith(protocol+':')
            or identifier==protocol+':' or 'section' in profile and identifier!=protocol+':'+str(profile['section'])):return None
    return claimed


def _snapshot(data):
    profiles=data.get('profiles',[]) if isinstance(data,dict) else []
    profiles=profiles if isinstance(profiles,list) else []
    by_id={};bindings={};logicals={}
    for profile in profiles[:400]:
        if not isinstance(profile,dict) or not isinstance(profile.get('id'),str) or not SAFE.fullmatch(profile['id']):continue
        identifier=profile['id'];tunnel=tunnel_identity(profile)
        # Duplicated profile IDs are ambiguous even when the rows look equal.
        if identifier in by_id:
            by_id[identifier]=None
        else:by_id[identifier]=profile
        if tunnel:
            bindings.setdefault(tunnel,[]).append(identifier)
            logicals.setdefault(profile['interface'],[]).append(tunnel)
    valid={}
    for tunnel,identifiers in bindings.items():
        if len(identifiers)!=1:continue
        identifier=identifiers[0];profile=by_id.get(identifier)
        if profile is not None and len(logicals[profile['interface']])==1:valid[tunnel]=profile
    return by_id,valid,set(bindings)


def _anchors(data):
    settings=data.get('settings',{}) if isinstance(data,dict) else {}
    if not isinstance(settings,dict):return {}
    result={}
    for side in ('source','target'):
        tunnel=settings.get('plan_'+side+'_tunnel');identifier=settings.get('plan_'+side)
        if (isinstance(tunnel,str) and TUNNEL.fullmatch(tunnel) and isinstance(identifier,str)
                and SAFE.fullmatch(identifier)):
            result.setdefault(tunnel,[]).append(identifier)
    return result


def current_bindings(profiles):
    """Only unambiguous bindings, for deriving own selected-channel anchors."""
    return _snapshot({'profiles':profiles})[1]


class VendorObserver:
    """Bounded process-local epochs. A restart starts fresh unproven epochs."""
    def __init__(self):
        self.states={};self.events=[]

    def observe(self,before,after,measured,now):
        try:valid_time=type(now) in (int,float) and math.isfinite(now) and now>=0
        except OverflowError:valid_time=False
        if not valid_time:raise ValueError('VENDOR-OBSERVATION-TIME')
        before_ids,pre,pre_claims=_snapshot(before)
        after_ids,post,post_claims=_snapshot(after)
        anchors=_anchors(after)
        measured=[row for row in measured[:400] if isinstance(row,dict)] if isinstance(measured,list) else []
        measured_by_id={row['id']:row for row in measured if isinstance(row.get('id'),str) and SAFE.fullmatch(row['id'])}
        tunnels=set(self.states)|pre_claims|post_claims|set(anchors)
        # Explicitly selected channels precede other live bindings and history.
        anchor_order={tunnel:index for index,tunnel in enumerate(anchors)}
        tunnels=sorted(tunnels,key=lambda key:(0,anchor_order[key],key) if key in anchor_order else
                       (1,key not in post,key))[:400]
        groups=[];next_states={}
        for tunnel in tunnels:
            old=self.states.get(tunnel,{})
            current=post.get(tunnel);earlier=pre.get(tunnel)
            identifier=current['id'] if current else None
            coherent=bool(current and earlier and current['id']==earlier['id'])
            row=measured_by_id.get(identifier,{})
            if row.get('code') in ('VENDOR-IDENTITY-CHANGED','VENDOR-IDENTITY-UNKNOWN'):coherent=False
            # Kernel identity participates in the epoch when observed. A missing
            # measurement never manufactures a new successful kernel binding.
            kernel=tuple(row.get(key) for key in ('device','mark','table','ifindex')) if row else old.get('_kernel')
            fingerprint=(identifier,tunnel,kernel) if coherent else None
            changed=not fingerprint or fingerprint!=old.get('_fingerprint') or now<old.get('time',now)
            previous=(old.get('current_profile') or old.get('previous_profile')) if changed else old.get('previous_profile')
            generation=uuid.uuid4().hex if changed and coherent else old.get('generation') if coherent else None
            changed_at=now if changed else old.get('changed_at',now)
            stable=(1 if changed else min(1000000,old.get('stable_samples',0)+(now>old.get('time',-1)))) if coherent else 0
            state='SETTLED' if stable>=2 else 'PENDING' if coherent else 'UNKNOWN'
            # This is recent observed membership, never the vendor's full queue.
            # Complete quality histories remain independently keyed by profile ID.
            recent=list(old.get('_members',old.get('profiles',[])))
            for member in (earlier['id'] if earlier else None,identifier):
                if member:recent=[member]+[item for item in recent if item!=member]
            members=[]
            for member in [identifier,previous]+anchors.get(tunnel,[])+recent:
                if member and member not in members:members.append(member)
            members=members[:8]
            profile_group=current.get('vendor_profile_group_id') if current else None
            if not isinstance(profile_group,str) or not PROFILE_GROUP.fullmatch(profile_group):profile_group=None
            group={'id':tunnel,'protocol':tunnel.split(':',1)[0],'profile_group_id':profile_group,
                   'profiles':list(members),'active_profiles':[identifier] if identifier else [],
                   'current_profile':identifier,'previous_profile':previous,'state':state,'generation':generation,
                   'changed_at':changed_at,'stable_samples':stable,'time':now,'vendor_attempts_exhausted':None}
            # Emit only observed transitions, not a retry/attempt/cause claim.
            if changed and (old.get('current_profile')!=identifier or not old or
                            old.get('_fingerprint') is not None and fingerprint is not None):
                self.events.append({'time':now,'tunnel':tunnel,'previous_profile':old.get('current_profile'),
                    'current_profile':identifier,'code':'VENDOR-FIRST-OBSERVATION' if not old else
                    'VENDOR-PROFILE-CHANGED' if identifier!=old.get('current_profile') and identifier else
                    'VENDOR-BINDING-CHANGED' if identifier else 'VENDOR-BINDING-UNKNOWN','cause':'UNOBSERVED'})
            next_states[tunnel]=dict(group,_kernel=kernel,_fingerprint=fingerprint,_members=tuple(members))
            groups.append(group)
        self.states=next_states;self.events=self.events[-50:]
        sanitized=[]
        for original in measured:
            # Measurement payloads never override inventory-owned identity or
            # copy arbitrary vendor metadata into the authenticated status.
            row={key:original[key] for key in MEASUREMENT_FIELDS if key in original}
            if 'probe_checks'in row:row['probe_checks']=probe_checks(row['probe_checks'])
            identifier=row.get('id')
            if not isinstance(identifier,str) or not SAFE.fullmatch(identifier):row['id']=identifier=None
            profile=before_ids.get(identifier)
            tunnel=tunnel_identity(profile);group=self.states.get(tunnel,{})
            matching=bool(tunnel and pre.get(tunnel) is profile and post.get(tunnel)
                          and post[tunnel]['id']==identifier and group.get('generation'))
            if not matching:
                for key in HEALTH:row.pop(key,None)
                row['code']='VENDOR-IDENTITY-CHANGED' if tunnel else 'VENDOR-IDENTITY-UNKNOWN'
            row.update(vendor_tunnel_id=tunnel,vendor_generation=group.get('generation') if matching else None,
                       vendor_state=group.get('state','UNKNOWN') if matching else 'UNKNOWN',
                       vendor_changed_at=group.get('changed_at'),interface=profile.get('interface') if profile else None)
            sanitized.append(row)
        return {'version':1,'time':now,'groups':groups,'events':list(self.events),
                'scope':'configured tunnel identity and recent observed members; vendor queue, cause and exhausted attempts unobserved'},sanitized
