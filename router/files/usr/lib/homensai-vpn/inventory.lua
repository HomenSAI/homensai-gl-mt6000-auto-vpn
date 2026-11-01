-- Metadata only. Never emit path, endpoint credentials, passwords or private keys.
local uci=require('uci').cursor()
local json=require('cjson')
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
    priority=tonumber(s.priority) or 100,enabled=s.enabled~='0'}
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
  main.onboarding_version=tonumber(s.onboarding_version) or 0
  main.onboarding_complete=s.onboarding_complete=='1' and s.onboarding_version=='1'
  main.onboarding_pair_deferred=s.onboarding_pair_deferred=='1'
  main.appearance_language=(s.appearance_language=='en' or s.appearance_language=='ru') and s.appearance_language or ''
  main.appearance_design=(s.appearance_design=='a' or s.appearance_design=='b' or s.appearance_design=='c') and s.appearance_design or 'b'
  main.appearance_theme=(s.appearance_theme=='system' or s.appearance_theme=='light' or s.appearance_theme=='dark') and s.appearance_theme or ''
  main.recovery_return_policy=s.recovery_return_policy=='hold_reserve' and 'hold_reserve' or 'healthy_primary'
  main.recovery_failures=math.max(3,math.min(10,tonumber(s.recovery_failures) or 3))
  main.recovery_successes=math.max(2,math.min(10,tonumber(s.recovery_successes) or 2))
  main.recovery_cooldown=math.max(60,math.min(1800,tonumber(s.recovery_cooldown) or 60))
  main.recovery_min_dwell=math.max(60,math.min(3600,tonumber(s.recovery_min_dwell) or 60))
  main.recovery_primary_successes=math.max(2,math.min(10,tonumber(s.recovery_primary_successes) or 2))
  main.recovery_primary_stable=math.max(30,math.min(600,tonumber(s.recovery_primary_stable) or 30))
  local function attempt_number(raw,default,maximum)
    if type(raw)~='string' or not raw:match('^%d%d?%d?$') then return default end
    local n=tonumber(raw);if not n or n<1 or n>maximum then return default end
    return n
  end
  main.recovery_attempt_limit=attempt_number(s.recovery_attempt_limit,3,10)
  main.recovery_attempt_window=attempt_number(s.recovery_attempt_window,15,15)

  main.speed_enabled=s.speed_enabled=='1'
  main.speed_auto_new=s.speed_auto_new=='1'
  main.speed_budget_mib=math.max(1,math.min(32,tonumber(s.speed_budget_mib) or 8))
  main.speed_duration=math.max(2,math.min(15,tonumber(s.speed_duration) or 5))
  main.speed_streams=math.max(1,math.min(4,tonumber(s.speed_streams) or 2))
  main.speed_daily_mib=math.max(1,math.min(1024,tonumber(s.speed_daily_mib) or 128))
  main.speed_busy_mbps=math.max(1,math.min(1000,tonumber(s.speed_busy_mbps) or 2))
  main.plan_enabled=s.plan_enabled=='1'
  main.pair_auto_mode=s.pair_auto_mode=='router-probed-ipv4' and 'router-probed-ipv4' or 'off'
  main.native_enabled=s.native_enabled=='1'
  main.native_session_loss=s.native_session_loss=='1'
  main.native_duration=math.max(1,math.min(240,tonumber(s.native_duration) or 10))
  main.native_until=s.native_until or ''
  main.terms_version=s.terms_version or ''
  main.plan_source=s.plan_source or ''
  main.plan_target=s.plan_target or ''
  main.plan_source_tunnel=s.plan_source_tunnel or ''
  main.plan_target_tunnel=s.plan_target_tunnel or ''
  main.telegram_enabled=s.telegram_enabled=='1'
  main.telegram_destination=s.telegram_chat or ''
  main.telegram_interval=math.max(5,math.min(10080,tonumber(s.telegram_interval) or 60))
  main.telegram_schedule=s.telegram_schedule or 'interval'
  main.telegram_hour=math.max(0,math.min(23,tonumber(s.telegram_hour) or 7))
  main.telegram_weekly=s.telegram_weekly~='0'
  main.telegram_monthly=s.telegram_monthly~='0'
  main.telegram_items=s.telegram_items or ''
  main.telegram_configured=type(s.telegram_token)=='string' and #s.telegram_token>20 and type(s.telegram_chat)=='string' and #s.telegram_chat>0
  main.interval=math.max(10,math.min(300,tonumber(s.interval) or 10))
  local level=tonumber(s.probe_level)
  main.probe_level=(level and level>=1 and level<=5 and level==math.floor(level)) and level or 0
  main.probe_boost=s.probe_boost~='0'
  local metric=s.response_metric
  main.response_metric=(metric=='icmp-1.1.1.1' or metric=='icmp-8.8.8.8' or metric=='icmp-9.9.9.9' or metric=='websites') and metric or 'icmp-1.1.1.1'
  main.response_compare=s.response_compare=='1'
  main.fast_switch=s.fast_switch~='0'
  main.stats_mode=s.stats_mode=='diagnostic' and 'diagnostic' or 'work'
  main.stats_until=math.max(0,math.floor(tonumber(s.stats_until) or 0))
  main.lua_core=s.lua_core=='1'
  local measure=tonumber(s.measure_interval)
  main.measure_interval=(measure and measure>=30 and measure<=300) and math.floor(measure) or 0
  -- Owner ping cadence (probe_policy.ping_interval): 10..300 s in steps of 10, otherwise once a minute.
  local ping=tonumber(s.ping_interval)
  main.ping_interval=(ping and ping>=10 and ping<=300 and ping%10==0) and math.floor(ping) or 60
  main.checkpoint=math.max(300,math.min(3600,tonumber(s.checkpoint) or 900))
  main.probe_limit=math.max(1,math.min(32,tonumber(s.probe_limit) or 16))
  main.live_log_limit=math.max(1,math.min(2000,math.floor(tonumber(s.live_log_limit) or 2000)))
  main.history_days=math.max(1,math.min(7,math.floor(tonumber(s.history_days) or 7)))
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
