-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- loop_guard.lua: isolation of event-loop callbacks and the record of what failed in them.
--
-- libubox-lua and libubus-lua call Lua with lua_call: an error in a timer, child, socket or ubus callback goes through
-- the C loop and ends uloop.run(), so one failing callback ended the whole monitor process (2.1.0-alpha8: one such end
-- in the soak, its text lost, about 37-40 s without decisions while the new vendor generations settled). The separate
-- monitor (monitor.run) and hv-core (hv_core.lua) now share these guards. A failing callback is logged and counted, the
-- loop goes on; what a lost callback leaves undone is the business of the caller's own deadlines (the pass watchdog,
-- monitor.loop_check). Lua has no way to restart a C loop an error escaped from, so that case ends the process: procd
-- restarts it and the record below says why.
--
-- The record: RUNTIME/lua-monitor-crashes.json, RAM only, the same idea as auto.lua's lua-auto-crashes.json: the last
-- KEEP different errors with count, first and last time, cleaned text. It survives a process restart (not a reboot),
-- never touches flash, and `homensai-vpn-diag` and status.json `monitor_loop` show it. Secrets: an error message is
-- text someone built at run time, so it is cut, masked by the rules of the diagnostic bundle and every long token-like
-- word is removed; when the masking itself is not available the message is withheld. The stack frames are source file
-- names, line numbers and function names only.
local native_pcall,native_xpcall=pcall,xpcall  -- loaded before hv_core replaces the globals with coroutine-safe ones

local M={}
M.RECORD='lua-monitor-crashes.json'
M.KEEP=5            -- different errors kept in the record
M.LOG_EVERY=60      -- seconds: the same error is logged and written at most this often (never a line per callback)
M.MESSAGE_LIMIT=300 -- characters of an error message
M.FRAMES=24         -- stack lines
M.TEXT_LIMIT=2000   -- characters of one recorded text, as lua-auto-crashes.json
M.WITHHELD='[message withheld]'

-- xpcall message handler: the text with the stack of the failure; a refusal table gives its code, never its fields
function M.trace(e)
  if type(e)=='table' then
    local code=rawget(e,'code')
    e=code~=nil and ('code '..tostring(code)) or 'error object'
  end
  return debug.traceback(tostring(e),2)
end

local function bundle_mask()
  local ok,bundle=native_pcall(require,'diag_bundle')
  if ok and type(bundle)=='table' and type(bundle.mask_line)=='function' then return bundle.mask_line end
  return nil
end
local function token(word)
  if #word<24 or string.find(word,'/homensai-vpn/',1,true) then return nil end
  return '<masked>'
end
-- Mask first, line by line, on the whole text: the rules are line rules (a UCI dump needs its line starts), and a cut before
-- them would leave the start of a secret they no longer recognise. Only then compress and cut.
local function message_text(text,mask)
  if not mask then return M.WITHHELD end
  local lines={}
  for line in string.gmatch(text,'[^\n]+') do
    local ok,masked=native_pcall(mask,line)
    if not ok or type(masked)~='string' then return M.WITHHELD end
    lines[#lines+1]=(string.gsub(masked,'[%w%+/=_%-]+',token))
  end
  local joined=string.gsub(table.concat(lines,' '),'%s+',' ')
  joined=string.gsub(joined,'^ *(.-) *$','%1')
  joined=string.gsub(joined,'[%c\128-\255]','?')
  return string.sub(joined,1,M.MESSAGE_LIMIT)
end
-- clean(text): 'message\nstack traceback:\n\tframes...' -> the same shape, safe to keep and to show
function M.clean(text)
  text=tostring(text)
  local head,frames=text,nil
  local at=string.find(text,'stack traceback:',1,true)
  if at then head,frames=string.sub(text,1,at-1),string.sub(text,at) end
  local mask=bundle_mask()
  local out={message_text(head,mask)}
  if frames then
    for line in string.gmatch(frames,'[^\n]+') do
      if #out>M.FRAMES then break end
      if mask then
        local ok,masked=native_pcall(mask,line)
        -- The marker can be part of an error message; Lua chunk names can also
        -- contain arbitrary text. Stack lines need the same token mask as the head.
        out[#out+1]=ok and type(masked)=='string' and string.gsub(masked,'[%w%+/=_%-]+',token) or '(frame withheld)'
      end
    end
  end
  return string.sub(table.concat(out,'\n'),1,M.TEXT_LIMIT)
end

------------------------------------------------------------------------------------------------------
-- isolation of callbacks
------------------------------------------------------------------------------------------------------
function M.guard(where,fn,report)
  return function(...)
    local n,args=select('#',...),{...}
    local ok,err=native_xpcall(function() return fn(unpack(args,1,n)) end,M.trace)
    if not ok then report(where,err) end
  end
end
-- uloop(real, report, process): uloop whose timer/process/fd callbacks run guarded (package.loaded.uloop).
-- process(real, path, args, env, guarded_exit) optionally starts the child itself (hv_core: the lock descriptors).
function M.uloop(real,report,process)
  local proxy=setmetatable({},{__index=real})
  proxy.timer=function(fn,ms)
    if ms~=nil then return real.timer(M.guard('timer',fn,report),ms) end
    return real.timer(M.guard('timer',fn,report))
  end
  proxy.process=function(path,args,env,fn)
    local exit=M.guard('process',fn,report)
    if process then return process(real,path,args,env,exit) end
    return real.process(path,args,env,exit)
  end
  proxy.fd_add=function(fd,fn,flags) return real.fd_add(fd,M.guard('fd',fn,report),flags) end
  return proxy
end
-- guard_object(object, conn, report, observe, clock): a failing ubus method answers {"fallback":true}
-- (rpcd -> agent.py); observe(name, seconds) hears how long each method held the loop
function M.guard_object(object,conn,report,observe,clock)
  for _,methods in pairs(object) do
    for name,spec in pairs(methods) do
      local fn=spec[1]
      if type(fn)=='function' then
        spec[1]=function(req,msg)
          local started=observe and clock and clock()
          local ok,result=native_xpcall(function() return fn(req,msg) end,M.trace)
          if started then native_pcall(observe,name,clock()-started) end
          if ok then return result end
          report('ubus '..tostring(name),result)
          native_pcall(conn.reply,conn,req,{fallback=true})
        end
      end
    end
  end
end

------------------------------------------------------------------------------------------------------
-- the record
------------------------------------------------------------------------------------------------------
-- recorder(d): d.path, d.read(path), d.write(path, text) (RAM), d.wall(), d.clock(), d.log(text).
--   report(where, err)   a failure of a callback: counted, logged and written at most every LOG_EVERY s per error
--   fatal(where, err)    the end of the process: always logged and written
--   summary()            status.json monitor_loop (nil while there is nothing to show)
-- Neither ever raises: they run where an error can do the most harm.
function M.recorder(d)
  local canon=require('canon')
  local R={}
  local rows
  local logged={}
  local function load_rows()
    if rows then return rows end
    rows={}
    local ok,value=native_pcall(function() return canon.decode(d.read(d.path)) end)
    if ok and canon.is_object(value) and canon.is_array(value.errors) then
      for _,row in ipairs(value.errors) do
        if canon.is_object(row) and type(row.signature)=='string' and #rows<M.KEEP then rows[#rows+1]=row end
      end
    end
    return rows
  end
  local function save()
    d.write(d.path,canon.encode(canon.object({schema=1,errors=canon.array(rows)})))
  end
  local function note(where,err,fatal)
    local text=M.clean(err)
    local message=string.match(text,'^[^\n]*') or ''
    local signature=tostring(where)..' | '..message
    local now=d.wall()
    load_rows()
    local row
    for index,item in ipairs(rows) do
      if item.signature==signature then row=item;table.remove(rows,index);break end
    end
    local new=row==nil
    if new then
      row=canon.object({signature=signature,where=tostring(where),first=canon.float(now),count=0})
      while #rows>=M.KEEP do table.remove(rows,1) end
    end
    rows[#rows+1]=row  -- the newest last
    row.count=(canon.number(row.count) or 0)+1
    row.last=canon.float(now)
    row.text=text
    if fatal then row.fatal=true end
    local clock=d.clock()
    if new or fatal or not logged[signature] or clock-logged[signature]>=M.LOG_EVERY then
      logged[signature]=clock
      native_pcall(save)
      d.log((fatal and 'MONITOR-LOOP-FATAL (' or 'MONITOR-LOOP-ERROR (')..tostring(where)..', seen '..canon.number(row.count)..'): '..text)
    end
  end
  local function safely(where,err,fatal)
    if not native_pcall(note,where,err,fatal) then
      native_pcall(function() io.stderr:write('hv-monitor: loop error in ',tostring(where),': ',M.WITHHELD,'\n') end)
    end
  end
  function R.report(where,err) safely(where,err,false) end
  function R.fatal(where,err) safely(where,err,true) end
  function R.load() native_pcall(load_rows) end
  function R.summary()
    local ok,value=native_pcall(function()
      load_rows()
      local last=rows[#rows]
      if not last then return nil end
      local total=0
      for _,row in ipairs(rows) do total=total+(canon.number(row.count) or 0) end
      return canon.object({errors=total,last_time=last.last,last_where=last.where,
        last_error=string.match(last.text or '','^[^\n]*') or '',fatal=last.fatal==true})
    end)
    if ok then return value end
    return nil
  end
  return R
end

return M
