-- page_controls.lua: manual_switch_control (pair_manual.controls / manual_control.control_status) and scan
-- (scan_control.public) in Lua, so the monitor answers the page without status_bridge.py.
-- Python differential mode (tests/test_lua_page_controls.py):
--   lua test_page_controls.lua --cases   reads a JSON array of cases on stdin, prints a JSON array of answers.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local C=require('page_controls')
local page=require('monitor_status')
local obj,arr=canon.object,canon.array
local NULL=canon.null

-- an env over in-memory files: 'run/<name>' -> /R/<name>, 'save/<name>' -> /P/<name>
local function file_env(files)
  local map={}
  for name,text in pairs(files or {}) do
    local path=string.gsub(string.gsub(name,'^run/','/R/'),'^save/','/P/')
    map[path]=text
  end
  local fs={read=function(path) return map[path] end,write_atomic=function(path,text) map[path]=text end,unsafe=function() return false end}
  local env={run={fs=fs,wall=function() return 0 end,clock=function() return 0 end},runtime='/R',persist='/P'}
  local function read_json(path,default)
    local text=map[path]
    if text==nil then return default end
    return canon.decode(text)
  end
  return env,read_json,map
end

-- deps of one case: the files are real (pair state envelope, intent, revision, manual row, native status, status,
-- budget, legacy records, display diagnostic); settings, order, journal, kernel, fast and now are given.
local function case_deps(case)
  local env,read_json=file_env(case.files)
  local now=canon.number(case.now)
  local function opt(v) if v==NULL then return nil end;return v end
  local common={now=now,runtime='/R',persist='/P',
    native=function() return read_json('/R/native-status.json',obj()) end,
    settings=function() if case.settings_error then error('POLICY-READ-FAILED',0) end;return opt(case.settings) end,
    current_revision=function() return page.current_revision(env) end,
    journal=function() return case.journal or obj() end,
    read_json=read_json}
  local pair_deps=setmetatable({
    read_state=function() return page.read_state(env) end,
    intent=function() return require('pair').intent(env) end,
    validate_bindings=function(b) return require('identity').validate(b) end,
    order=function() return case.order[1],case.order[2] end,
    status=function() return read_json('/R/status.json',obj()) end,
    queued=function() return require('manual').read(env) end,
    ledger=function() return read_json('/P/pair-auto-budget.json',obj({events=arr()})) end,
    kernel=function() return opt(case.kernel) or obj() end,
    fast=function() return case.fast==true end,
  },{__index=common})
  local legacy_deps=setmetatable({diagnostic=function()
    local row=read_json('/R/display-diagnostic.json',obj())
    local t_=canon.number(row.time)
    if not (t_ and 0<=now-t_ and now-t_<15 and canon.is_array(row.blockers)) then error(C.UNAVAILABLE,0) end
    local selection=row.selection;if selection==NULL then selection=nil end
    return row.blockers,selection
  end},{__index=common})
  return env,read_json,pair_deps,legacy_deps,now
end

if arg[1]=='--cases' then
  local cases=canon.decode(io.read('*a'))
  local out=arr()
  for _,case in ipairs(cases) do
    local env,read_json,pair_deps,legacy_deps,now=case_deps(case)
    local ok,result=pcall(function()
      if case.kind=='scan' then return C.scan_public(read_json('/R/scan.state',obj()),now) end
      local native=read_json('/R/native-status.json',obj({state='SERVICE-STOPPED'}))
      return C.manual_switch_control(pair_deps,legacy_deps,function(available)
        local use_pair=page.manual_switch(env,native,available)
        return use_pair
      end)
    end)
    out[#out+1]=ok and result or obj({lua_error=tostring(type(result)=='table' and result.code or result)})
  end
  io.write(canon.encode(out))
  os.exit(0)
end

------------------------------------------------------------------------------------------------------
-- unit tests (the differential with Python is in tests/test_lua_page_controls.py)
------------------------------------------------------------------------------------------------------
local NOW=1792750000.5

t.test('scan_public: idle, corrupt, running, deadline, completed fields only',function()
  t.eq(C.scan_public(obj(),NOW),{state='IDLE'})
  t.eq(C.scan_public(obj({request_id='x'}),NOW),{state='IDLE'})
  local id=string.rep('a',32)
  t.eq(C.scan_public(obj({request_id=id,state='WAT',requested_at=NOW}),NOW),{state='FAILED',code='SCAN-STATE-CORRUPT'})
  t.eq(C.scan_public(obj({request_id=id,state='QUEUED',requested_at=true}),NOW),{state='FAILED',code='SCAN-STATE-CORRUPT'})
  local running=C.scan_public(obj({request_id=id,state='RUNNING',requested_at=canon.float(NOW-10),started_at=canon.float(NOW-9),extra=1}),NOW)
  t.eq(running,{request_id=id,state='RUNNING',requested_at=NOW-10,started_at=NOW-9})
  t.eq(C.scan_public(obj({request_id=id,state='QUEUED',requested_at=canon.float(NOW-301)}),NOW).code,'SCAN-DEADLINE-EXCEEDED')
  t.eq(C.scan_public(obj({request_id=id,state='QUEUED',requested_at=canon.float(NOW+1)}),NOW).state,'FAILED')
  t.eq(C.scan_public(obj({request_id=id,state='COMPLETED',requested_at=canon.float(NOW-900),checked=2,failed=0,code=NULL}),NOW),
    {request_id=id,state='COMPLETED',requested_at=NOW-900,checked=2,failed=0,code=NULL})
end)

local SRC,TGT='wireguard:peer_3','openvpn:1_2'
local function pair_case(over)
  over=over or {}
  local env=file_env({})
  local revision=string.rep('b',32)
  local state=obj({id=string.rep('a',32),phase='RUNNING',owned=arr({'wgclient1','ovpnclient1'}),before_flags=obj({wgclient1='1',ovpnclient1='1'}),
    network_identity=string.rep('b',64),protected=obj(),order=arr({'s','t'}),policy_hash=string.rep('c',64),revision=revision})
  for k,v in pairs(over.state or {}) do state[k]=v end
  require('pair').save(env,state)
  return env,revision
end

t.test('pair_controls: not active, active quiet, kernel of the supervisor, rate limit only without the instant switch',function()
  local env,revision=pair_case()
  local files={}
  local status=obj({profiles=arr({obj({id=SRC,time=NOW-1,code=NULL,dns_ok=true,https_success=2}),obj({id=TGT,time=NOW-1,code=NULL,dns_ok=true,https_success=3})})})
  local native=obj({state='OBSERVING',time=canon.float(NOW-1),source=SRC,target=TGT,mode='continuous-pair'})
  local intent=obj({mode='on',id=string.rep('a',32),revision=revision,time=canon.float(NOW)})
  local ledger=obj({events=arr()})
  local d={now=NOW,read_state=function() return require('pair').read_state(env) end,intent=function() return intent end,
    current_revision=function() return revision end,validate_bindings=function(b) return require('identity').validate(b) end,
    settings=function() return obj({interval='10'}) end,order=function() return arr({'s','t'}),string.rep('c',64) end,
    native=function() return native end,status=function() return status end,journal=function() return obj() end,
    queued=function() return obj() end,ledger=function() return ledger end,kernel=function() return obj() end,fast=function() return true end}
  local r=C.pair_controls(d)
  t.eq(r.available,true);t.eq(r.control_revision,revision);t.eq(r.observation_valid_for,30);t.eq(r.instant,false)
  t.eq(r.primary,{allowed=false,blockers={'RETURN-NOT-APPLICABLE'}});t.eq(r.reserve,{allowed=true,blockers={}})
  t.eq(r.resume,{allowed=false,blockers={}});t.eq(r.hold,NULL)
  ledger=obj({events=arr({canon.float(NOW-10),canon.float(NOW-20),canon.float(NOW-30)})})
  r=C.pair_controls(d)
  t.eq(r.reserve.blockers,{'PAIR-RATE-LIMIT'},'outside a general pair session the limit applies')
  ledger=obj({events=arr({canon.float(NOW-10)})})
  t.eq(C.pair_controls(d).reserve.blockers,{'PAIR-MANUAL-COOLDOWN'})
  ledger=obj({events='bad'})
  r=C.pair_controls(d)
  t.eq(r.available,false);t.eq(r.blockers,{'PAIR-MANUAL-STATE-UNVERIFIED'})
  intent=obj({mode='off',id=string.rep('a',32),revision=revision,time=canon.float(NOW)})
  t.eq(canon.encode(C.pair_controls(d)),'{"available":false,"mode":"continuous-pair","time":1792750000.5}')
  t.eq(#files,0)
end)

t.test('channel_path.page_kernel: the supervisor proof only under the channel_path rule',function()
  local cp=require('channel_path')
  local proof=require('pair').policy.proof(obj({source_rule='r1',target_rule='r2',direction='first',order=arr({'r1','r2'}),
    source=obj({id=SRC}),target=obj({id=TGT})}))
  local state=obj({phase='RUNNING',order=arr({'r1','r2'}),policy_hash='h',policy_roles=proof})
  local native=obj({state='OBSERVING',source=SRC,target=TGT,
    channel_path=page.from_kernel({verified=true,role='source',profile_id=SRC,time=NOW-3},SRC,TGT,NOW-2)})
  local k=cp.page_kernel(native,state,{arr({'r1','r2'}),'h'},NOW)
  t.eq(k.verified,true);t.eq(k.role,'source')
  t.eq(cp.page_kernel(native,state,{arr({'r1','r2'}),'h'},NOW+20),nil,'older than 15 s')
  t.eq(cp.page_kernel(native,state,{arr({'r2','r1'}),'h'},NOW),nil,'the live order selects the other role')
  native.channel_path=page.from_kernel(nil,SRC,TGT,NOW-2)
  t.eq(cp.page_kernel(native,state,{arr({'r1','r2'}),'h'},NOW),nil,'no confirmed proof')
end)

------------------------------------------------------------------------------------------------------
-- the monitor: Lua answers, no Python child; the bridge only after a failed Lua computation
------------------------------------------------------------------------------------------------------
local monitor=require('monitor')
local function put(R,path,value) R.write_atomic(path,canon.encode(value)) end

t.test('status reply: manual_switch_control and scan from Lua, no bridge child at all',function()
  local R=t.fake_runner()
  put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  R.native_policy=obj({sections=arr(),settings=obj({interval='10'})})
  local m=monitor.new(R)
  m:pass()
  local reply
  for _=1,6 do reply=m.rpc.handle('status','{}');R.advance(15) end
  t.eq(#R.bridge_runs,0,'six page polls in 90 s start no Python')
  t.eq(reply.manual_switch_control.available,false);t.eq(reply.manual_switch_control.mode,'continuous-pair')
  t.eq(reply.manual_switch_control.bridge,nil,'a computed answer, not the pending placeholder')
  t.eq(reply.scan,{state='IDLE'})
  put(R,'/run/hv/scan.state',obj({request_id=string.rep('d',32),state='RUNNING',requested_at=canon.float(R.now-5),started_at=canon.float(R.now-4)}))
  reply=m.rpc.handle('status','{}')
  t.eq(reply.scan.state,'RUNNING')
  R.files['/run/hv/scan.state']='{bad'
  reply=m.rpc.handle('status','{}')
  t.eq(reply.scan,nil,'a damaged scan.state leaves the field out (as the bridge did)')
  local record=m:backend_record()
  t.eq(#record.bridges,0)
  local native={};for _,name in ipairs(record.native) do native[name]=true end
  t.truthy(native.manual_switch_control and native.scan)
end)

t.test('status reply: a failed Lua computation asks the bridge on demand, at most every 10 s',function()
  local R=t.fake_runner()
  put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  local m=monitor.new(R)
  m:pass()
  local original=C.manual_switch_control
  C.manual_switch_control=function() error('boom',0) end
  local ok,err=pcall(function()
    local reply=m.rpc.handle('status','{}')
    t.eq(#R.bridge_runs,1);t.eq(reply.manual_switch_control.blockers,{'PAIR-MANUAL-STATE-UNVERIFIED'});t.eq(reply.manual_switch_control.bridge,'pending')
    t.eq(reply.manual_switch.state,'IDLE')
    m.rpc.handle('status','{}')
    t.eq(#R.bridge_runs,1,'at most one refresh per 10 s')
    put(R,'/run/hv/status-bridge.json',obj({time=R.now,manual_switch_control=obj({available=true,mode='continuous-pair',blockers=arr()})}))
    reply=m.rpc.handle('status','{}')
    t.eq(reply.manual_switch_control.available,true)
    R.advance(31)
    reply=m.rpc.handle('status','{}')
    t.eq(reply.manual_switch_control.available,false,'an old bridge answer is not used');t.eq(#R.bridge_runs,2)
  end)
  C.manual_switch_control=original
  if not ok then error(err,0) end
end)

t.test('legacy controls: display diagnostic reused 15 s, else the Lua diagnostic once, then cached; a failure is UNAVAILABLE',function()
  local R=t.fake_runner()
  put(R,'/run/hv/native-status.json',obj({state='DISABLED',time=R.now-1}))
  R.native_policy=obj({sections=arr(),settings=obj({native_trial='t1'})})
  local m=monitor.new(R)
  m:pass()
  local runs=0
  m.diagnostic_override=function() runs=runs+1;return arr({'VENDOR-WORKER-BUSY'}),nil end
  local reply=m.rpc.handle('status','{}')
  t.eq(runs,1);t.eq(#R.bridge_runs,0)
  local c=reply.manual_switch_control
  t.eq(c.mode,nil,'the legacy control_status shape');t.eq(c.available,false)
  t.eq(c.reserve.blockers,{'MANUAL-SELECTION-UNVERIFIED','VENDOR-WORKER-BUSY'})
  m.rpc.handle('status','{}');R.advance(10);m.rpc.handle('status','{}')
  t.eq(runs,1,'display-diagnostic.json younger than 15 s is reused')
  R.advance(6);m.rpc.handle('status','{}')
  t.eq(runs,2)
  R.advance(20)
  m.diagnostic_override=function() error('no backend',0) end
  reply=m.rpc.handle('status','{}')
  t.eq(#R.bridge_runs,1,'the Lua diagnostic failed: the bridge answers this once');t.eq(reply.manual_switch_control.bridge,'pending')
end)

t.run()
