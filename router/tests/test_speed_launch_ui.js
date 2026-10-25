const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).filter(v=>v!=null);this.disabled=attrs.disabled!=null;this.value=attrs.value||'';}
 appendChild(n){this.children.push(n);return n;}get firstChild(){return this.children[0];}removeChild(n){this.children.splice(this.children.indexOf(n),1);}
 setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}
}
function walk(n){return n instanceof N?[n,...n.children.flatMap(walk)]:[];}
function text(n){return n instanceof N?(n.textContent||'')+n.children.map(text).join(' '):String(n||'');}
function fixture(lang,enabled=false,save=true,accepted=true){
 const calls=[],notes=[],f={modal:null},c={Date,Intl,Number,locale:lang,bi:(en,ru)=>lang==='ru'?ru:en,E:(...a)=>new N(...a),document:{createElementNS:(_ns,tag)=>new N(tag)},serverTitle:p=>p.name,safeCode:s=>typeof s==='string',foolCheckNumber:()=>({ok:true}),guardResume:n=>n,guardedAction:(_n,fn)=>fn(),rpc:{declare:spec=>(...args)=>{calls.push({method:spec.method,args});return Promise.resolve(spec.method==='setup_speed'?{saved:save,code:save?null:'UCI-PENDING-CHANGES'}:{accepted,code:accepted?null:'SPEED-CPU-BUSY'});}},ui:{showModal:(_t,n)=>f.modal=n,hideModal:()=>f.modal=null,addNotification:(_x,n)=>notes.push(text(n))}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('router/speed_live.inc.js','utf8')+'\n'+fs.readFileSync('router/speed_table.inc.js','utf8'),c);
 const profiles=[{id:'wg',name:'Main WG',interface:'wg1'},{id:'ovpn',name:'Reserve OVPN',interface:'tun1'},{id:'off',name:'Offline'}];
 const inventory={settings:{speed_enabled:enabled,speed_auto_new:true,speed_budget_mib:8,speed_duration:5,speed_streams:2,speed_daily_mib:64,speed_busy_mbps:3}};
 const status={profiles,speed_tests:{results:[],state:'IDLE'}},panel=c.speedPanel(status,inventory,'week',()=>{});
 return Object.assign(f,{c,calls,notes,panel,inventory,status,button:walk(panel).find(n=>n.tag==='button'&&n.attrs.class.includes('hv-primary-action'))});
}
(async()=>{
 for(const lang of ['en','ru']){
  let f=fixture(lang);assert(!f.button.disabled);assert.equal(f.calls.length,0,'render does not enable or run');
  const boxes=walk(f.panel).filter(n=>n.attrs['data-id']);assert.deepEqual(boxes.map(n=>n.checked),[true,true]);
  f.button.attrs.click();assert(f.modal);assert(f.modal.every(Boolean),'modal never receives null nodes');assert.equal(f.calls.length,0,'review is read-only');assert(text(new N('div',{},f.modal)).includes(lang==='en'?'Automatic tests':'Автотесты'));
  const confirm=walk(new N('div',{},f.modal)).filter(n=>n.tag==='button').at(-1);await confirm.attrs.click({currentTarget:confirm});
  assert.deepEqual(f.calls.map(r=>r.method),['setup_speed','speed_start']);assert.deepEqual(f.calls[0].args,[true,false,8,5,2,64,3]);assert.deepEqual(Array.from(f.calls[1].args[0]),['wg','ovpn']);assert.equal(f.inventory.settings.speed_auto_new,false);
  f=fixture(lang,false,false);f.button.attrs.click();let b=walk(new N('div',{},f.modal)).filter(n=>n.tag==='button').at(-1);await b.attrs.click({currentTarget:b});assert.deepEqual(f.calls.map(r=>r.method),['setup_speed'],'unconfirmed enable never starts');assert.equal(f.c.speedFeedback,'UCI-PENDING-CHANGES');
  f=fixture(lang,true,true,false);f.button.attrs.click();b=walk(new N('div',{},f.modal)).filter(n=>n.tag==='button').at(-1);await b.attrs.click({currentTarget:b});assert.deepEqual(f.calls.map(r=>r.method),['speed_start']);assert.equal(f.c.speedFeedback,'SPEED-CPU-BUSY');assert(text(f.c.speedPanel(f.status,f.inventory,'week',()=>{})).includes(lang==='en'?'CPU is busy':'Процессор роутера занят'));
  f=fixture(lang);f.status.speed_tests.state='RUNNING';assert(walk(f.c.speedPanel(f.status,f.inventory,'week',()=>{})).find(n=>n.tag==='button'&&n.attrs.class.includes('hv-primary-action')).disabled);
  f=fixture(lang);const now=Date.now()/1000;let rows=[1,2,3,4,5].map(i=>({id:'wg',time:now+i,download:{mbps:10*i},upload:{mbps:3*i},code:i===3?'SPEED-NETWORK':null}));
  const chart=f.c.renderSpeedChart(rows,f.status.profiles,'week'),nodes=walk(chart);
  assert.equal(nodes.filter(n=>n.tag==='circle').length,8);assert.equal(nodes.filter(n=>n.tag==='polyline').length,4,'failures split both series');assert(nodes.find(n=>n.tag==='svg').attrs['aria-label']);
  assert.equal(f.c.speedChartValue({code:'FAIL',download:{mbps:0}},'download'),null);assert.equal(f.c.speedChartValue({download:{mbps:NaN}},'download'),null);assert.equal(f.c.speedChartSamples(rows,'wg','latest').length,1);
  const select=nodes.find(n=>n.tag==='select');select.attrs.change({target:{value:'ovpn'}});assert.equal(walk(chart).filter(n=>n.tag==='circle').length,0,'server selector never borrows another server samples');
 }
 console.log('PASS: review-only enable/manual-start, preserved limits, auto-new OFF, guarded failed enable/CPU/busy, real-sample chart with error gaps and independent server selection EN/RU');
})().catch(e=>{console.error(e);process.exitCode=1;});
