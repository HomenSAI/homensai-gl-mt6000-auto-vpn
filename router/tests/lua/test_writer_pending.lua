-- R4-03 (night2 N3-regress 3): WRITER-UNRESOLVED is a pending condition - it never consumes the rollback-failure
-- budget (two of them used to reach ROLLBACK-GIVEN-UP), the recovery rechecks the writer on later ticks and resumes
-- the normal rollback once its exit is established; Stop ends the wait without a count.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local ctl=require('auto_control')
local R=require('rollback')
local A=require('auto')

local function env_of(stop_after)
  local sleeps=0
  local env={run={clock=function() return 100000 end,wall=function() return 1761830400 end},sleep=function() sleeps=sleeps+1 end,
    stop=function() return stop_after~=nil and sleeps>=stop_after end,backend={}}
  return env,function() return sleeps end
end

t.test('rollback_counted does not charge a WRITER-UNRESOLVED refusal; any other refusal is still counted',function()
  local original=R.rollback
  R.rollback=function() ctl.refuse('WRITER-UNRESOLVED') end
  local env=env_of()
  local value={phase='APPLYING'}
  local err=t.raises(R.rollback_counted,env,value,'TRANSACTION-FAILED')
  t.eq(err.code,'WRITER-UNRESOLVED');t.eq(value.rollback_failures,nil,'not charged')
  t.raises(R.rollback_counted,env,value,'TRANSACTION-FAILED')
  t.eq(value.rollback_failures,nil,'still not charged after a second wait')
  R.rollback=function() ctl.refuse('ROLLBACK-UNVERIFIED') end
  err=t.raises(R.rollback_counted,env,value,'TRANSACTION-FAILED')
  t.eq(err.code,'ROLLBACK-UNVERIFIED');t.eq(value.rollback_failures,1,'a real failure is counted as before')
  R.rollback=original
end)

t.test('boot_rollback waits for the writer (no count, long after the boot window) and resumes the normal rollback',function()
  local original=R.rollback
  local calls=0
  R.rollback=function() calls=calls+1;if calls<4 then ctl.refuse('WRITER-UNRESOLVED') end end
  local env,sleeps=env_of()
  local value={phase='APPLYING'}
  A.boot_rollback(env,value)
  t.eq(calls,4,'rechecked until the writer was established, then rolled back')
  t.eq(sleeps(),3,'one recheck wait per pending tick')
  t.eq(value.rollback_failures,nil,'the budget is untouched')
  R.rollback=original
end)

t.test('Stop ends the wait for an unresolved writer without charging the budget; a real failure past the boot window still counts',function()
  local original=R.rollback
  R.rollback=function() ctl.refuse('WRITER-UNRESOLVED') end
  local env,sleeps=env_of(2)
  local value={phase='APPLYING'}
  local err=t.raises(A.boot_rollback,env,value)
  t.eq(err.code,'WRITER-UNRESOLVED');t.eq(sleeps(),2);t.eq(value.rollback_failures,nil,'not charged')
  R.rollback=function() ctl.refuse('KERNEL-POLICY-UNVERIFIED') end
  err=t.raises(A.boot_rollback,env_of(),value)
  t.eq(err.code,'KERNEL-POLICY-UNVERIFIED');t.eq(value.rollback_failures,1,'counted as before')
  R.rollback=original
end)

t.run()
