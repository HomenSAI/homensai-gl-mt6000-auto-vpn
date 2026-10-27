/* Bottom-left of the sidebar: two small lamps in one row (Auto, Monitoring) and the program version. Always visible. */
function fillSideStatus(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var state=!model.fresh?'unknown':(model.on||model.transitioning)?'on':'off';
  var autoText=state==='on'?bi('Auto ON','Auto вкл.'):state==='off'?bi('Auto OFF','Auto выкл.'):bi('Auto: no connection','Auto: нет связи');
  var autoHint=state==='on'?bi('Auto is on: it can switch to the reserve VPN.','Auto включён: он может переключить на резервный VPN.'):state==='off'?bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.'):bi('No fresh data from the router, so the state is not known.','Нет свежих данных от роутера, поэтому состояние неизвестно.');
  var monText=bi('Monitoring','Мониторинг');
  var monHint=monitorFresh?bi('Monitoring works: fresh data from the router.','Мониторинг работает: свежие данные от роутера.'):status.rpc_error?bi('The router does not answer.','Роутер не отвечает.'):bi('Monitoring is not sending data.','Мониторинг не присылает данные.');
  function lamp(kind,text,hint){return E('span',{'class':'hv-side-lamp','role':'status','title':hint},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+hint)]);}
  function openAuto(event){if(event&&event.type==='keydown'&&event.key!=='Enter'&&event.key!==' ')return;if(event&&event.preventDefault)event.preventDefault();var link=document.querySelector('[data-hv-tab="overview"]');if(link&&typeof pageKeyNow==='function'&&pageKeyNow()!=='overview')link.click();else if(typeof overviewToAuto==='function')overviewToAuto();else if(typeof goToSection==='function')goToSection('overview','hv-auto-vpn');}
  var autoTitle=autoHint+' '+bi('Click to open Automatic VPN failover.','Нажмите, чтобы открыть «Автоматическое переключение VPN».');
  var autoLamp=E('span',{'class':'hv-side-lamp hv-side-lamp-link','role':'link','tabindex':'0','title':autoTitle,'click':openAuto,'keydown':openAuto},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+state,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},autoText),E('span',{'class':'hv-visually-hidden'},' — '+autoTitle)]);
  host.appendChild(E('div',{'class':'hv-side-lamps'},[autoLamp,lamp(monitorFresh?'on':'off',monText,monHint)]));
  var path=status.channel_path||{},ns=status.native_failover||{},selected=null;
  if(!status.rpc_error&&monitorFresh&&Number.isFinite(path.time)&&now-path.time>=-5&&now-path.time<=30&&path.confirmed===true)selected=path.active_profile_id;
  else if(!path.time&&model.fresh)selected=selectedProfile(status,now);
  var settings=(inventory||{}).settings||{},rows=status.profiles||[];
  function channel(role,label){
    var key=role==='source'?'source_profile_id':'target_profile_id',id=path[key]||ns[role]||settings['plan_'+role];
    var row=rows.filter(function(p){return p.id===id;})[0],health=row?profileHealth(row,now).state:'unknown',active=id&&selected===id;
    var rel=row&&health==='healthy'&&typeof channelReliability==='function'?channelReliability(row,status,now):null;
    var color,why;
    if(!monitorFresh){color='unknown';why=typeof dataCause==='function'?dataCause(status,now).text:bi('no router data','нет данных роутера');}
    else if(!row){color='off';why=bi('no channel is chosen for this role (Channels and servers)','для этой роли не выбран канал («Каналы и серверы»)');}
    else if(health==='inactive'){color='off';why=bi('switched off in the router','выключен в роутере');}
    else if(health==='failed'){color='off';why=typeof channelCheckText==='function'?channelCheckText(row,now):bi('router check failed','проверка роутера не прошла');}
    else if(rel&&rel.unreliable){color='switching';why=bi('works, but unreliable: ','работает, но ненадёжно: ')+reliabilityText(rel);}
    else if(health==='healthy'&&state!=='on'){color='switching';why=role==='source'?bi('Primary channel: alive and waiting to be switched on by Auto','Основной канал: живой и ожидает включения в режиме автомат'):bi('Reserve channel: alive and waiting to be switched on by Auto','Запасной канал: живой и ожидает включения в режиме автомат');}
    else if(health==='healthy'&&selected&&!active){color='switching';why=role==='source'?bi('Primary channel: alive and waiting to be switched on by Auto','Основной канал: живой и ожидает включения в режиме автомат'):bi('Reserve channel: alive and waiting to be switched on by Auto','Запасной канал: живой и ожидает включения в режиме автомат');}
    else if(health==='healthy'&&active){color='on';why=bi('works in Auto and carries your traffic','работает в автомате и несёт ваш трафик');}
    else{color='unknown';why=bi('waiting for the router\'s answer','ждём ответа роутера');}
    return lamp(color,label,label+': '+why);
    var hint=active&&health==='healthy'?bi('Selected channel; Internet works','Выбранный канал; Интернет работает'):active?bi('Selected channel; Internet check failed or pending','Выбранный канал; проверка Интернета не пройдена или ещё выполняется'):selected?bi('Channel not in use','Канал не задействован'):bi('The router has not reported which VPN is in use yet','Роутер ещё не сообщил, какой VPN работает');
    return lamp(color,label,hint);
  }
  host.appendChild(E('div',{'class':'hv-side-channel-lamps'},[channel('source',bi('Primary','Основной')),channel('target',bi('Reserve','Резерв'))]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}
