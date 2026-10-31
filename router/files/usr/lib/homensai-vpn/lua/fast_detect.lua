-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- fast_detect.lua: fast outage detection for the two Auto channels in the Lua monitor (Lua plan item 5).
-- Port of fast_detect.py (branch feat/fast-detection-20261030) onto the monitor's uloop; a heartbeat is never
-- a failure proof and never switches anything.
--
-- Pulse (once per second, from the monitor's existing 1 s loop timer; no extra uloop object, no child process):
--   per Auto channel (pair source/target of the last full pass, with its kernel binding device/ifindex/mark/table)
--   * sysfs: ifindex every beat (device gone -> lost 'link-missing'; re-created device -> not counted, the next
--     pass rebinds); only while the channel is not answering also operstate ('down' -> lost 'link-down') and
--     statistics/rx_packets, tx_packets (evidence only: seconds the tunnel received nothing since the first loss);
--   * one ICMP echo through a persistent raw socket bound to the tunnel device (SO_BINDTODEVICE, as probe.lua;
--     nixio has no SO_MARK). The reply is collected without blocking on the NEXT beat, so "no reply within one
--     beat" is a loss. A send the kernel refuses (EPERM of a firewall drop, ENETUNREACH, ENODEV...) is a loss
--     at once. Targets alternate 1.1.1.1 / 8.8.8.8: one anycast hiccup is not LOSSES losses in a row.
-- Debounce: LOSSES lost beats in a row of one armed channel make it a suspect. A suspect only starts the dense
--   confirmation episode of probe_policy.Booster:suspect (reason 'heartbeat-lost'): full monitor passes (DNS +
--   3 HTTPS through the channel, route identity before/after, vendor epochs) every DENSE_INTERVAL seconds,
--   published as ordinary samples. Auto decides with its unchanged rules (pair.streak over the owner's
--   'failures'/'successes', diagnosis, reserve proof, attempt budget, dwell); it re-reads status.json every
--   tick (about 2 s), so no separate wake file is needed in the Lua line.
-- After an episode started the channel is disarmed until it answers a beat again (one episode per outage, an
--   ICMP-filtering provider costs at most one false alarm); false alarms back off in Booster (30 s doubling).
-- Owner switch: `option lua_fast_detect '1'` in config main 'main' (default OFF; any other value is off).
local probe=require('probe')

local M={}
M.OPTION='lua_fast_detect'
M.INTERVAL=1           -- seconds between beats (the monitor's 1 s loop timer)
M.LOSSES=3             -- lost beats in a row that make a suspect
M.TARGETS={'1.1.1.1','8.8.8.8'}
M.REASON='heartbeat-lost'
M.RETRY=5              -- seconds before a suspect the Booster declined (episode running, resting) is offered again
M.DRAIN=32             -- datagrams read per channel per beat at most (the socket only sees ICMP of its device)
M.WATCHING={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true}
M.ROLES={'source','target'}
M.SCOPE='ICMP heartbeat and link counters of each Auto channel; it only starts real full checks and never switches by itself'

local function u16(n) return string.char(math.floor(n/256)%256,n%256) end

-- The owner switch, read from the configuration text (uci syntax; the last value wins as in uci).
function M.option_enabled(text)
  if type(text)~='string' then return false end
  local section,found=nil,nil
  for line in string.gmatch(text,'[^\n]+') do
    if string.find(line,'^%s*config%s') then
      section=string.match(line,'^%s*config%s+%S+%s+["\']?([A-Za-z0-9_]+)["\']?%s*$')
    elseif section=='main' then
      local value=string.match(line,'^%s*option%s+'..M.OPTION..'%s+["\']?([^"\'%s]*)["\']?%s*$')
      if value then found=value end
    end
  end
  return found=='1'
end

-- The two Auto channels of a published pass with a complete kernel binding: {id -> channel}.
function M.channels(rows,pair)
  local found={}
  if type(pair)~='table' or type(rows)~='table' then return found end
  for _,role in ipairs(M.ROLES) do
    local identifier=pair[role]
    if type(identifier)=='string' then
      for _,row in ipairs(rows) do
        if type(row)=='table' and row.id==identifier then
          local binding={device=row.device,mark=row.mark,table=row.table,ifindex=row.ifindex}
          if probe.binding_valid(binding) then
            found[identifier]={id=identifier,role=role,device=row.device,mark=row.mark,table=row.table,ifindex=row.ifindex}
          end
          break
        end
      end
    end
  end
  return found
end

local Pulse={};Pulse.__index=Pulse

-- runner: monitor_io.lua (beat_socket, sysfs, random, clock) or a test fake; paused() -> true while a speed test runs.
function M.Pulse(runner,paused)
  local salt=runner.random(8)
  return setmetatable({runner=runner,paused=paused or function() return false end,channels={},order={},
    active=false,round=0,sequence=0,salt=salt,pair_ids={}},Pulse)
end

function Pulse:close_socket(ch)
  if ch.sock then pcall(function() ch.sock:close() end) end
  ch.sock=nil;ch.pending=nil
end

-- configure(on, rows, pair, native_state): after every published pass. A changed kernel binding is a new channel
-- epoch: its counters start again. Off, outside the watching states or without a pair: no packet at all.
function Pulse:configure(on,rows,pair,native_state)
  local wanted={}
  if on and M.WATCHING[native_state] and type(pair)=='table' and type(pair.source)=='string' and type(pair.target)=='string'
     and pair.source~=pair.target then wanted=M.channels(rows,pair) end
  for id,ch in pairs(self.channels) do
    local w=wanted[id]
    if not w or w.device~=ch.device or w.ifindex~=ch.ifindex or w.mark~=ch.mark or w.table~=ch.table then
      self:close_socket(ch);self.channels[id]=nil
    end
  end
  local order={}
  for _,role in ipairs(M.ROLES) do
    for id,w in pairs(wanted) do
      if w.role==role then
        local ch=self.channels[id]
        if ch then ch.role=role
        else
          local ident=self.runner.random(2)
          ch={id=id,role=role,device=w.device,ifindex=w.ifindex,mark=w.mark,table=w.table,ident=string.byte(ident,1)*256+string.byte(ident,2),
            lost=0,lost_since=nil,armed=true,last='pending',reason=nil,beats=0,replies=0,ok_at=nil,rx=nil,tx=nil,rx_at=nil,hold_until=0}
          self.channels[id]=ch
        end
        order[#order+1]=id
      end
    end
  end
  self.order=order
  self.pair_ids=(#order>0) and {source=pair.source,target=pair.target} or {}
  self.active=#order>0
end

function Pulse:close()
  for _,ch in pairs(self.channels) do self:close_socket(ch) end
  self.channels={};self.order={};self.active=false;self.pair_ids={}
end

function Pulse:packet(ch,target)
  self.sequence=(self.sequence+1)%65536
  local sequence=self.sequence
  local payload='HV-BEAT\0'..self.salt..u16(sequence)..'\0\0\0\0\0\0'
  local sum=probe.icmp_checksum('\8\0\0\0'..u16(ch.ident)..u16(sequence)..payload)
  return '\8\0'..u16(sum)..u16(ch.ident)..u16(sequence)..payload,{identifier=ch.ident,sequence=sequence,payload=payload,target=target}
end

local function count(ch,outcome,reason,now)
  ch.beats=ch.beats+1;ch.last=outcome;ch.reason=reason
  if outcome=='ok' then
    ch.lost=0;ch.lost_since=nil;ch.armed=true;ch.ok_at=now;ch.replies=ch.replies+1
  elseif outcome=='lost' then
    if ch.lost==0 then ch.lost_since=now end
    ch.lost=ch.lost+1
  end
  return outcome
end

-- One beat of one channel. Exactly one outcome per beat: a current refusal/missing link wins over the answer
-- of the previous echo; the very first beat only sends.
function Pulse:beat(ch,target,now)
  local runner=self.runner
  local previous
  local p=ch.pending
  if p then
    ch.pending=nil;previous='lost'
    if ch.sock then
      for _=1,M.DRAIN do
        local data=ch.sock:recv()
        if not data then break end
        if probe.valid_reply(data,p.identifier,p.sequence,p.payload,p.target) then previous='ok';break end
      end
    end
  end
  local index=tonumber(runner.sysfs(ch.device,'ifindex') or '')
  if not index then self:close_socket(ch);return count(ch,'lost','link-missing',now) end
  if index~=ch.ifindex then self:close_socket(ch);return count(ch,'unavailable','link-changed',now) end
  if previous~='ok' or ch.last~='ok' then
    -- Not answering (or not yet proven): link state and counters as evidence. A healthy beat skips these three
    -- sysfs reads (each read is most of a beat's cost); a down link would refuse the send anyway (ENETDOWN).
    if runner.sysfs(ch.device,'operstate')=='down' then self:close_socket(ch);return count(ch,'lost','link-down',now) end
    local rx=tonumber(runner.sysfs(ch.device,'statistics/rx_packets') or '')
    if rx~=ch.rx then ch.rx=rx;ch.rx_at=now end
    ch.tx=tonumber(runner.sysfs(ch.device,'statistics/tx_packets') or '')
  else
    ch.rx=nil;ch.rx_at=nil;ch.tx=nil
  end
  if not ch.sock then
    local sock,kind=runner.beat_socket(ch.device)
    if not sock then
      if kind=='missing' then return count(ch,'lost','link-missing',now) end
      return count(ch,'unavailable','socket',now)
    end
    ch.sock=sock
  end
  local packet,pending=self:packet(ch,target)
  local sent,kind=ch.sock:send(target,packet)
  if not sent then
    -- a firewall refusal leaves the socket usable (kept: no new socket per beat during an outage)
    if kind~='refused' then self:close_socket(ch) end
    if kind=='refused' then return count(ch,'lost','send-refused',now) end
    if kind=='missing' then return count(ch,'lost','link-missing',now) end
    return count(ch,'unavailable','socket',now)
  end
  ch.pending=pending
  if previous then return count(ch,previous,previous=='lost' and 'timeout' or nil,now) end
  return nil
end

-- tick(now): one beat of every channel; returns the armed suspects (source first) or nil. now: monotonic seconds.
function Pulse:tick(now)
  if not self.active then return nil end
  if self.paused() then
    -- a speed test saturates the tunnels: no beats, and the evidence starts again afterwards
    for _,ch in pairs(self.channels) do self:close_socket(ch);ch.lost=0;ch.lost_since=nil end
    return nil
  end
  self.round=self.round+1
  local target=M.TARGETS[(self.round-1)%#M.TARGETS+1]
  local suspects
  for _,id in ipairs(self.order) do
    local ch=self.channels[id]
    local ok=pcall(self.beat,self,ch,target,now)
    if not ok then self:close_socket(ch);count(ch,'unavailable','error',now) end
    if ch.armed and ch.lost>=M.LOSSES and now>=ch.hold_until then
      suspects=suspects or {};suspects[#suspects+1]=ch
    end
  end
  return suspects
end

-- No new episode for this channel before it answered a beat again.
function Pulse:disarm(id) local ch=self.channels[id];if ch then ch.armed=false end end
function Pulse:hold(id,until_) local ch=self.channels[id];if ch then ch.hold_until=until_ end end
function Pulse:pair() return self.pair_ids end

-- Evidence for the suspicion row (probe-history.json): integers only.
function Pulse:evidence(ch,now)
  local evidence={losses=ch.lost,cause=ch.reason or 'timeout'}
  if ch.rx_at then evidence.stalled_s=math.floor(math.max(0,now-ch.rx_at)) end
  if ch.tx then evidence.tx_packets=ch.tx end
  return evidence
end

-- status.fast_detect (integers and strings only: no float formatting per pass)
function Pulse:public(now,on)
  local canon=require('canon')
  local rows=canon.array()
  for _,id in ipairs(self.order) do
    local ch=self.channels[id]
    rows[#rows+1]=canon.object({profile=id,role=ch.role,device=ch.device,state=ch.last,reason=ch.reason or canon.null,
      lost=ch.lost,armed=ch.armed,beats=ch.beats,replies=ch.replies,
      lost_for_s=ch.lost_since and math.floor(math.max(0,now-ch.lost_since)) or canon.null,
      ok_age_s=ch.ok_at and math.floor(math.max(0,now-ch.ok_at)) or canon.null,
      rx_quiet_s=ch.rx_at and math.floor(math.max(0,now-ch.rx_at)) or canon.null})
  end
  return canon.object({enabled=on==true,active=self.active,interval=M.INTERVAL,losses=M.LOSSES,
    targets=canon.array({M.TARGETS[1],M.TARGETS[2]}),channels=rows,option=M.OPTION,scope=M.SCOPE})
end

return M
