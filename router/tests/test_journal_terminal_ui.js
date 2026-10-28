const fs=require('fs'),vm=require('vm'),assert=require('assert');const {website}=require('./website_fixture');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(n=>n!=null);this.scrollTop=0;this.clientHeight=100;this.offsetHeight=20;this._text='';}
 appendChild(n){const old=this.children.indexOf(n);if(old>=0)this.children.splice(old,1);this.children.push(n);return n;}insertBefore(n,before){if(n===before)return n;const old=this.children.indexOf(n);if(old>=0)this.children.splice(old,1);const i=this.children.indexOf(before);if(i<0)this.children.push(n);else this.children.splice(i,0,n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0]||null;}get lastChild(){return this.children[this.children.length-1]||null;}get scrollHeight(){return this.children.length*20;}
 set textContent(v){this._text=String(v);this.children=[];}get textContent(){return this._text;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}addEventListener(){}all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}text(){return [this.textContent,...this.children.map(n=>n instanceof N?n.text():String(n))].join(' ');}
}
let now=100000,tick,intervals=0,rpcs=0;
const c={locale:'en',bi:a=>a,E:(...a)=>new N(...a),Date,statusNow:()=>now,setTimeout:()=>0,setInterval:f=>{tick=f;intervals++;return 1;},clearInterval:()=>{},document:{body:{contains:()=>true}},rpc:{declare:()=>{rpcs++;throw Error('unexpected network action');}},safeCode:v=>typeof v==='string'&&/^[A-Z][A-Z0-9-]{1,95}$/.test(v),serverTitle:p=>p.name||p.id,endpointText:()=>'',rolePairIds:()=>['wireguard:peer_1','openvpn:1_1'],autoLightModel:()=>({key:'reserve',title:'Reserve confirmed'}),autoWorking:()=>true,channelDisplayUse:p=>({kind:p.id==='openvpn:1_1'?'green':'yellow',label:p.id==='openvpn:1_1'?'Working':'Waiting'})};
vm.createContext(c);for(const file of ['ui_logic','journal_panel','live_terminal'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);c.statusNow=()=>now;
const status={time:now,profiles:[{id:'wireguard:peer_1',name:'Primary'},{id:'openvpn:1_1',name:'Reserve'}],native_history:{events:[{sequence:1,time:now-10,state:'COMMITTED',target:'openvpn:1_1'}]},accounting:{reliability:{events:[{sequence:1,time:now-20,profile:'wireguard:peer_1',kind:'failure',code:'DNS-001'}]}}};
const rows=c.journalRows(status,null,now);assert.equal(rows.length,2);assert.equal(c.filteredJournalRows(rows,status,'dns-001','time',true).length,1);assert.equal(c.filteredJournalRows(rows,status,'primary','time',true).length,1);
assert(c.filteredJournalRows(rows,status,'','time',false)[0].time<rows[0].time,'date sorting covers all rows');
const root=c.renderLiveTerminal(status,{});assert.equal(intervals,1);assert(root.all().some(n=>n.attrs['data-terminal-pinned']==='1'));assert.equal(c.LIVE_TERMINAL.body.children.length,2,'no inactive profile inventory is dumped into the journal');
const savedDisplay=c.channelDisplayUse;
for(const language of ['en','ru']){
 c.bi=(en,ru)=>language==='ru'?ru:en;
 for(const working of ['wireguard:peer_1','openvpn:1_1']){
  c.channelDisplayUse=p=>({kind:p.id===working?'green':'red',label:p.id===working?'Working':'Failed'});
  c.terminalPinned(now);
  const pinned=c.LIVE_TERMINAL.pinned.children;
  assert(pinned[0].text().includes('HomenS.AI monitor'));assert(pinned[1].text().includes('Auto VPN'));
  assert(pinned[2].children[0].attrs.class.includes('green'));assert(pinned[3].children[0].attrs.class.includes('red'));
  const title=working==='openvpn:1_1'?(language==='ru'?'Резервный канал':'Reserve channel'):(language==='ru'?'Основной канал':'Primary channel');
  assert.equal(pinned[2].children[1].children[0],title,'role label follows its channel after reordering');
 }
 c.channelDisplayUse=()=>({kind:'grey',label:'No fresh data'});c.terminalPinned(now);
 assert.equal(c.LIVE_TERMINAL.pinned.children[2].children[1].children[0],language==='ru'?'Основной канал':'Primary channel','equal states retain stable role order');
}
c.channelDisplayUse=savedDisplay;c.bi=en=>en;c.terminalPinned(now);
assert.equal(status.profiles[0].id,'wireguard:peer_1','display sorting never reorders profile inventory');
assert.equal(c.LIVE_TERMINAL.entries[0].state,'COMMITTED','latest real observation starts at the top');
for(let i=0;i<30;i++){now++;tick();}
assert.equal(c.LIVE_TERMINAL.body.scrollTop,0);assert.equal(c.LIVE_TERMINAL.entries[0].time,status.time-10,'clock does not manufacture fresh router events');
assert.equal(c.LIVE_TERMINAL.entries.filter(e=>e.heartbeat).length,0);assert.equal(c.LIVE_TERMINAL.body.children.length,2,'thirty seconds create no duplicate timer rows');assert(c.LIVE_TERMINAL.clock.textContent.includes(':'),'clock includes seconds');
c.terminalAppend({key:'before-anchor1',time:now-1,state:'STARTING'});c.terminalAppend({key:'before-anchor2',time:now,state:'OBSERVING'});const body=c.LIVE_TERMINAL.body;body.clientHeight=20;body.scrollTop=40;body.attrs.scroll();assert.equal(c.LIVE_TERMINAL.following,false);const visible=body.children[2];now++;c.terminalAppend({key:'live-new',time:now,state:'STOPPED'});tick();assert.strictEqual(body.children[Math.floor(body.scrollTop/20)],visible,'incoming rows preserve the visible older event');
assert.strictEqual(c.renderLiveTerminal(status,{}),root,'polling reuses the terminal DOM and scrollback');assert.equal(intervals,1,'only one second timer exists');assert.equal(c.LIVE_TERMINAL.entries.filter(e=>!e.heartbeat).length,5,'repeated status does not duplicate events');
const held=body.children[Math.floor(body.scrollTop/20)],heldTop=c.LIVE_TERMINAL.scrollTop;
body.isConnected=false;body.scrollTop=0;
c.terminalAppend({key:'detached-poll',time:now,state:'OBSERVING'});
assert.equal(c.LIVE_TERMINAL.scrollTop,heldTop,'detached layout cannot overwrite the remembered reading position');
body.isConnected=true;c.terminalRestoreView();assert.strictEqual(body.children[Math.floor(body.scrollTop/20)],held,'poll detach/reattach retains the same visible record');
c.LIVE_TERMINAL.followButton.attrs.click();assert.equal(body.scrollTop,0);assert(c.LIVE_TERMINAL.following);
c.terminalAppend({key:'late-history',time:now-15,state:'RECOVERY'});assert.equal(c.LIVE_TERMINAL.entries[0].time,now,'a delayed history page never hides newer records');
for(let i=1;i<c.LIVE_TERMINAL.entries.length;i++)assert(c.LIVE_TERMINAL.entries[i-1].time>=c.LIVE_TERMINAL.entries[i].time);
now+=100;tick();assert(c.LIVE_TERMINAL.pinned.text().includes('No fresh verified data'),'old evidence degrades without fabricating another probe');
c.LIVE_TERMINAL.entries=Array.from({length:2000},(_,i)=>({key:'test:'+(2098-i),time:now+2098-i,state:i%2?'OBSERVING':'COMMITTED',level:'info'}));c.terminalAppend({key:'test:2099',time:now+2099,state:'OBSERVING',level:'info'});
assert.equal(c.LIVE_TERMINAL.entries.length,2000);assert.equal(c.LIVE_TERMINAL.body.children.length,2000);assert.equal(c.LIVE_TERMINAL.entries[0].key,'test:2099');assert.equal(c.LIVE_TERMINAL.entries[1999].key,'test:100','oldest rows are evicted from the tail');assert.equal(rpcs,0,'screen clock/log updates dispatch no control or network RPC');
console.log('PASS: shared event sorting, one-second pinned clock without timer rows, bounded observations, reading anchor and no extra probes');

const event=(key,time,state,extra={})=>Object.assign({key,time,state,kind:'OBSERVATION',origin:'monitor',profile:'wireguard:peer_1',level:'ok'},extra);
c.LIVE_TERMINAL.entries=[];c.LIVE_TERMINAL.following=true;
c.terminalAppend(event('repeat1',now+3000,'OBSERVING'));
const repeatedNode=body.children[0];c.terminalAppend(event('repeat2',now+3010,'OBSERVING'));
assert.equal(body.children.length,1);assert.strictEqual(body.children[0],repeatedNode,'extending a run reuses its node');
assert.equal(body.children[0].attrs['data-repeat-count'],'2');assert(body.children[0].text().includes('repeated 2 times'));assert(body.children[0].text().includes(' — '),'range shows first and last observed timestamps');
assert.equal(c.terminalGroups(c.LIVE_TERMINAL.entries)[0].firstTime,now+3000);
c.terminalAppend(event('other-state',now+3020,'RECOVERY'));
c.terminalAppend(event('repeat3',now+3030,'OBSERVING'));
assert.equal(body.children.length,3,'A → B → A is three runs, not global unique-state filtering');
assert.equal(body.children[2].attrs['data-repeat-count'],'2');
c.terminalAppend(event('late-between',now+3005,'FAILURE',{code:'DNS-001',level:'error'}));
assert.equal(body.children.length,5,'late intervening history splits a previously grouped run accurately');
assert.equal(c.LIVE_TERMINAL.entries[0].key,'repeat3');
for(const extra of [{profile:'openvpn:1_1'},{code:'DNS-002'},{source:'wireguard:peer_2'},{target:'openvpn:1_2'},{origin:'controller'},{kind:'RECOVERY'}]){
 const runs=c.terminalGroups([event('x',20,'OBSERVING'),event('y',10,'OBSERVING',extra)]);assert.equal(runs.length,2,'different event identity is never merged: '+JSON.stringify(extra));
}
const beforeTimer=body.children.length;now++;tick();assert.equal(body.children.length,beforeTimer);
c.terminalAppend({key:'legacy-heartbeat',time:now,heartbeat:true});assert.equal(body.children.length,beforeTimer);
assert.equal(rpcs,0);
console.log('PASS: repeated-state range/count, stable grouped node, A-B-A transitions, late-history splitting and separate VPN/code/source identities');

// A large actual status frame groups in one render; re-polling it never inflates repeats.
c.LIVE_TERMINAL.entries=[];c.LIVE_TERMINAL.seen=new Set();
const large=Object.assign({},status,{time:now,native_history:{events:[]},accounting:{reliability:{events:[]}},events:Array.from({length:1000},(_,i)=>({sequence:i+1,time:now-i,state:'OBSERVING',profile:'wireguard:peer_1'}))});
c.renderLiveTerminal(large,{});assert.equal(body.children.length,1);assert.equal(body.children[0].attrs['data-repeat-count'],'1000');assert.equal(c.LIVE_TERMINAL.entries.length,1000);
const heldRun=body.children[0];c.renderLiveTerminal(large,{});assert.strictEqual(body.children[0],heldRun);assert.equal(body.children[0].attrs['data-repeat-count'],'1000');
const rowsWithTargets=c.journalRows(Object.assign({},large,{events:[{sequence:2001,time:now,state:'COMMITTED',source:'wireguard:peer_1',target:'openvpn:1_1'},{sequence:2002,time:now-1,state:'COMMITTED',source:'wireguard:peer_1',target:'openvpn:1_2'}]}),null,now);
assert.equal(c.terminalGroups(rowsWithTargets).length,2,'different route targets retained by actual journal adapter');
console.log('PASS: thousand-observation grouped frame, polling idempotence and route-target provenance');

const provenance=Object.assign({},status,{time:now,auto_control:{requested:'on',requested_at:now-60,request_action:'start',request_source:'manual',activation_source:'manual'},native_history:{events:[
 {sequence:1,time:now-50,state:'APPLYING',source:'wireguard:peer_1',target:'openvpn:1_1',transition_source:'automatic',control_action:'start',control_time:now-60,control_source:'manual'},
 {sequence:2,time:now-40,state:'COMMITTED',manual:true,transition_source:'manual',target:'openvpn:1_1'},
 {sequence:3,time:now-30,state:'ARMED',trial:true},
 {sequence:4,time:now-20,state:'COMMITTED'}]},accounting:{reliability:{events:[]}}});
const evidence=c.journalRows(provenance,null,now);
assert.equal(evidence.filter(e=>e.origin==='control').length,1,'current/persisted activation context deduplicates by actual request timestamp');
assert(c.journalMessage(evidence.find(e=>e.origin==='control'),provenance).includes('activation requested'));
assert(c.journalMessage(evidence.find(e=>e.state==='APPLYING'),provenance).includes('Auto, automatically'));
assert(c.journalMessage(evidence.find(e=>e.action_source==='manual'&&e.state==='COMMITTED'),provenance).includes('you, manually'));
assert(c.journalMessage(evidence.find(e=>e.trial===true||e.action_source==='test'),provenance).includes('programmatic test'));
assert(c.journalMessage(evidence.find(e=>e.state==='COMMITTED'&&!e.action_source),provenance).includes('source not recorded'));
assert.equal(c.terminalGroups([event('m',20,'COMMITTED',{action_source:'manual'}),event('a',10,'COMMITTED',{action_source:'automatic'})]).length,2);
c.renderLiveTerminal(provenance,{});assert(c.LIVE_TERMINAL.pinned.text().includes('Activation: you, manually'));
assert(c.filteredJournalRows(evidence,provenance,'programmatic test','time',true).length>0);
console.log('PASS: request versus confirmed state, persisted/current control deduplication, manual/automatic/test/unknown provenance and grouped-source boundaries');

assert(c.journalMessage({state:'APPLYING',action_source:'manual'},status).includes('primary → reserve'));
assert(c.journalMessage({state:'RESTORING',action_source:'test'},status).includes('reserve → primary'));
const oldManual=c.journalRows(Object.assign({},status,{native_history:{events:[{sequence:88,time:now,state:'COMMITTED',manual:true}]},accounting:{reliability:{events:[]}}}),null,now);
assert.equal(oldManual[0].action_source,'unknown','legacy manual API usage is not proof of a human clicking');
console.log('PASS: explicit transition direction and no human attribution guessed for legacy API calls');

const programStop=c.journalRows(Object.assign({},status,{native_history:{events:[{sequence:90,time:now,state:'STOPPED',control_action:'stop',control_time:now-1,control_source:'programmatic'}]},accounting:{reliability:{events:[]}}}),null,now);
assert(c.journalMessage(programStop.find(e=>e.state==='STOPPED'),status).includes('program command'));
assert(c.journalMessage(programStop.find(e=>e.state==='AUTO-STOP-REQUESTED'),status).includes('deactivation requested'));
console.log('PASS: programmatic deactivation request and confirmed stopped state carry separate truthful labels');

const delaySample={profile:'openvpn:1_1',metric:'https-rtt-ms',time:now-3601,rtt_ms:17.4,interface:'ovpnclient1',generation:'b'.repeat(32)};
const recorded={sequence:150,time:now-3600,state:'COMMITTED',source:'wireguard:peer_1',target:'openvpn:1_1',transition_source:'automatic',latency:delaySample};
const latest=Object.assign({},status,{time:now,native_history:{events:[recorded]},accounting:{reliability:{events:[]}},profiles:[{id:'openvpn:1_1',time:now,rtt_ms:999}]});
let delayRows=c.journalRows(latest,null,now),delayText=c.journalMessage(delayRows[0],latest);
assert(delayText.includes('17.4 ms HTTPS'));assert(!delayText.includes('999'),'today RTT must never replace the event snapshot');
const noSnapshot=Object.assign({},recorded);delete noSnapshot.latency;
const unknown=c.journalRows(Object.assign({},latest,{native_history:{events:[noSnapshot]}}),null,now)[0];
assert(c.journalMessage(unknown,latest).includes('no saved measurement'));
for(const changed of [{profile:'wireguard:peer_1'},{time:now},{rtt_ms:NaN},{generation:'bad'},{interface:'wgclient1'}]){
 assert.equal(c.journalLatencySample(Object.assign({},delaySample,changed),'openvpn:1_1',now-3600),null,'invalid or unrelated historical RTT');
}
const primarySample={profile:'wireguard:peer_1',metric:'https-rtt-ms',time:now-1,rtt_ms:12.3,interface:'wgclient1',generation:'a'.repeat(32)};
const returned=c.journalRows(Object.assign({},latest,{native_history:{events:[{sequence:151,time:now,state:'STOPPED',source:'wireguard:peer_1',target:'openvpn:1_1',codes:['OPERATOR-RETURN'],latency:primarySample}]}}),null,now)[0];
assert(c.journalMessage(returned,latest).includes('12.3 ms HTTPS'),'legacy return uses primary measurement');
const currentProfile=website({id:'wireguard:peer_1',name:'Primary',protocol:'wireguard',interface:'wgclient1',vendor_tunnel_id:'wireguard:wgclient1',vendor_generation:'a'.repeat(32),vendor_state:'SETTLED',time:now,rtt_ms:987.6,dns_ok:true,https_success:2,code:null},12.3);
assert.equal(c.journalCurrentLatency(currentProfile,{time:now},now).rtt_ms,12.3);
assert.equal(c.journalCurrentLatency(currentProfile,{time:now,rpc_error:'RPC-UNAVAILABLE'},now),null);
assert.equal(c.journalCurrentLatency(Object.assign({},currentProfile,{website_response:{...currentProfile.website_response,time:now-100}}),{time:now},now),null);
c.renderLiveTerminal(Object.assign({},status,{time:now,profiles:[currentProfile]}),{});
assert(c.LIVE_TERMINAL.pinned.text().includes('12.3 ms')&&!c.LIVE_TERMINAL.pinned.text().includes('987.6'));
assert.equal(rpcs,0);
console.log('PASS: immutable event-time delay, no backfill from live RTT, target/return direction validation and fresh pinned delay without additional probes');
const recoveryStatus={time:now,profiles:[{id:'wireguard:peer_1',name:'Germany · WireGuard'}],accounting:{reliability:{events:[{sequence:100,time:now,kind:'RECOVERY',profile:'wireguard:peer_1',role:'target'}]}}};
for(const language of ['en','ru']){
 c.bi=(en,ru)=>language==='ru'?ru:en;
 const entry=c.journalRows(recoveryStatus,null,now)[0];
 const message=c.journalMessage(entry,recoveryStatus);
 assert(message.startsWith(language==='ru'?'Соединение восстановлено на резервном канале':'Connection restored on the reserve channel'));
 assert(message.endsWith('Germany · WireGuard'));
 recoveryStatus.native_failover={source:'wireguard:peer_1',target:'openvpn:1_1'};
 assert.equal(c.journalMessage(entry,recoveryStatus),message,'today\'s configured role cannot relabel saved recovery');
 assert.equal(c.filteredJournalRows([entry],recoveryStatus,language==='ru'?'резервном':'reserve','time',true).length,1);
 const primary=Object.assign({},entry,{role:'source'});
 assert(c.journalMessage(primary,recoveryStatus).startsWith(language==='ru'?'Соединение восстановлено на основном канале':'Connection restored on the primary channel'));
 const legacy=Object.assign({},entry,{role:null});
 assert(c.journalMessage(legacy,recoveryStatus).includes(language==='ru'?'канал не сохранён':'channel was not saved'),'missing historical evidence must not be fabricated');
 assert.equal(c.terminalGroups([Object.assign({},entry,{time:20}),Object.assign({},primary,{time:10})]).length,2,'different saved roles cannot be merged');
}
c.bi=en=>en;
console.log('PASS: saved recovery roles precede server name in EN/RU, search, pair changes, legacy evidence and grouping');
for(const language of ['en','ru']){
 c.bi=(en,ru)=>language==='ru'?ru:en;
 for(const role of ['source','target']){
  const raw={time:now,kind:'FAILURE',profile:'wireguard:peer_1',role,code:'VPN-003',sequence:101};
  const s={profiles:[{id:raw.profile,name:'Germany · WireGuard'}],accounting:{reliability:{events:[raw]}}};
  const entry=c.journalRows(s,null,now)[0],message=c.journalMessage(entry,s);
  const expected=role==='source'?(language==='ru'?'Основной канал':'Primary channel'):(language==='ru'?'Резервный канал':'Reserve channel');
  assert(message.startsWith(expected+' — '+(language==='ru'?'Ошибка проверки соединения':'Connection check failed')));assert(message.includes('Germany · WireGuard'));assert(message.endsWith('VPN-003'));
 }
}
c.bi=en=>en;
console.log('PASS: failure messages start with the saved primary/reserve role before state/server/code in EN/RU');
for(const language of ['en','ru']){
 c.bi=(en,ru)=>language==='ru'?ru:en;
 const pair={source:'wireguard:peer_1',target:'openvpn:1_1'};
 for(const [state,extra,from,to,phase] of [
  ['APPLYING',{},'source','target','pending'],['WAIT-CLIENT',{},'source','target','pending'],
  ['COMMITTED',{},'source','target','confirmed'],['RESTORING',{},'target','source','pending'],
  ['ROLLED-BACK',{original_restored:true},'target','source','confirmed']
 ]){
  const entry=Object.assign({state},pair,extra),model=c.journalChannelModel(entry);
  assert.equal(model.from,from);assert.equal(model.to,to);assert.equal(model.phase,phase);
  const badge=c.renderJournalChannelBadge(entry);assert.equal(badge.attrs.role,'img');assert(badge.attrs['aria-label'].length>20);
  assert.equal(badge.children[0].children[0],'M');assert.equal(badge.children[2].children[0],'R');
  assert.equal(badge.children[1].children[0],from==='source'?'→':'←');
  if(phase==='confirmed'){
   assert(badge.children[to==='source'?0:2].attrs.class.includes('working'));
   assert(badge.children[from==='source'?0:2].attrs.class.includes('failed'));
   assert(!badge.attrs.class.includes('moving'));
  }else assert(badge.attrs.class.includes('moving'));
 }
 for(const role of ['source','target']){
  const entry={time:now,state:'FAILURE',kind:'FAILURE',role,profile:'wireguard:peer_1'},badge=c.renderJournalChannelBadge(entry);
  assert.equal(badge.children[1].children[0],'·','an isolated failure does not claim a switch');
  assert(badge.children[role==='source'?0:2].attrs.class.includes('failed'));
  assert(badge.children[role==='source'?2:0].attrs.class.includes('neutral'),'other channel health is not invented');
  const line=c.terminalLine(entry,status);assert(line.children[1].all().some(n=>n.attrs.class&&n.attrs.class.includes('hv-channel-badge')),'live line actually contains diagram');
 }
 assert.equal(c.renderJournalChannelBadge({state:'ROLLED-BACK',...pair}),null,'return without confirmation is not green');
 assert.equal(c.renderJournalChannelBadge({state:'FAILURE',role:null}),null,'legacy unknown role cannot invent M/R');
}
c.bi=en=>en;
const channelCSS=fs.readFileSync('router/design_layer.css','utf8');assert(channelCSS.includes('prefers-reduced-motion:reduce'));assert(channelCSS.includes('hv-channel-backward'));
console.log('PASS: M/R diagrams in live/history, both directions, pending animation, confirmed colours, failure-only semantics, EN/RU accessibility and reduced motion');
const diagramHistory=c.renderEventHistory({time:now,accounting:{reliability:{events:[{time:now,sequence:400,kind:'FAILURE',profile:'wireguard:peer_1',role:'source',code:'VPN-003'}]}}});
assert(diagramHistory.all().some(n=>n.attrs['data-channel-phase']==='failed'),'saved events actually render the shared diagram');
console.log('PASS: saved-history table renders M/R badge alongside failure state');
// Operator-selected capacity is enforced in raw observations and rendered runs.
c.LIVE_TERMINAL.inventory={settings:{live_log_limit:100}};c.LIVE_TERMINAL.entries=[];c.LIVE_TERMINAL.following=true;
for(let i=0;i<150;i++)c.terminalAppend({key:'capacity:'+i,time:now+i,state:i%2?'OBSERVING':'COMMITTED'});
assert.equal(c.LIVE_TERMINAL.entries.length,100);assert.equal(c.LIVE_TERMINAL.body.children.length,100);
assert.equal(c.LIVE_TERMINAL.entries[0].key,'capacity:149');
c.LIVE_TERMINAL.inventory={settings:{live_log_limit:1}};c.terminalAppend({key:'capacity:new',time:now+151,state:'OBSERVING'});assert.equal(c.LIVE_TERMINAL.entries.length,1);
const bounded={accounting:{reliability:{detail_days:1,events:[{time:now-2*86400,sequence:1,kind:'FAILURE'},{time:now-1,sequence:2,kind:'RECOVERY'}]}}};
assert.equal(c.journalRows(bounded,null,now).length,1);assert.equal(c.journalHistoryDays(bounded),1);
console.log('PASS: live limits 100/1 trim real entries/DOM, and selected day retention filters journal rows');
// Saved history starts with the latest twenty, and its triangle reveals the rest.
for(const language of ['en','ru']){
 c.locale=language;c.bi=(en,ru)=>language==='ru'?ru:en;
 const events=Array.from({length:35},(_,i)=>({sequence:i+1,time:now-35+i,kind:i%2?'RECOVERY':'FAILURE',profile:'wireguard:peer_1',role:'source'}));
 c.EVENT_VIEW={query:'',sort:'time',desc:true,expanded:false,page:0,stored:null,busy:false,error:null,request:0};
 const host=c.renderEventHistory({time:now,accounting:{reliability:{events}}});
 const rendered=()=>host.all().filter(n=>n.attrs['data-event-key']);
 assert.equal(host.all().filter(n=>n.tag==='button').length,2,'only sort direction and history disclosure; no read-saved button');
 assert.equal(rendered().length,20);assert.equal(rendered()[0].attrs['data-event-key'],'failures:35');assert.equal(rendered()[19].attrs['data-event-key'],'failures:16');
 const triangle=host.all().find(n=>n.tag==='button'&&n.attrs['aria-expanded']==='false');assert(triangle.text().startsWith('▸'));
 c.EVENT_VIEW.stored={controller:{events:[]},failures:{events}};
 triangle.attrs.click();assert.equal(rendered().length,35);assert.equal(triangle.attrs['aria-expanded'],'true');
 assert(triangle.text().includes(language==='ru'?'20 строк':'20 rows'));
 triangle.attrs.click();assert.equal(rendered().length,20);assert.equal(triangle.attrs['aria-expanded'],'false');
}
c.locale='en';c.bi=en=>en;
console.log('PASS: actual saved-history table shows latest 20, triangle expands 35 and collapses to 20, EN/RU');
