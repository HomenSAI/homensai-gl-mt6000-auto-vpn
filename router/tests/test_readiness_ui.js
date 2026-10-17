const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync('router/readiness_panel.inc.js','utf8'),c);
let s={time:100,system_readiness:{time:100,board:{model:'x86'},checks:[{code:'UBUS',state:'pass'}]},native_failover:{},auto_control:{requested:'on'}};
let m=c.readinessModel(s,101);assert.equal(m.environmentFresh,true);assert.equal(m.board.model,'x86');assert(m.blockers.includes('NATIVE-START-CERTIFICATION-REQUIRED'));
for(const now of [99,191,Infinity]){m=c.readinessModel(s,now);assert.equal(m.environmentFresh,false);assert.equal(m.auto,'off_or_unknown');assert(m.blockers.includes('MONITOR-EVIDENCE-STALE'));}
s.rpc_error=true;assert.equal(c.readinessModel(s,101).fresh,false);
assert.equal(c.readinessModel({},101).checks.length,0);
const css=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/ui27.css','utf8');assert(css.includes('.hv-app input.hv-search{box-sizing:border-box!important'));
console.log('PASS: readiness unknown/future/stale/RPC refusal and actual-LuCI search sizing guard');

const dashboard=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/dashboard49.js','utf8');assert(dashboard.indexOf("'require rpc'")<dashboard.indexOf('var RECOVERY_PRESETS='));assert(dashboard.replace(/^\/\/[^\n]*\n/,'').trimStart().startsWith("'use strict';"));
