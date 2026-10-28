const fs=require('fs'),vm=require('vm'),assert=require('assert');const {website}=require('./website_fixture');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs={...attrs};this.children=[].concat(children).flat().filter(v=>v!=null);this.disabled=attrs.disabled!=null;this.textContent='';this.classList={toggle:(name,on)=>{const list=new Set((this.attrs.class||'').split(/\s+/));if(on)list.add(name);else list.delete(name);this.attrs.class=Array.from(list).join(' ');}};}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k]??null;}
 all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}
 text(){return this.textContent+this.children.map(x=>x instanceof N?x.text():String(x)).join(' ');}
 querySelector(selector){return this.all().find(n=>selector==='.hv-auto-power'&&(n.attrs.class||'').split(/\s+/).includes('hv-auto-power'))||null;}
 click(){if(!this.disabled&&this.attrs.click)return this.attrs.click({currentTarget:this});}
}
function fixture(language){
 let now=1000,menu=0;const calls=[],replies=[];
 const c={E:(...args)=>new N(...args),bi:(en,ru)=>language==='ru'?ru:en,Date,WeakMap,window:{location:{reload(){}}},statusNow:()=>now,
  ui:{addNotification(){}},errorCodeLink:code=>code,
  rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise((resolve,reject)=>replies.push({resolve,reject}));}},
  vendorDisplayMember:(s,i,role)=>s.profiles.find(p=>p.id===i.settings['plan_'+role]),countryName:()=>language==='ru'?'Германия':'Germany',protocolLabel:p=>p.protocol==='wireguard'?'WireGuard':'OpenVPN',endpointText:p=>p?'Server: '+p.host:'Address not observed'};
 vm.createContext(c);for(const f of ['ui_logic','auto_panel','manual_panel','simple_home_policy','simple_home_panel'])vm.runInContext(fs.readFileSync('router/'+f+'.inc.js','utf8'),c);
 c.statusNow=()=>now;
 const inventory={settings:{terms_version:'1',onboarding_complete:true,onboarding_version:1,setup_complete:true,native_session_loss:true,enabled:true,plan_source:'a',plan_target:'b'}};
 const base={time:1000,profiles:[{id:'a',name:'Primary name',protocol:'wireguard',host:'primary.example',time:1000,interface:'wgclient1',dns_ok:true,https_success:2,rtt_ms:420},{id:'b',name:'Reserve name',protocol:'openvpn',host:'reserve.example',time:1000,interface:'ovpnclient1',dns_ok:true,https_success:2,rtt_ms:670}],native_failover:{time:1000,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,source:'a',target:'b',blockers:[]},auto_control:{requested:'on',pair_phase:'RUNNING',requested_at:900,control_revision:'a'.repeat(32)},channel_path:{time:1000,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:1000,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a'}};
 base.profiles=base.profiles.map((p,i)=>website(p,i?67.8:42.1));
 return {c,inventory,base,calls,replies,setNow:v=>now=v,now:()=>now,menu:()=>menu,open:()=>menu++};
}
const clone=x=>JSON.parse(JSON.stringify(x));
(async()=>{
for(const language of ['en','ru']){
 const f=fixture(language),{c,inventory,base}=f;
 const paused=clone(base);paused.speed_pause={active:true,phase:'PAUSED',auto_paused:true,monitor_paused:true};
 assert.equal(c.autoControlModel(paused,1000).on,false,'paused Auto cannot claim it watches the route');assert(c.autoControlModel(paused,1000).paused);
 assert.equal(c.simpleHomeModel(paused,inventory,1200).state,'pending','verified pause remains explicit when measurements age');
 assert(c.autoLightModel(paused,inventory,1200).title.includes(language==='ru'?'паузе':'paused'),'pause beats stale/off descriptions');
 let model=c.simpleHomeModel(base,inventory,1000);assert(model.showCard);assert.equal(model.state,'on');assert.equal(model.selectedRole,'source');
 const blocked=clone(base);blocked.native_failover.state='BLOCKED';blocked.native_failover.blockers=['HARDWARE-ACCELERATOR-UNVERIFIED'];blocked.auto_control.requested='off';blocked.auto_control.pair_phase='HELD';
 const blockedModel=c.simpleHomeModel(blocked,inventory,1000);assert.equal(blockedModel.state,'error');assert.equal(blockedModel.blockers[0],'HARDWARE-ACCELERATOR-UNVERIFIED');
 blocked.auto_control.requested='on';blocked.auto_control.pair_phase='RUNNING';assert.equal(c.simpleHomeAutoEnabled(blocked,1000),false,'old RUNNING intent cannot claim a blocked controller works');
 blocked.auto_control.requested='off';blocked.auto_control.pair_phase='FAILED';blocked.auto_control.requested_at=950;
 c.autoCommandPending={stop:false,acknowledged:true,baseline:900};
 assert.equal(c.autoCommandOperation(blocked,1000),null,'refused preflight ends queued Start');
 assert.equal(c.simpleHomeModel(blocked,inventory,1000).state,'error','failed Start shows reason instead of indefinite Starting');
 blocked.auto_control.requested='on';blocked.auto_control.pair_phase='STARTING';c.autoCommandPending={stop:false,acknowledged:true,baseline:900};
 assert.equal(c.autoCommandOperation(blocked,1000),null,'fresh explicit BLOCKED never hides behind Starting');
 assert.equal(c.simpleHomeModel(blocked,inventory,1000).state,'error');
 const moving=clone(base);moving.native_failover.state='APPLYING';moving.auto_control.requested='on';moving.auto_control.pair_phase='RUNNING';c.autoCommandPending=null;
 assert.equal(c.autoCommandOperation(moving,1000),null,'a route switch inside running Auto is not Turning Auto on');
 c.autoCommandPending={stop:false,acknowledged:true,baseline:5000,t0:Date.now()-10*60*1000};
 assert.equal(c.autoCommandOperation(base,1000),'unconfirmed','a missing completion is explicit after its deadline');assert.equal(c.autoCommandPending,null);assert(c.autoCommandUnconfirmed);c.autoCommandUnconfirmed=null;
 let clicked=0;const original=new N('button',{'class':'hv-auto-power','click':()=>clicked++}),control={querySelector:selector=>selector==='.hv-auto-power'?original:null};
 const card=c.renderSimpleHome(base,inventory,model,control,f.open),nodes=card.all(),power=nodes.find(n=>n.attrs['data-simple-home-auto']);
 assert.equal(f.calls.length,0,'Rendering performs no RPC');assert.equal(nodes.filter(n=>n.attrs['data-simple-home-auto']).length,1);
 assert.equal(nodes.filter(n=>n.attrs['data-simple-open-menu']).length,1);assert(card.text().includes('primary.example'));assert(card.text().includes('42.1'));assert(!card.text().includes('420'),'Minimum never substitutes old technical RTT');
 const details=nodes.find(n=>n.tag==='details'&&n.attrs['data-home-details']==='channels');assert(details&&!details.attrs.open,'Addresses/RTT initially collapsed');
 const reserve=nodes.find(n=>n.attrs['data-simple-role']==='target');assert(!/hv-manual-red|failed|inactive/.test(reserve.attrs.class),'Healthy standby is not an error');
 power.click();assert.equal(clicked,1);assert.equal(f.menu(),0,'Command does not abandon Minimum');
 const menu=nodes.find(n=>n.attrs['data-simple-open-menu']);menu.click();assert.equal(f.menu(),1);
 const unavailable=clone(base);unavailable.rpc_error='RPC';model=c.simpleHomeModel(unavailable,inventory,1000);assert(model.showCard);assert.equal(model.state,'unknown');assert.equal(model.selectedRole,null);assert.equal(model.sourceHealth.state,'unknown');assert.equal(model.targetHealth.state,'unknown');
 for(const edit of [s=>s.time=800,s=>s.native_failover.time=800,s=>s.auto_control.pair_phase='STOPPING',s=>s.auto_control.pair_phase='STARTING',s=>s.auto_control.requested='off']){const s=clone(base);edit(s);assert(c.simpleHomeModel(s,inventory,1000).showCard,'Changing evidence never removes Minimum');}
 for(const key of ['terms_version','onboarding_complete','setup_complete','native_session_loss','enabled']){const i=clone(inventory);i.settings[key]=false;assert(c.simpleHomeModel(base,i,1000).showCard);}
 const onReserve=clone(base);onReserve.native_failover.state='COMMITTED';onReserve.channel_path.active_profile_id='b';onReserve.profiles[0].code='VPN-003';model=c.simpleHomeModel(onReserve,inventory,1000);assert.equal(model.selectedRole,'target');assert.equal(model.state,'on');
 let navigated=0;const shortcut=c.renderSimpleHomeShortcut(()=>({showCard:false,dataUnavailable:true}),()=>navigated++);const button=shortcut.all().find(n=>n.attrs['data-simple-shortcut']);button.click();assert.equal(navigated,1,'Return remains accessible with stale/OFF data');assert(!button.disabled);
 // Old data must not issue a Start through the real authoritative controller.
 const off=clone(base);off.native_failover.state='STOPPED';off.auto_control.requested='off';off.auto_control.pair_phase='STOPPED';off.channel_path.confirmed=false;
 f.setNow(1000);const staleControl=c.renderAutoPowerControl(off,inventory);
 const staleCard=c.renderSimpleHome(off,inventory,c.simpleHomeModel(off,inventory,1000),{querySelector:selector=>selector==='.hv-auto-power'?staleControl.button:staleControl.actionLabel},f.open);
 const stalePower=staleCard.all().find(n=>n.attrs['data-simple-home-auto']);assert.strictEqual(stalePower,staleControl.button,'Home reuses authoritative DOM control');
 f.setNow(1200);stalePower.click();assert(!f.calls.some(call=>call.method==='native_start'),'Expired evidence cannot issue Start');
 if(f.replies.length){f.replies.shift().resolve({queued:false,accepted:false});await new Promise(r=>setImmediate(r));}
 f.calls.length=0;c.autoCommandPending=null;f.setNow(1000);
 // Real control, not a fake click: pending Start must permit immediate Stop.
 const authoritative=c.renderAutoPowerControl(off,inventory);const actualCard=c.renderSimpleHome(off,inventory,c.simpleHomeModel(off,inventory,1000),{querySelector:selector=>selector==='.hv-auto-power'?authoritative.button:authoritative.actionLabel},f.open);
 const actualPower=actualCard.all().find(n=>n.attrs['data-simple-home-auto']);actualPower.click();
 assert.equal(f.calls[0].method,'native_start');assert(!actualPower.disabled,'Pending Start stays cancellable from Minimum without a polling redraw');actualPower.click();
 assert.deepEqual(f.calls.map(x=>x.method),['native_start','native_stop'],'Immediate second action is Stop');
 f.replies[0].resolve({accepted:false,code:'STOP-SUPERSEDED-START'});f.replies[1].resolve({queued:true});await new Promise(r=>setImmediate(r));
 assert(actualPower.disabled,'Stop ACK alone is not completed Stop');
}
console.log('PASS: Minimum ON/OFF/UNKNOWN presentation, neutral standby, collapsed details, accessible menu/return, stale Start guard and actual pending Start/Stop forwarding EN/RU (model only)');
})().catch(error=>{console.error(error);process.exitCode=1;});
