'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const {Router,apply,STAGES}=require('./router_sim.js');
const results=[],checks={count:0};
function verify(value,message){checks.count++;assert(value,message);}
const categories=['linux-delays','power-loss','flash-errors','torn-journal','rpc-failures','ipv6','conntrack','workers','compound','idempotency'];
for(let family=0;family<10;family++)for(let variant=0;variant<20;variant++){
  const id=family*20+variant+1,r=new Router({ipv6:variant%3!==0}),o={id:'tx'+id};const initial=r.config();
  const stage=STAGES[variant%STAGES.length];let expectedBusy=false;
  if(family===0)o.delays={[stage]:variant%4===0?40000:variant*300};
  if(family===1)o.powerStage=stage;
  if(family===2)r.flash.fault={write:r.flash.writes+1+variant%3,mode:['ENOSPC','EROFS','EIO'][variant%3],persistent:variant>=10};
  if(family===3&&variant<15)r.flash.fault={write:r.flash.writes+1+variant%3,mode:['before-sync','torn','after-sync'][variant%3]};
  if(family===3&&variant>=15){o.corruptStage='config';o.corruptBoth=true;o.powerStage='config';}
  if(family===4){o.rpc4=['reject','timeout-before','timeout-after','ok'][variant%4];o.rpc6=['ok','timeout-before','timeout-after','reject'][variant%4];}
  if(family===5){if(variant%4===0)o.ipv6LeakStage='v6';else if(variant%4===1)o.healthStage='v6';else if(variant%4===2)o.rpc6='timeout-before';else o.rpc6='timeout-after';}
  if(family===6){r.flushFault=variant%3===0;if(variant%5===0){o.workerStage='conntrack';o.workerObeys=false;o.globalFlush=true;}}
  if(family===7){if(variant%4===0){r.lock={owner:'stock-worker',alive:true};expectedBusy=true;}else if(variant%4===1){r.lock={owner:'dead-worker',alive:false};}else{o.workerStage=stage;o.workerObeys=variant%4===2;}}
  if(family===8){o.rpc4='timeout-after';o.powerStage=stage;if(variant%2===0)o.wanStage='verify';if(variant%3===0)r.flash.fault={write:r.flash.writes+2,mode:'EROFS'};}
  if(family===9){o.rpc4='timeout-after';o.rpc6='timeout-after';if(variant%3===0)o.powerStage=stage;}
  const start=performance.now();
  try{
    const result=apply(r,o);r.invariant();
    verify(r.lan,'LAN must remain reachable');
    verify(!r.gate||r.safe(r.config().profile),'Unsafe forwarding after apply');
    if(expectedBusy){verify(r.lock?.owner==='stock-worker'&&r.lock.alive,'Stole a live worker lock');verify(r.config().generation===initial.generation,'Busy lock changed configuration');verify(r.gate,'Busy lock blocked previously healthy traffic');}
    const after=r.config();verify(after.generation>=initial.generation,'Configuration generation decreased');
    if(o.workerStage&&o.workerObeys===false&&r.log.some(e=>e.stage==='worker-wrote'||e.stage==='stock-global-flush'))verify(after.profile==='operator','Overwrote an external configuration change');
    if(family===6&&!o.globalFlush)verify(r.sessions.some(s=>s.id==='bank')&&r.sessions.some(s=>s.id==='youtube'),'Selective conntrack cleanup destroyed unrelated sessions');
    if(r.flash.fault?.persistent)verify(!r.gate,'Persistent storage failure released forwarding');
    if(result.state==='committed'){verify(r.sessions.every(s=>s.scope!=='common'),'Old common conntrack survived committed switch');verify(r.routes.v4==='backup','Commit selected wrong IPv4 profile');verify(r.routes.v6===(r.ipv6?'backup':'BLOCK'),'Commit selected wrong IPv6 profile');verify(r.gate,'Committed transaction stayed blocked');}
    // Clear the injected failure and restart repeatedly, as after restoration of power/storage.
    r.flash.fault=null;r.wan=true;r.profiles.backup.v6=true;
    let boot=r.boot();r.invariant();const once=r.config();let boot2=r.boot();r.invariant();
    verify(r.config().profile===once.profile,'Repeated boot changed profile');verify(r.gate||boot.state==='blocked'||boot2.state==='blocked','Unexplained blocked state');
    verify(r.lan,'LAN lost after reboot');verify(r.config().generation>=after.generation,'Reboot reverted configuration generation');
    if(family===9&&r.gate){const beforeCalls=r.rpcCalls;const again=apply(r,{id:o.id,rpc4:'timeout-after',rpc6:'timeout-after'});r.invariant();verify(r.confirmed.size<=1,'Duplicate transaction counted twice');if(result.state==='committed')verify(again.state==='duplicate'&&r.rpcCalls===beforeCalls,'Acknowledged transaction resent RPC');}
    results.push({id,category:categories[family],variant,stage,result:result.state,recovered:boot.state,finalProfile:r.config().profile,gate:r.gate,trace:r.log,passed:true,ms:Math.round(performance.now()-start)});
  }catch(error){results.push({id,category:categories[family],variant,stage,passed:false,error:error.message,trace:r.log});}
}
const report={suite:'router-transaction-fault-simulator',mode:'simulation-not-device',cases:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).length,assertions:checks.count,categories:Object.fromEntries(categories.map(c=>[c,results.filter(r=>r.category===c).length])),results};
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,results:results.filter(r=>!r.passed).map(({trace,...r})=>r)},null,2));process.exitCode=report.failed?1:0;
