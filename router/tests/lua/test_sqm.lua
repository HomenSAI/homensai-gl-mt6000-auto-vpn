-- Optional SQM (cake) on the VPN tunnel egress for the Lua monitor: sqm.lua with a fake tc.
-- Python twin: tests/test_sqm.py (shared cases tests/sqm_cases.json).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local sqm=require('sqm')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../sqm_cases.json'))
local function plain(v) if v==NULL then return nil end;return v end

local function fake_tc(devices,fail_replace,missing)
  local tc={roots={},commands={}}
  for name,root in pairs(devices) do tc.roots[name]={root[1],root[2]} end
  function tc.execute(argv)
    tc.commands[#tc.commands+1]=table.concat(argv,' ')
    if missing then return 127,'' end
    assert(argv[1]=='tc' and argv[2]=='qdisc' and argv[4]=='dev' and argv[6]=='root',table.concat(argv,' '))
    local verb,device=argv[3],argv[5]
    if not tc.roots[device] then return 1,'' end
    if verb=='show' then return 0,'qdisc '..tc.roots[device][1]..' '..tc.roots[device][2]..' root refcnt 2 \n' end
    if verb=='replace' then if fail_replace then return 2,'' end;tc.roots[device]={'cake','8001:'};return 0,'' end
    if verb=='del' then tc.roots[device]={'noqueue','0:'};return 0,'' end
    error('unexpected '..verb)
  end
  return tc
end

local function roots_of(json_roots)
  local out={};for name,root in pairs(json_roots) do out[name]={root[1],root[2]} end;return out
end
local function records_of(state)
  local out={}
  for i,r in ipairs(state.devices) do out[i]={device=r.device,ifindex=canon.number(r.ifindex),kbit=canon.number(r.kbit),checked=canon.number(r.checked)} end
  return out
end

t.test('shared cases: sync',function()
  for _,case in ipairs(CASES.sync) do
    local settings=case.settings=='on' and CASES.on or case.settings
    local tc=fake_tc(case.devices,case.fail_replace==true,case.missing_tc==true)
    local state,report=sqm.sync(settings,case.rows,case.state,tc.execute,case.now)
    t.eq(tc.commands,case.commands,case.name)
    t.eq(plain(report.code),plain(case.code),case.name)
    local result={};for k,v in pairs(report.devices) do result[k]=v end
    local expect={};for k,v in pairs(case.result) do expect[k]=v end
    t.eq(result,expect,case.name)
    t.eq(state.schema,1,case.name)
    t.eq(records_of(state),records_of({devices=case.records}),case.name)
    t.eq(tc.roots,roots_of(case.roots),case.name)
    -- the state file round-trips through JSON (floats of the clock included)
    t.eq(records_of(canon.decode(canon.encode(state))),records_of(state),case.name..' (JSON)')
  end
end)

t.test('shared cases: release',function()
  for _,case in ipairs(CASES.release) do
    local tc=fake_tc(case.devices)
    local state,failed=sqm.release(case.state,tc.execute)
    t.eq(tc.commands,case.commands,case.name)
    t.eq(failed,{});t.eq(#state.devices,0)
    t.eq(tc.roots,roots_of(case.roots))
  end
end)

t.test('shared cases: config and root_qdisc',function()
  for _,c in ipairs(CASES.config) do
    local kbit,code=sqm.config(c[1])
    t.eq({kbit,code},{plain(c[2]),plain(c[3])},canon.encode(c[1]))
  end
  for _,c in ipairs(CASES.root_qdisc) do
    local expect=plain(c[2])
    t.eq(sqm.root_qdisc(c[1]),expect and {expect[1],expect[2]} or nil,c[1])
  end
end)

t.test('off costs nothing; a failed restore keeps the record',function()
  t.eq(sqm.active({sqm_enabled=false,sqm_upload_kbit=18000},{}),false)
  t.eq(sqm.active({sqm_enabled=true,sqm_upload_kbit=0},{}),false)
  t.eq(sqm.active({sqm_enabled=true,sqm_upload_kbit=18000},{}),true)
  local function stuck(argv) if argv[3]=='show' then return 0,'qdisc cake 8001: root refcnt 2 \n' end;return 2,'' end
  local state={devices={{device='wgclient1',ifindex=12,kbit=18000,checked=1}}}
  local new,report=sqm.sync({sqm_enabled=false},{{device='wgclient1',ifindex=12}},state,stuck,10)
  t.eq(report.devices.wgclient1,'restore-failed');t.eq(report.code,'SQM-RESTORE-FAILED');t.eq(#new.devices,1)
  local kept,failed=sqm.release(state,stuck);t.eq(failed,{'wgclient1'});t.eq(#kept.devices,1)
end)

t.test('the monitor pass: state in RAM, report in status, nothing after the stop hook',function()
  package.loaded['monitor']=nil
  local monitor=require('monitor')
  local writes,commands={},{}
  local tc=fake_tc({wgclient1={'noqueue','0:'}})
  local fake={runtime='/run/x',runner={exec=function(argv,opts) t.eq(opts,{timeout=5});commands[#commands+1]=table.concat(argv,' ');return tc.execute(argv) end,
      clock=function() return 50 end},
    io={write_ram=function(path,value) writes[#writes+1]={path,canon.encode(value)} end},
    read_json=function() return canon.object() end}
  setmetatable(fake,{__index=monitor.Monitor})
  local status=canon.object()
  local settings={sqm_enabled=true,sqm_upload_kbit=18000}
  fake:sqm_pass(settings,{{device='wgclient1',ifindex=12}},status)
  t.eq(status.sqm.code,NULL);t.eq(#writes,1);t.eq(writes[1][1],'/run/x/sqm-state.json')
  t.eq(commands[2],'tc qdisc replace dev wgclient1 root cake bandwidth 18000kbit besteffort triple-isolate nat')
  local off=canon.object();fake:sqm_pass({sqm_enabled=false},{},off);t.eq(off.sqm.code,'SQM-OFF')
  fake:sqm_release();local after=#commands
  t.eq(tc.roots.wgclient1,{'noqueue','0:'})
  local late=canon.object();fake:sqm_pass(settings,{{device='wgclient1',ifindex=12}},late)
  t.eq(late.sqm,nil);t.eq(#commands,after)
end)

t.run()
