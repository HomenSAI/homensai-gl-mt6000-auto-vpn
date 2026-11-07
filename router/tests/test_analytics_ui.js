const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:(en)=>en,locale:'en'};vm.createContext(c);
vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),c);
vm.runInContext(fs.readFileSync('router/analytics_panel.inc.js','utf8'),c);
const profile=(id,protocol,channel,priority,code=null)=>({id,name:id,protocol,channel,priority,code,interface:'tun-'+id,time:99,dns_ok:true,https_success:2});
const status={time:99,profiles:[profile('a','openvpn','main',1),profile('b','openvpn','main',2),profile('c','openvpn','reserve',1),profile('d','wireguard','other',1)],native_failover:{state:'COMMITTED',target:'a',time:99}};
let model=c.cascadePathModel(status,100);assert.equal(model.selected,'a');assert.equal(model.next,'b');
status.profiles[1].code='VPN-003';assert.equal(c.cascadePathModel(status,100).next,'c');
status.profiles[2].enabled=false;assert.equal(c.cascadePathModel(status,100).next,'d');
assert.equal(c.cascadePathModel({...status,rpc_error:true},100).selected,null);assert.equal(c.cascadePathModel({...status,rpc_error:true},100).next,null);
assert.equal(c.cascadePathModel(status,200).next,null);
const e=(sequence,time,state,extra={})=>({sequence,time,state,source:'a',target:'b',codes:[],...extra});
let rows=c.retainedTransitions({events:[e(1,10,'APPLYING'),e(2,12,'WAIT-CLIENT'),e(3,14,'COMMITTED')]});
assert.equal(rows.length,1);assert.equal(rows[0].duration,4);assert.equal(rows[0].phases.length,3);
let s=c.recoverySummary(rows,0,20);assert.equal(s.success_ratio,1);assert.equal(s.p95,4);
assert.equal(c.recoverySummary(rows,0,13).known_outcomes,0);
assert.equal(c.recoverySummary(rows,20,30).success_ratio,null);
rows=c.retainedTransitions({events:[e(1,10,'APPLYING'),e(3,14,'COMMITTED')]});assert.equal(rows[0].outcome,'unknown');
rows=c.retainedTransitions({events:[e(1,10,'APPLYING'),e(2,11,'COMMITTED',{target:'c'})]});assert.equal(rows[0].outcome,'unknown');
rows=c.retainedTransitions({events:[e(1,10,'APPLYING'),e(2,9,'COMMITTED')]});assert.equal(rows[0].outcome,'unknown');
// review F-56: the router stores APPLYING 1000 -> COMMITTED at wall 990 as 1000, 1000 with clock_stepped_back. The outcome
// stays committed; the duration is unknown (null), not a fabricated 0 s, and is left out of median/P95/worst.
rows=c.retainedTransitions({events:[e(1,1000,'APPLYING'),e(2,1000,'WAIT-CLIENT',{clock_stepped_back:true}),e(3,1000,'COMMITTED',{clock_stepped_back:true}),
  e(4,1100,'APPLYING'),e(5,1102,'WAIT-CLIENT'),e(6,1105,'COMMITTED')]});
assert.equal(rows.length,2);assert.equal(rows[0].outcome,'committed');assert.equal(rows[0].duration,null);assert.equal(rows[1].duration,5);
s=c.recoverySummary(rows,0,2000);assert.equal(s.committed,2);assert.equal(s.known_outcomes,2);assert.equal(s.recovered_samples,1);
assert.equal(s.median,5);assert.equal(s.p95,5);assert.equal(s.worst,5);
rows=c.retainedTransitions({events:[e(1,10,'APPLYING'),e(2,11,'APPLYING'),e(3,12,'ROLLED-BACK')]});assert.equal(rows.length,2);assert.equal(rows[0].outcome,'unknown');assert.equal(rows[1].outcome,'rolled_back');
const samples=Array.from({length:20},(_,i)=>({start:i,end:i+1,target:'b',outcome:i<18?'committed':'rolled_back',duration:i+1}));
s=c.recoverySummary(samples,0,100);assert.equal(s.median,10.5);assert.equal(s.p95,19);assert.equal(s.worst,20);assert.equal(s.max_consecutive_failures,2);assert.equal(s.success_ratio,.9);
let groups=c.recoveryGroups(samples,[{id:'b',channel:'__proto__',protocol:'openvpn'}],0,100);assert.equal(groups.channel[0].name,'Current group: __proto__');assert.equal(groups.server[0].metrics.attempts,20);
const epoch=Date.parse('2026-03-31T22:30:00Z')/1000;
assert.equal(new Date(c.recoveryWindow('month',epoch,'UTC').start*1000).toISOString(),'2026-03-01T00:00:00.000Z');
assert.equal(new Date(c.recoveryWindow('week',epoch,'UTC').start*1000).toISOString(),'2026-03-30T00:00:00.000Z');
const march29=c.recoveryWindow('day',Date.parse('2026-03-29T12:00:00Z')/1000).start;
const march30=c.recoveryWindow('day',Date.parse('2026-03-30T12:00:00Z')/1000).start;
assert.equal(march30-march29,23*3600);
assert.equal(new Date(c.recoveryWindow('month',Date.parse('2026-10-01T00:00:00Z')/1000).start*1000).toISOString(),'2026-09-30T22:00:00.000Z');
assert.throws(()=>c.recoveryWindow('invalid',epoch));
for(const value of ['=1+1',' +SUM(A1)','\t=cmd','\ufeff@x','-2+3']){const csv=c.analyticsCSV('ranking',[{name:value,token:'MUST-NOT-EXPORT'}]);assert(csv.includes('"\''));assert(!csv.includes('MUST-NOT-EXPORT'));}
let csv=c.analyticsCSV('ranking',[{name:'русский, "name"\nnext'}]);assert(csv.startsWith('\ufeff'));assert(csv.includes('"русский, ""name""\nnext"'));
rows=c.retainedTransitions({events:[e(1,9,'ARMED',{attempt_id:1,retry_episode_id:1,probe_evidence:{source_streak_met:true,required_failures:3,token:'PRIVATE'}}),e(2,10,'APPLYING',{attempt_id:1,retry_episode_id:1}),e(3,14,'ARMED',{attempt_id:1,retry_episode_id:1,codes:['TRIAL-PASSED'],trial:true,phase_evidence:[{phase:'ARMED',time:9},{phase:'APPLYING',time:10},{phase:'RESTORING',time:13},{phase:'ROLLED-BACK',time:14}]})]});
assert.equal(rows.length,1);assert.equal(rows[0].outcome,'trial_passed');assert.equal(rows[0].duration,4);assert.equal(rows[0].prepared_at,9);assert.equal(rows[0].retry_episode_id,1);assert(!JSON.stringify(rows).includes('PRIVATE'));
assert.equal(c.recoverySummary(rows,0,20).trials_passed,1);assert.equal(c.recoverySummary(rows,0,20).success_ratio,1);
assert.equal(rows[0].trial,true);
assert.equal(c.recoverySummary([{start:1,end:2,target:'__proto__',outcome:'held'}],0,10).max_consecutive_failures,1);
assert.equal(c.retainedTransitions({events:[e(1,1e100,'APPLYING')]}).length,0);
assert(c.analyticsCSV('transitions',c.analyticsExportRows('transitions',{},rows)).includes('"required_failures"'));
assert.throws(()=>c.analyticsCSV('secrets',[]));
console.log('PASS: cascade grouping, trustworthy selected path, gap-aware transition metrics, calendar windows, per-group failures and private formula-safe CSV');

const ids=[{id:'openvpn:40354_2005',router_name:'de1552.nordvpn.com.tcp',protocol:'openvpn',channel:'default'}];
const inv={settings:{plan_target:ids[0].id}};
let identity=c.recoveryIdentity(ids[0].id,ids,inv);
assert(identity.server.includes('de1552.nordvpn.com.tcp')&&identity.server.includes('OpenVPN'));
assert.equal(identity.channel,'Reserve channel (current pair)');
assert.equal(c.recoveryIdentity('wireguard:peer_5',[],{}).protocol,'WireGuard');
assert.equal(c.recoveryIdentity('unknown',[],{}).server,'Server not recorded in event');
assert(!c.recoveryIdentity('unknown',[],{}).server.includes('de1552'));
assert.equal(c.recoveryIdentity(ids[0].id,[],{}).server.includes('Archived profile'),true);
assert.equal(c.recoveryGroups(samples,[],100,200).server.length,0,'no empty outside-window unknown groups');
console.log('PASS: concrete current configured server/protocol/role, honest archived or missing identities and selected-window grouping');

const prepEvents=[e(1,10,'ARMED',{source:null,target:null,codes:['PAIR-CONNECTING']}),e(2,11,'ARMED',{source:null,target:null,codes:['PAIR-WAITING-PROBES']}),e(3,12,'APPLYING'),e(4,15,'STOPPED-ON-RESERVE')];
const prepared=c.retainedTransitions({events:prepEvents});
assert.equal(prepared.length,2,'repeated unidentified preparation is one record, separate from actual application');
assert(c.recoveryPreparation(prepared[0]));assert(!c.recoveryPreparation(prepared[1]));
assert.equal(c.recoveryOutcomeText(prepared[1]),'Reserve retained after Stop');
assert.equal(c.recoveryOutcomeText(prepared[0]),'Preparation ended; a new attempt followed');
let gap=c.retainedTransitions({events:[e(1,10,'APPLYING'),e(3,14,'COMMITTED')]})[0];
assert.equal(c.recoveryOutcomeText(gap),'Result not recorded: missing history events');assert.equal(gap.outcome,'unknown','a UI label never fabricates success');
const english=c.bi;c.bi=(_en,ru)=>ru;
assert(c.recoveryChannelText({...prepared[1],target:'openvpn:40354_2005'},'target',ids,inv).includes('Резервный канал'));
for(const r of prepared.concat(gap)){assert(!/unknown|held/.test(c.recoveryOutcomeText(r)));assert(!c.recoveryChannelText(r,'source',ids,inv).includes('unknown'));}
c.bi=english;
console.log('PASS: grouped preparation, actual final reserve state, explicit gap reasons, concrete channel labels and Russian results without fabricated completion');
const historical={source:'wireguard:peer_1',target:'openvpn:40354_2005',start:10,outcome:'held',codes:['VPN-003'],probe_evidence:{}};
c.bi=en=>en;
const changedPair={settings:{plan_source:historical.target,plan_target:historical.source}};
assert(c.recoveryChannelText(historical,'source',[],changedPair).startsWith('Primary channel ·'));
assert(c.recoveryChannelText(historical,'target',[],changedPair).startsWith('Reserve channel ·'));
const historicalGroups=c.recoveryGroups([historical],[],0,20,changedPair);
assert.equal(historicalGroups.channel[0].name,'Reserve channel');assert(historicalGroups.server[0].name.startsWith('Reserve channel ·'));assert(historicalGroups.protocol[0].name.startsWith('Reserve channel ·'));
const exported=c.analyticsExportRows('failures',{},[historical])[0];assert.equal(exported.source_role,'primary');assert.equal(exported.target_role,'reserve');assert(c.analyticsCSV('failures',[exported]).includes('"source_role"'));
console.log('PASS: event-time roles across transaction cells/groups and CSV remain unchanged after current-pair swap');
vm.runInContext(fs.readFileSync('router/journal_panel.inc.js','utf8'),c);
c.E=(tag,attrs={},children=[])=>({tag,attrs,children});
const visual=c.renderTransitionBadge({sequence:1},{1:{from:2,to:1,confirmed:true}});
assert.equal(visual.children[0].children,'M');assert.equal(visual.children[2].children,'R');assert.equal(visual.children[1].children,'←');assert(visual.children[0].attrs.class.includes('working'));
console.log('PASS: older controller-event table uses the same M/R renderer and confirmed reverse colours');

// ---------- Honest P95 (same rule as scripts/honest_stats.py on feat/honest-p95-formal-ci-20261103): n >= 59 or "≈P95 ... мало данных" ----------
{
  c.bi=(en)=>en;
  assert.equal(c.P95_MIN_N,59);assert.equal(c.p95Honest(58),false);assert.equal(c.p95Honest(59),true);
  // 0.95^59 = 0.0485 < 0.05 <= 0.95^58: the smallest sample count at which the maximum bounds the P95 with 95 % confidence
  assert(Math.pow(.95,59)<.05&&Math.pow(.95,58)>.05);
  // coverage of the sample maximum with 95 % confidence = floor(100 * 0.05^(1/n)); the same numbers as scripts/honest_stats.py coverage_percent
  assert.deepEqual([1,4,14,20,58,59,100].map(c.p95MaxCoverage),[5,47,80,86,94,95,97]);
  assert.equal(c.p95MaxCoverage(0),0);
  const fmt=v=>v.toFixed(1);
  assert.equal(c.p95Text(null,0,fmt),'—');
  assert.equal(c.p95Text(8,4,fmt),'≈8.0 (too few samples: n=4, needs ≥59)');
  assert.equal(c.p95Text(58,59,fmt),'58.0','from n >= 59 the P95 estimate row drops the few-data note (it stays an estimate; the bound is a separate row)');
  assert.equal(c.p95MaxText(20,20,fmt),'20.0 (≥86 %)');assert.equal(c.p95MaxText(60,59,fmt),'60.0');
  assert.equal(c.p95MaxClaim(8,4,fmt),'max 8.0: with 95 % confidence ≥47 % of cases are no slower than the max');
  assert.equal(c.p95MaxClaim(60,59,fmt),'');
  c.bi=(_en,ru)=>ru;
  assert.equal(c.p95Text(8,4,fmt),'≈8.0 (мало данных: n=4, нужно ≥59)');
  assert.equal(c.p95MaxClaim(8,4,fmt),'max 8.0: с 95 % уверенностью ≥47 % случаев не медленнее max');
  c.bi=(en)=>en;
  // the summary carries the facts the panel prints; p95 itself keeps its meaning (the empirical quantile), only its presentation is honest
  const few=Array.from({length:20},(_,i)=>({start:i,end:i+1,target:'b',outcome:'committed',duration:i+1}));
  let h=c.recoverySummary(few,0,100);assert.equal(h.p95,19);assert.equal(h.recovered_samples,20);assert.equal(h.p95_honest,false);assert.equal(h.p95_max_coverage,86);
  const many=Array.from({length:59},(_,i)=>({start:i,end:i+1,target:'b',outcome:'committed',duration:i+1}));
  h=c.recoverySummary(many,0,100);assert.equal(h.p95,57);assert.equal(h.p95_honest,true);assert.equal(h.p95_max_coverage,95);
  const g=c.recoveryGroups(few,[{id:'b',channel:'x',protocol:'openvpn'}],0,100);assert.equal(g.server[0].metrics.p95_honest,false);
  // the panel prints P95 only through the honest helpers (no bare toFixed of a P95 left)
  const panel=fs.readFileSync('router/analytics_panel.inc.js','utf8');
  assert(panel.includes('p95Text(s.p95,s.recovered_samples,fmt)')&&panel.includes('p95Text(m.p95,m.recovered_samples,'));
  assert(!/fmt\(s\.p95\)|m\.p95\.toFixed/.test(panel),'no unqualified P95 cell');
  assert(panel.includes('p95MaxText(s.worst,s.recovered_samples,fmt)')&&panel.includes('p95MaxClaim(s.worst,s.recovered_samples,fmt)'));
  assert(panel.includes('«≈P95» — мало данных')&&panel.includes('Отдельная строка «верхняя граница P95» появляется от 59 измерений'),'the legend explains ≈P95 and the separate upper bound in Russian (F-59)');
  assert(panel.includes('“≈P95” means too few samples')&&panel.includes('The separate “P95 upper bound” appears from 59 samples'),'and in English');
}
console.log('PASS: P95 of recovery time is an estimate at every n: n >= 59 without the few-data note (bound is a separate row), otherwise "≈P95 … мало данных" and the maximum with its 95 %-confidence coverage (RU/EN)');
