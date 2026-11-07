// Three-signal Auto light: green = working and confirmed, yellow = checking or switching, red = a real failure.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(n=>n!=null);}appendChild(n){this.children.push(n);return n;}setAttribute(k,v){this.attrs[k]=v;}all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join(' ');}}
const inventory={settings:{plan_source:'a',plan_target:'b',setup_complete:true,enabled:true}};
function fixture(t){return {time:t,server_time:t,profiles:[{id:'a',interface:'wgclient1',protocol:'wireguard',time:t,dns_ok:true,https_success:2,code:null},{id:'b',interface:'ovpnclient1',protocol:'openvpn',time:t,dns_ok:true,https_success:2,code:null}],native_failover:{time:t,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,kernel_policy_verified:true,source:'a',target:'b',blockers:[]},auto_control:{requested:'on',pair_phase:'RUNNING',requested_at:900},channel_path:{time:t,confirmed:true,kernel_policy_verified:true,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',valid_for:15,checked_at:t,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a',transitioning:false}};}
for(const language of ['en','ru']){
  let now=1000;
  const c={locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...args)=>new N(...args),Date,localStorage:{getItem:()=>null},identityModel:()=>({}),identityLine:()=>'test',versionString:()=>'test',ownGet:(map,key)=>Object.prototype.hasOwnProperty.call(map,key)?map[key]:undefined,errorCodeLink:code=>new N('code',{},code)};
  vm.createContext(c);for(const name of ['ui_logic','auto_panel','manual_panel','sidebar_status'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  c.statusNow=()=>now;c.routerWall=()=>now;
  const light=s=>c.autoLightModel(s,inventory,now);
  // Confirmed route: green, and the button says Auto works.
  let s=fixture(1000),l=light(s);assert.equal(c.autoSignal(l),'green');assert(c.autoRuns(l));
  // The page shows an answer for 10-20 s before the next one: a proof that was fresh when the router served
  // the answer stays green while the page waits (content is judged at the answer time).
  now=1025;s=fixture(1000);s.server_time=1001;l=light(s);assert.equal(c.autoSignal(l),'green','a fresh answer stays green between page updates');assert(c.autoRuns(l));
  // The router itself served an old proof: a real route check, yellow while Auto runs.
  now=1030;s=fixture(1000);s.time=s.server_time=s.native_failover.time=s.profiles[0].time=s.profiles[1].time=1028;
  l=light(s);assert.equal(c.autoSignal(l),'yellow','a route re-check is yellow while Auto stays enabled');assert(c.autoRuns(l)&&!c.autoWorking(l),'a check never claims confirmed green, but Auto still runs');
  // Transient controller blockers during a running session are a check, not an alarm.
  now=2000;s=fixture(2000);s.native_failover.state='BLOCKED';s.native_failover.blockers=['OBSERVATION-STALE'];l=light(s);assert.equal(c.autoSignal(l),'yellow','a transient controller state is yellow');assert(c.autoRuns(l));
  // A critical controller alarm is red.
  s=fixture(2000);s.native_failover.state='BLOCKED';s.native_failover.blockers=['ROLLBACK-GIVEN-UP'];l=light(s);assert.equal(c.autoSignal(l),'red');assert(!c.autoRuns(l));
  // Every vendor wait keeps Auto enabled and yellow, and a long one names its observed cause. The main module holds the code only (its
  // size budget): the words live in the optional module (error_rows_extra), and there no row presents GL as idle.
  s=fixture(2000);s.native_failover.state='BLOCKED';s.native_failover.blockers=['VENDOR-WORKER-BUSY'];l=light(s);assert.notEqual(c.autoSignal(l),'red');assert(c.autoRuns(l));assert(!/^VENDOR-BUSY-/.test(String(l.code)));
  const busyRows=fs.readFileSync('router/error_rows_extra.inc.js','utf8');
  for(const code of ['VENDOR-BUSY-RTP-LOCK-DEAD','VENDOR-BUSY-RTP-LOCK-LIVE','VENDOR-BUSY-TUNNEL-SWITCH','VENDOR-BUSY-WORKERS','VENDOR-BUSY-UNIDENTIFIED']){
    s=fixture(2000);s.native_failover.state='BLOCKED';s.native_failover.blockers=['VENDOR-WORKER-BUSY'];s.native_failover.reason=code;s.native_failover.busy_seconds=125;l=light(s);
    assert.equal(c.autoSignal(l),'yellow',code);assert.equal(l.code,code);assert(c.autoRuns(l),code);assert(l.hint.includes(code),code+' is named');
    assert(!/Try again|Повторите/.test(l.hint),code);
    const row=busyRows.split('\n').filter(line=>line.includes("['"+code+"','switch'"));assert.equal(row.length,1,code+' has its row');assert(!/idle\.'|простаивает\.'/.test(row[0])||/does not prove|не доказывает/.test(row[0]),code);
  }
  assert(/not a proof/.test(busyRows.split('\n').filter(line=>line.includes("['VENDOR-BUSY-RTP-LOCK-DEAD','switch'"))[0]),'a dead holder is not presented as finished work');
  assert(/does not prove/.test(busyRows.split('\n').filter(line=>line.includes("['VENDOR-BUSY-UNIDENTIFIED','switch'"))[0]),'a missing file is not presented as a quiet router');
  // Another reason on a BLOCKED pair keeps today's meaning: the code comes with busy_seconds only.
  s=fixture(2000);s.native_failover.state='BLOCKED';s.native_failover.blockers=['ROLLBACK-GIVEN-UP'];s.native_failover.reason='KERNEL-POLICY-UNVERIFIED';l=light(s);assert.equal(l.code,'ROLLBACK-GIVEN-UP','a reason never replaces the blocker');
  s=fixture(2000);s.native_failover.state='BLOCKED';s.native_failover.blockers=['VENDOR-WORKER-BUSY'];s.native_failover.reason='PAIR-WAITING-PROBES';l=light(s);assert.notEqual(c.autoSignal(l),'red');
  // Data late while the owner's Auto runs: yellow "refreshing", never "Auto off".
  now=2200;s=fixture(2000);l=light(s);assert.equal(c.autoSignal(l),'yellow','late data is yellow while Auto runs (owner 01.11.2026: never better than monitoring)');assert(c.autoRuns(l));
  // A routine scheduled check is due: still green (the countdown shows it), not yellow.
  now=2012;s=fixture(2000);s.server_time=2012;s.channel_path.checked_at=s.channel_path.time=2010;s.probe_policy={effective_interval:10};l=light(s);assert.equal(c.autoSignal(l),'green');
  // The router itself reports the route unverified (not just aged): never held, yellow while Auto runs.
  now=2000;s=fixture(2000);s.channel_path.checked_at=null;s.channel_path.time=null;s.channel_path.kernel_policy_verified=false;
  l=light(s);assert.equal(c.autoSignal(l),'yellow','an unverified route is yellow; the text names the check');
  now=2000;
  // A switch in progress is yellow, never red.
  s=fixture(2000);s.native_failover.state='APPLYING';s.channel_path.transitioning=true;l=light(s);assert.equal(c.autoSignal(l),'yellow');
  // A completed failed check of the selected channel is red at once.
  s=fixture(2000);s.profiles[0].code='VPN-003';s.profiles[0].https_success=0;l=light(s);assert.equal(c.autoSignal(l),'red');assert(!c.autoRuns(l));
  // No connection to the router program: red.
  s=fixture(2000);s.rpc_error='RPC';l=light(s);assert.equal(c.autoSignal(l),'yellow','one missed answer is a yellow retry, not green and not an error (owner 01.11.2026)');assert(c.autoRuns(l));
  now=2000+c.AUTO_RPC_GRACE+1;l=light(s);assert.equal(c.autoSignal(l),'red','no answer for longer than the grace is an error');now=2000;
  l=light(fixture(2000));
  // Auto off by the owner: a quiet dark light, not an error.
  s=fixture(2000);s.auto_control={requested:'off',pair_phase:'STOPPED',requested_at:900};s.native_failover.state='STOPPED';l=light(s);assert.equal(c.autoSignal(l),'off');
  // Response metric: ping by default is one model for every place (number, unit, target); websites stay separate.
  s=fixture(2000);s.response_metric='icmp-1.1.1.1';s.profiles[0].ping={metric:'icmp-rtt-ms',target:'1.1.1.1',state:'ok',code:null,time:1995,rtt_ms:53.2,valid_for:60,interface:'wgclient1'};
  let m=c.channelPingModel(s.profiles[0],s,now);assert.equal(m.state,'ok');assert.equal(m.rtt_ms,53.2);assert(m.text.includes('1.1.1.1'));
  s.profiles[0].ping.target='8.8.8.8';assert.notEqual(c.channelPingModel(s.profiles[0],s,now).state,'ok','a ping to another target is not the chosen measurement');
  s.profiles[0].ping.target='1.1.1.1';s.profiles[0].ping.time=1000;assert.equal(c.channelPingModel(s.profiles[0],s,now).state,'stale');
  s.response_metric='websites';assert.notEqual(c.channelPingModel(s.profiles[0],s,now).kind,'ping');
  // Sidebar Auto lamp = button colour: green while Auto runs (also during a yellow check), red on failure, grey when off.
  {const host=new N('div');c.document={querySelector:()=>null};c.identityModel=()=>({});c.manualConfirmedPath=()=>({});c.manualChannelTone=()=>({color:'grey',text:''});c.dataCause=()=>({text:''});
   for(const [mut,knob] of [[s2=>{},'hv-lamp-on'],[s2=>{s2.native_failover.state='APPLYING';s2.channel_path.transitioning=true;},'hv-lamp-switching'],[s2=>{s2.profiles[0].code='VPN-003';s2.profiles[0].https_success=0;},'hv-lamp-off'],[s2=>{s2.auto_control={requested:'off',pair_phase:'STOPPED',requested_at:900};s2.native_failover.state='STOPPED';},'hv-lamp-dark']]){
     now=2000;const st=fixture(2000);mut(st);const h=new N('div');c.fillSideStatus(h,st,inventory);const k=h.all().find(n=>/hv-auto-pill-knob/.test(n.attrs.class||''));assert(k.attrs.class.includes(knob),'sidebar lamp '+knob);}}
  // The housing has three lamps and lights exactly the signal.
  for(const [state,signal] of [['OBSERVING','green'],['APPLYING','yellow']]){now=2000;
    s=fixture(2000);s.native_failover.state=state;s.channel_path.transitioning=state==='APPLYING';l=light(s);
    const lamps=c.renderAutoLight(l,'X').all().filter(n=>/\bhv-lamp-(red|yellow|green)\b/.test(n.attrs.class||''));
    assert.equal(lamps.length,3);assert.deepStrictEqual(lamps.filter(n=>/hv-lamp-lit/.test(n.attrs.class)).map(n=>n.attrs.class.match(/hv-lamp-(red|yellow|green)/)[1]),[signal]);
  }
}
console.log('PASS: three-signal Auto light: green works, yellow waits/checks, red only critical, dark when off (EN/RU)');
