-- Late-switch recheck: never leave a primary that already recovered before the failover commits.
-- MT3000 phase 2, 02.11.2026 (2.1.0-alpha5): a 15 s blackout was left at ~20 s (APPLYING 18.7 s) after the primary
-- had recovered at 15 s; 20-40 s blackouts were left at 20-22 s. Python twin: tests/test_late_switch.py
-- (late_switch_cases.json, the same decisions).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local T=require('transaction')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local CASES=canon.decode(read_file(t.here..'/../late_switch_cases.json'))
local PROFILE=CASES.profile
local N=canon.number
-- plain numbers for the simulation timing (canon keeps decoded fractions as float objects)
local SIM={}
for k,v in pairs(CASES.simulation) do SIM[k]=v end
for _,k in ipairs({'dense_first','dense_every','publish_after','tick_every','diagnostic_seconds','probe_up_seconds','end','max_added_seconds'}) do SIM[k]=N(SIM[k]) end
do local p={};for i,v in ipairs(CASES.simulation.normal_passes) do p[i]=N(v) end;SIM.normal_passes=p end

local function row(profile,r)
  return canon.object({id=profile.id,time=canon.float(N(r.t)),code=r.code,dns_ok=r.dns_ok,https_success=r.https,interface=profile.interface,
    vendor_tunnel_id=profile.vendor_tunnel_id,vendor_generation=(r.gen~=nil and r.gen~=NULL) and r.gen or profile.vendor_generation})
end

t.test('monitor_recovered: the shared cases',function()
  for _,case in ipairs(CASES.recovered) do
    local samples=canon.array({})
    for _,r in ipairs(case.rows) do samples[#samples+1]=row(PROFILE,r) end
    t.eq(pair.monitor_recovered(samples,PROFILE.id,case.evidence,case.now,PROFILE,nil),case.result,case.name)
  end
end)

t.test('same_evidence: the shared cases',function()
  for _,case in ipairs(CASES.same_evidence) do
    t.eq(pair.same_evidence(case.aborted,case.evidence),case.result,case.name)
  end
end)

t.test('newest_sample without a profile',function()
  local good=canon.object({id='a',time=5,code=NULL,dns_ok=true,https_success=3})
  local bad=canon.object({id='a',time=5,code='VPN-003',dns_ok=false,https_success=0})
  local old=canon.object({id='a',time=1,code='VPN-003',dns_ok=false,https_success=0})
  t.truthy(pair.newest_sample(canon.array({old,good,canon.object({id='b',time=9})}),'a')==good)
  t.eq(pair.newest_sample(canon.array({old,good,bad}),'a'),nil,'two disagreeing samples of one stamp')
  t.eq(pair.newest_sample(canon.array({canon.object({id='a',time='x'})}),'a'),nil)
  t.eq(pair.newest_sample(nil,'a'),nil)
end)

t.test('constants',function()
  t.eq({pair.LATE_RECHECK_CODE,pair.RECHECK_SECONDS},{'PRIMARY-RECOVERED-BEFORE-SWITCH',1})
end)

local function status(env,rows)
  local samples=canon.array({})
  for _,r in ipairs(rows) do samples[#samples+1]=row(PROFILE,r) end
  env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({samples=samples})))
end
local function selection() return {source=PROFILE,target=canon.object({id='openvpn:1_1'})} end

t.test('late_recheck: a newer healthy monitor sample aborts without probing',function()
  local env=t.env();env.run.wall_now=1018.5
  local probed=0;env.backend.recheck=function() probed=probed+1;return true end
  status(env,{{t=1011.5,code='VPN-003',dns_ok=false,https=0},{t=1015.5,code=NULL,dns_ok=true,https=3}})
  t.eq({pair.late_recheck(env,selection(),1011.5)},{'PRIMARY-RECOVERED-BEFORE-SWITCH','monitor'})
  t.eq(probed,0)
end)

t.test('late_recheck: only a true probe answer aborts; errors and other answers go on',function()
  local env=t.env();env.run.wall_now=1018.5
  status(env,{{t=1011.5,code='VPN-003',dns_ok=false,https=0}})
  local asked
  env.backend.recheck=function(id,seconds) asked={id,seconds};return true end
  t.eq({pair.late_recheck(env,selection(),1011.5)},{'PRIMARY-RECOVERED-BEFORE-SWITCH','probe'})
  t.eq(asked,{PROFILE.id,1})
  for _,answer in ipairs({false,1,'yes'}) do
    env.backend.recheck=function() return answer end
    t.eq(pair.late_recheck(env,selection(),1011.5),nil,tostring(answer))
  end
  env.backend.recheck=function() return nil end;t.eq(pair.late_recheck(env,selection(),1011.5),nil)
  env.backend.recheck=function() error('probe fault') end;t.eq(pair.late_recheck(env,selection(),1011.5),nil)
  env.backend.recheck=nil;t.eq(pair.late_recheck(env,selection(),1011.5),nil)
  env.run.fs.write_atomic(env.runtime..'/status.json','{')
  env.backend.recheck=function() return false end;t.eq(pair.late_recheck(env,selection(),1011.5),nil,'unreadable status goes on')
end)

t.test('late_recheck: a large-packet failure (VPN-MTU) is never contradicted by the short probe',function()
  local env=t.env();env.run.wall_now=1018.5
  local probed=0;env.backend.recheck=function() probed=probed+1;return true end
  status(env,{{t=1011.5,code='VPN-MTU',dns_ok=true,https=3}})
  t.eq(pair.late_recheck(env,selection(),1011.5,'VPN-MTU'),nil);t.eq(probed,0)
  t.eq({pair.late_recheck(env,selection(),1011.5,'VPN-003')},{'PRIMARY-RECOVERED-BEFORE-SWITCH','probe'});t.eq(probed,1)
  status(env,{{t=1011.5,code='VPN-MTU',dns_ok=true,https=3},{t=1015.5,code=NULL,dns_ok=true,https=3}})
  t.eq({pair.late_recheck(env,selection(),1011.5,'VPN-MTU')},{'PRIMARY-RECOVERED-BEFORE-SWITCH','monitor'})
end)

t.test('live_probe: the short wait reaches every HTTPS check and the DNS check',function()
  local L=require('live_probe')
  local seen={}
  local io_={wall=function() return 1000 end,clock=function() return 1000 end,random=function(n) return string.rep('a',n) end,
    route_binding=function() return {device='wg0',mark=4096,table='1',ifindex=7} end,
    probe_io=function(device,requests,dns)
      local secs={};for i,r in ipairs(requests) do secs[i]=r.seconds end
      seen[#seen+1]={secs,dns.seconds}
      return {},nil,'timeout'
    end}
  local lp=L.new(io_)
  lp.probe({id='wireguard:peer_1',interface='wgclient1'},false,1)
  lp.probe({id='wireguard:peer_1',interface='wgclient1'},false)
  lp.probe({id='wireguard:peer_1',interface='wgclient1'},false,6)
  t.eq(seen,{{{1,1,1},1},{{6,6,6},3},{{6,6,6},3}})
end)

-- pair.tick against the measured MT3000 timing (late_switch_cases.json 'simulation'): real streak, recheck and
-- transaction (fake instant switch); the diagnostic costs diagnostic_seconds, the probe answers as the primary is.
local function run_fault(healthy_at,recheck,mtu,model,extra,beat,reserve_ok,parallel,hold)
  -- extra: more options; beat(offset) -> the monitor's heartbeat row fields or nil; reserve_ok(offset) -> false: a failing reserve;
  -- parallel: the backend also has the two halves of the recheck (the same answer, the clock of the sequential probe)
  pair.late_aborts={}
  local env=t.env()
  local sel=env.backend.selection
  local start=env.run.wall()
  sel.source.vendor_changed_at=canon.float(start-1000);sel.target.vendor_changed_at=canon.float(start-1000)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(start),id=string.rep('11',16),request_source='manual'})))
  env.net={network=function() return canon.array({canon.object({['.name']='wgclient1',disabled='0'}),canon.object({['.name']='ovpnclient1',disabled='0'})}) end,
    identity=function() return string.rep('aa',32) end,configs=function() return canon.object({}) end,changed=function() return false end,
    client_down=function() return false end}
  pair.save(env,canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(start-1000),revision=env.revision,network_identity=string.rep('aa',32),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=canon.object({}),owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=sel.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(sel),manual_hold=hold}))
  env.backend.recovery_ready=function() return false end
  local log={switches={},rechecks={},published={}}
  local diagnostic=env.backend.diagnostic
  env.backend.diagnostic=function() env.run.advance(SIM.diagnostic_seconds);return diagnostic() end
  local function up(at) return healthy_at(at-start) end
  if recheck then
    env.backend.recheck=function(id,seconds)
      log.rechecks[#log.rechecks+1]=env.run.wall()-start
      local healthy=up(env.run.wall()) or mtu==true  -- the short probe never sees large-packet loss
      env.run.advance(healthy and SIM.probe_up_seconds or seconds)
      return healthy
    end
  end
  if parallel then
    env.backend.recheck_begin=function(id,seconds) log.begun=env.run.wall()-start;log.rechecks[#log.rechecks+1]=log.begun;return {healthy=up(env.run.wall()) or mtu==true} end
    env.backend.recheck_finish=function(pending) return pending.healthy end
  end
  local starts={}
  for _,x in ipairs(SIM.normal_passes) do starts[#starts+1]=start+x end
  local x=SIM.dense_first
  while x<SIM['end'] do starts[#starts+1]=start+x;x=x+SIM.dense_every end
  local real_attempt,real_late,real_publish=T.attempt,pair.late_recheck,T.publish
  T.attempt=function(e,s,u,f,opts) log.switches[#log.switches+1]=env.run.wall()-start;log.evidence=opts and opts.probe_evidence;return real_attempt(e,s,u,f,opts) end
  T.publish=function(e,value) log.published[#log.published+1]={env.run.wall()-start,value};return real_publish(e,value) end
  if not recheck then pair.late_recheck=function() return nil end end
  local ok,err=pcall(function()
    local tick=start-30
    env.run.advance(tick-env.run.wall())
    while tick<start+SIM['end'] and #log.switches==0 do
      if env.run.wall()<tick then env.run.advance(tick-env.run.wall()) end
      local now=env.run.wall()
      local rows=canon.array({})
      for _,s in ipairs(starts) do
        if s+SIM.publish_after<=now then
          local good=up(s)
          local small=good or mtu==true  -- a large-packet black hole still answers the small DNS/HTTPS checks
          rows[#rows+1]=canon.object({id=sel.source.id,time=canon.float(s),code=good and NULL or (mtu and 'VPN-MTU' or 'VPN-003'),dns_ok=small,https_success=small and 3 or 0,
            interface='wgclient1',vendor_tunnel_id='wireguard:wgclient1',vendor_generation=t.GEN1})
          local fine=reserve_ok==nil or reserve_ok(s-start)
          rows[#rows+1]=canon.object({id=sel.target.id,time=canon.float(s),code=fine and NULL or 'VPN-003',dns_ok=fine,https_success=fine and 3 or 0,interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2})
        end
      end
      env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=rows})))
      local row=beat and beat(now-start) or nil
      if row then
        local wake=canon.object({reason='heartbeat',time=canon.float(now),id=sel.source.id,target=sel.target.id})
        for k,v in pairs(row) do wake[k]=v end
        env.run.fs.write_atomic(env.runtime..'/pair-wake.json',canon.encode(wake))
      end
      local options={failure_model=model or 'consecutive'}
      for k,v in pairs(extra or {}) do options[k]=v end
      t.eq(pair.tick(env,t.settings(options),env.revision),true)
      tick=math.max(tick+SIM.tick_every,env.run.wall())
    end
  end)
  T.attempt,pair.late_recheck,T.publish=real_attempt,real_late,real_publish
  if not ok then error(err,0) end
  log.kernel=env.backend.kernel[1]
  log.leases=#env.backend.leases;log.hold=pair.read_state(env).manual_hold
  return log
end
local function blackout(seconds,recheck) return run_fault(function(o) return not (o>=0 and o<seconds) end,recheck) end
local function aborts(log)
  local out={}
  for _,p in ipairs(log.published) do if p[2].reason=='PRIMARY-RECOVERED-BEFORE-SWITCH' then out[#out+1]=p end end
  return out
end

t.test('simulation: blackouts against the unfixed decision',function()
  for _,case in ipairs(SIM.blackouts) do
    local name='blackout '..case.seconds
    local before=blackout(case.seconds,false)
    local after=blackout(case.seconds,true)
    t.eq(#before.switches>0,case.baseline_switch,name..': the unfixed decision reproduces the router')
    t.eq(#after.switches>0,case.switch,name)
    if case.switch then
      local added=after.switches[1]-before.switches[1]
      t.truthy(added>=0 and added<=SIM.max_added_seconds+1e-9,name..': added '..added)
      t.eq(#after.rechecks,1,name)
      t.eq(after.kernel,'r2',name..': the traffic left the primary')
    else
      local list=aborts(after)
      t.truthy(#list>0,name..': the abort is published with its code')
      t.eq(list[1][2].state,'OBSERVING')
      t.truthy(list[1][2].late_recheck=='probe' or list[1][2].late_recheck=='monitor')
      t.truthy(#after.rechecks<=1,name..': the same evidence is never probed twice')
      t.eq(after.published[#after.published][2].reason,'PAIR-WATCHING',name)
      t.eq(after.kernel,'r1',name..': stayed on the primary')
    end
  end
end)

t.test('simulation: a primary that dies again is left on new evidence',function()
  local log=run_fault(function(o) return not ((o>=0 and o<15) or o>=17) end,true)
  t.truthy(#log.switches>0)
  t.truthy(#aborts(log)>0)
  t.truthy(log.switches[1]<=27.5+SIM.publish_after+SIM.tick_every+4*SIM.diagnostic_seconds+1+1e-9,'switched at '..tostring(log.switches[1]))
end)

t.test('simulation: a dead primary is never held by a failing probe',function()
  local log=run_fault(function(o) return o<0 end,true)
  t.truthy(#log.switches>0)
  t.eq(#aborts(log),0)
end)

t.test('simulation: a large-packet black hole (VPN-MTU) is left without a contradicting probe',function()
  local log=run_fault(function(o) return o<0 end,true,true)
  t.truthy(#log.switches>0,'switched');t.eq(#log.rechecks,0,'the live probe is not asked');t.eq(#aborts(log),0)
  t.eq(log.kernel,'r2','the traffic left the primary')
end)

if os.getenv('LATE_SWITCH_REPORT') then
  for _,s in ipairs({5,10,15,20,25,30,40}) do
    local b,a=blackout(s,false),blackout(s,true)
    io.stderr:write('blackout ',s,' before ',tostring(b.switches[1]),' after ',tostring(a.switches[1]),' rechecks ',#a.rechecks,' aborts ',#aborts(a),'\n')
  end
end

t.test('the fast end with the same timing (leave_rule, FAST-SWITCH-2026-11-04.ru.md)',function()
  local function outage(seconds) return function(o) return not (0<=o and o<seconds) end end
  local model=run_fault(outage(40),true,false,'hmm')
  local two=run_fault(outage(40),true,false,'hmm',{hmm_or_failures=2})
  local three=run_fault(outage(40),true,false,'hmm',{hmm_or_failures=3})
  t.truthy(two.switches[1]<model.switches[1],'2 in a row leaves earlier than the model: '..two.switches[1]..' < '..model.switches[1])
  t.truthy(two.switches[1]<=three.switches[1],'and not later than 3 in a row')
  t.eq(two.evidence.failure_rule,'streak');t.eq(model.evidence.failure_rule,'model')
  t.eq(#two.rechecks,1,'the late recheck is not skipped')
  -- one failed sample is no streak; the recheck still cancels a blackout that ended
  t.eq(#run_fault(outage(4),true,false,'hmm',{hmm_or_failures=2}).switches,0,'a 4 s blackout stays')
  local short=run_fault(outage(12),true,false,'hmm',{hmm_or_failures=2})
  if #short.switches==0 then t.truthy(#aborts(short)>=0) end
  -- the reserve guard: without a healthy reserve nothing moves
  local bad=run_fault(outage(40),true,false,'hmm',{hmm_or_failures=2},nil,function(o) return o<0 end)
  t.eq(#bad.switches,0,'a failing reserve holds the switch');t.eq(bad.kernel,'r1')
end)

t.test('the heartbeat verdict with the same timing',function()
  local function outage(seconds) return function(o) return not (0<=o and o<seconds) end end
  local options={slider_turbo=true,turbo_beats=5}
  local function lost(reserve) return function(o) if o>=5 and o<40 then return {lost=math.floor(o),target_ok=reserve} end;return nil end end
  local beat=run_fault(outage(40),true,false,'hmm',options,lost(true))
  local plain=run_fault(outage(40),true,false,'hmm')
  t.truthy(beat.switches[1]<plain.switches[1]-5,'earlier by far: '..beat.switches[1]..' against '..plain.switches[1])
  t.eq(beat.evidence.failure_rule,'heartbeat');t.eq(#beat.rechecks,1,'the late recheck is not skipped')
  -- the reserve silent too: a WAN outage, no heartbeat verdict; without the opt-in the row means nothing
  local wan=run_fault(outage(40),true,false,'hmm',options,lost(false))
  t.truthy(wan.switches[1]>=plain.switches[1]-1,'no earlier than the model: '..wan.switches[1]);t.eq(wan.evidence.failure_rule,'model')
  local off=run_fault(outage(40),true,false,'hmm',nil,lost(true))
  t.eq(off.evidence.failure_rule,'model')
  -- a primary that answers the recheck stays, whatever the heartbeats say (a filtered ICMP target)
  local filtered=run_fault(function() return true end,true,false,'hmm',options,lost(true))
  t.eq(#filtered.switches,0,'the live recheck holds it');t.truthy(#aborts(filtered)>0)
end)

t.test('a refuted heartbeat run costs one lease (review 04.11.2026, finding 3)',function()
  local options={slider_turbo=true,turbo_beats=5}
  local function run(since) return function(o) if o>=5 then return {lost=math.floor(o),target_ok=true,since=since(o)} end end end
  local function outage(from,to) return function(o) return not (from<=o and o<to) end end
  local same=function() return canon.float(1000.5) end
  local filtered=run_fault(function() return true end,true,false,'hmm',options,run(same))
  t.eq(#filtered.switches,0);t.eq({filtered.leases,#filtered.rechecks},{1,1},'one lease on flash and one probe for the whole run')
  local seen=false
  for _,p in ipairs(filtered.published) do if p[2].late_recheck=='same-run' then seen=true end end
  t.truthy(seen,'published as the same run')
  -- without `since` (an older monitor row) nothing is remembered: as before
  local old=run_fault(function() return true end,true,false,'hmm',options,function(o) if o>=5 then return {lost=math.floor(o),target_ok=true} end end)
  t.truthy(old.leases>1)
  -- a new run of lost beats is new evidence: looked at once more, once
  local two=run_fault(function() return true end,true,false,'hmm',options,run(function(o) return canon.float(o<30 and 1000.5 or 2000.5) end))
  t.eq({two.leases,#two.rechecks},{2,2})
  -- the refutation ends where the monitor sees the failure itself
  local dying=run_fault(outage(20,60),true,false,'hmm',options,run(same))
  t.truthy(#dying.switches>0,'a real failure is never hidden by the refuted run');t.eq(dying.evidence.failure_rule,'model')
end)

t.test('a refuted decision keeps the owner hold; the switch ends it (finding 3)',function()
  local options={slider_turbo=true,turbo_beats=5}
  local beat=function(o) if o>=5 then return {lost=math.floor(o),target_ok=true,since=canon.float(1000.5)} end end
  local kept=run_fault(function() return true end,true,false,'hmm',options,beat,nil,nil,'source')
  t.eq(#kept.switches,0);t.eq(kept.hold,'source')
  local moved=run_fault(function(o) return not (0<=o and o<40) end,true,false,'hmm',options,beat,nil,nil,'source')
  t.truthy(#moved.switches>0);t.eq(moved.hold,nil)
end)

t.test('L2 in the tick: the probe starts before the lease and the diagnostic, the answer stops the switch',function()
  local function outage(seconds) return function(o) return not (0<=o and o<seconds) end end
  local log=run_fault(outage(40),true,false,'hmm',{hmm_or_failures=2,parallel_recheck='1'},nil,nil,true)
  t.truthy(#log.switches>0);t.eq(#log.rechecks,1)
  t.truthy(log.begun<log.switches[1],'begun before the switch')
  t.truthy(log.switches[1]-log.begun<=SIM.diagnostic_seconds+1e-9,'only the preparation lies between them, no probe wait')
  local healthy=run_fault(function() return true end,true,false,'hmm',{slider_turbo=true,turbo_beats=5,parallel_recheck='1'},function(o) if o>=5 then return {lost=9,target_ok=true} end end,nil,true)
  t.eq(#healthy.switches,0,'a healthy answer of the parallel probe stops it');t.truthy(#aborts(healthy)>0)
  -- the option off, or absent (the default, owner 05.11.2026): the sequential probe runs
  for _,value in ipairs({'0','absent'}) do
    local seq=run_fault(outage(40),true,false,'hmm',{hmm_or_failures=2,parallel_recheck=value~='absent' and value or nil},nil,nil,true)
    t.eq(seq.begun,nil,'no parallel start');t.eq(#seq.rechecks,1,'and the probe is not skipped')
  end
end)

t.test('the failure model (hmm / hmm-fast) with the same timing',function()
  -- 15 s never decides; 20 s decides on its last failure but the recheck finds the primary back; 40 s leaves at ~25 s
  for _,c in ipairs({{'hmm',15,false},{'hmm',20,false},{'hmm',40,true,27},{'hmm-fast',15,false},{'hmm-fast',40,true,23}}) do
    local model,seconds,switch,latest=c[1],c[2],c[3],c[4]
    local log=run_fault(function(o) return not (0<=o and o<seconds) end,true,false,model)
    t.eq(#log.switches>0,switch,model..' '..seconds)
    if switch then t.truthy(log.switches[1]<=latest,model..' '..seconds..' at '..tostring(log.switches[1])) end
    if seconds==15 then t.eq(#log.rechecks,0,'the model never decided') end
  end
  local log=run_fault(function(o) return o<0 end,true,true,'hmm')
  t.truthy(#log.switches>0,'VPN-MTU is a hard failure for the model');t.eq(#log.rechecks,0)
end)

t.run()
