-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- server_endpoint.lua: the Lua port of server_endpoint.py - the read-only public peer address of a live VPN
-- client, bound to the interface (ifindex) and, for OpenVPN, to the client process epoch.
--
--   local E=require('server_endpoint')
--   E.observe(profile, now, fs)        -> {profile,interface,host,port,transport,time,source} | nil   (no cache)
--   E.Observer(fs, options):observe(profile, now)                                              (the monitor's)
--
-- Same output fields, rules and refusals as server_endpoint.observe: never keys, credentials, configuration,
-- DNS results or names; exactly one peer or nothing; the interface ifindex read before and after; the OpenVPN
-- process start time (the epoch, /proc/<pid>/stat field 22) read before and after its sockets; 0.5 s bound.
-- Internal refusals carry the same ENDPOINT-* codes (ENDPOINT-ADDRESS, ENDPOINT-PROC, ENDPOINT-READ-LIMIT,
-- ENDPOINT-PROCESS-EPOCH) and end in nil, as Python's caught ValueError/OSError end in None.
--
-- fs (monitor_io.endpoint_fs() on the router, fakes in tests):
--   fs.read(path, limit) -> up to limit+1 bytes | nil when the file does not exist | false on another error
--   fs.readlink(path) -> target | nil       fs.dir(path) -> names (without . and ..) | nil
--   fs.clock() -> monotonic seconds         fs.wg(interface) -> `wg show <if> endpoints` output | nil on failure
--
-- Cost (Observer): WireGuard spawns `wg` only when the tunnel epoch (interface ifindex) changed or the last
-- reading is older than REFRESH seconds (RETRY after a failed reading); every other pass reads one sysfs file
-- and republishes the confirmed peer with the time of this pass. OpenVPN: /proc reads only, every pass (its
-- peer can move inside the same process and interface, so it is never cached).
-- Deliberate differences from Python 3.9 ipaddress: int() of a port accepts only ASCII digits/underscores
-- (Python also takes other Unicode digits; the inputs here are ASCII-checked first, so the results agree).
local M={}
M.SOURCE='live-kernel-peer'
M.DEADLINE=0.5
M.REFRESH=300   -- seconds: a confirmed WireGuard peer is re-read with `wg` at least this often
M.RETRY=60      -- seconds: after no WireGuard peer, the next `wg` call for the same epoch

local Refused={}
local function fail(code) error(setmetatable({code=code},Refused),0) end
M.Refused=Refused
local function refused(err) return type(err)=='table' and getmetatable(err)==Refused end

-- str.strip() / str.split() of an ASCII text (Python whitespace incl. \x1c-\x1f)
local WS='[%s\28-\31]'
local function strip(s) return (string.match(s,'^'..WS..'*(.-)'..WS..'*$')) end
local function split(s) local out={};for w in string.gmatch(s,'[^%s\28-\31]+') do out[#out+1]=w end;return out end
-- str.splitlines() of an ASCII text
local function splitlines(text)
  local lines={}
  local normalized=string.gsub(string.gsub(text,'\r\n','\n'),'[\r\v\f\28\29\30]','\n')
  for line in string.gmatch(normalized..(string.sub(normalized,-1)=='\n' and '' or '\n'),'([^\n]*)\n') do lines[#lines+1]=line end
  return lines
end
local function ascii(text) if string.find(text,'[\128-\255]') then fail('ENDPOINT-ASCII') end;return text end
M.strip,M.split,M.splitlines=strip,split,splitlines

-- int(text) of Python for an ASCII text: whitespace, a sign, digits with single underscores between them
local function py_int(text,base)
  local s=strip(text)
  local sign,body=string.match(s,'^([+-]?)(.*)$')
  local digits=base==16 and '%x' or '%d'
  if base==16 then
    local rest=string.match(body,'^0[xX](.*)$')
    if rest then body=string.match(rest,'^_?(.*)$') end
  end
  if not string.find(body,'^'..digits..'+$') and not string.find(body,'^'..digits..'[_'..digits..']*'..digits..'$') then fail('ENDPOINT-ADDRESS') end
  if string.find(body,'__',1,true) then fail('ENDPOINT-ADDRESS') end
  local n=tonumber((string.gsub(body,'_','')),base)
  if not n then fail('ENDPOINT-ADDRESS') end
  return sign=='-' and -n or n
end

------------------------------------------------------------------------------------------------------
-- ipaddress.ip_address(text) of Python 3.9 (IPv4 first, then IPv6 with an optional %scope)
------------------------------------------------------------------------------------------------------
local function parse_v4(text)
  local parts={}
  for part in string.gmatch(text..'.','([^.]*)%.') do parts[#parts+1]=part end
  if #parts~=4 then return nil end
  local out={}
  for i,part in ipairs(parts) do
    if not string.find(part,'^%d%d?%d?$') or (#part>1 and string.sub(part,1,1)=='0') then return nil end
    local n=tonumber(part)
    if n>255 then return nil end
    out[i]=n
  end
  return out
end
local function hextet(text)
  if #text<1 or #text>4 or not string.find(text,'^%x+$') then return nil end
  return tonumber(text,16)
end
local function parse_v6(text)
  local scope=nil
  local at=string.find(text,'%',1,true)
  if at then
    scope=string.sub(text,at+1);text=string.sub(text,1,at-1)
    if scope=='' or string.find(scope,'%',1,true) then return nil end
  end
  if text=='' then return nil end
  local parts={}
  for part in string.gmatch(text..':','([^:]*):') do parts[#parts+1]=part end
  if #parts<3 then return nil end
  if string.find(parts[#parts],'.',1,true) then
    local v4=parse_v4(table.remove(parts))
    if not v4 then return nil end
    parts[#parts+1]=string.format('%x',v4[1]*256+v4[2]);parts[#parts+1]=string.format('%x',v4[3]*256+v4[4])
  end
  local n=#parts
  if n>9 then return nil end
  local skip=nil
  for i=2,n-1 do
    if parts[i]=='' then
      if skip then return nil end
      skip=i
    end
  end
  local hi,lo,skipped
  if skip then
    hi=skip-1;lo=n-skip
    if parts[1]=='' then hi=hi-1;if hi~=0 then return nil end end
    if parts[n]=='' then lo=lo-1;if lo~=0 then return nil end end
    skipped=8-(hi+lo)
    if skipped<1 then return nil end
  else
    if n~=8 or parts[1]=='' or parts[n]=='' then return nil end
    hi,lo,skipped=n,0,0
  end
  local out={}
  for i=1,hi do local h=hextet(parts[i]);if not h then return nil end;out[#out+1]=h end
  for _=1,skipped do out[#out+1]=0 end
  for i=n-lo+1,n do local h=hextet(parts[i]);if not h then return nil end;out[#out+1]=h end
  return out,scope
end
-- ipaddress._BaseV6._compress_hextets: the first longest run (>1) of zero hextets becomes '::'
local function format_v6(h,scope)
  local best_start,best_len,start,len=-1,0,-1,0
  for i=1,8 do
    if h[i]==0 then
      len=len+1;if start==-1 then start=i end
      if len>best_len then best_len=len;best_start=start end
    else len=0;start=-1 end
  end
  local parts={}
  for i=1,8 do parts[i]=string.format('%x',h[i]) end
  if best_len>1 then
    local out={}
    if best_start==1 then out[1]='' end
    for i=1,best_start-1 do out[#out+1]=parts[i] end
    out[#out+1]=''
    for i=best_start+best_len,8 do out[#out+1]=parts[i] end
    if best_start+best_len-1==8 then out[#out+1]='' end
    parts=out
  end
  return table.concat(parts,':')..(scope and ('%'..scope) or '')
end
local function v4_text(o) return o[1]..'.'..o[2]..'.'..o[3]..'.'..o[4] end

-- the checks of server_endpoint.address on a parsed address -> host text
local function checked(kind,value,scope,port)
  if kind==4 then
    local a=value[1]
    if (a==0 and value[2]==0 and value[3]==0 and value[4]==0) or a==127 or (a>=224 and a<=239) then fail('ENDPOINT-ADDRESS') end
  else
    local zero=true
    for i=1,7 do if value[i]~=0 then zero=false end end
    if (zero and (value[8]==0 or value[8]==1)) or value[1]>=0xff00 then fail('ENDPOINT-ADDRESS') end
  end
  if not (port>=1 and port<=65535) then fail('ENDPOINT-ADDRESS') end
  if kind==4 then return v4_text(value) end
  if value[1]==0 and value[2]==0 and value[3]==0 and value[4]==0 and value[5]==0 and value[6]==0xffff then
    return v4_text({math.floor(value[7]/256),value[7]%256,math.floor(value[8]/256),value[8]%256})
  end
  return format_v6(value,scope)
end
local function parse_ip(text)
  local v4=parse_v4(text)
  if v4 then return 4,v4 end
  if string.find(text,'/',1,true) then fail('ENDPOINT-ADDRESS') end
  local v6,scope=parse_v6(text)
  if v6 then return 6,v6,scope end
  fail('ENDPOINT-ADDRESS')
end

-- server_endpoint.address("host:port" | "[v6]:port") -> host, port; raises ENDPOINT-ADDRESS
function M.address(value)
  if type(value)~='string' or #value>100 then fail('ENDPOINT-ADDRESS') end
  local host,port
  if string.sub(value,1,1)=='[' then
    local rest=string.sub(value,2)
    local a,b=string.find(rest,']:',1,true)
    if not a or string.find(rest,']:',b+1,true) then fail('ENDPOINT-ADDRESS') end
    host,port=string.sub(rest,1,a-1),string.sub(rest,b+1)
  else
    local at=string.match(value,'^.*():')
    if not at then fail('ENDPOINT-ADDRESS') end
    host,port=string.sub(value,1,at-1),string.sub(value,at+1)
  end
  local kind,parsed,scope=parse_ip(host)
  local number=py_int(port,10)
  return checked(kind,parsed,scope,number),number
end

-- server_endpoint.proc_address: "0100007F:04AA" of /proc/net/{tcp,udp}[6] -> host, port
function M.proc_address(value,ipv6)
  local fields={}
  for part in string.gmatch(value..':','([^:]*):') do fields[#fields+1]=part end
  if #fields~=2 then fail('ENDPOINT-PROC') end
  local host,port=fields[1],fields[2]
  if #host%2~=0 or not string.find(host,'^%x*$') then fail('ENDPOINT-PROC') end
  if #host~=(ipv6 and 32 or 8) then fail('ENDPOINT-PROC') end
  local raw={}
  for i=1,#host,2 do raw[#raw+1]=tonumber(string.sub(host,i,i+1),16) end
  local number=py_int(port,16)
  if not ipv6 then return checked(4,{raw[4],raw[3],raw[2],raw[1]},nil,number),number end
  local h={}
  for g=0,3 do  -- each 32-bit word is in host (little-endian) order
    local b=raw[g*4+1]+raw[g*4+2]*256+raw[g*4+3]*65536+raw[g*4+4]*16777216
    h[g*2+1]=math.floor(b/65536);h[g*2+2]=b%65536
  end
  return checked(6,h,nil,number),number
end

-- server_endpoint.socket_peers -> {key -> {host,port,transport}} (a set)
function M.socket_peers(text,inodes,transport,ipv6)
  local peers={}
  if #text>65536 then return peers end
  local lines=splitlines(text)
  for i=2,#lines do
    local fields=split(lines[i])
    if #fields>=10 and inodes[fields[10]] and not (transport=='tcp' and fields[4]~='01') then
      local ok,host,port=pcall(M.proc_address,fields[3],ipv6)
      if ok then peers[host..'|'..port..'|'..transport]={host,port,transport}
      elseif not refused(host) then error(host,0) end
    end
  end
  return peers
end

-- server_endpoint.process_epoch: the start time of /proc/<pid>/stat (field 22, after the command name)
function M.process_epoch(text)
  local close=string.match(text,'^.*()%)')
  if not close then fail('ENDPOINT-PROCESS-EPOCH') end
  local fields=split(string.sub(text,close+1))
  if #fields<=19 then fail('ENDPOINT-PROCESS-EPOCH') end
  local value=fields[20]
  if not string.find(value,'^%d+$') then fail('ENDPOINT-PROCESS-EPOCH') end
  return value
end

------------------------------------------------------------------------------------------------------
-- observe
------------------------------------------------------------------------------------------------------
local function interface_ok(s)
  if type(s)~='string' then return false end
  local digits=string.match(s,'^wgclient(%d+)$') or string.match(s,'^ovpnclient(%d+)$')
  return digits~=nil and #digits<=4
end
local function profile_ok(s)
  if type(s)~='string' then return false end
  local rest=string.match(s,'^wireguard:(.*)$') or string.match(s,'^openvpn:(.*)$')
  return rest~=nil and #rest>=1 and #rest<=80 and string.find(rest,'^[A-Za-z0-9_.:-]+$')~=nil
end
function M.valid(profile)
  local interface,identifier,protocol=profile.interface,profile.id,profile.protocol
  return interface_ok(interface) and profile_ok(identifier) and (protocol=='openvpn' or protocol=='wireguard')
    and string.sub(identifier,1,#protocol+1)==protocol..':'
end

-- server_endpoint._read: missing -> Lua nil (Python FileNotFoundError), more than limit -> ENDPOINT-READ-LIMIT
local function read(fs,path,limit)
  local data=fs.read(path,limit)
  if data==nil then return nil end
  if type(data)~='string' then fail('ENDPOINT-READ') end
  if #data>limit then fail('ENDPOINT-READ-LIMIT') end
  return ascii(data)
end
local function need(value) if value==nil then fail('ENDPOINT-MISSING') end;return value end

local NET={{'tcp','tcp',false},{'tcp6','tcp',true},{'udp','udp',false},{'udp6','udp',true}}

local function observe(profile,now,fs)
  local interface,identifier=profile.interface,profile.id
  local until_=fs.clock()+M.DEADLINE
  local ifindex_path='/sys/class/net/'..interface..'/ifindex'
  local index=strip(need(read(fs,ifindex_path,32)))
  local peers={}
  if profile.protocol=='wireguard' and string.sub(interface,1,8)=='wgclient' then
    local raw=fs.wg(interface)
    if raw==nil then fail('ENDPOINT-COMMAND') end
    if #raw>4096 then return nil end
    for _,line in ipairs(splitlines(ascii(raw))) do
      local parts=split(line)
      if #parts~=2 then return nil end
      local host,port=M.address(parts[2])
      peers[host..'|'..port..'|udp']={host,port,'udp'}
    end
  elseif profile.protocol=='openvpn' and string.sub(interface,1,10)=='ovpnclient' then
    local pid=strip(need(read(fs,'/var/run/ovpnclient-'..interface..'.pid',32)))
    if not string.find(pid,'^%d+$') then return nil end
    local n=tonumber(pid)
    if not (n>1 and n<2^31) then return nil end
    local process='/proc/'..pid
    if strip(need(read(fs,process..'/comm',64)))~='openvpn' then return nil end
    local epoch=M.process_epoch(need(read(fs,process..'/stat',4096)))
    local cmdline=string.match(need(read(fs,process..'/cmdline',16384)),'^%z*(.-)%z*$')
    local args={}
    for arg in string.gmatch(cmdline..'\0','([^%z]*)%z') do args[#args+1]=arg end
    local count,at=0,nil
    for i,arg in ipairs(args) do if arg=='--dev' then count=count+1;at=at or i end end
    if count~=1 or at+1>#args or args[at+1]~=interface then return nil end
    local names=fs.dir(process..'/fd')
    if names==nil then fail('ENDPOINT-FD') end
    local inodes={}
    for i,name in ipairs(names) do
      if i>256 or fs.clock()>until_ then return nil end
      local target=fs.readlink(process..'/fd/'..name)
      local inode=type(target)=='string' and string.match(target,'^socket:%[(%d+)%]$')
      if inode and #inode<=20 then inodes[inode]=true end
    end
    for _,net in ipairs(NET) do
      if fs.clock()>until_ then return nil end
      local text=read(fs,process..'/net/'..net[1],65536)
      if text then for key,peer in pairs(M.socket_peers(text,inodes,net[2],net[3])) do peers[key]=peer end end
    end
    -- the process may perform more than one connection: never guess
    if M.process_epoch(need(read(fs,process..'/stat',4096)))~=epoch then return nil end
  else return nil end
  local only,count=nil,0
  for _,peer in pairs(peers) do only=peer;count=count+1 end
  if fs.clock()>until_ or count~=1 or strip(need(read(fs,ifindex_path,32)))~=index then return nil end
  return {profile=identifier,interface=interface,host=only[1],port=only[2],transport=only[3],time=now,source=M.SOURCE}
end

-- observe(profile, now, fs): server_endpoint.observe without a cache
function M.observe(profile,now,fs)
  if type(profile)~='table' or not M.valid(profile) then return nil end
  local ok,value=pcall(observe,profile,now,fs)
  if ok then return value end
  if refused(value) then return nil end
  error(value,0)  -- a Lua fault, not a router answer
end

------------------------------------------------------------------------------------------------------
-- Observer: the monitor's cached view (see the header for the cost rules)
------------------------------------------------------------------------------------------------------
local Observer={};Observer.__index=Observer
function M.Observer(fs,options)
  options=options or {}
  return setmetatable({fs=fs,memo={},refresh=options.refresh or M.REFRESH,retry=options.retry or M.RETRY,calls=0},Observer)
end
local function copy(value,now)
  if value==nil then return nil end
  local out={};for k,v in pairs(value) do out[k]=v end
  out.time=now
  return out
end
function Observer:observe(profile,now)
  local fs=self.fs
  if not fs or type(profile)~='table' or not M.valid(profile) then return nil end
  if profile.protocol~='wireguard' then return M.observe(profile,now,fs) end
  local ok,text=pcall(read,fs,'/sys/class/net/'..profile.interface..'/ifindex',32)
  if not ok and not refused(text) then error(text,0) end
  local index=ok and text and strip(text) or nil
  if index==nil then self.memo[profile.id]=nil;return nil end
  local clock=fs.clock()
  local memo=self.memo[profile.id]
  if memo and memo.interface==profile.interface and memo.index==index then
    local age=clock-memo.at
    if age>=0 and age<(memo.value and self.refresh or self.retry) then return copy(memo.value,now) end
  end
  self.calls=self.calls+1
  local value=M.observe(profile,now,fs)
  self.memo[profile.id]={interface=profile.interface,index=index,at=clock,value=value and copy(value,now) or nil}
  return value
end
-- forget profiles no longer listed (ids: set of current profile ids)
function Observer:retain(ids) for id in pairs(self.memo) do if not ids[id] then self.memo[id]=nil end end end

return M
