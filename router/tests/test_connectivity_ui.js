const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:(e)=>e};vm.createContext(c);vm.runInContext(fs.readFileSync('router/connectivity_panel.inc.js','utf8'),c);
const id='a'.repeat(32),request={request_id:id,requested_at:100};
const scan={...request,state:'COMPLETED',measurement_request_id:id,measured_at:101,finished_at:102,checked:2,failed:1};
assert.equal(c.connectivityModel({scan:{...request,state:'QUEUED'}},request,102).state,'QUEUED');
assert.equal(c.connectivityModel({scan:{...request,state:'RUNNING'}},request,102).state,'RUNNING');
assert.equal(c.connectivityModel({scan:{...scan,measurement_request_id:'old'}},request,102).state,'UNAVAILABLE');
assert.equal(c.connectivityModel({scan},request,102).state,'COMPLETED');
assert.equal(c.connectivityModel({scan,measurement_request_id:null},request,600).state,'COMPLETED');
assert.equal(c.connectivityModel({scan:{...request,state:'QUEUED'}},request,401).state,'FAILED');
assert.equal(c.connectivityModel({scan:{...scan,checked:0,failed:0}},request,102).state,'EMPTY');
assert.equal(c.connectivityModel({scan,rpc_error:true},request,102).state,'UNAVAILABLE');
assert.equal(c.connectivityModel({scan:{...scan,failed:3}},request,102).state,'UNAVAILABLE');
assert.equal(c.connectivityModel({scan:{...scan,request_id:'b'.repeat(32)}},request,102).state,'QUEUED');
console.log('PASS: correlated check lifecycle, old snapshot rejection, empty/failed counts, RPC and timeout states');

// Labels and colors follow each actual profile, even when the failed primary is second in the probe list.
class Cell{constructor(tag,attrs,text){this.tag=tag;this.attrs=attrs||{};this.children=Array.isArray(text)?text:[];this.text=typeof text==='string'?text:'';}appendChild(n){this.children.push(n);}get firstChild(){return this.children[0];}removeChild(n){this.children.splice(this.children.indexOf(n),1);}setAttribute(k,v){this.attrs[k]=v;}}
c.E=(...a)=>new Cell(...a);c.Date=class extends Date{static now(){return 100000;}};c.locale='en';c.profileHealth=p=>({state:p.code?'failed':'healthy'});
c.connectivityControl={button:new Cell('button'),message:new Cell('p'),bar:new Cell('div'),next:new Cell('p'),settings:{plan_source:'p',plan_target:'r'}};
c.updateConnectivityCheck({time:100,profiles:[{id:'r',interface:'ovpnclient1',time:99},{id:'p',interface:'wgclient1',time:99,code:'DNS-001'}]});
const cells=c.connectivityControl.bar.children;assert.equal(cells[0].children[0].text,'Primary channel');assert.equal(cells[1].children[0].text,'Reserve channel');assert(!cells[0].children[1].attrs.class.includes('cell-ok'));assert(cells[1].children[1].attrs.class.includes('cell-ok'));
console.log('PASS: primary/reserve progress labels preserve actual health assignment');
