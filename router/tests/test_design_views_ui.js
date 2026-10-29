const fs=require('fs'),vm=require('vm'),assert=require('assert');
// Runs the generated page's helper code (everything before the view object) in a sandbox, then renders the three overviews.
class N{constructor(t,a,c){this.tag=t;this.attrs=a||{};this.children=[].concat(c===undefined?[]:c).flat().filter(x=>x!=null);}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join(' ');}
  addEventListener(k,f){(this.listeners||(this.listeners={}))[k]=f;}removeAttribute(k){delete this.attrs[k];}get style(){return this._s=this._s||{};}get classList(){return {add(){},remove(){},toggle(){}};}set textContent(v){this.children=[String(v)];}
  appendChild(c){this.children.push(c);return c;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]==null?null:this.attrs[k];}}
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base='router/files/www/luci-static/resources/view/homensai-vpn/';
const source=fs.readFileSync(base+page+'.js','utf8');
const unguardedPrefix=source.slice(0,source.lastIndexOf('return view.extend({'));
const prefix=unguardedPrefix.includes('function hvElementChildren(')?unguardedPrefix:unguardedPrefix.replace("'require ui';","'require ui';\n"+fs.readFileSync('router/element_guard.inc.js','utf8'));
function sandbox(lang){
  const ctx={window:{localStorage:{getItem(){return null},setItem(){}},HomenS:{},location:{search:lang?'?lang='+lang:'',href:'http://x/',hash:''}},
    document:{createElementNS:(ns,t)=>new N(t,{},[]),createElement:t=>new N(t),addEventListener(){}},localStorage:{getItem(){return null}},
    E:(t,a,c)=>new N(t,a,c),URLSearchParams,URL,Intl,console,L:{},rpc:{declare:()=>()=>Promise.resolve({})},ui:{},poll:{},view:{extend:o=>o}};
  ctx.location=ctx.window.location;vm.createContext(ctx);vm.runInContext(prefix,ctx);return ctx;
}
const now=Date.now()/1000;
function fixture(over){
  const profiles=[
    {id:'a',name:'de1459.nordvpn.com.udp',router_name:'de1459.nordvpn.com.udp',protocol:'openvpn',interface:'vpna',channel:'Main',time:now-5,dns_ok:true,https_success:2,rtt_ms:38,code:null},
    {id:'b',name:'Reserve',router_name:'nl-ams-001',protocol:'wireguard',interface:'vpnb',channel:'Main',time:now-5,dns_ok:true,https_success:2,rtt_ms:44,code:null},
    {id:'c',name:'fi-spare',router_name:'fi-spare',protocol:'openvpn',interface:null,channel:'Spare'}];
  const samples=[];for(let i=0;i<24;i++){samples.push({id:'a',time:now-(24-i)*30,code:null,dns_ok:true,https_success:2,rtt_ms:36+i%5});samples.push({id:'b',time:now-(24-i)*30,code:i===3?'DNS-001':null,dns_ok:i!==3,https_success:i===3?0:2,rtt_ms:i===3?null:44});}
  return Object.assign({version:'1.2.3',package:'1.2.3-1',time:now-3,profiles,samples,native_failover:{state:'OBSERVING',certified:true,source:'a',target:'b',time:now-2},
    native_history:{events:[{sequence:1,time:now-90,state:'COMMITTED',source:'a',target:'b',codes:[]},{sequence:2,time:now-60,state:'ROLLED-BACK',source:'b',target:'a',codes:['DNS-001']}]},
    accounting:{months:{}}},over||{});
}
const inventory={settings:{plan_source:'a',plan_target:'b'},profiles:[]};
function render(ctx,design,status,rows,extra){
  const control=new N('section',{'class':'control-card'},['CONTROL']);
  const node=ctx.renderDesignOverview(design,Object.assign({status,inventory,rows:rows||status.profiles||[],month:{rx:2e9,tx:1e9},controlCard:control},extra||{}));
  return {node,control};
}
const ctx=sandbox();
for(const d of ['a','b','c']){
  const {node,control}=render(ctx,d,fixture());
  assert(node.attrs.class.includes('hv-dv-'+d),d+' class');
  assert.equal(node.all().filter(n=>n===control).length,1,d+': the real Auto card is embedded exactly once');
  const text=node.text();
  if(d!=='b'){assert(/Germany/.test(text)&&/Netherlands/.test(text),d+': countries from the profile names');assert(node.all().some(n=>n.attrs&&n.attrs['data-profile']==='c'),d+': a profile that is not connected is still listed');}
  else{assert(!/Your VPNs/.test(text),'owner removed the complete duplicate VPN section');assert(!node.all().some(n=>n.attrs&&n.attrs['data-profile']),'Calm Overview has no duplicate channel cards');}
}
// A: strip, KPIs, servers with sparkline, recent events with codes.
let a=render(ctx,'a',fixture()).node,t=a.text();
assert(/Everything works\./.test(t));assert(/2 of 2/.test(t));assert(/Traffic this month/.test(t)&&/3\.000 GB/.test(t));
assert(a.all().some(n=>n.tag==='svg'&&/hv-dv-spark/.test(n.attrs.class)),'A: sparkline');
assert(/Reserve confirmed/.test(t)&&/Rolled back to the previous route/.test(t)&&/DNS-001/.test(t));
// Tone follows the real state: reserve in use -> warning, no data -> bad, nothing connected -> off.
assert(a.all().find(n=>(n.attrs.class||'').includes('hv-dv-strip')).attrs.class.includes('hv-dv-tone-ok'));
a=render(ctx,'a',fixture({native_failover:{state:'COMMITTED',source:'a',target:'b',time:now-1}})).node;assert(/Working on the reserve/.test(a.text()));assert(/hv-dv-tone-warn/.test(a.all().find(n=>(n.attrs.class||'').includes('hv-dv-strip')).attrs.class));
a=render(ctx,'a',fixture({rpc_error:'RPC-UNAVAILABLE'})).node;assert(/No data from the router/.test(a.text()));assert(/hv-dv-tone-bad/.test(a.all().find(n=>(n.attrs.class||'').includes('hv-dv-strip')).attrs.class));
const none=fixture({profiles:[],samples:[],native_history:{events:[]}});
a=render(ctx,'a',none,[]).node;assert(/No VPN is connected/.test(a.text()));assert(/No VPN profiles found/.test(a.text()));assert(/No switches or failures are recorded/.test(a.text()));
// B: plain words, tags, questions, links to the sections that are not in its menu.
let b=render(ctx,'b',fixture()).node;t=b.text();
for(const missing of [undefined,null,'invalid'])assert(render(ctx,missing,fixture()).node.attrs.class.includes('hv-dv-b'),'missing/invalid design renders Calm');
assert(!/Your VPN works|on the reserve/.test(t),'the state block was removed');assert(!/What happens if/.test(t),'the what-if block was removed');assert(!/Last thing that happened/.test(t),'the last event block was removed');
['#statistics','#help','#learn','#events'].forEach(h=>assert(b.all().some(n=>n.tag==='a'&&n.attrs.href===h),'B link '+h));
assert(!b.all().some(n=>/hv-dv-list|hv-dv-item|hv-vpn-more|hv-dv-statuscol/.test(n.attrs.class||'')),'entire duplicate Your VPNs block is absent, not just its title');
// C: status line with real identifiers, latency chart, log with codes, server table, keys.
const c=render(ctx,'c',fixture()).node;t=c.text();
const tc=t.replace(/\s+/g,' ');assert(/ctrl OBSERVING/.test(tc)&&/auto (OFF|ON)/.test(tc)&&/ui dashboard/.test(tc));assert(/Event log/.test(t)&&/DNS-001/.test(t));
const rowsC=c.all().filter(n=>n.tag==='tr'&&n.attrs['data-profile']);assert.equal(rowsC.length,3);
assert(/Working|Waiting/.test(rowsC[0].text()));
assert(/1.*9.*sections/.test(t.replace(/\s+/g,' '))&&/search/.test(t));
// Hostile names stay inert text; nothing builds markup from them.
const hostile=fixture();hostile.profiles[0].name='<img src=x onerror=alert(1)>';hostile.profiles[0].router_name='<b>de</b>';
for(const d of ['a','b','c']){const n=render(ctx,d,hostile).node;n.all().forEach(x=>{assert(!x.tag.includes('<'));});assert(!n.all().some(x=>x.tag==='img'),d+': no element from a name');}
// Router-supplied values that look like object keys or selector tricks stay harmless.
{const evil=fixture();evil.profiles[0].code='"]x[data-y="';evil.native_history.events.push({sequence:9,time:now-5,state:'constructor',codes:['__proto__','a"b'],source:'a',target:'b'});
 for(const d of ['a','b','c']){const n=render(ctx,d,evil).node;n.all().forEach(y=>{assert(typeof y.tag==='string');});}
 const hostileStatus=fixture({native_failover:{state:'__proto__',source:'a',target:'b',time:now-1},decision_explanation:{diagnosis:{code:'constructor'}}});
 assert.doesNotThrow(()=>{if(typeof ctx.renderDecisionExplanation==='function')ctx.renderDecisionExplanation(hostileStatus);ctx.renderCascadePath(Object.assign(fixture(),{profiles:[Object.assign({},fixture().profiles[0],{code:'a"]'})]}));});}
// Russian: same structure, translated text.
const ru=sandbox('ru');vm.runInContext("locale='ru'",ru);
const ra=render(ru,'a',fixture()).node.text();assert(/Всё работает\./.test(ra)&&/Последние события/.test(ra)&&/Германия/.test(ra));
assert(!/Что будет, если/.test(render(ru,'b',fixture()).node.text()));assert(/Журнал/.test(render(ru,'c',fixture()).node.text()));
// Legacy renderers remain callable for regression; the new view composes only the accepted design.
const releasedView=source.slice(source.lastIndexOf('return view.extend({'));
if(source.includes('hv-hybrid-release')){
 assert(releasedView.includes('renderDesignOverview('),'owner-selected legacy overview restored');
 assert(releasedView.includes('placeHybridControls(key)'),'actual controls reparented across Minimum and legacy overview');
}else{
 assert(!releasedView.includes('renderDesignOverview('),'no competing overview renderer in released view');
 assert(releasedView.includes('minimumComposePages(pages,panel,status,inventory,controlCard,minimumCommandHost,routerVpnUrl())'),'new composition retains actual source nodes');
 assert(releasedView.includes('renderMinimumSettings('),'persistent simplified settings replace layout picker');
}
assert(source.includes("installDesignKeys(appRoot,"));
// Keys of design C: digits open sections, ignored while typing and for other designs.
{const listeners=[];const doc={addEventListener:(n,f)=>listeners.push(f)};const root=new N('div',{'data-hv-design':'c'});root.isConnected=true;root.querySelector=()=>null;
  const k=sandbox();k.document=doc;vm.runInContext('1',k);const opened=[];k.installDesignKeys(root,['overview','channels','statistics'],key=>opened.push(key));
  const press=(key,target,extra)=>listeners.forEach(f=>f(Object.assign({key,target:target||{tagName:'BODY'},preventDefault(){}},extra||{})));
  press('2');press('9');press('3',{tagName:'INPUT'});press('1',null,{ctrlKey:true});assert.deepEqual(opened,['channels']);
  root.attrs['data-hv-design']='a';press('1');assert.deepEqual(opened,['channels']);}
// The stylesheet carries the three palettes, the new layouts and the attribute rules.
const css=fs.readFileSync(base+/ui[0-9]+\.css/.exec(source)[0],'utf8');
for(const part of ['.hv-dv-a','.hv-dv-b','.hv-dv-c','[data-hv-design="c"]{color-scheme:dark','[data-hv-dv] .hv-summary','prefers-color-scheme:dark'])assert(css.includes(part),part);
console.log('PASS: retained overview helpers handle real/hostile data and RU; release composes the accepted Minimum instead of alternate overviews');

// Render the actual control subtree, not a placeholder: daily graph/manual cards must survive every overview layout.
{
 const actual=sandbox('ru');vm.runInContext(fs.readFileSync('router/auto_panel.inc.js','utf8'),actual);actual.locale='ru';actual.document.documentElement={clientWidth:1200};actual.poll.add=()=>{};
 const st=fixture({native_failover:{state:'OBSERVING',time:now,source:'a',target:'b',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true},
   auto_control:{requested:'on',requested_at:now-60,pair_phase:'RUNNING',control_revision:'a'.repeat(32)},
   manual_switch_control:{mode:'continuous-pair',time:now,available:true,control_revision:'a'.repeat(32),primary:{allowed:false,blockers:['RETURN-NOT-APPLICABLE']},reserve:{allowed:true,blockers:[]}},
   channel_path:{time:now,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:now,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a',transitioning:false},
   accounting:{reliability:{route_history:{segments:[{start:now-100,end:now,kind:'source'}]}}}});
 const inv={settings:{enabled:true,interval:10,plan_source:'a',plan_target:'b',pair_auto_mode:'router-probed-ipv4'},profiles:st.profiles};
 const card=actual.renderAutoControl(st,inv,()=>Promise.resolve()),nodes=card.all();
 const automatic=card.children[0],header=automatic.children[0],controls=automatic.children[1];
 assert.equal(header.attrs.class,'hv-auto-header');assert.equal(header.children[0].tag,'h2');
 const monitor=controls.children.find(n=>n&&n.attrs&&(n.attrs.class||'').includes('hv-monitor-block'));assert(monitor,'monitor lamp sits right of the Auto controls');
 assert(monitor.all().some(n=>(n.attrs.class||'').includes('hv-monitor-lamp-green')),'fresh enabled monitor retains green lamp');
 assert.equal(controls.attrs.class,'hv-auto-controls');assert.equal(controls.children[0].attrs.class,'hv-auto-switch');
 const stepRow=automatic.children.find(n=>n&&n.attrs&&n.attrs.class==='hv-auto-step-row');assert(stepRow&&stepRow.all().includes(actual.connectivityControl.button),'real VPN check action sits below the Auto controls');
 assert(!source.includes("E('div',{'class':'hv-tools-row'},[renderConnectivityCheck"),'no duplicate controls in page header');
 const live=nodes.findIndex(n=>n.attrs.id==='hv-auto-live-chart'),day=nodes.findIndex(n=>n.attrs.id==='hv-auto-day-chart');
 assert(live>=0&&day>live,'Overview includes daily graph directly after live graph');
 const statistics=card.children[1];
 assert.equal(statistics.attrs['data-auto-disclosure'],'live-statistics');assert.equal(statistics.tag,'details');assert(!statistics.attrs.open);assert(!card.all().some(n=>n.attrs['data-auto-disclosure']==='technical'));
 assert(!automatic.all().some(n=>n.attrs.id==='hv-auto-live-chart'||n.attrs.id==='hv-auto-day-chart'),'expanded charts no longer push down manual controls inside Auto');
 assert(statistics.all().some(n=>n.attrs.id==='hv-auto-live-chart')&&statistics.all().some(n=>n.attrs.id==='hv-auto-day-chart'),'both graphs remain available together');
 const manual=nodes.find(n=>n.attrs['data-manual-controls']==='1');assert(manual&&card.children.includes(manual),'manual panel is a separate sibling');
 const choices=manual.all().filter(n=>n.tag==='button'&&n.attrs['data-manual-direction']!=='resume'&&n.attrs['data-manual-direction']);
 assert.equal(choices.length,2);assert(choices[0].attrs.class.includes('hv-manual-green'));assert(choices[1].attrs.class.includes('hv-manual-yellow'),'working spare card is amber');assert(choices[0].disabled);assert(choices[0].all().some(n=>n.attrs.class==='hv-manual-enable'&&/In use|Используется/.test(n.text())));assert(choices[1].all().some(n=>n.attrs.class==='hv-manual-enable'));
 assert.strictEqual(card.children[2],manual,'manual selection immediately follows compact disclosure headers');
 statistics.open=true;statistics.listeners.toggle();
 let redrawn=actual.renderAutoControl(st,inv,()=>Promise.resolve());assert.equal(redrawn.children[1].attrs.open,'open');assert.equal(redrawn.children[1].attrs.open,'open','ordinary redraw preserves expansion');
 redrawn.children[1].open=false;redrawn.children[1].listeners.toggle();redrawn=actual.renderAutoControl(st,inv,()=>Promise.resolve());assert(!redrawn.children[1].attrs.open,'collapse is remembered independently');
 assert(!manual.text().includes('default')&&!manual.text().includes('Нет свежего подтверждения пути'));
 for(const design of ['a','b','c']){
  const page=actual.renderDesignOverview(design,{status:st,inventory:inv,rows:st.profiles,month:{},controlCard:card});
  assert.strictEqual(page.children[0].children[0],card,design+' puts Auto first');
  assert(page.all().some(n=>n.attrs.id==='hv-auto-day-chart'),design+' keeps daily graph');
  assert(page.all().some(n=>n.attrs['data-manual-controls']==='1'),design+' keeps manual card');
 }
 console.log('PASS: source Auto layout in A/B/C keeps both graphs in remembered collapsed statistics and raises separate manual controls');
}
