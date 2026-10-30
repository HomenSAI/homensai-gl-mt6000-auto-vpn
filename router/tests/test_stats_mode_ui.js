// Advanced > Statistics collection: Work by default, Diagnostics only after consent (1/3/7/14 days), measured consequences,
// the catalogue of tracked data, and the Work-mode note on statistics surfaces.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
function node(tag,attrs,children){const n={tag,attrs:attrs||{},children:[],listeners:{},textContent:'',addEventListener(e,f){this.listeners[e]=f;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},appendChild(c){this.children.push(c);}};
  [].concat(children||[]).forEach(c=>{if(c!==null&&c!==undefined&&c!=='')n.children.push(c);});
  n.text=function(){return (this.textContent||'')+this.children.map(c=>typeof c==='string'?c:c.text?c.text():'').join('');};
  n.all=function(){return [this].concat(...this.children.filter(c=>c&&c.all).map(c=>c.all()));};return n;}
(async()=>{
for(const language of ['en','ru']){
  const c={locale:language,Date,Math,Number,String,Object,Array,JSON,Promise,saves:[],notes:[]};
  c.bi=(en,ru)=>language==='ru'?ru:en;c.E=node;
  vm.createContext(c);vm.runInContext(fs.readFileSync('router/stats_page.inc.js','utf8'),c);
  const model={diagnostic:false,until:0,storage:{'flash:checkpoint.json':977000,'ram:status.json':316000},
    save:(mode,hours)=>{c.saves.push([mode,hours]);return Promise.resolve({saved:true});},notify:t=>c.notes.push(t)};
  const page=c.renderCollectionPage(model),all=page.all();
  assert(page.text().includes(language==='ru'?'Режим сбора статистики':'Statistics collection mode'));
  assert(page.text().includes(language==='ru'?'Чего стоит роутеру':'What Diagnostics costs the router'),'consequences are shown before the choice');
  assert.strictEqual(all.filter(n=>n.attrs['data-impact']).length,5,'memory, flash, CPU, switch time, status answer');
  assert(page.text().includes(language==='ru'?'ещё не измерено':'not measured yet'),'unmeasured values are said so, never invented');
  const consent=all.find(n=>n.attrs['class']==='hv-stats-consent'),durations=all.filter(n=>n.attrs.name==='hv-stats-hours'),apply=all.find(n=>n.tag==='button');
  assert.strictEqual(consent.checked,false,'Work by default: no consent');
  assert.deepStrictEqual(durations.map(d=>d.attrs.value),['24','72','168','336'],'1, 3, 7 days or 2 weeks');
  assert(durations.every(d=>'disabled' in d.attrs),'durations are locked until the consent checkbox');
  apply.listeners.click();await new Promise(r=>setTimeout(r,0));
  assert.deepStrictEqual(c.saves.pop(),['work',24],'without consent the button keeps Work');
  consent.checked=true;consent.listeners.change();
  assert(durations.every(d=>!('disabled' in d.attrs)),'consent unlocks the durations');
  durations.find(d=>d.attrs.value==='336').listeners.change();
  apply.listeners.click();await new Promise(r=>setTimeout(r,0));
  assert.deepStrictEqual(c.saves.pop(),['diagnostic',336]);
  consent.checked=false;consent.listeners.change();apply.listeners.click();await new Promise(r=>setTimeout(r,0));
  assert.deepStrictEqual(c.saves.pop(),['work',336],'clearing the checkbox returns to Work');
  // Catalogue: every tracked item with where it lives and its current size.
  const rows=all.filter(n=>n.attrs['data-collection']);assert(rows.length>=13);
  assert(rows.find(r=>r.attrs['data-collection']==='accounting').text().includes(language==='ru'?'954 КБ':'954 KB'));
  // Measured values render with their difference.
  c.DIAGNOSTIC_IMPACT.rows[0][2]=60;c.DIAGNOSTIC_IMPACT.rows[0][3]=72;
  const measured=c.renderCollectionPage(model).all().find(n=>n.attrs['data-impact']==='memory').text();
  assert(measured.includes('+20 %'),measured);
}
// The note on statistics surfaces lives in the main page.
const m={locale:'ru',Date,Math,Number,String,Object,Array,JSON};m.bi=(en,ru)=>ru;m.E=node;
vm.createContext(m);vm.runInContext(fs.readFileSync('router/probe_panel.inc.js','utf8'),m);
assert.strictEqual(m.statsWorkNote({}),'','an older router reports no mode: no note');
const note=m.statsWorkNote({stats_mode:{mode:'work'}});assert(note.text().includes('Сбор статистики выключен'));
assert(note.all().some(n=>n.attrs.href==='#collection'),'the note links to the Statistics collection page');
assert.strictEqual(m.statsWorkNote({stats_mode:{mode:'diagnostic',until:Date.now()/1000+3600}}),'');
const built=fs.readFileSync('router/build_sidebar_ui.py','utf8');
assert(built.includes("['collection','◎',bi('Statistics collection','Сбор статистики')]"),'an Advanced menu item');
assert(!built.includes('statsSettings('),'no longer hidden among the general settings');
console.log('PASS: statistics collection page');
})().catch(e=>{console.error(e);process.exit(1);});
