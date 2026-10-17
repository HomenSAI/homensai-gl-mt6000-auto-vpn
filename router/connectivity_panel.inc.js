// A queued RPC is never proof of a completed network measurement.
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
function updateConnectivityCheck(status){
  connectivityLatest=status;
  if(!connectivityControl)return;
  var model=connectivityModel(status,connectivityRequest,Date.now()/1000);
  if(connectivityFailure)model={state:'UNAVAILABLE',busy:false};
  var labels={EMPTY:bi('No connected servers were measured','Нет измерений подключённых серверов'),IDLE:bi('Ready to check','Готово к проверке'),QUEUED:bi('Queued','В очереди'),RUNNING:bi('Checking DNS and HTTPS…','Проверяется DNS и HTTPS…'),COMPLETED:bi('Check completed','Проверка завершена'),FAILED:bi('Check failed','Проверка не выполнена'),UNAVAILABLE:bi('Result unavailable; no confirmed measurement','Результат недоступен: нет подтверждённого измерения')};
  connectivityControl.button.disabled=connectivityBusy||model.busy||status.error==='SERVICE-STOPPED';
  connectivityControl.message.textContent=labels[model.state]+(model.time?' · '+new Date(model.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}):'')+(model.checked!=null?' · '+bi('Checked: ','Проверено: ')+model.checked+' · '+bi('Failed: ','С ошибкой: ')+model.failed:'')+(model.code?' · '+model.code:'');
  connectivityControl.message.setAttribute('data-check-state',model.state);
  connectivityControl.button.setAttribute('aria-busy',model.busy?'true':'false');
}
function renderConnectivityCheck(status,refresh){
  var message=E('p',{'role':'status','aria-live':'polite'});
  var button=E('button',{'type':'button','class':'btn hv-primary-action hv-connectivity-action','click':function(){
    if(connectivityBusy||button.disabled)return;
    connectivityBusy=true;connectivityFailure=false;button.disabled=true;message.textContent=bi('Submitting check request…','Отправляется запрос проверки…');
    return scanCall().then(function(result){
      if(!result||result.queued!==true||!/^([a-f0-9]{32})$/.test(result.request_id)||!Number.isFinite(result.requested_at))throw new Error('SCAN-ACK-UNCONFIRMED');
      connectivityRequest={request_id:result.request_id,requested_at:result.requested_at};
      message.textContent=bi('Queued; waiting for a new measurement','В очереди: ожидается новое измерение');
      return refresh();
    }).catch(function(){connectivityFailure=true;message.textContent=bi('Request not confirmed. Retry after checking the monitoring service.','Запрос не подтверждён. Проверьте службу мониторинга перед повтором.');}).finally(function(){connectivityBusy=false;updateConnectivityCheck(connectivityLatest);});
  }},bi('Check VPN connectivity','Проверить доступность VPN'));
  connectivityControl={button:button,message:message};
  var node=E('section',{'class':'hv-connectivity-control'},[button,E('small',{},bi('DNS and HTTPS through connected VPN servers. Not a speed test.','DNS и HTTPS через подключённые VPN-серверы. Это не тест скорости.')),message]);
  updateConnectivityCheck(status);return node;
}
