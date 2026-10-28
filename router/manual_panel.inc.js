/* Explicit one-shot manual intent. Queue acknowledgements never select a route or enable Auto. */
var MANUAL_SWITCH_PENDING=false,MANUAL_SWITCH_DIRECTION=null;
function manualFresh(time,now,limit){return Number.isFinite(time)&&now-time>=-5&&now-time<=limit;}
function manualConfirmedPath(status,source,target,now){
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90))return neutral;
  var pairNative=status.native_failover||{};
  if(pairNative.mode==='continuous-pair'&&pairNative.proof_scope==='router-probed-ipv4'&&source&&target&&source.id!==target.id&&pairNative.source===source.id&&pairNative.target===target.id&&manualFresh(pairNative.time,now,30)){
    var moving=['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(pairNative.state)>=0;
    var pairSelected=pairNative.state==='OBSERVING'&&pairNative.readiness_verified===true?'source':['COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE'].indexOf(pairNative.state)>=0?'target':null;
    if(moving)return {source:'checking',target:'checking',direction:'forward',moving:true,selected:null};
    if(pairSelected)return {source:'ready',target:'ready',direction:pairSelected==='target'?'forward':'none',moving:false,selected:pairSelected};
  }
  var route=status.channel_path;
  if(route){
    if(!manualFresh(route.time,now,30)||!source||!target||source.id===target.id||route.source_profile_id!==source.id||route.target_profile_id!==target.id)return neutral;
    if(route.transitioning===true)return {source:'checking',target:'checking',direction:'forward',moving:true,selected:null};
    var selected=route.confirmed===true?(route.active_profile_id===source.id?'source':route.active_profile_id===target.id?'target':null):null;
    return {source:selected?'ready':'neutral',target:selected?'ready':'neutral',direction:selected==='target'?'forward':'none',moving:false,selected:selected};
  }
  // Legacy native confirmation remains usable only with fresh monitor/controller evidence.
  var ns=status.native_failover||{};
  if(!source||!target||ns.source&&ns.source!==source.id||ns.target&&ns.target!==target.id)return neutral;
  var path=autoPathModel(status,source,target,now),model=autoControlModel(status,now);
  if(model.fresh&&model.off&&ns.original_restored===true&&source&&target&&source.id!==target.id)path.selected='source';
  if(model.fresh&&ns.state==='STOPPED-ON-RESERVE'&&source&&target&&source.id!==target.id&&ns.original_restored===false)path.selected='target';
  return path;
}
function manualChannelTone(profile,key,path,now,autoRuns){
  var health=profile?profileHealth(profile,now).state:'unknown',selected=path.selected===key;
  var waitText=key==='target'||key==='reserve'?bi('Reserve channel: alive and waiting to be switched on by Auto','Запасной канал: живой и ожидает включения в режиме автомат'):bi('Primary channel: alive and waiting to be switched on by Auto','Основной канал: живой и ожидает включения в режиме автомат');
  if(!profile)return {color:'grey',text:bi('Not chosen','Не выбран'),carrier:false};
  if(path.moving)return {color:'grey',text:bi('Switching · waiting for the router','Переключение · ждём роутер'),carrier:false};
  // Owner colour rule: green works in Auto, yellow alive and waiting for Auto, grey waiting for the router, red error.
  if(health==='healthy'&&autoRuns===false)return {color:'yellow',text:waitText,carrier:selected};
  if(!path.selected&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Connectivity failed','Ошибка доступности'):bi('Tunnel not connected','Туннель не подключён'),carrier:false};
  if(!path.selected||health==='unknown'||health==='checking')return {color:'grey',text:bi('Waiting for the router\'s answer','Ждём ответа роутера'),carrier:false};
  if(selected&&health==='healthy')return {color:'green',text:bi('Works in Auto · carries your traffic','Работает в автомате · несёт трафик'),carrier:true};
  if(selected)return {color:'red',text:health==='failed'?bi('In use · connectivity failed','Используется · ошибка доступности'):bi('Selected tunnel is not connected','Выбранный туннель не подключён'),carrier:true};
  if(health==='healthy')return {color:'yellow',text:waitText,carrier:false};
  return {color:'red',text:health==='failed'?bi('Not in use · connectivity failed','Не используется · ошибка доступности'):health==='inactive'?bi('Not in use · not connected','Не используется · не подключён'):bi('Not in use · available','Не используется · доступен'),carrier:false};
}
function manualControlModel(status,now){
  var control=status.manual_switch_control||{},request=status.manual_switch||{},revision=control.control_revision;
  var fresh=!status.rpc_error&&!status.error&&manualFresh(status.time,now,90)&&manualFresh(control.time,now,30);
  var busy=MANUAL_SWITCH_PENDING||(manualFresh(request.updated_at,now,90)&&['QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'].indexOf(request.state)>=0);
  function direction(key){var row=control[key]||{},codes=Array.isArray(row.blockers)?row.blockers:Array.isArray(control.blockers)?control.blockers:[];
    return {allowed:fresh&&!busy&&control.available===true&&row.allowed===true&&typeof revision==='string'&&/^[a-f0-9]{32}$/.test(revision),blockers:codes.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);})};}
  return {fresh:fresh,busy:busy,revision:revision,mode:control.mode||'legacy',hold:control.hold||null,reserve:direction('reserve'),primary:direction('primary'),resume:direction('resume')};
}
function manualReason(codes){
  if(!codes.length)return bi('Manual switching is unavailable until the router confirms that it is ready.','Ручное переключение недоступно, пока роутер не подтвердит готовность.');
  return codes.map(function(code){
    var pairNotes={
      'PAIR-MANUAL-COOLDOWN':['Wait for the minimum dwell/cooldown interval before another forward switch.','Дождитесь окончания минимального интервала между переключениями.'],
      'PAIR-RATE-LIMIT':['The configured number of forward attempts has been used for the selected period. Wait; Stop and return remain available.','Достигнут заданный лимит попыток за выбранный период. Подождите; Stop и возврат остаются доступны.'],
      'PAIR-MANUAL-TARGET-UNHEALTHY':['The reserve has no fresh successful DNS/HTTPS confirmation. It will not be selected.','У резерва нет свежего успешного подтверждения DNS/HTTPS. Он не будет выбран.'],
      'PAIR-MANUAL-BUSY':['A transition or request is already in progress. The Auto power button remains available to stop or cancel startup.','Переключение или запрос уже выполняется. Кнопка Auto остаётся доступной для остановки.']};
    if(Object.prototype.hasOwnProperty.call(pairNotes,code))return bi(pairNotes[code][0],pairNotes[code][1]);
    var row=typeof ERROR_EXTRA_ROWS!=='undefined'?ERROR_EXTRA_ROWS.filter(function(item){return item[0]===code;})[0]:null;
    if(row)return bi(row[4],row[5])+(row[6]?' '+bi(row[6],row[7]):'');
    return typeof AUTO_BLOCKERS!=='undefined'&&Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?autoBlockerText(code):bi('Switching is currently unavailable.','Переключение сейчас недоступно.');}).filter(function(text,index,all){return all.indexOf(text)===index;}).join(' ');
}
function manualSelectionModel(status,source,target,now){
  var native=status.native_failover||{};
  if(!status.rpc_error&&manualFresh(status.time,now,90)&&manualFresh(native.time,now,30)&&['STOPPED','DISABLED','EXPIRED'].indexOf(native.state)>=0&&source&&target&&profileHealth(source,now).state==='inactive'&&profileHealth(target,now).state==='inactive')return {selected:null,moving:false,off:true};
  var route=status.channel_path;
  if(route){
    var valid=!status.rpc_error&&!status.error&&manualFresh(status.time,now,90)&&manualFresh(route.time,now,30)&&source&&target&&source.id!==target.id&&route.source_profile_id===source.id&&route.target_profile_id===target.id;
    return {selected:valid&&route.confirmed===true?(route.active_profile_id===source.id?'primary':route.active_profile_id===target.id?'reserve':null):null,moving:valid&&route.transitioning===true};
  }
  var path=manualConfirmedPath(status,source,target,now);
  return {selected:path.selected==='source'?'primary':path.selected==='target'?'reserve':null,moving:path.moving};
}
function renderManualSwitch(status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=manualControlModel(status,now),buttons=[],labels={},actionMarks={},signals={},settings=(inventory||{}).settings||{},ns=status.native_failover||{},route=status.channel_path||{},profiles=status.profiles||[];
  var source=profiles.filter(function(p){return p.id===(settings.plan_source||route.source_profile_id||ns.source);})[0],target=profiles.filter(function(p){return p.id===(settings.plan_target||route.target_profile_id||ns.target);})[0];
  var selection=manualSelectionModel(status,source,target,now);
  var pendingDirection=MANUAL_SWITCH_PENDING?MANUAL_SWITCH_DIRECTION:model.busy?(status.manual_switch||{}).direction:selection.moving?(ns.state==='RESTORING'||ns.reason==='PAIR-CONNECTING'||ns.reason==='PAIR-WAITING-PROBES'?'primary':'reserve'):null;
  function notice(text){ui.addNotification(null,E('p',{},text));}
  function button(direction,label){
    var enabled=model[direction].allowed,n=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-manual-direction':direction,'disabled':enabled?null:'','click':function(){
      if(MANUAL_SWITCH_PENDING||!enabled||!manualControlModel(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000))[direction].allowed)return;
      MANUAL_SWITCH_PENDING=true;MANUAL_SWITCH_DIRECTION=direction;buttons.forEach(function(node){node.disabled=true;var key=node.hvManualDirection;if(key==='primary'||key==='reserve'){node.setAttribute('class','hv-manual-channel hv-manual-'+(key===direction?'yellow':'red'));if(labels[key])labels[key].textContent=key===direction?bi('Switching','Переключение'):'';if(actionMarks[key])actionMarks[key].hidden=true;if(signals[key])signals[key].setAttribute('data-active','false');}});var request;
      try{var call=model.mode==='continuous-pair'?rpc.declare({object:'homensai-vpn',reject:true,method:'pair_manual',params:['direction','control_revision','request_source'],expect:{}}):rpc.declare({object:'homensai-vpn',reject:true,method:'manual_switch',params:['direction','control_revision','request_source'],expect:{}});request=call(direction,model.revision,'manual');}catch(e){request=Promise.reject(e);}
      return Promise.resolve(request).then(function(result){
        if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id))notice(model.mode==='continuous-pair'?bi('Request queued. Wait for confirmed completion. Auto stays on and keeps protecting the selected channel.','Запрос поставлен в очередь. Дождитесь подтверждения. Auto остаётся включённым и продолжает защищать выбранный канал.'):bi('Manual switch requested. Wait for the router to confirm the active path. This request does not enable Auto.','Ручное переключение запрошено. Дождитесь подтверждения активного пути роутером. Этот запрос не включает Auto.'));
        else notice(manualReason(result&&Array.isArray(result.blockers)?result.blockers.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}):[]));
      }).catch(function(){notice(bi('The request was not confirmed. Refresh the router state before trying again.','Запрос не подтверждён. Обновите состояние роутера перед повтором.'));}).finally(function(){MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;buttons.forEach(function(node){node.disabled=true;});});
    }},label);n.hvManualDirection=direction;buttons.push(n);return n;
  }
  function signal(direction,active){
    var icons=[
      '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
      '<rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 18h.01M10 18h.01M17 14V2M2 6a16 16 0 0 1 20 0M5 9a11 11 0 0 1 9-1"/>',
      '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>'
    ];
    var names=[bi('Computer','Компьютер'),bi('Router','Роутер'),bi('VPN server','VPN-сервер')],parts=[];
    icons.forEach(function(paths,index){
      if(index)parts.push(E('span',{'class':'hv-signal-wire','aria-hidden':'true'},[E('i',{}),E('i',{}),E('i',{})]));
      var icon=E('span',{'class':'hv-signal-device','aria-hidden':'true'});
      icon.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+paths+'</svg>';
      parts.push(E('span',{'class':'hv-signal-node'},[icon,E('span',{},names[index])]));
    });
    var diagram=E('span',{'class':'hv-channel-signal','data-active':active?'true':'false','role':'img','aria-label':bi('Computer connected through the router to the VPN server','Компьютер подключён через роутер к VPN-серверу')},parts);
    signals[direction]=diagram;return diagram;
  }
  function choice(direction,profile,role){
    var selected=selection.selected===direction,pending=model.busy||selection.moving;
    var health=profile?profileHealth(profile,now).state:'unknown';
    var autoRuns=typeof autoWorking!=='function'||typeof autoLightModel!=='function'||autoWorking(autoLightModel(status,inventory,now));
    var stale=!!status.rpc_error||!Number.isFinite(status.time)||now-status.time>90||now-status.time< -5;
    if(stale)health='unknown';
    var waiting=!pending&&health==='healthy'&&(!autoRuns||!selected);
    var color=waiting?'yellow':health==='failed'||health==='inactive'?'red':pending||!selection.selected||selection.off?'grey':selected&&health==='healthy'?'green':'grey';
    var protocol=profile?(typeof protocolLabel==='function'?protocolLabel(profile):profile.protocol==='wireguard'?'WireGuard':'OpenVPN'):bi('Profile not chosen','Профиль не выбран');
    var healthText=waiting?(direction==='primary'?bi('Primary channel: alive and waiting to be switched on by Auto','Основной канал: живой и ожидает включения в режиме автомат'):bi('Reserve channel: alive and waiting to be switched on by Auto','Запасной канал: живой и ожидает включения в режиме автомат')):pending?(pendingDirection===direction?bi('Switching','Переключение'):''):!selected?(health==='healthy'?bi('Reserve channel: alive and waiting to be switched on by Auto','Запасной канал: живой и ожидает включения в режиме автомат'):bi('Internet channel not in use','Интернет-канал не задействован')):health==='healthy'?(direction==='primary'?bi('Internet: primary channel in use','Интернет: задействован основной канал'):bi('Internet: reserve in use','Интернет: задействован резерв')):health==='failed'?bi('Internet: connection check failed','Интернет: ошибка проверки соединения')+(profile&&profile.code?' · '+profile.code:''):health==='inactive'?bi('Internet: VPN tunnel disconnected','Интернет: VPN-туннель отключён'):bi('Internet: checking the connection','Интернет: выполняется проверка соединения');
    var country=profile&&typeof countryLabel==='function'?countryLabel(profile):null;
    var indicator=E('strong',{'class':'hv-manual-health hv-health-'+health},healthText);labels[direction]=indicator;
    var action=!selected&&model[direction].allowed&&!pending?E('b',{'class':'hv-manual-enable'},bi('Turn on','Включить')):null;actionMarks[direction]=action;
    var card=button(direction,[E('small',{},role),E('strong',{'class':'hv-manual-protocol'},protocol),country?E('span',{},country):null,typeof endpointText==='function'?E('small',{},endpointText(profile,now)):null,signal(direction,selected&&health==='healthy'&&!pending),indicator,
      action].filter(Boolean));
    card.setAttribute('class','hv-manual-channel hv-manual-'+color);card.setAttribute('aria-pressed',selected?'true':'false');card.setAttribute('data-selected',selected?'true':'false');
    if(selected&&!pending)card.disabled=true;
    var reason=false&&!selected&&!model[direction].allowed&&!pending?E('details',{'class':'hv-manual-diagnostic','data-manual-diagnostic':direction},[E('summary',{},bi('Why this channel is not available','Почему канал недоступен')),E('p',{},manualReason(model[direction].blockers))]):null;
    if(reason&&typeof rememberDisclosure==='function')rememberDisclosure(reason,'manual-'+direction);
    return E('div',{'class':'hv-manual-choice'},[card,reason].filter(Boolean));
  }
  return E('section',{'class':'hv-chart-card hv-manual-switch','data-manual-controls':'1'},[
    E('h3',{},bi('Manual channel switch','Ручное переключение канала')),
    typeof renderLatencyRecommendation==='function'?renderLatencyRecommendation(status,inventory,'manual'):null,
    E('div',{'class':'hv-manual-channel-grid'},[choice('primary',source,bi('Primary channel','Основной канал')),choice('reserve',target,bi('Reserve channel','Резервный канал'))]),
    E('p',{},bi('Green: works in Auto. Yellow: alive and waiting to be switched on by Auto. Grey: waiting for the router\'s answer. Red: error, does not work.','Зелёный — работает в автомате. Жёлтый — живой и ожидает включения в режиме автомат. Серый — ждём ответа роутера. Красный — ошибка, не работает.')),
    false&&!selection.selected&&!selection.moving&&!selection.off?E('p',{'role':'status'},bi('The router has not returned a verified channel selection yet. Updating its policy state; no channel is assumed active from a button press.','Роутер ещё не передал проверенный выбор канала. Обновляем состояние маршрутизации; нажатие кнопки само по себе не означает, что канал выбран.')):null,
    !model.busy&&manualFresh((status.manual_switch||{}).updated_at,now,300)&&['REFUSED','UNCONFIRMED'].indexOf((status.manual_switch||{}).state)>=0?E('details',{'class':'hv-manual-error','data-manual-diagnostic':'last-request'},[E('summary',{'role':'alert'},bi('Switch not completed: ','Переключение не выполнено: ')+((status.manual_switch||{}).code||'MANUAL-SWITCH-UNCONFIRMED')),E('p',{},manualReason([(status.manual_switch||{}).code]))]):null,
    model.busy?E('p',{'role':'status'},bi('A switch request is pending. Wait for confirmation or press the Auto power button to stop.','Запрос переключения ожидает подтверждения. Дождитесь результата или нажмите кнопку Auto для остановки.')):null
  ].filter(Boolean));
}
