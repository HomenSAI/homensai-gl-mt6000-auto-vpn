-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- Driver of tests/test_lua_speed_telegram.py (plan item 7): runs the Lua speed pause, speed test and Telegram
-- functions on cases written by the Python test and prints one JSON result per case, so the test compares them
-- with speed_pause.py / speed_test.py / telegram_report.py on the same input.
-- Usage: lua5.1 speedtg_fixture.lua <cases.json>      (files of a case live in its own directory)
-- No network: curl and the Telegram sender are fakes; /proc is simulated from the case.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/?.lua;'..package.path
local canon=require('canon')
canon.configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})
local pause=require('speed_pause')
local speed=require('speed')
local telegram=require('telegram')
local NULL=canon.null

local function read(path) local f=io.open(path,'rb');if not f then return nil end;local t=f:read('*a');f:close();return t end
local function write(path,text) local f=assert(io.open(path,'wb'));f:write(text);f:close() end

local function stat_line(pid,start)
  local fields={'S'};for _=1,18 do fields[#fields+1]='0' end;fields[#fields+1]=string.format('%d',start)
  return string.format('%d (lua daemon) ',pid)..table.concat(fields,' ')..' 0 0\n'
end

-- deps over a real directory with the case's simulated clocks and processes
local function deps(case)
  local dir=case.dir
  local ctx=case.context or canon.object()
  local d={runtime=dir,persist=dir,kills=canon.array(),spawned=canon.array(),sent=canon.array()}
  local function n(v) return canon.number(v) end
  function d.read(path) return read(path) end
  function d.is_link(path) return false end
  function d.size(path) local t=read(path);return t and #t or nil end
  function d.write(path,text) write(path,text) end
  function d.remove(path) os.remove(path) end
  function d.clock() return n(ctx.clock) end
  function d.wall() return n(ctx.wall) end
  function d.boot() return ctx.boot or 'test-boot' end
  local starts=type(ctx.starts)=='table' and ctx.starts or {}
  local cmdlines=type(ctx.cmdlines)=='table' and ctx.cmdlines or {}
  function d.stat(pid) local s=starts[tostring(pid)];return s and stat_line(pid,s) or nil end
  function d.cmdline(pid) local c=cmdlines[tostring(pid)];return c and (string.gsub(c,'|','\0')) or nil end
  function d.getpid() return n(ctx.pid) or 1 end
  function d.kill(pid,signal) d.kills[#d.kills+1]=canon.array({pid,signal}) end
  function d.sha256(text) return canon.sha256(text) end
  function d.lock(fn) return true,fn() end
  function d.sleep() end
  function d.services() return ctx.services end
  function d.pair_state() return ctx.pair_state or canon.object() end
  function d.pair_intent() return ctx.pair_intent or canon.object() end
  function d.revision() return ctx.revision end
  function d.inventory() return ctx.inventory end
  function d.retention_days() return n(ctx.retention_days) or 7 end
  function d.day(now) return os.date('%Y-%m-%d',math.floor(now)) end
  local counters=type(ctx.counters)=='table' and ctx.counters or {}
  function d.sysfs(device,name)
    local row=counters[device];if not row then return nil end
    if name=='statistics/rx_bytes' then return tostring(row[1]) elseif name=='statistics/tx_bytes' then return tostring(row[2]) end
  end
  function d.spawn_worker(tx) d.spawned[#d.spawned+1]=tx;return n(ctx.spawn_pid) end
  function d.uuid() return ctx.uuid or string.rep('b',32) end
  function d.allow() return ctx.allow~=false end
  function d.config() if ctx.config==nil or ctx.config==NULL then error('no config',0) end;return ctx.config end
  function d.send(config,text)
    d.sent[#d.sent+1]=text
    local failure=ctx.send_error
    if failure and failure~=NULL then
      if failure.http then error(telegram.rejection(failure.http,failure.retry_after),0) end
      error(telegram.delivery_error(failure.code,failure.uncertain==true,failure.retry_after or 300),0)
    end
  end
  return d
end

local function encode_error(err)
  if type(err)=='table' and err.code then return canon.object({error=err.code}) end
  if type(err)=='string' and string.find(err,'^[A-Z][A-Z0-9-]+$') then return canon.object({error=err}) end
  return canon.object({error='LUA:'..tostring(err)})
end
local function set_of(list) local out={};for _,k in ipairs(list or {}) do out[k]=true end;return out end
local function files_of(dir,names)
  local out=canon.object()
  for _,name in ipairs(names or {}) do
    local text=read(dir..'/'..name)
    out[name]=text and canon.decode(text) or NULL
  end
  return out
end

local function run(case)
  local d=deps(case)
  local a=case.args or canon.array()
  local op=case.op
  local ok,result=pcall(function()
    if op=='gate' then return pause.gate(d,a[1],function() return a[2]==true end)
    elseif op=='public' then return pause.public(d)
    elseif op=='load' then local row=pause.load(d);return row==nil and NULL or row
    elseif op=='participants' then return pause.participants(d)
    elseif op=='interrupted' then return pause.interrupted(d,a[1])
    elseif op=='release' then pause.release(d,a[1]);return NULL
    elseif op=='cpu_parse' then d.cpu_text=function() return a[1] end;return pause.cpu_snapshot(d)
    elseif op=='speed_start' then return speed.start(d,a[1],a[2]==true)
    elseif op=='speed_cancel' then return speed.cancel(d)
    elseif op=='active_job' then return speed.active_job(d)
    elseif op=='public_live' then return speed.public_live(d)
    elseif op=='public_status' then return speed.public_status(d)
    elseif op=='append_history' then speed.append_history(d,a[1]);return NULL
    elseif op=='load_history' then return speed.load_history(d)
    elseif op=='prune_history' then speed.prune_history(d);return NULL
    elseif op=='reserve_quota' then return speed.reserve_quota(d,a[1],a[2],canon.number(a[3]))
    elseif op=='validate_request' then return speed.validate_request(a[1],a[2])
    elseif op=='observe_traffic' then speed.observe_traffic(d,a[1],a[2]);return NULL
    elseif op=='automatic_new' then
      local previous=nil
      if a[2]~=NULL then previous={};for _,id in ipairs(a[2]) do previous[id]=true end end
      local active=speed.automatic_new(d,a[1],previous,case.context.inventory)
      local ids=canon.array();for id in pairs(active) do ids[#ids+1]=id end;table.sort(ids);return ids
    elseif op=='is_global' then local g=speed.is_global(a[1]);if g==nil then return NULL end;return g
    elseif op=='format_report' then return telegram.format_report(a[1],a[2],canon.number(a[3]),a[4]~=NULL and set_of(a[4]) or nil)
    elseif op=='format_period' then
      local job=a[2];job.start=canon.number(job.start);job['end']=canon.number(job['end'])
      return telegram.format_period(a[1],job,canon.number(a[3]),a[4]~=NULL and set_of(a[4]) or nil)
    elseif op=='delta_lines' then return canon.array(telegram.delta_lines(a[1],a[2],canon.number(a[3])))
    elseif op=='prepare' then
      local jobs,state,public=telegram.prepare(a[1],a[2],canon.number(a[3]))
      local list=canon.array()
      for _,job in ipairs(jobs) do
        local row=canon.object();for k,v in pairs(job) do row[k]=(k=='start' or k=='end') and canon.float(v) or v end;list[#list+1]=row
      end
      return canon.array({list,state,public})
    elseif op=='limited_text' then return telegram.limited_text(a[1],canon.number(a[2]))
    elseif op=='valid' then return telegram.valid(a[1])
    elseif op=='parse_items' then local s=telegram.parse_items(a[1]);local out=canon.array();for _,k in ipairs(telegram.ITEMS) do if s[k] then out[#out+1]=k end end;return out
    elseif op=='deliver' then
      local public,state,sent=telegram.deliver(d,a[1],a[2],canon.number(a[3]))
      return canon.array({public,state,sent,d.sent})
    elseif op=='classify' then
      local okc,err=pcall(telegram.classify,a[1],a[2]~=NULL and a[2] or nil,a[3]~=NULL and a[3] or nil)
      if okc then return 'ok' end
      return canon.array({err.code,err.uncertain,err.retry_after})
    elseif op=='send_test' then return canon.array({telegram.send_test(d),d.sent})
    elseif op=='retry_unknown' then return telegram.retry_unknown(d)
    elseif op=='load_state' then local data,notice=telegram.load_state(d);return canon.array({data,notice or NULL})
    elseif op=='save_state' then telegram.save_state(d,a[1]);return NULL
    end
    error('unknown op '..tostring(op))
  end)
  local value=NULL
  if ok and result~=nil then value=result end
  local out=canon.object({result=value,error=ok and NULL or encode_error(result).error,
    files=files_of(case.dir,case.files),kills=d.kills,spawned=d.spawned})
  return out
end

local cases=canon.decode(read(arg[1]))
local results=canon.array()
for _,case in ipairs(cases) do results[#results+1]=run(case) end
io.write(canon.encode(results))
