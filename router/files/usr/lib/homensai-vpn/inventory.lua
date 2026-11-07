-- Metadata only. Never emit path, endpoint credentials, passwords or private keys.
local uci=require('uci').cursor()
local json=require('cjson')
-- BH2-01/02 (bug hunt 07.11.2026): every numeric option is read by one strict finite parser. Lua's tonumber (strtod) also
-- reads 'nan', 'inf', '1e999', '0x3c' and '1e1': cjson.encode refused NaN/Inf (the whole inventory failed: Auto
-- NATIVE-SYSTEM-001, no settings page) and math.min(hi,NaN) is hi. Grammar of recovery_settings.normalized /
-- pair.recovery_normalized (F-46/R2-03): blanks, a sign, at most 9 digits; frac: one '.' too, at most 15 digits.
-- Anything else is malformed and takes the documented default.
local function num(raw,frac)
  if type(raw)~='string' then return nil end
  local sign,int,dot,fr=raw:match('^%s*([+-]?)(%d*)(%.?)(%d*)%s*$')
  if not sign or #int+#fr==0 or #int+#fr>(frac and 15 or 9) or (dot~='' and not frac) then return nil end
  local v=tonumber(sign..int..dot..fr)
  if v==nil or v~=v or v==math.huge or v==-math.huge then return nil end
  return v+0
end
local function clamp(raw,lo,hi,default) local v=num(raw);if v==nil then return default end;return math.max(lo,math.min(hi,v)) end
local interfaces={}
uci:foreach('network','interface',function(s)
  if (s.proto=='ovpnclient' or s.proto=='wgclient') and s.config then
    local protocol=s.proto=='wgclient' and 'wireguard' or 'openvpn'
    local key=protocol..':'..s.config
    if interfaces[key] then interfaces[key].ambiguous=true
    else interfaces[key]={logical=s['.name'],protocol=protocol,administrative_state=s.disabled=='1' and 'disabled' or (s.disabled==nil or s.disabled=='0') and 'enabled' or 'unknown'} end
  end
end)
local profiles={}
for _,entry in ipairs({{'ovpnclient','openvpn'},{'wireguard','wireguard'}}) do
  uci:foreach(entry[1],nil,function(s)
    local section=s['.name'] or ''
    local a,b=section:match('^(%d+)_(%d+)$')
    local peer=section:match('^peer_(%d+)$')
    if (entry[2]=='openvpn' and a and b) or (entry[2]=='wireguard' and peer) then
      local bound=interfaces[entry[2]..':'..section]
      if bound and bound.ambiguous then bound=nil end
      local group=tostring(s.group_id or a or '')
      local valid_group=#group<=20 and group:match('^%d+$')
      local logical=bound and bound.logical
      if logical and (not logical:match('^[A-Za-z0-9_.-]+$') or #logical>64) then logical=nil end
      profiles[#profiles+1]={id=entry[2]..':'..section,section=section,protocol=entry[2],
        name=s.name or s.description or s.remark or section,
        group_id=group,profile_id=tostring(b or peer or ''),
        vendor_profile_group_id=valid_group and entry[2]..':'..group or json.null,
        vendor_tunnel_id=logical and entry[2]..':'..logical or json.null,
        interface=logical or json.null,administrative_state=bound and bound.administrative_state or 'unknown'}
    end
  end)
end
local channels={}
uci:foreach('homensai_vpn','server',function(s)
  channels[#channels+1]={id=s['.name'],profile=s.profile or '',name=s.name or '',channel=s.channel or 'default',
    priority=(function(v) return v and v>=1 and v<=1000 and v or 100 end)(num(s.priority)),enabled=s.enabled~='0'}
end)
local main={enabled=false,interval=10,checkpoint=900,probe_limit=16,live_log_limit=2000,history_days=7,timezone='CET-1CEST,M3.5.0,M10.5.0/3',
  onboarding_version=0,onboarding_complete=false,onboarding_pair_deferred=false,
  appearance_language='',appearance_design='b',appearance_theme='',router_model='auto',monitor_only=false,deployment_mode='standard'}
uci:foreach('homensai_vpn','main',function(s)
  main.enabled=s.enabled=='1'
  main.router_model=s.router_model or 'auto'
  main.monitor_only=s.monitor_only=='1'
  main.deployment_mode=s.monitor_only=='1' and 'monitor-only' or
    (s.monitor_only==nil or s.monitor_only=='0') and 'standard' or 'invalid'
  main.setup_complete=s.setup_complete=='1'
  -- Full first-run completion is independent of the older pair-only wizard.
  main.onboarding_version=math.max(0,num(s.onboarding_version) or 0)
  main.onboarding_complete=s.onboarding_complete=='1' and s.onboarding_version=='1'
  main.onboarding_pair_deferred=s.onboarding_pair_deferred=='1'
  main.appearance_language=(s.appearance_language=='en' or s.appearance_language=='ru') and s.appearance_language or ''
  main.appearance_design=(s.appearance_design=='a' or s.appearance_design=='b' or s.appearance_design=='c') and s.appearance_design or 'b'
  main.appearance_theme=(s.appearance_theme=='system' or s.appearance_theme=='light' or s.appearance_theme=='dark') and s.appearance_theme or ''
  main.recovery_return_policy=s.recovery_return_policy=='hold_reserve' and 'hold_reserve' or 'healthy_primary'
  main.recovery_failures=clamp(s.recovery_failures,2,10,3)
  main.recovery_successes=clamp(s.recovery_successes,2,10,2)
  main.recovery_cooldown=clamp(s.recovery_cooldown,60,1800,60)
  main.recovery_min_dwell=clamp(s.recovery_min_dwell,60,3600,60)
  main.recovery_primary_successes=clamp(s.recovery_primary_successes,2,10,2)
  main.recovery_primary_stable=clamp(s.recovery_primary_stable,30,600,120)
  main.recovery_rescue_stable=clamp(s.recovery_rescue_stable,0,60,10)
  local function attempt_number(raw,default,maximum)
    if type(raw)~='string' or not raw:match('^%d%d?%d?$') then return default end
    local n=tonumber(raw);if not n or n<1 or n>maximum then return default end
    return n
  end
  main.recovery_attempt_limit=attempt_number(s.recovery_attempt_limit,3,10)
  main.recovery_attempt_window=attempt_number(s.recovery_attempt_window,15,15)
  -- What one monitor pass measures (probe_plan.py): phases on an absolute grid on unless '0'; reserve budget off unless
  -- reserve_probe_interval is 20..120 s.
  main.probe_spread=s.probe_spread~='0'
  local reserve=num(s.reserve_probe_interval)
  main.reserve_probe_interval=reserve and reserve>=20 and reserve<=120 and reserve or 0
  -- The pause after a failed supervisor pass (retry_policy.py): 'fibonacci' default, 'fixed' the former 5 s.
  main.retry_backoff=s.retry_backoff=='fixed' and 'fixed' or 'fibonacci'
  -- Damping of the return (recovery_settings.py flap_*): absent = its default there.
  main.recovery_flap_model=s.recovery_flap_model=='halflife' and 'halflife' or 'double'
  main.recovery_flap_limit=attempt_number(s.recovery_flap_limit,2,10)
  main.recovery_flap_window=attempt_number(s.recovery_flap_window,60,120)
  main.recovery_flap_halflife=clamp(s.recovery_flap_halflife,600,3600,1800)
  main.recovery_flap_suppress=clamp(s.recovery_flap_suppress,1000,3000,1500)
  main.recovery_flap_reuse=clamp(s.recovery_flap_reuse,200,1000,500)
  -- Channel-failure model (channel_model.py/.lua, owner decision 03.11.2026): 'hmm' (default, standard),
  -- 'hmm-fast' (fast) or 'consecutive' (the previous rule: recovery_failures failed checks in a row).
  main.failure_model=(s.failure_model=='hmm-fast' or s.failure_model=='consecutive') and s.failure_model or 'hmm'
  -- Master slider / network advisor (2.1.0-alpha9, advisor.py): numeric detector options (absent = the preset of
  -- failure_model, exactly alpha8; channel_model.NUMERIC), the slider position and the advisor's mode / window.
  local function ranged(raw,low,high) local v=num(raw,true);if v and v==v and v>=low and v<=high then return v end;return nil end
  main.hmm_theta=ranged(s.hmm_theta,0.5,0.99)
  main.hmm_dur_b=ranged(s.hmm_dur_b,1,15)
  main.return_pg=ranged(s.return_pg,0.5,0.99)
  main.slider_t=ranged(s.slider_t,-0.7,1)
  -- Fast end (FAST-SWITCH-2026-11-04.ru.md): absent/0 = off; slider_fast: the advisor may recommend t < 0; slider_turbo:
  -- the expert opt-in of the heartbeat verdict (default off); the event wake is on unless '0', the parallel recheck off unless '1' (owner 05.11.2026: until measured).
  local function whole(raw,low,high) local v=ranged(raw,low,high);if v and v%1==0 then return v end;return nil end
  main.hmm_or_failures=whole(s.hmm_or_failures,2,10)
  main.turbo_beats=whole(s.turbo_beats,3,8)
  main.slider_fast=s.slider_fast=='1'
  main.slider_turbo=s.slider_turbo=='1'
  main.parallel_recheck=s.parallel_recheck=='1'
  main.auto_event_wake=s.auto_event_wake~='0'
  main.advisor_mode=(s.advisor_mode=='auto' or s.advisor_mode=='manual') and s.advisor_mode or 'advice'
  local window=num(s.advisor_window)
  main.advisor_window=(window==1 or window==30) and window or 7

  main.speed_enabled=s.speed_enabled=='1'
  main.speed_auto_new=s.speed_auto_new=='1'
  main.speed_budget_mib=clamp(s.speed_budget_mib,1,32,8)
  main.speed_duration=clamp(s.speed_duration,2,15,5)
  main.speed_streams=clamp(s.speed_streams,1,4,2)
  main.speed_daily_mib=clamp(s.speed_daily_mib,1,1024,128)
  main.speed_busy_mbps=clamp(s.speed_busy_mbps,1,1000,2)
  main.plan_enabled=s.plan_enabled=='1'
  main.pair_auto_mode=s.pair_auto_mode=='router-probed-ipv4' and 'router-probed-ipv4' or 'off'
  main.native_enabled=s.native_enabled=='1'
  main.native_session_loss=s.native_session_loss=='1'
  main.native_duration=clamp(s.native_duration,1,240,10)
  main.native_until=s.native_until or ''
  main.terms_version=s.terms_version or ''
  main.plan_source=s.plan_source or ''
  main.plan_target=s.plan_target or ''
  main.plan_source_tunnel=s.plan_source_tunnel or ''
  main.plan_target_tunnel=s.plan_target_tunnel or ''
  main.telegram_enabled=s.telegram_enabled=='1'
  -- Review F-14 (06.11.2026): the inventory is a read-ACL method, so readers get only a mask of the Telegram
  -- destination (owner decision 07.11.2026: from eight characters on its first two and last two characters around
  -- '…', e.g. '12…89'; otherwise only '…') plus telegram_configured. The same rule as agent.masked_destination;
  -- setup_config keeps the stored destination when the page sends this mask back.
  local chat=type(s.telegram_chat)=='string' and s.telegram_chat or ''
  local head,tail='',''
  if #chat>=8 then head,tail=chat:sub(1,2),chat:sub(-2) end
  if (head..tail):find('[^%w_@%-]') then head,tail='','' end
  main.telegram_destination=#chat>0 and (head..'\226\128\166'..tail) or ''
  main.telegram_interval=clamp(s.telegram_interval,5,10080,60)
  main.telegram_schedule=s.telegram_schedule or 'interval'
  main.telegram_hour=clamp(s.telegram_hour,0,23,7)
  main.telegram_weekly=s.telegram_weekly~='0'
  main.telegram_monthly=s.telegram_monthly~='0'
  main.telegram_items=s.telegram_items or ''
  main.telegram_configured=type(s.telegram_token)=='string' and #s.telegram_token>20 and type(s.telegram_chat)=='string' and #s.telegram_chat>0
  main.interval=clamp(s.interval,10,300,10)
  local level=num(s.probe_level)
  main.probe_level=(level and level>=1 and level<=5 and level==math.floor(level)) and level or 0
  main.probe_boost=s.probe_boost~='0'
  local metric=s.response_metric
  main.response_metric=(metric=='icmp-1.1.1.1' or metric=='icmp-8.8.8.8' or metric=='icmp-9.9.9.9' or metric=='websites') and metric or 'icmp-1.1.1.1'
  main.response_compare=s.response_compare=='1'
  main.fast_switch=s.fast_switch~='0'
  main.server_pick=s.server_pick=='1'  -- best server inside a channel (2.1.0): off unless the owner switched it on
  -- how it picks (server_pick.py MODELS): 'simple' (the 20 % rule) unless the owner set option server_pick_model 'bayes'
  -- (private/math/bayes-pick: far fewer useless changes and probes, but slower to find a better server)
  main.server_pick_model=s.server_pick_model=='bayes' and 'bayes' or 'simple'
  -- GL sensors (docs/architecture/GL-SENSORS-2026-11-04.ru.md): only an explicit '0' turns each part off; the k-of-n
  -- heartbeat quorum is off unless '1'. wan_recover_grace: 0..120 s (0 = no WAN-RECOVERING hold), otherwise 30.
  main.wan_sensor=s.wan_sensor~='0'
  local grace=num(s.wan_recover_grace)
  main.wan_recover_grace=(grace and grace>=0 and grace<=120 and grace%1==0) and math.floor(grace) or 30
  main.wg_events=s.wg_events~='0'
  main.stall_sensor=s.stall_sensor~='0'
  main.stall_veto=s.stall_veto~='0'
  main.heartbeat_quorum=s.heartbeat_quorum=='1'
  -- per-target probe log (probe_target_log.py/.lua): a RAM ring of the result of each probe target per pass for the
  -- sensor-correlation study; default ON, only an explicit '0' switches it off
  main.probe_target_log=s.probe_target_log~='0'
  -- CUSUM trigger of the dense episode, soft RTT signal, per-minute RTT log (docs/architecture/CUSUM-TRIGGER-2026-11-04.ru.md)
  main.cusum_trigger=s.cusum_trigger=='1'
  main.rtt_watch=s.rtt_watch=='1'
  main.heartbeat_rtt_log=s.heartbeat_rtt_log~='0'
  -- trust on first use of the VPN servers' keys (server_pin.py MODES): warn (default, also when the option is absent or
  -- unknown), enforce, off; read here so that the page shows the saved choice
  main.server_key_pin=(s.server_key_pin=='enforce' or s.server_key_pin=='off') and s.server_key_pin or 'warn'
  main.stats_mode=s.stats_mode=='diagnostic' and 'diagnostic' or 'work'
  -- the grammar of the stats_until twins (stats_mode.until / accounting stats.until_time): digits, an optional fraction
  local su_int,su_dot,su_fr=string.match(type(s.stats_until)=='string' and s.stats_until or '','^(%d+)(%.?)(%d*)$')
  main.stats_until=su_int and #su_int<=12 and #su_fr<=6 and math.floor(tonumber(su_int..su_dot..su_fr)) or 0
  main.lua_core=s.lua_core=='1'
  local measure=num(s.measure_interval)
  main.measure_interval=(measure and measure>=30 and measure<=300) and math.floor(measure) or 0
  -- Owner ping cadence (probe_policy.ping_interval): 10..300 s in steps of 10, otherwise once a minute.
  local ping=num(s.ping_interval)
  main.ping_interval=(ping and ping>=10 and ping<=300 and ping%10==0) and math.floor(ping) or 60
  -- SQM (sqm.py / lua/sqm.lua): cake on the tunnel egress; off unless the owner switched it on AND set an upload
  -- rate (1000..1000000 kbit/s); anything else reads as 0 = not set, and nothing is shaped.
  main.sqm_enabled=s.sqm_enabled=='1'
  local sqm_kbit=type(s.sqm_upload_kbit)=='string' and s.sqm_upload_kbit:match('^%d%d?%d?%d?%d?%d?%d?$') and tonumber(s.sqm_upload_kbit)
  main.sqm_upload_kbit=(sqm_kbit and sqm_kbit>=1000 and sqm_kbit<=1000000) and sqm_kbit or 0
  main.checkpoint=clamp(s.checkpoint,300,3600,900)
  main.probe_limit=clamp(s.probe_limit,1,32,16)
  main.live_log_limit=clamp(s.live_log_limit,1,2000,2000)
  main.history_days=clamp(s.history_days,1,7,7)
  -- Owner retention (retention_settings.choice): time (1..7, 14, 30 days) or size (1..32 MB); absent -> history_days.
  main.stats_retention_mode=(s.stats_retention_mode=='time' or s.stats_retention_mode=='size') and s.stats_retention_mode or nil
  local rdays=type(s.stats_retention_days)=='string' and s.stats_retention_days:match('^%d%d?$') and tonumber(s.stats_retention_days)
  main.stats_retention_days=rdays or nil
  local rmb=type(s.stats_retention_mb)=='string' and s.stats_retention_mb:match('^%d%d?$') and tonumber(s.stats_retention_mb)
  main.stats_retention_mb=rmb or nil
end)
-- Model preference never replaces hardware detection or controller platform guards.
local board_file=io.open('/tmp/sysinfo/board_name','r')
local board=board_file and board_file:read(128) or ''
if board_file then board_file:close() end
main.detected_router_model=({['glinet,gl-mt6000']='mt6000',['glinet,mt3000-snand']='mt3000'})[board:match('^%s*(.-)%s*$')] or 'unknown'
main.router_model_matches=main.router_model=='auto' or main.router_model==main.detected_router_model
local by_interface={}
for _,p in ipairs(profiles) do if type(p.interface)=='string' then by_interface[p.interface]=p end end
local native_candidates={}
local order=0
local function empty(value) return value==nil or value=='' or (type(value)=='table' and #value==0) end
uci:foreach('route_policy',nil,function(s)
  local p=by_interface[s.via]
  if s['.type']=='rule' and s.enabled=='1' and s.killswitch=='1' and p
      and empty(s.from_type) and empty(s.from) and empty(s.to_type) and empty(s.to)
      and empty(s.to_manual) and empty(s.to_list_external) then
    native_candidates[#native_candidates+1]={id=p.id,order=order,protocol=p.protocol}
  end
  order=order+1
end)
local wan={}
uci:foreach('firewall','zone',function(s)
 if s.name=='wan' then
  local names=s.network or {}
  if type(names)=='string' then names={names} end
  for _,name in ipairs(names) do wan[#wan+1]=name end
 end
end)
print(json.encode({profiles=profiles,servers=channels,settings=main,native_candidates=native_candidates,wan_interfaces=wan}))
