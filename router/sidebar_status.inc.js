/* Bottom-left of the sidebar: two small lamps in one row (Auto, Monitoring) and the program version. Always visible. */
function fillSideStatus(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var state=!model.fresh?'unknown':(model.on||model.transitioning)?'on':'off';
  var autoText=state==='on'?bi('Auto ON','Auto вкл.'):state==='off'?bi('Auto OFF','Auto выкл.'):bi('Auto: ?','Auto: ?');
  var autoHint=state==='on'?bi('Auto is on: it can switch to the reserve VPN.','Auto включён: он может переключить на резервный VPN.'):state==='off'?bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.'):bi('No fresh data from the router, so the state is not known.','Нет свежих данных от роутера, поэтому состояние неизвестно.');
  var monText=bi('Monitoring','Мониторинг');
  var monHint=monitorFresh?bi('Monitoring works: fresh data from the router.','Мониторинг работает: свежие данные от роутера.'):status.rpc_error?bi('The router does not answer.','Роутер не отвечает.'):bi('Monitoring is not sending data.','Мониторинг не присылает данные.');
  function lamp(kind,text,hint){return E('span',{'class':'hv-side-lamp','role':'status','title':hint},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+hint)]);}
  host.appendChild(E('div',{'class':'hv-side-lamps'},[lamp(state,autoText,autoHint),lamp(monitorFresh?'on':'off',monText,monHint)]));
  var path=status.channel_path||{},ns=status.native_failover||{},selected=null;
  if(!status.rpc_error&&monitorFresh&&Number.isFinite(path.time)&&now-path.time>=-5&&now-path.time<=30&&path.confirmed===true)selected=path.active_profile_id;
  else if(!path.time&&model.fresh)selected=selectedProfile(status,now);
  var settings=(inventory||{}).settings||{},rows=status.profiles||[];
  function channel(role,label){
    var key=role==='source'?'source_profile_id':'target_profile_id',id=path[key]||ns[role]||settings['plan_'+role];
    var row=rows.filter(function(p){return p.id===id;})[0],health=row?profileHealth(row,now).state:'unknown',active=id&&selected===id;
    var color=active&&health==='healthy'?'on':selected||health==='failed'||health==='inactive'?'off':'unknown';
    var hint=active&&health==='healthy'?bi('Selected channel; Internet works','Выбранный канал; Интернет работает'):active?bi('Selected channel; Internet check failed or pending','Выбранный канал; проверка Интернета не пройдена или ещё выполняется'):selected?bi('Channel not in use','Канал не задействован'):bi('Waiting for router channel selection','Ожидается выбор канала от роутера');
    return lamp(color,label,hint);
  }
  host.appendChild(E('div',{'class':'hv-side-channel-lamps'},[channel('source',bi('Primary','Основной')),channel('target',bi('Reserve','Резерв'))]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}
