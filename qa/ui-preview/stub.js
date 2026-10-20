window.E=function(tag,attrs,children){if(Array.isArray(tag)){let f=document.createDocumentFragment();tag.forEach(n=>f.append(n));return f;}let n=document.createElement(tag);Object.entries(attrs||{}).forEach(([k,v])=>{if(v==null)return;if(typeof v==='function')n.addEventListener(k,v);else if(v===true)n.setAttribute(k,'');else if(v!==false)n.setAttribute(k,v);});function add(c){if(c==null)return;if(Array.isArray(c))c.forEach(add);else n.append(c instanceof Node?c:document.createTextNode(String(c)));}add(children);return n;};
const asset='/router/files/www/luci-static/resources/view/homensai-vpn/';
window.L={resource:x=>asset+x.replace('view/homensai-vpn/',''),url:()=>'/qa/ui-preview/index.html'};window.view={extend:x=>x};
window.poll={add:fn=>{window.fixturePoll=fn;}};
window.ui={showModal:(title,children)=>{ui.hideModal();document.body.appendChild(E('section',{id:'qa-modal',role:'dialog','aria-label':title},[E('h2',{},title),children]));},hideModal:()=>{document.getElementById('qa-modal')?.remove();},addNotification:(_,node)=>{document.querySelector('.qa-notice')?.remove();document.body.appendChild(E('aside',{class:'qa-notice',role:'status'},node));}};
const now=Date.now()/1000,day=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const profiles=[['a','de1459.nordvpn.com.udp_2.6','openvpn','Main',null],['b','ua68.nordvpn.com.tcp_2.6','openvpn','Main',null],['c','nl-ams-wg-12','wireguard','Backup','CHECK-001'],['d','Poland Warsaw','openvpn','Backup','DNS-001']].map(([id,name,protocol,channel,code])=>({id,name,router_name:name,protocol,channel,interface:'vpn'+id,time:now,code,dns_ok:!code,https_success:code?0:2,rtt_ms:20+id.charCodeAt(0),exit_ip:code?undefined:'203.0.113.'+id.charCodeAt(0)}));
const lampMode=new URLSearchParams(location.search).get('lamp');if(lampMode==='inactive')profiles[1].interface=null;if(lampMode==='stale')profiles[1].time=now-120;
if(new URLSearchParams(location.search).get('stress')==='400'){for(let i=profiles.length;i<400;i++)profiles.push({id:'stress'+i,name:('Long synthetic server '+i+' — ').repeat(12),channel:'Synthetic long channel '+i,protocol:i%2?'wireguard':'openvpn',interface:null,time:now,code:'INACTIVE'});}
const servers=profiles.map((p,i)=>({profile:p.id,name:p.name,channel:p.channel,priority:i+1,enabled:true}));
const settings={terms_version:(new URLSearchParams(location.search).get('terms')==='gate'?'':'1'),setup_complete:true,onboarding_complete:true,onboarding_version:1,native_session_loss_fixture:true,enabled:true,plan_source:'a',plan_target:'b',interval:30,checkpoint:900,probe_limit:16,native_duration:10,native_session_loss:false,telegram_configured:true,telegram_destination:'@example_channel',telegram_enabled:false,telegram_schedule:'daily',telegram_hour:7,telegram_interval:60,telegram_weekly:true,telegram_monthly:true};
const spare=Array.from({length:8},(_,i)=>({id:'spare'+i,name:'offline-'+i,protocol:'openvpn',interface:null}));const inventory={profiles:profiles.concat(spare),servers,settings};
const status={version:'0.8.0-alpha2',time:now,profiles,samples:Array.from({length:40},(_,i)=>({id:i%2?'a':'b',time:now-(40-i)*30,code:null,dns_ok:true,https_success:2,rtt_ms:(i%2?38+((i*7)%13):72+((i*11)%29))})),...(new URLSearchParams(location.search).get('readiness')==='ok'?{system_readiness:{time:now,board:{model:'GL.iNet GL-MT6000',board_name:'glinet,gl-mt6000',firmware:'4.11.0'},checks:[['PYTHON-39-MINIMUM','pass'],['DEPENDENCY-UBUS','pass'],['DEPENDENCY-UCI','pass'],['DEPENDENCY-LUA','pass'],['DEPENDENCY-IP','pass'],['RPC-PLUGIN','pass'],['CA-BUNDLE','fail'],['CONFIG-STORAGE-FREE','pass']].map(([code,state])=>({code,state}))}}:{}),native_failover:{state:'COMMITTED',source:'a',target:'b',time:now},auto_control:{requested:'on',requested_at:now-10,control_revision:'00000000000000000000000000000001'},failover_plan:{state:'SWITCH-RECOMMENDED',source:'a',target:'b',applied:false,blockers:['GL-ADAPTER-UNVERIFIED','WORKER-COORDINATION-UNVERIFIED','LAN-PATH-UNVERIFIED','DNS-POLICY-UNVERIFIED','KILLSWITCH-UNVERIFIED','IPV6-POLICY-UNVERIFIED','WATCHDOG-UNVERIFIED','SCOPED-CONNTRACK-UNVERIFIED'],recommendation:{target:'b'}},accounting:{months:{[day.slice(0,7)]:{rx:1e9,tx:2e9,seconds:3600}},days:Object.assign({[day]:{rx:1e9,tx:2e9,seconds:3600,observed:true}},Object.fromEntries(Array.from({length:12},(_,k)=>{const d=new Date(Date.now()-(k+1)*86400000).toISOString().slice(0,10);return [d,k===4?{rx:0,tx:0,seconds:0,observed:false}:{rx:(0.4+((k*37)%9)/10)*1e9,tx:(0.2+((k*53)%7)/12)*1e9,seconds:86400,observed:true}];}))),activity:Object.fromEntries(profiles.map(p=>[p.id,{name:p.name,protocol:p.protocol,days:{[day]:{up:2880,down:720,unknown:0,connections:2,failures:1}}}]))},events:[{time:now-60,code:'DNS-001',profile:'d'}],native_history:{available:true,timezone:'Europe/Berlin',events:[{sequence:1,time:now-30,state:'APPLYING',source:'a',target:'b',transition_kind:'server',codes:['OFFLINE-FIXTURE'],trial:false},{sequence:2,time:now-28,state:'WAIT-CLIENT',source:'a',target:'b',codes:[],trial:false},{sequence:3,time:now-25,state:'COMMITTED',source:'a',target:'b',codes:[],trial:false},{sequence:4,time:now-20,state:'APPLYING',source:'b',target:'d',transition_kind:'channel',codes:['OFFLINE-FIXTURE'],trial:false},{sequence:5,time:now-12,state:'ROLLED-BACK',source:'b',target:'d',codes:['DNS-001'],trial:false}],months:{}},speed_tests:{results:[{id:'a',time:now,download:{mbps:30},upload:{mbps:10}},{id:'b',time:now,download:{mbps:50},upload:{mbps:20}}]}};
if(new URLSearchParams(location.search).get('source')==='failed'){profiles[0].code='DNS-001';profiles[0].dns_ok=false;profiles[0].https_success=0;} const power=new URLSearchParams(location.search).get('power');if(power==='off'){status.native_failover.state='STOPPED';status.auto_control.requested='off';}if(power==='primary'){status.native_failover.state='OBSERVING';status.native_failover.certified=true;}if(power==='restoring')status.native_failover.state='RESTORING';if(power==='pending')status.native_failover.state='APPLYING';if(power==='error')status.native_failover.state='DEGRADED-ON-RESERVE';
// A dedicated loopback harness supplies a RAM-only synthetic backend across document/browser-storage resets.
const onboardingFixture=['first','defer'].includes(new URLSearchParams(location.search).get('onboarding'))||!!window.fixtureOnboardingBackend;
if(onboardingFixture){
 Object.assign(settings,{onboarding_complete:false,onboarding_version:0,telegram_configured:false,telegram_destination:'',telegram_enabled:false,plan_enabled:false});
 Object.assign(status.native_failover,{state:'STOPPED'});status.auto_control.requested='off';
 if(window.fixtureOnboardingSaved){Object.assign(settings,window.fixtureOnboardingSaved.settings);inventory.servers=window.fixtureOnboardingSaved.servers;}
 if(new URLSearchParams(location.search).get('profiles')==='none'){inventory.profiles=[];inventory.servers=[];settings.plan_source='';settings.plan_target='';}
}
function fixtureOnboardingSave(args){
 function commit(){
  if(!window.fixtureOnboardingBackend)return Promise.resolve({saved:false,code:'SYNTHETIC-BACKEND-UNAVAILABLE'});
  return fetch(window.fixtureOnboardingBackend,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(args)}).then(response=>{if(!response.ok)throw Error('SYNTHETIC-BACKEND-FAILED');return response.json();});
 }
 if(window.fixtureOnboardingSaveMode==='pending')return new Promise((resolve,reject)=>{window.fixturePending={resolve:()=>commit().then(resolve,reject),reject};});
 return commit();
}
window.fixtureCalls=[];window.rpc={declare:spec=>(...args)=>{window.fixtureCalls.push({method:spec.method,params:spec.params,args:spec.method==='setup_telegram'?['<masked>',...args.slice(1)]:spec.method==='setup_onboarding'?args.map((part,index)=>index===4?{...part,token:part.token?'<masked>':''}:part):args});if(spec.method==='setup_onboarding'&&onboardingFixture)return fixtureOnboardingSave(args);if(spec.method==='scan'){if(new URLSearchParams(location.search).get('check')==='fail')return Promise.reject(new Error('OFFLINE-SCAN-FAILURE'));const stamp=Date.now()/1000,id=Math.floor(stamp*1000).toString(16).padStart(32,'0');status.scan={request_id:id,requested_at:stamp,state:'QUEUED'};setTimeout(()=>{status.scan.state='RUNNING';window.fixturePoll?.();},300);setTimeout(()=>{status.scan={...status.scan,state:'COMPLETED',finished_at:Date.now()/1000,measured_at:Date.now()/1000,measurement_request_id:id,checked:3,failed:0};window.fixturePoll?.();},1500);return Promise.resolve({...status.scan,queued:true});}if(new URLSearchParams(location.search).get('rpc')==='fail'&&spec.method.startsWith('setup_')&&spec.method!=='setup_check')return Promise.reject(new Error('OFFLINE-RPC-FAILURE'));if(new URLSearchParams(location.search).get('rpc')==='pending'&&spec.method.startsWith('setup_')&&spec.method!=='setup_check')return new Promise((resolve,reject)=>{window.fixturePending={resolve,reject};});return Promise.resolve(spec.method==='inventory'?inventory:spec.method==='status'?status:spec.method==='setup_check'?{passed:true}:spec.method.startsWith('setup_')?{saved:true}:spec.method==='native_start'?{accepted:false,blockers:['OFFLINE-NO-NATIVE-ADAPTER']}:{queued:true,accepted:true});}};
// Explicit synthetic diagnostics scenes, never inferred from a real router.
const vendorScene=new URLSearchParams(location.search).get('vendor');
if(['stable','pending','changed','unknown','stale','wan','same-tunnel'].includes(vendorScene)){
 const stamp=Date.now()/1000,changed=stamp-120;
 settings.plan_source_tunnel='openvpn:vpna';settings.plan_target_tunnel='openvpn:vpnb';
 status.capabilities={native_apply:false,reason:'SYNTHETIC-NO-VENDOR-ADAPTER'};
 status.native_failover.state='DISABLED';status.auto_control.requested='off';
 if(vendorScene==='changed'){
  const replacement={...profiles[0],id:'a2',name:'Germany replacement',router_name:'Germany replacement',interface:'vpna'};
  profiles[0].interface=null;profiles[0].code='PROFILE-INACTIVE';profiles.push(replacement);inventory.profiles.push(replacement);
 }
 profiles.forEach((p,index)=>{
  p.vendor_tunnel_id=p.interface?p.protocol+':'+p.interface:null;
  p.vendor_profile_group_id=p.protocol==='openvpn'?'openvpn:10':'wireguard:20';
  p.vendor_generation=p.interface?'abcde'[index%5].repeat(32):null;
  p.vendor_changed_at=changed;p.vendor_state=p.interface?'SETTLED':'UNKNOWN';
  p.time=stamp;
 });
 const groups=profiles.filter(p=>p.interface).map(p=>({id:p.vendor_tunnel_id,protocol:p.protocol,profile_group_id:p.vendor_profile_group_id,
  profiles:[p.id],active_profiles:[p.id],current_profile:p.id,previous_profile:null,state:'SETTLED',generation:p.vendor_generation,
  changed_at:changed,stable_samples:4,time:stamp,vendor_attempts_exhausted:null}));
 const source=groups.find(g=>g.id==='openvpn:vpna'),sourceRow=profiles.find(p=>p.id===source.current_profile);
 const coordination={version:1,time:stamp,state:'READY',code:'CROSS-TUNNEL-READY',source_tunnel:settings.plan_source_tunnel,
  target_tunnel:settings.plan_target_tunnel,transition:'channel',vendor_reason:'UNOBSERVED',can_apply:false,vendor_attempts_exhausted:null};
 const observedEvents=[];
 if(vendorScene==='pending'||vendorScene==='changed'){
  source.state='PENDING';source.stable_samples=1;source.changed_at=stamp-5;
  sourceRow.vendor_state='PENDING';sourceRow.vendor_changed_at=stamp-5;
  Object.assign(coordination,{state:'HOLD',code:'VENDOR-SETTLING',settle_until:stamp+55});
 }
 if(vendorScene==='changed'){
  source.profiles=['a','a2'];source.previous_profile='a';
  observedEvents.push({time:stamp-5,tunnel:source.id,previous_profile:'a',current_profile:'a2',code:'VENDOR-PROFILE-CHANGED',cause:'UNOBSERVED'});
 }
 if(vendorScene==='unknown'){
  Object.assign(source,{state:'UNKNOWN',generation:null,active_profiles:[],current_profile:null,stable_samples:0});
  Object.assign(sourceRow,{vendor_state:'UNKNOWN',vendor_generation:null,code:'VENDOR-IDENTITY-UNKNOWN'});
  Object.assign(coordination,{state:'UNKNOWN',code:'VENDOR-IDENTITY-UNKNOWN'});
 }
 if(vendorScene==='wan'){
  sourceRow.code='VPN-003';sourceRow.https_success=0;
  status.uplink_observation={time:stamp,state:'DOWN'};
  Object.assign(coordination,{state:'HOLD',code:'UPLINK-LINK-DOWN'});
 }
 if(vendorScene==='same-tunnel'){
  settings.plan_target_tunnel=settings.plan_source_tunnel;
  Object.assign(coordination,{target_tunnel:settings.plan_source_tunnel,state:'HOLD',code:'VENDOR-SAME-TUNNEL',transition:null});
 }
 status.vendor_observation={version:1,time:stamp,groups,events:observedEvents,scope:'synthetic configured-identity observations only'};
 status.failover_plan={mode:'dry-run',state:coordination.code,coordination,source:sourceRow.id,target:'b',recommendation:null,applied:false,native_apply:false,ready_to_apply:false};
 status.decision_explanation={diagnosis:{code:vendorScene==='wan'?'UPLINK-LINK-DOWN':vendorScene==='changed'||vendorScene==='pending'?'VENDOR-SETTLING':'VPN-PROBE-HEALTHY'},
  source:sourceRow.id,target:'b',coordination,required_failures:3,required_successes:2,source_failure_streak_met:false,reserve_success_streak_met:true};
 status.samples=profiles.filter(p=>p.interface).flatMap(p=>[0,30,60].map(age=>({id:p.id,time:stamp-age,code:p.code,dns_ok:p.dns_ok,https_success:p.https_success,
  interface:p.interface,vendor_tunnel_id:p.vendor_tunnel_id,vendor_generation:p.vendor_generation})));
 if(vendorScene==='stale'){
  status.time=stamp-600;status.native_failover.time=stamp-600;status.vendor_observation.time=stamp-600;coordination.time=stamp-600;
  groups.forEach(g=>g.time=stamp-600);profiles.forEach(p=>p.time=stamp-600);
 }
}
fetch('/preview-module.js',{cache:'no-store'}).then(r=>r.text()).then(s=>new Function(s)()).then(v=>v.load().then(d=>v.render(d))).then(n=>document.getElementById('app').append(n)).catch(e=>document.getElementById('app').textContent='OFFLINE FIXTURE ERROR: '+e.message);
const refreshFixture=()=>{const stamp=Date.now()/1000;status.time=stamp;status.native_failover.time=stamp;profiles.forEach(p=>p.time=stamp);return window.fixturePoll?.();};
for(const [caption,handler] of [['Refresh fixture',refreshFixture],['Mark selected failed',()=>{profiles[1].code='DNS-001';profiles[1].dns_ok=false;profiles[1].https_success=0;return refreshFixture();}],['Recover selected',()=>{profiles[1].code=null;profiles[1].dns_ok=true;profiles[1].https_success=2;return refreshFixture();}],
['Scenario: normal',()=>{for(const p of [profiles[0],profiles[1]]){p.code=null;p.dns_ok=true;p.https_success=2;}Object.assign(status.native_failover,{state:'OBSERVING',certified:true,source:'a',target:'b'});return refreshFixture();}],
['Scenario: primary fails',()=>{const p=profiles[0];p.code='DNS-001';p.dns_ok=false;p.https_success=0;profiles[1].code=null;profiles[1].dns_ok=true;profiles[1].https_success=2;Object.assign(status.native_failover,{state:'COMMITTED',certified:true,source:'a',target:'b'});return refreshFixture();}],
['Scenario: primary recovered',()=>{const p=profiles[0];p.code=null;p.dns_ok=true;p.https_success=2;Object.assign(status.native_failover,{state:'OBSERVING',certified:true,source:'a',target:'b'});return refreshFixture();}]])document.getElementById('fixture-banner').appendChild(E('button',{type:'button',click:handler},caption));

if(new URLSearchParams(location.search).get('rpc')==='pending'){
 const controls=E('aside',{'class':'qa-pending-controls'},[
 E('strong',{},'SYNTHETIC RPC CONTROL '),
 E('button',{type:'button',click:()=>{if(window.fixturePending){window.fixturePending.reject(new Error('OFFLINE-PRIVATE-FAILURE'));window.fixturePending=null;}}},'Fail pending save'),
 E('button',{type:'button',click:()=>{if(window.fixturePending){window.fixturePending.resolve({saved:true});window.fixturePending=null;}}},'Complete pending save')]);document.body.appendChild(controls);
}
