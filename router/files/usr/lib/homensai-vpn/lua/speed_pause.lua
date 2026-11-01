-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- speed_pause.lua: the bounded cooperative quiet window of the speed test (Lua port of speed_pause.py, owner
-- plan item 7). Same file (RUNTIME/speed-pause.json), same fields, same validation, same timeouts, same lock
-- (auto-control.lock), so a Python or a Lua speed worker can pause a Python or a Lua monitor/Auto supervisor.
-- Never writes Auto intent or service settings.
--   gate(d, role, quiescent)  the supervisor (role 'auto') and the monitor (role 'monitor') call it at a loop
--                              boundary, outside any network transaction or control lock: true = stay quiet now.
--   public(d)                  the page field speed_pause.
--   acquire/interrupted/release/cpu_usage  the speed worker (lua/speed.lua run).
-- Clocks: d.clock() is the monotonic clock of the Lua line (/proc/uptime, CLOCK_BOOTTIME; equal to Python's
-- time.monotonic() on a router that never suspends - the values of both lines are compared in this file).
-- d (deps, tests replace it): runtime, read(path)->text|nil, is_link(path), size(path)->n|nil, write(path,text)
-- (atomic), remove(path), clock(), wall(), boot()->text, stat(pid)->text|nil (/proc/<pid>/stat),
-- cmdline(pid)->text|nil, getpid(), kill(pid,signal), sha256(text), lock(fn)->(locked, ...) (the control lock;
-- blocking variants always return true), services()->instances table|nil, sleep(seconds), pair_state(), pair_intent().
local canon=require('canon')

local M={}
M.NAME='speed-pause.json'
M.ROLES={monitor=true,auto=true}
-- The daemon command of each role: the Python line or the Lua line (one exact argv element each, like Python's
-- `('/usr/lib/homensai-vpn/'+name).encode() in command`).
M.COMMANDS={monitor={'/usr/lib/homensai-vpn/agent.py','/usr/lib/homensai-vpn/lua/monitor.lua','/usr/lib/homensai-vpn/lua/hv_core.lua'},
  auto={'/usr/lib/homensai-vpn/native_switch.py','/usr/lib/homensai-vpn/lua/auto.lua'}}
-- Lua plan item 8: hv-core runs the monitor AND the Auto supervisor in the `monitor` instance; the `native`
-- instance then only stands by (`hv_core.lua standby`), so the Auto role is owned by the monitor's process.
M.CORE='/usr/lib/homensai-vpn/lua/hv_core.lua'
M.INTENTS={'pair-auto-control.json','auto-control.json','pair-manual-control.json','manual-control.json','native-return.json'}
M.PHASES={PAUSING=true,PAUSED=true,RESUMING=true}
M.ACK_SECONDS=3
M.ACQUIRE_SECONDS=25
M.RESUME_SECONDS=25
local NULL=canon.null

local Pause={}
Pause.__tostring=function(e) return e.code end
M.PauseError=Pause
local function refuse(code) error(setmetatable({code=code},Pause),0) end
M.refuse=refuse
function M.is_pause_error(e) return type(e)=='table' and getmetatable(e)==Pause end

local function is_dict(v) return canon.is_object(v) end
local function num(v) return canon.number(v) end
local function finite(v) local n=num(v);return n~=nil and n==n and n~=math.huge and n~=-math.huge end
local function pyint(v) return type(v)=='number' and v%1==0 end
local function hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end

-- Python ==: numbers by value (1 == 1.0), dicts/lists element-wise.
local function equal(a,b)
  local x,y=num(a),num(b)
  if x~=nil or y~=nil then return x~=nil and y~=nil and x==y end
  if type(a)~='table' or type(b)~='table' or a==NULL or b==NULL then return a==b end
  if canon.is_array(a)~=canon.is_array(b) then return false end
  for k,v in pairs(a) do if b[k]==nil or not equal(v,b[k]) then return false end end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end
M.equal=equal

function M.path(d) return d.runtime..'/'..M.NAME end

local function read_json(d,path,default)
  if d.is_link(path) then error('symlink storage refused',0) end
  local text=d.read(path)
  if text==nil then return default end
  return canon.decode(text)
end
M.read_json=read_json
local function write_json(d,path,value) d.write(path,canon.encode(value)) end
local function exists(d,path) return d.size(path)~=nil end

------------------------------------------------------------------------------------------------------
-- process identity: (pid, start time in clock ticks) from /proc/<pid>/stat
------------------------------------------------------------------------------------------------------
function M.identity(d,pid)
  if not pyint(pid) or pid<1 then refuse('SPEED-PAUSE-UNVERIFIED') end
  local raw=d.stat(pid)
  if raw==nil then error('no such process',0) end
  local close
  local at=0
  while true do local i=string.find(raw,')',at+1,true);if not i then break end;close=i;at=i end
  if not close then error('malformed stat',0) end
  local fields={}
  for word in string.gmatch(string.sub(raw,close+2),'%S+') do fields[#fields+1]=word end
  if fields[1]=='Z' or fields[1]=='X' then refuse('SPEED-PAUSE-UNVERIFIED') end
  local start=fields[20] and string.find(fields[20],'^%d+$') and tonumber(fields[20])
  if not start then error('malformed stat',0) end
  return canon.object({pid=pid,start=start})
end

function M.alive(d,owner)
  local ok,result=pcall(function()
    if not is_dict(owner) then error('owner',0) end
    return equal(M.identity(d,owner.pid),owner)
  end)
  return ok and result==true
end

-- the role -> owner identity of the running daemons (ubus service list), each checked by its command line
function M.participants(d)
  local reply=d.services()
  if not is_dict(reply) or not is_dict(reply['homensai-vpn']) or not is_dict(reply['homensai-vpn'].instances) then error('service list',0) end
  local rows=reply['homensai-vpn'].instances
  local result=canon.object()
  local function argv(pid)
    local parts,set={},{}
    for part in string.gmatch(d.cmdline(pid) or '','([^%z]*)%z') do parts[#parts+1]=part;set[part]=true end
    return set
  end
  for _,role in ipairs({'monitor','auto'}) do
    local row=rows[role=='auto' and 'native' or role]
    if is_dict(row) and row.running==true then
      local owner=M.identity(d,row.pid)
      local set=argv(owner.pid)
      if role=='auto' and set[M.CORE] and set.standby then
        local core=rows.monitor
        if not (is_dict(core) and core.running==true) then refuse('SPEED-PAUSE-UNVERIFIED') end
        owner=M.identity(d,core.pid)
        local core_set=argv(owner.pid)
        if not (core_set[M.CORE] and core_set.daemon) then refuse('SPEED-PAUSE-UNVERIFIED') end
      else
        local named=false
        for _,name in ipairs(M.COMMANDS[role]) do if set[name] then named=true end end
        if not named or not set.daemon then refuse('SPEED-PAUSE-UNVERIFIED') end
      end
      result[role]=owner
    end
  end
  return result
end

function M.fingerprints(d)
  local result=canon.object()
  for _,name in ipairs(M.INTENTS) do
    local path=d.runtime..'/'..name
    if d.is_link(path) then refuse('SPEED-PAUSE-UNVERIFIED') end
    local text=d.read(path)
    result[name]=text and d.sha256(text) or NULL
  end
  return result
end

------------------------------------------------------------------------------------------------------
-- load(): nil without a pause; the validated row; SPEED-PAUSE-UNVERIFIED for anything else
------------------------------------------------------------------------------------------------------
local function valid_owner(v)
  if not is_dict(v) or count(v)~=2 then return false end
  for _,k in ipairs({'pid','start'}) do if not pyint(v[k]) or v[k]<1 then return false end end
  return true
end

function M.load(d)
  local p=M.path(d)
  if not exists(d,p) and not d.is_link(p) then return nil end
  if d.is_link(p) or (d.size(p) or 0)>8192 then refuse('SPEED-PAUSE-UNVERIFIED') end
  local row=read_json(d,p,canon.object())
  local function bad() refuse('SPEED-PAUSE-UNVERIFIED') end
  if not is_dict(row) or num(row.schema)~=1 or row.boot~=d.boot() or not hex(row.tx,32) then bad() end
  if not M.PHASES[row.phase] then bad() end
  if not finite(row.deadline) or num(row.deadline)>d.clock()+360 or type(row.auto_was_on)~='boolean' then bad() end
  if not is_dict(row.owners) or not is_dict(row.acks) then bad() end
  for k in pairs(row.owners) do if not M.ROLES[k] then bad() end end
  if not hex(row.revision,32) or not is_dict(row.intents) then bad() end
  local want={};for _,n in ipairs(M.INTENTS) do want[n]=true end
  if count(row.intents)~=#M.INTENTS then bad() end
  for k,v in pairs(row.intents) do
    if not want[k] then bad() end
    if v~=NULL and not hex(v,64) then bad() end
  end
  for k,v in pairs(row.acks) do
    if row.owners[k]==nil then bad() end
    if not is_dict(v) or not equal(v.owner,row.owners[k]) or not finite(v.time) then bad() end
  end
  if not valid_owner(row.worker) then bad() end
  for _,v in pairs(row.owners) do if not valid_owner(v) then bad() end end
  if row.phase=='RESUMING' and (not finite(row.resume_time) or not finite(row.resume_deadline)) then bad() end
  return row
end

function M.unchanged(d,row)
  local revision=read_json(d,d.runtime..'/auto-control-revision.json',canon.object())
  local current=is_dict(revision) and revision.revision or nil
  return current==row.revision and equal(M.fingerprints(d),row.intents)
end

function M.begin_resume(d,row)
  if row.phase~='RESUMING' then
    row.phase='RESUMING';row.resume_time=canon.float(d.wall());row.resume_deadline=canon.float(d.clock()+M.RESUME_SECONDS)
    write_json(d,M.path(d),row)
  end
end

------------------------------------------------------------------------------------------------------
-- speed_test.worker_alive (the deadline branch of gate needs it): the exact worker command of this job
------------------------------------------------------------------------------------------------------
M.WORKERS={'/usr/lib/homensai-vpn/speed_test.py','/usr/lib/homensai-vpn/lua/speed.lua'}
function M.worker_alive(d,job)
  if not is_dict(job) then return false end
  local pid,tx=job.pid,job.tx
  if tx==nil then tx='' end
  if not pyint(pid) or pid<1 or not hex(tx,32) then return false end
  local ok,command=pcall(d.cmdline,pid)
  if not ok or type(command)~='string' then return false end
  for _,script in ipairs(M.WORKERS) do
    if string.find(command,script..'\0run\0'..tx..'\0',1,true) then return true end
  end
  return false
end

------------------------------------------------------------------------------------------------------
-- gate(role, quiescent): called by the supervisor/monitor loop. true: skip this pass (sleep ~1 s and call again).
------------------------------------------------------------------------------------------------------
function M.gate(d,role,quiescent)
  quiescent=quiescent or function() return true end
  local p=M.path(d)
  if not d.is_link(p) and not exists(d,p) then return false end
  local ok,result=pcall(function()
    local locked,value=d.lock(function()
      local row=M.load(d)
      if not row then return false end
      local worker_up=M.alive(d,row.worker)
      if d.clock()>=num(row.deadline) and worker_up then
        local job=read_json(d,d.runtime..'/speed-job.json',canon.object())
        if is_dict(job) and job.tx==row.tx and equal(job.pid,row.worker.pid) and M.worker_alive(d,job) then
          d.kill(row.worker.pid,15)
          if M.unchanged(d,row) then return true end
        else
          worker_up=false;M.begin_resume(d,row)
        end
      end
      if not M.unchanged(d,row) then
        -- A new human command supersedes the quiet window immediately.
        write_json(d,d.runtime..'/speed-cancel.json',canon.object({tx=row.tx,time=canon.float(d.wall())}))
        M.begin_resume(d,row)
        if not worker_up then d.remove(p) end
        return false
      end
      local current=M.identity(d,d.getpid())
      if not equal(row.owners[role],current) then return false end
      if not worker_up then M.begin_resume(d,row) end
      if row.phase=='RESUMING' then
        if role=='monitor' then
          if row.owners.auto==nil or not M.alive(d,row.owners.auto) then d.remove(p) end
          return false
        end
        local ready=row.owners.monitor==nil
        if not ready then
          local status=read_json(d,d.runtime..'/status.json',canon.object())
          if not is_dict(status) then error('status',0) end
          local resume=num(row.resume_time)
          local t=status.time;if t==nil then t=0 end
          if type(t)~='number' and not canon.is_float(t) then error('status time',0) end
          ready=num(t)>=resume
          if ready then
            local profiles=status.profiles;if profiles==nil then profiles=canon.array() end
            if type(profiles)~='table' or profiles==NULL then error('profiles',0) end
            for _,profile in ipairs(profiles) do
              if not is_dict(profile) then error('profile',0) end
              if profile.administrative_state=='enabled' then
                local pt=profile.time
                if not (type(pt)=='number' or canon.is_float(pt)) or num(pt)<resume then ready=false;break end
              end
            end
          end
        end
        if ready or d.clock()>=num(row.resume_deadline) then d.remove(p);return false end
        return true
      end
      -- The monitor may have bounded asynchronous probes still in flight: checked under the same lock that
      -- grants the quiet-window acknowledgement.
      local qok,qready=pcall(quiescent)
      if not (qok and qready==true) then
        if row.acks[role]~=nil then row.acks[role]=nil;write_json(d,p,row) end
        return true
      end
      row.acks[role]=canon.object({owner=current,time=canon.float(d.clock())});write_json(d,p,row)
      return true
    end)
    if not locked then return 'busy' end
    return value
  end)
  if not ok then return false end  -- An unreadable pause can never disable normal Auto/Stop.
  if result=='busy' then return true end  -- (non-blocking lock only) another holder: look again in a second
  return result==true
end

function M.public(d)
  local ok,result=pcall(function()
    local row=M.load(d)
    if not row then return canon.object({active=false}) end
    local active=M.unchanged(d,row) and (d.clock()<num(row.deadline) or row.phase=='RESUMING')
    return canon.object({active=active,phase=row.phase,auto_paused=active and row.acks.auto~=nil,
      monitor_paused=active and row.phase~='RESUMING' and row.acks.monitor~=nil})
  end)
  if ok then return result end
  return canon.object({active=false})
end

------------------------------------------------------------------------------------------------------
-- the speed worker's side
------------------------------------------------------------------------------------------------------
local BUSY_STATES={ARMED=true,APPLYING=true,['WAIT-CLIENT']=true,RESTORING=true,['RELEASE-PENDING']=true}
local QUEUE_STATES={QUEUED=true,CLAIMED=true,APPLYING=true,['WAIT-CLIENT']=true}

-- job: {tx=, monotonic_deadline=} of the running speed job
function M.acquire(d,job)
  local p=M.path(d)
  local owners
  local started=d.lock(function()
    if d.is_link(p) or exists(d,p) then
      local previous=M.load(d)
      if previous and previous.phase=='RESUMING' and not M.alive(d,previous.worker) then
        local any=false
        for _,v in pairs(previous.owners) do if M.alive(d,v) then any=true end end
        if d.clock()>num(previous.resume_deadline) or not any then d.remove(p)
        else refuse('SPEED-PAUSE-BUSY') end
      else refuse('SPEED-PAUSE-BUSY') end
    end
    local native=read_json(d,d.runtime..'/native-status.json',canon.object())
    if not is_dict(native) then native=canon.object() end
    if BUSY_STATES[native.state] then refuse('SPEED-SWITCH-IN-PROGRESS') end
    local pair,request=d.pair_state(),d.pair_intent()
    local on=request.mode=='on'
    if on and native.state~='OBSERVING' and native.state~='COMMITTED' then refuse('SPEED-SWITCH-IN-PROGRESS') end
    local phase=pair.phase
    if phase=='STARTING' or phase=='STOPPING' or phase=='HELD' or (phase=='RUNNING' and not on) then refuse('SPEED-SWITCH-IN-PROGRESS') end
    if not on and (native.state=='OBSERVING' or native.state=='COMMITTED' or native.state=='DEGRADED-ON-RESERVE') then refuse('SPEED-PAUSE-MODE') end
    for _,name in ipairs({'manual-control.json','pair-manual-control.json'}) do
      local pending=read_json(d,d.runtime..'/'..name,canon.object())
      if is_dict(pending) and QUEUE_STATES[pending.state] then refuse('SPEED-SWITCH-IN-PROGRESS') end
    end
    owners=M.participants(d)
    local row=canon.object({schema=1,tx=job.tx,boot=d.boot(),worker=M.identity(d,d.getpid()),owners=owners,acks=canon.object(),
      revision=d.revision(),intents=M.fingerprints(d),phase='PAUSING',deadline=job.monotonic_deadline,auto_was_on=on})
    write_json(d,p,row)
    return true
  end)
  if not started then refuse('SPEED-PAUSE-BUSY') end
  local end_=d.clock()+M.ACQUIRE_SECONDS
  while d.clock()<end_ do
    if M.interrupted(d,job.tx) then refuse('SPEED-CANCELLED') end
    local _,done=d.lock(function()
      local current=M.load(d)
      if not current or current.tx~=job.tx then refuse('SPEED-PAUSE-LOST') end
      for role,owner in pairs(owners) do
        local ack=current.acks[role]
        if not (is_dict(ack) and equal(ack.owner,owner)) then return false end
        local age=d.clock()-(num(ack.time) or 0)
        if not (age>=0 and age<=M.ACK_SECONDS) then return false end
      end
      current.phase='PAUSED';write_json(d,p,current)
      return true
    end)
    if done then return true end
    d.sleep(0.2)
  end
  refuse('SPEED-PAUSE-TIMEOUT')
end

function M.interrupted(d,tx)
  local row=M.load(d)
  if not row or row.tx~=tx or row.phase=='RESUMING' then return true end
  local cancel=read_json(d,d.runtime..'/speed-cancel.json',canon.object())
  if is_dict(cancel) and cancel.tx==tx then return true end
  if d.clock()>=num(row.deadline) or not M.unchanged(d,row) then return true end
  for _,owner in pairs(row.owners) do if not M.alive(d,owner) then return true end end
  return false
end

function M.release(d,tx)
  d.lock(function()
    local row=M.load(d)
    if row and row.tx==tx then
      local any=false
      for _,v in pairs(row.owners) do if M.alive(d,v) then any=true end end
      if not any then d.remove(M.path(d)) else M.begin_resume(d,row) end
    end
  end)
end

function M.cpu_snapshot(d)
  local text=d.cpu_text and d.cpu_text() or d.read('/proc/stat')
  local line=text and string.match(text,'^[^\n]*') or ''
  local fields={}
  for word in string.gmatch(line,'%S+') do fields[#fields+1]=word end
  if fields[1]~='cpu' or #fields<9 then refuse('SPEED-CPU-UNKNOWN') end
  local values={}
  for i=2,9 do
    if not string.find(fields[i],'^%d+$') then refuse('SPEED-CPU-UNKNOWN') end
    values[#values+1]=tonumber(fields[i])
  end
  return values
end

-- Python round(x, 1) of a value that is not a tie in practice: half away from zero on the decimal shown.
local function round1(x) return tonumber(string.format('%.1f',x)) end
function M.cpu_usage(d)
  local before=M.cpu_snapshot(d);d.sleep(1);local after=M.cpu_snapshot(d)
  local delta,total={},0
  for i=1,8 do delta[i]=after[i]-before[i];total=total+delta[i] end
  for i=1,8 do if delta[i]<0 then refuse('SPEED-CPU-UNKNOWN') end end
  if total<=0 then refuse('SPEED-CPU-UNKNOWN') end
  return round1(100*(total-delta[4]-delta[5])/total)
end

------------------------------------------------------------------------------------------------------
-- router deps (nixio/io); tests build their own table of the same shape
------------------------------------------------------------------------------------------------------
function M.router(options)
  options=options or {}
  local runtime=options.runtime or '/var/run/homensai-vpn'
  local persist=options.persist or '/etc/homensai-vpn'
  local okn,nixio=pcall(require,'nixio');if not okn or type(nixio)~='table' then nixio=nil end
  local okf,nfs=pcall(require,'nixio.fs');if not okf or type(nfs)~='table' then nfs=nil end
  local mio=options.io or require('monitor_io')
  local d={runtime=runtime,persist=persist}
  -- /proc and the boot id are read directly; state files through the runner (a test runner keeps them in memory)
  local function raw(path)
    local f=io.open(path,'rb');if not f then return nil end
    local text=f:read('*a');f:close();return text
  end
  function d.read(path) return mio.read_file(path) end
  function d.is_link(path) local st=nfs and nfs.lstat and nfs.lstat(path);return st~=nil and st~=false and st.type=='lnk' end
  function d.size(path) return mio.file_size(path) end
  function d.write(path,text) mio.write_atomic(path,text) end
  function d.remove(path) if mio.remove then mio.remove(path) else os.remove(path) end end
  d.clock=options.clock or mio.clock
  d.wall=options.wall or mio.wall
  function d.boot() local text=raw('/proc/sys/kernel/random/boot_id') or '';return (string.gsub(text,'%s+$','')) end
  function d.stat(pid) return raw('/proc/'..string.format('%d',pid)..'/stat') end
  function d.cmdline(pid) return raw('/proc/'..string.format('%d',pid)..'/cmdline') end
  function d.cpu_text() return raw('/proc/stat') end
  function d.getpid()
    if nixio and nixio.getpid then return nixio.getpid() end
    local text=raw('/proc/self/stat') or '';return tonumber(string.match(text,'^(%d+)'))
  end
  function d.kill(pid,signal)
    if nixio and nixio.kill then pcall(nixio.kill,pid,signal) else os.execute('kill -'..string.format('%d',signal)..' '..string.format('%d',pid)..' 2>/dev/null') end
  end
  function d.sha256(text) return canon.sha256(text) end
  -- the control lock: blocking for Auto and the worker (Python's control_lock), non-blocking in the monitor loop
  if options.lock then d.lock=options.lock
  elseif options.nonblocking then
    d.lock=function(fn) return mio.try_lock(runtime,fn) end
  else
    d.lock=function(fn) local results={require('control').lock(fn,runtime)};return true,unpack(results) end
  end
  function d.services()
    local text=mio.capture('ubus -t 5 call service list \'{"name":"homensai-vpn"}\'')
    if not text then error('service list',0) end
    return canon.decode(text)
  end
  function d.sleep(seconds)
    if nixio and nixio.nanosleep then nixio.nanosleep(math.floor(seconds),math.floor((seconds%1)*1e9))
    else os.execute('sleep '..string.format('%.1f',seconds)) end
  end
  local function env()
    local fs={read=function(path) return mio.read_file(path) end,write_atomic=mio.write_atomic,unsafe=mio.unsafe}
    return {run={fs=fs,wall=d.wall,clock=d.clock},runtime=runtime,persist=persist}
  end
  function d.pair_state() return require('pair').read_state(env()) end
  function d.pair_intent() return require('pair').intent(env()) end
  -- auto_control.revision_locked(RUNTIME): the caller holds the control lock
  function d.revision()
    local path=runtime..'/auto-control-revision.json'
    local ok,record=pcall(read_json,d,path,canon.object())
    local revision=nil
    if ok and is_dict(record) and count(record)==1 and hex(record.revision,32) then revision=record.revision end
    if not revision then
      revision=require('auto_control').uuid_hex()
      write_json(d,path,canon.object({revision=revision}))
    end
    return revision
  end
  for key,value in pairs(options.overrides or {}) do d[key]=value end
  return d
end

return M
