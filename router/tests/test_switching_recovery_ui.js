// One shared state/operation model: live transitions, deadlines, recovery-needed and connection wording on every surface.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N {
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children||[]).flat().filter(x=>x!=null);this.disabled=this.attrs.disabled!=null;this.style={setProperty(){}};this.classList={contains:k=>String(this.attrs.class||'').split(' ').includes(k),toggle:(k,on)=>{let w=String(this.attrs.class||'').split(' ').filter(x=>x!==k);if(on)w.push(k);this.attrs.class=w.join(' ');},add:k=>this.classList.toggle(k,true)};}
  setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}removeAttribute(k){delete this.attrs[k];}appendChild(v){this.children.push(v);return v;}get firstChild(){return this.children[0];}removeChild(v){this.children.splice(this.children.indexOf(v),1);}
  all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}
  text(){return ((this.textContent||'')+' '+this.children.map(x=>x instanceof N?x.text():String(x)).join(' ')).replace(/\s+/g,' ').trim();}
  querySelector(s){return this.all().find(n=>s[0]==='.'&&n.classList.contains(s.slice(1)))||null;}
}
const T=1000,ID='c'.repeat(32),REV='b'.repeat(32);
function fixture(language){
  const clock={wall:T*1000,tick:T*1000},calls=[],replies=[],notes=[];
  const c={console,Promise,E:(...a)=>new N(...a),bi:(en,ru)=>language==='ru'?ru:en,locale:language,
    Date:class extends Date{static now(){return clock.wall;}},performance:{now:()=>clock.tick},
    window:{localStorage:{getItem:()=>null,setItem(){}},location:{reload(){}}},setInterval:()=>1,clearInterval(){},
    ui:{addNotification:(_,n)=>notes.push(n.text())},errorCodeLink:code=>new N('code',{},code),
    rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise((resolve,reject)=>replies.push({resolve,reject}));}},
    vendorDisplayMember:(s,i,role)=>s.profiles.find(p=>p.id===i.settings['plan_'+role]),countryName:()=>null,protocolLabel:p=>p.protocol,endpointText:()=>'',identityModel:()=>({agent:'test'})};
  vm.createContext(c);
  for(const name of ['ui_logic','auto_panel','manual_panel','sidebar_status','simple_home_policy','simple_home_panel','monitor_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  return {c,clock,calls,replies,notes,inventory:{settings:{enabled:true,plan_source:'a',plan_target:'b'}}};
}
const path=extra=>Object.assign({mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,time:null,checked_at:null,confirmed:false,kernel_policy_verified:false,active_profile_id:null,transitioning:false,source_profile_id:'a',target_profile_id:'b',code:'KERNEL-POLICY-UNVERIFIED'},extra||{});
function base(){
  return {time:T,server_time:T,observation_valid_for:90,profiles:['a','b'].map((id,i)=>({id,interface:i?'ovpnclient1':'wgclient1',protocol:i?'openvpn':'wireguard',time:T,dns_ok:true,https_success:3,observation_valid_for:90})),
    native_failover:{time:T,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,source:'a',target:'b'},
    auto_control:{requested:'on',requested_at:500,pair_phase:'RUNNING',failure:null,control_revision:REV},
    channel_path:path({time:T,checked_at:T,confirmed:true,kernel_policy_verified:true,active_profile_id:'a',code:null}),
    manual_switch:{state:'IDLE'},
    manual_switch_control:{time:T,mode:'continuous-pair',control_revision:REV,available:true,reserve:{allowed:true,blockers:[]},primary:{allowed:true,blockers:[]},resume:{allowed:false,blockers:[]}}};
}
// The live incident: journal APPLYING with a dead worker (not visible as a live phase), pair HELD, intent off, native BLOCKED.
function incident(){
  const s=base();
  s.native_failover={time:T,state:'BLOCKED',mode:'continuous-pair',proof_scope:'router-probed-ipv4',original_restored:false,blockers:['PAIR-RECOVERY-REQUIRED'],channel_path:path()};
  s.auto_control={requested:'off',requested_at:900,pair_phase:'HELD',failure:{code:'PAIR-RECOVERY-REQUIRED',time:800},control_revision:REV};
  s.channel_path=path();
  s.manual_switch={state:'REFUSED',direction:'reserve',request_id:ID,requested_at:950,updated_at:951,completed:false,code:'KERNEL-POLICY-UNVERIFIED'};
  s.manual_switch_control={available:false,mode:'continuous-pair',time:T};
  return s;
}
// A claimed manual request whose worker wait has not republished for `age` seconds (no kernel proof yet).
function applying(age,extra){
  const s=base();
  s.native_failover=Object.assign({time:T-age,state:'APPLYING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',source:'a',target:'b',original_restored:false,channel_path:path({transitioning:true})},extra||{});
  s.channel_path=path({transitioning:true});
  s.manual_switch={state:'CLAIMED',direction:'reserve',request_id:ID,requested_at:T-age-2,updated_at:T-age-1,completed:false,code:null};
  s.manual_switch_control={time:T,mode:'continuous-pair',control_revision:REV,available:true,reserve:{allowed:false,blockers:['PAIR-MANUAL-BUSY']},primary:{allowed:false,blockers:['PAIR-MANUAL-BUSY']},resume:{allowed:false,blockers:['PAIR-MANUAL-BUSY']}};
  return s;
}
const surfaces=(f,s)=>{
  const {c,inventory}=f,now=c.statusNow(s),side=new N('div');c.fillSideStatus(side,s,inventory);
  const model=c.simpleHomeModel(s,inventory,now),home=c.renderSimpleHome(s,inventory,model,null,()=>{}),manual=c.renderManualSwitch(s,inventory),power=c.renderAutoPowerControl(s,inventory);
  return {now,light:c.autoLightModel(s,inventory,now),side,model,home,manual,power,all:[side.text(),home.text(),manual.text(),power.actionLabel.text()].join(' | ')};
};
const green=v=>v.manual.all().some(n=>/hv-manual-green/.test(n.attrs.class||''))||v.side.all().slice(0).filter(n=>/hv-auto-pill-knob/.test(n.attrs.class||'')).slice(2).some(n=>/hv-lamp-on/.test(n.attrs.class));
const knobs=v=>v.side.all().filter(n=>/hv-auto-pill-knob/.test(n.attrs.class||'')).map(n=>n.attrs.class.replace('hv-auto-pill-knob hv-lamp-',''));
const tasks=[];
for(const language of ['en','ru']){
  const ru=language==='ru';
  {
    // Incident: every zone says recovery is needed with its reason; nothing claims switching, success or an owner change.
    const f=fixture(language),s=incident(),v=surfaces(f,s);
    assert.equal(v.light.key,'problem');assert.equal(v.light.code,'PAIR-RECOVERY-REQUIRED');assert.equal(v.light.title,ru?'Нужно восстановление':'Recovery needed');
    assert.equal(v.model.state,'error');assert.equal(v.model.title,v.light.title,'Minimum and Overview share one title');
    assert(v.side.text().includes(v.light.title),'sidebar uses the same recovery title');assert(!/нет связи|no connection/i.test(v.side.text()),'fresh RPC is not described as a lost connection');
    assert.equal(knobs(v)[0],'off','Auto lamp is red, not unknown/green');assert(!green(v),'no green channel without kernel proof');
    assert(!/outside the app|вне приложения|Switching channel|Переключение канала|Switching the route|Переключение маршрута/.test(v.all),'no owner blame and no in-progress claim: '+v.all.slice(0,300));
    assert(/PAIR-RECOVERY-REQUIRED/.test(v.power.actionLabel.text())&&/recovery|восстановлен/.test(v.power.actionLabel.text()),'Start states why it will be refused');
    const cards=v.manual.all().filter(n=>n.attrs['data-manual-direction']);assert.equal(cards.length,2,'manual buttons stay visible');assert(cards.every(n=>n.disabled));
    ['primary','reserve'].forEach(d=>{const reason=v.manual.all().find(n=>n.attrs['data-manual-diagnostic']===d);assert(reason&&reason.text().includes('PAIR-RECOVERY-REQUIRED'),'each disabled direction names the recovery reason');});
    assert(v.manual.all().some(n=>n.attrs['data-manual-recovery']==='PAIR-RECOVERY-REQUIRED'),'manual panel explains the recovery state');
    assert(v.home.all().some(n=>n.attrs['data-auto-remedy']==='PAIR-RECOVERY-REQUIRED'),'Minimum offers the matching recovery explanation');
    assert.equal(f.c.autoRemedyKey('PAIR-RECOVERY-REQUIRED'),'unfinished');assert.equal(f.c.autoRemedyKey('PAIR-EXTERNAL-CONFIG-CHANGE'),'recovery');
    for(const code of ['PAIR-RECOVERY-REQUIRED','PAIR-EXTERNAL-CONFIG-CHANGE','PAIR-EXTERNAL-POLICY-CHANGE','TRANSACTION-IN-PROGRESS'])assert(!/outside the app|вне приложения|you changed|already in progress|уже идёт/.test(f.c.autoBlockerText(code)),code+' does not blame the owner or assert a running switch');
    // Same journal, but intent on and a fresh Start refusal: still recovery, never "Auto did not start" plus "switching".
    const refused=incident();refused.native_failover.state='BLOCKED';refused.auto_control.requested='off';assert.equal(f.c.autoCommandOperation(refused,T),null);
  }
  {
    // A live transition 40 s after its last publication: still proven by the controller's bounded deadline.
    const f=fixture(language),s=applying(40);
    const route=f.c.channelPathSelection(s,T,'a','b');assert.equal(route.moving,true);assert.equal(route.code,null,'no premature KERNEL-POLICY-UNVERIFIED during a proven live operation');
    assert(f.c.autoControlModel(s,T).fresh,'a worker wait is not stale controller data');assert(f.c.autoControlModel(s,T).transitioning);
    const v=surfaces(f,s);assert.equal(v.light.key,'switching');assert(!green(v),'no green while moving');
    assert(!/нет связи|no connection|устарел|out of date/i.test(v.side.text()));
    const timer=f.c.uiOperationTimerText(s,T);assert(timer.includes(ru?'Применение правил роутера':'Applying router rules'),'stage is named: '+timer);
    assert(timer.includes(ru?'0:42 прошло':'0:42 elapsed'),'elapsed from the request: '+timer);assert(timer.includes(ru?'предел через 1:20':'limit in 1:20'),'remaining to the real deadline: '+timer);
    const pendingCard=v.manual.all().find(n=>n.attrs['data-manual-direction']==='reserve');assert(pendingCard.all().some(n=>n.attrs['data-op-timer']),'the switching card carries the shared timer');
    const other=v.manual.all().find(n=>n.attrs['data-manual-diagnostic']==='primary');assert(other&&other.text().includes(ru?'Операция уже выполняется':'An operation is already running'),'repeat request explains the running operation');
    assert(v.power.actionLabel.all().some(n=>n.attrs['data-op-timer']),'Auto button shows the same timer during a manual switch');
    // One shared timer: the heartbeat refreshes every registered node from the same model.
    f.clock.tick+=10000;f.c.uiTimerTick();const node=v.manual.all().find(n=>n.attrs['data-op-timer']);assert(node.textContent.includes(ru?'0:52 прошло':'0:52 elapsed'),'shared tick advanced: '+node.textContent);
    // The published WAIT-CLIENT deadline is authoritative when present.
    const wait=applying(10,{state:'WAIT-CLIENT',deadline:T+20});assert(f.c.uiOperationTimerText(wait,T).includes(ru?'предел через 0:20':'limit in 0:20'));
    // Guarded recovery of an interrupted switch (vendor rebuild): recovery in progress with a timer, never success.
    const rec=applying(10,{state:'RESTORING',restore_proof_source:'vendor-rebuild'}),rv=surfaces(f,rec);
    assert.equal(f.c.uiTransitionModel(rec,T).state,'RECOVERING');assert.equal(rv.light.title,ru?'Восстановление после прерванного переключения':'Recovery after an interrupted switch');
    assert.equal(rv.model.title,rv.light.title,'Minimum shows the same recovery stage');assert(f.c.uiOperationTimerText(rec,T).includes(ru?'Восстановление после прерванного переключения':'Recovery after an interrupted switch'));
    assert(f.c.uiOperationTimerText(rec,T).includes(ru?'предел через 1:50':'limit in 1:50'),'120-s budget');assert(!green(rv));assert.equal(f.c.channelPathSelection(rec,T,'a','b').selected,null);
    // A 95-second transition: after the 90-s deadline the page checks the result instead of promising success.
    const late=applying(125);assert(f.c.uiTransitionModel(late,T).phase==='checking');const lv=surfaces(f,late);assert.equal(lv.light.key,'switching');
    assert(f.c.uiOperationTimerText(late,T).includes(ru?'проверяем результат':'checking the result'));assert(!f.c.manualOperationModel(late,T).uncertain,'still inside the grace period');assert(!green(lv));
    // Past deadline + grace: an unconfirmed result, never infinite switching and never success.
    const over=applying(150),ov=surfaces(f,over);assert(f.c.uiTransitionModel(over,T).overdue);
    assert.equal(f.c.channelPathSelection(over,T,'a','b').code,'KERNEL-POLICY-UNVERIFIED','a transition without a live operation keeps the real error');
    assert.equal(ov.light.code,'SWITCH-RESULT-UNCONFIRMED');assert.equal(ov.light.key,'problem');assert(f.c.manualOperationModel(over,T).uncertain);assert(!green(ov));
    assert(!/Switching the route|Переключение маршрута/.test(ov.all));assert(f.c.autoControlModel(over,T).stop===true||f.c.autoControlModel(over,T).stop===false);
  }
  {
    // The transitioning flag is not proof without a live controller phase.
    const f=fixture(language),s=applying(5);s.native_failover.state='BLOCKED';s.native_failover.blockers=['NATIVE-SYSTEM-001'];
    assert.equal(f.c.channelPathSelection(s,T,'a','b').moving,false);assert.equal(f.c.channelPathSelection(s,T,'a','b').code,'KERNEL-POLICY-UNVERIFIED');
    // A backwards router clock jump cannot keep an old phase "live" or forge success.
    const jump=applying(0);jump.native_failover.time=T+600;assert(!f.c.uiTransitionModel(jump,T).live);assert.equal(f.c.channelPathSelection(jump,T,'a','b').selected,null);
  }
  {
    // Connection wording: only a lost router-program answer is "no connection".
    const f=fixture(language),stale=base();stale.native_failover.time=T-200;const sv=surfaces(f,stale);
    assert(!/нет связи|no connection/i.test(sv.side.text()),'stale controller with fresh RPC is not a lost connection');assert(sv.side.text().includes(ru?'Auto вкл.':'Auto ON'),'Auto the owner turned on stays on while data is late');
    assert(!/Нет связи с роутером|No connection to the router/.test(sv.home.text()));
    const lost=Object.assign(base(),{rpc_error:'RPC-UNAVAILABLE'});const lv=surfaces(f,lost);assert(lv.side.text().includes(ru?'Auto вкл.':'Auto ON'),'one lost answer keeps Auto on');
  }
  {
    // Reload during an operation: the backend request keeps the buttons busy with a deadline-bounded stage.
    const f=fixture(language),q=base();q.manual_switch={state:'QUEUED',direction:'reserve',request_id:ID,requested_at:T-10,updated_at:T-10,completed:false,code:null};
    const m=f.c.manualOperationModel(q,T);assert(m.busy&&!m.uncertain);assert.equal(m.deadline,T+50);assert(f.c.uiOperationTimerText(q,T).includes(ru?'Ожидание контроллера':'Waiting for the controller'));
    assert(f.c.manualOperationModel(q,T+66).uncertain,'an unclaimed request past its 60-s expiry is uncertain, not switching');
  }
  {
    // Duplicate during a live operation: "already running" with the stage/timer, not a stored refusal of that operation.
    const f=fixture(language),s=applying(20);s.manual_switch={state:'IDLE'};s.manual_switch_control=base().manual_switch_control;s.channel_path=path({time:T,checked_at:T,confirmed:true,kernel_policy_verified:true,active_profile_id:'a',code:null});
    const view=f.c.renderManualSwitch(base(),f.inventory),card=view.all().find(n=>n.attrs['data-manual-direction']==='reserve');
    const pending=card.attrs.click();f.replies.shift().resolve({accepted:false,queued:false,completed:false,blockers:['PAIR-MANUAL-BUSY']});
    tasks.push(pending.then(()=>{assert.equal(f.c.MANUAL_SWITCH_FEEDBACK,null,'busy is not shown as "switch refused"');assert(f.notes.length===1);assert(f.notes[0].includes(ru?'операция уже выполняется':'an operation is already running'),'notice names the running operation: '+f.notes[0]);assert(!/Sending|Отправка/.test(f.notes[0]),'our own refused request is not described as the running operation');}));
  }
}
// Generated page: one heartbeat drives every timer; the Auto ring has no private interval.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const generated=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
assert(/var homeFreshTimer=window\.setInterval\(function\(\)\{[\s\S]*?uiTimerTick\(\);[\s\S]*?\},1000\);/.test(generated),'the page heartbeat refreshes the shared timer');
assert(!generated.includes('setInterval(autoCountdownTick'),'no second timer');
assert(generated.includes("UI_RECOVERY_CODES.indexOf(failureInfo)>=0?bi('Recovery needed','Нужно восстановление'):bi('Auto did not start'"),'a held recovery failure is not announced as a failed Start');
assert(generated.includes("var head=['Channel','Status','Proto'"),'Design C server table: Channel, then Status, then other fields');
for(const token of ['function uiTransitionModel(','function uiRecoveryModel(','function uiOperationTimerText(','SWITCH-RESULT-UNCONFIRMED'])assert(generated.includes(token),'generated page ships '+token);
Promise.all(tasks).then(()=>console.log('PASS: incident recovery on every surface, live transition without kernel proof, real deadlines, checking/overdue, connection wording, reload, duplicate request, one shared timer'),e=>{console.error(e);process.exitCode=1;});
