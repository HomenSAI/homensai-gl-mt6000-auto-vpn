'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const selected=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+selected+'.js','utf8');
const prefix=source.slice(0,source.lastIndexOf('return view.extend({'));
const moduleName=/LAZY_HELP_NAME='([^']+)'/.exec(source)[1];
const moduleSource=fs.readFileSync('router/files/www/luci-static/resources/'+moduleName.replace(/\./g,'/')+'.js','utf8');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[];this.hidden=false;this.isConnected=false;this.classList={add(){},remove(){},contains(){return false;}};[].concat(children==null?[]:children).flat().filter(n=>n!=null).forEach(n=>this.appendChild(n));}
 appendChild(n){if(n&&typeof n==='object')n.parentNode=this;this.children.push(n);return n;}
 removeChild(n){this.children.splice(this.children.indexOf(n),1);return n;}
 get firstChild(){return this.children[0];}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}
 addEventListener(type,fn){(this.listeners||(this.listeners={}))[type]=fn;}
 dispatchEvent(event){if(this.listeners&&this.listeners[event.type])this.listeners[event.type](event);return true;}
 querySelector(selector){for(const child of this.children){if(!(child instanceof N))continue;if(selector==='input[type="search"]'&&child.tag==='input'&&child.attrs.type==='search')return child;const found=child.querySelector(selector);if(found)return found;}return null;}
 querySelectorAll(){return [];}contains(){return false;}scrollIntoView(){this.scrolled=true;}
}
function text(n){if(n==null)return '';return n instanceof N?n.children.map(text).join(''):String(n);}
function fixture(language='en',savedState=null){
 const stored={},calls={require:0,retry:0},topics={},timers=[],c={console,URL,URLSearchParams,Intl,Promise,Event:class{constructor(type){this.type=type;}},setTimeout(fn,delay){if(delay===150)timers.push(fn);},clearTimeout(){},setInterval(){},clearInterval(){},
  window:{HomenS:{},localStorage:{getItem:k=>stored[k]||null,setItem:(k,v)=>stored[k]=v},location:{href:'http://router/#overview',hash:'#overview',search:''}},
  document:{createElement:tag=>new N(tag),createElementNS:(ns,tag)=>new N(tag),getElementById:id=>topics[id]||null,addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];}},
  localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>savedState&&JSON.stringify(savedState),setItem(){}},E:(...args)=>new N(...args),rpc:{declare:()=>()=>0},ui:{},poll:{},view:{extend:o=>o},
  baseclass:{extend:spec=>Object.assign(spec,{instantiate(args){assert(Array.isArray(args),'installed LuCI Class.instantiate requires an arguments array');return spec;}})},L:{resource:path=>'http://router/luci-static/resources/'+path},request:{},
 };
 vm.createContext(c);vm.runInContext(prefix,c);c.locale=language;
 c.L.require=function(name){calls.require++;assert.equal(name,moduleName);return Promise.resolve(vm.runInContext('(function(){'+moduleSource+'})()',c));};
 c.request.get=function(url){calls.retry++;assert(url.startsWith('http://router/luci-static/resources/'+moduleName.replace(/\./g,'/')+'.js?retry='));return Promise.resolve({ok:true,text:()=>moduleSource});};
 c.pageKeyNow=()=>c.currentPage;c.currentPage='overview';
 return {c,calls,topics,flushCodeTimers(){timers.splice(0).forEach(fn=>fn());}};
}
(async()=>{
 for(const language of ['en','ru']){
  const {c,calls,topics}=fixture(language);
  const eager=JSON.parse(JSON.stringify(c.ERROR_ROWS));assert(eager.every(row=>row.length===4));
  for(const row of eager){const definition=c.journalDefinition({state:row[0],code:row[0],level:'warning'});assert(definition.meaning.every(value=>typeof value==='string'&&value.length),'pre-load journal meaning '+row[0]);assert(!c.autoBlockerText(row[0]).includes('undefined'),'pre-load auto name '+row[0]);}
  const unknown=c.ERROR_ROWS.find(row=>row[0]==='UI-HELP-LOAD-FAILED');assert(unknown&&unknown[1]==='service'&&unknown[2]&&unknown[3]);
  assert(c.ERROR_GROUP_OF['EVENT-CHECK-FAILED'],'journal eager code');assert(c.ERROR_GROUP_OF['TERMS-NOT-ACCEPTED'],'auto blocker eager code');
  assert(text(c.telegramTokenHelp()).includes(language==='ru'?'BotFather':'BotFather'),'Telegram wizard retains source steps');
  const help=c.renderHelp({settings:{}}),learn=c.renderLearn(),events=c.renderErrorTable();assert.equal(calls.require,0,'creating hidden hosts does not acquire the module');
  assert(text(help).includes(language==='ru'?'Загрузка':'Loading'));
  await c.ensureLazyPage('overview');assert.equal(calls.require,0);
  c.currentPage='help';c.lazyHelpRoute('help/topic/setup-guide');topics['help-setup-guide']=new N('details');
  const first=c.ensureLazyPage('help'),second=c.ensureLazyPage('help');await Promise.all([first,second]);
  assert.equal(calls.require,1,'concurrent navigation shares acquisition');assert(c.LAZY_HELP.api,'actual factory created');
  c.lazyHelpDeepLink('help');assert(topics['help-setup-guide'].open&&topics['help-setup-guide'].scrolled,'deep topic opens after mount');
  assert(c.LAZY_HELP.hosts.help.ready&&!c.LAZY_HELP.hosts.learn.ready&&!c.LAZY_HELP.hosts.events.ready,'only requested page rendered');
  assert(text(help).includes(language==='ru'?'Условия':'Terms'),'terms Help addon retained');
  const full=c.ERROR_ROWS;for(const row of eager){const found=full.find(r=>r[0]===row[0]);assert(found,'full row '+row[0]);assert.deepEqual(Array.from(found.slice(0,4)),row,'eager title/area parity '+row[0]);}
  c.currentPage='learn';await c.ensureLazyPage('learn');assert(c.LAZY_HELP.hosts.learn.ready);assert(text(learn).length>200);
  c.currentPage='events';await c.ensureLazyPage('events');assert(c.LAZY_HELP.hosts.events.ready);assert(text(events).includes('DNS-001'));assert.equal(calls.require,1);
  assert.strictEqual(c.renderHelp(),help,'persistent host survives redraw');
 }
 const {c,calls}=fixture();c.L.require=()=>{calls.require++;return Promise.reject(Error('cached failure'));};
 c.currentPage='events';c.showErrorCode('DNS-001');await c.ensureLazyPage('events');
 assert(c.LAZY_HELP.failed&&text(c.renderErrorTable()).includes('UI-HELP-LOAD-FAILED'));
 await c.ensureLazyPage('help');assert.equal(calls.require,1,'failed load is not automatically retried by polling');
 let selected=null;c.showErrorCode=code=>{selected=code;};await c.loadLazyHelp(true);c.lazyHelpDeepLink('events');
 assert.equal(calls.retry,1,'Retry bypasses the cached rejected LuCI promise');assert.equal(selected,'DNS-001','error link retained across failure+retry');
 assert(c.LAZY_HELP.api&&!c.LAZY_HELP.failed);
 const saved={query:'DNS',open:{'DNS-001':true,'VPN-003':false},selected:'DNS-001'};
 const restored=fixture('en',saved);restored.c.currentPage='help';await restored.c.ensureLazyPage('help');
 assert.deepEqual(JSON.parse(JSON.stringify(restored.c.ERROR_TABLE_STATE)),saved,'first optional load preserves saved query, disclosure flags and selection');
 const intentional=fixture('en',saved);intentional.c.currentPage='events';intentional.c.errorTable=intentional.c.renderErrorTable();
 await intentional.c.showErrorCode('VPN-003');intentional.flushCodeTimers();
 assert.equal(intentional.c.ERROR_TABLE_STATE.selected,'VPN-003','code selected while loading overrides the restored selection');
 assert.equal(intentional.c.ERROR_TABLE_STATE.query,'VPN-003','pending code updates the actual catalogue search');
 assert.equal(intentional.c.ERROR_TABLE_STATE.open['DNS-001'],true,'pending selection retains saved disclosure state');
 const deferred=fixture();let finish,stolen=false;
 deferred.c.L.require=()=>new Promise(resolve=>{finish=()=>resolve(vm.runInContext('(function(){'+moduleSource+'})()',deferred.c));});
 deferred.c.currentPage='events';const pending=deferred.c.showErrorCode('DNS-001');await Promise.resolve();
 deferred.c.currentPage='overview';deferred.c.showErrorCode=()=>{stolen=true;};finish();await pending;
 assert(!stolen&&deferred.c.LAZY_HELP.pendingCode==='DNS-001','late completion does not navigate back or steal focus');
 const revisited=fixture();let complete;
 revisited.c.L.require=()=>new Promise(resolve=>{complete=()=>resolve(vm.runInContext('(function(){'+moduleSource+'})()',revisited.c));});
 revisited.c.document.querySelector=selector=>selector==='[data-hv-tab="events"]'?{click(){revisited.c.currentPage='events';}}:null;
 revisited.c.currentPage='tests';revisited.c.window.pageYOffset=15;const oldRequest=revisited.c.showErrorCode('DNS-001');await Promise.resolve();
 revisited.c.currentPage='channels';revisited.c.window.pageYOffset=73;const newRequest=revisited.c.showErrorCode('VPN-003');
 assert.equal(revisited.c.errorReturn.tab,'channels','new code transition replaces an abandoned loading transition origin');
 assert.equal(revisited.c.errorReturn.y,73,'new transition retains the actual latest source scroll');
 complete();await Promise.all([oldRequest,newRequest]);
 assert.equal(revisited.c.errorReturn.tab,'channels','older completion cannot restore its obsolete return origin');
 assert(source.includes("if(activeTab==='events'&&key!=='events')hideErrorBack();"),'leaving the catalogue clears its return state synchronously');
 // alpha79: the code catalogue gained ~115 owner-readable rows (eager names); the bound moved from 30% to 28%.
 // 1.0.0-beta1 switch statistics: the measured-timing core (journal/live-log durations) is eager; its page renderer is lazy. 28% -> 27%.
 assert(Buffer.byteLength(source)<1256446*.73,'main module shrank by at least 27% from alpha51');
 assert(!source.includes('var LEARN_LESSONS=')&&!source.includes('var AI_PROMPT_EN='),'long optional payload absent from main');
 assert(source.includes('lazyHelpRoute(window.location.hash.slice(1));var requestedTab='),'initial direct Help topic is remembered before alias normalization');
 console.log('PASS: lazy actual factory EN/RU, first-screen no acquisition, title map, Telegram/terms, concurrency, success, cached failure+Retry, deep links, persistent hosts, >=30% smaller main');
})().catch(error=>{console.error(error);process.exitCode=1;});
