-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- server_pin.lua: trust on first use of the VPN servers' keys, the Lua twin of server_pin.py (same behaviour, shared
-- cases router/tests/server_pin_cases.json). Owner option, default warn:
--   uci set homensai_vpn.main.server_key_pin='warn'|'enforce'|'off'; uci commit homensai_vpn
-- Pinned per SERVER IDENTITY = profile id + configured server host (never the resolved IP):
--   WireGuard: the peer public key of the running tunnel (`wg show <wgclientN> endpoints`, exactly one peer); host =
--     the peer's uci end_point host, or its name for provider peers without end_point (NordVPN via GL,
--     server_pick.endpoints). A pool that hands the profile another server gives another host: a first use, not a
--     change. Only the SAME server with ANOTHER key is a change.
--   OpenVPN: SHA-256 of every CA certificate (DER) of the running client's config (/proc/<pid>/cmdline --config,
--     inline <ca> or `ca <file>`, relative to --cd); host = the config's first `remote`.
-- Observed only for a channel the monitor just measured healthy, at most every RECHECK s per profile and at once when
-- its live endpoint changed; network.<interface>.config must name the profile before and after the reads.
-- pinned -> (another key) changed: event SERVER-KEY-CHANGED, sticky until `homensai-vpn-server-key accept` (event
-- SERVER-KEY-ACCEPTED) or `forget` (SERVER-KEY-FORGOTTEN, the next check pins anew). Mode enforce (T.key_unaccepted, review
-- 04.11.2026): SERVER-KEY-UNACCEPTED for a profile with an unaccepted change. A Start waits for the channel that carries
-- the traffic afterwards (T.carrying_unaccepted), a server hand-over for either; a working pair refuses only a move ONTO that channel, leaving it, a Stop and every rollback stay free.
-- Files: RUNTIME/server-keys.json (tmpfs, every change), PERSIST/server-keys.json (flash: at once for a change,
-- acceptance or forget; new first-use records at most every PERSIST_SPACING s; last_seen is RAM only).
-- run as a command (/usr/sbin/homensai-vpn-server-key), not when required by a test or a module
local MAIN=arg and type(arg[0])=='string' and (arg[0]=='server_pin.lua' or string.find(arg[0],'/server_pin%.lua$')~=nil)
if MAIN then package.path=(string.match(arg[0],'^(.*)/[^/]*$') or '.')..'/?.lua;'..package.path end
local canon=require('canon')
local NULL=canon.null

local M={}
M.STATE='server-keys.json'
M.REQUEST='server-keys-accept.json'
M.CORRUPT_COPY='server-keys.corrupt.json'
M.CONFIG='/etc/config/homensai_vpn'
M.PINNED='SERVER-KEY-PINNED'
M.CHANGED='SERVER-KEY-CHANGED'
M.ACCEPTED='SERVER-KEY-ACCEPTED'
M.FORGOTTEN='SERVER-KEY-FORGOTTEN'
M.BLOCKED='SERVER-KEY-UNACCEPTED'
M.CORRUPT='SERVER-KEY-STATE-CORRUPT'
M.DEFAULT_MODE='warn'
M.RECHECK=600
M.PERSIST_SPACING=600
M.MAX_RECORDS=256
M.MAX_TEXT=512
M.MAX_CONFIG=262144
M.MAX_CA=65536
local MODES={off=true,warn=true,enforce=true}
local BEGIN,END='-----BEGIN CERTIFICATE-----','-----END CERTIFICATE-----'
local WS='[ \t\n\r\f\v]'

local function lines_of(text)
  local out={}
  for line in string.gmatch(text..'\n','([^\n]*)\n') do out[#out+1]=line end
  return out
end
local function tokens(line)
  local out={}
  for word in string.gmatch(line,'[^ \t\n\r\f\v]+') do out[#out+1]=word end
  return out
end
local function strip(s) return (string.match(s,'^[ \t\n\r\f\v]*(.-)[ \t\n\r\f\v]*$')) end
local function is_text(v) return type(v)=='string' and #v>=1 and #v<=M.MAX_TEXT end
local function is_number(v) v=canon.number(v);return v~=nil and v==v and math.abs(v)<1e12 end
local function none(v) return v==nil or v==NULL end
local function profile_parts(v)
  if type(v)~='string' then return nil end
  local protocol,section=string.match(v,'^(%l+):([%w_]+)$')
  if (protocol=='wireguard' or protocol=='openvpn') and #section<=64 then return protocol,section end
  return nil
end
local function iface_ok(v)
  if type(v)~='string' then return false end
  local digits=string.match(v,'^wgclient(%d+)$') or string.match(v,'^ovpnclient(%d+)$')
  return digits~=nil and #digits>=1 and #digits<=4
end
local function host_ok(v) return type(v)=='string' and #v>=1 and #v<=253 and string.find(v,'^[%w.:%-]+$')~=nil end
local function sorted_keys(t)
  local keys={}
  for k in pairs(t) do keys[#keys+1]=k end
  table.sort(keys,canon.key_less)
  return keys
end

------------------------------------------------------------------------------------------------------
-- pure parsing (shared cases)
------------------------------------------------------------------------------------------------------
function M.mode(text)
  local found=M.DEFAULT_MODE
  if type(text)~='string' then return found end
  for _,line in ipairs(lines_of(text)) do
    local value=string.match(line,"^[ \t]*option[ \t]+server_key_pin[ \t]+'?(%a+)'?[ \t]*$")
    if value and MODES[value] then found=value end
  end
  return found
end

function M.wg_fingerprint(raw)
  if type(raw)~='string' or #raw>4096 then return nil end
  local lines={}
  for _,line in ipairs(lines_of(raw)) do if string.find(line,'[^ \t\n\r\f\v]') then lines[#lines+1]=line end end
  if #lines~=1 then return nil end
  local parts=tokens(lines[1])
  if #parts~=2 or #parts[1]~=44 or not string.find(parts[1],'^[%w+/]+[AEIMQUYcgkosw048]=$') then return nil end
  return 'wg:'..parts[1]
end

local B64='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
local B64INDEX={}
for i=1,64 do B64INDEX[string.byte(B64,i)]=i-1 end
-- s: [A-Za-z0-9+/]+={0,2}, #s%4==0 (checked by the caller)
local function b64decode(s)
  local out={}
  for i=1,#s,4 do
    local a,b,c,d=string.byte(s,i,i+3)
    local n=B64INDEX[a]*262144+B64INDEX[b]*4096+(B64INDEX[c] or 0)*64+(B64INDEX[d] or 0)
    local x,y,z=math.floor(n/65536),math.floor(n/256)%256,n%256
    if c==61 then out[#out+1]=string.char(x)
    elseif d==61 then out[#out+1]=string.char(x,y)
    else out[#out+1]=string.char(x,y,z) end
  end
  return table.concat(out)
end
M.b64decode=b64decode

function M.cert_digests(text)
  if type(text)~='string' then return nil end
  local seen,out,pos={},{},1
  while true do
    local start=string.find(text,BEGIN,pos,true)
    if not start then break end
    local finish=string.find(text,END,start+#BEGIN,true)
    if not finish then return nil end
    local body=string.gsub(string.sub(text,start+#BEGIN,finish-1),WS,'')
    if #body==0 or #body%4~=0 or not string.find(body,'^[%w+/]+=?=?$') then return nil end
    local digest=canon.sha256(b64decode(body))
    if not seen[digest] then seen[digest]=true;out[#out+1]=digest end
    pos=finish+#END
  end
  if #out==0 then return nil end
  table.sort(out)
  return out
end

function M.ovpn_parts(text)
  if type(text)~='string' then return nil,nil,nil end
  local inline=nil
  local start=string.find(text,'<ca>',1,true)
  if start then
    local finish=string.find(text,'</ca>',start,true)
    if finish and finish>start then inline=string.sub(text,start+4,finish-1) end
  end
  local ca,remote=nil,nil
  for _,line in ipairs(lines_of(text)) do
    local parts=tokens(line)
    if #parts>=2 and parts[1]=='ca' and ca==nil then
      ca=(string.gsub(parts[2],'^["\']+',''));ca=(string.gsub(ca,'["\']+$',''))
    end
    if #parts>=2 and parts[1]=='remote' and remote==nil and host_ok(parts[2]) then remote=string.lower(parts[2]) end
  end
  return inline,ca,remote
end

function M.wg_host(uci_text,section)
  local sp=require('server_pick')
  local data=type(uci_text)=='string' and sp.parse_uci(uci_text) or {}
  local found=sp.endpoints('wireguard',(data.wireguard or {})[section])
  local host=found[1] and string.lower(found[1].host) or nil
  if host_ok(host) then return host end
  return nil
end

function M.identity(profile,host) return profile..'|'..(host or '-') end

------------------------------------------------------------------------------------------------------
-- state
------------------------------------------------------------------------------------------------------
function M.empty() return canon.object({schema=1,records=canon.object()}) end

local function record_ok(r)
  if not canon.is_object(r) then return false end
  for _,k in ipairs({'profile','host','protocol','fingerprint','observed'}) do if not is_text(r[k]) then return false end end
  if r.state~='pinned' and r.state~='changed' then return false end
  if not is_number(r.first_seen) or not is_number(r.last_seen) then return false end
  for _,k in ipairs({'changed_at','accepted_at'}) do if not none(r[k]) and not is_number(r[k]) then return false end end
  return true
end

function M.load(text)
  if text==nil then return M.empty(),false end
  local ok,data=pcall(canon.decode,text)
  if not ok or not canon.is_object(data) or canon.number(data.schema)~=1 or not canon.is_object(data.records) then return M.empty(),true end
  local count=0
  for _,r in pairs(data.records) do
    count=count+1
    if not record_ok(r) then return M.empty(),true end
  end
  if count>2*M.MAX_RECORDS then return M.empty(),true end
  for _,r in pairs(data.records) do
    for _,k in ipairs({'first_seen','last_seen','changed_at','accepted_at'}) do
      if none(r[k]) then r[k]=NULL else r[k]=canon.number(r[k]) end
    end
  end
  return canon.object({schema=1,records=data.records}),false
end

local function event(code,r,now)
  return canon.object({time=now,code=code,profile=r.profile,host=r.host,fingerprint=r.observed,pinned=r.fingerprint})
end

function M.evict(state)
  local records=state.records
  while true do
    local count,victim=0,nil
    for _,key in ipairs(sorted_keys(records)) do
      count=count+1
      local r=records[key]
      if r.state=='pinned' and (victim==nil or r.last_seen<records[victim].last_seen) then victim=key end
    end
    if count<=M.MAX_RECORDS or victim==nil then return end
    records[victim]=nil
  end
end

function M.observe(state,live,now)
  local records=state.records
  local key,fingerprint=live.identity,live.fingerprint
  local r=records[key]
  if r==nil then
    r=canon.object({profile=live.profile,host=live.host,protocol=live.protocol,fingerprint=fingerprint,observed=fingerprint,
      state='pinned',first_seen=now,last_seen=now,changed_at=NULL,accepted_at=NULL})
    records[key]=r
    M.evict(state)
    return {event(M.PINNED,r,now)},'new'
  end
  local previous=r.observed
  r.last_seen=now;r.observed=fingerprint
  if fingerprint==r.fingerprint then return {},nil end
  if r.state=='pinned' then
    r.state='changed';r.changed_at=now
    return {event(M.CHANGED,r,now)},'urgent'
  end
  if fingerprint~=previous then return {event(M.CHANGED,r,now)},'urgent' end
  return {},nil
end

function M.apply_request(state,request,now)
  if not canon.is_object(request) or (request.action~='accept' and request.action~='forget') then return {},nil end
  local target=request.profile
  if not (target=='*' or profile_parts(target)) then return {},nil end
  -- the page (rpc server_key_accept, agent.py) names the key the administrator checked: a key that changed again
  -- after that is not accepted; the CLI request has no 'observed' and accepts the key seen now
  local seen=request.observed
  if seen==NULL then seen=nil end
  local records,events=state.records,{}
  for _,key in ipairs(sorted_keys(records)) do
    local r=records[key]
    if target=='*' or r.profile==target then
      if request.action=='accept' then
        if r.state=='changed' and (seen==nil or r.observed==seen) then
          r.fingerprint=r.observed;r.state='pinned';r.accepted_at=now;r.changed_at=NULL
          events[#events+1]=event(M.ACCEPTED,r,now)
        end
      else
        records[key]=nil
        events[#events+1]=event(M.FORGOTTEN,r,now)
      end
    end
  end
  return events,(#events>0 and 'urgent' or nil)
end

function M.blocker(state,mode,profiles)
  if mode~='enforce' or type(state)~='table' or type(state.records)~='table' then return nil end
  local wanted={}
  for _,p in ipairs(profiles or {}) do if type(p)=='string' then wanted[p]=true end end
  for _,r in pairs(state.records) do
    if type(r)=='table' and r.state=='changed' and wanted[r.profile] then return M.BLOCKED end
  end
  return nil
end

function M.public(state,mode)
  if mode=='off' then return canon.object({mode='off'}) end
  local changed,total=canon.array(),0
  for _,key in ipairs(sorted_keys(state.records)) do
    local r=state.records[key]
    total=total+1
    if r.state=='changed' then
      changed[#changed+1]=canon.object({profile=r.profile,host=r.host,pinned=r.fingerprint,observed=r.observed,changed_at=r.changed_at})
    end
  end
  return canon.object({mode=mode,pinned=total-#changed,changed=changed,code=#changed>0 and M.CHANGED or NULL})
end

------------------------------------------------------------------------------------------------------
-- live reads; io: read(path,limit) -> text|nil, run(argv) -> stdout|nil (non-zero exit)
------------------------------------------------------------------------------------------------------
function M.ovpn_live(interface,io)
  local pid=strip(io.read('/var/run/ovpnclient-'..interface..'.pid',32) or '')
  if not string.find(pid,'^[0-9]+$') or #pid>10 then return nil,nil end
  local n=tonumber(pid)
  if not (n>1 and n<2^31) then return nil,nil end
  local process='/proc/'..pid
  if strip(io.read(process..'/comm',64) or '')~='openvpn' then return nil,nil end
  local cmdline=string.match(io.read(process..'/cmdline',16384) or '','^%z*(.-)%z*$')
  local args={}
  for a in string.gmatch(cmdline..'\0','([^%z]*)%z') do args[#args+1]=a end
  local function value(flag)
    local count,at=0,nil
    for i,a in ipairs(args) do if a==flag then count=count+1;at=at or i end end
    if count~=1 or at+1>#args then return nil end
    return args[at+1]
  end
  if value('--dev')~=interface then return nil,nil end
  local config,cd=value('--config'),value('--cd')
  local function resolve(path)
    if not path or path=='' or string.find(path,'\n',1,true) then return nil end
    if string.sub(path,1,1)=='/' then return path end
    if cd and string.sub(cd,1,1)=='/' then return (string.gsub(cd,'/+$',''))..'/'..path end
    return nil
  end
  config=resolve(config)
  local text=config and io.read(config,M.MAX_CONFIG) or nil
  local inline,ca,host=M.ovpn_parts(text)
  if inline==nil and ca~=nil then
    local path=resolve(ca)
    inline=path and io.read(path,M.MAX_CA) or nil
  end
  local digests=M.cert_digests(inline)
  return digests and ('ovpn-ca:'..table.concat(digests,',')) or nil,host
end

function M.read_live(profile,io)
  if type(profile)~='table' then return nil end
  local pid,interface=profile.id,profile.interface
  local protocol,section=profile_parts(pid)
  if not protocol or not iface_ok(interface) then return nil end
  if (protocol=='wireguard')~=(string.sub(interface,1,8)=='wgclient') then return nil end
  local function bound()
    local out=io.run({'uci','-q','get','network.'..interface..'.config'})
    return type(out)=='string' and strip(out)==section
  end
  if not bound() then return nil end
  local fingerprint,host
  if protocol=='wireguard' then
    fingerprint=M.wg_fingerprint(io.run({'wg','show',interface,'endpoints'}))
    host=M.wg_host(io.run({'uci','-q','show','wireguard.'..section}),section)
  else
    fingerprint,host=M.ovpn_live(interface,io)
  end
  if fingerprint==nil or not bound() then return nil end
  return {profile=pid,protocol=protocol,host=host or '-',fingerprint=fingerprint,identity=M.identity(pid,host)}
end

------------------------------------------------------------------------------------------------------
-- the monitor's part (monitor.lua; agent.py holds server_pin.Pins)
-- io: read, run, write_ram(path,text), write_flash(path,text), remove(path)
------------------------------------------------------------------------------------------------------
local Pins={}
Pins.__index=Pins
M.Pins=Pins

function M.new(runtime,persist,io)
  local self=setmetatable({},Pins)
  self.runtime=string.gsub(runtime,'/+$','');self.persist=string.gsub(persist,'/+$','');self.io=io
  self.checked={};self.flash_at=nil;self.dirty=false;self.notice=nil
  local text=io.read(self.runtime..'/'..M.STATE,2*1024*1024)
  local source=text~=nil and text or io.read(self.persist..'/'..M.STATE,2*1024*1024)
  local corrupt
  self.state,corrupt=M.load(source)
  if corrupt then
    self.notice=M.CORRUPT
    io.write_ram(self.runtime..'/'..M.CORRUPT_COPY,string.sub(source,1,262144))
  end
  return self
end

function Pins:save(urgency,now)
  local text=canon.encode(self.state)
  self.io.write_ram(self.runtime..'/'..M.STATE,text)
  if urgency~=nil then self.dirty=true end
  local due=self.flash_at==nil or now<self.flash_at or now-self.flash_at>=M.PERSIST_SPACING
  if self.dirty and (urgency=='urgent' or due) then
    self.io.write_flash(self.persist..'/'..M.STATE,text)
    self.flash_at=now;self.dirty=false
  end
end

local function worse(a,b)
  if a=='urgent' or b=='urgent' then return 'urgent' end
  if a=='new' or b=='new' then return 'new' end
  return nil
end

function Pins:step(rows,mode,now)
  now=math.floor(now)
  local events,urgency,touched={},nil,false
  local function add(list) for _,e in ipairs(list) do events[#events+1]=e end end
  if self.notice then
    events[#events+1]=canon.object({time=now,code=self.notice})
    self.notice=nil;urgency='urgent';touched=true
  end
  local request_path=self.runtime..'/'..M.REQUEST
  local raw=self.io.read(request_path,4096)
  if raw~=nil then
    local ok,request=pcall(canon.decode,raw)
    local found,level=M.apply_request(self.state,ok and request or nil,now)
    add(found);urgency=worse(urgency,level);touched=true
    self.io.remove(request_path)
  end
  if mode~='off' then
    local list={}
    for _,row in ipairs(rows or {}) do if type(row)=='table' and type(row.id)=='string' then list[#list+1]=row end end
    table.sort(list,function(a,b) return canon.key_less(a.id,b.id) end)
    for _,row in ipairs(list) do
      if none(row.code) then
        local endpoint=row.server_endpoint
        local signature=canon.is_object(endpoint) and (tostring(endpoint.host)..'|'..tostring(canon.number(endpoint.port) or endpoint.port)) or '-'
        local last=self.checked[row.id]
        if not (last and last[2]==signature and now-last[1]>=0 and now-last[1]<M.RECHECK) then
          self.checked[row.id]={now,signature}
          local ok,live=pcall(M.read_live,row,self.io)
          if ok and live then
            local found,level=M.observe(self.state,live,now)
            add(found);urgency=worse(urgency,level);touched=true
          end
        end
      end
    end
  end
  if touched or self.dirty then self:save(urgency,now) end
  return events,M.public(self.state,mode)
end

-- The Auto diagnostic's check (backend.diagnostic; native_switch.diagnostic in Python): read(path) -> text|nil
function M.gate(read,runtime,persist,profiles)
  local mode=M.mode(read(M.CONFIG))
  if mode~='enforce' then return nil end
  local text=read((runtime or '/var/run/homensai-vpn')..'/'..M.STATE)
  if text==nil then text=read((persist or '/etc/homensai-vpn')..'/'..M.STATE) end
  local state=M.load(text)
  return M.blocker(state,mode,profiles)
end

------------------------------------------------------------------------------------------------------
-- router io and the administrator command (/usr/sbin/homensai-vpn-server-key)
------------------------------------------------------------------------------------------------------
function M.router_io()
  local durable=require('durable')
  local mio=require('monitor_io')
  local function read(path,limit)
    local f=io.open(path,'rb')
    if not f then return nil end
    local data=f:read(limit+1)
    f:close()
    if data==nil then data='' end
    if #data>limit then return nil end
    return data
  end
  local function run(argv)
    local ok,rc,out=pcall(mio.exec,argv,{timeout=2})
    if not ok or rc~=0 then return nil end
    return out
  end
  return {read=read,run=run,
    write_ram=function(path,text) durable.write(path,text,{sync=false}) end,
    write_flash=function(path,text) durable.write(path,text) end,
    remove=function(path) os.remove(path) end}
end

M.USAGE=table.concat({'usage: homensai-vpn-server-key list | accept <profile|all> [--offline] | forget <profile|all> [--offline]',
  '  list     pinned servers and unaccepted key changes (mode from option server_key_pin)',
  '  accept   trust the key now seen for a changed server (after checking it with the provider)',
  '  forget   drop the pins of a profile; its next healthy check pins anew (first use)',
  '  --offline  apply directly when the service is stopped (otherwise the monitor applies it at its next pass)'},'\n')

function M.cli(argv,io_,runtime,persist,now,wait,out)
  io_=io_ or M.router_io()
  runtime=runtime or '/var/run/homensai-vpn';persist=persist or '/etc/homensai-vpn'
  now=math.floor(now or os.time());wait=wait or 60;out=out or print
  local args,offline={},false
  for _,a in ipairs(argv) do if a=='--offline' then offline=true else args[#args+1]=a end end
  local command=args[1]
  if not (command=='list' or command=='accept' or command=='forget') or (command~='list')~=(#args==2) or #args>2 then out(M.USAGE);return 2 end
  if command=='list' then
    local text=io_.read(runtime..'/'..M.STATE,2*1024*1024)
    if text==nil then text=io_.read(persist..'/'..M.STATE,2*1024*1024) end
    local state,corrupt=M.load(text)
    local view=M.public(state,M.mode(io_.read(M.CONFIG,65536)))
    local records=canon.array()
    for _,key in ipairs(sorted_keys(state.records)) do
      local r=canon.object();for k,v in pairs(state.records[key]) do r[k]=v end;r.identity=key;records[#records+1]=r
    end
    view.records=records
    if corrupt then view.notice=M.CORRUPT end
    out(canon.encode(view))
    return 0
  end
  local target=args[2]=='all' and '*' or args[2]
  if target~='*' and not profile_parts(target) then
    out('SERVER-KEY-PROFILE-INVALID: expected wireguard:<section>, openvpn:<section> or all');return 2
  end
  local request=canon.object({action=command,profile=target,time=now})
  if offline then
    local pins=M.new(runtime,persist,io_)
    local found,level=M.apply_request(pins.state,request,now)
    pins:save(level,now)
    for _,e in ipairs(found) do out(e.code..' '..e.profile..' '..e.host) end
    out('APPLIED '..#found..' record(s)')
    return #found>0 and 0 or 1
  end
  io_.write_ram(runtime..'/'..M.REQUEST,canon.encode(request))
  for _=1,wait do
    if io_.read(runtime..'/'..M.REQUEST,4096)==nil then out('APPLIED by the monitor (see list and the event history)');return 0 end
    os.execute('sleep 1')
  end
  out('REQUESTED: the monitor applies it at its next pass (service stopped? use --offline)')
  return 0
end

if MAIN then os.exit(M.cli(arg)) end

return M
