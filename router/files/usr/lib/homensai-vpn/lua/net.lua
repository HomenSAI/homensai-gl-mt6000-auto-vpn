-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- net.lua: the network side of pair_auto.py for the Lua supervisor (2.0.0-lua line) - env.net of pair.lua:
-- network(), identity(rows,managed) (normalized_network), configs(managed), changed(state,observed,skip),
-- firewall_bytes(), static_firewall_digest([data]), set_disabled(state,interface,value,revision),
-- client_down(interface), ifup(interface,revision), ifdown(interface), quiet(seconds,revision),
-- interface_exists(interface).
-- The UCI network read and write are the exact Python Lua sources (NETWORK_READ / NETWORK_WRITE): the read runs in
-- this process, the write as a bounded child (F-24, 8 s like Python). Config digests are cached by the CONTENT of
-- each file (F-41): an unchanged file is read (bounded) but never re-hashed on a tick.
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
M.WRITE_TIMEOUT=8  -- pair_auto.set_disabled: subprocess.run(..., timeout=8)

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

-- F-34 (pair_auto.firewall_without_vendor_exit): the stock client's exit bookkeeping options are not an external
-- edit only on a zone that names a VPN client interface and only with the values the stock client writes; the same
-- option on any other section (the WAN or LAN zone) or with another value counts.
local function strip_cr(line) return (string.gsub(line,'\r+$','')) end
-- VPN_CLIENT_NAME.fullmatch: (?:wgclient|ovpnclient)(?:[1-9][0-9]{0,3})?
local function vpn_client_name(x)
  if type(x)~='string' then return false end
  local kind,number=string.match(x,'^(%a+)(%d*)$')
  if kind~='wgclient' and kind~='ovpnclient' then return false end
  return number=='' or (string.match(number,'^[1-9]%d*$')~=nil and #number<=4)
end
-- R4-05 (pair_auto.UCI_SECTION_START): ANY line that begins with the word config starts a new section, parsed or not
local function section_start(line)
  line=strip_cr(line)
  return string.match(line,'^[ \t]*config$')~=nil or string.match(line,'^[ \t]*config[ \t]')~=nil
end
-- pair_auto.UCI_SECTION.fullmatch: type and name each bare, 'quoted' or "quoted", an optional trailing # comment
-- -> kind, name|nil (or nil when the header cannot be parsed: a section of someone else)
local function word(text,class)
  local w=string.match(text,"^'(["..class.."]+)'$") or string.match(text,'^"(['..class..']+)"$') or string.match(text,'^(['..class..']+)$')
  return w
end
local function section_header(line)
  line=strip_cr(line)
  local rest=string.match(line,'^[ \t]*config[ \t]+(.*)$')
  if not rest then return nil end
  rest=string.gsub(rest,'[ \t]*#.*$','')
  rest=string.gsub(rest,'[ \t]+$','')
  local kind_text,name_text=string.match(rest,'^(%S+)[ \t]+(%S+)$')
  if not kind_text then kind_text=string.match(rest,'^(%S+)$') end
  if not kind_text then return nil end
  local kind=word(kind_text,'%w_%-')
  if not kind then return nil end
  if name_text==nil then return kind,nil end
  local name=word(name_text,'%w_')
  if not name then return nil end
  return kind,name
end
-- ZONE_MEMBER.fullmatch: [ \t]*(?:option[ \t]+(?:name|network)|list[ \t]+network)[ \t]+'([^'\r\n]*)'[ \t]*
local function zone_member(line)
  line=strip_cr(line)
  local word,key,value=string.match(line,"^[ \t]*(%a+)[ \t]+(%a+)[ \t]+'([^'\r\n]*)'[ \t]*$")
  if (word=='option' and (key=='name' or key=='network')) or (word=='list' and key=='network') then return value end
  return nil
end
local function vpn_client_zone(lines)
  local kind,name=section_header(lines[1])
  if kind~='zone' then return false end
  local names={}
  if name then names[#names+1]=name end
  for i=2,#lines do
    local value=zone_member(lines[i])
    if value then for token in string.gmatch(value,'%S+') do names[#names+1]=token end end
  end
  for _,x in ipairs(names) do if vpn_client_name(x) then return true end end
  return false
end
-- VENDOR_EXIT_OPTION.fullmatch with a value the stock client writes
local function vendor_exit_option(line)
  line=strip_cr(line)
  local name,value=string.match(line,"^[ \t]*option[ \t]+gl_([a-z_]+)[ \t]+'([^'\r\n]*)'[ \t]*$")
  if name=='wan_like' or name=='bwa_managed' or name=='bwa_bridge_reject' then return value=='0' or value=='1' end
  if name=='bwa_exit_id' then return vpn_client_name(value) end
  return false
end
local function firewall_sections(data)
  local sections,current={},{}
  for _,line in ipairs(lines_of(data)) do
    if section_start(line) and #current>0 then sections[#sections+1]=current;current={} end
    current[#current+1]=line
  end
  sections[#sections+1]=current
  return sections
end
function M.firewall_without_vendor_exit(data)
  local kept={}
  for _,lines in ipairs(firewall_sections(data)) do
    local owned=vpn_client_zone(lines)
    for _,line in ipairs(lines) do
      if not (owned and vendor_exit_option(line)) then kept[#kept+1]=line end
    end
  end
  return table.concat(kept,'\n')
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
  if name=='firewall' then data=M.firewall_without_vendor_exit(data) end
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
  local cache={}  -- config name -> {text=, managed=, sha=}

  -- F-41 / D07: the version of a config file is its CONTENT, never its metadata (type, inode, size, mtime, ctime):
  -- two same-size in-place edits within one timestamp tick share the metadata tuple and would keep a stale digest
  -- (Python reads and hashes the contents on every tick). The read is bounded by the 1 MB config limit; a file that
  -- cannot be read as a regular file of that size has no version and is never served from the cache. Lua interns
  -- strings, so the comparison of two equal 1 MB texts is a pointer comparison.
  local function content_key(path)
    local st=sys.lstat(path)
    if not st then return 'absent' end
    if st.type~='reg' or st.size>1048576 then return nil end
    local ok,text=pcall(sys.read,path,1048576)
    if not ok or text==nil then return nil end
    return text
  end
  -- the UCI network read, once per version of /etc/config/network and its uncommitted delta
  local network_cache=nil
  function N.network()
    local config,delta=content_key('/etc/config/network'),content_key('/tmp/.uci/network')
    local key=(config and delta) and (#config..':'..config..'|'..#delta..':'..delta) or nil
    if key and network_cache and network_cache.key==key then return py.copy(network_cache.data) end
    local ok,text=pcall(sys.chunk,'pair_network_read',M.NETWORK_READ)
    if not ok then value_error('PAIR-NETWORK-UNVERIFIED') end
    local dok,data=pcall(canon.decode,text)
    if not dok or not canon.is_array(data) or #data<1 or #data>400 then value_error('PAIR-NETWORK-UNVERIFIED') end
    network_cache=key and {key=key,data=data} or nil
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
      local text=config_bytes(path)
      local row=cache[name]
      if row and row.text==text and row.managed==mkey then result[name]=row.sha
      else
        local sha=M.config_digest(name,text,managed)
        cache[name]={text=text,managed=mkey,sha=sha};result[name]=sha
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
    -- F-24 / D11: Python runs NETWORK_WRITE as `lua -e <source>` with its job on stdin and an 8 s timeout. Here the
    -- same source and job are files of the private stage directory (0700, RAM) and a bounded child of the supervisor
    -- runs them (backend.network_dispatch: writer record, spawn under the lock, wait outside it, confirmed
    -- termination) - never in this process while the control lock is held. Its failure keeps the old code.
    local script,job=stage..'/write.lua',stage..'/job.json'
    local argv={'sh','-c','exec lua '..script..' <'..job}
    local function write()
      local wok=pcall(function() sys.write_private(script,M.NETWORK_WRITE);sys.write_private(job,payload) end)
      if not wok then value_error('PAIR-NETWORK-WRITE-FAILED') end
      local ok,err=pcall(env.backend.network_dispatch,argv,revision,M.WRITE_TIMEOUT)
      if not ok then
        if type(err)=='table' and err.code=='COMMAND-FAILED' then value_error('PAIR-NETWORK-WRITE-FAILED') end
        error(err,0)
      end
    end
    local ok,err=pcall(function()
      if revision==nil then write()
      else
        pair().require_running(env,revision)
        write()
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
