const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:(en)=>en,locale:'en'};vm.createContext(c);vm.runInContext(fs.readFileSync('router/ui_logic.inc.js','utf8'),c);
const row=(id,code=null,time=990)=>({id,interface:'vpn'+id,time,code,dns_ok:true,https_success:2});
assert.equal(c.profileHealth(row('a'),1000).state,'healthy');
assert.equal(c.profileHealth({...row('a'),dns_ok:undefined},1000).state,'checking');
assert.equal(c.profileHealth(row('a','VPN-003'),1000).state,'failed');
assert.equal(c.profileHealth(row('a',null,800),1000).state,'unknown');
assert.equal(c.profileHealth(row('a','CHECK-001'),1000).state,'checking');
let rows=[row('a'),row('b','DNS-001'),row('c'),{...row('d'),interface:null}];
// Owner P3: fixed roles (primary, reserve) on top; the active route never moves a row.
assert.deepEqual(Array.from(c.sortServerCards(rows,'c',1000),r=>r.id),['a','c','d','b'],'selected route is not promoted');
assert.deepEqual(Array.from(c.sortServerCards(rows,'c',1000,['b','c']),r=>r.id),['b','c','a','d'],'primary first even when failed, reserve second, others by health');
assert.deepEqual(Array.from(c.sortServerCards(rows,'b',1000,['b','c']),r=>r.id),Array.from(c.sortServerCards(rows,'c',1000,['b','c']),r=>r.id),'switching the active route keeps the row order');assert.equal(rows[0].id,'a');
assert.equal(c.selectedProfile({native_failover:{state:'COMMITTED',target:'c',time:999}},1000),'c');
assert.equal(c.selectedProfile({native_failover:{state:'COMMITTED',target:'c',time:800}},1000),null);
assert.equal(c.selectedProfile({native_failover:{state:'APPLYING',target:'c',time:999}},1000),null);
for(const direction of ['asc','desc'])assert(c.compareTableValues('—','10',direction)>0);
assert(c.compareTableValues('2','10','asc')<0);assert(c.compareTableValues('2','10','desc')>0);
assert(c.compareTableValues('5%','10%','asc')<0);assert(c.compareTableValues('Server 2','Server 10','asc')<0);
console.log('PASS: health freshness, selected-first stable ordering, unknown-last sorting');

// Ranking trust: sparse servers are labelled and never lead.
{
  const fs2=require('fs'),vm2=require('vm');
  const ctx={bi:(en)=>en};vm2.createContext(ctx);vm2.runInContext(fs2.readFileSync('router/ui_logic.inc.js','utf8'),ctx);
  const a=require('assert');
  a.equal(ctx.rankEnough(19),0);a.equal(ctx.rankEnough(20),1);a.equal(ctx.rankEnough(0),0);
  a.equal(ctx.rankConfidence(3),'3 · too few to rank');a.equal(ctx.rankConfidence(50),'50 · fair');a.equal(ctx.rankConfidence(500),'500 · good');
  const rows=[{n:2,good:2},{n:200,good:190},{n:25,good:20}].sort((x,y)=>(ctx.rankEnough(y.n)-ctx.rankEnough(x.n))||(y.good/y.n-x.good/x.n));
  a.deepEqual(rows.map(r=>r.n),[200,25,2]);   // the 100%-of-2 server is last
  const generated=fs2.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+JSON.parse(fs2.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'))['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
  a(generated.includes('rankConfidence(item.r.n)')&&generated.includes('rankEnough(b.r.n)-rankEnough(a.r.n)'));
  console.log('PASS: ranking shows the number of checks and puts sparse servers last');
}
