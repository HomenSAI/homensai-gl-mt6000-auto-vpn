"""MIT. Experimental, deadline-limited switching of existing GL.iNet rules.

Separate procd supervisor; does not start profiles, edit keys, or disable Kill Switch.
Only two adjacent, unrestricted, already connected VPN rules may exchange order.
No automatic use before an externally confirmed trial. Unknown prerequisites block.
"""
import fcntl
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import socket
import ssl
import subprocess
import sys
import time
import uuid
from datetime import datetime

from agent import RUNTIME, PERSIST, atomic_json, read_json, command, inventory, probe, bound_socket
from failover_plan import streak
from native_history import History, HistoryError

HELPER='/usr/lib/homensai-vpn/native_policy.lua'
TABLE='homensai_vpn_guard'
JOURNAL=PERSIST/'native-transaction.json'
STATE=RUNTIME/'native-status.json'
CERT=PERSIST/'native-certificate.json'
ATTEMPTS=PERSIST/'native-attempts.json'
PREPARE=PERSIST/'acceleration-prepare.json'
SAFE=re.compile(r'^[A-Za-z0-9_]{1,64}$')
STOP=False


class Refused(Exception):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def publish(value):
    value=dict(value,time=time.time())
    try:History(PERSIST).record(value)
    except (OSError,ValueError,KeyError,TypeError):
        atomic_json(STATE,{'state':'BLOCKED','blockers':['HISTORY-001']})
        raise Refused('HISTORY-001')
    atomic_json(STATE,value)


def journal_write(value):
    atomic_json(JOURNAL,{'schema':1,'data':value,'sha256':digest(value)})


def journal_read():
    envelope=read_json(JOURNAL,{})
    if not envelope:return {}
    value=envelope.get('data')
    if envelope.get('schema')!=1 or not isinstance(value,dict) or envelope.get('sha256')!=digest(value):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    before=value.get('before',[]);after=value.get('after',[])
    if not before or len(before)!=len(set(before)) or set(before)!=set(after) or len(before)!=len(after):
        raise Refused('JOURNAL-ORDER-INVALID')
    if any(not isinstance(s,str) or not SAFE.fullmatch(s) for s in before):raise Refused('JOURNAL-SECTION-INVALID')
    return value


def deadline(value):
    try:return float(value or 0)
    except ValueError:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:raise Refused('DEADLINE-TIMEZONE-REQUIRED')
        return parsed.timestamp()


def fresh_hook_state(lines,after):
    """Some vendor debugfs reads print status to the kernel ring, returning no bytes."""
    for line in reversed(lines.splitlines()):
        match=re.match(r'^\[\s*(\d+(?:\.\d+)?)\]\s*(.*)$',line)
        if not match or float(match[1])<after:continue
        message=match[2].lower()
        if 'going to' in message:continue  # An action request is not proof of resulting state.
        match=re.fullmatch(r'(?:hnat[ _]*)?hook(?:_toggle)?\s*(?:(?:is|state|status|currently|:|=)\s*)*(enabled|disabled)[ !.]*',message)
        if match:return match[1]
    return 'unknown'


def policy_hash(sections):
    return digest(sorted([{k:v for k,v in s.items() if k!='.index'} for s in sections],key=lambda s:s['.name']))


def choose(data,profiles):
    """Fail closed on policy layouts outside the explicitly supported small subset."""
    sections=data['sections']; settings=data['settings']
    defaults=[s for s in sections if s.get('.type')=='default']
    global_policy=[s for s in sections if s.get('.name')=='global']
    if len(defaults)!=1 or defaults[0].get('enabled')!='0':raise Refused('DIRECT-WAN-FALLBACK')
    if len(global_policy)!=1 or global_policy[0].get('enabled')!='1':raise Refused('VPN-POLICY-DISABLED')
    if data.get('ipv6')!='0':raise Refused('IPV6-NOT-EXPLICITLY-DISABLED')
    for s in data.get('firewall_defaults',[]):
        if any(s.get(k,'0') not in ('0',None) for k in ('flow_offloading','flow_offloading_hw')):
            raise Refused('FLOW-OFFLOAD-ENABLED')
    generic=[];special=[]
    for index,s in enumerate(sections):
        if s.get('.type')!='rule' or s.get('enabled')!='1':continue
        if s.get('killswitch')!='1':raise Refused('KILLSWITCH-NOT-ENABLED')
        # Empty selectors only. A malformed/unknown selector is never treated as catch-all.
        constrained=any(s.get(k) not in (None,'',[]) for k in ('from_type','from','to_type','to','to_manual','to_list_external'))
        (special if constrained else generic).append((index,s))
    if len(generic)!=2:raise Refused('EXACTLY-TWO-GENERIC-RULES-REQUIRED')
    if generic[1][0]!=generic[0][0]+1:raise Refused('GENERIC-RULES-NOT-ADJACENT')
    if any(i>generic[0][0] for i,_ in special):raise Refused('SPECIAL-RULES-MUST-PRECEDE-GENERIC')
    pmap={p['id']:p for p in profiles}
    source=pmap.get(settings.get('plan_source')); target=pmap.get(settings.get('plan_target'))
    if not source or not target or source['id']==target['id']:raise Refused('SOURCE-RESERVE-NOT-CONFIGURED')
    if not source.get('interface') or not target.get('interface'):raise Refused('PROFILE-INACTIVE')
    byvia={s.get('via'):(i,s) for i,s in generic}
    if source['interface'] not in byvia or target['interface'] not in byvia:raise Refused('PROFILES-NOT-GENERIC-RULES')
    if source['interface']==target['interface']:raise Refused('SAME-INTERFACE')
    direction=settings.get('native_order_direction')
    if direction not in ('first','last'):raise Refused('POLICY-ORDER-DIRECTION-UNVERIFIED')
    return {'source':source,'target':target,'source_rule':byvia[source['interface']][1]['.name'],
            'target_rule':byvia[target['interface']][1]['.name'],
            'order':[s['.name'] for s in sections],'hash':policy_hash(sections),'direction':direction}


def trace(profile):
    result=probe(profile)
    if result.get('code') or not result.get('dns_ok') or result.get('https_success',0)<2:
        raise Refused('TARGET-HTTPS-DNS-FAILED')
    raw=bound_socket(result['device'],result['mark'])
    try:
        raw.connect(('1.1.1.1',443))
        with ssl.create_default_context().wrap_socket(raw,server_hostname='one.one.one.one') as sock:
            sock.sendall(b'GET /cdn-cgi/trace HTTP/1.1\r\nHost: one.one.one.one\r\nConnection: close\r\n\r\n')
            response=http.client.HTTPResponse(sock);response.begin();body=response.read(32769)
            if response.status!=200 or len(body)>32768:raise Refused('EXIT-TRACE-FAILED')
            rows=dict(line.split('=',1) for line in body.decode('ascii').splitlines() if '=' in line)
            value=str(ipaddress.IPv4Address(rows['ip']))
            if not ipaddress.ip_address(value).is_global:raise Refused('EXIT-IP-NOT-GLOBAL')
            return value
    finally:raw.close()


class Linux:
    def policy(self):return json.loads(command(['/usr/bin/lua',HELPER]))
    def candidates(self):
        data=self.policy();profiles={p.get('interface'):p for p in inventory()['profiles'] if p.get('interface')}
        values=[]
        for index,s in enumerate(data['sections']):
            constrained=any(s.get(k) not in (None,'',[]) for k in ('from_type','from','to_type','to','to_manual','to_list_external'))
            profile=profiles.get(s.get('via'))
            if s.get('.type')=='rule' and s.get('enabled')=='1' and s.get('killswitch')=='1' and not constrained and profile:
                values.append({'id':profile['id'],'order':index,'protocol':profile.get('protocol')})
        return values
    def acceleration(self):
        loaded=[m for m in ('mtkhnat','mtk_hnat','shortcut_fe','fast_classifier') if Path('/sys/module',m).exists()]
        after=time.monotonic()
        try:
            with Path('/sys/kernel/debug/hnat/hook_toggle').open() as stream:runtime=stream.read(257).strip()
        except OSError:runtime='unknown'
        hook_log=[]
        if runtime=='':
            try:
                kernel=command(['dmesg']).decode(errors='replace')
                runtime=fresh_hook_state(kernel,after)
                hook_log=[line[-200:] for line in kernel.splitlines() if 'hook' in line.lower() and ('hnat' in line.lower() or 'toggle' in line.lower())][-3:]
            except (OSError,ValueError,subprocess.SubprocessError):pass
        return {'loaded':loaded,'hnat_runtime':runtime if runtime in ('enabled','disabled') else 'unknown',
                'hnat_state_text':runtime[:256],
                'hook_log':hook_log,
                'debugfs_mounted':Path('/sys/kernel/debug').is_mount(),'hook_exists':Path('/sys/kernel/debug/hnat/hook_toggle').exists()}
    def diagnostic(self):
        blockers=[]
        try:
            board=json.loads(command(['ubus','call','system','board']))
            if board.get('board_name')!='glinet,gl-mt6000':blockers.append('UNSUPPORTED-BOARD')
            if Path('/etc/glversion').read_text().strip()!='4.11.0':blockers.append('UNSUPPORTED-FIRMWARE')
        except (OSError,ValueError,subprocess.SubprocessError):blockers.append('FIRMWARE-UNKNOWN')
        acceleration=self.acceleration()
        # Loaded is not the same as enabled. Require both vendor config and runtime proof.
        if any(m in acceleration['loaded'] for m in ('shortcut_fe','fast_classifier')):
            blockers.append('SOFTWARE-ACCELERATOR-UNVERIFIED')
        try:command(['nft','--version'])
        except (OSError,subprocess.SubprocessError):blockers.append('NFT-GUARD-UNAVAILABLE')
        try:
            expected=json.loads(Path(__file__).with_name('native-audit-hashes.json').read_text())
            for name,sha in expected.items():
                if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha:blockers.append('VENDOR-CODE-CHANGED')
        except (OSError,ValueError):blockers.append('VENDOR-CODE-UNVERIFIED')
        try:
            data=self.policy(); lan=data.get('lan')
            if any(m in acceleration['loaded'] for m in ('mtkhnat','mtk_hnat')) and (data.get('hnat_enable')!='0' or acceleration['hnat_runtime']!='disabled'):
                blockers.append('HARDWARE-ACCELERATOR-UNVERIFIED')
            if lan!='br-lan':blockers.append('LAN-LAYOUT-UNSUPPORTED')
            selection=choose(data,inventory()['profiles'])
        except (Refused,OSError,ValueError,subprocess.SubprocessError) as e:
            blockers.append(str(e) if isinstance(e,Refused) else 'POLICY-READ-FAILED');selection=None
        if list(Path('/var/run').glob('tunnel-switch*.lock')) or Path('/tmp/run/rtp2.lock').exists():blockers.append('VENDOR-WORKER-BUSY')
        return list(dict.fromkeys(blockers)),selection
    def order(self):
        data=self.policy();return [s['.name'] for s in data['sections']],policy_hash(data['sections'])
    def reorder(self,order):
        for index,section in enumerate(order):
            if not SAFE.fullmatch(section):raise Refused('UNSAFE-SECTION')
            command(['uci','reorder','route_policy.'+section+'='+str(index)])
        command(['uci','commit','route_policy'])
    def apply(self):command(['/usr/bin/rtp2.sh','not_reload_network'],timeout=45)
    def guard_exists(self):
        result=subprocess.run(['nft','list','table','inet',TABLE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        if result.returncode==0:
            if b'homensai-owned-guard' not in result.stdout:raise Refused('FOREIGN-GUARD-TABLE')
            return True
        if result.returncode!=1:raise Refused('GUARD-QUERY-FAILED')
        return False
    def guard(self,devices=None):
        exists=self.guard_exists()
        if devices is not None:
            if not devices or any(not SAFE.fullmatch(d) or len(d)>15 for d in devices):raise Refused('UNSAFE-GUARD-DEVICE')
            elements=', '.join('"'+d+'"' for d in sorted(set(devices)))
            rules='iifname "br-lan" meta nfproto ipv6 drop comment "homensai-owned-guard"; iifname "br-lan" oifname != { '+elements+' } drop comment "homensai-owned-guard";'
        else:rules='iifname "br-lan" drop comment "homensai-owned-guard";'
        # One nft transaction: never delete/recreate the table in separate invocations.
        script=('delete table inet '+TABLE+'; ' if exists else '')+'table inet '+TABLE+' { chain forward { type filter hook forward priority -310; policy accept; '+rules+' } }'
        result=subprocess.run(['nft','-f','-'],input=script.encode(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        if result.returncode or not self.guard_exists():raise Refused('GUARD-INSTALL-FAILED')
    def unguard(self):
        if self.guard_exists():command(['nft','delete','table','inet',TABLE])
    def devices(self):
        devices=[]
        for p in inventory()['profiles']:
            if not p.get('interface'):continue
            s=json.loads(command(['ubus','call','network.interface.'+p['interface'],'status']))
            if s.get('up') and s.get('l3_device'):devices.append(s['l3_device'])
        return devices
    def health(self,identifier):
        profile=next((p for p in inventory()['profiles'] if p['id']==identifier),None)
        if not profile or not profile.get('interface'):return False
        result=probe(profile)
        if result.get('code') is None and result.get('dns_ok') is True and result.get('https_success',0)>=2:return True
        if result.get('code') in ('VPN-001','VPN-003','DNS-001','PROFILE-INACTIVE'):return False
        return None


def rollback(backend,journal,reason):
    if journal.get('phase')=='ARMED' and not journal.get('pid') and backend.order()==(journal['before'],journal['hash']):
        journal.update(phase='ROLLED-BACK',reason=reason,finished=time.time());journal_write(journal);return
    backend.guard()
    order,fingerprint=backend.order()
    if fingerprint!=journal['hash'] or order not in (journal['before'],journal['after']):
        raise Refused('EXTERNAL-POLICY-CHANGE-GUARD-RETAINED')
    if order!=journal['before']:backend.reorder(journal['before'])
    backend.apply()
    order,fingerprint=backend.order()
    if order!=journal['before'] or fingerprint!=journal['hash']:
        raise Refused('ROLLBACK-UNVERIFIED-GUARD-RETAINED')
    journal.update(phase='ROLLED-BACK',reason=reason,finished=time.time())
    journal_write(journal)
    # Retain the VPN-only guard during the experiment. INPUT/LAN management is unaffected.
    backend.guard(backend.devices())


def finish_committed(backend,journal,reason):
    """A completed, client-confirmed switch must not expire back onto a failed source."""
    order,fingerprint=backend.order()
    if fingerprint!=journal['hash'] or order not in (journal['before'],journal['after']):
        backend.guard();raise Refused('EXTERNAL-POLICY-CHANGE-GUARD-RETAINED')
    if order==journal['after'] and backend.health(journal['source']) is not True:
        healthy=backend.health(journal['target']) is True
        backend.guard(backend.devices())
        journal.update(phase='HELD-ON-RESERVE',reason='SOURCE-NOT-VERIFIED',finished=time.time(),reserve_healthy=healthy)
        journal_write(journal)
        publish({'state':'STOPPED-ON-RESERVE','reason':'SOURCE-NOT-VERIFIED','source':journal['source'],
                 'target':journal['target'],'expected_exit':journal.get('expected_exit'),
                 'reserve_healthy':healthy,'original_restored':False,'trial':journal.get('trial',False)})
        return False
    journal.update(phase='RESTORING');journal_write(journal)
    rollback(backend,journal,reason)
    return True


def disable_acceleration(backend,request):
    """Explicit authenticated own-config request only; never runs on default install."""
    if not re.fullmatch(r'off-[a-f0-9]{32}',request):raise Refused('INVALID-ACCELERATION-REQUEST')
    saved=read_json(PREPARE,{})
    if saved.get('request')==request and saved.get('phase')=='DONE':return saved
    attempts=saved.get('attempts',0) if saved.get('request')==request else 0
    if attempts>=3:raise Refused('ACCELERATION-PREPARE-ATTEMPT-LIMIT')
    data=backend.policy()
    if not saved.get('before'):
        saved['before']={'hnat_enable':data.get('hnat_enable'),'acceleration':backend.acceleration(),
                         'firewall_defaults':[{k:s.get(k) for k in ('.name','flow_offloading','flow_offloading_hw')} for s in data.get('firewall_defaults',[])]}
    saved.update(request=request,phase='STARTED',time=time.time(),attempts=attempts+1);atomic_json(PREPARE,saved)
    def step(name):
        saved['step']=name;atomic_json(PREPARE,saved)
    step('vendor-config')
    if data.get('hnat_enable')!='0':
        command(['uci','set','mtkhnat.global.enable=0']);command(['uci','commit','mtkhnat'])
    changed=False
    for section in data.get('firewall_defaults',[]):
        if not SAFE.fullmatch(section.get('.name','')):raise Refused('UNSAFE-FIREWALL-SECTION')
        for key in ('flow_offloading','flow_offloading_hw'):
            if section.get(key)=='1':
                command(['uci','set','firewall.'+section['.name']+'.'+key+'=0']);changed=True
    if changed:command(['uci','commit','firewall']);command(['/etc/init.d/firewall','reload'],timeout=30)
    step('stop-shortcut-fe')
    if Path('/etc/init.d/shortcut-fe').exists():
        try:command(['/etc/init.d/shortcut-fe','stop'],timeout=20)
        except subprocess.CalledProcessError:pass  # Already stopped can return nonzero; kernel state is checked below.
    # Normal rmmod refuses modules with users/dependants. Never force or remove Ethernet/Wi-Fi drivers.
    for module in ('fast_classifier','shortcut_fe'):
        if module in backend.acceleration()['loaded']:
            step('unload-unused-'+module);command(['rmmod',module])
    step('reload-mtkhnat')
    if Path('/etc/init.d/mtkhnat').exists():
        try:command(['/etc/init.d/mtkhnat','reload'],timeout=20)
        except subprocess.CalledProcessError:pass
    step('read-runtime-hook')
    debug=Path('/sys/kernel/debug')
    if debug.is_symlink():raise Refused('UNEXPECTED-DEBUGFS-PATH')
    hook=debug/'hnat/hook_toggle'
    hook_verified=False
    if hook.exists():
        if hook.is_symlink():raise Refused('UNEXPECTED-HNAT-PATH')
        hook.write_text('0\n',encoding='ascii')
        hook_verified=backend.acceleration()['hnat_runtime']=='disabled'
    if not hook_verified and any(m in backend.acceleration()['loaded'] for m in ('mtkhnat','mtk_hnat')):
        step('stop-mtkhnat-service')
        if Path('/etc/init.d/mtkhnat').exists():
            try:command(['/etc/init.d/mtkhnat','stop'],timeout=20)
            except subprocess.CalledProcessError:pass
        for module in ('mtkhnat','mtk_hnat'):
            if module in backend.acceleration()['loaded']:
                step('unload-unused-'+module);command(['rmmod',module])
    acceleration=backend.acceleration()
    if any(m in acceleration['loaded'] for m in ('shortcut_fe','fast_classifier')):raise Refused('SFE-DISABLE-UNVERIFIED')
    if any(m in acceleration['loaded'] for m in ('mtkhnat','mtk_hnat')) and acceleration['hnat_runtime']!='disabled':raise Refused('HNAT-DISABLE-UNVERIFIED')
    saved.update(phase='DONE',after=acceleration,finished=time.time());atomic_json(PREPARE,saved)
    return saved


def child(tx):
    for _ in range(100):
        journal=journal_read()
        if journal.get('tx')==tx and journal.get('pid')==os.getpid() and journal.get('phase')=='APPLYING':break
        time.sleep(.1)
    else:raise Refused('WATCHDOG-DID-NOT-ARM')
    if time.time()>journal['deadline']:raise Refused('TRANSACTION-EXPIRED')
    backend=Linux(); blockers,_=backend.diagnostic()
    if blockers:raise Refused(blockers[0])
    if backend.order()!=(journal['before'],journal['hash']):raise Refused('POLICY-GENERATION-CHANGED')
    backend.guard()
    backend.reorder(journal['after'])
    backend.apply()


def attempt(backend,selection,until,trial):
    before=selection['order'];after=list(before)
    i=after.index(selection['source_rule']);j=after.index(selection['target_rule'])
    if (i>j and selection['direction']=='first') or (i<j and selection['direction']=='last'):
        raise Refused('SOURCE-ORDER-MISMATCH')
    if trial:
        baseline=backend.policy()['settings'].get('native_baseline_exit')
        if not baseline or trace(selection['source'])!=baseline:raise Refused('LAN-BASELINE-NOT-SOURCE')
        if trace(selection['target'])==baseline:raise Refused('RESERVE-EXIT-NOT-DISTINCT')
    after[i],after[j]=after[j],after[i]
    tx=uuid.uuid4().hex
    journal={'tx':tx,'phase':'ARMED','before':before,'after':after,'hash':selection['hash'],
             'source':selection['source']['id'],'target':selection['target']['id'],
             'deadline':min(until,time.time()+90),'trial':trial,'trial_nonce':backend.policy()['settings'].get('native_trial'),
             'pid':None,'started':time.time()}
    publish({'state':'ARMED','source':journal['source'],'target':journal['target'],'trial':trial})
    journal_write(journal)
    process=subprocess.Popen([sys.executable,__file__,'apply',tx],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    journal.update(pid=process.pid,phase='APPLYING')
    released=False
    try:
        publish({'state':'APPLYING','source':journal['source'],'target':journal['target'],'trial':trial})
        journal_write(journal);released=True
        process.wait(timeout=max(1,min(50,journal['deadline']-time.time())))
        if process.returncode:raise Refused('VENDOR-APPLY-FAILED')
        if backend.order()!=(after,selection['hash']):raise Refused('POLICY-CHANGED-DURING-APPLY')
        target_exit=trace(selection['target'])
        blockers,_=backend.diagnostic()
        if blockers:raise Refused(blockers[0])
        backend.guard(backend.devices())
        journal.update(phase='WAIT-CLIENT',expected_exit=target_exit);journal_write(journal)
        publish({'state':'WAIT-CLIENT','tx':tx,'expected_exit':target_exit,'deadline':journal['deadline'],
                          'requires':'LAN client DNS/HTTPS and exit IP confirmation; no confirmation means rollback'})
        while time.time()<journal['deadline'] and not STOP:
            stopped=read_json(PERSIST/'native-stop.json',{})
            if stopped.get('requested',0)>=journal['started']:raise Refused('CLIENT-STOP')
            confirmation=read_json(RUNTIME/'native-confirm.json',{})
            if (confirmation.get('tx')==tx and confirmation.get('exit_ipv4')==target_exit
                    and confirmation.get('dns_ok') is True and confirmation.get('https_ok') is True
                    and journal['started']<=confirmation.get('time',0)<=time.time()
                    and time.time()-confirmation.get('time',0)<=30):
                if backend.order()!=(after,selection['hash']):raise Refused('EXTERNAL-POLICY-CHANGE')
                if trace(selection['target'])!=target_exit:raise Refused('EXIT-CHANGED')
                blockers,_=backend.diagnostic()
                if blockers:raise Refused(blockers[0])
                if backend.order()!=(after,selection['hash']):raise Refused('EXTERNAL-POLICY-CHANGE')
                journal.update(phase='COMMITTED',confirmed=time.time());journal_write(journal)
                if trial and not finish_committed(backend,journal,'TRIAL-PASSED'):return
                atomic_json(CERT,{'hash':selection['hash'],'source':selection['source']['id'],
                                 'target':selection['target']['id'],'direction':selection['direction'],'time':time.time(),'until':until})
                publish({'state':'ARMED' if trial else 'COMMITTED','tx':tx,'source':journal['source'],'target':journal['target'],
                                  'until':until,'trial':trial,'reason':'TRIAL-PASSED' if trial else 'CLIENT-CONFIRMED','guard':'VPN-only; IPv6 forwarded traffic blocked'})
                return
            time.sleep(1)
        raise Refused('CLIENT-CONFIRMATION-TIMEOUT')
    except BaseException:
        # A failed shell may already have exited while its children still run.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()
        if not released and backend.order()==(before,selection['hash']):
            journal.update(phase='ROLLED-BACK',reason='FAILED-BEFORE-APPLY');journal_write(journal)
        else:rollback(backend,journal,'TRANSACTION-FAILED')
        publish({'state':'ROLLED-BACK','reason':'TRANSACTION-FAILED','source':journal['source'],'target':journal['target'],'trial':trial})
        raise


def serve():
    RUNTIME.mkdir(parents=True,exist_ok=True);PERSIST.mkdir(mode=0o700,parents=True,exist_ok=True)
    with open(RUNTIME/'native.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        backend=Linux()
        try:journal=journal_read()
        except Refused:
            backend.guard();publish({'state':'BLOCKED','blockers':['JOURNAL-INTEGRITY-FAILED'],'guard':'closed'});return
        # Supervisor is independently respawned by procd. Reboot/pending work always rolls back.
        if journal.get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):
            if journal.get('phase')=='APPLYING' and journal.get('pid'):
                # Kill only a process group whose command line proves this exact child identity.
                cmd=Path('/proc',str(journal['pid']),'cmdline')
                if cmd.exists() and ('native_switch.py\x00apply\x00'+journal['tx']) in cmd.read_bytes().decode(errors='replace'):
                    try:os.killpg(journal['pid'],signal.SIGKILL)
                    except ProcessLookupError:pass
            rollback(backend,journal,'SUPERVISOR-RECOVERY')
        elif journal.get('phase')=='COMMITTED':
            if backend.order()!=(journal['after'],journal['hash']):backend.guard();raise Refused('EXTERNAL-POLICY-CHANGE-GUARD-RETAINED')
            backend.guard(backend.devices())
        consumed=read_json(ATTEMPTS,{})
        last_trial=consumed.get('trial');last_attempt=consumed.get('time',0)
        while not STOP:
            try:
                data=backend.policy(); settings=data['settings'];until=deadline(settings.get('native_until'))
                active=journal_read()
                enabled=settings.get('native_enabled')=='1'
                stopped=read_json(PERSIST/'native-stop.json',{})
                stop_latched=bool(stopped and stopped.get('trial')==settings.get('native_trial'))
                if active.get('phase')=='HELD-ON-RESERVE' and (not enabled or stop_latched or settings.get('native_trial')==active.get('trial_nonce')):
                    if backend.order()!=(active['after'],active['hash']):backend.guard();raise Refused('EXTERNAL-POLICY-CHANGE-GUARD-RETAINED')
                    publish({'state':'STOPPED-ON-RESERVE','reason':'SOURCE-NOT-VERIFIED','source':active['source'],
                             'target':active['target'],'expected_exit':active.get('expected_exit'),'original_restored':False,
                             'reserve_healthy':active.get('reserve_healthy',False),'trial':active.get('trial',False)})
                    time.sleep(5);continue
                preparation=settings.get('native_prepare_acceleration') or ''
                if preparation:
                    if active.get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED'):raise Refused('ACCELERATION-PREPARE-DURING-TRANSACTION')
                    disable_acceleration(backend,preparation)
                if active.get('phase')=='COMMITTED' and (time.time()>=until or not enabled or stop_latched):
                    if not finish_committed(backend,active,'TRIAL-ENDED'):time.sleep(5);continue
                    publish({'state':'ROLLED-BACK','reason':'TRIAL-ENDED'})
                    active=journal_read()
                    last_trial=settings.get('native_trial')
                blockers,selection=backend.diagnostic()
                if stop_latched:
                    if active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'STOPPED','reason':'CLIENT-STOP','blockers':blockers,'candidates':backend.candidates()});time.sleep(5);continue
                if not enabled:
                    if active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'DISABLED','blockers':blockers,'acceleration':backend.acceleration(),'candidates':backend.candidates(),'adapter':'experimental-existing-rule-order'});time.sleep(5);continue
                if until>0 and time.time()>=until:
                    if active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'EXPIRED','reason':'TRIAL-ENDED'});time.sleep(5);continue
                if settings.get('native_session_loss')!='1':blockers.append('SESSION-LOSS-NOT-ACCEPTED')
                if not time.time()<until<=time.time()+14400:blockers.append('BOUNDED-DEADLINE-REQUIRED')
                if blockers:
                    if time.time()>=until and active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'BLOCKED','blockers':blockers});time.sleep(5);continue
                if active.get('phase')=='COMMITTED':
                    previous=read_json(STATE,{})
                    publish(dict(previous,state='COMMITTED',source=active['source'],target=active['target']))
                    time.sleep(5);continue
                trial=settings.get('native_trial') or ''
                forced=bool(trial and trial!=last_trial)
                if consumed.get('until')!=until:consumed={'until':until,'count':0,'trial':last_trial,'time':last_attempt}
                if consumed.get('count',0)>=3:
                    publish({'state':'BLOCKED','blockers':['TRIAL-ATTEMPT-LIMIT']});time.sleep(5);continue
                status=read_json(RUNTIME/'status.json',{})
                age=90
                failures=streak(status.get('samples',[]),selection['source']['id'],3,time.time(),age,False)
                healthy=streak(status.get('samples',[]),selection['target']['id'],2,time.time(),age,True)
                certificate=read_json(CERT,{})
                certified=certificate.get('hash')==selection['hash'] and certificate.get('source')==selection['source']['id'] and certificate.get('target')==selection['target']['id'] and certificate.get('direction')==selection['direction'] and certificate.get('until',0)>=until
                if time.time()-last_attempt>=180 and (forced or (certified and failures and healthy)):
                    last_attempt=time.time();last_trial=trial
                    consumed.update(trial=trial,time=last_attempt,count=consumed.get('count',0)+1)
                    atomic_json(ATTEMPTS,consumed)
                    attempt(backend,selection,until,forced)
                else:publish({'state':'OBSERVING' if certified else 'TRIAL-REQUIRED','certified':certified,'source_failures':failures,'reserve_healthy':healthy})
            except (Refused,OSError,ValueError,KeyError,subprocess.SubprocessError) as e:
                # Never log configuration, stderr, credentials or arbitrary exception values.
                reason=str(e) if isinstance(e,Refused) else 'NATIVE-SYSTEM-001'
                preparation=read_json(PREPARE,{})
                failure={'state':'BLOCKED','blockers':[reason],'error_type':type(e).__name__,'acceleration':backend.acceleration(),
                         'preparation':{k:preparation.get(k) for k in ('phase','step','attempts')}}
                try:publish(failure)
                except Refused:atomic_json(STATE,dict(failure,history_error='HISTORY-001'))
                pending=journal_read()
                if 'GUARD-RETAINED' in reason or pending.get('phase') in ('ARMED','APPLYING','WAIT-CLIENT'):return
            time.sleep(5)
        active=journal_read()
        if active.get('phase')=='COMMITTED':
            if finish_committed(backend,active,'SERVICE-STOPPED') and backend.order()==(active['before'],active['hash']):backend.unguard()


if __name__=='__main__':
    os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3'
    time.tzset()
    def stop(*_):
        global STOP
        STOP=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    if len(sys.argv)==3 and sys.argv[1]=='apply':child(sys.argv[2])
    elif len(sys.argv)==2 and sys.argv[1]=='daemon':serve()
    else:raise SystemExit('fixed daemon/apply actions only')
