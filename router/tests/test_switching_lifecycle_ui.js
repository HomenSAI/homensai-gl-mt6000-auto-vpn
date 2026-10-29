// Regressions for the independently reproduced switching races and contradictory displays.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N {
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children||[]).flat().filter(x=>x!=null);this.disabled=this.attrs.disabled!=null;this.style={setProperty(){}};this.classList={contains:k=>String(this.attrs.class||'').split(' ').includes(k),toggle:(k,on)=>{let words=String(this.attrs.class||'').split(' ').filter(x=>x!==k);if(on)words.push(k);this.attrs.class=words.join(' ');},add:k=>this.classList.toggle(k,true)};}
  setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}appendChild(v){this.children.push(v);return v;}get firstChild(){return this.children[0];}removeChild(v){this.children.splice(this.children.indexOf(v),1);}
  all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}text(){return (this.textContent||'')+this.children.map(x=>x instanceof N?x.text():String(x)).join(' ');}
  querySelector(selector){return this.all().find(n=>selector[0]==='.'&&n.classList.contains(selector.slice(1)))||null;}
}
function fixture(language='en'){
  const clock={wall:1000000,tick:1000000},calls=[],replies=[],timers=new Map(),store={},notes=[];let timerId=0;
  const c={console,Promise,E:(...args)=>new N(...args),bi:(en,ru)=>language==='ru'?ru:en,locale:language,
    Date:class extends Date {static now(){return clock.wall;}},performance:{now:()=>clock.tick},
    window:{localStorage:{getItem:k=>store[k]||null,setItem:(k,v)=>store[k]=v},location:{reload(){}}},
    setInterval:fn=>{const id=++timerId;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id),
    ui:{addNotification:(_,n)=>notes.push(n.text())},errorCodeLink:code=>new N('code',{},code),
    rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise((resolve,reject)=>replies.push({resolve,reject}));}},
    vendorDisplayMember:(s,i,role)=>s.profiles.find(p=>p.id===i.settings['plan_'+role]),countryName:()=>null,protocolLabel:p=>p.protocol,endpointText:()=>'',identityModel:()=>({agent:'test'})};
  vm.createContext(c);for(const name of ['ui_logic','auto_panel','manual_panel','sidebar_status','simple_home_policy','simple_home_panel','monitor_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  const inventory={settings:{enabled:true,plan_source:'a',plan_target:'b'}};
  const status=()=>({time:1000,profiles:['a','b'].map((id,i)=>({id,interface:i?'ovpnclient1':'wgclient1',protocol:i?'openvpn':'wireguard',time:1000,dns_ok:true,https_success:2})),
    native_failover:{time:1000,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,source:'a',target:'b'},
    auto_control:{requested:'on',requested_at:990,pair_phase:'RUNNING',control_revision:'b'.repeat(32)},
    channel_path:{time:1000,checked_at:1000,valid_for:15,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',kernel_policy_verified:true,confirmed:true,active_profile_id:'a',source_profile_id:'a',target_profile_id:'b',transitioning:false},
    manual_switch_control:{time:1000,mode:'continuous-pair',control_revision:'b'.repeat(32),available:true,reserve:{allowed:true,blockers:[]},primary:{allowed:true,blockers:[]}}});
  return {c,clock,calls,replies,timers,store,notes,inventory,status};
}
const choice=(node,direction)=>node.all().find(n=>n.attrs['data-manual-direction']===direction);
async function main(){
  for(const language of ['en','ru']){
    const f=fixture(language),{c,status,inventory,calls,replies}=f,s=status(),before=JSON.stringify(s);let sidebar;
    c.UI_OPERATION_REFRESH=()=>{sidebar=new N('div');c.fillSideStatus(sidebar,s,inventory);};
    const manual=c.renderManualSwitch(s,inventory),primary=choice(manual,'primary'),reserve=choice(manual,'reserve');
    const pending=reserve.attrs.click();assert(primary.attrs.class.includes('hv-manual-grey'),'a click cannot turn a healthy existing channel red');
    assert(sidebar.all().filter(n=>(n.attrs.class||'').includes('hv-auto-pill-knob')).slice(2).every(n=>n.attrs.class.includes('hv-lamp-unknown')),'sidebar and manual cards enter the same pending presentation immediately');
    assert.equal(c.selectedProfile(s,1000),'a','pending presentation never forges kernel selection');assert.equal(JSON.stringify(s),before);
    replies.shift().resolve({accepted:true,queued:true,completed:false,request_id:'c'.repeat(32)});await pending;
    assert(c.MANUAL_SWITCH_PENDING);const stalePage=c.renderManualSwitch(s,inventory);assert(choice(stalePage,'reserve').disabled);choice(stalePage,'reserve').attrs.click();assert.equal(calls.length,1,'same pre-click snapshot cannot dispatch a duplicate after ACK');
    const terminal={...s,manual_switch:{state:'COMPLETED',completed:true,request_id:'d'.repeat(32),direction:'reserve',requested_at:1000,updated_at:1000}};
    assert(c.manualControlModel(terminal,1000).busy,'an unrelated completed request does not complete ours');
    terminal.manual_switch.request_id='c'.repeat(32);terminal.manual_switch.completed=false;assert(c.manualControlModel(terminal,1000).busy,'malformed COMPLETED flag cannot complete a request');terminal.manual_switch.completed=true;assert(!c.manualControlModel(terminal,1000).busy);assert(!c.MANUAL_SWITCH_PENDING);
    assert.equal(c.selectedProfile(terminal,1000),'a','a terminal queue result does not override actual route proof');
    terminal.channel_path={...s.channel_path,active_profile_id:'b'};
    const complete=c.renderManualSwitch(terminal,inventory);assert(choice(complete,'reserve').attrs.class.includes('hv-manual-green'));assert(choice(complete,'primary').attrs.class.includes('hv-manual-yellow'));
    assert(!f.notes.some(n=>/queued|очередь/.test(n)),'queue acknowledgements are transient state, not lingering notifications contradicting completion');
    // Lost transport can mean a stored request: keep it unresolved until current backend evidence arrives.
    const second=c.renderManualSwitch(s,inventory);const lost=choice(second,'reserve').attrs.click();replies.shift().reject(new Error('transport'));await lost;
    assert(c.manualControlModel(s,1000).uncertain);assert(choice(c.renderManualSwitch(s,inventory),'reserve').disabled);
    const recovered={...s,manual_switch:{state:'UNCONFIRMED',completed:false,request_id:'e'.repeat(32),direction:'reserve',requested_at:1000,updated_at:1000,code:'PAIR-MANUAL-RECOVERED'}};
    assert(!c.manualControlModel(recovered,1000).busy);assert(c.manualFailureResult(recovered,1000).text().includes('PAIR-MANUAL-RECOVERED'));
    const cancelTask=choice(c.renderManualSwitch(s,inventory),'reserve').attrs.click();replies.shift().resolve({accepted:true,queued:true,completed:false,request_id:'f'.repeat(32)});await cancelTask;
    const cancelled={...s,manual_switch:{state:'CANCELLED',completed:false,request_id:'f'.repeat(32),direction:'reserve',requested_at:1000,updated_at:1000,code:'CONTROL-REVISION-STALE'}};
    assert(!c.manualControlModel(cancelled,1000).busy);assert(c.manualFailureResult(cancelled,1000).text().includes(language==='ru'?'отменено':'cancelled'));
    // Fresh kernel selection, controller operation and channel health stay separate but agree across surfaces.
    const degraded=status();degraded.native_failover.state='DEGRADED-ON-RESERVE';degraded.channel_path.active_profile_id='b';degraded.profiles[1].code='DNS-001';
    assert(!c.autoWorking(c.autoLightModel(degraded,inventory,1000)));const hm=c.simpleHomeModel(degraded,inventory,1000);assert.equal(hm.state,'error');assert.equal(hm.title,c.autoLightModel(degraded,inventory,1000).title);
    const failedSidebar=new N('div');c.fillSideStatus(failedSidebar,degraded,inventory);assert(failedSidebar.text().includes(hm.title),'sidebar reports the selected-channel failure instead of falsely saying Auto is off');
    const recovering=status();recovering.native_failover.state='DEGRADED-ON-RESERVE';recovering.channel_path.active_profile_id='b';const recoveryLight=c.autoLightModel(recovering,inventory,1000);assert.equal(recoveryLight.key,'unknown');assert(recoveryLight.hint.includes(language==='ru'?'Последняя проверка канала прошла':'latest channel check passed'),'a recovered check is not described as a current failure');
    const held=status();held.native_failover.state='COMMITTED';held.auto_control.pair_phase='HELD';held.channel_path.active_profile_id='b';const h=c.simpleHomeModel(held,inventory,1000);assert.equal(h.state,'on');assert.equal(h.enabled,true);
    const stopped=status();stopped.auto_control.requested='off';stopped.auto_control.pair_phase='STOPPED';assert(!c.autoWorking(c.autoLightModel(stopped,inventory,1000)),'an old OBSERVING phase cannot override an explicit stopped pair');
    const missing=status();missing.profiles=missing.profiles.filter(p=>p.id!=='a');assert(!c.autoWorking(c.autoLightModel(missing,inventory,1000)),'no green claim without the selected channel health');
    const home=c.renderSimpleHome(held,inventory,h,null,()=>{}),responses=home.all().find(n=>n.attrs['data-home-response']==='both');assert(responses);assert.equal(responses.all().filter(n=>n.attrs.class==='hv-channel-ping').length,2);assert(responses.text().includes('0/3'),'both absent website measurements explain coverage visibly');
    // A slow monitor is fresh for its declared cadence, while kernel and website contracts remain short.
    const slow=status();slow.time=800;slow.observation_valid_for=900;slow.profiles.forEach(p=>{p.time=800;p.observation_valid_for=900;});
    assert(c.autoControlModel(slow,1000).fresh);assert.equal(c.monitorLightModel(slow,inventory,1000,false).key,'ok');assert(slow.profiles.every(p=>c.profileHealth(p,1000).state==='healthy'));assert(c.manualControlModel(slow,1000).reserve.allowed);
    slow.channel_path.checked_at=slow.channel_path.time=984;assert.equal(c.selectedProfile(slow,1000),null,'cadence cannot extend 15-second kernel proof');
    slow.native_failover.time=1000-31-(c.UI_DISPLAY_GRACE||0);assert(!c.autoControlModel(slow,1000).fresh,'cadence cannot extend the 30-second controller heartbeat (+display grace)');
    for(const value of [0,901,Infinity,'900'])assert.equal(c.observationValidFor({observation_valid_for:value}),90+(c.UI_DISPLAY_GRACE||0));
  }
  console.log('PASS: queued/unknown/cancelled/recovered manual lifecycle, consistent immediate lamps, typed terminal correlation, truthful channel state and cadence EN/RU');
  for(const language of ['en','ru']){
    const {c,status,inventory,calls,replies}=fixture(language),held=status();
    held.manual_switch_control.hold='source';held.manual_switch_control.resume={allowed:true,blockers:[]};
    const label=language==='ru'?'Возобновить Auto':'Resume Auto',view=c.renderManualSwitch(held,inventory),resume=choice(view,'resume');
    assert(resume,'a backend-authorized manual hold has a visible Resume Auto command');assert.equal(resume.text(),label);assert(!resume.disabled);
    const light=c.autoLightModel(held,inventory,1000);assert(!c.autoWorking(light),'manual hold cannot promise automatic switching');
    const home=c.simpleHomeModel(held,inventory,1000);assert.equal(home.title,light.title);assert.notEqual(home.state,'on');
    const sidebar=new N('div');c.fillSideStatus(sidebar,held,inventory);assert(sidebar.text().includes(light.title));
    for(const edit of [x=>delete x.manual_switch_control.hold,x=>x.manual_switch_control.hold='invalid',x=>x.manual_switch_control.mode='legacy']){
      const hidden=JSON.parse(JSON.stringify(held));edit(hidden);assert(!choice(c.renderManualSwitch(hidden,inventory),'resume'));
    }
    for(const edit of [x=>x.rpc_error='RPC-UNAVAILABLE',x=>x.manual_switch_control.time=900,x=>x.manual_switch_control.resume.allowed=false]){
      const blocked=JSON.parse(JSON.stringify(held));edit(blocked);const button=choice(c.renderManualSwitch(blocked,inventory),'resume');assert(button.disabled);button.attrs.click();assert.equal(calls.length,0);
    }
    const noPath=JSON.parse(JSON.stringify(held));noPath.channel_path.confirmed=false;noPath.profiles[1].code='DNS-001';assert(!choice(c.renderManualSwitch(noPath,inventory),'resume').disabled,'Resume clears the hold under backend authorization without promising a route or requiring reserve health');
    const task=resume.attrs.click();assert.equal(calls.length,1);assert.equal(calls[0].method,'pair_manual');assert.deepEqual(calls[0].args,['resume','b'.repeat(32),'manual']);
    replies.shift().resolve({accepted:true,queued:true,completed:false,request_id:'a'.repeat(32)});await task;
    const queued=c.renderManualSwitch(held,inventory);assert(choice(queued,'resume').disabled);choice(queued,'resume').attrs.click();assert.equal(calls.length,1);assert.equal(c.selectedProfile(held,1000),'a','Resume ACK never invents a route change');
    const done=JSON.parse(JSON.stringify(held));delete done.manual_switch_control.hold;done.manual_switch={state:'COMPLETED',completed:true,request_id:'a'.repeat(32),direction:'resume',requested_at:1000,updated_at:1000};
    assert(!c.manualControlModel(done,1000).busy);assert(!choice(c.renderManualSwitch(done,inventory),'resume'));assert(c.autoWorking(c.autoLightModel(done,inventory,1000)));
    const lost=choice(c.renderManualSwitch(held,inventory),'resume').attrs.click();replies.shift().reject(new Error('lost Resume acknowledgement'));await lost;
    assert(c.manualControlModel(held,1000).uncertain);assert(choice(c.renderManualSwitch(held,inventory),'resume').disabled);
  }
  console.log('PASS: Resume Auto renders only for manual hold, obeys backend gates, shares pending/correlation and never changes a route optimistically EN/RU');
  // Every status-call consumer shares dispatch provenance. Clock values are never used to order replies.
  {
    const {c}=fixture(),pending=[];const raw=()=>new Promise(resolve=>pending.push(resolve));let current;
    const p1=c.uiStatusRequest(raw),p2=c.uiStatusRequest(raw);await Promise.resolve();
    pending[1]({server_time:2000,time:1000,channel_path:{active_profile_id:'b'}});current=await p2;
    pending[0]({server_time:3000,time:1000,channel_path:{active_profile_id:'a'}});const old=await p1;
    assert.strictEqual(c.uiNewestStatus(current,old),current,'older RPC loses even with greater wall time');
    const reset=await c.uiStatusRequest(()=>({server_time:100,time:90,channel_path:{active_profile_id:'a'}}));assert.strictEqual(c.uiNewestStatus(current,reset),reset,'newer RPC wins after NTP/reboot backwards clock');current=reset;
    const sameTime=await c.uiStatusRequest(()=>({server_time:100,time:90,manual_switch:{state:'COMPLETED'}}));assert.strictEqual(c.uiNewestStatus(current,sameTime),sameTime,'new completion wins with identical monitor/server time');
    assert.strictEqual(c.uiNewestStatus(sameTime,c.uiStatusFailure(old,c.uiStatusOrder(p1))),sameTime,'timeout of an older RPC cannot mark a newer success as disconnected');
  }
  console.log('PASS: dispatch sequence fences stale callbacks, errors, same-time results and backwards router clocks');
  for(const scenario of [{delay:100},{delay:24000},{delay:24000,zeroTick:true},{delay:24000,wallBack:true},{delay:24000,routerBack:true}]){
    const {c,clock,status}=fixture();if(scenario.zeroTick)clock.tick=0;
    const previous=await c.uiStatusRequest(()=>({server_time:2000}));c.statusNow(previous);
    const stamp=scenario.routerBack?100:1000,s=status();s.server_time=s.time=s.channel_path.time=s.channel_path.checked_at=stamp;s.native_failover.time=stamp-10;s.observation_valid_for=900;
    s.profiles.forEach((p,i)=>{p.time=stamp;p.observation_valid_for=900;p.vendor_state='SETTLED';p.vendor_generation='a'.repeat(32);p.vendor_tunnel_id=p.protocol+':'+p.interface;
      p.website_response={metric:c.WEBSITE_METRIC,target_set:c.WEBSITE_TARGET_SET,state:'ok',avg_ms:100*(i+1),successes:3,attempted:3,time:stamp-25,valid_for:45,generation:p.vendor_generation,interface:p.interface,vendor_tunnel_id:p.vendor_tunnel_id,results:Object.keys(c.WEBSITE_URLS).map(id=>({id,url:c.WEBSITE_URLS[id],state:'ok',code:null,elapsed_ms:100*(i+1)}))};});
    const original=JSON.stringify(s);let resolve;const pending=c.uiStatusRequest(()=>new Promise(done=>{resolve=done}));await Promise.resolve();
    clock.tick+=scenario.delay;clock.wall+=scenario.wallBack?-600000:scenario.delay;resolve(s);const received=await pending,now=c.statusNow(received),slow=scenario.delay>15000;
    assert(Math.abs(now-stamp-scenario.delay/1000)<1e-9,'status evidence ages during RPC transport, including a zero monotonic tick and backwards clocks');
    assert.strictEqual(c.uiNewestStatus(previous,received),received);assert.equal(c.selectedProfile(received,now),slow?null:'a');assert.equal(c.autoControlModel(received,now).fresh,10+scenario.delay/1000<=30+(c.UI_DISPLAY_GRACE||0),'controller heartbeat ages in transit; display grace tolerates a slow status call');
    received.profiles.forEach((p,i)=>assert.equal(c.channelPingModel(p,received,now).rtt_ms,slow?null:100*(i+1),'both 45-second website results expire while in transit'));
    assert(c.observationFresh(received,now));assert.equal(JSON.stringify(received),original,'transport metadata does not rewrite router evidence');
  }
  {
    const {c,clock,status}=fixture(),untracked={...status(),server_time:1000};
    assert.equal(c.statusNow(untracked),1000,'an untracked initial/fixture snapshot retains the receipt-time fallback');clock.tick+=5000;assert.equal(c.statusNow(untracked),1005);
  }
  console.log('PASS: delayed replies consume kernel/controller/website TTLs, fast replies and untracked frames remain usable');
  for(const terminalTime of [100,1000]){
    const {c,status,inventory,replies}=fixture(),initial=status();initial.server_time=1000;
    const task=choice(c.renderManualSwitch(initial,inventory),'reserve').attrs.click();
    replies.shift().resolve({accepted:true,queued:true,completed:false,request_id:'c'.repeat(32)});await task;
    const reset=status();reset.server_time=reset.time=reset.native_failover.time=reset.manual_switch_control.time=reset.channel_path.time=reset.channel_path.checked_at=100;
    reset.auto_control.requested_at=90;reset.profiles.forEach(p=>{p.time=100;});reset.channel_path.active_profile_id='b';
    reset.manual_switch={request_id:'d'.repeat(32),direction:'reserve',state:'COMPLETED',completed:true,requested_at:1000,updated_at:100};
    assert(c.manualControlModel(await c.uiStatusRequest(()=>reset),100).busy,'clock correction cannot make another request complete ours');
    for(const updated_at of [NaN,-1,Infinity]){
      const malformed={...reset,manual_switch:{...reset.manual_switch,request_id:'c'.repeat(32),updated_at}};
      assert(c.manualControlModel(await c.uiStatusRequest(()=>malformed),100).busy,'matching identity does not excuse a malformed terminal record');
    }
    const complete={...reset,manual_switch:{...reset.manual_switch,request_id:'c'.repeat(32),updated_at:terminalTime}};
    assert(!c.manualControlModel(await c.uiStatusRequest(()=>complete),100).busy,'the exact terminal request ID remains authoritative after the router clock moves backwards');
    assert(!c.MANUAL_SWITCH_PENDING);assert.equal(c.selectedProfile(complete,100),'b');
  }
  {
    const {c,status,inventory,replies}=fixture(),initial=status();initial.server_time=1000;
    const task=choice(c.renderManualSwitch(initial,inventory),'reserve').attrs.click();replies.shift().reject(new Error('lost acknowledgement'));await task;
    const reset={...initial,time:100,server_time:100,manual_switch:{request_id:'e'.repeat(32),direction:'reserve',state:'COMPLETED',completed:true,requested_at:100,updated_at:100}};
    assert(c.manualOperationModel(reset,100).busy,'without an acknowledged ID the clock correction cannot assign an unrelated result');
    assert.equal(c.MANUAL_SWITCH_OPERATION.request_id,null);
  }
  console.log('PASS: matching manual terminal survives backwards router clock without accepting another request');
  for(const state of ['CANCELLED','REFUSED','UNCONFIRMED']){
    const {c,clock,status,inventory}=fixture();clock.tick=0;
    const row={state,completed:false,request_id:'c'.repeat(32),direction:'reserve',requested_at:1000,updated_at:1000,code:'CONTROL-REVISION-STALE'},stopped={...status(),time:100,server_time:100,manual_switch:row};
    assert(c.manualFailureResult(stopped,100).text().includes(row.code),'a cold tab must show a valid Stop/recovery outcome despite backwards router time');
    for(const updated_at of [NaN,Infinity,-1,'1000'])assert.equal(c.manualFailureResult({...stopped,manual_switch:{...row,updated_at}},100),null,'a malformed timestamp cannot gain a clock-skew allowance');
    for(const request_id of [null,'invalid',''])assert.equal(c.manualFailureResult({...stopped,manual_switch:{...row,request_id}},100),null,'clock-skew allowance needs a real request ID');
    assert.equal(c.manualFailureResult({...stopped,manual_switch:{...row,completed:true}},100),null);
    clock.tick=299999;assert(c.manualFailureResult(stopped,399));const beforeExpiry=c.uiStateSignature(stopped,inventory,399);clock.tick=300001;assert.equal(c.manualFailureResult(stopped,400),null,'clock-skew feedback expires after 300 monotonic seconds');
    assert.notEqual(c.uiStateSignature(stopped,inventory,400),beforeExpiry,'the presentation heartbeat removes expired feedback without waiting for another RPC');
    assert.equal(c.manualFailureResult(stopped,1000),null,'correcting the router clock again cannot revive expired feedback');
    const other={...row,request_id:'d'.repeat(32)};assert(c.manualFailureResult({...stopped,manual_switch:other},100));assert.equal(c.manualFailureResult(stopped,100),null,'another request cannot renew the old result window');
    c.MANUAL_SWITCH_OPERATION={direction:'reserve',request_id:'e'.repeat(32),baseline:1000,tick:clock.tick,t0:clock.wall};c.MANUAL_SWITCH_PENDING=true;
    assert(c.manualControlModel(stopped,100).busy,'another request terminal never completes the local request');assert(!c.renderManualSwitch(stopped,inventory).all().some(n=>n.attrs['data-manual-diagnostic']==='last-request'));
  }
  {
    const {c,clock,status}=fixture(),s={...status(),manual_switch:{state:'REFUSED',completed:false,request_id:'f'.repeat(32),updated_at:1000,code:'SOURCE-NOT-HEALTHY'}};
    assert(c.manualFailureResult(s,1000));clock.tick+=299999;assert(c.manualFailureResult(s,100));clock.tick+=2;assert.equal(c.manualFailureResult(s,100),null,'a later clock step retains the first-observation deadline');
    assert(c.manualFailureResult({...s,manual_switch:{...s.manual_switch,request_id:null,updated_at:100}},100),'a fresh local refusal without an accepted request ID retains its normal display');
  }
  console.log('PASS: Stop/recovery terminal feedback survives clock skew for a bounded monotonic window, including a cold tab');
  {
    const {c,status}=fixture(),saved={state:'REFUSED',completed:false,request_id:'c'.repeat(32),updated_at:1000,code:'SOURCE-NOT-HEALTHY'};c.MANUAL_SWITCH_FEEDBACK=saved;
    let oldReply;const oldRequest=c.uiStatusRequest(()=>new Promise(resolve=>{oldReply=resolve}));await Promise.resolve();
    const current=await c.uiStatusRequest(()=>({...status(),time:100,server_time:100,manual_switch:{state:'COMPLETED',completed:true,request_id:'d'.repeat(32),updated_at:100}}));
    assert.equal(c.manualFailureResult(current,100),null,'a completed new request from another tab supersedes an old correlated refusal despite backwards time');
    oldReply({...status(),server_time:1000,manual_switch:saved});const stale=await oldRequest;assert.strictEqual(c.uiNewestStatus(current,stale),current);
    assert.equal(c.manualFailureResult(c.uiNewestStatus(current,stale),100),null,'a late old RPC cannot resurrect the superseded refusal');
    const refused={...current,manual_switch:{...current.manual_switch,state:'REFUSED',completed:false,code:'PAIR-MANUAL-TARGET-UNHEALTHY'}};
    assert(c.manualFailureResult(refused,100).text().includes('PAIR-MANUAL-TARGET-UNHEALTHY'),'the current backend refusal takes precedence over the old request');
    for(const request_id of [null,'invalid',saved.request_id])assert(c.manualFailureResult({...current,manual_switch:{...current.manual_switch,request_id}},100).text().includes(saved.code),'missing, invalid or unchanged identity cannot displace known feedback using a backwards timestamp');
    c.MANUAL_SWITCH_FEEDBACK={...saved,request_id:null};assert(c.manualFailureResult(current,1000).text().includes(saved.code),'a fresh local refusal without an accepted request ID remains visible');
  }
  {
    const {c,status}=fixture(),reset=status();reset.time=reset.server_time=reset.native_failover.time=100;reset.auto_control.requested_at=990;
    assert(!c.autoControlModel(reset,100).awaiting,'correlated RUNNING pair survives a backwards clock');assert.equal(c.autoCommandOperation(reset,100),null);
    reset.auto_control.pair_phase='HELD';assert.equal(c.autoCommandOperation(reset,100),null);
    reset.auto_control.requested='off';reset.auto_control.pair_phase='STOPPED';assert(!c.autoControlModel(reset,100).awaiting);assert.equal(c.autoCommandOperation(reset,100),null);
    reset.auto_control.requested='on';
    reset.auto_control.pair_phase='STARTING';assert(c.autoControlModel(reset,100).awaiting);assert.equal(c.autoCommandOperation(reset,100),'starting');
    reset.auto_control.pair_phase='RUNNING';assert(!c.autoControlModel(reset,131+(c.UI_DISPLAY_GRACE||0)).fresh);
    reset.native_failover.mode='legacy';reset.native_failover.proof_scope='lan';delete reset.channel_path;assert(c.autoControlModel(reset,100).awaiting,'legacy timestamp validation is unchanged');
  }
  for(const observed of [false,true]){
    const {c,clock,status,inventory,store}=fixture(),current=status();current.server_time=1000;
    c.autoCommandPending={sequence:1,stop:false,baseline:observed?980:990,acknowledged:true,t0:clock.wall,tick:clock.tick};
    if(observed)current.auto_control.pair_phase='STARTING';
    c.autoCountdownBegin('start');clock.tick+=121000;
    assert.equal(c.autoCommandOperation(current,1000),'unconfirmed','timeout cannot treat the unchanged pre-command terminal as completion');
    if(observed){current.auto_control.pair_phase='RUNNING';assert.equal(c.autoCommandOperation(current,1000),null,'an observed newer intent may finish with the same intent timestamp');}
    else{const power=c.renderAutoPowerControl(current,inventory);assert(!power.button.disabled);assert.equal(power.button.attrs['data-auto-operation'],'unconfirmed');assert.equal(c.AUTO_COUNTDOWN,null);assert(!store['hv-auto-durations'],'an unresolved command never trains a successful duration');}
  }
  // Run the actual generated poll and presentation heartbeat, not a copied implementation.
  const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
  const moduleName=menu['admin/services/homensai-vpn'].action.path.split('/').pop(),generated=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+moduleName+'.js','utf8');
  {
    const {c}=fixture();let pending=[],timeouts=[],draws=[];c.document={hidden:false};c.lastGoodStatus={};c.statusCall=()=>c.uiStatusRequest(()=>new Promise(resolve=>pending.push(resolve)));c.uiRenderFailed=e=>{throw e};c.setTimeout=fn=>(timeouts.push(fn),timeouts.length);c.clearTimeout=()=>{};c.draw=s=>draws.push(s);
    const start=generated.indexOf('var hvStatusInFlight=null'),end=generated.indexOf(';UI_STATUS_REFRESH=hvStatusTick;',start);assert(start>=0&&end>start,'current generated poll contains fencing');vm.runInContext(generated.slice(start,end+1),c);
    const a=c.hvStatusTick(),b=c.hvStatusTick();assert.strictEqual(a,b,'poll and visibility refresh share one in-flight call');await Promise.resolve();assert.equal(pending.length,1);
    timeouts[0]();await a;assert.equal(draws.length,1);assert(draws[0].rpc_error);const next=c.hvStatusTick();await Promise.resolve();pending[1]({time:1000});await next;assert.equal(draws.length,2);
    pending[0]({time:9999});await Promise.resolve();await Promise.resolve();assert.equal(draws.length,2,'late response after timeout cannot paint the page');
    c.document.hidden=true;await c.hvStatusTick();assert.equal(pending.length,2,'hidden page does not poll');
  }
  {
    const f=fixture(),{c,clock,status,inventory,store}=f;const off=status();off.native_failover.state='STOPPED';off.auto_control.requested='off';off.auto_control.pair_phase='STOPPED';off.native_failover.original_restored=true;
    let view=c.renderAutoPowerControl(off,inventory);view.button.attrs.click();assert(c.AUTO_COUNTDOWN);
    c.appRoot={isConnected:true};c.homeShortcut=null;c.homeLatest=off;c.inventory=inventory;c.hybridUiState='initial';c.draw=s=>{view=c.renderAutoPowerControl(s,inventory);c.hybridUiState=c.uiStateSignature(s,inventory,c.statusNow(s));};
    const match=generated.match(/var homeFreshTimer=window\.setInterval\(function\(\)\{([\s\S]*?)\},1000\);/);assert(match,'generated page has one presentation heartbeat');
    c.window.clearInterval=()=>{};vm.runInContext('var homeFreshTimer=1;function presentationTick(){'+match[1]+'}',c);
    clock.tick+=121000;clock.wall-=600000;c.presentationTick();assert.equal(c.autoCommandPending,null);assert(c.autoCommandUnconfirmed);assert.equal(c.AUTO_COUNTDOWN,null,'unconfirmed timeout ends the estimate, never displays infinite +seconds');assert(!view.button.disabled,'operator Stop remains available after a hung Start');assert(!store['hv-auto-durations'],'an unconfirmed result is never trained as successful timing');
  }
  console.log('PASS: actual generated single-flight poll deadline, late-response fence and independent monotonic timeout heartbeat');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
