const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.listeners={};this.value=attrs.value||'';this.checked=false;this.disabled=!!attrs.disabled;this.textContent='';(Array.isArray(children)?children:[children]).forEach(c=>this.appendChild(c));}
 appendChild(n){if(n!==null&&n!==undefined)this.children.push(n);return n;}
 removeChild(n){this.children.splice(this.children.indexOf(n),1);return n;}
 get firstChild(){return this.children[0]||null;}
 setAttribute(k,v){this.attrs[k]=String(v);}
 addEventListener(k,f){(this.listeners[k]||(this.listeners[k]=[])).push(f);}
 fire(k='click'){let r;if(this.attrs[k])r=this.attrs[k]({target:this,currentTarget:this});for(const f of this.listeners[k]||[])r=f({target:this,currentTarget:this});return r;}
}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const text=n=>n instanceof Node?[n.textContent,...n.children.map(text)].join(' '):String(n);
const copy=n=>JSON.parse(JSON.stringify(n));
function inventory(){return {settings:{plan_source:'wireguard:a',plan_target:'openvpn:b',native_session_loss:false,interval:30,native_duration:10,appearance_design:'c',history_days:7,telegram_configured:true},profiles:[{id:'wireguard:a',section:'a',name:'Primary',protocol:'wireguard',interface:'wgclient1',vendor_tunnel_id:'wireguard:wgclient1'},{id:'openvpn:b',section:'b',name:'Reserve',protocol:'openvpn',interface:'ovpnclient1',vendor_tunnel_id:'openvpn:ovpnclient1'}],servers:[{profile:'wireguard:a',name:'Custom A',channel:'special group',priority:7,enabled:true},{profile:'openvpn:b',name:'Custom B',channel:'backup group',priority:8,enabled:true}]};}
function fixture(inv=inventory()){
 let modal=null,reloads=0,response={saved:true},setup={passed:true},fresh=copy(inv),transport=false,pending=null;
 const listeners={};
 const calls=[],opened=[];
 const c={URL,JSON,Object,Array,Number,Promise,Error,bi:(a)=>a,E:(...args)=>new Node(...args),
  FOOL_RANGES:{},window:{location:{reload:()=>reloads++},addEventListener:(key,fn)=>(listeners[key]||(listeners[key]=[])).push(fn),removeEventListener:(key,fn)=>listeners[key]=(listeners[key]||[]).filter(x=>x!==fn)},ui:{showModal:(_,nodes)=>modal=new Node('modal',{},nodes),hideModal:()=>modal=null},
  setupCheckRequest:()=>{calls.push({method:'setup_check'});return pending?pending:Promise.resolve(setup);},
  inventoryCall:()=>{calls.push({method:'inventory'});return Promise.resolve(fresh);},
  rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args:copy(args),params:copy(spec.params)});return transport?Promise.reject(new Error('private transport message')):Promise.resolve(response);}},
  openOnboardingSettings:(_,__,step)=>opened.push(step)
 };
 vm.createContext(c);
 const onboarding=fs.readFileSync('router/onboarding_panel.inc.js','utf8');
 vm.runInContext(onboarding.slice(0,onboarding.indexOf('function onboardingPairChannelLabel')),c);
 vm.runInContext("function onboardingPairChannelLabel(p){return p.name+' · '+p.protocol;}",c);
 vm.runInContext(fs.readFileSync('router/minimum_settings.inc.js','utf8'),c);
 const root=c.renderMinimumSettings(inv,{time:1000},()=>({time:1000}));
 const field=k=>{const n=walk(root).find(n=>n.attrs['data-minimum-field']===k);assert(n,'field '+k);return n;};
 const button=k=>{const n=walk(modal||root).find(n=>n.attrs['data-minimum-action']===k);assert(n,'action '+k);return n;};
 const set=(k,v)=>{const n=field(k);if(k==='session_loss')n.checked=v;else n.value=v;n.fire('change');};
 return {c,root,calls,opened,field,button,set,listeners,get modal(){return modal;},get reloads(){return reloads;},set response(v){response=v;},set setup(v){setup=v;},set fresh(v){fresh=v;},set transport(v){transport=v;},set pending(v){pending=v;}};
}
(async()=>{
 let f=fixture();assert.equal(f.calls.length,0,'render performs no RPC');assert.equal(f.root.attrs['data-hv-page'],'settings','form follows page visibility');assert(f.button('save').disabled);assert(f.button('cancel').disabled);assert(f.c.minimumSettingsCanLeave());
 const app={isConnected:true};f.c.installMinimumSettingsGuard(app);f.c.installMinimumSettingsGuard(app);assert.equal(f.listeners.beforeunload.length,1,'guard installation is idempotent');
 let prevented=0;const event={preventDefault(){prevented++;}};f.listeners.beforeunload[0](event);assert.equal(prevented,0,'clean form permits unload');f.set('session_loss',true);f.listeners.beforeunload[0](event);assert.equal(prevented,1);assert.equal(event.returnValue,'');app.isConnected=false;f.listeners.beforeunload[0](event);assert.equal(prevented,1,'detached app does not block another screen');f.c.MINIMUM_SETTINGS_GUARD();assert.equal(f.listeners.beforeunload.length,0);f.button('cancel').fire();
 f.set('source','openvpn:b');assert(f.button('save').disabled,'same profile invalid');assert(f.c.minimumSettingsDirty());f.set('target','wireguard:a');assert(!f.button('save').disabled);f.set('session_loss',true);
 const draftRoot=f.root;f.c.renderMinimumSettings(inventory(),{time:1010},()=>({time:1010}));assert.strictEqual(f.c.MINIMUM_SETTINGS_SESSION.host,draftRoot);assert.equal(f.field('source').value,'openvpn:b','polling retains selected draft');assert.equal(f.field('session_loss').checked,true);
 await f.button('save').fire();assert(f.modal,'save requires review');assert.equal(f.calls.length,0,'review alone writes nothing');assert(text(f.modal).includes('Reserve'));await f.button('confirm-save').fire();
 assert.equal(f.reloads,1);assert.equal(f.c.minimumSettingsDirty(),false);assert.deepEqual(f.calls.map(x=>x.method),['setup_check','inventory','setup_system']);
 const write=f.calls[2];assert.deepEqual(write.params,['source','target','interval','duration','session_loss','servers']);assert.equal(write.args[0],'openvpn:b');assert.equal(write.args[1],'wireguard:a');assert.equal(write.args[4],true);assert.deepEqual(write.args[5],inventory().servers);assert(!JSON.stringify(write.args).includes('telegram'));assert(!f.calls.some(c=>/start|stop|native|speed/.test(c.method)));
 f=fixture();f.set('session_loss',true);f.button('cancel').fire();assert(!f.c.minimumSettingsDirty());assert.equal(f.field('session_loss').checked,false);assert.equal(f.calls.length,0);
 // Fresh unrelated settings are kept; only a changed selected pair/consent invalidates the draft.
 f=fixture();f.set('session_loss',true);const fresh=inventory();fresh.settings.interval=77;fresh.servers[0].priority=17;f.fresh=fresh;await f.button('save').fire();await f.button('confirm-save').fire();assert.equal(f.calls[2].args[2],77);assert.equal(f.calls[2].args[5][0].priority,17);
 f=fixture();f.set('session_loss',true);const changed=inventory();changed.settings.plan_source='openvpn:b';changed.settings.plan_target='wireguard:a';f.fresh=changed;await f.button('save').fire();await f.button('confirm-save').fire();assert.equal(f.reloads,0);assert(!f.calls.some(c=>c.method==='setup_system'));assert(text(f.root).includes('SETUP-CONFIG-CHANGED'));assert(f.c.minimumSettingsDirty());
 // Writer or readiness failure must preserve the draft and expose only allowlisted error codes.
 for(const failure of ['response','transport','check']){
  f=fixture();f.set('session_loss',true);if(failure==='response')f.response={saved:false,code:'SETUP-STOP-FIRST'};if(failure==='transport')f.transport=true;if(failure==='check')f.setup={passed:false};await f.button('save').fire();await f.button('confirm-save').fire();assert.equal(f.reloads,0);assert(f.c.minimumSettingsDirty());assert.equal(f.field('session_loss').checked,true);assert(!text(f.root).includes('private transport message'));assert(!f.button('save').disabled);
 }
 f=fixture();f.set('session_loss',true);let resolve;f.pending=new Promise(r=>resolve=r);await f.button('save').fire();const confirm=f.button('confirm-save'),pending=confirm.fire();assert(f.c.minimumSettingsBusy());assert(f.field('source').disabled);assert(!f.c.minimumSettingsCanLeave());confirm.fire();resolve({passed:true});await pending;assert.equal(f.calls.filter(c=>c.method==='setup_system').length,1,'duplicate confirmation cannot write twice');
 f=fixture({error:'RPC-UNAVAILABLE'});f.set('session_loss',true);assert(f.button('save').disabled);assert.equal(f.calls.length,0);
 // Leave flow is explicit and writes nothing unless the reviewed Save is confirmed.
 f=fixture();let navigated=0;assert(f.c.minimumSettingsRequestLeave(()=>navigated++));assert.equal(navigated,1);f.set('session_loss',true);assert.equal(f.c.minimumSettingsRequestLeave(()=>navigated++),false);assert.equal(navigated,1);let discard=walk(f.modal).find(n=>n.tag==='button'&&text(n).trim()==='Discard changes');discard.fire();assert.equal(navigated,2);assert(!f.c.minimumSettingsDirty());assert.equal(f.calls.length,0);
 f=fixture();f.set('session_loss',true);const open=walk(f.root).find(n=>n.attrs['data-minimum-settings-open']==='monitor');open.fire();assert.equal(f.opened.length,0);discard=walk(f.modal).find(n=>n.tag==='button'&&text(n).trim()==='Discard changes');discard.fire();assert.deepEqual(f.opened,['monitor']);
 f=fixture();f.set('session_loss',true);let savedNavigation=0;f.c.minimumSettingsRequestLeave(()=>{assert(f.c.minimumSettingsCanLeave(),'confirmed save clears guard before navigation callback');savedNavigation++;});const leaveSave=walk(f.modal).find(n=>n.tag==='button'&&text(n).trim()==='Save changes');leaveSave.fire();await f.button('confirm-save').fire();assert.equal(savedNavigation,1);assert.equal(f.reloads,1);
 console.log('PASS: persistent pair draft, explicit review, exact setup_system fields, fresh metadata, conflict/readiness/error guards, no Auto writes and save/discard/stay navigation.');
})().catch(e=>{console.error(e);process.exitCode=1;});
