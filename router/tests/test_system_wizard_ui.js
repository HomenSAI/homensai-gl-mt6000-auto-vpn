const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.value=attrs.value||'';this.checked=false;this.disabled=attrs.disabled!=null;this.appendChild=n=>(this.children.push(n),n);this.setAttribute=(k,v)=>this.attrs[k]=v;(Array.isArray(children)?children:[children]).forEach(this.appendChild);}querySelectorAll(){return walk(this).filter(n=>['input','select'].includes(n.tag));}}
Node.prototype.addEventListener=function(event,fn){this.attrs[event]=fn;};
function walk(n){return n instanceof Node?[n,...n.children.flatMap(walk)]:[];}
let modal,calls=[],reloads=0,notes=[],checkResolve,saveResolve,saveMode='ok';
const context={E:(...a)=>new Node(...a),bi:en=>en,ui:{showModal:(_,body)=>modal=new Node('modal',{},body),hideModal:()=>modal=null,addNotification:(_,n)=>notes.push(n)},rpc:{declare:spec=>(...args)=>{if(spec.method==='setup_check')return new Promise(resolve=>checkResolve=resolve);calls.push({method:spec.method,args});return saveMode==='fail'?Promise.reject(new Error('fixture failure')):saveMode==='pending'?new Promise(resolve=>saveResolve=resolve):Promise.resolve({saved:true});}},window:{location:{reload:()=>reloads++}}};
context.setTimeout=function(){return 0;};vm.createContext(context);vm.runInContext(fs.readFileSync('router/fool_guard.inc.js','utf8'),context);vm.runInContext(fs.readFileSync('router/setup_wizard.inc.js','utf8'),context);
const field=(label,index=0)=>walk(modal).filter(n=>n.attrs['aria-label']===label)[index];
const button=label=>walk(modal).find(n=>n.tag==='button'&&n.children.includes(label));
async function click(label){let b=button(label);assert(b,label);return b.attrs.click({target:b});}
const inventory={settings:{plan_source:'a',plan_target:'b',interval:30,native_duration:10},profiles:[{id:'a',name:'Alpha',protocol:'openvpn'},{id:'b',name:'Beta',protocol:'wireguard'}],servers:[{profile:'a',name:'Alpha',channel:'Main',priority:1,enabled:true},{profile:'b',name:'Beta',channel:'Backup',priority:2,enabled:true}]};
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 context.setupWizard(inventory,'system');assert(button('Next').disabled);assert(field('Primary VPN').disabled);await click('Cancel');checkResolve({passed:true});await flush();assert.equal(modal,null,'late readiness must not reopen cancelled wizard');assert.equal(calls.length,0);
 context.setupWizard(inventory,'system');checkResolve({passed:false});await flush();assert(button('Next').disabled);await click('Cancel');
 context.setupWizard(inventory,'system');checkResolve({passed:true});await flush();
 field('Reserve VPN').value='a';await click('Next');assert(field('Primary VPN'));assert.equal(calls.length,0);
 field('Reserve VPN').value='b';field('Probe interval, seconds (10–300)').value='9';await click('Next');assert(field('Primary VPN'));
 field('Probe interval, seconds (10–300)').value='30';await click('Next');
 field('Monitor this server',1).checked=false;await click('Next');assert(field('Display name'),'disabled reserve cannot advance');
 field('Monitor this server',1).checked=true;field('Display name').value='bad\nname';await click('Next');assert(field('Display name'));
 field('Display name').value='Operator Alpha';await click('Next');assert(button('Save configuration'));assert.equal(calls.length,0,'review must not save');
 saveMode='fail';await click('Save configuration');assert.equal(reloads,0);assert(modal,'RPC failure keeps review and allows retry');assert.equal(calls.length,1);
 saveMode='pending';let saving=click('Save configuration');await click('Cancel');assert(modal,'in-flight commit cannot be represented as cancelled');await click('Save configuration');assert.equal(calls.length,2,'double click must not duplicate writer');saveResolve({saved:true});await saving;assert.equal(reloads,1);assert.equal(modal,null);
 const save=calls[1];assert.equal(save.method,'setup_system');assert.equal(save.args[0],'a');assert.equal(save.args[1],'b');assert.equal(save.args[5][0].name,'Operator Alpha');assert.equal(save.args[5][1].enabled,true);
 console.log('PASS: system wizard readiness/cancel, ranges, enabled pair, review, RPC failure/retry and single-flight save');
})().catch(e=>{console.error(e);process.exitCode=1;});
