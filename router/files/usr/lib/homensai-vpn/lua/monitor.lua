-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- monitor.lua: hv-monitor, the Lua port of agent.monitor_loop (owner plan items 2 and 3, 2.0.0-lua-alpha4).
-- One pass = inventory -> route-bound probes (asynchronous: curl children, device-bound UDP/ICMP sockets, never
-- blocking uloop) -> counters/activity -> events -> probe policy -> status.json -> checkpoint when due.
-- The published status stays in memory and is answered by rpc.lua without re-reading the file.
-- Runner (monitor_io.lua or a test fake) is the only way out of the process.
-- Not ported yet (fields absent or reduced, see docs/architecture/LUA-MONITOR-ITEM2-2026-10-31.ru.md):
-- failure_diagnosis/failover_plan/candidate_hierarchy, suspicion watcher, website/latency/
-- compare histories, reliability, scan_control. server_endpoint: server_endpoint.lua (cached per tunnel epoch). system_readiness: readiness.lua (refreshed every READINESS_REFRESH s).
-- Speed test and Telegram reports (plan item 7): speed.lua, speed_pause.lua, telegram.lua (see their headers).
if arg and arg[0] and string.find(arg[0],'monitor%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local canon=require('canon')
local probe=require('probe')
local accounting=require('accounting')
local reliability=require('reliability')
local rpc=require('rpc')
local policy=require('probe_policy')
local responses=require('response_history')
local latency=require('latency_history')
local retention=require('retention')
local resets=require('stats_reset')
local page=require('monitor_status')
local vendor=require('vendor')
local fast=require('fast_detect')
local endpoints=require('server_endpoint')

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

-- The fields of one probe result that accounting/reliability read, with Python's types: the probe time is
-- time.time() and rtt_ms is round(x, 1), both floats in Python, plain numbers in probe.lua.
function M.typed_result(row)
  local view={}
  for _,k in ipairs({'id','code','dns_ok','https_success','administrative_state'}) do view[k]=row[k] end
  view.time=reliability.pyf(row.time);view.rtt_ms=reliability.pyf(row.rtt_ms)
  return view
end

-- retention_settings.days(settings): the owner's period, by time or by size (retention.lua), 1..30 days
function M.retention_days(settings) return retention.days(settings) end
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
  self.readiness_sys=options.readiness_sys
  self.readiness_memo={}
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
  -- server_endpoint.lua: the peer address of every probed channel (agent.probe), cached per tunnel epoch
  self.endpoints=endpoints.Observer(options.endpoint_fs or (runner.endpoint_fs and runner.endpoint_fs()) or nil)
  -- Lua plan item 5: the 1 s pulse of the two Auto channels (off unless option lua_fast_detect '1')
  self.fast=fast.Pulse(runner,function() return runner.exists(self.runtime..'/speed-pause.json') end)
  self.fast_on=false;self.fast_key=nil
  -- plan item 7: speed test (speed.lua, the quiet window speed_pause.lua) and Telegram reports (telegram.lua)
  self.speed_deps=options.speed_deps or require('speed').router({runtime=self.runtime,persist=self.persist,io=runner,nonblocking=true,
    inventory=function() return self:inventory() end,retention_days=function() return M.retention_days(self.settings) end,
    overrides=options.speed_overrides})
  self.telegram_deps=options.telegram_deps or require('telegram').router({runtime=self.runtime,persist=self.persist,io=runner,
    lock=function(fn,directory) return runner.try_lock(directory,fn) end,overrides=options.telegram_overrides})
  self.telegram_run=options.telegram_run
  do
    local ok,saved,notice=pcall(require('telegram').load_state,self.telegram_deps)
    if ok then self.telegram_saved,self.telegram_notice=saved,notice else self.telegram_saved,self.telegram_notice=canon.object(),'TELEGRAM-STATE-CORRUPT' end
  end
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
    speed=function(method,arguments) return self:speed_rpc(method,arguments) end,
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
    end,
    control=function(method,arguments)
      local control=require('control_request')
      local deps=self:control_deps()
      local reply
      if method=='native_start' then reply=control.start(deps,arguments)
      elseif method=='native_stop' then reply=control.stop(deps,arguments)
      elseif method=='fault_cancel' then reply=control.fault_cancel(deps,arguments)
      elseif method=='fault_start' then reply=control.fault_start(deps,arguments)
      else return rpc.FALLBACK end
      if reply==control.FALLBACK then return rpc.FALLBACK end
      return reply
    end},runner)
  return self
end

-- control_request.lua's view of the router (Start/Stop/failure-test buttons, plan item 4)
function Monitor:control_deps()
  local runner,env=self.runner,self.env
  local platform_sys=nil
  local function psys()
    platform_sys=platform_sys or (runner.platform_sys and runner.platform_sys()) or error('platform view unavailable',0)
    return platform_sys
  end
  return {read=runner.read_file,write=runner.write_atomic,now=runner.wall,clock=runner.clock,runtime=self.runtime,persist=self.persist,
    exists=function(path) return (runner.present or runner.exists)(path) end,
    try_lock=function(fn) return runner.try_lock(self.runtime,fn) end,
    native_policy=function() return (runner.command('native_policy')) end,
    journal=function() return self:journal() end,
    auto_blocker=function() return require('platform').auto_blocker(psys(),self.persist) end,
    preparation=function(settings) return require('platform').preparation_snapshot(psys(),settings) end,
    read_state=function() return page.read_state(env) end,
    intent=function() return require('pair').intent(env) end,
    terminalize=function() return require('manual').terminalize_pending_locked(env,'CANCELLED','CONTROL-REVISION-STALE') end,
    nft=function(action)
      if not runner.command_rc then return 255,'' end
      return runner.command_rc(action=='list' and 'nft_fault_list' or 'nft_fault_delete')
    end}
end

-- native_switch.journal_read(): the checked journal (journal.lua), parsed again only when the file changed.
function Monitor:journal()
  local runner=self.runner
  local path=self.persist..'/native-transaction.json'
  local key=runner.file_key and runner.file_key(path) or nil
  local memo=self.journal_memo
  if key and memo and memo.key==key then
    if memo.err~=nil then error(memo.err,0) end
    return memo.value
  end
  local ok,value=pcall(require('journal').read,{fs={read=runner.read_file,unsafe=runner.unsafe},path=path})
  self.journal_memo={key=key,value=ok and value or nil,err=(not ok) and value or nil}
  if not ok then error(value,0) end
  return value
end

-- backend.order() for the display: the router policy (native_policy.lua) re-read only when one of its UCI
-- packages (or an uncommitted change of one) changed; order and hash cached per process bindings.
Monitor.POLICY_PACKAGES={'route_policy','firewall','homensai_vpn','mtkhnat','glipv6','network'}
function Monitor:policy_data()
  local runner=self.runner
  local parts={}
  for _,p in ipairs(Monitor.POLICY_PACKAGES) do
    parts[#parts+1]=tostring(runner.file_key and runner.file_key('/etc/config/'..p))
    parts[#parts+1]=tostring(runner.file_key and runner.file_key('/tmp/.uci/'..p))
  end
  local key=table.concat(parts,'|')
  local memo=self.policy_memo
  if not (runner.file_key and memo and memo.key==key) then
    local text,err=runner.command('native_policy')
    if not text then error(err or 'POLICY-READ-FAILED',0) end
    local value=canon.decode(text)
    local sections=is_dict(value) and value.sections or nil
    if type(sections)=='table' and not canon.is_array(sections) and next(sections)==nil then sections=canon.array() end
    if not canon.is_array(sections) then error('POLICY-READ-FAILED',0) end
    memo={key=key,sections=sections,settings=is_dict(value) and value.settings or nil,orders={}};self.policy_memo=memo
  end
  return memo
end
function Monitor:policy_order(bindings)
  local memo=self:policy_data()
  local bkey=bindings and canon.encode(bindings) or '-'
  local row=memo.orders[bkey]
  if not row then
    local identity=require('identity')
    row={identity.policy_order(memo.sections,bindings),identity.policy_hash(memo.sections,bindings)}
    memo.orders[bkey]=row
  end
  return row[1],row[2]
end

-- channel_path.public_status (channel_path.lua): no Python process, no kernel attestation of our own
function Monitor:channel_path(status,now)
  local env=self.env
  return require('channel_path').public_status({journal=function() return self:journal() end,
    state=function() return page.read_state(env) end,
    order=function(bindings) return self:policy_order(bindings) end},status,now)
end

-- A RAM/flash JSON file parsed again only when its file key changed (agent.read_json: default when missing,
-- raises on a damaged file). Callers never modify the value.
function Monitor:cached_json(path,default)
  local runner=self.runner
  local key=runner.file_key and runner.file_key(path) or nil
  self.json_memo=self.json_memo or {}
  if key==nil then
    self.json_memo[path]=nil
    local text=runner.read_file(path)
    if text==nil then return default end
    return canon.decode(text)
  end
  local memo=self.json_memo[path]
  if memo and memo.key==key then
    if memo.err~=nil then error(memo.err,0) end
    if memo.value==nil then return default end
    return memo.value
  end
  local ok,value=pcall(function()
    local text=runner.read_file(path)
    if text==nil then return nil end
    return canon.decode(text)
  end)
  self.json_memo[path]={key=key,value=ok and value or nil,err=(not ok) and value or nil}
  if not ok then error(value,0) end
  if value==nil then return default end
  return value
end

-- scan_control.public (page_controls.lua): scan.state parsed once per file version; a damaged file leaves the
-- field out, as the bridge did.
function Monitor:scan_status(now)
  return require('page_controls').scan_public(self:cached_json(self.runtime..'/scan.state',canon.object()),now)
end

-- manual_control.display_diagnostic: display-diagnostic.json younger than 15 s (shared with Python), else one
-- diagnostic of the Lua backend in this process (only the legacy non-pair path needs it), written back for 15 s.
Monitor.DISPLAY_DIAGNOSTIC_SECONDS=15
function Monitor:display_diagnostic(now)
  local path=self.runtime..'/display-diagnostic.json'
  local ok,row=pcall(function() return self:cached_json(path,canon.object()) end)
  if ok and is_dict(row) then
    local t=canon.number(row.time)
    if t and 0<=now-t and now-t<Monitor.DISPLAY_DIAGNOSTIC_SECONDS and canon.is_array(row.blockers)
       and (row.selection==nil or row.selection==NULL or is_dict(row.selection)) then
      local selection=row.selection;if selection==NULL then selection=nil end
      return row.blockers,selection
    end
  end
  local diagnose=self.diagnostic_override or function() return self:legacy_backend().diagnostic() end
  local dok,blockers,selection=pcall(diagnose)
  if not dok or not canon.is_array(blockers) then error(require('page_controls').UNAVAILABLE,0) end
  pcall(function()
    self.io.write_ram(path,canon.object({time=canon.float(now),blockers=blockers,selection=selection==nil and NULL or selection}))
  end)
  return blockers,selection
end

-- The Lua backend for the legacy display diagnostic, built on first use. Its commands run through the monitor's
-- file-captured exec (a pipe read would be cut short by the SIGCHLD of the monitor's own probe children).
function Monitor:legacy_backend()
  if self.backend_view then return self.backend_view end
  local runner=self.runner
  if not runner.exec then error('no command runner',0) end
  local sys=require('sys')
  local Refused=require('auto_control').Refused
  local view=setmetatable({},{__index=sys})
  function view.exec(argv,opts)
    if opts and opts.input then return sys.exec(argv,opts) end
    local rc,out=runner.exec(argv,opts and opts.timeout and {timeout=opts.timeout} or nil)
    out=out or ''
    if #out>((opts and opts.max) or 2*1024*1024) then error(setmetatable({code='NATIVE-SYSTEM-001',value_error=true},Refused),0) end
    return rc,out
  end
  function view.command(argv,opts)
    local rc,out=view.exec(argv,opts)
    if rc~=0 then error(setmetatable({code=opts and opts.code or 'COMMAND-FAILED',value_error=true},Refused),0) end
    return out
  end
  self.backend_view=require('backend').new(view)
  return self.backend_view
end

-- manual_switch_control (page_controls.lua): pair_manual.controls() or manual_control.control_status(), chosen
-- like agent.status_reply; returns control, manual_switch. A nil control: the Lua side could not answer.
function Monitor:manual_controls(status,now)
  local env=self.env
  local controls=require('page_controls')
  local native=status.native_failover
  local function native_file() return self:cached_json(self.runtime..'/native-status.json',canon.object()) end
  local function settings()
    local value=self:policy_data().settings
    if value==nil then error('KeyError',0) end
    return value
  end
  local common={now=now,runtime=self.runtime,persist=self.persist,native=native_file,settings=settings,
    current_revision=function() return page.current_revision(env) end,
    journal=function() return self:journal() end,
    read_json=function(path,default) return self:cached_json(path,default) end}
  local pair_deps=setmetatable({
    read_state=function() return page.read_state(env) end,
    intent=function() return require('pair').intent(env) end,
    validate_bindings=function(bindings) return require('identity').validate(bindings) end,
    order=function(bindings) return self:policy_order(bindings) end,
    status=function() return status end,
    queued=function() return require('manual').read(env) end,
    ledger=function() return self:cached_json(self.persist..'/pair-auto-budget.json',canon.object({events=canon.array()})) end,
    kernel=function(state,_,live) return require('channel_path').page_kernel(native_file(),state,live,now) end,
    fast=function() return require('manual_request').fast_switch_enabled(self.runner.config_text and self.runner.config_text() or nil) end,
  },{__index=common})
  local legacy_deps=setmetatable({diagnostic=function() return self:display_diagnostic(now) end},{__index=common})
  local manual=nil
  local function choose(available)
    local use_pair,public=page.manual_switch(env,native,available)
    manual=public
    return use_pair
  end
  local ok,control=pcall(controls.manual_switch_control,pair_deps,legacy_deps,choose)
  if not ok then
    if self.runner.log then self.runner.log('manual_switch_control in Lua: '..tostring(control)) end
    return nil,nil
  end
  return control,manual
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
-- The HTTPS-latency history (latency_history.lua) follows the same rule and is (re)loaded with it.
function Monitor:load_ping_history(diagnosing)
  if not diagnosing then self.latency=latency.new();return responses.new() end
  self.latency=latency.load(self.io,self.persist..'/'..latency.NAME)
  return responses.load(self.io,self.persist..'/'..responses.NAME)
end

-- agent.checkpoint(accounting, latency, ..., ping_response): the accounting always, the histories in Diagnostics.
function Monitor:checkpoint()
  accounting.checkpoint(self.runner,self.persist,self.accounting)
  if self.diagnosing and self.latency then
    local ok=pcall(function() self.latency:save(self.io,self.persist..'/'..latency.NAME,self.runner.wall()) end)
    if not ok and self.latency.notice~='LATENCY-HISTORY-UNAVAILABLE' then self.latency.notice='LATENCY-HISTORY-WRITE-FAILED' end
  end
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
-- the owner's statistics reset (stats_reset.lua; agent.monitor_loop applies it at the top of a pass)
------------------------------------------------------------------------------------------------------
-- Returns true when a request was applied (or refused with a coded result), false when none is queued or a lock
-- it needs is busy (the request stays queued for the next pass; the loop never waits for a lock).
function Monitor:stats_reset()
  local runner=self.runner
  local parts=resets.peek(runner,self.runtime)
  if not parts then
    if runner.exists(self.runtime..'/'..resets.REQUEST) then resets.pending(runner,self.runtime) end  -- malformed: drop it
    return false
  end
  local function work()
    local request=resets.pending(runner,self.runtime)
    if not request then return end
    -- Work mode holds empty histories: a reset works on the real flash copies and saves exactly those.
    local state=resets.histories(runner,self.persist,self.diagnosing and {latency=self.latency,ping=self.ping_history} or nil)
    local ctx={runner=runner,persist=self.persist,env=self.env,days=M.retention_days(self.settings)}
    local ok,result=pcall(resets.apply,ctx,request,self.accounting,state,runner.wall())
    if not ok then result=canon.object({nonce=request.nonce,scope=request.scope,time=canon.float(runner.wall()),done=false,code='STATS-RESET-FAILED'}) end
    if result.done then
      local saved=pcall(resets.save,ctx,self.accounting,state)
      if saved then self.last_save=runner.clock();self.accounting.reliability.critical=false
      else result.done=false;result.code='STORAGE-001' end
      if self.diagnosing then self.latency=state.latency;self.ping_history=state.ping end
    end
    pcall(function() (runner.write_ram or runner.write_atomic)(self.runtime..'/'..resets.RESULT,canon.encode(result)) end)
  end
  local function with_speed_lock()
    if not parts.speed or not runner.try_lock then return work() end
    local taken=runner.try_lock(self.runtime,work)
    if not taken then error('busy',0) end
  end
  local ok,err
  if parts.auto and runner.try_lock then
    ok,err=pcall(function()
      local taken=runner.try_lock(self.persist,with_speed_lock,'native-history.lock')
      if not taken then error('busy',0) end
    end)
  else ok,err=pcall(with_speed_lock) end
  if not ok then
    if err=='busy' then return false end
    error(err,0)
  end
  return true
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
  pcall(function() self:stats_reset() end)
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
    do local ids={};for _,p in ipairs(bound) do ids[p.id]=true end;self.endpoints:retain(ids) end
    local function endpoint(profile,now) return self.endpoints:observe(profile,now) end
    local ctx={data=data,settings=settings,observed=observed,selected=selected,bound=bound,results={}}
    local next_index,running,completed=1,0,0
    local function launch()
      while running<M.PROBE_WORKERS and next_index<=#bound do
        local index=next_index;next_index=next_index+1;running=running+1
        local okp=pcall(probe.probe,runner,bound[index],function(result)
          if ctx.results[index] then return end
          ctx.results[index]=result;running=running-1;completed=completed+1
          if completed==#bound then finish(ctx) else launch() end
        end,endpoint)
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
  -- Ping cadence is the owner's own setting (ping_interval, default 1 min), not the probe level (agent.py).
  self.ping:configure(policy.ping_interval(settings),target or nil,policy.ping_valid_for(settings))
  local okp=pcall(function() self.ping:apply(rows,pair,runner.wall()) end)
  if not okp then for _,row in ipairs(rows) do row.ping=probe.ping_public(row,'unavailable','PING-UNAVAILABLE') end end
  for _,row in ipairs(rows) do
    row.role=row.id==pair.source and 'source' or (row.id==pair.target and 'target' or 'unknown')
  end
  local native=self:read_json(self.runtime..'/native-status.json',canon.object())
  now=runner.wall()
  for _,row in ipairs(measured) do
    self.accounting:observe(M.typed_result(row),interval*3,native,pair)
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
  -- agent.monitor_loop's speed part: traffic sample, cancel on a failed channel, automatic tests, history age
  local okspeed=pcall(function() self:speed_pass(data,rows,measured,wan_devices) end)
  if not okspeed then self.events[#self.events+1]=canon.object({time=runner.wall(),code='SPEED-MONITOR-UNAVAILABLE'}) end
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
  local okf=pcall(function() self.fast:configure(self:fast_option(),rows,pair,status.native_failover.state) end)
  if not okf then pcall(function() self.fast:close() end) end
  if self.fast_on then status.fast_detect=self.fast:public(runner.clock(),true) end
  -- The response metric is the owner's setting, published even when the booster failed: without it the page
  -- would read the three-site model and show a dash next to a measured ping.
  status.response_metric=metric
  if okb then status.probe_policy=self.booster:public(settings,runner.wall())
  else status.probe_policy=canon.object({code='PROBE-POLICY-UNAVAILABLE'}) end
  local stats=accounting.stats.public(runner,now)
  stats.storage=accounting.stats.storage(runner,self.runtime,self.persist)
  -- the owner's retention (time or size) with its size model, and the room the page warns about
  stats.retention=retention.public(settings)
  stats.capacity=retention.capacity(self.persist,runner.read_file)
  status.stats_mode=stats
  -- size mode: the two minute-row files keep to their share of the owner's budget when saved
  local budgets=retention.resolve(settings)
  self.latency.byte_budget=budgets.latency_bytes;self.ping_history.byte_budget=budgets.response_bytes
  -- HTTPS latency minute means of the Auto pair (Diagnostics only; Work mode publishes the empty view)
  if self.diagnosing then pcall(function() self.latency:observe(status,settings,canon.float(runner.wall())) end) end
  local okl,lpublic=pcall(function() return latency.technical_history_tail(self.latency:public(),runner.wall()) end)
  if okl then status.latency_history=lpublic end
  -- Work mode keeps no response history (stats_mode.py); Diagnostics fills the ping history every pass.
  if metric=='websites' then status.website_response_history=responses.website_unavailable()
  else
    if self.diagnosing then pcall(function() self.ping_history:observe(status,settings,runner.wall(),M.retention_days(settings)) end) end
    local okh,public=pcall(function() return self.ping_history:public(runner.wall()) end)
    status.website_response_history=okh and public or responses.website_unavailable()
  end
  -- reliability.controller and the route history (agent.monitor_loop): a route change asks for an early save
  local rel=self.accounting.reliability
  local okc,active=pcall(function()
    local pair_mod=require('pair')
    return reliability.active_controller(status.native_failover,page.read_state(self.env),pair_mod.intent(self.env),runner.wall())
  end)
  rel:controller(okc and active or false,canon.float(runner.wall()),interval*3)
  local route_now=runner.wall()
  local okr,kind=pcall(reliability.observed_route,status,route_now)
  if rel.routes:observe(okr and kind or 'unknown',canon.float(route_now),interval*3) then rel.critical=true end
  status.accounting.reliability=rel:public()
  status.native_history=page.native_history(self.env,M.retention_days(settings),runner.wall())
  status.stats_reset=self:read_json(self.runtime..'/stats-reset-result.json',NULL)
  status.auto_control=page.auto_control(self.env,runner.wall())
  local readiness=self:system_readiness(settings)
  if readiness then status.system_readiness=readiness end
  status.lua_backend=self:backend_record()
  status.wan_devices=wan_devices
  status.speed_tests=self:speed_tests()
  status.telegram=self:telegram_field(settings,status)
  local status_text=canon.encode(status)
  runner.write_atomic(self.runtime..'/status.json',status_text)
  self.status=status;self.published_at=runner.clock()
  -- hv-core (Lua plan item 8): the Auto supervisor in this process takes this pass from memory, not from the file
  if self.on_status then pcall(self.on_status,status,status_text) end
  local since_save=runner.clock()-self.last_save
  local due
  -- Work mode: the accounting reaches flash once a day (and at shutdown); Diagnostics: every checkpoint interval
  -- and, after an outage edge or a route change, at most once a minute (agent.CRITICAL_SAVE_SPACING).
  if self.diagnosing then
    due=(rel.critical and since_save>=M.CRITICAL_SAVE_SPACING) or since_save>=(clamp_int(settings.checkpoint,60,86400) or 900)
  else due=since_save>=accounting.WORK_CHECKPOINT_SECONDS end
  if due then
    local saved=pcall(function() self:checkpoint() end)
    if saved then self.storage_error=nil;self.last_save=runner.clock();rel.critical=false else self.storage_error='STORAGE-001' end
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
  record.native=canon.array({'status','events','history','auto_live','inventory','setup_probe','setup_response','setup_stats',
    'pair_manual','native_start','native_stop','fault_cancel','channel_path','manual_switch_control','scan','system_readiness'})
  record.python=canon.array({'fault_start (the test itself)','other setup_*','statistics',
    'fallbacks of pair_manual/native_start/native_stop/fault_cancel'})
  record.speed_telegram=canon.array({'speed_pause','speed_start','speed_cancel','speed_live','speed_tests','speed worker','telegram reports',
    'telegram_retry','telegram_test (lua CLI)'})
  record.bridges=canon.array()
  record.bridge_fallback=canon.array({'manual_switch_control (only after a failed Lua computation; on demand, never on a timer)'})
  record.not_ported=canon.array({'failure_diagnosis','failover_plan','candidate_hierarchy','suspicion','website/compare histories'})
  return record
end

-- status.system_readiness (system_readiness.snapshot): the page's System readiness card. The dependency/board/
-- storage/preparation checks cost a few file stats and three short `uci -q get` children (the preparation), so they
-- run at most every READINESS_REFRESH seconds; between refreshes every pass publishes the same record with its own
-- time (the page shows its age). The board answer of ubus is read once per process (readiness.lua memo).
M.READINESS_REFRESH=30
function Monitor:system_readiness(settings)
  local runner=self.runner
  local now=runner.clock()
  if self.readiness_value and self.readiness_at and now>=self.readiness_at and now-self.readiness_at<M.READINESS_REFRESH then
    return self.readiness_value
  end
  local base=self.readiness_sys
  if not base and runner.platform_sys then
    local ok,view=pcall(runner.platform_sys)
    if ok and type(view)=='table' then base=view;self.readiness_sys=view end
  end
  if not base then return self.readiness_value end
  local view=setmetatable({preparation=base.preparation or function(s) return require('platform').preparation_snapshot(base,s) end},{__index=base})
  local ok,value=pcall(require('readiness').snapshot,view,settings,runner.wall(),self.readiness_memo)
  if ok then self.readiness_value=value;self.readiness_at=now end
  return self.readiness_value
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
-- speed_pause.public() natively (plan item 7; was the status bridge)
function Monitor:speed_pause()
  if not self.runner.exists(self.runtime..'/speed-pause.json') then return canon.object({active=false}) end
  return require('speed_pause').public(self.speed_deps)
end

------------------------------------------------------------------------------------------------------
-- speed test and Telegram (plan item 7)
------------------------------------------------------------------------------------------------------
-- speed_pause.gate('monitor'): true = stay quiet (no pass now, look again in a second). The acknowledgement waits
-- until no pass and no ping echo is in flight (agent.py: website/ping samplers idle).
function Monitor:speed_gate()
  if not self.runner.exists(self.runtime..'/speed-pause.json') then return false end
  local ok,quiet=pcall(require('speed_pause').gate,self.speed_deps,'monitor',function()
    return not self.passing and (self.ping.idle==nil or self.ping:idle())
  end)
  return ok and quiet==true
end

-- speed_test.public_status() for the status field. The job part (a small RAM file, worker checks) is read at every
-- call; the flash history is parsed and hashed again only when its files change or once a minute (age cutoff).
function Monitor:speed_tests()
  local runner=self.runner
  local speed=require('speed')
  local function key(name) return tostring(runner.file_key and runner.file_key(name) or nil) end
  local function cached_history(d)
    local history_key=table.concat({key(self.persist..'/speed-history.json'),key(self.persist..'/speed-history.backup.json'),
      tostring(M.retention_days(self.settings)),tostring(math.floor(runner.wall()/60))},'|')
    local cache=self.speed_history_cache
    if runner.file_key and cache and cache.key==history_key then
      if cache.err then error(cache.err,0) end
      local copy=canon.object();for k,v in pairs(cache.value) do copy[k]=v end
      return copy
    end
    local ok,value=pcall(speed.load_history,d)
    self.speed_history_cache={key=history_key,value=ok and value or nil,err=(not ok) and value or nil}
    if not ok then error(value,0) end
    local copy=canon.object();for k,v in pairs(value) do copy[k]=v end
    return copy
  end
  local ok,value=pcall(speed.public_status,self.speed_deps,cached_history)
  if not ok then value=canon.object({code='SPEED-STATUS-UNAVAILABLE',results=canon.array()}) end
  return value
end

M.SPEED_PRUNE_SECONDS=600
function Monitor:speed_pass(data,rows,measured,wan_devices)
  local speed=require('speed')
  local d=self.speed_deps
  local wan=type(wan_devices)=='table' and #wan_devices>0
  speed.observe_traffic(d,wan and wan_devices or measured,wan and 'wan' or 'vpn')
  if speed.active_job(d) then
    for _,p in ipairs(measured) do
      if p.code=='VPN-001' or p.code=='VPN-003' or p.code=='DNS-001' then speed.cancel(d);break end
    end
  end
  self.speed_previous=speed.automatic_new(d,rows,self.speed_previous,data)
  -- age cleanup of the flash history: agent.py every 60 s; here every 10 min (parsing and hashing up to 500 rows costs
  -- a sha256sum process and pure-Lua encoding on the MT3000, rows age by whole days)
  local now=self.runner.clock()
  if now-(self.speed_retention_check or -math.huge)>=M.SPEED_PRUNE_SECONDS then
    if speed.prune_history(d) then self.speed_retention_check=now end
  end
end

-- rpc speed_start / speed_cancel / speed_live / telegram_retry; rpc.FALLBACK when the control lock is busy
-- (agent.py then waits for it as before: the event loop never waits).
function Monitor:speed_rpc(method,arguments)
  local speed=require('speed')
  if method=='speed_start' then
    local ok,reply=pcall(speed.start,self.speed_deps,arguments,false)
    if not ok then
      if speed.is_speed_error(reply) then return canon.object({accepted=false,code=reply.code}) end
      error(reply,0)
    end
    if reply==nil then return rpc.FALLBACK end
    return reply
  end
  if next(arguments)~=nil then error({code='RPC-UNEXPECTED-ARGS'},0) end
  local reply
  if method=='speed_cancel' then reply=speed.cancel(self.speed_deps)
  elseif method=='speed_live' then reply=speed.public_live(self.speed_deps)
  elseif method=='telegram_retry' then reply=require('telegram').retry_unknown(self.telegram_deps)
  else return rpc.FALLBACK end
  if reply==nil then return rpc.FALLBACK end
  return reply
end

local function truthy(v) return v~=nil and v~=false and v~=NULL and v~='' and v~=0 end
M.TELEGRAM_SECONDS=300
-- agent.monitor_loop's Telegram part: one delivery at a time in a child process (`lua telegram.lua deliver`) on a
-- copy of this pass; its result is applied at the next pass. The child saves the sender state itself, so a
-- monitor restart never loses a confirmed delivery (no duplicate report).
function Monitor:telegram_field(settings,status)
  local enabled=truthy(settings.telegram_enabled)
  if self.telegram_notice=='TELEGRAM-STATE-CORRUPT' then return canon.object({enabled=enabled,code=self.telegram_notice}) end
  local job=self.telegram_job
  if job and job.done then self:telegram_collect(job);self.telegram_job=nil;job=nil end
  if not job and not enabled then self.telegram_public=canon.object({enabled=false})
  elseif not job then
    local ok,err=pcall(function() self:telegram_start(status,enabled) end)
    if not ok then
      if self.runner.log then self.runner.log('telegram: '..tostring(type(err)=='table' and err.code or err)) end
      self.telegram_job=nil;self.telegram_public=canon.object({enabled=enabled,code='TELEGRAM-REPORT-UNAVAILABLE'})
    end
  end
  if self.telegram_public then return shallow(self.telegram_public) end
  return canon.object({enabled=enabled})
end

function Monitor:telegram_start(status,enabled)
  local runner=self.runner
  local snapshot=canon.object({time=status.time,profiles=status.profiles,events=status.events,native_failover=status.native_failover,
    native_history=status.native_history,accounting=self.accounting:export()})
  local base=self.runtime..'/telegram-job-'..canon.unique()
  local job={input=base..'.in.json',output=base..'.out.json',enabled=enabled,done=false}
  local input=canon.object({status=snapshot,saved=self.telegram_saved,now=canon.float(runner.wall())})
  ;(runner.write_ram or runner.write_atomic)(job.input,canon.encode(input))
  self.telegram_job=job
  local function finished() job.done=true end
  if self.telegram_run then self.telegram_run(job,finished)
  elseif runner.spawn then
    runner.spawn({'/usr/bin/lua','/usr/lib/homensai-vpn/lua/telegram.lua','deliver',job.input,job.output},M.TELEGRAM_SECONDS,finished)
  else error('no child process support') end
end

function Monitor:telegram_collect(job)
  local runner=self.runner
  local ok,result=pcall(function() return canon.decode(runner.read_file(job.output)) end)
  pcall(runner.remove,job.input);pcall(runner.remove,job.output)
  if not ok or not is_dict(result) or not is_dict(result.public) then
    self.telegram_public=canon.object({enabled=job.enabled,code='TELEGRAM-REPORT-UNAVAILABLE'});return
  end
  local public=result.public
  if self.telegram_notice then public.storage_notice=self.telegram_notice end
  if result.stored==true then self.telegram_notice=nil
  elseif result.stored==false then public.storage_error='TELEGRAM-STATE-WRITE-FAILED' end
  if is_dict(result.saved) then self.telegram_saved=result.saved end
  self.telegram_public=public
end

function Monitor:page_fields(status)
  local runner=self.runner
  local now=runner.wall()
  local env=self.env
  status.speed_pause=self:speed_pause()
  if self.fast_on then status.fast_detect=self.fast:public(runner.clock(),true) end
  -- scan_control.public in Lua (was status_bridge.py); a damaged scan.state leaves the field out, as before
  local okscan,scan=pcall(self.scan_status,self,now)
  if okscan then status.scan=scan end
  status.stats_reset=self:read_json(self.runtime..'/stats-reset-result.json',NULL)
  status.switch_timing=page.switch_timing(env)
  status.auto_control=page.auto_control(env,now)
  -- manual_switch_control in Lua (page_controls.lua). status_bridge.py is only the fallback of a failed Lua
  -- computation: started on demand (at most every BRIDGE_EVERY s), never on a timer; until it answers, fail-safe.
  local control,manual=self:manual_controls(status,now)
  if not control then
    self.bridge:request()
    local bridged=self.bridge:current(now)
    control=bridged and is_dict(bridged.manual_switch_control) and bridged.manual_switch_control or nil
    local use_pair
    use_pair,manual=page.manual_switch(env,status.native_failover,control and control.available==true or false)
    if not control then control=use_pair and page.controls_fallback(now) or page.legacy_controls_fallback(now) end
  end
  status.manual_switch=manual
  status.manual_switch_control=control
  status.channel_path=self:channel_path(status,now)
  status.speed_tests=self:speed_tests()
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

------------------------------------------------------------------------------------------------------
-- fast outage detection (fast_detect.lua, Lua plan item 5)
------------------------------------------------------------------------------------------------------
-- The owner switch: option lua_fast_detect '1' in config main 'main'; re-read only when the file changed.
function Monitor:fast_option()
  local runner=self.runner
  local key=runner.config_mtime and runner.config_mtime() or nil
  if key~=self.fast_key then
    self.fast_key=key
    self.fast_on=key~=nil and fast.option_enabled(runner.config_text and runner.config_text() or nil) or false
  end
  return self.fast_on
end

-- One beat (the monitor's 1 s timer). Returns true when a dense confirmation episode just started: the caller
-- starts a pass now. A suspect never switches: it only asks Booster:suspect for real full checks, which apply
-- their own rest/back-off and watching-state rules with the CURRENT Auto state (read only when a suspect exists).
function Monitor:fast_tick()
  local runner=self.runner
  if not self:fast_option() then
    if self.fast.active then self.fast:close() end
    return false
  end
  local now=runner.clock()
  local suspects=self.fast:tick(now)
  if not suspects then return false end
  local native=self:read_json(self.runtime..'/native-status.json',canon.object())
  local state=is_dict(native) and native.state or nil
  for _,ch in ipairs(suspects) do
    local item={profile=ch.id,reason=fast.REASON,evidence=canon.object(self.fast:evidence(ch,now))}
    local ok,started=pcall(function() return self.booster:suspect(self.settings,{item},self.fast:pair(),state,runner.wall()) end)
    if ok and started then
      self.fast:disarm(ch.id)
      if runner.log then runner.log('fast detect: '..ch.id..' lost '..ch.lost..' beats ('..tostring(ch.reason)..'); dense confirmation started') end
      return true
    end
    self.fast:hold(ch.id,now+fast.RETRY)
  end
  return false
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
  pcall(function() self.fast:close() end)
  pcall(require('speed').cancel,self.speed_deps)  -- agent.monitor_loop: a running speed test ends with the monitor
end

------------------------------------------------------------------------------------------------------
-- uloop + ubus wiring (router only; the PC tests never call run())
------------------------------------------------------------------------------------------------------
-- uloop has no signal API in Lua 5.1 on OpenWrt 21.02: procd's SIGTERM ends the process without a final
-- checkpoint. The init script therefore calls `ubus call homensai-vpn-lua shutdown` (root only, not in the
-- rpcd ACL) before procd stops the instance; shutdown saves and keeps serving until procd's SIGTERM.
--
-- start(runner, options, hooks) wires the monitor into an initialised uloop and returns its handle
-- {monitor, conn, ready, kick()} (the caller keeps it: libubox-lua cancels unreferenced timers); run() is the
-- separate monitor process, hv_core.lua (Lua plan item 8) runs the same start() next to the Auto supervisor.
-- hooks.object(object, conn): called before the ubus object is added (hv-core guards every method).
-- The tick and the watcher re-arm themselves even when their body fails: one failing callback never ends the
-- monitor's loop (and, inside hv-core, never ends the Auto supervisor sharing the process).
function M.start(runner,options,hooks)
  hooks=hooks or {}
  local uloop=require('uloop');local ubus=require('ubus')
  if runner.attach_loop then runner.attach_loop(uloop) end
  -- leftovers of flash writes a power cut interrupted (POWER-CUT-INTEGRITY-2026-10-31.ru.md), before any read
  pcall(function() require('durable').sweep((options and options.persist) or runner.PERSIST or '/etc/homensai-vpn') end)
  local monitor=M.new(runner,options)
  local conn=ubus.connect()
  if not conn then error('ubus connect failed') end
  local object=monitor.rpc.ubus_object(conn,ubus)
  object[rpc.OBJECT].shutdown={function(req,msg) monitor:shutdown();conn:reply(req,{saved=true}) end,{}}
  object[rpc.OBJECT].checkpoint={function(req,msg)
    local ok=pcall(function() monitor:checkpoint() end)
    monitor.last_save=runner.clock();conn:reply(req,{saved=ok}) end,{}}
  if hooks.object then hooks.object(object,conn) end
  conn:add(object)
  local ready=monitor.runtime..'/'..(runner.READY or 'lua-monitor.ready')
  pcall(runner.write_ram or runner.write_atomic,ready,canon.encode(canon.object({version=monitor.version,started=runner.wall()})))
  -- Owner decision 31.10.2026: Auto the owner switched on comes back after a power cut (boot_resume.lua)
  local resume=nil
  do
    local ok,made=pcall(function()
      local control=require('control_request')
      local deps=monitor:control_deps()
      return require('boot_resume').new({read=deps.read,exists=deps.exists,now=deps.now,runtime=deps.runtime,persist=deps.persist,
        write_ram=runner.write_ram or runner.write_atomic,FALLBACK=control.FALLBACK,
        uptime=function() local text=runner.read_file('/proc/uptime');return text and tonumber(string.match(text,'^(%S+)')) end,
        intent=function() return deps.intent() end,
        revision=function()
          local locked,revision=deps.try_lock(function() return control.revision_locked(deps) end)
          if not locked then error('busy',0) end
          return revision
        end,
        start=function(arguments) return control.start(deps,arguments) end,
        fallback=function(arguments)
          local request=deps.runtime..'/boot-resume-request.json'
          runner.write_ram(request,canon.encode(arguments))
          runner.spawn({'/bin/sh','-c','/usr/bin/python3 /usr/lib/homensai-vpn/agent.py call native_start <'..request..' >/dev/null 2>&1; rm -f '..request},120,function() end)
        end})
    end)
    if ok then resume=made elseif runner.log then runner.log('boot resume: '..tostring(made)) end
  end
  local timer
  local config_stamp=runner.config_mtime()
  local function tick()
    local ok,err=pcall(function()
      -- the speed test's quiet window (speed_pause.gate('monitor')), at the loop boundary like agent.monitor_loop
      if monitor:speed_gate() then timer:set(1000);return end
      local started=monitor:start_pass(function()
        config_stamp=runner.config_mtime()
        timer:set(math.floor(monitor:next_delay()*1000))
      end)
      if not started then timer:set(1000) end
    end)
    if not ok then
      if runner.log then runner.log('monitor tick: '..tostring(err)) end
      timer:set(1000)
    end
  end
  timer=uloop.timer(tick)
  timer:set(100)
  -- A changed configuration or a page scan request starts the next pass now (agent.py's 1 s wait loop).
  -- scan_control is not ported: a new scan.request (its file key changed) only starts one pass now.
  local watcher
  local scan_key=runner.file_key and runner.file_key(monitor.runtime..'/scan.request') or nil
  local watch
  watcher=uloop.timer(function()
    local ok,err=pcall(watch)
    if not ok and runner.log then runner.log('monitor watcher: '..tostring(err)) end
    watcher:set(1000)
  end)
  watch=function()
    -- Lua plan item 5: the fast-detection pulse rides this timer (one beat per second while it is switched on);
    -- a started confirmation episode begins its first full pass now (a running pass schedules the dense one).
    local okf,suspected=pcall(monitor.fast_tick,monitor)
    if not okf and runner.log then runner.log('fast detect: '..tostring(suspected)) end
    if okf and suspected and not monitor.passing then timer:set(1) end
    if resume then local okr,err=pcall(resume.tick);if not okr and runner.log then runner.log('boot resume: '..tostring(err)) end end
    -- Diagnostics: `touch /var/run/homensai-vpn/lua-monitor-profile.request` (profiler.lua)
    pcall(function() require('profiler').tick(monitor.runtime,'lua-monitor-profile',60) end)
    if not monitor.passing then
      local stamp=runner.config_mtime()
      local key=runner.file_key and runner.file_key(monitor.runtime..'/scan.request') or nil
      -- a queued statistics reset is applied at the start of a pass (agent.py breaks its wait for it too)
      -- (once per new request file: a request left behind by a busy lock is retried by the normal passes)
      local rkey=runner.file_key and runner.file_key(monitor.runtime..'/'..resets.REQUEST) or nil
      local reset_waiting=rkey~=nil and rkey~=monitor.reset_key
      if reset_waiting then monitor.reset_key=rkey end
      if stamp~=config_stamp or (key~=nil and key~=scan_key) or reset_waiting then config_stamp=stamp;scan_key=key;timer:set(1)
      -- a speed-test pause file: answer it within a second (agent.py breaks its wait loop for it)
      elseif runner.exists(monitor.runtime..'/speed-pause.json') then timer:set(1) end
    end
  end
  watcher:set(1000)
  return {monitor=monitor,conn=conn,ready=ready,timer=timer,watcher=watcher,resume=resume,
    kick=function() if not monitor.passing then timer:set(1) end end}
end

function M.run(runner,options)
  local uloop=require('uloop')
  if runner.setup_timezone then runner.setup_timezone() end
  uloop.init()
  local handle=M.start(runner,options)
  uloop.run()
  pcall(os.remove,handle.ready)
  handle.conn:close()
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
