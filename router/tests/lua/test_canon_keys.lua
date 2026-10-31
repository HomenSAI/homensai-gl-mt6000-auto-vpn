-- canon.decode_keys: the kept fields equal decode()'s, the skipped ones may hold anything JSON allows
-- (strings with brackets, quotes and escapes, deep nesting, numbers, literals), and the same errors are raised.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')

local function same(a,b) return canon.encode(a)==canon.encode(b) end

t.test('kept fields equal the full decode, skipped fields are absent',function()
  local text=[==[{"accounting":{"a":[1,2,{"x":"]}[{\"\\"}],"b":"tricky \" ] } [ {"},"time":1793405535.045466,
 "samples":[{"id":"wireguard:peer_2002","ok":true,"rtt":40.0},{"id":"x","ok":false,"rtt":null}],
 "events":["{","}","[","]","\\",""],"error":null,"profiles":[{"id":"a","vendor_changed_at":1.5e3,"n":-0}],
 "native_history":{"deep":[[[[[[{"z":[]}]]]]]]},"uplink_observation":{"state":"UP","time":12},
 "vendor_observation":{"version":1,"groups":[]},"observation_valid_for":30,"speed_tests":[true,false,null,-1.25e-3]}]==]
  local full=canon.decode(text)
  local keys={time=true,error=true,profiles=true,samples=true,vendor_observation=true,uplink_observation=true,observation_valid_for=true}
  local part=canon.decode_keys(text,keys)
  for k in pairs(keys) do t.truthy(same(part[k],full[k]) or (part[k]==nil and full[k]==nil),k) end
  t.eq(part.accounting,nil);t.eq(part.events,nil);t.eq(part.native_history,nil);t.eq(part.speed_tests,nil)
  t.eq(canon.encode(part.samples[1].rtt),'40.0','float kept as float')
  t.eq(canon.encode(part.time),'1793405535.045466')
end)

t.test('random documents: every subset of keys equals the full decode',function()
  math.randomseed(7)
  local pieces={'"a]b"','"q\\"[{"','"\\\\"','"\u00e9"','12','-0.5','1e+20','true','false','null','[]','{}',
    '[1,"]",{"k":"}"}]','{"n":{"m":[[["x"]]]}}'}
  for round=1,300 do
    local parts,names={},{}
    local n=math.random(0,8)
    for i=1,n do
      local name='k'..i
      names[#names+1]=name
      parts[#parts+1]='"'..name..'":'..pieces[math.random(#pieces)]
    end
    local text='{'..table.concat(parts,',')..'}'
    local full=canon.decode(text)
    local keys={}
    for _,name in ipairs(names) do if math.random()<0.5 then keys[name]=true end end
    local part=canon.decode_keys(text,keys)
    for _,name in ipairs(names) do
      if keys[name] then t.truthy(same(part[name],full[name]),text..' '..name)
      else t.eq(part[name],nil,text..' '..name) end
    end
  end
end)

t.test('errors: not an object, broken skipped value, extra data, duplicate fields',function()
  t.raises(canon.decode_keys,'[1]',{})
  t.raises(canon.decode_keys,'{"a":"unterminated}',{})
  t.raises(canon.decode_keys,'{"a":[1,2}',{})
  t.raises(canon.decode_keys,'{"a":1} x',{})
  t.raises(canon.decode_keys,'{"a":1,"a":2}',{})
  t.raises(canon.decode_keys,'{"a":1,"b":2',{b=true})
  t.eq(canon.encode(canon.decode_keys('{}',{a=true})),'{}')
end)

t.run()
