"""Owner-requested reset of charts and statistics: archive first, then measure again from zero.

The RPC only queues a bounded request; the monitoring agent applies it in its own loop, so the running
agent never overwrites a reset with its in-memory copy. Every reset first writes the old data into a
checksummed archive on the router (newest ARCHIVE_KEEP kept), so nothing is lost silently.
"""
import copy,hashlib,json,re,time
from pathlib import Path

RUNTIME=Path('/var/run/homensai-vpn')
PERSIST=Path('/etc/homensai-vpn')
SCOPES=('latency','auto','traffic','quality','speed','ranking','all')
ARCHIVE_KEEP=10
ARCHIVE_BYTES=12*1024*1024
REQUEST='stats-reset-request.json'
RESULT='stats-reset-result.json'


def checksum(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def request(arguments,runtime=None,now=None):
    from agent import atomic_json
    runtime=RUNTIME if runtime is None else Path(runtime);now=time.time() if now is None else now
    if not isinstance(arguments,dict) or set(arguments)!={'scope'} or arguments['scope'] not in SCOPES:
        return {'queued':False,'code':'STATS-RESET-FIELDS'}
    from rpc_throttle import allow
    if not allow('stats_reset',3,now):return {'queued':False,'code':'RPC-RATE-LIMIT'}
    nonce=hashlib.sha256(('%s:%r'%(arguments['scope'],now)).encode()).hexdigest()[:32]
    atomic_json(runtime/REQUEST,{'scope':arguments['scope'],'time':now,'nonce':nonce})
    return {'queued':True,'scope':arguments['scope'],'nonce':nonce}


def pending(runtime=None):
    runtime=RUNTIME if runtime is None else Path(runtime);path=runtime/REQUEST
    try:
        if not path.exists() or path.is_symlink() or path.stat().st_size>4096:return None
        value=json.loads(path.read_text(encoding='utf8'))
    except (OSError,ValueError):value=None
    try:path.unlink()
    except OSError:pass
    if (not isinstance(value,dict) or value.get('scope') not in SCOPES or not isinstance(value.get('nonce'),str)
            or not re.fullmatch(r'[a-f0-9]{32}',value['nonce'])):return None
    return value


def archive(persist,scope,payload,now,writer):
    folder=Path(persist)/'stats-archive'
    if folder.is_symlink():raise ValueError('STATS-RESET-ARCHIVE-PATH')
    folder.mkdir(mode=0o700,exist_ok=True)
    name='%d-%s.json'%(int(now),scope)
    writer(folder/name,{'schema':1,'scope':scope,'time':now,'data':payload,'sha256':checksum(payload)})
    saved=sorted(p for p in folder.glob('*.json') if re.fullmatch(r'[0-9]+-[a-z]+\.json',p.name))
    # Bounded on flash: at most ARCHIVE_KEEP archives and ARCHIVE_BYTES in total; the newest one is always kept.
    def size(p):
        try:return p.stat().st_size
        except OSError:return 0
    while len(saved)>1 and (len(saved)>ARCHIVE_KEEP or sum(size(p) for p in saved)>ARCHIVE_BYTES):
        try:saved.pop(0).unlink()
        except OSError:pass
    return name


def reset_native_history(persist,writer,now,before=None):
    """Counters and events start again; correlation metadata of a running attempt is kept."""
    from native_history import History
    history=History(persist)
    with history.locked():
        data=history.load();old=copy.deepcopy(data)
        if before is not None:before(old)
        history.migrate(data)
        data.update({'events':[],'months':{},'days':{},'totals':{},'counted':{},'daily_since':now,'returns_since':now,
                     'detail_budget_dropped':0,'counter_accuracy':'reset by the owner','legacy_months':{}})
        for key in ('counted_state','counted_reason'):data.pop(key,None)
        writer(history.path,history.envelope(data));writer(history.backup,history.envelope(data))
    return old


def reset_speed_history(writer,before=None):
    from speed_test import HISTORY,load_history,control_lock
    with control_lock():
        data=load_history();old=copy.deepcopy(data)
        if before is not None:before(old)
        data['results']=[];data['history_truncated']=0
        envelope={'schema':1,'data':data,'sha256':checksum(data)}
        writer(HISTORY.with_name('speed-history.backup.json'),envelope);writer(HISTORY,envelope)
    return old


def apply(value,accounting,latency,now,writer,persist=None,website_response=None):
    """Runs inside the agent. Returns (accounting, latency, result); the caller saves a checkpoint."""
    from agent import Accounting
    from latency_history import LatencyHistory
    from reliability import Reliability
    persist=PERSIST if persist is None else Path(persist)
    scope=value['scope'];parts=('latency','auto','traffic','quality','speed') if scope=='all' else ('speed','quality') if scope=='ranking' else (scope,)
    if (website_response is not None and ('latency' in parts or 'quality' in parts)
            and website_response.notice=='WEBSITE-HISTORY-UNAVAILABLE'):
        return accounting,latency,{'nonce':value['nonce'],'scope':scope,'time':now,'done':False,'code':'WEBSITE-HISTORY-UNAVAILABLE'}
    payload={}
    try:
        exported=accounting.export()
        if 'latency' in parts:payload['latency']=copy.deepcopy(latency.data)
        if website_response is not None and ('latency' in parts or 'quality' in parts):payload['website_response']=copy.deepcopy(website_response.data)
        if 'auto' in parts:payload['reliability']=exported.get('reliability')
        if 'traffic' in parts:payload['traffic']={k:exported.get(k) for k in ('months','days','wan','gaps')}
        if 'quality' in parts:payload['quality']={k:exported.get(k) for k in ('quality','activity')}
        from native_history import History
        from speed_test import load_history
        if 'auto' in parts:
            history=History(persist)
            with history.locked():payload['native_history']=history.load()
        if 'speed' in parts:payload['speed']=load_history()
        name=archive(persist,scope,payload,now,writer)
        saved=json.loads((Path(persist)/'stats-archive'/name).read_text(encoding='utf8'))
        if saved.get('sha256')!=checksum(saved.get('data')):raise ValueError('STATS-RESET-ARCHIVE-UNVERIFIED')
        # The files are reset under their own locks; anything recorded after the archive is archived too.
        def extra(key):
            def keep(current):
                if current!=payload.get(key):
                    archive(persist,scope+'late',{key:current},now,writer)
            return keep
        if 'auto' in parts:reset_native_history(persist,writer,now,before=extra('native_history'))
        if 'speed' in parts:reset_speed_history(writer,before=extra('speed'))
    except Exception as error:
        code=str(error) if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'STATS-RESET-FAILED'
        return accounting,latency,{'nonce':value['nonce'],'scope':scope,'time':now,'done':False,'code':code}
    if 'latency' in parts:latency=LatencyHistory()
    if website_response is not None:
        if 'latency' in parts:website_response.clear(now)
        elif 'quality' in parts:website_response.clear_statistics(now)
    if 'auto' in parts:
        accounting.reliability=Reliability(None);accounting.reliability.critical=True
    if 'traffic' in parts:
        accounting.months={};accounting.days={};accounting.previous={};accounting.gaps=0
        if accounting.wan is not None:accounting.wan=Accounting(None,_nested=True)
    if 'quality' in parts:accounting.quality={};accounting.activity={};accounting.activity_previous={}
    return accounting,latency,{'nonce':value['nonce'],'scope':scope,'time':now,'done':True,'archive':name}
