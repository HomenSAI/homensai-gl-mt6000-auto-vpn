'use strict';
const assert=require('node:assert/strict');
const {Router,apply}=require('./router_sim.js');
let count=0;
function test(name,fn){fn();count++;console.log('OK '+name);}
test('Durable successful receipt survives a reboot',()=>{const r=new Router();assert.equal(apply(r,{id:'one'}).state,'committed');r.boot();const calls=r.rpcCalls;assert.equal(apply(r,{id:'one'}).state,'duplicate');assert.equal(r.rpcCalls,calls);});
test('Old successful request is not replayed after a later transaction',()=>{const r=new Router();apply(r,{id:'one'});apply(r,{id:'two',target:'primary'});r.boot();const calls=r.rpcCalls;const old=apply(r,{id:'one'});assert.equal(old.state,'duplicate');assert.equal(old.profile,'primary');assert.equal(old.originalTarget,'backup');assert.equal(r.rpcCalls,calls);});
test('Reusing a successful ID for another target is rejected',()=>{const r=new Router();apply(r,{id:'one'});r.boot();assert.equal(apply(r,{id:'one',target:'primary'}).state,'id-conflict');assert.equal(r.config().profile,'backup');});
test('Busy worker does not interrupt healthy forwarding',()=>{const r=new Router();r.lock={owner:'worker',alive:true};assert.equal(apply(r).state,'busy');assert(r.gate);assert.equal(r.lock.owner,'worker');});
test('Corrupted journal cannot release forwarding on reboot',()=>{const r=new Router();apply(r);r.flash.corrupt('journal',true);assert.equal(r.boot().state,'blocked');assert(!r.gate);assert(r.lan);});
test('External change after commit is retained and not labelled rollback',()=>{const r=new Router();const out=apply(r,{workerStage:'commit',workerObeys:false});assert.equal(out.state,'external-reconciled');assert.equal(r.config().profile,'operator');r.boot();assert.equal(r.flash.read('journal').outcome,'external-change');assert(r.gate);});
test('Stale generation rejects a new request without disrupting current exit',()=>{const r=new Router();apply(r,{id:'one',expectedGeneration:0});r.boot();const before=r.rpcCalls;assert.equal(apply(r,{id:'stale',target:'primary',expectedGeneration:0}).state,'generation-conflict');assert.equal(r.rpcCalls,before);assert(r.gate);assert.equal(r.config().profile,'backup');});
console.log(count+' transaction regressions passed');
