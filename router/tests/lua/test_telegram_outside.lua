-- Owner decision 07.11.2026: a HOLD (PAIR-OUTSIDE-CHANGE-HELD) or an automatic ADOPT (PAIR-OUTSIDE-CHANGE-ADOPTED) of a
-- change made outside the app is told in Telegram. The pair writes each decision into a bounded RAM ring
-- (pair.lua outside_notice -> telegram.outside_push); deliver() tells it on its next round (telegram.outside_notice), at
-- most one message per class every 10 min, gated like the VENDOR-BUSY notice. Fake sender only, no network, no real
-- token. Python twin: tests/test_telegram_outside.py (it also compares the text with this module where lua5.1 exists).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/auto_harness.lua')
local canon=t.canon
local pair=require('pair')
local ctl=require('auto_control')
local telegram=require('telegram')

local T0=1794040000
local TOKEN,CHAT='123456:SYNTHETICtokenNOTREAL','-100123'
local function hold(at,packages,trigger)
  return canon.object({decision='HOLD',trigger=trigger or 'PAIR-EXTERNAL-CONFIG-CHANGE',packages=canon.array(packages or {'wireguard','firewall'}),why='FOREIGN-PACKAGES',time=canon.float(at)})
end
local function adopt(at,packages)
  return canon.object({decision='ADOPT',trigger='PAIR-EXTERNAL-CONFIG-CHANGE',packages=canon.array(packages or {'dhcp','wireless'}),why='ADOPT-PACKAGES-ONLY',time=canon.float(at)})
end
local function release(at,kind,packages,trigger)  -- owner decision 07.11.2026: the owner's Stop / Start ended an outside-change hold
  return canon.object({decision='RELEASE',release=kind,trigger=trigger or 'PAIR-EXTERNAL-CONFIG-CHANGE',packages=canon.array(packages or {'wireguard','firewall'}),why='OWNER-'..kind,time=canon.float(at)})
end
local function has(text,part) return string.find(text,part,1,true)~=nil end

-- the sender deps: memory files, the fake sender records every text
local function fake(config)
  local d={runtime='/run/hv',persist='/persist',files={},sent={},fail=nil}
  d.read=function(path) return d.files[path] end
  d.size=function(path) return d.files[path] and #d.files[path] or nil end
  d.is_link=function() return false end
  d.write=function(path,text) d.files[path]=text end
  d.remove=function(path) d.files[path]=nil end
  d.lock=function(fn) return fn() end
  d.sleep=function() end
  d.send=function(_,text) if d.fail then error(d.fail,0) end;d.sent[#d.sent+1]=text end
  d.cfg={telegram_enabled='1',telegram_chat=CHAT,telegram_token=TOKEN,telegram_schedule='interval',telegram_interval='60',telegram_weekly='0',telegram_monthly='0'}
  for k,v in pairs(config or {}) do d.cfg[k]=v end
  d.config=function() local out={};for k,v in pairs(d.cfg) do out[k]=v end;return out end
  d.sha256=function() return string.rep('ab',32) end
  d.wall=function() return T0 end
  d.clock=function() return d.mono end  -- BH-05: nil = no monotonic clock, the wall-clock age (the cases above BH-05)
  return d
end
local function record(d,verdict,mono)
  local path=d.runtime..'/'..telegram.OUTSIDE_FILE
  local old=d.files[path] and canon.decode(d.files[path]) or canon.object()
  d.files[path]=canon.encode(telegram.outside_push(old,verdict,mono))
end
local function deliver(d,now,saved,status)
  local s=canon.object({sent=canon.float(now-1)})
  for k,v in pairs(saved or {}) do s[k]=v end
  return telegram.deliver(d,status or canon.object({native_failover=canon.object({state='OBSERVING',time=canon.float(now)})}),s,now)
end

t.test('ring: bounded, deduplicated, codes and names only',function()
  local ring=canon.object()
  for i=0,39 do ring=telegram.outside_push(ring,hold(T0+i)) end
  ring=telegram.outside_push(ring,hold(T0+39))
  t.eq(#ring.items,telegram.OUTSIDE_KEEP);t.eq(canon.number(ring.items[#ring.items].time),T0+39);t.eq(canon.number(ring.items[1].time),T0+24)
  local bad=hold(T0,{'wireguard','key=AAAA/BBBB+=','endpoint 1.2.3.4:51820','Wireguard'});bad.token=TOKEN;bad.endpoint='1.2.3.4:51820';bad.why='bad why'
  ring=telegram.outside_push(canon.object(),bad)
  ring=telegram.outside_push(ring,canon.object({decision='HOLD',trigger='123:abc/def',packages=canon.array({}),why='X',time=canon.float(T0)}))
  ring=telegram.outside_push(ring,canon.object({decision='ELSE',trigger='PAIR-X',packages=canon.array({}),why='X',time=canon.float(T0)}))
  t.eq(#ring.items,1);t.eq(ring.items[1].packages[1],'wireguard');t.eq(#ring.items[1].packages,1);t.eq(ring.items[1].why,'UNCLASSIFIED')
  local text=canon.encode(ring)
  for _,secret in ipairs({'SYNTHETIC','1.2.3.4','AAAA','endpoint','token'}) do t.eq(has(text,secret),false,secret) end
end)

-- pair.tick: the same fixtures as lua/test_outside_change.lua
local function net_for(observed)
  return {configs=function() return observed end,
    changed=function(state,obs,skip)
      local skipped={};for k,v in pairs(skip or {}) do if type(k)=='number' then skipped[v]=true else skipped[k]=v end end
      for name,sha in pairs(state.protected) do
        if name~='route_policy' and not skipped[name] and obs[name]~=sha then return true end
      end
      return false
    end,
    network=function() return canon.array({}) end,identity=function() return string.rep('b',64) end,client_down=function() return false end}
end
local function protected_set()
  local f=io.open(t.here..'/../outside_change_cases.json','rb');local data=canon.decode(f:read('*a'));f:close()
  local p=canon.object({});for k,v in pairs(data.protected) do p[k]=v end
  return p
end
local function running(env,protected)
  env.run.fs.write_atomic(env.runtime..'/pair-auto-control.json',canon.encode(canon.object({mode='on',revision=env.revision,time=canon.float(env.run.wall()),id=string.rep('11',16),request_source='manual'})))
  pair.save(env,canon.object({id=string.rep('11',16),phase='RUNNING',ran=true,started=canon.float(env.run.wall()-1000),revision=env.revision,network_identity=string.rep('b',64),
    interfaces=canon.object({wgclient1='wgclient',ovpnclient1='ovpnclient'}),protected=protected,owned=canon.array({}),
    before_flags=canon.object({wgclient1='0',ovpnclient1='0'}),process_bindings=env.backend.selection.process_bindings,order=canon.array({'r1','r2'}),policy_hash=t.HEX64,
    policy_roles=pair.policy.proof(env.backend.selection)}))
end
local function ring_of(env) return t.read(env,env.runtime..'/'..telegram.OUTSIDE_FILE) end

t.test('pair.tick: an ADOPT and a HOLD go into the ring once, names only; the ADOPT reaches the sender after ARMED is gone',function()
  local protected=protected_set()
  local observed=canon.object({});for k,v in pairs(protected) do observed[k]=v end;observed.wireless='l2';observed.dhcp='d2'
  local env=t.env();env.net=net_for(observed)
  running(env,protected)
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  t.eq(t.read(env,env.runtime..'/native-status.json').state,'ARMED')
  local ring=ring_of(env)
  t.eq({#ring.items,ring.items[1].decision,ring.items[1].packages[1],ring.items[1].packages[2]},{1,'ADOPT','dhcp','wireless'})
  -- the sender's next round sees an ordinary status: the ADOPT is still told
  local d=fake();d.files[d.runtime..'/'..telegram.OUTSIDE_FILE]=canon.encode(ring)
  local now=canon.number(ring.items[1].time)+300
  deliver(d,now,nil,canon.object({native_failover=canon.object({state='OBSERVING',reason='PAIR-WATCHING',time=canon.float(now)})}))
  t.eq(#d.sent,1);t.truthy(has(d.sent[1],'PAIR-OUTSIDE-CHANGE-ADOPTED'));t.truthy(has(d.sent[1],'Changed packages: dhcp wireless'));t.truthy(has(d.sent[1],'Nothing to do.'))
  -- wireguard: HELD, one item, the next pass adds none
  observed=canon.object({});for k,v in pairs(protected) do observed[k]=v end;observed.wireguard='zz'
  env=t.env();env.net=net_for(observed)
  running(env,protected)
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  t.eq(pair.tick(env,t.settings(),env.revision),true)
  ring=ring_of(env)
  t.eq({#ring.items,ring.items[1].decision,ring.items[1].packages[1]},{1,'HOLD','wireguard'})
  t.eq(has(canon.encode(ring),'zz'),false)
end)

t.test('pair: a failing ring write never reaches Auto',function()
  local protected=protected_set()
  local observed=canon.object({});for k,v in pairs(protected) do observed[k]=v end;observed.firewall='f2'
  local env=t.env();env.net=net_for(observed)
  running(env,protected)
  local real=package.loaded['telegram'];package.loaded['telegram']={OUTSIDE_FILE='x.json',outside_push=function() error('boom') end}
  local ok,result=pcall(pair.tick,env,t.settings(),env.revision)
  package.loaded['telegram']=real
  t.eq({ok,result},{true,true});t.eq(pair.read_state(env).phase,'HELD')
end)

t.test('deliver: a HOLD is one message with packages and what to do; told once',function()
  local d=fake();record(d,hold(T0))
  local public,state,sent=deliver(d,T0+30)
  t.eq(#d.sent,1);t.eq(sent,false,'no report was due')
  for _,part in ipairs({'PAIR-OUTSIDE-CHANGE-HELD','Changed packages: wireguard firewall','Trigger: PAIR-EXTERNAL-CONFIG-CHANGE','press Stop, then Start',
      'Изменённые пакеты: wireguard firewall','«Стоп», затем «Старт»'}) do t.truthy(has(d.sent[1],part),part) end
  t.truthy(telegram.valid(state));t.eq(state.last_code,'TELEGRAM-DELIVERED')
  deliver(d,T0+90);deliver(d,T0+900);t.eq(#d.sent,1,'told once')
end)

t.test('deliver: one message per class per 10 min, the rest told together afterwards',function()
  local d=fake()
  record(d,hold(T0));deliver(d,T0+5);t.eq(#d.sent,1)
  record(d,hold(T0+60,{'firewall'}));record(d,hold(T0+120,{'ovpnclient'}))
  deliver(d,T0+130);deliver(d,T0+400);t.eq(#d.sent,1,'held back inside the window')
  record(d,adopt(T0+410));deliver(d,T0+420)
  t.eq(#d.sent,2,'another class has its own window');t.truthy(has(d.sent[2],'ADOPTED'))
  deliver(d,T0+606)
  t.eq(#d.sent,3);t.truthy(has(d.sent[3],'Changed packages: ovpnclient'))
  t.truthy(has(d.sent[3],'1 earlier decision(s) of this class since'));t.truthy(has(d.sent[3],'не отправленных отдельно: 1'))
  deliver(d,T0+2000);t.eq(#d.sent,3)
end)

t.test('deliver: no secret in any text',function()
  local d=fake()
  local h=hold(T0,{'wireguard','private_key=QUJDRA=='});h.endpoint='203.0.113.7:51820';record(d,h)
  local a=adopt(T0+1);a.key='FAKEQUJDRA==';record(d,a)  -- an obviously fake test value (secret scan); still contains QUJDRA
  deliver(d,T0+10)
  t.eq(#d.sent,2)
  for _,text in ipairs(d.sent) do
    for _,secret in ipairs({TOKEN,CHAT,'QUJDRA','203.0.113.7','private_key'}) do t.eq(has(text,secret),false,secret) end
  end
end)

t.test('deliver: Telegram off or not configured -> no message; told once it is on',function()
  local d=fake();record(d,hold(T0))
  for _,change in ipairs({{telegram_enabled='0'},{telegram_enabled=''},{telegram_token=''},{telegram_chat='not a chat'}}) do
    local saved={};for k,v in pairs(d.cfg) do saved[k]=v end
    for k,v in pairs(change) do d.cfg[k]=v end
    deliver(d,T0+10)
    d.cfg=saved
  end
  t.eq(#d.sent,0)
  deliver(d,T0+20);t.eq(#d.sent,1)
end)

t.test('deliver: a failed send keeps the backoff and is not lost; an old decision is marked, not sent',function()
  local d=fake();record(d,hold(T0))
  d.fail=telegram.rejection(429,600)
  local _,state=deliver(d,T0+10)
  t.eq({state.last_code,canon.number(state.retry_after),canon.number(state.attempt)},{'TELEGRAM-RATE-LIMIT',600,T0+10})
  d.fail=nil
  deliver(d,T0+300,{attempt=state.attempt,retry_after=state.retry_after,last_code=state.last_code,known_failures=state.known_failures})
  t.eq(#d.sent,0,'the backoff holds')
  deliver(d,T0+700);t.eq(#d.sent,1)
  local old=fake();record(old,hold(T0))
  deliver(old,T0+telegram.OUTSIDE_MAX_AGE+1);deliver(old,T0+telegram.OUTSIDE_MAX_AGE+700);t.eq(#old.sent,0)
end)

t.test('BH-05: a wall-clock step (boot before NTP) does not drop a fresh HOLD',function()
  local d=fake();record(d,hold(T0),50)
  t.eq(canon.number(canon.decode(d.files[d.runtime..'/'..telegram.OUTSIDE_FILE]).items[1].mono),50)
  d.mono=80;deliver(d,T0+10*3600)
  t.eq(#d.sent,1);t.truthy(has(d.sent[1],'PAIR-OUTSIDE-CHANGE-HELD'))
  d.mono=200;deliver(d,T0+10*3600+900);t.eq(#d.sent,1,'told once')
end)

t.test('BH-05: old by the monotonic clock is marked, not sent; an unusable clock falls back to the wall clock',function()
  local d=fake();record(d,hold(T0),50)
  d.mono=50+telegram.OUTSIDE_MAX_AGE+1;deliver(d,T0+5);t.eq(#d.sent,0)
  d.mono=50+telegram.OUTSIDE_MAX_AGE+700;deliver(d,T0+700);t.eq(#d.sent,0)
  local b=fake();record(b,hold(T0),50)
  b.mono=10;deliver(b,T0+telegram.OUTSIDE_MAX_AGE+1);t.eq(#b.sent,0,'behind the stamp: the wall clock decides')
  record(b,hold(T0+1,{'firewall'}),50);b.mono=nil;deliver(b,T0+30);t.eq(#b.sent,1)
  -- a mono already in the verdict is kept; a bad one is dropped
  local ring=telegram.outside_push(canon.object(),(function() local h=hold(T0);h.mono=canon.float(7);return h end)(),99)
  t.eq(canon.number(ring.items[1].mono),7)
  ring=telegram.outside_push(canon.object(),hold(T0),-1);t.eq(ring.items[1].mono,nil)
end)

t.test('deliver: the told keys stay bounded by the ring',function()
  local d=fake()
  for i=0,39 do record(d,hold(T0+i*700));deliver(d,T0+i*700+5) end
  t.eq(#d.sent,40)
  local seen=canon.decode(d.files[d.runtime..'/'..telegram.OUTSIDE_SEEN])
  t.truthy(#seen.done<=telegram.OUTSIDE_KEEP)
end)

t.test('ring: RELEASE entries keep their STOP/START kind; a missing or unknown kind is dropped; codes and names only',function()
  local ring=telegram.outside_push(canon.object(),release(T0,'STOP'))
  ring=telegram.outside_push(ring,release(T0,'START'))
  ring=telegram.outside_push(ring,release(T0,'START'))
  t.eq(#ring.items,2)
  t.eq({ring.items[1].decision,ring.items[1].release,ring.items[1].why,ring.items[1].packages[2]},{'RELEASE','STOP','OWNER-STOP','firewall'})
  t.eq({ring.items[2].decision,ring.items[2].release,ring.items[2].why},{'RELEASE','START','OWNER-START'})
  t.truthy(ring.items[1].key~=ring.items[2].key)
  local bad=canon.object()
  for _,kind in ipairs({'ADOPT','stop'}) do bad=telegram.outside_push(bad,(function() local r=release(T0,'STOP');r.release=kind;return r end)()) end
  bad=telegram.outside_push(bad,(function() local r=release(T0,'STOP');r.release=nil;return r end)())
  bad=telegram.outside_push(bad,(function() local r=release(T0,'STOP');r.release=true;return r end)())
  bad=telegram.outside_push(bad,canon.object({decision='STOP',trigger='PAIR-EXTERNAL-CONFIG-CHANGE',packages=canon.array({}),why='OWNER-STOP',time=canon.float(T0)}))
  t.eq(#bad.items,0)
  local v=release(T0,'START',{'wireguard','key=AAAA/BBBB+=','endpoint 1.2.3.4:51820'});v.token=TOKEN
  local one=telegram.outside_push(canon.object(),v)
  t.eq(#one.items[1].packages,1)
  for _,secret in ipairs({'SYNTHETIC','1.2.3.4','AAAA','endpoint','token'}) do t.eq(has(canon.encode(one),secret),false,secret) end
end)

t.test('deliver: RELEASE texts (EN then RU), told once, privacy',function()
  local d=fake();record(d,release(T0,'STOP'))
  deliver(d,T0+30)
  t.eq(#d.sent,1)
  for _,part in ipairs({'PAIR-OUTSIDE-CHANGE-RELEASED','hold ended: owner Stop','Trigger: PAIR-EXTERNAL-CONFIG-CHANGE','Changed packages: wireguard firewall','Class: OWNER-STOP',
      'press Start','Удержание изменения, сделанного вне приложения, завершено: «Стоп» владельца','Изменённые пакеты: wireguard firewall','Класс: OWNER-STOP','«Старт»'}) do t.truthy(has(d.sent[1],part),part) end
  t.truthy(string.find(d.sent[1],'hold ended: owner Stop',1,true)<string.find(d.sent[1],'«Стоп» владельца',1,true),'EN first, then RU')
  for _,secret in ipairs({TOKEN,CHAT}) do t.eq(has(d.sent[1],secret),false,secret) end
  deliver(d,T0+90);deliver(d,T0+900);t.eq(#d.sent,1,'told once')
  local s=fake();record(s,release(T0,'START'))
  deliver(s,T0+30)
  t.eq(#s.sent,1)
  for _,part in ipairs({'PAIR-OUTSIDE-CHANGE-RELEASED','hold ended: owner Start, new configuration accepted','Class: OWNER-START',
      'Удержание изменения, сделанного вне приложения, завершено: «Старт» владельца, новая конфигурация принята','Класс: OWNER-START'}) do t.truthy(has(s.sent[1],part),part) end
  t.eq(has(s.sent[1],'press Start'),false)
end)

t.test('deliver: RELEASE has its own rate-limit bucket',function()
  local d=fake()
  record(d,hold(T0));deliver(d,T0+5);t.eq(#d.sent,1)
  record(d,release(T0+10,'STOP'));deliver(d,T0+20)
  t.eq(#d.sent,2,'a HOLD message does not hold back a RELEASE');t.truthy(has(d.sent[2],'RELEASED'))
  record(d,release(T0+100,'START',{'firewall'}));record(d,release(T0+200,'STOP',{'dhcp'}))
  deliver(d,T0+300);t.eq(#d.sent,2,'held back inside the RELEASE window')
  deliver(d,T0+700)
  t.eq(#d.sent,3);t.truthy(has(d.sent[3],'Changed packages: dhcp'));t.truthy(has(d.sent[3],'owner Stop'));t.truthy(has(d.sent[3],'1 earlier decision(s) of this class since'))
  record(d,adopt(T0+710));deliver(d,T0+720)
  t.eq(#d.sent,4,'an ADOPT is not held back by RELEASE messages')
end)

t.test('pair.release_session: the owner Start records a START release; the automatic adoption records none; a failing write never stops it',function()
  local protected=protected_set()
  local function held_env()
    local env=t.env();env.net=net_for(protected)
    running(env,protected)
    local state=pair.read_state(env);state.phase='HELD';state.recovery_error='PAIR-EXTERNAL-CONFIG-CHANGE';pair.save(env,state)
    return env,pair.read_state(env)
  end
  local env,state=held_env()
  t.eq(pair.release_session(env,state,'PAIR-EXTERNAL-CONFIG-CHANGE'),true)
  t.eq(pair.read_state(env).phase,'STOPPED')
  local ring=ring_of(env)
  t.eq(#ring.items,1)
  t.eq({ring.items[1].decision,ring.items[1].release,ring.items[1].why,ring.items[1].trigger},{'RELEASE','START','OWNER-START','PAIR-EXTERNAL-CONFIG-CHANGE'})
  t.truthy(has(telegram.outside_text(ring.items[1]),'hold ended: owner Start, new configuration accepted'))
  env,state=held_env()
  t.eq(pair.release_session(env,state,'PAIR-EXTERNAL-CONFIG-CHANGE',pair.readopt_class(env,state,'PAIR-EXTERNAL-CONFIG-CHANGE'),'automatic'),true)
  t.eq((ring_of(env) or canon.object()).items,nil,'the automatic adoption is told by readopt_running as ADOPT, never as a RELEASE')
  env,state=held_env()
  local real=package.loaded['telegram'];package.loaded['telegram']={OUTSIDE_FILE='x.json',outside_push=function() error('boom') end}
  local ok,result=pcall(pair.release_session,env,state,'PAIR-EXTERNAL-CONFIG-CHANGE')
  package.loaded['telegram']=real
  t.eq({ok,result},{true,true});t.eq(pair.read_state(env).phase,'STOPPED')
end)

t.run()
