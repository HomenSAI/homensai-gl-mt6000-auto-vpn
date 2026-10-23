const fs=require('fs'),vm=require('vm'),assert=require('assert');
// Runs the generated page's helper code (everything before the view object) in a sandbox, then renders the three overviews.
class N{constructor(t,a,c){this.tag=t;this.attrs=a||{};this.children=[].concat(c===undefined?[]:c).flat().filter(x=>x!=null);}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join(' ');}
  addEventListener(){}removeAttribute(k){delete this.attrs[k];}get style(){return this._s=this._s||{};}get classList(){return {add(){},remove(){},toggle(){}};}set textContent(v){this.children=[String(v)];}
  appendChild(c){this.children.push(c);return c;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]==null?null:this.attrs[k];}}
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base='router/files/www/luci-static/resources/view/homensai-vpn/';
const source=fs.readFileSync(base+page+'.js','utf8');
const prefix=source.slice(0,source.lastIndexOf('return view.extend({'));
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
  assert(/Germany/.test(text)&&/Netherlands/.test(text),d+': countries from the profile names');
  assert(!/nordvpn\.com/.test(text),d+': provider host names are never shown');
  assert(node.all().some(n=>n.attrs&&n.attrs['data-profile']==='c'),d+': a profile that is not connected is still listed');
}
// A: strip, KPIs, servers with sparkline, recent events with codes.
let a=render(ctx,'a',fixture()).node,t=a.text();
assert(/Everything works\./.test(t));assert(/2 of 2/.test(t));assert(/Traffic this month/.test(t)&&/3\.000 GB/.test(t));
assert(a.all().some(n=>n.tag==='svg'&&/hv-dv-spark/.test(n.attrs.class)),'A: sparkline');
assert(/Reserve confirmed/.test(t)&&/Rolled back to the previous route/.test(t)&&/DNS-001/.test(t));
// Tone follows the real state: reserve in use -> warning, no data -> bad, nothing connected -> off.
assert(a.all()[1].attrs.class.includes('hv-dv-tone-ok'));
a=render(ctx,'a',fixture({native_failover:{state:'COMMITTED',source:'a',target:'b',time:now-1}})).node;assert(/Working on the reserve/.test(a.text()));assert(/hv-dv-tone-warn/.test(a.all()[1].attrs.class));
a=render(ctx,'a',fixture({rpc_error:'RPC-UNAVAILABLE'})).node;assert(/No data from the router/.test(a.text()));assert(/hv-dv-tone-bad/.test(a.all()[1].attrs.class));
const none=fixture({profiles:[],samples:[],native_history:{events:[]}});
a=render(ctx,'a',none,[]).node;assert(/No VPN is connected/.test(a.text()));assert(/No VPN profiles found/.test(a.text()));assert(/No switches or failures are recorded/.test(a.text()));
// B: plain words, tags, questions, links to the sections that are not in its menu.
let b=render(ctx,'b',fixture()).node;t=b.text();
for(const missing of [undefined,null,'invalid'])assert(render(ctx,missing,fixture()).node.attrs.class.includes('hv-dv-b'),'missing/invalid design renders Calm');
assert(!/Your VPN works|on the reserve/.test(t),'the state block was removed');assert(/What happens if Germany stops working\?/.test(t));assert(/Last thing that happened/.test(t));
['#statistics','#help','#learn','#events'].forEach(h=>assert(b.all().some(n=>n.tag==='a'&&n.attrs.href===h),'B link '+h));
assert(b.all().some(n=>/hv-dv-flag/.test(n.attrs.class||'')&&n.text().trim()==='DE'));
// The VPN list has a separate status column with a lamp per profile.
const lampCol=b.all().filter(n=>/hv-dv-statuscol/.test(n.attrs.class||''));assert.equal(lampCol.length,3);
assert(lampCol[0].all().some(n=>/hv-check-green/.test(n.attrs.class||'')),'working VPN: green lamp');assert(lampCol[1].all().some(n=>/hv-check-yellow/.test(n.attrs.class||'')),'healthy standby: yellow lamp');assert(lampCol[2].all().some(n=>/hv-check-red/.test(n.attrs.class||'')),'known disconnected: red lamp');
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
 assert.doesNotThrow(()=>{ctx.renderDecisionExplanation(hostileStatus);ctx.renderCascadePath(Object.assign(fixture(),{profiles:[Object.assign({},fixture().profiles[0],{code:'a"]'})]}));});}
// Russian: same structure, translated text.
const ru=sandbox('ru');vm.runInContext("locale='ru'",ru);
const ra=render(ru,'a',fixture()).node.text();assert(/Всё работает\./.test(ra)&&/Последние события/.test(ra)&&/Германия/.test(ra));
assert(/Что будет, если/.test(render(ru,'b',fixture()).node.text()));assert(/Журнал/.test(render(ru,'c',fixture()).node.text()));
// A broken design view must leave the original overview in place (generated wiring).
assert(source.includes("renderDesignOverview(currentDesign(),{status:status,inventory:inventory,rows:rows,month:month,controlCard:controlCard})"));
assert(source.includes("pages.overview.setAttribute('data-hv-dv','1')")&&source.includes('DESIGN-VIEW-ERROR'));
assert(source.includes('draw(lastGoodStatus||data[1])'),'changing the design redraws at once');
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
console.log('PASS: A/B/C overviews from real status, tones, hostile names, Russian, keys and wiring');

// Render the actual control subtree, not a placeholder: daily graph/manual cards must survive every overview layout.
{
 const actual=sandbox('ru');actual.locale='ru';actual.document.documentElement={clientWidth:1200};actual.poll.add=()=>{};
 const st=fixture({native_failover:{state:'OBSERVING',time:now,source:'a',target:'b',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true},
   auto_control:{requested:'on',requested_at:now-60,pair_phase:'RUNNING',control_revision:'a'.repeat(32)},
   manual_switch_control:{mode:'continuous-pair',time:now,available:true,control_revision:'a'.repeat(32),primary:{allowed:false,blockers:['RETURN-NOT-APPLICABLE']},reserve:{allowed:true,blockers:[]}},
   channel_path:{time:now,confirmed:true,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a',transitioning:false},
   accounting:{reliability:{route_history:{segments:[{start:now-100,end:now,kind:'source'}]}}}});
 const inv={settings:{plan_source:'a',plan_target:'b',pair_auto_mode:'router-probed-ipv4'},profiles:st.profiles};
 const card=actual.renderAutoControl(st,inv),nodes=card.all();
 const live=nodes.findIndex(n=>n.attrs.id==='hv-auto-live-chart'),day=nodes.findIndex(n=>n.attrs.id==='hv-auto-day-chart');
 assert(live>=0&&day>live,'Overview includes daily graph directly after live graph');
 const manual=nodes.find(n=>n.attrs['data-manual-controls']==='1');assert(manual&&card.children.includes(manual),'manual panel is a separate sibling');
 const choices=manual.all().filter(n=>n.tag==='button'&&n.attrs['data-manual-direction']!=='resume'&&n.attrs['data-manual-direction']);
 assert.equal(choices.length,2);assert(choices[0].attrs.class.includes('hv-manual-green'));assert(choices[1].attrs.class.includes('hv-manual-red'));assert(choices.every(n=>n.text().includes('Включить')));
 assert(!manual.text().includes('default')&&!manual.text().includes('Нет свежего подтверждения пути'));
 for(const design of ['a','b','c']){
  const page=actual.renderDesignOverview(design,{status:st,inventory:inv,rows:st.profiles,month:{},controlCard:card});
  assert(page.all().some(n=>n.attrs.id==='hv-auto-day-chart'),design+' keeps daily graph');
  assert(page.all().some(n=>n.attrs['data-manual-controls']==='1'),design+' keeps manual card');
 }
 console.log('PASS: generated complete A/B/C control tree includes live/day graphs and separate primary/reserve card-buttons');
}
