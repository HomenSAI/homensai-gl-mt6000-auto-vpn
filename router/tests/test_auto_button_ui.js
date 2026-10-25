const fs=require('fs'),vm=require('vm'),assert=require('assert');
let calls=[],replies=[];
function E(tag,attrs,children){return {tag,attrs:attrs||{},children,disabled:!!(attrs&&attrs.disabled!=null),classList:{toggle(){}},setAttribute(k,v){this.attrs[k]=v;}};}
const c={E,bi:en=>en,Date:{now:()=>1000000},ui:{addNotification(){}},window:{location:{reload(){}}},errorCodeLink:code=>code,rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise((resolve,reject)=>replies.push({resolve,reject}));}}};
vm.createContext(c);vm.runInContext(fs.readFileSync('router/auto_panel.inc.js','utf8'),c);c.autoLightModel=()=>({});c.autoWorking=()=>false;
const status=(phase,state,requested,at)=>({time:1000,native_failover:{time:Math.max(1000,at),state,mode:'continuous-pair',readiness_verified:phase==='RUNNING'},auto_control:{pair_phase:phase,requested,requested_at:at,control_revision:'a'.repeat(32)}});
const render=s=>c.renderAutoPowerControl(s,{settings:{}});
(async()=>{
 const off=status('STOPPED','STOPPED','off',900);let view=render(off);assert(!view.button.disabled);
 const start=view.button.attrs.click();assert(!view.button.disabled,'pending Start remains cancellable');
 view=render(off);assert(!view.button.disabled);const stop=view.button.attrs.click();view.button.attrs.click();
 assert.deepEqual(calls.map(x=>x.method),['native_start','native_stop']);assert.deepEqual(calls[1].args,['manual']);assert(view.button.disabled);
 replies.shift().resolve({accepted:false,code:'STOP-SUPERSEDED-START'});await start;assert(render(off).button.disabled,'late Start cannot replace Stop');
 replies.shift().resolve({queued:true});await stop;assert(render(off).button.disabled,'ACK is not completion');
 view=render(status('STOPPED','STOPPED','off',1001));assert(!view.button.disabled);c.autoCommandPending=null;
 for(const phase of ['STARTING','RUNNING'])assert(!render(status(phase,'ARMED','on',1002)).button.disabled,'startup can be cancelled after reload');
 view=render(status('RUNNING','OBSERVING','on',1002));const failed=view.button.attrs.click();replies.shift().reject(new Error('transport'));await failed;
 assert(!render(status('RUNNING','OBSERVING','on',1002)).button.disabled,'lost Stop permits retry');assert(render(status('STOPPING','RESTORING','off',1003)).button.disabled);
 c.autoCommandPending=null;view=render({rpc_error:'unavailable'});assert(!view.button.disabled);const unknown=view.button.attrs.click();assert.equal(calls.at(-1).method,'native_stop');replies.shift().resolve({queued:false,accepted:false});await unknown;assert(!render({rpc_error:'unavailable'}).button.disabled);
 console.log('PASS: single power control, startup cancellation/races, late replies, duplicate Stop, real completion, reload/stale state and failed Stop retry');
})().catch(e=>{console.error(e);process.exitCode=1;});
