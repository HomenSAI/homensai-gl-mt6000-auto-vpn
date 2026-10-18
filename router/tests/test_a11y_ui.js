const fs=require('fs'),vm=require('vm'),assert=require('assert');
// Accessibility checks of the generated page and of the A/B/C overviews (structure only; a real screen reader is not available offline).
class N{constructor(t,a,c){this.tag=t;this.attrs=a||{};this.children=[].concat(c===undefined?[]:c).flat().filter(x=>x!=null);}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join(' ');}
  appendChild(c){this.children.push(c);return c;}setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]==null?null:this.attrs[k];}
  addEventListener(){}removeAttribute(){}get style(){return {};}get classList(){return {add(){},remove(){},toggle(){}};}}
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const base='router/files/www/luci-static/resources/view/homensai-vpn/';
const source=fs.readFileSync(base+page+'.js','utf8');
const prefix=source.slice(0,source.lastIndexOf('return view.extend({'));
const ctx={window:{localStorage:{getItem(){return null},setItem(){}},HomenS:{},location:{search:'',href:'http://x/',hash:''}},document:{createElementNS:(ns,t)=>new N(t,{},[]),createElement:t=>new N(t),addEventListener(){}},localStorage:{getItem(){return null}},E:(t,a,c)=>new N(t,a,c),URLSearchParams,URL,Intl,console,L:{},rpc:{declare:()=>()=>Promise.resolve({})},ui:{},poll:{},view:{extend:o=>o}};
ctx.location=ctx.window.location;vm.createContext(ctx);vm.runInContext(prefix,ctx);
// 1. Page structure: skip link, focusable heading that receives focus on section change, one main landmark, labelled navigation.
assert(source.includes("'class':'hv-skip'"),'skip link');
assert(source.includes("heading=E('h1',{'tabindex':'-1'}"),'focusable heading');
assert(source.includes("heading.focus({preventScroll:true})"),'focus moves to the heading when another section opens');
assert(/E\('nav',\{'tabindex':'0','aria-label':/.test(source),'labelled navigation');
assert((source.match(/E\('main',/g)||[]).length===1,'exactly one main landmark');
// 2. CSS: visible focus for every kind of control, skip link hidden until focused, reduced motion handled.
const css=fs.readFileSync(base+/ui[0-9]+\.css/.exec(source)[0],'utf8');
for(const part of ['.hv-app a:focus-visible','.hv-app button:focus-visible','.hv-app summary:focus-visible','.hv-app .hv-skip:focus{top:8px}','prefers-reduced-motion'])assert(css.includes(part),part);
// 3. Rendered overviews: every control has a name, no positive tabindex, lamps are never the only carrier of a state.
const now=Date.now()/1000;
const profiles=[{id:'a',name:'de-1',router_name:'de-1',protocol:'openvpn',interface:'vpna',channel:'Main',time:now-5,dns_ok:true,https_success:2,rtt_ms:38,code:null},{id:'b',name:'nl-1',router_name:'nl-1',protocol:'wireguard',interface:'vpnb',channel:'Main',time:now-5,dns_ok:false,https_success:0,rtt_ms:null,code:'DNS-001'},{id:'c',name:'fi-1',router_name:'fi-1',protocol:'openvpn',interface:null,channel:'Spare'}];
const status={version:'1',time:now-2,profiles,samples:[],native_failover:{state:'OBSERVING',certified:true,source:'a',target:'b',time:now-1},native_history:{events:[]},accounting:{months:{}}};
for(const d of ['a','b','c']){
  const control=new N('section',{},[new N('button',{'aria-label':'Auto'},[])]);
  const node=ctx.renderDesignOverview(d,{status,inventory:{settings:{plan_source:'a',plan_target:'b'}},rows:profiles,month:null,controlCard:control});
  for(const n of node.all()){
    if(['a','button','input','select','summary'].includes(n.tag)){
      const name=(n.attrs['aria-label']||n.attrs.title||n.text()).toString().trim();
      assert(name,d+': control without a name: '+n.tag);
    }
    if(n.attrs&&n.attrs.tabindex!=null)assert(Number(n.attrs.tabindex)<=0,d+': positive tabindex');
    if(/hv-check-lamp|hv-server-lamp/.test(n.attrs.class||''))assert(n.attrs['aria-hidden']==='true'||n.attrs.role==='img','lamp without role or aria-hidden');
  }
  // A lamp next to its word: every status column row has visible text, not only a colour.
  for(const col of node.all().filter(n=>/hv-dv-statuscol/.test(n.attrs.class||'')))assert(col.text().trim().length>0,d+': status column without a word');
  const strip=node.all().find(n=>/hv-dv-strip/.test(n.attrs.class||''));
  if(strip){assert.notEqual(strip.attrs.role,'status','the summary strip must not be a live region that re-announces every refresh');assert(strip.attrs['aria-label']);}
}
const c=ctx.renderDesignOverview('c',{status,inventory:{settings:{}},rows:profiles,month:null,controlCard:new N('section')});
assert(c.all().filter(n=>n.tag==='th').every(n=>n.attrs.scope==='col'),'table headers carry scope=col');
console.log('PASS: skip link, heading focus, visible focus, control names, lamps with words, table scope, no live-region spam');
