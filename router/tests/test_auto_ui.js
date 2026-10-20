const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={bi:(en)=>en};vm.createContext(context);
vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),context);
vm.runInContext(fs.readFileSync('router/auto_panel.inc.js','utf8'),context);
const model=(ns,intent={})=>context.autoControlModel({native_failover:ns,auto_control:intent,time:1000},1000);
assert.equal(model({state:'OBSERVING',certified:true,time:999}).on,true);
assert.equal(model({state:'OBSERVING',certified:false,time:999}).on,false);
assert.equal(model({state:'COMMITTED',time:900}).on,false);
assert.equal(model({state:'COMMITTED',time:1100}).on,false);
assert.equal(model({state:'WAIT-CLIENT',time:999}).stop,true);
assert.equal(model({state:'STOPPED-ON-RESERVE',time:999,original_restored:false}).returned,false);
assert.equal(model({state:'STOPPED',time:999,original_restored:true}).returned,true);
assert.equal(model({state:'STOPPED',time:999,original_restored:false}).returned,false);
assert.equal(model({state:'STOPPED',time:999},{requested:'on',requested_at:1000}).color,'pending');
assert.equal(model({state:'STOPPED',time:999},{requested:'on',requested_at:1000}).stop,true);
assert.equal(context.autoControlModel({native_failover:{state:'COMMITTED',time:999},time:800},1000).on,false);
assert.equal(context.autoControlModel({native_failover:{state:'COMMITTED',time:999},time:999,rpc_error:'RPC-UNAVAILABLE'},1000).on,false);
assert.equal(model({state:'DEGRADED-ON-RESERVE',time:999}).color,'error');
assert.equal(model({state:'DEGRADED-ON-RESERVE',time:999}).stop,true);
assert.equal(model({state:'DEGRADED-ON-RESERVE',time:800}).stop,true);
console.log('PASS: 15 UI state/confirmation invariants');

for(const value of [0,'0',' 0 ','',null,false,-1,'-1','invalid','2026-10-16'])assert.equal(context.autoWindowDeadline({}, {native_until:value}),0);
assert.equal(context.autoWindowDeadline({until:0},{native_until:'0'}),0);
assert.equal(context.autoWindowDeadline({until:1792170000},{native_until:'0'}),1792170000);
assert.equal(context.autoWindowDeadline({}, {native_until:'2026-10-16T21:00:00+02:00'}),Date.parse('2026-10-16T19:00:00Z')/1000);
assert.equal(context.autoWindowDeadline({}, {native_until:'1792170000'}),1792170000);
console.log('PASS: cleared/invalid deadline never becomes a phantom year-2000 window');

for(const value of [null,{}, {queued:'true',accepted:true},{queued:true,accepted:'true'},{queued:false,accepted:true}])assert.equal(context.autoRequestAcknowledged(value,false),false);
assert.equal(context.autoRequestAcknowledged({queued:true,accepted:true},false),true);
assert.equal(context.autoRequestAcknowledged({queued:true},true),true);
assert.equal(context.autoRequestAcknowledged({queued:true,accepted:false},true),false);
console.log('PASS: typed start/stop acknowledgement; unknown payload never claims queued');

const good={interface:'vpn0',time:999,dns_ok:true,https_success:2},bad={...good,code:'DNS-001'};
const path=(state,source=bad,target=good,extra={})=>context.autoPathModel({time:1000,native_failover:{state,time:999,certified:true},...extra},source,target,1000);
for(const state of ['DISABLED','STOPPED','EXPIRED','ROLLED-BACK']){assert.equal(path(state).source,'neutral');assert.equal(path(state).target,'neutral');assert.equal(path(state).moving,false);}
assert.equal(path('APPLYING').moving,true);assert.equal(path('APPLYING').target,'checking');assert.equal(path('APPLYING').selected,null);
assert.equal(path('COMMITTED').source,'failed');assert.equal(path('COMMITTED').target,'healthy');assert.equal(path('COMMITTED').selected,'target');assert.equal(path('COMMITTED').moving,false);
assert.equal(path('COMMITTED',good,good).source,'ready'); // a healthy former primary must not be fabricated as failed
assert.equal(path('COMMITTED',bad,{...good,time:800}).target,'neutral');
assert.equal(path('RESTORING').direction,'back');
assert.equal(path('COMMITTED',bad,good,{rpc_error:'RPC-FAILED'}).direction,'none');
assert.equal(path('COMMITTED',bad,good,{auto_control:{requested_at:1000}}).moving,false);
console.log('PASS: failover path health, stale/off neutrality, confirmed selection and bidirectional transition');

assert.equal(path('OBSERVING',good,good).source,'healthy');
assert.equal(path('OBSERVING',good,good).target,'ready');
assert.equal(path('RESTORING',good,good).source,'checking');
assert.equal(path('RESTORING',good,good).target,'ready');
assert.equal(path('DEGRADED-ON-RESERVE',good,bad).target,'failed');
assert.equal(path('DEGRADED-ON-RESERVE',good,bad).source,'ready');
for(const state of ['OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','ARMED','APPLYING','WAIT-CLIENT','RESTORING','STOPPED']){
 for(const a of [good,bad,{...good,time:800},{...good,code:'CHECK-001'},{...good,interface:null}]){
  for(const b of [good,bad,{...good,time:800},{...good,code:'CHECK-001'},{...good,interface:null}]){
   const p=path(state,a,b);assert([p.source,p.target].filter(x=>x==='healthy').length<=1);
   if(p.source==='healthy')assert.equal(p.selected,'source');
   if(p.target==='healthy')assert.equal(p.selected,'target');
  }
 }
}
console.log('PASS: 200 path combinations, at most one green confirmed traffic path; healthy standby is not a failure');

// Every pre-start blocker the router can publish must have a plain, bilingual explanation.
{
  const src=fs.readFileSync('router/files/usr/lib/homensai-vpn/native_switch.py','utf8');
  const auto=fs.readFileSync('router/files/usr/lib/homensai-vpn/auto_control.py','utf8');
  const slice=(text,a,b)=>text.slice(text.indexOf(a),text.indexOf(b));
  const area=slice(src,'def choose(','def trace(')+slice(src,'    def diagnostic(','    def order(')+slice(auto,'def readiness(','def effective_intent(');
  const codes=new Set([...area.matchAll(/(?:Refused\(|append\()'([A-Z0-9-]+)'/g)].map(m=>m[1]));
  assert(codes.size>=20,'extracted '+codes.size+' codes');
  for(const code of codes){
    const text=context.autoBlockerText(code);
    assert(typeof text==='string'&&text.length>20&&!/Unrecognised/.test(text),'no plain explanation for '+code);
    assert(context.AUTO_BLOCKERS[code].length===2&&/[А-Яа-я]/.test(context.AUTO_BLOCKERS[code][1]),'no Russian text for '+code);
  }
  assert(/Unrecognised/.test(context.autoBlockerText('NOT-A-CODE')));
  assert(/Unrecognised/.test(context.autoBlockerText('constructor')),'prototype keys are not codes');
  console.log('PASS: '+codes.size+' controller blocker codes explained in EN and RU');
}

// Readiness checklist: ordered, never claims ready without a fresh certified controller.
{
  const now=1000,fresh={time:now-1};
  const good={id:'a',interface:'v1',time:now-1,dns_ok:true,https_success:2},good2={...good,id:'b',interface:'v2'};
  const settings={setup_complete:true,plan_source:'a',plan_target:'b',native_session_loss:true};
  const make=(status,inv)=>context.autoReadiness({time:now-1,profiles:[good,good2],...status},{settings:{...settings,...(inv||{})}},now);
  let r=make({native_failover:{...fresh,state:'OBSERVING',certified:true}});
  assert.equal(r.ready,true);assert.equal(r.next,null);
  r=make({native_failover:{...fresh,state:'DISABLED',blockers:[]}});
  assert.equal(r.ready,false);assert.equal(r.next.key,'trial');
  r=make({native_failover:{...fresh,state:'DISABLED',blockers:['HARDWARE-ACCELERATOR-UNVERIFIED','LAN-TRIAL-REQUIRED']}});
  assert.equal(r.next.key,'router');assert.deepEqual(r.steps[3].codes,['HARDWARE-ACCELERATOR-UNVERIFIED']);
  r=make({native_failover:{...fresh,state:'DISABLED'}},{native_session_loss:false});assert.equal(r.next.key,'session');
  r=make({native_failover:{...fresh,state:'DISABLED'}},{plan_target:'a'});assert.equal(r.next.key,'profiles');
  r=make({native_failover:{...fresh,state:'DISABLED'},profiles:[{...good,code:'DNS-001'},good2]});assert.equal(r.next.key,'profiles');
  r=make({time:now-500,native_failover:{...fresh,state:'OBSERVING',certified:true}});assert.equal(r.next.key,'monitor');assert.equal(r.ready,false);
  r=make({native_failover:{time:now-200,state:'OBSERVING',certified:true}});assert.equal(r.steps[4].done,false);
  r=make({rpc_error:'RPC-UNAVAILABLE',native_failover:{...fresh,state:'OBSERVING',certified:true}});assert.equal(r.ready,false);
  console.log('PASS: Auto readiness checklist order and fail-closed freshness');
}

// alpha5: operator return, release-on-external-change and exit address copy.
{
  for(const code of ['RETURN-NOT-APPLICABLE','SOURCE-NOT-HEALTHY','JOURNAL-UNVERIFIED','EXTERNAL-POLICY-CHANGE','EXTERNAL-POLICY-CHANGE-RELEASED','ROLLBACK-UNVERIFIED','OPERATOR-RETURN','PRIMARY-RECOVERED']){
    assert(!/Unrecognised/.test(context.autoBlockerText(code)),code);assert(/[А-Яа-я]/.test(context.AUTO_BLOCKERS[code][1]),code);
  }
  // No remaining text may tell the owner that Auto keeps the LAN blocked after an outside change.
  assert(!/LAN traffic is held|трафик LAN удерживается/.test(JSON.stringify(context.AUTO_BLOCKERS['EXTERNAL-POLICY-CHANGE-RELEASED'])));
  const src=fs.readFileSync('router/auto_panel.inc.js','utf8');
  assert(src.includes("method:'native_return'"));assert(src.includes('p.exit_ip'));
  // Return to the primary is offered on the Auto card whenever traffic is on the reserve, including a committed reserve.
  assert(src.includes("STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE','COMMITTED'].indexOf(ns.state)>=0"));
  // Two-state lamp and two-colour nodes: green = automatic switching works / carries traffic and works.
  assert(context.autoWorking({key:'ok'})&&context.autoWorking({key:'reserve'})&&context.autoWorking({key:'switching'}));
  for(const key of ['off','problem','unknown',undefined])assert(!context.autoWorking({key}),String(key));
  assert(src.includes("hv-auto-lit-on")&&src.includes("hv-auto-lit-off"),'the round button is green when Auto works, red when it does not');
  assert(src.includes("hv-node-'+(tone.green?'green':'red')")&&src.includes("'Press to turn Auto off'"));
  console.log('PASS: operator return, outside-change copy and exit address are wired');
}

// Traffic light: the lamp, not the button, carries the status.
{
  const now=1000,light=(ns,intent={},extra={})=>context.autoLightModel({time:now-1,native_failover:{time:now-1,...ns},auto_control:intent,...extra},{settings:{}},now);
  assert.equal(light({state:'OBSERVING',certified:true}).lamp,'green');
  assert.equal(light({state:'OBSERVING',certified:false}).key,'off');
  for(const state of ['ARMED','APPLYING','WAIT-CLIENT','RESTORING'])assert.equal(light({state}).lamp,'yellow',state);
  assert.equal(light({state:'STOPPED'},{requested:'on',requested_at:now}).lamp,'yellow');
  assert.equal(light({state:'COMMITTED'}).lamp,'orange');
  for(const state of ['DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE','TRIAL-REQUIRED'])assert.equal(light({state}).lamp,'red',state);
  assert.equal(light({state:'BLOCKED',blockers:['HARDWARE-ACCELERATOR-UNVERIFIED']},{requested:'on'}).lamp,'red');
  assert.equal(light({state:'BLOCKED',blockers:['HARDWARE-ACCELERATOR-UNVERIFIED']},{requested:'off'}).lamp,null);
  for(const requested of ['on','off']){
    const pending=light({state:'BLOCKED',blockers:['GUARD-RELEASE-UNCONFIRMED']},{requested});
    assert.equal(pending.lamp,'red');assert(/not confirmed/.test(pending.title));
    assert.equal(light({state:'RELEASE-PENDING'},{requested}).lamp,'red');
  }
  for(const state of ['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'])assert.equal(light({state}).lamp,null,state);
  // Stale or missing status is never green; the light says there is no data.
  assert.equal(context.autoLightModel({time:now-500,native_failover:{time:now-1,state:'OBSERVING',certified:true}},{},now).key,'unknown');
  assert.equal(context.autoLightModel({time:now-1,native_failover:{time:now-200,state:'OBSERVING',certified:true}},{},now).lamp,null);
  assert.equal(context.autoLightModel({time:now-1,rpc_error:'RPC-UNAVAILABLE',native_failover:{time:now-1,state:'OBSERVING',certified:true}},{},now).key,'unknown');
  // Exhaustive: one lamp at most, text always present, green only for a fresh certified watch.
  const states=['DISABLED','STOPPED','EXPIRED','ROLLED-BACK','OBSERVING','TRIAL-REQUIRED','ARMED','APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE','BLOCKED','UNKNOWN-STATE',undefined];
  let combos=0;
  for(const state of states)for(const certified of [true,false,undefined])for(const requested of ['on','off',undefined])for(const age of [1,50,200])for(const rpc of [null,'RPC-UNAVAILABLE']){
    const l=context.autoLightModel({time:now-1,rpc_error:rpc,native_failover:{state,certified,time:now-age},auto_control:{requested,requested_at:requested==='on'?now:0}},{settings:{}},now);combos++;
    assert(['off','unknown','ok','switching','reserve','problem'].includes(l.key));
    assert(l.lamp===null||['green','yellow','orange','red'].includes(l.lamp));
    assert(typeof l.title==='string'&&l.title.length>3&&typeof l.hint==='string'&&l.hint.length>10);
    if(l.lamp==='green')assert(state==='OBSERVING'&&certified===true&&age<=30&&!rpc);
  }
  assert(combos>=800);
  // The button carries no status colour class any more.
  const src=fs.readFileSync('router/auto_panel.inc.js','utf8');
  assert(src.includes("'hv-auto-power hv-auto-neutral'")&&!src.includes("'hv-auto-power hv-auto-'+model.color"));
  console.log('PASS: traffic light maps '+combos+' controller combinations to one lamp; button is neutral');
}
