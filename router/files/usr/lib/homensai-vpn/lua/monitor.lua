-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- monitor.lua: hv-monitor, the Lua port of agent.monitor_loop (owner plan items 2 and 3, 2.0.0-lua-alpha4).
-- One pass = inventory -> route-bound probes (asynchronous: curl children, device-bound UDP/ICMP sockets, never
-- blocking uloop) -> counters/activity -> events -> probe policy -> status.json -> checkpoint when due.
-- The published status stays in memory and is answered by rpc.lua without re-reading the file.
-- Runner (monitor_io.lua or a test fake) is the only way out of the process.
-- Not ported yet (fields absent or reduced, see docs/architecture/LUA-MONITOR-ITEM2-2026-10-31.ru.md):
-- failure_diagnosis/failover_plan/candidate_hierarchy, suspicion watcher, website/latency/
-- compare histories, speed tests, Telegram, reliability, system_readiness, scan_control.
if arg and arg[0] and string.find(arg[0],'monitor%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local canon=require('canon')
local probe=require('probe')
local accounting=require('accounting')
local rpc=require('rpc')
local policy=require('probe_policy')
local responses=require('response_history')
local page=require('monitor_status')
local vendor=require('vendor')

local M={}
M.VERSION=require('version')
M.PROFILE_PATTERN=function(s) return type(s)=='string' and (string.find(s,'^openvpn:%d+_%d+$') or string.find(s,'^wireguard:peer_%d+$'))~=nil end
M.CLOCK_FLOOR=1704067200
M.LEVELS=policy.LEVELS
M.CRITICAL_SAVE_SPACING=60
M.PROBE_WORKERS=2          -- agent.monitor_loop: ThreadPoolExecutor(max_workers=2) over the profiles
M.PASS_WATCHDOG=60         -- seconds: a probe that never called back is reported SYSTEM-001 and the pass ends
local NULL=canon.null

local function is_dict(v) return type(v)=='table' and v~=NULL and not canon.is_array(v) and not canon.is_float(v) end
local function array_of(v) if type(v)~='table' or v==NULL or (not canon.is_array(v) and next(v)~=nil and #v==0) then return nil end;return v end
local function clamp_int(v,low,high) v=canon.number(v) or tonumber(v);if v and v%1==0 and v>=low and v<=high then return v end;return nil end
local function shallow(t) local out={};for k,v in pairs(t) do out[k]=v end;return setmetatable(out,getmetatable(t)) end
local function tail(list,n) local out=canon.array();for i=math.max(1,#list-n+1),#list do out[#out+1]=list[i] end;return out end

------------------------------------------------------------------------------------------------------
-- inventory (agent.inventory post-processing of inventory.lua's JSON)
------------------------------------------------------------------------------------------------------
function M.normalise_inventory(data)
  if not is_dict(data) then error('invalid inventory') end
  for _,key in ipairs({'profiles','servers','native_candidates','wan_interfaces'}) do
    local value=data[key]
    if value==nil or value==NULL or (type(value)=='table' and next(value)==nil) then value=canon.array() end
    if not array_of(value) then error('invalid inventory array') end
    data[key]=canon.array(value)
  end
  local profiles=canon.array()
  for _,p in ipairs(data.profiles) do
    if not is_dict(p) then error('invalid profile row') end
    if probe.safe(p.id) and probe.safe(p.section) then
      local name=p.name;if name==nil or name==NULL then name=p.id end
      p.name=string.sub(tostring(name),1,64)
      if p.interface~=nil and p.interface~=NULL and not probe.safe(p.interface) then p.interface=NULL end
      if #profiles<400 then profiles[#profiles+1]=p end
    end
  end
  data.profiles=profiles
  if not is_dict(data.settings) then data.settings=canon.object() end
  return data
end

-- monitoring_profiles: enabled catalogue rows plus the two anchored tunnels the plan follows.
function M.monitoring_profiles(data)
  local selected,disabled={},{}
  for _,s in ipairs(data.servers) do
    if s.enabled==true then selected[s.profile]=s elseif s.enabled==false then disabled[s.profile]=true end
  end
  local settings=data.settings
  local anchors={}
  for _,side in ipairs({'source','target'}) do
    local a=settings['plan_'..side..'_tunnel'];if type(a)=='string' then anchors[a]=true end
  end
  local observed=canon.array()
  if #data.servers==0 then
    for _,p in ipairs(data.profiles) do observed[#observed+1]=p end
  else
    for _,p in ipairs(data.profiles) do
      local follow=type(p.vendor_tunnel_id)=='string' and anchors[p.vendor_tunnel_id] and not disabled[p.id]
      if selected[p.id] or follow then observed[#observed+1]=p end
    end
  end
  return observed,selected
end

-- reliability.failure_pair_context on one snapshot: roles from the configured anchors, never route health.
function M.failure_pair(data)
  local settings,rows=data.settings,data.profiles
  local bindings={}
  for _,p in ipairs(rows) do if type(p.vendor_tunnel_id)=='string' and p.interface and p.interface~=NULL then bindings[p.vendor_tunnel_id]=p end end
  local result,anchors={},{}
  for _,role in ipairs({'source','target'}) do
    local anchor=settings['plan_'..role..'_tunnel']
    if not anchor or anchor==NULL or anchor=='' then
      anchor=nil
      local matches={}
      for _,r in ipairs(rows) do if r.id==settings['plan_'..role] then matches[#matches+1]=r end end
      if #matches==1 and type(matches[1].vendor_tunnel_id)=='string' then anchor=matches[1].vendor_tunnel_id end
    end
    local row=anchor and bindings[anchor]
    if not row or not M.PROFILE_PATTERN(row.id) then return canon.object() end
    result[role]=row.id;anchors[#anchors+1]=anchor
  end
  if anchors[1]==anchors[2] or result.source==result.target then return canon.object() end
  return canon.object(result)
end

function M.retention_days(settings)
  local raw=settings.history_days
  if type(raw)=='string' and string.find(raw,'^[1-7]$') then return tonumber(raw) end
  return clamp_int(raw,1,7) or 7
end
function M.observation_valid_for(settings)
  local v=clamp_int(settings.interval,10,300)
  if not v then return 90 end
  return math.max(30,math.min(900,v*3))
end
function M.probe_level(settings) return policy.level(settings) end

------------------------------------------------------------------------------------------------------
-- the daemon state
------------------------------------------------------------------------------------------------------
local Monitor={};Monitor.__index=Monitor

function M.new(runner,options)
  options=options or {}
  local self=setmetatable({},Monitor)
  self.runner=runner
  self.runtime=options.runtime or runner.RUNTIME or '/var/run/homensai-vpn'
  self.persist=options.persist or runner.PERSIST or '/etc/homensai-vpn'
  self.version=options.version or M.VERSION
  self.events=canon.array();self.samples=canon.array()
  self.status=nil
  self.published_at=nil
  self.previous_codes=nil
  self.last_save=runner.clock()
  self.settings={interval=30}
  self.critical=false
  local acc,storage_error=accounting.restore(runner,self.persist)
  self.accounting=acc;self.storage_error=storage_error
  self.env=page.env(runner,self.runtime,self.persist)
  local function read_json(path,default)
    local text=runner.read_file(path)
    if text==nil then return default end
    return canon.decode(text)
  end
  self.io={read_json=read_json,write_json=function(path,value) runner.write_atomic(path,canon.encode(value)) end,
    write_ram=function(path,value) (runner.write_ram or runner.write_atomic)(path,canon.encode(value)) end,
    unsafe=function(path,limit) local size=runner.file_size(path);return size~=nil and size>limit end}
  self.booster=policy.Booster(self.runtime,self.persist,{read_json=read_json,
    write_json=function(path,value)
      if string.sub(path,1,#self.runtime)==self.runtime then self.io.write_ram(path,value) else self.io.write_json(path,value) end
    end})
  self.diagnosing=accounting.stats.diagnostic(runner,runner.wall())
  self.ping_history=self:load_ping_history(self.diagnosing)
  self.ping=probe.PingSampler(runner,function(logical) return probe.route_binding(runner,logical) end,
    function() return runner.exists(self.runtime..'/speed-pause.json') end)
  self.bridge=page.Bridge(runner,self.runtime)
  self.vendor=vendor.Observer(options.uuid)
  self.setup_deps={runner=runner,runtime=self.runtime,persist=self.persist,now=runner.wall,
    cursor=options.cursor or function() return require('uci').cursor() end}
  self.rpc=rpc.new({version=self.version,now=function() return runner.wall() end,
    status=function() return self.status end,
    native_status=function() return self:read_json(self.runtime..'/native-status.json',canon.object({state='SERVICE-STOPPED'})) end,
    native_history=function() return page.native_history(self.env,M.retention_days(self.settings),runner.wall()) end,
    inventory=function() return self:inventory() end,
    extras=function(status) self:page_fields(status) end,
    live_extras=function(result,native,clean) self:live_fields(result,native,clean) end,
    live_manual=function(native) local _,value=page.manual_switch(self.env,native,false);return value end,
    speed_pause=function() return self:speed_pause() end,
    polled=function() self.bridge:poll() end,
    setup=function(method,arguments)
      local reply=require('setup').save(self.setup_deps,method,arguments)
      if reply==require('setup').FALLBACK then return rpc.FALLBACK end
      return reply
    end,
    pair_manual=function(arguments)
      local manual=require('manual_request')
      local reply=manual.request(self:manual_deps(),arguments)
      if reply==manual.FALLBACK then return rpc.FALLBACK end
      return reply
    end},runner)
  return self
end

-- manual_request.lua's view of the router (plan item 4): RAM/flash files, the config file, the control lock
function Monitor:manual_deps()
  local runner,env=self.runner,self.env
  local cursor_fn=self.setup_deps.cursor
  return {read=runner.read_file,write=runner.write_atomic,now=runner.wall,runtime=self.runtime,persist=self.persist,
    config_text=function() return runner.config_text and runner.config_text() or nil end,
    uci_get=function(option) local c=cursor_fn();return c:get('homensai_vpn','main',option) end,
    status=function() return self.status end,
    read_state=function() return page.read_state(env) end,
    current_revision=function() return page.current_revision(env) end,
    try_lock=function(fn) return runner.try_lock(self.runtime,fn) end}
end

function Monitor:read_json(path,default)
  local ok,value=pcall(function()
    local text=self.runner.read_file(path)
    if text==nil then return nil end
    return canon.decode(text)
  end)
  if ok and value~=nil then return value end
  return default
end

function Monitor:inventory()
  local text,err=self.runner.command('inventory')
  if not text then error(err or 'inventory unavailable') end
  return M.normalise_inventory(canon.plain(canon.decode(text)))
end

-- Work mode: an empty in-memory history, never filled nor saved (the flash copy stays intact).
function Monitor:load_ping_history(diagnosing)
  if not diagnosing then return responses.new() end
  return responses.load(self.io,self.persist..'/'..responses.NAME)
end

-- agent.checkpoint(accounting, ..., ping_response): the accounting always, the ping history in Diagnostics.
function Monitor:checkpoint()
  accounting.checkpoint(self.runner,self.persist,self.accounting)
  if self.diagnosing and self.ping_history then
    local ok=pcall(function() self.ping_history:save(self.io,self.persist..'/'..responses.NAME,self.runner.wall()) end)
    if not ok and self.ping_history.notice~=responses.PREFIX..'-UNAVAILABLE' then self.ping_history.notice=responses.PREFIX..'-WRITE-FAILED' end
  end
end

-- sample_wan_counters: WAN firewall-zone interfaces are explicit sources, not guessed default routes.
function Monitor:sample_wan(data,now,max_gap)
  local runner=self.runner
  local links,seen,devices={},{},canon.array()
  for _,logical in ipairs(data.wan_interfaces) do
    if type(logical)=='string' and probe.safe(logical) then
      local ok=pcall(function()
        local text,err=runner.command('iface_status',logical)
        if not text then error(err) end
        local interface=canon.plain(canon.decode(text))
        links[#links+1]=type(interface.up)=='boolean' and interface.up or 'unknown'
        local proto=interface.proto
        if not interface.up or proto=='ovpnclient' or proto=='wgclient' or proto=='openvpn' or proto=='wireguard' then return end
        local device=interface.l3_device or ''
        if not probe.safe(device,15) or seen[device] then return end
        seen[device]=true
        if self.accounting.wan==nil then self.accounting.wan=accounting.new() end
        local ifindex=tonumber(runner.sysfs(device,'ifindex'));local rx=tonumber(runner.sysfs(device,'statistics/rx_bytes'));local tx=tonumber(runner.sysfs(device,'statistics/tx_bytes'))
        if not ifindex or not rx or not tx then error('unreadable counters') end
        self.accounting.wan:sample(device,ifindex,rx,tx,now,max_gap)
        devices[#devices+1]=canon.object({device=device})
      end)
      if not ok then
        links[#links+1]='unknown'
        if self.accounting.wan then self.accounting.wan.gaps=self.accounting.wan.gaps+1;self.accounting.wan:note_gap(now,now) end
      end
    end
  end
  local any_up,all_down=false,#links>0
  for _,v in ipairs(links) do if v==true then any_up=true end;if v~=false then all_down=false end end
  data.uplink_observation=canon.object({time=now,state=all_down and 'DOWN' or (any_up and 'LINK-UP' or 'UNKNOWN'),
    scope='configured WAN-zone interface link state; not Internet proof'})
  return devices
end

------------------------------------------------------------------------------------------------------
-- one pass, asynchronous
------------------------------------------------------------------------------------------------------
-- start_pass(done): begins a pass; done(status) runs once when it is published (at once with synchronous fakes).
function Monitor:start_pass(done)
  done=done or function() end
  if self.passing then return false end
  self.passing=true
  local runner=self.runner
  local now_diagnosing=accounting.stats.diagnostic(runner,runner.wall())
  if now_diagnosing~=self.diagnosing then
    if self.diagnosing then pcall(function() self:checkpoint();self.last_save=runner.clock() end) end
    self.diagnosing=now_diagnosing
    self.ping_history=self:load_ping_history(now_diagnosing)
  end
  self.pass_started=runner.clock()
  local finished=false
  local watchdog
  local function finish(ctx,err)
    if finished then return end;finished=true
    if watchdog then watchdog.cancel() end
    if ctx and not err then
      local ok,ferr=pcall(function() self:finish_pass(ctx) end)
      if not ok then err=ferr end
    end
    if err then self:publish_failure(err) end
    self.pass_seconds=runner.clock()-self.pass_started
    self.passing=false
    done(self.status)
  end
  local ok,err=pcall(function()
    local data=self:inventory()
    local settings=data.settings
    self.settings=settings
    local now=runner.wall()
    self.accounting:apply_detail_retention(M.retention_days(settings),now)
    local observed,selected=M.monitoring_profiles(data)
    local bound=probe.probe_profiles(observed,settings)
    local ctx={data=data,settings=settings,observed=observed,selected=selected,bound=bound,results={}}
    local next_index,running,completed=1,0,0
    local function launch()
      while running<M.PROBE_WORKERS and next_index<=#bound do
        local index=next_index;next_index=next_index+1;running=running+1
        local okp=pcall(probe.probe,runner,bound[index],function(result)
          if ctx.results[index] then return end
          ctx.results[index]=result;running=running-1;completed=completed+1
          if completed==#bound then finish(ctx) else launch() end
        end)
        if not okp and not ctx.results[index] then
          ctx.results[index]={id=bound[index].id,time=runner.wall(),code='SYSTEM-001'};running=running-1;completed=completed+1
        end
      end
      if completed==#bound then finish(ctx) end
    end
    if runner.after then
      watchdog=runner.after(M.PASS_WATCHDOG*1000,function()
        local pending={}
        for index,p in ipairs(bound) do
          if not ctx.results[index] then pending[#pending+1]=tostring(p.id);ctx.results[index]={id=p.id,time=runner.wall(),code='SYSTEM-001'} end
        end
        local live=runner.live_count and runner.live_count() or -1
        if runner.log then runner.log('pass watchdog: probes did not finish in '..M.PASS_WATCHDOG..' s: '..table.concat(pending,',')..'; armed loop objects '..live) end
        finish(ctx)
      end)
    end
    launch()
  end)
  if not ok then finish(nil,err) end
  return true
end

function Monitor:publish_failure(err)
  local runner=self.runner
  if runner.log then runner.log('pass failed: '..tostring(err)) end
  local stub=canon.object({version=self.version,mode='monitor',error='SYSTEM-001',time=runner.wall()})
  pcall(function() runner.write_atomic(self.runtime..'/status.json',canon.encode(stub)) end)
  self.status=stub
  self.settings={interval=30}
end

function Monitor:finish_pass(ctx)
  local runner=self.runner
  local data,settings,observed,selected=ctx.data,ctx.settings,ctx.observed,ctx.selected
  local raw={}
  for index in ipairs(ctx.bound) do raw[#raw+1]=ctx.results[index] end
  -- Read metadata again after the network observations (agent.monitor_loop): never attach a former configured
  -- profile's success to its replacement on a tunnel.
  local after=self:inventory()
  local observation,measured=self.vendor:observe(data,after,raw,runner.wall())
  local mapped={}
  for _,p in ipairs(measured) do mapped[p.id]=p end
  local rows=canon.array()
  for _,p in ipairs(observed) do
    local row=shallow(p)
    local result=mapped[p.id]
    if result then for k,v in pairs(result) do row[k]=v end
    else
      local inactive=not p.interface or p.interface==NULL or p.administrative_state=='disabled'
      row.code=inactive and 'PROFILE-INACTIVE' or 'CHECK-LIMIT'
    end
    if row.code==nil then row.code=NULL end  -- Python writes "code": null for a healthy channel
    local custom=selected[p.id] or {}
    row.router_name=p.name
    row.name=(custom.name and custom.name~=NULL and custom.name~='') and custom.name or p.name
    row.channel=(custom.channel and custom.channel~=NULL and custom.channel~='') and custom.channel or 'default'
    row.priority=custom.priority==nil and 100 or custom.priority
    rows[#rows+1]=row
  end
  local interval=clamp_int(settings.interval,1,3600) or 10
  local now=runner.wall()
  local wan_devices=canon.array()
  if now>=M.CLOCK_FLOOR then
    wan_devices=self:sample_wan(data,now,interval*3)
    accounting.sample_counters(runner,measured,self.accounting,now,interval*3)
    self.accounting:track_activity(rows,now,interval*3)
  else self.storage_error='CLOCK-001' end
  local pair=M.failure_pair(data)
  local metric=policy.response_metric(settings)
  local target=policy.RESPONSE_METRICS[metric]
  self.ping:configure(self.booster:measure(settings),target or nil)
  local okp=pcall(function() self.ping:apply(rows,pair,runner.wall()) end)
  if not okp then for _,row in ipairs(rows) do row.ping=probe.ping_public(row,'unavailable','PING-UNAVAILABLE') end end
  for _,row in ipairs(rows) do
    row.role=row.id==pair.source and 'source' or (row.id==pair.target and 'target' or 'unknown')
  end
  local native=self:read_json(self.runtime..'/native-status.json',canon.object())
  now=runner.wall()
  for _,row in ipairs(measured) do
    self.accounting:observe(row)
    local sample=canon.object()
    for _,k in ipairs({'id','time','code','rtt_ms','https_success','dns_ok','interface','vendor_tunnel_id','vendor_generation'}) do
      sample[k]=row[k]==nil and NULL or row[k]
    end
    self.samples[#self.samples+1]=sample
  end
  local kept=self.diagnosing and 86400*M.retention_days(settings) or accounting.WORK_SAMPLE_SECONDS
  local samples=canon.array()
  for _,s in ipairs(self.samples) do
    local t=canon.number(s.time) or 0
    if t>=now-kept then samples[#samples+1]=s end
  end
  self.samples=tail(samples,10000)
  -- events: a changed verdict per profile against the previous published pass (status.json after a restart)
  if self.previous_codes==nil then
    self.previous_codes={}
    local previous=self:read_json(self.runtime..'/status.json',canon.object())
    for _,p in ipairs(type(previous.profiles)=='table' and previous.profiles or {}) do
      if is_dict(p) and p.id then
        local code=p.code;if code==NULL then code=nil end
        self.previous_codes[p.id]=code or false
      end
    end
  end
  local current={}
  for _,row in ipairs(rows) do
    local code=row.code;if code==NULL then code=nil end
    current[row.id]=code or false
    if self.previous_codes[row.id]==nil or self.previous_codes[row.id]~=(code or false) then
      local event=canon.object({time=now,profile=row.id,role=row.role,code=code or 'OK',
        measurement_time=row.time==nil and NULL or row.time})
      for _,k in ipairs({'https_success','dns_ok','probe_checks'}) do if row[k]~=nil then event[k]=row[k] end end
      self.events[#self.events+1]=event
    end
  end
  self.previous_codes=current
  if self.storage_error then self.events[#self.events+1]=canon.object({time=now,code=self.storage_error}) end
  local status=canon.object({version=self.version,mode='monitor',time=now,profiles=rows,
    accounting=self.accounting:public_export(now),samples=tail(self.samples,1000),events=tail(self.events,300),
    capabilities=canon.object({native_apply=false,reason='GL.iNet worker/firewall transaction is not device-validated'}),
    scope='IPv4 router-originated HTTPS/DNS, not LAN/IPv6 validation',
    storage_error=self.storage_error==nil and NULL or self.storage_error})
  local valid_for=M.observation_valid_for(settings)
  status.observation_valid_for=valid_for
  for _,row in ipairs(rows) do row.observation_valid_for=valid_for end
  status.uplink_observation=data.uplink_observation or canon.object({state='UNKNOWN'})
  status.vendor_observation=observation
  status.package=runner.package_version and runner.package_version() or NULL
  if status.package==nil then status.package=NULL end
  status.native_failover=native
  if native.state==nil then status.native_failover=canon.object({state='SERVICE-STOPPED'}) end
  local okb=pcall(function() return self.booster:observe(settings,measured,pair,status.native_failover.state,runner.wall()) end)
  if okb then
    status.probe_policy=self.booster:public(settings,runner.wall())
    status.response_metric=metric
  else status.probe_policy=canon.object({code='PROBE-POLICY-UNAVAILABLE'}) end
  local stats=accounting.stats.public(runner,now)
  stats.storage=accounting.stats.storage(runner,self.runtime,self.persist)
  status.stats_mode=stats
  -- Work mode keeps no response history (stats_mode.py); Diagnostics fills the ping history every pass.
  if metric=='websites' then status.website_response_history=responses.website_unavailable()
  else
    if self.diagnosing then pcall(function() self.ping_history:observe(status,settings,runner.wall(),M.retention_days(settings)) end) end
    local okh,public=pcall(function() return self.ping_history:public(runner.wall()) end)
    status.website_response_history=okh and public or responses.website_unavailable()
  end
  status.native_history=page.native_history(self.env,M.retention_days(settings),runner.wall())
  status.stats_reset=self:read_json(self.runtime..'/stats-reset-result.json',NULL)
  status.auto_control=page.auto_control(self.env,runner.wall())
  status.lua_backend=self:backend_record()
  status.wan_devices=wan_devices
  runner.write_atomic(self.runtime..'/status.json',canon.encode(status))
  self.status=status;self.published_at=runner.clock()
  local since_save=runner.clock()-self.last_save
  local due
  if self.diagnosing then due=since_save>=(clamp_int(settings.checkpoint,60,86400) or 900)
  else due=since_save>=accounting.WORK_CHECKPOINT_SECONDS end
  if due then
    local saved=pcall(function() self:checkpoint() end)
    if saved then self.storage_error=nil;self.last_save=runner.clock() else self.storage_error='STORAGE-001' end
  end
  self.events=tail(self.events,1000)
end

-- status.lua_backend: what runs in Lua, the detected router capabilities and the temporary bridges.
function Monitor:backend_record()
  local runner=self.runner
  local caps=runner.capabilities and runner.capabilities() or {}
  local record=canon.object()
  for k,v in pairs(caps) do record[k]=v end
  record.monitor='lua';record.version=self.version
  record.native=canon.array({'status','events','history','auto_live','inventory','setup_probe','setup_response','setup_stats'})
  record.python=canon.array({'pair_manual','native_start','native_stop','fault_start','fault_cancel','other setup_*','statistics','speed','telegram'})
  record.bridges=canon.array({'manual_switch_control','channel_path','speed_pause','speed_tests','scan'})
  record.not_ported=canon.array({'failure_diagnosis','failover_plan','candidate_hierarchy','suspicion','website/latency/compare histories',
    'reliability','system_readiness','speed','telegram'})
  return record
end

-- One synchronous pass (tests, one-shot tools): starts the pass and drains a fake loop when there is one.
function Monitor:pass()
  self:start_pass()
  if self.runner.drain then self.runner.drain() end
  return self.status
end

------------------------------------------------------------------------------------------------------
-- page fields added at reply time (agent.status_reply)
------------------------------------------------------------------------------------------------------
function Monitor:speed_pause()
  if not self.runner.exists(self.runtime..'/speed-pause.json') then return canon.object({active=false}) end
  local bridged=self.bridge:current(self.runner.wall())
  if bridged and is_dict(bridged.speed_pause) then return bridged.speed_pause end
  return canon.object({active=false,code='SPEED-PAUSE-UNVERIFIED'})
end

function Monitor:page_fields(status)
  local runner=self.runner
  local now=runner.wall()
  local env=self.env
  local bridged=self.bridge:current(now)
  status.speed_pause=self:speed_pause()
  if bridged and is_dict(bridged.scan) then status.scan=bridged.scan end
  status.stats_reset=self:read_json(self.runtime..'/stats-reset-result.json',NULL)
  status.switch_timing=page.switch_timing(env)
  status.auto_control=page.auto_control(env,now)
  local control=bridged and is_dict(bridged.manual_switch_control) and bridged.manual_switch_control or nil
  local available=control and control.available==true or false
  local use_pair,manual=page.manual_switch(env,status.native_failover,available)
  status.manual_switch=manual
  if control then status.manual_switch_control=control
  else
    status.manual_switch_control=use_pair and page.controls_fallback(now) or page.legacy_controls_fallback(now)
  end
  status.channel_path=(bridged and is_dict(bridged.channel_path)) and bridged.channel_path or page.channel_path_fallback(status.native_failover,now)
  if bridged and is_dict(bridged.speed_tests) then status.speed_tests=bridged.speed_tests
  else status.speed_tests=canon.object({code='SPEED-STATUS-UNAVAILABLE',results=canon.array()}) end
end

-- auto_live: auto_control {requested,pair_phase} and the cached channel_path projection, as auto_live.snapshot.
function Monitor:live_fields(result,native,clean)
  local env=self.env
  local now=self.runner.wall()
  local required=clean.mode=='continuous-pair' or clean.proof_scope=='router-probed-ipv4'
  local ok=pcall(function()
    -- the pair state through the cached reader (no hashing of an unchanged file); an invalid state is not valid
    local present=self.runner.exists(self.persist..'/pair-auto-state.json')
    local okv,owned=pcall(page.read_state,env)
    local valid=okv and is_dict(owned) and next(owned)~=nil
    if not valid then owned=canon.object() end
    required=required or (present and clean.proof_scope~='external-lan')
    local request=self:read_json(self.runtime..'/pair-auto-control.json',canon.object())
    local revision=self:read_json(self.runtime..'/auto-control-revision.json',canon.object())
    local stopped=self:read_json(self.persist..'/native-stop.json',canon.object())
    local mode=request.mode;if mode==nil then mode='off' end
    if (mode~='on' and mode~='off') or (mode=='on' and (request.revision~=revision.revision or not valid or stopped.control_revision_failed==true)) then mode='unknown' end
    local phase=valid and owned.phase or nil
    local PH={STARTING=true,RUNNING=true,STOPPING=true,HELD=true,STOPPED=true,FAILED=true}
    if not PH[phase] then phase=nil end
    if mode=='on' and (request.id~=owned.id or request.revision~=owned.revision) then phase='STARTING' end
    if mode~='on' and (phase=='STARTING' or phase=='RUNNING' or phase=='STOPPING') then phase='STOPPING' end
    result.auto_control=canon.object({requested=mode,pair_phase=phase==nil and NULL or phase})
  end)
  if not ok then
    required=required or clean.proof_scope~='external-lan'
    result.auto_control=canon.object({requested='unknown',pair_phase=NULL})
  end
  if required then
    local path=page.cached_projection(native.channel_path,now)
    local s=clean.state
    if s=='BLOCKED' or s=='ARMED' or s=='APPLYING' or s=='WAIT-CLIENT' or s=='RESTORING' or (type(native.blockers)=='table' and native.blockers~=NULL and #native.blockers>0) then
      path=page.from_kernel(nil,clean.source,clean.target,now)
    end
    result.channel_path=path
    clean.mode='continuous-pair'
  end
end

-- Seconds until the next pass: the probe policy interval (boost/dense shorter), never overlapping a pass.
function Monitor:next_delay()
  local ok,interval=pcall(function() return self.booster:interval(self.settings,self.runner.wall()) end)
  if not ok or not interval then interval=clamp_int(self.settings.interval,1,3600) or 30 end
  return math.max(1,interval-(self.pass_seconds or 0))
end

-- Final save (work mode: the only save besides the daily one). Called from the ubus 'shutdown' hook/stop path.
function Monitor:shutdown()
  pcall(function() self:checkpoint() end)
  self.ping:close()
end

------------------------------------------------------------------------------------------------------
-- uloop + ubus wiring (router only; the PC tests never call run())
------------------------------------------------------------------------------------------------------
-- uloop has no signal API in Lua 5.1 on OpenWrt 21.02: procd's SIGTERM ends the process without a final
-- checkpoint. The init script therefore calls `ubus call homensai-vpn-lua shutdown` (root only, not in the
-- rpcd ACL) before procd stops the instance; shutdown saves and keeps serving until procd's SIGTERM.
function M.run(runner,options)
  local uloop=require('uloop');local ubus=require('ubus')
  if runner.setup_timezone then runner.setup_timezone() end
  uloop.init()
  if runner.attach_loop then runner.attach_loop(uloop) end
  local monitor=M.new(runner,options)
  local conn=ubus.connect()
  if not conn then error('ubus connect failed') end
  local object=monitor.rpc.ubus_object(conn,ubus)
  object[rpc.OBJECT].shutdown={function(req,msg) monitor:shutdown();conn:reply(req,{saved=true}) end,{}}
  object[rpc.OBJECT].checkpoint={function(req,msg)
    local ok=pcall(function() monitor:checkpoint() end)
    monitor.last_save=runner.clock();conn:reply(req,{saved=ok}) end,{}}
  conn:add(object)
  local ready=monitor.runtime..'/'..(runner.READY or 'lua-monitor.ready')
  pcall(runner.write_ram or runner.write_atomic,ready,canon.encode(canon.object({version=monitor.version,started=runner.wall()})))
  local timer
  local config_stamp=runner.config_mtime()
  local function tick()
    local started=monitor:start_pass(function()
      config_stamp=runner.config_mtime()
      timer:set(math.floor(monitor:next_delay()*1000))
    end)
    if not started then timer:set(1000) end
  end
  timer=uloop.timer(tick)
  timer:set(100)
  -- A changed configuration or a page scan request starts the next pass now (agent.py's 1 s wait loop).
  -- scan_control is not ported: a new scan.request (its file key changed) only starts one pass now.
  local watcher
  local scan_key=runner.file_key and runner.file_key(monitor.runtime..'/scan.request') or nil
  watcher=uloop.timer(function()
    -- Diagnostics: `touch /var/run/homensai-vpn/lua-monitor-profile.request` (profiler.lua)
    pcall(function() require('profiler').tick(monitor.runtime,'lua-monitor-profile',60) end)
    if not monitor.passing then
      local stamp=runner.config_mtime()
      local key=runner.file_key and runner.file_key(monitor.runtime..'/scan.request') or nil
      if stamp~=config_stamp or (key~=nil and key~=scan_key) then config_stamp=stamp;scan_key=key;timer:set(1) end
    end
    watcher:set(1000)
  end)
  watcher:set(1000)
  uloop.run()
  pcall(os.remove,ready)
  conn:close()
end

------------------------------------------------------------------------------------------------------
-- Read-only comparison for the router test (docs/architecture/LUA-MONITOR-ITEM2-2026-10-31.ru.md):
--   lua /usr/lib/homensai-vpn/lua/monitor.lua compare
-- Two Lua passes 5 s apart (the first opens the vendor epochs, the second settles them and sends the pings),
-- then one JSON line per profile: the Lua verdict next to the live verdict of the running (Python) monitor.
-- Every file this run writes stays in /tmp/homensai-lua-compare; the live status.json is only read; no ubus
-- object is registered; nothing of the running service changes. The exit address is not printed.
------------------------------------------------------------------------------------------------------
M.COMPARE_DIR='/tmp/homensai-lua-compare'
function M.compare_rows(lua_status,live_status,ping_cache)
  local function index(status)
    local out={}
    for _,p in ipairs(type(status)=='table' and type(status.profiles)=='table' and status.profiles or {}) do
      if type(p)=='table' and type(p.id)=='string' then out[p.id]=p end
    end
    return out
  end
  local live=index(live_status)
  local rows={}
  for _,p in ipairs(type(lua_status.profiles)=='table' and lua_status.profiles or {}) do
    local function side(row)
      if not row then return NULL end
      local ping=type(row.ping)=='table' and row.ping or {}
      return canon.object({code=row.code==nil and NULL or row.code,https_success=row.https_success==nil and NULL or row.https_success,
        dns_ok=row.dns_ok==nil and NULL or row.dns_ok,rtt_ms=row.rtt_ms==nil and NULL or row.rtt_ms,
        exit_ip_seen=type(row.exit_ip)=='string',exit_country=row.exit_country==nil and NULL or row.exit_country,
        vendor_state=row.vendor_state==nil and NULL or row.vendor_state,
        ping_state=ping.state==nil and NULL or ping.state,ping_ms=ping.rtt_ms==nil and NULL or ping.rtt_ms,
        checks=row.probe_checks==nil and NULL or row.probe_checks})
    end
    local cached=NULL
    for _,value in pairs(ping_cache or {}) do
      if type(value)=='table' and value.vendor_tunnel_id==p.vendor_tunnel_id then cached=canon.object({state=value.state,rtt_ms=value.rtt_ms==nil and NULL or value.rtt_ms}) end
    end
    rows[#rows+1]=canon.object({id=p.id,interface=p.interface==nil and NULL or p.interface,lua=side(p),lua_ping_after=cached,python=side(live[p.id])})
  end
  return rows
end

function M.compare(runner)
  local uloop=require('uloop')
  if runner.setup_timezone then runner.setup_timezone() end
  uloop.init()
  runner.attach_loop(uloop)
  local live_text=runner.read_file(runner.RUNTIME..'/status.json')
  local ok_live,live=pcall(canon.decode,live_text or '{}')
  if not ok_live then live=canon.object() end
  os.execute('mkdir -p '..M.COMPARE_DIR..' && chmod 700 '..M.COMPARE_DIR)
  runner.configure({RUNTIME=M.COMPARE_DIR,PERSIST=M.COMPARE_DIR})
  local m=M.new(runner,{runtime=M.COMPARE_DIR,persist=M.COMPARE_DIR})
  local durations={}
  local function rss()
    local f=io.open('/proc/self/status','r');if not f then return NULL end
    local text=f:read('*a');f:close()
    return tonumber(string.match(text,'VmRSS:%s*(%d+)')) or NULL
  end
  local function report()
    local status=m.status or canon.object()
    for _,row in ipairs(M.compare_rows(status,live,m.ping.cache)) do print(canon.encode(row)) end
    print(canon.encode(canon.object({summary=true,pass_seconds=canon.array(durations),vm_rss_kb=rss(),error=status.error or NULL,
      lua_backend=status.lua_backend or NULL,python_status_time=live.time or NULL,python_version=live.version or NULL})))
    uloop.cancel()
  end
  local t0=runner.hires()
  m:start_pass(function()
    durations[1]=math.floor((runner.hires()-t0)*1000+0.5)/1000
    uloop.timer(function()
      local t1=runner.hires()
      m:start_pass(function()
        durations[2]=math.floor((runner.hires()-t1)*1000+0.5)/1000
        uloop.timer(report,2500)
      end)
    end,5000)
  end)
  uloop.run()
end

if arg and arg[0] and string.find(arg[0],'monitor%.lua$') and arg[1]=='daemon' then M.run(require('monitor_io')) end
if arg and arg[0] and string.find(arg[0],'monitor%.lua$') and arg[1]=='compare' then M.compare(require('monitor_io')) end

return M
