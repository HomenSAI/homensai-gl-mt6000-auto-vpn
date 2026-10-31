// Owner request 31 Oct 2026: (1) the setup sections are on top of the menu, and the page opens on Getting started,
// only while the system is being set up; once it is set up the Overview is first. (2) System readiness never shows
// "waiting" for parts that the running system already proves, and an old router report is shown with its age.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const store={};
const c={window:{localStorage:{getItem:k=>Object.prototype.hasOwnProperty.call(store,k)?store[k]:null,setItem:(k,v)=>{store[k]=String(v);}}},
  bi:(en)=>en,locale:'en',console};
c.E=function(tag,attrs,children){const kids=[].concat(children===undefined?[]:children).filter(x=>x!==null&&x!==undefined&&x!==false);
  return {tag,attrs:attrs||{},children:kids,get text(){return kids.map(k=>typeof k==='string'?k:k.text).join(' ');}};};
vm.createContext(c);
for(const file of ['router/auto_panel.inc.js','router/summary_panel.inc.js','router/readiness_panel.inc.js'])vm.runInContext(fs.readFileSync(file,'utf8'),c,{filename:file});

const NOW=1792750000;
const pair={settings:{setup_complete:true,plan_source:'wireguard:peer_1',plan_target:'openvpn:1_2'},profiles:[],servers:[]};
const fresh={time:NOW-5,server_time:NOW,auto_control:{requested:'off',requested_at:0},native_history:{retained_events:0},native_failover:{state:'STOPPED',time:NOW-5}};
const running=Object.assign({},fresh,{auto_control:{requested:'on',requested_at:NOW-600,pair_phase:'RUNNING'},lua_backend:{monitor:'lua'},
  native_failover:{state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,kernel_policy_verified:true,time:NOW-3}});
c.statusNow=()=>NOW;
const SETUP=['start','readiness','overview','channels','settings','help','learn'],WORK=['overview','channels','settings','help','learn','readiness','start'];
const order=(s,i)=>JSON.parse(JSON.stringify(c.sidebarOrder(s,i)));

// (1) the order rule
assert.deepEqual(order(fresh,{settings:{},profiles:[],servers:[]}),SETUP,'fresh install: setup first');
assert.equal(c.startLanding(fresh,{settings:{}}),'start','fresh install lands on Getting started');
assert.deepEqual(order(fresh,pair),SETUP,'pair saved but Auto never started: still setting up');
assert.deepEqual(order(running,pair),WORK,'Auto runs: Overview first');
assert.equal(c.startLanding(running,pair),'overview','set up: lands on the Overview');
assert.deepEqual(order(Object.assign({},fresh,{auto_control:{requested:'off',requested_at:NOW-86400}}),pair),WORK,'Auto started before and stopped since: still set up');
assert.deepEqual(order(Object.assign({},fresh,{native_history:{retained_events:3}}),pair),WORK,'controller history proves an earlier start');
assert.deepEqual(order({rpc_error:'RPC-UNAVAILABLE'},pair),WORK,'no status answer keeps the last decision (work)');
assert.deepEqual(order(fresh,{settings:{}}),SETUP);
assert.deepEqual(order({rpc_error:'RPC-UNAVAILABLE'},pair),SETUP,'no status answer keeps the last decision (setup)');
assert.deepEqual(order(running,{error:'RPC-INVENTORY-UNAVAILABLE',settings:{}}),SETUP,'unknown configuration never flips the menu');
// the live menu is reordered in place, the advanced toggle stays after the links, nothing moves when already in order
function node(key){return {key,getAttribute:n=>n==='data-hv-tab'?key:null,get nextSibling(){return nav.children[nav.children.indexOf(this)+1]||null;}};}
const toggle={key:'toggle',getAttribute:()=>null};
const nav={children:SETUP.map(node).concat([toggle]),moves:0,attrs:{},setAttribute(k,v){this.attrs[k]=v;},
  insertBefore(n,before){this.moves++;const list=this.children.filter(x=>x!==n);const at=before?list.indexOf(before):list.length;list.splice(at,0,n);this.children=list;}};
const root={querySelector:s=>s==='#hv-expanded-nav'?nav:null};
c.applySidebarOrder(root,c.SIDEBAR_WORK_ORDER);
assert.deepEqual(nav.children.map(n=>n.key),WORK.concat(['toggle']));assert.equal(nav.attrs['data-hv-order'],'work');
nav.moves=0;c.applySidebarOrder(root,c.SIDEBAR_WORK_ORDER);assert.equal(nav.moves,0,'no DOM move (focus kept) when the order is unchanged');
c.applySidebarOrder(root,c.SIDEBAR_SETUP_ORDER);assert.deepEqual(nav.children.map(n=>n.key),SETUP.concat(['toggle']));
// the generated page uses the same rule for the first menu, every refresh and the landing tab
// the current page module from the menu (the module name changes with every version)
const page=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'))['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
assert(page.includes('var links=sidebarOrder(data[1],inventory).map(tabLink)'),'first menu from the rule');
assert(page.includes('applySidebarOrder(appRoot,sidebarOrder(status,inventory))'),'every refresh applies the rule');
assert(!page.includes("['start','readiness','overview','channels','settings','help','learn'].map(tabLink)"),'no fixed setup-first menu');
assert(page.includes("startLanding(data[1],inventory)"),'landing tab from the same rule');
assert(/Promise\.all\(\['brand','robot','brand-ui'\]\.map/.test(page)&&page.includes('script.async=false'),'style scripts load in parallel, in order');
console.log('PASS: menu order and landing follow the setup state (fresh, pair only, running, stopped, history, RPC loss)');

// (2) readiness while Auto runs
let m=c.readinessModel(running,NOW);
const state=code=>(m.checks.find(r=>r.code===code)||{}).state;
const proof=code=>(m.checks.find(r=>r.code===code)||{}).proof;
for(const code of ['DEPENDENCY-UBUS','RPC-PLUGIN','DEPENDENCY-LUA','DEPENDENCY-UCI','DEPENDENCY-IP'])assert.equal(state(code),'pass',code+' proven while Auto runs');
assert.equal(proof('DEPENDENCY-IP'),'auto');assert.equal(proof('RPC-PLUGIN'),'page');
for(const code of ['PYTHON-39-MINIMUM','CA-BUNDLE','CONFIG-STORAGE-FREE'])assert.equal(state(code),undefined,code+' is not proven by Auto and is never invented');
const stopped=Object.assign({},running,{auto_control:{requested:'off',requested_at:NOW-10},native_failover:{state:'STOPPED',time:NOW-3}});
m=c.readinessModel(stopped,NOW);assert.equal(state('DEPENDENCY-IP'),undefined,'a stopped Auto proves nothing about ip');assert.equal(state('DEPENDENCY-UBUS'),'pass');
m=c.readinessModel(Object.assign({},running,{time:NOW-200}),NOW);assert.equal(m.checks.length,0,'a stale status proves nothing');
// a fresh router report: its states are kept, except a proven part
const report={time:NOW-20,board:{model:'GL.iNet GL-MT3000'},checks:[{code:'PYTHON-39-MINIMUM',state:'pass'},{code:'DEPENDENCY-IP',state:'fail'},{code:'CA-BUNDLE',state:'fail'}]};
m=c.readinessModel(Object.assign({},running,{system_readiness:report}),NOW);
assert.equal(m.environmentFresh,true);assert.equal(state('DEPENDENCY-IP'),'pass');assert.equal(proof('DEPENDENCY-IP'),'auto','the running Auto outweighs a failed PATH lookup');
assert.equal(state('CA-BUNDLE'),'fail','an unproven part keeps its real state');assert.equal(state('PYTHON-39-MINIMUM'),'pass');
// an old report is shown with its age instead of "waiting"
m=c.readinessModel(Object.assign({},fresh,{system_readiness:Object.assign({},report,{time:NOW-600})}),NOW);
assert.equal(m.environmentFresh,false);assert.equal(m.reported,true);assert.equal(Math.round(m.age),600);assert.equal(m.board.model,'GL.iNet GL-MT3000');
assert.equal((m.checks.find(r=>r.code==='CA-BUNDLE')||{}).stale,true);assert(m.blockers.includes('ENVIRONMENT-EVIDENCE-UNAVAILABLE'),'old evidence never counts as fresh for Auto');
assert.equal(c.readinessAge(600),'10 min ago');assert.equal(c.readinessAge(20),'20 s ago');
// the preparation card does not say "no information" while the running Auto proves its start check
c.helpLink=()=>null;
const text=c.renderPreparation(running,NOW).text;
assert(text.includes('Auto is running: its start check found every preparation item ready'),text.slice(0,200));
assert(c.renderPreparation(fresh,NOW).text.includes('Fresh preparation evidence is not available.'));
console.log('PASS: readiness shows the parts the running Auto and this page prove, keeps unproven states, and shows old reports with their age');
