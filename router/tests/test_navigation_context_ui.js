const fs=require('fs'),vm=require('vm'),assert=require('assert'),navSource=fs.readFileSync('router/navigation_context.inc.js','utf8'),nav={URL};vm.createContext(nav);vm.runInContext(navSource,nav);
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8')),moduleName=menu['admin/services/homensai-vpn'].action.path.split('/').pop(),source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+moduleName+'.js','utf8');
const handlerLine=source.split('\n').find(l=>l.includes("language.addEventListener('change',function(){"));assert(handlerLine);const body=handlerLine.slice(handlerLine.indexOf('function(){')+'function(){'.length,handlerLine.lastIndexOf('});'));
const changeLanguage=new Function('language','localStorage','window','activeTab','languageNavigationUrl',body);
const begin=source.indexOf('    var homeLatest=data[1],homeMenuRequested=false;'),end=source.indexOf('    function showPage(key){',begin);assert(begin>0&&end>begin);
const init=new Function('setup','window','validTab','startLanding','simpleHomeModel','data','inventory','statusNow','tabs','showPage','var bi=function(en){return en;};'+navSource+source.slice(begin,end)+';return {active:activeTab,full:homeMenuRequested};');
const pages=['overview','start','channels','settings','help','events','tests','traffic','services','readiness','statistics','learn','home'];
function browser(href){const u=new URL(href),w={location:{href:u.href,hash:u.hash}};w.history={replaceState(a,b,url){const n=new URL(url);w.location.href=n.href;w.location.hash=n.hash;}};w.location.assign=url=>w.destination=url;return w;}
function boot(href,ready=true){const w=browser(href),result=init(new URL(href).searchParams.get('setup'),w,k=>pages.includes(k),()=> 'start',()=>({showCard:ready}),[{},{}],{},()=>1000,[],()=>{});return {w,result};}
for(const page of pages)for(const from of ['ru','en'])for(const to of ['ru','en']){
 const w=browser('http://router:8080/cgi-bin/luci/admin/services/homensai-vpn?lang='+from+'&keep=1#overview'),stored=[];
 changeLanguage({value:to},{setItem:(...a)=>stored.push(a)},w,page,nav.languageNavigationUrl);
 const dest=new URL(w.destination);assert.equal(dest.searchParams.get('lang'),to);assert.equal(dest.hash,'#'+page);assert.equal(dest.origin,'http://router:8080');assert.equal(dest.pathname,'/cgi-bin/luci/admin/services/homensai-vpn');assert.equal(dest.searchParams.get('keep'),'1');assert.deepEqual(stored,[['homensai-vpn-language',to]]);
 const next=boot(w.destination);assert.equal(next.result.active,page,'Language reload must keep '+page);assert.equal(next.result.full,page!=='home');assert(!new URL(next.w.location.href).searchParams.has('hv_view'),'One-reload marker must be consumed');
}
// Exact reported regression: running Auto defaults to Home, full Overview survives RU→EN→RU.
assert.equal(boot('http://router/#overview').result.active,'home');
let href='http://router/?lang=ru#overview';for(const lang of ['en','ru']){href=nav.languageNavigationUrl(href,lang,'overview');const next=boot(href);assert.equal(next.result.active,'overview');href=next.w.location.href;}
// Visible section may differ from an old hash; stale settings-entry params must not redirect it.
assert.equal(new URL(nav.languageNavigationUrl('http://router/?setup=telegram#overview','en','events')).searchParams.has('setup'),false);
assert.equal(new URL(nav.languageNavigationUrl('http://router/?setup=telegram#settings','ru','settings')).searchParams.get('setup'),'telegram');
assert.equal(nav.languageViewContext('http://router/?hv_view=full&hv_view=home'),null);assert.equal(nav.languageViewContext('not a URL'),null);
const gateLine=source.split('\n').find(l=>l.includes('return renderOnboardingGate(inventory,data[1])')),condition=/if\((.*)\)return renderOnboardingGate/.exec(gateLine)[1];
const wizard=new Function('inventory','data','onboardingComplete','simpleHomeAutoEnabled','statusNow','languageViewContext','window','onboardingEntryDeferred','return '+condition+';');
assert.equal(wizard({},[{},{}],()=>false,()=>false,()=>1000,nav.languageViewContext,browser(nav.languageNavigationUrl('http://router/#start','en','start')),()=>false),false,'Language change in full OFF/incomplete setup must not reopen the wizard');
assert.equal(wizard({},[{},{}],()=>false,()=>false,()=>1000,nav.languageViewContext,browser('http://router/#start'),()=>false),true,'An ordinary fresh unconfigured OFF entry still offers the wizard');
console.log('PASS: actual language handler and generated startup preserve RU/EN page+full/home mode, repeated switches, stale hashes/setup links, OFF incomplete setup and one-use context without config/Auto calls.');
