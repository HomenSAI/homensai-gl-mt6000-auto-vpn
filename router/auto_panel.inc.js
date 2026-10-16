function autoControlModel(status,now){
  var ns=status.native_failover||{}, intent=status.auto_control||{};
  var monitorFresh=Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var fresh=!status.rpc_error&&monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var on=fresh&&((ns.state==='OBSERVING'&&ns.certified===true)||ns.state==='COMMITTED');
  var transitioning=fresh&&['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0;
  var off=fresh&&['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(ns.state)>=0;
  var awaiting=fresh&&intent.requested_at>ns.time;
  return {fresh:fresh,on:on,transitioning:transitioning,off:off,awaiting:awaiting,
    stop:on||transitioning||intent.requested==='on'||ns.state==='STOPPED-ON-RESERVE',
    returned:off&&ns.original_restored===true,
    color:!fresh?'unknown':awaiting||transitioning?'pending':on?'on':off?'off':'error'};
}
var autoRequestBusy=false;
function renderAutoControl(status,inventory){
  var ns=status.native_failover||{},intent=status.auto_control||{},model=autoControlModel(status,Date.now()/1000);
  var names={on:bi('Auto mode is ON','Авторежим включён'),off:bi('Auto mode is OFF','Авторежим выключен'),pending:bi('Waiting for controller','Ожидание контроллера'),error:bi('Auto mode needs attention','Авторежим требует внимания'),unknown:bi('Controller status unknown','Состояние контроллера неизвестно')};
  var stateText=names[model.color];
  var explanation={
    'LAN-TRIAL-REQUIRED':'Run the LAN helper to certify the configured primary and reserve.',
    'BOUNDED-DEADLINE-REQUIRED':'The certified trial window has expired. A new LAN-certified window is required.',
    'SESSION-LOSS-NOT-ACCEPTED':'Accept possible call/session reconnection in Settings before testing.',
    'TRANSACTION-IN-PROGRESS':'A transaction is already in progress. Wait or request Stop.',
    'TRIAL-ATTEMPT-LIMIT':'This window reached its attempt limit. Start a new controlled trial.'
  };
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-'+model.color,'aria-label':model.stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим'),'aria-pressed':model.on?'true':'false','disabled':autoRequestBusy?'':null,'click':function(){
    if(autoRequestBusy)return;autoRequestBusy=true;button.disabled=true;
    return rpc.declare({object:'homensai-vpn',method:model.stop?'native_stop':'native_start',expect:{}})().then(function(result){
      if(result.accepted===false){ui.addNotification(null,E('div',{},[E('strong',{},'AUTO-START-REFUSED'),E('ul',{},(result.blockers||[]).map(function(code){return E('li',{},code+' · '+(explanation[code]||'See controller diagnostics in Settings.'));}))]));}
      else ui.addNotification(null,E('p',{},bi('Request queued. The indicator changes only after controller confirmation.','Запрос принят. Индикатор изменится после подтверждения контроллера.')));
    }).catch(function(){ui.addNotification(null,E('p',{},'AUTO-CONTROL-FAILED: no confirmed response; check controller state.'));}).finally(function(){autoRequestBusy=false;button.disabled=false;});
  }},E('span',{'aria-hidden':'true'},'⏻'));
  var rows=status.profiles||[],settings=inventory.settings||{};
  function profile(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=profile(ns.source||settings.plan_source),target=profile(ns.target||settings.plan_target);
  function box(p,label,selected){return E('div',{'class':'hv-auto-node'+(selected?' hv-auto-selected':'')},[E('small',{},label),E('strong',{},p?(p.protocol==='wireguard'?'WireGuard':'OpenVPN'):'—'),E('span',{},p?p.channel||'default':'—'),E('b',{},p?p.name:bi('Choose in Settings','Выберите в настройках'))]);}
  var diagram=E('div',{'class':'hv-auto-diagram','aria-label':bi('Configured failover path','Настроенная схема переключения')},[box(source,bi('Primary','Основной'),model.on&&ns.state!=='COMMITTED'),E('span',{'class':'hv-auto-arrow '+(model.on?'hv-arrow-on':''),'aria-label':model.on?bi('Automatic transition enabled','Автопереход включён'):bi('Automatic transition inactive','Автопереход неактивен')},model.on?'→':'⋯'),box(target,bi('Reserve','Резерв'),model.on&&ns.state==='COMMITTED')]);
  var handover=model.returned?bi('Control returned to router; original policy verified.','Управление возвращено роутеру; исходная политика проверена.'):ns.state==='STOPPED-ON-RESERVE'?bi('Automatic switching stopped; reserve retained because the primary is not verified healthy.','Автопереключение остановлено; резерв сохранён, поскольку работа основного не подтверждена.'):bi('Monitoring continues. Original-route restoration is shown only when verified.','Мониторинг продолжается. Восстановление исходного маршрута показывается после проверки.');
  var until=intent.until||Number(settings.native_until)||Date.parse(settings.native_until||'')/1000;
  return E('section',{'class':'hv-chart-card hv-auto-control'},[E('h2',{},bi('Automatic VPN failover','Автоматическое переключение VPN')),E('div',{'class':'hv-auto-switch'},[button,E('div',{},[E('strong',{'class':'hv-auto-label'},stateText),E('p',{'role':'status','aria-live':'polite'},'Controller: '+(ns.state||'UNKNOWN')+(model.fresh?'':' · STATUS-STALE'))])]),diagram,E('p',{},handover),E('p',{'class':'hv-auto-limit'},bi('Experimental bounded mode: a running LAN helper confirms each switch.','Ограниченный экспериментальный режим: работающий LAN-помощник подтверждает каждое переключение.')),E('small',{},bi('Window ends: ','Окончание окна: ')+(Number.isFinite(until)&&until>0?new Date(until*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB'):'—')),E('p',{},E('a',{'href':'#settings'},bi('Configure profiles and download LAN helper','Настроить профили и скачать LAN-помощник')))]);
}
