"""How long statistics are kept (owner, 31 Oct 2026): by time or by a size budget.

UCI main options (lua/retention.lua is the same code for the Lua line; the page reads model() from the status):
  stats_retention_mode  'time' | 'size'           absent: the old option history_days (1..7, default 7) decides
  stats_retention_days  1..7, 14 or 30            the slider stops of the time mode
  stats_retention_mb    1..32 (whole MB of flash) the size mode budget

The chosen period applies to every detail the app keeps per day: latency and response minute rows, accounting
detail (quality hours, activity days, incidents), the event history and speed tests. Count/byte caps of each file
remain independent upper bounds. In size mode the period is the number of whole days the size model fits into the
budget (at least 1, at most 30) and the two minute-row files additionally drop their oldest rows at save time when
they exceed their share of the budget (trim_to_budget), so the budget holds even where the model is off.

Size model (bytes; an estimate, not a measurement of this router). Minute rows: one row per observed minute,
86400 // max(60, interval) rows a day. Calibrated 31 Oct 2026 by filling one day through the real classes
(latency_history.LatencyHistory, ping/website_response_history; compact JSON as atomic_json writes it) and by
decoding those files with canon.decode in Lua 5.1 64-bit (collectgarbage delta):
  latency row        79 B on flash with checks faster than once a minute (long float means), 57 B otherwise; 422 B RAM
  response row       69 B on flash (ping and websites alike, 1-5 min ping interval); 548 B RAM
  accounting detail  69778 B a day = checkpoint.json 477 KB at 7 days, measured on the MT3000 (1.0.0-beta10,
                     30 Oct 2026); twice on flash (backup copy); capped by the accounting's own 3 MB budget;
                     RAM assumed 7x the file (the history files above decode to 5.4-8.0x)
  comparison         36421 B flash / 212753 B RAM, fixed: 7 days of hourly means (response_compare.KEEP), only
                     when 'measure all methods' is on
Not modelled (bounded by their own caps, independent of the setting's growth): status samples (10000 rows), the
event history (switches are rare; 2 MB budget), speed and failure tests.
"""
import json
import re
import time
from pathlib import Path

MODES=('time','size')
DAY_STOPS=(1,2,3,4,5,6,7,14,30)
MAX_DAYS=30
LEGACY_MAX_DAYS=7
DEFAULT_DAYS=7
MB_MIN=1
MB_MAX=32
DEFAULT_MB=4
MIB=1048576
MODEL={'latency_row_flash_fast':79,'latency_row_flash_slow':57,'response_row_flash':69,
       'latency_row_ram':422,'response_row_ram':548,
       'accounting_day_flash':69778,'accounting_cap':3*MIB,'accounting_ram_ratio':7,
       'compare_flash':36421,'compare_ram':212753}
CONFIG=Path('/etc/config/homensai_vpn')
OPTIONS=('history_days','stats_retention_mode','stats_retention_days','stats_retention_mb','interval','response_metric','response_compare')
_cached=None


def _int(raw):
    """A whole number from inventory (int) or UCI text (decimal digits); anything else is None."""
    if type(raw) is int:return raw
    if isinstance(raw,str) and re.fullmatch(r'[0-9]{1,4}',raw):return int(raw)
    return None


def legacy_days(settings):
    raw=settings.get('history_days',DEFAULT_DAYS) if isinstance(settings,dict) else DEFAULT_DAYS
    if type(raw) is int and 1<=raw<=LEGACY_MAX_DAYS:return raw
    if isinstance(raw,str) and raw in tuple(str(n) for n in range(1,LEGACY_MAX_DAYS+1)):return int(raw)
    return DEFAULT_DAYS


def choice(settings):
    """(mode, days, mb) the owner chose; without the new options the old history_days decides (time mode)."""
    settings=settings if isinstance(settings,dict) else {}
    mode=settings.get('stats_retention_mode')
    days=_int(settings.get('stats_retention_days'))
    if mode not in MODES or days not in DAY_STOPS:days=legacy_days(settings)
    mb=_int(settings.get('stats_retention_mb'))
    if mb is None or not MB_MIN<=mb<=MB_MAX:mb=DEFAULT_MB
    return (mode if mode in MODES else 'time',days,mb)


def _interval(settings):
    value=_int(settings.get('interval')) if isinstance(settings,dict) else None
    return value if value is not None and 10<=value<=300 else 10


def _flag(value):return value is True or value=='1'


def per_day(settings):
    """Bytes a day of each modelled part: {'latency':(flash,ram),'response':(flash,ram),'accounting':(flash,ram)}."""
    interval=_interval(settings);rows=86400//max(60,interval)
    latency=MODEL['latency_row_flash_fast'] if interval<60 else MODEL['latency_row_flash_slow']
    accounting=MODEL['accounting_day_flash']
    return {'rows':rows,'latency':(rows*latency,rows*MODEL['latency_row_ram']),
            'response':(rows*MODEL['response_row_flash'],rows*MODEL['response_row_ram']),
            'accounting':(accounting,accounting*MODEL['accounting_ram_ratio'])}


def compare_on(settings):return isinstance(settings,dict) and _flag(settings.get('response_compare'))


def estimate(settings,days):
    """Approximate bytes kept for `days` days: flash and RAM while Diagnostics records, and in Work mode."""
    part=per_day(settings);compare=compare_on(settings)
    accounting=min(MODEL['accounting_cap'],days*part['accounting'][0])
    accounting_ram=accounting*MODEL['accounting_ram_ratio']
    flash=days*(part['latency'][0]+part['response'][0])+2*accounting+(MODEL['compare_flash'] if compare else 0)
    ram=days*(part['latency'][1]+part['response'][1])+accounting_ram+(MODEL['compare_ram'] if compare else 0)
    return {'flash':flash,'ram':ram,'work_flash':2*accounting,'work_ram':accounting_ram}


def size_days(settings,mb):
    """Whole days the model fits into mb MB of flash (1..30)."""
    part=per_day(settings)
    budget=mb*MIB-(MODEL['compare_flash'] if compare_on(settings) else 0)
    daily=part['latency'][0]+part['response'][0]+2*part['accounting'][0]
    return max(1,min(MAX_DAYS,budget//daily))


def resolve(settings):
    """The effective retention: period in days and, in size mode, the byte budgets of the two minute-row files."""
    mode,days,mb=choice(settings)
    result={'mode':mode,'days':days,'mb':mb,'effective_days':days,'latency_bytes':None,'response_bytes':None}
    if mode=='size':
        part=per_day(settings)
        budget=max(0,mb*MIB-(MODEL['compare_flash'] if compare_on(settings) else 0))
        daily=part['latency'][0]+part['response'][0]+2*part['accounting'][0]
        result.update(effective_days=size_days(settings,mb),latency_bytes=budget*part['latency'][0]//daily,
                      response_bytes=budget*part['response'][0]//daily)
    return result


def days(settings):
    """Effective detail period in days (1..30) for the histories, accounting detail, events and speed tests."""
    return resolve(settings)['effective_days']


def public(settings):
    """status.stats_mode.retention: the choice, the effective period and the model inputs for the page."""
    resolved=resolve(settings);settings=settings if isinstance(settings,dict) else {}
    return dict(resolved,interval=_interval(settings),compare=compare_on(settings),
                websites=settings.get('response_metric')=='websites',day_stops=list(DAY_STOPS),
                mb_min=MB_MIN,mb_max=MB_MAX,model=dict(MODEL),estimate=estimate(settings,resolved['effective_days']))


def trim_to_budget(data,budget):
    """Drop the oldest minute rows until the compact JSON of data fits budget bytes; returns how many were dropped.
    Integer steps only, so lua/retention.lua drops exactly the same rows."""
    if type(budget) is not int or budget<0 or not isinstance(data,dict) or not isinstance(data.get('rows'),list):return 0
    size=len(json.dumps(data,separators=(',',':'),allow_nan=False).encode())
    dropped=0
    while size>budget and data['rows']:
        count=len(data['rows'])
        take=min(count,max(1,-(-(size-budget)*count//size)))
        del data['rows'][:take];dropped+=take
        size=len(json.dumps(data,separators=(',',':'),allow_nan=False).encode())
    return dropped


def payload(arguments):
    """setup_stats {'mode':'retention','retention':'time','days':N} or {'mode':'retention','retention':'size','mb':N}."""
    if not isinstance(arguments,dict) or arguments.get('retention') not in MODES:raise ValueError('STATS-RETENTION-FIELDS')
    if arguments['retention']=='time':
        if set(arguments)!={'mode','retention','days'}:raise ValueError('STATS-RETENTION-FIELDS')
        if type(arguments['days']) is not int or arguments['days'] not in DAY_STOPS:raise ValueError('STATS-RETENTION-DAYS')
        # history_days keeps the closest old value for older readers and a downgrade.
        return {'main':{'stats_retention_mode':'time','stats_retention_days':str(arguments['days']),
                        'history_days':str(min(LEGACY_MAX_DAYS,arguments['days']))},'servers':[]}
    if set(arguments)!={'mode','retention','mb'}:raise ValueError('STATS-RETENTION-FIELDS')
    if type(arguments['mb']) is not int or not MB_MIN<=arguments['mb']<=MB_MAX:raise ValueError('STATS-RETENTION-SIZE')
    return {'main':{'stats_retention_mode':'size','stats_retention_mb':str(arguments['mb'])},'servers':[]}


def config_settings(config=None):
    """The retention-relevant options of the main section of the package config (no process); None without it."""
    path=Path(config) if config is not None else CONFIG
    try:text=path.read_text(encoding='utf8')
    except (OSError,UnicodeError):return None
    found={};section=None
    for line in text.splitlines():
        head=re.match(r"^\s*config\s+(\S+)",line)
        if head:section=head.group(1);continue
        if section!='main':continue
        match=re.match(r"^\s*option\s+([a-z_]+)\s+'?([A-Za-z0-9_.-]{1,32})'?\s*$",line)
        if match and match.group(1) in OPTIONS and match.group(1) not in found:found[match.group(1)]=match.group(2)
    return found


def configured_days(config=None):
    """days() of the installed package config, cached for 5 s; 7 without a readable config (a host, tests)."""
    global _cached
    now=time.monotonic()
    if config is None and _cached and 0<=now-_cached[0]<5:return _cached[1]
    found=config_settings(config)
    value=days(found) if found is not None else DEFAULT_DAYS
    if config is None:_cached=(now,value)
    return value


def memory_available():
    try:
        with open('/proc/meminfo') as stream:
            for line in stream:
                if line.startswith('MemAvailable:'):return int(line.split()[1])*1024
    except (OSError,ValueError,IndexError):pass
    return None


def capacity(persist):
    """status.stats_mode.capacity: free flash under the persist directory and available RAM, in bytes (or None)."""
    import shutil
    try:free=shutil.disk_usage(str(persist)).free
    except OSError:free=None
    return {'flash_free':free,'ram_available':memory_available()}
