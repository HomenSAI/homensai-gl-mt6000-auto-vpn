-- kernel.lua: decode, one-pass snapshot, shlex/fields/parse_mangle, attest subset, prepare/verify.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local k=require('kernel')
local fp=require('fast_policy')
local UCI,MANGLE,replace=t.UCI,t.MANGLE,t.replace

-- The full FW3 layout attest_route expects (fixture MANGLE plus chain headers and DROP rules).
local FULL=table.concat({'*mangle',':PREROUTING ACCEPT [0:0]',':ROUTE_POLICY - [0:0]',':TUNNEL4192_ROUTE_POLICY - [0:0]',
  ':TUNNEL5841_ROUTE_POLICY - [0:0]',':TUNNEL10100_LOCAL_POLICY - [0:0]',
  '-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000',
  '-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
  '-A TUNNEL10100_LOCAL_POLICY -m comment --comment "TUNNEL10100 rule for set mark" -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000',
  '-A TUNNEL4192_ROUTE_POLICY -m comment --comment "TUNNEL4192 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000',
  '-A TUNNEL4192_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP',
  '-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000',
  '-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP','COMMIT',''},'\n')

local function rules() local o,l,m=fp.uci_rules(UCI);return {order=o,local_tunnel=l,local_mark=m} end

t.test('decode is bytes.decode(utf8, replace)',function()
  local R='\239\191\189'
  t.eq(k.decode('plain'),'plain');t.eq(k.decode('\255'),R);t.eq(k.decode('\226\128'),R)
  t.eq(k.decode('\226\128A'),R..'A');t.eq(k.decode('\224\128'),R..R);t.eq(k.decode('\237\160\128'),R..R..R)
  t.eq(k.decode('\240\159\152\128'),'\240\159\152\128');t.eq(k.decode('\244\144\128\128'),R..R..R..R)
end)

t.test('shlex.split posix rules',function()
  t.eq(k.shlex_split('-A X -m comment --comment "a b" -j Y'),{'-A','X','-m','comment','--comment','a b','-j','Y'})
  t.eq(k.shlex_split([[a"b c"d 'e\f' "g\"h\i" j\ k]]),{'ab cd','e\\f','g"h\\i','j k'})
  t.eq(k.shlex_split('x ""'),{'x',''})
  t.eq(k.shlex_split('"open'),nil);t.eq(k.shlex_split('end\\'),nil)
end)

t.test('fields normalises numbers and modules like kernel_policy.fields',function()
  local f=k.fields(k.shlex_split('-m mark -m comment --comment x --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000'))
  t.eq(f['--set-xmark'],'45056/61440');t.eq(f['--mark'],'0/61440');t.eq(f['-m'],{'mark'})
  t.code('KERNEL-POLICY-UNVERIFIED',k.fields,{'-j','A','-j','B'})
  t.code('KERNEL-POLICY-UNVERIFIED',k.fields,{'!','!','-j','A'})
  t.code('KERNEL-POLICY-UNVERIFIED',k.fields,{'--unknown','x'})
  t.code('KERNEL-POLICY-UNVERIFIED',k.fields,{'--mark','0x1234567890abcdef0'})
end)

t.test('parse_mangle and the attest subset',function()
  local chains=k.parse_mangle(k.snapshot(FULL))
  t.eq(#chains.ROUTE_POLICY,4)
  local proof=k.attest_route(chains,{'5841','4192'})
  t.eq(proof.first,'5841');t.eq(proof.marks['5841'],4096);t.eq(proof.marks['4192'],45056)
  t.code('KERNEL-POLICY-UNVERIFIED',k.attest_route,chains,{'4192','5841'})  -- wrong order
  t.code('KERNEL-POLICY-UNVERIFIED',k.attest_route,k.parse_mangle(k.snapshot(replace(FULL,'-A TUNNEL4192_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP\n',''))),{'5841','4192'})
  t.code('KERNEL-POLICY-UNVERIFIED',k.parse_mangle,k.snapshot(replace(FULL,'COMMIT\n','')))
  t.code('KERNEL-POLICY-UNVERIFIED',k.parse_mangle,k.snapshot(replace(FULL,':PREROUTING ACCEPT',':PREROUTING DROP')))
  t.code('KERNEL-POLICY-UNVERIFIED',k.parse_mangle,k.snapshot(FULL..'-A ROUTE_POLICY -j X\n'))
end)

t.test('prepare reads the snapshot once for plan and old mark; verify after the restore',function()
  local snap=k.snapshot(MANGLE)
  local plan=k.prepare(rules(),snap)
  t.eq(plan.changed,true);t.eq(plan.old_first,'5841');t.eq(plan.old_mark,'0x1000')
  t.eq(plan.payload,(fp.plan(MANGLE,{'4192','5841'},'10100','0xb000')))
  t.code('FAST-PATH-UNVERIFIED',k.verify,rules(),snap)
  local applied=k.snapshot(replace(replace(MANGLE,
    '-j TUNNEL5841_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
    '-j TUNNEL4192_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY'),
    'gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000','gid-owner 20000 -j MARK --set-xmark 0xb000/0xf000'))
  t.truthy(k.verify(rules(),applied))
  t.eq(k.prepare(rules(),applied).old_mark,nil)
  t.code('KERNEL-POLICY-UNVERIFIED',k.snapshot,string.rep('x',k.MAX_TEXT+1))
end)

t.run()
