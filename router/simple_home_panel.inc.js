/* Startup view consumes current router evidence; the existing Auto control owns RPC. */
function simpleHomeShortcutReason(model){
  if(model&&model.dataUnavailable)return bi('Wait for fresh router data before opening the simplified view','Дождитесь свежих данных роутера для перехода');
  var reasons={
    'TERMS-NOT-ACCEPTED':['Accept the current terms first','Сначала примите условия использования'],
    'SETUP-INCOMPLETE':['Complete the initial setup first','Сначала завершите первичную настройку'],
    'CURRENT-PAIR-TESTS-REQUIRED':['Complete the required checks for this VPN pair','Пройдите обязательные проверки этой пары VPN'],
    'CURRENT-STATUS-REQUIRED':['Wait for fresh router data','Дождитесь свежих данных роутера'],
    'AUTO-NOT-CONFIRMED-RUNNING':['Start Auto and wait for confirmation','Включите Auto и дождитесь подтверждения'],
    'ACTIVE-CHANNEL-NOT-CONFIRMED':['Wait for the active channel to be confirmed','Дождитесь подтверждения рабочего канала']
  },row=reasons[model&&model.reason]||['The simplified view is not ready yet','Упрощённый интерфейс пока не готов'];
  return bi(row[0],row[1]);
}
function renderSimpleHomeShortcut(getModel,goHome){
  var reason=E('small',{'id':'hv-simple-shortcut-reason','class':'hv-simple-shortcut-reason'});
  var button=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-simple-shortcut-button','data-simple-shortcut':'1','aria-describedby':'hv-simple-shortcut-reason','click':function(){
    var model=getModel();update(model);if(model.showCard===true)goHome();
  }},bi('Simplified interface','Упрощённый интерфейс'));
  var host=E('div',{'class':'hv-simple-shortcut-group'},[button,reason]);
  function update(model){
    model=model||getModel();var available=model.showCard===true;
    button.disabled=!available;button.setAttribute('aria-disabled',available?'false':'true');
    host.setAttribute('data-simple-home-available',available?'true':'false');
    reason.hidden=available;reason.textContent=available?'':simpleHomeShortcutReason(model);
  }
  host.update=update;update();return host;
}
function simpleHomeModel(status,inventory,now){
  status=status||{};inventory=inventory||{};
  var settings=inventory.settings||{},ns=status.native_failover||{},control=autoControlModel(status,now);
  var source=vendorDisplayMember(status,inventory,'source',now),target=vendorDisplayMember(status,inventory,'target',now);
  var bound=!!(source&&target&&source.id!==target.id&&ns.source===source.id&&ns.target===target.id);
  var path=manualConfirmedPath(status,source,target,now),route=status.channel_path;
  var routeBound=!!(route&&manualFresh(route.time,now,30)&&route.confirmed===true&&route.transitioning!==true&&source&&target&&route.source_profile_id===source.id&&route.target_profile_id===target.id&&route.active_profile_id===(path.selected==='source'?source.id:path.selected==='target'?target.id:null));
  var continuous=ns.mode==='continuous-pair'&&ns.proof_scope==='router-probed-ipv4';
  var prepared=(ns.certified===true||continuous&&(ns.readiness_verified===true||ns.state==='COMMITTED'&&routeBound&&(status.auto_control||{}).pair_phase==='RUNNING'))&&(!Array.isArray(ns.blockers)||ns.blockers.length===0);
  var active=path.selected==='source'?source:path.selected==='target'?target:null;
  var decision=simpleHomeEntry({termsAccepted:termsAccepted(inventory),onboardingComplete:onboardingComplete(inventory),setupComplete:settings.setup_complete===true&&settings.native_session_loss===true,pairValid:bound,pairDeferred:settings.onboarding_pair_deferred===true,
    testsPassed:prepared,testsMatchCurrentPair:bound,statusFresh:!inventory.error&&!status.error&&!status.rpc_error&&settings.enabled===true&&manualFresh(status.time,now,90),controllerFresh:control.fresh,
    autoRunning:control.on,commandPending:control.awaiting||!!autoCommandOperation(status,now),transitioning:control.transitioning||path.moving,activePathConfirmed:!!active&&profileHealth(active,now).state==='healthy'&&(route?routeBound:!!path.selected),selectedRole:path.selected});
  decision.source=source;decision.target=target;decision.selectedRole=path.selected;decision.dataUnavailable=!!inventory.error||!!status.error||!!status.rpc_error||!manualFresh(status.time,now,90)||!control.fresh;return decision;
}
function renderSimpleHome(status,inventory,model,controlCard,openMenu){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var original=controlCard&&controlCard.querySelector('.hv-auto-power');
  var power=E('button',{'type':'button','class':'hv-auto-power hv-auto-neutral hv-auto-lit-on','aria-label':bi('Stop auto mode','Выключить авторежим'),'aria-pressed':'true','disabled':!original||original.disabled?'':null,'data-simple-home-auto':'1','click':function(){
    var latest=simpleHomeModel(status,inventory,typeof statusNow==='function'?statusNow(status):Date.now()/1000);
    if(!latest.showCard||!original||original.disabled){openMenu();return;}
    power.disabled=true;original.click();openMenu();
  }},E('span',{'class':'hv-power-symbol','aria-hidden':'true'}));
  function member(profile,role){
    var selected=model.selectedRole===role,health=profileHealth(profile,now),raw=profile.rtt_ms;
    var latency=health.state==='healthy'&&Number.isFinite(raw)&&raw>=0?raw.toFixed(0)+' '+bi('ms','мс'):bi('No fresh measurement','Нет свежего замера');
    return E('div',{'class':'hv-simple-channel hv-manual-channel '+(selected?'hv-manual-green':'hv-manual-red'),'data-simple-role':role},[
      E('div',{'class':'hv-simple-channel-top'},[E('strong',{},(role==='source'?'M · ':'R · ')+(role==='source'?bi('Primary','Основной'):bi('Reserve','Резервный'))),E('span',{'class':'hv-simple-selection'},[E('span',{'class':'hv-server-lamp '+(selected?'hv-lamp-healthy':'hv-lamp-inactive'),'aria-hidden':'true'}),selected?bi('In use','Задействован'):bi('Not in use','Не задействован')])]),
      E('div',{'class':'hv-simple-server'},endpointText(profile,now)),E('div',{},[countryName(profile)||'',countryName(profile)?' · ':'',protocolLabel(profile)]),E('div',{'class':'hv-simple-latency'},bi('Delay: ','Задержка: ')+latency)
    ]);
  }
  return E('section',{'class':'hv-simple-home','data-simple-home':'ready'},[
    E('div',{'class':'hv-simple-card'},[
      E('div',{'class':'hv-simple-top'},[E('strong',{},'Auto VPN'),E('span',{'class':'hv-simple-monitor'},[E('span',{'class':'hv-server-lamp hv-lamp-healthy','aria-hidden':'true'}),bi('Monitoring is on','Мониторинг включён')])]),
      E('h2',{'class':'hv-simple-state'},bi('Auto works','Auto работает')),E('div',{'class':'hv-simple-power'},power),
      E('p',{'class':'hv-simple-route'},model.selectedRole==='source'?bi('Primary channel is in use','Задействован основной канал'):bi('Reserve is in use','Задействован резерв')),
      E('div',{'class':'hv-simple-pair'},[member(model.source,'source'),member(model.target,'target')]),
      E('button',{'type':'button','class':'cbi-button hv-simple-open-menu','data-simple-open-menu':'1','click':openMenu},bi('Open current menu','Открыть текущее меню'))
    ])
  ]);
}
