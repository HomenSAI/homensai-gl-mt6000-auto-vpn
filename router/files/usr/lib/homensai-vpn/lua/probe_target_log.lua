-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- probe_target_log.lua: the per-target probe log of the Lua monitor (twin of probe_target_log.py; shared cases
-- router/tests/probe_target_log_cases.json, the format is described in the Python module's header).
-- The monitor writes one line per Auto channel per pass into a RAM ring (two append-only segments of at most
-- SEGMENT bytes, /var/run/homensai-vpn/probe-targets.log and .1); the RPC probe_targets reads it. It measures nothing:
-- the numbers are the ones of the pass (probe_checks, dns_ok, the verdict) and of the ICMP heartbeat counters
-- (fast_detect.lua Pulse:take_heartbeat). Option probe_target_log (inventory.lua), default on.
local canon=require('canon')

local M={}
M.OPTION='probe_target_log'
M.NAME='probe-targets.log'
M.SEGMENT=128*1024
M.RING_BYTES=2*M.SEGMENT
M.FORMAT=1
M.TARGETS={'one.one.one.one','dns.google','dns.quad9.net'}
M.HEARTBEAT_SLOTS={'1.1.1.1','8.8.8.8','9.9.9.9'}
M.DEFAULT_ROWS=200
M.MAX_ROWS=1000
local RESULTS={ok=0,timeout=1,['tls-error']=2,['invalid-response']=3,['transport-error']=4,['http-error']=5,['http-unsupported']=6}
local RESULT_UNKNOWN,NOT_MEASURED,UNTRUSTED=7,9,10
local TRUST_REASONS={['untrusted-certificate']=true,['portal-redirect']=true,['stale-response']=true}
local VERDICTS={['DNS-001']=1,['VPN-003']=2,['VPN-001']=3,['VPN-MTU']=4,['ROUTE-001']=5,['CHECK-001']=6,['SYSTEM-001']=7,
  ['VENDOR-IDENTITY-CHANGED']=8}
local VERDICT_OTHER=9
local MAX_MS,MAX_COUNT,MAX_STAMP=600000,65535,999999999999
M.MAX_COUNT=MAX_COUNT
local NULL=canon.null

function M.enabled(settings) return type(settings)=='table' and settings[M.OPTION]==true end

-- a plain number, or the value of a Python-float box; nil for anything else (also NaN and infinity)
local function number(v)
  if canon.is_float(v) then v=v.value end
  if type(v)~='number' or v~=v or v==math.huge or v==-math.huge then return nil end
  return v
end
local function is_id(v) return type(v)=='string' and #v>=1 and #v<=64 and string.find(v,'^[A-Za-z0-9_.:-]+$')~=nil end
local function present(v) if v==NULL then return nil end;return v end

-- result_code(detail) -> code, latency ms
function M.result_code(detail)
  if type(detail)~='table' or detail==NULL then return NOT_MEASURED,-1 end
  local code=RESULTS[present(detail.result)]
  if code==nil then code=RESULT_UNKNOWN end
  if TRUST_REASONS[present(detail.trust)] then code=code+UNTRUSTED end
  local elapsed=number(detail.elapsed_ms)
  if elapsed==nil then return code,-1 end
  return code,math.min(math.max(math.floor(elapsed+0.5),0),MAX_MS)
end

function M.verdict_code(code)
  code=present(code)
  if code==nil then return 0 end
  if type(code)~='string' then return VERDICT_OTHER end
  return VERDICTS[code] or VERDICT_OTHER
end

function M.heartbeat_slot(target)
  for i,name in ipairs(M.HEARTBEAT_SLOTS) do if name==target then return i end end
  return #M.HEARTBEAT_SLOTS+1
end

local function heartbeat(hb)
  if type(hb)~='table' or hb==NULL or #hb~=8 then return {} end
  local sent=false
  for i=1,8 do
    local v=hb[i]
    if type(v)~='number' or v%1~=0 or v<0 or v>MAX_COUNT then return {} end
    if i%2==1 and v>0 then sent=true end
  end
  if not sent then return {} end
  return hb
end

-- encode(seq, result, dense, hb, now) -> line with its newline, or nil
function M.encode(seq,result,dense,hb,now)
  if type(result)~='table' or result==NULL or not is_id(result.id) then return nil end
  local stamp=number(result.time)
  if stamp==nil then stamp=number(now) end
  if stamp==nil or stamp<0 or stamp>MAX_STAMP then return nil end
  local by_target={}
  local list=present(result.probe_checks)
  if type(list)=='table' then
    for _,detail in ipairs(list) do
      if type(detail)=='table' and detail~=NULL then
        local name=present(detail.target)
        for _,known in ipairs(M.TARGETS) do if name==known then by_target[known]=detail end end
      end
    end
  end
  local checks={}
  for _,target in ipairs(M.TARGETS) do
    local code,ms=M.result_code(by_target[target])
    checks[#checks+1]=code;checks[#checks+1]=ms
  end
  local dns=present(result.dns_ok)
  if dns==true then dns=0 elseif dns==false then dns=1 else dns=NOT_MEASURED end
  return string.format('[%d,%d,"%s",%d,%d,[%s],%d,[%s]]\n',seq,math.floor(stamp),result.id,M.verdict_code(result.code),
    dense and 1 or 0,table.concat(checks,','),dns,table.concat(heartbeat(hb),','))
end

local function ints(text)
  local out=canon.array()
  for token in string.gmatch(text,'[^,]+') do out[#out+1]=tonumber(token) end
  return out
end

-- parse_line(line) -> the row (a JSON array of this format) or nil for anything else than exactly a line of it
function M.parse_line(line)
  if #line>400 then return nil end
  local seq,stamp,ident,verdict,flags,checks,dns,hb=string.match(line,
    '^%[(%d+),(%d+),"([A-Za-z0-9_.:-]+)",(%d+),(%d+),%[([%d,%-]+)%],(%d+),%[([%d,]*)%]%]$')
  if not seq or #seq>15 or #stamp>12 or #ident>64 or #verdict>2 or #flags>3 or #dns>2 then return nil end
  -- the checks: three (code 1-2 digits, latency -1 or up to 6 digits) pairs; the heartbeat: none or 8 numbers of up to 5 digits
  local c1,l1,c2,l2,c3,l3=string.match(checks,'^(%d%d?),(%-?%d+),(%d%d?),(%-?%d+),(%d%d?),(%-?%d+)$')
  if not c1 then return nil end
  for _,l in ipairs({l1,l2,l3}) do
    local digits=string.gsub(l,'^%-','')
    if #digits>6 then return nil end
  end
  local row_hb=canon.array()
  if hb~='' then
    if not string.find(hb,'^%d%d?%d?%d?%d?,%d%d?%d?%d?%d?,%d%d?%d?%d?%d?,%d%d?%d?%d?%d?,%d%d?%d?%d?%d?,%d%d?%d?%d?%d?,%d%d?%d?%d?%d?,%d%d?%d?%d?%d?$') then return nil end
    row_hb=ints(hb)
  end
  return canon.array({tonumber(seq),tonumber(stamp),ident,tonumber(verdict),tonumber(flags),
    canon.array({tonumber(c1),tonumber(l1),tonumber(c2),tonumber(l2),tonumber(c3),tonumber(l3)}),tonumber(dns),row_hb})
end

-- the complete lines of a segment (a last line without its newline is a torn or running write: dropped)
local function complete_lines(text)
  local lines={}
  if type(text)~='string' or text=='' then return lines end
  local start=1
  while true do
    local stop=string.find(text,'\n',start,true)
    if not stop then break end
    lines[#lines+1]=string.sub(text,start,stop-1)
    start=stop+1
  end
  return lines
end
M.complete_lines=complete_lines

function M.last_seq(text)
  local last=0
  for _,line in ipairs(complete_lines(text)) do
    local row=M.parse_line(line)
    if row then last=row[1] end
  end
  return last
end

-- select(old, new, after, limit) -> the reply object of the RPC
function M.select(old,new,after,limit)
  after=after or 0;limit=limit or M.DEFAULT_ROWS
  local lines={}
  for _,text in ipairs({old or '',new or ''}) do
    for _,line in ipairs(complete_lines(text)) do lines[#lines+1]=line end
  end
  -- first and last are the numbers of the first and the last valid line of the ring; the lines in between are only
  -- looked at when their number (a cheap prefix test) is beyond the cursor, so a poll of the newest rows costs little
  local first,last=0,0
  for i=1,#lines do local row=M.parse_line(lines[i]);if row then first=row[1];break end end
  for i=#lines,1,-1 do local row=M.parse_line(lines[i]);if row then last=row[1];break end end
  local rows,more=canon.array(),false
  for i=1,#lines do
    local number=tonumber(string.match(lines[i],'^%[(%d+),') or '')
    if number and number>after then
      local row=M.parse_line(lines[i])
      if row then
        if #rows<limit then rows[#rows+1]=row else more=true;break end
      end
    end
  end
  local slots=canon.array();for i,name in ipairs(M.HEARTBEAT_SLOTS) do slots[i]=name end;slots[#slots+1]='other'
  local targets=canon.array();for i,name in ipairs(M.TARGETS) do targets[i]=name end
  return canon.object({version=M.FORMAT,targets=targets,heartbeat=slots,first=first,last=last,count=#rows,truncated=more,rows=rows})
end

-- arguments(request) -> after, limit (request: the decoded argument object); raises the codes the page already explains:
-- RPC-INPUT-OBJECT (not an object), RPC-UNEXPECTED-ARGS (another field), RPC-INPUT-INVALID (a value outside its form)
function M.arguments(request)
  local function bad(code) error({code=code},0) end
  if type(request)~='table' or request==NULL or canon.is_array(request) then bad('RPC-INPUT-OBJECT') end
  for key in pairs(request) do if key~='after' and key~='limit' then bad('RPC-UNEXPECTED-ARGS') end end
  local after,limit=request.after,request.limit
  if after==nil then after=0 end
  if limit==nil then limit=M.DEFAULT_ROWS end
  if type(after)~='number' or after%1~=0 or after<0 or after>1e15 or type(limit)~='number' or limit%1~=0 or limit<1 or limit>M.MAX_ROWS then bad('RPC-INPUT-INVALID') end
  return after,limit
end

-- read(read_file, directory, request) -> reply object; read_file(path) -> text | nil (raises on a link: the runner's)
function M.read(read_file,directory,request)
  local after,limit=M.arguments(request or canon.object())
  local base=directory..'/'..M.NAME
  return M.select(read_file(base..'.1'),read_file(base),after,limit)
end

------------------------------------------------------------------------------------------------------
-- the monitor's side
------------------------------------------------------------------------------------------------------
local Writer={};Writer.__index=Writer
-- runner: read_file(path), append(path, text), rename(from, to); directory: the RAM runtime directory
function M.Writer(runner,directory,segment)
  return setmetatable({runner=runner,path=directory..'/'..M.NAME,segment=segment or M.SEGMENT,seq=nil,size=0},Writer)
end

function Writer:resume()
  local runner=self.runner
  local current=runner.read_file(self.path) or ''
  self.size=#current
  local seq=M.last_seq(current)
  if seq==0 then seq=M.last_seq(runner.read_file(self.path..'.1') or '') end
  self.seq=seq
end

-- record(results, hb, dense, now) -> number of lines written; hb: {profile id -> 8 counters} or nil. Raises when the
-- ring cannot be written (the monitor catches it and goes on).
function Writer:record(results,hb,dense,now)
  if self.seq==nil then self:resume() end
  local lines,seq={},self.seq
  for _,result in ipairs(results) do
    local counters=nil
    if hb and type(result)=='table' then counters=hb[result.id] end
    local line=M.encode(seq+1,result,dense,counters,now)
    if line then seq=seq+1;lines[#lines+1]=line end
  end
  if #lines==0 then return 0 end
  local data=table.concat(lines)
  if self.size+#data>self.segment and self.size>0 then
    self.runner.rename(self.path,self.path..'.1')
    self.size=0
  end
  self.runner.append(self.path,data)
  self.size=self.size+#data
  self.seq=seq
  return #lines
end

return M
