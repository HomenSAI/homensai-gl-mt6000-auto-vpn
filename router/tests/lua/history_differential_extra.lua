-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- Further drivers of history_differential.lua: latency history, stats reset, switch-history journal.
return function(cases,results,util)
  local canon=util.canon

  -- journal (schema 2): {persist, wall, days, limit, tail?, retention_bytes?, compact_bytes?, trace?, reference?,
  -- resident?, ops=[{op='record',value,now} | {op='public',now,days?} | {op='load'}]} -> {steps, cpu, wall}. The directory is a
  -- real one prepared by Python (maybe damaged); with trace every record reports the sha256 of the three files.
  -- reference: the frozen schema-1 writer (history_v1_reference.lua) instead, for the before/after timing.
  if cases.journal then
    local history=require('history')
    local page=require('monitor_status')
    local out=canon.array()
    for _,case in ipairs(cases.journal) do
      local module=history
      if case.reference==true then module=dofile(util.here..'/history_v1_reference.lua') end
      local saved={history.RETENTION_BYTES,history.COMPACT_BYTES,history.TAIL}
      if case.retention_bytes~=nil then history.RETENTION_BYTES=case.retention_bytes end
      if case.compact_bytes~=nil then history.COMPACT_BYTES=case.compact_bytes end
      if case.tail~=nil then history.TAIL=case.tail end
      local clock={now=canon.number(case.wall),persist=case.persist,runtime=case.persist}
      local R=util.file_runner(clock)
      local env=page.env(R,case.persist,case.persist)
      if case.resident==true then
        -- a change key like nixio's (no nixio here): a version per path, bumped by every write; renames carry it
        local fs=env.run.fs
        local version,count={},0
        local write,rename,append=fs.write_atomic,fs.rename,fs.append
        fs.write_atomic=function(p,t) count=count+1;version[p]=count;return write(p,t) end
        fs.rename=function(a,b) version[b]=version[a];version[a]=nil;return rename(a,b) end
        fs.append=function(p,t) count=count+1;version[p]=count;return append(p,t) end
        fs.key=function(p) local size=R.file_size(p);if size==nil then return 'absent' end;return tostring(version[p] or 0)..':'..size end
      end
      module.forget_resident()
      local days=case.days or 7
      local h=module.new(env,case.persist,case.limit or 10000,days)
      local function digest(name)
        local text=util.read(case.persist..'/'..name)
        if text==nil then return canon.null end
        return canon.sha256(text)
      end
      local steps=canon.array()
      local ok,err=pcall(function()
        local cpu,started=os.clock(),util.wall()
        for _,op in ipairs(case.ops) do
          local row=canon.object()
          if op.op=='record' then
            local done,res=pcall(h.record,h,op.value,canon.number(op.now))
            if done then row.result=res else row.result='error:'..tostring(res) end
            if case.trace==true then
              row.main=digest('native-history.json');row.backup=digest('native-history.backup.json')
              row.archive=digest('native-history.events.jsonl')
            end
          elseif op.op=='public' then
            row.public=canon.encode(page.history_public(env,op.days or days,canon.number(op.now)))
          elseif op.op=='load' then
            row.load=canon.encode(module.new(env,case.persist,10000,days):load())
          else error('unknown journal op '..tostring(op.op)) end
          steps[#steps+1]=row
        end
        out[#out+1]=canon.object({steps=steps,cpu=canon.float(os.clock()-cpu),wall=canon.float(util.wall()-started)})
      end)
      history.RETENTION_BYTES,history.COMPACT_BYTES,history.TAIL=saved[1],saved[2],saved[3]
      if not ok then out[#out+1]=canon.object({error=tostring(err)}) end
    end
    results.journal=out
  end

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
