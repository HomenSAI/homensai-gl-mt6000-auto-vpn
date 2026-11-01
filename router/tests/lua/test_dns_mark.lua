-- dns_mark.lua against a fake /proc/dns_mark tree in a temp directory (the same cases as test_dns_mark.py).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local kernel=require('kernel')
local dm=require('dns_mark')
local NULL=canon.null

local DUMP='Rule 5841: macs: none ifnames: none domains: none Mark: 0x1000\nRule 4192: macs: none ifnames: none domains: none Mark: 0xb000\n'

local function sh(path) return "'"..path.."'" end  -- test-only paths from os.tmpname()
local function put(path,text) local f=assert(io.open(path,'wb'));f:write(text);f:close() end
local function get(path) local f=io.open(path,'rb');if not f then return nil end;local s=f:read('*a');f:close();return s end
local function tree(options)
  options=options or {}
  local root=os.tmpname();os.remove(root)
  assert(os.execute('mkdir -p '..sh(root)))
  put(root..'/dump',options.dump or DUMP)
  for _,name in ipairs({'create','clear','debug'}) do put(root..'/'..name,'untouched-'..name) end
  for _,rule in ipairs({{'rule5841','0x1000'},{'rule4192','0xb000'},{'rule12x','0x1000'}}) do
    assert(os.execute('mkdir -p '..sh(root..'/'..rule[1])))
    put(root..'/'..rule[1]..'/mark',(options.marks and options.marks[rule[1]] or rule[2])..'\n')
    for _,f in ipairs({'ifnames','macs','mac_flag','domains','domain_flag','dump'}) do put(root..'/'..rule[1]..'/'..f,'') end
  end
  return root
end
local function cleanup(root) os.execute('rm -rf '..sh(root)) end
local function untouched(root)
  for _,name in ipairs({'create','clear','debug'}) do t.eq(get(root..'/'..name),'untouched-'..name,name) end
  t.eq(get(root..'/rule12x/mark'),'0x1000\n','malformed rule directory untouched')
end
local function rules(result) local out={};for i,r in ipairs(result.rules) do out[i]={r.rule,r.mark==NULL and 'null' or r.mark} end;return out end

t.test('switch to the reserve, then back to the primary',function()
  local root=tree()
  local r=dm.sync('0xb000',{root=root})
  t.eq({r.active,r.verified,r.code,r.written},{'0xb000',true,NULL,1})
  t.eq(rules(r),{{'rule5841','0xb000'},{'rule4192','0xb000'}})
  t.eq({get(root..'/rule5841/mark'),get(root..'/rule4192/mark')},{'0xb000\n','0xb000\n'})
  t.truthy(dm.last==r,'last result kept for the status')
  r=dm.sync('0x1000',{root=root})
  t.eq({r.verified,r.code,r.written},{true,NULL,2})
  t.eq(rules(r),{{'rule5841','0x1000'},{'rule4192','0x1000'}})
  untouched(root);cleanup(root)
end)

t.test('module absent: no-op, DNS-MARK-UNAVAILABLE, nothing published',function()
  dm.last=nil
  local r=dm.sync('0xb000',{root='/nonexistent/dns_mark'})
  t.eq({r.verified,r.code,r.written,#r.rules},{false,'DNS-MARK-UNAVAILABLE',0,0})
  t.eq(dm.last,nil);t.eq(dm.available({root='/nonexistent/dns_mark'}),false)
end)

t.test('value already correct: no write',function()
  local root=tree({marks={rule5841='0xb000',rule4192='45056'}})
  local r=dm.sync('0xb000',{root=root,write=function() error('must not write') end})
  t.eq({r.verified,r.code,r.written},{true,NULL,0})
  t.eq(rules(r),{{'rule5841','0xb000'},{'rule4192','0xb000'}})
  t.eq(get(root..'/rule4192/mark'),'45056\n')
  cleanup(root)
end)

t.test('write failure and a write that does not stick: DNS-MARK-UNVERIFIED',function()
  local root=tree()
  os.remove(root..'/rule4192/mark');assert(os.execute('mkdir '..sh(root..'/rule4192/mark')))
  local r=dm.sync('0x1000',{root=root})
  t.eq({r.verified,r.code,r.written},{false,'DNS-MARK-UNVERIFIED',0})
  t.eq(rules(r),{{'rule5841','0x1000'},{'rule4192','null'}})
  cleanup(root)
  root=tree()
  r=dm.sync('0xb000',{root=root,write=function() return true end})
  t.eq({r.verified,r.code,r.written},{false,'DNS-MARK-UNVERIFIED',1})
  t.eq(rules(r),{{'rule5841','0x1000'},{'rule4192','0xb000'}})
  cleanup(root)
end)

t.test('malformed values and rule names are refused',function()
  local root=tree({dump=DUMP..'Rule 12x: Mark: 0x1000\nRule -3: Mark: 0x1000\nrule 77: Mark: 0x1000\nRule 1234567890123: Mark: 0x1000\n'})
  for _,bad in ipairs({'0xB000','b000','0x','0x123456789','0xb000;reboot',45056,nil}) do
    local r=dm.sync(bad,{root=root,write=function() error('must not write') end})
    t.eq({r.active,r.verified,r.code,r.written,#r.rules},{NULL,false,'DNS-MARK-UNVERIFIED',0,0},tostring(bad))
  end
  local r=dm.sync('0xb000',{root=root})
  t.eq(rules(r),{{'rule5841','0xb000'},{'rule4192','0xb000'}})
  t.eq({dm.valid_rule('rule5841'),dm.valid_rule('rule12x'),dm.valid_rule('rule'),dm.valid_rule('../rule1')},{true,false,false,false})
  untouched(root);cleanup(root)
end)

t.test('mark file formats',function()
  t.eq({dm.parse('0x1000\n'),dm.parse('4096'),dm.parse('Mark: 0xb000'),dm.parse(' 0XB000 ')},{4096,4096,45056,45056})
  t.eq({dm.parse('0x'),dm.parse('zz'),dm.parse(''),dm.parse('0x123456789'),dm.parse(nil)},{})
  t.eq({dm.format(4096),dm.format(45056),dm.format(0),dm.format(-1),dm.format(1.5)},{'0x1000','0xb000'})
end)

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

t.test('the active mark is that of the first ROUTE_POLICY jump',function()
  t.eq(dm.active_from_chains(chains(MANGLE),kernel.fields),'0x1000')
  local swapped=MANGLE:gsub('j TUNNEL5841_ROUTE_POLICY\n%-A ROUTE_POLICY %-m addrtype ! %-%-dst%-type LOCAL %-j TUNNEL4192_ROUTE_POLICY',
    'j TUNNEL4192_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY')
  t.eq(dm.active_from_chains(chains(swapped),kernel.fields),'0xb000')
  t.eq(dm.active_from_chains({},kernel.fields),nil)
  t.eq(dm.active_from_chains(chains(MANGLE:gsub('%-j MARK %-%-set%-xmark 0x1000/0xf000','-j DROP')),kernel.fields),nil)
end)

t.test('the published block is checked',function()
  local root=tree()
  local r=dm.sync('0xb000',{root=root})
  t.eq(canon.encode(dm.project(canon.decode(canon.encode(r)))),canon.encode(r))
  for _,edit in ipairs({function(v) v.active='0xB000' end,function(v) v.code='X' end,function(v) v.verified=false end,
                        function(v) v.rules[1].rule='rule1;x' end,function(v) v.rules[1].mark='4096' end,function(v) v.written=-1 end}) do
    local v=canon.decode(canon.encode(r));edit(v);t.eq(dm.project(v),nil)
  end
  cleanup(root)
end)

t.run()
