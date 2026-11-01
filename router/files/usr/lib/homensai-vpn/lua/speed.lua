-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- speed.lua: the optional bounded HTTPS goodput test on Lua (port of speed_test.py, owner plan item 7).
-- No route, VPN or firewall writes. Same files (RUNTIME/speed-job.json, speed-cancel.json, speed-traffic.json,
-- speed-auto-pending.json; PERSIST/speed-history.json + backup, speed-quota.json), same fields, same codes, same
-- history rows, so the Python and the Lua line read each other's state (worker_alive accepts both workers).
--   start/cancel/public_live/public_status  rpc speed_start/speed_cancel/speed_live and the status field (monitor)
--   observe_traffic/automatic_new/prune_history/active_job  the monitor pass (agent.monitor_loop's speed part)
--   run(tx)  the worker: `lua /usr/lib/homensai-vpn/lua/speed.lua run <tx>` (a detached process of its own)
-- Measurement differences to the Python worker (documented in docs/architecture/LUA-SPEED-TELEGRAM-ITEM7):
--   * HTTPS goes through `curl --interface <dev> --resolve host:443:<address>` children (nixio has no TLS and no
--     SO_MARK, see LUA-ROUTER-FACTS); the route of the tunnel's fwmark is still verified before every request;
--   * latency_ms is curl's time_total of a 0-byte download (Python: wall time around connect+TLS+request);
--   * live samples are taken when a request (<= 1 MiB) completes, not every 64 KiB.
-- d (deps): the speed_pause deps (read/write/remove/size/is_link/clock/wall/lock/getpid/cmdline/kill/...) plus
-- persist, inventory(), retention_days(), day(now), sysfs(device,name), spawn_worker(tx)->pid|nil, uuid(),
-- route_binding(logical), route_get(address,mark)->decoded json, curl_start(argv)->handle,
-- curl_poll(handle)->nil|{exit=,out=}, curl_kill(handle), zero_file(size)->path, hires().
if arg and arg[0] and string.find(arg[0],'speed%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local canon=require('canon')
local pause=require('speed_pause')

local M={}
M.HOST='speed.cloudflare.com'
M.MIB=1024*1024
M.CLOCK_FLOOR=1704067200
M.WORKER='/usr/lib/homensai-vpn/lua/speed.lua'
M.KEYS={'speed_enabled','speed_auto_new','speed_budget_mib','speed_duration','speed_streams','speed_daily_mib','speed_busy_mbps'}
M.STATUS_KEYS={'state','started','finished','code','profiles','payload_budget_bytes','quota_reserved_bytes','daily_reserved_bytes',
  'completed','automatic','preparation','cpu_percent_after_pause'}
local NULL=canon.null
local equal=pause.equal

local Speed={}
Speed.__tostring=function(e) return e.code end
local function fail(code) error(setmetatable({code=code},Speed),0) end
M.fail=fail
function M.is_speed_error(e) return type(e)=='table' and getmetatable(e)==Speed end

local function is_dict(v) return canon.is_object(v) end
local function num(v) return canon.number(v) end
local function finite(v) local n=num(v);return n~=nil and n==n and n~=math.huge and n~=-math.huge end
local function pyint(v) return type(v)=='number' and v%1==0 end
local function hex(v,n) return type(v)=='string' and #v==n and string.find(v,'^[a-f0-9]+$')~=nil end
local function truthy(v) return v~=nil and v~=NULL and v~=false and v~='' and v~=0 and not (canon.is_float(v) and v.value==0) end
-- Python round(x, n) for display values (the decimal text of x rounded by printf, then a float)
local function round(x,n) return canon.float(tonumber(string.format('%.'..n..'f',x))) end
M.round=round
local function dget(t,k,default) if is_dict(t) and t[k]~=nil then return t[k] end;return default end

function M.paths(d)
  return {job=d.runtime..'/speed-job.json',cancel=d.runtime..'/speed-cancel.json',traffic=d.runtime..'/speed-traffic.json',
    pending=d.runtime..'/speed-auto-pending.json',history=d.persist..'/speed-history.json',backup=d.persist..'/speed-history.backup.json',
    ledger=d.persist..'/speed-quota.json'}
end
local function read_json(d,path,default) return pause.read_json(d,path,default) end
local function write_json(d,path,value) d.write(path,canon.encode(value)) end
local function read_dict(d,path) local value=read_json(d,path,canon.object());if not is_dict(value) then error('not an object',0) end;return value end

------------------------------------------------------------------------------------------------------
-- settings
------------------------------------------------------------------------------------------------------
-- Python int(value): ints, truncated floats, decimal strings with optional sign/space; anything else fails.
local function int_of(value)
  if type(value)=='number' then return value>=0 and math.floor(value) or -math.floor(-value) end
  if canon.is_float(value) then local x=value.value;return x>=0 and math.floor(x) or -math.floor(-x) end
  if type(value)=='string' then
    local text=string.match(value,'^%s*([+-]?%d+)%s*$')
    if text then return tonumber(text) end
  end
  return nil
end
M.int_of=int_of

function M.option_int(values,key,default,low,high)
  local value=values[key];if value==nil then value=default end
  local n=int_of(value)
  if n==nil then fail('SPEED-CONFIG') end
  if not (low<=n and n<=high) then fail('SPEED-CONFIG') end
  return n
end

function M.settings(data)
  local values=is_dict(data) and data.settings or nil
  if type(values)~='table' then values={} end
  local out={}
  for _,key in ipairs(M.KEYS) do
    local v=values[key]
    if v==true then out[key]='1' elseif v==false then out[key]='0' elseif v==nil then out[key]='' else out[key]=v end
  end
  return out
end

function M.value_int(values,key,default,low,high)
  local copy={};for k,v in pairs(values) do copy[k]=v end
  if not truthy(copy[key]) then copy[key]=default end
  return M.option_int(copy,key,default,low,high)
end

------------------------------------------------------------------------------------------------------
-- history (PERSIST/speed-history.json, checksummed envelope, backup)
------------------------------------------------------------------------------------------------------
function M.load_history(d)
  local p=M.paths(d)
  local found=false
  for _,path in ipairs({p.history,p.backup}) do
    local ok,result=pcall(function()
      local item=read_json(d,path,nil)
      if item==nil then return nil end
      found=true
      if not is_dict(item) then error('envelope',0) end
      local data=item.data
      if data==nil then error('data',0) end
      if num(item.schema)~=1 or item.sha256~=canon.digest(data) then return nil end
      if not is_dict(data) then error('data',0) end
      local results=data.results
      if not canon.is_array(results) and not (type(results)=='table' and results~=NULL and next(results)==nil and not is_dict(results)) then return nil end
      if #results>500 then return nil end
      for _,row in ipairs(results) do if not is_dict(row) or not finite(row.time) then return nil end end
      local period=d.retention_days()
      local cutoff=d.wall()-period*86400
      local kept=canon.array()
      for _,row in ipairs(results) do if num(row.time)>=cutoff then kept[#kept+1]=row end end
      data.results=kept;data.retention_days=period
      return data
    end)
    if ok and result~=nil then return result end
    if not ok then found=true end
  end
  if found then fail('SPEED-HISTORY-CORRUPT') end
  return canon.object({results=canon.array(),retention_days=d.retention_days()})
end

function M.append_history(d,rows)
  local p=M.paths(d)
  local data=M.load_history(d)
  local cutoff=d.wall()-num(data.retention_days)*86400
  local kept=canon.array()
  local function keep(row) local t=num(dget(row,'time',0)) or 0;if t>=cutoff then kept[#kept+1]=row end end
  for _,row in ipairs(data.results) do keep(row) end
  for _,row in ipairs(rows) do keep(row) end
  data.history_truncated=(num(dget(data,'history_truncated',0)) or 0)+math.max(0,#kept-500)
  local results=canon.array()
  for i=math.max(1,#kept-499),#kept do results[#results+1]=kept[i] end
  data.results=results
  local okr,old=pcall(read_json,d,p.history,nil)
  if okr and is_dict(old) and next(old)~=nil and old.sha256==canon.digest(old.data==nil and NULL or old.data) then write_json(d,p.backup,old) end
  write_json(d,p.history,canon.object({schema=1,data=data,sha256=canon.digest(data)}))
end

-- Age cleanup also runs without a new speed test; never spends test quota. Returns false when the lock was busy.
function M.prune_history(d)
  local p=M.paths(d)
  if d.size(p.history)==nil and d.size(p.backup)==nil then return true end
  local locked=d.lock(function()
    local data=M.load_history(d)
    local current=read_json(d,p.history,canon.object())
    if is_dict(current) and equal(current.data,data) then return end
    local envelope=canon.object({schema=1,data=data,sha256=canon.digest(data)})
    write_json(d,p.backup,envelope)
    write_json(d,p.history,envelope)
  end)
  return locked
end

------------------------------------------------------------------------------------------------------
-- quota ledger (PERSIST/speed-quota.json)
------------------------------------------------------------------------------------------------------
function M.reserve_quota(d,amount,daily_limit,now)
  local p=M.paths(d)
  local day=d.day(now)
  local envelope=read_json(d,p.ledger,nil)
  local days=canon.object()
  if envelope~=nil and envelope~=NULL and not (type(envelope)=='table' and next(envelope)==nil) then
    if not is_dict(envelope) then error('ledger',0) end
    days=envelope.data;if days==nil then days=canon.object() end
    local ok=type(days)=='table' and days~=NULL and not canon.is_array(days) and not canon.is_float(days)
    if ok then
      for k,v in pairs(days) do
        if type(k)~='string' or not string.find(k,'^%d%d%d%d%-%d%d%-%d%d$') or not pyint(v) or v<0 then ok=false end
      end
    end
    if not ok or envelope.sha256~=canon.digest(canon.object(days)) then fail('SPEED-QUOTA-CORRUPT') end
    days=canon.object(days)
  end
  if (days[day] or 0)+amount>daily_limit then fail('SPEED-DAILY-LIMIT') end
  days[day]=(days[day] or 0)+amount
  local keys={};for k in pairs(days) do keys[#keys+1]=k end
  table.sort(keys)
  local kept=canon.object()
  for i=math.max(1,#keys-6),#keys do kept[keys[i]]=days[keys[i]] end
  if kept[day]==nil then error('quota day outside the kept window',0) end  -- Python: KeyError
  write_json(d,p.ledger,canon.object({data=kept,sha256=canon.digest(kept)}))
  return kept[day]
end

------------------------------------------------------------------------------------------------------
-- request validation
------------------------------------------------------------------------------------------------------
function M.validate_request(arguments,profiles)
  local want={profiles=true,budget_mib=true,duration=true,streams=true}
  local n=0
  for k in pairs(arguments) do if not want[k] then fail('SPEED-REQUEST') end;n=n+1 end
  if n~=4 then fail('SPEED-REQUEST') end
  local ids=arguments.profiles
  if not (canon.is_array(ids) or (type(ids)=='table' and ids~=NULL and not is_dict(ids) and not canon.is_float(ids))) or #ids<1 or #ids>8 then fail('SPEED-PROFILES') end
  local seen={}
  for _,i in ipairs(ids) do
    if type(i)~='string' or seen[i] then fail('SPEED-PROFILES') end
    seen[i]=true
  end
  local known={}
  for _,p in ipairs(profiles) do known[p.id]=true end
  for _,i in ipairs(ids) do if not known[i] then fail('SPEED-PROFILES') end end
  for _,row in ipairs({{'budget_mib',1,32},{'duration',2,15},{'streams',1,4}}) do
    local v=arguments[row[1]]
    if not pyint(v) or v<row[2] or v>row[3] then fail('SPEED-REQUEST') end
  end
  return canon.object({profiles=canon.array(ids),budget_mib=arguments.budget_mib,duration=arguments.duration,streams=arguments.streams})
end

------------------------------------------------------------------------------------------------------
-- job state
------------------------------------------------------------------------------------------------------
function M.worker_alive(d,job) return pause.worker_alive(d,job) end

function M.active_job(d)
  local job=read_dict(d,M.paths(d).job)
  if job.state=='FAILED' and job.code=='SPEED-WORKER-TIMEOUT' then return M.worker_alive(d,job) end
  if job.state~='QUEUED' and job.state~='RUNNING' then return false end
  if M.worker_alive(d,job) then return true end
  return job.state=='QUEUED' and d.wall()-(num(dget(job,'started',0)) or 0)<10
end

function M.publish_job(d,job)
  local _,result=d.lock(function()
    local current=read_dict(d,M.paths(d).job)
    if current.tx~=job.tx then return false end
    local s=current.state
    if (s=='FAILED' or s=='DONE' or s=='CANCELLED') and s~=job.state then return false end
    write_json(d,M.paths(d).job,job);return true
  end)
  return result==true
end

-- Terminate only a proven own worker after its monotonic deadline + grace.
function M.expire_worker(d)
  local p=M.paths(d)
  local initial=read_dict(d,p.job)
  if initial.state~='QUEUED' and initial.state~='RUNNING' then return end
  d.lock(function()
    local job=read_dict(d,p.job)
    if (job.state~='QUEUED' and job.state~='RUNNING') or not M.worker_alive(d,job) then return end
    local limit=num(job.monotonic_deadline);if limit==nil then limit=math.huge end
    if d.clock()<=limit+15 then return end
    d.kill(job.pid,15)
    job.state='FAILED';job.finished=canon.float(d.wall());job.code='SPEED-WORKER-TIMEOUT'
    write_json(d,p.job,job)
  end)
end

local function refusal(code) return canon.object({accepted=false,code=code}) end

-- start(arguments, automatic) -> reply. The caller's lock decides blocking (worker/CLI) or not (monitor):
-- returns nil when a non-blocking control lock was busy.
function M.start(d,arguments,automatic)
  local p=M.paths(d)
  local locked,reply=d.lock(function()
    local data=d.inventory();local values=M.settings(data)
    if values.speed_enabled~='1' then return refusal('SPEED-DISABLED') end
    if automatic and values.speed_auto_new~='1' then return refusal('SPEED-AUTO-DISABLED') end
    local okv,options=pcall(M.validate_request,arguments,data.profiles)
    if not okv then
      if M.is_speed_error(options) then return refusal(options.code) end
      error(options,0)
    end
    if options.budget_mib>M.value_int(values,'speed_budget_mib',8,1,32) or options.duration>M.value_int(values,'speed_duration',5,2,15)
       or options.streams>M.value_int(values,'speed_streams',2,1,4) then return refusal('SPEED-CONFIG-LIMIT') end
    local now=d.wall()
    local old=read_dict(d,p.job)
    if now<M.CLOCK_FLOOR then return refusal('SPEED-CLOCK-UNSET') end
    local old_started=num(dget(old,'started',0)) or 0
    if old_started>now+5 then return refusal('SPEED-CLOCK-BACKWARD') end
    if M.active_job(d) then return refusal('SPEED-BUSY') end
    if pause.public(d).active==true then return refusal('SPEED-PAUSE-BUSY') end
    if now-old_started<(automatic and 300 or 60) then return refusal('SPEED-COOLDOWN') end
    local native=read_json(d,d.runtime..'/native-status.json',canon.object())
    local state=is_dict(native) and native.state or nil
    if state=='ARMED' or state=='APPLYING' or state=='WAIT-CLIENT' or state=='RESTORING' then return refusal('SPEED-SWITCH-IN-PROGRESS') end
    -- CPU admission is measured by the worker after the two quiet-window acknowledgements.
    local traffic=read_dict(d,p.traffic)
    local rate=num(traffic.rate_bps)
    local age=d.clock()-(num(dget(traffic,'monotonic',0)) or 0)
    if rate==nil or not (0<=age and age<=90) then return refusal('SPEED-TRAFFIC-UNKNOWN') end
    if rate>M.value_int(values,'speed_busy_mbps',2,1,1000)*1e6 then return refusal('SPEED-TRAFFIC-BUSY') end
    local quota=options.budget_mib*M.MIB*#options.profiles
    local daily=M.value_int(values,'speed_daily_mib',128,1,1024)*M.MIB
    local okq,used=pcall(M.reserve_quota,d,quota,daily,now)
    if not okq then
      if M.is_speed_error(used) then return refusal(used.code) end
      error(used,0)
    end
    local tx=d.uuid()
    local duration=35+math.min(300,#options.profiles*(2*options.duration+15))
    local job=canon.object({profiles=options.profiles,budget_mib=options.budget_mib,duration=options.duration,streams=options.streams,
      state='QUEUED',tx=tx,started=canon.float(now),deadline=canon.float(now+duration),monotonic_deadline=canon.float(d.clock()+duration),
      quota_reserved_bytes=quota,daily_reserved_bytes=used,automatic=automatic and true or false})
    write_json(d,p.job,job)
    local okp,pid=pcall(d.spawn_worker,tx)
    if not okp or not pyint(pid) or pid<1 then
      job.state='FAILED';job.code='SPEED-WORKER-START';write_json(d,p.job,job)
      return refusal('SPEED-WORKER-START')
    end
    -- Child progress uses the same lock (held here until the reply): this pid publication cannot overwrite it.
    job.pid=pid;write_json(d,p.job,job)
    return canon.object({accepted=true,queued=true,run_id=tx,payload_budget_bytes=quota})
  end)
  if not locked then return nil end
  return reply
end

function M.cancel(d)
  local p=M.paths(d)
  local locked,reply=d.lock(function()
    local job=read_dict(d,p.job)
    if not M.active_job(d) then return canon.object({queued=false,code='SPEED-NOT-RUNNING'}) end
    write_json(d,p.cancel,canon.object({tx=job.tx,time=canon.float(d.wall())}))
    return canon.object({queued=true})
  end)
  if not locked then return nil end
  return reply
end

------------------------------------------------------------------------------------------------------
-- the monitor's part
------------------------------------------------------------------------------------------------------
local SAFE='^[A-Za-z0-9_.:-]+$'
-- Sample unique VPN (or WAN) device counters in RAM; counter resets remain unknown.
function M.observe_traffic(d,rows,scope)
  local path=M.paths(d).traffic
  local old=read_json(d,path,canon.object());if not is_dict(old) then old=canon.object() end
  local counters,order=canon.object(),{}
  local now=d.clock()
  for _,row in ipairs(rows) do
    local device=is_dict(row) and row.device or (type(row)=='table' and row.device) or nil
    if type(device)=='string' and #device<=15 and #device>=1 and string.find(device,SAFE) and counters[device]==nil then
      local rx,tx=int_of(d.sysfs(device,'statistics/rx_bytes')),int_of(d.sysfs(device,'statistics/tx_bytes'))
      if rx and tx then counters[device]=rx+tx;order[#order+1]=device end
    end
  end
  local elapsed=now-(num(dget(old,'monotonic',now)) or now)
  local previous=dget(old,'counters',canon.object())
  local valid=#order>0 and is_dict(previous) and elapsed>0 and elapsed<=90
  if valid then
    local n=0
    for k,v in pairs(previous) do n=n+1;if counters[k]==nil then valid=false end end
    if n~=#order then valid=false end
    for k,v in pairs(counters) do local before=num(previous[k]);if before==nil or v<before then valid=false end end
  end
  local rate=NULL
  if valid then
    local sum=0;for k,v in pairs(counters) do sum=sum+(v-num(previous[k])) end
    rate=canon.float(8*sum/elapsed)
  end
  write_json(d,path,canon.object({monotonic=canon.float(now),counters=counters,rate_bps=rate,scope=scope}))
end

-- First observation is baseline; busy tests stay pending without reconnecting. previous: set {id=true} or nil.
-- Returns the new set (the same `previous` when the control lock was busy: the new profiles are tried next pass).
function M.automatic_new(d,rows,previous,data)
  local active={}
  for _,row in ipairs(rows) do if truthy(row.interface) then active[row.id]=true end end
  local values=M.settings(data)
  if previous==nil or values.speed_enabled~='1' or values.speed_auto_new~='1' then return active end
  local path=M.paths(d).pending
  local saved=read_json(d,path,canon.object())
  local pending={}
  for _,id in ipairs(is_dict(saved) and type(saved.profiles)=='table' and saved.profiles~=NULL and saved.profiles or {}) do
    if type(id)=='string' and active[id] then pending[id]=true end
  end
  for id in pairs(active) do if not previous[id] then pending[id]=true end end
  local sorted={};for id in pairs(pending) do sorted[#sorted+1]=id end;table.sort(sorted)
  local selected=canon.array();for i=1,math.min(8,#sorted) do selected[#selected+1]=sorted[i] end
  if #selected>0 then
    local args=canon.object({profiles=selected,budget_mib=M.value_int(values,'speed_budget_mib',8,1,32),
      duration=M.value_int(values,'speed_duration',5,2,15),streams=M.value_int(values,'speed_streams',2,1,4)})
    local result=M.start(d,args,true)
    if result==nil then return previous end
    if result.accepted==true then for _,id in ipairs(selected) do pending[id]=nil end end
    sorted={};for id in pairs(pending) do sorted[#sorted+1]=id end;table.sort(sorted)
    local kept=canon.array();for i=1,math.min(32,#sorted) do kept[#kept+1]=sorted[i] end
    write_json(d,path,canon.object({profiles=kept,last_code=result.code==nil and NULL or result.code}))
  end
  return active
end

------------------------------------------------------------------------------------------------------
-- page views
------------------------------------------------------------------------------------------------------
local PHASES={waiting=true,resolving=true,latency=true,download=true,upload=true,done=true,failed=true,cancelled=true}
local STATES={QUEUED=true,RUNNING=true,DONE=true,FAILED=true,CANCELLED=true}
local function idle(d) return canon.object({state='IDLE',profiles=canon.array(),server_time=canon.float(d.wall())}) end
local function code_ok(v) return type(v)=='string' and #v>=7 and #v<=70 and string.find(v,'^SPEED%-[A-Z0-9-]+$')~=nil end
local function number_within(v,limit) return finite(v) and num(v)>=0 and num(v)<=limit end
local function list_of(v) return (canon.is_array(v) or (type(v)=='table' and v~=NULL and not is_dict(v) and not canon.is_float(v))) and v or nil end

-- Read-only lightweight snapshot; never probes, reserves quota or loads flash history.
function M.public_live(d,job)
  if job==nil then job=read_json(d,M.paths(d).job,canon.object()) end
  if not is_dict(job) then return idle(d) end
  local tx,ids=job.tx,list_of(job.profiles)
  if not hex(tx,32) or not ids or #ids<1 or #ids>8 then return idle(d) end
  local seen,unique={},0
  for _,i in ipairs(ids) do
    if type(i)~='string' or #i<1 or #i>96 or not string.find(i,SAFE) then return idle(d) end
    if not seen[i] then seen[i]=true;unique=unique+1 end
  end
  if unique~=#ids then return idle(d) end
  local result=canon.object({run_id=tx,state=STATES[job.state] and job.state or 'FAILED',profiles=canon.array(),server_time=canon.float(d.wall())})
  if result.state=='RUNNING' and not M.worker_alive(d,job) then result.state='FAILED';result.code='SPEED-WORKER-LOST' end
  if result.state=='QUEUED' and not M.worker_alive(d,job) and (not finite(job.started) or d.wall()-num(job.started)>=10) then
    result.state='FAILED';result.code='SPEED-WORKER-LOST'
  end
  local live=list_of(job.live) or {}
  for index,raw in ipairs(live) do
    if index>8 then break end
    local duplicate=false
    if is_dict(raw) then for _,r in ipairs(result.profiles) do if r.id==raw.id then duplicate=true end end end
    if is_dict(raw) and seen[raw.id] and not duplicate then
      local row=canon.object({id=raw.id,phase=PHASES[raw.phase] and raw.phase or 'failed',samples=canon.array()})
      local samples=list_of(raw.samples)
      if samples and #samples<=128 then
        local previous=-1
        for _,point in ipairs(samples) do
          local okp=list_of(point) and #point==3 and number_within(point[1],300) and num(point[1])>=previous
          if okp then
            local present=0
            for i=2,3 do
              if point[i]~=NULL then
                if not number_within(point[i],10000000) then okp=false end
                present=present+1
              end
            end
            if present~=1 then okp=false end
          end
          if okp then row.samples[#row.samples+1]=point;previous=num(point[1]) end
        end
      end
      for _,key in ipairs({'download_mbps','upload_mbps'}) do if number_within(raw[key],10000000) then row[key]=raw[key] end end
      if number_within(raw.updated,4102444800) then row.updated=raw.updated end
      if code_ok(raw.code) then row.code=raw.code end
      result.profiles[#result.profiles+1]=row
    end
  end
  if code_ok(job.code) then result.code=job.code end
  if job.preparation=='pausing' or job.preparation=='testing' then result.preparation=job.preparation end
  return result
end

-- load_history: the monitor passes a cached reader (the history file is parsed and hashed only when it changed)
function M.public_status(d,load_history)
  M.expire_worker(d)
  local job=read_dict(d,M.paths(d).job)
  local result=canon.object()
  for _,key in ipairs(M.STATUS_KEYS) do if job[key]~=nil then result[key]=job[key] end end
  if (job.state=='QUEUED' or job.state=='RUNNING') and not M.active_job(d) then result.state='FAILED';result.code='SPEED-WORKER-LOST' end
  result.live=M.public_live(d,job)
  local ok,history=pcall(load_history or M.load_history,d)
  if ok then for k,v in pairs(history) do result[k]=v end
  elseif M.is_speed_error(history) then result.results=canon.array();result.history_error=history.code
  else error(history,0) end
  return result
end

------------------------------------------------------------------------------------------------------
-- the worker
------------------------------------------------------------------------------------------------------
-- IPv4Address(text).is_global of Python 3.9 (not private, not 100.64.0.0/10); nil for an invalid address.
local NOT_GLOBAL={{0,0,0,0,8},{10,0,0,0,8},{127,0,0,0,8},{169,254,0,0,16},{172,16,0,0,12},{192,0,0,0,29},{192,0,0,170,31},
  {192,0,2,0,24},{192,168,0,0,16},{198,18,0,0,15},{198,51,100,0,24},{203,0,113,0,24},{240,0,0,0,4},{255,255,255,255,32},{100,64,0,0,10}}
function M.ipv4(text)
  if type(text)~='string' then return nil end
  local parts={string.match(text,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')}
  if #parts~=4 then return nil end
  local value=0
  for _,part in ipairs(parts) do
    if #part>3 or (#part>1 and string.sub(part,1,1)=='0') then return nil end
    local n=tonumber(part);if n>255 then return nil end
    value=value*256+n
  end
  return value
end
function M.is_global(text)
  local value=M.ipv4(text)
  if not value then return nil end
  for _,net in ipairs(NOT_GLOBAL) do
    local base=((net[1]*256+net[2])*256+net[3])*256+net[4]
    local size=2^(32-net[5])
    if value>=base and value<base+size then return false end
  end
  return true
end

function M.verify_route(d,binding,address)
  local global=M.is_global(address)
  if global==nil then error('invalid address',0) end
  if not global then fail('SPEED-ADDRESS') end
  local answer=d.route_get(address,binding.mark)
  if type(answer)~='table' or #answer~=1 or not is_dict(answer[1]) or answer[1].dev~=binding.device then fail('SPEED-ROUTE-UNVERIFIED') end
  local tbl=answer[1].table;if tbl==nil then tbl='main' end
  if tostring(canon.number(tbl) or tbl)~=tostring(binding.table) then fail('SPEED-ROUTE-UNVERIFIED') end
end

-- One curl request through the tunnel device to a fixed address. spec: {host=, address=, path=, method='GET'|'POST',
-- amount=, seconds=, max=bytes}. Returns {exit=, http=, size_download=, size_upload=, time_total=}.
M.WRITE_OUT='%{http_code} %{size_download} %{size_upload} %{time_total}'
function M.curl_argv(d,binding,spec)
  local argv={'/usr/bin/curl','-q','-s','--http1.1','--proto','=https','--max-redirs','0',
    '--connect-timeout',string.format('%.3f',math.max(0.1,math.min(3,spec.seconds))),'-m',string.format('%.3f',math.max(0.1,spec.seconds)),
    '--speed-limit','1','--speed-time','3','--interface',binding.device,'--resolve',spec.host..':443:'..spec.address,
    '-H','Connection: close','-H','Cache-Control: no-cache','-o','/dev/null','-w',M.WRITE_OUT}
  if spec.max then argv[#argv+1]='--max-filesize';argv[#argv+1]=string.format('%d',spec.max) end
  if spec.method=='POST' then
    argv[#argv+1]='-H';argv[#argv+1]='Content-Type: application/octet-stream'
    argv[#argv+1]='--data-binary';argv[#argv+1]='@'..d.zero_file(spec.amount)
  end
  argv[#argv+1]='https://'..spec.host..spec.path
  return argv
end
function M.parse_write_out(text)
  local code,down,up,total=string.match(text or '','(%d+) (%d+) (%d+) ([0-9.]+)%s*$')
  if not code then return nil end
  return {http=tonumber(code),size_download=tonumber(down),size_upload=tonumber(up),time_total=tonumber(total)}
end

-- Starts one transfer: verifies the route first (Python connect()), then the curl child.
local function start_request(d,binding,address,direction,amount,deadline)
  M.verify_route(d,binding,address)
  local path=direction=='upload' and '/__up' or ('/__down?bytes='..string.format('%d',amount))
  local spec={host=M.HOST,address=address,path=path,method=direction=='upload' and 'POST' or 'GET',amount=amount,
    seconds=deadline-d.clock(),max=direction=='upload' and 8192 or math.max(amount,1)}
  return d.curl_start(M.curl_argv(d,binding,spec))
end

-- The outcome of a finished transfer: bytes of a complete payload, or an error code (Python request()).
-- 'window' = the request was cut by the end of the measurement window (Python: retained only completed payloads).
local function outcome(d,result,direction,amount,deadline)
  local out=M.parse_write_out(result.out)
  if result.exit==28 or (result.exit~=0 and d.clock()>=deadline) then
    if d.clock()>=deadline then return nil,'window' end
    return nil,'SPEED-NETWORK'
  end
  if direction=='upload' and result.exit==63 then return nil,'SPEED-RESPONSE-LIMIT' end
  if result.exit==18 then return nil,'SPEED-SHORT-RESPONSE' end
  if result.exit~=0 or not out then return nil,'SPEED-NETWORK' end
  if out.http~=200 then return nil,'SPEED-HTTP' end
  if direction=='upload' then
    if out.size_upload<amount then return nil,'SPEED-NETWORK' end
    return amount
  end
  if out.size_download<amount then return nil,'SPEED-SHORT-RESPONSE' end
  return amount
end

-- resolve_endpoint: DNS over HTTPS to dns.google (8.8.8.8) through the tunnel, first global A record.
function M.resolve_endpoint(d,binding,deadline)
  M.verify_route(d,binding,'8.8.8.8')
  local body=d.temp_file and d.temp_file() or nil
  local argv={'/usr/bin/curl','-q','-s','--http1.1','--proto','=https','--max-redirs','0',
    '--connect-timeout',string.format('%.3f',math.max(0.1,math.min(3,deadline-d.clock()))),'-m',string.format('%.3f',math.max(0.1,deadline-d.clock())),
    '--interface',binding.device,'--resolve','dns.google:443:8.8.8.8','-H','Connection: close','--max-filesize','32768',
    '-o',body or '/dev/null','-w',M.WRITE_OUT,'https://dns.google/resolve?name=speed.cloudflare.com&type=A'}
  local result=d.curl_wait(d.curl_start(argv))
  local text=body and d.read(body) or nil
  if body then d.remove(body) end
  local out=M.parse_write_out(result.out)
  if result.exit==63 then fail('SPEED-DNS') end
  if result.exit~=0 or not out then error('dns transport',0) end
  if out.http~=200 or text==nil or #text>32768 then fail('SPEED-DNS') end
  local data=canon.decode(text)
  if not is_dict(data) or num(data.Status)~=0 or not list_of(data.Answer) or #data.Answer>32 then fail('SPEED-DNS') end
  for _,row in ipairs(data.Answer) do
    if is_dict(row) and num(row.type)==1 and type(row.data)=='string' then
      if M.is_global(row.data) then M.verify_route(d,binding,row.data);return row.data end
    end
  end
  fail('SPEED-DNS')
end

-- stage(): `streams` parallel transfers of <= 1 MiB each from one payload budget for `duration` seconds.
-- progress(mbps, observed_bytes, elapsed) like Python's report(): at most every 0.5 s and once at the end.
function M.stage(d,binding,address,direction,budget,duration,streams,cancelled,progress)
  local remaining=budget
  local started=d.clock();local deadline=started+duration
  local observed,last_bytes,last_at=0,0,started
  local function report(amount,final)
    observed=observed+(amount or 0);local now=d.clock();local elapsed=now-last_at
    if progress and observed>last_bytes and elapsed>0 and (final or elapsed>=0.5) then
      progress((observed-last_bytes)*8/elapsed/1e6,observed,now-started)
      last_bytes=observed;last_at=now
    end
  end
  local running,total,failure={},0,nil
  local function launch()
    while #running<streams and failure==nil and d.clock()<deadline and remaining>0 and not cancelled() do
      local amount=math.min(M.MIB,remaining);remaining=remaining-amount
      local ok,handle=pcall(start_request,d,binding,address,direction,amount,deadline)
      if not ok then failure=M.is_speed_error(handle) and handle.code or 'SPEED-NETWORK';return end
      running[#running+1]={handle=handle,amount=amount}
    end
  end
  local stopped=false
  launch()
  local next_check=d.clock()+0.5
  while #running>0 do
    d.sleep(0.05)
    local still={}
    for _,job in ipairs(running) do
      local result=d.curl_poll(job.handle)
      if result==nil then still[#still+1]=job
      else
        local bytes,code=outcome(d,result,direction,job.amount,deadline)
        if bytes then total=total+bytes;report(bytes)
        elseif code~='window' and failure==nil then failure=code end
      end
    end
    running=still
    if d.clock()>=next_check then
      next_check=d.clock()+0.5
      if not stopped and (cancelled() or failure~=nil) then
        stopped=true;for _,job in ipairs(running) do d.curl_kill(job.handle) end
      end
    end
    if not stopped and failure==nil then launch() end
  end
  local elapsed=d.clock()-started
  if cancelled() then fail('SPEED-CANCELLED') end
  if failure then fail(failure) end
  if total<=0 or elapsed<=0 then fail('SPEED-NO-SAMPLE') end
  report(0,true)
  return canon.object({payload_bytes=total,seconds=round(elapsed,3),mbps=round(total*8/elapsed/1e6,3)})
end

-- LiveProgress: measured payload rates in RAM only, bounded and bound to one job/profile.
local Live={};Live.__index=Live
function M.Live(d,job)
  local rows=canon.array()
  for _,identifier in ipairs(job.profiles) do rows[#rows+1]=canon.object({id=identifier,phase='waiting',samples=canon.array()}) end
  job.live=rows
  return setmetatable({d=d,job=job,starts={}},Live)
end
function Live:row(identifier) for _,r in ipairs(self.job.live) do if r.id==identifier then return r end end end
function Live:phase(identifier,phase)
  local row=self:row(identifier)
  if self.starts[identifier]==nil then self.starts[identifier]=self.d.clock() end
  row.phase=phase;row.updated=canon.float(self.d.wall());self.job.current_profile=identifier
  M.publish_job(self.d,self.job)
end
function Live:sample(identifier,direction,mbps,total)
  if not (mbps==mbps and mbps>=0 and mbps<=10000000) then return end
  local row=self:row(identifier)
  local elapsed=round(self.d.clock()-self.starts[identifier],3)
  local value=round(mbps,3)
  local samples=canon.array();for _,s in ipairs(row.samples) do samples[#samples+1]=s end
  samples[#samples+1]=canon.array({elapsed,direction=='download' and value or NULL,direction=='upload' and value or NULL})
  local kept=canon.array();for i=math.max(1,#samples-127),#samples do kept[#kept+1]=samples[i] end
  row.samples=kept;row.updated=canon.float(self.d.wall());row[direction..'_mbps']=value;row[direction..'_bytes']=total
  M.publish_job(self.d,self.job)
end
function Live:finish(identifier,code)
  local row=self:row(identifier)
  row.phase=code=='SPEED-CANCELLED' and 'cancelled' or (code and 'failed' or 'done')
  row.code=code==nil and NULL or code;row.updated=canon.float(self.d.wall())
  M.publish_job(self.d,self.job)
end

-- measure(profile, job, cancelled, live) -> the history row (Python measure(): same keys and codes)
function M.measure(d,profile,options,cancelled,live)
  local row=canon.object({id=profile.id,name=profile.name,protocol=profile.protocol,channel=profile.channel==nil and 'default' or profile.channel,
    time=canon.float(d.wall()),endpoint=M.HOST,method='bounded-HTTPS-payload-goodput',scope='router-originated-IPv4',
    payload_budget_bytes=options.budget_mib*M.MIB,overhead_in_budget=false})
  if live then live:phase(profile.id,'resolving') end
  if not truthy(profile.interface) then
    if live then live:finish(profile.id,'SPEED-PROFILE-INACTIVE') end
    row.code='SPEED-PROFILE-INACTIVE';return row
  end
  local ok,err=pcall(function()
    local binding=d.route_binding(profile.interface)
    if binding.code~=nil and binding.code~=NULL then fail('SPEED-ROUTE-UNVERIFIED') end
    local address=M.resolve_endpoint(d,binding,d.clock()+6)
    if live then live:phase(profile.id,'latency') end
    local latencies={}
    for _=1,3 do
      local start=d.clock()
      local result=d.curl_wait(start_request(d,binding,address,'download',0,start+3))
      local out=M.parse_write_out(result.out)
      if result.exit~=0 or not out then error('latency transport',0) end
      if out.http~=200 then fail('SPEED-HTTP') end
      latencies[#latencies+1]=out.time_total*1000
    end
    table.sort(latencies)
    row.latency_ms=round(latencies[2],1)
    local budget=options.budget_mib*M.MIB;local down=math.floor(budget*3/4)
    for _,step in ipairs({{'download',down},{'upload',budget-down}}) do
      local direction,amount=step[1],step[2]
      if live then live:phase(profile.id,direction) end
      local callback=live and function(mbps,total) live:sample(profile.id,direction,mbps,total) end or nil
      row[direction]=M.stage(d,binding,address,direction,amount,options.duration,options.streams,cancelled,callback)
    end
  end)
  if ok then
    if live then live:finish(profile.id) end
    row.code=NULL;return row
  end
  local code=M.is_speed_error(err) and err.code or 'SPEED-NETWORK'
  if d.log and not M.is_speed_error(err) then d.log('speed measure: '..tostring(type(err)=='table' and err.code or err)) end
  if live then live:finish(profile.id,code) end
  row.code=code;return row
end

function M.run(d,tx)
  if not hex(tx,32) then return end
  local p=M.paths(d)
  local job=read_json(d,p.job,canon.object())
  if not is_dict(job) or job.tx~=tx or job.state~='QUEUED' then return end
  local quiet_acquired=false
  local function cancelled()
    local cancel=read_json(d,p.cancel,canon.object())
    if is_dict(cancel) and cancel.tx==tx then return true end
    if d.clock()>=num(job.monotonic_deadline) then return true end
    local current=read_json(d,p.job,canon.object())
    if not is_dict(current) or current.tx~=tx then return true end
    return quiet_acquired and pause.interrupted(d,tx)
  end
  job.pid=d.getpid();job.completed=0;job.preparation='pausing'
  if not M.publish_job(d,job) then return end
  local rows=canon.array()
  local live=M.Live(d,job)
  M.publish_job(d,job)
  local ok,err=pcall(function()
    pause.acquire(d,job);quiet_acquired=true
    local usage=pause.cpu_usage(d);job.cpu_percent_after_pause=canon.float(usage)
    if cancelled() then fail('SPEED-CANCELLED') end
    if usage>75 then fail('SPEED-CPU-BUSY') end
    job.state='RUNNING';job.preparation='testing';M.publish_job(d,job)
    for _,identifier in ipairs(job.profiles) do
      if cancelled() then break end
      local data=d.inventory()
      local profile=nil
      for _,candidate in ipairs(data.profiles) do if candidate.id==identifier then profile=candidate end end
      local custom={}
      for _,s in ipairs(data.servers) do if is_dict(s) and s.profile==identifier then custom=s;break end end
      if not profile then fail('SPEED-PROFILES-CHANGED') end
      local copy=canon.object();for k,v in pairs(profile) do copy[k]=v end
      copy.name=truthy(custom.name) and custom.name or profile.name
      copy.channel=truthy(custom.channel) and custom.channel or 'default'
      rows[#rows+1]=M.measure(d,copy,job,cancelled,live);job.completed=#rows;M.publish_job(d,job)
    end
    if #rows>0 then d.lock(function() M.append_history(d,rows) end) end
    local stop=cancelled()
    job.state=stop and 'CANCELLED' or 'DONE';job.finished=canon.float(d.wall());job.code=stop and 'SPEED-CANCELLED' or 'SPEED-COMPLETE'
    M.publish_job(d,job)
  end)
  if not ok then
    local code='SPEED-SYSTEM'
    if M.is_speed_error(err) or pause.is_pause_error(err) then code=err.code end
    if d.log and code=='SPEED-SYSTEM' then d.log('speed worker: '..tostring(type(err)=='table' and err.code or err)) end
    local failed=canon.object();for k,v in pairs(job) do failed[k]=v end
    failed.state='FAILED';failed.finished=canon.float(d.wall());failed.code=code
    pcall(M.publish_job,d,failed)
  end
  -- Withdrawal grants no new Start: original intent is never overwritten. The monitor resumes first; Auto waits
  -- for its post-test observation.
  pcall(pause.release,d,tx)
end

------------------------------------------------------------------------------------------------------
-- router deps
------------------------------------------------------------------------------------------------------
local function quote(arg)
  if type(arg)~='string' or string.find(arg,"[%z\n']") then error('speed: unsafe command argument',0) end
  return "'"..arg.."'"
end
M.quote=quote
-- A detached child never inherits a held control lock (control.lua's or the monitor's try_lock descriptor):
-- a flock belongs to the open file description, so an inherited descriptor would keep the lock for the
-- child's whole life (Python's Popen closes them: close_fds).
function M.closing(mio)
  local parts={}
  local held={require('control').held_fd(),mio and mio.held_fd and mio.held_fd() or false}
  for i=1,2 do
    local fd=held[i]
    if type(fd)=='number' then parts[#parts+1]=' '..string.format('%d',fd)..'>&-' end
  end
  return table.concat(parts)
end

-- options: runtime, persist, io (monitor_io or the monitor's runner), inventory=function() (the monitor's),
-- retention_days=function(), nonblocking=true (the monitor loop)
function M.router(options)
  options=options or {}
  local mio=options.io or require('monitor_io')
  local d=pause.router(options)
  local runtime,persist=d.runtime,d.persist
  local probe=require('probe')
  d.inventory=options.inventory or function()
    local text,err=mio.command('inventory')
    if not text then error(err or 'inventory unavailable',0) end
    return require('monitor').normalise_inventory(canon.plain(canon.decode(text)))
  end
  d.retention_days=options.retention_days or function()
    -- retention_settings.configured_days(): the owner's period (time or size mode) from the main section
    local ok,value=pcall(function() return require('uci').cursor():get_all('homensai_vpn','main') end)
    return require('retention').days(ok and type(value)=='table' and value or nil)
  end
  function d.day(now) return os.date('%Y-%m-%d',math.floor(now)) end
  function d.sysfs(device,name) return mio.sysfs(device,name) end
  function d.uuid() return require('auto_control').uuid_hex() end
  function d.hires() return mio.hires and mio.hires() or d.clock() end
  function d.log(text) if mio.log then pcall(mio.log,text) end end
  function d.route_binding(logical) return probe.route_binding(mio,logical) end
  function d.route_get(address,mark)
    local text,err=mio.command('route_get',address,string.format('%d',mark))
    if not text then error(err or 'route get',0) end
    return canon.plain(canon.decode(text))
  end
  -- the detached worker: its own process (not a child the monitor's uloop reaps); the pid comes back from $!
  function d.spawn_worker(tx)
    if not hex(tx,32) then return nil end
    local pidfile=runtime..'/.speed-worker-'..canon.unique()..'.pid'
    local line='/usr/bin/lua '..M.WORKER..' run '..tx..' </dev/null >/dev/null 2>&1'..M.closing(mio)..' & echo $! >'..pidfile
    os.execute(line)
    local text=d.read(pidfile);os.remove(pidfile)
    return tonumber(string.match(text or '','^(%d+)'))
  end
  local zeros={}
  function d.zero_file(size)
    if zeros[size] then return zeros[size] end
    local path=runtime..'/.speed-zero-'..string.format('%d',size)..'-'..canon.unique()..'.bin'
    local f=assert(io.open(path,'wb'))
    local block=string.rep('\0',65536);local left=size
    while left>0 do local n=math.min(65536,left);f:write(n==65536 and block or string.sub(block,1,n));left=left-n end
    f:close();zeros[size]=path
    return path
  end
  function d.cleanup() for _,path in pairs(zeros) do os.remove(path) end;zeros={} end
  function d.temp_file() return runtime..'/.speed-body-'..canon.unique()..'.out' end
  -- curl children: a background subshell records the child's pid, its -w line and its exit status in our RAM files
  function d.curl_start(argv)
    local base=runtime..'/.speed-curl-'..canon.unique()
    local parts={};for i,a in ipairs(argv) do parts[i]=quote(a) end
    local line='( '..table.concat(parts,' ')..' >'..base..'.out 2>/dev/null </dev/null & echo $! >'..base..'.pid; wait $!; echo $? >'..base..'.st.part; mv '..base..'.st.part '..base..'.st ) </dev/null >/dev/null 2>&1'..M.closing(mio)..' &'
    os.execute(line)
    return {base=base}
  end
  function d.curl_poll(handle)
    local status=d.read(handle.base..'.st')
    if status==nil then return nil end
    local out=d.read(handle.base..'.out') or ''
    for _,suffix in ipairs({'.st','.out','.pid'}) do os.remove(handle.base..suffix) end
    return {exit=tonumber(string.match(status,'^(%d+)')) or 255,out=out}
  end
  function d.curl_kill(handle)
    local pid=tonumber(string.match(d.read(handle.base..'.pid') or '','^(%d+)'))
    if pid and pid>1 then d.kill(pid,9) end
  end
  function d.curl_wait(handle)
    local limit=d.clock()+30
    while true do
      local result=d.curl_poll(handle)
      if result then return result end
      if d.clock()>limit then d.curl_kill(handle);error('curl wait',0) end
      d.sleep(0.05)
    end
  end
  for key,value in pairs(options.overrides or {}) do d[key]=value end
  return d
end

-- `lua /usr/lib/homensai-vpn/lua/speed.lua run <tx>`: the worker process
function M.main(argv)
  if argv[1]~='run' or not hex(argv[2],32) then return 2 end
  local okn,nixio=pcall(require,'nixio')
  if okn and type(nixio)=='table' then
    if nixio.setsid then pcall(nixio.setsid) end  -- like start_new_session: a monitor restart never ends the test
    if nixio.setenv then nixio.setenv('TZ',require('monitor_io').TZ) end
  end
  local d=M.router({})
  local ok,err=pcall(M.run,d,argv[2])
  pcall(d.cleanup)
  if not ok then io.stderr:write('speed worker: ',tostring(type(err)=='table' and err.code or err),'\n');return 1 end
  return 0
end

if arg and arg[0] and string.find(arg[0],'speed%.lua$') and arg[1]=='run' then os.exit(M.main(arg)) end

return M
