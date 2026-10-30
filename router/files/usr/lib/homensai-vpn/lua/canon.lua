-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- canon.lua: canonical JSON and SHA-256 of the Lua core, byte-identical to Python
--   native_switch.digest(v)   = sha256(json.dumps(v, sort_keys=True, separators=(',',':')))
--   native_history.encoded(v) = json.dumps(v, sort_keys=True, separators=(',',':'), allow_nan=False)
-- lua-cjson / luci.jsonc cannot reproduce that text (they escape '/', print 14 digits, cannot tell 5 from
-- 5.0 and do not sort keys), so encoding and decoding are done here, the way Python does them:
--   * Python int  <-> plain Lua number with an integral value (|n| <= 2^53; larger ints are refused);
--   * Python float <-> canon.float(x) box (decode always boxes floats); a plain non-integral number is
--     also written as a float; floats are written as repr(float): the shortest round-trip digits;
--   * None <-> canon.null; lists/dicts carry canon.array/canon.object metatables; an unmarked empty
--     table is refused (it could be either);
--   * strings are UTF-8; a lone surrogate from a backslash-u-D800 escape is kept as WTF-8, as Python keeps it;
--   * output is ensure_ascii=True with sorted keys and no spaces; NaN/Infinity are refused both ways;
--   * input rules of agent.read_json: strict UTF-8, no BOM, no duplicate keys, no NaN/Infinity,
--     nesting depth <= 64.
-- SHA-256 has one implementation per device, chosen once: nixio.crypto when it passes a known-answer
-- test, otherwise busybox `sha256sum` reading a pipe (constant command, output into our own RAM file).
local M={}

local NULL=setmetatable({},{__tostring=function() return 'null' end})
local ARRAY={__name='canon.array'}
local OBJECT={__name='canon.object'}
local FLOAT={__name='canon.float'}
M.null=NULL
function M.array(t) return setmetatable(t or {},ARRAY) end
function M.object(t) return setmetatable(t or {},OBJECT) end
function M.float(x)
  if type(x)~='number' then error('canon.float needs a number',2) end
  return setmetatable({value=x},FLOAT)
end
function M.is_float(v) return type(v)=='table' and getmetatable(v)==FLOAT end
function M.is_array(v) return type(v)=='table' and getmetatable(v)==ARRAY end
function M.is_object(v) return type(v)=='table' and getmetatable(v)==OBJECT end
-- Numeric value of a Python int or float; nil for anything else (bool is not a number, as in Python checks).
function M.number(v)
  if type(v)=='number' then return v end
  if M.is_float(v) then return v.value end
  return nil
end

local TWO53=9007199254740992

------------------------------------------------------------------------------------------------------
-- repr(float)
------------------------------------------------------------------------------------------------------
local function scientific(x,p)  -- correctly rounded p significant digits of x>0: digits, exponent
  local s=string.format('%.'..(p-1)..'e',x)
  local lead,frac,exp=string.match(s,'^(%d)%.?(%d*)e([-+]%d+)$')
  return lead..frac,tonumber(exp)
end
local function value_of(digits,exp)
  return tonumber(string.sub(digits,1,1)..'.'..string.sub(digits,2)..'e'..exp)
end
local function step(digits,exp,direction)  -- the adjacent decimal with the same number of digits
  local p=#digits;local bytes={string.byte(digits,1,p)}
  if direction>0 then
    local i=p
    while i>=1 and bytes[i]==57 do bytes[i]=48;i=i-1 end
    if i==0 then return '1'..string.rep('0',p-1),exp+1 end
    bytes[i]=bytes[i]+1
  else
    if string.find(digits,'^10*$') then return string.rep('9',p),exp-1 end
    local i=p
    while bytes[i]==48 do bytes[i]=57;i=i-1 end
    bytes[i]=bytes[i]-1
  end
  return string.char(unpack(bytes)),exp
end
local function shortest(x)
  for p=1,17 do
    local digits,exp=scientific(x,p)
    local near=value_of(digits,exp)
    if near==x then return digits,exp end
    -- Next to a power of two the round-trip interval is asymmetric: the correctly rounded p digits can
    -- miss it while the neighbour on the other side of x is inside (dtoa's shortest output then).
    local other,oexp=step(digits,exp,near<x and 1 or -1)
    if value_of(other,oexp)==x then return other,oexp end
  end
  error('canon: no round-trip digits')
end
function M.repr_float(x)
  if x~=x or x==math.huge or x==-math.huge then error('canon: float is not finite') end
  if x==0 then return (1/x<0) and '-0.0' or '0.0' end
  local sign='';if x<0 then sign='-';x=-x end
  local digits,exp=shortest(x)
  digits=string.gsub(digits,'0+$','');if digits=='' then digits='0' end
  local point=exp+1  -- Python format_float_short: exponent form when decpt <= -4 or decpt > 16
  if point>-4 and point<=16 then
    if point<=0 then return sign..'0.'..string.rep('0',-point)..digits end
    if point>=#digits then return sign..digits..string.rep('0',point-#digits)..'.0' end
    return sign..string.sub(digits,1,point)..'.'..string.sub(digits,point+1)
  end
  local mantissa=string.sub(digits,1,1)
  if #digits>1 then mantissa=mantissa..'.'..string.sub(digits,2) end
  local e=point-1
  return sign..mantissa..'e'..(e<0 and '-' or '+')..string.format('%02d',math.abs(e))
end

------------------------------------------------------------------------------------------------------
-- UTF-8 / WTF-8
------------------------------------------------------------------------------------------------------
-- Code point at i and the next index, or nil. surrogates=true accepts ED A0..BF (WTF-8, from escapes).
local function codepoint(s,i,surrogates)
  local b=string.byte(s,i)
  if b<0x80 then return b,i+1 end
  local n,cp,lo,hi
  if b>=0xC2 and b<=0xDF then n=1;cp=b-0xC0
  elseif b>=0xE0 and b<=0xEF then n=2;cp=b-0xE0
  elseif b>=0xF0 and b<=0xF4 then n=3;cp=b-0xF0
  else return nil end
  lo,hi=0x80,0xBF
  if b==0xE0 then lo=0xA0 elseif b==0xED and not surrogates then hi=0x9F
  elseif b==0xF0 then lo=0x90 elseif b==0xF4 then hi=0x8F end
  for k=1,n do
    local c=string.byte(s,i+k)
    if not c or c<(k==1 and lo or 0x80) or c>(k==1 and hi or 0xBF) then return nil end
    cp=cp*64+(c-0x80)
  end
  return cp,i+n+1
end
M.codepoint=codepoint

local function utf8_char(cp)
  if cp<0x80 then return string.char(cp) end
  if cp<0x800 then return string.char(0xC0+math.floor(cp/64),0x80+cp%64) end
  if cp<0x10000 then return string.char(0xE0+math.floor(cp/4096),0x80+math.floor(cp/64)%64,0x80+cp%64) end
  return string.char(0xF0+math.floor(cp/262144),0x80+math.floor(cp/4096)%64,0x80+math.floor(cp/64)%64,0x80+cp%64)
end

function M.valid_utf8(s)
  if not string.find(s,'[\128-\255]') then return true end
  local i=1
  while true do
    local j=string.find(s,'[\128-\255]',i)
    if not j then return true end
    local _,nxt=codepoint(s,j,false)
    if not nxt then return false end
    i=nxt
  end
end

------------------------------------------------------------------------------------------------------
-- encode
------------------------------------------------------------------------------------------------------
local NAMED={[8]='\\b',[9]='\\t',[10]='\\n',[12]='\\f',[13]='\\r',[34]='\\"',[92]='\\\\'}
local function quote(s)
  if not string.find(s,'[^ -~]') and not string.find(s,'["\\]') then return '"'..s..'"' end
  local out,n,i,len={'"'},1,1,#s
  while i<=len do
    local j=string.find(s,'[^ -~]',i);local k=string.find(s,'["\\]',i)
    local stop=math.min(j or len+1,k or len+1)
    if stop>i then n=n+1;out[n]=string.sub(s,i,stop-1);i=stop end
    if i<=len then
      local cp,nxt=codepoint(s,i,true)
      if not cp then error('canon: string is not UTF-8') end
      local text=NAMED[cp]
      if not text then
        if cp<0x10000 then text=string.format('\\u%04x',cp)
        else
          local v=cp-0x10000
          text=string.format('\\u%04x\\u%04x',0xD800+math.floor(v/1024),0xDC00+v%1024)
        end
      end
      n=n+1;out[n]=text;i=nxt
    end
  end
  n=n+1;out[n]='"'
  return table.concat(out)
end
M.quote=quote

local function key_less(a,b)  -- code point order of Python's sort_keys (byte order of UTF-8/WTF-8)
  local n=math.min(#a,#b)
  for i=1,n do
    local x,y=string.byte(a,i),string.byte(b,i)
    if x~=y then return x<y end
  end
  return #a<#b
end

local function kind(t)
  local mt=getmetatable(t)
  if mt==ARRAY then return 'array' end
  if mt==OBJECT then return 'object' end
  if mt==FLOAT then return 'float' end
  if mt~=nil then error('canon: unsupported table') end
  local count=0
  for _ in pairs(t) do count=count+1 end
  if count==0 then error('canon: empty table without canon.array/object') end
  if count==#t then return 'array' end
  return 'object'
end

local function encode_number(x)
  if x~=x or x==math.huge or x==-math.huge then error('canon: number is not finite') end
  if x%1==0 then
    if math.abs(x)>TWO53 then error('canon: integer beyond 2^53') end
    if x==0 then return '0' end
    return string.format('%.0f',x)
  end
  return M.repr_float(x)
end
local function encode_value(v,out,depth)
  if depth>200 then error('canon: nesting too deep') end
  local t=type(v)
  if v==NULL then out[#out+1]='null'
  elseif t=='boolean' then out[#out+1]=v and 'true' or 'false'
  elseif t=='number' then out[#out+1]=encode_number(v)
  elseif t=='string' then out[#out+1]=quote(v)
  elseif t=='table' then
    local k=kind(v)
    if k=='float' then out[#out+1]=M.repr_float(v.value)
    elseif k=='array' then
      out[#out+1]='['
      for i=1,#v do
        if i>1 then out[#out+1]=',' end
        encode_value(v[i],out,depth+1)
      end
      out[#out+1]=']'
    else
      local keys={}
      for key in pairs(v) do
        if type(key)~='string' then error('canon: object key is not a string') end
        keys[#keys+1]=key
      end
      table.sort(keys,key_less)
      out[#out+1]='{'
      for i,key in ipairs(keys) do
        if i>1 then out[#out+1]=',' end
        out[#out+1]=quote(key);out[#out+1]=':'
        encode_value(v[key],out,depth+1)
      end
      out[#out+1]='}'
    end
  else
    error('canon: cannot encode '..t)
  end
end
-- json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=True, allow_nan=False)
function M.encode(value)
  local out={}
  encode_value(value,out,0)
  return table.concat(out)
end

------------------------------------------------------------------------------------------------------
-- decode
------------------------------------------------------------------------------------------------------
local ESCAPES={['"']='"',['\\']='\\',['/']='/',b='\b',f='\f',n='\n',r='\r',t='\t'}
local function fail(i,what) error('canon: '..what..' at byte '..i,0) end

local function skip(s,i) return (string.find(s,'[^ \t\n\r]',i)) or #s+1 end

local function hex4(s,i)
  local h=string.sub(s,i,i+3)
  if #h<4 or not string.find(h,'^[0-9a-fA-F]+$') then return nil end
  return tonumber(h,16)
end

local function parse_string(s,i)  -- s[i]=='"'
  local out,n={},0
  i=i+1
  while true do
    local j=string.find(s,'[%z\1-\31"\\]',i)
    if not j then fail(i,'unterminated string') end
    if j>i then n=n+1;out[n]=string.sub(s,i,j-1) end
    local c=string.sub(s,j,j)
    if c=='"' then return table.concat(out),j+1 end
    if c~='\\' then fail(j,'invalid control character') end
    local e=string.sub(s,j+1,j+1)
    if e~='u' then
      local text=ESCAPES[e]
      if not text then fail(j,'invalid escape') end
      n=n+1;out[n]=text;i=j+2
    else
      local cp=hex4(s,j+2)
      if not cp then fail(j,'invalid \\uXXXX escape') end
      i=j+6
      if cp>=0xD800 and cp<=0xDBFF and string.sub(s,i,i+1)=='\\u' then
        local low=hex4(s,i+2)
        if not low then fail(i,'invalid \\uXXXX escape') end
        if low>=0xDC00 and low<=0xDFFF then
          cp=0x10000+(cp-0xD800)*1024+(low-0xDC00);i=i+6
        end
      end
      n=n+1;out[n]=utf8_char(cp)
    end
  end
end

local function parse_number(s,i)
  local j=i
  if string.sub(s,j,j)=='-' then j=j+1 end
  local c=string.sub(s,j,j)
  if c=='0' then j=j+1
  elseif string.find(c,'^[1-9]$') then j=(string.find(s,'[^0-9]',j)) or #s+1
  else fail(i,'invalid value') end
  local float=false
  if string.sub(s,j,j)=='.' and string.find(string.sub(s,j+1,j+1),'^[0-9]$') then
    float=true;j=(string.find(s,'[^0-9]',j+1)) or #s+1
  end
  local e=string.sub(s,j,j)
  if e=='e' or e=='E' then
    local k=j+1
    local sign=string.sub(s,k,k)
    if sign=='+' or sign=='-' then k=k+1 end
    if string.find(string.sub(s,k,k),'^[0-9]$') then float=true;j=(string.find(s,'[^0-9]',k)) or #s+1 end
  end
  local raw=string.sub(s,i,j-1)
  local x=tonumber(raw)
  if float then
    if x~=x or x==math.huge or x==-math.huge then fail(i,'nonfinite number') end
    return M.float(x),j
  end
  local magnitude=string.gsub(raw,'^%-','')  -- compare the digits: tonumber() already rounded 2^53+1
  if #magnitude>16 or (#magnitude==16 and magnitude>'9007199254740992') then fail(i,'integer beyond 2^53') end
  if x==0 then x=0 end  -- Python int('-0') is 0
  return x,j
end

local parse_value
parse_value=function(s,i,depth)
  if depth>64 then fail(i,'nesting limit') end
  i=skip(s,i)
  local c=string.sub(s,i,i)
  if c=='{' then
    local obj={}
    i=skip(s,i+1)
    if string.sub(s,i,i)=='}' then return M.object(obj),i+1 end
    while true do
      if string.sub(s,i,i)~='"' then fail(i,'expected property name') end
      local key;key,i=parse_string(s,i)
      i=skip(s,i)
      if string.sub(s,i,i)~=':' then fail(i,'expected colon') end
      if obj[key]~=nil then fail(i,'duplicate field') end
      local value;value,i=parse_value(s,i+1,depth+1)
      obj[key]=value
      i=skip(s,i)
      local d=string.sub(s,i,i)
      if d=='}' then return M.object(obj),i+1 end
      if d~=',' then fail(i,'expected , or }') end
      i=skip(s,i+1)
    end
  elseif c=='[' then
    local arr,n={},0
    i=skip(s,i+1)
    if string.sub(s,i,i)==']' then return M.array(arr),i+1 end
    while true do
      local value;value,i=parse_value(s,i,depth+1)
      n=n+1;arr[n]=value
      i=skip(s,i)
      local d=string.sub(s,i,i)
      if d==']' then return M.array(arr),i+1 end
      if d~=',' then fail(i,'expected , or ]') end
      i=i+1
    end
  elseif c=='"' then return parse_string(s,i)
  elseif string.sub(s,i,i+3)=='null' then return NULL,i+4
  elseif string.sub(s,i,i+3)=='true' then return true,i+4
  elseif string.sub(s,i,i+4)=='false' then return false,i+5
  end
  return parse_number(s,i)
end

-- agent.read_json() of the file text (json.loads with its hooks); errors are raised as strings.
function M.decode(text)
  if type(text)~='string' then error('canon: text expected',0) end
  if string.sub(text,1,3)=='\239\187\191' then fail(1,'unexpected UTF-8 BOM') end
  if not M.valid_utf8(text) then fail(1,'invalid UTF-8') end
  local value,i=parse_value(text,1,0)
  i=skip(text,i)
  if i<=#text then fail(i,'extra data') end
  return value
end

------------------------------------------------------------------------------------------------------
-- SHA-256
------------------------------------------------------------------------------------------------------
M.RUNTIME='/var/run/homensai-vpn'
-- Directories that may appear inside a constant command line: absolute, plain characters, no '..'.
function M.safe_directory(path)
  return type(path)=='string' and string.find(path,'^/[A-Za-z0-9_./-]+$')~=nil and not string.find(path,'..',1,true)
end
function M.configure(options)
  if options.runtime~=nil then
    if not M.safe_directory(options.runtime) then error('canon: unsafe runtime directory',2) end
    M.RUNTIME=options.runtime
  end
end

local KNOWN_INPUT,KNOWN_DIGEST='abc','ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
local function tohex(raw) return (string.gsub(raw,'.',function(c) return string.format('%02x',string.byte(c)) end)) end

local function nixio_sha256()
  local ok,crypto=pcall(require,'nixio.crypto')
  if not ok or type(crypto)~='table' or type(crypto.hash)~='function' then return nil end
  local function run(text)
    local h=crypto.hash('sha256')
    if not h then return nil end
    h:update(text)
    local hex,raw=h:final()
    if type(hex)=='string' and #hex==64 then return string.lower(hex) end
    if type(raw)=='string' and #raw==32 then return tohex(raw) end
    return nil
  end
  local ok2,value=pcall(run,KNOWN_INPUT)
  if ok2 and value==KNOWN_DIGEST then return run end  -- never trust an algorithm name we have not checked
  return nil
end

local sequence=0
function M.unique()  -- [0-9a-f-] only: safe inside a constant command line
  sequence=sequence+1
  local f=io.open('/proc/sys/kernel/random/uuid','r')
  local id=f and f:read('*l') or string.format('%x',os.time())
  if f then f:close() end
  return (string.gsub(id,'[^0-9a-f]',''))..'-'..sequence
end

-- busybox sha256sum: the text goes through the pipe, never through the command line.
local function pipe_sha256(text)
  local path=M.RUNTIME..'/.canon-'..M.unique()..'.sha256'
  local p=io.popen('sha256sum >'..path..' 2>/dev/null','w')
  if not p then error('canon: SHA256-UNAVAILABLE',0) end
  p:write(text);p:close()
  local f=io.open(path,'r');local out=f and f:read('*a') or '';if f then f:close() end
  os.remove(path)
  local digest=string.match(out,'^([0-9a-f]+)%s')
  if not digest or #digest~=64 then error('canon: SHA256-UNAVAILABLE',0) end
  return digest
end

local provider,provider_name
function M.sha256(text)
  if not provider then
    provider=nixio_sha256()
    provider_name=provider and 'nixio.crypto' or 'sha256sum'
    provider=provider or pipe_sha256
  end
  return provider(text)
end
function M.sha256_backend() M.sha256('');return provider_name end
-- Tests and the dry run may pin a provider (e.g. Python's hashlib result checked separately).
function M.set_sha256(fn,name) provider,provider_name=fn,name or 'custom' end

-- native_switch.digest(value)
function M.digest(value) return M.sha256(M.encode(value)) end

return M
