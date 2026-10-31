-- canon.lua: Python json text (sort_keys, separators, ensure_ascii, repr floats) and read_json rules.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local json=require('canon')

t.test('repr of floats as Python prints them',function()
  -- Lua 5.1 folds the literals 0 and -0.0 into one constant: build both zeros at run time.
  local zero=tonumber('0');local negative_zero=-zero
  local cases={{0.1,'0.1'},{1761830400.1234567,'1761830400.1234567'},{1e16,'1e+16'},{1e15,'1000000000000000.0'},
    {1e-5,'1e-05'},{0.0001,'0.0001'},{123,'123.0'},{negative_zero,'-0.0'},{zero,'0.0'},{5e-324,'5e-324'},
    {1.7976931348623157e308,'1.7976931348623157e+308'},{2^70,'1.1805916207174113e+21'},{-2.5,'-2.5'},
    {1/3,'0.3333333333333333'},{100,'100.0'},{1e22,'1e+22'},{9007199254740993,'9007199254740992.0'}}
  for _,c in ipairs(cases) do t.eq(json.repr_float(c[1]),c[2],'repr '..c[2]) end
end)

t.test('canonical text: sorted keys, no spaces, ensure_ascii, ints vs floats',function()
  local value=json.object({b=1,a=json.array({1,2.5,json.float(3),json.null,true,false,'x/\226\128\168"\\\1\127'}),
    ['\208\175']=json.object({}),['Z']=json.array({})})
  t.eq(json.encode(value),'{"Z":[],"a":[1,2.5,3.0,null,true,false,"x/\\u2028\\"\\\\\\u0001\\u007f"],"b":1,"\\u042f":{}}')
  t.eq(json.encode('\240\159\152\128'),'"\\ud83d\\ude00"')
end)

t.test('decode keeps Python types and re-encodes byte-identically',function()
  local text='{"schema":1,"data":{"x":5.0,"y":5,"z":-0.0,"w":-0,"e":1E5,"s":"\\ud800\\u00e9\\ud83d\\ude00\\/"},"sha256":null}'
  local v=json.decode(text)
  t.truthy(json.is_float(v.data.x));t.eq(v.data.y,5);t.truthy(json.is_float(v.data.e));t.eq(v.data.w,0)
  t.eq(v.sha256,json.null)
  t.eq(json.encode(v),'{"data":{"e":100000.0,"s":"\\ud800\\u00e9\\ud83d\\ude00/","w":0,"x":5.0,"y":5,"z":-0.0},"schema":1,"sha256":null}')
end)

t.test('read_json refusals',function()
  for _,bad in ipairs({'{"a":1,"a":2}','NaN','[Infinity]','-Infinity','1e400','[1,]','01','"\1"','\239\187\191{}',
                       '{} x','','"\\x"','"\\u12"','{"a" 1}','[1 2]','"\237\160\128"','"\255"','9007199254740993',
                       string.rep('[',66)..string.rep(']',66),'tru','nul'}) do
    local ok=pcall(json.decode,bad)
    t.truthy(not ok,'should refuse '..t.show(bad))
  end
  for _,good in ipairs({' {} ','[1.5e-7]','"\\ud800"','9007199254740992','-9007199254740992',
                        string.rep('[',65)..string.rep(']',65),'"\127"','{"":null}'}) do
    local ok,err=pcall(json.decode,good)
    t.truthy(ok,'should accept '..t.show(good)..' '..tostring(err))
  end
end)

t.test('ambiguous or unsupported Lua values are refused',function()
  for _,bad in ipairs({{},{1,nil,3},{[1]=1,x=2},math.huge,0/0,2^53+2,function() end}) do
    t.truthy(not pcall(json.encode,bad),'should refuse')
  end
end)

t.test('sha256: one implementation, known answers',function()
  t.eq(json.sha256(''),'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
  t.eq(json.sha256('abc'),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  t.eq(json.sha256(string.rep('a',4096)),'c93eee2d0db02f10acc7460d9576e122dcf8cd53c4bf8dfcae1b3e74ebcfff5a')
  t.eq(json.sha256('x\0y\n\255'),'58681c472cd19fe33f183c80af5b4484d244def09a90e87be278a5c5ee75aa44')  -- binary-safe pipe
  t.truthy(({['nixio.crypto']=1,sha256sum=1})[json.sha256_backend()])
end)

t.test('unsafe runtime directories are refused',function()
  for _,bad in ipairs({'relative','/tmp/a b','/tmp/$(id)','/tmp/../etc',"/tmp/'x"}) do
    t.truthy(not pcall(json.configure,{runtime=bad}),bad)
  end
end)

t.test('repr_float: cached texts equal fresh ones, zero signs stay apart, the cache is bounded',function()
  local xs={0.1,1/3,1793405535.045466,40.0,-2.5,1e22,5e-324,2^70,123.456,-0.0001}
  local first={}
  for i,x in ipairs(xs) do first[i]=json.repr_float(x) end
  for i,x in ipairs(xs) do t.eq(json.repr_float(x),first[i],'cached '..first[i]) end
  local zero=tonumber('0')
  t.eq(json.repr_float(zero),'0.0');t.eq(json.repr_float(-zero),'-0.0');t.eq(json.repr_float(zero),'0.0')
  local max=json.REPR_CACHE_MAX;json.REPR_CACHE_MAX=5
  for i=1,20 do t.eq(json.repr_float(i+0.5),tostring(i)..'.5') end
  json.REPR_CACHE_MAX=max
  t.eq(json.repr_float(0.1),'0.1')
end)

t.run()
