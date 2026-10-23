/* Explicit one-shot manual intent. Queue acknowledgements never select a route or enable Auto. */
var MANUAL_SWITCH_PENDING=false;
function manualFresh(time,now,limit){return Number.isFinite(time)&&now-time>=-5&&now-time<=limit;}
function manualConfirmedPath(status,source,target,now){
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90))return neutral;
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
function manualChannelTone(profile,key,path,now){
  var health=profile?profileHealth(profile,now).state:'unknown',selected=path.selected===key;
  if(!profile)return {color:'grey',text:bi('Not chosen','Не выбран'),carrier:false};
  if(path.moving)return {color:'yellow',text:bi('Switching · awaiting confirmation','Переключение · ожидается подтверждение'),carrier:false};
  if(!path.selected&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Connectivity failed','Ошибка доступности'):bi('Tunnel not connected','Туннель не подключён'),carrier:false};
  if(!path.selected||health==='unknown'||health==='checking')return {color:'grey',text:bi('No fresh path confirmation','Нет свежего подтверждения пути'),carrier:false};
  if(selected&&health==='healthy')return {color:'green',text:bi('In use · works','Используется · работает'),carrier:true};
  if(selected)return {color:'red',text:health==='failed'?bi('In use · connectivity failed','Используется · ошибка доступности'):bi('Selected tunnel is not connected','Выбранный туннель не подключён'),carrier:true};
  return {color:'red',text:health==='failed'?bi('Not in use · connectivity failed','Не используется · ошибка доступности'):health==='inactive'?bi('Not in use · not connected','Не используется · не подключён'):bi('Not in use · available','Не используется · доступен'),carrier:false};
}
function manualControlModel(status,now){
  var control=status.manual_switch_control||{},request=status.manual_switch||{},revision=control.control_revision;
  var fresh=!status.rpc_error&&!status.error&&manualFresh(status.time,now,90)&&manualFresh(control.time,now,30);
  var busy=MANUAL_SWITCH_PENDING||(manualFresh(request.updated_at,now,90)&&['QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'].indexOf(request.state)>=0);
  function direction(key){var row=control[key]||{},codes=Array.isArray(row.blockers)?row.blockers:Array.isArray(control.blockers)?control.blockers:[];
    return {allowed:fresh&&!busy&&control.available===true&&row.allowed===true&&typeof revision==='string'&&/^[a-f0-9]{32}$/.test(revision),blockers:codes.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);})};}
  return {fresh:fresh,busy:busy,revision:revision,reserve:direction('reserve'),primary:direction('primary')};
}
function manualReason(codes){
  if(!codes.length)return bi('Manual switching is unavailable until the router confirms that it is ready.','Ручное переключение недоступно, пока роутер не подтвердит готовность.');
  return codes.map(function(code){
    var row=typeof ERROR_EXTRA_ROWS!=='undefined'?ERROR_EXTRA_ROWS.filter(function(item){return item[0]===code;})[0]:null;
    if(row)return bi(row[4],row[5])+(row[6]?' '+bi(row[6],row[7]):'');
    return typeof AUTO_BLOCKERS!=='undefined'&&Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?autoBlockerText(code):bi('Switching is currently unavailable.','Переключение сейчас недоступно.');}).filter(function(text,index,all){return all.indexOf(text)===index;}).join(' ');
}
function renderManualSwitch(status,inventory){
  var model=manualControlModel(status,Date.now()/1000),buttons=[];
  function notice(text){ui.addNotification(null,E('p',{},text));}
  function button(direction,label){
    var enabled=model[direction].allowed,n=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-manual-direction':direction,'disabled':enabled?null:'','click':function(){
      if(MANUAL_SWITCH_PENDING||!enabled||!manualControlModel(status,Date.now()/1000)[direction].allowed)return;
      MANUAL_SWITCH_PENDING=true;buttons.forEach(function(node){node.disabled=true;});var request;
      try{request=rpc.declare({object:'homensai-vpn',reject:true,method:'manual_switch',params:['direction','control_revision'],expect:{}})(direction,model.revision);}catch(e){request=Promise.reject(e);}
      return Promise.resolve(request).then(function(result){
        if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id))notice(bi('Manual switch requested. Wait for the router to confirm the active path. This request does not enable Auto.','Ручное переключение запрошено. Дождитесь подтверждения активного пути роутером. Этот запрос не включает Auto.'));
        else notice(manualReason(result&&Array.isArray(result.blockers)?result.blockers.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}):[]));
      }).catch(function(){notice(bi('The request was not confirmed. Refresh the router state before trying again.','Запрос не подтверждён. Обновите состояние роутера перед повтором.'));}).finally(function(){MANUAL_SWITCH_PENDING=false;buttons.forEach(function(node){node.disabled=true;});});
    }},label);buttons.push(n);return n;
  }
  function choice(direction,label){return E('div',{},[button(direction,label),!model[direction].allowed&&!model.busy?E('p',{'class':'hv-step-note'},manualReason(model[direction].blockers)):null].filter(Boolean));}
  return E('section',{'class':'hv-chart-card hv-manual-switch','data-manual-controls':'1'},[
    E('h3',{},bi('Manual channel switch','Ручное переключение канала')),
    E('p',{},bi('One explicit switch without enabling Auto. Calls and sessions may reconnect. The channel colors change only after fresh router confirmation. Emergency Stop remains available.','Одно явное переключение без включения Auto. Звонки и сессии могут переподключиться. Цвета каналов меняются только после свежего подтверждения роутером. Аварийный стоп остаётся доступен.')),
    E('div',{'class':'hv-wizard-actions'},[choice('reserve',bi('Switch to reserve','Переключить на резерв')),choice('primary',bi('Switch to primary','Переключить на основной'))]),
    model.busy?E('p',{'role':'status'},bi('A switch request is pending. Wait for confirmation or use Emergency Stop.','Запрос переключения ожидает подтверждения. Дождитесь результата или нажмите «Аварийный стоп».')):null
  ].filter(Boolean));
}
