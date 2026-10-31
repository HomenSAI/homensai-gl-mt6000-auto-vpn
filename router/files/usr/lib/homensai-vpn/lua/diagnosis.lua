-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- diagnosis.lua: failure_diagnosis.py for the Lua supervisor (2.0.0-lua line): fresh, scoped_samples,
-- resolve_pair, diagnose. Pure functions over the decoded status.json; results equal the Python dicts.
local canon=require('canon')
local py=require('py')
local identity=require('identity')

local M={}
local NULL=canon.null
local isnone,eq,num=py.isnone,py.eq,canon.number

local function finite(v) return py.finite(v) end
M.finite=finite
function M.fresh(stamp,now,age)
  if not (finite(now) and num(now)>=0 and finite(stamp) and num(stamp)>=0) then return false end
  local d=num(now)-num(stamp)
  return 0<=d and d<=num(age)
end
local fresh=M.fresh
local function get(t,k) if not canon.is_object(t) then return nil end;local v=t[k];if v==NULL then return nil end;return v end

-- A rebound generation cannot borrow the former binding's health history.
function M.scoped_samples(samples,profile)
  local id=identity.profile_identity(profile)
  if not id or not canon.is_array(samples) then return canon.array({}) end
  local changed=get(profile,'vendor_changed_at')
  if not finite(changed) then return canon.array({}) end
  local points={}
  for _,point in ipairs(samples) do
    if canon.is_object(point) and eq(get(point,'id'),id.id) and finite(get(point,'time')) and num(point.time)>=num(changed)
       and eq(get(point,'interface'),id.interface) and eq(get(point,'vendor_tunnel_id'),id.vendor_tunnel_id)
       and eq(get(point,'vendor_generation'),id.vendor_generation) then
      points[#points+1]=point
    end
  end
  local seen={}
  for _,point in ipairs(points) do
    local stamp=num(point.time)
    local health=canon.array({point.code==nil and NULL or point.code,point.dns_ok==nil and NULL or point.dns_ok,point.https_success==nil and NULL or point.https_success})
    if seen[stamp]~=nil and not eq(seen[stamp],health) then return canon.array({}) end
    seen[stamp]=health
  end
  return canon.array(points)
end

local function boxed(x,like) if canon.is_float(like) then return canon.float(x) end;return x end

function M.resolve_pair(status,settings,now,max_age,settle_seconds)
  local coordination=canon.object({version=1,time=finite(now) and now or NULL,state='UNKNOWN',code='VENDOR-IDENTITY-UNKNOWN',
    source_tunnel=NULL,target_tunnel=NULL,transition=NULL,vendor_reason='UNOBSERVED',can_apply=false,vendor_attempts_exhausted=NULL,
    vendor_settle_seconds=settle_seconds,settle_until=NULL,scope='application planning gate; current configured tunnel identity only'})
  local result={source=NULL,target=NULL,coordination=coordination}
  local function refuse(code,state) coordination.code=code;coordination.state=state or 'UNKNOWN';return result end
  if not finite(max_age) or not (0<num(max_age) and num(max_age)<=900) or not finite(settle_seconds)
     or not (30<=num(settle_seconds) and num(settle_seconds)<=600) then return result end
  if not canon.is_object(status) or not canon.is_object(settings) then return refuse('OBSERVATION-STALE') end
  if py.truthy(status.error) or not fresh(get(status,'time'),now,max_age) then return refuse('OBSERVATION-STALE') end
  local rows=status.profiles
  if not canon.is_array(rows) or #rows>400 then return result end
  for _,row in ipairs(rows) do if not canon.is_object(row) then return result end end
  local by_id,count={},0
  for _,row in ipairs(rows) do
    local id=get(row,'id')
    if type(id)~='string' or id=='' then return result end
    if by_id[id] then return result end
    by_id[id]=row;count=count+1
  end
  local anchors={}
  for i,role in ipairs({'source','target'}) do
    local anchor=settings['plan_'..role..'_tunnel']
    if isnone(anchor) or anchor=='' then
      local selected=settings['plan_'..role]
      anchor=type(selected)=='string' and identity.tunnel_identity(by_id[selected]) or nil
    end
    if type(anchor)~='string' or not identity.tunnel_pattern(anchor) then return result end
    coordination[role..'_tunnel']=anchor;anchors[i]=anchor
  end
  if anchors[1]==anchors[2] then return refuse('VENDOR-SAME-TUNNEL','HOLD') end
  local function proto(a) return string.match(a,'^([^:]*):') end
  coordination.transition=proto(anchors[1])==proto(anchors[2]) and 'channel' or 'protocol'
  local observation=status.vendor_observation
  if not canon.is_object(observation) or not py.is_int(observation.version) or observation.version~=1
     or not fresh(get(observation,'time'),now,max_age) or not canon.is_array(observation.groups) then return result end
  local groups=observation.groups
  if #groups>400 then return result end
  for _,group in ipairs(groups) do if not canon.is_object(group) then return result end end
  local by_tunnel={}
  for _,group in ipairs(groups) do
    local id=group.id
    if type(id)~='string' or by_tunnel[id] then return result end
    by_tunnel[id]=group
  end
  local settle_until,settle_box=0,nil
  for i,role in ipairs({'source','target'}) do
    local anchor=anchors[i]
    local group=by_tunnel[anchor]
    if not group or not py.truthy(group) or not fresh(get(group,'time'),now,max_age) then return result end
    if group.state=='PENDING' then return refuse('VENDOR-SETTLING','HOLD') end
    if group.state~='SETTLED' then return result end
    local identifier,active=group.current_profile,group.active_profiles
    if type(identifier)~='string' or not (canon.is_array(active) and #active==1 and active[1]==identifier) or group.protocol~=proto(anchor) then return result end
    local row=by_id[identifier]
    local id=identity.profile_identity(row)
    if not id or id.vendor_tunnel_id~=anchor then return refuse('PROFILE-IDENTITY-CHANGED') end
    if not eq(id.vendor_generation,get(group,'generation')) then return refuse('PROFILE-IDENTITY-CHANGED') end
    if row.vendor_state=='PENDING' then return refuse('VENDOR-SETTLING','HOLD') end
    if row.vendor_state~='SETTLED' then return result end
    if not fresh(get(row,'time'),now,max_age) then return refuse('OBSERVATION-STALE') end
    local changed=get(group,'changed_at')
    if not finite(changed) or not (0<=num(changed) and num(changed)<=num(now)) or not eq(get(row,'vendor_changed_at'),changed)
       or not py.is_int(group.stable_samples) or group.stable_samples<2 then return result end
    local candidate=num(changed)+num(settle_seconds)
    if candidate>settle_until then settle_until=candidate;settle_box=boxed(candidate,canon.is_float(changed) and changed or settle_seconds) end
    result[role]=row
  end
  coordination.settle_until=settle_box or 0
  if num(now)<settle_until then return refuse('VENDOR-SETTLING','HOLD') end
  local uplink=status.uplink_observation
  if canon.is_object(uplink) and uplink.state=='DOWN' and fresh(get(uplink,'time'),now,max_age) then return refuse('UPLINK-LINK-DOWN','HOLD') end
  coordination.state='READY';coordination.code='CROSS-TUNNEL-READY'
  return result
end

function M.diagnose(status,source,now,settings)
  local pair=require('pair')
  local age
  if settings~=nil then age=pair.valid_for(settings)
  else
    local v=canon.is_object(status) and status.observation_valid_for or nil
    age=(py.is_int(v) and v>=30 and v<=900) and v or 90
  end
  local scope='current profile router probes; channel retry exhaustion and LAN confirmation unverified'
  local function result(code,suppress,next_action)
    local out={code=code,suppress_switch=suppress,scope=scope}
    if next_action then out.next_action=next_action end
    return out
  end
  if not canon.is_object(status) or py.truthy(status.error) or not fresh(get(status,'time'),now,age) then return result('OBSERVATION-STALE',true) end
  local uplink=status.uplink_observation
  if uplink==nil then uplink=canon.object({}) end
  if canon.is_object(uplink) and uplink.state=='DOWN' and fresh(get(uplink,'time'),now,age) then
    return result('UPLINK-LINK-DOWN',true,'Restore configured uplink; do not cycle VPN reserves.')
  end
  local profiles=status.profiles
  if profiles==nil then profiles=canon.array({}) end
  if not canon.is_array(profiles) then return result('OBSERVATION-UNKNOWN',true) end
  local rows={}
  for _,p in ipairs(profiles) do if canon.is_object(p) and eq(get(p,'id'),source) then rows[#rows+1]=p end end
  if #rows~=1 then return result('OBSERVATION-UNKNOWN',true) end
  local row=rows[1]
  if not py.truthy(row.interface) then return result('TUNNEL-DISCONNECTED',true) end
  if not fresh(get(row,'time'),now,age) then return result('OBSERVATION-STALE',true) end
  local code=get(row,'code')
  if code=='VENDOR-IDENTITY-CHANGED' then return result('PROFILE-IDENTITY-CHANGED',true) end
  if row.vendor_state=='PENDING' then return result('VENDOR-SETTLING',true) end
  if row.vendor_state=='UNKNOWN' then return result('VENDOR-IDENTITY-UNKNOWN',true) end
  if code=='ROUTE-001' then return result('ROUTE-MISMATCH',true) end
  if code=='CHECK-001' or code=='CHECK-LIMIT' then return result('PATH-UNVERIFIED',true) end
  if code=='VPN-001' then return result('TUNNEL-DISCONNECTED',false) end
  if code=='DNS-001' then return result('DNS-FAILED',false) end
  if code=='VPN-003' then return result('HTTPS-FAILED',false) end
  local successes=row.https_success
  if code==nil and row.dns_ok==true and py.is_int(successes) and successes>=2 then return result('VPN-PROBE-HEALTHY',false) end
  return result('OBSERVATION-UNKNOWN',true)
end

return M
