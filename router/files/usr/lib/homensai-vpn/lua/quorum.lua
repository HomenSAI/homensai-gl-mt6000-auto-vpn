-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- quorum.lua: k-of-n heartbeat targets with rotation (GL-SENSORS-2026-11-04.ru.md, item 4). Twin of quorum.py (same
-- pool, same rotation; shared cases router/tests/gl_sensors_cases.json). Option heartbeat_quorum '1' (default off):
-- one echo per active target per beat; the beat is lost when >= K of the N active targets did not reply; a target
-- that misses MISS_LIMIT times in WINDOW s while the beat was answered is replaced by the next pool target; a lost
-- beat never rotates.
local M={}
M.POOL={'1.1.1.1','8.8.8.8','9.9.9.9','208.67.222.222','1.0.0.1','8.8.4.4','149.112.112.112','208.67.220.220'}
M.ACTIVE=3
M.K=2
M.MISS_LIMIT=3
M.WINDOW=60
M.OPTION='heartbeat_quorum'

local Pool={};Pool.__index=Pool
function M.Pool(pool,active,k,start)
  pool=pool or M.POOL;active=active or M.ACTIVE;k=k or M.K;start=(start or 0)%#pool
  local self=setmetatable({pool=pool,k=k,active={},misses={},rotations=0},Pool)
  for i=0,active-1 do self.active[#self.active+1]=pool[(start+i)%#pool+1] end
  self.next=(start+active)%#pool
  return self
end
function Pool:targets() local out={};for i,t in ipairs(self.active) do out[i]=t end;return out end
local function index_of(list,value) for i,v in ipairs(list) do if v==value then return i end end;return nil end
function Pool:replace(target)
  for _=1,#self.pool do
    local candidate=self.pool[self.next+1];self.next=(self.next+1)%#self.pool
    if not index_of(self.active,candidate) then
      self.active[index_of(self.active,target)]=candidate
      self.misses[target]=nil;self.rotations=self.rotations+1
      return candidate
    end
  end
  return nil
end
-- answered: {[target]=true|false} for the active targets of the beat. Returns 'ok' or 'lost'.
function Pool:judge(answered,now)
  local missing={}
  for _,t in ipairs(self.active) do if answered[t]~=true then missing[#missing+1]=t end end
  if #missing>=self.k then return 'lost' end
  local missed={}
  for _,target in ipairs(missing) do
    missed[target]=true
    local stamps={}
    for _,s in ipairs(self.misses[target] or {}) do if now-s>=0 and now-s<M.WINDOW then stamps[#stamps+1]=s end end
    stamps[#stamps+1]=now
    self.misses[target]=stamps
    if #stamps>=M.MISS_LIMIT then self:replace(target) end
  end
  local names={}
  for target in pairs(self.misses) do names[#names+1]=target end
  table.sort(names)
  for _,target in ipairs(names) do
    if not missed[target] and index_of(self.active,target) then
      local kept={}
      for _,s in ipairs(self.misses[target]) do if now-s>=0 and now-s<M.WINDOW then kept[#kept+1]=s end end
      self.misses[target]=(#kept>0) and kept or nil
    end
  end
  return 'ok'
end

function M.enabled(settings) return type(settings)=='table' and settings[M.OPTION]==true end

return M
