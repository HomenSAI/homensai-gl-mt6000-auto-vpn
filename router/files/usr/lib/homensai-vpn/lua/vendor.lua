-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- vendor.lua: vendor_observation.VendorObserver for the Lua monitor. Read-only configured tunnel identity
-- epochs: a profile measurement keeps its health fields only when the same profile was bound to the same
-- tunnel before and after the measurement; each row then carries vendor_tunnel_id, vendor_generation (a new
-- 32-hex epoch on every observed change), vendor_state (UNKNOWN/PENDING/SETTLED after two stable samples) and
-- vendor_changed_at - the identity the Auto controller scopes its sample streaks with
-- (failure_diagnosis.profile_identity/scoped_samples). A restart starts fresh unproven epochs, as in Python.
-- One addition: exit_country (cdn-cgi/trace loc=) is kept next to exit_ip as a health field.
local canon=require('canon')

local M={}
local NULL=canon.null
M.HEALTH={'https_success','dns_ok','rtt_ms','exit_ip','exit_country','server_endpoint','probe_checks'}
M.MEASUREMENT_FIELDS={'id','time','code','scope','lan_path_verified','device','mark','table','ifindex',
  'https_success','dns_ok','rtt_ms','exit_ip','exit_country','server_endpoint','probe_checks'}
local TARGETS={['one.one.one.one']=true,['dns.google']=true,['dns.quad9.net']=true}
local OUTCOMES={ok=true,['http-unsupported']=true,['http-error']=true,timeout=true,['tls-error']=true,['transport-error']=true,
  ['invalid-response']=true,unknown=true}

local function map(v) return type(v)=='table' and v~=NULL and not canon.is_array(v) and not canon.is_float(v) end
local function safe(s) return type(s)=='string' and #s>=1 and #s<=96 and string.find(s,'^[A-Za-z0-9_.:-]+$')~=nil end
local function tunnel_name(s)
  if type(s)~='string' then return false end
  local proto,rest=string.match(s,'^(%a+):(.+)$')
  return (proto=='openvpn' or proto=='wireguard') and #rest<=64 and string.find(rest,'^[A-Za-z0-9_.-]+$')~=nil
end
local function profile_group(s) return type(s)=='string' and (string.find(s,'^openvpn:%d+$') or string.find(s,'^wireguard:%d+$'))~=nil and #s<=30 end
local function num(v) return canon.number(v) end

function M.probe_checks(value)
  local result,seen=canon.array(),{}
  if type(value)~='table' then return result end
  for i=1,math.min(3,#value) do
    local row=value[i]
    if map(row) and TARGETS[row.target] and not seen[row.target] and OUTCOMES[row.result] then
      seen[row.target]=true
      local clean=canon.object({target=row.target,result=row.result})
      local status,elapsed=row.http_status,num(row.elapsed_ms)
      if type(status)=='number' and status%1==0 and status>=100 and status<=599 then clean.http_status=status end
      if elapsed and elapsed==elapsed and elapsed>=0 and elapsed<=60000 then clean.elapsed_ms=row.elapsed_ms end
      result[#result+1]=clean
    end
  end
  return result
end

function M.tunnel_identity(profile)
  if not map(profile) then return nil end
  local protocol,logical,claimed,identifier=profile.protocol,profile.interface,profile.vendor_tunnel_id,profile.id
  if (protocol~='openvpn' and protocol~='wireguard') or type(logical)~='string' or not tunnel_name(claimed)
     or claimed~=protocol..':'..logical or not safe(identifier) or string.sub(identifier,1,#protocol+1)~=protocol..':'
     or identifier==protocol..':' or (profile.section~=nil and identifier~=protocol..':'..tostring(profile.section)) then return nil end
  return claimed
end

local function snapshot(data)
  local profiles=map(data) and type(data.profiles)=='table' and data.profiles or {}
  local by_id,bindings,logicals,claims={},{},{},{}
  for i=1,math.min(400,#profiles) do
    local profile=profiles[i]
    if map(profile) and safe(profile.id) then
      local id=profile.id
      if by_id[id]~=nil then by_id[id]=false else by_id[id]=profile end
      local tunnel=M.tunnel_identity(profile)
      if tunnel then
        bindings[tunnel]=bindings[tunnel] or {};table.insert(bindings[tunnel],id)
        logicals[profile.interface]=logicals[profile.interface] or {};table.insert(logicals[profile.interface],tunnel)
        claims[tunnel]=true
      end
    end
  end
  local valid={}
  for tunnel,ids in pairs(bindings) do
    if #ids==1 then
      local profile=by_id[ids[1]]
      if profile and #logicals[profile.interface]==1 then valid[tunnel]=profile end
    end
  end
  for k,v in pairs(by_id) do if v==false then by_id[k]=nil end end
  return by_id,valid,claims
end
M.snapshot=snapshot

local function anchors(data)
  local settings=map(data) and data.settings or nil
  local result,order={},{}
  if not map(settings) then return result,order end
  for _,side in ipairs({'source','target'}) do
    local tunnel,identifier=settings['plan_'..side..'_tunnel'],settings['plan_'..side]
    if tunnel_name(tunnel) and safe(identifier) then
      if not result[tunnel] then result[tunnel]={};order[#order+1]=tunnel end
      table.insert(result[tunnel],identifier)
    end
  end
  return result,order
end

function M.current_bindings(profiles) local _,valid=snapshot({profiles=profiles});return valid end

local function fingerprint_of(identifier,tunnel,kernel)
  local parts={tostring(identifier),tostring(tunnel)}
  for i=1,4 do parts[#parts+1]=tostring(kernel and kernel[i]) end
  return table.concat(parts,'\31')
end

local Observer={};Observer.__index=Observer
-- uuid: function() -> 32 hex (the runner's random source in tests)
function M.Observer(uuid)
  return setmetatable({states={},events={},uuid=uuid or require('auto_control').uuid_hex},Observer)
end

function Observer:observe(before,after,measured,now)
  if type(now)~='number' or now~=now or now<0 or now==math.huge then error('VENDOR-OBSERVATION-TIME',0) end
  local before_ids,pre,pre_claims=snapshot(before)
  local _,post,post_claims=snapshot(after)
  local anchor_map,anchor_list=anchors(after)
  local rows={}
  for i=1,math.min(400,type(measured)=='table' and #measured or 0) do if map(measured[i]) then rows[#rows+1]=measured[i] end end
  local measured_by_id={}
  for _,row in ipairs(rows) do if safe(row.id) then measured_by_id[row.id]=row end end
  local set={}
  for k in pairs(self.states) do set[k]=true end
  for k in pairs(pre_claims) do set[k]=true end
  for k in pairs(post_claims) do set[k]=true end
  for k in pairs(anchor_map) do set[k]=true end
  local anchor_index={};for i,k in ipairs(anchor_list) do anchor_index[k]=i end
  local tunnels={};for k in pairs(set) do tunnels[#tunnels+1]=k end
  table.sort(tunnels,function(a,b)
    local ia,ib=anchor_index[a],anchor_index[b]
    if ia and ib then return ia<ib end
    if ia or ib then return ia~=nil end
    local pa,pb=post[a]==nil,post[b]==nil
    if pa~=pb then return not pa end
    return a<b
  end)
  local groups,next_states=canon.array(),{}
  for index=1,math.min(400,#tunnels) do
    local tunnel=tunnels[index]
    local old=self.states[tunnel] or {}
    local current,earlier=post[tunnel],pre[tunnel]
    local identifier=current and current.id or nil
    local coherent=current~=nil and earlier~=nil and current.id==earlier.id
    local row=measured_by_id[identifier] or nil
    if row and (row.code=='VENDOR-IDENTITY-CHANGED' or row.code=='VENDOR-IDENTITY-UNKNOWN') then coherent=false end
    local kernel
    if row then kernel={row.device,row.mark,row.table,row.ifindex} else kernel=old._kernel end
    local fingerprint=coherent and fingerprint_of(identifier,tunnel,kernel) or nil
    local changed=not fingerprint or fingerprint~=old._fingerprint or now<(old.time or now)
    local previous
    if changed then previous=old.current_profile or old.previous_profile else previous=old.previous_profile end
    local generation
    if changed and coherent then generation=self.uuid() elseif coherent then generation=old.generation else generation=nil end
    local changed_at=changed and now or (old.changed_at or now)
    local stable=0
    if coherent then
      if changed then stable=1 else stable=math.min(1000000,(old.stable_samples or 0)+((now>(old.time or -1)) and 1 or 0)) end
    end
    local state=stable>=2 and 'SETTLED' or (coherent and 'PENDING' or 'UNKNOWN')
    local recent={};for _,m in ipairs(old._members or {}) do recent[#recent+1]=m end
    for _,member in ipairs({earlier and earlier.id or false,identifier or false}) do
      if member then
        local kept={member};for _,item in ipairs(recent) do if item~=member then kept[#kept+1]=item end end
        recent=kept
      end
    end
    local members,seen={},{}
    local candidates={identifier or false,previous or false}
    for _,m in ipairs(anchor_map[tunnel] or {}) do candidates[#candidates+1]=m end
    for _,m in ipairs(recent) do candidates[#candidates+1]=m end
    for _,m in ipairs(candidates) do if m and not seen[m] then seen[m]=true;members[#members+1]=m end end
    while #members>8 do table.remove(members) end
    local group_id=current and current.vendor_profile_group_id or nil
    if not profile_group(group_id) then group_id=nil end
    local group=canon.object({id=tunnel,protocol=string.match(tunnel,'^([^:]+)'),profile_group_id=group_id or NULL,
      profiles=canon.array({unpack(members)}),active_profiles=identifier and canon.array({identifier}) or canon.array(),
      current_profile=identifier or NULL,previous_profile=previous or NULL,state=state,generation=generation or NULL,
      changed_at=changed_at,stable_samples=stable,time=now,vendor_attempts_exhausted=NULL})
    if changed and (old.current_profile~=identifier or next(old)==nil or (old._fingerprint~=nil and fingerprint~=nil)) then
      local code
      if next(old)==nil then code='VENDOR-FIRST-OBSERVATION'
      elseif identifier~=old.current_profile and identifier then code='VENDOR-PROFILE-CHANGED'
      elseif identifier then code='VENDOR-BINDING-CHANGED' else code='VENDOR-BINDING-UNKNOWN' end
      self.events[#self.events+1]=canon.object({time=now,tunnel=tunnel,previous_profile=old.current_profile or NULL,
        current_profile=identifier or NULL,code=code,cause='UNOBSERVED'})
    end
    next_states[tunnel]={current_profile=identifier,previous_profile=previous,generation=generation,changed_at=changed_at,
      stable_samples=stable,time=now,state=state,_kernel=kernel,_fingerprint=fingerprint,_members=members}
    groups[#groups+1]=group
  end
  self.states=next_states
  while #self.events>50 do table.remove(self.events,1) end
  local sanitized={}
  for _,original in ipairs(rows) do
    local row={}
    for _,key in ipairs(M.MEASUREMENT_FIELDS) do if original[key]~=nil then row[key]=original[key] end end
    if row.probe_checks~=nil then row.probe_checks=M.probe_checks(row.probe_checks) end
    local identifier=row.id
    if not safe(identifier) then identifier=nil;row.id=NULL end
    local profile=identifier and before_ids[identifier] or nil
    local tunnel=M.tunnel_identity(profile)
    local group=tunnel and self.states[tunnel] or {}
    local matching=tunnel~=nil and pre[tunnel]==profile and post[tunnel]~=nil and post[tunnel].id==identifier and group.generation~=nil
    if not matching then
      for _,key in ipairs(M.HEALTH) do row[key]=nil end
      row.code=tunnel and 'VENDOR-IDENTITY-CHANGED' or 'VENDOR-IDENTITY-UNKNOWN'
    end
    row.vendor_tunnel_id=tunnel or NULL
    row.vendor_generation=matching and group.generation or NULL
    row.vendor_state=matching and (group.state or 'UNKNOWN') or 'UNKNOWN'
    row.vendor_changed_at=group.changed_at==nil and NULL or group.changed_at
    row.interface=profile and profile.interface or NULL
    sanitized[#sanitized+1]=row
  end
  local events=canon.array();for _,e in ipairs(self.events) do events[#events+1]=e end
  return canon.object({version=1,time=now,groups=groups,events=events,
    scope='configured tunnel identity and recent observed members; vendor queue, cause and exhausted attempts unobserved'}),sanitized
end

return M
