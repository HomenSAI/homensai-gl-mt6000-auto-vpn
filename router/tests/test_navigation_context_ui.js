const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={URL};vm.createContext(c);
for(const file of ['minimum_navigation','navigation_context'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
const cases={home:'home',overview:'home',channels:'channels',tests:'diagnostics',readiness:'diagnostics/readiness',services:'diagnostics/technical',statistics:'events/statistics',traffic:'events/traffic',events:'events',settings:'settings',start:'settings/setup',learn:'help/training',help:'help'};
for(const [page,expected] of Object.entries(cases))for(const from of ['ru','en'])for(const to of ['ru','en']){
 const href='http://router:8080/cgi-bin/luci/admin/services/homensai-vpn?lang='+from+'&keep=1#'+page;
 const url=new URL(c.languageNavigationUrl(href,to,page));
 assert.equal(url.searchParams.get('lang'),to);assert.equal(url.hash,'#'+expected);assert.equal(url.origin,'http://router:8080');assert.equal(url.searchParams.get('keep'),'1');
 assert.equal(url.searchParams.get('hv_view'),expected==='home'?'home':'full');
 const clear=new URL(c.clearLanguageViewUrl(url.href));assert(!clear.searchParams.has('hv_view'));assert.equal(clear.hash,url.hash);
}
for(const path of ['diagnostics/speed','diagnostics/recovery','events/traffic','help/topic/VPN-003','help/training']){
 const page=path.split('/')[0],href='http://router/?setup=telegram#'+path,url=new URL(c.languageNavigationUrl(href,'ru',page));
 assert.equal(url.hash,'#'+path);assert(!url.searchParams.has('setup'));
}
assert.equal(new URL(c.languageNavigationUrl('http://router/?setup=telegram#settings','ru','settings')).searchParams.get('setup'),'telegram');
assert.equal(c.languageViewContext('http://router/?hv_view=full&hv_view=home'),null);assert.equal(c.languageViewContext('not a URL'),null);
assert.equal(new URL(c.languageNavigationUrl('http://router/#home','unsupported','../../x')).hash,'#home');
console.log('PASS: RU/EN retains canonical page/subview and help deep links, consumes one-use context without losing query parameters, canonicalizes legacy routes and performs no commands.');

// The relocated actual language control still guards unsaved pair drafts before reload.
{
 const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
 const path=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
 const selected=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+path+'.js','utf8');
 const handler=selected.split('\n').find(line=>line.includes("language.addEventListener('change',function(){"));assert(handler);
 const body=handler.slice(handler.indexOf('function(){')+11,handler.lastIndexOf('});'));
 const hybrid=selected.includes('hv-hybrid-release');
 const legacyContext={URL};vm.createContext(legacyContext);vm.runInContext(fs.readFileSync('router/navigation_context.inc.js','utf8'),legacyContext);
 const change=new Function('language','locale','localStorage','window','minimumCurrentRoute','languageNavigationUrl','minimumSettingsRequestLeave','activeTab',body);
 for(const allowed of hybrid?[true]:[false,true]){
  const language={value:'ru'},saved=[],window={location:{href:'http://router/#diagnostics/speed',assign:url=>window.destination=url}};
  change(language,'en',{setItem:(...args)=>saved.push(args)},window,{hash:'diagnostics/speed'},hybrid?legacyContext.languageNavigationUrl:c.languageNavigationUrl,fn=>{if(allowed)fn();},'tests');
  if(!hybrid)assert.equal(language.value,'en','visible control resets until permitted reload');
  if(allowed){assert.equal(new URL(window.destination).hash,hybrid?'#tests':'#diagnostics/speed');assert.equal(new URL(window.destination).searchParams.get('lang'),'ru');assert.deepEqual(saved,[['homensai-vpn-language','ru']]);}
  else{assert.equal(window.destination,undefined);assert.equal(saved.length,0,'Stay neither reloads nor persists the unconfirmed language');}
 }
 console.log('PASS: relocated actual language handler preserves dirty-draft guard and current subview before reload');
}
