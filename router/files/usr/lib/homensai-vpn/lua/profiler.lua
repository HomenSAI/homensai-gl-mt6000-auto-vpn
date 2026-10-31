-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- profiler.lua: on-request sampling profile of a Lua daemon (the Auto supervisor, the monitor).
-- tick(runtime, name, seconds) is called from the daemon's own loop. When <runtime>/<name>.request exists it is
-- consumed and a window starts: every 1000 Lua instructions the CPU time since the previous sample (os.clock)
-- is added to the running function and line. At the first tick after the window <runtime>/<name>.json (RAM)
-- holds the 40 heaviest functions and lines. Off, a tick costs one failed open().
local canon=require('canon')
local M={}
local state=nil

local function top(t,n)
  local rows={}
  for k,v in pairs(t) do rows[#rows+1]={k,v} end
  table.sort(rows,function(a,b) return a[2]>b[2] end)
  local out={}
  for i=1,math.min(n,#rows) do out[i]=canon.array({rows[i][1],canon.float(math.floor(rows[i][2]*1000+0.5)/1000)}) end
  return canon.array(out)
end

function M.tick(runtime,name,seconds)
  if state then
    if os.time()<state.deadline then return end
    debug.sethook()
    local report=canon.object({cpu_s=canon.float(os.clock()-state.start),wall_s=os.time()-state.began,
      functions=top(state.functions,40),lines=top(state.lines,40)})
    local path=state.path
    state=nil
    pcall(require('runner').fs.write_atomic,path,canon.encode(report))
    return
  end
  local request=runtime..'/'..name..'.request'
  local f=io.open(request,'r')
  if not f then return end
  f:close();os.remove(request)
  local now=os.clock()
  local p={start=now,began=os.time(),deadline=os.time()+(seconds or 60),functions={},lines={},last=now,
    path=runtime..'/'..name..'.json'}
  state=p
  debug.sethook(function()
    local info=debug.getinfo(2,'Sln')
    local t=os.clock();local dt=t-p.last;p.last=t
    if not info then return end
    local fn=info.short_src..':'..tostring(info.linedefined)..' '..tostring(info.name)
    local line=info.short_src..':'..tostring(info.currentline)
    p.functions[fn]=(p.functions[fn] or 0)+dt
    p.lines[line]=(p.lines[line] or 0)+dt
  end,'',1000)
end

return M
