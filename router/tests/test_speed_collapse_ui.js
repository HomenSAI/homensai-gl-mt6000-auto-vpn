const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children);this.value=attrs.value||'';this.disabled=attrs.disabled!=null;}
 appendChild(n){this.children.push(n);return n;}
 setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}getAttribute(k){return this.attrs[k];}
 querySelectorAll(tag){return this.children.filter(n=>n instanceof N).flatMap(n=>[...(n.tag===tag?[n]:[]),...n.querySelectorAll(tag)]);}
 querySelector(tag){return this.querySelectorAll(tag)[0]||null;}
}
for(const lang of ['en','ru']){
 const observers=[],c={E:(...a)=>new N(...a),bi:(en,ru)=>lang==='ru'?ru:en,locale:lang,Date,Intl,serverTitle:p=>p.name,
  MutationObserver:class{constructor(fn){this.fn=fn;}observe(){observers.push(this.fn);}}};
 vm.createContext(c);for(const file of ['channel_guidance','speed_table'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
 const now=Date.now()/1000,profiles=Array.from({length:8},(_,i)=>({id:'vpn'+i,name:'Server '+i,interface:'wg'+i}));
 const results=profiles.map((p,i)=>({id:p.id,name:p.name,time:now-i,download:{mbps:100-i},upload:{mbps:50-i}}));
 const panel=c.speedPanel({profiles,speed_tests:{results}},{settings:{speed_enabled:true}},'latest',()=>{});
 const speed=panel.children.find(n=>n instanceof N&&n.attrs.class==='hv-limited-table');
 function check(host,total){
  const [table,button]=host.children,rows=()=>table.querySelectorAll('tr').filter(n=>n.querySelector('td'));
  const visible=()=>rows().filter(n=>!n.hidden&&!n.attrs['data-over-limit']);
  assert.equal(rows().length,total);assert.equal(visible().length,5);assert.equal(button.attrs['aria-expanded'],'false');
  const initial=visible().slice();assert.deepEqual(initial,rows().slice(0,5),'first five retain current order');
  button.attrs.click();assert.equal(visible().length,total);assert.equal(button.attrs['aria-expanded'],'true');
  button.attrs.click();assert.equal(visible().length,5);
  return {table,rows,visible,button};
 }
 check(speed,8);
 // Execute the actual ranking renderer with only its final host wrapped, as the builder does.
 const manifest=JSON.parse(fs.readFileSync('VERSION.json','utf8'));
 const built=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+manifest.application.ui_module+'.js','utf8');
 const start=built.indexOf("var ranking=E('table'"),newAnchor="addSearch('ranking',ranking);put('ranking',limitTableRows(ranking,5,'server-ranking-other'));",anchor=built.includes(newAnchor)?newAnchor:"addSearch('ranking',ranking);put('ranking',ranking);",end=built.indexOf(anchor,start)+anchor.length;
 assert(start>=0&&end>start);c.ranked=profiles.map(p=>({p,r:{n:30,good:30,sum:300}}));c.cell=v=>new N('td',{},v);c.tr=x=>x;c.rankConfidence=n=>n;c.addSearch=()=>{};
 let output;c.put=(_,node)=>{output=node;};
 vm.runInContext(built.slice(start,end).replace(anchor,"addSearch('ranking',ranking);put('ranking',limitTableRows(ranking,5,'server-ranking-other'));"),c);
 const rank=check(output,8);rank.rows().forEach((row,i)=>row.hidden=i!==7);observers.forEach(fn=>fn());assert.equal(rank.visible().length,1);assert(rank.button.hidden,'search includes entries after the initial five');
 rank.rows().forEach(row=>row.hidden=false);rank.table.children=[rank.table.children[0],...rank.rows().reverse()];observers.forEach(fn=>fn());assert.equal(rank.visible().length,5,'sort reapplies limit to reordered rows');
 assert.equal(c.HV_DISCLOSURES['speed-other'],false);assert.equal(c.HV_DISCLOSURES['server-ranking-other'],false);
 const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');assert(builder.includes("put('ranking',limitTableRows(ranking,5,'server-ranking-other'))"));
}
console.log('PASS: speed results and server ranking each show first five, independent expansion, full ranking search/sort, EN/RU');
