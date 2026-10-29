/* Display only. The existing Auto control remains the sole owner of commands. */
function simpleHomeShortcutReason(){return '';}
function simpleHomeAutoEnabled(status,now){
  status=status||{};var ns=status.native_failover||{},intent=status.auto_control||{};
  if(status.rpc_error||status.error||!observationFresh(status,now)||!manualFresh(ns.time,now,30))return false;
  if(intent.requested==='off')return false;
  var control=autoControlModel(status,now);
  if(intent.pair_phase)return ['RUNNING','HELD'].indexOf(intent.pair_phase)>=0&&intent.requested==='on'&&(control.on||control.transitioning||ns.state==='DEGRADED-ON-RESERVE');
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
  // A lost answer, stale router data and a stale controller are different facts; a named recovery stays visible.
  var lost=!!status.error||!!status.rpc_error,light=autoLightModel(status,inventory,now),unavailable=lost||!observationFresh(status,now)||!control.fresh&&light.key!=='problem';
  var decision=simpleHomeEntry({statusFresh:!status.error&&!status.rpc_error&&observationFresh(status,now),controllerFresh:control.fresh,autoRunning:simpleHomeAutoEnabled(status,now)});
  var operation=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null,manual=manualOperationModel(status,now);
  var sourceHealth=simpleHomeHealth(source,now,unavailable),targetHealth=simpleHomeHealth(target,now,unavailable);
  var selected=unavailable?null:path.selected,activeHealth=selected==='source'?sourceHealth:selected==='target'?targetHealth:null;
  decision.source=source;decision.target=target;decision.selectedRole=selected;
  decision.sourceHealth=sourceHealth;decision.targetHealth=targetHealth;
  decision.activeHealthy=!!activeHealth&&activeHealth.state==='healthy';
  decision.moving=!unavailable&&(!!path.moving||control.transitioning||manual.busy);
  decision.dataUnavailable=unavailable;decision.connectionLost=lost;decision.control=control;decision.operation=operation;
  decision.enabled=simpleHomeAutoEnabled(status,now);decision.actionStop=control.stop||operation==='starting'||operation==='unconfirmed'||!control.fresh;decision.light=light;decision.path=path;
  decision.blockers=control.fresh&&Array.isArray(ns.blockers)?ns.blockers.slice(0,4):[];
  if(path.code&&decision.blockers.indexOf(path.code)<0)decision.blockers.push(path.code);
  decision.setupRequired=!unavailable&&control.off&&!decision.moving&&!operation&&(!source||!target||!source.id||!target.id||source.id===target.id);
  if(control.paused){decision.state='pending';decision.title=bi('Auto paused for speed test','Auto на паузе для теста скорости');decision.summary=bi('Monitoring resumes first, then Auto. Your VPNs stay connected.','Сначала возобновится мониторинг, затем Auto. VPN остаются подключёнными.');}
  else if(unavailable&&(lost||!observationFresh(status,now))){decision.state='unknown';decision.title=bi('No fresh data','Нет свежих данных');decision.summary=lost?bi('Check the connection to the router.','Проверьте связь с роутером.'):bi('The router has not sent fresh measurements.','Роутер не присылает свежие измерения.');}
  else if(unavailable){decision.state='unknown';decision.title=light.title;decision.summary=light.hint;}
  else if(operation==='stopping'){decision.state='pending';decision.title=bi('Turning Auto off…','Выключение Auto…');decision.summary=bi('The router is carrying out the command, wait a few seconds.','Роутер выполняет команду, подождите несколько секунд.');}
  else if(operation==='starting'){decision.state='pending';decision.title=bi('Turning Auto on…','Включение Auto…');decision.summary=bi('The router is carrying out the command, wait a few seconds.','Роутер выполняет команду, подождите несколько секунд.');}
  else if(operation==='unconfirmed'||manual.uncertain){decision.state=light.key==='problem'?'error':'unknown';decision.title=light.title;decision.summary=light.hint;}
  else if(decision.moving){decision.state='pending';decision.title=manual.busy||light.key==='switching'?light.title:bi('Switching channel','Переключение канала');decision.summary=(manual.busy||light.key==='switching')&&light.hint?light.hint:bi('The active channel is being confirmed.','Рабочий канал уточняется.');}
  else if(light.key==='problem'){decision.state='error';decision.title=light.title;decision.summary=light.hint;}
  else if(light.key==='unknown'){decision.state='unknown';decision.title=light.title;decision.summary=light.hint;}
  else if(light.hold){decision.state='pending';decision.title=light.title;decision.summary=light.hint;}
  else if(control.on&&path.code){decision.state='unknown';decision.title=bi('The traffic channel is not verified','Канал трафика не подтверждён');decision.summary=bi('Waiting for verified router VPN rules.','Ждём подтверждения действующих правил VPN роутером.')+' ('+path.code+')';}
  else if(control.on&&decision.activeHealthy){decision.state='on';decision.title=selected==='target'?bi('Reserve is working','Работает резерв'):bi('Auto works','Auto работает');decision.summary=selected==='target'?bi('Reserve channel is in use.','Задействован резервный канал.'):bi('Primary channel is in use.','Задействован основной канал.');}
  else if(control.on){decision.state=activeHealth&&['failed','inactive'].indexOf(activeHealth.state)>=0?'error':'unknown';decision.title=bi('Internet through the VPN has not been checked recently','Давно не проверялось, есть ли интернет через VPN');decision.summary=bi('Press "Check connection".','Нажмите «Проверить соединение».');}
  else if(ns.state==='BLOCKED'){decision.state='error';decision.title=bi('Auto is blocked','Auto заблокирован');decision.summary=decision.blockers.length?autoBlockerText(decision.blockers[0]):bi('Open diagnostics for the current reason.','Откройте диагностику для уточнения причины.');}
  else if(decision.setupRequired){decision.state='setup';decision.title=bi('Finish setup','Завершите настройку');decision.summary=bi('Choose a primary and a different reserve profile.','Выберите основной и другой, резервный профиль.');}
  else if(control.off){decision.state='off';decision.title=bi('Auto is off','Auto выключен');decision.summary=selected==='target'?bi('Automatic switching is stopped; reserve remains selected.','Автопереключение остановлено; выбран резерв.'):bi('Automatic switching is stopped.','Автоматическое переключение остановлено.');}
  else{decision.state='error';decision.title=bi('Auto cannot run','Auto не может работать');decision.summary=bi('Press to see why.','Нажмите, чтобы узнать почему.');}
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
    var tone=manualChannelTone(profile,role,model.path||manualConfirmedPath(status,model.source,model.target,now),now,autoWorking(model.light||autoLightModel(status,inventory,now)),status);
    var latency=renderChannelPing(profile,status,now);
    var title=profile&&(profile.name||profile.router_name)||bi('No VPN selected','VPN не выбран');
    return E('div',{'class':'hv-simple-channel hv-simple-channel-'+health.state,'data-simple-role':role,'data-node-tone':tone.color},[
      E('div',{'class':'hv-simple-channel-top'},[E('strong',{},role==='source'?bi('Primary','Основной'):bi('Reserve','Резервный')),E('span',{},health.label)]),
      E('div',{'class':'hv-simple-profile'},title),E('div',{'class':'hv-simple-selection'},tone.text),
      E('div',{'class':'hv-simple-server'},endpointText(profile,now)),E('div',{},profile&&['wireguard','openvpn'].indexOf(profile.protocol)>=0?protocolLabel(profile):bi('Not reported by the router','Роутер не сообщил')),
      profile&&countryName(profile)?E('div',{},countryName(profile)):null,E('div',{'class':'hv-simple-latency'},latency)
    ].filter(Boolean));
  }
  var monitor=model.connectionLost?bi('No connection to the router','Нет связи с роутером'):model.dataUnavailable?bi('Data out of date','Данные устарели'):model.light&&model.light.hold?model.light.title:model.state==='error'?bi('Needs attention','Нужно внимание'):model.enabled?bi('Auto is on','Auto включён'):model.control&&model.control.off?bi('Auto is off','Auto выключен'):bi('Being confirmed','Уточняется');
  return E('section',{'class':'hv-simple-home','data-simple-home':model.state},[
    E('div',{'class':'hv-simple-card'},[
      E('div',{'class':'hv-simple-top'},[E('strong',{},'Auto VPN'),E('span',{'class':'hv-simple-monitor hv-simple-monitor-'+model.state},monitor)]),
      E('h2',{'class':'hv-simple-state','role':'status'},model.title),
      E('div',{'class':'hv-simple-power-unit'},[E('div',{'class':'hv-simple-power'},power),actionLabel]),
      E('p',{'class':'hv-simple-route'},model.summary),
      typeof renderAutoRemedy==='function'?E('div',{},(model.blockers||[]).map(renderAutoRemedy).filter(Boolean)):null,
      model.setupRequired?E('p',{'class':'hv-simple-setup-action'},E('a',{'class':'cbi-button hv-minimum-action','href':'#settings','data-simple-setup':'1'},bi('Configure pair','Настроить пару'))):null,
      E('div',{'class':'hv-simple-reserve'},[E('span',{},bi('Reserve channel','Резервный канал')),E('strong',{},model.targetHealth.label)]),
      E('div',{'class':'hv-simple-pair hv-simple-response','data-home-response':'both'},['source','target'].map(function(role){return E('div',{'class':'hv-simple-latency'},[E('strong',{},role==='source'?bi('Primary response','Отклик основного'):bi('Reserve response','Отклик резерва')),renderChannelPing(role==='source'?model.source:model.target,status,now)]);})),
      E('details',{'class':'hv-simple-details','data-home-details':'channels'},[E('summary',{},bi('Connection details','Подробности соединения')),E('div',{'class':'hv-simple-pair'},[member(model.source,'source'),member(model.target,'target')]),E('p',{},bi('Checks originate from the router over IPv4.','Проверки выполняются с роутера по IPv4.'))]),
      E('button',{'type':'button','class':'cbi-button hv-simple-open-menu','data-simple-open-menu':'1','click':openMenu},bi('Advanced menu →','Расширенное меню →')),
      E('p',{'class':'hv-simple-menu-hint'},bi('Overview · channels · checks · settings','Обзор · каналы · проверки · настройки'))
    ].filter(Boolean))
  ]);
}
