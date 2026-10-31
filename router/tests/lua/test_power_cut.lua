-- Power-cut integrity (POWER-CUT-INTEGRITY-2026-10-31.ru.md):
--  1. durable.write on a pessimistic flash model: a cut after every step leaves the old or the new file, never a
--     mix, an empty or a zero-filled one; after write() returns only the new one; failures leave no .pending
--  2. sweep() removes only old .pending leftovers; quarantine() keeps damaged bytes once, bounded
--  3. readers: every truncation, zero fill, empty and missing file of the journal / state / history / accounting
--     files ends in a known state (a coded refusal or the backup), never a plain Lua error (a restart loop)
--  4. a power cut before every durable step (flash file write, UCI change) of five switch flows, then the boot
--     recovery (and a second boot): the journal is settled, the order is the one it records, the kernel follows,
--     no LAN-wide guard is left; a second cut inside the recovery itself ends the same way
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local durable=require('durable')
local T=require('transaction')
local A=require('auto')
local ctl=require('auto_control')
local recovery=require('recovery')
local pair=require('pair')
local journal=require('journal')
local P=pair.policy

------------------------------------------------------------------------------------------------------
-- 1. durable.write on a flash model
------------------------------------------------------------------------------------------------------
-- inodes with a data-synced flag; the directory as written (cur) and as on flash (dur, after fsync_dir).
local function flash_model(opts)
  opts=opts or {}
  local m={inodes={},cur={},dur={},n=0,log={},snaps={},mtime={}}
  local function copy(t_) local o={};for k,v in pairs(t_) do o[k]=v end;return o end
  local function snap()
    local inodes={}
    for id,node in pairs(m.inodes) do inodes[id]={data=node.data,synced=node.synced} end
    m.snaps[#m.snaps+1]={inodes=inodes,cur=copy(m.cur),dur=copy(m.dur),step=m.log[#m.log]}
  end
  local function step(name) m.log[#m.log+1]=name;snap() end
  local ops={}
  function ops.open_write(path)
    if opts.no_create then return nil end
    m.n=m.n+1;local id=m.n;m.inodes[id]={data='',synced=false};m.cur[path]=id;m.mtime[path]=1000;step('create')
    local file={}
    function file.write(_,text) if opts.fail_write then return nil,'ENOSPC' end;m.inodes[id].data=m.inodes[id].data..text;step('write');return true end
    function file.flush() return true end
    function file.close() end
    return file
  end
  function ops.mkdir() return true end
  function ops.chmod600() return true end
  function ops.fsync(path)
    if opts.no_fsync then return false end
    local id=m.cur[path];if not id then return false end
    if not opts.lying_fsync then m.inodes[id].synced=true end
    step('fsync');return true
  end
  function ops.fsync_dir(directory)
    if opts.no_dir_sync then return false end
    for k in pairs(m.dur) do if string.sub(k,1,#directory+1)==directory..'/' and m.cur[k]==nil then m.dur[k]=nil end end
    for k,v in pairs(m.cur) do if string.sub(k,1,#directory+1)==directory..'/' then m.dur[k]=v end end
    step('fsync_dir');return true
  end
  function ops.sync_all() if opts.no_sync_all then return false end;for _,node in pairs(m.inodes) do node.synced=true end;m.dur=copy(m.cur);step('sync');return true end
  function ops.rename(a,b) if opts.fail_rename then return nil,'EXDEV' end;m.cur[b]=m.cur[a];m.cur[a]=nil;step('rename');return true end
  function ops.remove(path) if m.cur[path]==nil then return nil end;m.cur[path]=nil;step('remove');return true end
  function ops.dir(directory)
    local out={}
    for k in pairs(m.cur) do local d,n=string.match(k,'^(.*)/([^/]+)$');if d==directory then out[#out+1]=n end end
    return out
  end
  function ops.lstat(path) local id=m.cur[path];if not id then return nil end;return {type='reg',size=#m.inodes[id].data,mtime=m.mtime[path] or 0} end
  function ops.now() return 1000 end
  -- an existing, fully durable file
  function m.seed(path,text) m.n=m.n+1;m.inodes[m.n]={data=text,synced=true};m.cur[path]=m.n;m.dur[path]=m.n end
  -- every content a reader may find at `path` after a power cut in this snapshot (nil = no file)
  function m.outcomes(s,path)
    local out={}
    for _,id in ipairs({s.cur[path] or false,s.dur[path] or false}) do
      if not id then out['<missing>']=true
      else
        local node=s.inodes[id]
        out[node.data]=true
        if not node.synced then out['']=true;out[string.rep('\0',#node.data)]=true end
      end
    end
    return out
  end
  m.ops=ops
  return m
end
local function with_ops(ops,fn)
  local saved=durable.ops;durable.ops=ops
  local ok,err=pcall(fn)
  durable.ops=saved
  if not ok then error(err,0) end
end

local OLD,NEW='{"v":"old version"}','{"v":"new version, longer than the old one"}'
local TARGET='/etc/hv/native-transaction.json'

t.test('durable.write: a cut after any step leaves the old or the new file; after return only the new one',function()
  local m=flash_model()
  m.seed(TARGET,OLD)
  with_ops(m.ops,function() durable.write(TARGET,NEW) end)
  t.eq(m.log,{'create','write','fsync','rename','fsync_dir'},'steps in order')
  for i,s in ipairs(m.snaps) do
    for text in pairs(m.outcomes(s,TARGET)) do
      t.truthy(text==OLD or text==NEW,'cut after step '..i..' ('..s.step..') can leave '..string.format('%q',string.sub(text,1,20)))
    end
  end
  local final=m.outcomes(m.snaps[#m.snaps],TARGET)
  t.eq(next(final),NEW);t.eq(next(final,NEW),nil,'durable once write() returned')
  -- one .pending existed between create and rename; none after
  local names=m.ops.dir('/etc/hv');t.eq(#names,1)
end)

t.test('the flash model catches a writer without the file fsync (sanity of the model)',function()
  local m=flash_model({lying_fsync=true})
  m.seed(TARGET,OLD)
  with_ops(m.ops,function() durable.write(TARGET,NEW) end)
  local bad=false
  for _,s in ipairs(m.snaps) do for text in pairs(m.outcomes(s,TARGET)) do if text~=OLD and text~=NEW then bad=true end end end
  t.truthy(bad,'an unsynced rename may leave an empty or zero-filled file: the order fsync -> rename matters')
end)

t.test('durable.write without nixio: `sync` before the rename and after it',function()
  local m=flash_model({no_fsync=true,no_dir_sync=true})
  m.seed(TARGET,OLD)
  with_ops(m.ops,function() durable.write(TARGET,NEW) end)
  t.eq(m.log,{'create','write','sync','rename','sync'})
  for _,s in ipairs(m.snaps) do for text in pairs(m.outcomes(s,TARGET)) do t.truthy(text==OLD or text==NEW) end end
end)

t.test('durable.write failures: the target is unchanged and no .pending is left',function()
  for _,case in ipairs({{fail_write=true},{fail_rename=true},{no_fsync=true,no_sync_all=true}}) do
    local m=flash_model(case)
    m.seed(TARGET,OLD)
    local ok=pcall(with_ops,m.ops,function() durable.write(TARGET,NEW) end)
    t.eq(ok,false)
    t.eq(m.inodes[m.cur[TARGET]].data,OLD)
    t.eq(#m.ops.dir('/etc/hv'),1,'only the target')
  end
  local m=flash_model({no_create=true})
  t.eq(pcall(with_ops,m.ops,function() durable.write(TARGET,NEW) end),false)
  t.eq(pcall(durable.write,'/etc/hv/../x','1'),false,'unsafe path')
  t.eq(pcall(durable.write,'relative/x','1'),false,'relative path')
end)

t.test('durable.write in RAM: no fsync at all; sync=true forces it',function()
  local m=flash_model()
  with_ops(m.ops,function() durable.write('/var/run/homensai-vpn/status.json','{}') end)
  t.eq(m.log,{'create','write','rename'})
  m=flash_model()
  with_ops(m.ops,function() durable.write('/etc/hv/x.json','{}',{sync=false}) end)
  t.eq(m.log,{'create','write','rename'})
end)

------------------------------------------------------------------------------------------------------
-- 2. sweep / quarantine / damage
------------------------------------------------------------------------------------------------------
t.test('sweep removes only .pending leftovers older than the age, in both clock directions',function()
  local m=flash_model()
  m.seed('/etc/hv/.native-transaction.json.0a1b-3.pending','{"half')
  m.seed('/etc/hv/.checkpoint.json.k2x_9q1.pending','')              -- Python mkstemp name
  m.seed('/etc/hv/.native-history.json.ff-1.pending','x')
  m.seed('/etc/hv/native-transaction.json',OLD)
  m.seed('/etc/hv/notes.pending','x')                                  -- not ours: no leading dot
  m.mtime['/etc/hv/.native-transaction.json.0a1b-3.pending']=1000-500  -- old
  m.mtime['/etc/hv/.checkpoint.json.k2x_9q1.pending']=1000+5000        -- clock went back at boot
  m.mtime['/etc/hv/.native-history.json.ff-1.pending']=1000-10         -- a writer running now
  m.mtime['/etc/hv/notes.pending']=0
  local removed
  with_ops(m.ops,function() removed=durable.sweep('/etc/hv') end)
  t.eq(removed,2)
  local names=m.ops.dir('/etc/hv');table.sort(names)
  t.eq(names,{'.native-history.json.ff-1.pending','native-transaction.json','notes.pending'})
  t.eq(m.log[#m.log],'fsync_dir','the removals are made durable')
  with_ops(flash_model().ops,function() t.eq(durable.sweep('/nonexistent'),0) end)
end)

t.test('damage kinds and quarantine: once per content, bounded, never raises',function()
  t.eq(durable.damage(''),'EMPTY');t.eq(durable.damage(string.rep('\0',40)),'ZERO-FILLED');t.eq(durable.damage('{"a"\0'),'BINARY')
  t.eq(durable.damage('{"a":'),nil);t.eq(durable.damage(nil),nil)
  local fs=t.memory_fs()
  local log=durable.log;local lines={};durable.log=function(l) lines[#lines+1]=l end
  local copy=durable.quarantine('/etc/hv/native-stop.json','{"requ',ctl.DAMAGED,fs)
  t.truthy(copy and string.find(copy,'^/etc/hv/quarantine/native%-stop%.json%.%x+%.damaged$'),copy)
  t.eq(fs.files[copy],'{"requ')
  t.eq(durable.quarantine('/etc/hv/native-stop.json','{"requ',ctl.DAMAGED,fs),copy)
  t.eq(#lines,1,'one log line per damaged content');t.truthy(string.find(lines[1],'STATE-FILE-DAMAGED native-stop.json UNPARSEABLE 6 bytes',1,true),lines[1])
  t.eq(durable.quarantine('/etc/hv/../x','x',nil,fs),nil)
  local m=flash_model()
  for i=1,durable.QUARANTINE_LIMIT+3 do
    with_ops(m.ops,function() durable.quarantine('/etc/hv/native-stop.json','damaged '..i) end)
  end
  t.eq(#m.ops.dir('/etc/hv/quarantine'),durable.QUARANTINE_LIMIT)
  durable.log=log
end)

------------------------------------------------------------------------------------------------------
-- 3. readers of damaged files
------------------------------------------------------------------------------------------------------
local function wired(opts)
  local env=t.env(opts)
  env.deps.rollback_recovery=recovery.helpers()
  env.deps.activation_finalize=function(e,state,value,allow) return recovery.finalize(e,state,value,allow) end
  env.net={}
  return env
end
local function pair_attempt(env,extra)
  local opts={control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})}
  for k,v in pairs(extra or {}) do opts[k]=v end
  return T.attempt(env,env.backend.selection,env.run.wall()+3600,false,opts)
end
-- every damaged form of `text`: each strict prefix, the same length zero-filled, one flipped byte in the middle
local function damaged_forms(text)
  local out={}
  for n=0,#text-1 do out[#out+1]=string.sub(text,1,n) end
  out[#out+1]=string.rep('\0',#text)
  out[#out+1]=string.rep('\0',4096)
  local mid=math.floor(#text/2)
  out[#out+1]=string.sub(text,1,mid-1)..string.char((string.byte(text,mid)+1)%256)..string.sub(text,mid+1)
  return out
end
local function plain_error(err) return type(err)~='table' end

t.test('journal: every truncation / zero fill / flipped byte is JOURNAL-INTEGRITY-FAILED; missing is {}',function()
  local env=t.env()
  pair_attempt(env)
  local path=env.persist..'/native-transaction.json'
  local good=env.run.fs.files[path]
  t.truthy(#good>1000,'a full journal')
  for _,text in ipairs(damaged_forms(good)) do
    env.run.fs.files[path]=text
    local ok,err=pcall(T.journal_read,env)
    t.truthy(not ok and type(err)=='table' and err.code=='JOURNAL-INTEGRITY-FAILED','length '..#text..': '..tostring(ok and 'read' or (type(err)=='table' and err.code or err)))
  end
  env.run.fs.files[path]=nil
  t.eq(T.journal_read(env),canon.object({}))
  env.run.fs.files[path]=good
  t.eq(T.journal_read(env).phase,'COMMITTED')
end)

t.test('state files read by the supervisor: damaged -> STATE-FILE-DAMAGED + one quarantine copy; missing -> default',function()
  local env=t.env()
  local log=durable.log;durable.log=function() end
  local stop=env.persist..'/native-stop.json'
  local good=canon.encode(canon.object({requested=canon.float(1761830000),trial=t.HEX32,source='manual'}))
  local copies={}
  for _,text in ipairs(damaged_forms(good)) do
    env.run.fs.files[stop]=text
    local ok,value=pcall(ctl.read_json,env.run,stop,canon.object({}))
    if ok then
      t.truthy(canon.is_object(value) or canon.is_array(value) or type(value)~='table','decodable prefix '..#text)
    else
      t.truthy(type(value)=='table' and value.code==ctl.DAMAGED,'length '..#text..': '..tostring(type(value)=='table' and value.code or value))
      t.truthy(ctl.is_refused(value),'a coded refusal: the iteration keeps running')
    end
    t.eq(ctl.read_json_safe(env.run,stop,'default')~=nil,true)
  end
  for p in pairs(env.run.fs.files) do if string.find(p,'/quarantine/') then copies[#copies+1]=p end end
  t.truthy(#copies>=#good-2,'one copy per distinct damaged content ('..#copies..')')
  env.run.fs.files[stop]=nil
  t.eq(ctl.read_json(env.run,stop,'default'),'default')
  -- RAM files are refused the same way but never copied to flash
  env.run.fs.files['/var/run/x/status.json']='{"tim'
  t.code(ctl.DAMAGED,ctl.read_json,env.run,'/var/run/x/status.json',canon.object({}))
  t.eq(env.run.fs.files['/var/run/x/quarantine/status.json'],nil)
  durable.log=log
end)

t.test('pair state: every damaged form is a coded refusal; pair.recover publishes it instead of raising',function()
  local env=t.env()
  local log=durable.log;durable.log=function() end
  local state=canon.object({id=string.rep('11',16),phase='RUNNING',started=canon.float(1),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),owned=canon.array({'wgclient1'}),before_flags=canon.object({wgclient1='1',ovpnclient1='0'}),
    order=canon.array({'r1','r2'}),policy_hash=t.HEX64,policy_roles=P.proof(t.selection())})
  pair.save(env,state)
  local path=env.persist..'/pair-auto-state.json'
  local good=env.run.fs.files[path]
  for _,text in ipairs(damaged_forms(good)) do
    env.run.fs.files[path]=text
    local ok,err=pcall(pair.read_state,env)
    t.truthy(not ok and not plain_error(err),'length '..#text..': '..tostring(err))
  end
  env.run.fs.files[path]=''
  local ok,result=pcall(pair.recover,env)
  t.truthy(ok,'pair.recover never raises: '..tostring(result))
  t.eq(t.read(env,env.runtime..'/native-status.json').state,'BLOCKED')
  durable.log=log
end)

t.test('history: a damaged main falls back to the backup; both damaged is HISTORY-CORRUPT (coded), never a Lua error',function()
  local env=t.env()
  pair_attempt(env)
  local main,backup=env.persist..'/native-history.json',env.persist..'/native-history.backup.json'
  local good_main,good_backup=env.run.fs.files[main],env.run.fs.files[backup]
  local H=require('history')
  local forms=damaged_forms(good_main)
  for i=1,#forms,37 do  -- every 37th offset keeps the run short; the journal test covers every offset
    H.forget_resident()
    env.run.fs.files[main]=forms[i];env.run.fs.files[backup]=good_backup
    local h=H.new(env,env.persist,10000)
    local ok,data=pcall(h.load,h)
    t.truthy(ok and canon.is_object(data) and h.restored==true,'main length '..#forms[i])
  end
  H.forget_resident()
  env.run.fs.files[main]='';env.run.fs.files[backup]=string.rep('\0',100)
  local h=H.new(env,env.persist,10000)
  local ok,err=pcall(h.load,h)
  t.truthy(not ok and type(err)=='table' and err.code=='HISTORY-CORRUPT',tostring(type(err)=='table' and err.code or err))
  H.forget_resident()
end)

t.test('monitor files: accounting checkpoint falls back to its backup; ping history to -UNAVAILABLE',function()
  local accounting=require('accounting')
  local responses=require('response_history')
  local files={}
  local runner={read_file=function(p) return files[p] end,write_atomic=function(p,text) files[p]=text end,wall=function() return 1761830400 end}
  local acc=accounting.new()
  accounting.checkpoint(runner,'/etc/hv',acc)
  accounting.checkpoint(runner,'/etc/hv',acc)
  local good=files['/etc/hv/checkpoint.json']
  t.truthy(files['/etc/hv/checkpoint.backup.json'],'a backup exists')
  for _,text in ipairs({'',string.sub(good,1,#good-1),string.rep('\0',#good)}) do
    files['/etc/hv/checkpoint.json']=text
    local ok,restored,code=pcall(accounting.restore,runner,'/etc/hv')
    t.truthy(ok and restored~=nil,'restore ran');t.eq(code,'STORAGE-RECOVERED')
  end
  files['/etc/hv/checkpoint.backup.json']=''
  local ok,restored,code=pcall(accounting.restore,runner,'/etc/hv')
  t.truthy(ok and restored~=nil);t.eq(code,'STORAGE-001')
  local io_={read_json=function(p) local text=files[p];if text==nil then return nil end;return canon.decode(text) end}
  files['/etc/hv/ping.json']=string.rep('\0',64)
  t.eq(responses.load(io_,'/etc/hv/ping.json').notice,responses.PREFIX..'-UNAVAILABLE')
end)

------------------------------------------------------------------------------------------------------
-- 4. a power cut before every durable step of a switch, then the boot recovery
------------------------------------------------------------------------------------------------------
local function copy_list(list) local o={};for i,x in ipairs(list) do o[i]=x end;return o end
local function deep(v) return canon.decode(canon.encode(v)) end

-- Counts the durable steps of env (flash files under persist, UCI changes: the route_policy order and the own
-- config options) and keeps what is on flash just before step `cut` - what the router finds after a cut there.
local function instrument(env,cut)
  local rec={n=0,snap=nil}
  local fs,B=env.run.fs,env.backend
  local function on_flash(p) return string.sub(p,1,#env.persist+1)==env.persist..'/' end
  local store={uci=B.uci}
  local function snapshot()
    local files={}
    for p,text in pairs(fs.files) do if on_flash(p) then files[p]=text end end
    rec.snap={files=files,uci=copy_list(store.uci),settings=deep(B.settings)}
  end
  local function tick() rec.n=rec.n+1;if rec.n==cut then snapshot() end end
  local write,rename,remove=fs.write_atomic,fs.rename,fs.remove
  fs.write_atomic=function(p,text) if on_flash(p) then tick() end;return write(p,text) end
  fs.rename=function(a,b) if on_flash(b) then tick() end;return rename(a,b) end
  fs.remove=function(p) if on_flash(p) and fs.files[p]~=nil then tick() end;return remove(p) end
  B.uci=nil
  setmetatable(B,{__index=function(_,k) if k=='uci' then return store.uci end end,
    __newindex=function(tb,k,v) if k=='uci' then tick();store.uci=v else rawset(tb,k,v) end end})
  for _,name in ipairs({'write_lease','clear_native_options'}) do
    local fn=B[name];B[name]=function(...) tick();return fn(...) end
  end
  rec.finish=function() if not rec.snap then snapshot() end;return rec.snap end
  return rec
end

-- the router after the boot: the flash snapshot, the kernel rebuilt from UCI by the vendor, no nft guard, empty RAM
local function boot(snap)
  local env=wired({settings=deep(snap.settings)})
  for p,text in pairs(snap.files) do env.run.fs.files[p]=text end
  env.backend.uci=copy_list(snap.uci);env.backend.kernel=copy_list(snap.uci)
  env.run.mono_now=25  -- uptime
  return env
end

local SETTLED={['ROLLED-BACK']=true,COMMITTED=true,['HELD-ON-RESERVE']=true}
local PRIMARY,RESERVE='r1,r2','r2,r1'
-- the safety properties after a boot recovery; returns a short outcome for the table
local function check_recovered(env,label)
  local j=T.journal_read(env)
  local B=env.backend
  local order=table.concat(B.uci,',')
  t.eq(table.concat(B.kernel,','),order,label..': kernel follows UCI')
  t.truthy(order==PRIMARY or order==RESERVE,label..': a known order '..order)
  if j.phase==nil then
    t.eq(order,PRIMARY,label..': no journal, primary order')
  else
    t.truthy(SETTLED[j.phase],label..': settled journal, got '..tostring(j.phase))
    if j.phase=='ROLLED-BACK' and j.abandoned~=true then
      t.eq(order,table.concat(j.restored_order~=nil and j.restored_order or j.before,','),label..': restored order')
    elseif j.phase~='ROLLED-BACK' then
      t.eq(order,table.concat(j.after,','),label..': committed order')
      -- COMMITTED keeps the VPN-only guard; a manual HELD-ON-RESERVE runs without one (as before the cut)
      if j.phase=='COMMITTED' then t.truthy(B.guarded,label..': VPN-only guard on the reserve') end
    end
  end
  if B.guarded then t.eq(B.guard_calls[#B.guard_calls],'vpn-only',label..': the guard left is VPN-only, never a LAN-wide block') end
  return (j.phase or 'none')..(j.abandoned==true and '/abandoned' or '')..' '..order
end

local function setup_committed(env) pair_attempt(env) end
local function setup_held(env) pair_attempt(env,{manual_request_id=string.rep('ab',16),request_source='manual',pair_destination='target'}) end
local FLOWS={
  {'automatic switch to the reserve',nil,function(env) pair_attempt(env) end},
  {'switch whose kernel write fails (rollback inside the transaction)',nil,function(env) env.backend.fail_apply='VENDOR-APPLY-FAILED';pair_attempt(env) end},
  {'manual switch (instant path) to HELD-ON-RESERVE',nil,function(env) setup_held(env) end},
  {'return to the primary from COMMITTED',setup_committed,function(env) T.finish_committed(env,T.journal_read(env),'PRIMARY-STABLY-RECOVERED') end},
  {'operator return from HELD-ON-RESERVE',setup_held,function(env)
    local j=T.journal_read(env)
    T.handle_return(env,j,canon.object({time=canon.float(env.run.wall()),tx=j.tx}),0,nil) end},
}

local function run_flow(flow,cut)
  local env=wired()
  if flow[2] then flow[2](env);env.run.advance(60) end
  local rec=instrument(env,cut)
  pcall(flow[3],env)
  return rec.n,rec.finish()
end

local report={}
for _,flow in ipairs(FLOWS) do
  t.test('power cut before every durable step: '..flow[1],function()
    local log=durable.log;durable.log=function() end
    local total=run_flow(flow,math.huge)
    t.truthy(total>=3,'the flow has durable steps ('..total..')')
    local outcomes={}
    for cut=1,total+1 do
      local _,snap=run_flow(flow,cut)
      local env=boot(snap)
      local ok,result=pcall(A.recover,env)
      t.truthy(ok,flow[1]..' cut '..cut..': recover raised '..tostring(type(result)=='table' and result.code or result))
      t.eq(result,'ready',flow[1]..' cut '..cut)
      local outcome=check_recovered(env,flow[1]..' cut '..cut)
      -- a second boot right after the recovery changes nothing
      local again=boot({files=(function() local f={};for p,x in pairs(env.run.fs.files) do if string.sub(p,1,#env.persist+1)==env.persist..'/' then f[p]=x end end;return f end)(),
        uci=env.backend.uci,settings=env.backend.settings})
      local ok2,result2=pcall(A.recover,again)
      t.truthy(ok2 and result2=='ready',flow[1]..' cut '..cut..': second boot '..tostring(result2))
      t.eq(check_recovered(again,flow[1]..' cut '..cut..' second boot'),outcome)
      outcomes[#outcomes+1]=cut..':'..outcome
    end
    report[#report+1]=flow[1]..' ('..total..' steps) -> '..table.concat(outcomes,' | ')
    durable.log=log
  end)
end

t.test('a second power cut inside the boot recovery (every step of it) still ends settled',function()
  local log=durable.log;durable.log=function() end
  local flow=FLOWS[1]
  local total=run_flow(flow,math.huge)
  local runs=0
  for cut=1,total+1 do
    local _,snap=run_flow(flow,cut)
    local probe=boot(snap)
    local rec=instrument(probe,math.huge);pcall(A.recover,probe)
    for cut2=1,rec.n+1 do
      local env=boot(snap)
      local inner=instrument(env,cut2)
      pcall(A.recover,env)
      local final=boot(inner.finish())
      local ok,result=pcall(A.recover,final)
      t.truthy(ok and result=='ready','cut '..cut..'/'..cut2..': '..tostring(type(result)=='table' and result.code or result))
      check_recovered(final,'cut '..cut..'/'..cut2)
      runs=runs+1
    end
  end
  t.truthy(runs>total,'nested cuts ran ('..runs..')')
  durable.log=log
end)

t.test('boot with a COMMITTED journal before the tunnels are up: bounded wait, then the guard; no tunnel -> no guard, no error',function()
  local env=wired();pair_attempt(env)
  local _,snap=(function() local r=instrument(env,math.huge);return 0,r.finish() end)()
  local b=boot(snap)
  local calls=0
  b.backend.devices=function() calls=calls+1;if calls<4 then return {} end;return {'wgclient1'} end
  t.eq(A.recover(b),'ready');t.eq(calls,4);t.eq(b.backend.guard_calls,{'vpn-only'})
  t.eq(T.journal_read(b).phase,'COMMITTED')
  b=boot(snap)
  b.backend.devices=function() return {} end
  local lines={};local log=durable.log;durable.log=function(l) lines[#lines+1]=l end
  t.eq(A.recover(b),'ready');t.eq(b.backend.guarded,false,'no LAN-wide block')
  t.truthy(b.run.clock()-25>=A.BOOT_DEVICE_WAIT,'waited the bounded time')
  t.truthy(string.find(lines[1] or '','GUARD-DEVICE-UNAVAILABLE',1,true),'logged')
  durable.log=log
end)

t.test('boot with a damaged journal: quarantine copy, one timed block, then give_up with the VPN-only guard',function()
  local env=wired()
  local log=durable.log;durable.log=function() end
  env.run.fs.files[env.persist..'/native-transaction.json']=string.rep('\0',1800)
  env.stopped=true
  t.eq(A.recover(env),'stopped')
  t.eq(env.backend.guard_calls,{'full','vpn-only'},'the timed block is replaced at once by the VPN-only guard')
  local copied=false
  for p in pairs(env.run.fs.files) do if string.find(p,'/quarantine/native%-transaction%.json%.') then copied=true end end
  t.truthy(copied,'damaged journal kept for the maintainer')
  t.eq(t.read(env,env.runtime..'/native-status.json').alarm,'JOURNAL-INTEGRITY-FAILED')
  durable.log=log
end)

t.test('outcome table (printed for the documentation)',function()
  for _,line in ipairs(report) do io.stdout:write('  ',line,'\n') end
end)

t.run()
