const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=Object.assign({},attrs);this.children=[].concat(children).filter(v=>v!=null);this.textContent=this.children.filter(v=>typeof v==='string').join('');this.parentNode=null;this.children.forEach(c=>{if(c instanceof N)c.parentNode=this;});}
 appendChild(n){if(n.parentNode)n.parentNode.children.splice(n.parentNode.children.indexOf(n),1);this.children.push(n);n.parentNode=this;return n;}
 get lastChild(){return this.children[this.children.length-1]||null;}
 getAttribute(k){return this.attrs[k];}setAttribute(k,v){this.attrs[k]=String(v);}removeAttribute(k){delete this.attrs[k];}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
 querySelectorAll(sel){const m=sel.match(/^\[([a-z-]+)(?:="([^"]*)")?\]$/);return this.all().slice(1).filter(n=>n.attrs&&m&&n.attrs[m[1]]!==undefined&&(m[2]===undefined||n.attrs[m[1]]===m[2]));}
 querySelector(sel){return this.querySelectorAll(sel)[0]||null;}
}
const calls=[],modals=[],notes=[];let statusReply=null;
const c={bi:(en)=>en,E:(t,a,ch)=>new N(t,a,ch),setTimeout:(f)=>f(),Promise,Date,window:{pageYOffset:0,scrollTo(){}},
 document:{querySelector:()=>null},
 ui:{showModal:(title,nodes)=>modals.push({title,nodes}),hideModal(){},addNotification:(_t,n)=>notes.push(n)},
 rpc:{declare:(o)=>(...args)=>{calls.push({method:o.method,args});return Promise.resolve(o.method==='stats_reset'?{queued:true,nonce:'n1'}:statusReply);}}};
vm.createContext(c);
const src=fs.readFileSync('router/summary_panel.inc.js','utf8');
const start=src.indexOf('/* "Reset chart"'),end=src.indexOf('function showErrorCode')>0?src.length:src.length;
vm.runInContext(src.slice(start),c);

// Every marked card gets exactly one reset button, also after a repeated page refresh.
const page=new N('div',{},[new N('section',{'data-stats-reset':'latency'}),new N('details',{'data-stats-reset':'auto'}),new N('section',{})]);
assert.equal(c.attachStatsResets(page),2);assert.equal(c.attachStatsResets(page),0,'no duplicate buttons');
const buttons=page.querySelectorAll('[data-stats-reset-button]');assert.deepEqual(buttons.map(b=>b.attrs['data-stats-reset-button']),['latency','auto']);
assert.equal(buttons[0].textContent,'Reset chart');
console.log('PASS: one Reset chart button per chart and statistics card');

// Pressing asks first; nothing is sent until the owner confirms.
buttons[1].attrs.click({currentTarget:buttons[1]});assert.equal(calls.length,0,'confirmation comes first');
assert.equal(modals[0].title,'Reset the chart?');
const confirm=modals[0].nodes[1].children.find(n=>n instanceof N&&n.textContent==='Reset');
c.autoLivePoints=[{time:1}];statusReply={stats_reset:{nonce:'n1',done:true}};
(async()=>{
 await confirm.attrs.click();await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
 assert.deepEqual(calls[0],{method:'stats_reset',args:['auto']});
 assert.equal(notes.length,1,'success is reported only after the router confirms');assert.equal(c.autoLivePoints.length,0,'the live chart restarts too');
 assert.equal(buttons[1].disabled,false);
 console.log('PASS: confirmed reset is sent once and reported only after the router result');
 // A refusal shows its code in a window.
 statusReply={stats_reset:{nonce:'n1',done:false,code:'STATS-RESET-FAILED'}};modals.length=0;
 await c.statsResetRun('latency',buttons[0]);await new Promise(r=>setImmediate(r));
 assert.equal(modals[0].title,'Reset did not complete');
 console.log('PASS: failed reset shows a coded error window');
 // "Go back" returns to the previous page.
 c.pageBackRemember('overview',120);c.pageBackRemember('overview',300);c.pageBackRemember('tests',10);
 assert.deepEqual(c.PAGE_BACK_STACK.map(r=>r.page),['overview','tests']);
 const host=new N('div',{},[new N('section',{'data-hv-page':'events'})]);const back=c.pageBackPlace(host,'events');
 assert.equal(back.textContent,'← Go back');assert(!('hidden' in back.attrs));
 console.log('PASS: Go back button with remembered pages');
})().catch(e=>{console.error(e);process.exit(1);});
