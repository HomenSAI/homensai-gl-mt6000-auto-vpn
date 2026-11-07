// The shipped page = the approved mockups (private/ui-variants-2026-11-03: A «Простой», D «Пульт», wizard of C).
// Safety and owner rules on the real built module: attribution on every view, lamps, one source of readings with
// "no fresh data", terms never accepted and Auto never started without the owner, the same router calls as before,
// RU by default and clean EN, the view switch next to the language, and the module size.
'use strict';
const fs=require('fs'),assert=require('assert');
const {load,strip,pageSource,CSS,app}=require('./approved_page');
const src=pageSource(),css=fs.readFileSync(CSS,'utf8');
const CYR=/[А-Яа-яЁё]/;

(async()=>{
// ---------- Owner attributes on every view ----------
for(const lang of ['ru','en']){
  const {T,c}=load({lang});
  const foot=strip(T.footerHTML()),brand=T.brandHTML(),v=T.VER();
  for(const part of ['HomenS .AI Auto VPN','GL.iNet GL-MT6000 · Flint 2',lang==='ru'?'Разработчик · Serhii Khomenko':'Developer · Serhii Khomenko',
    (lang==='ru'?'Программа ':'Program ')+app.version,'HomenS.AI Style 1.14.3','© 2026 Serhii Khomenko'])
    assert(foot.includes(part),'footer '+lang+': '+part+' in '+foot);
  assert(/href="https:\/\/homensai\.com"/.test(T.footerHTML())&&/href="https:\/\/homensai\.com"/.test(brand),'developer link');
  assert(new RegExp('class="badge-ver hv-version"[^>]*>v'+app.version.replace(/\./g,'\\.')+'<').test(brand),'header version badge');
  assert(strip(brand).includes('HomenS .AI Auto VPN')&&brand.includes('GL.iNet GL-MT6000 · Flint 2'),'product name and router model in the header');
  assert(!('page' in v),'no page module among the shown values');
}
{ // RPC down: every attribute stays, the version falls back to the page's own build value.
  const {T}=load({mutate:({status})=>{for(const k of Object.keys(status))delete status[k];status.rpc_error='RPC-UNAVAILABLE';}});
  const foot=strip(T.footerHTML());
  assert(foot.includes('Программа '+app.version)&&foot.includes('Serhii Khomenko')&&foot.includes('HomenS.AI Style'),'attribution without status');
  assert(T.brandHTML().includes('v'+app.version));
}
// Every view and the wizard are composed of header (brand + tools) and footer.
assert(src.includes("HV.root.innerHTML=hdr+main+footerHTML()+topHTML();"),'render always adds the footer');
assert(/var hdr='<header class="hdr"><div class="wrap hdr-in">'\+brandHTML\(\)/.test(src),'every view has the brand header (F1: brand and badge cells, then menu and tools)');
// No stylesheet rule hides the footer, the brand or the version badge.
const rules=[...css.replace(/\/\*[\s\S]*?\*\//g,'').matchAll(/([^{}]+)\{([^{}]*)\}/g)];
for(const [,selector,body] of rules){
  if(!/display\s*:\s*none|visibility\s*:\s*hidden/.test(body))continue;
  // The mockups drop only the small model line under the name on phones; the footer keeps the model (asserted above).
  for(const one of selector.split(','))if(!/\.hdr \.devline$/.test(one.trim()))assert(!/\.attr\b|hv-attribution|\.badge-ver|hv-version|\.brand\b|\.hdr\b/.test(one),'hidden attribute: '+one.trim());
}
assert(/\.hvx \.attr \.wrap\{display:flex/.test(css),'the footer lays out its attributes');
console.log('PASS: owner attributes (name, model, developer link, program version, Style, badge, author footer) on every view, RU and EN');

// ---------- Lamps blink: green 2.4 s, yellow 1 s, red 1.4 s, grey still, reduced motion still ----------
assert(/\.hvx \.lamp\.g\{[^}]*animation:hv-blink 2\.4s ease-in-out infinite/.test(css));
assert(/\.hvx \.lamp\.y\{[^}]*animation:hv-blink 1s ease-in-out infinite/.test(css));
assert(/\.hvx \.lamp\.r\{[^}]*animation:hv-blink 1\.4s ease-in-out infinite/.test(css));
assert(/\.hvx \.lamp\.n\{animation:none\}/.test(css));
assert(/@media \(prefers-reduced-motion:reduce\)\{\.hvx \.lamp,\.hvx \.lamp\.g,\.hvx \.lamp\.y,\.hvx \.lamp\.r\{animation:none!important\}/.test(css));
console.log('PASS: lamps blink green 2.4 s, yellow 1 s, red 1.4 s; grey and reduced motion are still');

// ---------- One source of readings; stale data says "no fresh data" ----------
{
  const {T}=load({scn:'ok'});const o=T.overall(),p=T.reading('primary'),r=T.reading('reserve');
  assert.equal(o.title,'Интернет работает');assert.equal(o.lamp,'g');assert.equal(T.autoIndicator().text,'Auto включён');
  assert.equal(p.state,'ok');assert.equal(p.ms,38);assert(/проверено \d+ с назад/.test(p.ageText));
  assert.equal(r.ms,55);assert.equal(T.autoState().text,'Auto работает');
  const home=T.homeA(),ch=T.tabs.ch();
  for(const html of [home,ch])assert(html.includes('data-b="p.ms"')&&html.includes('data-b="ov.title"')===(html===home),'cards read the shared bindings');
}
{
  const {T}=load({scn:'stale'});const o=T.overall(),p=T.reading('primary');
  assert.equal(o.title,'Нет свежих данных');assert.equal(o.lamp,'n');
  assert.equal(p.text,'нет свежих данных');assert.equal(p.ms,null);assert.equal(p.lamp,'n');
  assert.notEqual(T.autoState().lamp,'g','stale Auto is never green');
}
{
  const {T}=load({scn:'reserve'});assert.equal(T.overall().title,'Работает через резерв');assert.equal(T.overall().lamp,'g','owner rule 07.11.2026: the internet works via the reserve = green');assert.equal(T.reading('primary').lamp,'r');
}
assert(!/setInterval\(function\(\)\{[^}]*rpc/.test(src),'the 1 s heartbeat repaints, it does not call the router');
console.log('PASS: one snapshot feeds every view; stale evidence shows "нет свежих данных", never a green lamp');

// ---------- Terms are never accepted for the owner; Auto never starts silently ----------
{
  const {T,calls,modals,methods,flush}=load({scn:'first'});
  T.homeA();T.settingsA();T.wizard();Object.values(T.tabs).forEach(f=>f());
  assert.deepEqual(methods(),[],'rendering makes no write call');
  T.HV.step=4;const w=T.wizard();
  assert.equal((w.match(/type="checkbox" class="wacc[ "]/g)||[]).length,2,'two acknowledgement boxes in the wizard');
  assert(!/class="wacc"[^>]*checked/.test(w),'wizard boxes are not pre-ticked');
  assert(/id="wstart" disabled/.test(w),'start is disabled until the owner ticks both boxes');
  T.toggleAuto();await flush();
  assert.equal(modals.length,1,'terms open in a window');const m=modals[0];
  assert.equal((m.body.match(/type="checkbox"/g)||[]).length,2);assert(!/checked/.test(m.body),'terms boxes are not pre-ticked');
  const accept=m.buttons.find(b=>b.id==='tbtn');assert(accept&&accept.disabled===true,'accept is disabled until ticked');
  assert.deepEqual(methods(),[],'opening the terms writes nothing');
  accept.fn();for(let i=0;i<10;i++)await flush();
  assert.deepEqual(methods(),['terms_accept','native_start'],'only the owner\'s press accepts the terms, then starts Auto');
  assert.deepEqual(calls.find(x=>x.method==='terms_accept').args,['2']);
  const start=calls.find(x=>x.method==='native_start');assert.deepEqual(start.params,['control_revision','request_source']);assert.deepEqual(start.args,['0123456789abcdef0123456789abcdef','manual']);
}
{ // Wizard: "Save without starting" writes the setup only; the start button needs both boxes.
  const {T,methods,flush}=load({scn:'first'});T.HV.wiz=true;T.HV.step=4;Object.assign(T.draft(),{pairP:'wireguard:peer_2002',pairR:'openvpn:1_2020'});
  const ok=await T.wizardSave(false);for(let i=0;i<5;i++)await flush();
  assert.equal(ok,true);assert.deepEqual(methods(),['setup_onboarding'],'save without starting never accepts terms or starts Auto');
}
{
  const {T,methods,flush}=load({scn:'first'});T.HV.wiz=true;T.HV.step=4;T.HV.root={contains:()=>true};
  const click=act=>T.onClick({target:{closest:()=>({dataset:{act},tagName:'BUTTON',getAttribute:()=>null})},preventDefault(){},stopPropagation(){}});
  // No boxes ticked (the vm document has none): the start press does nothing.
  T.HV.root.querySelectorAll=()=>[];click('wstart');await flush();
  assert.deepEqual(methods(),[],'unticked boxes: no call');
}
{ // Terms accepted: Auto on with one press; a second press while starting sends nothing more.
  const {T,methods,flush}=load({scn:'off'});
  T.toggleAuto();T.toggleAuto();for(let i=0;i<5;i++)await flush();
  assert.deepEqual(methods(),['native_start']);
}
{ // Stop asks first, then native_stop('manual'); unknown/stale state turns the switch into Stop (fail-safe).
  const {T,calls,modals,methods,flush}=load({scn:'ok'});
  T.toggleAuto();assert.equal(modals.length,1);assert(/Выключить Auto\?/.test(modals[0].title));assert.deepEqual(methods(),[]);
  modals[0].buttons.find(b=>/danger/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
  assert.deepEqual(methods(),['native_stop']);assert.deepEqual(calls.find(x=>x.method==='native_stop').args,['manual']);
  const stale=load({scn:'stale'});stale.T.toggleAuto();assert(/Выключить Auto\?/.test(stale.modals[0].title),'stale state offers Stop, never Start');
}
console.log('PASS: terms only by the owner (2 unticked boxes, disabled button), Auto starts only on his press, Stop is confirmed and fail-safe');

// ---------- The same router calls as before ----------
{
  const {T,calls,modals,methods,flush}=load({scn:'ok'});
  T.switchTo('reserve');assert(/Переключить на «OpenVPN · Frankfurt»\?/.test(modals[0].title));
  modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();await flush();
  const manualCall=calls.find(x=>x.method==='pair_manual');assert.deepEqual(manualCall.args.slice(0,3),['reserve','0123456789abcdef0123456789abcdef','manual']);assert.match(manualCall.args[3],/^[a-f0-9]{32}$/,'F-35: one client_request_id per click');
  T.checkNow();await flush();assert(methods().includes('scan'));
  T.HV.draft=null;T.draft().level=4;await T.saveSection('load');for(let i=0;i<5;i++)await flush();
  assert.deepEqual(calls.find(x=>x.method==='setup_probe').args,[4,true]);
  assert.deepEqual(calls.find(x=>x.method==='setup_response').params,['metric','compare','fast_switch','ping_interval']);
  assert(!methods().includes('native_start')&&!methods().includes('terms_accept'),'actions never start Auto or accept terms');
}
{ // Rules need Auto off: saving offers "Stop Auto and save", nothing is written before the owner agrees.
  const {T,modals,methods}=load({scn:'ok'});T.saveSection('rules');
  assert(/Сначала остановить Auto/.test(modals[0].title));assert.deepEqual(methods(),[]);
}
{ // Auto off: rules save through setup_recovery with the values in the old order, rescue_stable before the interval
  // (integration alpha8: the optional field of rescue-tune; failure_model is not sent, the stored model stays).
  const {T,calls,flush}=load({scn:'off'});T.HV.draft=null;T.saveSection('rules');for(let i=0;i<8;i++)await flush();
  const r=calls.find(x=>x.method==='setup_recovery');assert(r,'setup_recovery');
  assert.deepEqual(r.params,['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','rescue_stable','interval']);
  assert.deepEqual(r.args,[3,2,60,60,'healthy_primary',2,30,3,15,10,20]);
}
console.log('PASS: manual switch, check, load and rules use pair_manual/scan/setup_probe/setup_response/setup_recovery as before');

// ---------- RU by default, clean EN, the view switch next to the language ----------
{
  const {T,stored}=load({});assert.equal(T.pickLocale({}),'ru','Russian is the default');
  assert.equal(T.pickLocale({appearance_language:'en'}),'en');stored['homensai-vpn-language']='ru';assert.equal(T.pickLocale({appearance_language:'en'}),'ru','this browser\'s choice wins');
  const tools=T.toolsHTML();
  assert(/<span class="viewsw"[\s\S]*data-v="simple"[^>]*title="Вид: Простой"[\s\S]*data-v="console"[^>]*title="Вид: Пульт"[\s\S]*<\/span><button class="iconbtn" data-act="lang"/.test(tools),'two view icons right before the language button');
  assert(src.includes("VIEW_KEY='homensai-vpn-view'")&&src.includes('store.set(VIEW_KEY,HV.view)'),'the view is kept per browser');
}
{
  const {T}=load({lang:'en'});
  assert(/title="View: Simple"[\s\S]*title="View: Console"/.test(T.toolsHTML()));
  const pages=[T.homeA(),T.settingsA(),T.wizard()].concat(Object.values(T.tabs).map(f=>f()));
  T.HV.step=4;pages.push(T.wizard());
  for(const html of pages){const text=strip(html);const bad=(text.match(/\S*[А-Яа-яЁё]\S*/g)||[]).filter(w=>w!=='Русский');assert(!bad.length,'Cyrillic in EN: '+bad.slice(0,5).join(' '));}  // the language button names Russian in Russian
  for(const role of ['primary','reserve'])assert(!CYR.test(T.reading(role).text+T.reading(role).ageText));
  assert(!CYR.test(T.overall().title+T.overall().sub+T.autoState().text+T.autoIndicator().text));
}
console.log('PASS: RU by default, EN without Cyrillic, view switch «Вид: Простой / Пульт» next to the language, kept per browser');

// ---------- Boot with an empty browser profile: every view and the wizard render with header and footer ----------
for(const [scn,hash,expect] of [['ok','','class="hero'],['ok','#ch','class="tabbar'],['first','','class="wiz']]){
  const {c,inventory,status}=load({scn,hash});let html='';
  const root={className:'',set innerHTML(v){html=v;},get innerHTML(){return html;},setAttribute(){},removeAttribute(){},addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];},contains(){return false;},appendChild(){}};
  c.HVX.boot(root,[inventory,status]);
  assert(html.includes(expect),'boot '+scn+hash+' shows '+expect);
  assert(html.includes('class="attr hv-attribution"')&&html.includes('class="badge-ver hv-version"')&&html.includes('class="viewsw"'),'boot '+scn+hash+': attribution, badge, view switch');
  assert(html.includes('lang="ru"')||/Настройки|Каналы|Роутер/.test(html),'Russian by default');
}
console.log('PASS: boot with an empty browser profile renders «Простой», «Пульт» and the first-run wizard with the owner attributes');

// ---------- Size: the new main module is much smaller than the page it replaces ----------
{
  const bytes=Buffer.byteLength(src),legacy=Buffer.byteLength(fs.readFileSync('qa/legacy-page/dashboard.js','utf8'));
  // Bound: 46 % of the alpha51 baseline (1,256,446 B) and at most 66 % of the legacy page; help/codes/training stay lazy.
  // 2.1.0-alpha9: 45 -> 46 % and 60 -> 61 % for the auto-adaptation, master slider, sensors and the honest-P95 recovery
  // panel (574 758 B = 45.74 % / 60.37 %; 577 883 B before fix/ui-polish-a9, 577 193 B after it); the reasons are in test_lazy_help_ui.js next to the same bound.
  // fix/a9-ui-docs-20261106: 46 -> 48 % and 61 -> 63 % for the review fixes (escaping, locks, section drafts, one presenter for lamps and buttons)
  // fix/a9-polish-20261107: 63 -> 66 % of the legacy page, owner decision of 07.11.2026 (the page keeps the reviewed fixes, the bound follows the real size)
  // fix/a9-decisions-20261107: 48 -> 49 % of alpha51 for the owner decisions of 07.11.2026 (install reason lines, the Telegram
  // recipient show click, F-35 re-read and Retry after a lost answer): 608 900 B = 48.5 % of alpha51, 63.7 % of the legacy page;
  // the 66 % legacy bound (owner decision of 07.11.2026) is unchanged and still holds.
  assert(bytes<1256446*.49,'main module '+bytes+' B');assert(bytes<legacy*.66,'main '+bytes+' B vs legacy '+legacy+' B');
  assert(!src.includes('var LEARN_LESSONS=')&&!src.includes('var AI_PROMPT_EN='),'training and AI prompts stay in the optional module');
  assert(/var LAZY_HELP_NAME='homensai-vpn\.help[0-9]+'/.test(src));
  console.log('PASS: main module '+bytes+' B ('+Math.round(bytes/legacy*100)+' % of the legacy '+legacy+' B); help, codes and training load on demand');
}
})().catch(e=>{console.error(e);process.exit(1);});
