const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.value=attrs.value||'';this.disabled=attrs.disabled!=null;this.checked=false;this.events={};(Array.isArray(children)?children:[children]).forEach(n=>this.appendChild(n));}
  appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]??null;}removeAttribute(k){delete this.attrs[k];}
  querySelectorAll(selector){return walk(this).filter(n=>selector.split(',').includes(n.tag));}
  addEventListener(k,fn){(this.events[k]||(this.events[k]=[])).push(fn);}
  get childNodes(){return this.children;}get textContent(){return this.children.map(n=>n instanceof Node?n.textContent:String(n)).join('');}set textContent(v){this.children=[String(v)];}
}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const button=(root,label)=>walk(root).find(n=>n.tag==='button'&&n.textContent===label);
const click=n=>n.attrs.click({target:n,currentTarget:n});
function make(){
  let modal,calls=[],pending={},timers=[],reloads=0;
  const c={E:(...a)=>new Node(...a),L:{resource:s=>s},bi:en=>en,locale:'en',safeCode:s=>typeof s==='string'&&/^[A-Z][A-Z0-9-]+$/.test(s),errorCodeLink:s=>s,helpLink:(_,label)=>new Node('a',{},label),serverTitle:p=>p.name,setTimeout:fn=>timers.push(fn),window:{location:{reload(){reloads++;}}},
    ui:{showModal:(_,nodes)=>modal=new Node('modal',{},nodes),hideModal:()=>modal=null,addNotification(){}},rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise(resolve=>(pending[spec.method]||(pending[spec.method]=[])).push(resolve));}}};
  vm.createContext(c);for(const f of ['fool_guard','ui_logic','auto_panel','vendor_diagnostics','setup_wizard','fault_panel','speed_live','speed_table'])vm.runInContext(fs.readFileSync('router/'+f+'.inc.js','utf8'),c);
  return {c,calls,get reloads(){return reloads;},get modal(){return modal;},finish:(method,value)=>pending[method].shift()(value),tick:()=>{const old=timers;timers=[];old.forEach(fn=>fn());}};
}
function faultFixture(now){
  const profiles=[['openvpn:a','openvpn','ovpnclient1','a'],['wireguard:b','wireguard','wgclient1','b']].map(([id,protocol,logical,letter])=>({id,name:id,protocol,interface:logical,channel:'Same editable label',time:now,code:null,dns_ok:true,https_success:2,vendor_tunnel_id:protocol+':'+logical,vendor_generation:letter.repeat(32),vendor_state:'SETTLED',vendor_changed_at:now-20}));
  const groups=profiles.map(p=>({id:p.vendor_tunnel_id,protocol:p.protocol,profiles:[p.id],active_profiles:[p.id],current_profile:p.id,state:'SETTLED',stable_samples:2,generation:p.vendor_generation,time:now,changed_at:now-20}));
  const inventory={settings:{plan_source:profiles[0].id,plan_target:profiles[1].id,plan_source_tunnel:profiles[0].vendor_tunnel_id,plan_target_tunnel:profiles[1].vendor_tunnel_id,native_session_loss:true,interval:30}};
  const status={time:now,profiles,vendor_observation:{version:1,time:now,groups,events:[]},native_failover:{state:'OBSERVING',certified:true,time:now,source:profiles[0].id,target:profiles[1].id,vendor_identity:'c'.repeat(64),source_generation:profiles[0].vendor_generation,target_generation:profiles[1].vendor_generation},failover_plan:{coordination:{version:1,time:now,state:'READY',code:'CROSS-TUNNEL-READY',source_tunnel:groups[0].id,target_tunnel:groups[1].id,transition:'protocol',can_apply:false,vendor_attempts_exhausted:null,vendor_reason:'UNOBSERVED'}}};
  return {status,inventory};
}
(async()=>{
  let m=make(),c=m.c,now=Date.now()/1000;
  const profiles=[{id:'a',name:'Alpha',channel:'main',interface:'wg0'},{id:'b',name:'Beta',channel:'main',interface:'wg1'}];
  c.speedSelected.a=true;let panel=c.speedPanel({profiles},{settings:{speed_enabled:true}},'latest',()=>{});
  click(button(panel,'Test speed'));let run=button(m.modal,'Run test'),work=click(run);click(run);assert.equal(m.calls.filter(x=>x.method==='speed_start').length,1);
  const cancel=click(button(panel,'Cancel current test'));assert.equal(m.calls.at(-1).method,'speed_cancel','cancel dispatches while start pending');m.finish('speed_cancel',{queued:true});await cancel;m.finish('speed_start',{accepted:false});await work;
  // Invalid stored values are rejected, rather than silently replaced with defaults.
  panel=c.speedPanel({profiles},{settings:{speed_enabled:true,speed_budget_mib:0}},'latest',()=>{});click(button(panel,'Test speed'));assert(!m.modal);assert.equal(m.calls.filter(x=>x.method==='speed_start').length,1);
  m=make();c=m.c;let refreshed=0;
  let fixture=faultFixture(now);panel=c.faultPanel(fixture.status,fixture.inventory,()=>{refreshed++;return Promise.resolve();});
  const selects=walk(panel).filter(n=>n.tag==='select');assert.equal(selects.length,1,'only duration is selected; channel is automatic');assert(!button(panel,'Stop test and restore traffic'),'no idle cancel button');assert(!panel.textContent.includes('Simulate server failure'));
  click(button(panel,'Simulate traffic failure'));run=button(m.modal,'Start transition test');assert(m.modal.textContent.includes('openvpn:ovpnclient1'));assert(!m.modal.textContent.includes('wireguard:wgclient1'),'equal editable labels never broaden affected tunnel scope');
  selects[0].value='30';work=click(run);click(run);assert.equal(m.calls.filter(x=>x.method==='fault_start').length,1);assert.deepEqual(Array.from(m.calls[0].args),['openvpn:a','channel',150],'send precisely the reviewed tunnel/id/duration');
  fixture.status.operator_fault={state:'ACTIVE'};panel=c.faultPanel(fixture.status,fixture.inventory,()=>{refreshed++;return Promise.resolve();});const faultCancel=click(button(panel,'Stop test and restore traffic'));assert.equal(m.calls.at(-1).method,'fault_cancel');m.finish('fault_cancel',{code:'FAULT-CANCELLED'});await faultCancel;m.finish('fault_start',{code:'FAULT-QUEUED'});await work;assert.equal(refreshed,2);
  // Fresh public certificate hints must match the exact current members and generation; server authorization is separate.
  for(const change of [s=>s.native_failover.source='openvpn:old',s=>s.native_failover.target='wireguard:old',s=>s.native_failover.source_generation='d'.repeat(32),s=>s.native_failover.vendor_identity=null,s=>s.native_failover.certified=false,s=>s.native_failover.time=now-31,s=>s.failover_plan.coordination.code='VENDOR-SETTLING',s=>s.vendor_observation.groups[0].state='PENDING',s=>s.profiles[0].vendor_generation='e'.repeat(32)]){
    m=make();c=m.c;fixture=faultFixture(now);change(fixture.status);panel=c.faultPanel(fixture.status,fixture.inventory,()=>Promise.resolve());const disabled=button(panel,'Simulate traffic failure');assert(!disabled.disabled);click(disabled);assert(m.modal.textContent.includes('must confirm'));assert.equal(m.calls.length,0,'preparation explains missing evidence without a destructive RPC');
    fixture.status.operator_fault={state:'UNKNOWN'};panel=c.faultPanel(fixture.status,fixture.inventory,()=>Promise.resolve());const stopFault=click(button(panel,'Stop test and restore traffic'));assert.equal(m.calls.at(-1).method,'fault_cancel','cleanup stays available for unknown state');m.finish('fault_cancel',{code:'FAULT-CANCELLED'});await stopFault;
  }
  // Prepared continuous Auto needs no legacy LAN certificate and automatically targets reserve too.
  for(const reserve of [false,true]){
    m=make();c=m.c;fixture=faultFixture(now);fixture.inventory.settings.pair_auto_mode='router-probed-ipv4';
    fixture.status.auto_control={pair_phase:'RUNNING'};Object.assign(fixture.status.native_failover,{mode:'continuous-pair',proof_scope:'router-probed-ipv4',certified:false,readiness_verified:!reserve,state:reserve?'COMMITTED':'OBSERVING'});
    panel=c.faultPanel(fixture.status,fixture.inventory,()=>Promise.resolve());assert(c.faultCurrentBinding(fixture.status,fixture.inventory).ready);
    click(button(panel,'Simulate traffic failure'));run=button(m.modal,'Start transition test');work=click(run);
    assert.equal(m.calls[0].args[0],reserve?'wireguard:b':'openvpn:a');m.finish('fault_start',{accepted:true,code:'FAULT-ACTIVE'});await work;
  }
  // A new observed member or generation while the review is open refuses; it never retargets a reviewed destructive request.
  m=make();c=m.c;fixture=faultFixture(now);fixture.inventory.settings.interval=300;fixture.status.profiles[0].time=now-91;fixture.status.profiles[0].vendor_changed_at=now-120;fixture.status.vendor_observation.groups[0].changed_at=now-120;panel=c.faultPanel(fixture.status,fixture.inventory,()=>Promise.resolve());assert(!c.faultCurrentBinding(fixture.status,fixture.inventory).ready,'fault probe freshness stays90s even if general observation allows900s');
  m=make();c=m.c;fixture=faultFixture(now);panel=c.faultPanel(fixture.status,fixture.inventory,()=>Promise.resolve());click(button(panel,'Simulate traffic failure'));run=button(m.modal,'Start transition test');fixture.status.profiles[0].vendor_generation='e'.repeat(32);c.faultPanel(fixture.status,fixture.inventory,()=>Promise.resolve());click(run);assert.equal(m.calls.length,0);assert(m.modal,'stale review remains cancellable');
  m=make();c=m.c;const delivery=new Node('button',{},'Test Telegram');work=c.telegramTestDelivery(delivery);for(let i=0;i<20;i++)c.telegramTestDelivery(delivery);assert.equal(m.calls.length,1);m.finish('telegram_test',{code:'TELEGRAM-TEST-QUEUED'});await work;for(let i=0;i<20;i++)c.telegramTestDelivery(delivery);assert.equal(m.calls.length,1,'cooldown prevents repeated messages');for(let i=0;i<11;i++)m.tick();assert(!delivery.disabled);
  // Reopening System setup must not create expensive diagnostic storms or revive older dialogs.
  m=make();c=m.c;let checkClock=0;c.Date={now:()=>checkClock};for(let i=0;i<30;i++)c.setupWizard({settings:{},profiles:[]},'system');assert.equal(m.calls.length,1,'one shared pending readiness request');click(button(m.modal,'Cancel'));m.finish('setup_check',{passed:true});await Promise.resolve();await Promise.resolve();assert.equal(m.modal,null,'old readiness callbacks cannot reopen replaced/cancelled dialogs');
  c.setupWizard({settings:{},profiles:[]},'system');await Promise.resolve();await Promise.resolve();assert.equal(m.calls.length,1,'short cache bounds repeated settled checks');checkClock=10001;c.setupWizard({settings:{},profiles:[]},'system');assert.equal(m.calls.length,2,'expired cache permits a fresh check');m.finish('setup_check',{passed:false});await Promise.resolve();await Promise.resolve();
  // The normal toggle waits for controller completion; independent emergency Stop stays available.
  m=make();c=m.c;
  c.autoControlModel=s=>({stop:(s.native_failover||{}).state==='COMMITTED',fresh:!!s.time,on:(s.native_failover||{}).state==='COMMITTED',off:(s.native_failover||{}).state==='STOPPED'});c.autoLightModel=()=>({key:'ok'});c.autoWorking=()=>true;c.renderAutoLight=()=>new Node('span');c.autoPathModel=()=>({source:'neutral',target:'neutral',direction:'none'});c.autoWindowDeadline=()=>0;c.autoReadiness=()=>({steps:[]});
  let stamp=Date.now()/1000;
  const status=(state,phase='RUNNING')=>({auto_control:{control_revision:'a'.repeat(32),pair_phase:phase,requested_at:stamp},native_failover:{state,time:Date.now()/1000},time:Date.now()/1000}),render=(state,phase)=>c.renderAutoControl(status(state,phase),{settings:{}}),power=p=>walk(p).find(n=>(n.attrs.class||'').includes('hv-auto-power '));
  panel=render('COMMITTED');work=click(button(panel,'Return to primary'));const stop=click(power(panel));assert.deepEqual(m.calls.map(x=>x.method),['native_return','native_stop']);
  assert(power(render('COMMITTED')).disabled);m.finish('native_return',{queued:true,accepted:true});await work;assert(power(render('COMMITTED')).disabled,'late Return must not unlock pending Stop');m.finish('native_stop',{queued:true});await stop;assert(power(render('COMMITTED')).disabled,'Stop ACK is not completion');
  stamp++;panel=render('STOPPED','STOPPED');assert(!power(panel).disabled,'completed Stop unlocks normal toggle');
  work=click(power(panel));assert.deepEqual(Array.from(m.calls.at(-1).args),['a'.repeat(32),'manual']);assert(!power(panel).disabled,'pending Start allows cancellation on the same button');
  panel=render('COMMITTED','STARTING');assert(!power(panel).disabled,'redraw preserves cancellation');const secondStop=click(power(panel));assert.equal(m.calls.at(-1).method,'native_stop');m.finish('native_start',{accepted:false,blockers:['STOP-SUPERSEDED-START']});await work;assert(power(render('COMMITTED','STOPPING')).disabled,'late Start response cannot unlock Stop');m.finish('native_stop',{queued:true});await secondStop;
  stamp++;panel=render('STOPPED','STOPPED');assert(!power(panel).disabled);
  const before=m.calls.length;panel=c.renderAutoControl({...status('STOPPED','STOPPED'),auto_control:{}},{settings:{}});click(power(panel));assert.equal(m.calls.length,before,'unknown revision cannot send Start');assert.equal(m.reloads,1);
  panel=render('STOPPED','STOPPED');work=click(power(panel));m.finish('native_start',{accepted:false,blockers:['CONTROL-REVISION-STALE']});await work;assert.equal(m.reloads,2,'stale revision must refresh current controls');
  panel=c.renderAutoControl({}, {error:'RPC-UNAVAILABLE',settings:{}});const emergency=power(panel);assert(emergency&&!emergency.disabled,'unknown/off/unavailable state still offers Emergency Stop');const emergencyWork=click(emergency);click(emergency);assert.equal(m.calls.at(-1).method,'native_stop');assert.deepEqual(Array.from(m.calls.at(-1).args),['manual']);assert(power(render('STOPPED','STOPPING')).disabled,'redraw joins pending Stop lock');m.finish('native_stop',{queued:true});await emergencyWork;
  stamp++;assert(!power(render('STOPPED','STOPPED')).disabled,'confirmed stop releases emergency lock');
  console.log('PASS: active speed-table and fault single-flight, immediate cancels, immutable reviewed fault parameters, no silent zero defaults, Telegram burst cooldown and independent emergency Stop during pending Start/Return');
})().catch(error=>{console.error(error);process.exitCode=1;});
