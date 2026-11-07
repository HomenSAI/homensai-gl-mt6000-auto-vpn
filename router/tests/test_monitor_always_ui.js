// Owner main rule 07.11.2026: monitoring ALWAYS runs. The page has no monitor-off control; an absent monitor is a red ERROR
// state with the fix (Restore monitoring / reinstall), never a neutral "off".
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat();}
 appendChild(c){this.children.push(c);return c;}get firstChild(){return this.children[0]||null;}removeChild(c){this.children.splice(this.children.indexOf(c),1);}}
function text(n){return typeof n==='string'?n:n&&n.children?n.children.map(text).join(' '):'';}
function walk(n,f){if(n&&typeof n==='object'){f(n);(n.children||[]).forEach(c=>walk(c,f));}}
const ctx={bi:(en)=>en,E:(t,a,c)=>new Node(t,a,c),window:{sessionStorage:{getItem:()=>null}}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('router/monitor_panel.inc.js','utf8'),ctx);
const now=1000;
// the monitor process is absent: no status at all (STATUS_DEFAULT: SERVICE-STOPPED), config enabled or not, stale data
for(const [status,settings] of [[{error:'SERVICE-STOPPED'},{enabled:true}],[{error:'SERVICE-STOPPED'},{enabled:false}],[{},{enabled:true}],[{time:now-4000},{enabled:true}],[{time:now-4000},{enabled:false}]]){
  const m=ctx.monitorLightModel(status,{settings},now,false);
  assert.equal(m.lamp,'red',JSON.stringify(status)+JSON.stringify(settings));assert.equal(m.key,'problem');
  assert(/ERROR/.test(m.title),'title says ERROR: '+m.title);
  assert(/Restore monitoring/.test(m.hint)&&/reinstall/.test(m.hint),'hint carries the fix: '+m.hint);
  assert(m.code,'a code is shown');
  // the block offers exactly one button, a restore (start), never an off control
  const host=new Node('div');ctx.fillMonitorBlock(host,status,{settings});
  const buttons=[];walk(host,n=>{if(n.tag==='button')buttons.push(n);});
  assert.equal(buttons.length,1);assert(/Restore monitoring/.test(text(buttons[0])));
}
// a running monitor: green, no button at all
{const host=new Node('div');ctx.fillMonitorBlock(host,{time:Date.now()/1000-3},{settings:{enabled:true}});
 let b=0;walk(host,n=>{if(n.tag==='button')b++;});assert.equal(b,0);}
// owner decision 07.11.2026 15:10: the router starts the monitor whatever option enabled says. Fresh data with enabled=0 is
// green ("Monitoring is on"), never an error; only a note says the Auto service is off, with its own (start) button.
{const host=new Node('div');ctx.fillMonitorBlock(host,{time:Date.now()/1000-3},{settings:{enabled:false}});
 const all=text(host);assert(/Monitoring is on/.test(all),all);assert(!/ERROR/.test(all),all);assert(/SERVICE-AUTO-OFF/.test(all),all);
 const buttons=[];walk(host,n=>{if(n.tag==='button')buttons.push(n);});
 assert.equal(buttons.length,1);assert(/Switch the Auto service on/.test(text(buttons[0])));assert(!/Restore monitoring/.test(text(buttons[0])));}
// IR-01: a package operation holds the maintenance marker (service stopped by the hooks): yellow, the code, no Restore button
for(const status of [{error:'SERVICE-STOPPED',maintenance:{state:'active',code:'MAINTENANCE-IN-PROGRESS'}},{time:now-4000,maintenance:{state:'active',code:'MAINTENANCE-IN-PROGRESS'}}]){
  const m=ctx.monitorLightModel(status,{settings:{enabled:true}},now,false);
  assert.equal(m.key,'transition');assert.equal(m.lamp,'yellow');assert.equal(m.code,'MAINTENANCE-IN-PROGRESS');assert(m.maintenance);assert(!/ERROR/.test(m.title));
  const host=new Node('div');ctx.fillMonitorBlock(host,status,{settings:{enabled:true}});
  let b=0;walk(host,n=>{if(n.tag==='button')b++;});assert.equal(b,0,'no Restore during maintenance');
}
// a stale (interrupted) marker is no excuse: the absent monitor is an error again
assert.equal(ctx.monitorLightModel({error:'SERVICE-STOPPED',maintenance:{state:'stale',code:'MAINTENANCE-INTERRUPTED'}},{settings:{enabled:true}},now,false).key,'problem');
// fresh data during maintenance stays green
assert.equal(ctx.monitorLightModel({time:now-3,maintenance:{state:'active',code:'MAINTENANCE-IN-PROGRESS'}},{settings:{enabled:true}},now,false).key,'ok');
// a missing inventory (no settings) is never read as "service off"
{const host=new Node('div');ctx.fillMonitorBlock(host,{time:Date.now()/1000-3},{});
 let b=0;walk(host,n=>{if(n.tag==='button')b++;});assert.equal(b,0);assert(!/SERVICE-AUTO-OFF/.test(text(host)));}
// the sources and the shipped page: no off control, no retired codes, only start requests
const app=JSON.parse(fs.readFileSync('VERSION.json','utf8')).application;
const dir='router/files/www/luci-static/resources/';
const page=fs.readFileSync(dir+'view/homensai-vpn/'+app.ui_module+'.js','utf8');
const help=fs.readFileSync(dir+'homensai-vpn/help'+app.ui_module.replace('dashboard','')+'.js','utf8');
for(const bad of ['Stop monitor','Остановить мониторинг','MONITOR-STOP-AUTO-FIRST','MONITOR-STOP-REQUESTED','Выключить мониторинг','Turn off monitoring']){
  assert(!page.includes(bad),'page has no '+bad);assert(!help.includes(bad),'help has no '+bad);
}
const calls=[...page.matchAll(/monitor_control['"][^)]*\)\)?\(([^)]*)\)/g)].map(m=>m[1]);
assert(calls.length>0&&calls.every(a=>a==='true'),'every monitor_control call is a start: '+calls);
assert(help.includes('MONITOR-ALWAYS-ON')&&help.includes('Мониторинг работает всегда'),'catalogue row EN+RU');
assert(help.includes('SERVICE-AUTO-OFF')&&help.includes('служба Auto выключена'),'SERVICE-AUTO-OFF catalogue row EN+RU');
assert(!/settings\|\|\{\}\)\.enabled\?E\('span'/.test(page),'the legacy settings card never treats a missing flag as service off');
console.log('PASS: monitor always on - error state when absent, restore only, no off control, MONITOR-ALWAYS-ON catalogued');
