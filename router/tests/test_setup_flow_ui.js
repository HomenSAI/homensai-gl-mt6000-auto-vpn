const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.value=attrs.value||'';this.disabled=attrs.disabled!=null&&attrs.disabled!==false;this.checked=false;(Array.isArray(children)?children:[children]).forEach(n=>this.appendChild(n));}
 appendChild(n){this.children.push(n);return n;} setAttribute(k,v){this.attrs[k]=v;}
 querySelectorAll(selector){const tags=selector.split(',').map(v=>v.trim());return walk(this).filter(n=>tags.includes(n.tag));}
}
Node.prototype.addEventListener=function(event,fn){this.attrs[event]=fn;};
function walk(n){return n instanceof Node?[n,...n.children.flatMap(walk)]:[];}
const source=fs.readFileSync('router/setup_wizard.inc.js','utf8');
function make(options={}){
 let modal=null,reloads=0,calls=[],notes=[],resolveSave,rejectSave,resolveCheck;
 const context={E:(...a)=>new Node(...a),bi:en=>en,ui:{showModal:(title,body)=>modal=new Node('modal',{},body),hideModal:()=>modal=null,addNotification:(_,node)=>notes.push(node)},window:{location:{reload:()=>reloads++}},rpc:{declare:spec=>(...args)=>{
  calls.push({spec,args});
  if(spec.method==='setup_check')return options.checkPending?new Promise(r=>resolveCheck=r):Promise.resolve(options.check===undefined?{passed:true}:options.check);
  if(options.pending)return new Promise((resolve,reject)=>{resolveSave=resolve;rejectSave=reject;});
  return Promise.resolve(options.save===undefined?{saved:true}:options.save);
 }}};
 context.setTimeout=function(){return 0;};vm.createContext(context);vm.runInContext(fs.readFileSync('router/fool_guard.inc.js','utf8'),context);vm.runInContext(source,context);
 function button(name){const node=walk(modal).find(n=>n.tag==='button'&&n.children.includes(name));assert(node,'missing '+name);return node;}
 async function click(name){const node=button(name);return node.attrs.click({target:node});}
 return {context,button,click,get modal(){return modal;},get reloads(){return reloads;},get calls(){return calls;},get notes(){return notes;},get resolveSave(){return resolveSave;},get rejectSave(){return rejectSave;},get resolveCheck(){return resolveCheck;}};
}
const inventory={settings:{plan_source:'a',plan_target:'b',interval:30,native_duration:10,native_session_loss:true},profiles:[{id:'a',name:'Primary',protocol:'openvpn'},{id:'b',name:'Reserve',protocol:'wireguard'}]};
async function ready(value){value.context.setupWizard(inventory,'system');await Promise.resolve();await Promise.resolve();await value.click('Next');await value.click('Next');assert(value.button('Save configuration'));}
(async()=>{
 let value=make({pending:true});await ready(value);const review=value.modal;
 assert(walk(review).some(n=>n.tag==='td'&&n.children.includes('Primary')),'review must show actual edited metadata');
 assert(walk(review).some(n=>n.tag==='p'&&n.children.includes('Calls/sessions may reconnect: Allowed')),'review must show reconnection choice');
 const pending=value.click('Save configuration');
 for(const label of ['Back','Cancel','Save configuration'])assert.equal(value.button(label).disabled,true,label+' must visibly block while save pending');
 await value.click('Back');await value.click('Cancel');await value.click('Save configuration');
 assert.strictEqual(value.modal,review,'pending navigation must not replace review');assert.equal(value.calls.filter(c=>c.spec.method==='setup_system').length,1,'no duplicate request');
 value.rejectSave(new Error('PRIVATE_FAILURE_DETAILS'));await pending;
 assert.equal(value.reloads,0);assert.strictEqual(value.modal,review);
 for(const label of ['Back','Cancel','Save configuration'])assert.equal(value.button(label).disabled,false,'failed save must allow retry/cancel');
 assert(!JSON.stringify(value.notes).includes('PRIVATE_FAILURE_DETAILS'),'do not echo private rejection detail');
 await value.click('Cancel');assert.equal(value.modal,null);
 for(const reply of [null,{}, {saved:'true'},{saved:'false',code:'private token = example'}]){
  value=make({save:reply});await ready(value);await value.click('Save configuration');assert(value.modal,'unverified reply must retain draft');assert.equal(value.reloads,0);assert(!JSON.stringify(value.notes).includes('private token'));
 }
 for(const reply of [null,{}, {passed:'true'},{passed:false}]){
  value=make({check:reply});value.context.setupWizard(inventory,'system');await Promise.resolve();await Promise.resolve();assert.equal(value.button('Next').disabled,true,'unknown check result must not unlock save');
 }
 value=make({checkPending:true});value.context.setupWizard(inventory,'system');await value.click('Cancel');value.resolveCheck({passed:true});await Promise.resolve();await Promise.resolve();assert.equal(value.modal,null,'late check must not reopen cancelled wizard');
 value=make();await ready(value);await value.click('Save configuration');assert.equal(value.reloads,1);assert.equal(value.modal,null);
 const save=value.calls.find(c=>c.spec.method==='setup_system');assert(!save.spec.params.includes('native_enabled'));assert(!value.calls.some(c=>c.spec.method.startsWith('native_')),'wizard save cannot start Auto');
 console.log('PASS: system wizard pending navigation, duplicate save, private error redaction, typed replies, late cancellation and metadata-only success');
})().catch(error=>{console.error(error);process.exitCode=1;});
