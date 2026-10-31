-- control_request.lua (plan item 4): the Start / Stop / failure-test buttons in the Lua monitor, same order and
-- codes as agent.control_reply -> auto_control.start/stop, pair_auto.request, fault_control.start/cancel;
-- FALLBACK (agent.py) for what it cannot decide without waiting, always before anything is written.
-- Python cross-check mode (tests/test_lua_control_request.py):
--   lua test_control_request.lua --dir <directory> start|stop|cancel [policy-json]
-- runs one request on real files under <directory>/run and <directory>/etc and prints the reply.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local M=require('control_request')

local REV=string.rep('a',32)
local TRIAL=string.rep('d',32)
local NONCE=string.rep('e',32)
local NOW=1793420000.5
local MONO=5000
local MODE='router-probed-ipv4'
local UUID='0123abcd-0123-4567-89ab-0123456789ab\n'
local UUIDHEX='0123abcd0123456789ab0123456789ab'
local obj,arr=canon.object,canon.array

------------------------------------------------------------------------------------------------------
-- real files (Python cross-check)
------------------------------------------------------------------------------------------------------
if arg[1]=='--dir' then
  local dir,action,policy=arg[2],arg[3],arg[4]
  local function read(path)
    local f=io.open(path,'rb');if not f then return nil end
    local text=f:read('*a');f:close();return text
  end
  local function write(path,text)
    local f=assert(io.open(path..'.pending','wb'));f:write(text);f:close();assert(os.rename(path..'.pending',path))
  end
  local runtime,persist=dir..'/run',dir..'/etc'
  local env={run={fs={read=read,write_atomic=write},wall=function() return NOW end,clock=function() return MONO end},runtime=runtime,persist=persist}
  local function wall() return NOW end
  local now_value=tonumber(os.getenv('QA_NOW') or '')
  if now_value then NOW=now_value end
  local deps={read=read,write=write,exists=function(p) return read(p)~=nil end,now=function() return NOW end,clock=function() return MONO end,
    runtime=runtime,persist=persist,try_lock=function(fn) return true,fn() end,
    native_policy=function() return policy end,
    journal=function() return require('journal').read({fs={read=read},path=persist..'/native-transaction.json'}) end,
    auto_blocker=function() return nil end,
    preparation=function() return {checks={}} end,
    read_state=function() return require('pair').read_state(env) end,
    intent=function() return require('pair').intent(env) end,
    terminalize=function() return require('manual').terminalize_pending_locked(env,'CANCELLED','CONTROL-REVISION-STALE') end,
    nft=function() return 1,'' end}
  local _=wall
  local arguments=canon.decode(os.getenv('QA_ARGS') or '{}')
  local reply
  if action=='start' then reply=M.start(deps,arguments)
  elseif action=='stop' then reply=M.stop(deps,arguments)
  elseif action=='cancel' then reply=M.fault_cancel(deps,arguments)
  else error('unknown action') end
  if reply==M.FALLBACK then io.write('"FALLBACK"') else io.write(canon.encode(reply)) end
  os.exit(0)
end

------------------------------------------------------------------------------------------------------
-- a fake router
------------------------------------------------------------------------------------------------------
local function world(over)
  over=over or {}
  local files={}
  files['/run/auto-control-revision.json']=canon.encode(obj({revision=REV}))
  files['/proc/sys/kernel/random/uuid']=UUID
  for k,v in pairs(over.files or {}) do files[k]=v end
  local calls={terminalize=0,nft={}}
  local nft=over.nft or {list={{1,''}}}
  local deps={files=files,calls=calls,
    read=function(p) return files[p] end,
    write=function(p,text) if over.write_fails and over.write_fails[p] then error('disk',0) end;files[p]=text end,
    exists=function(p) return files[p]~=nil end,
    now=function() return NOW end,clock=function() return MONO end,runtime='/run',persist='/etc',
    try_lock=function(fn) if over.locked then return false end;return true,fn() end,
    native_policy=function()
      if over.policy==false then return nil end
      return over.policy or canon.encode(obj({settings=obj({pair_auto_mode=MODE,native_trial=TRIAL}),sections=arr()}))
    end,
    journal=function() if over.journal_error then error({code='JOURNAL-ORDER-INVALID'},0) end;return over.journal or obj() end,
    auto_blocker=function() return over.blocker end,
    preparation=function(settings) calls.preparation=settings;return over.prep or {checks={}} end,
    read_state=function() if over.state_error then error({code='PAIR-STATE-UNVERIFIED'},0) end;return over.state or obj() end,
    intent=function() local text=files['/run/pair-auto-control.json'];return text and canon.decode(text) or obj() end,
    terminalize=function() calls.terminalize=calls.terminalize+1;if over.terminalize_fails then error('x',0) end end,
    nft=function(action)
      calls.nft[#calls.nft+1]=action
      local queue=nft[action] or {}
      local step=table.remove(queue,1) or queue.last or {1,''}
      if #queue==0 then queue.last=step end
      return step[1],step[2]
    end}
  return deps
end
local function decode(deps,path) return canon.decode(deps.files[path]) end
local function blockers(reply) return reply.blockers and reply.blockers[1] end
local function start_args(extra)
  local a=obj({control_revision=REV,request_source='manual'})
  for k,v in pairs(extra or {}) do a[k]=v end
  return a
end

------------------------------------------------------------------------------------------------------
-- native_start
------------------------------------------------------------------------------------------------------
t.test('start: one queued pair intent, the same reply as pair_auto.request',function()
  local d=world()
  local reply=M.start(d,start_args())
  t.eq(reply,{accepted=true,queued=true,mode='continuous-pair',proof_scope=MODE,external_lan_verified=false})
  local row=decode(d,'/run/pair-auto-control.json')
  t.eq(row.mode,'on');t.eq(row.revision,REV);t.eq(row.id,UUIDHEX);t.eq(row.request_source,'manual')
  t.truthy(canon.is_float(row.time) and row.time.value==NOW,'time.time() float')
  t.eq(d.calls.preparation.pair_auto_mode,MODE,'the snapshot sees the router settings')
  t.eq(M.start(d,start_args()),{accepted=true,queued=true,already_requested=true},'a repeated click')
  t.eq(decode(d,'/run/pair-auto-control.json').id,UUIDHEX)
  local d2=world()
  M.start(d2,start_args({request_source='browser'}))
  t.eq(decode(d2,'/run/pair-auto-control.json').request_source,'unknown')
end)

t.test("start: only the owners own Start leaves the boot-resume marker on flash (owner decision 31.10.2026)",function()
  local d=world()
  M.start(d,start_args())
  local marker=decode(d,'/etc/auto-resume.json')
  t.eq(marker.enabled,true);t.eq(marker.request_source,'manual');t.truthy(canon.is_float(marker.time) and marker.time.value==NOW)
  for _,source in ipairs({'programmatic','test','browser'}) do
    local d2=world();M.start(d2,start_args({request_source=source}))
    t.eq(d2.read('/etc/auto-resume.json'),nil,source)
  end
end)

t.test('start: argument shape and revision codes',function()
  t.eq(blockers(M.start(world(),obj({request_source='manual'}))),'CONTROL-REVISION-STALE')
  t.eq(blockers(M.start(world(),start_args({extra=1}))),'CONTROL-REVISION-STALE')
  t.eq(blockers(M.start(world(),obj({control_revision='XYZ'}))),'CONTROL-REVISION-STALE')
  t.eq(blockers(M.start(world(),obj({control_revision=string.rep('b',32)}))),'CONTROL-REVISION-STALE')
  local d=world({files={['/run/auto-control-revision.json']='{"revision":"bad"}'}})
  t.eq(blockers(M.start(d,start_args())),'CONTROL-REVISION-STALE')
  t.eq(decode(d,'/run/auto-control-revision.json').revision,UUIDHEX,'revision_locked creates a missing revision under the lock')
  t.eq(d.files['/run/pair-auto-control.json'],nil)
end)

t.test('start: refusals in Python order, nothing written',function()
  local cases={
    {{policy=canon.encode(obj({sections=arr()}))},'START-STATE-UNVERIFIED'},
    {{policy=canon.encode(obj({settings=arr({1})}))},'START-STATE-UNVERIFIED'},
    {{journal_error=true},'JOURNAL-INTEGRITY-FAILED'},
    {{journal=obj({phase='APPLYING'})},'TRANSACTION-IN-PROGRESS'},
    {{journal=obj({phase='COMMITTED'})},'TRANSACTION-IN-PROGRESS'},
    {{journal=obj({phase='RELEASE-PENDING'})},'TRANSACTION-IN-PROGRESS'},
    {{blocker='PREPARATION-RESTART-REQUIRED'},'PREPARATION-RESTART-REQUIRED'},
    {{state_error=true},'PAIR-STATE-UNVERIFIED'},
    {{state=obj({phase='RUNNING',id=string.rep('c',32)})},'PAIR-RECOVERY-REQUIRED'},
    {{state=obj({phase='HELD',id=string.rep('c',32),recovery_error='PAIR-NETWORK-WRITE-FAILED'})},'PAIR-RECOVERY-REQUIRED'},
  }
  for i,case in ipairs(cases) do
    local d=world(case[1])
    t.eq(blockers(M.start(d,start_args())),case[2],'case '..i)
    t.eq(d.files['/run/pair-auto-control.json'],nil,'case '..i..' wrote nothing')
  end
  local d=world({journal=obj({phase='ROLLED-BACK'}),state=obj({phase='STOPPED',id=string.rep('c',32)})})
  t.eq(M.start(d,start_args()).accepted,true,'a settled journal and a stopped session')
  d=world({prep={checks={{code='PREP-SFE-RUNTIME',state='fail'},{code='PREP-SFE-AUTOLOAD',state='unknown'}}}})
  t.eq(M.start(d,start_args()).accepted,true,'checks Start does not repair do not stop it (as auto_prepare)')
end)

t.test('start: what Lua cannot decide without waiting goes to agent.py, nothing written',function()
  local cases={
    {locked=true},
    {files={['/run/speed-pause.json']='{}'}},
    {policy=false},
    {policy='{bad'},
    {prep={checks={{code='PREP-SOURCE-AUTOSTART',state='fail'}}}},
    {prep={checks={{code='PREP-HNAT-CONFIG',state='unknown'}}}},
    {policy=canon.encode(obj({settings=obj({native_trial=TRIAL})}))},
    {state=obj({phase='HELD',id=string.rep('c',32),recovery_error='PAIR-EXTERNAL-POLICY-CHANGE'})},
  }
  for i,over in ipairs(cases) do
    local d=world(over)
    t.truthy(M.start(d,start_args())==M.FALLBACK,'case '..i)
    t.eq(d.files['/run/pair-auto-control.json'],nil,'case '..i..' wrote nothing')
  end
end)

------------------------------------------------------------------------------------------------------
-- native_stop
------------------------------------------------------------------------------------------------------
t.test('stop: rotated revision, pair intent off, pending click cancelled, trial latch',function()
  local d=world({files={['/run/pair-auto-control.json']=canon.encode(obj({mode='on',revision=REV,time=canon.float(NOW-50),id=string.rep('c',32)}))}})
  local reply=M.stop(d,obj({request_source='manual'}))
  t.eq(reply,{queued=true})
  local revision=decode(d,'/run/auto-control-revision.json').revision
  t.eq(revision,UUIDHEX,'Stop rotates the revision')
  local pair=decode(d,'/run/pair-auto-control.json')
  t.eq(pair.mode,'off');t.eq(pair.revision,UUIDHEX);t.eq(pair.request_source,'manual');t.truthy(canon.is_float(pair.time))
  t.eq(d.calls.terminalize,1)
  local latch=decode(d,'/etc/native-stop.json')
  t.eq(latch.trial,TRIAL);t.eq(latch.all_trials,nil);t.eq(latch.request_source,'manual');t.truthy(canon.is_float(latch.requested))
  t.eq(M.stop(d,obj()),{queued=true,already_requested=true},'the same trial already latched')
end)

t.test('stop: settings unverified or no trial -> global latch; a later start request is superseded',function()
  local d=world({policy=false})
  t.eq(M.stop(d,obj()),{queued=true,settings_unverified=true})
  local latch=decode(d,'/etc/native-stop.json')
  t.eq(latch.all_trials,true);t.eq(latch.trial,canon.null);t.eq(latch.request_source,'unknown')
  t.eq(d.files['/run/pair-auto-control.json'],nil,'no pair intent file: none is created')
  d=world({policy=canon.encode(obj({settings=obj({native_trial=7})}))})
  t.eq(M.stop(d,obj()).settings_unverified,true,'a non-string trial is unverified')
  d=world({files={['/run/auto-control.json']=canon.encode(obj({mode='on',trial=string.rep('9',32),time=canon.float(NOW-5)}))}})
  t.eq(M.stop(d,obj()),{queued=true})
  t.eq(decode(d,'/etc/native-stop.json').all_trials,true,'start request for another trial: global latch')
  d=world({files={['/etc/native-stop.json']=canon.encode(obj({requested=canon.float(NOW+100),trial=TRIAL})),
    ['/run/auto-control.json']=canon.encode(obj({mode='on',trial=TRIAL,time=canon.float(NOW+200)}))}})
  t.eq(M.stop(d,obj()),{queued=true},'an older latch than the start request is renewed')
  t.eq(decode(d,'/etc/native-stop.json').requested.value,NOW+100,'max(time.time(), previous)')
end)

t.test('stop: fields, held lock, failure test and storage failures',function()
  t.eq(M.stop(world(),obj({request_source='manual',x=1})),{error='RPC-UNEXPECTED-ARGS'})
  local d=world({locked=true})
  t.truthy(M.stop(d,obj())==M.FALLBACK);t.eq(d.files['/etc/native-stop.json'],nil)
  d=world({files={['/run/fault-intent.json']='{}'}})
  t.truthy(M.stop(d,obj())==M.FALLBACK,'Stop + failure-test cleanup stay one Python step');t.eq(d.files['/etc/native-stop.json'],nil)
  d=world({write_fails={['/run/auto-control-revision.json']=true}})
  t.eq(M.stop(d,obj()),{queued=false,code='STOP-UNCONFIRMED'})
  local latch=decode(d,'/etc/native-stop.json')
  t.eq(latch.control_revision_failed,true);t.eq(latch.all_trials,true,'a failed rotation latches every trial')
  d=world({write_fails={['/etc/native-stop.json']=true}})
  t.eq(M.stop(d,obj()),{queued=false,code='STOP-UNCONFIRMED'})
  d=world({terminalize_fails=true})
  t.eq(M.stop(d,obj()),{queued=true},'a damaged click row never prevents Stop')
end)

------------------------------------------------------------------------------------------------------
-- failure test
------------------------------------------------------------------------------------------------------
local function intent_files(extra)
  local data=obj({nonce=NONCE,phase='ACTIVE',started=canon.float(NOW-20),['until']=canon.float(NOW+100),monotonic_until=canon.float(MONO+100),
    profiles=arr({'wireguard:peer_1'}),devices=arr({'wgclient1'}),scope='channel',duration=120,control_revision=REV})
  for k,v in pairs(extra or {}) do data[k]=v end
  return {['/run/fault-intent.json']=canon.encode(obj({data=data,sha256=canon.digest(data)}))}
end

t.test('fault_cancel: no test, fields, a removed table, result and history',function()
  t.eq(M.fault_cancel(world(),obj()),{queued=false,code='FAULT-NOT-ACTIVE'})
  t.eq(M.fault_cancel(world(),obj({x=1})),{queued=false,code='FAULT-FIELDS'})
  local d=world({files=intent_files()})
  t.eq(M.fault_cancel(d,obj()),{queued=true,cleaned=true,code='FAULT-CANCELLED',history_error=canon.null})
  t.eq(decode(d,'/run/fault-cancel.json'),{nonce=NONCE})
  local result=decode(d,'/run/fault-result.json')
  t.eq(result.nonce,NONCE);t.eq(result.cleaned,true);t.eq(result.code,'FAULT-CANCELLED')
  local history=decode(d,'/etc/fault-history.json')
  t.eq(history.sha256,canon.digest(history.data));t.eq(#history.data,1)
  t.eq(history.data[1].code,'FAULT-CANCELLED');t.eq(history.data[1].profiles,{'wireguard:peer_1'});t.eq(history.data[1].duration,120)
  t.eq(d.calls.nft,{'list'})
end)

t.test('fault_cancel: own table deleted under the lock and confirmed; foreign and failing tables refused',function()
  local d=world({files=intent_files(),nft={list={{0,'table inet homensai_vpn_fault { comment "homensai-owned-fault-'..NONCE..'" }'},{1,''}},delete={{0,''}}}})
  t.eq(M.fault_cancel(d,obj()).code,'FAULT-CANCELLED');t.eq(d.calls.nft,{'list','delete','list'})
  d=world({files=intent_files(),nft={list={{0,'table inet homensai_vpn_fault { comment "homensai-owned-fault-other" }'}}}})
  t.eq(M.fault_cancel(d,obj()),{accepted=false,code='FAULT-FOREIGN-TABLE'})
  d=world({files=intent_files(),nft={list={{2,''}}}})
  t.eq(M.fault_cancel(d,obj()),{accepted=false,code='FAULT-NFT-QUERY-FAILED'})
  d=world({files=intent_files(),nft={list={{0,'homensai-owned-fault-'..NONCE},{0,'homensai-owned-fault-'..NONCE}},delete={{0,''}}}})
  t.eq(M.fault_cancel(d,obj()),{accepted=false,code='FAULT-CLEANUP-UNCONFIRMED'})
  d=world({files=intent_files(),nft={list={{0,'homensai-owned-fault-'..NONCE}},delete={{1,''}}}})
  t.eq(M.fault_cancel(d,obj()),{accepted=false,code='FAULT-TIMEOUT-RULE-FAILED'})
  d=world({files=intent_files(),nft={list={{124,''}}}})
  t.truthy(M.fault_cancel(d,obj())==M.FALLBACK,'a timed-out query: agent.py repeats the idempotent cancel')
end)

t.test('fault_cancel: corrupt intent, held lock, damaged history',function()
  local files=intent_files();files['/run/fault-intent.json']=string.gsub(files['/run/fault-intent.json'],'"phase":"ACTIVE"','"phase":"ARMED"')
  t.eq(M.fault_cancel(world({files=files}),obj()),{accepted=false,code='FAULT-STATE-CORRUPT'})
  t.truthy(M.fault_cancel(world({files=intent_files(),locked=true}),obj())==M.FALLBACK)
  files=intent_files();files['/etc/fault-history.json']='{"data":[],"sha256":"0"}'
  local d=world({files=files})
  t.eq(M.fault_cancel(d,obj()).history_error,'FAULT-HISTORY-UNAVAILABLE')
  t.eq(d.files['/etc/fault-history.json'],'{"data":[],"sha256":"0"}','a damaged history is not overwritten')
end)

t.test('fault_start: the locked refusals in Lua, every start goes to agent.py',function()
  local d=world({files={['/run/auto-control-revision.json']='{"revision":"x"}'}})
  t.eq(M.fault_start(d,obj()),{accepted=false,code='FAULT-CONTROL-CHANGED'})
  d=world({files=intent_files()})
  t.eq(M.fault_start(d,obj({profile='wireguard:peer_1',scope='channel',duration=60})),{accepted=false,code='FAULT-ALREADY-ACTIVE'})
  local files=intent_files({monotonic_until=canon.float(MONO-1)})
  t.truthy(M.fault_start(world({files=files}),obj())==M.FALLBACK,'an elapsed test')
  files=intent_files();files['/run/fault-result.json']=canon.encode(obj({nonce=NONCE,cleaned=true}))
  t.truthy(M.fault_start(world({files=files}),obj())==M.FALLBACK,'a cleaned test')
  t.truthy(M.fault_start(world(),obj())==M.FALLBACK,'no test yet')
  t.truthy(M.fault_start(world({locked=true}),obj())==M.FALLBACK)
  files=intent_files();files['/run/fault-intent.json']='{"data":{},"sha256":"x"}'
  t.eq(M.fault_start(world({files=files}),obj()),{accepted=false,code='FAULT-STATE-CORRUPT'})
end)

t.run()
