/* Explicit one-shot manual intent. Queue acknowledgements never select a route or enable Auto. */
var MANUAL_SWITCH_PENDING=false,MANUAL_SWITCH_DIRECTION=null,MANUAL_SWITCH_OPERATION=null,MANUAL_SWITCH_FEEDBACK=null;
var MANUAL_TERMINAL_STATES=['COMPLETED','REFUSED','CANCELLED','UNCONFIRMED'];
function manualClockTick(){return typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();}
function manualOperationModel(status,now){
  var row=status.manual_switch||{},op=MANUAL_SWITCH_OPERATION,valid=!status.rpc_error&&!status.error&&observationFresh(status,now);
  var same=op&&typeof row.request_id==='string'&&(op.request_id?row.request_id===op.request_id:row.request_id!==op.previous&&row.direction===op.direction&&Number.isFinite(row.requested_at)&&row.requested_at>=op.baseline-5);
  // An acknowledged request ID survives router clock corrections; an uncorrelated reply still needs the original time fence.
  var terminal=MANUAL_TERMINAL_STATES.indexOf(row.state)>=0,typedTerminal=terminal&&row.completed===(row.state==='COMPLETED')&&Number.isFinite(row.updated_at)&&row.updated_at>=0&&(op&&op.request_id&&row.request_id===op.request_id||row.updated_at>=(op?op.baseline:0)-5&&row.updated_at<=now+5);
  if(op&&valid&&same&&typedTerminal){
    MANUAL_SWITCH_FEEDBACK=row;MANUAL_SWITCH_OPERATION=op=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;
  }else if(op&&valid&&same){op.request_id=row.request_id;op.acknowledged=true;if(terminal)op.uncertain=true;}
  if(op&&(Number.isFinite(op.tick)?manualClockTick()-op.tick:Date.now()-op.t0)>120000)op.uncertain=true;
  var backendPending=['QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'].indexOf(row.state)>=0;
  return {busy:!!op||backendPending,direction:op?op.direction:backendPending?row.direction:null,
    uncertain:!!(op&&op.uncertain)||backendPending&&(!valid||!manualFresh(row.updated_at,now,90)),request:op||row};
}
function manualFresh(time,now,limit){return Number.isFinite(time)&&now-time>=-5&&now-time<=limit;}
function manualHoldText(){return bi('Channel selected manually and held. Resume Auto restores normal selection; failover protection remains active.','Канал выбран вручную и удерживается. «Возобновить Auto» возвращает обычный автовыбор; защита при отказе сохраняется.');}
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
  var waitText=key==='target'||key==='reserve'?bi('Reserve channel: Alive','Запасной канал: Живой'):bi('Primary channel: Alive','Основной канал: Живой');
  if(!profile)return {color:'grey',text:bi('Not chosen','Не выбран'),carrier:false};
  if(path.moving||path.pending)return {color:'grey',text:path.uncertain?bi('Request not confirmed · waiting for fresh router state','Запрос не подтверждён · ждём актуального состояния роутера'):bi('Switching · waiting for the router','Переключение · ждём роутер'),carrier:false};
  // Owner colour rule: green works in Auto, yellow alive and available for manual switching, grey waiting for the router, red error.
  if(!path.selected&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Connectivity failed','Ошибка доступности'):bi('Tunnel not connected','Туннель не подключён'),carrier:false};
  if(path.code&&!path.selected)return {color:'grey',text:bi('Traffic selection is not verified','Выбор канала трафика не подтверждён')+' · '+path.code,carrier:false};
  if(health==='healthy'&&autoRuns===false)return {color:'yellow',text:waitText,carrier:selected};
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
      'PAIR-MANUAL-BUSY':['A transition or request is already in progress. The Auto power button remains available to stop or cancel startup.','Переключение или запрос уже выполняется. Кнопка Auto остаётся доступной для остановки.']};
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
function manualRecordedResult(status,now){
  var request=status.manual_switch||{};
  if(status.rpc_error||status.error||!observationFresh(status,now)||!manualFresh(request.updated_at,now,300)||request.state!=='COMPLETED'||request.completed!==true||request.code!=='MANUAL-ALREADY-SELECTED')return null;
  return E('p',{'data-manual-result':'already-selected'},[typeof errorCodeLink==='function'?errorCodeLink(request.code):request.code,' · ',bi('Last manual request: the channel was already selected and verified; no additional switch was needed.','Последний ручной запрос: канал уже был выбран и проверен; повторное переключение не потребовалось.')]);
}
function manualFailureResult(status,now){
  var saved=MANUAL_SWITCH_FEEDBACK,current=status.manual_switch||{},row=saved&&(!Number.isFinite(current.updated_at)||current.updated_at<saved.updated_at)?saved:current;
  if(['REFUSED','CANCELLED','UNCONFIRMED'].indexOf(row.state)<0||!manualFresh(row.updated_at,now,300))return null;
  var code=typeof row.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(row.code)?row.code:'MANUAL-REQUEST-UNCONFIRMED';
  var label=row.state==='CANCELLED'?bi('Switch cancelled: ','Переключение отменено: '):row.state==='UNCONFIRMED'?bi('Switch result not confirmed: ','Результат переключения не подтверждён: '):bi('Switch refused: ','Переключение отклонено: ');
  return E('div',{'class':'hv-manual-error','data-manual-diagnostic':'last-request','role':'status'},[E('strong',{},label+code),E('p',{},manualReason([code]))]);
}
function renderManualSwitch(status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=manualControlModel(status,now),buttons=[],labels={},actionMarks={},signals={},settings=(inventory||{}).settings||{},ns=status.native_failover||{},route=status.channel_path||{},profiles=status.profiles||[];
  var source=profiles.filter(function(p){return p.id===(settings.plan_source||route.source_profile_id||ns.source);})[0],target=profiles.filter(function(p){return p.id===(settings.plan_target||route.target_profile_id||ns.target);})[0];
  var selection=manualSelectionModel(status,source,target,now);
  var held=model.mode==='continuous-pair'&&['source','target'].indexOf(model.hold)>=0;
  var pendingDirection=model.busy?model.direction:selection.moving?(ns.state==='RESTORING'||ns.reason==='PAIR-CONNECTING'||ns.reason==='PAIR-WAITING-PROBES'?'primary':'reserve'):null;
  function notice(text){ui.addNotification(null,E('p',{},text));}
  function button(direction,label){
    var resume=direction==='resume',profile=direction==='primary'?source:target,enabled=model[direction].allowed&&(resume?held:!!profile&&!!selection.selected&&selection.selected!==direction&&!selection.code&&!selection.moving&&profileHealth(profile,now).state==='healthy'),n=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-manual-direction':direction,'disabled':enabled?null:'','click':function(){
      var at=typeof statusNow==='function'?statusNow(status):Date.now()/1000,live=manualSelectionModel(status,source,target,at);
      if(MANUAL_SWITCH_PENDING||!enabled||!manualControlModel(status,at)[direction].allowed||!resume&&(!live.selected||live.selected===direction||live.code||live.moving))return;
      var operation={direction:direction,request_id:null,previous:(status.manual_switch||{}).request_id,baseline:Number.isFinite(status.server_time)?status.server_time:(status.manual_switch_control||{}).time||status.time,t0:Date.now(),tick:manualClockTick(),acknowledged:false,uncertain:false};
      MANUAL_SWITCH_OPERATION=operation;MANUAL_SWITCH_FEEDBACK=null;MANUAL_SWITCH_PENDING=true;MANUAL_SWITCH_DIRECTION=direction;
      buttons.forEach(function(node){node.disabled=true;var key=node.hvManualDirection;if(key==='primary'||key==='reserve'){node.setAttribute('class','hv-manual-channel hv-manual-grey');if(labels[key])labels[key].textContent=bi('Waiting for the router','Ждём роутер');if(actionMarks[key])actionMarks[key].textContent=key===direction?bi('Switching…','Переключение…'):bi('Wait','Подождите');if(signals[key])signals[key].setAttribute('data-active','false');}});
      if(typeof uiOperationRefresh==='function')uiOperationRefresh(false);var request;
      try{var call=model.mode==='continuous-pair'?rpc.declare({object:'homensai-vpn',reject:true,method:'pair_manual',params:['direction','control_revision','request_source'],expect:{}}):rpc.declare({object:'homensai-vpn',reject:true,method:'manual_switch',params:['direction','control_revision','request_source'],expect:{}});request=call(direction,model.revision,'manual');}catch(e){request=Promise.reject(e);}
      return Promise.resolve(request).then(function(result){
        if(MANUAL_SWITCH_OPERATION!==operation)return;
        if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id)){operation.request_id=result.request_id;operation.acknowledged=true;}
        else if(result&&result.accepted===false&&result.queued!==true){
          var codes=Array.isArray(result.blockers)?result.blockers.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}):[];
          MANUAL_SWITCH_FEEDBACK={state:'REFUSED',completed:false,updated_at:typeof statusNow==='function'?statusNow(status):Date.now()/1000,code:codes[0]||'MANUAL-REQUEST-UNCONFIRMED'};
          MANUAL_SWITCH_OPERATION=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;notice(manualReason(codes));
        }else operation.uncertain=true;
      }).catch(function(){if(MANUAL_SWITCH_OPERATION===operation)operation.uncertain=true;}).finally(function(){buttons.forEach(function(node){node.disabled=true;});if(typeof uiOperationRefresh==='function')uiOperationRefresh();});
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
    var stale=!!status.rpc_error||!!status.error||!observationFresh(status,now);
    if(stale||selection.code&&health==='healthy')health='unknown';
    var waiting=!pending&&health==='healthy'&&(!autoRuns||!selected);
    var color=waiting?'yellow':health==='failed'||health==='inactive'?'red':pending||!selection.selected||selection.off?'grey':selected&&health==='healthy'?'green':'grey';
    var protocol=profile?(typeof protocolLabel==='function'?protocolLabel(profile):profile.protocol==='wireguard'?'WireGuard':'OpenVPN'):bi('Profile not chosen','Профиль не выбран');
    var healthText=selection.code?bi('Traffic selection is not verified','Выбор канала трафика не подтверждён')+' · '+selection.code:waiting?(direction==='primary'?bi('Primary channel: Alive','Основной канал: Живой'):bi('Reserve channel: Alive','Запасной канал: Живой')):pending?(model.uncertain?bi('Request not confirmed','Запрос не подтверждён'):pendingDirection===direction?bi('Switching','Переключение'):bi('Waiting for the router','Ждём роутер')):!selected?(health==='healthy'?bi('Reserve channel: Alive','Запасной канал: Живой'):bi('Internet channel not in use','Интернет-канал не задействован')):health==='healthy'?(direction==='primary'?bi('Internet: primary channel in use','Интернет: задействован основной канал'):bi('Internet: reserve in use','Интернет: задействован резерв')):health==='failed'?bi('Internet: connection check failed','Интернет: ошибка проверки соединения')+(profile&&profile.code?' · '+profile.code:''):health==='inactive'?bi('Internet: VPN tunnel disconnected','Интернет: VPN-туннель отключён'):bi('Internet: checking the connection','Интернет: выполняется проверка соединения');
    var country=profile&&typeof countryLabel==='function'?countryLabel(profile):null;
    var indicator=E('strong',{'class':'hv-manual-health hv-health-'+health},healthText);labels[direction]=indicator;
    var action=E('b',{'class':'hv-manual-enable'},pending?bi('Wait','Подождите'):selected?bi('In use','Используется'):bi('Switch to this channel','Переключиться на канал'));actionMarks[direction]=action;
    var card=button(direction,[E('small',{},role),E('strong',{'class':'hv-manual-protocol'},protocol),country?E('span',{},country):null,typeof endpointText==='function'?E('small',{},endpointText(profile,now)):null,typeof renderChannelPing==='function'?renderChannelPing(profile,status,now):null,signal(direction,selected&&health==='healthy'&&!pending),indicator,
      action].filter(Boolean));
    card.setAttribute('class','hv-manual-channel hv-manual-'+color);card.setAttribute('aria-pressed',selected?'true':'false');card.setAttribute('data-selected',selected?'true':'false');
    if(selected&&!pending)card.disabled=true;
    if(!selected&&!pending&&card.disabled)action.textContent=bi('Switch unavailable','Переключение недоступно');
    var reason=!selected&&card.disabled?E('p',{'class':'hv-manual-diagnostic','id':'hv-manual-reason-'+direction,'data-manual-diagnostic':direction,'role':'status'},pending?(model.uncertain?bi('The result is not confirmed. Refreshing the router state; Stop remains available.','Результат не подтверждён. Обновляем состояние роутера; Stop остаётся доступен.'):bi('A request is pending. Wait for the router.','Запрос выполняется. Дождитесь ответа роутера.')):selection.code?manualReason([selection.code]):!selection.selected?bi('Channel selection is not verified.','Выбор канала не подтверждён.'):manualReason(model[direction].blockers)):null;
    if(reason)card.setAttribute('aria-describedby','hv-manual-reason-'+direction);
    return E('div',{'class':'hv-manual-choice'},[card,reason].filter(Boolean));
  }
  return E('section',{'class':'hv-chart-card hv-manual-switch','data-manual-controls':'1'},[
    E('h3',{},bi('Manual channel switch','Ручное переключение канала')),
    typeof renderLatencyRecommendation==='function'?renderLatencyRecommendation(status,inventory,'manual'):null,
    E('div',{'class':'hv-manual-channel-grid'},[choice('primary',source,bi('Primary channel','Основной канал')),choice('reserve',target,bi('Reserve channel','Резервный канал'))]),
    held?E('div',{'data-manual-hold':model.hold},[E('p',{},manualHoldText()),button('resume',bi('Resume Auto','Возобновить Auto')),!model.resume.allowed&&!model.busy?E('p',{'role':'status'},manualReason(model.resume.blockers)):null].filter(Boolean)):null,
    manualRecordedResult(status,now),
    E('p',{},bi('Green: works in Auto. Yellow: the channel is alive; see the button for switching availability. Grey: waiting for the router\'s answer. Red: error, does not work.','Зелёный — работает в автомате. Жёлтый — канал живой; доступность переключения указана на кнопке. Серый — ждём ответа роутера. Красный — ошибка, не работает.')),
    false&&!selection.selected&&!selection.moving&&!selection.off?E('p',{'role':'status'},bi('The router has not returned a verified channel selection yet. Updating its policy state; no channel is assumed active from a button press.','Роутер ещё не передал проверенный выбор канала. Обновляем состояние маршрутизации; нажатие кнопки само по себе не означает, что канал выбран.')):null,
    !model.busy?manualFailureResult(status,now):null,
    model.busy?E('p',{'role':'status','data-manual-operation':model.uncertain?'unconfirmed':'pending'},model.uncertain?bi('The switch result is not confirmed. Waiting for a fresh result from the router; you can press Auto to stop.','Результат переключения не подтверждён. Ждём актуальный ответ роутера; можно нажать Auto для остановки.'):bi('A switch request is pending. Wait for confirmation or press the Auto power button to stop.','Запрос переключения ожидает подтверждения. Дождитесь результата или нажмите кнопку Auto для остановки.')):null
  ].filter(Boolean));
}
