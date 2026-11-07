// OFFLINE SYNTHETIC FIXTURE for the approved page (03.11.2026): a router-probed IPv4 continuous pair with fresh
// evidence, so the views can be checked and photographed without a router. Loaded before stub.js; enabled only by
// ?fixture=pair. Scenario: &scn=ok|reserve|stale|off|down|first. Nothing here is real router data.
(function(){
const q=new URLSearchParams(location.search);if(q.get('fixture')!=='pair')return;
const scn=q.get('scn')||'ok';
// 2.1.0-alpha10 scenes: &adv=few|auto|custom|consecutive|none (auto-adaptation), &wan=down|recovering, &key=changed|off.
// The curve is a copy of the shipped slider_curve.json anchors (offline study, not router data).
const ADV_CURVE={"version":1,"params":["theta","dur_b","losses","pg","primary_stable","rescue_stable"],"metrics":["downtime_s_day","unnecessary_per_day","failovers_per_day","switch_after_s","rides_out_s","return_after_40s_blackout_s","reserve_failure_worst_downtime_s"],"anchors":[{"t":0,"p":[0.6,3,2,0.8,120,5],"m":[218.8,0.4684,1.513,18.87,15.27,143.3,160.3]},{"t":0.1,"p":[0.6,3,2,0.9,120,5],"m":[218.8,0.4684,1.513,18.87,15.27,143.3,160.3]},{"t":0.2,"p":[0.6,3,2,0.9,120,10],"m":[218.8,0.4684,1.513,18.87,15.27,143.3,160.3]},{"t":0.3,"p":[0.6,4,2,0.9,120,10],"m":[221.5,0.2234,1.146,22.4,18.86,145,163.4]},{"t":0.4,"p":[0.6,4,2,0.95,120,10],"m":[221.5,0.2234,1.146,22.4,18.86,145,163.4]},{"t":0.5,"p":[0.6,5,2,0.95,120,10],"m":[223.9,0.1759,1.067,22.91,21,144.4,163.4]},{"t":0.6,"p":[0.6,7,2,0.95,120,10],"m":[224.6,0.1374,1.028,25.94,22,143.7,163.6]},{"t":0.7,"p":[0.6,8,2,0.95,180,10],"m":[225.4,0.0727,0.963,25.97,23.62,200.6,164.1]},{"t":0.8,"p":[0.6,8,2,0.95,300,20],"m":[226,0.0727,0.963,25.97,23.62,326.3,174.4]},{"t":0.9,"p":[0.6,8,2,0.99,300,20],"m":[226,0.0727,0.963,25.97,23.62,326.3,174.4]},{"t":1,"p":[0.6,8,2,0.99,300,20],"m":[226,0.0727,0.963,25.97,23.62,326.3,174.4]}],"alpha8":{"m":[234.8,0.0488,0.928,null,null,142,164.5],"p":[0.8,4,2,0.9,120,10]}};
// 2.1.0-alpha10 expert scenes: &adv=fast (fast segment switched on) | turbo (turbo unlocked, position -0.5); &xd=changed (some expert fields differ from the defaults).
ADV_CURVE.fast_params=["cons_f", "beat_k", "dense_interval"];ADV_CURVE.fast_anchors=[{"t":-0.1,"p":[0.6,3,2,0.8,120,5],"x":[3,null,4],"m":[180.43,0.4695,1.558,18.87,15.27,143.3,160.3]},{"t":-0.2,"p":[0.6,3,2,0.8,120,5],"x":[2,null,4],"m":[156.56,0.5575,1.772,17.07,14.18,143.3,158]},{"t":-0.3,"p":[0.5,2.5,2,0.8,120,5],"x":[2,8,3],"m":[152.07,1.2541,2.543,14,11.36,143.3,153.7]},{"t":-0.4,"p":[0.5,2.5,2,0.8,120,5],"x":[2,6,3],"m":[150.11,2.4496,3.741,11.97,9.23,143.3,151.7]},{"t":-0.5,"p":[0.5,2,2,0.8,120,5],"x":[2,5,3],"m":[148.53,3.0381,4.329,10.99,8.31,143.3,150.5]},{"t":-0.6,"p":[0.5,2,2,0.8,120,5],"x":[2,4,3],"m":[145.15,3.6652,4.969,9.95,7.31,143.3,149.8]},{"t":-0.7,"p":[0.5,1,2,0.8,120,5],"x":[2,3,3],"m":[138.81,4.5741,5.905,9,6.35,143.3,148.7]}];
const advScn=q.get('adv')||'advice',wanScn=q.get('wan')||'',keyScn=q.get('key')||'';
const ADV={mode:advScn==='auto'?'auto':advScn==='custom'?'manual':'advice',window:7,t:advScn==='turbo'?-0.5:0.5,custom:advScn==='custom',fast:advScn==='fast'||advScn==='turbo',turbo:advScn==='turbo'};
window.HV_FIXTURE=function(f){
 const {status,inventory,settings,profiles}=f;
 const rev='0123456789abcdef0123456789abcdef';
 const A={id:'wireguard:peer_2002',section:'peer_2002',protocol:'wireguard',name:'WG · Amsterdam',router_name:'nl-ams-2002.example',interface:'wgclient1',vendor_tunnel_id:'wireguard:wgclient1',administrative_state:'enabled'};
 const B={id:'openvpn:1_2020',section:'1_2020',protocol:'openvpn',name:'OpenVPN · Frankfurt',router_name:'de-fra-2020.example',interface:'ovpnclient1',vendor_tunnel_id:'openvpn:ovpnclient1',administrative_state:'enabled'};
 const C={id:'wireguard:peer_3001',section:'peer_3001',protocol:'wireguard',name:'WG · Warsaw',router_name:'pl-waw-3001.example',interface:null,vendor_tunnel_id:null,administrative_state:'disabled'};
 profiles.length=0;profiles.push(Object.assign({},A),Object.assign({},B));
 inventory.profiles=[A,B,C];inventory.servers=[A,B,C].map((p,i)=>({profile:p.id,name:p.name,channel:'default',priority:(i+1)*10,enabled:true}));
 Object.assign(settings,{terms_version:scn==='first'?'':'2',onboarding_complete:scn!=='first',onboarding_version:scn==='first'?0:1,plan_source:scn==='first'?'':A.id,plan_target:scn==='first'?'':B.id,plan_enabled:false,
  pair_auto_mode:'router-probed-ipv4',detected_router_model:'mt6000',router_model:'auto',native_session_loss:true,enabled:true,interval:20,checkpoint:900,probe_limit:16,live_log_limit:2000,history_days:7,
  server_key_pin:'warn',recovery_flap_model:'double',recovery_flap_limit:2,recovery_flap_window:60,recovery_flap_halflife:1800,recovery_flap_suppress:1500,recovery_flap_reuse:500,retry_backoff:'fibonacci',probe_spread:true,reserve_probe_interval:0,parallel_recheck:false,auto_event_wake:true,wan_sensor:true,wan_recover_grace:30,wg_events:true,stall_sensor:true,stall_veto:true,heartbeat_quorum:false,probe_target_log:true,
  recovery_failures:3,recovery_successes:2,recovery_cooldown:60,recovery_min_dwell:60,recovery_return_policy:'healthy_primary',recovery_primary_successes:2,recovery_primary_stable:30,recovery_attempt_limit:3,recovery_attempt_window:15,recovery_rescue_stable:10,failure_model:'hmm',server_pick_model:'simple',
  response_metric:'icmp-1.1.1.1',ping_interval:60,fast_switch:true,server_pick:true,probe_level:3,probe_boost:true,speed_enabled:false,speed_budget_mib:8,speed_duration:5,speed_streams:2,speed_daily_mib:128,speed_busy_mbps:2,
  telegram_configured:false,telegram_enabled:false,telegram_destination:'',telegram_schedule:'interval',telegram_interval:60,telegram_hour:7,telegram_weekly:true,telegram_monthly:true,telegram_items:'',sqm_enabled:false,sqm_upload_kbit:0,stats_mode:'work'});
 if(q.get('incomplete')==='1'){settings.onboarding_complete=false;settings.onboarding_version=0;}
 if(q.get('xd')==='changed')Object.assign(settings,{recovery_flap_model:'halflife',recovery_flap_limit:3,retry_backoff:'fixed',reserve_probe_interval:60,heartbeat_quorum:true,server_key_pin:'enforce',wan_sensor:false});
 delete status.failover_plan;
 function tick(){
  const now=Date.now()/1000,cmd=window.HV_FIXTURE_CMD,starting=cmd&&cmd.on&&now-cmd.at<4,off=cmd?!cmd.on||starting:(scn==='off'||scn==='first'||scn==='down'),stale=scn==='stale',age=stale?400:0,t=now-age;
  const onReserve=scn==='reserve';
  status.version='2.1.0-alpha10';status.package='2.1.0-alpha10-1';status.server_time=now;status.time=t;status.response_metric='icmp-1.1.1.1';
  profiles[0]=Object.assign(profiles[0],{time:t-3,code:onReserve||scn==='down'?'VPN-003':null,dns_ok:!(onReserve||scn==='down'),https_success:onReserve||scn==='down'?0:3,vendor_state:'SETTLED',
   ping:{metric:'icmp-rtt-ms',target:'1.1.1.1',interface:'wgclient1',state:onReserve||scn==='down'?'fail':'ok',rtt_ms:38.2,time:t-3,valid_for:120},ping_last:{rtt_ms:38.2,time:t-3},
   server_endpoint:{source:'live-kernel-peer',profile:A.id,interface:'wgclient1',time:t-3,host:'185.107.56.20',port:51820,transport:'udp'}});
  profiles[1]=Object.assign(profiles[1],{time:t-5,code:null,dns_ok:true,https_success:3,vendor_state:'SETTLED',
   ping:{metric:'icmp-rtt-ms',target:'1.1.1.1',interface:'ovpnclient1',state:'ok',rtt_ms:54.6,time:t-5,valid_for:120},ping_last:{rtt_ms:54.6,time:t-5},
   server_endpoint:{source:'live-kernel-peer',profile:B.id,interface:'ovpnclient1',time:t-5,host:'193.176.84.10',port:1194,transport:'udp'}});
  status.native_failover={state:off?'STOPPED':onReserve?'COMMITTED':'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,certified:true,source:A.id,target:B.id,time:t,original_restored:off?true:undefined,blockers:[]};
  status.auto_control={requested:cmd?(cmd.on?'on':'off'):off?'off':'on',requested_at:cmd?cmd.at:1700000000,control_revision:rev,pair_phase:starting?'STARTING':off?'STOPPED':'RUNNING',request_source:'manual'};
  status.channel_path={mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,time:t-1,checked_at:t-1,source_profile_id:A.id,target_profile_id:B.id,active_profile_id:onReserve?B.id:A.id,confirmed:true,kernel_policy_verified:true,transitioning:false};
  status.manual_switch_control={mode:'continuous-pair',available:!off&&!stale,time:t,control_revision:rev,primary:{allowed:!off,blockers:[]},reserve:{allowed:!off,blockers:[]},resume:{allowed:false}};
  status.probe_policy={level:3,boost_enabled:true,boost_active:false,effective_interval:20,ping_interval:60};
  status.switch_timing={avg_seconds:3.9,count:9,last_seconds:4.4};
  status.system_readiness={time:t,board:{model:'GL.iNet GL-MT6000',board_name:'glinet,gl-mt6000',firmware:'4.8.1'},checks:['PYTHON-39-MINIMUM','DEPENDENCY-UBUS','DEPENDENCY-UCI','DEPENDENCY-LUA','DEPENDENCY-IP','RPC-PLUGIN','CA-BUNDLE','CONFIG-STORAGE-FREE'].map(code=>({code,state:'pass'}))};
  status.stats_mode={mode:'work',storage:{'ram:history':1887436,'flash:history':629145},capacity:{flash_free:8388608,ram_available:52428800}};
  const ev=(dt,state,extra)=>Object.assign({sequence:Math.round(now-dt),time:now-dt,state,source:A.id,target:B.id,codes:[],trial:false},extra||{});
  status.native_history={available:true,timezone:'Europe/Berlin',detail_days:7,events:[
   ev(90000,'APPLYING',{codes:['SOURCE-FAILED'],transition_source:'automatic'}),ev(89996,'COMMITTED',{codes:['SOURCE-FAILED'],transition_source:'automatic'}),
   ev(89400,'RESTORING',{codes:['PRIMARY-STABLY-RECOVERED'],transition_source:'automatic'}),ev(89395,'ROLLED-BACK',{codes:['PRIMARY-STABLY-RECOVERED'],original_restored:true,return_primary:true,transition_source:'automatic'}),
   ev(1300,'APPLYING',{codes:['SOURCE-FAILED'],transition_source:'automatic'}),ev(1296,'COMMITTED',{codes:['SOURCE-FAILED'],transition_source:'automatic'}),
   ...(onReserve?[]:[ev(700,'RESTORING',{codes:['PRIMARY-STABLY-RECOVERED'],transition_source:'automatic'}),ev(695,'ROLLED-BACK',{codes:['PRIMARY-STABLY-RECOVERED'],original_restored:true,return_primary:true,transition_source:'automatic'})])],months:{}};
  status.accounting=Object.assign(status.accounting||{},{reliability:{detail_days:7,events:[{time:now-90020,kind:'FAILURE',profile:A.id,role:'source',code:'WEBSITE-TIMEOUT'},{time:now-89500,kind:'RECOVERY',profile:A.id,role:'source'},{time:now-1320,kind:'FAILURE',profile:A.id,role:'source',code:'VPN-003'}].concat(onReserve?[]:[{time:now-760,kind:'RECOVERY',profile:A.id,role:'source'}]),
   route_history:{segments:[{kind:'source',start:now-86400,end:now-1300},{kind:'switching',start:now-1300,end:now-1296},{kind:'target',start:now-1296,end:onReserve?now:now-700}].concat(onReserve?[]:[{kind:'source',start:now-695,end:now}])}}});
  const rows=[];for(let k=72;k>=0;k--){const ts=now-k*300;const down=k>=4&&k<=5;rows.push([Math.round(ts),down?null:Math.round((38+Math.sin(k)*6)*10),Math.round((54+Math.cos(k)*7)*10),down?0:1,1,down?'down':'source']);}
  status.website_response_history={version:1,metric:'icmp-rtt-ms',target:'1.1.1.1',row_encoding:'sum-tenths',pair:[A.id,B.id],rows:rows};
  status.server_pick={time:t,enabled:true,tunnels:[{protocol:'wireguard',interface:'wgclient1',current:'p1',best:'p1',candidates:[{profile:'p1',location:'nl-ams-2002',latency_ms:38,alive:true},{profile:'p2',location:'nl-ams-2004',latency_ms:44,alive:true},{profile:'p3',location:'nl-ams-2001',latency_ms:61,alive:true},{profile:'p4',location:'nl-ams-2007',latency_ms:null,alive:false}],last_change:{time:now-20000,from_location:'nl-ams-2001',to_location:'nl-ams-2002',from_ms:61,to_ms:38}},
   {protocol:'openvpn',interface:'ovpnclient1',current:'q2',best:'q1',candidates:[{profile:'q1',location:'de-fra-2016',latency_ms:49,alive:true},{profile:'q2',location:'de-fra-2020',latency_ms:54,alive:true},{profile:'q3',location:'de-fra-2011',latency_ms:72,alive:true}]}]};
  status.speed_tests={results:[{id:A.id,time:now-7200,download:{mbps:212},upload:{mbps:48}}]};
  status.operator_fault={state:'IDLE',history:[{time:now-172800,code:'FAULT-CANCELLED',profiles:[A.id],scope:'channel'}]};
  status.events=[];status.samples=[];
  if(window.HV_FIXTURE_ADVISOR_OFF)return;  // node tests drive these fields and answers themselves
  const curT=ADV.custom?null:ADV.t,few=advScn==='few';
  status.network_advisor=advScn==='none'?undefined:{mode:ADV.mode,window_days:ADV.window,curve_version:1,
   current:{t_ref:ADV.custom?0.6:curT,slider_t:curT,attached:!ADV.custom&&advScn!=='consecutive',label:advScn==='consecutive'?'preset':ADV.custom?'custom':'slider',nearest_t:ADV.custom?0.6:curT,
    failure_model:advScn==='consecutive'?'consecutive':'hmm',theta:ADV.custom?0.62:0.6,dur_b:ADV.custom?6:5,pg:0.95,primary_stable:120,rescue_stable:10,fast:ADV.fast,turbo:ADV.turbo},
   recommendation:few?{state:'few-data',events:2,days_used:3,counts:{natural:2,loss_episodes:0,flaps:0,reserve_failures:0},reason_ru:'Мало данных: 2 события за 3 дня (нужно не меньше 5). Настройки не меняются.',reason_en:'Not enough data: 2 events in 3 days (at least 5 needed). Settings stay as they are.',window_days:ADV.window,generated:now-3600}:
    {state:ADV.t>=0.7?'keep':'shift',t:0.7,best_t:0.7,method:'golden',events:16,days_used:7,window_days:ADV.window,generated:now-3600,counts:{natural:14,loss_episodes:1,flaps:1,reserve_failures:0},
     effect:{saving_pct:7.5,downtime_s_day:-1.5,unnecessary_per_day:0.1},
     reason_ru:ADV.t>=0.7?'Оставить положение '+String(ADV.t).replace('.',',')+': на основании 7 дней: обрывов основного 14 (медиана 9 с), эпизодов потерь 1, дребезга 1, отказов резерва 0.':'Рекомендовано на основании 7 дней: обрывов основного 14 (медиана 9 с), эпизодов потерь 1, дребезга 1, отказов резерва 0. Предлагается положение 0,70 (сейчас: положение 0,50). Ожидаемо за сутки: простой −1,5 с, лишних переключений −0,10, экономия 7,5 %.',
     reason_en:ADV.t>=0.7?'Keep position '+ADV.t+': based on 7 days: 14 outages of the primary (median 9 s), 1 loss episodes, 1 flaps, 0 reserve failures.':'Recommended based on 7 days: 14 outages of the primary (median 9 s), 1 loss episodes, 1 flaps, 0 reserve failures. Suggested position 0.70 (now: position 0.50). Expected per day: downtime -1.5 s, unnecessary switches -0.10, saving 7.5 %.'},
   journal:{days:7,window_days:ADV.window,tunnels:{},pair:{switches:2,returns:2,unnecessary:1}},
   last_change:{time:now-86400*2,source:'auto',from:0.4,to:0.5,params:{},reason_ru:'Рекомендовано на основании 7 дней: много коротких обрывов — сдвиг к «Без лишних переключений».',reason_en:'Recommended based on 7 days: many short outages — moved toward "No unnecessary switches".'}};
  status.wan_diagnosis={time:now,enabled:true,verdict:wanScn==='down'?'WAN':'N',confidence:wanScn?930:880,code:wanScn==='down'?'WAN-DOWN':wanScn==='recovering'?'WAN-RECOVERING':null,hold:!!wanScn,recovering:wanScn==='recovering',down_since:wanScn==='down'?now-42:null,up_at:wanScn==='recovering'?now-8:null};
  status.server_keys=keyScn==='off'?{mode:'off'}:{mode:'warn',pinned:keyScn==='changed'?1:2,code:keyScn==='changed'?'SERVER-KEY-CHANGED':null,
   changed:keyScn==='changed'?[{profile:A.id,host:'nl-ams-2002.example',pinned:'wg:q3Yp1E6rM2u1Lr0m8X4h6c8w2T5fW1kJ9Zx0bVnAs0E=',observed:'wg:Bz7Q0mYk4sV8pT2xR6wN1cL5dH9fJ3gA0eU7iO4yK2w=',changed_at:now-600}]:[]};
 }
 tick();
 const declare=window.rpc.declare;
 window.rpc.declare=function(spec){const f=declare(spec);return function(){if(spec.method==='status')tick();
  if(['native_start','native_stop','setup_onboarding','terms_accept','scan'].indexOf(spec.method)>=0)window.fixtureCalls.push({method:spec.method,args:Array.from(arguments)});
  if(spec.method==='native_start')window.HV_FIXTURE_CMD={on:true,at:Date.now()/1000};if(spec.method==='native_stop')window.HV_FIXTURE_CMD={on:false,at:Date.now()/1000};
  if(spec.method==='native_start')return Promise.resolve({accepted:true,queued:true});
  if(spec.method==='setup_onboarding'){settings.onboarding_complete=true;settings.onboarding_version=1;return Promise.resolve({saved:true,onboarding_complete:true,onboarding_version:1});}
  if(spec.method==='terms_accept'){settings.terms_version='2';return Promise.resolve({saved:true});}
  if(spec.method==='native_stop')return Promise.resolve({queued:true});
  if(!window.HV_FIXTURE_ADVISOR_OFF&&spec.method==='advisor')return Promise.resolve({curve:ADV_CURVE});
  if(!window.HV_FIXTURE_ADVISOR_OFF&&(spec.method==='setup_detector'||spec.method==='setup_recovery')){const a=arguments;spec.params.forEach((k,i)=>{if(spec.method==='setup_detector')settings[k]=a[i];else if(/^flap_/.test(k))settings['recovery_'+k]=a[i];});return Promise.resolve({saved:true,mode:'monitor'});}
  if(!window.HV_FIXTURE_ADVISOR_OFF&&spec.method==='advisor_settings'){const a=arguments,P=spec.params;ADV.mode=a[0];ADV.window=a[1];if(P.indexOf('theta')>=0){ADV.custom=true;}if(P.indexOf('fast')>=0){ADV.fast=a[P.indexOf('fast')];if(!ADV.fast){ADV.turbo=false;if(ADV.t<0)ADV.t=0;}}if(P.indexOf('turbo')>=0){ADV.turbo=a[P.indexOf('turbo')];if(ADV.turbo)ADV.fast=true;else if(ADV.t<-0.2)ADV.t=-0.2;}tick();return Promise.resolve({saved:true,mode:a[0],window:a[1]});}
  if(!window.HV_FIXTURE_ADVISOR_OFF&&spec.method==='advisor_apply'){ADV.t=arguments.length?Math.round(arguments[0]*100)/100:0.7;ADV.custom=false;tick();return Promise.resolve({saved:true,t:ADV.t});}
  if(!window.HV_FIXTURE_ADVISOR_OFF&&spec.method==='server_key_accept')return Promise.resolve({queued:true,code:null});
  if(spec.method==='scan'){const id='a'.repeat(32),now=Date.now()/1000;status.scan={request_id:id,requested_at:now,state:'COMPLETED',measurement_request_id:id,measured_at:now+0.5,finished_at:now+1,checked:2,failed:0};return Promise.resolve({queued:true,request_id:id,requested_at:now});}
  return f.apply(null,arguments);};};
};
})();
