"""Fenced one-shot operator override inside the existing continuous pair.

Only the native supervisor dispatches. Stop revokes the same revision; queued or
claimed work is never replayed after process recovery. No external certificate.
"""
import math,re,subprocess,time,uuid

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


def healthy(status,identifier,now):
    profiles=status.get('profiles',[])
    if not isinstance(profiles,list):return False
    for row in profiles:
        if isinstance(row,dict) and row.get('id')==identifier:
            stamp=row.get('time')
            return type(stamp) in (int,float) and math.isfinite(stamp) and 0<=now-stamp<=90 and row.get('code') is None and row.get('dns_ok') is True and row.get('https_success',0)>=2
    return False


def public():
    try:row=read()
    except (OSError,ValueError):return {'state':'UNCONFIRMED','completed':False,'code':'PAIR-MANUAL-STATE-UNVERIFIED'}
    if not row:return {'state':'IDLE','completed':False}
    return {'state':row['state'],'direction':row['direction'],'request_id':row['id'],
            'requested_at':row['requested'],'updated_at':row['updated'],'request_source':row.get('request_source','unknown'),'completed':row['state']=='COMPLETED','code':row['code']}


def controls():
    from agent import RUNTIME,PERSIST,read_json
    from auto_control import current_revision
    import native_switch as n,pair_auto as pair
    now=time.time();result={'available':False,'mode':'continuous-pair','time':now}
    try:
        state=pair.read_state();revision=current_revision(RUNTIME)
        if not active(state,pair.intent(),revision):return result
        result.update(available=True,control_revision=revision,hold=state.get('manual_hold'))
        native=read_json(n.STATE,{});status=read_json(RUNTIME/'status.json',{});journal=n.journal_read();queued=read()
        if not isinstance(native,dict) or not isinstance(status,dict):raise ValueError('PAIR-MANUAL-STATE-UNVERIFIED')
        fresh=type(native.get('time')) in (int,float) and 0<=now-native['time']<=30
        busy=bool(queued and queued['state'] in PENDING) or native.get('state') in ('ARMED','APPLYING','WAIT-CLIENT','RESTORING')
        reasons=['PAIR-MANUAL-BUSY'] if busy else ['PAIR-MANUAL-STALE'] if not fresh else []
        # Use the observed fixed pair's native IDs; final dispatch revalidates policy.
        source=native.get('source');target=native.get('target')
        primary=list(reasons);reserve=list(reasons)
        if journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE'):primary.append('RETURN-NOT-APPLICABLE')
        if journal.get('phase') not in (None,'ROLLED-BACK'):reserve.append('TRANSACTION-IN-PROGRESS')
        if not healthy(status,source,now):primary.append('SOURCE-NOT-HEALTHY')
        if not healthy(status,target,now):reserve.append('PAIR-MANUAL-TARGET-UNHEALTHY')
        ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]});events,permitted=pair.budget(ledger.get('events'),now)
        if not permitted:reserve.append('PAIR-RATE-LIMIT')
        elif events:
            from recovery_settings import normalized
            policy=normalized(n.Linux().policy()['settings'])
            if now-events[-1]<max(policy['cooldown'],policy['min_dwell']):reserve.append('PAIR-MANUAL-COOLDOWN')
        result.update(primary={'allowed':not primary,'blockers':primary},reserve={'allowed':not reserve,'blockers':reserve},
                      resume={'allowed':not reasons and state.get('manual_hold') in ('source','target'),'blockers':reasons},blockers=reasons)
        return result
    except (OSError,ValueError,TypeError,KeyError,n.Refused):
        result.update(available=False,blockers=['PAIR-MANUAL-STATE-UNVERIFIED']);return result


def request(direction,revision,request_source=None):
    from agent import RUNTIME,read_json,atomic_json
    from auto_control import control_lock,revision_locked,normalize_request_source
    import native_switch as n,pair_auto as pair
    def refuse(code):return {'accepted':False,'queued':False,'completed':False,'blockers':[code]}
    if direction not in ('primary','reserve','resume') or not isinstance(revision,str) or not re.fullmatch('[a-f0-9]{32}',revision):return refuse('PAIR-MANUAL-FIELDS')
    try:
        backend=n.Linux();settings=backend.policy()['settings']
        if settings.get('pair_auto_mode')!=pair.MODE:return refuse('PAIR-MODE-NOT-CONFIGURED')
        control=controls();choice=control.get(direction,{})
        if not control.get('available') or not choice.get('allowed'):return refuse((choice.get('blockers') or control.get('blockers') or ['PAIR-MANUAL-NOT-AVAILABLE'])[0])
        selection={}
        if direction!='resume':
            blockers,chosen=backend.diagnostic()
            if blockers:return refuse(blockers[0])
            selection={k:chosen.get(k) for k in ('hash','settings_hash','vendor_identity')}
            selection.update(source=chosen['source']['id'],target=chosen['target']['id'],tx=n.journal_read().get('tx'))
        with control_lock(RUNTIME):
            from speed_pause import public as pause_status
            if pause_status().get('active'):return refuse('SPEED-BUSY')
            current=revision_locked(RUNTIME);state=pair.read_state()
            if current!=revision or not active(state,pair.intent(),revision):return refuse('CONTROL-REVISION-STALE')
            old=read()
            if old and old['state'] in PENDING:return refuse('PAIR-MANUAL-BUSY')
            now=time.time();row={'id':uuid.uuid4().hex,'pair':state['id'],'revision':revision,'direction':direction,
                'state':'QUEUED','requested':now,'updated':now,'selection':selection,'code':None,'request_source':normalize_request_source(request_source)}
            atomic_json(path(),row)
        return {'accepted':True,'queued':True,'completed':False,'request_id':row['id'],'control_revision':revision}
    except (OSError,ValueError,KeyError,TypeError,n.Refused,subprocess.SubprocessError):return refuse('PAIR-MANUAL-REQUEST-UNCONFIRMED')


def recover():
    from agent import atomic_json
    row=read()
    if row and row['state'] in PENDING:
        row.update(state='UNCONFIRMED',updated=max(time.time(),row['requested']),code='PAIR-MANUAL-RECOVERED');atomic_json(path(),row)


def consume(backend,state,settings,revision):
    from agent import RUNTIME,PERSIST,read_json,atomic_json
    from auto_control import control_lock,revision_locked,normalize_request_source
    import native_switch as n,pair_auto as pair
    row=read()
    if not row or row['state'] not in PENDING:return False
    with control_lock(RUNTIME):
        row=read()
        if not row or row['state']!='QUEUED':return False
        reason=None
        if revision_locked(RUNTIME)!=row['revision'] or row['pair']!=state['id']:reason='CONTROL-REVISION-STALE'
        elif not row['requested']<=time.time()<=row['requested']+60:reason='PAIR-MANUAL-EXPIRED'
        if reason:
            row.update(state='CANCELLED',updated=max(time.time(),row['requested']),code=reason);atomic_json(path(),row);return True
        row.update(state='CLAIMED',updated=time.time());atomic_json(path(),row)
    def finish(result,code=None):
        with control_lock(RUNTIME):
            current=read()
            if not current or current['id']!=row['id']:return
            if revision_locked(RUNTIME)!=revision:result='CANCELLED';code='CONTROL-REVISION-STALE'
            current.update(state=result,code=code,updated=max(time.time(),row['requested']));atomic_json(path(),current)
    try:
        pair.require_running(revision)
        if row['direction']=='resume':
            with control_lock(RUNTIME):
                pair.require_running(revision);state.pop('manual_hold',None);pair.save(state)
            finish('COMPLETED');return True
        blockers,selection=backend.diagnostic();expected=row['selection']
        if blockers:raise n.Refused(blockers[0])
        if any(selection.get(k)!=expected.get(k) for k in ('hash','settings_hash','vendor_identity')) or any(selection[k]['id']!=expected.get(k) for k in ('source','target')):
            raise n.Refused('MANUAL-CONFIG-CHANGED')
        journal=n.journal_read()
        if row['direction']=='reserve':
            if journal.get('phase') not in (None,'ROLLED-BACK') or backend.order()!=(state['order'],state['policy_hash']):raise n.Refused('TRANSACTION-IN-PROGRESS')
            if backend.health(selection['target']['id']) is not True:raise n.Refused('PAIR-MANUAL-TARGET-UNHEALTHY')
            pair.require_running(revision);now=time.time();ledger=read_json(PERSIST/'pair-auto-budget.json',{'events':[]});events,permitted=pair.budget(ledger.get('events'),now)
            from recovery_settings import normalized
            recovery=normalized(settings)
            if not permitted:raise n.Refused('PAIR-RATE-LIMIT')
            if events and now-events[-1]<max(recovery['cooldown'],recovery['min_dwell']):raise n.Refused('PAIR-MANUAL-COOLDOWN')
            pair.require_running(revision);atomic_json(PERSIST/'pair-auto-budget.json',{'events':events+[now]})
            until=pair.configure_lease(state);blockers,selection=backend.diagnostic()
            if blockers:raise n.Refused(blockers[0])
            n.attempt(backend,selection,until,False,control_revision=revision,manual_request_id=row['id'],request_source=row.get('request_source'))
            journal=n.journal_read()
            if journal.get('manual_request_id')!=row['id'] or journal.get('phase')!='HELD-ON-RESERVE' or not journal.get('confirmed') or backend.order()!=(journal['after'],journal['hash']):raise n.Refused('MANUAL-COMPLETION-UNVERIFIED')
            hold='target'
        else:
            if journal.get('tx')!=expected.get('tx') or journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE'):raise n.Refused('RETURN-TRANSACTION-MISMATCH')
            handled,_=n.handle_return(backend,journal,{'time':row['requested'],'tx':journal['tx']},0,control_revision=revision)
            from manual_dispatch import _confirmed_return
            record={'requested_at':row['requested'],'transaction_id':journal['tx'],'source_id':expected['source'],'target_id':expected['target']}
            if not handled or not _confirmed_return(record,read_json(n.return_result_path(),{}),n.journal_read(),backend.order(),time.time()):raise n.Refused('RETURN-UNCONFIRMED')
            hold='source'
        with control_lock(RUNTIME):
            pair.require_running(revision);state['manual_hold']=hold;state['manual_hold_source']=row.get('request_source','unknown');pair.save(state)
        n.publish({'state':'COMMITTED' if hold=='target' else 'ROLLED-BACK','mode':'continuous-pair','proof_scope':pair.MODE,
                   'source':expected['source'],'target':expected['target'],'reason':'OPERATOR-MANUAL',
                   'manual':True,'transition_source':row.get('request_source','unknown'),'original_restored':hold=='source'})
        finish('COMPLETED')
    except (n.Refused,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        code=str(error) if isinstance(error,n.Refused) and re.fullmatch('[A-Z][A-Z0-9_-]{0,95}',str(error)) else 'PAIR-MANUAL-UNCONFIRMED'
        finish('REFUSED' if isinstance(error,n.Refused) else 'UNCONFIRMED',code)
    return True


def held_reserve(backend,state,journal,settings,status):
    import native_switch as n,pair_auto as pair
    if state.get('manual_hold')!='target':return False
    if journal.get('phase') not in ('COMMITTED','HELD-ON-RESERVE') or not journal.get('confirmed') or backend.order()!=(journal['after'],journal['hash']):raise n.Refused('PAIR-MANUAL-HOLD-UNVERIFIED')
    from recovery_settings import normalized
    from failure_diagnosis import scoped_samples,resolve_pair,profile_identity
    from failover_plan import streak
    row=next((p for p in status.get('profiles',[]) if p.get('id')==journal['target']),None)
    recovery=normalized(settings);now=time.time()
    age=max(30,min(900,int(settings.get('interval',30))*3))
    resolved=resolve_pair(status,settings,now,age,max(30,min(600,int(settings.get('interval',30))*2)))
    expected=journal.get('vendor_profiles',{}).get('target')
    verified=(resolved['coordination']['state']=='READY' and resolved['target'] is not None
              and resolved['target']['id']==journal['target'] and (expected is None or profile_identity(resolved['target'])==expected))
    if not verified:
        n.publish({'state':'DEGRADED-ON-RESERVE','reason':'RESERVE-IDENTITY-UNKNOWN','manual':True,'transition_source':state.get('manual_hold_source','unknown'),'source':journal['source'],'target':journal['target'],'mode':'continuous-pair','proof_scope':pair.MODE})
        return True
    failed=row and streak(scoped_samples(status.get('samples',[]),row),row['id'],recovery['failures'],now,90,False,row)
    if failed:
        state.pop('manual_hold',None);pair.save(state);return False
    n.publish({'state':'COMMITTED','reason':'PAIR-MANUAL-HOLD-RESERVE','manual':True,'transition_source':state.get('manual_hold_source','unknown'),'source':journal['source'],'target':journal['target'],
               'mode':'continuous-pair','proof_scope':pair.MODE})
    return True
