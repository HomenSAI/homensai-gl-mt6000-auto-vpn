"""Small read-only live view. No probes, subprocesses, locks or credentials."""
import math
import re
import time


def snapshot():
    from agent import RUNTIME, read_json
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
    for key in ('state','reason','source','target','mode','proof_scope'):
        value=native.get(key)
        if isinstance(value,str)and len(value)<=128 and re.fullmatch(r'[A-Za-z0-9_:.-]+',value):clean[key]=value
    for key in ('certified','readiness_verified','original_restored','external_lan_verified'):
        if type(native.get(key))is bool:clean[key]=native[key]
    stamp=native.get('time')
    if type(stamp)in(int,float)and math.isfinite(stamp)and 0<=stamp<=now+5:clean['time']=stamp
    stamp=monitor.get('time')
    result={'time':stamp if type(stamp)in(int,float)and math.isfinite(stamp)and 0<=stamp<=now+5 else None,
            'server_time':now,'native_failover':clean}
    # Channel verdicts of the two selected profiles only, so the chart can show "no working channel".
    rows=[]
    for p in (monitor.get('profiles') or [])[:8]:
        if not isinstance(p,dict)or not isinstance(p.get('id'),str)or len(p['id'])>96:continue
        row={'id':p['id']}
        for key in ('time','https_success'):
            if type(p.get(key))in(int,float)and math.isfinite(p[key]):row[key]=p[key]
        code=p.get('code')
        row['code']=code if isinstance(code,str)and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',code)else None
        row['dns_ok']=p['dns_ok']if type(p.get('dns_ok'))is bool else None
        rows.append(row)
    result['profiles']=rows
    blockers=native.get('blockers')
    if isinstance(blockers,list):clean['blockers']=[b for b in blockers[:8] if isinstance(b,str)and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',b)]
    from speed_pause import public as pause_status
    result['speed_pause']=pause_status()
    return result
