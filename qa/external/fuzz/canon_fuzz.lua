-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- canon_fuzz.lua: returns check(text) for canon_fuzz.c. Needs CANON_LUA_DIR (router/files/usr/lib/homensai-vpn/lua).
-- check() raises an error (the harness aborts) when canon.lua and canon_c disagree on the same input.
package.path=assert(os.getenv('CANON_LUA_DIR'))..'/?.lua;'..package.path
local canon=require('canon')
local C=assert(canon.c_module,'canon_c rejected by canon.lua probe')
local NULL=canon.null
local KEYS={a=true,b=true,['']=true,events=true}

local function same(a,b)  -- order-insensitive deep equality; markers (metatables) and -0.0 included
  if a==NULL or b==NULL then return a==b end
  local ta,tb=type(a),type(b)
  if ta~=tb then return false end
  if ta=='number' then
    if a~=a then return b~=b end
    return a==b and (a~=0 or 1/a==1/b)
  end
  if ta~='table' then return a==b end
  if getmetatable(a)~=getmetatable(b) then return false end
  for k,v in pairs(a) do if not same(v,b[k]) then return false end end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end
local function strip(e) return (string.gsub(tostring(e),'^[^:]*canon%.lua:%d+: ','')) end
local function q(s) return string.format('%q',string.sub(tostring(s),1,200)) end

local function compare(name,lf,cf,text,arg)
  local okL,vL=pcall(lf,text,arg)
  local okC,vC=pcall(cf,text,arg)
  if okL~=okC then
    error(name..' accept differs: lua='..tostring(okL)..' '..(okL and '' or q(vL))..' c='..tostring(okC)..' '..
      (okC and '' or q(vC))..' input='..q(text),0)
  end
  if not okL then
    if vL~=vC then error(name..' error text differs: lua='..q(vL)..' c='..q(vC)..' input='..q(text),0) end
    return
  end
  if not same(vL,vC) then error(name..' value differs input='..q(text),0) end
  local eL,tL=pcall(canon.lua_encode,vL)
  local eC,tC=pcall(C.encode,vL)
  if eL~=eC or (eL and tL~=tC) or (not eL and strip(tL)~=strip(tC)) then
    error(name..' encode differs: lua='..q(tL)..' c='..q(tC)..' input='..q(text),0)
  end
end

return function(text)
  compare('decode',canon.lua_decode,C.decode,text)
  compare('decode_keys',canon.lua_decode_keys,C.decode_keys,text,KEYS)
end
