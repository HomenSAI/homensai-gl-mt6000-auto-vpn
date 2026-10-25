const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('router/simple_home_policy.inc.js','utf8'),context);
const ready={termsAccepted:true,onboardingComplete:true,setupComplete:true,pairValid:true,pairDeferred:false,testsPassed:true,testsMatchCurrentPair:true,statusFresh:true,controllerFresh:true,autoRunning:true,commandPending:false,transitioning:false,activePathConfirmed:true,selectedRole:'source'};
assert.equal(context.simpleHomeEntry(ready).page,'home');
assert.equal(context.simpleHomeEntry({...ready,selectedRole:'target',primaryHealthy:false}).page,'home','Healthy reserve is not an unfinished setup');
const required=['termsAccepted','onboardingComplete','setupComplete','pairValid','testsPassed','testsMatchCurrentPair','statusFresh','controllerFresh','autoRunning','activePathConfirmed'];
for(const key of required){for(const value of [false,undefined,null,'true',1])assert.equal(context.simpleHomeEntry({...ready,[key]:value}).showCard,false,key+' must be explicitly true');}
for(const key of ['pairDeferred','commandPending','transitioning'])assert.equal(context.simpleHomeEntry({...ready,[key]:true}).showCard,false,key);
for(const role of ['unknown','',null,undefined])assert.equal(context.simpleHomeEntry({...ready,selectedRole:role}).showCard,false);
assert.equal(context.simpleHomeEntry({}).page,'terms');
assert.equal(context.simpleHomeEntry({...ready,termsAccepted:false,onboardingComplete:false,autoRunning:false}).page,'terms');
assert.equal(context.simpleHomeEntry({...ready,onboardingComplete:false,testsPassed:false}).page,'setup');
assert.equal(context.simpleHomeEntry({...ready,testsPassed:false,autoRunning:false}).page,'tests');
assert.equal(context.simpleHomeEntry({...ready,autoRunning:false}).page,'full');
assert.equal(context.simpleHomeEntry({...ready,testsMatchCurrentPair:false,localStorageReady:true}).showCard,false);
console.log('PASS: startup terms/setup/current-pair tests/fresh confirmed Auto gate; no truthy shortcuts, stale data, queued commands or invalid role; working reserve accepted.');
