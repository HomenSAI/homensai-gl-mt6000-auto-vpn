const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat().filter(c=>c!=null);this.checked=false;this.textContent='';}
  setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k];}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join(' ');}}
const store={};let blocked=false;
const storage={getItem:k=>{if(blocked)throw new Error('blocked');return k in store?store[k]:null;},setItem:(k,v)=>{if(blocked)throw new Error('blocked');store[k]=String(v);}};
const src=fs.readFileSync('router/design_panel.inc.js','utf8');
const context={bi:(en)=>en,E:(tag,attrs,children)=>new Node(tag,attrs,children),window:{localStorage:storage}};
vm.createContext(context);vm.runInContext(src,context);
// Three designs, B Calm is the default; unknown or hostile values cannot choose a different default.
assert.deepEqual(Array.from(context.HV_DESIGNS.map(d=>d.key)),['a','b','c']);
assert.equal(context.storedDesign(),'b');assert.equal(context.currentDesign(),'b');
for(const bad of ['', 'd', 'A', '<img src=x>', 'a ', 'constructor']){store['homensai-vpn-design']=bad;assert.equal(context.storedDesign(),'b');}
// Explicit browser A/C still win over a router default; without an override the router's A/C stay intact.
for(const saved of ['a','c']){
  delete store['homensai-vpn-design'];context.HV_ROUTER_DISPLAY={design:saved};assert.equal(context.storedDesign(),saved);
  store['homensai-vpn-design']=saved==='a'?'c':'a';assert.equal(context.currentDesign(),store['homensai-vpn-design']);
}
context.HV_ROUTER_DISPLAY={design:'invalid'};delete store['homensai-vpn-design'];assert.equal(context.currentDesign(),'b');
context.HV_ROUTER_DISPLAY={design:'b'};
store['homensai-vpn-design']='c';assert.equal(context.storedDesign(),'c');
assert.equal(context.saveDesign('x'),false);assert.equal(store['homensai-vpn-design'],'c');
// Every design names who it suits, in both languages.
for(const d of context.HV_DESIGNS){for(const f of ['name','about','suits'])assert(d[f][0]&&d[f][1]&&d[f][0]!==d[f][1],d.key+' '+f);}
// The picker preselects the stored design; choosing B applies it to the page and stores it.
const root=new Node('div');let applied=null;
const picker=context.renderDesignPicker(()=>root,(k)=>{applied=k;});
const radios=picker.all().filter(n=>n.tag==='input'&&n.attrs.type==='radio');
assert.equal(radios.length,3);assert.deepEqual(radios.map(r=>r.checked),[false,false,true]);
assert(picker.text().includes('Suits:'));
const note=picker.all().find(n=>n.attrs.class==='hv-design-note');assert.equal(note.attrs['aria-live'],'polite');
radios[1].attrs.change();
assert.equal(store['homensai-vpn-design'],'b');assert.equal(root.attrs['data-hv-design'],'b');assert.equal(applied,'b');
assert(/next time/.test(note.textContent));
// Next visit opens in the stored design.
assert.equal(context.storedDesign(),'b');
// Storage blocked: the design still applies now; a missing browser/router preference falls back to B.
blocked=true;radios[2].attrs.change();
assert.equal(root.attrs['data-hv-design'],'c');assert(/resets after a reload/.test(note.textContent));
assert.equal(context.storedDesign(),'b');
// ...but the page keeps the choice for this session, so the next redraw uses C, not A.
assert.equal(context.currentDesign(),'c');blocked=false;
context.applyDesign(root,'invalid');assert.equal(root.attrs['data-hv-design'],'b','invalid direct application uses the same Calm default');
// Retained legacy helper remains tested above; released view fixes the accepted layout and removes its picker.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base='router/files/www/luci-static/resources/view/homensai-vpn/';
const dashboard=fs.readFileSync(base+page+'.js','utf8');
assert(dashboard.includes("'class':'hv-app hv-workspace hv-minimum-release','data-hv-design':'b'"));
const releasedView=dashboard.slice(dashboard.lastIndexOf('return view.extend({'));
assert(!releasedView.includes('renderDesignPicker('),'operator settings no longer expose competing layouts');
const fixed=/function currentDesign\(\)\{return 'b';\}/.exec(dashboard);assert(fixed,'release ignores legacy layout choices');
vm.runInContext(fixed[0],context);
for(const old of ['a','c','constructor']){store['homensai-vpn-design']=old;assert.equal(context.currentDesign(),'b');}
assert(dashboard.includes("'data-hv-tab':tab[0],'title':tab[2]"));
const css=/ui[0-9]+\.css/.exec(dashboard)[0];
const sheet=fs.readFileSync(base+css,'utf8');
for(const k of ['a','b','c'])assert(sheet.includes('[data-hv-design="'+k+'"]'),'css '+k);
assert(sheet.includes('.hv-design-options'));
console.log('PASS: retained legacy layout helpers and storage safety; released Minimum fixes accepted palette B and exposes no design picker');
