-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- gl_sensors.lua: the monitor side of the GL sensors (docs/architecture/GL-SENSORS-2026-11-04.ru.md). Python twin:
-- gl_sensors.py (agent.py). Owns the I/O; every decision is in the pure modules wan_diag / wg_events / boot_cause.
--   tick(now)   the monitor's 1 s timer: the underlay echo through the WAN device (one raw ICMP socket bound to it,
--               SO_BINDTODEVICE, no tunnel mark; one echo per 10 s, every 2 s while a channel fails or the WAN is
--               suspected; the reply is read on the next tick, no blocking), new WireGuard events (one lstat per
--               second, the file is read only when it changed) and, once per boot after 120 s of uptime, the crash
--               log fingerprint (boot_cause.refresh). Returns the suspicion items of REKEY events of pair devices.
--   configure(settings, wan_devices, rows, pair)   after every pass (the WAN device, the wg flag file, the channels)
--   pass(rows, pair, wall, age, settings, uplink)  the status field wan_diagnosis (Auto reads its hold through
--               diagnosis.diagnose) and the hasten flag (the monitor starts the dense confirmation of the primary).
local canon=require('canon')
local probe=require('probe')
local wan=require('wan_diag')
local wg=require('wg_events')

local M={}
M.KMWAN='/proc/gl-kmwan/config'
M.BOOT_REFRESH_UPTIME=120
M.DRAIN=16
M.SCOPE='WAN versus tunnel diagnosis: own ICMP echo through the WAN device, GL multi-WAN and repeater verdicts, the pair probes and WireGuard events; holds a switch only while the WAN is proven down'

local function u16(n) return string.char(math.floor(n/256)%256,n%256) end

local S={};S.__index=S
function M.new(runner,runtime,persist)
  local ident=runner.random(2)
  return setmetatable({runner=runner,runtime=runtime,persist=persist,underlay=wan.Underlay(),tracker=wan.Tracker(),
    reader=wg.Reader(),events={},events_key=false,enabled=false,wg_on=false,alert=false,sock=nil,pending=nil,
    salt=runner.random(8),sequence=0,ident=string.byte(ident,1)*256+string.byte(ident,2),channels={},boot_done=false,flag_done=false},S)
end

function S:close()
  if self.sock then pcall(function() self.sock:close() end) end
  self.sock=nil;self.pending=nil
end

-- after every pass
function S:configure(settings,wan_devices,rows,pair)
  self.enabled=wan.enabled(settings)
  local device=nil
  if self.enabled and type(wan_devices)=='table' then
    for _,row in ipairs(wan_devices) do
      if type(row)=='table' and type(row.device)=='string' then device=row.device;break end
    end
  end
  if device~=self.underlay.device then self:close() end
  self.underlay:bind(device)
  local channels={}
  if type(pair)=='table' then
    for _,row in ipairs(type(rows)=='table' and rows or {}) do
      if type(row)=='table' and type(row.id)=='string' and type(row.device)=='string' and (row.id==pair.source or row.id==pair.target) then
        channels[#channels+1]={id=row.id,device=row.device}
      end
    end
  end
  self.channels=channels
  local on=wg.enabled(settings)
  if on~=self.wg_on then self.reader=wg.Reader();self.events={};self.events_key=false;self.flag_done=false end
  self.wg_on=on
end

-- the hotplug listener writes only while RUNTIME/wg-events.on exists: kept in step with the option by the 1 s timer
-- (a pass itself writes nothing)
function S:flag_tick()
  if self.flag_done then return end
  local runner=self.runner
  local flag=self.runtime..'/'..wg.FLAG
  if self.wg_on and not runner.exists(flag) then runner.write_ram(flag,'file\n')
  elseif not self.wg_on and runner.exists(flag) then runner.remove(flag) end
  self.flag_done=true
end

function S:packet(target)
  self.sequence=(self.sequence+1)%65536
  local payload='HV-WAN\0\0'..self.salt..u16(self.sequence)..'\0\0\0\0\0\0'
  local sum=probe.icmp_checksum('\8\0\0\0'..u16(self.ident)..u16(self.sequence)..payload)
  return '\8\0'..u16(sum)..u16(self.ident)..u16(self.sequence)..payload,
    {identifier=self.ident,sequence=self.sequence,payload=payload,target=target}
end

function S:underlay_tick(now)
  local runner,u=self.runner,self.underlay
  if not self.enabled or u.device==nil then return end
  local p=self.pending
  if p then
    if now-p.at<1 then return end
    self.pending=nil
    local ok=false
    if self.sock then
      for _=1,M.DRAIN do
        local data=self.sock:recv()
        if not data then break end
        if probe.valid_reply(data,p.identifier,p.sequence,p.payload,p.target) then ok=true;break end
      end
    end
    u:record(ok,p.target,p.at)  -- the send time: the same cadence as the blocking Python echo
    return
  end
  if not u:due(now,self.alert) then return end
  if not self.sock then
    local sock,kind=runner.beat_socket(u.device)
    if not sock then
      if kind=='missing' then u:record(false,u:target(),now) end
      return
    end
    self.sock=sock
  end
  local target=u:target()
  local packet,pending=self:packet(target)
  local sent,kind=self.sock:send(target,packet)
  if not sent then
    if kind~='refused' then self:close() end
    if kind=='refused' or kind=='missing' then u:record(false,target,now) end
    return
  end
  pending.at=now
  self.pending=pending
end

function S:events_tick(now)
  if not self.wg_on then return {} end
  local runner=self.runner
  local path=self.runtime..'/'..wg.FILE
  local key=runner.file_key and runner.file_key(path) or nil
  if key==self.events_key then return {} end
  self.events_key=key
  local ok,text=pcall(runner.read_file,path)
  self.events=wg.parse(ok and text or nil)
  return wg.suspicions(self.reader:new(self.events),self.channels)
end

-- the monitor's 1 s timer; returns suspicion items (REKEY of a pair device)
function S:tick(now)
  pcall(self.flag_tick,self)
  pcall(self.underlay_tick,self,now)
  local ok,items=pcall(self.events_tick,self,now)
  if not self.boot_done and now>=M.BOOT_REFRESH_UPTIME then
    self.boot_done=true
    pcall(function() require('boot_cause').refresh(self.persist,{write=self.runner.write_atomic}) end)
  end
  return ok and items or {}
end

local function object(t)
  local out=canon.object()
  for k,v in pairs(t) do if v==nil then out[k]=canon.null else out[k]=v end end
  return out
end

-- one pass: the status field wan_diagnosis
function S:pass(rows,pair,wall,age,settings,uplink)
  local runner=self.runner
  local mono=runner.clock()
  local kmwan=nil
  pcall(function() kmwan=wan.kmwan_verdict(runner.read_file(M.KMWAN)) end)
  local wg_state=nil
  if self.wg_on and type(pair)=='table' then
    for _,ch in ipairs(self.channels) do
      if ch.id==pair.source then wg_state=wg.latest(self.events,ch.device,mono) end
    end
  end
  local sensors={uplink=uplink,underlay=self.underlay:state(mono),kmwan=kmwan,wg=wg_state,null=canon.null}
  local ev=wan.evidence(rows,pair,wall,age,sensors)
  if self.enabled and ev.primary=='bad' and runner.command then
    -- GL repeater captive portal (gl_led:73-78): one ubus call per pass, only while the primary fails
    pcall(function()
      local text=runner.command('repeater_status')
      if text then sensors.portal=wan.portal_verdict(canon.plain(canon.decode(text))) end
    end)
    ev=wan.evidence(rows,pair,wall,age,sensors)
  end
  local diag=wan.diagnose(ev,self.enabled)
  local primary_ok_at=nil
  if type(pair)=='table' then
    for _,row in ipairs(type(rows)=='table' and rows or {}) do
      if type(row)=='table' and row.id==pair.source and wan.channel_state(row,wall,age,canon.null)=='ok' then primary_ok_at=wan.plain(row.time) end
    end
  end
  local tracked
  if self.enabled then tracked=self.tracker:update(diag,wall,primary_ok_at,wan.grace_seconds(settings))
  else self.tracker=wan.Tracker();tracked={hold=false,recovering=false,restored=false,code=diag.code} end
  local failing={bad=true,dns=true}
  self.alert=failing[ev.primary]==true or failing[ev.reserve]==true or self.underlay.fails>0 or tracked.hold==true
  self.restored=tracked.restored==true
  self.hasten=diag.hasten==true
  local under=self.underlay:public(mono)
  local N=canon.null
  local public_under=object(under)
  if under.device==nil then public_under.device=N end
  if under.age_s==nil then public_under.age_s=N end
  return object({time=wall,enabled=self.enabled,verdict=diag.verdict,confidence=diag.confidence,
    code=tracked.code==nil and N or tracked.code,hold=tracked.hold==true,recovering=tracked.recovering==true,
    hasten=diag.hasten==true,posterior=object(diag.posterior),evidence=object(ev),underlay=public_under,
    down_since=tracked.down_since==nil and N or tracked.down_since,up_at=tracked.up_at==nil and N or tracked.up_at,scope=M.SCOPE})
end

return M
