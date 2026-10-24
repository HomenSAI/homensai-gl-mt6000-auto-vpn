const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{removeAttribute(k){delete this.attrs[k];}querySelectorAll(selector){return this.children.filter(x=>x instanceof N).flatMap(x=>[...(x.tag===selector?[x]:[]),...x.querySelectorAll(selector)]);}querySelector(selector){return this.querySelectorAll(selector)[0]||null;}constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children);this.listeners={};}appendChild(n){this.children.push(n);}setAttribute(k,v){this.attrs[k]=v;if(k==='open')this.open=true;}addEventListener(k,f){this.listeners[k]=f;}}
const c={bi:a=>a,E:(...a)=>new N(...a),Date};vm.createContext(c);vm.runInContext(fs.readFileSync('router/channel_guidance.inc.js','utf8'),c);
const primary={id:'wireguard:peer_1'},reserve={id:'openvpn:1_1'},other={id:'openvpn:1_2'},rows=[reserve,other,primary],inventory={settings:{plan_source:primary.id,plan_target:reserve.id}},status={profiles:rows,native_failover:{state:'COMMITTED',source:primary.id,target:reserve.id}};
assert.equal(c.roleOrderedRows(rows,status,inventory,100)[0].id,primary.id);assert.equal(c.roleOrderedRows(rows,status,inventory,100)[1].id,reserve.id);assert.strictEqual(rows[0],reserve,'presentation never reorders saved input');
let cards=new N('div'),hosts=c.channelCardHosts(rows,status,inventory,cards);for(const p of c.roleOrderedRows(rows,status,inventory,100))hosts.get(p).appendChild(new N('article',{'data-profile':p.id}));hosts.finish();
assert.equal(cards.children[0].attrs['data-profile'],primary.id);assert.equal(cards.children[1].attrs['data-profile'],reserve.id);const details=cards.children[2];assert(!details.attrs.open);assert.equal(details.children[1].children.length,1);
details.open=true;details.listeners.toggle();cards=new N('div');hosts=c.channelCardHosts(rows,status,inventory,cards);hosts.finish();assert.equal(cards.children[0].attrs.open,'open','polling retains disclosure without swapping roles');
const p={id:primary.id,interface:'wgclient1',time:100,vendor_state:'SETTLED',server_endpoint:{profile:primary.id,interface:'wgclient1',time:100,host:'198.51.100.8',port:51820,transport:'udp',source:'live-kernel-peer'}};
assert(c.endpointText(p,101).includes('198.51.100.8:51820'));assert(!c.endpointText(p,200).includes('198.51.100.8'));
for(const changed of [{profile:reserve.id},{source:'configured'},{host:'user:password@host'},{host:'<img>'},{port:0}]){const bad=JSON.parse(JSON.stringify(p));Object.assign(bad.server_endpoint,changed);assert.equal(c.endpointText(bad,101),'Server address: not observed');}
assert(!c.roleDescription(primary,status,inventory).includes('default'));assert(c.roleDescription(reserve,status,inventory).includes('Reserve'));
console.log('PASS: fixed primary/reserve positions, collapsed other cards with persistent expansion, truthful fresh bound peer addresses and no default-group noise');

// Execute the generated current-checks renderer, not a duplicate of its cell wiring.
let observed;
c.MutationObserver=class{constructor(f){this.f=f;}observe(){observed=this.f;}};
c.serverTitle=p=>p.name||p.id;c.checkLampCell=()=>new N('td');c.cell=v=>new N('td',{},[v]);c.protocolLabel=p=>p.protocol;c.healthBadge=()=>new N('span');c.profileHealth=()=>({state:'inactive'});c.tr=x=>x;
c.rows=[reserve,other,primary,...Array.from({length:8},(_,i)=>({id:'other'+i}))];
c.inventory=inventory;c.status=status;c.status.profiles=c.rows;
Object.assign(primary,p,{time:Date.now()/1000});primary.server_endpoint.time=primary.time;
Object.assign(reserve,{interface:'ovpnclient1',vendor_state:'SETTLED',time:primary.time,server_endpoint:{profile:reserve.id,interface:'ovpnclient1',time:primary.time,host:'203.0.113.20',port:443,transport:'tcp',source:'live-kernel-peer'}});
let output;
c.put=(key,node)=>{output=node;};c.addSearch=()=>{};
const manifest=JSON.parse(fs.readFileSync('VERSION.json','utf8'));
const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+manifest.application.ui_module+'.js','utf8');
const start=source.indexOf("var table=E('table',{'class':'table hv-check-table'}");
assert(start>=0);
const end=source.indexOf("limitTableRows(table,5,'current-checks-other'));",start)+"limitTableRows(table,5,'current-checks-other'));".length;
vm.runInContext(source.slice(start,end),c);
const table=output.children[0],button=output.children[1];
const data=()=>table.querySelectorAll('tr').filter(row=>row.querySelector('td'));
const visible=()=>data().filter(row=>!row.hidden&&!row.attrs['data-over-limit']);
assert.equal(data().length,11);assert.equal(visible().length,5);
assert.equal(data()[0].children[2].children[0],'Primary channel');assert.equal(data()[1].children[2].children[0],'Reserve channel');
function text(n){return n instanceof N?n.children.map(text).join(' '):String(n||'');}
assert(text(data()[0]).includes('198.51.100.8:51820'));assert(text(data()[1]).includes('203.0.113.20:443'));assert(!text(table).includes('default'));
button.attrs.click();assert.equal(visible().length,11);button.attrs.click();assert.equal(visible().length,5);
// Search reaches a row outside the initial five; sorting/reordering reapplies the limit.
data().forEach((row,i)=>row.hidden=i!==10);observed();assert.equal(visible().length,1);assert(button.hidden);
data().forEach(row=>row.hidden=false);table.children=[table.children[0],...data().reverse()];observed();assert.equal(visible().length,5);
console.log('PASS: generated current-checks table shows five rows, explicit roles, bound live IPs, expand/collapse and full-list filtering/reordering');
