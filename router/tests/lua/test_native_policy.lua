-- The Lua supervisor decides with the owner's settings (independent review 04.11.2026, finding 2).
-- backend.B.policy() is the decoded output of native_policy.lua (the helper the Python line runs too). Its key list had
-- no failure_model: channel_model.name() fell back to 'hmm' and the owner's 'consecutive' / 'hmm-fast' (shown by the
-- monitor and the page) never reached pair.tick / the committed return. The real helper runs here with a fake UCI.
-- Python twin: tests/test_native_policy_settings.py.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local CM=require('channel_model')
local pair=require('pair')
local SP=require('server_pick')
local HELPER=t.here..'/../../files/usr/lib/homensai-vpn/native_policy.lua'

-- runs the helper with homensai_vpn.main = main; returns its settings as backend.B.policy() decodes them
local function policy(main)
  package.loaded['uci']=nil
  package.preload['uci']=function()
    return {cursor=function() return {foreach=function() end,
      get_all=function(_,package,section) if package=='homensai_vpn' and section=='main' then return main end end,
      get=function() return nil end} end}
  end
  if not pcall(require,'cjson') then package.preload['cjson']=function() return {encode=canon.encode} end end
  local out={}
  local real=print
  print=function(text) out[#out+1]=text end
  local ok,err=pcall(dofile,HELPER)
  print=real
  assert(ok,err)
  return canon.decode(out[#out]).settings
end

local OWNER={pair_auto_mode='router-probed-ipv4',failure_model='consecutive',server_pick_model='bayes',server_pick='1',interval='20',
  recovery_failures='4',recovery_successes='3',recovery_cooldown='90',recovery_min_dwell='120',recovery_return_policy='hold_reserve',
  recovery_primary_successes='3',recovery_primary_stable='200',recovery_rescue_stable='15',recovery_attempt_limit='5',recovery_attempt_window='10'}
local function with(fields) local out={};for k,v in pairs(OWNER) do out[k]=v end;for k,v in pairs(fields or {}) do out[k]=v end;return out end

t.test('every owner failure model reaches the deciders (hmm before the fix)',function()
  for _,model in ipairs({'hmm','hmm-fast','consecutive'}) do t.eq(CM.name(policy(with({failure_model=model}))),model,model) end
  t.eq(CM.name(policy(with({failure_model='typo'}))),CM.DEFAULT)
end)

t.test('the server pick model and the recovery options arrive',function()
  local settings=policy(OWNER)
  t.eq(SP.model_name(settings.server_pick_model),'bayes')
  local r=pair.recovery_normalized(settings)
  t.eq({r.failures,r.successes,r.cooldown,r.min_dwell,r.return_policy,r.primary_successes,r.primary_stable,r.attempt_limit,r.attempt_window,r.rescue_stable},
       {4,3,90,120,'hold_reserve',3,200,5,10,15})
end)

t.test('the numeric options are numbers for the supervisor (channel_model.numeric accepts numbers only)',function()
  local settings=policy(with({hmm_theta='0.9',hmm_dur_b='junk',return_pg='nan'}))
  t.eq(canon.number(settings.hmm_theta),0.9);t.eq(settings.hmm_dur_b,nil);t.eq(settings.return_pg,nil)
end)

t.test('the numeric detector options arrive (channel_model.NUMERIC, 2.1.0-alpha9 on)',function()
  if CM.NUMERIC==nil or CM.numeric==nil then return end
  local extra={failure_model='hmm'}
  for key,range in pairs(CM.NUMERIC) do extra[key]=tostring((range[1]+range[2])/2) end
  local settings=policy(with(extra))
  for key,range in pairs(CM.NUMERIC) do t.eq(CM.numeric(settings,key),(range[1]+range[2])/2,key) end
end)

t.run()
