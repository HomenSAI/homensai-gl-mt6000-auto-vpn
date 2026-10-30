// Probe level slider, automatic boost checkbox and the decision log wording.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
function node(tag,attrs,children){const n={tag,attrs:attrs||{},children:[],listeners:{},addEventListener(e,f){this.listeners[e]=f;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},appendChild(c){this.children.push(c);}};
  [].concat(children||[]).forEach(c=>{if(c!==null&&c!==undefined)n.children.push(c);});
  n.text=function(){if(typeof this.textContent==='string')return this.textContent;return this.children.map(c=>typeof c==='string'?c:c.text?c.text():'').join('');};
  n.all=function(){return [this].concat(...this.children.filter(c=>c&&c.all).map(c=>c.all()));};return n;}
for(const language of ['en','ru']){
  const c={locale:language,Date,Math,Number,String,Object,Array,JSON,Promise,calls:[]};
  c.bi=(en,ru)=>language==='ru'?ru:en;c.E=node;c.ui={addNotification(){}};
  c.rpc={declare:(spec)=>(...args)=>{c.calls.push([spec.method].concat(args));return Promise.resolve({saved:true,events:[]});}};
  vm.createContext(c);vm.runInContext(fs.readFileSync('router/probe_panel.inc.js','utf8'),c);
  // Every level states its cadence and the detection time; the boost shortens it.
  for(const level of [1,2,3,4,5]){const t=c.probeLevelText(level,false);assert(/\d+/.test(t)&&t.includes(String(c.PROBE_LEVELS[level][0])),'level '+level+' cadence');}
  assert(c.probeLevelText(1,true).includes(language==='ru'?'без ускорения 180':'without boost 180'),'boost shortens economy detection');
  // Panel: slider 1-5, checkbox, Apply disabled until something changes.
  const status={probe_policy:{level:3,boost_enabled:true,boost_active:false,interval:20,measure_interval:60}};
  const panel=c.renderProbeControl(status,{settings:{}}),all=panel.all();
  const slider=all.find(n=>n.attrs.type==='range'),box=all.find(n=>n.attrs.type==='checkbox'),apply=all.find(n=>n.tag==='button');
  assert.equal(slider.attrs.value,'3');assert.equal(slider.attrs.min,'1');assert.equal(slider.attrs.max,'5');assert.strictEqual(box.checked,true);
  assert('disabled' in apply.attrs,'nothing to apply yet');
  slider.value='1';slider.listeners.input();assert(!('disabled' in apply.attrs),'a new level can be applied');
  apply.listeners.click();assert.deepStrictEqual(c.calls.pop(),['setup_probe',1,true]);
  assert(panel.text().includes(language==='ru'?'Автоматическое ускорение':'Automatic boost'));
  assert(panel.text().includes(language==='ru'?'10 минут':'10 minutes'),'the boost is explained');
  // Active boost is shown with its channel and code.
  c.PROBE_DRAFT=null;c.PROBE_SECTION=null;const boosted=c.renderProbeControl({probe_policy:{level:2,boost_enabled:true,boost_active:true,boost_until:Date.now()/1000+300,boost_trigger:{role:'source',code:'VPN-003'}}},{settings:{}});
  assert(boosted.text().includes(language==='ru'?'основной канал':'primary channel')&&boosted.text().includes('VPN-003'));
  // No policy from the router: nothing invented.
  c.PROBE_SECTION=null;assert.equal(c.renderProbeControl({},{settings:{}}),null);
  // Decision log: level choice, boost start and every result have a decision and a reason.
  const level=c.probeDecision({kind:'level',level:2,interval:30,measure_interval:120,boost_enabled:false});
  assert(level[0].includes('2')&&level[1].includes('30')&&level[1].includes('120'));
  const start=c.probeDecision({kind:'boost-start',level:1,interval:60,measure_interval:300,role:'target',boost_interval:10});
  assert(start[1].includes(language==='ru'?'резервный канал':'reserve channel')&&start[1].includes('10'));
  for(const result of ['switched','failure-confirmed','false-alarm','disabled']){
    const d=c.probeDecision({kind:'boost-end',level:3,interval:20,measure_interval:60,role:'source',result,failures:3,duration:600});
    assert(d[0].length>5&&d[0]!==result&&d[1].includes('10'),'result '+result+' is explained');
  }
  // Suspicion episodes: the reason is explained and the log says a suspicion alone never switches.
  for(const reason of ['rx-stall','wg-handshake-stale','link-missing']){
    const s=c.probeDecision({kind:'suspicion-start',level:1,interval:60,measure_interval:300,role:'source',reason,evidence:{stalled_s:7},dense_interval:4});
    assert(s[0].length>5&&!s[1].includes(reason)&&s[1].includes('4')&&s[1].includes(language==='ru'?'никогда не переключает':'never switches'),'suspicion '+reason);
  }
  for(const result of ['false-alarm','failure-confirmed','switched','expired','cancelled']){
    const d=c.probeDecision({kind:'suspicion-end',level:1,interval:60,measure_interval:300,role:'target',reason:'rx-stall',result,failures:3,checks:4,duration:21});
    assert(d[0].length>5&&d[0]!==result&&d[1].includes('21')&&d[1].includes(language==='ru'?'резервный канал':'reserve channel'),'suspicion result '+result);
  }
}
console.log('PASS: probe level slider, boost checkbox, active boost and decision log wording (EN/RU)');
// Yellow pulse around the scheduled check: 1 s before, through the check, 1 s after the router's answer.
{
  const c={locale:'ru',Date:{now:()=>c.nowMs},Math,Number,String,Object,Array,JSON,Promise,calls:[],nowMs:100000};
  c.bi=(en,ru)=>ru;c.E=node;c.statusNow=()=>c.nowMs/1000;vm.createContext(c);vm.runInContext(fs.readFileSync('router/probe_panel.inc.js','utf8'),c);
  const status=t=>({time:t,probe_policy:{effective_interval:10}});
  c.probeCheckSchedule(status(100));                 // next check at 110 s
  c.nowMs=105000;assert(!c.probeCheckPulse(),'green well before the check');
  c.nowMs=109200;assert(c.probeCheckPulse(),'yellow one second before the check');
  c.nowMs=112000;assert(c.probeCheckPulse(),'yellow through the check');
  c.nowMs=113500;assert(!c.probeCheckPulse(),'then back to the base colour, without waiting for the next poll');
  c.probeCheckSchedule(status(110.5));               // the router's answer for that check arrives later
  c.nowMs=114000;assert(!c.probeCheckPulse(),'an arriving answer does not re-light yellow');
  c.nowMs=119500;assert(c.probeCheckPulse(),'the next check pulses again');
  // A slider choice moves the schedule to the new interval at once.
  c.PROBE_APPLIED={level:1,boost:true,at:c.nowMs};c.probeCheckSchedule(status(119));
  assert.equal(c.PROBE_SCHEDULE.interval,60,'countdown follows the applied level before the router publishes it');
}
console.log('PASS: check pulse and applied-level countdown');
