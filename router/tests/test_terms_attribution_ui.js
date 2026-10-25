const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(n=>n!=null);this.checked=false;this.disabled=false;this.listeners={};}
  addEventListener(name,fn){this.listeners[name]=fn;}setAttribute(name,value){this.attrs[name]=value;}removeAttribute(name){delete this.attrs[name];}
  all(){return [this,...this.children.flatMap(n=>n instanceof Node?n.all():[])];}
  text(){return this.children.map(n=>n instanceof Node?n.text():String(n)).join('');}
}
const app=JSON.parse(fs.readFileSync('VERSION.json','utf8')).application;
const terms=/^TERMS_VERSION = '([^']+)'/m.exec(fs.readFileSync('router/files/usr/lib/homensai-vpn/agent.py','utf8'))[1];
let cases=0;
for(const locale of ['en','ru'])for(const design of ['a','b','c',null])for(const theme of ['system','light','dark'])for(const width of [390,1440]){
  const storage={'homensai-vpn-theme':theme},html=new Node('html');if(design!==null)storage['homensai-vpn-design']=design;let rpcCount=0,footerCalls=[];
  const c={locale,bi:(en,ru)=>locale==='ru'?ru:en,E:(...args)=>new Node(...args),helpCommand:s=>new Node('code',{},s),L:{resource:s=>'/r/'+s},document:{documentElement:html},
    window:{innerWidth:width,localStorage:{getItem:key=>storage[key]??null},location:{href:'http://fixture/?terms=gate'},HomenS:{brandUi:{renderFooter:(host,lang,variant)=>{footerCalls.push({lang,variant});host.children.push(new Node('p',{},'© 2026 Serhii Khomenko · homensai.com'));}}}},
    rpc:{declare:()=>{rpcCount++;throw new Error('rendering the gate must not request acceptance or any other RPC');}},ui:{},URL};
  vm.createContext(c);
  for(const file of ['identity_panel','attribution_panel','theme_panel','design_panel','terms_panel'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8').replace('__UI_BUILD__',app.ui_module).replace('__UI_AGENT__',app.version).replace('__TERMS_VERSION__',terms),c);
  const status={version:app.version,package:app.package_version},gate=c.renderTermsGate({settings:{terms_version:''}},status),all=gate.all(),text=gate.text();
  assert.equal(gate.attrs['data-hv-design'],design||'b');assert.equal(gate.attrs['data-terms-gate'],terms);assert.equal(html.attrs['data-theme'],theme==='system'?undefined:theme);
  for(const value of ['HomenS.AI Auto VPN','GL.iNet GL-MT6000 · Flint 2','Serhii Khomenko',app.version])assert(text.includes(value),locale+'/'+design+': '+value);
  assert(text.includes(locale==='ru'?'Разработчик':'Developer'));assert(all.some(n=>n.tag==='a'&&n.attrs.href==='https://homensai.com'));
  assert(all.some(n=>n.attrs.class==='hv-attribution'));assert(all.some(n=>n.tag==='footer'&&n.attrs.class==='hv-brand-footer'));assert(all.some(n=>n.attrs.class==='hv-version'&&n.text()==='v'+app.version));
  assert.deepEqual(footerCalls,[{lang:locale,variant:'platform'}]);
  const boxes=all.filter(n=>n.tag==='input'&&n.attrs.type==='checkbox');assert.equal(boxes.length,2);assert(boxes.every(n=>n.checked===false));assert(all.find(n=>n.attrs.class&&n.attrs.class.includes('hv-terms-accept')).disabled);
  assert.equal(rpcCount,0);assert(!all.some(n=>n.attrs.class==='hv-workspace'||n.attrs['data-hv-tab']),'normal controls stay behind the gate');
  assert(/width:100%/.test(gate.attrs.style)&&/box-sizing:border-box/.test(gate.attrs.style),'narrow-width sizing is bounded');assert(all.some(n=>n.tag==='header'&&/flex-wrap:wrap/.test(n.attrs.style)),'badge can wrap on narrow screens');
  const fallback=c.renderTermsGate({settings:{}},{rpc_error:'RPC-UNAVAILABLE'}).text();assert(fallback.includes(app.version)&&!fallback.includes(app.ui_module));assert(!fallback.includes(app.package_version),'unknown installed package is not invented');assert(!fallback.includes('HomenS.AI Style'));
  cases++;
}
console.log('PASS: '+cases+' terms attribution cases (EN/RU, explicit A/B/C and fresh Calm default, system/light/dark, narrow/wide), live identity/fallback, theme markers, owner footer and untouched acceptance gate');
