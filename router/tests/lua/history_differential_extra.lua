-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- Further drivers of history_differential.lua: latency history, stats reset.
return function(cases,results,util)
  local canon=util.canon

  -- latency: {initial=data|null, ops=[{status,settings,now}], now} -> data, public, technical tail; save -> file
  if cases.latency then
    local latency=require('latency_history')
    local out=canon.array()
    for _,case in ipairs(cases.latency) do
      local row=canon.object()
      local ok,err=pcall(function()
        local h=latency.new(case.initial~=canon.null and case.initial or nil)
        for _,op in ipairs(case.ops) do h:observe(op.status,op.settings,op.now) end
        row.data=canon.encode(h.data)
        row.public=canon.encode(h:public())
        row.tail=canon.encode(latency.technical_history_tail(h:public(),case.now))
        if case.save then
          local io_={write_json=function(path,value) util.write(path,canon.encode(value)) end}
          h:save(io_,case.save,case.now)
        end
        if case.load then
          local io_={read_json=function(path,default) local text=util.read(path);if text==nil then return default end;return canon.decode(text) end,
            unsafe=function() return false end}
          local loaded=latency.load(io_,case.load)
          row.loaded=canon.encode(loaded.data);row.notice=loaded.notice or canon.null
        end
      end)
      if not ok then row.error=tostring(err) end
      out[#out+1]=row
    end
    results.latency=out
  end

  -- capture: native_history.capture_transition_latency(value, status, binding, now) -> canonical text or null
  if cases.capture then
    local history=require('history')
    local out=canon.array()
    for _,case in ipairs(cases.capture) do
      local ok,value=pcall(history.capture_transition_latency,case.value,case.status,case.binding,canon.number(case.now))
      if not ok then out[#out+1]='error:'..tostring(value)
      else out[#out+1]=value==nil and canon.null or canon.encode(value) end
    end
    results.capture=out
  end

  if cases.reset then
    local reset=require('stats_reset')
    local accounting=require('accounting')
    local out=canon.array()
    for _,case in ipairs(cases.reset) do
      local clock={now=canon.number(case.now),persist=case.persist,runtime=case.runtime}
      local R=util.file_runner(clock)
      local row=canon.object()
      local ok,err=pcall(function()
        local acc=accounting.new(case.accounting~=canon.null and case.accounting or nil)
        local ctx={runner=R,persist=case.persist,env=require('monitor_status').env(R,case.runtime,case.persist),days=7}
        local state=reset.histories(R,case.persist)
        local request=reset.pending(R,case.runtime)
        row.request=request or canon.null
        if request then
          local result=reset.apply(ctx,request,acc,state,case.now)
          row.result=result
          if result.done then reset.save(ctx,acc,state) end
          row.accounting=canon.encode(acc:export())
        end
      end)
      if not ok then row.error=tostring(err) end
      out[#out+1]=row
    end
    results.reset=out
  end
end
