-- retention.lua: statistics kept by time or by size (owner, 31 Oct 2026). The full Python comparison is
-- tests/test_retention_model.py; here: defaults, legacy mapping, payload codes, the trim and the monitor's use.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local retention=require('retention')
local setup=require('setup')
local monitor=require('monitor')

local function code(fn,...) local ok,err=pcall(fn,...);if ok then return 'OK' end;return type(err)=='table' and err.code or tostring(err) end

t.test('defaults keep the old history_days (1..7, default 7); the new options win when valid',function()
  t.eq(retention.days({}),7);t.eq(retention.days(nil),7)
  t.eq(retention.days({history_days=3}),3);t.eq(retention.days({history_days='5'}),5);t.eq(retention.days({history_days=9}),7)
  t.eq(retention.days({history_days=2,stats_retention_mode='time',stats_retention_days=30}),30)
  t.eq(retention.days({history_days=2,stats_retention_mode='time',stats_retention_days=8}),2,'not a slider stop')
  t.eq(retention.days({stats_retention_mode='size',stats_retention_mb=4,interval=10}),11)
  t.eq(monitor.retention_days({stats_retention_mode='time',stats_retention_days='14'}),14,'the monitor follows the choice')
  t.eq(require('latency_history').days({stats_retention_mode='time',stats_retention_days=30}),30)
end)

t.test('size model: the same numbers as retention_settings.py',function()
  local e=retention.estimate({interval=10},7)
  t.eq({e.flash,e.ram,e.work_flash,e.work_ram},{2468732,13196722,976892,3419122})
  local r=retention.resolve({interval=10,stats_retention_mode='size',stats_retention_mb=4})
  t.eq({r.effective_days,r.latency_bytes,r.response_bytes},{11,1352924,1181668})
  t.eq(retention.size_days({interval=300},1),5);t.eq(retention.size_days({interval=10,response_compare=true},1),2)
end)

t.test('setup_stats mode retention: keys and refusal codes',function()
  t.eq(setup.stats_payload(canon.decode('{"mode":"retention","retention":"time","days":14}'),1000),
    {stats_retention_mode='time',stats_retention_days='14',history_days='7'})
  t.eq(setup.stats_payload(canon.decode('{"mode":"retention","retention":"size","mb":8}'),1000),{stats_retention_mode='size',stats_retention_mb='8'})
  t.eq(code(setup.stats_payload,canon.decode('{"mode":"retention","retention":"time","days":10}'),1000),'STATS-RETENTION-DAYS')
  t.eq(code(setup.stats_payload,canon.decode('{"mode":"retention","retention":"size","mb":64}'),1000),'STATS-RETENTION-SIZE')
  t.eq(code(setup.stats_payload,canon.decode('{"mode":"retention","retention":"size"}'),1000),'STATS-RETENTION-FIELDS')
  for _,key in ipairs({'stats_retention_mode','stats_retention_days','stats_retention_mb','history_days'}) do t.truthy(setup.ALLOWED[key],key) end
end)

t.test('trim drops the oldest rows only until the budget fits',function()
  local rows=canon.array()
  for i=1,500 do rows[i]=canon.array({1793000040+60*i,canon.float(12.5),canon.null,1,0,'source','0123456789abcdef'}) end
  local data=canon.object({version=1,rows=rows,pairs=canon.object(),current=canon.null,seen=canon.object(),saved=canon.null})
  local size=#canon.encode(data)
  t.eq(retention.trim_to_budget(data,nil),0);t.eq(retention.trim_to_budget(data,size),0);t.eq(#data.rows,500)
  local dropped=retention.trim_to_budget(data,math.floor(size/2))
  t.truthy(dropped>0 and #canon.encode(data)<=math.floor(size/2));t.eq(data.rows[1][1],1793000040+60*(dropped+1))
end)

t.test('capacity: free flash and MemAvailable when the router tells them, null otherwise',function()
  local c=retention.capacity('/nonexistent',function() return 'MemTotal: 1 kB\nMemAvailable:  2048 kB\n' end)
  t.eq(c.ram_available,2097152)
  local none=retention.capacity('/nonexistent',function() return nil end)
  t.truthy(none.ram_available==canon.null)
end)

t.run()
