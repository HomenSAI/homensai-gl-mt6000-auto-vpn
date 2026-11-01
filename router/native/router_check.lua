-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- router_check.lua: read-only check of canon_c on a router (not shipped). Run from a kit directory holding canon.lua,
-- canon_c.so and this file:   LUA_PATH='<kit>/?.lua;;' LUA_CPATH='<kit>/?.so' lua <kit>/router_check.lua [reps]
-- Reads /etc/homensai-vpn/native-history.json and /var/run/homensai-vpn/status.json (never writes them), compares
-- canon_c with canon.lua's Lua code on them and prints the timings (os.clock: CPU seconds of this process).
local canon=require('canon')
local reps=tonumber(arg and arg[1]) or 3
local NULL=canon.null
local out={}
local function say(k,v) out[#out+1]=k..'='..tostring(v) end

local ok,err=pcall(require,'canon_c')
say('canon_c_require',ok and 'ok' or string.gsub(tostring(err),'%s+',' '))
local C=canon.c_module
say('canon_c_in_use',C~=nil)
if not C then print(table.concat(out,'\n'));os.exit(1) end

local function same(a,b)
  if a==NULL or b==NULL then return a==b end
  if type(a)~=type(b) then return false end
  if type(a)=='number' then return a==b and (a~=0 or 1/a==1/b) end
  if type(a)~='table' then return a==b end
  if getmetatable(a)~=getmetatable(b) then return false end
  local ka,kb={},{}
  for k in pairs(a) do ka[#ka+1]=k end
  for k in pairs(b) do kb[#kb+1]=k end
  if #ka~=#kb then return false end
  for i=1,#ka do if ka[i]~=kb[i] or not same(a[ka[i]],b[kb[i]]) then return false end end
  return true
end
local function best_ms(fn)
  local best=math.huge
  for _=1,reps do local a=os.clock();fn();best=math.min(best,os.clock()-a) end
  return string.format('%.1f',best*1000)
end
local function read(path)
  local f=io.open(path,'rb')
  if not f then return nil end
  local text=f:read('*a');f:close()
  return text
end
local function shell_sha(path)
  local p=io.popen('sha256sum '..path..' 2>/dev/null')
  local line=p and p:read('*l') or '';if p then p:close() end
  return string.match(line or '','^(%x+)')
end

local failed=false
for _,item in ipairs({{'history','/etc/homensai-vpn/native-history.json'},{'status','/var/run/homensai-vpn/status.json'}}) do
  local name,path=item[1],item[2]
  local text=read(path)
  if not text then say(name,'absent')
  else
    say(name..'_bytes',#text)
    local lok,lv=pcall(canon.lua_decode,text)
    local cok,cv=pcall(C.decode,text)
    local agree=lok==cok and (lok and same(lv,cv) or (not lok and lv==cv))
    say(name..'_decode_same',agree);failed=failed or not agree
    if lok and cok then
      local lt=canon.lua_encode(lv)
      local ct=C.encode(lv)
      say(name..'_encode_same',lt==ct);failed=failed or lt~=ct
      say(name..'_reencode_equals_file',lt==text)
      local keys={}
      local n=0
      for k in pairs(lv) do n=n+1;if n%2==1 then keys[k]=true end end
      local kok,kv=pcall(canon.lua_decode_keys,text,keys)
      local cok2,ckv=pcall(C.decode_keys,text,keys)
      local kagree=kok==cok2 and (not kok or same(kv,ckv))
      say(name..'_decode_keys_same',kagree);failed=failed or not kagree
      local digest=shell_sha(path)
      say(name..'_sha256_same',digest==C.sha256(text));failed=failed or digest~=C.sha256(text)
      say(name..'_lua_decode_ms',best_ms(function() canon.lua_decode(text) end))
      say(name..'_c_decode_ms',best_ms(function() C.decode(text) end))
      say(name..'_lua_encode_ms',best_ms(function() canon.lua_encode(lv) end))
      say(name..'_c_encode_ms',best_ms(function() C.encode(lv) end))
      say(name..'_lua_decode_keys_ms',best_ms(function() canon.lua_decode_keys(text,keys) end))
      say(name..'_c_decode_keys_ms',best_ms(function() C.decode_keys(text,keys) end))
      say(name..'_c_sha256_ms',best_ms(function() C.sha256(text) end))
      local a=os.time();for _=1,reps do shell_sha(path) end
      say(name..'_sha256sum_process_wall_s_total',os.time()-a)
    else
      say(name..'_decode_error',string.sub(tostring(lv),1,120))
    end
  end
end
say('result',failed and 'MISMATCH' or 'OK')
print(table.concat(out,'\n'))
os.exit(failed and 1 or 0)
