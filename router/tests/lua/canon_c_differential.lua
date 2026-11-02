-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- canon_c_differential.lua: canon_c (router/native/canon_c.c) against canon.lua's own Lua code.
--   lua canon_c_differential.lua fuzz <cases> [seed]   encode/decode/decode_keys/sha256 differential fuzz
--   lua canon_c_differential.lua bench [reps]          ~1 MB native-history document: Lua vs C timings
--   lua canon_c_differential.lua off                   HOMENSAI_CANON_C=0: the module must stay unused
-- LUA_CPATH must reach canon_c.so (router/native/build.sh). Prints one JSON-like summary line per mode.
local here=(arg and arg[0] and string.match(arg[0],'^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local canon=require('canon')
local NULL=canon.null
local mode=arg[1] or 'fuzz'

if mode=='off' then
  if canon.c_module~=nil then io.stderr:write('canon_c used with HOMENSAI_CANON_C=0\n');os.exit(1) end
  if canon.encode~=canon.lua_encode or canon.decode~=canon.lua_decode then os.exit(1) end
  print('off: lua only, ok');os.exit(0)
end
local C=canon.c_module
if not C then io.stderr:write('canon_c not loaded (LUA_CPATH='..tostring(os.getenv('LUA_CPATH'))..')\n');os.exit(1) end
if canon.encode~=C.encode or canon.decode~=C.decode or canon.decode_keys~=C.decode_keys then os.exit(1) end
local L_encode,L_decode,L_keys=canon.lua_encode,canon.lua_decode,canon.lua_decode_keys

-- Park-Miller: exact in doubles (and in LNUM integers), the same sequence on every Lua.
local seed=tonumber(arg[3]) or 20261031
local function rnd(n) seed=(seed*16807)%2147483647;return seed%n end
local function pick(t) return t[rnd(#t)+1] end

------------------------------------------------------------------------------------------------------
-- deep comparison: types, markers, numbers (sign of zero), strings, and the same next() order
------------------------------------------------------------------------------------------------------
local function same(a,b)
  if a==NULL or b==NULL then return a==b end
  local ta,tb=type(a),type(b)
  if ta~=tb then return false end
  if ta=='number' then
    if a~=a then return b~=b end
    return a==b and (a~=0 or 1/a==1/b)
  end
  if ta~='table' then return a==b end
  if getmetatable(a)~=getmetatable(b) then return false end
  local ka,kb={},{}
  for k in pairs(a) do ka[#ka+1]=k end
  for k in pairs(b) do kb[#kb+1]=k end
  if #ka~=#kb then return false end
  for i=1,#ka do
    if ka[i]~=kb[i] then return false end
    if not same(a[ka[i]],b[kb[i]]) then return false end
  end
  return true
end

------------------------------------------------------------------------------------------------------
-- values for encode
------------------------------------------------------------------------------------------------------
local FLOATS={0.1,0.2,0.3,1/3,2/3,1e16,1e17,1e15,123456789012345680,1e-4,1e-5,0.001,1e22,1e23,5e-324,2.2250738585072014e-308,
  1.7976931348623157e308,2^-1074,2^-1022,2^52+0.5,2^53,2^63,4.35,0.07,9.999999999999999e22,1.5,-1.5,100.25,3.14159,
  2.5e-7,7e-10,1e300,1.2345678901234567e-300,0.5,0.25,-0.0,0.0,1.0,2^60,1e21,1e-7,123.456,9007199254740993}
local INTS={0,1,-1,2,10,255,65535,2147483647,2147483648,-2147483648,-2147483649,4294967296,1e15,1e16,
  9007199254740991,9007199254740992,-9007199254740992,9007199254740994,1761900000000,-0.0}
local function rfloat()
  local r=rnd(6)
  if r==0 then return pick(FLOATS) end
  if r==1 then return (rnd(2000000)-1000000)/(rnd(999)+1) end
  if r==2 then return math.ldexp(rnd(2^30)+rnd(2^23)/2^23,rnd(2100)-1100) end
  if r==3 then return rnd(1000000)/1000 end
  if r==4 then return -math.ldexp(rnd(2^30)+1,rnd(120)-60) end
  return (rnd(2^30)/2^30)*10^(rnd(40)-20)
end
local PIECES={'a','Z','0',' ','~','"','\\','/','\b','\f','\n','\r','\t','\0','\1','\31','\127','\194\128','\195\169',
  '\223\191','\224\160\128','\226\130\172','\237\159\191','\238\128\128','\239\191\191','\240\144\128\128',
  '\240\159\152\128','\244\143\191\191','\237\160\128','\237\175\191','\237\176\128','\237\191\191','<tag>','{"x":1}'}
local BAD={'\128','\191','\192\128','\193\191','\224\128\128','\240\128\128\128','\244\144\128\128','\245','\255','\195',
  '\226\130','\240\159\152'}
local function rstring(bad)
  local out={}
  for i=1,rnd(12) do out[i]=pick(PIECES) end
  if bad then table.insert(out,rnd(#out+1)+1,pick(BAD)) end
  return table.concat(out)
end
local KEYS={'a','b','A','_','','zz','a\0b','é','\226\130\172','key','sequence','events','\237\160\128','10','1'}
local gen
gen=function(depth,allow_bad)
  local r=rnd(depth>5 and 9 or 16)
  if r==0 then return NULL elseif r==1 then return rnd(2)==0
  elseif r==2 then return pick(INTS) elseif r==3 then return rfloat()
  elseif r==4 then return canon.float(rfloat()) elseif r==5 or r==6 then return rstring(allow_bad and rnd(25)==0)
  elseif r==7 then return rnd(100000)-50000 elseif r==8 then return 'plain'
  elseif r<=11 then
    local t={}
    for i=1,rnd(6) do t[i]=gen(depth+1,allow_bad) end
    local k=rnd(4)
    if k==0 then return canon.array(t) elseif k==1 and #t>0 then return t end
    return canon.array(t)
  else
    local t={}
    for _=1,rnd(6) do t[pick(KEYS)..(rnd(3)==0 and tostring(rnd(50)) or '')]=gen(depth+1,allow_bad) end
    if rnd(3)==0 and next(t)~=nil then return t end
    return canon.object(t)
  end
end
local function nest(n,leaf) local v=leaf;for i=1,n do v=(i%2==0) and canon.array({v}) or canon.object({k=v}) end;return v end
local function bad_value()
  local r=rnd(16)
  if r==0 then return 0/0 elseif r==1 then return 1/0 elseif r==2 then return -1/0
  elseif r==3 then return canon.float(0/0) elseif r==4 then return canon.float(1/0)
  elseif r==5 then return setmetatable({value='1.5'},getmetatable(canon.float(1))) elseif r==6 then return {}
  elseif r==7 then return canon.object({[1]='x'}) elseif r==8 then return setmetatable({1},{})
  elseif r==9 then return print elseif r==10 then return 2^53+2 elseif r==11 then return -2^60
  elseif r==12 then return {1,2,nil,4} elseif r==13 then return {[1]=1,[3]=3,x=1}
  elseif r==14 then return setmetatable({},getmetatable(canon.float(1))) end
  return rstring(true)
end

local function message(e) return (string.gsub(tostring(e),'^.-canon: ','canon: ')) end
local stats={encode=0,encode_err=0,decode=0,decode_err=0,keys=0,keys_err=0,sha=0,mismatch=0}
local failures={}
local function mismatch(kind,detail)
  stats.mismatch=stats.mismatch+1
  if #failures<20 then failures[#failures+1]=kind..': '..detail end
end
local function show(s) return (string.gsub(string.sub(s,1,160),'[%z\1-\31\127-\255]',function(c) return string.format('\\%d',string.byte(c)) end)) end

local function check_encode(v)
  local ok1,r1=pcall(L_encode,v)
  local ok2,r2=pcall(C.encode,v)
  stats.encode=stats.encode+1
  if ok1~=ok2 then mismatch('encode accept',tostring(r1)..' | '..tostring(r2));return end
  if ok1 then
    if r1~=r2 then mismatch('encode text',show(r1)..' | '..show(r2)) end
  else
    stats.encode_err=stats.encode_err+1
    local m1,m2=message(r1),message(r2)
    -- canon.float with a non-number value: Lua fails comparing it, C names it
    if m1~=m2 and not (m2=='canon: float value is not a number' and string.find(m1,'attempt to compare',1,true)) then
      mismatch('encode error',m1..' | '..m2)
    end
  end
end

local function check_decode(text)
  local ok1,r1=pcall(L_decode,text)
  local ok2,r2=pcall(C.decode,text)
  stats.decode=stats.decode+1
  if ok1~=ok2 then mismatch('decode accept',show(text)..' => '..tostring(r1)..' | '..tostring(r2));return end
  if ok1 then
    if not same(r1,r2) then mismatch('decode value',show(text)) end
    local e1,e2=L_encode(r1),L_encode(r2)
    if e1~=e2 then mismatch('decode re-encode',show(text)) end
  else
    stats.decode_err=stats.decode_err+1
    if r1~=r2 then mismatch('decode error',show(text)..' => '..tostring(r1)..' | '..tostring(r2)) end
  end
end

local function check_keys(text,keys)
  local ok1,r1=pcall(L_keys,text,keys)
  local ok2,r2=pcall(C.decode_keys,text,keys)
  stats.keys=stats.keys+1
  if ok1~=ok2 then mismatch('keys accept',show(text)..' => '..tostring(r1)..' | '..tostring(r2));return end
  if type(keys)=='table' and string.find(text,'^[ \t\n\r]*{') then  -- F2: skipped fields as strict as decode()
    local ok3,r3=pcall(L_decode,text)
    if ok3~=ok1 or (not ok1 and r3~=r1) then mismatch('keys vs decode',show(text)..' => '..tostring(r1)..' | '..tostring(r3)) end
  end
  if ok1 then
    if not same(r1,r2) then mismatch('keys value',show(text)) end
  else
    stats.keys_err=stats.keys_err+1
    local nil_keys=string.find(tostring(r1),'attempt to index',1,true) and string.find(tostring(r2),'attempt to index',1,true)
    if message(r1)~=message(r2) and not nil_keys then mismatch('keys error',show(text)..' => '..tostring(r1)..' | '..tostring(r2)) end
  end
end

------------------------------------------------------------------------------------------------------
-- texts for decode
------------------------------------------------------------------------------------------------------
local WS={'',' ','\t','\n','\r','  \n '}
local NUMS={'0','-0','1','-1','01','-01','1.','.5','1.5','-1.5','1e5','1E5','1e+5','1e-5','1e','1e+','-','+1','1.5e3',
  '0.0','-0.0','1e400','-1e400','1e-400','9007199254740992','9007199254740993','-9007199254740992','-9007199254740993',
  '90071992547409920','0009','1.0e0','123456789012345678901234567890','2147483647','2147483648','-2147483648','4294967296',
  '1.7976931348623157e308','1.7976931348623159e308','5e-324','2e-324','3.141592653589793238462643383279',
  '0.30000000000000004','100','1e22','12345678901234567890e-10','-0e0','0e5','1.5E-3x'}
local ESC={'\\"','\\\\','\\/','\\b','\\f','\\n','\\r','\\t','\\u0041','\\u00e9','\\u00E9','\\u0000','\\u001f','\\u007f',
  '\\ud83d\\ude00','\\uD83D\\uDE00','\\ud800','\\udc00','\\ud800\\u0041','\\ud800\\udbff','\\ud800\\ud800\\udc00',
  '\\ud800\\uzzzz','\\u12','\\x','\\a','\\','\\u','\\uffff','\\ufeff'}
local RAW={'a','Z',' ','é','€','😀','\127','\t','\n','\0','\31','\237\160\128','\255','\192\128'}
local function json_of(v) local ok,text=pcall(L_encode,v);return ok and text or 'null' end
local function jstring()
  local out={'"'}
  for _=1,rnd(8) do
    local r=rnd(10)
    if r<4 then out[#out+1]=pick({'a','b','key','x y','0','{','[',']','}',',',':'})
    elseif r<7 then out[#out+1]=pick(ESC) else out[#out+1]=pick(RAW) end
  end
  if rnd(30)~=0 then out[#out+1]='"' end
  return table.concat(out)
end
local jvalue
jvalue=function(depth)
  local ws=pick(WS)
  local r=rnd(depth>8 and 6 or 10)
  if r==0 then return ws..pick(NUMS)
  elseif r==1 then return ws..pick({'null','true','false','nul','tru','fals','nullx','NaN','Infinity','-Infinity','None'})
  elseif r==2 or r==3 then return ws..jstring()
  elseif r==4 then return ws..json_of(gen(depth))
  elseif r==5 then return ws..tostring(rnd(1000)-500)
  elseif r<=7 then
    local items={}
    for i=1,rnd(5) do items[i]=jvalue(depth+1)..pick(WS) end
    local sep=rnd(40)==0 and ';' or ','
    local tail=rnd(40)==0 and ',' or ''
    return ws..'['..table.concat(items,sep)..tail..pick(WS)..(rnd(50)==0 and '' or ']')
  else
    local items={}
    for i=1,rnd(5) do
      local key=rnd(6)==0 and jstring() or L_encode(pick(KEYS))
      if rnd(15)==0 and i>1 then key=string.match(items[1],'^%s*("[^"]*")') or key end
      items[i]=pick(WS)..key..pick(WS)..(rnd(60)==0 and '' or ':')..jvalue(depth+1)
    end
    local tail=rnd(40)==0 and ',' or ''
    return ws..'{'..table.concat(items,',')..tail..pick(WS)..(rnd(50)==0 and '' or '}')
  end
end
local MUT={'"','\\','{','}','[',']',',',':','0','-','.','e','n','t','f',' ','\0','\31','\128','\237','\239\187\191','x'}
local function mutate(text)
  for _=1,rnd(3)+1 do
    local n=#text;local p=rnd(n+1)+1;local r=rnd(5)
    if r==0 and n>0 then text=string.sub(text,1,p-1)..string.sub(text,p+1)
    elseif r==1 then text=string.sub(text,1,p-1)..pick(MUT)..string.sub(text,p)
    elseif r==2 and n>0 then text=string.sub(text,1,p-1)..pick(MUT)..string.sub(text,p+1)
    elseif r==3 then text=string.sub(text,1,p)
    else text=string.sub(text,p)..string.sub(text,1,p-1) end
  end
  return text
end
local function deep_text(n,open,close,leaf) return string.rep(open,n)..leaf..string.rep(close,n) end

------------------------------------------------------------------------------------------------------
-- sha256 against the system sha256sum
------------------------------------------------------------------------------------------------------
local function sha_check(count)
  local dir=os.getenv('TMPDIR') or '/tmp'
  local KA={['']='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    abc='ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq='248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'}
  for text,digest in pairs(KA) do stats.sha=stats.sha+1;if C.sha256(text)~=digest then mismatch('sha256 known',text) end end
  local probe=io.popen('command -v sha256sum 2>/dev/null')
  local have=probe and probe:read('*a') or '';if probe then probe:close() end
  if have=='' then return end
  for i=1,count do
    local len=({0,1,55,56,57,63,64,65,119,120,127,128,129,1000,4096})[i%15+1]+rnd(3)
    local bytes={}
    for k=1,len do bytes[k]=string.char(rnd(256)) end
    local text=table.concat(bytes)
    local path=dir..'/canon-c-sha-'..i
    local f=assert(io.open(path,'wb'));f:write(text);f:close()
    local p=io.popen('sha256sum '..path);local out=p:read('*a');p:close();os.remove(path)
    stats.sha=stats.sha+1
    if string.match(out,'^(%x+)')~=C.sha256(text) then mismatch('sha256',tostring(len)) end
  end
end

------------------------------------------------------------------------------------------------------
-- the ~1 MB native-history document (the shape history.lua writes)
------------------------------------------------------------------------------------------------------
local function history_doc(target)
  local profiles={}
  for i=1,40 do profiles[i]=string.format('wg_%02d_%s',i,({'nl','de','pl','fi','se','ch','fr'})[i%7+1]) end
  local function order(n) local o={};local start=rnd(#profiles);for i=1,n do o[i]=profiles[(start+i)%#profiles+1] end;return canon.array(o) end
  local events={};local months=canon.object({});local days=canon.object({})
  local totals=canon.object({})
  local t=1760000000.25;local size=0;local n=0
  while size<target do
    n=n+1;t=t+rnd(4000)+rnd(1000)/1000
    local ev=canon.object({state=pick({'SWITCHED','RESTORED','REFUSED','HELD','COMMITTED'}),
      codes=canon.array({pick({'PROBE-FAIL','OPERATOR-MANUAL','DNS-TIMEOUT','HANDSHAKE-STALE'}),'NATIVE-SWITCH'}),
      trial=rnd(2)==0,time=canon.float(t),sequence=n,source=pick(profiles),target=pick(profiles),
      from_role='source',destination_role='target',transition_source=pick({'manual','automatic','test'}),
      transition_outcome=pick({'committed','restored','refused'}),transition_kind=pick({'server','channel','protocol'}),
      route_changed=rnd(2)==0,transition_completed=true,proof_scope='router-probed-ipv4',
      before_order=order(rnd(20)+8),after_order=order(rnd(20)+8),
      latency=canon.object({detect_ms=rnd(5000),switch_ms=canon.float(rnd(900000)/1000),total=canon.float(rnd(90000)/100),
        samples=canon.array({canon.float(rnd(9000)/100),canon.float(rnd(9000)/100),canon.float(rnd(9000)/100)})}),
      phase_evidence=canon.array({canon.object({phase='DETECT',time=canon.float(t-3.5)}),canon.object({phase='SWITCH',time=canon.float(t-1.25)}),
        canon.object({phase='VERIFY',time=canon.float(t)})}),
      probe_evidence=canon.object({required_failures=3,required_successes=2,source_streak_met=true,reserve_streak_met=rnd(2)==0}),
      key=C.sha256(tostring(n)),note=(rnd(10)==0) and 'проверка \226\128\148 ok' or NULL})
    events[#events+1]=ev
    local month=os.date('!%Y-%m',math.floor(t));local day=os.date('!%Y-%m-%d',math.floor(t))
    for _,bucket in ipairs({months,days}) do
      local key=bucket==months and month or day
      bucket[key]=bucket[key] or canon.object({switches=0,restored=0,refused=0,manual=0,automatic=0})
      bucket[key].switches=bucket[key].switches+1
    end
    if n%50==0 then size=#C.encode(canon.array(events)) end
  end
  return canon.object({sequence=n,events=canon.array(events),months=months,days=days,totals=totals,last_key=C.sha256('last'),
    last_time=canon.float(t),timezone='Europe/Berlin',daily_since=canon.float(1760000000.5),schema=1})
end

local clock=os.clock
local function timed(fn,reps)
  local best=math.huge
  for _=1,reps do local a=clock();fn();local d=clock()-a;if d<best then best=d end end
  return best*1000
end

if mode=='floats' then
  -- repr(float): random bit patterns over the whole exponent range, powers of two and ten with their neighbours
  local count,bad=tonumber(arg[2]) or 200000,0
  local function one(x)
    local want=canon.repr_float(x)
    local got=C.encode(canon.float(x))
    if got~=want then bad=bad+1;if bad<=10 then print(string.format('  float %.17g: lua %s c %s',x,want,got)) end end
  end
  for k=-1074,1023 do
    local p=2^k;one(p);one(p*(1+2^-52));if k>-1074 then one(p*(1-2^-53)) end
  end
  for k=-323,308 do local p=tonumber('1e'..k);if p and p~=0 and p<math.huge then one(p);one(-p) end end
  for _=1,count do
    local m=rnd(2^26)*2^27+rnd(2^27)
    local x=math.ldexp(m,rnd(2098)-1126)
    if x~=0 and x<math.huge then one(rnd(2)==0 and x or -x) end
    one((rnd(2^30)+1)/(rnd(2^20)+1))
  end
  print('floats: checked='..(2*count+2098*3+632*2)..' mismatch='..bad)
  os.exit(bad==0 and 0 or 1)
end

if mode=='bench' then
  local reps=tonumber(arg[2]) or 5
  local doc=history_doc(1000000)
  local text=L_encode(doc)
  assert(C.encode(doc)==text,'encode differs')
  assert(same(L_decode(text),C.decode(text)),'decode differs')
  local wanted={sequence=true,months=true,last_key=true}
  assert(same(L_keys(text,wanted),C.decode_keys(text,wanted)),'decode_keys differs')
  local r={bytes=#text,events=#doc.events}
  r.lua_encode_ms=timed(function() L_encode(doc) end,reps)
  r.c_encode_ms=timed(function() C.encode(doc) end,reps)
  r.lua_decode_ms=timed(function() L_decode(text) end,reps)
  r.c_decode_ms=timed(function() C.decode(text) end,reps)
  r.lua_decode_keys_ms=timed(function() L_keys(text,wanted) end,reps)
  r.c_decode_keys_ms=timed(function() C.decode_keys(text,wanted) end,reps)
  r.c_sha256_ms=timed(function() C.sha256(text) end,reps)
  local keys={};for k,v in pairs(r) do keys[#keys+1]=k..'='..(math.floor(v)==v and tostring(v) or string.format('%.2f',v)) end
  table.sort(keys)
  print('bench: '..table.concat(keys,' '))
  print(string.format('bench speedup: encode x%.1f decode x%.1f decode_keys x%.1f',r.lua_encode_ms/r.c_encode_ms,
    r.lua_decode_ms/r.c_decode_ms,r.lua_decode_keys_ms/r.c_decode_keys_ms))
  os.exit(0)
end

------------------------------------------------------------------------------------------------------
-- fuzz
------------------------------------------------------------------------------------------------------
local cases=tonumber(arg[2]) or 20000
-- fixed edge cases first
for _,v in ipairs({NULL,true,false,0,-0.0,1,-1,0.5,canon.float(-0.0),canon.float(0),canon.float(5),canon.array({}),canon.object({}),
  nest(200,1),nest(201,1),nest(199,canon.array({})),2^53,-2^53,2^53+2,'',"\0",'\237\160\128\237\176\128',canon.object({['\0']=1,['']=2})}) do
  check_encode(v)
end
for _,v in ipairs(INTS) do check_encode(v);check_encode(canon.float(v)) end
for _,v in ipairs(FLOATS) do check_encode(v);check_encode(canon.float(v));check_encode(-v) end
for _,s in ipairs(BAD) do check_encode(s);check_encode(canon.object({[s]=1})) end
for _,t in ipairs({'','  ','\239\187\191{}','{}','[]','{"a":1,"a":2}','{"a":{"b":1,"b":2}}',deep_text(64,'[',']','1'),deep_text(65,'[',']','1'),
  deep_text(64,'[',']',''),deep_text(65,'[',']',''),deep_text(66,'[',']',''),'"\\ud800"','"\\udc00\\ud800"','[1,]','{"a":1,}','[1 2]','{"a" 1}',
  '{1:2}','"abc','"\\u12"','1 2','nulls','[nul]','\128','"\237\160\128"','-','--1','1.e5','[-]','{"a":-}'}) do
  check_decode(t);check_keys(t,{a=true,b=true})
end
for _,n in ipairs(NUMS) do check_decode(n);check_decode('['..n..']');check_decode('{"a":'..n..'}') end
for _,e in ipairs(ESC) do check_decode('"'..e..'"');check_decode('["'..e..'x"]') end
for _,r in ipairs(RAW) do check_decode('"'..r..'"') end
local deep_obj=string.rep('{"k":',64)..'1'..string.rep('}',64)
check_keys('{"x":'..deep_obj..'}',{});check_keys('{"x":'..string.rep('[',65)..string.rep(']',65)..'}',{})
check_keys('{"x":'..string.rep('[',64)..string.rep(']',64)..',"y":1}',{y=true})
check_keys('{"x":"a\\"b\\\\","y":[1,"]",{"z":"}"}],"w":2}',{w=true})
check_keys('{"x":[}],"y":1}',{y=true});check_keys('{"x":"abc','y',{y=true});check_keys('[1]',{});check_keys('{"a":1} x',{a=true})
for _,v in ipairs({'[garbage}','"\\q"','"a\1b"','[1,]','{"k":1,"k":2}','1e400','01','nul','{"k":1]'}) do
  check_keys('{"x":'..v..',"a":1}',{a=true});check_keys('{"a":1,"x":['..v..']}',{a=true})
end
check_keys('{"a":1}',nil);check_keys('{}',nil)
for _=1,cases do
  local r=rnd(10)
  if r<3 then check_encode(gen(0,true))
  elseif r==3 then check_encode(canon.array({gen(0),bad_value(),gen(0)}))
  elseif r<=6 then
    local text=jvalue(0)
    check_decode(text)
    if rnd(3)==0 then check_decode(mutate(text)) end
  elseif r==7 then
    local text=json_of(gen(0))
    check_decode(rnd(2)==0 and text or mutate(text))
  else
    local obj=canon.object({});for _=1,rnd(6) do obj[pick(KEYS)]=gen(1) end
    local text=pick({'',' ','\n'})..json_of(obj)
    if rnd(2)==0 then text=jvalue(0) end
    if rnd(3)==0 then text=mutate(text) end
    local keys={};for _=1,rnd(4) do keys[pick(KEYS)]=true end
    check_keys(text,keys)
  end
end
sha_check(math.min(300,math.floor(cases/50)+30))
local parts={}
for k,v in pairs(stats) do parts[#parts+1]=k..'='..v end
table.sort(parts)
print('fuzz: '..table.concat(parts,' ')..' seed='..(tonumber(arg[3]) or 20261031))
for _,f in ipairs(failures) do print('  '..f) end
os.exit(stats.mismatch==0 and 0 or 1)
