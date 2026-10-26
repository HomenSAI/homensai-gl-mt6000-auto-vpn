const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(x=>x!=null);this.textContent='';}
 all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}
 text(){return this.textContent+this.children.map(x=>x instanceof N?x.text():String(x)).join(' ');}
 appendChild(x){this.children.push(x);}get firstChild(){return this.children[0];}
 removeChild(x){this.children.splice(this.children.indexOf(x),1);}setAttribute(k,v){this.attrs[k]=v;}
}
for(const locale of ['en','ru']){
 const c={locale,FOOL_RANGES:{},bi:(en,ru)=>locale==='ru'?ru:en,E:(...a)=>new N(...a),window:{location:{hostname:'192.168.11.1',protocol:'http:',port:'8080'}},errorCodeLink:code=>code,
  profileHealth:p=>({state:p.code?'failed':'healthy'}),statusNow:()=>110};
 vm.createContext(c);
 for(const f of ['auto_panel','connectivity_panel','onboarding_panel','minimum_settings'])vm.runInContext(fs.readFileSync('router/'+f+'.inc.js','utf8'),c);
 for(const code of ['HARDWARE-ACCELERATOR-UNVERIFIED','SOFTWARE-ACCELERATOR-UNVERIFIED','PREP-HNAT-CONFIG']){
  const node=c.renderAutoRemedy(code),a=node.all().find(n=>n.tag==='a');
  assert.equal(a.attrs.href,'http://192.168.11.1/#/netnat','GL panel must not inherit the LuCI port');
  assert(node.text().includes('Network Acceleration')&&node.text().includes('Enable')&&node.text().includes('Apply'));
  assert(node.all().some(n=>n.tag==='a'&&n.attrs.href==='https://docs.gl-inet.com/router/en/4/interface_guide/network_acceleration/'));
 }
 assert(c.renderAutoRemedy('FLOW-OFFLOAD-ENABLED').text().includes('Software flow offloading'));
 assert(c.renderAutoRemedy('PREP-WGCLIENT1-AUTOSTART').text().includes('Bring up on boot'));
 assert.equal(c.renderAutoRemedy('PREP-WGCLIENT1-AUTOSTART').all().find(n=>n.tag==='a').attrs.href,'/cgi-bin/luci/admin/network/network');
 assert(c.renderAutoRemedy('PREP-STOCK-VPN-BOOT').text().includes('vpn-client'));
 assert.equal(c.renderAutoRemedy('PREP-STOCK-VPN-BOOT').all().find(n=>n.tag==='a').attrs.href,'/cgi-bin/luci/admin/system/startup');
 assert(c.renderAutoRemedy('PAIR-EXTERNAL-POLICY-CHANGE').text().includes(locale==='ru'?'сессии':'session'));
 assert.equal(c.renderAutoRemedy('unknown'),null);
 assert.equal(c.autoRemedyKey('constructor'),null);
 c.window.location.protocol='https:';assert.equal(c.autoRemedyHref(c.AUTO_REMEDIES.acceleration),'https://192.168.11.1/#/netnat');
 c.connectivityControl={button:new N('button'),message:new N('p'),bar:new N('div'),next:new N('p'),settings:{plan_source:'old',plan_source_tunnel:'wireguard:wgclient1',plan_target:'removed',plan_target_tunnel:'openvpn:ovpnclient1'}};
 const profiles=[{id:'removed',interface:'ovpnclient1',administrative_state:'disabled',time:90,code:'PROFILE-INACTIVE'},
  {id:'ovpn2',interface:'ovpnclient2',administrative_state:'enabled',time:109},
  {id:'replacement',interface:'wgclient1',vendor_tunnel_id:'wireguard:wgclient1',administrative_state:'enabled',time:109}];
 const scan={state:'COMPLETED',request_id:'a'.repeat(32),requested_at:90,measurement_request_id:'a'.repeat(32),measured_at:91,finished_at:92,checked:4,failed:3};
 c.updateConnectivityCheck({profiles,scan});
 assert.equal(c.connectivityControl.bar.children.length,2,'disabled/deleted channels leave current check cells');
 assert.equal(c.connectivityControl.bar.children[0].children[0].text(),locale==='ru'?'Основной канал':'Primary channel','role follows tunnel after server change');
 assert(c.connectivityControl.message.textContent.includes('2 '+(locale==='ru'?'из':'of')+' 2'),'fresh current count replaces historical four-channel check');
 c.updateConnectivityCheck({profiles:[],scan});assert(!c.connectivityControl.message.textContent.includes('4'),'removed channels cannot remain in the last-check total');
 const current={settings:{plan_source:'old',plan_source_tunnel:'wireguard:wgclient1',plan_target:'deleted',plan_target_tunnel:'openvpn:ovpnclient1'},profiles:[{id:'wireguard:new',protocol:'wireguard',interface:'wgclient1',vendor_tunnel_id:'wireguard:wgclient1'},{id:'openvpn:new',protocol:'openvpn',interface:'ovpnclient2',vendor_tunnel_id:'openvpn:ovpnclient2'}]};
 const chosen=c.minimumSettingsPair(current);assert.equal(chosen.source,'wireguard:new');assert.equal(chosen.target,'','removed anchor is not silently rebound to a new tunnel');
}
console.log('PASS: EN/RU actionable acceleration/flow/recovery guides, router links, 4→2 live totals, replaced server roles and deleted-pair settings');
