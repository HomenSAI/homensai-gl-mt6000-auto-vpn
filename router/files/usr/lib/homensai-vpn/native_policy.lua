-- Internal root-only inventory for the native controller. Never an RPC response.
local c=require('uci').cursor()
local json=require('cjson')
local sections={}
c:foreach('route_policy',nil,function(s) sections[#sections+1]=s end)
local defaults={}
c:foreach('firewall','defaults',function(s) defaults[#defaults+1]=s end)
local own=c:get_all('homensai_vpn','main') or {}
local settings={}
for _,k in ipairs({'native_enabled','native_trial','native_until','native_ack','native_session_loss','native_order_direction','native_baseline_exit','native_prepare_acceleration','plan_source','plan_target'}) do
 settings[k]=own[k]
end
print(json.encode({sections=sections,settings=settings,firewall_defaults=defaults,
 hnat_enable=c:get('mtkhnat','global','enable'),
 ipv6=c:get('glipv6','globals','enabled'),lan=c:get('network','lan','device') or c:get('network','lan','ifname')}))
