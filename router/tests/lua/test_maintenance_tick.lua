-- Plan item 54 (audit F-16): pair.tick begins no new session while a package operation holds the maintenance marker;
-- the Start stays queued and begins once the marker is gone (or stale). Python twin: test_maintenance_gates.py
-- (pair_auto.tick).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')

t.test('pair.tick: no new session during a package operation, the Start stays queued',function()
  local env=t.env()
  local id=string.rep('21',16)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,
    time=canon.float(env.run.wall()),id=id})))
  local began=0
  env.backend.pair_preflight=function() began=began+1;error(setmetatable({code='PAIR-PLATFORM-UNVERIFIED'},require('auto_control').Refused),0) end
  env.run.fs.write_atomic(env.persist..'/maintenance.json',canon.encode(canon.object({action='upgrade',time=canon.float(env.run.wall()-5)})))
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  t.eq(began,0,'begin never ran')
  local status=t.read(env,env.runtime..'/native-status.json')
  t.eq({status.state,status.reason,status.blockers},{'ARMED','MAINTENANCE-IN-PROGRESS',canon.array({'MAINTENANCE-IN-PROGRESS'})})
  t.eq(pair.intent(env).mode,'on','the Start stays queued')
  t.eq(next(pair.read_state(env)),nil,'nothing acquired')
  -- the marker is gone: the same Start begins (here its preflight refuses, proving begin ran)
  env.run.fs.remove(env.persist..'/maintenance.json')
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  t.eq(began,1)
end)

-- audit F-17: the shutdown leaves its recovery result for the package prerm guard after the stop
t.test('auto.shutdown: supervisor-shutdown.json says whether the pair recovery finished',function()
  local auto=require('auto')
  local env=t.env()
  auto.shutdown(env)
  local row=t.read(env,env.runtime..'/supervisor-shutdown.json')
  t.eq({row.ok,row.code},{true,canon.null})
  local real=pair.recover
  pair.recover=function() return false end
  local ok,err=pcall(auto.shutdown,env)
  pair.recover=real
  t.truthy(ok,err)
  row=t.read(env,env.runtime..'/supervisor-shutdown.json')
  t.eq({row.ok,row.code},{false,'PAIR-RECOVERY-REQUIRED'})
end)

-- IR-05 (integration review 07.11.2026): the first prerm guard pre-writes the expected record {ok:false} while a
-- supervisor runs; the supervisor's own ok:true at the end of its shutdown recovery replaces it
t.test('auto.shutdown replaces the expected record of the prerm guard',function()
  local auto=require('auto')
  local env=t.env()
  env.run.fs.write_atomic(env.runtime..'/supervisor-shutdown.json',canon.encode(canon.object({ok=false,
    code='LIFECYCLE-RECOVERY-UNFINISHED',expected=true,time=canon.float(1)})))
  auto.shutdown(env)
  local row=t.read(env,env.runtime..'/supervisor-shutdown.json')
  t.eq({row.ok,row.code,row.expected},{true,canon.null,nil})
end)

t.run()
