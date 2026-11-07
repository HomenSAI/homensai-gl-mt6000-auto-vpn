"""Fenced one-shot operator override inside the existing continuous pair.

Only the native supervisor dispatches. Stop revokes the same revision; queued or
claimed work is never replayed after process recovery. No external certificate.
"""
import json,math,re,subprocess,time,uuid

PENDING={'QUEUED','CLAIMED'}
STATES=PENDING|{'COMPLETED','REFUSED','CANCELLED','UNCONFIRMED'}


def path():
    from agent import RUNTIME
    return RUNTIME/'pair-manual-control.json'


def valid(row):
    basic=(isinstance(row,dict) and set(row) in ({'id','pair','revision','direction','state','requested','updated','selection','code'},{'id','pair','revision','direction','state','requested','updated','selection','code','request_source'})
        and ('request_source' not in row or isinstance(row['request_source'],str) and row['request_source'] in ('manual','test','programmatic','unknown'))
        and all(isinstance(row.get(key),str) and re.fullmatch('[a-f0-9]{32}',row[key]) for key in ('id','pair','revision'))
        and isinstance(row['direction'],str) and row['direction'] in ('primary','reserve','resume') and isinstance(row['state'],str) and row['state'] in STATES
        and all(type(row[key]) in (int,float) and math.isfinite(row[key]) and row[key]>0 for key in ('requested','updated'))
        and row['updated']>=row['requested'] and isinstance(row['selection'],dict)
        and (row['code'] is None or isinstance(row['code'],str) and re.fullmatch('[A-Z][A-Z0-9_-]{0,95}',row['code'])))
    if not basic:return False
    selected=row['selection']
    if row['direction']=='resume':return selected=={}
    if set(selected)=={'tx'}:return selected['tx'] is None or isinstance(selected['tx'],str) and re.fullmatch('[a-f0-9]{32}',selected['tx']) is not None
    return (set(selected)=={'hash','settings_hash','vendor_identity','source','target','tx'}
            and all(isinstance(selected[k],str) and re.fullmatch('[a-f0-9]{64}',selected[k]) for k in ('hash','settings_hash','vendor_identity'))
            and all(isinstance(selected[k],str) and re.fullmatch(r'(?:openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)',selected[k]) for k in ('source','target'))
            and selected['source']!=selected['target']
            and (selected['tx'] is None or isinstance(selected['tx'],str) and re.fullmatch('[a-f0-9]{32}',selected['tx'])))


def read():
    from agent import read_json
    row=read_json(path(),{})
    if row and not valid(row):raise ValueError('PAIR-MANUAL-STATE-UNVERIFIED')
    return row


def active(state,intent,revision):
    return (state.get('phase')=='RUNNING' and intent.get('mode')=='on'
            and state.get('id')==intent.get('id') and state.get('revision')==intent.get('revision')==revision)


def healthy(status,identifier,now,valid_for=90):
    profiles=status.get('profiles',[])
    if not isinstance(profiles,list):return False
    for row in profiles:
        if isinstance(row,dict) and row.get('id')==identifier:
            stamp=row.get('time')
            return type(stamp) in (int,float) and math.isfinite(stamp) and 0<=now-stamp<=valid_for and row.get('code') is None and row.get('dns_ok') is True and row.get('https_success',0)>=2
    return False


def public():
    try:row=read()
    except (OSError,ValueError):return {'state':'UNCONFIRMED','completed':False,'code':'PAIR-MANUAL-STATE-UNVERIFIED'}
    if not row:return {'state':'IDLE','completed':False}
    return {'state':row['state'],'direction':row['direction'],'request_id':row['id'],
            'requested_at':row['requested'],'updated_at':row['updated'],'request_source':row.get('request_source','unknown'),'completed':row['state']=='COMPLETED','code':row['code']}


def public_for_status(native=None,available=False):
    """Keep the last pair outcome visible even when Stop disables its buttons."""
    from manual_control import public_status
    pair_result=public();legacy=public_status()
    native=native if isinstance(native,dict) else {}
    def requested(row):
        value=row.get('requested_at')
        return value if type(value) in (int,float) and math.isfinite(value) else -1
    use_pair=(available or native.get('mode')=='continuous-pair'
              or requested(pair_result)>=0 and requested(pair_result)>=requested(legacy))
    return use_pair,pair_result if use_pair else legacy


ATTEST_CACHE_SECONDS=15


def attested(backend,journal,full=False):
    """Kernel attestation for the status poll, reused for 15 s in RAM.

    A full attestation costs ~5 s of CPU on the MT3000 and the UI polls every
    10 s; repeating it made the status call slow enough for the page to show
    stale data. Only the button availability uses it; every manual dispatch
    re-attests from scratch. A changed journal or policy order misses the cache.
    """
    from agent import RUNTIME,read_json,atomic_json
    path=RUNTIME/'pair-manual-kernel-cache.json'
    key=[journal.get('tx'),journal.get('phase'),list(backend.order()),sorted((backend.process_bindings or {}).items()) if isinstance(getattr(backend,'process_bindings',None),dict) else None]
    key=json.loads(json.dumps(key))  # compare in its stored JSON form: tuples come back as lists
    now=time.monotonic()
    try:
        row=read_json(path,{})
        if (isinstance(row,dict) and row.get('key')==key and type(row.get('at')) in (int,float)
                and 0<=now-row['at']<ATTEST_CACHE_SECONDS and isinstance(row.get('kernel'),dict)):return row['kernel']
    except (OSError,ValueError):pass
    kernel=backend.attest_policy()
    try:atomic_json(path,{'key':key,'at':now,'kernel':{k:v for k,v in kernel.items() if isinstance(v,(str,int,float,bool,list,type(None)))}})
    except (OSError,ValueError,TypeError):pass
    return kernel


def controls():
    from agent import RUNTIME,PERSIST,read_json
    from auto_control import current_revision
    import native_switch as n,pair_auto as pair
    now=time.time();result={'available':False,'mode':'continuous-pair','time':now}
    try:
        state=pair.read_state();revision=current_revision(RUNTIME)
        if not active(state,pair.intent(),revision):return result
        result.update(available=True,control_revision=revision,hold=state.get('manual_hold'))
        backend=n.Linux();n.bind_policy_context(backend,state)
        from observation_freshness import valid_for as observation_window
        settings=backend.policy()['settings'];valid_for=observation_window(settings)
        result['observation_valid_for']=valid_for
        native=read_json(n.STATE,{});status=read_json(RUNTIME/'status.json',{});journal=n.journal_read();queued=read()
        if not isinstance(native,dict) or not isinstance(status,dict):raise ValueError('PAIR-MANUAL-STATE-UNVERIFIED')
        fresh=type(native.get('time')) in (int,float) and 0<=now-native['time']<=30
        busy=bool(queued and queued['state'] in PENDING) or native.get('state') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING')
        reasons=['PAIR-MANUAL-BUSY'] if busy else ['PAIR-MANUAL-STALE'] if not fresh else []
        # Use the observed fixed pair's native IDs; final dispatch revalidates policy.
        source=native.get('source');target=native.get('target')
        primary=list(reasons);reserve=list(reasons)
        general=state.get('policy_roles') is not None
        if general:
            from pair_policy import state_order_matches
            if journal.get('phase') not in (None,'ROLLED-BACK','COMMITTED','HELD-ON-RESERVE') or not state_order_matches(state,journal,backend.order()):
                primary.append('TRANSACTION-IN-PROGRESS');reserve.append('TRANSACTION-IN-PROGRESS')
        else:
            if journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE'):primary.append('RETURN-NOT-APPLICABLE')
            if journal.get('phase') not in (None,'ROLLED-BACK'):reserve.append('TRANSACTION-IN-PROGRESS')
        if not healthy(status,source,now,valid_for):primary.append('SOURCE-NOT-HEALTHY')
        if not healthy(status,target,now,valid_for):reserve.append('PAIR-MANUAL-TARGET-UNHEALTHY')
        for side,identifier in ((primary,source),(reserve,target)):
            pinned=n.key_unaccepted(identifier)  # a button is refused only towards the channel with the unaccepted key
            if pinned:side.append(pinned)
        ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]})
        events=ledger.get('events')
        if events:events=pair.effective_events(ledger,now)  # BH3-03: ages on the monotonic clock of this boot
        if events:
            from recovery_settings import normalized
            policy=normalized(settings)
            events,permitted=pair.budget(events,now,policy['attempt_window']*60,policy['attempt_limit'])
        else:events,permitted=pair.budget(events,now)
        # During a transaction the buttons are blocked anyway; a full diagnostic
        # and attestation per UI poll (~7 s of CPU) would only slow the switch.
        busy_switch='TRANSACTION-IN-PROGRESS' in primary
        kernel=attested(backend,journal) if general and not busy_switch else {}
        known=kernel.get('role') if kernel.get('verified') is True and kernel.get('role') in ('source','target') else None
        if general and not busy_switch and known is None and kernel.get('repairable_missing') is not True:
            primary.append('KERNEL-POLICY-UNVERIFIED');reserve.append('KERNEL-POLICY-UNVERIFIED')
        if general and n.fast_switch_enabled():pass  # the instant owner switch is never rate limited (see consume)
        elif not permitted:
            if known!='target':reserve.append('PAIR-RATE-LIMIT')
            if general and known!='source':primary.append('PAIR-RATE-LIMIT')
        elif events:
            if now-events[-1]<max(policy['cooldown'],policy['min_dwell']):
                if known!='target':reserve.append('PAIR-MANUAL-COOLDOWN')
                if general and known!='source':primary.append('PAIR-MANUAL-COOLDOWN')
        result['instant']=general and n.fast_switch_enabled()  # the page shows the instant switch's short expected time
        result.update(primary={'allowed':not primary,'blockers':primary},reserve={'allowed':not reserve,'blockers':reserve},
                      resume={'allowed':not reasons and state.get('manual_hold') in ('source','target'),'blockers':reasons},blockers=reasons)
        return result
    except (OSError,ValueError,TypeError,KeyError,n.Refused):
        result.update(available=False,blockers=['PAIR-MANUAL-STATE-UNVERIFIED']);return result


def light_gate(direction,settings):
    """The first blocker of an instant click from RAM state only (no diagnostic, no kernel attestation), or None."""
    from agent import RUNTIME,read_json
    import native_switch as n
    from observation_freshness import valid_for as observation_window
    now=time.time();native=read_json(n.STATE,{});status=read_json(RUNTIME/'status.json',{});queued=read()
    if not isinstance(native,dict) or not isinstance(status,dict):return 'PAIR-MANUAL-STATE-UNVERIFIED'
    if queued and queued['state'] in PENDING or native.get('state') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING'):return 'PAIR-MANUAL-BUSY'
    if not (type(native.get('time')) in (int,float) and 0<=now-native['time']<=30):return 'PAIR-MANUAL-STALE'
    if n.journal_read().get('phase') not in (None,'ROLLED-BACK','COMMITTED','HELD-ON-RESERVE'):return 'TRANSACTION-IN-PROGRESS'
    target=native.get('source') if direction=='primary' else native.get('target')
    if not healthy(status,target,now,observation_window(settings)):
        return 'SOURCE-NOT-HEALTHY' if direction=='primary' else 'PAIR-MANUAL-TARGET-UNHEALTHY'
    return n.key_unaccepted(target)


CLIENT_REQUEST_ID='[A-Za-z0-9_-]{8,64}'
CLIENT_LEDGER_LIMIT=16


def client_request_valid(value):
    return isinstance(value,str) and re.fullmatch(CLIENT_REQUEST_ID,value) is not None


def ledger_path(runtime=None):
    from agent import RUNTIME
    return (RUNTIME if runtime is None else runtime)/'pair-manual-requests.json'


def ledger_read(runtime=None):
    """The answers already given to caller-supplied request ids (F-35), newest last. Raises on a damaged file.
    Lua: manual_request.ledger_read."""
    from agent import read_json
    data=read_json(ledger_path(runtime),{})
    if data=={}:return []
    entries=data.get('entries') if isinstance(data,dict) and set(data)=={'entries'} else None
    if (not isinstance(entries,list) or len(entries)>CLIENT_LEDGER_LIMIT
            or not all(isinstance(e,dict) and set(e)=={'client','reply'} and client_request_valid(e['client'])
                       and isinstance(e['reply'],dict) and type(e['reply'].get('accepted')) is bool for e in entries)):
        raise ValueError('PAIR-MANUAL-STATE-UNVERIFIED')
    return entries


# BH-07 (bug hunt 07.11.2026): a refusal for a condition that passes by itself (a speed test ending, another manual
# operation running, an unconfirmed answer after a storage error) is not kept for its id: the owner's Retry with the
# same id after a lost answer is decided afresh instead of replaying a stale refusal for ever. Accepted answers (they
# changed state: the no-double-switch guarantee) and lasting refusals are still kept and replayed. An entry of this kind
# written by an older version is ignored the same way. Lua: manual_request.TRANSIENT / transient_refusal.
TRANSIENT_REFUSALS=frozenset(('SPEED-BUSY','PAIR-MANUAL-BUSY','PAIR-MANUAL-REQUEST-UNCONFIRMED'))


def transient_refusal(reply):
    blockers=reply.get('blockers') if isinstance(reply,dict) else None
    return (isinstance(reply,dict) and reply.get('accepted') is False and isinstance(blockers,list) and len(blockers)>0
            and blockers[0] in TRANSIENT_REFUSALS)


def ledger_find(client,runtime=None):
    for entry in reversed(ledger_read(runtime)):
        if entry['client']==client:return None if transient_refusal(entry['reply']) else dict(entry['reply'],replayed=True)
    return None


def ledger_store_locked(client,reply,runtime=None):
    """Caller holds the control lock. Keeps the last CLIENT_LEDGER_LIMIT answers."""
    from agent import atomic_json
    entries=[e for e in ledger_read(runtime) if e['client']!=client][-(CLIENT_LEDGER_LIMIT-1):]
    atomic_json(ledger_path(runtime),{'entries':entries+[{'client':client,'reply':reply}]})


def request(direction,revision,request_source=None,client_request_id=None):
    """The owner's click. With a caller-supplied client_request_id (F-35) the first answer is kept and a repeated id
    gets that answer back (replayed: true) instead of a second action: a delayed retry of a Resume can never clear a
    newer hold. Without an id the behaviour is unchanged. Lua: manual_request.request (same ledger file)."""
    from agent import RUNTIME
    from auto_control import control_lock
    def refuse(code):return {'accepted':False,'queued':False,'completed':False,'blockers':[code]}
    if client_request_id is None:return _request(direction,revision,request_source,None)
    if not client_request_valid(client_request_id):return refuse('PAIR-MANUAL-FIELDS')
    try:
        stored=ledger_find(client_request_id)
        if stored is not None:return stored
    except (OSError,ValueError):return refuse('PAIR-MANUAL-STATE-UNVERIFIED')
    reply=_request(direction,revision,request_source,client_request_id)
    if reply.get('accepted') is True:return reply  # stored with its row under the same lock
    try:
        with control_lock(RUNTIME):
            stored=ledger_find(client_request_id)
            if stored is not None:return stored
            if not transient_refusal(reply):ledger_store_locked(client_request_id,reply)  # BH-07
    except (OSError,ValueError):pass
    return reply


def _request(direction,revision,request_source,client):
    from agent import RUNTIME,read_json,atomic_json
    from auto_control import control_lock,revision_locked,normalize_request_source
    import native_switch as n,pair_auto as pair
    def refuse(code):return {'accepted':False,'queued':False,'completed':False,'blockers':[code]}
    if direction not in ('primary','reserve','resume') or not isinstance(revision,str) or not re.fullmatch('[a-f0-9]{32}',revision):return refuse('PAIR-MANUAL-FIELDS')
    try:
        backend=n.Linux();n.bind_policy_context(backend,pair.read_state())
        settings=backend.policy()['settings']
        if settings.get('pair_auto_mode')!=pair.MODE:return refuse('PAIR-MODE-NOT-CONFIGURED')
        if direction!='resume' and n.fast_switch_enabled():
            # Instant switch: a light gate. beta9 measured 2.5-6 s here for the full button model (kernel attestation
            # under the monitor's load) although the supervisor proves everything again when it takes the click.
            code=light_gate(direction,settings)
            if code:return refuse(code)
        else:
            control=controls();choice=control.get(direction,{})
            if not control.get('available') or not choice.get('allowed'):return refuse((choice.get('blockers') or control.get('blockers') or ['PAIR-MANUAL-NOT-AVAILABLE'])[0])
        selection={}
        if direction!='resume':
            if n.fast_switch_enabled():
                # The supervisor diagnoses the pair itself when it consumes the click (well under a second later);
                # a second ~1 s diagnostic here only delayed the instant switch. The journal binds the click.
                selection={'tx':n.journal_read().get('tx')}
            else:
                blockers,chosen=backend.diagnostic()
                if blockers:return refuse(blockers[0])
                selection={k:chosen.get(k) for k in ('hash','settings_hash','vendor_identity')}
                selection.update(source=chosen['source']['id'],target=chosen['target']['id'],tx=n.journal_read().get('tx'))
        with control_lock(RUNTIME):
            from speed_pause import public as pause_status
            if pause_status().get('active'):return refuse('SPEED-BUSY')
            current=revision_locked(RUNTIME);state=pair.read_state()
            if current!=revision or not active(state,pair.intent(),revision):return refuse('CONTROL-REVISION-STALE')
            if client is not None:
                stored=ledger_find(client)  # the same id raced in meanwhile: its answer, never a second action
                if stored is not None:return stored
            old=read()
            if old and old['state'] in PENDING:return refuse('PAIR-MANUAL-BUSY')
            now=time.time();row={'id':uuid.uuid4().hex,'pair':state['id'],'revision':revision,'direction':direction,
                'state':'QUEUED','requested':now,'updated':now,'selection':selection,'code':None,'request_source':normalize_request_source(request_source)}
            atomic_json(path(),row)
            reply={'accepted':True,'queued':True,'completed':False,'request_id':row['id'],'control_revision':revision}
            if client is not None:ledger_store_locked(client,reply)
        return reply
    except (OSError,ValueError,KeyError,TypeError,n.Refused,subprocess.SubprocessError):return refuse('PAIR-MANUAL-REQUEST-UNCONFIRMED')


def terminalize_pending_locked(result,code,runtime=None):
    """Caller holds the control lock. Terminal outcomes are never rewritten."""
    from agent import RUNTIME,atomic_json,read_json
    if result not in ('CANCELLED','UNCONFIRMED') or code not in ('CONTROL-REVISION-STALE','PAIR-MANUAL-RECOVERED'):
        raise ValueError('PAIR-MANUAL-STATE-UNVERIFIED')
    target=(RUNTIME if runtime is None else runtime)/'pair-manual-control.json'
    row=read_json(target,{})
    if row and not valid(row):raise ValueError('PAIR-MANUAL-STATE-UNVERIFIED')
    if row and row['state'] in PENDING:
        row.update(state=result,updated=max(time.time(),row['requested']),code=code);atomic_json(target,row)
        return True
    return False


def recover():
    from auto_control import control_lock
    with control_lock():
        terminalize_pending_locked('UNCONFIRMED','PAIR-MANUAL-RECOVERED')


def expire_queued():
    """The 60 s of a queued click end outside consume too (review 04.11.2026, finding 4): a pass that fails before it
    never reached the expiry, the row stayed QUEUED and the page busy. Only an old row is touched, with consume's own
    result. Never fails a pass. Lua: manual.expire_queued."""
    from agent import RUNTIME,atomic_json
    from auto_control import control_lock
    def stale(row):
        return bool(row) and row['state']=='QUEUED' and not row['requested']<=time.time()<=row['requested']+60
    try:
        if not stale(read()):return False
        with control_lock(RUNTIME):
            row=read()
            if not stale(row):return False
            row.update(state='CANCELLED',updated=max(time.time(),row['requested']),code='PAIR-MANUAL-EXPIRED');atomic_json(path(),row)
        return True
    except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError):return False


def lease_until(settings,state):
    """The pair's current transaction lease when it still covers a whole transaction (saves a flash write)."""
    import native_switch as n
    try:until=float(settings.get('native_until') or 0)
    except (TypeError,ValueError):return None
    now=time.time()
    # An instant switch finishes in seconds; its journal deadline is min(lease, now+120), so 30 s of lease is plenty.
    if settings.get('native_trial')!=state.get('id') or not now+30<=until<=now+14400:return None
    return until


def consume(backend,state,settings,revision):
    from agent import RUNTIME,PERSIST,read_json,atomic_json
    from auto_control import control_lock,revision_locked,normalize_request_source
    import native_switch as n,pair_auto as pair
    row=read()
    if not row or row['state'] not in PENDING:return False
    with control_lock(RUNTIME):
        row=read()
        if not row or row['state'] not in PENDING:return False
        if row['state']=='CLAIMED':
            # Only this serialized supervisor claims requests and dispatch is
            # synchronous. A claim seen on the next tick was interrupted; it
            # is never permission to replay the action or keep buttons busy.
            terminalize_pending_locked('UNCONFIRMED','PAIR-MANUAL-RECOVERED')
            return True
        reason=None
        if revision_locked(RUNTIME)!=row['revision'] or row['pair']!=state['id']:reason='CONTROL-REVISION-STALE'
        elif not row['requested']<=time.time()<=row['requested']+60:reason='PAIR-MANUAL-EXPIRED'
        if reason:
            row.update(state='CANCELLED',updated=max(time.time(),row['requested']),code=reason);atomic_json(path(),row);return True
        row.update(state='CLAIMED',updated=time.time());atomic_json(path(),row)
    n.manual_stamp('claimed',row['id'])
    def finish(result,code=None):
        with control_lock(RUNTIME):
            current=read()
            if not current or current['id']!=row['id'] or current['state'] not in PENDING:return
            if revision_locked(RUNTIME)!=revision:result='CANCELLED';code='CONTROL-REVISION-STALE'
            current.update(state=result,code=code,updated=max(time.time(),row['requested']));atomic_json(path(),current)
    try:
        pair.require_running(revision)
        if row['direction']=='resume':
            with control_lock(RUNTIME):
                pair.require_running(revision);state.pop('manual_hold',None);state.pop('manual_selection',None);pair.save(state)
            finish('COMPLETED');return True
        n.bind_policy_context(backend,state)
        blockers,selection=backend.diagnostic();expected=row['selection']
        n.manual_stamp('diagnosed')
        if blockers:raise n.Refused(blockers[0])
        if set(expected)!={'tx'} and (any(selection.get(k)!=expected.get(k) for k in ('hash','settings_hash','vendor_identity'))
                                      or any(selection[k]['id']!=expected.get(k) for k in ('source','target'))):
            raise n.Refused('MANUAL-CONFIG-CHANGED')
        journal=n.journal_read()
        if state.get('policy_roles') is not None:
            from pair_policy import metadata,proof,state_order_matches
            if (proof(selection)!=state['policy_roles'] or journal.get('tx')!=expected.get('tx')
                    or journal.get('phase') not in (None,'ROLLED-BACK','COMMITTED','HELD-ON-RESERVE')
                    or not state_order_matches(state,journal,backend.order())):
                raise n.Refused('MANUAL-CONFIG-CHANGED')
            hold='source' if row['direction']=='primary' else 'target'
            from observation_freshness import valid_for as observation_window
            instant=n.fast_switch_enabled()
            alive=instant and healthy(read_json(RUNTIME/'status.json',{}),selection[hold]['id'],time.time(),observation_window(settings))
            if not alive and backend.health(selection[hold]['id']) is not True:
                raise n.Refused('SOURCE-NOT-HEALTHY' if hold=='source' else 'PAIR-MANUAL-TARGET-UNHEALTHY')
            kernel=backend.attest_policy(selection)
            n.manual_stamp('attested')
            if kernel.get('verified') is True and kernel.get('role')==hold:
                from failure_diagnosis import profile_identity
                if kernel.get('policy_hash')!=selection['hash'] or kernel.get('order')!=selection['order']:
                    raise n.Refused('KERNEL-POLICY-UNVERIFIED')
                selected={'request_id':row['id'],'role':hold,'order':list(selection['order']),'hash':selection['hash'],
                          'vendor_identity':selection['vendor_identity'],'profiles':{key:profile_identity(selection[key]) for key in ('source','target')}}
                if any(not isinstance(value,dict) for value in selected['profiles'].values()):raise n.Refused('PROFILE-IDENTITY-CHANGED')
                with control_lock(RUNTIME):
                    pair.require_running(revision);state['manual_hold']=hold;state['manual_hold_source']=row.get('request_source','unknown')
                    pair.remember_selected(state,kernel)
                    state['manual_selection']=selected;pair.save(state)
                n.publish({'state':'OBSERVING','mode':'continuous-pair','proof_scope':pair.MODE,'source':selection['source']['id'],'target':selection['target']['id'],
                           'reason':'MANUAL-ALREADY-SELECTED','manual':True,'readiness_verified':True,'kernel_policy_verified':True,'kernel_proof':kernel,
                           'route_changed':False,'transition_completed':True,'transition_outcome':'policy-verified','transition_source':row.get('request_source','unknown')})
                finish('COMPLETED','MANUAL-ALREADY-SELECTED');return True
            if kernel.get('verified') is not True and kernel.get('repairable_missing') is not True:
                raise n.Refused('KERNEL-POLICY-UNVERIFIED')
            pinned=n.key_unaccepted(selection[hold]['id'])  # before the lease and the budget; attempt() and instant_manual() refuse it too
            if pinned:raise n.Refused(pinned)
            if instant:
                # Owner button (30 Oct 2026): a manual switch to a live channel happens at once. The attempt budget and
                # cooldown exist against automatic flapping; a person's click neither waits for them nor uses them up.
                pair.require_running(revision)
                until=lease_until(settings,state) or pair.configure_lease(state)
                n.manual_stamp('lease')
                kernel=n.instant_manual(backend,selection,until,revision,row['id'],row.get('request_source'),hold,state['order'],kernel_before=kernel)
                fresh=selection
            else:
                from recovery_settings import normalized
                recovery=normalized(settings)
                pair.require_running(revision);now=time.time();ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]})
                events,permitted=pair.budget(pair.effective_events(ledger,now),now,recovery['attempt_window']*60,recovery['attempt_limit'])
                if not permitted:raise n.Refused('PAIR-RATE-LIMIT')
                if events and now-events[-1]<max(recovery['cooldown'],recovery['min_dwell']):raise n.Refused('PAIR-MANUAL-COOLDOWN')
                until=pair.configure_lease(state);blockers,fresh=backend.diagnostic()
                if blockers:raise n.Refused(blockers[0])
                if (proof(fresh)!=state['policy_roles'] or any(fresh.get(k)!=expected.get(k) for k in ('hash','settings_hash','vendor_identity'))
                        or not state_order_matches(state,journal,backend.order())):raise n.Refused('MANUAL-CONFIG-CHANGED')
                def charge_dispatched():
                    pair.require_running(revision);stamp=time.time();fresh_ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]})
                    charged,allowed=pair.budget(pair.effective_events(fresh_ledger,stamp),stamp,recovery['attempt_window']*60,recovery['attempt_limit'])
                    if not allowed:raise n.Refused('PAIR-RATE-LIMIT')
                    if charged and stamp-charged[-1]<max(recovery['cooldown'],recovery['min_dwell']):raise n.Refused('PAIR-MANUAL-COOLDOWN')
                    pair.ledger_charge(charged,stamp)
                n.attempt(backend,fresh,until,False,control_revision=revision,manual_request_id=row['id'],
                          request_source=row.get('request_source'),pair_destination=hold,pair_session_order=state['order'],on_dispatch=charge_dispatched)
            journal=n.journal_read();context=metadata(journal)
            if (context is None or context['destination_role']!=hold or context['session_order']!=state['order']
                    or journal.get('manual_request_id')!=row['id'] or journal.get('phase')!='HELD-ON-RESERVE'
                    or not journal.get('confirmed') or backend.order()!=(journal['after'],journal['hash'])):
                raise n.Refused('MANUAL-COMPLETION-UNVERIFIED')
            if not instant:kernel=backend.attest_policy(dict(fresh,order=list(journal['after'])))  # instant_manual attested after its write
            if kernel.get('verified') is not True or kernel.get('role')!=hold:raise n.Refused('KERNEL-POLICY-UNVERIFIED')
        elif row['direction']=='reserve':
            if journal.get('phase') not in (None,'ROLLED-BACK') or backend.order()!=(state['order'],state['policy_hash']):raise n.Refused('TRANSACTION-IN-PROGRESS')
            pinned=n.key_unaccepted(selection['target']['id'])
            if pinned:raise n.Refused(pinned)
            if backend.health(selection['target']['id']) is not True:raise n.Refused('PAIR-MANUAL-TARGET-UNHEALTHY')
            from recovery_settings import normalized
            recovery=normalized(settings)
            pair.require_running(revision);now=time.time();ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]});events,permitted=pair.budget(pair.effective_events(ledger,now),now,recovery['attempt_window']*60,recovery['attempt_limit'])
            if not permitted:raise n.Refused('PAIR-RATE-LIMIT')
            if events and now-events[-1]<max(recovery['cooldown'],recovery['min_dwell']):raise n.Refused('PAIR-MANUAL-COOLDOWN')
            pair.require_running(revision);pair.ledger_charge(events,now)
            until=pair.configure_lease(state);blockers,selection=backend.diagnostic()
            if blockers:raise n.Refused(blockers[0])
            n.attempt(backend,selection,until,False,control_revision=revision,manual_request_id=row['id'],request_source=row.get('request_source'))
            journal=n.journal_read()
            if journal.get('manual_request_id')!=row['id'] or journal.get('phase')!='HELD-ON-RESERVE' or not journal.get('confirmed') or backend.order()!=(journal['after'],journal['hash']):raise n.Refused('MANUAL-COMPLETION-UNVERIFIED')
            hold='target'
        else:
            if journal.get('tx')!=expected.get('tx') or journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE'):raise n.Refused('RETURN-TRANSACTION-MISMATCH')
            pinned=n.key_unaccepted(selection['source']['id'])
            if pinned:raise n.Refused(pinned)
            handled,_=n.handle_return(backend,journal,{'time':row['requested'],'tx':journal['tx']},0,control_revision=revision)
            from manual_dispatch import _confirmed_return
            record={'requested_at':row['requested'],'transaction_id':journal['tx'],'source_id':selection['source']['id'],'target_id':selection['target']['id']}
            if not handled or not _confirmed_return(record,read_json(n.return_result_path(),{}),n.journal_read(),backend.order(),time.time()):raise n.Refused('RETURN-UNCONFIRMED')
            hold='source'
        with control_lock(RUNTIME):
            pair.require_running(revision);state.pop('manual_selection',None);state['manual_hold']=hold;state['manual_hold_source']=row.get('request_source','unknown')
            if state.get('policy_roles') is not None:
                from failure_diagnosis import profile_identity
                pair.remember_selected(state,kernel)
                state['manual_selection']={'request_id':row['id'],'role':hold,'order':list(journal['after']),'hash':journal['hash'],
                                           'vendor_identity':fresh['vendor_identity'],'profiles':{key:profile_identity(fresh[key]) for key in ('source','target')}}
            pair.save(state)
        n.manual_stamp('saved')
        fields=n.pair_event_fields(journal,completed=True,outcome='committed') if state.get('policy_roles') is not None else {}
        if journal.get('manual_instant') is True:fields.update(manual_instant=True,switch_seconds=journal.get('instant_seconds'))
        n.publish(dict(fields,state='COMMITTED' if hold=='target' else 'OBSERVING' if state.get('policy_roles') is not None else 'ROLLED-BACK',mode='continuous-pair',proof_scope=pair.MODE,
                   source=selection['source']['id'],target=selection['target']['id'],reason='OPERATOR-MANUAL',manual=True,
                   readiness_verified=state.get('policy_roles') is not None,kernel_policy_verified=state.get('policy_roles') is not None,
                   kernel_proof=kernel if state.get('policy_roles') is not None else None,
                   transition_source=row.get('request_source','unknown'),original_restored=backend.order()==(state['order'],state['policy_hash'])))
        finish('COMPLETED');n.manual_stamp('done')
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        code=str(error) if isinstance(error,n.Refused) and re.fullmatch('[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'PAIR-MANUAL-UNCONFIRMED'
        finish('REFUSED' if isinstance(error,n.Refused) else 'UNCONFIRMED',code)
    return True


def hold_verified(backend,state,journal,settings,status,hold,resolved,now,age,required):
    """Finding 7 in a manual hold (the same rule as native_switch.committed_recovery_decision): the held channel is the
    recorded one, or the vendor rebuilt it. Only vendor_generation changed, the vendor is quiet (READY): a healthy streak of
    the NEW generation proves it (the journal proof is rebound, a primary hold may sit on a ROLLED-BACK journal), a
    failure streak of the new generation is left to the caller's failure check, which releases the hold. False: unknown.
    required: the journal must hold a proof for this role. Lua: manual.hold_verified."""
    import native_switch as n,pair_auto as pair
    from failure_diagnosis import profile_identity
    from failover_plan import streak
    from recovery_settings import normalized
    expected=(journal.get('vendor_profiles') or {}).get(hold);profile=resolved.get(hold)
    if resolved['coordination']['state']!='READY' or profile is None or profile.get('id')!=journal[hold]:return False
    if expected is None:return not required
    live=profile_identity(profile)
    if live==expected:return True
    if live is None or any(live.get(key)!=expected.get(key) for key in n.RESERVE_STABLE):return False
    policy=normalized(settings);samples=status.get('samples',[])
    if streak(samples,profile['id'],policy['failures'],now,age,False,profile):return True
    if not streak(samples,profile['id'],policy['successes'],now,age,True,profile):return False
    pair.reserve_rebound(backend,state.get('revision'),settled=True)
    return True


def hold_released(backend,state,journal,settings,status,now):
    """Finding 7: a held reserve of unknown identity is no reason to stay on it once the automatic rule returns to a stably
    healthy primary (committed_recovery_decision: min_dwell, max(primary_stable, hold), the model gate, the owner's
    hold_reserve). The hold ends here; the same tick then takes that guarded return. Lua: manual.hold_released."""
    import native_switch as n,pair_auto as pair
    decision=n.committed_recovery_decision(backend,journal,settings,status.get('samples',[]),now,status,hold=pair.ledger_hold(settings,now))
    if decision['action']!='RESTORE-PRIMARY':return False
    state.pop('manual_hold',None);pair.save(state)
    return True


def held_reserve(backend,state,journal,settings,status):
    import native_switch as n,pair_auto as pair
    from pair_policy import metadata,current_role,state_order_matches
    from observation_freshness import valid_for,settle_for
    n.bind_policy_context(backend,state)
    adopted=state.get('manual_selection')
    if isinstance(adopted,dict) and state.get('manual_hold')==adopted.get('role'):
        blockers,selection=backend.diagnostic()
        if blockers:raise n.Refused(blockers[0])
        kernel=backend.attest_policy(selection)
        from failure_diagnosis import profile_identity
        if kernel.get('verified') is not True:return False  # The supervisor may repair only wholly absent stock rules.
        current=profile_identity(selection[adopted['role']]);expected=adopted['profiles'][adopted['role']]
        if (kernel.get('role')!=adopted['role']
                or backend.order()!=(adopted['order'],adopted['hash']) or current is None
                or any(current.get(key)!=expected.get(key) for key in ('id','protocol','interface','vendor_tunnel_id'))):
            raise n.Refused('PAIR-MANUAL-HOLD-UNVERIFIED')
        if backend.health(selection[adopted['role']]['id']) is not True:
            state.pop('manual_hold',None);state.pop('manual_selection',None);pair.save(state);return False
        if current!=expected:
            adopted['profiles'][adopted['role']]=current;pair.save(state)
        pair.resume_running(state)
        n.publish({'state':'OBSERVING','reason':'PAIR-MANUAL-HOLD-RESERVE' if adopted['role']=='target' else 'PAIR-MANUAL-HOLD-PRIMARY',
                   'manual':True,'source':selection['source']['id'],'target':selection['target']['id'],
                   'readiness_verified':True,'kernel_policy_verified':True,'kernel_proof':kernel,'transition_source':state.get('manual_hold_source','unknown'),'mode':'continuous-pair','proof_scope':pair.MODE})
        return True
    context=metadata(journal)
    if state.get('manual_hold') in ('source','target') and context is not None:
        hold=state['manual_hold']
        if (not journal.get('confirmed') or current_role(journal)!=hold
                or not state_order_matches(state,journal,backend.order())):raise n.Refused('PAIR-MANUAL-HOLD-UNVERIFIED')
        kernel=backend.attest_policy()
        if kernel.get('verified') is not True:return False
        from failure_diagnosis import resolve_pair,scoped_samples
        from recovery_settings import normalized
        from failover_plan import streak
        now=time.time();age=valid_for(settings)
        resolved=resolve_pair(status,settings,now,age,settle_for(settings))
        profile=resolved.get(hold)
        if not hold_verified(backend,state,journal,settings,status,hold,resolved,now,age,True):
            if hold=='target' and hold_released(backend,state,journal,settings,status,now):return False
            n.publish({'state':'BLOCKED','reason':'PROFILE-IDENTITY-CHANGED','blockers':['PROFILE-IDENTITY-CHANGED'],
                       'source':journal['source'],'target':journal['target'],'mode':'continuous-pair','proof_scope':pair.MODE})
            return True
        if streak(scoped_samples(status.get('samples',[]),profile),profile['id'],normalized(settings)['failures'],now,age,False,profile):
            state.pop('manual_hold',None);pair.save(state);return False
        pair.resume_running(state)
        n.publish({'state':'COMMITTED' if hold=='target' else 'OBSERVING','reason':'PAIR-MANUAL-HOLD-RESERVE' if hold=='target' else 'PAIR-MANUAL-HOLD-PRIMARY',
                   'manual':True,'transition_source':state.get('manual_hold_source','unknown'),'source':journal['source'],'target':journal['target'],
                   'readiness_verified':True,'kernel_policy_verified':True,'kernel_proof':kernel,'mode':'continuous-pair','proof_scope':pair.MODE})
        return True
    if state.get('manual_hold')!='target':return False
    if journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE') or not journal.get('confirmed') or backend.order()!=(journal['after'],journal['hash']):raise n.Refused('PAIR-MANUAL-HOLD-UNVERIFIED')
    from recovery_settings import normalized
    from failure_diagnosis import scoped_samples,resolve_pair
    from failover_plan import streak
    row=next((p for p in status.get('profiles',[]) if p.get('id')==journal['target']),None)
    recovery=normalized(settings);now=time.time()
    age=valid_for(settings)
    resolved=resolve_pair(status,settings,now,age,settle_for(settings))
    if not hold_verified(backend,state,journal,settings,status,'target',resolved,now,age,False):
        if hold_released(backend,state,journal,settings,status,now):return False
        n.publish({'state':'DEGRADED-ON-RESERVE','reason':'RESERVE-IDENTITY-UNKNOWN','manual':True,'transition_source':state.get('manual_hold_source','unknown'),'source':journal['source'],'target':journal['target'],'mode':'continuous-pair','proof_scope':pair.MODE})
        return True
    failed=row and streak(scoped_samples(status.get('samples',[]),row),row['id'],recovery['failures'],now,age,False,row)
    if failed:
        state.pop('manual_hold',None);pair.save(state);return False
    n.publish({'state':'COMMITTED','reason':'PAIR-MANUAL-HOLD-RESERVE','manual':True,'transition_source':state.get('manual_hold_source','unknown'),'source':journal['source'],'target':journal['target'],
               'mode':'continuous-pair','proof_scope':pair.MODE})
    return True
