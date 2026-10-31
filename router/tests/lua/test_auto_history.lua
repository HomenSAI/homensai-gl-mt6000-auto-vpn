-- history.lua: item fields, correlation, counters, prune, backup rename, load refusals.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local history=require('history')

local function fresh()
  local env=t.env()
  return env,history.new(env,env.persist,10000)
end
local function record(env,h,value) return h:record(value,env.run.wall()) end

t.test('first record creates the file; the same event twice is not recorded again',function()
  local env,h=fresh()
  t.eq(record(env,h,{state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_1',target='openvpn:1_1',proof_scope='router-probed-ipv4'}),true)
  local data=t.history(env)
  t.eq(data.sequence,1);t.eq(#data.events,1);t.eq(data.counter_version,2);t.eq(data.events[1].codes,canon.array({'PAIR-WATCHING'}))
  t.eq(data.events[1].sequence,1);t.eq(data.events[1].trial,false);t.eq(data.events[1].proof_scope,'router-probed-ipv4')
  t.truthy(canon.is_float(data.events[1].time) and canon.is_float(data.last_time))
  t.eq(data.totals.attempts,0);t.eq(#data.events[1].counted_metrics,0)
  env.run.advance(5)
  t.eq(record(env,h,{state='OBSERVING',reason='PAIR-WATCHING',source='wireguard:peer_1',target='openvpn:1_1',proof_scope='router-probed-ipv4'}),false)
  t.eq(t.history(env).sequence,1)
  -- envelope shape: {"data":...,"schema":1,"sha256":...} with the checksum of the canonical data
  local text=env.run.fs.read(env.persist..'/native-history.json')
  t.truthy(text:sub(1,8)=='{"data":')
  local envelope=canon.decode(text)
  t.eq(envelope.sha256,canon.sha256(canon.encode(envelope.data)))
end)

t.test('attempt correlation and counters over a switch',function()
  local env,h=fresh()
  local base={source='wireguard:peer_1',target='openvpn:1_1',proof_scope='router-probed-ipv4',transition_source='automatic'}
  local function ev(extra) local v={};for k,x in pairs(base) do v[k]=x end;for k,x in pairs(extra) do v[k]=x end;return v end
  record(env,h,ev({state='ARMED',reason='SOURCE-FAILED'}));env.run.advance(1)
  record(env,h,ev({state='APPLYING',reason='SOURCE-FAILED',probe_evidence=canon.object({source_streak_met=true,required_failures=3,required_successes=11})}));env.run.advance(1)
  record(env,h,ev({state='WAIT-CLIENT'}));env.run.advance(1)
  record(env,h,ev({state='COMMITTED',reason='CLIENT-CONFIRMED',transition_completed=true,transition_outcome='committed',transition_kind='protocol',
    destination_role='target',destination_profile_id='openvpn:1_1',from_role='source',from_profile_id='wireguard:peer_1',route_changed=true,
    before_order=canon.array({'r1','r2'}),after_order=canon.array({'r2','r1'})}))
  local data=t.history(env)
  t.eq(data.sequence,4)
  for i=1,4 do t.eq(data.events[i].attempt_id,1);t.eq(data.events[i].retry_episode_id,1) end
  t.eq(data.active_attempt,canon.object({id=1,episode=1,source='wireguard:peer_1',target='openvpn:1_1',terminal=true}))
  t.eq(data.retry_episode.closed,true)
  t.eq(data.totals.attempts,1);t.eq(data.totals.automatic_attempts,1);t.eq(data.totals.committed,1);t.eq(data.totals.automatic_committed,1);t.eq(data.totals.protocol_switches,1)
  t.eq(data.events[2].probe_evidence,canon.object({source_streak_met=true,required_failures=3}))
  t.eq(data.events[4].counted_metrics,canon.array({'committed','automatic_committed','protocol_switches'}))
  t.eq(data.events[4].before_order,canon.array({'r1','r2'}));t.eq(data.events[4].from_profile_id,'wireguard:peer_1')
  local month=os.date('!%Y-%m',env.run.wall());t.eq(data.months[month].committed,1);t.eq(data.days[os.date('!%Y-%m-%d',env.run.wall())].attempts,1)
  -- a return: rollback with the primary restored counts a return once
  env.run.advance(1)
  record(env,h,ev({state='RESTORING',reason='PRIMARY-STABLY-RECOVERED',transition_metadata_present=true,route_changed=true,destination_role='source',destination_profile_id='wireguard:peer_1'}))
  env.run.advance(1)
  record(env,h,ev({state='ROLLED-BACK',reason='PRIMARY-STABLY-RECOVERED',original_restored=true,transition_completed=true,transition_outcome='restored',
    from_role='target',from_profile_id='openvpn:1_1',destination_role='source',destination_profile_id='wireguard:peer_1',route_changed=true}))
  data=t.history(env)
  t.eq(data.events[5].attempt_id,5)  -- Python: a new attempt id is the next sequence number;t.eq(data.totals.rollbacks,1);t.eq(data.totals.returns,1)
  -- BLOCKED episodes and rate limit episodes count once per run
  env.run.advance(1);record(env,h,ev({state='BLOCKED',blockers=canon.array({'PAIR-RATE-LIMIT'})}))
  env.run.advance(1);record(env,h,ev({state='BLOCKED',blockers=canon.array({'PAIR-RATE-LIMIT','X'})}))
  data=t.history(env);t.eq(data.totals.blocked_episodes,1);t.eq(data.totals.rate_limited_episodes,1)
  -- manual
  env.run.advance(1);record(env,h,ev({state='APPLYING',reason='OPERATOR-MANUAL',manual=true,transition_source='manual'}))
  env.run.advance(1);record(env,h,ev({state='COMMITTED',reason='OPERATOR-MANUAL',manual=true,transition_source='manual'}))
  data=t.history(env);t.eq(data.totals.manual_attempts,1);t.eq(data.totals.manual_committed,1);t.eq(data.events[#data.events].manual,true)
  t.eq(data.events[#data.events].transition_source,'manual')
end)

t.test('backup is the previous main (renamed); load falls back to the backup; corrupt pair refuses',function()
  local env,h=fresh()
  record(env,h,{state='OBSERVING'});env.run.advance(1)
  local first=env.run.fs.read(env.persist..'/native-history.json')
  record(env,h,{state='BLOCKED',blockers=canon.array({'X'})})
  t.eq(env.run.fs.read(env.persist..'/native-history.backup.json'),first)
  env.run.fs.write_atomic(env.persist..'/native-history.json','garbage')
  local data=h:load();t.eq(data.sequence,1);t.eq(h.restored,true)
  env.run.fs.write_atomic(env.persist..'/native-history.backup.json','{}')
  t.code('HISTORY-CORRUPT',function() return h:load() end)
  env.run.fs.remove(env.persist..'/native-history.json');env.run.fs.remove(env.persist..'/native-history.backup.json')
  t.eq(h:load().sequence,0)
end)

t.test('item validation: bad state refused, unknown codes dropped, phase evidence cleaned, orders checked',function()
  local env,h=fresh()
  t.code('HISTORY-STATE',record,env,h,{state='bad state'})
  t.code('HISTORY-SCOPE',record,env,h,{state='X',proof_scope='lan'})
  local now=env.run.wall()
  record(env,h,{state='ARMED',blockers=canon.array({'ok-not','GOOD','x y'}),phase_evidence=canon.array({canon.object({phase='ARMED',time=canon.float(now-1)}),
    canon.object({phase='bad',time=canon.float(now)}),canon.object({phase='APPLYING',time=canon.float(now+5)}),canon.object({phase='LATE',time=canon.float(now-5)})}),
    before_order=canon.array({'a','a'}),after_order=canon.array({'a','b'}),source='nope',target='openvpn:1_1',transition_kind='magic'})
  local item=t.history(env).events[1]
  t.eq(item.codes,canon.array({'GOOD'}));t.eq(#item.phase_evidence,1);t.eq(item.phase_evidence[1].phase,'ARMED')
  t.eq(item.before_order,nil);t.eq(item.after_order,canon.array({'a','b'}));t.eq(item.source,nil);t.eq(item.target,'openvpn:1_1');t.eq(item.transition_kind,nil)
end)

t.test('prune drops old detailed events but keeps the aggregates',function()
  local env,h=fresh()
  record(env,h,{state='OBSERVING'})
  env.run.advance(8*86400)
  record(env,h,{state='BLOCKED',blockers=canon.array({'Y'})})
  local data=t.history(env)
  t.eq(#data.events,1);t.eq(data.events[1].state,'BLOCKED');t.eq(data.sequence,2);t.eq(data.totals.blocked_episodes,1)
  t.eq(select(2,next(data.days))~=nil,true)
end)

t.test('history.new bounds',function()
  local env=t.env()
  t.code('HISTORY-RETENTION',history.new,env,env.persist,10000,0)
  t.code('HISTORY-LIMIT',history.new,env,env.persist,0)
  t.eq(history.new(env,env.persist,10000,3).detail_days,3)
end)

t.run()
