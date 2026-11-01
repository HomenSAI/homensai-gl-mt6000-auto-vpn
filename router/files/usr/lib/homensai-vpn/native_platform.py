"""Live MT3000 FW3 adapter contract. Device preference grants no capability."""
import hashlib
import os
from pathlib import Path
import stat as stat_module
import threading
import time

PINS={
 '/etc/init.d/firewall':'dbc6e31653ba3d7e57534386cf1a83523318ed9dbb0d793f7947520e33b0e776',
 '/etc/rc.common':'ebeeedc132a75942ce876465e4636a75f745e468c573fdf9ad058e57e58a0341',
 '/etc/init.d/dnsmasq':'63cb5858ced4dee214f2cceb8a0de986e344607440fff5bf4eae21af381c9936',
 '/usr/bin/gl_block_wan_access_exit':'a02a43b46c6722b012745fd5f960f35414b34e011379181cc5c52d98135926ce',
}

# Derived-value cache by file fingerprint (TODO-PERF 4.1), the same rules as platform.lua cached_file() and the C
# core (docs/architecture/DIAGNOSTIC-CACHE-2026-11-01.ru.md):
#   key     = type:inode:size:mtime:ctime of lstat(path) taken BEFORE the read (whole seconds, as the Lua sys.key on
#             the router); no entry for a missing file;
#   trusted = the newest of mtime/ctime is at least CACHE_RACY seconds older than the wall clock at the read;
#   reused  = same key, trusted, computed less than CACHE_MAX_AGE seconds ago (monotonic);
#   a compute() that raises leaves no entry.
CACHE_RACY=2
CACHE_MAX_AGE=30
_DERIVED={}
_DERIVED_LOCK=threading.Lock()


def _kind(mode):
    for test,name in ((stat_module.S_ISREG,'reg'),(stat_module.S_ISDIR,'dir'),(stat_module.S_ISLNK,'lnk'),
                      (stat_module.S_ISCHR,'chr'),(stat_module.S_ISBLK,'blk'),(stat_module.S_ISFIFO,'fifo'),(stat_module.S_ISSOCK,'sock')):
        if test(mode):return name
    return 'other'


def stat_row(path):
    """The lstat facts of the key (None when the path is missing), as the Lua sys.lstat returns them."""
    try:st=os.lstat(str(path))
    except OSError:return None
    return {'type':_kind(st.st_mode),'ino':st.st_ino,'size':st.st_size,'mtime':int(st.st_mtime),'ctime':int(st.st_ctime)}


def stat_key(row):
    return ':'.join(str(row.get(k)) for k in ('type','ino','size','mtime','ctime'))


def cache_trusted(row,wall):
    newest=max(row['mtime'] if isinstance(row.get('mtime'),int) else float('inf'),row['ctime'] if isinstance(row.get('ctime'),int) else float('inf'))
    return newest+CACHE_RACY<=wall


def cache_reusable(entry,row,clock):
    if not entry or row is None or not entry['trusted'] or entry['key']!=stat_key(row):return False
    return 0<=clock-entry['time']<CACHE_MAX_AGE


def cached_file(name,path,compute,lstat=None,wall=None,clock=None):
    """compute() reads path itself; returns (value, computed). Callers must not change the returned value."""
    lstat=lstat or stat_row;wall=wall or time.time;clock=clock or time.monotonic
    row=lstat(path)
    with _DERIVED_LOCK:entry=_DERIVED.get(name)
    if row is not None and cache_reusable(entry,row,clock()):return entry['value'],False
    with _DERIVED_LOCK:_DERIVED.pop(name,None)
    value=compute()
    if row is not None:
        with _DERIVED_LOCK:_DERIVED[name]={'key':stat_key(row),'value':value,'trusted':cache_trusted(row,wall()),'time':clock()}
    return value,True


def forget_derived(name=None):
    with _DERIVED_LOCK:
        if name is None:_DERIVED.clear()
        else:_DERIVED.pop(name,None)


def sha_file(path,maximum=None,read=None):
    """sha256 of a file, cached by its fingerprint; read(path, maximum) defaults to mt3000_manual_platform._read."""
    def compute():
        if read is not None:data=read(path,maximum)
        elif maximum is None:data=Path(path).read_bytes()
        else:
            from mt3000_manual_platform import _read
            data=_read(path,maximum)
        return hashlib.sha256(data).hexdigest()
    return cached_file('sha:%s:%s'%(maximum if maximum is not None else '-',path),path,compute)[0]


FW3_STATE='/var/run/fw3.state'


def fw3_zones():
    """The zone set of /var/run/fw3.state (read, UTF-8, _zones), cached by the file's fingerprint."""
    from mt3000_manual_platform import _read,_zones
    return cached_file('fw3-zones',FW3_STATE,lambda:frozenset(_zones(_read(FW3_STATE,65536).decode('utf8'))))[0]


def assess(board,data):
    """Additional actual-platform checks; common vendor/offload/LAN guards remain."""
    if board.get('board_name')=='glinet,gl-mt6000':return []
    if board.get('board_name')!='glinet,mt3000-snand':return ['UNSUPPORTED-BOARD']
    errors=[]
    release=board.get('release');release=release if isinstance(release,dict)else{}
    if (board.get('model')!='GL.iNet GL-MT3000' or board.get('kernel')!='5.4.211'
            or release.get('target')!='mediatek/mt7981' or os.uname().machine!='aarch64'):
        errors.append('MT3000-FIRMWARE-UNVERIFIED')
    include=data.get('firewall_include',{})
    if (not isinstance(include,dict) or include.get('path')!='/usr/bin/rtp2.sh' or include.get('type')!='script'
            or include.get('reload')!='0' or include.get('enabled')not in(None,'1')):
        errors.append('FW3-INCLUDE-CONTRACT-UNVERIFIED')
    from mt3000_manual_platform import _workers
    try:
        if Path('/sbin/fw4').exists()or Path('/usr/sbin/fw4').exists():errors.append('MT3000-FIREWALL-UNVERIFIED')
        zones=fw3_zones()
        from pair_interfaces import roles
        if not set(roles(data.get('settings',{})).values()).issubset(zones):errors.append('FW3-SELECTED-ZONE-UNVERIFIED')
    except (OSError,ValueError,UnicodeError):errors.append('FW3-RUNTIME-STATE-UNVERIFIED')
    try:
        for name,want in PINS.items():
            if sha_file(name,262144)!=want:errors.append('VENDOR-CODE-CHANGED')
    except (OSError,ValueError):errors.append('VENDOR-CODE-UNVERIFIED')
    try:
        if _workers(time.monotonic()+2)['busy']:errors.append('VENDOR-WORKER-BUSY')
        for name in ('gl_reload_service','gl_restart_service'):
            p=Path('/var/run')/name
            if p.is_symlink()or p.exists()and(not p.is_dir()or any(p.iterdir())):errors.append('VENDOR-WORKER-BUSY')
    except (OSError,ValueError):errors.append('VENDOR-WORKER-QUIET-UNVERIFIED')
    return list(dict.fromkeys(errors))


def wait_quiet(seconds=20,clock=time.monotonic,sleep=time.sleep,sample=None):
    """RTP backgrounds DNS restart and firewall reload; command exit is not done."""
    from mt3000_manual_platform import _workers
    sample=sample or _workers;end=clock()+seconds;quiet=None;count=0;unverified=False
    while clock()<end:
        try:
            row=sample(end)
            if not isinstance(row,dict):raise ValueError('VENDOR-WORKER-QUIET-UNVERIFIED')
            busy=row.get('busy')
            if row.get('verified')is not True or type(busy)is not int or not 0<=busy<=16:raise ValueError('VENDOR-WORKER-QUIET-UNVERIFIED')
            queues=False
            for name in ('gl_reload_service','gl_restart_service'):
                p=Path('/var/run')/name
                if p.is_symlink()or p.exists()and(not p.is_dir()or any(p.iterdir())):queues=True
        except (OSError,ValueError):
            # Process/queue reads can race a short-lived vendor child. Unknown
            # never counts as quiet; restart the streak within the same deadline.
            quiet=None;count=0;unverified=True
            sleep(min(.75,max(0,end-clock())));continue
        if clock()>=end:break
        if busy or queues:quiet=None;count=0
        else:
            quiet=clock()if quiet is None else quiet;count+=1
            if clock()-quiet>=3 and count>=4:return
        sleep(min(.75,max(0,end-clock())))
    raise ValueError('VENDOR-WORKER-QUIET-UNVERIFIED' if unverified else 'VENDOR-WORKER-BUSY')
