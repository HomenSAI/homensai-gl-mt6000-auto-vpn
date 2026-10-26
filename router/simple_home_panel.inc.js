/* Display only. The existing Auto control remains the sole owner of commands. */
function simpleHomeShortcutReason(){return '';}
function simpleHomeAutoEnabled(status,now){
  status=status||{};var ns=status.native_failover||{},intent=status.auto_control||{};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90)||!manualFresh(ns.time,now,30))return false;
  if(intent.requested==='off')return false;
  if(intent.pair_phase)return intent.pair_phase==='RUNNING'&&intent.requested==='on';
  var control=autoControlModel(status,now);
  return control.fresh&&!control.awaiting&&(control.on||control.transitioning&&intent.requested==='on');
}
function renderSimpleHomeShortcut(getModel,goHome){
  var button=E('button',{'type':'button','class':'cbi-button hv-simple-shortcut-button','data-simple-shortcut':'1','aria-label':bi('Return to minimum','Вернуться к минимуму'),'click':function(){goHome();}},bi('← To minimum','← К минимуму'));
  var host=E('div',{'class':'hv-simple-shortcut-group','data-simple-home-available':'true'},button);
  host.update=function(){button.disabled=false;button.setAttribute('aria-disabled','false');};host.update();return host;
}
function simpleHomeHealth(profile,now,unavailable){
  if(unavailable||!profile)return {state:'unknown',label:bi('No fresh data','Нет свежих данных')};
  var health=profileHealth(profile,now);
  return {state:health.state,label:health.state==='healthy'?bi('Available','Доступен'):health.state==='failed'?bi('Unavailable','Недоступен'):health.state==='inactive'?bi('Tunnel is off','Туннель отключён'):bi('No fresh data','Нет свежих данных')};
}
function simpleHomeModel(status,inventory,now){
  status=status||{};inventory=inventory||{};
  var ns=status.native_failover||{},control=autoControlModel(status,now);
  var source=vendorDisplayMember(status,inventory,'source',now,ns.source),target=vendorDisplayMember(status,inventory,'target',now,ns.target);
  var path=manualConfirmedPath(status,source,target,now);
  var unavailable=!!status.error||!!status.rpc_error||!manualFresh(status.time,now,90)||!control.fresh;
  var decision=simpleHomeEntry({statusFresh:!status.error&&!status.rpc_error&&manualFresh(status.time,now,90),controllerFresh:control.fresh,autoRunning:simpleHomeAutoEnabled(status,now)});
  var operation=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null;
  var sourceHealth=simpleHomeHealth(source,now,unavailable),targetHealth=simpleHomeHealth(target,now,unavailable);
  var selected=unavailable?null:path.selected,activeHealth=selected==='source'?sourceHealth:selected==='target'?targetHealth:null;
  decision.source=source;decision.target=target;decision.selectedRole=selected;
  decision.sourceHealth=sourceHealth;decision.targetHealth=targetHealth;
  decision.activeHealthy=!!activeHealth&&activeHealth.state==='healthy';
  decision.moving=!unavailable&&(!!path.moving||control.transitioning);
  decision.dataUnavailable=unavailable;decision.control=control;decision.operation=operation;
  decision.enabled=simpleHomeAutoEnabled(status,now);decision.actionStop=control.stop||operation==='starting'||!control.fresh;
  decision.setupRequired=!unavailable&&control.off&&!decision.moving&&!operation&&(!source||!target||!source.id||!target.id||source.id===target.id);
  if(unavailable){decision.state='unknown';decision.title=bi('No fresh data','Нет свежих данных');decision.summary=bi('Check the connection to the router.','Проверьте связь с роутером.');}
  else if(operation==='stopping'){decision.state='pending';decision.title=bi('Turning Auto off…','Выключение Auto…');decision.summary=bi('Waiting for controller confirmation.','Ожидается подтверждение контроллера.');}
  else if(operation==='starting'){decision.state='pending';decision.title=bi('Turning Auto on…','Включение Auto…');decision.summary=bi('Waiting for controller confirmation.','Ожидается подтверждение контроллера.');}
  else if(decision.moving){decision.state='pending';decision.title=bi('Switching channel','Переключение канала');decision.summary=bi('The active channel is being confirmed.','Рабочий канал уточняется.');}
  else if(control.on&&decision.activeHealthy){decision.state='on';decision.title=selected==='target'?bi('Reserve is working','Работает резерв'):bi('Auto works','Auto работает');decision.summary=selected==='target'?bi('Reserve channel is in use.','Задействован резервный канал.'):bi('Primary channel is in use.','Задействован основной канал.');}
  else if(control.on){decision.state=activeHealth&&['failed','inactive'].indexOf(activeHealth.state)>=0?'error':'unknown';decision.title=bi('Connection needs checking','Нужна проверка соединения');decision.summary=selected?bi('The selected channel has no fresh successful check.','У выбранного канала нет свежей успешной проверки.'):bi('The active channel is not confirmed.','Рабочий канал не подтверждён.');}
  else if(decision.setupRequired){decision.state='setup';decision.title=bi('Finish setup','Завершите настройку');decision.summary=bi('Choose a primary and a different reserve profile.','Выберите основной и другой, резервный профиль.');}
  else if(control.off){decision.state='off';decision.title=bi('Auto is off','Auto выключен');decision.summary=selected==='target'?bi('Automatic switching is stopped; reserve remains selected.','Автопереключение остановлено; выбран резерв.'):bi('Automatic switching is stopped.','Автоматическое переключение остановлено.');}
  else{decision.state='error';decision.title=bi('Auto needs attention','Нужна проверка Auto');decision.summary=bi('Open diagnostics to see the reason.','Причина доступна в диагностике.');}
  return decision;
}
function renderSimpleHome(status,inventory,model,controlCard,openMenu){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var original=controlCard&&controlCard.querySelector('.hv-auto-power');
  // Mount the original element and action label: pending Start remains cancellable,
  // and async completion updates the same controls without a second command path.
  var power=original||E('span',{'class':'hv-simple-control-unavailable'},bi('Auto control unavailable','Управление Auto недоступно'));
  if(original)original.setAttribute('data-simple-home-auto','1');
  var actionLabel=controlCard&&controlCard.querySelector('.hv-auto-action')||E('span',{'class':'hv-simple-action'},bi('Open diagnostics','Откройте диагностику'));
  if(actionLabel.classList&&actionLabel.classList.add)actionLabel.classList.add('hv-simple-action');
  function member(profile,role){
    var health=role==='source'?model.sourceHealth:model.targetHealth,selected=model.selectedRole===role;
    var latency=health.state==='healthy'&&profile&&Number.isFinite(profile.rtt_ms)&&profile.rtt_ms>=0?profile.rtt_ms.toFixed(0)+' '+bi('ms','мс'):bi('No fresh measurement','Нет свежего замера');
    var title=profile&&(profile.name||profile.router_name)||bi('Profile not confirmed','Профиль не подтверждён');
    return E('div',{'class':'hv-simple-channel hv-simple-channel-'+health.state,'data-simple-role':role},[
      E('div',{'class':'hv-simple-channel-top'},[E('strong',{},role==='source'?bi('Primary','Основной'):bi('Reserve','Резервный')),E('span',{},health.label)]),
      E('div',{'class':'hv-simple-profile'},title),E('div',{'class':'hv-simple-selection'},selected?bi('In use','Используется'):model.selectedRole?bi('Not in use','Не используется'):bi('Selection not confirmed','Выбор не подтверждён')),
      E('div',{'class':'hv-simple-server'},endpointText(profile,now)),E('div',{},profile&&['wireguard','openvpn'].indexOf(profile.protocol)>=0?protocolLabel(profile):bi('Protocol not confirmed','Протокол не подтверждён')),
      profile&&countryName(profile)?E('div',{},countryName(profile)):null,E('div',{'class':'hv-simple-latency'},bi('Delay: ','Задержка: ')+latency)
    ].filter(Boolean));
  }
  var monitor=model.dataUnavailable?bi('State unknown','Состояние неизвестно'):model.enabled?bi('Auto is on','Auto включён'):model.control&&model.control.off?bi('Auto is off','Auto выключен'):bi('Being confirmed','Уточняется');
  return E('section',{'class':'hv-simple-home','data-simple-home':model.state},[
    E('div',{'class':'hv-simple-card'},[
      E('div',{'class':'hv-simple-top'},[E('strong',{},'Auto VPN'),E('span',{'class':'hv-simple-monitor hv-simple-monitor-'+model.state},monitor)]),
      E('h2',{'class':'hv-simple-state','role':'status'},model.title),
      E('div',{'class':'hv-simple-power-unit'},[E('div',{'class':'hv-simple-power'},power),actionLabel]),
      E('p',{'class':'hv-simple-route'},model.summary),
      model.setupRequired?E('p',{'class':'hv-simple-setup-action'},E('a',{'class':'cbi-button hv-minimum-action','href':'#settings','data-simple-setup':'1'},bi('Configure pair','Настроить пару'))):null,
      E('div',{'class':'hv-simple-reserve'},[E('span',{},bi('Reserve channel','Резервный канал')),E('strong',{},model.targetHealth.label)]),
      E('details',{'class':'hv-simple-details','data-home-details':'channels'},[E('summary',{},bi('Connection details','Подробности соединения')),E('div',{'class':'hv-simple-pair'},[member(model.source,'source'),member(model.target,'target')]),E('p',{},bi('Checks originate from the router over IPv4.','Проверки выполняются с роутера по IPv4.'))]),
      E('button',{'type':'button','class':'cbi-button hv-simple-open-menu','data-simple-open-menu':'1','click':openMenu},bi('Advanced menu →','Расширенное меню →')),
      E('p',{'class':'hv-simple-menu-hint'},bi('Channels · diagnostics · events · settings','Каналы · диагностика · события · настройки'))
    ].filter(Boolean))
  ]);
}
