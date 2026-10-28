"""Small read-only live view. No probes, subprocesses, locks or credentials."""
import math
import re
import time


def snapshot():
    from agent import RUNTIME,PERSIST,read_json,checksum
    now=time.time()
    try:
        for name,limit in (('native-status.json',65536),('status.json',2097152)):
            path=RUNTIME/name
            if path.is_symlink()or path.stat().st_size>limit:raise ValueError()
        native=read_json(RUNTIME/'native-status.json',{})
        monitor=read_json(RUNTIME/'status.json',{})
        if not isinstance(native,dict)or not isinstance(monitor,dict):raise ValueError()
    except (OSError,ValueError):
        return {'time':now,'native_failover':{},'rpc_error':'RPC-UNAVAILABLE'}
    clean={}
    for key in ('state','reason','source','target','mode','proof_scope','destination_role','destination_profile_id','from_role','from_profile_id'):
        value=native.get(key)
        if isinstance(value,str)and len(value)<=128 and re.fullmatch(r'[A-Za-z0-9_:.-]+',value):clean[key]=value
    for key in ('certified','readiness_verified','original_restored','external_lan_verified','kernel_policy_verified','transition_metadata_present','route_changed','transition_completed','activation_reapply'):
        if type(native.get(key))is bool:clean[key]=native[key]
    stamp=native.get('time')
    if type(stamp)in(int,float)and math.isfinite(stamp)and 0<=stamp<=now+5:clean['time']=stamp
    stamp=monitor.get('time')
    result={'time':stamp if type(stamp)in(int,float)and math.isfinite(stamp)and 0<=stamp<=now+5 else None,
            'server_time':now,'native_failover':clean}
    from observation_freshness import cached as observation_window
    result['observation_valid_for']=observation_window(monitor)
    def bounded(path,limit=65536):
        if path.is_symlink():raise ValueError()
        if not path.exists():return {}
        if path.stat().st_size>limit:raise ValueError()
        value=read_json(path,{})
        if not isinstance(value,dict):raise ValueError()
        return value
    required=clean.get('mode')=='continuous-pair' or clean.get('proof_scope')=='router-probed-ipv4'
    try:
        envelope=bounded(PERSIST/'pair-auto-state.json')
        owned=envelope.get('data',{})
        valid=bool(isinstance(owned,dict) and envelope.get('sha256')==checksum(owned))
        required=required or bool(envelope and clean.get('proof_scope')!='external-lan')
        request=bounded(RUNTIME/'pair-auto-control.json');revision=bounded(RUNTIME/'auto-control-revision.json')
        stopped=bounded(PERSIST/'native-stop.json')
        mode=request.get('mode','off')
        if mode not in ('on','off') or mode=='on' and (request.get('revision')!=revision.get('revision') or not valid or stopped.get('control_revision_failed') is True):mode='unknown'
        phase=owned.get('phase') if valid else None
        if phase not in ('STARTING','RUNNING','STOPPING','HELD','STOPPED','FAILED'):phase=None
        if mode=='on' and (request.get('id')!=owned.get('id') or request.get('revision')!=owned.get('revision')):phase='STARTING'
        if mode!='on' and phase in ('STARTING','RUNNING','STOPPING'):phase='STOPPING'
        result['auto_control']={'requested':mode,'pair_phase':phase}
    except (OSError,ValueError,TypeError):
        required=required or clean.get('proof_scope')!='external-lan'
        result['auto_control']={'requested':'unknown','pair_phase':None}
    if required:
        from channel_path import cached_projection,from_kernel
        path=cached_projection(native.get('channel_path'),now)
        if clean.get('state') in ('BLOCKED','ARMED','APPLYING','WAIT-CLIENT','RESTORING') or native.get('blockers'):
            path=from_kernel(None,clean.get('source'),clean.get('target'),now)
        result['channel_path']=path
        clean['mode']='continuous-pair'
    # Channel verdicts of the two selected profiles only, so the chart can show "no working channel".
    rows=[]
    profiles=monitor.get('profiles')
    for p in (profiles if isinstance(profiles,list) else [])[:8]:
        if not isinstance(p,dict)or not isinstance(p.get('id'),str)or len(p['id'])>96:continue
        row={'id':p['id'],'observation_valid_for':result['observation_valid_for']}
        for key in ('time','https_success'):
            if type(p.get(key))in(int,float)and math.isfinite(p[key]):row[key]=p[key]
        code=p.get('code')
        row['code']=code if isinstance(code,str)and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',code)else None
        row['dns_ok']=p['dns_ok']if type(p.get('dns_ok'))is bool else None
        rows.append(row)
    result['profiles']=rows
    from pair_manual import public_for_status
    _,result['manual_switch']=public_for_status(native)
    blockers=native.get('blockers')
    if isinstance(blockers,list):clean['blockers']=[b for b in blockers[:8] if isinstance(b,str)and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',b)]
    from speed_pause import public as pause_status
    result['speed_pause']=pause_status()
    return result
