-- Minimal test harness for the Lua core: plain lua5.1, no router modules.
-- Usage in a test file:  local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/?.lua;'..package.path

local T={here=here,cases={},failures=0}

-- canon's sha256sum pipe writes its output file into a RAM directory; on a PC use TMPDIR or /tmp.
require('canon').configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})

function T.test(name,fn) T.cases[#T.cases+1]={name,fn} end

local function show(v)
  if type(v)=='string' then return string.format('%q',v) end
  if type(v)=='table' then
    local parts={}
    for i=1,#v do parts[i]=show(v[i]) end
    return '{'..table.concat(parts,',')..'}'
  end
  return tostring(v)
end
T.show=show

local function deep(a,b)
  if type(a)~=type(b) then return false end
  if type(a)~='table' then return a==b end
  for k,v in pairs(a) do if not deep(v,b[k]) then return false end end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end

function T.eq(actual,expected,message)
  if not deep(actual,expected) then
    error((message or 'not equal')..': got '..show(actual)..', expected '..show(expected),2)
  end
end
function T.truthy(v,message) if not v then error(message or 'expected a true value',2) end end

-- Calls fn and returns the error object; fails when fn does not raise.
function T.raises(fn,...)
  local ok,err=pcall(fn,...)
  if ok then error('expected an error',2) end
  return err
end
-- Expects a coded error ({code=...}) with this code.
function T.code(expected,fn,...)
  local ok,err=pcall(fn,...)
  if ok then error('expected '..expected..', got success',2) end
  local code=type(err)=='table' and err.code or tostring(err)
  if code~=expected then error('expected '..expected..', got '..tostring(code),2) end
end

function T.run()
  local passed=0
  for _,case in ipairs(T.cases) do
    local ok,err=pcall(case[2])
    if ok then passed=passed+1
    else T.failures=T.failures+1;io.stderr:write('FAIL ',case[1],': ',tostring(type(err)=='table' and (err.code or show(err)) or err),'\n') end
  end
  local name=(arg and arg[0] or '?'):match('([^/]*)$')
  if T.failures==0 then print(name..': '..passed..' tests OK') else print(name..': '..T.failures..' FAILED of '..#T.cases) end
  os.exit(T.failures==0 and 0 or 1)
end

-- The fixtures of tests/test_fast_policy.py (byte-identical copies).
T.UCI=[[route_policy.gl_process_vpn=rule_process
route_policy.gl_process_vpn.from='20000'
route_policy.gl_process_vpn.tunnel_id='10100'
route_policy.gl_process_vpn.enabled='1'
route_policy.gl_process_vpn.via='ovpnclient2'
route_policy.gl_process_vpn.mark='0xb000'
route_policy.@rule[0].tunnel_id='4192'
route_policy.@rule[0].mark='0xb000'
route_policy.@rule[1].tunnel_id='5841'
route_policy.@rule[1].mark='0x1000'
]]
T.MANGLE=[[*mangle
-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000
-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN
-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY
-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY
-A TUNNEL10100_LOCAL_POLICY -m comment --comment "TUNNEL10100 rule for set mark" -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000
-A TUNNEL10100_LOCAL_POLICY -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j VPN_LOCAL_POLICY_DROP
-A TUNNEL4192_ROUTE_POLICY -m comment --comment "TUNNEL4192 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000
-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000
COMMIT
]]

-- Python str.replace(old,new): plain text, every occurrence; a fixture that no longer matches is an error.
function T.replace(text,old,new)
  local out,pos,found={},1,false
  while true do
    local i=string.find(text,old,pos,true)
    if not i then break end
    found=true;out[#out+1]=string.sub(text,pos,i-1);out[#out+1]=new;pos=i+#old
  end
  if not found then error('fixture text not found: '..old,2) end
  out[#out+1]=string.sub(text,pos)
  return table.concat(out)
end

return T
