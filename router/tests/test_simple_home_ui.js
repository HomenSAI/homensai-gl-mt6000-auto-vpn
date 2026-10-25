const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(v=>v!=null);this.disabled=attrs.disabled!=null;this.textContent='';}setAttribute(k,v){this.attrs[k]=String(v);}all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}text(){return this.textContent+this.children.map(x=>x instanceof N?x.text():String(x)).join(' ');}}
for(const language of ['en','ru']){
 let now=1000,clicked=0,opened=0;const c={E:(...args)=>new N(...args),bi:(en,ru)=>language==='ru'?ru:en,Date,WeakMap,window:{},statusNow:()=>now,
  termsAccepted:i=>!i.error&&i.settings.terms_version==='1',onboardingComplete:i=>i.settings.onboarding_complete===true&&i.settings.onboarding_version===1,
  vendorDisplayMember:(s,i,role)=>s.profiles.find(p=>p.id===i.settings['plan_'+role]),countryName:()=>language==='ru'?'Германия':'Germany',protocolLabel:p=>p.protocol==='wireguard'?'WireGuard':'OpenVPN',endpointText:p=>p?'Server: '+p.host:'Server address: not observed'};vm.createContext(c);
 for(const file of ['ui_logic','auto_panel','manual_panel','simple_home_policy','simple_home_panel'])vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8'),c);
 c.statusNow=()=>now;
 const inventory={settings:{terms_version:'1',onboarding_complete:true,onboarding_version:1,setup_complete:true,native_session_loss:true,enabled:true,plan_source:'a',plan_target:'b'}};
 const base={time:1000,profiles:[{id:'a',protocol:'wireguard',host:'primary.example',time:1000,interface:'wgclient1',dns_ok:true,https_success:2,rtt_ms:420},{id:'b',protocol:'openvpn',host:'reserve.example',time:1000,interface:'ovpnclient1',dns_ok:true,https_success:2,rtt_ms:670}],native_failover:{time:1000,state:'OBSERVING',mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true,source:'a',target:'b',blockers:[]},auto_control:{requested:'on',pair_phase:'RUNNING',requested_at:900},channel_path:{time:1000,confirmed:true,source_profile_id:'a',target_profile_id:'b',active_profile_id:'a'}};
 const clone=x=>JSON.parse(JSON.stringify(x));
 let model=c.simpleHomeModel(base,inventory,now);assert(model.showCard);assert.equal(model.selectedRole,'source');
 const original={disabled:false,click(){clicked++;}},control={querySelector:()=>original};
 const card=c.renderSimpleHome(base,inventory,model,control,()=>opened++),nodes=card.all();
 assert.equal(nodes.filter(n=>n.attrs['data-simple-home-auto']).length,1);assert.equal(nodes.filter(n=>n.attrs['data-simple-role'])[0].attrs['data-simple-role'],'source');
 assert(nodes.findIndex(n=>n.attrs['data-simple-home-auto'])<nodes.findIndex(n=>n.attrs['data-simple-role']));assert(card.text().includes('primary.example'));assert(card.text().includes('420'));
 nodes.find(n=>n.attrs['data-simple-home-auto']).attrs.click();assert.equal(clicked,1);assert.equal(opened,1);
 // Freshness is revalidated at click time, not only during initial rendering.
 now=1200;nodes.find(n=>n.attrs['data-simple-home-auto']).attrs.click();assert.equal(clicked,1);assert.equal(opened,2);now=1000;
 for(const edit of [s=>s.rpc_error='RPC',s=>s.time=800,s=>s.native_failover.time=800,s=>s.auto_control.pair_phase='STOPPING',s=>s.auto_control.pair_phase='STARTING',s=>s.auto_control.requested='off']){const s=clone(base);edit(s);assert.equal(c.simpleHomeModel(s,inventory,now).showCard,false);}
 for(const edit of [s=>s.native_failover.source='old',s=>s.native_failover.readiness_verified=false,s=>s.native_failover.blockers=['UNVERIFIED'],s=>s.auto_control.requested_at=1001,s=>s.channel_path.confirmed=false,s=>s.channel_path.source_profile_id='old',s=>s.channel_path.time=800,s=>s.channel_path.transitioning=true,s=>s.profiles[0].code='VPN-001']){const s=clone(base);edit(s);assert.equal(c.simpleHomeModel(s,inventory,now).showCard,true,'Enabled Auto stays accessible through display/health changes');}
 for(const key of ['terms_version','onboarding_complete','setup_complete','native_session_loss','enabled']){const i=clone(inventory);i.settings[key]=false;assert.equal(c.simpleHomeModel(base,i,now).showCard,true,key);}
 const missing=clone(base);missing.profiles=[];const unknown=c.simpleHomeModel(missing,inventory,now);assert(unknown.showCard);const unknownCard=c.renderSimpleHome(missing,inventory,unknown,control,()=>{});assert(unknownCard.text().includes('уточняется')||unknownCard.text().includes('Confirming'));assert(!unknownCard.text().includes('Reserve is in use'));
 const reserve=clone(base);reserve.native_failover.state='COMMITTED';reserve.native_failover.readiness_verified=false;reserve.channel_path.active_profile_id='b';reserve.profiles[0].code='VPN-003';model=c.simpleHomeModel(reserve,inventory,now);assert(model.showCard,'Confirmed healthy reserve after prepared RUNNING does not require current primary health');assert.equal(model.selectedRole,'target');
 reserve.auto_control.pair_phase='HELD';assert.equal(c.simpleHomeModel(reserve,inventory,now).showCard,false);
 let shortcutState={showCard:false,reason:'SETUP-INCOMPLETE'},navigated=0;
 const shortcut=c.renderSimpleHomeShortcut(()=>shortcutState,()=>navigated++),shortcutButton=shortcut.all().find(n=>n.attrs['data-simple-shortcut']),shortcutReason=shortcut.all().find(n=>n.attrs.id==='hv-simple-shortcut-reason');
 assert(!shortcutButton.disabled,'Unavailable button must still support hover/focus/touch explanation');assert.equal(shortcutButton.attrs['aria-disabled'],'true');assert.equal(shortcutReason.attrs.role,'tooltip');assert(shortcutReason.textContent.length>10);assert(!shortcutReason.hidden);
 shortcutButton.attrs.click();assert.equal(navigated,0,'Off Auto cannot navigate');assert.equal(shortcut.attrs['data-tooltip-open'],'true');
 shortcutButton.attrs.keydown({key:'Escape'});assert.equal(shortcut.attrs['data-tooltip-dismissed'],'true');shortcut.attrs.mouseenter();assert.equal(shortcut.attrs['data-tooltip-dismissed'],'false');
 shortcutState={showCard:true};shortcut.update();assert(!shortcutButton.disabled);assert(shortcutReason.hidden);shortcutButton.attrs.click();assert.equal(navigated,1);
 shortcutState={showCard:false,reason:'CURRENT-STATUS-REQUIRED'};shortcutButton.attrs.click();assert.equal(navigated,1,'Recheck at click time even if the displayed button was enabled');assert.equal(shortcutButton.attrs['aria-disabled'],'true');assert(!shortcutButton.disabled);
 shortcutState={showCard:false,dataUnavailable:true};shortcut.update();assert(/not confirmed|не подтверждено/.test(shortcutReason.textContent));
}
console.log('PASS: real Auto/path/health models gate source and reserve, stale/mismatched/incomplete evidence, click-time guard, original-button forwarding, primary-first cards and real addresses, EN/RU.');
// Execute the actual generated entry block: ready default versus explicit deep links.
{
 const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
 const module=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
 const source=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+module+'.js','utf8');
 const begin=source.indexOf('    var homeLatest=data[1],homeMenuRequested=false;'),end=source.indexOf('    function showPage(key){',begin);assert(begin>0&&end>begin);
 const entry=new Function('setup','window','validTab','startLanding','simpleHomeModel','data','inventory','statusNow','tabs','showPage','var bi=function(en){return en;};'+source.slice(begin,end)+';return {active:activeTab,fullMenu:()=>homeMenuRequested,open:openHomeMenu,simple:goSimpleHome};');
 for(const [hash,ready,setup,expected] of [['',true,false,'home'],['#overview',true,false,'home'],['#home',true,false,'home'],['',false,false,'start'],['#home',false,false,'start'],['#tests',true,false,'tests'],['',true,true,'settings']]){
  const w={location:{hash}},tabs=[],opened=[];const result=entry(setup,w,k=>['overview','home','tests'].includes(k),()=> 'start',()=>({showCard:ready}),[{},{}],{},()=>1000,tabs,k=>opened.push(k));assert.equal(result.active,expected);
  if(expected==='tests')assert(result.fullMenu(),'A direct tests link stays in full management');
  result.open();assert(result.fullMenu());assert.equal(w.location.hash,'overview');assert.deepEqual(opened,['overview']);
  assert.equal(result.simple(),ready);assert.equal(w.location.hash,ready?'home':'overview');if(ready)assert(!result.fullMenu());
 }
 assert(source.indexOf('if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate')<source.indexOf('if(!inventory.error&&!onboardingComplete(inventory)'));
 assert(source.includes("if(activeTab==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)"),'Home must expire even while no new RPC frame arrives');
 assert(source.includes("E('div',{'class':'hv-heading-row'},[heading,(homeShortcut=renderSimpleHomeShortcut"),'Shortcut must sit beside the actual page title');
 assert(source.includes('if(homeShortcut)homeShortcut.update(homeModel);'));
 assert(source.includes('!simpleHomeAutoEnabled(data[1],statusNow(data[1]))&&!onboardingEntryDeferred()'),'Enabled Auto must bypass only the unfinished wizard display gate');
 const css=fs.readFileSync('router/design_layer.css','utf8');assert(css.includes('.hv-app .hv-skip:not(:focus)'));assert(css.includes('clip-path:inset(50%)'));assert(css.includes('.hv-workspace[data-hv-design] .hv-start-done{opacity:1}'));
 console.log('PASS: generated startup routing, explicit setup/tests links, full-menu request and stale-home watchdog.');
}
