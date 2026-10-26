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
// The release has compact persistent identity; detailed attribution/version stays reachable in About.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base='router/files/www/luci-static/resources/view/homensai-vpn/';
const dashboard=fs.readFileSync(base+page+'.js','utf8');
assert(dashboard.includes('minimumCommandHost,settingsHost,panel,renderMinimumFooter(data[1])])'),'persistent pair form precedes closed controller details');
assert(dashboard.includes("E('div',{'class':'hv-page-actions'},[])"),'common header stays concise');
assert(dashboard.includes("settingsHost.appendChild(minimumDisclosure(bi('Interface in this browser','Интерфейс в этом браузере'),'browser-interface'"),'language/theme remain in Settings disclosure');
const sections=fs.readFileSync('router/minimum_sections.inc.js','utf8');
assert(sections.includes("minimumSubview('help','about'"));
assert(sections.includes("typeof renderAttribution==='function'?renderAttribution(status):null"),'detailed owner attribution remains in About');
vm.runInContext(sections,context);
const compact=context.renderMinimumFooter({version:'1.2.3-alpha4'});
assert(compact.text().includes('HomenS.AI')&&compact.text().includes('Serhii Khomenko'));
assert(compact.all().some(n=>n.tag==='a'&&n.attrs.href==='#help/about'),'About/licenses reachable from persistent footer');
assert(!compact.text().includes('dashboard'),'implementation id stays out of ordinary footer');
assert(!dashboard.includes('insertBefore(identityNotice'),'the version banner is not inserted into any page');
assert(dashboard.includes("'class':'hv-version'"));
// No stylesheet rule (in any design) hides the attribution strip, the brand footer or the version badge.
const css=fs.readFileSync(base+/ui[0-9]+\.css/.exec(dashboard)[0],'utf8').replace(/\/\*[\s\S]*?\*\//g,'');
const rules=[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
for(const [,selector,body] of rules){
  if(!/display\s*:\s*none|visibility\s*:\s*hidden/.test(body))continue;
  for(const one of selector.split(',')){assert(!/hv-attribution|hv-brand-footer|\.hv-version\b/.test(one),'hidden: '+one.trim());}
}
assert(/\.hv-app \.hv-attribution\{display:flex!important/.test(css));
const compactFooter=/\.hv-minimum-release \.hv-minimum-footer\{([^}]+)\}/.exec(css);
assert(compactFooter&&compactFooter[1].includes('display:flex')&&/gap:[1-9]/.test(compactFooter[1]),'compact identity links have visible spacing and wrap');
console.log('PASS: compact owner identity on every page; detailed attribution/version and licenses remain reachable in About');
