const fs=require('fs'),vm=require('vm'),assert=require('assert');
const store={};let clock=1000000;
const c={bi:(en)=>en,Date:{now:()=>clock},window:{localStorage:{getItem:k=>store[k]||null,setItem:(k,v)=>{store[k]=v;}}},Math,Number,JSON,String,Array};
vm.createContext(c);
const src=fs.readFileSync('router/auto_panel.inc.js','utf8');
const a=src.indexOf('/* Countdown on the Auto button'),b=src.indexOf('function autoCountdownTick');
vm.runInContext(src.slice(a,b),c);
// Nothing measured yet: honest defaults.
assert.equal(c.autoDurationEstimate('start'),30);assert.equal(c.autoDurationEstimate('stop'),10);
// The estimate is the median of the last five measured runs.
[12,40,14,13,90,15].forEach(s=>c.autoDurationRecord('start',s));
assert.deepEqual(JSON.parse(store['hv-auto-durations']).start,[40,14,13,90,15]);
assert.equal(c.autoDurationEstimate('start'),15);
c.autoDurationRecord('start',-1);c.autoDurationRecord('start',9999);assert.equal(JSON.parse(store['hv-auto-durations']).start.length,5,'impossible durations are ignored');
// Text counts down and then shows the overrun instead of stopping at zero.
vm.runInContext("AUTO_COUNTDOWN={kind:'start',t0:Date.now(),estimate:15}",c);
assert.equal(c.autoCountdownText(),'15 s');clock+=6200;assert.equal(c.autoCountdownText(),'9 s');clock+=12000;assert.equal(c.autoCountdownText(),'+3 s');
console.log('PASS: Auto countdown uses measured durations and shows the overrun');

const f={bi:(en)=>en,countryName:p=>p.country,protocolLabel:p=>p.protocol==='wireguard'?'WireGuard':'OpenVPN'};vm.createContext(f);
const fp=fs.readFileSync('router/fault_panel.inc.js','utf8');vm.runInContext(fp.slice(fp.indexOf('function faultChannelName'),fp.indexOf('function faultPanel(')),f);
const settings={plan_source:'wireguard:peer_2002',plan_target:'openvpn:1'};
assert.equal(f.faultChannelName({id:'wireguard:peer_2002',country:'Germany',protocol:'wireguard',vendor_tunnel_id:'wireguard:wgclient1'},settings),'Primary channel — Germany · WireGuard (wgclient1)');
assert(/^Reserve channel/.test(f.faultChannelName({id:'openvpn:1',protocol:'openvpn'},settings)));
console.log('PASS: failure test names the primary or reserve channel plainly');
