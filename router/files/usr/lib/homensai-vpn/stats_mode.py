"""Statistics mode (owner decision, 30 Oct 2026).

'work' (default): only what switching needs is kept. Switch events are rare and always written to the flash
history (read, shown, released: no resident copy in work mode); the accounting is saved to flash once a day; the
latency/response histories are neither recorded nor saved. On the MT3000 (beta10) the checkpoint alone wrote
2 x 477 KB every 15 min, about 92 MB per day; the measured Work/Diagnostics difference is in docs/MEASUREMENTS.

'diagnostic': everything is recorded as before, for a bounded time the owner agreed to (1, 3, 7 or 14 days);
then the router returns to 'work' by itself. Diagnostic data already on flash is kept and shown again later.

Read from the package config file itself (no process), cached by its mtime: every monitor pass and every
controller transition asks. Without the package config (a host, the test suite) everything is recorded as
before, like fast_switch_enabled() keeps the old path there.
"""
import re
import time
from pathlib import Path

CONFIG=Path('/etc/config/homensai_vpn')
HOURS=(24,72,168,336)  # 1, 3, 7 or 14 days
DEFAULT_HOURS=24
WORK_SAMPLE_SECONDS=6*3600     # work mode: probe samples kept for decisions and recommendations
WORK_CHECKPOINT_SECONDS=86400  # work mode: accounting saved to flash at most once a day (and at shutdown)
_CACHE={'key':None,'options':{}}


def options(config=None):
    path=Path(config) if config is not None else CONFIG
    try:
        info=path.stat();key=(str(path),info.st_ino,info.st_size,info.st_mtime_ns)
    except OSError:
        return None
    if _CACHE['key']==key:return _CACHE['options']
    try:text=path.read_text(encoding='utf8')
    except (OSError,UnicodeError):return {}
    found={}
    for name in ('stats_mode','stats_until'):
        match=re.search(r"^\s*option\s+%s\s+'?([A-Za-z0-9_.-]{1,32})'?\s*$"%name,text,re.M)
        if match:found[name]=match.group(1)
    _CACHE.update(key=key,options=found)
    return found


def until(config=None):
    try:value=float((options(config) or {}).get('stats_until') or 0)
    except ValueError:return 0.0
    return value if value>0 else 0.0


def diagnostic(now=None,config=None):
    """True while the owner's bounded diagnostic window is open."""
    now=time.time() if now is None else now
    found=options(config)
    if found is None:return True  # no package config: not an installed router, record everything as before
    return found.get('stats_mode')=='diagnostic' and now<until(config)<=now+HOURS[-1]*3600+60


def public(now=None,config=None):
    now=time.time() if now is None else now
    active=diagnostic(now,config)
    bounded=active and until(config)>0
    return {'mode':'diagnostic' if active else 'work','until':until(config) if bounded else None,
            'remaining':max(0,round(until(config)-now)) if bounded else 0,'hours':list(HOURS),'default_hours':DEFAULT_HOURS,
}


def payload(arguments,now=None):
    """setup_stats: {'mode':'work'} or {'mode':'diagnostic','hours':24|72|168|336}; {'mode':'retention',...} is the
    retention choice (retention_settings.payload)."""
    now=time.time() if now is None else now
    if isinstance(arguments,dict) and arguments.get('mode')=='retention':
        from retention_settings import payload as retention_payload
        return retention_payload(arguments)
    if not isinstance(arguments,dict) or arguments.get('mode') not in ('work','diagnostic'):raise ValueError('STATS-SETTINGS-FIELDS')
    if arguments['mode']=='work':
        if set(arguments)!={'mode'}:raise ValueError('STATS-SETTINGS-FIELDS')
        return {'main':{'stats_mode':'work','stats_until':'0'},'servers':[]}
    if set(arguments)!={'mode','hours'} or type(arguments['hours']) is not int or arguments['hours'] not in HOURS:
        raise ValueError('STATS-SETTINGS-FIELDS')
    return {'main':{'stats_mode':'diagnostic','stats_until':str(int(now+arguments['hours']*3600))},'servers':[]}


# Files listed on Advanced > Statistics collection: (where, name, backup copy or None).
STORAGE=(('ram','status.json',None),
         ('flash','native-transaction.json',None),('flash','pair-auto-state.json',None),
         ('flash','native-history.json','native-history.backup.json'),('flash','checkpoint.json','checkpoint.backup.json'),
         ('flash','latency-history.json',None),('flash','ping-response-history.json',None),('flash','website-response-history.json',None),
         ('flash','response-compare.json',None),('flash','probe-history.json',None),('flash','switch-timing.json',None),
         ('flash','speed-history.json','speed-history.backup.json'),('flash','fault-history.json',None))


def storage(runtime,persist):
    """Bytes per listed file (with its backup copy), keyed 'ram:<name>' / 'flash:<name>'; only stat() calls."""
    result={}
    for where,name,backup in STORAGE:
        base=Path(runtime if where=='ram' else persist);total=None
        for item in (name,backup):
            if item is None:continue
            try:total=(total or 0)+(base/item).stat().st_size
            except OSError:pass
        if total is not None:result[where+':'+name]=total
    return result


def history_target(runtime,persist,now=None):
    """(directory, limit) of the event journal: always the flash history; switch events are rare (owner decision)."""
    return (persist,10000)
