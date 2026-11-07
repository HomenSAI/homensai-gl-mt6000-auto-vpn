// F-63..F-70, F-79 (review of 2026-11-06): lamps and buttons show the same state the same way everywhere. The shipped page is driven
// in a vm with a minimal fake root for the live bindings; no browser, so colours and focus are checked as classes and attributes,
// not as pixels.
'use strict';
const assert=require('assert');
const {load,strip}=require('./approved_page');
const flush=()=>new Promise(r=>setTimeout(r,25));
const count=(p,m)=>p.calls.filter(c=>c.method===m).length;

function el(dataset){const attrs={},cls=new Set();return {dataset:dataset||{},attrs,innerHTML:'',className:'',
  setAttribute(k,v){attrs[k]=String(v);},removeAttribute(k){delete attrs[k];},getAttribute(k){return k in attrs?attrs[k]:null;},
  classList:{toggle(k,on){if(on)cls.add(k);else cls.delete(k);},has:k=>cls.has(k)}};}
/* a root that serves the live bindings the test asks for; paintLive() then writes into them */
function paint(p,nodes){
  const root={querySelectorAll:sel=>nodes[sel]||[],contains:()=>true};
  p.T.HV.root=root;p.T.paintLive();p.T.HV.root=null;
}
const ok=({status})=>{};
const applying=({status})=>{const n=status.native_failover;n.state='APPLYING';n.started=n.time;n.deadline=n.time+60;};
const primaryBadReserveStale=({status})=>{status.profiles[0].code='VPN-003';status.profiles[0].https_success=0;status.profiles[1].time-=300;};
const primaryBadReserveChecking=({status})=>{status.profiles[0].code='VPN-003';status.profiles[0].https_success=0;status.profiles[1].code='CHECK-001';};
const bothBad=({status})=>{for(const r of status.profiles){r.code='VPN-003';r.https_success=0;}};
const speed=({status})=>{status.speed_pause={active:true,phase:'PAUSED',auto_paused:true,monitor_paused:true};};

const failures=[];
async function section(name,fn){
  try{await fn();console.log('PASS: '+name);}
  catch(e){failures.push(name);console.log('FAIL: '+name+' :: '+String(e&&e.message||e).split(/\r?\n/)[0].slice(0,220));}
}
(async()=>{
// ---------- F-63: the Auto switch track follows the Auto presentation ----------
await section('F-63 - the Auto switch track colour is the AUTO indicator (green on, red manual/stuck, yellow starting, grey no data; owner rule 07.11.2026, two indicators), not only "checked"',async()=>{
  const sig=(scn,mutate)=>{const p=load({scn,mutate});const sw=el();paint(p,{'[data-auto-switch]':[sw]});return [sw.attrs['data-sig'],sw.attrs['aria-checked'],p.T.autoIndicator().lamp];};
  assert.deepEqual(sig('ok',ok),['g','true','g'],'Auto on: green');
  assert.deepEqual(sig('ok',applying),['g','true','g'],'APPLYING: Auto is on (the main light shows the switching, not the Auto track)');
  assert.equal(sig('stale',ok)[0],'n','no fresh data is grey on the track too (never red or green without proof)');
  assert.equal(sig('ok',({status})=>{for(const r of status.profiles){r.code='VPN-003';r.https_success=0;}})[0],'g','both channels proven failed: the internet light is red, the Auto track still says Auto is on');
  assert.deepEqual(sig('off',ok),['r','false','r'],'Auto off = manual mode: red track');
  const css=require('fs').readFileSync(require('path').join(__dirname,'../files/www/luci-static/resources/view/homensai-vpn/ui176.css'),'utf8');
  assert(/\.hvx \.aswitch\[data-sig="y"\] \.trk\{background:var\(--warn\)\}/.test(css)&&/\.hvx \.aswitch\[data-sig="r"\] \.trk\{background:var\(--bad\)\}/.test(css),'the stylesheet colours the track by data-sig');
});

// ---------- F-64: sensors ----------
await section('F-64 - WAN sensor: unknown without proof or fresh data; server-key sensor not green from an empty list',async()=>{
  const wan=(w,k)=>{const p=load({mutate:({status})=>{status.wan_diagnosis=w;status.server_keys=k===undefined?{mode:'warn',pinned:2,changed:[]}:k;}});p.T.snap();return p.T.sensorWan();};
  const now=()=>Date.now()/1000;
  assert.equal(wan({time:now(),enabled:true,verdict:'N',confidence:970,code:null,evidence:{}}).lamp,'n','a fresh diagnosis without any proof is not "WAN is fine"');
  assert.equal(wan({time:now(),enabled:true,verdict:'N',confidence:970,code:null,evidence:{underlay:'ok'}}).lamp,'g','proof that the provider internet works: green');
  assert.equal(wan({time:now(),enabled:true,verdict:'N',confidence:970,code:null,evidence:{kmwan:'online'}}).lamp,'g','router WAN state online: green');
  const old=wan({time:now()-1000,enabled:true,verdict:'N',code:null,evidence:{underlay:'ok'}});
  assert.equal(old.lamp,'n','an old diagnosis is not a reading');assert(/нет свежих данных/.test(old.text),old.text);
  assert.equal(wan({enabled:true,verdict:'N',code:null,evidence:{underlay:'ok'}}).lamp,'n','no time at all: grey');
  const html=k=>{const p=load({mutate:({status})=>{status.wan_diagnosis={time:Date.now()/1000,enabled:true,code:null,evidence:{underlay:'ok'}};status.server_keys=k;}});p.T.snap();return p.T.sensorsHTML();};
  assert(/lamp g/.test(html({mode:'warn',pinned:2,changed:[]})),'something remembered and nothing changed: green');
  assert(!/lamp g"><\/i><span>Ключи/.test(html({mode:'warn',pinned:0,changed:[]}))&&/lamp n"><\/i><span>Ключи серверов: пока нечего сравнивать/.test(html({mode:'warn',pinned:0,changed:[]})),'an empty list with nothing remembered is not green');
  assert(!/lamp g"><\/i><span>Ключи/.test(html({mode:'warn'})),'no list at all is not green');
  assert(/lamp r/.test(html({mode:'warn',pinned:1,changed:[{profile:'wireguard:peer_2002',host:'h',pinned:'a',observed:'b'}]})),'a changed key: red');
});

// ---------- F-66: "Restore monitoring" follows the live state ----------
await section('F-66 - the Restore-monitoring button is a live binding',async()=>{
  const p=load({scn:'ok'});const box=el();
  paint(p,{'[data-b]':[Object.assign(box,{dataset:{b:'monrestore'}})]});
  assert.equal(box.innerHTML,'','the monitor works: no button');
  p.T.HV.st=Object.assign({},p.T.HV.st,{time:p.T.HV.st.time-3000});      // the monitor stopped publishing
  paint(p,{'[data-b]':[box]});
  assert(box.innerHTML.includes('data-act="monrestore"'),'the monitor stopped: the button appears without a re-render: '+box.innerHTML);
  p.T.HV.st=Object.assign({},p.T.HV.st,{time:Date.now()/1000});
  paint(p,{'[data-b]':[box]});
  assert(!box.innerHTML.includes('monrestore'),'the monitor is back: the button goes away');
  assert(p.T.monitorExtra().includes('data-b="monrestore"'),'both views carry the live slot');
});

// ---------- F-67: wizard step 2 and the channel card read a VPN the same way ----------
await section('F-67 - the wizard reads every VPN through the same reading as the channel card (inventory joined to status by identity)',async()=>{
  const p=load({scn:'ok'});p.T.snap();p.T.HV.step=2;
  const rows=[...p.T.wizard().matchAll(/<div><i class="lamp (\w)"><\/i><b class="fx1">([^<]*)<\/b><span class="small mute">([^<]*)<\/span><\/div>/g)];
  assert(rows.length>=2,'the wizard lists the VPN clients');
  const A=rows.find(r=>/Amsterdam/.test(r[2])),B=rows.find(r=>/Frankfurt/.test(r[2]));
  const prim=p.T.reading('primary'),res=p.T.reading('reserve');
  assert.equal(A[1],prim.lamp,'primary: the wizard lamp is the card lamp');assert(A[3].includes(prim.text),'and the same words: '+A[3]);
  assert.equal(B[1],res.lamp);assert(B[3].includes(res.text));
  assert.equal(A[2],p.T.B['p.name']().replace(/&amp;/g,'&'),'the same name');
  // the join is by identity: an inventory profile without measurements takes the status row of the same id
  const inv=p.inventory.profiles[0],joined=p.T.joinedProfile(inv);assert(Number.isFinite(joined.time)&&joined.id===inv.id);
});

// ---------- F-68: "both fail" needs two proven failures ----------
await section('F-68 - "both fail" only when both are proven failed; stale or checking is named as such',async()=>{
  const t=(mut,scn)=>{const p=load({scn:scn||'ok',mutate:mut});p.T.snap();return p.T.overall();};
  const a=t(primaryBadReserveStale);
  assert(/Текущий канал не отвечает/.test(a.title)&&!/Нет интернета/.test(a.title)&&/нет свежих данных/.test(a.sub),'reserve stale: only the current channel is proven failed: '+JSON.stringify(a));
  const b=t(primaryBadReserveChecking);
  assert(/Текущий канал не отвечает/.test(b.title)&&/проверяется/.test(b.sub),'reserve still checking: not a failure: '+JSON.stringify(b));
  const c=t(bothBad);assert(/Нет интернета через VPN/.test(c.title)&&c.lamp==='r','both proven failed: red "no internet"');
  const d=t(({status})=>{status.profiles[0].time-=300;},'reserve');   // on the reserve, the primary has no fresh check
  assert(!/Основной не отвечает/.test(d.sub)&&/Основной: нет свежих данных/.test(d.sub),'traffic on the reserve, primary unknown: do not claim it is not responding: '+d.sub);
  const e=t(({status})=>{},'reserve');assert(/Основной не отвечает/.test(e.sub),'primary proven failed: said so');
});

// ---------- F-69 and F-65 (UI part): a speed test of another session ----------
await section('F-69/F-65 - a speed test reported by the router drives status, Start, Cancel and "Switch here"',async()=>{
  const p=load({scn:'ok',mutate:speed});p.T.snap();
  const o=p.T.overall();assert(o.lamp==='g'&&/Идёт тест скорости/.test(o.sub),'owner 07.11.2026: the internet light stays green, the line names the test: '+JSON.stringify(o));
  assert(/data-act="speedcancel"/.test(p.T.speedHTML()),'Stop is offered for a test the router reports');
  assert.equal(p.T.switchAllowed('reserve'),false,'switching is not allowed during the pause');
  assert(/aria-disabled="true"/.test(p.T.B['r.sw']())&&/title="[^"]*тест скорости/i.test(p.T.B['r.sw']()),'the button is disabled and says why');
  p.T.switchTo('reserve');let m=p.modals.pop();assert(m&&/SPEED-BUSY/.test(m.body),'the explanation names the cause');
  p.T.speedTest('primary');m=p.modals.pop();assert(m&&/SPEED-BUSY/.test(m.body),'Start is refused with the honest code');
  assert.equal(count(p,'speed_start'),0);
  const btn=el({act:'speed'});paint(p,{'[data-act="speed"]':[btn]});assert.equal(btn.attrs['aria-disabled'],'true','Start buttons are disabled');
  p.T.speedCancel();await flush();assert.equal(count(p,'speed_cancel'),1,'Cancel reaches the router');
  // the paused monitor publishes nothing for minutes: the pause (read from the status reply itself) still explains the stale data
  const old=load({scn:'stale',mutate:speed});old.T.snap();assert(/Идёт тест скорости/.test(old.T.overall().sub),'stale monitor data during the pause: the test, not "no fresh data"');
  const q=load({scn:'ok'});q.T.snap();assert.equal(q.T.switchAllowed('reserve'),true,'without a pause the same switch is allowed');
  const b2=el({act:'speed'});paint(q,{'[data-act="speed"]':[b2]});assert.equal(b2.attrs['aria-disabled'],undefined);
});

// ---------- F-70: the plain description follows the detector that acts ----------
await section('F-70 - the description of Auto names the detector that acts (HMM, fast HMM, previous rule, hybrid)',async()=>{
  const text=(set)=>{const p=load({mutate:({settings})=>Object.assign(settings,set)});p.T.snap();return strip(p.T.B.autoplain());};
  const hmm=text({failure_model:'hmm'});assert(/HMM/.test(hmm)&&!/неудачных проверок подряд/.test(hmm),hmm);
  assert(/быстрая вероятностная модель/.test(text({failure_model:'hmm-fast'})));
  const cons=text({failure_model:'consecutive',recovery_failures:4});assert(/после 4 неудачных проверок подряд/.test(cons)&&!/HMM/.test(cons),cons);
  const hyb=text({failure_model:'hmm',hmm_or_failures:5});assert(/HMM/.test(hyb)&&/или после 5 неудачных проверок подряд/.test(hyb),hyb);
  // the overall line under a failed current channel with Auto on uses the same words
  const sub=set=>{const p=load({scn:'ok',mutate:({status,settings})=>{status.profiles[0].code='VPN-003';status.profiles[0].https_success=0;Object.assign(settings,set);}});p.T.snap();return p.T.overall().sub;};
  assert(/HMM/.test(sub({failure_model:'hmm'}))&&!/неудачных проверок подряд/.test(sub({failure_model:'hmm'})),'HMM: no "N failed checks" claim');
  assert(/после 3 неудачных проверок подряд/.test(sub({failure_model:'consecutive'})));
});

// ---------- F-79 ----------
await section('F-79 - one failure-test label, last-switch lamp from the event presenter, readiness codes as links, wizard step semantics',async()=>{
  const p=load({scn:'ok'});p.T.snap();
  const label=h=>[...h.matchAll(/data-act="fault">([^<]*)</g)].map(x=>x[1]);
  assert.deepEqual([...new Set(label(p.T.homeA()).concat(label(p.T.tabs.auto())))],['Запустить тест сбоя'],'one label for the failure test on every view');
  const en=load({scn:'ok',lang:'en'});en.T.snap();assert.deepEqual([...new Set(label(en.T.homeA()).concat(label(en.T.tabs.auto())))],['Run failure test']);
  // the last-switch lamp comes from the same event presenter as the event list
  assert(p.T.tabs.ch().includes('data-lamp="last"'),'the lamp is a live binding');
  const lamp=el({lamp:'last'});paint(p,{'[data-lamp]':[lamp]});
  const e=p.T.lastSwitch();assert(e,'the fixture has a completed switch');
  assert(lamp.classList.has(p.T.evKind(e).lamp),'the lamp shows the event kind: '+p.T.evKind(e).lamp);
  // readiness codes are links
  const r=load({scn:'ok',mutate:({status})=>{status.system_readiness.checks[6].state='fail';}});r.T.snap();
  const h=r.T.readinessHTML();assert(/<a class="code" href="#" data-act="code" data-code="CA-BUNDLE">CA-BUNDLE<\/a>/.test(h),'a failed check names its code as a link: '+strip(h));
  // wizard steps
  p.T.HV.step=2;const w=p.T.wizard();
  assert(/<li class="cur" aria-current="step">2 <span>Каналы<\/span><\/li>/.test(w),'the current step is announced');
  assert(/<li class="done">1 <span>Роутер<\/span><i class="vh"> — выполнен<\/i><\/li>/.test(w),'a completed step says so in text');
  const css=require('fs').readFileSync(require('path').join(__dirname,'../files/www/luci-static/resources/view/homensai-vpn/ui176.css'),'utf8');
  assert(/@media \(max-width:560px\)\{\.hvx \.steps li span\{display:inline;position:absolute/.test(css)&&/\.hvx \.steps li\.cur span\{position:static/.test(css),'on narrow screens the names stay in the tree and the current one is visible (not verified in a browser)');
});
if(failures.length){console.error(failures.length+' section(s) failed');process.exit(1);}
})().catch(e=>{console.error(e);process.exit(1);});
