// 2.1.0-alpha9 expert settings on the SHIPPED page (04.11.2026): the fast end of the master slider (positions -0.1 / -0.2 with the
// administrator switch, turbo points locked until the acknowledgement phrase, rpc advisor_settings fast / turbo / turbo_ack) and the
// collapsed expert group «Для эксперта → Детектор и датчики» (19 fields: flap damping through setup_recovery, the rest through
// setup_detector; fields that need Auto off offer to stop it instead of failing). Texts, ranges and the renderer come with the
// optional module (help<N>.js), so the first screen stays within its size bound.
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const {load,strip,pageSource,CSS,ROOT,app}=require('./approved_page');
const raw=JSON.parse(fs.readFileSync(path.join(ROOT,'router/files/usr/lib/homensai-vpn/slider_curve.json'),'utf8'));
const curve={version:raw.version,params:raw.params,metrics:raw.metrics,anchors:raw.anchors.map(a=>({t:a.t,p:a.p,m:a.m})),alpha8:raw.alpha8,
  fast_params:raw.fast_params,fast_anchors:raw.fast_anchors.map(a=>({t:a.t,p:a.p,x:a.x,m:a.m}))};
const flush=()=>new Promise(r=>setTimeout(r,30));

// ---- the optional module: the expert pieces, evaluated exactly as shipped ----
const moduleText=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m))),'utf8');
const from=moduleText.indexOf('var EXPERT_GROUPS='),endMark='act:act,hint:hint};\n};',to=moduleText.indexOf(endMark,from)+endMark.length;
assert(from>0&&to>from,'expert pieces found in the optional module');
assert(/expertUI:EXPERT_UI\}/.test(moduleText),'the module exports expertUI');
const mc=vm.createContext({document:{getElementById:()=>null}});
const lazy=vm.runInContext(moduleText.slice(from,to)+';({F:EXPERT_FIELDS,G:EXPERT_GROUPS,UI:EXPERT_UI,ACK:EXPERT_ACK,CODE:EXPERT_ACK_CODE})',mc);
const api={expertFields:()=>lazy.F,expertGroups:()=>lazy.G,expertUI:lazy.UI,helpTopics:()=>[]};

function advisor(over){
  const base={mode:'advice',window_days:7,curve_version:1,
    current:{t_ref:0.5,slider_t:0.5,attached:true,label:'slider',nearest_t:0.5,failure_model:'hmm',theta:0.6,dur_b:5,pg:0.95,primary_stable:120,rescue_stable:10,fast:false,turbo:false},
    recommendation:{state:'keep',t:0.5,reason_ru:'Оставить.',reason_en:'Keep.',events:16,days_used:7,window_days:7,generated:1700000000,counts:{}},
    journal:{days:7,window_days:7,tunnels:{},pair:{switches:2,returns:2,unnecessary:1}},last_change:null};
  return Object.assign(base,over||{},{current:Object.assign(base.current,(over||{}).current||{})});
}
async function page(opts){
  opts=opts||{};
  const p=load({lang:opts.lang||'ru',scn:opts.scn,answers:Object.assign({advisor:()=>({curve}),setup_detector:()=>({saved:true}),setup_recovery:()=>({saved:true}),advisor_settings:()=>({saved:true}),advisor_apply:()=>({saved:true})},opts.answers||{}),
    mutate:({status,settings})=>{status.network_advisor=advisor(opts.adv);Object.assign(settings,opts.settings||{});}});
  p.c.HV_FIXTURE_ADVISOR_OFF=true;
  p.c.L.require=()=>Promise.resolve({create:()=>api});
  p.T.snap();p.T.advCardHTML();await flush();p.T.snap();
  if(!opts.cold){p.T.HV.open['sec-adv']=true;p.T.advSectionBody();await flush();}  // opening the panel asks for the optional module once
  return p;
}
const el=(k,v,type)=>({dataset:{xd:k},checked:v===true,value:String(v),type:type||'text'});
const rpcs=p=>p.calls.filter(c=>/^(setup_|advisor_)/.test(c.method));

(async()=>{
// ---------- the descriptors: complete, bilingual, the ranges and defaults of the backend ----------
{
  const F=lazy.F,keys=F.map(f=>f.k);
  assert.deepEqual(keys,['recovery_flap_model','recovery_flap_limit','recovery_flap_window','recovery_flap_halflife','recovery_flap_suppress','recovery_flap_reuse',
    'retry_backoff','auto_event_wake','parallel_recheck','probe_spread','reserve_probe_interval','probe_target_log','wan_sensor','wan_recover_grace','wg_events','stall_sensor','stall_veto','heartbeat_quorum','server_key_pin']);
  const want={recovery_flap_model:'double',recovery_flap_limit:[2,1,10],recovery_flap_window:[60,1,120],recovery_flap_halflife:[1800,600,3600],recovery_flap_suppress:[1500,1000,3000],recovery_flap_reuse:[500,200,1000],
    retry_backoff:'fibonacci',auto_event_wake:true,parallel_recheck:false,probe_spread:true,reserve_probe_interval:[0,20,120],probe_target_log:true,wan_sensor:true,wan_recover_grace:[30,0,120],wg_events:true,stall_sensor:true,stall_veto:true,heartbeat_quorum:false,server_key_pin:'warn'};
  F.forEach(f=>{
    const w=want[f.k];assert(w!==undefined,f.k);
    if(Array.isArray(w))assert.deepEqual([f.d,f.min,f.max],w,f.k+' default and safe range');else assert.strictEqual(f.d,w,f.k+' default');
    assert(f.l[0]&&f.l[1]&&f.h[0]&&f.h[1],f.k+' label and explanation in both languages');
    assert(!/[А-Яа-яЁё]/.test(f.l[0]+f.h[0]+(f.o||[]).map(o=>o[1][0]).join('')),f.k+' English text clean');
    assert(/[А-Яа-яЁё]/.test(f.l[1]+f.h[1]),f.k+' Russian text');
    if(f.ty==='s')assert(f.o.some(o=>o[0]===f.d),f.k+' the default is one of the choices');
    assert.equal(!!f.stop,['recovery_flap_model','recovery_flap_limit','recovery_flap_window','recovery_flap_halflife','recovery_flap_suppress','recovery_flap_reuse','retry_backoff','auto_event_wake','parallel_recheck'].includes(f.k),f.k+' needs Auto off exactly where the backend asks');
    if(f.dep)assert(keys.includes(f.dep[0]),f.k+' depends on a known field');
  });
  assert.equal(lazy.G.length,5);F.forEach(f=>assert(f.g>=0&&f.g<5));
  // the backend ranges are the same numbers (recovery_settings.RANGES, setup_config.DETECTOR_*)
  const rs=fs.readFileSync(path.join(ROOT,'router/files/usr/lib/homensai-vpn/recovery_settings.py'),'utf8');
  for(const [k,r] of [['flap_limit',[1,10]],['flap_window',[1,120]],['flap_halflife',[600,3600]],['flap_suppress',[1000,3000]],['flap_reuse',[200,1000]]])
    assert(rs.includes("'"+k+"':("+r[0]+","+r[1]+")"),k+' range in recovery_settings.py');
  assert(!/[А-Яа-я]/.test(JSON.stringify(lazy.CODE))&&lazy.CODE==='minimum-downtime-up-to-8-extra-switches-a-day');
}
console.log('PASS: 19 fields - keys, defaults, safe ranges equal to the backend, RU and EN text, where Auto must be off');

// ---------- the section: collapsed, nothing loaded until it is opened ----------
{
  const q=load({lang:'ru'});q.c.L.require=()=>{q.required=(q.required||0)+1;return Promise.resolve({create:()=>api});};q.T.snap();
  const html=q.T.settingsA();
  assert(html.includes('id="sec-xdet"')&&!/id="sec-xdet"[^>]* open/.test(html),'collapsed');
  assert(html.indexOf('Для эксперта</h2>')<html.indexOf('id="sec-xdet"')&&html.indexOf('id="sec-xdet"')<html.indexOf('id="sec-system"'),'under the group «Для эксперта»');
  assert(strip(html).includes('Для эксперта → Детектор и датчики'),'title');
  assert(!html.includes('data-xd='),'no fields while collapsed');assert(!q.required,'the optional module is not asked for while the section is closed');
  assert(q.T.tabs.auto().includes('id="sec-xdet"'),'also in the console «Auto» tab');
  const e=load({lang:'en'});e.T.snap();assert(strip(e.T.settingsA()).includes('For experts → Detector and sensors'));
}
console.log('PASS: section «Для эксперта → Детектор и датчики» is collapsed and loads nothing until opened');

// ---------- opening: loading, then the fields with defaults marks, ranges and the Auto-off notes ----------
for(const lang of ['ru','en']){
  const p=await page({lang,scn:'off',cold:true});p.T.HV.open['sec-xdet']=true;
  let html=p.T.settingsA();assert(html.includes(lang==='ru'?'Загрузка…':'Loading…')&&!html.includes('data-xd='),'loading placeholder');
  await flush();p.T.snap();html=p.T.settingsA();
  assert.equal((html.match(/data-xd="/g)||[]).length,19,'19 fields');
  const text=strip(html);
  for(const s of lang==='ru'?['Качели: пауза возврата','Цикл Auto: паузы и пробуждение','Проверки монитора','Датчики','Ключи серверов','Модель паузы возврата','по умолчанию','допустимо: 1–10','допустимо: 0 или 20–120 с','допустимо: 0–120 с','нужен выключенный Auto','Пульс «2 из 3 целей»','Не использовать канал']:
                           ['Flapping: pause before the return','Auto loop: pauses and waking','Monitor checks','Sensors','Server keys','Return pause model','default','allowed: 1–10','allowed: 0 or 20–120 s','allowed: 0–120 s','needs Auto off','Heartbeat «2 of 3 targets»','Block the channel'])
    assert(text.includes(s),lang+' text: '+s);
  assert(!/class="dm chg"/.test(html),'every value is the default at first');
  assert(html.includes('<select id="xd-server_key_pin"')&&html.includes('value="warn" selected'),'server_key_pin shows the default (inventory carries it)');
  assert(/id="xd-heartbeat_quorum"[^>]*data-xd="heartbeat_quorum"><\/div>|id="xd-heartbeat_quorum" data-xd="heartbeat_quorum">/.test(html)||!/id="xd-heartbeat_quorum"[^>]* checked/.test(html),'heartbeat quorum off by default');
  // dependants are greyed while their parent is off
  assert(/id="xd-recovery_flap_halflife"[^>]* disabled/.test(html),'half-life fields are for the half-life model only');
  assert(!/id="xd-wan_recover_grace"[^>]* disabled/.test(html),'WAN grace is on while the WAN diagnosis is on');
  assert(html.includes('data-sec="xdet"')&&html.includes('data-dirty="xdet"'),'save bar');
  assert(!html.includes('Auto сейчас работает')&&!html.includes('Auto is running now'),'Auto is off: no stop note');
}
{
  const p=await page({scn:'ok'});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  assert(strip(p.T.settingsA()).includes('Auto сейчас работает'),'Auto works: the page says in advance what saving will ask');
}
console.log('PASS: opened section - loading, 19 fields with default marks, safe ranges, Auto-off notes, RU and EN');

// ---------- values from the router, changed marks, dependants ----------
{
  const p=await page({scn:'off',settings:{recovery_flap_model:'halflife',recovery_flap_limit:4,retry_backoff:'fixed',reserve_probe_interval:60,wan_sensor:false,stall_sensor:false,heartbeat_quorum:true,server_key_pin:'enforce'}});
  p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();const html=p.T.settingsA(),text=strip(html);
  assert((html.match(/class="dm chg"/g)||[]).length===8,'eight values differ from the defaults: '+(html.match(/class="dm chg"/g)||[]).length);
  assert(text.includes('по умолчанию: Удвоение')&&text.includes('по умолчанию: 2')&&text.includes('отличается от умолчаний: 8 из 19'));
  assert(!/id="xd-recovery_flap_halflife"[^>]* disabled/.test(html),'half-life model: fields active');
  assert(/id="xd-wan_recover_grace"[^>]* disabled/.test(html)&&/id="xd-stall_veto"[^>]* disabled/.test(html),'dependants off with their sensor');
  assert(html.includes('value="enforce" selected')&&html.includes('value="fixed" selected'));
}
console.log('PASS: values read from the router, «по умолчанию: …» where they differ, dependants follow their parent');

// ---------- editing and saving: only changed fields, the right rpc, Auto off where needed ----------
{ // sensors alone: no stop needed even with Auto working
  const p=await page({scn:'ok'});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  assert.equal(p.T.xdU().prep(),null,'nothing changed: nothing to save');assert(p.toasts.some(m=>/Нечего сохранять/.test(m)));
  p.T.xdU().input(el('stall_veto',false),{type:'input'});p.T.xdU().input(el('wan_recover_grace',45,'number'),{type:'input'});p.T.xdU().input(el('server_key_pin','off'),{type:'input'});
  assert.equal(p.T.HV.dirty.xdet,true);
  p.modals.length=0;await p.T.saveSection('xdet');await flush();
  assert(!p.modals.some(m=>/Сначала остановить Auto/.test(m.title)),'a sensor change does not ask to stop Auto');
  const r=rpcs(p);assert.equal(r.length,1);assert.equal(r[0].method,'setup_detector');
  assert.deepEqual(r[0].params,['wan_recover_grace','stall_veto','server_key_pin']);assert.deepEqual(r[0].args,[45,false,'off']);
  assert(p.toasts.some(m=>/Сохранено/.test(m)),'confirmed by the router');
}
{ // an option of the Auto loop while Auto works: the page explains and offers the stop, nothing is sent
  const p=await page({scn:'ok'});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  p.T.xdU().input(el('retry_backoff','fixed'),{type:'change'});p.T.xdU().input(el('probe_spread',false),{type:'input'});
  p.modals.length=0;p.T.saveSection('xdet');await flush();
  const m=p.modals.find(x=>/Сначала остановить Auto/.test(x.title));
  assert(m&&/CONFIG-STOP-AUTO-FIRST/.test(m.body)&&/Auto останется выключенным/.test(m.body),'plain explanation with the offer: '+JSON.stringify(m));
  assert(m.buttons.some(b=>/Остановить Auto и сохранить/.test(b.t))&&m.buttons.some(b=>/Отмена/.test(b.t)));
  assert.equal(rpcs(p).length,0,'nothing is sent before the owner agrees');
}
{ // the same with Auto off: saved at once, setup_detector only
  const p=await page({scn:'off'});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  p.T.xdU().input(el('parallel_recheck',true),{type:'input'});p.T.xdU().input(el('reserve_probe_interval',60,'number'),{type:'input'});p.T.xdU().input(el('heartbeat_quorum',true),{type:'input'});
  p.modals.length=0;await p.T.saveSection('xdet');await flush();
  assert(!p.modals.length);const r=rpcs(p);assert.equal(r.length,1);
  assert.deepEqual(r[0].params,['parallel_recheck','reserve_probe_interval','heartbeat_quorum']);assert.deepEqual(r[0].args,[true,60,true]);
}
{ // flap damping travels with the stored recovery rules (setup_recovery), the rest in a second call
  const p=await page({scn:'off',settings:{recovery_failures:3,recovery_successes:2,recovery_cooldown:60,recovery_min_dwell:60,recovery_primary_successes:2,recovery_primary_stable:120}});
  p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  p.T.xdU().input(el('recovery_flap_model','halflife'),{type:'input'});p.T.xdU().input(el('recovery_flap_halflife',900,'number'),{type:'input'});p.T.xdU().input(el('wg_events',false),{type:'input'});
  await p.T.saveSection('xdet');await flush();
  const r=rpcs(p);assert.deepEqual(r.map(x=>x.method),['setup_recovery','setup_detector']);
  assert.deepEqual(r[0].params,['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','rescue_stable','interval','failure_model','flap_model','flap_limit','flap_window','flap_halflife','flap_suppress','flap_reuse']);
  assert.deepEqual(r[0].args.slice(0,2),[3,2]);assert.deepEqual(r[0].args.slice(12),['halflife',2,60,900,1500,500],'unchanged flap fields keep their stored value');
  assert.deepEqual([r[1].params,r[1].args],[['wg_events'],[false]]);
}
{ // out of range: explained, nothing sent
  const p=await page({scn:'off'});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  p.T.xdU().input(el('reserve_probe_interval',19,'number'),{type:'input'});p.T.xdU().input(el('wan_recover_grace',121,'number'),{type:'input'});
  p.modals.length=0;await p.T.saveSection('xdet');await flush();
  const m=p.modals[0];assert(m&&/Резервное|Редкие проверки резерва — 0 или 20–120 с/.test(strip(m.body))&&/Ожидание после возврата WAN — 0–120 с/.test(strip(m.body))&&/SETUP-RANGE/.test(m.body),strip(m&&m.body||''));
  assert.equal(rpcs(p).length,0);
  p.T.XD.ed={reserve_probe_interval:NaN};p.modals.length=0;assert.equal(p.T.xdU().prep(),null);assert(p.modals.length,'an empty number field is explained');
  p.T.XD.ed={reserve_probe_interval:0};assert.equal(p.T.xdU().prep(),null,'0 is the default: nothing to save');
}
{ // a refusal of the router is shown with its code and nothing is lost
  const p=await page({scn:'off',answers:{setup_detector:()=>({saved:false,code:'CONFIG-STOP-AUTO-FIRST'})}});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  p.T.xdU().input(el('probe_spread',false),{type:'input'});p.modals.length=0;await p.T.saveSection('xdet');await flush();
  assert(p.modals.some(m=>/Не сохранено/.test(m.title)&&/CONFIG-STOP-AUTO-FIRST/.test(m.body)));assert.equal(p.T.XD.ed.probe_spread,false,'the edit stays for another try');
  const q=await page({scn:'off',answers:{setup_recovery:()=>({saved:false,code:'SETUP-SAVE-FAILED'})}});q.T.HV.open['sec-xdet']=true;q.T.settingsA();await flush();q.T.snap();
  q.T.xdU().input(el('recovery_flap_limit',3,'number'),{type:'input'});q.modals.length=0;await q.T.saveSection('xdet');await flush();
  assert(q.modals.some(m=>/SETUP-SAVE-FAILED/.test(m.body)),'flap save refused by an old writer: the code, not a silent failure');
}
{ // discard
  const p=await page({scn:'off'});p.T.HV.open['sec-xdet']=true;p.T.settingsA();await flush();p.T.snap();
  p.T.xdU().input(el('wg_events',false),{type:'input'});assert.equal(p.T.xdU().changed().length,1);
}
console.log('PASS: saving - changed fields only, setup_recovery for flap, setup_detector for the rest, stop offered not failed, range errors explained, refusals shown');

// ---------- the fast end of the master slider ----------
{
  const p=await page();const A=p.T.advAt;
  assert.deepEqual([A(-0.1).t,A(-0.15).t,A(-0.2).t,A(-0.3).t,A(-0.7).t,A(-0.05).t,A(-0.8).t,A(0).t,A(0.5).t],[-0.1,-0.1,-0.2,-0.3,-0.7,0,-0.7,0,0.5],'steps, never interpolated');
  assert.equal(A(-0.2).p.cons_f,2);assert.equal(A(-0.1).p.cons_f,3);assert.equal(A(-0.5).p.beat_k,5);assert.equal(A(-0.7).p.dense_interval,3);
  assert.equal(A(-0.2).m.downtime_s_day,raw.fast_anchors[1].m[0]);assert.equal(A(-0.05).p.cons_f,undefined);
}
for(const lang of ['ru','en']){ // fast off: locked, with the switch to open it
  const p=await page({lang});const html=p.T.advSectionBody();const text=strip(html);
  assert.equal((html.match(/data-act="advlock"/g)||[]).length,7,'all seven fast positions are locked');assert(!html.includes('data-act="advpos"'));
  assert(html.includes('data-act="advfast" aria-checked="false"')&&html.includes('data-act="advturbo"'));
  assert(text.includes(lang==='ru'?'Быстрый сегмент −0,1 … −0,2 (администратор)':'Fast segment −0.1 … −0.2 (administrator)'));
  assert(text.includes('🔒'));
  p.toasts.length=0;p.T.advClick('advlock',{dataset:{t:'-0.1'}});assert(p.toasts.length,'a locked fast point explains what to do');assert.equal(rpcs(p).length,0);
  // the switch: the router is told, the position is not changed
  await p.T.advClick('advfast',{dataset:{}});await flush();
  const r=p.calls.filter(c=>c.method==='advisor_settings');assert.deepEqual([r[0].params,r[0].args],[['mode','window','fast'],['advice',7,true]]);assert(!p.calls.some(c=>c.method==='advisor_apply'));
}
{ // fast on: -0.1 / -0.2 open, turbo points stay locked
  const p=await page({adv:{current:{fast:true}}});const html=p.T.advSectionBody();
  assert.equal((html.match(/data-act="advpos"/g)||[]).length,2,'-0.1 and -0.2');assert.equal((html.match(/data-act="advlock"/g)||[]).length,5,'turbo points locked');
  assert(html.includes('data-act="advfast" aria-checked="true"'));
  p.T.advClick('advpos',{dataset:{t:'-0.2'}});assert.equal(p.T.ADV.t,-0.2);
  let h=p.T.advSectionBody();assert(h.includes('aria-pressed="true"')&&strip(h).includes('t = -0,20')&&strip(h).includes('быстрый сегмент'));
  assert(h.includes('value="0"'),'the main slider stays 0..1');
  assert(strip(h).includes('уход при 2 ошибках подряд')&&strip(h).includes('плотная проба 4 с'),'the extra rule of the position is shown');
  assert(strip(h).includes('Ожидаемо'),'the expectation is shown for the fast position');assert(/class="anc fast"/.test(h),'the available fast anchors are on the chart');
  await p.T.advClick('advapply',{dataset:{}});await flush();
  const a=p.calls.filter(c=>c.method==='advisor_apply');assert.deepEqual([a[0].params,a[0].args],[['t'],[-0.2]]);
  // a router that is on a fast position shows it
  const q=await page({adv:{current:{fast:true,t_ref:-0.1,slider_t:-0.1,attached:true,nearest_t:-0.1}}});
  assert(strip(q.T.advCardHTML()).includes('t = -0,10 · быстрый сегмент'));
  assert(/value="0"/.test(q.T.advSectionBody()));
}
{ // administrator switch off again: the router is told (it moves the position back in a calm moment)
  const p=await page({adv:{current:{fast:true}}});await p.T.advClick('advfast',{dataset:{}});await flush();
  const r=p.calls.filter(c=>c.method==='advisor_settings');assert.deepEqual([r[0].params,r[0].args],[['mode','window','fast'],['advice',7,false]]);
}
{ // the mode Auto and the previous rule: the fast positions are not selectable
  const p=await page({adv:{mode:'auto',current:{fast:true}}});const html=p.T.advSectionBody();
  assert.equal((html.match(/data-act="advpos"[^>]*disabled/g)||[]).length,2);
  const o=await page({adv:{current:{failure_model:'consecutive',fast:true}}});assert(!o.T.advSectionBody().includes('data-act="advfast"'),'the previous rule: no fast segment');
}
console.log('PASS: fast segment - steps -0.1/-0.2 behind the administrator switch, shown on the slider panel and the chart, apply sends t, locked states explained');

// ---------- turbo: locked until the acknowledgement phrase ----------
for(const lang of ['ru','en']){
  const p=await page({lang,adv:{current:{fast:true}}});
  p.T.advClick('advlock',{dataset:{t:'-0.5'}});
  const m=p.modals[p.modals.length-1];assert(m,'the locked turbo point opens the unlock dialog');
  const body=strip(m.body);
  assert(body.includes(lang==='ru'?'до ~8 в сутки':'up to ~8 a day'),'plain warning: up to ~8 unnecessary switches a day');
  assert(body.includes(lang==='ru'?'минимум простоя, допускаю до ~8 лишних уходов в сутки':'minimum downtime, i accept up to ~8 extra switches a day'),'the phrase is shown');
  assert(m.body.includes('id="adv-ack"'));const go=m.buttons.find(b=>b.id==='adv-ackgo');assert(go&&go.disabled===true,'the button starts disabled');
  assert.equal(rpcs(p).length,0);
  const u=p.T.xdU();
  for(const ok of ['минимум простоя, допускаю до ~8 лишних уходов в сутки','Минимум простоя допускаю до 8 лишних уходов в сутки','  МИНИМУМ  простоя,  допускаю до ~8 лишних уходов в сутки. ','minimum downtime, I accept up to ~8 extra switches a day'])assert(u.ackOk(ok),ok);
  for(const bad of ['','минимум простоя','допускаю до ~6 лишних уходов в сутки','минимум простоя, допускаю до ~8 лишних уходов','минимум простоя, допускаю до ~5 лишних уходов в сутки','minimum downtime, i accept up to ~5 extra switches a day','yes','minimum-downtime-up-to-8-extra-switches-a-day'])assert(!u.ackOk(bad),bad);
  go.fn();await flush();
  const r=p.calls.filter(c=>c.method==='advisor_settings');
  assert.deepEqual([r[0].params,r[0].args],[['mode','window','turbo','turbo_ack'],['advice',7,true,'minimum-downtime-up-to-8-extra-switches-a-day']],'the explicit acknowledgement goes with the request');
}
{ // the input enables the button; a wrong phrase keeps it off
  const p=await page({adv:{current:{fast:true}}});p.T.advClick('advturbo',{dataset:{}});
  const btn={disabled:true};
  p.T.HV.root={contains:()=>true,querySelector:sel=>sel==='#adv-ackgo'?btn:null};
  assert(p.T.advInput({id:'adv-ack',value:'минимум простоя, допускаю до ~8 лишних уходов в сутки'}));assert.equal(btn.disabled,false);
  p.T.advInput({id:'adv-ack',value:'минимум'});assert.equal(btn.disabled,true);
}
{ // turbo on: -0.3 ... -0.7 open, switch off available; selecting sends t
  const p=await page({adv:{current:{fast:true,turbo:true}}});const html=p.T.advSectionBody();
  assert.equal((html.match(/data-act="advpos"/g)||[]).length,7);assert(!html.includes('data-act="advlock"')&&!html.includes('data-act="advturbo"'));
  assert(strip(html).includes('Турбо включено')&&html.includes('data-act="advturbooff"'));
  p.T.advClick('advpos',{dataset:{t:'-0.7'}});assert.equal(p.T.ADV.t,-0.7);
  assert(strip(p.T.advSectionBody()).includes('плотная проба 3 с'));
  await p.T.advClick('advapply',{dataset:{}});await flush();assert.deepEqual(p.calls.filter(c=>c.method==='advisor_apply')[0].args,[-0.7]);
  await p.T.advClick('advturbooff',{dataset:{}});await flush();
  const r=p.calls.filter(c=>c.method==='advisor_settings');assert.deepEqual([r[0].params,r[0].args],[['mode','window','turbo'],['advice',7,false]]);
}
{ // a router that refuses shows its code; nothing else changes
  const p=await page({adv:{current:{fast:true}},answers:{advisor_settings:()=>({saved:false,code:'ADVISOR-BUSY-SWITCH'})}});
  assert(p.T.advSectionBody().includes('Уверенность модели'),'the table explanations come from the optional module');
  await p.T.advClick('advfast',{dataset:{}});await flush();assert(p.modals.some(m=>/ADVISOR-BUSY-SWITCH/.test(m.body)));
}
console.log('PASS: turbo - points locked, warning about ~8 unnecessary switches a day, phrase check RU/EN, turbo_ack sent, unlocked points apply, switch off');

// ---------- recovery disclosure: the renderer and explanations are optional; calculations remain eager ----------
for(const lang of ['ru','en']){
  const p=await page({lang,cold:true});let requested=0;
  p.c.L.require=()=>{requested++;return Promise.resolve({create:()=>api});};
  assert.equal(requested,0,'closed recovery disclosure loads nothing');
  const before=rpcs(p).length;
  assert(p.T.recStatsHTML().includes(lang==='ru'?'Загрузка…':'Loading…'));
  await flush();p.T.snap();
  const html=p.T.recStatsHTML();assert.equal(requested,1);assert(html.includes('data-act="recper"'));
  assert(strip(html).includes(lang==='ru'?'Измерений времени восстановления (n)':'Recovery-time samples (n)'));
  assert(strip(html).includes(lang==='ru'?'P95 (оценка) — 95-й процентиль самой выборки, а не гарантия':'P95 (estimate) is the 95th percentile of the sample itself, not a guarantee'),'F-59: the estimate is not presented as a guarantee');
  assert.equal(rpcs(p).length,before,'rendering recovery statistics sends no settings or control RPC');
}
{
  const p=await page({cold:true});let attempts=0;
  let retries=0;p.c.RECOVERY_TEST_API=api;
  // F-77 (CSP): the cached name keeps failing; Retry asks L.require for the same file under a fresh name (no eval)
  p.c.L.require=name=>/^homensai-vpn\.help[0-9]+$/.test(name)?(attempts++,Promise.reject(Error('cached failure'))):(retries++,Promise.resolve({create:()=>api}));
  p.T.recStatsHTML();await flush();
  const failed=p.T.recStatsHTML();assert(failed.includes('UI-HELP-LOAD-FAILED')&&failed.includes('data-act="helpretry"'));
  p.T.recStatsHTML();assert.equal(attempts,1,'polling does not repeat a cached failure');
  const retry={dataset:{act:'helpretry'},getAttribute:()=>null};p.T.HV.root={contains:()=>true};
  p.T.onClick({target:{closest:()=>retry},preventDefault(){}});p.T.HV.root=null;
  await flush();assert.equal(retries,1);assert(p.T.recStatsHTML().includes('data-act="recper"'),'Retry restores the recovery table');
}
assert(!pageSource().includes('P95 (estimate) is the 95th percentile of the sample itself')&&moduleText.includes('P95 (estimate) is the 95th percentile of the sample itself'),'long explanation belongs only to the optional module');
console.log('PASS: recovery disclosure lazy loading, numeric table, RU/EN explanation, no writes, cached failure and actual Retry');

// ---------- layout rules ----------
{
  const css=fs.readFileSync(CSS,'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
  assert(/\.hvx \.fastseg \.btn[^{]*\{[^}]*min-height:44px/.test(css),'fast positions: 44 px');
  assert(/\.hvx \.xdf \.tg::before\{[^}]*inset:-5px 0/.test(css)&&/\.f label\{[^}]*min-height:44px/.test(css.replace(/\.hvx /g,'')),'switch and label: 44 px areas');
  assert(/\.hvx \.f input\[type=number\][^{]*\{[^}]*min-height:44px/.test(css),'number and choice fields: 44 px');
  assert(/\.hvx \[data-secid="xdet"\] \.savebar \.btn\{min-height:44px\}/.test(css));
  assert(!/overflow-x:\s*scroll/.test(css.slice(css.indexOf('.xdh'))),'no forced horizontal scroll');
  const src=pageSource();assert(!src.includes('Загрузка описаний'),'the field texts are not in the main module');
  assert(!src.includes('Поля с пометкой «нужен выключенный Auto»')&&!src.includes('минимум простоя, допускаю'),'texts stay in the optional module');
  assert(src.includes('Для эксперта → Детектор и датчики'),'only the title is eager');
  const html=load({lang:'ru'});html.T.snap();
  const attr=html.T.footerHTML();assert(/Serhii Khomenko|homensai\.com/.test(attr)&&/data-attribution/.test(attr),'owner attributes stay in the footer');
}
console.log('PASS: 44 px tap areas, no scroll rule, owner attributes, texts only in the optional module');
})().catch(e=>{console.error(e);process.exit(1);});
