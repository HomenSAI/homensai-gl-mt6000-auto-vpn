-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- cusum.lua: twin of cusum.py (same rules and constants; shared cases router/tests/cusum_cases.json), fed once per second
-- by fast_detect.lua. Neither detector ever decides a switch; the rules are described in cusum.py and in
-- docs/architecture/CUSUM-TRIGGER-2026-11-04.ru.md.
--   LossCusum: Bernoulli CUSUM over lost heartbeat echoes; a fire only asks for a dense confirmation episode
--     (probe_policy Booster:suspect, reason 'cusum-loss').
--   RttWatch: Kalman filter on log RTT; raises the soft 'congested' signal (status field, code CHANNEL-CONGESTED).
local M={}
M.P0=0.01;M.P1=0.5;M.H=8;M.CAP=2;M.GATE=8
M.LOST_STEP=math.log(M.P1/M.P0)
M.KEPT_STEP=math.log((1-M.P1)/(1-M.P0))
M.OPTION='cusum_trigger'
M.REASON='cusum-loss'

local LossCusum={};LossCusum.__index=LossCusum
function M.LossCusum() local self=setmetatable({fired=0,gated=0},LossCusum);self:reset();return self end
function LossCusum:reset() self.s=0;self.run=0;self.beat=0;self.seen={} end
-- feed(lost, target) -> true when the detector fires; target nil: the beat is not attributed to a target
function LossCusum:feed(lost,target)
  self.beat=self.beat+1
  local step
  if lost then
    self.run=self.run+1
    if target~=nil then self.seen[target]=self.beat end
    step=self.run<=M.CAP and M.LOST_STEP or 0
  else
    self.run=0;step=M.KEPT_STEP
  end
  self.s=math.max(0,self.s+step)
  if self.s<M.H then return false end
  self.s=0
  if target~=nil then
    local recent=0
    for _,at in pairs(self.seen) do if self.beat-at<M.GATE then recent=recent+1 end end
    if recent<2 then self.gated=self.gated+1;return false end
  end
  self.fired=self.fired+1
  return true
end

M.RTT_OPTION='rtt_watch'
M.CODE='CHANNEL-CONGESTED'
M.WARM=120;M.TARGET_MIN=5;M.SIG_MIN=0.05
M.Z_ON=4;M.Z_OFF=2;M.CLEAR=30;M.TRACK=1800;M.MAX_HOLD=1800
M.Q_L=2e-5;M.Q_S=1e-9;M.P_START=0.05;M.INNOVATION_GATE=3;M.LEVEL_SOFT=0.05*0.05

local RttWatch={};RttWatch.__index=RttWatch
function M.RttWatch() local self=setmetatable({raised=0,relearned=0},RttWatch);self:learn();return self end
function RttWatch:learn()
  self.samples={};self.base=nil;self.congested=false;self.calm=0;self.held=0;self.z=0;self.drift=0
end
local function key(target) if target==nil then return '' end;return target end
function RttWatch:start()
  local by_target={}
  for _,sample in ipairs(self.samples) do
    local list=by_target[sample[1]]
    if not list then list={};by_target[sample[1]]=list end
    list[#list+1]=sample[2]
  end
  local base,residuals,any={},{},false
  for target,values in pairs(by_target) do
    if #values>=M.TARGET_MIN then
      table.sort(values)
      local middle=values[math.floor(#values/2)+1]
      base[target]=middle;any=true
      for _,y in ipairs(values) do residuals[#residuals+1]=math.abs(y-middle) end
    end
  end
  self.samples={}
  if not any then return end
  table.sort(residuals)
  local sigma=math.max(residuals[math.floor(#residuals/2)+1]*1.4826,M.SIG_MIN)
  self.base=base;self.R=sigma*sigma
  self.x0=0;self.x1=0;self.P00=M.P_START;self.P01=0;self.P11=1e-6
end
function RttWatch:predict()
  self.x0=self.x0+self.x1
  local P00=self.P00+2*self.P01+self.P11+M.Q_L
  self.P01=self.P01+self.P11;self.P11=self.P11+M.Q_S;self.P00=P00
end
function RttWatch:update(y)
  local innovation=self.P00+self.R
  local e=y-self.x0
  local limit=M.INNOVATION_GATE*math.sqrt(innovation)
  if e>limit then e=limit elseif e<-limit then e=-limit end
  local K0,K1=self.P00/innovation,self.P01/innovation
  self.x0=self.x0+K0*e;self.x1=self.x1+K1*e
  local P00,P01=(1-K0)*self.P00,(1-K0)*self.P01
  self.P11=self.P11-K1*self.P01
  self.P00=P00;self.P01=P01
end
-- feed(rtt_ms, target) -> 'learning' | 'ok' | 'congested'; rtt_ms nil: no answer this beat
function RttWatch:feed(rtt_ms,target)
  local answered=type(rtt_ms)=='number' and rtt_ms>0 and rtt_ms~=math.huge
  target=key(target)
  if self.base==nil then
    if answered then
      self.samples[#self.samples+1]={target,math.log(rtt_ms)}
      if #self.samples>=M.WARM then self:start() end
    end
    return 'learning'
  end
  self:predict()
  if answered and self.base[target]~=nil then
    self:update(math.log(rtt_ms)-self.base[target])
    self.z=(self.x0-self.drift)/math.sqrt(self.P00+M.LEVEL_SOFT)
    if self.congested then
      self.held=self.held+1
      self.calm=self.z<M.Z_OFF and self.calm+1 or 0
      if self.calm>=M.CLEAR then self.congested=false;self.calm=0;self.held=0
      elseif self.held>=M.MAX_HOLD then
        self.relearned=self.relearned+1
        self:learn()
        return 'learning'
      end
    elseif self.z>=M.Z_ON then
      self.congested=true;self.calm=0;self.held=0;self.raised=self.raised+1
    elseif math.abs(self.z)<M.Z_OFF then
      self.drift=self.drift+(self.x0-self.drift)/M.TRACK
    end
  end
  return self.congested and 'congested' or 'ok'
end

-- both off unless the owner switched them on (inventory.lua; the design note says why)
function M.enabled(settings) return type(settings)=='table' and settings[M.OPTION]==true end
function M.rtt_enabled(settings) return type(settings)=='table' and settings[M.RTT_OPTION]==true end

return M
