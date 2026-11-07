// Review F-55: the 24-hour tile is the route-selection share over the observed time with its coverage, not "availability".
// route_history records the selected channel even while it fails, so 10 s source + 10 s target + 1000 s unknown must not
// read as "100 % availability"; unknown time stays unknown.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const core=fs.readFileSync('router/ui/core.js','utf8');
function grab(name){const start=core.indexOf('function '+name+'(');assert(start>=0,name);let depth=0,i=core.indexOf('{',start);
  for(;i<core.length;i++){if(core[i]==='{')depth++;else if(core[i]==='}'&&--depth===0)break;}return core.slice(start,i+1);}
const c={};vm.createContext(c);vm.runInContext(grab('segmentSeconds')+'\n'+grab('routeShare'),c);
// Python RouteHistory for source@0, source@10, target@1010, target@1020 (router/tests/test_route_history.py)
const segments=[{start:0,end:10,kind:'source'},{start:10,end:1010,kind:'unknown'},{start:1010,end:1020,kind:'target'}];
const share=c.routeShare(segments,1020-86400,1020);
assert.equal(share.selected,20);assert.equal(share.known,20);assert.equal(share.unknown,1000);
assert.equal(share.share,1,'the selected route carried all observed time');
assert(Math.abs(share.coverage-20/86400)<1e-12,'coverage is 20 s of the day, not the whole day');
assert.equal(c.routeShare([],0,86400).share,null,'no observation: no percentage');
assert.equal(c.routeShare([{start:0,end:30,kind:'down'},{start:30,end:60,kind:'source'}],0,86400).share,0.5,'an outage of both channels counts against');
// the tile names what it measures and shows the coverage; the old "availability 24 h" wording is gone
assert(!core.includes("t('доступность за 24 ч','availability 24 h')"),'no availability claim from route selection');
assert(core.includes("'VPN route selected, 24 h'")&&core.includes("'маршрут через VPN выбран, 24 ч'"));
assert(/cover24/.test(grab('statsTiles')),'coverage shown next to the share');
console.log('PASS: route-selection share with coverage (10 s source + 10 s target + 1000 s unknown), no availability claim');
