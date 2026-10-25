/* Startup view consumes current router evidence; the existing Auto control owns RPC. */
function simpleHomeShortcutReason(model){
  if(model&&model.dataUnavailable)return bi('Auto is not confirmed on. Check the router connection, configure the system and enable Auto to use the simplified interface.','Включение Auto не подтверждено. Проверьте связь с роутером, настройте систему и включите Auto, чтобы воспользоваться упрощённым интерфейсом.');
  return bi('Configure the system and enable Auto to use the simplified interface.','Чтобы воспользоваться упрощённым интерфейсом, необходимо настроить систему и включить Auto.');
}
function simpleHomeAutoEnabled(status,now){
  status=status||{};var ns=status.native_failover||{},intent=status.auto_control||{};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90)||!manualFresh(ns.time,now,30))return false;
  if(intent.requested==='off')return false;
  if(intent.pair_phase)return intent.pair_phase==='RUNNING'&&intent.requested==='on';
  var control=autoControlModel(status,now);
  return control.fresh&&!control.awaiting&&(control.on||control.transitioning&&intent.requested==='on');
}
function renderSimpleHomeShortcut(getModel,goHome){
  var reason=E('small',{'id':'hv-simple-shortcut-reason','class':'hv-simple-shortcut-reason','role':'tooltip'});
  var button=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-simple-shortcut-button','data-simple-shortcut':'1','aria-describedby':'hv-simple-shortcut-reason','focus':function(){host.setAttribute('data-tooltip-dismissed','false');},'blur':function(){host.setAttribute('data-tooltip-open','false');},'keydown':function(event){if(event.key==='Escape'){host.setAttribute('data-tooltip-open','false');host.setAttribute('data-tooltip-dismissed','true');}},'click':function(){
    var model=getModel();update(model);if(model.showCard===true)goHome();else{host.setAttribute('data-tooltip-dismissed','false');host.setAttribute('data-tooltip-open','true');}
  }},bi('Simplified interface','Упрощённый интерфейс'));
  var host=E('div',{'class':'hv-simple-shortcut-group','mouseenter':function(){host.setAttribute('data-tooltip-dismissed','false');},'mouseleave':function(){host.setAttribute('data-tooltip-open','false');}},[button,reason]);
  function update(model){
    model=model||getModel();var available=model.showCard===true;
    button.disabled=false;button.setAttribute('aria-disabled',available?'false':'true');
    host.setAttribute('data-simple-home-available',available?'true':'false');
    reason.hidden=available;reason.textContent=available?'':simpleHomeShortcutReason(model);
    if(available)host.setAttribute('data-tooltip-open','false');
  }
  host.update=update;update();return host;
}
function simpleHomeModel(status,inventory,now){
  status=status||{};inventory=inventory||{};
  var ns=status.native_failover||{},control=autoControlModel(status,now);
  var source=vendorDisplayMember(status,inventory,'source',now,ns.source),target=vendorDisplayMember(status,inventory,'target',now,ns.target);
  var path=manualConfirmedPath(status,source,target,now);
  var decision=simpleHomeEntry({statusFresh:!status.error&&!status.rpc_error&&manualFresh(status.time,now,90),controllerFresh:control.fresh,autoRunning:simpleHomeAutoEnabled(status,now)});
  var active=path.selected==='source'?source:path.selected==='target'?target:null;
  decision.source=source;decision.target=target;decision.selectedRole=path.selected;decision.activeHealthy=!!active&&profileHealth(active,now).state==='healthy';decision.moving=!!path.moving||control.transitioning;decision.dataUnavailable=!!status.error||!!status.rpc_error||!manualFresh(status.time,now,90)||!control.fresh;return decision;
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
    var selected=model.selectedRole===role,known=!!profile,health=known?profileHealth(profile,now):{state:'unknown'},raw=known&&profile.rtt_ms;
    var uncertain=!model.selectedRole,failed=health.state==='failed'||health.state==='inactive',color=uncertain?'hv-manual-yellow':selected&&!failed?'hv-manual-green':'hv-manual-red';
    var label=health.state==='inactive'?bi('Tunnel is off','Туннель отключён'):failed?bi('Connection failed','Ошибка соединения'):uncertain?(model.moving?bi('Switching','Переключение'):bi('Being confirmed','Уточняется')):selected?bi('In use','Задействован'):bi('Not in use','Не задействован');
    var latency=health.state==='healthy'&&Number.isFinite(raw)&&raw>=0?raw.toFixed(0)+' '+bi('ms','мс'):bi('No fresh measurement','Нет свежего замера');
    return E('div',{'class':'hv-simple-channel hv-manual-channel '+color,'data-simple-role':role},[
      E('div',{'class':'hv-simple-channel-top'},[E('strong',{},(role==='source'?'M · ':'R · ')+(role==='source'?bi('Primary','Основной'):bi('Reserve','Резервный'))),E('span',{'class':'hv-simple-selection'},[E('span',{'class':'hv-server-lamp '+(uncertain?'hv-lamp-checking':selected&&!failed?'hv-lamp-healthy':'hv-lamp-inactive'),'aria-hidden':'true'}),label])]),
      E('div',{'class':'hv-simple-server'},endpointText(profile,now)),E('div',{},[known?countryName(profile)||'':'',known&&countryName(profile)?' · ':'',known&&['wireguard','openvpn'].indexOf(profile.protocol)>=0?protocolLabel(profile):bi('Protocol not confirmed','Протокол не подтверждён')]),E('div',{'class':'hv-simple-latency'},bi('Delay: ','Задержка: ')+latency)
    ]);
  }
  return E('section',{'class':'hv-simple-home','data-simple-home':'ready'},[
    E('div',{'class':'hv-simple-card'},[
      E('div',{'class':'hv-simple-top'},[E('strong',{},'Auto VPN'),E('span',{'class':'hv-simple-monitor'},[E('span',{'class':'hv-server-lamp hv-lamp-healthy','aria-hidden':'true'}),bi('Monitoring is on','Мониторинг включён')])]),
      E('h2',{'class':'hv-simple-state'},model.activeHealthy&&!model.moving?bi('Auto works','Auto работает'):bi('Auto is on','Auto включён')),E('div',{'class':'hv-simple-power'},power),
      E('p',{'class':'hv-simple-route'},model.selectedRole==='source'?bi('Primary channel is in use','Задействован основной канал'):model.selectedRole==='target'?bi('Reserve is in use','Задействован резерв'):model.moving?bi('Switching the channel','Переключение канала'):bi('Confirming the active channel','Рабочий канал уточняется')),
      E('div',{'class':'hv-simple-pair'},[member(model.source,'source'),member(model.target,'target')]),
      E('button',{'type':'button','class':'cbi-button hv-simple-open-menu','data-simple-open-menu':'1','click':openMenu},bi('Advanced menu','Расширенное меню'))
    ])
  ]);
}
