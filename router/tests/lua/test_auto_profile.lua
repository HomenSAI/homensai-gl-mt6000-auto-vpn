-- The diagnostics profiler of the Lua supervisor: off without the request file; with it, one window of samples
-- and a JSON report in the runtime directory, and the request file is consumed.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local A=require('auto')

local dir=os.tmpname();os.remove(dir)
os.execute('mkdir -p '..dir)

t.test('no request file: nothing is written and no hook is set',function()
  A.profile_tick(dir)
  t.eq(debug.gethook(),nil)
  t.eq(io.open(dir..'/lua-profile.json','r'),nil)
end)

t.test('a request starts one window and the next tick after it writes the report',function()
  A.PROFILE_SECONDS=0
  local f=io.open(dir..'/lua-profile.request','w');f:write('');f:close()
  A.profile_tick(dir)
  t.truthy(debug.gethook()~=nil,'hook set')
  t.eq(io.open(dir..'/lua-profile.request','r'),nil,'request consumed')
  local x=0
  for i=1,200000 do x=x+i%7 end
  A.profile_tick(dir)
  t.eq(debug.gethook(),nil,'hook cleared')
  local h=io.open(dir..'/lua-profile.json','r');local text=h:read('*a');h:close()
  local report=canon.decode(text)
  t.truthy(canon.is_array(report.functions) and canon.is_array(report.lines),text)
  t.truthy(#report.lines>0,'samples recorded')
end)

t.test('status.json is decoded once per version for every reader',function()
  local ctl=require('auto_control')
  local a=ctl.decode_resident('/x/status.json','{"time":1.0,"accounting":[1]}')
  t.eq(ctl.decode_resident('/x/status.json','{"time":1.0,"accounting":[1]}'),a,'same text: the same decoded value')
  local b=ctl.decode_resident('/x/status.json','{"time":2.0,"accounting":[1]}')
  t.truthy(b~=a,'a new version is decoded')
  t.eq(canon.encode(b),'{"time":2.0}','only the fields the supervisor reads')
end)

t.test('cleanup',function() os.execute('rm -rf '..dir) end)
t.run()
