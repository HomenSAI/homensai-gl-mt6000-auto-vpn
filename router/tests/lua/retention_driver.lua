-- Driver for tests/test_retention_model.py: reads a JSON array of cases on stdin, answers a JSON array with what
-- lua/retention.lua (and the Lua consumers that follow it) computes for each case.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local canon=require('canon')
canon.configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})
local retention=require('retention')
local setup=require('setup')
local latency=require('latency_history')

local cases=canon.decode(io.read('*a'))
local out=canon.array()
for _,case in ipairs(cases) do
  local op,result=case.op,nil
  local settings=case.settings
  if op=='public' then result=retention.public(settings)
  elseif op=='estimate' then result=retention.estimate(settings,case.days)
  elseif op=='size_days' then result=retention.size_days(settings,case.mb)
  elseif op=='days' then result=retention.days(settings)
  elseif op=='payload' then
    local ok,value=pcall(setup.stats_payload,canon.decode(case.request),1000.0)
    if ok then local main=canon.object();for k,v in pairs(value) do main[k]=v end;result=canon.object({kind='OK',value=main})
    else result=canon.object({kind='ERR',value=type(value)=='table' and value.code or tostring(value)}) end
  elseif op=='trim' then
    local data=case.data
    local dropped=retention.trim_to_budget(data,case.budget)
    result=canon.object({dropped=dropped,rows=#data.rows,first=#data.rows>0 and data.rows[1][1] or canon.null})
  elseif op=='latency_observe' then
    local h=latency.new(case.data)
    h:observe(canon.object({profiles=canon.array()}),settings,case.now)
    result=canon.object({rows=#h.data.rows,retention_seconds=h.retention_seconds})
  else error('unknown op '..tostring(op)) end
  out[#out+1]=result
end
io.write(canon.encode(out))
