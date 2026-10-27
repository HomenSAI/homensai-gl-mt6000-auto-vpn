const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={URL};vm.createContext(context);
for(const file of ['minimum_navigation.inc.js','navigation_context.inc.js','simple_home_policy.inc.js'])vm.runInContext(fs.readFileSync('router/'+file,'utf8'),context);
const aliases={overview:['home','summary'],start:['settings','setup'],tests:['diagnostics','checks'],readiness:['diagnostics','readiness'],services:['diagnostics','technical'],ranking:['diagnostics','speed'],statistics:['events','statistics'],traffic:['events','traffic'],learn:['help','training']};
for(const [alias,[page,subview]] of Object.entries(aliases)){
 const r=context.minimumRoute('#'+alias);assert.equal(r.page,page);assert.equal(r.subview,subview);assert(r.recognized);assert(r.legacy);
 assert.equal(context.minimumRoute(r.hash).hash,r.hash,'canonical route round-trips');
}
for(const page of ['home','channels','diagnostics','events','settings','help'])assert.equal(context.minimumRoute(page).page,page);
assert.equal(Array.from(context.MINIMUM_MAIN_PAGES).join(','),'channels,diagnostics,events,settings,help');
for(const raw of ['',null,{},'unknown','__proto__','constructor','help/topic','help/topic/a/b','help/topic/%2f','diagnostics/unknown','diagnostics/','home/summary/extra','%E0%A4%A','help/topic/%3Cscript%3E']){
 const r=context.minimumRoute(raw);assert.equal(r.page,'home',String(raw));assert(!r.recognized,String(raw));
}
assert.equal(context.minimumRoute('help/topic/RPC-UNAVAILABLE').topic,'RPC-UNAVAILABLE');
assert.equal(context.minimumRoute('help/topic/no-internet').hash,'help/topic/no-internet');
assert.equal(context.minimumRoute('diagnostics/checks').hash,'diagnostics');
assert.equal(context.minimumRouteFromUrl('http://router/?setup=telegram').hash,'settings/setup');
assert.equal(context.minimumRouteFromUrl('http://router/?setup=system#settings').hash,'settings/setup');
assert.equal(context.minimumRouteFromUrl('http://router/?setup=telegram#events/traffic').hash,'events/traffic');
assert.equal(context.minimumRouteFromUrl('http://router/?setup=telegram&setup=system').hash,'home');
let state=context.minimumNavigationState('home');assert.equal(context.minimumAdvancedRoute(state).hash,'channels');
state=context.minimumNavigationTransition(state,'events/traffic');
const previous=state;state=context.minimumNavigationTransition(state,'home');assert.equal(previous.route.hash,'events/traffic');assert.equal(context.minimumAdvancedRoute(state).hash,'events/traffic');
state=context.minimumNavigationTransition(state,'help/training');state=context.minimumNavigationTransition(state,'home');assert.equal(context.minimumAdvancedRoute(state).hash,'help/training');
for(const path of ['home','channels','diagnostics/speed','diagnostics/recovery','events/traffic','settings/setup','help/training','help/topic/no-internet']){
 const href=context.languageNavigationUrl('http://router/cgi-bin/luci/admin/services/homensai-vpn?keep=1#'+path,'ru',path),url=new URL(href);
 assert.equal(url.hash,'#'+path);assert.equal(url.searchParams.get('lang'),'ru');assert.equal(url.searchParams.get('keep'),'1');assert.equal(url.origin,'http://router');
 assert.equal(url.searchParams.get('hv_view'),path==='home'?'home':'full');
 assert.equal(context.minimumRouteFromUrl(href).hash,path);
}
assert.equal(new URL(context.languageNavigationUrl('http://router/#events/traffic','en','events')).hash,'#events/traffic');
assert.equal(new URL(context.languageNavigationUrl('http://router/#home','en','events')).hash,'#events');
assert.equal(new URL(context.languageNavigationUrl('http://router/?setup=telegram#settings/setup','en','settings/setup')).searchParams.get('setup'),'telegram');
assert(!new URL(context.languageNavigationUrl('http://router/?setup=telegram#events','ru','events')).searchParams.has('setup'));
assert.equal(new URL(context.languageNavigationUrl('http://router/#events','ru','unknown')).hash,'#home');
for(const evidence of [{},{statusFresh:false,controllerFresh:false,autoRunning:false},{statusFresh:true,controllerFresh:true,autoRunning:false},{statusFresh:true,controllerFresh:true,autoRunning:true},{statusFresh:'true',controllerFresh:1,autoRunning:true}]){
 const home=context.simpleHomeEntry(evidence);assert.equal(home.page,'home');assert.equal(home.showCard,true);
 assert.equal(home.autoRunning,evidence.statusFresh===true&&evidence.controllerFresh===true&&evidence.autoRunning===true);
}
assert.equal(context.simpleHomeEntry({}).reason,'CURRENT-STATUS-REQUIRED');
assert.equal(context.simpleHomeEntry({statusFresh:true,controllerFresh:true}).reason,'AUTO-NOT-CONFIRMED-RUNNING');
assert.equal(context.simpleHomeEntry({statusFresh:true,controllerFresh:true,autoRunning:true}).reason,'AUTO-READY-RUNNING');
// Exercise the generated routing handler, including a blocked Back/hash transition.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const selected=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
// Preserve the released five-section adapter regression independently of the
// owner's subsequently selected legacy-expanded/current-Minimum combination.
const generated=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/dashboard104.js','utf8');
if(generated.includes('var minimumCurrentRoute=minimumRouteFromUrl')){
 const a=generated.indexOf('    function showPage(key){'),b=generated.indexOf('    function put(key,node){',a);
 assert(a>=0&&b>a);
 let dirty=true,pendingLeave=null,leaveRequests=0,viewportResets=0;
 const attrs={},scope={querySelectorAll:()=>[],querySelector:()=>null,setAttribute:(k,v)=>attrs[k]=v};
 Object.assign(context,{
  activeTab:'settings',minimumCurrentRoute:context.minimumRoute('settings'),minimumNav:context.minimumNavigationState('settings'),minimumControlNodes:null,
  appRoot:scope,panel:scope,heading:null,subtitle:null,tabs:[],document:{body:{contains:()=>false}},
  window:{location:{href:'http://router/#settings',hash:'#settings'},history:{replaceState(_a,_b,url){context.window.location.href=url;context.window.location.hash=new URL(url).hash;}}},
  minimumSettingsDirty:()=>dirty,minimumSettingsCanLeave:()=>!dirty,
  minimumSettingsRequestLeave:fn=>{leaveRequests++;pendingLeave=fn;return false;},
  rememberPageViewport(){},minimumApplyRoute(){},updateSidebarLayout(){},revisitPageViewport(){viewportResets++;}
 });
 vm.runInContext(generated.slice(a,b),context);
 const navigationLine=generated.split('\n').find(line=>line.includes('    minimumNavigate=function(key)'));assert(navigationLine,'generated canonical navigation bridge exists');
 vm.runInContext(navigationLine,context);
 context.window.location.href='http://router/#events/traffic';context.window.location.hash='#events/traffic';
 context.showPage('events/traffic');assert.equal(leaveRequests,1);assert.equal(context.minimumCurrentRoute.hash,'settings');assert.equal(new URL(context.window.location.href).hash,'#settings');assert.equal(viewportResets,0);
 context.showPage('settings');assert.equal(leaveRequests,1,'polling same route does not re-open dirty modal');
 dirty=false;pendingLeave();assert.equal(context.minimumCurrentRoute.hash,'events/traffic');assert.equal(context.minimumNav.lastExpanded,'events/traffic');assert.equal(attrs['data-hv-active'],'events');
 context.showPage('home');assert.equal(context.minimumCurrentRoute.hash,'home');assert.equal(context.minimumAdvancedRoute(context.minimumNav).hash,'events/traffic');
}
console.log('PASS: five-section routing, legacy subviews, unknown refusal, session return, language deep links and unconditional display access without command authority.');
