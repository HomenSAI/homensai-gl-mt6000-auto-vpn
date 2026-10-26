const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync('router/sidebar_layout.inc.js','utf8'),c);
for(const [width,height,header,top] of [[978,808,78,90],[1280,720,40,60],[1024,600,50,100],[800,480,50,62],[1280,300,40,52]]){
 const g=c.sidebarGeometry(height,top,header,width);assert.equal(g.mobile,false);assert(g.top>=header+12);assert(Math.max(g.top,top)+g.height<=height-12);assert(g.height>0);
}
assert.equal(c.sidebarGeometry(300,52,40,1280).tiny,true);
for(const width of [360,414,640,760])assert.equal(c.sidebarGeometry(360,100,80,width).mobile,true);
console.log('PASS: constrained-height sidebar geometry, external header clearance, tiny-panel fallback and mobile wrap');

// Opening another page always scrolls to the top; the first draw and refreshes of the same page do not.
{
  const fs3=require('fs'),a3=require('assert');
  const menu=JSON.parse(fs3.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
  const page=fs3.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
  const start=page.indexOf('function showPage(key){');a3(start>0);
  const body=page.slice(start,page.indexOf('\n    }',start));
  a3(body.includes('oldTab=activeTab,oldRoute=minimumCurrentRoute'));
  a3(body.includes('if(oldRoute.hash!==route.hash){revisitPageViewport'),'restore position only when canonical route/subview changes');
  // showPage must set activeTab before it compares, so a refresh of the same page never jumps.
  a3(body.includes('rememberPageViewport(appRoot||panel,oldTab)'));
  a3(page.includes('finally {if(refreshViewport&&refreshViewport.page===activeTab)restorePageViewport'));
  console.log('PASS: refresh preserves viewport; page navigation remembers each visited position');
}

// Real LuCI serialises null children; a module-local factory must clean all callers,
// not hide literal words in CSS or alter meaningful zeroes/attributes/JSON text.
{
 const guard=fs.readFileSync('router/element_guard.inc.js','utf8');
 class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=Array.isArray(children)?children:[children];this.nodeType=1;}text(){return this.children.map(n=>n instanceof Node?n.text():String(n)).join('');}}
 const native=function(tag,attrs,children){if(Array.isArray(tag))return new Node('fragment',{},tag);if(Array.isArray(attrs)&&arguments.length===2)return new Node(tag,{},attrs);return new Node(tag,attrs,arguments.length>2?children:[]);};
 let nativeThis;
 const dom={create:function(){nativeThis=this;return native.apply(null,arguments);}};
 const globalFactory=native;
 const element=new Function('L',guard+'; return E;')({dom});
 let clicked=0;const attrs={disabled:null,click:()=>clicked++};
 const original=Object.freeze([null,undefined,0,'—',Object.freeze([null,'Нет данных'])]);
 const node=element('div',attrs,original);assert.equal(node.text(),'0—Нет данных');assert.strictEqual(nativeThis,dom);assert.strictEqual(node.attrs,attrs);node.attrs.click();assert.equal(clicked,1);assert.strictEqual(node.attrs.disabled,null);
 assert.equal(element('p',{},undefined).text(),'');assert.equal(element('p',{},null).text(),'');
 assert.equal(element('div',[null,'two arguments',undefined]).text(),'two arguments');
 assert.equal(element([null,'fragment',undefined]).text(),'fragment');
 assert.equal(element('pre',{},'{"value":null}').text(),'{"value":null}','diagnostic data is not rewritten');
 assert.equal(original.length,5,'source arrays remain untouched');
 const ctx={E:globalFactory,bi:(en,ru)=>ctx.ru?ru:en,Date,window:{localStorage:{getItem:()=>null,setItem:()=>{}}}};vm.createContext(ctx);
 vm.runInContext(guard,ctx);vm.runInContext(guard,ctx);assert.equal(ctx.E('span',{},[null,0,undefined]).text(),'0','reloading cannot recursively wrap its own factory');
 vm.runInContext(fs.readFileSync('router/summary_panel.inc.js','utf8'),ctx);
 for(const ru of [false,true])for(const done of [false,true]){
  ctx.ru=ru;ctx.startSteps=()=>[{key:'terms',done:true,title:'Terms',hint:null},{key:'learn',done,title:'Training',hint:undefined},{key:'monitor',done,title:'Monitoring',hint:null}];
  const start=ctx.renderStartPage({},{settings:{}});assert(!/null|undefined/.test(start.text()),'actual Getting started page with absent optional copy');
  const journalIntro=ctx.ru?'Живой журнал того, что видит роутер.':'A live log of what the router sees.';
  assert.equal(ctx.E('header',{},[ctx.E('p',{},journalIntro),null,undefined]).text(),journalIntro,'live journal shared subtitle omits absent connectivity slot');
  const intro='Первые шаги: условия, обучение, мониторинг, два ваших VPN и Auto.';
  assert.equal(ctx.E('header',{},[ctx.E('p',{},intro),null,undefined]).text(),intro,'reported subtitle/footer slot cannot print null');
 }
 const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');assert(builder.includes("element_guard.inc.js"));assert(builder.includes("must_replace(\"'require ui';\""),'guard follows dependency directives');
 console.log('PASS: module-local LuCI element guard, nested null/undefined cleanup, zero/attributes/callback preservation, reload safety and actual Getting started rendering in EN/RU');
}

// Exercise the selected generated release's five actual navigation links.
{
 const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
 const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
 const tabsLine=source.split('\n').find(line=>line.includes('    var tabs='));
 const linkLine=source.split('\n').find(line=>line.includes('function tabLink(key)'));
 const linksLine=source.split('\n').find(line=>line.includes("var links=['channels','diagnostics','events','settings','help'].map(tabLink)"));
 assert(tabsLine&&linkLine&&linksLine,'selected module declares five canonical navigation destinations');
 class NavNode{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children);}setAttribute(k,v){this.attrs[k]=v;}}
 for(const ru of [false,true]){
  const opened=[],ctx={E:(...args)=>new NavNode(...args),bi:(en,rus)=>ru?rus:en,showPage:key=>opened.push(key),minimumNavigate:key=>opened.push(key)};
  vm.createContext(ctx);vm.runInContext(tabsLine+'\n'+linkLine+'\n'+linksLine,ctx);
  assert.deepEqual(Array.from(ctx.links.map(n=>n.attrs['data-hv-tab'])),['channels','diagnostics','events','settings','help']);
  ctx.links.forEach(link=>{assert(link.attrs.title);assert.equal(link.attrs.href,'#'+link.attrs['data-hv-tab']);link.attrs.click({preventDefault(){}});});
  assert.deepEqual(opened,['channels','diagnostics','events','settings','help']);
 }
 const css=fs.readFileSync('router/minimum_ui.css','utf8');
 assert(css.includes('data-minimum-menu-open'),'mobile expanded state is styled');
 assert(source.includes("'aria-controls':'hv-minimum-nav','aria-expanded':'false'"),'mobile menu discloses controlled navigation');
 assert(source.includes("homeShortcut=renderSimpleHomeShortcut"),'return to Minimum remains visible in the heading');
 assert(!source.slice(source.lastIndexOf('return view.extend({')).includes("var advancedOpen=false;"),'obsolete nested twelve-section menu removed');
 console.log('PASS: actual five release links in EN/RU, named mobile disclosure, explicit return and canonical navigation without old menu group');
}
