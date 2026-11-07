// Owner rule 07.11.2026 (TWO indicators, replaces the single program lamp of the same night).
// MAIN LIGHT = the internet only: green = internet works (primary or reserve, Auto on or off); yellow = a channel transition
// (switching, checking, Auto handling a failed channel for up to 60 s); red = no internet proven (both channels failed, router WAN
// check, carrying channel failed with Auto off, or still failed 60 s after Auto should act). AUTO INDICATOR: green = Auto on,
// red = manual mode, red + warning = Auto stuck (recovery needed), yellow = starting/paused. Grey + "?" = no fresh data on both.
// The Auto switch track (data-sig) agrees with the AUTO INDICATOR.
// The shipped page runs in a vm with a stub root (no browser): colours are checked as classes/attributes, not pixels.
'use strict';
const assert=require('assert');
const {load,CSS}=require('./approved_page');
const fs=require('fs');

function el(dataset){const attrs={},cls=new Set();return {dataset:dataset||{},attrs,innerHTML:'',className:'',cls,
  setAttribute(k,v){attrs[k]=String(v);},removeAttribute(k){delete attrs[k];},getAttribute(k){return k in attrs?attrs[k]:null;},
  classList:{toggle(k,on){if(on)cls.add(k);else cls.delete(k);},has:k=>cls.has(k)}};}
function paint(p){
  const lamp=el({lamp:'ov'}),alamp=el({lamp:'auto'}),title=el({b:'ov.title'}),atext=el({b:'auto.text'}),asub=el({b:'auto.sub'}),sw=el(),rtag=el({b:'r.tag'});
  // the header pair (owner 07.11.2026): "Internet" and "Auto" lamps with labels, on every page
  const hov=el({lamp:'ov',hl:p.T.headLampsHTML().indexOf('Интернет')>=0?'Интернет':'Internet'}),hauto=el({lamp:'auto',hl:'Auto'});
  const nodes={'[data-lamp]':[lamp,alamp,hov,hauto],'[data-b]':[title,atext,asub,rtag],'[data-auto-switch]':[sw]};
  p.T.HV.root={querySelectorAll:sel=>nodes[sel]||[],contains:()=>true};p.T.paintLive();p.T.HV.root=null;
  const lit=x=>['g','y','r','n'].filter(k=>x.cls.has(k));
  return {lamp:lit(lamp),alamp:lit(alamp),aria:lamp.attrs['aria-label'],aaria:alamp.attrs['aria-label'],title:title.innerHTML,atext:atext.innerHTML,asub:asub.innerHTML,track:sw.attrs['data-sig'],rtag:rtag.innerHTML,
    hov:lit(hov),hauto:lit(hauto),hovAria:hov.attrs['aria-label'],hautoAria:hauto.attrs['aria-label'],hovTip:hov.attrs.title,hautoTip:hauto.attrs.title};
}
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
const bad=r=>{r.code='VPN-003';r.https_success=0;r.dns_ok=false;if(r.ping)r.ping.state='fail';};
const S={
  'Auto OFF':{scn:'off'},
  'STARTING':{scn:'ok',mutate:({status})=>{status.auto_control.pair_phase='STARTING';status.auto_control.requested_at=status.time+1;}},
  'RUNNING on primary':{scn:'ok'},
  'RUNNING on reserve':{scn:'reserve'},
  'APPLYING':{scn:'ok',mutate:({status})=>{const n=status.native_failover;n.state='APPLYING';n.started=n.time;n.deadline=n.time+60;}},
  'HELD (pair recovery required)':{scn:'ok',mutate:({status})=>{status.auto_control.pair_phase='HELD';const n=status.native_failover;n.state='BLOCKED';n.blockers=['PAIR-RECOVERY-REQUIRED'];}},
  'BLOCKED':{scn:'ok',mutate:({status})=>{const n=status.native_failover;n.state='BLOCKED';n.blockers=['KERNEL-POLICY-MISMATCH'];}},
  'speed pause':{scn:'ok',mutate:({status})=>{status.speed_pause={active:true,phase:'PAUSED',auto_paused:true,monitor_paused:true};}},
  'stale controller':{scn:'stale'},
  'both channels proven failed':{scn:'ok',mutate:({status})=>{status.profiles.forEach(bad);}},
  'one failed + other stale':{scn:'ok',mutate:({status})=>{bad(status.profiles[0]);status.profiles[1].time-=300;}},
  'RPC failed':{scn:'ok',mutate:({status})=>{status.rpc_error='timeout';}},
  'router WAN check: no internet':{scn:'ok',mutate:({status})=>{status.wan_diagnosis={time:status.time,enabled:true,verdict:'WAN',code:'WAN-DOWN',confidence:930};}},
  'current failed, Auto off':{scn:'off',mutate:({status})=>{bad(status.profiles[0]);}},
  'current failed, Auto on, other works':{scn:'ok',mutate:({status})=>{bad(status.profiles[0]);}}
};
// state -> [main lamp, RU words, EN words, main icon, Auto lamp, RU Auto words, EN Auto words, Auto icon]
const ON=['g',/^Auto включён$/,/^Auto is on$/,''],MANUAL=['r',/^Ручной режим \(Auto выключен\)$/,/^Manual mode \(Auto is off\)$/,'○'],
  STUCK=['r',/^Auto остановлен: нужно восстановление$/,/^Auto stopped: recovery needed$/,'⚠'],ANODATA=['n',/^Auto: нет свежих данных$/,/^Auto: no fresh data$/,'?'],
  NET=['g',/^Интернет работает$/,/^Internet works$/,''],NODATA=['n',/Нет свежих данных/,/No fresh data/,'?'];
const EXPECT={
  'Auto OFF':[...NET,...MANUAL],
  'STARTING':[...NET,'y',/^Auto запускается$/,/^Auto is starting$/,''],
  'RUNNING on primary':[...NET,...ON],
  'RUNNING on reserve':['g',/^Работает через резерв$/,/^Works via the reserve$/,'',...ON],
  'APPLYING':['y',/^Переключение…$/,/^Switching…$/,'',...ON],
  'HELD (pair recovery required)':[...NET,...STUCK],
  'BLOCKED':[...NET,...STUCK],
  'speed pause':[...NET,'y',/^Auto на паузе: тест скорости$/,/^Auto paused: speed test$/,''],
  'stale controller':[...NODATA,...ANODATA],
  'both channels proven failed':['r',/^Нет интернета через VPN$/,/^No internet through the VPN$/,'✕',...ON],
  'one failed + other stale':['y',/^Текущий канал не отвечает$/,/^Current channel is not responding$/,'',...ON],
  'RPC failed':[...NODATA,...ANODATA],
  'router WAN check: no internet':['r',/^Нет интернета$/,/^No internet$/,'✕',...ON],
  'current failed, Auto off':['r',/^Текущий канал не отвечает$/,/^Current channel is not responding$/,'✕',...MANUAL],
  'current failed, Auto on, other works':['y',/^Текущий канал не отвечает$/,/^Current channel is not responding$/,'',...ON]
};
const failures=[],rows=[];
for(const name of Object.keys(S)){
  try{
    const e=EXPECT[name];
    for(const lang of ['ru','en']){
      const p=load(Object.assign({lang},S[name]));p.T.snap();
      const o=p.T.overall(),ai=p.T.autoIndicator(),v=paint(p),ru=lang==='ru';
      assert.equal(o.lamp,e[0],name+'/'+lang+': main lamp '+o.lamp+' title '+o.title+' :: '+o.sub);
      assert(e[ru?1:2].test(o.title),name+'/'+lang+': main words "'+o.title+'"');
      assert.equal(o.icon,e[3],name+'/'+lang+': main icon');
      assert.deepEqual(v.lamp,[e[0]],name+'/'+lang+': the painted main lamp class');
      assert(v.aria.indexOf(o.title)>0,name+'/'+lang+': the main lamp says its meaning in words: '+v.aria);
      if(e[3])assert(v.title.indexOf('aria-hidden="true">'+e[3]+'</span>')>=0,name+'/'+lang+': icon painted beside the main words');
      assert.equal(ai.lamp,e[4],name+'/'+lang+': Auto lamp '+ai.lamp+' '+ai.text);
      assert(e[ru?5:6].test(ai.text),name+'/'+lang+': Auto words "'+ai.text+'"');
      assert.equal(ai.icon,e[7],name+'/'+lang+': Auto icon');
      assert.deepEqual(v.alamp,[e[4]],name+'/'+lang+': the painted Auto lamp class');
      assert.equal(v.track,e[4],name+'/'+lang+': the Auto switch track agrees with the AUTO indicator');
      assert(v.aaria.indexOf(ai.text)>0,name+'/'+lang+': the Auto lamp says its meaning in words: '+v.aaria);
      assert(v.atext.indexOf(esc(ai.text))>=0,name+'/'+lang+': the Auto switch shows the Auto words: '+v.atext);
      if(e[7])assert(v.atext.indexOf('aria-hidden="true">'+e[7]+'</span>')>=0,name+'/'+lang+': icon painted beside the Auto words');
      // header pair: the same colours as the big lamp and the Auto indicator, the label first in the accessible name, words in the tooltip
      assert.deepEqual(v.hov,[e[0]],name+'/'+lang+': header Internet lamp agrees with the main light');
      assert.deepEqual(v.hauto,[e[4]],name+'/'+lang+': header Auto lamp agrees with the Auto indicator and the track');
      assert(v.hovAria.indexOf(ru?'Интернет: ':'Internet: ')===0&&v.hovAria.indexOf(o.title)>0,name+'/'+lang+': header Internet lamp name: '+v.hovAria);
      assert(v.hautoAria.indexOf('Auto: ')===0&&v.hautoAria.indexOf(ai.text)>0,name+'/'+lang+': header Auto lamp name: '+v.hautoAria);
      assert(v.hovTip.indexOf(o.title)===0&&v.hautoTip.indexOf(ai.text)===0,name+'/'+lang+': header tooltips carry the words');
      if(ru)rows.push(name+' -> '+o.lamp+' '+(o.icon?o.icon+' ':'')+o.title+' -> '+ai.lamp+' '+(ai.icon?ai.icon+' ':'')+ai.text);
    }
  }catch(err){failures.push(name);console.log('FAIL: '+name+' :: '+String(err&&err.message||err).split(/\r?\n/)[0].slice(0,300));}
}
// the 60 s rule with a fake clock: current channel proven failed while Auto is on: yellow at first sight, red after 60 s if still
// failed, green once the channel works again, and a new failure starts a new window
for(const lang of ['ru','en'])try{
  const base=Date.now()/1000;let clock=base;
  const p=load({lang,scn:'ok',mutate:({status})=>{bad(status.profiles[0]);}});
  p.c.performance.now=()=>clock*1000;  // the page clock (statusNow) advances with this fake clock
  // the router keeps reporting the same evidence while the fake clock moves: every observation stays fresh
  const at=sec=>{clock=base+sec;const now=p.T.snap().now,last=p.status.time;
    const walk=x=>{if(!x||typeof x!=='object')return;for(const k of Object.keys(x)){if(['time','updated','checked_at','server_time'].includes(k)&&Number.isFinite(x[k]))x[k]+=now-last;else walk(x[k]);}};walk(p.status);p.T.snap();return p.T.overall();};
  let o=at(0);
  assert.equal(o.lamp,'y',lang+' t=0: yellow while Auto acts: '+o.title+' :: '+o.sub);
  o=at(59);assert.equal(o.lamp,'y',lang+' t=59: still yellow: '+o.title);
  o=at(61);
  assert.equal(o.lamp,'r',lang+' t=61: red after the 60 s window: '+o.title+' :: '+o.sub);
  assert((lang==='ru'?/^Нет интернета$/:/^No internet$/).test(o.title)&&o.icon==='✕',lang+' t=61: words and icon: '+o.title);
  {const ai=p.T.autoIndicator();assert.equal(ai.lamp,'g',lang+' t=61: the Auto indicator still says Auto is on: '+ai.text+' :: '+JSON.stringify(p.T.snap().light));}
  Object.assign(p.status.profiles[0],{code:null,https_success:3,dns_ok:true});if(p.status.profiles[0].ping)p.status.profiles[0].ping.state='ok';
  o=at(70);assert.equal(o.lamp,'g',lang+' t=70: the channel works again: green '+o.title);
  bad(p.status.profiles[0]);o=at(80);assert.equal(o.lamp,'y',lang+' t=80: a new failure starts a new window: '+o.title);
  console.log('PASS: 60 s yellow->red window with a fake clock ('+lang+')');
}catch(err){failures.push('60 s window '+lang);console.log('FAIL: 60 s window '+lang+' :: '+String(err.message).slice(0,300));}
// on the reserve the main light is green, the words say "via the reserve", no spare channel, and the reserve card keeps "Traffic here"
try{
  const p=load({scn:'reserve'});p.T.snap();const v=paint(p);
  assert(/Трафик здесь/.test(v.rtag),'the reserve card keeps its "Traffic here" chip: '+v.rtag);
  assert(/запаса нет/.test(p.T.overall().sub),'the words say redundancy is gone: '+p.T.overall().sub);
  assert.equal(p.T.reading('primary').lamp,'r','the primary card shows its own failure');
  console.log('PASS: reserve keeps its words and chip');
}catch(err){failures.push('reserve words');console.log('FAIL: reserve words :: '+String(err.message).slice(0,260));}
// track colours come from data-sig only (the AUTO indicator), and reduced motion still stops the blinking
try{
  const css=fs.readFileSync(CSS,'utf8');
  for(const [k,c] of [['g','ok'],['y','warn'],['r','bad'],['n','off']])assert(new RegExp('\\.hvx \\.aswitch\\[data-sig="'+k+'"\\] \\.trk\\{background:var\\(--'+c+'\\)\\}').test(css),'track rule '+k);
  assert(!/\.hvx \.aswitch\.busy \.trk\{background/.test(css),'"busy" alone does not repaint the track against the Auto indicator');
  assert(/prefers-reduced-motion:reduce\)\{\.hvx \.lamp,\.hvx \.lamp\.g,\.hvx \.lamp\.y,\.hvx \.lamp\.r\{animation:none!important\}\}/.test(css),'reduced motion still stops the blinking');
  console.log('PASS: stylesheet: track by the Auto indicator, reduced motion');
}catch(err){failures.push('css');console.log('FAIL: css :: '+String(err.message).slice(0,260));}
// speed test: the internet works during the test (main light green, the line names the test), Auto is paused (yellow)
for(const lang of ['ru','en'])try{
  const p=load(Object.assign({lang},S['speed pause']));p.T.snap();const o=p.T.overall();
  assert((lang==='ru'?/^Идёт тест скорости/:/^Speed test running/).test(o.sub),lang+': the main line names the speed test: '+o.sub);
  console.log('PASS: speed test keeps the internet light green with the test in words ('+lang+')');
}catch(err){failures.push('speed words '+lang);console.log('FAIL: speed words '+lang+' :: '+String(err.message).slice(0,300));}
// stuck Auto: one phrase, the exact reason (HELD / BLOCKED) and the code in the state line and the header tooltip
for(const [name,want] of [['HELD (pair recovery required)',['HELD','PAIR-RECOVERY-REQUIRED']],['BLOCKED',['BLOCKED','KERNEL-POLICY-MISMATCH']]])try{
  const p=load(S[name]);p.T.snap();const v=paint(p);
  for(const w of want){assert(v.asub.indexOf(w)>=0,name+': the state line carries '+w+': '+v.asub);assert(v.hautoTip.indexOf(w)>=0,name+': the header tooltip carries '+w+': '+v.hautoTip);}
  console.log('PASS: '+name+' reason and code in the line and the tooltip');
}catch(err){failures.push('reason '+name);console.log('FAIL: reason '+name+' :: '+String(err.message).slice(0,300));}
// both header lamps are rendered on Simple and Console (and in the wizard), inside the header, with RU/EN labels
for(const lang of ['ru','en'])for(const view of ['simple','console','wizard'])try{
  const p=load({lang,scn:'ok'});const T=p.T;let html='';
  T.HV.view=view==='wizard'?'simple':view;T.HV.wiz=view==='wizard';
  T.HV.root={set innerHTML(x){html=x;},get innerHTML(){return html;},className:'',setAttribute(){},removeAttribute(){},contains:()=>false,querySelector:()=>null,querySelectorAll:()=>[]};
  T.render();T.HV.root=null;
  const head=(html.match(/<header[\s\S]*?<\/header>/)||[''])[0],label=lang==='ru'?'Интернет':'Internet';
  assert(head.indexOf('data-lamp="ov" data-hl="'+label+'"')>=0,view+'/'+lang+': header Internet lamp');
  assert(head.indexOf('data-lamp="auto" data-hl="Auto"')>=0,view+'/'+lang+': header Auto lamp');
  assert(head.indexOf('<span class="hll" aria-hidden="true">'+label+'</span>')>=0&&head.indexOf('<span class="hll" aria-hidden="true">Auto</span>')>=0,view+'/'+lang+': visible labels');
  assert(!/<button[^>]*>[^<]*<i class="lamp"/.test(head),view+'/'+lang+': the header lamps are not controls');
  console.log('PASS: header lamps on '+view+' ('+lang+')');
}catch(err){failures.push('header '+view+' '+lang);console.log('FAIL: header '+view+' '+lang+' :: '+String(err.message).slice(0,300));}
// phone width: the header pair takes its own full-width grid row, so the header does not overflow
try{
  const css=fs.readFileSync(CSS,'utf8');
  assert(/@media \(max-width:760px\)\{[^@]*\.hvx \.hdr \.wrap\.hdr-in\{grid-template-areas:"hb badge" "lamps lamps" "nav tools"\}/.test(css),'phone grid row for the header lamps (Simple)');
  assert(/\.hvx\.v-console \.hdr \.wrap\.hdr-in,\.hvx\.v-wizard \.hdr \.wrap\.hdr-in\{grid-template-areas:"hb badge" "lamps lamps" "tools tools"\}/.test(css),'phone grid row for the header lamps (Console, wizard)');
  assert(/\.hvx \.hdr-in \.hlamps\{grid-area:lamps\}/.test(css),'the lamps sit in their row');
  const at=css.lastIndexOf('"hb badge" "lamps lamps" "nav tools"'),old=css.lastIndexOf('"hb badge" "nav tools"');assert(at>old,'the phone rule comes after the mockup rule, so it wins');
  console.log('PASS: header lamps get their own row on a phone');
}catch(err){failures.push('header css');console.log('FAIL: header css :: '+String(err.message).slice(0,300));}
console.log(rows.join('\n'));
if(failures.length){console.log('FAILED: '+failures.join(', '));process.exit(1);}
console.log('PASS: two-indicator table ('+Object.keys(S).length+' states x RU/EN)');
