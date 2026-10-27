const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children||[]).flat();}appendChild(n){this.children.push(n);}get firstChild(){return this.children[0];}removeChild(n){this.children.splice(this.children.indexOf(n),1);}all(){return [this,...this.children.filter(x=>x instanceof N).flatMap(x=>x.all())];}}
const c={E:(...a)=>new N(...a),bi:en=>en,Date:class extends Date{static now(){return 1000000;}}};vm.createContext(c);
for(const name of ['ui_logic','auto_panel','identity_panel','sidebar_status'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
const row=id=>({id,time:999,interface:id,dns_ok:true,https_success:2});
const state=id=>({time:999,version:'0.9.0-alpha41',profiles:[row('a'),row('b')],native_failover:{time:999,state:id==='a'?'OBSERVING':'COMMITTED',mode:'continuous-pair',readiness_verified:true,source:'a',target:'b'},channel_path:{time:999,confirmed:true,active_profile_id:id,source_profile_id:'a',target_profile_id:'b'}});
for(const selected of ['a','b']){
 const root=new N('div');c.fillSideStatus(root,state(selected),{settings:{}});
 const channels=root.children.find(n=>n.attrs.class==='hv-side-channel-lamps');assert(channels,'channel lamps always exist below Auto/Monitoring');
 const knobs=channels.all().filter(n=>(n.attrs.class||'').includes('hv-auto-pill-knob'));
 assert.equal(knobs.length,2);assert(knobs[selected==='a'?0:1].attrs.class.includes('hv-lamp-on'));assert(knobs[selected==='a'?1:0].attrs.class.includes('hv-lamp-switching'),'a working spare channel is amber (ready), neither green nor red');
}
{const st=state('b');Object.assign(st.profiles[0],{code:'VPN-003',dns_ok:false,https_success:0});const root=new N('div');c.fillSideStatus(root,st,{settings:{}});
 const knobs=root.all().filter(n=>(n.attrs.class||'').includes('hv-auto-pill-knob')).slice(2);assert(knobs[0].attrs.class.includes('hv-lamp-off'),'failing channel is red');assert(knobs[1].attrs.class.includes('hv-lamp-on'));
 const stale=new N('div');c.fillSideStatus(stale,Object.assign(state('a'),{time:1}),{settings:{}});assert(stale.all().filter(n=>(n.attrs.class||'').includes('hv-auto-pill-knob')).slice(2).every(k=>k.attrs.class.includes('hv-lamp-off')),'no data is red, never grey');}
console.log('PASS: sidebar channel lamps show the real channel state: working green, failing or no data red');
