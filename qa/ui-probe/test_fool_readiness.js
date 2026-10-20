const assert=require('assert');
const {frameState,waitForReady,readinessDetails,createFrame,frameLayout}=require('./fool.js');
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
  const root={getAttribute:()=> 'c'},sheet={href:'http://fixture/ui.css',sheet:{cssRules:[]},disabled:false,media:''};
  const detail=readinessDetails({contentDocument:{readyState:'complete',querySelector:s=>s==='.hv-app'?root:{textContent:'fixture'},querySelectorAll:s=>s==='.hv-app'?[root]:[sheet],getElementsByTagName:()=>[root]},contentWindow:{location:{href:'http://fixture/'},performance:{getEntriesByType:()=>[]},getComputedStyle:()=>({getPropertyValue:()=>''})}});
  assert(detail.accessible&&detail.app);assert.equal(detail.design,'c');assert.equal(detail.links[0].rules,0,'an empty sheet is recorded, never inferred ready');
  // The probe HTML already owns iframe#f: appending another would put the app below the viewport.
  const existing={style:{},getBoundingClientRect(){const width=Number(/width:(\d+)px/.exec(this.style.cssText)[1]),height=Number(/height:(\d+)px/.exec(this.style.cssText)[1]);return {left:0,top:0,right:width,bottom:height,width,height};}},output={hidden:false};let creations=0;
  const doc2={documentElement:{style:{}},body:{style:{},appendChild(){throw new Error('must reuse existing iframe');}},getElementById:id=>id==='f'?existing:output,createElement(){creations++;throw new Error('duplicate iframe');},querySelectorAll:()=>[existing]};
  const host={innerWidth:1280,innerHeight:760};assert.strictEqual(createFrame(doc2,{w:1280,h:900},host),existing);assert.equal(creations,0);assert(output.hidden);
  const layout=frameLayout(doc2,existing,host);assert.equal(layout.count,1);assert(layout.visible&&layout.inside);assert.equal(layout.height,760);
  const offscreen={getBoundingClientRect:()=>({left:0,top:900,right:1280,bottom:1660,width:1280,height:760})};assert(!frameLayout(doc2,offscreen,host).visible,'the previous second-iframe layout must be rejected');
  console.log('PASS: stable document+CSS readiness, delayed CSS, transient navigation recovery, bounded missing-app/CSS/origin refusal and unexpected-error propagation');
})().catch(error=>{console.error(error);process.exitCode=1;});
