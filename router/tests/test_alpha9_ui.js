// 2.1.0-alpha9 UI (04.11.2026) on the SHIPPED page: the auto-adaptation card of the simple view, the expert settings
// (mode Авто / Совет / Вручную, window 1/7/30, master slider with the live chart, «Ожидаемо», the table of all variables,
// fine tuning that detaches the slider and «Привязать к ползунку», safety rules), the 5-step training (lazy module), the
// recovery time with the honest P95, the WAN diagnosis and server key pins with «Принять новый ключ», the low importance
// of a planned reboot. Single source: state from status.network_advisor, only the curve from rpc advisor.
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const {load,strip,pageSource,CSS,ROOT,app}=require('./approved_page');
const src=pageSource(),css=fs.readFileSync(CSS,'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
const raw=JSON.parse(fs.readFileSync(path.join(ROOT,'router/files/usr/lib/homensai-vpn/slider_curve.json'),'utf8'));
const curve={version:raw.version,params:raw.params,metrics:raw.metrics,anchors:raw.anchors.map(a=>({t:a.t,p:a.p,m:a.m})),alpha8:raw.alpha8};
const flush=()=>new Promise(r=>setTimeout(r,25));
function advisor(over){
  const base={mode:'advice',window_days:7,curve_version:1,
    current:{t_ref:0.5,slider_t:0.5,attached:true,label:'slider',nearest_t:0.5,failure_model:'hmm',theta:0.6,dur_b:5,pg:0.95,primary_stable:120,rescue_stable:10},
    recommendation:{state:'shift',t:0.7,best_t:0.7,method:'golden',effect:{saving_pct:7.5,downtime_s_day:-1.5,unnecessary_per_day:0.1},predicted:null,
      reason_ru:'Рекомендовано на основании 7 дней: обрывов основного 14 (медиана 9 с).',reason_en:'Recommended based on 7 days: 14 outages of the primary (median 9 s).',
      events:16,days_used:7,counts:{natural:14,loss_episodes:1,flaps:1,reserve_failures:0},generated:1700000000,window_days:7},
    journal:{days:7,window_days:7,tunnels:{},pair:{switches:2,returns:2,unnecessary:1}},
    last_change:{time:1700000000,source:'auto',from:0.4,to:0.5,params:{},reason_ru:'Сдвиг к «Без лишних переключений».',reason_en:'Moved toward "No unnecessary switches".'}};
  return Object.assign(base,over||{},{current:Object.assign(base.current,(over||{}).current||{})});
}
function page(opts){
  opts=opts||{};
  const p=load({lang:opts.lang||'ru',storage:opts.storage,answers:Object.assign({advisor:()=>({curve})},opts.answers||{}),
    mutate:({status})=>{status.network_advisor=opts.adv===null?undefined:advisor(opts.adv);if(opts.status)opts.status(status);}});
  p.c.HV_FIXTURE_ADVISOR_OFF=true;  // the preview fixture's alpha9 scenes stay out: this test sets the fields and answers
  p.T.snap();if(opts.adv!==null)p.T.advCardHTML();return p;  // the first paint asks for the curve once
}

(async()=>{
// ---------- simple view: the card, before and after the curve arrives ----------
for(const lang of ['ru','en']){
  const p=page({lang});
  let card=p.T.advCardHTML();
  assert(card.includes(lang==='ru'?'Кривая загружается':'Loading the curve'),'curve not loaded yet: honest placeholder '+lang);
  assert.deepEqual(p.calls.filter(c=>c.method==='advisor').map(c=>c.args),[[]],'rpc advisor once, no arguments');
  await flush();p.T.snap();card=p.T.advCardHTML();
  assert(/<svg class="advchart"/.test(card)&&card.includes('class="now"'),'small chart with the current point '+lang);
  const text=strip(card);
  for(const s of lang==='ru'?['Автоподстройка: Совет + «Применить»','t = 0,50','Последнее изменение','Сдвиг к «Без лишних переключений».','Ожидаемо','Настроить (для эксперта)']:
                              ['Auto-adaptation: Advice + Apply','t = 0.50','Last change','Moved toward No unnecessary switches','Expected','Adjust (expert)'])
    assert(text.includes(s),lang+' card: '+s+' in '+text);
  assert(/class="lamp l g"/.test(card),'green lamp with data');
  p.T.advCardHTML();assert.equal(p.calls.filter(c=>c.method==='advisor').length,1,'the curve is read once per page');
}
{ // «мало данных»: yellow lamp and the router's own reason
  const p=page({adv:{recommendation:{state:'few-data',events:2,days_used:3,reason_ru:'Мало данных: 2 события за 3 дня (нужно не меньше 5).',reason_en:'Not enough data: 2 events in 3 days (at least 5 needed).'}}});
  await flush();p.T.snap();const card=p.T.advCardHTML();
  assert(/class="lamp l y"/.test(card)&&strip(card).includes('Мало данных: 2 события за 3 дня (нужно не меньше 5).')&&!strip(card).includes('Мало данных — действуют'),'few data');
}
{ // an older monitor without the field: no invented state
  const p=page({adv:null});const card=p.T.advCardHTML();
  assert(strip(card).includes('Роутер пока не сообщает её состояние')&&!p.calls.some(c=>c.method==='advisor'),'no field: no curve request, honest text');
  assert(strip(p.T.advSectionBody()).includes('Настройки недоступны'));
}
{ // the card sits in the left golden column of the home page and is a live binding
  const p=page();const home=p.T.homeA();
  assert(/<section class="card advcard" data-g="advisor" data-b="adv\.card"><\/section><\/div>/.test(home),'card in the left column');
  assert(typeof p.T.B['adv.card']==='function'&&typeof p.T.B.sensors==='function');
}
console.log('PASS: simple view card «Автоподстройка» - state, point on the small chart, last change and reason, few data, RU/EN, one curve read');

// ---------- expert settings ----------
{
  const p=page();await flush();p.T.snap();
  const settings=p.T.settingsA();
  assert(/<h2 class="grp">Для эксперта<\/h2><details class="sec" id="sec-adv"/.test(settings),'first expert section of the simple view');
  assert(p.T.tabs.auto().includes('id="sec-adv"'),'console Auto tab has it too');
  let body=p.T.advSectionBody();
  for(const m of ['auto','advice','manual'])assert(body.includes('data-act="advmode" data-m="'+m+'"'),'mode '+m);
  assert(body.includes('data-m="advice" aria-pressed="true"')&&body.includes('data-w="7" aria-pressed="true"'),'current mode and window pressed');
  for(const w of [1,7,30])assert(body.includes('data-act="advwin" data-w="'+w+'"'),'window '+w);
  assert(/<input class="slider" type="range" id="adv-t" min="0" max="1" step="0\.01" value="0\.5" aria-label="Быстрая реакция — без лишних переключений">/.test(body),'master slider enabled in advice mode');
  assert(body.includes('data-act="advrec"')&&strip(body).includes('Совет: Рекомендовано на основании 7 дней'),'advice with Apply');
  assert(body.includes('<span>0,25</span><span>0,5</span><span>0,75</span>'),'RU decimal comma on the slider ticks');
  { const e=page({lang:'en'});await flush();e.T.snap();const b=e.T.advSectionBody();
    assert(b.includes('<span>0.25</span><span>0.5</span><span>0.75</span>'),'EN decimal point on the slider ticks');
    for(const part of [b,e.T.advCardHTML(),e.T.recStatsHTML(),e.T.sensorsHTML()])assert(!/[А-Яа-яЁё]/.test(strip(part)),'no Cyrillic in the EN alpha9 parts'); }
  assert(/<svg class="advchart" viewBox="0 0 640 300"/.test(body)&&body.includes('class="mk def"')&&(body.match(/class="mk pro"/g)||[]).length===3,'big chart: default and named-position markers');
  assert(body.includes('class="halo"')&&body.includes('class="pt"'),'the moving point');
  const text=strip(body);
  for(const s of ['Быстрая реакция','Без лишних переключений','Ожидаемо','Все переменные','Порог ухода θ','Длина «короткого обрыва» в модели','Порог возврата P(здоров)','Стабильность основного перед возвратом','Возврат с упавшего резерва через','Сейчас на роутере','По умолчанию','Тонкая настройка','Правила безопасности'])
    assert(text.includes(s),'expert: '+s);
  assert(!/td class="num chg"/.test(body),'nothing highlighted while the slider stands at the router value');
  // dragging: t 0.9 -> P(G) 0.99, primary_stable 300, rescue 20 differ from the router: highlighted with arrows
  p.T.ADV.t=0.9;body=p.T.advSectionBody();
  const chg=(body.match(/<td class="num chg">[^<]*/g)||[]).map(x=>x.replace('<td class="num chg">',''));
  assert(chg.includes('0,99')&&chg.includes('300 с')&&chg.includes('20 с')&&chg.includes('8,0 с'),'changed values highlighted: '+chg);
  assert(body.includes('<span class="ar" aria-label="изменится">↑</span>'),'arrow');
  assert(body.includes('data-act="advapply"')&&!/data-act="advapply" disabled/.test(body),'apply enabled for a moved slider');
  // the same interpolation as advisor.interpolate (rounded to the steps)
  const at=p.T.advAt(0.75);assert.deepEqual(at.p,{theta:0.6,dur_b:8,losses:2,pg:0.95,primary_stable:240,rescue_stable:15},'advAt(0.75)');
  // advInput repaints only the moving parts
  p.T.ADV.t=null;assert.equal(p.T.advInput({id:'adv-t',value:'0.3',dataset:{}}),true);assert.equal(p.T.ADV.t,0.3);
  // auto mode: the system moves the slider - disabled, explained
  const q=page({adv:{mode:'auto'}});await flush();q.T.snap();const ab=q.T.advSectionBody();
  assert(/id="adv-t"[^>]* disabled>/.test(ab)&&strip(ab).includes('«Авто»: ползунок двигает система'),'auto: slider disabled with the reason');
  // consecutive detector: inactive with its code
  const r=page({adv:{current:{failure_model:'consecutive',attached:false,label:'preset'}}});await flush();r.T.snap();const cb=r.T.advSectionBody();
  assert(cb.includes('data-code="ADVISOR-MODEL-CONSECUTIVE"')&&/id="adv-t"[^>]* disabled>/.test(cb)&&/data-act="advfine" aria-checked="false" disabled/.test(cb),'consecutive: inactive');
  // custom values: «Пользовательская», detached, «Привязать к ползунку» to the nearest anchor
  const u=page({adv:{current:{attached:false,label:'custom',slider_t:null,t_ref:0.6,nearest_t:0.6,theta:0.62}}});await flush();u.T.snap();const ub=u.T.advSectionBody();
  assert(strip(ub).includes('Пользовательская')&&ub.includes('data-act="advrebind"')&&strip(ub).includes('Привязать к ползунку (t = 0,60)')&&/id="adv-t"[^>]* disabled>/.test(ub),'custom: detached');
}
console.log('PASS: expert settings - modes, window, master slider with the moving point, default and named markers, «Ожидаемо», table with changed values highlighted, auto/consecutive/custom states');

// ---------- fine tuning and safety in the page ----------
{
  const p=page({adv:{mode:'manual'}});await flush();p.T.snap();
  await p.T.advClick('advfine',{dataset:{}});
  assert.deepEqual(p.T.ADV.fine,{theta:0.6,dur_b:5,pg:0.95});
  let body=p.T.advSectionBody();
  for(const k of ['theta','dur_b','pg'])assert(body.includes('data-advf="'+k+'"'),'fine slider '+k);
  assert(/data-advf="theta" min="0\.5" max="0\.99" step="0\.01"/.test(body)&&/data-advf="dur_b" min="1" max="15" step="0\.5"/.test(body),'safe ranges of the router');
  assert(strip(body).includes('Пользовательская')&&/id="adv-t"[^>]* disabled>/.test(body),'any fine value detaches the master');
  // θ above P(G): P(G) follows with the explanation; P(G) below θ is clamped
  p.T.advInput({dataset:{advf:'theta'},value:'0.97'});assert.equal(p.T.ADV.fine.pg,0.97);assert(p.T.ADV.fineWhy.includes('P(G) поднят до θ'));
  p.T.advInput({dataset:{advf:'pg'},value:'0.5'});assert.equal(p.T.ADV.fine.pg,0.97,'P(G) never below θ');
  p.T.advInput({dataset:{advf:'dur_b'},value:'99'});assert.equal(p.T.ADV.fine.dur_b,15,'clamped to the bound');
  await p.T.advClick('advsave',{dataset:{}});await flush();
  const save=p.calls.filter(c=>c.method==='advisor_settings').pop();
  assert.deepEqual([save.params,save.args],[['mode','window','theta','dur_b','pg'],['manual',7,0.97,15,0.97]],'own values saved through advisor_settings');
}
{ // modes, window, apply, advice, rebind: the RPCs and their arguments; refusal codes shown, nothing assumed
  const p=page();await flush();p.T.snap();
  await p.T.advClick('advmode',{dataset:{m:'auto'}});await flush();
  await p.T.advClick('advwin',{dataset:{w:'30'}});await flush();
  p.T.ADV.t=0.8;await p.T.advClick('advapply',{dataset:{}});await flush();
  await p.T.advClick('advrec',{dataset:{}});await flush();
  const got=p.calls.filter(c=>/^advisor_/.test(c.method)).map(c=>[c.method,c.params,c.args]);
  assert.deepEqual(got,[['advisor_settings',['mode','window'],['auto',7]],['advisor_settings',['mode','window'],['advice',30]],['advisor_apply',['t'],[0.8]],['advisor_apply',[],[]]]);
  assert.equal(p.methods().filter(m=>/native_start|terms_accept/.test(m)).length,0,'never starts Auto, never accepts terms');
  const q=page({answers:{advisor_apply:()=>({saved:false,code:'ADVISOR-BUSY-SWITCH'})}});await flush();q.T.snap();
  q.T.ADV.t=0.8;await q.T.advClick('advapply',{dataset:{}});await flush();
  assert(q.modals.some(m=>m.body.includes('data-code="ADVISOR-BUSY-SWITCH"')),'the router refusal code is shown');
  const r=page({adv:{current:{attached:false,label:'custom',slider_t:null,nearest_t:0.6}}});await flush();r.T.snap();
  await r.T.advClick('advrebind',{dataset:{}});await flush();
  assert.deepEqual(r.calls.filter(c=>c.method==='advisor_apply').map(c=>c.args),[[0.6]],'rebind = apply the nearest anchor');
}
console.log('PASS: fine tuning detaches, «Привязать к ползунку», P(G) ≥ θ and the bounds in the page, RPC arguments, refusal codes, no Auto start');

// ---------- training: offered once, reachable from help, texts in the optional module ----------
{
  const p=page();await flush();p.T.snap();
  assert(p.T.advCardHTML().includes('data-act="advtour" data-i="0"')&&p.T.advCardHTML().includes('data-act="advnotour"'),'offered while never seen');
  p.T.advClick('advnotour',{dataset:{}});
  assert.equal(p.stored['homensai-vpn-advisor-tour'],'later');assert(!p.T.advCardHTML().includes('data-act="advnotour"'),'offered once');
  assert(p.T.settingsA().includes('data-act="advtour" data-i="0"')&&p.T.tabs.sys().includes('data-act="advtour" data-i="0"'),'reachable from help in both views');
  const q=page({storage:{'homensai-vpn-advisor-tour':'seen'}});assert(!q.T.advCardHTML().includes('data-act="advnotour"'));
  // the lazy module carries the five steps in both languages
  const ctx=vm.createContext({});const mod=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m))),'utf8');
  assert(/advTour:ADV_TOUR[,}]/.test(mod),'the help module exports the training');
  const tour=vm.runInContext(mod.slice(mod.indexOf('var ADV_TOUR='),mod.indexOf('}];',mod.indexOf('var ADV_TOUR='))+3)+';ADV_TOUR',ctx);
  assert.equal(tour.length,5);
  assert.deepEqual(tour.map(s=>s.h[1]),['Две цели, которые тянут в разные стороны','Что такое кривая','Точка и таблица','Как решает автоподстройка','Как вмешаться и вернуть автоматику']);
  tour.forEach(s=>{assert(s.b[0]&&s.b[1]&&!/[А-Яа-яЁё]/.test(s.b[0]+s.h[0]),'EN text clean');});
  assert(!src.includes('Две цели, которые тянут в разные стороны'),'the training texts are not in the main module');
  // the modal opens through the help module; without it the honest code
  await p.T.advTour(0);await flush();assert(p.modals.some(m=>m.body.includes('UI-HELP-LOAD-FAILED')),'help module unavailable in the vm: code shown');
}
console.log('PASS: training - 5 steps RU/EN in the optional module, offered once, reachable from help');

// ---------- recovery time: honest P95 ----------
{
  const mod=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m))),'utf8');
  const from=mod.indexOf('var EXPERT_GROUPS='),end='act:act,hint:hint};\n};',to=mod.indexOf(end,from)+end.length;
  const expertUI=vm.runInNewContext(mod.slice(from,to)+';EXPERT_UI',{});
  async function loadRecovery(p){p.c.L.require=()=>Promise.resolve({create:()=>({expertUI,helpTopics:()=>[]})});assert(/Loading|Загрузка/.test(p.T.recStatsHTML()));await flush();p.T.snap();}
  const now=Date.now()/1000;
  const mk=(n)=>({available:true,timezone:'Europe/Berlin',events:[].concat(...Array.from({length:n},(_,i)=>{const s=now-600*(n-i);return [
    {sequence:2*i+1,time:s,state:'APPLYING',source:'wireguard:peer_2002',target:'openvpn:1_2020',codes:['SOURCE-FAILED'],trial:false},
    {sequence:2*i+2,time:s+3+i%5,state:'COMMITTED',source:'wireguard:peer_2002',target:'openvpn:1_2020',codes:['SOURCE-FAILED'],trial:false}];}))});
  const few=page({status:s=>{s.native_history=mk(6);}});few.T.ADV.per='month';await loadRecovery(few);
  let h=few.T.recStatsHTML(),text=strip(h);
  assert(text.includes('≈P95')&&text.includes('мало данных: n=6, нужно ≥59')&&/Максимум \S+ с \(≥\d+ %\)/.test(text),'few samples: ≈P95 and the max coverage: '+text);
  assert(text.includes('с 95 % уверенностью'),'coverage wording');
  const many=page({lang:'en',status:s=>{s.native_history=mk(60);}});many.T.ADV.per='month';await loadRecovery(many);
  text=strip(many.T.recStatsHTML());
  assert(text.includes('Recovery-time samples (n) 60')&&/ P95 \(estimate\) \d+\.\d s P95 upper bound, 95 % confidence \d+\.\d s Maximum \d+\.\d s P95 \(estimate\) is the 95th percentile/.test(text)&&!/≈\d/.test(text)&&!text.includes('too few'),'n >= 59: the estimate, its upper bound as a separate row, a plain maximum: '+text);
  assert(few.T.tabs.auto().includes('data-lazy="rec"')&&few.T.homeA().includes('data-lazy="rec"'),'both views offer it');
}
console.log('PASS: recovery time - median, ≈P95 below n=59 with the max coverage, plain P95 from n=59 (the rule of scripts/honest_stats.py)');

// ---------- sensors ----------
{
  const p=page({status:s=>{
    s.wan_diagnosis={time:Date.now()/1000,enabled:true,verdict:'WAN',confidence:930,code:'WAN-DOWN',hold:true,recovering:false,down_since:Date.now()/1000-40};
    s.server_keys={mode:'warn',pinned:1,changed:[{profile:'wireguard:peer_2002',host:'nl-ams-2002.example',pinned:'wg:OLDKEY=',observed:'wg:NEWKEY=',changed_at:Date.now()/1000-100}],code:'SERVER-KEY-CHANGED'};}});
  const banner=p.T.sensorBanner();
  assert(banner.includes('data-code="WAN-DOWN"')&&banner.includes('data-code="SERVER-KEY-CHANGED"')&&banner.includes('data-act="gokeys"'),'notices on every view');
  const block=p.T.sensorsHTML();
  assert(strip(block).includes('Нет интернета у провайдера (WAN)')&&block.includes('class="lamp r"'),'WAN-DOWN');
  assert(block.includes('data-act="keyaccept" data-profile="wireguard:peer_2002" data-observed="wg:NEWKEY="')&&strip(block).includes('WG · Amsterdam'),'accept button with the profile name');
  p.T.keyAccept({dataset:{profile:'wireguard:peer_2002',observed:'wg:NEWKEY='}});
  const m=p.modals.pop();assert(m.body.includes('wg:NEWKEY=')&&m.buttons.length===2);
  m.buttons[1].fn();await flush();
  assert.deepEqual(p.calls.filter(c=>c.method==='server_key_accept').map(c=>[c.params,c.args]),[[['profile','observed'],['wireguard:peer_2002','wg:NEWKEY=']]],'rpc server_key_accept with the checked key');
  const q=page({status:s=>{s.wan_diagnosis={time:Date.now()/1000,enabled:true,code:'WAN-RECOVERING',recovering:true,hold:true};s.server_keys={mode:'off'};}});
  assert(q.T.sensorsHTML().includes('class="lamp y"')&&strip(q.T.sensorsHTML()).includes('выключена'),'recovering, pins off');
  assert(q.T.tabs.sys().includes('data-b="sensors"')&&q.T.settingsA().includes('data-b="sensors"'),'sensors block in both views');
}
{ // a planned reboot is a normal, low-importance event
  const p=page();const k=p.T.evKind({time:1,code:'RESTART-PLANNED-REBOOT'});
  assert.equal(k.problem,false);assert.notEqual(k.lamp,'r');assert.notEqual(k.lamp,'y');
  assert(/RESTART-CLEAN RESTART-PLANNED-REBOOT/.test(src),'severity table: low');
}
console.log('PASS: sensors - WAN-DOWN/WAN-RECOVERING, server key change with «Принять новый ключ», planned reboot of low importance');

// ---------- the wizard always has an exit and never traps (owner 04.11.2026) ----------
{
  for(const lang of ['ru','en'])for(const step of [1,2,3,4]){
    const {T}=load({scn:'first',lang});T.HV.step=step;T.snap();const w=T.wizard();
    assert(w.includes('data-act="wskip"')&&strip(w).includes(lang==='ru'?'Пропустить — открыть интерфейс':'Skip — open the interface'),'exit on step '+step+' '+lang);
  }
  // skip with Auto stopped and with Auto running: only the narrow RPC, never Auto or the terms; the wizard closes
  for(const scn of ['first','ok']){
    const p=load({scn,mutate:({settings})=>{settings.onboarding_complete=false;settings.onboarding_version=0;}});
    p.T.HV.wiz=true;p.T.snap();assert.equal(await p.T.wizardSkip(),true);await p.flush();
    assert.deepEqual(p.methods(),['setup_onboarding_skip'],'only the mark: '+scn);assert.equal(p.T.HV.wiz,false,'wizard closed: '+scn);
    assert.deepEqual(p.calls.find(c=>c.method==='setup_onboarding_skip').args,[],'no arguments');
  }
  // a refused mark still lets the person out, with the code
  const r=load({scn:'first',answers:{setup_onboarding_skip:()=>({saved:false,code:'CONFIG-RECOVERY-UNVERIFIED'})}});
  r.T.HV.wiz=true;r.T.snap();await r.T.wizardSkip();assert.equal(r.T.HV.wiz,false);assert(r.toasts.some(m=>m.includes('CONFIG-RECOVERY-UNVERIFIED')),'code shown');
  // an already finished router: the exit only closes
  const c=load({scn:'ok'});c.T.HV.wiz=true;c.T.snap();await c.T.wizardSkip();assert.deepEqual(c.methods(),[]);assert.equal(c.T.HV.wiz,false);
  // forced only on a really unconfigured router
  assert.equal(load({scn:'first'}).T.wizardNeeded(),true,'nothing configured: the wizard opens');
  const off=m=>load({scn:'first',mutate:({settings,status})=>{m(settings,status);}}).T.wizardNeeded();
  assert.equal(off(s=>{s.plan_source='a';s.plan_target='b';}),false,'a configured pair: no forced wizard');
  assert.equal(off(s=>{s.plan_source_tunnel='openvpn:x';s.plan_target_tunnel='openvpn:y';}),false,'a configured tunnel pair: no forced wizard');
  assert.equal(load({scn:'ok',mutate:({settings})=>{settings.onboarding_complete=false;settings.onboarding_version=0;}}).T.wizardNeeded(),false,'Auto running: no forced wizard');
  // step 4 with Auto running offers no save that fails, it explains and leaves the exit
  const a=load({scn:'ok',mutate:({settings})=>{settings.onboarding_complete=false;settings.onboarding_version=0;}});a.T.HV.step=4;a.T.snap();const w4=a.T.wizard();
  assert(w4.includes('data-wiz-running')&&strip(w4).includes('Auto работает — настройки меняются после Stop'),'explained');
  assert(!w4.includes('data-act="wsave"')&&!w4.includes('data-act="wstart"')&&w4.includes('data-act="wskip"'),'only the exit');
  const f=load({scn:'first'});f.T.HV.step=4;f.T.snap();assert(f.T.wizard().includes('data-act="wsave"')&&!f.T.wizard().includes('data-wiz-running'),'Auto stopped: the normal step 4');
}
console.log('PASS: wizard - exit on every step in RU/EN, skip with Auto running or stopped, no trap on a refused mark, not forced over Auto or a pair, step 4 honest');

// ---------- style: owner rules ----------
assert(/\.hvx \.tgl\{[^}]*min-height:44px/.test(css)&&/\.hvx \.advslider \.slider,\.hvx \.advfine \.slider\{min-height:44px\}/.test(css)&&/\.hvx \.filters button::after\{content:"";position:absolute;inset:-5px\}/.test(css),'44 px tap areas');
assert(/@media \(prefers-reduced-motion:reduce\)\{\.hvx \.tgl \.trk,\.hvx \.tgl \.trk::after\{transition:none\}\}/.test(css),'reduced motion');
assert(/\.hvx \.scrollx\{overflow-x:auto;max-width:100%\}/.test(css)&&/\.hvx \.advchart\{width:100%;height:auto/.test(css),'no horizontal page scroll: tables scroll in their box, charts scale');
console.log('PASS: style - 44 px areas, reduced motion, no horizontal scroll');
})().catch(e=>{console.error(e);process.exit(1);});
