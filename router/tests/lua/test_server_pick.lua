-- server_pick.lua: the best server inside a channel (2.1.0). The cases are shared with tests/test_server_pick.py
-- (tests/server_pick_cases.json): Lua and Python read, rank, order, plan and publish the same.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local S=require('server_pick')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local text=f:read('*a');f:close();return text end
local CASES=canon.decode(read_file(t.here..'/../server_pick_cases.json'))
local function plain(v) if v==nil or v==NULL then return nil end;return canon.is_float(v) and canon.number(v) or v end

-- Lua value (plain tables, nil) against the decoded Python value (canon tables, null)
local function same(a,e,path)
  path=path or '$'
  if e==NULL then if a~=nil and a~=NULL then error(path..': expected null, got '..t.show(a),0) end;return end
  if type(e)=='number' or canon.is_float(e) then
    if type(a)=='boolean' or canon.number(a)~=canon.number(e) then error(path..': expected '..tostring(canon.number(e))..', got '..t.show(a),0) end
    return
  end
  if type(e)~='table' then if a~=e then error(path..': expected '..t.show(e)..', got '..t.show(a),0) end;return end
  if type(a)~='table' or a==NULL then error(path..': expected a table, got '..t.show(a),0) end
  if canon.is_array(e) then
    if #a~=#e then error(path..': length '..#a..' ~= '..#e,0) end
    for i=1,#e do same(a[i],e[i],path..'['..i..']') end
    return
  end
  for k,v in pairs(e) do same(a[k],v,path..'.'..k) end
  for k,v in pairs(a) do if e[k]==nil and v~=NULL then error(path..': unexpected key '..tostring(k),0) end end
end

local function uci_of(text) return S.parse_uci(text) end

t.test('uci_values',function() for _,c in ipairs(CASES.uci_values) do same(S.uci_values(c.raw),c.expect,c.raw) end end)
t.test('parse_profiles',function() for _,c in ipairs(CASES.parse_profiles) do same(S.parse_profiles(plain(c.text)),c.expect) end end)
t.test('tunnels',function() for _,c in ipairs(CASES.tunnels) do same(S.tunnels(uci_of(c.uci)),c.expect) end end)
t.test('candidates',function()
  for _,c in ipairs(CASES.candidates) do
    local tunnel={};for k,v in pairs(c.tunnel) do tunnel[k]=plain(v) end
    same(S.candidates(tunnel,c.profiles,uci_of(c.uci)),c.expect)
  end
end)
t.test('endpoints',function() for i,c in ipairs(CASES.endpoints) do same(S.endpoints(c.protocol,c.section),c.expect,'endpoints '..i) end end)
t.test('pick_uplink',function() for i,c in ipairs(CASES.pick_uplink) do same(S.pick_uplink(plain(c.rows)),c.expect,'uplink '..i) end end)
t.test('parse_ping',function() for i,c in ipairs(CASES.parse_ping) do same(S.parse_ping(plain(c.text)),c.expect,'ping '..i) end end)
t.test('rank and decide',function()
  for i,c in ipairs(CASES.rank_decide) do
    local rows={}
    for j,r in ipairs(c.rows) do rows[j]={profile=r.profile,current=r.current,alive=plain(r.alive),latency_ms=plain(r.latency_ms),switchable=plain(r.switchable)} end
    local ranked=S.rank(rows);local names={}
    for j,r in ipairs(ranked) do names[j]=r.profile end
    same(names,c.expect_rank,'rank '..i)
    local target=S.decide(ranked)
    same(target and target.profile or nil,c.expect_target,'decide '..i)
  end
end)
t.test('plan_profiles_order',function()
  for i,c in ipairs(CASES.plan_order) do
    local ranked={};for j,r in ipairs(c.ranked) do ranked[j]={profile=r.profile,alive=plain(r.alive)} end
    t.eq(S.plan_profiles_order(c.text,plain(c.current),ranked),c.expect,'order '..i)
  end
end)
t.test('switch_plan',function()
  for i,c in ipairs(CASES.switch_plan) do
    local tunnel={};for k,v in pairs(c.tunnel) do tunnel[k]=plain(v) end
    local p=S.switch_plan(tunnel,c.target,c.enabled,c.auto_on,c.carrying,c.busy,c.left)
    same(p,c.expect,'plan '..i)
  end
end)
t.test('execute is gated by the owner switch',function()
  local ran=0
  local io_={exec=function() ran=ran+1;return 0,'' end}
  local plan=S.switch_plan({section='cfg1',protocol='wireguard',interface='wgclient1'},{group_id='1',profile_id='2'},true,true,false,false,4)
  t.eq(S.execute(plan,io_,false),'SERVER-PICK-OFF');t.eq(S.execute(plan,io_,'1'),'SERVER-PICK-OFF');t.eq(ran,0)
  t.eq(S.execute(plan,io_,true),'SERVER-PICKED');t.eq(ran,10,'WireGuard: update_provider_config as in tunnel-switch.sh')
  io_.exec=function(argv) if argv[3]=='-q' or argv[2]=='-q' then return 1,'' end;return 0,'' end
  t.eq(S.execute(plan,io_,true),'SERVER-PICKED','an absent option to delete is not a failure')
  io_.exec=function() error('boom') end
  t.eq(S.execute(plan,io_,true),'SERVER-PICK-FAILED')
end)
t.test('switchable (shared cases)',function()
  for _,c in ipairs(CASES.switchable) do t.eq(S.switchable(c.protocol,plain(c.section),uci_of(c.uci)),c.expect,c.name) end
end)
t.test('run_plan tells what a failed change touched',function()
  local plan=S.switch_plan({section='cfg1',protocol='wireguard',interface='wgclient1'},{group_id='1',profile_id='2'},true,true,false,false,4)
  local function outcome(pred,raises)
    local r=S.run_plan(plan,{exec=function(argv) if pred(argv) then if raises then error('sys: unsafe command argument',0) end;return 1,'' end;return 0,'' end},true)
    return {r.code,r.changed,r.committed,r.touched}
  end
  t.eq(outcome(function(a) return a[1]=='uci' and a[2]=='set' end),{'SERVER-PICK-FAILED',false,false,false},'the first uci set: nothing written')
  t.eq(outcome(function(a) return a[1]=='uci' and a[2]=='commit' and a[3]=='route_policy' end),{'SERVER-PICK-FAILED',true,false,false})
  t.eq(outcome(function(a) return a[1]=='sh' end,true),{'SERVER-PICK-FAILED',true,true,false},'MT3000 23:36: provider step raised')
  t.eq(outcome(function(a) return a[1]=='sh' end),{'SERVER-PICK-FAILED',true,true,false})
  t.eq(outcome(function(a) return a[1]=='ifdown' end),{'SERVER-PICK-FAILED',true,true,true})
  t.eq(outcome(function() return false end),{'SERVER-PICKED',true,true,true})
  t.eq(S.run_plan(plan,{exec=function() return 0,'' end},false).code,'SERVER-PICK-OFF')
  t.eq(S.rollback_note(true,{touched=true},{}),'rolled back')
  t.eq(S.rollback_note(false,{touched=false},{committed=true,rebound=true}),'rolled back (the tunnel was not restarted)')
  t.eq(S.rollback_note(false,{touched=true},{committed=true,rebound=true}),'rollback failed')
  t.eq(S.rollback_note(false,{touched=false},{committed=false,rebound=true}),'rollback failed')
  t.eq(S.rollback_note(false,{touched=false},{committed=true,rebound=false}),'rollback failed')
end)
t.test('every step of a WireGuard plan passes the real sys.exec; the provider step sends GL JSON (MT3000 02.11.2026 23:36)',function()
  local sys=require('sys')
  local plan=S.switch_plan({section='cfg0123ab',protocol='wireguard',interface='wgclient1'},{group_id='10004',profile_id='2000'},true,true,false,false,4)
  for _,argv in ipairs(plan.steps) do
    local line={'true'};for _,a in ipairs(argv) do line[#line+1]=a end
    local ok,rc=pcall(sys.exec,line,{timeout=5})
    t.truthy(ok,'sys.exec refused '..argv[1]..': '..tostring(rc));t.eq(rc,0,argv[1])
  end
  -- uci and ubus as shell functions in front of the script (the CI sandbox mounts its temp directories noexec)
  local fake='uci(){ case "$3" in wireguard.group_10004.group_name) echo NordVPN;; wireguard.group_7.group_name) echo Hideme;; esac; };'
    ..'ubus(){ printf "%s|%s|%s\\n" "$2" "$3" "$4"; };'  -- one line: sys.exec refuses a newline in an argument
  local function run(g,p,i)
    return sys.exec({'sh','-c',fake..S.PROVIDER_SCRIPT,'update_provider_config',g,p,i},{timeout=10})
  end
  local rc,out=run('10004','2000','wgclient1')
  t.eq(rc,0);t.eq(out,'gl-session|call|{"module":"wg_client","func":"update_provider_config","params":{"group_id":10004,"peer_id":2000,"update_all":false}}\n')
  rc,out=run('7','12','wgclient2')
  t.eq(out,'gl-session|call|{"module":"wg_client","func":"update_provider_config","params":{"group_id":7,"peer_id":12,"instance":"wgclient2","update_all":false}}\n')
  rc,out=run('8','1','wgclient1');t.eq({rc,out},{0,''},'another provider: nothing, exit 0')
end)
t.test('due',function() for i,c in ipairs(CASES.due) do t.eq(S.due(plain(c.last),c.previous,c.failed,c.clock),c.expect,'due '..i) end end)
t.test('carrying_retry',function() for i,c in ipairs(CASES.carrying_retry) do t.eq(S.carrying_retry(plain(c.picked),c.previous,c.retried,plain(c.last),c.clock),c.expect,'carrying_retry '..i) end end)
t.test('failed_interfaces',function() for _,c in ipairs(CASES.failed_interfaces) do same(S.failed_interfaces(c.profiles),c.expect) end end)
t.test('project',function()
  for i,c in ipairs(CASES.project) do
    local got=S.project(c.value)
    if c.expect==NULL then t.eq(got,nil,'project '..i) else t.eq(canon.encode(got),canon.encode(c.expect),'project '..i) end
  end
end)
t.test('events',function() for i,c in ipairs(CASES.events) do t.eq(canon.encode(S.events(c.result,c.seen)),canon.encode(c.expect),'events '..i) end end)

t.test('stage 2: request_valid, claim, gate (shared cases)',function()
  for _,c in ipairs(CASES.request_valid) do t.eq(S.request_valid(plain(c.row),plain(c.now)),c.expect,c.name) end
  for _,c in ipairs(CASES.claim) do
    local ran=canon.array({})
    local io_={exec=function(argv) local a=canon.array({});for i,x in ipairs(argv) do a[i]=x end;ran[#ran+1]=a;return c.rc,c.uci end}
    local got=S.claim(io_,c.row,100100)
    same(got,c.expect,c.name);t.eq(canon.encode(ran),canon.encode(c.exec),c.name)
  end
  for _,c in ipairs(CASES.gate) do
    local ctx={};for k,v in pairs(c.ctx) do ctx[k]=plain(v) end
    t.eq(S.gate(ctx),plain(c.expect),c.name)
  end
  t.eq(S.profile_id('openvpn','40354','2016'),'openvpn:40354_2016');t.eq(S.profile_id('wireguard','10004','2000'),'wireguard:peer_2000')
  t.eq(S.profile_id('openvpn','x','1'),nil)
end)
t.test('stage 2: rebind (shared cases)',function()
  for _,c in ipairs(CASES.rebind) do
    local ok,state,journal=pcall(S.rebind,c.state,c.journal,c.order,plain(c.hash),plain(c.target_id),plain(c.role))
    if c.expect.error then t.eq(ok,false,c.name);t.eq(state,c.expect.error,c.name)
    else
      t.truthy(ok,c.name..': '..tostring(state))
      t.eq(canon.encode(state),canon.encode(c.expect.state),c.name)
      t.eq(canon.encode(journal==nil and NULL or journal),canon.encode(c.expect.journal),c.name)
    end
  end
end)
t.test('stage 2: the job never executes a switch',function()
  for _,c in ipairs(CASES.job) do
    for _,argv in ipairs(c.expect.exec) do t.truthy(argv[1]~='ifdown' and argv[1]~='ifup' and not (argv[1]=='uci' and argv[2]=='set'),c.name) end
    t.eq(c.expect.writes['/run/'..S.STATE],nil,c.name)
  end
end)
t.test('stage 2: record and event once',function()
  local files,logs={},{}
  local io_={runtime='/run',read=function(p) return files[p] end,write=function(p,text) files[p]=text;return true end,log=function(l) logs[#logs+1]=l end}
  t.eq(S.record(io_,4192,1000),true);t.eq(S.record(io_,4192,1100,canon.object({time=1100,from='1_1',to='1_2'}),false),true)
  local state=canon.decode(files['/run/'..S.STATE])
  t.eq(state.changes,canon.object({['4192']=canon.array({1000})}));t.eq(state.last['4192'].to,'1_2')
  local tunnel={tunnel_id=4192,protocol='openvpn'}
  t.eq(S.event(io_,S.LIMIT,tunnel,1200,nil,999),true);t.eq(S.event(io_,S.LIMIT,tunnel,1210,nil,999),false,'the same refusal once')
  t.eq(S.event(io_,S.FAILED,tunnel,1220,canon.object({from='1_1',to='1_2',from_ms=48,to_ms=NULL}),999,'rolled back'),true)
  t.eq(canon.encode(S.events(canon.decode(files['/run/'..S.EVENT]),1210)),canon.encode(canon.array({canon.object({time=1220,code=S.FAILED,tunnel_id=4192})})))
  t.eq(logs[#logs],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 4192 openvpn): 1_1 -> 1_2, 48 -> ? ms; rolled back')
  t.eq(#logs,2)
end)

local function world(c)
  local w={files={},writes={},exec=canon.array({}),logs={}}
  for k,v in pairs(c.files) do w.files[k]=v end
  local fail={};for _,p in ipairs(c.write_fail or {}) do fail[p]=true end
  local alive={};for _,p in ipairs(c.alive or {}) do alive[p]=true end
  w.io={runtime='/run',
    read=function(path) return w.files[path] end,
    write=function(path,text) if fail[path] then return false end;w.files[path]=text;w.writes[path]=text;return true end,
    exec=function(argv,seconds)
      local copy=canon.array({});for i,a in ipairs(argv) do copy[i]=a end;w.exec[#w.exec+1]=copy
      if argv[1]=='uci' and argv[2]=='-q' and argv[3]=='-X' and argv[4]=='show' then
        local text=c.uci[argv[5]];if text then return 0,text end;return 1,''
      end
      if argv[1]=='ping' then
        local text=c.ping[argv[#argv]]
        return (text and string.find(text,'round-trip',1,true)) and 0 or 1,text or ''
      end
      return plain((c.rc or {})[table.concat(argv,' ')]) or 0,''
    end,
    tcp=function(host,port,timeout,device)
      w.exec[#w.exec+1]=canon.array({'tcp',host,tostring(port),device or ''})
      return plain(c.tcp[host..':'..port])
    end,
    alive=function(pid) return alive[pid]==true end,
    wan=function() return plain(c.wan) end,
    active_mark=function() return plain(c.active_mark) end,
    log=function(line) w.logs[#w.logs+1]=line end}
  return w
end

for _,c in ipairs(CASES.job) do
  t.test('job: '..c.name,function()
    local w=world(c)
    local result=S.job(w.io,c.request,plain(c.now))
    t.eq(canon.encode(result),canon.encode(c.expect.result),'result')
    local writes=canon.object();for k,v in pairs(w.writes) do writes[k]=v end
    t.eq(canon.encode(writes),canon.encode(c.expect.writes),'writes')
    t.eq(canon.encode(w.exec),canon.encode(c.expect.exec),'commands')
    same(w.logs,c.expect.logs,'logs')
  end)
end

t.test('the published file is the projection input of both monitors',function()
  local c=CASES.job[3]
  local w=world(c)
  S.job(w.io,c.request,plain(c.now))
  local projected=S.project(canon.decode(w.files['/run/server-pick.json']))
  t.eq(canon.encode(projected),canon.encode(c.expect.result))
end)

t.run()
