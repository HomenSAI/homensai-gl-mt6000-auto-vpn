-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- stall.lua: passive stall sensor of one tunnel device (GL-SENSORS-2026-11-04.ru.md, item 3). Twin of stall.py
-- (same rules and constants; shared cases router/tests/gl_sensors_cases.json). Fed once per second by fast_detect.lua
-- with two sysfs counters (rx_bytes, tx_bytes minus the heartbeat's own echoes):
--   'stall'   tx grew >= MIN_TX_BYTES since rx last moved while rx is flat for STALL_SECONDS: a suspicion only
--             (Booster:suspect reason 'rx-stall'), never a switch;
--   'flowing' rx moved since the previous sample and grew >= VETO_BYTES over VETO_SECONDS (10 kbit/s): a lost heartbeat
--             echo is vetoed (option stall_veto); the veto ends the second rx stops (no delay on a real outage);
--   'idle'    anything else (first sample, counter reset, gap).
local M={}
M.STALL_SECONDS=3
M.VETO_SECONDS=3
M.VETO_BYTES=3750
M.MIN_TX_BYTES=300
M.GAP=5
M.HISTORY=6
M.OPTION='stall_sensor'
M.VETO_OPTION='stall_veto'

local function count(v) return type(v)=='number' and v>=0 and v%1==0 end
local function idle() return {state='idle',stalled_s=0,tx_bytes=0} end

local Stall={};Stall.__index=Stall
function M.Stall() local self=setmetatable({},Stall);self:reset();return self end
function Stall:reset() self.last=nil;self.rx_at=nil;self.base_tx=nil;self.history={} end

function Stall:feed(now,rx_bytes,tx_bytes)
  if not (count(rx_bytes) and count(tx_bytes)) then self:reset();return idle() end
  local last=self.last
  if last==nil or now-last[1]>M.GAP or now<last[1] or rx_bytes<last[2] or tx_bytes<last[3] then
    self.last={now,rx_bytes,tx_bytes};self.rx_at=now;self.base_tx=tx_bytes;self.history={{now,rx_bytes}}
    return idle()
  end
  if rx_bytes~=last[2] then self.rx_at=now;self.base_tx=tx_bytes end
  self.last={now,rx_bytes,tx_bytes}
  local h=self.history
  h[#h+1]={now,rx_bytes}
  if #h>M.HISTORY then
    local kept={}
    for i=#h-M.HISTORY+1,#h do kept[#kept+1]=h[i] end
    self.history=kept;h=kept
  end
  local oldest=nil
  for _,s in ipairs(h) do if now-s[1]>=M.VETO_SECONDS then oldest=s end end
  if oldest~=nil and self.rx_at==now and rx_bytes-oldest[2]>=M.VETO_BYTES then return {state='flowing',stalled_s=0,tx_bytes=0} end
  local stalled=now-self.rx_at
  local sent=tx_bytes-self.base_tx
  if stalled>=M.STALL_SECONDS and sent>=M.MIN_TX_BYTES then
    return {state='stall',stalled_s=math.floor(stalled),tx_bytes=sent}
  end
  return idle()
end

function M.enabled(settings,option) return not (type(settings)=='table' and settings[option or M.OPTION]==false) end

return M
