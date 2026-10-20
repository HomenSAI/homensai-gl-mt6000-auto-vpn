"""Explicit synthetic configured tunnel provenance for policy tests."""
import hashlib


def stamp(profile,now=1000):
    protocol=profile.get('protocol') or profile['id'].split(':',1)[0]
    tunnel=protocol+':'+profile['interface']
    profile.update(protocol=protocol,vendor_tunnel_id=tunnel,
        vendor_generation=hashlib.sha256(tunnel.encode()).hexdigest()[:32],
        vendor_state='SETTLED',vendor_changed_at=max(0,now-120),time=now)
    profile.setdefault('code',None);profile.setdefault('dns_ok',True);profile.setdefault('https_success',2)
    return profile


def attach(status,now=1000):
    status['time']=now;groups=[]
    for profile in status['profiles']:
        stamp(profile,now)
        groups.append({'id':profile['vendor_tunnel_id'],'protocol':profile['protocol'],
            'current_profile':profile['id'],'profiles':[profile['id']],
            'active_profiles':[profile['id']],'generation':profile['vendor_generation'],
            'state':'SETTLED','stable_samples':2,'changed_at':profile['vendor_changed_at'],'time':now})
    status['vendor_observation']={'version':1,'time':now,'groups':groups}
    by_id={profile['id']:profile for profile in status['profiles']}
    for sample in status.get('samples',[]):
        profile=by_id[sample['id']]
        sample.update({key:profile[key] for key in ('interface','vendor_tunnel_id','vendor_generation')})
    return status
