const assert=require('assert');
const {frameState,waitForReady}=require('./fool.js');
const app={},attribute={},doc={readyState:'complete',querySelector:s=>s==='.hv-app'?app:attribute};
const win={getComputedStyle:()=>({getPropertyValue:()=> '1px'})};
const frame={contentDocument:doc,contentWindow:win};
(async()=>{
  let now=0,attached=0;
  let state=await waitForReady(frame,1000,async ms=>now+=ms,()=>now,()=>attached++);
  assert(state.ready&&state.doc===doc);assert.equal(now,100,'requires two stable reads');assert.equal(attached,2);
  // App exists before CSS: it must not start an interaction budget yet.
  now=0;win.getComputedStyle=()=>({getPropertyValue:()=>now>=800?'1px':''});
  state=await waitForReady(frame,1000,async ms=>now+=ms,()=>now);
  assert(state.ready);assert.equal(state.waitMs,900);
  // An iframe navigation can temporarily reject same-origin access. Bounded recovery is allowed.
  now=0;win.getComputedStyle=()=>({getPropertyValue:()=> '1px'});
  const navigation={get contentWindow(){if(now<300){const e=new Error('transient');e.name='SecurityError';throw e;}return win;},get contentDocument(){return doc;}};
  assert.equal(frameState(navigation).reason,'navigation-origin-pending');
  state=await waitForReady(navigation,1000,async ms=>now+=ms,()=>now);assert(state.ready);assert.equal(state.waitMs,400);
  // Missing app, CSS, or a persistently foreign frame can never pass.
  for(const bad of [{contentWindow:win,contentDocument:null},{contentWindow:{getComputedStyle:()=>({getPropertyValue:()=>''})},contentDocument:doc},{get contentWindow(){const e=new Error();e.name='SecurityError';throw e;}}]){
    now=0;state=await waitForReady(bad,500,async ms=>now+=ms,()=>now);assert.equal(state.ready,false);assert.equal(state.waitMs,500);
  }
  const bug={get contentWindow(){throw new Error('real harness defect');}};
  assert.throws(()=>frameState(bug),/real harness defect/,'only navigation SecurityError is pending');
  console.log('PASS: stable document+CSS readiness, delayed CSS, transient navigation recovery, bounded missing-app/CSS/origin refusal and unexpected-error propagation');
})().catch(error=>{console.error(error);process.exitCode=1;});
