-- Harness for the hv-auto Lua tests: fake runner (memory or real-file fs, fake clocks, lock, revision fence),
-- fake Linux backend (UCI order + kernel order + attestation), fixtures and the test runner.
-- Module search order: $HOMENSAI_LUA_CORE (the lua-core worktree), the project lua dir, then tests/lua/stubs.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
local core=os.getenv('HOMENSAI_LUA_CORE')
package.path=(core and (core..'/?.lua;') or '')..here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/stubs/?.lua;'..here..'/?.lua;'..package.path
-- the write stage of the instant switch is always the fake (the real one needs uci/iptables on a router)
package.preload['instant_switch']=function() return dofile(here..'/stubs/instant_switch.lua') end
local canon=require('canon')
pcall(canon.configure,{runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or os.getenv('TMPDIR') or '/tmp'})
local journal=require('journal')

local H={here=here,cases={},failures=0}
H.canon=canon

function H.test(name,fn) H.cases[#H.cases+1]={name,fn} end
local function show(v)
  if type(v)=='table' then local ok,text=pcall(canon.encode,v);if ok then return text end end
  if type(v)=='string' then return string.format('%q',v) end
  return tostring(v)
end
H.show=show
function H.eq(actual,expected,message)
  local a,b=show(actual),show(expected)
  if a~=b then error((message or 'not equal')..': got '..a..', expected '..b,2) end
end
function H.truthy(v,message) if not v then error(message or 'expected a true value',2) end end
function H.code(expected,fn,...)
  local ok,err=pcall(fn,...)
  if ok then error('expected '..expected..', got success',2) end
  local code=type(err)=='table' and err.code or tostring(err)
  if code~=expected then error('expected '..expected..', got '..tostring(code),2) end
  return err
end
function H.run()
  local passed=0
  for _,case in ipairs(H.cases) do
    local ok,err=pcall(case[2])
    if ok then passed=passed+1
    else H.failures=H.failures+1;io.stderr:write('FAIL ',case[1],': ',tostring(type(err)=='table' and (err.code or show(err)) or err),'\n') end
  end
  local name=(arg and arg[0] or '?'):match('([^/]*)$')
  if H.failures==0 then print(name..': '..passed..' tests OK') else print(name..': '..H.failures..' FAILED of '..#H.cases) end
  os.exit(H.failures==0 and 0 or 1)
end

------------------------------------------------------------------------------------------------------
-- file systems
------------------------------------------------------------------------------------------------------
function H.memory_fs()
  local files={}
  return {files=files,
    read=function(path) return files[path] end,
    write_atomic=function(path,text) files[path]=text end,
    rename=function(a,b) files[b]=files[a];files[a]=nil end,
    remove=function(path) files[path]=nil end}
end
function H.real_fs()
  return {
    read=function(path) local f=io.open(path,'rb');if not f then return nil end;local t=f:read('*a');f:close();return t end,
    write_atomic=function(path,text)
      local dir=string.match(path,'^(.*)/[^/]+$');os.execute('mkdir -p "'..dir..'"')
      local f=assert(io.open(path..'.pending','wb'));f:write(text);f:close();assert(os.rename(path..'.pending',path))
    end,
    rename=function(a,b) assert(os.rename(a,b)) end,
    remove=function(path) os.remove(path) end}
end

------------------------------------------------------------------------------------------------------
-- fake runner
------------------------------------------------------------------------------------------------------
function H.runner(fs,runtime)
  local run={fs=fs,RUNTIME=runtime,wall_now=1761830400,mono_now=1000,locks=0}
  function run.wall() return run.wall_now end
  function run.clock() return run.mono_now end
  function run.advance(seconds) run.wall_now=run.wall_now+seconds;run.mono_now=run.mono_now+seconds end
  function run.sha256(text) return canon.sha256(text) end
  function run.lock(fn,directory) run.locks=run.locks+1;local r={pcall(fn)};run.locks=run.locks-1;if not r[1] then error(r[2],0) end;return unpack(r,2) end
  function run.require_revision(expected,directory)
    local text=fs.read((directory or runtime)..'/auto-control-revision.json')
    local ok,record=pcall(canon.decode,text or '')
    if not ok or not canon.is_object(record) or record.revision~=expected or type(expected)~='string' or #expected~=32 then
      error(setmetatable({code='CLIENT-STOP'},require('auto_control').Refused),0)
    end
  end
  function run.fenced(expected,fn) return run.lock(function() run.require_revision(expected);return fn() end) end
  return run
end

------------------------------------------------------------------------------------------------------
-- fixtures
------------------------------------------------------------------------------------------------------
H.HEX64=string.rep('ab',32)
H.HEX32=string.rep('cd',16)
H.GEN1=string.rep('01',16)
H.GEN2=string.rep('02',16)
function H.selection(overrides)
  local s=canon.object({
    source=canon.object({id='wireguard:peer_1',protocol='wireguard',interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',vendor_generation=H.GEN1}),
    target=canon.object({id='openvpn:1_1',protocol='openvpn',interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=H.GEN2}),
    source_rule='r1',target_rule='r2',order=canon.array({'r1','r2'}),generic_rules=canon.array({'r1','r2'}),hash=H.HEX64,direction='first',
    process_bindings=canon.object({wgclient1=4096,ovpnclient1=45056}),proof_scope='router-probed-ipv4',vendor_identity=string.rep('ef',32),settings_hash=string.rep('12',32)})
  for k,v in pairs(overrides or {}) do s[k]=v end
  return s
end
function H.settings(overrides)
  local s=canon.object({native_trial=H.HEX32,native_until=tostring(1761830400+3600),native_enabled='1',native_session_loss='1',pair_auto_mode='router-probed-ipv4',
    native_proof_scope='router-probed-ipv4',terms_version='1',interval='10'})
  for k,v in pairs(overrides or {}) do s[k]=v end
  return s
end

------------------------------------------------------------------------------------------------------
-- fake Linux backend: UCI order (`uci`) and kernel order (`kernel`) with an attestation derived from them
------------------------------------------------------------------------------------------------------
function H.backend(run,selection,settings)
  local pair=require('pair')
  local B={uci={'r1','r2'},kernel={'r1','r2'},hash=selection.hash,selection=selection,settings=settings,blockers={},guarded=false,guard_calls={},
           health_of={},trace_of={['wireguard:peer_1']='198.51.100.1',['openvpn:1_1']='203.0.113.5'},probe_ok=true,fail_apply=nil,on_probe=nil,fast=true,cleared=0,leases={}}
  local function copy(t) local o={};for i,x in ipairs(t) do o[i]=x end;return canon.array(o) end
  function B.policy() return canon.object({settings=B.settings,sections=canon.array({})}) end
  function B.order() return copy(B.uci),B.hash end
  function B.diagnostic() local b={};for i,x in ipairs(B.blockers) do b[i]=x end;return b,(#b==0) and B.selection or nil end
  function B.kernel_fingerprint() return canon.sha256('kernel:'..table.concat(B.kernel,',')) end
  function B.attest_policy(sel)
    local proof=pair.policy.proof(B.selection)
    local ok,role=pcall(pair.policy.role,proof,copy(B.kernel))
    local uci_eq=table.concat(B.kernel,',')==table.concat(B.uci,',')
    return canon.object({verified=ok and uci_eq,role=ok and role or canon.null,kernel_fingerprint=B.kernel_fingerprint(),order=copy(B.kernel),policy_hash=B.hash,time=canon.float(run.wall())})
  end
  function B.reorder(order,before_write,write_command)
    local function set() B.uci=copy(order) end
    if write_command then write_command('uci',set) else set() end
  end
  function B.apply(write_command)
    local function set()
      B.kernel=copy(B.uci)
      if B.fail_apply then local code=B.fail_apply;B.fail_apply=nil;error(setmetatable({code=code},require('auto_control').Refused),0) end
    end
    if write_command then write_command('kernel',set) else set() end
  end
  function B.uci_commit() end
  function B.guard(devices,revision) B.guarded=true;B.guard_calls[#B.guard_calls+1]=devices and 'vpn-only' or 'full' end
  function B.unguard() B.guarded=false end
  function B.guard_exists() return B.guarded end
  function B.devices() return {'wgclient1','ovpnclient1'} end
  function B.health(id) local h=B.health_of[id];if h==nil then return true end;return h end
  function B.recovery_ready(id,settings) return B.health(id)==true end
  function B.probe(profile) if B.on_probe then B.on_probe() end;if B.probe_ok then return canon.object({code=canon.null,dns_ok=true,https_success=2}) end;return canon.object({code='VPN-001'}) end
  function B.trace(profile) return B.trace_of[profile.id] end
  function B.candidates() return canon.array({}) end
  function B.acceleration() return canon.object({loaded=canon.array({}),hnat_runtime='disabled'}) end
  function B.use_process_bindings(b) B.bindings=b end
  function B.clear_native_options() B.cleared=B.cleared+1;return true end
  function B.write_lease(scope,trial,until_) B.leases[#B.leases+1]={scope,trial,until_};B.settings.native_trial=trial;B.settings.native_until=until_ end
  function B.fast_switch_enabled() return B.fast end
  function B.history_days() return 7 end
  function B.instant_request(sel,after) return canon.object({r1='cfg01',r2='cfg02'}),canon.array({'5841','4192'}) end
  function B.pair_preflight(settings) return B.selection end
  function B.selection_interfaces(sel) return canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}) end
  return B
end

-- env with everything wired; opts.fs (default memory), opts.runtime/persist
function H.env(opts)
  opts=opts or {}
  local fs=opts.fs or H.memory_fs()
  local runtime,persist=opts.runtime or '/run/hv',opts.persist or '/etc/hv'
  local run=H.runner(fs,runtime)
  local selection=opts.selection or H.selection()
  local settings=opts.settings or H.settings()
  local backend=H.backend(run,selection,settings)
  local env={run=run,backend=backend,runtime=runtime,persist=persist,stopped=false,slept={},
    localdate=function(fmt,t) return os.date('!'..fmt,t) end,version='2.0.0-lua-alpha2',
    deps={resolve_pair=function(status,settings,now,age,settle)
            return {coordination={state='READY'},source=selection.source,target=selection.target} end}}
  env.stop=function() return env.stopped end
  env.sleep=function(s) env.slept[#env.slept+1]=s;run.advance(s) end
  -- control revision file like Python's start: {"revision": hex32}
  env.revision=string.rep('77',16)
  fs.write_atomic(runtime..'/auto-control-revision.json',canon.encode(canon.object({revision=env.revision})))
  -- the fake instant switch (stub instant_switch.lua) plays the write stage on the backend
  run.fake_instant=function(request,direction,ienv)
    local value=request.journal
    local jenv={fs=fs,path=ienv and ienv.journal_path or persist..'/native-transaction.json',now=run.wall,hash=run.sha256,template=canon.decode(canon.encode(value))}  -- like instant_switch: the request journal pins the delegated records
    local current=journal.read(jenv)
    if not journal.settled(current) then return canon.object({ok=false,code='TRANSACTION-IN-PROGRESS'}),2 end
    local ok,err=pcall(run.fenced,request.control_revision,function() journal.write(jenv,value) end)
    if not ok then return canon.object({ok=false,code=err.code or 'NATIVE-SYSTEM-001'}),2 end
    local wrote=false
    local sok,serr=pcall(function()
      run.fenced(request.control_revision,function() wrote=true;backend.uci=value.after end)
      run.fenced(request.control_revision,function() backend.kernel=value.after end)
      if backend.fail_instant then local c=backend.fail_instant;backend.fail_instant=nil;error(setmetatable({code=c},require('auto_control').Refused),0) end
    end)
    if not sok then
      value.failure_code=serr.code
      if not wrote then value.phase='ROLLED-BACK';value.reason='FAILED-BEFORE-APPLY';value.restored_order=value.before;value.finished=canon.float(run.wall()) end
      journal.write(jenv,value)
      return canon.object({ok=false,code=serr.code,rollback_required=wrote}),2
    end
    value.phase='HELD-ON-RESERVE';value.reason='OPERATOR-MANUAL';value.confirmed=canon.float(run.wall());value.reserve_healthy=true
    value.instant_seconds=canon.float(0.5)
    run.fenced(request.control_revision,function() journal.write(jenv,value) end)
    return canon.object({ok=true,code=canon.null,phase='HELD-ON-RESERVE'}),0
  end
  return env
end

function H.read(env,path) local text=env.run.fs.read(path);return text and canon.decode(text) or nil end
function H.journal(env) return require('transaction').journal_read(env) end
function H.history(env)
  local text=env.run.fs.read(env.persist..'/native-history.json')
  return text and canon.decode(text).data or nil
end
function H.states(env)
  local out={}
  for _,row in ipairs(H.history(env).events) do out[#out+1]=row.state end
  return out
end
return H
