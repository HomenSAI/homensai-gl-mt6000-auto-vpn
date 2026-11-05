// Owner 01.11.2026: under the Auto light two tunnel icons, primary then reserve: green works, red failed, the one carrying traffic marked.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(n=>n!=null);}appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=v;}all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join('');}}
const inventory={settings:{plan_source:'a',plan_target:'b',setup_complete:true,enabled:true}};
function fixture(t,active){return {time:t,server_time:t,profiles:[{id:'a',interface:'wgclient1',protocol:'wireguard',time:t,dns_ok:true,https_success:2,code:null},{id:'b',interface:'ovpnclient1',protocol:'openvpn',time:t,dns_ok:true,https_success:2,code:null}],native_failover:{time:t,state:active==='b'?'COMMITTED':'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,kernel_policy_verified:true,source:'a',target:'b',blockers:[]},auto_control:{requested:'on',pair_phase:'RUNNING',requested_at:900},channel_path:{time:t,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:t,source_profile_id:'a',target_profile_id:'b',active_profile_id:active,transitioning:false}};}
for(const language of ['en','ru']){
  const now=2000;
  const c={locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...args)=>new N(...args),Date,localStorage:{getItem:()=>null},identityModel:()=>({}),identityLine:()=>'test',versionString:()=>'test',ownGet:(map,key)=>Object.prototype.hasOwnProperty.call(map,key)?map[key]:undefined};
  vm.createContext(c);for(const name of ['ui_logic','auto_panel','manual_panel','sidebar_status'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  c.statusNow=()=>now;c.routerWall=()=>now;
  const icons=l=>c.renderAutoLight(l,'X').all().filter(n=>/\bhv-tn\b/.test(n.attrs.class||'')).map(n=>({cur:/hv-tc/.test(n.attrs.class),color:n.all().find(d=>/hv-dot-/.test(d.attrs.class||'')).attrs.class.match(/hv-dot-(green|red)/)[1],text:n.text()}));
  // On the reserve with the primary failed: primary red, reserve green and marked as the working one.
  let s=fixture(2000,'b');s.profiles[0].code='VPN-003';s.profiles[0].https_success=0;
  let l=c.autoLightModel(s,inventory,now);assert.equal(l.key,'reserve');
  let i=icons(l);assert.equal(i.length,2);
  assert.deepStrictEqual(i.map(x=>[x.color,x.cur]),[['red',false],['green',true]]);
  assert.equal(i[0].text,language==='ru'?'Основной':'Primary');assert.equal(i[1].text,language==='ru'?'Резерв':'Reserve');
  // On the primary with both healthy: both green, the primary marked.
  l=c.autoLightModel(fixture(2000,'a'),inventory,now);assert.equal(l.key,'ok');
  assert.deepStrictEqual(icons(l).map(x=>[x.color,x.cur]),[['green',true],['green',false]]);
  // Auto off: no tunnel icons.
  s=fixture(2000,'a');s.auto_control={requested:'off',pair_phase:'STOPPED',requested_at:900};s.native_failover.state='STOPPED';
  assert.equal(icons(c.autoLightModel(s,inventory,now)).length,0);
  // 03.11.2026: Auto off with healthy tunnels says nothing more; with a selected tunnel down the owner is told that Auto
  // brings the pair up (the GL toggle does not while preparation keeps their autostart off).
  l=c.autoLightModel(s,inventory,now);assert.equal(l.key,'off');assert.equal(l.hint,'');assert.equal(l.code,null);
  const hint=language==='ru'?'Туннели поднимает Auto — нажмите Start.':'Auto brings the tunnels up — press Start.';
  for(const down of [{administrative_state:'disabled'},{code:'VPN-001',dns_ok:false,https_success:0}]){
    const d=fixture(2000,'a');d.auto_control=s.auto_control;d.native_failover.state='STOPPED';Object.assign(d.profiles[1],down);
    l=c.autoLightModel(d,inventory,now);assert.equal(l.key,'off');assert.equal(l.hint,hint);assert.equal(l.code,'TUNNEL-DISCONNECTED');
  }
  const unbound=fixture(2000,'a');unbound.auto_control=s.auto_control;unbound.native_failover.state='STOPPED';unbound.profiles[1].interface=null;unbound.profiles[1].code='PROFILE-INACTIVE';
  assert.equal(c.autoLightModel(unbound,inventory,now).hint,'','a profile without a GL interface is a setup problem, not a stopped tunnel');
  const failed=fixture(2000,'a');failed.auto_control=s.auto_control;failed.native_failover.state='STOPPED';failed.profiles[1].code='VPN-003';
  assert.equal(c.autoLightModel(failed,inventory,now).hint,'','a failing but connected tunnel is not "down"');
}
console.log('PASS: Auto tunnel icons - primary and reserve, green works, red failed, the carrying one marked (EN/RU)');
