// Owner report (31 Oct 2026, Lua line): every channel card said "Server address: not observed" although traffic went
// through the tunnel - the Lua monitor did not publish profiles[].server_endpoint. lua/server_endpoint.lua now fills
// it exactly like server_endpoint.py; this test renders the real card code with a status row of that shape and
// checks the address is shown in the pair cards, the other-VPN cards and the minimum channel cards, and that the
// delay on those cards comes from the shared last-ping reading (no dash while a measurement exists).
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
  constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children||[]).flat().filter(x=>x!=null);this.listeners={};}
  addEventListener(e,f){this.listeners[e]=f;}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}getAttribute(k){return this.attrs[k];}
  appendChild(c){this.children.push(c);return c;}
  all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}
  text(){return this.children.map(x=>x instanceof N?x.text():String(x)).join(' ');}
}
const NOW=1761830400;
// The fields of server_endpoint.observe / server_endpoint.lua (same names, same source tag)
function endpoint(id,iface,host,port,transport,time){return {profile:id,interface:iface,host,port,transport,time,source:'live-kernel-peer'};}
function row(id,iface,ep,extra){
  return Object.assign({id,protocol:id.split(':')[0],interface:iface,name:id,vendor_state:'SETTLED',vendor_tunnel_id:id.split(':')[0]+':'+iface,
    vendor_generation:'b'.repeat(32),administrative_state:'enabled',time:NOW-4,observation_valid_for:90,code:null,dns_ok:true,https_success:3,
    ping:{metric:'icmp-rtt-ms',target:'1.1.1.1',state:'checking',code:'PING-CHECK-PENDING',time:null,rtt_ms:null,valid_for:105,interface:iface},
    ping_last:{rtt_ms:31.5,time:NOW-20,target:'1.1.1.1'},server_endpoint:ep},extra||{});
}
const P='wireguard:peer_2',R='openvpn:1_1',O='wireguard:peer_3';
const rows=[row(P,'wgclient1',endpoint(P,'wgclient1','2001:db8::7',51820,'udp',NOW-4)),
  row(R,'ovpnclient1',endpoint(R,'ovpnclient1','203.0.113.20',443,'tcp',NOW-4)),
  row(O,'wgclient2',endpoint(O,'wgclient2','198.51.100.9',51820,'udp',NOW-4))];
const status={time:NOW-4,observation_valid_for:90,response_metric:'icmp-1.1.1.1',profiles:rows,native_failover:{state:'OBSERVING'}};
const inventory={settings:{plan_source:P,plan_target:R},profiles:rows.map(p=>({id:p.id,name:p.name,protocol:p.protocol}))};
for(const language of ['en','ru']){
  const c={console,locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...a)=>new N(...a),Date,Math,Number,String,Object,Array,JSON,
    routerWall:()=>NOW,statusNow:()=>NOW,serverTitle:p=>p.name||p.id,protocolLabel:p=>p.protocol,countryName:()=> 'DE',
    manualFresh:(t,now,limit)=>Number.isFinite(t)&&now-t>=-5&&now-t<=limit,MutationObserver:undefined};
  vm.createContext(c);
  for(const name of ['ui_logic','channel_guidance','minimum_channels'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  c.routerWall=()=>NOW;c.statusNow=()=>NOW;
  c.channelDisplayUse=()=>({state:'selected',kind:'green',label:'In use'});c.reliabilityRecommendation=()=>null;
  const healthy={state:'healthy',label:'OK'};
  c.simpleHomeModel=()=>({source:rows[0],target:rows[1],sourceHealth:healthy,targetHealth:healthy,selectedRole:'source',dataUnavailable:false});
  c.simpleHomeHealth=()=>healthy;
  const server=language==='ru'?'Сервер: ':'Server: ',missing=language==='ru'?'Адрес сервера: не получен':'Server address: not observed';
  assert.strictEqual(c.endpointText(rows[0],NOW),server+'[2001:db8::7]:51820 · UDP');
  assert.strictEqual(c.endpointText(rows[1],NOW),server+'203.0.113.20:443 · TCP');
  // every card of the pair and of the other VPNs shows its own address
  const cascade=c.renderCompactCascade(status,inventory),items=cascade.all().filter(n=>n.attrs['data-profile']);
  assert.strictEqual(items.length,3);
  const text=id=>items.find(n=>n.attrs['data-profile']===id).text();
  assert(text(P).includes('[2001:db8::7]:51820'),text(P));assert(text(R).includes('203.0.113.20:443 · TCP'),text(R));assert(text(O).includes('198.51.100.9:51820'),text(O));
  assert(!cascade.text().includes(missing),'no card says "not observed" while the status carries the address');
  const minimum=c.renderMinimumChannels(status,inventory,null),cards=minimum.all().filter(n=>n.attrs['data-minimum-channel']);
  assert.strictEqual(cards.length,2);
  assert(cards[0].text().includes('[2001:db8::7]:51820'),cards[0].text());assert(cards[1].text().includes('203.0.113.20:443'),cards[1].text());
  // the delay on the card is the shared last-ping reading, never a dash while a measurement exists
  const ms=language==='ru'?'мс':'ms';
  assert(cards[0].text().includes('31.5 '+ms+' (20 '),cards[0].text());
  assert.strictEqual(c.renderChannelPing(rows[0],status,NOW).text(),c.pingReading(rows[0],status,NOW).text);
  // without the field (or with a foreign/old one) the card stays truthful
  const none=JSON.parse(JSON.stringify(rows[0]));delete none.server_endpoint;assert.strictEqual(c.endpointText(none,NOW),missing);
  const foreign=JSON.parse(JSON.stringify(rows[0]));foreign.server_endpoint.interface='wgclient9';assert.strictEqual(c.endpointText(foreign,NOW),missing);
  const old=JSON.parse(JSON.stringify(rows[0]));old.server_endpoint.time=NOW-400;assert.strictEqual(c.endpointText(old,NOW),missing);
}
console.log('PASS: the server address of the Lua status row is shown in the pair, other-VPN and minimum channel cards; card delay uses the shared ping reading');
