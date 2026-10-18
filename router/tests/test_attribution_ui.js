const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat().filter(c=>c!=null);}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join('');}}
// Owner rule: every page in every design shows the product name, device, developer, version/package/page and style.
const identity=fs.readFileSync('router/identity_panel.inc.js','utf8').replace('__UI_BUILD__','dashboard99').replace('__UI_AGENT__','1.2.3-alpha4');
const src=fs.readFileSync('router/attribution_panel.inc.js','utf8');
const context={bi:(en)=>en,E:(tag,attrs,children)=>new Node(tag,attrs,children)};
vm.createContext(context);vm.runInContext(identity,context);vm.runInContext(src,context);
const node=context.renderAttribution({version:'1.2.3-alpha4',package:'1.2.3-alpha4-1'});
const text=node.text();
for(const part of ['HomenS.AI Auto VPN','GL.iNet GL-MT6000 · Flint 2','Developer · Serhii Khomenko','Version 1.2.3-alpha4 · package 1.2.3-alpha4-1 · page dashboard99','HomenS.AI Style'])assert(text.includes(part),part);
assert(node.all().some(n=>n.tag==='a'&&n.attrs.href==='https://homensai.com'));
// No status (RPC down) still shows every attribute, with the page's own version.
assert(context.renderAttribution(undefined).text().includes('Version 1.2.3-alpha4'));
// A page/program mismatch is not a banner on any page: only a quiet link in the attribution line to its Help topic.
context.helpLink=(id,label)=>new Node('a',{href:'#help','data-topic':id},label);
const old=context.renderAttribution({version:'1.2.2',package:'1.2.2-1'});
assert(old.all().some(n=>n.tag==='a'&&n.attrs['data-topic']==='stale'&&/versions differ/.test(n.text())));
assert(!node.all().some(n=>n.attrs&&n.attrs['data-topic']==='stale'),'no warning when versions match');
// The generated page puts it into the main area of every page, after the content and before the brand footer.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base='router/files/www/luci-static/resources/view/homensai-vpn/';
const dashboard=fs.readFileSync(base+page+'.js','utf8');
assert(dashboard.includes('panel,settingsHost,renderAttribution(data[1]),footer])'));
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
console.log('PASS: owner attributes on every page and in every design');
