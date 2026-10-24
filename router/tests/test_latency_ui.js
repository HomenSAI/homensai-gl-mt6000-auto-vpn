const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).filter(v=>v!=null);this.listeners={};}
 appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0]||null;}
 setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}addEventListener(k,f){this.listeners[k]=f;}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
}
const now=100000,c={locale:'en',bi:(a)=>a,E:(...a)=>new N(...a),document:{createElementNS:(_,tag)=>new N(tag)},Date,serverTitle:p=>p.name||p.id,protocolLabel:p=>p.protocol,statusNow:()=>now,profileHealth:(p,t)=>({state:p.time<=t+5&&t-p.time<=90&&p.code===null?'healthy':'unknown'})};
vm.createContext(c);for(const file of ['channel_guidance','latency_panel'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
const inventory={settings:{plan_source:'wireguard:peer_1',plan_target:'openvpn:1_1'}};
function status(){return {profiles:[{id:'wireguard:peer_1',time:now,protocol:'wireguard',code:null,rtt_ms:20,dns_ok:true,https_success:2,vendor_state:'SETTLED'},{id:'openvpn:1_1',time:now,protocol:'openvpn',code:null,rtt_ms:40,dns_ok:true,https_success:2,vendor_state:'SETTLED'}],latency_history:{version:1,metric:'https-rtt-ms',pair:['wireguard:peer_1','openvpn:1_1'],rows:[[now-120,30,50,1,1,'source'],[now-60,40,null,1,0,'target']]}};}
let s=status();assert(c.latencyRecommendation(s,inventory,now).text.includes('wireguard:peer_1'),'recommendation identifies the actual profile');assert.equal(c.latencyRecommendation(s,inventory,now).index,0);s.profiles[0].rtt_ms=80;assert.equal(c.latencyRecommendation(s,inventory,now).index,1);
for(const change of [{time:now-100},{rtt_ms:NaN},{vendor_state:'CHANGING'},{dns_ok:false},{https_success:0}]){s=status();Object.assign(s.profiles[0],change);assert.equal(c.latencyRecommendation(s,inventory,now).index,null);}
s=status();s.profiles[0].rtt_ms=40;assert.equal(c.latencyRecommendation(s,inventory,now).index,null,'ties do not force a recommendation');
s=status();s.latency_history.pair.reverse();assert.equal(c.latencyHistoryRows(s,inventory,now).length,0,'another pair never supplies this graph');
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
assert(JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('Current traffic channel is not confirmed.'),'never bypass route helper refusal');
delete c.vendorDisplaySelected;
assert(JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('Traffic currently uses the primary channel.'));
s.rpc_error='RPC-UNAVAILABLE';assert.equal(c.latencyRecommendation(s,inventory,now).index,null);
assert(JSON.stringify(c.renderLatencyRecommendation(s,inventory)).includes('Current traffic channel is not confirmed.'),'RPC error cannot reuse cached selection');
assert(!JSON.stringify(c.renderLatencyStatistics([],now-60,now)).includes('NaN'));
console.log('PASS: weighted window statistics, empty history, route-helper refusal and cached RPC-error fences');
