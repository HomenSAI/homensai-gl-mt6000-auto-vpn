'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const {Model,monthStart}=require('./model.js');
const report={suite:'long-running-and-capacity',passed:0,failed:0,results:[]};
function test(name,fn){const start=performance.now();try{const data=fn()||{};report.passed++;report.results.push({name,passed:true,ms:Math.round(performance.now()-start),...data});}catch(e){report.failed++;report.results.push({name,passed:false,error:e.message,ms:Math.round(performance.now()-start)});}}
test('400 profiles: independent sampling and ranking',()=>{const channels=Array.from({length:20},(_,i)=>({id:'id_c'+i,name:'Канал '+i,priority:i+1,servers:Array.from({length:20},(_,j)=>({id:'id_s'+i+'x'+j,name:'Сервер '+j,protocol:j%2?'OpenVPN':'WireGuard'}))}));const m=new Model({version:1,channels},{seedHistory:false});assert.equal(m.candidates().length,400);m.measureServers();const ranking=m.ranking(604800000,true);assert.equal(ranking.length,400);assert.equal(new Set(ranking.map(r=>r.s.id)).size,400);assert(ranking.every(r=>r.eligible));return {profiles:400,nodeHeapMB:Math.round(process.memoryUsage().heapUsed/1048576)};});
test('50,000 ticks: month rollover, unknown periods, bounded history',()=>{
  const m=new Model(undefined,{seedHistory:false});m.time=Date.parse('2026-10-31T22:59:50Z');m.lastProbe=null;m.goodSince={};
  let expectedStart=monthStart(m.time),rx=0,tx=0,coverage=0,lastMonthly=0;
  for(let i=0;i<50000;i++){
    if(i%400===0)m.scenario('server');if(i%400===30)m.scenario('restore');
    if(i%1700===200)m.scenario('unknown');if(i%1700===240)m.scenario('restore');
    if(i%2700===500)m.scenario('wan');if(i%2700===540)m.scenario('restore');
    m.tick();const h=m.history.at(-1),key=monthStart(m.time);if(key!==expectedStart){expectedStart=key;rx=tx=coverage=lastMonthly=0;}
    const overlap=Math.max(0,h.end-Math.max(h.start,key));if(h.known){coverage+=overlap;if(h.channel){rx+=h.rx*overlap/(h.end-h.start);tx+=h.tx*overlap/(h.end-h.start);}}
    const month=m.monthly();assert(Math.abs(month.rx-rx)<.01);assert(Math.abs(month.tx-tx)<.01);assert.equal(month.coverage,coverage);assert(month.rx>=lastMonthly);lastMonthly=month.rx;
    assert(m.history.length<=5000);assert(m.events.length<=1000);assert(Object.values(m.probes).every(p=>p.rows.length<=3000));
  }
  return {ticks:50000,modelHours:50000*5/3600,history:m.history.length,events:m.events.length,rx,tx,nodeHeapMB:Math.round(process.memoryUsage().heapUsed/1048576)};
});
test('Repeated failed applies use backoff instead of 30-second loop',()=>{const m=new Model(undefined,{seedHistory:false});m.scenario('server');for(let i=0;i<360;i++){m.failNextSwitch=true;m.tick();}const attempts=m.events.filter(e=>e.kind==='switch').sort((a,b)=>a.time-b.time);assert(attempts.length<12);for(let i=1;i<attempts.length;i++)assert(attempts[i].time-attempts[i-1].time>=Math.min(300000,30000*2**Math.min(4,i-1)));return {modelMinutes:30,attempts:attempts.length};});
test('18-month retention and ledger boundary handling',()=>{const m=new Model(undefined,{seedHistory:false});m.ensureMonthLedger();for(let i=0;i<30;i++){const mid=Date.UTC(2024,i,15),start=monthStart(mid);m.accountInterval({start,end:start+5000,known:true,channel:'id_c',rx:100,tx:10});assert(Object.keys(m.monthLedger).length<=18);}assert.equal(Object.keys(m.monthLedger).length,18);});
test('Manual samples do not change selection or traffic',()=>{const m=new Model(undefined,{seedHistory:false}),active=m.active,before=m.monthly();for(let i=0;i<1000;i++)m.measureServers();assert.equal(m.active,active);assert.equal(m.monthly().rx,before.rx);assert.equal(m.history.length,0);return {tests:1000};});
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));process.exitCode=report.failed?1:0;
