-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- wan_diag.lua: WAN down versus tunnel down, a small Bayesian fault diagnosis (GL-SENSORS-2026-11-04.ru.md, item 1).
-- Twin of wan_diag.py (same tables, same order of every multiplication and sum: identical results; shared cases
-- router/tests/gl_sensors_cases.json). Hypotheses N/TUNNEL/SERVER/BOTH/WAN/DNS; evidence underlay/link/kmwan/portal/
-- primary/reserve/wg, each optional ('unknown' or absent = no factor). Safety rules on top of the posterior:
--   hold   = P(WAN) >= HOLD_P AND hard WAN evidence (underlay fail | link down | kmwan offline) AND the primary
--            failing AND the reserve not healthy -> failure_diagnosis returns WAN-DOWN (no switch, no budget used);
--   hasten = WAN proven up (underlay ok | kmwan online) AND the primary failing AND the reserve healthy AND
--            P(WAN) <= HASTEN_WAN_MAX -> the monitor starts the dense confirmation of the primary at once.
-- Without WAN evidence both stay false: the previous behaviour. Pure, no I/O (the monitor does the I/O).
local M={}
M.HYPOTHESES={'N','TUNNEL','SERVER','BOTH','WAN','DNS'}
M.PRIOR={0.968,0.012,0.004,0.004,0.010,0.002}
--                                N      TUNNEL  SERVER  BOTH    WAN     DNS
M.LIKELIHOOD={
  underlay={ok=  {0.98,  0.98,   0.98,   0.97,   0.02,   0.97},
            fail={0.02,  0.02,   0.02,   0.03,   0.98,   0.03}},
  link=    {up=  {0.999, 0.999,  0.999,  0.999,  0.4,    0.999},
            down={0.001, 0.001,  0.001,  0.001,  0.6,    0.001}},
  kmwan=   {online= {0.99, 0.99, 0.99,   0.99,   0.1,    0.99},
            offline={0.01, 0.01, 0.01,   0.01,   0.9,    0.01}},
  portal=  {yes= {0.001, 0.001,  0.001,  0.001,  0.3,    0.001},
            no=  {0.999, 0.999,  0.999,  0.999,  0.7,    0.999}},
  primary= {ok=  {0.97,  0.03,   0.03,   0.03,   0.01,   0.05},
            bad= {0.02,  0.95,   0.9,    0.95,   0.97,   0.1},
            dns= {0.01,  0.02,   0.07,   0.02,   0.02,   0.85}},
  reserve= {ok=  {0.97,  0.95,   0.95,   0.03,   0.01,   0.05},
            bad= {0.02,  0.03,   0.03,   0.95,   0.97,   0.1},
            dns= {0.01,  0.02,   0.02,   0.02,   0.02,   0.85}},
  wg=      {giveup= {0.001, 0.3,  0.01,   0.3,    0.3,    0.001},
            timeout={0.01,  0.4,  0.02,   0.4,    0.4,    0.01},
            created={0.05,  0.01, 0.3,    0.01,   0.01,   0.05}},
}
M.ORDER={'underlay','link','kmwan','portal','primary','reserve','wg'}
M.HOLD_P=0.95
M.HASTEN_WAN_MAX=0.01  -- hasten: the WAN is ruled out (posterior), the reserve answers, the primary just failed
M.CONFIDENT=0.8
M.CODES={TUNNEL='DIAG-TUNNEL-DOWN',SERVER='DIAG-VPN-SERVER',BOTH='DIAG-VPN-BOTH-DOWN',WAN='DIAG-WAN-SUSPECT',DNS='DIAG-DNS-FAILED'}
M.HOLD_CODE='WAN-DOWN'
M.RECOVER_CODE='WAN-RECOVERING'
M.UNSURE_CODE='DIAG-UNSURE'
M.OPTION='wan_sensor'
M.GRACE_OPTION='wan_recover_grace'
M.GRACE_DEFAULT=30
M.GRACE_MAX=120
M.BAD_CODES={['VPN-001']=true,['VPN-003']=true,['VPN-MTU']=true}
M.WG_WINDOW=120

local function str(t,k) if type(t)~='table' then return nil end;local v=t[k];if type(v)=='string' then return v end;return nil end

function M.posterior(evidence)
  local p={}
  for i=1,#M.PRIOR do p[i]=M.PRIOR[i] end
  if type(evidence)~='table' then evidence={} end
  for _,key in ipairs(M.ORDER) do
    local value=str(evidence,key)
    local row=value and M.LIKELIHOOD[key][value] or nil
    if row then
      for i=1,#p do p[i]=p[i]*row[i] end
      local total=0.0
      for i=1,#p do total=total+p[i] end
      for i=1,#p do p[i]=p[i]/total end
    end
  end
  return p
end

function M.permille(value) return math.floor(value*1000+0.5) end

function M.diagnose(evidence,enabled)
  if type(evidence)~='table' then evidence={} end
  if enabled==nil then enabled=true end
  local p=M.posterior(evidence)
  local best=1
  for i=2,#p do if p[i]>p[best] then best=i end end
  local verdict=M.HYPOTHESES[best]
  local function get(key) return str(evidence,key) end
  local wan_proof=get('underlay')=='fail' or get('link')=='down' or get('kmwan')=='offline'
  local up_proof=get('underlay')=='ok' or get('kmwan')=='online'
  local hold=enabled==true and p[5]>=M.HOLD_P and wan_proof and get('primary')=='bad' and get('reserve')~='ok'
  local hasten=enabled==true and not hold and up_proof and get('primary')=='bad' and get('reserve')=='ok' and p[5]<=M.HASTEN_WAN_MAX
  local code
  if hold then code=M.HOLD_CODE
  elseif p[best]<M.CONFIDENT then code=M.UNSURE_CODE
  else code=M.CODES[verdict] end
  local post={}
  for i,name in ipairs(M.HYPOTHESES) do post[name]=M.permille(p[i]) end
  return {verdict=verdict,confidence=M.permille(p[best]),hold=hold and true or false,hasten=hasten and true or false,
    code=code,posterior=post,wan_proof=wan_proof and true or false,up_proof=up_proof and true or false}
end

local function finite(v) return type(v)=='number' and v==v and v~=math.huge and v~=-math.huge end
-- a canon.float box ({value=x}) from a decoded status.json reads as its number
local function plain(v) if type(v)=='table' and type(v.value)=='number' then return v.value end;return v end
M.plain=plain

-- 'ok' | 'bad' | 'dns' | 'unknown' from one published probe row. null: canon.null or nil.
function M.channel_state(row,now,age,null)
  if type(row)~='table' or row==null then return 'unknown' end
  local stamp=plain(row.time)
  if not finite(stamp) or not (now-stamp>=0 and now-stamp<=age) then return 'unknown' end
  local code=row.code;if code==null then code=nil end
  if type(code)=='string' and M.BAD_CODES[code] then return 'bad' end
  if code=='DNS-001' then return 'dns' end
  local successes=plain(row.https_success)
  if code==nil and row.dns_ok==true and type(successes)=='number' and successes%1==0 and successes>=2 then return 'ok' end
  return 'unknown'
end

-- evidence(rows, pair, now, age, sensors): sensors = {uplink=, underlay=, kmwan=, portal=, wg=, null=}
function M.evidence(rows,pair,now,age,sensors)
  sensors=sensors or {}
  local null=sensors.null
  local by_id={}
  for _,row in ipairs(type(rows)=='table' and rows or {}) do
    if type(row)=='table' and type(row.id)=='string' then by_id[row.id]=row end
  end
  if type(pair)~='table' then pair={} end
  local found={primary=M.channel_state(by_id[str(pair,'source') or false],now,age,null),
    reserve=M.channel_state(by_id[str(pair,'target') or false],now,age,null)}
  local uplink=sensors.uplink
  if type(uplink)=='table' and uplink~=null then
    local stamp=plain(uplink.time)
    if finite(stamp) and now-stamp>=0 and now-stamp<=age then
      local state=uplink.state
      found.link=(state=='DOWN' and 'down') or (state=='LINK-UP' and 'up') or 'unknown'
    end
  end
  local allowed={underlay={ok=true,fail=true},kmwan={online=true,offline=true},portal={yes=true,no=true},
    wg={giveup=true,timeout=true,created=true}}
  for _,key in ipairs({'underlay','kmwan','portal','wg'}) do
    local value=sensors[key]
    if type(value)=='string' and allowed[key][value] then found[key]=value end
  end
  return found
end

function M.kmwan_verdict(text)
  if type(text)~='string' or text=='' then return nil end
  local lowered=string.lower(text)
  if string.find(lowered,'online',1,true) then return 'online' end
  if string.find(lowered,'offline',1,true) then return 'offline' end
  return nil
end

function M.portal_verdict(value)
  if type(value)~='table' then return nil end
  if value.portal==true then return 'yes' end
  if value.portal==false then return 'no' end
  return nil
end

function M.grace_seconds(settings)
  local value=type(settings)=='table' and settings[M.GRACE_OPTION] or nil
  if type(value)=='number' and value%1==0 and value>=0 and value<=M.GRACE_MAX then return value end
  return M.GRACE_DEFAULT
end

function M.enabled(settings) return not (type(settings)=='table' and settings[M.OPTION]==false) end

------------------------------------------------------------------------------------------------------
-- Underlay: own ICMP echo through the WAN device (see wan_diag.py Underlay)
------------------------------------------------------------------------------------------------------
local Underlay={};Underlay.__index=Underlay
M.UNDERLAY={TARGETS={'1.1.1.1','8.8.8.8','9.9.9.9','208.67.222.222'},FAIL_N=3,OK_AGE=30,STALE=60,IDLE=10,ALERT=2}
function M.Underlay()
  local self=setmetatable({device=nil},Underlay);self:reset();return self
end
function Underlay:reset() self.calibrated=false;self.fails=0;self.fail_targets={};self.last_ok=nil;self.last_at=nil;self.sent=0 end
function Underlay:bind(device) if device~=self.device then self.device=device;self:reset() end end
function Underlay:target() local t=M.UNDERLAY.TARGETS;return t[self.sent%#t+1] end
function Underlay:due(now,alert)
  if self.device==nil then return false end
  return self.last_at==nil or now-self.last_at>=(alert and M.UNDERLAY.ALERT or M.UNDERLAY.IDLE)
end
function Underlay:record(ok,target,now)
  self.last_at=now;self.sent=self.sent+1
  if ok then self.calibrated=true;self.fails=0;self.fail_targets={};self.last_ok=now
  else
    self.fails=self.fails+1
    local seen=false
    for _,t in ipairs(self.fail_targets) do if t==target then seen=true end end
    if not seen then self.fail_targets[#self.fail_targets+1]=target end
  end
end
function Underlay:state(now)
  local U=M.UNDERLAY
  if self.device==nil or self.last_at==nil or now-self.last_at>U.STALE or now<self.last_at then return nil end
  if self.calibrated and self.fails>=U.FAIL_N and #self.fail_targets>=2 then return 'fail' end
  if self.fails==0 and self.last_ok~=nil and now-self.last_ok>=0 and now-self.last_ok<=U.OK_AGE then return 'ok' end
  return nil
end
function Underlay:public(now)
  return {device=self.device,state=self:state(now) or 'unknown',calibrated=self.calibrated,fails=self.fails,
    age_s=self.last_at and math.floor(math.max(0,now-self.last_at)) or nil}
end

------------------------------------------------------------------------------------------------------
-- Tracker: hold while the WAN is down, WAN-RECOVERING after it came back (see wan_diag.py Tracker)
------------------------------------------------------------------------------------------------------
local Tracker={};Tracker.__index=Tracker
function M.Tracker() return setmetatable({down_since=nil,up_at=nil},Tracker) end
function Tracker:update(diagnosis,now,primary_ok_at,grace)
  local restored=false
  if diagnosis.hold then
    if self.down_since==nil then self.down_since=now end
    self.up_at=nil
    return {hold=true,recovering=false,restored=false,code=M.HOLD_CODE,down_since=self.down_since,up_at=nil}
  end
  if self.down_since~=nil then self.down_since=nil;self.up_at=now;restored=true end
  local recovering=false
  if self.up_at~=nil then
    local healthy_after=type(primary_ok_at)=='number' and primary_ok_at>self.up_at
    if grace>0 and now-self.up_at>=0 and now-self.up_at<grace and not healthy_after then recovering=true
    else self.up_at=nil end
  end
  return {hold=recovering,recovering=recovering,restored=restored,code=recovering and M.RECOVER_CODE or diagnosis.code,
    down_since=nil,up_at=self.up_at}
end

return M
