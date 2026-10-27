const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(x=>x!=null);this.disabled=false;}
 setAttribute(k,v){this.attrs[k]=v;}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
 text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join(' ');}
 click(){if(!this.disabled&&this.attrs.click)return this.attrs.click();}
}
function fixture(lang){
 const calls=[],pending=[],notices=[];let modal=null;
 const c={bi:(en,ru)=>lang==='ru'?ru:en,E:(...args)=>new N(...args),rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return new Promise((resolve,reject)=>pending.push({resolve,reject}));}},ui:{showModal:(title,nodes)=>modal=new N('modal',{},nodes),hideModal:()=>modal=null,addNotification:(_,node)=>notices.push(node)}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('router/preparation_control.inc.js','utf8'),c);
 return {c,calls,pending,notices,modal:()=>modal};
}
const plan=action=>({accepted:true,action,board:'mt6000',revision:'a'.repeat(64),control_revision:'b'.repeat(32),already_done:false,restart_required:false});
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 for(const lang of ['en','ru']){
  for(const [code,action] of Object.entries({'PREP-WGCLIENT1-AUTOSTART':'wg-autostart','PREP-OVPNCLIENT1-AUTOSTART':'ovpn-autostart','PREP-STOCK-VPN-BOOT':'vpn-boot','PREP-SFE-BOOT':'sfe-boot','PREP-HNAT-CONFIG':'hnat','FLOW-OFFLOAD-ENABLED':'flow-offload','PREP-SFE-AUTOLOAD':'sfe-autoload'})){
   const f=fixture(lang),{c}=f,host=c.renderPreparationButtons(code),button=host.all().find(n=>n.tag==='button');
   assert.equal(f.calls.length,0,'render and polling cannot change router settings');
   const preview=button.click();button.click();assert.equal(f.calls.length,1,'preview single flight');assert.equal(f.calls[0].method,'preparation_preview');assert.equal(f.calls[0].args[0],action);
   f.pending.shift().resolve(plan(action));await preview;
   assert(f.modal().text().includes('MT6000'),'actual router model shown before writing');
   assert(f.modal().text().includes(lang==='ru'?'Исходное значение':'original setting'));
   const apply=f.modal().all().find(n=>n.attrs['data-preparation-confirm']);assert(apply);
   const promise=apply.click();apply.click();assert.equal(f.calls.length,2,'one reviewed apply only');assert.equal(f.calls[1].method,'preparation_apply');assert.deepEqual(f.calls[1].args,[action,'a'.repeat(64),'b'.repeat(32)]);
   f.pending.shift().resolve({applied:true,verified:true,action,auto_started:false,restart_required:action==='flow-offload'});await promise;
   assert.equal(f.modal(),null);assert(f.notices.at(-1).text().includes(lang==='ru'?'проверена':'verified'));
   assert(!f.calls.some(call=>/native_|reboot|monitor_control/.test(call.method)),'preparation never starts Auto or reboots');
  }
  {
   const f=fixture(lang),button=f.c.renderPreparationButtons('PREP-STOCK-VPN-BOOT').all().find(n=>n.tag==='button'),promise=button.click();
   f.pending.shift().resolve(plan('vpn-boot'));await promise;
   const staleApply=f.modal().all().find(n=>n.attrs['data-preparation-confirm']);f.modal().all().find(n=>n.tag==='button'&&!n.attrs['data-preparation-confirm']).click();
   staleApply.click();assert.equal(f.calls.length,1,'Cancel and retained old nodes never write');
  }
  for(const answer of [{accepted:false,code:'PREPARATION-RECOVERY-REQUIRED'},{...plan('wg-autostart'),revision:'invalid'},{...plan('wg-autostart'),board:'unknown'}]){
   const f=fixture(lang),button=f.c.renderPreparationButtons('PREP-WGCLIENT1-AUTOSTART').all().find(n=>n.tag==='button'),promise=button.click();
   f.pending.shift().resolve(answer);await promise;assert.equal(f.calls.length,1);assert.equal(f.modal(),null);assert(f.notices.length);
  }
  {
   const f=fixture(lang),button=f.c.renderPreparationButtons('PREP-WGCLIENT1-AUTOSTART').all().find(n=>n.tag==='button');
   let promise=button.click();f.pending.shift().resolve(plan('wg-autostart'));await promise;
   promise=f.modal().all().find(n=>n.attrs['data-preparation-confirm']).click();f.pending.shift().reject(Error('lost reply'));await promise;
   assert(f.notices.at(-1).text().includes('PREPARATION-WRITE-UNCONFIRMED'));assert.equal(f.calls.length,2,'lost reply never auto-retries');
  }
  {
   const f=fixture(lang),button=f.c.renderPreparationButtons('PREP-HNAT-CONFIG').all().find(n=>n.tag==='button'),promise=button.click();
   f.pending.shift().resolve({...plan('hnat'),already_done:true});await promise;
   assert(!f.modal().all().some(n=>n.attrs['data-preparation-confirm']),'already disabled does not offer another write');
  }
  assert.equal(fixture(lang).c.renderPreparationButtons('constructor'),null);
 }
 console.log('PASS: seven EN/RU preparation actions, actual-model review, Cancel, single-flight writes, stale/invalid/refused replies, no replay/automatic retry, no Auto Start/reboot and already-off no-op');
})().catch(e=>{console.error(e);process.exit(1);});
