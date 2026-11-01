// Owner 01.11.2026: "Server uptime and failures" shows only the Auto pair plus servers with hours or failures in the
// selected period; the rest are hidden behind "Show all (N)". The built page wires it into the Statistics page.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[];
  (Array.isArray(children)?children:[children]).forEach(c=>{if(c!=null)this.children.push(c);});}
  appendChild(c){this.children.push(c);return c;} setAttribute(k,v){this.attrs[k]=v;}}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const text=n=>typeof n==='string'||typeof n==='number'?String(n):n instanceof Node?n.children.map(text).join(''):'';
const ctx={E:(t,a,c)=>new Node(t,a,c),bi:en=>en,Intl,Date,Object,console};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('router/ui_histogram.js','utf8')+'\n'+fs.readFileSync('router/server_pair_histogram.inc.js','utf8'),ctx);
const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const day=(up,failures)=>({[today]:{up,down:0,unknown:0,connections:0,failures}});
const activity={'wireguard:peer_1':{name:'Primary WG',protocol:'wireguard',days:{}},'openvpn:1_2':{name:'Reserve OVPN',protocol:'openvpn',days:day(0,0)},
  'openvpn:9_9':{name:'Germany · OpenVPN',protocol:'openvpn',days:day(0,0)},'openvpn:8_8':{name:'Used today',protocol:'openvpn',days:day(3600,0)},
  'wireguard:peer_5':{name:'Failed today',protocol:'wireguard',days:day(0,2)},'wireguard:peer_6':{name:'Idle WG',protocol:'wireguard',days:{'2000-01-01':{up:9999}}}};
const settings={plan_source:'wireguard:peer_1',plan_target:'openvpn:1_2'};
let redraws=0;
const names=s=>walk(s).filter(n=>n.tag==='b').map(text);
let section=ctx.serverPairHistogram({activity},()=>{},'day',settings,{},()=>redraws++);
assert.deepEqual(names(section).sort(),['Failed today','Primary WG','Reserve OVPN','Used today']);
let toggle=walk(section).find(n=>n.tag==='button'&&n.attrs['data-server-filter']==='all');
assert(toggle,'a Show all toggle');assert.equal(section.attrs['data-stats-reset'],'quality','reset next to the chart');assert.equal(text(toggle),'Show all (6)');assert(/Hidden: 2/.test(text(section)));
toggle.attrs.click();assert.equal(redraws,1);
section=ctx.serverPairHistogram({activity},()=>{},'day',settings,{},()=>redraws++);
assert.equal(names(section).length,6,'all servers after the toggle');
toggle=walk(section).find(n=>n.tag==='button'&&n.attrs['data-server-filter']==='pair');assert(toggle);toggle.attrs.click();
// the live Auto pair from native_failover also counts; nothing hidden -> no toggle
section=ctx.serverPairHistogram({activity:{'openvpn:9_9':activity['openvpn:9_9']}},()=>{},'day',{},{native_failover:{source:'openvpn:9_9'}});
assert.deepEqual(names(section),['Germany · OpenVPN']);assert(!walk(section).some(n=>n.tag==='button'));
// built page: the Statistics page uses the filtered histogram
const built=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+JSON.parse(fs.readFileSync('VERSION.json','utf8')).application.ui_module+'.js','utf8');
assert(built.includes("put('statistics',serverPairHistogram(")&&built.includes('function serverPairHistogram('),'built page wiring');
console.log('PASS: server uptime shows the Auto pair and active servers; Show all (N) toggles the rest');
