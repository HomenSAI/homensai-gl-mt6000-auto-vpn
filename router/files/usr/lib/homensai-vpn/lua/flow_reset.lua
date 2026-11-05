-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- flow_reset.lua: after a verified move of the LAN traffic from one channel to the other, drop the LAN flows
-- that are still source-NATed to the channel left, so applications reconnect at once (flow_reset.py is the
-- Python twin; tests/flow_reset_cases.json is shared by both).
--
-- Why (MT3000, 03.11.2026, external LAN client): GL route_policy marks every packet again (MARK, no CONNMARK
-- save for TCP: the TCP flow's ctmark stays 0x0), so after the move the packets of an old TCP flow leave
-- through the new tunnel while conntrack still rewrites their source to the OLD tunnel address; the new peer
-- drops them silently and the connection hangs until the application's own timeout (~40 s). The existing
-- `conntrack -D -m <old mark>` only catches the few flows whose ctmark was saved (DNS).
--
-- What identifies exactly those flows: masqueraded (source-NAT) and reply destination = the old tunnel's
-- IPv4 address. One command (conntrack-tools 1.4.6 of GL 4.x, -D accepts -f, --reply-dst and --src-nat):
--   conntrack -D -f ipv4 --reply-dst <old address> --src-nat
-- Not matched, by construction: the router's own flows (not NATed: SSH/LuCI from the LAN, the router's probes
-- bound to a tunnel), inbound flows, the new tunnel's flows (other address; equal addresses -> nothing done).
-- After the delete the next packet of such a flow creates a fresh entry through the CURRENT policy (new tunnel,
-- new NAT address); the far end does not know that address/port and answers with a reset, so the application
-- sees the error now instead of after its timeout. Nothing opens a WAN path: the routing and the VPN-only guard
-- are untouched. Bounded (timeout 1 s); every failure is a code in the system log, never a switch failure.
-- On by default; `option flow_reset '0'` in /etc/config/homensai_vpn turns it off. Without that file (a host,
-- the tests) nothing runs.
local M={}
M.CONFIG='/etc/config/homensai_vpn'
M.TIMEOUT=1
M.PREFIX='FLOW-RESET-'

-- enabled(config text): on unless `option flow_reset '0'`; no config -> off
function M.enabled(text)
  if type(text)~='string' then return false end
  for line in string.gmatch(text..'\n','([^\n]*)\n') do
    if string.find(line,"^%s*option%s+flow_reset%s+'?0'?%s*$") then return false end
  end
  return true
end

-- strict dotted quad, no leading zeros; not 0/8, 127/8, multicast/reserved
function M.ipv4(text)
  if type(text)~='string' or #text>15 then return nil end
  local a,b,c,d=string.match(text,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  if not a then return nil end
  local parts={a,b,c,d}
  for i=1,4 do
    local p=parts[i]
    if #p>1 and string.sub(p,1,1)=='0' then return nil end
    local n=tonumber(p)
    if not n or n>255 then return nil end
    parts[i]=n
  end
  if parts[1]==0 or parts[1]==127 or parts[1]>=224 then return nil end
  return text
end

-- address(netifd interface status): the first IPv4 address of an interface that is up, else nil
function M.address(status)
  if type(status)~='table' or status.up~=true then return nil end
  local list=status['ipv4-address']
  if type(list)~='table' then return nil end
  for _,row in ipairs(list) do
    if type(row)=='table' then
      local address=M.ipv4(row.address)
      if address then return address end
    end
  end
  return nil
end

function M.argv(address) return {'conntrack','-D','-f','ipv4','--reply-dst',address,'--src-nat'} end

local function lines(out)
  local n=0
  for line in string.gmatch(type(out)=='string' and out or '','[^\n]+') do
    if string.find(line,'%S') then n=n+1 end
  end
  return n
end

-- outcome(rc, stdout, timed_out) -> code, deleted. conntrack -D prints one line per deleted flow and
-- exits 1 when it deleted none; timeout(1) ends it with 124 (coreutils) or 143 (busybox, SIGTERM).
function M.outcome(rc,out,timed_out)
  local deleted=lines(out)
  if timed_out or rc==124 or rc==143 or rc==137 then return 'FLOW-RESET-TIMEOUT',deleted end
  if rc==126 or rc==127 then return 'FLOW-RESET-NO-TOOL',0 end
  if rc==0 then return 'FLOW-RESET-DONE',deleted end
  if rc==1 and deleted==0 then return 'FLOW-RESET-NONE',0 end
  return 'FLOW-RESET-FAILED',deleted
end

-- run(ctx): ctx.config (text|nil), ctx.old_status / ctx.new_status (netifd status|nil),
-- ctx.exec(argv) -> rc, stdout, timed_out; ctx.log(line). Returns {code=, deleted=, address=}.
function M.run(ctx)
  local result={code='FLOW-RESET-OFF',deleted=0,address=nil}
  if not M.enabled(ctx.config) then return result end
  local old,new=M.address(ctx.old_status),M.address(ctx.new_status)
  result.address=old
  local code,deleted=nil,0
  if not old or not new then code='FLOW-RESET-NO-ADDRESS'
  elseif old==new then code='FLOW-RESET-SAME-ADDRESS'
  else
    local ok,rc,out,timed_out=pcall(ctx.exec,M.argv(old))
    if ok then code,deleted=M.outcome(rc,out,timed_out) else code='FLOW-RESET-FAILED' end
  end
  result.code=code;result.deleted=deleted
  if ctx.log then pcall(ctx.log,result.code..': address '..(old or 'none')..' deleted '..tostring(deleted)) end
  return result
end

return M
