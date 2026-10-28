"""Conditional alpha53 recovery from an independently parsed pre-install backup.

Only the known options_in_used=0 plus network-section interleaving is accepted.
The old native procd instance must be removed first. No RTP or VPN flag writes.
Baseline configuration arrives on stdin and is never persisted or printed.
"""
import copy
import hashlib
import json
import os
import math
import re
from pathlib import Path
import stat
import sys
import time
import uuid

ROOT=Path('/')


def refuse():
    import native_switch as n
    raise n.Refused('PAIR-RECOVERY-REQUIRED')


def encode(value):return json.dumps(value,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()


def private_bytes(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077 or info.st_size>1048576:refuse()
    return path.read_bytes()


def legacy_section(section,bindings=None):
    from process_policy import recognizes
    anonymous=section.get('.anonymous') in (True,'1')
    return {k:v for k,v in section.items() if k not in ('.index','name') and not (anonymous and k=='.name')
            and not (recognizes(section,bindings) and k in ('via','mark'))}


def legacy_order(rows):
    import native_switch as n
    return ['a_'+n.digest(legacy_section(row))[:60] if row.get('.anonymous') in (True,'1') else row['.name'] for row in rows]


def legacy_hash(rows,bindings):
    import native_switch as n
    values=sorted([legacy_section(row,bindings) for row in rows],key=n.digest)
    return n.digest(values if bindings is None else {'sections':values,'process_bindings':bindings})


def legacy_network(rows,managed):
    from agent import checksum
    import pair_auto as pair
    kept=[]
    for original in rows:
        row=copy.deepcopy(original);name=row.get('.name')
        if name in managed:row.pop('disabled',None)
        elif isinstance(name,str) and pair.ORPHAN_CLIENT.fullmatch(name) and row.get('disabled')=='1':continue
        kept.append(row)
    return checksum(kept)


def writers_quiet():
    """Read both procd ownership and live argv; a new lock alone cannot fence v53."""
    import native_switch as n
    services=json.loads(n.command(['ubus','call','service','list','{"name":"homensai-vpn"}']))
    instances=services.get('homensai-vpn',{}).get('instances')
    if not isinstance(instances,dict) or 'native' in instances or not isinstance(instances.get('monitor'),dict) or instances['monitor'].get('running') is not True:refuse()
    paths=list((ROOT/'proc').glob('[0-9]*/cmdline'))
    if len(paths)>4096:refuse()
    for path in paths:
        try:
            with path.open('rb') as stream:raw=stream.read(8193)
        except FileNotFoundError:continue
        except OSError:refuse()
        if len(raw)>8192:refuse()
        if any(Path(item.decode('utf8','replace')).name=='native_switch.py' for item in raw.split(b'\0') if item):refuse()


def facts(backend,state,journal,baseline):
    import native_switch as n,pair_auto as pair
    from activation_recovery import platform_checked
    from agent import RUNTIME,read_json
    from auto_control import public_status
    from pair_interfaces import state as interfaces
    from pair_policy import metadata,proof,role
    from stock_derived import no_override_options
    platform_checked();writers_quiet()
    requested=pair.intent();revision=read_json(RUNTIME/'auto-control-revision.json',{}).get('revision')
    if requested.get('mode')!='off' or requested.get('revision')!=revision or public_status().get('requested')!='off':refuse()
    n.require_control_revision(revision)
    if (state.get('phase') not in ('HELD','STOPPING','STOPPED') or state.get('owned')!=[]
            or journal.get('phase')!='RESTORING' or journal.get('activation_reapply') is not True
            or journal.get('rtp_dispatched') is not True or journal.get('restore_before_verified') is not True
            or journal.get('kernel_before_verified') is not False or journal.get('confirmed') is not None
            or journal.get('kernel_confirmed') is not None or journal.get('manual_request_id') is not None
            or journal.get('before')!=journal.get('after') or journal.get('before')!=state.get('order')
            or journal.get('hash')!=state.get('policy_hash') or state.get('process_bindings')!=journal.get('process_bindings')):refuse()
    context=metadata(journal)
    if (not context or context['session_order']!=state['order'] or context['destination_role']!='target'
            or context['before_policy_role']!='target' or role(context,state['order'])!='target'
            or any(context.get(key)!=value for key,value in state.get('policy_roles',{}).items())
            or set(state.get('policy_roles',{}))!={'source_rule','target_rule','source_id','target_id','direction','generic_rules'}
            or journal.get('restore_target_order')!=journal['before']):refuse()
    # Repair this one known writer anomaly only for structural validation, not adoption.
    repaired=copy.deepcopy(journal);repaired['restore_before_order']=list(journal['before']);n.validate_journal(repaired)
    if not isinstance(baseline,dict) or not isinstance(baseline.get('network'),list) or not isinstance(baseline.get('route_policy'),list):refuse()
    before=baseline['route_policy'];old_network=baseline['network'];bindings=state['process_bindings'];managed=interfaces(state)
    if (legacy_order(before)!=state['order'] or legacy_hash(before,bindings)!=state['policy_hash']
            or legacy_network(old_network,managed)!=state['network_identity']):refuse()
    n.bind_policy_context(backend,state);current=backend.policy()['sections'];rows=pair.network()
    if (legacy_order(current)!=journal.get('restore_before_order') or journal['restore_before_order']==journal['before']
            or len(current)!=len(before) or pair.normalized_network(old_network,managed)!=pair.normalized_network(rows,managed)):refuse()
    changes=0
    for old,new in zip(before,current):
        old=copy.deepcopy(old);new=copy.deepcopy(new)
        if old.get('.anonymous') in (True,'1'):old.pop('.name',None)
        if new.get('.anonymous') in (True,'1'):new.pop('.name',None)
        old.pop('.index',None);new.pop('.index',None)
        if 'options_in_used' not in old and no_override_options(new,bindings):new.pop('options_in_used');changes+=1
        if old!=new:refuse()
    if changes!=2 or backend.order()!=(state['order'],state['policy_hash']):refuse()
    if pair.changed(state,pair.configs(managed)):refuse()
    blockers,selection=backend.diagnostic()
    if blockers or not selection or proof(selection)!=state['policy_roles'] or selection.get('vendor_identity')!=journal.get('vendor_identity'):refuse()
    kernel=backend.attest_policy(selection)
    if (kernel.get('verified') is not True or kernel.get('role')!='target'
            or kernel.get('profile_id')!=journal['target'] or kernel.get('order')!=state['order']
            or kernel.get('policy_hash')!=state['policy_hash']
            or not isinstance(kernel.get('kernel_fingerprint'),str) or not re.fullmatch('[a-f0-9]{64}',kernel['kernel_fingerprint'])
            or type(kernel.get('time')) not in (int,float) or not math.isfinite(kernel['time']) or not 0<=time.time()-kernel['time']<=5):refuse()
    # guard_exists also rejects tables without the application's ownership marker.
    backend.guard_exists()
    return revision,kernel,pair.normalized_network(rows,managed)


def recover(baseline,backend=None,check_only=False):
    import native_switch as n,pair_auto as pair
    from agent import PERSIST,atomic_json,checksum
    from auto_control import control_lock
    from native_platform import wait_quiet
    backend=backend or n.Linux();state_path=pair.paths()[1];progress_path=PERSIST/'stock-derived-recovery.json'
    raw=private_bytes(n.JOURNAL);state_raw=private_bytes(state_path)
    progress=None
    if progress_path.exists():
        envelope=json.loads(private_bytes(progress_path));progress=envelope.get('data')
        if not isinstance(progress,dict) or envelope.get('sha256')!=checksum(progress) or progress.get('baseline_sha256')!=n.digest(baseline):refuse()
        directory=PERSIST/'session-recovery'
        if directory.is_symlink() or directory.stat().st_uid!=os.geteuid() or directory.stat().st_mode&0o077:refuse()
        import re
        if any(not isinstance(progress.get(key),str) or not re.fullmatch(r'stock53-(?:journal|state)-[a-f0-9]{32}\.json',progress[key]) for key in ('journal_archive','state_archive')):refuse()
        old_raw=private_bytes(directory/progress['journal_archive']);old_state_raw=private_bytes(directory/progress['state_archive'])
        if sha(old_raw)!=progress['journal_sha256'] or sha(old_state_raw)!=progress['state_sha256']:refuse()
    else:old_raw=raw;old_state_raw=state_raw
    envelope=json.loads(old_raw);saved=json.loads(old_state_raw);journal=envelope.get('data');state=saved.get('data')
    if (not isinstance(journal,dict) or type(envelope.get('schema')) is not int or envelope['schema']!=1 or envelope.get('sha256')!=n.digest(journal)
            or not isinstance(state,dict) or saved.get('sha256')!=checksum(state)):refuse()
    if progress:
        expected=copy.deepcopy(progress['target_state']);actual=pair.read_state();phase=actual.get('phase');actual['phase']=expected['phase']
        if state_raw!=old_state_raw and (actual!=expected or phase not in ('HELD','STOPPING','STOPPED')):refuse()
        if raw not in (old_raw,encode(progress['target_journal_envelope'])):refuse()
    elif pair.read_state()!=state:refuse()
    revision,kernel,network_identity=facts(backend,state,journal,baseline)
    wait_quiet(8)
    second=facts(backend,state,journal,baseline)
    if second[0]!=revision or second[1].get('kernel_fingerprint')!=kernel.get('kernel_fingerprint') or second[2]!=network_identity:refuse()
    if n.JOURNAL.read_bytes()!=raw or state_path.read_bytes()!=state_raw:refuse()
    if progress and (progress['revision']!=revision or progress['kernel_fingerprint']!=kernel.get('kernel_fingerprint')):refuse()
    if progress and pair.read_state().get('phase')=='STOPPED' and raw==encode(progress['target_journal_envelope']) and not backend.guard_exists():
        return {'result':'ALREADY_STOPPED','changed':False,'kernel_verified':True}
    if check_only:return {'result':'READY_KNOWN_STOCK_CHANGE','changed':False,'kernel_verified':True}
    if not progress:
        target=copy.deepcopy(journal);target.update(phase='ROLLED-BACK',restore_before_order=list(journal['before']),restored_order=list(journal['before']),
            finished=time.time(),kernel_confirmed=kernel['time'],reason='KNOWN-STOCK-DERIVED-RECOVERY',failed_stock_activation_resolved=True)
        n.note_phase(target,'ROLLED-BACK');n.validate_journal(target)
        target_state=copy.deepcopy(state);target_state['network_identity']=network_identity
        target_state['stock_derived_recovery']={'baseline_sha256':n.digest(baseline),'journal_sha256':sha(raw),'time':time.time()}
        directory=PERSIST/'session-recovery';nonce=uuid.uuid4().hex
        progress={'revision':revision,'baseline_sha256':n.digest(baseline),'journal_sha256':sha(raw),'state_sha256':sha(state_raw),
                  'journal_archive':'stock53-journal-'+nonce+'.json','state_archive':'stock53-state-'+nonce+'.json',
                  'kernel_fingerprint':kernel.get('kernel_fingerprint'),'target_state':target_state,
                  'target_journal_envelope':{'schema':1,'data':target,'sha256':n.digest(target)}}
        with control_lock():
            n.require_control_revision(revision)
            if pair.intent().get('mode')!='off' or n.JOURNAL.read_bytes()!=raw or state_path.read_bytes()!=state_raw:refuse()
            if directory.is_symlink():refuse()
            directory.mkdir(mode=0o700,exist_ok=True);info=directory.stat()
            if info.st_uid!=os.geteuid() or info.st_mode&0o077:refuse()
            for name,content in ((progress['journal_archive'],raw),(progress['state_archive'],state_raw)):
                path=directory/name;fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
                with os.fdopen(fd,'wb') as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
                if private_bytes(path)!=content:refuse()
            fd=os.open(str(directory),os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
            atomic_json(progress_path,{'data':progress,'sha256':checksum(progress)})
    def same_facts():
        latest=facts(backend,state,journal,baseline)
        if latest[0]!=revision or latest[1].get('kernel_fingerprint')!=kernel.get('kernel_fingerprint') or latest[2]!=network_identity:refuse()
    # Fresh proof after the archive; none of the slow work holds the UI lock.
    same_facts()
    with control_lock():
        n.require_control_revision(revision)
        if pair.intent().get('mode')!='off' or n.JOURNAL.read_bytes()!=raw or state_path.read_bytes()!=state_raw:refuse()
        pair.save(progress['target_state'])
        n.journal_write(copy.deepcopy(progress['target_journal_envelope']['data']))
        if n.JOURNAL.read_bytes()!=encode(progress['target_journal_envelope']):refuse()
    current=pair.read_state()
    if current['phase']!='STOPPED':
        same_facts()
        if not pair.cleanup(backend,current,stop_revision=revision):refuse()
        n.publish({'state':'STOPPED','mode':'continuous-pair','proof_scope':pair.MODE,'original_restored':True,
                   'readiness_verified':False,'reason':'KNOWN-STOCK-DERIVED-RECOVERY','blockers':[]})
    if backend.guard_exists() or pair.read_state()['phase']!='STOPPED':refuse()
    return {'result':'KNOWN_STOCK_CHANGE_STOPPED','changed':True,'kernel_verified':True,'archived':True}


def main():
    import native_switch as n
    if len(sys.argv)!=2 or sys.argv[1] not in ('--check','--recover'):raise SystemExit('RECOVERY-ACTION')
    n.HELPER=str(Path(__file__).with_name('native_policy.lua'))
    try:
        raw=sys.stdin.buffer.read(1048577)
        if len(raw)>1048576:refuse()
        result=recover(json.loads(raw),check_only=sys.argv[1]=='--check')
    except (n.Refused,OSError,ValueError,TypeError,KeyError):
        print(json.dumps({'result':'REFUSED','code':'PAIR-RECOVERY-REQUIRED'}));raise SystemExit(1)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
