/* Bottom-left of the sidebar: always visible Auto switch state, monitor state and program version. */
function fillSideStatus(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=Date.now()/1000,model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var state=!model.fresh?'unknown':(model.on||model.transitioning)?'on':'off';
  var label=state==='on'?bi('Auto ON','Auto включён'):state==='off'?bi('Auto OFF','Auto выключен'):bi('Auto: no data','Auto: нет данных');
  var hint=state==='on'?bi('Auto is on: it can switch to the reserve VPN.','Auto включён: он может переключить на резервный VPN.'):state==='off'?bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.'):bi('No fresh data from the router, so the state is not known.','Нет свежих данных от роутера, поэтому состояние неизвестно.');
  host.appendChild(E('div',{'class':'hv-auto-pill hv-auto-pill-'+state,'role':'status','aria-live':'polite','title':hint},[E('span',{'class':'hv-auto-pill-knob','aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},label)]));
  host.appendChild(E('p',{'class':'hv-side-monitor'},[E('span',{'class':'hv-dot hv-dot-'+(monitorFresh?'green':'red'),'aria-hidden':'true'}),' '+(monitorFresh?bi('Monitor works','Мониторинг работает'):status.rpc_error?bi('Router does not answer','Роутер не отвечает'):bi('Monitor is not sending data','Мониторинг не присылает данные'))]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}
