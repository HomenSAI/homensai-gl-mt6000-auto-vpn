-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- server_pick.lua: the best server inside a channel (2.1.0, docs/architecture/SERVER-PICK-DESIGN-2026-11-02.ru.md).
-- Lua port of server_pick.py - the same reading, ranking, file order, switch steps and published block (shared
-- cases: router/tests/server_pick_cases.json). Pure logic over an injected `io`; the monitor runs one round off its
-- event loop in a child (`lua server_pick.lua job <runtime>/server-pick-request.json`) at most every MEASURE_EVERY
-- seconds and right after a channel failure.
--
-- GL firmware facts (MT3000, GL 4.x, read 02.11.2026): every VPN tunnel is a route_policy rule (tunnel_id, via_type,
-- via, group_id, peer_id | client_id, profiles='/etc/vpn_profiles.d/profile<tunnel_id>'); the profiles file holds one
-- candidate per line, `[proto:]<group>_<id>`; /usr/bin/tunnel-switch.sh takes the NEXT line after the current one,
-- round robin, without looking at ping. So:
--   measure  OpenVPN: TCP connect time to the first reachable `remote` (ICMP is closed on some servers); WireGuard:
--            busybox ping of `end_point` (a name may move to another machine; ping resolves it). From the router
--            itself through the WAN, without raising a tunnel: not LAN traffic, no leak rule applies;
--   order    the best live server goes right after the current line, so the firmware's own round robin takes it
--            next (no switch of ours); written atomically and only when the text changes;
--   switch   an IDLE (not carrying) failed tunnel gets the best server the way tunnel-switch.sh does it (uci +
--            ifdown/ifup of that interface only). Refused while the tunnel carries traffic, while the firmware's own
--            switch holds its lock, with Auto off or the owner switch `server_pick` off (default off until the router
--            check). Hysteresis: a working server is replaced only by one >= 20 % faster; <= CHANGES per hour per tunnel.
--   stage 2  (MT3000 02.11.2026: a change made outside the pair cost the working channel a 7 s LAN stall and a pair
--            readopt) the job never switches itself any more: it writes the hand-off CHANGE and the Auto supervisor
--            (lua/pair.lua / pair_auto.py) changes the idle reserve inside its own lock, re-binds its session
--            (rebind()), waits for the tunnel (CONNECT_WAIT), verifies it through the tunnel and rolls back on failure.
-- Every measurement and switch is gated by the owner switch; with it off the block lists the candidates only.
if arg and arg[0] and string.find(arg[0],'server_pick%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local canon=require('canon')

local M={}
local NULL=canon.null
M.PICKED='SERVER-PICKED';M.FAILED='SERVER-PICK-FAILED';M.WAITING='SERVER-PICK-WAITING-VENDOR'
M.LIMIT='SERVER-PICK-LIMIT';M.CARRYING='SERVER-PICK-CARRYING';M.OFF='SERVER-PICK-OFF'
M.REQUESTED='SERVER-PICK-REQUESTED';M.DEFERRED='SERVER-PICK-DEFERRED'
M.CHANGING='SERVER-CHANGING'  -- the Auto status reason while its own server change waits for the tunnel (stage 2)
M.CODES={[M.PICKED]=true,[M.FAILED]=true,[M.WAITING]=true,[M.LIMIT]=true,[M.CARRYING]=true,[M.OFF]=true,[M.REQUESTED]=true,[M.DEFERRED]=true}
M.EVENT_CODES={[M.PICKED]=true,[M.FAILED]=true,[M.WAITING]=true,[M.LIMIT]=true}
M.MEASURE_EVERY=600;M.RETRY_CARRYING=20;M.CHANGES=4;M.WINDOW=3600
M.TCP_TIMEOUT=1.5;M.TCP_ATTEMPTS=4;M.TCP_SAMPLES=3
M.PING={'ping','-c','3','-W','1','-w','5'};M.PING_SECONDS=8;M.EXEC_SECONDS=20
M.MAX_TUNNELS=8;M.MAX_CANDIDATES=32;M.MAX_MEASURED=12;M.MAX_ENDPOINTS=8;M.MAX_TEXT=262144
M.RESULT='server-pick.json';M.STATE='server-pick-state.json';M.REQUEST='server-pick-request.json'
M.CHANGE='server-pick-change.json'  -- the monitor job's hand-off to the Auto supervisor (stage 2)
M.EVENT='server-pick-event.json'    -- the supervisor's last outcome, read by both monitors as history events
M.REQUEST_AGE=900;M.CONNECT_WAIT=60;M.SETTLE_WAIT=90
M.LOCKS={'/var/run/tunnel-switch-tid-%d.lock','/var/run/tunnel-switch-network-switch.lock'}
M.TEXT={[M.PICKED]='server of the channel changed',[M.FAILED]='server change of the channel failed',
  [M.WAITING]='the firmware is switching this channel itself; waiting',[M.LIMIT]='server change limit reached (4 per hour)',
  [M.CARRYING]='the channel carries traffic; its server is never changed',[M.OFF]='server pick is off',
  [M.REQUESTED]='server change handed to Auto',[M.DEFERRED]='Auto is not ready for a server change; waiting'}
local IFACE={openvpn='^ovpnclient[0-9]+$',wireguard='^wgclient[0-9]+$'}

local function none(v) return v==nil or v==NULL end
local function n0(v) if v==nil then return NULL end;return v end
local function is_list(v) return canon.is_array(v) end
local function is_dict(v) return canon.is_object(v) end
local function sized(s,low,high) return type(s)=='string' and #s>=low and #s<=high end
local function digits(v) if sized(v,1,9) and string.find(v,'^[0-9]+$') then return v end;return nil end
M.digits=digits
local function iface_ok(protocol,v) return IFACE[protocol]~=nil and sized(v,1,14) and string.find(v,IFACE[protocol])~=nil and #string.match(v,'[0-9]+$')<=4 end
local function strip(s) return (string.match(s,'^[ \t\r]*(.-)[ \t\r]*$')) end
local function lines_of(text)
  local out={};local start=1
  while true do
    local i=string.find(text,'\n',start,true)
    if not i then out[#out+1]=string.sub(text,start);return out end
    out[#out+1]=string.sub(text,start,i-1);start=i+1
  end
end
-- `[proto:]<group>_<id>` (Python _LINE): group, id or nil
local function line_parts(s)
  if type(s)~='string' then return nil end
  local proto,g,i=string.match(s,'^([a-z]+):([0-9]+)_([0-9]+)$')
  if proto then if #proto>16 then return nil end else g,i=string.match(s,'^([0-9]+)_([0-9]+)$') end
  if not g or #g>9 or #i>9 then return nil end
  return g,i
end
M.line_parts=line_parts
local function location(v)
  if not sized(v,1,64) or string.find(v,'[%z\1-\31\127]') or not canon.valid_utf8(v) or string.find(v,'\239\191\189',1,true) then return NULL end
  return v
end
M.location=location

-- milliseconds as a whole number (the same rounding in Python), nil when not a sane reading
function M.whole_ms(v)
  if canon.is_float(v) then v=canon.number(v) end
  if type(v)~='number' or v~=v or v<0 or v>60000 then return nil end
  return math.floor(v+0.5)
end

-- the value part of a `uci show` line -> list of strings ('a' 'b', 'it'\''s', bare words), nil when broken
function M.uci_values(raw)
  local out,token,i,n={},nil,1,#raw
  while i<=n do
    local c=string.sub(raw,i,i)
    if c=="'" then
      local e=string.find(raw,"'",i+1,true)
      if not e then return nil end
      token=(token or '')..string.sub(raw,i+1,e-1);i=e+1
    elseif string.sub(raw,i,i+1)=="\\'" then token=(token or '').."'";i=i+2
    elseif c==' ' or c=='\t' then
      if token then out[#out+1]=token;token=nil end
      i=i+1
    else token=(token or '')..c;i=i+1 end
  end
  if token then out[#out+1]=token end
  return out
end

-- `uci show` text (several configs) -> {config={section={['.type']=type, option=str | {str...}}}}
function M.parse_uci(text)
  local out={}
  if type(text)~='string' or #text>M.MAX_TEXT then return out end
  for _,line in ipairs(lines_of(text)) do
    local eq=string.find(line,'=',1,true)
    if eq then
      local key,raw=string.sub(line,1,eq-1),string.sub(line,eq+1)
      local parts={};for p in string.gmatch(key..'.','([^.]*)%.') do parts[#parts+1]=p end
      if #parts>=2 and #parts<=3 and sized(parts[1],1,32) and string.find(parts[1],'^[a-z_]+$') and sized(parts[2],1,64)
         and string.find(parts[2],'^[%w_@%[%]%-]+$') then
        local values=M.uci_values(raw)
        if values and #values>0 then
          out[parts[1]]=out[parts[1]] or {}
          local section=out[parts[1]][parts[2]] or {}
          out[parts[1]][parts[2]]=section
          if #parts==2 then section['.type']=values[1]
          elseif sized(parts[3],1,64) and string.find(parts[3],'^[%w_]+$') then section[parts[3]]=#values==1 and values[1] or values end
        end
      end
    end
  end
  return out
end

function M.parse_mark(v)
  if type(v)~='string' then return nil end
  local hex=string.match(v,'^0[xX]([0-9a-fA-F]+)$')
  if not hex or #hex>8 then return nil end
  return tonumber(hex,16)
end

-- route_policy rules with a tunnel id, a protocol and a profiles file, by tunnel id
function M.tunnels(uci)
  local rows={}
  for name,s in pairs(uci.route_policy or {}) do
    local protocol,tunnel,path=s.via_type,digits(s.tunnel_id),s.profiles
    if IFACE[protocol] and tunnel and sized(path,1,64) and string.find(path,'^/etc/vpn_profiles%.d/profile[0-9]+$') and #string.match(path,'[0-9]+$')<=9 then
      rows[#rows+1]={section=name,tunnel_id=tonumber(tunnel),protocol=protocol,interface=iface_ok(protocol,s.via) and s.via or nil,
        group_id=digits(s.group_id),current_id=digits(protocol=='openvpn' and s.client_id or s.peer_id),profiles=path,mark=M.parse_mark(s.mark)}
    end
  end
  table.sort(rows,function(a,b) if a.tunnel_id~=b.tunnel_id then return a.tunnel_id<b.tunnel_id end;return a.section<b.section end)
  local out={};for i=1,math.min(#rows,M.MAX_TUNNELS) do out[i]=rows[i] end
  return out
end

-- candidate lines of a profiles file -> {{profile, group_id, profile_id}}; blank, # and foreign lines skipped
function M.parse_profiles(text)
  local out,seen={},{}
  if type(text)~='string' or #text>M.MAX_TEXT then return out end
  for _,line in ipairs(lines_of(text)) do
    local s=strip(line)
    local g,i=line_parts(s)
    if g and not seen[s] then
      seen[s]=true;out[#out+1]={profile=s,group_id=g,profile_id=i}
      if #out>=M.MAX_CANDIDATES then break end
    end
  end
  return out
end

function M.hostname(v)
  if not sized(v,3,253) then return false end
  local parts=0
  for label in string.gmatch(v..'.','([^.]*)%.') do
    if not (#label>=1 and #label<=63 and string.find(label,'^[%w][%w%-]*$')) then return false end
    parts=parts+1
  end
  return parts>=2 and parts<=7
end

-- `network.interface dump` rows -> the device of the up non-VPN interface with the lowest-metric default route
function M.pick_uplink(rows)
  local best_metric,best
  for _,row in ipairs(is_list(rows) and rows or {}) do
    local name,device=is_dict(row) and row.interface,is_dict(row) and row.l3_device
    local skip=type(name)~='string' or string.find(name,'^wgclient') or string.find(name,'^ovpnclient') or string.find(name,'^wgserver')
      or string.find(name,'^ovpnserver') or string.find(name,'^lan') or string.find(name,'^loopback')
    if not skip and row.up==true and sized(device,1,15) and string.find(device,'^[%w_.%-]+$') then
      for _,route in ipairs(is_list(row.route) and row.route or {}) do
        if is_dict(route) and route.target=='0.0.0.0' and route.mask==0 then
          local metric=type(route.metric)=='number' and route.metric or 0
          if best_metric==nil or metric<best_metric then best_metric,best=metric,device end
        end
      end
    end
  end
  return best
end

function M.endpoints(protocol,section)
  local raw=type(section)=='table' and section[protocol=='openvpn' and 'remote' or 'end_point'] or nil
  local list=type(raw)=='string' and {raw} or (type(raw)=='table' and raw or {})
  local out={}
  for _,v in ipairs(list) do
    local host,port
    if type(v)=='string' then host,port=string.match(v,'^([%w][%w%.%-]*)[: ]([0-9]+)$') end
    if host and #host<=253 and #port<=5 and tonumber(port)>=1 and tonumber(port)<=65535 and #out<M.MAX_ENDPOINTS then
      out[#out+1]={host=host,port=tonumber(port)}
    end
  end
  -- Provider peers (NordVPN via GL) keep no end_point in uci; their name is the server host name (MT3000, 02.11.2026).
  local name=protocol=='wireguard' and #out==0 and type(section)=='table' and section.name or nil
  if M.hostname(name) then out[1]={host=name,port=51820} end
  return out
end

-- the tunnel's candidates with their server data: profile, config name, location, endpoints, current
local function filled(v)
  if type(v)=='string' then return string.find(v,'[^ \t]')~=nil end
  if type(v)=='table' then for _,x in ipairs(v) do if filled(x) then return true end end end
  return false
end

-- a candidate this supervisor may change to (server_pick.switchable: the reasons). OpenVPN: yes. WireGuard: a host:port
-- end_point, public_key and allowed_ips on the peer, private_key and an address on the peer or its group_<group_id>
function M.switchable(protocol,section,uci)
  if protocol=='openvpn' then return true end
  if type(section)~='table' then return false end
  local raw=section.end_point
  local list=type(raw)=='string' and {raw} or (type(raw)=='table' and raw or {})
  local ok=false
  for _,v in ipairs(list) do
    local host,port
    if type(v)=='string' then host,port=string.match(v,'^([%w][%w%.%-]*)[: ]([0-9]+)$') end
    if host and #host<=253 and #port<=5 and tonumber(port)>=1 and tonumber(port)<=65535 then ok=true end
  end
  if not ok then return false end
  local gid=digits(section.group_id)
  local group=gid and type(uci)=='table' and type(uci.wireguard)=='table' and uci.wireguard['group_'..gid] or nil
  if type(group)~='table' then group={} end
  local function either(key) return filled(section[key]) or filled(group[key]) end
  return filled(section.public_key) and filled(section.allowed_ips) and either('private_key') and (either('address_v4') or either('address_v6'))
end

function M.candidates(tunnel,profiles_text,uci)
  local rows={}
  for _,e in ipairs(M.parse_profiles(profiles_text)) do
    local config,section
    if tunnel.protocol=='openvpn' then config=e.group_id..'_'..e.profile_id;section=(uci.ovpnclient or {})[config]
    else config='peer_'..e.profile_id;section=(uci.wireguard or {})[config] end
    rows[#rows+1]={profile=e.profile,group_id=e.group_id,profile_id=e.profile_id,config=config,
      location=type(section)=='table' and location(section.location) or NULL,endpoints=M.endpoints(tunnel.protocol,section),
      switchable=M.switchable(tunnel.protocol,section,uci),
      current=e.profile_id==tunnel.current_id and (tunnel.group_id==nil or e.group_id==tunnel.group_id)}
  end
  return rows
end

local function quad(s)
  local a,b,c,d=string.match(s,'^([0-9]+)%.([0-9]+)%.([0-9]+)%.([0-9]+)$')
  return a~=nil and #a<=3 and #b<=3 and #c<=3 and #d<=3
end
local function decimal(s) local w,f=string.match(s,'^([0-9]+)%.?([0-9]*)$');return w~=nil and #w<=6 and #f<=6 and not (string.find(s,'%.$')) end
-- busybox/iputils ping output -> {address, avg_ms} (avg nil when nothing came back)
function M.parse_ping(text)
  local out={}
  if type(text)~='string' or #text>65536 then return out end
  for _,line in ipairs(lines_of(text)) do
    local ip=string.match(line,'^PING [^ ]+ %(([0-9.]+)%)')
    if ip and quad(ip) and out.address==nil then out.address=ip end
    local min,avg=string.match(line,'= ([0-9.]+)/([0-9.]+)/')
    if min and decimal(min) and decimal(avg) and (string.find(line,'round-trip',1,true) or string.find(line,'rtt',1,true)) then out.avg_ms=M.whole_ms(tonumber(avg)) end
  end
  return out
end

function M.ping_argv(host,device)
  local argv={};for i,v in ipairs(M.PING) do argv[i]=v end
  if device then argv[#argv+1]='-I';argv[#argv+1]=device end
  argv[#argv+1]=host
  return argv
end

-- -> {alive, latency_ms, address}; OpenVPN the fastest of TCP_SAMPLES connects (at most TCP_ATTEMPTS tries), WireGuard one
-- ping run. One connect varied 59-191 ms on the MT3000 (02.11.2026), too noisy for a 20 % margin.
function M.measure(protocol,row,io,device)
  local eps=row.endpoints
  if #eps==0 then return {alive=false,samples={}} end
  if protocol=='openvpn' then
    local best,host,samples=nil,nil,{}
    for attempt=0,M.TCP_ATTEMPTS-1 do
      local ep=eps[attempt%#eps+1]
      local ok,ms=pcall(io.tcp,ep.host,ep.port,M.TCP_TIMEOUT,device)
      ms=ok and M.whole_ms(ms) or nil
      if ms then
        samples[#samples+1]=ms
        if best==nil or ms<best then best,host=ms,ep.host end
        if #samples>=M.TCP_SAMPLES then break end
      end
    end
    if best then return {alive=true,latency_ms=best,address=host,samples=samples} end
    return {alive=false,samples={}}
  end
  local ok,_,text=pcall(io.exec,M.ping_argv(eps[1].host,device),M.PING_SECONDS)
  local parsed=M.parse_ping(ok and text or nil)
  return {alive=parsed.avg_ms~=nil,latency_ms=parsed.avg_ms,address=parsed.address,samples={parsed.avg_ms}}
end

-- live first, then by latency, then the file order (stable); not measured rows (alive nil) after dead ones
function M.rank(rows)
  local keyed={}
  for i,row in ipairs(rows) do keyed[i]={row=row,a=row.alive==true and 0 or (row.alive==false and 1 or 2),l=row.latency_ms or 60001,i=i} end
  table.sort(keyed,function(x,y) if x.a~=y.a then return x.a<y.a end;if x.l~=y.l then return x.l<y.l end;return x.i<y.i end)
  local out={};for i,k in ipairs(keyed) do out[i]=k.row end
  return out
end

-- the candidate to change to, or nil: the best live one when the current one is dead or unknown, otherwise only
-- when it is >= 20 % faster (best*5 <= current*4: whole numbers, the same in Python)
function M.decide(ranked)
  local best,current
  for _,row in ipairs(ranked) do
    if best==nil and row.alive==true and row.switchable~=false then best=row end
    if current==nil and row.current then current=row end
  end
  if best==nil or best==current then return nil end
  if current==nil or current.alive~=true then return best end
  if best.latency_ms*5<=current.latency_ms*4 then return best end
  return nil
end

-- the profiles file text with the best live non-current candidate right after the current line (the firmware's
-- round robin then takes it next); the other lines keep their order. Unchanged text when nothing is to move.
function M.plan_profiles_order(text,current,ranked)
  if type(text)~='string' then return text end
  local target
  for _,row in ipairs(ranked) do if row.alive==true and row.profile~=current then target=row.profile;break end end
  if target==nil or current==nil then return text end
  local lines=lines_of(text)
  local order,at,to,nat,nto={},nil,nil,0,0
  for i,line in ipairs(lines) do
    local s=strip(line)
    if line_parts(s) then
      order[#order+1]=i
      if s==current then at=i;nat=nat+1 end
      if s==target then to=i;nto=nto+1 end
    end
  end
  if nat~=1 or nto~=1 then return text end
  for k,i in ipairs(order) do if i==at and order[k%#order+1]==to then return text end end
  local moved=lines[to]
  local rest={};for i,line in ipairs(lines) do if i~=to then rest[#rest+1]=line end end
  local place=to<at and at or at+1  -- 1-based: insert at this index of rest
  table.insert(rest,place,moved)
  return table.concat(rest,'\n')
end

function M.changes_left(history,tunnel_id,now)
  local list=is_dict(history) and history[tostring(tunnel_id)] or nil
  local times=canon.array({})
  if is_list(list) then
    for _,t in ipairs(list) do
      local x=type(t)~='boolean' and canon.number(t) or nil
      if x and x>now-M.WINDOW and x<=now+5 then times[#times+1]=t end
    end
  end
  return M.CHANGES-#times,times
end

-- the firmware's own tunnel-switch.sh holds its lock (a live pid inside one of its lock files)
function M.vendor_busy(tunnel_id,io)
  for _,pattern in ipairs(M.LOCKS) do
    local path=string.find(pattern,'%d',1,true) and string.format(pattern,tunnel_id) or pattern
    local ok,text=pcall(io.read,path)
    local pid=ok and type(text)=='string' and digits(string.match(text,'^%s*(.-)%s*$')) or nil
    if pid and tonumber(pid)>1 then
      local aok,alive=pcall(io.alive,tonumber(pid))
      if not aok or alive then return true end
    end
  end
  return false
end

-- Stage 3 (WireGuard): tunnel-switch.sh switch_tunnel() calls update_provider_config <group> <peer> <iface> after
-- `uci commit network` and before ifdown/ifup; mirrored exactly, its result ignored like the script ignores it
-- (server_pick.PROVIDER_SCRIPT: the reasons and what is not mirrored). The same bytes as the Python constant. No
-- single quote in it: sys.exec refuses an argument with one (MT3000 02.11.2026 23:36: the step raised, see Python).
M.PROVIDER_SCRIPT=[[n=$(uci -q get wireguard.group_$1.group_name);case "$n" in Hideme|ExpressVPN) [ -n "$3" ] && ubus call gl-session call "{\"module\":\"wg_client\",\"func\":\"update_provider_config\",\"params\":{\"group_id\":$1,\"peer_id\":$2,\"instance\":\"$3\",\"update_all\":false}}";; PIA|IPVanish|NordVPN|PureVPN|XVPN) ubus call gl-session call "{\"module\":\"wg_client\",\"func\":\"update_provider_config\",\"params\":{\"group_id\":$1,\"peer_id\":$2,\"update_all\":false}}";; esac;exit 0]]

-- -> {code=nil | refusal, steps={argv...}}: tunnel-switch.sh's own writes for one idle interface
function M.switch_plan(tunnel,target,enabled,auto_on,carrying,busy,left)
  if left==nil then left=M.CHANGES end
  local function refuse(code) return {code=code,steps={}} end
  if enabled~=true or auto_on~=true then return refuse(M.OFF) end
  if carrying~=false then return refuse(M.CARRYING) end
  if busy then return refuse(M.WAITING) end
  if left<=0 then return refuse(M.LIMIT) end
  local section,iface=tunnel.section,tunnel.interface
  local group,profile=target and target.group_id,target and target.profile_id
  if not (sized(section,1,32) and string.find(section,'^[%w_]+$') and iface_ok(tunnel.protocol,iface) and digits(group) and digits(profile)) then
    return refuse(M.FAILED)
  end
  local rule='route_policy.'..section
  local own,other,config
  if tunnel.protocol=='openvpn' then own,other,config='client_id','peer_id',group..'_'..profile
  else own,other,config='peer_id','client_id','peer_'..profile end
  local steps={{'uci','set',rule..'.'..own..'='..profile},{'uci','-q','delete',rule..'.'..other},
    {'uci','set',rule..'.group_id='..group},{'uci','set','network.'..iface..'.config='..config},
    {'uci','set','network.'..iface..'.disabled=0'},{'uci','commit','route_policy'},{'uci','commit','network'}}
  if tunnel.protocol=='wireguard' then steps[#steps+1]={'sh','-c',M.PROVIDER_SCRIPT,'update_provider_config',group,profile,iface} end
  steps[#steps+1]={'ifdown',iface};steps[#steps+1]={'ifup',iface}
  return {code=nil,steps=steps}
end

-- runs the steps of a switch_plan -> {code, changed, committed, touched} (server_pick.run_plan: the meaning); only
-- behind the owner switch: refuses (OFF) unless enabled is exactly true
function M.run_plan(plan,io,enabled)
  local out={code=nil,changed=false,committed=false,touched=false}
  if enabled~=true then out.code=M.OFF;return out end
  if plan.code~=nil or #plan.steps==0 then out.code=plan.code or M.FAILED;return out end
  for _,argv in ipairs(plan.steps) do
    if argv[1]=='ifdown' or argv[1]=='ifup' then out.touched=true end
    local ok,rc=pcall(io.exec,argv,M.EXEC_SECONDS)
    if not ok then rc=nil end
    local quiet=false;for _,a in ipairs(argv) do if a=='-q' then quiet=true end end
    if rc==nil or (rc~=0 and not quiet) then  -- `uci -q delete` of an absent option is not a failure
      if argv[1]~='uci' then out.changed=true end
      out.code=M.FAILED;return out
    end
    out.changed=true
    if #argv==3 and argv[1]=='uci' and argv[2]=='commit' and argv[3]=='network' then out.committed=true end
  end
  out.code=M.PICKED
  return out
end

function M.execute(plan,io,enabled) return M.run_plan(plan,io,enabled).code end

M.NOT_CHANGED='not changed'

-- the log note of a failed change that wrote something and was rolled back (server_pick.rollback_note)
function M.rollback_note(undone,first,back)
  if undone==true then return 'rolled back' end
  if type(first)=='table' and first.touched==false and type(back)=='table' and back.committed==true and back.rebound==true then
    return 'rolled back (the tunnel was not restarted)'
  end
  return 'rollback failed'
end

------------------------------------------------------------------------------------------------------
-- stage 2: the Auto supervisor's side (lua/pair.lua / pair_auto.py)
------------------------------------------------------------------------------------------------------
-- the pair profile id of a server line (inventory.lua): openvpn:<group>_<id>, wireguard:peer_<id>
function M.profile_id(protocol,group,profile)
  if not digits(group) or not digits(profile) or IFACE[protocol]==nil then return nil end
  if protocol=='openvpn' then return 'openvpn:'..group..'_'..profile end
  return 'wireguard:peer_'..profile
end

local function finite(v) local x=type(v)~='boolean' and canon.number(v) or nil;return x~=nil and x==x and x~=math.huge and x~=-math.huge,x end

-- a hand-off of the monitor job that the supervisor may act on: complete, consistent and at most REQUEST_AGE old
function M.request_valid(row,now)
  if not is_dict(row) then return false end
  local ok,t=finite(row.time);local okn,n=finite(now)
  if not ok or not okn or n-t<0 or n-t>M.REQUEST_AGE then return false end
  local protocol,iface,section,tunnel=row.protocol,row.interface,row.section,row.tunnel_id
  if not iface_ok(protocol,iface) then return false end
  if not (sized(section,1,32) and string.find(section,'^[%w_]+$')) or type(tunnel)~='number' or tunnel%1~=0 then return false end
  if not digits(row.group_id) or not digits(row.profile_id) then return false end
  if not line_parts(row.from) or not line_parts(row.to) then return false end
  local g,i=line_parts(row.to)
  return g==row.group_id and i==row.profile_id and row.from~=row.to
end

-- the live tunnel of a valid hand-off: {tunnel, target, previous} or nil (stale: its server or rule moved).
-- Read again from uci here: the supervisor never trusts the RAM file for what it writes.
function M.claim(io,row,now)
  if not M.request_valid(row,now) then return nil end
  local ok,rc,out=pcall(io.exec,{'uci','-q','-X','show','route_policy'},M.EXEC_SECONDS)
  if not ok or rc~=0 or type(out)~='string' then return nil end
  for _,tunnel in ipairs(M.tunnels(M.parse_uci(out))) do
    if tunnel.tunnel_id==row.tunnel_id and tunnel.section==row.section and tunnel.protocol==row.protocol and tunnel.interface==row.interface then
      local group,current=tunnel.group_id,tunnel.current_id
      local g,i=line_parts(row.from)
      if group==nil or current==nil or g~=group or i~=current then return nil end
      return {tunnel=tunnel,target={group_id=row.group_id,profile_id=row.profile_id},previous={group_id=group,profile_id=current}}
    end
  end
  return nil
end

-- network.<iface>.config of a server (tunnel-switch.sh build_config_name): <group>_<id> for OpenVPN, peer_<id>
function M.network_config(protocol,group,profile)
  if not digits(group) or not digits(profile) or IFACE[protocol]==nil then return nil end
  if protocol=='openvpn' then return group..'_'..profile end
  return 'peer_'..profile
end

-- group_id, profile_id the route_policy rule of this tunnel names now, or nil (server_pick.live_server)
function M.live_server(io,tunnel)
  local ok,rc,out=pcall(io.exec,{'uci','-q','-X','show','route_policy'},M.EXEC_SECONDS)
  if not ok or rc~=0 or type(out)~='string' or type(tunnel)~='table' then return nil end
  for _,row in ipairs(M.tunnels(M.parse_uci(out))) do
    if row.tunnel_id==tunnel.tunnel_id and row.section==tunnel.section and row.protocol==tunnel.protocol and row.interface==tunnel.interface then
      if row.group_id~=nil and row.current_id~=nil then return row.group_id,row.current_id end
      return nil
    end
  end
  return nil
end

-- the supervisor's refusal of one hand-off, or nil (server_pick.gate): never the carrying tunnel; stage 2 the idle
-- reserve while the kernel proves the traffic on the primary and the pair rests, stage 3 the failed primary while the
-- kernel proves the traffic on the reserve after a COMMITTED automatic switch; never during a transition, a manual hold
-- or another pending change, and only a tunnel bound by its tunnel id. The role it changes: role_of(c).
function M.gate(c)
  if c.enabled~=true then return M.OFF end
  local role=nil
  if c.kernel_verified==true and (c.kernel_role=='source' or c.kernel_role=='target') then role=c.kernel_role end
  if role==nil or c.interface==c[role..'_interface'] then return M.CARRYING end  -- an unknown route is carrying (stage 1)
  if c.phase~='RUNNING' or M.role_of(c)==nil or not none(c.manual_hold) or c.pending==true or c.anchored~=true then return M.DEFERRED end
  if c.busy==true then return M.WAITING end
  local left=c.left
  if type(left)~='number' or left%1~=0 or left<=0 then return M.LIMIT end
  return nil
end

-- the pair role of the requested idle tunnel the gate may change, or nil (server_pick.role_of)
function M.role_of(c)
  if c.kernel_verified~=true then return nil end
  if c.kernel_role=='source' and c.interface==c.target_interface and (none(c.journal_phase) or c.journal_phase=='ROLLED-BACK') then return 'target' end
  if c.kernel_role=='target' and c.interface==c.source_interface and c.journal_phase=='COMMITTED' and c.journal_manual~=true then return 'source' end
  return nil
end

local function copy(value) return canon.decode(canon.encode(value)) end
local function sorted(list) local out={};for i,x in ipairs(list) do out[i]=x end;table.sort(out);return canon.array(out) end
local function same_strings(a,b)
  if not is_list(a) or not is_list(b) or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end
local RENAMED={'before','after','restored_order','restore_target_order','restore_before_order','restore_order_origin'}
-- the session after its own server change of one idle tunnel: state, journal or nil (server_pick.rebind; see there).
-- role 'target' (stage 2) compares the live order with the session order and renames a finished ROLLED-BACK journal;
-- role 'source' (stage 3) compares it with the session order with the pair rules swapped (the COMMITTED journal's
-- after) and re-binds that open journal (orders, pair context, source id, vendor_profiles.source.id, hash) so that the
-- session check holds; a journal already re-bound is accepted. error(FAILED) for anything but that one rule moving.
function M.rebind(state,journal,order,hash,profile,role)
  role=role or 'target'
  local function fail() error(M.FAILED,0) end
  local old=is_dict(state) and state.order or nil
  local roles=is_dict(state) and state.policy_roles or nil
  if (role~='source' and role~='target') or not is_list(old) or not is_list(order) or #old~=#order or not is_dict(roles) or type(profile)~='string'
     or not (type(hash)=='string' and #hash==64 and string.find(hash,'^[a-f0-9]+$')) then fail() end
  local seen={}
  for i=1,#order do
    if type(old[i])~='string' or type(order[i])~='string' or seen[order[i]] then fail() end
    seen[order[i]]=true
  end
  local expected={};for i,x in ipairs(old) do expected[i]=x end
  if role=='source' then
    local context=is_dict(journal) and journal.pair_transition or nil
    local a,b,live
    for i,x in ipairs(old) do if x==roles.source_rule then a=i end;if x==roles.target_rule then b=i end end
    for i,x in ipairs(order) do if x==roles.target_rule then live=i end end
    if not is_dict(context) or journal.phase~='COMMITTED' or a==nil or b==nil or live==nil
       or (journal.source~=roles.source_id and journal.source~=profile) or (context.source_id~=roles.source_id and context.source_id~=profile) then fail() end
    -- the two pair rules stand live as the reserve rule (its id does not change in stage 3) says: the session order is
    -- the order at Start and may already be the reserve-first one (MT3000 02.11.2026, OpenVPN primary: the
    -- always-swapped expectation refused a correct change - SERVER-PICK-FAILED, rollback failed)
    if old[live]~=roles.target_rule then expected[a],expected[b]=expected[b],expected[a] end
  end
  local moved={}
  for i=1,#expected do if expected[i]~=order[i] then moved[#moved+1]=i end end
  if #moved>1 or (#moved==1 and expected[moved[1]]~=roles[role..'_rule']) then fail() end
  local names={};for _,i in ipairs(moved) do names[expected[i]]=order[i] end
  local function name(x) local v=names[x];if v==nil then return x end;return v end
  local function rename(values) local out={};for i,x in ipairs(values) do out[i]=name(x) end;return canon.array(out) end
  local value=copy(state);local previous_hash=value.policy_hash
  value.order=rename(old);value.policy_hash=hash
  local r=copy(roles)
  r[role..'_rule']=name(roles[role..'_rule']);r.generic_rules=sorted(rename(is_list(roles.generic_rules) and roles.generic_rules or {}));r[role..'_id']=profile
  value.policy_roles=r
  if is_dict(value.selected_policy) and is_list(value.selected_policy.order) then
    value.selected_policy.order=rename(value.selected_policy.order);value.selected_policy.hash=hash
  end
  if not is_dict(journal) or journal.phase~=(role=='source' and 'COMMITTED' or 'ROLLED-BACK') then return value,nil end
  local renamed=copy(journal)
  for _,key in ipairs(RENAMED) do
    if is_list(renamed[key]) then renamed[key]=rename(renamed[key]) end
  end
  local step=renamed.restore_order_step
  if is_dict(step) then for _,key in ipairs({'before','after'}) do if is_list(step[key]) then step[key]=rename(step[key]) end end end
  local context=renamed.pair_transition
  if is_dict(context) then
    for _,key in ipairs({'source_rule','target_rule'}) do if type(context[key])=='string' then context[key]=name(context[key]) end end
    if is_list(context.generic_rules) then context.generic_rules=sorted(rename(context.generic_rules)) end
    for _,key in ipairs({'session_order','primary_order'}) do if is_list(context[key]) then context[key]=rename(context[key]) end end
  end
  if renamed.hash==previous_hash then renamed.hash=hash end
  if role=='source' then
    context.source_id=profile;renamed.source=profile
    local proofs=renamed.vendor_profiles
    if is_dict(proofs) and is_dict(proofs.source) then proofs.source.id=profile end
    if not same_strings(renamed.after,order) or renamed.hash~=hash or not same_strings(context.session_order,value.order) then fail() end
    for key,item in pairs(r) do if canon.encode(context[key]==nil and NULL or context[key])~=canon.encode(item) then fail() end end
  end
  return value,renamed
end

-- the supervisor's change of one tunnel: counted in the rate-limit history (count), shown (change), and the time of
-- the hand-off it took (taken: a hand-off is acted on once, also after a rollback) (STATE)
function M.record(io,tunnel_id,now,change,count,taken)
  if count==nil then count=true end
  local okstate,state=pcall(function() return canon.decode(io.read(io.runtime..'/'..M.STATE) or '{}') end)
  if not okstate or not is_dict(state) then state=canon.object() end
  local history=is_dict(state.changes) and state.changes or canon.object()
  local last=is_dict(state.last) and state.last or canon.object()
  local _,times=M.changes_left(history,tunnel_id,now)
  if count then times[#times+1]=now end
  history[tostring(tunnel_id)]=times
  if change~=nil then last[tostring(tunnel_id)]=change end
  local value=canon.object({changes=history,last=last})
  if taken==nil and finite(state.taken) then taken=state.taken end
  if taken~=nil then value.taken=taken end
  local ok,wrote=pcall(io.write,io.runtime..'/'..M.STATE,canon.encode(value))
  return ok and wrote==true
end

-- one outcome of the supervisor: the history event file (EVENT, both monitors read it) and the system log line;
-- the same refusal of the same hand-off is published once
function M.event(io,code,tunnel,now,change,request,note)
  local okp,previous=pcall(function() return canon.decode(io.read(io.runtime..'/'..M.EVENT) or 'null') end)
  if not okp then previous=nil end
  local rows=is_dict(previous) and previous.tunnels or nil
  if request~=nil and is_dict(previous) and previous.request==request and is_list(rows) and #rows==1 and is_dict(rows[1]) and rows[1].code==code then
    return false
  end
  local value=canon.object({time=now,request=n0(request),tunnels=canon.array({canon.object({tunnel_id=tunnel.tunnel_id,code=code})})})
  pcall(io.write,io.runtime..'/'..M.EVENT,canon.encode(value))
  if io.log then pcall(io.log,M.log_line(code,tunnel,change)..(note and ('; '..note) or '')) end
  return true
end

local function public_row(row)
  return canon.object({profile=row.profile,location=row.location,latency_ms=n0(row.latency_ms),alive=n0(row.alive)})
end

------------------------------------------------------------------------------------------------------
-- the Bayesian pick (owner setting server_pick_model 'bayes'; 'simple' = the 20 % rule above). Python twin:
-- server_pick.py (the same arithmetic, order and fixed-point file; shared cases server_pick_bayes_cases.json). Per
-- server: Normal-Inverse-Gamma posterior of log RTT on every sample, Beta availability, evidence decaying with
-- HALF_LIFE; a working server is replaced only when P(candidate faster by >= MARGIN) >= 0.95 (z >= Z_CHANGE); a
-- deterministic UCB bandit picks which servers a round measures (the current one, unknown, stale and plausible best).
------------------------------------------------------------------------------------------------------
M.MODEL='server-pick-model.json'
M.HALF_LIFE=3600;M.PRIOR_A=2;M.PRIOR_B_E4=1600;M.MARGIN_PCT=0;M.Z_CHANGE_E3=1645;M.Z_PLAUSIBLE_E3=2000
M.STALE=3600;M.AVAILABLE_PCT=80;M.MODEL_MAX=64;M.MODEL_AGE=604800
local LN2=0.6931471805599453
local MODEL_LIMITS={2147483647,100000000,200000,1000000000,100000000,100000000,1}  -- t, n*1000, mu*1e4, SS*1e4, ok*1000, bad*1000, alive

-- the owner setting server_pick_model: 'bayes' or 'simple' (anything else is the simple rule)
function M.model_name(v) if v=='bayes' then return 'bayes' end;return 'simple' end
local function q(v,scale) return math.floor(v*scale+0.5) end
function M.model_key(tunnel_id,profile) return string.format('%d',tunnel_id)..':'..profile end
local function model_key_ok(k)
  if type(k)~='string' then return false end
  local tid,rest=string.match(k,'^([0-9]+):(.+)$')
  return tid~=nil and #tid<=9 and line_parts(rest)~=nil
end

-- a stored entry [t, n*1000, mu*1e4, SS*1e4, ok*1000, bad*1000, alive] checked, else nil
function M.model_entry(raw)
  if not is_list(raw) or #raw~=7 then return nil end
  for i=1,7 do
    local v=raw[i]
    if type(v)~='number' or v~=v or v%1~=0 or v<0 or v>MODEL_LIMITS[i] then return nil end
  end
  return raw
end

-- {key=entry} of the MODEL file; broken entries (and a broken file) are left out
function M.model_read(io_)
  local ok,value=pcall(function() return canon.decode(io_.read(io_.runtime..'/'..M.MODEL) or '{}') end)
  local rows=ok and is_dict(value) and value.servers or nil
  local out={}
  if is_dict(rows) then
    for k,raw in pairs(rows) do
      local entry=M.model_entry(raw)
      if model_key_ok(k) and entry then out[k]=entry end
    end
  end
  return out
end

-- the MODEL file text: entries not older than MODEL_AGE, at most MODEL_MAX (the newest; ties by key)
function M.model_text(model,now)
  local keys={}
  for k,e in pairs(model) do if now-e[1]<=M.MODEL_AGE then keys[#keys+1]=k end end
  table.sort(keys,function(a,b) if model[a][1]~=model[b][1] then return model[a][1]>model[b][1] end;return canon.key_less(a,b) end)
  local servers=canon.object()
  for i=1,math.min(#keys,M.MODEL_MAX) do
    local e=model[keys[i]];local copy=canon.array({});for j=1,7 do copy[j]=e[j] end
    servers[keys[i]]=copy
  end
  return canon.encode(canon.object({servers=servers,version=1}))
end

-- the decayed evidence of an entry at `now`, or nil
function M.model_state(entry,now)
  if entry==nil then return nil end
  local f=math.exp(-math.max(0,now-entry[1])*LN2/M.HALF_LIFE)
  return {t=entry[1],n=entry[2]/1000*f,mu=entry[3]/10000,ss=entry[4]/10000*f,ok=entry[5]/1000*f,bad=entry[6]/1000*f,alive=entry[7]==1}
end

-- the entry after one round: samples (ms) of a server that answered, or nil/{} for one that did not
function M.model_update(entry,now,samples)
  local s=M.model_state(entry,now) or {n=0,mu=0,ss=0,ok=0,bad=0}
  local n,mu,ss,ok,bad,alive=s.n,s.mu,s.ss,s.ok,s.bad,0
  local xs={}
  for _,x in ipairs(samples or {}) do xs[#xs+1]=math.log(math.max(1,canon.number(x))) end
  if #xs>0 then
    local k,total=#xs,0.0
    for _,x in ipairs(xs) do total=total+x end
    local mean,inner=total/k,0.0
    for _,x in ipairs(xs) do inner=inner+(x-mean)*(x-mean) end
    local m,d=n+k,mean-mu
    mu=mu+k*d/m;ss=ss+inner+n*k*d*d/m;n=m;ok=ok+1;alive=1
  else bad=bad+1 end
  return canon.array({math.floor(now),math.min(q(n,1000),100000000),math.min(math.max(q(mu,10000),0),200000),math.min(q(ss,10000),1000000000),
    math.min(q(ok,1000),100000000),math.min(q(bad,1000),100000000),alive})
end

-- mu and the variance of mu of a decayed state, nil with less than one sample of evidence
function M.posterior(state)
  if state==nil or state.n<1 then return nil end
  local n=state.n
  return {state.mu,(M.PRIOR_B_E4/10000+state.ss/2)/(n*(M.PRIOR_A+n/2-1))}
end

-- Beta(ok+1, bad+1) mean, percent
function M.availability(state)
  if state==nil then return 50 end
  return 100*(state.ok+1)/(state.ok+state.bad+2)
end

-- which rows this round measures (index -> true): the current one, unknown and stale ones, and the plausible best
function M.probe_plan(rows,states,now)
  local z=M.Z_PLAUSIBLE_E3/1000
  local posts,upper={},nil
  for i=1,#rows do
    posts[i]=M.posterior(states[i])
    if posts[i] and states[i].alive then
      local u=posts[i][1]+z*math.sqrt(posts[i][2])
      if upper==nil or u<upper then upper=u end
    end
  end
  local plan={}
  for i,row in ipairs(rows) do
    local p,s=posts[i],states[i]
    plan[i]=i<=M.MAX_MEASURED and (row.current==true or p==nil or now-s.t>=M.STALE or upper==nil or p[1]-z*math.sqrt(p[2])<=upper)
  end
  return plan
end

-- the candidate to change to, or nil (server_pick.py decide_bayes)
function M.decide_bayes(rows,states)
  local current,cp,eligible=nil,nil,{}
  for i,row in ipairs(rows) do
    local p=M.posterior(states[i])
    if row.current then current,cp=row,p
    elseif row.alive==true and row.switchable~=false and p then eligible[#eligible+1]={row=row,p=p,s=states[i]} end
  end
  if #eligible==0 then return nil end
  if current==nil or current.alive~=true or cp==nil then
    local best=nil
    for _,e in ipairs(eligible) do if best==nil or e.p[1]<best.p[1] then best=e end end
    return best.row
  end
  local margin=-math.log(1-M.MARGIN_PCT/100)
  local best=nil
  for _,e in ipairs(eligible) do
    if M.availability(e.s)>=M.AVAILABLE_PCT then
      local z=(cp[1]-e.p[1]-margin)/math.sqrt(cp[2]+e.p[2])
      if z>=M.Z_CHANGE_E3/1000 and (best==nil or e.p[1]<best.p[1]) then best=e end
    end
  end
  return best and best.row or nil
end

-- measure the rows the bandit picks (all of them when the current server does not answer), update the model in
-- place, give every row its published reading -> target or nil, the number of measured servers
function M.bayes_round(tunnel,rows,model,io_,device,now)
  local keys,states={},{}
  for i,row in ipairs(rows) do keys[i]=M.model_key(tunnel.tunnel_id,row.profile);states[i]=M.model_state(model[keys[i]],now) end
  local plan=M.probe_plan(rows,states,now)
  local measured,count={},0
  local function run(i)
    local m=M.measure(tunnel.protocol,rows[i],io_,device)
    rows[i].alive,rows[i].latency_ms,rows[i].address=m.alive,m.latency_ms,m.address
    model[keys[i]]=M.model_update(model[keys[i]],now,m.alive and m.samples or nil)
    states[i]=M.model_state(model[keys[i]],now);measured[i]=true;count=count+1
  end
  local dead=false
  for i,row in ipairs(rows) do
    if plan[i] then run(i);if row.current and row.alive~=true then dead=true end
    else row.alive,row.latency_ms,row.address=nil,nil,nil end
  end
  if dead then for i=1,math.min(#rows,M.MAX_MEASURED) do if not measured[i] then run(i) end end end
  local target=M.decide_bayes(rows,states)
  for i,row in ipairs(rows) do
    local p=M.posterior(states[i])
    if not measured[i] and states[i]~=nil then row.alive=states[i].alive end
    if row.alive==true and p then row.latency_ms=M.whole_ms(math.exp(p[1])) end
  end
  return target,count
end

function M.log_line(code,tunnel,change)
  local line=string.format('%s: %s (tunnel %d %s)',code,M.TEXT[code],tunnel.tunnel_id,tunnel.protocol)
  if change then
    local function name(l,p) if not none(l) then return l end;if not none(p) then return p end;return '?' end
    local function ms(v) if none(v) then return '?' end;return tostring(canon.number(v)) end
    line=line..': '..name(change.from_location,change.from)..' -> '..name(change.to_location,change.to)..', '..ms(change.from_ms)..' -> '..ms(change.to_ms)..' ms'
  end
  return line
end

-- one round: read, (measure, order, switch when enabled), write the published block; returns it.
-- request: {enabled=bool, auto_on=bool, failed={interface...}, model='simple'|'bayes' (absent: simple)}; the Bayesian
-- model (bayes_round) only changes which servers are measured, the published readings and the choice of the target
function M.job(io,request,now)
  request=is_dict(request) and request or canon.object()
  local enabled,auto_on=request.enabled==true,request.auto_on==true
  local bayes=enabled and M.model_name(request.model)=='bayes'
  local model=bayes and M.model_read(io) or nil
  local failed={}
  if is_list(request.failed) then for _,x in ipairs(request.failed) do if type(x)=='string' then failed[x]=true end end end
  local parts={}
  for _,config in ipairs({'route_policy','ovpnclient','wireguard'}) do
    local ok,rc,out=pcall(io.exec,{'uci','-q','-X','show',config},M.EXEC_SECONDS)
    if ok and rc==0 and type(out)=='string' then parts[#parts+1]=out..'\n' end
  end
  local uci=M.parse_uci(table.concat(parts))
  local okstate,state=pcall(function() return canon.decode(io.read(io.runtime..'/'..M.STATE) or '{}') end)
  if not okstate or not is_dict(state) then state=canon.object() end
  local history=is_dict(state.changes) and state.changes or canon.object()
  local last=is_dict(state.last) and state.last or canon.object()
  local device=nil
  if enabled and io.wan then device=io.wan() end
  local active,active_read=nil,false
  local result=canon.object({time=now,enabled=enabled,tunnels=canon.array({})})
  for _,tunnel in ipairs(M.tunnels(uci)) do
    local okp,profiles=pcall(io.read,tunnel.profiles)
    if not okp then profiles=nil end
    local rows=M.candidates(tunnel,profiles,uci)
    local current=nil
    for _,row in ipairs(rows) do if row.current then current=row.profile;break end end
    local code,ordered,target=nil,false,nil
    if bayes then target=M.bayes_round(tunnel,rows,model,io,device,now)
    else
      for index,row in ipairs(rows) do
        if enabled and index<=M.MAX_MEASURED then
          local m=M.measure(tunnel.protocol,row,io,device)
          row.alive,row.latency_ms,row.address=m.alive,m.latency_ms,m.address
        else row.alive,row.latency_ms,row.address=nil,nil,nil end
      end
    end
    local ranked=M.rank(rows)
    local best=nil
    for _,row in ipairs(ranked) do if row.alive==true then best=row.profile;break end end
    if enabled and type(profiles)=='string' then
      local planned=M.plan_profiles_order(profiles,current,ranked)
      if planned~=profiles then
        local okw,wrote=pcall(io.write,tunnel.profiles,planned)
        ordered=okw and wrote==true
      end
    end
    if not bayes then target=M.decide(ranked) end
    local key=tostring(tunnel.tunnel_id)
    if enabled and target~=nil and tunnel.interface~=nil and failed[tunnel.interface] then
      if not active_read then
        active_read=true
        local oka,mark=pcall(io.active_mark)
        active=oka and mark~=NULL and mark or nil
      end
      local carrying=active==nil or tunnel.mark==nil or tunnel.mark==active
      local left,times=M.changes_left(history,tunnel.tunnel_id,now)
      local plan=M.switch_plan(tunnel,target,enabled,auto_on,carrying,M.vendor_busy(tunnel.tunnel_id,io),left)
      code=plan.code
      if code==nil then
        -- Stage 2: only the Auto supervisor changes a server (inside its lock, without a pair readopt).
        local old=nil
        for _,row in ipairs(rows) do if row.current then old=row;break end end
        local hand=canon.object({time=now,tunnel_id=tunnel.tunnel_id,protocol=tunnel.protocol,interface=tunnel.interface,section=tunnel.section,
          from=n0(current),to=target.profile,group_id=target.group_id,profile_id=target.profile_id,from_ms=old and n0(old.latency_ms) or NULL,
          to_ms=n0(target.latency_ms),from_location=old and old.location or NULL,to_location=target.location})
        local okw,wrote=pcall(io.write,io.runtime..'/'..M.CHANGE,canon.encode(hand))
        code=(okw and wrote==true) and M.REQUESTED or M.FAILED
      end
      if M.EVENT_CODES[code] and io.log then pcall(io.log,M.log_line(code,tunnel,nil)) end
    end
    local candidates=canon.array({})
    for i,row in ipairs(rows) do candidates[i]=public_row(row) end
    result.tunnels[#result.tunnels+1]=canon.object({tunnel_id=tunnel.tunnel_id,protocol=tunnel.protocol,interface=n0(tunnel.interface),
      current=n0(current),best=n0(best),ordered=ordered,code=n0(code),last_change=n0(last[key]),candidates=candidates})
  end
  if bayes then pcall(function() io.write(io.runtime..'/'..M.MODEL,M.model_text(model,now)) end) end
  pcall(io.write,io.runtime..'/'..M.RESULT,canon.encode(result))
  return result
end

------------------------------------------------------------------------------------------------------
-- the monitor's side
------------------------------------------------------------------------------------------------------
-- interfaces of channels whose last check failed (not inactive, not skipped by the check limit), sorted
function M.failed_interfaces(profiles)
  local out,seen=canon.array({}),{}
  if type(profiles)~='table' then return out end
  for _,row in ipairs(profiles) do
    if is_dict(row) or (type(row)=='table' and not is_list(row)) then
      local code,iface=row.code,row.interface
      if type(code)=='string' and code~='PROFILE-INACTIVE' and code~='CHECK-LIMIT' and type(iface)=='string' and not seen[iface] then
        seen[iface]=true;out[#out+1]=iface
      end
    end
  end
  table.sort(out)
  return out
end

-- a new round is due: never ran, MEASURE_EVERY seconds passed, or a channel failed that was not failed before
-- {failed,retried}: previous_failed without the channels the last round skipped because they still carried the
-- traffic, once RETRY_CARRYING s passed, and at most once per failure (retried; the caller drops a channel from it when
-- the channel recovers). The round a failure starts often runs before Auto moved the traffic to the reserve (MT3000
-- 02.11.2026, SERVER-PICK-CARRYING and no server change); a channel that keeps carrying gets no further rounds
function M.carrying_retry(picked,previous_failed,retried,last_start,clock)
  local failed,done={},{}
  for _,x in ipairs(previous_failed or {}) do failed[#failed+1]=x end
  for _,x in ipairs(retried or {}) do done[#done+1]=x end
  if last_start==nil or last_start==NULL or clock-last_start<M.RETRY_CARRYING or type(picked)~='table' or type(picked.tunnels)~='table' then
    return {failed=failed,retried=done}
  end
  local skipped,was,keep={},{},{}
  for _,row in ipairs(picked.tunnels) do if type(row)=='table' and row.code==M.CARRYING and type(row.interface)=='string' then skipped[row.interface]=true end end
  for _,x in ipairs(done) do was[x]=true end
  for _,x in ipairs(failed) do if skipped[x] and not was[x] then done[#done+1]=x else keep[#keep+1]=x end end
  return {failed=keep,retried=done}
end

function M.due(last_start,previous_failed,failed,clock)
  if last_start==nil or last_start==NULL or clock-last_start>=M.MEASURE_EVERY then return true end
  local before={};for _,x in ipairs(previous_failed or {}) do before[x]=true end
  for _,x in ipairs(failed) do if not before[x] then return true end end
  return false
end

local function stamp_ok(v) local x=canon.number(v);return type(v)~='boolean' and x~=nil and x==x and x~=math.huge and x~=-math.huge end
local function ms_ok(v) if none(v) then return true end;local x=canon.number(v);return type(v)~='boolean' and x~=nil and M.whole_ms(x)==x end
local function line_or_null(v) if type(v)=='string' and line_parts(v) then return v end;return NULL end

-- a last_change record checked field by field: NULL (none yet), false (malformed) or the copy
function M.project_change(change)
  if none(change) then return NULL end
  if not is_dict(change) or not stamp_ok(change.time) then return false end
  local out=canon.object({time=change.time})
  for _,k in ipairs({'from','to'}) do
    local v=change[k]
    if not none(v) and not (type(v)=='string' and line_parts(v)) then return false end
    out[k]=n0(v)
  end
  for _,k in ipairs({'from_ms','to_ms'}) do
    if not ms_ok(change[k]) then return false end
    out[k]=n0(change[k])
  end
  out.from_location=location(change.from_location);out.to_location=location(change.to_location)
  return out
end

-- the checked copy of server-pick.json for the status (both monitors), or nil
function M.project(value)
  if not is_dict(value) or type(value.enabled)~='boolean' or not is_list(value.tunnels) then return nil end
  if not stamp_ok(value.time) or canon.number(value.time)<0 then return nil end
  local tunnels=canon.array({})
  for t=1,math.min(#value.tunnels,M.MAX_TUNNELS) do
    local row=value.tunnels[t]
    if not is_dict(row) or not IFACE[row.protocol] or not is_list(row.candidates) then return nil end
    local list=canon.array({})
    for i=1,math.min(#row.candidates,M.MAX_CANDIDATES) do
      local c=row.candidates[i]
      if not is_dict(c) or not (type(c.profile)=='string' and line_parts(c.profile)) then return nil end
      if not ms_ok(c.latency_ms) or not (none(c.alive) or type(c.alive)=='boolean') then return nil end
      list[i]=canon.object({profile=c.profile,location=location(c.location),latency_ms=n0(c.latency_ms),alive=n0(c.alive)})
    end
    local change=M.project_change(row.last_change)
    if change==false then return nil end
    local id=row.tunnel_id
    tunnels[t]=canon.object({tunnel_id=(type(id)=='number' and id%1==0) and id or NULL,protocol=row.protocol,
      interface=iface_ok(row.protocol,row.interface) and row.interface or NULL,current=line_or_null(row.current),best=line_or_null(row.best),
      ordered=row.ordered==true,code=M.CODES[row.code] and row.code or NULL,last_change=change,candidates=list})
  end
  return canon.object({time=value.time,enabled=value.enabled,tunnels=tunnels})
end

-- history events of a finished round newer than `seen` (one per tunnel with an event code)
function M.events(result,seen)
  local out=canon.array({})
  if not is_dict(result) or not stamp_ok(result.time) then return out end
  if seen~=nil and seen~=NULL and canon.number(result.time)<=canon.number(seen) then return out end
  for _,row in ipairs(is_list(result.tunnels) and result.tunnels or {}) do
    if is_dict(row) and M.EVENT_CODES[row.code] then
      out[#out+1]=canon.object({time=result.time,code=row.code,tunnel_id=n0(row.tunnel_id)})
    end
  end
  return out
end

------------------------------------------------------------------------------------------------------
-- the router's io (Lua runtime) and the child entry
------------------------------------------------------------------------------------------------------
function M.router_io(runtime)
  local sys=require('sys')
  local okn,nixio=pcall(require,'nixio')
  if not (okn and type(nixio)=='table') then nixio=nil end
  local io_={runtime=runtime or sys.RUNTIME}
  function io_.read(path)
    local f=io.open(path,'rb');if not f then return nil end
    local text=f:read(M.MAX_TEXT);f:close();return text or ''
  end
  -- durable leaves its files 0600; the firmware's own profiles file keeps the usual 0644 (the same as agent.py writes it)
  function io_.write(path,text)
    local ok=pcall(sys.write_atomic,path,text)
    if ok and string.find(path,'^/etc/vpn_profiles%.d/') then sys.exec({'chmod','644',path},{timeout=5}) end
    return ok
  end
  function io_.exec(argv,seconds) return sys.exec(argv,{timeout=seconds}) end
  -- non-blocking connect, then poll for writability within the timeout; SO_ERROR tells the result. Timed with the
  -- microsecond wall clock: sys.clock (/proc/uptime) has 10 ms steps, too coarse for a 20 ms connect.
  function io_.tcp(host,port,timeout,device)
    if not (nixio and nixio.socket and nixio.poll) then return nil end
    local sock=nixio.socket('inet','stream')
    if not sock then return nil end
    local ok,ms=pcall(function()
      if device then assert(sock:setopt('socket','bindtodevice',device)) end
      assert(sock:setblocking(false))
      local started=sys.wall()
      local done,code=sock:connect(host,port)
      if not done then
        local inprogress=(nixio.const and nixio.const.EINPROGRESS) or 115
        if code~=inprogress then return nil end
        local count=nixio.poll({{fd=sock,events=nixio.poll_flags('out')}},math.floor(timeout*1000))
        if type(count)~='number' or count<1 or sock:getopt('socket','error')~=0 then return nil end
      end
      return (sys.wall()-started)*1000
    end)
    pcall(function() sock:close() end)
    return ok and ms or nil
  end
  function io_.alive(pid) return sys.exists('/proc/'..string.format('%d',pid)) end
  -- the uplink that holds the default route: wan, or wwan when the router is a Wi-Fi repeater (MT3000, 02.11.2026)
  function io_.wan()
    local rc,out=sys.exec({'ubus','call','network.interface','dump'},{timeout=5})
    local ok,data=pcall(canon.decode,rc==0 and out or '')
    return M.pick_uplink(ok and is_dict(data) and data.interface or nil)
  end
  function io_.active_mark()
    local kernel=require('kernel')
    local rc,out=sys.exec({'iptables-save','-t','mangle'},{timeout=10})
    if rc~=0 then return nil end
    return M.parse_mark(require('dns_mark').active_from_chains(kernel.parse_mangle(kernel.snapshot(out)),kernel.fields))
  end
  function io_.log(line) sys.exec({'logger','-t','homensai-vpn',line},{timeout=5}) end
  return io_
end

-- `lua server_pick.lua job <runtime>/server-pick-request.json`: one round of the monitor, in a child process
function M.main(argv)
  local sys=require('sys')
  if argv[1]~='job' or argv[2]~=sys.RUNTIME..'/'..M.REQUEST then return 2 end
  local io_=M.router_io(sys.RUNTIME)
  local ok,request=pcall(function() return canon.decode(io_.read(argv[2]) or 'null') end)
  M.job(io_,ok and request or nil,sys.wall())
  return 0
end

if arg and arg[0] and string.find(arg[0],'server_pick%.lua$') and arg[1] then os.exit(M.main(arg)) end

return M
