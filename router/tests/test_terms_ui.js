const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat();this.checked=false;this.disabled=false;this.listeners={};
  this.addEventListener=(n,f)=>{(this.listeners[n]=this.listeners[n]||[]).push(f);};}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join(' ');}}
const agent=fs.readFileSync('router/files/usr/lib/homensai-vpn/agent.py','utf8');
const version=/^TERMS_VERSION = '([^']+)'/m.exec(agent)[1];
const src=fs.readFileSync('router/terms_panel.inc.js','utf8').replace('__TERMS_VERSION__',version);
const calls=[],notes=[];let reloads=0,failure=null;
const context={bi:(en)=>en,locale:'en',E:(tag,attrs,children)=>new Node(tag,attrs,children),L:{resource:p=>'/r/'+p},
  ui:{addNotification:(_,n)=>notes.push(n)},window:{location:{reload:()=>reloads++,href:'http://r/x'}},URL,
  rpc:{declare:spec=>(...args)=>{calls.push({spec,args});return failure?Promise.reject(new Error('x')):Promise.resolve(context.answer);}}};
vm.createContext(context);vm.runInContext(src,context);
const accepted={settings:{terms_version:version}};
assert.equal(context.termsAccepted(accepted),true);
for(const bad of [{settings:{terms_version:''}},{settings:{terms_version:'0'}},{settings:{}},{},null,undefined,{error:'X',settings:{terms_version:version}}])assert.equal(context.termsAccepted(bad),false);
(async()=>{
  const gate=context.renderTermsGate({settings:{terms_version:''}});
  assert.equal(gate.attrs['data-terms-gate'],version);
  const boxes=gate.all().filter(n=>n.tag==='input'&&n.attrs.type==='checkbox'),button=gate.all().find(n=>n.attrs.class&&n.attrs.class.includes('hv-terms-accept'));
  assert.equal(boxes.length,2);assert.equal(button.disabled,true);
  const toggle=(box,on)=>{box.checked=on;(box.listeners.change||[]).forEach(f=>f());};
  // The button stays disabled until BOTH boxes are ticked, and clicking while disabled does nothing.
  await button.attrs.click();assert.equal(calls.length,0);
  toggle(boxes[0],true);assert.equal(button.disabled,true);await button.attrs.click();assert.equal(calls.length,0);
  toggle(boxes[1],true);assert.equal(button.disabled,false);
  toggle(boxes[0],false);assert.equal(button.disabled,true);toggle(boxes[0],true);
  // Refusal and transport failure never claim acceptance and re-enable the button.
  context.answer={saved:false,code:'TERMS-VERSION'};await button.attrs.click();
  assert.equal(calls.length,1);assert.equal(reloads,0);assert.equal(button.disabled,false);assert(notes.length===1);
  failure=true;await button.attrs.click();assert.equal(reloads,0);assert.equal(button.disabled,false);failure=false;
  // Success sends exactly the current version through the typed own RPC and reloads.
  context.answer={saved:true};await button.attrs.click();
  const ok=calls[calls.length-1];assert.equal(ok.spec.method,'terms_accept');assert.deepEqual(Array.from(ok.spec.params),['version']);assert.deepEqual(Array.from(ok.args),[version]);
  assert.equal(reloads,1);
  // Content: seven points, English and Russian, matching the documents.
  assert.equal(context.TERMS_POINTS.length,7);
  const en=fs.readFileSync('DISCLAIMER.md','utf8'),ru=fs.readFileSync('DISCLAIMER.ru.md','utf8'),cyr=/[А-Яа-я]/;
  for(const p of context.TERMS_POINTS){assert(!cyr.test(p.h[0])&&cyr.test(p.h[1])&&!cyr.test(p.t[0])&&cyr.test(p.t[1]));assert(en.includes('**'+p.h[0]+'.**'),p.h[0]);assert(ru.includes('**'+p.h[1]+'.**'),p.h[1]);}
  assert(en.includes('Terms version: '+version+'.')&&ru.includes('Версия условий: '+version+'.'));
  for(const phrase of ['AS IS','at your own risk'])assert(en.includes(phrase),phrase);
  for(const phrase of ['КАК ЕСТЬ','на свой риск'])assert(ru.includes(phrase),phrase);
  // Wired into the generated page: the gate replaces everything until accepted; Help repeats the terms.
  const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
  const page=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
  assert(page.includes("if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory);")&&page.includes("TERMS_VERSION='"+version+"'")&&!page.includes('__TERMS_'));
  assert(page.includes("HELP_TOPICS.push({id:'terms'"));
  console.log('PASS: first-run terms gate (two boxes, typed acceptance, documents and Help in step)');
})().catch(e=>{console.error(e);process.exitCode=1;});
