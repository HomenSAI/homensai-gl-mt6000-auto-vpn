function autoRequestAcknowledged(result,stop){return !!result&&typeof result==='object'&&result.queued===true&&result.accepted!==false&&(stop||result.accepted===true);}
// Display-only parsing; the controller separately enforces bounded deadlines.
function autoWindowDeadline(intent,settings){
  function positive(raw){
    if(typeof raw==='number')return Number.isFinite(raw)&&raw>0?raw:0;
    if(typeof raw!=='string')return 0;
    raw=raw.trim();if(!raw)return 0;
    if(/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw)){var n=Number(raw);return Number.isFinite(n)&&n>0?n:0;}
    if(!/T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(raw))return 0;
    var parsed=Date.parse(raw)/1000;return Number.isFinite(parsed)&&parsed>0?parsed:0;
  }
  return positive((intent||{}).until)||positive((settings||{}).native_until);
}
function autoControlModel(status,now){
  var ns=status.native_failover||{}, intent=status.auto_control||{};
  var monitorFresh=Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var fresh=!status.rpc_error&&monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var on=fresh&&((ns.state==='OBSERVING'&&ns.certified===true)||ns.state==='COMMITTED');
  var transitioning=fresh&&['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0;
  var off=fresh&&['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(ns.state)>=0;
  var awaiting=fresh&&intent.requested_at>ns.time;
  return {fresh:fresh,on:on,transitioning:transitioning,off:off,awaiting:awaiting,
    stop:on||transitioning||intent.requested==='on'||['DEGRADED-ON-RESERVE','COMMITTED','ARMED','APPLYING','WAIT-CLIENT','RESTORING','STOPPED-ON-RESERVE'].indexOf(ns.state)>=0,
    returned:off&&ns.original_restored===true,
    color:!fresh?'unknown':awaiting||transitioning?'pending':on?'on':off?'off':'error'};
}
function autoPathModel(status,source,target,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{};
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  if(!model.fresh||model.off||model.awaiting)return neutral;
  if(source&&target&&source.id&&source.id===target.id)return neutral;
  var selected=ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE'?'target':ns.state==='OBSERVING'&&ns.certified===true?'source':null;
  if(!selected&&!model.transitioning)return neutral;
  var destination=model.transitioning?(ns.state==='RESTORING'?'source':'target'):null;
  function color(p,key){
    var state=p?profileHealth(p,now).state:'unknown';
    if(state==='failed')return 'failed';
    if(state==='inactive')return 'inactive';
    if(state==='unknown')return 'neutral';
    if(destination===key)return 'checking';
    if(state==='checking')return 'checking';
    return selected===key?'healthy':'ready';
  }
  return {source:color(source,'source'),target:color(target,'target'),direction:destination?(ns.state==='RESTORING'?'back':'forward'):selected==='target'?'forward':'none',moving:!!destination,selected:selected};
}

var autoRequestBusy=false;
function renderAutoControl(status,inventory){
  var ns=status.native_failover||{},intent=status.auto_control||{},model=autoControlModel(status,Date.now()/1000);
  var names={on:bi('Auto mode is ON','Авторежим включён'),off:bi('Auto mode is OFF','Авторежим выключен'),pending:bi('Waiting for controller','Ожидание контроллера'),error:bi('Auto mode needs attention','Авторежим требует внимания'),unknown:bi('Controller status unknown','Состояние контроллера неизвестно')};
  var stateText=names[model.color];
  if(model.fresh&&ns.state==='RESTORING')stateText=bi('Restoring previous policy','Восстанавливается предыдущая политика');
  else if(model.awaiting)stateText=intent.requested==='off'?bi('Stopping Auto; waiting for confirmation','Останавливается авторежим: ожидается подтверждение'):bi('Starting Auto; waiting for confirmation','Запускается авторежим: ожидается подтверждение');
  else if(model.transitioning)stateText=bi('Switching; waiting for path confirmation','Переключение: ожидается подтверждение пути');
  var explanation={
    'LAN-TRIAL-REQUIRED':'Run the LAN helper to certify the configured primary and reserve.',
    'BOUNDED-DEADLINE-REQUIRED':'The certified trial window has expired. A new LAN-certified window is required.',
    'SESSION-LOSS-NOT-ACCEPTED':'Accept possible call/session reconnection in Settings before testing.',
    'TRANSACTION-IN-PROGRESS':'A transaction is already in progress. Wait or request Stop.',
    'TRIAL-ATTEMPT-LIMIT':'This window reached its attempt limit. Start a new controlled trial.'
  };
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-'+model.color,'aria-label':model.stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим'),'aria-pressed':model.on?'true':'false','disabled':autoRequestBusy||(inventory.error||!model.fresh)&&!model.stop?'':null,'click':function(){
    if(autoRequestBusy)return;autoRequestBusy=true;button.disabled=true;
    return rpc.declare({object:'homensai-vpn',method:model.stop?'native_stop':'native_start',expect:{}})().then(function(result){
      if(result&&result.accepted===false){ui.addNotification(null,E('div',{},[E('strong',{},'AUTO-START-REFUSED'),E('ul',{},(result.blockers||[]).map(function(code){return E('li',{},code+' · '+(explanation[code]||'See controller diagnostics in Settings.'));}))]));}
      else if(!autoRequestAcknowledged(result,model.stop))ui.addNotification(null,E('p',{},'AUTO-CONTROL-UNVERIFIED: no confirmed acceptance; check controller state.'));
      else ui.addNotification(null,E('p',{},bi('Request queued. The indicator changes only after controller confirmation.','Запрос принят. Индикатор изменится после подтверждения контроллера.')));
    }).catch(function(){ui.addNotification(null,E('p',{},'AUTO-CONTROL-FAILED: no confirmed response; check controller state.'));}).finally(function(){autoRequestBusy=false;button.disabled=false;});
  }},E('span',{'class':'hv-power-symbol','aria-hidden':'true'}));
  var rows=status.profiles||[],settings=inventory.settings||{};
  function profile(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=profile(ns.source||settings.plan_source),target=profile(ns.target||settings.plan_target);
  var path=autoPathModel(status,source,target,Date.now()/1000);
  var pathLabels={neutral:bi('No current path confirmation','Нет свежего подтверждения пути'),healthy:bi('Active traffic path','Активный путь трафика'),ready:bi('Ready; not selected for traffic','Готов; трафик не направлен'),inactive:bi('Tunnel not connected','Туннель не подключён'),failed:bi('Connectivity failed','Ошибка доступности'),checking:bi('Checking / awaiting path confirmation','Проверяется / ожидается подтверждение пути')};
  function box(p,label,key){var state=path[key];return E('div',{'class':'hv-auto-node hv-path-'+state+(path.selected===key?' hv-path-selected':''),'data-path-node':key,'data-path-state':state},[E('small',{},label),E('strong',{},p?(p.protocol==='wireguard'?'WireGuard':'OpenVPN'):'—'),E('span',{},p?p.channel||'default':'—'),E('b',{},p?p.name:bi('Choose in Settings','Выберите в настройках')),E('span',{'class':'hv-path-label'},pathLabels[state]+(path.selected===key&&state!=='healthy'?' · '+bi('Selected route','Выбранный маршрут'):''))]);}
  var diagram=E('div',{'class':'hv-auto-diagram hv-path-diagram'+(path.moving?' hv-path-moving':'')+(path.direction==='back'?' hv-path-back':''),'aria-label':bi('Configured failover path','Настроенная схема переключения')},[box(source,bi('Primary','Основной'),'source'),E('span',{'class':'hv-auto-arrow '+(path.direction!=='none'?'hv-arrow-on':''),'aria-label':path.moving?bi('Switching in progress','Выполняется переключение'):path.direction!=='none'?bi('Reserve selected','Выбран резерв'):bi('Automatic transition inactive','Автопереход неактивен')},path.direction==='back'?'←':path.direction==='forward'?'→':'⋯'),box(target,bi('Reserve','Резерв'),'target')]);
  var handover=model.returned?bi('Auto is OFF. Monitoring continues. Control returned to router; original policy verified.','Авторежим выключен. Мониторинг продолжается. Управление возвращено роутеру; исходная политика проверена.'):ns.state==='STOPPED-ON-RESERVE'?bi('Automatic switching stopped; reserve retained because the primary is not verified healthy.','Автопереключение остановлено; резерв сохранён, поскольку работа основного не подтверждена.'):bi('Monitoring continues. Original-route restoration is shown only when verified.','Мониторинг продолжается. Восстановление исходного маршрута показывается после проверки.');
  var until=autoWindowDeadline(intent,settings);
  return E('section',{'class':'hv-chart-card hv-auto-control'},[E('h2',{},bi('Automatic VPN failover','Автоматическое переключение VPN')),E('div',{'class':'hv-auto-switch'},[E('div',{'class':'hv-auto-power-unit'},[button,E('span',{'class':'hv-auto-action'},model.stop?bi('Stop','Стоп'):bi('Start','Старт'))]),E('div',{},[E('strong',{'class':'hv-auto-label'},stateText),E('p',{'role':'status','aria-live':'polite'},bi('Controller: ','Контроллер: ')+(ns.state||'UNKNOWN')+(ns.reason?' · '+ns.reason:'')+(model.fresh?'':' · STATUS-STALE'))])]),diagram,E('p',{'class':'hv-path-legend'},bi('Green: selected and healthy. Grey: ready but not selected, or unconfirmed. Yellow: transition/check. Red: confirmed failure. Both tunnels may be connected; this diagram shows the selected path for this failover plan.','Зелёный: выбран и исправен. Серый: готов, но не выбран, либо нет подтверждения. Жёлтый: переход/проверка. Красный: подтверждённый сбой. Оба туннеля могут быть подключены; схема показывает выбранный путь этого плана переключения.')),E('p',{},handover),E('p',{'class':'hv-auto-limit'},bi('Experimental bounded mode: a running LAN helper confirms each switch.','Ограниченный экспериментальный режим: работающий LAN-помощник подтверждает каждое переключение.')),E('small',{},bi('Window ends: ','Окончание окна: ')+(Number.isFinite(until)&&until>0?new Date(until*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB'):'—')),E('p',{},E('a',{'href':'#settings'},bi('Configure profiles and download LAN helper','Настроить профили и скачать LAN-помощник')))]);
}
