const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(v=>v!=null);}appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=v;}addEventListener(){}}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const text=n=>n instanceof Node?n.children.map(text).join(' '):String(n);
const clone=v=>JSON.parse(JSON.stringify(v));
function freeze(v){if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;}
const clock=1005,generation='a'.repeat(32),otherGeneration='b'.repeat(32);
function sandbox(language='en'){
  const c={locale:language,E:(...args)=>new Node(...args),bi:(en,ru)=>language==='ru'?ru:en,Date:class extends Date{static now(){return clock*1000;}},localStorage:{getItem:()=>null},ownGet:(o,k)=>Object.hasOwn(o,k)?o[k]:undefined,errorCodeLink:code=>new Node('span',{},code)};
  vm.createContext(c);for(const name of ['ui_logic','vendor_diagnostics','analytics_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);return c;
}
function fixture(){
  const row=(id,protocol,tunnel,epoch)=>({id,protocol,interface:tunnel.split(':')[1],vendor_tunnel_id:tunnel,vendor_generation:epoch,vendor_state:'SETTLED',vendor_changed_at:970,time:1000,code:null,dns_ok:true,https_success:2,channel:'Same editable label',router_name:'DO-NOT-DISPLAY-provider.example',exit_ip:'DO-NOT-DISPLAY-exit',endpoint:'DO-NOT-DISPLAY-endpoint'});
  const group=(id,protocol,current,epoch,profileGroup)=>({id,protocol,profile_group_id:profileGroup,profiles:[current],active_profiles:[current],current_profile:current,previous_profile:null,state:'SETTLED',generation:epoch,stable_samples:2,time:1000,changed_at:970,vendor_attempts_exhausted:null});
  const source='openvpn:ovpnclient1',target='wireguard:wgclient1';
  const status={time:1000,profiles:[row('openvpn:a','openvpn',source,generation),row('wireguard:b','wireguard',target,otherGeneration)],vendor_observation:{version:1,time:1000,groups:[group(source,'openvpn','openvpn:a',generation,'openvpn:12'),group(target,'wireguard','wireguard:b',otherGeneration,'wireguard:7')],events:[{time:990,tunnel:source,previous_profile:'openvpn:old',current_profile:'openvpn:a',code:'VENDOR-PROFILE-CHANGED',cause:'UNOBSERVED'}]},failover_plan:{mode:'dry-run',applied:false,coordination:{version:1,time:1000,state:'READY',code:'CROSS-TUNNEL-READY',source_tunnel:source,target_tunnel:target,transition:'protocol',can_apply:false,vendor_attempts_exhausted:null,vendor_reason:'UNOBSERVED'}},native_failover:{state:'OBSERVING',time:1000},decision_explanation:{required_failures:3,required_successes:2,source_failure_streak_met:true,reserve_success_streak_met:true,diagnosis:{code:'VPN-PROBE-HEALTHY'}}};
  const inventory={settings:{interval:30,plan_source:'openvpn:old',plan_target:'wireguard:old',plan_source_tunnel:source,plan_target_tunnel:target,recovery_return_policy:'healthy_primary'},servers:[{profile:'openvpn:a',name:'Owner primary',channel:'Same editable label'},{profile:'wireguard:b',name:'Owner reserve',channel:'Same editable label'}]};
  return {status,inventory};
}
const c=sandbox(),model=(s,i)=>c.vendorDiagnosticsModel(s,i,clock);
let {status,inventory}=fixture(),m=model(freeze(status),freeze(inventory));
assert.equal(m.groups.length,2);assert.equal(m.groups[0].health,'healthy');assert.equal(m.groups[0].state,'stable');assert(m.coordination.known);assert.equal(m.coordination.transition,'protocol');
assert.equal(m.source,'openvpn:ovpnclient1');assert.equal(m.groups[0].current,'openvpn:a','shows the resolved current member, not saved stale chosen profile');
for(const renderer of ['renderVendorEvents']){
  const node=c[renderer](status,inventory),body=text(node);assert(walk(node).some(n=>n.attrs['data-vendor-diagnostics']));
  assert(!body.includes('DO-NOT-DISPLAY'));assert(!walk(node).some(n=>n.tag==='button'),'observations have no mutating actions');
}
let body=text(c.renderVendorChannels(status,inventory));assert.equal(body,'','the owner removed the complete VPN names disclosure');assert(!walk(c.renderVendorChannels(status,inventory)).some(n=>n.tag==='details'||n.attrs['data-vendor-diagnostics']),'no hidden replacement disclosure remains');
// Same provider profile group and equal editable labels do not merge distinct configured tunnels.
({status,inventory}=fixture());const extra=clone(status.vendor_observation.groups[0]);Object.assign(extra,{id:'openvpn:ovpnclient2',profiles:['openvpn:c'],active_profiles:['openvpn:c'],current_profile:'openvpn:c'});status.vendor_observation.groups.push(extra);const third=clone(status.profiles[0]);Object.assign(third,{id:'openvpn:c',vendor_tunnel_id:extra.id});status.profiles.push(third);m=model(status,inventory);assert.equal(m.groups.length,3);assert.equal(m.groups[2].profileGroup,'openvpn:12');
// A profile or kernel generation change invalidates old health. Two stable identity scans never prove exhausted retries.
for(const mutate of [
  s=>s.profiles[0].vendor_generation='c'.repeat(32),s=>s.profiles[0].vendor_tunnel_id='openvpn:elsewhere',s=>s.profiles[0].time=800,s=>s.profiles[0].time=1010,s=>s.profiles[0].protocol='wifi',s=>s.profiles[0].https_success='2',s=>s.profiles[0].https_success=2.5,s=>s.profiles[0].dns_ok=1,s=>s.profiles[0].interface='different-logical-interface',s=>s.profiles[0].vendor_state='PENDING',s=>s.profiles[0].vendor_changed_at=969,s=>s.vendor_observation.groups[0].changed_at=1010,
  s=>{s.profiles.push(clone(s.profiles[0]));},s=>{s.vendor_observation.groups[0].current_profile='openvpn:new';s.vendor_observation.groups[0].profiles.push('openvpn:new');s.vendor_observation.groups[0].active_profiles=['openvpn:new'];},
  s=>{s.vendor_observation.groups[0].state='PENDING';s.vendor_observation.groups[0].stable_samples=1;},s=>s.vendor_observation.groups[0].generation=null,s=>s.vendor_observation.groups[0].stable_samples=1,s=>s.vendor_observation.groups[0].active_profiles.push('openvpn:ambiguous'),
  s=>s.vendor_observation.groups[0].time=800,s=>s.vendor_observation.time=800,s=>s.time=800,s=>s.rpc_error='RPC-UNAVAILABLE',s=>s.error='SERVICE-STOPPED'
]){({status,inventory}=fixture());mutate(status);assert.equal(model(status,inventory).groups[0].health,'unknown');assert.equal(model(status,inventory).coordination.known,false,'no ready candidate without current coherent evidence');}
({status,inventory}=fixture());status.vendor_observation.groups.push(clone(status.vendor_observation.groups[0]));assert.equal(model(status,inventory).groups[0].health,'unknown','duplicate tunnel identity is ambiguous');
({status,inventory}=fixture());inventory.servers[0].enabled=false;assert.equal(model(status,inventory).groups[0].health,'unknown','explicitly disabled metadata cannot preserve stale positive readiness');
({status,inventory}=fixture());status.vendor_observation.groups[0].profiles=Array.from({length:9},(_,i)=>'openvpn:'+i).concat('openvpn:a');assert.equal(model(status,inventory).groups[0].health,'unknown','observed member history is bounded to the public eight-entry contract');
({status,inventory}=fixture());status.profiles[0].code='DNS-001';assert.equal(model(status,inventory).groups[0].health,'failed');assert(model(status,inventory).coordination.known,'source failure can still yield a read-only candidate');
// Freshness follows the configured interval without accepting future, nonfinite or string timestamps.
({status,inventory}=fixture());for(const group of status.vendor_observation.groups){group.time=400;group.changed_at=300;}for(const row of status.profiles){row.time=400;row.vendor_changed_at=300;}status.time=400;status.vendor_observation.time=400;status.failover_plan.coordination.time=400;inventory.settings.interval=300;assert.equal(model(status,inventory).groups[0].health,'healthy');
for(const value of [Infinity,NaN,'1000',true,-1,1010]){({status,inventory}=fixture());status.time=value;assert.equal(model(status,inventory).groups[0].health,'unknown');}
for(const malformed of [null,{},[],{version:'1',time:1000,groups:[]},{version:2,time:1000,groups:[]},{version:1,time:1000,groups:{}}]){({status,inventory}=fixture());status.vendor_observation=malformed;assert.equal(model(status,inventory).available,false);assert.doesNotThrow(()=>c.renderVendorChannels(status,inventory));}
// Recognized fresh application codes are known planner reasons, never evidence of vendor cause or route authorization.
for(const code of ['VENDOR-SAME-TUNNEL','VENDOR-SETTLING','VENDOR-IDENTITY-UNKNOWN','OBSERVATION-STALE','PROFILE-IDENTITY-CHANGED','UPLINK-LINK-DOWN','PLAN-CONFIG']){
  ({status,inventory}=fixture());Object.assign(status.failover_plan.coordination,{state:'HOLD',code,settle_until:1030});m=model(status,inventory);assert(m.coordination.known,code);assert(!text(c.renderVendorChannels(status,inventory)).includes('DO-NOT-DISPLAY'));assert(c.vendorCoordinationText(m).length>0,'recognized coordination still has a source explanation');
}
for(const patch of [{version:2},{time:800},{code:'__proto__'},{code:'SECRET-UNREVIEWED'},{can_apply:true},{vendor_attempts_exhausted:true},{vendor_reason:'KNOWN'},{transition:'channel'},{source_tunnel:'wireguard:wgclient1'},{state:'HOLD'}]){({status,inventory}=fixture());Object.assign(status.failover_plan.coordination,patch);assert.equal(model(status,inventory).coordination.known,false,JSON.stringify(patch));}
// Retained events are bounded and identify observations only. Raw reason/endpoint/secret fields are never rendered.
({status,inventory}=fixture());status.vendor_observation.events=Array.from({length:80},(_,i)=>({time:900+i,tunnel:'openvpn:ovpnclient1',previous_profile:'openvpn:a',current_profile:'openvpn:a',code:'VENDOR-BINDING-CHANGED',cause:'UNOBSERVED',reason:'DO-NOT-DISPLAY-secret'}));m=model(status,inventory);assert.equal(m.events.length,8);assert.equal(m.events[0].time,979);body=text(c.renderVendorEvents(status,inventory));assert(!body.includes('DO-NOT-DISPLAY'));assert(body.includes('not proof of automatic failover'));
for(const event of [{time:1000,tunnel:'openvpn:ovpnclient1',code:'SECRET-UNREVIEWED',cause:'UNOBSERVED'},{time:1000,tunnel:'openvpn:ovpnclient1',code:'VENDOR-PROFILE-CHANGED',previous_profile:'same',current_profile:'same',cause:'UNOBSERVED'},{time:1000,tunnel:'https://secret.example',code:'VENDOR-BINDING-UNKNOWN',cause:'UNOBSERVED'},{time:1000,tunnel:'openvpn:ovpnclient1',code:'VENDOR-BINDING-UNKNOWN',cause:'KNOWN'}]){({status,inventory}=fixture());status.vendor_observation.events=[event];assert.equal(model(status,inventory).events.length,0);}
// Existing decision explanation must not contradict Stop/hold policy or promise switching from probe quorum.
for(const language of ['en','ru']){
  const ctx=sandbox(language);
  for(const state of ['STOPPED-ON-RESERVE','HELD-ON-RESERVE']){({status,inventory}=fixture());status.native_failover.state=state;body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'отдельное действие':'explicit'));assert(!/Auto will switch(?! or wait)/.test(body));assert(!body.includes('Auto вернётся'));status.native_failover.time=800;body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'текущее состояние контроллера неизвестно':'current controller state is unknown'));}
  ({status,inventory}=fixture());status.native_failover.state='COMMITTED';inventory.settings.recovery_return_policy='hold_reserve';body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'до решения оператора':'operator review'));assert(!body.includes('when it has recovered'));
  inventory.settings.recovery_return_policy='healthy_primary';body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'возврат не обещан':'return is not promised'));
  status.native_failover.time=800;body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'данные контроллера устарели':'controller data is stale'));
  ({status,inventory}=fixture());body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'не разрешают изменение маршрута':'do not authorize a route change'));assert(!/Auto will switch(?! or wait)/.test(body));assert(!body.includes('Auto переключится'));
  status.time=800;body=text(ctx.renderDecisionExplanation(status,inventory));assert(body.includes(language==='ru'?'устаревшим данным':'stale data'));assert(!body.includes('Ready: if the primary fails'));
  ({status,inventory}=fixture());for(const renderer of ['renderVendorChannels','renderVendorEvents'])assert.doesNotThrow(()=>ctx[renderer](status,inventory));
}
// A vendor member change keeps the saved tunnel anchor, updates every live display, and never revives the old member.
const live=sandbox();Object.assign(live,{document:{createElementNS:(_,tag)=>new Node(tag)},chart:()=>new Node('svg',{},'Existing chart'),bytes:v=>String(v),UI_BUILD:'test',safeCode:code=>typeof code==='string'&&/^[A-Z][A-Z0-9-]+$/.test(code),L:{resource:p=>p},rpc:{declare:()=>()=>{throw Error('render dispatched an RPC');}},ui:{},setTimeout:()=>0});
for(const file of ['ui_logic','fool_guard','auto_panel','country_panel','servers_panel','channel_guidance','latency_panel','design_views'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),live);
({status,inventory}=fixture());Object.assign(inventory.settings,{setup_complete:true,native_session_loss:true});Object.assign(status.native_failover,{certified:true,source:'openvpn:old',target:'wireguard:old'});
status.profiles[0].name='New current server';status.profiles[1].name='Current reserve server';inventory.servers=[];
assert.equal(live.vendorDisplayMember(status,inventory,'source',clock).id,'openvpn:a');assert.equal(live.vendorDisplaySelected(status,inventory,clock),'openvpn:a');
assert.equal(live.vendorDisplayMember(status,inventory,'source',clock).name,'New current server','current member identity stays available to the remaining cards');
const readiness=live.autoReadiness(status,inventory,clock);assert(readiness.steps.find(step=>step.key==='profiles').done,'readiness follows current members through anchors');
const control=live.renderAutoControl(status,inventory);assert(!text(control).includes('Choose in Settings'),'Auto diagram resolves both current members');
for(const design of ['a','b','c']){
  const dm=live.dvModel(status,inventory,status.profiles,{rx:0,tx:0});assert.equal(dm.primary.id,'openvpn:a');assert.equal(dm.reserve.id,'wireguard:b');assert.equal(dm.selected,'openvpn:a');
  const node=live.renderDesignOverview(design,{status,inventory,rows:status.profiles,month:{rx:0,tx:0},controlCard:control});assert(!text(node).includes('openvpn:old'));
  if(design==='b'){assert(!walk(node).some(n=>n.attrs['data-profile']),'owner removed duplicate VPN list from Calm Overview');assert.equal(walk(node).filter(n=>n===control).length,1,'Calm retains the resolved actual control');}
  else assert(walk(node).some(n=>n.attrs['data-profile']==='openvpn:a'));
}
status.native_failover.state='COMMITTED';assert.equal(live.vendorDisplaySelected(status,inventory,clock),'wireguard:b');
status.vendor_observation.groups[0].generation='c'.repeat(32);assert.equal(live.vendorDisplayMember(status,inventory,'source',clock),null,'anchored unknown identity never falls back to stale saved profile');assert.equal(live.dvModel(status,inventory,status.profiles,{rx:0,tx:0}).primary,null);
inventory.settings.plan_source_tunnel='bad-anchor';assert.equal(live.vendorDisplayMember(status,inventory,'source',clock),null);
delete inventory.settings.plan_source_tunnel;inventory.settings.plan_source='openvpn:a';assert.equal(live.vendorDisplayMember(status,inventory,'source',clock).id,'openvpn:a','anchorless legacy display keeps its explicit profile selection');
// Selected anchors remain visible even behind many other tunnel groups.
({status,inventory}=fixture());status.vendor_observation.groups=Array.from({length:39},(_,i)=>({id:'openvpn:spare'+i,protocol:'openvpn',profiles:[],active_profiles:[],state:'UNKNOWN',time:1000})).concat(status.vendor_observation.groups);
assert.equal(c.vendorDisplayMember(status,inventory,'source',clock).id,'openvpn:a');assert.equal(c.vendorDisplayMember(status,inventory,'target',clock).id,'wireguard:b');assert.equal(text(c.renderVendorChannels(status,inventory)),'','many tunnel groups do not revive the removed disclosure');
const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');for(const anchor of ['vendor_diagnostics.inc.js',"put('channels',renderVendorChannels(status,inventory));","put('events',renderVendorEvents(status,inventory));"])assert(builder.includes(anchor),anchor);
assert(builder.includes('must_replace("put(\'tests\',renderDecisionExplanation(status));","")'));
console.log('PASS: immutable vendor-tunnel identity vs labels/provider groups, current-generation health/freshness/unknown, bounded observed-change events, known read-only coordination vs unobserved cause, EN/RU and truthful held-reserve/return-policy/quorum decision explanation');

assert(!builder.includes("put('overview',renderVendorOverview"));
assert(!fs.readFileSync('router/vendor_diagnostics.inc.js','utf8').includes('Два уровня восстановления VPN'));
