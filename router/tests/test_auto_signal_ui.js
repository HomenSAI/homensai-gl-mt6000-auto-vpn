// Three-signal Auto light: green = working and confirmed, yellow = checking or switching, red = a real failure.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(n=>n!=null);}appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=v;}all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join(' ');}}
const inventory={settings:{plan_source:'a',plan_target:'b',setup_complete:true,enabled:true}};
function fixture(t){return {time:t,server_time:t,profiles:[{id:'a',interface:'wgclient1',protocol:'wireguard',time:t,dns_ok:true,https_success:2,code:null},{id:'b',interface:'ovpnclient1',protocol:'openvpn',time:t,dns_ok:true,https_success:2,code:null}],native_failover:{time:t,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,kernel_policy_verified:true,source:'a',target:'b',blockers:[]},auto_control:{requested:'on',pair_phase:'RUNNING',requested_at:900},channel_path:{time:t,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:t,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a',transitioning:false}};}
for(const language of ['en','ru']){
  let now=1000;
  const c={locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...args)=>new N(...args),Date,localStorage:{getItem:()=>null},identityModel:()=>({}),identityLine:()=>'test',versionString:()=>'test',ownGet:(map,key)=>Object.prototype.hasOwnProperty.call(map,key)?map[key]:undefined,errorCodeLink:code=>new N('code',{},code)};
  vm.createContext(c);for(const name of ['ui_logic','auto_panel','manual_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  c.statusNow=()=>now;c.routerWall=()=>now;
  const light=s=>c.autoLightModel(s,inventory,now);
  // Confirmed route: green, and the button says Auto works.
  let s=fixture(1000),l=light(s);assert.equal(c.autoSignal(l),'green');assert(c.autoRuns(l));
  // The 15-second kernel proof ages during a slow status round trip: the last confirmed route is held, still green.
  now=1030;s=fixture(1000);s.time=s.server_time=s.native_failover.time=s.profiles[0].time=s.profiles[1].time=1028;
  l=light(s);assert.equal(c.autoSignal(l),'green','an aged proof within the hold is not a failure');
  // Beyond the hold the router is re-checking: yellow, Auto still runs (no red, button stays on).
  now=1000+c.AUTO_ROUTE_HOLD+20;s=fixture(1000);s.time=s.server_time=s.native_failover.time=s.profiles[0].time=s.profiles[1].time=now-2;
  l=light(s);assert.equal(c.autoSignal(l),'yellow');assert(c.autoRuns(l)&&!c.autoWorking(l),'yellow is not a green claim, but Auto still runs');
  // The router itself reports the route unverified (not just aged): never held, yellow while Auto runs.
  now=2000;c.UI_LAST_ROUTE=null;light(fixture(2000));s=fixture(2000);s.channel_path.checked_at=null;s.channel_path.time=null;s.channel_path.kernel_policy_verified=false;
  l=light(s);assert.notEqual(c.autoSignal(l),'green','an explicit unverified route is never held green');assert.equal(c.autoSignal(l),'yellow');
  // A switch in progress is yellow, never red.
  s=fixture(2000);s.native_failover.state='APPLYING';s.channel_path.transitioning=true;l=light(s);assert.equal(c.autoSignal(l),'yellow');
  // A completed failed check of the selected channel is red at once.
  s=fixture(2000);s.profiles[0].code='VPN-003';s.profiles[0].https_success=0;l=light(s);assert.equal(c.autoSignal(l),'red');assert(!c.autoRuns(l));
  // No connection to the router program: red.
  s=fixture(2000);s.rpc_error='RPC';l=light(s);assert.equal(c.autoSignal(l),'red');
  // Auto off: red (automatic switching does not work), not yellow.
  s=fixture(2000);s.auto_control={requested:'off',pair_phase:'STOPPED',requested_at:900};s.native_failover.state='STOPPED';l=light(s);assert.equal(c.autoSignal(l),'red');
  // The housing has three lamps and lights exactly the signal.
  for(const [state,signal] of [['OBSERVING','green'],['APPLYING','yellow']]){
    s=fixture(2000);s.native_failover.state=state;s.channel_path.transitioning=state==='APPLYING';l=light(s);
    const lamps=c.renderAutoLight(l,'X').all().filter(n=>/\bhv-lamp-(red|yellow|green)\b/.test(n.attrs.class||''));
    assert.equal(lamps.length,3);assert.deepStrictEqual(lamps.filter(n=>/hv-lamp-lit/.test(n.attrs.class)).map(n=>n.attrs.class.match(/hv-lamp-(red|yellow|green)/)[1]),[signal]);
  }
}
console.log('PASS: three-signal Auto light, held confirmed route, yellow re-check/switching, red only on failure (EN/RU)');
