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
  var clock=function(seconds){return new Date(seconds*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'});};
  // The idle line shows the latest automatic check, so it always says something true.
  var rows=(status.profiles||[]).filter(function(p){return p.interface;}),working=rows.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';}).length;
  var latest=rows.reduce(function(newest,p){return Number.isFinite(p.time)&&p.time>newest?p.time:newest;},0);
  var summary=function(time,total,ok){return bi('Last check ','Последняя проверка ')+clock(time)+'\n'+ok+' '+bi('of','из')+' '+total+' '+bi('VPNs work','VPN работают');};
  var text;
  if(model.state==='EMPTY')text=bi('No VPN is connected right now, so there was nothing to check.','Сейчас ни один VPN не подключён, проверять нечего.');
  else if(model.state==='COMPLETED'&&model.checked!=null&&model.time)text=summary(model.time,model.checked,model.checked-model.failed);
  else if(model.state==='IDLE')text=rows.length&&latest?summary(latest,rows.length,working):bi('No VPN is connected right now.','Сейчас ни один VPN не подключён.');
  else text={QUEUED:bi('Request sent. Waiting for the router…','Запрос отправлен. Ждём роутер…'),RUNNING:bi('Checking now…','Идёт проверка…'),FAILED:bi('The check could not run. Make sure the monitor is running.','Проверку выполнить не удалось. Убедитесь, что мониторинг запущен.'),UNAVAILABLE:bi('No answer from the router, so no result.','Роутер не ответил, результата нет.')}[model.state]||'';
  connectivityControl.button.disabled=connectivityBusy||model.busy||status.error==='SERVICE-STOPPED';
  connectivityControl.message.textContent=text+(model.code?' · '+model.code:'');
  connectivityControl.message.setAttribute('data-check-state',model.state);
  // One cell per connected VPN: green works, grey does not (or is not checked yet). Then the next step in plain words.
  if(connectivityControl.bar){
    var bar=connectivityControl.bar;while(bar.firstChild)bar.removeChild(bar.firstChild);
    var cells=Math.min(rows.length,16);
    for(var i=0;i<cells;i++)bar.appendChild(E('span',{'class':'hv-check-cell'+(i<working?' hv-check-cell-ok':'')}));
    bar.hidden=!cells;bar.setAttribute('aria-label',working+' '+bi('of','из')+' '+rows.length+' '+bi('VPNs work','VPN работают'));
  }
  if(connectivityControl.next){
    connectivityControl.next.hidden=!rows.length;
    connectivityControl.next.textContent=working?bi('Step 2: turn on Auto with the button in “Automatic VPN failover” below.','Шаг 2: включите Auto кнопкой в блоке «Автоматическое переключение VPN» ниже.'):bi('No VPN works right now. Check the VPN profiles in GL.iNet, then press the button again.','Сейчас ни один VPN не работает. Проверьте VPN-профили в GL.iNet и нажмите кнопку ещё раз.');
  }
  connectivityControl.button.setAttribute('aria-busy',model.busy?'true':'false');
}
function renderConnectivityCheck(status,refresh){
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
  connectivityControl={button:button,message:message,bar:bar,next:next};
  var node=E('section',{'class':'hv-connectivity-control'},[button,E('div',{'class':'hv-check-text'},[E('strong',{},bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас')),E('small',{},bi('First you need to check your VPNs. Press this button: it shows which VPNs give internet right now. The router also repeats this check by itself all the time.','Сначала нужно проверить VPN. Нажмите эту кнопку: она покажет, какие VPN сейчас дают интернет. Роутер и сам постоянно повторяет эту проверку.')),message,bar,next])]);
  updateConnectivityCheck(status);return node;
}
