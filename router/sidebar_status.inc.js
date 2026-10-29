/* Bottom-left of the sidebar: two small lamps in one row (Auto, Monitoring) and the program version. Always visible. */
function fillSideStatus(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&observationFresh(status,now);
  var light=typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null;
  // "No connection" is reserved for a lost router-program answer; stale controller data and recovery have their own words.
  var rpcLost=!!(status.rpc_error||status.error),problem=!rpcLost&&light&&light.key==='problem';
  var state=rpcLost||!model.fresh&&!problem?'unknown':light&&typeof autoWorking==='function'?(autoWorking(light)?'on':light.key==='switching'||light.key==='unknown'?'unknown':'off'):(model.on||model.transitioning)?'on':'off';
  var signal=light&&typeof autoSignal==='function'?autoSignal(light):null;
  if(signal)state=signal==='off'?'dark':(typeof autoRuns==='function'?autoRuns(light):signal!=='red')?'on':signal==='yellow'?'switching':'off';
  var autoText=state==='on'?bi('Auto ON','Auto вкл.'):state==='off'?bi('Auto OFF','Auto выкл.'):rpcLost?bi('Auto: no connection','Auto: нет связи'):bi('Auto: data out of date','Auto: данные устарели');
  var autoHint=state==='on'?bi('Auto is on: it can switch to the reserve VPN.','Auto включён: он может переключить на резервный VPN.'):state==='off'?bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.'):rpcLost?bi('The page gets no answer from the router program, so the state is not known.','Страница не получает ответ от программы роутера, поэтому состояние неизвестно.'):bi('The router answers, but the Auto controller state is out of date.','Роутер отвечает, но состояние контроллера Auto устарело.');
  if(signal==='off'){autoText=bi('Auto OFF','Auto выкл.');autoHint=bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.');}
  else if(signal&&signal!=='green'&&light&&state!=='on'){autoText=light.title;autoHint=light.hint;}
  else if(!signal&&!rpcLost&&(model.fresh||problem)&&light&&(light.hold||['switching','unknown','problem'].indexOf(light.key)>=0)){autoText=light.title;autoHint=light.hint;}
  if(!signal&&state==='unknown'&&model.fresh&&light&&['KERNEL-POLICY-UNVERIFIED','PAIR-POLICY-UNVERIFIED'].indexOf(light.code)>=0){autoText=bi('Auto: route not verified','Auto: маршрут не подтверждён');autoHint=light.hint+' · '+light.code;}
  var monText=bi('Monitoring','Мониторинг');
  var monHint=monitorFresh?bi('Monitoring works: fresh data from the router.','Мониторинг работает: свежие данные от роутера.'):status.rpc_error?bi('The router does not answer.','Роутер не отвечает.'):bi('Monitoring is not sending data.','Мониторинг не присылает данные.');
  function lamp(kind,text,hint){return E('span',{'class':'hv-side-lamp','role':'status','title':hint},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+hint)]);}
  function openAuto(event){if(event&&event.type==='keydown'&&event.key!=='Enter'&&event.key!==' ')return;if(event&&event.preventDefault)event.preventDefault();var link=document.querySelector('[data-hv-tab="overview"]');if(link&&typeof pageKeyNow==='function'&&pageKeyNow()!=='overview')link.click();else if(typeof overviewToAuto==='function')overviewToAuto();else if(typeof goToSection==='function')goToSection('overview','hv-auto-vpn');}
  var autoTitle=autoHint+' '+bi('Click to open Automatic VPN failover.','Нажмите, чтобы открыть «Автоматическое переключение VPN».');
  var autoLamp=E('span',{'class':'hv-side-lamp hv-side-lamp-link','role':'link','tabindex':'0','title':autoTitle,'click':openAuto,'keydown':openAuto},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+state,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},autoText),E('span',{'class':'hv-visually-hidden'},' — '+autoTitle)]);
  host.appendChild(E('div',{'class':'hv-side-lamps'},[autoLamp,lamp(monitorFresh?'on':'off',monText,monHint)]));
  var path=status.channel_path||{},ns=status.native_failover||{},settings=(inventory||{}).settings||{},rows=status.profiles||[];
  var sourceId=settings.plan_source||path.source_profile_id||ns.source,targetId=settings.plan_target||path.target_profile_id||ns.target;
  var source=rows.filter(function(p){return p.id===sourceId;})[0],target=rows.filter(function(p){return p.id===targetId;})[0];
  var confirmed=(typeof heldConfirmedPath==='function'?heldConfirmedPath:manualConfirmedPath)(status,source,target,now),runs=autoRuns(light);
  function channel(role,label){
    var row=role==='source'?source:target,tone=manualChannelTone(row,role,confirmed,now,runs,status);
    if(!monitorFresh)tone={color:'grey',text:typeof dataCause==='function'?dataCause(status,now).text:bi('no router data','нет данных роутера')};
    return lamp({green:'on',yellow:'switching',grey:'unknown',red:'off'}[tone.color]||'unknown',label,label+': '+tone.text);
  }
  host.appendChild(E('div',{'class':'hv-side-channel-lamps'},[channel('source',bi('Primary','Основной')),channel('target',bi('Reserve','Резерв'))]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}
