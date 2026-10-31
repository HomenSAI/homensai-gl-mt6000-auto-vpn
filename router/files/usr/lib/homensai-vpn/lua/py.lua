-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- py.lua: the few Python value semantics the backend port needs over canon values (2.0.0-lua line).
--   isnone(v)        v is None (missing key or JSON null)
--   truthy(v)        bool(v): None/False/0/0.0/''/[]/{} are false
--   eq(a,b)          a == b: 1 == 1.0, list == list element-wise, dict == dict by keys (None kept distinct
--                    from a missing key, as in Python); bool and number are never equal here (Python would say
--                    True == 1: no value the backend compares mixes them)
--   str(v)           str(v) for None/bool/int/str (floats as repr)
--   int(v)           int(v) for an int or a decimal string (whitespace and one sign allowed); nil otherwise
--   is_int(v)        type(v) is int
--   copy(v)          copy.deepcopy with the canon metatables kept
--   list/object      canon.array/canon.object constructors
local canon=require('canon')

local M={}
local NULL=canon.null
M.NULL=NULL

function M.isnone(v) return v==nil or v==NULL end

function M.is_int(v) return type(v)=='number' and v%1==0 and v==v and v~=math.huge and v~=-math.huge end
function M.is_number(v) return canon.number(v)~=nil end
function M.finite(v)
  local x=canon.number(v)
  return x~=nil and x==x and x~=math.huge and x~=-math.huge
end

function M.truthy(v)
  if v==nil or v==NULL or v==false then return false end
  if type(v)=='number' then return v~=0 end
  if canon.is_float(v) then return v.value~=0 end
  if type(v)=='string' then return v~='' end
  if type(v)=='table' then return next(v)~=nil end
  return true
end

local function is_list(v) return type(v)=='table' and (canon.is_array(v) or (getmetatable(v)==nil and (next(v)==nil or #v>0))) end
local function is_dict(v) return type(v)=='table' and (canon.is_object(v) or (getmetatable(v)==nil and next(v)~=nil and #v==0)) end
M.is_list=function(v) return canon.is_array(v) end
M.is_dict=function(v) return canon.is_object(v) end

function M.eq(a,b)
  if M.isnone(a) or M.isnone(b) then return M.isnone(a) and M.isnone(b) end
  local ta,tb=type(a),type(b)
  if ta=='boolean' or tb=='boolean' then return a==b end
  local na,nb=canon.number(a),canon.number(b)
  if na~=nil or nb~=nil then return na~=nil and nb~=nil and na==nb end
  if ta~=tb then return false end
  if ta~='table' then return a==b end
  if is_list(a) and is_list(b) and not (canon.is_object(a) or canon.is_object(b)) then
    if #a~=#b then return false end
    for i=1,#a do if not M.eq(a[i],b[i]) then return false end end
    return true
  end
  if canon.is_array(a) or canon.is_array(b) then return false end
  for k,v in pairs(a) do if b[k]==nil or not M.eq(v,b[k]) then return false end end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end

function M.str(v)
  if M.isnone(v) then return 'None' end
  if v==true then return 'True' end
  if v==false then return 'False' end
  if type(v)=='number' then
    if v%1==0 and math.abs(v)<=2^53 then return string.format('%.0f',v) end
    return canon.repr_float(v)
  end
  if canon.is_float(v) then return canon.repr_float(v.value) end
  if type(v)=='string' then return v end
  return tostring(v)
end

-- int(x): Python int() of an int or of a str (surrounding whitespace, one sign, ASCII digits, '_' between digits).
function M.int(v)
  if type(v)=='number' then if v%1==0 then return v end;return v<0 and -math.floor(-v) or math.floor(v) end
  if canon.is_float(v) then local x=v.value;return x<0 and -math.floor(-x) or math.floor(x) end
  if type(v)~='string' then return nil end
  local s=string.match(v,'^[ \t\n\r\f\v]*(.-)[ \t\n\r\f\v]*$')
  local sign,digits=string.match(s,'^([+-]?)([0-9][0-9_]*)$')
  if not digits or string.find(digits,'__',1,true) or string.sub(digits,-1)=='_' then return nil end
  digits=string.gsub(digits,'_','')
  if #digits>15 then return nil end
  local x=tonumber(digits)
  return sign=='-' and -x or x
end

-- int(text, 0): base from the prefix (0x/0o/0b), no leading zeros on a decimal.
function M.int_auto(v)
  if type(v)~='string' then return nil end
  local s=string.match(v,'^%s*(.-)%s*$')
  local sign,rest=string.match(s,'^([+-]?)(.*)$')
  local x
  if string.find(rest,'^0[xX][0-9a-fA-F]+$') then if #rest>15 then return nil end;x=tonumber(string.sub(rest,3),16)
  elseif string.find(rest,'^0[oO][0-7]+$') then x=tonumber(string.sub(rest,3),8)
  elseif string.find(rest,'^0[bB][01]+$') then x=tonumber(string.sub(rest,3),2)
  elseif string.find(rest,'^[1-9][0-9]*$') then if #rest>15 then return nil end;x=tonumber(rest)
  elseif string.find(rest,'^0+$') then x=0
  else return nil end
  return sign=='-' and -x or x
end

function M.copy(v)
  if type(v)~='table' or v==NULL then return v end
  if canon.is_float(v) then return canon.float(v.value) end
  local out={}
  for k,x in pairs(v) do out[k]=M.copy(x) end
  return setmetatable(out,getmetatable(v))
end

function M.list(t) return canon.array(t or {}) end
function M.object(t) return canon.object(t or {}) end

-- list(dict.fromkeys(values)): first occurrence order, duplicates dropped
function M.unique(values)
  local seen,out={},{}
  for _,x in ipairs(values) do if not seen[x] then seen[x]=true;out[#out+1]=x end end
  return out
end

function M.contains(list,x)
  if type(list)~='table' then return false end
  for i=1,#list do if M.eq(list[i],x) then return true end end
  return false
end

-- text[:n] in code points (UTF-8 text)
function M.prefix(text,n)
  local count,i=0,1
  while i<=#text do
    if count==n then return string.sub(text,1,i-1) end
    local b=string.byte(text,i)
    i=i+((b<0x80 and 1) or (b<0xE0 and 2) or (b<0xF0 and 3) or 4)
    count=count+1
  end
  return text
end

return M
