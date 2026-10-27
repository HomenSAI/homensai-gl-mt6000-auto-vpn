"""Reviewed, narrowly scoped preparation changes on the local router.

No remote address, command, path or UCI key is accepted from an RPC caller.
Startup edits do not stop services, reload networking, reconnect VPNs or start
Auto. Each change has a durable private before-record and independent readback.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import uuid

from agent import RUNTIME, PERSIST, atomic_json, read_json, checksum, inventory
from auto_control import control_lock, revision_locked

ROOT = Path('/')
ACTIONS = {
    'wg-autostart': {'kind':'uci', 'package':'network', 'interface':'wgclient1', 'proto':'wgclient'},
    'ovpn-autostart': {'kind':'uci', 'package':'network', 'interface':'ovpnclient1', 'proto':'ovpnclient'},
    'source-autostart': {'kind':'uci','package':'network','role':'source'},
    'target-autostart': {'kind':'uci','package':'network','role':'target'},
    'vpn-boot': {'kind':'boot', 'service':'vpn-client'},
    'sfe-boot': {'kind':'boot', 'service':'shortcut-fe'},
    'hnat': {'kind':'uci', 'package':'mtkhnat'},
    'flow-offload': {'kind':'uci', 'package':'firewall'},
    'sfe-autoload': {'kind':'autoload'},
}
PACKAGES = ('network','firewall','mtkhnat','homensai_vpn','route_policy','wireguard','ovpnclient')
TERMINAL_MANUAL = {'COMPLETED','REFUSED','CANCELLED','UNCONFIRMED'}


class Refused(ValueError):
    pass


def safe_code(error):
    value = str(error)
    return value if isinstance(error, Refused) and re.fullmatch('[A-Z][A-Z0-9-]{0,95}', value) else 'PREPARATION-UNVERIFIED'


def regular(path, limit=1048576):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise Refused('PREPARATION-FILE-UNVERIFIED')
    return path.read_bytes()


def sync_directory(path):
    fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def file_hashes():
    result={}
    for name in PACKAGES:
        path=ROOT/'etc/config'/name
        result[name]=None if not path.exists() and not path.is_symlink() else hashlib.sha256(regular(path)).hexdigest()
    return result


def boot_id():
    value=regular(ROOT/'proc/sys/kernel/random/boot_id',128).decode('ascii').strip()
    if not re.fullmatch('[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',value):raise Refused('PREPARATION-PLATFORM-UNVERIFIED')
    return value


def records():
    directory = PERSIST/'preparation-changes'
    if directory.is_symlink():raise Refused('PREPARATION-BACKUP-UNVERIFIED')
    if not directory.exists():return []
    if not directory.is_dir():raise Refused('PREPARATION-BACKUP-UNVERIFIED')
    paths = list(directory.iterdir())
    if len(paths) > 64:raise Refused('PREPARATION-HISTORY-LIMIT')
    rows = []
    for path in paths:
        if not re.fullmatch(r'[a-f0-9]{32}\.json',path.name) or path.is_symlink() or not path.is_file() or path.stat().st_size>65536:
            raise Refused('PREPARATION-BACKUP-UNVERIFIED')
        envelope = read_json(path,{})
        data = envelope.get('data') if isinstance(envelope,dict) else None
        if (not isinstance(data,dict) or envelope.get('sha256') != checksum(data)
                or type(data.get('action')) is not str or data['action'] not in ACTIONS or data.get('state') != 'VERIFIED'
                or type(data.get('restart_required')) is not bool or not isinstance(data.get('boot_id'),str)
                or not re.fullmatch('[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',data['boot_id'])
                or type(data.get('time')) not in (int,float) or not 0<data['time']<1e12
                or type(data.get('verified_at')) not in (int,float) or not 0<data['verified_at']<1e12
                or not isinstance(data.get('before'),dict) or data.get('board') not in ('mt3000','mt6000')
                or not isinstance(data.get('revision'),str) or not re.fullmatch('[a-f0-9]{64}',data['revision'])):
            raise Refused('PREPARATION-RECOVERY-REQUIRED')
        rows.append(data)
    return rows


def auto_blocker():
    """Saving firewall/SFE boot settings is not proof of changed live flows."""
    try:
        rows=records()
        if rows and any(row.get('restart_required') and row.get('boot_id')==boot_id() for row in rows):
            return 'PREPARATION-RESTART-REQUIRED'
    except (OSError,ValueError,TypeError,KeyError):return 'PREPARATION-RECOVERY-REQUIRED'
    return None


def guard(settings):
    from configuration_guard import blocked
    from pair_auto import read_state, intent
    from native_switch import Refused as NativeRefused
    try:
        reason = blocked(settings)
        state, request = read_state(), intent()
        if reason or request.get('mode') == 'on':raise Refused('PREPARATION-STOP-AUTO-FIRST')
        if state and (state.get('phase') != 'STOPPED' and not (state.get('phase') == 'FAILED' and not state.get('owned'))):
            raise Refused('PREPARATION-RECOVERY-REQUIRED')
        for name in ('manual-control.json','pair-manual-control.json'):
            pending = read_json(RUNTIME/name,{})
            if pending and (not isinstance(pending,dict) or pending.get('state') not in TERMINAL_MANUAL):
                raise Refused('PREPARATION-STOP-AUTO-FIRST')
    except Refused:raise
    except (OSError,ValueError,TypeError,KeyError,NativeRefused):
        raise Refused('PREPARATION-RECOVERY-REQUIRED') from None


READ_OPTIONS = r"""
local c=require('uci').cursor();local j=require('cjson');local result={}
for _,p in ipairs({'network','firewall','mtkhnat','homensai_vpn','route_policy','wireguard','ovpnclient'}) do
 local changed=c:changes(p);assert(not changed or next(changed)==nil,'pending')
end
c:foreach('network','interface',function(s)
 local name=s['.name']or''
 if name:match('^wgclient[1-9]%d*$')or name:match('^ovpnclient[1-9]%d*$')then
  result[name]={proto=s.proto or j.null,auto=s.auto or j.null}
 end
end)
result.hnat=c:get('mtkhnat','global','enable')or j.null
result.hnat_type=c:get('mtkhnat','global')or j.null
result.defaults={}
c:foreach('firewall','defaults',function(s)
 result.defaults[#result.defaults+1]={section=s['.name'],flow_offloading=s.flow_offloading or j.null,flow_offloading_hw=s.flow_offloading_hw or j.null}
end)
print(j.encode(result))
"""


def options():
    reply = subprocess.run(['/usr/bin/lua','-e',READ_OPTIONS],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8)
    if reply.returncode or len(reply.stdout)>32768:raise Refused('PREPARATION-PENDING-OR-UNREADABLE')
    value = json.loads(reply.stdout)
    if not isinstance(value,dict):raise Refused('PREPARATION-PENDING-OR-UNREADABLE')
    return value


def boot_links(service):
    parent = ROOT/'etc/rc.d'
    if parent.is_symlink() or not parent.is_dir():raise Refused('PREPARATION-BOOT-UNVERIFIED')
    rows=[]
    for path in parent.iterdir():
        if not re.fullmatch('[SK][0-9]{2}'+re.escape(service),path.name):continue
        if not path.is_symlink() or path.resolve() != (ROOT/'etc/init.d'/service).resolve():
            raise Refused('PREPARATION-BOOT-UNVERIFIED')
        metadata=path.lstat()
        rows.append({'name':path.name,'target':os.readlink(str(path)), 'inode':metadata.st_ino,'device':metadata.st_dev})
    if len(rows)>16:raise Refused('PREPARATION-BOOT-UNVERIFIED')
    return sorted(rows,key=lambda row:row['name'])


def hook_available():
    debug = ROOT/'sys/kernel/debug';hook = debug/'hnat/hook_toggle'
    return (not debug.is_symlink() and debug.is_mount() and not (debug/'hnat').is_symlink()
            and not hook.is_symlink() and hook.is_file())


def context(action):
    from device_profile import BOARDS, validate
    from native_switch import Linux
    board = regular(ROOT/'tmp/sysinfo/board_name',128).decode('ascii').strip()
    if board not in BOARDS or regular(ROOT/'etc/glversion',128).decode('ascii').strip()!='4.11.0':
        raise Refused('PREPARATION-PLATFORM-UNVERIFIED')
    data = inventory();settings=data.get('settings',{})
    validate(settings.get('router_model','auto'),BOARDS[board]);guard(settings);history=records()
    before_hashes = file_hashes();boot=boot_id()
    values = options()
    definition=ACTIONS[action];changes=[];before={};done=False;restart=False
    acceleration = Linux().acceleration() if action in ('hnat','sfe-boot','sfe-autoload') else {}
    if definition['kind']=='uci':
        package=definition['package']
        if action in ('wg-autostart','ovpn-autostart','source-autostart','target-autostart'):
            from pair_interfaces import roles,protocol
            name=roles(settings)[definition['role']] if 'role' in definition else definition['interface']
            proto=protocol(name);row=values.get(name,{})
            if not isinstance(row,dict) or row.get('proto')!=proto:raise Refused('PREPARATION-BINDING-UNVERIFIED')
            changes=[{'section':name,'type':'interface','option':'auto','before':row.get('auto'),'after':'0'}]
            before['interface']=name
        elif action=='hnat':
            section_type=values.get('hnat_type')
            if not isinstance(section_type,str) or not re.fullmatch('[A-Za-z0-9_]{1,64}',section_type):raise Refused('PREPARATION-HNAT-UNVERIFIED')
            changes=[{'section':'global','type':section_type,'option':'enable','before':values.get('hnat'),'after':'0'}]
            runtime=acceleration.get('hnat_runtime')
            loaded=acceleration.get('loaded',[])
            if runtime not in ('enabled','disabled') and any(name in loaded for name in ('mtkhnat','mtk_hnat')):
                raise Refused('PREPARATION-HNAT-UNVERIFIED')
            if runtime=='enabled' and not hook_available():raise Refused('PREPARATION-HNAT-UNVERIFIED')
            before['runtime']=runtime
        else:
            restart=True
            defaults=values.get('defaults',[])
            if not isinstance(defaults,list) or not 1<=len(defaults)<=16:raise Refused('PREPARATION-FIREWALL-UNVERIFIED')
            for row in defaults:
                if not isinstance(row,dict) or not isinstance(row.get('section'),str) or not re.fullmatch('[A-Za-z0-9_]{1,64}',row['section']):raise Refused('PREPARATION-FIREWALL-UNVERIFIED')
                for name in ('flow_offloading','flow_offloading_hw'):
                    changes.append({'section':row['section'],'type':'defaults','option':name,'before':row.get(name),'after':'0'})
        if any(row['before'] not in (None,'0','1') for row in changes):raise Refused('PREPARATION-VALUE-UNVERIFIED')
        before.update(package=package,options=changes)
        done=all(row['before']=='0' or action=='flow-offload' and row['before'] is None for row in changes)
        if action=='hnat':done=done and acceleration.get('hnat_runtime')!='enabled'
    elif definition['kind']=='boot':
        before['links']=boot_links(definition['service'])
        done=not any(row['name'].startswith('S') for row in before['links'])
        restart=any(name in acceleration.get('loaded',[]) for name in ('shortcut_fe','shortcut_fe_ipv6','fast_classifier'))
    else:
        from preparation_status import AUTOLOAD_SHA
        source=ROOT/'etc/modules.d/09-shortcut-fe';saved=ROOT/'etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe'
        saved_parent=saved.parent
        if saved_parent.is_symlink():raise Refused('PREPARATION-AUTOLOAD-UNVERIFIED')
        if source.exists() or source.is_symlink():
            content=regular(source,4096)
            if hashlib.sha256(content).hexdigest()!=AUTOLOAD_SHA or saved.exists() or saved.is_symlink():raise Refused('PREPARATION-AUTOLOAD-UNVERIFIED')
            before={'sha256':AUTOLOAD_SHA,'mode':stat.S_IMODE(source.stat().st_mode)}
        else:
            if hashlib.sha256(regular(saved,4096)).hexdigest()!=AUTOLOAD_SHA:raise Refused('PREPARATION-AUTOLOAD-UNVERIFIED')
            before={'sha256':AUTOLOAD_SHA};done=True
        restart=any(name in acceleration.get('loaded',[]) for name in ('shortcut_fe','shortcut_fe_ipv6','fast_classifier'))
    if file_hashes()!=before_hashes:raise Refused('PREPARATION-STALE-REVIEW')
    if not done and len(history)>=64:raise Refused('PREPARATION-HISTORY-LIMIT')
    return {'action':action,'board':BOARDS[board],'boot_id':boot,'firmware':'4.11.0','before':before,'hashes':before_hashes,
            'already_done':done,'restart_required':restart,'runtime':acceleration.get('hnat_runtime')}


def preview(arguments):
    if set(arguments)!={'action'} or type(arguments.get('action')) is not str or arguments['action'] not in ACTIONS:
        return {'accepted':False,'code':'PREPARATION-FIELDS'}
    try:
        with control_lock():
            plan=context(arguments['action']);revision=revision_locked(RUNTIME)
            plan['control_revision']=revision
        return {'accepted':True,'action':plan['action'],'revision':checksum(plan),'control_revision':revision,
                'board':plan['board'],'interface':plan['before'].get('interface'),'already_done':plan['already_done'],'restart_required':plan['restart_required'],
                'auto_started':False}
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        return {'accepted':False,'code':safe_code(error)}


def write_uci(action,plan):
    package=plan['before']['package']
    original=regular(ROOT/'etc/config'/package).decode('utf-8')
    if hashlib.sha256(original.encode()).hexdigest()!=plan['hashes'][package]:raise Refused('PREPARATION-STALE-REVIEW')
    with tempfile.TemporaryDirectory(prefix='preparation-stage-',dir=str(RUNTIME)) as stage:
        request={'action':action,'expected':original,'changes':plan['before']['options'],'stage':stage}
        reply=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/preparation_write.lua'],input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
    if reply.returncode or reply.stdout.strip()!=b'OK':raise Refused('PREPARATION-WRITE-UNCONFIRMED')
    if action=='hnat' and plan['runtime']=='enabled':
        if not hook_available():raise Refused('PREPARATION-HNAT-UNVERIFIED')
        (ROOT/'sys/kernel/debug/hnat/hook_toggle').write_text('0\n',encoding='ascii')


def mutate(action,plan):
    kind=ACTIONS[action]['kind']
    if kind=='uci':write_uci(action,plan)
    elif kind=='boot':
        service=ACTIONS[action]['service']
        if boot_links(service)!=plan['before']['links']:raise Refused('PREPARATION-STALE-REVIEW')
        # Remove only reviewed startup symlinks. No init-script execution or
        # running-service Stop; even an unusual kill-link is preserved.
        for row in plan['before']['links']:
            if not row['name'].startswith('S'):continue
            path=ROOT/'etc/rc.d'/row['name']
            if not path.is_symlink() or path.lstat().st_ino!=row['inode'] or os.readlink(str(path))!=row['target']:
                raise Refused('PREPARATION-STALE-REVIEW')
            path.unlink()
    else:
        source=ROOT/'etc/modules.d/09-shortcut-fe';saved=ROOT/'etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe'
        content=regular(source,4096);metadata=source.stat()
        if source.is_symlink() or hashlib.sha256(content).hexdigest()!=plan['before']['sha256']:
            raise Refused('PREPARATION-STALE-REVIEW')
        if saved.parent.is_symlink():raise Refused('PREPARATION-AUTOLOAD-UNVERIFIED')
        saved.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        # Exclusive, fsynced copy also works across overlay filesystems. A
        # crash can leave both copies; an existing backup is never overwritten.
        fd=os.open(str(saved),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(content);stream.flush();os.fsync(stream.fileno())
        sync_directory(saved.parent.parent)
        sync_directory(saved.parent)
        if (source.is_symlink() or source.stat().st_ino!=metadata.st_ino
                or source.stat().st_dev!=metadata.st_dev or regular(source,4096)!=content):
            raise Refused('PREPARATION-STALE-REVIEW')
        source.unlink()
    for directory in ({'uci':ROOT/'etc/config','boot':ROOT/'etc/rc.d','autoload':ROOT/'etc/modules.d'}[kind],):
        sync_directory(directory)


def apply(arguments,automatic=False):
    if (set(arguments)!={'action','revision','control_revision'} or type(arguments.get('action')) is not str
            or arguments['action'] not in ACTIONS or not isinstance(arguments['revision'],str)
            or not re.fullmatch('[a-f0-9]{64}',arguments['revision']) or not isinstance(arguments['control_revision'],str)
            or not re.fullmatch('[a-f0-9]{32}',arguments['control_revision'])):
        return {'applied':False,'code':'PREPARATION-FIELDS'}
    record=None;path=None;attempted=False
    try:
        with control_lock():
            if revision_locked(RUNTIME)!=arguments['control_revision']:raise Refused('PREPARATION-STALE-REVIEW')
            action=arguments['action'];plan=context(action);plan['control_revision']=arguments['control_revision']
            if checksum(plan)!=arguments['revision']:raise Refused('PREPARATION-STALE-REVIEW')
            if plan['already_done']:
                return {'applied':True,'verified':True,'already_done':True,'action':action,'code':'PREPARATION-VERIFIED','restart_required':plan['restart_required'],'auto_started':False}
            from rpc_throttle import allow
            if not automatic and not allow('preparation_apply',2):raise Refused('RPC-RATE-LIMIT')
            record={'action':action,'state':'PREPARED','time':time.time(),'board':plan['board'],'boot_id':plan['boot_id'],
                    'before':plan['before'],'revision':arguments['revision']}
            path=PERSIST/'preparation-changes'/(uuid.uuid4().hex+'.json')
            if PERSIST.is_symlink() or path.parent.is_symlink():raise Refused('PREPARATION-BACKUP-UNVERIFIED')
            path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            sync_directory(PERSIST)
            atomic_json(path,{'data':record,'sha256':checksum(record)})
            attempted=True
            mutate(action,plan)
            # Ignore only our own PREPARED record during readback; every other
            # guard and a fresh UCI/file observation remains mandatory.
            after=verify(action,plan)
            record.update(state='VERIFIED',verified_at=time.time(),restart_required=after['restart_required'])
            atomic_json(path,{'data':record,'sha256':checksum(record)})
        return {'applied':True,'verified':True,'action':action,'code':'PREPARATION-VERIFIED',
                'restart_required':after['restart_required'],'auto_started':False}
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        # A durable PREPARED record deliberately survives an unconfirmed write.
        # Do not undo over a possible newer router edit or report a false PASS.
        return {'applied':False,'verified':False,'code':safe_code(error),'change_may_have_applied':attempted,'auto_started':False}


# Pressing Auto is the owner's consent to the preparation it needs. Each failed check that can be
# repaired without a router restart is fixed with the same reviewed writer as its button: the original
# value is preserved first and the result is read back. A restart-only fix still ends in a named refusal.
AUTO_ACTIONS={'PREP-STOCK-VPN-BOOT':'vpn-boot','PREP-SOURCE-AUTOSTART':'source-autostart','PREP-TARGET-AUTOSTART':'target-autostart',
              'PREP-WGCLIENT1-AUTOSTART':'wg-autostart','PREP-OVPNCLIENT1-AUTOSTART':'ovpn-autostart','PREP-HNAT-CONFIG':'hnat','PREP-SFE-BOOT':'sfe-boot'}


def auto_prepare(settings,control_revision):
    from preparation_status import snapshot
    repaired=[]
    for _ in range(len(AUTO_ACTIONS)):
        failed=[row.get('code') for row in snapshot(settings=settings).get('checks',[]) if row.get('state')!='pass']
        todo=[code for code in failed if code in AUTO_ACTIONS and code not in repaired]
        if not todo:return {'repaired':repaired,'code':None}
        code=todo[0];action=AUTO_ACTIONS[code]
        try:
            with control_lock():
                plan=context(action);plan['control_revision']=control_revision
                revision=checksum(plan)
        except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
            return {'repaired':repaired,'code':safe_code(error)}
        result=apply({'action':action,'revision':revision,'control_revision':control_revision},automatic=True)
        if not result.get('applied'):return {'repaired':repaired,'code':result.get('code') or 'PREPARATION-WRITE-UNCONFIRMED'}
        if result.get('restart_required'):return {'repaired':repaired+[code],'code':'PREPARATION-RESTART-REQUIRED'}
        repaired.append(code)
    return {'repaired':repaired,'code':None}


def verify(action,plan):
    from native_switch import Linux
    guard(inventory().get('settings',{}))
    values=options();kind=ACTIONS[action]['kind'];restart=action=='flow-offload'
    if kind=='uci':
        for row in plan['before']['options']:
            if action in ('wg-autostart','ovpn-autostart','source-autostart','target-autostart'):value=values.get(row['section'],{}).get('auto')
            elif action=='hnat':value=values.get('hnat')
            else:
                matches=[item for item in values.get('defaults',[]) if item.get('section')==row['section']]
                if len(matches)!=1:raise Refused('PREPARATION-WRITE-UNCONFIRMED')
                value=matches[0].get(row['option'])
            if value!='0':raise Refused('PREPARATION-WRITE-UNCONFIRMED')
        if action=='hnat':
            acceleration=Linux().acceleration()
            if any(name in acceleration.get('loaded',[]) for name in ('mtkhnat','mtk_hnat')) and acceleration.get('hnat_runtime')!='disabled':
                raise Refused('PREPARATION-HNAT-UNVERIFIED')
    elif kind=='boot':
        if any(row['name'].startswith('S') for row in boot_links(ACTIONS[action]['service'])):raise Refused('PREPARATION-WRITE-UNCONFIRMED')
    else:
        source=ROOT/'etc/modules.d/09-shortcut-fe';saved=ROOT/'etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe'
        if source.exists() or source.is_symlink() or hashlib.sha256(regular(saved,4096)).hexdigest()!=plan['before']['sha256']:
            raise Refused('PREPARATION-WRITE-UNCONFIRMED')
    if action in ('sfe-boot','sfe-autoload'):
        restart=any(name in Linux().acceleration().get('loaded',[]) for name in ('shortcut_fe','shortcut_fe_ipv6','fast_classifier'))
    after_hashes=file_hashes()
    changed=ACTIONS[action].get('package')
    if any(after_hashes[name]!=value for name,value in plan['hashes'].items() if name!=changed):
        raise Refused('PREPARATION-EXTERNAL-CHANGE')
    return {'restart_required':restart}
