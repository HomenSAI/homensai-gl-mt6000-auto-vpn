# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""After a supervisor restart, finish an interrupted automatic switch to the reserve instead of rolling it back.

03.11.2026. Lua: lua/forward_resume.lua (same rules, same codes). Shared cases: tests/forward_resume_cases.json.

MT3000, 2.1.0-alpha5, 03.11.2026: the Auto process was SIGKILLed ~2.4 s into an automatic switch (journal APPLYING,
kernel already on the reserve) while the primary stayed down. The recovery rolled back onto the dead primary
(SUPERVISOR-RECOVERY), the pair cleanup stopped both clients (~24 s), the monitor's restart resume pressed Start, the
new session connected (~28 s) and waited for the vendor (~34 s), then Auto switched again: 128 s without internet on
the LAN (a normal failover ~20 s).

decide() accepts only: journal APPLYING or WAIT-CLIENT of a continuous pair (router-probed-ipv4); an automatic switch
to the reserve (no trial, manual request, return or reapply); no rollback started, no failure recorded, no earlier
resume of this tx; the same boot (a RAM file of this transaction - the apply progress names its tx or the monotonic
lease is the journal's - and the monotonic deadline no further than one transaction away: a power cut always rolls
back as before); at least MIN_LEFT seconds of the transaction left; the owner's Auto still wanted (resume marker, no
newer Stop latch, the service not stopping); the primary failing and the reserve healthy by a fresh live probe.
resume() then proves the live state again (the pair session of this switch unchanged, the vendor quiet, the diagnostic
identity the journal's, the live order exactly before or after, the kernel either the recorded pre-switch graph -
the writes are then redone exactly as child() does, under the new control revision - or already the reserve's,
attested, nothing written), records forward_resumed in the journal before any write (one resume per transaction),
and ends like attempt(): kernel attested target, VPN-only guard, WAIT-CLIENT, router probes confirm, COMMITTED with
reason SUPERVISOR-FORWARD-RESUMED. Any refusal goes to the unchanged rollback with the journal as written. The RAM
marker FILE lets the pair cleanup hand the reserve over to the monitor's restart Start (variant D) without a boot.
"""
import time

REASON='SUPERVISOR-FORWARD-RESUMED'
FILE='supervisor-forward.json'   # runtime (RAM): {tx,at=<monotonic>,outcome='committed'|'refused'} of this restart's resume
MIN_LEFT=15                      # seconds of the transaction (wall and monotonic) a resume needs at least
SILENT=('PHASE','NOT-PAIR')      # not a continuous-pair switch: the old recovery, nothing to log


def _num(value):
    return value if type(value) in (int,float) else None


def _fact(facts,name):
    value=facts.get(name)
    return value() if callable(value) else value


def decide(journal,facts):
    """-> None when the switch may be finished, else the refusal code (log only)."""
    if not isinstance(journal,dict) or journal.get('phase') not in ('APPLYING','WAIT-CLIENT'):return 'PHASE'
    ctx=journal.get('pair_transition')
    if not isinstance(ctx,dict) or journal.get('proof_scope','external-lan')!='router-probed-ipv4':return 'NOT-PAIR'
    if (journal.get('trial') is not False or journal.get('manual_request_id') is not None or journal.get('activation_reapply') is not None
            or journal.get('transition_source')!='automatic'):return 'NOT-AUTOMATIC'
    if ctx.get('destination_role')!='target' or ctx.get('before_policy_role')!='source' or journal.get('before')==journal.get('after'):
        return 'NOT-FORWARD'
    if any(isinstance(key,str) and key.startswith('restore') for key in journal):return 'ROLLBACK-STARTED'
    failures=journal.get('rollback_failures')
    if failures is None:failures=0
    if (journal.get('failure_code') is not None or journal.get('failure_detail') is not None or _num(failures) is None or failures!=0
            or journal.get('confirmed') is not None or journal.get('kernel_confirmed') is not None or journal.get('finished') is not None):
        return 'ROLLBACK-STARTED'
    if journal.get('forward_resumed') is not None:return 'ALREADY-RESUMED'
    md,deadline,started=_num(journal.get('monotonic_deadline')),_num(journal.get('deadline')),_num(journal.get('started'))
    wall,mono=_num(facts.get('wall')),_num(facts.get('mono'))
    from native_switch import TRANSACTION_SECONDS
    if not isinstance(journal.get('tx'),str) or facts.get('same_boot') is not True or md is None or mono is None or md-mono>TRANSACTION_SECONDS+1:
        return 'OTHER-BOOT'
    if deadline is None or started is None or wall is None or deadline-wall<MIN_LEFT or md-mono<MIN_LEFT:return 'EXPIRED'
    if facts.get('stopping') is True or facts.get('wanted') is not True:return 'OWNER-STOP'
    stopped=facts.get('stop_requested')
    if stopped is not None and (_num(stopped) is None or stopped>=started):return 'OWNER-STOP'
    if _fact(facts,'source_health') is not False:return 'SOURCE-NOT-FAILED'
    if _fact(facts,'reserve_health') is not True:return 'RESERVE-NOT-HEALTHY'
    return None


def facts(backend,journal):
    """The live facts of decide(); a Stop latch that cannot be read counts as a Stop."""
    import native_switch as n
    import boot_resume
    try:progress=n.read_json(n.RUNTIME/'native-apply-progress.json',{})
    except (OSError,ValueError):progress={}
    try:lease=n.read_json(n.RUNTIME/'native-lease.json',{})
    except (OSError,ValueError):lease={}
    data=lease.get('data') if isinstance(lease,dict) else None
    until=_num(journal.get('lease_monotonic_until'))
    same_boot=((isinstance(progress,dict) and isinstance(journal.get('tx'),str) and progress.get('tx')==journal['tx'])
               or (isinstance(data,dict) and until is not None and _num(data.get('monotonic_until'))==until))
    stop_requested=None
    path=n.PERSIST/'native-stop.json'
    if path.exists():
        try:row=n.read_json(path,None)
        except (OSError,ValueError):row=None
        stop_requested=_num(row.get('requested')) if isinstance(row,dict) else None
        if stop_requested is None:stop_requested='UNREADABLE'
    try:wanted,_=boot_resume.wanted(n.PERSIST)
    except (OSError,ValueError):wanted=False
    return {'same_boot':bool(same_boot),'wall':n.time.time(),'mono':n.time.monotonic(),'wanted':wanted is True,'stop_requested':stop_requested,
            'stopping':bool(n.STOP),'source_health':lambda:backend.health(journal['source']),'reserve_health':lambda:backend.health(journal['target'])}


def restarted(tx,committed=False):
    """This supervisor's recovery ran the forward resume of tx (finished or refused) within the pair's KEEP_SECONDS
    (monotonic): a restart without a boot, whose monitor restart resume presses the owner's Start."""
    import native_switch as n
    import pair_auto
    try:row=n.read_json(n.RUNTIME/FILE,{})
    except (OSError,ValueError):return False
    if not isinstance(tx,str) or not isinstance(row,dict) or row.get('tx')!=tx:return False
    if committed and row.get('outcome','committed')!='committed':return False
    try:now=pair_auto._uptime()
    except (OSError,ValueError):return False
    at=_num(row.get('at'))
    return type(now) in (int,float) and at is not None and at<=now and now-at<pair_auto.KEEP_SECONDS


def marked(tx):
    """This supervisor's recovery finished tx forward (COMMITTED) within the pair's KEEP_SECONDS (monotonic)."""
    return restarted(tx,committed=True)


def _settled_selection(backend):
    """diagnostic(), waiting (bounded, like the verify step of child()) while only the vendor is busy or settling."""
    import native_switch as n
    blockers,current=backend.diagnostic()
    until=n.time.monotonic()+n.VERIFY_VENDOR_WAIT
    while blockers and set(blockers)<=n.VERIFY_TRANSIENT and n.time.monotonic()<until and not n.STOP:
        n.time.sleep(2);blockers,current=backend.diagnostic()
    if blockers:raise n.Refused(blockers[0])
    if not isinstance(current,dict):raise n.Refused('PROFILE-IDENTITY-CHANGED')
    return current


def _same_identity(journal,ctx,current):
    from pair_policy import proof
    from failure_diagnosis import profile_identity
    if current.get('hash')!=journal.get('hash') or not journal.get('vendor_identity') or current.get('vendor_identity')!=journal.get('vendor_identity'):return False
    if current.get('process_bindings')!=journal.get('process_bindings'):return False
    if (current.get('source') or {}).get('id')!=journal.get('source') or (current.get('target') or {}).get('id')!=journal.get('target'):return False
    try:identity=proof(current)
    except (ValueError,TypeError,KeyError):return False
    if any(ctx.get(key)!=item for key,item in identity.items()):return False
    profiles=journal.get('vendor_profiles')
    if not isinstance(profiles,dict):return False
    for role in ('source','target'):
        found=profile_identity(current.get(role))
        if found is None or found!=profiles.get(role):return False
    return True


def resume(backend,journal):
    """-> (True, None) when COMMITTED; (False, code) when refused before any write; raises (coded) after."""
    import native_switch as n
    from auto_control import current_revision
    from pair_auto import read_state
    from pair_policy import metadata
    code=decide(journal,facts(backend,journal))
    if code:return False,code
    from_phase=journal['phase']
    revision=current_revision(n.RUNTIME)
    n.require_control_revision(revision)
    ctx=metadata(journal)
    # the pair session that made this switch, unchanged (fenced by this recovery only)
    state=read_state()
    if (not isinstance(state,dict) or state.get('phase') not in ('RUNNING','HELD') or state.get('id')!=journal.get('trial_nonce')
            or state.get('revision')!=journal.get('control_revision') or state.get('order')!=ctx['session_order'] or state.get('policy_hash')!=journal['hash']):
        return False,'PAIR-SESSION'
    # an rtp2.sh of the killed apply child finishes first (MT3000: quiet GL workers, a stable kernel graph; bounded)
    from rollback_recovery import vendor_settled
    vendor_settled(backend)
    try:current=_settled_selection(backend)
    except n.Refused as error:return False,str(error)
    if not _same_identity(journal,ctx,current):return False,'IDENTITY'
    n.bind_policy_context(backend,journal)
    order,fingerprint_hash=backend.order()
    if fingerprint_hash!=journal['hash']:return False,'ORDER'
    at_after=order==journal['after']
    if not at_after and order!=journal['before']:return False,'ORDER'
    fingerprint=backend.kernel_fingerprint()
    proof=backend.attest_policy(current)
    forward=at_after and proof.get('verified') is True and proof.get('role')=='target'
    untouched=(not forward and isinstance(fingerprint,str) and len(fingerprint)==64
               and fingerprint==journal.get('kernel_before_fingerprint'))
    if not forward and not untouched:return False,'KERNEL'
    if n.STOP:return False,'OWNER-STOP'
    # one resume per transaction: recorded before the first write
    try:progress=n.read_json(n.RUNTIME/'native-apply-progress.json',{})
    except (OSError,ValueError):progress={}
    n.require_control_revision(revision)
    journal['forward_resumed']={'time':n.time.time(),'from_phase':from_phase,'kernel':'reserve' if forward else 'untouched',
                                'stage':progress.get('stage') if isinstance(progress,dict) and isinstance(progress.get('stage'),str) else None}
    n.journal_write(journal)
    _log('SUPERVISOR-FORWARD: resuming %s from %s (kernel %s)'%(journal['tx'],from_phase,journal['forward_resumed']['kernel']))
    if untouched:
        # the writes of child(), from the recorded pre-switch graph only, fenced by the new revision (Stop wins).
        # The stock boot prefix of rtp2.sh is checked (and recreated) like the recovery's own rollback does, NOT through
        # rtp_boot.prepare(): prepare() requires a running owner pair intent of this revision, and serve() has just
        # rotated the revision and fenced the pair intent off (fence_recovery), so prepare() refused CLIENT-STOP on every
        # real restart (MT3000 2.1.0-alpha7, 03.11.2026: SIGKILL in APPLYING, kernel untouched -> rollback, 130 s).
        # The owner's will is proven by decide() (resume marker, no newer Stop latch, service not stopping) and every
        # write below stays fenced by the new revision, which an owner Stop rotates.
        from rtp_boot import recovery_prefix,ready
        from auto_control import control_lock
        with control_lock():
            n.require_control_revision(revision)
            try:recovery_prefix()
            except (OSError,ValueError):raise n.Refused('RTP-BOOT-PRECONDITION-UNVERIFIED') from None
        n.require_control_revision(revision)
        backend.guard(control_revision=revision)
        def write_command(args,timeout=5):
            n.require_control_revision(revision)
            if n.STOP:raise n.Refused('CLIENT-STOP')
            n.assert_selection(backend,current)
            n.require_control_revision(revision)
            if n.transaction_expired(journal):raise n.Refused('TRANSACTION-EXPIRED')
            if backend.kernel_fingerprint()!=journal.get('kernel_before_fingerprint'):raise n.Refused('KERNEL-POLICY-UNVERIFIED')
            if args[0]=='/usr/bin/rtp2.sh':
                if journal.get('monotonic_deadline') is None or journal['monotonic_deadline']-n.time.monotonic()<n.RTP_DISPATCH_RESERVE:
                    raise n.Refused('TRANSACTION-EXPIRED')
                try:ready()
                except (OSError,ValueError):raise n.Refused('RTP-BOOT-PRECONDITION-UNVERIFIED') from None
            if args[0] in ('/usr/bin/rtp2.sh','iptables-restore'):journal['rtp_dispatched']=True
            else:journal['forward_policy_touched']=True
            n.journal_write(journal)
            if args[0]=='/usr/bin/rtp2.sh':n.apply_progress(journal['tx'],'rtp-dispatch')
            output=n.forward_dispatch(args,revision,timeout)
            if args[0]=='/usr/bin/rtp2.sh':n.apply_progress(journal['tx'],'rtp-returned')
            return output
        if not at_after:backend.reorder(journal['after'],write_command=write_command)
        backend.apply(write_command=write_command)
        current=_settled_selection(backend)
        if not _same_identity(journal,ctx,current):raise n.Refused('PROFILE-IDENTITY-CHANGED')
    # from here exactly the end of attempt(): kernel proof, exit, VPN-only guard, router probes, COMMITTED
    n.require_control_revision(revision)
    if backend.order()!=(journal['after'],journal['hash']):raise n.Refused('POLICY-CHANGED-DURING-APPLY')
    def kernel_target():
        kernel=backend.attest_policy(dict(current,order=list(journal['after'])))
        if kernel.get('verified') is not True or kernel.get('role')!='target':raise n.Refused('KERNEL-POLICY-UNVERIFIED')
        return kernel
    kernel=kernel_target()
    target_exit=n.trace(current['target'])
    n.assert_selection(backend,current)
    n.require_control_revision(revision)
    backend.guard(backend.devices(),control_revision=revision)  # VPN-only on the tunnels: the LAN goes out through the reserve
    journal.update(phase='WAIT-CLIENT',expected_exit=target_exit);n.journal_write(journal)
    kind=n.transition_kind(current['source'],current['target'])
    def publish(value,completed=False):
        fields=n.pair_event_fields(journal,completed=True,outcome='committed') if completed else n.pair_event_fields(journal)
        value=dict(fields,**value)
        value.update(transition_source='automatic',destination_role='target',destination_profile_id=journal['target'])
        try:n.publish(value)
        except (n.Refused,OSError,ValueError,KeyError,TypeError):n.atomic_json(n.STATE,dict(value,time=n.time.time(),history_error='HISTORY-001'))
    publish({'state':'WAIT-CLIENT','tx':journal['tx'],'expected_exit':target_exit,'deadline':journal['deadline'],'source':journal['source'],
             'target':journal['target'],'trial':False,'reason':REASON,'transition_kind':kind})
    while not n.transaction_expired(journal) and not n.STOP:
        n.require_control_revision(revision)
        stopped=n.read_json(n.PERSIST/'native-stop.json',{})
        if stopped.get('requested',0)>=journal['started']:raise n.Refused('CLIENT-STOP')
        measured=n.probe(current['target'])
        n.require_control_revision(revision)
        if (measured.get('code') is None and measured.get('dns_ok') is True and measured.get('https_success',0)>=2
                and n.trace(current['target'])==target_exit):
            if backend.order()!=(journal['after'],journal['hash']):raise n.Refused('EXTERNAL-POLICY-CHANGE')
            kernel=kernel_target()
            n.assert_selection(backend,current)
            n.require_control_revision(revision)
            if backend.order()!=(journal['after'],journal['hash']):raise n.Refused('EXTERNAL-POLICY-CHANGE')
            # K5 (formal model 03.11.2026): the revision check and the COMMITTED write under the control lock, as attempt():
            # a Stop (it rotates the revision under this lock) is before (CLIENT-STOP, rollback) or after the commit
            from auto_control import control_lock
            with control_lock(n.RUNTIME):
                n.require_control_revision(revision)
                journal.update(phase='COMMITTED',confirmed=n.time.time(),reason=REASON);n.journal_write(journal)
            import pair_auto
            try:n.atomic_json(n.RUNTIME/FILE,{'tx':journal['tx'],'at':float(pair_auto._uptime()),'time':journal['confirmed'],'outcome':'committed'})
            except (OSError,ValueError):pass
            # as after attempt()'s COMMITTED: end the LAN flows still NATed to the primary (flow_reset.py; a code, never a failure)
            n.reset_old_flows(backend,journal,'target')
            publish({'state':'COMMITTED','tx':journal['tx'],'source':journal['source'],'target':journal['target'],'trial':False,'transition_kind':kind,
                     'reason':REASON,'readiness_verified':True,'kernel_policy_verified':True,'kernel_proof':kernel,
                     'guard':'VPN-only; IPv6 forwarded traffic blocked'},completed=True)
            return True,None
        n.time.sleep(1)
    raise n.Refused('CLIENT-CONFIRMATION-TIMEOUT')


def _log(line):
    """Best effort: a failing system log never changes the recovery (the rollback must still run)."""
    try:
        from pair_auto import _log as log
        log(line)
    except Exception:
        pass


def restart_of_this_boot(backend,journal):
    """A restart without a boot: a RAM file of this transaction (facts.same_boot) and the monotonic deadline no further
    than one transaction away (decide's OTHER-BOOT rule). After a boot the cleanup keeps its own boot window and boot
    resume state (pair_auto.boot_keep), so no refusal marker is written then."""
    from native_switch import TRANSACTION_SECONDS
    try:found=facts(backend,journal)
    except Exception:  # best effort: never a reason to keep the clients
        return False
    md,mono=_num(journal.get('monotonic_deadline')),_num(found.get('mono'))
    return found.get('same_boot') is True and md is not None and mono is not None and md-mono<=TRANSACTION_SECONDS+1


def attempt(backend,journal):
    """-> (True, None) when the switch was finished; else (False, why): logged, and the caller rolls back as before."""
    import native_switch as n
    try:done,code=resume(backend,journal)
    except n.Refused as error:done,code=False,str(error)
    except Exception as error:  # a bug here must never cost the proven rollback
        done,code=False,'ERROR %s'%type(error).__name__
    if done:
        _log('SUPERVISOR-FORWARD-RESUMED: %s committed on the reserve'%journal['tx'])
        return True,None
    if code not in SILENT:
        _log('SUPERVISOR-FORWARD: rollback (%s)'%code)
        # MT3000 2.1.0-alpha7 (03.11.2026): after the refused resume and the rollback, the pair cleanup of this restart
        # (uptime past the boot window) stopped both clients, the healthy reserve too (~20 s), and the restart Start
        # brought them up again (~26 s). The marker lets that cleanup keep them up for the restart Start like the boot
        # cleanup does (variant C, pair_auto.boot_keep: the owner's marker, no newer Stop latch, every client up, the
        # restart resume of this start not failed or skipped, KEEP_SECONDS; the VPN-only guard stays until then).
        try:
            import pair_auto
            if isinstance(journal,dict) and isinstance(journal.get('tx'),str) and restart_of_this_boot(backend,journal):
                n.atomic_json(n.RUNTIME/FILE,{'tx':journal['tx'],'at':float(pair_auto._uptime()),'outcome':'refused','code':str(code)})
        except Exception:  # best effort: the rollback must still run
            pass
    return False,code
