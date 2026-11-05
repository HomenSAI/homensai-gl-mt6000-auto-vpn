// Owner 01.11.2026: choosing a recovery preset fills every field at once, visibly (changed fields are marked and
// listed); "Default values" resets every field; typing a value returns the select to Custom.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=Object.assign({},attrs);this.value=attrs.value||'';this.children=[];this.handlers={};
  (Array.isArray(children)?children:[children]).forEach(c=>{if(c!=null)this.children.push(c);});}
  appendChild(c){this.children.push(c);return c;} setAttribute(k,v){this.attrs[k]=v;} getAttribute(k){return this.attrs[k];}
  addEventListener(e,f){(this.handlers[e]=this.handlers[e]||[]).push(f);} emit(e){(this.handlers[e]||[]).forEach(f=>f({currentTarget:this,target:this}));}}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const text=n=>typeof n==='string'?n:n instanceof Node?n.children.map(text).join(''):'';
let modal;
const ctx={RECOVERY_PRESETS:JSON.parse(fs.readFileSync('router/files/usr/lib/homensai-vpn/recovery_presets.json','utf8')),E:(...a)=>new Node(...a),bi:en=>en,locale:'en',
  ui:{showModal:(_,c)=>modal=new Node('modal',{},c),hideModal:()=>modal=null,addNotification:()=>{}},window:{location:{reload(){}}},rpc:{declare:()=>()=>Promise.resolve({})},
  setTimeout:()=>0,console};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('router/fool_guard.inc.js','utf8'),ctx);vm.runInContext(fs.readFileSync('router/recovery_panel.inc.js','utf8'),ctx);
const field=label=>walk(modal).find(n=>n.attrs['aria-label']===label);
const L={interval:'Check interval, seconds (10–300)',attempt_limit:'Maximum switching attempts (1–10)',attempt_window:'Attempt counting window, minutes (1–15)',failures:'Consecutive failures before switching (3–10)',
  successes:'Reserve successes required (2–10)',cooldown:'Cooldown between attempts, seconds (60–1800)',min_dwell:'Minimum dwell time, seconds (60–3600)',primary_successes:'Primary successes before return (2–10)',primary_stable:'Primary stable interval, seconds (30–600)',rescue_stable:'If the reserve failed, seconds (0–60)'};
const defaults={interval:10,attempt_limit:3,attempt_window:15,failures:3,successes:2,cooldown:60,min_dwell:60,primary_successes:2,primary_stable:120,rescue_stable:10};  // 03.11.2026: 120 s + rescue 10 s
ctx.recoveryWizard({settings:{interval:40,recovery_attempt_limit:6,recovery_attempt_window:9,recovery_failures:7}});
assert.equal(field('Recovery preset').value,'');
for(const name of Object.keys(ctx.RECOVERY_PRESETS)){
  const sel=field('Recovery preset');sel.value=name;sel.emit('change');
  const want=Object.assign({},defaults,ctx.RECOVERY_PRESETS[name]);
  for(const key of Object.keys(L))assert.equal(Number(field(L[key]).value),want[key],name+' '+key);
  assert.equal(field('Return policy').value,want.return_policy,name+' policy');
  assert.equal(field('Recovery preset').value,name,'the select keeps the chosen preset');
}
// visible: the note lists the changed fields and the changed inputs are outlined
ctx.recoveryWizard({settings:{interval:40,recovery_attempt_limit:6}});
let sel=field('Recovery preset');sel.value='stability';sel.emit('change');
const note=walk(modal).find(n=>n.attrs['class']==='hv-preset-note');assert(note,'a status note after the preset');
assert(/Changed fields: .*Check interval.*Maximum switching attempts/.test(text(note)),text(note));
assert.equal(field(L.interval).attrs['data-preset-changed'],'1');assert.equal(field(L.attempt_window).attrs['data-preset-changed'],undefined,'unchanged field not marked');
// defaults reset every field; a typed value returns the select to Custom
field(L.failures).value='9';field(L.failures).emit('input');assert.equal(field('Recovery preset').value,'');
sel=field('Recovery preset');sel.value='defaults';sel.emit('change');
for(const key of Object.keys(L))assert.equal(Number(field(L[key]).value),defaults[key],'defaults '+key);
assert.equal(field('Return policy').value,'healthy_primary');
console.log('PASS: every recovery preset fills all fields visibly; defaults reset every field');
