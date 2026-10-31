-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- net.lua: the network side of pair_auto.py for the Lua supervisor (2.0.0-lua line) - env.net of pair.lua:
-- network(), identity(rows,managed) (normalized_network), configs(managed), changed(state,observed,skip),
-- firewall_bytes(), static_firewall_digest([data]), set_disabled(state,interface,value,revision),
-- client_down(interface), ifup(interface,revision), ifdown(interface), quiet(seconds,revision),
-- interface_exists(interface).
-- The UCI network read and write are the exact Python Lua sources (NETWORK_READ / NETWORK_WRITE), run in this
-- process. Config digests are cached by (inode, size, mtime, ctime) of each file: an unchanged file is never
-- re-read or re-hashed on a tick.
local canon=require('canon')
local py=require('py')
local identity=require('identity')
local platform=require('platform')

local M={}
local NULL=canon.null
local value_error=identity.value_error

M.NETWORK_READ=[[
local c=require('uci').cursor();local j=require('cjson');local sections={}
local pending=c:changes('network');assert(not pending or next(pending)==nil,'pending')
c:foreach('network',nil,function(s) s['.index']=nil;sections[#sections+1]=s end)
print(j.encode(sections))
]]
M.NETWORK_WRITE=[[
local j=require('cjson');local u=require('uci');local q=j.decode(io.read('*a'))
local c=u.cursor('/etc/config',q.stage);local all={}
for _,p in ipairs({'network','wireguard','ovpnclient','route_policy','homensai_vpn'})do
 local x=u.cursor():changes(p);assert(not x or next(x)==nil,'pending')end
c:foreach('network',nil,function(s)s['.index']=nil;all[#all+1]=s end)
local function eq(a,b)
 if type(a)~=type(b)then return false end
 if type(a)~='table'then return a==b end
 for k,v in pairs(a)do if not eq(v,b[k])then return false end end
 for k in pairs(b)do if a[k]==nil then return false end end return true end
assert(eq(all,q.expected),'changed')
assert(type(q.managed)=='table'and q.managed[q.interface],'interface')
local count=0
for name,proto in pairs(q.managed)do
 assert(name:match('^wgclient[1-9]%d*$')and proto=='wgclient'or name:match('^ovpnclient[1-9]%d*$')and proto=='ovpnclient','interface')
 assert(#name<=14,'interface');count=count+1
end
assert(count==2,'interface')
assert(q.value=='0'or q.value=='1','value')
assert(c:set('network',q.interface,'disabled',q.value));assert(c:save('network'));assert(c:commit('network'))
]]
M.CONFIGS={'wireguard','ovpnclient','firewall','route_policy','wireless','dhcp','gl-dns-v2'}

local function safe_interface(name) return type(name)=='string' and #name>=1 and #name<=15 and string.find(name,'^[A-Za-z0-9_]+$')~=nil end

-- orphan clients: (?:wgclient|ovpnclient)[1-9][0-9]{0,3}
local function orphan_client(name)
  if type(name)~='string' then return false end
  local kind,number=string.match(name,'^(%a+)([1-9]%d*)$')
  return (kind=='wgclient' or kind=='ovpnclient') and #number<=4
end

function M.normalized_network(data,managed)
  managed=managed or identity.LEGACY
  local rows={}
  for _,original in ipairs(data) do
    local row=py.copy(original)
    local name=row['.name']
    if type(name)=='string' and managed[name]~=nil then row.disabled=nil;rows[#rows+1]=row
    elseif orphan_client(name) and row.disabled=='1' then  -- a stopped stock leftover the pair does not use
    else rows[#rows+1]=row end
  end
  return canon.digest(identity.network_partition(rows))
end

-- split(data, '\n(?=config<sep>)'): blocks without the separating newline
local function split_blocks(data,tab)
  local blocks,start,i={},1,1
  while true do
    local j=string.find(data,'\nconfig',i,true)
    if not j then break end
    local after=string.sub(data,j+7,j+7)
    if after==' ' or (tab and after=='\t') then blocks[#blocks+1]=string.sub(data,start,j-1);start=j+1 end
    i=j+1
  end
  blocks[#blocks+1]=string.sub(data,start)
  return blocks
end
local function lines_of(data) local out={};for line in string.gmatch(data..'\n','([^\n]*)\n') do out[#out+1]=line end;return out end

-- VENDOR_EXIT_OPTIONS.fullmatch(line.rstrip('\r')): [ \t]*option[ \t]+gl_(wan_like|bwa_managed|bwa_exit_id|bwa_bridge_reject)[ \t].*
local function vendor_exit_option(line)
  line=string.gsub(line,'\r+$','')
  if string.find(line,'\n',1,true) then return false end
  local name,sep=string.match(line,'^[ \t]*option[ \t]+gl_([a-z_]+)([ \t])')
  return name=='wan_like' or name=='bwa_managed' or name=='bwa_exit_id' or name=='bwa_bridge_reject'
end

function M.config_digest(name,data,managed)
  managed=managed or identity.LEGACY
  if name=='dhcp' then
    local kept={}
    for _,block in ipairs(split_blocks(data,false)) do
      local client=string.match(block,"^config[ \t]+dnsmasq[ \t]+'(%a+%d+)'")
      local drop=false
      if client and orphan_client(client) and managed[client]==nil and string.find(block,"\n[ \t]*option[ \t]+disabled[ \t]+'1'") then drop=true end
      if not drop then kept[#kept+1]=block end
    end
    data=table.concat(kept,'\n')
  end
  if name=='firewall' then
    local kept={}
    for _,line in ipairs(lines_of(data)) do if not vendor_exit_option(line) then kept[#kept+1]=line end end
    data=table.concat(kept,'\n')
  end
  return canon.sha256(data)
end

-- GL_VPN_RULES.search('\n'+block): \n[ \t]*option[ \t]+gl_vpn_rules[ \t]+'1'[ \t]*\r?(?:\n|$)
local function gl_vpn_rules(block)
  local text='\n'..block
  local i=1
  while true do
    local s,e=string.find(text,"\n[ \t]*option[ \t]+gl_vpn_rules[ \t]+'1'[ \t]*",i)
    if not s then return false end
    local rest=string.sub(text,e+1)
    if rest=='' or rest=='\n' or string.sub(rest,1,1)=='\n' or rest=='\r' or rest=='\r\n' or string.sub(rest,1,2)=='\r\n' then return true end
    i=s+1
  end
end

function M.new(env,sys)
  local N={}
  local cache={}  -- config name -> {key=, managed=, sha=}

  -- the UCI network read, once per version of /etc/config/network and its uncommitted delta
  local network_cache=nil
  function N.network()
    local key=sys.key('/etc/config/network')..'|'..sys.key('/tmp/.uci/network')
    if network_cache and network_cache.key==key then return py.copy(network_cache.data) end
    local ok,text=pcall(sys.chunk,'pair_network_read',M.NETWORK_READ)
    if not ok then value_error('PAIR-NETWORK-UNVERIFIED') end
    local dok,data=pcall(canon.decode,text)
    if not dok or not canon.is_array(data) or #data<1 or #data>400 then value_error('PAIR-NETWORK-UNVERIFIED') end
    network_cache={key=key,data=data}
    return py.copy(data)
  end
  function N.forget() network_cache=nil;cache={} end
  function N.identity(rows,managed) return M.normalized_network(rows,managed) end

  local function config_bytes(path)
    local st=sys.lstat(path)
    if not st or st.type~='reg' or st.size>1048576 then value_error('PAIR-CONFIG-UNVERIFIED') end
    local text=sys.read(path,1048576)
    if text==nil then value_error('PAIR-CONFIG-UNVERIFIED') end
    return text
  end
  function N.configs(managed)
    local result=canon.object({})
    local mkey=managed and canon.encode(managed) or ''
    for _,name in ipairs(M.CONFIGS) do
      local path='/etc/config/'..name
      local key=sys.key(path)
      local row=cache[name]
      if row and row.key==key and row.managed==mkey and key~='absent' then result[name]=row.sha
      else
        local sha=M.config_digest(name,config_bytes(path),managed)
        cache[name]={key=key,managed=mkey,sha=sha};result[name]=sha
      end
    end
    return result
  end
  function N.firewall_bytes() return config_bytes('/etc/config/firewall') end
  function N.static_firewall_digest(data)
    data=data or N.firewall_bytes()
    local kept={}
    for _,block in ipairs(split_blocks(data,true)) do if not gl_vpn_rules(block) then kept[#kept+1]=block end end
    return M.config_digest('firewall',table.concat(kept,'\n'))
  end
  function N.changed(state,observed,skip)
    local skipped={}
    for k,v in pairs(skip or {}) do if type(k)=='number' then skipped[v]=true else skipped[k]=v end end
    local protected=state.protected
    if not canon.is_object(protected) then value_error('PAIR-STATE-UNVERIFIED') end
    for name,sha in pairs(protected) do
      if name~='route_policy' and not skipped[name] then
        if observed[name]==nil then value_error('PAIR-CONFIG-UNVERIFIED') end
        if observed[name]~=sha and not (name=='firewall' and canon.sha256(N.firewall_bytes())==sha) then return true end
      end
    end
    return false
  end

  local pair=function() return require('pair') end
  function N.set_disabled(state,interface,value,revision)
    local data=N.network()
    local managed=pair().state_interfaces(state)
    if managed[interface]==nil then value_error('PAIR-PROFILES-UNVERIFIED') end
    if N.identity(data,managed)~=state.network_identity then value_error('PAIR-EXTERNAL-NETWORK-CHANGE') end
    if N.changed(state,N.configs(managed)) then value_error('PAIR-EXTERNAL-CONFIG-CHANGE') end
    local stage=sys.RUNTIME..'/pair-uci-'..sys.unique()
    if not sys.mkdir(stage,448) then value_error('PAIR-NETWORK-WRITE-FAILED') end
    local payload=canon.encode(canon.object({stage=stage,expected=data,interface=interface,value=value,managed=managed}))
    local function write()
      local ok=pcall(sys.chunk,'pair_network_write',M.NETWORK_WRITE,payload)
      if not ok then value_error('PAIR-NETWORK-WRITE-FAILED') end
    end
    local ok,err=pcall(function()
      if revision==nil then write()
      else
        pair().require_running(env,revision)
        env.run.lock(function()
          if require('auto_control').revision_locked(env)~=revision then value_error('CONTROL-REVISION-STALE') end
          write()
        end,env.runtime)
        pair().require_running(env,revision)
      end
    end)
    for _,name in ipairs(sys.dir(stage) or {}) do sys.remove(stage..'/'..name) end
    sys.rmdir(stage)
    N.forget()
    if not ok then error(err,0) end
    local after=N.network()
    local row=canon.object({})
    for _,r in ipairs(after) do if r['.name']==interface then row=r;break end end
    if N.identity(after,managed)~=state.network_identity or row.disabled~=value then value_error('PAIR-NETWORK-WRITE-UNVERIFIED') end
  end

  function N.client_down(interface)
    if not safe_interface(interface) then return false end
    local status=sys.ubus('network.interface.'..interface,'status')
    if not canon.is_object(status) then return false end
    local available=status.available
    return status.up==false and not py.truthy(status.pending) and available~=false
  end
  -- forward_dispatch(['ifup','-w',interface], revision, 20): dispatched under the lock, awaited outside it
  function N.ifup(interface,revision)
    if not safe_interface(interface) then value_error('PAIR-PROFILES-UNVERIFIED') end
    env.backend.forward_dispatch({'ifup','-w',interface},revision,20)
  end
  function N.ifdown(interface)
    if not safe_interface(interface) then value_error('PAIR-PROFILES-UNVERIFIED') end
    sys.command({'ifdown',interface},{timeout=20})
  end
  function N.quiet(seconds,revision)
    local T=require('transaction')
    local last=-1e9
    local function sample(end_)
      if revision~=nil then pair().require_running(env,revision) end
      local now=sys.clock()
      if now-last>=4 then
        T.publish(env,{state=revision and 'ARMED' or 'RESTORING',reason=revision and 'PAIR-CONNECTING' or 'PAIR-CLEANUP',
          mode='continuous-pair',proof_scope=pair().MODE,blockers=canon.array({})})
        last=now
      end
      return platform.workers(sys,end_)
    end
    platform.wait_quiet(sys,seconds,sample)
  end
  function N.interface_exists(interface)
    if not safe_interface(interface) then return true end  -- unknown is not "stopped"
    return sys.exists('/sys/class/net/'..interface)
  end
  return N
end

return M
