'use strict';
// English interface audit. In English mode no visible text or accessible attribute may contain Cyrillic.
//  1) Static: every bi(en,ru) pair in router/*.inc.js has a Cyrillic-free, non-empty EN side and a non-empty RU side,
//     and every [en,ru] data pair that is detectable by shape is checked at runtime below.
//  2) Runtime: the real page (every tab), the lazy Help/Training/Catalogue module, the error and journal catalogues are rendered
//     in English with realistic fixtures and all text nodes plus title/aria-label/placeholder/alt attributes are collected.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const CY_RAW=/[Ѐ-ӿ]/;
// A language name written in its own language (the language switcher, the link to the Russian terms text) is intentionally Russian.
const ALLOWED=/[Русский](DISCLAIMER.ru.md)|(?:^|[^Ѐ-ӿ])Русский(?![Ѐ-ӿ])|Українська|(?:^|[^Ѐ-ӿ])Русская версия(?![Ѐ-ӿ])/g;
const CY={test:v=>CY_RAW.test(String(v).replace(ALLOWED,' '))};

// ---------- 1. static scan ----------
const Q=/(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`)/.source;
const BI=new RegExp('\\bbi\\(\\s*('+Q+')\\s*,\\s*('+Q+')','g');
const staticProblems=[];
for(const file of fs.readdirSync(root).filter(f=>f.endsWith('.inc.js'))){
  const source=fs.readFileSync(path.join(root,file),'utf8');let m;
  while((m=BI.exec(source))){
    const en=m[1].slice(1,-1),ru=m[2].slice(1,-1);
    if(CY.test(en))staticProblems.push(file+': Cyrillic in the English argument of bi(): '+en.slice(0,100));
    if(!en.trim())staticProblems.push(file+': empty English argument of bi() near '+ru.slice(0,60));
    if(!ru.trim())staticProblems.push(file+': empty Russian argument of bi(): '+en.slice(0,60));
  }
}

// ---------- fake DOM ----------
class N{
  constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[];this.parentNode=null;this.hidden=false;this._style={};
    [].concat(children==null?[]:children).flat(Infinity).filter(x=>x!=null&&x!==false).forEach(c=>this.appendChild(c));
    for(const k of Object.keys(this.attrs))if(typeof this.attrs[k]==='function')(this.listeners=this.listeners||{})[k]=this.attrs[k];}
  appendChild(c){if(c instanceof N){if(c.parentNode)c.parentNode.removeChild(c);c.parentNode=this;}else if(typeof c!=='object')c=String(c);this.children.push(c);return c;}
  insertBefore(c,r){if(c instanceof N&&c.parentNode)c.parentNode.removeChild(c);const i=r?this.children.indexOf(r):-1;if(c instanceof N)c.parentNode=this;if(i<0)this.children.push(c);else this.children.splice(i,0,c);return c;}
  removeChild(c){const i=this.children.indexOf(c);if(i>=0)this.children.splice(i,1);if(c instanceof N)c.parentNode=null;return c;}
  replaceChild(n,o){const i=this.children.indexOf(o);if(i>=0){this.children[i]=n;n.parentNode=this;}return o;}
  replaceChildren(...v){this.children.forEach(c=>{if(c instanceof N)c.parentNode=null;});this.children=[];v.forEach(c=>this.appendChild(c));}
  append(...v){v.forEach(c=>this.appendChild(c));}
  remove(){if(this.parentNode)this.parentNode.removeChild(this);}
  get firstChild(){return this.children[0]||null;}get lastChild(){return this.children[this.children.length-1]||null;}
  get nextSibling(){const p=this.parentNode;if(!p)return null;return p.children[p.children.indexOf(this)+1]||null;}
  get childNodes(){return this.children;}get parentElement(){return this.parentNode;}get isConnected(){return true;}
  get style(){const s=this._style;s.setProperty=s.setProperty||function(){};s.removeProperty=s.removeProperty||function(){};return s;}
  get classList(){const self=this,get=()=>String(self.attrs['class']||'').split(/\s+/).filter(Boolean);
    return {add(...v){self.attrs['class']=get().concat(v).join(' ');},remove(...v){self.attrs['class']=get().filter(x=>!v.includes(x)).join(' ');},
      toggle(v,f){const h=get().includes(v);if(f===undefined?!h:f)this.add(v);else this.remove(v);},contains:v=>get().includes(v)};}
  get className(){return this.attrs['class']||'';}set className(v){this.attrs['class']=v;}
  get textContent(){return this.text();}set textContent(v){this.children=[String(v)];}
  get innerHTML(){return '';}set innerHTML(v){this.children=[];}
  get value(){return this._value!==undefined?this._value:(this.attrs.value==null?'':this.attrs.value);}set value(v){this._value=v;}
  get id(){return this.attrs.id||'';}set id(v){this.attrs.id=v;}get href(){return this.attrs.href;}set href(v){this.attrs.href=v;}set target(v){this.attrs.target=v;}set rel(v){this.attrs.rel=v;}set title(v){this.attrs.title=v;}get title(){return this.attrs.title;}set type(v){this.attrs.type=v;}set lang(v){this.attrs.lang=v;}set src(v){this.attrs.src=v;}set alt(v){this.attrs.alt=v;}set placeholder(v){this.attrs.placeholder=v;}get dataset(){return {};}
  get open(){return !!this._open;}set open(v){this._open=v;}
  setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k]==null?null:String(this.attrs[k]);}hasAttribute(k){return this.attrs[k]!=null;}removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,f){(this.listeners=this.listeners||{})[k]=f;}removeEventListener(){}dispatchEvent(){return true;}
  focus(){}blur(){}click(){}scrollIntoView(){}getBoundingClientRect(){return {top:0,left:0,width:0,height:0,bottom:0,right:0};}
  contains(n){return this.all().includes(n);}
  all(){return [this].concat(...this.children.filter(c=>c instanceof N).map(c=>c.all()));}
  text(){return this.children.map(c=>c instanceof N?c.text():String(c)).join(' ');}
  matches(sel){return sel.split(',').some(s=>matchOne(this,s.trim()));}
  closest(sel){for(let n=this;n;n=n.parentNode)if(n.matches(sel))return n;return null;}
  querySelectorAll(sel){return this.all().slice(1).filter(n=>n.matches(sel));}
  querySelector(sel){return this.querySelectorAll(sel)[0]||null;}
  getElementsByTagName(t){return this.all().slice(1).filter(n=>n.tag===t);}
  cloneNode(){return new N(this.tag,Object.assign({},this.attrs),this.children.slice());}
}
function matchOne(n,s){
  s=s.replace(/:not\([^)]*\)/g,'').split(/\s+/).pop();
  const m=/^([a-z0-9]*)((?:[.#][\w-]+|\[[^\]]+\])*)$/i.exec(s);if(!m)return false;
  if(m[1]&&n.tag!==m[1])return false;
  return (m[2].match(/[.#][\w-]+|\[[^\]]+\]/g)||[]).every(p=>{
    if(p[0]==='.')return n.classList.contains(p.slice(1));
    if(p[0]==='#')return n.attrs.id===p.slice(1);
    const a=/^\[([\w-]+)(?:([~^$*|]?=)"?([^"\]]*)"?)?\]$/.exec(p);if(!a)return false;
    const v=n.attrs[a[1]];if(!a[2])return v!=null;return v!=null&&String(v)===a[3];});
}

// ---------- collection ----------
const ATTRS=['title','aria-label','placeholder','alt','aria-description','data-tip'];
let found=new Map();
function collect(scope,node){
  if(!(node instanceof N))return;
  for(const n of node.all()){
    for(const c of n.children)if(typeof c==='string'&&CY.test(c))add(scope,c,'text <'+n.tag+'>');
    for(const k of ATTRS){const v=n.attrs[k];if(typeof v==='string'&&CY.test(v))add(scope,v,k+' <'+n.tag+'>');}
    if(n.tag==='option'&&typeof n.attrs.label==='string'&&CY.test(n.attrs.label))add(scope,n.attrs.label,'label');
    if(n.tag==='input'&&typeof n.attrs.value==='string'&&n.attrs.type!=='hidden'&&CY.test(n.attrs.value))add(scope,n.attrs.value,'value');
  }
}
function add(scope,value,where){const key=value.trim();if(!found.has(key))found.set(key,{scope,where});}
const sources=fs.readdirSync(root).filter(f=>f.endsWith('.js')&&!f.startsWith('build')).concat(fs.readdirSync(root).filter(f=>f.endsWith('.py'))).map(f=>[f,fs.readFileSync(path.join(root,f),'utf8')]);
function origin(value){
  const frags=value.split(/[\n\r]/).map(s=>s.trim()).filter(s=>CY.test(s)).map(s=>s.slice(0,28));
  for(const frag of frags)for(const [f,s] of sources)if(s.includes(frag))return f;
  return '?';
}

// ---------- fixtures ----------
const now=Math.floor(Date.now()/1000);
function inventoryFixture(termsVersion){
  const profile=(id,name,proto,iface,channel)=>({id,name,router_name:name,protocol:proto,interface:iface,channel,enabled:true,priority:1,endpoint:'203.0.113.'+(id.charCodeAt(0)%200),country:'DE'});
  return {profiles:[profile('a','de1459.nordvpn.com.udp','openvpn','ovpnclient1','Main'),profile('b','nl-ams-001','wireguard','wgclient1','Main'),profile('c','fi-spare','openvpn',null,'Spare')],
    settings:{enabled:true,terms_version:termsVersion,plan_source:'a',plan_target:'b',telegram_configured:false,detected_router_model:'gl-mt3000',appearance_language:'en',appearance_theme:'auto',
      probe_interval_seconds:15,response_metric:'ping',probe_level:'normal',probe_boost:'auto',onboarding_done:true,auto_requested:'on'},
    router:{model:'GL.iNet GL-MT3000',firmware:'4.8.4',hardware:'mt3000'},version:'1.2.3'};
}
function statusFixture(kind){
  const base=(id,iface,proto,code,rtt)=>({id,name:id==='a'?'de1459.nordvpn.com.udp':id==='b'?'nl-ams-001':'fi-spare',router_name:id==='a'?'de1459.nordvpn.com.udp':id==='b'?'nl-ams-001':'fi-spare',
    protocol:proto,interface:iface,channel:'Main',time:now-3,dns_ok:!code,https_success:code?0:2,rtt_ms:code?null:rtt,code:code||null,enabled:true,connected:!!iface,
    ping_ms:code?null:rtt,ping_loss:0,website_ms:code?null:rtt*3,metric:'ping'});
  const samples=[];for(let i=0;i<30;i++){for(const [id,rtt] of [['a',36],['b',52]]){const bad=kind==='fault'&&i%7===3&&id==='b';
    samples.push({id,time:now-(30-i)*30,code:bad?'DNS-001':null,dns_ok:!bad,https_success:bad?0:2,rtt_ms:bad?null:rtt+i%5,ping_ms:bad?null:rtt+i%5});}}
  const fault=kind==='fault';
  const status={version:'1.2.3',package:'1.2.3-1',time:now-1,profiles:[base('a','ovpnclient1','openvpn',fault?'VPN-003':null,38),base('b','wgclient1','wireguard',fault?'DNS-001':null,52),{id:'c',name:'fi-spare',router_name:'fi-spare',protocol:'openvpn',interface:null,channel:'Spare'}],samples,
    native_failover:{time:now-1,state:fault?'DEGRADED-ON-RESERVE':'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,certified:true,source:'a',target:'b'},
    native_history:{events:[{sequence:1,time:now-900,state:'APPLYING',source:'a',target:'b',codes:[]},{sequence:2,time:now-898,state:'COMMITTED',source:'a',target:'b',codes:[]},
      {sequence:3,time:now-600,state:'ROLLED-BACK',source:'b',target:'a',codes:['DNS-001']},{sequence:4,time:now-300,state:'FAILED',source:'a',target:'b',codes:['VPN-003','PAIR-MANUAL-RECOVERED']}]},
    auto_control:{requested:fault?'off':'on',requested_at:now-100,pair_phase:fault?'STOPPED':'RUNNING',control_revision:'b'.repeat(32)},
    channel_path:{time:now-1,checked_at:now-1,valid_for:15,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',kernel_policy_verified:true,confirmed:true,active_profile_id:'a',source_profile_id:'a',target_profile_id:'b'},
    manual_switch_control:{time:now-1,mode:'continuous-pair',control_revision:'b'.repeat(32),available:true,reserve:{allowed:true,blockers:[]},primary:{allowed:!fault,blockers:fault?['PAIR-MANUAL-BUSY']:[]}},
    probe:{level:'normal',boost:{active:false},interval_seconds:15,next_at:now+9,last_at:now-6,metric:'ping',targets:['1.1.1.1','8.8.8.8','9.9.9.9']},
    accounting:{months:{}},telegram:{enabled:false},
    guard:{blockers:fault?['GUARD-DEVICE-UNVERIFIED','VPN-POLICY-DISABLED']:[]}};
  if(fault)status.native_failover.codes=['VPN-003'];
  return status;
}

// ---------- real page ----------
const menu=JSON.parse(fs.readFileSync(path.join(root,'files/usr/share/luci/menu.d/luci-app-homensai-vpn.json'),'utf8'));
const selected=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base=path.join(root,'files/www/luci-static/resources/');
const pageSource=fs.readFileSync(base+'view/homensai-vpn/'+selected+'.js','utf8');
const moduleName=/LAZY_HELP_NAME='([^']+)'/.exec(pageSource)[1];
const moduleSource=fs.readFileSync(base+moduleName.replace(/\./g,'/')+'.js','utf8');
const termsVersion=/TERMS_VERSION='([^']+)'/.exec(pageSource);

function sandbox(language,rpcMode){
  const stored={},listeners={},timers=[],shown=[];
  const doc=new N('html',{},[]),body=new N('body',{},[]);doc.appendChild(body);
  const win={localStorage:{getItem:k=>stored[k]||null,setItem:(k,v)=>{stored[k]=v;},removeItem(k){delete stored[k];}},HomenS:{},
    location:{search:'?lang='+language,href:'http://router/cgi-bin/luci/admin/services/homensai-vpn#overview',hash:'#overview',origin:'http://router',reload(){}},
    addEventListener:(k,f)=>{listeners[k]=f;},removeEventListener(){},matchMedia:()=>({matches:false,addEventListener(){},addListener(){}}),pageYOffset:0,scrollTo(){},innerWidth:1280,
    requestAnimationFrame:f=>0,setInterval:()=>0,clearInterval(){},setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){},getComputedStyle:()=>({getPropertyValue:()=>''}),history:{replaceState(){},pushState(){}},navigator:{language:'en-US',clipboard:{writeText:()=>Promise.resolve()}}};
  const document={body,documentElement:doc,createElement:t=>new N(t),createElementNS:(ns,t)=>new N(t),createTextNode:t=>String(t),createComment:()=>new N('#comment'),createDocumentFragment:()=>new N('#fragment'),addEventListener(){},removeEventListener(){},
    getElementById:id=>body.all().find(n=>n.attrs.id===id)||null,querySelector:s=>body.querySelector(s),querySelectorAll:s=>body.querySelectorAll(s),
    activeElement:null,hidden:false,visibilityState:'visible',head:new N('head')};
  const ctx={window:win,document,E:(t,a,c)=>new N(t,a,c),console:{log(){},warn(){},error(){}},URLSearchParams,URL,Intl,Promise,Date,Math,JSON,Event:class{constructor(type){this.type=type;}},CustomEvent:class{constructor(type){this.type=type;}},
    localStorage:win.localStorage,sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},navigator:win.navigator,location:win.location,
    setTimeout:(fn)=>{timers.push(fn);return timers.length;},clearTimeout(){},setInterval:()=>0,clearInterval(){},requestAnimationFrame:()=>0,cancelAnimationFrame(){},
    getComputedStyle:win.getComputedStyle,performance:{now:()=>Date.now()},
    rpc:{declare:()=>()=>rpcMode==='reject'?Promise.reject(new Error('transport')):Promise.resolve(rpcMode==='accepted'?{accepted:true,queued:true,ok:true}:{})},
    ui:{addNotification:(t,n)=>{shown.push(n);return n;},showModal:(t,n)=>{shown.push(t,n);},hideModal(){}},alert:m=>{shown.push(String(m));},confirm:m=>{shown.push(String(m));return true;},prompt:m=>{shown.push(String(m));return 'TEST';},poll:{add(){},remove(){},start(){},stop(){}},view:{extend:o=>o},
    request:{get:()=>Promise.resolve({ok:false})},
    baseclass:{extend:spec=>Object.assign(spec,{instantiate(args){return spec;}})},
    L:{url:(...p)=>'/cgi-bin/luci/'+p.join('/'),resource:p=>'http://router/luci-static/resources/'+p,require:()=>Promise.resolve(vm.runInContext('(function(){'+moduleSource+'})()',ctx))}};
  ctx.location=win.location;ctx.self=win;vm.createContext(ctx);
  const prefix=pageSource.slice(0,pageSource.lastIndexOf('return view.extend({'));
  const brandDir=base+'view/homensai-vpn/style/js/';
  for(const f of ['brand.js','brand-ui.js'])vm.runInContext(fs.readFileSync(brandDir+f,'utf8'),ctx,{filename:f});
  vm.runInContext(prefix,ctx);
  vm.runInContext(pageSource.slice(pageSource.lastIndexOf('return view.extend({')).replace(/^return view\.extend\(/,'__view=(')+';',ctx);
  return {ctx,win,body,listeners,timers,shown};
}

// Data tables hold [English, Russian] pairs. Walk every reachable table and report pairs whose English half is Russian or empty.
function auditPairs(scope,ctx,skip){
  const seen=new Set();
  const visit=(value,trail,depth)=>{
    if(value==null||typeof value!=='object'||seen.has(value)||depth>9||value instanceof N)return;seen.add(value);
    if(Array.isArray(value)){ if(process.env.EN_DBG&&value.length===2&&typeof value[0]==='string')globalThis.__pairs=(globalThis.__pairs||0)+1;
      if(value.length===2&&typeof value[0]==='string'&&typeof value[1]==='string'&&(value[0]||value[1])){
        if(CY.test(value[0])||(!value[0].trim()&&value[1].trim())||(value[0].trim()&&!value[1].trim()))add(scope+' '+trail,CY.test(value[0])?value[0]:'(one side empty) '+value[0]+' | '+value[1],'pair');
        return;
      }
    }
    for(const key of Object.keys(value)){let v;try{v=value[key];}catch(error){continue;}visit(v,trail+'.'+key,depth+1);}
  };
  for(const name of Object.keys(ctx)){if(skip.includes(name))continue;let v;try{v=ctx[name];}catch(error){continue;}
    if(v&&typeof v==='object')visit(v,name,0);}
}

// State sweep: every journal state, Auto blocker and catalogue code is injected into the status and the state-dependent renderers are
// called directly, so texts that the single fixtures above never reach are audited too.
function collectValue(scope,value,where,depth){
  if(value==null||depth>4)return;
  if(typeof value==='string'){if(CY.test(value))add(scope,value,where);return;}
  if(value instanceof N){collect(scope,value);return;}
  if(typeof value==='object')for(const k of Object.keys(value))collectValue(scope,value[k],where+'.'+k,depth+1);
}
const failures={};
function sweepStates(){
  const s=sandbox('en'),c=s.ctx,inv=inventoryFixture(termsVersion?termsVersion[1]:'');
  const codes=Array.from(new Set(c.ERROR_ROWS.map(r=>r[0].replace(/\*$/,'')).concat(Object.keys(c.AUTO_BLOCKERS||{}),Object.keys(c.AUTO_REMEDIES||{}),Object.keys(c.PLAN_BLOCKERS||{}),Object.keys(c.JOURNAL_TYPES||{}))));
  const states=Array.from(new Set(['OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','APPLYING','WAIT-CLIENT','ROLLED-BACK','FAILED','HELD','BLOCKED','IDLE','UNKNOWN','STOPPED','RUNNING','WAITING','OK','REFUSED','RETURNING','RECOVERING','PENDING','CANCELLED','UNCONFIRMED','QUEUED','COMPLETED','FAULT-ACTIVE'].concat(Object.keys(c.JOURNAL_TYPES||{}))));
  const run=(fn)=>{try{fn();}catch(error){const k=String(fn).slice(6,40)+' '+String(error.message).slice(0,50);failures[k]=(failures[k]||0)+1;}};
  const names=['fillSideStatus','autoLightModel','simpleHomeModel','renderManualSwitch','manualFailureResult','renderEventHistory','renderAutoControl','renderProbeControl','probeCountdown','renderLatencyPanel','renderLiveLog','renderServerSummary','renderCascadePath','renderStoredStatistics','renderTransitionAnalytics','renderSummary','renderVendorEvents','renderAutoLive','renderAutoDay','renderMonitorBlock','renderReadiness','renderPreparation'];
  const missing=names.filter(n=>typeof c[n]!=='function');
  const pair=(state,code,mode)=>{
    const st=statusFixture(mode),t=st.time,codeList=code?[code]:[];
    st.native_failover=Object.assign(st.native_failover,{state,codes:codeList,code,reason:code,blockers:codeList,last_error:code});
    st.auto_control=Object.assign(st.auto_control,{pair_phase:state,codes:codeList,code,blockers:codeList,refusal:code});
    st.manual_switch={state,completed:state==='COMPLETED',request_id:'c'.repeat(32),direction:'reserve',requested_at:t-5,updated_at:t-1,code};
    st.profiles[0].code=code;st.profiles[1].code=null;
    st.native_history={events:[{sequence:1,time:t-40,state:'APPLYING',source:'a',target:'b',codes:[]},{sequence:2,time:t-30,state,source:'a',target:'b',codes:codeList,code,level:'error'},{sequence:3,time:t-20,state:code||state,source:'b',target:'a',codes:codeList,code}]};
    st.guard={blockers:codeList};
    return st;
  };
  const exercise=(st,tag)=>{
    const t=st.time,rows=st.profiles;
    run(()=>collectValue(tag,c.autoLightModel(st,inv,t),'autoLightModel',0));
    run(()=>collectValue(tag,c.simpleHomeModel(st,inv,t),'simpleHomeModel',0));
    run(()=>{const h=new N('div');c.fillSideStatus(h,st,inv);collect(tag,h);});
    run(()=>collect(tag,c.renderManualSwitch(st,inv)));
    run(()=>collectValue(tag,c.manualFailureResult(st,t),'manualFailureResult',0));
    run(()=>collect(tag,c.renderEventHistory(st)));
    run(()=>collect(tag,c.renderAutoControl(st,inv,()=>Promise.resolve())));
    run(()=>collect(tag,c.renderProbeControl(st,inv)));
    run(()=>collectValue(tag,c.probeCountdown(st),'probeCountdown',0));
    run(()=>collect(tag,c.renderLatencyPanel(st,inv)));
    run(()=>collect(tag,c.renderLiveLog(st,rows,{},inv,{})));
    run(()=>collect(tag,c.renderServerSummary(st,inv,rows)));
    run(()=>collect(tag,c.renderCascadePath(st,inv)));
    run(()=>collect(tag,c.renderStoredStatistics(st)));
    run(()=>collect(tag,c.renderTransitionAnalytics(st,inv)));
    run(()=>collect(tag,c.renderSummary(st,inv)));
    run(()=>collect(tag,c.renderVendorEvents(st,inv)));
    run(()=>collect(tag,c.renderAutoLive(st,inv)));
    run(()=>collect(tag,c.renderAutoDay(st)));
    run(()=>collect(tag,c.renderMonitorBlock(st,inv)));
    run(()=>collect(tag,c.renderReadiness(st,inv)));
    run(()=>collect(tag,c.renderPreparation(st,t)));
  };
  for(const state of states)for(const mode of ['ok','fault'])exercise(pair(state,null,mode),'state '+state+'/'+mode);
  for(const code of codes){exercise(pair('BLOCKED',code,'fault'),'code '+code);exercise(pair('FAILED',code,'ok'),'code '+code);}
  // Probe level / boost / response metric variants.
  for(const level of ['low','normal','high','boost','off',undefined])for(const metric of ['ping','http','dns','website',undefined]){
    const st=statusFixture('ok');st.probe=Object.assign(st.probe,{level,metric,boost:{active:level==='boost',until:st.time+60,reason:'latency'}});
    const i2=inventoryFixture(termsVersion?termsVersion[1]:'');i2.settings.probe_level=level;i2.settings.response_metric=metric;exercise(st,'probe '+level+'/'+metric);
    run(()=>collect('settings '+level+'/'+metric,c.renderMinimumSettings(i2,st,()=>st)));
  }
  run(()=>collect('measurements',c.renderMeasurements()));
  if(missing.length)logCrash.push('sweep: functions not found in the page: '+missing.join(', '));
}
const TABS=['start','home','overview','channels','tests','statistics','traffic','services','events','readiness','settings','learn','help'];
const logCrash=[];
async function renderPages(kind,language,rpcMode,interact){
  const s=sandbox(language,rpcMode),inv=inventoryFixture(termsVersion?termsVersion[1]:'');
  const status=statusFixture(kind);
  let root;
  try{
    root=s.ctx.__view.render.call(s.ctx.__view,[inv,status,{}]);
  }catch(error){logCrash.push(kind+' render: '+(error.stack||error).toString().split('\n').slice(0,3).join(' | '));return null;}
  if(root&&typeof root.then==='function')root=await root;
  s.body.appendChild(root);
  const scope=kind+'/overview';collect(scope,root);
  for(const tab of TABS){
    s.win.location.hash='#'+tab;
    try{if(s.listeners.hashchange)s.listeners.hashchange({type:'hashchange'});}catch(error){logCrash.push(kind+' tab '+tab+': '+(error.stack||error).toString().split('\n').slice(0,3).join(' | '));}
    for(let i=0;i<3;i++)await Promise.resolve();
    // open every details so that bodies are part of the audit (the fake DOM keeps closed content as well)
    collect(kind+'/'+tab,root);
    if(interact){
      // Press every button/link and feed invalid values to every input of the visible page, then audit what appeared.
      const page=root.all().find(n=>n.attrs['data-hv-page']===tab&&!n.hidden)||root;
      const targets=page.all().filter(n=>n.listeners);
      for(const n of targets){
        for(const type of ['click','input','change','blur','keydown']){
          const fn=n.listeners[type];if(typeof fn!=='function')continue;
          if(['input','textarea','select'].includes(n.tag))n.value=type==='input'?'abc':'-1';
          const event={type,key:'Enter',preventDefault(){},stopPropagation(){},target:n,currentTarget:n};
          globalThis.__fired=(globalThis.__fired||0)+1;try{const r=fn.call(n,event);if(r&&typeof r.then==='function')r.catch(()=>{});}catch(error){}
        }
      }
      for(let i=0;i<8;i++)await Promise.resolve();
      collect(kind+'/'+tab+' after interaction ('+(rpcMode||'empty')+')',root);
      globalThis.__shown=(globalThis.__shown||0)+s.shown.length;for(const item of s.shown.splice(0))collectValue(kind+'/'+tab+' notification',item,'notification',0);
    }
  }
  if(!interact&&language==='en'&&kind==='ok'){
    const all=root.text();
    for(const needle of ['Measured results of Auto mode','Probe level and automatic boost','DNS check did not pass','Traffic this month','Channels and servers'])assert(all.includes(needle),'the audit reached: '+needle);
  }
  return {s,root};
}
function renderCatalogue(language){
  const s=sandbox(language);
  return s;
}

process.on('unhandledRejection',error=>logCrash.push('async: '+(error&&error.stack||error).toString().split(String.fromCharCode(10)).slice(0,3).join(' | ')));
(async()=>{
  // Control: the same collector must see plenty of Cyrillic in Russian mode, otherwise the audit would be blind.
  {
    const english=found;found=new Map();await renderPages('ok','ru');
    assert(found.size>150,'the collector sees the Russian interface ('+found.size+' strings)');found=english;
  }
  for(const kind of ['ok','fault']){await renderPages(kind,'en');for(const mode of ['empty','reject','accepted'])await renderPages(kind,'en',mode,true);}
  // Help module direct: every topic, learn scenes, the error catalogue, the journal dictionary.
  {
    const s=sandbox('en');
    const api=vm.runInContext('(function(){'+moduleSource+'})()',s.ctx).create(s.ctx.lazyHelpContext());
    const inv=inventoryFixture(termsVersion?termsVersion[1]:'');
    for(const [name,fn] of [['help',()=>api.renderHelp(inv)],['learn',()=>api.renderLearn(inv)],['events catalogue',()=>api.renderErrorTable(inv)]]){
      try{collect('lazy '+name,fn());}catch(error){logCrash.push('lazy '+name+': '+(error.stack||error).toString().split('\n').slice(0,3).join(' | '));}
    }
    // Every catalogue row, journal definition and Auto blocker text.
    const c=s.ctx;
    try{
      for(const row of c.ERROR_ROWS)for(let i=2;i<row.length;i+=2){const v=row[i];if(typeof v==='string'&&(CY.test(v)||!v.trim()))add('error catalogue '+row[0],v||'(empty English field '+i+')','row field '+i);}
    }catch(error){logCrash.push('catalogue rows: '+error.message);}
    try{
      for(const key of Object.keys(c.JOURNAL_TYPES)){const t=c.JOURNAL_TYPES[key];for(const field of Object.keys(t)){const v=t[field];
        if(Array.isArray(v)&&v.length===2&&typeof v[0]==='string'){if(CY.test(v[0])||!v[0].trim())add('journal type '+key,v[0]||'(empty English '+field+')','JOURNAL_TYPES.'+field);if(!String(v[1]).trim())add('journal type '+key,'(empty Russian '+field+')','JOURNAL_TYPES.'+field);}}}
    }catch(error){logCrash.push('journal types: '+error.message);}
    try{
      for(const code of Object.keys(c.AUTO_BLOCKERS||{})){const t=c.autoBlockerText(code);if(typeof t==='string'&&CY.test(t))add('auto blocker '+code,t,'autoBlockerText');}
    }catch(error){logCrash.push('auto blockers: '+error.message);}
  }
  {
    const probe=sandbox('en');const api=vm.runInContext('(function(){'+moduleSource+'})()',probe.ctx).create(probe.ctx.lazyHelpContext());
    auditPairs('page data',probe.ctx,['window','document','console','L','rpc','ui','poll','view','request','baseclass','location','self','navigator','localStorage','sessionStorage','translations','Intl','JSON','Math']);
    try{const topics=probe.ctx.eval?null:null;}catch(error){}
  }
  sweepStates();
  // Older pattern: tr("Русский") looks the English text up in the translations map; a missing key shows Russian in English mode.
  {
    const s=sandbox('en'),TR=new RegExp('\\btr\\(\\s*('+Q+')\\s*\\)','g');let m;
    while((m=TR.exec(pageSource))){
      const literal=vm.runInContext(m[1],s.ctx);
      if(CY.test(literal)&&!Object.prototype.hasOwnProperty.call(s.ctx.translations,literal))add('tr() without an English entry',literal,'translations');
    }
    for(const key of Object.keys(s.ctx.translations))if(CY.test(s.ctx.translations[key])||!String(s.ctx.translations[key]).trim())add('translations map',key+' -> '+s.ctx.translations[key],'translations');
  }
  for(let i=0;i<10;i++)await new Promise(r=>setImmediate(r));
  const report=[];
  for(const [value,info] of found)report.push('['+info.scope+' / '+info.where+' / '+origin(value)+'] '+value.replace(/\s+/g,' ').slice(0,160));
  if(logCrash.length)console.log('CRASHES\n  '+logCrash.join('\n  '));
  if(report.length)console.log('CYRILLIC IN ENGLISH MODE ('+report.length+')\n  '+report.join('\n  '));
  if(staticProblems.length)console.log('STATIC\n  '+staticProblems.join('\n  '));
  assert.equal(logCrash.length,0,'fixture rendering must not throw');
  assert.equal(staticProblems.length,0,'bi() pairs');
  assert.equal(report.length,0,'English interface contains Russian text');
  if(process.env.EN_DBG)console.log('pairs walked',globalThis.__pairs,'listeners fired',globalThis.__fired,'notifications',globalThis.__shown);
  if(process.env.EN_DBG)console.log(failures);
  console.log('english ui ok');
})().catch(error=>{console.error(error);process.exit(1);});
