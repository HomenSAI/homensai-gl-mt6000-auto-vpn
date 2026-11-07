// HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
'use strict';
'require view';
'require rpc';
'require poll';
'require ui';
'require baseclass';
'require request';
/* Display logic extracted from the legacy pipeline (router/legacy_page_build.py) by router/ui_extract.py. */
function hvElementChildren(value){
  if(value===null||value===undefined)return [];
  if(!Array.isArray(value))return value;
  var result=[];
  value.forEach(function(child){
    if(child===null||child===undefined)return;
    if(Array.isArray(child)){var nested=hvElementChildren(child);Array.prototype.push.apply(result,nested);}
    else result.push(child);
  });return result;
}
var E=(function(nativeElement){
  nativeElement=nativeElement&&nativeElement.__homensaiRawElement||nativeElement;
  if(typeof nativeElement!=='function')throw new Error('DOM element factory unavailable');
  function element(){
    var args=Array.prototype.slice.call(arguments);
    if(Array.isArray(args[0]))args[0]=hvElementChildren(args[0]);
    if(args.length>2)args[2]=hvElementChildren(args[2]);
    else if(args.length===2&&Array.isArray(args[1]))args[1]=hvElementChildren(args[1]);
    return nativeElement.apply(null,args);
  }
  Object.defineProperty(element,'__homensaiRawElement',{value:nativeElement});return element;
})(typeof L!=='undefined'&&L.dom&&typeof L.dom.create==='function'?L.dom.create.bind(L.dom):typeof globalThis!=='undefined'?globalThis.E:window.E);
var savedLanguage='en';
var requestedLanguage=new URLSearchParams(window.location.search).get('lang');
var locale=(requestedLanguage||savedLanguage)==='ru'?'ru':'en';
var translations = {"Туннель не подключён": "Tunnel disconnected", "HTTPS через VPN не проходит": "HTTPS through VPN failed", "DNS не отвечает": "DNS unavailable", "Маршрут не соответствует VPN": "Route does not match VPN", "Путь проверки не подтверждён": "Probe path unverified", "Ошибка службы или зависимости": "Service or dependency error", "Ошибка сохранения статистики": "Statistics storage error", "Статистика восстановлена из резервной копии": "Statistics restored from backup", "Время роутера ещё не установлено": "Router clock is not set", "Профиль сейчас не подключён": "This VPN is not connected", "Профиль вне лимита текущего раунда": "Skipped this round (check limit reached)", "Служба остановлена": "Service unavailable", "График появится после двух успешных измерений. Искусственных данных здесь нет.": "The chart appears after two successful checks. Nothing is made up.", "Приоритет": "Priority", "Наблюдать": "Monitor", "ожидается": "pending", " из ": " of ", "Нет данных": "No data", "Ошибка": "Error", "Каждые ": "Every ", " мин": " min", "Отключён": "Disabled", "Отправлен ": "Sent ", "Нет подтверждённой отправки": "No confirmed delivery", "Измерено ": "Measured ", "нет данных": "no data", "Подключённые серверы не обнаружены.": "No connected servers detected.", "Задержка серверов во времени": "Server latency over time", "Сервер": "Server", "Канал": "Channel", "Протокол": "Protocol", "Интерфейс": "Interface", "Результат": "Result", "Время проверки": "Checked at", "Текущие проверки серверов": "Current check per server", "Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.": "VPNs that are not connected are listed but never started by this program. To test one, connect it yourself in the GL.iNet VPN Dashboard.", "Рейтинг измеренных профилей": "Ranking of measured servers", "Успех проверок": "Checks passed", " мс": " ms", "Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.": "The ranking uses hourly averages from up to seven days of checks. It is not a speed test and changes no priorities by itself.", "VPN-трафик по календарным месяцам · Europe/Berlin": "VPN traffic by calendar month · Europe/Berlin", "Месяц": "Month", "Входящий": "Received", "Исходящий": "Sent", "Всего": "Total", "Наблюдение": "Observation", " интерфейс-часов": " interface-hours", " · граница оценена": " · estimated month boundary", "Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ": "Unique VPN interfaces are counted once, including protocol overhead. Observation gaps: ", ". После потери питания возможна потеря последнего интервала checkpoint.": ". A power loss may lose the latest checkpoint interval.", "Монитор служб": "Service monitor", "Скачать журнал": "Export events"};
function tr(value){return locale==='ru'?value:(translations[value]||value);}
function bi(en,ru){return locale==='ru'?ru:en;}
function diagnosticText(value){return translations[value]||value;}
var statusRpc=rpc.declare({object:'homensai-vpn',reject:true,method:'status',expect:{}});
var statusCall=function(){return uiStatusRequest(statusRpc);};
var inventoryCall=rpc.declare({object:'homensai-vpn',reject:true,method:'inventory',expect:{}});
var codes={
  'VPN-001':diagnosticText("Туннель не подключён"), 'VPN-003':diagnosticText("HTTPS через VPN не проходит"),
  'DNS-001':diagnosticText("DNS не отвечает"), 'ROUTE-001':diagnosticText("Маршрут не соответствует VPN"),
  'CHECK-001':diagnosticText("Путь проверки не подтверждён"), 'SYSTEM-001':diagnosticText("Ошибка службы или зависимости"),
  'STORAGE-001':diagnosticText("Ошибка сохранения статистики"), 'STORAGE-RECOVERED':diagnosticText("Статистика восстановлена из резервной копии"), 'CLOCK-001':diagnosticText("Время роутера ещё не установлено"), 'PROFILE-INACTIVE':diagnosticText("Профиль сейчас не подключён"),
  'CHECK-LIMIT':diagnosticText("Профиль вне лимита текущего раунда"), 'SERVICE-STOPPED':diagnosticText("Служба остановлена")
};
function text(value){return value==null?'—':String(value);}
var MANUAL_SWITCH_PENDING=false,MANUAL_SWITCH_DIRECTION=null,MANUAL_SWITCH_OPERATION=null,MANUAL_SWITCH_FEEDBACK=null;
var MANUAL_RESULT_SEEN=new Map();
var MANUAL_TERMINAL_STATES=['COMPLETED','REFUSED','CANCELLED','UNCONFIRMED'];
function manualClockTick(){return typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();}
function manualOperationModel(status,now){
  var row=status.manual_switch||{},op=MANUAL_SWITCH_OPERATION,valid=!status.rpc_error&&!status.error&&observationFresh(status,now);
  var same=op&&typeof row.request_id==='string'&&(op.request_id?row.request_id===op.request_id:row.request_id!==op.previous&&row.direction===op.direction&&Number.isFinite(row.requested_at)&&row.requested_at>=op.baseline-5);
  var terminal=MANUAL_TERMINAL_STATES.indexOf(row.state)>=0,typedTerminal=terminal&&row.completed===(row.state==='COMPLETED')&&Number.isFinite(row.updated_at)&&row.updated_at>=0&&(op&&op.request_id&&row.request_id===op.request_id||row.updated_at>=(op?op.baseline:0)-5&&row.updated_at<=now+5);
  if(op&&valid&&same&&typedTerminal){
    MANUAL_SWITCH_FEEDBACK=row;MANUAL_SWITCH_OPERATION=op=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;
  }else if(op&&valid&&same){op.request_id=row.request_id;op.acknowledged=true;if(terminal)op.uncertain=true;}
  var backendPending=['QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'].indexOf(row.state)>=0,ours=backendPending&&(!op||same);
  var transition=typeof uiTransitionModel==='function'?uiTransitionModel(status,now):{live:false},stage=op&&!op.acknowledged?'SENT':null,deadline=null;
  if(ours&&valid){stage=row.state;deadline=row.state==='QUEUED'&&Number.isFinite(row.requested_at)?row.requested_at+60:Number.isFinite(row.updated_at)?row.updated_at+125:null;}
  if((op||backendPending)&&transition.live){stage=transition.state;deadline=transition.deadline;}
  var elapsed=op&&Number.isFinite(op.tick)?(manualClockTick()-op.tick)/1000:op?(Date.now()-op.t0)/1000:backendPending&&Number.isFinite(row.requested_at)?now-row.requested_at:null;
  var late=Number.isFinite(deadline)?now>deadline+15:Number.isFinite(elapsed)&&elapsed>120;
  if(op&&late)op.uncertain=true;
  return {busy:!!op||backendPending,direction:op?op.direction:backendPending?row.direction:null,
    uncertain:!!(op&&op.uncertain)||backendPending&&(!valid||late),request:op||row,
    stage:stage,deadline:deadline,elapsed:elapsed,checking:transition.live&&transition.phase==='checking'||Number.isFinite(deadline)&&now>deadline};
}
function uiOperationTimerText(status,now){
  status=status||{};var timing=status.switch_timing;UI_SWITCH_AVG=timing&&Number.isFinite(timing.avg_seconds)&&timing.avg_seconds>=1&&timing.avg_seconds<=600?timing.avg_seconds:null;var manual=manualOperationModel(status,now),transition=typeof uiTransitionModel==='function'?uiTransitionModel(status,now):{live:false};
  if(manual.busy)return manual.uncertain?bi('Result not confirmed','Результат не подтверждён')+(Number.isFinite(manual.elapsed)?' · '+uiClock(manual.elapsed)+bi(' elapsed',' прошло'):''):uiOperationTimer(manual.stage,manual.elapsed,Number.isFinite(manual.deadline)?manual.deadline-now:null,manual.checking,!!(status.manual_switch_control&&status.manual_switch_control.instant===true));
  var command=typeof autoCommandPending!=='undefined'&&(autoCommandPending||autoObservedOperation),elapsed=command?autoElapsedMs(command)/1000:transition.started?now-transition.started:null;
  if(transition.live)return uiTransitionText(transition,elapsed,now);
  if(command)return uiOperationTimer(null,elapsed,null,false);
  return '';
}
function uiTransitionText(transition,elapsed,now){return uiOperationTimer(transition.state,elapsed,transition.deadline-now,transition.phase==='checking');}
function manualFresh(time,now,limit){return Number.isFinite(time)&&now-time>=-5&&now-time<=limit;}
function manualResultFresh(row,now){
  var stamp=row.updated_at,id=row.request_id,tick=manualClockTick();
  if(!Number.isFinite(stamp)||stamp<0)return false;
  var known=typeof id==='string'&&/^[a-f0-9]{32}$/.test(id),first=known?MANUAL_RESULT_SEEN.get(id):undefined;
  if(known&&first===undefined){first=tick;MANUAL_RESULT_SEEN.set(id,first);}
  return (!known||tick-first>=0&&tick-first<=300000)&&(manualFresh(stamp,now,300)||known&&stamp>now+5);
}
var UI_PATH_MEMORY=null,UI_PATH_MEMORY_SECONDS=120;
function heldConfirmedPath(status,source,target,now){
  var proof=manualConfirmedPath(status,source,target,now),ns=(status||{}).native_failover||{},sid=source&&source.id,tid=target&&target.id;
  if(proof.selected){UI_PATH_MEMORY={selected:proof.selected,source:sid,target:tid,at:now};return proof;}
  var blockers=Array.isArray(ns.blockers)?ns.blockers:[];
  if(!proof.moving&&!proof.pending&&UI_PATH_MEMORY&&UI_PATH_MEMORY.source===sid&&UI_PATH_MEMORY.target===tid&&now-UI_PATH_MEMORY.at>=-5&&now-UI_PATH_MEMORY.at<=UI_PATH_MEMORY_SECONDS
     &&((status||{}).auto_control||{}).requested==='on'&&['OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','BLOCKED'].indexOf(ns.state)>=0
     &&(typeof AUTO_TRANSIENT==='undefined'||blockers.every(function(c){return AUTO_TRANSIENT.indexOf(c)>=0;})))
    return Object.assign({},proof,{selected:UI_PATH_MEMORY.selected,code:null,held:true});
  return proof;
}
function manualConfirmedPath(status,source,target,now){
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
  if(proof.authoritative){
    if(proof.moving)return {source:'checking',target:'checking',direction:'forward',moving:true,selected:null};
    if(!proof.selected)return Object.assign({},neutral,{code:proof.code});
    var selected=source&&proof.selected===source.id?'source':target&&proof.selected===target.id?'target':null;
    var operation=manualOperationModel(status,now),autoOperation=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null;return {source:selected?'ready':'neutral',target:selected?'ready':'neutral',direction:operation.busy?(operation.direction==='primary'?'back':operation.direction==='reserve'?'forward':'none'):selected==='target'?'forward':'none',moving:false,pending:operation.busy||!!autoOperation,uncertain:operation.uncertain||autoOperation==='unconfirmed',selected:selected,code:proof.code};
  }
  if(status.rpc_error||status.error||!observationFresh(status,now))return neutral;
  var ns=status.native_failover||{};
  if(!source||!target||ns.source&&ns.source!==source.id||ns.target&&ns.target!==target.id)return neutral;
  var path=autoPathModel(status,source,target,now),model=autoControlModel(status,now);
  if(model.fresh&&model.off&&ns.original_restored===true&&source&&target&&source.id!==target.id)path.selected='source';
  if(model.fresh&&ns.state==='STOPPED-ON-RESERVE'&&source&&target&&source.id!==target.id&&ns.original_restored===false)path.selected='target';
  return path;
}
function manualChannelTone(profile,key,path,now,autoRuns,status){
  var health=profile?profileHealth(profile,now).state:'unknown',selected=path.selected===key;
  var waitText=channelAliveText(key==='target'||key==='reserve'?'reserve':'primary',status,now);
  if(!profile)return {color:'grey',text:bi('Not chosen','Не выбран'),carrier:false};
  if((path.moving||path.pending)&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Not working','Не работает'):bi('Not connected','Не подключён'),carrier:false};
  if(path.moving||path.pending)return {color:'yellow',switching:true,text:path.uncertain?bi('Request not confirmed · waiting for fresh router state','Запрос не подтверждён · ждём актуального состояния роутера'):bi('Switching · waiting for the router','Переключение · ждём роутер'),carrier:false};
  if(!path.selected&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Not working','Не работает'):bi('Not connected','Не подключён'),carrier:false};
  if(path.code&&!path.selected)return {color:autoRuns===false||(health!=='healthy'&&health!=='checking')||!(status&&!status.rpc_error&&!status.error&&observationFresh(status,now))?'grey':'yellow',switching:autoRuns!==false,text:bi('Router is confirming the route','Роутер подтверждает маршрут')+' · '+path.code,carrier:false};
  if(health==='healthy'&&autoRuns===false)return {color:'yellow',text:selected?bi('Live · carries your traffic; Auto is not running','Живой · несёт трафик; Auto не работает'):waitText,carrier:selected};
  var answered=!!status&&!status.rpc_error&&!status.error&&observationFresh(status,now);
  if(!path.selected&&answered&&autoRuns!==false&&(health==='healthy'||health==='checking'))return {color:'yellow',switching:true,text:bi('Router is confirming the route','Роутер подтверждает маршрут'),carrier:false};
  if(!path.selected||health==='unknown'||health==='checking')return {color:'grey',text:bi('Waiting for the router\'s answer','Ждём ответа роутера'),carrier:false};
  if(selected&&health==='healthy')return {color:'green',text:bi('Works in Auto · carries your traffic','Работает в автомате · несёт трафик'),carrier:true};
  if(selected)return {color:'red',text:health==='failed'?bi('In use · connectivity failed','Используется · ошибка доступности'):bi('Selected tunnel is not connected','Выбранный туннель не подключён'),carrier:true};
  if(health==='healthy')return {color:'yellow',text:waitText,carrier:false};
  return {color:'red',text:health==='failed'?bi('Not in use · connectivity failed','Не используется · ошибка доступности'):health==='inactive'?bi('Not in use · not connected','Не используется · не подключён'):bi('Not in use · available','Не используется · доступен'),carrier:false};
}
function manualControlModel(status,now){
  var control=status.manual_switch_control||{},request=status.manual_switch||{},revision=control.control_revision;
  var fresh=!status.rpc_error&&!status.error&&observationFresh(status,now)&&manualFresh(control.time,now,30);
  var operation=manualOperationModel(status,now),autoOperation=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null,busy=operation.busy||!!autoOperation;
  function direction(key){var row=control[key]||{},codes=Array.isArray(row.blockers)?row.blockers:Array.isArray(control.blockers)?control.blockers:[];
    return {allowed:fresh&&!busy&&control.available===true&&row.allowed===true&&typeof revision==='string'&&/^[a-f0-9]{32}$/.test(revision),blockers:codes.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);})};}
  return {fresh:fresh,busy:busy,uncertain:operation.uncertain,direction:operation.direction,revision:revision,mode:control.mode||'legacy',hold:control.hold||null,reserve:direction('reserve'),primary:direction('primary'),resume:direction('resume')};
}
function manualReason(codes){
  if(!codes.length)return bi('Manual switching is unavailable until the router confirms that it is ready.','Ручное переключение недоступно, пока роутер не подтвердит готовность.');
  return codes.map(function(code){
    var pairNotes={
      'PAIR-MANUAL-COOLDOWN':['Wait for the minimum dwell/cooldown interval before another forward switch.','Дождитесь окончания минимального интервала между переключениями.'],
      'PAIR-RATE-LIMIT':['The configured number of forward attempts has been used for the selected period. Wait; Stop and return remain available.','Достигнут заданный лимит попыток за выбранный период. Подождите; Stop и возврат остаются доступны.'],
      'PAIR-MANUAL-TARGET-UNHEALTHY':['The reserve has no fresh successful DNS/HTTPS confirmation. It will not be selected.','У резерва нет свежего успешного подтверждения DNS/HTTPS. Он не будет выбран.'],
      'PAIR-MANUAL-BUSY':['A transition or request is already in progress. The Auto switch remains available to turn Auto off or cancel startup.','Переключение или запрос уже выполняется. Переключатель Auto остаётся доступным, чтобы выключить Auto или отменить запуск.']};
    if(Object.prototype.hasOwnProperty.call(pairNotes,code))return bi(pairNotes[code][0],pairNotes[code][1]);
    var row=typeof ERROR_EXTRA_ROWS!=='undefined'?ERROR_EXTRA_ROWS.filter(function(item){return item[0]===code;})[0]:null;
    if(!row&&typeof ERROR_ROWS!=='undefined')row=ERROR_ROWS.filter(function(item){return item[0]===code;})[0];
    if(row)return row.length>=8?bi(row[4],row[5])+(row[6]?' '+bi(row[6],row[7]):''):code+' · '+bi(row[2],row[3]);
    return typeof AUTO_BLOCKERS!=='undefined'&&Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?autoBlockerText(code):bi('Switching is currently unavailable.','Переключение сейчас недоступно.');}).filter(function(text,index,all){return all.indexOf(text)===index;}).join(' ');
}
function manualSelectionModel(status,source,target,now){
  var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
  if(proof.authoritative)return {selected:source&&proof.selected===source.id?'primary':target&&proof.selected===target.id?'reserve':null,moving:proof.moving,code:proof.code};
  var native=status.native_failover||{};
  if(!status.rpc_error&&observationFresh(status,now)&&manualFresh(native.time,now,30)&&['STOPPED','DISABLED','EXPIRED'].indexOf(native.state)>=0&&source&&target&&profileHealth(source,now).state==='inactive'&&profileHealth(target,now).state==='inactive')return {selected:null,moving:false,off:true};
  var path=manualConfirmedPath(status,source,target,now);
  return {selected:path.selected==='source'?'primary':path.selected==='target'?'reserve':null,moving:path.moving};
}
function autoRequestAcknowledged(result,stop){return !!result&&typeof result==='object'&&result.queued===true&&result.accepted!==false&&(stop||result.accepted===true);}
function autoControlModel(status,now){
  var ns=status.native_failover||{}, intent=status.auto_control||{};
  var paused=!!status.speed_pause&&status.speed_pause.active===true&&status.speed_pause.auto_paused===true;
  var monitorFresh=typeof observationFresh==='function'?observationFresh(status,now):Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var live=typeof uiTransitionModel==='function'&&uiTransitionModel(status,now).live;
  var servedAt=typeof statusServedAt==='function'?statusServedAt(status,now):now;
  var fresh=!status.rpc_error&&!status.error&&monitorFresh&&Number.isFinite(ns.time)&&servedAt-ns.time>=-5&&(servedAt-ns.time<=30||live);
  var pairScope=ns.mode==='continuous-pair'||ns.proof_scope==='router-probed-ipv4'||(status.channel_path||{}).mode==='continuous-pair';
  var pairPermitsOn=intent.requested==='on'&&['RUNNING','HELD'].indexOf(intent.pair_phase)>=0,runningPair=pairScope&&pairPermitsOn;
  var on=!paused&&fresh&&(!pairScope||pairPermitsOn)&&((ns.state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true))||ns.state==='COMMITTED'||ns.state==='ROLLED-BACK'&&runningPair);
  var transitioning=fresh&&['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0;
  var off=fresh&&!on&&(['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(ns.state)>=0||pairScope&&intent.requested==='off'&&intent.pair_phase==='STOPPED');
  var awaiting=fresh&&intent.requested_at>ns.time&&!(pairScope&&(pairPermitsOn||intent.requested==='off'&&intent.pair_phase==='STOPPED'));
  return {fresh:fresh,on:on,paused:paused,transitioning:transitioning,off:off,awaiting:awaiting,
    stop:on||transitioning||intent.requested==='on'||['DEGRADED-ON-RESERVE','COMMITTED','ARMED','APPLYING','WAIT-CLIENT','RESTORING','STOPPED-ON-RESERVE'].indexOf(ns.state)>=0,
    returned:off&&ns.original_restored===true,
    color:paused?'pending':!fresh?'unknown':awaiting||transitioning?'pending':on?'on':off?'off':'error'};
}
function autoPathModel(status,source,target,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{};
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
  if(proof.authoritative){
    var picked=source&&proof.selected===source.id?'source':target&&proof.selected===target.id?'target':null;
    function tone(p,key){var h=p?profileHealth(p,now).state:'unknown';return h==='failed'?'failed':h==='inactive'?'inactive':h==='unknown'?'neutral':proof.moving||h==='checking'?'checking':picked===key?'healthy':picked?'ready':'neutral';}
    return {source:tone(source,'source'),target:tone(target,'target'),direction:proof.moving?'forward':picked==='target'?'forward':'none',moving:proof.moving,selected:picked,code:proof.code};
  }
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
var AUTO_BLOCKERS={
  'GUARD-DEVICE-UNVERIFIED':['An enabled VPN interface has no readable live state. Check Network → Interfaces for the selected clients; deleted or disabled profiles are excluded.','Не удалось прочитать рабочее состояние включённого VPN-интерфейса. Проверьте выбранные клиенты в «Сеть → Интерфейсы»; удалённые и отключённые профили исключаются.'],
  'EXISTING-TUNNEL-BINDING-UNVERIFIED':['The two selected VPN clients need distinct, confirmed live interfaces, routing tables and marks. Check the selected pair and current tunnel state.','У двух выбранных VPN-клиентов должны быть разные подтверждённые интерфейсы, таблицы маршрутизации и метки. Проверьте выбранную пару и текущее состояние туннелей.'],
  'MT3000-FIRMWARE-UNVERIFIED':['The actual MT3000 firmware, kernel or architecture does not match the verified profile. Keep monitoring and check the router facts.','Фактическая прошивка, ядро или архитектура MT3000 не совпадает с проверенным профилем. Оставьте мониторинг и проверьте данные роутера.'],
  'MT3000-FIREWALL-UNVERIFIED':['This MT3000 firewall arrangement is not verified. Native switching remains blocked.','Этот вариант firewall MT3000 не проверен. Нативное переключение остаётся заблокировано.'],
  'FW3-INCLUDE-CONTRACT-UNVERIFIED':['The stock FW3 VPN include differs from the verified configuration. Review it before switching.','VPN include штатного FW3 отличается от проверенной конфигурации. Проверьте его перед переключением.'],
  'FW3-RUNTIME-STATE-UNVERIFIED':['The running FW3 state cannot be verified. A connected VPN alone is insufficient.','Не удалось проверить рабочее состояние FW3. Одного подключённого VPN недостаточно.'],
  'FW3-SELECTED-ZONE-UNVERIFIED':['The running firewall does not contain both verified VPN zones.','Рабочий firewall не содержит обе проверенные VPN-зоны.'],
  'VENDOR-WORKER-QUIET-UNVERIFIED':['Completion of the router background work is unconfirmed. New switching stays blocked.','Завершение фоновой работы роутера не подтверждено. Новое переключение заблокировано.'],
  'MONITOR-ONLY-DEPLOYMENT':['This installation is limited to monitoring. Native switching is disabled; monitoring does not certify router firmware coordination or the LAN path.','Эта установка ограничена мониторингом. Нативное переключение выключено; мониторинг не подтверждает координацию с прошивкой роутера и путь LAN.'],
  'MONITOR-ONLY-INVALID':['The deployment mode could not be verified. Native actions remain blocked until the deployment settings are checked.','Не удалось проверить режим установки. Нативные действия остаются заблокированы до проверки параметров установки.'],
  'NATIVE-PROGRESS-UNVERIFIED':['Controller progress records cannot be trusted. New actions are blocked; Stop and recovery from a trusted journal remain available. Review the diagnostics before retrying.','Записям состояния контроллера нельзя доверять. Новые действия заблокированы; остановка и восстановление по доверенному журналу остаются доступны. Перед повтором проверьте диагностику.'],
  'RESERVE-IDENTITY-UNKNOWN':['Current reserve identity could not be matched to comparable observations. Its health and any automatic return remain unconfirmed.','Не удалось сопоставить текущий резерв с подходящими наблюдениями. Его здоровье и автоматический возврат остаются неподтверждёнными.'],
  'OBSERVATION-STALE':['Current tunnel or probe observations are missing or stale. Wait for fresh matching observations; old measurements cannot authorize a change.','Текущие наблюдения туннеля или проверок отсутствуют либо устарели. Дождитесь свежих согласованных данных; старые измерения не разрешают изменение.'],
  'VENDOR-IDENTITY-UNKNOWN':['The router tunnel binding is unknown or ambiguous. Save an active source and reserve in Settings after their exact bindings are observed.','Привязка туннеля роутера неизвестна или неоднозначна. Сохраните активный основной и резервный профили в настройках после наблюдения точных привязок.'],
  'VENDOR-SAME-TUNNEL':['Both profiles belong to one router tunnel. Server selection inside it belongs to the router firmware; this app does not switch that pair.','Оба профиля относятся к одному туннелю роутера. Выбор серверов внутри него относится к штатной прошивке; приложение не переключает такую пару.'],
  'RESERVE-NOT-CONNECTED':['The reserve channel is enabled but not connected. Auto tries to start it by itself (at most every two minutes); the primary keeps working meanwhile. If it stays down, check or replace the reserve server.','Резервный канал включён, но не подключён. Auto сам пытается его запустить (не чаще раза в две минуты); основной канал пока работает. Если резерв не поднимается, проверьте или замените сервер резерва.'],
  'PROFILE-IDENTITY-CHANGED':['The configured profile or tunnel binding changed. Old checks no longer describe the current member; wait for fresh observations and repeat validation.','Профиль или привязка туннеля изменились. Старые проверки больше не описывают текущий сервер; дождитесь свежих наблюдений и повторите проверку.'],
  'VENDOR-SETTLING':['The configured tunnel identity observation window is still pending. This does not establish whether firmware retries have finished.','Окно наблюдения за конфигурацией туннеля ещё не завершено. Это не устанавливает, закончились ли повторные попытки прошивки.'],
  'CONTROL-REVISION-STALE':['Auto controls changed. Refresh the current state before starting again.','Состояние управления Auto изменилось. Обновите данные перед новым запуском.'],
  'START-STATE-UNVERIFIED':['Saved Auto state could not be verified. Stop Auto, review the settings, then try again.','Не удалось проверить сохранённое состояние Auto. Остановите Auto, проверьте настройки и повторите попытку.'],
  'STOP-SUPERSEDED-START':['Turning Auto off cancelled this pending start. Turn the Auto switch on again when ready.','Выключение Auto отменило ожидающий запуск. При необходимости снова включите переключатель Auto.'],
  'START-CONFIG-CHANGED':['Settings changed while checking. Review them and try Start again.','Настройки изменились во время проверки. Проверьте их и повторите запуск.'],
  "LAN-TRIAL-REQUIRED":["This selected client-confirmed mode requires its matching LAN trial. Prepared continuous router-probed mode does not use this certificate.", "Выбранному клиентскому режиму нужен соответствующий LAN-тест. Подготовленный непрерывный router-probed режим этот сертификат не использует."],
  "BOUNDED-DEADLINE-REQUIRED":["A bounded window is missing/expired for the selected trial. Verify actual recovery and time before a new authorized run.", "Для выбранного теста нет действующего ограниченного окна. До нового разрешённого запуска проверьте фактическое восстановление и время."],
  'SESSION-LOSS-NOT-ACCEPTED':['Confirm in Settings that a short reconnection of calls and sessions is acceptable.','Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим.'],
  'TRANSACTION-IN-PROGRESS':['An unfinished switch record is open on the router. If a switch is running, wait for it or turn Auto off with its switch; without a running switch, recovery is needed.','На роутере открыта запись незавершённого переключения. Если переключение выполняется, дождитесь его или выключите Auto переключателем; без выполняющегося переключения нужно восстановление.'],
  "TRIAL-ATTEMPT-LIMIT":["The trial attempt budget is exhausted. Preserve failures and respect the budget/cooldown; never reset a nonce or ledger to bypass it.", "Бюджет попыток теста исчерпан. Сохраните отказы и соблюдайте бюджет/паузу; не сбрасывайте nonce или журнал ради обхода."],
  'UNSUPPORTED-BOARD':['Native switching requires a verified GL-MT6000 or GL-MT3000 firmware profile. Choosing a model does not bypass these checks.','Нативное переключение требует проверенного профиля прошивки GL-MT6000 или GL-MT3000. Выбор модели не отменяет эти проверки.'],
  'UNSUPPORTED-FIRMWARE':['Switching is verified only for GL.iNet firmware 4.11.0.','Переключение проверено только для прошивки GL.iNet 4.11.0.'],
  'FIRMWARE-UNKNOWN':['The router model or firmware could not be read.','Не удалось определить модель или прошивку роутера.'],
  'VENDOR-CODE-CHANGED':['GL.iNet system scripts differ from the audited ones. Switching stays blocked.','Системные скрипты GL.iNet отличаются от проверенных. Переключение заблокировано.'],
  'VENDOR-CODE-UNVERIFIED':['GL.iNet system scripts could not be verified.','Не удалось проверить системные скрипты GL.iNet.'],
  'VENDOR-WORKER-BUSY':['The router is applying its own VPN change right now. Try again in a minute.','Роутер сейчас сам применяет изменение VPN. Повторите через минуту.'],
  'HARDWARE-ACCELERATOR-UNVERIFIED':['Hardware acceleration (HNAT) is not confirmed disabled. It must be off for the LAN check to be trustworthy.','Аппаратное ускорение (HNAT) не подтверждено как выключенное. Для достоверной проверки оно должно быть выключено.'],
  'SOFTWARE-ACCELERATOR-UNVERIFIED':['A software acceleration module is loaded and not confirmed disabled.','Загружен модуль программного ускорения, его отключение не подтверждено.'],
  'FLOW-OFFLOAD-ENABLED':['Firewall flow offloading is on. Turn it off in the router firewall settings.','Включён flow offloading в firewall. Выключите его в настройках firewall роутера.'],
  'IPV6-NOT-EXPLICITLY-DISABLED':['IPv6 must be explicitly turned off on the router (IPv6 leaks are not covered).','IPv6 на роутере должен быть явно выключен (утечки IPv6 не контролируются).'],
  'KILLSWITCH-NOT-ENABLED':['Kill Switch must be on for every active VPN rule.','Kill Switch должен быть включён для каждого активного VPN-правила.'],
  'DIRECT-WAN-FALLBACK':['The router is allowed to bypass the VPN. Disable the direct-internet fallback in GL.iNet VPN settings.','Роутеру разрешён выход мимо VPN. Отключите прямой выход в интернет в настройках VPN GL.iNet.'],
  'VPN-POLICY-DISABLED':['The global VPN policy is off in the router settings.','Глобальная VPN-политика выключена в настройках роутера.'],
  'TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED':['Two or more general (all-traffic) VPN rules are required.','Нужно два или больше общих VPN-правил (для всего трафика).'],
  'GENERIC-RULES-NOT-ADJACENT':['The general VPN rules must follow one another without special rules between them.','Общие VPN-правила должны идти подряд, без специальных правил между ними.'],
  'GENERIC-DUPLICATE-INTERFACE':['Two general rules use the same VPN interface.','Два общих правила используют один и тот же VPN-интерфейс.'],
  'SPECIAL-RULES-MUST-PRECEDE-GENERIC':['Special rules (by device or destination) must be placed before the general rules.','Специальные правила (по устройствам или назначениям) должны стоять до общих.'],
  'SOURCE-RESERVE-NOT-CONFIGURED':['Choose a primary and a different reserve profile in Settings.','Выберите в настройках основной и другой, резервный профиль.'],
  'PROFILE-INACTIVE':['The primary or the reserve tunnel is not connected. Connect both in GL.iNet VPN Dashboard.','Основной или резервный туннель не подключён. Подключите оба в VPN Dashboard GL.iNet.'],
  'PROFILES-NOT-GENERIC-RULES':['The chosen profiles are not general VPN rules in the router policy.','Выбранные профили не являются общими VPN-правилами в политике роутера.'],
  'SAME-INTERFACE':['Primary and reserve use the same interface.','Основной и резервный профили используют один интерфейс.'],
  "POLICY-ORDER-DIRECTION-UNVERIFIED":["Policy-order direction has not been established for this mode. The client-confirmed helper and prepared continuous workflow have different setup evidence.", "Направление политики для этого режима ещё не установлено. У клиентского помощника и подготовленного непрерывного режима разные данные настройки."],
  'LAN-LAYOUT-UNSUPPORTED':['The LAN is not on the standard br-lan bridge.','Локальная сеть не на стандартном мосту br-lan.'],
  'PROFILE-NOT-MONITORED':['Enable monitoring for both chosen profiles in Settings.','Включите наблюдение для обоих выбранных профилей в настройках.'],
  'NFT-GUARD-UNAVAILABLE':['The router firewall tool (nft) is unavailable.','Недоступен инструмент firewall роутера (nft).'],
  'POLICY-READ-FAILED':['The router VPN policy could not be read.','Не удалось прочитать VPN-политику роутера.'],
  'UPLINK-LINK-DOWN':['The internet cable/uplink is down; changing VPN would not help.','Нет связи с интернет-провайдером; смена VPN не поможет.'],
  "LEASE-INTEGRITY-FAILED":["The bounded lease record failed integrity checks. Preserve it and inspect recovery/storage; do not delete it or create another lease as a bypass.", "Запись ограниченного окна не прошла целостность. Сохраните её и проверьте восстановление/хранилище; не удаляйте и не создавайте другое окно как обход."],
  'LEASE-STORAGE-FAILED':['The test window could not be stored on the router.','Не удалось сохранить окно теста на роутере.'],
  'LEGACY-LEASE-RECOVERY':['An old transaction needs recovery; wait or turn Auto off with its switch.','Старая транзакция требует восстановления; подождите или выключите Auto переключателем.'],
  'JOURNAL-INTEGRITY-FAILED':['The transaction journal is damaged. Switching is blocked and LAN traffic may be held; see the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций повреждён. Переключение заблокировано, трафик LAN может удерживаться; см. аварийные шаги в router-test-kit/EMERGENCY.md.'],
  'HISTORY-001':['The history file is damaged or the router clock went backwards.','Файл истории повреждён или часы роутера пошли назад.'],
  'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':['The router VPN policy was changed by someone else during a switch; LAN traffic is held. Check the rule order and see router-test-kit/EMERGENCY.md.','Политику VPN роутера изменили во время переключения; трафик LAN удерживается. Проверьте порядок правил, см. router-test-kit/EMERGENCY.md.'],
  'ROLLBACK-UNVERIFIED-GUARD-RETAINED':['The rollback could not be verified; LAN traffic is held. See router-test-kit/EMERGENCY.md.','Откат не удалось подтвердить; трафик LAN удерживается. См. router-test-kit/EMERGENCY.md.'],
  "CLIENT-CONFIRMATION-TIMEOUT":["Required client confirmation did not arrive in time. Recovery was requested; verify whether the original route returned or reserve was retained.", "Нужное подтверждение клиента не пришло вовремя. Восстановление запрошено; проверьте, вернулся ли исходный маршрут или сохранён резерв."],
  'CLIENT-STOP':['Stopped by request.','Остановлено по запросу.'],
  'TARGET-HTTPS-DNS-FAILED':['The reserve did not pass the DNS/HTTPS check.','Резерв не прошёл проверку DNS/HTTPS.'],
  'LAN-BASELINE-NOT-SOURCE':['The LAN computer is not currently using the primary route.','Компьютер в LAN сейчас не использует основной маршрут.'],
  'RESERVE-EXIT-NOT-DISTINCT':['Primary and reserve have the same external IP; the switch could not be proven.','У основного и резервного одинаковый внешний IP; переключение невозможно доказать.'],
  'VENDOR-APPLY-FAILED':['The router failed to apply the change; it was rolled back.','Роутер не смог применить изменение; выполнен откат.'],
  'POLICY-CHANGED-DURING-APPLY':['The policy changed while switching; it was rolled back.','Политика изменилась во время переключения; выполнен откат.'],
  'NATIVE-SYSTEM-001':['Internal controller error. See the Service monitor.','Внутренняя ошибка контроллера. См. «Службу мониторинга».'],
  'TERMS-NOT-ACCEPTED':['The terms of use are not accepted yet. Open this page in LuCI and accept them on the first screen.','Условия использования ещё не приняты. Откройте эту страницу в LuCI и примите их на первом экране.'],
  'RETURN-NOT-APPLICABLE':['There is nothing to return from: Auto is not holding the reserve.','Возвращаться не откуда: Auto не удерживает резерв.'],
  'SOURCE-NOT-HEALTHY':['The primary does not pass its check right now, so the router stays on the reserve. Try again when the primary works.','Основной VPN сейчас не проходит проверку, роутер остаётся на резерве. Повторите, когда основной заработает.'],
  'JOURNAL-UNVERIFIED':['The transaction journal could not be verified. Use the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций не удалось проверить. Используйте аварийные шаги из router-test-kit/EMERGENCY.md.'],
  'EXTERNAL-POLICY-CHANGE':['The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.','Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.'],
  'EXTERNAL-POLICY-CHANGE-RELEASED':['The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.','Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.'],
  'ROLLBACK-UNVERIFIED':['The return to the previous route could not be verified. Traffic is allowed only through VPN tunnels; check the VPN rule order in GL.iNet.','Возврат на прежний маршрут не удалось подтвердить. Трафик разрешён только через VPN-туннели; проверьте порядок правил VPN в GL.iNet.'],
  'ENVIRONMENT-EVIDENCE-UNAVAILABLE':['The router has not yet reported what it is made of (model, firmware, installed tools). Monitoring starts by itself: wait a minute and reload the page.','Роутер ещё не сообщил, из чего он состоит (модель, прошивка, установленные программы). Мониторинг запускается сам: подождите минуту и обновите страницу.'],
  'MONITOR-EVIDENCE-STALE':['There is no fresh data from the monitor. Monitoring starts by itself; wait a minute and reload. If it stays, press Restore monitoring in Monitoring service (Settings → System and diagnostics; Console: System tab) or see Help → “The page is old, empty or says the monitor is not running”.','Нет свежих данных от мониторинга. Мониторинг запускается сам; подождите минуту и обновите страницу. Если не помогло, нажмите «Восстановить мониторинг» в «Служба мониторинга» («Настройки → Система и диагностика»; в «Пульте» — вкладка «Система») или см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает». Без мониторинга Auto использовать нельзя.'],
  'NATIVE-START-CERTIFICATION-REQUIRED':['Nothing blocks you here, but the router itself still checks everything again at the moment you turn Auto on (current device, time window, your computer’s confirmation, safe return).','Здесь ничто не мешает, но роутер всё равно перепроверит всё в момент включения Auto (текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат).'],
  'OPERATOR-RETURN':['Returned to the primary on your request.','Возврат на основной выполнен по вашему запросу.'],
  'PRIMARY-RECOVERED':['The primary recovered and Auto returned to it.','Основной восстановился, Auto вернулся на него.']
};
function autoBlockerText(code){
  var row=Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?AUTO_BLOCKERS[code]:null;
  var guide=typeof AUTO_REMEDIES!=='undefined'&&AUTO_REMEDIES[autoRemedyKey(code)];
  if(!row&&!/^[A-Z][A-Z0-9-]{1,95}$/.test(String(code)))return bi('Unrecognised controller code; see the Service monitor.','Неизвестный код контроллера; см. «Службу мониторинга».');
  var table=!row&&!guide&&typeof ERROR_ROWS!=='undefined'?ERROR_ROWS.filter(function(r){return r[0]===code;})[0]:null;
  return row?bi(row[0],row[1]):guide?bi(guide.title[0],guide.title[1]):table?bi(table[2],table[3]):bi('Code '+code+': see its row in Events and errors.','Код '+code+': описание в «События и ошибки».');
}
var AUTO_REMEDIES={
  'acceleration':{
    title:['Disable network acceleration','Отключите сетевое ускорение'],path:['GL.iNet → NETWORK → Network Acceleration','GL.iNet → Сеть → Сетевое ускорение (Network Acceleration)'],
    text:['Turn Enable off and click Apply. Selecting Auto, Hardware or Software mode does not disable acceleration. Return here and check readiness again; Auto VPN needs a separate Start. Older firmware calls this menu Hardware Acceleration.','Выключите переключатель Enable («Включить») и нажмите Apply («Применить»). Выбор режима Auto, Hardware или Software не отключает ускорение. Вернитесь сюда и обновите готовность; Auto VPN запускается отдельно. В старых прошивках пункт называется Hardware Acceleration.'],
    route:'/#/netnat',docs:'https://docs.gl-inet.com/router/en/4/interface_guide/network_acceleration/'},
  'offload':{
    title:['Disable firewall flow offloading','Отключите flow offloading в firewall'],path:['LuCI → Network → Firewall → General Settings → Routing/NAT Offloading','LuCI → Сеть → Межсетевой экран → Общие настройки → Routing/NAT Offloading'],
    text:['Clear Software flow offloading and Hardware flow offloading, then Save & Apply. Return here and check readiness again.','Снимите Software flow offloading и Hardware flow offloading, затем нажмите Save & Apply («Сохранить и применить»). Вернитесь сюда и обновите готовность.'],route:'/cgi-bin/luci/admin/network/firewall'},
  'pair':{
    title:['Review the current VPN pair','Проверьте текущую пару VPN'],path:['Settings → Channels: primary and reserve (Console: Channels → Change the channel pair)','Настройки → Каналы: основной и резерв (в «Пульте» — Каналы → Изменить пару каналов)'],
    text:['The selected channel was removed, rebound or is not supported by this controller. Review the actual tunnel bindings in GL.iNet → VPN → VPN Dashboard, then explicitly save a supported pair here. On the prepared MT3000 mode these are wgclient1 and ovpnclient1; a server catalogue entry is not a second tunnel.','Выбранный канал удалён, перепривязан или не поддерживается этим контроллером. Проверьте привязки в GL.iNet → VPN → VPN Dashboard, затем явно сохраните здесь поддерживаемую пару. Для подготовленного режима MT3000 это wgclient1 и ovpnclient1; запись каталога серверов не является вторым туннелем.'],route:'#settings'},
  'recovery':{
    title:['Router configuration differs from the saved session','Конфигурация роутера отличается от сохранённой сессии'],path:['Home → Auto switch (Console: the top strip)','Главная → переключатель Auto (в «Пульте» — верхняя полоса)'],
    text:['A protected router setting no longer matches the saved Auto session. Who or what changed it is not established: an edit in the stock panel and the stock router services can both change it. When you turn Auto on, it archives the old session and adopts the current settings by itself. If it refuses again within 15 minutes, the settings are still changing: wait and turn the Auto switch on once more.','Защищённая настройка роутера не совпадает с сохранённой сессией Auto. Кто или что её изменил, не установлено: её могут менять и правка в штатной панели, и штатные службы роутера. При включении Auto сам архивирует старую сессию и примет текущие настройки. Если в течение 15 минут отказ повторяется, настройки ещё меняются: подождите и включите переключатель Auto ещё раз.'],route:'#settings'},
  'unfinished':{
    title:['Unfinished switch needs recovery','Незавершённое переключение требует восстановления'],path:['Home → Events and reasons → this code (Console: Log tab)','Главная → События и причины → этот код (в «Пульте» — вкладка «Журнал»)'],
    text:['A previous switch or Auto session did not finish and is not running. Its journal and safety guard are kept; the traffic channel is not verified. Start and manual switching are refused until recovery completes, so repeated presses do not help. This is not a sign that you changed settings.','Предыдущее переключение или сессия Auto не завершились и не выполняются. Журнал и защита сохранены; канал трафика не подтверждён. Start и ручное переключение отклоняются до завершения восстановления, поэтому повторные нажатия не помогут. Это не признак того, что вы меняли настройки.'],route:'#events',label:['Open events','Открыть события']}
};
AUTO_REMEDIES.preparation={title:['Complete router preparation','Завершите подготовку роутера'],path:['Settings → System and diagnostics → Router readiness (Console: System tab)','Настройки → Система и диагностика → Готовность роутера (в «Пульте» — вкладка «Система»)'],text:['Open Router readiness: the row Router preparation (acceleration) says whether preparation is needed. Turning Auto on performs what can be repaired without a restart; a refusal names its code, press it for the exact step. A failed boot or runtime check remains separate from the hardware acceleration switch.','Откройте «Готовность роутера»: строка «Подготовка роутера (ускорение)» показывает, нужна ли подготовка. Включение Auto выполняет то, что можно исправить без перезагрузки; отказ называет свой код — нажмите его, чтобы увидеть точный шаг. Ошибки автозапуска и работающих модулей проверяются отдельно от переключателя аппаратного ускорения.'],route:'#readiness'};
AUTO_REMEDIES.stockboot={title:['Disable competing VPN startup','Отключите конкурирующий автозапуск VPN'],path:['LuCI → System → Startup → vpn-client','LuCI → Система → Автозагрузка → vpn-client'],text:['After stopping Auto and verifying completed recovery, use Disable for vpn-client in the startup list. Disable changes startup; Stop is a different action and disconnects the running service. Return here and check preparation again.','После остановки Auto и подтверждённого завершения восстановления нажмите Disable («Отключить») у vpn-client в списке автозапуска. Это отключает запуск при загрузке. Кнопка Stop («Остановить») выполняет другое действие и останавливает работающую службу. Вернитесь сюда и повторите проверку подготовки.'],route:'/cgi-bin/luci/admin/system/startup'};
function autoRemedyKey(code){
  if(code==='PREP-SOURCE-AUTOSTART')return 'sourceboot';
  if(code==='PREP-TARGET-AUTOSTART')return 'targetboot';
  if(code==='PREPARATION-RESTART-REQUIRED')return 'restart';
  if(/^PREPARATION-/.test(code||''))return 'preparation';
  if(code==='PREP-WGCLIENT1-AUTOSTART')return 'autostart-wgclient1';
  if(code==='PREP-OVPNCLIENT1-AUTOSTART')return 'autostart-ovpnclient1';
  if(code==='PREP-STOCK-VPN-BOOT')return 'stockboot';
  if(['HARDWARE-ACCELERATOR-UNVERIFIED','SOFTWARE-ACCELERATOR-UNVERIFIED','PREP-HNAT-CONFIG','PREP-SFE-BOOT','PREP-SFE-AUTOLOAD','PREP-SFE-RUNTIME'].indexOf(code)>=0)return 'acceleration';
  if(code==='FLOW-OFFLOAD-ENABLED')return 'offload';
  if(code==='PAIR-PREPARATION-REQUIRED'||/^PREP-/.test(code||''))return 'preparation';
  if(['SOURCE-RESERVE-NOT-CONFIGURED','VENDOR-IDENTITY-UNKNOWN','PROFILE-IDENTITY-CHANGED','RESERVE-NOT-CONNECTED','EXISTING-TUNNEL-BINDING-UNVERIFIED','PAIR-PROFILES-UNVERIFIED'].indexOf(code)>=0)return 'pair';
  if(/^PAIR-(RECOVERY-REQUIRED|STATE-UNVERIFIED)$/.test(code||'')||code==='JOURNAL-INTEGRITY-FAILED'||code==='SWITCH-RESULT-UNCONFIRMED')return 'unfinished';
  if(/^PAIR-EXTERNAL-/.test(code||''))return 'recovery';
  return null;
}
function autoRemedyHref(guide){
  if(guide.route==='/#/netnat'){
    var loc=typeof window!=='undefined'&&window.location;
    return loc&&loc.hostname?(loc.protocol==='https:'?'https:':'http:')+'//'+loc.hostname+guide.route:guide.docs;
  }
  return guide.route;
}
function renderAutoRemedy(code){
  var g=AUTO_REMEDIES[autoRemedyKey(code)];if(!g)return null;
  var nodes=[E('strong',{},bi(g.title[0],g.title[1])),E('p',{},bi(g.path[0],g.path[1])),E('p',{},bi(g.text[0],g.text[1])),E('a',{'href':autoRemedyHref(g),'class':'cbi-button','target':g.route.charAt(0)==='#'?null:'_blank','rel':'noopener noreferrer','click':function(event){if(g.route.charAt(0)==='#'&&typeof minimumNavigate==='function'&&minimumNavigate){event.preventDefault();minimumNavigate(g.route.slice(1));}}},bi((g.label||['Open settings'])[0],(g.label||[0,'Открыть настройки'])[1]))];
  if(g.docs)nodes.push(E('p',{},E('a',{'href':g.docs,'target':'_blank','rel':'noopener noreferrer'},bi('GL.iNet instructions','Инструкция GL.iNet'))));
  if(typeof renderPreparationButtons==='function'){var preparationButtons=renderPreparationButtons(code);if(preparationButtons)nodes.splice(1,0,preparationButtons);}
  if(autoRemedyKey(code)==='acceleration')nodes.push(E('p',{},bi('If it is already off but the check still fails, open Router readiness (Settings → System and diagnostics; Console: System tab) and the code of the refusal for the exact failed check. Saved configuration and loaded runtime acceleration are checked separately.','Если уже выключено, а ошибка остаётся, откройте «Готовность роутера» («Настройки → Система и диагностика»; в «Пульте» — вкладка «Система») и код отказа: там указан конкретный непрошедший пункт. Сохранённые настройки и фактически работающее ускорение проверяются отдельно.')));
  return E('div',{'class':'hv-chart-card hv-auto-remedy','data-auto-remedy':code},nodes);
}
AUTO_REMEDIES.restart={title:['Router restart required','Нужна перезагрузка роутера'],path:['LuCI → System → Reboot','LuCI → Система → Перезагрузка'],text:['The boot/acceleration setting is saved and verified. Restart this router deliberately, then wait for fresh preparation checks before a separate Auto Start. The preparation button never reboots the router itself.','Настройка автозапуска/ускорения сохранена и проверена. Отдельно перезагрузите этот роутер, дождитесь новых проверок подготовки и затем явно запустите Auto. Кнопка подготовки сама роутер не перезагружает.'],route:'/cgi-bin/luci/admin/system/reboot'};
AUTO_BLOCKERS['PREPARATION-RESTART-REQUIRED']=AUTO_REMEDIES.restart.title.slice();
AUTO_BLOCKERS['PREPARATION-RECOVERY-REQUIRED']=['A preparation change needs recovery','Изменение подготовки требует восстановления'];
var AUTO_LAN_ONLY=['LAN-TRIAL-REQUIRED','BOUNDED-DEADLINE-REQUIRED','SESSION-LOSS-NOT-ACCEPTED'];
var AUTO_SIGNAL_TABLE={
  working:{lamp:'green',enabled:true,working:true,text:['Auto works','Auto работает']},
  checking:{lamp:'yellow',enabled:true,working:false,text:['Auto is on · waiting or checking','Auto включён · ожидание или проверка']},
  pending:{lamp:'yellow',enabled:false,working:false,text:['Auto state is being confirmed','Состояние Auto подтверждается']},
  failure:{lamp:'red',enabled:true,working:false,text:['Auto is on · needs attention','Auto включён · требует внимания']},
  refused:{lamp:'red',enabled:false,working:false,text:['Auto needs attention','Auto требует внимания']},
  off:{lamp:'off',enabled:false,working:false,text:['Auto is off','Auto выключен']}
};
function autoPresentation(light){
  if(!light)return AUTO_SIGNAL_TABLE.pending;
  var enabled=light.enabled===true||light.enabled===undefined&&(light.running===true||light.hold===true||light.key==='ok'||light.key==='reserve');
  return AUTO_SIGNAL_TABLE[light.key==='off'?'off':light.key==='problem'?(enabled?'failure':'refused'):light.key==='ok'||light.key==='reserve'?(enabled?'working':'pending'):enabled?'checking':'pending'];
}
function autoEnabled(light){return autoPresentation(light).enabled;}
function autoStateText(light){var words=autoPresentation(light).text;return bi(words[0],words[1]);}
var AUTO_RPC_GRACE=90,UI_AUTO_LAST_ON=null,UI_RPC_LOST_SINCE=null,UI_DATA_LATE_SINCE=null,UI_TRANSIENT_SINCE=null,AUTO_TRANSIENT_GRACE=180;
var AUTO_TRANSIENT=['OBSERVATION-STALE','VENDOR-SETTLING','VENDOR-WORKER-BUSY','VENDOR-WORKER-QUIET-UNVERIFIED','PROFILE-IDENTITY-CHANGED','VENDOR-IDENTITY-UNKNOWN','KERNEL-POLICY-UNVERIFIED','STATUS-STALE','MONITOR-DATA-STALE'];
function autoLightModel(status,inventory,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{},intent=status.auto_control||{},state=ns.state;
  var blockers=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  var sessionRuns=intent.requested==='on'&&['RUNNING','HELD'].indexOf(intent.pair_phase)>=0&&!model.awaiting;
  var confirmedOn=intent.requested==='on'&&['RUNNING','HELD'].indexOf(intent.pair_phase)>=0||intent.pair_phase==='STOPPING'&&UI_AUTO_LAST_ON!==null||model.on||(status.rpc_error||status.error)&&UI_AUTO_LAST_ON!==null;
  function out(key,title,hint,code,running){var light={enabled:key!=='off'&&(confirmedOn||!intent.pair_phase&&running===true),running:running===true,key:key,
    icon:key==='off'?'○':key==='problem'?'!':key==='ok'?'✓':'⟳',title:title,hint:hint,code:code||null};
    light.lamp=autoSignal(light)==='off'?null:autoSignal(light);
    if(autoEnabled(light)&&typeof channelLampTone==='function'&&typeof manualConfirmedPath==='function')light.tunnels=['source','target'].map(function(role){var tone=channelLampTone(status,inventory,role,now,light);return {color:tone.color,carrier:tone.carrier};});
    return light;}
  if(!status.rpc_error&&!status.error){UI_RPC_LOST_SINCE=null;
    if(confirmedOn)UI_AUTO_LAST_ON=now;else UI_AUTO_LAST_ON=null;}
  else if(UI_RPC_LOST_SINCE===null)UI_RPC_LOST_SINCE=now;
  if(model.fresh)UI_DATA_LATE_SINCE=null;else if(UI_DATA_LATE_SINCE===null)UI_DATA_LATE_SINCE=now;
  var monitorLamp=typeof monitorLightModel==='function'?monitorLightModel(status,inventory,now,false):null;
  if(monitorLamp&&monitorLamp.lamp==='red'&&!model.fresh&&!status.rpc_error&&!status.error)return out('problem',bi('No connection to the router program','Нет связи с программой роутера'),bi('Monitoring cannot be read, so the page cannot see Auto. If the router is running, Auto keeps working on it by itself; after a power cut it comes back by itself.','Мониторинг не читается, поэтому страница не видит Auto. Если роутер работает, Auto продолжает работать на нём сам; после отключения питания он возвращается сам.'),monitorLamp.code||'STATUS-STALE');
  if(typeof uiBootResuming==='function'&&uiBootResuming(status,now))return out('switching',bi('Restoring after a router restart','Восстановление после перезапуска роутера'),bi('The router was restarted. Auto finishes the interrupted switch, waits for the VPN channels and turns itself back on. Nothing needs to be pressed; this usually takes 3–4 minutes after power-on.','Роутер перезапускался. Auto завершает прерванное переключение, ждёт VPN-каналы и включится сам. Нажимать ничего не нужно; обычно это 3–4 минуты после включения питания.'),'AUTO-RESUME-PENDING',false);
  var command=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null;
  var silent=!model.fresh&&Math.max(UI_RPC_LOST_SINCE===null?0:now-UI_RPC_LOST_SINCE,UI_DATA_LATE_SINCE===null?0:now-UI_DATA_LATE_SINCE)>AUTO_RPC_GRACE;
  if((command==='starting'||command==='stopping')&&!silent)return out('switching',command==='starting'?bi('Turning Auto on…','Включение Auto…'):bi('Turning Auto off…','Выключение Auto…'),bi('Waiting for the router to confirm the command.','Ждём подтверждения команды роутером.'));
  if(command==='unconfirmed')return out('unknown',bi('Auto command is not confirmed','Команда Auto не подтверждена'),bi('The router has not confirmed completion. Refreshing its state; Stop remains available.','Роутер не подтвердил завершение. Обновляем его состояние; Stop остаётся доступен.'),'AUTO-CONTROL-UNCONFIRMED');
  if(model.paused)return out('switching',bi('Auto paused for speed test','Auto на паузе для теста скорости'),bi('Background checks are paused. They resume before Auto; a manual Stop stays in force.','Фоновые проверки приостановлены. Они возобновятся перед Auto; ручной Stop сохраняет силу.'));
  var manual=typeof manualOperationModel==='function'?manualOperationModel(status,now):null,recovery=typeof uiRecoveryModel==='function'&&!(manual&&manual.busy&&!manual.uncertain)?uiRecoveryModel(status,now):null;
  if(recovery)return out('problem',recovery.code==='SWITCH-RESULT-UNCONFIRMED'?bi('Switch result not confirmed','Результат переключения не подтверждён'):bi('Recovery needed','Нужно восстановление'),uiRecoveryText(recovery),recovery.code);
  var lostFor=Math.max(UI_RPC_LOST_SINCE===null?0:now-UI_RPC_LOST_SINCE,UI_DATA_LATE_SINCE===null?0:now-UI_DATA_LATE_SINCE),turnedOn=confirmedOn;
  var onlyTransient=blockers.every(function(code){return AUTO_TRANSIENT.indexOf(code)>=0;});
  if(!model.fresh&&state==='BLOCKED'&&!onlyTransient)return out('problem',autoStateText({key:'problem',enabled:confirmedOn}),autoBlockerText(blockers[0]),blockers[0]);
  if(!model.fresh&&turnedOn&&onlyTransient&&lostFor<=AUTO_RPC_GRACE){var late=out('unknown',status.rpc_error||status.error?bi('No answer, retrying','Нет ответа, повтор'):bi('Updating data','Обновление данных'),bi('Auto stays on. Fresh data from the router has not arrived yet; this is not an error. Red is shown only if the router stays silent for 90 s.','Auto остаётся включённым. Свежие данные роутера ещё не пришли; это не ошибка. Красный будет, только если роутер молчит дольше 90 с.'),null,true);late.stale=true;return late;}
  if(!model.fresh&&intent.requested==='off'&&intent.pair_phase==='STOPPED'&&onlyTransient&&lostFor<=AUTO_RPC_GRACE)return out('off',bi('Auto is off · updating data','Auto выключен · обновление данных'),bi('Auto was off in the last router answer. Fresh data has not arrived yet; red is shown only if the router stays silent for 90 s.','В последнем ответе роутера Auto был выключен. Свежие данные ещё не пришли; красный будет, только если роутер молчит дольше 90 с.'));
  if(!model.fresh)return out(silent?'problem':'unknown',status.rpc_error||status.error?bi('No connection to the router program','Нет связи с программой роутера'):bi('Controller state is out of date','Состояние контроллера устарело'),status.rpc_error||status.error?bi('The page gets no answer from the router program.','Страница не получает ответ от программы роутера.'):bi('The router answers, but the Auto controller has not reported a current state. Check Monitoring service in Settings → System and diagnostics (Console: System tab) and make sure the monitor is running.','Роутер отвечает, но контроллер Auto не сообщил актуальное состояние. Проверьте «Служба мониторинга» в «Настройки → Система и диагностика» (в «Пульте» — вкладка «Система»): мониторинг должен работать.'));
  if(ns.proof_scope==='router-probed-ipv4'&&ns.mode==='continuous-pair'){
    var scopeHint='';
    if(model.awaiting)return out('switching',bi('Starting or stopping Auto','Запуск или остановка Auto'),scopeHint);
    if(model.transitioning&&typeof uiTransitionModel==='function'&&uiTransitionModel(status,now).state==='RECOVERING')return out('switching',bi('Recovery after an interrupted switch','Восстановление после прерванного переключения'),bi('The previous route is being restored; the channel is not verified yet.','Возвращается прежний маршрут; канал ещё не подтверждён.'),'TRANSACTION-IN-PROGRESS');
    if(manual&&manual.busy)return out(manual.uncertain?'unknown':'switching',manual.uncertain?bi('Manual request is not confirmed','Ручной запрос не подтверждён'):manual.direction==='resume'?bi('Resuming Auto','Возобновление Auto'):bi('Switching channel','Переключение канала'),manual.uncertain?bi('Waiting for the result from the router. Stop remains available.','Ждём результат от роутера. Stop остаётся доступен.'):bi('Waiting for the router to confirm the manual request.','Ждём подтверждения ручного запроса роутером.'),manual.uncertain?'MANUAL-REQUEST-UNCONFIRMED':null,sessionRuns&&!manual.uncertain&&manual.direction!=='resume');
    if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),scopeHint,null,sessionRuns);
    var route=channelPathSelection(status,now,ns.source,ns.target),active=(status.profiles||[]).filter(function(p){return p.id===route.selected;})[0],health=active&&profileHealth(active,now).state;
    if((model.on||sessionRuns)&&route.selected&&(health==='failed'||health==='inactive'))return out('problem',bi('The selected VPN channel has failed','Выбранный VPN-канал не работает'),bi('Auto is watching the route, but the selected channel has failed its connection check.','Auto следит за маршрутом, но выбранный канал не прошёл проверку соединения.'),active&&active.code);
    if((model.on||sessionRuns)&&['OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','ROLLED-BACK'].indexOf(state)>=0){
      if(!route.selected)return out('unknown',bi('Route check','Проверка маршрута'),bi('The router is confirming its VPN rules again. Auto keeps working.','Роутер заново подтверждает действующие правила VPN. Auto продолжает работать.'),route.code||'KERNEL-POLICY-UNVERIFIED',true);
      if(!active||health!=='healthy')return out('unknown',bi('Waiting for a current channel check','Ждём актуальную проверку канала'),bi('The selected route is verified, but current channel health has not been confirmed.','Выбранный маршрут проверен, но актуальная доступность канала не подтверждена.'),null,true);
      if(state==='DEGRADED-ON-RESERVE')return out('unknown',bi('Recovery is being confirmed','Восстановление подтверждается'),bi('The latest channel check passed after a controller failure. Waiting for Auto to confirm recovery.','Последняя проверка канала прошла после сбоя контроллера. Ждём подтверждения восстановления от Auto.'));
      if(route.selected===ns.target)return out('reserve',bi('Working on the reserve','Работаю на резерве'),scopeHint);
      return out('ok',bi('Two-channel Auto is on','Авторежим двух каналов включён'),scopeHint);
    }
    var failedCode=blockers.filter(function(code){return AUTO_TRANSIENT.indexOf(code)<0;})[0]||ns.busy_seconds&&ns.reason||blockers[0]||(intent.failure&&intent.failure.code&&intent.requested!=='on'?intent.failure.code:null);
    var waitingNow=sessionRuns&&blockers.length&&blockers.every(function(code){return AUTO_TRANSIENT.indexOf(code)>=0;});
    if(!waitingNow)UI_TRANSIENT_SINCE=null;
    if(waitingNow){if(UI_TRANSIENT_SINCE===null)UI_TRANSIENT_SINCE=now;var vendorWait=blockers.some(function(code){return code.indexOf('VENDOR-')===0;});
      var waited=out('unknown',vendorWait?bi('Auto is on, waiting for the router','Auto включён, ждёт прошивку'):bi('Updating data','Обновление данных'),autoBlockerText(failedCode||blockers[0]),failedCode||blockers[0],true);
      waited.stale=vendorWait||now-UI_TRANSIENT_SINCE>AUTO_TRANSIENT_GRACE;return waited;}
    if(model.off&&!intent.failure&&(!failedCode||onlyTransient)){
      var s0=(inventory&&inventory.settings)||{},down=(status.profiles||[]).some(function(p){return (p.id===s0.plan_source||p.id===s0.plan_target)&&p.interface&&(p.administrative_state==='disabled'||p.code==='VPN-001');});
      return out('off',bi('Auto is off','Auto выключен'),down?bi('Auto brings the tunnels up — press Start.','Туннели поднимает Auto — нажмите Start.'):scopeHint,down?'TUNNEL-DISCONNECTED':null);
    }
    if(!failedCode&&['BLOCKED','RELEASE-PENDING','STOPPED-ON-RESERVE','TRIAL-REQUIRED','DEGRADED-ON-RESERVE'].indexOf(state)<0)return out('unknown',autoStateText({key:'unknown',enabled:confirmedOn}),scopeHint);
    return out('problem',bi('Auto needs attention','Auto требует внимания'),failedCode?autoBlockerText(failedCode):scopeHint,failedCode);
  }
  if(ns.proof_scope==='router-hosted-ipv4')return out('problem',bi('Checked by the router itself','Проверку делает сам роутер'),bi('This trial checks IPv4 forwarding with a client inside the router. It does not certify traffic from a separate LAN computer.','Этот тест проверяет пересылку IPv4 клиентом внутри роутера. Трафик отдельного компьютера LAN им не подтверждён.'));
  if(model.awaiting)return out('switching',intent.requested==='off'?bi('Stopping Auto','Auto останавливается'):bi('Starting Auto','Auto запускается'),bi('Waiting for the router to confirm. The lamp changes when it does.','Ожидается подтверждение роутера. Лампа изменится, когда оно придёт.'));
  if(state==='RESTORING')return out('switching',bi('Returning to the previous route','Возврат на прежний маршрут'),bi('The router is putting the original route back and checking it.','Роутер возвращает исходный маршрут и проверяет его.'));
  if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),bi('The router is changing the route and waits for a LAN computer to confirm it. This takes up to 2 minutes.','Роутер меняет маршрут и ждёт подтверждения от компьютера в LAN. Это занимает до 2 минут.'));
  if(state==='OBSERVING'&&ns.certified===true)return out('ok',bi('Auto is on','Auto включён'),bi('Watching the primary. If it fails, the router switches to the reserve after a LAN computer confirms the new route.','Следит за основным. При его отказе роутер переключится на резерв после подтверждения нового маршрута компьютером в LAN.'));
  if(state==='COMMITTED')return out('reserve',bi('Working on the reserve','Работаю на резерве'),bi('The reserve route is selected. Primary health is shown separately; return depends on policy, fresh evidence and operator hold.','Выбран резервный маршрут. Исправность основного показана отдельно; возврат зависит от политики, свежих данных и ручного удержания.'));
  if(state==='DEGRADED-ON-RESERVE')return out('problem',bi('The reserve is failing too','Резерв тоже не работает'),bi('The selected reserve has problems. Check both VPNs; any return must satisfy the current mode, saved policy and fresh primary readiness.','На выбранном резерве есть проблемы. Проверьте оба VPN; возврат должен соответствовать текущему режиму, политике и свежей готовности основного.'));
  if(state==='STOPPED-ON-RESERVE')return out('problem',bi('Stopped, but still on the reserve','Остановлен, но роутер всё ещё на резерве'),bi('The original route is not restored. Press Switch here on the Primary card when the primary works.','Исходный маршрут не восстановлен. Нажмите «Переключить сюда» на карточке «Основной», когда основной заработает.'));
  if(state==='RELEASE-PENDING'||blockers.indexOf('GUARD-RELEASE-UNCONFIRMED')>=0)return out('problem',bi('Internet may be blocked: the return has not finished','Интернет может быть заблокирован: возврат не закончился'),bi('Recovery is still pending. See Help → “I have no internet” (emergency return); turning Auto off has not completed.','Восстановление ещё не завершено. См. «Помощь» → «У меня пропал интернет» (аварийный возврат); выключение Auto не завершено.'),'GUARD-RELEASE-UNCONFIRMED');
  if(state==='BLOCKED'&&intent.requested==='on'&&blockers.length===1&&blockers[0]==='VENDOR-WORKER-BUSY')return out('switching',bi('The router is busy; Auto will continue by itself','Роутер занят, Auto продолжит сам'),bi('A stock network worker or lock is busy. Auto continues after it clears.','Штатный сетевой обработчик или блокировка заняты. Auto продолжит работу после их завершения.'));
  if(state==='BLOCKED'&&intent.requested==='on')return out('problem',bi('Auto is blocked','Auto заблокирован'),blockers.length?autoBlockerText(blockers[0]):bi('The router reports a condition that blocks Auto. See the list below.','Роутер сообщает условие, блокирующее Auto. См. список ниже.'),blockers[0]);
  if(state==='TRIAL-REQUIRED')return out('problem',bi('A LAN trial is required','Нужен LAN-тест'),autoBlockerText('LAN-TRIAL-REQUIRED'),'LAN-TRIAL-REQUIRED');
  if(state==='EXPIRED')return out('off',bi('Auto is off: the test window ended','Auto выключен: окно теста закончилось'),autoBlockerText('BOUNDED-DEADLINE-REQUIRED'));
  if(state==='STOPPED'&&ns.original_restored===true)return out('off',bi('Auto is off','Auto выключен'),bi('Control is back with the router; the original route is verified.','Управление вернулось роутеру; исходный маршрут проверен.'));
  return out('off',bi('Auto is off','Auto выключен'),bi('Monitoring continues; nothing is switched while Auto is off.','Мониторинг продолжается; пока Auto выключен, ничего не переключается.'));
}
function autoWorking(light){return autoPresentation(light).working;}
function autoSignal(light){return autoPresentation(light).lamp;}
function autoRuns(light){return autoEnabled(light)&&autoSignal(light)!=='red';}
var autoRequestBusy=false,autoStopBusy=false,autoStartPending=false;
var autoCommandPending=null,autoCommandUnconfirmed=null,autoCommandSequence=0,autoObservedOperation=null,autoControlRefresh=function(){};
var AUTO_COUNTDOWN=null,AUTO_COUNTDOWN_TIMER=null,AUTO_COUNTDOWN_NODES=null,AUTO_DURATION_KEY='hv-auto-durations';
function autoClockTick(){return typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();}
function autoElapsedMs(value){return Math.max(0,Number.isFinite(value.tick)?autoClockTick()-value.tick:Date.now()-value.t0);}
function autoDurations(){try{var v=JSON.parse(window.localStorage.getItem(AUTO_DURATION_KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(error){return {};}}
function autoDurationEstimate(kind){
  var rows=(autoDurations()[kind]||[]).filter(function(n){return Number.isFinite(n)&&n>0&&n<600;}).sort(function(a,b){return a-b;});
  if(!rows.length)return kind==='stop'?10:30;
  var mid=Math.floor(rows.length/2),median=rows.length%2?rows[mid]:(rows[mid-1]+rows[mid])/2;
  return Math.max(3,Math.ceil(median));
}
function autoCommandOperation(status,now){
  var model=autoControlModel(status,now),intent=status.auto_control||{},phase=intent.pair_phase;
  var startBlockers=Array.isArray((status.native_failover||{}).blockers)?status.native_failover.blockers:[];
  var failedStart=model.fresh&&(status.native_failover||{}).state==='BLOCKED'&&!model.awaiting&&!model.on&&!model.transitioning&&!(startBlockers.length&&startBlockers.every(function(code){return AUTO_TRANSIENT.indexOf(code)>=0;}));
  if(autoCommandPending&&autoCommandPending.acknowledged&&model.fresh&&intent.requested_at>autoCommandPending.baseline){
    var terminal=['FAILED','STOPPED','HELD'].indexOf(phase)>=0||!autoCommandPending.stop&&failedStart;
    var done=autoCommandPending.stop?terminal:terminal||phase==='RUNNING'&&model.on&&!model.awaiting&&!model.transitioning;
    var legacyDone=!phase&&!model.awaiting&&!model.transitioning&&
      (autoCommandPending.stop?model.off:model.on||model.off||model.color==='error');
    if(done||legacyDone){autoCommandPending=null;autoCommandUnconfirmed=null;}
  }
  if(autoCommandPending&&Number.isFinite(autoCommandPending.t0)&&autoElapsedMs(autoCommandPending)>Math.max(120000,2000*autoDurationEstimate(autoCommandPending.stop?'stop':'start'))){
    autoCommandUnconfirmed=autoCommandPending;autoCommandUnconfirmed.observed=model.fresh&&autoCommandPending.acknowledged&&intent.requested_at>autoCommandPending.baseline;autoCommandUnconfirmed.baseline=Math.max(autoCommandUnconfirmed.baseline||0,intent.requested_at||0);autoCommandPending=null;autoStopBusy=false;autoRequestBusy=false;autoStartPending=false;
  }
  if(autoCommandUnconfirmed&&model.fresh&&(intent.requested_at>autoCommandUnconfirmed.baseline||autoCommandUnconfirmed.observed&&intent.requested_at===autoCommandUnconfirmed.baseline&&!model.awaiting&&!model.transitioning&&['FAILED','STOPPED','HELD','RUNNING'].indexOf(phase)>=0))autoCommandUnconfirmed=null;
  if(autoCommandPending)return autoCommandPending.stop?'stopping':'starting';
  if(autoCommandUnconfirmed)return 'unconfirmed';
  var observed=phase==='STARTING'&&!failedStart?'starting':phase==='STOPPING'?'stopping':null;
  if(observed){
    var observedKey=observed+':'+intent.requested_at;
    if(!autoObservedOperation||autoObservedOperation.key!==observedKey)autoObservedOperation={key:observedKey,t0:Date.now(),tick:autoClockTick()};
    if(autoElapsedMs(autoObservedOperation)>120000)return 'unconfirmed';
  }else autoObservedOperation=null;
  if(phase==='STARTING')return failedStart?null:'starting';
  if(phase==='STOPPING')return 'stopping';
  if(phase==='UNKNOWN')return 'unknown';
  if(model.awaiting)return intent.requested==='off'?'stopping':'starting';
  if(model.transitioning)return intent.requested==='off'?'stopping':['RUNNING','HELD'].indexOf(phase)>=0?null:'starting';
  return null;
}
var PROBE_APPLIED=null,PROBE_LOG_KEY='homensai-vpn-probe-log-open',PROBE_LOG_ROWS=null,PROBE_RPC='homensai-vpn',PROBE_LEVELS={1:[60,300],2:[30,120],3:[20,60],4:[15,45],5:[10,30]},PROBE_DRAFT=null,PROBE_BUSY=false,PROBE_LOG_OPEN=false;
function probeDecision(row){
  var level=bi('level ','уровень ')+row.level,cadence=bi('check every ','проверка раз в ')+row.interval+bi(' s, websites every ',' с, сайты раз в ')+row.measure_interval+bi(' s',' с');
  var role=row.role==='source'?bi('primary channel','основной канал'):row.role==='target'?bi('reserve channel','резервный канал'):bi('channel','канал');
  if(row.kind==='level')return [bi('Level ','Выбран уровень ')+row.level,cadence+'; '+(row.boost_enabled?bi('boost on','ускорение включено'):bi('boost off','ускорение выключено'))];
  if(row.kind==='boost-start')return [bi('Boost started','Ускорение включено'),role+bi(' failed a check; checks every ',' не прошёл проверку; проверка раз в ')+row.boost_interval+bi(' s for 10 min (',' с на 10 мин (')+level+')'];
  if(row.kind==='suspicion-start'||row.kind==='suspicion-end'){
    var ev=row.evidence||{},why={'rx-stall':bi('sends data but receives nothing','отправляет данные, но ничего не получает')+(ev.stalled_s!=null?bi(' for '+Math.round(ev.stalled_s)+' s',' '+Math.round(ev.stalled_s)+' с'):''),
      'wg-handshake-stale':bi('WireGuard handshake is older than 3 min while sending','рукопожатие WireGuard старше 3 мин при отправке данных'),
      'link-missing':bi('the tunnel interface disappeared','интерфейс туннеля пропал'),
      'cusum-loss':bi('heartbeat echoes keep getting lost','ответы пульса теряются снова и снова')}[row.reason]||String(row.reason||'');
    if(row.kind==='suspicion-start')return [bi('Suspicion: dense checks','Подозрение: частые проверки'),role+' '+why+bi('; full checks every ','; полные проверки раз в ')+row.dense_interval+bi(' s. A suspicion alone never switches.',' с. Одно подозрение никогда не переключает.')];
    var ended={'false-alarm':bi('Suspicion cleared: checks passed','Подозрение снято: проверки пройдены'),'failure-confirmed':bi('Suspicion confirmed by failed checks','Подозрение подтверждено неудачными проверками'),'switched':bi('Suspicion ended: Auto switched','Подозрение завершено: Auto переключил канал'),'expired':bi('Suspicion ended without confirmation','Подозрение завершено без подтверждения'),'cancelled':bi('Suspicion ended: Auto is not watching','Подозрение завершено: Auto не наблюдает')};
    return [ended[row.result]||row.result,role+'; '+(row.failures||0)+bi(' failed of ',' неудачных из ')+(row.checks||0)+bi(' checks in ',' проверок за ')+(row.duration||0)+bi(' s; back to ',' с; возврат на ')+level];
  }
  var results={'switched':bi('Boost ended: the channel was switched','Ускорение завершено: было переключение'),'failure-confirmed':bi('Boost ended: failure confirmed','Ускорение завершено: сбой подтверждён'),'false-alarm':bi('Boost ended: false alarm, the channel recovered','Ускорение завершено: ложная тревога, канал восстановился'),'disabled':bi('Boost turned off by the owner','Ускорение выключено владельцем')};
  return [results[row.result]||row.result,role+'; '+row.failures+bi(' failed checks in ',' неудачных проверок за ')+Math.round((row.duration||0)/60)+bi(' min; back to ',' мин; возврат на ')+level];
}
function statsModeModel(source,now){
  var s=(source&&source.stats_mode&&typeof source.stats_mode==='object')?source.stats_mode:null;
  if(s)return {diagnostic:s.mode==='diagnostic',until:Number(s.until)||0};
  var settings=(source&&source.settings)||{},until=Number(settings.stats_until)||0;
  return {diagnostic:settings.stats_mode==='diagnostic'&&until>now,until:until};
}
function collectionModel(status){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,m=statsModeModel(status||{},now);
  var sm=(status&&status.stats_mode)||{};
  return {diagnostic:m.diagnostic,until:m.until,storage:sm.storage||{},retention:sm.retention,capacity:sm.capacity,
    saveRetention:function(kind,value){return rpc.declare({object:PROBE_RPC,reject:true,method:'setup_stats',params:['mode','retention',kind==='time'?'days':'mb'],expect:{}})('retention',kind,value);},
    save:function(mode,hours){return mode==='work'?rpc.declare({object:PROBE_RPC,reject:true,method:'setup_stats',params:['mode'],expect:{}})('work')
      :rpc.declare({object:PROBE_RPC,reject:true,method:'setup_stats',params:['mode','hours'],expect:{}})('diagnostic',hours);},
    notify:function(text){ui.addNotification(null,E('p',{},text));}};
}
var TG_ITEMS=[
  ['servers','Connected servers and their state','Подключённые серверы и их состояние','One line per server: name, protocol, OK or error code, response time. (Period reports: hours up/down per server.)','По строке на сервер: имя, протокол, OK или код ошибки, время ответа. (В сводках: часы работы и простоя сервера.)'],
  ['events','State changes','Изменения состояния','How many times a server changed state in the period, with the last ones listed.','Сколько раз сервер менял состояние за период, последние перечислены.'],
  ['traffic','VPN traffic','Трафик VPN','Gigabytes through the VPN this month (period reports: WAN and VPN traffic).','Гигабайты через VPN в этом месяце (в сводках: трафик WAN и VPN).'],
  ['delta','Traffic since the last report','Трафик с прошлого отчёта','How much traffic passed since the last confirmed report.','Сколько трафика прошло с прошлого подтверждённого отчёта.'],
  ['controller','Auto controller state','Состояние контроллера Auto','One line: what the automatic switching is doing now.','Одна строка: что сейчас делает автопереключение.'],
  ['controller_events','Controller events','События контроллера','Attempts, trials and switches during the period, with codes.','Попытки, тесты и переключения за период, с кодами.'],
  ['controller_totals','Controller monthly totals','Итоги контроллера за месяц','Attempts, passed trials, commits and rollbacks this month.','Попытки, пройденные тесты, переключения и откаты за месяц.'],
  ['gaps','Monitoring gaps and notes','Пропуски наблюдений и пометки','How often monitoring missed a check, plus the standard reading notes.','Сколько раз мониторинг пропустил проверку и стандартные пометки.']];
var TG_PRESETS={minimum:['servers'],standard:['servers','events','traffic','controller'],maximum:TG_ITEMS.map(function(i){return i[0];}),brief:['brief']};
var RECOVERY_PRESETS={"fast_recovery":{"attempt_limit":3,"attempt_window":15,"cooldown":60,"failures":3,"min_dwell":60,"primary_stable":60,"primary_successes":3,"rescue_stable":10,"return_policy":"healthy_primary","successes":2},"hold_reserve":{"attempt_limit":3,"attempt_window":15,"cooldown":180,"failures":3,"min_dwell":180,"primary_stable":60,"primary_successes":3,"rescue_stable":10,"return_policy":"hold_reserve","successes":2},"stability":{"attempt_limit":3,"attempt_window":15,"cooldown":300,"failures":5,"min_dwell":300,"primary_stable":300,"primary_successes":5,"rescue_stable":20,"return_policy":"healthy_primary","successes":3}};
function faultCurrentBinding(status,inventory){
  status=status||{};inventory=inventory||{};
  var now=(typeof routerWall==='function'?routerWall():Date.now()/1000),native=(status||{}).native_failover||{},settings=(inventory||{}).settings||{};
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):null,target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):null;
  var model=typeof vendorDiagnosticsModel==='function'?vendorDiagnosticsModel(status,inventory,now):null,coord=model&&model.coordination;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&0<=now-status.time&&now-status.time<=90&&Number.isFinite(native.time)&&0<=now-native.time&&now-native.time<=30;
  var healthy=source&&target&&Number.isFinite(source.time)&&0<=now-source.time&&now-source.time<=90&&Number.isFinite(target.time)&&0<=now-target.time&&now-target.time<=90&&source.code===null&&target.code===null&&source.dns_ok===true&&target.dns_ok===true&&Number.isInteger(source.https_success)&&source.https_success>=2&&Number.isInteger(target.https_success)&&target.https_success>=2;
  var ready=!!(fresh&&native.state==='OBSERVING'&&native.certified===true&&settings.native_session_loss===true&&source&&target&&healthy&&native.source===source.id&&native.target===target.id&&typeof native.vendor_identity==='string'&&/^[0-9a-f]{64}$/.test(native.vendor_identity)&&native.source_generation===source.vendor_generation&&native.target_generation===target.vendor_generation&&coord&&coord.known&&coord.state==='READY'&&coord.code==='CROSS-TUNNEL-READY'&&coord.source===source.vendor_tunnel_id&&coord.target===target.vendor_tunnel_id);
  var pairMode=settings.pair_auto_mode==='router-probed-ipv4';
  if(pairMode){
    var running=(status.auto_control||{}).pair_phase==='RUNNING';
    var path=typeof channelPathSelection==='function'?channelPathSelection(status,now,source&&source.id,target&&target.id):null;
    var selected=path&&path.selected&&source&&path.selected===source.id?'source':path&&path.selected&&target&&path.selected===target.id?'target':null;
    ready=!!(fresh&&running&&selected&&healthy&&settings.native_session_loss===true&&native.mode==='continuous-pair'&&native.proof_scope==='router-probed-ipv4'&&source&&target&&native.source===source.id&&native.target===target.id&&coord&&coord.known&&coord.state==='READY'&&coord.code==='CROSS-TUNNEL-READY');
    if(selected==='target'){var original=source;source=target;target=original;}
  }
  return {ready:ready,source:source,target:target,pairMode:pairMode,certificate:pairMode&&source&&target?source.vendor_generation+target.vendor_generation:native.vendor_identity||null};
}
function faultBlockers(status,inventory,source){
  var native=status.native_failover||{},settings=(inventory||{}).settings||{},profiles=status.profiles||[],now=(typeof routerWall==='function'?routerWall():Date.now()/1000);
  var reasons=[],hash=function(tab,label){return E('a',{'class':'cbi-button','href':'#'+tab},label);};
  var target=faultCurrentBinding(status,inventory).target;
  if(!settings.plan_source||!settings.plan_target||!source)reasons.push({en:'No primary and reserve VPN are chosen.',ru:'Не выбраны основной и резервный VPN.',link:hash('settings',bi('Go to Settings → Channels: primary and reserve','Перейти в «Настройки → Каналы: основной и резерв»'))});
  if(status.rpc_error||!(0<=now-status.time&&now-status.time<=90))reasons.push({en:'The router sends no fresh data, so the monitor may not be running.',ru:'Роутер не присылает свежих данных, возможно, мониторинг не работает.',link:hash('settings',bi('Check Monitoring service in Settings → System and diagnostics','Проверить «Служба мониторинга» в «Настройки → Система и диагностика»'))});
  var current=faultCurrentBinding(status,inventory);
  if(!current.ready&&!current.pairMode)reasons.push({en:'The current tunnel identity, fresh coordination and a certificate for exactly these current profiles must agree. The router independently rechecks the private certificate.',ru:'Текущая идентичность туннеля, свежая координация и сертификат именно этих текущих профилей должны совпадать. Роутер независимо перепроверяет закрытый сертификат.',link:hash('channels',bi('Review current tunnel observations','Проверить текущие наблюдения туннелей'))});
  if(settings.native_session_loss===false||settings.native_session_loss==='0')reasons.push({en:'You have not allowed a short reconnection of calls and sessions (Settings → How fast to switch → Allow a brief drop of calls and downloads).',ru:'Вы не разрешили короткое переподключение звонков и сессий («Настройки → Как быстро переключать» → «Разрешить короткий обрыв звонков и загрузок»).',link:hash('settings',bi('Go to Settings → How fast to switch and tick Allow a brief drop of calls and downloads','Перейти в «Настройки → Как быстро переключать» и включить «Разрешить короткий обрыв звонков и загрузок»'))});
  if(target&&profileHealth(target,now).state!=='healthy')reasons.push({en:'The reserve VPN does not work now; the test needs a healthy reserve.',ru:'Резервный VPN сейчас не работает; для теста нужен исправный резерв.',link:hash('home',bi('Check the Reserve card on Home','Проверить карточку «Резерв» на «Главной»'))});
  var running=['OBSERVING','COMMITTED'].indexOf(native.state)>=0;
  if(!running)reasons.push({en:'Auto is not on. The test requires a confirmed current channel and running Auto.',ru:'Auto не включён. Для теста нужен подтверждённый текущий канал и работающий Auto.',link:hash('home',bi('Turn Auto on with the Auto switch on Home','Включить Auto переключателем на «Главной»'))});
  else if(!current.pairMode&&native.certified!==true)reasons.push({en:'This fault trial requires an independent client-confirmed certificate. Router-probed Auto may already be running; this is a separate permission for deliberate interruption.',ru:'Для этого теста сбоя нужен отдельный сертификат с подтверждением LAN-клиента. Router-probed Auto при этом может уже работать; это отдельное разрешение на преднамеренное прерывание.',link:[hash('settings',bi('Go to Settings → LAN trial','Перейти в «Настройки» → LAN-тест')),' ',helpLink('helper-what',bi('Help: how to run the LAN helper','Помощь: как запустить LAN-помощник'))]});
  else if(!(0<=now-native.time&&now-native.time<=30))reasons.push({en:'The controller status is old.',ru:'Статус контроллера устарел.',link:hash('home',bi('Check the Auto status line on Home','Посмотреть строку состояния Auto на «Главной»'))});
  if(current.pairMode&&!current.ready&&!reasons.length)reasons.push({en:'The current pair is not ready yet. Press Check now and check both channel cards on Home (Console: Channels tab).',ru:'Текущая пара ещё не готова. Нажмите «Проверить сейчас» и проверьте обе карточки каналов на «Главной» (в «Пульте» — вкладка «Каналы»).',link:hash('home',bi('Home','Главная'))});
  if(!reasons.length)reasons.push({en:'The router refused to start the test.',ru:'Роутер отказался запускать тест.',link:errorCodeLink('FAULT-CERTIFIED-AUTO-REQUIRED')});
  return reasons;
}
function loadInventory(attempt){
  return inventoryCall().then(function(data){
    if(!data||typeof data!=='object'||!Array.isArray(data.profiles)||!Array.isArray(data.servers)||!data.settings||typeof data.settings.enabled!=='boolean')throw new Error('RPC-INVENTORY-INVALID');
    return data;
  }).catch(function(){
    if(attempt<2)return new Promise(function(resolve){setTimeout(resolve,250*(attempt+1));}).then(function(){return loadInventory(attempt+1);});
    return {profiles:[],servers:[],settings:{},error:'RPC-INVENTORY-UNAVAILABLE'};
  });
}
var UI_DISPLAY_GRACE=25;
function observationValidFor(row){var n=row&&row.observation_valid_for;return (Number.isFinite(n)&&n>=30&&n<=900?n:90)+UI_DISPLAY_GRACE;}
function observationFresh(row,now){return !!row&&Number.isFinite(row.time)&&Number.isFinite(now)&&now-row.time>=-5&&now-row.time<=observationValidFor(row);}
var UI_STATUS_REQUEST_SEQUENCE=0,UI_STATUS_ORDER=new WeakMap();
var UI_HISTORY=null,UI_HISTORY_AT=0,UI_HISTORY_BUSY=false;
function uiHistoryDue(){
  var page=typeof activeTab==='string'?activeTab:'';
  var every=['statistics','events','services','tests','analytics','switches','collection'].indexOf(page)>=0?60000:300000;
  return !UI_HISTORY_BUSY&&Date.now()-UI_HISTORY_AT>=every;
}
function uiHistoryRefresh(){
  if(!uiHistoryDue()||typeof rpc==='undefined'||!rpc.declare)return;
  UI_HISTORY_BUSY=true;
  Promise.resolve().then(function(){return rpc.declare({object:'homensai-vpn',method:'history',expect:{}})();})
    .then(function(h){if(h&&typeof h==='object'&&!h.error){var first=!UI_HISTORY;UI_HISTORY=h;UI_HISTORY_AT=Date.now();if(first&&typeof UI_STATUS_REFRESH==='function')UI_STATUS_REFRESH();}})
    .catch(function(){UI_HISTORY_AT=Date.now()-240000;}).finally(function(){UI_HISTORY_BUSY=false;});
}
function uiMergeHistory(status){
  if(!status||typeof status!=='object'||!Array.isArray(status.history_split)||!UI_HISTORY)return status;
  status.history_split.forEach(function(path){
    var value=UI_HISTORY[path];if(value===undefined)return;
    var keys=path.split('.'),node=status;
    if(keys.some(function(k){return k==='__proto__'||k==='constructor'||k==='prototype';}))return;  // semgrep 01.11.2026: no prototype writes
    for(var i=0;i<keys.length-1;i++){if(!node[keys[i]]||typeof node[keys[i]]!=='object')return;node=node[keys[i]];}
    node[keys[keys.length-1]]=value;
  });
  return status;
}
function uiStatusRequest(call){
  uiHistoryRefresh();
  var order=++UI_STATUS_REQUEST_SEQUENCE,tick=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now()/1000:Date.now()/1000;
  var promise=Promise.resolve().then(call).then(function(status){if(status&&typeof status==='object'){uiMergeHistory(status);UI_STATUS_ORDER.set(status,order);if(Number.isFinite(status.server_time))UI_STATUS_CLOCKS.set(status,{server:status.server_time,tick:tick});}return status;});
  UI_STATUS_ORDER.set(promise,order);return promise;
}
function uiStatusOrder(value){return value&&typeof value==='object'?UI_STATUS_ORDER.get(value)||0:0;}
function uiStatusFailure(current,order){
  var failed=Object.assign({},current,{rpc_error:'RPC-UNAVAILABLE',server_time:typeof routerWall==='function'?routerWall():Date.now()/1000});
  UI_STATUS_ORDER.set(failed,order);return failed;
}
function uiNewestStatus(current,next){
  if(!current||current===next||!next)return next||current;
  var before=uiStatusOrder(current),after=uiStatusOrder(next);
  return before&&(!after||after<before)?current:next;
}
var UI_OPERATION_REFRESH=function(){},UI_STATUS_REFRESH=function(){};
var UI_STATUS_CLOCKS=new WeakMap();
var UI_CLOCK_SKEW=0;
function routerWall(){return Date.now()/1000+UI_CLOCK_SKEW;}
function statusNow(status){
  var wall=Date.now()/1000;
  if(!status||typeof status!=='object'||!Number.isFinite(status.server_time)||status.server_time<=0||status.server_time>253370764799)return wall;
  var tick=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now()/1000:wall;
  var saved=UI_STATUS_CLOCKS.get(status);
  if(!saved){saved={server:status.server_time,tick:tick};UI_STATUS_CLOCKS.set(status,saved);}
  var value=saved.server+Math.max(0,tick-saved.tick);UI_CLOCK_SKEW=value-wall;return value;
}
function websiteMs(value){return (Math.floor(value*10+.5)/10).toFixed(1);}
var WEBSITE_METRIC='websites-https-mean-ms-v1',WEBSITE_TARGET_SET='google-cloudflare-wikipedia-v1';
var WEBSITE_URLS={google:'https://www.google.com/generate_204',cloudflare:'https://www.cloudflare.com/cdn-cgi/trace',wikipedia:'https://www.wikipedia.org/'};
var UI_LAST_DELAY={};
function lastHistoryDelay(status,id){
  var h=(status||{}).website_response_history||{},side=Array.isArray(h.pair)?h.pair.indexOf(id):-1;
  if(side<0||!Array.isArray(h.rows))return null;
  for(var i=h.rows.length-1;i>=0;i--){var r=h.rows[i];if(Array.isArray(r)&&Number.isInteger(r[side+3])&&r[side+3]>0&&Number.isFinite(r[side+1]))return {rtt_ms:r[side+1]/(10*r[side+3]),time:r[0]+30,metric:h.metric};}
  return null;
}
function delayAge(seconds){seconds=Math.max(0,Math.round(seconds));return seconds<90?seconds+' '+bi('s ago','с назад'):seconds<5400?Math.round(seconds/60)+' '+bi('min ago','мин назад'):Math.round(seconds/3600)+' '+bi('h ago','ч назад');}
function pingReading(p,status,now){
  if(!p||typeof p!=='object')return null;
  var best=null;
  function take(x){if(x&&typeof x==='object'&&Number.isFinite(x.rtt_ms)&&x.rtt_ms>=0&&x.rtt_ms<=60000&&Number.isFinite(x.time)&&(!best||x.time>best.time))best={rtt_ms:x.rtt_ms,time:x.time,target:typeof x.target==='string'?x.target:null};}
  if(p.ping&&p.ping.metric==='icmp-rtt-ms'&&p.ping.state==='ok')take(p.ping);
  take(p.ping_last);
  if(!best)return null;
  var at=Number.isFinite(now)?now:(typeof statusNow==='function'&&status?statusNow(status):Date.now()/1000),age=Math.max(0,at-best.time);
  return {rtt_ms:best.rtt_ms,time:best.time,age:age,target:best.target,text:websiteMs(best.rtt_ms)+' '+bi('ms','мс')+' ('+delayAge(age)+')'};
}
function channelPingModel(p,status,now){
  if(status&&typeof status.response_metric==='string'&&status.response_metric.indexOf('icmp-')===0)return channelIcmpModel(p,status,now);
  return channelWebsiteModel(p,status,now);
}
function channelDelayModel(p,status,now){
  var ping=status&&typeof status.response_metric==='string'&&status.response_metric.indexOf('icmp-')===0;
  var model=channelPingModel(p,status,now),id=p&&p.id;
  if(!id)return model;
  if(ping){
    var r=pingReading(p,status,now);
    if(!r)return model;
    return {state:model.state==='ok'?'ok':'last',code:model.state==='ok'?null:model.code,rtt_ms:r.rtt_ms,successes:model.successes,kind:'ping',
      time:r.time,age:r.age,target:r.target||String(status.response_metric).slice(5),text:r.text};
  }
  if(model.state==='ok'&&Number.isFinite(model.rtt_ms)){UI_LAST_DELAY[id+'|websites']={rtt_ms:model.rtt_ms,time:now};return model;}
  if(model.state==='inactive')return model;
  var last=UI_LAST_DELAY[id+'|websites'];
  if(!last){var h=lastHistoryDelay(status,id);if(h&&h.metric===WEBSITE_METRIC)last=h;}
  if(!last)return model;
  return {state:'last',code:model.code,rtt_ms:last.rtt_ms,successes:model.successes,kind:model.kind,
    text:websiteMs(last.rtt_ms)+' '+bi('ms','мс')+' · '+bi('three sites','три сайта')+' · '+bi('last measured ','последний замер ')+delayAge(now-last.time)};
}
function channelIcmpModel(p,status,now){
  var x=p&&p.ping,target=String(status.response_metric).slice(5);
  function no(state,code){return {state:state,code:code,rtt_ms:null,successes:0,kind:'ping',text:bi('No fresh ping','Нет свежего пинга')};}
  if(!status||status.rpc_error||status.error)return no('unavailable','STATUS-REQUEST-FAILED');
  if(!observationFresh(status,now))return no('stale','MONITOR-DATA-STALE');
  if(!p||!p.interface||p.administrative_state==='disabled')return no('inactive','PING-UNAVAILABLE');
  if(!x||x.state==='checking')return no('checking','PING-PENDING');
  if(x.metric!=='icmp-rtt-ms'||x.target!==target||x.interface!==p.interface)return no('checking','PING-PENDING');
  if(!Number.isFinite(x.time)||!Number.isFinite(x.valid_for)||x.valid_for<=0||x.valid_for>465||now-x.time< -5||now-x.time>x.valid_for+(typeof UI_DISPLAY_GRACE==='number'?UI_DISPLAY_GRACE:0))return no('stale','PING-DATA-STALE');
  if(x.state!=='ok'||!Number.isFinite(x.rtt_ms))return no(x.state==='failed'?'failed':'unavailable',x.code||'PING-FAILED');
  return {state:'ok',code:null,rtt_ms:x.rtt_ms,successes:1,kind:'ping',text:websiteMs(x.rtt_ms)+' '+bi('ms','мс')+' · '+bi('ping ','пинг ')+target};
}
function channelWebsiteModel(p,status,now){
  var x=p&&p.website_response,n=x&&Number.isInteger(x.successes)&&x.successes>=0&&x.successes<=3?x.successes:0;
  function no(state,code){return {state:state,code:code,rtt_ms:null,successes:n,text:bi('No complete three-site check','Нет полной проверки трёх сайтов')+' · '+n+'/3'};}
  if(!status||status.rpc_error||status.error)return no('unavailable','STATUS-REQUEST-FAILED');
  if(!observationFresh(status,now))return no('stale','MONITOR-DATA-STALE');
  if(!p||!p.interface||p.administrative_state==='disabled')return no('inactive','WEBSITE-UNAVAILABLE');
  if(!x)return no('checking','WEBSITE-CHECK-PENDING');
  if(x.metric!==WEBSITE_METRIC||x.target_set!==WEBSITE_TARGET_SET||p.vendor_state!=='SETTLED'||typeof p.vendor_generation!=='string'||!/^[a-f0-9]{32}$/.test(p.vendor_generation)||x.generation!==p.vendor_generation||x.interface!==p.interface||typeof p.vendor_tunnel_id!=='string'||p.vendor_tunnel_id!==p.protocol+':'+p.interface||x.vendor_tunnel_id!==p.vendor_tunnel_id)return no('checking','WEBSITE-IDENTITY-CHANGED');
  if(x.state==='checking')return no('checking','WEBSITE-CHECK-PENDING');
  if(x.state==='inactive'||x.state==='unavailable')return no(x.state,'WEBSITE-UNAVAILABLE');
  if(!Number.isFinite(x.time)||!Number.isFinite(x.valid_for)||x.valid_for<=0||x.valid_for>465||now-x.time< -5||now-x.time>x.valid_for||x.state==='stale')return no('stale','WEBSITE-DATA-STALE');
  if(x.state!=='ok')return no(x.state==='partial'?'partial':'failed',x.state==='partial'?'WEBSITE-PARTIAL':'WEBSITE-RESPONSE-FAILED');
  var results=x.results,seen={},sum=0;
  if(x.successes!==3||x.attempted!==3||!Array.isArray(results)||results.length!==3)return no('unavailable','WEBSITE-UNAVAILABLE');
  if(!results.every(function(r){if(!r||!Object.prototype.hasOwnProperty.call(WEBSITE_URLS,r.id)||seen[r.id]||r.url!==WEBSITE_URLS[r.id]||r.state!=='ok'||r.code!=null||!Number.isFinite(r.elapsed_ms)||r.elapsed_ms<0||r.elapsed_ms>6000)return false;seen[r.id]=true;sum+=r.elapsed_ms;return true;})||!Number.isFinite(x.avg_ms)||x.avg_ms<0||x.avg_ms>6000||Math.abs(x.avg_ms-sum/3)>.051)return no('unavailable','WEBSITE-UNAVAILABLE');
  return {state:'ok',code:null,rtt_ms:x.avg_ms,successes:3,text:websiteMs(x.avg_ms)+' '+bi('ms','мс')};
}
function responseHistoryKind(h){return !h?null:h.metric===WEBSITE_METRIC&&h.target_set===WEBSITE_TARGET_SET?'websites':h.metric==='icmp-rtt-ms'&&h.target_set==='icmp-echo'?'ping':null;}
var UI_DATA_CAUSE=null;
function dataCause(status,now){
  if(!status||status.rpc_error)return {code:'STATUS-REQUEST-FAILED',text:bi('the page got no answer from the router program','страница не получила ответ от программы на роутере')};
  if(!observationFresh(status,now))return {code:'MONITOR-DATA-STALE',text:bi('the router has not sent fresh data'+(Number.isFinite(status.time)?' for '+Math.round(now-status.time)+' s':''),'роутер не присылает свежие данные'+(Number.isFinite(status.time)?' уже '+Math.round(now-status.time)+' с':''))};
  return {code:'VENDOR-OBSERVATION-PENDING',text:bi('the monitor has not finished observing this channel yet (up to a minute after a start or change)','мониторинг ещё не закончил наблюдение этого канала (до минуты после запуска или изменения)')};
}
function profileHealth(profile,now){
  if(!profile.interface||profile.administrative_state==='disabled')return {state:'inactive',label:bi('Inactive','Неактивен')};
  if(!observationFresh(profile,now))return {state:'unknown',label:bi('Check data unavailable','Нет данных проверки')};
  if(['CHECK-001','CHECK-LIMIT'].indexOf(profile.code)>=0)return {state:'checking',label:bi('Checking','Проверяется')};
  if(profile.code)return {state:'failed',label:bi('Failed','Сбой')};
  if(profile.dns_ok===true&&profile.https_success>=2)return {state:'healthy',label:bi('Healthy','Работает')};
  return {state:'checking',label:bi('Checking','Проверяется')};
}
var UI_TRANSITION_STATES=['ARMED','APPLYING','WAIT-CLIENT','RESTORING'],UI_TRANSITION_GRACE=15;
function uiTransitionModel(status,now){
  status=status||{};var ns=status.native_failover||{};
  if(UI_TRANSITION_STATES.indexOf(ns.state)<0||Array.isArray(ns.blockers)&&ns.blockers.length||status.rpc_error||status.error||!observationFresh(status,now)||!Number.isFinite(ns.time)||now-ns.time< -5)return {live:false,overdue:false,state:null};
  var started=Number.isFinite(ns.started)&&ns.started<=ns.time+5&&ns.time-ns.started<=125?ns.started:null;
  var deadline=Number.isFinite(ns.deadline)&&ns.deadline>=ns.time-125&&ns.deadline<=(started||ns.time)+125?ns.deadline:(started||ns.time)+120;
  var phase=now<=deadline?'running':now<=deadline+UI_TRANSITION_GRACE?'checking':'overdue';
  var state=ns.state==='RESTORING'&&(ns.restore_proof_source==='vendor-rebuild'||ns.reason==='SUPERVISOR-RECOVERY')?'RECOVERING':ns.state;
  return {live:phase!=='overdue',overdue:phase==='overdue',phase:phase,state:state,started:started,deadline:deadline};
}
var UI_RECOVERY_CODES=['PAIR-RECOVERY-REQUIRED','PAIR-STATE-UNVERIFIED','JOURNAL-INTEGRITY-FAILED'];
function uiBootResuming(status,now){
  var b=(status||{}).boot_resume,intent=(status||{}).auto_control||{};
  return !!b&&typeof b==='object'&&b.state==='WAITING'&&Number.isFinite(b.time)&&now-b.time>=-5&&now-b.time<=120&&intent.requested!=='on';
}
function uiRecoveryModel(status,now){
  status=status||{};if(status.rpc_error||status.error||!observationFresh(status,now))return null;
  if(uiBootResuming(status,now))return null;
  var ns=status.native_failover||{},intent=status.auto_control||{},t=uiTransitionModel(status,now);
  if(t.overdue)return {code:'SWITCH-RESULT-UNCONFIRMED',stage:t.state,deadline:t.deadline};
  if(t.live)return null;
  var blockers=Array.isArray(ns.blockers)?ns.blockers:[],failure=intent.failure&&intent.failure.code;
  var code=blockers.filter(function(c){return UI_RECOVERY_CODES.indexOf(c)>=0;})[0]||(UI_RECOVERY_CODES.indexOf(failure)>=0&&intent.requested!=='on'?failure:null);
  return code?{code:code,stage:null,deadline:null}:null;
}
function uiRecoveryText(recovery){
  if(!recovery)return '';
  if(recovery.code==='SWITCH-RESULT-UNCONFIRMED')return bi('The router did not report the end of the switch by its deadline. The channel is not verified; do not repeat the switch. Stop remains available.','Роутер не сообщил о завершении переключения к предельному сроку. Канал не подтверждён; не повторяйте переключение. Stop остаётся доступен.');
  var text=typeof AUTO_REMEDIES!=='undefined'&&AUTO_REMEDIES.unfinished?AUTO_REMEDIES.unfinished.text:['A previous switch did not finish; recovery is needed.','Предыдущее переключение не завершилось; нужно восстановление.'];return bi(text[0],text[1]);
}
var UI_STAGE_TEXT={ARMED:['Preparing','Подготовка'],APPLYING:['Applying router rules','Применение правил роутера'],'WAIT-CLIENT':['Checking the new route','Проверка нового маршрута'],RESTORING:['Restoring the previous route','Возврат прежнего маршрута'],RECOVERING:['Recovery after an interrupted switch','Восстановление после прерванного переключения'],QUEUED:['Waiting for the controller','Ожидание контроллера'],CLAIMED:['Accepted by the controller','Принято контроллером'],SENT:['Sending the request','Отправка запроса']};
function uiClock(seconds){seconds=Math.max(0,Math.floor(seconds));return Math.floor(seconds/60)+':'+('0'+seconds%60).slice(-2);}
var UI_SWITCH_AVG=null,UI_SWITCH_MEASURED=56;
var UI_INSTANT_EXPECTED=4;
function uiOperationTimer(stage,elapsed,remaining,checking,instant){
  var text=stage&&UI_STAGE_TEXT[stage]?bi(UI_STAGE_TEXT[stage][0],UI_STAGE_TEXT[stage][1]):'';
  if(Number.isFinite(elapsed))text+=(text?' · ':'')+uiClock(elapsed)+bi(' elapsed',' прошло');
  if(Number.isFinite(elapsed)&&!checking){
    var expected=instant?UI_INSTANT_EXPECTED:Math.round((Number.isFinite(UI_SWITCH_AVG)?UI_SWITCH_AVG:UI_SWITCH_MEASURED)*1.25),left=expected-elapsed;
    text+=(text?' · ':'')+(left>=1?bi('about ','ещё около ')+uiClock(left)+bi(' (expected ',' (ожидается ')+uiClock(expected)+')':bi('longer than expected (','дольше ожидаемого (')+uiClock(expected)+')');
    if(left<1&&Number.isFinite(remaining))text+=' · '+bi('limit in ','предел через ')+uiClock(remaining);
    return text;
  }
  if(checking)text+=(text?' · ':'')+bi('checking the result','проверяем результат');
  else if(Number.isFinite(remaining))text+=(text?' · ':'')+bi('limit in ','предел через ')+uiClock(remaining);
  return text;
}
function channelAliveText(direction,status,now){var m=status&&typeof manualControlModel==='function'?manualControlModel(status,now):null;return m&&m[direction]&&m[direction].allowed?bi('Live, you can switch to it manually','Живой, можно переключиться на него вручную'):bi('Live; manual switching is unavailable now','Живой; ручное переключение сейчас недоступно');}
function statusServedAt(status,now){var t=status&&status.server_time;return Number.isFinite(t)&&t>0&&t<=now+5?Math.min(t,now):now;}
function channelPathSelection(status,now,sourceId,targetId){
  status=status||{};var native=status.native_failover||{},path=status.channel_path;
  var required=native.mode==='continuous-pair'||native.proof_scope==='router-probed-ipv4'||!!(path&&(path.mode==='continuous-pair'||path.selection_proof==='fw3-kernel-marking')),authoritative=required||Object.prototype.hasOwnProperty.call(status,'channel_path');
  var result={authoritative:authoritative,selected:null,moving:false,code:authoritative?'KERNEL-POLICY-UNVERIFIED':null};
  if(!authoritative)return result;
  if(status.rpc_error||status.error){result.code='STATUS-REQUEST-FAILED';return result;}
  if(!observationFresh(status,now)){result.code='MONITOR-DATA-STALE';return result;}
  if(!path||typeof path!=='object'||Array.isArray(path))return result;
  if(required&&path.transitioning===true&&uiTransitionModel(status,now).live&&(!sourceId||!path.source_profile_id||path.source_profile_id===sourceId)&&(!targetId||!path.target_profile_id||path.target_profile_id===targetId)){result.moving=true;result.code=null;return result;}
  if(required&&(path.mode!=='continuous-pair'||path.selection_proof!=='fw3-kernel-marking'||!Number.isFinite(path.valid_for)||path.valid_for<=0||path.valid_for>15||!Number.isFinite(path.checked_at)||path.time!==path.checked_at))return result;
  var maxAge=required?path.valid_for:30;
  var checkedAt=required?path.checked_at:path.time;
  var servedAt=statusServedAt(status,now);
  if(!Number.isFinite(checkedAt)||servedAt-checkedAt< -5||servedAt-checkedAt>maxAge){result.code=required?'KERNEL-POLICY-UNVERIFIED':'MONITOR-DATA-STALE';result.expired=Number.isFinite(checkedAt)&&servedAt-checkedAt>maxAge;return result;}
  var source=path.source_profile_id,target=path.target_profile_id;
  if(typeof source!=='string'||!source||typeof target!=='string'||!target||source===target||sourceId&&source!==sourceId||targetId&&target!==targetId){result.code='PAIR-POLICY-UNVERIFIED';return result;}
  result.moving=path.transitioning===true;
  if(result.moving){result.code=null;return result;}
  if(path.confirmed!==true||required&&path.kernel_policy_verified!==true)return result;
  if(path.active_profile_id!==source&&path.active_profile_id!==target){result.code='PAIR-POLICY-UNVERIFIED';return result;}
  result.selected=path.active_profile_id;result.code=null;return result;
}
function savedTransition(entry){
  entry=entry||{};
  var fields=['from_role','from_profile_id','destination_role','destination_profile_id','route_changed','transition_completed','transition_outcome','activation_reapply','before_policy_role'];
  var present=Object.prototype.hasOwnProperty.call(entry,'transition_metadata_present')||fields.some(function(key){return Object.prototype.hasOwnProperty.call(entry,key);});
  if(!present)return {present:false};
  function role(key,idKey){var value=entry[key],identifier=entry[idKey];return (value==='source'||value==='target')&&typeof identifier==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(identifier)&&entry.source!==entry.target&&identifier===entry[value]?value:null;}
  var from=role('from_role','from_profile_id'),to=role('destination_role','destination_profile_id'),changed=entry.route_changed===true,unchanged=entry.route_changed===false;
  var outcome=['committed','restored','refused','policy-verified'].indexOf(entry.transition_outcome)>=0?entry.transition_outcome:null;
  var invalid=changed&&from&&to&&from===to||unchanged&&from&&to&&from!==to&&outcome!=='refused';
  if(invalid){from=null;to=null;}
  return {present:true,from:from,to:to,changed:changed,unchanged:unchanged,completed:entry.transition_completed===true,outcome:outcome,reapply:entry.activation_reapply===true,invalid:!!invalid};
}
function channelLampPair(status,inventory){
  var path=status.channel_path||{},ns=status.native_failover||{},settings=(inventory||{}).settings||{},rows=status.profiles||[];
  var sourceId=settings.plan_source||path.source_profile_id||ns.source,targetId=settings.plan_target||path.target_profile_id||ns.target;
  return {source:rows.filter(function(p){return p.id===sourceId;})[0],target:rows.filter(function(p){return p.id===targetId;})[0]};
}
function channelLampTone(status,inventory,role,now,light){
  var pair=channelLampPair(status,inventory);
  if(status.rpc_error||status.error||!observationFresh(status,now))return {color:'grey',text:typeof dataCause==='function'?dataCause(status,now).text:bi('no router data','нет данных роутера'),carrier:false};
  light=light||(typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null);
  var confirmed=(typeof heldConfirmedPath==='function'?heldConfirmedPath:manualConfirmedPath)(status,pair.source,pair.target,now);
  return manualChannelTone(pair[role],role,confirmed,now,!light||(typeof autoRuns==='function'?autoRuns(light):autoWorking(light)),status);
}
function retainedTransitions(history){
  var events=(history.events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}),rows=[],open=null,last=null,lastTime=null;
  function close(outcome,event,reason){if(!open)return;open.outcome=outcome;open.close_reason=reason||null;open.terminal_state=event&&event.state||null;
    if(event&&Number.isFinite(event.time)&&event.time>=open.start){open.end=event.time;open.duration=open.applied_at==null?null:event.time-open.applied_at;}
    rows.push(open);open=null;
  }
  function identifier(value){return Number.isSafeInteger(value)&&value>0?value:null;}
  function begin(e){var transition=savedTransition(e);open={id:identifier(e.attempt_id)||e.sequence,retry_episode_id:identifier(e.retry_episode_id),
    prepared_at:e.state==='ARMED'?e.time:null,applied_at:e.state==='APPLYING'?e.time:null,start:e.time,end:null,duration:null,
    pair_source:e.source||'unknown',pair_target:e.target||'unknown',
    source:transition.present?(transition.from?e[transition.from]:'unknown'):e.source||'unknown',target:transition.present?(transition.to?e[transition.to]:'unknown'):e.target||'unknown',
    source_role:transition.present?transition.from:'source',target_role:transition.present?transition.to:'target',transition_metadata_present:transition.present,
    kind:['server','channel','protocol'].indexOf(e.transition_kind)>=0?e.transition_kind:'unknown',
    trial:e.trial===true,outcome:'pending',phases:[],codes:[],probe_evidence:{}};}
  events.forEach(function(e){
    if(!Number.isFinite(e.time)||e.time<0||e.time>253402300799||!Number.isSafeInteger(e.sequence)||e.sequence<1)return;
    if(last!==null&&e.sequence<=last)return;
    if(lastTime!==null&&e.time<lastTime){close('unknown',null,'clock-order');last=e.sequence;return;}
    lastTime=e.time;
    if(last!==null&&e.sequence!==last+1)close('unknown',null,'missing-events');
    last=e.sequence;
    var transition=savedTransition(e),refused=transition.present&&transition.completed&&transition.outcome==='refused';
    if(transition.present&&(!transition.changed||transition.unchanged||transition.reapply)&&!refused)return;
    var restoration=transition.present&&transition.completed&&transition.outcome==='restored';
    if(restoration&&(!open||identifier(e.attempt_id)&&e.attempt_id!==open.id||e.source&&e.source!==open.pair_source||e.target&&e.target!==open.pair_target)){
      close('unknown',null,'next-operation');begin(e);open.operation='restoration';open.applied_at=null;
    }
    var trialPassed=(e.codes||[]).indexOf('TRIAL-PASSED')>=0;
    var starting=e.state==='APPLYING'||e.state==='ARMED'&&!trialPassed;
    if(starting){
      var same=open&&open.applied_at==null&&(e.state==='APPLYING'||!identifier(e.attempt_id)||identifier(e.attempt_id)===open.id)&&
        (!e.attempt_id||e.attempt_id===open.id)&&(!e.source||e.source===open.pair_source)&&(!e.target||e.target===open.pair_target);
      if(!same){close('unknown',null,'next-attempt');begin(e);}
      else if(e.state==='APPLYING'){open.applied_at=e.time;open.start=e.time;if(['server','channel','protocol'].indexOf(e.transition_kind)>=0)open.kind=e.transition_kind;}
    }
    if(!open)return;
    if(e.trial===true)open.trial=true;
    if((identifier(e.attempt_id)&&e.attempt_id!==open.id)||(e.source&&e.source!==open.pair_source)||(e.target&&e.target!==open.pair_target)){close('unknown',null,'pair-changed');return;}
    open.phases.push({state:e.state,time:e.time});
    (e.codes||[]).forEach(function(code){if(typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)&&open.codes.indexOf(code)<0)open.codes.push(code);});
    var evidence=e.probe_evidence||{};
    ['source_streak_met','reserve_streak_met'].forEach(function(key){if(typeof evidence[key]==='boolean')open.probe_evidence[key]=evidence[key];});
    ['required_failures','required_successes'].forEach(function(key){if(Number.isInteger(evidence[key])&&evidence[key]>=2&&evidence[key]<=10)open.probe_evidence[key]=evidence[key];});
    if(Array.isArray(e.phase_evidence)){
      var phases=e.phase_evidence.filter(function(p){return p&&/^[A-Z0-9_-]{1,96}$/.test(p.phase)&&Number.isFinite(p.time)&&p.time<=e.time;});
      if(phases.length){open.phases=phases.map(function(p){return {state:p.phase,time:p.time};});if(open.phases[open.phases.length-1].state!==e.state)open.phases.push({state:e.state,time:e.time});}
    }
    if(transition.present&&transition.completed){
      if(transition.outcome==='committed'&&transition.to)close('committed',e);
      else if(transition.outcome==='restored'&&transition.to)close(open.operation==='restoration'?'restored':'rolled_back',e);
      else if(transition.outcome==='refused')close('refused',e);
      else close('unknown',e,'metadata-unverified');
    }
    else if(!transition.present&&e.state==='COMMITTED')close('committed',e);
    else if(!transition.present&&trialPassed)close('trial_passed',e);
    else if(!transition.present&&e.state==='ROLLED-BACK')close('rolled_back',e);
    else if(!transition.present&&['BLOCKED','STOPPED','STOPPED-ON-RESERVE','EXPIRED'].indexOf(e.state)>=0)close('held',e);
  });
  close('pending',null);
  return rows;
}
var P95_MIN_N=59;
function p95Honest(n){return n>=P95_MIN_N;}
function p95MaxCoverage(n){return n>0?Math.floor(Math.pow(0.05,1/n)*100+1e-9):0;}
function p95Text(value,n,fmt){
  if(value==null)return '—';
  var v=fmt?fmt(value):String(value);
  return p95Honest(n)?v:'≈'+v+' ('+bi('too few samples: n='+n+', needs ≥'+P95_MIN_N,'мало данных: n='+n+', нужно ≥'+P95_MIN_N)+')';
}
function p95MaxText(value,n,fmt){
  if(value==null||p95Honest(n))return fmt?fmt(value):String(value);
  return (fmt?fmt(value):String(value))+' (≥'+p95MaxCoverage(n)+' %)';
}
function p95MaxClaim(value,n,fmt){
  if(value==null||p95Honest(n))return '';
  return bi('max '+(fmt?fmt(value):value)+': with 95 % confidence ≥'+p95MaxCoverage(n)+' % of cases are no slower than the max','max '+(fmt?fmt(value):value)+': с 95 % уверенностью ≥'+p95MaxCoverage(n)+' % случаев не медленнее max');
}
function recoverySummary(rows,start,end){
  var selected=rows.filter(function(r){return r.start>=start&&r.start<end&&r.operation!=='restoration';}),durations=[],known=0,committed=0,trialsPassed=0;
  var streaks=Object.create(null),maxFailures=0;
  selected.slice().sort(function(a,b){return a.start-b.start;}).forEach(function(r){
    var outcome=r.end!=null&&r.end>=end?'pending':r.outcome;
    if(['committed','trial_passed','rolled_back','held'].indexOf(outcome)>=0)known++;
    if(outcome==='committed')committed++;
    if(outcome==='trial_passed')trialsPassed++;
    if(['committed','trial_passed','rolled_back'].indexOf(outcome)>=0&&Number.isFinite(r.duration)&&r.duration>=0)durations.push(r.duration);
    streaks[r.target]=['rolled_back','held'].indexOf(outcome)>=0?(streaks[r.target]||0)+1:0;
    maxFailures=Math.max(maxFailures,streaks[r.target]);
  });
  durations.sort(function(a,b){return a-b;});
  var n=durations.length;
  return {attempts:selected.length,known_outcomes:known,unknown_or_pending:selected.length-known,
    trial_attempts:selected.filter(function(r){return r.trial===true;}).length,
    automatic_attempts:selected.filter(function(r){return r.trial!==true;}).length,
    committed:committed,trials_passed:trialsPassed,success_ratio:known?(committed+trialsPassed)/known:null,recovered_samples:n,
    median:n?(durations[Math.floor((n-1)/2)]+durations[Math.floor(n/2)])/2:null,
    p95:n?durations[Math.ceil(n*0.95)-1]:null,p95_honest:p95Honest(n),p95_max_coverage:p95MaxCoverage(n),worst:n?durations[n-1]:null,max_consecutive_failures:maxFailures};
}
function recoveryWindow(period,now,timezone){
  timezone=timezone||'Europe/Berlin';
  var formatter=new Intl.DateTimeFormat('en-GB',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  function localEpoch(stamp){var parts={};formatter.formatToParts(new Date(stamp)).forEach(function(p){parts[p.type]=p.value;});return Date.UTC(Number(parts.year),Number(parts.month)-1,Number(parts.day),Number(parts.hour),Number(parts.minute),Number(parts.second));}
  var d=new Date(localEpoch(now*1000));d.setUTCHours(0,0,0,0);
  if(period==='week')d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
  else if(period==='month')d.setUTCDate(1);
  else if(period!=='day')throw new Error('RECOVERY-PERIOD');
  var desired=d.getTime(),candidate=desired;
  for(var i=0;i<3;i++)candidate=desired-(localEpoch(candidate)-candidate);
  return {start:candidate/1000,end:now,timezone:timezone};
}
function recoveryPreparation(row){return row.operation!=='restoration'&&row.applied_at==null&&(!row.source||row.source==='unknown'||!row.target||row.target==='unknown');}
function resolveRouterVpnUrl(pageUrl,previewOrigin){
  var page;try{page=new URL(pageUrl);}catch(e){return null;}
  if(['http:','https:'].indexOf(page.protocol)<0||page.username||page.password)return null;
  var local=['localhost','127.0.0.1','[::1]'].indexOf(page.hostname.toLowerCase())>=0;
  if(local){
    if(!previewOrigin)return null;
    var router;try{router=new URL(previewOrigin);}catch(e){return null;}
    if(['http:','https:'].indexOf(router.protocol)<0||router.username||router.password||router.search||router.hash||router.pathname!=='/'||['localhost','127.0.0.1','[::1]'].indexOf(router.hostname.toLowerCase())>=0)return null;
    return router.origin+'/#/vpndashboard';
  }
  return page.protocol+'//'+page.hostname+'/#/vpndashboard';
}
var connectivityRequest=null,connectivityBusy=false,connectivityControl=null,connectivityLatest={},connectivityFailure=false;
function connectivityModel(status,request,now){
  var row=status.scan||{},id=request&&request.request_id||row.request_id;
  var requested=request&&request.requested_at||row.requested_at;
  if(!id)return {state:status.rpc_error||status.error?'UNAVAILABLE':'IDLE',busy:false};
  if(status.rpc_error)return {state:'UNAVAILABLE',busy:true};
  if(!Number.isFinite(requested)||now<requested-5||(row.state!=='COMPLETED'&&now-requested>300))return {state:'FAILED',busy:false,code:'SCAN-DEADLINE-EXCEEDED'};
  if(row.request_id!==id)return {state:'QUEUED',busy:true};
  if(row.state==='COMPLETED'){
    if(row.measurement_request_id!==id||!Number.isFinite(row.measured_at)||row.measured_at<requested||!Number.isFinite(row.finished_at)||row.finished_at>now+5||!Number.isInteger(row.checked)||!Number.isInteger(row.failed)||row.checked<0||row.failed<0||row.failed>row.checked)return {state:'UNAVAILABLE',busy:false,code:'SCAN-SNAPSHOT-UNCONFIRMED'};
    return {state:row.checked?'COMPLETED':'EMPTY',busy:false,time:row.measured_at,checked:row.checked,failed:row.failed};
  }
  if(row.state==='FAILED')return {state:'FAILED',busy:false,code:row.code||'SCAN-MEASUREMENT-FAILED'};
  return {state:row.state==='RUNNING'?'RUNNING':'QUEUED',busy:true};
}
function incidentText(value){
  return String(value==null?'unknown':value).slice(0,1000)
    .replace(/-----BEGIN[\s\S]*?-----END[^-]*-----/g,'[REDACTED]')
    .replace(/\b\d{6,12}:[A-Za-z0-9_-]{20,}\b/g,'[REDACTED]')
    .replace(/\b(?:ghp_|github_pat_)[A-Za-z0-9_]+/g,'[REDACTED]')
    .replace(/https?:\/\/[^\s]+/g,'[URL REDACTED]')
    .replace(/\b(?:token|password|secret|private[_ -]?key)\s*[:=]\s*[^\s,;]+/gi,'[REDACTED]');
}
function incidentFields(row){
  return {attempt:incidentText(row.id),source:incidentText(row.source),target:incidentText(row.target),
    outcome:incidentText(row.outcome),codes:(row.codes||[]).slice(0,32).map(incidentText),
    phases:(row.phases||[]).slice(0,64).map(function(p){return incidentText(p.state)+' @ '+(Number.isFinite(p.time)&&p.time>=0&&p.time<=253402300799?new Date(p.time*1000).toISOString():'unknown');}),
    scope:'Retained controller evidence; gaps and missing client/DNS evidence remain unknown. This is not measured LAN outage duration.'};
}
function incidentHTML(rows){
  function esc(v){return incidentText(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>HomenSAI incident report</title><style>body{font:16px sans-serif;max-width:900px;margin:2rem auto;padding:1rem}section{break-inside:avoid;border:1px solid #aaa;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0}}</style></head><body><h1>HomenSAI incident report</h1><p>Print this document and choose Save as PDF. No external resources or scripts.</p>'+rows.slice(0,100).map(function(row){var f=incidentFields(row);return '<section><h2>Attempt '+esc(f.attempt)+'</h2><p>'+esc(f.source)+' → '+esc(f.target)+' · '+esc(f.outcome)+'</p><pre>'+esc(f.codes.join(' | '))+'\n'+esc(f.phases.join('\n'))+'</pre><p>'+esc(f.scope)+'</p></section>';}).join('')+'</body></html>';
}
function downloadIncidentReport(rows){
  var url=URL.createObjectURL(new Blob([incidentHTML(rows)],{type:'text/html;charset=utf-8'}));
  var link=document.createElement('a');link.href=url;link.download='homensai-incidents.html';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
}
function readinessProof(status,now,fresh){
  var proof={},ns=status.native_failover||{};if(!fresh)return proof;
  proof['DEPENDENCY-UBUS']=proof['RPC-PLUGIN']='page';
  if((status.lua_backend||{}).monitor==='lua')proof['DEPENDENCY-LUA']='page';
  if(typeof autoControlModel==='function'&&autoControlModel(status,now).on&&ns.mode==='continuous-pair'&&ns.readiness_verified===true&&ns.kernel_policy_verified===true)proof['DEPENDENCY-UCI']=proof['DEPENDENCY-IP']='auto';
  return proof;
}
function readinessModel(status,now){
  var data=status.system_readiness||{},native=status.native_failover||{};
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&now>=status.time&&now-status.time<=90;
  var reported=!status.rpc_error&&Number.isFinite(data.time)&&data.time<=now+5;
  var environmentFresh=fresh&&reported&&now>=data.time&&now-data.time<=90;
  var blockers=Array.isArray(native.blockers)?native.blockers.slice(0,32):[];
  if(!environmentFresh)blockers.push('ENVIRONMENT-EVIDENCE-UNAVAILABLE');
  if(!fresh)blockers.push('MONITOR-EVIDENCE-STALE');
  if(!blockers.length)blockers.push('NATIVE-START-CERTIFICATION-REQUIRED');
  var proof=readinessProof(status,now,fresh),checks=[],seen={};
  (reported&&Array.isArray(data.checks)?data.checks.slice(0,16):[]).forEach(function(c){
    var code=String(c.code);if(seen[code])return;seen[code]=1;
    checks.push(proof[code]&&!(environmentFresh&&c.state==='pass')?{code:code,state:'pass',proof:proof[code]}:{code:code,state:String(c.state),stale:!environmentFresh});
  });
  Object.keys(proof).forEach(function(code){if(!seen[code])checks.push({code:code,state:'pass',proof:proof[code]});});
  return {fresh:fresh,environmentFresh:environmentFresh,reported:reported,age:reported?Math.max(0,now-data.time):null,board:reported?data.board||{}:{},
    checks:checks,blockers:blockers,
    auto:(status.auto_control||{}).requested==='on'&&fresh?'requested':'off_or_unknown'};
}
var READINESS_CHECKS={
  'PYTHON-39-MINIMUM':['Python 3.9 or newer','Python 3.9 или новее','Runs the program','Запускает программу','🐍'],
  'DEPENDENCY-UBUS':['ubus','ubus','Talks to the router system','Связь с системой роутера','⇄'],
  'DEPENDENCY-UCI':['uci','uci','Reads and saves settings','Чтение и сохранение настроек','⚙'],
  'DEPENDENCY-LUA':['Lua','Lua','Settings helper','Помощник настроек','λ'],
  'DEPENDENCY-IP':['ip','ip','Network tool','Сетевой инструмент','⛓'],
  'RPC-PLUGIN':['Program plugin','Модуль программы','Connects this page to the program','Связывает эту страницу с программой','🔌'],
  'CA-BUNDLE':['Certificates','Сертификаты','For HTTPS checks','Для проверок HTTPS','🔒'],
  'CONFIG-STORAGE-FREE':['Writable configuration storage','Записываемое хранилище настроек','Writable filesystem and at least 1 MB free','Доступная запись и не менее 1 МБ свободно','💾']
};
var READINESS_GUIDES={
  'PYTHON-39-MINIMUM':{packages:'python3',install:'opkg install python3',verify:'python3 --version',en:'Runs the application. Version 3.9 or newer is required; installing an older vendor Python is not a pass.',ru:'Выполняет программу. Нужен Python 3.9 или новее; установка более старой версии из feeds не означает готовность.'},
  'DEPENDENCY-UBUS':{packages:'ubus',install:'opkg install ubus',verify:'ubus call system board',en:'Connects the application to router services. A missing command and a stopped ubus service need different diagnoses.',ru:'Обеспечивает связь со службами роутера. Отсутствующая команда и остановленная служба ubus — разные причины.'},
  'DEPENDENCY-UCI':{packages:'uci',install:'opkg install uci',verify:'command -v uci',en:'Reads and saves router settings. Never delete configuration or reset the router to repair this check.',ru:'Читает и сохраняет настройки. Не удаляйте конфигурацию и не сбрасывайте роутер ради исправления проверки.'},
  'DEPENDENCY-LUA':{packages:'lua lua-cjson libuci-lua',install:'opkg install lua lua-cjson libuci-lua',verify:'lua -e "require(\'cjson\'); require(\'uci\')"',en:'Runs the settings helper. Both the interpreter and its JSON/UCI modules must load.',ru:'Запускает помощник настроек. Должны работать интерпретатор и модули JSON/UCI.'},
  'DEPENDENCY-IP':{packages:'ip-full',install:'opkg install ip-full',verify:'ip -Version',en:'Inspects interfaces and policy routes. Keep the matching vendor package; do not remove networking packages to force a replacement.',ru:'Проверяет интерфейсы и маршруты. Нужен пакет этой прошивки; не удаляйте сетевые компоненты ради принудительной замены.'},
  'RPC-PLUGIN':{packages:'application / rpcd',install:'',verify:'ubus -v list homensai-vpn',en:'Connects this page to the installed application. Check the verified application package and rpcd registration; a Python package alone cannot repair it. Follow the installation prompt for a verified repair, without force flags.',ru:'Связывает страницу с приложением. Проверьте проверенный пакет программы и регистрацию в rpcd: установка Python сама по себе это не исправит. Для восстановления используйте установочный промпт без force-флагов.'},
  'CA-BUNDLE':{packages:'ca-bundle',install:'opkg install ca-bundle',verify:'test -s /etc/ssl/certs/ca-certificates.crt',en:'Supplies trusted certificate authorities for HTTPS. Also check the router clock; never disable TLS verification to make a probe pass.',ru:'Содержит доверенные центры сертификатов HTTPS. Проверьте и часы роутера; не отключайте проверку TLS ради зелёного результата.'},
  'CONFIG-STORAGE-FREE':{packages:'none',install:'',verify:'df -k /etc/config; cat /proc/mounts',en:'Settings need a writable filesystem and at least 1 MiB free; installation preflight separately needs 20 MiB. Read-only storage can have plenty of space but cannot save settings. Diagnose filesystem/recovery first; never automatically remount a production router, delete arbitrary files or reset it.',ru:'Для настроек нужна записываемая файловая система и минимум 1 МиБ; установочный preflight отдельно требует 20 МиБ. Read-only хранилище может иметь много места, но не сохранять настройки. Сначала диагностика файловой системы/восстановления; не перемонтируйте рабочий роутер автоматически, не удаляйте произвольные файлы и не сбрасывайте его.'}
};
function readinessRepairPrompt(code){
  var g=READINESS_GUIDES[code],r=READINESS_CHECKS[code];if(!g||!r)return '';
  return bi('On the specific router I identify, diagnose and repair this failed application check: ','На указанном мной роутере проверь и исправь этот пункт готовности приложения: ')+code+' — '+bi(r[0],r[1])+'.\n'+
    bi('Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.\n','Сначала только чтением: модель/прошивка, штатные feeds, фактическая причина и место. Сохрани проверенную приватную копию. Используй разрешённый доступ; не запрашивай секреты в чат.\n')+
    bi('Purpose: ','Назначение: ')+bi(g.en,g.ru)+'\n'+
    (g.install?bi('After checking compatibility, install only from this firmware\'s original vendor feeds. Example: ','После проверки совместимости устанавливай только из штатных feeds этой прошивки. Пример: ')+g.install+'\n':'')+
    bi('Verify using: ','Проверь командой: ')+g.verify+'\n'+
    bi('Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.\n','Без force, массового обновления, чужих feeds, прошивки, сброса firewall и изменений сети компьютера. Не запускай Auto и не принимай соглашение за меня. Обнови готовность и проверь свежий результат, не только exit установщика. Отчитайся PASS/FAIL/BLOCKED/UNKNOWN и перечисли непроверенное.\n')+
    'https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.'+(locale==='ru'?'ru':'en')+'.md';
}
function renderReadinessHelp(code){
  var g=READINESS_GUIDES[code],r=READINESS_CHECKS[code];
  var prompt=E('textarea',{'readonly':'readonly','rows':'12','style':'width:100%;box-sizing:border-box','aria-label':bi('AI repair prompt','Промпт исправления с ИИ')});prompt.value=readinessRepairPrompt(code);
  var copy=E('button',{'type':'button','class':'cbi-button','click':function(){
    function select(){prompt.focus();prompt.select();}
    if(typeof navigator!=='undefined'&&navigator.clipboard)return navigator.clipboard.writeText(prompt.value).then(function(){copy.textContent=bi('Copied','Скопировано');}).catch(select);
    select();
  }},bi('Copy repair prompt','Скопировать промпт исправления'));
  return E('div',{'data-readiness-help':code},[
    E('h3',{},bi(r[0],r[1])+' · '+code),E('p',{},bi(g.en,g.ru)),
    E('h4',{},bi('Install manually','Установить самостоятельно')),
    E('p',{},bi('Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.','Подключитесь к нужному роутеру, проверьте прошивку/место и сохраните проверенную приватную копию. Используйте только штатные feeds этой прошивки. Выполняйте opkg update лишь для обновления списка пакетов. Не запускайте opkg upgrade и не используйте force.')),
    g.install?E('pre',{'class':'hv-cmd'},g.install):E('p',{},bi('This needs diagnosis/recovery, not an arbitrary additional package.','Здесь нужна диагностика/восстановление, а не произвольный дополнительный пакет.')),
    E('h4',{},bi('Verify the result','Проверить результат')),E('pre',{'class':'hv-cmd'},g.verify),
    E('p',{},bi('Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.','Обновите страницу и снова откройте «Готовность роутера» («Настройки → Система и диагностика»; в «Пульте» — вкладка «Система»); дождитесь свежих данных. Ошибка или устаревшая проверка остаётся непроверенной даже после успешной команды установки.')),
    E('h4',{},bi('Let ChatGPT/Codex or Claude do it','Поручить ChatGPT/Codex или Claude')),E('p',{},bi('Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.','Нужен агент с терминалом и доступом к роутеру. Промпт относится только к этому пункту и не разрешает другие сетевые изменения.')),copy,prompt
  ].filter(Boolean));
}
function monitorLightModel(status,inventory,now,recent){
  var settings=(inventory||{}).settings||{},enabled=settings.enabled===true;
  var age=Number.isFinite(status.time)?now-status.time:Infinity;
  var fresh=!status.rpc_error&&!status.error&&(typeof observationFresh==='function'?observationFresh(status,now):age>=-5&&age<=90);
  function out(key,lamp,icon,title,hint,code){return {key:key,lamp:lamp,icon:icon,title:title,hint:hint,code:code||null,enabled:enabled};}
  if(!status.rpc_error&&status.speed_pause&&status.speed_pause.active&&status.speed_pause.monitor_paused)return out('transition','yellow','Ⅱ',bi('Monitoring paused for speed test','Мониторинг на паузе для теста скорости'),bi('A fresh check runs after the test, before Auto continues.','После теста выполнится свежая проверка, затем продолжит работу Auto.'));
  if(status.rpc_error)return out('problem','red','!',bi('Cannot read the monitor','Не удаётся прочитать мониторинг'),bi('The page could not get the status from the router. Reload the page and sign in again; see Help → “The page is old, empty or says the monitor is not running”.','Страница не смогла получить статус от роутера. Обновите страницу и войдите снова; см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'),'RPC-UNAVAILABLE');
  if(!status.rpc_error&&status.speed_pause&&status.speed_pause.active&&status.speed_pause.phase==='RESUMING')return out('transition','yellow','⟳',bi('Monitoring is resuming','Мониторинг возобновляется'),bi('Waiting for the first post-test observation.','Ожидается первая проверка после теста.'));
  if(enabled&&fresh)return out('ok','green','✓',bi('Monitor is running','Мониторинг работает'),bi('Fresh data arrived '+Math.max(0,Math.round(age))+' s ago. Each connected VPN is checked about every '+(Number(settings.interval)||10)+' seconds.','Свежие данные пришли '+Math.max(0,Math.round(age))+' с назад. Каждый подключённый VPN проверяется примерно раз в '+(Number(settings.interval)||10)+' с.'));
  if(enabled&&(recent||(!status.error&&age<=300)))return out('transition','yellow','⟳',bi('Starting or catching up','Запускается или догоняет'),bi('The monitor is switched on and the first fresh data is not here yet. This takes up to a minute.','Мониторинг включён, первых свежих данных ещё нет. Это занимает до минуты.'));
  if(enabled)return out('problem','red','!',bi('Switched on, but not running','Включён, но не работает'),bi('The router program is not producing data.','Программа на роутере не выдаёт данные.'),status.error||'STATUS-STALE');
  return out('problem','red','!',bi('Monitoring must be running','Мониторинг должен работать'),bi('Monitoring is required for Auto. Restore monitoring before starting automatic control.','Мониторинг необходим для Auto. Восстановите мониторинг перед запуском автоматического управления.'),'SERVICE-STOPPED');
}
var COUNTRIES={
  al:['Albania','Албания'],ar:['Argentina','Аргентина'],am:['Armenia','Армения'],au:['Australia','Австралия'],at:['Austria','Австрия'],az:['Azerbaijan','Азербайджан'],
  bd:['Bangladesh','Бангладеш'],be:['Belgium','Бельгия'],ba:['Bosnia and Herzegovina','Босния и Герцеговина'],br:['Brazil','Бразилия'],bg:['Bulgaria','Болгария'],
  by:['Belarus','Беларусь'],ca:['Canada','Канада'],ch:['Switzerland','Швейцария'],cl:['Chile','Чили'],co:['Colombia','Колумбия'],cr:['Costa Rica','Коста-Рика'],
  hr:['Croatia','Хорватия'],cy:['Cyprus','Кипр'],cz:['Czechia','Чехия'],dk:['Denmark','Дания'],de:['Germany','Германия'],ee:['Estonia','Эстония'],es:['Spain','Испания'],
  fi:['Finland','Финляндия'],fr:['France','Франция'],gb:['United Kingdom','Великобритания'],ge:['Georgia','Грузия'],gr:['Greece','Греция'],hk:['Hong Kong','Гонконг'],
  hu:['Hungary','Венгрия'],is:['Iceland','Исландия'],in:['India','Индия'],id:['Indonesia','Индонезия'],ie:['Ireland','Ирландия'],il:['Israel','Израиль'],it:['Italy','Италия'],
  jp:['Japan','Япония'],kz:['Kazakhstan','Казахстан'],kr:['South Korea','Южная Корея'],lv:['Latvia','Латвия'],lt:['Lithuania','Литва'],lu:['Luxembourg','Люксембург'],
  md:['Moldova','Молдова'],me:['Montenegro','Черногория'],mk:['North Macedonia','Северная Македония'],mx:['Mexico','Мексика'],my:['Malaysia','Малайзия'],nl:['Netherlands','Нидерланды'],
  nz:['New Zealand','Новая Зеландия'],no:['Norway','Норвегия'],pa:['Panama','Панама'],pe:['Peru','Перу'],ph:['Philippines','Филиппины'],pl:['Poland','Польша'],pt:['Portugal','Португалия'],
  ro:['Romania','Румыния'],rs:['Serbia','Сербия'],ru:['Russia','Россия'],sg:['Singapore','Сингапур'],sk:['Slovakia','Словакия'],si:['Slovenia','Словения'],za:['South Africa','Южная Африка'],
  se:['Sweden','Швеция'],th:['Thailand','Таиланд'],tr:['Turkey','Турция'],tw:['Taiwan','Тайвань'],ua:['Ukraine','Украина'],ae:['United Arab Emirates','ОАЭ'],us:['United States','США'],
  uy:['Uruguay','Уругвай'],uz:['Uzbekistan','Узбекистан'],vn:['Vietnam','Вьетнам']
};
var COUNTRY_ALIASES={uk:'gb',usa:'us',uae:'ae',holland:'nl','czech republic':'cz','south korea':'kr',korea:'kr'};
function countryCodeFromName(text){
  if(typeof text!=='string'||!text)return null;
  var name=text.toLowerCase().slice(0,96),code;
  var words=[];Object.keys(COUNTRIES).forEach(function(key){words.push([COUNTRIES[key][0].toLowerCase(),key]);words.push([COUNTRIES[key][1].toLowerCase(),key]);});
  Object.keys(COUNTRY_ALIASES).forEach(function(alias){words.push([alias,COUNTRY_ALIASES[alias]]);});
  words.sort(function(a,b){return b[0].length-a[0].length;});
  for(var i=0;i<words.length;i++){
    var at=name.indexOf(words[i][0]);
    if(at>=0&&words[i][0].length>=3&&!/[a-zа-я]/.test(name.charAt(at-1)||' ')&&!/[a-zа-я]/.test(name.charAt(at+words[i][0].length)||' '))return words[i][1];
  }
  var match=/^([a-z]{2})(?:[0-9]{1,5}(?=[._-]|$)|[-_ ])/.exec(name)||/^([a-z]{2})$/.exec(name);
  if(match){code=COUNTRY_ALIASES[match[1]]||match[1];if(COUNTRIES[code])return code;}
  return null;
}
function countryOf(profile){
  if(!profile)return null;
  var code=countryCodeFromName(profile.router_name)||countryCodeFromName(profile.name)||countryCodeFromName(profile.channel);
  return code?{code:code,en:COUNTRIES[code][0],ru:COUNTRIES[code][1]}:null;
}
function countryName(profile){var country=countryOf(profile);return country?bi(country.en,country.ru):'';}
function protocolLabel(profile){return profile&&profile.protocol==='wireguard'?'WireGuard':'OpenVPN';}
function customName(profile){return profile&&profile.router_name&&profile.name&&profile.name!==profile.router_name?String(profile.name):'';}
function serverTitle(profile){
  var country=countryName(profile);
  return country?country+' · '+protocolLabel(profile)+(customName(profile)?' · '+customName(profile):''):(customName(profile)||(profile&&profile.name)||'—');
}
var VENDOR_COORDINATION_TEXT={
  'CROSS-TUNNEL-READY':['Ready: if the primary fails, the reserve can take over. This is only a plan; this line switches nothing.','Готово: если основной откажет, резерв сможет принять трафик. Это только план, эта строка ничего не переключает.'],
  'VENDOR-SAME-TUNNEL':['Both choices are the same router tunnel. The router picks its server itself; the app does not switch inside it.','Выбран один и тот же туннель роутера. Сервер в нём выбирает сам роутер, приложение внутри него не переключает.'],
  'VENDOR-SETTLING':['Watching: the app waits until the channel settings stop changing.','Идёт наблюдение: приложение ждёт, пока настройки каналов перестанут меняться.'],
  'VENDOR-IDENTITY-UNKNOWN':['The app cannot tell which router tunnel this is yet.','Приложение пока не может определить, какой это туннель роутера.'],
  'OBSERVATION-STALE':['The latest checks are too old to rely on.','Последние проверки слишком старые, на них нельзя опираться.'],
  'PROFILE-IDENTITY-CHANGED':['The channel profile changed; new checks are needed.','Профиль канала изменился; нужны новые проверки.'],
  'UPLINK-LINK-DOWN':['The router has no internet cable or Wi-Fi uplink; switching VPN would not help, so it is paused.','У роутера нет интернета (кабель или Wi-Fi). Переключение VPN не поможет, поэтому оно приостановлено.'],
  'PLAN-CONFIG':['The chosen pair of tunnels needs to be reviewed in Settings → Channels: primary and reserve (Console: Channels → Change the channel pair).','Выбранную пару туннелей нужно проверить в «Настройки → Каналы: основной и резерв» (в «Пульте» — «Каналы» → «Изменить пару каналов»).']
};
function vendorTunnelId(value){return typeof value==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.-]{1,64}$/.test(value)?value:null;}
function vendorProfileId(value){return typeof value==='string'&&/^[A-Za-z0-9_.:-]{1,96}$/.test(value)?value:null;}
function vendorLabel(value){return typeof value==='string'&&Array.from(value).length<=64&&value.trim()&&!/[\p{C}\p{Zl}\p{Zp}]/u.test(value)?value:null;}
function vendorFresh(stamp,now,age){return typeof stamp==='number'&&Number.isFinite(stamp)&&stamp>=0&&stamp<=now&&now-stamp<=age;}
function vendorDiagnosticsModel(status,inventory,now){
  if(typeof dataCause==='function')UI_DATA_CAUSE=dataCause(status,now);
  status=status&&typeof status==='object'?status:{};inventory=inventory&&typeof inventory==='object'?inventory:{};
  var settings=inventory.settings||{},interval=Number(settings.interval),age=Number.isFinite(status.observation_valid_for)?observationValidFor(status):Number.isInteger(interval)&&interval>=10&&interval<=300?Math.max(30,interval*3):90;
  var observation=status.vendor_observation,available=!!observation&&observation.version===1&&Array.isArray(observation.groups);
  var fresh=available&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(observation.time,now,age);
  var profiles=Array.isArray(status.profiles)?status.profiles.slice(0,400):[],metadata=Array.isArray(inventory.servers)?inventory.servers.slice(0,400):[],profileMap=Object.create(null),metadataMap=Object.create(null);
  profiles.forEach(function(p){if(p&&vendorProfileId(p.id))profileMap[p.id]=Object.prototype.hasOwnProperty.call(profileMap,p.id)?null:p;});
  metadata.forEach(function(p){if(p&&vendorProfileId(p.profile))metadataMap[p.profile]=Object.prototype.hasOwnProperty.call(metadataMap,p.profile)?null:p;});
  function profileName(id){var row=metadataMap[id],measured=profileMap[id],configured=(Array.isArray(inventory.profiles)?inventory.profiles:[]).filter(function(p){return p&&p.id===id;})[0];return row&&vendorLabel(row.name)||measured&&vendorLabel(measured.name)||measured&&vendorLabel(measured.router_name)||configured&&vendorLabel(configured.name)||id||bi('Not reported by the router','Роутер не сообщил');}
  var groups=[],seen={};
  (available?observation.groups.slice(0,400):[]).forEach(function(raw){
    if(!raw||typeof raw!=='object')return;
    var id=vendorTunnelId(raw.id);if(!id||raw.protocol!==id.split(':')[0])return;
    if(seen[id]){seen[id].state='unknown';seen[id].health='unknown';seen[id].current=null;return;}
    var ids=Array.isArray(raw.profiles)?raw.profiles.slice(0,8).filter(function(v,i,a){return vendorProfileId(v)&&a.indexOf(v)===i;}):[];
    var active=Array.isArray(raw.active_profiles)?raw.active_profiles.slice(0,2).filter(function(v,i,a){return vendorProfileId(v)&&ids.indexOf(v)>=0&&a.indexOf(v)===i;}):[];
    var current=vendorProfileId(raw.current_profile),generation=typeof raw.generation==='string'&&/^[0-9a-f]{32}$/.test(raw.generation)?raw.generation:null;
    var coherent=!!generation&&!!current&&Array.isArray(raw.profiles)&&raw.profiles.length===ids.length&&Array.isArray(raw.active_profiles)&&raw.active_profiles.length===1&&active.length===1&&active[0]===current;
    var stable=fresh&&vendorFresh(raw.time,now,age)&&raw.state==='SETTLED'&&Number.isInteger(raw.stable_samples)&&raw.stable_samples>=2&&raw.stable_samples<=1000000&&coherent;
    var state=!fresh||!vendorFresh(raw.time,now,age)?'unknown':stable?'stable':raw.state==='PENDING'&&coherent&&raw.stable_samples===1?'pending':'unknown';
    var row=profileMap[current],health='unknown';
    var member=stable&&row&&!(metadataMap[current]&&metadataMap[current].enabled===false)&&row.protocol===raw.protocol&&row.interface===id.split(':')[1]&&row.vendor_state==='SETTLED'&&row.vendor_tunnel_id===id&&row.vendor_generation===generation&&vendorFresh(row.time,now,age)&&vendorFresh(raw.changed_at,now,now)&&row.vendor_changed_at===raw.changed_at&&raw.changed_at<=row.time&&raw.changed_at<=raw.time?row:null;
    if(member){
      if(row.code===null&&row.dns_ok===true&&Number.isInteger(row.https_success)&&row.https_success>=2)health='healthy';
      else if(['VPN-001','VPN-003','DNS-001','VPN-MTU','ROUTE-001'].indexOf(row.code)>=0)health='failed';
    }
    var labels=[];ids.forEach(function(profile){var measured=profileMap[profile],saved=metadataMap[profile],label=vendorLabel(saved&&saved.channel)||vendorLabel(measured&&measured.channel);if(label&&labels.indexOf(label)<0)labels.push(label);});
    var profileGroup=typeof raw.profile_group_id==='string'&&/^(openvpn|wireguard):[0-9]{1,20}$/.test(raw.profile_group_id)&&raw.profile_group_id.split(':')[0]===raw.protocol?raw.profile_group_id:null;
    var group={id:id,protocol:raw.protocol,profileGroup:profileGroup,current:state!=='unknown'&&current&&ids.indexOf(current)>=0?current:null,member:member,name:profileName(current),state:state,health:health,labels:labels,changedAt:vendorFresh(raw.changed_at,now,now)?raw.changed_at:null};seen[id]=group;groups.push(group);
  });
  var rawCoord=(status.failover_plan||{}).coordination,coordination={known:false,code:null,state:'UNKNOWN',source:null,target:null,transition:null,settleUntil:null};
  if(rawCoord&&rawCoord.version===1&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(rawCoord.time,now,age)&&rawCoord.can_apply===false&&rawCoord.vendor_attempts_exhausted===null&&rawCoord.vendor_reason==='UNOBSERVED'&&Object.prototype.hasOwnProperty.call(VENDOR_COORDINATION_TEXT,rawCoord.code)&&['READY','HOLD','UNKNOWN'].indexOf(rawCoord.state)>=0){
    var source=vendorTunnelId(rawCoord.source_tunnel),target=vendorTunnelId(rawCoord.target_tunnel);
    var sourceGroup=groups.filter(function(g){return g.id===source;})[0],targetGroup=groups.filter(function(g){return g.id===target;})[0];
    var transition=source&&target&&(source.split(':')[0]===target.split(':')[0]?'channel':'protocol');
    var ready=rawCoord.code!=='CROSS-TUNNEL-READY'||rawCoord.state==='READY'&&source&&target&&source!==target&&rawCoord.transition===transition&&sourceGroup&&sourceGroup.state==='stable'&&sourceGroup.health!=='unknown'&&targetGroup&&targetGroup.state==='stable'&&targetGroup.health==='healthy';
    if(ready)coordination={known:true,code:rawCoord.code,state:rawCoord.state,source:source,target:target,transition:['channel','protocol'].indexOf(rawCoord.transition)>=0?rawCoord.transition:null,settleUntil:typeof rawCoord.settle_until==='number'&&Number.isFinite(rawCoord.settle_until)&&rawCoord.settle_until>now?rawCoord.settle_until:null};
  }
  var events=[];
  (available&&Array.isArray(observation.events)?observation.events.slice(-50):[]).forEach(function(event){
    if(!event||event.cause!=='UNOBSERVED'||!vendorFresh(event.time,now,now)||!vendorTunnelId(event.tunnel))return;
    if(['VENDOR-PROFILE-CHANGED','VENDOR-BINDING-CHANGED','VENDOR-BINDING-UNKNOWN','VENDOR-FIRST-OBSERVATION'].indexOf(event.code)<0)return;
    var before=vendorProfileId(event.previous_profile),after=vendorProfileId(event.current_profile);
    if(event.code==='VENDOR-PROFILE-CHANGED'&&(!before||!after||before===after))return;
    events.push({time:event.time,tunnel:event.tunnel,before:before,after:after,code:event.code});
  });
  events.sort(function(a,b){return b.time-a.time;});
  return {available:available,fresh:fresh,groups:groups,coordination:coordination,events:events.slice(0,8),source:vendorTunnelId(settings.plan_source_tunnel),target:vendorTunnelId(settings.plan_target_tunnel)};
}
function vendorDisplayMember(status,inventory,role,now,legacyId){
  if(role!=='source'&&role!=='target')return null;
  var settings=(inventory||{}).settings||{},anchor=settings['plan_'+role+'_tunnel'];
  if(anchor!=null&&anchor!==''){
    if(!vendorTunnelId(anchor))return null;
    var group=vendorDiagnosticsModel(status,inventory,now).groups.filter(function(g){return g.id===anchor;})[0];
    return group&&group.state==='stable'&&group.member||null;
  }
  var id=legacyId||settings['plan_'+role],rows=Array.isArray((status||{}).profiles)?status.profiles.filter(function(p){return p&&p.id===id;}):[];
  return rows.length===1?rows[0]:null;
}
var ERROR_ROWS=(function(g){return [["CLIENT-CONTROL-PATH-MISMATCH",0,"Management route uses another interface","Управление идёт через другой интерфейс"],["WAN-001",1,"Internet is down at the router","Нет интернета на роутере"],["DNS-001",1,"DNS check did not pass","DNS-проверка не прошла"],["VPN-001",1,"VPN did not connect","VPN не подключился"],["VPN-002",1,"VPN login rejected","VPN отклонил вход"],["VPN-003",1,"HTTPS availability below threshold","Недостаточно успешных HTTPS-проверок"],["VPN-MTU",1,"Large packets are lost","Большие пакеты теряются"],["VPN-004",1,"VPN server name does not resolve","Имя VPN-сервера не находится"],["TLS-001",1,"Certificate check failed","Ошибка проверки сертификата"],["ROUTE-001",1,"Traffic goes another way","Трафик идёт другим путём"],["CHECK-001",1,"Check not confirmed","Проверка не подтверждена"],["SWITCH-001",2,"No ready reserve","Нет готового резерва"],["AUTO-CONTROL-UNVERIFIED",2,"Auto request not confirmed","Запрос Auto не подтверждён"],["AUTO-CONTROL-FAILED",2,"Auto request got no answer","Запрос Auto остался без ответа"],["AUTO-START-REFUSED",2,"Auto start refused","Запуск Auto отклонён"],["ROLLBACK-GIVEN-UP",2,"Automatic return stopped","Автоматический возврат остановлен"],["EXIT-TRACE-FAILED",2,"Exit address could not be read","Не удалось прочитать внешний адрес"],["STOP-UNCONFIRMED",2,"Stop not confirmed","Остановка не подтверждена"],["SWITCH-002",2,"Internet not restored after the switch","Интернет не вернулся после переключения"],["SWITCH-003",2,"Switch could not be applied","Переключение не удалось применить"],["CONFIG-001",2,"Automation paused after manual change","Автоматика на паузе после ручного изменения"],["SYSTEM-001",3,"Unsupported firmware or missing tool","Неподдерживаемая прошивка или нет программы"],["MONITOR-START-REQUESTED",3,"Start requested","Запуск запрошен"],["MONITOR-STOP-REQUESTED",3,"Stop requested","Остановка запрошена"],["MONITOR-STOP-AUTO-FIRST",3,"Stop Auto first","Сначала остановите Auto"],["MONITOR-JOURNAL-UNVERIFIED",3,"Journal cannot be read","Журнал не читается"],["MONITOR-SAVE-FAILED",3,"Setting not saved","Настройка не сохранилась"],["MONITOR-SERVICE-UNCONFIRMED",3,"Service change not confirmed","Смена состояния службы не подтверждена"],["MONITOR-INVALID",3,"Invalid request","Неверный запрос"],["MONITOR-RPC-UNCONFIRMED",3,"No confirmed answer","Нет подтверждённого ответа"],["RPC-UNAVAILABLE",3,"Router does not answer","Роутер не отвечает"],["PRIMARY-PROVEN",2,"The primary is already proven","Основной уже проверен"],["SESSION-ORDER",2,"Saved channel order differs","Сохранённый порядок каналов другой"],["RESUME-MARKER-UNREADABLE",2,"Resume marker unreadable","Метка возобновления не читается"],["BOOT-RESERVE-ADOPTED",2,"Auto resumed on the reserve after a restart","Auto возобновлён на резерве после перезапуска"],["BOOT-RESERVE-UNVERIFIED",2,"Reserve not confirmed after a restart","Резерв не подтверждён после перезапуска"],["DNS-MARK-UNVERIFIED",2,"LAN DNS channel not confirmed","DNS-канал LAN не подтверждён"],["DNS-MARK-UNAVAILABLE",2,"No GL dns_mark module","Нет модуля GL dns_mark"],["DNS-DUAL-UNVERIFIED",2,"DNS through both tunnels not confirmed","DNS через оба туннеля не подтверждён"],["DNS-DUAL-UNAVAILABLE",2,"DNS through both tunnels not possible here","DNS через оба туннеля здесь невозможен"],["SERVER-PICKED",2,"Channel server changed","Сервер канала сменён"],["SERVER-PICK-FAILED",2,"Channel server not changed","Сервер канала не сменён"],["SERVER-PICK-WAITING-VENDOR",2,"GL is switching the server itself","GL сам меняет сервер"],["SERVER-PICK-LIMIT",2,"Server change limit reached","Достигнут предел смены серверов"],["SERVER-PICK-CARRYING",2,"Channel carries traffic: server kept","Канал везёт трафик: сервер не меняется"],["SERVER-PICK-REQUESTED",2,"Server change handed to Auto","Смена сервера передана Auto"],["SERVER-PICK-DEFERRED",2,"Server change waits for Auto","Смена сервера ждёт Auto"],["SERVER-CHANGING",2,"Auto is changing an idle channel server","Auto меняет сервер незанятого канала"],["SERVER-PICK-OFF",2,"Server pick is off","Подбор сервера выключен"],["SERVER-KEY-PINNED",1,"Server key remembered","Ключ сервера запомнен"],["SERVER-KEY-CHANGED",1,"Server key changed","Ключ сервера изменился"],["SERVER-KEY-ACCEPTED",1,"New server key accepted","Новый ключ сервера принят"],["SERVER-KEY-FORGOTTEN",1,"Remembered server key removed","Запомненный ключ сервера удалён"],["SERVER-KEY-UNACCEPTED",2,"Changed server key not accepted","Сменившийся ключ сервера не принят"],["SERVER-KEY-STATE-CORRUPT",1,"Remembered server keys unreadable","Запомненные ключи серверов не читаются"],["SERVER-KEY-PROFILE-INVALID",1,"Server key request not understood","Запрос по ключу сервера не понят"],["SERVER-KEY-NOT-CHANGED",1,"No such key change to accept","Такой смены ключа нет"],["KEYPAIR-CREATED",1,"WireGuard handshake completed","Рукопожатие WireGuard выполнено"],["REKEY-TIMEOUT",1,"WireGuard handshake not answered","Рукопожатие WireGuard без ответа"],["REKEY-GIVEUP",1,"WireGuard stopped retrying the handshake","WireGuard перестал повторять рукопожатие"],["ADVISOR-BUSY-OUTAGE",4,"Not now: an outage is in progress","Не сейчас: идёт обрыв"],["ADVISOR-BUSY-SWITCH",4,"Not now: a switch is in progress","Не сейчас: идёт переключение"],["ADVISOR-CALM-UNKNOWN",4,"Calm state not confirmed","Спокойствие не подтверждено"],["ADVISOR-MODEL-CONSECUTIVE",4,"Slider does not apply to this detector","Ползунок не действует на этот детектор"],["ADVISOR-NO-RECOMMENDATION",4,"No recommendation to apply","Нет рекомендации для применения"],["ADVISOR-OUT-OF-BOUNDS",4,"Value outside the safe range","Значение вне безопасного диапазона"],["ADVISOR-PG-BELOW-THETA",4,"Return threshold below leave threshold","Порог возврата ниже порога ухода"],["ADVISOR-RESCUE-ABOVE-STABLE",4,"Rescue return longer than primary stability","Возврат после отказа резерва дольше стабильности"],["ADVISOR-RIDE-NOT-BELOW-LEAVE",4,"This setting would never leave a dead channel","Такая настройка не уйдёт с мёртвого канала"],["ADVISOR-RANGE",4,"Slider value not accepted","Значение ползунка не принято"],["ADVISOR-ONCE-A-DAY",4,"Auto-adaptation already moved today","Автоподстройка сегодня уже двигала"],["ADVISOR-UNAVAILABLE",4,"Auto-adaptation status unavailable","Состояние автоподстройки недоступно"],["AUTO-RESUME-PENDING",3,"Auto is coming back after a restart","Auto возвращается после перезапуска"],["RESTART-CLEAN",3,"Clean restart","Штатный перезапуск"],["RESTART-FIRST-START",3,"First start","Первый запуск"],["RESTART-PROCESS",3,"Process restarted","Процесс перезапущен"],["RESTART-INTERRUPTED-BOOT",3,"Cut while starting","Сбой при запуске"],["RESTART-INTERRUPTED-SWITCH",3,"Cut during a switch","Сбой при переключении"],["RESTART-INTERRUPTED-RESERVE-HOLD",3,"Cut on the reserve","Сбой на резерве"],["RESTART-INTERRUPTED-OPERATION",3,"Cut in normal operation","Сбой при обычной работе"],["RESTART-INTERRUPTED-AUTO-OFF",3,"Cut with Auto off","Сбой при выключенном Auto"],["RESTART-PLANNED-REBOOT",3,"Planned reboot","Плановая перезагрузка"],["RESTART-KERNEL-CRASH",3,"Router kernel crash","Сбой ядра роутера"],["STATUS-STALE",3,"Status is old","Статус устарел"],["RPC-PLUGIN",3,"Program plugin missing","Нет модуля программы"],["RPC-INPUT-SIZE",3,"Request too large","Слишком большой запрос"],["CLIENT-CABLE-LINK-DOWN",0,"Cable adapter is down","Кабельный адаптер не подключён"],["CLIENT-CABLE-ADDRESS-AMBIGUOUS",0,"Cable IPv4 address is ambiguous","Неоднозначный IPv4-адрес кабеля"],["CLIENT-CABLE-NOT-LOCAL",0,"Selected cable does not reach this router locally","Выбранный кабель не ведёт к роутеру локально"],["CLIENT-CABLE-PROBE-ROUTE-MISMATCH",0,"Cable probe route differs","Маршрут кабельной проверки не совпадает"],["CLIENT-CABLE-HTTPS-FAILED",0,"Bound HTTPS check failed","Привязанная HTTPS-проверка не прошла"],["CLIENT-GATEWAY-MISMATCH",0,"Client path uses another gateway","Клиентский путь использует другой шлюз"],["CLIENT-DNS-CONFIG-UNVERIFIED",0,"DNS settings unverified","Настройки DNS не подтверждены"],["CLIENT-IPV6-DEFAULT-UNVERIFIED",0,"IPv6 route unverified","Маршрут IPv6 не подтверждён"],["CLIENT-PROBE-ROUTE-CONFLICT",0,"Legacy probe-route conflict","Конфликт проверочных маршрутов старой версии"],["CLIENT-CANCELLED",0,"Cancelled","Отменено"],["CLIENT-TRIAL-UNCONFIRMED",0,"Trial not confirmed","Тест не подтверждён"],["CLIENT-RESERVE-NOT-VERIFIED",0,"Reserve not verified","Резерв не подтверждён"],["POWERSHELL-7-REQUIRED",0,"PowerShell 7 needed","Нужен PowerShell 7"],["PRIVATE-LAN-ROUTER-REQUIRED",0,"Router address is not private","Адрес роутера не частный"],["TELEGRAM-TOKEN-REQUIRED",5,"Bot token missing","Нет токена бота"],["TELEGRAM-TOKEN-FORMAT",5,"Token looks wrong","Токен выглядит неверно"],["TELEGRAM-TOKEN-REJECTED",5,"Token rejected by Telegram","Telegram отклонил токен"],["TELEGRAM-DESTINATION-FORMAT",5,"Chat ID looks wrong","ID чата выглядит неверно"],["TELEGRAM-PERMISSION",5,"Bot cannot write there","Бот не может туда писать"],["TELEGRAM-RATE-LIMIT",5,"Too many messages","Слишком много сообщений"],["TELEGRAM-DNS",5,"Telegram address not found","Адрес Telegram не найден"],["TELEGRAM-TLS",5,"Secure connection failed","Защищённое соединение не удалось"],["TELEGRAM-DELIVERY-UNKNOWN",5,"Delivery not confirmed","Доставка не подтверждена"],["TELEGRAM-DELIVERED",5,"Delivered","Доставлено"],["TELEGRAM-TEST-DELIVERED",5,"Test delivered","Тест доставлен"],["TELEGRAM-CONFIG",5,"Telegram setup incomplete","Настройка Telegram неполная"],["TELEGRAM-CLOCK-BACKWARD",5,"Clock went back","Часы пошли назад"],["TELEGRAM-STATE-CORRUPT",5,"Report state damaged","Состояние отчётов повреждено"],["SETUP-INVALID",4,"Invalid input","Неверный ввод"],["SETUP-RANGE",4,"Value out of range","Значение вне диапазона"],["SETUP-SAVE-FAILED",4,"Settings not saved","Настройки не сохранены"],["SETUP-STOP-FIRST",4,"Stop Auto first","Сначала остановите Auto"],["SETUP-SAVE-UNCONFIRMED",4,"Save not confirmed","Сохранение не подтверждено"],["SETUP-PENDING-DELTA",4,"Unsaved router changes","Есть несохранённые изменения роутера"],["SETUP-PRIMARY-RESERVE-DISABLED",4,"Primary or reserve is off","Основной или резервный отключён"],["SETUP-PROFILES",4,"Profiles not found","Профили не найдены"],["SPEED-DISABLED",6,"Speed tests are off","Тесты скорости выключены"],["SPEED-DAILY-LIMIT",6,"Daily quota used","Суточная квота исчерпана"],["SPEED-COOLDOWN",6,"Please wait","Нужна пауза"],["SPEED-BUSY",6,"Another test is running","Уже идёт другой тест"],["SPEED-TRAFFIC-BUSY",6,"VPN is busy","VPN сейчас занят"],["SPEED-ROUTE-UNVERIFIED",6,"Test route unverified","Путь теста не подтверждён"],["SPEED-PROFILE-INACTIVE",6,"VPN not connected","VPN не подключён"],["SPEED-NETWORK",6,"Test network error","Сетевая ошибка теста"],["SPEED-CANCELLED",6,"Cancelled","Отменено"],["SCAN-DEADLINE-EXCEEDED",6,"Check took too long","Проверка заняла слишком много времени"],["SCAN-STATE-CORRUPT",6,"Check state damaged","Состояние проверки повреждено"],["CLOCK-001",7,"Wrong router date","Неверная дата на роутере"],["HISTORY-001",7,"History unavailable","История недоступна"],["FAULT-CERTIFIED-AUTO-REQUIRED",2,"Transition test needs running Auto","Для теста перехода нужен работающий Auto"],["FAULT-UNVERIFIED",2,"Failure test not confirmed","Сбой не подтверждён"],["FAULT-UNKNOWN",2,"Failure test result unknown","Итог теста сбоя неизвестен"],["FAULT-CANCEL-UNKNOWN",2,"Cancel not confirmed","Отмена не подтверждена"],["FAULT-RPC-UNCONFIRMED",2,"No answer from the router","Нет ответа от роутера"],["FAULT-FIELDS",2,"Invalid request","Неверный запрос"],["FAULT-HISTORY-UNAVAILABLE",7,"Failure history unavailable","История сбоев недоступна"],["FAULT-STATE-CORRUPT",2,"Failure state damaged","Состояние сбоя повреждено"],["FAULT-NFT-QUERY-FAILED",2,"Cannot read the firewall rule","Не удаётся прочитать правило межсетевого экрана"],["FAULT-TABLE-ALREADY-EXISTS",2,"A previous test is still active","Предыдущий тест ещё активен"],["HISTORY-PARTIAL",7,"History partly aggregated","История частично объединена"],["SPEED-HISTORY-TRUNCATED",6,"Speed history shortened","История скорости сокращена"],["JOURNAL-INTEGRITY-FAILED",2,"Journal failed its check","Журнал не прошёл проверку"],["INTEGRITY-MODE-DIFFERS",3,"File permissions differ","Права файлов отличаются"],["INTEGRITY-OK",3,"Program files verified","Файлы программы проверены"],["INTEGRITY-RESTORED",3,"Damaged program files restored","Повреждённые файлы программы восстановлены"],["INTEGRITY-FILE-RESTORED",3,"A program file was restored","Файл программы восстановлен"],["INTEGRITY-FILE-DAMAGED",3,"A program file is damaged","Файл программы повреждён"],["INTEGRITY-FILE-MISSING",3,"A program file is missing","Файл программы отсутствует"],["INTEGRITY-FILE-MODE",3,"A program file has wrong permissions","У файла программы неверные права"],["INTEGRITY-MANIFEST-UNREADABLE",3,"Checksum list damaged","Список контрольных сумм повреждён"],["INTEGRITY-SOURCE-MISSING",3,"No pristine copy to restore from","Нет эталонной копии для восстановления"],["INTEGRITY-SOURCE-DAMAGED",3,"Pristine copy damaged","Эталонная копия повреждена"],["INTEGRITY-SOURCE-VERSION",3,"Pristine copy is another version","Эталонная копия другой версии"],["INTEGRITY-RESTORE-LIMIT",3,"Restore limit reached","Достигнут предел восстановлений"],["INTEGRITY-RESTORE-FAILED",3,"Restore did not succeed","Восстановление не удалось"],["INTEGRITY-NEVER-RESTORED",3,"Owner data is never restored","Данные владельца не восстанавливаются"],["INTEGRITY-LUA-DAMAGED",3,"Lua files damaged, Python runs","Файлы Lua повреждены, работает Python"],["INTEGRITY-C-MODULE-DAMAGED",3,"C module damaged, pure Lua runs","C-модуль повреждён, работает чистый Lua"],["INTEGRITY-SERVICE-STOPPED",3,"Program damaged, service stays off","Программа повреждена, служба не запущена"],["INTEGRITY-UNVERIFIED",3,"Files not verified","Файлы не проверены"],["INTEGRITY-DEFERRED",3,"Check postponed during installation","Проверка отложена на время установки"],["INTEGRITY-SNAPSHOT-MADE",3,"Pristine copy saved","Эталонная копия сохранена"],["INTEGRITY-SNAPSHOT-REFUSED",3,"Pristine copy not saved","Эталонная копия не сохранена"],["INTEGRITY-SNAPSHOT-NO-SPACE",3,"No space for the pristine copy","Нет места для эталонной копии"],["INTEGRITY-TOOL-MISSING",3,"Self-check tool missing","Нет инструмента самопроверки"],["INTEGRITY-TOOL-DAMAGED",3,"Self-check tool damaged","Инструмент самопроверки повреждён"],["WAN-DOWN",1,"The router has no Internet (WAN)","У роутера нет интернета (WAN)"],["WAN-RECOVERING",1,"Internet is back, checking the VPN","Интернет вернулся, проверка VPN"],["DIAG-TUNNEL-DOWN",1,"Diagnosis: the main tunnel is down","Диагноз: основной туннель не работает"],["DIAG-VPN-SERVER",1,"Diagnosis: the VPN server passes nothing","Диагноз: VPN-сервер ничего не пропускает"],["DIAG-VPN-BOTH-DOWN",1,"Diagnosis: both VPN channels are down, the Internet works","Диагноз: оба VPN не работают, интернет есть"],["DIAG-WAN-SUSPECT",1,"Diagnosis: the Internet is probably down","Диагноз: вероятно, нет интернета"],["DIAG-DNS-FAILED",1,"Diagnosis: DNS fails on both channels","Диагноз: DNS не работает в обоих каналах"],["DIAG-UNSURE",1,"Diagnosis: not sure yet","Диагноз: пока неясно"],["CHANNEL-CONGESTED",1,"The channel's delay is climbing","Задержка канала растёт"],["WEBSITE-*",1,"Website measurement detail","Подробность замера сайтов"],["WEBSITE-IDENTITY-CHANGED",1,"VPN identity changed","Изменилась привязка VPN"],["WEBSITE-DNS-FAILED",1,"Website DNS failed","Не прошёл DNS сайта"],["WEBSITE-HTTP-FAILED",1,"Website HTTP failed","Не прошёл HTTP сайта"],["WEBSITE-TIMEOUT",1,"Website response timed out","Истекло время ответа сайта"],["WEBSITE-TLS-FAILED",1,"Website TLS failed","Не прошёл TLS сайта"],["WEBSITE-RESPONSE-FAILED",1,"Website response failed","Не получен ответ сайта"],["WEBSITE-UNAVAILABLE",1,"Website measurement unavailable","Замер сайтов недоступен"],["WEBSITE-PARTIAL",1,"Only some websites answered","Ответили не все сайты"],["WEBSITE-CHECK-PENDING",1,"Website check pending","Ожидается проверка сайтов"],["WEBSITE-NOT-SELECTED",1,"VPN is outside the measured pair","VPN вне измеряемой пары"],["WEBSITE-DATA-STALE",1,"Website result is old","Замер сайтов устарел"],["WEBSITE-HISTORY-WRITE-FAILED",1,"Website history was not saved","История сайтов не сохранена"],["WEBSITE-HISTORY-UNAVAILABLE",1,"Website history unavailable","История сайтов недоступна"],["WEBSITE-HISTORY-PAIR-LIMIT",1,"Website history pair limit reached","Достигнут лимит пар истории"],["PING-HISTORY-WRITE-FAILED",1,"Ping history was not saved","История пинга не сохранена"],["PING-HISTORY-UNAVAILABLE",1,"Ping history unavailable","История пинга недоступна"],["PING-HISTORY-PAIR-LIMIT",1,"Ping history pair limit reached","Достигнут лимит пар истории"],["KNOWN-STOCK-DERIVED-RECOVERY",8,"Known stock changes reconciled","Служебные изменения учтены"],["RTP-BOOT-PRECONDITION-UNVERIFIED",9,"Router VPN runtime preparation is not confirmed","Не подтверждена штатная подготовка VPN"],["KERNEL-POLICY-VERIFIED",9,"Router VPN rules verified","Правила выбора VPN проверены"],["KERNEL-POLICY-UNVERIFIED",9,"Applied VPN selection rules are unverified","Действующие правила выбора VPN не подтверждены"],["PAIR-POLICY-UNVERIFIED",2,"Primary and reserve VPN policy is unverified","Правила основного и резервного VPN не подтверждены"],["PROBE-SETTINGS-FIELDS",4,"Probe level request is incomplete","Неполный запрос уровня опроса"],["PROBE-SETTINGS-RANGE",4,"Unknown probe level","Неизвестный уровень опроса"],["PROBE-SETTINGS-BUSY",4,"A switch is in progress","Идёт переключение"],["SQM-OFF",3,"SQM on the VPN is off","SQM на VPN выключен"],["SQM-BANDWIDTH-UNSET",3,"SQM is on but has no upload rate","SQM включён, но скорость отдачи не задана"],["SQM-ROOT-QDISC-BUSY",3,"The tunnel already has its own queue","У туннеля уже своя очередь"],["SQM-APPLY-FAILED",3,"SQM could not be applied","SQM не удалось применить"],["SQM-RESTORE-FAILED",3,"SQM could not be removed","SQM не удалось снять"],["PROBE-POLICY-UNAVAILABLE",3,"Probe level state unavailable","Состояние уровня опроса недоступно"],["PROBE-HISTORY-UNAVAILABLE",3,"Decision log unavailable","Журнал решений недоступен"],["PING-PENDING",3,"Ping not measured yet","Пинг ещё не измерен"],["PING-INTERVAL-INVALID",4,"Ping interval not accepted","Интервал пинга не принят"],["RESPONSE-METRIC-INVALID",4,"Unknown response measurement","Неизвестный способ измерения отклика"],["MANUAL-ALREADY-SELECTED",10,"This channel is already selected","Этот канал уже выбран"],["PING-FAILED",1,"No ICMP reply","Нет ответа ICMP"],["PING-DATA-STALE",1,"ICMP result is old","ICMP-результат устарел"],["PING-CHECK-PENDING",1,"Waiting for an ICMP check","Ожидается ICMP-проверка"],["PING-UNAVAILABLE",1,"ICMP measurement is unavailable","ICMP-измерение недоступно"],["PING-INACTIVE",1,"ICMP check is inactive","ICMP-проверка не выполняется"],["PING-IDENTITY-CHANGED",1,"ICMP result belongs to another VPN connection","ICMP-результат относится к другому подключению"],["PING-NOT-SELECTED",1,"VPN is outside the measured pair","VPN не входит в измеряемую пару"],["UI-HELP-LOAD-FAILED",3,"Help could not be loaded","Не удалось загрузить справку"],["PUBLICATION-RECORD-SCOPE",11,"Release record differs from the tested source","Запись выпуска отличается от проверенного исходника"],["PUBLICATION-CI-LUA",11,"The CI receipt does not prove Lua tests ran","Квитанция CI не подтверждает проверку Lua"],["SPEED-PAUSE-UNVERIFIED",6,"Pause could not be verified","Не удалось проверить паузу"],["SPEED-PAUSE-BUSY",6,"Pause recovery in progress","Пауза ещё завершается"],["SPEED-PAUSE-LOST",6,"Pause ownership changed","Условия паузы изменились"],["SPEED-PAUSE-TIMEOUT",6,"Pause acknowledgement timed out","Нет подтверждения паузы"],["SPEED-PAUSE-MODE",6,"Auto transition is not ready for pause","Состояние Auto не готово к паузе"],["SPEED-CPU-UNKNOWN",6,"CPU observation unavailable","Загрузка CPU не прочитана"],["DEVICE-MODEL-INVALID",9,"Choose a supported router model","Выберите поддерживаемую модель"],["DEVICE-MODEL-MISMATCH",9,"Router model does not match","Модель роутера не совпадает"],["MANUAL-FIELDS",10,"Manual request form changed","Форма ручного запроса изменилась"],["MANUAL-DIRECTION-INVALID",10,"Choose a supported direction","Выберите допустимое направление"],["MANUAL-STATE-UNVERIFIED",10,"Manual control state is unknown","Состояние ручного управления неизвестно"],["MANUAL-ALREADY-CLAIMED",10,"Request was already taken","Запрос уже принят в работу"],["MANUAL-REQUEST-EXPIRED",10,"Manual request expired","Время ручного запроса истекло"],["STOP-SUPERSEDED-MANUAL",10,"Stop cancelled the pending switch","Остановка отменила ожидающее переключение"],["MANUAL-CONFIG-CHANGED",10,"Settings changed during the request","Настройки изменились во время запроса"],["MANUAL-SUPERVISOR-UNAVAILABLE",10,"No fresh controller state","Нет свежего состояния контроллера"],["MANUAL-STOP-AUTO-FIRST",10,"Stop Auto before manual switching","Остановите Auto перед ручным переключением"],["MANUAL-SELECTION-UNVERIFIED",10,"Selected pair is not verified","Выбранная пара не проверена"],["MANUAL-REQUEST-PENDING",10,"Another manual request is pending","Другой ручной запрос ещё выполняется"],["MANUAL-REQUEST-UNCONFIRMED",10,"Request was not confirmed","Запрос не подтверждён"],["MANUAL-RESULT-INVALID",10,"Result record is invalid","Запись результата некорректна"],["MANUAL-COMPLETION-UNVERIFIED",10,"Switch completion is not proved","Завершение переключения не доказано"],["RETURN-UNCONFIRMED",10,"Return to primary is unconfirmed","Возврат на основной не подтверждён"],["MANUAL-RESULT-UNCONFIRMED",10,"Manual result is unknown","Результат ручного переключения неизвестен"],["MANUAL-SUPERVISOR-RECOVERED",10,"Controller recovered an unfinished request","Контроллер восстановился после незавершённого запроса"],["MANUAL-TRANSACTION-STATE-UNVERIFIED",10,"The previous switch did not finish","Прошлое переключение не завершилось"],["MANUAL-REQUEST-INVALID",10,"Manual request could not be trusted","Ручному запросу нельзя доверять"],["OPERATOR-MANUAL",10,"Manual-channel control command","Команда ручного выбора канала"],["MT3000-MANUAL-ADAPTER-NOT-CERTIFIED",9,"MT3000 manual switching is not certified","Ручное переключение MT3000 не подтверждено"],["MT3000-COLLECTION-DEADLINE",9,"Readiness check took too long","Проверка готовности заняла слишком много времени"],["MT3000-COLLECTION-CLOCK-CHANGED",9,"Router clock changed during checks","Часы роутера изменились во время проверок"],["MT3000-READ-TIMEOUT",9,"Router read timed out","Чтение данных роутера превысило время"],["MT3000-READ-FAILED",9,"Router evidence could not be read","Не удалось прочитать данные роутера"],["MT3000-READ-UNVERIFIED",9,"Router read could not be validated","Чтение данных роутера не проверено"],["MT3000-PLATFORM-UNVERIFIED",9,"Router model is not verified","Модель роутера не проверена"],["MT3000-FIRMWARE-UNVERIFIED",9,"Router firmware is not verified","Прошивка роутера не проверена"],["MT3000-FIREWALL-UNVERIFIED",9,"Firewall type is not verified","Тип firewall не проверен"],["FW3-INCLUDE-CONTRACT-UNVERIFIED",9,"Firmware firewall integration is unverified","Интеграция firewall прошивки не проверена"],["FW3-RUNTIME-STATE-UNVERIFIED",9,"Live firewall state is unknown","Рабочее состояние firewall неизвестно"],["VENDOR-WORKER-QUIET-UNVERIFIED",9,"Router VPN changes may still be running","Изменение VPN роутером может ещё выполняться"],["NATIVE-CONTROLLER-STATE-UNVERIFIED",9,"Auto controller is not confirmed off","Выключение контроллера Auto не подтверждено"],["SELECTED-RULES-NOT-ADJACENT",9,"Selected VPN rules are not adjacent","Правила выбранных VPN не соседние"],["EXISTING-TUNNEL-BINDING-UNVERIFIED",9,"Working VPN not checked","Рабочий VPN не проверен"],["FW3-SELECTED-ZONE-UNVERIFIED",9,"VPN firewall zone is unverified","Зона firewall VPN не проверена"],["SHARED-KERNEL-BINDING",9,"VPN choices share the same routing resource","Выбранные VPN используют общий ресурс маршрутизации"],["TARGET-ROUTER-PATH-UNVERIFIED",9,"Reserve router checks have not passed","Резерв не прошёл проверки с роутера"],["MT3000-EVIDENCE-UNVERIFIED",9,"MT3000 readiness evidence is incomplete","Данные готовности MT3000 неполны"],["MONITOR-ONLY-DEPLOYMENT",2,"Installation is limited to monitoring","Установка ограничена мониторингом"],["MONITOR-ONLY-INVALID",2,"Deployment mode could not be verified","Не удалось проверить режим установки"],["NATIVE-PROGRESS-UNVERIFIED",2,"Controller progress records are unverified","Записи состояния контроллера не проверены"],["VENDOR-IDENTITY-UNKNOWN",2,"Cannot find this VPN on the router","Не удаётся найти этот VPN на роутере"],["VENDOR-IDENTITY-CHANGED",1,"VPN changed during a check","VPN изменился во время проверки"],["PROFILE-IDENTITY-CHANGED",2,"VPN profile changed","VPN-профиль изменился"],["PAIR-EXTERNAL-POLICY-CHANGE",2,"Route rules differ from the saved session","Правила маршрутов отличаются от сохранённой сессии"],["PAIR-EXTERNAL-NETWORK-CHANGE",2,"Network settings differ from the saved session","Сетевые настройки отличаются от сохранённой сессии"],["PAIR-EXTERNAL-CONFIG-CHANGE",2,"Protected router configuration differs","Защищённая конфигурация роутера отличается"],["PAIR-RECOVERY-REQUIRED",2,"Unfinished switch needs recovery","Незавершённое переключение требует восстановления"],["PAIR-READOPTED",8,"Auto re-read changed settings","Auto заново прочитал изменённые настройки"],["SWITCH-RESULT-UNCONFIRMED",2,"Switch result not confirmed in time","Результат переключения не подтверждён вовремя"],["VENDOR-REASON-UNOBSERVED",1,"Firmware server choice is not visible","Выбор сервера прошивкой не виден"],["AUTOMATIC-EXTERNAL-CHANGE-READOPT",8,"Old Auto session archived automatically","Старая сессия Auto архивирована автоматически"],["STATUS-REQUEST-FAILED",1,"No answer from the router program","Нет ответа от программы на роутере"],["MONITOR-DATA-STALE",1,"Router data is old","Данные роутера устарели"],["VENDOR-OBSERVATION-PENDING",1,"Channel not observed yet","Канал ещё не наблюдался"],["AUTO-CONTROL-UNCONFIRMED",2,"Auto did not confirm the command","Auto не подтвердил команду"],["UI-ACTION-FAILED",1,"The page could not finish the action","Страница не смогла выполнить действие"],["UI-RENDER-FAILED",1,"Part of the page could not be drawn","Часть страницы не удалось показать"],["MANUAL-SWITCH-UNCONFIRMED",2,"Manual switch not confirmed","Ручное переключение не подтверждено"],["STATS-RESET-ARCHIVE-UNVERIFIED",1,"Archive could not be read back","Архив не прочитался обратно"],["STATS-RESET-FIELDS",1,"Reset request not accepted","Запрос сброса не принят"],["STATS-RESET-FAILED",1,"Reset not completed","Сброс не выполнен"],["STATS-RESET-ARCHIVE-PATH",1,"Archive folder is not safe","Папка архива небезопасна"],["STATS-RESET-UNCONFIRMED",1,"Reset not confirmed in time","Сброс не подтверждён вовремя"],["PRIMARY-RECOVERED-BEFORE-SWITCH",8,"The primary recovered before the switch","Основной восстановился до переключения"],["RESERVE-ALREADY-FIRST",8,"The reserve is already the router first choice","Резерв уже стоит первым у роутера"],["CHANNEL-UNRELIABLE",1,"Channel reliability problem","Проблема с надёжностью канала"],["RESERVE-NOT-CONNECTED",2,"Reserve channel is not connected","Резервный канал не подключён"],["VENDOR-SAME-TUNNEL",2,"Server selection belongs to the router","Сервер выбирает штатная прошивка"],["SETUP-SAME-TUNNEL",4,"Choose two different tunnels","Выберите два разных туннеля"],["VENDOR-SETTLING",2,"The router is still checking VPN settings","Роутер ещё проверяет настройки VPN"],["CROSS-TUNNEL-READY",2,"This VPN pair is suitable for Auto","Эта пара VPN подходит для Auto"],["CURRENT-PROFILE-FAILURE-STREAK",2,"Current profile failed repeated checks","Текущий профиль не прошёл несколько проверок"],["RESERVE-IDENTITY-UNKNOWN",2,"Cannot find this VPN on the router","Не удаётся найти этот VPN на роутере"],["VENDOR-FIRST-OBSERVATION",7,"VPN seen for the first time","VPN замечен впервые"],["VENDOR-PROFILE-CHANGED",7,"Configured tunnel member changed","Профиль в конфигурации туннеля изменился"],["VENDOR-BINDING-CHANGED",7,"VPN settings changed","Настройки VPN изменились"],["VENDOR-BINDING-UNKNOWN",7,"VPN profile changed or removed on the router","VPN-профиль изменён или удалён на роутере"],["VENDOR-OBSERVATION-TIME",7,"Invalid observation clock","Некорректное время наблюдения"],["ONBOARDING-FIELDS",4,"Setup form changed","Форма настройки изменилась"],["ONBOARDING-SYSTEM-FIELDS",4,"Check VPN setup","Проверьте настройку VPN"],["ONBOARDING-PAIR-DEFERRED",4,"Review deferred VPN pair","Проверьте отложенную пару VPN"],["ONBOARDING-APPEARANCE",4,"Check appearance defaults","Проверьте оформление по умолчанию"],["ONBOARDING-TELEGRAM-FIELDS",4,"Check optional Telegram setup","Проверьте необязательную настройку Telegram"],["ONBOARDING-TOO-LARGE",4,"Setup request is too large","Запрос настройки слишком большой"],["ONBOARDING-SAVE-UNCONFIRMED",4,"Setup save not confirmed","Сохранение настройки не подтверждено"],["CONTROL-REVISION-STALE",2,"Auto controls changed","Управление Auto изменилось"],["START-STATE-UNVERIFIED",2,"Saved Auto state unverified","Состояние Auto не проверено"],["STOP-SUPERSEDED-START",2,"Pending Start cancelled","Ожидающий запуск отменён"],["START-CONFIG-CHANGED",2,"Settings changed during Start","Настройки изменились при запуске"],["GUARD-RELEASE-ARM-FAILED",2,"Safety timer unavailable","Аварийный таймер недоступен"],["GUARD-RELEASE-UNCONFIRMED",2,"Safety block removal unconfirmed","Снятие блокировки не подтверждено"],["RELEASE-PENDING",8,"Waiting for block removal","Ожидается снятие блокировки"],["RETURN-TRANSACTION-MISMATCH",2,"Old return request rejected","Старый запрос возврата отклонён"],["RETURN-REQUEST-EXPIRED",2,"Return request expired","Запрос возврата устарел"],["JOURNAL-PHASE-INVALID",2,"Invalid recovery phase","Неверная фаза восстановления"],["OBSERVING",8,"Watching the primary","Слежу за основным"],["ARMED",8,"Ready to switch","Готов к переключению"],["APPLYING",8,"Switching now","Идёт переключение"],["WAIT-CLIENT",8,"Waiting for your computer","Ждём ваш компьютер"],["COMMITTED",8,"Reserve confirmed","Резерв подтверждён"],["ROLLED-BACK",8,"Returned to the previous route","Возврат на прежний маршрут"],["ROLLING-BACK",8,"Returning now","Возвращаюсь"],["RESTORING",8,"Restoring the route","Восстанавливаю маршрут"],["TRIAL-REQUIRED",8,"LAN trial needed","Нужен LAN-тест"],["BLOCKED",8,"Blocked","Заблокировано"],["STOPPED",8,"Stopped","Остановлен"],["STOPPED-ON-RESERVE",8,"Stopped on the reserve","Остановлен на резерве"],["DEGRADED-ON-RESERVE",8,"Reserve is failing too","Резерв тоже не работает"],["HELD-ON-RESERVE",8,"Staying on the reserve; Auto keeps watching","Остаюсь на резерве; Auto продолжает наблюдать"],["DISABLED",8,"Auto disabled","Auto выключен"],["EXPIRED",8,"Test window ended","Окно теста закончилось"],["SERVICE-STOPPED",8,"Monitor service is not running","Служба мониторинга не работает"],["WAIT-CONFIRM",8,"Waiting for confirmation","Ожидание подтверждения"],["CLIENT-CONFIRMED",2,"Your computer confirmed","Компьютер подтвердил"],["TRIAL-PASSED",2,"Trial passed","Тест пройден"],["TRIAL-ENDED",2,"Test window ended","Окно теста закончилось"],["SOURCE-FAILED",2,"The primary failed","Основной отказал"],["SOURCE-HEALTH-UNKNOWN",2,"Primary state unknown","Состояние основного неизвестно"],["OPERATOR-TRIAL",2,"Started by you","Запущено вами"],["OPERATOR-HOLD-RESERVE",2,"Held by your rule","Удержание по вашему правилу"],["PRIMARY-STABLY-RECOVERED",2,"Primary recovered for good","Основной стабильно восстановился"],["RESERVE-FAILED",2,"The reserve failed","Резерв отказал"],["RESERVE-FAILED-PRIMARY-VERIFIED",2,"Reserve failed, primary is fine","Резерв отказал, основной исправен"],["RESERVE-HEALTH-UNKNOWN",2,"Reserve state unknown","Состояние резерва неизвестно"],["SOURCE-NOT-VERIFIED",2,"Primary not verified","Основной не проверен"],["SUPERVISOR-RECOVERY",2,"Recovery after a restart","Восстановление после перезапуска"],["SUPERVISOR-FORWARD-RESUMED",2,"Switch finished after a restart","Переключение завершено после перезапуска"],["NOT-PAIR",2,"Restart: not a pair switch","Перезапуск: не переключение пары"],["NOT-AUTOMATIC",2,"Restart: not automatic","Перезапуск: не автоматическое"],["NOT-FORWARD",2,"Restart: not to the reserve","Перезапуск: не на резерв"],["ROLLBACK-STARTED",2,"Restart: rollback begun","Перезапуск: откат начат"],["ALREADY-RESUMED",2,"Restart: already resumed","Перезапуск: уже возобновлялось"],["OTHER-BOOT",2,"Restart: router rebooted","Перезапуск: была перезагрузка"],["OWNER-STOP",2,"Restart: owner Stop","Перезапуск: Стоп владельца"],["SOURCE-NOT-FAILED",2,"Restart: primary not down","Перезапуск: основной не упал"],["RESERVE-NOT-HEALTHY",2,"Restart: reserve not proven","Перезапуск: резерв не подтверждён"],["TRANSACTION-FAILED",2,"The switch failed","Переключение не удалось"],["FAILED-BEFORE-APPLY",2,"Failed before any change","Сбой до изменений"],["TIMEOUT-ELAPSED",2,"Time ran out","Время вышло"],["SELECTED-BY-CONTROLLER",2,"Chosen by the controller","Выбран контроллером"],["EDGE-NOT-CERTIFIED",2,"Works, switch not certified","Работает, переключение не подтверждено"],["THREE-CONFIRMED-FAILURES",2,"Three failures in a row","Три сбоя подряд"],["CONFIGURED-FAILURE-STREAK",2,"Failure streak reached","Достигнут порог сбоев"],["RESTORE-PRIMARY",2,"Return to the primary","Возврат на основной"],["SWITCH-RECOMMENDED",2,"A switch is recommended","Рекомендуется переключение"],["TARGET-INACTIVE",2,"Reserve not connected","Резерв не подключён"],["TARGET-NOT-READY",2,"Reserve not ready","Резерв не готов"],["PLAN-CONFIG",2,"Primary and reserve not chosen","Основной и резерв не выбраны"],["UPLINK-DOWN",2,"Provider line is down","Линия провайдера не работает"],["STOPPED-NO-HEALTHY-PATH",2,"No healthy path","Нет исправного пути"],["GUARD-RETAINED",2,"Safety block kept","Защитная блокировка сохранена"],["WATCHDOG-DID-NOT-ARM",2,"Safety timer did not start","Страхующий таймер не запустился"],["TRANSACTION-EXPIRED",2,"The switch ran out of time","Переключение не уложилось по времени"],["DNS-FAILED",1,"Name lookup fails","Не работает поиск адресов"],["LARGE-PACKETS-FAILED",1,"Large packets are lost","Большие пакеты теряются"],["HTTPS-FAILED",1,"HTTPS checks below threshold","HTTPS-проверки ниже порога"],["TUNNEL-DISCONNECTED",1,"Tunnel not connected","Туннель не подключён"],["ROUTE-MISMATCH",1,"Check did not go through the VPN","Проверка шла не через VPN"],["PATH-UNVERIFIED",1,"Check path unconfirmed","Путь проверки не подтверждён"],["VPN-PROBE-HEALTHY",1,"VPN works","VPN работает"],["OBSERVATION-STALE",1,"Measurements are old","Измерения устарели"],["OBSERVATION-UNKNOWN",1,"Not enough measurements","Мало измерений"],["LINK-UP",1,"Link is up","Линия поднята"],["CHECK-LIMIT",1,"Check limit reached","Достигнут лимит проверок"],["FOREIGN-GUARD-TABLE",2,"Foreign table with our name","Чужая таблица с нашим именем"],["GUARD-CHECK-FAILED",2,"Safety block rejected","Защитная блокировка отклонена"],["GUARD-INSTALL-FAILED",2,"Safety block not installed","Защитная блокировка не установлена"],["GUARD-QUERY-FAILED",2,"Safety block cannot be read","Защитная блокировка не читается"],["POLICY-DUPLICATE-IDENTITY",2,"Two identical VPN rules","Два одинаковых VPN-правила"],["POLICY-GENERATION-CHANGED",2,"Rules changed meanwhile","Правила изменились"],["POLICY-IDENTITY-CHANGED",2,"Rule identity changed","Правило изменилось"],["POLICY-REORDER-UNVERIFIED",2,"New order not confirmed","Новый порядок не подтверждён"],["SOURCE-ORDER-MISMATCH",2,"Rule order is not as expected","Порядок правил не тот"],["EXIT-CHANGED",2,"The exit address changed","Внешний адрес изменился"],["EXIT-IP-NOT-GLOBAL",2,"Exit address is private","Внешний адрес не публичный"],["JOURNAL-ORDER-INVALID",2,"Journal order invalid","Порядок в журнале неверен"],["JOURNAL-SECTION-INVALID",2,"Journal names an invalid rule","Журнал называет неверное правило"],["DEADLINE-TIMEZONE-REQUIRED",2,"Deadline needs a time zone","Для срока нужен часовой пояс"],["INVALID-ACCELERATION-REQUEST",2,"Invalid request","Неверный запрос"],["ACCELERATION-PREPARE-ATTEMPT-LIMIT",2,"Too many preparation attempts","Слишком много попыток подготовки"],["ACCELERATION-PREPARE-DURING-TRANSACTION",2,"Preparation during a switch","Подготовка во время переключения"],["HNAT-DISABLE-UNVERIFIED",2,"Hardware acceleration not confirmed off","Аппаратное ускорение не подтверждено как выключенное"],["SFE-DISABLE-UNVERIFIED",2,"Software acceleration not confirmed off","Программное ускорение не подтверждено как выключенное"],["UNEXPECTED-DEBUGFS-PATH",2,"Unexpected system path","Неожиданный системный путь"],["UNEXPECTED-HNAT-PATH",2,"Unexpected system path","Неожиданный системный путь"],["UNSAFE-FIREWALL-SECTION",2,"Unsafe firewall section name","Небезопасное имя секции брандмауэра"],["UNSAFE-GUARD-DEVICE",2,"Unsafe interface name","Небезопасное имя интерфейса"],["UNSAFE-SECTION",2,"Unsafe rule name","Небезопасное имя правила"],["FAULT-ACTIVE",2,"Failure test is running","Тест сбоя выполняется"],["FAULT-ALREADY-ACTIVE",2,"Failure test already runs","Тест сбоя уже идёт"],["FAULT-CANCELLED",2,"Failure test cancelled","Тест сбоя отменён"],["FAULT-TRANSITION-CONFIRMED",2,"Transition test passed","Тест перехода пройден"],["FAULT-TRANSITION-NOT-CONFIRMED",2,"Transition not confirmed","Переход не подтверждён"],["FAULT-CLEANED",2,"Failure test cleaned up","Тест сбоя убран"],["FAULT-NOT-ACTIVE",2,"No failure test is running","Тест сбоя не идёт"],["FAULT-NATIVE-PREREQUISITES",2,"Router checks not passed","Проверки роутера не пройдены"],["FAULT-SESSION-CONSENT-REQUIRED",2,"Reconnection not allowed","Переподключение не разрешено"],["FAULT-WINDOW-TOO-SHORT",2,"Test window too short","Окно теста слишком короткое"],["FAULT-NOT-CURRENT-SOURCE",2,"Not the current primary","Это не текущий основной"],["FAULT-HEALTHY-RESERVE-REQUIRED",2,"Reserve must be healthy","Нужен исправный резерв"],["FAULT-WOULD-REMOVE-RESERVE",2,"The test would also break the reserve","Тест сломал бы и резерв"],["FAULT-PATH-UNVERIFIED",2,"Path of the VPN not confirmed","Путь VPN не подтверждён"],["FAULT-WATCHDOG-NOT-READY",2,"Safety timer not ready","Страхующий таймер не готов"],["FAULT-UNSAFE-SCOPE",2,"Unsafe scope","Небезопасная область"],["FAULT-FOREIGN-TABLE",2,"Foreign firewall table","Чужая таблица брандмауэра"],["FAULT-TIMEOUT-RULE-FAILED",2,"Automatic end could not be set","Автоматическое окончание не задано"],["FAULT-APPLY-UNCONFIRMED",2,"Block not confirmed","Блокировка не подтверждена"],["FAULT-CLEANUP-UNCONFIRMED",2,"Removal not confirmed","Снятие не подтверждено"],["FAULT-STATE-UNVERIFIED",2,"Test state unverified","Состояние теста не подтверждено"],["FAULT-HISTORY-CORRUPT",2,"Test history damaged","История тестов повреждена"],["FAULT-WORKER-INVALID",2,"Helper process invalid","Вспомогательный процесс недействителен"],["FAULT-WORKER-STALE",2,"Helper process stale","Вспомогательный процесс устарел"],["TELEGRAM-FORMAT-FAILED",5,"Report could not be formed","Отчёт не сформирован"],["TELEGRAM-REPORT-UNAVAILABLE",5,"Report data not available","Данные для отчёта недоступны"],["TELEGRAM-REQUEST-REJECTED",5,"Telegram rejected the request","Telegram отклонил запрос"],["TELEGRAM-RETRY",5,"Will retry","Повторю отправку"],["TELEGRAM-SCHEDULE",5,"Invalid schedule","Неверное расписание"],["TELEGRAM-SETUP-FIELDS",5,"Wrong fields","Неверные поля"],["TELEGRAM-STATE-RECOVERED",5,"Report state recovered","Состояние отчётов восстановлено"],["TELEGRAM-STATE-WRITE-FAILED",5,"Report state not saved","Состояние отчётов не сохранено"],["TELEGRAM-TEST-RATE-LIMIT",5,"Test message too often","Тестовое сообщение слишком часто"],["SETUP-FIELDS",4,"Wrong fields in the form","Неверные поля формы"],["SETUP-KIND",4,"Unknown setup kind","Неизвестный вид настройки"],["SETUP-NAME",4,"Invalid name","Неверное название"],["SETUP-SERVER",4,"Invalid server row","Неверная строка сервера"],["SETUP-DELTA-UNVERIFIED",4,"Unsaved changes unverifiable","Несохранённые изменения не проверить"],["SETUP-CHECK-OK",4,"Settings writer works","Запись настроек работает"],["SETUP-CHECK-FAILED",4,"Settings writer self-check failed","Самопроверка записи настроек не прошла"],["TERMS-VERSION",4,"Terms version mismatch","Версия условий не совпадает"],["MONITOR-PREFERENCES-FIELDS",4,"Wrong fields","Неверные поля"],["PRIORITY-SAVED",4,"Priorities saved","Приоритеты сохранены"],["PRIORITY-SAVE-FAILED",4,"Priorities not saved","Приоритеты не сохранены"],["PRIORITY-STALE-REVIEW",4,"The review is outdated","Просмотр устарел"],["PRIORITY-FIELDS",4,"Wrong fields","Неверные поля"],["PRIORITY-INVALID-SELECTION",4,"Invalid selection","Неверный выбор"],["PRIORITY-PROFILE-INELIGIBLE",4,"Server not eligible","Сервер не подходит"],["RECOVERY-FIELDS",4,"Wrong fields","Неверные поля"],["RECOVERY-RANGE",4,"Value out of range","Значение вне диапазона"],["RECOVERY-REQUIRED",4,"Recovery rules required","Нужны правила восстановления"],["RECOVERY-RETURN-POLICY",4,"Invalid return rule","Неверное правило возврата"],["CONFIG-STOP-AUTO-FIRST",4,"Stop Auto first","Сначала остановите Auto"],["CONFIG-RECOVERY-UNVERIFIED",4,"Configuration cannot be confirmed","Конфигурацию не подтвердить"],["CONFIG-STORAGE-FREE",7,"Not enough free space","Мало свободного места"],["LIFECYCLE-STOP-AUTO-FIRST",3,"Stop Auto first","Сначала остановите Auto"],["STORAGE-001",7,"Router storage problem","Проблема с хранилищем роутера"],["STORAGE-RECOVERED",7,"Storage recovered","Хранилище восстановлено"],["SCAN-MEASUREMENT-FAILED",6,"Check request failed","Запрос проверки не удался"],["SCAN-SNAPSHOT-MISMATCH",6,"Measurement does not match","Измерение не совпало"],["SCAN-STORAGE",6,"Request not saved","Запрос не сохранён"],["RPC-DUPLICATE-FIELD",3,"Duplicate field in a request","Повтор поля в запросе"],["RPC-INPUT-COMPLEXITY",3,"Request too complex","Запрос слишком сложный"],["RPC-INPUT-DEPTH",3,"Request too deep","Запрос слишком вложенный"],["RPC-INPUT-OBJECT",3,"Request has a wrong form","Запрос неверного вида"],["RPC-UNCONFIRMED",3,"Button result not confirmed","Результат кнопки не подтверждён"],["STATS-SETTINGS-FIELDS",3,"Statistics setting not accepted","Настройка статистики не принята"],["STATS-RETENTION-FIELDS",3,"Statistics storage choice not accepted","Выбор хранения статистики не принят"],["STATS-RETENTION-DAYS",3,"Statistics period not accepted","Срок хранения статистики не принят"],["STATS-RETENTION-SIZE",3,"Statistics size limit not accepted","Ограничение объёма статистики не принято"],["LUA-CORE-UNAVAILABLE",2,"Lua core did not answer","Ядро Lua не ответило"],["JOURNAL-DELEGATED-UNVERIFIED",2,"Switch journal from Python not accepted by Lua","Журнал от Python не принят ядром Lua"],["CONTROL-LOCK-UNAVAILABLE",2,"Control lock not available","Блокировка управления недоступна"],["CONTROL-LOCK-REENTRY",2,"Control lock taken twice","Повторный захват блокировки"],["COMMAND-FAILED",2,"System command failed","Системная команда не выполнилась"],["LUA-AUTO-FALLBACK",2,"Lua Auto handed over to Python","Auto на Lua передал работу Python"],["BRIDGE-REQUEST-INVALID",2,"Lua probe bridge refused the request","Мост проверки Lua отклонил запрос"],["STATE-FILE-DAMAGED",2,"Saved state file damaged","Файл сохранённого состояния повреждён"],["RPC-NONFINITE-NUMBER",3,"Invalid number","Неверное число"],["OFFLINE-FIXTURE",7,"Test data of the offline preview","Тестовые данные офлайн-просмотра"],["AUTO-STOP-QUEUED",2,"Stop was queued","Остановка поставлена в очередь"],["RETURN-REFUSED",2,"Return refused","Возврат отклонён"],["RECOVERY-SAVED",4,"Recovery rules saved","Правила восстановления сохранены"],["RECOVERY-SAVE-FAILED",4,"Recovery rules not saved","Правила восстановления не сохранены"],["RECOVERY-SAVE-UNCONFIRMED",4,"Save not confirmed","Сохранение не подтверждено"],["SPEED-CONFIG-SAVED",6,"Speed settings saved","Настройки скорости сохранены"],["SPEED-CONFIG-FAILED",6,"Speed settings not saved","Настройки скорости не сохранены"],["SPEED-QUEUED",6,"Speed test queued","Тест скорости поставлен в очередь"],["SPEED-START-FAILED",6,"Speed test did not start","Тест скорости не запустился"],["SPEED-CANCEL-QUEUED",6,"Cancel queued","Отмена поставлена в очередь"],["SCAN-ACK-UNCONFIRMED",6,"Check request not confirmed","Запрос проверки не подтверждён"],["SCAN-SNAPSHOT-UNCONFIRMED",6,"Result not confirmed","Результат не подтверждён"],["MONITOR-PREFERENCES-SAVED",4,"Monitoring preferences saved","Параметры мониторинга сохранены"],["MONITOR-PREFERENCES-FAILED",4,"Monitoring preferences not saved","Параметры мониторинга не сохранены"],["MONITOR-PREFERENCES-UNCONFIRMED",4,"Save not confirmed","Сохранение не подтверждено"],["MONITOR-UNKNOWN",3,"Monitor answer unknown","Ответ мониторинга неизвестен"],["PRIORITY-PREVIEW-FAILED",4,"Preview failed","Просмотр не удался"],["PRIORITY-PREVIEW-UNCONFIRMED",4,"Preview not confirmed","Просмотр не подтверждён"],["PRIORITY-RPC-UNCONFIRMED",4,"Answer not confirmed","Ответ не подтверждён"],["PRIORITY-SELECT-ELIGIBLE-SERVERS",4,"Choose servers first","Сначала выберите серверы"],["PRIORITY-UNKNOWN",4,"Priority answer unknown","Ответ по приоритетам неизвестен"],["RECOVERY-PERIOD",4,"Invalid period","Неверный период"],["RPC-INVENTORY-INVALID",3,"Router list unreadable","Список роутера нечитаем"],["RPC-INVENTORY-UNAVAILABLE",3,"Router list unavailable","Список роутера недоступен"],["TELEGRAM-FORGET-UNCONFIRMED",5,"Token removal not confirmed","Удаление токена не подтверждено"],["TERMS-SAVE-FAILED",4,"Terms not saved","Условия не сохранены"],["TERMS-SAVE-UNCONFIRMED",4,"Acceptance not confirmed","Принятие не подтверждено"],["CAUSE-UNKNOWN",7,"Cause not known","Причина неизвестна"],["UNKNOWN-FUTURE-TIMESTAMP",7,"Time in the future","Время из будущего"],["EXPORT-KIND",7,"Unknown export","Неизвестный экспорт"],["DEPENDENCY-IP",3,"Program “ip” missing","Нет программы «ip»"],["DEPENDENCY-LUA",3,"Lua missing","Нет Lua"],["DEPENDENCY-UBUS",3,"ubus missing","Нет ubus"],["DEPENDENCY-UCI",3,"UCI missing","Нет UCI"],["SPEED-COMPLETE",6,"Speed test finished","Тест скорости завершён"],["SPEED-NOT-RUNNING",6,"No speed test is running","Тест скорости не идёт"],["SPEED-NO-SAMPLE",6,"No measurement","Нет измерения"],["SPEED-CPU-BUSY",6,"Router is busy","Роутер занят"],["SPEED-TRAFFIC-UNKNOWN",6,"Traffic unknown","Трафик неизвестен"],["SPEED-SWITCH-IN-PROGRESS",6,"A switch is running","Идёт переключение"],["SPEED-PROFILES",6,"No server chosen","Сервер не выбран"],["SPEED-PROFILES-CHANGED",6,"Server list changed","Список серверов изменился"],["SPEED-CONFIG-LIMIT",6,"Limit exceeded","Лимит превышен"],["AUTO-OPTIONS-NOT-CLEARED",2,"Auto settings could not be reset","Настройки Auto не удалось сбросить"],["BOARD-OVERSIZE",3,"Router board data too big","Данные о плате роутера слишком велики"],["CA-BUNDLE",3,"Certificates package missing","Нет пакета сертификатов"],["LUCI-CACHE-ROOT",3,"Page cache folder is wrong","Папка кэша страниц неверна"],["PYTHON-39-MINIMUM",3,"Python is too old","Python слишком старый"],["SPEED-WORKER-TIMEOUT",6,"Test took too long","Тест шёл слишком долго"],["PAIR-WATCHING",8,"Auto is watching both channels","Auto наблюдает за обоими каналами"],["PAIR-WAITING-PROBES",8,"Auto is collecting the first checks","Auto собирает первые проверки"],["PAIR-CONNECTING",8,"Connecting the second channel","Подключаю второй канал"],["PAIR-CLEANUP",8,"Putting the route back in order","Привожу маршрут в порядок"],["PAIR-WAITING-VENDOR",8,"Waiting for the router VPN data","Жду данные VPN от роутера"],["PAIR-MANUAL-HOLD-RESERVE",8,"Reserve chosen manually; Auto keeps watching","Резерв выбран вручную; Auto продолжает наблюдать"],["PAIR-MANUAL-HOLD-PRIMARY",8,"Primary chosen manually; Auto keeps watching","Основной выбран вручную; Auto продолжает наблюдать"],["PAIR-MANUAL-HOLD-UNVERIFIED",2,"Manual choice could not be confirmed","Ручной выбор не удалось подтвердить"],["PAIR-MANUAL-RECOVERED",2,"Interrupted manual switch cleared","Прерванное ручное переключение снято"],["PAIR-MANUAL-BUSY",2,"Another switch is in progress","Уже идёт другое переключение"],["PAIR-MANUAL-COOLDOWN",2,"Short pause between manual switches","Короткая пауза между ручными переключениями"],["PAIR-MANUAL-EXPIRED",2,"Manual request expired","Ручной запрос устарел"],["PAIR-MANUAL-FIELDS",2,"Manual request was malformed","Ручной запрос составлен неверно"],["PAIR-MANUAL-NOT-AVAILABLE",2,"Manual switch is not available now","Ручное переключение сейчас недоступно"],["PAIR-MANUAL-REQUEST-UNCONFIRMED",2,"Manual request not confirmed","Ручной запрос не подтверждён"],["PAIR-MANUAL-STALE",2,"Router data is too old for a manual switch","Данные роутера устарели для ручного переключения"],["PAIR-MANUAL-STATE-UNVERIFIED",2,"Cannot confirm the state for a manual switch","Не удаётся подтвердить состояние для ручного переключения"],["PAIR-MANUAL-TARGET-UNHEALTHY",2,"The chosen channel does not pass its checks","Выбранный канал не проходит проверки"],["PAIR-MANUAL-UNCONFIRMED",2,"Manual switch not confirmed","Ручное переключение не подтверждено"],["PAIR-RATE-LIMIT",2,"Many switches; Auto holds the reserve longer","Частые переключения; Auto дольше держит резерв"],["PAIR-MODE-NOT-CONFIGURED",4,"Two-channel Auto is not set up","Авторежим двух каналов не настроен"],["PAIR-PLATFORM-UNVERIFIED",2,"Router platform not confirmed","Платформа роутера не подтверждена"],["PAIR-READINESS-CHANGED",2,"Readiness changed while Auto was working","Готовность изменилась во время работы Auto"],["PAIR-STOPPED",8,"Auto was stopped and the route restored","Auto остановлен, маршрут восстановлен"],["PAIR-SYSTEM-001",11,"Unexpected internal error in Auto","Неожиданная внутренняя ошибка Auto"],["PAIR-BUDGET-UNVERIFIED",11,"Switch limit record is unreadable","Запись о лимите переключений нечитаема"],["PAIR-CONFIG-UNVERIFIED",11,"Saved Auto settings not confirmed","Сохранённые настройки Auto не подтверждены"],["PAIR-INTENT-UNVERIFIED",11,"Unfinished switch record not confirmed","Запись о незавершённом переключении не подтверждена"],["PAIR-NETWORK-UNVERIFIED",11,"Network state not confirmed","Состояние сети не подтверждено"],["PAIR-NETWORK-WRITE-FAILED",2,"Could not write the network settings","Не удалось записать сетевые настройки"],["PAIR-NETWORK-WRITE-UNVERIFIED",2,"Network settings write not confirmed","Запись сетевых настроек не подтверждена"],["PAIR-PROFILE-STOP-UNVERIFIED",2,"Could not confirm the extra VPN stopped","Не удалось подтвердить остановку лишнего VPN"],["RESPONSE-COMPARE-UNAVAILABLE",7,"Method comparison is unavailable","Сравнение способов недоступно"],["RESPONSE-COMPARE-WRITE-FAILED",7,"Method comparison was not saved","Сравнение способов не сохранено"],["RESPONSE-COMPARE-SCHEMA",7,"Method comparison file has the wrong form","Файл сравнения способов в неверном виде"],["RESPONSE-COMPARE-SIZE",7,"Method comparison file is too large","Файл сравнения способов слишком велик"],["RESPONSE-COMPARE-VALUE",7,"Method comparison has a wrong value","В сравнении способов неверное значение"],["PING-HISTORY",7,"Ping history problem","Проблема истории пинга"],["LATENCY-HISTORY-UNAVAILABLE",7,"Delay history is unavailable","История задержки недоступна"],["LATENCY-HISTORY-WRITE-FAILED",7,"Delay history was not saved","История задержки не сохранена"],["LIFECYCLE-READY",3,"Ready for an upgrade check passed","Проверка перед обновлением пройдена"],["LIFECYCLE-UPGRADE-READY",3,"Ready to upgrade","Готово к обновлению"],["LIFECYCLE-AUTO-DISABLED",3,"Auto was switched off for the upgrade","Auto выключен на время обновления"],["LIFECYCLE-AUTO-DISABLE-FAILED",3,"Could not switch Auto off","Не удалось выключить Auto"],["LIFECYCLE-ACTION",3,"Unknown service action","Неизвестное действие службы"],["LIFECYCLE-CONFIG-UNVERIFIED",3,"Settings not confirmed before the upgrade","Настройки не подтверждены перед обновлением"],["LIFECYCLE-CONTROL-BUSY",3,"Another control action is running","Выполняется другое управляющее действие"],["LIFECYCLE-CONTROL-UNVERIFIED",3,"Control state not confirmed","Состояние управления не подтверждено"],["LIFECYCLE-JOURNAL-ACTIVE",3,"A switch is still unfinished","Переключение ещё не завершено"],["LIFECYCLE-JOURNAL-UNVERIFIED",3,"Switch journal not confirmed","Журнал переключений не подтверждён"],["LIFECYCLE-PENDING-UCI-CHANGES",3,"Unsaved router settings exist","Есть неприменённые настройки роутера"],["LIFECYCLE-STATE-UNVERIFIED",3,"Program state not confirmed","Состояние программы не подтверждено"],["PREPARATION-VERIFIED",4,"Router preparation verified","Подготовка роутера подтверждена"],["PREPARATION-UNVERIFIED",4,"Router preparation not confirmed","Подготовка роутера не подтверждена"],["PREPARATION-STOP-AUTO-FIRST",4,"Stop Auto before changing the preparation","Остановите Auto перед сменой подготовки"],["PREPARATION-STALE-REVIEW",4,"The review is out of date","Проверка устарела"],["PREPARATION-EXTERNAL-CHANGE",4,"Router settings changed from outside","Настройки роутера изменены снаружи"],["PREPARATION-PENDING-OR-UNREADABLE",4,"Router settings pending or unreadable","Настройки роутера ожидают применения или нечитаемы"],["PREPARATION-WRITE-UNCONFIRMED",4,"Preparation write not confirmed","Запись подготовки не подтверждена"],["PREPARATION-AUTOLOAD-UNVERIFIED",4,"Startup loading not confirmed","Автозагрузка не подтверждена"],["PREPARATION-BACKUP-UNVERIFIED",4,"Backup copy not confirmed","Резервная копия не подтверждена"],["PREPARATION-BINDING-UNVERIFIED",4,"Preparation does not match this router","Подготовка не соответствует этому роутеру"],["PREPARATION-BOOT-UNVERIFIED",4,"Start-at-boot not confirmed","Запуск при загрузке не подтверждён"],["PREPARATION-FIELDS",4,"Preparation request was malformed","Запрос подготовки составлен неверно"],["PREPARATION-FILE-UNVERIFIED",4,"A program file is not confirmed","Файл программы не подтверждён"],["PREPARATION-FIREWALL-UNVERIFIED",4,"Firewall rules not confirmed","Правила файрвола не подтверждены"],["PREPARATION-HISTORY-LIMIT",4,"Too many preparation records","Слишком много записей подготовки"],["PREPARATION-HNAT-UNVERIFIED",4,"Hardware acceleration not confirmed off","Аппаратное ускорение не подтверждено выключенным"],["PREPARATION-PLATFORM-UNVERIFIED",4,"Router model not confirmed","Модель роутера не подтверждена"],["PREPARATION-VALUE-UNVERIFIED",4,"A setting value is not confirmed","Значение настройки не подтверждено"],["FAULT-CERTIFICATE-STALE",2,"Failure test approval expired","Разрешение теста сбоя устарело"],["FAULT-CLAIM-STALE",2,"Failure test request expired","Запрос теста сбоя устарел"],["FAULT-COMMAND-UNCONFIRMED",2,"Test command not confirmed","Команда теста не подтверждена"],["FAULT-CONTROL-CHANGED",2,"Test control changed meanwhile","Управление тестом изменилось"],["FAULT-IDENTITY-GONE",2,"Tested VPN disappeared","Проверяемый VPN исчез"],["FAULT-IDENTITY-UNVERIFIED",2,"Tested VPN not confirmed","Проверяемый VPN не подтверждён"],["FAULT-START-UNCONFIRMED",2,"Test start not confirmed","Запуск теста не подтверждён"],["RPC-RATE-LIMIT",3,"Too many requests, wait a moment","Слишком много запросов, подождите"],["RPC-INPUT-INVALID",3,"Request has a wrong value","В запросе неверное значение"],["RPC-UNKNOWN-METHOD",3,"The router does not know this request","Роутер не знает такой запрос"],["RPC-UNEXPECTED-ARGS",3,"Request has extra data","В запросе лишние данные"],["RPC-CONFIRM-NO-PENDING",3,"Nothing is waiting for confirmation","Нечего подтверждать"],["RPC-CONFIRM-EXPIRED",3,"Confirmation came too late","Подтверждение пришло слишком поздно"],["RPC-CONFIRM-ADDRESS",3,"Confirmation came from another address","Подтверждение пришло с другого адреса"],["RPC-CONFIRM-FIELDS",3,"Confirmation was malformed","Подтверждение составлено неверно"],["RPC-CONFIRM-TRANSACTION",3,"Confirmation is for another switch","Подтверждение относится к другому переключению"],["RPC-CONFIRM-TRIAL",3,"Confirmation is for another test","Подтверждение относится к другому тесту"],["RPC-CONFIRM-UNVERIFIED",3,"Confirmation not verified","Подтверждение не проверено"],["SPEED-ADDRESS",6,"Speed test server address refused","Адрес сервера теста скорости отклонён"],["SPEED-AUTO-DISABLED",6,"Speed test needs Auto off or ready","Тест скорости недоступен при таком состоянии Auto"],["SPEED-CANCEL-UNVERIFIED",6,"Test cancel not confirmed","Отмена теста не подтверждена"],["SPEED-CLOCK-BACKWARD",6,"Router clock went back","Часы роутера пошли назад"],["SPEED-CLOCK-UNSET",6,"Router clock is not set","Часы роутера не установлены"],["SPEED-CONFIG",6,"Speed test settings are out of range","Настройки теста скорости вне диапазона"],["SPEED-CONFIG-FIELDS",6,"Speed test settings were malformed","Настройки теста скорости составлены неверно"],["SPEED-DNS",6,"Speed test name not resolved","Имя сервера теста скорости не найдено"],["SPEED-HISTORY-CORRUPT",6,"Speed history unreadable","История скорости нечитаема"],["SPEED-HTTP",6,"Speed test server answered with an error","Сервер теста скорости ответил ошибкой"],["SPEED-MONITOR-UNAVAILABLE",6,"Monitor is not available for the speed test","Мониторинг недоступен для теста скорости"],["SPEED-QUOTA-CORRUPT",6,"Speed test limit record unreadable","Запись лимита теста скорости нечитаема"],["SPEED-REQUEST",6,"Speed test request is wrong","Запрос теста скорости неверен"],["SPEED-RESPONSE-LIMIT",6,"Speed test download limit reached","Достигнут лимит скачивания теста"],["SPEED-SHORT-RESPONSE",6,"Speed test answer too short","Ответ сервера теста слишком короткий"],["SPEED-STATUS-UNAVAILABLE",6,"Speed test status unavailable","Состояние теста скорости недоступно"],["SPEED-SYSTEM",6,"Speed test system error","Системная ошибка теста скорости"],["SPEED-WORKER-LOST",6,"Speed test worker stopped","Исполнитель теста скорости остановился"],["SPEED-WORKER-START",6,"Speed test could not start","Тест скорости не удалось запустить"],["POLICY-CHANGED-DURING-PREFLIGHT",2,"VPN rules changed during the check","Правила VPN изменились во время проверки"],["RECOVERY-ACTION",3,"Unknown recovery action","Неизвестное действие восстановления"],["TELEGRAM-ITEMS",5,"Telegram report items are wrong","Состав отчёта Telegram неверен"],["ENDPOINT-ADDRESS",7,"Server address not valid","Адрес сервера недопустим"],["ENDPOINT-PROC",7,"Server address could not be read","Адрес сервера не удалось прочитать"],["ENDPOINT-PROCESS-EPOCH",7,"Server address changed while reading","Адрес сервера изменился при чтении"],["ENDPOINT-READ-LIMIT",7,"Server address table too large","Таблица адреса сервера слишком велика"],["FLOW-RESET-*",2,"Ending old connections after a switch","Завершение старых соединений после переключения"],["AUTO-RESUME-*",2,"Auto resume after a reboot","Возобновление Auto после перезагрузки"],["FAST-*",2,"Fast switch not used","Быстрое переключение не применено"],["RESPONSE-COMPARE*",7,"Comparison of response methods","Сравнение способов отклика"],["PING-HISTORY*",7,"Ping history check","Проверка истории пинга"],["PREPARATION-*",4,"Router preparation action","Действие подготовки роутера"],["LATENCY-*",7,"Delay history unavailable","История задержки недоступна"],["ENDPOINT-*",7,"Current server address not observed","Текущий адрес сервера не получен"],["STATISTICS-*",7,"Saved statistics check","Проверка сохранённой статистики"],["PREP-*",9,"Persistent router preparation (PREP-…)","Постоянная подготовка роутера (PREP-…)"],["PAIR-*",11,"Two-channel Auto (PAIR-…)","Авторежим двух каналов (PAIR-…)"],["CASCADE-*",11,"Internal check of the fallback model (CASCADE-…)","Внутренняя проверка модели каскада (CASCADE-…)"],["CANDIDATE-*",11,"Internal check of candidate probing (CANDIDATE-…)","Внутренняя проверка пробы кандидатов (CANDIDATE-…)"],["MODEL-*",11,"Internal check of the switching model (MODEL-…)","Внутренняя проверка модели переключения (MODEL-…)"],["CHECKPOINT-*",7,"Saved statistics file check (CHECKPOINT-…)","Проверка файла сохранённой статистики (CHECKPOINT-…)"],["MIGRATION-*",7,"Settings upgrade check (MIGRATION-…)","Проверка обновления настроек (MIGRATION-…)"],["HISTORY-*",7,"Controller history check (HISTORY-…)","Проверка истории контроллера (HISTORY-…)"],["LIFECYCLE-*",3,"Upgrade and service safety check (LIFECYCLE-…)","Проверка безопасности обновления и службы (LIFECYCLE-…)"],["SPEED-*",6,"Speed test code (SPEED-…)","Код теста скорости (SPEED-…)"],["FAULT-*",2,"Failure test code (FAULT-…)","Код теста сбоя (FAULT-…)"],["TELEGRAM-*",5,"Telegram code (TELEGRAM-…)","Код Telegram (TELEGRAM-…)"],["SETUP-*",4,"Settings code (SETUP-…)","Код настроек (SETUP-…)"],["ADVISOR-*",4,"Auto-adaptation code (ADVISOR-…)","Код автоподстройки (ADVISOR-…)"],["PRIORITY-*",4,"Priorities code (PRIORITY-…)","Код приоритетов (PRIORITY-…)"],["RECOVERY-*",4,"Recovery rules code (RECOVERY-…)","Код правил восстановления (RECOVERY-…)"],["RPC-*",3,"Request to the router (RPC-…)","Запрос к роутеру (RPC-…)"],["SCAN-*",6,"Check request code (SCAN-…)","Код запроса проверки (SCAN-…)"],["DEPENDENCY-*",3,"Missing program (DEPENDENCY-…)","Не хватает программы (DEPENDENCY-…)"],["GUARD-*",2,"Safety block code (GUARD-…)","Код защитной блокировки (GUARD-…)"],["POLICY-*",2,"VPN rules code (POLICY-…)","Код VPN-правил (POLICY-…)"],["JOURNAL-*",2,"Switch journal code (JOURNAL-…)","Код журнала переключения (JOURNAL-…)"],["UNSAFE-*",2,"Unsafe name (UNSAFE-…)","Небезопасное имя (UNSAFE-…)"],["GUARD-DEVICE-UNVERIFIED",2,"VPN interface state unavailable","Состояние VPN-интерфейса недоступно"],["LAN-TRIAL-REQUIRED",2,"LAN trial required","Нужен LAN-тест"],["BOUNDED-DEADLINE-REQUIRED",2,"Test window missing","Нет окна теста"],["SESSION-LOSS-NOT-ACCEPTED",2,"Reconnection not accepted","Не разрешён разрыв сессий"],["TRANSACTION-IN-PROGRESS",2,"Switch in progress","Переключение идёт"],["TRIAL-ATTEMPT-LIMIT",2,"Trial attempt limit","Лимит попыток теста"],["UNSUPPORTED-BOARD",2,"Unsupported router model","Неподдерживаемая модель роутера"],["UNSUPPORTED-FIRMWARE",2,"Unsupported firmware","Неподдерживаемая прошивка"],["FIRMWARE-UNKNOWN",2,"Firmware unknown","Прошивка неизвестна"],["VENDOR-CODE-CHANGED",2,"GL.iNet code changed","Код GL.iNet изменился"],["VENDOR-CODE-UNVERIFIED",2,"GL.iNet code unverified","Код GL.iNet не проверен"],["VENDOR-WORKER-BUSY",2,"GL.iNet program is busy","Программа GL.iNet занята"],["HARDWARE-ACCELERATOR-UNVERIFIED",2,"Hardware acceleration unverified","Аппаратное ускорение не проверено"],["SOFTWARE-ACCELERATOR-UNVERIFIED",2,"Software acceleration unverified","Программное ускорение не проверено"],["FLOW-OFFLOAD-ENABLED",2,"Flow offload is on","Включён flow offload"],["IPV6-NOT-EXPLICITLY-DISABLED",2,"IPv6 not disabled","IPv6 не отключён"],["KILLSWITCH-NOT-ENABLED",2,"Kill Switch is off","Kill Switch выключен"],["DIRECT-WAN-FALLBACK",2,"Direct exit without VPN possible","Возможен выход мимо VPN"],["VPN-POLICY-DISABLED",2,"VPN policy is off","Политика VPN выключена"],["TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED",2,"Two to sixteen rules needed","Нужно от 2 до 16 правил VPN"],["GENERIC-RULES-NOT-ADJACENT",2,"Rules not adjacent","Правила идут не подряд"],["GENERIC-DUPLICATE-INTERFACE",2,"Duplicate interface","Повтор интерфейса"],["SPECIAL-RULES-MUST-PRECEDE-GENERIC",2,"Special rules in wrong order","Особые правила в неверном порядке"],["SOURCE-RESERVE-NOT-CONFIGURED",2,"Primary or reserve not set","Основной или резерв не заданы"],["PROFILE-INACTIVE",2,"Profile not connected","Профиль не подключён"],["PROFILES-NOT-GENERIC-RULES",2,"Profiles not in general rules","Профили не в общих правилах"],["SAME-INTERFACE",2,"Same interface twice","Один интерфейс дважды"],["POLICY-ORDER-DIRECTION-UNVERIFIED",2,"Rule order direction unverified","Направление порядка правил не проверено"],["LAN-LAYOUT-UNSUPPORTED",2,"Unsupported LAN layout","Неподдерживаемая схема LAN"],["PROFILE-NOT-MONITORED",2,"Profile not monitored","Профиль не наблюдается"],["NFT-GUARD-UNAVAILABLE",2,"Safety block unavailable","Страхующая блокировка недоступна"],["POLICY-READ-FAILED",2,"Cannot read VPN rules","Не удаётся прочитать правила VPN"],["UPLINK-LINK-DOWN",2,"Uplink is down","Внешний канал отключён"],["LEASE-INTEGRITY-FAILED",2,"Lease damaged","Аренда повреждена"],["LEASE-STORAGE-FAILED",2,"Lease cannot be saved","Аренда не сохраняется"],["LEGACY-LEASE-RECOVERY",2,"Old lease recovered","Восстановлена старая аренда"],["EXTERNAL-POLICY-CHANGE-GUARD-RETAINED",2,"Outside change, block kept","Изменение извне, блокировка сохранена"],["ROLLBACK-UNVERIFIED-GUARD-RETAINED",2,"Return unverified, block kept","Возврат не подтверждён, блокировка сохранена"],["CLIENT-CONFIRMATION-TIMEOUT",2,"Computer did not confirm","Компьютер не подтвердил"],["CLIENT-STOP",2,"Stopped by the helper","Остановлено помощником"],["TARGET-HTTPS-DNS-FAILED",2,"Reserve check failed","Проверка резерва не прошла"],["LAN-BASELINE-NOT-SOURCE",2,"Computer was not on the primary","Компьютер был не на основном"],["RESERVE-EXIT-NOT-DISTINCT",2,"Reserve exit equals primary","Выход резерва совпал с основным"],["VENDOR-APPLY-FAILED",2,"GL.iNet did not apply the change","GL.iNet не применил изменение"],["POLICY-CHANGED-DURING-APPLY",2,"Rules changed during the switch","Правила изменились во время переключения"],["NATIVE-SYSTEM-001",2,"System check failed","Проверка системы не прошла"],["TERMS-NOT-ACCEPTED",2,"Terms not accepted","Условия не приняты"],["RETURN-NOT-APPLICABLE",2,"Nothing to return","Возвращать нечего"],["SOURCE-NOT-HEALTHY",2,"Primary not healthy yet","Основной ещё не исправен"],["JOURNAL-UNVERIFIED",2,"Journal unverified","Журнал не проверен"],["EXTERNAL-POLICY-CHANGE",2,"Changed from outside","Изменено извне"],["EXTERNAL-POLICY-CHANGE-RELEASED",2,"Changed from outside, block removed","Изменено извне, блокировка снята"],["ROLLBACK-UNVERIFIED",2,"Return unverified","Возврат не подтверждён"],["ENVIRONMENT-EVIDENCE-UNAVAILABLE",2,"No data about the router","Нет данных о роутере"],["MONITOR-EVIDENCE-STALE",2,"Monitor data is old","Данные мониторинга устарели"],["NATIVE-START-CERTIFICATION-REQUIRED",2,"Checked again at Start","Повторная проверка при запуске"],["OPERATOR-RETURN",2,"Return-control command","Команда возврата маршрута"],["PRIMARY-RECOVERED",2,"Primary recovered","Основной восстановился"],["PAIR-STATE-UNVERIFIED",2,"Unfinished switch needs recovery","Незавершённое переключение требует восстановления"],["PAIR-PROFILES-UNVERIFIED",2,"Review the current VPN pair","Проверьте текущую пару VPN"],["PAIR-PREPARATION-REQUIRED",2,"Complete router preparation","Завершите подготовку роутера"],["PREP-HNAT-CONFIG",2,"Disable network acceleration","Отключите сетевое ускорение"],["PREP-WGCLIENT1-AUTOSTART",2,"Review wgclient1 startup","Проверьте автозапуск wgclient1"],["PREP-OVPNCLIENT1-AUTOSTART",2,"Review ovpnclient1 startup","Проверьте автозапуск ovpnclient1"],["PREP-STOCK-VPN-BOOT",2,"Disable competing VPN startup","Отключите конкурирующий автозапуск VPN"],["PREP-SFE-BOOT",2,"Disable network acceleration","Отключите сетевое ускорение"],["PREP-SFE-AUTOLOAD",2,"Disable network acceleration","Отключите сетевое ускорение"],["PREP-SFE-RUNTIME",2,"Disable network acceleration","Отключите сетевое ускорение"],["PREPARATION-RESTART-REQUIRED",2,"Router restart required","Нужна перезагрузка роутера"],["PREPARATION-RECOVERY-REQUIRED",2,"Complete router preparation","Завершите подготовку роутера"],["PREP-SOURCE-AUTOSTART",2,"Disable primary VPN boot startup","Отключите автозапуск основного VPN"],["PREP-TARGET-AUTOSTART",2,"Disable reserve VPN boot startup","Отключите автозапуск резервного VPN"],["GL-ADAPTER-UNVERIFIED",2,"GL.iNet VPN manager","Менеджер VPN GL.iNet"],["WORKER-COORDINATION-UNVERIFIED",2,"GL.iNet background programs","Фоновые программы GL.iNet"],["LAN-PATH-UNVERIFIED",2,"Path of a home computer","Путь домашнего компьютера"],["DNS-POLICY-UNVERIFIED",2,"Name lookups (DNS)","Поиск адресов (DNS)"],["KILLSWITCH-UNVERIFIED",2,"Kill Switch","Kill Switch"],["IPV6-POLICY-UNVERIFIED",2,"IPv6 traffic","Трафик IPv6"],["WATCHDOG-UNVERIFIED",2,"Safety timer","Страхующий таймер"],["SCOPED-CONNTRACK-UNVERIFIED",2,"Open connections","Открытые соединения"],["EVENT-CHECK-OK",12,"Check passed","Проверка прошла"],["EVENT-CHECK-FAILED",12,"Check failed","Ошибка проверки"],["EVENT-CONNECTION-RECOVERED",12,"Availability restored","Доступность восстановлена"],["EVENT-PROFILE-DISABLED",12,"Profile disabled","Профиль отключён"],["EVENT-OBSERVATION-GAP",12,"No observation interval","Перерыв наблюдений"],["EVENT-MONITORING",12,"Observing channels","Наблюдение за каналами"],["EVENT-START-CONFIRMATION-PENDING",12,"Start awaiting confirmation","Запуск ожидает подтверждения"],["EVENT-CHANNEL-PREPARATION",12,"Preparing channels","Подготовка каналов"],["EVENT-ROUTE-APPLYING",12,"Selecting route","Выбор маршрута"],["EVENT-PATH-CONFIRMATION",12,"Verifying path","Подтверждение пути"],["EVENT-RESERVE-SELECTED",12,"Reserve selected","Резерв выбран"],["EVENT-RESERVE-HELD",12,"Reserve retained","Резерв удержан"],["EVENT-RETURN-IN-PROGRESS",12,"Returning route","Возврат маршрута"],["EVENT-ROLLBACK-RECORDED",12,"Rollback recorded","Записан откат"],["EVENT-ORIGINAL-RESTORED",12,"Original route restored","Исходный маршрут восстановлен"],["EVENT-OPERATION-STOPPED",12,"Operation stopped","Операция остановлена"],["EVENT-AUTO-RUNNING",12,"Auto running","Auto работает"],["EVENT-AUTO-START-REQUESTED",12,"Start requested","Запрошен запуск"],["EVENT-AUTO-STOP-REQUESTED",12,"Stop requested","Запрошена остановка"],["EVENT-OPERATION-BLOCKED",12,"Action refused","Действие отклонено"],["EVENT-OPERATION-FAILED",12,"Operation failed","Операция не выполнена"],["EVENT-WINDOW-EXPIRED",12,"Test window ended","Окно теста завершено"],["EVENT-RECOVERY-PENDING",12,"Recovery pending","Восстановление ожидается"],["EVENT-RESERVE-DEGRADED",12,"Reserve check failed","Проблема на резерве"],["EVENT-TRIAL-PREREQUISITE",12,"Mode prerequisite missing","Не выполнено условие режима"],["EVENT-DETAILS-NOT-SAVED",12,"Record lacks detail","Подробности не сохранены"],["EVENT-RECORD-CONFLICT",12,"Record data conflict","Ошибка данных записи"],["EVENT-COMMAND-CANCELLED",12,"Command cancelled","Команда отменена"],["EVENT-COMMAND-ACCEPTED",12,"Command accepted","Команда принята"],["EVENT-COMMAND-QUEUED",12,"Command queued","Команда в очереди"],["EVENT-CONTROLLER-IDLE",12,"Waiting for a command","Ожидание команды"],["EVENT-RESULT-NEEDS-VERIFICATION",12,"Verify the result","Нужна проверка результата"],["EVENT-CHANNEL-SELECTION",12,"Channel selection record","Запись выбора канала"],["EVENT-POLICY-REAPPLY",12,"VPN rules applied again","Повторное применение правил VPN"],["EVENT-ROUTER-OBSERVATION",12,"Auto state","Состояние Auto"],["EVENT-DIRECTION-NOT-SAVED",12,"Switch direction not recorded","Направление перехода не сохранено"],["EVENT-VENDOR-WAIT",12,"Waiting for router operation","Ожидание операции роутера"]].map(function(r){r[1]=g[r[1]];return r;});})(["helper","monitor","switch","service","setup","telegram","speed","data","state","platform","manual","internal","journal"]);
var HELP_TOPICS=[{"id":"telegram","steps":[{"t":["Open the official https://t.me/BotFather in Telegram and send /newbot there, not in a terminal. Follow its current instructions.","Откройте официальный https://t.me/BotFather в Telegram и отправьте /newbot именно в его чат, а не в терминал. Следуйте его текущим указаниям."],"c":"/newbot"},{"t":["BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).","BotFather спросит имя (показывается в чате, любой текст, например «Мой VPN роутер») и затем username, который должен заканчиваться на «bot» (например my_router_vpn_bot)."],"c":null},{"t":["BotFather provides the bot token. Treat it as a password and paste it only into the dedicated private token field. Do not put it into a browser URL, chat, Git or diagnostic output.","BotFather выдаёт токен бота. Храните его как пароль и вставляйте только в специальное приватное поле токена. Не помещайте его в адрес браузера, чат, Git или диагностический вывод."],"c":null},{"t":["Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.","Откройте нового бота (ссылка в конце сообщения BotFather, https://t.me/<username_вашего_бота>) и нажмите Start или отправьте /start. Бот не может написать вам первым."],"c":null},{"t":["Way 1, the simplest: in Telegram open the bot @userinfobot (https://t.me/userinfobot) and press Start. The bot answers with your data; the line Id: 123456789 is your ID. Copy only the digits and paste them into the field Recipient. This is a third-party bot, not ours and not Telegram’s: never send it your token. Your own bot is still needed: open it and press Start once, otherwise Telegram will not let it write to you.","Способ 1, самый простой: в Telegram откройте бота @userinfobot (https://t.me/userinfobot) и нажмите Start. Бот ответит вашими данными; строка Id: 123456789 и есть ваш ID. Скопируйте только цифры и вставьте их в поле «Получатель». Это сторонний бот, не наш и не Telegram: токен ему никогда не отправляйте. Свой бот всё равно нужен: откройте его и один раз нажмите Start, иначе Telegram не позволит ему писать вам."],"c":null}]}];
function richText(text){return String(text).split('`').map(function(part,i){return i%2?E('code',{'class':'hv-code'},part):part;});}
function helpCommand(command){
  var button=E('button',{'type':'button','class':'cbi-button','click':function(){
    try{navigator.clipboard.writeText(command).then(function(){button.textContent=bi('Copied','Скопировано');}).catch(function(){});}catch(error){}
  }},bi('Copy','Копировать'));
  return E('div',{'class':'hv-cmd-row'},[E('pre',{'class':'hv-cmd'},command),button]);
}
function openHelpTopic(id){
  var link=document.querySelector('[data-hv-tab="help"]');if(link)link.click();
  LAZY_HELP.pendingTopic=id;return ensureLazyPage('help').then(function(){lazyHelpDeepLink('help');});
}
function helpLink(id,label){return E('a',{'href':'#help','class':'hv-help-link','click':function(ev){ev.preventDefault();openHelpTopic(id);}},label);}
var LAZY_HELP_NAME='homensai-vpn.help209';
var LAZY_HELP={api:null,promise:null,failed:false,attempt:0,hosts:Object.create(null),inventory:null,pendingTopic:null,pendingCode:null};
var helpNode=null,learnNode=null,errorTable=null,ERROR_GROUP_OF={},ERROR_GROUPS=[],ERROR_TABLE_STATE={query:'',open:Object.create(null),selected:null};
var ERROR_FAMILIES=ERROR_ROWS.filter(function(row){return row[0].endsWith('*');}).map(function(row){return [row[0].slice(0,-1)].concat(row.slice(1));});
ERROR_ROWS.forEach(function(row){ERROR_GROUP_OF[row[0]]=row[1];if(!ERROR_GROUPS.some(function(g){return g[0]===row[1];}))ERROR_GROUPS.push([row[1],[row[1],row[1]]]);});
function errorFamilyOf(code){return ERROR_FAMILIES.find(function(row){return code.indexOf(row[0])===0;})||null;}
function persistErrorTableState(){try{sessionStorage.setItem('homensai-vpn-error-table',JSON.stringify(ERROR_TABLE_STATE));}catch(error){}}
function lazyHelpDeepLink(key){
  if(!LAZY_HELP.api||typeof document==='undefined')return;
  if(typeof pageKeyNow==='function'&&pageKeyNow()!==key)return;
  if(key==='help'&&LAZY_HELP.pendingTopic){var topic=document.getElementById('help-'+LAZY_HELP.pendingTopic);if(topic){LAZY_HELP.pendingTopic=null;topic.open=true;try{topic.scrollIntoView({block:'start'});}catch(error){}}}
  if(key==='events'&&LAZY_HELP.pendingCode){var code=LAZY_HELP.pendingCode;LAZY_HELP.pendingCode=null;showErrorCode(code);}
}
function lazyHelpStatus(host,failed){
  while(host.firstChild)host.removeChild(host.firstChild);
  host.appendChild(E('p',{'role':failed?'alert':'status'},failed?['UI-HELP-LOAD-FAILED: ',bi('Help could not be loaded. Try again.','Не удалось загрузить справку. Повторите попытку.')]:bi('Loading…','Загрузка…')));
  if(failed)host.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){return loadLazyHelp(true).then(function(){lazyHelpDeepLink(typeof pageKeyNow==='function'?pageKeyNow():'');});}},bi('Retry','Повторить')));
}
function renderLazyPage(key,inventory){
  if(inventory)LAZY_HELP.inventory=inventory;
  if(!LAZY_HELP.hosts[key]){var host=E('div',{'data-hv-lazy-page':key});LAZY_HELP.hosts[key]={node:host,ready:false,requested:false};lazyHelpStatus(host,LAZY_HELP.failed);}
  return LAZY_HELP.hosts[key].node;
}
function mountLazyHelp(){
  if(!LAZY_HELP.api)return;
  Object.keys(LAZY_HELP.hosts).forEach(function(key){var item=LAZY_HELP.hosts[key];if(item.ready||!item.requested)return;
    var node=key==='switches'?LAZY_HELP.api.renderSwitchPage(switchStatsModel(LAZY_HELP.switchStatus)):key==='collection'?LAZY_HELP.api.renderCollectionPage(collectionModel(LAZY_HELP.collectionStatus)):LAZY_HELP.api[{help:'renderHelp',learn:'renderLearn',events:'renderErrorTable'}[key]](LAZY_HELP.inventory);
    while(item.node.firstChild)item.node.removeChild(item.node.firstChild);item.node.appendChild(node);item.ready=true;
  });
}
function lazyHelpContext(){return {E:E,bi:bi,locale:locale,richText:richText,helpCommand:helpCommand,
  READINESS_GUIDES:READINESS_GUIDES,READINESS_CHECKS:READINESS_CHECKS,renderReadinessHelp:renderReadinessHelp,
  renderAutoRemedy:renderAutoRemedy,AUTO_BLOCKERS:AUTO_BLOCKERS,AUTO_REMEDIES:AUTO_REMEDIES,autoRemedyKey:autoRemedyKey,
  PLAN_BLOCKERS:PLAN_BLOCKERS,errorCodeLink:errorCodeLink,spanText:spanText,ensureJournalDictionary:ensureJournalDictionary,extraHelpTopics:HELP_TOPICS,
  installCatalogue:function(value){ERROR_ROWS=value.rows;ERROR_GROUPS=value.groups;ERROR_GROUP_OF=value.groupOf;ERROR_TABLE_STATE=value.state;persistErrorTableState=value.persist;}
};}
function lazyHelpRequire(retry){
  if(!retry)return L.require(LAZY_HELP_NAME);
  var path=LAZY_HELP_NAME.replace(/\./g,'/')+'.js';
  return request.get(L.resource(path)+'?retry='+LAZY_HELP.attempt,{cache:false}).then(function(response){
    if(!response.ok)throw new Error('UI-HELP-LOAD-FAILED');
    var klass=new Function('window','document','L','baseclass',response.text())(window,document,L,baseclass);
    if(!klass||typeof klass.instantiate!=='function')throw new Error('UI-HELP-LOAD-FAILED');
    return klass.instantiate([]);
  });
}
function loadLazyHelp(retry){
  if(LAZY_HELP.api){mountLazyHelp();return Promise.resolve(LAZY_HELP.api);}
  if(LAZY_HELP.promise)return LAZY_HELP.promise;
  if(LAZY_HELP.failed&&!retry)return Promise.resolve(null);
  LAZY_HELP.failed=false;LAZY_HELP.attempt++;
  Object.keys(LAZY_HELP.hosts).forEach(function(key){lazyHelpStatus(LAZY_HELP.hosts[key].node,false);});
  LAZY_HELP.promise=Promise.resolve().then(function(){return lazyHelpRequire(retry);}).then(function(module){
    if(!module||typeof module.create!=='function')throw new Error('UI-HELP-LOAD-FAILED');
    LAZY_HELP.api=module.create(lazyHelpContext());mountLazyHelp();return LAZY_HELP.api;
  }).catch(function(){LAZY_HELP.api=null;LAZY_HELP.failed=true;Object.keys(LAZY_HELP.hosts).forEach(function(key){LAZY_HELP.hosts[key].ready=false;lazyHelpStatus(LAZY_HELP.hosts[key].node,true);});return null;
  }).then(function(value){LAZY_HELP.promise=null;return value;});return LAZY_HELP.promise;
}
function ensureLazyPage(key,inventory){
  if(['help','learn','events','switches','collection'].indexOf(key)<0)return Promise.resolve(null);
  renderLazyPage(key,inventory);LAZY_HELP.hosts[key].requested=true;return loadLazyHelp(false);
}
var TERMS_VERSION='2';
var TERMS_FULL_EN="# Experimental software: operational terms and licensing\n\n[Русский](DISCLAIMER.ru.md)\n\n**HomenS.AI Auto VPN is experimental software.** Read this before installation or use. A versioned acknowledgement is shown at first run; automatic switching cannot start until the current terms are accepted. These operational terms supplement, and do not replace, the [software LICENSE](LICENSE).\n\n1. **Experimental and device-specific.** This software is under development, and testing/qualification applies only to the exact configurations documented in the current test and readiness guides. Do not assume that every GL-MT6000, GL-MT3000, firmware revision, or operating mode is qualified.\n2. **Possible network interruption.** VPN switching may disconnect calls, downloads, devices or sessions. A bug or unexpected state may require manual recovery. Maintain an independent way to reach the router and internet; check your encrypted backup and recovery procedure before upgrading.\n3. **Changes to router settings.** The application can reorder existing VPN routing rules and temporarily adjust firewall rules. It is not GL.iNet firmware. Stop Auto and follow documented recovery/lifecycle steps before upgrading or uninstalling; removal may be refused while a transaction is active.\n4. **License and payment.** The current source distribution is governed, where applicable, by the **HomenSAI Personal & Commercial Source License v1.0**. Unmodified personal non-commercial use is free; use by or for any business or organization requires a separate **paid written license**. Code changes, redistribution, resale and integration need the rightsholder's **prior written consent**. Keep the developer notice **Serhii Khomenko — https://homensai.com**. See [LICENSE](LICENSE), [LICENSING.md](LICENSING.md), and [commercial licensing](COMMERCIAL-LICENSING.md). Earlier MIT grants remain valid for earlier covered copies.\n5. **No warranty and limitations.** The software is supplied \"AS IS\" to the maximum extent permitted by applicable law. Use it at your own risk; the license contains the applicable liability limitations and non-excludable exceptions.\n6. **User responsibility.** You are responsible for your network, VPN accounts, VPN provider rules, and applicable laws. Never rely on this experimental system where network interruption could threaten life, health or physical safety.\n7. **Optional reports.** Telegram reporting, if enabled, sends summaries through Telegram servers with a bot token stored locally. Nothing is sent through Telegram unless you configure this feature.\n8. **No guaranteed support.** Support, maintenance, uninterrupted operation and compatibility are not promised. Future releases and operational terms may change; updated terms may require another acknowledgement.\n\nThese operational terms do not replace third-party licenses or statutory rights. They are not legal advice.\n\n## How acknowledgement works\n\nOn first use, the LuCI screen presents these operational terms and two confirmations. The version/time are stored on the router. Until accepted, Auto switching is refused (`TERMS-NOT-ACCEPTED`). A changed terms version requires acknowledgement again.\n\nAcceptance here does **not** grant Commercial Use, modification or redistribution rights; obtain a separate agreement with the rightsholder first where applicable. If you disagree, do not start Auto, and use the normal documented safe uninstall procedure.\n\nOperational terms version: **2**. License text version: **1.0**.\n";
var TERMS_FULL_RU="# Экспериментальное ПО: условия эксплуатации и лицензирования\n\n[English](DISCLAIMER.md)\n\n**HomenS.AI Auto VPN — экспериментальная программа.** Прочитайте условия перед установкой и использованием. При первом запуске показывается соглашение; автоматическое переключение невозможно до подтверждения актуальной версии условий. Эти условия дополняют [лицензию](LICENSE), но не заменяют её.\n\n1. **Экспериментальность и совместимость.** Программа разрабатывается и проверена только в конфигурациях, указанных в актуальных документах и отчётах. Не считайте автоматически поддерживаемыми любые версии GL-MT6000, GL-MT3000, прошивки или режимы.\n2. **Возможный обрыв интернета.** Переключение VPN может прервать звонки, загрузки и соединения. Ошибка может потребовать ручного восстановления. До обновления подготовьте независимый доступ и проверенную зашифрованную резервную копию.\n3. **Изменения настроек роутера.** Приложение может менять порядок правил маршрутизации и временно настройки firewall. Это не прошивка GL.iNet. Перед обновлением или удалением выключите Auto и следуйте штатной процедуре восстановления; активная операция может блокировать удаление.\n4. **Лицензия и оплата.** Новые поставки исходников, на которые распространяется лицензия, регулируются **HomenSAI Personal & Commercial Source License v1.0**. Неизменённую программу можно бесплатно использовать лично и некоммерчески; компаниям, предпринимателям при работе и иным организациям требуется **отдельная платная письменная лицензия**. Изменение кода, распространение, перепродажа и интеграция требуют **предварительного письменного разрешения** автора. Сохраняйте указание **Serhii Khomenko — https://homensai.com**. См. [LICENSE](LICENSE), [LICENSING.md](LICENSING.md), [коммерческие условия](COMMERCIAL-LICENSING.md). Предыдущие разрешения MIT для старых версий остаются в силе.\n5. **Гарантии и ответственность.** ПО поставляется «КАК ЕСТЬ» в пределах, допускаемых законодательством. Использование — на ваш риск; ответственность и обязательные исключения описаны в тексте лицензии.\n6. **Ваша ответственность.** Вы отвечаете за роутер, сеть, VPN-аккаунты, условия провайдера и законность использования. Не полагайтесь на экспериментальную систему там, где обрыв связи угрожает жизни, здоровью или имуществу.\n7. **Необязательные отчёты.** При настройке Telegram отчёты отправляются через серверы Telegram; токен бота хранится на роутере. Без настройки функция не активна.\n8. **Поддержка не гарантируется.** Не обещаются поддержка, обновления, совместимость или бесперебойность. Новые версии и условия могут требовать повторного подтверждения.\n\nЭти эксплуатационные условия не отменяют лицензии сторонних компонентов и обязательные права по закону. Текст не является юридической консультацией.\n\n## Как работает подтверждение\n\nПри первом запуске в LuCI показываются условия и два флажка. Версия и время подтверждения сохраняются на роутере. Пока подтверждения нет, Auto не запускается (`TERMS-NOT-ACCEPTED`). При изменении версии подтверждение запрашивается снова.\n\nНажатие «Принять» **не даёт** права на коммерческое использование, изменение или распространение — для этого заранее нужен отдельный договор. Если вы не согласны, не запускайте Auto и следуйте процедуре безопасного удаления.\n\nВерсия эксплуатационных условий: **2**. Версия лицензии: **1.0**.\n";
var TERMS_POINTS=[
  {h:["Experimental and device-specific","Экспериментальность и совместимость"],t:["This software is under development, and testing/qualification applies only to the exact configurations documented in the current test and readiness guides. Do not assume that every GL-MT6000, GL-MT3000, firmware revision, or operating mode is qualified.","Программа разрабатывается и проверена только в конфигурациях, указанных в актуальных документах и отчётах. Не считайте автоматически поддерживаемыми любые версии GL-MT6000, GL-MT3000, прошивки или режимы."]},
  {h:["Possible network interruption","Возможный обрыв интернета"],t:["VPN switching may disconnect calls, downloads, devices or sessions. A bug or unexpected state may require manual recovery. Maintain an independent way to reach the router and internet; check your encrypted backup and recovery procedure before upgrading.","Переключение VPN может прервать звонки, загрузки и соединения. Ошибка может потребовать ручного восстановления. До обновления подготовьте независимый доступ и проверенную зашифрованную резервную копию."]},
  {h:["Changes to router settings","Изменения настроек роутера"],t:["The application can reorder existing VPN routing rules and temporarily adjust firewall rules. It is not GL.iNet firmware. Stop Auto and follow documented recovery/lifecycle steps before upgrading or uninstalling; removal may be refused while a transaction is active.","Приложение может менять порядок правил маршрутизации и временно настройки firewall. Это не прошивка GL.iNet. Перед обновлением или удалением выключите Auto и следуйте штатной процедуре восстановления; активная операция может блокировать удаление."]},
  {h:["License and payment","Лицензия и оплата"],t:["The current source distribution is governed, where applicable, by the HomenSAI Personal & Commercial Source License v1.0. Unmodified personal non-commercial use is free; use by or for any business or organization requires a separate paid written license. Code changes, redistribution, resale and integration need the rightsholder's prior written consent. Keep the developer notice Serhii Khomenko — https://homensai.com. See LICENSE, LICENSING.md, and commercial licensing. Earlier MIT grants remain valid for earlier covered copies.","Новые поставки исходников, на которые распространяется лицензия, регулируются HomenSAI Personal & Commercial Source License v1.0. Неизменённую программу можно бесплатно использовать лично и некоммерчески; компаниям, предпринимателям при работе и иным организациям требуется отдельная платная письменная лицензия. Изменение кода, распространение, перепродажа и интеграция требуют предварительного письменного разрешения автора. Сохраняйте указание Serhii Khomenko — https://homensai.com. См. LICENSE, LICENSING.md, коммерческие условия. Предыдущие разрешения MIT для старых версий остаются в силе."]},
  {h:["No warranty and limitations","Гарантии и ответственность"],t:["The software is supplied \"AS IS\" to the maximum extent permitted by applicable law. Use it at your own risk; the license contains the applicable liability limitations and non-excludable exceptions.","ПО поставляется «КАК ЕСТЬ» в пределах, допускаемых законодательством. Использование — на ваш риск; ответственность и обязательные исключения описаны в тексте лицензии."]},
  {h:["User responsibility","Ваша ответственность"],t:["You are responsible for your network, VPN accounts, VPN provider rules, and applicable laws. Never rely on this experimental system where network interruption could threaten life, health or physical safety.","Вы отвечаете за роутер, сеть, VPN-аккаунты, условия провайдера и законность использования. Не полагайтесь на экспериментальную систему там, где обрыв связи угрожает жизни, здоровью или имуществу."]},
  {h:["Optional reports","Необязательные отчёты"],t:["Telegram reporting, if enabled, sends summaries through Telegram servers with a bot token stored locally. Nothing is sent through Telegram unless you configure this feature.","При настройке Telegram отчёты отправляются через серверы Telegram; токен бота хранится на роутере. Без настройки функция не активна."]},
  {h:["No guaranteed support","Поддержка не гарантируется"],t:["Support, maintenance, uninterrupted operation and compatibility are not promised. Future releases and operational terms may change; updated terms may require another acknowledgement.","Не обещаются поддержка, обновления, совместимость или бесперебойность. Новые версии и условия могут требовать повторного подтверждения."]}
];
var TERMS_CHECKS=[
  ["I understand that this software is experimental and may interrupt my internet connection.","Я понимаю, что это ПО экспериментальное и может прервать моё подключение к интернету."],
  ["I have read the license and terms. I will use this only privately and non-commercially unless I hold a separate paid written license.","Я прочитал лицензию и условия. Я использую программу лично и некоммерчески либо имею отдельную платную письменную лицензию."]
];
function termsAccepted(inventory){
  return !!inventory&&!inventory.error&&!!inventory.settings&&inventory.settings.terms_version===TERMS_VERSION;
}
var ONBOARDING_VERSION=1,ONBOARDING_SESSION=null,HV_ROUTER_DISPLAY=null;
function onboardingPairChannels(profiles,settings){
  var ids=Object.create(null),logicals=Object.create(null),rows=[];
  (Array.isArray(profiles)?profiles:[]).slice(0,400).forEach(function(p){
    if(!p||typeof p.id!=='string')return;ids[p.id]=(ids[p.id]||0)+1;
    if(['wireguard','openvpn'].indexOf(p.protocol)<0||!p.id.startsWith(p.protocol+':')||!/^[A-Za-z0-9_.:-]{1,96}$/.test(p.id)||typeof p.interface!=='string'||!/^[A-Za-z0-9_.-]{1,64}$/.test(p.interface)||p.vendor_tunnel_id!==p.protocol+':'+p.interface||p.section!==undefined&&p.id!==p.protocol+':'+p.section)return;
    logicals[p.interface]=(logicals[p.interface]||0)+1;rows.push(p);
  });
  var mt3000=(settings||{}).detected_router_model==='mt3000'||(settings||{}).pair_auto_mode==='router-probed-ipv4';
  return rows.filter(function(p){return ids[p.id]===1&&logicals[p.interface]===1&&(!mt3000||(p.protocol==='wireguard'&&/^wgclient[1-9][0-9]{0,3}$/.test(p.interface)||p.protocol==='openvpn'&&/^ovpnclient[1-9][0-9]{0,3}$/.test(p.interface)));});
}
function onboardingComplete(inventory){
  var s=inventory&&inventory.settings;
  return !!s&&!inventory.error&&s.onboarding_complete===true&&s.onboarding_version===ONBOARDING_VERSION;
}
var PLAN_BLOCKERS={
  'GL-ADAPTER-UNVERIFIED':['GL.iNet VPN manager','Менеджер VPN GL.iNet','Not proven that this program’s way of switching works together with the VPN manager built into this exact GL.iNet firmware.','Не доказано, что способ переключения этой программы работает вместе со встроенным менеджером VPN именно этой прошивки GL.iNet.'],
  'WORKER-COORDINATION-UNVERIFIED':['GL.iNet background programs','Фоновые программы GL.iNet','GL.iNet runs its own background programs that also connect and reconnect VPNs. Not tested that they do not fight with this program.','GL.iNet запускает свои фоновые программы, которые тоже подключают и переподключают VPN. Не проверено, что они не мешают этой программе.'],
  'LAN-PATH-UNVERIFIED':['Path of a home computer','Путь домашнего компьютера','Not confirmed from a computer in your network that its traffic really goes through the chosen VPN. This is what the LAN helper checks.','Не подтверждено с компьютера в вашей сети, что его трафик действительно идёт через выбранный VPN. Это проверяет LAN-помощник.'],
  'DNS-POLICY-UNVERIFIED':['Name lookups (DNS)','Поиск адресов (DNS)','Not confirmed that DNS requests of your devices follow the VPN and do not leak outside it during and after a switch.','Не подтверждено, что DNS-запросы ваших устройств идут через VPN и не утекают мимо него во время и после переключения.'],
  'KILLSWITCH-UNVERIFIED':['Kill Switch','Kill Switch','Not confirmed that the GL.iNet Kill Switch blocks the internet, instead of leaking, when a VPN drops during a switch.','Не подтверждено, что Kill Switch GL.iNet блокирует интернет, а не пропускает трафик мимо VPN, когда VPN обрывается во время переключения.'],
  'IPV6-POLICY-UNVERIFIED':['IPv6 traffic','Трафик IPv6','Not confirmed that IPv6 traffic cannot bypass the VPN.','Не подтверждено, что трафик IPv6 не может обойти VPN.'],
  'WATCHDOG-UNVERIFIED':['Safety timer','Страхующий таймер','Not confirmed on this router that the independent timer, which releases the program’s traffic block and returns to a safe state if something hangs, always fires.','Не подтверждено на этом роутере, что независимый таймер, который снимает собственную блокировку трафика и возвращает безопасное состояние при зависании, всегда срабатывает.'],
  'SCOPED-CONNTRACK-UNVERIFIED':['Open connections','Открытые соединения','Not confirmed that a switch resets only the connections it must (the router’s connection table), not all of them.','Не подтверждено, что при переключении сбрасываются только нужные соединения (таблица соединений роутера), а не все.']
};
function safeCode(code){return typeof code==='string'&&/^[A-Z][A-Z0-9-]{1,95}$/.test(code);}
function errorCodeLink(code){return E('a',{'href':'#events','class':'hv-errlink','click':function(ev){ev.preventDefault();showErrorCode(code);}},code);}
var SPEED_LIVE_CACHE=null,SPEED_LIVE_REQUESTED=null,SPEED_LIVE_HOSTS=[],SPEED_LIVE_BUSY=false;
function speedLiveRunning(data){return !!data&&['QUEUED','RUNNING'].indexOf(data.state)>=0;}
function speedLiveNumber(n,max){return Number.isFinite(n)&&n>=0&&n<=max;}
function speedLiveSnapshot(raw){
  if(!raw||!['IDLE','QUEUED','RUNNING','DONE','FAILED','CANCELLED'].includes(raw.state)||!Array.isArray(raw.profiles)||raw.profiles.length>8||!speedLiveNumber(raw.server_time,4102444800))return null;
  if(raw.state!=='IDLE'&&(typeof raw.run_id!=='string'||!/^[a-f0-9]{32}$/.test(raw.run_id)))return null;
  var rows=[],seen={};
  raw.profiles.forEach(function(r){
    if(!r||typeof r.id!=='string'||!/^[A-Za-z0-9_.:-]{1,96}$/.test(r.id)||seen[r.id]||!Array.isArray(r.samples)||r.samples.length>128)return;
    seen[r.id]=true;var last=-1,samples=[];
    r.samples.forEach(function(p){if(!Array.isArray(p)||p.length!==3||!speedLiveNumber(p[0],300)||p[0]<last||p.slice(1).some(function(v){return v!==null&&!speedLiveNumber(v,10000000);})||p.slice(1).filter(function(v){return v!==null;}).length!==1)return;last=p[0];samples.push(p.slice());});
    rows.push({id:r.id,phase:['waiting','resolving','latency','download','upload','done','failed','cancelled'].includes(r.phase)?r.phase:'failed',samples:samples,updated:r.updated,download_mbps:speedLiveNumber(r.download_mbps,10000000)?r.download_mbps:null,upload_mbps:speedLiveNumber(r.upload_mbps,10000000)?r.upload_mbps:null,code:typeof r.code==='string'&&/^SPEED-[A-Z0-9-]{1,64}$/.test(r.code)?r.code:null});
  });
  return {run_id:raw.run_id||null,state:raw.state,profiles:rows,server_time:raw.server_time,code:raw.code};
}
function speedLiveQueued(result,ids){
  if(!result||result.accepted!==true||typeof result.run_id!=='string'||!/^[a-f0-9]{32}$/.test(result.run_id))return;
  SPEED_LIVE_REQUESTED={run_id:result.run_id,state:'QUEUED',server_time:Date.now()/1000,profiles:ids.map(function(id){return {id:id,phase:'waiting',samples:[]};})};
  SPEED_LIVE_CACHE=null;SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;}).forEach(function(h){h.updateSpeedLive(SPEED_LIVE_REQUESTED);});
}
function speedReason(code){
  var messages={
    'SPEED-BUSY':['A speed test is already running.','Тест скорости уже выполняется.'],
    'SPEED-CPU-BUSY':['Router CPU is busy even after pausing Auto and monitoring; retry later.','Процессор роутера занят даже после паузы Auto и мониторинга; повторите позже.'],
    'SPEED-TRAFFIC-BUSY':['VPN traffic is above the configured limit; retry when it is quieter.','VPN-трафик выше заданного порога; повторите, когда нагрузка снизится.'],
    'SPEED-TRAFFIC-UNKNOWN':['Waiting for fresh traffic observations.','Ожидание свежих наблюдений за трафиком.'],
    'SPEED-COOLDOWN':['Wait at least 60 seconds between manual tests.','Между ручными тестами нужно подождать не менее 60 секунд.'],
    'SPEED-DAILY-LIMIT':['The daily test quota has been reached.','Достигнута суточная квота тестов.'],
    'SPEED-SWITCH-IN-PROGRESS':['A channel switch is in progress; wait until it finishes.','Идёт переключение канала; дождитесь его завершения.']
  };
  return messages[code]?bi.apply(null,messages[code]):bi('Test not started. See diagnostic code: ','Тест не запущен. Код диагностики: ')+code;
}
function findErrorCodes(text){
  var pattern=/\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*\b/g,match,found=[];
  while((match=pattern.exec(text))){
    var code=match[0];
    if(code.length<5||!(Object.prototype.hasOwnProperty.call(ERROR_GROUP_OF,code)||(typeof errorFamilyOf==='function'&&errorFamilyOf(code))))continue;
    found.push({code:code,index:match.index});
  }
  return found;
}
var JOURNAL_TYPES={
  "OK": {
    "code": "EVENT-CHECK-OK",
    "label": [
      "Check passed",
      "Проверка прошла"
    ],
    "message": [
      "Channel availability threshold was met",
      "Условие доступности канала выполнено"
    ],
    "meaning": [
      "The monitor received a result without a diagnostic error. This records channel availability at that observation; it does not mean traffic switched or that Auto was activated.",
      "Монитор получил результат без диагностической ошибки. Это наблюдение доступности канала в тот момент; оно не означает переключение трафика или включение Auto."
    ],
    "level": "ok"
  },
  "FAILURE": {
    "code": "EVENT-CHECK-FAILED",
    "label": [
      "Check failed",
      "Ошибка проверки"
    ],
    "message": [
      "Connection check failed",
      "Ошибка проверки соединения"
    ],
    "meaning": [
      "A failed channel check was recorded. Open the saved diagnostic code for the observed failure. It does not by itself prove a route switch.",
      "Зафиксирована неудачная проверка канала. Причину наблюдаемого отказа смотрите в сохранённом диагностическом коде. Сама запись не доказывает смену маршрута."
    ],
    "level": "error"
  },
  "RECOVERY": {
    "code": "EVENT-CONNECTION-RECOVERED",
    "label": [
      "Availability restored",
      "Доступность восстановлена"
    ],
    "message": [
      "Connection availability recovered",
      "Доступность соединения восстановлена"
    ],
    "meaning": [
      "A previously failed channel became available again in observations. This is recovery of availability, not proof that it became the traffic route.",
      "Ранее отказавший канал снова стал доступен по наблюдениям. Это восстановление доступности, а не доказательство, что через него уже идёт трафик."
    ],
    "level": "ok"
  },
  "DISABLED": {
    "code": "EVENT-PROFILE-DISABLED",
    "label": [
      "Profile disabled",
      "Профиль отключён"
    ],
    "message": [
      "VPN profile was disabled",
      "VPN-профиль отключён"
    ],
    "meaning": [
      "The profile is administratively disabled or inactive. This is distinct from a failed Internet check.",
      "Профиль административно отключён или неактивен. Это отличается от ошибки проверки Интернета."
    ],
    "level": "warning"
  },
  "GAP": {
    "code": "EVENT-OBSERVATION-GAP",
    "label": [
      "No observation interval",
      "Перерыв наблюдений"
    ],
    "message": [
      "A gap in observations was recorded",
      "Зафиксирован перерыв наблюдений"
    ],
    "meaning": [
      "There were no trusted measurements for an interval. Neither successful connectivity nor failure is invented for the missing period.",
      "За интервал нет достоверных измерений. Пропуск не превращается ни в исправность, ни в выдуманный отказ."
    ],
    "level": "warning"
  },
  "OBSERVING": {
    "code": "EVENT-MONITORING",
    "label": [
      "Observing channels",
      "Наблюдение за каналами"
    ],
    "message": [
      "The controller is observing the VPN channels",
      "Контроллер наблюдает за VPN-каналами"
    ],
    "meaning": [
      "The controller is checking the channels. This state alone does not describe a newly completed traffic switch; channel selection has separate confirmation.",
      "Контроллер проверяет каналы. Само это состояние не означает только что выполненное переключение трафика; выбор маршрута подтверждается отдельно."
    ],
    "level": "ok"
  },
  "STARTING": {
    "code": "EVENT-AUTO-STARTING",
    "label": [
      "Auto starting",
      "Запуск Auto"
    ],
    "message": [
      "Auto startup is in progress",
      "Выполняется запуск Auto"
    ],
    "meaning": [
      "Startup was accepted and is still being prepared. Wait for its actual completion or a specific refusal; a request is not a running session.",
      "Запуск принят и ещё подготавливается. Дождитесь фактического завершения или конкретного отказа; запрос не равен работающему сеансу."
    ],
    "level": "warning"
  },
  "ARMED": {
    "code": "EVENT-CHANNEL-PREPARATION",
    "label": [
      "Preparing channels",
      "Подготовка каналов"
    ],
    "message": [
      "Channel prerequisites are being prepared and checked",
      "Подготавливаются и проверяются условия работы каналов"
    ],
    "meaning": [
      "A preparation stage was recorded. Connectivity and routing may still be checked; this is not a completed switch.",
      "Зафиксирован подготовительный этап. Связность и маршрут ещё могут проверяться; это не завершённое переключение."
    ],
    "level": "warning"
  },
  "APPLYING": {
    "code": "EVENT-ROUTE-APPLYING",
    "label": [
      "Selecting route",
      "Выбор маршрута"
    ],
    "message": [
      "A route-selection command is being applied",
      "Выполняется команда выбора маршрута"
    ],
    "meaning": [
      "The operation is applying the planned traffic selection. Its final outcome must be confirmed by a later event.",
      "Операция применяет запланированный выбор трафика. Итог должен быть подтверждён следующим событием."
    ],
    "level": "warning"
  },
  "WAIT-CLIENT": {
    "code": "EVENT-PATH-CONFIRMATION",
    "label": [
      "Verifying path",
      "Подтверждение пути"
    ],
    "message": [
      "The selected path is awaiting verification",
      "Ожидается подтверждение выбранного пути"
    ],
    "meaning": [
      "The change is not yet accepted as a confirmed route. The required evidence depends on the recorded operating mode: router observations or a separate client witness.",
      "Изменение ещё не принято как подтверждённый маршрут. Требуемое доказательство зависит от сохранённого режима: наблюдения роутера либо отдельный клиентский тест."
    ],
    "level": "warning"
  },
  "COMMITTED": {
    "code": "EVENT-RESERVE-SELECTED",
    "label": [
      "Reserve selected",
      "Резерв выбран"
    ],
    "message": [
      "Reserve traffic selection was confirmed",
      "Выбор резервного маршрута подтверждён"
    ],
    "meaning": [
      "The recorded operation confirmed reserve selection. This does not imply that the primary is broken; its health is a separate observation.",
      "Операция подтвердила выбор резерва. Это не означает неисправность основного: его состояние проверяется отдельно."
    ],
    "level": "ok"
  },
  "STOPPED-ON-RESERVE": {
    "code": "EVENT-RESERVE-HELD",
    "label": [
      "Reserve retained",
      "Резерв удержан"
    ],
    "message": [
      "The operation ended while retaining the reserve",
      "Операция завершилась с сохранением резерва"
    ],
    "meaning": [
      "The operation retained reserve routing. In a continuous session Auto may remain on; this transaction state is not proof of a global Auto shutdown.",
      "Операция сохранила резервный маршрут. В непрерывном сеансе Auto может продолжать работать; это состояние транзакции не доказывает глобальное выключение Auto."
    ],
    "level": "ok"
  },
  "RESTORING": {
    "code": "EVENT-RETURN-IN-PROGRESS",
    "label": [
      "Returning route",
      "Возврат маршрута"
    ],
    "message": [
      "The original route is being restored",
      "Восстанавливается исходный маршрут"
    ],
    "meaning": [
      "Restoration is in progress. A later verified outcome is required before describing the original route as restored.",
      "Восстановление выполняется. Прежде чем считать исходный маршрут восстановленным, требуется последующее подтверждение."
    ],
    "level": "warning"
  },
  "ROLLED-BACK": {
    "code": "EVENT-ROLLBACK-RECORDED",
    "label": [
      "Rollback recorded",
      "Записан откат"
    ],
    "message": [
      "A rollback stage was recorded",
      "Зафиксирован этап отката"
    ],
    "meaning": [
      "This old record names a rollback. If it lacks an original_restored confirmation, successful restoration must not be invented.",
      "Старая запись содержит этап отката. Если подтверждение original_restored в ней отсутствует, успешное восстановление не приписывается."
    ],
    "level": "warning"
  },
  "RETURNED": {
    "code": "EVENT-ORIGINAL-RESTORED",
    "label": [
      "Original route restored",
      "Исходный маршрут восстановлен"
    ],
    "message": [
      "Restoration of the original route was confirmed",
      "Восстановление исходного маршрута подтверждено"
    ],
    "meaning": [
      "The event includes explicit verified restoration evidence. This is separate from a request to return or a restoration-in-progress stage.",
      "В событии есть явное подтверждение восстановления. Это отличается от запроса возврата или незавершённого восстановления."
    ],
    "level": "ok"
  },
  "STOPPED": {
    "code": "EVENT-OPERATION-STOPPED",
    "label": [
      "Operation stopped",
      "Операция остановлена"
    ],
    "message": [
      "The controller operation was stopped",
      "Управляющая операция остановлена"
    ],
    "meaning": [
      "The operation ended. A global Auto state and the resulting route must be read from their own recorded confirmations, not inferred from this word alone.",
      "Операция завершена. Общее состояние Auto и итоговый маршрут определяются по собственным подтверждениям, а не выводятся только из этого слова."
    ],
    "level": "warning"
  },
  "RUNNING": {
    "code": "EVENT-AUTO-RUNNING",
    "label": [
      "Auto running",
      "Auto работает"
    ],
    "message": [
      "The Auto session is running",
      "Сеанс Auto работает"
    ],
    "meaning": [
      "A running controller session was recorded. Each channel still needs fresh connectivity checks; it is not a guarantee of every client path.",
      "Зафиксирован работающий сеанс контроллера. Каналам по-прежнему нужны свежие проверки; это не гарантия каждого клиентского пути."
    ],
    "level": "ok"
  },
  "AUTO-START-REQUESTED": {
    "code": "EVENT-AUTO-START-REQUESTED",
    "label": [
      "Start requested",
      "Запрошен запуск"
    ],
    "message": [
      "Auto activation requested",
      "Запрошено включение Auto"
    ],
    "meaning": [
      "This is the request, including its recorded initiator. Startup is not confirmed until a later completed state.",
      "Это запрос с сохранённым инициатором. Запуск не подтверждён до последующего завершённого состояния."
    ],
    "level": "warning"
  },
  "AUTO-STOP-REQUESTED": {
    "code": "EVENT-AUTO-STOP-REQUESTED",
    "label": [
      "Stop requested",
      "Запрошена остановка"
    ],
    "message": [
      "Auto deactivation requested",
      "Запрошено выключение Auto"
    ],
    "meaning": [
      "This is a stop request, not proof that routing was restored or the controller finished stopping.",
      "Это запрос остановки, а не доказательство восстановления маршрута или завершения остановки контроллера."
    ],
    "level": "warning"
  },
  "BLOCKED": {
    "code": "EVENT-OPERATION-BLOCKED",
    "label": [
      "Action refused",
      "Действие отклонено"
    ],
    "message": [
      "A required prerequisite blocked the action",
      "Действие отклонено из-за невыполненного условия"
    ],
    "meaning": [
      "No success is inferred. Read the saved reason code; do not bypass the gate or treat a queued request as applied routing.",
      "Успех не предполагается. Прочитайте сохранённый код причины; не обходите условие и не считайте очередь выполненным выбором маршрута."
    ],
    "level": "error"
  },
  "FAILED": {
    "code": "EVENT-OPERATION-FAILED",
    "label": [
      "Operation failed",
      "Операция не выполнена"
    ],
    "message": [
      "The operation ended with an error",
      "Операция завершилась ошибкой"
    ],
    "meaning": [
      "Read the specific recorded reason and recovery outcome. Failed application or rollback is not reported as successful switching.",
      "Прочитайте конкретную сохранённую причину и итог восстановления. Неудачное применение или откат не выдаётся за успешное переключение."
    ],
    "level": "error"
  },
  "EXPIRED": {
    "code": "EVENT-WINDOW-EXPIRED",
    "label": [
      "Test window ended",
      "Окно теста завершено"
    ],
    "message": [
      "The bounded operation window expired",
      "Закончилось ограниченное окно операции"
    ],
    "meaning": [
      "A configured time boundary ended. The final routing/recovery outcome is a separate confirmation.",
      "Истёк заданный предел времени. Итог маршрутизации или восстановления подтверждается отдельно."
    ],
    "level": "warning"
  },
  "RELEASE-PENDING": {
    "code": "EVENT-RECOVERY-PENDING",
    "label": [
      "Recovery pending",
      "Восстановление ожидается"
    ],
    "message": [
      "Traffic-block release is awaiting confirmation",
      "Ожидается подтверждение снятия блокировки"
    ],
    "meaning": [
      "Recovery has not yet been verified complete. Read the saved recovery code; an attempted cleanup is not the final result.",
      "Завершение восстановления ещё не проверено. Смотрите сохранённый код; попытка очистки не равна итоговому результату."
    ],
    "level": "warning"
  },
  "DEGRADED-ON-RESERVE": {
    "code": "EVENT-RESERVE-DEGRADED",
    "label": [
      "Reserve check failed",
      "Проблема на резерве"
    ],
    "message": [
      "The selected reserve also has a connectivity problem",
      "На выбранном резерве тоже выявлена проблема связи"
    ],
    "meaning": [
      "A problem was observed on the reserve. Returning to primary still requires current evidence and the applicable policy.",
      "На резерве наблюдается проблема. Возврат на основной по-прежнему требует актуальных доказательств и применимой политики."
    ],
    "level": "error"
  },
  "TRIAL-REQUIRED": {
    "code": "EVENT-TRIAL-PREREQUISITE",
    "label": [
      "Mode prerequisite missing",
      "Не выполнено условие режима"
    ],
    "message": [
      "The chosen mode needs an additional prerequisite",
      "Для выбранного режима нужно дополнительное условие"
    ],
    "meaning": [
      "The saved reason describes the mode-specific prerequisite. A legacy LAN trial refusal does not imply every prepared router-probed session needs a client certificate.",
      "Сохранённая причина описывает условие конкретного режима. Отказ прежнего LAN-теста не означает, что любой подготовленный router-probed сеанс требует клиентский сертификат."
    ],
    "level": "warning"
  },
  "LEGACY": {
    "code": "EVENT-DETAILS-NOT-SAVED",
    "label": [
      "Record lacks detail",
      "Подробности не сохранены"
    ],
    "message": [
      "An older record did not retain a full event description",
      "В старой записи не сохранено полное описание события"
    ],
    "meaning": [
      "Only the saved fields can be explained. A missing initiator, role or final outcome is not replaced with today's route or an invented successful switch.",
      "Объясняются только сохранённые поля. Отсутствующие инициатор, роль или итог не заменяются сегодняшним маршрутом или выдуманным успешным переключением."
    ],
    "level": "warning"
  }
};
JOURNAL_TYPES.CONFLICT={code:'EVENT-RECORD-CONFLICT',label:['Record data conflict','Ошибка данных записи'],message:['The saved event contains conflicting results','В сохранённом событии противоречивые результаты'],meaning:['Success and failure were both recorded. Do not treat this as a successful channel or confirmed switch; inspect the saved diagnostic data.','Одновременно записаны успех и ошибка. Это не считается успешной проверкой или подтверждённым переходом; проверьте сохранённые диагностические данные.'],level:'error'};
JOURNAL_TYPES["HELD-ON-RESERVE"]=JOURNAL_TYPES["STOPPED-ON-RESERVE"];
JOURNAL_TYPES.CHANNEL_SELECTION={code:'EVENT-CHANNEL-SELECTION',label:['Channel selection record','Запись выбора канала'],message:['The router recorded a channel selection operation','Роутер сохранил операцию выбора канала'],meaning:['The saved direction and completion describe this operation. A controller phase alone does not prove the selected route or independent LAN availability.','Сохранённые направление и завершение описывают эту операцию. Сам этап контроллера не доказывает выбранный маршрут или доступность независимого клиента LAN.'],level:'warning'};
JOURNAL_TYPES.POLICY_REAPPLY={code:'EVENT-POLICY-REAPPLY',label:['VPN rules applied again','Повторное применение правил VPN'],message:['The router applied VPN rules without changing channel order','Роутер повторно применил правила VPN без изменения порядка каналов'],meaning:['This is a rule application, not a channel switch or an internet availability result. Completion and the saved policy reason are separate facts.','Это применение правил, а не переключение канала или результат проверки интернета. Завершение и сохранённая причина проверки правил указываются отдельно.'],level:'warning'};
JOURNAL_TYPES.ROUTER_OBSERVATION={code:'EVENT-ROUTER-OBSERVATION',label:['Auto state','Состояние Auto'],message:['Auto state was recorded; the channel did not change','Записано состояние Auto; канал не менялся'],meaning:['This observation did not record a channel-order change. Use the saved event-time selection evidence rather than interpreting the controller phase as a new switch.','В этом наблюдении смена порядка каналов не записана. Используйте сохранённое подтверждение выбора на момент события; этап контроллера не считается новым переключением.'],level:'ok'};
JOURNAL_TYPES.DIRECTION_NOT_SAVED={code:'EVENT-DIRECTION-NOT-SAVED',label:['Switch direction not recorded','Направление перехода не сохранено'],message:['The saved data does not establish the direction of this operation','Сохранённые данные не подтверждают направление этой операции'],meaning:['The event lacks valid explicit source or destination metadata. The current pair and controller phase are not used to invent the missing direction.','В событии нет корректно сохранённых исходного канала или назначения. Текущая пара и этап контроллера не используются для выдумывания направления.'],level:'warning'};
function journalCodeRow(code){
  if(typeof ERROR_ROWS==='undefined'||typeof code!=='string')return null;
  return ERROR_ROWS.find(function(r){return r[0]===code;})||ERROR_ROWS.find(function(r){return r[0].endsWith('*')&&code.indexOf(r[0].slice(0,-1))===0;})||null;
}
JOURNAL_TYPES.STARTING={code:'EVENT-START-CONFIRMATION-PENDING',label:['Start awaiting confirmation','Запуск ожидает подтверждения'],message:['Start accepted; waiting for the controller','Запрос включения принят; ожидается подтверждение контроллера'],meaning:['The Start request is recorded while the previous stopped state is still visible. This is not another Stop command.','Запрос Start сохранён, пока ещё видно прежнее остановленное состояние. Это ожидание запуска, а не новая команда Stop.'],level:'warning'};
JOURNAL_TYPES.VENDOR_WAIT={code:'EVENT-VENDOR-WAIT',label:['Waiting for router operation','Ожидание операции роутера'],message:['Waiting for the stock network operation or lock to clear','Ожидание завершения штатной сетевой операции или снятия её блокировки'],meaning:['A GL.iNet worker or lock was observed. The controller defers switching decisions until it clears; the record alone does not establish a VPN outage. The exact worker may not have been retained.','Обнаружен обработчик или блокировка GL.iNet. Контроллер временно откладывает решения о переключении; сама запись не подтверждает отказ VPN. Конкретный обработчик мог не сохраниться в истории.'],level:'warning'};
function journalDefinition(entry){
  var transition=savedTransition(entry);
  if(transition.present){
    if(transition.outcome==='refused')return Object.assign({},JOURNAL_TYPES.CHANNEL_SELECTION,{level:'warning'});
    if(transition.reapply)return JOURNAL_TYPES.POLICY_REAPPLY;
    if(transition.unchanged)return JOURNAL_TYPES.ROUTER_OBSERVATION;
    if(!transition.to)return JOURNAL_TYPES.DIRECTION_NOT_SAVED;
    return Object.assign({},JOURNAL_TYPES.CHANNEL_SELECTION,{level:transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0?'ok':'warning'});
  }
  if(entry.state==='BLOCKED'&&entry.code==='VENDOR-WORKER-BUSY')return JOURNAL_TYPES.VENDOR_WAIT;
  if((entry.state==='OK'||entry.code==='OK')&&(entry.state==='FAILURE'||entry.kind==='FAILURE'||entry.state==='OK'&&entry.code&&entry.code!=='OK'&&entry.level==='error'))return JOURNAL_TYPES.CONFLICT;
  if(entry.return_primary===true||entry.state==='ROLLED-BACK'&&entry.original_restored===true)return JOURNAL_TYPES.RETURNED;
  if(JOURNAL_TYPES[entry.state])return JOURNAL_TYPES[entry.state];
  if(JOURNAL_TYPES[entry.kind])return JOURNAL_TYPES[entry.kind];
  if(entry.code==='OK')return JOURNAL_TYPES.OK;
  var r=journalCodeRow(entry.code||entry.state);
  return r?{code:r[0],label:[r[2],r[3]],message:[r[2],r[3]],meaning:[r[4]||'Open this code to load its detailed explanation.',r[5]||'Откройте этот код для загрузки подробного объяснения.'],level:entry.level}:JOURNAL_TYPES.LEGACY;
}
function ensureJournalDictionary(){
  if(typeof ERROR_ROWS==='undefined'||typeof ERROR_GROUPS==='undefined'||typeof ERROR_GROUP_OF==='undefined')return;
  if(!ERROR_GROUPS.some(function(g){return g[0]==='journal';}))ERROR_GROUPS.unshift(['journal',['Events and states','События и состояния']]);
  Object.keys(JOURNAL_TYPES).forEach(function(key){var t=JOURNAL_TYPES[key];if(!ERROR_ROWS.some(function(r){return r[0]===t.code;}))ERROR_ROWS.push([t.code,'journal',t.label[0],t.label[1],t.meaning[0],t.meaning[1],t.message[0]+'. Read the separate saved reason code if present; observation and a confirmed route change are different.',t.message[1]+'. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.']);ERROR_GROUP_OF[t.code]='journal';});
  ['OPERATOR-MANUAL','OPERATOR-RETURN'].forEach(function(code){var r=ERROR_ROWS.find(function(r){return r[0]===code;});if(r){r[2]=code==='OPERATOR-MANUAL'?'Manual-channel control command':'Return-control command';r[3]=code==='OPERATOR-MANUAL'?'Команда ручного выбора канала':'Команда возврата маршрута';r[4]='This is the manual-control command family, not proof that a human clicked. The recorded initiator distinguishes operator, automation, test or programmatic access.';r[5]='Это семейство команд ручного управления, а не доказательство нажатия человеком. Сохранённый инициатор различает оператора, автоматику, тест или программный доступ.';}});
}
var EVENT_SEVERITY_CODES=(function(o){[['critical','ROLLBACK-GIVEN-UP PAIR-RECOVERY-REQUIRED RECOVERY-REQUIRED STATE-FILE-DAMAGED STORAGE-001 CONFIG-001 LUA-CORE-UNAVAILABLE EXTERNAL-POLICY-CHANGE-GUARD-RETAINED ROLLBACK-UNVERIFIED-GUARD-RETAINED FOREIGN-GUARD-TABLE NFT-GUARD-UNAVAILABLE KILLSWITCH-NOT-ENABLED AUTO-OPTIONS-NOT-CLEARED WATCHDOG-DID-NOT-ARM CONTROL-REVISION-STALE SYSTEM-001 NATIVE-SYSTEM-001 PAIR-SYSTEM-001 STOPPED-NO-HEALTHY-PATH MANUAL-SUPERVISOR-UNAVAILABLE UNSUPPORTED-BOARD UNSUPPORTED-FIRMWARE TERMS-NOT-ACCEPTED RESTART-INTERRUPTED-SWITCH FAILED'],
 ['medium','RESERVE-FAILED-PRIMARY-VERIFIED RELEASE-PENDING AUTO-RESUME-PENDING'],
 ['low','OK RECOVERY OBSERVING OBSERVATION RUNNING IDLE STARTING QUEUED CLAIMED CANCELLED STOPPED DISABLED ARMED APPLYING WAIT-CLIENT RESTORING RETURNED TRIAL-REQUIRED PAIR-WATCHING PRIMARY-RECOVERED-BEFORE-SWITCH PAIR-CONNECTING PAIR-WAITING-PROBES PAIR-WAITING-VENDOR PAIR-STOPPED PAIR-CLEANUP PAIR-READOPTED VENDOR-SETTLING VENDOR-FIRST-OBSERVATION CLIENT-STOP SERVICE-STOPPED RESTORE-PRIMARY TRIAL-PASSED TRIAL-ENDED OPERATOR-MANUAL OPERATOR-RETURN OPERATOR-TRIAL OPERATOR-HOLD-RESERVE SELECTED-BY-CONTROLLER LINK-UP EXTERNAL-POLICY-CHANGE-RELEASED RESTART-CLEAN RESTART-PLANNED-REBOOT RESTART-FIRST-START STOP-SUPERSEDED-START STOP-SUPERSEDED-MANUAL EVENT-ROUTER-OBSERVATION']].forEach(function(p){p[1].split(' ').forEach(function(c){o[c]=p[0];});});return o;})(Object.create(null));
function codeSeverity(code){
  if(typeof code!=='string'||!code)return null;
  if(EVENT_SEVERITY_CODES[code])return EVENT_SEVERITY_CODES[code];
  if(/^(GUARD|JOURNAL|HISTORY|LUA-AUTO|HV-CORE|UNSAFE|DEPENDENCY|DEVICE-MODEL)-/.test(code))return 'critical';
  if(/-(OK|SAVED|DELIVERED|COMPLETE|READY|VERIFIED|CONFIRMED|HEALTHY|RECOVERED|PENDING|WAITING|QUEUED|REQUESTED)$/.test(code))return 'low';
  return /^(AUTO|PAIR|MANUAL|LIFECYCLE|LEASE|NATIVE|COMMAND)-.*FAILED$/.test(code)?'critical':null;
}
function journalHistoryDays(status){
  var values=[((status.accounting||{}).reliability||{}).detail_days,(status.native_history||{}).detail_days].filter(function(n){return Number.isInteger(n)&&n>=1&&n<=7;});
  return values.length?Math.min.apply(Math,values):7;
}
function journalSourceLabel(source){
  return source==='manual'?bi('you, manually','вы, вручную'):source==='automatic'?bi('Auto, automatically','Auto, автоматически'):source==='test'?bi('programmatic test','тестовая программа — автоматически'):source==='programmatic'?bi('program command','команда программы'):bi('source not recorded','источник не указан');
}
function journalToken(value,fallback){return typeof value==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(value)?value.toUpperCase():fallback;}
function journalLatencySample(raw,profile,eventTime){
  if(typeof profile!=='string'||!/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(profile)||!raw||typeof raw!=='object'||raw.profile!==profile||raw.metric!=='https-rtt-ms'||!Number.isFinite(eventTime)||!Number.isFinite(raw.time)||raw.time<eventTime-90||raw.time>eventTime+5||!Number.isFinite(raw.rtt_ms)||raw.rtt_ms<0||raw.rtt_ms>600000||typeof raw.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(raw.interface)||(profile.indexOf('wireguard:')===0)!==(raw.interface.indexOf('wgclient')===0)||typeof raw.generation!=='string'||!/^[a-f0-9]{32}$/.test(raw.generation))return null;
  return {profile:profile,metric:'https-rtt-ms',time:raw.time,rtt_ms:raw.rtt_ms,interface:raw.interface,generation:raw.generation};
}
function journalWebsiteSample(raw,profile,time){
  if(typeof profile!=='string'||!/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(profile)||!raw||raw.profile!==profile||raw.metric!==WEBSITE_METRIC||raw.target_set!==WEBSITE_TARGET_SET||['ok','partial','failed'].indexOf(raw.state)<0||!Number.isInteger(raw.successes)||raw.successes<0||raw.successes>3||raw.attempted!==3||!Number.isFinite(raw.time)||!Number.isFinite(time)||time-raw.time< -5||time-raw.time>45||typeof raw.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(raw.interface)||(profile.indexOf('wireguard:')===0)!==(raw.interface.indexOf('wgclient')===0)||typeof raw.generation!=='string'||!/^[a-f0-9]{32}$/.test(raw.generation)||raw.vendor_tunnel_id!==(raw.interface.indexOf('wgclient')===0?'wireguard:':'openvpn:')+raw.interface||!Array.isArray(raw.site_ms)||raw.site_ms.length!==3||!raw.site_ms.every(function(v){return v===null||Number.isFinite(v)&&v>=0&&v<=6000;})||raw.site_ms.filter(function(v){return v!==null;}).length!==raw.successes)return null;
  if(raw.successes===3){if(raw.state!=='ok'||!Number.isFinite(raw.avg_ms)||raw.avg_ms<0||raw.avg_ms>6000||Math.abs(raw.avg_ms-raw.site_ms.reduce(function(a,b){return a+b;},0)/3)>.051)return null;}
  else if(raw.avg_ms!=null||raw.state!==(raw.successes?'partial':'failed'))return null;
  return {rtt_ms:raw.successes===3?raw.avg_ms:null,time:raw.time,successes:raw.successes};
}
function journalLatencyText(entry){
  var transition=savedTransition(entry),reverse=['RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0||entry.return_primary===true,profile=transition.present?(transition.changed&&!transition.reapply&&transition.to?entry[transition.to]:null):reverse?entry.source:entry.target;
  if(entry.website_response){var web=journalWebsiteSample(entry.website_response,profile,entry.time);return web&&web.rtt_ms!==null?bi('Three-site response: ','Ответ трёх сайтов: ')+websiteMs(web.rtt_ms)+' '+bi('ms','мс'):bi('Three-site response: —','Ответ трёх сайтов: —')+(web?' · '+web.successes+'/3':'');}
  var sample=journalLatencySample(entry.latency,profile,entry.time);
  return sample?bi('Technical health HTTPS: ','Техническая HTTPS-проверка: ')+sample.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')+' · '+bi('measured ','замер ')+new Date(sample.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):bi('Delay: no saved measurement at this event','Задержка: нет сохранённого замера на момент события');
}
function journalAutoStateText(entry,transition,names){
  var codes=[entry.code].concat(Array.isArray(entry.codes)?entry.codes:[]).filter(function(c){return typeof c==='string'&&c;});
  var where=transition.to&&names[transition.to]?bi(' · traffic on the ',' · трафик на ')+names[transition.to]+bi(' channel',' канале'):'';
  if(codes.indexOf('PAIR-MANUAL-HOLD-PRIMARY')>=0)return bi('Auto works · primary channel chosen by you','Auto работает · основной канал выбран вручную');
  if(codes.indexOf('PAIR-MANUAL-HOLD-RESERVE')>=0)return bi('Auto works · reserve channel chosen by you','Auto работает · резервный канал выбран вручную');
  var waiting=codes.filter(function(c){return !/^(PAIR-WATCHING|EVENT-|OPERATOR-)/.test(c);})[0];
  if(waiting){var row=typeof journalCodeRow==='function'?journalCodeRow(waiting):null;return bi('Auto works · waiting: ','Auto работает · ожидание: ')+(row?bi(row[2],row[3]):waiting)+where;}
  return bi('Auto works · channel unchanged','Auto работает · канал не менялся')+where;
}
function journalMessage(entry,status,hideCode){
  var t=journalDefinition(entry),text=bi(t.message[0],t.message[1]);
  var profiles=Array.isArray(status.profiles)?status.profiles:[],p=profiles.find(function(p){return p.id===entry.profile;});
  if(entry.code==='VPN-003'&&entry.probe)text=entry.probe.https_success>0?bi('HTTPS checks passed partially; some traffic is passing','HTTPS-проверки прошли частично; часть трафика проходит'):bi('HTTPS availability was not confirmed by this check','Эта проверка не подтвердила HTTPS-доступность');
  if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')text=entry.role==='source'?bi('Connection restored on the primary channel','Соединение восстановлено на основном канале'):entry.role==='target'?bi('Connection restored on the reserve channel','Соединение восстановлено на резервном канале'):bi('Connection restored · channel was not saved in this record','Соединение восстановлено · канал не сохранён в этой записи');
  else if(entry.profile)text=(entry.role==='source'?bi('Primary channel','Основной канал'):entry.role==='target'?bi('Reserve channel','Резервный канал'):bi('VPN profile','VPN-профиль'))+' — '+text;
  var transition=savedTransition(entry);
  if(transition.present){
    var names={source:bi('primary','основной'),target:bi('reserve','резервный')},direction=transition.to?(transition.changed&&transition.from?names[transition.from]+' → '+names[transition.to]:names[transition.to]):null;
    if(transition.outcome==='refused')text=bi('Channel selection request was refused','Запрос выбора канала отклонён')+(transition.to?' · '+names[transition.to]:'');
    else if(transition.reapply)text=transition.completed&&transition.outcome==='policy-verified'?bi('VPN rules verified; channel order unchanged','Правила VPN проверены; порядок каналов не изменился'):bi('Applying VPN rules again; no channel switch is claimed','Повторное применение правил VPN; переключение канала не заявлено');
    else if(transition.unchanged)text=journalAutoStateText(entry,transition,names);
    else if(!direction)text=bi('Switch direction was not saved; see the recorded reason','Направление перехода не сохранено; смотрите записанную причину');
    else if(transition.completed&&transition.outcome==='restored')text=bi('Return confirmed: ','Возврат подтверждён: ')+direction;
    else if(transition.completed&&transition.outcome==='committed')text=(transition.changed&&transition.from?bi('Switch confirmed: ','Переход подтверждён: '):bi('Channel selected: ','Выбран канал: '))+direction;
    else text=(transition.changed&&transition.from?bi('Switch requested: ','Запрошен переход: '):bi('Channel selection requested: ','Запрошен выбор канала: '))+direction;
  }else{
    if(entry.state==='APPLYING')text=bi('Switch: primary → reserve','Переход: основной → резервный');
    if(entry.state==='RESTORING')text=bi('Switch: reserve → primary','Переход: резервный → основной');
    if(entry.return_primary)text=bi('Returned: reserve → primary','Возврат: резервный → основной');
  }
  var sourced=transition.present&&transition.changed||entry.origin==='control'||entry.action_source||['APPLYING','RESTORING','COMMITTED','ROLLED-BACK','STOPPED'].indexOf(entry.state)>=0;
  var switching=transition.present?transition.changed&&!transition.reapply&&transition.outcome!=='refused':entry.return_primary===true||['APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE','RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0;
  var code=!hideCode&&entry.code&&entry.code!=='OK'&&entry.code!==entry.state?' · '+entry.code:'';
  if(entry.probe){
    text+=' · HTTPS '+entry.probe.https_success+'/3 · '+(entry.probe.dns_ok===true?bi('DNS passed','DNS прошёл'):entry.probe.dns_ok===false?bi('DNS failed','DNS не прошёл'):bi('DNS result unavailable','Результат DNS не сохранён'));
    entry.probe.checks.filter(function(c){return c.result==='http-unsupported';}).forEach(function(c){text+=' · '+bi('Check endpoint incompatible: ','Несовместимый проверочный адрес: ')+c.target+(c.http_status?' (HTTP '+c.http_status+')':'');});
  }
  return text+(entry.timing?' · ⏱ '+entry.timing:'')+(entry.profile?' · '+(p?serverTitle(p):entry.profile):'')+(sourced?' · '+journalSourceLabel(entry.action_source):'')+(switching?' · '+journalLatencyText(entry):'')+code;
}
function journalProbeSnapshot(e,profile,status,code){
  if(!code&&(e.kind==='FAILURE'||e.state==='FAILURE'))return null;
  if(!profile||['VPN-001','VPN-003','DNS-001','VPN-MTU','OK',null].indexOf(code)<0)return null;
  var expected=code==='OK'?null:code;
  function sameCode(r){return (r.code==='OK'?null:r.code||null)===expected;}
  function count(r){return Number.isInteger(r.https_success)&&r.https_success>=0&&r.https_success<=3;}
  var stamp=Number.isFinite(e.measurement_time)&&e.measurement_time>0&&e.measurement_time<=e.time+5?e.measurement_time:null;
  var row=stamp!==null&&count(e)?e:null;
  if(!row){
    var snapshots=(status.events||[]).filter(function(r){return r.profile===profile&&sameCode(r)&&count(r)&&Number.isFinite(r.measurement_time)&&Math.abs(r.measurement_time-(stamp===null?e.time:stamp))<.001;});
    if(snapshots.length===1){row=snapshots[0];stamp=row.measurement_time;}
  }
  if(!row){
    var samples=(status.samples||[]).filter(function(r){return r.id===profile&&sameCode(r)&&count(r)&&Number.isFinite(r.time)&&(stamp!==null?Math.abs(r.time-stamp)<.001:r.time<=e.time+.001&&e.time-r.time<=10);});
    var exact=samples.filter(function(r){return Math.abs(r.time-e.time)<.001;});if(exact.length===1)samples=exact;
    if(samples.length===1){row=samples[0];stamp=row.time;}
  }
  if(!row)return null;
  var checks=(Array.isArray(row.probe_checks)?row.probe_checks:[]).slice(0,3).filter(function(r){return r&&['one.one.one.one','dns.google','dns.quad9.net'].indexOf(r.target)>=0&&['ok','http-unsupported','http-error','timeout','tls-error','transport-error','invalid-response','unknown'].indexOf(r.result)>=0;}).map(function(r){return {target:r.target,result:r.result,http_status:Number.isInteger(r.http_status)&&r.http_status>=100&&r.http_status<=599?r.http_status:null};});
  return {time:stamp,https_success:row.https_success,dns_ok:typeof row.dns_ok==='boolean'?row.dns_ok:null,checks:checks};
}
function journalRows(status,stored,now){
  var retainedSeconds=journalHistoryDays(status)*86400;
  var groups=[['controller',stored?stored.controller.events:(status.native_history||{}).events||[]],['failures',stored?stored.failures.events:((status.accounting||{}).reliability||{}).events||[]],['monitor',stored?[]:status.events||[]]],result=[],seen=Object.create(null);
  function control(action,stamp,source){
    if(['start','stop'].indexOf(action)<0||!Number.isFinite(stamp)||stamp<=0||stamp<now-retainedSeconds||stamp>now+5)return;
    var key='control:'+action+':'+stamp;if(seen[key])return;seen[key]=true;
    result.push({key:key,time:stamp,state:action==='start'?'AUTO-START-REQUESTED':'AUTO-STOP-REQUESTED',kind:'CONTROL',profile:null,code:null,level:'warning',origin:'control',action_source:['manual','automatic','test','programmatic'].indexOf(source)>=0?source:'unknown'});
  }
  groups.forEach(function(group){if(!Array.isArray(group[1]))return;
    group[1].slice(-10000).forEach(function(e){
      if(!e||!Number.isFinite(e.time)||e.time<now-retainedSeconds||e.time>now+5)return;
      control(e.control_action,e.control_time,e.control_source);
      var state=journalToken(e.state||e.kind||e.code,'OBSERVATION'),code=typeof e.code==='string'&&safeCode(e.code)?e.code:Array.isArray(e.codes)?e.codes.find(safeCode)||null:null;
      var profile=typeof(e.profile||e.id)==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e.profile||e.id)?e.profile||e.id:null;
      if(state==='STOPPED'&&e.control_action==='start'&&Number.isFinite(e.control_time)&&e.control_time<=e.time&&e.time-e.control_time<=30){state='STARTING';if(code==='CLIENT-STOP')code=Array.isArray(e.codes)?e.codes.find(function(c){return c!=='CLIENT-STOP'&&safeCode(c);})||null:null;}
      var probe=journalProbeSnapshot(e,profile,status,code);
      var family=state==='FAILURE'||['VPN-001','VPN-003','DNS-001','VPN-MTU'].indexOf(code)>=0?'failure':state==='RECOVERY'||code==='OK'?'recovery':null;
      var key=probe&&family?'measurement:'+profile+':'+probe.time+':'+family:group[0]+':'+(Number.isSafeInteger(e.sequence)?e.sequence:[e.time,profile,state,code].join(':'));
      if(seen[key])return;seen[key]=true;
      var failed=/FAIL|REFUS|ERROR|DEGRADED/.test(state)||!!code&&/^(DNS-|VPN-|SYSTEM-|CHECK-)|FAILED|ERROR|REFUSED/.test(code),level=failed?'error':/GAP|UNKNOWN|UNCONFIRMED|UNAVAILABLE|UNVERIFIED|CANCEL|INACTIVE/.test(state+' '+(code||''))?'warning':'ok';
      var pair={};['source','target'].forEach(function(k){pair[k]=typeof e[k]==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e[k])?e[k]:null;});
      var actionSource=['manual','automatic','test','programmatic','unknown'].indexOf(e.transition_source)>=0?e.transition_source:e.manual===true?'unknown':e.trial===true?'test':null;
      if(!actionSource&&Array.isArray(e.codes)){
        if(e.codes.some(function(c){return c==='OPERATOR-MANUAL'||c==='OPERATOR-RETURN';}))actionSource='unknown';
        else if(e.codes.some(function(c){return c==='OPERATOR-TRIAL'||c==='TRIAL-PASSED';}))actionSource='test';
        else if(e.codes.some(function(c){return ['SOURCE-FAILED','PRIMARY-STABLY-RECOVERED','RESERVE-FAILED-PRIMARY-VERIFIED'].indexOf(c)>=0;}))actionSource='automatic';
      }
      if(!actionSource&&state==='STOPPED'&&e.control_action==='stop')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      if(!actionSource&&state==='STARTING'&&e.control_action==='start')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      var returnPrimary=state==='STOPPED'&&Array.isArray(e.codes)&&e.codes.indexOf('OPERATOR-RETURN')>=0;
      var transition=savedTransition(e),delayProfile=transition.present?(transition.changed&&!transition.reapply&&transition.to?pair[transition.to]:null):(returnPrimary||['RESTORING','ROLLED-BACK'].indexOf(state)>=0)?pair.source:pair.target;
      var role=['source','target'].indexOf(e.role)>=0?e.role:null;
      if(!role&&profile&&pair.source&&pair.target&&pair.source!==pair.target)role=profile===pair.source?'source':profile===pair.target?'target':null;
      var record={key:key,time:e.time,state:state,kind:journalToken(e.kind,'OBSERVATION'),code:code,profile:profile,role:role,source:pair.source,target:pair.target,original_restored:e.original_restored===true,return_primary:returnPrimary,latency:journalLatencySample(e.latency,delayProfile,e.time),action_source:actionSource,level:level,origin:group[0],probe:probe,outage_seconds:Number.isFinite(e.observed_duration_seconds)&&e.observed_duration_seconds>=0?e.observed_duration_seconds:null,fault:[].concat(e.codes,e.code).find(function(c){return /^(SUPERVISOR-RECOVERY|ROLLBACK-(GIVEN-UP|UNVERIFIED)|JOURNAL-INTEGRITY-FAILED)$/.test(c);})||null};
      if(Object.prototype.hasOwnProperty.call(e,'website_response')){
        record.website_response={};if(journalWebsiteSample(e.website_response,delayProfile,e.time)){['profile','metric','target_set','state','time','avg_ms','successes','attempted','interface','generation','vendor_tunnel_id'].forEach(function(k){record.website_response[k]=e.website_response[k];});record.website_response.site_ms=e.website_response.site_ms.slice();}
      }
      if(transition.present){
        record.transition_metadata_present=true;
        ['from_role','destination_role','before_policy_role'].forEach(function(key){if(e[key]==='source'||e[key]==='target')record[key]=e[key];});
        ['from_profile_id','destination_profile_id'].forEach(function(key){if(typeof e[key]==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(e[key]))record[key]=e[key];});
        ['route_changed','transition_completed','activation_reapply'].forEach(function(key){if(typeof e[key]==='boolean')record[key]=e[key];});
        if(['committed','restored','refused','policy-verified'].indexOf(e.transition_outcome)>=0)record.transition_outcome=e.transition_outcome;
        record.return_primary=transition.completed&&transition.outcome==='restored'&&transition.to==='source';
      }
      var definition=journalDefinition(record);if(!(definition.code==='EVENT-DETAILS-NOT-SAVED'&&record.level==='error'))record.level=definition.level||record.level;result.push(record);
    });
  });
  var request=status.auto_control||{};
  if(request.requested==='on'||request.requested==='off')control(request.request_action,request.requested_at,request.request_source);
  if(typeof switchTimeline==='function')switchTimeline(result);
  return result.sort(function(a,b){return b.time-a.time||a.key.localeCompare(b.key);});
}
function spanText(s){
  if(!Number.isFinite(s)||s<0)return '—';
  if(s<10)return Math.round(s*1000)+bi(' ms',' мс');  // owner 01.11: fast switches are 0.5-0.8 s, never "0 s"
  if(s<60)return String(Math.round(s*10)/10).replace('.',locale==='ru'?',':'.')+bi(' s',' с');
  s=Math.round(s);
  var h=Math.floor(s/3600),m=Math.floor(s%3600/60),r=s%60,u=function(n,en,ru){return n+bi(' '+en,' '+ru);};
  return h?u(h,'h','ч')+(m?' '+u(m,'min','мин'):''):m?u(m,'min','мин')+(r?' '+u(r,'s','с'):''):u(r,'s','с');
}
function switchKind(r){
  if(r.action_source==='manual'||/^OPERATOR-(MANUAL|RETURN)$/.test(r.code||''))return 'manual';
  return r.action_source==='test'?'test':r.action_source==='automatic'||/^(SOURCE-FAILED|PRIMARY-STABLY-RECOVERED|RESERVE-FAILED)/.test(r.code||'')?'auto':'unknown';
}
function switchTimeline(records){
  var list=(records||[]).slice().sort(function(a,b){var o={failures:0,monitor:1,controller:2};function n(r){var m=/:(\d+)$/.exec(r.key||'');return m?+m[1]:0;}
    return a.time-b.time||(o[a.origin]||0)-(o[b.origin]||0)||n(a)-n(b);});
  var episodes=[],cur=null,fails={},ups={},WEEK=7*86400;
  list.forEach(function(r){delete r.timing;});
  function d(a,b){var v=b-a;return a!=null&&b!=null&&Number.isFinite(v)&&v>=0&&v<=WEEK?v:null;}
  function note(r,text){if(text)r.timing=r.timing?r.timing+' · '+text:text;}
  function open(r,props){cur=Object.assign({key:r.key,source:r.source,target:r.target,kind:switchKind(r),failure:null,start:null,reserve:null,returnStart:null,back:null,rolledBack:null,recovery:null,down:null,returnKind:null},props);episodes.push(cur);return cur;}
  list.forEach(function(r){
    var failed=r.state==='FAILURE'||r.kind==='FAILURE',up=r.state==='RECOVERY'||r.kind==='RECOVERY';
    if(failed&&r.profile){if(!fails[r.profile])fails[r.profile]=r;return;}
    if(up&&r.profile){
      var down=Number.isFinite(r.outage_seconds)&&r.outage_seconds>=0?r.outage_seconds:null;delete fails[r.profile];ups[r.profile]=r;
      if(down!==null)note(r,(r.role==='source'?bi('primary channel was down ','основной канал не работал '):r.role==='target'?bi('reserve channel was down ','резервный канал не работал '):bi('channel was down ','канал не работал '))+spanText(down));
      if(cur&&cur.source===r.profile&&cur.reserve!==null&&cur.back===null&&cur.recovery===null){cur.recovery=r.time;cur.down=down;}
      return;
    }
    var g=r.fault,gu=/GIVEN|INTEGRITY/.test(g),rc=cur&&cur.kind==='recovery';
    if(rc&&!cur.closed&&r.state==='AUTO-START-REQUESTED'){cur.closed=1;cur.outcome='restart';}
    if(g&&!(rc&&cur.outcome==='gave-up'&&gu)){
      if(rc&&cur.outcome==='gave-up'){cur.closed=0;cur.outcome=cur.end=null;}
      else if(!rc||cur.closed){
        var o=cur&&!cur.closed&&cur.back===null&&cur.rolledBack===null;
        if(o&&cur.restore&&cur.reserve===null){delete cur.restore.timing;cur.kind='recovery';cur.rec=cur.start;cur.start=cur.failure=null;}
        else{if(o){cur.closed=1;cur.cut=r.time;}open(r,{kind:'recovery',rec:r.time});}
        note(r,bi('recovery after a fault or restart','восстановление после сбоя'));
      }
      if(gu){cur.closed=1;cur.outcome='gave-up';cur.code=g;cur.end=r.time;}
    }
    var t=savedTransition(r),s=r.state,dir=null,done=false;
    if(t.present){if(t.changed&&!t.reapply&&!t.unchanged&&t.outcome!=='refused'&&!t.invalid){dir=t.to;done=t.completed&&(t.outcome==='committed'||t.outcome==='restored');}}
    else{dir=['APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE'].indexOf(s)>=0?'target':['RESTORING','ROLLED-BACK'].indexOf(s)>=0||r.return_primary?'source':null;done=s==='COMMITTED'||s==='ROLLED-BACK'||r.return_primary;}
    if(!dir)return;
    if(cur&&cur.kind==='recovery'&&!cur.closed){
      if(done){cur.closed=1;cur.outcome=dir;cur.end=r.time;if(r.time>cur.rec)note(r,bi('recovery ','восстановление ')+spanText(r.time-cur.rec));return;}
      if(s!=='APPLYING')return;cur.closed=1;
    }
    var starting=!done&&(s==='APPLYING'||s==='RESTORING'),c=cur&&!cur.closed?cur:null,shut=!c||c.back!==null||c.rolledBack!==null;
    if(dir==='target'&&starting){
      if(c&&c.start!==null&&c.reserve===null&&c.rolledBack===null)return;
      var f=r.source&&fails[r.source];if(f&&d(f.time,r.time)===null)f=null;
      open(r,{start:r.time,failure:f?f.time:null,restore:s==='RESTORING'&&r});
      if(f)note(r,bi('failure confirmed ','сбой подтверждён за ')+spanText(r.time-f.time)+bi(' after the first failed check',' после первой неудачной проверки'));
    }else if(dir==='target'&&done){
      if(c&&c.reserve===null&&c.rolledBack===null&&c.returnStart===null&&c.back===null){cur.reserve=r.time;
        if(cur.start!==null)note(r,bi('switch took ','переключение ')+spanText(r.time-cur.start)+bi(' (from switch start)',' (с начала перехода)'));
        if(cur.failure!==null)note(r,bi('from the first failed check ','от первой неудачной проверки ')+spanText(r.time-cur.failure));
      }else if(shut)open(r,{reserve:r.time});
    }else if(dir==='source'&&starting){
      if(c&&c.reserve!==null&&c.returnStart===null&&c.back===null){cur.returnStart=r.time;cur.returnKind=switchKind(r);
        note(r,bi('on the reserve for ','на резерве ')+spanText(r.time-cur.reserve));
        var u=cur.source&&ups[cur.source];if(u&&u.time>=cur.reserve&&u.time<=r.time)note(r,bi('primary working again for ','основной снова работает ')+spanText(r.time-u.time));
      }else if(shut)open(r,{returnStart:r.time,returnKind:switchKind(r)});
    }else if(dir==='source'&&done){
      if(c&&c.start!==null&&c.reserve===null&&c.rolledBack===null){cur.rolledBack=r.time;note(r,bi('attempt ended without a switch after ','попытка завершилась без переключения через ')+spanText(r.time-cur.start));}
      else if(c&&(c.reserve!==null||c.returnStart!==null)&&c.back===null){cur.back=r.time;if(!cur.returnKind)cur.returnKind=switchKind(r);
        if(cur.returnStart!==null)note(r,bi('return took ','возврат ')+spanText(r.time-cur.returnStart)+bi(' (from return start)',' (с начала возврата)'));
        if(cur.reserve!==null)note(r,bi('reserve used for ','на резерве ')+spanText(r.time-cur.reserve));
        if(cur.failure!==null)note(r,bi('whole episode ','весь эпизод ')+spanText(r.time-cur.failure)+bi(' from the first failed check',' от первой неудачной проверки'));
      }else if(shut)open(r,{back:r.time,returnKind:switchKind(r)});
    }
  });
  episodes.forEach(function(e){
    e.detect=d(e.failure,e.start);e.switching=d(e.start,e.reserve);e.total=d(e.failure,e.reserve);e.onReserve=d(e.reserve,e.returnStart);e.returning=d(e.returnStart,e.back);
    e.time=[e.failure,e.start,e.reserve,e.returnStart,e.back,e.rec].find(Number.isFinite);
  });
  return episodes;
}
function switchStatsModel(status){
  status=status||{};var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  return {now:now,episodes:switchTimeline(journalRows(status,null,now)),timing:status.switch_timing&&typeof status.switch_timing==='object'?status.switch_timing:null,history:!!(status.native_history&&Array.isArray(status.native_history.events))};
}
var LATENCY_HISTORY_SECONDS=7*86400;
function latencyHistoryRows(status,inventory,now){
  var h=status.website_response_history||{},ids=rolePairIds(status,inventory,now);
  if(h.version!==1||!responseHistoryKind(h)||h.row_encoding!=='sum-tenths'||!Array.isArray(h.pair)||h.pair.length!==2||h.pair[0]!==ids[0]||h.pair[1]!==ids[1])return [];
  var rows=h.rows;
  if(h.rows_json!==undefined){
    if(typeof h.rows_json!=='string'||h.rows_json.length>850000)return [];
    try{rows=JSON.parse(h.rows_json);}catch(error){return [];}
  }
  if(!Array.isArray(rows)||rows.length>10081||h.rows_count!==undefined&&(!Number.isInteger(h.rows_count)||h.rows_count!==rows.length))return [];
  return rows.filter(function(r){return Array.isArray(r)&&r.length===6&&Number.isFinite(r[0])&&r[0]>=now-LATENCY_HISTORY_SECONDS&&r[0]<=now+5&&[1,2].every(function(i){return Number.isInteger(r[i+2])&&r[i+2]>=0&&r[i+2]<=120&&(r[i+2]===0?r[i]===null:Number.isInteger(r[i])&&r[i]>=0&&r[i]<=60000*r[i+2]);})&&['source','target','unknown','off','switching','blocked','down'].indexOf(r[5])>=0;}).map(function(r){var decoded=r.slice();[1,2].forEach(function(i){decoded[i]=r[i+2]?r[i]/(10*r[i+2]):null;});return decoded;}).sort(function(a,b){return a[0]-b[0];});
}
function rolePairIds(status,inventory,now){
  var settings=(inventory||{}).settings||{},rows=(status||{}).profiles||[];
  function member(role,key){
    var p=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,role,now):null;
    return p&&p.id||settings[key]||(status.native_failover||{})[role]||null;
  }
  return [member('source','plan_source'),member('target','plan_target')];
}
function endpointText(p,now){
  var e=p&&p.server_endpoint;
  if(!e||typeof e!=='object'||e.source!=='live-kernel-peer'||p.vendor_state!=='SETTLED'||!observationFresh(p,now)||typeof p.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(p.interface)||e.profile!==p.id||e.interface!==p.interface||!Number.isFinite(e.time)||now-e.time< -5||now-e.time>observationValidFor(p)||typeof e.host!=='string'||!/^[A-Fa-f0-9.:-]{1,100}$/.test(e.host)||!Number.isInteger(e.port)||e.port<1||e.port>65535||['tcp','udp'].indexOf(e.transport)<0)return bi('Server address: not observed','Адрес сервера: не получен');
  var host=e.host.indexOf(':')>=0?'['+e.host+']':e.host;
  return bi('Server: ','Сервер: ')+host+':'+e.port+' · '+e.transport.toUpperCase();
}
function simpleHomeEntry(evidence){
  var e=evidence&&typeof evidence==='object'?evidence:{};
  var fresh=e.statusFresh===true&&e.controllerFresh===true;
  return {page:'home',showCard:true,
    reason:!fresh?'CURRENT-STATUS-REQUIRED':e.autoRunning===true?'AUTO-READY-RUNNING':'AUTO-NOT-CONFIRMED-RUNNING',
    statusFresh:e.statusFresh===true,controllerFresh:e.controllerFresh===true,
    autoRunning:fresh&&e.autoRunning===true};
}
function simpleHomeAutoEnabled(status,now,light){return autoEnabled(light||autoLightModel(status,{},now));}
function simpleHomeHealth(profile,now,unavailable){
  if(unavailable||!profile)return {state:'unknown',label:bi('No fresh data','Нет свежих данных')};
  var health=profileHealth(profile,now);
  return {state:health.state,label:health.state==='healthy'?bi('Available','Доступен'):health.state==='failed'?bi('Unavailable','Недоступен'):health.state==='inactive'?bi('Tunnel is off','Туннель отключён'):bi('No fresh data','Нет свежих данных')};
}
function simpleHomeModel(status,inventory,now){
  status=status||{};inventory=inventory||{};
  var ns=status.native_failover||{},control=autoControlModel(status,now);
  var source=vendorDisplayMember(status,inventory,'source',now,ns.source),target=vendorDisplayMember(status,inventory,'target',now,ns.target);
  var waiting=ns.state==='BLOCKED'&&Array.isArray(ns.blockers)&&ns.blockers.length&&ns.blockers.every(function(code){return AUTO_TRANSIENT.indexOf(code)>=0;});
  var path=(waiting?heldConfirmedPath:manualConfirmedPath)(status,source,target,now);
  var lost=!!status.error||!!status.rpc_error,light=autoLightModel(status,inventory,now),unavailable=lost||!observationFresh(status,now);
  var decision=simpleHomeEntry({statusFresh:!status.error&&!status.rpc_error&&observationFresh(status,now),controllerFresh:control.fresh,autoRunning:simpleHomeAutoEnabled(status,now,light)});
  var operation=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null,manual=manualOperationModel(status,now);
  var sourceHealth=simpleHomeHealth(source,now,unavailable),targetHealth=simpleHomeHealth(target,now,unavailable);
  var selected=unavailable?null:path.selected,activeHealth=selected==='source'?sourceHealth:selected==='target'?targetHealth:null;
  decision.source=source;decision.target=target;decision.selectedRole=selected;
  decision.sourceHealth=sourceHealth;decision.targetHealth=targetHealth;
  decision.activeHealthy=!!activeHealth&&activeHealth.state==='healthy';
  decision.moving=!unavailable&&(!!path.moving||control.transitioning||manual.busy);
  decision.dataUnavailable=unavailable;decision.connectionLost=lost;decision.control=control;decision.operation=operation;
  decision.enabled=simpleHomeAutoEnabled(status,now,light);decision.actionStop=control.stop||operation==='starting'||operation==='unconfirmed'||!control.fresh;decision.light=light;decision.path=path;
  decision.blockers=control.fresh&&Array.isArray(ns.blockers)?ns.blockers.slice(0,4):[];
  if(path.code&&decision.blockers.indexOf(path.code)<0)decision.blockers.push(path.code);
  decision.setupRequired=!unavailable&&control.off&&!decision.moving&&!operation&&(!source||!target||!source.id||!target.id||source.id===target.id);
  if(control.paused){decision.state='pending';decision.title=bi('Auto paused for speed test','Auto на паузе для теста скорости');decision.summary=bi('Monitoring resumes first, then Auto. Your VPNs stay connected.','Сначала возобновится мониторинг, затем Auto. VPN остаются подключёнными.');}
  else if(unavailable&&(lost||!observationFresh(status,now))){decision.state='unknown';decision.title=bi('No fresh data','Нет свежих данных');decision.summary=lost?bi('Check the connection to the router.','Проверьте связь с роутером.'):bi('The router has not sent fresh measurements.','Роутер не присылает свежие измерения.');}
  else if(!control.fresh){decision.state=light.key==='problem'?'error':'unknown';decision.title=light.title;decision.summary=light.hint;}
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
var preparationPreviewCall=rpc.declare({object:'homensai-vpn',method:'preparation_preview',params:['action']});
var preparationApplyCall=rpc.declare({object:'homensai-vpn',method:'preparation_apply',params:['action','revision','control_revision']});
var preparationBusy=false,preparationDialog=0;
var PREPARATION_ACTIONS={
 'source-autostart':['Disable primary VPN startup','Отключить автозапуск основного VPN','Disable Bring up on boot for the currently selected primary VPN. The running VPN stays connected.','Отключить «Поднимать при загрузке» для текущего выбранного основного VPN. Работающий VPN остаётся подключённым.'],
 'target-autostart':['Disable reserve VPN startup','Отключить автозапуск резервного VPN','Disable Bring up on boot for the currently selected reserve VPN. The running VPN stays connected.','Отключить «Поднимать при загрузке» для текущего выбранного резервного VPN. Работающий VPN остаётся подключённым.'],
 'wg-autostart':['Disable WireGuard startup','Отключить автозапуск WireGuard','Disable Bring up on boot for WireGuard (wgclient1). The running VPN stays connected.','Отключить «Поднимать при загрузке» для WireGuard (wgclient1). Работающий VPN остаётся подключённым.'],
 'ovpn-autostart':['Disable OpenVPN startup','Отключить автозапуск OpenVPN','Disable Bring up on boot for OpenVPN (ovpnclient1). The running VPN stays connected.','Отключить «Поднимать при загрузке» для OpenVPN (ovpnclient1). Работающий VPN остаётся подключённым.'],
 'vpn-boot':['Disable stock VPN startup','Отключить штатный автозапуск VPN','Disable vpn-client startup when the router boots. The running service is not stopped.','Отключить запуск службы vpn-client при включении роутера. Работающая служба не останавливается.'],
 'sfe-boot':['Disable SFE startup','Отключить автозапуск SFE','Disable shortcut-fe startup when the router boots. Loaded acceleration remains until a deliberate router restart.','Отключить запуск shortcut-fe при включении роутера. Работающее ускорение сохранится до отдельной перезагрузки роутера.'],
 'hnat':['Disable hardware acceleration','Отключить аппаратное ускорение','Disable hardware acceleration in the saved settings and the running system. No network/firewall restart or module removal.','Выключить аппаратное ускорение в сохранённых настройках и в работающей системе. Без перезапуска сети/firewall и удаления модулей.'],
 'flow-offload':['Disable firewall offloading','Отключить ускорение firewall','Save both flow-offloading flags as 0. This does not reload the firewall. Auto remains blocked until a separate deliberate router restart applies the setting to live flows.','Сохранить оба флага flow offloading=0. Firewall не перезапускается. Auto останется заблокирован до отдельной перезагрузки роутера, которая применит настройку к действующим потокам.'],
 'sfe-autoload':['Disable SFE module autoload','Отключить автозагрузку модулей SFE','Disable loading SFE modules when the router boots and preserve the verified original startup file. Loaded modules are not forcibly removed.','Отключить загрузку модулей SFE при включении роутера и сохранить проверенный исходный файл запуска. Загруженные модули принудительно не удаляются.']
};
var PREPARATION_REASONS={
 'PREPARATION-STOP-AUTO-FIRST':['Stop Auto and wait for completed recovery before changing preparation.','Сначала остановите Auto и дождитесь завершения восстановления.'],
 'PREPARATION-RECOVERY-REQUIRED':['The previous session or an unconfirmed preparation write needs recovery. Existing changes and backups are retained.','Предыдущая сессия или неподтверждённое изменение подготовки требует восстановления. Изменения и исходные значения сохранены.'],
 'PREPARATION-STALE-REVIEW':['Settings or Auto controls changed after review. Review this action again.','Настройки или управление Auto изменились после просмотра. Проверьте действие заново.'],
 'PREPARATION-PLATFORM-UNVERIFIED':['This button requires a verified GL-MT3000/GL-MT6000 with firmware 4.11.0.','Кнопке нужен проверенный GL-MT3000/GL-MT6000 с прошивкой 4.11.0.'],
 'PREPARATION-HNAT-UNVERIFIED':['The hardware acceleration runtime hook cannot be safely verified. Use the linked GL.iNet settings.','Не удалось безопасно проверить работающий HNAT hook. Используйте ссылку на настройки GL.iNet.'],
 'PREPARATION-PENDING-OR-UNREADABLE':['There are unsaved router changes or settings cannot be read. Resolve them in the router panel first.','Есть несохранённые изменения роутера или настройки не читаются. Сначала проверьте их в панели роутера.'],
 'PREPARATION-WRITE-UNCONFIRMED':['The change could not be confirmed. Do not repeat it blindly; inspect recovery and the saved original values.','Изменение не подтверждено. Не повторяйте его вслепую; проверьте восстановление и сохранённые исходные значения.']
};
PREPARATION_REASONS['PREPARATION-RESTART-REQUIRED']=['The boot setting is saved. Restart this router deliberately before starting Auto; existing live flows/modules are not proof of the new state.','Настройка сохранена. Перед запуском Auto отдельно перезагрузите этот роутер: действующие потоки/модули ещё не подтверждают новое состояние.'];
function preparationReason(code){var row=PREPARATION_REASONS[code];return row?bi(row[0],row[1]):bi('The router refused this change; inspect the code and use the linked settings.','Роутер отказал в изменении; проверьте код и используйте ссылку на настройки.');}
function preparationActionsForCode(code){
 if(code==='PREP-SOURCE-AUTOSTART')return ['source-autostart'];
 if(code==='PREP-TARGET-AUTOSTART')return ['target-autostart'];
 var single={'PREP-WGCLIENT1-AUTOSTART':'wg-autostart','PREP-OVPNCLIENT1-AUTOSTART':'ovpn-autostart','PREP-STOCK-VPN-BOOT':'vpn-boot','PREP-SFE-BOOT':'sfe-boot','PREP-SFE-AUTOLOAD':'sfe-autoload','PREP-HNAT-CONFIG':'hnat','HARDWARE-ACCELERATOR-UNVERIFIED':'hnat','FLOW-OFFLOAD-ENABLED':'flow-offload'};
 if(code==='SOFTWARE-ACCELERATOR-UNVERIFIED'||code==='PREP-SFE-RUNTIME')return ['sfe-boot','sfe-autoload'];
 return Object.prototype.hasOwnProperty.call(single,code)?[single[code]]:[];
}
function preparationNotice(code,uncertain){
 ui.addNotification(null,E('p',{'role':'status'},[E('strong',{},code+' · '),preparationReason(code),uncertain?' '+bi('Some settings may already have changed; the durable recovery record is retained.','Часть настроек уже могла измениться; запись восстановления сохранена.'):'']));
}
function preparationReview(action,button){
 if(preparationBusy)return Promise.resolve();
 preparationBusy=true;button.disabled=true;button.setAttribute('aria-busy','true');
 var token=++preparationDialog;
 return preparationPreviewCall(action).then(function(plan){
  if(token!==preparationDialog)return;
  if(!plan||plan.accepted!==true){preparationNotice(plan&&plan.code||'PREPARATION-UNVERIFIED');return;}
  if(plan.action!==action||typeof plan.revision!=='string'||typeof plan.control_revision!=='string'||typeof plan.already_done!=='boolean'||!/^([a-f0-9]{64})$/.test(plan.revision)||!/^([a-f0-9]{32})$/.test(plan.control_revision)||['mt3000','mt6000'].indexOf(plan.board)<0)throw Error('PREPARATION-REPLY-INVALID');
  var description=PREPARATION_ACTIONS[action];
  var cancel=E('button',{'type':'button','class':'cbi-button','click':function(){preparationDialog++;ui.hideModal();}},bi('Cancel','Отмена'));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-preparation-confirm':action,'click':function(){
   if(preparationBusy||token!==preparationDialog)return;
   preparationBusy=true;apply.disabled=true;cancel.disabled=true;apply.setAttribute('aria-busy','true');
   return preparationApplyCall(action,plan.revision,plan.control_revision).then(function(reply){
    if(!reply||reply.applied!==true||reply.verified!==true||reply.action!==action||reply.auto_started!==false){preparationNotice(reply&&reply.code||'PREPARATION-WRITE-UNCONFIRMED',reply&&reply.change_may_have_applied);return;}
    ui.addNotification(null,E('p',{'role':'status'},bi('The setting was read back and verified. Auto has not been started. Other prerequisites remain separate.','Настройка прочитана заново и проверена. Auto не запускался. Остальные условия проверяются отдельно.')+(reply.restart_required?' '+bi('Loaded acceleration/active flows still need a separate deliberate restart or apply.','Загруженному ускорению/действующим потокам ещё нужно отдельное применение или перезагрузка.') :'')));
   }).catch(function(){preparationNotice('PREPARATION-WRITE-UNCONFIRMED',true);}).finally(function(){preparationBusy=false;preparationDialog++;ui.hideModal();});
  }},bi('Apply this change','Применить это изменение'));
  ui.showModal(bi('Review router change','Проверьте изменение роутера'),[
   E('p',{},bi('This router: GL-','Этот роутер: GL-')+plan.board.toUpperCase()),E('h3',{},bi(description[0],description[1])),E('p',{},bi(description[2],description[3])),plan.interface?E('p',{},bi('Interface: ','Интерфейс: ')+plan.interface):null,
   E('p',{},bi('The original setting is saved privately on this router before writing. A changed review, active Auto or unfinished recovery refuses the write. Auto requires its own explicit Start.','Исходное значение сохраняется приватно в этом роутере до записи. Изменившиеся данные, активный Auto или незавершённое восстановление запрещают запись. Auto требует отдельного явного запуска.')),
   plan.already_done?E('p',{},bi('Already disabled; verified by a fresh read.','Уже отключено; подтверждено свежим чтением.')):null,
   E('div',{'class':'hv-wizard-actions'},[cancel,plan.already_done?null:apply].filter(Boolean))
  ].filter(Boolean));
 }).catch(function(){preparationNotice('PREPARATION-UNVERIFIED');}).finally(function(){preparationBusy=false;button.disabled=false;button.setAttribute('aria-busy','false');});
}
function renderPreparationButtons(code){
 var buttons=preparationActionsForCode(code).map(function(action){var text=PREPARATION_ACTIONS[action];var button=E('button',{'type':'button','class':'cbi-button','data-preparation-action':action,'click':function(){return preparationReview(action,button);}},bi(text[0],text[1]));return button;});
 return buttons.length?E('div',{'class':'hv-preparation-actions'},buttons):null;
}
/* The approved page (router/ui). */
/* Module top level of the approved page: build identity, the bridges the legacy logic and the help module call
   (code links open the code window of this page), the page itself and the LuCI view. */
var HV_AGENT='2.1.0-alpha8',HV_STYLE='HomenS.AI Style 1.14.3',HV_STYLESHEET='ui175.css';
var activeTab='statistics';  // the history list is refreshed every 60 s: the home view shows events
function pageKeyNow(){return '';}
function showErrorCode(code){if(HVX&&HVX.showCode)HVX.showCode(code);}
var HVX=(function(){
/* Shared readings for Simple and Console; Auto presentation comes from AUTO_SIGNAL_TABLE. */
var $=function(s,r){return (r||document).querySelector(s);},$$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));};
var store={get:function(k,d){try{var v=window.localStorage.getItem(k);return v===null?d:v;}catch(e){return d;}},set:function(k,v){try{window.localStorage.setItem(k,v);}catch(e){}}};
var LANG_KEY='homensai-vpn-language',THEME_KEY='homensai-vpn-theme',VIEW_KEY='homensai-vpn-view';
function t(ru,en){return locale==='en'?(en===undefined?ru:en):ru;}
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
var NODATA=function(){return t('нет данных','no data');};
var HV={inv:{settings:{},profiles:[],servers:[]},st:{},root:null,view:'simple',page:'home',tab:'ch',wiz:false,step:1,open:{},dirty:{},draft:null,
  filters:{a:'all',d:'all'},all:false,evOpen:{},probeRows:null,speedRun:null,scan:null,busy:{},theme:'system',codeQ:''};
var V=null;  // the one snapshot of readings for the current paint

/* ---------------- Versions and identity (attribution on every view) ---------------- */
function VER(){
  var st=HV.st||{},s=(HV.inv||{}).settings||{};
  var okv=function(v){return typeof v==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(v);};
  var model=s.detected_router_model==='mt3000'?'GL.iNet GL-MT3000 · Beryl AX':s.detected_router_model==='mt6000'?'GL.iNet GL-MT6000 · Flint 2':'GL.iNet GL-MT6000 · Flint 2 / GL-MT3000 · Beryl AX';
  return {app:okv(st.version)?st.version:HV_AGENT,style:HV_STYLE,model:model,
    detected:s.detected_router_model==='mt3000'||s.detected_router_model==='mt6000',terms:TERMS_VERSION,mismatch:okv(st.version)&&st.version!==HV_AGENT};
}

/* ---------------- Router calls (the same RPCs and arguments as before) ---------------- */
function rpcCall(method,params){return rpc.declare({object:'homensai-vpn',reject:true,method:method,params:params||[],expect:{}});}
function codeOk(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}

/* ---------------- ONE snapshot of readings ---------------- */
function snap(){
  var st=HV.st||{},inv=HV.inv||{},now=statusNow(st);
  var d=simpleHomeModel(st,inv,now),light=d.light;
  var sel=manualSelectionModel(st,d.source,d.target,now);
  var path=Object.assign({},d.path||{},{moving:!!d.moving});
  return {st:st,inv:inv,s:inv.settings||{},now:now,d:d,light:light,control:d.control,op:d.operation,src:d.source,tgt:d.target,sel:sel,path:path,
    manual:manualControlModel(st,now),runs:autoRuns(light),terms:termsAccepted(inv),monitor:monitorLightModel(st,inv,now,false)};
}
function roleProfile(role){return role==='primary'?V.src:V.tgt;}
function profileName(p){
  if(!p)return NODATA();
  var row=((HV.inv||{}).servers||[]).filter(function(r){return r&&r.profile===p.id;})[0];
  return (row&&row.name)||p.name||p.router_name||p.id;
}
function chName(role){var p=roleProfile(role);return p?profileName(p):t('не выбран','not chosen');}
function roleName(role){return role==='primary'?t('Основной','Primary'):t('Резерв','Reserve');}
function ageText(sec){sec=Math.max(0,Math.round(sec));return sec<90?sec+' '+t('с','s'):sec<5400?Math.round(sec/60)+' '+t('мин','min'):Math.round(sec/3600)+' '+t('ч','h');}
function reading(role){
  var p=roleProfile(role),key=role==='primary'?'source':'target';
  if(!p)return {lamp:'n',state:'none',text:t('канал не выбран','channel not chosen'),ms:null,ageText:t('выберите пару в Настройках','choose the pair in Settings'),why:''};
  var h=profileHealth(p,V.now).state,tone=manualChannelTone(p,key,V.path,V.now,V.runs,V.st);
  var stale=V.d.dataUnavailable||h==='unknown';
  if(stale)return {lamp:'n',state:'stale',text:t('нет свежих данных','no fresh data'),ms:null,ageText:t('нет свежих данных','no fresh data'),why:tone.text};
  var delay=channelDelayModel(p,V.st,V.now),ms=delay&&Number.isFinite(delay.rtt_ms)?Math.round(delay.rtt_ms):null;
  var age=t('проверено '+ageText(V.now-p.time)+' назад','checked '+ageText(V.now-p.time)+' ago');
  if(tone.switching&&V.d.moving)return {lamp:'y',state:'switching',text:t('переключение…','switching…'),ms:ms,ageText:age,why:tone.text};
  if(h==='failed')return {lamp:'r',state:'bad',text:t('не отвечает','not responding')+(codeOk(p.code)?' · '+p.code:''),ms:null,ageText:age,why:tone.text,code:p.code};
  if(h==='inactive')return {lamp:'r',state:'bad',text:t('туннель отключён','tunnel is off'),ms:null,ageText:age,why:tone.text};
  if(h==='checking')return {lamp:'y',state:'checking',text:t('проверяется','checking'),ms:ms,ageText:age,why:tone.text};
  return {lamp:'g',state:'ok',text:t('работает','works'),ms:ms,ageText:age,why:tone.text};
}
function selectedRole(){var r=V.d.selectedRole;return r==='source'?'primary':r==='target'?'reserve':null;}
function autoOn(){return autoEnabled(V.light);}
function autoState(){
  var l=V.light;return {lamp:{green:'g',yellow:'y',red:'r',off:'n'}[autoSignal(l)],text:autoStateText(l),sub:[l.title,l.hint,codeOk(l.code)?l.code:''].filter(Boolean).join(' · ')};
}
function overall(){
  var d=V.d,sr=selectedRole(),auto=autoOn();
  if(d.dataUnavailable&&(d.connectionLost||!observationFresh(V.st,V.now)))return {lamp:'n',title:t('Нет свежих данных','No fresh data'),sub:d.connectionLost?t('Нет связи с роутером. Проверьте подключение и обновите страницу.','No connection to the router. Check the connection and reload the page.'):t('Роутер давно не присылал измерений, состояние каналов неизвестно. Нажмите «Проверить сейчас».','The router has not sent measurements for a while; channel state is unknown. Press "Check now".')};
  if(d.dataUnavailable)return {lamp:'n',title:d.title,sub:d.summary};
  if(d.moving)return {lamp:'y',title:t('Переключение…','Switching…'),sub:d.summary};
  if(d.state==='setup')return {lamp:'n',title:d.title,sub:d.summary};
  var a=sr?reading(sr):null,o=sr?reading(sr==='primary'?'reserve':'primary'):null;
  if(!sr)return {lamp:d.state==='error'?'r':d.state==='on'?'g':'y',title:d.title,sub:d.summary};
  if(a.state==='ok'&&sr==='primary')return {lamp:'g',title:t('VPN работает','VPN works'),sub:t('Трафик идёт через основной канал','Traffic uses the primary channel')+(auto?'':t(' · Auto выключен',' · Auto is off'))};
  if(a.state==='ok'){var back=auto&&V.s.recovery_return_policy!=='hold_reserve';
    return {lamp:'y',title:t('Работает резерв','Reserve in use'),sub:o.state==='ok'?t('Основной снова здоров — '+(back?'Auto вернёт трафик по правилам.':'вернуть можно вручную.'),'Primary is healthy again — '+(back?'Auto will return by the rules.':'return manually.')):t('Основной не отвечает. Интернет есть через резерв.','Primary is not responding. Internet goes through the reserve.')};}
  if(a.state==='checking'||a.state==='stale')return {lamp:'y',title:d.title,sub:d.summary};
  if(o.state==='ok')return {lamp:'r',title:t('Текущий канал не отвечает','Current channel is not responding'),sub:auto?t('Auto переключит на '+roleName(sr==='primary'?'reserve':'primary').toLowerCase()+' после '+(Number(V.s.recovery_failures)||3)+' неудачных проверок.','Auto will switch after '+(Number(V.s.recovery_failures)||3)+' failed checks.'):t('Auto выключен. Включите Auto или переключитесь вручную.','Auto is off. Turn Auto on or switch manually.')};
  return {lamp:'r',title:t('Нет интернета через VPN','No internet through the VPN'),sub:t('Оба канала не отвечают. Откройте «Помощь → У меня пропал интернет».','Both channels fail. Open "Help → I have no internet".')};
}

/* ---------------- Time ---------------- */
function fmtTime(sec,withDay){
  if(!Number.isFinite(sec))return '—';
  var opt={timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false};
  var day=function(x){return new Date(x*1000).toLocaleDateString('en-CA',{timeZone:'Europe/Berlin'});};
  var dd=new Date(sec*1000).toLocaleDateString('ru-RU',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit'});
  return (withDay||day(sec)!==day(V?V.now:Date.now()/1000)?dd+' ':'')+new Date(sec*1000).toLocaleTimeString('ru-RU',opt);
}

/* ---------------- Events (journal of the router: one list for every view) ---------------- */
var SWITCH_STATES=['APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','ROLLED-BACK','RETURNED','STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE'];
function eventRows(){
  var rows=[];try{rows=journalRows(V.st,null,V.now)||[];}catch(e){rows=[];}
  return rows.filter(function(r){return r&&Number.isFinite(r.time);}).sort(function(a,b){return b.time-a.time;});
}
function evKind(e){
  var tr=savedTransition(e),def=journalDefinition(e);
  var sw=tr.present?tr.changed&&!tr.reapply&&tr.outcome!=='refused':e.return_primary===true||SWITCH_STATES.indexOf(e.state)>=0;
  var lvl=def.level||e.level;
  // a code-only event that the severity table grades low (a planned reboot, a clean restart) is no problem: grey lamp
  if(!e.state&&!tr.present&&codeOk(e.code)&&typeof codeSeverity==='function'&&codeSeverity(e.code)==='low'&&e.level!=='error'&&e.level!=='warning')lvl=null;
  return {sw:sw,done:tr.present?tr.completed&&['committed','restored'].indexOf(tr.outcome)>=0:['COMMITTED','ROLLED-BACK','RETURNED'].indexOf(e.state)>=0||e.return_primary===true,
    problem:lvl==='error'||lvl==='warning'||e.level==='error'||e.level==='warning',mine:e.action_source==='manual',lamp:lvl==='error'||e.level==='error'?'r':lvl==='warning'||e.level==='warning'?'y':lvl==='ok'?'g':'n'};
}
var EVF={all:function(){return true;},switch:function(e){return evKind(e).sw;},problem:function(e){return evKind(e).problem;},mine:function(e){return evKind(e).mine;}};
function evKey(e){return e.key||e.time+':'+(e.state||'')+':'+(e.code||'');}
function evParts(e){var x='';try{x=journalMessage(e,V.st,true)||'';}catch(err){x=e.state||e.code||'';}return String(x).split(' · ');}
function evWhy(e){
  var def=journalDefinition(e),m=def.meaning||def.message||['',''],rest=evParts(e).slice(1).filter(Boolean);
  return t(m[1],m[0])+(rest.length?' '+rest.join(' · ')+'.':'');
}
function evText(e){return evParts(e)[0]+(e.action_source==='manual'?t(' (вы)',' (you)'):'');}
function fmtSpan(s){if(!Number.isFinite(s))return '—';if(s<60)return (Math.round(s*10)/10).toFixed(1).replace('.',locale==='en'?'.':',')+' '+t('с','s');var m=Math.round(s/60);return m<60?m+' '+t('мин','min'):Math.floor(m/60)+' '+t('ч','h')+' '+(m%60)+' '+t('мин','min');}
function lastSwitch(){return eventRows().filter(function(e){var k=evKind(e);return k.sw&&k.done;})[0]||null;}
function eventsHTML(n,filter,opts){
  opts=opts||{};var list=eventRows().filter(EVF[filter||'all']).slice(0,n);
  if(!list.length)return '<p class="mute">'+(V.d.dataUnavailable?t('Нет свежих данных','No fresh data'):t('Событий нет','No events'))+'</p>';
  var op=function(e,i){var k=evKey(e);if(HV.evOpen[k]!==undefined)return HV.evOpen[k];return opts.open||(opts.openFirst&&i===0)||(opts.openSwitch&&evKind(e).sw);};
  return '<ul class="evl">'+list.map(function(e,i){var k=evKind(e),code=codeOk(e.code)&&e.code!=='OK'?e.code:'';
    return '<li><div class="ev-h" data-act="evx" data-k="'+esc(evKey(e))+'" role="button" tabindex="0" aria-expanded="'+(op(e,i)?'true':'false')+'"><span class="tm">'+fmtTime(e.time)+'</span><i class="lamp '+k.lamp+'" style="margin-top:4px"></i><span class="tx">'+esc(evText(e))+(code?' <a class="code" href="#" data-act="code" data-code="'+esc(code)+'">'+esc(code)+'</a>':'')+'</span></div><div class="ev-why"'+(op(e,i)?'':' hidden')+'>'+t('Почему: ','Why: ')+esc(evWhy(e))+'</div></li>';}).join('')+'</ul>';
}
function filtersHTML(cur,id){return '<div class="filters" role="group" data-filters="'+id+'">'+[['all',t('Все','All')],['switch',t('Переходы','Switches')],['problem',t('Проблемы','Problems')],['mine',t('Мои действия','My actions')]].map(function(f){return '<button data-act="filter" data-f="'+f[0]+'" data-id="'+id+'" aria-pressed="'+(cur===f[0])+'">'+f[1]+'</button>';}).join('')+'</div>';}

/* ---------------- Statistics from the router's own records ---------------- */
function routeSegments(){var r=((V.st.accounting||{}).reliability||{}).route_history||{};return Array.isArray(r.segments)?r.segments:[];}
function sumKinds(kinds,from,to){var s=0;routeSegments().forEach(function(g){if(kinds.indexOf(g.kind)<0||!Number.isFinite(g.start))return;var a=Math.max(g.start,from),b=Math.min(Number.isFinite(g.end)?g.end:to,to);if(b>a)s+=b-a;});return s;}
function episodes(){try{return switchTimeline(eventRows().slice().reverse());}catch(e){return [];}}
function stats(){
  var now=V.now,from=now-86400,eps=episodes().filter(function(e){return e.kind!=='recovery';});
  var up=sumKinds(['source','target'],from,now),known=sumKinds(['source','target','switching','down','blocked'],from,now);
  var det=eps.map(function(e){return e.detect;}).filter(Number.isFinite),avg=function(a){return a.length?a.reduce(function(x,y){return x+y;},0)/a.length:null;};
  var timing=V.st.switch_timing||{},sw24=eps.filter(function(e){return Number.isFinite(e.reserve)&&e.reserve>=from;}).length;
  var onRes=sumKinds(['target'],from,now),num=function(x){return String(x).replace('.',locale==='en'?'.':',');};
  return {avail24:known>0?num((Math.floor(up/known*1000)/10).toFixed(1))+' %':NODATA(),sw24:V.d.dataUnavailable&&!eps.length?NODATA():String(sw24),
    swAvg:Number.isFinite(timing.avg_seconds)?fmtSpan(timing.avg_seconds):NODATA(),detect:avg(det)!=null?fmtSpan(avg(det)):NODATA(),
    onRes:routeSegments().length?ageText(onRes):NODATA(),eps:eps};
}
function statsTiles(){var s=stats();return '<div class="tiles"><div class="tile"><b>'+esc(s.avail24)+'</b><span>'+t('доступность за 24 ч','availability 24 h')+'</span></div><div class="tile"><b>'+esc(s.sw24)+'</b><span>'+t('переходов за 24 ч','switches 24 h')+'</span></div><div class="tile"><b>'+esc(s.swAvg)+'</b><span>'+t('среднее переключение','avg switch time')+'</span></div><div class="tile"><b>'+esc(s.detect)+'</b><span>'+t('обнаружение сбоя','failure detection')+'</span></div><div class="tile"><b>'+esc(s.onRes)+'</b><span>'+t('на резерве за 24 ч','on reserve 24 h')+'</span></div></div>';}
function latencyChart(){
  var W=640,H=170,P=28,now=V.now,start=now-6*3600,rows=[];
  try{rows=latencyHistoryRows(V.st,V.inv,now).filter(function(r){return r[0]>=start;});}catch(e){rows=[];}
  if(rows.length<2)return '<p class="mute">'+t('Данных пока нет: роутер ещё не накопил историю отклика за 6 часов.','No data yet: the router has no 6-hour response history.')+'</p>';
  var max=0;rows.forEach(function(r){[1,2].forEach(function(i){if(r[i]!=null&&r[i]>max)max=r[i];});});max=Math.max(30,Math.ceil(max/30)*30);
  var x=function(ts){return P+(ts-start)/(now-start)*(W-P-6);},y=function(v){return H-20-(v/max)*(H-34);};
  var path=function(i){var d='',pen=false,prev=null;rows.forEach(function(r){var v=r[i];if(v==null||(prev!=null&&r[0]-prev>900)){pen=false;}if(v==null){prev=null;return;}d+=(pen?'L':'M')+x(r[0]).toFixed(1)+' '+y(v).toFixed(1)+' ';pen=true;prev=r[0];});return d;};
  var gaps='',outage=null;rows.forEach(function(r){if(r[5]==='down'||r[5]==='blocked'){gaps+='<rect class="gap" x="'+(x(r[0])-4).toFixed(1)+'" y="10" width="8" height="'+(H-30)+'"/>';outage=outage||r[0];}});
  var grid=[0,max/3,2*max/3,max].map(function(v){v=Math.round(v);return '<line class="axis" x1="'+P+'" x2="'+W+'" y1="'+y(v)+'" y2="'+y(v)+'"/><text x="2" y="'+(y(v)+3)+'">'+v+'</text>';}).join('');
  var lab=['−6 '+t('ч','h'),'−4 '+t('ч','h'),'−2 '+t('ч','h'),t('сейчас','now')].map(function(l,i){return '<text x="'+(P+i*(W-P-30)/3)+'" y="'+(H-4)+'">'+l+'</text>';}).join('');
  return '<svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+t('Отклик двух каналов за 6 часов, мс','Response of both channels over 6 hours, ms')+'">'+gaps+grid+lab+'<path class="lr" d="'+path(2)+'"/><path class="lp" d="'+path(1)+'"/></svg><div class="legend"><span><i></i>'+t('основной, мс','primary, ms')+'</span><span><i class="r"></i>'+t('резерв, мс','reserve, ms')+'</span>'+(outage?'<span>▮ '+t('провал','outage')+' '+fmtTime(outage).slice(-8,-3)+'</span>':'')+'</div>';
}
function trafficChart(){
  var acc=V.st.accounting||{},days=acc.days||{},wan=(acc.wan||{}).days||{},keys=Object.keys(days).sort().slice(-3);
  if(!keys.length)return '<p class="mute">'+t('Нет данных о трафике.','No traffic data.')+'</p>';
  var gb=function(r){return r&&r.observed!==false&&Number.isFinite(r.rx)?((r.rx||0)+(r.tx||0))/1e9:null;};
  var vals=keys.map(function(k){return [k,gb(days[k]),gb(wan[k])];}),max=Math.max.apply(null,vals.map(function(v){return Math.max(v[1]||0,v[2]||0);}).concat([0.1])),W=320,H=120,sc=(H-34)/max;
  var month=function(m){var s=0,ok=false;Object.keys(days).forEach(function(k){if(k.slice(0,7)===m){var v=gb(days[k]);if(v!=null){s+=v;ok=true;}}});return ok?s:null;};
  var cur=keys[keys.length-1].slice(0,7),f=function(v){return v==null?t('неизвестно','unknown'):(Math.round(v*10)/10).toFixed(1).replace('.',locale==='en'?'.':',')+' '+t('ГБ','GB');};
  return '<svg class="chart" viewBox="0 0 '+W+' '+H+'" style="max-width:420px">'+vals.map(function(r,i){var h=(r[1]||0)*sc,h2=(r[2]||0)*sc;return '<rect class="bar" x="'+(30+i*90)+'" y="'+(H-20-h)+'" width="34" height="'+h+'"/><rect class="bar2" x="'+(66+i*90)+'" y="'+(H-20-h2)+'" width="14" height="'+h2+'"/><text x="'+(32+i*90)+'" y="'+(H-6)+'">'+r[0].slice(8,10)+'.'+r[0].slice(5,7)+' · '+(r[1]==null?'—':f(r[1]))+'</text>';}).join('')+'</svg><div class="legend"><span>▮ VPN</span><span style="color:#8e5bd8">▮ '+t('напрямую через WAN','direct via WAN')+'</span><span>'+t('Этот месяц: ','This month: ')+f(month(cur))+'</span></div>';
}
function switchTimesTable(){
  var eps=episodes().slice(-5).reverse(),s=stats();
  if(!eps.length)return '<p class="mute">'+t('Переключений в сохранённой истории нет.','No switches in the retained history.')+'</p>';
  var sp=fmtSpan,kind={auto:t('Сбой → резерв','Failure → reserve'),manual:t('Ручное','Manual'),test:t('Тест','Test'),unknown:t('Переход','Switch'),recovery:t('Восстановление','Recovery')};
  return '<div class="scrollx"><table class="tbl"><thead><tr><th>'+t('Когда','When')+'</th><th>'+t('Тип','Type')+'</th><th class="num">'+t('Обнаружение','Detection')+'</th><th class="num">'+t('Переключение','Switch')+'</th><th class="num">'+t('На резерве','On reserve')+'</th><th class="num">'+t('Возврат','Return')+'</th></tr></thead><tbody>'+
    eps.map(function(e){return '<tr><td>'+fmtTime(e.time).slice(0,-3)+'</td><td>'+esc(kind[e.kind]||kind.unknown)+'</td><td class="num">'+sp(e.detect)+'</td><td class="num">'+sp(e.switching)+'</td><td class="num">'+sp(e.onReserve)+'</td><td class="num">'+sp(e.returning)+'</td></tr>';}).join('')+
    '</tbody><tfoot><tr><td colspan="2"><b>'+t('Среднее роутера','Router average')+'</b></td><td class="num">'+esc(s.detect)+'</td><td class="num">'+esc(s.swAvg)+'</td><td></td><td class="num">—</td></tr></tfoot></table></div>';
}
function serversHTML(role){
  var p=roleProfile(role),pick=V.st.server_pick,iface=p&&p.interface,tun=pick&&Array.isArray(pick.tunnels)?pick.tunnels.filter(function(x){return x&&x.interface&&x.interface===iface;})[0]:null;
  if(!tun)return '<p class="small mute">'+t('Данных о серверах от роутера пока нет.','No server data from the router yet.')+'</p>';
  var nm=function(c){return c.location?c.location+' ('+c.profile+')':c.profile;};
  var rows=(tun.candidates||[]).map(function(c){var ms=c.alive===true&&Number.isFinite(c.latency_ms)?c.latency_ms+' '+t('мс','ms'):c.alive===false?t('нет ответа','no answer'):t('не измерен','not measured');
    return '<tr><td><i class="lamp '+(c.alive===true?'g':c.alive===false?'r':'n')+'"></i></td><td class="mono">'+esc(nm(c))+'</td><td class="num">'+esc(ms)+'</td><td>'+(c.profile===tun.current?'<span class="chip ok">'+t('текущий','current')+'</span> ':'')+(c.profile===tun.best?'<span class="chip acc">'+t('лучший','best')+'</span>':'')+'</td></tr>';}).join('');
  var ch=tun.last_change;
  return '<table class="tbl"><thead><tr><th></th><th>'+t('Сервер','Server')+'</th><th class="num">'+t('Пинг','Ping')+'</th><th></th></tr></thead><tbody>'+rows+'</tbody></table>'+
    (ch&&Number.isFinite(ch.time)?'<p class="tiny mute">'+t('Последняя смена: ','Last change: ')+esc((ch.from_location||ch.from||'?')+' → '+(ch.to_location||ch.to||'?'))+', '+esc(ch.from_ms)+' → '+esc(ch.to_ms)+' '+t('мс','ms')+' · '+fmtTime(ch.time)+'</p>':'')+
    (pick.enabled?'':'<p class="tiny mute">'+t('Пинг серверов меряется, только когда подбор включён.','Server ping is measured only while the pick is on.')+'</p>')+
    (codeOk(tun.code)?'<p class="tiny"><a class="code" href="#" data-act="code" data-code="'+esc(tun.code)+'">'+esc(tun.code)+'</a></p>':'');
}
var READY_LABELS={'PYTHON-39-MINIMUM':'Python 3.9+','DEPENDENCY-UBUS':'ubus','DEPENDENCY-UCI':'uci','DEPENDENCY-LUA':'Lua','DEPENDENCY-IP':'ip','RPC-PLUGIN':['Модуль rpcd','rpcd plugin'],'CA-BUNDLE':['Сертификаты','Certificates'],'CONFIG-STORAGE-FREE':['Хранилище настроек','Settings storage']};
function readinessHTML(){
  var m=readinessModel(V.st,V.now),v=VER(),b=m.board||{},items=[];
  items.push([v.detected?'g':'y',t('Модель','Model'),v.model+(b.firmware?' · '+t('прошивка GL.iNet ','GL.iNet firmware ')+b.firmware:'')+(v.detected?'':' · '+t('модель не определена роутером','model not detected by the router'))]);
  // As in the mockup: the tool checks share one row (ubus · uci · ip · Lua · rpcd); the worst state wins.
  var GROUP=['DEPENDENCY-UBUS','DEPENDENCY-UCI','DEPENDENCY-IP','DEPENDENCY-LUA','RPC-PLUGIN'],rows=[],grp=null;
  (m.checks||[]).forEach(function(c){if(GROUP.indexOf(c.code)>=0){if(!grp){grp={code:'',state:'pass',stale:false,codes:[]};rows.push(grp);}grp.codes.push(c);if(c.state!=='pass'&&grp.state==='pass'||c.state==='fail')grp.state=c.state;grp.stale=grp.stale||!!c.stale;}else rows.push(c);});
  rows.forEach(function(c){var l=READY_LABELS[c.code],name=c.codes?'ubus · uci · ip · Lua · rpcd':Array.isArray(l)?t(l[0],l[1]):l||c.code,bad=c.codes?c.codes.filter(function(x){return x.state!=='pass';}).map(function(x){return x.code;}).join(', '):c.code;
    items.push([c.state==='pass'?(c.stale?'y':'g'):c.state==='fail'?'r':'y',name,(c.state==='pass'?t('есть','present'):c.state==='fail'?t('нет или повреждено','missing or broken'):c.state)+(c.stale&&m.age!=null?' · '+t('отчёт ','report ')+ageText(m.age)+t(' назад',' ago'):'')+(c.state!=='pass'?' · '+bad:'')]);});
  if(!(m.checks||[]).length)items.push(['n',t('Проверки роутера','Router checks'),t('нет свежих данных','no fresh data')]);
  var prep=(V.st.system_readiness||{}).preparation;
  if(prep&&typeof prep==='object')items.push([prep.state==='ready'||prep.ready===true?'g':'y',t('Подготовка роутера (ускорение)','Router preparation (acceleration)'),prep.ready===true||prep.state==='ready'?t('выполнена, исходные значения сохранены','done, original values saved'):t('требуется при запуске Auto (кнопка Auto выполнит её сама)','needed at Auto start (the Auto button does it itself)')]);
  if(V.s.detected_router_model!=='mt3000')items.push(['y',t('Непрерывный режим на этой модели','Continuous mode on this model'),t('GL-MT6000 ещё не прошёл отдельную приёмку непрерывного Auto; проверено на GL-MT3000 с прошивкой 4.11.0','GL-MT6000 has not yet passed the separate continuous-Auto acceptance; tested on GL-MT3000 with firmware 4.11.0')]);
  return '<ul class="evl">'+items.map(function(i){return '<li class="row" style="flex-wrap:nowrap;align-items:flex-start"><i class="lamp '+i[0]+'" style="margin-top:4px"></i><div><b>'+esc(i[1])+'</b><div class="small mute">'+esc(i[2])+'</div></div></li>';}).join('')+'</ul>';
}
function liveLogHTML(){
  var rows=eventRows().slice(0,Math.min(40,Number(V.s.live_log_limit)||40));
  if(!rows.length)return '<div class="log" aria-label="'+t('Живой журнал','Live log')+'">'+esc(t('нет данных','no data'))+'</div>';
  return '<div class="log" aria-label="'+t('Живой журнал','Live log')+'">'+rows.map(function(e){var k=evKind(e);return '<span class="'+(k.lamp==='r'?'e':k.lamp==='y'?'w':'o')+'">'+esc(fmtTime(e.time,true)+' '+(e.state||'')+'  '+evText(e))+'</span>';}).join('\n')+'</div>';
}
function monText(){var m=V.monitor;return m.title+(m.key==='ok'?' · '+t('проверка каждые ','check every ')+(Number(((V.st.probe_policy||{}).effective_interval))||Number(V.s.interval)||10)+' '+t('с','s'):(m.code?' · '+m.code:''));}
function monLamp(){return {green:'g',yellow:'y',red:'r'}[V.monitor.lamp]||'n';}

/* Actions of the approved mockups, wired to the same router calls and safety rules as before:
   - Auto Start/Stop: native_start(control_revision,'manual') / native_stop('manual'); an ACK is never completion (the
     next fresh status confirms it); a stale or unknown state turns the switch into Stop (fail-safe).
   - Terms: only the owner ticks the boxes (never pre-ticked) and presses the button; terms_accept(version) first.
   - Manual switch: pair_manual / manual_switch(direction,control_revision,'manual'); one request at a time.
   - Check now: scan(); Speed: speed_start; Failure test: fault_start/fault_cancel; Reset: stats_reset. */

/* ---------------- UI helpers (mockup) ---------------- */
function toast(msg){if(HV.testToast)return HV.testToast(msg);var old=$('.toast',HV.root);if(old)old.remove();var d=document.createElement('div');d.className='toast';d.setAttribute('role','status');d.textContent=msg;HV.root.appendChild(d);setTimeout(function(){d.remove();},4200);}
function modal(o){
  if(HV.testModal)return HV.testModal(o);
  var bg=document.createElement('div');bg.className='modal-bg';
  bg.innerHTML='<div class="modal'+(o.wide?' wide':'')+'" role="dialog" aria-modal="true" aria-labelledby="mt"><h2 id="mt">'+o.title+'</h2><div class="mb">'+(o.body||'')+'</div><div class="acts"></div></div>';
  if(o.node)$('.mb',bg).appendChild(o.node);
  var acts=$('.acts',bg);
  function close(){bg.remove();document.removeEventListener('keydown',key);if(o.onClose)o.onClose();}
  function key(e){if(e.key==='Escape')close();}
  (o.buttons||[{t:t('Закрыть','Close')}]).forEach(function(b){var x=document.createElement('button');x.className='btn '+(b.cls||'');x.innerHTML=b.t;if(b.id)x.id=b.id;if(b.disabled)x.disabled=true;
    x.onclick=function(){if(b.keep&&b.fn){b.fn(bg);return;}close();if(b.fn)b.fn(bg);};acts.appendChild(x);});
  bg.addEventListener('click',function(e){if(e.target===bg)close();});
  document.addEventListener('keydown',key);
  HV.root.appendChild(bg);var f=$('button:not([disabled]),input',bg);if(f)f.focus();if(o.onOpen)o.onOpen(bg);return bg;
}
function codeNotice(code,extra){
  var row=errorRow(code);
  return '<p><a class="code" href="#" data-act="code" data-code="'+esc(code)+'">'+esc(code)+'</a> '+(row?esc(t(row[3],row[2])):'')+(extra?' · '+esc(extra):'')+'</p><div class="small" data-code-hint="'+esc(code)+'">'+codeHint(code)+'</div>';
}
/* what to do, from the full table of the optional module */
function codeHint(code){var r=errorRow(code);return r&&r[6]?esc(t(r[7],r[6])):'';}
function failModal(title,code,extra){modal({title:title,body:codeNotice(code,extra)});}
function errorRow(code){if(typeof ERROR_ROWS==='undefined'||!codeOk(code))return null;var r=ERROR_ROWS.filter(function(x){return x[0]===code;})[0];if(!r&&typeof errorFamilyOf==='function'){var f=errorFamilyOf(code);if(f)r=[code].concat(f.slice(1));}return r||null;}
function refreshSoon(){if(HV.refresh)HV.refresh();}

/* ---------------- Terms: the owner accepts them himself ---------------- */
function termsText(){
  var pts=(typeof TERMS_POINTS!=='undefined'?TERMS_POINTS:[]).map(function(p){return '<p><b>'+esc(t(p.h[1],p.h[0]))+'</b> '+esc(t(p.t[1],p.t[0]))+'</p>';}).join('');
  return '<p><b>'+t('HomenS.AI Auto VPN — экспериментальное ПО.','HomenS.AI Auto VPN is experimental software.')+'</b> '+t('Версия условий ','Terms version ')+esc(TERMS_VERSION)+'.</p>'+pts+
    '<details><summary>'+t('Полный текст условий и лицензии','Full terms and licence text')+'</summary><pre style="white-space:pre-wrap;font:inherit;font-size:.82rem">'+esc(t(TERMS_FULL_RU,TERMS_FULL_EN))+'</pre></details>';
}
function termsChecks(prefix){return (typeof TERMS_CHECKS!=='undefined'?TERMS_CHECKS:[]).map(function(c,i){return '<label class="row" style="margin-top:10px;align-items:flex-start;flex-wrap:nowrap"><input type="checkbox" class="'+prefix+'acc" id="'+prefix+'acc'+i+'" style="margin-top:4px"> <span>'+esc(t(c[1],c[0]))+'</span></label>';}).join('');}
function acceptTerms(){
  if(HV.busy.terms)return Promise.reject(new Error('busy'));HV.busy.terms=true;
  return rpcCall('terms_accept',['version'])(TERMS_VERSION).then(function(r){
    if(!(r&&r.saved===true)){failModal(t('Условия не сохранены','Terms not saved'),codeOk(r&&r.code)?r.code:'TERMS-SAVE-FAILED');throw new Error('refused');}
    return reloadInventory();
  },function(e){failModal(t('Условия не сохранены','Terms not saved'),'TERMS-SAVE-UNCONFIRMED');throw e;}).finally(function(){HV.busy.terms=false;});
}
function termsModal(onAccept,btnLabel){
  modal({title:t('Условия использования','Terms of use'),
    body:'<div class="terms-box">'+termsText()+'</div>'+termsChecks('t')+'<p class="tiny mute">'+t('Галочки не ставятся автоматически. Принятие сохраняется на роутере.','The boxes are never pre-ticked. Acceptance is stored on the router.')+'</p>',
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:btnLabel||t('Принять и включить Auto','Accept and turn Auto on'),cls:'pri',id:'tbtn',disabled:true,fn:function(){acceptTerms().then(function(){if(onAccept)onAccept();}).catch(function(){});}}],
    onOpen:function(bg){var b=$('#tbtn',bg),cs=$$('.tacc',bg);cs.forEach(function(c){c.onchange=function(){b.disabled=!cs.every(function(x){return x.checked;});};});}});
}

/* ---------------- Auto ---------------- */
function toggleAuto(){
  V=snap();var op=V.op,stop=V.d.actionStop||autoStartPending;
  if(autoStopBusy||op==='stopping')return;
  if(stop)return stopAuto();
  if(op||autoRequestBusy)return;
  if(HV.inv.error)return failModal(t('Настройки роутера не прочитаны','Router settings were not read'),'RPC-INVENTORY-UNAVAILABLE');
  if(V.monitor.key!=='ok')return modal({title:t('Сначала нужен работающий мониторинг','Monitoring must run first'),body:'<p><b>'+esc(V.monitor.title)+'</b></p><p class="small">'+esc(V.monitor.hint||'')+'</p>'+(V.monitor.code?codeNotice(V.monitor.code):''),
    buttons:[{t:t('Закрыть','Close'),cls:'ghost'},{t:t('Восстановить мониторинг','Restore monitoring'),cls:'pri',fn:restoreMonitor}]});
  if(!V.terms)return termsModal(function(){refreshNow().then(function(){autoCommand(false);});});
  autoCommand(false);
}
function stopAuto(){
  var where=selectedRole();
  modal({title:t('Выключить Auto?','Turn Auto off?'),body:'<p>'+(where?t('Трафик останется на текущем канале ('+chName(where)+'). ','Traffic stays on the current channel ('+chName(where)+'). '):'')+t('При сбое автоматического перехода не будет. Включить снова можно в любой момент.','There will be no automatic switch on a failure. You can turn it on again at any time.')+'</p>',
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Выключить Auto','Turn Auto off'),cls:'danger',fn:function(){autoCommand(true);}}]});
}
function autoCommand(stop){
  V=snap();var st=HV.st,intent=st.auto_control||{},rev=intent.control_revision,op=V.op;
  if(autoStopBusy||op==='stopping')return;
  if(!stop&&(op||autoRequestBusy))return;
  if(!stop&&(typeof rev!=='string'||!/^[0-9a-f]{32}$/.test(rev))){failModal(t('Auto не запущен','Auto did not start'),'CONTROL-REVISION-STALE');refreshNow();return;}
  var command={sequence:++autoCommandSequence,stop:stop,baseline:intent.requested_at||0,acknowledged:false,t0:Date.now(),tick:autoClockTick()};
  autoCommandPending=command;autoCommandUnconfirmed=null;autoObservedOperation=null;
  if(stop){autoStopBusy=true;autoRequestBusy=false;autoStartPending=false;}else{autoRequestBusy=true;autoStartPending=true;}
  paintLive();toast(t('Запрос отправлен. Ждём подтверждения роутера…','Request sent. Waiting for the router…'));
  var call=stop?rpcCall('native_stop',['request_source']):rpcCall('native_start',['control_revision','request_source']);
  return (stop?call('manual'):call(rev,'manual')).then(function(result){
    if(autoCommandSequence!==command.sequence)return;
    if(autoCommandPending===command){if(autoRequestAcknowledged(result,stop))command.acknowledged=true;else autoCommandPending=null;}
    if(!stop&&result&&result.accepted===false&&(result.code==='CONTROL-REVISION-STALE'||Array.isArray(result.blockers)&&result.blockers.indexOf('CONTROL-REVISION-STALE')>=0)){failModal(t('Auto не запущен','Auto did not start'),'CONTROL-REVISION-STALE',t('состояние роутера обновилось, нажмите ещё раз','the router state changed, press again'));return;}
    if(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9-]{2,95}$/.test(result.code)&&(result.accepted===false||result.queued===false))failModal(stop?t('Auto не выключен','Auto not turned off'):t('Auto не запущен','Auto did not start'),result.code,result.settings_unverified?t('настройки роутера не прочитаны','router settings could not be read'):'');
    else if(result&&result.accepted===false)modal({title:t('Auto не запустился','Auto did not start'),body:codeNotice('AUTO-START-REFUSED')+'<ul class="small">'+(result.blockers||[]).filter(codeOk).map(function(c){return '<li><a class="code" href="#" data-act="code" data-code="'+esc(c)+'">'+esc(c)+'</a> · '+esc(autoBlockerText(c))+'</li>';}).join('')+'</ul>'});
    else if(!autoRequestAcknowledged(result,stop))failModal(t('Команда не подтверждена','Command not confirmed'),'AUTO-CONTROL-UNVERIFIED');
  }).catch(function(){if(autoCommandSequence!==command.sequence)return;if(autoCommandPending===command){if(stop){autoCommandPending=null;autoCommandUnconfirmed=command;}else command.acknowledged=true;}failModal(t('Команда не подтверждена','Command not confirmed'),'AUTO-CONTROL-FAILED');
  }).finally(function(){if(autoCommandSequence!==command.sequence)return;if(stop)autoStopBusy=false;else{autoRequestBusy=false;autoStartPending=false;}refreshNow();});
}
function restoreMonitor(){
  if(HV.busy.monitor)return;HV.busy.monitor=true;
  rpcCall('monitor_control',['enabled'])(true).then(function(r){if(r&&r.accepted===true){toast(t('Мониторинг запускается…','Monitoring is starting…'));reloadInventory();}else failModal(t('Мониторинг не запущен','Monitoring not started'),codeOk(r&&r.code)?r.code:'MONITOR-UNKNOWN');})
    .catch(function(){failModal(t('Мониторинг не запущен','Monitoring not started'),'MONITOR-RPC-UNCONFIRMED');}).finally(function(){HV.busy.monitor=false;refreshNow();});
}

/* ---------------- Manual switch ---------------- */
function switchAllowed(role){
  var p=roleProfile(role),m=V.manual[role],sel=V.sel;
  return !!(m&&m.allowed&&p&&sel.selected&&sel.selected!==role&&!sel.code&&!sel.moving&&profileHealth(p,V.now).state==='healthy');
}
function switchTo(role){
  V=snap();if(MANUAL_SWITCH_PENDING)return;
  if(V.sel.selected===role){toast(t('Этот канал уже выбран (MANUAL-ALREADY-SELECTED)','This channel is already selected (MANUAL-ALREADY-SELECTED)'));return;}
  if(!switchAllowed(role)){
    var x=reading(role),m=V.manual[role]||{blockers:[]};
    var why=x.state==='stale'?t('не имеет свежей проверки','has no fresh check'):x.state!=='ok'?t('не прошёл последнюю проверку','failed its last check'):!V.sel.selected?t('роутер ещё не подтвердил, какой канал везёт трафик','the router has not yet confirmed which channel carries traffic'):'';
    modal({title:t('Переключение сейчас недоступно','Switching unavailable now'),body:(why?'<p>'+t('Канал «'+chName(role)+'» '+why+'.','Channel "'+chName(role)+'" '+why+'.')+'</p>':'')+'<p class="small">'+esc(manualReason(m.blockers||[]))+'</p><p class="small mute">'+t('Нажмите «Проверить сейчас» и попробуйте снова.','Press "Check now" and try again.')+'</p>'});return;
  }
  modal({title:t('Переключить на «'+esc(chName(role))+'»?','Switch to "'+esc(chName(role))+'"?'),
    body:'<p>'+t('Звонки и загрузки могут коротко прерваться (обычно 1–4 с).','Calls and downloads may drop briefly (usually 1–4 s).')+'</p>'+(autoOn()?'<p class="small mute">'+t('Auto продолжит следить. Если этот канал откажет, Auto переключит по правилам.','Auto keeps watching. If this channel fails, Auto switches by the rules.')+'</p>':''),
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Переключить','Switch'),cls:'pri',fn:function(){manualRequest(role);}}]});
}
function manualRequest(direction){
  V=snap();var st=HV.st,model=V.manual;
  if(MANUAL_SWITCH_PENDING||!switchAllowed(direction))return;
  var operation={direction:direction,request_id:null,previous:(st.manual_switch||{}).request_id,baseline:Number.isFinite(st.server_time)?st.server_time:(st.manual_switch_control||{}).time||st.time,t0:Date.now(),tick:manualClockTick(),acknowledged:false,uncertain:false};
  MANUAL_SWITCH_OPERATION=operation;MANUAL_SWITCH_FEEDBACK=null;MANUAL_SWITCH_PENDING=true;MANUAL_SWITCH_DIRECTION=direction;paintLive();
  var call=model.mode==='continuous-pair'?rpcCall('pair_manual',['direction','control_revision','request_source']):rpcCall('manual_switch',['direction','control_revision','request_source']),req;
  try{req=call(direction,model.revision,'manual');}catch(e){req=Promise.reject(e);}
  Promise.resolve(req).then(function(result){
    if(MANUAL_SWITCH_OPERATION!==operation)return;
    if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id)){operation.request_id=result.request_id;operation.acknowledged=true;toast(t('Запрос принят. Роутер переключает канал…','Request accepted. The router is switching…'));}
    else if(result&&result.accepted===false&&result.queued!==true){
      var codes=Array.isArray(result.blockers)?result.blockers.filter(codeOk):[],running=['PAIR-MANUAL-BUSY','TRANSACTION-IN-PROGRESS'].indexOf(codes[0])>=0;
      MANUAL_SWITCH_FEEDBACK=running?null:{state:'REFUSED',completed:false,updated_at:statusNow(st),code:codes[0]||'MANUAL-REQUEST-UNCONFIRMED'};
      MANUAL_SWITCH_OPERATION=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;
      modal({title:running?t('Повторно не отправлено','Not sent again'):t('Переключение отклонено','Switch refused'),body:(codes[0]?codeNotice(codes[0]):'')+'<p class="small">'+esc(running?t('Операция уже выполняется.','An operation is already running.'):manualReason(codes))+'</p>'});
    }else operation.uncertain=true;
  }).catch(function(){if(MANUAL_SWITCH_OPERATION===operation)operation.uncertain=true;}).finally(function(){refreshNow();});
}
function manualFeedback(){
  var now=V.now,row=V.st.manual_switch||{};
  var fail=MANUAL_SWITCH_FEEDBACK&&['REFUSED','CANCELLED','UNCONFIRMED'].indexOf(MANUAL_SWITCH_FEEDBACK.state)>=0?MANUAL_SWITCH_FEEDBACK:null;
  if(!fail&&['REFUSED','CANCELLED','UNCONFIRMED'].indexOf(row.state)>=0&&row.completed===false&&manualResultFresh(row,now))fail=row;
  if(fail){var code=codeOk(fail.code)?fail.code:'MANUAL-REQUEST-UNCONFIRMED';return '<p class="note warn small" style="margin-top:10px">'+(fail.state==='CANCELLED'?t('Переключение отменено: ','Switch cancelled: '):fail.state==='UNCONFIRMED'?t('Результат переключения не подтверждён: ','Switch result not confirmed: '):t('Переключение отклонено: ','Switch refused: '))+'<a class="code" href="#" data-act="code" data-code="'+esc(code)+'">'+esc(code)+'</a> '+esc(manualReason([code]))+'</p>';}
  var op=manualOperationModel(V.st,now);
  if(op.busy)return '<p class="note small" style="margin-top:10px">'+t('Переключение: ','Switching: ')+esc(uiOperationTimerText(V.st,now)||t('ждём роутер','waiting for the router'))+(op.uncertain?' · '+t('результат пока не подтверждён','result not confirmed yet'):'')+'</p>';
  return '';
}

/* ---------------- Check now ---------------- */
function checkNow(btn){
  if(connectivityBusy)return;connectivityBusy=true;connectivityFailure=false;paintLive();
  rpcCall('scan')().then(function(r){
    if(!r||r.queued!==true||typeof r.request_id!=='string'||!/^[a-f0-9]{32}$/.test(r.request_id)||!Number.isFinite(r.requested_at))throw new Error('SCAN-UNCONFIRMED');
    connectivityRequest={request_id:r.request_id,requested_at:r.requested_at};HV.scanSeen=null;
  }).catch(function(){connectivityFailure=true;failModal(t('Проверка не запущена','Check not started'),'SCAN-MEASUREMENT-FAILED',t('Запрос не подтверждён. Убедитесь, что мониторинг запущен.','Request not confirmed. Make sure the monitor is running.'));})
    .finally(function(){connectivityBusy=false;refreshNow();});
}
function scanModel(){return connectivityRequest?connectivityModel(V.st,connectivityRequest,V.now):{state:'IDLE',busy:false};}
function scanFollow(){
  var m=scanModel();if(!connectivityRequest)return;
  if(m.busy)return;
  var id=connectivityRequest.request_id;if(HV.scanSeen===id)return;HV.scanSeen=id;
  if(m.state==='COMPLETED')toast(t('Свежая проверка получена: ','Fresh check received: ')+(m.checked-m.failed)+' '+t('из','of')+' '+m.checked+' '+t('VPN работают','VPNs work'));
  else if(m.state==='EMPTY')toast(t('Сейчас ни один VPN не подключён, проверять нечего.','No VPN is connected right now, nothing to check.'));
  else if(m.code)failModal(t('Проверка не завершилась','The check did not finish'),m.code);
  connectivityRequest=null;
}
function checkBtnHTML(cls){var busy=connectivityBusy||scanModel().busy;return '<button class="btn sm'+(cls||'')+'" data-act="check"'+(busy?' disabled aria-busy="true"':'')+'>'+(busy?t('Идёт проверка…','Checking…'):'↻ '+t('Проверить сейчас','Check now'))+'</button>';}

/* ---------------- Speed test ---------------- */
function speedTest(role){
  V=snap();var s=V.s;
  if(HV.speedRun||HV.busy.speed)return;
  var r=role||selectedRole()||'primary',p=roleProfile(r);
  if(!p||!p.interface)return failModal(t('Тест скорости недоступен','Speed test unavailable'),'SPEED-PROFILE-UNAVAILABLE',t('канал не подключён','the channel is not connected'));
  var mib=Number(s.speed_budget_mib)||8,dur=Number(s.speed_duration)||5,streams=Number(s.speed_streams)||2,off=s.speed_enabled!==true;
  modal({title:t('Проверьте запуск теста','Review speed test'),body:'<p>'+t('Канал: ','Channel: ')+'<b>'+esc(chName(r))+'</b> · '+t('до ','up to ')+mib+' '+t('МиБ трафика','MiB of traffic')+' · '+dur+' '+t('с на направление','s per direction')+'</p><p class="small">'+t('На время теста Auto и фоновый мониторинг приостанавливаются. VPN остаются подключёнными. Затем возобновляется мониторинг и после него Auto; ручной Stop учитывается.','Auto and background monitoring pause for the test. VPN connections remain up. Afterwards monitoring resumes before Auto; a manual Stop is respected.')+'</p>'+(off?'<p class="note warn small">'+t('Тесты скорости выключены в настройках; эта кнопка включит их с текущими параметрами.','Speed tests are off in Settings; this button turns them on with the current parameters.')+'</p>':''),
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:off?t('Включить и запустить','Enable and run'):t('Запустить тест','Run test'),cls:'pri',fn:function(){
      HV.busy.speed=true;paintLive();
      var start=function(){return rpcCall('speed_start',['profiles','budget_mib','duration','streams'])([p.id],mib,dur,streams);};
      (off?rpcCall('setup_speed',['enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'])(true,false,mib,dur,streams,Number(s.speed_daily_mib)||128,Number(s.speed_busy_mbps)||2).then(function(x){if(!(x&&x.saved===true))throw {code:codeOk(x&&x.code)?x.code:'SPEED-CONFIG-FAILED'};s.speed_enabled=true;return start();}):start())
        .then(function(res){if(res&&res.accepted===true&&typeof res.run_id==='string'){HV.speedRun={run_id:res.run_id,role:r,id:p.id,t0:Date.now(),dur:dur,snap:null};speedLiveQueued(res,[p.id]);toast(t('Тест поставлен в очередь…','Test queued…'));speedPoll();}
          else failModal(t('Тест скорости не запущен','Speed test not started'),codeOk(res&&res.code)?res.code:'SPEED-START-FAILED',res&&res.code?speedReason(res.code):'');})
        .catch(function(e){failModal(t('Тест скорости не запущен','Speed test not started'),e&&codeOk(e.code)?e.code:'SPEED-START-FAILED');})
        .finally(function(){HV.busy.speed=false;paintLive();});
    }}]});
}
function speedPoll(){
  if(!HV.speedRun)return;
  rpcCall('speed_live')().then(function(raw){var d=speedLiveSnapshot(raw);if(d&&HV.speedRun&&d.run_id===HV.speedRun.run_id){HV.speedRun.snap=d;if(!speedLiveRunning(d)){var done=HV.speedRun;HV.speedRun=null;HV.speedDone={role:done.role,data:d};refreshNow();}}})
    .catch(function(){}).finally(function(){paintLive();if(HV.speedRun){if(Date.now()-HV.speedRun.t0>300000){HV.speedRun=null;paintLive();return;}setTimeout(speedPoll,1000);}});
}
function speedCancel(){rpcCall('speed_cancel')().then(function(r){toast(r&&r.queued?t('Отмена запрошена.','Cancel requested.'):t('Тест не идёт.','No test is running.'));}).catch(function(){failModal(t('Отмена не подтверждена','Cancel not confirmed'),'SPEED-CANCEL-UNVERIFIED');});}
function speedHTML(){
  var run=HV.speedRun;
  if(run){var d=run.snap,row=d&&d.profiles.filter(function(x){return x.id===run.id;})[0],ph=row?row.phase:'waiting';
    var phase={waiting:t('Auto ставится на паузу…','Pausing Auto…'),resolving:t('Подготовка…','Preparing…'),latency:t('Отклик: измеряем…','Latency: measuring…'),download:t('Загрузка: измеряем…','Download: measuring…'),upload:t('Отдача: измеряем…','Upload: measuring…'),done:t('Завершение, Auto продолжает…','Finishing, Auto resumes…')}[ph]||ph;
    var pct=Math.min(95,Math.round((Date.now()-run.t0)/1000/(run.dur*2+8)*100));
    return '<div class="small">'+esc(phase)+' <button class="btn sm ghost" data-act="speedcancel">'+t('Остановить','Stop')+'</button></div><div class="prog"><i style="width:'+pct+'%"></i></div>';}
  var res=((V.st.speed_tests||{}).results||[]).filter(function(x){return x&&Number.isFinite(x.time);}).sort(function(a,b){return b.time-a.time;})[0];
  if(!res)return '<span class="mute small">'+t('Тест ещё не запускали. Тест расходует трафик, Auto на это время ставится на паузу.','No test yet. A test uses traffic; Auto pauses during it.')+'</span>';
  var down=res.download&&Number.isFinite(res.download.mbps)?Math.round(res.download.mbps):'—',up=res.upload&&Number.isFinite(res.upload.mbps)?Math.round(res.upload.mbps):'—';
  var who=V.src&&res.id===V.src.id?roleName('primary'):V.tgt&&res.id===V.tgt.id?roleName('reserve'):(res.name||res.id);
  if(codeOk(res.code)&&down==='—')return '<span class="small">'+t('Последний тест ','Last test ')+fmtTime(res.time)+': <a class="code" href="#" data-act="code" data-code="'+esc(res.code)+'">'+esc(res.code)+'</a></span>';
  return '<div><b style="font-size:1.25rem">'+down+' / '+up+'</b> '+t('Мбит/с (загрузка / отдача)','Mbit/s (down / up)')+' · '+esc(who)+'<div class="tiny mute">'+fmtTime(res.time)+'</div></div>';
}

/* ---------------- Failure test ---------------- */
function faultActive(){var f=V.st.operator_fault||{};return ['PREPARING','ARMED','ACTIVE','TIMEOUT-ELAPSED','UNKNOWN'].indexOf(f.state)>=0||f.cleaned===false;}
function faultTest(){
  V=snap();if(faultActive()||HV.busy.fault)return;
  var b=faultCurrentBinding(HV.st,HV.inv);
  if(!b.ready){var list=[];try{list=faultBlockers(HV.st,HV.inv,b.source)||[];}catch(e){list=[];}
    return modal({title:t('Нужен работающий Auto','Auto must be running'),body:'<p>'+t('Тест сбоя проверяет, что Auto сам уйдёт на резерв и вернётся. Сначала включите Auto и дождитесь двух здоровых каналов.','The failure test checks that Auto moves to the reserve and back by itself. Turn Auto on first and wait for two healthy channels.')+'</p>'+codeNotice('FAULT-CERTIFIED-AUTO-REQUIRED')+(list.length?'<ul class="small">'+list.slice(0,8).map(function(x){return '<li>'+esc(typeof x==='string'?x:x&&(x.ru||x.en)?t(x.ru,x.en):(x&&(x.text||x.code))||'')+'</li>';}).join('')+'</ul>':'')});}
  var name=profileName(b.source);
  modal({title:t('Запустить тест сбоя?','Run the failure test?'),body:'<p>'+t('Роутер на выбранное время перекроет трафик канала «'+esc(name)+'». Auto должен заметить сбой, перейти на другой канал и вернуться. Звонки прервутся на несколько секунд. Тест можно остановить в любой момент.','For the chosen time the router blocks the traffic of "'+esc(name)+'". Auto should notice, move to the other channel and come back. Calls drop for a few seconds. You can stop the test at any time.')+'</p><div class="f"><label for="fdur">'+t('Длительность сбоя','Fault duration')+'</label><select id="fdur">'+[30,60,120,150,180].map(function(s){return '<option value="'+s+'"'+(s===150?' selected':'')+'>'+s+' '+t('с','s')+'</option>';}).join('')+'</select></div>',
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Запустить тест','Run test'),cls:'pri',fn:function(bg){
      var dur=Number(($('#fdur',bg)||{}).value)||150,now=faultCurrentBinding(HV.st,HV.inv);
      if(!now.ready||!now.source||now.source.id!==b.source.id||now.certificate!==b.certificate)return failModal(t('Тест не запущен','Test not started'),'FAULT-NOT-CURRENT-SOURCE',t('VPN изменился, пока окно было открыто','the VPN changed while this window was open'));
      HV.busy.fault=true;rpcCall('fault_start',['profile','scope','duration'])(now.source.id,'channel',dur).then(function(r){if(r&&codeOk(r.code)&&r.code!=='FAULT-ACTIVE')failModal(t('Тест сбоя','Failure test'),r.code);else toast(t('Тест сбоя запущен','Failure test started'));})
        .catch(function(){failModal(t('Тест сбоя','Failure test'),'FAULT-RPC-UNCONFIRMED');}).finally(function(){HV.busy.fault=false;refreshNow();});
    }}]});
}
function stopFault(){rpcCall('fault_cancel')().then(function(r){toast(codeOk(r&&r.code)?r.code:t('Запрос отправлен','Request sent'));}).catch(function(){failModal(t('Тест сбоя','Failure test'),'FAULT-CANCEL-UNKNOWN');}).finally(refreshNow);}
function faultHTML(){
  var f=V.st.operator_fault||{},hist=Array.isArray(f.history)?f.history.filter(function(h){return h&&Number.isFinite(h.time);}).sort(function(a,b){return b.time-a.time;}):[];
  if(faultActive())return '<div class="row"><span class="chip warn"><i class="lamp y"></i>'+t('Идёт · ','Running · ')+(Number.isFinite(f.remaining_seconds)?f.remaining_seconds+' '+t('с','s'):esc(f.state||''))+'</span> <button class="btn sm danger" data-act="stopfault">'+t('Остановить и снять сбой','Stop and remove fault')+'</button></div>';
  if(!hist.length)return '<span class="mute small">'+t('Тест сбоя ещё не запускали.','No failure test yet.')+'</span>';
  var h=hist[0];return '<span class="small">'+t('Последний тест: ','Last test: ')+fmtTime(h.time,true)+(codeOk(h.code)?' — <a class="code" href="#" data-act="code" data-code="'+esc(h.code)+'">'+esc(h.code)+'</a>':'')+'</span>';
}

/* ---------------- Statistics reset ---------------- */
function resetStats(){
  modal({title:t('Сбросить статистику?','Reset statistics?'),body:'<p>'+t('Обнулятся счётчики доступности, переходов и графики. Старые данные архивируются на роутере. Настройки останутся.','Availability and switch counters and the charts are cleared. Old data is archived on the router. Settings stay.')+'</p>',
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Сбросить','Reset'),cls:'danger',fn:function(){
      rpcCall('stats_reset',['scope'])('all').then(function(r){
        if(!(r&&r.queued===true))return failModal(t('Сброс не выполнен','Reset not done'),codeOk(r&&r.code)?r.code:'STATS-RESET-UNCONFIRMED');
        var nonce=r.nonce,until=Date.now()+45000;
        (function wait(){statusCall().then(function(st){var x=st&&st.stats_reset;if(x&&x.nonce===nonce){if(x.done===true){toast(t('Статистика сброшена','Statistics reset'));refreshNow();}else failModal(t('Сброс не завершился','Reset did not complete'),codeOk(x.code)?x.code:'STATS-RESET-UNCONFIRMED');return;}
          if(Date.now()<until)setTimeout(wait,3000);else failModal(t('Сброс не подтверждён','Reset not confirmed'),'STATS-RESET-UNCONFIRMED');}).catch(function(){if(Date.now()<until)setTimeout(wait,3000);});})();
      }).catch(function(){failModal(t('Сброс не выполнен','Reset not done'),'STATS-RESET-UNCONFIRMED');});
    }}]});
}

/* ---------------- Help, codes, training (catalogue module loaded on demand) ---------------- */
function helpApi(r){
  if(LAZY_HELP.api)return Promise.resolve(LAZY_HELP.api);
  LAZY_HELP.inventory=HV.inv;
  return loadLazyHelp(r).then(function(){if(!LAZY_HELP.api)throw new Error('UI-HELP-LOAD-FAILED');return LAZY_HELP.api;});
}
function helpFail(){return 'UI-HELP-LOAD-FAILED · '+t('справка не загрузилась','help did not load')+' <button class="btn sm" data-act="helpretry">'+t('Повторить','Retry')+'</button>';}
function helpListHTML(){
  if(!LAZY_HELP.api)return '<p class="small mute" data-help-list>'+(LAZY_HELP.failed?helpFail():t('Загрузка тем…','Loading topics…'))+'</p>';
  var topics=LAZY_HELP.api.helpTopics();
  return '<ul class="evl" data-help-list>'+topics.map(function(h){return '<li class="row" style="justify-content:space-between;flex-wrap:nowrap"><a href="#" data-act="help" data-h="'+esc(h.id)+'">'+esc(t(h.title[1],h.title[0]))+'</a>'+(h.id!=='diagnose-all'&&h.id!=='ai-prompt'&&h.id!=='ai-lan-prompt'?'<button class="btn sm ghost" data-act="prompt" data-h="'+esc(h.id)+'" title="'+t('Скопировать промпт для ИИ-помощника','Copy a prompt for an AI assistant')+'">'+t('Промпт для ИИ','AI prompt')+'</button>':'')+'</li>';}).join('')+'</ul>';
}
function helpCount(){return LAZY_HELP.api?LAZY_HELP.api.helpTopics().length:null;}
function fillHelpLists(r){helpApi(r).catch(function(){}).then(function(){$$('[data-help-list]',HV.root).forEach(function(n){n.outerHTML=helpListHTML();});$$('[data-cb]',HV.root).forEach(function(n){n.outerHTML=codeBody(n.dataset.cb);});$$('[data-help-count]',HV.root).forEach(function(n){var c=helpCount();if(c)n.textContent=c+' '+t('тем','topics')+' · '+n.getAttribute('data-sub');});if(r&&LAZY_HELP.api&&!$('.modal-bg',HV.root))render();});}
function openTopic(id){
  helpApi().then(function(api){var topic=api.helpTopics().filter(function(x){return x.id===id;})[0];if(!topic)return failModal(t('Помощь','Help'),'UI-HELP-LOAD-FAILED');
    modal({title:esc(t(topic.title[1],topic.title[0])),node:api.topicNode(id),wide:true});})
    .catch(function(){failModal(t('Помощь','Help'),'UI-HELP-LOAD-FAILED');});
}
function copyText(text,done){
  function fallback(){var a=document.createElement('textarea');a.value=text;a.setAttribute('readonly','');a.style.position='fixed';a.style.opacity='0';HV.root.appendChild(a);a.select();var ok=false;try{ok=document.execCommand('copy');}catch(e){}a.remove();done(ok);}
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(text).then(function(){done(true);},fallback);else fallback();
}
function copyPrompt(id){
  helpApi().then(function(api){var text=id?api.topicPrompt(id):api.generalPrompt();if(!text)return;
    copyText(text,function(ok){if(ok)toast(t('Промпт для ИИ скопирован','AI prompt copied'));else modal({title:t('Промпт для ИИ','AI prompt'),body:'<textarea rows="10" readonly>'+esc(text)+'</textarea>'});});})
    .catch(function(){failModal(t('Промпт для ИИ','AI prompt'),'UI-HELP-LOAD-FAILED');});
}
function openLearn(){helpApi().then(function(api){modal({title:t('Обучение','Training'),node:api.renderLearn(),wide:true});}).catch(function(){failModal(t('Обучение','Training'),'UI-HELP-LOAD-FAILED');});}
function codesHTML(q){
  q=(q||'').toLowerCase();var rows=(typeof ERROR_ROWS!=='undefined'?ERROR_ROWS:[]).filter(function(r){return r&&typeof r[0]==='string';});
  var L=rows.filter(function(c){return !q||(c[0]+' '+c[2]+' '+c[3]+' '+(c[4]||'')+' '+(c[5]||'')).toLowerCase().indexOf(q)>=0;});
  return '<table class="tbl codes-tbl"><tbody>'+L.slice(0,40).map(function(c){return '<tr data-act="code" data-code="'+esc(c[0])+'" tabindex="0"><td class="mono" style="white-space:nowrap">'+esc(c[0])+'</td><td>'+esc(t(c[3],c[2]))+'</td></tr>';}).join('')+'</tbody></table><p class="tiny mute">'+(L.length>40?t('Показаны первые 40 из ','Showing 40 of ')+L.length+'. ':'')+t('Всего в справочнике ','The reference has ')+rows.length+t(' кодов с объяснением и «что делать». Нажмите строку.',' codes with explanations and actions. Tap a row.')+'</p>';
}
function codeBody(code){var row=errorRow(code)||[code,'',code,code];
  return '<div data-cb="'+esc(code)+'"><p><b>'+esc(t(row[3],row[2]))+'</b></p>'+(row[4]?'<p class="small">'+esc(t(row[5],row[4]))+'</p>':'<p class="small mute">'+(LAZY_HELP.failed?helpFail():t('Подробное объяснение загружается…','Loading the detailed explanation…'))+'</p>')+(row[6]?'<h3>'+t('Что делать','What to do')+'</h3><p class="small">'+esc(t(row[7],row[6]))+'</p>':'')+(row[8]?'<p class="tiny mute">'+t('Пример: ','Example: ')+esc(t(row[9],row[8]))+'</p>':'')+'</div>';}
function showCode(code){
  if(!codeOk(code.replace(/\*$/,'')))return;
  modal({title:esc(code),body:codeBody(code)});
  if(!LAZY_HELP.api)fillHelpLists();
}
function helpModal(){
  modal({title:t('Помощь','Help'),body:helpListHTML()+'<p class="small"><a href="#" data-act="gohelp">'+t('Коды, обучение и условия — в Настройках → Справка','Codes, training and terms — Settings → Reference')+'</a></p>',onOpen:function(){fillHelpLists();}});
}
function decisionsModal(){
  var m=modal({title:t('Журнал решений','Decision log'),body:'<p class="small mute">'+t('Загрузка…','Loading…')+'</p>',wide:true});
  rpcCall('statistics',['kind','after','until'])('probe',0,0).then(function(r){
    var rows=Array.isArray(r&&r.events)?r.events.slice(-30).reverse():[],mb=$('.mb',m);if(!mb)return;
    if(!rows.length){mb.innerHTML='<p class="mute">'+t('Решений пока нет.','No decisions yet.')+'</p>';return;}
    mb.innerHTML='<div class="scrollx"><table class="tbl"><tr><th>'+t('Время','Time')+'</th><th>'+t('Уровень','Level')+'</th><th>'+t('Решение','Decision')+'</th><th>'+t('Почему','Why')+'</th></tr>'+rows.map(function(x){var d=probeDecision(x)||['',''];return '<tr><td>'+fmtTime(x.time,true)+'</td><td>'+esc(x.level!=null?x.level:'—')+'</td><td>'+esc(d[0])+'</td><td>'+esc(d[1])+(codeOk(x.code)?' · <a class="code" href="#" data-act="code" data-code="'+esc(x.code)+'">'+esc(x.code)+'</a>':'')+'</td></tr>';}).join('')+'</table></div>';
  }).catch(function(){var mb=$('.mb',m);if(mb)mb.innerHTML=codeNotice('STATISTICS-REPLY');});
}
function incidentReport(){
  var rows=eventRows().filter(function(e){return evKind(e).sw;}).slice(0,100).map(function(e){return {id:e.key||String(e.time),source:e.source||'',target:e.target||'',outcome:e.state||'',codes:(e.codes||[e.code]).filter(Boolean),phases:[{state:e.state,time:e.time}]};});
  if(!rows.length)return toast(t('Переключений для отчёта нет','No switches to report'));
  downloadIncidentReport(rows);toast(t('Отчёт для печати сохранён: homensai-incidents.html','Printable report saved: homensai-incidents.html'));
}
function lanHelperHTML(){return '<a class="btn sm" href="'+esc(L.resource('view/homensai-vpn/client-test.ps1'))+'" download="homensai-vpn-client-test.ps1">'+t('Скачать LAN-помощник','Download LAN helper')+'</a><a class="btn sm ghost" href="'+esc(L.resource('view/homensai-vpn/start-lan-helper.ps1'))+'" download="start-lan-helper.ps1">'+t('Скрипт запуска','Launcher script')+'</a>';}
function glVpnUrl(){var u=null;try{u=resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);}catch(e){}return u;}

/* Settings: ONE definition (mockup SECTIONS), every view arranges it differently. Values come from the router
   inventory; each section saves through the same RPC and arguments as before. Saving never starts Auto. Sections that
   need Auto off (rules, pair, history) offer "Stop Auto and save"; Auto then stays off. */
var LEVELS=function(){return [[t('Экономно','Economy'),60],[t('Лёгкий','Light'),30],[t('Сбалансировано','Balanced'),20],[t('Надёжно','Reliable'),15],[t('Максимальная надёжность','Max reliability'),10]];};
var REC_KEYS=['interval','fails','resOk','cooldown','dwell','attempts','window','retOk','stab','rescue'];
var REC_MAP={fails:'failures',resOk:'successes',cooldown:'cooldown',dwell:'min_dwell',attempts:'attempt_limit',window:'attempt_window',retOk:'primary_successes',stab:'primary_stable',rescue:'rescue_stable'};
var REC_DEFAULTS={failures:3,successes:2,cooldown:60,min_dwell:60,return_policy:'healthy_primary',primary_successes:2,primary_stable:120,attempt_limit:3,attempt_window:15,rescue_stable:10};
function presetValues(id){return id==='calm'?Object.assign({},REC_DEFAULTS,RECOVERY_PRESETS.stability):id==='fast'?Object.assign({},REC_DEFAULTS,RECOVERY_PRESETS.fast_recovery):Object.assign({},REC_DEFAULTS);}
function presetOf(D){var keys=Object.keys(REC_MAP);return ['balanced','calm','fast'].filter(function(id){var v=presetValues(id);return keys.every(function(k){return Number(D[k])===v[REC_MAP[k]];});})[0]||'custom';}
function pairChoices(){var s=(HV.inv||{}).settings||{};try{return onboardingPairChannels((HV.inv||{}).profiles||[],s)||[];}catch(e){return [];}}
function currentPairId(role){var s=HV.inv.settings||{},anchor=s['plan_'+role+'_tunnel'],rows=pairChoices();if(anchor){var m=rows.filter(function(p){return p.vendor_tunnel_id===anchor;});if(m.length===1)return m[0].id;}return s['plan_'+role]||'';}
function draftFromInventory(){
  var s=(HV.inv||{}).settings||{},n=function(v,d){return Number.isFinite(Number(v))&&v!==''&&v!=null?Number(v):d;},pp=(HV.st||{}).probe_policy||{};
  var tgItems=s.telegram_items==='none'?'none':!s.telegram_items?'maximum':(['minimum','standard','maximum','brief'].filter(function(k){return TG_PRESETS[k].join(',')===s.telegram_items;})[0]||'custom');
  var D={pairP:currentPairId('source'),pairR:currentPairId('target'),pick:s.server_pick===true,allowDrop:s.native_session_loss===true,
    interval:n(s.interval,10),fails:n(s.recovery_failures,3),resOk:n(s.recovery_successes,2),cooldown:n(s.recovery_cooldown,60),dwell:n(s.recovery_min_dwell,60),
    attempts:n(s.recovery_attempt_limit,3),window:n(s.recovery_attempt_window,15),retOk:n(s.recovery_primary_successes,2),stab:n(s.recovery_primary_stable,120),rescue:n(s.recovery_rescue_stable,10),
    failModel:['hmm','hmm-fast','consecutive'].indexOf(s.failure_model)>=0?s.failure_model:'hmm',pickModel:s.server_pick_model==='bayes'?'bayes':'simple',
    returnPolicy:s.recovery_return_policy==='hold_reserve'?'hold_reserve':'healthy_primary',fast:s.fast_switch!==false,
    level:Number.isInteger(pp.level)&&pp.level>=1&&pp.level<=5?pp.level:(Number.isInteger(s.probe_level)&&s.probe_level>=1?s.probe_level:3),boost:pp.boost_enabled!==undefined?pp.boost_enabled!==false:s.probe_boost!==false,
    method:['icmp-1.1.1.1','icmp-8.8.8.8','icmp-9.9.9.9','websites'].indexOf(s.response_metric)>=0?s.response_metric:'icmp-1.1.1.1',pingInt:n(s.ping_interval,60),compare:s.response_compare===true,
    tg:s.telegram_enabled===true,tgToken:'',tgChat:s.telegram_destination||'',tgSchedule:s.telegram_schedule==='daily'?'daily':'interval',tgInterval:n(s.telegram_interval,60),tgHour:n(s.telegram_hour,7),
    tgWeekly:s.telegram_weekly!==false&&s.telegram_monthly!==false,tgItems:tgItems,
    speedOn:s.speed_enabled===true,speedNew:s.speed_auto_new===true,speedMib:n(s.speed_budget_mib,8),speedSec:n(s.speed_duration,5),speedStreams:n(s.speed_streams,2),speedDaily:n(s.speed_daily_mib,128),speedBusy:n(s.speed_busy_mbps,2),
    mode:(((HV.st||{}).stats_mode||{}).mode||s.stats_mode)==='diagnostic'?'diagnostic':'work',diagHours:24,days:n(s.history_days,7),live:n(s.live_log_limit,2000),
    monInterval:n(s.interval,10),checkpoint:n(s.checkpoint,900),probeLimit:Math.min(16,n(s.probe_limit,16)),planning:s.plan_enabled===true,theme:HV.theme};
  D.preset=presetOf(D);return D;
}
function D(){if(!HV.draft)HV.draft=draftFromInventory();return HV.draft;}
function snapshotDraft(){HV.draft=draftFromInventory();HV.dirty={};XD.ed={};}
function levelText(l){var x=LEVELS()[(l||D().level)-1]||LEVELS()[2];return x[0]+' · '+t('проверка раз в '+x[1]+' с','check every '+x[1]+' s');}
function presetName(){return {calm:t('Спокойно','Calm'),balanced:t('Обычно','Normal'),fast:t('Быстро','Fast'),custom:t('Свои значения','Custom')}[D().preset];}
function presetHint(id){var v=presetValues(id);return t(v.failures+' ошибки · пауза '+v.cooldown+' с · возврат после '+v.primary_successes+' проверок за '+v.primary_stable+' с',v.failures+' failures · pause '+v.cooldown+' s · return after '+v.primary_successes+' checks over '+v.primary_stable+' s');}

/* ---------------- Field builders (mockup) ---------------- */
function fNum(k,label,min,max,unit,hint){return '<div class="f"><label for="s-'+k+'">'+label+'</label><span><input type="number" id="s-'+k+'" data-set="'+k+'" min="'+min+'" max="'+max+'" value="'+esc(D()[k])+'"> <span class="small mute">'+(unit||'')+'</span></span>'+(hint?'<div class="h">'+hint+' · '+min+'–'+max+'</div>':'<div class="h">'+min+'–'+max+'</div>')+'</div>';}
function fSel(k,label,opts,hint,disabled){return '<div class="f"><label for="s-'+k+'">'+label+'</label><select id="s-'+k+'" data-set="'+k+'"'+(disabled?' disabled':'')+'>'+opts.map(function(o){return '<option value="'+esc(o[0])+'"'+(String(D()[k])===String(o[0])?' selected':'')+'>'+esc(o[1])+'</option>';}).join('')+'</select>'+(hint?'<div class="h">'+hint+'</div>':'')+'</div>';}
function fTog(k,label,hint,disabled,id){id=id||'s-'+k;return '<div class="f"><label for="'+id+'">'+label+'</label><input class="tg" type="checkbox" id="'+id+'" data-set="'+k+'"'+(D()[k]?' checked':'')+(disabled?' disabled':'')+'>'+(hint?'<div class="h">'+hint+'</div>':'')+'</div>';}
function fTxt(k,label,ph,hint,type){return '<div class="f"><label for="s-'+k+'">'+label+'</label><input type="'+(type||'text')+'" id="s-'+k+'" data-set="'+k+'" value="'+esc(D()[k]||'')+'" placeholder="'+esc(ph||'')+'" autocomplete="off">'+(hint?'<div class="h">'+hint+'</div>':'')+'</div>';}
function saveBar(id,note){return '<div class="savebar"><button class="btn pri sm" data-act="save" data-sec="'+id+'">'+t('Сохранить','Save')+'</button><button class="btn sm ghost" data-act="discard" data-sec="'+id+'">'+t('Отменить','Discard')+'</button><span class="dirty" data-dirty="'+id+'" '+(HV.dirty[id]?'':'hidden')+'>'+t('есть несохранённые изменения','unsaved changes')+'</span>'+(note?'<span class="tiny mute" style="flex-basis:100%">'+note+'</span>':'')+'</div>';}
function pairOptions(){var rows=pairChoices();if(!rows.length)return [['',t('нет подходящих VPN-клиентов','no suitable VPN clients')]];return [['','—']].concat(rows.map(function(p){return [p.id,profileName(p)+' · '+(p.protocol==='wireguard'?'WireGuard':'OpenVPN')+(p.interface?' · '+p.interface:'')];}));}
var TG_ITEM_NAMES=function(){return [['brief',t('Кратко по-русски','Brief in Russian')],['minimum',t('Минимум: только серверы','Minimum: servers only')],['standard',t('Стандарт: серверы, события, трафик, контроллер','Standard: servers, events, traffic, controller')],['maximum',t('Всё','Everything')],['none',t('Ничего, кроме теста','Nothing but the test')]].concat(D().tgItems==='custom'?[['custom',t('Свой набор (как сохранён)','Custom set (as saved)')]]:[]);};

var SECTIONS={
 adv:{lvl:'x',title:function(){return t('Автоподстройка: реакция на сбои','Auto-adaptation: failure reaction');},sum:function(){var a=advSt();if(!a)return NODATA();var c=a.current;return advModeName(a.mode)+' · '+(c.failure_model==='consecutive'?t('ползунок не действует','slider inactive'):c.attached?'t = '+advNum(c.slider_t,2):c.label==='preset'?t('по умолчанию','default'):t('пользовательская','custom'))+' · '+a.window_days+' '+t('дн.','d');},
   body:function(){return advSectionBody();}},
 pair:{lvl:'s',title:function(){return t('Каналы: основной и резерв','Channels: primary and reserve');},sum:function(){return chName('primary')+' + '+chName('reserve');},
   body:function(){return fSel('pairP',t('Основной VPN-клиент','Primary VPN client'),pairOptions())+fSel('pairR',t('Резервный VPN-клиент','Reserve VPN client'),pairOptions())+
   fTog('pick',t('Подбирать лучший сервер (основной)','Pick the best server (primary)'),t('Роутер меряет серверы канала и переходит на самый быстрый, пока канал простаивает. Один выключатель на оба канала; сохраняется сразу.','The router measures the channel servers and moves to the fastest while the channel is idle. One switch for both channels; saved at once.'))+fTog('pick',t('Подбирать лучший сервер (резерв)','Pick the best server (reserve)'),'',false,'s-pickR')+
   '<p class="small"><a href="'+esc(glVpnUrl()||'#')+'" target="_blank" rel="noopener noreferrer" data-act="glvpn">'+t('Профили VPN в панели GL.iNet ↗','VPN profiles in the GL.iNet panel ↗')+'</a> · '+t('новые серверы добавляются там','add new servers there')+'</p>'+saveBar('pair',t('Сохранение не включает Auto. Перед следующим запуском готовность проверяется заново.','Saving does not start Auto. Readiness is checked again before the next start.'));}},
 rules:{lvl:'s',title:function(){return t('Как быстро переключать','How fast to switch');},sum:function(){var d=D();return presetName()+' · '+t(d.fails+' ошибки по '+d.interval+' с, лимит '+d.attempts+' за '+d.window+' мин',d.fails+' failures × '+d.interval+' s, limit '+d.attempts+' per '+d.window+' min');},
   body:function(){var d=D(),mt3000=V&&V.s.detected_router_model==='mt3000';return '<div class="presets" role="radiogroup">'+[['calm',t('Спокойно','Calm')],['balanced',t('Обычно (по умолчанию)','Normal (default)')],['fast',t('Быстро','Fast')]].map(function(p){return '<label><input type="radio" name="preset" value="'+p[0]+'" data-set="preset"'+(d.preset===p[0]?' checked':'')+'><b>'+p[1]+'</b><small>'+esc(presetHint(p[0]))+'</small></label>';}).join('')+'</div>'+
   fSel('returnPolicy',t('Когда основной снова здоров','When the primary is healthy again'),[['healthy_primary',t('Вернуться на основной автоматически','Return to primary automatically')],['hold_reserve',t('Оставаться на работающем резерве','Stay on the working reserve')]])+
   fTog('allowDrop',t('Разрешить короткий обрыв звонков и загрузок','Allow a brief drop of calls and downloads'),t('Без этого Auto не переключит, пока идёт активная сессия.','Without it Auto will not switch during an active session.'))+
   '<details class="more"'+(HV.open.rulesMore?' open':'')+' data-open="rulesMore"><summary>'+t('Свои значения (11 параметров)','Custom values (11 parameters)')+'</summary>'+fNum('interval',t('Интервал проверки','Check interval'),10,300,t('с','s'))+fNum('fails',t('Ошибок основного до перехода','Primary failures before switching'),2,10)+fNum('resOk',t('Успешных проверок резерва','Reserve successes required'),2,10)+fNum('cooldown',t('Пауза между попытками','Pause between attempts'),60,1800,t('с','s'))+fNum('dwell',t('Минимум на резерве','Minimum time on reserve'),60,3600,t('с','s'))+fNum('attempts',t('Лимит попыток','Attempt limit'),1,10,'',t('защищает от «качелей»','prevents flapping'))+fNum('window',t('…за окно','…per window'),1,15,t('мин','min'))+fNum('retOk',t('Проверок основного для возврата','Primary checks before return'),2,10)+fNum('stab',t('Стабильность основного','Primary stability'),30,600,t('с','s'))+fNum('rescue',t('Стабильность основного, если резерв отказал','Primary stability when the reserve failed'),0,60,t('с','s'),t('0 — вся «стабильность основного»','0 = the whole primary stability'))+
   fTog('fast',t('Быстрое переключение (без перестройки GL)','Fast switch (no GL rebuild)'),mt3000?t('Проверено на GL-MT3000. Сохраняется сразу.','Verified on GL-MT3000. Saved at once.'):t('Проверено только на GL-MT3000. На этой модели недоступно, пока не пройдёт проверку.','Verified only on GL-MT3000. Unavailable on this model until it passes verification.'),!mt3000)+'<button class="btn sm" data-act="defaults">'+t('Значения по умолчанию','Default values')+'</button></details>'+
   saveBar('rules',t('Правила меняются при выключенном Auto: при сохранении программа предложит остановить Auto. Сама Auto не включит.','Rules change with Auto off: saving offers to stop Auto. It never starts Auto by itself.'));}},
 load:{lvl:'s',title:function(){return t('Нагрузка на роутер','Router load');},sum:function(){return levelText()+(D().boost?t(' · ускорение вкл.',' · boost on'):'');},
   body:function(){var d=D();return '<div class="f wide"><label for="s-level">'+t('Уровень опроса: нагрузка ↔ надёжность','Probe level: load ↔ reliability')+' — <span data-lvl>'+esc(levelText())+'</span></label><input class="slider" type="range" id="s-level" min="1" max="5" step="1" value="'+d.level+'" data-set="level"><div class="ticks">'+LEVELS().map(function(l){return '<span>'+l[0]+'</span>';}).join('')+'</div><div class="h">'+t('Каналы падают редко; частые проверки грузят CPU. На уровнях 1–2 автоматическое ускорение включено всегда.','Channels fail rarely; frequent checks load the CPU. On levels 1–2 automatic boost is always on.')+'</div></div>'+
   fTog('boost',t('Автоматическое ускорение','Automatic boost'),t('При первой же неудачной проверке роутер временно проверяет чаще, потом возвращается к уровню.','After the first failed check the router temporarily checks more often, then returns to the level.'),d.level<=2)+
   '<details class="more"'+(HV.open.loadMore?' open':'')+' data-open="loadMore"><summary>'+t('Как измеряется отклик','How response is measured')+'</summary>'+fSel('method',t('Способ','Method'),[['icmp-1.1.1.1',t('Пинг 1.1.1.1 через каждый VPN (рекомендуется)','Ping 1.1.1.1 through each VPN (recommended)')],['icmp-8.8.8.8',t('Пинг 8.8.8.8','Ping 8.8.8.8')],['icmp-9.9.9.9',t('Пинг 9.9.9.9','Ping 9.9.9.9')],['websites',t('Три сайта по HTTPS','Three websites over HTTPS')]],t('Только для показа скорости отклика. Решения Auto принимает по своим проверкам здоровья.','Display only. Auto decides by its own health checks.'))+fSel('pingInt',t('Интервал пинга','Ping interval'),[10,20,30,60,120,300].map(function(s){return [s,s<60?s+' '+t('с','s'):s/60+' '+t('мин','min')];}))+fTog('compare',t('Мерить все способы (сравнение)','Measure all methods (comparison)'),t('Чуть больше нагрузки и трафика.','A little more load and traffic.'))+'<p class="small"><a href="#" data-act="decisions">'+t('Журнал решений: уровни и ускорение','Decision log: levels and boost')+'</a></p></details>'+
   saveBar('load',t('Применяется сразу, со следующей проверки. Auto не перезапускается.','Applies from the next check. Auto is not restarted.'));}},
 tg:{lvl:'s',title:function(){return t('Уведомления в Telegram','Telegram notifications');},sum:function(){var d=D();return d.tg?t('включены · '+(d.tgSchedule==='daily'?'раз в день':'каждые '+d.tgInterval+' мин'),'on · '+(d.tgSchedule==='daily'?'daily':'every '+d.tgInterval+' min')):t('выключены','off');},
   body:function(){var d=D(),conf=(HV.inv.settings||{}).telegram_configured===true;return fTog('tg',t('Присылать отчёты','Send reports'))+fTxt('tgToken',t('Токен бота','Bot token'),conf?'••••••••':'123456:ABC…',t('Хранится только на роутере, на странице не показывается.','Stored on the router only, never shown on the page.')+(conf?' '+t('Пусто — оставить сохранённый.','Empty keeps the stored one.'):''),'password')+fTxt('tgChat',t('Получатель','Recipient'),t('@channel или Chat ID','@channel or Chat ID'))+
   fSel('tgSchedule',t('Когда присылать','When to send'),[['interval',t('Регулярно, через интервал','Regularly, at an interval')],['daily',t('Сводка раз в день','Daily summary')]])+(d.tgSchedule==='daily'?fSel('tgHour',t('Время сводки','Summary time'),Array.from({length:24},function(_,h){return [h,('0'+h).slice(-2)+':00'];}),t('Время Европа/Берлин','Europe/Berlin time')):fNum('tgInterval',t('Интервал отчётов','Report interval'),5,10080,t('мин','min')))+fTog('tgWeekly',t('Недельная и месячная сводка','Weekly and monthly summary'))+fSel('tgItems',t('Что присылать','What to send'),TG_ITEM_NAMES())+
   '<button class="btn sm" data-act="tgtest">'+t('Отправить тестовое сообщение','Send a test message')+'</button> '+(conf?'<button class="btn sm danger" data-act="tgforget">'+t('Удалить токен','Delete the token')+'</button> ':'')+'<a class="small" href="#" data-act="help" data-h="telegram">'+t('Как получить токен и Chat ID','How to get a token and Chat ID')+'</a>'+saveBar('tg');}},
 speed:{lvl:'x',title:function(){return t('Тест скорости: параметры','Speed test: parameters');},sum:function(){var d=D();return t('сервер: '+NODATA()+' · '+d.speedStreams+' потока · '+d.speedSec+' с','server: '+NODATA()+' · '+d.speedStreams+' streams · '+d.speedSec+' s');},
   body:function(){return fTog('speedOn',t('Разрешить тесты скорости','Allow speed tests'),t('Во время теста Auto ставится на паузу и сам продолжает. Есть суточная квота.','Auto pauses during a test and resumes by itself. Daily quota applies.'))+'<div class="f"><label for="s-speedSrv">'+t('Сервер для теста','Test server')+'</label><select id="s-speedSrv" disabled><option>'+NODATA()+'</option></select><div class="h">'+t('Роутер выбирает сервер теста сам; выбора нет.','The router picks the test server itself; there is no choice.')+'</div></div>'+fNum('speedStreams',t('Параллельные потоки','Parallel streams'),1,4)+fNum('speedSec',t('Секунд на направление','Seconds per direction'),2,15,t('с','s'))+
   '<details class="more"'+(HV.open.speedMore?' open':'')+' data-open="speedMore"><summary>'+t('Квоты','Quotas')+'</summary>'+fNum('speedMib',t('Трафик на один тест','Traffic per test'),1,32,t('МиБ','MiB'))+fNum('speedDaily',t('Суточная квота','Daily quota'),1,1024,t('МиБ','MiB'))+fNum('speedBusy',t('Не тестировать, если трафик VPN выше','Skip while VPN traffic is above'),1,1000,t('Мбит/с','Mbit/s'))+fTog('speedNew',t('Тестировать новый сервер после подключения','Test a new server after it connects'))+'</details>'+saveBar('speed');}},
 history:{lvl:'x',title:function(){return t('История и память','History and memory');},sum:function(){var d=D();return (d.mode==='work'?t('режим «Работа»','"Work" mode'):t('режим «Диагностика»','"Diagnostics" mode'))+' · '+t(d.days+' дн. · '+d.live+' записей',d.days+' days · '+d.live+' entries');},
   body:function(){var sm=(HV.st||{}).stats_mode||{},stg=sm.storage||{},cap=sm.capacity||{},sum=function(prefix){var n=0,seen=false;Object.keys(stg).forEach(function(k){if(k.indexOf(prefix)===0&&Number.isFinite(stg[k])){n+=stg[k];seen=true;}});return seen?n:NaN;},mb=function(b){return Number.isFinite(b)?(Math.round(b/104857.6)/10).toFixed(1).replace('.',locale==='en'?'.':',')+' '+t('МБ','MB'):NODATA();};
   return fSel('mode',t('Сбор статистики','Statistics collection'),[['work',t('Работа — только нужное, бережёт флеш','Work — essentials, saves flash')],['diagnostic',t('Диагностика — подробно, на время','Diagnostics — detailed, for a while')]],t('Диагностика сама вернётся в «Работу» по окончании срока.','Diagnostics returns to "Work" by itself at the end of the period.'))+(D().mode==='diagnostic'?fSel('diagHours',t('Срок диагностики','Diagnostics period'),[[24,'24 '+t('ч','h')],[72,'72 '+t('ч','h')],[168,'7 '+t('дн.','days')],[336,'14 '+t('дн.','days')]]):'')+fNum('days',t('Хранить подробную историю','Keep detailed history'),1,7,t('дн.','days'))+fNum('live',t('Записей в живом журнале','Live log entries'),1,2000)+
   '<p class="small mute">'+t('Сейчас занято: ','In use: ')+t('ОЗУ ','RAM ')+mb(sum('ram:'))+' · '+t('флеш ','flash ')+mb(sum('flash:'))+(Number.isFinite(cap.flash_free)?' · '+t('свободно на флеш ','flash free ')+mb(cap.flash_free):'')+'.</p><button class="btn sm danger" data-act="reset">'+t('Сбросить статистику…','Reset statistics…')+'</button>'+saveBar('history',t('Срок истории и живой журнал меняются при выключенном Auto.','History period and live log change with Auto off.'));}},
 ui:{lvl:'s',title:function(){return t('Язык и вид','Language and look');},sum:function(){return (locale==='ru'?'Русский':'English')+' · '+{system:t('тема как в системе','system theme'),light:t('светлая','light'),dark:t('тёмная','dark')}[HV.theme]+' · '+viewName();},
   body:function(){return '<div class="f"><label>'+t('Язык','Language')+'</label><span><button class="btn sm" data-act="lang">'+(locale==='ru'?'English':'Русский')+'</button></span></div>'+fSel('theme',t('Тема','Theme'),[['system',t('Как в системе','System')],['light',t('Светлая','Light')],['dark',t('Тёмная','Dark')]])+
   '<div class="f"><label>'+t('Вид','View')+'</label><span><button class="btn sm" data-act="view" data-v="'+(HV.view==='simple'?'console':'simple')+'">'+(HV.view==='simple'?t('Вид: Пульт','View: Console'):t('Вид: Простой','View: Simple'))+'</button></span><div class="h">'+t('Переключатель вида есть и в шапке, рядом с языком. Выбор хранится в этом браузере.','The view switch is also in the header next to the language. The choice is kept in this browser.')+'</div></div><p class="tiny mute">'+t('Оформления A/B/C заменены одним; меняются только язык, тема и вид.','Designs A/B/C are replaced by one; only language, theme and view change.')+'</p><button class="btn sm" data-act="rewiz">'+t('Пройти мастер заново','Run the wizard again')+'</button>';}},
 system:{lvl:'x',title:function(){return t('Система и диагностика','System and diagnostics');},sum:function(){var m=readinessModel(V.st,V.now),bad=(m.checks||[]).filter(function(c){return c.state!=='pass';}).length;return (m.reported?(bad?t('готовность: '+bad+' проблем','readiness: '+bad+' problems'):t('готовность: всё на месте','readiness: all present')):t('готовность: нет свежих данных','readiness: no fresh data'))+' · '+V.monitor.title.toLowerCase();},
   body:function(){return '<h3>'+t('Готовность роутера','Router readiness')+'</h3><div data-b="ready">'+readinessHTML()+'</div><div class="row" style="margin:8px 0"><button class="btn sm" data-act="prompt" data-h="">'+t('Промпт исправления для ИИ','AI fix prompt')+'</button>'+lanHelperHTML()+'<button class="btn sm" data-act="incident">'+t('Отчёт об инцидентах (печать)','Incident report (print)')+'</button></div>'+
   '<h3>'+t('Служба мониторинга','Monitoring service')+'</h3><p class="row small"><i class="lamp" data-lamp="mon"></i><span data-b="mon.text"></span></p><h3 id="sensors">'+t('Датчики: WAN и ключи серверов','Sensors: WAN and server keys')+'</h3><div data-b="sensors"></div>'+monitorExtra()+expertExtra()+
   '<h3 style="margin-top:8px">'+t('Живой журнал','Live log')+'</h3><div data-b="live">'+liveLogHTML()+'</div>'+
   '<h3 style="margin-top:10px">'+t('Справочник кодов','Code reference')+'</h3><input type="search" class="inp" data-act="codeq" aria-label="'+t('Код или слово','Code or word')+'" value="'+esc(HV.codeQ)+'" placeholder="'+t('Код или слово…','Code or word…')+'"><div data-codes>'+codesHTML(HV.codeQ)+'</div>';}},
 xdet:{lvl:'x',title:function(){return t('Для эксперта → Детектор и датчики','For experts → Detector and sensors');},sum:function(){return xdSum();},
   body:function(){return '<div data-secid="xdet" data-xd-host>'+(HV.open['sec-xdet']?xdBody():'')+'</div>';}},
 about:{lvl:'s',title:function(){return t('О программе, условия, лицензия','About, terms, licence');},sum:function(){return 'v'+VER().app+' · '+(V&&V.terms?t('условия приняты','terms accepted'):t('условия не приняты','terms not accepted'));},
   body:function(){var v=VER();return '<dl class="kv"><dt>'+t('Программа','Program')+'</dt><dd>HomenS.AI Auto VPN '+esc(v.app)+'</dd><dt>'+t('Стиль','Style')+'</dt><dd>'+esc(v.style)+'</dd><dt>'+t('Устройство','Device')+'</dt><dd>'+esc(v.model)+'</dd><dt>'+t('Разработчик','Developer')+'</dt><dd><a href="https://homensai.com" target="_blank" rel="noopener noreferrer">Serhii Khomenko · homensai.com</a></dd><dt>'+t('Условия','Terms')+'</dt><dd>'+(V&&V.terms?t('приняты вами, версия '+v.terms,'accepted by you, version '+v.terms):t('не приняты — будут предложены при включении Auto','not accepted — offered when Auto is turned on'))+'</dd></dl><p class="row" style="margin-top:8px"><button class="btn sm" data-act="terms">'+t('Прочитать условия','Read the terms')+'</button><button class="btn sm ghost" data-act="help" data-h="backup">'+t('Обновление, откат, удаление','Update, rollback, removal')+'</button><button class="btn sm ghost" data-act="help" data-h="about-project">'+t('О проекте и откуда идея','About the project and where the idea comes from')+'</button></p><p class="small">'+t('Почему в проекте столько математики, физики и биологии. Эти эксперименты появились потому, что автор проекта, Serhii Khomenko, всегда любил эти науки, хотя они всегда давались ему непросто. Поэтому каждая идея проверяется честно: сравнением со старым способом на симуляторе и на роутере, и остаётся только то, что действительно лучше.','Why this project has so much mathematics, physics and biology. These experiments exist because the author, Serhii Khomenko, has always loved these sciences, even though they never came easily to him. That is why every idea is tested honestly: compared with the previous method in the simulator and on the router, and only what is really better is kept.')+'</p>';}}
};
function monitorExtra(){
  var s=V.s,sqm=V.st.sqm,feat=[];
  feat.push(t('Сброс соединений при переходе (flow_reset): ','Connection reset on switch (flow_reset): ')+(s.flow_reset===false||s.flow_reset==='0'?t('выключен','off'):s.flow_reset===true||s.flow_reset==='1'?t('включён','on'):NODATA()));
  feat.push(t('Двойной DNS (dns_dual): ','Dual DNS (dns_dual): ')+(s.dns_dual===true||s.dns_dual==='1'?t('включён','on'):s.dns_dual===false||s.dns_dual==='0'?t('выключен','off'):NODATA()));
  feat.push('SQM: '+(s.sqm_enabled===true?t('включён','on')+(s.sqm_upload_kbit?' · '+s.sqm_upload_kbit+' '+t('кбит/с','kbit/s'):''):s.sqm_enabled===false?t('выключен','off'):NODATA())+(sqm&&codeOk(sqm.code)?' · '+sqm.code:''));
  return '<div class="row" style="margin:6px 0">'+(V.monitor.key!=='ok'?'<button class="btn sm" data-act="monrestore">'+t('Восстановить мониторинг','Restore monitoring')+'</button>':'')+'</div>'+
   '<details class="more"'+(HV.open.monMore?' open':'')+' data-open="monMore"><summary>'+t('Параметры службы и функции роутера','Service parameters and router features')+'</summary>'+fNum('monInterval',t('Интервал проверки','Probe interval'),10,300,t('с','s'))+fNum('checkpoint',t('Сохранение статистики на флеш (checkpoint)','Statistics checkpoint to flash'),300,3600,t('с','s'))+fNum('probeLimit',t('Лимит профилей за раунд','Profile limit per round'),1,16)+fTog('planning',t('Режим прогноза: показывать, переключил бы Auto сейчас','Forecast mode: show whether Auto would switch now'),t('Ничего не переключается.','Nothing is switched.'))+saveBar('monitor',t('Меняется при выключенном Auto.','Changes with Auto off.'))+
   '<ul class="small" style="margin:8px 0 0;padding-left:18px">'+feat.map(function(x){return '<li>'+esc(x)+'</li>';}).join('')+'</ul><p class="tiny mute">'+t('Эти три функции меняются только в /etc/config/homensai_vpn (на странице их нет, как и раньше).','These three features change only in /etc/config/homensai_vpn (not on the page, as before).')+'</p></details>';
}
function expertExtra(){
  return '<details class="more"'+(HV.open.detectMore?' open':'')+' data-open="detectMore"><summary>'+t('Эксперт: детектор сбоя и выбор сервера','Expert: failure detector and server pick')+'</summary><div data-secid="detect">'+
   fSel('failModel',t('Детектор сбоя канала','Channel failure detector'),[['hmm',t('Стандартный — модель HMM (по умолчанию)','Standard — HMM model (default)')],['hmm-fast',t('Быстрый — модель HMM, уходит раньше','Fast — HMM model, leaves earlier')],['consecutive',t('Прежнее правило: ошибки подряд','Previous rule: failures in a row')]],
     t('Стандартный не уходит ради сбоев короче 20 с; быстрый уходит примерно на 4 с раньше, но и на большинстве сбоев по 20 с. «Ошибок основного до перехода» действует только для прежнего правила. Меняется при выключенном Auto.','Standard ignores blips shorter than 20 s; Fast leaves about 4 s earlier but also on most 20 s blips. "Primary failures before switching" applies to the previous rule only. Changes with Auto off.'))+
   fSel('pickModel',t('Подбор лучшего сервера','Best-server pick'),[['simple',t('Простой — правило 20 % (по умолчанию)','Simple — the 20 % rule (default)')],['bayes',t('Байесовский — реже лишние смены и пробы','Bayesian — fewer useless changes and probes')]],
     t('Действует, когда включено «Подбирать лучший сервер». Байесовский находит лучший сервер медленнее.','Applies when "Pick the best server" is on. Bayesian finds a better server more slowly.'))+
   saveBar('detect',t('Детектор меняется при выключенном Auto: при сохранении программа предложит остановить Auto. Сама Auto не включит.','The detector changes with Auto off: saving offers to stop Auto. It never starts Auto by itself.'))+'</div></details>';
}
/* Expert group «Детектор и датчики»: fields, texts, renderer and saver come with the optional module (api.expertUI). */
var XD={ed:{},u:null,wait:false};
function xEnv(){return {t:t,esc:esc,HV:HV,XD:XD,ADV:ADV,saveBar:saveBar,needsStop:needsStop,rpcCall:rpcCall,draft:draftFromInventory,modal:modal,toast:toast,codeNotice:codeNotice,$$:$$,advNum:advNum,advRpc:advRpc,fill:xdFill,advChart:advChart,advLegend:advLegend,VER:VER,P95_MIN_N:P95_MIN_N,p95Text:p95Text,p95MaxText:p95MaxText,p95MaxClaim:p95MaxClaim};}
function xdU(){var a=LAZY_HELP.api;if(!XD.u&&a&&a.expertUI)XD.u=a.expertUI(xEnv());return XD.u;}
function xdLoad(){if(xdU()||XD.wait||LAZY_HELP.failed)return;XD.wait=true;helpApi().catch(function(){}).then(function(){XD.wait=false;if(HV.root)render();});}
function xdBody(){var u=xdU();if(u)return u.body();xdLoad();return '<p class="small mute">'+(LAZY_HELP.failed?helpFail():t('Загрузка…','Loading…'))+'</p>';}
function xdFill(){var h=$('[data-xd-host]',HV.root);if(h&&HV.open['sec-xdet'])h.innerHTML=xdBody();}
function xdSum(){var u=xdU();return u?u.sum():t('19 настроек','19 settings');}
function xdInput(el,ev){if(!el.dataset||!el.dataset.xd)return false;var u=xdU();if(u)u.input(el,ev);return true;}
function secHTML(id,o){o=o||{};var s=SECTIONS[id],lv={m:t('главное','main'),s:t('иногда','sometimes'),x:t('эксперт','expert')}[s.lvl];
  return '<details class="sec" id="sec-'+id+'" data-open="sec-'+id+'"'+(HV.open['sec-'+id]||o.open?' open':'')+'><summary><span class="t"><b>'+s.title()+' '+(o.tag===false?'':'<span class="lvl '+s.lvl+'">'+lv+'</span>')+'</b><span>'+esc(secSum(id))+'</span></span></summary><div class="body"><div style="height:8px"></div>'+s.body()+'</div></details>';}
function secBody(id){return SECTIONS[id].body();}
/* the form's values, and it says so until they are saved */
function secSum(id){return SECTIONS[id].sum()+(HV.dirty[id]?' · '+t('не сохранено','not saved'):'');}
/* a pasted «Id: 123456789» gives its digits; setup_config.telegram_destination does the same on the router */
function tgChatClean(v){var s=String(v||'').trim(),m=s.match(/(?:^|\s)id\s*[:=]?\s*(-?\d{1,20})[ \t]*(?:\r?\n|$)/i);return m?m[1]:s;}

/* ---------------- Saving with honest rules ---------------- */
function saveFail(code){failModal(t('Не сохранено','Not saved'),codeOk(code)?code:'SETUP-SAVE-FAILED');if(!LAZY_HELP.api)helpApi().catch(function(){}).then(function(){$$('[data-code-hint]').forEach(function(n){n.innerHTML=codeHint(n.dataset.codeHint);});});}
function saved(id,msg){HV.dirty[id]=false;return reloadInventory().then(function(){snapshotDraft();render();toast(msg||t('Сохранено. Роутер подтвердил.','Saved. Confirmed by the router.'));});}
function needsStop(){V=snap();return V.d.actionStop||V.control.on||V.control.transitioning;}
function withAutoOff(id,run){
  if(!needsStop())return run();
  modal({title:t('Сначала остановить Auto','Stop Auto first'),body:'<p>'+t('Эти настройки меняются только при выключенном Auto (CONFIG-STOP-AUTO-FIRST). Остановить Auto и сохранить? После сохранения Auto останется выключенным — включите его сами.','These settings change only with Auto off (CONFIG-STOP-AUTO-FIRST). Stop Auto and save? Auto stays off afterwards — turn it on yourself.')+'</p>',
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Остановить Auto и сохранить','Stop Auto and save'),cls:'pri',fn:function(){
      autoCommand(true);var until=Date.now()+150000;
      (function wait(){refreshNow().then(function(){V=snap();if(!needsStop()&&!V.op)return run();if(Date.now()<until)setTimeout(wait,3000);else failModal(t('Не сохранено','Not saved'),'CONFIG-STOP-AUTO-FIRST',t('роутер не подтвердил остановку Auto','the router did not confirm that Auto stopped'));});})();
    }}]});
}
function serversRows(){
  var rows=(HV.inv.servers||[]);
  return (HV.inv.profiles||[]).map(function(p){var r=rows.filter(function(x){return x.profile===p.id;})[0]||{};return {profile:p.id,name:r.name!=null?r.name:(p.name||p.id),channel:r.channel!=null?r.channel:'default',priority:Number(r.priority!=null?r.priority:100),enabled:r.enabled!==false};});
}
function savePair(d,done){
  if(!d.pairP||!d.pairR||d.pairP===d.pairR)return modal({title:t('Нужны два разных канала','Two different channels needed'),body:'<p>'+t('Основной и резерв должны быть разными VPN-клиентами.','Primary and reserve must be different VPN clients.')+'</p>'});
  return rpcCall('setup_check')().then(function(c){if(!(c&&c.passed===true))throw {code:'SETUP-CHECK-FAILED'};
    var s=HV.inv.settings||{};return rpcCall('setup_system',['source','target','interval','duration','session_loss','servers'])(d.pairP,d.pairR,Number(s.interval)||10,Number(s.native_duration)||10,d.allowDrop===true,serversRows());})
    .then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return done();});
}
function saveSection(id){
  var d=D();if(HV.busy.save)return;
  var run=function(p){HV.busy.save=true;return Promise.resolve().then(p).catch(function(e){saveFail(e&&e.code?e.code:e&&e.message&&codeOk(e.message)?e.message:'SETUP-SAVE-UNCONFIRMED');}).finally(function(){HV.busy.save=false;});};
  if(id==='pair')return withAutoOff(id,function(){return run(function(){return savePair(d,function(){return saved('pair');});});});
  if(id==='rules')return withAutoOff(id,function(){return run(function(){
    return rpcCall('setup_recovery',['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','rescue_stable','interval'])(Number(d.fails),Number(d.resOk),Number(d.cooldown),Number(d.dwell),d.returnPolicy,Number(d.retOk),Number(d.stab),Number(d.attempts),Number(d.window),Number(d.rescue),Number(d.interval))
      .then(function(r){if(!(r&&r.saved===true))throw {code:(r&&r.code)||'RECOVERY-SAVE-FAILED'};
        var s=HV.inv.settings||{};if((s.native_session_loss===true)!==(d.allowDrop===true))return savePair({pairP:currentPairId('source'),pairR:currentPairId('target'),allowDrop:d.allowDrop},function(){return true;});})
      .then(function(){return saved('rules');});});});
  if(id==='detect'){
    // expert block: the failure detector is saved with the stored rules (setup_recovery, Auto off), the pick model alone
    var s0=HV.inv.settings||{},cur=draftFromInventory(),modelChanged=d.failModel!==cur.failModel,pickChanged=d.pickModel!==cur.pickModel;
    var pick=function(){return pickChanged?rpcCall('setup_response',['metric','server_pick_model'])(s0.response_metric||'icmp-1.1.1.1',d.pickModel).then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};}):Promise.resolve();};
    var model=function(){return rpcCall('setup_recovery',['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','rescue_stable','interval','failure_model'])(Number(cur.fails),Number(cur.resOk),Number(cur.cooldown),Number(cur.dwell),cur.returnPolicy,Number(cur.retOk),Number(cur.stab),Number(cur.attempts),Number(cur.window),Number(cur.rescue),Number(cur.interval),d.failModel)
      .then(function(r){if(!(r&&r.saved===true))throw {code:(r&&r.code)||'RECOVERY-SAVE-FAILED'};});};
    if(modelChanged)return withAutoOff(id,function(){return run(function(){return model().then(pick).then(function(){return saved('detect');});});});
    return run(function(){return pick().then(function(){return saved('detect');});});
  }
  if(id==='xdet'){var u=xdU(),ch=u&&u.prep();if(!ch)return;
    var job=function(){return run(function(){return u.send(ch).then(function(){return saved('xdet');},function(e){return reloadInventory().then(function(){render();throw e;});});});};
    return ch.some(function(f){return f.stop;})?withAutoOff(id,job):job();}
  if(id==='load')return run(function(){
    return rpcCall('setup_probe',['level','boost'])(Number(d.level),d.level<=2?true:d.boost===true).then(function(r){if(!(r&&r.saved===true))throw {code:(r&&r.code)||'PROBE-SETTINGS-FAILED'};
      return rpcCall('setup_response',['metric','compare','fast_switch','ping_interval'])(d.method,d.compare===true,d.fast===true,Number(d.pingInt));})
      .then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return saved('load');});});
  if(id==='tg')return run(function(){
    var items=d.tgItems==='custom'?(HV.inv.settings||{}).telegram_items||'':d.tgItems==='none'?'none':TG_PRESETS[d.tgItems].join(',');
    return rpcCall('setup_telegram',['token','chat','enabled','interval','schedule','hour','weekly','monthly','items'])(String(d.tgToken||'').trim(),tgChatClean(d.tgChat),d.tg===true,Number(d.tgInterval),d.tgSchedule,Number(d.tgHour),d.tgWeekly===true,d.tgWeekly===true,items)
      .then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return saved('tg');});});
  if(id==='speed')return run(function(){
    if(Number(d.speedMib)>Number(d.speedDaily))throw {code:'SPEED-DAILY-LIMIT'};
    return rpcCall('setup_speed',['enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'])(d.speedOn===true,d.speedNew===true,Number(d.speedMib),Number(d.speedSec),Number(d.speedStreams),Number(d.speedDaily),Number(d.speedBusy))
      .then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return saved('speed');});});
  if(id==='history'||id==='monitor')return withAutoOff(id,function(){return run(function(){
    var s=HV.inv.settings||{},stats=d.mode==='diagnostic'?rpcCall('setup_stats',['mode','hours'])('diagnostic',Number(d.diagHours)):rpcCall('setup_stats',['mode'])('work');
    return (id==='history'?stats:Promise.resolve({saved:true})).then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};
      return rpcCall('setup_monitor',['interval','checkpoint','probe_limit','planning_enabled','live_log_limit','history_days'])(Number(id==='monitor'?d.monInterval:Number(s.interval)||10),Number(id==='monitor'?d.checkpoint:Number(s.checkpoint)||900),Number(id==='monitor'?d.probeLimit:Math.min(16,Number(s.probe_limit)||16)),id==='monitor'?d.planning===true:s.plan_enabled===true,Number(d.live),Number(d.days));})
      .then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return saved(id);});});});
}
function saveImmediate(k,v){
  var s=HV.inv.settings||{};
  if(k==='pick')return rpcCall('setup_response',['metric','server_pick'])(s.response_metric||'icmp-1.1.1.1',v===true).then(function(r){if(r&&r.saved===true){s.server_pick=v===true;D().pick=v===true;toast(t('Сохранено. Роутер применит со следующей проверки серверов.','Saved. The router applies it at the next server check.'));render();}else{saveFail(r&&r.code);D().pick=!v;render();}}).catch(function(){saveFail('SETUP-SAVE-UNCONFIRMED');D().pick=!v;render();});
  if(k==='fast')return rpcCall('setup_response',['metric','fast_switch'])(s.response_metric||'icmp-1.1.1.1',v===true).then(function(r){if(r&&r.saved===true){s.fast_switch=v===true;toast(t('Сохранено.','Saved.'));}else{saveFail(r&&r.code);D().fast=!v;render();}}).catch(function(){saveFail('SETUP-SAVE-UNCONFIRMED');D().fast=!v;render();});
}
function discardSection(id){HV.draft=null;HV.dirty[id]=false;XD.ed={};render();}
function secOf(el){var x=el.closest('[data-secid]');if(x)return x.dataset.secid;var s=el.closest('details.sec');if(s)return s.id.replace('sec-','');var b=el.closest('.savebar');return b?null:null;}
function tgTest(){if(HV.busy.tg)return;HV.busy.tg=true;rpcCall('telegram_test')().then(function(r){var c=codeOk(r&&r.code)?r.code:'TELEGRAM-TEST-UNKNOWN';if(c==='TELEGRAM-TEST-DELIVERED')toast(t('Тестовое сообщение доставлено','Test message delivered'));else failModal('Telegram',c);}).catch(function(){failModal('Telegram','TELEGRAM-TEST-UNKNOWN');}).finally(function(){setTimeout(function(){HV.busy.tg=false;},10000);});}
function tgForget(){modal({title:t('Удалить сохранённый токен?','Delete the stored token?'),body:'<p>'+t('Отчёты в Telegram будут выключены.','Telegram reports will be turned off.')+'</p>',buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Удалить токен','Delete token'),cls:'danger',fn:function(){rpcCall('telegram_forget')().then(function(r){if(r&&r.saved===true)saved('tg',t('Токен удалён','Token deleted'));else saveFail(r&&r.code);}).catch(function(){saveFail('SETUP-SAVE-UNCONFIRMED');});}}]});}

/* Auto-adaptation (network advisor) and the master slider «Быстрая реакция ↔ Без лишних переключений» (2.1.0-alpha9,
   docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md; owner mockup private/math/master-slider). Also the recovery-time
   statistics with the honest P95 and the new sensors (WAN diagnosis, server key pins).
   Single source: every state value is the status field network_advisor (status RPC, each poll); the curve (the anchors of
   the offline study) is the only thing read from rpc advisor, once per page. Changes go through rpc advisor_settings /
   advisor_apply; the router checks every safety rule again and answers with a code. Nothing here starts Auto. */
var ADV={curve:null,load:null,err:null,t:null,fine:null,per:'week'};
var ADV_TOUR_KEY='homensai-vpn-advisor-tour';
var ADV_SAFE={theta:[0.5,0.99,0.01],dur_b:[1,15,0.5],pg:[0.5,0.99,0.01]};
var ADV_STEPS={theta:0.01,dur_b:0.5,losses:1,pg:0.01,primary_stable:5,rescue_stable:1};
function advSt(){var a=V&&V.st&&V.st.network_advisor;return a&&typeof a==='object'&&a.current&&typeof a.current==='object'?a:null;}
function advCurveOk(c){return !!(c&&Array.isArray(c.anchors)&&c.anchors.length>=2&&Array.isArray(c.params)&&Array.isArray(c.metrics)&&c.anchors.every(function(a){return a&&Number.isFinite(a.t)&&Array.isArray(a.p)&&Array.isArray(a.m);}));}
function advLoad(){
  if(ADV.curve||ADV.load||ADV.err)return;
  ADV.load=rpcCall('advisor')().then(function(r){if(advCurveOk(r&&r.curve))ADV.curve=r.curve;else ADV.err=r&&codeOk(r.code)?r.code:'ADVISOR-CURVE-INVALID';},function(){ADV.err='ADVISOR-UNAVAILABLE';})
    .then(function(){ADV.load=null;if(HV.root)render();});
}
/* the same interpolation as advisor.interpolate: linear between anchors, every setting rounded to its step */
function advStep(x,s){var v=Math.floor(x/s+0.5)*s;return s>=1?Math.floor(v+0.5):Math.floor(v*100+0.5)/100;}
function advAt(t){
  var c=ADV.curve,A=c.anchors,i=0;
  if(t<-1e-9){  // fast segment: a step (advisor.fast_anchor)
    var q=null,p0={},m0={};(c.fast_anchors||[]).forEach(function(a){if(t<=a.t+1e-9)q=a;});
    if(q){c.params.concat(c.fast_params||[]).forEach(function(k,j){p0[k]=j<q.p.length?q.p[j]:q.x[j-q.p.length];});c.metrics.forEach(function(k,j){m0[k]=q.m[j];});return {t:q.t,p:p0,m:m0};}
    t=0;}
  t=Math.min(1,Math.max(0,t));
  while(i<A.length-2&&A[i+1].t<=t)i++;
  var a=A[i],b=A[i+1],f=(t-a.t)/(b.t-a.t),p={},m={};
  c.params.forEach(function(k,j){p[k]=advStep(a.p[j]+f*(b.p[j]-a.p[j]),(c.steps||ADV_STEPS)[k]||0.01);});
  c.metrics.forEach(function(k,j){var u=a.m[j],v=b.m[j];m[k]=u==null||v==null?null:u+f*(v-u);});
  return {t:Math.floor(t*100+0.5)/100,p:p,m:m};
}
function advDefault(){var c=ADV.curve,a=c&&c.alpha8,p={},m={};if(!a||!Array.isArray(a.p)||!Array.isArray(a.m))return null;c.params.forEach(function(k,j){p[k]=a.p[j];});c.metrics.forEach(function(k,j){m[k]=a.m[j];});return {p:p,m:m};}
function advNum(v,d){if(v==null||!Number.isFinite(Number(v)))return '—';var s=(Math.round(Number(v)*Math.pow(10,d||0))/Math.pow(10,d||0)).toFixed(d||0);return locale==='en'?s:s.replace('.',',');}
function advModeName(m){return {auto:t('Авто','Auto'),advice:t('Совет + «Применить»','Advice + "Apply"'),manual:t('Вручную','Manual')}[m]||m;}
function advWhere(a){var c=a.current;if(c.failure_model==='consecutive')return '<span class="chip">'+t('ползунок не действует','slider inactive')+'</span>';
  if(c.attached&&Number.isFinite(c.slider_t))return '<span class="chip acc">t = '+advNum(c.slider_t,2)+' · '+advZone(c.slider_t)+'</span>';
  if(c.label==='preset')return '<span class="chip warn">'+t('По умолчанию','Default')+'</span>';
  return '<span class="chip vio">'+t('Пользовательская','Custom')+'</span>';}
function advZone(x){return x<0?t('быстрый сегмент','fast segment'):x<0.2?t('быстрая реакция','fast reaction'):x>0.8?t('без лишних переключений','no unnecessary switches'):t('баланс','balance');}
function advReason(o){return o?(locale==='en'?o.reason_en:o.reason_ru)||'':'';}
function advFew(r){return !r||r.state==='no-data'||r.state==='few-data';}

/* ---------- the chart: losses per day against unnecessary switches per day, the slider curve and its point ---------- */
function advChart(tNow,tDraft,small,custom){
  var c=ADV.curve;if(!c)return '<p class="small mute">'+(ADV.err?codeNotice(ADV.err):t('Кривая загружается…','Loading the curve…'))+'</p>';
  var xi=c.metrics.indexOf('unnecessary_per_day'),yi=c.metrics.indexOf('downtime_s_day'),def=advDefault(),pts=c.anchors.map(function(a){return [a.m[xi],a.m[yi]];});
  if(def)pts.push([def.m.unnecessary_per_day,def.m.downtime_s_day]);
  var cc=(advSt()||{}).current||{},FA=(c.fast_anchors||[]).filter(function(a){return a.t>=(cc.turbo?-0.7:cc.fast?-0.2:0)-1e-9;});
  FA.forEach(function(a){pts.push([a.m[xi],a.m[yi]]);});
  pts=pts.filter(function(p){return Number.isFinite(p[0])&&Number.isFinite(p[1]);});
  var x0=Math.min.apply(null,pts.map(function(p){return p[0];})),x1=Math.max.apply(null,pts.map(function(p){return p[0];})),y0=Math.min.apply(null,pts.map(function(p){return p[1];})),y1=Math.max.apply(null,pts.map(function(p){return p[1];}));
  var dx=(x1-x0)||1,dy=(y1-y0)||1;x0=Math.max(0,x0-dx*0.12);x1+=dx*0.12;y0-=dy*0.18;y1+=dy*0.18;
  var W=small?320:640,H=small?190:300,PL=small?36:48,PR=small?10:16,PT=12,PB=small?30:40;
  var X=function(v){return (PL+(v-x0)/(x1-x0)*(W-PL-PR)).toFixed(1);},Y=function(v){return (PT+(y1-v)/(y1-y0)*(H-PT-PB)).toFixed(1);},s='';
  for(var i=0;i<=3;i++){var yv=y0+(y1-y0)*i/3,xv=x0+(x1-x0)*i/3;
    s+='<line class="ax" x1="'+PL+'" x2="'+(W-PR)+'" y1="'+Y(yv)+'" y2="'+Y(yv)+'"/><text x="'+(PL-4)+'" y="'+(Number(Y(yv))+3)+'" text-anchor="end">'+advNum(yv,0)+'</text>';
    s+='<line class="ax" y1="'+PT+'" y2="'+(H-PB)+'" x1="'+X(xv)+'" x2="'+X(xv)+'"/><text x="'+X(xv)+'" y="'+(H-PB+12)+'" text-anchor="middle">'+advNum(xv,2)+'</text>';}
  s+='<text x="'+((PL+W-PR)/2)+'" y="'+(H-4)+'" text-anchor="middle">'+t('лишних переключений в сутки →','unnecessary switches per day →')+'</text>';
  s+='<text transform="translate(10 '+((PT+H-PB)/2)+') rotate(-90)" text-anchor="middle">'+t('простой, с/сутки ↑','downtime, s/day ↑')+'</text>';
  s+='<polyline class="curve" points="'+c.anchors.map(function(a){return X(a.m[xi])+','+Y(a.m[yi]);}).join(' ')+'"/>';
  c.anchors.forEach(function(a){s+='<circle class="anc" cx="'+X(a.m[xi])+'" cy="'+Y(a.m[yi])+'" r="3"/>';});
  FA.forEach(function(a){s+='<circle class="anc fast" cx="'+X(a.m[xi])+'" cy="'+Y(a.m[yi])+'" r="3"/>';});
  var PRO=small?[]:[[0,t('«Быстрая реакция»','"Fast reaction"')],[0.5,t('«Баланс»','"Balance"')],[1,t('«Без лишних»','"No unnecessary"')]].map(function(q){var m=advAt(q[0]).m;return {t:q[0],n:q[1],x:Number(X(m.unnecessary_per_day)),y:Number(Y(m.downtime_s_day))};});
  if(def){var dxp=X(def.m.unnecessary_per_day),dyp=Y(def.m.downtime_s_day);s+='<rect class="mk def" x="'+(dxp-5)+'" y="'+(dyp-5)+'" width="10" height="10" transform="rotate(45 '+dxp+' '+dyp+')"><title>'+t('По умолчанию (alpha8)','Default (alpha8)')+'</title></rect>';PRO.unshift({x:Number(dxp),y:Number(dyp),k:1});}
  PRO.forEach(function(p){if(!p.k)s+='<path class="mk pro" d="M'+p.x+' '+(p.y-12)+'L'+(p.x+5)+' '+(p.y-3)+'L'+(p.x-5)+' '+(p.y-3)+'Z"><title>'+esc(p.n)+' t = '+p.t+'</title></path>';});
  if(!small&&xdU())s+=xdU().chartLabels(PRO,W);  /* the labels are placed without overlaps by the optional module */
  if(Number.isFinite(tNow)){var n=advAt(tNow).m;s+='<circle class="now'+(custom?' custom':'')+'" cx="'+X(n.unnecessary_per_day)+'" cy="'+Y(n.downtime_s_day)+'" r="'+(small?7:9)+'"><title>'+t('Сейчас на роутере','Now on the router')+'</title></circle>';}
  if(Number.isFinite(tDraft)){var d=advAt(tDraft).m;s+='<circle class="halo" cx="'+X(d.unnecessary_per_day)+'" cy="'+Y(d.downtime_s_day)+'" r="13"/><circle class="pt" cx="'+X(d.unnecessary_per_day)+'" cy="'+Y(d.downtime_s_day)+'" r="6"/>';}
  return '<svg class="advchart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+t('Кривая ползунка: простой в сутки против лишних переключений в сутки; точка — положение','Slider curve: downtime per day against unnecessary switches per day; the dot is the position')+'">'+s+'</svg>';
}
function advLegend(){return '<div class="legend"><span><i class="lg-curve"></i>'+t('кривая ползунка (11 опорных точек)','slider curve (11 anchors)')+'</span><span><i class="lg-now"></i>'+t('сейчас на роутере','now on the router')+'</span><span><i class="lg-pt"></i>'+t('положение ползунка','slider position')+'</span><span><i class="lg-def"></i>'+t('по умолчанию (alpha8)','default (alpha8)')+'</span><span><i class="lg-pro"></i>'+t('готовые положения','named positions')+'</span></div><p class="tiny mute">'+t('Прогноз офлайн-модели (откалиброван по MT3000), не измерения этого роутера. Простой — секунды без интернета в сутки.','Forecast of the offline model (calibrated on the MT3000), not measurements of this router. Downtime is seconds without internet per day.')+'</p>';}
function advExpect(m,approx,p){return '<div class="expect" data-adv="expect"><b>'+t('Ожидаемо','Expected')+(approx?' ≈':'')+':</b> '+t('уход на резерв через ~','switch to the reserve after ~')+'<b>'+advNum(m.switch_after_s,0)+' '+t('с','s')+'</b> · '+t('пережидает обрывы до ~','rides out outages up to ~')+'<b>'+advNum(m.rides_out_s,0)+' '+t('с','s')+'</b> · '+t('лишних переключений ≈ ','unnecessary switches ≈ ')+'<b>'+advNum(m.unnecessary_per_day,2)+'</b> '+t('в сутки','per day')+' · '+t('простой ≈ ','downtime ≈ ')+'<b>'+advNum(m.downtime_s_day,0)+' '+t('с','s')+'</b> '+t('в сутки','per day')+'</div>'+(p&&xdU()?xdU().note(p):'');}

/* ---------- simple view: card «Автоподстройка» (live binding adv.card) ---------- */
function advCardHTML(){
  var a=advSt();
  if(!a)return '<div class="hline"><i class="lamp l n"></i><h2>'+t('Автоподстройка','Auto-adaptation')+'</h2></div><p class="small mute">'+t('Роутер пока не сообщает её состояние (служба мониторинга старой версии или остановлена).','The router does not report its state yet (an older or stopped monitoring service).')+'</p>';
  advLoad();
  var c=a.current,r=a.recommendation,few=advFew(r),off=c.failure_model==='consecutive',lamp=off?'n':few?'y':'g',lc=a.last_change,out='';
  out+='<div class="hline"><i class="lamp l '+lamp+'" role="img" aria-label="'+(lamp==='g'?t('зелёный','green'):lamp==='y'?t('жёлтый','yellow'):t('серый','grey'))+'"></i><h2>'+t('Автоподстройка','Auto-adaptation')+': '+esc(advModeName(a.mode))+'</h2></div>';
  out+='<p class="row small">'+advWhere(a)+'<span class="mute">'+t('окно данных ','data window ')+a.window_days+' '+t(a.window_days===1?'день':'дней',a.window_days===1?'day':'days')+'</span></p>';
  if(off)out+='<p class="note">'+t('Детектор «ошибки подряд»: ползунок и автоподстройка на него не действуют.','Detector "failures in a row": the slider and the adaptation do not apply to it.')+'</p>';
  else if(few)out+='<p class="note warn">'+esc(advReason(r)||t('Мало данных — действуют текущие настройки.','Not enough data — the current settings stay.'))+'</p>';
  else if(r)out+='<p class="small">'+esc(advReason(r))+'</p>';
  out+='<dl class="kv"><dt>'+t('Последнее изменение','Last change')+'</dt><dd>'+(lc&&Number.isFinite(lc.time)?esc(fmtTime(lc.time,true))+' · '+(lc.to==null?t('свои значения','own values'):'t '+(lc.from==null?'—':advNum(lc.from,2))+' → '+advNum(lc.to,2))+' · '+esc({auto:t('автоматически','automatically'),owner:t('владелец','owner'),'owner-manual':t('владелец, вручную','owner, manual')}[lc.source]||lc.source||'')+'<br><span class="small mute">'+esc(advReason(lc))+'</span>':t('ещё не было','none yet'))+'</dd></dl>';
  if(!off&&ADV.curve){var tn=Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t;out+='<div class="advmini">'+advChart(tn,null,true,!c.attached)+'</div>'+advExpect(advAt(tn).m,!c.attached);}
  else if(!off)out+=advChart(null,null,true);
  out+='<p class="row" style="margin-top:8px"><button class="btn sm" data-act="advopen">'+t('Настроить (для эксперта)','Adjust (expert)')+'</button>'+advOfferHTML()+'</p>';
  return out;
}
function advOfferHTML(){return store.get(ADV_TOUR_KEY,null)===null?'<button class="btn sm pri" data-act="advtour" data-i="0">🎓 '+t('Как это работает (5 шагов)','How it works (5 steps)')+'</button><button class="btn sm ghost" data-act="advnotour">'+t('Не сейчас','Not now')+'</button>':'';}

/* ---------- expert settings: section adv (simple view «Для эксперта», console tab Auto) ---------- */
function advCurParams(c){return {theta:c.theta,dur_b:c.dur_b,pg:c.pg,primary_stable:c.primary_stable,rescue_stable:c.rescue_stable};}
function advRows(a,draft,fine){
  var c=a.current,cur=advCurParams(c),def=advDefault()||{p:{},m:{}},tn=Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t,mNow=advAt(tn).m,h='';
  var P=[['theta',t('Порог ухода θ','Leave threshold θ'),'',2,''],
    ['dur_b',t('Длина «короткого обрыва» в модели','Short-outage length of the model'),'',1,' '+t('с','s')],
    ['pg',t('Порог возврата P(здоров)','Return threshold P(healthy)'),'',2,''],
    ['primary_stable',t('Стабильность основного перед возвратом','Primary stability before the return'),'',0,' '+t('с','s')],
    ['rescue_stable',t('Возврат с упавшего резерва через','Return from a failed reserve after'),'',0,' '+t('с','s')]];
  P.forEach(function(d){var v=fine&&fine[d[0]]!=null?fine[d[0]]:draft.p[d[0]],n=cur[d[0]],ch=Number.isFinite(v)&&Number.isFinite(n)&&Math.abs(v-n)>1e-9,ar=ch?(v>n?'↑':'↓'):'';
    var hint=xdU()?xdU().hint(d[0]):'';  // the long explanations load with the expert module (help<N>.js)
    h+='<tr><td>'+esc(d[1])+(hint?'<div class="tiny mute">'+esc(hint)+'</div>':'')+'</td><td class="num'+(ch?' chg':'')+'">'+advNum(v,d[3])+d[4]+(ar?'<span class="ar" aria-label="'+t('изменится','will change')+'">'+ar+'</span>':'')+'</td><td class="num">'+advNum(n,d[3])+d[4]+'</td><td class="num mute">'+advNum(def.p[d[0]],d[3])+d[4]+'</td></tr>';});
  var M=[['switch_after_s',t('Уход после долгого обрыва через','Leaves a long outage after'),0,' '+t('с','s')],['rides_out_s',t('Пережидает обрывы до','Rides out outages up to'),0,' '+t('с','s')],['unnecessary_per_day',t('Лишних переключений в сутки','Unnecessary switches per day'),2,''],['downtime_s_day',t('Простой в сутки','Downtime per day'),0,' '+t('с','s')],['return_after_40s_blackout_s',t('Возврат после обрыва 40 с через','Return after a 40 s outage in'),0,' '+t('с','s')],['reserve_failure_worst_downtime_s',t('Худший случай: упал и резерв (простой)','Worst case: the reserve fails too (downtime)'),0,' '+t('с','s')]];
  M.forEach(function(d){var v=fine?null:draft.m[d[0]],n=mNow[d[0]],ch=v!=null&&n!=null&&Math.abs(v-n)>1e-6;h+='<tr class="sub"><td>'+esc(d[1])+'</td><td class="num'+(ch?' chg':'')+'">'+(fine?'≈':'')+advNum(fine?n:v,d[2])+d[3]+'</td><td class="num">'+advNum(n,d[2])+d[3]+'</td><td class="num mute">'+(def.m[d[0]]==null?'—':advNum(def.m[d[0]],d[2])+d[3])+'</td></tr>';});
  [[t('Быстрое обнаружение: пингов подряд','Fast detection: pings in a row'),'2'],[t('Интервал и частота проверок','Check interval and boost'),t('ползунок «нагрузка ↔ надёжность»','the slider "load ↔ reliability"')],[t('Возврат без уверенности модели','Return without model confidence'),t('после 300 с без ошибок','after 300 s without errors')]].forEach(function(f){h+='<tr class="sub fixed"><td>'+esc(f[0])+'<div class="tiny mute">'+t('не меняется этим ползунком','not changed by this slider')+'</div></td><td class="num" colspan="3">'+esc(f[1])+'</td></tr>';});
  return '<div class="scrollx"><table class="tbl advtbl" data-adv="table"><thead><tr><th>'+t('Переменная','Variable')+'</th><th class="num">'+(fine?t('Свои значения','Own values'):t('Положение ползунка','Slider position'))+'</th><th class="num">'+t('Сейчас на роутере','Now on the router')+'</th><th class="num">'+t('По умолчанию','Default')+'</th></tr></thead><tbody>'+h+'</tbody></table></div><p class="tiny mute">'+t('Жёлтым — что изменится при применении (стрелка — куда). Нижние строки — прогноз модели, серые — не зависят от ползунка.','Yellow: what changes when applied (the arrow shows where). The lower rows are the model forecast, grey rows do not depend on the slider.')+'</p>';
}
function advDraftT(a){var c=a.current;return ADV.t!=null?ADV.t:c.attached&&Number.isFinite(c.slider_t)?c.slider_t:Number.isFinite(c.nearest_t)?c.nearest_t:0.5;}
/* Without the optional module the fast row and the switches are absent: their state stays visible and a failure offers Retry. */
function xdFast(c){var o=function(v){return v?t('вкл','on'):t('выкл','off');};return '<p class="note">'+t('Быстрый сегмент: ','Fast segment: ')+o(c.fast)+' · '+t('Турбо: ','Turbo: ')+o(c.turbo)+(LAZY_HELP.failed?' · '+helpFail():'')+'</p>';}
function advSectionBody(){
  var a=advSt();
  if(!a)return '<p class="small mute">'+t('Роутер пока не сообщает состояние автоподстройки (служба мониторинга старой версии или остановлена). Настройки недоступны.','The router does not report the auto-adaptation state yet (an older or stopped monitoring service). Settings unavailable.')+'</p>';
  advLoad();if(HV.open['sec-adv'])xdLoad();
  var c=a.current,r=a.recommendation,off=c.failure_model==='consecutive',auto=a.mode==='auto',fine=ADV.fine,custom=!!fine||c.label==='custom',out='';
  out+=advOfferHTML()?'<p class="note row">'+t('Новое: ползунок реакции на сбои и автоподстройка.','New: the failure-reaction slider and auto-adaptation.')+' '+advOfferHTML()+'</p>':'';
  out+='<div class="row advhead"><span>'+advWhere(a)+'</span><span class="small mute">'+t('режим: ','mode: ')+esc(advModeName(a.mode))+'</span></div>';
  out+='<div class="advseg" role="group" aria-label="'+t('Режим','Mode')+'">'+['auto','advice','manual'].map(function(m){return '<button class="btn sm" data-act="advmode" data-m="'+m+'" aria-pressed="'+(a.mode===m)+'">'+esc(advModeName(m))+(m==='auto'?' <span class="tiny">'+t('(система двигает сама)','(the system moves it)')+'</span>':'')+'</button>';}).join('')+'</div>';
  out+='<div class="advseg" role="group" aria-label="'+t('Окно данных','Data window')+'"><span class="small mute">'+t('Окно данных:','Data window:')+'</span>'+[1,7,30].map(function(w){return '<button class="btn sm" data-act="advwin" data-w="'+w+'" aria-pressed="'+(a.window_days===w)+'">'+w+' '+t(w===1?'день':'дней',w===1?'day':'days')+'</button>';}).join('')+'</div>';
  if(off)out+='<p class="note warn">'+t('Детектор сбоя — «ошибки подряд»: ползунок на него не действует. Выберите детектор HMM в «Эксперт: детектор сбоя», чтобы пользоваться ползунком.','The failure detector is "failures in a row": the slider does not apply to it. Choose the HMM detector in "Expert: failure detector" to use the slider.')+' <a class="code" href="#" data-act="code" data-code="ADVISOR-MODEL-CONSECUTIVE">ADVISOR-MODEL-CONSECUTIVE</a></p>';
  else if(advFew(r))out+='<p class="note warn">'+t('Мало данных: ','Not enough data: ')+esc(advReason(r)||t('расчёт ещё не выполнялся (ночью в 03:30).','no calculation yet (nightly at 03:30).'))+'</p>';
  else if(r&&r.state==='shift'&&!auto)out+='<p class="note">'+t('Совет: ','Advice: ')+esc(advReason(r))+' <button class="btn sm pri" data-act="advrec">'+t('Применить','Apply')+' t = '+advNum(r.t,2)+'</button></p>';
  else if(r)out+='<p class="note">'+(auto?t('Автоматически: ','Automatically: '):'')+esc(advReason(r))+'</p>';
  if(auto&&!off)out+='<p class="small mute">'+t('«Авто»: ползунок двигает система — не больше 0,1 в сутки, при ≥ 5 событиях и экономии ≥ 5 %. Двигать самому — «Вручную» или «Совет».','Auto: the system moves the slider — at most 0.1 a day, with ≥ 5 events and a saving ≥ 5 %. To move it yourself: Manual or Advice.')+'</p>';
  var td=advDraftT(a),draft=ADV.curve?advAt(td):null,dis=auto||off||custom;
  out+='<div class="advslider"><div class="ends"><span>'+t('Быстрая реакция','Fast reaction')+'</span><span>'+t('Без лишних переключений','No unnecessary switches')+'</span></div>'+
    '<input class="slider" type="range" id="adv-t" min="0" max="1" step="0.01" value="'+Math.max(0,td)+'" aria-label="'+t('Быстрая реакция — без лишних переключений','Fast reaction — no unnecessary switches')+'"'+(dis||!ADV.curve?' disabled':'')+'>'+
    '<div class="ticks"><span>0</span><span>'+advNum(0.25,2)+'</span><span>'+advNum(0.5,1)+'</span><span>'+advNum(0.75,2)+'</span><span>1</span></div>'+
    '<p class="row"><output data-adv="tval">t = '+advNum(td,2)+' · '+esc(advZone(td))+'</output>'+(!dis&&ADV.curve?'<button class="btn sm pri" data-act="advapply"'+(c.attached&&Math.abs(td-c.slider_t)<0.005?' disabled':'')+'>'+t('Применить положение','Apply the position')+'</button>':'')+(ADV.t!=null?'<button class="btn sm ghost" data-act="advreset">'+t('Вернуть как на роутере','Back to the router value')+'</button>':'')+'</p>'+(xdU()?xdU().fastRow(c,dis,td):xdFast(c))+
    (custom?'<p class="note warn">'+t('Ползунок отвязан: значения заданы вручную («Пользовательская»).','The slider is detached: values set by hand ("Custom").')+' <button class="btn sm" data-act="advrebind">'+t('Привязать к ползунку','Attach to the slider')+' (t = '+advNum(c.nearest_t,2)+')</button></p>':'')+'</div>';
  if(xdU()&&!off)out+=xdU().fastAdmin(c);
  if(draft){out+='<div data-adv="expectbox">'+advExpect(fine?advAt(c.nearest_t).m:draft.m,!!fine||custom,fine?null:draft.p)+'</div><div class="advchartbox" data-adv="chart">'+advChart(Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t,custom?null:td,false,custom)+'</div>'+advLegend();}
  else out+=advChart(null,null,false);
  if(draft)out+='<h3>'+t('Все переменные','All variables')+'</h3><div data-adv="tablebox">'+advRows(a,draft,fine)+'</div>';
  out+='<div class="row" style="margin-top:8px"><button class="tgl" role="switch" data-act="advfine" aria-checked="'+(!!fine)+'"'+(off||!ADV.curve?' disabled':'')+'><span class="trk"></span>'+t('Тонкая настройка','Fine tuning')+'</button></div>'+(fine?advFineHTML(c):'');
  out+=more('advSafe',t('Правила безопасности (роутер проверяет при каждом изменении; код — объяснение)','Safety rules (checked by the router at every change; the code explains)'),'<ul class="small">'+[['ADVISOR-OUT-OF-BOUNDS',t('θ и P(G) 0,50–0,99; «короткий обрыв» 1–15 с; стабильность 30–600 с; возврат после отказа резерва 0–60 с','θ and P(G) 0.50–0.99; short outage 1–15 s; stability 30–600 s; return after a failed reserve 0–60 s')],['ADVISOR-PG-BELOW-THETA',t('P(G) не ниже θ','P(G) not below θ')],['ADVISOR-RIDE-NOT-BELOW-LEAVE',t('пережидаемый обрыв короче времени ухода','the ridden-out outage is shorter than the leave time')],['ADVISOR-RESCUE-ABOVE-STABLE',t('возврат после отказа резерва не дольше стабильности основного','the rescue return is not longer than the primary stability')],['ADVISOR-BUSY-SWITCH',t('ничего не меняется во время обрыва или переключения; Auto не включается','nothing changes during an outage or a switch; Auto is not started')]].map(function(r){return '<li>'+esc(r[1])+' <a class="code" href="#" data-act="code" data-code="'+r[0]+'">'+r[0]+'</a></li>';}).join('')+'</ul>');
  if(a.last_change)out+='<p class="small mute">'+t('Последнее изменение: ','Last change: ')+esc(fmtTime(a.last_change.time,true))+' · '+esc(advReason(a.last_change))+'</p>';
  return out;
}
function advFineHTML(c){
  var f=ADV.fine,rows=[['theta',t('Порог ухода θ','Leave threshold θ'),2],['dur_b',t('Длина «короткого обрыва»','Short-outage length'),1],['pg',t('Порог возврата P(G)','Return threshold P(G)'),2]];
  var note=xdU()?xdU().hint('fine'):'';
  return '<div class="advfine">'+(note?'<p class="note">'+esc(note)+'</p>':'')+
    rows.map(function(r){var s=ADV_SAFE[r[0]];return '<div class="fine"><label for="advf-'+r[0]+'">'+esc(r[1])+'</label><output data-adv="o-'+r[0]+'">'+advNum(f[r[0]],r[2])+(r[0]==='dur_b'?' '+t('с','s'):'')+'</output><input class="slider" type="range" id="advf-'+r[0]+'" data-advf="'+r[0]+'" min="'+s[0]+'" max="'+s[1]+'" step="'+s[2]+'" value="'+f[r[0]]+'"><div class="h">'+advNum(s[0],r[2])+'–'+advNum(s[1],r[2])+'</div></div>';}).join('')+
    '<p class="small" data-adv="finewhy">'+esc(ADV.fineWhy||'')+'</p><div class="savebar"><button class="btn pri sm" data-act="advsave">'+t('Сохранить свои значения','Save own values')+'</button><button class="btn sm ghost" data-act="advfine">'+t('Отменить','Discard')+'</button></div></div>';
}
/* dragging: only the parts that depend on the position are repainted (point, expectation, table, value) */
function advPaint(){
  var a=advSt();if(!a||!ADV.curve||!HV.root)return;var c=a.current,td=advDraftT(a),d=advAt(td),custom=!!ADV.fine||c.label==='custom';
  var set=function(k,h){$$('[data-adv="'+k+'"]',HV.root).forEach(function(el){el.innerHTML=h;});};
  set('chart',advChart(Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t,custom?null:td,false,custom));
  set('expectbox',advExpect(ADV.fine?advAt(c.nearest_t).m:d.m,custom,ADV.fine?null:d.p));set('tablebox',advRows(a,d,ADV.fine));set('tval','t = '+advNum(td,2)+' · '+esc(advZone(td)));
  if(ADV.fine){['theta','dur_b','pg'].forEach(function(k){set('o-'+k,advNum(ADV.fine[k],k==='dur_b'?1:2)+(k==='dur_b'?' '+t('с','s'):''));var i=$('#advf-'+k,HV.root);if(i&&Number(i.value)!==ADV.fine[k])i.value=ADV.fine[k];});set('finewhy',esc(ADV.fineWhy||''));}
  var ap=$('[data-act="advapply"]',HV.root);if(ap)ap.disabled=c.attached&&Math.abs(td-c.slider_t)<0.005;
}
function advInput(el){
  if(el.id==='adv-ack'){var g=$('#adv-ackgo',HV.root),u=xdU();if(g&&u)g.disabled=!u.ackOk(el.value);return true;}
  if(el.id==='adv-t'){ADV.t=Math.round(Number(el.value)*100)/100;advPaint();return true;}
  var k=el.dataset&&el.dataset.advf;if(!k||!ADV.fine)return false;
  var s=ADV_SAFE[k],v=Math.min(s[1],Math.max(s[0],advStep(Number(el.value),s[2])));ADV.fine[k]=v;ADV.fineWhy='';
  // safety in the page as on the router: P(G) never below θ
  if(k==='theta'&&ADV.fine.pg<v){ADV.fine.pg=v;ADV.fineWhy=t('P(G) поднят до θ: возврат не может требовать меньше уверенности, чем уход.','P(G) raised to θ: the return cannot need less confidence than leaving.');}
  if(k==='pg'&&v<ADV.fine.theta){ADV.fine.pg=ADV.fine.theta;ADV.fineWhy=t('P(G) не ниже θ (правило безопасности).','P(G) not below θ (safety rule).');}
  advPaint();return true;
}
function advRpc(p,ok){
  if(HV.busy.adv)return;HV.busy.adv=true;
  return p.then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};toast(ok);ADV.t=null;ADV.fine=null;return refreshNow();})
    .catch(function(e){failModal(t('Не применено','Not applied'),e&&codeOk(e.code)?e.code:'ADVISOR-APPLY-UNCONFIRMED');})
    .finally(function(){HV.busy.adv=false;render();});
}
function advClick(act,a){
  var s=advSt();
  if(act==='advopen'){go(function(){HV.open['sec-adv']=true;if(HV.view==='console')HV.tab='auto';else HV.page='settings';});setHash();return;}
  if(act==='advtour'){advTour(Number(a.dataset.i)||0);return;}
  if(act==='advnotour'){store.set(ADV_TOUR_KEY,'later');render();toast(t('Обучение есть в «Помощь и обучение».','The training is in "Help and training".'));return;}
  if(!s)return;var c=s.current;
  if(act==='advmode'){var m=a.dataset.m;if(m===s.mode)return;return advRpc(rpcCall('advisor_settings',['mode','window'])(m,s.window_days),t('Режим сохранён: ','Mode saved: ')+advModeName(m));}
  if(act==='advwin'){var w=Number(a.dataset.w);if(w===s.window_days)return;return advRpc(rpcCall('advisor_settings',['mode','window'])(s.mode,w),t('Окно данных сохранено. Пересчёт — в течение 10 минут.','Data window saved. Recalculated within 10 minutes.'));}
  if(act==='advrec')return advRpc(rpcCall('advisor_apply')(),t('Совет применён. Роутер подтвердил.','Advice applied. Confirmed by the router.'));
  if(act==='advapply')return advRpc(rpcCall('advisor_apply',['t'])(advDraftT(s)),t('Положение применено. Роутер подтвердил.','Position applied. Confirmed by the router.'));
  if(act==='advrebind')return advRpc(rpcCall('advisor_apply',['t'])(c.nearest_t),t('Значения снова на ползунке.','Values are on the slider again.'));
  if(act==='advreset'){ADV.t=null;render();return;}
  if(act==='advpos'){ADV.t=Number(a.dataset.t);render();return;}
  if(/^adv(lock|fast|turbo)/.test(act)){var u=xdU();if(u)u.act(act,a,s);return;}
  if(act==='advfine'){ADV.fine=ADV.fine?null:{theta:c.theta,dur_b:c.dur_b,pg:c.pg};ADV.fineWhy='';render();return;}
  if(act==='advsave'){var f=ADV.fine;if(!f)return;if(f.pg<f.theta){failModal(t('Не сохранено','Not saved'),'ADVISOR-PG-BELOW-THETA');return;}
    return advRpc(rpcCall('advisor_settings',['mode','window','theta','dur_b','pg'])('manual',s.window_days,f.theta,f.dur_b,f.pg),t('Свои значения сохранены. Роутер подтвердил.','Own values saved. Confirmed by the router.'));}
}

/* ---------- training: 5 steps, offered once, reachable from help ---------- */
function advTour(i){
  store.set(ADV_TOUR_KEY,'seen');
  // the texts live in the optional help module (help<N>.js) like the other training; the curve of step 2 is live
  helpApi().then(function(){xdU().tour(i);}).catch(function(){failModal(t('Обучение','Training'),'UI-HELP-LOAD-FAILED');});
}

/* ---------- recovery time with the honest P95 (rules of scripts/honest_stats.py, analytics_panel.inc.js) ---------- */
function recStatsHTML(){
  var u=xdU();if(!u){xdLoad();return '<p class="small mute">'+(LAZY_HELP.failed?helpFail():t('Загрузка…','Loading…'))+'</p>';}
  var h=V.st.native_history||{},rows=[],s=null,w=null;
  try{rows=retainedTransitions(h).filter(function(r){return !recoveryPreparation(r);});w=recoveryWindow(ADV.per,V.now,h.timezone||'Europe/Berlin');s=recoverySummary(rows,w.start,w.end);}
  catch(e){return '<p class="small mute">'+codeNotice('RECOVERY-TIMEZONE-UNKNOWN')+'</p>';}
  return u.recoveryStats(s);
}

/* ---------- new sensors: WAN diagnosis and server key pins ---------- */
function sensorWan(){
  var w=V.st.wan_diagnosis;
  if(!w||typeof w!=='object')return {lamp:'n',text:t('WAN-диагностика: нет данных (старая служба мониторинга)','WAN diagnosis: no data (older monitoring service)'),code:null};
  if(w.code==='WAN-DOWN')return {lamp:'r',text:t('Нет интернета у провайдера (WAN) — VPN тут ни при чём. Auto не переключает каналы, пока WAN не вернётся','No internet from the provider (WAN) — not a VPN problem. Auto does not switch channels until the WAN is back')+(Number.isFinite(w.down_since)?' · '+t('с ','since ')+fmtTime(w.down_since):''),code:'WAN-DOWN'};
  if(w.code==='WAN-RECOVERING')return {lamp:'y',text:t('Интернет провайдера вернулся; Auto ждёт, пока основной канал подтвердит связь, прежде чем решать','The provider internet is back; Auto waits for the primary channel to confirm before deciding'),code:'WAN-RECOVERING'};
  if(w.enabled===false)return {lamp:'n',text:t('WAN-диагностика выключена (option wan_sensor)','WAN diagnosis is off (option wan_sensor)'),code:null};
  if(codeOk(w.code))return {lamp:'y',text:t('Диагноз: ','Diagnosis: ')+(errorRow(w.code)?t(errorRow(w.code)[3],errorRow(w.code)[2]):w.code)+(Number.isFinite(w.confidence)?' · '+t('уверенность ','confidence ')+Math.round(w.confidence/10)+' %':''),code:w.code};
  return {lamp:'g',text:t('WAN в порядке: интернет провайдера есть','WAN is fine: the provider internet works'),code:null};
}
function sensorKeys(){var k=V.st.server_keys;return k&&typeof k==='object'?k:null;}
function sensorsHTML(){
  var w=sensorWan(),k=sensorKeys(),out='<p class="row small"><i class="lamp '+w.lamp+'"></i><span>'+esc(w.text)+(w.code?' <a class="code" href="#" data-act="code" data-code="'+esc(w.code)+'">'+esc(w.code)+'</a>':'')+'</span></p>';
  if(!k)out+='<p class="row small"><i class="lamp n"></i><span>'+t('Ключи серверов: нет данных','Server keys: no data')+'</span></p>';
  else if(k.mode==='off')out+='<p class="row small"><i class="lamp n"></i><span>'+t('Проверка ключей серверов выключена (server_key_pin off)','Server key check is off (server_key_pin off)')+'</span></p>';
  else{var ch=Array.isArray(k.changed)?k.changed:[];
    out+='<p class="row small"><i class="lamp '+(ch.length?'r':'g')+'"></i><span>'+(ch.length?t('Ключ сервера изменился: ','Server key changed: ')+ch.length:t('Ключи серверов совпадают с запомненными','Server keys match the remembered ones'))+' · '+t('запомнено ','remembered ')+(Number(k.pinned)||0)+' · '+t('режим ','mode ')+esc(k.mode)+(ch.length?' <a class="code" href="#" data-act="code" data-code="SERVER-KEY-CHANGED">SERVER-KEY-CHANGED</a>':'')+'</span></p>';
    ch.forEach(function(r){var p=((HV.inv||{}).profiles||[]).filter(function(x){return x.id===r.profile;})[0];
      out+='<div class="keychg"><b>'+esc(p?profileName(p):r.profile)+'</b> · '+esc(r.host)+(Number.isFinite(r.changed_at)?' · '+esc(fmtTime(r.changed_at,true)):'')+'<dl class="kv small"><dt>'+t('Был','Was')+'</dt><dd class="mono">'+esc(r.pinned)+'</dd><dt>'+t('Сейчас','Now')+'</dt><dd class="mono">'+esc(r.observed)+'</dd></dl><button class="btn sm" data-act="keyaccept" data-profile="'+esc(r.profile)+'" data-observed="'+esc(r.observed)+'">'+t('Принять новый ключ','Accept the new key')+'</button></div>';});}
  return out;
}
function sensorBanner(){
  var w=sensorWan(),k=sensorKeys(),out='';
  if(w.code==='WAN-DOWN'||w.code==='WAN-RECOVERING')out+='<p class="note '+(w.lamp==='r'?'bad':'warn')+' warnbar">'+esc(w.text)+' <a class="code" href="#" data-act="code" data-code="'+w.code+'">'+w.code+'</a></p>';
  if(k&&Array.isArray(k.changed)&&k.changed.length)out+='<p class="note bad warnbar">'+t('Ключ VPN-сервера изменился — проверьте его у провайдера. ','A VPN server key changed — check it with the provider. ')+'<a class="code" href="#" data-act="code" data-code="SERVER-KEY-CHANGED">SERVER-KEY-CHANGED</a> · <a href="#" data-act="gokeys">'+t('подробнее','details')+'</a></p>';
  return out;
}
function keyAccept(a){
  var profile=a.dataset.profile,observed=a.dataset.observed;
  modal({title:t('Принять новый ключ сервера?','Accept the new server key?'),body:'<p>'+t('Сменившийся ключ бывает при ротации ключей провайдером, но так же выглядит подменённый сервер. Принимайте только после сверки с провайдером (список серверов или заново скачанный конфиг).','A changed key happens when the provider rotates keys, but a substituted server looks the same. Accept only after checking it with the provider (server list or a freshly downloaded config).')+'</p><p class="mono small">'+esc(observed)+'</p>',
    buttons:[{t:t('Отмена','Cancel')},{t:t('Ключ сверен — принять','Key checked — accept'),cls:'pri',fn:function(){
      rpcCall('server_key_accept',['profile','observed'])(profile,observed).then(function(r){if(!(r&&r.queued===true))throw {code:r&&r.code};toast(t('Принято. Монитор применит при следующей проверке.','Accepted. The monitor applies it at its next check.'));refreshSoon();})
        .catch(function(e){failModal(t('Ключ не принят','Key not accepted'),e&&codeOk(e.code)?e.code:'SERVER-KEY-NOT-CHANGED');});}}]});
}

/* Views: «Простой» (mockup A), «Пульт» (mockup D) and the first-run wizard (mockup C). Header and footer carry the
   owner attributes on every view; the view switch sits next to the language button. */

/* ---------------- Shared chrome ---------------- */
function viewName(){return HV.view==='console'?t('Пульт','Console'):t('Простой','Simple');}
function brandHTML(){var v=VER();return '<div class="hb"><a class="brand" href="https://homensai.com" target="_blank" rel="noopener noreferrer" title="homensai.com"><span class="logo">HS</span><span class="col" style="gap:0"><b>HomenS<span class="ai">.AI</span> Auto VPN</b><span class="devline" data-b="model">'+esc(v.model)+'</span></span></a></div><div class="bv"><span class="badge-ver hv-version" title="'+t('Версия программы','Program version')+'" data-b="badge">v'+esc(v.app)+'</span></div>';}
function toolsHTML(){
  var vs='<span class="viewsw" role="group" aria-label="'+t('Вид','View')+'"><span class="vlabel">'+t('Вид','View')+'</span>'+[['simple','☰',t('Вид: Простой','View: Simple')],['console','▦',t('Вид: Пульт','View: Console')]].map(function(x){return '<button class="iconbtn" data-act="view" data-v="'+x[0]+'" aria-pressed="'+(HV.view===x[0])+'" title="'+x[2]+'" aria-label="'+x[2]+'">'+x[1]+'</button>';}).join('')+'</span>';
  return vs+'<button class="iconbtn" data-act="lang" title="'+t('Язык','Language')+'" aria-label="'+t('Переключить язык','Switch language')+'">'+(locale==='ru'?'EN':'RU')+'</button><button class="iconbtn" data-act="theme" title="'+t('Тема','Theme')+'" aria-label="'+t('Переключить тему','Switch theme')+'">'+({system:'◐',light:'☀',dark:'☾'}[HV.theme])+'</button>';
}
function footerHTML(){var v=VER();return '<footer class="attr hv-attribution" data-attribution="1"><div class="wrap"><strong>HomenS<span class="ai">.AI</span> Auto VPN</strong><span>'+esc(v.model)+' <span class="tiny">('+(v.detected?t('обнаружено роутером','detected by the router'):t('модель не определена роутером','model not detected by the router'))+')</span></span><a href="https://homensai.com" target="_blank" rel="noopener noreferrer">'+t('Разработчик · Serhii Khomenko','Developer · Serhii Khomenko')+'</a><span data-b="buildline">'+buildLine()+'</span><span>'+esc(v.style)+'</span><span class="copy">© 2026 Serhii Khomenko · HomenS.AI · <a href="https://homensai.com" target="_blank" rel="noopener noreferrer">homensai.com</a></span></div></footer>';}
function buildLine(){var v=VER();return esc(t('Программа','Program')+' '+v.app);}
function noticesHTML(){
  var v=VER(),out='';
  if(v.mismatch)out+='<p class="note warn warnbar">'+t('Версии страницы и роутера различаются: нажмите Ctrl+F5.','The page and router versions differ: press Ctrl+F5.')+' ('+esc(HV_AGENT)+' / '+esc(v.app)+')</p>';
  if(HV.inv.error)out+='<p class="note bad warnbar">'+t('Настройки роутера не прочитаны. Обновите страницу.','Router settings were not read. Reload the page.')+' <a class="code" href="#" data-act="code" data-code="RPC-INVENTORY-UNAVAILABLE">RPC-INVENTORY-UNAVAILABLE</a></p>';
  return out;
}
function readinessBanner(){
  var m=readinessModel(V.st,V.now),bad=(m.checks||[]).filter(function(c){return c.state==='fail';});
  return bad.length?'<p class="note bad warnbar">'+t('Готовность роутера: есть проблемы — ','Router readiness: problems — ')+bad.map(function(c){return '<a class="code" href="#" data-act="code" data-code="'+esc(c.code)+'">'+esc(c.code)+'</a>';}).join(' ')+' · <a href="#" data-act="goready">'+t('подробнее','details')+'</a></p>':'';
}
function chCard(role,opt){opt=opt||{};var k=role==='primary'?'p':'r';
  return '<div class="ch" data-ch="'+role+'" data-b-class="'+k+'.active"><div class="top"><i class="lamp l" data-lamp="'+role+'"></i><div style="flex:1;min-width:0"><div class="role" data-b="'+k+'.role"></div><div class="nm" data-b="'+k+'.name"></div></div><span data-b="'+k+'.tag"></span></div>'+
  '<div class="row" style="margin-top:6px;justify-content:space-between"><div class="ms" data-b="'+k+'.ms"></div><div class="small" style="text-align:right"><div data-b="'+k+'.text"></div><div class="mute tiny" data-b="'+k+'.age"></div></div></div>'+
  (opt.meta===false?'':'<div class="tiny mute" data-b="'+k+'.meta"></div>')+
  '<div class="foot"><span class="tiny mute" data-b="'+k+'.pick"></span><span data-b="'+k+'.sw"></span></div></div>';}
function autoSwitchHTML(sub){return '<button class="aswitch" role="switch" data-act="auto" data-auto-switch aria-label="Auto"><span class="trk"></span>'+(sub===false?'<b data-b="auto.text"></b>':'<span><b data-b="auto.text"></b><br><span class="small mute" data-b="auto.sub"></span></span>')+'</button>';}
function helpSecHTML(sub,extra){return '<details class="sec" data-open="sec-help"'+(HV.open['sec-help']?' open':'')+' data-help-sec><summary><span class="t"><b>'+sub[0]+'</b><span data-help-count data-sub="'+esc(sub[1])+'">'+(helpCount()?helpCount()+' '+t('тем','topics')+' · ':'')+sub[1]+'</span></span></summary><div class="body hlp">'+helpListHTML()+(extra||'')+'</div></details>';}

/* ---------------- Live bindings: every view reads the same snapshot ---------------- */
var LAMP={ov:function(){return overall().lamp;},auto:function(){return autoState().lamp;},primary:function(){return reading('primary').lamp;},reserve:function(){return reading('reserve').lamp;},mon:monLamp};
var B={
  'ov.title':function(){return esc(overall().title);},'ov.sub':function(){return esc(overall().sub);},
  'auto.text':function(){return esc(autoState().text);},'auto.sub':function(){return esc(autoState().sub);},
  'last.short':function(){var e=lastSwitch();return e?esc(fmtTime(e.time)+' · '+evText(e)):t('переходов в сохранённой истории нет','no switches in the retained history');},
  'last.why':function(){var e=lastSwitch();return e?esc(evWhy(e)):'';},
  'last.time':function(){var e=lastSwitch();return e?esc(fmtTime(e.time)):'—';},'last.what':function(){var e=lastSwitch();return e?esc(evText(e)):t('переходов в сохранённой истории нет','no switches in the retained history');},
  'speed':function(){return speedHTML();},'fault':function(){return faultHTML();},'mon.text':function(){return esc(monText());},
  'manual':function(){return manualFeedback();},'check':function(){return checkBtnHTML();},'check.l':function(){return checkBtnHTML().replace('class="btn sm"','class="btn"');},
  'events':function(){return eventsHTML(HV.all?20:5,HV.filters.a,{openFirst:true});},'events20':function(){return eventsHTML(20,HV.filters.d,{openSwitch:true});},
  'tiles':function(){return statsTiles();},'live':function(){return liveLogHTML();},'ready':function(){return readinessHTML();},'banner':function(){return noticesHTML()+readinessBanner()+sensorBanner();},'adv.card':function(){return advCardHTML();},'sensors':function(){return sensorsHTML();},
  'badge':function(){return 'v'+esc(VER().app);},'model':function(){return esc(VER().model);},'buildline':function(){return buildLine();},
  'autochip':function(){return esc(presetName())+' · '+t('уровень','level')+' '+D().level;},
  'autoplain':function(){var d=draftFromInventory();return t('Сейчас Auto проверяет каналы каждые '+(Number(((V.st.probe_policy||{}).effective_interval))||d.interval)+' с. Переключит после '+d.fails+' неудачных проверок подряд, если резерв прошёл '+d.resOk+'. Не больше '+d.attempts+' переключений за '+d.window+' мин.','Auto checks both channels every '+(Number(((V.st.probe_policy||{}).effective_interval))||d.interval)+' s. It switches after '+d.fails+' failed checks in a row if the reserve passed '+d.resOk+'. No more than '+d.attempts+' switches per '+d.window+' min.');}
};
['primary','reserve'].forEach(function(r){var k=r==='primary'?'p':'r';
  B[k+'.name']=function(){return esc(chName(r));};B[k+'.role']=function(){return esc(roleName(r));};
  B[k+'.meta']=function(){var p=roleProfile(r);if(!p)return '';var ep='';try{ep=endpointText(p,V.now)||'';}catch(e){}var c='';try{c=countryName(p)||'';}catch(e){}
    return esc([p.protocol==='wireguard'?'WireGuard':p.protocol==='openvpn'?'OpenVPN':t('протокол: нет данных','protocol: no data'),ep?ep.replace(/^(Server|Сервер): /,''):t('сервер: нет данных','server: no data'),c||t('страна: нет данных','country: no data')].join(' · '));};
  B[k+'.ms']=function(){var x=reading(r);return x.ms==null?'—':x.ms+' <small>'+t('мс','ms')+'</small>';};
  B[k+'.text']=function(){var x=reading(r);return '<span title="'+esc(x.why||'')+'">'+esc(x.text)+'</span>';};B[k+'.age']=function(){return esc(reading(r).ageText);};
  B[k+'.tag']=function(){var s=selectedRole();if(V.d.dataUnavailable||!roleProfile(r))return '';return s===r?'<span class="chip ok">'+t('Трафик здесь','Traffic here')+'</span>':s?'<span class="chip">'+t('Ждёт в резерве','Standing by')+'</span>':'<span class="chip warn">'+t('уточняется','being confirmed')+'</span>';};
  B[k+'.pick']=function(){return V.s.server_pick===true?t('Подбор лучшего сервера: вкл.','Best server pick: on'):'';};
  B[k+'.sw']=function(){var s=selectedRole();if(s===r||!roleProfile(r))return '';var ok=switchAllowed(r)&&!MANUAL_SWITCH_PENDING;return '<button class="btn sm" data-act="switch" data-role="'+r+'"'+(ok?'':' aria-disabled="true" style="opacity:.55"')+'>'+t('Переключить сюда','Switch here')+'</button>';};
  B[k+'.active']=function(){return selectedRole()===r&&!V.d.dataUnavailable?'ch active':'ch';};
  B[k+'.srv']=function(){return selectedRole()===r&&!V.d.dataUnavailable?'card srv active':'card srv';};
});
function paintLive(){
  if(!HV.root)return;V=snap();
  $$('[data-b]',HV.root).forEach(function(el){var f=B[el.dataset.b];if(f){var v;try{v=f();}catch(e){v=esc(NODATA());}if(el.innerHTML!==v)el.innerHTML=v;}});
  $$('[data-b-class]',HV.root).forEach(function(el){var f=B[el.dataset.bClass];if(f){var v=f();if(el.className!==v)el.className=v;}});
  $$('[data-lamp]',HV.root).forEach(function(el){var f=LAMP[el.dataset.lamp];if(!f)return;var c;try{c=f();}catch(e){c='n';}['g','y','r','n'].forEach(function(k){el.classList.toggle(k,k===c);});el.setAttribute('role','img');el.setAttribute('aria-label',{g:t('зелёный','green'),y:t('жёлтый','yellow'),r:t('красный','red'),n:t('серый','grey')}[c]);});
  var on=autoEnabled(V.light),busy=V.op==='starting'||V.op==='stopping'||V.op==='unconfirmed'||V.control.paused;
  $$('[data-auto-switch]',HV.root).forEach(function(el){el.setAttribute('aria-checked',String(!!on));el.classList.toggle('busy',!!busy);el.setAttribute('aria-busy',busy?'true':'false');});
  var probs=eventRows().filter(function(e){return evKind(e).problem&&V.now-e.time<86400;}).length;$$('[data-cnt]',HV.root).forEach(function(n){n.textContent=probs?String(probs):'';n.hidden=!probs;});
  scanFollow();
}

/* ---------------- View «Простой» (mockup A) ---------------- */
function navA(){return '<nav class="topnav" aria-label="'+t('Меню','Menu')+'">'+[['home',t('Главная','Home')],['settings',t('Настройки','Settings')]].map(function(p){return '<button data-act="go" data-p="'+p[0]+'"'+(HV.page===p[0]?' aria-current="page"':'')+'>'+p[1]+'</button>';}).join('')+'<button data-act="helpall" aria-label="'+t('Помощь','Help')+'">?<span class="hl"> '+t('Помощь','Help')+'</span></button></nav>';}
/* F1 «Золотая сетка»: columns 38.2 % / 61.8 %; the status card is a golden rectangle; the channel carrying traffic gets 61.8 % of the pair. */
function homeA(){return '<div data-b="banner"></div>'+
 '<div class="gold"><div class="gcol gl"><section class="card hero" data-g="status" aria-live="polite"><div class="hero-top"><i class="lamp xl" data-lamp="ov"></i><div class="hero-t"><h1 data-b="ov.title" tabindex="-1"></h1><p class="mute" data-b="ov.sub"></p></div></div>'+
  '<div class="hero-act">'+autoSwitchHTML()+'<span data-b="check.l"></span></div></section>'+
  '<section class="card stcard" data-g="stats"><h2>'+t('За 24 часа','Last 24 hours')+'</h2><div data-b="tiles"></div>'+
   '<details class="more" data-open="aLat"'+(HV.open.aLat?' open':'')+'><summary>'+t('График отклика за 6 часов','Response chart, 6 hours')+'</summary><div data-lazy="lat">'+(HV.open.aLat?latencyChart():'')+'</div></details>'+
   '<details class="more" data-open="aSw"'+(HV.open.aSw?' open':'')+'><summary>'+t('Время каждого переключения','Timing of each switch')+'</summary><div data-lazy="sw">'+(HV.open.aSw?switchTimesTable():'')+'</div></details>'+
   '<details class="more" data-open="aTr"'+(HV.open.aTr?' open':'')+'><summary>'+t('Трафик за месяц','Monthly traffic')+'</summary><div data-lazy="tr">'+(HV.open.aTr?trafficChart():'')+'</div></details>'+
   '<details class="more" data-open="aRec"'+(HV.open.aRec?' open':'')+'><summary>'+t('Время восстановления: медиана, P95, максимум','Recovery time: median, P95, maximum')+'</summary><div data-lazy="rec">'+(HV.open.aRec?recStatsHTML():'')+'</div></details></section>'+
  '<section class="card advcard" data-g="advisor" data-b="adv.card"></section></div>'+
 '<div class="gcol gr"><div class="chpair" data-g="channels">'+chCard('primary')+chCard('reserve')+'</div><div data-b="manual"></div>'+
  '<section class="card evcard" data-g="events"><div class="head2"><h2>'+t('События и причины','Events and reasons')+'</h2><span class="tiny mute">'+t('нажмите строку — «почему»','tap a row for "why"')+'</span></div>'+filtersHTML(HV.filters.a,'a')+'<div id="evbox" data-b="events"></div><button class="btn sm ghost" data-act="all">'+(HV.all?t('Свернуть до 5','Collapse to 5'):t('Показать 20 последних','Show last 20'))+'</button></section></div></div>'+
 '<div class="tests"><section class="card"><h3>'+t('Тест скорости','Speed test')+'</h3><div data-b="speed" class="tbox"></div><button class="btn sm" data-act="speed">'+t('Измерить скорость текущего канала','Measure current channel speed')+'</button></section>'+
 '<section class="card"><h3>'+t('Тест сбоя','Failure test')+'</h3><div data-b="fault" class="tbox"></div><button class="btn sm" data-act="fault">'+t('Проверить, что Auto спасёт','Check that Auto rescues')+'</button></section></div>';}
function settingsA(){return '<h1 class="pg-h" tabindex="-1">'+t('Настройки','Settings')+'</h1><p class="mute small">'+t('Всё, что нужно редко. Изменения применяются только после «Сохранить». Сохранение никогда не включает Auto.','Everything you need rarely. Changes apply only after "Save". Saving never turns Auto on.')+'</p>'+
 '<h2 class="grp">'+t('Основное','Main')+'</h2>'+['pair','rules','load','tg','ui'].map(function(id){return secHTML(id);}).join('')+
 '<h2 class="grp">'+t('Для эксперта','Expert')+'</h2>'+['adv','xdet','speed','history','system'].map(function(id){return secHTML(id);}).join('')+
 '<h2 class="grp">'+t('Справка','Reference')+'</h2>'+secHTML('about')+helpSecHTML([t('Помощь и обучение','Help and training'),t('промпты для ИИ · коды · обучение 5 минут','AI prompts · codes · 5-minute training')],'<button class="btn sm" data-act="learn">🎓 '+t('Пройти обучение (5 минут)','Take the training (5 minutes)')+'</button> <button class="btn sm" data-act="advtour" data-i="0">🎓 '+t('Как работает автоподстройка (5 шагов)','How auto-adaptation works (5 steps)')+'</button>');}

/* ---------------- View «Пульт» (mockup D in F1) ---------------- */
var TABS=[['ch','⇄',function(){return t('Каналы','Channels');}],['auto','A',function(){return 'Auto';}],['srv','◎',function(){return t('Серверы','Servers');}],['log','≡',function(){return t('Журнал','Log');}],['sys','⚙',function(){return t('Система','System');}]];
function more(id,title,html){return '<details class="more" data-open="'+id+'"'+(HV.open[id]?' open':'')+'><summary>'+title+'</summary>'+html+'</details>';}
/* Golden grid of a tab: left 38.2 % and right 61.8 % columns; data-o gives the phone order (one column, by importance). */
function goldCols(l,r){return '<div class="gold"><div class="gcol gl">'+l+'</div><div class="gcol gr">'+r+'</div></div>';}
function ordered(n,h){return h.replace(/^<(\w+)/,'<$1 data-o="'+n+'"');}
function tabCh(){
  var last='<section class="card hero" data-o="2" data-g="last"><div class="hline"><i class="lamp l n"></i><h2>'+t('Последний переход','Last switch')+'</h2></div><div><div class="big" data-b="last.time"></div><div class="what" data-b="last.what"></div></div><p class="small mute" data-b="last.why"></p></section>';
  var pair=ordered(1,'<div class="chpair" data-g="channels">'+chCard('primary')+chCard('reserve')+'</div>')+'<div data-b="manual" data-o="1"></div>';
  var mo='<section class="card" data-o="3">'+more('dLat','<b>'+t('График отклика за 6 часов','Response chart, 6 hours')+'</b>','<div data-lazy="lat">'+(HV.open.dLat?latencyChart():'')+'</div>')+more('dPair','<b>'+t('Изменить пару каналов','Change the channel pair')+'</b>','<div data-secid="pair">'+secBody('pair')+'</div>')+'</section>';
  return '<div data-b="banner"></div><div class="panel-h"><h1 tabindex="-1">'+t('Каналы','Channels')+'</h1><span data-b="check"></span></div>'+goldCols(last,pair+mo);}
function tabAuto(){
  var hero='<section class="card hero" data-o="1" data-g="auto"><div class="row" style="justify-content:space-between">'+autoSwitchHTML()+'</div><div><span class="chip acc" data-b="autochip"></span></div><p data-b="autoplain"></p></section>';
  var fault='<section class="card" data-o="4"><h2>'+t('Тест сбоя','Failure test')+'</h2><p class="small mute">'+t('Короткий управляемый сбой канала, который везёт трафик: проверяет, что Auto уйдёт на другой канал и вернётся.','A short controlled failure of the channel carrying traffic: checks that Auto moves to the other channel and back.')+'</p><div data-b="fault" class="tbox"></div><button class="btn sm" data-act="fault">'+t('Запустить тест сбоя','Run failure test')+'</button></section>';
  var stats='<section class="card stcard" data-o="5"><h2>'+t('Как Auto справлялся','How Auto performed')+'</h2><div data-b="tiles"></div>'+more('dSw',t('Время каждого переключения','Timing of each switch'),'<div data-lazy="sw">'+(HV.open.dSw?switchTimesTable():'')+'</div>')+more('dRec',t('Время восстановления: медиана, P95, максимум','Recovery time: median, P95, maximum'),'<div data-lazy="rec">'+(HV.open.dRec?recStatsHTML():'')+'</div>')+'</section>';
  return '<div class="panel-h"><h1 tabindex="-1">Auto</h1></div>'+goldCols(hero+fault,ordered(2,secHTML('adv',{tag:false}))+ordered(3,secHTML('rules',{tag:false}))+ordered(3,secHTML('load',{tag:false}))+ordered(3,secHTML('xdet',{tag:false}))+stats);}
function srvCard(r){var k=r==='primary'?'p':'r';return '<section class="card srv" data-b-class="'+k+'.srv" data-ch="'+r+'"><h2>'+esc(roleName(r))+' · '+esc(chName(r))+'</h2><div class="f"><label for="pk-'+r+'">'+t('Подбирать лучший сервер','Pick the best server')+'</label><input class="tg" type="checkbox" id="pk-'+r+'" data-set="pick"'+(D().pick?' checked':'')+'><div class="h">'+t('Меняет сервер только когда канал простаивает. Один выключатель на оба канала.','Changes the server only while the channel is idle. One switch for both channels.')+'</div></div>'+serversHTML(r)+'</section>';}
function tabSrv(){return '<div class="panel-h"><h1 tabindex="-1">'+t('Серверы','Servers')+'</h1></div><div class="srvpair">'+srvCard('primary')+srvCard('reserve')+'</div>'+
 '<section class="card spd"><div><h2>'+t('Тест скорости','Speed test')+'</h2><div data-b="speed" class="tbox"></div><div class="row"><button class="btn sm" data-act="speed" data-role="primary">'+t('Основной','Primary')+'</button><button class="btn sm" data-act="speed" data-role="reserve">'+t('Резерв','Reserve')+'</button></div></div><div>'+more('dSp',t('Параметры теста скорости','Speed test parameters'),'<div data-secid="speed">'+secBody('speed')+'</div>')+'</div></section>'+
 '<p class="small srvnote"><a href="'+esc(glVpnUrl()||'#')+'" target="_blank" rel="noopener noreferrer" data-act="glvpn">'+t('Добавить или удалить серверы — в панели GL.iNet → VPN ↗','Add or remove servers in the GL.iNet panel → VPN ↗')+'</a></p>';}
function tabLog(){
  var ev='<section class="card evcard" data-o="1">'+filtersHTML(HV.filters.d,'d')+'<div id="evbox" data-b="events20"></div></section>';
  var rail='<section class="card" data-o="2">'+more('dTr','<b>'+t('Трафик за месяц','Monthly traffic')+'</b>','<div data-lazy="tr">'+(HV.open.dTr?trafficChart():'')+'</div>')+more('dLive','<b>'+t('Живой журнал (эксперт)','Live log (expert)')+'</b>','<div data-b="live"></div>')+more('dDec','<b>'+t('Журнал решений: уровни и ускорение','Decision log: levels and boost')+'</b>','<p class="small"><a href="#" data-act="decisions">'+t('Открыть','Open')+'</a></p>')+'</section>';
  return '<div class="panel-h"><h1 tabindex="-1">'+t('Журнал','Log')+'</h1><button class="btn sm" data-act="incident">'+t('Отчёт для печати','Printable report')+'</button></div>'+goldCols(rail,ev);}
function tabSys(){
  var ready='<section class="card" id="ready" data-o="1"><h2>'+t('Готовность роутера','Router readiness')+'</h2><div class="rd" data-b="ready"></div><p class="row small"><i class="lamp" data-lamp="mon"></i><span data-b="mon.text"></span></p><h3 id="sensors">'+t('Датчики: WAN и ключи серверов','Sensors: WAN and server keys')+'</h3><div data-b="sensors"></div>'+monitorExtra()+'</section>';
  var help=ordered(5,helpSecHTML([t('Помощь, коды, обучение','Help, codes, training'),t('коды · промпты для ИИ','codes · AI prompts')],'<h3>'+t('Справочник кодов','Code reference')+'</h3><input type="search" class="inp" data-act="codeq" aria-label="'+t('Код или слово','Code or word')+'" value="'+esc(HV.codeQ)+'" placeholder="'+t('Код или слово…','Code or word…')+'"><div data-codes>'+codesHTML(HV.codeQ)+'</div><div class="row" style="margin-top:8px">'+lanHelperHTML()+'<button class="btn sm" data-act="prompt" data-h="">'+t('Промпт диагностики для ИИ','AI diagnostics prompt')+'</button><button class="btn sm" data-act="learn">🎓 '+t('Обучение','Training')+'</button><button class="btn sm" data-act="advtour" data-i="0">🎓 '+t('Автоподстройка (5 шагов)','Auto-adaptation (5 steps)')+'</button></div>'));
  return '<div class="panel-h"><h1 tabindex="-1">'+t('Система','System')+'</h1></div>'+goldCols(ready,ordered(2,secHTML('tg',{tag:false}))+ordered(3,secHTML('history',{tag:false}))+ordered(4,secHTML('ui',{tag:false}))+help+ordered(6,secHTML('about',{tag:false})));}

/* ---------------- First-run wizard (mockup C, wizard only) ---------------- */
function wizard(){
  var names=[t('Роутер','Router'),t('Каналы','Channels'),t('Поведение','Behaviour'),t('Условия и запуск','Terms and start')],body='',d=D(),step=HV.step,running=step===4&&needsStop();
  if(step===1)body='<h2>'+t('1. Проверяем роутер','1. Checking the router')+'</h2><p class="mute">'+t('Модель и нужные части определяются автоматически. Выбрать модель вручную нельзя — проверки готовности обязательны.','The model and required parts are detected automatically. A model cannot be chosen by hand — readiness checks are mandatory.')+'</p><div data-b="ready"></div>';
  if(step===2){var rows=pairChoices();body='<h2>'+t('2. Выберите два канала','2. Choose two channels')+'</h2><p class="mute">'+t('Найдены VPN-клиенты, настроенные в панели GL.iNet. Основной используется всегда, резерв — при сбое.','VPN clients configured in the GL.iNet panel were found. Primary is used always, reserve on a failure.')+'</p><div class="prof">'+(rows.length?rows.map(function(p){var h=profileHealth(p,V.now).state,dm=channelDelayModel(p,V.st,V.now),ms=dm&&Number.isFinite(dm.rtt_ms)?Math.round(dm.rtt_ms)+' '+t('мс','ms'):'';return '<div><i class="lamp '+(h==='healthy'?'g':h==='failed'?'r':h==='checking'?'y':'n')+'"></i><b style="flex:1">'+esc(profileName(p))+'</b><span class="small mute">'+(p.protocol==='wireguard'?'WireGuard':'OpenVPN')+(ms?' · '+ms:h==='inactive'?' · '+t('отключён в GL.iNet','disabled in GL.iNet'):'')+'</span></div>';}).join(''):'<div><i class="lamp n"></i><b style="flex:1">'+t('Подходящих VPN-клиентов нет','No suitable VPN clients')+'</b></div>')+'</div><div style="margin-top:10px">'+fSel('pairP',t('Основной','Primary'),pairOptions())+fSel('pairR',t('Резерв','Reserve'),pairOptions())+'</div><p class="small"><a href="'+esc(glVpnUrl()||'#')+'" target="_blank" rel="noopener noreferrer" data-act="glvpn">'+t('Нет нужного? Добавьте профиль в GL.iNet → VPN ↗','Missing one? Add a profile in GL.iNet → VPN ↗')+'</a></p>';}
  if(step===3)body='<h2>'+t('3. Как переключать','3. How to switch')+'</h2><p class="mute">'+t('Можно оставить как есть — значения по умолчанию проверены на роутере.','You can keep the defaults — they were verified on a router.')+'</p>'+noSave(secBody('rules'))+'<hr class="sep"><h3>'+t('Нагрузка на роутер','Router load')+'</h3>'+noSave(secBody('load'))+'<hr class="sep"><h3>'+t('Telegram (необязательно)','Telegram (optional)')+'</h3>'+fTog('tg',t('Присылать отчёты о переходах','Send switch reports'))+(d.tg?fTxt('tgToken',t('Токен бота','Bot token'),(HV.inv.settings||{}).telegram_configured?'••••••••':'123456:ABC…','','password'):'')+fTxt('tgChat',t('Получатель','Recipient'),t('@channel или Chat ID','@channel or Chat ID'));
  if(step===4)body='<h2>'+t('4. Условия и запуск','4. Terms and start')+'</h2><dl class="kv" style="margin-bottom:10px"><dt>'+t('Основной','Primary')+'</dt><dd>'+esc(nameOf(d.pairP))+'</dd><dt>'+t('Резерв','Reserve')+'</dt><dd>'+esc(nameOf(d.pairR))+'</dd><dt>'+t('Переключение','Switching')+'</dt><dd>'+esc(presetName())+'</dd><dt>'+t('Нагрузка','Load')+'</dt><dd>'+esc(levelText())+'</dd><dt>Telegram</dt><dd>'+(d.tg?t('вкл.','on'):t('выкл.','off'))+'</dd></dl>'+
    (running?'<p class="note warn" data-wiz-running>'+t('Auto работает — настройки меняются после Stop. Откройте интерфейс; остановить Auto можно там.','Auto is running — settings change after Stop. Open the interface; you can stop Auto there.')+'</p>':(V.terms?'<p class="note">'+t('Условия уже приняты вами (версия '+TERMS_VERSION+').','Terms already accepted by you (version '+TERMS_VERSION+').')+'</p>':'<div class="terms-box">'+termsText()+'</div>'+termsChecks('w'))+
    '<p class="tiny mute">'+t('Auto включится только по кнопке ниже. «Сохранить без запуска» оставит Auto выключенным.','Auto turns on only with the button below. "Save without starting" leaves Auto off.')+'</p>');
  var nav='<div class="nav">'+(step>1?'<button class="btn" data-act="wprev">‹ '+t('Назад','Back')+'</button>':'<span></span>')+(step<4?'<button class="btn pri" data-act="wnext">'+t('Далее','Next')+' ›</button>':running?'<span></span>':'<span class="row"><button class="btn" data-act="wsave">'+t('Сохранить без запуска','Save without starting')+'</button><button class="btn ok" data-act="wstart" id="wstart"'+(V.terms?'':' disabled')+'>'+(V.terms?t('Включить Auto','Turn Auto on'):t('Принять условия и включить Auto','Accept terms and turn Auto on'))+'</button></span>')+'</div>';
  var exit='<div class="wz-exit"><button class="btn" data-act="wskip">'+t('Пропустить — открыть интерфейс','Skip — open the interface')+'</button><p class="tiny mute">'+(onboardingComplete(HV.inv)?t('Мастер закроется без изменений.','The wizard closes without changes.'):t('Настройки останутся текущими или по умолчанию. Auto не включится, условия не будут приняты за вас.','The current or default settings stay. Auto is not started and the terms are not accepted for you.'))+'</p></div>';
  return '<div class="wiz" data-g="wizard"><div class="wz-side"><p class="wz-lead mute">'+t('Первая настройка · около 2 минут','First setup · about 2 minutes')+'</p><ol class="steps">'+names.map(function(n,i){return '<li class="'+(i+1<step?'done':i+1===step?'cur':'')+'">'+(i+1)+' <span>'+n+'</span></li>';}).join('')+'</ol>'+(onboardingComplete(HV.inv)?'<p class="small"><a href="#" data-act="wclose">'+t('Закрыть мастер без изменений','Close the wizard without changes')+'</a></p>':'')+'</div><section class="card wz-main">'+body+nav+exit+'</section></div>';
}
function noSave(h){return h.replace(/<div class="savebar">[\s\S]*?<\/div>/g,'');}
function nameOf(id){var p=((HV.inv||{}).profiles||[]).filter(function(x){return x.id===id;})[0];return p?profileName(p):'—';}
function onboardingDraft(){
  var d=D(),s=HV.inv.settings||{},n=function(v,x){return Number.isFinite(Number(v))&&v!==''&&v!=null?Number(v):x;};
  return {system:{defer_pair:false,source:d.pairP,target:d.pairR,duration:n(s.native_duration,10),session_loss:d.allowDrop===true,servers:serversRows()},
    monitor:{interval:Number(d.interval),checkpoint:n(s.checkpoint,900),probe_limit:Math.min(32,n(s.probe_limit,16)),planning_enabled:s.plan_enabled===true,live_log_limit:n(s.live_log_limit,2000),history_days:n(s.history_days,7)},
    recovery:{failures:Number(d.fails),successes:Number(d.resOk),cooldown:Number(d.cooldown),min_dwell:Number(d.dwell),primary_successes:Number(d.retOk),primary_stable:Number(d.stab),attempt_limit:Number(d.attempts),attempt_window:Number(d.window),rescue_stable:Number(d.rescue),return_policy:d.returnPolicy},
    speed:{enabled:s.speed_enabled===true,auto_new:s.speed_auto_new===true,budget_mib:n(s.speed_budget_mib,8),duration:n(s.speed_duration,5),streams:n(s.speed_streams,2),daily_mib:n(s.speed_daily_mib,128),busy_mbps:n(s.speed_busy_mbps,2)},
    telegram:d.tg||String(d.tgToken||'').trim()?{configure:true,token:String(d.tgToken||'').trim(),chat:tgChatClean(d.tgChat),enabled:d.tg===true,interval:n(s.telegram_interval,60),schedule:s.telegram_schedule==='daily'?'daily':'interval',hour:n(s.telegram_hour,7),weekly:s.telegram_weekly!==false,monthly:s.telegram_monthly!==false,items:s.telegram_items||TG_PRESETS.maximum.join(',')}:{configure:false},
    appearance:{language:locale==='en'?'en':'ru',theme:HV.theme,design:'b',router_model:'auto'}};
}
/* The exit of the wizard (owner 04.11.2026): always there, with Auto running or stopped. It only marks the first run as
   done (rpc setup_onboarding_skip); it never starts Auto or accepts the terms. A refused mark never keeps the person in. */
function wizardSkip(){
  if(HV.busy.wiz)return Promise.resolve(false);
  var leave=function(msg){go(function(){HV.wiz=false;});setHash();if(msg)toast(msg);return true;};
  if(onboardingComplete(HV.inv))return Promise.resolve(leave());
  HV.busy.wiz=true;
  return rpcCall('setup_onboarding_skip')().then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return reloadInventory();})
    .then(function(){snapshotDraft();return leave(t('Интерфейс открыт. Настройки остались как были; Auto не менялся.','The interface is open. Settings stayed as they were; Auto was not changed.'));})
    .catch(function(e){var c=e&&codeOk(e.code)?e.code:'SETUP-SAVE-UNCONFIRMED';return leave(t('Интерфейс открыт, но отметка не сохранилась ('+c+'): мастер может появиться снова.','The interface is open, but the mark was not saved ('+c+'): the wizard may appear again.'));})
    .finally(function(){HV.busy.wiz=false;});
}
/* The wizard opens by itself only on a really unconfigured router: never over a running Auto or an existing pair. */
function wizardNeeded(){
  if(HV.inv.error||onboardingComplete(HV.inv))return false;
  V=snap();var s=HV.inv.settings||{};
  return !(autoOn()||V.d.enabled||(s.plan_source&&s.plan_target)||(s.plan_source_tunnel&&s.plan_target_tunnel));
}
function wizardSave(start){
  if(HV.busy.wiz)return Promise.resolve(false);var d=D();
  if(!d.pairP||!d.pairR||d.pairP===d.pairR){HV.step=2;render();modal({title:t('Нужны два разных канала','Two different channels needed'),body:'<p>'+t('Основной и резерв должны быть разными VPN-клиентами.','Primary and reserve must be different VPN clients.')+'</p>'});return Promise.resolve(false);}
  HV.busy.wiz=true;var p=onboardingDraft();
  return rpcCall('setup_onboarding',['system','monitor','recovery','speed','telegram','appearance'])(p.system,p.monitor,p.recovery,p.speed,p.telegram,p.appearance).then(function(r){
    if(!(r&&r.saved===true&&r.onboarding_complete===true&&r.onboarding_version===1))throw {code:(r&&r.code)||'ONBOARDING-SAVE-FAILED'};
    var s=HV.inv.settings||{};
    if(Number(d.level)!==Number(((HV.st||{}).probe_policy||{}).level)||(d.boost===true)!==(((HV.st||{}).probe_policy||{}).boost_enabled!==false))return rpcCall('setup_probe',['level','boost'])(Number(d.level),d.level<=2?true:d.boost===true).then(function(x){if(!(x&&x.saved===true))throw {code:(x&&x.code)||'PROBE-SETTINGS-FAILED'};});
  }).then(function(){return reloadInventory();}).then(function(){snapshotDraft();return true;})
    .catch(function(e){failModal(t('Настройки не сохранены','Settings not saved'),e&&codeOk(e.code)?e.code:'ONBOARDING-SAVE-UNCONFIRMED');return false;}).finally(function(){HV.busy.wiz=false;});
}

/* ---------------- Render ---------------- */
function render(){
  if(!HV.root)return;V=snap();
  var y=window.pageYOffset||0,focus=document.activeElement&&HV.root.contains(document.activeElement)?document.activeElement.id:null;
  HV.root.className='hvx v-'+(HV.wiz?'wizard':HV.view);
  if(HV.theme==='system')HV.root.removeAttribute('data-theme');else HV.root.setAttribute('data-theme',HV.theme);
  HV.root.setAttribute('lang',locale);
  var hdr='<header class="hdr"><div class="wrap hdr-in">'+brandHTML()+(!HV.wiz&&HV.view==='simple'?navA():'')+'<div class="hdr-tools">'+toolsHTML()+'</div></div></header>',main;
  if(HV.wiz)main='<main><div class="wrap">'+wizard()+'</div></main>';
  else if(HV.view==='console'){var probs='<span class="cnt" data-cnt hidden></span>';
    main='<div class="strip" aria-live="polite"><div class="wrap"><div class="st"><i class="lamp l" data-lamp="ov"></i><div><div class="st-t" data-b="ov.title"></div><div class="st-s" data-b="ov.sub"></div></div></div><div class="st-r">'+autoSwitchHTML()+'</div></div></div>'+
    '<div class="tabbar"><div class="wrap"><nav role="tablist" aria-label="'+t('Разделы','Sections')+'">'+TABS.map(function(x){return '<button role="tab" data-act="tab" data-t="'+x[0]+'" aria-selected="'+(HV.tab===x[0])+'"><span class="ic" aria-hidden="true">'+x[1]+'</span>'+x[2]()+(x[0]==='log'?' '+probs:'')+'</button>';}).join('')+'</nav></div></div>'+
    '<main><div class="wrap" role="tabpanel">'+({ch:tabCh,auto:tabAuto,srv:tabSrv,log:tabLog,sys:tabSys}[HV.tab])()+'</div></main>';}
  else main='<main><div class="wrap">'+(HV.page==='settings'?settingsA():homeA())+'</div></main>';
  HV.root.innerHTML=hdr+main+footerHTML();
  var cs=$$('.wacc',HV.root),b=$('#wstart',HV.root);if(cs.length&&b)cs.forEach(function(c){c.onchange=function(){b.disabled=!cs.every(function(x){return x.checked;});};});
  paintLive();
  if($('[data-help-list]',HV.root)&&HV.open['sec-help'])fillHelpLists();
  if(focus){var f=document.getElementById(focus);if(f)f.focus();}
  window.scrollTo(0,y);
}
function go(fn){$$('.modal-bg',HV.root).forEach(function(m){m.remove();});fn();render();window.scrollTo(0,0);var h=$('h1',HV.root);if(h&&h.focus)try{h.focus({preventScroll:true});}catch(e){}}
function setHash(){try{history.replaceState(null,'',window.location.pathname+window.location.search+'#'+(HV.view==='console'?HV.tab:HV.page));}catch(e){}}

/* ---------------- Events ---------------- */
function onClick(e){var a=e.target.closest('[data-act]');if(!a||!HV.root.contains(a))return;var act=a.dataset.act;
  if(/^adv/.test(act)){e.preventDefault();if(a.disabled||a.getAttribute('aria-disabled')==='true')return;advClick(act,a);return;}
  if(act==='keyaccept'){keyAccept(a);return;}
  if(act==='recper'){ADV.per=a.dataset.p;$$('[data-lazy="rec"]',HV.root).forEach(function(z){if(z.innerHTML)z.innerHTML=recStatsHTML();});return;}
  if(act==='gokeys'){e.preventDefault();go(function(){if(HV.view==='console')HV.tab='sys';else{HV.page='settings';HV.open['sec-system']=true;}});setHash();return;}
  var H={
    lang:function(){locale=locale==='ru'?'en':'ru';store.set(LANG_KEY,locale);render();},
    theme:function(){HV.theme={system:'light',light:'dark',dark:'system'}[HV.theme];store.set(THEME_KEY,HV.theme);D().theme=HV.theme;render();},
    view:function(){HV.view=a.dataset.v==='console'?'console':'simple';store.set(VIEW_KEY,HV.view);go(function(){});setHash();},
    go:function(){go(function(){HV.page=a.dataset.p;});setHash();},tab:function(){go(function(){HV.tab=a.dataset.t;});setHash();},
    helpall:helpModal,gohelp:function(){go(function(){HV.view='simple';HV.page='settings';HV.open['sec-help']=true;});},
    goready:function(){go(function(){if(HV.view==='console')HV.tab='sys';else{HV.page='settings';HV.open['sec-system']=true;}});},
    auto:toggleAuto,switch:function(){switchTo(a.dataset.role);},check:function(){checkNow(a);},speed:function(){speedTest(a.dataset.role);},speedcancel:speedCancel,
    fault:faultTest,stopfault:stopFault,reset:resetStats,all:function(){HV.all=!HV.all;render();},
    evx:function(){var w=a.parentNode.querySelector('.ev-why');w.hidden=!w.hidden;a.setAttribute('aria-expanded',String(!w.hidden));HV.evOpen[a.dataset.k]=!w.hidden;},
    code:function(){e.stopPropagation();showCode(a.dataset.code);},filter:function(){if(a.dataset.id==='a')HV.filters.a=a.dataset.f;else HV.filters.d=a.dataset.f;render();},
    save:function(){saveSection(a.dataset.sec);},discard:function(){discardSection(a.dataset.sec);},
    defaults:function(){Object.assign(D(),{interval:10,fails:3,resOk:2,cooldown:60,dwell:60,attempts:3,window:15,retOk:2,stab:120,rescue:10,returnPolicy:'healthy_primary',preset:'balanced'});HV.dirty.rules=true;render();},
    terms:function(){modal({title:t('Условия использования','Terms of use'),body:'<div class="terms-box">'+termsText()+'</div><p class="small mute">'+(V.terms?t('Вы приняли эти условия. Версия '+TERMS_VERSION+'.','You accepted these terms. Version '+TERMS_VERSION+'.'):t('Условия ещё не приняты. Их предложат при включении Auto.','Terms are not accepted yet. They are offered when Auto is turned on.'))+'</p>'});},
    help:function(){openTopic(a.dataset.h);},prompt:function(){copyPrompt(a.dataset.h);},learn:openLearn,helpretry:function(){fillHelpLists(1);},
    tgtest:tgTest,tgforget:tgForget,glvpn:function(){if(!glVpnUrl()){e.preventDefault();toast(t('Откройте штатную панель GL.iNet → VPN','Open the GL.iNet panel → VPN'));}},
    incident:incidentReport,decisions:decisionsModal,monrestore:restoreMonitor,
    rewiz:function(){go(function(){HV.wiz=true;HV.step=1;snapshotDraft();});},wclose:function(){go(function(){HV.wiz=false;});},
    wnext:function(){if(HV.step===2){var d=D();if(!d.pairP||!d.pairR||d.pairP===d.pairR){modal({title:t('Нужны два разных канала','Two different channels needed'),body:'<p>'+t('Основной и резерв должны быть разными VPN-клиентами.','Primary and reserve must be different VPN clients.')+'</p>'});return;}}HV.step++;render();window.scrollTo(0,0);},
    wprev:function(){HV.step--;render();},
    wskip:function(){wizardSkip();},
    wsave:function(){wizardSave(false).then(function(ok){if(ok){go(function(){HV.wiz=false;});toast(t('Настройки сохранены. Auto выключен.','Settings saved. Auto is off.'));}});},
    wstart:function(){var accepted=V.terms;if(!accepted){var cs=$$('.wacc',HV.root);if(!cs.length||!cs.every(function(c){return c.checked;}))return;}
      wizardSave(true).then(function(ok){if(!ok)return;return (accepted?Promise.resolve():acceptTerms()).then(function(){go(function(){HV.wiz=false;});return refreshNow();}).then(function(){toggleAuto();}).catch(function(){});});}
  };
  if(H[act]){if(a.tagName==='A'&&act!=='glvpn')e.preventDefault();if(a.getAttribute('aria-disabled')==='true'&&act!=='switch')return;H[act]();}
}
function onInput(e){var el=e.target;if(!HV.root.contains(el))return;
  if(advInput(el)||xdInput(el,e))return;
  if(el.matches('[data-act="codeq"]')){HV.codeQ=el.value;var box=el.parentNode.querySelector('[data-codes]');if(box)box.innerHTML=codesHTML(el.value);return;}
  if(!el.dataset||!el.dataset.set)return;var k=el.dataset.set,d=D(),v=el.type==='checkbox'?el.checked:el.value;if(el.type==='number'||el.type==='range'||['level','pingInt','tgHour','diagHours'].indexOf(k)>=0)v=Number(v);
  if(k==='pick'||k==='fast'){d[k]=v;if(e.type==='change')saveImmediate(k,v);return;}
  if(k==='preset'){d.preset=v;var pv=presetValues(v);Object.keys(REC_MAP).forEach(function(x){d[x]=pv[REC_MAP[x]];});d.returnPolicy=pv.return_policy;}
  else{d[k]=v;if(REC_KEYS.indexOf(k)>=0&&k!=='interval')d.preset=presetOf(d);}
  if(k==='theme'){HV.theme=v;store.set(THEME_KEY,v);render();return;}
  if(k==='level'){$$('[data-lvl]',HV.root).forEach(function(l){l.textContent=levelText();});var bx=$('#s-boost',HV.root);if(bx){bx.disabled=v<=2;if(v<=2)bx.checked=true;}}
  var sec=secOf(el)||(el.closest('[data-secid]')||{}).dataset;if(typeof sec==='object')sec=sec&&sec.secid;
  if(!sec&&el.closest('#ready,.more'))sec=el.closest('details.more[data-open="monMore"]')?'monitor':null;
  if(el.closest('details.more[data-open="monMore"]'))sec='monitor';
  if(sec){HV.dirty[sec]=true;$$('[data-dirty="'+sec+'"]',HV.root).forEach(function(x){x.hidden=false;});var sm=$('#sec-'+sec+' summary .t>span',HV.root);if(sm&&SECTIONS[sec])sm.textContent=secSum(sec);}
  if(k==='preset'){$$('input[type=number][data-set]',HV.root).forEach(function(i){if(d[i.dataset.set]!==undefined)i.value=d[i.dataset.set];});$$('select[data-set="returnPolicy"]',HV.root).forEach(function(i){i.value=d.returnPolicy;});}
  if(k==='tgSchedule'||k==='mode'||(k==='tg'&&HV.wiz))render();
}
function onToggle(e){var d=e.target;if(!d.dataset||!d.dataset.open)return;HV.open[d.dataset.open]=d.open;
  if(d.open&&/^sec-(xdet|adv)$/.test(d.dataset.open))xdLoad();
  if(d.open){var z=$('[data-lazy]',d);if(z&&!z.innerHTML)z.innerHTML={lat:latencyChart,sw:switchTimesTable,tr:trafficChart,rec:recStatsHTML}[z.dataset.lazy]();if(d.hasAttribute('data-help-sec'))fillHelpLists();}}
function onKey(e){if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('.ev-h,.codes-tbl tr')){e.preventDefault();e.target.click();}}

/* ---------------- Data: load, poll, refresh ---------------- */
function reloadInventory(){return loadInventory(0).then(function(inv){if(inv&&!inv.error)HV.inv=inv;else HV.inv=Object.assign({},HV.inv,{error:inv&&inv.error||'RPC-INVENTORY-UNAVAILABLE'});return HV.inv;});}
var STATUS_BUSY=null;
function refreshNow(){
  if(STATUS_BUSY)return STATUS_BUSY;
  var current=HV.st;
  STATUS_BUSY=statusCall().then(function(st){HV.st=uiNewestStatus(HV.st,st);},function(){HV.st=uiStatusFailure(current,0);}).then(function(){STATUS_BUSY=null;paintLive();});
  return STATUS_BUSY;
}
/* RU is the default; an explicit ?lang=, then this browser's choice, then the router's saved appearance win. */
function pickLocale(s){var q=null;try{q=new URLSearchParams(window.location.search).get('lang');}catch(e){}var saved=store.get(LANG_KEY,null);return q==='en'||q==='ru'?q:saved==='en'||saved==='ru'?saved:s.appearance_language==='en'?'en':'ru';}
function boot(root,data){
  HV.root=root;HV.inv=data[0]||{};HV.st=data[1]||{rpc_error:'RPC-UNAVAILABLE'};
  locale=pickLocale(HV.inv.settings||{});
  var th=store.get(THEME_KEY,null);HV.theme=['system','light','dark'].indexOf(th)>=0?th:['light','dark'].indexOf((HV.inv.settings||{}).appearance_theme)>=0?(HV.inv.settings||{}).appearance_theme:'system';
  HV.view=store.get(VIEW_KEY,'simple')==='console'?'console':'simple';
  var h=(window.location.hash||'').slice(1);if(['ch','auto','srv','log','sys'].indexOf(h)>=0){HV.view='console';HV.tab=h;}else if(h==='settings'||h==='home'){HV.view='simple';HV.page=h;}
  var wq=null;try{wq=new URLSearchParams(window.location.search).get('wizard');}catch(e){}
  HV.wiz=wizardNeeded()||(!HV.inv.error&&wq==='1');
  HV.refresh=refreshNow;UI_STATUS_REFRESH=function(){refreshNow();};
  root.addEventListener('click',onClick);root.addEventListener('input',onInput);root.addEventListener('change',onInput);root.addEventListener('toggle',onToggle,true);root.addEventListener('keydown',onKey);
  snapshotDraft();render();
  poll.add(function(){if(typeof document!=='undefined'&&document.hidden)return Promise.resolve();return refreshNow();},10);
  setInterval(function(){if(!document.hidden)paintLive();},1000);
  document.addEventListener('visibilitychange',function(){if(!document.hidden)refreshNow();});
}

return {boot:boot,showCode:showCode,render:render,paintLive:paintLive,
  // Test seam (router/tests/test_approved_ui.js): the pure builders and actions, driven without a browser.
  _test:{HV:HV,snap:function(){V=snap();return V;},overall:overall,autoState:autoState,reading:reading,VER:VER,brandHTML:brandHTML,toolsHTML:toolsHTML,footerHTML:footerHTML,
    homeA:homeA,settingsA:settingsA,tabs:{ch:tabCh,auto:tabAuto,srv:tabSrv,log:tabLog,sys:tabSys},wizard:wizard,pickLocale:pickLocale,toggleAuto:toggleAuto,stopAuto:stopAuto,switchTo:switchTo,
    checkNow:checkNow,speedTest:speedTest,faultTest:faultTest,saveSection:saveSection,wizardSave:wizardSave,onClick:onClick,onInput:onInput,codeHint:codeHint,termsModal:termsModal,eventsHTML:eventsHTML,draft:D,setLocale:function(l){locale=l;},
    ADV:ADV,advAt:advAt,advCardHTML:advCardHTML,advSectionBody:advSectionBody,advClick:advClick,advInput:advInput,advTour:advTour,advChart:advChart,
    XD:XD,xdU:xdU,wizardSkip:wizardSkip,wizardNeeded:wizardNeeded,buildLine:buildLine,recStatsHTML:recStatsHTML,sensorsHTML:sensorsHTML,sensorBanner:sensorBanner,keyAccept:keyAccept,evKind:evKind,B:B}};
})();
return view.extend({
  handleSave:null,handleSaveApply:null,handleReset:null,
  load:function(){return Promise.all([loadInventory(0),statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};})]);},
  render:function(data){
    if(typeof document!=='undefined'&&document.head&&!document.querySelector('link[data-hvx-css]'))document.head.appendChild(E('link',{'rel':'stylesheet','data-hvx-css':'1','href':L.resource('view/homensai-vpn/'+HV_STYLESHEET)}));
    var root=E('div',{'class':'hvx','id':'hvx'});HVX.boot(root,data);return root;
  }
});
