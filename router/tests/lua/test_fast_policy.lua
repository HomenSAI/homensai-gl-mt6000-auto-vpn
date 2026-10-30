-- fast_policy.lua: the cases of tests/test_fast_policy.py (class Plan) plus the Lua-specific edges.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local f=require('fast_policy')
local UCI,MANGLE,replace=t.UCI,t.MANGLE,t.replace

t.test('reorders jumps and local mark in one payload',function()
  local order,localt,mark=f.uci_rules(UCI)
  t.eq({order,localt,mark},{{'4192','5841'},'10100','0xb000'})
  local payload,old,changed=f.plan(MANGLE,order,localt,mark)
  t.eq(changed,true);t.eq(old,'5841')
  local lines=f.splitlines(payload)
  t.eq({lines[1],lines[2]},{'*mangle',':ROUTE_POLICY - [0:0]'})
  local jumps={}
  for _,l in ipairs(lines) do
    if l:sub(1,15)=='-A ROUTE_POLICY' and l:find('TUNNEL',1,true) then jumps[#jumps+1]=l:match('%-j (%S+)$') end
  end
  t.eq(jumps,{'TUNNEL4192_ROUTE_POLICY','TUNNEL5841_ROUTE_POLICY'})
  local own
  for _,l in ipairs(lines) do if l:find('TUNNEL10100 rule',1,true) then own=l;break end end
  t.truthy(own:find('--set-xmark 0xb000/0xf000',1,true),'local mark rewritten')
  t.eq(lines[#lines],'COMMIT');t.eq(f.mark_of(MANGLE,old),'0x1000')
end)

t.test('exact payload bytes',function()
  local payload=f.plan(MANGLE,{'4192','5841'},'10100','0xb000')
  t.eq(payload,'*mangle\n:ROUTE_POLICY - [0:0]\n'..
    '-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000\n'..
    '-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN\n'..
    '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY\n'..
    '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY\n'..
    ':TUNNEL10100_LOCAL_POLICY - [0:0]\n'..
    '-A TUNNEL10100_LOCAL_POLICY -m comment --comment "TUNNEL10100 rule for set mark" -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j MARK --set-xmark 0xb000/0xf000\n'..
    '-A TUNNEL10100_LOCAL_POLICY -m connmark --mark 0x0/0xf000 -m mark --mark 0x0/0xf000 -m owner --gid-owner 20000 -j VPN_LOCAL_POLICY_DROP\n'..
    'COMMIT\n')
end)

t.test('already applied changes nothing',function()
  local _,_,changed=f.plan(MANGLE,{'5841','4192'},'10100','0x1000')
  t.eq(changed,false)
end)

t.test('anything unexpected falls back',function()
  for _,bad in ipairs({
      replace(MANGLE,'-j TUNNEL4192_ROUTE_POLICY\n','-j TUNNEL9999_ROUTE_POLICY\n'),
      replace(MANGLE,'-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY\n',''),
      replace(MANGLE,'--set-xmark 0x1000/0xf000\n-A TUNNEL10100_LOCAL_POLICY -m connmark','--set-xmark 0x1000/0xffff\n-A TUNNEL10100_LOCAL_POLICY -m connmark')}) do
    local err=t.raises(f.plan,bad,{'4192','5841'},'10100','0xb000')
    t.truthy(f.is_unsupported(err),'Unsupported expected')
  end
  for _,bad in ipairs({
      replace(UCI,"@rule[1].tunnel_id='5841'","@rule[1].tunnel_id='4192'"),
      replace(UCI,"gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='bad'"),
      UCI.."route_policy.@rule[2].tunnel_id='7'\n"}) do
    t.truthy(f.is_unsupported(t.raises(f.uci_rules,bad)),'Unsupported expected')
  end
end)

t.test('refusal codes',function()
  t.code('FAST-RULES',f.uci_rules,'')
  t.code('FAST-LOCAL-RULE',f.uci_rules,replace(UCI,"gl_process_vpn.enabled='1'","gl_process_vpn.enabled='0'"))
  t.code('FAST-ROUTE-CHAIN',f.plan,replace(MANGLE,'TUNNEL5841_ROUTE_POLICY\n-A ROUTE_POLICY','TUNNEL5841_ROUTE_POLICY\n-A ROUTE_POLICY -j RETURN\n-A ROUTE_POLICY'),{'4192','5841'},'10100','0xb000')
  t.code('FAST-LOCAL-CHAIN',f.plan,MANGLE,{'4192','5841'},'999','0xb000')
  t.code('FAST-MARK',f.mark_of,MANGLE,'7')
end)

t.test('rule indices sort numerically and merge leading zeros',function()
  local text="route_policy.gl_process_vpn.tunnel_id='1'\nroute_policy.gl_process_vpn.mark='0x1'\n"..
    "route_policy.@rule[10].tunnel_id='20'\nroute_policy.@rule[2].tunnel_id='30'\nroute_policy.@rule[02].enabled='1'\n"
  t.eq(f.uci_rules(text),{'30','20'})
  t.eq((f.uci_rules(text.."route_policy.@rule[3].tunnel_id='40'\nroute_policy.@rule[003].enabled='0'\n")),{'30','20'})
end)

t.test('python splitlines',function()
  t.eq(f.splitlines('a\r\nb\rc\11d\12e\28f\29g\30h\194\133i\226\128\168j\226\128\169k\n'),
       {'a','b','c','d','e','f','g','h','i','j','k'})
  t.eq(f.splitlines(''),{})
  t.eq(f.splitlines('\n\n'),{'',''})
  t.eq(f.splitlines('x\194y\226\128z'),{'x\194y\226\128z'})
end)

t.test('only the target after the last -j decides what is a jump',function()
  local commented=replace(MANGLE,'-A ROUTE_POLICY -p udp','-A ROUTE_POLICY -m comment --comment "x_ROUTE_POLICY" -p udp')
  local _,_,changed=f.plan(commented,{'4192','5841'},'10100','0xb000')
  t.eq(changed,true)
  local odd=replace(MANGLE,'-A ROUTE_POLICY -p udp','-A ROUTE_POLICY -m x -j -j _ROUTE_POLICY\n-A ROUTE_POLICY -p udp')
  t.code('FAST-ROUTE-CHAIN',f.plan,odd,{'4192','5841'},'10100','0xb000')
end)

t.test('mark_of needs a space before the -j part',function()
  local m="-A TUNNEL7_ROUTE_POLICY -j MARK --set-xmark 0x7000/0xf000\n"
  t.code('FAST-MARK',f.mark_of,m,'7')
  t.eq(f.mark_of("-A TUNNEL7_ROUTE_POLICY  -j MARK --set-xmark 0x7000/0xf000\n",'7'),'0x7000')
  t.code('FAST-MARK',f.mark_of,"-A TUNNEL7_ROUTE_POLICY x -j MARK --set-xmark 0x123456789/0xf000\n",'7')
end)

t.test('libuci reader gives what `uci show` gives',function()
  local function cursor(rows)
    return {foreach=function(_,config,kind,fn) for _,r in ipairs(rows) do if r['.type']==kind then fn(r) end end end,
            get_all=function(_,config,name) for _,r in ipairs(rows) do if r['.name']==name then return r end end end}
  end
  local rows={{['.name']='gl_process_vpn',['.type']='rule_process',tunnel_id='10100',enabled='1',mark='0xb000'},
              {['.name']='cfg01',['.type']='rule',['.anonymous']=true,tunnel_id='4192',mark='0xb000'},
              {['.name']='named',['.type']='rule',['.anonymous']=false,tunnel_id='999'},  -- uci show: route_policy.named.*
              {['.name']='cfg03',['.type']='rule',['.anonymous']=true,tunnel_id={'1','2'}},  -- a list: not matched
              {['.name']='cfg02',['.type']='rule',['.anonymous']=true,tunnel_id='5841',mark='0x1000'}}
  t.eq({f.uci_rules_from_cursor(cursor(rows))},{f.uci_rules(UCI)})
  rows[5].enabled='0'
  t.code('FAST-RULES',f.uci_rules_from_cursor,cursor(rows))
end)

t.test('line API: one split serves plan and mark_of',function()
  local lines=f.splitlines(MANGLE)
  t.eq({f.plan_lines(lines,{'4192','5841'},'10100','0xb000')},{f.plan(MANGLE,{'4192','5841'},'10100','0xb000')})
  t.eq(f.mark_of_lines(lines,'5841'),f.mark_of(MANGLE,'5841'))
end)

t.run()
