-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- dns_dual.lua: LAN DNS through both tunnels at once (dns_dual.py, the same behaviour). Owner option, default OFF:
--   uci set homensai_vpn.main.dns_dual='1'; uci commit homensai_vpn
--
-- GL 4.11 (firmware audit, /usr/bin/setup_instance): every VPN instance runs its own dnsmasq, `dhcp.<instance>` with
-- conf-dir /tmp/dnsmasq.d.<instance> holding `mark=<mark>` (wgclientN 0x1000.., port 2053+100N; ovpnclientN 0xa000..,
-- port 4053+100N). That mark is set on every upstream socket and `ip rule fwmark <mark>/0xf000 lookup <table>` sends it
-- into the tunnel; the table also has a blackhole, so a down tunnel never falls back to the WAN. The GL module
-- dns_mark (dns_mark.lua) redirects LAN DNS to the instance of the ACTIVE tunnel. With a lossy or dead active tunnel
-- every LAN lookup waits for that one tunnel.
--
-- While Auto runs (the supervisor's verified pass, backend dns_mark_follow) each instance of the pair gets one snippet
-- in its own conf-dir:
--     all-servers
--     server=<upstream of the OTHER tunnel>@<other tunnel device>
-- dnsmasq then sends every upstream query through its own tunnel (the GL mark, unchanged) AND through the other
-- tunnel, and answers with the first reply. `@device` is SO_BINDTODEVICE: the kernel sends such a socket only through
-- that device (a missing route is "on link" via the device; a missing device fails the bind) - never via the WAN.
-- Only `all-servers` and `server=<IPv4>[#port]@<wgclientN|ovpnclientN>` lines are ever written.
--   * the other tunnel's upstreams: the `server=` lines of its generated /var/etc/dnsmasq.conf.<instance> plus, unless
--     `no-resolv`, the nameservers of its resolv-file (GL's own values, any provider). None now (tunnel down, file
--     emptied): the servers this program installed last (no restart because a tunnel is down);
--   * a changed snippet: written atomically, `dnsmasq --test` on the instance config, `/etc/init.d/dnsmasq restart
--     <instance>`, procd must report it running; the active instance (the dns_mark mark) is restarted last.
--     A failure restores the previous snippet (none: GL's own config), code DNS-DUAL-UNVERIFIED, and the same text
--     is not retried by this process;
--   * fewer than two GL instances recognised (other firmware, instance not running): nothing changes,
--     code DNS-DUAL-UNAVAILABLE;
--   * off(): option off, Auto stopped (backend unguard), package removal (prerm): every snippet is removed and its
--     instance restarted - GL's own configuration again. /tmp is RAM: a reboot removes the snippets too.
local canon=require('canon')

local M={}
M.FILE='homensai-dns-dual.conf'
M.CONF='/var/etc/dnsmasq.conf.'
M.CONFDIR='/tmp/dnsmasq.d.'
M.INIT='/etc/init.d/dnsmasq'
M.DNSMASQ='/usr/sbin/dnsmasq'
M.SETTINGS='/etc/config/homensai_vpn'
M.UNAVAILABLE='DNS-DUAL-UNAVAILABLE'
M.UNVERIFIED='DNS-DUAL-UNVERIFIED'
M.MAX_SERVERS=4
M.MAX_TEXT=16384
M.NAMES={'wgclient1','wgclient2','wgclient3','wgclient4','wgclient5',
         'ovpnclient1','ovpnclient2','ovpnclient3','ovpnclient4','ovpnclient5'}
M.HEADER='# HomenS.AI Auto VPN: LAN DNS through both tunnels (dns_dual). Generated; removed when Auto stops.'
M.memo={}  -- instance -> snippet text whose install failed in this process (not retried until the text changes)
local NULL=canon.null

local function lines_of(text)
  local out={}
  for line in string.gmatch(text..'\n','([^\n]*)\n') do out[#out+1]=line end
  return out
end
local function trim(s) return string.match(s,'^[ \t\n\r\f\v]*(.-)[ \t\n\r\f\v]*$') end

-- enabled(text of /etc/config/homensai_vpn): only an explicit `option dns_dual '1'` turns it on
function M.enabled(text)
  if type(text)~='string' then return false end
  for _,line in ipairs(lines_of(text)) do
    if string.find(line,"^[ \t\n\r\f\v]*option[ \t\n\r\f\v]+dns_dual[ \t\n\r\f\v]+'?1'?[ \t\n\r\f\v]*$") then return true end
  end
  return false
end

function M.valid_name(name)
  return type(name)=='string' and (string.find(name,'^wgclient[1-5]$')~=nil or string.find(name,'^ovpnclient[1-5]$')~=nil)
end

-- '0x1000' -> 'wgclient1', '0xb000' -> 'ovpnclient2' (GL setup_instance: 0x1000+0x1000*(N-1), 0xa000+0x1000*(N-1))
function M.instance_of(mark)
  if type(mark)~='string' or #mark<3 or #mark>10 or not string.find(mark,'^0x[0-9a-f]+$') then return nil end
  local n=tonumber(string.sub(mark,3),16)
  if n%4096~=0 then return nil end
  local h=n/4096
  if h>=1 and h<=5 then return 'wgclient'..string.format('%d',h) end
  if h>=10 and h<=14 then return 'ovpnclient'..string.format('%d',h-9) end
  return nil
end

local function octet(t)
  if not string.find(t,'^[0-9]+$') or #t>3 or (#t>1 and string.sub(t,1,1)=='0') then return nil end
  local n=tonumber(t)
  if n>255 then return nil end
  return n
end
-- valid_server('103.86.99.100') / ('10.8.0.1#5353'): a routable unicast IPv4 address, optional port; no names,
-- no IPv6, no loopback/link-local/multicast (a local DNS proxy of the router cannot be reached through a tunnel)
function M.valid_server(entry)
  if type(entry)~='string' or #entry>21 then return false end
  local ip,port=string.match(entry,'^([0-9.]+)#([0-9]+)$')
  if not ip then ip=entry end
  local a,b,c,d=string.match(ip,'^([0-9]+)%.([0-9]+)%.([0-9]+)%.([0-9]+)$')
  if not a then return false end
  a,b,c,d=octet(a),octet(b),octet(c),octet(d)
  if not (a and b and c and d) then return false end
  if a==0 or a==127 or a>=224 or (a==169 and b==254) then return false end
  if port then
    if #port>5 or string.sub(port,1,1)=='0' then return false end
    local p=tonumber(port)
    if p<1 or p>65535 then return false end
  end
  return true
end

local function safe_resolv(path)
  return type(path)=='string' and #path<=128 and string.find(path,'^/tmp/[A-Za-z0-9._/-]+$')~=nil
    and string.find(path,'..',1,true)==nil
end

-- servers_of(config, read): the upstreams of an instance from its generated /var/etc/dnsmasq.conf.<instance>
-- (`server=` lines, then the resolv-file nameservers unless `no-resolv`), valid ones only, each once, at most 4
function M.servers_of(config,read)
  local out,seen={},{}
  local function add(s)
    if #out<M.MAX_SERVERS and M.valid_server(s) and not seen[s] then seen[s]=true;out[#out+1]=s end
  end
  if type(config)~='string' then return out end
  local noresolv,resolv=false,nil
  for _,raw in ipairs(lines_of(config)) do
    local line=trim(raw)
    if line=='no-resolv' then noresolv=true end
    local v=string.match(line,'^server=(.*)$')
    if v then add(v) end
    local r=string.match(line,'^resolv%-file=(.*)$')
    if r then resolv=r end
  end
  if not noresolv and safe_resolv(resolv) then
    local ok,text=pcall(read,resolv)
    if ok and type(text)=='string' then
      for _,raw in ipairs(lines_of(text)) do
        local ns=string.match(raw,'^[ \t\n\r\f\v]*nameserver[ \t\n\r\f\v]+([^ \t\n\r\f\v]+)[ \t\n\r\f\v]*$')
        if ns then add(ns) end
      end
    end
  end
  return out
end

-- confdir_of(config): the conf-dir of a generated instance config (without a ',*.conf' filter), or nil
function M.confdir_of(config)
  if type(config)~='string' then return nil end
  local found=nil
  for _,raw in ipairs(lines_of(config)) do
    local v=string.match(trim(raw),'^conf%-dir=(.*)$')
    if v then found=string.match(v,'^([^,]*)') end
  end
  return found
end

-- mark_matches(text of <conf-dir>/mark, '0x1000'): GL's `mark=0x1000` for exactly this mark
function M.mark_matches(text,mark)
  if type(text)~='string' or type(mark)~='string' or not string.find(mark,'^0x[0-9a-f]+$') or #mark>10 then return false end
  local hex=string.match(trim(text),'^mark=0[xX]([0-9a-fA-F]+)$')
  if not hex or #hex>8 then return false end
  return tonumber(hex,16)==tonumber(string.sub(mark,3),16)
end

-- snippet(peers): the conf-dir file for one instance; peers = {{device, servers={...}}, ...}; nil when no server
function M.snippet(peers)
  local lines={M.HEADER,'all-servers'}
  for _,p in ipairs(peers) do
    for _,s in ipairs(p.servers) do lines[#lines+1]='server='..s..'@'..p.device end
  end
  if #lines==2 then return nil end
  return table.concat(lines,'\n')..'\n'
end

-- parse_snippet(text) -> {device={servers...}}: what this program installed (the sticky servers of a down tunnel)
function M.parse_snippet(text)
  local out={}
  if type(text)~='string' then return out end
  for _,raw in ipairs(lines_of(text)) do
    local s,device=string.match(trim(raw),'^server=([0-9.#]+)@([a-z0-9]+)$')
    if s and M.valid_server(s) and M.valid_name(device) then
      out[device]=out[device] or {}
      local list=out[device]
      local dup=false
      for _,x in ipairs(list) do if x==s then dup=true end end
      if not dup and #list<M.MAX_SERVERS then list[#list+1]=s end
    end
  end
  return out
end

-- marks_from_chains(chains, fields): the marks of every TUNNEL<id>_ROUTE_POLICY jump of ROUTE_POLICY, in order
function M.marks_from_chains(chains,fields)
  local out,seen=canon.array({}),{}
  if type(chains)~='table' or type(chains.ROUTE_POLICY)~='table' then return out end
  for _,tokens in ipairs(chains.ROUTE_POLICY) do
    local ok,entry=pcall(fields,tokens)
    local target=ok and entry['-j'] or nil
    if type(target)=='string' and string.find(target,'^TUNNEL[0-9]+_ROUTE_POLICY$') then
      for _,rule in ipairs(chains[target] or {}) do
        local fok,set=pcall(fields,rule)
        if fok and set['-j']=='MARK' and type(set['--set-xmark'])=='string' then
          local value=string.match(set['--set-xmark'],'^([0-9]+)/[0-9]+$')
          local n=value and tonumber(value) or nil
          if n and n>0 and n<=0x7fffffff then
            local mark=string.format('0x%x',n)
            if not seen[mark] then seen[mark]=true;out[#out+1]=mark end
          end
          break
        end
      end
    end
  end
  return out
end

------------------------------------------------------------------------------------------------------
-- file and command access; tests pass opts.read / write / remove / run
------------------------------------------------------------------------------------------------------
local function default_read(path)
  local f=io.open(path,'rb')
  if not f then return nil end
  local text=f:read(M.MAX_TEXT+1)
  f:close()
  if text==nil then return '' end
  if #text>M.MAX_TEXT then return nil end
  return text
end
local function default_write(path,text)
  local directory=string.match(path,'^(.*)/[^/]+$')
  local tmp=directory..'/.'..M.FILE..'.tmp'
  local f=io.open(tmp,'wb')
  if not f then error('dns_dual: write',0) end
  local ok=f:write(text)
  local closed=f:close()
  if not ok or not closed then os.remove(tmp);error('dns_dual: write',0) end
  local renamed=os.rename(tmp,path)
  if not renamed then os.remove(tmp);error('dns_dual: rename',0) end
end
local function default_remove(path)
  os.remove(path)
  local f=io.open(path,'rb')
  if f then f:close();error('dns_dual: remove',0) end
end
local function default_run(argv,timeout)
  return require('sys').exec(argv,{timeout=timeout})
end
M.default_io={read=default_read,write=default_write,remove=default_remove}  -- tests: the real file access
local function access(opts)
  opts=opts or {}
  return {read=opts.read or default_read,write=opts.write or default_write,remove=opts.remove or default_remove,
          run=opts.run or default_run}
end
local function safe_read(io_,path)
  local ok,text=pcall(io_.read,path)
  if ok and type(text)=='string' then return text end
  return nil
end
local function run(io_,argv,timeout)
  local ok,rc,out=pcall(io_.run,argv,timeout)
  if not ok then return 255,'' end
  return tonumber(rc) or 255,type(out)=='string' and out or ''
end

-- procd reports the instance running (`ubus call service list {"name":"dnsmasq"}`)
local function running(io_,name)
  local rc,out=run(io_,{'ubus','call','service','list','{"name":"dnsmasq"}'},5)
  if rc~=0 then return false end
  local ok,value=pcall(canon.decode,out)
  if not ok or not canon.is_object(value) then return false end
  local service=value.dnsmasq
  local instances=canon.is_object(service) and service.instances or nil
  local instance=canon.is_object(instances) and instances[name] or nil
  return canon.is_object(instance) and instance.running==true
end

-- apply(x, want): bring one instance's snippet to `want` (nil: none); x.current follows what is on disk
local function apply(io_,x,want,result)
  if x.current==want then return end
  if want~=nil and M.memo[x.name]==want then result.code=M.UNVERIFIED;return end
  local path=x.dir..'/'..M.FILE
  local previous=x.current
  local function put(text) if text==nil then io_.remove(path) else io_.write(path,text) end end
  local ok=pcall(put,want)
  local restarted=false
  if ok and want~=nil then ok=run(io_,{M.DNSMASQ,'--test','-C',M.CONF..x.name},10)==0 end
  if ok then
    restarted=true
    -- an installed snippet must come up running; a removal only restarts (the instance may be gone with the pair)
    ok=run(io_,{M.INIT,'restart',x.name},30)==0 and (want==nil or running(io_,x.name))
  end
  if ok then
    x.current=want;M.memo[x.name]=nil;result.changed=result.changed+1
    return
  end
  result.code=M.UNVERIFIED
  if want==nil then x.current=safe_read(io_,path);return end
  -- back to what the instance ran before (GL's own configuration when nothing was installed)
  M.memo[x.name]=want
  pcall(put,previous)
  if restarted then run(io_,{M.INIT,'restart',x.name},30) end
  x.current=safe_read(io_,path)
end

local function row(x,peers)
  return canon.object({instance=x.name,mark=x.mark or NULL,installed=x.current~=nil,peers=peers or canon.array({})})
end
local function new_result(enabled)
  return canon.object({enabled=enabled,code=NULL,changed=0,instances=canon.array({})})
end

-- failed(): the result of a sync that could not run to its end (an unexpected Lua error)
function M.failed()
  return canon.object({enabled=NULL,code=M.UNVERIFIED,changed=0,instances=canon.array({})})
end

-- sync(marks, opts): every recognised GL instance of the pair gets the other tunnels' upstreams. opts.active: the
-- mark LAN DNS uses now (dns_mark), restarted last.
function M.sync(marks,opts)
  opts=opts or {}
  local io_=access(opts)
  local result=new_result(true)
  local usable,seen={},{}
  for _,mark in ipairs(type(marks)=='table' and marks or {}) do
    local name=M.instance_of(mark)
    if name and not seen[name] then
      seen[name]=true
      local dir=M.CONFDIR..name
      local conf=safe_read(io_,M.CONF..name)
      if M.confdir_of(conf)==dir and M.mark_matches(safe_read(io_,dir..'/mark'),mark) then
        usable[#usable+1]={name=name,mark=mark,conf=conf,dir=dir,current=safe_read(io_,dir..'/'..M.FILE)}
      end
    end
  end
  if #usable<2 then result.code=M.UNAVAILABLE;return result end
  local servers={}
  for _,p in ipairs(usable) do
    local list=M.servers_of(p.conf,function(path) return safe_read(io_,path) end)
    if #list==0 then
      for _,x in ipairs(usable) do
        local got=x~=p and M.parse_snippet(x.current)[p.name] or nil
        if got and #got>0 then list=got;break end
      end
    end
    servers[p.name]=list
  end
  local order={}
  for _,x in ipairs(usable) do if x.mark~=opts.active then order[#order+1]=x end end
  for _,x in ipairs(usable) do if x.mark==opts.active then order[#order+1]=x end end
  local rows={}
  for _,x in ipairs(order) do
    local peers,shown={},canon.array({})
    for _,p in ipairs(usable) do
      if p~=x and #servers[p.name]>0 then
        peers[#peers+1]={device=p.name,servers=servers[p.name]}
        local copy=canon.array({})
        for i,s in ipairs(servers[p.name]) do copy[i]=s end
        shown[#shown+1]=canon.object({device=p.name,servers=copy})
      end
    end
    apply(io_,x,M.snippet(peers),result)
    rows[x.name]=row(x,shown)
  end
  for _,x in ipairs(usable) do result.instances[#result.instances+1]=rows[x.name] end
  return result
end

-- off(opts): no snippet anywhere (option off, Auto stopped, package removal)
function M.off(opts)
  local io_=access(opts)
  local result=new_result(false)
  M.memo={}  -- the next start tries every text again
  for _,name in ipairs(M.NAMES) do
    local dir=M.CONFDIR..name
    local current=safe_read(io_,dir..'/'..M.FILE)
    if current~=nil then
      local x={name=name,dir=dir,current=current}
      apply(io_,x,nil,result)
      result.instances[#result.instances+1]=row(x)
    end
  end
  return result
end

-- follow(chains, fields, opts): the supervisor's verified pass. The owner option decides; off removes leftovers.
function M.follow(chains,fields,opts)
  opts=opts or {}
  local io_=access(opts)
  if not M.enabled(safe_read(io_,opts.settings or M.SETTINGS)) then return M.off(opts) end
  return M.sync(M.marks_from_chains(chains,fields),opts)
end

-- summary(result): one log line (DNS-DUAL-SYNC)
function M.summary(result)
  local parts={}
  for _,r in ipairs(type(result)=='table' and type(result.instances)=='table' and result.instances or {}) do
    parts[#parts+1]=tostring(r.instance)..(r.installed and '+' or '-')
  end
  local code=result and result.code
  return 'DNS-DUAL-SYNC: enabled '..tostring(result and result.enabled==true)..' changed '..tostring(result and result.changed)
    ..' code '..((code==nil or code==NULL) and 'none' or tostring(code))..' instances '..(#parts>0 and table.concat(parts,',') or 'none')
end

return M
