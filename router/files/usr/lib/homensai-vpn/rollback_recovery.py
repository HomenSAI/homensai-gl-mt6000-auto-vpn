"""Resume only our proven, unchanged pre-RTP rollback graph.

This never infers permission from a role or from a legacy journal. A recorded
full mangle/rule fingerprint, current tunnel bindings and the stopped owning
session must all agree before any retry can be dispatched.
"""
import copy
import re


def order_steps(before,target):
    """The minimal left-to-right UCI moves used by Linux.reorder()."""
    if (not isinstance(before,list) or not isinstance(target,list) or not 2<=len(before)<=400
            or len(before)!=len(target) or any(not isinstance(x,str) for x in before+target)
            or len(set(before))!=len(before) or set(before)!=set(target)):
        raise ValueError('JOURNAL-INTEGRITY-FAILED')
    current=list(before)
    for index,identifier in enumerate(target):
        if current[index]==identifier:continue
        previous=list(current);current.remove(identifier);current.insert(index,identifier)
        yield {'version':1,'kind':'reorder','before':previous,'after':list(current),'section':identifier,'index':index}


def validate_step(journal):
    """A new checkpoint grants only one canonical before/after transition."""
    before=restore_origin(journal);target=journal.get('restore_target_order')
    if 'restore_order_step' not in journal:return None
    step=journal['restore_order_step']
    if (not isinstance(step,dict) or type(step.get('version')) is not int or step['version']!=1
            or journal.get('phase') not in ('RESTORING','ROLLED-BACK','RELEASE-PENDING')
            or journal.get('restore_before_verified') is not True
            or not isinstance(journal.get('restore_kernel_fingerprint'),str)
            or not re.fullmatch('[a-f0-9]{64}',journal['restore_kernel_fingerprint'])
            or journal.get('restore_before_order') not in (journal.get('before'),journal.get('after'),journal.get('restored_order'))):
        raise ValueError('JOURNAL-INTEGRITY-FAILED')
    moves=list(order_steps(before,target))
    commit={'version':1,'kind':'commit','before':target,'after':target}
    if step==commit:return step
    if type(step.get('index')) is int and any(step==expected for expected in moves):return step
    raise ValueError('JOURNAL-INTEGRITY-FAILED')


def restore_origin(journal):
    """Keep the UCI plan separate from the order proven by the actual kernel."""
    if 'restore_proof_source' not in journal and 'restore_order_origin' not in journal:return journal.get('restore_before_order')
    source=journal.get('restore_proof_source')
    origins=[journal.get('after')]
    if source=='vendor-rebuild':
        # Our own vendor RTP died mid-rebuild (worker stage rtp-dispatch). The
        # UCI origin may be either recorded order; every forward flag still holds.
        detail=journal.get('failure_detail')
        if not isinstance(detail,dict) or detail.get('worker_stage')!='rtp-dispatch':raise ValueError('JOURNAL-INTEGRITY-FAILED')
        origins.append(journal.get('before'))
    elif source!='forward':raise ValueError('JOURNAL-INTEGRITY-FAILED')
    if (journal.get('restore_order_origin') not in origins
            or journal.get('restore_before_order')!=journal.get('before') or journal.get('restore_target_order')!=journal.get('before')
            or journal.get('before')==journal.get('after') or journal.get('kernel_before_verified') is not True
            or journal.get('restore_before_verified') is not True or journal.get('rtp_dispatched') is not True
            or journal.get('forward_policy_touched') is not True or journal.get('confirmed') is not None
            or journal.get('kernel_confirmed') is not None or 'restore_order_step' not in journal
            or journal.get('restore_kernel_fingerprint')!=journal.get('kernel_before_fingerprint')):
        raise ValueError('JOURNAL-INTEGRITY-FAILED')
    return journal['restore_order_origin']


def order_allowed(journal,order):
    step=validate_step(journal)
    return order in (step['before'],step['after']) if step is not None else order==journal.get('restore_target_order')


def record_step(backend,journal,args):
    """Persist a verified pending UCI write before dispatch, never infer a lost step."""
    import native_switch as n
    if args[:2]!=['uci','reorder'] and args!=['uci','commit','route_policy']:return
    if journal.get('restore_before_verified') is not True:return
    if n.journal_read()!=journal:raise n.Refused('JOURNAL-INTEGRITY-FAILED')
    sections=backend.policy()['sections'];bindings=journal.get('process_bindings')
    live=n.policy_order(sections,bindings)
    if n.policy_hash(sections,bindings)!=journal['hash']:raise n.Refused('POLICY-IDENTITY-CHANGED')
    target=journal['restore_target_order']
    if args==['uci','commit','route_policy']:
        if live!=target:raise n.Refused('POLICY-IDENTITY-CHANGED')
        step={'version':1,'kind':'commit','before':list(live),'after':list(live)}
    else:
        step=next((row for row in order_steps(restore_origin(journal),target) if row['before']==live),None)
        names={n.section_id(row,bindings):row['.name'] for row in sections}
        if step is None or args!=['uci','reorder','route_policy.'+names[step['section']]+'='+str(step['index'])]:
            raise n.Refused('POLICY-IDENTITY-CHANGED')
    if n.journal_read()!=journal or backend.order()!=(live,journal['hash']):raise n.Refused('POLICY-IDENTITY-CHANGED')
    journal['restore_order_step']=step
    n.journal_write(journal)
    if n.journal_read()!=journal or backend.order()!=(live,journal['hash']):raise n.Refused('POLICY-IDENTITY-CHANGED')


def forward_proof(journal):
    return (journal.get('phase') in ('APPLYING','WAIT-CLIENT') and journal.get('rtp_dispatched') is True
            and journal.get('forward_policy_touched') is True and journal.get('kernel_before_verified') is True
            and journal.get('confirmed') is None and journal.get('kernel_confirmed') is None
            and journal.get('before')!=journal.get('after')
            and not any(key.startswith('restore') for key in journal))


def authorize(backend,journal,forward=False):
    import native_switch as n
    import pair_auto as pair
    from agent import RUNTIME,read_json
    from pair_policy import metadata,proof
    from pair_interfaces import state as interfaces
    from failure_diagnosis import profile_identity

    def refuse():raise n.Refused('KERNEL-POLICY-UNVERIFIED')
    fingerprint=journal.get('kernel_before_fingerprint' if forward else 'restore_kernel_fingerprint')
    context=metadata(journal)
    if context is None or not isinstance(fingerprint,str) or not re.fullmatch('[a-f0-9]{64}',fingerprint):refuse()
    if forward:
        if not forward_proof(journal):refuse()
    elif (journal.get('phase')!='RESTORING' or journal.get('restore_before_verified') is not True
          or journal.get('restore_target_order') is None or journal.get('restore_before_order') is None):refuse()
    # A new supervisor revision fences the old operation. Its stopped intent
    # is observed, never replaced or rotated by this recovery helper.
    marker=read_json(RUNTIME/'auto-control-revision.json',{})
    revision=marker.get('revision') if isinstance(marker,dict) else None
    n.require_control_revision(revision)
    state=pair.read_state();requested=pair.intent()
    if (requested.get('mode')!='off' or requested.get('revision')!=revision
            or state.get('phase') not in ('RUNNING','HELD','STOPPING')
            or state.get('id')!=journal.get('trial_nonce')
            or state.get('revision')!=journal.get('control_revision')
            or state.get('process_bindings')!=journal.get('process_bindings')
            or state.get('order')!=context['session_order'] or state.get('policy_hash')!=journal.get('hash')
            or state.get('policy_roles')!={key:context[key] for key in ('source_rule','target_rule','direction','generic_rules','source_id','target_id')}):refuse()

    def check():
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.guard_exists() is not True):refuse()
        managed=interfaces(state)
        if (pair.normalized_network(pair.network(),managed)!=state['network_identity']
                or pair.changed(state,pair.configs(managed))):refuse()
        # diagnostic() validates each live route_binding (default route,
        # marked route lookups, device/ifindex/table/mark and profile epoch).
        # Missing/down or changed bindings never use this narrow exception.
        blockers,selection=backend.diagnostic()
        if (blockers or not isinstance(selection,dict) or proof(selection)!=state['policy_roles']
                or selection.get('hash')!=journal['hash']
                or selection.get('vendor_identity')!=journal.get('vendor_identity')
                or selection.get('process_bindings')!=journal.get('process_bindings')):refuse()
        for role in ('source','target'):
            current=selection.get(role,{})
            identity=profile_identity(current)
            if identity is None or identity!=(journal.get('vendor_profiles') or {}).get(role):refuse()
            binding=current.get('kernel_binding')
            if (not isinstance(binding,dict) or binding.get('code') is not None
                    or not isinstance(binding.get('device'),str) or not re.fullmatch('[A-Za-z0-9_]{1,15}',binding['device'])
                    or type(binding.get('mark')) is not int or binding['mark']<=0
                    or not isinstance(binding.get('table'),str) or not binding['table'].isdigit()
                    or type(binding.get('ifindex')) is not int or binding['ifindex']<=0):refuse()
        observed_identity=n.digest({role:{'profile':profile_identity(selection[role]),'kernel':selection[role]['kernel_binding']}
                                    for role in ('source','target')})
        if observed_identity!=journal['vendor_identity']:refuse()
        live=backend.order()
        # Old proofs still require the completed order. A new durable step
        # permits only its exact before/after, never any other permutation or
        # an invented checkpoint for a legacy interrupted multi-rule move.
        if (live!=(selection.get('order'),journal['hash'])
                or (live[0]!=journal['after'] if forward else not order_allowed(journal,live[0]))
                or backend.kernel_fingerprint()!=fingerprint):refuse()
        # Recheck the durable/Stop fence after the expensive read-only checks.
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.order()!=live or backend.guard_exists() is not True):refuse()

    check()
    return check,revision


def promote_forward(backend,journal,target):
    """Reuse an existing full forward proof only after Stop, never infer one."""
    import native_switch as n
    import pair_auto as pair
    from agent import RUNTIME
    from auto_control import control_lock
    if target!=journal.get('before'):raise n.Refused('KERNEL-POLICY-UNVERIFIED')
    check,revision=authorize(backend,journal,forward=True)
    state=pair.read_state();requested=pair.intent()
    pending=copy.deepcopy(journal)
    pending.update(phase='RESTORING',restore_proof_source='forward',restore_order_origin=list(journal['after']),
                   restore_before_order=list(journal['before']),restore_before_verified=True,restore_target_order=list(target),
                   restore_kernel_fingerprint=journal['kernel_before_fingerprint'])
    pending['restore_order_step']=next(order_steps(pending['restore_order_origin'],target))
    check()  # Repeat the live graph/bindings proof before the bounded durable CAS.
    with control_lock(RUNTIME):
        n.require_control_revision(revision)
        if n.journal_read()!=journal or pair.read_state()!=state or pair.intent()!=requested:
            raise n.Refused('JOURNAL-INTEGRITY-FAILED')
        n.journal_write(pending)
        if n.journal_read()!=pending:raise n.Refused('JOURNAL-INTEGRITY-FAILED')
    journal.clear();journal.update(pending)
    return authorize(backend,journal)


# --- Own interrupted vendor rebuild -----------------------------------------
# The stock rtp2.sh flushes its mangle chains and deletes every gl_vpn_rules
# firewall section before rebuilding them. When our own apply worker died at
# stage rtp-dispatch (e.g. the old 50 s parent cap SIGKILLed its group), the
# kernel and those vendor sections are a partial vendor intermediate: there is
# no verified graph to prove and nothing else completes it. This narrow path
# restores our recorded UCI order and reruns the vendor rebuild to completion,
# then requires the exact protected configuration, an attested original role
# and the owned guard. Every other mismatch refuses before any write.
VENDOR_LOCK='/tmp/run/rtp2.lock'
RECOVERY_RTP_TIMEOUT=90  # supervisor recovery: no parent kills it; still bounded
ALLOWED_STALE_LOCK=[None]  # set only while a vendor-rebuild proof reads diagnostics
STABLE_PROFILE=('id','protocol','interface','vendor_tunnel_id')  # profile identity without the monitor epoch
SETTLE_SECONDS=90;SETTLE_POLL=3
VENDOR_SETTLE_SECONDS=60;VENDOR_SETTLE_POLL=3  # GL hotplug/firewall reloads after a switch  # monitor settle after a restart is 30 s at the 10 s interval


def vendor_lock_pid():
    """None if absent; the recorded pid when the lock is provably stale; else refuse."""
    from pathlib import Path
    if list(Path('/var/run').glob('tunnel-switch*.lock')):raise ValueError('VENDOR-WORKER-BUSY')
    path=Path(VENDOR_LOCK)
    if path.is_symlink():raise ValueError('VENDOR-WORKER-BUSY')
    try:raw=path.read_bytes()
    except FileNotFoundError:return None
    text=raw.decode('ascii').strip() if len(raw)<=32 else ''
    if not re.fullmatch('[1-9][0-9]{0,9}',text):raise ValueError('VENDOR-WORKER-BUSY')
    try:command=(Path('/proc')/text/'cmdline').read_bytes()
    except FileNotFoundError:return int(text)  # dead pid: its EXIT trap never ran
    if b'rtp2' in command:raise ValueError('VENDOR-WORKER-BUSY')
    return int(text)  # pid reused by an unrelated process


def rtp_lock_busy():
    """Any vendor lock is busy, except the one stale lock a rebuild proof just proved."""
    from pathlib import Path
    if not Path(VENDOR_LOCK).exists() and not Path(VENDOR_LOCK).is_symlink():return False
    allowed=ALLOWED_STALE_LOCK[0]
    if allowed is None:return True
    try:return vendor_lock_pid()!=allowed
    except (OSError,ValueError):return True


def interrupted_vendor_rtp(journal):
    detail=journal.get('failure_detail')
    return (journal.get('phase')=='APPLYING' and forward_proof(journal)
            and isinstance(detail,dict) and detail.get('worker_stage')=='rtp-dispatch')


def vendor_rebuild_applies(backend,journal):
    if journal.get('phase')=='RESTORING' and journal.get('restore_proof_source')=='vendor-rebuild':return True
    # The rebuild never overwrites a routed graph: only an unrouted vendor
    # intermediate (flushed, no TUNNEL route chain, no LAN MARK) qualifies.
    return (interrupted_vendor_rtp(journal) and backend.kernel_fingerprint()!=journal.get('kernel_before_fingerprint')
            and unrouted_kernel())


def settled(backend,clock=None,sleep=None):
    """diagnostic(), waiting a bounded time while it is only not ready yet.

    A supervisor restart (upgrade, reboot) also restarts the monitor, which
    renews every vendor generation; the pair stays unsettled for ~30 s. Nothing
    is written while waiting; the caller decides on the last reading.
    """
    import time
    clock=clock or time.monotonic;sleep=sleep or time.sleep
    until=clock()+SETTLE_SECONDS
    import native_switch as n
    while True:
        blockers,current=backend.diagnostic()
        if not blockers and isinstance(current,dict) or clock()>=until or n.STOP:return blockers,current
        sleep(SETTLE_POLL)


def vendor_settled(backend,clock=None,sleep=None,board=None):
    """MT3000 only: wait (bounded) until GL workers are quiet and the kernel graph is stable.

    Right after a switch the vendor may cycle the tunnel and reload the firewall
    several times (hotplug ifdown/ifup). A rollback proof taken in those seconds
    sees a moving kernel fingerprint and refuses, spending the bounded budget on
    a transient. Nothing is written while waiting; the caller still decides.
    """
    import time
    from device_profile import detect
    if (board or detect())!='mt3000':return
    clock=clock or time.monotonic;sleep=sleep or time.sleep
    until=clock()+VENDOR_SETTLE_SECONDS
    try:
        from native_platform import wait_quiet
        wait_quiet(min(30,max(1,until-clock())))
    except (OSError,ValueError,ImportError):pass
    previous=None
    import native_switch as n
    while clock()<until and not n.STOP:
        try:current=backend.kernel_fingerprint()
        except Exception:current=None
        if current is not None and current==previous:return
        previous=current;sleep(VENDOR_SETTLE_POLL)


def unrouted_kernel():
    import native_switch as n
    from kernel_policy import unrouted
    try:return unrouted(n.command(['iptables-save','-t','mangle']).decode('utf8'))
    except (OSError,ValueError,UnicodeError):return False


def rebuild(backend,journal,reason,target):
    import time
    from pathlib import Path
    import native_switch as n
    import pair_auto as pair
    from agent import RUNTIME,read_json
    from auto_control import control_lock
    from pair_policy import metadata,proof,role
    from pair_interfaces import state as interfaces
    from failure_diagnosis import profile_identity

    def refuse(code='KERNEL-POLICY-UNVERIFIED'):raise n.Refused(code)
    context=metadata(journal)
    if context is None or target!=journal.get('before'):refuse()
    if journal.get('phase')=='RESTORING':
        if journal.get('restore_proof_source')!='vendor-rebuild':refuse()
        try:validate_step(journal)
        except (ValueError,TypeError,KeyError):refuse('JOURNAL-INTEGRITY-FAILED')
    elif not interrupted_vendor_rtp(journal):refuse()
    pid=journal.get('pid')
    if pid is not None:
        try:
            if ('native_switch.py\x00apply\x00'+journal['tx']).encode() in Path('/proc',str(pid),'cmdline').read_bytes():
                refuse('VENDOR-WORKER-BUSY')  # our worker still lives: never race it
        except FileNotFoundError:pass
    marker=read_json(RUNTIME/'auto-control-revision.json',{})
    revision=marker.get('revision') if isinstance(marker,dict) else None
    n.require_control_revision(revision)
    state=pair.read_state();requested=pair.intent()
    if (requested.get('mode')!='off' or requested.get('revision')!=revision
            or state.get('phase') not in ('RUNNING','HELD','STOPPING')
            or state.get('id')!=journal.get('trial_nonce')
            or state.get('revision')!=journal.get('control_revision')
            or state.get('process_bindings')!=journal.get('process_bindings')
            or state.get('order')!=context['session_order'] or state.get('policy_hash')!=journal.get('hash')
            or state.get('policy_roles')!={key:context[key] for key in ('source_rule','target_rule','direction','generic_rules','source_id','target_id')}):refuse()
    managed=interfaces(state);lock=[None];kernel=[None]

    def pending(final=False):
        lines=[x for x in n.command(['uci','-q','changes']).decode('utf8','replace').splitlines() if x.strip()]
        step=journal.get('restore_order_step') or {}
        # Only our own recorded, still uncommitted route_policy move may be pending.
        owned=step.get('kind')=='reorder' or step.get('kind')=='commit' and journal.get('restore_order_origin')!=journal.get('restore_target_order')
        if lines and (final or not owned or any(not x.startswith('route_policy.') for x in lines)):
            refuse('PAIR-EXTERNAL-CONFIG-CHANGE')

    def configuration(final=False):
        if pair.normalized_network(pair.network(),managed)!=state['network_identity']:refuse('PAIR-EXTERNAL-NETWORK-CHANGE')
        observed=pair.configs(managed)
        if pair.changed(state,observed,skip=('firewall',)):refuse('PAIR-EXTERNAL-CONFIG-CHANGE')
        if not pair.changed(state,observed):return
        # Before the rebuild only vendor-owned gl_vpn_rules sections may differ;
        # a session without the stored static digest is decided after the rebuild.
        static=(state.get('protected_static') or {}).get('firewall')
        if final or static is not None and pair.static_firewall_digest(pair.firewall_bytes())!=static:
            refuse('PAIR-EXTERNAL-CONFIG-CHANGE')

    def selection():
        try:lock[0]=vendor_lock_pid()
        except (OSError,ValueError):refuse('VENDOR-WORKER-BUSY')
        ALLOWED_STALE_LOCK[0]=lock[0]
        try:blockers,current=settled(backend)
        finally:ALLOWED_STALE_LOCK[0]=None
        if (blockers or not isinstance(current,dict) or proof(current)!=state['policy_roles']
                or current.get('hash')!=journal['hash']
                or current.get('process_bindings')!=journal.get('process_bindings')):refuse()
        recorded=journal.get('vendor_profiles') or {};same_epoch=True
        for key in ('source','target'):
            row=current.get(key,{});binding=row.get('kernel_binding');live=profile_identity(row)
            if live is None or not isinstance(recorded.get(key),dict):refuse()
            # vendor_generation is the monitor's observation epoch: a restart
            # (upgrade, reboot) renews it. The configured tunnel identity must
            # still match exactly; the result is proven by kernel attestation.
            if any(live.get(field)!=recorded[key].get(field) for field in STABLE_PROFILE):refuse()
            same_epoch=same_epoch and live==recorded[key]
            if (not isinstance(binding,dict) or binding.get('code') is not None
                    or not isinstance(binding.get('device'),str) or not re.fullmatch('[A-Za-z0-9_]{1,15}',binding['device'])
                    or type(binding.get('mark')) is not int or binding['mark']<=0
                    or not isinstance(binding.get('table'),str) or not binding['table'].isdigit()
                    or type(binding.get('ifindex')) is not int or binding['ifindex']<=0):refuse()
        if same_epoch and (current.get('vendor_identity')!=journal.get('vendor_identity')
                or n.digest({key:{'profile':profile_identity(current[key]),'kernel':current[key]['kernel_binding']}
                             for key in ('source','target')})!=journal['vendor_identity']):refuse()
        return current

    def check():
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.guard_exists() is not True):refuse()
        pending();configuration();current=selection()
        live=backend.order()
        allowed=(order_allowed(journal,live[0]) if journal.get('phase')=='RESTORING'
                 else live[0] in (journal['after'],journal['before']))
        fingerprint=backend.kernel_fingerprint()
        if live!=(current.get('order'),journal['hash']) or not allowed or not isinstance(fingerprint,str):refuse()
        # Until our own rebuild runs, nobody else may touch the partial graph.
        if journal.get('restore_rtp_dispatched') is not True:
            if not unrouted_kernel():refuse()
            if kernel[0] is None:kernel[0]=fingerprint
            elif fingerprint!=kernel[0]:refuse()
        n.require_control_revision(revision)
        if (pair.intent()!=requested or pair.read_state()!=state or n.journal_read()!=journal
                or backend.order()!=live or backend.guard_exists() is not True):refuse()
        return live[0]

    live=check()
    if journal.get('phase')=='APPLYING':
        updated=copy.deepcopy(journal)
        updated.update(phase='RESTORING',restore_proof_source='vendor-rebuild',restore_order_origin=list(live),
                       restore_before_order=list(journal['before']),restore_before_verified=True,restore_target_order=list(target),
                       restore_kernel_fingerprint=journal['kernel_before_fingerprint'])
        updated['restore_order_step']=next(order_steps(live,target),{'version':1,'kind':'commit','before':list(target),'after':list(target)})
        with control_lock(RUNTIME):
            n.require_control_revision(revision)
            if n.journal_read()!=journal or pair.read_state()!=state or pair.intent()!=requested:refuse('JOURNAL-INTEGRITY-FAILED')
            n.journal_write(updated)
            if n.journal_read()!=updated:refuse('JOURNAL-INTEGRITY-FAILED')
        journal.clear();journal.update(updated)
        n.publish(dict(n.pair_event_fields(journal,restoring=True,restore_order=target),state='RESTORING',reason=reason,
                       source=journal['source'],target=journal['target'],proof_scope=journal.get('proof_scope','router-probed-ipv4')))

    def write(args,timeout=5):
        check()
        record_step(backend,journal,args)
        check()
        if args[0]=='/usr/bin/rtp2.sh':
            if lock[0] is not None:
                # Remove only the lock just proven stale (same dead pid); rtp2.sh
                # would wait 30 s and remove it itself, inside our RTP bound.
                try:same=vendor_lock_pid()==lock[0]
                except (OSError,ValueError):same=False
                if not same:refuse('VENDOR-WORKER-BUSY')
                try:Path(VENDOR_LOCK).unlink()
                except FileNotFoundError:pass
            journal['restore_rtp_dispatched']=True;n.journal_write(journal)
            timeout=RECOVERY_RTP_TIMEOUT
        elif args[0]=='iptables-restore':
            # Fast path writes the same kernel graph as rtp2; a resumed recovery must know the graph moved.
            journal['restore_rtp_dispatched']=True;n.journal_write(journal)
        return n.forward_dispatch(args,revision,timeout=timeout)

    step=journal.get('restore_order_step') or {}
    if live!=target:backend.reorder(target,write_command=write)
    elif step.get('kind')=='reorder':write(['uci','commit','route_policy'])  # our last move, uncommitted
    backend.apply(write_command=write)

    def failed(code='ROLLBACK-UNVERIFIED'):
        try:backend.guard(backend.devices())
        except (n.Refused,OSError,ValueError):pass
        refuse(code)
    if backend.order()!=(target,journal['hash']):failed()
    blockers,current=settled(backend)
    kernel_proof=backend.attest_policy(current) if not blockers and current else {}
    if kernel_proof.get('verified') is not True or kernel_proof.get('role')!=role(context,target):failed()
    if backend.guard_exists() is not True:failed()
    try:pending(final=True);configuration(final=True)
    except n.Refused as error:failed(str(error))
    n.require_control_revision(revision)
    if pair.intent()!=requested or pair.read_state()!=state:failed('CLIENT-STOP')
    journal.update(phase='ROLLED-BACK',reason=reason,finished=time.time(),restored_order=list(target))
    n.journal_write(journal)
    backend.guard(backend.devices())
    fields=n.pair_event_fields(journal,completed=True,outcome='restored',restoring=True)
    n.publish(dict(fields,state='RESTORING' if reason in ('PAIR-STOPPED','SERVICE-STOPPED','SUPERVISOR-RECOVERY') else 'ROLLED-BACK',
                   reason=reason,source=journal['source'],target=journal['target'],proof_scope=journal.get('proof_scope','router-probed-ipv4'),
                   kernel_proof=kernel_proof,original_restored=target==context['session_order'],vendor_rebuild=True))
