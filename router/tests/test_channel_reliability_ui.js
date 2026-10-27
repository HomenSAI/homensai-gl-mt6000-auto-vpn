const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children);}}
const c={bi:(a,b)=>b,E:(...a)=>new N(...a),Date,Math,Number,Array,Object,locale:'ru'};
vm.createContext(c);
for(const f of ['ui_logic','channel_guidance','design_views'])vm.runInContext(fs.readFileSync('router/'+f+'.inc.js','utf8'),c);
vm.runInContext("function vendorDisplayMember(status,inventory,role,now){var id=inventory.settings[role==='source'?'plan_source':'plan_target'];return status.profiles.filter(function(p){return p.id===id;})[0]||null;}function vendorDisplaySelected(){return null;}function serverTitle(p){return p.name||p.id;}function safeCode(code){return typeof code==='string'&&/^[A-Z][A-Z0-9-]{1,95}$/.test(code);}",c);
const now=1000,primary={id:'wireguard:peer_1',name:'de1552',interface:'wgclient1',time:now-5,code:'VPN-003',dns_ok:false,https_success:0};
const reserve={id:'openvpn:1_1',name:'ua66',interface:'ovpnclient2',time:now-5,code:null,dns_ok:true,https_success:2};
const spare={id:'openvpn:1_9',name:'de2000'},weak={id:'openvpn:1_8',name:'ua90'};
function samples(profile,ok,total,start=now-290){
  const rows=[];for(let i=0;i<total;i++){const good=i<ok;rows.push({id:profile.id,time:start+i*10,code:good?null:'VPN-003',dns_ok:good,https_success:good?2:0});}return rows;
}
const inventory={settings:{plan_source:primary.id,plan_target:reserve.id}};
const status={profiles:[primary,reserve,spare,weak],time:now-2,server_time:now,samples:[...samples(primary,9,30),...samples(reserve,30,30)],
  accounting:{quality:{[spare.id]:{buckets:{a:{n:200,success:198,rtt_sum:200*300}}},[weak.id]:{buckets:{a:{n:200,success:150,rtt_sum:200*200}}},[reserve.id]:{buckets:{a:{n:100,success:100,rtt_sum:100*400}}}}}};

// Loss share is measured over the retained window; too few samples give no verdict.
const r=c.channelReliability(primary,status,now);
assert.equal(r.n,30);assert.equal(r.bad,21);assert.equal(Math.round(r.loss),70);assert.equal(r.unreliable,true);
assert.equal(c.channelReliability(reserve,status,now).unreliable,false);
assert.equal(c.channelReliability(primary,{samples:samples(primary,0,5)},now),null);
assert.equal(c.channelReliability(primary,{samples:samples(primary,0,30,now-1200)},now),null,'old samples are outside the window');
assert.equal(c.channelReliability(primary,{samples:[...samples(primary,30,30),{id:primary.id,time:now-1,code:'CHECK-001'}]},now).n,30,'unverifiable cycles are not counted as loss');
assert(c.reliabilityText(r).includes('70%')&&c.reliabilityText(r).includes('21 из 30'));

// Channel label names the problem and its percentage and carries the catalogue code.
const use=c.channelDisplayUse(primary,status,inventory);
assert(use.label.startsWith('Проблема с надёжностью: потери проверок 70%'),use.label);assert.equal(use.code,'CHANNEL-UNRELIABLE');assert.equal(use.kind,'red');
const ok=c.channelDisplayUse(reserve,status,inventory);assert(!ok.code&&!/надёжн/.test(ok.label));
// A connected tunnel that mostly passes now but lost many earlier checks is not green.
const flaky=Object.assign({},primary,{code:null,dns_ok:true,https_success:2});
const mixed=c.channelDisplayUse(flaky,Object.assign({},status,{profiles:[flaky,reserve,spare,weak]}),inventory);
assert.equal(mixed.kind,'yellow');assert(mixed.label.startsWith('Работает, но проблема с надёжностью'),mixed.label);
// A stopped tunnel is a connection problem, never a reliability statistic.
const down=Object.assign({},primary,{code:'VPN-001'});assert(!c.channelDisplayUse(down,Object.assign({},status,{profiles:[down,reserve]}),inventory).code);

// Recommendation: computed from the statistics, best measured alternative only above the confidence floor.
const rec=c.reliabilityRecommendation(status,inventory,now);
assert.equal(rec.code,'CHANNEL-UNRELIABLE');
assert(rec.text.includes('Держите трафик на резерве (потери 0%)'),rec.text);assert(rec.text.includes('de2000')&&rec.text.includes('99%'),rec.text);assert(!rec.text.includes('ua90'),'below the success floor');
const none=c.reliabilityRecommendation(Object.assign({},status,{accounting:{quality:{}}}),inventory,now);assert(none.text.includes('мало измерений'),none.text);
assert.equal(c.reliabilityRecommendation(Object.assign({},status,{samples:samples(primary,30,30).concat(samples(reserve,30,30))}),inventory,now),null,'no recommendation when both are reliable');
const both=c.reliabilityRecommendation(Object.assign({},status,{samples:[...samples(primary,9,30),...samples(reserve,12,30)]}),inventory,now);assert(both.text.includes('Оба канала'),both.text);
const reserveBad=c.reliabilityRecommendation(Object.assign({},status,{samples:[...samples(primary,30,30),...samples(reserve,9,30)]}),inventory,now);assert(reserveBad.text.includes('резервного канала')&&reserveBad.text.includes('Держите трафик на основном'),reserveBad.text);
// Catalogue entry exists for the displayed code.
for(const f of ['error_table','error_rows_extra'])assert(fs.readFileSync('router/'+f+'.inc.js','utf8').includes('CHANNEL-UNRELIABLE'));
console.log('PASS: channel reliability loss share, labelled problem with percentage and catalogue code, statistic-based recommendation');
