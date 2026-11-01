-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- live_probe.lua: the live channel probe of the Lua Auto supervisor (plan item 4) - agent.probe(profile) and
-- native_switch.trace(profile) in Lua, in place of the lua_bridge.py Python start (~2 s CPU per call).
--
--   local L=require('live_probe').new(io)
--   L.probe(profile, keep)  -> the agent.probe result (same fields and codes as lua_bridge.py `probe`)
--   L.trace(profile)        -> exit IPv4 text, or raises the native_switch.trace refusal code
--
-- io (sys.lua on the router through backend.lua, fakes in tests):
--   io.wall()  io.clock()  io.random(n)
--   io.route_binding(logical) -> backend.route_binding result; a coded refusal = Python's command/JSON failure
--   io.probe_io(device, requests, dns) -> answers, dns_data|nil, dns_kind
--     requests[i]={address,hostname,path,seconds}; answers[i]={response={status,body,oversize}|nil, kind, elapsed}
--     dns={host,port,packet,seconds,accept(data)}; all HTTPS checks and the DNS check run at the same time.
--
-- Same rules as agent.probe: route binding before and after (VENDOR-IDENTITY-CHANGED), 3 HTTPS targets (2 valid
-- answers else VPN-003), DNS over UDP to 9.9.9.9 (else DNS-001), exit_ip only from a global IPv4 in the trace.
-- Router facts as in the Lua monitor: no SO_MARK, the checks are bound to the tunnel device only (UDP through a
-- nixio socket, HTTPS through `curl --interface`); the fwmark stays part of the compared route identity.
-- Deliberate differences: no `server_endpoint` (the supervisor never reads it; the monitor publishes it through
-- server_endpoint.lua), and
-- elapsed/rtt values are curl's own time_total (Python measured inside its TLS socket).
-- trace(): Python probes and then fetches /cdn-cgi/trace once more over the same device. The probe's own trace
-- target is that same request; when it answered with a valid trace body that body is used, otherwise the
-- separate fetch runs exactly as in Python. A probe(profile, true) result is kept for one trace() of the same
-- profile within TRACE_REUSE_SECONDS (the WAIT-CLIENT confirmation calls probe() and then trace() at once).
local canon=require('canon')
local probe=require('probe')
local py=require('py')

local M={}
local NULL=canon.null
M.HTTP_SECONDS=probe.HTTP_SECONDS   -- probe_deadline.HTTP_SECONDS
M.DNS_SECONDS=3                     -- agent.bound_socket settimeout(3)
M.TRACE_REUSE_SECONDS=2
M.TRACE_TARGET={address='1.1.1.1',hostname='one.one.one.one',path='/cdn-cgi/trace'}
local TARGETS=probe.TARGETS
local BINDING_KEYS=probe.BINDING_KEYS
local ADMIN={enabled=true,disabled=true,unknown=true}

local function isnone(v) return v==nil or v==NULL end
local truthy=py.truthy
local function refuse(code) error(setmetatable({code=code},require('auto_control').Refused),0) end
local function coded(err) return type(err)=='table' and type(err.code)=='string' end
local function ms(seconds)
  local v=(tonumber(seconds) or 0)*1000
  if v~=v or v<0 then v=0 end
  return canon.float(math.floor(v*10+0.5)/10)
end

------------------------------------------------------------------------------------------------------
-- ipaddress.IPv4Address(text) and .is_global as in Python 3.9 (the router's python3)
------------------------------------------------------------------------------------------------------
-- strict dotted quad: four decimal octets <= 255, no leading zero (Python >= 3.9.5); nil otherwise
function M.ipv4(text)
  if type(text)~='string' then return nil end
  local parts={}
  for part in string.gmatch(text..'.','([^.]*)%.') do parts[#parts+1]=part end
  if #parts~=4 then return nil end
  local out={}
  for i,part in ipairs(parts) do
    if not string.find(part,'^%d%d?%d?$') or (#part>1 and string.sub(part,1,1)=='0') then return nil end
    local n=tonumber(part)
    if n>255 then return nil end
    out[i]=n
  end
  return out
end
-- ipaddress._private_networks of Python 3.9 and the shared 100.64.0.0/10 (is_global = neither)
function M.is_global(o)
  local a,b,c,d=o[1],o[2],o[3],o[4]
  if a==0 or a==10 or a==127 or a>=240 then return false end            -- 0/8, 10/8, 127/8, 240/4 (incl. 255.255.255.255)
  if a==169 and b==254 then return false end                            -- 169.254/16
  if a==172 and b>=16 and b<=31 then return false end                   -- 172.16/12
  if a==192 and b==168 then return false end                            -- 192.168/16
  if a==192 and b==0 and c==0 and (d<8 or d==170 or d==171) then return false end  -- 192.0.0.0/29, 192.0.0.170/31
  if a==192 and b==0 and c==2 then return false end                     -- 192.0.2/24
  if a==198 and (b==18 or b==19) then return false end                  -- 198.18/15
  if a==198 and b==51 and c==100 then return false end                  -- 198.51.100/24
  if a==203 and b==0 and c==113 then return false end                   -- 203.0.113/24
  if a==100 and b>=64 and b<=127 then return false end                  -- 100.64/10 (shared)
  return true
end
-- str.splitlines() of an ASCII text: \n, \r, \r\n, \v, \f, \x1c, \x1d, \x1e
local function splitlines(text)
  local lines={}
  local normalized=string.gsub(string.gsub(text,'\r\n','\n'),'[\r\v\f\28\29\30]','\n')
  for line in string.gmatch(normalized..(string.sub(normalized,-1)=='\n' and '' or '\n'),'([^\n]*)\n') do lines[#lines+1]=line end
  return lines
end
M.splitlines=splitlines
-- str.strip(): ASCII whitespace incl. \x1c-\x1f
local function strip(s) return (string.match(s,'^[%s\28-\31]*(.-)[%s\28-\31]*$')) end

-- agent.remember_exit: the first `ip=` line decides; a global IPv4 only
function M.remember_exit(body)
  for _,line in ipairs(splitlines(body)) do
    if string.sub(line,1,3)=='ip=' then
      local text=strip(string.sub(line,4))
      local o=M.ipv4(text)
      if o and M.is_global(o) then return text end
      return nil
    end
  end
  return nil
end

-- native_switch.trace: the reply of GET /cdn-cgi/trace -> exit IPv4, or EXIT-TRACE-FAILED / EXIT-IP-NOT-GLOBAL
function M.exit_of(response)
  if type(response)~='table' or response.status~=200 or response.oversize or type(response.body)~='string' or #response.body>32768 then refuse('EXIT-TRACE-FAILED') end
  local body=response.body
  if string.find(body,'[\128-\255]') then refuse('EXIT-TRACE-FAILED') end  -- body.decode('ascii')
  local ip=nil
  for _,line in ipairs(splitlines(body)) do  -- dict(line.split('=',1) ...): the last `ip` key wins
    local key,value=string.match(line,'^([^=]*)=(.*)$')
    if key=='ip' then ip=value end
  end
  if ip==nil then refuse('EXIT-TRACE-FAILED') end
  local text=strip(ip)
  local o=M.ipv4(text)
  if not o then refuse('EXIT-TRACE-FAILED') end
  if not M.is_global(o) then refuse('EXIT-IP-NOT-GLOBAL') end
  return text
end

------------------------------------------------------------------------------------------------------
-- one HTTPS check (agent.https_probe + https_for_probe) from a probe_io answer
------------------------------------------------------------------------------------------------------
local function https_check(target,answer,token)
  local kind=target[4]
  local detail=canon.object({target=target[2],result='unknown'})
  answer=answer or {kind='transport-error'}
  detail.elapsed_ms=ms(answer.elapsed)
  local response=answer.response
  if not response then detail.result=answer.kind or 'transport-error';return detail,nil end
  detail.http_status=response.status
  if response.status~=200 then
    detail.result=(response.status==426 or response.status==505) and 'http-unsupported' or 'http-error';return detail,nil
  end
  local body=response.body
  if response.oversize or type(body)~='string' or #body>32768 then detail.result='invalid-response';return detail,nil end
  local valid=false
  if kind=='trace' then
    valid=string.find('\n'..body,'\nip=',1,true)~=nil and string.find('\n'..body,'\nhttp=',1,true)~=nil
  elseif kind=='dns-json' then
    -- payload.get('Status') == 0 and bool(payload.get('Answer'))
    local ok,payload=pcall(canon.decode,body)
    valid=ok and canon.is_object(payload) and canon.number(payload.Status)==0 and py.truthy(payload.Answer)
  else
    valid=probe.valid_dns(body,token)
  end
  detail.result=valid and 'ok' or 'invalid-response'
  if not valid then return detail,nil end
  return detail,detail.elapsed_ms.value
end

------------------------------------------------------------------------------------------------------
-- probe / trace
------------------------------------------------------------------------------------------------------
function M.new(io_)
  local L={}
  local kept={}

  -- measure(profile) -> result, trace_body (the valid trace body of this very probe, never published)
  local function measure(profile)
    local result=canon.object({id=profile.id,time=canon.float(io_.wall()),code='CHECK-001',scope='router-originated',lan_path_verified=false})
    local administrative_state=profile.administrative_state
    if administrative_state==nil then administrative_state='unknown' end
    if type(administrative_state)=='string' and ADMIN[administrative_state] then result.administrative_state=administrative_state end
    if not truthy(profile.interface) or administrative_state=='disabled' then result.code='PROFILE-INACTIVE';return result,nil end
    local trace_body=nil
    local ok,err=pcall(function()
      local binding=io_.route_binding(profile.interface)
      for k,v in pairs(binding) do result[k]=v end
      if not isnone(binding.code) then return end
      local requests,tokens={},{}
      for i,target in ipairs(TARGETS) do
        local path=target[3]
        if target[4]=='dns-wire' then
          local token,packet=probe.dns_question(io_)
          tokens[i]=token;path=path..'?dns='..probe.urlsafe_b64(packet)
        end
        requests[i]={address=target[1],hostname=target[2],path=path,seconds=M.HTTP_SECONDS}
      end
      local token,packet,question=probe.dns_question(io_)
      local answers,dns_data=io_.probe_io(binding.device,requests,{host='9.9.9.9',port=53,packet=packet,seconds=M.DNS_SECONDS,
        accept=function(data) return type(data)=='string' and string.sub(data,1,2)==token end})
      local times,checks,sum=0,canon.array({}),0
      for i,target in ipairs(TARGETS) do
        local answer=answers[i]
        local detail,value=https_check(target,answer,tokens[i])
        checks[#checks+1]=detail
        if value then
          times=times+1;sum=sum+value
          if target[4]=='trace' then trace_body=answer.response.body end
        end
      end
      local dns_ok=type(dns_data)=='string' and probe.valid_dns(dns_data,token) and string.sub(dns_data,13,12+#question)==question
      result.https_success=times;result.dns_ok=dns_ok==true;result.probe_checks=checks
      result.rtt_ms=times>0 and canon.float(math.floor(sum/times*10+0.5)/10) or NULL
      result.code=times<2 and 'VPN-003' or (dns_ok and NULL or 'DNS-001')
      -- a socket quorum cannot survive a route/device epoch change during the measurement
      local after=io_.route_binding(profile.interface)
      local changed=not isnone(after.code)
      for _,key in ipairs(BINDING_KEYS) do if after[key]~=binding[key] then changed=true end end
      if changed then
        for _,key in ipairs({'https_success','dns_ok','rtt_ms','exit_ip','probe_checks'}) do result[key]=nil end
        result.code='VENDOR-IDENTITY-CHANGED';trace_body=nil
        return
      end
      local exit_ip=trace_body and M.remember_exit(trace_body)
      if exit_ip and isnone(result.code) then result.exit_ip=exit_ip end
    end)
    if not ok then
      if not coded(err) then error(err,0) end  -- a Lua fault, not a router answer: the caller falls back to Python
      result.code='SYSTEM-001';trace_body=nil  -- Python: OSError/ValueError/SubprocessError
    end
    return result,trace_body
  end

  -- probe(profile, keep): keep=true remembers a passing result for one following trace() of the same profile
  function L.probe(profile,keep)
    local result,trace_body=measure(profile)
    kept[profile.id]=nil
    if keep and isnone(result.code) and result.dns_ok==true and (result.https_success or 0)>=2 and trace_body then
      kept[profile.id]={clock=io_.clock(),interface=profile.interface,trace_body=trace_body}
    end
    return result
  end

  function L.trace(profile)
    local row=kept[profile.id]
    kept[profile.id]=nil
    local now=io_.clock()
    if row and row.interface==profile.interface and now-row.clock>=0 and now-row.clock<=M.TRACE_REUSE_SECONDS then
      return M.exit_of({status=200,body=row.trace_body})
    end
    local result,trace_body=measure(profile)
    if not isnone(result.code) or result.dns_ok~=true or (result.https_success or 0)<2 then refuse('TARGET-HTTPS-DNS-FAILED') end
    if trace_body then return M.exit_of({status=200,body=trace_body}) end
    -- the probe's own trace target failed while two others passed: the separate fetch of native_switch.trace
    local t=M.TRACE_TARGET
    local answers=io_.probe_io(result.device,{{address=t.address,hostname=t.hostname,path=t.path,seconds=M.HTTP_SECONDS}},nil)
    local answer=answers[1] or {kind='transport-error'}
    if not answer.response then
      -- curl's "oversize" (63) is a body Python reads and refuses; every socket/TLS/time failure is an OSError
      -- there, which lua_bridge.py reports as NATIVE-SYSTEM-001
      refuse(answer.kind=='invalid-response' and 'EXIT-TRACE-FAILED' or 'NATIVE-SYSTEM-001')
    end
    return M.exit_of(answer.response)
  end

  L.measure=measure
  return L
end

return M
