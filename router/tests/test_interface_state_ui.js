const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:en=>en,locale:'en'};vm.createContext(c);
for(const name of ['ui_logic','auto_live_chart','design_views','analytics_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
const now=100,primary={id:'a',interface:'wgclient1',time:99,dns_ok:true,https_success:2,code:null},reserve={...primary,id:'b',interface:'ovpnclient1'};
const model={now,primary,reserve,selected:'a',settings:{plan_source:'a',plan_target:'b'}};
const status={time:99,native_failover:{state:'OBSERVING',time:99}};
assert.equal(c.dvChannelUse(primary,model,status).kind,'green');assert.equal(c.dvChannelUse(primary,model,status).role,'Primary channel');
assert.equal(c.dvChannelUse(reserve,model,status).kind,'yellow');assert.equal(c.dvChannelUse(reserve,model,status).label,'Spare · ready to take over');
assert.equal(c.dvChannelUse({...reserve,interface:null},model,status).kind,'red');
assert.equal(c.dvChannelUse({...primary,code:'DNS-001'},model,status).kind,'red');
assert.equal(c.dvChannelUse(primary,model,{...status,rpc_error:true}).kind,'red');
assert.equal(c.dvChannelUse(reserve,{...model,selected:'b'},status).kind,'green');assert.equal(c.dvChannelUse(primary,{...model,selected:'b'},status).kind,'yellow');
assert.equal(c.dvChannelUse(primary,{...model,selected:null},status).kind,'green');assert.equal(c.dvChannelUse(primary,{...model,selected:null},status).label,'Ready for automatic mode');
assert.equal(c.selectedProfile({native_failover:{state:'OBSERVING',source:'a',time:99,mode:'continuous-pair',readiness_verified:true}},100),'a');
let segments=c.autoDaySegments({segments:[{start:0,end:10,kind:'source'},{start:99990,end:100000,kind:'target'},{start:100001,end:100002,kind:'source'},{start:99990,end:99999,kind:'invalid'}]},100000);
assert.equal(segments.length,1);assert.equal(segments[0].kind,'target');
const marks=c.controllerTransitionMarks([{sequence:1,attempt_id:1,state:'APPLYING'},{sequence:2,attempt_id:1,state:'COMMITTED'},{sequence:3,attempt_id:1,state:'DEGRADED-ON-RESERVE'},{sequence:4,attempt_id:1,state:'COMMITTED'},{sequence:5,attempt_id:1,state:'ROLLED-BACK',original_restored:true},{sequence:6,attempt_id:2,state:'ROLLED-BACK',original_restored:true}]);
assert.equal(marks[1].confirmed,false);assert.equal(marks[2].confirmed,true);assert.equal(marks[4],undefined);assert.equal(marks[5].from,2);assert.equal(marks[6],undefined);
let chartY=500,scrollY=600;
const details=[{open:true}],chart={id:'hv-auto-live-chart',getAttribute:()=>null,getBoundingClientRect:()=>({top:chartY-scrollY,bottom:chartY-scrollY+300})};
const section={querySelectorAll:selector=>selector==='details'?details:[chart],querySelector:selector=>selector==='#hv-auto-live-chart'?chart:null};
const root={isConnected:true,querySelector:()=>section};
c.window={get scrollY(){return scrollY},scrollX:0,innerHeight:700,scrollTo:opts=>{scrollY=opts.top}};
vm.runInContext(fs.readFileSync('router/viewport_state.inc.js','utf8'),c);
const saved=c.capturePageViewport(root,'overview');scrollY=0;details[0].open=false;c.restorePageViewport(root,saved);assert.equal(scrollY,600);assert.equal(details[0].open,true);
scrollY=0;chartY=580;c.restorePageViewport(root,saved);assert.equal(scrollY,680,'anchor remains at the same visual offset after height changes');
c.rememberPageViewport(root,'overview');scrollY=0;c.revisitPageViewport(root,'overview');assert.equal(scrollY,680);
const src=fs.readFileSync('router/build_sidebar_ui.py','utf8');assert(src.includes("if(table.closest('.hv-errtable'))return;"));assert(src.includes('finally {if(refreshViewport'));
const css=fs.readFileSync('router/design_layer.css','utf8');assert(css.includes('select.hv-traffic-scope option{font-size:13px!important'));
console.log('PASS: primary/reserve and at most one green, yellow standby/red disconnected, persisted day segments, deduplicated transition badges, redraw clamp/anchor/details and page-return scroll preservation');

// Router timestamps are compared on the router clock, not a drifting operator computer clock.
{
 let monotonic=0;c.performance={now:()=>monotonic};c.Date={now:()=>1300000};
 const frame={server_time:1000,time:999,native_failover:{time:999}};
 assert.equal(c.statusNow(frame),1000);
 const row={id:'p',interface:'wgclient1',time:999,dns_ok:true,https_success:2};
 assert.equal(c.dvChannelUse(row,{now:c.statusNow(frame),settings:{},selected:'p'},frame).kind,'green');
 monotonic=92000;assert.equal(c.statusNow(frame),1092);
 assert.equal(c.dvChannelUse(row,{now:c.statusNow(frame),settings:{},selected:'p'},frame).kind,'red','an old frame still expires');
 delete c.Date;delete c.performance;
}
console.log('PASS: client clock skew does not grey out fresh VPN data; old observations still expire');

{
 const disclosure=(key,open)=>({key,open,getAttribute:()=>key});
 const technical=disclosure('technical',false),live=disclosure('live-statistics',true);
 let nodes=[technical,live];
 const section={querySelectorAll:s=>s==='details'?nodes:[],querySelector:s=>nodes.find(n=>s==='details[data-auto-disclosure="'+n.key+'"]')||null};
 const root={isConnected:true,querySelector:()=>section};
 const saved=c.capturePageViewport(root,'overview');
 const inserted=disclosure('new-readiness-detail',false);nodes=[inserted,technical,live];technical.open=true;live.open=false;
 c.restorePageViewport(root,saved);assert.equal(technical.open,false);assert.equal(live.open,true);assert.equal(inserted.open,false,'a new earlier detail must not inherit the chart expansion');
 console.log('PASS: Auto technical/live disclosures restore by stable identity when readiness details change order');
}
