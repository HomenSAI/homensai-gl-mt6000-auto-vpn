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
    from speed_pause import public as pause_status
    result['speed_pause']=pause_status()
    return result
