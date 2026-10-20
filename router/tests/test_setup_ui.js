const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.value=attrs.value||'';this.disabled=false;this.checked=false;this.appendChild=child=>{this.children.push(child);return child;};this.setAttribute=(k,v)=>this.attrs[k]=v;(Array.isArray(children)?children:[children]).forEach(this.appendChild);}
 querySelectorAll(){return walk(this).filter(n=>n.tag==='input'||n.tag==='select');}
}
Node.prototype.addEventListener=function(event,fn){this.attrs[event]=fn;};
function walk(n){return n instanceof Node?[n,...n.children.flatMap(walk)]:[];}
let modal,calls=[],reloads=0,notes=[];
const context={E:(...a)=>new Node(...a),bi:(en)=>en,ui:{showModal:(title,body)=>{modal=new Node('modal',{},body);},hideModal:()=>{modal=null;},addNotification:(_,n)=>notes.push(n)},rpc:{declare:spec=>(...args)=>{calls.push({spec,args});return Promise.resolve({saved:true});}},window:{location:{reload:()=>reloads++}}};
context.setTimeout=function(){return 0;};vm.createContext(context);vm.runInContext(fs.readFileSync('router/fool_guard.inc.js','utf8'),context);vm.runInContext(fs.readFileSync('router/setup_wizard.inc.js','utf8'),context);
function field(label){return walk(modal).find(n=>n.attrs['aria-label']===label);}
function button(label){return walk(modal).find(n=>n.tag==='button'&&n.children.includes(label));}
async function click(label){const b=button(label);assert(b,label);await b.attrs.click({target:b});}
(async()=>{
 const inventory={settings:{telegram_configured:true,telegram_destination:'@example_channel',telegram_enabled:true,telegram_interval:120,telegram_schedule:'daily',telegram_hour:7,telegram_weekly:true,telegram_monthly:false}};
 context.setupWizard(inventory,'telegram');
 assert.equal(field('Bot token (leave blank to keep the stored token)').value,'');
 await click('Next');
 assert.equal(field('Channel / destination ID').value,'@example_channel');
 assert.equal(field('Schedule').value,'daily');assert.equal(field('Monthly summary on day 1').checked,false);
 field('Daily hour, Europe/Berlin (0–23)').value='24';await click('Next');assert(field('Schedule'),'invalid hour must retain step');assert.equal(calls.length,0);
 field('Daily hour, Europe/Berlin (0–23)').value='8';field('Monthly summary on day 1').checked=true;
 await click('Next');await click('Save configuration');
 assert.equal(calls.length,1);assert.equal(calls[0].spec.method,'setup_telegram');
 assert.deepEqual(Array.from(calls[0].spec.params),['token','chat','enabled','interval','schedule','hour','weekly','monthly','items']);
 assert.deepEqual(Array.from(calls[0].args),['','@example_channel',true,120,'daily',8,true,true,'servers,events,traffic,delta,controller,controller_events,controller_totals,gaps']);assert.equal(reloads,1);
 context.setupWizard(inventory,'telegram');await click('Cancel');assert.equal(calls.length,1);assert.equal(modal,null);
 // The stored token can be deleted only after an explicit confirmation, with a typed own RPC and no arguments.
 context.window.confirm=()=>false;context.setupWizard(inventory,'telegram');await click('Delete the stored token');assert.equal(calls.length,1);
 context.window.confirm=()=>true;await click('Delete the stored token');
 assert.equal(calls.length,2);assert.equal(calls[1].spec.method,'telegram_forget');assert.deepEqual(Array.from(calls[1].args),[]);
 context.setupWizard({settings:{telegram_configured:false}},'telegram');assert(!button('Delete the stored token'),'no delete button without a stored token');
 console.log('PASS: Telegram wizard stored defaults, private blank token, validation, calendar RPC and cancellation');
})().catch(e=>{console.error(e);process.exitCode=1;});
