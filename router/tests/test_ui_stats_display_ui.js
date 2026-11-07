// F-53, F-59, F-61 (review of 2026-11-06): the displayed statistics must say what they are. Latest-success count from one population,
// the P95 shown as an estimate next to a separately computed upper confidence bound (scripts/honest_stats.py rule), and the
// manual or automatic origin of a transition kept. The page logic is executed from its sources in a vm. No browser.
'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');

// ---------- F-53: "successful / all" ----------
class N{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).filter(v=>v!=null);this.disabled=attrs.disabled!=null;this.value=attrs.value||'';}
  appendChild(n){this.children.push(n);return n;}get firstChild(){return this.children[0];}removeChild(n){this.children.splice(this.children.indexOf(n),1);}
  setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}
}
const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
const text=n=>n instanceof N?(n.textContent||'')+n.children.map(text).join(' '):String(n==null?'':n);
function speedRows(period,results){
  const c={Date,Intl,Number,locale:'en',bi:(en)=>en,E:(...a)=>new N(...a),document:{createElementNS:(_ns,tag)=>new N(tag)},serverTitle:p=>p.name,safeCode:()=>null,showErrorCode(){},ui:{addNotification(){},showModal(){}},rpc:{declare:()=>()=>Promise.resolve({})},window:{}};
  vm.createContext(c);vm.runInContext(fs.readFileSync('router/speed_live.inc.js','utf8')+'\n'+fs.readFileSync('router/speed_table.inc.js','utf8'),c);
  const profiles=[{id:'wg',name:'Main WG',interface:'wg1'}];
  const panel=c.speedPanel({profiles,speed_tests:{results,state:'IDLE'}},{settings:{speed_enabled:true}},period,()=>{});
  const row=walk(panel).filter(n=>n.tag==='tr').find(n=>text(n).includes('Main WG'));
  const cells=row.children.filter(n=>n instanceof N&&n.tag==='td');return text(cells[cells.length-1]).replace(/\s+/g,' ').trim();
}
const now=Date.now()/1000;
const ok=(i)=>({id:'wg',time:now-i*60,download:{mbps:90},upload:{mbps:40}});
const bad=(i)=>({id:'wg',time:now-i*60,code:'SPEED-TIMEOUT'});
const twenty=(firstOk)=>Array.from({length:20},(_,i)=>i===0&&!firstOk?bad(i):ok(i));
assert.equal(speedRows('latest',twenty(true)),'1 / 1','latest: one test, one success (was 1 / 20)');
assert.equal(speedRows('latest',twenty(false)),'0 / 1','latest: the newest test failed: 0 / 1, not 0 / 20');
assert.equal(speedRows('week',twenty(true)),'20 / 20','a period counts both numbers from the period');
assert.equal(speedRows('week',twenty(false)),'19 / 20');
console.log('PASS: F-53 - the latest-success count has numerator and denominator from the same population');

// ---------- F-59 and F-61: the analytics logic ----------
const c={bi:(en)=>en,locale:'en'};vm.createContext(c);
vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),c);vm.runInContext(fs.readFileSync('router/analytics_panel.inc.js','utf8'),c);
// ranks of the one-sided upper confidence bound = scripts/honest_stats.py _ranks(n, 0.95, 0.95)[2] (computed there with exact fractions)
assert.deepEqual([1,20,58,59,60,70,100,200,500,1000].map(n=>c.quantileUpperRank(n)),[null,null,null,59,60,70,99,196,484,962],'the same ranks as honest_stats.py');
const dur=n=>Array.from({length:n},(_,i)=>({start:i,end:i+1,target:'b',outcome:'committed',duration:i+1,provenance:'automatic'}));
let s=c.recoverySummary(dur(59),0,100);
assert.equal(s.p95,57,'the empirical 95th percentile of the sample (an estimate)');assert.equal(s.p95_upper,59,'the upper confidence bound is another number (honest_stats: 59)');
s=c.recoverySummary(dur(20),0,100);assert.equal(s.p95_upper,null,'below 59 samples there is no honest upper bound');
const fmt=v=>v.toFixed(1);
assert.equal(c.p95UpperText(null,20,fmt),'— (needs ≥59 samples; n=20)');assert.equal(c.p95UpperText(59,59,fmt),'59.0');
// the panel shows the estimate and the bound as separate rows
const panel=fs.readFileSync('router/analytics_panel.inc.js','utf8');
assert(/Recovery time, P95 estimate \(s\)/.test(panel)&&/Recovery time, P95 upper bound, 95 % confidence \(s\)/.test(panel)&&panel.includes('p95UpperText(s.p95_upper,s.recovered_samples,fmt)'),'two rows in the panel');
assert(!/Recovery time, P95 \(s\)/.test(panel),'no unqualified "P95" row');
console.log('PASS: F-59 - P95 is labelled an estimate; the upper confidence bound is its own row, absent below 59 samples (same ranks as honest_stats.py)');

const ev=(seq,time,state,extra)=>Object.assign({sequence:seq,time,state,source:'a',target:'b',codes:[],trial:false},extra||{});
const rows=c.retainedTransitions({events:[
  ev(1,100,'APPLYING',{transition_source:'automatic'}),ev(2,104,'COMMITTED',{transition_source:'automatic'}),
  ev(3,200,'APPLYING',{transition_source:'manual'}),ev(4,203,'COMMITTED',{transition_source:'manual'}),
  ev(5,300,'APPLYING'),ev(6,305,'COMMITTED')]});
assert.deepEqual(rows.map(r=>r.provenance),['automatic','manual','unknown'],'the origin survives in the row');
s=c.recoverySummary(rows,0,1000);
assert.equal(s.attempts,3);assert.equal(s.automatic_attempts,1,'only the automatic one is automatic (was 3)');assert.equal(s.manual_attempts,1);assert.equal(s.other_attempts,1,'an unrecorded origin is not guessed');
const man=c.retainedTransitions({events:[ev(1,10,'APPLYING',{action_source:'manual'}),ev(2,13,'COMMITTED',{action_source:'manual'})]});
assert.equal(man[0].provenance,'manual','action_source is honoured when transition_source is absent');
console.log('PASS: F-61 - manual and automatic origin is kept: counted apart, an unrecorded origin stays "other"');
