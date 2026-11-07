"""Mutation check of the fixes of the independent safety review of 71053c32 (findings 1-8): every mutant of a new guard must make
the matching suite fail. Each mutant is applied in place, the suites run, the file is restored (also on error). Run on a copy
(docker), never on the router:
  python router/tests/mutate_safety_review.py [py|lua] [substring]   -> one line per mutant, exit 1 when a mutant survives
"""
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
PY=[[sys.executable,'-W','ignore','-m','unittest','-f','test_key_gate.Gate','test_key_gate.Rollback','test_key_gate.Doors','test_key_gate.Session','test_key_gate.Failover','test_key_gate.Buttons','test_key_gate.ServerChange','test_wave3_product.Ledger','test_wave3_product.FailedPassRest','test_wave3_product.QueuedClickExpiry',
     'test_fast_switch.Tick','test_network_advisor.Control','test_pair_manual_directions','test_forward_resume.BeforeReorder','test_forward_resume.EndToEnd','-q']]
LUA=[[sys.executable,'-W','ignore','-m','unittest','test_wave3_product.Ledger','-q'],['lua5.1','lua/test_key_gate.lua'],['lua5.1','lua/test_late_switch.lua'],['lua5.1','lua/test_flap_damping.lua'],['lua5.1','lua/test_wave3_product.lua'],
     ['lua5.1','lua/test_forward_resume.lua'],['lua5.1','lua/test_page_controls.lua'],['lua5.1','lua/test_network_advisor.lua']]
SETUP=[[sys.executable,'-W','ignore','-m','unittest','test_lua_contracts','test_gl_sensors.SystemFiles','-q']]

PY_MUTANTS=[
    # findings 1, 2: the proof knows nothing of keys; the gate is directional
    ('pair_auto.py',"    if 'selected_policy' not in state:\n        # A Start does not begin","    if False:\n        # A Start does not begin"),
    ('pair_auto.py',"pinned=n.key_unaccepted(selection['source']['id'],selection['target']['id'])\n        if pinned:\n            n.publish","pinned=n.key_unaccepted(selection['source']['id'])\n        if pinned:\n            n.publish"),
    ('pair_auto.py',"pinned=n.key_unaccepted(selection['target']['id'])\n            if pinned:\n                # the owner's option","pinned=n.key_unaccepted(selection['source']['id'])\n            if pinned:\n                # the owner's option"),
    ('pair_auto.py',"            pinned=n.key_unaccepted(selection['target']['id'])\n            if pinned:\n                # the owner's option","            pinned=None\n            if pinned:\n                # the owner's option"),
    ('pair_auto.py',"if n.key_unaccepted(roles.get('source_id'),roles.get('target_id')):code=S.DEFERRED","pass"),
    ('native_switch.py',"    pinned=key_unaccepted(journal['source'])  # no return","    pinned=None  # no return"),
    ('native_switch.py',"    if not pair_reapply:  # a repair of the rules","    if False:  # a repair of the rules"),
    ('native_switch.py',"    if not pair_reapply:  # a repair of the rules","    if True:  # a repair of the rules"),
    ('native_switch.py',"pinned=key_unaccepted(selection[pair_destination or 'target']['id'])","pinned=key_unaccepted(selection['target']['id'])"),
    ('native_switch.py',"    pinned=key_unaccepted(selection[pair_destination]['id'])\n    if pinned:raise Refused(pinned)\n    from auto_control import normalize_request_source,control_lock","    from auto_control import normalize_request_source,control_lock"),
    ('native_switch.py',"    if reason=='OPERATOR-RETURN':\n        pinned=key_unaccepted(journal.get('source'))","    if True:\n        pinned=key_unaccepted(journal.get('source'))"),
    ('native_switch.py',"    if reason=='OPERATOR-RETURN':\n        pinned=key_unaccepted(journal.get('source'))","    if False:\n        pinned=key_unaccepted(journal.get('source'))"),
    ('native_switch.py',"if not pinned:return {'action':'RESTORE-PRIMARY'","if True:return {'action':'RESTORE-PRIMARY'"),
    ('native_switch.py',"reason':refused or 'RESERVE-FAILED'","reason':'RESERVE-FAILED'"),
    ('native_switch.py',"'reason':refused or ('PAIR-RATE-LIMIT'","'reason':('PAIR-RATE-LIMIT'"),
    ('native_switch.py',"    return gate(read,RUNTIME,PERSIST,[x for x in profiles if isinstance(x,str)])","    return None"),
    ('native_switch.py',"return blockers+[pinned] if pinned and pinned not in blockers else blockers","return blockers+[pinned] if pinned else blockers"),
    ('pair_manual.py',"    return n.key_unaccepted(target)\n","    return None\n"),
    ('pair_manual.py',"            if pinned:side.append(pinned)\n","            pass\n"),
    ('pair_manual.py',"            pinned=n.key_unaccepted(selection[hold]['id'])  # before the lease","            pinned=None  # before the lease"),
    ('forward_resume.py',"    if untouched:\n        # nothing moved yet","    if False:\n        # nothing moved yet"),
    ('forward_resume.py',"    if untouched:\n        # nothing moved yet","    if True:\n        # nothing moved yet"),
    # finding 3
    ('pair_auto.py',"if beat_run is not None and LATE_ABORTS.get(('beat',selection['source']['id']))==beat_run:return late_abort('same-run')","pass"),
    ('pair_auto.py',"beat_run=beat.get('since') if rule=='heartbeat' and isinstance(beat,dict) else None","beat_run=beat.get('since') if isinstance(beat,dict) else None"),
    ('pair_auto.py',"                    if beat_run is not None:LATE_ABORTS[('beat',decided['source']['id'])]=beat_run\n",""),
    ('pair_auto.py',"            if state.get('manual_hold'):\n                state.pop('manual_hold',None);save(state)\n            charged=[]\n","            charged=[]\n"),
    # finding 4
    ('native_switch.py',"    if key==QUEUED_SEEN[0]:return None\n",""),
    ('native_switch.py',"if queued_click() is not None:return\n        time.sleep(min(.2,left))","time.sleep(min(.2,left))"),
    ('pair_manual.py',"return bool(row) and row['state']=='QUEUED' and not row['requested']<=time.time()<=row['requested']+60","return bool(row) and row['state']=='QUEUED'"),
    ('pair_manual.py',"return bool(row) and row['state']=='QUEUED' and not row['requested']<=time.time()<=row['requested']+60","return bool(row) and not row['requested']<=time.time()<=row['requested']+60"),
    ('pair_manual.py',"row.update(state='CANCELLED',updated=max(time.time(),row['requested']),code='PAIR-MANUAL-EXPIRED');atomic_json(path(),row)\n        return True","pass\n        return True"),
    # finding 5
    ('pair_auto.py',"return [x for x in events if x not in others] if isinstance(others,list) else events","return events"),
    ('pair_auto.py',"    if not failover:others.append(stamp)\n",""),
    ('pair_auto.py',"others=[x for x in ledger.get('others') if x in events] if isinstance(ledger.get('others'),list) else []","others=list(ledger.get('others') or [])"),
    ('pair_auto.py',"    if aborted:row['aborted']=aborted  # a refund","    # a refund"),
    ('pair_auto.py',"    if ledger.get('others'):row['others'] = ledger['others']\n",""),
    ('pair_auto.py',"return return_hold(failover_events(events,ledger),now,recovery)","return return_hold(events,now,recovery)"),
    ('pair_auto.py',"def charge_attempt(settings,revision,limited=True,failover=True):","def charge_attempt(settings,revision,limited=True,failover=False):"),
    ('pair_auto.py',"on_dispatch=lambda:charge_attempt(settings,revision,limited=False,failover=False))","on_dispatch=lambda:charge_attempt(settings,revision,limited=False))"),
    # finding 6
    ('advisor.py',"            or calm.get('manual')):\n","            ):\n"),
    ('advisor_control.py',"'phase':None,'manual':manual_pending(runtime)}","'phase':None}"),
    ('advisor_control.py',"(('pair-manual-control.json',('QUEUED','CLAIMED')),","(('pair-manual-control.json',('QUEUED',)),"),
]

LUA_MUTANTS=[
    ('lua/pair.lua',"  if state.selected_policy==nil then\n    -- A Start does not begin","  if false then\n    -- A Start does not begin"),
    ('lua/pair.lua',"local pinned=T.key_unaccepted(env,selection.source.id,selection.target.id)\n  if pinned then refuse(pinned) end","local pinned=T.key_unaccepted(env,selection.source.id)\n  if pinned then refuse(pinned) end"),
    ('lua/pair.lua',"      local pinned=T.key_unaccepted(env,selection.target.id)\n      if pinned then\n        -- the owner's option","      local pinned=nil\n      if pinned then\n        -- the owner's option"),
    ('lua/pair.lua',"      local pinned=T.key_unaccepted(env,selection.target.id)\n      if pinned then\n        -- the owner's option","      local pinned=T.key_unaccepted(env,selection.source.id)\n      if pinned then\n        -- the owner's option"),
    ('lua/transaction.lua',"  local pinned=M.key_unaccepted(env,value.source)  -- no return","  local pinned=nil  -- no return"),
    ('lua/transaction.lua',"  if not pair_reapply then  -- a repair of the rules","  if false then  -- a repair of the rules"),
    ('lua/transaction.lua',"local pinned=M.key_unaccepted(env,selection[pair_destination or 'target'].id)","local pinned=M.key_unaccepted(env,selection.target.id)"),
    ('lua/manual.lua',"  local pinned=T.key_unaccepted(env,selection[destination].id)\n  if pinned then refuse(pinned) end\n",""),
    ('lua/transaction.lua',"  if reason=='OPERATOR-RETURN' then\n    local pinned","  if true then\n    local pinned"),
    ('lua/transaction.lua',"  if reason=='OPERATOR-RETURN' then\n    local pinned","  if false then\n    local pinned"),
    ('lua/transaction.lua',"if not pinned then return {action='RESTORE-PRIMARY'","if true then return {action='RESTORE-PRIMARY'"),
    ('lua/transaction.lua',"reason=refused or 'RESERVE-FAILED'","reason='RESERVE-FAILED'"),
    ('lua/transaction.lua',"    if type(identifier)=='string' then profiles[#profiles+1]=identifier end\n","    profiles[#profiles+1]=identifier\n"),
    ('lua/forward_resume.lua',"  if untouched then\n    -- nothing moved yet","  if false then\n    -- nothing moved yet"),
    ('lua/forward_resume.lua',"  if untouched then\n    -- nothing moved yet","  if true then\n    -- nothing moved yet"),
    ('lua/page_controls.lua',"pinned=d.key_unaccepted(target);if pinned then reserve[#reserve+1]=pinned end","pinned=d.key_unaccepted(source);if pinned then reserve[#reserve+1]=pinned end"),
    # finding 3
    ('lua/pair.lua',"if beat_run~=nil and M.late_aborts['beat:'..selection.source.id]==beat_run then return late_abort('same-run') end\n",""),
    ('lua/pair.lua',"if rule=='heartbeat' and type(beat)=='table' and beat~=NULL then beat_run=num(beat.since) end","if type(beat)=='table' and beat~=NULL then beat_run=num(beat.since) end"),
    ('lua/pair.lua',"          if beat_run~=nil then M.late_aborts['beat:'..selection.source.id]=beat_run end\n",""),
    ('lua/pair.lua',"      if not isnone(state.manual_hold) then state.manual_hold=nil;M.save(env,state) end\n      local charged=nil\n","      local charged=nil\n"),
    # finding 4
    ('lua/auto.lua',"  if key==env.queued_seen then return nil end\n",""),
    ('lua/auto.lua',"  require('manual').expire_queued(env)\n",""),
    ('lua/manual.lua',"    return not (asked<=now and now<=asked+60)\n","    return true\n"),
    ('lua/manual.lua',"    if row.state~='QUEUED' then return false end\n",""),
    # finding 5
    ('lua/pair.lua',"  if not canon.is_array(others) then return events end\n","  if true then return events end\n"),
    ('lua/pair.lua',"  if not failover then others[#others+1]=canon.float(stamp) end\n",""),
    ('lua/pair.lua',"on_dispatch=function() M.charge_attempt(env,settings,revision,false,false) end})","on_dispatch=function() M.charge_attempt(env,settings,revision,false) end})"),
    ('lua/pair.lua',"on_dispatch=function() M.charge_attempt(env,settings,revision,nil,false) end})","on_dispatch=function() M.charge_attempt(env,settings,revision) end})"),
    ('lua/pair.lua',"  M.ledger_charge(env,events,now,failover~=false)\n","  M.ledger_charge(env,events,now,failover==true)\n"),
    ('lua/pair.lua',"for _,x in ipairs(ledger.others) do if present[num(x)] then others[#others+1]=x end end","for _,x in ipairs(ledger.others) do others[#others+1]=x end"),
    # finding 6
    ('lua/advisor.lua',"     or (calm.manual~=nil and calm.manual~=NULL and calm.manual~=false) then\n","     then\n"),
]

SETUP_MUTANTS=[
    # findings 7, 8
    ('setup_save.lua',"recovery_flap_model=true,",""),
    ('setup_save.lua',"recovery_flap_reuse=true,",""),
    ('../../../lib/upgrade/keep.d/homensai-vpn',"/etc/homensai-vpn/server-keys.json\n",""),
    ('../../../lib/upgrade/keep.d/homensai-vpn',"/etc/homensai-vpn/keys.local/\n",""),
]


def run(group,mutants,commands):
    survived=[]
    for index,(name,old,new) in enumerate(mutants,1):
        path=LIB/name
        original=path.read_bytes()
        text=original.decode('utf-8').replace('\r\n','\n')
        if text.count(old)!=1:
            print(group,index,'NOT-APPLIED',name,old[:60],flush=True);survived.append((name,old));continue
        try:
            path.write_bytes(text.replace(old,new,1).encode('utf-8'))
            killed=False
            for argv in commands:
                done=subprocess.run(argv,cwd=HERE,capture_output=True,text=True,timeout=900)
                if done.returncode!=0:killed=True;break
        finally:
            path.write_bytes(original)
        print(group,index,'killed' if killed else 'SURVIVED',name,old[:60].replace('\n',' '),flush=True)
        if not killed:survived.append((name,old))
    return survived


def main():
    which=sys.argv[1] if len(sys.argv)>1 else 'all'
    only=sys.argv[2] if len(sys.argv)>2 else ''
    groups=(('py',PY_MUTANTS,PY),('lua',LUA_MUTANTS,LUA),('setup',SETUP_MUTANTS,SETUP))
    bad=[];total=0
    for name,mutants,commands in groups:
        if which not in ('all',name):continue
        chosen=[m for m in mutants if only in m[1]]
        total+=len(chosen);bad+=run(name,chosen,commands)
    print('mutants: %d, survived: %d'%(total,len(bad)))
    return 1 if bad else 0


if __name__=='__main__':raise SystemExit(main())
