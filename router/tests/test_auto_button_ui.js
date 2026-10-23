const fs=require('fs'),vm=require('vm'),assert=require('assert');
let calls=[],replies=[];
function E(tag,attrs,children){return {tag,attrs:attrs||{},children,disabled:!!(attrs&&attrs.disabled!=null),setAttribute(k,v){this.attrs[k]=v;}};}
const c={E,bi:en=>en,Date:{now:()=>1000000},ui:{addNotification(){}},window:{location:{reload(){}}},
  errorCodeLink:code=>code,rpc:{declare:spec=>(()=>{calls.push(spec.method);return new Promise(resolve=>replies.push(resolve));})}};
vm.createContext(c);vm.runInContext(fs.readFileSync('router/auto_panel.inc.js','utf8'),c);
c.autoLightModel=()=>({});c.autoWorking=()=>false;
const src=fs.readFileSync('router/auto_panel.inc.js','utf8');
vm.runInContext(src.slice(src.indexOf('function renderAutoControl('),src.indexOf('  var rows=status.profiles'))+
  'return {button,emergencyButton,actionLabel};}',c);
const status=(phase,state,requested,at)=>({time:1000,native_failover:{time:Math.max(1000,at),state,mode:'continuous-pair',readiness_verified:phase==='RUNNING'},
  auto_control:{pair_phase:phase,requested,requested_at:at,control_revision:'a'.repeat(32)}});
const render=s=>c.renderAutoControl(s,{settings:{}});
(async()=>{
  const off=status('STOPPED','STOPPED','off',900);let view=render(off);
  assert.equal(view.button.disabled,false);
  const start=view.button.attrs.click();assert.equal(view.button.disabled,true);
  view.button.attrs.click();assert.deepEqual(calls,['native_start']);
  view=render(off);assert.equal(view.button.disabled,true,'redraw during RPC must remain locked');
  replies.shift()({accepted:true,queued:true});await start;
  assert.equal(view.button.disabled,true,'ACK is not completion');
  view=render(status('STARTING','ARMED','on',1000));assert.equal(view.button.disabled,true);
  assert(/Turning Auto on/.test(view.actionLabel.textContent));assert.equal(view.emergencyButton.disabled,false);
  view=render(status('RUNNING','OBSERVING','on',1000));assert.equal(view.button.disabled,false);
  const stop=view.button.attrs.click();view.button.attrs.click();assert.deepEqual(calls,['native_start','native_stop']);
  replies.shift()({queued:true});await stop;assert.equal(view.button.disabled,true);
  view=render(status('STOPPING','RESTORING','off',1001));assert.equal(view.button.disabled,true);
  assert.equal(view.emergencyButton.disabled,true);assert(/Turning Auto off/.test(view.actionLabel.textContent));
  view=render(status('STOPPED','STOPPED','off',1001));assert.equal(view.button.disabled,false);
  // Reload has no local pending flag; authoritative phases still block both transitions.
  c.autoCommandPending=null;
  for(const [phase,state,requested] of [['STARTING','ARMED','on'],['STOPPING','RESTORING','off']]){
    view=render(status(phase,state,requested,1002));assert.equal(view.button.disabled,true);
    const count=calls.length;view.button.attrs.click();assert.equal(calls.length,count);
  }
  // Failed startup is a completed operation; show existing failure diagnostics and allow another deliberate action.
  view=render(status('FAILED','STOPPED','off',1003));assert.equal(view.button.disabled,false);
  console.log('PASS: duplicate clicks, ACK vs completion, redraw/reload locks, failure unlock and emergency Stop availability');
})().catch(e=>{console.error(e);process.exitCode=1;});
