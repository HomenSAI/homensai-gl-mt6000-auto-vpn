-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- identity.lua: the policy identity of native_switch.py for the Lua supervisor (2.0.0-lua line).
-- Ports, byte for byte in their results:
--   process_policy   mark, validate, system_section, recognizes, selected_bindings, applied
--   stock_derived    anonymous, no_override_options, network_partition
--   native_switch    semantic_section, section_id, policy_order, policy_hash, choose
--   native_proof     requested;  vendor_observation.tunnel_identity;  failure_diagnosis.profile_identity
--   pair_interfaces  protocol, validate, roles, selection, state;  device_profile detect/validate
--   recovery_settings.fingerprint
-- Errors: Python's Refused -> ctl.refuse(code); Python's ValueError -> value_error(code) (a refusal with
-- value_error=true), so a caller can tell them apart like the Python except clauses do.
-- digest(value) is canon.digest unless the caller installs a memo (backend.lua does: the same section texts
-- are hashed on every order() call, and sha256 may be a process on the router).
local canon=require('canon')
local ctl=require('auto_control')
local py=require('py')

local M={}
local NULL=canon.null
local isnone,eq=py.isnone,py.eq
local refuse=ctl.refuse
local function value_error(code) error(setmetatable({code=code,value_error=true},ctl.Refused),0) end
M.value_error=value_error
M.digest=canon.digest
function M.set_digest(fn) M.digest=fn end

local function full(s,pattern) return type(s)=='string' and string.find(s,'^'..pattern..'$')~=nil end
local function get(t,k) if type(t)~='table' then return nil end;local v=t[k];if v==NULL then return nil end;return v end

------------------------------------------------------------------------------------------------------
-- process_policy
------------------------------------------------------------------------------------------------------
function M.mark(value)
  if type(value)~='string' then value_error('POLICY-IDENTITY-CHANGED') end
  local number
  if string.find(value,'^0x%x+$') and #value<=10 then number=tonumber(string.sub(value,3),16)
  elseif string.find(value,'^%d+$') and #value<=10 then number=tonumber(value,10)
  else value_error('POLICY-IDENTITY-CHANGED') end
  if not (number>0 and number<=0xffffffff) then value_error('POLICY-IDENTITY-CHANGED') end
  return number
end

local function binding_name(k) return type(k)=='string' and (string.find(k,'^wgclient%d+$') or string.find(k,'^ovpnclient%d+$'))
  and #string.match(k,'%d+$')<=4 end
function M.validate(bindings)
  if isnone(bindings) then return nil end
  if not canon.is_object(bindings) then value_error('POLICY-IDENTITY-CHANGED') end
  local count,values,distinct={},{},0
  local n=0
  for k,v in pairs(bindings) do
    n=n+1
    if not binding_name(k) or not py.is_int(v) or not (v>0 and v<=0xffffffff) then value_error('POLICY-IDENTITY-CHANGED') end
    if not values[v] then values[v]=true;distinct=distinct+1 end
  end
  if n~=2 or distinct~=2 then value_error('POLICY-IDENTITY-CHANGED') end
  local out=canon.object({})
  for k,v in pairs(bindings) do out[k]=v end
  return out
end

function M.system_section(section)
  return get(section,'.name')=='gl_process_vpn' and get(section,'.type')=='rule_process' and get(section,'enabled')=='1'
    and get(section,'from_type')=='process_gid'
end

function M.recognizes(section,bindings)
  if bindings==nil or not M.system_section(section) then return false end
  local via=get(section,'via')
  if type(via)~='string' or bindings[via]==nil then return false end
  local ok,value=pcall(M.mark,get(section,'mark'))
  return ok and value==bindings[via]
end

function M.selected_bindings(sections,interfaces)
  local system={}
  for _,s in ipairs(sections) do if get(s,'.name')=='gl_process_vpn' then system[#system+1]=s end end
  if #system==0 or not M.system_section(system[1]) then return nil end
  if #system~=1 then value_error('POLICY-DUPLICATE-IDENTITY') end
  local result=canon.object({})
  for _,interface in ipairs(interfaces) do
    local rows={}
    for _,s in ipairs(sections) do
      if get(s,'.type')=='rule' and get(s,'enabled')=='1' and eq(get(s,'via'),interface) then rows[#rows+1]=s end
    end
    if #rows~=1 then value_error('POLICY-IDENTITY-CHANGED') end
    result[interface]=M.mark(get(rows[1],'mark'))
  end
  result=M.validate(result)
  if not M.recognizes(system[1],result) then value_error('POLICY-IDENTITY-CHANGED') end
  return result
end

local function first_vpn_rule(sections)
  for _,s in ipairs(sections) do
    if get(s,'.type')=='rule' and get(s,'enabled')=='1' and get(s,'via')~='novpn' then return s end
  end
  return nil
end
local function system_of(sections)
  for _,s in ipairs(sections) do if get(s,'.name')=='gl_process_vpn' then return s end end
  return nil
end
M.first_vpn_rule,M.system_of=first_vpn_rule,system_of

-- applied(): after RTP the first enabled VPN rule must be the process binding (ValueError on a bad mark).
function M.applied(sections,bindings)
  if bindings==nil then return true end
  local first,system=first_vpn_rule(sections),system_of(sections)
  if not (first and system and M.recognizes(system,bindings) and eq(get(system,'via'),get(first,'via'))) then return false end
  return M.mark(get(system,'mark'))==M.mark(get(first,'mark'))
end

------------------------------------------------------------------------------------------------------
-- stock_derived
------------------------------------------------------------------------------------------------------
function M.anonymous(value) return value==true or value=='1' end

local SELECTORS={'from_type','from','to_type','to','to_manual','to_list_external'}
local function empty_selector(v) return isnone(v) or v=='' or (canon.is_array(v) and #v==0) end
M.empty_selector=empty_selector

function M.no_override_options(section,bindings)
  local ok,b=pcall(M.validate,bindings)
  if not ok then return false end
  bindings=b
  local via=get(section,'via')
  if bindings==nil or type(via)~='string' or bindings[via]==nil or not M.anonymous(get(section,'.anonymous'))
     or get(section,'.type')~='rule' or get(section,'enabled')~='1' or get(section,'killswitch')~='1'
     or get(section,'options_in_used')~='0' then return false end
  for _,key in ipairs({'mtu','masq','local_access'}) do if section[key]~=nil then return false end end
  for _,key in ipairs(SELECTORS) do if not empty_selector(section[key]) then return false end end
  local mok,value=pcall(M.mark,get(section,'mark'))
  if not mok or value~=bindings[via] then return false end
  local function digits(v) return type(v)=='string' and string.find(v,'^%d+$')~=nil and #v<=10 end
  if get(section,'via_type')=='wireguard' then
    return string.find(via,'^wgclient[1-5]$')~=nil and digits(get(section,'peer_id'))
  end
  if get(section,'via_type')=='openvpn' then
    local client=section.client_id
    if client==nil then client=section.peer_id end
    if client==NULL then client=nil end
    return string.find(via,'^ovpnclient[1-5]$')~=nil and digits(get(section,'group_id')) and digits(client)
  end
  return false
end

function M.network_partition(rows)
  local result=canon.object({ipv4_rules=canon.array({}),other_sections=canon.array({})})
  for _,original in ipairs(rows) do
    local row=py.copy(original)
    local name=get(row,'.name')
    if M.anonymous(get(row,'.anonymous')) and type(name)=='string' and string.find(name,'^cfg%x+$') and #name>=9 and #name<=19 then
      row['.name']=nil
    end
    local list=get(row,'.type')=='rule' and result.ipv4_rules or result.other_sections
    list[#list+1]=row
  end
  return result
end

------------------------------------------------------------------------------------------------------
-- native_switch policy identity
------------------------------------------------------------------------------------------------------
function M.semantic_section(section,bindings)
  local anonymous=M.anonymous(section['.anonymous'])  -- `in (True,'1')`
  local derived=M.recognizes(section,bindings)
  local options=M.no_override_options(section,bindings)
  local out=canon.object({})
  for k,v in pairs(section) do
    if not (k=='.index' or k=='name' or (anonymous and k=='.name') or (derived and (k=='via' or k=='mark'))
            or (options and k=='options_in_used')) then
      out[k]=v
    end
  end
  return out
end

function M.section_id(section,bindings)
  if M.anonymous(section['.anonymous']) then return 'a_'..string.sub(M.digest(M.semantic_section(section,bindings)),1,60) end
  local name=section['.name']
  if name==nil then value_error('POLICY-READ-FAILED') end  -- KeyError in Python
  return name
end

function M.policy_order(sections,bindings)
  local values,seen={},{}
  for i,s in ipairs(sections) do
    local id=M.section_id(s,bindings)
    if type(id)~='string' then value_error('POLICY-READ-FAILED') end
    if seen[id] then refuse('POLICY-DUPLICATE-IDENTITY') end
    seen[id]=true;values[i]=id
  end
  return canon.array(values)
end

function M.policy_hash(sections,bindings)
  M.policy_order(sections,bindings)
  bindings=M.validate(bindings)
  local rows={}
  for i,s in ipairs(sections) do local value=M.semantic_section(s,bindings);rows[i]={value=value,key=M.digest(value)} end
  table.sort(rows,function(a,b) return a.key<b.key end)
  local values={}
  for i,row in ipairs(rows) do values[i]=row.value end
  values=canon.array(values)
  if bindings==nil then return M.digest(values) end
  return M.digest(canon.object({sections=values,process_bindings=bindings}))
end

------------------------------------------------------------------------------------------------------
-- native_proof / vendor_observation / failure_diagnosis identities
------------------------------------------------------------------------------------------------------
M.EXTERNAL,M.HOSTED,M.ROUTER='external-lan','router-hosted-ipv4','router-probed-ipv4'
function M.requested(settings)
  if not canon.is_object(settings) then value_error('LAN-TRIAL-REQUIRED') end
  local value=settings.native_proof_scope
  if value==nil then value=M.EXTERNAL end
  if type(value)~='string' or not (value==M.EXTERNAL or value==M.HOSTED or value==M.ROUTER) then value_error('LAN-TRIAL-REQUIRED') end
  if value==M.ROUTER and get(settings,'pair_auto_mode')~=M.ROUTER then value_error('PAIR-MODE-NOT-CONFIGURED') end
  return value
end

local function tunnel_pattern(v)  -- ^(openvpn|wireguard):[A-Za-z0-9_.-]{1,64}$
  if type(v)~='string' then return false end
  local proto,name=string.match(v,'^([a-z]+):(.*)$')
  return (proto=='openvpn' or proto=='wireguard') and name~=nil and #name>=1 and #name<=64 and string.find(name,'^[A-Za-z0-9_.-]+$')~=nil
end
M.tunnel_pattern=tunnel_pattern
local function safe_id(v) return type(v)=='string' and #v>=1 and #v<=96 and string.find(v,'^[A-Za-z0-9_.:-]+$')~=nil end
M.safe_id=safe_id

function M.tunnel_identity(profile)
  if not canon.is_object(profile) then return nil end
  local protocol,logical,claimed,identifier=get(profile,'protocol'),get(profile,'interface'),get(profile,'vendor_tunnel_id'),get(profile,'id')
  if not (protocol=='openvpn' or protocol=='wireguard') or type(logical)~='string' or type(claimed)~='string'
     or not tunnel_pattern(claimed) or claimed~=protocol..':'..logical or not safe_id(identifier)
     or string.sub(identifier,1,#protocol+1)~=protocol..':' or identifier==protocol..':' then return nil end
  if profile.section~=nil and identifier~=protocol..':'..py.str(profile.section) then return nil end
  return claimed
end

M.PROFILE_KEYS={'id','protocol','interface','vendor_tunnel_id','vendor_generation'}
function M.profile_identity(profile)
  local tunnel=M.tunnel_identity(profile)
  local generation=canon.is_object(profile) and get(profile,'vendor_generation') or nil
  if not tunnel or type(generation)~='string' or not string.find(generation,'^[a-f0-9]+$') or #generation~=32 then return nil end
  local out=canon.object({})
  for _,key in ipairs(M.PROFILE_KEYS) do local v=profile[key];out[key]=v==nil and NULL or v end
  return out
end

------------------------------------------------------------------------------------------------------
-- choose(): fail closed on policy layouts outside the supported small subset
------------------------------------------------------------------------------------------------------
local function constrained(s)
  for _,k in ipairs(SELECTORS) do
    local v=s[k]
    if not (isnone(v) or v=='' or (canon.is_array(v) and #v==0)) then return true end
  end
  return false
end
M.constrained=constrained

function M.choose(data,profiles)
  local sections,settings=data.sections,data.settings
  if not canon.is_array(sections) or not canon.is_object(settings) then value_error('POLICY-READ-FAILED') end
  local ok,scope=pcall(M.requested,settings)
  if not ok then refuse(scope.code) end
  local defaults,global={},{}
  for _,s in ipairs(sections) do
    if get(s,'.type')=='default' then defaults[#defaults+1]=s end
    if get(s,'.name')=='global' then global[#global+1]=s end
  end
  if #defaults~=1 or get(defaults[1],'enabled')~='0' then refuse('DIRECT-WAN-FALLBACK') end
  if #global~=1 or get(global[1],'enabled')~='1' then refuse('VPN-POLICY-DISABLED') end
  if data.ipv6~='0' then refuse('IPV6-NOT-EXPLICITLY-DISABLED') end
  local fw=data.firewall_defaults
  if canon.is_array(fw) then
    for _,s in ipairs(fw) do
      for _,k in ipairs({'flow_offloading','flow_offloading_hw'}) do
        local v=s[k];if v==nil then v='0' end
        if not (v=='0' or v==NULL) then refuse('FLOW-OFFLOAD-ENABLED') end
      end
    end
  end
  local generic,special={},{}
  for index,s in ipairs(sections) do
    if get(s,'.type')=='rule' and get(s,'enabled')=='1' then
      if get(s,'killswitch')~='1' then refuse('KILLSWITCH-NOT-ENABLED') end
      local list=constrained(s) and special or generic
      list[#list+1]={index=index,row=s}
    end
  end
  if #generic<2 or #generic>16 then refuse('TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED') end
  for i,g in ipairs(generic) do if g.index~=generic[1].index+i-1 then refuse('GENERIC-RULES-NOT-ADJACENT') end end
  local vias,count={},0
  for _,g in ipairs(generic) do
    local via=g.row.via;local key=isnone(via) and '\0none' or via
    if type(key)~='string' then value_error('POLICY-READ-FAILED') end
    if not vias[key] then vias[key]=true;count=count+1 end
  end
  if count~=#generic then refuse('GENERIC-DUPLICATE-INTERFACE') end
  for _,s in ipairs(special) do if s.index>generic[1].index then refuse('SPECIAL-RULES-MUST-PRECEDE-GENERIC') end end
  local pmap,np={},0
  for _,p in ipairs(profiles) do
    local id=p.id
    if type(id)~='string' then value_error('POLICY-READ-FAILED') end
    if not pmap[id] then np=np+1 end
    pmap[id]=p
  end
  if np~=#profiles then refuse('VENDOR-IDENTITY-UNKNOWN') end
  local selected={}
  for i,role in ipairs({'source','target'}) do
    local anchor=settings['plan_'..role..'_tunnel']
    local profile
    if isnone(anchor) or anchor=='' then
      local id=settings['plan_'..role]
      profile=type(id)=='string' and pmap[id] or nil
    else
      if type(anchor)~='string' or not tunnel_pattern(anchor) then refuse('VENDOR-IDENTITY-UNKNOWN') end
      local matches={}
      for _,p in ipairs(profiles) do if M.tunnel_identity(p)==anchor then matches[#matches+1]=p end end
      if #matches~=1 then refuse('VENDOR-IDENTITY-UNKNOWN') end
      profile=matches[1]
    end
    selected[i]=profile
  end
  local source,target=selected[1],selected[2]
  if not source or not target or eq(source.id,target.id) then refuse('SOURCE-RESERVE-NOT-CONFIGURED') end
  if not py.truthy(source.interface) or not py.truthy(target.interface) then refuse('PROFILE-INACTIVE') end
  local st,tt=M.tunnel_identity(source),M.tunnel_identity(target)
  if not st or not tt then refuse('VENDOR-IDENTITY-UNKNOWN') end
  if st==tt then refuse('VENDOR-SAME-TUNNEL') end
  local byvia={}
  for _,g in ipairs(generic) do local via=g.row.via;if type(via)=='string' then byvia[via]=g end end
  if not byvia[source.interface] or not byvia[target.interface] then refuse('PROFILES-NOT-GENERIC-RULES') end
  if source.interface==target.interface then refuse('SAME-INTERFACE') end
  local direction=settings.native_order_direction
  if direction~='first' and direction~='last' then refuse('POLICY-ORDER-DIRECTION-UNVERIFIED') end
  local bok,bindings=pcall(M.selected_bindings,sections,{source.interface,target.interface})
  if not bok then refuse(bindings.code) end
  local identities={source=M.profile_identity(source),target=M.profile_identity(target)}
  local generic_ids={}
  for i,g in ipairs(generic) do generic_ids[i]=M.section_id(g.row,bindings) end
  return canon.object({source=source,target=target,source_rule=M.section_id(byvia[source.interface].row,bindings),
    target_rule=M.section_id(byvia[target.interface].row,bindings),order=M.policy_order(sections,bindings),
    hash=M.policy_hash(sections,bindings),direction=direction,generic_rules=canon.array(generic_ids),
    process_bindings=bindings==nil and NULL or bindings,proof_scope=scope,
    vendor_identity=(identities.source and identities.target) and M.digest(canon.object(identities)) or NULL})
end

------------------------------------------------------------------------------------------------------
-- pair_interfaces / device_profile / recovery_settings
------------------------------------------------------------------------------------------------------
function M.protocol(name)
  if type(name)~='string' then value_error('PAIR-PROFILES-UNVERIFIED') end
  local kind,number=string.match(name,'^(%a+)([1-9]%d*)$')
  if not (kind=='wgclient' or kind=='ovpnclient') or #number>4 then value_error('PAIR-PROFILES-UNVERIFIED') end
  return kind
end
function M.validate_interfaces(values)
  if not canon.is_object(values) then value_error('PAIR-PROFILES-UNVERIFIED') end
  local n=0
  for name,proto in pairs(values) do n=n+1;if M.protocol(name)~=proto then value_error('PAIR-PROFILES-UNVERIFIED') end end
  if n~=2 then value_error('PAIR-PROFILES-UNVERIFIED') end
  local out=canon.object({});for k,v in pairs(values) do out[k]=v end
  return out
end
function M.roles(settings)
  local result=canon.object({})
  for _,pair_ in ipairs({{'source','wgclient1'},{'target','ovpnclient1'}}) do
    local role,legacy=pair_[1],pair_[2]
    local anchor=canon.is_object(settings) and settings['plan_'..role..'_tunnel'] or nil
    if not py.truthy(anchor) then result[role]=legacy
    else
      if type(anchor)~='string' then value_error('PAIR-PROFILES-UNVERIFIED') end
      local _,colons=string.gsub(anchor,':',':')
      if colons~=1 then value_error('PAIR-PROFILES-UNVERIFIED') end
      local kind,name=string.match(anchor,'^(.*):(.*)$')
      local proto=M.protocol(name)
      if kind~=(proto=='wgclient' and 'wireguard' or 'openvpn') then value_error('PAIR-PROFILES-UNVERIFIED') end
      result[role]=name
    end
  end
  local check=canon.object({})
  for _,name in pairs(result) do check[name]=M.protocol(name) end
  M.validate_interfaces(check)
  return result
end
function M.selection_interfaces(rows)
  local result=canon.object({})
  for _,role in ipairs({'source','target'}) do
    local row=rows[role]
    if row==nil then row=canon.object({}) end
    if not canon.is_object(row) then value_error('PAIR-PROFILES-UNVERIFIED') end
    local name=get(row,'interface');local proto=M.protocol(name)
    local p=get(row,'protocol')
    if p~=nil and p~=(proto=='wgclient' and 'wireguard' or 'openvpn') then value_error('PAIR-PROFILES-UNVERIFIED') end
    result[name]=proto
  end
  return M.validate_interfaces(result)
end
M.LEGACY=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'})
function M.state_interfaces(value)
  local v=value.interfaces
  if v==nil then v=M.LEGACY end
  return M.validate_interfaces(v)
end

M.BOARDS={['glinet,gl-mt6000']='mt6000',['glinet,mt3000-snand']='mt3000'}
function M.detect(text)  -- text: the first 128 bytes of /tmp/sysinfo/board_name, or nil
  if type(text)~='string' then return 'unknown' end
  if string.find(text,'[\128-\255]') then return 'unknown' end  -- encoding='ascii'
  return M.BOARDS[string.match(text,'^%s*(.-)%s*$')] or 'unknown'
end
function M.validate_model(value,detected)
  if type(value)~='string' or not (value=='auto' or value=='mt6000' or value=='mt3000') then value_error('DEVICE-MODEL-INVALID') end
  if value~='auto' and value~=detected then value_error('DEVICE-MODEL-MISMATCH') end
  return value
end

function M.fingerprint(settings)
  local normalized=require('pair').recovery_normalized(settings)
  local out=canon.object({})
  for k,v in pairs(normalized) do out[k]=v end
  return canon.sha256(canon.encode(out))
end

return M
