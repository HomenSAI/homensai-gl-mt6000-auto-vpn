-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- probe_trust.lua: probe authenticity, the twin of probe_trust.py (same rules, shared cases
-- tests/probe_trust_cases.json; design docs/architecture/PROBE-AUTHENTICITY-2026-11-03.ru.md).
--   anchor_file(host)  the pinned roots of a fixed probe host (curl --cacert); nil = the system store (alpha7 check)
--   agent(random)      User-Agent 'HomenSAI-probe/<32 hex>' with a fresh 128-bit nonce (curl -A)
--   fresh(body,agent,wall_start,wall_end,elapsed)  nil when a /cdn-cgi/trace body answers this very request,
--                      else 'nonce-mismatch' | 'no-freshness' | 'clock-jump' | 'stale-time'
--   dns_mode(text)     'doh' with `option probe_dns 'doh'` in config main 'main', else 'udp'
-- curl exit codes of an untrusted peer (7.83): 60 peer verification failed (CA or name), 51 its older number,
-- 83 issuer check failed, 90 pinned key mismatch. 77 (CA file unreadable) is a local fault, not untrusted.
local M={}
M.ANCHORS='/usr/lib/homensai-vpn/probe-anchors'
M.AGENT_PREFIX='HomenSAI-probe/'
M.FRESH_SECONDS=60
M.JUMP_SECONDS=2
M.UNTRUSTED='untrusted-certificate'
M.REDIRECT='portal-redirect'
M.STALE='stale-response'
M.REASONS={['untrusted-certificate']=true,['portal-redirect']=true,['stale-response']=true}
M.DNS_OPTION='probe_dns'
M.DOH_TARGET={'8.8.8.8','dns.google','/dns-query','dns-wire'}
M.CURL_UNTRUSTED={[51]=true,[60]=true,[83]=true,[90]=true}

local present={}
function M.anchor_file(hostname)
  if type(hostname)~='string' or #hostname<1 or #hostname>64 or not string.find(hostname,'^[a-z0-9.-]+$')
     or string.find(hostname,'..',1,true) then return nil end
  local path=M.ANCHORS..'/'..hostname..'.pem'
  if present[path]==nil then
    local f=io.open(path,'rb')
    present[path]=f~=nil
    if f then f:close() end
  end
  return present[path] and path or nil
end

function M.agent(random)
  local bytes=random(16)
  local out={}
  for i=1,#bytes do out[i]=string.format('%02x',string.byte(bytes,i)) end
  return M.AGENT_PREFIX..table.concat(out)
end

function M.redirect(status) return type(status)=='number' and status%1==0 and status>=300 and status<=399 end

function M.fresh(body,expected,wall_start,wall_end,elapsed)
  local agents,stamps={},{}
  for line in string.gmatch((body or '')..'\n','([^\n]*)\n') do
    if string.sub(line,-1)=='\r' then line=string.sub(line,1,-2) end
    if string.sub(line,1,4)=='uag=' then agents[#agents+1]=string.sub(line,5)
    elseif string.sub(line,1,3)=='ts=' then stamps[#stamps+1]=string.sub(line,4) end
  end
  if #agents>0 then
    for _,value in ipairs(agents) do if value~=expected then return 'nonce-mismatch' end end
    return nil
  end
  local ts=stamps[1]
  if #stamps~=1 or not (string.find(ts,'^%d+$') or string.find(ts,'^%d+%.%d+$')) then return 'no-freshness' end
  local whole,fraction=string.match(ts,'^(%d+)%.?(%d*)$')
  if #whole>12 or #fraction>9 then return 'no-freshness' end
  if math.abs((wall_end-wall_start)-elapsed)>M.JUMP_SECONDS then return 'clock-jump' end
  local stamp=tonumber(ts)
  if stamp>=wall_start-M.FRESH_SECONDS and stamp<=wall_end+M.FRESH_SECONDS then return nil end
  return 'stale-time'
end

function M.dns_mode(text)
  if type(text)~='string' then return 'udp' end
  local section,found=nil,nil
  for line in string.gmatch(text,'[^\n]+') do
    if string.find(line,'^%s*config%s') then
      section=string.match(line,'^%s*config%s+%S+%s+["\']?([A-Za-z0-9_]+)["\']?%s*$')
    elseif section=='main' then
      local value=string.match(line,'^%s*option%s+'..M.DNS_OPTION..'%s+["\']?([^"\'%s]*)["\']?%s*$')
      if value then found=value end
    end
  end
  return found=='doh' and 'doh' or 'udp'
end

-- current_dns_mode(mtime_fn, text_fn): dns_mode() of the configuration, re-read only when its key changed
local cached={key=nil,value='udp'}
function M.current_dns_mode(key_fn,text_fn)
  if not key_fn or not text_fn then return 'udp' end
  local ok,key=pcall(key_fn)
  if not ok or key==nil then return 'udp' end
  if key~=cached.key then
    local okt,text=pcall(text_fn)
    if not okt or type(text)~='string' then return 'udp' end
    cached.key=key;cached.value=M.dns_mode(text)
  end
  return cached.value
end
function M.reset() present={};cached={key=nil,value='udp'} end

function M.untrusted(checks)
  for _,row in ipairs(checks or {}) do if type(row)=='table' and M.REASONS[row.trust] then return true end end
  return false
end

return M
