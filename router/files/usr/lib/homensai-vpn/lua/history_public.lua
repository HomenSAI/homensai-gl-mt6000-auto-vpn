-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- history_public.lua: the page's switch-history projection (monitor_status.history_public) built in a child
-- process, so the monitor's event loop never decodes the ~1 MB history file itself (MT3000, alpha19).
--   lua history_public.lua <persist> <runtime> <days> <now> <out>
-- writes <out> atomically as a Lua table constructor (dump below); the monitor reads it with load(): the C lexer
-- instead of the Lua JSON parser. Exit 0 only when <out> holds a projection.
local script=(...)~='history_public'
if script then
  local here=arg and arg[0] and string.match(arg[0],'^(.*)/[^/]*$') or '.'
  package.path=here..'/?.lua;'..package.path
end
local canon=require('canon')
local M={}
local NULL=canon.null

-- dump(value): Lua source that load() turns back into the same canon value (objects, arrays, floats, null,
-- plain tables, strings, integers, booleans). canon.encode of the result is byte-identical.
local function number(x)
  if x~=x or x==math.huge or x==-math.huge then error('history_public: number is not finite') end
  return string.format('%.17g',x)
end
local function dump_value(v,out,depth)
  if depth>200 then error('history_public: nesting too deep') end
  local t=type(v)
  if v==NULL then out[#out+1]='N'
  elseif t=='string' then out[#out+1]=string.format('%q',v)
  elseif t=='number' then out[#out+1]=number(v)
  elseif t=='boolean' then out[#out+1]=v and 'true' or 'false'
  elseif t=='table' then
    local wrap
    if canon.is_float(v) then out[#out+1]='F('..number(v.value)..')';return
    elseif canon.is_array(v) then wrap='A'
    elseif canon.is_object(v) then wrap='O'
    elseif getmetatable(v)==nil then wrap='P'
    else error('history_public: unsupported table') end
    out[#out+1]=wrap..'{'
    local n=#v
    for i=1,n do dump_value(v[i],out,depth+1);out[#out+1]=',' end
    for k,item in pairs(v) do
      if not (type(k)=='number' and k>=1 and k<=n and k%1==0) then
        if type(k)~='string' then error('history_public: key is not a string') end
        out[#out+1]='['..string.format('%q',k)..']='
        dump_value(item,out,depth+1);out[#out+1]=','
      end
    end
    out[#out+1]='}'
  else error('history_public: cannot dump '..t) end
end
function M.dump(value)
  local out={'return '}
  dump_value(value,out,0)
  return table.concat(out)
end

-- load(text): the value dump() wrote; the chunk sees only the four constructors (no globals).
function M.load(text)
  local chunk,err=loadstring(text,'=history_public')
  if not chunk then error(err,0) end
  setfenv(chunk,{N=NULL,F=canon.float,A=canon.array,O=canon.object,P=function(t) return t end})
  return chunk()
end

function M.main(argv)
  local persist,runtime,days,now,out=argv[1],argv[2],tonumber(argv[3]),tonumber(argv[4]),argv[5]
  if not (persist and runtime and days and now and out) then return 2 end
  local mio=require('monitor_io')
  local page=require('monitor_status')
  local env=page.env(mio,runtime,persist)
  local value=page.history_public(env,days,now)
  if not canon.is_object(value) or value.error~=nil then return 1 end
  mio.write_atomic(out,M.dump(value))
  return 0
end

if script then
  local ok,code=pcall(M.main,arg)
  os.exit(ok and code or 1)
end

return M
