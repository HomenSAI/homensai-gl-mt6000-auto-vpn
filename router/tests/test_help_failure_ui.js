// 05.11.2026 (fix/ui-polish-a9): what the page shows when the optional help module fails, and the small layout defects found in the
// final alpha9 UI pass. Every assertion below fails on 815bebc1.
//  1. master slider without help209.js: the state of the fast segment / turbo stays visible, UI-HELP-LOAD-FAILED + Retry
//  2. Retry really retries (loadLazyHelp(true)); LuCI 23.05 caches a rejected L.require per name
//     (luci.js: classes[name]=Request.get(...).then(compileClass) is never removed), so the old xdretry could not succeed;
//     since F-77 (CSP, no eval) the retry asks L.require for the same pinned file under a fresh name
//  3. the code dialog on failure: no endless «загружается…», the failure and Retry instead
//  4. phone Home: the status card first (the auto-adaptation card has an order after the channels)
//  5. sensors: the lamp never stands alone on a line; the heading keeps a gap
//  6. the chart label «по умолчанию» does not cover the labels of the three marked positions
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const {load,strip,pageSource,CSS,ROOT,app}=require('./approved_page');
const src=pageSource(),css=fs.readFileSync(CSS,'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
const raw=JSON.parse(fs.readFileSync(path.join(ROOT,'router/files/usr/lib/homensai-vpn/slider_curve.json'),'utf8'));
const curve={version:raw.version,params:raw.params,metrics:raw.metrics,anchors:raw.anchors.map(a=>({t:a.t,p:a.p,m:a.m})),alpha8:raw.alpha8,fast_anchors:raw.fast_anchors};
const lazyFile=path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m)));
const moduleSource=fs.readFileSync(lazyFile,'utf8');
const LAZY_NAME=/LAZY_HELP_NAME='([^']+)'/.exec(pageSource())[1];
// what luci.js compileClass yields: the factory evaluated with its 'require baseclass' and the class instantiated
function lazyInstance(p){p.c.baseclass.extend=spec=>Object.assign(spec,{instantiate(a){assert(Array.isArray(a));return spec;}});return vm.runInContext('(function(){'+moduleSource+'})()',p.c).instantiate([]);}
const flush=()=>new Promise(r=>setTimeout(r,25));
function advisor(current){
  return {mode:'advice',window_days:7,curve_version:1,
    current:Object.assign({t_ref:0.5,slider_t:0.5,attached:true,label:'slider',nearest_t:0.5,failure_model:'hmm',theta:0.6,dur_b:5,pg:0.95,primary_stable:120,rescue_stable:10},current),
    recommendation:{state:'keep',t:0.5,best_t:0.5,reason_ru:'',reason_en:'',events:16,days_used:7,counts:{natural:14,loss_episodes:1,flaps:1,reserve_failures:0},generated:1700000000,window_days:7},
    journal:{days:7,window_days:7,tunnels:{},pair:{switches:2,returns:2,unnecessary:1}},last_change:null};
}
function page(lang,current){
  const p=load({lang,answers:{advisor:()=>({curve})},mutate:({status})=>{status.network_advisor=advisor(current);}});
  p.c.HV_FIXTURE_ADVISOR_OFF=true;p.T.snap();p.T.advCardHTML();return p;
}
function fakeRoot(extra){
  const root=Object.assign({className:'',innerHTML:'',contains:()=>true,setAttribute(){},removeAttribute(){},querySelector:()=>null,querySelectorAll:()=>[],appendChild(){},scrollTo(){}},extra||{});
  return root;
}

(async()=>{
// ---------- 1. the slider section without the module ----------
for(const lang of ['ru','en']){
  const p=page(lang,{fast:true,turbo:true});await flush();p.T.HV.open['sec-adv']=true;p.T.HV.root=fakeRoot();
  let body=strip(p.T.advSectionBody());await flush();body=strip(p.T.advSectionBody());   // the first call starts the load, the failure arrives later
  assert(body.includes('UI-HELP-LOAD-FAILED'),lang+': the failure is named in the slider section: '+body.slice(0,200));
  assert(p.T.advSectionBody().includes('data-act="helpretry"'),lang+': Retry in the slider section');
  assert(body.includes(lang==='ru'?'Быстрый сегмент: вкл':'Fast segment: on')&&body.includes(lang==='ru'?'Турбо: вкл':'Turbo: on'),lang+': an enabled fast segment and turbo stay visible: '+body.slice(0,300));
  const q=page(lang,{fast:false,turbo:false});await flush();q.T.HV.open['sec-adv']=true;q.T.HV.root=fakeRoot();q.T.advSectionBody();await flush();
  const b2=strip(q.T.advSectionBody());
  assert(b2.includes(lang==='ru'?'Быстрый сегмент: выкл':'Fast segment: off')&&b2.includes(lang==='ru'?'Турбо: выкл':'Turbo: off'),lang+': the off state is shown too');
  assert(!p.T.advSectionBody().includes('data-act="xdretry"'),'one retry action for every help failure');
}
console.log('PASS: slider section without the help module shows state + UI-HELP-LOAD-FAILED + Retry');

// ---------- 2. Retry asks LuCI for the pinned file under a fresh name and the sections come back ----------
{
  const p=page('ru',{fast:true,turbo:true});
  let required=0,fetched=0,lastName='';
  // LuCI keeps returning the cached rejection for the first name; a fresh name for the same file compiles the module
  p.c.L.require=name=>{if(name===LAZY_NAME){required++;return Promise.reject(new Error('cached rejection'));}fetched++;lastName=name;return Promise.resolve(lazyInstance(p));};
  p.c.request.get=()=>{throw new Error('no eval path: the module is never fetched as text');};
  const nodes=[];const root=fakeRoot({querySelectorAll:sel=>sel==='[data-cb]'?nodes:[]});
  p.T.HV.root=root;p.T.HV.view='simple';p.T.HV.page='settings';p.T.HV.open['sec-adv']=true;
  p.T.advSectionBody();await flush();
  assert.equal(required,1,'the first load uses L.require once');assert.equal(fetched,0);assert(!p.T.xdU(),'module failed');
  const retry={dataset:{act:'helpretry'},tagName:'BUTTON',getAttribute:()=>null,disabled:false};
  const click=()=>p.T.onClick({target:{closest:()=>retry},preventDefault(){},stopPropagation(){}});
  click();await flush();await flush();
  assert.equal(required,1,'Retry does not call the cached L.require again');
  assert.equal(fetched,1,'Retry asks LuCI once');assert.equal(decodeURIComponent(lastName),LAZY_NAME.replace(/\./g,'/'),'the same pinned file: '+lastName);
  assert(p.T.xdU(),'the expert module is usable after Retry');
  const body=p.T.advSectionBody();
  assert(body.includes('data-act="advfast"')&&body.includes('data-act="advturbooff"')&&!body.includes('UI-HELP-LOAD-FAILED'),'fast switch and turbo-off are back after Retry');
  assert(root.innerHTML.length>0,'the page was drawn again after a successful Retry');
}
console.log('PASS: Retry reloads the pinned file under a fresh LuCI name (not the cached L.require, no eval) and redraws the page');

// ---------- 3. the code dialog ----------
{
  const p=page('en');
  p.c.HVX.showCode('DNS-001');
  const loading=body=>/role="status"/.test(body)&&/Loading the (?:detailed )?explanation/.test(body);
  assert(loading(p.modals[0].body),'first open: honest loading status');
  await flush();
  p.c.HVX.showCode('DNS-001');
  const b=p.modals[1].body;
  assert(b.includes('UI-HELP-LOAD-FAILED')&&b.includes('data-act="helpretry"')&&!loading(b),'failed: the failure and Retry replace the loading text: '+b);
  // the open dialog is redrawn in place: the page marks the body with data-cb
  const node={dataset:{cb:'DNS-001'},set outerHTML(v){this.html=v;}};
  p.T.HV.root=fakeRoot({querySelectorAll:sel=>sel==='[data-cb]'?[node]:[]});
  p.c.HVX.showCode('DNS-001');await flush();
  assert(node.html&&node.html.includes('UI-HELP-LOAD-FAILED')&&node.html.includes('data-act="helpretry"')&&!loading(node.html),'the open dialog changes from loading to failure + Retry');
}
console.log('PASS: code dialog shows failure + Retry instead of an endless loading text');

// ---------- 4/5. phone layout ----------
{
  const phone=css.slice(css.indexOf('@media (max-width:900px){.hvx .gold [data-b="manual"]'));
  assert(/\.hvx \.gold \.advcard\{order:5\}/.test(phone),'the auto-adaptation card follows the channels, events and statistics on a phone');
  assert(/\.hvx \.gold \.hero\{order:1\}/.test(css),'the status card stays first');
  assert(/p\.row:has\(>\.lamp:first-child\)\{flex-wrap:nowrap/.test(css)&&/p\.row:has\(>\.lamp:first-child\)>span\{flex:1 1 0;min-width:0\}/.test(css),'a lamp row keeps its lamp beside the text');
  assert(/\.hvx #sensors\{margin-top:\d+px\}/.test(css),'the sensors heading keeps a gap above');
}
console.log('PASS: phone Home order and sensors rows');

// ---------- 6. the chart labels do not overlap ----------
async function withModule(p){
  p.c.L.require=name=>name===LAZY_NAME?Promise.reject(new Error('cached rejection')):Promise.resolve(lazyInstance(p));
  p.T.HV.root=fakeRoot();p.T.HV.view='simple';p.T.HV.page='settings';p.T.HV.open['sec-adv']=true;
  p.T.advSectionBody();await flush();
  p.T.onClick({target:{closest:()=>({dataset:{act:'helpretry'},tagName:'BUTTON',getAttribute:()=>null})},preventDefault(){},stopPropagation(){}});
  await flush();await flush();assert(p.T.xdU(),'module loaded');
}
for(const lang of ['ru','en']){
  const p=page(lang,{fast:true,turbo:true});await flush();p.T.snap();
  const bare=p.T.advChart(0.5,0.3,false);
  assert(/class="mk def"/.test(bare)&&(bare.match(/class="mk pro"/g)||[]).length===3&&!/class="lbl"/.test(bare),'without the module the markers are drawn, the labels wait');
  await withModule(p);
  const svg=p.T.advChart(0.5,0.3,false);
  const labels=[...svg.matchAll(/<text class="lbl" x="([\d.]+)" y="([\d.-]+)" text-anchor="(\w+)">([^<]+)<\/text>/g)].map(m=>{const n=m[4].replace(/&quot;/g,'"'),w=n.length*5.8,x=Number(m[1]),end=m[3]==='end';return {n,x0:end?x-w:x,x1:end?x:x+w,y:Number(m[2])};});
  assert.equal(labels.length,4,lang+': default + three positions are labelled');
  for(let i=0;i<labels.length;i++){assert(labels[i].x0>=50&&labels[i].x1<=636,lang+': "'+labels[i].n+'" stays inside the chart');
    for(let j=i+1;j<labels.length;j++){const a=labels[i],b=labels[j];
      assert(a.x1<=b.x0||b.x1<=a.x0||Math.abs(a.y-b.y)>=11,lang+': labels "'+a.n+'" and "'+b.n+'" overlap');}}
  assert(!/class="lbl"/.test(p.T.advChart(0.5,0.3,true)),'the small chart of the Home card has no labels');
}
console.log('PASS: chart labels do not overlap');
})().catch(error=>{console.error(error);process.exitCode=1;});
