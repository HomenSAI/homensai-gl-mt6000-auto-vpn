// BH3-01 (bug hunt third pass, 07.11.2026): LuCI's E(tag, attrs, child) puts a single non-array, non-node child into
// innerHTML ('' + child); only array items become text nodes. The module-local E wrapper (router/element_guard.inc.js,
// built into the shipped page) must therefore turn every scalar child into [String(child)], so a router string can never
// become markup. The doubles follow LuCI through router/tests/luci_dom_model.js and record every innerHTML assignment.
// Checked: the model itself (raw LuCI E does take the innerHTML branch), the wrapper rules, the shipped page's
// preparationNotice/collection notify with a payload code, a full approved-page render with hostile names, and the
// optional server-pick module (pick<N>.js, not shipped now) with hostile profile/server names even under a raw LuCI E.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const {luciE}=require('./luci_dom_model');
const {load,ROOT,app}=require('./approved_page');
const PAYLOAD='<img src=x onerror=alert(1)>';
const node=(tag,attrs)=>({tag,attrs,children:[],addEventListener(){},setAttribute(){},removeAttribute(){}});
const live=sinks=>sinks.filter(s=>/<img\b|<script\b/i.test(s.html));

// ---------- 1. the model is LuCI: a single scalar child goes to innerHTML, array items are text ----------
{
  const sinks=[],E=luciE(node,sinks);
  const a=E('p',{},PAYLOAD);assert.equal(a.innerHTML,PAYLOAD);assert.equal(sinks.length,1,'raw LuCI E: scalar child -> innerHTML');
  const b=E('p',PAYLOAD);assert.equal(b.innerHTML,PAYLOAD);assert.equal(b.attrs,null,'a non-object 2nd argument is the data');
  const c=E('p',{},[PAYLOAD,null]);assert.deepStrictEqual(c.children,[PAYLOAD,'null'],'array items are text nodes (null -> "null")');
  assert.equal(sinks.length,2);
}
console.log('PASS: the LuCI model takes the innerHTML branch for a single scalar child (as luci.js 21.02 dom.append)');

// ---------- 2. the wrapper rules (router/element_guard.inc.js over the LuCI model) ----------
function wrapped(guardSource){
  const sinks=[],ctx={console,Object,Array,String,Error};
  ctx.E=luciE(node,sinks);ctx.globalThis=ctx;vm.createContext(ctx);vm.runInContext(guardSource,ctx);
  return {E:ctx.E,sinks};
}
const GUARD=fs.readFileSync(path.join(ROOT,'router/element_guard.inc.js'),'utf8');
{
  const {E,sinks}=wrapped(GUARD);
  assert.deepStrictEqual(E('p',{},PAYLOAD).children,[PAYLOAD],'string child is text');
  assert.deepStrictEqual(E('p',{},42).children,['42'],'number child is text');
  assert.deepStrictEqual(E('p',{},false).children,['false'],'boolean child is text');
  assert.deepStrictEqual(E('p',PAYLOAD).children,[PAYLOAD],'E(tag, string) is text');
  assert.deepStrictEqual(E('p',7).children,['7'],'E(tag, number) is text');
  const inner=E('b',{},['x']);
  assert.strictEqual(E('p',{},inner).children[0],inner,'a node child passes through');
  let called=null;const fnNode=E('p',{},el=>{called=el;return ['y'];});
  assert.strictEqual(called,fnNode,'a function child is called by LuCI with the element');assert.deepStrictEqual(fnNode.children,['y']);
  assert.deepStrictEqual(E('p',{},null).children,[],'null child: nothing');
  assert.deepStrictEqual(E('p',{},undefined).children,[],'undefined child: nothing');
  assert.deepStrictEqual(E('p',{},['a',null,['b',[undefined,'c']]]).children,['a','b','c'],'arrays are flattened, null items dropped');
  assert.deepStrictEqual(E('p',{'class':'k'},'').children,[''],'empty string stays an (empty) text node');
  assert.deepStrictEqual(sinks,[],'the wrapper never lets LuCI use innerHTML');
}
// The pre-fix wrapper passed a scalar through: the model must catch it (otherwise this test would prove nothing).
{
  const before=GUARD.replace("return typeof value==='object'||typeof value==='function'?value:[String(value)];","return value;")
    .replace(/\n *if\(args\.length>=2&&args\[1\]!=null&&typeof args\[1\]!=='object'[^\n]*/,'');
  assert.notEqual(before,GUARD,'pre-fix variant built');
  const {E,sinks}=wrapped(before);E('p',{},PAYLOAD);E('p',PAYLOAD);
  assert.equal(live(sinks).length,2,'the model detects the pre-fix scalar pass-through');
}
console.log('PASS: the module E wrapper turns string/number/boolean children (also E(tag, text)) into text; nodes, functions, arrays, null as before');

// ---------- 3. the shipped page: the wrapper is built in, router codes in notices are text ----------
const PAGE=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/view/homensai-vpn/'+app.ui_module+'.js'),'utf8');
assert(PAGE.includes("return typeof value==='object'||typeof value==='function'?value:[String(value)];"),'the shipped page carries the BH3-01 wrapper');
{
  class N{constructor(t,a){this.tag=t;this.attrs=a||{};this.children=[];}
    all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
    text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join('');}
    appendChild(c){this.children.push(c);return c;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]==null?null:this.attrs[k];}
    addEventListener(){}removeAttribute(){}get style(){return {};}get classList(){return {add(){},remove(){},toggle(){}};}}
  const sinks=[],notes=[];
  const ctx={window:{localStorage:{getItem(){return null},setItem(){}},HomenS:{},location:{search:'',href:'http://x/',hash:''}},
    document:{createElementNS:(ns,t)=>new N(t),createElement:t=>new N(t),addEventListener(){}},localStorage:{getItem(){return null}},
    E:luciE((t,a)=>new N(t,a),sinks),URLSearchParams,URL,Intl,console,L:{},rpc:{declare:()=>()=>Promise.resolve({})},
    ui:{addNotification:(t,n)=>notes.push(n)},poll:{},view:{extend:o=>o}};
  ctx.location=ctx.window.location;vm.createContext(ctx);
  vm.runInContext(PAGE.slice(0,PAGE.lastIndexOf('return view.extend({')),ctx);
  ctx.preparationNotice(PAYLOAD,false);                 // dashboard: E('strong',{},code+' · ') with the preparation reply code
  ctx.collectionModel({}).notify(PAYLOAD);              // help module: model.notify((r&&r.code)||...) -> E('p',{},text)
  assert.equal(notes.length,2);
  assert(notes[0].text().startsWith(PAYLOAD+' · '),'the code is shown as text: '+notes[0].text());
  assert.equal(notes[1].text(),PAYLOAD,'the notify text is a text node');
  assert.deepStrictEqual(sinks,[],'no innerHTML from a router code: '+JSON.stringify(sinks));
}
console.log('PASS: the shipped page shows router codes in preparation and collection notices as text (no innerHTML)');

// ---------- 4. the approved page renders with hostile names and never reaches innerHTML through E ----------
for(const lang of ['ru','en']){
  const p=load({lang,mutate:({inventory,status})=>{
    inventory.servers.forEach(r=>{r.name=PAYLOAD;});inventory.profiles.forEach(r=>{r.name=PAYLOAD;});
    status.profiles.forEach(r=>{r.name=PAYLOAD;r.router_name=PAYLOAD;});}});
  p.T.snap();
  for(const tab of Object.keys(p.T.tabs))p.T.tabs[tab]();
  p.T.settingsA();p.T.wizard();
  assert.deepStrictEqual(p.innerHtml,[],lang+' approved page: no element got innerHTML through E: '+JSON.stringify(p.innerHtml).slice(0,300));
}
console.log('PASS: approved page (RU/EN, every tab, settings, wizard) with hostile names: no innerHTML through E');

// ---------- 5. the optional server-pick module (pick<N>.js; not shipped while the page does not reference it) ----------
const PICK=path.join(ROOT,'router/files/www/luci-static/resources/homensai-vpn/pick'+app.ui_module.replace(/^dashboard/,'')+'.js');
assert(fs.existsSync(PICK),'pick module is generated: '+PICK);
const pickSource=fs.readFileSync(PICK,'utf8');
function renderPick(E,sinks){
  const ctx={console,Object,Array,String,Number,Math,Date,JSON,Promise};vm.createContext(ctx);
  const mod=vm.runInContext('(function(baseclass){'+pickSource+'\n})',ctx)({extend:o=>o});
  const status={time:1e9,server_time:1e9+30,profiles:[{interface:'wgclient1',name:PAYLOAD,router_name:PAYLOAD}],
    server_pick:{time:1e9,enabled:true,tunnels:[
      {protocol:'wireguard',interface:'wgclient1',current:'p1',best:'p2',code:null,
       candidates:[{profile:'p1',location:PAYLOAD,latency_ms:38,alive:true},{profile:PAYLOAD,location:null,latency_ms:44,alive:true}],
       last_change:{time:1e9-20,from_location:PAYLOAD,to_location:PAYLOAD,from_ms:61,to_ms:38}},
      {protocol:'openvpn',interface:'ovpnclient1',current:PAYLOAD,best:null,candidates:[]}]}};
  const root=mod.render({E,bi:(en)=>en,rpc:{declare:()=>()=>Promise.resolve({})},ui:{addNotification(){}},status,inventory:{settings:{}},errorCodeLink:c=>c});
  return {root,sinks};
}
{
  // Raw LuCI E (no wrapper): the module itself passes every name as an array child.
  const sinks=[];renderPick(luciE(node,sinks),sinks);
  assert.deepStrictEqual(live(sinks),[],'pick module under raw LuCI E: no name reaches innerHTML: '+JSON.stringify(sinks).slice(0,300));
  // Through the page wrapper: nothing at all goes to innerHTML.
  const w=wrapped(GUARD);renderPick(w.E,w.sinks);
  assert.deepStrictEqual(w.sinks,[],'pick module through the wrapper: no innerHTML');
}
console.log('PASS: server-pick module keeps GL profile/server names as text under a raw LuCI E and through the wrapper');
