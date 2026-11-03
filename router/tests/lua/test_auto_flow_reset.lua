-- flow_reset.lua + its two call sites (transaction COMMITTED, rollback ROLLED-BACK). The decision cases are shared
-- with tests/test_flow_reset.py (tests/flow_reset_cases.json): Lua and Python drop exactly the same flows.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local F=require('flow_reset')
local T=require('transaction')
local R=require('rollback')

local function read_file(path) local f=assert(io.open(path,'rb'));local text=f:read('*a');f:close();return text end
local CASES=canon.decode(read_file(t.here..'/../flow_reset_cases.json')).cases
local function plain(v) if v==canon.null then return nil end;return v end

for _,case in ipairs(CASES) do
  t.test('shared: '..case.name,function()
    local ran,logs={},{}
    local ctx={config=plain(case.config),old_status=plain(case.old),new_status=plain(case.new),
      exec=function(argv)
        ran[#ran+1]=argv
        if case.exec.raise==true then error('runner failed') end
        return canon.number(case.exec.rc),case.exec.out,case.exec.timed_out==true
      end,
      log=function(line) logs[#logs+1]=line end}
    local result=F.run(ctx)
    local e=case.expect
    t.eq(result.code,e.code,'code');t.eq(result.deleted,canon.number(e.deleted),'deleted');t.eq(result.address,plain(e.address),'address')
    if plain(e.argv)==nil then t.eq(#ran,0,'no command') else t.eq(#ran,1,'one command');t.eq(canon.array(ran[1]),e.argv,'argv') end
    if plain(e.log)==nil then t.eq(#logs,0,'no log') else t.eq(#logs,1,'one log');t.eq(logs[1],e.log,'log') end
  end)
end

t.test('the command never names a mark, a protocol or a WAN device: only the old NAT address',function()
  t.eq(canon.array(F.argv('10.5.0.2')),canon.array({'conntrack','-D','-f','ipv4','--reply-dst','10.5.0.2','--src-nat'}))
  t.eq(F.TIMEOUT,1)
end)

local function recorder(env)
  local calls={}
  env.backend.flow_reset=function(old,new) calls[#calls+1]={old,new};return {code='FLOW-RESET-DONE',deleted=1} end
  return calls
end

t.test('reset_old_flows: roles, missing backend method, failures are a code only',function()
  local env=t.env()
  local value={source='wireguard:peer_1',target='openvpn:1_1'}
  t.eq(T.reset_old_flows(env,value,'target'),nil,'fake backend without flow_reset: nothing')
  local calls=recorder(env)
  t.eq(T.reset_old_flows(env,value,'target'),'FLOW-RESET-DONE')
  t.eq(T.reset_old_flows(env,value,'source'),'FLOW-RESET-DONE')
  t.eq(calls,{{'wireguard:peer_1','openvpn:1_1'},{'openvpn:1_1','wireguard:peer_1'}})
  t.eq(T.reset_old_flows(env,value,nil),nil,'unknown role: no guess');t.eq(#calls,2)
  env.backend.flow_reset=function() error('boom') end
  t.eq(T.reset_old_flows(env,value,'target'),'FLOW-RESET-FAILED')
  env.backend.flow_reset=function() error(setmetatable({code='COMMAND-FAILED'},require('auto_control').Refused),0) end
  t.eq(T.reset_old_flows(env,value,'target'),'FLOW-RESET-FAILED')
end)

local function pair_attempt(env)
  local opts={control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})}
  return T.attempt(env,env.backend.selection,env.run.wall()+3600,false,opts)
end

t.test('failover COMMITTED resets the flows of the primary just left, once, after the guard',function()
  local env=t.env()
  local calls=recorder(env)
  local order={}
  local guard=env.backend.guard
  env.backend.guard=function(...) order[#order+1]='guard';return guard(...) end
  local reset=env.backend.flow_reset
  env.backend.flow_reset=function(...) order[#order+1]='reset';return reset(...) end
  pair_attempt(env)
  t.eq(t.journal(env).phase,'COMMITTED')
  t.eq(calls,{{'wireguard:peer_1','openvpn:1_1'}})
  t.eq(order[#order],'reset','the reset is the last router step');t.truthy(order[1]=='guard','guard before the reset')
end)

t.test('a failed reset never fails or undoes the committed switch',function()
  local env=t.env()
  env.backend.flow_reset=function() error('conntrack exploded') end
  pair_attempt(env)
  local j=t.journal(env)
  t.eq(j.phase,'COMMITTED');t.eq(env.backend.kernel,{'r2','r1'})
end)

t.test('return to the primary (finish_committed -> ROLLED-BACK) resets the reserve flows',function()
  local env=t.env()
  pair_attempt(env)
  local calls=recorder(env)
  local j=t.journal(env)
  T.finish_committed(env,j,'PRIMARY-STABLY-RECOVERED')
  j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(env.backend.kernel,{'r1','r2'})
  t.eq(calls,{{'openvpn:1_1','wireguard:peer_1'}})
end)

t.test('a failed switch rolled back after the kernel write resets the reserve flows; a refusal before any write does not',function()
  local env=t.env()
  local calls=recorder(env)
  env.backend.fail_apply='VENDOR-APPLY-FAILED'
  t.code('VENDOR-APPLY-FAILED',pair_attempt,env)
  t.eq(t.journal(env).phase,'ROLLED-BACK')
  t.eq(calls,{{'openvpn:1_1','wireguard:peer_1'}})
  local env2=t.env()
  local calls2=recorder(env2)
  env2.backend.blockers={'VENDOR-SETTLING'}
  pcall(pair_attempt,env2)
  t.eq(#calls2,0,'nothing moved, nothing reset')
end)

t.test('rollback.lua and transaction.lua call the same helper',function()
  local text=read_file(t.here..'/../../files/usr/lib/homensai-vpn/lua/rollback.lua')
  t.truthy(string.find(text,'T.reset_old_flows(env,value,',1,true))
  t.eq(type(R.rollback),'function')
end)

t.run()
