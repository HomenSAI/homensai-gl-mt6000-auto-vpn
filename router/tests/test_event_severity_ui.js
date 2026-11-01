const fs=require('fs'),vm=require('vm'),assert=require('assert');
// Event severity (owner request 01.11.2026): one grading function keyed by code, a severity column with a marker AND
// text, and sorting by severity next to date/state on "Events and errors".
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(v=>v!=null);this.textContent='';}appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0]||null;}setAttribute(k,v){this.attrs[k]=v;}all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}text(){return [this.textContent,...this.children.map(n=>n instanceof N?n.text():n)].join(' ');}}
const now=100000;
const c={locale:'ru',bi:(en,ru)=>ru,E:(...a)=>new N(...a),Date,statusNow:()=>now,safeCode:v=>typeof v==='string'&&/^[A-Z][A-Z0-9-]+$/.test(v),serverTitle:p=>p.name||p.id,rpc:{declare:()=>async()=>({events:[]})}};
vm.createContext(c);for(const file of ['ui_logic','analytics_panel','journal_panel'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);c.statusNow=()=>now;

const expect={
  critical:['ROLLBACK-GIVEN-UP','PAIR-RECOVERY-REQUIRED','JOURNAL-INTEGRITY-FAILED','HISTORY-CORRUPT','LUA-AUTO-FALLBACK','LUA-AUTO-LOAD-FAILED','GUARD-INSTALL-FAILED','GUARD-RETAINED','RESTART-INTERRUPTED-SWITCH','AUTO-OPTIONS-NOT-CLEARED','COMMAND-FAILED'],
  medium:['SOURCE-FAILED','ROLLED-BACK','VENDOR-WORKER-BUSY','RESTART-PROCESS','RESTART-INTERRUPTED-BOOT','RESTART-INTERRUPTED-RESERVE-HOLD','RESTART-INTERRUPTED-OPERATION','RESTART-INTERRUPTED-AUTO-OFF','VPN-001','DNS-FAILED','SPEED-START-FAILED','SOMETHING-NEW-AND-UNKNOWN'],
  low:['PAIR-WATCHING','PAIR-CONNECTING','VENDOR-SETTLING','CLIENT-STOP','EVENT-ROUTER-OBSERVATION','RESTART-CLEAN','RESTART-FIRST-START','OK','PRIMARY-STABLY-RECOVERED','TELEGRAM-DELIVERED']};
for(const [level,codes] of Object.entries(expect))for(const code of codes)assert.equal(c.eventSeverity({code,state:'OBSERVATION'}),level,code);
// the row state decides when there is no code; an unknown state and code are medium; the saved fault can raise a row
assert.equal(c.eventSeverity({state:'OBSERVING'}),'low');assert.equal(c.eventSeverity({state:'BLOCKED'}),'medium');
assert.equal(c.eventSeverity({state:'BRAND-NEW-STATE'}),'medium');assert.equal(c.eventSeverity({}),'medium');
assert.equal(c.eventSeverity({state:'ROLLED-BACK',code:'SUPERVISOR-RECOVERY',fault:'ROLLBACK-GIVEN-UP'}),'critical');
assert.equal(c.eventSeverity({state:'OK',code:'OK'}),'low');
// the level names (RU), never colour alone
assert.equal(c.eventSeverityText('critical'),'Критичная');assert.equal(c.eventSeverityText('medium'),'Среднекритичная');assert.equal(c.eventSeverityText('low'),'Некритичная');

// sorting: critical > medium > low, newest first inside a level; ascending reverses the levels
const rows=[{key:'a',time:10,state:'OBSERVING',code:'PAIR-WATCHING'},{key:'b',time:20,state:'BLOCKED',code:'ROLLBACK-GIVEN-UP'},{key:'c',time:30,state:'FAILURE',code:'VPN-001'},
  {key:'d',time:40,state:'BLOCKED',code:'GUARD-RETAINED'},{key:'e',time:50,state:'OBSERVING'}];
const sorted=(desc)=>c.filteredJournalRows(rows,{},'','severity',desc).map(r=>r.key).join('');
assert.equal(sorted(true),'dbcea');assert.equal(sorted(false),'eacdb');
assert.equal(c.filteredJournalRows(rows,{},'','time',true).map(r=>r.key).join(''),'edcba','date sort unchanged');
assert.deepEqual(c.filteredJournalRows(rows,{},'среднекритичная','time',true).map(r=>r.key),['c'],'search finds the severity text');

// the page: a severity column with a coloured marker and its text, and the severity sort option
const events=rows.map((r,i)=>({sequence:i+1,time:now-100+i,state:r.state,code:r.code}));
const root=c.renderEventHistory({profiles:[],native_history:{events},accounting:{reliability:{events:[]}}});
const head=root.all().find(n=>n.tag==='thead').text();assert(head.includes('Критичность'),head);
const marks=root.all().filter(n=>n.attrs['data-severity']);assert.equal(marks.length,events.length);
for(const m of marks){assert(m.text().trim().length>0,'text next to the marker');assert(m.children.some(k=>k instanceof N&&k.attrs['aria-hidden']==='true'&&/color:#/.test(k.attrs.style)),'marker');}
const select=root.all().find(n=>n.tag==='select');assert(select.children.some(o=>o.attrs.value==='severity'));
select.attrs.change({target:{value:'severity'}});assert.equal(c.EVENT_VIEW.sort,'severity');
assert.equal(root.all().find(n=>n.tag==='tbody').children[0].all().find(n=>n.attrs['data-severity']).attrs['data-severity'],'critical');
select.attrs.change({target:{value:'bogus'}});assert.equal(c.EVENT_VIEW.sort,'time');
console.log('PASS: severity by code (critical/medium/low, unknown medium), marker with text, severity sort and search');
