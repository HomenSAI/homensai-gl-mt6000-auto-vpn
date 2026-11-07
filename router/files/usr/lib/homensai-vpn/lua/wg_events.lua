-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- wg_events.lua: WireGuard kernel events as a fast sensor (GL-SENSORS-2026-11-04.ru.md, item 2). Twin of wg_events.py
-- (shared cases router/tests/gl_sensors_cases.json). /etc/hotplug.d/wireguard/60-homensai appends
-- '<uptime> <ACTION> <ifname>' to RUNTIME/wg-events.log while RUNTIME/wg-events.on exists (option wg_events on);
-- REKEY-TIMEOUT/REKEY-GIVEUP of a pair device -> Booster:suspect reason 'wg-rekey' (dense checks only);
-- KEYPAIR-CREATED -> evidence 'created' for wan_diag.
local M={}
M.FILE='wg-events.log'
M.FLAG='wg-events.on'
M.ACTIONS={['REKEY-TIMEOUT']='timeout',['REKEY-GIVEUP']='giveup',['KEYPAIR-CREATED']='created'}
M.WINDOW=120
M.REASON='wg-rekey'
M.OPTION='wg_events'
M.MAX_LINES=200

local function valid_device(s) return #s>=1 and #s<=15 and string.find(s,'^[A-Za-z0-9_.-]+$')~=nil end
local function valid_stamp(s)
  local whole,frac=string.match(s,'^(%d+)%.?(%d*)$')
  if not whole or #whole>9 or #frac>3 then return nil end
  if string.find(s,'%.$') then return nil end
  return tonumber(s)
end

function M.parse(text)
  local lines={}
  if type(text)~='string' then return {} end
  for line in string.gmatch(text..'\n','([^\n]*)\n') do lines[#lines+1]=line end
  local found={}
  for i=math.max(1,#lines-M.MAX_LINES),#lines do
    local line=string.gsub(lines[i],'\r$','')
    local stamp,action,device=string.match(line,'^(%S+) (%S+) (%S+)$')
    local t=stamp and valid_stamp(stamp)
    if t and M.ACTIONS[action] and valid_device(device) then found[#found+1]={t,M.ACTIONS[action],device} end
  end
  return found
end

function M.latest(events,device,now,window)
  window=window or M.WINDOW
  local best=nil
  for _,e in ipairs(events) do
    if e[3]==device and now-e[1]>=0 and now-e[1]<=window and (best==nil or e[1]>=best[1]) then best={e[1],e[2]} end
  end
  return best and best[2] or nil
end

local Reader={};Reader.__index=Reader
function M.Reader() return setmetatable({seen=nil},Reader) end
function Reader:new(events)
  local newest=nil
  for _,e in ipairs(events) do if newest==nil or e[1]>newest then newest=e[1] end end
  if self.seen==nil then self.seen=newest or 0.0;return {} end
  local fresh={}
  local top=nil
  for _,e in ipairs(events) do if e[1]>self.seen then fresh[#fresh+1]=e;if top==nil or e[1]>top then top=e[1] end end end
  if top then self.seen=top
  elseif newest~=nil and newest<self.seen then self.seen=newest end
  return fresh
end

function M.suspicions(fresh,channels)
  local items={}
  for _,e in ipairs(fresh) do
    if e[2]=='timeout' or e[2]=='giveup' then
      for _,ch in ipairs(channels) do
        if type(ch)=='table' and ch.device==e[3] and type(ch.id)=='string' then
          items[#items+1]={profile=ch.id,reason=M.REASON,evidence={event=e[2]}}
        end
      end
    end
  end
  return items
end

function M.enabled(settings) return not (type(settings)=='table' and settings[M.OPTION]==false) end

return M
