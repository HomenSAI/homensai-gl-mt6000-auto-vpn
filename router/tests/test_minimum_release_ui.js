/* Independent revision-3 contract checks. This is a Node model suite, not native
   browser/device acceptance. Requirements come from the accepted five-section UI. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const touched=[];
const forbidden=new Proxy({}, {get(_,key){touched.push(String(key));throw new Error('Unexpected side effect: '+String(key));}});
const c={URL,window:forbidden,document:forbidden,localStorage:forbidden,rpc:forbidden};
vm.createContext(c);
for(const name of ['minimum_navigation','navigation_context','simple_home_policy'])
  vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
const plain=value=>JSON.parse(JSON.stringify(value));

assert.deepStrictEqual(plain(c.MINIMUM_MAIN_PAGES),['channels','diagnostics','events','settings','help'],
  'Exactly five advanced menu destinations; home is not a sixth advanced item');

// Opening a display page cannot establish operational readiness from preferences.
for(const evidence of [null,undefined,{},false,[],{localStorageReady:true},
  {statusFresh:false,controllerFresh:false,autoRunning:true},
  {statusFresh:true,controllerFresh:true,autoRunning:false},
  {statusFresh:'true',controllerFresh:1,autoRunning:true},
  {termsAccepted:false,onboardingComplete:false,setupComplete:false}]){
  const before=JSON.stringify(evidence),entry=c.simpleHomeEntry(evidence);
  assert.strictEqual(entry.page,'home');assert.strictEqual(entry.showCard,true);
  assert.strictEqual(entry.autoRunning,false,'Unknown/off display never asserts running Auto');
  assert.strictEqual(JSON.stringify(evidence),before,'Display policy does not mutate evidence');
}
assert.strictEqual(c.simpleHomeEntry({statusFresh:true,controllerFresh:true,autoRunning:true}).autoRunning,true);

// Accepted old bookmarks retain the feature, not just the nearest main page.
const aliases={overview:['home','summary'],start:['settings','setup'],tests:['diagnostics','checks'],
  readiness:['diagnostics','readiness'],services:['diagnostics','technical'],ranking:['diagnostics','speed'],
  statistics:['events','statistics'],traffic:['events','traffic'],learn:['help','training'],
  home:['home','summary'],channels:['channels','pair'],events:['events','journal'],
  settings:['settings','main'],help:['help','topics']};
for(const [hash,[page,subview]] of Object.entries(aliases)){
  const result=c.minimumRoute('#'+hash);assert.strictEqual(result.page,page,hash);assert.strictEqual(result.subview,subview,hash);
  assert.strictEqual(result.recognized,true,hash);assert.deepStrictEqual(plain(c.minimumRoute(result.hash)),{...plain(result),legacy:false});
}
for(const hash of ['',null,{},'#missing','diagnostics/unknown','events/traffic/extra','channels/',
  'settings/%2fsetup','help/topic','help/topic/../','help/topic/%ZZ','help/topic/a%2fb','__proto__','constructor']){
  const result=c.minimumRoute(hash);assert.strictEqual(result.page,'home',String(hash));
  assert.strictEqual(result.subview,'summary');
}
for(const hash of ['diagnostics/recovery','diagnostics/speed','events/traffic','help/about','help/training','help/topic/VPN-003'])
  assert.strictEqual(c.minimumRoute(hash).recognized,true,hash);

// The first expanded entry is Channels; subsequent returns retain the subview.
let state=c.minimumNavigationState('home');
assert.strictEqual(c.minimumAdvancedRoute(state).hash,'channels');
state=c.minimumNavigationTransition(state,'services');
const prior=JSON.stringify(state);const home=c.minimumNavigationTransition(state,'home');
assert.strictEqual(JSON.stringify(state),prior,'Navigation transition does not mutate prior state');
assert.strictEqual(home.route.page,'home');assert.strictEqual(c.minimumAdvancedRoute(home).hash,'diagnostics/technical');
state=c.minimumNavigationTransition(home,'traffic');state=c.minimumNavigationTransition(state,'home');
assert.strictEqual(c.minimumAdvancedRoute(state).hash,'events/traffic');

for(const [hash,page] of [['#diagnostics/speed','diagnostics'],['#help/topic/VPN-003','help'],['#events/traffic','events']]){
  const before='http://127.0.0.1/ui?lang=en&setup=telegram'+hash;
  const after=new URL(c.languageNavigationUrl(before,'ru',page));
  assert.strictEqual(after.hash,hash,'Language preserves current subview/deep link');
  assert.strictEqual(after.searchParams.get('lang'),'ru');assert.strictEqual(after.searchParams.has('setup'),false);
  assert.strictEqual(after.origin,new URL(before).origin);
}
assert.strictEqual(c.minimumRouteFromUrl('http://127.0.0.1/ui?setup=telegram#settings').hash,'settings/setup');
assert.strictEqual(c.minimumRouteFromUrl('http://127.0.0.1/ui?setup=telegram#channels').hash,'channels');
assert.deepStrictEqual(touched,[],'Route/language/policy functions perform no browser, storage or RPC operations');
console.log('PASS: revision-3 five sections, OFF/UNKNOWN display without readiness, aliases, retained expanded subviews, language deep links and no navigation side effects (model only)');

// Channel inventory is read-only and independent of selection/health coloring.
{
 class Node{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.textContent='';this.hidden=false;[].concat(children).flat().forEach(n=>this.appendChild(n));}
  appendChild(n){if(n!=null){if(n instanceof Node)n.parentNode=this;this.children.push(n);}return n;}
  all(){return [this,...this.children.flatMap(n=>n instanceof Node?n.all():[])];}
  text(){return this.textContent+this.children.map(n=>n instanceof Node?n.text():String(n)).join(' ');}
 }
 for(const language of ['en','ru']){
  const profiles=[{id:'a',name:'Primary observed',protocol:'wireguard',host:'primary.example',time:1000,rtt_ms:40},
   {id:'b',name:'Reserve observed',protocol:'openvpn',host:'reserve.example',time:1000,rtt_ms:60},
   {id:'c',name:'Third observed',protocol:'openvpn',host:'third.example',time:1000,rtt_ms:80}];
  let unavailable=false;
  const health={state:'healthy',label:language==='ru'?'Доступен':'Available'};
  const q={locale:language,E:(...args)=>new Node(...args),bi:(en,ru)=>language==='ru'?ru:en,Date,
   statusNow:()=>1000,manualFresh:(stamp,now,limit)=>now-stamp>=0&&now-stamp<=limit,
   simpleHomeModel:()=>({source:profiles[0],target:profiles[1],sourceHealth:unavailable?{state:'unknown',label:'Unknown'}:health,targetHealth:unavailable?{state:'unknown',label:'Unknown'}:health,selectedRole:unavailable?null:'source',dataUnavailable:unavailable}),
   simpleHomeHealth:(_,now,missing)=>missing?{state:'unknown',label:'Unknown'}:health,
   endpointText:p=>p&&p.host||'No address',protocolLabel:p=>p.protocol,countryName:()=> 'Germany',
   rpc:forbidden,window:forbidden,document:forbidden};
  vm.createContext(q);vm.runInContext(fs.readFileSync('router/minimum_channels.inc.js','utf8'),q);
  const inventory={profiles:[...profiles,profiles[2]],servers:[{profile:'a',name:'Saved primary'},{profile:'c',name:'Third saved'}]};
  const before=JSON.stringify(inventory),page=q.renderMinimumChannels({profiles},inventory,'http://router/#vpn');
  assert.strictEqual(JSON.stringify(inventory),before,'Rendering retains original inventory');
  const cards=page.all().filter(n=>n.attrs['data-minimum-channel']);assert.strictEqual(cards.length,2);
  assert(cards[0].text().includes('Saved primary'),'Configured display name wins over endpoint');
  assert(!/failed|inactive/.test(cards[1].attrs.class),'Healthy reserve is neutral despite not being selected');
  const disclosure=page.all().find(n=>n.attrs['data-minimum-details']==='other-profiles');assert(disclosure&&!disclosure.attrs.open);
  const rows=disclosure.all().filter(n=>n.attrs.class==='hv-minimum-profile-row');assert.strictEqual(rows.length,1,'Selected and duplicate profiles excluded');
  const search=disclosure.all().find(n=>n.tag==='input');search.value='no matching name';search.attrs.input();assert(rows[0].hidden);
  search.value='third saved';search.attrs.input();assert(!rows[0].hidden);assert.strictEqual(touched.length,0,'Searching never invokes commands');
  unavailable=true;const unknown=q.renderMinimumChannels({profiles},inventory,null);
  unknown.all().filter(n=>n.attrs['data-minimum-channel']).forEach(n=>assert(n.attrs.class.includes('health-unknown'),'Stale evidence cannot remain a healthy card'));
  assert(!unknown.all().some(n=>n.tag==='a'&&n.attrs.target==='_blank'),'Missing router origin never creates a guessed link');
 }
 console.log('PASS: selected pair, neutral healthy reserve, configured names, collapsed deduplicated other profiles and no RPC from filtering (model only)');
}

// Compose real source nodes once, keeping the sole authoritative command alive
// when switching home/advanced subviews. A small DOM models reparenting here.
{
 class Dom{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs={...attrs};this.children=[];this.parentNode=null;this.hidden=false;[].concat(children).flat().forEach(n=>this.appendChild(n));}
  appendChild(n){if(n!=null){if(n instanceof Dom){if(n.parentNode)n.parentNode.removeChild(n);n.parentNode=this;}this.children.push(n);}return n;}
  removeChild(n){const i=this.children.indexOf(n);assert(i>=0);this.children.splice(i,1);if(n instanceof Dom)n.parentNode=null;return n;}
  insertBefore(n,before){if(n instanceof Dom&&n.parentNode)n.parentNode.removeChild(n);const i=this.children.indexOf(before);if(i<0)return this.appendChild(n);if(n instanceof Dom)n.parentNode=this;this.children.splice(i,0,n);return n;}
  get firstChild(){return this.children[0]||null;}
  get tagName(){return this.tag.toUpperCase();}
  all(){return [this,...this.children.flatMap(n=>n instanceof Dom?n.all():[])];}
  getAttribute(k){return this.attrs[k]??null;}setAttribute(k,v){this.attrs[k]=String(v);}removeAttribute(k){delete this.attrs[k];}
  matches(selector){if(selector.startsWith('.'))return (this.attrs.class||'').split(/\s+/).includes(selector.slice(1));const m=/^\[([^=\]]+)(?:="([^"]*)")?\]$/.exec(selector);return !!m&&Object.hasOwn(this.attrs,m[1])&&(m[2]===undefined||this.attrs[m[1]]===m[2]);}
  querySelectorAll(s){return this.all().slice(1).filter(n=>n.matches(s));}querySelector(s){return this.querySelectorAll(s)[0]||null;}
 }
 const E=(...args)=>new Dom(...args),panel=E('div'),command=E('section'),legacy={};
 for(const page of ['home','overview','channels','tests','readiness','settings','services','events','statistics','traffic','help','learn','start','ranking']){
  legacy[page]=E('section',{'data-hv-page':page},page);panel.appendChild(legacy[page]);
 }
 const power=E('button',{'class':'hv-auto-power'}),action=E('span',{'class':'hv-auto-action'});
 const homePower=E('div',{'class':'hv-simple-power'},power),homeAction=E('div',{},[homePower,action]);legacy.home.appendChild(homeAction);
 const monitor=E('section',{'class':'hv-connectivity-control','data-test-monitor':'1'}),scanAction=E('button',{'class':'hv-connectivity-action'}),connectivity=E('section',{'class':'hv-connectivity-control'},scanAction),manual=E('section',{'class':'hv-manual-switch','data-manual-controls':'1'});
 const liveStatistics=E('details',{'class':'hv-auto-statistics'}),hold=E('details',{'class':'hv-auto-hold'}),scope=E('details',{'class':'hv-auto-scope'});
 const control=E('div',{'class':'hv-auto-sections'},[E('section',{'class':'hv-auto-control'},[monitor,connectivity,hold,scope]),manual,liveStatistics]);legacy.overview.appendChild(control);
 const errors=E('section',{'class':'hv-errtable'});legacy.events.appendChild(errors);
 const journal=E('section',{'data-event-history':'1'}),analytics=E('section',{'data-test-analytics':'1'}),download=E('button',{},'Download');
 legacy.events.appendChild(journal);legacy.events.appendChild(analytics);legacy.events.appendChild(download);
 const speedPanel=E('section',{'class':'hv-speed-panel'}),cascade=E('section',{'class':'hv-cascade'});
 legacy.tests.appendChild(cascade);legacy.tests.appendChild(speedPanel);
 const status={time:1000,system_readiness:{time:800,checks:[{code:'DEPENDENCY-UCI',state:'pass'}]},native_failover:{time:1000,blockers:['VPN-POLICY-DISABLED']}};
 const q={E,bi:en=>en,Date,statusNow:()=>1000,
  simpleHomeModel:()=>({title:'Current state',summary:'Current route',dataUnavailable:false}),
  autoReadiness:()=>({steps:[],next:null,ready:false}),autoCodeNotice:code=>E('code',{},code),
  renderReadiness:()=>E('section',{'data-rendered-readiness':'1'}),renderMinimumChannels:()=>E('section',{'data-rendered-channels':'1'}),
  renderMinimumHelp:node=>E('section',{},node),EVENT_VIEW:{page:0,draw(){}},rpc:forbidden,window:forbidden,document:forbidden};
 vm.createContext(q);vm.runInContext(fs.readFileSync('router/readiness_panel.inc.js','utf8'),q);
 // Override only the full read-only renderer; the actual environment-freshness model is used.
 q.renderReadiness=()=>E('section',{'data-rendered-readiness':'1'});
 vm.runInContext(fs.readFileSync('router/minimum_sections.inc.js','utf8'),q);
 const composed=q.minimumComposePages(legacy,panel,status,{settings:{}},control,command,null),root=E('div',{},[command,panel]);
 assert.deepStrictEqual(Object.keys(composed.pages).sort(),['channels','diagnostics','events','help','home','settings']);
 assert.strictEqual(root.querySelectorAll('[data-hv-page]').length,6,'Legacy page roots cannot compete with canonical destinations');
 assert.strictEqual(root.all().filter(n=>n===power).length,1,'Authoritative power has one DOM instance');
 assert(composed.pages.channels.all().includes(manual),'Manual command is retained under Channels');
 assert(composed.pages.events.all().includes(liveStatistics),'Existing real-time history is retained');
 assert(composed.pages.help.all().includes(errors),'Diagnostic codes remain reachable in Help');
 assert(composed.pages.diagnostics.all().includes(hold),'Held-reserve recovery is retained');
 const connectionChecks=composed.pages.diagnostics.querySelector('[data-minimum-subview="diagnostics/checks"]');
 assert(connectionChecks.all().includes(scanAction),'Checks must expose the actual scan action, not the same-class monitor block');
 assert(!connectionChecks.all().includes(monitor),'Monitoring status is distinct from explicit connection-check action');
 const eventDetails=composed.pages.events.querySelector('[data-minimum-disclosure="event-analytics"]');
 assert(eventDetails&&!eventDetails.attrs.open&&eventDetails.all().includes(analytics),'Event analytics are retained but collapsed by default');
 assert(!eventDetails.all().includes(journal)&&!eventDetails.all().includes(download),'Primary journal and export stay outside detailed analytics');
 const speedView=composed.pages.diagnostics.querySelector('[data-minimum-subview="diagnostics/speed"]');
 assert.strictEqual(speedPanel.parentNode,speedView,'Actual speed controls are primary, not buried among rankings');
 const speedDetails=composed.pages.diagnostics.querySelector('[data-minimum-disclosure="speed-settings"]');
 assert(speedDetails&&!speedDetails.attrs.open&&speedDetails.all().includes(cascade),'Other test/ranking details remain collapsed');
 assert(!composed.pages.diagnostics.querySelector('[data-minimum-disclosure="passed-checks"]'),'Stale environment cannot produce passed-check count');
 q.minimumApplyRoute(root,{page:'home',subview:'summary'},composed.control);assert.strictEqual(power.parentNode,homePower);assert.strictEqual(action.parentNode,homeAction);
 q.minimumApplyRoute(root,{page:'diagnostics',subview:'recovery'},composed.control);assert.strictEqual(power.parentNode,composed.control.fullPower);assert.strictEqual(action.parentNode,command);
 assert.strictEqual(composed.pages.diagnostics.querySelector('[data-minimum-subview="diagnostics/recovery"]').hidden,false);
 assert.strictEqual(composed.pages.diagnostics.querySelector('[data-minimum-subview="diagnostics/speed"]').hidden,true);
 q.minimumApplyRoute(root,{page:'home',subview:'summary'},composed.control);assert.strictEqual(power.parentNode,homePower);assert.strictEqual(action.parentNode,homeAction);
 q.minimumApplyRoute(root,{page:'help',subview:'topic',topic:'no-internet'},composed.control);
 assert.strictEqual(composed.pages.help.querySelector('[data-minimum-subview="help/topics"]').hidden,false,'A help topic deep link keeps the topics content visible');
 assert.strictEqual(touched.length,0,'Composition/route application invokes no RPC or browser commands');
 console.log('PASS: actual composition preserves unique command identity, recovery/manual/history/code nodes, canonical pages and stale environment handling (model only)');
}

{
 const outer={tagName:'DETAILS',open:false,parentElement:null},inner={tagName:'DETAILS',open:false,parentElement:outer};
 let scrolls=0;const topic={tagName:'DETAILS',open:false,parentElement:inner,scrollIntoView(){scrolls++;}};
 const opened=[],q={document:{getElementById:id=>id==='help-no-internet'?topic:null},window:forbidden};
 vm.createContext(q);vm.runInContext(fs.readFileSync('router/minimum_sections.inc.js','utf8'),q);
 q.minimumNavigate=path=>{opened.push(path);return true;};
 q.openHelpTopic('no-internet');assert.deepStrictEqual(opened,['help/topic/no-internet']);
 for(const invalid of [null,{},'',"a\"]bad",'../settings','x/y','a'.repeat(97)])q.openHelpTopic(invalid);
 assert.strictEqual(opened.length,1,'Malformed help ids never produce navigation');
 q.minimumRevealTopic('no-internet');assert(topic.open&&inner.open&&outer.open,'Deep-linked topic opens all enclosing disclosures');assert.strictEqual(scrolls,1);
 console.log('PASS: Help topic navigation retains its canonical deep link, rejects malformed ids and opens ancestor disclosures without commands');
}

{
 const rows=[{key:'recent-error',time:99999,level:'error',origin:'failures'},
  {key:'recent-switch',time:99998,level:'ok',origin:'controller'},
  {key:'control',time:99997,level:'warning',origin:'control',kind:'CONTROL'},
  {key:'old-error',time:1000,level:'error',origin:'failures'}],forwarded=[];
 const q={Date,statusNow:()=>100000,retainedFilteredJournalRows:(items,status,query,sort,desc)=>{forwarded.push({query,sort,desc});return items;}};
 vm.createContext(q);vm.runInContext(fs.readFileSync('router/minimum_sections.inc.js','utf8'),q);
 const before=JSON.stringify(rows),keys=result=>Array.from(result,row=>row.key);
 assert.deepStrictEqual(keys(q.filteredJournalRows(rows,{},'needle','time',true)),['recent-error','recent-switch','control']);
 q.MINIMUM_JOURNAL_FILTER.type='errors';assert.deepStrictEqual(keys(q.filteredJournalRows(rows,{},'','state',false)),['recent-error']);
 q.MINIMUM_JOURNAL_FILTER.type='switches';assert.deepStrictEqual(keys(q.filteredJournalRows(rows,{},'','time',true)),['recent-switch','control']);
 q.MINIMUM_JOURNAL_FILTER.period='all';q.MINIMUM_JOURNAL_FILTER.type='all';assert.deepStrictEqual(keys(q.filteredJournalRows(rows,{},'','time',true)),rows.map(row=>row.key));
 assert.deepStrictEqual(forwarded[0],{query:'needle',sort:'time',desc:true},'Existing retained search/sort contract is preserved');
 assert.strictEqual(JSON.stringify(rows),before,'Filters do not mutate retained history');
 console.log('PASS: journal period/type filtering preserves retained search/sort and original history');
}

// An incomplete pair is a fresh OFF display state, never a new Start permission.
{
 class Node{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs={...attrs};this.children=[].concat(children).flat().filter(n=>n!=null);this.classList={add(){}};this.disabled=attrs.disabled!=null;}
  setAttribute(k,v){this.attrs[k]=String(v);}all(){return [this,...this.children.flatMap(n=>n instanceof Node?n.all():[])];}
 }
 for(const language of ['en','ru']){
  let members={source:null,target:null};const q={E:(...args)=>new Node(...args),bi:(en,ru)=>language==='ru'?ru:en,Date,
   vendorDisplayMember:(_s,_i,role)=>members[role],statusNow:()=>1000,countryName:()=>'',protocolLabel:p=>p.protocol,
   endpointText:p=>p&&p.host||'No observed endpoint',rpc:forbidden,window:forbidden};
  vm.createContext(q);for(const name of ['ui_logic','auto_panel','manual_panel','simple_home_policy','simple_home_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),q);
  const profile=id=>({id,name:id,time:1000,interface:'wgclient1',protocol:'wireguard',dns_ok:true,https_success:2});
  const off={time:1000,profiles:[],native_failover:{time:1000,state:'STOPPED'},auto_control:{requested:'off',pair_phase:'STOPPED'}};
  const inv={settings:{setup_complete:false,onboarding_complete:false}};
  const cases=[
   {pair:{source:null,target:null},status:off,setup:true},
   {pair:{source:profile('a'),target:null},status:off,setup:true},
   {pair:{source:profile('a'),target:profile('a')},status:off,setup:true},
   {pair:{source:profile('a'),target:profile('b')},status:off,setup:false},
   {pair:{source:null,target:null},status:{...off,rpc_error:'RPC-UNAVAILABLE'},setup:false},
   {pair:{source:null,target:null},status:{...off,time:800},setup:false},
   {pair:{source:null,target:null},status:{...off,native_failover:{time:1000,state:'OBSERVING',certified:true},auto_control:{requested:'on',pair_phase:'RUNNING'}},setup:false},
   {pair:{source:null,target:null},status:{...off,native_failover:{time:1000,state:'ARMED'},auto_control:{requested:'on',pair_phase:'STARTING'}},setup:false}
  ];
  for(const test of cases){
   members=test.pair;const model=q.simpleHomeModel(test.status,inv,1000);assert.strictEqual(model.setupRequired,test.setup);
   if(test.setup)assert.strictEqual(model.state,'setup');
   const power=new Node('button',{'class':'hv-auto-power',disabled:''}),action=new Node('span',{'class':'hv-auto-action'});
   const card=q.renderSimpleHome(test.status,inv,model,{querySelector:s=>s==='.hv-auto-power'?power:action},()=>{});
   assert.strictEqual(card.all().find(n=>n.attrs['data-simple-home-auto']),power,'Setup state retains exact existing authoritative button');assert(power.disabled,'Display cannot override authoritative disabled state');
   const setup=card.all().filter(n=>n.attrs['data-simple-setup']);assert.strictEqual(setup.length,test.setup?1:0);
   if(test.setup){assert.strictEqual(setup[0].tag,'a');assert.strictEqual(setup[0].attrs.href,'#settings');assert.strictEqual(setup[0].attrs.click,undefined,'Configure pair is navigation, not an implicit writer');}
  }
 }
 assert.strictEqual(touched.length,0,'Missing-pair rendering performs no RPC');
 console.log('PASS: missing/same pair prompts setup only with fresh idle OFF; running/pending/stale stay truthful and authoritative Auto identity/permissions are retained EN/RU');
}
