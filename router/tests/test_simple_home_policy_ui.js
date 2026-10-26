const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={};vm.createContext(context);vm.runInContext(fs.readFileSync('router/simple_home_policy.inc.js','utf8'),context);
const ready={termsAccepted:true,onboardingComplete:true,setupComplete:true,pairValid:true,statusFresh:true,controllerFresh:true,autoRunning:true};
assert.equal(context.simpleHomeEntry(ready).page,'home');
assert.equal(context.simpleHomeEntry(ready).autoRunning,true);
for(const key of ['statusFresh','controllerFresh','autoRunning'])for(const value of [false,undefined,null,'true',1]){
 const result=context.simpleHomeEntry({...ready,[key]:value});
 assert.equal(result.showCard,true,key+' is a displayed state, not an access gate');
 assert.equal(result.autoRunning,false,key+' must be explicitly true to assert running Auto');
}
for(const key of ['termsAccepted','onboardingComplete','setupComplete','pairValid','testsPassed','testsMatchCurrentPair','activePathConfirmed']){
 const result=context.simpleHomeEntry({...ready,[key]:false});assert.equal(result.showCard,true);assert.equal(result.autoRunning,true,'UI completion flags cannot replace actual fresh Auto evidence');
}
for(const flags of [{},{autoRunning:false},{autoRunning:false,localStorageReady:true},{autoRunning:true,localStorageReady:true}]){
 const result=context.simpleHomeEntry(flags);assert.equal(result.page,'home');assert.equal(result.autoRunning,false);
}
assert.equal(context.simpleHomeEntry({...ready,selectedRole:'target',primaryHealthy:false}).autoRunning,true);
console.log('PASS: Minimum is accessible ON/OFF/UNKNOWN; only strict fresh running evidence asserts Auto, never UI completion or browser storage.');
