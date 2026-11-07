-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- fast_detect.lua: fast outage detection for the two Auto channels in the Lua monitor (Lua plan item 5).
-- Port of fast_detect.py (branch feat/fast-detection-20261030) onto the monitor's uloop; a heartbeat is never
-- a failure proof and never switches anything.
--
-- Pulse (once per second, from the monitor's existing 1 s loop timer; no child process; since the round trips one
-- read watch per socket, monitor_io.beat_socket):
--   per Auto channel (pair source/target of the last full pass, with its kernel binding device/ifindex/mark/table)
--   * sysfs: ifindex every beat (device gone -> lost 'link-missing'; re-created device -> not counted, the next
--     pass rebinds); only while the channel is not answering also operstate ('down' -> lost 'link-down') and
--     statistics/rx_packets, tx_packets (evidence only: seconds the tunnel received nothing since the first loss);
--   * one ICMP echo through a persistent raw socket bound to the tunnel device (SO_BINDTODEVICE, as probe.lua;
--     nixio has no SO_MARK). The reply is collected without blocking on the NEXT beat, so "no reply within one
--     beat" is a loss. A send the kernel refuses (EPERM of a firewall drop, ENETUNREACH, ENODEV...) is a loss
--     at once. Targets alternate 1.1.1.1 / 8.8.8.8: one anycast hiccup is not LOSSES losses in a row.
-- Turbo (expert opt-in, default off): beats alone may also give Auto's verdict, see Pulse:beat_state; otherwise never.
-- Debounce: LOSSES lost beats in a row of one armed channel make it a suspect. A suspect only starts the dense
--   confirmation episode of probe_policy.Booster:suspect (reason 'heartbeat-lost'): full monitor passes (DNS +
--   3 HTTPS through the channel, route identity before/after, vendor epochs) every DENSE_INTERVAL seconds,
--   published as ordinary samples. Auto decides with its unchanged rules (pair.streak over the owner's
--   'failures'/'successes', diagnosis, reserve proof, attempt budget, dwell); it re-reads status.json every
--   tick (about 2 s), so no separate wake file is needed in the Lua line.
-- After an episode started the channel is disarmed until it answers a beat again (one episode per outage, an
--   ICMP-filtering provider costs at most one false alarm); false alarms back off in Booster (30 s doubling).
-- Owner switch: `option lua_fast_detect` in config main 'main'. Default ON since 2.0.0-alpha24 (owner decision
-- 01.11.2026 after the MT3000 measurement: Auto decision 26-28 s instead of 58-88 s); '0' or any value other
-- than '1' turns it off.
-- Per-target log (probe_target_log.lua): every echo of a beat is counted per target (sent, unanswered), in 8 counters
--   {1.1.1.1 sent, missed, 8.8.8.8 sent, missed, 9.9.9.9 sent, missed, others sent, missed}; the monitor takes and
--   resets them once per pass (Pulse:take_heartbeat). Counting only: no packet, no decision and no time is added.
-- GL sensors (GL-SENSORS-2026-11-04.ru.md), passed by the monitor from the owner's settings (configure's options;
-- without options all three stay off, the rule above exactly):
--   stall (option stall_sensor, default on): rx_bytes/tx_bytes of each channel every beat (two sysfs reads, no fork),
--     minus the beat's own echoes, through stall.lua: tx growing while rx is flat >= 3 s makes a suspect with reason
--     'rx-stall' (dense checks only, the same disarm as the heartbeat).
--   veto (option stall_veto, default on, needs stall): a beat whose echo got no reply while the channel received
--     >= 10 kbit/s for the last 3 s is 'vetoed', not lost: the peer is delivering authenticated data, only the echo
--     target is filtered. Refused sends and a missing link are never vetoed.
--   quorum (option heartbeat_quorum, default OFF): one echo to each of 3 rotating targets per beat (quorum.lua);
--     the beat is lost when 2 of 3 got no reply; LOSSES lost beats in a row as before.
-- CUSUM trigger and RTT (CUSUM-TRIGGER-2026-11-04.ru.md), also passed by the monitor (without options both stay off):
--   cusum (option cusum_trigger): cusum.LossCusum over the raw echo result of every beat, also a vetoed one (traffic
--     flowing does not disprove 30 % loss, and the bound below keeps a false start cheap). A fire is a suspect with
--     reason 'cusum-loss': it does not need the armed/hold state, and Booster:suspect lets it past the suspicion pause at
--     most once per CUSUM_GAP s. Dense checks only; the failure model still decides.
--   rtt (option rtt_watch, default off): cusum.RttWatch over the echo round trips: the soft signal CHANNEL-CONGESTED.
--   Round trips (always measured): monitor_io stamps a reply when it arrives (handle:recv() -> data, arrival time), so
--     status.fast_detect shows rtt_ms and the monitor keeps the per-minute RAM log heartbeat_rtt_log.lua. A reply read
--     without an arrival stamp has no round trip (the arrival is known only to the beat, not to the millisecond).
local probe=require('probe')
local stall=require('stall')
local quorum=require('quorum')
local target_log=require('probe_target_log')
local cusum=require('cusum')

local M={}
M.OPTION='lua_fast_detect'
M.INTERVAL=1           -- seconds between beats (the monitor's 1 s loop timer)
-- lost beats in a row that make a suspect. 2 since 03.11.2026 (was 3): the offline GA/annealing study chose 2 in 8 of
-- 8 re-optimisations (detection ~1 s earlier, same false-switch rate: a suspect only starts the dense DNS/HTTPS
-- confirmation, never a switch). Two in a row still means one lost echo to each of 1.1.1.1 and 8.8.8.8.
M.LOSSES=2
M.TARGETS={'1.1.1.1','8.8.8.8'}
M.REASON='heartbeat-lost'
M.RETRY=5              -- seconds before a suspect the Booster declined (episode running, resting) is offered again
M.DRAIN=32             -- datagrams read per channel per beat at most (the socket only sees ICMP of its device)
M.WATCHING={OBSERVING=true,COMMITTED=true,['DEGRADED-ON-RESERVE']=true}
M.ROLES={'source','target'}
M.SCOPE='ICMP heartbeat and link counters of each Auto channel; it only starts real full checks and never switches by itself'
M.STALL_REASON='rx-stall'
M.ECHO_BYTES=52        -- one echo as the tunnel device counts it: IPv4 20 + ICMP 8 + payload 24 (Pulse:packet)
M.CUSUM_REASON=cusum.REASON
M.RTT_MAX_MS=2000      -- a stamp further than this from its send is no round trip of this echo
M.RTT_KEEP=512         -- round trips kept per target between two take_rtt calls

local function u16(n) return string.char(math.floor(n/256)%256,n%256) end

-- The owner switch, read from the configuration text (uci syntax; the last value wins as in uci); absent = on.
-- No configuration text at all (unreadable file) stays off.
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
  return found==nil or found=='1'
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
    active=false,round=0,sequence=0,salt=salt,pair_ids={},opts={stall=false,veto=false,quorum=false,cusum=false,rtt=false}},Pulse)
end

function Pulse:close_socket(ch)
  if ch.sock then pcall(function() ch.sock:close() end) end
  ch.sock=nil;ch.pending=nil
end

-- configure(on, rows, pair, native_state): after every published pass. A changed kernel binding is a new channel
-- epoch: its counters start again. Off, outside the watching states or without a pair: no packet at all.
-- options: {stall=bool, veto=bool, quorum=bool, cusum=bool, rtt=bool}; absent = all off. A changed quorum switch starts
-- every channel again (its pending echoes have another shape); a detector switched on starts empty.
function Pulse:configure(on,rows,pair,native_state,options)
  options=type(options)=='table' and options or {}
  local opts={stall=options.stall==true,veto=options.stall==true and options.veto==true,quorum=options.quorum==true,
    cusum=options.cusum==true,rtt=options.rtt==true}
  if opts.quorum~=self.opts.quorum then
    for id,ch in pairs(self.channels) do self:close_socket(ch);self.channels[id]=nil end
  end
  for _,ch in pairs(self.channels) do
    if opts.cusum and not self.opts.cusum then ch.cusum:reset() end
    if opts.rtt and not self.opts.rtt then ch.rtt_watch:learn();ch.congested=false end
  end
  self.opts=opts
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
            lost=0,lost_since=nil,armed=true,last='pending',reason=nil,beats=0,replies=0,ok_at=nil,rx=nil,tx=nil,rx_at=nil,hold_until=0,
            stall=stall.Stall(),own_bytes=0,vetoed=0,flowing=false,stalled=nil,suspect_reason=nil,hb={0,0,0,0,0,0,0,0},
            cusum=cusum.LossCusum(),rtt_watch=cusum.RttWatch(),judged=nil,rtt_ms=nil,rtt_target=nil,rtt_at=nil,rtt_last=nil,rtts={},congested=false}
          if opts.quorum then
            local seed=self.runner.random(1)
            ch.pool=quorum.Pool(nil,nil,nil,string.byte(seed,1)%#quorum.POOL)
          end
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
  return '\8\0'..u16(sum)..u16(ch.ident)..u16(sequence)..payload,{identifier=ch.ident,sequence=sequence,payload=payload,target=target,
    sent_at=self.runner.hires and self.runner.hires() or nil}
end

-- one answered echo with a usable arrival stamp: the channel's round trip of this beat (the first one, under the
-- quorum), kept for the status, the RTT watch and the per-minute log
function Pulse:round_trip(ch,echo,arrived,now)
  if type(arrived)~='number' or type(echo.sent_at)~='number' then return end
  local ms=(arrived-echo.sent_at)*1000
  if ms<0 or ms>M.RTT_MAX_MS then return end
  if ch.rtt_ms==nil then ch.rtt_ms=ms;ch.rtt_target=echo.target end
  ch.rtt_at=now;ch.rtt_last=math.floor(ms+0.5)
  local list=ch.rtts[echo.target]
  if not list then list={};ch.rtts[echo.target]=list end
  if #list<M.RTT_KEEP then list[#list+1]=ch.rtt_last end
end

local function count(ch,outcome,reason,now)
  ch.beats=ch.beats+1;ch.last=outcome;ch.reason=reason
  if outcome=='ok' then
    ch.lost=0;ch.lost_since=nil;ch.armed=true;ch.ok_at=now;ch.replies=ch.replies+1
  elseif outcome=='lost' then
    if ch.lost==0 then ch.lost_since=now end
    ch.lost=ch.lost+1
  elseif outcome=='vetoed' then
    -- rx is flowing: evidence of life, the run of lost beats ends (the channel stays as armed as it was)
    ch.lost=0;ch.lost_since=nil;ch.vetoed=ch.vetoed+1
  end
  return outcome
end

-- One beat of one channel. Exactly one outcome per beat: a current refusal/missing link wins over the answer
-- of the previous echo; the very first beat only sends.
function Pulse:beat(ch,target,now)
  local runner=self.runner
  local previous
  local pending=ch.pending
  ch.judged=nil;ch.rtt_ms=nil;ch.rtt_target=nil
  if pending then
    ch.pending=nil
    local answered,left={},#pending
    if ch.sock then
      for _=1,M.DRAIN do
        local data,arrived=ch.sock:recv()
        if not data then break end
        for _,p in ipairs(pending) do
          if not answered[p.target] and probe.valid_reply(data,p.identifier,p.sequence,p.payload,p.target) then
            answered[p.target]=true;left=left-1
            self:round_trip(ch,p,arrived,now)
          end
        end
        if left<=0 then break end
      end
    end
    for _,p in ipairs(pending) do
      local slot=2*target_log.heartbeat_slot(p.target)-1
      ch.hb[slot]=math.min(ch.hb[slot]+1,target_log.MAX_COUNT)
      if not answered[p.target] then ch.hb[slot+1]=math.min(ch.hb[slot+1]+1,target_log.MAX_COUNT) end
    end
    if ch.pool then previous=ch.pool:judge(answered,now)
    else previous=answered[pending[1].target] and 'ok' or 'lost';ch.judged=pending[1].target end
  end
  local index=tonumber(runner.sysfs(ch.device,'ifindex') or '')
  if not index then self:close_socket(ch);ch.stall:reset();ch.flowing=false;ch.stalled=nil;return count(ch,'lost','link-missing',now) end
  if index~=ch.ifindex then self:close_socket(ch);ch.stall:reset();ch.flowing=false;ch.stalled=nil;return count(ch,'unavailable','link-changed',now) end
  if self.opts.stall then
    -- two sysfs reads, the beat's own echoes taken out of tx (they must not look like traffic into a silence)
    local rx=tonumber(runner.sysfs(ch.device,'statistics/rx_bytes') or '')
    local tx=tonumber(runner.sysfs(ch.device,'statistics/tx_bytes') or '')
    local seen=ch.stall:feed(now,rx,tx and tx-ch.own_bytes or nil)
    ch.flowing=seen.state=='flowing'
    ch.stalled=seen.state=='stall' and seen or nil
  end
  if previous=='lost' and self.opts.veto and ch.flowing then previous='vetoed' end
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
  local targets=ch.pool and ch.pool:targets() or {target}
  local sent_now={}
  for _,to in ipairs(targets) do
    local packet,pending_echo=self:packet(ch,to)
    local sent,kind=ch.sock:send(to,packet)
    if not sent then
      -- a firewall refusal leaves the socket usable (kept: no new socket per beat during an outage)
      if kind~='refused' then self:close_socket(ch) end
      if kind=='refused' then return count(ch,'lost','send-refused',now) end
      if kind=='missing' then return count(ch,'lost','link-missing',now) end
      return count(ch,'unavailable','socket',now)
    end
    ch.own_bytes=ch.own_bytes+M.ECHO_BYTES
    sent_now[#sent_now+1]=pending_echo
  end
  ch.pending=sent_now
  if previous then return count(ch,previous,(previous=='lost' and 'timeout') or (previous=='vetoed' and 'rx-flowing') or nil,now) end
  return nil
end

-- The sequential detectors read the outcome of this beat (cusum.lua); returns true when the loss detector fired.
-- Only an echo that went out and was judged counts ('unavailable' and the first beat say nothing about the channel).
-- A timeout belongs to the target of that echo; a refused send or a missing link belongs to no target.
function Pulse:detect(ch,outcome)
  if outcome~='ok' and outcome~='lost' and outcome~='vetoed' then return false end
  local fired=false
  if self.opts.cusum then
    local timeout=ch.reason=='timeout' or ch.reason=='rx-flowing'
    fired=ch.cusum:feed(outcome~='ok',timeout and ch.judged or nil)
  end
  if self.opts.rtt then
    local was=ch.congested
    ch.congested=ch.rtt_watch:feed(ch.rtt_ms,ch.rtt_target)=='congested'
    if ch.congested~=was and self.runner.log then
      self.runner.log('rtt watch: '..ch.id..(ch.congested and ' '..cusum.CODE or ' calm again'))
    end
  end
  return fired
end

-- tick(now): one beat of every channel; returns the armed suspects (source first) or nil. now: monotonic seconds.
function Pulse:tick(now)
  if not self.active then return nil end
  if self.paused() then
    -- a speed test saturates the tunnels: no beats, and the evidence starts again afterwards
    for _,ch in pairs(self.channels) do self:close_socket(ch);ch.lost=0;ch.lost_since=nil;ch.stall:reset();ch.flowing=false;ch.stalled=nil;ch.cusum:reset() end
    return nil
  end
  self.round=self.round+1
  local target=M.TARGETS[(self.round-1)%#M.TARGETS+1]
  local suspects
  for _,id in ipairs(self.order) do
    local ch=self.channels[id]
    local ok,outcome=pcall(self.beat,self,ch,target,now)
    if not ok then self:close_socket(ch);count(ch,'unavailable','error',now);outcome=nil end
    ch.suspect_reason=nil
    if self:detect(ch,outcome) then
      ch.suspect_reason=M.CUSUM_REASON
      suspects=suspects or {};suspects[#suspects+1]=ch
    elseif ch.armed and now>=ch.hold_until then
      if ch.lost>=M.LOSSES then ch.suspect_reason=M.REASON
      elseif ch.stalled then ch.suspect_reason=M.STALL_REASON end
      if ch.suspect_reason then suspects=suspects or {};suspects[#suspects+1]=ch end
    end
  end
  return suspects
end

-- No new episode for this channel before it answered a beat again.
function Pulse:disarm(id) local ch=self.channels[id];if ch then ch.armed=false end end
function Pulse:hold(id,until_) local ch=self.channels[id];if ch then ch.hold_until=until_ end end
function Pulse:pair() return self.pair_ids end

-- take_heartbeat(id) -> the 8 per-target counters since the last call (a fresh table), reset; nil without the channel
function Pulse:take_heartbeat(id)
  local ch=self.channels[id]
  if not ch then return nil end
  local out=ch.hb
  ch.hb={0,0,0,0,0,0,0,0}
  return out
end

-- The expert opt-in (FAST-SWITCH-2026-11-04.ru.md, channel_model.heartbeat_failed): the source's run of lost beats and
-- whether the reserve answered a beat within TARGET_OK s, for the row the monitor leaves in RAM. Only that row, and only
-- with the opt-in, makes a heartbeat count as a verdict; Auto still needs every guard and the late recheck of its tick.
M.TARGET_OK=2
function Pulse:beat_state(now)
  local source,target=self.channels[self.pair_ids.source or ''],self.channels[self.pair_ids.target or '']
  if not source or not target then return nil end
  return {id=source.id,target=target.id,lost=source.lost,since=source.lost_since,target_ok=target.last=='ok' and target.ok_at~=nil and now-target.ok_at<=M.TARGET_OK}
end

-- take_rtt(id) -> {target -> round trips in ms (integers)} since the last call; the monitor's per-minute log. nil
-- without the channel.
function Pulse:take_rtt(id)
  local ch=self.channels[id]
  if not ch then return nil end
  local out=ch.rtts
  ch.rtts={}
  return out
end

-- Evidence for the suspicion row (probe-history.json): integers only.
function Pulse:evidence(ch,now)
  local evidence={losses=ch.lost,cause=ch.reason or 'timeout'}
  if ch.rx_at then evidence.stalled_s=math.floor(math.max(0,now-ch.rx_at)) end
  if ch.tx then evidence.tx_packets=ch.tx end
  if ch.suspect_reason==M.CUSUM_REASON then evidence.cause='cusum' end
  if ch.suspect_reason==M.STALL_REASON and ch.stalled then evidence.stalled_s=ch.stalled.stalled_s;evidence.cause='rx-stall' end
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
      rx_quiet_s=ch.rx_at and math.floor(math.max(0,now-ch.rx_at)) or canon.null,
      vetoed=ch.vetoed,flowing=ch.flowing==true,stalled=ch.stalled~=nil,
      quorum_targets=ch.pool and canon.array(ch.pool:targets()) or canon.null,rotations=ch.pool and ch.pool.rotations or canon.null,
      rtt_ms=ch.rtt_last or canon.null,rtt_age_s=ch.rtt_at and math.floor(math.max(0,now-ch.rtt_at)) or canon.null,
      cusum_centi=math.floor(ch.cusum.s*100+0.5),cusum_fired=ch.cusum.fired,cusum_gated=ch.cusum.gated,
      congested=ch.congested==true,code=ch.congested and cusum.CODE or canon.null,
      rtt_z_centi=self.opts.rtt and math.floor(ch.rtt_watch.z*100+0.5) or canon.null})
  end
  return canon.object({enabled=on==true,active=self.active,interval=M.INTERVAL,losses=M.LOSSES,
    targets=canon.array({M.TARGETS[1],M.TARGETS[2]}),channels=rows,option=M.OPTION,scope=M.SCOPE,
    stall=self.opts.stall,veto=self.opts.veto,quorum=self.opts.quorum,cusum=self.opts.cusum,rtt_watch=self.opts.rtt})
end

return M
