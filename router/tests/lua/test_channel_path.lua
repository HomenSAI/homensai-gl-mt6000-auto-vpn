-- channel_path.lua (plan item 4): channel_path.public_status for the Lua monitor without status_bridge.py.
-- Python differential mode (tests/test_lua_channel_path.py):
--   lua test_channel_path.lua --cases   reads a JSON array of cases on stdin, prints a JSON array of results.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local C=require('channel_path')
local obj,arr=canon.object,canon.array
local NULL=canon.null

if arg[1]=='--cases' then
  local cases=canon.decode(io.read('*a'))
  local out=arr()
  for _,case in ipairs(cases) do
    local live=NULL
    if canon.is_array(case.live) then live={case.live[1],case.live[2]} else live=nil end
    local now=canon.number(case.now)
    local ok,result
    if case.kind=='snapshot' then ok,result=pcall(C.snapshot,case.status,case.journal,live,now)
    else
      local kernel=case.kernel;if kernel==NULL then kernel=nil end
      ok,result=pcall(C.pair_snapshot,case.status,case.state,case.journal,live,now,kernel)
    end
    out[#out+1]=ok and result or obj({lua_error=tostring(type(result)=='table' and result.code or result)})
  end
  io.write(canon.encode(out))
  os.exit(0)
end

local NOW=1793420000
local SRC,TGT='openvpn:1_1','wireguard:peer_2'
local function selection()
  return obj({source_rule='r1',target_rule='r2',direction='first',order=arr({'r1','r2'}),generic_rules=arr({'r1','r2'}),
    source=obj({id=SRC}),target=obj({id=TGT})})
end
local function state()
  local proof=require('pair').policy.proof(selection())
  return obj({phase='RUNNING',order=arr({'r1','r2'}),policy_hash='h',policy_roles=proof})
end
local function native(over)
  local n=obj({state='OBSERVING',mode='continuous-pair',proof_scope='router-probed-ipv4',time=NOW-2,source=SRC,target=TGT,blockers=arr(),
    channel_path=require('monitor_status').from_kernel({verified=true,role='source',profile_id=SRC,time=NOW-3},SRC,TGT,NOW-2)})
  for k,v in pairs(over or {}) do n[k]=v end
  return n
end
local function deps(over)
  over=over or {}
  return {journal=function() if over.journal_error then error({code='JOURNAL-INTEGRITY-FAILED'},0) end;return over.journal or obj() end,
    state=function() return over.state or state() end,
    order=function(bindings) over.bindings=bindings;return over.order or arr({'r1','r2'}),over.hash or 'h' end}
end

t.test('public_status: the supervisor proof of this session makes the primary green',function()
  local status=obj({time=NOW-5,native_failover=native()})
  local path=C.public_status(deps(),status,NOW)
  t.eq(path.confirmed,true);t.eq(path.kernel_policy_verified,true);t.eq(path.active_profile_id,SRC);t.eq(path.code,NULL)
  t.eq(path.configured_profile_id,SRC);t.eq(path.checked_at,NOW-3);t.eq(path.selection_proof,'fw3-kernel-marking')
end)

t.test('public_status: no fresh supervisor proof, another role, a changed order or a transition never give green',function()
  local function code(n,over) return C.public_status(deps(over),obj({time=NOW-5,native_failover=n}),NOW) end
  local stale=native();stale.channel_path.checked_at=NOW-20
  t.eq(code(stale).code,'KERNEL-POLICY-UNVERIFIED','older than 15 s')
  local other=native({channel_path=require('monitor_status').from_kernel({verified=true,role='target',profile_id=TGT,time=NOW-3},SRC,TGT,NOW-2)})
  t.eq(code(other).confirmed,false,'the proof names the reserve while the live order selects the primary')
  t.eq(code(native(),{order=arr({'r2','r1'})}).confirmed,false,'the live order differs from the session')
  t.eq(code(native(),{hash='x'}).confirmed,false)
  local moving=native({state='APPLYING'})
  local r=code(moving);t.eq(r.transitioning,true);t.eq(r.confirmed,false)
  local blocked=native({state='BLOCKED',blockers=arr({'KERNEL-POLICY-UNVERIFIED'})})
  r=code(blocked);t.eq(r.code,'KERNEL-POLICY-UNVERIFIED');t.eq(r.source_profile_id,SRC)
  local foreign=native();foreign.channel_path.target_profile_id='wireguard:peer_9'
  t.eq(code(foreign).confirmed,false,'a proof of another pair')
  local s=state();s.phase='STOPPING'
  t.eq(code(native(),{state=s}).confirmed,false,'the session is not RUNNING')
  t.eq(C.public_status(deps(),obj({time=NOW-200,native_failover=native()}),NOW).confirmed,false,'a stale monitor')
end)

t.test('public_status: read failures are fail-safe; non-pair mode uses the legacy snapshot',function()
  local r=C.public_status(deps({journal_error=true}),obj({time=NOW,native_failover=native()}),NOW)
  t.eq(r.code,'KERNEL-POLICY-UNVERIFIED');t.eq(r.source_profile_id,SRC)
  r=C.public_status(deps({journal_error=true}),obj({time=NOW,native_failover=obj({state='OBSERVING'})}),NOW)
  t.eq(r.scope,'client-confirmed general VPN rule');t.eq(r.confirmed,false)
  local bad=state();bad.process_bindings=obj({wgclient1=1})
  r=C.public_status(deps({state=bad}),obj({time=NOW,native_failover=native()}),NOW)
  t.eq(r.code,'KERNEL-POLICY-UNVERIFIED','invalid process bindings: POLICY-IDENTITY-CHANGED -> fail-safe')
  local d=deps({state=obj()})
  r=C.public_status(d,obj({time=NOW,native_failover=obj({state='OBSERVING'})}),NOW)
  t.eq(r.scope,'client-confirmed general VPN rule','no journal, no pair: the empty legacy snapshot')
end)

t.run()
