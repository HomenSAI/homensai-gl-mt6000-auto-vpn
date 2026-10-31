-- manual.lua, the checks before the policy write of an instant click (plan item 4): the target's health (fresh
-- monitor row, else one live probe), the stock boot prefix (prepare only when it is not already in place), the
-- journal transaction. A refusal before the write leaves the policy and the journal untouched.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local manual=require('manual')
local P=pair.policy

local function setup(opts)
  opts=opts or {}
  local env=t.env()
  local now=env.run.wall()
  local sel=env.backend.selection
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(now-10),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,policy_roles=P.proof(sel)})
  pair.save(env,state)
  local row=canon.object({id=string.rep('ab',16),pair=state.id,revision=env.revision,direction='reserve',state='QUEUED',requested=canon.float(now),updated=canon.float(now),
    selection=canon.object({tx=canon.null}),code=canon.null,request_source='manual'})
  env.run.fs.write_atomic(env.runtime..'/pair-manual-control.json',canon.encode(row))
  local fresh=opts.fresh~=false
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({profiles=canon.array({
    canon.object({id=sel.target.id,time=canon.float(fresh and now-2 or now-600),code=canon.null,dns_ok=true,https_success=2})})})))
  local calls={assess=0,prepare=0,health=0}
  env.deps.rtp_boot={assess=function() calls.assess=calls.assess+1;if opts.assess_refuses then require('auto_control').refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end
                       return canon.object({safe=true,ready=opts.ready~=false,kernel_verified=false}) end,
                     prepare=function() calls.prepare=calls.prepare+1;return {prepared=true,changed=true} end}
  local health=env.backend.health
  env.backend.health=function(id,reuse) calls.health=calls.health+1;return health(id,reuse) end
  return env,state,calls
end

t.test('ready boot prefix: no prepare (no extra control lock); a fresh healthy monitor row: no live probe',function()
  local env,state,calls=setup()
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'COMPLETED')
  t.eq(calls,{assess=1,prepare=0,health=0})
  t.eq(t.journal(env).phase,'HELD-ON-RESERVE');t.eq(env.backend.kernel,{'r2','r1'})
end)

t.test('a boot prefix that is not in place is still prepared before the write',function()
  local env,state,calls=setup({ready=false})
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'COMPLETED');t.eq(calls.prepare,1)
end)

t.test('refusals before the write keep the policy and the journal untouched',function()
  local env,state,calls=setup({assess_refuses=true})
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'REFUSED');t.eq(manual.read(env).code,'RTP-BOOT-PRECONDITION-UNVERIFIED')
  t.eq(env.backend.uci,{'r1','r2'});t.eq(t.journal(env).phase,nil);t.eq(calls.prepare,0)
  -- a stale monitor row: one live probe of the target decides; unhealthy refuses before any write
  env,state,calls=setup({fresh=false})
  env.backend.health_of[env.backend.selection.target.id]=false
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'REFUSED');t.eq(manual.read(env).code,'PAIR-MANUAL-TARGET-UNHEALTHY')
  t.eq(calls.health,1);t.eq(calls.assess,0);t.eq(env.backend.uci,{'r1','r2'});t.eq(t.journal(env).phase,nil)
  env,state,calls=setup({fresh=false})
  t.eq(manual.consume(env,state,t.settings(),env.revision),true)
  t.eq(manual.read(env).state,'COMPLETED');t.eq(calls.health,1)
end)

t.run()
