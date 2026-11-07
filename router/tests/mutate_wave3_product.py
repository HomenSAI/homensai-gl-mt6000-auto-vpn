"""Mutation check of the wave 3 product items (WAVE3-PRODUCT-2026-11-04.ru.md): every mutant of the decision code must make
the fast part of the suites fail. Each mutant is applied in place, the matching suite runs, the file is restored (also on
error). Run on a copy (docker), never on the router:
  python router/tests/mutate_wave3_product.py [py|lua] [substring]   -> one line per mutant, exit 1 when a mutant survives
A mutant that deletes a whole line is written as `pass` in its place, so that it dies on behaviour and not on an IndentationError.
Not listed (equivalent): 'penalty<reuse' in the last check of halflife_hold - a negative logarithm is cut by max(stable, ...).
"""
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
PY=[[sys.executable,'-m','unittest','test_wave3_product','test_flap_damping.SharedCases','test_flap_damping.Units','-q']]
LUA=[['lua5.1','lua/test_wave3_product.lua'],['lua5.1','lua/test_wave3_monitor.lua'],['lua5.1','lua/test_flap_damping.lua']]

PY_MUTANTS=[
    # 1. flap damping
    ('recovery_settings.py',"'flap_limit':2,'flap_window':60","'flap_limit':3,'flap_window':60"),
    ('recovery_settings.py',"'flap_limit':2,'flap_window':60","'flap_limit':2,'flap_window':15"),
    ('recovery_settings.py',"'flap_model':'double','flap_limit'","'flap_model':'halflife','flap_limit'"),
    ('recovery_settings.py',"'flap_window':(1,120)","'flap_window':(1,121)"),
    ('recovery_settings.py',"result[key]=value if value in FLAP_MODELS else default","result[key]=value"),
    ('recovery_settings.py',"-set(FLAP_FIELDS)\n","\n"),
    ('pair_auto.py',"window=recovery['flap_window']*60","window=recovery['attempt_window']*60"),
    ('pair_auto.py',"excess=count-recovery['flap_limit']+1","excess=count-recovery['attempt_limit']+1"),
    ('pair_auto.py',"if recovery['flap_model']=='halflife':return halflife_hold(events,now,recovery)\n","pass\n"),
    ('pair_auto.py',"LEDGER_MEMORY = 14400","LEDGER_MEMORY = 900"),
    ('pair_auto.py',"LEDGER_SIZE = 15","LEDGER_SIZE = 16"),
    ('pair_auto.py',"recent = sorted(x for x in events if now - x < RATE_MEMORY)","recent = sorted(x for x in events if now - x < LEDGER_MEMORY)"),
    ('pair_auto.py',"return (older[-room:] if room else [])+recent, count < limit","return older+recent, count < limit"),
    ('pair_auto.py',"room = max(0, LEDGER_SIZE-len(recent))","room = LEDGER_SIZE"),
    ('pair_auto.py',"if suppressed and penalty<reuse:suppressed=False\n","pass\n"),
    ('pair_auto.py',"if penalty>recovery['flap_suppress']:suppressed=True","if penalty>=recovery['flap_reuse']:suppressed=True"),
    ('pair_auto.py',"penalty=penalty*0.5**((stamp-last)/half) if last is not None else 0.0","penalty=penalty if last is not None else 0.0"),
    ('pair_auto.py',"penalty*=0.5**((now-last)/half)\n","pass\n"),
    ('pair_auto.py',"max(stable,stable+half*math.log(penalty/reuse,2))","max(stable,half*math.log(penalty/reuse,2))"),
    ('pair_auto.py',"for stamp in sorted(x for x in events if x<=now):","for stamp in sorted(events):"),
    # 2. retries
    ('retry_policy.py','CAP=15','CAP=60'),
    ('retry_policy.py','BASE=2','BASE=3'),
    ('retry_policy.py','FIBONACCI=(1,1,2,3,5,8)','FIBONACCI=(1,2,4,8,16,32)'),
    ('retry_policy.py','FLOOR=0.5','FLOOR=0.0'),
    ('retry_policy.py',"if mode(settings)=='fixed':return FIXED\n","pass\n"),
    ('retry_policy.py',"failures+1 if last is not None and 0<=now-last<RESET else 1","failures+1"),
    ('retry_policy.py',"0<=now-last<RESET","0<=now-last<=RESET"),
    ('retry_policy.py','()*base(failures)','()*CAP'),
    ('retry_policy.py','()*base(failures)','()*0+base(failures)'),
    ('native_switch.py',"if queued_click() is not None:return\n        time.sleep(min(.2,left))","time.sleep(min(.2,left))"),
    ('native_switch.py',"(Lua: auto.nap).\"\"\"\n    end=time.monotonic()+seconds\n    while not STOP:\n        left=","(Lua: auto.nap).\"\"\"\n    end=time.monotonic()+seconds\n    while True:\n        left="),
    # 3. phases and grid
    ('probe_plan.py','SPREAD_CAP=3.0','SPREAD_CAP=30.0'),
    ('probe_plan.py',"step=min(float(interval)/len(every_id),SPREAD_CAP)","step=SPREAD_CAP"),
    ('probe_plan.py',"if spread_enabled(settings) and is_idle and len(every_id)>1:step","if is_idle and len(every_id)>1:step"),
    ('probe_plan.py',"if spread_enabled(settings) and is_idle and len(every_id)>1:step","if spread_enabled(settings) and len(every_id)>1:step"),
    ('probe_plan.py',"every_id=[x for x in every_id if x!=source]+[source]","every_id=[source]+[x for x in every_id if x!=source]"),
    ('probe_plan.py',"kept=[(x,index*step) for index,x in enumerate(every_id) if x not in skip]","kept=[(x,index*step) for index,x in enumerate(y for y in every_id if y not in skip)]"),
    ('probe_plan.py',"return isinstance(settings,dict) and settings.get('probe_spread') is not False","return True"),
    ('probe_plan.py',"if planned-now<1:return now+1,1","if planned-now<0:return now+1,1"),
    ('probe_plan.py',"planned=slot+interval","planned=now+interval"),
    ('probe_plan.py',"abs(now-expected)>SLOT_TOLERANCE","False"),
    # 4. reserve budget
    ('probe_plan.py',"limit=min(wanted,valid_for-interval)","limit=wanted"),
    ('probe_plan.py',"return limit if limit>interval else 0","return limit"),
    ('probe_plan.py',"RESERVE_RANGE=(20,120)","RESERVE_RANGE=(19,121)"),
    ('probe_plan.py',"and context.get('native')=='OBSERVING'\n",""+"\n"),
    ('probe_plan.py',"and context.get('source_clean') is True and context.get('target_clean') is True","and context.get('target_clean') is True"),
    ('probe_plan.py',"and context.get('source_clean') is True and context.get('target_clean') is True","and context.get('source_clean') is True"),
    ('probe_plan.py',"and not context.get('dense') and not context.get('boost') and not context.get('waiting'))","and not context.get('boost') and not context.get('waiting'))"),
    ('probe_plan.py',"and not context.get('dense') and not context.get('boost') and not context.get('waiting'))","and not context.get('dense') and not context.get('waiting'))"),
    ('probe_plan.py',"and not context.get('dense') and not context.get('boost') and not context.get('waiting'))","and not context.get('dense') and not context.get('boost'))"),
    ('probe_plan.py',"stamp is not None and 0<=now-stamp and now-stamp+interval<=every+SLACK","stamp is not None and now-stamp+interval<=every+SLACK"),
    ('probe_plan.py',"now-stamp+interval<=every+SLACK","now-stamp+interval<=every"),
    ('probe_plan.py',"now-stamp+interval<=every+SLACK","now-stamp<=every+SLACK"),
    ('probe_plan.py',"model.get('suspect') is True or model.get('failed') is True","model.get('failed') is True"),
    ('probe_plan.py',"model.get('suspect') is True or model.get('failed') is True","model.get('suspect') is True"),
    ('probe_plan.py',"group.get('generation') is not None and group.get('generation')==row.get('vendor_generation')","group.get('generation') is not None"),
    ('probe_plan.py',"and group.get('changed_at')==row.get('vendor_changed_at'))",")"),
    ('probe_plan.py',"group.get('state')=='SETTLED' and group.get('current_profile')==row.get('id')","group.get('current_profile')==row.get('id')"),
    ('probe_plan.py',"group.get('state')=='SETTLED' and group.get('current_profile')==row.get('id')","group.get('state')=='SETTLED'"),
    ('probe_plan.py',"or row.get('vendor_state')!='SETTLED':return False","or False:return False"),
    ('agent.py',"if kept is not None:mapped[identifier]=kept","mapped[identifier]=plan_memo['measured'].get(identifier,{})"),
    ('agent.py',"left=started+item[1]-time.monotonic()","left=0"),
    ('agent.py',"bound=[by_id[identifier] for identifier in planned['order']]","pass"),
]
LUA_MUTANTS=[
    ('lua/pair.lua',"flap_model='double',flap_limit=2,flap_window=60","flap_model='double',flap_limit=3,flap_window=60"),
    ('lua/pair.lua',"flap_model='double',flap_limit=2,flap_window=60","flap_model='double',flap_limit=2,flap_window=15"),
    ('lua/pair.lua',"flap_window={1,120}","flap_window={1,121}"),
    ('lua/pair.lua',"local window=recovery.flap_window*60","local window=recovery.attempt_window*60"),
    ('lua/pair.lua',"local excess=count-recovery.flap_limit+1","local excess=count-recovery.attempt_limit+1"),
    ('lua/pair.lua',"if recovery.flap_model=='halflife' then return M.halflife_hold(events,now,recovery) end\n",""),
    ('lua/pair.lua',"M.LEDGER_MEMORY=14400","M.LEDGER_MEMORY=900"),
    ('lua/pair.lua',"M.LEDGER_SIZE=15","M.LEDGER_SIZE=16"),
    ('lua/pair.lua',"for i=#older-math.max(0,M.LEDGER_SIZE-#recent)+1,#older do","for i=1,#older do"),
    ('lua/pair.lua',"if suppressed and penalty<reuse then suppressed=false end\n",""),
    ('lua/pair.lua',"if penalty>recovery.flap_suppress then suppressed=true end","if penalty>=recovery.flap_reuse then suppressed=true end"),
    ('lua/pair.lua',"  penalty=penalty*0.5^((now-last)/half)\n",""),
    ('lua/retry_policy.lua','M.CAP=15','M.CAP=60'),
    ('lua/retry_policy.lua','M.FIBONACCI={1,1,2,3,5,8}','M.FIBONACCI={1,2,4,8,16,32}'),
    ('lua/retry_policy.lua','M.FLOOR=0.5','M.FLOOR=0.0'),
    ('lua/retry_policy.lua',"if M.mode(settings)=='fixed' then return M.FIXED end\n",""),
    ('lua/retry_policy.lua',"now-last>=0 and now-last<M.RESET","now-last>=0"),
    ('lua/retry_policy.lua',"(uniform or M.uniform)()*M.base(failures)","(uniform or M.uniform)()*M.CAP"),
    ('lua/retry_policy.lua',"return (string.byte(data,1)*256+string.byte(data,2))/65536","return 0.5"),
    ('lua/probe_plan.lua','M.SPREAD_CAP=3.0','M.SPREAD_CAP=30.0'),
    ('lua/probe_plan.lua',"if M.spread_enabled(settings) and is_idle and #all>1 then","if is_idle and #all>1 then"),
    ('lua/probe_plan.lua',"if M.spread_enabled(settings) and is_idle and #all>1 then","if M.spread_enabled(settings) and #all>1 then"),
    ('lua/probe_plan.lua',"moved[#moved+1]=source;all=moved","all=all"),
    ('lua/probe_plan.lua',"offsets[#offsets+1]=(index-1)*step","offsets[#offsets+1]=(#order-1)*step"),
    ('lua/probe_plan.lua',"if planned-now<1 then return now+1,1 end","if planned-now<0 then return now+1,1 end"),
    ('lua/probe_plan.lua',"local planned=slot+interval","local planned=now+interval"),
    ('lua/probe_plan.lua',"math.abs(now-expected)>M.SLOT_TOLERANCE","false"),
    ('lua/probe_plan.lua',"local limit=math.min(wanted,valid_for-interval)","local limit=wanted"),
    ('lua/probe_plan.lua',"and context.source_clean==true and context.target_clean==true","and context.target_clean==true"),
    ('lua/probe_plan.lua',"and context.source_clean==true and context.target_clean==true","and context.source_clean==true"),
    ('lua/probe_plan.lua',"and not value(context,'dense') and not value(context,'boost')","and not value(context,'boost')"),
    ('lua/probe_plan.lua',"and not value(context,'dense') and not value(context,'boost')","and not value(context,'dense')"),
    ('lua/probe_plan.lua',"now-stamp+interval<=every+M.SLACK","now-stamp+interval<=every"),
    ('lua/probe_plan.lua',"now-stamp+interval<=every+M.SLACK","now-stamp<=every+M.SLACK"),
    ('lua/probe_plan.lua',"(model.suspect==true or model.failed==true)","(model.failed==true)"),
    ('lua/probe_plan.lua',"generation~=nil and generation==value(row,'vendor_generation')","generation~=nil"),
    ('lua/probe_plan.lua',"and value(group,'changed_at')==value(row,'vendor_changed_at') then return row end","then return row end"),
    ('lua/monitor.lua',"if ctx.released or offset<=0 or not runner.after then return false end","if true then return false end"),
    ('lua/monitor.lua',"if kept~=nil then mapped[id]=kept end","mapped[id]=self.plan_memo.measured[id]"),
    ('lua/monitor.lua',"    self.spread_release=nil\n",""),
    ('lua/monitor.lua',"if self.passing then self:spread_now() else timer:set(1) end","if not self.passing then timer:set(1) end"),
    ('lua/monitor.lua',"if okf and suspected then monitor:suspected_now(timer) end","if okf and suspected and not monitor.passing then timer:set(1) end"),
    ('lua/monitor.lua',"self.grid_slot,delay=probe_plan.next_slot(self.pass_slot,interval,(self.pass_started or self.runner.clock())+(self.pass_seconds or 0))","self.grid_slot,delay=nil,math.max(1,interval-(self.pass_seconds or 0))"),
    ('lua/auto.lua',"local pause=retry.pause(ctx.failed_passes,rok and settings or nil)","local pause=5"),
    ('lua/auto.lua',"ctx.failed_passes,ctx.failed_at=retry.count(ctx.failed_passes or 0,ctx.failed_at,env.run.clock())","ctx.failed_passes=1"),
    ('lua/auto.lua',"if rok and retry.mode(settings)=='fixed' then return pause end\n",""),
    ('lua/auto.lua',"M.nap(env,ctx.nap_seconds or 2);ctx.nap_seconds=nil","M.nap(env,2);ctx.nap_seconds=nil"),
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
    which=sys.argv[1] if len(sys.argv)>1 else 'both'
    only=sys.argv[2] if len(sys.argv)>2 else ''
    python=[m for m in PY_MUTANTS if only in m[1]];lua=[m for m in LUA_MUTANTS if only in m[1]]
    bad=[]
    if which in ('py','both'):bad+=run('py',python,PY)
    if which in ('lua','both'):bad+=run('lua',lua,LUA)
    print('mutants: %d, survived: %d'%(len(python)*(which!='lua')+len(lua)*(which!='py'),len(bad)))
    return 1 if bad else 0


if __name__=='__main__':raise SystemExit(main())
