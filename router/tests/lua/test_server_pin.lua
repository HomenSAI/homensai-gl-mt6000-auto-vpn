-- server_pin.lua: the shared cases of ../server_pin_cases.json (the same as test_server_pin.py) and the
-- administrator command over a fake file view.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local sp=require('server_pin')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local RAW=canon.decode(read_file(t.here..'/../server_pin_cases.json'))
local function expand(v)
  if type(v)=='string' then
    for name,pem in pairs(RAW.certs) do
      local out,pos={},1
      while true do
        local a,b=string.find(v,name,pos,true)
        if not a then break end
        out[#out+1]=string.sub(v,pos,a-1);out[#out+1]=pem;pos=b+1
      end
      out[#out+1]=string.sub(v,pos);v=table.concat(out)
    end
    return v
  end
  if type(v)=='table' and v~=NULL then
    local out=setmetatable({},getmetatable(v))
    for k,x in pairs(v) do out[k]=expand(x) end
    return out
  end
  return v
end
local CASES=expand(RAW)
local function val(v) if v==NULL then return nil end return v end
local function same(actual,expected,message)
  local a,e=canon.encode(actual==nil and NULL or actual),canon.encode(expected==nil and NULL or expected)
  if a~=e then error((message or 'not equal')..':\n got      '..a..'\n expected '..e,2) end
end
local function codes(events) local out=canon.array();for _,e in ipairs(events) do out[#out+1]=e.code end;return out end

local function fake(files,run)
  local f={files={},answers={},flash=0,ram=0}
  for k,v in pairs(files or {}) do f.files[k]=val(v) end
  for k,v in pairs(run or {}) do f.answers[k]=val(v) end
  f.io={
    read=function(path,limit) local s=f.files[path];if s==nil or (limit and #s>limit) then return nil end;return s end,
    run=function(argv)
      local v=f.answers[table.concat(argv,' ')]
      if type(v)=='table' and v~=NULL then  -- successive answers; the last one repeats
        if #v>1 then return table.remove(v,1) end
        return v[1]
      end
      return v
    end,
    write_ram=function(path,text) f.ram=f.ram+1;f.files[path]=text end,
    write_flash=function(path,text) f.flash=f.flash+1;f.files[path]=text end,
    remove=function(path) f.files[path]=nil end}
  return f
end

t.test('shared cases: mode, wg, cert digests, ovpn parts, wg host, load',function()
  for _,c in ipairs(CASES.mode) do t.eq(sp.mode(val(c[1])),c[2],tostring(val(c[1]))) end
  for _,c in ipairs(CASES.wg) do t.eq(sp.wg_fingerprint(val(c[1])),val(c[2]),tostring(val(c[1]))) end
  for _,c in ipairs(CASES.cert_digests) do same(sp.cert_digests(val(c[1])),c[2],string.sub(tostring(val(c[1])),1,60)) end
  same(sp.cert_digests(RAW.certs['@CA1@']),{RAW.digests.ca1})
  same(sp.cert_digests(RAW.certs['@CA2@']),{RAW.digests.ca2})
  for _,c in ipairs(CASES.ovpn_parts) do
    local inline,ca,remote=sp.ovpn_parts(val(c[1]))
    t.eq({inline~=nil,ca or false,remote or false},{c[2],val(c[3]) or false,val(c[4]) or false},tostring(val(c[1])))
  end
  for _,c in ipairs(CASES.wg_host) do t.eq(sp.wg_host(val(c[1]),c[2]),val(c[3]),tostring(val(c[1]))) end
  for _,c in ipairs(CASES.load) do
    local state,bad=sp.load(val(c[1]))
    local n=0;for _ in pairs(state.records) do n=n+1 end
    t.eq({bad,n},{c[2],c[3]},tostring(val(c[1])))
  end
end)

t.test('shared cases: sequence (observe, requests, blocker, public)',function()
  local state=sp.empty()
  for i,step in ipairs(CASES.sequence) do
    local where='sequence step '..i
    local events,urgency
    if step.op=='observe' then events,urgency=sp.observe(state,step.live,step.now)
    elseif step.op=='request' then events,urgency=sp.apply_request(state,step.request,step.now)
    elseif step.op=='blocker' then t.eq(sp.blocker(state,step.mode,step.profiles),val(step.expect),where)
    else same(sp.public(state,step.mode),step.expect,where) end
    if events then
      same(codes(events),step.events,where)
      t.eq(urgency,val(step.urgency),where)
      if step.record then
        local r=state.records[step.record[1]]
        t.eq({r.state,r.fingerprint,r.observed},{step.record[2],step.record[3],step.record[4]},where)
      end
      local _,bad=sp.load(canon.encode(state));t.eq(bad,false,where)
    end
  end
end)

t.test('shared cases: evict',function()
  local original=sp.MAX_RECORDS
  sp.MAX_RECORDS=CASES.evict.max
  local state=sp.empty()
  for _,s in ipairs(CASES.evict.steps) do sp.observe(state,s[1],s[2]) end
  sp.MAX_RECORDS=original
  local keys={};for k in pairs(state.records) do keys[#keys+1]=k end;table.sort(keys)
  t.eq(keys,CASES.evict.expect)
end)

t.test('shared cases: gate (RAM first, then flash)',function()
  for _,case in ipairs(CASES.gate) do
    local files={[sp.CONFIG]=val(case.config),['/r/'..sp.STATE]=val(case.ram),['/p/'..sp.STATE]=val(case.flash)}
    t.eq(sp.gate(function(path) return files[path] end,'/r','/p',case.profiles),val(case.expect),case.name)
  end
end)

t.test('shared cases: live reads',function()
  for _,case in ipairs(CASES.live) do
    local f=fake(case.files,case.run)
    same(sp.read_live(case.profile,f.io),val(case.expect),case.name)
  end
end)

t.test('shared cases: the monitor object',function()
  for _,case in ipairs(CASES.pins) do
    local f=fake(case.files,case.run)
    local pins=sp.new('/var/run/homensai-vpn','/etc/homensai-vpn',f.io)
    for _,step in ipairs(case.steps) do
      for k,v in pairs(step.set_run or {}) do f.answers[k]=val(v) end
      for k,v in pairs(step.set_files or {}) do f.files[k]=val(v) end
      local events,public=pins:step(step.rows,step.mode,step.now)
      local where=case.name..' @'..tostring(step.now)
      same(codes(events),step.events,where)
      t.eq(f.flash,step.flash,where)
      if step.public then same(public,step.public,where) end
      if step.file then t.eq(f.files[step.file[1]],step.file[2],where) end
      for _,path in ipairs(step.absent or {}) do t.eq(f.files[path],nil,where) end
      for _,g in ipairs(step.gate or {}) do
        local function reader(path) if path==sp.CONFIG then return g[1] end;return f.files[path] end
        t.eq(sp.gate(reader,nil,nil,g[2]),val(g[3]),where)
      end
      for _,e in ipairs(events) do t.eq(e.time,step.now,where) end
    end
  end
end)

t.test('administrator command over a fake view',function()
  local f=fake({},{['uci -q get network.wgclient1.config']='peer_1\n',
    ['wg show wgclient1 endpoints']='q3Yp1E6rM2u1Lr0m8X4h6c8w2T5fW1kJ9Zx0bVnAs0E=\t1.1.1.1:51820\n'})
  local pins=sp.new('/r','/p',f.io)
  pins:step({canon.object({id='wireguard:peer_1',interface='wgclient1',code=NULL})},'warn',100)
  f.answers['wg show wgclient1 endpoints']='Bz7Q0mYk4sV8pT2xR6wN1cL5dH9fJ3gA0eU7iO4yK2w=\t1.1.1.1:51820\n'
  local events=pins:step({canon.object({id='wireguard:peer_1',interface='wgclient1',code=NULL})},'warn',800)
  same(codes(events),{'SERVER-KEY-CHANGED'})
  local out={}
  local function say(s) out[#out+1]=s end
  t.eq(sp.cli({'list'},f.io,'/r','/p',1,0,say),0)
  local listed=canon.decode(out[#out])
  t.eq(#listed.changed,1);t.eq(#listed.records,1);t.eq(listed.records[1].identity,'wireguard:peer_1|-')
  t.eq(sp.cli({'accept','wireguard:peer_1'},f.io,'/r','/p',900,0,say),0)
  t.truthy(string.find(out[#out],'REQUESTED',1,true))
  same(codes((pins:step({},'warn',900))),{'SERVER-KEY-ACCEPTED'})
  t.eq(f.files['/r/'..sp.REQUEST],nil)
  t.eq(sp.cli({'forget','all','--offline'},f.io,'/r','/p',950,0,say),0)
  t.eq(next(canon.decode(f.files['/p/'..sp.STATE]).records),nil)
  for _,argv in ipairs({{},{'accept'},{'list','x'},{'delete','all'},{'accept','a','b'}}) do t.eq(sp.cli(argv,f.io,'/r','/p',1,0,say),2) end
  t.eq(sp.cli({'accept','wireguard:peer 1'},f.io,'/r','/p',1,0,say),2)
  t.truthy(string.find(out[#out],'SERVER-KEY-PROFILE-INVALID',1,true))
end)

t.run()
