'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {Model}=require('./model.js');
const results=[];
function run(name,fn){const start=performance.now();try{fn();results.push({name,passed:true,ms:Math.round(performance.now()-start)});}catch(e){results.push({name,passed:false,error:e.message,ms:Math.round(performance.now()-start)});}}
function fresh(){const old=Date.now;Date.now=()=>Date.parse('2026-10-15T12:00:00Z');try{const m=new Model();m.events=[];return m;}finally{Date.now=old;}}
function ticks(m,n){for(let i=0;i<n;i++)m.tick();}
run('Revoking direct WAN permission closes the bypass',()=>{const m=fresh();m.wanFallback=true;m.scenario('all');ticks(m,3);assert.equal(m.usingWan,true);m.wanFallback=false;m.tick();assert.equal(m.usingWan,false);});
run('WAN outage invalidates the primary recovery timer',()=>{const m=fresh(),primary=m.active;const spare=m.channels[1].servers[0].id;m.switchTo(spare);ticks(m,50);m.scenario('wan');ticks(m,20);m.scenario('restore');m.tick();assert.equal(m.active,spare);ticks(m,24);assert.equal(m.active,primary);});
run('Recommendations never promote a newly failed server',()=>{const m=fresh();m.scenario('server');assert.equal(m.ranking(604800000,true).find(r=>r.s.id===m.active).eligible,false);});
run('Recommendations are invalidated while WAN is down',()=>{const m=fresh();m.scenario('wan');assert(m.ranking(604800000,true).every(r=>!r.eligible));});
run('Recommendations reject unmeasured and stale profiles',()=>{const m=fresh();m.time+=61000;assert(m.ranking(604800000,true).every(r=>!r.eligible));});
run('Monthly counter survives detailed history eviction',()=>{const m=fresh();const {monthStart}=require('./model.js');m.history=[{start:monthStart(m.time),end:m.time,channel:m.channels[0].id,server:m.active,known:true,ok:true,rx:1e12,tx:1e11}];const before=m.monthly().rx;ticks(m,5100);assert(m.history.length<=5000);assert(m.monthly().rx>=before);});
run('Recovery includes a failed first attempt and retry delay',()=>{const m=fresh();m.scenario('apply');m.scenario('server');ticks(m,9);const restored=m.events.find(e=>e.kind==='switch'&&e.success);assert.equal(restored.recovery,45);});
run('Retries share one outage episode',()=>{const m=fresh();m.scenario('apply');m.scenario('server');ticks(m,9);const attempts=m.events.filter(e=>e.kind==='switch');assert.equal(attempts.length,2);assert.equal(attempts[0].episode,attempts[1].episode);});
run('Healthy manual switch is not outage recovery',()=>{const m=fresh();m.switchTo(m.channels[0].servers[1].id);assert.equal(m.events[0].recovery,null);assert.equal(m.metrics(3600000).average,null);});
run('Usable VPN replaces direct WAN without five-minute hold',()=>{const m=fresh();m.wanFallback=true;m.scenario('all');ticks(m,10);assert(m.usingWan);m.scenario('restore');ticks(m,2);assert(m.active);assert.equal(m.usingWan,false);});
run('Adding a profile never selects VPN over an active WAN bypass',()=>{const m=fresh();m.wanFallback=true;m.scenario('all');ticks(m,3);const active=m.active;m.addServer(m.channels[0].id,'Новый сервер','WireGuard');assert.equal(m.active,active);assert.equal(m.usingWan,true);});
run('Switch totals survive log eviction',()=>{const m=new Model(undefined,{seedHistory:false});for(let i=0;i<1200;i++)m.switchTo(m.active===m.channels[0].servers[0].id?m.channels[0].servers[1].id:m.channels[0].servers[0].id);assert.equal(m.events.length,1000);assert.equal(m.metrics(86400000).switches,1200);assert.equal(m.metrics(86400000).intra,1200);});
const report={suite:'business-regressions',total:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length,results};
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));process.exitCode=report.failed?1:0;
