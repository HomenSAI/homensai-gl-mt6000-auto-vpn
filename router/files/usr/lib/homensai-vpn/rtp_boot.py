"""The exact pinned stock boot prefix, without running stock boot/start.

This prepares only empty runtime directories and the zero-byte RTP gate file.
It is not kernel readiness, VPN health, consent or an Auto Start operation.
"""
import hashlib
import os
from pathlib import Path
import stat

ROOT=Path('/')
PINS={'/etc/init.d/vpn-client':'3b751f0691202bc930b8113d7b55d0a38003369c015c672d0797723f1aa79e9a',
      '/usr/bin/rtp2.sh':'d6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e'}
CODE='RTP-BOOT-PRECONDITION-UNVERIFIED'


def checked(path,directory=False,optional=False,temporary_root=False):
    try:info=path.lstat()
    except FileNotFoundError:
        if optional:return None
        raise ValueError(CODE) from None
    if (stat.S_ISLNK(info.st_mode) or info.st_uid!=os.geteuid()
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (info.st_mode&0o022 and not temporary_root)
            or not directory and info.st_size!=0):raise ValueError(CODE)
    if temporary_root and stat.S_IMODE(info.st_mode)!=0o1777:raise ValueError(CODE)
    return info


def contract(root):
    for name,sha in PINS.items():
        path=root/name.lstrip('/')
        if path.is_symlink() or not path.is_file() or path.stat().st_size>262144 or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError(CODE)
    for name,wanted in (('tmp/sysinfo/board_name','glinet,mt3000-snand'),('etc/glversion','4.11.0')):
        path=root/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size>128 or path.read_text().strip()!=wanted:raise ValueError(CODE)
    checked(root/'tmp',directory=True,temporary_root=True)
    checked(root/'tmp/run',directory=True)


def ready(root=None):
    root=ROOT if root is None else Path(root)
    contract(root)
    for name in ('tmp/resolv.conf.d','tmp/hosts.vpn'):checked(root/name,directory=True)
    checked(root/'tmp/run/vpn-client-booted')
    return True


def assess(root=None):
    root=ROOT if root is None else Path(root)
    contract(root)
    directories=[checked(root/name,directory=True,optional=True) is not None for name in ('tmp/resolv.conf.d','tmp/hosts.vpn')]
    marker=checked(root/'tmp/run/vpn-client-booted',optional=True) is not None
    return {'safe':True,'ready':all(directories) and marker,'kernel_verified':False}


def prepare(revision,root=None):
    import native_switch as n
    from agent import RUNTIME,atomic_json
    from auto_control import control_lock
    root=ROOT if root is None else Path(root)
    try:
        with control_lock():
            n.require_control_revision(revision)
            from pair_auto import intent,read_state
            requested=intent();state=read_state()
            if (requested.get('mode')!='on' or requested.get('revision')!=revision or requested.get('id')!=state.get('id')
                    or state.get('revision')!=revision or state.get('phase') not in ('STARTING','RUNNING','HELD')):
                raise n.Refused('CLIENT-STOP')
            assess(root)  # Check every optional path before the first journal/directory mutation.
            paths=[root/name for name in ('tmp/resolv.conf.d','tmp/hosts.vpn')]
            marker=root/'tmp/run/vpn-client-booted'
            before={'directories':[checked(path,directory=True,optional=True) is not None for path in paths],
                    'marker':checked(marker,optional=True) is not None}
            if all(before['directories']) and before['marker']:
                ready(root);return {'prepared':True,'changed':False,'kernel_verified':False}
            record={'revision':revision,'state':'PREPARED','before':before}
            atomic_json(RUNTIME/'rtp-boot-preparation.json',record)
            for path in paths:
                n.require_control_revision(revision)
                if checked(path,directory=True,optional=True) is None:
                    try:path.mkdir(mode=0o755)
                    except FileExistsError:pass
                checked(path,directory=True)
            n.require_control_revision(revision)
            if checked(marker,optional=True) is None:
                fd=os.open(str(marker),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
                try:os.fsync(fd)
                finally:os.close(fd)
            ready(root)
            n.require_control_revision(revision)
            record['state']='VERIFIED';atomic_json(RUNTIME/'rtp-boot-preparation.json',record)
            return {'prepared':True,'changed':True,'kernel_verified':False}
    except (OSError,ValueError):raise n.Refused(CODE) from None
