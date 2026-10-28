const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:x=>x};vm.createContext(c);vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),c);vm.runInContext(fs.readFileSync('router/auto_live_chart.inc.js','utf8'),c);
const status=(state,extra={})=>({time:100,native_failover:{state,time:100,...extra}});
assert.equal(c.autoLiveSample({...status('OBSERVING',{mode:'continuous-pair',readiness_verified:true,source:'a',target:'b'}),channel_path:{time:100,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:100,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a'}},101).kind,'source');
assert.equal(c.autoLiveSample({...status('OBSERVING',{mode:'continuous-pair',readiness_verified:true,source:'a',target:'b'}),channel_path:{time:100,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:100,source_profile_id:'a',target_profile_id:'b',active_profile_id:'b'}},101).kind,'target','a live timeline follows actual selection, not OBSERVING phase');
assert.equal(c.autoLiveSample(status('OBSERVING',{mode:'continuous-pair',readiness_verified:true}),101).kind,'unknown','no green primary timeline without current kernel proof');
const pairPath={time:100,checked_at:100,valid_for:15,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',kernel_policy_verified:true,confirmed:true,source_profile_id:'a',target_profile_id:'b',active_profile_id:'b'};
for(const state of ['STOPPED','DISABLED','EXPIRED']){const sample=c.autoLiveSample({...status(state,{mode:'continuous-pair',proof_scope:'router-probed-ipv4',source:'a',target:'b'}),channel_path:pairPath,auto_control:{requested:'off',pair_phase:'STOPPED'}},101);assert.equal(sample.kind,'off','known Auto OFF remains grey despite a known traffic route');assert.equal(sample.selected_profile_id,'b','separate route metadata is not erased by Auto OFF');}
assert.equal(c.autoLiveSample({...status('ROLLED-BACK',{mode:'continuous-pair',proof_scope:'router-probed-ipv4',source:'a',target:'b'}),channel_path:pairPath,auto_control:{requested:'on',pair_phase:'RUNNING'}},101).kind,'target','a running pair after a restoration uses verified route data');
assert.equal(c.autoLiveSample(status('COMMITTED'),101).kind,'target');
assert.equal(c.autoLiveSample(status('RESTORING'),101).kind,'switching');
assert.equal(c.autoLiveSample(status('STOPPED'),101).kind,'off');
assert.equal(c.autoLiveSample(status('OBSERVING',{certified:false}),101).kind,'unknown');
assert.equal(c.autoLiveSample(status('COMMITTED'),131).kind,'unknown');
assert.equal(c.autoLiveSample({...status('COMMITTED'),rpc_error:true},101).kind,'unknown');
assert.equal(c.autoLiveSample(status('COMMITTED'),90).kind,'unknown');
let rows=[];
for(let i=0;i<1000;i++)rows=c.autoLiveAppend(rows,{time:i,stamp:i,kind:'source'});
assert.equal(rows.length,600);assert.equal(rows[0].time,400);
let count=rows.length,last=rows[rows.length-1];
rows=c.autoLiveAppend(rows,{time:1000,stamp:1,kind:'target'});assert.equal(rows[rows.length-1].kind,last.kind);
rows=c.autoLiveAppend(rows,{time:998,stamp:998,kind:'target'});assert.equal(rows[rows.length-1].time,999);
let segments=c.autoLiveSegments([{time:1,kind:'source'},{time:3,kind:'source'},{time:5,kind:'target'},{time:40,kind:'target'}]);
assert.equal(segments[0].kind,'source');assert.equal(segments[1].kind,'source');assert(segments[2].gap);
let shown=c.autoLiveDisplayPoints([{time:1,kind:'off'},{time:3,kind:'switching'},{time:5,kind:'source'},{time:7,kind:'switching'},{time:9,kind:'target'},{time:11,kind:'unknown'},{time:13,kind:'switching'},{time:40,kind:'switching'}]);
assert.deepEqual(Array.from(shown,p=>p.kind),['off','off','source','source','target','unknown','unknown','unknown']);
assert.deepEqual(Object.keys(c.AUTO_LIVE_COLORS).sort(),['blocked','down','off','source','target']);
assert(c.autoLiveSegments(shown).filter(s=>!s.gap).every(s=>['source','target','off'].includes(s.a.kind)&&['source','target','off'].includes(s.b.kind)));
const day=c.autoDaySegments({segments:[{start:1,end:3,kind:'source'},{start:3,end:5,kind:'switching'},{start:5,end:7,kind:'target'},{start:7,end:9,kind:'unknown'},{start:9,end:11,kind:'switching'},{start:11,end:13,kind:'off'}]},15);
assert.deepEqual(Array.from(day,r=>r.kind),['source','source','target','off']);
assert.equal(day[3].start,11,'missing observations are gaps, never invented off time');
const src=fs.readFileSync('router/auto_live_chart.inc.js','utf8');assert(src.includes("method:'auto_live'"));assert(src.includes('},2)'));assert(!src.includes('innerHTML'));assert(!src.includes('localStorage'));
assert(!src.includes("kind==='switching'?67")&&!src.includes('#d97706'));
console.log('PASS: exactly three plotted levels, held confirmed route during transitions, unknown gaps, freshness, delayed replies and bounded memory');

assert.equal(c.autoDayWindow(1),1);assert.equal(c.autoDayWindow(24),24);
for(const bad of [0,25,'oops',1.5])assert.equal(c.autoDayWindow(bad),24);
const rangeHistory={segments:[{start:1,end:5000,kind:'source'},{start:5000,end:9500,kind:'target'}]};
assert.equal(c.autoDaySegments(rangeHistory,10000,1)[0].start,6400);assert.equal(c.autoDaySegments(rangeHistory,10000,1)[0].kind,'target');
assert.equal(c.autoDaySegments(rangeHistory,10000,24).length,2);
console.log('PASS: 1–24h selected window clips saved history without changing stored intervals');

class DayNode{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.value=this.attrs.value;this.children=[].concat(children||[]);}appendChild(n){this.children.push(n);}get firstChild(){return this.children[0];}removeChild(n){this.children.splice(this.children.indexOf(n),1);}setAttribute(k,v){this.attrs[k]=v;}all(){return [this,...this.children.filter(x=>x instanceof DayNode).flatMap(x=>x.all())];}}
c.E=(...args)=>new DayNode(...args);c.document={documentElement:{clientWidth:800},createElementNS:(_,tag)=>new DayNode(tag)};c.Date=class extends Date{static now(){return 10000000;}};c.locale='en';const stored={};c.window={sessionStorage:{setItem:(k,v)=>stored[k]=v}};
const plot=c.renderAutoDay({});const slider=plot.all().find(n=>n.tag==='input');assert.equal(slider.attrs.min,1);assert.equal(slider.attrs.max,24);
slider.attrs.input({target:{value:'1'}});assert.equal(c.autoDayHours,1);assert.equal(plot.all().find(n=>n.tag==='input'),slider,'drag updates plot without replacing its slider');
assert.equal(plot.all().filter(n=>n.tag==='svg').length,2);assert.equal(stored['homensai-vpn-day-hours'],'1');
assert.equal(c.renderAutoDay({}).all().find(n=>n.tag==='input').value,1,'ordinary redraw keeps selected hours');
console.log('PASS: live 1–24h slider interaction and redraw retention');

const failures=c.autoDayFailures({events:[[9999,'source','source'],[9998,'target','source'],[9997,'unknown','unknown'],[1,'source','source'],[10001,'target','target']]},10000,1);
assert.equal(failures.totals.source,1);assert.equal(failures.totals.target,1);assert.equal(failures.excluded,1);
assert.equal(failures.bins[0].selected.source,2);
const failuresView=c.renderAutoDay({accounting:{reliability:{failure_history:{since:0,details_dropped:0,events:[[9999,'source','target']]}}}});
assert(failuresView.all().some(n=>n.tag==='rect'&&Number(n.attrs.height)===100));
assert(failuresView.all().some(n=>n.tag==='title'&&String(n.textContent||'').includes('reserve: 1')));
assert.equal(failuresView.all().filter(n=>n.tag==='input').length,1);
console.log('PASS: failure episodes by original role, unknown history, selected route, clipped window, two charts share one retained slider');

const two=c.renderAutoDay({accounting:{reliability:{failure_history:{since:0,details_dropped:0,events:[[9999,'source','source'],[9998,'target','source'],[9997,'unknown','target']]}}}});
const bars=two.all().filter(n=>n.tag==='rect');assert.equal(bars.length,2);
assert.deepEqual(new Set(bars.map(n=>n.attrs.fill)),new Set(['#2563eb','#e07816']));
assert(!two.all().some(n=>n.tag==='summary'&&n.children.join('').includes('Archive without saved role: 1')));
assert(!two.all().some(n=>String(n.textContent||'').includes('Channel unknown')));
assert(two.all().filter(n=>n.attrs['data-failure-role']==='source').length>=2,'legend and bar share role');
console.log('PASS: exactly two coloured series and matching legend; legacy unassigned rows excluded without fabricated attribution');
// A blocked Auto and two failing channels are drawn as states of their own, not as an empty line.
{
  const now=1000,ns={state:'BLOCKED',time:now-2,blockers:['PAIR-EXTERNAL-POLICY-CHANGE']};
  const bad=id=>({id,time:now-3,code:'VPN-003',dns_ok:false,https_success:0}),good=id=>({id,time:now-3,code:null,dns_ok:true,https_success:2});
  const inv={settings:{plan_source:'a',plan_target:'b'}},base={time:now-2,server_time:now,native_failover:ns};
  c.rolePairIds=(status,inventory)=>[inventory.settings.plan_source,inventory.settings.plan_target];
  assert.equal(c.autoLiveSample(Object.assign({profiles:[good('a'),good('b')]},base),now,inv).kind,'blocked');
  assert.equal(c.autoLiveSample(Object.assign({profiles:[bad('a'),good('b')]},base),now,inv).kind,'blocked','one working channel is not an outage');
  const down=c.autoLiveSample(Object.assign({profiles:[bad('a'),bad('b')]},base),now,inv);
  assert.equal(down.kind,'down');assert(c.autoLiveLabel('down').includes('оба канала')||c.autoLiveLabel('down').includes('both channels'));
  assert.equal(c.autoLiveSample(Object.assign({profiles:[bad('a'),bad('b')]},base,{native_failover:{state:'OBSERVING',certified:true,time:now-2}}),now,inv).kind,'down','outage wins over a stale route confirmation');
  assert.equal(c.autoLiveSample({time:now-2,native_failover:{}},now,inv).kind,'unknown');
  console.log('PASS: blocked Auto and no working channel are visible states');
}
