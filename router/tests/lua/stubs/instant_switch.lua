-- TEST STUB of lua-core instant_switch.lua: switch() delegates to run.fake_instant (the harness), which plays
-- the write stage (APPLYING journal, order change, HELD-ON-RESERVE) or a refusal.
local M={}
function M.switch(run,request,direction,env)
  if not run.fake_instant then error('instant_switch stub: run.fake_instant missing',0) end
  return run.fake_instant(request,direction,env)
end
return M
