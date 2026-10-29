// A queued RPC is never proof of a completed network measurement.
var connectivityRequest=null,connectivityBusy=false,connectivityControl=null,connectivityLatest={},connectivityFailure=false;
function connectivityProfiles(status){return (status.profiles||[]).filter(function(p){return p.interface&&p.administrative_state!=='disabled';});}
function connectivityRoleId(rows,settings,role,fallback){
  var anchor=settings['plan_'+role+'_tunnel'];
  if(anchor){var matches=rows.filter(function(p){return p.vendor_tunnel_id===anchor;});return matches.length===1?matches[0].id:null;}
  return settings['plan_'+role]||fallback;
}
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
function updateConnectivityCheck(status){
  connectivityLatest=status;
  if(!connectivityControl)return;
  var model=connectivityModel(status,connectivityRequest,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  if(connectivityFailure)model={state:'UNAVAILABLE',busy:false};
  var clock=function(seconds){return new Date(seconds*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'});};
  // The idle line shows the latest automatic check, so it always says something true.
  var rows=connectivityProfiles(status),working=rows.filter(function(p){return profileHealth(p,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='healthy';}).length;
  var stale=rows.filter(function(p){return profileHealth(p,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='unknown';}).length;
  var latest=rows.reduce(function(newest,p){return Number.isFinite(p.time)&&p.time>newest?p.time:newest;},0);
  var summary=function(time,total,ok){return bi('Last check ','Последняя проверка ')+clock(time)+'\n'+(stale&&!ok?bi('Waiting for fresh router data','Ждём свежие данные роутера'):ok+' '+bi('of','из')+' '+total+' '+bi('VPNs work','VPN работают'));};
  var text;
  if(model.state==='EMPTY')text=bi('No VPN is connected right now, so there was nothing to check.','Сейчас ни один VPN не подключён, проверять нечего.');
  else if(model.state==='COMPLETED'&&model.checked!=null&&model.time)text=latest>=model.time?summary(latest,rows.length,working):model.checked!==rows.length?bi('Channels changed. Check the VPNs again.','Состав каналов изменился. Повторите проверку VPN.'):summary(model.time,model.checked,model.checked-model.failed);
  else if(model.state==='IDLE')text=rows.length&&latest?summary(latest,rows.length,working):bi('No VPN is connected right now.','Сейчас ни один VPN не подключён.');
  else text={QUEUED:bi('Request sent. Waiting for the router…','Запрос отправлен. Ждём роутер…'),RUNNING:bi('Checking now…','Идёт проверка…'),FAILED:bi('The check could not run. Make sure the monitor is running.','Проверку выполнить не удалось. Убедитесь, что мониторинг запущен.'),UNAVAILABLE:bi('No answer from the router, so no result.','Роутер не ответил, результата нет.')}[model.state]||'';
  connectivityControl.button.disabled=connectivityBusy||model.busy||status.error==='SERVICE-STOPPED';
  connectivityControl.message.textContent=text+(model.code?' · '+model.code:'');
  connectivityControl.message.setAttribute('data-check-state',model.state);
  // A cell belongs to a named channel; do not sort healthy cells ahead of failed ones.
  if(connectivityControl.bar){
    var bar=connectivityControl.bar;while(bar.firstChild)bar.removeChild(bar.firstChild);
    var ids=connectivityControl.settings||{},native=status.native_failover||{},path=status.channel_path||{};
    var primary=connectivityRoleId(rows,ids,'source',path.source_profile_id||native.source),reserve=connectivityRoleId(rows,ids,'target',path.target_profile_id||native.target);
    var cells=rows.slice(0,16).map(function(p,index){return {profile:p,label:p.id===primary?bi('Primary channel','Основной канал'):p.id===reserve?bi('Reserve channel','Резервный канал'):bi('VPN channel ','VPN-канал ')+(index+1)};});
    cells.sort(function(a,b){return (a.profile.id===primary?0:a.profile.id===reserve?1:2)-(b.profile.id===primary?0:b.profile.id===reserve?1:2);});
    cells.forEach(function(cell){var healthy=profileHealth(cell.profile,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='healthy';bar.appendChild(E('span',{'class':'hv-check-channel'},[E('small',{},cell.label),E('span',{'class':'hv-check-cell'+(healthy?' hv-check-cell-ok':''),'title':cell.label+' · '+(healthy?bi('Internet available','Интернет доступен'):bi('Internet check not passed','Проверка Интернета не пройдена'))})]));});
    bar.hidden=!cells.length;bar.setAttribute('aria-label',working+' '+bi('of','из')+' '+rows.length+' '+bi('VPNs work','VPN работают'));
  }
  if(connectivityControl.next){
    connectivityControl.next.hidden=!rows.length;
    connectivityControl.next.textContent=!working&&stale?bi('The router data is being refreshed; this is not a VPN failure.','Данные роутера обновляются; это не сбой VPN.'):working?bi('Use the Auto button to control automatic switching.','Управляйте автоматическим переключением кнопкой Auto.'):bi('No VPN works right now. Check the VPN profiles in GL.iNet, then press the button again.','Сейчас ни один VPN не работает. Проверьте VPN-профили в GL.iNet и нажмите кнопку ещё раз.');
  }
  connectivityControl.button.setAttribute('aria-busy',model.busy?'true':'false');
}
function renderConnectivityCheck(status,refresh,inventory){
  var message=E('p',{'role':'status','aria-live':'polite'});
  var button=E('button',{'type':'button','class':'hv-connectivity-action','click':function(){
    if(connectivityBusy||button.disabled)return;
    connectivityBusy=true;connectivityFailure=false;button.disabled=true;message.textContent=bi('Submitting check request…','Отправляется запрос проверки…');
    return scanCall().then(function(result){
      if(!result||result.queued!==true||!/^([a-f0-9]{32})$/.test(result.request_id)||!Number.isFinite(result.requested_at))throw new Error('SCAN-ACK-UNCONFIRMED');
      connectivityRequest={request_id:result.request_id,requested_at:result.requested_at};
      message.textContent=bi('Queued; waiting for a new measurement','В очереди: ожидается новое измерение');
      return refresh();
    }).catch(function(){connectivityFailure=true;message.textContent=bi('Request not confirmed. Retry after checking the monitoring service.','Запрос не подтверждён. Проверьте службу мониторинга перед повтором.');}).finally(function(){connectivityBusy=false;updateConnectivityCheck(connectivityLatest);});
  }},E('span',{'class':'hv-check-icon','aria-hidden':'true'},'↻'));
  button.setAttribute('aria-label',bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас'));button.setAttribute('title',bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас'));
  var bar=E('div',{'class':'hv-check-bar','role':'img'}),next=E('p',{'class':'hv-check-next'});
  connectivityControl={button:button,message:message,bar:bar,next:next,settings:(inventory||{}).settings||{}};
  var node=E('section',{'class':'hv-connectivity-control'},[button,E('div',{'class':'hv-check-text'},[E('strong',{},bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас')),E('small',{},bi('To check the VPNs by hand, press the button.','Для ручной проверки VPN нажмите кнопку.')),message,bar,next])]);
  updateConnectivityCheck(status);return node;
}
