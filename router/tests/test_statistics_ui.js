const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={bi:(en)=>en,locale:'en'};vm.createContext(c);
vm.runInContext(fs.readFileSync('router/analytics_panel.inc.js','utf8'),c);
const rows=c.storedStatisticsRows({native_history:{totals:{attempts:3,committed:2,automatic_committed:2,returns:1},weekly:{committed:1,automatic_committed:1},months:{'2026-10':{committed:2,automatic_committed:2}},events:Array.from({length:7},()=>({state:'COMMITTED'}))},accounting:{reliability:{totals:{outages:5,failed_checks:23,auto_observed_seconds:7200},weekly:{outages:2},months:{'2026-10':{outages:5}}}}});
assert.equal(rows[0].switches,2);assert.equal(rows[0].outages,5);assert.equal(rows[0].failed_checks,23);assert.equal(rows[0].auto_seconds,7200);
assert.equal(rows[1].switches,1);assert.equal(rows[1].outages,2);assert.equal(rows[2].period,'2026-10');
assert.equal(c.storedStatisticsRows({})[0].outages,undefined);
(async()=>{
 const calls=[];
 const result=await c.fetchStoredStatistics('controller',async(kind,after,until)=>{
  calls.push([kind,after,until]);
  return {kind,until:3,events:after===0?[{sequence:1},{sequence:2}]:[{sequence:3}],next_after:after===0?2:3,has_more:after===0,summary:{totals:{committed:1}},as_of:100};
 });
 assert.equal(result.events.length,3);assert.equal(calls[1][2],3);assert.equal(result.summary.totals.committed,1);
 for(const reply of [
  {kind:'controller',until:3,events:[],next_after:0,has_more:true,summary:{}},
  {kind:'controller',until:3,events:[{sequence:2},{sequence:1}],next_after:2,has_more:false,summary:{}},
  {kind:'controller',until:3,events:[{sequence:1}],next_after:2,has_more:false,summary:{}},
  {error:'RPC-UNAVAILABLE'}
 ])await assert.rejects(()=>c.fetchStoredStatistics('controller',async()=>reply),/STATISTICS-/);
 console.log('PASS: authoritative stored counters, weekly/monthly rows, full paginated export and malformed/cyclic response refusal');
})().catch(error=>{console.error(error);process.exitCode=1;});
