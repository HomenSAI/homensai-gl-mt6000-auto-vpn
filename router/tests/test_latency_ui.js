const fs=require('fs'),vm=require('vm'),assert=require('assert');
const {website,history}=require('./website_fixture');
function setResponse(p,value){p.website_response.avg_ms=value;p.website_response.results.forEach(r=>r.elapsed_ms=value);}
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).filter(v=>v!=null);this.listeners={};}
 appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0]||null;}
 setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}addEventListener(k,f){this.listeners[k]=f;}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
}
const now=100000,c={locale:'en',bi:(a)=>a,E:(...a)=>new N(...a),document:{createElementNS:(_,tag)=>new N(tag)},Date,serverTitle:p=>p.name||p.id,protocolLabel:p=>p.protocol,statusNow:()=>now,profileHealth:(p,t)=>({state:p.time<=t+5&&t-p.time<=90&&p.code===null?'healthy':'unknown'})};
vm.createContext(c);for(const file of ['ui_logic','channel_guidance','latency_panel'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
const inventory={settings:{plan_source:'wireguard:peer_1',plan_target:'openvpn:1_1'}};
c.statusNow=()=>now;c.routerWall=()=>now;c.helpLink=(id,label)=>new N('a',{href:'#help/topic/'+id},label);
function status(){return {time:now,profiles:[website({id:'wireguard:peer_1',time:now,protocol:'wireguard',code:null,rtt_ms:777,dns_ok:true,https_success:2,vendor_state:'SETTLED'},20),website({id:'openvpn:1_1',time:now,protocol:'openvpn',code:null,rtt_ms:999,dns_ok:true,https_success:2,vendor_state:'SETTLED'},40)],website_response_history:history(['wireguard:peer_1','openvpn:1_1'],[[now-120,30,50,1,1,'source'],[now-60,40,null,1,0,'target']])};}
let s=status();assert(c.latencyRecommendation(s,inventory,now).text.includes('wireguard:peer_1'),'recommendation identifies the actual profile');assert.equal(c.latencyRecommendation(s,inventory,now).index,0);setResponse(s.profiles[0],80);assert.equal(c.latencyRecommendation(s,inventory,now).index,1);
for(const edit of [p=>p.website_response.time=now-100,p=>p.website_response.avg_ms=NaN,p=>p.vendor_state='CHANGING',p=>{p.website_response.state='partial';p.website_response.avg_ms=null;p.website_response.successes=2;}]){s=status();edit(s.profiles[0]);c.UI_LAST_DELAY={};delete s.website_response_history;const r=c.latencyRecommendation(s,inventory,now);assert.equal(r.index,1);assert(r.single&&/Only the reserve has a complete three-site measurement/.test(r.text));assert(!/only.*works/i.test(r.text),'missing site responses do not declare a VPN failed');}
for(const change of [{dns_ok:false},{https_success:0},{code:'DNS-001'},{time:now-100-(c.UI_DISPLAY_GRACE||0)}]){const v=status();Object.assign(v.profiles[0],change);const r=c.latencyRecommendation(v,inventory,now);assert.equal(r.index,1);assert(r.single&&/eligible/.test(r.text));assert.equal(c.latencyCurrent(v,inventory,now)[0].rtt_ms,20,'independent current value stays visible while failed/unknown health excludes recommendation');}
s=status();setResponse(s.profiles[0],40);assert.equal(c.latencyRecommendation(s,inventory,now).index,null,'ties do not force a recommendation');
s=status();s.website_response_history.pair.reverse();assert.equal(c.latencyHistoryRows(s,inventory,now).length,0,'another pair never supplies this graph');
const segments=c.latencySegments([[100,20,30,1,1,'source'],[160,null,40,0,1,'target'],[400,25,35,1,1,'target']],0,0,500,100);
assert.equal(segments.length,2,'failed/missing observations split the path');assert.equal(segments[0].color,'#16a765');assert.equal(segments[1].color,'#c49500');
let panel=c.renderLatencyPanel(status(),inventory),inputs=panel.all().filter(n=>n.tag==='input');assert.equal(inputs.length,2);
inputs[0].attrs.input({target:{value:'12'}});assert.equal(c.LATENCY_VIEW.hours,12);
inputs[1].attrs.input({target:{value:'30'}});assert.equal(c.LATENCY_VIEW.end,now-1800);
panel=c.renderLatencyPanel(status(),inventory);assert.equal(c.LATENCY_VIEW.end,now-1800,'polling keeps the inspected historical window');
assert(!panel.all().some(n=>n.attrs.click&&/native_start|pair_manual|setup_/.test(String(n.attrs.click))),'graph/recommendation has no control RPC');
console.log('PASS: fresh comparable latency recommendation, unknown/tie refusal, pair isolation, gap/color semantics and persistent1–24h view without routing writes');

// Weighted aggregates and real refusal gates, including a fresh-looking cached route after RPC loss.
const aggregate=[[now-120,20,50,1,2,'source'],[now-60,40,null,3,0,'target'],[now,null,10,0,1,'target']];
let summary=c.latencyStatistics(aggregate,now-3600,now);
assert.equal(summary[0].mean,35);assert.equal(summary[0].count,4);assert.equal(summary[0].min,20);assert.equal(summary[0].max,40);
assert(Math.abs(summary[1].mean-110/3)<1e-9);assert.equal(summary[1].count,3);
summary=c.latencyStatistics(aggregate,now-60,now);assert.equal(summary[0].mean,40);assert.equal(summary[1].mean,10);
summary=c.latencyStatistics([],now-60,now);assert.equal(summary[0].mean,null);assert.equal(summary[0].count,0);
s=status();s.time=now;s.channel_path={time:now,confirmed:true,active_profile_id:inventory.settings.plan_source};
c.vendorDisplaySelected=()=>null;
assert(JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('traffic follows the VPN priority list of the router')&&!JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('Traffic currently uses'),'never bypass route helper refusal');
delete c.vendorDisplaySelected;
assert(JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('Traffic currently uses the primary channel.'));
s.rpc_error='RPC-UNAVAILABLE';assert.equal(c.latencyRecommendation(s,inventory,now).index,null);
assert(JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('STATUS-REQUEST-FAILED'),'RPC error cannot reuse cached selection');
assert(!JSON.stringify(c.renderLatencyStatistics([],now-60,now)).includes('NaN'));
console.log('PASS: weighted window statistics, empty history, route-helper refusal and cached RPC-error fences');

const originalBi=c.bi,originalProtocol=c.protocolLabel;
c.bi=(_en,ru)=>ru;c.countryName=()=> 'Германия';c.protocolLabel=()=> 'WireGuard';
s=status();s.time=now;s.profiles[0].router_name='de678.nordvpn.com';s.profiles[0].name='Германия · WireGuard';
let recommendation=c.renderLatencyRecommendation(s,inventory,'manual');
assert.equal(recommendation.tag,'details');assert(!Object.hasOwn(recommendation.attrs,'open'));
assert.equal(recommendation.children[0].tag,'summary');
function textOf(n){return n instanceof N?n.children.map(textOf).join(''):String(n);}
let text=textOf(recommendation);assert.equal((text.match(/WireGuard/g)||[]).length,1);
assert(text.includes('de678.nordvpn.com'));assert(!text.includes('Ручное переключение')&&!text.includes('не ICMP'));
const lines=recommendation.all().filter(n=>n.attrs.class==='hv-recommendation-line');
assert.deepEqual(lines.slice(0,2).map(textOf),['Меньший измеренный ответ: Основной канал','Его задержка: 20.0 мс']);
assert(lines.some(n=>textOf(n)==='Страна: Германия'));assert(lines.some(n=>textOf(n)==='Протокол: WireGuard'));
recommendation.open=true;recommendation.listeners.toggle();
assert(c.renderLatencyRecommendation(s,inventory,'manual').attrs.open,'poll preserves expansion');
assert(!c.renderLatencyRecommendation(s,inventory,'channels').attrs.open,'separate view has independent disclosure');
s.profiles[0].website_response.time=now-100;c.UI_LAST_DELAY={};delete s.website_response_history;text=textOf(c.renderLatencyRecommendation(s,inventory,'manual'));assert(!text.includes('de678.nordvpn.com'),'a channel never measured cannot be recommended');
c.bi=originalBi;c.protocolLabel=originalProtocol;delete c.countryName;
console.log('PASS: collapsed structured RU recommendation, independent remembered disclosures, exact server name, single protocol and no manual-navigation footer');
// Weekly browsing keeps the inspected offset and restores live mode, without RPC.
c.bi=(_en,ru)=>ru;c.statusNow=()=>900000;
const weekStatus=status();weekStatus.profiles.forEach(p=>p.time=900000);
weekStatus.website_response_history=history(inventory.settings.plan_source?[inventory.settings.plan_source,inventory.settings.plan_target]:[],[[900000-6*86400,25,55,1,1,'source'],[900000,30,60,1,1,'target']]);
c.LATENCY_VIEW.hours=1;c.LATENCY_VIEW.end=null;
let weekPanel=c.renderLatencyPanel(weekStatus,inventory),weekInputs=weekPanel.all().filter(n=>n.tag==='input');
assert.equal(weekInputs[0].attrs.max,'168');assert.equal(weekInputs[1].max,String(167*60));
assert(textOf(weekPanel).includes('Просмотр последних 7 суток'));
weekInputs[1].attrs.input({target:{value:String(6*24*60)}});assert.equal(c.LATENCY_VIEW.end,900000-6*86400);
weekPanel=c.renderLatencyPanel(weekStatus,inventory);assert.equal(c.LATENCY_VIEW.end,900000-6*86400);
weekInputs=weekPanel.all().filter(n=>n.tag==='input');weekInputs[0].attrs.input({target:{value:'168'}});
assert.equal(c.LATENCY_VIEW.hours,168);assert.equal(c.LATENCY_VIEW.end,null);assert.equal(weekInputs[1].max,'0');
assert.equal(c.latencyHistoryRows(weekStatus,inventory,900000).length,2,'six-day sample survives filtering');
const bulk=Array.from({length:10081},(_,i)=>[900000-7*86400+i*60,20+i%30,40+i%40,1,1,'source']);
const weeklyGraph=c.renderLatencyGraph(bulk,900000-7*86400,900000);
assert(weeklyGraph.all().filter(n=>n.tag==='circle').length<=1440,'weekly marker budget stays bounded');
assert.equal(weeklyGraph.all().filter(n=>n.tag==='polyline').length,2,'minute lines remain continuous without filling gaps');
assert.equal(c.latencyStatistics(bulk,900000-7*86400,900000)[0].count,10081,'stats use every retained minute');
const packed=history([inventory.settings.plan_source,inventory.settings.plan_target],bulk).rows;
const weeklyStatus={...weekStatus,website_response_history:{...weekStatus.website_response_history,rows:packed}};
assert.equal(c.latencyHistoryRows(weeklyStatus,inventory,900000).length,10081);
weeklyStatus.website_response_history.rows=[...bulk,bulk.at(-1)];assert.equal(c.latencyHistoryRows(weeklyStatus,inventory,900000).length,0,'oversize payload refused');
weekPanel.all().find(n=>n.tag==='button'&&textOf(n)==='Сейчас').attrs.click();assert.equal(c.LATENCY_VIEW.end,null);
c.bi=originalBi;
console.log('PASS: RU seven-day label,1–168h window, six-day pan and polling preservation/live reset,10081-minute filtering/statistics and bounded markers, no routing RPC');

const encodedWeek={...weekStatus,website_response_history:{...weekStatus.website_response_history,rows:packed.slice(-1441),rows_count:10081,rows_json:JSON.stringify(packed)}};
assert.equal(c.latencyHistoryRows(encodedWeek,inventory,900000).length,10081,'complete encoded week wins over legacy daily tail');
encodedWeek.website_response_history.rows_json='broken';assert.equal(c.latencyHistoryRows(encodedWeek,inventory,900000).length,0);
encodedWeek.website_response_history.rows_json=' '.repeat(850001);assert.equal(c.latencyHistoryRows(encodedWeek,inventory,900000).length,0);
encodedWeek.website_response_history.rows_json=JSON.stringify(packed);encodedWeek.website_response_history.rows_count=2;assert.equal(c.latencyHistoryRows(encodedWeek,inventory,900000).length,0,'count mismatch is not a successful truncated week');
console.log('PASS: bounded weekly transport decoding, legacy daily compatibility, malformed/oversize/count mismatch refusals');

const compact=c.renderLatencyPanel(weekStatus,inventory),notes=compact.all().find(n=>n.tag==='details'&&n.attrs['data-auto-disclosure']==='latency-statistics');
assert(notes&&!notes.attrs.open);assert(notes.all().some(n=>n.tag==='a'&&n.attrs.href==='#help/topic/website-response'));assert(fs.readFileSync('router/help_panel.inc.js','utf8').includes('Statistics follow the selected graph window.'));
assert(!textOf(compact).includes('Зелёный: выбранный маршрут.'));assert(!textOf(compact).includes('Grey: route unconfirmed.'));
console.log('PASS: compact statistic explanation links to retained lazy method/history paragraphs and no confusing permanent route-color prose');
c.statusNow=()=>now;
// Regression: a failing primary must render (the page once threw "ids is not defined" and stopped refreshing).
{const s=status();Object.assign(s.profiles[0],{code:'VPN-003',dns_ok:false,https_success:0,rtt_ms:null});
 const panel=c.renderLatencyPanel(s,inventory);assert(panel,'panel renders with a failing primary');
 const again=c.renderLatencyPanel(s,inventory);assert(textOf(again).includes('20.0 ms'),'technical health failure does not replace an independently valid website mean');
 console.log('PASS: failing primary renders and shows its latest check');}
{
  // alpha79 owner rule: a channel without a current measurement keeps its last known delay, so the recommendation still compares.
  const fresh=status();c.UI_LAST_DELAY={};c.latencyRecommendation(fresh,inventory,now);
  const later=status();later.profiles[0].website_response.time=now-100;
  const r=c.latencyRecommendation(later,inventory,now);assert(r.index===0||r.index===1,'last known delay keeps the recommendation');assert(!r.single);
  console.log('PASS: last known delay keeps the recommendation');
}
