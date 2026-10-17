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
