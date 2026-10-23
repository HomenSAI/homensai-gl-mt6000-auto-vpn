const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.listeners={};this.value=attrs.value||'';this.checked=false;this.disabled=false;this.textContent='';this.classList={add(){},remove(){}};(Array.isArray(children)?children:[children]).forEach(c=>this.appendChild(c));}
  appendChild(child){if(child!=null){if(child instanceof Node){if(child.parentNode)child.parentNode.removeChild(child);child.parentNode=this;}this.children.push(child);}return child;}
  removeChild(child){this.children.splice(this.children.indexOf(child),1);if(child instanceof Node)child.parentNode=null;return child;}
  get firstChild(){return this.children[0]||null;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,f){(this.listeners[k]||(this.listeners[k]=[])).push(f);}
  fire(k){if(this.attrs[k])this.attrs[k]({currentTarget:this,target:this});(this.listeners[k]||[]).slice().forEach(f=>f({currentTarget:this,target:this}));}
}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const text=n=>n instanceof Node?[n.textContent,...n.children.map(text)].join(' '):String(n);
const clean=v=>JSON.parse(JSON.stringify(v));
const app=JSON.parse(fs.readFileSync('VERSION.json','utf8')).application;
function fixture({language='en',design,inventory,store={},status,showIntro=false}={}){
  let modal=null,reloads=0,response={saved:true,onboarding_complete:true,onboarding_version:1},pending=null,fail=false,stopPending=null,stopFail=false,stopResponse={queued:true,accepted:true};
  const calls=[],notes=[],writes=[];
  const storage={getItem:k=>Object.hasOwn(store,k)?store[k]:null,setItem:(k,v)=>{store[k]=String(v);writes.push([k,v]);}};
  const c={console,URL,requestedLanguage:null,locale:language,bi:(en,ru)=>c.locale==='ru'?ru:en,E:(...a)=>new Node(...a),L:{resource:p=>'/resources/'+p},
    document:{documentElement:new Node('html')},window:{localStorage:storage,location:{href:'http://router/cgi-bin/luci/admin/services/homensai-vpn',reload:()=>reloads++},history:{replaceState(){}},HomenS:{brandUi:{renderFooter:n=>n.appendChild(new Node('p',{},'Developer · Serhii Khomenko'))}}},
    ui:{showModal:(_,nodes)=>modal=new Node('modal',{},nodes),hideModal:()=>modal=null,addNotification:(_,n)=>notes.push(n)},
    helpLink:(_,label)=>new Node('a',{},label),helpCommand:label=>new Node('pre',{},label),richText:s=>s,errorCodeLink:code=>new Node('span',{},code),
    rpc:{declare:spec=>(...args)=>{calls.push({spec:clean(spec),args:clean(args)});if(spec.method==='native_stop'){if(stopFail)return Promise.reject(new Error('never-display-stop-secret'));if(stopPending)return new Promise(resolve=>stopPending.resolve=resolve);return Promise.resolve(stopResponse);}if(fail)return Promise.reject(new Error('never-display-transport-secret'));if(pending)return new Promise(resolve=>pending.resolve=resolve);return Promise.resolve(response);}}
  };
  vm.createContext(c);
  for(const file of ['fool_guard','auto_panel','setup_wizard','theme_panel','design_panel','router_link','identity_panel','attribution_panel','onboarding_panel']){
    vm.runInContext(fs.readFileSync('router/'+file+'.inc.js','utf8').replace('__UI_BUILD__',app.ui_module).replace('__UI_AGENT__',app.version),c,{filename:file});
  }
  if(design!==undefined)store['homensai-vpn-design']=design;
  inventory=inventory||baseInventory();c.onboardingDisplayDefaults(inventory);
  let root=c.renderOnboardingGate(inventory,status||{version:app.version,package_version:app.version+'-1'});
  if(!showIntro){const intro=walk(root).find(n=>n.attrs['data-onboarding-action']==='intro-ok');if(intro)intro.attrs.click();}
  const active=()=>modal||root;
  const field=k=>{const n=walk(active()).find(n=>n.attrs['data-onboarding-field']===k);assert(n,'field '+k);return n;};
  const button=k=>{const n=walk(active()).find(n=>n.attrs['data-onboarding-action']===k);assert(n,'button '+k);return n;};
  const step=()=>walk(active()).find(n=>n.attrs['data-hv-onboarding']==='1').attrs['data-step'];
  const set=(key,value)=>{const n=field(key);if(n.attrs.type==='checkbox')n.checked=value;else n.value=String(value);n.fire(n.tag==='select'||n.attrs.type==='checkbox'?'change':'input');};
  const click=k=>{const n=button(k);return n.attrs.click({currentTarget:n,target:n});};
  return {c,inventory,calls,notes,writes,store,field,button,set,click,step,get root(){return active();},get reloads(){return reloads;},get modal(){return modal;},set response(v){response=v;},set fail(v){fail=v;},set pending(v){pending=v;},get pending(){return pending;},set stopPending(v){stopPending=v;},get stopPending(){return stopPending;},set stopFail(v){stopFail=v;},set stopResponse(v){stopResponse=v;},open(){c.openOnboardingSettings(inventory,{version:app.version});}};
}
function baseInventory(count=2){return {settings:{terms_version:'1',plan_source:count?'p0':'',plan_target:count>1?'p1':'',interval:30,checkpoint:900,probe_limit:16,native_duration:10,telegram_configured:false,appearance_language:'',appearance_theme:'',appearance_design:''},profiles:Array.from({length:count},(_,i)=>({id:'p'+i,name:'Server '+i,protocol:i?'wireguard':'openvpn'})),servers:[]};}
function advance(f,target='review'){
  while(f.step()!==target){assert(!f.button('next').disabled,'unexpected validation at '+f.step());f.click('next');}
}
(async()=>{
  for(const language of ['en','ru']){const intro=fixture({language,showIntro:true});assert.equal(intro.step(),'intro');const section=walk(intro.root).find(n=>n.attrs['data-onboarding-intro']==='1');assert.equal(walk(section).filter(n=>n.tag==='p').length,2);assert.equal(walk(section).filter(n=>n.attrs['data-intro-mode']).length,3);assert.equal(walk(section).filter(n=>n.attrs.role==='img').length,3);assert(!walk(intro.root).some(n=>n.attrs['data-onboarding-action']==='open-dashboard'));assert.equal(intro.calls.length,0);intro.click('intro-ok');assert.equal(intro.step(),'appearance');assert.equal(intro.calls.length,0);assert.equal(intro.writes.length,0);assert.equal(intro.reloads,0);}

  // Hardware selection survives save/reload and never allows a different detected model.
  for(const detected of ['mt6000','mt3000','unknown']){
    const inventory=baseInventory();inventory.settings.detected_router_model=detected;
    let device=fixture({inventory});assert.equal(device.field('appearance.router_model').value,'auto');
    device.set('appearance.router_model',detected==='mt6000'?'mt3000':'mt6000');
    assert(device.button('next').disabled);device.click('next');assert.equal(device.step(),'appearance');assert.equal(device.calls.length,0);
    device.set('appearance.router_model','auto');assert(!device.button('next').disabled);
    if(detected!=='unknown'){
      device.set('appearance.router_model',detected);assert(!device.button('next').disabled);advance(device);await device.click('save');
      assert.equal(device.calls[0].args[5].router_model,detected);
      inventory.settings.router_model=detected;device=fixture({inventory});assert.equal(device.field('appearance.router_model').value,detected);
      assert(device.c.renderAttribution({}).children.some(n=>text(n).includes(detected==='mt3000'?'Beryl AX':'Flint 2')));
      assert(!text(device.c.renderAttribution({})).includes(detected==='mt3000'?'Flint 2':'Beryl AX'));
    }
  }
  // Completion is a typed router marker, never the old profile flag or local browser persistence.
  let f=fixture();
  for(const settings of [{setup_complete:true},{onboarding_complete:true},{onboarding_complete:1,onboarding_version:1},{onboarding_complete:true,onboarding_version:'1'},{onboarding_complete:true,onboarding_version:2}])assert.equal(f.c.onboardingComplete({settings}),false);
  assert.equal(f.c.onboardingComplete({settings:{onboarding_complete:true,onboarding_version:1}}),true);
  assert.equal(f.c.onboardingComplete({error:'RPC',settings:{onboarding_complete:true,onboarding_version:1}}),false);
  assert.equal(f.calls.length,0,'render must not add a status/readiness RPC');
  assert.equal(f.step(),'appearance');assert.equal(f.field('appearance.language').value,'en');
  assert.equal(f.c.currentDesign(),'b');assert.equal(f.field('appearance.design').value,'b','fresh wizard starts Calm without persisting a browser override');assert.equal(f.writes.length,0);
  assert(!walk(f.root).some(n=>n.attrs['data-onboarding-action']==='emergency-stop'));assert(f.button('open-dashboard').attrs.class.includes('hv-onboarding-recovery-link'));
  f.set('appearance.theme','dark');f.set('appearance.language','ru');assert.equal(f.c.locale,'ru');assert(text(f.root).includes('Язык и оформление'));assert(text(f.root).includes('Далее'));assert.equal(new URL(f.button('open-dashboard').attrs.href).searchParams.get('lang'),'ru');assert(text(f.root).includes('Открыть панель и средства восстановления'));assert(!text(f.root).includes('Language and appearance'));assert.equal(f.field('appearance.theme').value,'dark');assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);assert.equal(f.reloads,0);
  const skip=walk(f.root).find(n=>n.attrs['data-onboarding-skip']==='1'),nav=f.button('next').parentNode;assert.equal(skip.parentNode,nav.parentNode);assert(skip.parentNode.children.indexOf(skip)>skip.parentNode.children.indexOf(nav),'skip is below Cancel/Next');assert(text(skip).includes('ничего не сбрасывает'));const guideUrl=new URL(f.button('setup-help').attrs.href);assert.equal(guideUrl.hash,'#help');assert.equal(guideUrl.searchParams.get('setup_help'),'1');assert.equal(guideUrl.searchParams.get('onboarding'),'defer');assert.equal(f.button('setup-help').attrs.target,'_blank');
  f.set('appearance.language','en');assert(text(f.root).includes('Language and appearance'));assert(text(f.root).includes('Next'));assert(!text(f.root).includes('Язык и оформление'));
  f.set('appearance.theme','dark');f.click('next');assert.equal(f.step(),'monitor');assert.equal(f.writes.length,0,'draft does not change browser preferences');
  f.set('monitor.interval','9');assert(f.button('next').disabled);f.click('next');assert.equal(f.step(),'monitor');
  assert.equal(f.field('monitor.interval').value,'9','never silently coerce input');
  f.set('monitor.interval','30');f.set('monitor.probe_limit','33');assert(f.button('next').disabled);f.set('monitor.probe_limit','32');assert(!f.button('next').disabled);
  f.click('back');assert.equal(f.field('appearance.theme').value,'dark');f.click('cancel');assert.equal(f.step(),'paused');assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);
  f.click('resume');assert.equal(f.field('appearance.theme').value,'dark');advance(f,'system');
  f.set('system.target','p0');assert(f.button('next').disabled);f.set('system.target','p1');f.click('next');
  f.set('servers.0.name','Name\u202e');assert(f.button('next').disabled,'bidi labels match backend prohibition');
  f.set('servers.0.name','😀'.repeat(64));assert(!f.button('next').disabled,'64 Unicode code points are valid even when 128 UTF-16 units');assert.equal(f.field('servers.0.name').attrs['aria-invalid'],'false');assert.equal(f.field('servers.0.name').attrs.maxlength,'128');
  f.set('servers.0.name','😀'.repeat(65));assert(f.button('next').disabled,'65 code points exceed backend limit');f.set('servers.0.name','Edited primary');
  f.set('servers.1.enabled',false);assert(f.button('next').disabled,'disabled selected reserve cannot advance');f.set('servers.1.enabled',true);
  advance(f,'speed');f.set('speed.budget_mib','32');f.set('speed.daily_mib','1');assert(f.button('next').disabled);f.set('speed.daily_mib','128');advance(f);
  const review=text(f.root);for(const phrase of ['Edited primary','Europe/Berlin','Failures before switching','Traffic per test, MiB','Keep all existing settings and token'])assert(review.includes(phrase),phrase);
  assert.equal(f.calls.length,0,'final review is read only');
  // Refusals, malformed success and lost acknowledgement keep the reviewed draft, without secret echo.
  for(const result of [null,{saved:true},{saved:true,onboarding_complete:true,onboarding_version:'1'},{saved:false,code:'CONFIG-RECOVERY-BUSY'},{saved:false,code:'secret token not-safe'}]){
    f.response=result;await f.click('save');assert.equal(f.reloads,0);assert.equal(f.step(),'review');assert(!f.button('save').disabled);assert(!text(f.root).includes('secret token not-safe'));
  }
  f.fail=true;await f.click('save');assert(!text(f.root).includes('never-display-transport-secret'));assert.equal(f.reloads,0);f.fail=false;
  // Pending commit is exactly one writer even if old buttons are invoked, Back/Cancel are clicked, or Settings is reopened.
  f.pending={};const before=f.calls.length,p=f.click('save');assert(f.button('save').disabled);await f.click('save');await f.click('cancel');await f.click('back');f.open();assert.equal(f.step(),'review');assert.equal(f.calls.length,before+1);
  f.pending.resolve({saved:true,onboarding_complete:true,onboarding_version:1});await p;assert.equal(f.reloads,1);assert.equal(f.c.ONBOARDING_SESSION,null);
  const commit=f.calls.at(-1);assert.equal(commit.spec.method,'setup_onboarding');assert.deepEqual(commit.spec.params,['system','monitor','recovery','speed','telegram','appearance']);
  const [system,monitor,recovery,speed,telegram,appearance]=commit.args;
  assert.deepEqual(Object.keys(system).sort(),['defer_pair','duration','servers','session_loss','source','target']);assert.equal(system.servers[0].name,'Edited primary');assert.equal(monitor.probe_limit,32);assert.equal(monitor.interval,30);assert.equal(recovery.cooldown,180);assert.equal(speed.budget_mib,32);assert.deepEqual(telegram,{configure:false});assert.equal(appearance.theme,'dark');
  assert(f.calls.every(call=>call.spec.method==='setup_onboarding'),'never accepts terms, toggles a service or starts Auto');
  // Zero/one-profile installations require a deliberate defer; outgoing pair is empty, planning off, metadata retained.
  for(const count of [0,1]){
    const inv=baseInventory(count);inv.settings.plan_enabled=true;f=fixture({inventory:inv});advance(f,'system');assert(f.button('next').disabled);assert(walk(f.root).some(n=>n.attrs['data-onboarding-link']==='router-vpn'&&n.attrs.rel==='noopener noreferrer'));
    f.set('system.defer_pair',true);assert(!f.button('next').disabled);advance(f);await f.click('save');const args=f.calls[0].args;assert.equal(args[0].defer_pair,true);assert.equal(args[0].source,'');assert.equal(args[0].target,'');assert.equal(args[0].servers.length,count);assert.equal(args[1].planning_enabled,false);assert.equal(f.reloads,1);
  }
  // Optional Telegram: configure=false sends only KEEP, while enabled reporting requires a valid chat + token.
  f=fixture();advance(f,'telegram');f.set('telegram.configure',true);assert(!f.button('next').disabled,'disabled empty optional reports allowed');
  f.set('telegram.enabled',true);assert(f.button('next').disabled);f.set('telegram.chat','@owner_channel');assert(f.button('next').disabled);
  const token='123456789:'+('A'.repeat(35));f.set('telegram.token',token);assert(!f.button('next').disabled);f.set('telegram.items.servers',false);f.click('next');assert(!text(f.root).includes(token));assert(!walk(f.root).some(n=>n.attrs.type==='password'),'review must not contain a password field');
  f.response={saved:false,code:'TELEGRAM-TOKEN-REQUIRED'};await f.click('save');assert.equal(f.step(),'review');assert(!text(f.root).includes(token));f.click('back');assert.equal(f.field('telegram.token').value,token,'unconfirmed save retains draft');
  f.set('telegram.configure',false);f.click('next');f.response={saved:true,onboarding_complete:true,onboarding_version:1};await f.click('save');assert.deepEqual(f.calls.at(-1).args[4],{configure:false});assert(!f.writes.some(row=>String(row).includes(token)),'never persists token in browser');
  const stored=baseInventory();stored.settings.telegram_configured=true;stored.settings.telegram_destination='@stored_channel';stored.settings.telegram_enabled=true;f=fixture({inventory:stored});advance(f,'telegram');f.set('telegram.configure',true);assert.equal(f.field('telegram.token').value,'');assert(!f.button('next').disabled,'blank token retains valid stored token');advance(f);assert(text(f.root).includes('Stored token retained (hidden)'));
  // Change every section through its real controls, then verify the complete transaction independently.
  f=fixture();f.set('appearance.language','ru');f.set('appearance.theme','light');f.set('appearance.design','b');f.click('next');
  f.set('monitor.interval',45);f.set('monitor.checkpoint',1200);f.set('monitor.probe_limit',24);f.set('monitor.planning_enabled',true);f.click('next');
  f.set('system.source','p1');f.set('system.target','p0');f.set('system.duration',20);f.set('system.session_loss',true);f.click('next');
  f.set('servers.0.name','Main display');f.set('servers.0.channel','Group A');f.set('servers.0.priority',12);f.set('servers.1.name','Reserve display');f.set('servers.1.channel','Group B');f.set('servers.1.priority',34);f.click('next');
  const customRecovery={failures:5,successes:4,cooldown:360,min_dwell:240,primary_successes:5,primary_stable:120,return_policy:'hold_reserve'};
  for(const [key,value] of Object.entries(customRecovery))f.set('recovery.'+key,value);f.click('next');
  const customSpeed={enabled:true,auto_new:true,budget_mib:16,duration:10,streams:3,daily_mib:256,busy_mbps:10};
  for(const [key,value] of Object.entries(customSpeed))f.set('speed.'+key,value);f.click('next');
  f.set('telegram.configure',true);f.set('telegram.enabled',true);f.set('telegram.token',token);f.set('telegram.chat','-1001234567890');f.set('telegram.interval',120);f.set('telegram.schedule','daily');f.set('telegram.hour',22);f.set('telegram.weekly',false);f.set('telegram.monthly',false);f.set('telegram.items.gaps',false);f.click('next');
  assert.equal(f.calls.length,0);assert(!text(f.root).includes(token));await f.click('save');assert.equal(f.reloads,1);
  const full=f.calls[0].args;
  assert.deepEqual(full[0],{defer_pair:false,source:'p1',target:'p0',duration:20,session_loss:true,servers:[{profile:'p0',name:'Main display',channel:'Group A',priority:12,enabled:true},{profile:'p1',name:'Reserve display',channel:'Group B',priority:34,enabled:true}]});
  assert.deepEqual(full[1],{interval:45,checkpoint:1200,probe_limit:24,planning_enabled:true});assert.deepEqual(full[2],customRecovery);assert.deepEqual(full[3],customSpeed);
  assert.deepEqual(full[4],{configure:true,token,chat:'-1001234567890',enabled:true,interval:120,schedule:'daily',hour:22,weekly:false,monthly:false,items:'servers,events,traffic,delta,controller,controller_events,controller_totals'});
  assert.deepEqual(full[5],{language:'ru',theme:'light',design:'b',router_model:'auto'});assert.equal(f.store['homensai-vpn-language'],'ru');assert.equal(f.store['homensai-vpn-theme'],'light');assert.equal(f.store['homensai-vpn-design'],'b');
  // Router defaults survive an empty browser, browser overrides win, and Settings reopens the same values/draft.
  const saved=baseInventory();Object.assign(saved.settings,{onboarding_complete:true,onboarding_version:1,appearance_language:'ru',appearance_design:'c',appearance_theme:'dark',probe_limit:32,recovery_cooldown:420});
  f=fixture({inventory:saved});assert.equal(f.c.locale,'ru');assert.equal(f.c.currentDesign(),'c');assert.equal(f.c.storedTheme(),'dark');assert.equal(f.c.onboardingComplete(saved),true);f.open();assert.equal(f.field('appearance.language').value,'ru');advance(f,'monitor');assert.equal(f.field('monitor.probe_limit').value,'32');f.set('monitor.checkpoint','1200');f.click('cancel');assert.equal(f.modal,null);f.open();assert.equal(f.field('monitor.checkpoint').value,'1200');advance(f,'recovery');assert.equal(f.field('recovery.cooldown').value,'420');
  f=fixture({inventory:saved,store:{'homensai-vpn-language':'en','homensai-vpn-theme':'system','homensai-vpn-design':'b'}});assert.equal(f.c.locale,'en');assert.equal(f.c.storedTheme(),'system');assert.equal(f.c.currentDesign(),'b');
  f.c.window.localStorage.getItem=()=>{throw Error('storage unavailable');};f.c.onboardingDisplayDefaults(saved);assert.equal(f.c.locale,'ru');assert.equal(f.c.storedTheme(),'dark');assert.equal(f.c.currentDesign(),'c','router defaults work when browser persistence is unavailable');
  f=fixture({inventory:saved});f.c.requestedLanguage='en';f.c.locale='en';f.c.onboardingDisplayDefaults(saved);assert.equal(f.c.locale,'en','explicit language URL wins over router default');
  // An accepted, configured legacy installation can still have Auto ON before the new marker exists.
  // Stop must be an explicit zero-argument RPC, usable with active/stale/unknown status and pending controls.
  for(const legacyStatus of [{native_failover:{state:'OBSERVING',certified:true},auto_control:{requested:'on'}},{rpc_error:'RPC-UNAVAILABLE'},{}]){
    const legacy=baseInventory();Object.assign(legacy.settings,{setup_complete:true,native_enabled:true});
    f=fixture({inventory:legacy,status:legacyStatus});assert(!f.c.onboardingComplete(legacy));assert.equal(f.calls.length,0,'render never automatically stops or starts Auto');
    assert(!walk(f.root).some(n=>n.attrs['data-onboarding-action']==='emergency-stop'),'appearance has no Stop');f.click('next');
    f.c.autoStartPending=true;f.c.autoRequestBusy=true;f.c.autoStopBusy=true;
    assert(!f.button('emergency-stop').disabled,'independent of status and other controls');
    f.stopPending={};let stopping=f.click('emergency-stop');assert.equal(f.calls.length,1);assert.equal(f.calls[0].spec.method,'native_stop');assert.deepEqual(f.calls[0].args,[]);assert(!f.calls[0].spec.params||f.calls[0].spec.params.length===0);
    await f.click('emergency-stop');assert.equal(f.calls.length,1,'only its own pending Stop is deduped');
    f.click('next');assert.equal(f.step(),'system');assert(f.button('emergency-stop').disabled,'recreated control shares its pending Stop');
    f.stopPending.resolve({queued:true,accepted:true});await stopping;assert(!f.button('emergency-stop').disabled,'current recreated control unlocks when request settles');
    f.stopPending=null;await f.click('emergency-stop');assert.equal(f.calls.length,2,'no Stop cooldown after settlement');assert.equal(f.reloads,0,'Stop preserves the wizard draft');
    f.stopResponse={queued:false,accepted:false};await f.click('emergency-stop');assert(!f.button('emergency-stop').disabled);assert(f.notes.some(n=>text(n).includes('AUTO-CONTROL-UNVERIFIED')));
    f.stopFail=true;await f.click('emergency-stop');assert(!f.button('emergency-stop').disabled);assert(f.notes.some(n=>text(n).includes('AUTO-CONTROL-FAILED')));assert(!f.notes.some(n=>text(n).includes('never-display-stop-secret')));
  }
  f=fixture();advance(f);f.pending={};let saving=f.click('save');assert(f.button('save').disabled);assert(!f.button('emergency-stop').disabled,'writer lock must never delay Stop dispatch');
  f.stopPending={};let stopping=f.click('emergency-stop');assert.deepEqual(f.calls.map(c=>c.spec.method),['setup_onboarding','native_stop']);
  await f.click('emergency-stop');await f.click('save');await f.click('back');assert.equal(f.calls.length,2);assert.equal(f.step(),'review');
  f.stopPending.resolve({queued:true,accepted:true});await stopping;assert(!f.button('emergency-stop').disabled);assert(f.button('save').disabled,'Stop settling does not falsely unlock pending configuration save');
  f.pending.resolve({saved:false,code:'CONFIG-STOP-AUTO-FIRST'});await saving;assert.equal(f.step(),'review');assert(!f.button('emergency-stop').disabled);assert(!f.button('save').disabled);assert.equal(f.reloads,0);
  f.click('cancel');assert.equal(f.step(),'paused');assert(!f.button('emergency-stop').disabled);f.stopPending=null;await f.click('emergency-stop');assert.equal(f.calls.at(-1).spec.method,'native_stop','paused wizard keeps emergency Stop');
  // Held reserve recovery needs the existing dashboard's explicit return control as well as Stop.
  for(const held of ['HELD-ON-RESERVE','STOPPED-ON-RESERVE']){
    f=fixture({status:{native_failover:{state:held},auto_control:{requested:'off'}}});
    const link=f.button('open-dashboard'),url=new URL(link.attrs.href);
    assert.equal(url.origin,new URL(f.c.window.location.href).origin);assert.equal(url.searchParams.get('onboarding'),'defer');assert.equal(url.hash,'#overview');assert.equal(link.attrs.target,'_blank');assert.equal(link.attrs.rel,'noopener noreferrer');assert.equal(f.calls.length,0,'rendering an escape never executes recovery or completion');
    f.click('cancel');assert.equal(f.step(),'paused');assert.equal(f.button('open-dashboard').attrs.href,link.attrs.href);assert.equal(f.c.onboardingComplete(f.inventory),false);
  }
  f=fixture();advance(f,'telegram');f.set('telegram.configure',true);f.set('telegram.token',token);f.set('telegram.chat','@owner_channel');f.click('next');f.pending={};saving=f.click('save');
  const escape=f.button('open-dashboard');assert(!escape.disabled,'pending save does not block dashboard escape');assert(!escape.attrs.href.includes(token));assert.equal(new URL(escape.attrs.href).searchParams.get('onboarding'),'defer');
  f.pending.resolve({saved:false,code:'CONFIG-RECOVERY-BUSY'});await saving;assert.equal(f.c.onboardingComplete(f.inventory),false);assert(!f.writes.some(row=>String(row).includes(token)));
  // Only the exact explicit query bypasses once; scrub preserves unrelated URL state and never writes settings/storage.
  f=fixture();const originalSettings=JSON.stringify(f.inventory.settings),history=[];
  f.c.window.history.replaceState=(_state,_title,url)=>{history.push(String(url));f.c.window.location.href=String(url);};
  for(const query of ['', 'onboarding=other','onboarding=DEFER','onboarding=defer-extra','onboarding=defer&onboarding=defer','onboarding=defer&onboarding=other']){
    f.c.window.location.href='http://router/cgi-bin/luci/admin/services/homensai-vpn?'+query+'#overview';assert.equal(f.c.onboardingEntryDeferred(),false,query);
  }
  assert.equal(history.length,0);f.c.window.location.href='http://router/cgi-bin/luci/admin/services/homensai-vpn?lang=ru&keep=example&onboarding=defer#overview';assert.equal(f.c.onboardingEntryDeferred(),true);assert.equal(history.length,1);
  const scrubbed=new URL(f.c.window.location.href);assert(!scrubbed.searchParams.has('onboarding'));assert.equal(scrubbed.searchParams.get('lang'),'ru');assert.equal(scrubbed.searchParams.get('keep'),'example');assert.equal(scrubbed.hash,'#overview');assert.equal(f.c.onboardingEntryDeferred(),false,'consumed entry cannot bypass a second render');
  assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);assert.equal(JSON.stringify(f.inventory.settings),originalSettings);assert.equal(f.c.onboardingComplete(f.inventory),false);
  const fresh=fixture();fresh.c.window.location.href=f.c.window.location.href;assert.equal(fresh.c.onboardingEntryDeferred(),false,'a normal reload of the scrubbed URL offers setup again');
  const blockedHistory=fixture();blockedHistory.c.window.location.href='http://router/?onboarding=defer';blockedHistory.c.window.history.replaceState=()=>{throw Error('history unavailable');};assert.equal(blockedHistory.c.onboardingEntryDeferred(),false,'cannot promise one-entry escape when URL cleanup fails');
  // Every step/pause in every design and locale retains complete owner identity; full-page styles load once.
  for(const language of ['en','ru'])for(const design of ['a','b','c']){
    f=fixture({language,design});assert.equal(walk(f.root).filter(n=>n.tag==='link').length,4);
    while(true){const identity=walk(f.root).find(n=>n.attrs['data-hv-attribution']==='1');assert(identity);assert.equal(walk(f.root).some(n=>n.attrs['data-onboarding-action']==='emergency-stop'),f.step()!=='appearance','Stop removed only from appearance');assert(f.button('open-dashboard').attrs.href,'recovery escape available on '+f.step());const contents=text(f.root);for(const phrase of ['GL.iNet GL-MT6000','Serhii Khomenko','homensai.com','Style 1.14.3'].filter(p=>p!=='homensai.com'))assert(contents.includes(phrase));assert(walk(f.root).some(n=>n.attrs.class==='hv-version'));assert.equal(walk(f.root).find(n=>n.attrs['data-hv-onboarding']==='1').attrs['data-hv-design'],design);if(f.step()==='review')break;f.click('next');}
    if(language==='ru'){assert(text(f.root).includes('Пауза, секунд'));assert(!text(f.root).includes('budget_mib'));assert(!text(f.root).includes('primary_successes'));}
    f.click('cancel');assert.equal(f.step(),'paused');assert(!f.button('emergency-stop').disabled);assert(walk(f.root).some(n=>n.attrs['data-hv-attribution']==='1'));assert.equal(f.calls.length,0);
  }
  const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');
  assert(builder.includes("onboarding_panel.inc.js"));assert(builder.includes("if(!inventory.error&&!onboardingComplete(inventory)&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);"));assert(builder.includes("openOnboardingSettings(inventory,lastGoodStatus||data[1]);"));assert(builder.includes("!onboardingComplete(inventory)?E('p',{'class':'alert-message warning','data-onboarding-incomplete':'1'}"));
  assert(builder.indexOf('return renderTermsGate(inventory,data[1]);')<builder.indexOf('return renderOnboardingGate(inventory,data[1]);'),'terms gate precedes complete setup');
  console.log('PASS: integrated eight-step onboarding, typed persistence and validation, safe drafts/Telegram, router appearance, EN/RU A/B/C identity, independent emergency Stop and one-entry same-origin dashboard recovery escape with URL cleanup, no completion/storage/RPC writes and held-reserve/pending-save coverage');
})().catch(error=>{console.error(error);process.exitCode=1;});
