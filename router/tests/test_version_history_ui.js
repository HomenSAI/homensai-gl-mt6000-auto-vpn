// Help "Speed by version": the per-version stage bars must agree with the measured runs they summarise.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const c={Math,Number,String,Object,Array,JSON,HELP_TOPICS:[]};c.bi=(en,ru)=>en;c.E=(tag,attrs,children)=>({tag,attrs,children});
vm.createContext(c);vm.runInContext(fs.readFileSync('router/measurements_help.inc.js','utf8')+';this.VH=VERSION_HISTORY;this.AM=AUTO_MEASUREMENTS;this.VS=VERSION_STAGES;',c);
const mean=a=>a.reduce((x,y)=>x+y,0)/a.length,total=v=>v.stages.reduce((x,y)=>x+y,0);
for(const v of c.VH.auto){
  const set=c.AM.find(s=>s.version===v.version&&s.level===3);assert(set,'measured runs for '+v.version);
  assert.strictEqual(set.rows.length,v.runs,v.version+' run count');
  assert(Math.abs(total(v)-mean(set.rows.map(r=>r[3])))<0.6,v.version+': stages add up to the mean time to traffic on the reserve');
  assert(Math.abs(v.stages[0]-mean(set.rows.map(r=>r[1])))<0.6,v.version+': noticed');
  assert(Math.abs(v.ret-mean(set.rows.map(r=>r[5]-r[4])))<0.6,v.version+': return');
  assert.strictEqual(v.stages.length,c.VS.auto.length);
}
for(const v of c.VH.manual)assert.strictEqual(v.stages.length,c.VS.manual.length,v.version+' manual stages');
assert(Math.abs(total(c.VH.manual[0])-42.2)<0.2,'beta7 manual return took 42.2 s');
assert(total(c.VH.manual[1])>14.5&&total(c.VH.manual[1])<20.3,'beta8 mean lies inside the measured 14.5-20.2 s');
assert(Math.abs(total(c.VH.manual[2])-9.9)<0.1,'beta9 mean 9.9 s (8.2-12.6 s)');
const versions=c.VH.auto.map(v=>v.version);assert.strictEqual(JSON.stringify(versions),JSON.stringify([...versions].sort()),'oldest first');
console.log('PASS: version history');
