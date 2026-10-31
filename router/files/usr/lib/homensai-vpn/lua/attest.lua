-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- attest.lua: kernel_policy.py (static_bindings, rule_bindings, attest, missing_only, unrouted) for the Lua
-- supervisor (2.0.0-lua line), over kernel.lua's parse_mangle/fields/shlex. Any form the Python code does not
-- accept raises (ValueError in Python, value_error here): the caller turns it into KERNEL-POLICY-UNVERIFIED.
-- Every check is the Python one; nothing is accepted that kernel_policy.attest would refuse.
local canon=require('canon')
local kernel=require('kernel')
local py=require('py')
local identity=require('identity')

local M={}
local NULL=canon.null
M.MASK=0xf000
local MASK_TEXT='61440'
local isnone,eq=py.isnone,py.eq
local function bad() identity.value_error('KERNEL-POLICY-UNVERIFIED') end
local function get(t,k) if type(t)~='table' then return nil end;local v=t[k];if v==NULL then return nil end;return v end

-- kernel_policy.number: an int, or a hex/decimal string
function M.number(value)
  if type(value)=='number' and value%1==0 then return value end
  if type(value)~='string' then bad() end
  local ok,x=pcall(kernel.number,value)
  if not ok then bad() end
  return x
end
function M.numeric(value)
  local ok,x=pcall(kernel.numeric,value)
  if not ok then bad() end
  return x
end

-- parse_mangle(text) -> chains (name -> list of token lists), names in file order
function M.parse(text)
  if type(text)~='string' or #text>2*1024*1024 then bad() end
  local ok,chains,order=pcall(kernel.parse_mangle,{lines=require('fast_policy').splitlines(text)})
  if not ok then bad() end
  return chains,order
end
-- The parsed graph as Python's parse_mangle dict (canon types), for kernel_fingerprint digests.
function M.as_value(chains)
  local out=canon.object({})
  for name,rules in pairs(chains) do
    local list={}
    for i,tokens in ipairs(rules) do local t={};for j,x in ipairs(tokens) do t[j]=x end;list[i]=canon.array(t) end
    out[name]=canon.array(list)
  end
  return out
end

local function fields(tokens)
  local ok,f=pcall(kernel.fields,tokens)
  if not ok then bad() end
  return f
end
M.fields=fields
-- dict equality for fields() results ('-m' is a sorted list; Python a tuple: compared element-wise)
local function same(a,b)
  for k,v in pairs(a) do
    local w=b[k]
    if type(v)=='table' then
      if type(w)~='table' or #v~=#w then return false end
      for i=1,#v do if v[i]~=w[i] then return false end end
    elseif v~=w then return false end
  end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end
M.same=same
local function count_of(list,value) local n=0;for _,e in ipairs(list) do if same(e,value) then n=n+1 end end;return n end
local function iface(v) return type(v)=='string' and #v>=1 and #v<=15 and string.find(v,'^[A-Za-z0-9_.-]+$')~=nil end

------------------------------------------------------------------------------------------------------
-- static_bindings: the pinned setup_instance/RTP slot contract (a client that was never UP too)
------------------------------------------------------------------------------------------------------
function M.static_bindings(selection,network)
  if not canon.is_array(network) then bad() end
  local rows,n={},0
  for _,row in ipairs(network) do
    if canon.is_object(row) then
      local name=row['.name'];local key=name==nil and '\0none' or name
      if type(key)=='string' then if rows[key]==nil then n=n+1 end;rows[key]=row else bad() end
    end
  end
  if n~=#network then bad() end
  local result=py.copy(selection)
  for _,role in ipairs({'source','target'}) do
    local profile=result[role]
    local interface=get(profile,'interface')
    local proto,index=string.match(type(interface)=='string' and interface or '','^(%a+)([1-5])$')
    if not (proto=='wgclient' or proto=='ovpnclient') then bad() end
    index=tonumber(index)
    local protocol=proto=='wgclient' and 'wireguard' or 'openvpn'
    local identifier=get(profile,'id') or ''
    if type(identifier)~='string' then bad() end
    local prefix=protocol..':'
    local config=string.sub(identifier,1,#prefix)==prefix and string.sub(identifier,#prefix+1) or ''
    local config_ok
    if protocol=='wireguard' then config_ok=string.find(config,'^peer_%d+$')~=nil else config_ok=string.find(config,'^%d+_%d+$')~=nil end
    if not config_ok or get(profile,'protocol')~=protocol or get(profile,'vendor_tunnel_id')~=protocol..':'..interface then bad() end
    local expected_mark=((proto=='wgclient' and 1 or 10)+index-1)*4096
    local table_=tostring((proto=='wgclient' and 1000 or 1010)+index)
    local row=rows[interface] or canon.object({});local rule=rows['rt_'..interface] or canon.object({})
    local mark_text=rule.mark;if mark_text==nil then mark_text='' end
    if get(row,'.type')~='interface' or get(row,'proto')~=proto or get(row,'config')~=config or get(row,'ip4table')~=table_
       or get(rule,'.type')~='rule' or M.numeric(py.str(mark_text))~=string.format('%d/%s',expected_mark,MASK_TEXT)
       or py.str(rule.lookup)~=table_ or py.str(rule.priority)~='6000' then bad() end
    local binding=profile.kernel_binding
    if binding==nil then binding=canon.object({}) end
    if get(binding,'code')=='VPN-001' then
      profile.kernel_binding=canon.object({code=NULL,mark=expected_mark,table=table_,declared_down=true})
    elseif not isnone(get(binding,'code')) or not eq(get(binding,'mark'),expected_mark) or get(binding,'table')~=table_ then bad() end
  end
  return result
end

------------------------------------------------------------------------------------------------------
-- rule_bindings: the routing rules that carry each selected mark
------------------------------------------------------------------------------------------------------
local function split_mark(raw)
  local mark,mask=string.match(raw,'^([^/]*)/(.*)$')
  if mark then return mark,true,mask end
  return raw,false,''
end

function M.rule_bindings(selection,marks,ip_rules)
  if not canon.is_array(ip_rules) or #ip_rules>400 then bad() end
  for _,row in ipairs(ip_rules) do if not canon.is_object(row) or not py.is_int(row.priority) then bad() end end
  for i=2,#ip_rules do if ip_rules[i].priority<ip_rules[i-1].priority then bad() end end
  local allowed={priority=true,src=true,dst=true,fwmark=true,fwmask=true,table=true,protocol=true}
  for _,key in ipairs({'source','target'}) do
    local profile=selection[key]
    local binding=get(profile,'kernel_binding') or canon.object({})
    local value=marks[selection[key..'_rule']]
    if value==nil then bad() end
    if not isnone(get(binding,'code')) or not eq(get(binding,'mark'),value) or type(get(binding,'table'))~='string' then bad() end
    local matching={}
    for index,row in ipairs(ip_rules) do
      if not isnone(row.fwmark) then
        local raw_mark,separator,raw_mask=split_mark(py.str(row.fwmark))
        if M.number(raw_mark)==value then
          local mask
          if separator then mask=M.number(raw_mask) else local m=row.fwmask;if m==nil then m=0xffffffff end;mask=M.number(m) end
          local foreign=false
          for k in pairs(row) do if not allowed[k] then foreign=true end end
          local src,dst=row.src,row.dst
          if src==nil then src='all' end;if dst==nil then dst='all' end
          if mask~=M.MASK or py.str(row.table)~=binding.table or foreign or row.priority>=9910
             or not (src=='all' or src=='0.0.0.0/0') or not (dst=='all' or dst=='0.0.0.0/0') then bad() end
          matching[#matching+1]=index
        end
      end
    end
    if #matching~=1 then bad() end
    for i=1,matching[1]-1 do
      local prior=ip_rules[i]
      local skip=false
      if not isnone(prior.fwmark) then
        local raw_mark,separator,raw_mask=split_mark(py.str(prior.fwmark))
        local mask
        if separator then mask=M.number(raw_mask) else local m=prior.fwmask;if m==nil then m=0xffffffff end;mask=M.number(m) end
        local applies=M.band(value,mask)==M.band(M.number(raw_mark),mask)
        if prior['not']~=nil then applies=not applies end
        if not applies then skip=true end
      end
      if not skip then
        if prior['not']==nil and type(prior.iif)=='string' and prior.iif~='br-lan' then skip=true end
      end
      if not skip then
        local exact0=eq(prior,canon.object({priority=0,src='all',table='local'}))
        local exact800=eq(prior,canon.object({priority=800,src='all',table='9910',suppress_prefixlen=0}))
        if not (exact0 or exact800) then bad() end
      end
    end
  end
end

-- bitwise and of two non-negative integers below 2^53
function M.band(a,b)
  local result,bit=0,1
  while a>0 and b>0 do
    local x,y=a%2,b%2
    if x==1 and y==1 then result=result+bit end
    a=(a-x)/2;b=(b-y)/2;bit=bit*2
  end
  return result
end

local function marks_of(policy,selection,generic)
  local sections={}
  for _,row in ipairs(policy.sections) do sections[identity.section_id(row,get(selection,'process_bindings'))]=row end
  return sections
end

------------------------------------------------------------------------------------------------------
-- attest(): the pinned FW3 catch-all packet-mark path of new IPv4 LAN flows
------------------------------------------------------------------------------------------------------
function M.attest(policy,selection,mangle,ip_rules)
  local P=require('pair').policy
  local proof=P.proof(selection)
  local selected=P.role(proof,selection.order)
  if proof.direction~='first' then bad() end
  local chains=M.parse(mangle)
  if not canon.is_array(ip_rules) or #ip_rules>400 then bad() end
  local prerouting={}
  for i,tokens in ipairs(chains.PREROUTING or {}) do prerouting[i]=fields(tokens) end
  if count_of(prerouting,{['-j']='VPN_PREROUTING_HOOK'})~=1 then bad() end
  local function harmless(chain,seen)
    if seen[chain] or not chains[chain] then bad() end
    for _,tokens in ipairs(chains[chain]) do
      local entry=fields(tokens);local target=entry['-j']
      if not (target=='TTL' or target=='TCPMSS' or target=='RETURN') then
        if target~='PORTAL_TTL' then bad() end
        local next_seen={};for k in pairs(seen) do next_seen[k]=true end;next_seen[chain]=true
        harmless(target,next_seen)
      end
    end
  end
  for _,entry in ipairs(prerouting) do
    if same(entry,{['-j']='VPN_PREROUTING_HOOK'}) then
    elseif entry['-j']=='TCPMSS' or entry['-j']=='TTL' then
    elseif entry['-j']=='PORTAL_TTL' then harmless('PORTAL_TTL',{})
    else bad() end
  end
  local hook={}
  for i,tokens in ipairs(chains.VPN_PREROUTING_HOOK or {}) do hook[i]=fields(tokens) end
  if count_of(hook,{['-i']='br-lan',['-j']='ROUTE_POLICY'})~=1 then bad() end
  for _,entry in ipairs(hook) do
    local target=entry['-j']
    if same(entry,{['-i']='br-lan',['-j']='ROUTE_POLICY'}) then
    elseif target~=nil and same(entry,{['-j']=target}) and (target=='vpn_in_new_mark' or target=='wan_in_new_mark') then
      if not chains[target] then bad() end
      for _,tokens in ipairs(chains[target]) do
        local ingress=fields(tokens);local interface=ingress['-i']
        if not interface or interface=='br-lan' or not iface(interface) then bad() end
      end
    elseif target=='CONNMARK' and entry['--save-mark']==true and entry['--restore-mark']==nil then
    elseif entry['-i']~=nil and entry['-i']~='br-lan' and iface(entry['-i']) then
    else bad() end
  end
  local sections=marks_of(policy,selection)
  local generic={}
  local position={}
  for i,id in ipairs(selection.order) do position[id]=i end
  for i,id in ipairs(proof.generic_rules) do
    if position[id]==nil then bad() end
    generic[i]=id
  end
  table.sort(generic,function(a,b) return position[a]<position[b] end)
  local expected,marks={},{}
  local zero='0/'..MASK_TEXT
  for _,rule_id in ipairs(generic) do
    local row=sections[rule_id]
    if row==nil then bad() end
    local tunnel=get(row,'tunnel_id')
    if type(tunnel)~='string' or not string.find(tunnel,'^%d+$') or #tunnel>12 then bad() end
    local chain='TUNNEL'..tunnel..'_ROUTE_POLICY'
    expected[#expected+1]={['-m']={'addrtype'},['! --dst-type']='LOCAL',['-j']=chain}
    local ok,value=pcall(identity.mark,get(row,'mark'))
    if not ok then bad() end
    marks[rule_id]=value
    local wanted={{['-m']={'mark'},['--mark']=zero,['-j']='MARK',['--set-xmark']=string.format('%d/%s',value,MASK_TEXT)},
                  {['-m']={'mark'},['--mark']=zero,['-j']='DROP'}}
    local rules=chains[chain] or {}
    if #rules~=#wanted then bad() end
    for i,tokens in ipairs(rules) do if not same(fields(tokens),wanted[i]) then bad() end end
  end
  local route={}
  for i,tokens in ipairs(chains.ROUTE_POLICY or {}) do route[i]=fields(tokens) end
  local restore={['-m']={'connmark'},['! --mark']=zero,['-j']='CONNMARK',['--restore-mark']=true,['--nfmask']=MASK_TEXT,['--ctmask']=MASK_TEXT}
  local dns={['-m']={'addrtype','udp'},['--dst-type']='LOCAL',['-p']='udp',['--dport']='53',['-j']='RETURN'}
  local want={restore,dns}
  for _,e in ipairs(expected) do want[#want+1]=e end
  if #route~=#want then bad() end
  for i=1,#want do if not same(route[i],want[i]) then bad() end end
  M.rule_bindings(selection,marks,ip_rules)
  local order={};for i,x in ipairs(selection.order) do order[i]=x end
  return canon.object({verified=true,role=selected,profile_id=selection[selected].id,policy_hash=selection.hash,order=canon.array(order),
    scope='new IPv4 LAN catch-all marking; no external-client proof'})
end

-- missing_only(): only wholly absent stock chains with an otherwise understood LAN hook may be repaired.
function M.missing_only(policy,selection,mangle,ip_rules)
  local P=require('pair').policy
  local proof=P.proof(selection)
  P.role(proof,selection.order)
  local chains=M.parse(mangle)
  for name in pairs(chains) do
    if name=='VPN_PREROUTING_HOOK' or name=='ROUTE_POLICY' or name=='LOCAL_POLICY' or name=='POST_ROUTE_POLICY' or string.sub(name,1,6)=='TUNNEL' then return false end
  end
  local sections=marks_of(policy,selection)
  local marks={}
  for _,key in ipairs(proof.generic_rules) do
    local row=sections[key]
    if row==nil then bad() end
    local ok,value=pcall(identity.mark,get(row,'mark'))
    if not ok then bad() end
    marks[key]=value
  end
  M.rule_bindings(selection,marks,ip_rules)
  local function safe(chain,seen)
    if seen[chain] or not chains[chain] then return false end
    for _,tokens in ipairs(chains[chain]) do
      local entry=fields(tokens);local target=entry['-j']
      if target=='TTL' or target=='TCPMSS' or (target=='RETURN' and chain~='PREROUTING') then
      else
        local ok=false
        if target=='PORTAL_TTL' then
          local next_seen={};for k in pairs(seen) do next_seen[k]=true end;next_seen[chain]=true
          ok=safe(target,next_seen)
        end
        if not ok then return false end
      end
    end
    return true
  end
  return proof.direction=='first' and safe('PREROUTING',{})
end

-- unrouted(): what rtp2.sh leaves after its flush and before any TUNNEL route chain exists.
function M.unrouted(text)
  local chains=M.parse(text)
  for name in pairs(chains) do if string.sub(name,1,6)=='TUNNEL' then return false end end
  local pending,seen={'PREROUTING'},{}
  while #pending>0 do
    local chain=table.remove(pending)
    if not seen[chain] then
      seen[chain]=true
      for _,tokens in ipairs(chains[chain] or {}) do
        for _,flag in ipairs({'-j','-g'}) do
          local index=nil
          for i,t in ipairs(tokens) do if t==flag then index=i;break end end
          if index then
            if index+1>#tokens then return false end
            local target=tokens[index+1]
            if target=='MARK' or string.sub(target,1,6)=='TUNNEL' then return false end
            if chains[target] then pending[#pending+1]=target end
          end
        end
      end
    end
  end
  return true
end

return M
