const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(v=>v!=null);this.textContent='';}appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0]||null;}setAttribute(k,v){this.attrs[k]=v;}all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}text(){return [this.textContent,...this.children.map(n=>n instanceof N?n.text():n)].join(' ');}}
async function main(){
 const now=100000,events=Array.from({length:130},(_,i)=>({sequence:i+1,time:now-130+i,state:i===0?'SPECIAL-OLD-EVENT':'OBSERVING'})),methods=[];
 const c={locale:'en',bi:a=>a,E:(...a)=>new N(...a),Date,statusNow:()=>now,safeCode:v=>typeof v==='string'&&/^[A-Z][A-Z0-9-]+$/.test(v),serverTitle:p=>p.name||p.id,rpc:{declare:spec=>{methods.push(spec.method);return async(kind,after,until)=>{const rows=kind==='controller'?events:[],fixed=rows.length,selected=rows.filter(r=>r.sequence>after).slice(0,100);return {kind,until:fixed,events:selected,next_after:selected.length?selected[selected.length-1].sequence:after,has_more:!!selected.length&&selected[selected.length-1].sequence<fixed,summary:{sequence:fixed},as_of:now};};}}};
 vm.createContext(c);for(const file of ['analytics_panel','journal_panel'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
 const status={profiles:[],native_history:{events:events.slice(-10)},accounting:{reliability:{events:[]}}};
 let root=c.renderEventHistory(status);assert.equal(root.all().filter(n=>n.tag==='tbody')[0].children.length,10);
 const search=root.all().find(n=>n.attrs.type==='search');search.attrs.input({target:{value:'SPECIAL-OLD-EVENT'}});
 await new Promise(resolve=>setImmediate(resolve));
 assert(c.EVENT_VIEW.stored&&c.EVENT_VIEW.stored.controller.events.length===130,'all pages are loaded for searching, not only the visible ten');
 assert.equal(root.all().find(n=>n.tag==='tbody').children.length,1);assert(root.text().includes('SPECIAL-OLD-EVENT'));
 assert.strictEqual(c.renderEventHistory(status),root,'polling retains search input/focus/reading DOM');assert.equal(c.EVENT_VIEW.query,'SPECIAL-OLD-EVENT');
 search.attrs.input({target:{value:''}});assert.equal(root.all().find(n=>n.tag==='tbody').children.length,10);
 const more=root.all().find(n=>n.tag==='button'&&n.attrs['aria-expanded']);more.attrs.click();assert.equal(root.all().find(n=>n.tag==='tbody').children.length,130);more.attrs.click();assert.equal(root.all().find(n=>n.tag==='tbody').children.length,10);
 const order=root.all().find(n=>n.tag==='select');order.attrs.change({target:{value:'state'}});assert.equal(c.EVENT_VIEW.sort,'state');assert(methods.every(v=>v==='statistics'),'history is read-only and does not dispatch any runtime control');
 console.log('PASS: ten-row disclosure, full130-event paginated search beyond visible rows, state/date controls and stable search DOM with statistics-only RPC');
}
main().catch(e=>{console.error(e);process.exit(1);});
