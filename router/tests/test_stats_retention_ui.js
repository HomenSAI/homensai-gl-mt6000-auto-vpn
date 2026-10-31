// Advanced > Statistics collection > How long statistics are kept (owner, 31 Oct 2026): by time (1-7 days, 2 weeks,
// 1 month) or by size (MB), the live flash/RAM estimate of the router's size model, warnings, keyboard/labels, save calls.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
function node(tag,attrs,children){const n={tag,attrs:attrs||{},children:[],listeners:{},textContent:'',hidden:false,addEventListener(e,f){this.listeners[e]=f;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},appendChild(c){this.children.push(c);}};
  [].concat(children||[]).forEach(c=>{if(c!==null&&c!==undefined&&c!=='')n.children.push(c);});
  n.text=function(){return (this.textContent||'')+this.children.map(c=>typeof c==='string'?c:c.text?c.text():'').join('');};
  n.all=function(){return [this].concat(...this.children.filter(c=>c&&c.all).map(c=>c.all()));};return n;}
const tick=()=>new Promise(r=>setTimeout(r,0));
// The page's fallback model is the router's model (retention_settings.MODEL).
const py=fs.readFileSync('router/files/usr/lib/homensai-vpn/retention_settings.py','utf8');
const pyModel=Function('MIB','return '+/^MODEL=(\{[\s\S]*?\})\n/m.exec(py)[1].replace(/\n\s*/g,''))(1048576);
const luaText=fs.readFileSync('router/files/usr/lib/homensai-vpn/lua/retention.lua','utf8');
const luaModel=Function('return '+/M\.MODEL=(\{[\s\S]*?\})\r?\n/.exec(luaText)[1].replace(/\r?\n\s*/g,'').replace(/([a-z_]+)=/g,'"$1":'))();
(async()=>{
for(const language of ['en','ru']){
  const c={locale:language,Date,Math,Number,String,Object,Array,JSON,Promise,calls:[],notes:[]};
  c.bi=(en,ru)=>language==='ru'?ru:en;c.E=node;
  vm.createContext(c);vm.runInContext(fs.readFileSync('router/stats_page.inc.js','utf8'),c);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(c.RETENTION_MODEL)),pyModel,'page fallback model = retention_settings.MODEL');
  assert.deepStrictEqual(pyModel,luaModel,'retention_settings.MODEL = lua/retention.lua M.MODEL');
  assert.deepStrictEqual(Array.from(c.RETENTION_STOPS),[1,2,3,4,5,6,7,14,30]);
  // The same numbers as retention_settings.estimate/size_days (test_retention_settings.py pins them too).
  assert.deepStrictEqual(JSON.parse(JSON.stringify(c.retentionEstimate({interval:10},7))),{flash:2468732,ram:13196722,work_flash:976892,work_ram:3419122});
  assert.deepStrictEqual(JSON.parse(JSON.stringify(c.retentionEstimate({interval:60,compare:true},30))),{flash:9666301,ram:56770133,work_flash:4186680,work_ram:14653380});
  assert.strictEqual(c.retentionSizeDays({interval:10},4),11);assert.strictEqual(c.retentionSizeDays({interval:300},1),5);assert.strictEqual(c.retentionSizeDays({interval:10,compare:true},1),2);
  if(language==='ru'){assert.strictEqual(c.retentionDays(1),'1 день');assert.strictEqual(c.retentionDays(3),'3 дня');assert.strictEqual(c.retentionDays(11),'11 дней');assert.strictEqual(c.retentionDays(21),'21 день');assert.strictEqual(c.retentionDays(14),'2 недели');assert.strictEqual(c.retentionDays(30),'1 месяц');}
  else{assert.strictEqual(c.retentionDays(1),'1 day');assert.strictEqual(c.retentionDays(5),'5 days');assert.strictEqual(c.retentionDays(30),'1 month');}

  const retention={mode:'time',days:7,mb:4,effective_days:7,interval:10,compare:false,mb_min:1,mb_max:32,model:pyModel};
  const model={diagnostic:false,until:0,storage:{'flash:checkpoint.json':977000},retention,capacity:{flash_free:40*1048576,ram_available:300*1048576},
    save:()=>Promise.resolve({saved:true}),saveRetention:(kind,value)=>{c.calls.push([kind,value]);return Promise.resolve({saved:true});},notify:t=>c.notes.push(t)};
  const page=c.renderCollectionPage(model),all=page.all();
  const section=all.find(n=>n.attrs['data-stats-retention']);assert(section,'retention section on the collection page');
  assert.strictEqual(all.find(n=>n.tag==='button').attrs.class,'cbi-button cbi-button-action','the mode button stays the first button of the page');
  const s=section.all(),find=cls=>s.find(n=>(n.attrs.class||'').split(' ').includes(cls));
  const radios=s.filter(n=>n.attrs.name==='hv-retention-mode'),days=s.find(n=>n.attrs.id==='hv-retention-days'),mb=s.find(n=>n.attrs.id==='hv-retention-mb');
  const save=find('hv-retention-save'),panel=k=>s.find(n=>n.attrs['data-retention-panel']===k),meter=k=>s.find(n=>n.attrs['data-retention-meter']===k);
  // accessible: native radios and ranges, each range has its <label for>, and a spoken value
  assert.deepStrictEqual(radios.map(r=>r.attrs.value),['time','size']);assert(radios[0].checked&&!radios[1].checked,'time mode by default');
  for(const input of [days,mb]){assert.strictEqual(input.attrs.type,'range');assert(s.some(n=>n.tag==='label'&&n.attrs.for===input.attrs.id),'label for '+input.attrs.id);}
  assert(s.some(n=>n.tag==='fieldset')&&s.some(n=>n.tag==='legend'),'the mode choice is a fieldset with a legend');
  assert(s.some(n=>n.attrs.role==='status'&&n.attrs['aria-live']==='polite'),'the estimate is announced');
  assert.strictEqual(days.attrs.min,'0');assert.strictEqual(days.attrs.max,'8');assert.strictEqual(days.value,'6','7 days = stop 7');
  assert.strictEqual(days.attrs['aria-valuetext'],language==='ru'?'7 дней':'7 days');
  assert(!panel('time').hidden&&panel('size').hidden);
  assert('disabled' in save.attrs,'nothing changed: Save is off');
  const flash=()=>meter('flash').text(),ram=()=>meter('ram').text();
  assert(flash().includes(language==='ru'?'2,4 МБ':'2.4 MB'),flash());assert(ram().includes(language==='ru'?'13 МБ':'13 MB'),ram());
  assert(section.text().includes(language==='ru'?'≈ 0,9 МБ на флеше':'≈ 0.9 MB on flash'),'Work mode estimate');
  // move to 1 month: the estimate grows; the RAM share of 300 MB stays below a quarter
  days.value='8';days.listeners.input();
  assert.strictEqual(days.attrs['aria-valuetext'],language==='ru'?'1 месяц':'1 month');
  assert(flash().includes(language==='ru'?'10 МБ':'10 MB'),flash());assert(ram().includes(language==='ru'?'54 МБ':'54 MB'),ram());
  assert.strictEqual(days.attrs.style,'--hv-fill:100%');assert(!('disabled' in save.attrs),'changed: Save is on');
  assert(find('hv-retention-warn').hidden,'enough room: no warning');
  save.listeners.click();await tick();
  assert.deepStrictEqual(c.calls.pop(),['time',30]);assert(find('hv-retention-current').text().includes(language==='ru'?'1 месяц':'1 month'));
  assert('disabled' in save.attrs,'saved: Save is off again');
  // size mode: the MB slider starts at the size of the saved period (7 days -> 3 MB) and shows the days it holds
  radios[1].checked=true;radios[1].listeners.change();
  assert(panel('time').hidden&&!panel('size').hidden);assert.strictEqual(mb.value,'3');
  mb.value='4';mb.listeners.input();
  assert(find('hv-retention-holds').text().includes(language==='ru'?'11 дней':'11 days'),find('hv-retention-holds').text());
  mb.value='32';mb.listeners.input();assert(find('hv-retention-holds').text().includes(language==='ru'?'максимум':'maximum'));
  mb.value='4';mb.listeners.input();save.listeners.click();await tick();assert.deepStrictEqual(c.calls.pop(),['size',4]);
  // refusal codes are shown as they come
  model.saveRetention=()=>Promise.resolve({saved:false,code:'STATS-RETENTION-SIZE'});mb.value='5';mb.listeners.input();save.listeners.click();await tick();
  assert.strictEqual(c.notes.pop(),'STATS-RETENTION-SIZE');

  // little room: flash and RAM warnings
  const tight=Object.assign({},model,{capacity:{flash_free:6*1048576,ram_available:40*1048576},storage:{}});
  const t=c.renderCollectionPage(tight).all().find(n=>n.attrs['data-stats-retention']).all();
  const tdays=t.find(n=>n.attrs.id==='hv-retention-days'),twarn=t.find(n=>n.attrs.class==='hv-retention-warn');
  assert(twarn.hidden,'7 days fits');tdays.value='8';tdays.listeners.input();
  assert(!twarn.hidden&&twarn.text().includes(language==='ru'?'Флеш может закончиться':'The flash may run out'),twarn.text());
  assert(twarn.text().includes(language==='ru'?'больше половины доступной ОЗУ':'more than half of the available RAM'),twarn.text());
  assert(t.some(n=>n.attrs['data-level']==='bad'));
  // an older router without the fields: defaults, unknown room, no warning
  const old=c.renderCollectionPage({diagnostic:false,storage:{}}).all().find(n=>n.attrs['data-stats-retention']).all();
  assert(old.some(n=>n.attrs['data-level']==='unknown'));assert(old.find(n=>n.attrs.class==='hv-retention-warn').hidden);
  assert(old.find(n=>n.attrs.class==='hv-retention-current').text().includes(language==='ru'?'ещё не сообщил':'has not reported'));
}
// The main page passes the router fields and calls setup_stats with mode 'retention'.
const probe=fs.readFileSync('router/probe_panel.inc.js','utf8');
assert(probe.includes("retention:sm.retention,capacity:sm.capacity"));
assert(probe.includes("method:'setup_stats',params:['mode','retention',kind==='time'?'days':'mb']"));
// Help topic and error rows (EN/RU).
const help=fs.readFileSync('router/help_panel.inc.js','utf8');assert(help.includes("id:'stats-retention'"));
const rows=fs.readFileSync('router/error_rows_extra.inc.js','utf8');
for(const code of ['STATS-RETENTION-FIELDS','STATS-RETENTION-DAYS','STATS-RETENTION-SIZE'])assert(rows.includes("['"+code+"','service'"),code);
const css=fs.readFileSync('router/design_layer.css','utf8');
assert(css.includes('.hv-app .hv-retention-range::-webkit-slider-thumb')&&css.includes('.hv-app .hv-retention-range::-moz-range-thumb'),'styled slider');
assert(css.includes('.hv-app .hv-retention-range:focus-visible')&&css.includes('.hv-app .hv-retention-choice input:focus-visible+span'),'visible keyboard focus');
assert(/prefers-reduced-motion:reduce\)\{\.hv-app \.hv-retention-bar-fill\{transition:none\}/.test(css));
console.log('PASS: statistics retention slider (time/size, live estimate, warnings, labels, save)');
})().catch(e=>{console.error(e);process.exit(1);});
