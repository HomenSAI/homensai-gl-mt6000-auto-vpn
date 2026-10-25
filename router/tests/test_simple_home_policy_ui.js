const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('router/simple_home_policy.inc.js','utf8'),context);
const ready={termsAccepted:true,onboardingComplete:true,setupComplete:true,pairValid:true,pairDeferred:false,testsPassed:true,testsMatchCurrentPair:true,statusFresh:true,controllerFresh:true,autoRunning:true,commandPending:false,transitioning:false,activePathConfirmed:true,selectedRole:'source'};
assert.equal(context.simpleHomeEntry(ready).page,'home');
assert.equal(context.simpleHomeEntry({...ready,selectedRole:'target',primaryHealthy:false}).page,'home','Healthy reserve is not an unfinished setup');
const required=['statusFresh','controllerFresh','autoRunning'];
for(const key of required){for(const value of [false,undefined,null,'true',1])assert.equal(context.simpleHomeEntry({...ready,[key]:value}).showCard,false,key+' must be explicitly true');}
for(const key of ['termsAccepted','onboardingComplete','setupComplete','pairValid','testsPassed','testsMatchCurrentPair','activePathConfirmed'])assert.equal(context.simpleHomeEntry({...ready,[key]:false}).showCard,true,key+' cannot block enabled Auto');
for(const key of ['pairDeferred','commandPending','transitioning'])assert.equal(context.simpleHomeEntry({...ready,[key]:true}).showCard,true,key);
for(const role of ['unknown','',null,undefined])assert.equal(context.simpleHomeEntry({...ready,selectedRole:role}).showCard,true,'Missing path is a display state, not an access restriction');
assert.equal(context.simpleHomeEntry({}).page,'full');
assert.equal(context.simpleHomeEntry({...ready,termsAccepted:false,onboardingComplete:false,autoRunning:false}).page,'full');
assert.equal(context.simpleHomeEntry({...ready,onboardingComplete:false,testsPassed:false}).page,'home');
assert.equal(context.simpleHomeEntry({...ready,testsPassed:false,autoRunning:false}).page,'full');
assert.equal(context.simpleHomeEntry({...ready,autoRunning:false}).page,'full');
assert.equal(context.simpleHomeEntry({...ready,autoRunning:false,localStorageReady:true}).showCard,false);
console.log('PASS: enabled Auto grants display access regardless of setup/tests/path flags; off, unknown and stale states never gain access from browser storage.');
