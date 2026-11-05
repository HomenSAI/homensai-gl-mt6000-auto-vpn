-- dns_dual.lua: the shared cases of ../dns_dual_cases.json (the same as test_dns_dual.py), follow() over a real
-- mangle graph, the real file access in a temp directory.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local kernel=require('kernel')
local dd=require('dns_dual')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local RAW=read_file(t.here..'/../dns_dual_cases.json')
RAW=string.gsub(RAW,'@H@',(string.gsub(dd.HEADER,'%%','%%%%')))
local CASES=canon.decode(RAW)
local MANGLE=table.concat({'*mangle',':PREROUTING ACCEPT [0:0]',':ROUTE_POLICY - [0:0]',':TUNNEL4192_ROUTE_POLICY - [0:0]',
  ':TUNNEL5841_ROUTE_POLICY - [0:0]',
  '-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000',
  '-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
  '-A TUNNEL4192_ROUTE_POLICY -m comment --comment "TUNNEL4192 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000',
  '-A TUNNEL4192_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP',
  '-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000',
  '-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP','COMMIT',''},'\n')
local function chains(text) return (kernel.parse_mangle(kernel.snapshot(text))) end
local function val(v) if v==NULL then return nil end return v end
-- canonical JSON of a value, so a Lua result compares with the decoded expectation exactly (null, [] and {})
local function same(actual,expected,message)
  local a,e=canon.encode(actual),canon.encode(expected)
  if a~=e then error((message or 'not equal')..':\n got      '..a..'\n expected '..e,2) end
end

-- files as a table (absent = nil), commands answered from a table, every command recorded
local function fake(files,run,fail_write)
  local f={files={},answers={},calls=canon.array({}),fail={}}
  for path,text in pairs(CASES.gl_files) do f.files[path]=text end
  for path,text in pairs(files or {}) do f.files[path]=val(text) end
  for k,v in pairs(CASES.run_default) do f.answers[k]=v end
  for k,v in pairs(run or {}) do f.answers[k]=v end
  for _,p in ipairs(fail_write or {}) do f.fail[p]=true end
  f.io={
    read=function(path) return f.files[path] end,
    write=function(path,text) if f.fail[path] then error('write',0) end;f.files[path]=text end,
    remove=function(path) f.files[path]=nil end,
    run=function(argv,timeout)
      local copy=canon.array({});for i,a in ipairs(argv) do copy[i]=a end
      f.calls[#f.calls+1]=copy
      local answer=f.answers[table.concat(argv,' ')]
      if answer then return answer[1],answer[2] end
      return 0,''
    end}
  return f
end
local function memo_of(value)
  local out={}
  if type(value)=='table' then for k,v in pairs(value) do out[k]=v end end
  return out
end
local function check(case,result,f)
  local expected=case.expected
  same(result,expected.result,case.name)
  for path,text in pairs(expected.files) do t.eq(f.files[path],val(text),case.name..': '..path) end
  same(f.calls,expected.calls,case.name..': calls')
  t.eq(dd.memo,memo_of(expected.memo),case.name..': memo')
end

t.test('shared cases: enabled, instance_of, valid_server, servers_of, snippet',function()
  for _,c in ipairs(CASES.enabled) do t.eq(dd.enabled(val(c[1])),c[2],tostring(c[1])) end
  for _,c in ipairs(CASES.instance_of) do t.eq(dd.instance_of(val(c[1])),val(c[2]),tostring(c[1])) end
  for _,c in ipairs(CASES.valid_server) do t.eq(dd.valid_server(val(c[1])),c[2],tostring(c[1])) end
  for _,c in ipairs(CASES.servers_of) do
    same(canon.array(dd.servers_of(val(c.config),function(path) return val(c.files[path]) end)),c.expected,c.name)
  end
  for _,c in ipairs(CASES.snippet) do t.eq(dd.snippet(c.peers),val(c.expected)) end
end)

t.test('shared cases: sync',function()
  for _,case in ipairs(CASES.sync) do
    dd.memo=memo_of(case.memo)
    local f=fake(case.files,case.run,case.fail_write)
    local opts={active=val(case.active)}
    for k,v in pairs(f.io) do opts[k]=v end
    check(case,dd.sync(case.marks,opts),f)
  end
  dd.memo={}
end)

t.test('shared cases: off',function()
  for _,case in ipairs(CASES.off) do
    dd.memo=memo_of(case.memo)
    local f=fake(case.files,case.run)
    check(case,dd.off(f.io),f)
  end
  dd.memo={}
end)

t.test('every written line is bound to another GL tunnel (the leak property)',function()
  for _,case in ipairs(CASES.sync) do
    dd.memo={}
    local f=fake(case.files,case.run,case.fail_write)
    local opts={active=val(case.active)}
    for k,v in pairs(f.io) do opts[k]=v end
    dd.sync(case.marks,opts)
    for path,text in pairs(f.files) do
      if string.sub(path,-#dd.FILE-1)=='/'..dd.FILE then
        for line in string.gmatch(text,'([^\n]*)\n') do
          if line~=dd.HEADER and line~='all-servers' then
            local server,device=string.match(line,'^server=([0-9.#]+)@([a-z0-9]+)$')
            t.truthy(server and dd.valid_server(server) and dd.valid_name(device),line)
            t.truthy(path~=dd.CONFDIR..device..'/'..dd.FILE,'own tunnel listed: '..line)
          end
        end
      end
    end
  end
  dd.memo={}
end)

t.test('follow: the owner option decides; the marks come from the verified graph',function()
  same(dd.marks_from_chains(chains(MANGLE),kernel.fields),canon.array({'0x1000','0xb000'}))
  same(dd.marks_from_chains({},kernel.fields),canon.array({}))
  local f=fake({['/tmp/dnsmasq.d.wgclient1/'..dd.FILE]=dd.HEADER..'\nall-servers\nserver=1.1.1.1@ovpnclient2\n',
                [dd.SETTINGS]="config main 'main'\n    option dns_dual '0'\n"})
  local opts={active='0x1000'};for k,v in pairs(f.io) do opts[k]=v end
  local r=dd.follow(chains(MANGLE),kernel.fields,opts)
  t.eq({r.enabled,r.changed,r.code},{false,1,NULL})
  t.eq(f.files['/tmp/dnsmasq.d.wgclient1/'..dd.FILE],nil)
  f=fake()
  opts={active='0x1000'};for k,v in pairs(f.io) do opts[k]=v end
  r=dd.follow(chains(MANGLE),kernel.fields,opts)
  t.eq({r.enabled,r.changed,#f.calls},{false,0,0},'no option: off')
  f=fake({[dd.SETTINGS]="config main 'main'\n    option dns_dual '1'\n"})
  opts={active='0x1000'};for k,v in pairs(f.io) do opts[k]=v end
  r=dd.follow(chains(MANGLE),kernel.fields,opts)
  t.eq({r.enabled,r.changed,r.code},{true,2,NULL})
  t.eq(f.calls[2],{'/etc/init.d/dnsmasq','restart','ovpnclient2'})
  t.eq(f.calls[5],{'/etc/init.d/dnsmasq','restart','wgclient1'})
  t.truthy(string.find(f.files['/tmp/dnsmasq.d.wgclient1/'..dd.FILE],'server=103.86.99.100@ovpnclient2',1,true))
  t.eq(dd.summary(r),'DNS-DUAL-SYNC: enabled true changed 2 code none instances wgclient1+,ovpnclient2+')
  t.eq(dd.summary(dd.failed()),'DNS-DUAL-SYNC: enabled false changed 0 code DNS-DUAL-UNVERIFIED instances none')
  dd.memo={}
end)

t.test('real files: atomic write without leftovers, verified remove, oversize unreadable',function()
  local base=os.tmpname();os.remove(base)
  assert(os.execute("mkdir -p '"..base.."'"))
  local path=base..'/'..dd.FILE
  dd.default_io.write(path,'all-servers\n')
  t.eq(dd.default_io.read(path),'all-servers\n')
  local p=io.popen("ls -A '"..base.."'");local listing=p:read('*a');p:close()
  t.eq(listing,dd.FILE..'\n','no temporary file left')
  dd.default_io.remove(path);dd.default_io.remove(path)
  t.eq(dd.default_io.read(path),nil)
  local f=assert(io.open(path,'wb'));f:write(string.rep('x',dd.MAX_TEXT+1));f:close()
  t.eq(dd.default_io.read(path),nil)
  t.truthy(not pcall(dd.default_io.write,base..'/missing/x','y'))
  os.execute("rm -rf '"..base.."'")
end)

t.run()
