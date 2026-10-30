'use strict';
// Measured switch timing: episodes from saved controller/failure events, durations in the journal/live log, and the
// Advanced > Switch statistics page (lazy renderer) in EN/RU with automatic, manual and incomplete episodes.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const selected=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+selected+'.js','utf8');
const prefix=source.slice(0,source.lastIndexOf('return view.extend({'));
const moduleName=/LAZY_HELP_NAME='([^']+)'/.exec(source)[1];
const moduleSource=fs.readFileSync('router/files/www/luci-static/resources/'+moduleName.replace(/\./g,'/')+'.js','utf8');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[];this.hidden=false;this.classList={add(){},remove(){},contains(){return false;}};[].concat(children==null?[]:children).flat(Infinity).filter(n=>n!=null&&n!==false).forEach(n=>this.appendChild(n));}
 appendChild(n){if(n&&typeof n==='object')n.parentNode=this;this.children.push(n);return n;}
 removeChild(n){this.children.splice(this.children.indexOf(n),1);return n;}
 insertBefore(n,r){const o=this.children.indexOf(n);if(o>=0)this.children.splice(o,1);const i=r?this.children.indexOf(r):-1;if(i<0)this.children.push(n);else this.children.splice(i,0,n);n.parentNode=this;return n;}
 get firstChild(){return this.children[0];}
 set textContent(v){this.children=[String(v)];}get textContent(){return text(this);}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}
 addEventListener(){}querySelector(){return null;}querySelectorAll(){return [];}contains(){return false;}
 all(){return [this].concat(...this.children.filter(c=>c instanceof N).map(c=>c.all()));}
}
function text(n){if(n==null)return '';return n instanceof N?n.children.map(text).join(' '):String(n);}
function context(language){
 const c={console,URL,URLSearchParams,Intl,Promise,setTimeout(){},clearTimeout(){},setInterval(){},clearInterval(){},
  window:{HomenS:{},localStorage:{getItem:()=>null,setItem(){}},location:{href:'http://router/#switches',hash:'#switches',search:''}},
  document:{body:{contains:()=>false},createElement:tag=>new N(tag),createElementNS:(ns,tag)=>new N(tag),getElementById:()=>null,addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];}},
  localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>null,setItem(){}},E:(...args)=>new N(...args),rpc:{declare:()=>()=>0},ui:{},poll:{},view:{extend:o=>o},
  baseclass:{extend:spec=>Object.assign(spec,{instantiate(){return spec;}})},L:{resource:p=>p},request:{}};
 vm.createContext(c);vm.runInContext(prefix,c);c.locale=language;
 c.L.require=()=>Promise.resolve(vm.runInContext('(function(){'+moduleSource+'})()',c));
 c.pageKeyNow=()=>'switches';
 return c;
}
const P='wireguard:peer_1',R='openvpn:1_2',T0=Math.floor(Date.now()/1000)-5300;
const meta=(from,to,extra)=>Object.assign({source:P,target:R,transition_metadata_present:true,from_role:from,from_profile_id:from==='source'?P:R,destination_role:to,destination_profile_id:to==='source'?P:R,route_changed:true},extra||{});
function status(){
 return {profiles:[{id:P,name:'Primary'},{id:R,name:'Reserve'}],switch_timing:{avg_seconds:61.4,count:5,last_seconds:58},
  accounting:{reliability:{events:[
   {sequence:1,time:T0,profile:P,kind:'FAILURE',code:'VPN-001',role:'source'},
   {sequence:2,time:T0+200,profile:P,kind:'RECOVERY',role:'source',observed_duration_seconds:195},
   {sequence:3,time:T0+5000,profile:P,kind:'FAILURE',code:'VPN-003',role:'source'}]}},
  native_history:{events:[
   // 1) automatic: first failed check T0, switch start +52, on reserve +113 (61 s), return start +230, back +275 (45 s)
   {sequence:10,time:T0+52,state:'APPLYING',codes:['SOURCE-FAILED'],transition_source:'automatic',...meta('source','target')},
   {sequence:11,time:T0+113,state:'COMMITTED',codes:['CLIENT-CONFIRMED'],transition_source:'automatic',...meta('source','target',{transition_completed:true,transition_outcome:'committed'})},
   {sequence:12,time:T0+113,state:'COMMITTED',codes:['CLIENT-CONFIRMED'],source:P,target:R},
   {sequence:13,time:T0+230,state:'RESTORING',codes:['PRIMARY-STABLY-RECOVERED'],...meta('target','source')},
   {sequence:14,time:T0+275,state:'ROLLED-BACK',codes:['PRIMARY-STABLY-RECOVERED'],original_restored:true,...meta('target','source',{transition_completed:true,transition_outcome:'restored'})},
   // 2) manual switch and manual return (OBSERVING completion), no failure
   {sequence:20,time:T0+1000,state:'APPLYING',codes:['OPERATOR-MANUAL'],manual:true,transition_source:'manual',...meta('source','target')},
   {sequence:21,time:T0+1070,state:'STOPPED-ON-RESERVE',codes:['OPERATOR-MANUAL'],transition_source:'manual',...meta('source','target',{transition_completed:true,transition_outcome:'committed'})},
   {sequence:22,time:T0+3000,state:'APPLYING',codes:['OPERATOR-MANUAL'],transition_source:'manual',...meta('target','source')},
   {sequence:23,time:T0+3050,state:'OBSERVING',codes:['OPERATOR-MANUAL'],transition_source:'manual',...meta('target','source',{transition_completed:true,transition_outcome:'committed'})},
   // 3) missing pieces: commit saved without its start (legacy, no metadata), return end never saved
   {sequence:30,time:T0+4000,state:'COMMITTED',codes:['CLIENT-CONFIRMED'],source:P,target:R},
   {sequence:31,time:T0+4500,state:'RESTORING',codes:['PRIMARY-STABLY-RECOVERED'],source:P,target:R},
   // 4) automatic attempt with failure at +5000 that is still switching
   {sequence:40,time:T0+5040,state:'APPLYING',codes:['SOURCE-FAILED'],transition_source:'automatic',...meta('source','target')}]}};
}
(async()=>{
 for(const language of ['en','ru']){
  const c=context(language),st=status(),now=Date.now()/1000;
  const rows=c.journalRows(st,null,now),episodes=c.switchTimeline(rows);
  assert.equal(episodes.length,4,'four episodes');
  const [auto,manual,partial,current]=episodes;
  assert.equal(auto.kind,'auto');assert.equal(auto.detect,52);assert.equal(auto.switching,61);assert.equal(auto.total,113);assert.equal(auto.onReserve,117);assert.equal(auto.returning,45);assert.equal(auto.down,195);
  assert.equal(manual.kind,'manual');assert.equal(manual.returnKind,'manual');assert.strictEqual(manual.detect,null,'manual switch has no detection');assert.equal(manual.switching,70);assert.strictEqual(manual.total,null);
  assert.equal(manual.onReserve,1930);assert.equal(manual.returning,50);
  assert.strictEqual(partial.start,null);assert.strictEqual(partial.switching,null,'missing start is never invented');assert.equal(partial.onReserve,500);assert.strictEqual(partial.back,null);assert.strictEqual(partial.returning,null);
  assert.equal(current.detect,40);assert.strictEqual(current.reserve,null);
  // The same records carry the durations in Events and errors and in the live log.
  const byKey=k=>rows.find(r=>r.key==='controller:'+k);
  const msg=k=>c.journalMessage(byKey(k),st,true);
  if(language==='en'){
   assert(msg(10).includes('failure confirmed 52 s after the first failed check'),msg(10));
   assert(msg(11).includes('switch took 1 min 1 s (from switch start)')&&msg(11).includes('from the first failed check 1 min 53 s'),msg(11));
   assert(!byKey(12).timing,'duplicate commit carries no second measurement');
   assert(msg(13).includes('on the reserve for 1 min 57 s'),msg(13));
   assert(msg(14).includes('return took 45 s (from return start)')&&msg(14).includes('whole episode 4 min 35 s'),msg(14));
   assert(msg(23).includes('return took 50 s'),msg(23));
   const recovery=rows.find(r=>r.kind==='RECOVERY');assert(c.journalMessage(recovery,st,true).includes('primary channel was down 3 min 15 s'));
  }else{
   assert(msg(10).includes('сбой подтверждён за 52 с после первой неудачной проверки'),msg(10));
   assert(msg(11).includes('переключение 1 мин 1 с (с начала перехода)'),msg(11));
   assert(msg(14).includes('возврат 45 с (с начала возврата)'),msg(14));
   const recovery=rows.find(r=>r.kind==='RECOVERY');assert(c.journalMessage(recovery,st,true).includes('основной канал не работал 3 мин 15 с'));
  }
  // Live terminal uses the same annotated rows.
  const live=c.renderLiveTerminal(st,{settings:{}});assert(text(live).includes(language==='en'?'switch took 1 min 1 s':'переключение 1 мин 1 с'),'live log shows durations');
  // Page: lazy host, then the real renderer after the module is loaded.
  const host=c.renderSwitchStats(st);assert(text(host).includes(language==='en'?'Loading':'Загрузка'));
  await c.ensureLazyPage('switches');
  const page=c.renderSwitchStats(st),all=text(page);
  assert(page.all().some(n=>n.attrs['data-switch-cards']),'summary cards');
  assert(page.all().some(n=>n.tag==='svg'),'phase chart always drawn');
  const table=page.all().find(n=>n.attrs['data-switch-table']);assert(table,'table');
  assert.equal(table.children.length,1+4+1,'header, four episodes, mean row');
  assert.equal(page.all().filter(n=>n.tag==='rect').length,4+3+1+2,'phase segments incl. still running');assert.equal(page.all().filter(n=>n.tag==='rect'&&n.attrs['fill-opacity']).length,1,'running switch drawn up to now');assert(all.includes(language==='en'?'Switching now':'Идёт переключение'));
  assert(all.includes(language==='en'?'Switch statistics':'Статистика переключений'));
  assert(all.includes('1 min 1 s')||all.includes('1 мин 1 с'));
  assert(all.includes(language==='en'?'Router switch average':'Среднее роутера')&&all.includes(language==='en'?'1 min 1 s':'1 мин 1 с'));
  if(language==='en')assert(!/[Ѐ-ӿ]/.test(all),'no Cyrillic in English: '+(all.match(/.{0,40}[Ѐ-ӿ].{0,40}/)||[''])[0]);
  else assert(/[Ѐ-ӿ]/.test(all));
  // Empty state, and a history that has not arrived yet.
  const api=c.LAZY_HELP.api;
  const empty=text(api.renderSwitchPage({episodes:[],history:true,timing:null}));assert(empty.includes(language==='en'?'No switches in the saved history yet':'В сохранённой истории пока нет переключений'));
  const waiting=text(api.renderSwitchPage({episodes:[],history:false}));assert(waiting.includes(language==='en'?'has not arrived yet':'ещё не загружена'));
  if(language==='en')assert(!/[Ѐ-ӿ]/.test(empty+waiting));


 }
 const c=context('en');assert.equal(c.spanText(59.6),'1 min');assert.equal(c.spanText(3725),'1 h 2 min');assert.equal(c.spanText(-1),'—');assert.equal(c.spanText(null),'—');
 assert(source.includes("['switches','⏱',"),'Advanced tab');assert(source.includes("var ADVANCED_KEYS=['tests','statistics','traffic','services','events','switches'];"));
 assert(source.includes("'analytics','switches'].indexOf(page)>=0?60000"),'history refresh every minute on the page');
 console.log('PASS: switch episodes (auto/manual/missing/running), journal+live-log durations, Switch statistics page EN/RU, empty states');
})().catch(error=>{console.error(error);process.exitCode=1;});
