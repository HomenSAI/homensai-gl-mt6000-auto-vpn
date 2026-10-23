"""Live MT3000 FW3 adapter contract. Device preference grants no capability."""
import hashlib
import os
from pathlib import Path
import time

PINS={
 '/etc/init.d/firewall':'dbc6e31653ba3d7e57534386cf1a83523318ed9dbb0d793f7947520e33b0e776',
 '/etc/rc.common':'ebeeedc132a75942ce876465e4636a75f745e468c573fdf9ad058e57e58a0341',
 '/etc/init.d/dnsmasq':'63cb5858ced4dee214f2cceb8a0de986e344607440fff5bf4eae21af381c9936',
 '/usr/bin/gl_block_wan_access_exit':'a02a43b46c6722b012745fd5f960f35414b34e011379181cc5c52d98135926ce',
}


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
    from mt3000_manual_platform import _read,_zones,_workers
    try:
        if Path('/sbin/fw4').exists()or Path('/usr/sbin/fw4').exists():errors.append('MT3000-FIREWALL-UNVERIFIED')
        zones=_zones(_read('/var/run/fw3.state',65536).decode('utf8'))
        if not {'wgclient1','ovpnclient1'}.issubset(zones):errors.append('FW3-SELECTED-ZONE-UNVERIFIED')
    except (OSError,ValueError,UnicodeError):errors.append('FW3-RUNTIME-STATE-UNVERIFIED')
    try:
        for name,want in PINS.items():
            if hashlib.sha256(_read(name,262144)).hexdigest()!=want:errors.append('VENDOR-CODE-CHANGED')
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
