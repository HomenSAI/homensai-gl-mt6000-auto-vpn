# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Why the service is starting: one code per start (owner request 01.11.2026).

Python counterpart of lua/interruption.lua - the same files, the same decision, the same log lines (shared cases:
router/tests/interruption_cases.json). The supervisor (native_switch.serve) calls start() once before its recovery
changes anything and mark_running() when its recovery is finished; the monitor (agent.monitor_loop) calls
monitor_start() once.

  <persist>/service-run.json     {"state":"starting|running|stopped","time":..}: 'stopped' from the init script's
                                 stop_service (one small write per stop), 'starting' at a start, 'running' when the
                                 recovery finished; written only when the state changes (a crash loop writes nothing)
  <runtime>/supervisor-run.json  RAM: absent = the first supervisor start of this boot
  <runtime>/monitor-run.json     RAM: the same for the monitor process
  <runtime>/service-stop.flag    mtime: touched by every stop_service
"""
import json
import math
import time

MARKER='service-run.json'
SUPERVISOR='supervisor-run.json'
MONITOR='monitor-run.json'
STOP_FLAG='service-stop.flag'
LIMIT=3
WINDOW=600
SWITCH=('ARMED','APPLYING','WAIT-CLIENT','RESTORING')
HOLD=('HELD-ON-RESERVE','COMMITTED')
TEXT={
    'RESTART-CLEAN':'clean reboot or service stop and start, not an interruption',
    'RESTART-FIRST-START':'no record of the previous run (first start after install or upgrade), not an interruption',
    'RESTART-PROCESS':'the process ended without a service stop and procd restarted it (crash or kill)',
    'RESTART-INTERRUPTED-BOOT':'power lost or the router hung while booting: the previous start never finished its recovery',
    'RESTART-INTERRUPTED-SWITCH':'power lost during a channel switch; the recovery rolls the switch back',
    'RESTART-INTERRUPTED-RESERVE-HOLD':'power lost while the reserve channel was held',
    'RESTART-INTERRUPTED-OPERATION':'power lost during normal operation with Auto on',
    'RESTART-INTERRUPTED-AUTO-OFF':'power lost while Auto was off',
}


def _decode(text):
    if not isinstance(text,str):return None
    try:row=json.loads(text)
    except ValueError:return None
    return row if isinstance(row,dict) else None


def _number(value):
    if type(value) in (int,float) and math.isfinite(value):return value
    return None


def _int(value):
    value=_number(value)
    return None if value is None else int(math.floor(value))


def previous(text):
    if text is None:return None
    row=_decode(text)
    state=row.get('state') if row else None
    return state if state in ('stopped','starting','running') else 'invalid'


def auto_on(read,runtime,persist):
    """The Auto intent of the run that ended (boot_resume.wanted's marker/stop-latch decision after a boot)."""
    intent=_decode(read(runtime+'/pair-auto-control.json'))
    if intent and intent.get('mode')=='on':return True
    marker=_decode(read(persist+'/auto-resume.json'))
    at=_number(marker.get('time')) if marker and marker.get('enabled') is True else None
    if at is None:return False
    text=read(persist+'/native-stop.json')
    if text is not None:
        latch=_decode(text)
        stopped=_number(latch.get('requested')) if latch else None
        if stopped is None or stopped>=at:return False
    return True


def classify(f):
    if not f['fresh']:
        return 'RESTART-CLEAN' if f['previous']=='stopped' or f['stopped_since'] else 'RESTART-PROCESS'
    if f['previous']=='stopped':return 'RESTART-CLEAN'
    if f['previous'] is None:return 'RESTART-FIRST-START'
    if f['phase'] in SWITCH:return 'RESTART-INTERRUPTED-SWITCH'
    if f['previous']=='starting':return 'RESTART-INTERRUPTED-BOOT'
    if f['phase'] in HOLD:return 'RESTART-INTERRUPTED-RESERVE-HOLD'
    if f['auto_on']:return 'RESTART-INTERRUPTED-OPERATION'
    return 'RESTART-INTERRUPTED-AUTO-OFF'


def _uptime_text(up):
    return 'unknown' if up is None else '%.0f'%up


def _ram_marker(ctx,path,restart_code_of):
    text=ctx['read'](path)
    row=_decode(text) or {}
    stop=_int(ctx['mtime'](ctx['runtime']+'/'+STOP_FLAG))
    fresh=text is None
    stopped_since=not fresh and stop!=_int(row.get('stop'))
    code=restart_code_of(fresh,stopped_since)
    up=ctx['uptime']()
    kept=[]
    for t in row.get('restarts') if isinstance(row.get('restarts'),list) else []:
        n=_number(t)
        if n is not None and up is not None and up-n<WINDOW and n<=up:kept.append(float(n))
    recorded=True
    if code=='RESTART-PROCESS':
        if len(kept)>=LIMIT:recorded=False
        elif up is not None:kept.append(float(up))
    try:ctx['write_ram'](path,json.dumps({'restarts':kept,'stop':stop,'time':float(ctx['now']())},separators=(',',':'),sort_keys=True))
    except Exception:pass
    return code,fresh,stopped_since,recorded,up


def _emit(ctx,code,line,recorded):
    if not recorded:line+='; not saved to the history (restart limit)'
    try:ctx['log'](line)
    except Exception:pass
    if recorded and ctx.get('record'):
        try:ctx['record'](code)
        except Exception:pass


def start(ctx,phase):
    persist_path=ctx['persist']+'/'+MARKER
    prior=previous(ctx['read'](persist_path))
    facts={'previous':prior,'phase':phase if isinstance(phase,str) else None}
    try:facts['auto_on']=auto_on(ctx['read'],ctx['runtime'],ctx['persist']) is True
    except Exception:facts['auto_on']=False
    def code_of(fresh,since):
        facts['fresh']=fresh;facts['stopped_since']=since
        return classify(facts)
    code,fresh,_,recorded,up=_ram_marker(ctx,ctx['runtime']+'/'+SUPERVISOR,code_of)
    facts['uptime']=up
    persisted=prior
    if not (prior=='starting' or (not fresh and prior=='running')):
        try:
            ctx['write_persist'](persist_path,json.dumps({'state':'starting','time':float(ctx['now']())},separators=(',',':'),sort_keys=True))
            persisted='starting'
        except Exception:pass
    _emit(ctx,code,'%s: %s (journal %s, Auto %s, uptime %s s)'%(code,TEXT[code],facts['phase'] or 'none','on' if facts['auto_on'] else 'off',
                                                             _uptime_text(up)),recorded)
    return {'code':code,'persisted':persisted,'facts':facts}


def mark_running(ctx,handle):
    if not isinstance(handle,dict) or handle.get('persisted')=='running':return False
    stopping=ctx.get('stopping')
    if stopping and stopping():return False
    path=ctx['persist']+'/'+MARKER
    try:
        ctx['write_persist'](path,json.dumps({'state':'running','time':float(ctx['now']())},separators=(',',':'),sort_keys=True))
        ok=True
    except Exception:ok=False
    if ok:handle['persisted']='running'
    if ok and stopping and stopping():
        try:ctx['write_persist'](path,json.dumps({'state':'stopped','time':float(ctx['now']())},separators=(',',':'),sort_keys=True))
        except Exception:pass
        handle['persisted']='stopped'
    return ok


def monitor_start(ctx):
    code,_,_,recorded,up=_ram_marker(ctx,ctx['runtime']+'/'+MONITOR,
                                     lambda fresh,since:'RESTART-PROCESS' if not fresh and not since else None)
    if code is None:return None
    _emit(ctx,code,'%s: the monitor process ended without a service stop and procd restarted it (uptime %s s)'%(code,_uptime_text(up)),recorded)
    return code if recorded else None


def context(runtime,persist,record=None,stopping=None,log=None):
    """The router functions: files, stat, agent.atomic_json (fsync on flash), /proc/uptime, logger."""
    import os
    from pathlib import Path
    def read(path):
        try:
            with open(path,'rb') as handle:return handle.read().decode('utf-8','replace')
        except OSError:return None
    def mtime(path):
        try:return os.stat(path).st_mtime
        except OSError:return None
    def write(path,text):
        from agent import atomic_json
        atomic_json(Path(path),json.loads(text))
    def uptime():
        text=read('/proc/uptime')
        try:return float(text.split()[0]) if text else None
        except (ValueError,IndexError):return None
    if log is None:
        from pair_auto import _log as log
    return {'runtime':str(runtime),'persist':str(persist),'read':read,'mtime':mtime,'write_ram':write,'write_persist':write,
            'now':time.time,'uptime':uptime,'log':log,'record':record,'stopping':stopping}
