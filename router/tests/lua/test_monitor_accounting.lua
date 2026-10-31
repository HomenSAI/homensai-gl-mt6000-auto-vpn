-- accounting.lua: counters by month/day, gaps, quality, activity, checkpoint envelope, validator, stats mode.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local accounting=require('accounting')

local function local_time(y,m,d,h) return os.time({year=y,month=m,day=d,hour=h or 0,min=0,sec=0}) end

t.test('sample splits traffic across a day and a month boundary by time weight',function()
  local acc=accounting.new()
  local midnight=local_time(2026,11,1,0)  -- also a month boundary (October -> November)
  acc:sample('wgclient',20,1000,2000,midnight-30)
  acc:sample('wgclient',20,1000+600,2000+1200,midnight+30)
  t.eq(acc.months['2026-10'].rx,300);t.eq(acc.months['2026-11'].rx,300);t.eq(acc.months['2026-10'].tx,600)
  t.eq(acc.months['2026-10'].seconds,30);t.eq(acc.months['2026-10'].boundary_estimated,true);t.eq(acc.months['2026-11'].boundary_estimated,false)
  t.eq(acc.days['2026-10-31'].rx,300);t.eq(acc.days['2026-11-01'].rx,300);t.eq(acc.days['2026-11-01'].observed,true)
  t.eq(acc.days['2026-10-31'].first_sample,midnight-30);t.eq(acc.days['2026-10-31'].last_sample,midnight)
  t.eq(acc.gaps,0)
end)

t.test('counter resets, ifindex change, long gaps and clock steps count as gaps, never traffic',function()
  local acc=accounting.new()
  local base=local_time(2026,10,30,12)
  acc:sample('wgclient',20,1000,2000,base)
  acc:sample('wgclient',21,1500,2500,base+10)  -- new ifindex
  t.eq(acc.gaps,1);t.eq(acc.months[os.date('%Y-%m',base)],nil)
  acc:sample('wgclient',21,100,2500,base+20)  -- rx went backwards
  t.eq(acc.gaps,2)
  acc:sample('wgclient',21,200,2600,base+200)  -- longer than max_gap 90
  t.eq(acc.gaps,3)
  acc:sample('wgclient',21,300,2700,base+150)  -- clock stepped back
  t.eq(acc.gaps,4);t.eq(acc.previous.wgclient,nil)
  t.eq(acc.days[os.date('%Y-%m-%d',base)].gaps,4);t.eq(acc.days[os.date('%Y-%m-%d',base)].observed,false)
  acc:sample('wgclient',21,300,2700,base+300);acc:sample('wgclient',21,300,2700,base+300)  -- identical repeat is not a gap
  t.eq(acc.gaps,4)
  t.raises(function() acc:sample('bad dev',1,1,1,base) end)
end)

t.test('note_gap marks every day of the interval, bounded to 400 days',function()
  local acc=accounting.new()
  local base=local_time(2026,10,28,23)
  acc:note_gap(base,base+2*86400)
  t.eq(acc.days['2026-10-28'].gaps,1);t.eq(acc.days['2026-10-29'].gaps,1);t.eq(acc.days['2026-10-30'].gaps,1);t.eq(acc.days['2026-10-31'],nil)
end)

t.test('observe: hourly quality buckets; unknown codes do not count as checks',function()
  local acc=accounting.new()
  local stamp=1761825600
  acc:observe({id='wireguard:peer_7',time=stamp,code=canon.null,rtt_ms=40})
  acc:observe({id='wireguard:peer_7',time=stamp+60,code='VPN-003',rtt_ms=canon.null})
  acc:observe({id='wireguard:peer_7',time=stamp+120,code='CHECK-001'})
  local profile=acc.quality['wireguard:peer_7']
  local bucket=profile.buckets[tostring(math.floor(stamp/3600))]
  t.eq(bucket,{n=2,success=1,rtt_sum=40,unknown=1})
  t.eq(profile.last,{time=stamp+120,code='CHECK-001',rtt_ms=canon.null})
  acc:observe({id='wireguard:peer_7',time=stamp+8*86400,code=canon.null,rtt_ms=10})
  profile=acc.quality['wireguard:peer_7']
  t.eq(profile.buckets[tostring(math.floor(stamp/3600))],nil,'buckets older than detail_days are dropped')
  local remaining=0;for _ in pairs(profile.buckets) do remaining=remaining+1 end;t.eq(remaining,1)
end)

t.test('track_activity: states, connections and failures per local day',function()
  local acc=accounting.new()
  local base=local_time(2026,10,30,10)
  local day=os.date('%Y-%m-%d',base)
  local rows={{id='wireguard:peer_7',name='Vienna',protocol='wireguard',interface='wgclient',code=canon.null}}
  acc:track_activity(rows,base,30)
  acc:track_activity(rows,base+10,30)
  t.eq(acc.activity['wireguard:peer_7'].days[day].up,10);t.eq(acc.activity['wireguard:peer_7'].name,'Vienna')
  rows[1].code='VPN-003'
  acc:track_activity(rows,base+20,30)
  t.eq(acc.activity['wireguard:peer_7'].days[day].up,20);t.eq(acc.activity['wireguard:peer_7'].days[day].failures,1)
  acc:track_activity(rows,base+30,30)
  t.eq(acc.activity['wireguard:peer_7'].days[day].down,10)
  rows[1].interface=canon.null;rows[1].code='PROFILE-INACTIVE'
  acc:track_activity(rows,base+40,30)
  rows[1].interface='wgclient';rows[1].code=canon.null
  acc:track_activity(rows,base+50,30)
  t.eq(acc.activity['wireguard:peer_7'].days[day].idle,10);t.eq(acc.activity['wireguard:peer_7'].days[day].connections,1)
  acc:track_activity(rows,base+200,30)
  t.eq(acc.activity['wireguard:peer_7'].days[day].unknown,150,'beyond max_gap the interval is unknown')
  acc:track_activity(rows,base+100,30)
  t.eq(acc.gaps,1,'a backwards clock is a gap, nothing is double counted')
end)

t.test('export/public_export shapes, compact and detail retention',function()
  local acc=accounting.new()
  local exported=acc:export()
  t.eq(canon.encode(exported),'{"activity":{},"days":{},"gaps":0,"months":{},"quality":{},"retention":{},"wan":null}')
  local stamp=1761825600
  for i=0,30 do acc:observe({id='p'..(i%3),time=stamp+i*3600,code=canon.null,rtt_ms=i}) end
  local limit=#canon.encode(acc:export())-200
  acc:compact(limit)
  t.truthy(acc.retention.quality_buckets_dropped>0);t.truthy(#canon.encode(acc:export())<=limit)
  t.raises(function() acc:compact(10) end,'nothing left to drop: budget exceeded')
  acc=accounting.new()
  for i=0,10 do acc:observe({id='q',time=stamp+i*86400,code=canon.null,rtt_ms=1}) end
  acc:apply_detail_retention(2,stamp+10*86400)
  local kept=0;for _ in pairs(acc.quality.q.buckets) do kept=kept+1 end
  t.eq(kept,3);t.eq(acc.detail_days,2)
  local public=acc:public_export(stamp)
  t.truthy(canon.is_object(public));t.eq(public.rpc_aggregated,nil)
end)

t.test('checkpoint envelope: {data:{version,saved,accounting},sha256}; restore verifies the digest',function()
  local R=t.fake_runner()
  local acc=accounting.new()
  acc:observe({id='wireguard:peer_7',time=R.now,code=canon.null,rtt_ms=12.5})
  local envelope=accounting.checkpoint(R,R.PERSIST,acc)
  local text=R.files[R.PERSIST..'/checkpoint.json']
  t.truthy(text~=nil);t.eq(R.files[R.PERSIST..'/checkpoint.backup.json'],nil,'no backup before a first valid checkpoint')
  local decoded=canon.decode(text)
  t.eq(decoded.data.version,1);t.eq(canon.number(decoded.data.saved),R.now)
  t.eq(decoded.sha256,canon.digest(decoded.data),'digest over the re-encoded data')
  t.eq(#decoded.sha256,64)
  local restored,notice=accounting.restore(R,R.PERSIST)
  t.eq(notice,nil);t.eq(restored.gaps,1,'a restart adds one gap');t.truthy(restored.quality['wireguard:peer_7']~=nil)
  t.eq(restored.quality['wireguard:peer_7'].last.rtt_ms,12.5)
  accounting.checkpoint(R,R.PERSIST,restored)
  t.truthy(R.files[R.PERSIST..'/checkpoint.backup.json']~=nil,'the previous valid checkpoint became the backup')
  R.files[R.PERSIST..'/checkpoint.json']=string.gsub(text,'"gaps":0','"gaps":1')
  restored,notice=accounting.restore(R,R.PERSIST)
  t.eq(notice,'STORAGE-RECOVERED','tampered checkpoint, backup used')
  R.files[R.PERSIST..'/checkpoint.backup.json']='{"data":{"version":1,"saved":1,"accounting":{"gaps":-1}},"sha256":"x"}'
  restored,notice=accounting.restore(R,R.PERSIST)
  t.eq(notice,'STORAGE-001');t.eq(restored.gaps,0)
  R.files={}
  restored,notice=accounting.restore(R,R.PERSIST)
  t.eq(notice,nil)
end)

t.test('validate refuses what checkpoint_schema.validate refuses',function()
  local function env(acc,extra)
    local data=canon.object({version=1,saved=1761825600,accounting=acc})
    for k,v in pairs(extra or {}) do data[k]=v end
    return canon.object({data=data,sha256='x'})
  end
  local ok_acc=canon.object({months=canon.object({['2026-10']=canon.object({rx=1,tx=2,seconds=3})}),days=canon.object({['2026-10-30']=canon.object({rx=0})}),
    gaps=0,quality=canon.object({p=canon.object({buckets=canon.object({['489395']=canon.object({n=1})}),last=canon.null})}),
    activity=canon.object({p=canon.object({days=canon.object(),last_seen=1761825600})}),retention=canon.object()})
  t.truthy(accounting.validate(env(ok_acc)))
  local function refused(code,envelope) local err=t.raises(accounting.validate,envelope);t.eq(err,code) end
  refused('CHECKPOINT-ENVELOPE',canon.array({1}))
  refused('CHECKPOINT-VERSION',canon.object({data=canon.object({version=canon.float(1),saved=1,accounting=canon.object()}),sha256='x'}))
  refused('CHECKPOINT-TIME',canon.object({data=canon.object({version=1,saved=-1,accounting=canon.object()}),sha256='x'}))
  refused('CHECKPOINT-ACCOUNTING',canon.object({data=canon.object({version=1,saved=1,accounting=canon.array({1})}),sha256='x'}))
  refused('CHECKPOINT-GAPS',env(canon.object({gaps=-1})))
  refused('CHECKPOINT-GAPS',env(canon.object({gaps=canon.float(1)})))
  refused('CHECKPOINT-MONTH',env(canon.object({months=canon.object({['2026-13']=canon.object()})})))
  refused('CHECKPOINT-DAY',env(canon.object({days=canon.object({['2026-02-30']=canon.object()})})))
  refused('CHECKPOINT-COUNTER',env(canon.object({days=canon.object({['2026-02-28']=canon.object({rx=-1})})})))
  refused('CHECKPOINT-BUCKET',env(canon.object({quality=canon.object({p=canon.object({buckets=canon.object({x=canon.object()})})})})))
  refused('CHECKPOINT-LAST',env(canon.object({quality=canon.object({p=canon.object({last=5})})})))
  refused('CHECKPOINT-ACTIVITY',env(canon.object({activity=canon.object({p=canon.object({days=canon.array({1})})})})))
  refused('CHECKPOINT-WAN-DEPTH',env(canon.object({wan=canon.object({wan=canon.object()})})))
  refused('CHECKPOINT-NUMBER',env(canon.object(),{extra=canon.float(1e31)}))
  refused('CHECKPOINT-STRING',env(canon.object(),{extra=string.rep('x',4097)}))
  local deep=canon.object();local cursor=deep
  for _=1,13 do cursor.x=canon.object();cursor=cursor.x end
  refused('CHECKPOINT-BOUNDS',env(canon.object(),{extra=deep}))
end)

t.test('stats mode: work/diagnostic from the package config, bounded window, storage sizes',function()
  local R=t.fake_runner({config="config main 'main'\n\toption enabled '1'\n\toption stats_mode 'work'\n\toption stats_until '0'\n"})
  t.eq(accounting.stats.diagnostic(R,R.now),false)
  t.eq(accounting.stats.public(R,R.now),{mode='work',['until']=canon.null,remaining=0,hours={24,72,168,336},default_hours=24})
  R.config="config main 'main'\n\toption stats_mode 'diagnostic'\n\toption stats_until '"..math.floor(R.now+3600).."'\n";R.config_version=2
  t.eq(accounting.stats.diagnostic(R,R.now),true)
  t.eq(accounting.stats.public(R,R.now).remaining,3600)
  R.config="config main 'main'\n\toption stats_mode 'diagnostic'\n\toption stats_until '"..math.floor(R.now+400*3600).."'\n";R.config_version=3
  t.eq(accounting.stats.diagnostic(R,R.now),false,'a window beyond 14 days is not honoured')
  R.config=nil
  t.eq(accounting.stats.diagnostic(R,R.now),true,'no package config: record everything')
  R.files['/run/hv/status.json']='{}';R.files['/etc/hv/checkpoint.json']='12345';R.files['/etc/hv/checkpoint.backup.json']='123'
  t.eq(accounting.stats.storage(R,'/run/hv','/etc/hv'),{['ram:status.json']=2,['flash:checkpoint.json']=8})
end)

t.run()
