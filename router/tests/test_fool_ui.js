const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.value=attrs.value||'';this.disabled=attrs.disabled!=null;this.checked=false;this.events={};this.classList={add:()=>{},remove:()=>{}};(Array.isArray(children)?children:[children]).forEach(n=>this.appendChild(n));}
  appendChild(n){this.children.push(n);return n;}
  setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]??null;}removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,fn){(this.events[k]||(this.events[k]=[])).push(fn);}
  emit(k){(this.events[k]||[]).forEach(fn=>fn());}
  get childNodes(){return this.children;}
  get textContent(){return this.children.map(n=>n instanceof Node?n.textContent:String(n)).join('');}
  set textContent(v){this.children=[String(v)];}
  querySelectorAll(selector){return walk(this).filter(n=>selector.split(',').includes(n.tag));}
}
function walk(n){return n instanceof Node?[n,...n.children.flatMap(walk)]:[];}
function make(){
  let modal,clock=0,timers=new Map(),calls=[],resolve;
  const ctx={E:(...a)=>new Node(...a),bi:(en,ru)=>ctx.locale==='ru'?ru:en,locale:'en',setTimeout:fn=>{timers.set(++clock,fn);return clock;},safeCode:()=>false,errorCodeLink:c=>c,
    ui:{showModal:(_,body)=>modal=new Node('modal',{},body),hideModal:()=>modal=null,addNotification:()=>{}},window:{location:{reload:()=>{}}},
    RECOVERY_PRESETS:JSON.parse(fs.readFileSync('router/files/usr/lib/homensai-vpn/recovery_presets.json','utf8')),
    rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise(r=>resolve=r);}}};
  vm.createContext(ctx);for(const file of ['fool_guard','recovery_panel','speed_panel','setup_wizard'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),ctx);
  return {ctx,calls,get modal(){return modal;},finish:value=>resolve(value),tick:()=>{const pending=[...timers.values()];timers.clear();pending.forEach(fn=>fn());},get timerCount(){return timers.size;}};
}
const field=(root,label)=>walk(root).find(n=>n.attrs['aria-label']===label);
const button=(root,label)=>walk(root).find(n=>n.tag==='button'&&n.textContent===label);
const click=node=>node.attrs.click({currentTarget:node,target:node});
(async()=>{
  let m=make(),c=m.ctx;
  for(const [key,range] of Object.entries(c.FOOL_RANGES)){
    for(const value of [range[0],range[1]])assert(c.foolCheckNumber(key,String(value)).ok,key);
    for(const value of ['', ' ', '1e2','0x10','1.0','10,0','+10',' 10','10 ',String(range[0]-1),String(range[1]+1)])assert(!c.foolCheckNumber(key,value).ok,key+': '+value);
  }
  assert(!c.foolCheckText('name','valid\n').ok,'trailing newline must be rejected before trim');
  assert(c.foolCheckNumber('system.interval','9'.repeat(400)).message.includes('too big'));
  assert(c.foolCheckNumber('system.interval','-'+'9'.repeat(400)).message.includes('too small'));
  assert(!c.foolCheckText('channel','valid\x7f').ok);
  assert(c.foolCheckText('chat','@example_channel').ok);assert(!c.foolCheckText('chat','@x').ok);
  assert(!c.foolCheckText('token','PRIVATE INVALID TOKEN').ok);
  assert(!c.foolCheckText('token','PRIVATE INVALID TOKEN').message.includes('PRIVATE'));
  c.locale='ru';assert(/[А-Яа-я]/.test(c.foolCheckNumber('monitor.interval','').message));c.locale='en';
  let release,requests=0,first=new Node('button',{},'Save'),second=new Node('button',{},'Save');
  const saving=c.guardedAction(first,()=>{requests++;return new Promise(r=>release=r);},{key:'redraw'});
  c.guardResume(second,'redraw');assert(first.disabled&&second.disabled);
  await c.guardedAction(second,()=>requests++,{key:'redraw'});assert.equal(requests,1);
  c.foolGate(second,[()=>true]);assert(second.disabled,'validation must not unlock RPC');
  release();await saving;assert(second.textContent.startsWith('Wait '),'recreated button gets cooldown updates');
  for(let i=0;i<11;i++)m.tick();assert(!first.disabled&&!second.disabled);assert.equal(second.textContent,'Save');assert(!c.FOOL_LOCKS.redraw);
  let confirmed=0;c.confirmAction('Review',[],'Confirm',()=>confirmed++);const confirm=button(m.modal,'Confirm');click(confirm);click(confirm);assert.equal(confirmed,1);
  // A redrawn speed settings card joins the pending lock and keeps invalid edits disabled after cooldown.
  let card=c.speedSettings({settings:{}}),save=button(card,'Save speed settings'),budget=field(card,'Payload budget per server, MiB');
  budget.value='1e1';budget.emit('input');assert(save.disabled);assert.equal(budget.value,'1e1');click(save);assert.equal(m.calls.length,0);
  budget.value='8';budget.emit('input');const pending=click(save);assert.equal(m.calls.length,1);assert.equal(m.calls[0].method,'setup_speed');
  card=c.speedSettings({settings:{}});save=walk(card).find(n=>n.tag==='button');assert(save.disabled);click(save);assert.equal(m.calls.length,1);
  budget=field(card,'Payload budget per server, MiB');budget.value='33';budget.emit('input');m.finish({saved:false});await pending;
  for(let i=0;i<11;i++)m.tick();assert(save.disabled,'cooldown must not override validation');budget.value='8';budget.emit('input');assert(!save.disabled);
  // Monitor preferences reject silently coercible numeric text and do not duplicate a pending save.
  m=make();c=m.ctx;c.monitorPreferences({settings:{interval:0}});save=button(m.modal,'Save monitoring preferences');assert(save.disabled,'invalid stored zero is preserved');
  const interval=field(m.modal,'Probe interval, seconds');assert.equal(interval.value,0);interval.value='30';interval.emit('input');assert(!save.disabled);
  const liveLimit=field(m.modal,'Live journal observations'),historyDays=field(m.modal,'Detailed history, days');
  liveLimit.value='2001';liveLimit.emit('input');assert(save.disabled);liveLimit.value='100';liveLimit.emit('input');
  historyDays.value='0';historyDays.emit('input');assert(save.disabled);historyDays.value='2';historyDays.emit('input');assert(!save.disabled);
  const monitorSave=click(save);click(save);assert.equal(m.calls.length,1);assert.equal(m.calls[0].args[0],30);assert.deepEqual(Array.from(m.calls[0].args.slice(4)),[100,2]);m.finish({saved:false});await monitorSave;
  m=make();c=m.ctx;c.monitorPreferences({settings:{live_log_limit:1500,history_days:1}});assert.equal(field(m.modal,'Live journal observations').value,1500);assert.equal(field(m.modal,'Detailed history, days').value,1);
  // Recovery review cannot convert exponent syntax into an accepted integer.
  m=make();c=m.ctx;c.recoveryWizard({settings:{}});const failures=field(m.modal,'Consecutive failures before switching (3–10)');failures.value='3e0';failures.emit('input');save=button(m.modal,'Next');assert(save.disabled);click(save);assert.equal(m.calls.length,0);assert(field(m.modal,'Return policy'));
  c.setupWizard({settings:{telegram_configured:false}},'telegram');assert(button(m.modal,'Next').disabled);assert(m.modal.textContent.includes('No stored token is available.'));
  // The actual builder embeds the helper and its visible validation styles.
  const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');assert(builder.includes("/'fool_guard.inc.js').read_text"));assert(builder.includes('.hv-fool-invalid'));
  console.log('PASS: '+Object.keys(c.FOOL_RANGES).length+' range contracts, strict numeric/text validation, bilingual errors, no secret echo, redraw single-flight/countdown, validation-lock composition, one-shot confirmation, speed/monitor/recovery integration and builder wiring');
})().catch(error=>{console.error(error);process.exitCode=1;});
