'use strict';
// Switch statistics truth after a power cut (MT3000 soak, 31.10.2026, 2.0.0-alpha12 Lua line): the router was held on a
// manual switch (HELD-ON-RESERVE / OPERATOR-MANUAL), a sysrq-b power cut hit it, the supervisor recovery after the boot
// published RESTORING (route toward the saved order, not a new switch), failed (RTP-BOOT-PRECONDITION-UNVERIFIED,
// ROLLBACK-UNVERIFIED crashes are not history events) and gave up (BLOCKED / ROLLBACK-GIVEN-UP). 1.5 h later the operator
// archived the journal with homensai-vpn-emergency close-journal (no event), pressed Start (control start) and Auto returned
// to the primary (RESTORING + ROLLED-BACK, PRIMARY-STABLY-RECOVERED). The page used to draw that as a 1 h 42 min
// "Switching to the reserve" bar of unknown type. Now: its own kind, colour and outcome; never in the averages.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const selected=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+selected+'.js','utf8');
const prefix=source.slice(0,source.lastIndexOf('return view.extend({'));
const moduleName=/LAZY_HELP_NAME='([^']+)'/.exec(source)[1];
const moduleSource=fs.readFileSync('router/files/www/luci-static/resources/'+moduleName.replace(/\./g,'/')+'.js','utf8');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[];this.hidden=false;this.classList={add(){},remove(){},contains(){return false;}};[].concat(children==null?[]:children).flat(Infinity).filter(n=>n!=null&&n!==false).forEach(n=>this.appendChild(n));}
 appendChild(n){if(n&&typeof n==='object')n.parentNode=this;this.children.push(n);return n;}
 removeChild(n){this.children.splice(this.children.indexOf(n),1);return n;}
 insertBefore(n,r){const o=this.children.indexOf(n);if(o>=0)this.children.splice(o,1);const i=r?this.children.indexOf(r):-1;if(i<0)this.children.push(n);else this.children.splice(i,0,n);n.parentNode=this;return n;}
 get firstChild(){return this.children[0];}
 set textContent(v){this.children=[String(v)];}get textContent(){return text(this);}
 setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}
 addEventListener(){}querySelector(){return null;}querySelectorAll(){return [];}contains(){return false;}
 all(){return [this].concat(...this.children.filter(c=>c instanceof N).map(c=>c.all()));}
}
function text(n){if(n==null)return '';return n instanceof N?n.children.map(text).join(' '):String(n);}
function context(language){
 const c={console,URL,URLSearchParams,Intl,Promise,setTimeout(){},clearTimeout(){},setInterval(){},clearInterval(){},
  window:{HomenS:{},localStorage:{getItem:()=>null,setItem(){}},location:{href:'http://router/#switches',hash:'#switches',search:''}},
  document:{body:{contains:()=>false},createElement:tag=>new N(tag),createElementNS:(ns,tag)=>new N(tag),getElementById:()=>null,addEventListener(){},querySelector(){return null;},querySelectorAll(){return [];}},
  localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>null,setItem(){}},E:(...args)=>new N(...args),rpc:{declare:()=>()=>0},ui:{},poll:{},view:{extend:o=>o},
  baseclass:{extend:spec=>Object.assign(spec,{instantiate(){return spec;}})},L:{resource:p=>p},request:{}};
 vm.createContext(c);vm.runInContext(prefix,c);c.locale=language;
 c.L.require=()=>Promise.resolve(vm.runInContext('(function(){'+moduleSource+'})()',c));
 c.pageKeyNow=()=>'switches';
 return c;
}
const P='wireguard:peer_2002',R='openvpn:40354_2020',NOW=Math.floor(Date.now()/1000),B=NOW-4*3600;
// pair_event_fields as T.publish stores them (continuous-pair: transition metadata on every event, route_changed false by default)
const meta=(from,to,extra)=>Object.assign({source:P,target:R,mode:'continuous-pair',proof_scope:'router-probed-ipv4',transition_metadata_present:true,from_role:from,from_profile_id:from==='source'?P:R,destination_role:to,destination_profile_id:to==='source'?P:R,before_policy_role:from,route_changed:true,transition_completed:false},extra||{});
const still=extra=>Object.assign({source:P,target:R,mode:'continuous-pair',proof_scope:'router-probed-ipv4',transition_metadata_present:true,route_changed:false},extra||{});
// Times relative to the power cut at B (08:40 on the router): recovery 09:01, give-up 09:04, Start 10:39, back 10:43.
const HELD=[
 {sequence:1,time:B-7200,state:'APPLYING',codes:['OPERATOR-MANUAL'],manual:true,transition_source:'manual',...meta('source','target')},
 {sequence:2,time:B-7130,state:'STOPPED-ON-RESERVE',codes:['OPERATOR-MANUAL'],manual:true,transition_source:'manual',...meta('source','target',{transition_completed:true,transition_outcome:'committed'})}];
const RETURN=[
 {sequence:9,time:B+7140,state:'ARMED',codes:['PAIR-CONNECTING'],control_action:'start',control_source:'manual',control_time:B+7136,...still()},
 {sequence:10,time:B+7380,state:'RESTORING',codes:['PRIMARY-STABLY-RECOVERED'],transition_source:'automatic',control_action:'start',control_source:'manual',control_time:B+7136,...meta('target','source')},
 {sequence:11,time:B+7386,state:'ROLLED-BACK',codes:['PRIMARY-STABLY-RECOVERED'],transition_source:'automatic',original_restored:true,control_action:'start',control_source:'manual',control_time:B+7136,...meta('target','source',{transition_completed:true,transition_outcome:'restored'})}];
function status(events){return {profiles:[{id:P,name:'Primary'},{id:R,name:'Reserve'}],switch_timing:{avg_seconds:4.2,count:3,last_seconds:4},accounting:{reliability:{events:[]}},native_history:{events}};}
// A) the real sequence: the supervisor recovery itself starts the episode (reason SUPERVISOR-RECOVERY, toward the saved reserve order)
const realSequence=status([...HELD,
 {sequence:3,time:B+1293,state:'RESTORING',codes:['SUPERVISOR-RECOVERY'],...meta('source','target')},
 {sequence:4,time:B+1329,state:'RESTORING',codes:['SUPERVISOR-RECOVERY'],control_action:'start',control_source:'unknown',control_time:B-9000,...meta('source','target')},
 {sequence:5,time:B+1446,state:'BLOCKED',codes:['ROLLBACK-GIVEN-UP'],original_restored:false,control_action:'stop',control_source:'unknown',control_time:B+1446,...still()},
 {sequence:6,time:B+1456,state:'BLOCKED',codes:['ROLLBACK-GIVEN-UP'],original_restored:false,control_action:'stop',control_source:'unknown',control_time:B+1446,guard:'VPN-only',...still()},
 ...RETURN]);
// B) the restore toward the reserve carried another reason (Stop cleanup) and only the give-up shows the fault; its codes are sorted
const otherReason=status([...HELD,
 {sequence:3,time:B+1293,state:'RESTORING',codes:['PAIR-STOPPED'],transition_source:'unknown',...meta('source','target')},
 {sequence:5,time:B+1446,state:'BLOCKED',codes:['AUTO-OPTIONS-NOT-CLEARED','ROLLBACK-GIVEN-UP'],original_restored:false,...still()},
 ...RETURN]);
// C) a power cut on the reserve after an automatic switch; the recovery restores the primary by itself
const C0=NOW-3*3600;
const restored=status([
 {sequence:1,time:C0,state:'APPLYING',codes:['SOURCE-FAILED'],transition_source:'automatic',...meta('source','target')},
 {sequence:2,time:C0+61,state:'COMMITTED',codes:['CLIENT-CONFIRMED'],transition_source:'automatic',...meta('source','target',{transition_completed:true,transition_outcome:'committed'})},
 {sequence:3,time:C0+900,state:'RESTORING',codes:['SUPERVISOR-RECOVERY'],...meta('target','source')},
 {sequence:4,time:C0+930,state:'RESTORING',codes:['SUPERVISOR-RECOVERY'],original_restored:true,...meta('target','source',{transition_completed:true,transition_outcome:'restored'})}]);
// D) the recovery hangs without a saved give-up; the journal is archived by hand (no event) and Auto is started again;
//    E) a missing/damaged journal gives up at once (no source/target known)
const restart=status([...HELD,
 {sequence:3,time:B+1293,state:'RESTORING',codes:['SUPERVISOR-RECOVERY'],...meta('source','target')},
 ...RETURN,
 {sequence:20,time:NOW-600,state:'BLOCKED',codes:['JOURNAL-INTEGRITY-FAILED'],original_restored:false,mode:'continuous-pair',transition_metadata_present:true,route_changed:false}]);
(async()=>{
 for(const language of ['en','ru']){
  const en=language==='en',c=context(language),now=Date.now()/1000;
  const episodesOf=st=>c.switchTimeline(c.journalRows(st,null,now));
  // A
  let rows=c.journalRows(realSequence,null,now),ep=c.switchTimeline(rows);
  assert.equal(ep.length,3,'held manual switch, recovery, automatic return: '+JSON.stringify(ep.map(e=>e.kind)));
  let [held,rec,ret]=ep;
  assert.equal(held.kind,'manual');assert.equal(held.switching,70,'the real manual switch keeps its measurement');assert.equal(held.cut,B+1293,'interrupted by the recovery');
  assert.strictEqual(held.onReserve,null,'time on the reserve across a power cut is not invented');assert.strictEqual(held.returning,null,'a missing return is a dash, not 0 s');assert.strictEqual(held.detect,null);
  assert.equal(rec.kind,'recovery');assert.equal(rec.rec,B+1293);assert.equal(rec.end,B+1446,'repeated give-up adds nothing');assert.equal(rec.outcome,'gave-up');assert.equal(rec.code,'ROLLBACK-GIVEN-UP');
  for(const k of ['start','reserve','returnStart','back','rolledBack','detect','switching','total','onReserve','returning'])assert.strictEqual(rec[k],null,'recovery has no switch phase '+k);
  assert.equal(ret.kind,'auto');assert.strictEqual(ret.detect,null,'no detection without its two moments');assert.equal(ret.returnKind,'auto');assert.equal(ret.returning,6,'Auto return after Start measured on its own');assert.strictEqual(ret.start,null);
  const msg=k=>c.journalMessage(rows.find(r=>r.key==='controller:'+k),realSequence,true);
  assert(msg(3).includes(en?'recovery after a fault or restart':'восстановление после сбоя'),msg(3));
  assert(![3,4,5,6].some(k=>/switch|переключ/.test(rows.find(r=>r.key==='controller:'+k).timing||'')),'no switch duration is written for the recovery');
  // the page
  await c.ensureLazyPage('switches');
  let page=c.renderSwitchStats(realSequence),all=text(page);
  const rects=page.all().filter(n=>n.tag==='rect');
  assert(!rects.some(n=>n.attrs['data-phase']==='2'&&text(n).includes('1 h')),'no hour-long "switching to the reserve" bar');
  const purple=rects.filter(n=>n.attrs['data-phase']==='5');assert.equal(purple.length,1,'one recovery bar');assert.equal(purple[0].attrs.fill,'#8e44ad');
  assert(text(purple[0]).includes(en?'Recovery after a fault or restart':'Восстановление после сбоя или перезапуска')&&text(purple[0]).includes(en?'2 min 33 s':'2 мин 33 с'),text(purple[0]));
  const table=page.all().find(n=>n.attrs['data-switch-table']),cells=table.children.slice(1,-1).map(tr=>tr.children.map(text));
  assert.equal(cells.length,3);
  const recRow=cells[1];
  assert.equal(recRow[1],en?'Recovery after a fault or restart':'Восстановление после сбоя или перезапуска');
  assert.deepEqual(recRow.slice(2,8),['—','—','—','—','—','—'],'every switch column stays a dash');
  assert.equal(recRow[8],en?'Recovery given up after 2 min 33 s (ROLLBACK-GIVEN-UP); Auto stopped':'Восстановление прекращено через 2 мин 33 с (ROLLBACK-GIVEN-UP); Auto остановлен');
  assert.equal(cells[2][8],en?'Interrupted by a fault or restart':'Прервано сбоем или перезапуском');
  assert.equal(cells[0][8],en?'Back on the primary':'Снова на основном');
  const mean=table.children[table.children.length-1].children.map(text);
  assert.equal(mean[3],en?'1 min 10 s':'1 мин 10 с','switching mean = the manual switch only');assert.equal(mean[6],en?'6 s':'6 с','return mean = the automatic return only');
  const cards=page.all().find(n=>n.attrs['data-switch-cards']),cardText=text(cards);
  assert(cardText.includes(en?'recoveries after a fault 1':'восстановлений после сбоя 1'),cardText);
  assert(/Switching \(mean\) 1 min 10 s|Переключение \(среднее\) 1 мин 10 с/.test(cardText),cardText);
  assert(all.includes(en?'R = recovery after a fault or restart':'R — восстановление после сбоя или перезапуска'),'chart explanation names the kind');
  const legend=page.all().find(n=>n.attrs['class']==='hv-measure-legend');assert(text(legend).includes(en?'Recovery after a fault or restart (not a switch)':'Восстановление после сбоя или перезапуска (не переключение)'));
  const labels=page.all().filter(n=>n.tag==='text').map(text);assert(labels.some(l=>/ R$/.test(l)),'row label R: '+labels.join('|'));assert(!labels.some(l=>/ \?$/.test(l)),'no unknown-type row');
  if(en)assert(!/[Ѐ-ӿ]/.test(all),'no Cyrillic in English: '+(all.match(/.{0,40}[Ѐ-ӿ].{0,40}/)||[''])[0]);
  // B: the restore that opened the bar becomes the recovery itself (no separate sliver), its "switch" note removed
  ep=episodesOf(otherReason);assert.equal(ep.length,3,JSON.stringify(ep.map(e=>e.kind)));
  assert.equal(ep[1].kind,'recovery');assert.equal(ep[1].rec,B+1293);assert.equal(ep[1].end,B+1446);assert.equal(ep[1].code,'ROLLBACK-GIVEN-UP');assert.strictEqual(ep[1].switching,null);assert.strictEqual(ep[1].start,null);
  // C: the switch before the power cut stays measured; the recovery that restored the primary is reported as such
  ep=episodesOf(restored);assert.equal(ep.length,2);
  assert.equal(ep[0].kind,'auto');assert.equal(ep[0].switching,61);assert.equal(ep[0].cut,C0+900);assert.strictEqual(ep[0].returning,null);assert.strictEqual(ep[0].back,null);
  assert.equal(ep[1].kind,'recovery');assert.equal(ep[1].outcome,'source');assert.equal(ep[1].end,C0+930);
  page=c.LAZY_HELP.api.renderSwitchPage({episodes:ep,now,history:true,timing:null});all=text(page);
  assert(all.includes(en?'Recovered: traffic on the primary after 30 s':'Восстановлено: трафик на основном через 30 с'),all);
  // D/E
  ep=episodesOf(restart);assert.equal(ep.length,4,JSON.stringify(ep.map(e=>e.kind)));
  assert.equal(ep[1].outcome,'restart');assert(ep[1].end==null,'the hand-archived end is not invented');
  assert.equal(ep[2].kind,'auto');assert.equal(ep[2].returning,6);
  assert.equal(ep[3].kind,'recovery');assert.equal(ep[3].outcome,'gave-up');assert.equal(ep[3].code,'JOURNAL-INTEGRITY-FAILED');assert.equal(ep[3].rec,ep[3].end);
  page=c.LAZY_HELP.api.renderSwitchPage({episodes:ep,now,history:true,timing:null});all=text(page);
  assert(all.includes(en?'Ended by a new start of Auto; the end of the recovery was not saved':'Завершено новым запуском Auto; окончание восстановления не сохранено'));
  assert(all.includes(en?'Recovery given up (JOURNAL-INTEGRITY-FAILED); Auto stopped':'Восстановление прекращено (JOURNAL-INTEGRITY-FAILED); Auto остановлен'));
  const slivers=page.all().filter(n=>n.tag==='rect'&&n.attrs['data-phase']==='5');assert.equal(slivers.length,2);
  assert(slivers.every(n=>text(n).includes(en?'length not saved':'длительность не сохранена')),slivers.map(text).join('|'));
  // a recovery still running is drawn open up to now
  ep=episodesOf(status([{sequence:1,time:now-120,state:'RESTORING',codes:['SUPERVISOR-RECOVERY'],...meta('source','target')}]));
  assert.equal(ep.length,1);page=c.LAZY_HELP.api.renderSwitchPage({episodes:ep,now,history:true,timing:null});
  assert(text(page).includes(en?'Recovering now':'Идёт восстановление'));assert.equal(page.all().filter(n=>n.tag==='rect'&&n.attrs['fill-opacity']).length,1);
 }
 console.log('PASS: power-cut recovery is its own episode (kind, colour, outcome), never a switch nor averaged; interrupted switches keep their measured part');
})().catch(error=>{console.error(error);process.exitCode=1;});
