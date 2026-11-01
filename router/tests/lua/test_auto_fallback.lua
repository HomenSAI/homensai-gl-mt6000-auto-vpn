-- Safety net of the Lua supervisor: plain Lua errors are counted in a RAM file; the third inside 600 s hands the
-- process over to the Python supervisor. Old entries, clock jumps and a damaged file never block the count.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local A=require('auto')

local function memfs()
  local files={}
  return {files=files,read=function(p) return files[p] end,write_atomic=function(p,text) files[p]=text end}
end
local P='/run/lua-auto-crashes.json'

t.test('three errors inside the window reach the fallback count',function()
  local fs=memfs()
  t.eq(A.record_crash(fs,P,1000,'a'),1)
  t.eq(A.record_crash(fs,P,1100,'b'),2)
  t.eq(A.record_crash(fs,P,1500,'c'),A.FALLBACK_CRASHES)
  local row=canon.decode(fs.files[P])
  t.eq(row.last_error,'c')
end)

t.test('errors older than the window do not count',function()
  local fs=memfs()
  A.record_crash(fs,P,1000,'a');A.record_crash(fs,P,1100,'b')
  t.eq(A.record_crash(fs,P,1000+A.FALLBACK_WINDOW+200,'c'),1)
end)

t.test('a time in the future (clock jump) and a damaged file are dropped',function()
  local fs=memfs()
  A.record_crash(fs,P,5000,'a')
  t.eq(A.record_crash(fs,P,100,'b'),1)
  fs.files[P]='{not json'
  t.eq(A.record_crash(fs,P,200,'c'),1)
end)

t.test('the error text kept is bounded',function()
  local fs=memfs()
  A.record_crash(fs,P,1,string.rep('x',5000))
  t.eq(#canon.decode(fs.files[P]).last_error,2000)
end)

t.test('the Python supervisor is the packaged native_switch daemon',function()
  t.eq(A.PYTHON_SUPERVISOR[1],'/usr/bin/python3')
  t.eq(A.PYTHON_SUPERVISOR[2],'/usr/lib/homensai-vpn/native_switch.py')
  t.eq(A.PYTHON_SUPERVISOR[3],'daemon')
end)

t.test('with_trace keeps refusals and adds the place of a plain error',function()
  local r={code='X'}
  t.eq(A.with_trace(r),r)
  local text=A.with_trace('boom')
  t.truthy(string.find(text,'^boom\nstack traceback:'),text)
end)

t.run()
