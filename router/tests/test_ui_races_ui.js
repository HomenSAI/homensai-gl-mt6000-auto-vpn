// F-71, F-72, F-73, F-74 (review of 2026-11-06): ordering of replies, locks that cover a whole operation, section-wise drafts
// and the advisor lock taken before the request is sent. The shipped page is driven in a vm with answers that the test
// resolves by hand, so the order of replies is under the test's control. No browser.
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const {load,ROOT,app}=require('./approved_page');
const flush=()=>new Promise(r=>setTimeout(r,25));
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};
const clone=o=>JSON.parse(JSON.stringify(o));
const count=(p,m)=>p.calls.filter(c=>c.method===m).length;

(async()=>{
// ---------- F-71: replies of the inventory may arrive in any order; the newest request wins ----------
{
  const q=[];
  const p=load({scn:'off',answers:{inventory:()=>{const d=deferred();q.push(d);return d.promise;}}});
  const mk=interval=>{const x=clone(p.inventory);x.settings.interval=interval;return x;};
  const first=p.T.reloadInventory(),second=p.T.reloadInventory();
  await flush();assert.equal(q.length,2);
  q[1].resolve(mk(22));await flush();
  q[0].resolve(mk(11));await Promise.all([first,second]);
  assert.equal(p.T.HV.inv.settings.interval,22,'the older reply that arrives last must not overwrite the newer one');
}
console.log('PASS: F-71 - inventory replies in reverse order: the newest request wins');
{ // a request made while one is in flight gets one trailing request, shared by all callers
  const q=[];
  const p=load({scn:'off',answers:{status:()=>{const d=deferred();q.push(d);return d.promise;}}});
  const answer=()=>clone(p.status);
  const base=count(p,'status');
  const a=p.T.refreshNow();let aDone=false,bDone=false,cDone=false;a.then(()=>{aDone=true;});
  await flush();assert.equal(count(p,'status')-base,1,'one request in flight');
  const b=p.T.refreshNow(),c=p.T.refreshNow();b.then(()=>{bDone=true;});c.then(()=>{cDone=true;});
  await flush();assert.equal(count(p,'status')-base,1,'no second request while the first one is in flight');
  q[0].resolve(answer());await flush();
  assert(aDone,'the first caller is answered by the first reply');
  assert.equal(count(p,'status')-base,2,'the action that finished while the first request was in flight asks once more');
  assert(!bDone&&!cDone,'the late callers are not answered by the older reply');
  q[1].resolve(answer());await Promise.all([b,c]);
  assert.equal(count(p,'status')-base,2,'one trailing request for both late callers');
}
console.log('PASS: F-71 - a refresh requested during a refresh is answered by one trailing request, not by the older reply');

// ---------- F-72: locks cover the whole operation ----------
{ // "Stop Auto and save": the lock is taken at the confirmation, not when the save is sent
  const p=load({scn:'ok'});p.T.snap();
  p.T.draft().tgChat='@mine';p.T.saveSection('monitor');
  const m=p.modals.pop();assert(m&&/CONFIG-STOP-AUTO-FIRST/.test(m.body),'Auto runs: the page offers to stop it first');
  m.buttons[1].fn();
  assert.equal(p.T.HV.busy.save,true,'locked from the confirmation');
  p.T.saveSection('tg');await flush();
  assert.equal(count(p,'setup_telegram'),0,'a second save pressed while Auto is being stopped sends nothing');
}
console.log('PASS: F-72 - saving while Auto is being stopped is locked from the confirmation');
{ // restore monitoring: the lock is kept until the status after the action has been read (the failure test start uses the same pattern;
  // its confirmation window needs a certified pair that the synthetic fixture does not reach, so that path is reviewed, not run)
  const q=[];let hold=false;
  const p=load({scn:'ok',answers:{monitor_control:()=>({accepted:true}),status:()=>{if(!hold)return clone(p.status);const d=deferred();q.push(d);return d.promise;}}});
  p.T.snap();hold=true;
  p.T.restoreMonitor();p.T.restoreMonitor();
  await flush();assert.equal(count(p,'monitor_control'),1,'a second press sends nothing');
  assert.equal(p.T.HV.busy.monitor,true,'still locked while the status after the action is not read');
  p.T.restoreMonitor();assert.equal(count(p,'monitor_control'),1);
  await flush();q.forEach(d=>d.resolve(clone(p.status)));await flush();await flush();await flush();q.forEach(d=>d.resolve(clone(p.status)));await flush();
  assert.equal(p.T.HV.busy.monitor,false,'released after the status was read');
}
console.log('PASS: F-72 - restore-monitoring lock lasts until the status after the action is read');
{ // stop of the failure test and restore of monitoring cannot be sent twice
  const q=[];
  const p=load({scn:'ok',answers:{fault_cancel:()=>{const d=deferred();q.push(d);return d.promise;}}});
  p.T.snap();p.T.stopFault();p.T.stopFault();await flush();
  assert.equal(count(p,'fault_cancel'),1,'one cancel request');
}

// ---------- F-73: saving one section keeps the drafts of the others, and does not send them ----------
{
  const p=load({scn:'off'});p.T.snap();
  const d=p.T.draft();
  d.tgChat='@mine';p.T.HV.dirty.tg=true;
  d.live=999;d.days=3;p.T.HV.dirty.history=true;
  d.monInterval=33;p.T.HV.dirty.monitor=true;
  await p.T.saveSection('monitor');await flush();
  const mon=p.calls.filter(c=>c.method==='setup_monitor');
  assert.equal(mon.length,1);
  assert.deepEqual(mon[0].params,['interval','checkpoint','probe_limit','planning_enabled','live_log_limit','history_days']);
  assert.equal(mon[0].args[0],33,'the monitor field is sent');
  assert.equal(mon[0].args[4],2000,'the stored live-log size, not the unsaved History draft (999)');
  assert.equal(mon[0].args[5],7,'the stored history days, not the unsaved History draft (3)');
  assert.equal(count(p,'setup_stats'),0,'saving the monitor writes no statistics mode');
  assert.equal(p.T.draft().tgChat,'@mine','the Telegram draft survives');assert.equal(p.T.HV.dirty.tg,true,'and is still marked unsaved');
  assert.equal(p.T.draft().live,999,'the History draft survives');assert.equal(p.T.HV.dirty.history,true);
  assert.equal(p.T.HV.dirty.monitor,false,'the saved section is clean');
}
{ // Discard touches only its own section
  const p=load({scn:'off'});p.T.snap();const d=p.T.draft();
  d.tgChat='@mine';p.T.HV.dirty.tg=true;d.speedMib=9;p.T.HV.dirty.speed=true;
  p.T.discardSection('tg');
  assert.equal(p.T.draft().tgChat,'','the discarded section returns to the router value');
  assert.equal(p.T.draft().speedMib,9,'the other draft stays');assert.equal(p.T.HV.dirty.speed,true,'and stays marked unsaved');assert.equal(p.T.HV.dirty.tg,false);
}
{ // the pair save does not carry the unsaved allow-drop edit of the rules section
  const p=load({scn:'off'});p.T.snap();const d=p.T.draft();
  d.allowDrop=!d.allowDrop;p.T.HV.dirty.rules=true;
  const stored=p.inventory.settings.native_session_loss===true;
  await p.T.saveSection('pair');await flush();
  const sys=p.calls.filter(c=>c.method==='setup_system');assert.equal(sys.length,1);
  assert.equal(sys[0].args[4],stored,'session_loss is the stored value');assert.equal(p.T.HV.dirty.rules,true);
}
console.log('PASS: F-73 - a section saves only its own fields (monitor sends no History values) and keeps the other unsaved drafts');

// ---------- F-74: the advisor lock is taken before the request is sent ----------
const raw=JSON.parse(fs.readFileSync(path.join(ROOT,'router/files/usr/lib/homensai-vpn/slider_curve.json'),'utf8'));
const curve={version:raw.version,params:raw.params,metrics:raw.metrics,anchors:raw.anchors.map(a=>({t:a.t,p:a.p,m:a.m})),alpha8:raw.alpha8};
{
  const p=load({answers:{advisor:()=>({curve}),advisor_settings:()=>({saved:true})},mutate:({status})=>{status.network_advisor={mode:'advice',window_days:7,curve_version:1,
    current:{t_ref:0.5,slider_t:0.5,attached:true,label:'slider',nearest_t:0.5,failure_model:'hmm',theta:0.6,dur_b:5,pg:0.95,primary_stable:120,rescue_stable:10},
    recommendation:{state:'shift',t:0.7,reason_ru:'r',reason_en:'r'},last_change:null};}});
  p.c.HV_FIXTURE_ADVISOR_OFF=true;p.T.snap();p.T.advCardHTML();await flush();p.T.snap();
  p.T.advClick('advmode',{dataset:{m:'auto'}});p.T.advClick('advmode',{dataset:{m:'manual'}});p.T.advClick('advwin',{dataset:{w:'30'}});
  await flush();
  assert.equal(count(p,'advisor_settings'),1,'two more presses while the first request is in progress send nothing');
}
{ // the optional module passes a function as well (the request is not started before the lock)
  const mod=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m))),'utf8');
  const from=mod.indexOf('var EXPERT_GROUPS='),end='act:act,hint:hint};\n};',to=mod.indexOf(end,from)+end.length;
  const expertUI=vm.runInNewContext(mod.slice(from,to)+';EXPERT_UI',{});
  const seen=[];let sent=0;
  const u=expertUI({t:(ru,en)=>en===undefined?ru:en,esc:String,HV:{inv:{settings:{}}},XD:{ed:{}},ADV:{},$$:()=>[],advNum:String,
    rpcCall:()=>()=>{sent++;return Promise.resolve({saved:true});},advRpc:(fn,msg)=>{seen.push(typeof fn);},toast(){},modal(){}});
  u.act('advfast',{dataset:{}},{mode:'auto',window_days:7,current:{fast:false}});
  assert.deepEqual(seen,['function'],'the module hands over a function');assert.equal(sent,0,'nothing is sent by the module itself');
}
console.log('PASS: F-74 - the advisor busy lock is taken before the request is sent (page and optional module)');
})().catch(e=>{console.error(e);process.exit(1);});
