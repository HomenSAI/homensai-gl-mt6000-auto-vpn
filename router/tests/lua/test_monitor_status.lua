-- monitor_status.lua and the status reply: switch_timing, auto_control, manual_switch, channel_path, the Python
-- bridge, native_history public, the ping response history (Diagnostics only), auto_live extras.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local page=require('monitor_status')
local monitor=require('monitor')
local responses=require('response_history')

local DIAG="config main 'main'\n\toption stats_mode 'diagnostic'\n\toption stats_until '1761900000'\n"
local WORK="config main 'main'\n\toption stats_mode 'work'\n"
local function put(R,path,value) R.write_atomic(path,canon.encode(value)) end
local function obj(t_) return canon.object(t_) end

t.test('switch_timing.read: bounds and rounding',function()
  local R=t.fake_runner();local env=page.env(R,'/run/hv','/etc/hv')
  t.eq(page.switch_timing(env),canon.null)
  put(R,'/etc/hv/switch-timing.json',obj({avg_seconds=canon.float(4.26),count=3,last_seconds=canon.float(3.9),updated=canon.float(1761825000.5)}))
  local v=page.switch_timing(env)
  t.eq(canon.encode(v),'{"avg_seconds":4.3,"count":3,"last_seconds":3.9,"updated":1761825000.5}')
  put(R,'/etc/hv/switch-timing.json',obj({avg_seconds=700,count=3}));t.eq(page.switch_timing(env),canon.null)
  put(R,'/etc/hv/switch-timing.json',obj({avg_seconds=5,count=0}));t.eq(page.switch_timing(env),canon.null)
  R.files['/etc/hv/switch-timing.json']='{bad';t.eq(page.switch_timing(env),canon.null)
end)

t.test('auto_control.public_status: modes, stop latch, return result, revision creation only with a free lock',function()
  local R=t.fake_runner();local env=page.env(R,'/run/hv','/etc/hv')
  local now=R.now
  local v=page.auto_control(env,now)
  t.eq(v.requested,'off');t.eq(v.requested_at,0);t.eq(v.request_action,'stop');t.eq(v.pair_phase,canon.null);t.eq(v.failure,canon.null)
  t.eq(v.reboot_autostart,false);t.eq(v.return_result,canon.null)
  t.truthy(type(v.control_revision)=='string' and #v.control_revision==32,'a missing revision is created under the free lock')
  local revision=v.control_revision
  t.eq(page.auto_control(env,now).control_revision,revision,'and then read back')
  put(R,'/run/hv/auto-control.json',obj({mode='on',time=now-10,['until']=now+100,request_source='manual'}))
  v=page.auto_control(env,now)
  t.eq(v.requested,'on');t.eq(v.request_action,'start');t.eq(v.requested_at,now-10);t.eq(v['until'],now+100)
  t.eq(v.request_source,'manual');t.eq(v.activation_source,'manual')
  put(R,'/etc/hv/native-stop.json',obj({requested=now-5,trial=canon.null,all_trials=true}))
  v=page.auto_control(env,now)
  t.eq(v.requested,'off','a later stop wins');t.eq(v.requested_at,now-5)
  put(R,'/run/hv/native-return-result.json',obj({request=now-3,ok=true,code=canon.null,time=now-2}))
  t.eq(page.auto_control(env,now).return_result,{request=now-3,ok=true,code=canon.null,time=now-2})
  put(R,'/run/hv/native-return-result.json',obj({request=now-3,ok='yes',time=now-2}))
  t.eq(page.auto_control(env,now).requested,'unknown','a malformed record makes the whole answer unknown')
  R.files['/run/hv/native-return-result.json']=nil
  put(R,'/etc/hv/native-stop.json',obj({requested=now-5,all_trials=true,control_revision_failed=true}))
  t.eq(page.auto_control(env,now).control_revision,canon.null)
  local R2=t.fake_runner();local env2=page.env(R2,'/run/hv','/etc/hv')
  R2.locked['auto-control.lock']=true
  t.eq(page.auto_control(env2,R2.now).control_revision,canon.null,'busy lock: no waiting, no revision yet')
  put(R2,'/run/hv/pair-auto-control.json',obj({mode='off',revision='x',time='bad'}))
  t.eq(page.public_phase(env2),'UNKNOWN','an invalid pair intent')
end)

t.test('the pair state is validated once per file version (no sha256 child per status reply)',function()
  local R=t.fake_runner();local env=page.env(R,'/run/hv','/etc/hv')
  local pair=require('pair')
  local original=pair.read_state
  local calls=0
  pair.read_state=function(e) calls=calls+1;return original(e) end
  put(R,'/etc/hv/pair-auto-state.json',obj({data=obj({phase='RUNNING'}),sha256='0'}))
  for _=1,3 do t.eq(page.public_phase(env),'UNKNOWN') end
  page.auto_control(env,R.now)
  t.eq(calls,1,'one validation for an unchanged file')
  put(R,'/etc/hv/pair-auto-state.json',obj({data=obj({phase='STOPPED'}),sha256='1'}))
  page.public_phase(env)
  t.eq(calls,2,'a new file version is validated again')
  pair.read_state=original
end)

t.test('manual_switch: the pair record, the legacy record, the choice between them',function()
  local R=t.fake_runner();local env=page.env(R,'/run/hv','/etc/hv')
  local use,value=page.manual_switch(env,obj({}),false)
  t.eq(value,{state='IDLE',completed=false});t.eq(use,false,'nothing requested: the legacy record (Python public_for_status)')
  local id=string.rep('a',32)
  put(R,'/run/hv/pair-manual-control.json',obj({id=id,pair=string.rep('b',32),revision=string.rep('c',32),direction='reserve',state='COMPLETED',
    requested=canon.float(R.now-20),updated=canon.float(R.now-10),selection=obj({tx=canon.null}),code=canon.null,request_source='manual'}))
  use,value=page.manual_switch(env,obj({mode='continuous-pair'}),false)
  t.eq(value.state,'COMPLETED');t.eq(value.completed,true);t.eq(value.request_id,id);t.eq(value.request_source,'manual');t.eq(value.code,canon.null)
  R.files['/run/hv/pair-manual-control.json']='{"id":"x"}'
  use,value=page.manual_switch(env,obj({mode='continuous-pair'}),false)
  t.eq(value,{state='UNCONFIRMED',completed=false,code='PAIR-MANUAL-STATE-UNVERIFIED'})
  R.files['/run/hv/pair-manual-control.json']=nil
  local legacy=obj({schema=1,state='REFUSED',direction='reserve',request_id=string.rep('d',32),control_revision=string.rep('e',32),
    requested_at=R.now-30,updated_at=R.now-25,trial='t1',['until']=R.now+60,source_id='wireguard:peer_7',target_id='wireguard:peer_8',
    transaction_id=canon.null,selection_hash=string.rep('1',64),vendor_identity=string.rep('2',64),settings_hash=string.rep('3',64),code='X-1'})
  put(R,'/run/hv/manual-control.json',legacy)
  use,value=page.manual_switch(env,obj({}),false)
  t.eq(use,false);t.eq(value.state,'REFUSED');t.eq(value.code,'X-1');t.eq(value.request_source,'unknown');t.eq(value.source_id,'wireguard:peer_7')
  legacy.schema=2;put(R,'/run/hv/manual-control.json',legacy)
  use,value=page.manual_switch(env,obj({}),false)
  t.eq(value.code,'MANUAL-STATE-UNVERIFIED')
end)

t.test('channel_path fallback: cached projection of the supervisor, fail-safe otherwise',function()
  local now=1761825600
  t.eq(page.channel_path_fallback(obj({state='OBSERVING'}),now).scope,'client-confirmed general VPN rule','not a pair session')
  local native=obj({mode='continuous-pair',state='OBSERVING',source='wireguard:peer_7',target='wireguard:peer_8',
    channel_path=obj({mode='continuous-pair',selection_proof='fw3-kernel-marking',source_profile_id='wireguard:peer_7',target_profile_id='wireguard:peer_8',
      active_profile_id='wireguard:peer_7',confirmed=true,kernel_policy_verified=true,checked_at=now-3})})
  local path=page.channel_path_fallback(native,now)
  t.eq(path.confirmed,true);t.eq(path.active_profile_id,'wireguard:peer_7');t.eq(path.code,canon.null)
  native.channel_path.checked_at=now-60
  path=page.channel_path_fallback(native,now)
  t.eq(path.confirmed,false,'older than 15 s: unverified');t.eq(path.code,'KERNEL-POLICY-UNVERIFIED')
  native.channel_path.checked_at=now-3;native.blockers=canon.array({'X'})
  t.eq(page.channel_path_fallback(native,now).confirmed,false,'blockers: never green')
end)

t.test('status reply: page fields, bridge pending, then the bridge answer while fresh',function()
  local R=t.fake_runner()
  put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  put(R,'/etc/hv/switch-timing.json',obj({avg_seconds=4,count=1}))
  local m=monitor.new(R)
  m:pass()
  local reply=m.rpc.handle('status','{}')
  t.eq(#R.bridge_runs,1,'the page poll started one bridge refresh');t.eq(R.bridge_runs[1],'/run/hv/status-bridge.json')
  t.eq(reply.manual_switch_control.blockers,{'PAIR-MANUAL-STATE-UNVERIFIED'});t.eq(reply.manual_switch_control.available,false)
  t.eq(reply.manual_switch.state,'IDLE');t.eq(reply.switch_timing.count,1);t.eq(reply.speed_pause,{active=false})
  t.eq(reply.channel_path.code,'KERNEL-POLICY-UNVERIFIED');t.eq(reply.speed_tests.code,'SPEED-STATUS-UNAVAILABLE')
  t.truthy(reply.auto_control.control_revision~=nil);t.eq(reply.stats_reset,canon.null)
  m.rpc.handle('status','{}')
  t.eq(#R.bridge_runs,1,'at most one refresh per 10 s')
  put(R,'/run/hv/status-bridge.json',obj({time=R.now,manual_switch_control=obj({available=true,mode='continuous-pair',blockers=canon.array()}),
    channel_path=obj({confirmed=true,active_profile_id='wireguard:peer_7'}),scan=obj({state='IDLE'}),speed_tests=obj({results=canon.array()})}))
  reply=m.rpc.handle('status','{}')
  t.eq(reply.manual_switch_control.available,true);t.eq(reply.channel_path.confirmed,true);t.eq(reply.scan,{state='IDLE'})
  R.advance(31)
  reply=m.rpc.handle('status','{}')
  t.eq(reply.manual_switch_control.available,false,'an old bridge answer is not used');t.eq(#R.bridge_runs,2)
end)

t.test('native_history public: the flash history file, cached by file key',function()
  local R=t.fake_runner()
  local env=page.env(R,'/run/hv','/etc/hv')
  local history=require('history')
  local h=history.new(env,'/etc/hv',10000,7)
  h:record({state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_7',target='wireguard:peer_8'},R.now)
  local v=page.native_history(env,7,R.now)
  t.eq(v.available,true);t.eq(v.sequence,1);t.eq(#v.events,1);t.eq(v.detail_days,7);t.eq(v.restored_from_backup,false)
  t.eq(v.event_history_truncated,false);t.eq(v.weekly_detail_complete,true);t.truthy(canon.is_object(v.weekly))
  t.truthy(page.native_history(env,7,R.now)==v,'unchanged files: the same parsed value')
  local m=monitor.new(R)
  m:pass()
  t.eq(m.rpc.handle('status','{}').native_history.events,nil,'split out of the status reply')
  t.eq(#m.rpc.handle('history','{}')['native_history.events'],1,'served by the history call')
  t.eq(#page.native_history(env,7,R.now).events,1,'the cached value keeps its events')
  R.files['/etc/hv/native-history.json']='{"broken":'
  R.versions['/etc/hv/native-history.json']=99
  v=page.native_history(env,7,R.now)
  t.eq(v.restored_from_backup,true,'a broken main file: the backup copy (the state before the first event)');t.eq(v.sequence,0)
  R.files['/etc/hv/native-history.backup.json']='{"broken":'
  R.versions['/etc/hv/native-history.backup.json']=99
  t.eq(page.native_history(env,7,R.now),{available=false,error='HISTORY-001'})
end)

t.test('ping history: filled and saved only in Diagnostics; work mode keeps nothing',function()
  local R=t.fake_runner({config=DIAG})
  put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',proof_scope='router-probed-ipv4',readiness_verified=true,
    time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  local m=monitor.new(R)
  local status=m:pass()
  t.eq(status.website_response_history.rows[1][4],0,'first pass: the vendor epoch is not settled, no echo yet')
  R.advance(10);put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',proof_scope='router-probed-ipv4',readiness_verified=true,
    time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  status=m:pass()
  local h=status.website_response_history
  t.eq(h.metric,'icmp-rtt-ms');t.eq(h.pair,{'wireguard:peer_7','wireguard:peer_8'});t.eq(#h.rows,1)
  t.eq(h.rows[1][2],123);t.eq(h.rows[1][4],1);t.eq(h.statistics.source.complete_samples,1)
  t.eq(R.files['/etc/hv/ping-response-history.json'],nil,'saved at the checkpoint interval only')
  R.advance(900);put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',proof_scope='router-probed-ipv4',readiness_verified=true,
    time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  m:pass()
  local saved=canon.decode(R.files['/etc/hv/ping-response-history.json'])
  t.eq(saved.sha256,canon.digest(saved.data));t.eq(#saved.data.rows,2)
  local loaded=responses.load(m.io,'/etc/hv/ping-response-history.json')
  t.eq(loaded.notice,nil);t.eq(#loaded.data.rows,2)
  local W=t.fake_runner({config=WORK})
  W.config_version='work'  -- stats_mode caches by the config file key
  put(W,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',proof_scope='router-probed-ipv4',readiness_verified=true,
    time=W.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  local w=monitor.new(W)
  status=w:pass()
  t.eq(#status.website_response_history.rows,0,'work mode: no rows recorded')
  W.advance(86400);w:pass();w:shutdown()
  t.eq(W.files['/etc/hv/ping-response-history.json'],nil,'work mode: never saved')
  t.truthy(W.files['/etc/hv/checkpoint.json']~=nil)
  local S=t.fake_runner({config=DIAG})
  S.inventory_data.settings.response_metric='websites'
  status=monitor.new(S):pass()
  t.eq(status.website_response_history.notice,'WEBSITE-HISTORY-UNAVAILABLE')
end)

t.test('ping history file rules: corrupt file -> UNAVAILABLE notice, never overwritten',function()
  local R=t.fake_runner()
  local m=monitor.new(R)
  R.files['/etc/hv/ping-response-history.json']='{"data":{},"sha256":"0"}'
  local h=responses.load(m.io,'/etc/hv/ping-response-history.json')
  t.eq(h.notice,'PING-HISTORY-UNAVAILABLE')
  t.eq(pcall(h.save,h,m.io,'/etc/hv/ping-response-history.json',R.now),false)
  t.eq(R.files['/etc/hv/ping-response-history.json'],'{"data":{},"sha256":"0"}')
  t.eq(pcall(responses.validate,canon.object({version=1})),false)
end)

t.test('auto_live: auto_control, cached channel_path and manual_switch like auto_live.snapshot',function()
  local R=t.fake_runner()
  put(R,'/run/hv/native-status.json',obj({state='OBSERVING',mode='continuous-pair',time=R.now-1,source='wireguard:peer_7',target='wireguard:peer_8'}))
  local m=monitor.new(R)
  m:pass()
  local live=m.rpc.handle('auto_live','{}')
  t.eq(live.auto_control,{requested='off',pair_phase=canon.null})
  t.eq(live.channel_path.code,'KERNEL-POLICY-UNVERIFIED');t.eq(live.native_failover.mode,'continuous-pair')
  t.eq(live.manual_switch.state,'IDLE');t.eq(live.speed_pause,{active=false})
end)

t.run()
