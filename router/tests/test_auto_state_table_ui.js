// Owner contract: one state table drives every Auto lamp, text and confirmed switch.
// No router or RPC: real display functions and Simple/Console bindings in a synthetic DOM.
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children??[]).flat().filter(x=>x!=null);this.style={};this.classList={toggle:(key,on)=>{const names=new Set((this.attrs.class||'').split(/\s+/));on?names.add(key):names.delete(key);this.attrs.class=[...names].join(' ');}};}
 appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=String(v);}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
 text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join(' ');}
}
const inventory={settings:{plan_source:'a',plan_target:'b',setup_complete:true,enabled:true}};
function fixture(){return {time:1000,server_time:1000,profiles:['a','b'].map(id=>({id,interface:id==='a'?'wgclient1':'ovpnclient1',protocol:id==='a'?'wireguard':'openvpn',time:1000,dns_ok:true,https_success:2,code:null})),native_failover:{time:1000,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,kernel_policy_verified:true,source:'a',target:'b',blockers:[]},auto_control:{requested:'on',pair_phase:'RUNNING',requested_at:900},channel_path:{time:1000,checked_at:1000,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a',transitioning:false}};}
const expected={
 working:['green',true,true,['Auto works','Auto работает']],
 checking:['yellow',true,false,['Auto is on · waiting or checking','Auto включён · ожидание или проверка']],
 pending:['yellow',false,false,['Auto state is being confirmed','Состояние Auto подтверждается']],
 failure:['red',true,false,['Auto is on · needs attention','Auto включён · требует внимания']],
 refused:['red',false,false,['Auto needs attention','Auto требует внимания']],
 off:['off',false,false,['Auto is off','Auto выключен']]
};
let count=0,surfaces=0;
for(const language of ['en','ru']){
 let now=1000;
 const c={locale:language,bi:(en,ru)=>language==='en'?en:ru,Date,E:(...args)=>new N(...args),setTimeout:()=>0,setInterval:()=>0,clearInterval(){},identityModel:()=>({}),errorCodeLink:code=>new N('code',{},code),document:{querySelector:()=>null},window:{localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>null}},termsAccepted:()=>true};
 vm.createContext(c);
 for(const file of ['ui_logic','auto_panel','manual_panel','vendor_diagnostics','monitor_panel','simple_home_policy','simple_home_panel','sidebar_status'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
 for(const file of ['core','views'])vm.runInContext(fs.readFileSync('router/ui/'+file+'.js','utf8'),c);
 c.statusNow=()=>now;c.routerWall=()=>now;c.scanFollow=()=>{};c.eventRows=()=>[];
 function reset(){now=1000;c.UI_AUTO_LAST_ON=c.UI_RPC_LOST_SINCE=c.UI_DATA_LATE_SINCE=c.UI_TRANSIENT_SINCE=c.UI_PATH_MEMORY=null;c.autoCommandPending=c.autoCommandUnconfirmed=c.autoObservedOperation=null;}
 function contract(light){
  const row=c.autoPresentation(light),name=Object.keys(c.AUTO_SIGNAL_TABLE).find(k=>c.AUTO_SIGNAL_TABLE[k]===row);
  assert(name,'a named table row');const [lamp,enabled,working,words]=expected[name];
  assert.equal(c.autoSignal(light),lamp);assert.equal(c.autoEnabled(light),enabled);assert.equal(c.autoWorking(light),working);
  assert.equal(c.autoRuns(light),enabled&&lamp!=='red');assert.equal(c.autoStateText(light),words[language==='en'?0:1]);
  for(const paused of [false,true])assert.equal(c.autoLampColor(light,paused),lamp==='off'?'grey':lamp,'no surface overrides the table');count++;return name;
 }
 assert.deepEqual(Object.keys(c.AUTO_SIGNAL_TABLE).sort(),Object.keys(expected).sort());
 for(const [name,[lamp,enabled,working,words]] of Object.entries(expected)){
  const row=c.AUTO_SIGNAL_TABLE[name];assert.equal(row.lamp,lamp);assert.equal(row.enabled,enabled);assert.equal(row.working,working);assert.equal(JSON.stringify(row.text),JSON.stringify(words));
 }
 // Exhaust every input accepted by the display contract; legacy direct callers are included.
 for(const key of ['ok','reserve','unknown','switching','problem','off',undefined])for(const enabled of [true,false,undefined])for(const running of [true,false])for(const stale of [true,false])for(const hold of [true,false])contract({key,enabled,running,stale,hold});
 function inspect(status,row){
  const light=c.autoLightModel(status,inventory,now);assert.equal(contract(light),row);assert.equal(light.lamp,c.autoSignal(light)==='off'?null:c.autoSignal(light));
  if(status.native_failover.blockers.includes('NATIVE-SYSTEM-001'))assert.equal(light.code,'NATIVE-SYSTEM-001','busy diagnostics never hide a critical blocker');
  c.HV.st=status;c.HV.inv=inventory;c.V=c.snap();const ui=c.autoState();
  assert.equal(ui.lamp,{green:'g',yellow:'y',red:'r',off:'n'}[c.autoSignal(light)]);assert.equal(ui.text,c.autoStateText(light));
  const knob=new N('button');c.HV.root={querySelectorAll:selector=>selector==='[data-auto-switch]'?[knob]:[]};c.paintLive();
  assert.equal(knob.attrs['aria-checked'],String(c.autoEnabled(light)),'Simple and Console switch reflects confirmed session');
  if(!status.rpc_error&&!status.error&&status.channel_path.confirmed&&status.channel_path.active_profile_id==='a'&&status.native_failover.time===800)assert.equal(c.V.d.selectedRole,'source','fresh carrier proof survives a late Auto heartbeat');
  const power=c.renderAutoPowerControl(status,inventory).button;assert.equal(power.attrs['aria-pressed'],String(c.autoEnabled(light)));
  assert.equal(/hv-auto-lit-on/.test(power.attrs.class),c.autoEnabled(light));
  const side=new N('div');c.fillSideStatus(side,status,inventory);const nodes=side.all();
  assert(nodes.find(n=>/hv-auto-pill-knob/.test(n.attrs.class||'')).attrs.class.includes('hv-lamp-'+{green:'on',yellow:'switching',red:'off',off:'dark'}[c.autoSignal(light)]));
  assert.equal(nodes.find(n=>n.attrs.class==='hv-auto-pill-text').text(),c.autoStateText(light));
  const housing=c.renderAutoLight(light,'X').all().find(n=>n.attrs['data-signal']);assert.equal(housing.attrs['aria-label'],c.autoStateText(light));
  surfaces++;return light;
 }
 const cases=[
  ['primary works','working',()=>{}],
  ['boot recovery is not confirmed ON','pending',s=>{s.boot_resume={state:'WAITING',time:1000};s.auto_control={requested:'off',pair_phase:'STOPPED'};s.native_failover.state='STOPPED';}],
  ['unknown controller state waits','checking',s=>{s.native_failover.state='UNKNOWN-STATE';}],
  ['stopped session with transient code','off',s=>{s.auto_control.requested='off';s.auto_control.pair_phase='STOPPED';s.native_failover.state='STOPPED';s.native_failover.blockers=['OBSERVATION-STALE'];}],
  ['reserve works with failed primary','working',s=>{s.channel_path.active_profile_id='b';s.native_failover.state='COMMITTED';s.profiles[0].code='VPN-001';}],
  ['route proof pending','checking',s=>{s.channel_path.kernel_policy_verified=false;}],
  ['channel check pending','checking',s=>{delete s.profiles[0].time;}],
  ['selected channel failed','failure',s=>{s.profiles[0].code='VPN-003';s.profiles[0].https_success=0;}],
  ['controller failure still enabled','failure',s=>{s.native_failover.state='BLOCKED';s.native_failover.blockers=['ROLLBACK-GIVEN-UP'];}],
  ['selected channel failed during vendor wait','failure',s=>{s.profiles[0].code='VPN-003';s.profiles[0].https_success=0;s.native_failover.state='BLOCKED';s.native_failover.blockers=['VENDOR-WORKER-BUSY'];}],
  ['mixed wait and failure','failure',s=>{s.native_failover.state='BLOCKED';s.native_failover.blockers=['VENDOR-WORKER-BUSY','ROLLBACK-GIVEN-UP'];}],
  ['recovery check','checking',s=>{s.native_failover.state='DEGRADED-ON-RESERVE';}],
  ['route switch','checking',s=>{s.native_failover.state='APPLYING';s.channel_path.transitioning=true;}],
  ['start unconfirmed','pending',s=>{s.auto_control.pair_phase='STARTING';}],
  ['cold stop has no confirmed ON','pending',s=>{s.auto_control.requested='off';s.auto_control.pair_phase='STOPPING';s.native_failover.state='RESTORING';}],
  ['confirmed stopped','off',s=>{s.auto_control.requested='off';s.auto_control.pair_phase='STOPPED';s.native_failover.state='STOPPED';}],
  ['start refused','refused',s=>{s.auto_control.requested='off';s.auto_control.pair_phase='FAILED';s.auto_control.failure={code:'ROLLBACK-GIVEN-UP'};s.native_failover.state='BLOCKED';s.native_failover.blockers=['ROLLBACK-GIVEN-UP'];}],
  ['speed pause keeps confirmed switch','checking',s=>{s.speed_pause={active:true,auto_paused:true,monitor_paused:true};}],
  ['old controller alarm is still a failure','failure',s=>{s.native_failover.time=800;s.native_failover.state='BLOCKED';s.native_failover.blockers=['ROLLBACK-GIVEN-UP'];}],
  ['mixed blocker names the real failure','failure',s=>{s.native_failover.state='BLOCKED';s.native_failover.blockers=['VENDOR-WORKER-BUSY','NATIVE-SYSTEM-001'];s.native_failover.busy_seconds=125;s.native_failover.reason='VENDOR-BUSY-WORKERS';}],
  ['missing controller data','checking',s=>{s.native_failover.time=800;}]
 ];
 for(const [name,row,mutate] of cases){reset();const s=fixture();mutate(s);try{inspect(s,row);}catch(error){error.message=name+': '+error.message;throw error;}}
 // Check the actual shipped module too: extraction must retain the same table and adapters.
 const {load}=require('./approved_page'),shipped=load({lang:language});
 for(const [name,row,mutate] of cases){const s=fixture();mutate(s);shipped.T.HV.st=s;Object.assign(shipped.inventory.settings,inventory.settings);shipped.T.snap();
  const ui=shipped.T.autoState(),[lamp,,,words]=expected[row];assert.equal(ui.lamp,{green:'g',yellow:'y',red:'r',off:'n'}[lamp],'shipped '+name);assert.equal(ui.text,words[language==='en'?0:1],'shipped '+name);}
 // Every transient code, both confirmed phases, both carrying channels, at 0 s and after a 10-minute wait.
 for(const code of c.AUTO_TRANSIENT)for(const phase of ['RUNNING','HELD'])for(const carrier of ['a','b'])for(const age of [0,600]){
  reset();const s=fixture();s.native_failover.state='BLOCKED';s.native_failover.blockers=[code];s.auto_control.pair_phase=phase;s.channel_path.active_profile_id=carrier;
  c.autoLightModel(s,inventory,now);now+=age;for(const obj of [s,s.native_failover,s.channel_path,...s.profiles])obj.time=now;s.server_time=s.channel_path.checked_at=now;
  const light=inspect(s,'checking');const carrying=light.tunnels.findIndex(t=>t.carrier);assert.equal(carrying,carrier==='a'?0:1,'a wait preserves the proven traffic channel');
 }
 // Temporary missing proof keeps the last confirmed carrier in every display, never in command authorization.
 reset();let held=fixture();held.channel_path.active_profile_id='b';held.native_failover.state='BLOCKED';held.native_failover.blockers=['VENDOR-WORKER-BUSY'];inspect(held,'checking');
 held.channel_path.confirmed=false;held.channel_path.kernel_policy_verified=false;let heldLight=inspect(held,'checking');
 assert.equal(c.V.d.selectedRole,'target');assert.equal(c.selectedRole(),'reserve');assert(heldLight.tunnels[1].carrier);
 assert.equal(c.manualConfirmedPath(held,held.profiles[0],held.profiles[1],now).selected,null,'held display proof cannot authorize a manual switch');
 now=1121;for(const obj of [held,held.native_failover,...held.profiles])obj.time=now;held.server_time=now;heldLight=inspect(held,'checking');assert(!heldLight.tunnels.some(t=>t.carrier));assert.equal(c.V.d.selectedRole,null,'held carrier expires after 120 s');
 reset();const stopping=fixture();inspect(stopping,'working');stopping.auto_control.requested='off';stopping.auto_control.pair_phase='STOPPING';stopping.native_failover.state='RESTORING';inspect(stopping,'checking');
 stopping.auto_control.pair_phase='STOPPED';stopping.native_failover.state='STOPPED';inspect(stopping,'off');
 // Exhaust native states, session phases, intent, blockers, route proof and selected-channel health.
 const states=['DISABLED','STOPPED','EXPIRED','ROLLED-BACK','OBSERVING','TRIAL-REQUIRED','ARMED','APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE','BLOCKED','RELEASE-PENDING','UNKNOWN-STATE',undefined];
 for(const state of states)for(const phase of ['STARTING','RUNNING','HELD','STOPPING','STOPPED','FAILED',undefined])for(const requested of ['on','off',undefined])for(const blockers of [[],['OBSERVATION-STALE'],['VENDOR-WORKER-BUSY'],['ROLLBACK-GIVEN-UP']])for(const route of ['a','b',null])for(const failed of [true,false]){
  reset();const s=fixture();s.native_failover.state=state;s.native_failover.blockers=blockers;s.auto_control.pair_phase=phase;s.auto_control.requested=requested;s.channel_path.active_profile_id=route;
  if(failed){s.profiles[route==='b'?1:0].code='VPN-003';s.profiles[route==='b'?1:0].https_success=0;}
  const before=JSON.stringify(s),light=c.autoLightModel(s,inventory,now);contract(light);assert.equal(JSON.stringify(s),before,'display never changes controller or routing data');
  if(light.key==='off')assert(!c.autoEnabled(light));
  if(phase==='STARTING'&&!['ok','reserve'].includes(light.key))assert(!c.autoEnabled(light),'Start request is not confirmed ON');
  if(requested==='on'&&['RUNNING','HELD'].includes(phase)&&light.key!=='off')assert(c.autoEnabled(light),'confirmed ON survives wait or failure');
 }
 // A transport failure without a previous confirmed session never invents ON. A known session stays ON,
 // yellow for the first missed answer, red after 90 s; recovery resets the timer.
 reset();let s=fixture();s.rpc_error='RPC';s.auto_control={};inspect(s,'pending');
 reset();s=fixture();inspect(s,'working');s.rpc_error='RPC';inspect(s,'checking');now+=c.AUTO_RPC_GRACE+1;inspect(s,'failure');
 delete s.rpc_error;now=1000;inspect(s,'working');
}
console.log('PASS: Auto state table, '+count+' exhaustive contracts and '+surfaces+' EN/RU surface scenarios; enabled switch, wait/failure lamps and carrying channel agree');
