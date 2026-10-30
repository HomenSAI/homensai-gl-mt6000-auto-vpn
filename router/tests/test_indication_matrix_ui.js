// Generated indication matrix: every plausible combination of Auto intent, controller phase/state, carrier channel,
// manual hold, channel health and transport freshness is rendered through the real page code. Every surface that shows
// a channel lamp or the Auto lamp must show the same thing (owner rule: one source, channelLampTone / autoLampColor).
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N {
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(x=>x!=null&&x!==false);this.disabled=this.attrs.disabled!=null;this.style={setProperty(){}};
    this.classList={contains:k=>String(this.attrs.class||'').split(' ').includes(k),toggle:(k,on)=>{const words=String(this.attrs.class||'').split(' ').filter(x=>x&&x!==k);if(on)words.push(k);this.attrs.class=words.join(' ');},add:k=>this.classList.toggle(k,true)};}
  setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}removeAttribute(k){delete this.attrs[k];}appendChild(v){this.children.push(v);return v;}get firstChild(){return this.children[0];}removeChild(v){this.children.splice(this.children.indexOf(v),1);}
  all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}text(){return (this.textContent||'')+' '+this.children.map(x=>x instanceof N?x.text():String(x)).join(' ');}
  querySelector(selector){return this.all().find(n=>selector[0]==='.'&&n.classList.contains(selector.slice(1)))||null;}
}
const NOW=10000;let now=NOW;
const c={console,Promise,Math,JSON,Object,Array,Number,String,E:(...args)=>new N(...args),bi:en=>en,locale:'en',
  Date:class extends Date{static now(){return now*1000;}},performance:{now:()=>now*1000},
  window:{localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},location:{reload(){}}},
  setInterval:()=>1,clearInterval(){},setTimeout:()=>1,document:{querySelector:()=>null,body:{contains:()=>true}},
  ui:{addNotification(){}},rpc:{declare:()=>()=>new Promise(()=>{})},errorCodeLink:code=>new N('code',{},code),
  safeCode:code=>typeof code==='string'&&/^[A-Z][A-Z0-9-]{1,95}$/.test(code),countryLabel:()=>'Country',countryName:()=>'',customName:()=>'',
  protocolLabel:p=>p&&p.protocol==='wireguard'?'WireGuard':'OpenVPN',identityModel:()=>({agent:'test'}),journalSourceLabel:()=>'source',ownGet:(m,k)=>Object.prototype.hasOwnProperty.call(m,k)?m[k]:undefined};
vm.createContext(c);
for(const name of ['ui_logic','auto_panel','manual_panel','sidebar_status','vendor_diagnostics','channel_guidance','design_views','live_terminal'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
c.journalSourceLabel=()=>'source';c.statusNow=()=>now;c.routerWall=()=>now;
const inventory={settings:{enabled:true,setup_complete:true,plan_source:'a',plan_target:'b',pair_auto_mode:'router-probed-ipv4'}};

// ---- matrix dimensions ----
const REQUESTED=['on','off'],PHASES=['STARTING','RUNNING','STOPPED'];
const STATES=['OBSERVING','COMMITTED','APPLYING','WAIT-CLIENT','BLOCKED-TRANSIENT','BLOCKED-REAL','DEGRADED-ON-RESERVE','STOPPED'];
const CARRIERS=['primary','reserve','none'],HOLDS=['none','source','target'],HEALTH=['healthy','failed','inactive','unknown'];
const TRANSPORT=['fresh','rpc-new','rpc-long','stale-new','stale-long'];
// Returns a reason string for combinations the controller cannot publish, otherwise null.
function impossible(d){
  // The pair phase follows the owner's intent: Off is only STOPPED; On is never STOPPED (a refused start is FAILED, not part of this matrix).
  if(d.requested==='off'&&d.phase!=='STOPPED')return 'off-intent-with-live-phase';
  if(d.requested==='on'&&d.phase==='STOPPED')return 'on-intent-stopped-phase';
  // A stopped pair restores the original route and leaves the controller STOPPED.
  if(d.phase==='STOPPED'&&d.state!=='STOPPED')return 'stopped-pair-live-controller';
  if(d.phase!=='STOPPED'&&d.state==='STOPPED'&&d.phase!=='STARTING')return 'running-pair-stopped-controller';
  // While starting the controller has not committed to the reserve yet.
  if(d.phase==='STARTING'&&['COMMITTED','DEGRADED-ON-RESERVE','WAIT-CLIENT'].includes(d.state))return 'starting-with-reserve-commit';
  // Carrier follows the controller state: OBSERVING/STOPPED watch the primary, COMMITTED/DEGRADED hold the reserve.
  if(['OBSERVING','STOPPED'].includes(d.state)&&d.carrier==='reserve')return 'primary-state-reserve-carrier';
  if(['COMMITTED','DEGRADED-ON-RESERVE'].includes(d.state)&&d.carrier==='primary')return 'reserve-state-primary-carrier';
  // A manual hold exists only inside a running pair and holds the channel that carries traffic.
  if(d.hold!=='none'&&d.phase!=='RUNNING')return 'hold-outside-running-pair';
  if(d.hold==='source'&&d.carrier==='reserve'||d.hold==='target'&&d.carrier==='primary')return 'hold-on-other-channel';
  return null;
}
function profile(id,i,health,t){
  const p={id,interface:i?'ovpnclient1':'wgclient1',protocol:i?'openvpn':'wireguard',time:t,dns_ok:true,https_success:2,code:null};
  if(health==='failed'){p.code='DNS-001';p.dns_ok=false;p.https_success=0;}
  if(health==='inactive')p.interface=null;
  if(health==='unknown')p.time=t-400;
  return p;
}
function buildStatus(d){
  const t=d.transport==='fresh'?NOW:d.transport==='rpc-new'?NOW-10:d.transport==='rpc-long'?NOW-100:NOW-130;
  const state=d.state.startsWith('BLOCKED')?'BLOCKED':d.state;
  const blockers=d.state==='BLOCKED-TRANSIENT'?['OBSERVATION-STALE']:d.state==='BLOCKED-REAL'?['ROLLBACK-GIVEN-UP']:[];
  const moving=['APPLYING','WAIT-CLIENT'].includes(state);
  const s={time:t,server_time:NOW,profiles:[profile('a',0,d.primary,t),profile('b',1,d.reserve,t)],
    native_failover:{time:t,state,mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,kernel_policy_verified:true,source:'a',target:'b',blockers,started:moving?t-5:undefined},
    auto_control:{requested:d.requested,requested_at:t-50,pair_phase:d.phase,control_revision:'b'.repeat(32)},
    channel_path:{time:t,checked_at:t,valid_for:15,mode:'continuous-pair',selection_proof:'fw3-kernel-marking',kernel_policy_verified:true,confirmed:d.carrier!=='none',
      active_profile_id:d.carrier==='primary'?'a':d.carrier==='reserve'?'b':null,source_profile_id:'a',target_profile_id:'b',transitioning:moving},
    manual_switch_control:{time:t,mode:'continuous-pair',control_revision:'c'.repeat(32),available:true,reserve:{allowed:true,blockers:[]},primary:{allowed:true,blockers:[]},resume:{allowed:true,blockers:[]}}};
  if(d.state==='STOPPED')s.native_failover.original_restored=true;
  if(d.hold!=='none')s.manual_switch_control.hold=d.hold;
  if(d.transport.startsWith('rpc'))s.rpc_error='RPC-UNAVAILABLE';
  return s;
}
function resetGlobals(d){
  for(const [k,v] of Object.entries({UI_PATH_MEMORY:null,UI_RPC_LOST_SINCE:null,UI_DATA_LATE_SINCE:null,UI_TRANSIENT_SINCE:null,UI_AUTO_LAST_ON:null,
    autoCommandPending:null,autoCommandUnconfirmed:null,autoObservedOperation:null,AUTO_COUNTDOWN:null,autoRequestBusy:false,autoStopBusy:false,autoStartPending:false,
    MANUAL_SWITCH_OPERATION:null,MANUAL_SWITCH_PENDING:false,MANUAL_SWITCH_DIRECTION:null,MANUAL_SWITCH_FEEDBACK:null,UI_TIMER_NODES:[]}))c[k]=v;
  c.MANUAL_RESULT_SEEN.clear();
  // The page has been watching: a lost answer / late data started 95 s ago for the "long" variants.
  if(d.transport==='rpc-long')c.UI_RPC_LOST_SINCE=NOW-95;
  if(d.transport==='stale-long')c.UI_DATA_LATE_SINCE=NOW-95;
  if(d.transport!=='fresh'&&d.requested==='on'&&d.phase!=='STOPPED')c.UI_AUTO_LAST_ON=NOW-100;
}
const knob=n=>(String(n.attrs.class).match(/hv-lamp-(\w+)/)||[])[1];
const SIDEBAR_CHANNEL={on:'green',switching:'yellow',unknown:'grey',off:'red'},SIDEBAR_AUTO={on:'green',switching:'yellow',off:'red',dark:'grey',unknown:'red?'};
const OFFER=/you can switch/;
function surfaces(s){
  const out={channel:{source:{},target:{}},auto:{},text:{source:{},target:{}},misc:{}};
  // Sidebar
  const side=new N('div');c.fillSideStatus(side,s,inventory);
  const autoKnob=side.all().find(n=>/hv-auto-pill-knob/.test(n.attrs.class||''));out.auto.sidebar=SIDEBAR_AUTO[knob(autoKnob)]||knob(autoKnob);
  const channelLamps=side.all().find(n=>n.attrs.class==='hv-side-channel-lamps').children;
  ['source','target'].forEach((role,i)=>{const lamp=channelLamps[i],k=lamp.all().find(n=>/hv-auto-pill-knob/.test(n.attrs.class||''));out.channel[role].sidebar=SIDEBAR_CHANNEL[knob(k)]||knob(k);out.text[role].sidebar=lamp.text();});
  // Manual switch cards
  const manual=c.renderManualSwitch(s,inventory);out.misc.resume=manual.all().some(n=>n.attrs['data-manual-direction']==='resume');
  [['source','primary'],['target','reserve']].forEach(([role,dir])=>{const card=manual.all().find(n=>n.attrs['data-manual-direction']===dir);
    out.channel[role].manual=(String(card.attrs.class).match(/hv-manual-(green|yellow|grey|red|switching)\b/)||[])[1];out.text[role].manual=card.text();out.misc[role+'Selected']=card.attrs['data-selected']==='true';out.misc[role+'Enabled']=!card.disabled;});
  // Channel cards (channelDisplayUse via the card header: lamp + badge)
  for(const p of s.profiles){const role=p.id==='a'?'source':'target',head=c.renderChannelHeader(p,s,inventory);
    const lamp=head.all().find(n=>/hv-check-lamp/.test(n.attrs.class||'')),badge=head.all().find(n=>/hv-route-badge/.test(n.attrs.class||''));
    out.channel[role].cardLamp=(lamp.attrs.class.match(/hv-check-(\w+)$/)||[])[1];out.channel[role].badge=(badge.attrs.class.match(/hv-route-(green|yellow|grey|red)\b/)||[])[1];out.text[role].badge=badge.text();}
  // Live journal pinned lines
  const T=c.LIVE_TERMINAL;T.pinned=new N('div');T.clock=new N('time');T.followButton=new N('button');T.frame=s;T.inventory=inventory;c.terminalPinned(now);
  for(const line of T.pinned.children){const name=line.children[1].text().trim(),kind=(line.children[0].attrs.class.match(/hv-check-(green|yellow|red|grey)\b/)||[])[1];
    if(name==='Auto VPN')out.auto.journal=kind;else if(name==='Primary channel'){out.channel.source.journal=kind;out.text.source.journal=line.text();}else if(name==='Reserve channel'){out.channel.target.journal=kind;out.text.target.journal=line.text();}}
  // Auto card: button, state text, traffic light, path nodes
  const auto=c.renderAutoControl(s,inventory);
  const button=auto.all().find(n=>/(^| )hv-auto-power( |$)/.test(n.attrs.class||''));out.auto.button=/hv-auto-lit-on/.test(button.attrs.class)?'green':'not-green';
  const stateText=auto.all().find(n=>/hv-auto-state\b/.test(n.attrs.class||'')).text();out.auto.stateText=/Auto works/.test(stateText)?'green':/Auto is off/.test(stateText)?'grey':'not-green';
  out.auto.signal=auto.all().find(n=>n.attrs['data-signal']).attrs['data-signal'];
  for(const node of auto.all().filter(n=>n.attrs['data-path-node']))out.channel[node.attrs['data-path-node']].autoCard=node.attrs['data-node-tone'];
  out.misc.resume=out.misc.resume||auto.all().some(n=>n.attrs['data-manual-direction']==='resume');
  // The rule functions themselves
  const light=c.autoLightModel(s,inventory,now);out.light=light;out.auto.lampColor=c.autoLampColor(light,false);
  for(const role of ['source','target']){const tone=c.channelLampTone(s,inventory,role,now);out.channel[role].rule=tone.color;out.misc[role+'Carrier']=tone.carrier;}
  return out;
}
// ---- run ----
const failures=new Map();let run=0,skipped=0;const skipReasons={};
function fail(kind,d,detail){const key=kind;if(!failures.has(key))failures.set(key,{count:0,example:null});const f=failures.get(key);f.count++;if(!f.example)f.example={d,detail};}
const byKey=new Map(),seen={channel:{},auto:{},signal:{},offers:0};const tally=(m,k)=>m[k]=(m[k]||0)+1;
for(const requested of REQUESTED)for(const phase of PHASES)for(const state of STATES)for(const carrier of CARRIERS)for(const hold of HOLDS)for(const primary of HEALTH)for(const reserve of HEALTH)for(const transport of TRANSPORT){
  const d={requested,phase,state,carrier,hold,primary,reserve,transport},why=impossible(d);
  if(why){skipped++;skipReasons[why]=(skipReasons[why]||0)+1;continue;}
  run++;now=NOW;resetGlobals(d);const s=buildStatus(d);let o;
  try{o=surfaces(s);}catch(e){fail('render-exception '+e.message.split('\n')[0],d,e.stack.split('\n').slice(0,3).join(' | '));continue;}
  byKey.set(JSON.stringify(d),o);tally(seen.auto,o.auto.lampColor);tally(seen.signal,o.auto.signal);for(const role of ['source','target']){tally(seen.channel,o.channel[role].rule);if(OFFER.test(o.text[role].manual))seen.offers++;}
  const fresh=transport==='fresh',moving=['APPLYING','WAIT-CLIENT'].includes(state),health={source:primary,target:reserve};
  const carrierRole=carrier==='primary'?'source':carrier==='reserve'?'target':null;
  // (a) channel lamps agree per role across every surface (the manual card's blinking "switching" destination is a pending grey)
  for(const role of ['source','target']){
    const v=o.channel[role],norm=Object.fromEntries(Object.entries(v).map(([k,x])=>[k,k==='manual'&&x==='switching'?'yellow':x]));
    if(new Set(Object.values(norm)).size!==1)fail('channel-disagree '+role+' '+JSON.stringify(v),d,v);
  }
  // (b) Auto surfaces agree: the lamp (button, state text, sidebar, journal) is one colour; the traffic light refines it.
  const a=o.auto,lamp=a.lampColor;
  if(a.journal!==lamp)fail('auto journal '+a.journal+' vs lamp '+lamp,d,a);
  if(a.sidebar!==lamp)fail('auto sidebar '+a.sidebar+' vs lamp '+lamp,d,a);
  if((a.button==='green')!==(lamp==='green'))fail('auto button '+a.button+' vs lamp '+lamp,d,a);
  if((a.stateText==='green')!==(lamp==='green')||(a.stateText==='grey')!==(lamp==='grey'))fail('auto state text '+a.stateText+' vs lamp '+lamp,d,a);
  const okSignal={green:['green','yellow'],yellow:['yellow'],red:['red'],grey:['off']}[lamp]||[];
  if(!okSignal.includes(a.signal))fail('auto traffic light '+a.signal+' vs lamp '+lamp,d,a);
  // Owner Auto rules
  if(fresh&&requested==='off'&&lamp!=='grey')fail('owner-off-not-dark '+lamp,d,o.light);
  if(fresh&&phase==='RUNNING'&&['OBSERVING','COMMITTED'].includes(state)&&carrierRole&&health[carrierRole]==='healthy'&&lamp!=='green')fail('running-healthy-carrier-not-green '+lamp+' '+o.light.key,d,o.light);
  if(fresh&&phase==='RUNNING'&&['OBSERVING','COMMITTED','DEGRADED-ON-RESERVE'].includes(state)&&carrierRole&&['failed','inactive'].includes(health[carrierRole])&&lamp!=='red')fail('failed-carrier-not-red '+lamp,d,o.light);
  if(fresh&&requested==='on'&&state==='BLOCKED-REAL'&&lamp!=='red')fail('controller-alarm-not-red '+lamp,d,o.light);
  if(fresh&&phase==='RUNNING'&&state==='BLOCKED-TRANSIENT'&&lamp!=='green')fail('transient-blocker-not-green '+lamp,d,o.light);
  if(fresh&&phase==='RUNNING'&&moving&&(lamp!=='green'||a.signal!=='yellow'))fail('running-switch-not-green-lamp-yellow-light '+lamp+'/'+a.signal,d,o.light);
  if(fresh&&phase==='STARTING'&&state!=='BLOCKED-REAL'&&a.signal!=='yellow')fail('starting-not-yellow '+a.signal+' '+o.light.key,d,o.light);
  // A controller alarm in the last answer stays red while the next answer is missing; everything else waits out the 90 s grace.
  if(['rpc-new','stale-new'].includes(transport)&&requested==='on'&&state!=='BLOCKED-REAL'&&lamp==='red')fail('short-loss-red ('+transport+')',d,o.light);
  if(['rpc-long','stale-long'].includes(transport)&&requested==='on'&&lamp!=='red')fail('long-loss-not-red '+lamp+' ('+transport+')',d,o.light);
  if(['rpc-new','stale-new'].includes(transport)&&requested==='off'&&lamp==='red')fail('owner-off-short-loss-red ('+transport+')',d,o.light);
  if(lamp==='red'){
    // DEGRADED-ON-RESERVE is the controller's own degraded alarm; it stays red until Auto confirms recovery (owner decision pending).
    const proven=state==='BLOCKED-REAL'||fresh&&(state==='DEGRADED-ON-RESERVE'||carrierRole&&['failed','inactive'].includes(health[carrierRole]))||['rpc-long','stale-long'].includes(transport);
    if(!proven)fail('red-without-proven-failure '+o.light.key+' '+o.light.title,d,o.light);
  }
  // (c) channel colour rules (judged on the single rule; (a) already ties every surface to it)
  const pending=o.light.key==='switching'&&!moving||phase==='STARTING';
  for(const role of ['source','target']){
    const color=o.channel[role].rule,h=health[role],isCarrier=carrierRole===role;
    if(!fresh&&color!=='grey')fail('no-fresh-data-not-grey '+color,d,role);
    if(fresh&&['failed','inactive'].includes(h)&&color!=='red')fail('failed-not-red ('+(moving?'switching':pending?'pending':'idle')+') '+color,d,role);
    if(fresh&&!moving&&!pending&&isCarrier&&h==='healthy'&&c.autoRuns(o.light)&&color!=='green')fail('healthy-carrier-not-green '+color,d,role);
    if(fresh&&!moving&&!pending&&carrierRole&&!isCarrier&&h==='healthy'&&c.autoRuns(o.light)){
      if(color!=='yellow')fail('healthy-standby-not-yellow '+color,d,role);
      else if(!OFFER.test(o.text[role].manual))fail('yellow-standby-without-switch-offer',d,o.text[role].manual);
    }
    for(const [surface,text] of Object.entries(o.text[role]))if(OFFER.test(text)&&(color!=='yellow'||isCarrier&&!moving))fail('switch-offer-on-non-yellow-or-carrier '+surface+' '+color,d,role);
    if(fresh&&!moving&&!pending&&isCarrier&&OFFER.test(o.text[role].manual))fail('carrier-offers-switch-to-itself',d,role);
  }
  // (e) no Resume Auto command
  if(o.misc.resume)fail('resume-auto-button-present',d,null);
}
// (d) a manual hold never changes the Auto lamp by itself
let holdPairs=0;
for(const [key,o] of byKey){const d=JSON.parse(key);if(d.hold==='none')continue;const base=byKey.get(JSON.stringify({...d,hold:'none'}));if(!base)continue;holdPairs++;
  if(o.auto.lampColor!==base.auto.lampColor||o.auto.signal!==base.auto.signal)fail('hold-changes-auto '+base.auto.lampColor+'->'+o.auto.lampColor,d,null);
  if(o.auto.lampColor!=='green'&&d.transport==='fresh'&&base.auto.lampColor==='green')fail('hold-makes-auto-non-green',d,null);}
console.log('Indication matrix: '+run+' combinations run, '+skipped+' skipped as impossible, '+holdPairs+' hold/no-hold pairs compared');
console.log('Coverage: channel lamps '+JSON.stringify(seen.channel)+', Auto lamp '+JSON.stringify(seen.auto)+', traffic light '+JSON.stringify(seen.signal)+', switch offers '+seen.offers);
for(const k of ['green','yellow','grey','red'])assert(seen.channel[k]>0&&seen.auto[k]>0,'matrix exercises '+k);assert(seen.offers>0);
console.log('Skipped: '+Object.entries(skipReasons).map(([k,v])=>k+'='+v).join(', '));
if(failures.size){
  for(const [kind,f] of failures)console.log('FAIL x'+f.count+': '+kind+'\n   e.g. '+JSON.stringify(f.example.d)+' -> '+JSON.stringify(f.example.detail&&f.example.detail.title?{key:f.example.detail.key,title:f.example.detail.title,running:f.example.detail.running}:f.example.detail).slice(0,300));
  console.log('Failures: '+[...failures.values()].reduce((n,f)=>n+f.count,0)+' in '+failures.size+' groups');process.exitCode=1;
}else console.log('PASS: every channel and Auto surface agrees across the whole matrix; owner colour rules hold; no Resume Auto command');
