-- net.set_disabled with a fake router (backend_fake.lua): F-24 / D11 - the UCI network write is a bounded child of
-- the supervisor (Python: subprocess.run(['lua','-e',NETWORK_WRITE], timeout=8)), dispatched through
-- backend.network_dispatch (writer record on flash, spawn under the control lock, wait outside it), never run in
-- this process while the lock is held. The error codes of the old in-process path are kept.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
package.preload['sys']=function() return {} end
local canon=require('canon')
local fake=require('backend_fake')
local backend_mod=require('backend')
local net=require('net')
local NOW=1761830400
local REVISION=string.rep('7',32)

local function O(t_) return canon.object(t_) end
local function A(t_) return canon.array(t_) end

local function rows()
  return A({O({['.name']='wgclient1',['.type']='interface',proto='wgclient',disabled='0',config='peer_2'}),
            O({['.name']='ovpnclient2',['.type']='interface',proto='ovpnclient',disabled='1',config='current'}),
            O({['.name']='lan',['.type']='interface',proto='static'})})
end
local MANAGED=O({wgclient1='wgclient',ovpnclient2='ovpnclient'})

-- a world whose `sh -c 'exec lua <script> <<job>'` child is the fake handler: it reads the job file of the stage
-- directory, checks the written source is NETWORK_WRITE and applies the one change to the network read
local function world(child)
  local w={wall=NOW,clock=1000,runtime='/run/hv',files={['/etc/glversion']='4.11.0\n'},dirs={['/var/run']={},['/proc']={}},
    ubus={},commands={},scripts={},chunks={},mtimes={},network=rows(),children={},in_lock=false,waits_in_lock=0}
  for _,name in ipairs(net.CONFIGS) do w.files['/etc/config/'..name]="config x '"..name.."'\n" end
  w.chunks['pair_network_read']=function() return canon.encode(w.network) end
  w.handler=function(argv,opts,S)
    if argv[1]~='sh' or argv[2]~='-c' then return nil end
    local script,job=string.match(argv[3],'^exec lua (%S+) <(%S+)$')
    if not script then return nil end
    w.children[#w.children+1]={script=script,job=job,timeout=opts and opts.timeout,source=w.files[script],payload=w.files[job]}
    return child(w,w.children[#w.children])
  end
  return w
end
local function backend(w)
  local sys=fake.new(w)
  local B=backend_mod.new(sys)
  local env={run={wall=sys.wall,clock=sys.clock,
    lock=function(fn) w.in_lock=true;local ok,err=pcall(fn);w.in_lock=false;if not ok then error(err,0) end;return err end,
    require_revision=function(r) if r~=REVISION then error(setmetatable({code='CLIENT-STOP'},require('auto_control').Refused),0) end end,
    fenced=function(r,fn) return fn() end,fs={read=function(p) return w.files[p] end,key=function(p) return sys.key(p) end,
      write_atomic=function(p,text) w.files[p]=text end,unsafe=function() return false end}},
    runtime='/run/hv',persist='/etc/hv',stop=function() return false end,sleep=function() end}
  -- the wait of a writer must happen outside the control lock (Python holds the lock only for 8 s of the child;
  -- the Lua supervisor must not hold it for an unbounded in-process write)
  local real_wait=sys.wait
  sys.wait=function(handle,seconds) if w.in_lock then w.waits_in_lock=w.waits_in_lock+1 end;return real_wait(handle,seconds) end
  -- the fake's dir() knows only declared directories; the stage cleanup lists the files written into it
  sys.dir=function(path)
    local names={}
    for p in pairs(w.files) do local n=string.match(p,'^'..string.gsub(path,'%-','%%-')..'/([^/]+)$');if n then names[#names+1]=n end end
    if #names==0 and not w.dirs[path] then return nil end
    return names
  end
  B.bind(env);env.backend=B
  w.files['/run/hv/auto-control-revision.json']=canon.encode(O({revision=REVISION}))
  -- pair.require_running: the pair state file says RUNNING for this revision
  local pair=require('pair')
  pair.require_running=function() end
  return B,sys,env
end
local function state(env)
  local data=env.net.network()
  return O({interfaces=MANAGED,network_identity=env.net.identity(data,MANAGED),protected=env.net.configs(MANAGED)})
end
-- the child that applies the job to the fake network (exit 0)
local function apply(w,child)
  local q=canon.decode(child.payload)
  for _,row in ipairs(w.network) do if row['.name']==q.interface then row.disabled=q.value end end
  return 0,''
end

t.test('the network write is a bounded child with NETWORK_WRITE and the job as files of the private stage, not an in-process chunk',function()
  local w=world(apply);local B,sys,env=backend(w)
  local s=state(env)
  env.net.set_disabled(s,'ovpnclient2','0',REVISION)
  t.eq(#w.children,1,'one child')
  local child=w.children[1]
  t.eq(child.source,net.NETWORK_WRITE,'the exact Python source as the script file')
  t.eq(child.timeout,8,'the 8 s bound of pair_auto.set_disabled')
  t.truthy(string.find(child.script,'^/run/hv/pair%-uci%-') and string.find(child.job,'^/run/hv/pair%-uci%-'),'stage files')
  local q=canon.decode(child.payload)
  t.eq(q.interface,'ovpnclient2');t.eq(q.value,'0');t.eq(q.managed,MANAGED)
  t.eq(sys.calls['chunk:pair_network_write'],nil,'never run in this process')
  t.eq(w.network[2].disabled,'0','applied')
  -- the writer ownership record was saved on flash before the spawn and removed after the confirmed exit
  local recorded=false
  for _,x in ipairs(sys.writes) do if x[1]=='atomic' and x[2]=='/etc/hv/writer-pending.json' then recorded=true end end
  t.truthy(recorded,'writer record');t.eq(w.files['/etc/hv/writer-pending.json'],nil,'record dropped')
  t.eq(w.waits_in_lock,0,'the wait happened outside the control lock')
  -- the stage directory is cleaned
  t.eq(w.files[child.script],nil);t.eq(w.files[child.job],nil)
end)

t.test('without a revision the child runs without the control lock, as in Python',function()
  local w=world(apply);local B,sys,env=backend(w)
  local locks=0
  local lock=env.run.lock
  env.run.lock=function(fn,...) locks=locks+1;return lock(fn,...) end
  env.net.set_disabled(state(env),'ovpnclient2','0')
  t.eq(locks,0);t.eq(#w.children,1)
end)

t.test('a failed child is PAIR-NETWORK-WRITE-FAILED and the stage is cleaned; a stale revision is CONTROL-REVISION-STALE before any child',function()
  local w=world(function() return 1,'' end);local B,sys,env=backend(w)
  t.code('PAIR-NETWORK-WRITE-FAILED',env.net.set_disabled,state(env),'ovpnclient2','0',REVISION)
  t.eq(#w.children,1);t.eq(w.files[w.children[1].job],nil,'stage cleaned')
  w.files['/run/hv/auto-control-revision.json']=canon.encode(O({revision=string.rep('8',32)}))
  t.code('CONTROL-REVISION-STALE',env.net.set_disabled,state(env),'ovpnclient2','0',REVISION)
  t.eq(#w.children,1,'no second child')
end)

t.test('a hung child: confirmed termination is PAIR-NETWORK-WRITE-FAILED, an unconfirmed one WRITER-UNRESOLVED',function()
  local w=world(apply);local B,sys,env=backend(w)
  sys.wait=function() return nil end
  w.terminate=true
  t.code('PAIR-NETWORK-WRITE-FAILED',env.net.set_disabled,state(env),'ovpnclient2','0',REVISION)
  t.eq(sys.terminated,1)
  w.terminate=false
  t.code('WRITER-UNRESOLVED',env.net.set_disabled,state(env),'ovpnclient2','0',REVISION)
  t.truthy(B.writer_unresolved(),'the writer stays unresolved')
end)

t.test('a write the child did not apply is PAIR-NETWORK-WRITE-UNVERIFIED',function()
  local w=world(function() return 0,'' end);local B,sys,env=backend(w)
  t.code('PAIR-NETWORK-WRITE-UNVERIFIED',env.net.set_disabled,state(env),'ovpnclient2','0',REVISION)
end)

t.run()
