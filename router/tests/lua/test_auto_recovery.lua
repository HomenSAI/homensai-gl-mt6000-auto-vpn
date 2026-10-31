-- Supervisor recovery with the real rollback_recovery port (recovery.lua) wired as env.deps.rollback_recovery:
-- restart in WAIT-CLIENT/APPLYING, a recorded restore step that cannot be authorized, the activation finalizer
-- refusing outside its narrow case, and Stop during the switch.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local T=require('transaction')
local R=require('rollback')
local A=require('auto')
local recovery=require('recovery')
local pair=require('pair')

local function wired(opts)
  local env=t.env(opts)
  env.deps.rollback_recovery=recovery.helpers()
  env.deps.activation_finalize=function(e,state,value,allow) return recovery.finalize(e,state,value,allow) end
  env.net={}
  return env
end
local function pair_attempt(env)
  return T.attempt(env,env.backend.selection,env.run.wall()+3600,false,{control_revision=env.revision,pair_session_order=canon.array({'r1','r2'}),
    probe_evidence=canon.object({source_streak_met=true,reserve_streak_met=true,required_failures=3,required_successes=2})})
end

t.test('restart in WAIT-CLIENT: helpers.settled() proves the restored role, journal ROLLED-BACK, guard VPN-only',function()
  local env=wired()
  pair_attempt(env)
  local j=t.journal(env);j.phase='WAIT-CLIENT';j.confirmed=nil;T.journal_write(env,j)
  local diagnostics=0
  local diagnostic=env.backend.diagnostic
  env.backend.diagnostic=function() diagnostics=diagnostics+1;return diagnostic() end
  t.eq(A.recover(env),'ready')
  j=t.journal(env)
  t.eq(j.phase,'ROLLED-BACK');t.eq(j.reason,'SUPERVISOR-RECOVERY');t.eq(j.restored_order,canon.array({'r1','r2'}))
  t.eq(env.backend.uci,{'r1','r2'});t.eq(env.backend.kernel,{'r1','r2'})
  t.truthy(diagnostics>=1,'settled() read the diagnostic')
  t.eq(env.backend.guard_calls[#env.backend.guard_calls],'vpn-only')
end)

t.test('power cut: recovery recreates the stock boot prefix before the rollback, without an Auto intent (soak trial)',function()
  local env=wired()
  pair_attempt(env)
  local j=t.journal(env);j.phase='RESTORING';T.journal_write(env,j)
  local order={}
  env.deps.rtp_boot={recovery_prefix=function() order[#order+1]='prefix';return true end}
  t.eq(A.recover(env),'ready')
  t.eq(order,{'prefix'})
  t.eq(t.journal(env).phase,'ROLLED-BACK')
end)

t.test('a failing boot prefix is logged, never an error of its own: the rollback decides',function()
  local env=wired()
  pair_attempt(env)
  local j=t.journal(env);j.phase='WAIT-CLIENT';T.journal_write(env,j)
  env.deps.rtp_boot={recovery_prefix=function() error({code='RTP-BOOT-PRECONDITION-UNVERIFIED'},0) end}
  t.eq(A.recover(env),'ready')
  t.eq(t.journal(env).phase,'ROLLED-BACK')
end)

t.test('a recorded restore step whose graph is unchanged needs authorize(): without the stopped session it refuses and counts',function()
  local env=wired()
  pair_attempt(env)
  local j=t.journal(env)
  j.phase='RESTORING';j.confirmed=nil;j.kernel_confirmed=nil
  j.restore_before_order=canon.array({'r2','r1'});j.restore_target_order=canon.array({'r1','r2'});j.restore_before_verified=true
  j.restore_kernel_fingerprint=env.backend.kernel_fingerprint()
  j.restore_order_step=recovery.order_steps(j.restore_before_order,j.restore_target_order)[1]
  T.journal_write(env,j)
  local err=t.code('KERNEL-POLICY-UNVERIFIED',R.rollback_counted,env,t.journal(env),'SUPERVISOR-RECOVERY')
  j=t.journal(env)
  t.eq(j.phase,'RESTORING');t.eq(j.rollback_failures,1)
  t.eq(env.backend.uci,{'r2','r1'},'nothing was written')
end)

t.test('order_allowed with a recorded step allows exactly its before/after orders',function()
  local j=canon.object({phase='RESTORING',before=canon.array({'a','b','c'}),after=canon.array({'b','a','c'}),restore_before_order=canon.array({'b','a','c'}),
    restore_target_order=canon.array({'a','b','c'}),restore_before_verified=true,restore_kernel_fingerprint=string.rep('f',64)})
  j.restore_order_step=recovery.order_steps(j.restore_before_order,j.restore_target_order)[1]
  t.eq(recovery.order_allowed(j,canon.array({'b','a','c'})),true)
  t.eq(recovery.order_allowed(j,canon.array({'a','b','c'})),true)
  t.eq(recovery.order_allowed(j,canon.array({'c','a','b'})),false)
  j.restore_order_step.index=7
  t.truthy(not pcall(recovery.order_allowed,j,canon.array({'a','b','c'})),'a forged step is an integrity failure')
end)

t.test('vendor rebuild applies only to our own interrupted rtp2.sh dispatch',function()
  local env=wired()
  pair_attempt(env)
  local j=t.journal(env);j.phase='APPLYING';j.confirmed=nil
  t.eq(recovery.vendor_rebuild_applies(env,j),false)
  j.failure_detail=canon.object({worker_stage='rtp-returned'})
  t.eq(recovery.vendor_rebuild_applies(env,j),false)
  j.phase='RESTORING';j.restore_proof_source='vendor-rebuild'
  t.eq(recovery.vendor_rebuild_applies(env,j),true)
end)

t.test('activation finalizer refuses a journal outside its narrow case (no write)',function()
  local env=wired()
  env.backend.sys={lstat=function() return nil end,read=function() return nil end}
  pair_attempt(env)
  local j=t.journal(env);j.phase='APPLYING';j.activation_reapply=true;j.before=j.after
  t.code('PAIR-RECOVERY-REQUIRED',recovery.finalize,env,canon.object({phase='STOPPED',owned=canon.array({})}),j,true)
  t.eq(t.journal(env).phase,'COMMITTED','unchanged')
end)

t.test('Stop during the switch with the helpers wired: CLIENT-STOP, then the restart restores the primary',function()
  local env=wired()
  env.backend.probe_ok=false
  env.backend.on_probe=function()
    env.run.fs.write_atomic(env.runtime..'/auto-control-revision.json',canon.encode(canon.object({revision=string.rep('99',16)})))
  end
  pcall(pair_attempt,env)
  local j=t.journal(env)
  t.truthy(j.phase=='ROLLED-BACK' or j.phase=='RESTORING' or j.phase=='WAIT-CLIENT','left '..tostring(j.phase))
  if j.phase~='ROLLED-BACK' then t.eq(A.recover(env),'ready');j=t.journal(env) end
  t.eq(j.phase,'ROLLED-BACK');t.eq(env.backend.uci,{'r1','r2'})
end)

-- a memory fs with fs.key: every write gets a new "inode", like a rename into place on the router
local function keyed_fs()
  local fs=t.memory_fs()
  local version,next_version,reads={},0,{}
  local write,rename,read=fs.write_atomic,fs.rename,fs.read
  fs.write_atomic=function(path,text) next_version=next_version+1;version[path]=next_version;return write(path,text) end
  fs.rename=function(a,b) version[b]=version[a];version[a]=nil;return rename(a,b) end
  fs.read=function(path) reads[path]=(reads[path] or 0)+1;return read(path) end
  fs.key=function(path) if fs.files[path]==nil then return 'absent' end;return tostring(version[path])..':'..#fs.files[path] end
  fs.reads=reads
  return fs
end

t.test('history: an unchanged publish reuses the resident copy; any rewrite of the files is seen',function()
  require('history').forget_resident()
  local fs=keyed_fs()
  local env=wired({fs=fs})
  local path=env.persist..'/native-history.json'
  T.publish(env,{state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_1',target='openvpn:1_1'})
  T.publish(env,{state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_1',target='openvpn:1_1'})
  local reads=fs.reads[path] or 0
  for _=1,5 do T.publish(env,{state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_1',target='openvpn:1_1'}) end
  t.eq(fs.reads[path] or 0,reads,'no history read while the files are unchanged')
  t.eq(#t.history(env).events,1,'one event, not seven')
  -- someone else rewrites the history (a statistics reset): the next publish reloads it
  local data=t.history(env);data.events=canon.array({})
  require('history').new(env,env.persist,10000):atomic(path,require('history').new(env,env.persist,10000):envelope(data))
  T.publish(env,{state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_1',target='openvpn:1_1'})
  t.truthy((fs.reads[path] or 0)>reads,'reloaded after the external write')
  t.eq(#t.history(env).events,0,'the reset history was used (same last state: no new event)')
  T.publish(env,{state='BLOCKED',blockers=canon.array({'OBSERVATION-STALE'})})
  t.eq(#t.history(env).events,1)
  require('history').forget_resident()
end)

t.test('status.json is decoded once per monitor write',function()
  local fs=keyed_fs()
  local env=wired({fs=fs})
  local ctl=require('auto_control')
  local path=env.runtime..'/status.json'
  fs.write_atomic(path,canon.encode(canon.object({time=1,profiles=canon.array({})})))
  local a=ctl.read_json(env.run,path,canon.object({}))
  local b=ctl.read_json(env.run,path,canon.object({}))
  t.truthy(a==b,'same decoded object');t.eq(fs.reads[path],1)
  fs.write_atomic(path,canon.encode(canon.object({time=2,profiles=canon.array({})})))
  t.eq(ctl.read_json(env.run,path,canon.object({})).time,2)
  t.eq(ctl.read_json(env.run,env.runtime..'/missing/status.json','x'),'x')
end)

t.run()
