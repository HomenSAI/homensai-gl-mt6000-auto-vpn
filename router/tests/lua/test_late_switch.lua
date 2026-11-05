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
local function run_fault(healthy_at,recheck,mtu,model)
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
    policy_roles=pair.policy.proof(sel)}))
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
  local starts={}
  for _,x in ipairs(SIM.normal_passes) do starts[#starts+1]=start+x end
  local x=SIM.dense_first
  while x<SIM['end'] do starts[#starts+1]=start+x;x=x+SIM.dense_every end
  local real_attempt,real_late,real_publish=T.attempt,pair.late_recheck,T.publish
  T.attempt=function(...) log.switches[#log.switches+1]=env.run.wall()-start;return real_attempt(...) end
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
          rows[#rows+1]=canon.object({id=sel.target.id,time=canon.float(s),code=NULL,dns_ok=true,https_success=3,interface='ovpnclient1',vendor_tunnel_id='openvpn:ovpnclient1',vendor_generation=t.GEN2})
        end
      end
      env.run.fs.write_atomic(env.runtime..'/status.json',canon.encode(canon.object({time=canon.float(now),samples=rows})))
      t.eq(pair.tick(env,t.settings({failure_model=model or 'consecutive'}),env.revision),true)
      tick=math.max(tick+SIM.tick_every,env.run.wall())
    end
  end)
  T.attempt,pair.late_recheck,T.publish=real_attempt,real_late,real_publish
  if not ok then error(err,0) end
  log.kernel=env.backend.kernel[1]
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
