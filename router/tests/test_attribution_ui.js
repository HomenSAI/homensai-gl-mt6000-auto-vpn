const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat().filter(c=>c!=null);}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join('');}}
// Current owner rule: retain product/device/developer/app version; hide implementation labels.
const identity=fs.readFileSync('router/identity_panel.inc.js','utf8').replace('__UI_BUILD__','dashboard99').replace('__UI_AGENT__','1.2.3-alpha4');
const src=fs.readFileSync('router/attribution_panel.inc.js','utf8');
const context={bi:(en)=>en,E:(tag,attrs,children)=>new Node(tag,attrs,children)};
vm.createContext(context);vm.runInContext(identity,context);vm.runInContext(src,context);
const node=context.renderAttribution({version:'1.2.3-alpha4',package:'1.2.3-alpha4-1'});
const text=node.text();
for(const part of ['HomenS.AI Auto VPN','GL.iNet GL-MT6000 · Flint 2','Developer · Serhii Khomenko','Version 1.2.3-alpha4'])assert(text.includes(part),part);
assert(!/package |dashboard99|HomenS\.AI Style/.test(text),'implementation identity is not ordinary attribution');
assert(node.all().some(n=>n.tag==='a'&&n.attrs.href==='https://homensai.com'));
// No status (RPC down) still shows every attribute, with the page's own version.
assert(context.renderAttribution(undefined).text().includes('Version 1.2.3-alpha4'));
// A page/program mismatch is not a banner on any page: only a quiet link in the attribution line to its Help topic.
context.helpLink=(id,label)=>new Node('a',{href:'#help','data-topic':id},label);
const old=context.renderAttribution({version:'1.2.2',package:'1.2.2-1'});
assert(old.all().some(n=>n.tag==='a'&&n.attrs['data-topic']==='stale'&&/versions differ/.test(n.text())));
assert(!node.all().some(n=>n.attrs&&n.attrs['data-topic']==='stale'),'no warning when versions match');
// The shipped page (approved mockups, 03.11.2026): the same owner attributes in the header and in the footer of every
// view and of the first-run wizard; the version badge; no stylesheet rule hides them.
const {load,strip,pageSource,CSS,app}=require('./approved_page');
const dashboard=pageSource();
for(const lang of ['en','ru']){
  const {T}=load({lang});
  const footer=strip(T.footerHTML()),brand=strip(T.brandHTML());
  for(const part of ['HomenS .AI Auto VPN','GL.iNet GL-MT6000 · Flint 2',lang==='en'?'Developer · Serhii Khomenko':'Разработчик · Serhii Khomenko',app.version,'HomenS.AI Style 1.14.3'])
    assert(footer.includes(part),lang+' footer: '+part);
  assert(brand.includes('HomenS .AI Auto VPN')&&brand.includes('GL.iNet GL-MT6000 · Flint 2')&&brand.includes('v'+app.version),'header: name, model, version badge');
  assert(/<a href="https:\/\/homensai\.com"[^>]*>(Developer|Разработчик) · Serhii Khomenko<\/a>/.test(T.footerHTML()),'developer link to homensai.com');
  // owner 04.11.2026 and 05.11.2026: «пакет …» and «страница dashboardNNN» mean nothing to a person: nowhere on the page,
  // the diagnostics of the System tab included; only the program and the style in the footer and in «О программе»
  assert(!footer.includes(app.ui_module)&&!/пакет|страница|package|page /.test(strip(T.buildLine())),'no build identity in the footer');
  assert(strip(T.buildLine())===(lang==='en'?'Program ':'Программа ')+app.version,'the footer line is the program version');
  assert(!strip(T.settingsA().slice(T.settingsA().indexOf('id="sec-about"'))).includes(app.ui_module),'not in About either');
  for(const [name,html] of [['footer',T.footerHTML()],['brand',T.brandHTML()],['system tab',T.tabs.sys()],['settings',T.settingsA()]]){
    assert(!html.includes('data-diag-build'),name+': no build line');
    assert(!html.includes(app.ui_module)&&!html.includes(app.package_version),name+': neither the page module nor the package version');
    assert(!/Сборка: |Build: |страница dashboard/.test(strip(html)),name+': no build words');
  }
  assert(!('pkg' in T.VER())&&!('page' in T.VER()),'the page keeps no build values it does not use');
}
assert(dashboard.includes("HV.root.innerHTML=hdr+main+footerHTML()+topHTML();"),'every view and the wizard end with the footer');
assert(dashboard.includes('class="badge-ver hv-version"'),'version badge');
const css=fs.readFileSync(CSS,'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
const rules=[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
for(const [,selector,body] of rules){
  if(!/display\s*:\s*none|visibility\s*:\s*hidden/.test(body))continue;
  // As in the mockups only the small model line under the name is dropped on phones; the footer keeps the model.
  for(const one of selector.split(','))if(!/\.hdr \.devline$/.test(one.trim()))assert(!/\.attr|hv-attribution|\.badge-ver|hv-version|\.brand/.test(one),'hidden: '+one.trim());
}
assert(/\.hvx \.attr \.wrap\{display:flex/.test(css)&&/\.hvx \.attr\{border-top/.test(css),'the footer strip lays out its attributes');
console.log('PASS: owner identity in the header and footer of every view (RU/EN): name, model, developer link, program version, Style, version badge');
