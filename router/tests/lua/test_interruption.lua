-- interruption.lua: one code per service start (owner request 01.11.2026). The cases are shared with
-- tests/test_interruption.py (tests/interruption_cases.json): Lua and Python decide the same.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local I=require('interruption')

local function read_file(path) local f=assert(io.open(path,'rb'));local text=f:read('*a');f:close();return text end
local CASES=canon.decode(read_file(t.here..'/../interruption_cases.json'))
local function plain(v) if v==nil or v==canon.null then return nil end;return v end

local function world(case)
  local files={};for k,v in pairs(case.files) do files[k]=v end
  local mtimes={};for k,v in pairs(case.mtimes) do mtimes[k]=canon.number(v) end
  local w={files=files,logs={},records={},persist_writes=0,stopping=false}
  w.ctx={runtime='/run',persist='/etc',
    read=function(p) return files[p] end,mtime=function(p) return mtimes[p] end,
    write_ram=function(p,text) files[p]=text end,
    write_persist=function(p,text) w.persist_writes=w.persist_writes+1;files[p]=text end,
    now=function() return 1000 end,uptime=function() return canon.number(case.uptime) end,
    log=function(line) w.logs[#w.logs+1]=line end,record=function(code) w.records[#w.records+1]=code end,
    stopping=function() return w.stopping end}
  return w
end
local function state_of(text) local ok,row=pcall(canon.decode,text or '');return ok and canon.is_object(row) and row.state or nil end

for _,case in ipairs(CASES.start) do
  t.test('start: '..case.name,function()
    local w=world(case)
    local handle=I.start(w.ctx,plain(case.phase))
    t.eq(handle.code,case.expect,'code')
    t.eq(state_of(w.files['/etc/service-run.json']),case.written,'flash marker')
    t.eq(handle.facts.auto_on,case.auto=='on','auto')
    t.eq(#w.records,case.recorded and 1 or 0,'history events')
    if case.recorded then t.eq(w.records[1],case.expect) end
    t.eq(#w.logs,1,'one log line')
    t.truthy(string.find(w.logs[1],'^'..string.gsub(case.expect,'%-','%%-')..': '),w.logs[1])
    t.truthy(w.files['/run/supervisor-run.json']~=nil,'RAM marker')
  end)
end

for _,case in ipairs(CASES.monitor) do
  t.test('monitor: '..case.name,function()
    local w=world(case)
    t.eq(I.monitor_start(w.ctx),plain(case.expect))
    t.eq(#w.logs,case.logged and 1 or 0,'log lines')
    t.eq(w.persist_writes,0,'no flash write')
    t.truthy(w.files['/run/monitor-run.json']~=nil,'RAM marker')
  end)
end

t.test('steady state: running once, never over a stop, nothing more in a crash loop',function()
  local w=world({files={},mtimes={},uptime=60})
  local handle=I.start(w.ctx,nil)
  t.eq(w.persist_writes,1)
  t.truthy(I.mark_running(w.ctx,handle));t.eq(state_of(w.files['/etc/service-run.json']),'running');t.eq(w.persist_writes,2)
  t.eq(I.mark_running(w.ctx,handle),false);t.eq(w.persist_writes,2)
  -- a procd restart: no flash write at the start nor at the end of the recovery
  local again=I.start(w.ctx,nil)
  t.eq(again.code,'RESTART-PROCESS');t.eq(I.mark_running(w.ctx,again),false);t.eq(w.persist_writes,2)
  -- a stop during the recovery keeps the init script's 'stopped'
  local s=world({files={['/etc/service-run.json']='{"state":"stopped","time":1}'},mtimes={},uptime=60})
  local h=I.start(s.ctx,nil);s.stopping=true;s.files['/etc/service-run.json']='{"state":"stopped","time":2}'
  t.eq(I.mark_running(s.ctx,h),false);t.eq(state_of(s.files['/etc/service-run.json']),'stopped')
end)

t.test('the init script marker and every code have a text',function()
  t.eq(I.previous('{"state":"stopped","time":1730000000}'),'stopped')
  t.eq(I.previous(nil),nil);t.eq(I.previous('{"state":"other"}'),'invalid')
  for _,case in ipairs(CASES.start) do t.truthy(I.TEXT[case.expect],case.expect) end
end)

t.test('a failing flash write or log never stops the start',function()
  local w=world({files={},mtimes={},uptime=nil})
  w.ctx.write_persist=function() error('flash full') end
  w.ctx.log=function() error('no logger') end
  local handle=I.start(w.ctx,'APPLYING')
  t.eq(handle.code,'RESTART-FIRST-START');t.eq(handle.persisted,nil)
end)

t.run()
