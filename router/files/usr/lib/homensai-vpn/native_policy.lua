-- Internal root-only inventory for the native controller. Never an RPC response.
local c=require('uci').cursor()
local json=require('cjson')
local sections={}
c:foreach('route_policy',nil,function(s) sections[#sections+1]=s end)
local defaults={}
c:foreach('firewall','defaults',function(s) defaults[#defaults+1]=s end)
local own=c:get_all('homensai_vpn','main') or {}
local settings={pair_auto_mode=own.pair_auto_mode}
for _,k in ipairs({'router_model','terms_version','monitor_only','native_proof_scope','native_enabled','native_trial','native_until','native_ack','native_session_loss','native_order_direction','native_baseline_exit','native_prepare_acceleration','plan_source','plan_target','plan_source_tunnel','plan_target_tunnel','server_pick','interval','recovery_failures','recovery_successes','recovery_cooldown','recovery_min_dwell','recovery_return_policy','recovery_primary_successes','recovery_primary_stable','recovery_rescue_stable','recovery_attempt_limit','recovery_attempt_window',
  -- review 04.11.2026 (finding 2): the channel-failure model and the server-pick model decide in the supervisor too
  -- (channel_model.name, server_pick.model_name); without them it used 'hmm'/'simple' while the page showed the owner's choice
  'failure_model','server_pick_model'}) do
 settings[k]=own[k]
end
-- the numeric detector options of 2.1.0-alpha9 (channel_model.NUMERIC: hmm_theta, hmm_dur_b, return_pg) as numbers, the way
-- inventory.lua hands them to the monitor; channel_model.numeric checks the range (absent = the preset of failure_model)
for _,k in ipairs({'hmm_theta','hmm_dur_b','return_pg','hmm_or_failures','turbo_beats'}) do
 -- BH2-02: the strict decimal grammar of inventory.lua num(raw,true) (no nan/inf/hex/exponent), so both read the same value
 local raw=type(own[k])=='string' and own[k] or ''
 local sign,int,dot,fr=raw:match('^%s*([+-]?)(%d*)(%.?)(%d*)%s*$')
 local v=sign and #int+#fr>=1 and #int+#fr<=15 and tonumber(sign..int..dot..fr) or nil
 if v and v==v and v~=math.huge and v~=-math.huge then settings[k]=v+0 end
end
for _,k in ipairs({'recovery_flap_model','recovery_flap_limit','recovery_flap_window','recovery_flap_halflife','recovery_flap_suppress','recovery_flap_reuse','retry_backoff'}) do
 settings[k]=own[k]
end
-- The failure model and the master slider's detector options: Auto decides with them (channel_model.resolve / leave_rule).
-- Absent stays absent (the alpha8 preset, the same settings fingerprint); the numbers are in the guarded loop above.
for _,k in ipairs({'failure_model','slider_turbo','parallel_recheck'}) do settings[k]=own[k] end
print(json.encode({sections=sections,settings=settings,firewall_defaults=defaults,
 firewall_include={path=c:get('firewall','vpnclient','path'),type=c:get('firewall','vpnclient','type'),reload=c:get('firewall','vpnclient','reload'),enabled=c:get('firewall','vpnclient','enabled')},
 hnat_enable=c:get('mtkhnat','global','enable'),
 ipv6=c:get('glipv6','globals','enabled'),lan=c:get('network','lan','device') or c:get('network','lan','ifname')}))
