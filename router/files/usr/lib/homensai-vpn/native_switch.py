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
import math
import os
from pathlib import Path
import re
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime

# The daemon/apply CLI and imported helpers must share exception classes,
# Stop and proof scope. A second module instance can turn a coded refusal into
# an uncaught daemon crash and make procd roll an otherwise owned session back.
if __name__=='__main__':
    sys.modules['native_switch']=sys.modules[__name__]

from agent import RUNTIME, PERSIST, TERMS_VERSION, atomic_json, read_json, command, inventory, probe, bound_socket,route_binding
from failover_plan import streak
from native_history import History, HistoryError
from probe_deadline import DeadlineSocket, HTTP_SECONDS, remaining

HELPER='/usr/lib/homensai-vpn/native_policy.lua'
TABLE='homensai_vpn_guard'
JOURNAL=PERSIST/'native-transaction.json'
STATE=RUNTIME/'native-status.json'
CERT=PERSIST/'native-certificate.json'
ATTEMPTS=PERSIST/'native-attempts.json'
PREPARE=PERSIST/'acceleration-prepare.json'
SAFE=re.compile(r'^[A-Za-z0-9_]{1,64}$')
STOP=False
PROOF_SCOPE='external-lan'


class Refused(Exception):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def bind_policy_context(backend,record):
    setter=getattr(backend,'use_process_bindings',None)
    if callable(setter):setter(record.get('process_bindings'))


def publish(value):
    value=dict(value,time=time.time())
    # This is observation-only: missing/corrupt evidence cannot affect Stop or routing.
    value.pop('latency',None)
    from native_history import capture_transition_latency,transition_destination
    role,identifier=transition_destination(value)
    if identifier:
        try:
            journal=journal_read()
            if journal.get('source')==value.get('source') and journal.get('target')==value.get('target'):
                latency=capture_transition_latency(value,read_json(RUNTIME/'status.json',{}),(journal.get('vendor_profiles') or {}).get(role),value['time'])
                if latency is not None:value['latency']=latency
        except (Refused,OSError,ValueError,TypeError,KeyError,OverflowError):pass
    from auto_control import action_context,manual_action_source
    value.update(action_context(RUNTIME,PERSIST,value['time']))
    if value.get('manual') is True or value.get('reason') in ('OPERATOR-MANUAL','OPERATOR-RETURN'):
        if 'transition_source' not in value:value['transition_source']=manual_action_source(RUNTIME,value,value['time'])
    elif value.get('trial') is True or value.get('reason') in ('OPERATOR-TRIAL','TRIAL-PASSED'):value.setdefault('transition_source','test')
    elif value.get('reason') in ('SOURCE-FAILED','PRIMARY-STABLY-RECOVERED','RESERVE-FAILED-PRIMARY-VERIFIED'):
        from fault_control import testing_profile
        tested=value.get('source') if value.get('reason')=='SOURCE-FAILED' else value.get('target')
        value.setdefault('transition_source','test' if tested and testing_profile(tested) else 'automatic')
    value.setdefault('proof_scope',PROOF_SCOPE)
    if value['proof_scope']=='router-probed-ipv4':
        value.setdefault('mode','continuous-pair')
        value['external_lan_verified']=False
    try:History(PERSIST).record(value)
    except (OSError,ValueError,KeyError,TypeError):
        atomic_json(STATE,{'state':'BLOCKED','blockers':['HISTORY-001']})
        raise Refused('HISTORY-001')
    atomic_json(STATE,value)


RETURN_CHECKS=6
# Owner decision (18 Oct 2026): a full LAN block for an unreadable journal happens once; a rollback that failed twice is not retried.
ROLLBACK_FAILURE_LIMIT=2
JOURNAL_ALARM=PERSIST/'native-journal-alarm.json'
RETURN_PAUSE=10
GUARD_RELEASE_SECONDS=90


def return_request_path():return RUNTIME/'native-return.json'
def return_result_path():return RUNTIME/'native-return-result.json'


def progress_read(path,kind):
    """Missing progress is initial state; corrupt progress never resets a budget.

    This is not the recovery journal. Refuse new work while still allowing the
    trusted journal's recovery, Stop, expiry and an explicit Return to proceed.
    """
    missing=object()
    try:record=read_json(path,missing)
    except (OSError,ValueError):raise Refused('NATIVE-PROGRESS-UNVERIFIED') from None
    if record is missing:return {}
    def stamp(value):
        try:return type(value) in (int,float) and math.isfinite(value) and value>=0
        except OverflowError:return False
    valid=isinstance(record,dict)
    if valid and kind=='attempts':
        trial=record.get('trial')
        valid=({'until','count','trial','time'}<=set(record)
            and type(record['count']) is int and 0<=record['count']<=3
            and stamp(record['until']) and stamp(record['time'])
            and (trial is None and record['count']==0 or isinstance(trial,str)
                 and re.fullmatch(r'[A-Za-z0-9_:.\-]{1,96}',trial) is not None))
    elif valid and kind=='return':
        valid=({'request','ok','code','time'}<=set(record)
            and stamp(record['request']) and record['request']>0 and stamp(record['time'])
            and type(record['ok']) is bool and isinstance(record['code'],str)
            and re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}',record['code']) is not None)
    else:valid=False
    if not valid:raise Refused('NATIVE-PROGRESS-UNVERIFIED')
    return record


def clear_native_options():
    """Close the test window in the own config; skipped when unrelated changes are pending."""
    try:
        pending=subprocess.run(['uci','-q','changes','homensai_vpn'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        if pending.returncode or pending.stdout.strip():return False
        batch=b"set homensai_vpn.main.native_enabled='0'\nset homensai_vpn.main.native_until='0'\nset homensai_vpn.main.native_trial=''\ncommit homensai_vpn\n"
        return subprocess.run(['uci','-q','batch'],input=batch,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10).returncode==0
    except (OSError,subprocess.SubprocessError):return False


def stop_latch(trial):
    """Terminal recovery stops every trial until a later explicit Start.

    Use the UI lock too: otherwise its atomic writer and the supervisor can
    truncate/rename the same .pending file concurrently.
    """
    from auto_control import control_lock, revision_locked
    with control_lock(RUNTIME):
        revision_error=None
        try:revision_locked(RUNTIME,rotate=True)
        except (OSError,ValueError) as error:revision_error=error
        try:old=read_json(PERSIST/'native-stop.json',{})
        except (OSError,ValueError):old={}
        previous=old.get('requested',0) if isinstance(old,dict) else 0
        now=time.time()
        if type(previous) in (int,float) and math.isfinite(previous):now=max(now,previous)
        record={'requested':now,'trial':trial,'all_trials':True}
        if revision_error is not None:record['control_revision_failed']=True
        atomic_json(PERSIST/'native-stop.json',record)
        if revision_error is not None:raise revision_error


def abandon(backend,journal,code):
    """The router policy was changed by someone else: stop, release our traffic guard, never hold the LAN."""
    try:backend.unguard()
    except (Refused,OSError,subprocess.SubprocessError):
        # Preserve recovery work across restart; never publish released/STOPPED
        # when removal of our guard has not been confirmed.
        journal.update(phase='RELEASE-PENDING',reason=code,abandoned=True)
        journal_write(journal)
        stop_latch(journal.get('trial_nonce'))
        clear_native_options()
        publish({'state':'BLOCKED','reason':'GUARD-RELEASE-UNCONFIRMED',
                 'blockers':['GUARD-RELEASE-UNCONFIRMED'],'guard':'unverified',
                 'original_restored':False,'source':journal.get('source'),'target':journal.get('target')})
        raise Refused('GUARD-RELEASE-UNCONFIRMED') from None
    journal.update(phase='ROLLED-BACK',reason=code,abandoned=True,finished=time.time())
    try:journal_write(journal)
    except (OSError,ValueError):pass
    try:stop_latch(journal.get('trial_nonce'))
    except (OSError,ValueError):pass
    clear_native_options()
    try:publish({'state':'STOPPED','reason':code,'original_restored':False,'source':journal.get('source'),'target':journal.get('target'),'trial':journal.get('trial',False)})
    except Refused:pass


def note_phase(value,phase):
    rows=value.get('phase_evidence',[])
    rows=rows if isinstance(rows,list) else []
    rows=[r for r in rows[-31:] if isinstance(r,dict) and set(r)=={'phase','time'} and isinstance(r['phase'],str) and re.fullmatch(r'[A-Z0-9_-]{1,96}',r['phase']) and type(r['time']) in (int,float) and math.isfinite(r['time'])]
    if not rows or rows[-1]['phase']!=phase:rows.append({'phase':phase,'time':time.time()})
    value['phase_evidence']=rows


def journal_write(value):
    if isinstance(value.get('phase'),str) and re.fullmatch(r'[A-Z0-9_-]{1,96}',value['phase']):note_phase(value,value['phase'])
    atomic_json(JOURNAL,{'schema':1,'data':value,'sha256':digest(value)})


def journal_read():
    # A truncated or non-JSON journal is an integrity failure with a code, never an uncaught error.
    missing=object()
    try:
        if JOURNAL.is_symlink() or JOURNAL.exists() and (not JOURNAL.is_file() or JOURNAL.stat().st_size>1024*1024):
            raise Refused('JOURNAL-INTEGRITY-FAILED')
        envelope=read_json(JOURNAL,missing)
    except (ValueError,UnicodeDecodeError,OSError):raise Refused('JOURNAL-INTEGRITY-FAILED') from None
    if envelope is missing:return {}
    if not isinstance(envelope,dict):raise Refused('JOURNAL-INTEGRITY-FAILED')
    value=envelope.get('data')
    if type(envelope.get('schema')) is not int or envelope['schema']!=1 or not isinstance(value,dict) or envelope.get('sha256')!=digest(value):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    before=value.get('before',[]);after=value.get('after',[])
    if (not isinstance(before,list) or not isinstance(after,list) or not 2<=len(before)<=400
            or len(before)!=len(after)):
        raise Refused('JOURNAL-ORDER-INVALID')
    if any(not isinstance(s,str) or not SAFE.fullmatch(s) for s in before+after):raise Refused('JOURNAL-SECTION-INVALID')
    if len(before)!=len(set(before)) or len(after)!=len(set(after)) or set(before)!=set(after):
        raise Refused('JOURNAL-ORDER-INVALID')
    if value.get('phase') not in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING','ROLLED-BACK','RELEASE-PENDING'):
        raise Refused('JOURNAL-PHASE-INVALID')
    from native_proof import matches
    if not matches(value,value):raise Refused('JOURNAL-INTEGRITY-FAILED')
    from process_policy import validate
    try:validate(value.get('process_bindings'))
    except ValueError:raise Refused('JOURNAL-INTEGRITY-FAILED') from None
    if not isinstance(value.get('hash'),str) or not re.fullmatch(r'[a-f0-9]{64}',value['hash']):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'vendor_identity' in value and (not isinstance(value['vendor_identity'],str) or not re.fullmatch(r'[a-f0-9]{64}',value['vendor_identity'])):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'control_revision' in value and (not isinstance(value['control_revision'],str) or not re.fullmatch(r'[a-f0-9]{32}',value['control_revision'])):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'vendor_profiles' in value:
        from failure_diagnosis import profile_identity
        proofs=value['vendor_profiles']
        if (not isinstance(proofs,dict) or set(proofs)!={'source','target'}
                or any(not isinstance(proofs[role],dict) or profile_identity(proofs[role])!=proofs[role]
                       or proofs[role].get('id')!=value.get(role) for role in ('source','target'))):
            raise Refused('JOURNAL-INTEGRITY-FAILED')
    for name in ('started','deadline','monotonic_deadline','lease_monotonic_until','confirmed','finished'):
        if name=='monotonic_deadline' and value.get(name) is None:continue  # legacy bounded journals
        if name in value and (type(value[name]) not in (int,float) or not math.isfinite(value[name]) or value[name]<0):
            raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'pid' in value and value['pid'] is not None and (type(value['pid']) is not int or value['pid']<=1):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'rollback_failures' in value and (type(value['rollback_failures']) is not int or not 0<=value['rollback_failures']<=ROLLBACK_FAILURE_LIMIT):
        raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'trial' in value and type(value['trial']) is not bool:raise Refused('JOURNAL-INTEGRITY-FAILED')
    if 'manual_request_id' in value and (not isinstance(value['manual_request_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',value['manual_request_id'])):raise Refused('JOURNAL-INTEGRITY-FAILED')
    if value['phase'] not in ('ROLLED-BACK','RELEASE-PENDING'):
        for name in ('tx','source','target','trial_nonce'):
            if not isinstance(value.get(name),str) or not re.fullmatch(r'[A-Za-z0-9_:.\-]{1,96}',value[name]):
                raise Refused('JOURNAL-INTEGRITY-FAILED')
        if value['source']==value['target'] or any(name not in value for name in ('started','deadline')):
            raise Refused('JOURNAL-INTEGRITY-FAILED')
        if value['deadline']<value['started']:raise Refused('JOURNAL-INTEGRITY-FAILED')
    return value


def deadline(value):
    if value is None or value=='':return 0
    if type(value) not in (int,float,str):raise Refused('BOUNDED-DEADLINE-REQUIRED')
    try:result=float(value)
    except (ValueError,OverflowError):
        if not isinstance(value,str):raise Refused('BOUNDED-DEADLINE-REQUIRED') from None
        try:
            normal=re.sub(r'(\.\d{6})\d+(?=[+-]\d{2}:\d{2}$)',r'\1',value.replace('Z','+00:00'))
            parsed=datetime.fromisoformat(normal)
            if parsed.tzinfo is None:raise Refused('DEADLINE-TIMEZONE-REQUIRED')
            result=parsed.timestamp()
        except (ValueError,OverflowError,OSError):raise Refused('BOUNDED-DEADLINE-REQUIRED') from None
    if not math.isfinite(result) or result<0:raise Refused('BOUNDED-DEADLINE-REQUIRED')
    return result


def fresh_hook_state(lines,after):
    """Some vendor debugfs reads print status to the kernel ring, returning no bytes."""
    for line in reversed(lines.splitlines()):
        match=re.match(r'^\[\s*(\d+(?:\.\d+)?)\]\s*(.*)$',line)
        if not match or float(match[1])<after:continue
        message=match[2].lower()
        if 'going to' in message:continue  # An action request is not proof of resulting state.
        actual=re.fullmatch(r'value=([01]), hook is (disabled|enabled) now!',message)
        if actual and actual[2]==('disabled' if actual[1]=='0' else 'enabled'):
            return actual[2]
        match=re.fullmatch(r'(?:hnat[ _]*)?hook(?:_toggle)?\s*(?:(?:is|state|status|currently|:|=)\s*)*(enabled|disabled)[ !.]*',message)
        if match:return match[1]
    return 'unknown'


def appended_hook_state(before,after):
    if not before:return 'unknown'
    marker=before.splitlines()[-1]
    lines=after.splitlines()
    if lines.count(marker)!=1:return 'unknown'
    return fresh_hook_state('\n'.join(lines[lines.index(marker)+1:]),0)


def semantic_section(section,process_bindings=None):
    anonymous=section.get('.anonymous') in (True,'1')
    from process_policy import recognizes
    derived=recognizes(section,process_bindings)
    return {k:v for k,v in section.items() if k!='.index' and not (anonymous and k=='.name')
            and not (derived and k in ('via','mark'))}


def section_id(section):
    return 'a_'+digest(semantic_section(section))[:60] if section.get('.anonymous') in (True,'1') else section['.name']


def policy_order(sections):
    values=[section_id(s) for s in sections]
    if len(values)!=len(set(values)):raise Refused('POLICY-DUPLICATE-IDENTITY')
    return values


def policy_hash(sections,process_bindings=None):
    policy_order(sections)
    from process_policy import validate
    bindings=validate(process_bindings)
    value=sorted([semantic_section(s,bindings) for s in sections],key=digest)
    return digest(value if bindings is None else {'sections':value,'process_bindings':bindings})


def choose(data,profiles):
    """Fail closed on policy layouts outside the explicitly supported small subset."""
    sections=data['sections']; settings=data['settings']
    from native_proof import requested
    try:proof_scope=requested(settings)
    except ValueError as error:raise Refused(str(error)) from None
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
    if not 2<=len(generic)<=16:raise Refused('TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED')
    if [index for index,_ in generic]!=list(range(generic[0][0],generic[-1][0]+1)):raise Refused('GENERIC-RULES-NOT-ADJACENT')
    if len({row.get('via') for _,row in generic})!=len(generic):raise Refused('GENERIC-DUPLICATE-INTERFACE')
    if any(i>generic[0][0] for i,_ in special):raise Refused('SPECIAL-RULES-MUST-PRECEDE-GENERIC')
    from failure_diagnosis import tunnel_identity,TUNNEL
    pmap={p['id']:p for p in profiles}
    if len(pmap)!=len(profiles):raise Refused('VENDOR-IDENTITY-UNKNOWN')
    selected=[]
    for role in ('source','target'):
        anchor=settings.get('plan_'+role+'_tunnel')
        if anchor in (None,''):profile=pmap.get(settings.get('plan_'+role))
        else:
            if not isinstance(anchor,str) or not TUNNEL.fullmatch(anchor):raise Refused('VENDOR-IDENTITY-UNKNOWN')
            matches=[p for p in profiles if tunnel_identity(p)==anchor]
            if len(matches)!=1:raise Refused('VENDOR-IDENTITY-UNKNOWN')
            profile=matches[0]
        selected.append(profile)
    source,target=selected
    if not source or not target or source['id']==target['id']:raise Refused('SOURCE-RESERVE-NOT-CONFIGURED')
    if not source.get('interface') or not target.get('interface'):raise Refused('PROFILE-INACTIVE')
    source_tunnel=tunnel_identity(source);target_tunnel=tunnel_identity(target)
    if not source_tunnel or not target_tunnel:raise Refused('VENDOR-IDENTITY-UNKNOWN')
    if source_tunnel==target_tunnel:raise Refused('VENDOR-SAME-TUNNEL')
    byvia={s.get('via'):(i,s) for i,s in generic}
    if source['interface'] not in byvia or target['interface'] not in byvia:raise Refused('PROFILES-NOT-GENERIC-RULES')
    if source['interface']==target['interface']:raise Refused('SAME-INTERFACE')
    direction=settings.get('native_order_direction')
    if direction not in ('first','last'):raise Refused('POLICY-ORDER-DIRECTION-UNVERIFIED')
    from process_policy import selected_bindings
    try:process_bindings=selected_bindings(sections,(source['interface'],target['interface']))
    except ValueError as error:raise Refused(str(error)) from None
    from failure_diagnosis import profile_identity
    identities={role:profile_identity(row) for role,row in (('source',source),('target',target))}
    return {'source':source,'target':target,'source_rule':section_id(byvia[source['interface']][1]),
            'target_rule':section_id(byvia[target['interface']][1]),
            'order':policy_order(sections),'hash':policy_hash(sections,process_bindings),'direction':direction,
            'process_bindings':process_bindings,
            'proof_scope':proof_scope,
            'vendor_identity':digest(identities) if all(identities.values()) else None}


def trace(profile):
    result=probe(profile)
    if result.get('code') or not result.get('dns_ok') or result.get('https_success',0)<2:
        raise Refused('TARGET-HTTPS-DNS-FAILED')
    raw=bound_socket(result['device'],result['mark'])
    end=time.monotonic()+HTTP_SECONDS
    try:
        raw.settimeout(remaining(end))
        raw.connect(('1.1.1.1',443))
        raw.settimeout(remaining(end))
        with ssl.create_default_context().wrap_socket(raw,server_hostname='one.one.one.one') as sock:
            sock.settimeout(remaining(end))
            sock.sendall(b'GET /cdn-cgi/trace HTTP/1.1\r\nHost: one.one.one.one\r\nConnection: close\r\n\r\n')
            # A cut, garbled or non-IPv4 reply is a coded refusal, never an uncaught error that ends the supervisor.
            try:
                response=http.client.HTTPResponse(DeadlineSocket(sock,end));response.begin();body=response.read(32769)
                remaining(end)
                if response.status!=200 or len(body)>32768:raise Refused('EXIT-TRACE-FAILED')
                rows=dict(line.split('=',1) for line in body.decode('ascii').splitlines() if '=' in line)
                value=str(ipaddress.IPv4Address(rows['ip'].strip()))
            except (http.client.HTTPException,KeyError,ValueError):raise Refused('EXIT-TRACE-FAILED') from None
            if not ipaddress.ip_address(value).is_global:raise Refused('EXIT-IP-NOT-GLOBAL')
            return value
    finally:raw.close()


class Linux:
    def __init__(self):self.process_bindings=None
    def use_process_bindings(self,bindings):
        from process_policy import validate
        try:self.process_bindings=validate(bindings)
        except ValueError:raise Refused('POLICY-IDENTITY-CHANGED') from None
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
        try:kernel_before=command(['dmesg']).decode(errors='replace')
        except (OSError,ValueError,subprocess.SubprocessError):kernel_before=None
        try:
            with Path('/sys/kernel/debug/hnat/hook_toggle').open() as stream:runtime=stream.read(257).strip()
        except OSError:runtime='unknown'
        hook_log=[]
        if runtime=='':
            try:
                kernel=command(['dmesg']).decode(errors='replace')
                # printk and Python monotonic clocks differ on this vendor kernel.
                # Accept only text appended by this read, never an older ring entry.
                runtime=appended_hook_state(kernel_before,kernel)
                hook_log=[line[-200:] for line in kernel.splitlines() if 'hook' in line.lower() and ('hnat' in line.lower() or 'toggle' in line.lower())][-3:]
            except (OSError,ValueError,subprocess.SubprocessError):pass
        return {'loaded':loaded,'hnat_runtime':runtime if runtime in ('enabled','disabled') else 'unknown',
                'hnat_state_text':runtime[:256],
                'hook_log':hook_log,
                'debugfs_mounted':Path('/sys/kernel/debug').is_mount(),'hook_exists':Path('/sys/kernel/debug/hnat/hook_toggle').exists()}
    def diagnostic(self):
        blockers=[];board={}
        from preparation_control import auto_blocker
        preparation_reason=auto_blocker()
        if preparation_reason:blockers.append(preparation_reason)
        try:
            board=json.loads(command(['ubus','call','system','board']))
            if board.get('board_name')not in('glinet,gl-mt6000','glinet,mt3000-snand'):blockers.append('UNSUPPORTED-BOARD')
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
            from native_platform import assess
            blockers.extend(assess(board,data))
            from device_profile import detect, validate
            try:validate(data.get('settings',{}).get('router_model','auto'), detect())
            except ValueError as error:blockers.append(str(error))
            mode=data.get('settings',{}).get('monitor_only')
            if mode not in (None,'0'):
                blockers.append('MONITOR-ONLY-DEPLOYMENT' if mode=='1' else 'MONITOR-ONLY-INVALID')
            if data.get('settings',{}).get('terms_version')!=TERMS_VERSION:blockers.append('TERMS-NOT-ACCEPTED')
            if any(m in acceleration['loaded'] for m in ('mtkhnat','mtk_hnat')) and (data.get('hnat_enable')!='0' or acceleration['hnat_runtime']!='disabled'):
                blockers.append('HARDWARE-ACCELERATOR-UNVERIFIED')
            if lan!='br-lan':blockers.append('LAN-LAYOUT-UNSUPPORTED')
            metadata=inventory();selection=choose(data,metadata['profiles'])
            if board.get('board_name')=='glinet,mt3000-snand':
                from pair_interfaces import selection as selected_interfaces
                try:selected_interfaces(selection)
                except ValueError:blockers.append('EXISTING-TUNNEL-BINDING-UNVERIFIED')
            self.use_process_bindings(selection.get('process_bindings'))
            from failure_diagnosis import resolve_pair,profile_identity
            interval=data.get('settings',{}).get('interval','10')
            try:interval=int(interval)
            except (ValueError,TypeError,OverflowError):raise Refused('OBSERVATION-STALE')
            observed=read_json(RUNTIME/'status.json',{})
            pair=resolve_pair(observed,data.get('settings',{}),time.time(),max(30,min(900,interval*3)),max(30,min(600,interval*2)))
            if pair['coordination']['state']!='READY':raise Refused(pair['coordination']['code'])
            for role in ('source','target'):
                current=selection[role];measured=pair[role]
                if any(current.get(key)!=measured.get(key) for key in ('id','protocol','interface','vendor_tunnel_id')):
                    raise Refused('PROFILE-IDENTITY-CHANGED')
                selection[role]=dict(current,**{key:measured.get(key) for key in ('vendor_generation','vendor_state','vendor_changed_at')})
                live=route_binding(current['interface'])
                if (live.get('code') is not None and not (role=='source' and live.get('code')=='VPN-001' and measured.get('code')=='VPN-001')
                        or any(live.get(key)!=measured.get(key) for key in ('device','mark','table','ifindex'))):
                    raise Refused('PROFILE-IDENTITY-CHANGED')
                selection[role]['kernel_binding']={key:live.get(key) for key in ('code','device','mark','table','ifindex')}
            selection['vendor_identity']=digest({role:{'profile':profile_identity(selection[role]),
                'kernel':selection[role]['kernel_binding']} for role in ('source','target')})
            selection['coordination']=pair['coordination']
            from recovery_settings import fingerprint
            selection['settings_hash']=fingerprint(data.get('settings',{}))
            groups={s.get('profile'):s.get('channel','default') for s in metadata.get('servers',[])}
            for profile in (selection['source'],selection['target']):profile['channel']=groups.get(profile['id'],profile.get('group_id','default'))
            disabled={s.get('profile') for s in metadata.get('servers',[]) if s.get('enabled') is False}
            if selection['source']['id'] in disabled or selection['target']['id'] in disabled:blockers.append('PROFILE-NOT-MONITORED')
        except (Refused,OSError,ValueError,subprocess.SubprocessError) as e:
            blockers.append(str(e) if isinstance(e,Refused) else 'POLICY-READ-FAILED');selection=None
        if list(Path('/var/run').glob('tunnel-switch*.lock')) or Path('/tmp/run/rtp2.lock').exists():blockers.append('VENDOR-WORKER-BUSY')
        return list(dict.fromkeys(blockers)),selection
    def order(self):
        data=self.policy();return policy_order(data['sections']),policy_hash(data['sections'],self.process_bindings)
    def reorder(self,order,before_write=None,write_command=None):
        sections=self.policy()['sections']
        current=policy_order(sections)
        if len(order)!=len(current) or set(order)!=set(current):raise Refused('POLICY-IDENTITY-CHANGED')
        fingerprint=policy_hash(sections,self.process_bindings)
        for index,identifier in enumerate(order):
            live=self.policy()['sections']
            if policy_hash(live,self.process_bindings)!=fingerprint:raise Refused('POLICY-IDENTITY-CHANGED')
            names={section_id(s):s['.name'] for s in live}
            section=names[identifier]
            if not SAFE.fullmatch(section):raise Refused('UNSAFE-SECTION')
            if before_write:before_write()
            (write_command or command)(['uci','reorder','route_policy.'+section+'='+str(index)])
        if before_write:before_write()
        (write_command or command)(['uci','commit','route_policy'])
        if self.order()!=(order,fingerprint):raise Refused('POLICY-REORDER-UNVERIFIED')
    def apply(self,write_command=None):
        from process_policy import synchronization_script
        with tempfile.TemporaryDirectory(prefix='homensai-process-')as stage:
            try:script=synchronization_script(self.policy()['sections'],self.process_bindings,stage)
            except ValueError:raise Refused('POLICY-IDENTITY-CHANGED')from None
            if script is not None:
                # One UCI transaction; the same Stop/revision fence used for
                # rule ordering protects this already-modelled derived state.
                (write_command or command)(['lua','-e',script],timeout=8)
        (write_command or command)(['/usr/bin/rtp2.sh','not_reload_network'],timeout=45)
        from device_profile import detect
        if detect()=='mt3000':
            from native_platform import wait_quiet
            try:wait_quiet()
            except (OSError,ValueError) as error:raise Refused(str(error)if str(error)in('VENDOR-WORKER-BUSY','VENDOR-WORKER-QUIET-UNVERIFIED')else'VENDOR-WORKER-QUIET-UNVERIFIED') from None
        from process_policy import applied
        try:verified=applied(self.policy()['sections'],self.process_bindings)
        except (ValueError,KeyError,TypeError):verified=False
        if not verified:raise Refused('POLICY-IDENTITY-CHANGED')
    def guard_exists(self):
        result=subprocess.run(['nft','list','table','inet',TABLE],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        if result.returncode==0:
            if b'homensai-owned-guard' not in result.stdout:raise Refused('FOREIGN-GUARD-TABLE')
            return True
        if result.returncode!=1:raise Refused('GUARD-QUERY-FAILED')
        return False
    def guard(self,devices=None,control_revision=None):
        exists=self.guard_exists()
        if devices is not None:
            if not devices or any(not SAFE.fullmatch(d) or len(d)>15 for d in devices):raise Refused('UNSAFE-GUARD-DEVICE')
            elements=', '.join('"'+d+'"' for d in sorted(set(devices)))
            rules='iifname "br-lan" meta nfproto ipv6 drop comment "homensai-owned-guard"; iifname "br-lan" oifname != { '+elements+' } drop comment "homensai-owned-guard";'
        else:
            generation=uuid.uuid4().hex[:8]
            # The kernel expires the match even if both Python and the cleanup
            # process die. No unbounded full-block rule is ever installed.
            rules='iifname @blocked_lan_'+generation+' drop comment "homensai-owned-guard-'+generation+'";'
        # One nft transaction: never delete/recreate the table in separate invocations.
        # Vendor nft opens /dev/stdin for '-', but that node is absent here.
        fd,path=tempfile.mkstemp(prefix='guard-',suffix='.nft',dir=str(RUNTIME))
        try:
            with os.fdopen(fd,'w') as stream:
                if exists:stream.write('delete table inet '+TABLE+';\n')
                stream.write('table inet '+TABLE+' {\n')
                if devices is None:
                    stream.write('  set blocked_lan_%s { type ifname; flags timeout; timeout %ds; elements = { "br-lan" timeout %ds }; }\n' % (generation,GUARD_RELEASE_SECONDS,GUARD_RELEASE_SECONDS))
                stream.write('  chain forward {\n    type filter hook forward priority -310; policy accept;\n')
                for rule in rules.split(';'):
                    if rule.strip():stream.write('    '+rule.strip()+';\n')
                stream.write('  }\n}\n')
            checked=subprocess.run(['nft','-c','-f',path],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            if checked.returncode:raise Refused('GUARD-CHECK-FAILED')
            if devices is None:self.schedule_release(generation)
            if control_revision is None:
                result=subprocess.run(['nft','-f',path],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            else:
                forward_dispatch(['nft','-f',path],control_revision,timeout=5)
                result=subprocess.CompletedProcess(['nft','-f',path],0)
        finally:os.unlink(path)
        if result.returncode or not self.guard_exists():raise Refused('GUARD-INSTALL-FAILED')
    def schedule_release(self,generation):
        """Release only this generation's element; never delete a later replacement table."""
        # A read/check followed by table deletion races with guard replacement.
        # Unique set identity makes this single nft mutation harmless after any
        # replacement. The kernel timeout still works if this process is lost.
        script=('sleep %d; nft delete element inet %s blocked_lan_%s \'{ "br-lan" }\' 2>/dev/null || :'
                %(GUARD_RELEASE_SECONDS,TABLE,generation))
        try:subprocess.Popen(['sh','-c',script],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        except OSError:raise Refused('GUARD-RELEASE-ARM-FAILED') from None
    def unguard(self):
        if self.guard_exists():command(['nft','delete','table','inet',TABLE])
        if self.guard_exists():raise Refused('GUARD-RELEASE-UNCONFIRMED')
    def devices(self):
        devices=[]
        for p in inventory()['profiles']:
            if not p.get('interface') or p.get('administrative_state')=='disabled':continue
            try:
                s=json.loads(command(['ubus','call','network.interface.'+p['interface'],'status']))
                if not isinstance(s,dict):raise ValueError('status')
            except (OSError,ValueError,subprocess.SubprocessError):
                raise Refused('GUARD-DEVICE-UNVERIFIED') from None
            if s.get('up') and s.get('l3_device'):devices.append(s['l3_device'])
        return devices
    def recovery_ready(self,identifier,settings):
        from recovery_settings import normalized,stable_success
        from failure_diagnosis import resolve_pair,scoped_samples
        policy=normalized(settings)
        status=read_json(RUNTIME/'status.json',{})
        interval=int(settings.get('interval',10))
        pair=resolve_pair(status,settings,time.time(),max(30,min(900,interval*3)),max(30,min(600,interval*2)))
        row=next((pair[role] for role in ('source','target') if pair[role] and pair[role]['id']==identifier),None)
        return (pair['coordination']['state']=='READY' and row is not None
                and stable_success(scoped_samples(status.get('samples',[]),row),identifier,policy['primary_successes'],policy['primary_stable'],time.time(),max(30,min(900,interval*3)))
                and self.health(identifier) is True)
    def health(self,identifier):
        profile=next((p for p in inventory()['profiles'] if p['id']==identifier),None)
        if not profile or not profile.get('interface'):return False
        result=probe(profile)
        if result.get('code') is None and result.get('dns_ok') is True and result.get('https_success',0)>=2:return True
        if result.get('code') in ('VPN-001','VPN-003','DNS-001','PROFILE-INACTIVE'):return False
        return None


def rollback(backend,journal,reason):
    bind_policy_context(backend,journal)
    note_phase(journal,'RESTORING')
    if journal.get('phase')=='ARMED' and not journal.get('pid') and backend.order()==(journal['before'],journal['hash']):
        journal.update(phase='ROLLED-BACK',reason=reason,finished=time.time());journal_write(journal);return
    backend.guard()
    order,fingerprint=backend.order()
    if fingerprint!=journal['hash'] or order not in (journal['before'],journal['after']):
        abandon(backend,journal,'EXTERNAL-POLICY-CHANGE')
        raise Refused('EXTERNAL-POLICY-CHANGE-RELEASED')
    if order!=journal['before']:backend.reorder(journal['before'])
    backend.apply()
    order,fingerprint=backend.order()
    if order!=journal['before'] or fingerprint!=journal['hash']:
        # Never keep LAN traffic closed: fall back to the VPN-only guard and report the unverified state.
        try:backend.guard(backend.devices())
        except (Refused,OSError,subprocess.SubprocessError):pass
        raise Refused('ROLLBACK-UNVERIFIED')
    journal.update(phase='ROLLED-BACK',reason=reason,finished=time.time())
    journal_write(journal)
    # Retain the VPN-only guard during the experiment. INPUT/LAN management is unaffected.
    backend.guard(backend.devices())


def rollback_counted(backend,journal,reason):
    """rollback() that remembers each failure in the journal, so repeated failures end in give_up() instead of a loop."""
    try:return rollback(backend,journal,reason)
    except Exception:
        journal['rollback_failures']=int(journal.get('rollback_failures',0) or 0)+1
        try:journal_write(journal)
        except (OSError,ValueError):pass
        raise


def give_up(backend,journal,code):
    """No more automatic recovery: VPN-only guard (no full block), Auto stopped and not restartable by itself, alarm published."""
    guard='VPN-only; IPv6 forwarded traffic blocked'
    try:backend.guard(backend.devices())
    except (Refused,OSError,ValueError,subprocess.SubprocessError):guard='VPN-only guard could not be confirmed'
    # The stop latch must name the trial that is configured now (the journal may be empty or unreadable), otherwise it would not hold.
    try:trial=backend.policy().get('settings',{}).get('native_trial')
    except (Refused,OSError,ValueError,KeyError,AttributeError,TypeError,subprocess.SubprocessError):trial=None
    trial=trial or journal.get('trial_nonce')
    try:stop_latch(trial)
    except (OSError,ValueError):pass
    blockers=[code]
    if not clear_native_options():blockers.append('AUTO-OPTIONS-NOT-CLEARED')
    state={'state':'BLOCKED','blockers':blockers,'alarm':code,'original_restored':False,'source':journal.get('source'),'target':journal.get('target'),'guard':guard}
    while True:
        try:publish(state)
        except Refused:atomic_json(STATE,dict(state,history_error='HISTORY-001',time=time.time()))
        if STOP:return
        # An operator who restored the rules and closed the journal ends the alarm; the supervisor then restarts normally.
        try:
            if not journal_read():return
        except Refused:pass
        time.sleep(10)


def source_ready(backend,journal,settings,reason):
    """A passed trial returns on a fresh bound check (with retries); later returns need stable history."""
    if reason!='TRIAL-PASSED':
        return backend.recovery_ready(journal['source'],settings) is True
    for index in range(RETURN_CHECKS):
        if backend.health(journal['source']) is True:return True
        if index+1<RETURN_CHECKS:time.sleep(RETURN_PAUSE)
    return False


def operator_return(backend,journal,reason='OPERATOR-RETURN',control_revision=None):
    """Leave a held or committed reserve and restore the original order; needs the source freshly healthy."""
    if journal.get('phase') not in ('HELD-ON-RESERVE','COMMITTED'):return 'RETURN-NOT-APPLICABLE'
    if backend.health(journal['source']) is not True:return 'SOURCE-NOT-HEALTHY'
    if control_revision is not None:require_control_revision(control_revision)
    rollback(backend,journal,reason)
    return None


def handle_return(backend,journal,request,last_time,control_revision=None):
    """Answer each operator return request exactly once with a public result. Returns (handled,last_time)."""
    stamp=request.get('time') if isinstance(request,dict) else None
    if type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<=0:return False,last_time
    if stamp==last_time:return False,last_time
    now=time.time()
    # A rejected future request must not suppress a later real request. Keep
    # equality deduplication, but distrust a watermark ahead of the clock.
    if type(last_time) not in (int,float) or not math.isfinite(last_time) or not 0<=last_time<=now:last_time=0
    if stamp<=last_time:return False,last_time
    if (not isinstance(request.get('tx'),str) or not request['tx']
            or request['tx']!=journal.get('tx')):code='RETURN-TRANSACTION-MISMATCH'
    elif not journal.get('started',0)<=stamp<=now or now-stamp>60:code='RETURN-REQUEST-EXPIRED'
    else:
        try:code=operator_return(backend,journal,control_revision=control_revision)
        except Refused as error:code=str(error)
    if code is None:
        try:backend.unguard()
        except (Refused,OSError,subprocess.SubprocessError):code='GUARD-RELEASE-UNCONFIRMED'
        if code is None:
            clear_native_options()
            try:publish({'state':'STOPPED','reason':'OPERATOR-RETURN','original_restored':True,'source':journal.get('source'),'target':journal.get('target'),'trial':journal.get('trial',False)})
            except Refused:pass
    atomic_json(return_result_path(),{'request':stamp,'ok':code is None,'code':code or 'RETURNED','time':time.time()})
    return True,stamp


def finish_committed(backend,journal,reason):
    bind_policy_context(backend,journal)
    """A completed, client-confirmed switch must not expire back onto a failed source."""
    order,fingerprint=backend.order()
    if fingerprint!=journal['hash'] or order not in (journal['before'],journal['after']):
        abandon(backend,journal,'EXTERNAL-POLICY-CHANGE')
        raise Refused('EXTERNAL-POLICY-CHANGE-RELEASED')
    from recovery_settings import normalized
    settings=backend.policy().get('settings',{})
    recovery=normalized(settings)
    if order==journal['after'] and (recovery['return_policy']=='hold_reserve' or not source_ready(backend,journal,settings,reason)):
        healthy=backend.health(journal['target']) is True
        backend.guard(backend.devices())
        journal.update(phase='HELD-ON-RESERVE',reason='OPERATOR-HOLD-RESERVE' if recovery['return_policy']=='hold_reserve' else 'SOURCE-NOT-VERIFIED',finished=time.time(),reserve_healthy=healthy)
        journal_write(journal)
        publish({'state':'STOPPED-ON-RESERVE','reason':journal['reason'],'source':journal['source'],
                 'target':journal['target'],'expected_exit':journal.get('expected_exit'),
                 'reserve_healthy':healthy,'original_restored':False,'trial':journal.get('trial',False)})
        return False
    journal.update(phase='RESTORING');journal_write(journal)
    rollback(backend,journal,reason)
    return True


def committed_recovery_decision(backend,journal,settings,samples,now,status=None):
    """Observe a confirmed reserve without inventing permission for another hop.

    Returning to the certified original route requires stable primary samples
    plus recovery_ready's fresh bound DNS/HTTPS check. A reserve failure is
    never hidden behind the historical COMMITTED status.
    """
    from recovery_settings import normalized
    from failure_diagnosis import resolve_pair,profile_identity
    recovery=normalized(settings)
    age=max(30,min(900,int(settings.get('interval',10))*3))
    selection_settings=dict(settings)
    for role in ('source','target'):
        if not selection_settings.get('plan_'+role):selection_settings['plan_'+role]=journal[role]
    pair=resolve_pair(status,selection_settings,now,age,max(30,min(600,int(settings.get('interval',10))*2)))
    proofs=journal.get('vendor_profiles',{})
    target=pair['target'];expected=proofs.get('target') if isinstance(proofs,dict) else None
    if (pair['coordination']['state']!='READY' or target is None or target['id']!=journal['target']
            or expected is not None and profile_identity(target)!=expected):
        return {'action':'HOLD','reason':'RESERVE-IDENTITY-UNKNOWN','reserve_healthy':None}
    failed=streak(samples,target['id'],recovery['failures'],now,age,False,target)
    from fault_control import testing_profile
    fault_test=failed and testing_profile(journal['target'])
    if recovery['return_policy']=='healthy_primary' or fault_test:
        dwell=now-journal.get('confirmed',journal.get('started',now))
        if (failed or dwell>=recovery['min_dwell']) and backend.recovery_ready(journal['source'],settings) is True:
            return {'action':'RESTORE-PRIMARY','reason':'RESERVE-FAILED-PRIMARY-VERIFIED' if failed else 'PRIMARY-STABLY-RECOVERED'}
    if failed:
        # A fresh negative check avoids acting on stale monitor failure history.
        health=backend.health(journal['target'])
        if health is False:return {'action':'HOLD','reason':'RESERVE-FAILED','reserve_healthy':False}
        if health is None:return {'action':'HOLD','reason':'RESERVE-HEALTH-UNKNOWN','reserve_healthy':None}
    return {'action':'OBSERVE','reason':'CLIENT-CONFIRMED'}


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
    if transaction_expired(journal):raise Refused('TRANSACTION-EXPIRED')
    require_control_revision(journal.get('control_revision'))
    backend=Linux();blockers,selection=backend.diagnostic()
    if blockers:raise Refused(blockers[0])
    if not selection or selection.get('vendor_identity')!=journal.get('vendor_identity') or not journal.get('vendor_identity'):
        raise Refused('PROFILE-IDENTITY-CHANGED')
    if selection.get('process_bindings')!=journal.get('process_bindings'):raise Refused('POLICY-IDENTITY-CHANGED')
    bind_policy_context(backend,journal)
    if backend.order()!=(journal['before'],journal['hash']):raise Refused('POLICY-GENERATION-CHANGED')
    require_control_revision(journal.get('control_revision'))
    backend.guard(control_revision=journal['control_revision'])
    def before_write():
        require_control_revision(journal.get('control_revision'))
        assert_selection(backend,selection)
        require_control_revision(journal.get('control_revision'))
        if transaction_expired(journal):raise Refused('TRANSACTION-EXPIRED')
    def write_command(args,timeout=5):
        before_write()
        return forward_dispatch(args,journal['control_revision'],timeout)
    backend.reorder(journal['after'],write_command=write_command)
    backend.apply(write_command=write_command)


def transition_kind(source,target):
    source_protocol=source.get('protocol') or source['id'].split(':',1)[0]
    target_protocol=target.get('protocol') or target['id'].split(':',1)[0]
    if source_protocol!=target_protocol:return 'protocol'
    if source.get('vendor_tunnel_id')!=target.get('vendor_tunnel_id'):return 'channel'
    return 'server'


def assert_selection(backend,selection):
    """Fresh configured binding/epoch proof immediately before a forward write.

    Recovery rollback deliberately does not use this gate: it must remain
    possible after a vendor change invalidates the forward-action evidence.
    """
    blockers,current=backend.diagnostic()
    if blockers:raise Refused(blockers[0])
    identity=selection.get('vendor_identity')
    if (not isinstance(identity,str) or not re.fullmatch(r'[a-f0-9]{64}',identity)
            or not current or current.get('vendor_identity')!=identity
            or current.get('proof_scope','external-lan')!=selection.get('proof_scope','external-lan')
            or current.get('hash')!=selection.get('hash')
            or any(current[role]['id']!=selection[role]['id'] for role in ('source','target'))):
        raise Refused('PROFILE-IDENTITY-CHANGED')
    return current


def require_control_revision(expected):
    """Stop rotates this RAM marker even when its flash latch is deduplicated."""
    if not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{32}',expected):raise Refused('CLIENT-STOP')
    try:record=read_json(RUNTIME/'auto-control-revision.json',{})
    except (OSError,ValueError):raise Refused('CLIENT-STOP') from None
    if not isinstance(record,dict) or set(record)!={'revision'} or record['revision']!=expected:
        raise Refused('CLIENT-STOP')


def forward_dispatch(args,control_revision,timeout=5):
    """Fence dispatch against Stop; never wait on a command under the UI lock.

    An already dispatched vendor command can remain in flight after Stop.
    Inherit the owning apply child's process group for its existing cleanup.
    """
    from auto_control import control_lock
    with control_lock(RUNTIME):
        require_control_revision(control_revision)
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:output,_=process.communicate(timeout=timeout)
    except BaseException:
        try:process.kill()
        except ProcessLookupError:pass
        # A vendor grandchild can retain stdout after its parent is killed.
        # The enclosing apply group owns descendant cleanup; never wait here
        # without a bound and prevent a delayed pipe EOF from blocking Stop.
        try:process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            if process.stdout:process.stdout.close()
            if process.stderr:process.stderr.close()
        raise
    if process.returncode:raise subprocess.CalledProcessError(process.returncode,args)
    if len(output)>2*1024*1024:raise Refused('NATIVE-SYSTEM-001')
    return output


def monotonic_lease(settings,until,wall=None,mono=None):
    """Freeze the elapsed-time lease on first observation; NTP cannot extend it."""
    wall=time.time() if wall is None else wall
    mono=time.monotonic() if mono is None else mono
    trial=settings.get('native_trial')
    if not isinstance(trial,str) or not trial or not wall<until<=wall+14400:
        return 0,'BOUNDED-DEADLINE-REQUIRED'
    identity=digest({'trial':trial,'until':until})
    path=RUNTIME/'native-lease.json'
    missing=object()
    try:record=read_json(path,missing)
    except (OSError,ValueError):return 0,'LEASE-INTEGRITY-FAILED'
    if record is not missing:
        if not isinstance(record,dict):return 0,'LEASE-INTEGRITY-FAILED'
        data=record.get('data')
        if not isinstance(data,dict) or record.get('sha256')!=digest(data):return 0,'LEASE-INTEGRITY-FAILED'
        end=data.get('monotonic_until');start=data.get('monotonic_start')
        if (not isinstance(data.get('identity'),str) or not re.fullmatch(r'[a-f0-9]{64}',data['identity'])
                or type(end) not in (int,float) or type(start) not in (int,float)
                or not math.isfinite(end) or not math.isfinite(start)
                or not 0<=start<=mono or not start<=end<=start+14400):
            return 0,'LEASE-INTEGRITY-FAILED'
        if data.get('identity')==identity:
            return end,None
    data={'identity':identity,'monotonic_start':mono,'monotonic_until':mono+until-wall}
    try:atomic_json(path,{'data':data,'sha256':digest(data)})
    except (OSError,ValueError):return 0,'LEASE-STORAGE-FAILED'
    return data['monotonic_until'],None


def transaction_expired(journal,wall=None,mono=None):
    wall=time.time() if wall is None else wall
    mono=time.monotonic() if mono is None else mono
    return wall>=journal['deadline'] or (journal.get('monotonic_deadline') is not None and mono>=journal['monotonic_deadline'])


def attempt(backend,selection,until,trial,probe_evidence=None,control_revision=None,manual_request_id=None,request_source=None):
    global PROOF_SCOPE
    PROOF_SCOPE=selection.get('proof_scope','external-lan')
    if manual_request_id is not None and (trial or not isinstance(manual_request_id,str) or not re.fullmatch(r'[a-f0-9]{32}',manual_request_id)):
        raise Refused('MANUAL-REQUEST-INVALID')
    if control_revision is None:
        from auto_control import current_revision
        control_revision=current_revision(RUNTIME)
    bind_policy_context(backend,selection)
    require_control_revision(control_revision)
    assert_selection(backend,selection)
    from auto_control import normalize_request_source
    def publish_transition(value):
        value=dict(value,transition_source=normalize_request_source(request_source) if manual_request_id is not None else 'test' if trial else 'automatic')
        publish(value)
    cause='OPERATOR-TRIAL' if trial else 'SOURCE-FAILED' if probe_evidence and probe_evidence.get('source_streak_met') is True else 'SOURCE-HEALTH-UNKNOWN'
    if manual_request_id is not None:cause='OPERATOR-MANUAL'

    before=selection['order'];after=list(before)
    i=after.index(selection['source_rule']);j=after.index(selection['target_rule'])
    if (i>j and selection['direction']=='first') or (i<j and selection['direction']=='last'):
        raise Refused('SOURCE-ORDER-MISMATCH')
    if trial:
        require_control_revision(control_revision)
        baseline=backend.policy()['settings'].get('native_baseline_exit')
        if not baseline or trace(selection['source'])!=baseline:raise Refused('LAN-BASELINE-NOT-SOURCE')
        require_control_revision(control_revision)
        if trace(selection['target'])==baseline:raise Refused('RESERVE-EXIT-NOT-DISTINCT')
        require_control_revision(control_revision)
    assert_selection(backend,selection)
    require_control_revision(control_revision)
    after[i],after[j]=after[j],after[i]
    tx=uuid.uuid4().hex
    wall=time.time();mono=time.monotonic()
    lease_end,lease_error=monotonic_lease(backend.policy()['settings'],until,wall,mono)
    if lease_error:raise Refused(lease_error)
    journal={'tx':tx,'phase':'ARMED','before':before,'after':after,'hash':selection['hash'],
             'source':selection['source']['id'],'target':selection['target']['id'],
             'deadline':min(until,wall+90),'monotonic_deadline':min(lease_end,mono+90),'lease_monotonic_until':lease_end,'trial':trial,'trial_nonce':backend.policy()['settings'].get('native_trial'),
             'pid':None,'started':time.time(),'vendor_identity':selection['vendor_identity'],
             'process_bindings':selection.get('process_bindings'),
             'proof_scope':PROOF_SCOPE,
             'control_revision':control_revision,
             'vendor_profiles':{role:{key:selection[role].get(key) for key in ('id','protocol','interface','vendor_tunnel_id','vendor_generation')} for role in ('source','target')}}
    if manual_request_id is not None:journal['manual_request_id']=manual_request_id
    publish_transition({'state':'ARMED','source':journal['source'],'target':journal['target'],'trial':trial,'reason':cause,'phase_evidence':journal.get('phase_evidence',[]),'probe_evidence':probe_evidence,'transition_kind':transition_kind(selection['source'],selection['target'])})
    require_control_revision(control_revision)
    journal_write(journal)
    require_control_revision(control_revision)
    from auto_control import control_lock
    with control_lock(RUNTIME):
        require_control_revision(control_revision)
        process=subprocess.Popen([sys.executable,__file__,'apply',tx],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    journal.update(pid=process.pid,phase='APPLYING')
    released=False
    try:
        publish_transition({'state':'APPLYING','source':journal['source'],'target':journal['target'],'trial':trial,'reason':cause,'phase_evidence':journal.get('phase_evidence',[]),'probe_evidence':probe_evidence,'transition_kind':transition_kind(selection['source'],selection['target'])})
        journal_write(journal);released=True
        process.wait(timeout=max(1,min(50,journal['monotonic_deadline']-time.monotonic())))
        if process.returncode:
            result=read_json(RUNTIME/'native-apply-result.json',{})
            code=result.get('code')if isinstance(result,dict)and result.get('tx')==tx else None
            raise Refused(code if isinstance(code,str)and re.fullmatch('[A-Z][A-Z0-9_-]{0,95}',code)else'VENDOR-APPLY-FAILED')
        if backend.order()!=(after,selection['hash']):raise Refused('POLICY-CHANGED-DURING-APPLY')
        target_exit=trace(selection['target'])
        assert_selection(backend,selection)
        require_control_revision(control_revision)
        backend.guard(backend.devices(),control_revision=control_revision)
        journal.update(phase='WAIT-CLIENT',expected_exit=target_exit);journal_write(journal)
        publish_transition({'state':'WAIT-CLIENT','tx':tx,'expected_exit':target_exit,'deadline':journal['deadline'],'source':journal['source'],'target':journal['target'],'trial':trial,'phase_evidence':journal.get('phase_evidence',[]),
                          'requires':'LAN client DNS/HTTPS and exit IP confirmation; no confirmation means rollback'})
        while not transaction_expired(journal) and not STOP:
            require_control_revision(control_revision)
            stopped=read_json(PERSIST/'native-stop.json',{})
            if stopped.get('requested',0)>=journal['started']:raise Refused('CLIENT-STOP')
            confirmation=read_json(RUNTIME/'native-confirm.json',{})
            if PROOF_SCOPE=='router-probed-ipv4':
                # Explicit router-only mode: these are bound tunnel probes,
                # never an external-LAN or hosted-forwarding acknowledgement.
                measured=probe(selection['target'])
                require_control_revision(control_revision)
                if (measured.get('code') is None and measured.get('dns_ok') is True
                        and measured.get('https_success',0)>=2 and trace(selection['target'])==target_exit):
                    confirmation={'tx':tx,'exit_ipv4':target_exit,'dns_ok':True,'https_ok':True,
                                  'time':time.time(),'proof_scope':PROOF_SCOPE}
            from native_proof import matches
            if (confirmation.get('tx')==tx and confirmation.get('exit_ipv4')==target_exit
                    and matches(confirmation,journal)
                    and confirmation.get('dns_ok') is True and confirmation.get('https_ok') is True
                    and journal['started']<=confirmation.get('time',0)<=time.time()
                    and time.time()-confirmation.get('time',0)<=30):
                if backend.order()!=(after,selection['hash']):raise Refused('EXTERNAL-POLICY-CHANGE')
                if trace(selection['target'])!=target_exit:raise Refused('EXIT-CHANGED')
                assert_selection(backend,selection)
                require_control_revision(control_revision)
                if backend.order()!=(after,selection['hash']):raise Refused('EXTERNAL-POLICY-CHANGE')
                require_control_revision(control_revision)
                journal.update(phase='COMMITTED',confirmed=time.time());journal_write(journal)
                if manual_request_id is not None:
                    with control_lock(RUNTIME):
                        require_control_revision(control_revision)
                        journal.update(phase='HELD-ON-RESERVE',reason='OPERATOR-MANUAL',reserve_healthy=True);journal_write(journal)
                    publish_transition({'state':'STOPPED-ON-RESERVE','reason':'OPERATOR-MANUAL','source':journal['source'],'target':journal['target'],
                             'original_restored':False,'reserve_healthy':True,'trial':False,'tx':tx})
                    return
                if trial and not finish_committed(backend,journal,'TRIAL-PASSED'):return
                require_control_revision(control_revision)
                atomic_json(CERT,{'hash':selection['hash'],'source':selection['source']['id'],
                                 'target':selection['target']['id'],'direction':selection['direction'],'settings_hash':selection.get('settings_hash'),
                                 'vendor_identity':selection['vendor_identity'],'proof_scope':PROOF_SCOPE,'time':time.time(),'until':until})
                publish_transition({'state':'ARMED' if trial else 'COMMITTED','tx':tx,'source':journal['source'],'target':journal['target'],
                                  'until':until,'trial':trial,'phase_evidence':journal.get('phase_evidence',[]),'transition_kind':transition_kind(selection['source'],selection['target']),'reason':'TRIAL-PASSED' if trial else 'CLIENT-CONFIRMED','guard':'VPN-only; IPv6 forwarded traffic blocked'})
                return
            time.sleep(1)
        raise Refused('CLIENT-CONFIRMATION-TIMEOUT')
    except BaseException as error:
        failure_code=str(error) if isinstance(error,Refused) and re.fullmatch(r'[A-Z0-9_-]{1,96}',str(error)) else 'NATIVE-SYSTEM-001'
        # A failed shell may already have exited while its children still run.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()
        if not released and backend.order()==(before,selection['hash']):
            journal.update(phase='ROLLED-BACK',reason='FAILED-BEFORE-APPLY');journal_write(journal)
        else:rollback_counted(backend,journal,'TRANSACTION-FAILED')
        publish_transition({'state':'ROLLED-BACK','reason':'TRANSACTION-FAILED','source':journal['source'],'target':journal['target'],'trial':trial,'phase_evidence':journal.get('phase_evidence',[]),'blockers':[failure_code]})
        raise


def serve():
    global PROOF_SCOPE
    RUNTIME.mkdir(parents=True,exist_ok=True);PERSIST.mkdir(mode=0o700,parents=True,exist_ok=True)
    with open(RUNTIME/'native.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        from auto_control import current_revision
        revision_error=False
        try:current_revision(runtime=RUNTIME,rotate=True)
        except (OSError,ValueError):revision_error=True
        backend=Linux()
        try:journal=journal_read()
        except Refused:
            # Block the LAN once (timed release); on every later start only the VPN-only guard is used, never another full block.
            missing_alarm=object()
            try:first=read_json(JOURNAL_ALARM,missing_alarm) is missing_alarm
            except (OSError,ValueError):first=False  # an unreadable marker means we already blocked once
            if first:
                try:backend.guard()
                except (Refused,OSError,ValueError,subprocess.SubprocessError):pass
                try:atomic_json(JOURNAL_ALARM,{'first_block':time.time(),'code':'JOURNAL-INTEGRITY-FAILED'})
                except (OSError,ValueError):pass
            give_up(backend,{},'JOURNAL-INTEGRITY-FAILED');return
        try:JOURNAL_ALARM.unlink()
        except OSError:pass
        bind_policy_context(backend,journal)
        PROOF_SCOPE=journal.get('proof_scope','external-lan')
        if PROOF_SCOPE not in('external-lan','router-hosted-ipv4','router-probed-ipv4'):raise Refused('JOURNAL-INTEGRITY-FAILED')
        if journal.get('phase')=='RELEASE-PENDING':
            abandon(backend,journal,journal.get('reason','EXTERNAL-POLICY-CHANGE'))
        # Supervisor is independently respawned by procd. Reboot/pending work always rolls back.
        if journal.get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):
            if journal.get('phase')=='APPLYING' and journal.get('pid'):
                # Kill only a process group whose command line proves this exact child identity.
                cmd=Path('/proc',str(journal['pid']),'cmdline')
                if cmd.exists() and ('native_switch.py\x00apply\x00'+journal['tx']) in cmd.read_bytes().decode(errors='replace'):
                    try:os.killpg(journal['pid'],signal.SIGKILL)
                    except ProcessLookupError:pass
            if int(journal.get('rollback_failures',0) or 0)>=ROLLBACK_FAILURE_LIMIT:
                give_up(backend,journal,'ROLLBACK-GIVEN-UP');return
            try:rollback_counted(backend,journal,'SUPERVISOR-RECOVERY')
            except (Refused,OSError,ValueError,subprocess.SubprocessError):
                if int(journal.get('rollback_failures',0) or 0)>=ROLLBACK_FAILURE_LIMIT:
                    give_up(backend,journal,'ROLLBACK-GIVEN-UP');return
                raise
        elif journal.get('phase')=='COMMITTED':
            if backend.order()!=(journal['after'],journal['hash']):abandon(backend,journal,'EXTERNAL-POLICY-CHANGE')
            else:
                backend.guard(backend.devices())
                if journal.get('manual_request_id') and journal.get('confirmed'):
                    journal.update(phase='HELD-ON-RESERVE',reason='OPERATOR-MANUAL');journal_write(journal)
        from manual_dispatch import recover_pending
        recover_pending(backend,runtime=RUNTIME,persist=PERSIST)
        from pair_auto import recover as pair_recover
        pair_recover(backend)
        if revision_error:
            # A UI freshness marker failure alone does not authorize a traffic
            # guard on a monitor-only installation. Preserve the durable stop
            # while leaving network state to the journal recovery above.
            try:stop_latch(journal.get('trial_nonce'))
            except (OSError,ValueError):pass
            publish({'state':'BLOCKED','blockers':['CONTROL-REVISION-STALE'],
                     'alarm':'CONTROL-REVISION-STALE','original_restored':False})
            return
        last_return=0;consumed={};last_trial=None;last_attempt=0
        while not STOP:
            try:
                from speed_pause import gate as speed_gate
                if speed_gate('auto'):
                    time.sleep(1);continue
                from auto_control import current_revision
                decision_revision=current_revision(RUNTIME)
                progress_error=None
                try:
                    returned=progress_read(return_result_path(),'return')
                    attempts=progress_read(ATTEMPTS,'attempts')
                except Refused:progress_error='NATIVE-PROGRESS-UNVERIFIED'
                else:
                    last_return=returned.get('request',0);consumed=attempts
                    last_trial=consumed.get('trial');last_attempt=consumed.get('time',0)
                data=backend.policy(); settings=data['settings']
                from pair_auto import tick as pair_tick
                if pair_tick(backend,settings,decision_revision):
                    time.sleep(2);continue
                until=deadline(settings.get('native_until'))
                from native_proof import requested,matches
                try:PROOF_SCOPE=requested(settings)
                except ValueError:raise Refused('LAN-TRIAL-REQUIRED') from None
                active=journal_read()
                if active.get('phase')=='RELEASE-PENDING':
                    abandon(backend,active,active.get('reason','EXTERNAL-POLICY-CHANGE'))
                    time.sleep(2);continue
                enabled=settings.get('native_enabled')=='1'
                stopped=read_json(PERSIST/'native-stop.json',{})
                from auto_control import effective_intent
                enabled,stop_latched=effective_intent(settings,stopped,read_json(RUNTIME/'auto-control.json',{}),time.time())
                from manual_dispatch import consume as consume_manual
                if consume_manual(backend,settings,decision_revision,stopped,runtime=RUNTIME,persist=PERSIST):
                    time.sleep(1);continue
                lease_error=None;lease_end=0
                if enabled or active.get('phase')=='COMMITTED':lease_end,lease_error=monotonic_lease(settings,until)
                if active.get('phase')=='COMMITTED':
                    if not active.get('lease_monotonic_until'):lease_error='LEGACY-LEASE-RECOVERY'
                    else:lease_end=min(lease_end,active['lease_monotonic_until'])
                lease_expired=time.time()>=until or (lease_end>0 and time.monotonic()>=lease_end) or (active.get('phase')=='COMMITTED' and lease_error is not None)
                request=read_json(return_request_path(),{})
                if request:
                    handled,last_return=handle_return(backend,active,request,last_return)
                    if handled:time.sleep(2);continue
                if active.get('phase')=='HELD-ON-RESERVE' and (not enabled or stop_latched or settings.get('native_trial')==active.get('trial_nonce')):
                    if backend.order()!=(active['after'],active['hash']):
                        abandon(backend,active,'EXTERNAL-POLICY-CHANGE');time.sleep(5);continue
                    from recovery_settings import normalized as recovery_normalized
                    if not active.get('manual_request_id') and recovery_normalized(settings)['return_policy']=='healthy_primary' and backend.recovery_ready(active['source'],settings) is True:
                        if operator_return(backend,active,'PRIMARY-RECOVERED') is None:
                            publish({'state':'ROLLED-BACK','reason':'PRIMARY-RECOVERED','source':active['source'],'target':active['target'],'original_restored':True,'trial':active.get('trial',False)})
                            time.sleep(2);continue
                    publish({'state':'STOPPED-ON-RESERVE','reason':active.get('reason','SOURCE-NOT-VERIFIED'),'source':active['source'],
                             'target':active['target'],'expected_exit':active.get('expected_exit'),'original_restored':False,
                             'reserve_healthy':active.get('reserve_healthy',False),'trial':active.get('trial',False)})
                    time.sleep(5);continue
                preparation=settings.get('native_prepare_acceleration') or ''
                if preparation:
                    if active.get('phase') in ('ARMED','APPLYING','WAIT-CLIENT','COMMITTED'):raise Refused('ACCELERATION-PREPARE-DURING-TRANSACTION')
                    disable_acceleration(backend,preparation)
                if active.get('phase')=='COMMITTED' and (lease_expired or not enabled or stop_latched):
                    if not finish_committed(backend,active,'TRIAL-ENDED'):time.sleep(5);continue
                    publish({'state':'ROLLED-BACK','reason':'TRIAL-ENDED'})
                    active=journal_read()
                    last_trial=settings.get('native_trial')
                blockers,selection=backend.diagnostic()
                if stop_latched:
                    if progress_error:blockers.append(progress_error)
                    if active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'STOPPED','reason':'CLIENT-STOP','original_restored':active.get('phase')=='ROLLED-BACK' and backend.order()==(active.get('before'),active.get('hash')),'blockers':blockers,'candidates':backend.candidates()});time.sleep(5);continue
                if not enabled:
                    if progress_error:blockers.append(progress_error)
                    if active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'DISABLED','original_restored':active.get('phase')=='ROLLED-BACK' and backend.order()==(active.get('before'),active.get('hash')),'blockers':blockers,'acceleration':backend.acceleration(),'candidates':backend.candidates(),'adapter':'experimental-existing-rule-order'});time.sleep(5);continue
                if until>0 and lease_expired:
                    if active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    clear_native_options()
                    publish({'state':'EXPIRED','reason':'TRIAL-ENDED'});time.sleep(5);continue
                if lease_error:blockers.append(lease_error)
                if settings.get('native_session_loss')!='1':blockers.append('SESSION-LOSS-NOT-ACCEPTED')
                if not time.time()<until<=time.time()+14400:blockers.append('BOUNDED-DEADLINE-REQUIRED')
                if blockers:
                    if time.time()>=until and active.get('phase')=='ROLLED-BACK' and backend.order()==(active['before'],active['hash']):backend.unguard()
                    publish({'state':'BLOCKED','blockers':blockers});time.sleep(5);continue
                if active.get('phase')=='COMMITTED':
                    status=read_json(RUNTIME/'status.json',{})
                    decision=committed_recovery_decision(backend,active,settings,status.get('samples',[]),time.time(),status)
                    if decision['action']=='RESTORE-PRIMARY':
                        if finish_committed(backend,active,decision['reason']):
                            publish({'state':'ROLLED-BACK','reason':decision['reason'],'source':active['source'],'target':active['target'],'original_restored':True})
                    else:
                        previous=read_json(STATE,{})
                        publish(dict(previous,state='COMMITTED' if decision['action']=='OBSERVE' else 'DEGRADED-ON-RESERVE',
                                     source=active['source'],target=active['target'],reason=decision['reason'],
                                     blockers=[],reserve_healthy=decision.get('reserve_healthy'),candidates=backend.candidates()))
                    time.sleep(5);continue
                if progress_error:
                    publish({'state':'BLOCKED','blockers':[progress_error]})
                    time.sleep(5);continue
                trial=settings.get('native_trial') or ''
                forced=bool(trial and trial!=last_trial)
                if consumed.get('until')!=until:consumed={'until':until,'count':0,'trial':last_trial,'time':last_attempt}
                if consumed.get('count',0)>=3:
                    publish({'state':'BLOCKED','blockers':['TRIAL-ATTEMPT-LIMIT']});time.sleep(5);continue
                status=read_json(RUNTIME/'status.json',{})
                from failure_diagnosis import diagnose
                diagnosis=diagnose(status,selection['source']['id'],time.time())
                if diagnosis.get('suppress_switch'):
                    publish({'state':'BLOCKED','blockers':[diagnosis['code']],'reason':diagnosis['code'],'source':selection['source']['id'],'target':selection['target']['id'],'certified':False,'next_action':diagnosis.get('next_action')});time.sleep(5);continue
                from recovery_settings import normalized
                recovery=normalized(settings)
                age=max(30,min(900,int(settings.get('interval',10))*3))
                failures=streak(status.get('samples',[]),selection['source']['id'],recovery['failures'],time.time(),age,False,selection['source'])
                healthy=streak(status.get('samples',[]),selection['target']['id'],recovery['successes'],time.time(),age,True,selection['target'])
                certificate=read_json(CERT,{})
                certified=certificate.get('hash')==selection['hash'] and certificate.get('source')==selection['source']['id'] and certificate.get('target')==selection['target']['id'] and certificate.get('direction')==selection['direction'] and certificate.get('until',0)>=until and certificate.get('settings_hash')==selection.get('settings_hash') and certificate.get('vendor_identity')==selection.get('vendor_identity') and matches(certificate,selection)
                if time.time()-last_attempt>=max(recovery['cooldown'],recovery['min_dwell']) and (forced or (certified and failures and healthy)):
                    last_attempt=time.time();last_trial=trial
                    consumed.update(trial=trial,time=last_attempt,count=consumed.get('count',0)+1)
                    atomic_json(ATTEMPTS,consumed)
                    attempt(backend,selection,until,forced,probe_evidence={'source_streak_met':failures,'reserve_streak_met':healthy,'required_failures':recovery['failures'],'required_successes':recovery['successes']},control_revision=decision_revision)
                else:publish({'state':'OBSERVING' if certified else 'TRIAL-REQUIRED','certified':certified,
                    'source':selection['source']['id'],'target':selection['target']['id'],
                    'source_generation':selection['source'].get('vendor_generation'),
                    'target_generation':selection['target'].get('vendor_generation'),
                    'vendor_identity':selection.get('vendor_identity'),'source_failures':failures,'reserve_healthy':healthy})
            except (Refused,OSError,ValueError,KeyError,subprocess.SubprocessError,http.client.HTTPException) as e:
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
        from pair_auto import recover as pair_shutdown
        pair_shutdown(backend)


def configure_timezone():
    os.environ['TZ']='CET-1CEST,M3.5.0,M10.5.0/3'
    if callable(getattr(time,'tzset',None)):
        time.tzset()
    else:
        import ctypes
        ctypes.CDLL(None).tzset()


if __name__=='__main__':
    configure_timezone()
    def stop(*_):
        global STOP
        STOP=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    if len(sys.argv)==3 and sys.argv[1]=='apply':
        try:child(sys.argv[2])
        except (Refused,OSError,ValueError,subprocess.SubprocessError)as error:
            code=str(error)if isinstance(error,Refused)and re.fullmatch('[A-Z][A-Z0-9_-]{0,95}',str(error))else'NATIVE-SYSTEM-001'
            frames=[];cursor=error.__traceback__
            while cursor:
                frames.append({'file':Path(cursor.tb_frame.f_code.co_filename).name,'line':cursor.tb_lineno})
                cursor=cursor.tb_next
            result={'tx':sys.argv[2],'code':code,'time':time.time(),'error_at':frames[-5:]}
            if code=='POLICY-IDENTITY-CHANGED':
                try:
                    sections=Linux().policy()['sections']
                    system=next((s for s in sections if s.get('.name')=='gl_process_vpn'),{})
                    first=next((s for s in sections if s.get('.type')=='rule'and s.get('enabled')=='1'and s.get('via')!='novpn'),{})
                    result['derived_context']={name:{k:row.get(k)for k in('.type','via','mark','enabled','from_type')}for name,row in(('system',system),('first_rule',first))}
                except (Refused,OSError,ValueError,subprocess.SubprocessError):result['context_unavailable']=True
            atomic_json(RUNTIME/'native-apply-result.json',result)
            raise SystemExit(1)
    elif len(sys.argv)==2 and sys.argv[1]=='daemon':serve()
    else:raise SystemExit('fixed daemon/apply actions only')
