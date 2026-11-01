-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- Test harness of the Lua monitor: plain lua5.1, no router modules; a fake runner replaces monitor_io.lua.
-- MERGE NOTE: feat/lua-core-20261030 has tests/lua/harness.lua with the same test/eq/truthy/raises/run API;
-- this file adds the fake runner. Unify into one harness at merge.
local here=(arg and arg[0] and arg[0]:match('^(.*)/[^/]*$')) or '.'
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..here..'/?.lua;'..package.path
local canon=require('canon')
canon.configure({runtime=os.getenv('HOMENSAI_TEST_RUNTIME') or '/tmp'})

local T={here=here,cases={},failures=0,canon=canon}
function T.test(name,fn) T.cases[#T.cases+1]={name,fn} end
local function show(v)
  if type(v)=='string' then return string.format('%q',v) end
  if type(v)=='table' then
    if v==canon.null then return 'null' end
    local ok,text=pcall(canon.encode,v);if ok then return text end
    local parts={};for k,item in pairs(v) do parts[#parts+1]=tostring(k)..'='..show(item) end;return '{'..table.concat(parts,',')..'}'
  end
  return tostring(v)
end
T.show=show
-- Value equality; a Python-float box equals the plain number of the same value (accounting keeps Python's
-- int/float types since Lua plan item 6; the byte-level typing is checked by tests/test_lua_history.py).
local function deep(a,b)
  if canon.is_float(a) or canon.is_float(b) then return canon.number(a)~=nil and canon.number(a)==canon.number(b) end
  if type(a)~=type(b) then return false end
  if type(a)~='table' then return a==b end
  if a==canon.null or b==canon.null then return a==b end
  for k,v in pairs(a) do if not deep(v,b[k]) then return false end end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end
function T.eq(actual,expected,message)
  if not deep(actual,expected) then error((message or 'not equal')..': got '..show(actual)..', expected '..show(expected),2) end
end
function T.truthy(v,message) if not v then error(message or 'expected a true value',2) end end
function T.raises(fn,...) local ok,err=pcall(fn,...);if ok then error('expected an error',2) end;return err end
function T.run()
  local passed=0
  for _,case in ipairs(T.cases) do
    local ok,err=pcall(case[2])
    if ok then passed=passed+1 else T.failures=T.failures+1;io.stderr:write('FAIL ',case[1],': ',show(err),'\n') end
  end
  local name=(arg and arg[0] or '?'):match('([^/]*)$')
  if T.failures==0 then print(name..': '..passed..' tests OK') else print(name..': '..T.failures..' FAILED of '..#T.cases) end
  os.exit(T.failures==0 and 0 or 1)
end

------------------------------------------------------------------------------------------------------
-- fake runner
------------------------------------------------------------------------------------------------------
local function u16(n) return string.char(math.floor(n/256)%256,n%256) end
local function be16(s,i) local a,b=string.byte(s,i,i+1);return a*256+b end
T.u16,T.be16=u16,be16

function T.b64url_decode(text)
  local alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
  local bits,out='',{}
  for c in string.gmatch(text,'.') do
    local index=string.find(alphabet,c,1,true)-1
    local b='';for k=5,0,-1 do b=b..(math.floor(index/2^k)%2) end
    bits=bits..b
  end
  for i=1,#bits-7,8 do out[#out+1]=string.char(tonumber(string.sub(bits,i,i+7),2)) end
  return table.concat(out)
end

-- A valid DNS answer to our question packet (QR set, no error, one question echoed, one A answer).
function T.dns_answer(packet)
  local token=string.sub(packet,1,2);local question=string.sub(packet,13)
  return token..u16(0x8180)..u16(1)..u16(1)..u16(0)..u16(0)..question..'\192\12'..u16(1)..u16(1)..'\0\0\0\60'..u16(4)..'\93\184\216\34'
end

local function http(status,body,extra) return 'HTTP/1.1 '..status..' OK\r\nContent-Type: text/plain\r\n'..(extra or '')..'Content-Length: '..#body..'\r\nConnection: close\r\n\r\n'..body end
T.http=http

-- Inventory fixture: two WireGuard peers bound to tunnels, one OpenVPN without interface.
function T.inventory(overrides)
  local data={
    profiles={
      {id='wireguard:peer_7',section='peer_7',protocol='wireguard',name='Vienna',group_id='1',profile_id='7',vendor_profile_group_id='wireguard:1',vendor_tunnel_id='wireguard:wgclient',interface='wgclient',administrative_state='enabled'},
      {id='wireguard:peer_8',section='peer_8',protocol='wireguard',name='Berlin',group_id='1',profile_id='8',vendor_profile_group_id='wireguard:1',vendor_tunnel_id='wireguard:wgclient2',interface='wgclient2',administrative_state='enabled'},
      {id='openvpn:1_2',section='1_2',protocol='openvpn',name='Paris',group_id='1',profile_id='2',vendor_profile_group_id='openvpn:1',vendor_tunnel_id=canon.null,interface=canon.null,administrative_state='unknown'}},
    servers={{id='cfg1',profile='wireguard:peer_7',name='Main',channel='primary',priority=10,enabled=true},
             {id='cfg2',profile='wireguard:peer_8',name='Reserve',channel='reserve',priority=20,enabled=true}},
    native_candidates=canon.array(),wan_interfaces=canon.array({'wan'}),
    settings={enabled=true,interval=10,checkpoint=900,probe_limit=16,live_log_limit=2000,history_days=7,
              plan_source='wireguard:peer_7',plan_target='wireguard:peer_8',plan_source_tunnel='wireguard:wgclient',plan_target_tunnel='wireguard:wgclient2'}}
  for k,v in pairs(overrides or {}) do data[k]=v end
  return data
end

function T.fake_runner(options)
  options=options or {}
  local R={RUNTIME='/run/hv',PERSIST='/etc/hv',now=options.now or 1761825600.5,mono=options.mono or 1000.0,
    files={},writes={},commands_log={},forwards={},logs={},config=options.config,config_version=1,
    counters={wgclient={ifindex=20,rx=1000,tx=2000},wgclient2={ifindex=21,rx=500,tx=600},eth0={ifindex=2,rx=9000,tx=8000}},
    interfaces={wgclient={up=true,l3_device='wgclient',proto='wgclient'},wgclient2={up=true,l3_device='wgclient2',proto='wgclient'},
                wan={up=true,l3_device='eth0',proto='dhcp'}},
    marks={wgclient={mark=0x1000,table='53'},wgclient2={mark=0x2000,table='54'}},
    https_status=200,https_fail={},dns_fail=false,icmp_rtt=12.3,icmp_kind=nil,
    inventory_data=options.inventory or T.inventory(),forward_reply='{"accepted":true}',caps={so_mark=false,tls=false,raw_icmp=true,bindtodevice=true,nixio=true,sha256='fake'}}
  function R.wall() return R.now end
  function R.clock() return R.mono end
  function R.advance(seconds) R.now=R.now+seconds;R.mono=R.mono+seconds end
  function R.random(n) local out={};for i=1,n do out[i]=string.char((i*37+n)%256) end;return table.concat(out) end
  function R.log(text) R.logs[#R.logs+1]=text end
  function R.read_file(path) return R.files[path] end
  function R.file_size(path) return R.files[path] and #R.files[path] or nil end
  function R.exists(path) return R.files[path]~=nil end
  function R.write_atomic(path,text) R.files[path]=text;R.writes[#R.writes+1]=path end
  function R.sysfs(device,name)
    local row=R.counters[device];if not row then return nil end
    if name=='ifindex' then return tostring(row.ifindex) elseif name=='statistics/rx_bytes' then return tostring(row.rx) elseif name=='statistics/tx_bytes' then return tostring(row.tx) end
  end
  function R.config_mtime() if R.config==nil then return nil end;return R.config_version end
  function R.config_text() return R.config end
  function R.package_version() return '2.0.0-lua-alpha3-test' end
  function R.capabilities() return R.caps end
  function R.command(name,a,b)
    R.commands_log[#R.commands_log+1]={name,a,b}
    if name=='inventory' then return canon.encode(R.inventory_data) end
    if name=='native_policy' then
      R.policy_reads=(R.policy_reads or 0)+1
      if R.native_policy then return canon.encode(R.native_policy) end
      return nil,'COMMAND-FAILED'
    end
    if name=='iface_status' then
      local row=R.interfaces[a];if not row then return nil,'COMMAND-FAILED' end
      return canon.encode(canon.object(row))
    end
    if name=='routes' then
      local rows=canon.array()
      for dev,m in pairs(R.marks) do rows[#rows+1]=canon.object({dst='default',dev=dev,table=tonumber(m.table)}) end
      rows[#rows+1]=canon.object({dst='default',dev='eth0',gateway='192.0.2.1'})
      return canon.encode(rows)
    end
    if name=='rules' then
      local rows=canon.array({canon.object({priority=0,src='all',table='local'})})
      for dev,m in pairs(R.marks) do rows[#rows+1]=canon.object({priority=100,src='all',fwmark=string.format('0x%x',m.mark),table=m.table}) end
      return canon.encode(rows)
    end
    if name=='route_get' then
      for dev,m in pairs(R.marks) do if tostring(m.mark)==b then return canon.encode(canon.array({canon.object({dst=a,dev=dev,table=tonumber(m.table)})})) end end
      return canon.encode(canon.array({canon.object({dst=a,dev='eth0'})}))
    end
    return nil,'unknown command'
  end
  -- asynchronous primitives: answered at once, or queued while R.deferred is set (R.drain() delivers them)
  R.queue={}
  local function deliver(fn) if R.deferred then R.queue[#R.queue+1]=fn else fn() end end
  function R.drain() while #R.queue>0 do local fn=table.remove(R.queue,1);fn() end end
  function R.hires() return R.mono end
  function R.datagram(kind,device,host,port,packet,seconds,accept,cb)
    if kind=='udp' then
      R.last_udp={device=device,host=host,port=port}
      deliver(function()
        if R.dns_fail then cb(nil,R.dns_fail);return end
        local data=T.dns_answer(packet)
        if accept(data,host) then cb(data,nil,R.mono,R.mono) else cb(nil,'timeout') end
      end)
      return
    end
    R.last_icmp={device=device,target=host}
    deliver(function()
      if R.icmp_rtt==nil then cb(nil,R.icmp_kind or 'timeout');return end
      local identifier,sequence,payload=be16(packet,5),be16(packet,7),string.sub(packet,9)
      local echo='\0\0'..u16(0)..u16(identifier)..u16(sequence)..payload
      local probe=require('probe')
      echo='\0\0'..u16(probe.icmp_checksum(echo))..string.sub(echo,5)
      local a,b,c,d=string.match(host,'^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
      local ip='\69\0'..u16(20+#echo)..u16(1)..u16(0)..'\64\1'..u16(0)..string.char(tonumber(a),tonumber(b),tonumber(c),tonumber(d))..'\192\168\8\1'
      local data=ip..echo
      if accept(data,host) then cb(data,nil,R.mono,R.mono+R.icmp_rtt/1000) else cb(nil,'timeout') end
    end)
  end
  local function respond(address,path)
    if R.https_status~=200 then return {status=R.https_status,body=''} end
    if address=='1.1.1.1' then return {status=200,body='fl=1f\nh=one.one.one.one\nip='..(R.exit_ip or '93.184.216.34')..'\nts=1\nvisit_scheme=https\nhttp=http/1.1\nloc='..(R.exit_country or 'DE')..'\n'} end
    if address=='8.8.8.8' then return {status=200,body='{"Status":0,"TC":false,"Answer":[{"name":"example.com.","type":1,"TTL":60,"data":"93.184.216.34"}]}'} end
    local packet=T.b64url_decode(string.match(path,'dns=([A-Za-z0-9_-]+)'))
    return {status=200,body=T.dns_answer(packet)}
  end
  function R.https_get(device,address,hostname,path,seconds,cb)
    R.last_https={device=device,address=address,hostname=hostname,path=path,seconds=seconds}
    R.https_calls=(R.https_calls or 0)+1
    deliver(function()
      local fail=R.https_fail[address];if fail then cb(nil,fail);return end
      if R.https_reply then cb(R.https_reply(address,path));return end
      cb(respond(address,path))
    end)
  end
  -- files and locks used by the item-2/3 modules
  R.versions={};R.locked={}
  local write=R.write_atomic
  function R.write_atomic(path,text) write(path,text);R.versions[path]=(R.versions[path] or 0)+1 end
  R.write_ram=R.write_atomic
  function R.remove(path) R.files[path]=nil;R.versions[path]=(R.versions[path] or 0)+1 end
  function R.file_key(path) if R.files[path]==nil then return nil end;return tostring(R.versions[path] or 0)..':'..#R.files[path] end
  function R.unsafe(path) return false end
  function R.list_dir(directory)
    local names={}
    for path in pairs(R.files) do
      local name=string.match(path,'^'..string.gsub(directory,'[%-%.%+%[%]%(%)%$%^%%%?%*]','%%%0')..'/([^/]+)$')
      if name then names[#names+1]=name end
    end
    table.sort(names);return names
  end
  function R.try_lock(directory,fn,name)
    name=name or 'auto-control.lock'
    if R.locked[name] then return false end
    R.locked[name]=true
    local results={pcall(fn)}
    R.locked[name]=nil
    if not results[1] then error(results[2],0) end
    return true,unpack(results,2)
  end
  R.bridge_runs={}
  function R.bridge(output,cb) R.bridge_runs[#R.bridge_runs+1]=output;deliver(function() cb(0) end) end
  function R.forward(method,json_text) R.forwards[#R.forwards+1]={method,json_text};return R.forward_reply end
  return R
end

-- synchronous wrappers of the asynchronous checks
function T.await(R,start)
  local got,box=false,{}
  start(function(...) got=true;box={...} end)
  if R.drain then R.drain() end
  if not got then error('callback never ran',2) end
  return unpack(box)
end
function T.probe_now(R,profile) return T.await(R,function(cb) require('probe').probe(R,profile,cb) end) end
function T.dns_now(R,device) return T.await(R,function(cb) require('probe').dns_probe(R,device,cb) end) end
function T.https_now(R,device,target,detail,sink) return T.await(R,function(cb) require('probe').https_probe(R,device,target,detail,sink,cb) end) end

-- A fake libuci cursor over a table {main={key=value}} with a save directory for the pending-delta check.
function T.fake_uci(store,options)
  options=options or {}
  local function cursor()
    local staged={}
    local c={}
    function c:get_savedir() return options.savedir or '/nonexistent-homensai-savedir' end
    function c:set(config,section,key,value)
      if options.fail_set then return false end
      staged[#staged+1]={section,key,value};return true
    end
    function c:save(config) return true end
    function c:commit(config)
      for _,row in ipairs(staged) do store[row[1]]=store[row[1]] or {};store[row[1]][row[2]]=row[3] end
      staged={};store.commits=(store.commits or 0)+1
      if options.corrupt_after_commit then store.main[options.corrupt_after_commit]='tampered' end
      return true
    end
    function c:revert(config) staged={};store.reverts=(store.reverts or 0)+1 end
    function c:get(config,section,key) return store[section] and store[section][key] end
    return c
  end
  return cursor
end

return T
