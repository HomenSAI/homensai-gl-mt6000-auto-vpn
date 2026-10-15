'use strict';
// Reproducible generated scenario testing. Never reads or contacts a router.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {Model,monthStart}=require('./model.js');
const RUNS=Number(process.env.ALTA_RUNS||600),STEPS=Number(process.env.ALTA_STEPS||300),SEED_START=Number(process.env.ALTA_SEED_START||1);
function prng(seed){let n=seed>>>0;return()=>{n+=0x6D2B79F5;let t=n;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}
const report={suite:'seeded-scenario-stress',runs:RUNS,stepsPerRun:STEPS,completed:0,totalSteps:0,checks:0,failures:[],actionCounts:{},transitions:0,failedAttempts:0,modelSeconds:0,seedStart:SEED_START,elapsedMs:0};
function check(condition,message){report.checks++;assert(condition,message);}
function config(seed,rng){const count=1+Math.floor(rng()*6);return {version:1,channels:Array.from({length:count},(_,i)=>({id:`id_c${seed}x${i}`,name:i%3?'Канал '+i:'Одинаковое имя',priority:i+1,servers:Array.from({length:1+Math.floor(rng()*7)},(_,j)=>({id:`id_s${seed}x${i}x${j}`,name:'Сервер '+j,protocol:rng()<.5?'OpenVPN':'WireGuard'}))}))};}
const boundaries=['2026-10-14T12:00:00Z','2026-10-31T22:50:00Z','2026-01-31T22:50:00Z','2026-03-28T23:50:00Z','2026-10-24T23:50:00Z','2026-12-31T22:50:00Z'];
const started=performance.now(),realRandom=Math.random,realNow=Date.now;
for(let index=0;index<RUNS;index++){
  const seed=SEED_START+index;
  const rng=prng(seed),base=Date.parse(boundaries[(seed-1)%boundaries.length]);Math.random=rng;Date.now=()=>base;
  const m=new Model(config(seed,rng));m.history=[];m.events=[];m.monthLedger=null;
  let previousMonthly={start:monthStart(m.time),rx:0,tx:0},lastAutomatic=-Infinity;const ledger=[],trace=[];
  try{
    for(let step=0;step<STEPS;step++){
      const pick=xs=>xs.length?xs[Math.floor(rng()*xs.length)]:null;
      const profile=pick(m.candidates()),action=rng()<.42?Math.floor(rng()*22):-1;
      trace.push({step,action,time:m.time});if(trace.length>35)trace.shift();report.actionCounts[action]=(report.actionCounts[action]||0)+1;
      if(profile){
        if(action===0)profile.s.online=!profile.s.online;
        if(action===1)profile.s.dns=!profile.s.dns;
        if(action===2)profile.s.path=!profile.s.path;
        if(action===3)profile.s.connected=!profile.s.connected;
        if(action===13){profile.c.name='Своё <название> '+seed;profile.s.name='Переименованный '+step;}
        if(action===15&&profile.s.id!==m.active)profile.s.archived=true;
        if(action===18)profile.c.servers.reverse();
        if(action===19&&profile.s.id!==m.active)profile.s.protocol=profile.s.protocol==='WireGuard'?'OpenVPN':'WireGuard';
      }
      if(action===4)m.wan=!m.wan;
      if(action===5)m.scenario('all');
      if(action===6)m.scenario('restore');
      if(action===7)m.auto=!m.auto;
      if(action===8)m.priority=!m.priority;
      if(action===9)m.wanFallback=!m.wanFallback;
      if(action===10)m.autoReturn=!m.autoReturn;
      if(action===11){const healthy=m.wan?m.candidates().filter(({s})=>!m.health(s)):[];const candidate=pick(healthy);if(candidate)m.switchTo(candidate.s.id);}
      if(action===12)m.scenario('apply');
      if(action===14){const channel=pick(m.channels.filter(c=>!c.archived&&c.servers.length<20));if(channel)m.addServer(channel.id,'Новый сервер '+step,rng()<.5?'OpenVPN':'WireGuard');}
      if(action===16){const eligible=m.ranking(86400000,rng()<.5).filter(r=>r.eligible);const ids=eligible.filter(()=>rng()<.5).map(r=>r.s.id);const active=m.active;m.applyRanking(ids,86400000,false,rng()<.2);check(m.active===active,'Accepting ranking changed active route');}
      if(action===17)m.measureServers();
      if(action===20){const c=pick(m.channels);if(c)c.priority=1+Math.floor(rng()*20);}
      if(action===21&&m.channels.length<20){const c=m.addChannel('Дополнительный');m.addServer(c.id,'Дополнительный сервер','WireGuard');}
      const before=m.active,wasWAN=m.wan,enabled=m.auto&&m.priority,oldEvent=m.events[0]?.id;
      m.tick();report.totalSteps++;report.modelSeconds+=5;ledger.push({...m.history.at(-1)});
      check(Number.isFinite(m.time),'Non-finite model time');
      check(!m.usingWan||m.wanFallback,'WAN used without explicit permission');
      check(!m.usingWan||m.active===null,'WAN and VPN selected simultaneously');
      const changed=before!==m.active,newEvents=[];for(const e of m.events){if(e.id===oldEvent)break;newEvents.push(e);}
      const attempts=newEvents.filter(e=>e.kind==='switch');
      check(attempts.length<=1,'Multiple switching attempts in one tick');
      for(const e of attempts){report.transitions++;if(!e.success)report.failedAttempts++;check(wasWAN&&enabled,'Automatic attempt while WAN/automation off');check(m.time-lastAutomatic>=30000,'Automatic transition cooldown broken');lastAutomatic=m.time;
        const target=m.find(e.to.server);check(target&&!target.c.archived&&!target.s.archived&&!m.health(target.s),'Selected unhealthy or archived candidate');check(e.success||m.active===before,'Failed attempt did not retain previous route');check(e.recovery===null||e.recovery>=0,'Negative recovery');}
      if(changed)check(wasWAN&&enabled,'Route changed while automation disabled');
      const stats=m.metrics(86400000);
      check(stats.availability===null||(stats.availability>=0&&stats.availability<=100),'Availability outside 0..100');
      check(stats.efficiency===null||(stats.efficiency>=0&&stats.efficiency<=100),'Efficiency outside 0..100');
      check(stats.intra+stats.cross<=stats.switches,'Switch double counting');
      check(stats.protocol<=stats.switches,'Protocol double counting');
      check(Math.abs(stats.known+stats.unknown-stats.coverage)<.001,'Observation coverage mismatch');
      check(Math.abs(stats.good+stats.down-stats.known)<.001,'Unknown time included as uptime/downtime');
      for(const v of Object.values(stats.channels))check(v.rx>=0&&v.tx>=0&&Number.isFinite(v.rx+v.tx),'Invalid traffic');
      const monthly=m.monthly(),start=monthStart(m.time);let rx=0,tx=0,coverage=0;
      for(const h of ledger){const overlap=Math.max(0,h.end-Math.max(h.start,start));if(h.known){coverage+=overlap;if(h.channel){rx+=h.rx*overlap/(h.end-h.start);tx+=h.tx*overlap/(h.end-h.start);}}}
      check(Math.abs(monthly.rx-rx)<.01&&Math.abs(monthly.tx-tx)<.01,'Monthly traffic differs from independent interval oracle');
      check(monthly.coverage===coverage,'Monthly known coverage incorrect');
      if(previousMonthly.start===monthly.start)check(monthly.rx>=previousMonthly.rx&&monthly.tx>=previousMonthly.tx,'Monthly counter decreased inside month');
      previousMonthly=monthly;
      if(step%25===0){const ranking=m.ranking(86400000,true);check(ranking.length===m.candidates().length,'Ranking omits active candidate');for(const r of ranking)if(r.eligible)check(m.wan&&!m.health(r.s)&&r.last?.known&&r.last.passed&&m.time-r.last.time<=60000,'Unusable recommendation');
        const exported=JSON.parse(JSON.stringify(m.exportConfig()));const copy=new Model(exported);check(copy.candidates().map(v=>v.s.id).join(',')===m.candidates().map(v=>v.s.id).join(','),'Saving/reloading changed operator order');}
      check(m.history.length<=5000&&m.events.length<=1000,'History/event limits exceeded');
      check(Object.keys(m.monthLedger).length<=18,'Monthly ledger unbounded');
      for(const p of Object.values(m.probes))check(p.rows.length<=3000,'Probe history unbounded');
    }
    report.completed++;
  }catch(error){report.failures.push({seed,base,step:trace.at(-1)?.step,message:error.message,trace});}
  if((index+1)%100===0)console.log('Progress '+(index+1)+'/'+RUNS+'; failures='+report.failures.length);
}
Math.random=realRandom;Date.now=realNow;report.elapsedMs=Math.round(performance.now()-started);
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,failures:report.failures.slice(0,5).map(({trace,...f})=>f)},null,2));process.exitCode=report.failures.length?1:0;
