// F-01, F-75, F-76 (review of 2026-11-06): text that comes from the router (VPN names from the GL.iNet inventory, numbers of the
// advisor, date keys of the traffic accounting) must never become markup of the page. The shipped page is driven in a vm;
// the checks are on the HTML strings that reach innerHTML (modal title/body, renders, live bindings). No browser: whether a
// browser would have executed the payload is not tested, only that no element or attribute can be created from it.
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert'),vm=require('vm');
const {load,strip,ROOT,app}=require('./approved_page');
const PAYLOAD='<img src=x onerror=alert(1)>',ATTR='"><img src=x onerror=alert(2)>',SVG='</text><script>alert(3)</script>';
const flush=()=>new Promise(r=>setTimeout(r,25));
const bad=h=>/<img\b|<script\b/i.test(String(h));
const noMarkup=(h,what)=>assert(!bad(h),what+' carries live markup: '+String(h).slice(0,200));

(async()=>{
// ---------- F-01: the channel name in modal text ----------
for(const lang of ['ru','en']){
  const p=load({lang,mutate:({inventory,status})=>{
    inventory.servers.forEach(r=>{r.name=PAYLOAD;});inventory.profiles.forEach(r=>{r.name=PAYLOAD;});
    status.profiles.forEach(r=>{r.name=PAYLOAD;});
    status.manual_switch_control.reserve.allowed=false;status.manual_switch_control.reserve.blockers=['MANUAL-NOT-READY'];}});
  p.T.snap();
  p.T.stopAuto();                       // "Turn Auto off?" names the current channel
  const stop=p.modals.pop();noMarkup(stop.title+stop.body,lang+' stopAuto modal');
  assert(stop.body.includes('&lt;img'),lang+' the name is shown as text: '+stop.body);
  p.T.switchTo('reserve');              // not allowed: "Switching unavailable" names the channel
  const sw=p.modals.pop();noMarkup(sw.title+sw.body,lang+' switch-unavailable modal');
  p.T.snap();
  for(const k of ['p.name','r.name','p.meta','r.meta','p.text','r.text'])noMarkup(p.T.B[k](),lang+' binding '+k);
  noMarkup(p.T.settingsA(),lang+' settings');noMarkup(p.T.wizard(),lang+' wizard');
  for(const tab of Object.keys(p.T.tabs))noMarkup(p.T.tabs[tab](),lang+' tab '+tab);
  p.T.speedTest('primary');const sp=p.modals.pop();noMarkup(sp.title+sp.body,lang+' speed modal');
  p.T.faultTest();for(const m of p.modals)noMarkup(m.title+m.body,lang+' fault modal');
}
console.log('PASS: F-01 - VPN names from the router are text in every modal, binding, tab, settings and wizard (RU/EN)');

// ---------- F-76: date keys of the traffic accounting ----------
{
  const p=load({mutate:({status})=>{
    const day={rx:1e9,tx:1e9,observed:true};
    status.accounting=Object.assign(status.accounting||{},{days:{['2026-11-01']:day,['2026-11-02']:day,['2026-11-03'+SVG]:day,[ATTR]:day,['abcde<iXX<b']:day},wan:{days:{}}});}});
  p.T.snap();
  p.T.HV.open.dTr=true;
  const log=p.T.tabs.log();noMarkup(log,'traffic chart');
  assert(!log.includes('<b.<i')&&log.includes('01.11')&&log.includes('02.11'),'only valid YYYY-MM-DD keys are drawn: '+strip(log).slice(0,300));
}
console.log('PASS: F-76 - traffic chart draws only valid YYYY-MM-DD keys and escapes the labels');

// ---------- F-75: numbers of the advisor ----------
const raw=JSON.parse(fs.readFileSync(path.join(ROOT,'router/files/usr/lib/homensai-vpn/slider_curve.json'),'utf8'));
const curve={version:raw.version,params:raw.params,metrics:raw.metrics,anchors:raw.anchors.map(a=>({t:a.t,p:a.p,m:a.m})),alpha8:raw.alpha8};
function advisor(){return {mode:'advice',window_days:PAYLOAD,curve_version:1,
  current:{t_ref:0.5,slider_t:0.5,attached:true,label:'slider',nearest_t:0.5,failure_model:'hmm',theta:ATTR,dur_b:PAYLOAD,pg:'0.95'+ATTR,primary_stable:120,rescue_stable:10},
  recommendation:{state:'shift',t:0.7,reason_ru:'r',reason_en:'r'},last_change:{time:1700000000,source:'auto',from:PAYLOAD,to:ATTR,reason_ru:'x',reason_en:'x'}};}
{
  const p=load({answers:{advisor:()=>({curve})},mutate:({status})=>{status.network_advisor=advisor();}});
  p.c.HV_FIXTURE_ADVISOR_OFF=true;p.T.snap();p.T.advCardHTML();await flush();p.T.snap();
  noMarkup(p.T.advCardHTML(),'advisor card');
  assert(!/data window\s+<|окно данных\s+</.test(p.T.advCardHTML()),'window days is a number or a dash');
  noMarkup(p.T.advSectionBody(),'advisor section');
  p.T.advClick('advfine',{dataset:{}});                      // fine tuning copies theta, dur_b and pg from the router
  const f=p.T.ADV.fine;
  assert(f&&['theta','dur_b','pg'].every(k=>typeof f[k]==='number'&&Number.isFinite(f[k])),'fine values are finite numbers: '+JSON.stringify(f));
  noMarkup(p.T.advSectionBody(),'advisor fine tuning');
  const m=p.T.advSectionBody().match(/id="advf-theta"[^>]*value="([^"]*)"/);assert(m&&Number.isFinite(Number(m[1])),'the range value is numeric: '+(m&&m[1]));
}
{ // a curve whose fast anchors are not numbers is refused (it is read once per page)
  const bad2=JSON.parse(JSON.stringify(curve));bad2.fast_params=['cons_f'];bad2.fast_anchors=[{t:ATTR,p:[],m:[],x:[1]}];
  const p=load({answers:{advisor:()=>({curve:bad2})},mutate:({status})=>{status.network_advisor=Object.assign(advisor(),{window_days:7});}});
  p.c.HV_FIXTURE_ADVISOR_OFF=true;p.T.snap();p.T.advCardHTML();await flush();p.T.snap();
  assert.equal(p.T.ADV.curve,null,'invalid fast anchors: no curve');assert(p.T.ADV.err,'the honest code is shown');
  noMarkup(p.T.advCardHTML()+p.T.advSectionBody(),'advisor with a refused curve');
}
{ // the optional module escapes by itself as well (defence in depth)
  const mod=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m))),'utf8');
  const from=mod.indexOf('var EXPERT_GROUPS='),end='act:act,hint:hint};\n};',to=mod.indexOf(end,from)+end.length;
  const expertUI=vm.runInNewContext(mod.slice(from,to)+';EXPERT_UI',{});
  const p=load({});const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const advNum=(v,d)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(d||0);
  const u=expertUI({t:(ru,en)=>en===undefined?ru:en,esc,HV:{inv:{settings:{}}},XD:{ed:{}},ADV:{curve:{fast_anchors:[{t:ATTR,p:[],m:[]},{t:-0.1,p:[],m:[]}]}},$$:()=>[],advNum});
  noMarkup(u.fastRow({fast:true,turbo:true},false,0.5),'fast row');
  noMarkup(u.note({cons_f:PAYLOAD,beat_k:ATTR,dense_interval:SVG}),'fast segment note');
}
console.log('PASS: F-75 - advisor numbers (window, theta, dur_b, pg, fast anchors, fast-segment note) never reach HTML as text');
{ // F-77: the page's own markup carries no inline style="" attribute (the static ones are classes of the stylesheet; the progress width is set through the CSSOM)
  const {pageSource,CSS}=require('./approved_page');
  const src=pageSource(),css=fs.readFileSync(CSS,'utf8');
  assert.equal((src.match(/style="/g)||[]).length,0,'no inline style attribute in the page markup');
  for(const cls of ['mt8','mt4','mt10','fx1','fx1m0','tar','mw420','mv8','mv6','sb','sbnw','h8','fb100','prewrap'])assert(css.includes('.hvx.hvx .'+cls+'{'),'the stylesheet defines .'+cls);
  assert(css.includes('.hvx.hvx .btn[aria-disabled="true"]{opacity:.55}'),'a disabled-by-attribute button is dimmed by the stylesheet');
  assert(/i\.style\.width=/.test(src)&&/data-pct=/.test(src),'the progress width goes through the CSSOM');
  console.log('PASS: F-77 - no inline style attribute in the page markup; static layout lives in the stylesheet (visual equality not verified: no browser)');
}
})().catch(e=>{console.error(e);process.exit(1);});
