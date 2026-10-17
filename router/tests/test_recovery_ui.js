const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.value=attrs.value||'';this.checked=false;this.addEventListener=(event,fn)=>{this.attrs[event]=fn;};this.children=[];this.appendChild=child=>this.children.push(child);(Array.isArray(children)?children:[children]).forEach(this.appendChild);this.setAttribute=(k,v)=>this.attrs[k]=v;this.getAttribute=k=>this.attrs[k];}}
function walk(n){return n instanceof Node?[n,...n.children.flatMap(walk)]:[];}
let modal,calls=[],reloads=0;
const context={RECOVERY_PRESETS:JSON.parse(fs.readFileSync('router/files/usr/lib/homensai-vpn/recovery_presets.json','utf8')),E:(...args)=>new Node(...args),bi:en=>en,locale:'en',ui:{showModal:(_,children)=>modal=new Node('modal',{},children),hideModal:()=>modal=null,addNotification:()=>{}},window:{location:{reload:()=>reloads++}},rpc:{declare:spec=>(...args)=>{calls.push({spec,args});return Promise.resolve(spec.method==='priority_preview'?{accepted:true,revision:'a'.repeat(64),rows:[{profile:'b',name:'B',protocol:'wireguard',channel:'Reserve',enabled:true},{profile:'a',name:'A',protocol:'openvpn',channel:'Main',enabled:true}]}:{saved:true});}}};
vm.createContext(context);vm.runInContext(fs.readFileSync('router/recovery_panel.inc.js','utf8'),context);vm.runInContext(fs.readFileSync('router/speed_panel.inc.js','utf8'),context);
const field=label=>walk(modal).find(n=>n.attrs['aria-label']===label);
async function click(label){const button=walk(modal).find(n=>n.tag==='button'&&n.children.includes(label));assert(button,label);await button.attrs.click({currentTarget:button,target:button});}
(async()=>{
 context.recoveryWizard({settings:{}});field('Consecutive failures before switching (3–10)').value='2';await click('Next');assert.equal(calls.length,0);assert(field('Return policy'));
 field('Consecutive failures before switching (3–10)').value='4';await click('Next');await click('Save recovery settings');assert.equal(calls[0].spec.method,'setup_recovery');assert.equal(calls[0].args[0],4);assert.equal(calls[0].args[4],'healthy_primary');
 await context.reviewPriorities(['b','a']);assert.equal(calls[1].spec.method,'priority_preview');await click('Apply priorities');assert.equal(calls[2].spec.method,'priority_apply');assert.equal(calls[2].args[1],'a'.repeat(64));assert.equal(reloads,2);
 const now=Date.now()/1000;let selected;context.reviewPriorities=ids=>selected=ids;context.prioritySelections={a:true,b:true};
 const result=id=>({id,time:now,name:id,protocol:'openvpn',download:{mbps:id==='a'?100:50},upload:{mbps:20}});
 const panel=context.speedPanel({profiles:[{id:'a',name:'A',interface:'wg0',code:null},{id:'b',name:'B',interface:'wg1',code:null}],speed_tests:{results:[result('b'),result('a')]}},{settings:{}},'latest',()=>{});
 const button=walk(panel).find(n=>n.tag==='button'&&n.children.includes('Review recommended priorities'));await button.attrs.click();assert.deepEqual(Array.from(selected),['a','b']);
 console.log('PASS: recovery validation/review, exact save RPC, priority review/apply and measured rank order');
})().catch(error=>{console.error(error);process.exitCode=1;});
