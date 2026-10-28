"""Finalize only an inactive failed, no-order-change activation at its exact old missing baseline.

No RTP, routes, VPN flags, kernel rules, boot markers or attempt budgets are written.
The original journal is archived and read back before its own transaction is closed.
This module can be run from a CI-verified recovery payload before upgrading alpha52.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid

ROOT=Path('/')
PINS={'/etc/init.d/vpn-client':'3b751f0691202bc930b8113d7b55d0a38003369c015c672d0797723f1aa79e9a',
      '/usr/bin/rtp2.sh':'d6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e'}


def refuse():
    import native_switch as n
    raise n.Refused('PAIR-RECOVERY-REQUIRED')


def platform_checked():
    for name,wanted in (('tmp/sysinfo/board_name','glinet,mt3000-snand'),('etc/glversion','4.11.0')):
        path=ROOT/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size>128 or path.read_text().strip()!=wanted:refuse()
    for name,sha in PINS.items():
        path=ROOT/name.lstrip('/')
        if path.is_symlink() or not path.is_file() or path.stat().st_size>262144 or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:refuse()


def facts(backend,state,journal,allow_stopping=False):
    import native_switch as n,pair_auto as pair
    from agent import RUNTIME,read_json
    from pair_interfaces import state as interfaces
    from pair_policy import metadata
    from pair_manual import read as manual_read,PENDING
    platform_checked()
    requested=pair.intent();marker=read_json(RUNTIME/'auto-control-revision.json',{})
    revision=marker.get('revision')
    if requested.get('mode')!='off' or requested.get('revision')!=revision or not isinstance(revision,str) or not re.fullmatch('[a-f0-9]{32}',revision):refuse()
    n.require_control_revision(revision)
    from auto_control import public_status
    if public_status().get('requested')!='off':refuse()
    phases=('STOPPED','FAILED','STOPPING','HELD','RUNNING') if allow_stopping else ('STOPPED','FAILED')
    if state.get('phase') not in phases or state.get('owned')!=[]:refuse()
    pending=manual_read()
    if pending and pending.get('state') in PENDING and pending.get('revision')==revision:refuse()
    context=metadata(journal)
    identity=state.get('policy_roles')
    if (not context or journal.get('activation_reapply') is not True or journal.get('manual_request_id') is not None
            or not isinstance(identity,dict) or set(identity)!={'source_rule','target_rule','source_id','target_id','direction','generic_rules'}
            or any(context.get(key)!=value for key,value in identity.items())
            or state.get('process_bindings')!=journal.get('process_bindings')
            or journal.get('phase') not in ('ARMED','APPLYING','RESTORING') or journal.get('confirmed') is not None
            or journal.get('kernel_confirmed') is not None or journal.get('kernel_before_verified') is not False
            or journal.get('before')!=journal.get('after') or journal['before']!=state.get('order')
            or context['session_order']!=state['order'] or journal.get('hash')!=state.get('policy_hash')
            or journal.get('restore_before_order',journal['before'])!=journal['before']
            or journal.get('restore_target_order',journal['before'])!=journal['before']):refuse()
    pid=journal.get('pid');tx=journal.get('tx')
    if type(pid) is int and pid>1:
        path=ROOT/'proc'/str(pid)/'cmdline'
        try:
            if path.exists():
                with path.open('rb') as stream:raw=stream.read(8193)
                if len(raw)>8192 or not raw.endswith(b'\0') or ('native_switch.py\0apply\0'+str(tx)) in raw.decode('utf8','replace'):refuse()
        except OSError:refuse()
    n.bind_policy_context(backend,state)  # The unbound process-rule digest is intentionally different.
    if backend.order()!=(state['order'],state['policy_hash']):refuse()
    managed=interfaces(state)
    if pair.normalized_network(pair.network(),managed)!=state['network_identity'] or pair.changed(state,pair.configs(managed)):refuse()
    kernel=backend.attest_policy()
    original=journal.get('kernel_before_fingerprint')
    if (not isinstance(original,str) or not re.fullmatch('[a-f0-9]{64}',original)
            or kernel.get('verified') is not False or kernel.get('repairable_missing') is not True
            or kernel.get('kernel_fingerprint')!=original):refuse()
    if not allow_stopping and backend.guard_exists():refuse()
    return revision


def finalize(backend=None,state=None,journal=None,allow_stopping=False,check_only=False):
    import native_switch as n,pair_auto as pair
    from agent import PERSIST,checksum
    from auto_control import control_lock
    from native_platform import wait_quiet
    backend=backend or n.Linux();state=state if state is not None else pair.read_state()
    journal=journal if journal is not None else n.journal_read()
    if journal.get('phase')=='ROLLED-BACK' and journal.get('failed_activation_unchanged') is True:
        return {'result':'ALREADY_FINALIZED','changed':False,'kernel_verified':False}
    state_path=pair.paths()[1]
    if n.JOURNAL.is_symlink() or state_path.is_symlink():refuse()
    raw=n.JOURNAL.read_bytes();state_raw=state_path.read_bytes()
    if len(raw)>1024*1024 or len(state_raw)>1024*1024:refuse()
    envelope=json.loads(raw);owned=json.loads(state_raw)
    if (not isinstance(envelope,dict) or envelope.get('schema')!=1 or envelope.get('data')!=journal or envelope.get('sha256')!=n.digest(journal)
            or not isinstance(owned,dict) or owned.get('data')!=state or owned.get('sha256')!=checksum(state)):refuse()
    revision=facts(backend,state,journal,allow_stopping)
    wait_quiet(8)  # No control lock around process scanning, Lua or full kernel attestation.
    facts(backend,state,journal,allow_stopping)
    if n.JOURNAL.read_bytes()!=raw or state_path.read_bytes()!=state_raw:refuse()
    sha=hashlib.sha256(raw).hexdigest()
    if check_only:return {'result':'READY_UNCHANGED','changed':False,'kernel_verified':False,'journal_sha256':sha}
    directory=PERSIST/'session-recovery'
    with control_lock():
        n.require_control_revision(revision)
        if pair.intent().get('mode')!='off' or n.JOURNAL.read_bytes()!=raw or state_path.read_bytes()!=state_raw:refuse()
        if directory.is_symlink():refuse()
        directory.mkdir(mode=0o700,exist_ok=True)
        info=directory.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077:refuse()
        archive=directory/('failed-activation-'+uuid.uuid4().hex+'.json')
        fd=os.open(str(archive),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if archive.read_bytes()!=raw:refuse()
        fd=os.open(str(directory),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    # Revalidate expensive live facts after archiving, before the bounded revision/file CAS.
    facts(backend,state,journal,allow_stopping)
    with control_lock():
        n.require_control_revision(revision)
        if pair.intent().get('mode')!='off' or n.JOURNAL.read_bytes()!=raw or state_path.read_bytes()!=state_raw or archive.read_bytes()!=raw:refuse()
        resolved=copy.deepcopy(journal)
        resolved.update(phase='ROLLED-BACK',restored_order=list(journal['before']),finished=time.time(),
                        failed_activation_unchanged=True,kernel_policy_verified=False,
                        failure_resolution={'archive':archive.name,'sha256':sha,'old_phase':journal['phase'],'time':time.time(),'kernel_unchanged':True})
        n.journal_write(resolved)
        if n.journal_read()!=resolved:refuse()
        journal.clear();journal.update(resolved)
    return {'result':'FINALIZED_UNCHANGED','changed':True,'archived':True,'journal_sha256':sha,'kernel_verified':False}


def main():
    import native_switch as n
    if len(sys.argv)!=2 or sys.argv[1] not in ('--check','--finalize'):raise SystemExit('RECOVERY-ACTION')
    try:result=finalize(check_only=sys.argv[1]=='--check')
    except (n.Refused,OSError,ValueError,TypeError,KeyError):
        print(json.dumps({'result':'REFUSED','code':'PAIR-RECOVERY-REQUIRED','kernel_verified':False}));raise SystemExit(1)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':
    sys.path.insert(0,'/usr/lib/homensai-vpn')
    main()
