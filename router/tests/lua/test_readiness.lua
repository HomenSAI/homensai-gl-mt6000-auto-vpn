-- readiness.lua (system_readiness.snapshot in Lua) and its place in the monitor's status: codes, states, board
-- allowlist and bounds, the once-per-process board answer, the refresh cadence and the fake-free fallback.
-- The Python differential runs from tests/test_lua_readiness.py (--cases mode of this file).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local readiness=require('readiness')
local monitor=require('monitor')
local NULL=canon.null

-- A fake router: world.exec_board = {rc,out}; world.files[path]='reg'|'dir'; world.exec[path]=true (X_OK);
-- world.links[path]=target; world.dirs[path]={names}; world.storage={free,writable}; world.glversion=text.
local function fake(world)
  local S={calls=0}
  function S.path_env() return world.path or '/usr/sbin:/usr/bin:/sbin:/bin' end
  function S.executable(path) return world.exec[path]==true end
  function S.is_file(path) return world.files[path]=='reg' end
  function S.readlink(path) return world.links and world.links[path] or nil end
  function S.dir(path) return world.dirs and world.dirs[path] or nil end
  function S.read(path,maximum)
    if path~='/etc/glversion' or world.glversion==nil then return nil end
    if maximum and #world.glversion>maximum then error({code='OVERSIZE-FILE'},0) end
    return world.glversion
  end
  function S.storage(path)
    if path~='/etc/config' or world.storage==nil then return nil,nil end
    return world.storage[1],world.storage[2]
  end
  function S.exec(argv,opts)
    S.calls=S.calls+1
    assert(table.concat(argv,' ')=='ubus call system board' and opts.timeout==3)
    if world.board_error then error('exec failed',0) end
    return world.board[1],world.board[2]
  end
  function S.preparation(settings) S.settings=settings;return world.preparation or {scope='persistent-mt3000-preparation',state='unsupported',checks={},native_permission=false,external_lan_verified=false} end
  return S
end

local function healthy()
  return {exec={['/usr/bin/python3']=true,['/usr/bin/python3.11']=true,['/bin/ubus']=true,['/sbin/uci']=true,['/usr/bin/lua']=true,['/sbin/ip']=true},
    links={['/usr/bin/python3']='python3.11'},
    files={['/usr/libexec/rpcd/homensai-vpn']='reg',['/etc/ssl/certs/ca-certificates.crt']='reg'},
    storage={30*1048576,true},glversion='4.11.0\n',
    board={0,'{"model":"GL.iNet GL-MT3000","board_name":"glinet,mt3000-snand","serial":"private","release":{"version":"23.05-SNAPSHOT"},"hostname":"private"}'}}
end
local function states(snapshot) local out={};for _,c in ipairs(snapshot.checks) do out[c.code]=c.state end;return out end
local ORDER={'PYTHON-39-MINIMUM','DEPENDENCY-UBUS','DEPENDENCY-UCI','DEPENDENCY-LUA','DEPENDENCY-IP','RPC-PLUGIN','CA-BUNDLE','CONFIG-STORAGE-FREE'}

t.test('a healthy MT3000: every part passes in the Python order, board allowlisted, no permission',function()
  local sys=fake(healthy())
  local s=readiness.snapshot(sys,canon.object({plan_source='x'}),1761825600.5,{})
  local codes={};for i,c in ipairs(s.checks) do codes[i]=c.code;t.eq(c.state,'pass',c.code) end
  t.eq(codes,ORDER)
  t.eq(s.board,{model='GL.iNet GL-MT3000',board_name='glinet,mt3000-snand',firmware='4.11.0',openwrt='23.05-SNAPSHOT'})
  t.eq(s.native_permission,'not_assessed');t.eq(s.config_free_bytes,30*1048576);t.eq(s.config_storage_writable,true)
  t.eq(s.preparation.state,'unsupported');t.eq(sys.settings.plan_source,'x','the monitor settings reach the preparation')
  t.truthy(not string.find(canon.encode(s),'private'),'serial/hostname never leave the board allowlist')
  t.eq(canon.encode(s.time),'1761825600.5')
end)

t.test('missing parts fail, storage rules match system_readiness.py',function()
  local w=healthy();w.exec['/sbin/ip']=nil;w.files['/etc/ssl/certs/ca-certificates.crt']='dir';w.storage={30*1048576,false}
  local st=states(readiness.snapshot(fake(w),{},1,{}))
  t.eq(st['DEPENDENCY-IP'],'fail');t.eq(st['CA-BUNDLE'],'fail');t.eq(st['CONFIG-STORAGE-FREE'],'fail','read-only storage with space')
  w.storage={1048575,true};t.eq(states(readiness.snapshot(fake(w),{},1,{}))['CONFIG-STORAGE-FREE'],'fail')
  w.storage={nil,true};t.eq(states(readiness.snapshot(fake(w),{},1,{}))['CONFIG-STORAGE-FREE'],'unknown')
  w.storage=nil
  local s=readiness.snapshot(fake(w),{},1,{})
  t.eq(states(s)['CONFIG-STORAGE-FREE'],'unknown');t.eq(s.config_free_bytes,NULL);t.eq(s.config_storage_writable,NULL)
end)

t.test('Python version: link, versioned siblings, absent binary',function()
  local w=healthy();w.links={['/usr/bin/python3']='python3.8'}
  t.eq(readiness.python_state(fake(w)),'fail')
  w.links=nil;w.dirs={['/usr/bin']={'python3','python3.10','python3.8'}};w.exec['/usr/bin/python3.10']=true
  t.eq(readiness.python_state(fake(w)),'pass','the newest executable sibling')
  w.dirs={['/usr/bin']={'python3'}};t.eq(readiness.python_state(fake(w)),'unknown','present but version unproven')
  w.exec['/usr/bin/python3']=nil;t.eq(readiness.python_state(fake(w)),'fail')
end)

t.test('board: malformed, oversize, failed and partial answers; read once per process after success',function()
  for _,case in ipairs({{0,'null'},{0,'[]'},{0,string.rep('x',32769)},{1,'{}'},{0,'{bad'}}) do
    local w=healthy();w.board=case
    local b=readiness.snapshot(fake(w),{},1,{}).board
    t.eq({b.model,b.board_name,b.openwrt},{'unknown','unknown','unknown'},case[2]:sub(1,10))
  end
  local w=healthy();w.board={0,'{"model":"x86","board_name":"generic","release":null}'}
  t.eq(readiness.snapshot(fake(w),{},1,{}).board,{model='x86',board_name='generic',firmware='4.11.0',openwrt='unknown'},'release null keeps the model')
  w.board={0,'{"model":7,"board_name":null}'}
  local b=readiness.snapshot(fake(w),{},1,{}).board;t.eq({b.model,b.board_name},{'7','None'},'str() of non-strings')
  w.board_error=true;t.eq(readiness.snapshot(fake(w),{},1,{}).board.model,'unknown')
  w=healthy();local memo={};local sys=fake(w)
  readiness.snapshot(sys,{},1,memo);readiness.snapshot(sys,{},2,memo);t.eq(sys.calls,1,'board cached after success')
  w.board={1,''};sys=fake(w);memo={}
  readiness.snapshot(sys,{},1,memo);readiness.snapshot(sys,{},2,memo);t.eq(sys.calls,2,'a failure is asked again')
  w=healthy();w.glversion='4.11.0;reboot\n';t.eq(readiness.snapshot(fake(w),{},1,{}).board.firmware,'unknown')
  w.glversion=string.rep('4',257);t.eq(readiness.snapshot(fake(w),{},1,{}).board.firmware,'unknown')
end)

t.test('monitor: the status carries system_readiness, refreshed at most every READINESS_REFRESH s',function()
  local R=t.fake_runner()
  R.files['/run/hv/native-status.json']=canon.encode(canon.object({state='OBSERVING',mode='continuous-pair',time=R.now-1}))
  local sys=fake(healthy())
  local m=monitor.new(R,{readiness_sys=sys})
  local first=m:pass()
  t.eq(canon.encode(first.system_readiness.time),canon.encode(canon.float(first.time)),'computed in the pass');t.eq(#first.system_readiness.checks,8)
  local seen=canon.encode(first.system_readiness.time)
  R.advance(10);local second=m:pass()
  t.eq(canon.encode(second.system_readiness.time),seen,'reused inside the refresh window');t.eq(sys.calls,1)
  R.advance(monitor.READINESS_REFRESH);local third=m:pass()
  t.eq(canon.encode(third.system_readiness.time),canon.encode(canon.float(third.time)),'refreshed after the window')
  t.eq(sys.calls,1,'the board answer stays memoised')
  local found=false;for _,name in ipairs(third.lua_backend.native) do if name=='system_readiness' then found=true end end
  t.truthy(found,'backend record lists the native field')
  local without=monitor.new(t.fake_runner())
  t.eq(without:pass().system_readiness,nil,'no platform view: the field stays absent, never invented')
end)

-- Differential driver: tests/test_lua_readiness.py passes JSON worlds on stdin; one snapshot per line.
if arg[1]=='--cases' then
  local cases=canon.decode(io.read('*a'))
  for _,c in ipairs(cases) do
    local free,writable=nil,nil
    if c.free~=NULL then free=c.free end
    if c.writable~=NULL then writable=c.writable end
    local w={exec={},files={},links={},dirs={},glversion=c.glversion~=NULL and c.glversion or nil,storage={free,writable},
      board={c.board_rc,c.board_out},preparation={scope='persistent-mt3000-preparation',state='unsupported',checks={},native_permission=false,external_lan_verified=false}}
    for _,name in ipairs(c.binaries) do w.exec['/usr/bin/'..name]=true end
    if c.python_minor~=NULL then w.exec['/usr/bin/python3']=true;w.links['/usr/bin/python3']='python3.'..c.python_minor end
    for _,path in ipairs(c.files) do w.files[path]='reg' end
    local s=readiness.snapshot(fake(w),{},c.now,{})
    io.write(canon.encode(s),'\n')
  end
  os.exit(0)
end
t.run()
