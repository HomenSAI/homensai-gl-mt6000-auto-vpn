-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- mtu_check.lua: the large-packet check of a VPN channel for the Lua monitor; twin of mtu_check.py (same verdicts,
-- shared cases tests/mtu_check_cases.json). Router finding 02.11.2026 (MT3000, primary-mtu): packets longer than
-- 1300 bytes into the primary were dropped, the small HTTPS/DNS probes passed and Auto never left the primary.
--
-- One check: per target (1.1.1.1, 9.9.9.9) one small echo and two large ones of the tunnel device MTU (IP length,
-- at most 1500), each through a raw ICMP socket bound to the tunnel device (runner.datagram; no SO_MARK in nixio,
-- as every Lua probe). ok = a large echo came back (truncated counts) or "fragmentation needed" answered it;
-- black-hole = no large echo came back while a small one did; inconclusive = nothing came back; unavailable =
-- a socket could not be used. Only black-hole fails an otherwise healthy probe, with VPN-MTU.
-- Rate: first probe of a channel, then every INTERVAL s; after a black hole every probe until a check passes.
-- Only the monitor runs it (probe.probe's mtu argument); Auto's live probe (live_probe.lua) does not.
local probe=require('probe')

local M={}
M.CODE='VPN-MTU'
M.TARGETS={'1.1.1.1','9.9.9.9'}
M.INTERVAL=300
M.TIMEOUT=1.5
M.LARGE_COUNT=2
M.SMALL_SIZE=64
M.MIN_SIZE=576
M.MAX_SIZE=1500
M.HEADER=28
M.MAGIC='HV-MTU\0\0'
M.STATES={ok=true,['black-hole']=true,inconclusive=true,unavailable=true}
M.LIMIT=32
M.SEPARATOR='\31'

local u16,be16=probe.u16,probe.be16

function M.parse_mtu(text)
  if type(text)~='string' then return nil end
  text=string.match(text,'^%s*(.-)%s*$')
  if not string.find(text,'^%d+$') or #text>5 then return nil end
  return tonumber(text)
end

function M.probe_size(mtu)
  if type(mtu)~='number' or mtu%1~=0 or mtu<M.MIN_SIZE then return nil end
  return math.min(mtu,M.MAX_SIZE)
end

function M.request(identifier,sequence,payload)
  local sum=probe.icmp_checksum('\8\0'..u16(0)..u16(identifier)..u16(sequence)..payload)
  return '\8\0'..u16(sum)..u16(identifier)..u16(sequence)..payload
end

function M.plan(size,random)
  local probes={}
  for _,target in ipairs(M.TARGETS) do
    local kinds={{'small',M.SMALL_SIZE}}
    for _=1,M.LARGE_COUNT do kinds[#kinds+1]={'large',size} end
    for _,item in ipairs(kinds) do
      local idseq=random(4)
      local identifier,sequence=be16(idseq,1),be16(idseq,3)
      local payload=M.MAGIC..random(item[2]-M.HEADER-#M.MAGIC)
      probes[#probes+1]={target=target,kind=item[1],identifier=identifier,sequence=sequence,payload=payload,
        packet=M.request(identifier,sequence,payload)}
    end
  end
  return probes
end

local function dotted(s,i) local a,b,c,d=string.byte(s,i,i+3);return a..'.'..b..'.'..c..'.'..d end

function M.classify(data,identifier,sequence,payload,target)
  if type(data)~='string' or #data<28 or math.floor(string.byte(data,1)/16)~=4 then return nil end
  local header=(string.byte(data,1)%16)*4
  if header<20 or #data<header+8 or string.byte(data,10)~=1 then return nil end
  local length=be16(data,3)
  if length<header+8 or length>#data or probe.band(be16(data,7),0xbfff)~=0 then return nil end
  local message=string.sub(data,header+1,length)
  if probe.icmp_checksum(message)~=0 then return nil end
  local kind,code=string.byte(message,1),string.byte(message,2)
  if kind==0 and code==0 then
    local body=string.sub(message,9)
    if dotted(data,13)==target and be16(message,5)==identifier and be16(message,7)==sequence
      and #body<=#payload and string.sub(payload,1,#body)==body then return 'echo' end
    return nil
  end
  if kind==3 and code==4 then
    local inner=string.sub(message,9)
    if #inner<28 or math.floor(string.byte(inner,1)/16)~=4 then return nil end
    local inner_header=(string.byte(inner,1)%16)*4
    if inner_header<20 or #inner<inner_header+8 or string.byte(inner,10)~=1 then return nil end
    if dotted(inner,17)~=target then return nil end
    if string.byte(inner,inner_header+1)==8 and be16(inner,inner_header+5)==identifier and be16(inner,inner_header+7)==sequence then
      return 'pmtu'
    end
  end
  return nil
end

function M.group(probes,outcomes)
  local rows={}
  for _,target in ipairs(M.TARGETS) do
    local row={target=target,small=nil,large={}}
    for i,p in ipairs(probes) do
      if p.target==target then
        if p.kind=='small' then row.small=outcomes[i] else row.large[#row.large+1]=outcomes[i] or false end
      end
    end
    rows[#rows+1]=row
  end
  return rows
end

function M.verdict(rows)
  for _,row in ipairs(rows) do
    for _,outcome in ipairs(row.large) do if outcome=='echo' or outcome=='pmtu' then return 'ok' end end
  end
  for _,row in ipairs(rows) do if row.small=='echo' then return 'black-hole' end end
  return 'inconclusive'
end

function M.key(profile_id,binding)
  return tostring(profile_id)..M.SEPARATOR..tostring(binding.device)..M.SEPARATOR..tostring(binding.ifindex)
end

local Schedule={};Schedule.__index=Schedule
function M.Schedule(interval) return setmetatable({interval=interval or M.INTERVAL,state={}},Schedule) end
function Schedule:due(name,now)
  local row=self.state[name]
  return row==nil or row.suspect or not (now-row.time>=0 and now-row.time<self.interval)
end
function Schedule:record(name,state,now)
  local previous=self.state[name]
  local suspect=state=='black-hole' or (state~='ok' and previous~=nil and previous.suspect)
  self.state[name]={time=now,state=state,suspect=suspect}
  while true do
    local count,oldest=0,nil
    for item,row in pairs(self.state) do
      count=count+1
      local o=oldest and self.state[oldest]
      if not oldest or row.time<o.time or (row.time==o.time and item<oldest) then oldest=item end
    end
    if count<=M.LIMIT then break end
    self.state[oldest]=nil
  end
end

-- run(runner, schedule, profile_id, binding, cb): cb(check|nil) exactly once; check={state,size}.
function M.run(runner,schedule,profile_id,binding,cb)
  if schedule==nil or not probe.binding_valid(binding) then cb(nil);return end
  local name=M.key(profile_id,binding)
  local now=runner.clock()
  if not schedule:due(name,now) then cb(nil);return end
  local size=M.probe_size(M.parse_mtu(runner.sysfs(binding.device,'mtu')))
  if not size then cb(nil);return end
  local probes=M.plan(size,runner.random)
  local outcomes,pending,unavailable,done={},#probes,false,false
  local function settle()
    pending=pending-1
    if pending>0 or done then return end
    done=true
    local state=unavailable and 'unavailable' or M.verdict(M.group(probes,outcomes))
    schedule:record(name,state,now)
    cb({state=state,size=size})
  end
  for i,p in ipairs(probes) do
    local ok=pcall(runner.datagram,'icmp',binding.device,p.target,0,p.packet,M.TIMEOUT,function(data)
      return M.classify(data,p.identifier,p.sequence,p.payload,p.target)~=nil
    end,function(data,kind)
      if data then outcomes[i]=M.classify(data,p.identifier,p.sequence,p.payload,p.target)
      elseif kind~='timeout' then unavailable=true end
      settle()
    end)
    if not ok then unavailable=true;settle() end
  end
end

function M.apply(result,check)
  if check==nil then return result end
  result.mtu_check={state=check.state,size=check.size}
  if result.code==nil and check.state=='black-hole' then result.code=M.CODE end
  return result
end

function M.sanitize(value)
  if type(value)~='table' or not M.STATES[value.state] or type(value.size)~='number' or value.size%1~=0
    or value.size<M.MIN_SIZE or value.size>M.MAX_SIZE then return nil end
  return {state=value.state,size=value.size}
end

return M
