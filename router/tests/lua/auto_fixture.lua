-- Writes real files for tests/test_lua_auto.py: a full happy-path attempt (journal COMMITTED, history, status)
-- into <dir>/etc and <dir>/run, then a manual instant switch and an operator return.
-- Usage: lua5.1 auto_fixture.lua <dir>
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local dir=assert(arg[1],'directory argument')
os.execute('mkdir -p "'..dir..'/etc" "'..dir..'/run"')
local env=t.env({fs=t.real_fs(),runtime=dir..'/run',persist=dir..'/etc'})
env.localdate=os.date
T.attempt(env,env.backend.selection,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
  probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
local j=T.journal_read(env)
assert(j.phase=='COMMITTED','expected COMMITTED, got '..tostring(j.phase))
-- a second transaction: the operator returns to the primary through finish_committed
env.run.advance(120)
assert(T.finish_committed(env,j,'PRIMARY-STABLY-RECOVERED'),'finish_committed')
j=T.journal_read(env)
assert(j.phase=='ROLLED-BACK')
io.write(canon.encode(canon.object({journal=j.phase,tx=j.tx,history_events=#t.history(env).events})),'\n')
