-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- heartbeat_rtt_log.lua: the per-minute RAM log of the heartbeat's echo round trips (CUSUM-TRIGGER-2026-11-04.ru.md,
-- section 5). Later studies need the real RTT noise of the pulse; nothing kept it (status shows only the newest value,
-- the per-target probe log keeps echo counts, not times). Lua only: the Python monitor has no heartbeat.
-- It measures nothing and decides nothing: once a minute the monitor hands over what the pulse measured.
-- Ring of two append-only segments in RAM, like the per-target log: heartbeat-rtt.log and heartbeat-rtt.log.1, at most
-- SEGMENT bytes each. One line per Auto channel per minute (only with at least one round trip), a JSON array:
--   [t, "id", n, min, median, max, n, min, median, max, n, min, median, max]   integers, ms
-- three groups: echoes to 1.1.1.1, to 8.8.8.8, to any other target (heartbeat_quorum); a group without answers is 0,0,0,0.
-- Median: the upper middle of the sorted values. Option heartbeat_rtt_log (inventory.lua), default on.
local M={}
M.OPTION='heartbeat_rtt_log'
M.NAME='heartbeat-rtt.log'
M.SEGMENT=128*1024
M.PERIOD=60
M.SLOTS={'1.1.1.1','8.8.8.8'}

function M.enabled(settings) return type(settings)=='table' and settings[M.OPTION]==true end

local function is_id(v) return type(v)=='string' and #v>=1 and #v<=64 and string.find(v,'^[A-Za-z0-9_.:-]+$')~=nil end

local function group(values)
  if #values==0 then return '0,0,0,0' end
  local sorted={}
  for i,v in ipairs(values) do sorted[i]=v end
  table.sort(sorted)
  return string.format('%d,%d,%d,%d',#sorted,sorted[1],sorted[math.floor(#sorted/2)+1],sorted[#sorted])
end

-- line(stamp, id, targets) -> text | nil; targets: {target -> round trips in ms}
function M.line(stamp,id,targets)
  if not is_id(id) or type(targets)~='table' then return nil end
  local others,any={},false
  for target,values in pairs(targets) do
    if #values>0 then any=true end
    if target~=M.SLOTS[1] and target~=M.SLOTS[2] then
      for _,v in ipairs(values) do others[#others+1]=v end
    end
  end
  if not any then return nil end
  return string.format('[%d,"%s",%s,%s,%s]\n',math.floor(stamp),id,group(targets[M.SLOTS[1]] or {}),group(targets[M.SLOTS[2]] or {}),group(others))
end

local Writer={};Writer.__index=Writer
-- runner: read_file(path), append(path, text), rename(from, to); directory: the RAM runtime directory
function M.Writer(runner,directory,segment)
  return setmetatable({runner=runner,path=directory..'/'..M.NAME,segment=segment or M.SEGMENT,size=nil},Writer)
end

-- record(rows, now) -> lines written; rows: {{id=, targets=}}. Raises when the ring cannot be written.
function Writer:record(rows,now)
  local lines={}
  for _,row in ipairs(rows) do
    local line=M.line(now,row.id,row.targets)
    if line then lines[#lines+1]=line end
  end
  if #lines==0 then return 0 end
  local data=table.concat(lines)
  if self.size==nil then self.size=#(self.runner.read_file(self.path) or '') end
  if self.size+#data>self.segment and self.size>0 then
    self.runner.rename(self.path,self.path..'.1')
    self.size=0
  end
  self.runner.append(self.path,data)
  self.size=self.size+#data
  return #lines
end

return M
