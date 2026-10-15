'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const {Model}=require('./model.js');
const report={suite:'exhaustive-boolean-matrix',cases:0,passed:0,failed:0,steps:0,failures:[]};
const start=performance.now();
for(let flags=0;flags<4096;flags++){
  const m=new Model({version:1,channels:[{id:'id_c1',name:'Основной',priority:1,servers:[{id:'id_s1',name:'Первый',protocol:'OpenVPN'}]},{id:'id_c2',name:'Резерв',priority:2,servers:[{id:'id_s2',name:'Второй',protocol:flags%2?'OpenVPN':'WireGuard'}]}]},{seedHistory:false});
  const [primary,backup]=m.candidates().map(x=>x.s);
  for(const [i,key]of ['connected','online','dns','path'].entries()){primary[key]=!!(flags&(1<<i));backup[key]=!!(flags&(1<<(i+4)));}
  m.wan=!!(flags&256);m.auto=!!(flags&512);m.priority=!!(flags&1024);m.wanFallback=!!(flags&2048);
  const primaryCode=m.health(primary),backupCode=m.health(backup),can=m.wan&&m.auto&&m.priority&&primaryCode&&primaryCode!=='CHECK-001';
  const expected=can&&!backupCode?'id_s2':can&&backupCode&&m.wanFallback?null:'id_s1';
  const expectedWan=!!(can&&backupCode&&m.wanFallback);
  try{
    for(let i=0;i<3;i++){m.tick();report.steps++;}
    assert.equal(m.active,expected);assert.equal(m.usingWan,expectedWan);
    assert(m.events.filter(e=>e.kind==='switch').length<=1);
    if(expected==='id_s2')assert.equal(m.events.find(e=>e.kind==='switch').recovery,15);
    report.passed++;
  }catch(e){report.failed++;report.failures.push({flags,message:e.message});}
  report.cases++;
}
report.elapsedMs=Math.round(performance.now()-start);
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,failures:report.failures.slice(0,10)},null,2));process.exitCode=report.failed?1:0;
