'use strict';
// Reference transaction contract, NOT an implementation of the GL.iNet RPC API.
const {createHash}=require('node:crypto');
const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
class PowerLoss extends Error {}
class FlashError extends Error {}
class Flash {
  constructor(){this.files=new Map();this.writes=0;this.fault=null;}
  write(name,value){
    this.writes++;const fault=this.fault&&(this.fault.write===this.writes||(this.fault.persistent&&this.writes>=this.fault.write))?this.fault:null;
    if(fault&&['ENOSPC','EROFS','EIO'].includes(fault.mode))throw new FlashError(fault.mode);
    const prior=this.files.get(name),record={value:clone(value),hash:digest(value)};
    if(fault?.mode==='before-sync')throw new PowerLoss('power before durable write');
    if(fault?.mode==='torn')record.hash='invalid';
    this.files.set(name,{current:record,previous:prior?.current||prior?.previous});
    if(fault?.mode==='torn')throw new PowerLoss('torn flash write');
    if(fault?.mode==='after-sync')throw new PowerLoss('power after durable write');
  }
  read(name){const file=this.files.get(name);for(const r of [file?.current,file?.previous])if(r&&digest(r.value)===r.hash)return clone(r.value);throw new FlashError('no verified '+name);}
  corrupt(name,both=false){const f=this.files.get(name);if(f?.current)f.current.hash='corrupt';if(both&&f?.previous)f.previous.hash='corrupt';}
}
class Router {
  constructor({ipv6=true}={}){
    this.flash=new Flash();this.ipv6=ipv6;this.time=0;this.lock=null;this.fence=0;this.gate=false;this.lan=true;this.wan=true;
    this.routes={v4:'primary',v6:ipv6?'primary':'BLOCK'};
    this.profiles={primary:{v4:true,v6:true},backup:{v4:true,v6:true},operator:{v4:true,v6:true}};
    this.sessions=[{id:'bank',scope:'bank',profile:'primary'},{id:'call',scope:'common',profile:'primary'},{id:'youtube',scope:'special',profile:'operator'}];
    this.log=[];this.confirmed=new Set();this.rpcApplied=new Set();this.rpcCalls=0;this.flushFault=false;
    this.flash.write('config',{profile:'primary',generation:0,writer:'initial'});
    this.flash.write('journal',{state:'committed',profile:'primary',generation:0,transaction:'initial',receipts:{}});
    this.gate=true;
  }
  config(){return this.flash.read('config');}
  safe(profile){return this.wan&&this.profiles[profile]?.v4&&(!this.ipv6||this.profiles[profile]?.v6)&&this.routes.v4===profile&&this.routes.v6===(this.ipv6?profile:'BLOCK');}
  invariant(){if(!this.lan)throw Error('LAN management lost');if(this.gate){const c=this.config();if(!this.safe(c.profile))throw Error('Unverified, split-family, or WAN traffic escaped gate');}if(this.routes.v6==='WAN'&&this.gate)throw Error('IPv6 leak');}
  trace(stage){this.invariant();this.log.push({stage,time:this.time,gate:this.gate,routes:{...this.routes},generation:this.config().generation});}
  worker(profile,{obeyLock=true,globalFlush=false}={}){
    if(this.lock?.alive&&obeyLock){this.log.push({stage:'worker-deferred'});return false;}
    this.gate=false;const c=this.config();this.flash.write('config',{profile,generation:c.generation+1,writer:'worker'});
    this.routes={v4:profile,v6:this.ipv6?profile:'BLOCK'};
    if(globalFlush)this.sessions=[];
    this.log.push({stage:globalFlush?'stock-global-flush':'worker-wrote',generation:c.generation+1});return true;
  }
  rpc(profile,family,{mode='ok',transaction}={}){
    this.rpcCalls++;const key=transaction+':'+family;if(this.rpcApplied.has(key))return 'duplicate';
    if(mode==='reject')throw Error('RPC rejected');if(mode==='timeout-before')return 'unknown';
    this.routes[family]=profile;this.rpcApplied.add(key);return mode==='timeout-after'?'unknown':'ok';
  }
  flushCommon(){if(this.flushFault)throw Error('conntrack operation failed');this.sessions=this.sessions.filter(s=>s.scope!=='common');}
  boot(){
    this.gate=false;this.lock=null;this.rpcApplied.clear();this.confirmed.clear();this.routes={v4:'BLOCK',v6:'BLOCK'};
    try{
      const journal=this.flash.read('journal'),c=this.config();let profile=c.profile,outcome=journal.outcome||'reconciled';if(journal.state==='committed'&&(journal.profile!==c.profile||journal.generation!==c.generation))outcome='external-change';
      if(journal.state==='intent'){outcome='rolled-back';
        const own=c.writer===journal.transaction||c.writer===journal.before.writer;if(!own)outcome='external-change';
        if(own&&c.profile!==journal.before.profile){this.flash.write('config',{profile:journal.before.profile,generation:c.generation+1,writer:journal.transaction});profile=journal.before.profile;}
      }else if(journal.state!=='committed')throw Error('unknown journal state');
      const current=this.config();this.routes={v4:profile,v6:this.ipv6?profile:'BLOCK'};
      if(!this.safe(profile))return {state:'blocked',profile};
      this.flash.write('journal',{state:'committed',profile,generation:current.generation,transaction:journal.transaction,outcome,receipts:journal.receipts||{}});
      for(const transaction of Object.keys(journal.receipts||{}))this.confirmed.add(transaction);
      this.gate=true;this.trace('boot-reconciled');return {state:'reconciled',profile};
    }catch(error){this.gate=false;this.log.push({stage:'boot-blocked',error:error.message});return {state:'blocked',error:error.message};}
  }
}
const STAGES=['lock','intent','v4','v6','conntrack','verify','config','commit','release'];
function apply(router,options={}){
  const transaction=options.id||'tx',target=options.target||'backup',start=router.time;let before;try{before=router.config();}catch(error){router.gate=false;return {state:'blocked',error:error.message};}
  let acquired=false,committed=false,intent=false;
  const hook=stage=>{
    router.time+=options.delays?.[stage]||0;
    if(options.workerStage===stage)router.worker('operator',{obeyLock:options.workerObeys!==false,globalFlush:!!options.globalFlush});
    if(options.wanStage===stage){router.wan=false;router.gate=false;}
    if(options.ipv6LeakStage===stage){router.routes.v6='WAN';}
    if(options.healthStage===stage){router.profiles.backup.v6=false;router.gate=false;}
    if(options.corruptStage===stage)router.flash.corrupt('journal',!!options.corruptBoth);
    if(options.powerStage===stage){router.gate=false;throw new PowerLoss('power at '+stage);}
    router.trace(stage);
    if(router.time-start>(options.deadline||30000))throw Error('Linux scheduling deadline exceeded');
    const c=router.config();if(c.writer!==transaction&&(c.generation!==before.generation||c.profile!==before.profile))throw Error('external configuration changed');
  };
  try{
    if(router.confirmed.has(transaction)){const receipt=router.flash.read('journal').receipts?.[transaction];return {state:receipt&&receipt.target!==target?'id-conflict':'duplicate',transaction,profile:before.profile,originalTarget:receipt?.target,verified:router.safe(before.profile)};}
    if(options.expectedGeneration!==undefined&&before.generation!==options.expectedGeneration)return {state:'generation-conflict',transaction,profile:before.profile};
    if(router.lock?.alive)throw Error('worker owns live lock');
    router.lock={owner:transaction,alive:true,fence:++router.fence};acquired=true;hook('lock');
    router.gate=false;
    const receipts=router.flash.read('journal').receipts||{};router.flash.write('journal',{state:'intent',transaction,target,before,receipts});intent=true;hook('intent');
    router.rpc(target,'v4',{mode:options.rpc4,transaction});hook('v4');
    if(router.ipv6)router.rpc(target,'v6',{mode:options.rpc6,transaction});else router.routes.v6='BLOCK';hook('v6');
    router.flushCommon();hook('conntrack');
    if(!router.safe(target))throw Error('post-apply verification failed');hook('verify');
    router.flash.write('config',{profile:target,generation:before.generation+1,writer:transaction});hook('config');
    const outcomes={...receipts,[transaction]:{target,generation:before.generation+1}};while(Object.keys(outcomes).length>64)delete outcomes[Object.keys(outcomes)[0]];router.flash.write('journal',{state:'committed',transaction,profile:target,generation:before.generation+1,outcome:'applied',receipts:outcomes});committed=true;hook('commit');
    // Never open forwarding based on RPC success alone: recheck config and both families.
    if(router.config().profile!==target||!router.safe(target))throw Error('final verification failed');
    router.gate=true;router.confirmed.add(transaction);hook('release');
    router.lock=null;return {state:'committed',transaction,profile:target};
  }catch(error){
    if(!acquired)return {state:'busy',transaction,error:error.message};
    router.gate=false;
    if(error instanceof PowerLoss){router.lock=null;return {state:'power-lost',transaction,error:error.message};}
    if(acquired)router.lock=null;
    const result=acquired?router.boot():{state:'busy'};
    const state=result.state!=='reconciled'?result.state:result.profile===before.profile?'rolled-back':result.profile===target?'committed-reconciled':'external-reconciled';
    return {state,transaction,committed,intent,error:error.message,profile:result.profile};
  }
}
module.exports={Router,Flash,PowerLoss,FlashError,apply,STAGES};
