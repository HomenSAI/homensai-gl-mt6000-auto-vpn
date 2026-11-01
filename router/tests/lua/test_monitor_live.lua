-- monitor_io keeps every armed uloop object reachable until it completes: libubox-lua userdata cancel
-- themselves in __gc, so a timer only an unreachable closure points to would never fire in the daemon.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local io_=require('monitor_io')

-- a fake uloop whose timers, like libubox-lua's, are cancelled when collected
local armed={}
local fake={}
function fake.timer(fn)
  local timer=newproxy(true)
  local entry={fn=fn,active=false}
  getmetatable(timer).__index={
    set=function(_,ms) entry.active=true;armed[entry]=true end,
    cancel=function() entry.active=false;armed[entry]=nil end}
  getmetatable(timer).__gc=function() entry.active=false;armed[entry]=nil end
  return timer
end
local function fire_all()
  local list={}
  for entry in pairs(armed) do list[#list+1]=entry end
  for _,entry in ipairs(list) do if entry.active then entry.active=false;armed[entry]=nil;entry.fn() end end
end

t.test('a timer kept only by the event loop survives garbage collection and fires',function()
  io_.attach_loop(fake)
  local fired=false
  io_.after(10,function() fired=true end)  -- the handle is dropped on purpose
  collectgarbage();collectgarbage()
  t.eq(io_.live_count(),1,'held while armed')
  fire_all()
  t.truthy(fired,'callback ran')
  t.eq(io_.live_count(),0,'released after firing')
end)

t.test('a cancelled timer is released and never fires',function()
  io_.attach_loop(fake)
  local fired=false
  local h=io_.after(10,function() fired=true end)
  h.cancel()
  collectgarbage()
  fire_all()
  t.eq(fired,false)
  t.eq(io_.live_count(),0)
end)

t.run()
