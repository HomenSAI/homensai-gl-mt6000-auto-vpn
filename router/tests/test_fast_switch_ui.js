// Settings: the owner checkbox for the fast channel switch lives with the response settings and is saved as one setup_response call.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
function node(tag,attrs,children){const n={tag,attrs:attrs||{},children:[],listeners:{},addEventListener(e,f){this.listeners[e]=f;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},appendChild(c){this.children.push(c);}};
  [].concat(children||[]).forEach(c=>{if(c!==null&&c!==undefined)n.children.push(c);});
  n.text=function(){return this.children.map(c=>typeof c==='string'?c:c.text?c.text():'').join('');};
  n.all=function(){return [this].concat(...this.children.filter(c=>c&&c.all).map(c=>c.all()));};return n;}
(async()=>{
for(const language of ['en','ru']){
  for(const stored of [undefined,true,false]){
    const c={locale:language,Date,Math,Number,String,Object,Array,JSON,Promise,calls:[]};
    c.bi=(en,ru)=>language==='ru'?ru:en;c.E=node;c.ui={addNotification(){}};
    c.rpc={declare:(spec)=>(...args)=>{c.calls.push([spec.method,spec.params].concat(args));return Promise.resolve({saved:true});}};
    vm.createContext(c);vm.runInContext(fs.readFileSync('router/probe_panel.inc.js','utf8'),c);
    const settings={response_metric:'icmp-1.1.1.1',response_compare:false};if(stored!==undefined)settings.fast_switch=stored;
    const panel=c.responseSettings({settings}),all=panel.all();
    const box=all.find(n=>n.attrs['class']==='hv-fast-switch'),save=all.find(n=>n.tag==='button');
    assert(box,'the fast switch checkbox is in the response settings');
    assert.strictEqual(box.checked,stored!==false,'default on; only an explicit off is shown unchecked');
    assert(panel.text().includes(language==='ru'?'Быстрое переключение (без перестройки GL)':'Fast switch (without the GL rebuild)'));
    assert('disabled' in save.attrs,'nothing to save yet');
    box.checked=!box.checked;box.listeners.change();assert(!('disabled' in save.attrs),'a changed checkbox can be saved');
    box.checked=!box.checked;box.listeners.change();assert('disabled' in save.attrs,'back to the stored value: nothing to save');
    box.checked=!box.checked;box.listeners.change();const wanted=box.checked;
    save.listeners.click();await new Promise(r=>setTimeout(r,0));
    const call=c.calls.pop();
    assert.strictEqual(JSON.stringify(call),JSON.stringify(['setup_response',['metric','compare','fast_switch','ping_interval'],'icmp-1.1.1.1',false,wanted,60]));
    assert('disabled' in save.attrs,'saved: the button waits for the next change');
  }
}
// Instant owner switch: the countdown expects seconds, not the guarded automatic transaction's average.
for(const language of ['en','ru']){
  const c={locale:language,Date,Math,Number,String,Object,Array,JSON};c.bi=(en,ru)=>language==='ru'?ru:en;c.E=node;
  vm.createContext(c);vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),c);
  c.UI_SWITCH_AVG=30;
  assert(c.uiOperationTimer(null,1,null,false,true).includes('0:04'),'instant: about four seconds expected');
  assert(c.uiOperationTimer(null,1,null,false,false).includes('0:38'),'guarded: average + 25%');
  assert(c.uiOperationTimer(null,1,null,false).includes('0:38'),'no flag: guarded');
}
console.log('PASS: fast switch setting');
})().catch(e=>{console.error(e);process.exit(1);});
