-- TEST STUB of lua-core canon.lua (feat/lua-core-20261030). Used only when the real module is not on the path.
-- Same API, minimal implementation: canonical JSON (sorted keys, ',' ':' separators, ensure_ascii), repr(float)
-- by the shortest round-trip %.Ng, a small JSON decoder with tagged tables, sha256 through `sha256sum`.
local M={}
local NULL=setmetatable({},{__tostring=function() return 'null' end})
local ARRAY={__name='canon.array'};local OBJECT={__name='canon.object'};local FLOAT={__name='canon.float'}
M.null=NULL
function M.array(t) return setmetatable(t or {},ARRAY) end
function M.object(t) return setmetatable(t or {},OBJECT) end
function M.float(x) return setmetatable({value=x},FLOAT) end
function M.is_float(v) return type(v)=='table' and getmetatable(v)==FLOAT end
function M.is_array(v) return type(v)=='table' and getmetatable(v)==ARRAY end
function M.is_object(v) return type(v)=='table' and getmetatable(v)==OBJECT end
function M.number(v) if type(v)=='number' then return v end;if M.is_float(v) then return v.value end;return nil end

function M.repr_float(x)
  if x~=x or x==math.huge or x==-math.huge then error('canon: float is not finite') end
  if x==0 then return (1/x<0) and '-0.0' or '0.0' end
  local s
  for p=1,17 do s=string.format('%.'..p..'g',x);if tonumber(s)==x then break end end
  local mant,exp=string.match(s,'^(-?[%d.]+)e([-+]%d+)$')
  if mant then
    local e=tonumber(exp)
    if e>=-4 and e<16 then  -- Python prints positional for these; rebuild from %.17f-style digits
      local digits=string.gsub(mant,'[-.]','')
      local sign=string.sub(mant,1,1)=='-' and '-' or ''
      local point=e+1
      if point<=0 then return sign..'0.'..string.rep('0',-point)..digits end
      if point>=#digits then return sign..digits..string.rep('0',point-#digits)..'.0' end
      return sign..string.sub(digits,1,point)..'.'..string.sub(digits,point+1)
    end
    return mant..'e'..(e<0 and '-' or '+')..string.format('%02d',math.abs(e))
  end
  if not string.find(s,'%.') then s=s..'.0' end
  return s
end

local function quote(s)
  s=string.gsub(s,'[%c"\\\128-\255]',function(c)
    local b=string.byte(c)
    if c=='"' then return '\\"' elseif c=='\\' then return '\\\\' elseif c=='\n' then return '\\n' elseif c=='\r' then return '\\r'
    elseif c=='\t' then return '\\t' elseif c=='\b' then return '\\b' elseif c=='\f' then return '\\f' end
    if b<0x80 then return string.format('\\u%04x',b) end
    return c  -- multi-byte handled below
  end)
  -- UTF-8 -> \uXXXX (BMP) / surrogate pair
  s=string.gsub(s,'[\194-\244][\128-\191]*',function(seq)
    local b=string.byte(seq,1);local cp,n
    if b>=0xF0 then cp=b-0xF0;n=3 elseif b>=0xE0 then cp=b-0xE0;n=2 else cp=b-0xC0;n=1 end
    for i=2,n+1 do cp=cp*64+(string.byte(seq,i)-0x80) end
    if cp<0x10000 then return string.format('\\u%04x',cp) end
    local v=cp-0x10000
    return string.format('\\u%04x\\u%04x',0xD800+math.floor(v/1024),0xDC00+v%1024)
  end)
  return '"'..s..'"'
end
M.quote=quote

local function encode_value(v,out)
  local t=type(v)
  if v==NULL then out[#out+1]='null'
  elseif t=='boolean' then out[#out+1]=v and 'true' or 'false'
  elseif t=='number' then
    if v%1==0 and math.abs(v)<=2^53 then out[#out+1]=(v==0) and '0' or string.format('%.0f',v) else out[#out+1]=M.repr_float(v) end
  elseif t=='string' then out[#out+1]=quote(v)
  elseif t=='table' then
    if M.is_float(v) then out[#out+1]=M.repr_float(v.value)
    elseif M.is_array(v) or (not M.is_object(v) and #v>0) then
      out[#out+1]='[';for i=1,#v do if i>1 then out[#out+1]=',' end;encode_value(v[i],out) end;out[#out+1]=']'
    else
      if not M.is_object(v) and next(v)==nil then error('canon: empty table without canon.array/object') end
      local keys={};for k in pairs(v) do keys[#keys+1]=k end;table.sort(keys)
      out[#out+1]='{'
      for i,k in ipairs(keys) do if i>1 then out[#out+1]=',' end;out[#out+1]=quote(k);out[#out+1]=':';encode_value(v[k],out) end
      out[#out+1]='}'
    end
  else error('canon: cannot encode '..t) end
end
function M.encode(value) local out={};encode_value(value,out);return table.concat(out) end

local function utf8_char(cp)
  if cp<0x80 then return string.char(cp) end
  if cp<0x800 then return string.char(0xC0+math.floor(cp/64),0x80+cp%64) end
  if cp<0x10000 then return string.char(0xE0+math.floor(cp/4096),0x80+math.floor(cp/64)%64,0x80+cp%64) end
  return string.char(0xF0+math.floor(cp/262144),0x80+math.floor(cp/4096)%64,0x80+math.floor(cp/64)%64,0x80+cp%64)
end
local function skip(s,i) return (string.find(s,'[^ \t\n\r]',i)) or #s+1 end
local parse
local function parse_string(s,i)
  local out={};i=i+1
  while true do
    local j=string.find(s,'["\\]',i)
    if not j then error('canon: unterminated string',0) end
    out[#out+1]=string.sub(s,i,j-1)
    if string.sub(s,j,j)=='"' then return table.concat(out),j+1 end
    local e=string.sub(s,j+1,j+1)
    local map={['"']='"',['\\']='\\',['/']='/',b='\b',f='\f',n='\n',r='\r',t='\t'}
    if e=='u' then
      local cp=tonumber(string.sub(s,j+2,j+5),16);i=j+6
      if cp>=0xD800 and cp<=0xDBFF and string.sub(s,i,i+1)=='\\u' then
        local low=tonumber(string.sub(s,i+2,i+5),16)
        if low and low>=0xDC00 and low<=0xDFFF then cp=0x10000+(cp-0xD800)*1024+(low-0xDC00);i=i+6 end
      end
      out[#out+1]=utf8_char(cp)
    else out[#out+1]=map[e] or error('canon: invalid escape',0);i=j+2 end
  end
end
parse=function(s,i)
  i=skip(s,i)
  local c=string.sub(s,i,i)
  if c=='{' then
    local obj=M.object({});i=skip(s,i+1)
    if string.sub(s,i,i)=='}' then return obj,i+1 end
    while true do
      local key;key,i=parse_string(s,i);i=skip(s,i)
      if string.sub(s,i,i)~=':' then error('canon: expected colon',0) end
      local value;value,i=parse(s,i+1)
      if obj[key]~=nil then error('canon: duplicate field',0) end
      obj[key]=value;i=skip(s,i)
      local d=string.sub(s,i,i)
      if d=='}' then return obj,i+1 end
      if d~=',' then error('canon: expected , or }',0) end
      i=skip(s,i+1)
    end
  elseif c=='[' then
    local arr=M.array({});i=skip(s,i+1)
    if string.sub(s,i,i)==']' then return arr,i+1 end
    while true do
      local value;value,i=parse(s,i);arr[#arr+1]=value;i=skip(s,i)
      local d=string.sub(s,i,i)
      if d==']' then return arr,i+1 end
      if d~=',' then error('canon: expected , or ]',0) end
      i=i+1
    end
  elseif c=='"' then return parse_string(s,i)
  elseif string.sub(s,i,i+3)=='null' then return NULL,i+4
  elseif string.sub(s,i,i+3)=='true' then return true,i+4
  elseif string.sub(s,i,i+4)=='false' then return false,i+5
  end
  local raw=string.match(s,'^-?%d+%.?%d*[eE]?[-+]?%d*',i)
  if not raw or raw=='' then error('canon: invalid value at '..i,0) end
  local x=tonumber(raw)
  if x==nil then error('canon: invalid number',0) end
  if string.find(raw,'[.eE]') then return M.float(x),i+#raw end
  return x,i+#raw
end
function M.decode(text)
  if type(text)~='string' then error('canon: text expected',0) end
  local value,i=parse(text,1)
  if skip(text,i)<=#text then error('canon: extra data',0) end
  return value
end

M.RUNTIME=os.getenv('TMPDIR') or '/tmp'
function M.safe_directory(path) return type(path)=='string' and string.find(path,'^/[A-Za-z0-9_./-]+$')~=nil and not string.find(path,'..',1,true) end
function M.configure(options) if options.runtime then M.RUNTIME=options.runtime end end
local sequence=0
function M.unique() sequence=sequence+1;return string.format('%x-%d',os.time(),sequence) end
local provider=nil
function M.sha256(text)
  if provider then return provider(text) end
  local path=M.RUNTIME..'/.canon-stub-'..M.unique()..'.sha256'
  local p=assert(io.popen('sha256sum >'..path,'w'));p:write(text);p:close()
  local f=assert(io.open(path,'r'));local out=f:read('*a');f:close();os.remove(path)
  return string.match(out,'^([0-9a-f]+)')
end
function M.set_sha256(fn) provider=fn end
function M.sha256_backend() return 'sha256sum (stub)' end
function M.digest(value) return M.sha256(M.encode(value)) end
return M
