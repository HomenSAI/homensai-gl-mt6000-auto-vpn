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
function errorRow(code){if(typeof ERROR_ROWS==='undefined'||typeof code!=='string')return null;var r=ERROR_ROWS.filter(function(x){return x[0]===code;})[0];if(r)return r;if(!codeOk(code))return null;if(typeof errorFamilyOf==='function'){var f=errorFamilyOf(code);if(f)r=[code].concat(f.slice(1));}return r||null;}
function refreshSoon(){if(HV.refresh)HV.refresh();}

/* ---------------- Terms: the owner accepts them himself ---------------- */
function termsText(){
  var pts=(typeof TERMS_POINTS!=='undefined'?TERMS_POINTS:[]).map(function(p){return '<p><b>'+esc(t(p.h[1],p.h[0]))+'</b> '+esc(t(p.t[1],p.t[0]))+'</p>';}).join('');
  return '<p><b>'+t('HomenS.AI Auto VPN — экспериментальное ПО.','HomenS.AI Auto VPN is experimental software.')+'</b> '+t('Версия условий ','Terms version ')+esc(TERMS_VERSION)+'.</p>'+pts+
    '<details><summary>'+t('Полный текст условий и лицензии','Full terms and licence text')+'</summary><pre class="prewrap">'+esc(t(TERMS_FULL_RU,TERMS_FULL_EN))+'</pre></details>';
}
function termsChecks(prefix){return (typeof TERMS_CHECKS!=='undefined'?TERMS_CHECKS:[]).map(function(c,i){return '<label class="row rowtop10"><input type="checkbox" class="'+prefix+'acc mt4" id="'+prefix+'acc'+i+'"> <span>'+esc(t(c[1],c[0]))+'</span></label>';}).join('');}
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
    buttons:[{t:t('Закрыть','Close'),cls:'ghost'}].concat(V.monitor.maintenance?[]:[{t:t('Восстановить мониторинг','Restore monitoring'),cls:'pri',fn:restoreMonitor}])});
  // owner decision 07.11.2026 15:10: monitoring runs, but with service option enabled=0 the router starts no Auto supervisor
  if(V.monitor.serviceOff)return modal({title:t('Служба Auto выключена','The Auto service is switched off'),body:'<p class="small">'+esc(monitorServiceOffText())+'</p>'+codeNotice('SERVICE-AUTO-OFF'),
    buttons:[{t:t('Закрыть','Close'),cls:'ghost'},{t:t('Включить службу Auto','Switch the Auto service on'),cls:'pri',fn:restoreMonitor}]});
  if(!V.terms)return termsModal(function(){refreshNow().then(function(){autoCommand(false);});});
  autoCommand(false);
}
function stopAuto(){
  var where=selectedRole();
  modal({title:t('Выключить Auto?','Turn Auto off?'),body:'<p>'+(where?t('Трафик останется на текущем канале ('+esc(chName(where))+'). ','Traffic stays on the current channel ('+esc(chName(where))+'). '):'')+t('При сбое автоматического перехода не будет. Включить снова можно в любой момент.','There will be no automatic switch on a failure. You can turn it on again at any time.')+'</p>',
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
  }).catch(function(){if(autoCommandSequence!==command.sequence)return;if(autoCommandPending===command)autoCommandPending=null;command.lost=true;
  }).finally(function(){if(autoCommandSequence!==command.sequence)return;if(stop)autoStopBusy=false;else{autoRequestBusy=false;autoStartPending=false;}var r=refreshNow();if(command.lost)Promise.resolve(r).then(function(){autoLost(command);});});
}
/* F-35 (owner 07.11.2026): no answer to Start/Stop. The state is re-read first: the router took it -> done/waiting; else a Retry button. Never resent by itself. */
function autoLost(c){
  if(autoCommandSequence!==c.sequence)return;V=snap();
  var intent=HV.st.auto_control||{},m=autoControlModel(HV.st,V.now);
  if(m.fresh&&intent.requested_at>c.baseline&&intent.requested===(c.stop?'off':'on')){
    c.acknowledged=true;if(!autoCommandPending)autoCommandPending=c;paintLive();
    toast((c.stop?m.off:m.on)?t('Готово: Auto '+(c.stop?'выключен':'включён')+'. Ответ роутера потерялся, команда не повторялась.','Done: Auto is '+(c.stop?'off':'on')+'. The answer was lost; nothing was sent again.'):t('Роутер получил команду. Ждём подтверждения…','The router received the command. Waiting for confirmation…'));return;}
  modal({title:t('Команда не дошла до роутера','The command did not reach the router'),body:codeNotice('AUTO-CONTROL-FAILED')+'<p class="small">'+(m.fresh?t('Состояние перечитано: ничего не изменилось.','The state was re-read: nothing changed.'):t('Состояние роутера не прочитано.','The router state could not be read.'))+' '+t('Повторно не отправлялось.','Nothing was sent again.')+'</p>',
    buttons:[{t:t('Закрыть','Close'),cls:'ghost'},{t:t('Повторить','Retry'),cls:'pri',fn:function(){autoCommand(c.stop);}}]});
}
function restoreMonitor(){
  if(HV.busy.monitor)return;HV.busy.monitor=true;
  var serviceOn=V.monitor&&V.monitor.serviceOff&&V.monitor.key!=='problem';
  rpcCall('monitor_control',['enabled'])(true).then(function(r){if(r&&r.accepted===true){toast(serviceOn?t('Служба Auto включается… Auto сам не запустится.','The Auto service is switching on… Auto does not start by itself.'):t('Мониторинг запускается…','Monitoring is starting…'));reloadInventory();}else failModal(t('Мониторинг не запущен','Monitoring not started'),codeOk(r&&r.code)?r.code:'MONITOR-UNKNOWN');})
    .catch(function(){failModal(t('Мониторинг не запущен','Monitoring not started'),'MONITOR-RPC-UNCONFIRMED');}).finally(function(){refreshNow().then(function(){HV.busy.monitor=false;paintLive();});});
}

/* ---------------- Manual switch ---------------- */
function switchAllowed(role){
  var p=roleProfile(role),m=V.manual[role],sel=V.sel;
  return !!(!speedPauseNow()&&m&&m.allowed&&p&&sel.selected&&sel.selected!==role&&!sel.code&&!sel.moving&&profileHealth(p,V.now).state==='healthy');
}
function switchTo(role){
  V=snap();if(MANUAL_SWITCH_PENDING)return;
  if(V.sel.selected===role){toast(t('Этот канал уже выбран (MANUAL-ALREADY-SELECTED)','This channel is already selected (MANUAL-ALREADY-SELECTED)'));return;}
  if(!switchAllowed(role)){
    var x=reading(role),m=V.manual[role]||{blockers:[]};
    var why=x.state==='stale'?t('не имеет свежей проверки','has no fresh check'):x.state!=='ok'?t('не прошёл последнюю проверку','failed its last check'):!V.sel.selected?t('роутер ещё не подтвердил, какой канал везёт трафик','the router has not yet confirmed which channel carries traffic'):'';
    var sp=speedPauseNow();
    modal({title:t('Переключение сейчас недоступно','Switching unavailable now'),body:(sp?'<p>'+t('Идёт тест скорости: Auto и мониторинг на паузе. Переключиться можно после его окончания (SPEED-BUSY).','A speed test is running: Auto and monitoring are paused. You can switch when it ends (SPEED-BUSY).')+'</p>':'')+(why&&!sp?'<p>'+t('Канал «'+esc(chName(role))+'» '+why+'.','Channel "'+esc(chName(role))+'" '+why+'.')+'</p>':'')+'<p class="small">'+esc(manualReason(m.blockers||[]))+'</p><p class="small mute">'+t('Нажмите «Проверить сейчас» и попробуйте снова.','Press "Check now" and try again.')+'</p>'});return;
  }
  modal({title:t('Переключить на «'+esc(chName(role))+'»?','Switch to "'+esc(chName(role))+'"?'),
    body:'<p>'+t('Звонки и загрузки могут коротко прерваться (обычно 1–4 с).','Calls and downloads may drop briefly (usually 1–4 s).')+'</p>'+(autoOn()?'<p class="small mute">'+t('Auto продолжит следить. Если этот канал откажет, Auto переключит по правилам.','Auto keeps watching. If this channel fails, Auto switches by the rules.')+'</p>':''),
    buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Переключить','Switch'),cls:'pri',fn:function(){manualRequest(role);}}]});
}
function manualClientId(){
  var bytes=[],i,c=typeof crypto!=='undefined'&&crypto&&typeof crypto.getRandomValues==='function'?crypto:null;
  if(c){var a=new Uint8Array(16);c.getRandomValues(a);for(i=0;i<16;i++)bytes.push(a[i]);}
  else for(i=0;i<16;i++)bytes.push(Math.floor(Math.random()*256));
  return bytes.map(function(b){return (b<16?'0':'')+b.toString(16);}).join('');
}
function manualRequest(direction,retryId){
  V=snap();var st=HV.st,model=V.manual;
  if(MANUAL_SWITCH_PENDING||!switchAllowed(direction))return;
  var operation={direction:direction,request_id:null,previous:(st.manual_switch||{}).request_id,baseline:Number.isFinite(st.server_time)?st.server_time:(st.manual_switch_control||{}).time||st.time,t0:Date.now(),tick:manualClockTick(),acknowledged:false,uncertain:false};
  MANUAL_SWITCH_OPERATION=operation;MANUAL_SWITCH_FEEDBACK=null;MANUAL_SWITCH_PENDING=true;MANUAL_SWITCH_DIRECTION=direction;paintLive();
  // F-35: one fresh id per click. A lost answer is never resent by itself (owner 07.11.2026): the page re-reads the state
  // (manualLost); only the owner's Retry sends again, with the SAME id, so the router replays instead of switching twice.
  var pairMode=model.mode==='continuous-pair',clientId=pairMode?retryId||manualClientId():null;
  var call=pairMode?rpcCall('pair_manual',['direction','control_revision','request_source','client_request_id']):rpcCall('manual_switch',['direction','control_revision','request_source']);
  function send(){try{return Promise.resolve(pairMode?call(direction,model.revision,'manual',clientId):call(direction,model.revision,'manual'));}catch(e){return Promise.reject(e);}}
  send().then(function(result){
    if(MANUAL_SWITCH_OPERATION!==operation)return;
    if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id)){operation.request_id=result.request_id;operation.acknowledged=true;toast(t('Запрос принят. Роутер переключает канал…','Request accepted. The router is switching…'));}
    else if(result&&result.accepted===false&&result.queued!==true){
      var codes=Array.isArray(result.blockers)?result.blockers.filter(codeOk):[],running=['PAIR-MANUAL-BUSY','TRANSACTION-IN-PROGRESS'].indexOf(codes[0])>=0;
      MANUAL_SWITCH_FEEDBACK=running?null:{state:'REFUSED',completed:false,updated_at:statusNow(st),code:codes[0]||'MANUAL-REQUEST-UNCONFIRMED'};
      MANUAL_SWITCH_OPERATION=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;
      // BH-07: a replayed refusal is the router's earlier answer to this same click; a new click (fresh id) decides afresh
      if(result.replayed===true&&!running)modal({title:t('Прежний ответ на это нажатие','Earlier answer to this click'),body:(codes[0]?codeNotice(codes[0]):'')+'<p class="small">'+esc(manualReason(codes))+' '+t('Роутер уже отклонил это нажатие раньше; новое нажатие проверит всё заново.','The router refused this click earlier; a new click checks everything again.')+'</p>',
        buttons:[{t:t('Закрыть','Close'),cls:'ghost'},{t:t('Нажать заново','Click again'),cls:'pri',fn:function(){MANUAL_SWITCH_FEEDBACK=null;manualRequest(direction);}}]});
      else modal({title:running?t('Повторно не отправлено','Not sent again'):t('Переключение отклонено','Switch refused'),body:(codes[0]?codeNotice(codes[0]):'')+'<p class="small">'+esc(running?t('Операция уже выполняется.','An operation is already running.'):manualReason(codes))+'</p>'});
    }else operation.uncertain=true;
    return refreshNow();
  },function(){if(MANUAL_SWITCH_OPERATION!==operation)return;operation.uncertain=true;return Promise.resolve(refreshNow()).then(function(){manualLost(operation,clientId);});});
}
function manualLost(op,clientId){
  if(MANUAL_SWITCH_OPERATION!==op)return;V=snap();
  var st=V.st,row=st.manual_switch||{},fresh=!st.rpc_error&&observationFresh(st,V.now);
  var seen=fresh&&typeof row.request_id==='string'&&row.request_id!==op.previous&&row.direction===op.direction&&Number.isFinite(row.requested_at)&&row.requested_at>=op.baseline-5;
  if(fresh&&V.sel.selected===op.direction&&!(seen&&MANUAL_TERMINAL_STATES.indexOf(row.state)<0)){
    MANUAL_SWITCH_OPERATION=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;paintLive();
    toast(t('Готово: трафик на канале «'+chName(op.direction)+'». Ответ роутера потерялся, команда не повторялась.','Done: traffic is on "'+chName(op.direction)+'". The answer was lost; nothing was sent again.'));return;}
  if(seen){op.request_id=row.request_id;op.acknowledged=true;op.uncertain=false;paintLive();toast(t('Роутер получил запрос и переключает канал…','The router received the request and is switching…'));return;}
  MANUAL_SWITCH_OPERATION=null;MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;
  MANUAL_SWITCH_FEEDBACK={state:'LOST',direction:op.direction,client:clientId,code:'MANUAL-REQUEST-UNCONFIRMED',completed:false};paintLive();
  modal({title:t('Ответ роутера не получен','No answer from the router'),body:codeNotice('MANUAL-REQUEST-UNCONFIRMED')+'<p class="small">'+(fresh?t('Состояние перечитано: переключения не было.','The state was re-read: no switch happened.'):t('Состояние роутера не прочитано.','The router state could not be read.'))+' '+t('Повторно не отправлялось.','Nothing was sent again.')+'</p>',
    buttons:[{t:t('Закрыть','Close'),cls:'ghost'},{t:t('Повторить','Retry'),cls:'pri',fn:manualRetry}]});
}
/* the owner's Retry after a lost answer: the same request id (the router replays a request it already has) */
function manualRetry(){var f=MANUAL_SWITCH_FEEDBACK;if(!f||f.state!=='LOST')return;V=snap();if(!switchAllowed(f.direction))return switchTo(f.direction);MANUAL_SWITCH_FEEDBACK=null;manualRequest(f.direction,f.client);}
function manualFeedback(){
  var now=V.now,row=V.st.manual_switch||{},lost=MANUAL_SWITCH_FEEDBACK&&MANUAL_SWITCH_FEEDBACK.state==='LOST'?MANUAL_SWITCH_FEEDBACK:null;
  if(lost&&V.sel.selected===lost.direction)MANUAL_SWITCH_FEEDBACK=lost=null;  // it took effect after all
  if(lost)return '<p class="note warn small mt10">'+t('Ответ роутера не получен, переключения не было: ','No answer from the router, no switch happened: ')+'<a class="code" href="#" data-act="code" data-code="MANUAL-REQUEST-UNCONFIRMED">MANUAL-REQUEST-UNCONFIRMED</a> <button class="btn sm" data-act="manualretry">'+t('Повторить','Retry')+'</button></p>';
  var fail=MANUAL_SWITCH_FEEDBACK&&['REFUSED','CANCELLED','UNCONFIRMED'].indexOf(MANUAL_SWITCH_FEEDBACK.state)>=0?MANUAL_SWITCH_FEEDBACK:null;
  if(!fail&&['REFUSED','CANCELLED','UNCONFIRMED'].indexOf(row.state)>=0&&row.completed===false&&manualResultFresh(row,now))fail=row;
  if(fail){var code=codeOk(fail.code)?fail.code:'MANUAL-REQUEST-UNCONFIRMED';return '<p class="note warn small mt10">'+(fail.state==='CANCELLED'?t('Переключение отменено: ','Switch cancelled: '):fail.state==='UNCONFIRMED'?t('Результат переключения не подтверждён: ','Switch result not confirmed: '):t('Переключение отклонено: ','Switch refused: '))+'<a class="code" href="#" data-act="code" data-code="'+esc(code)+'">'+esc(code)+'</a> '+esc(manualReason([code]))+'</p>';}
  var op=manualOperationModel(V.st,now);
  if(op.busy)return '<p class="note small mt10">'+t('Переключение: ','Switching: ')+esc(uiOperationTimerText(V.st,now)||t('ждём роутер','waiting for the router'))+(op.uncertain?' · '+t('результат пока не подтверждён','result not confirmed yet'):'')+'</p>';
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
  if(speedPauseNow())return failModal(t('Тест скорости уже идёт','A speed test is already running'),'SPEED-BUSY',t('запущен из другой сессии или роутером; кнопка «Остановить» отменит его','started from another session or by the router; the Stop button cancels it'));
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
function speedCancel(){if(HV.busy.speedCancel)return;HV.busy.speedCancel=true;rpcCall('speed_cancel')().then(function(r){toast(r&&r.queued?t('Отмена запрошена.','Cancel requested.'):t('Тест не идёт.','No test is running.'));}).catch(function(){failModal(t('Отмена не подтверждена','Cancel not confirmed'),'SPEED-CANCEL-UNVERIFIED');}).finally(function(){refreshNow().then(function(){HV.busy.speedCancel=false;paintLive();});});}
function speedHTML(){
  var run=HV.speedRun;
  if(run){var d=run.snap,row=d&&d.profiles.filter(function(x){return x.id===run.id;})[0],ph=row?row.phase:'waiting';
    var phase={waiting:t('Auto ставится на паузу…','Pausing Auto…'),resolving:t('Подготовка…','Preparing…'),latency:t('Отклик: измеряем…','Latency: measuring…'),download:t('Загрузка: измеряем…','Download: measuring…'),upload:t('Отдача: измеряем…','Upload: measuring…'),done:t('Завершение, Auto продолжает…','Finishing, Auto resumes…')}[ph]||ph;
    var pct=Math.min(95,Math.round((Date.now()-run.t0)/1000/(run.dur*2+8)*100));
    return '<div class="small">'+esc(phase)+' <button class="btn sm ghost" data-act="speedcancel">'+t('Остановить','Stop')+'</button></div><div class="prog"><i data-pct="'+pct+'"></i></div>';}
  var pause=speedPauseNow();
  if(pause){var word={PAUSING:t('Auto и мониторинг ставятся на паузу…','Pausing Auto and monitoring…'),PAUSED:t('Тест идёт, Auto и мониторинг на паузе','The test is running; Auto and monitoring are paused'),RESUMING:t('Тест завершён, Auto и мониторинг возобновляются…','The test has finished; Auto and monitoring are resuming…')}[pause.phase]||t('Тест скорости идёт','A speed test is running');
    return '<div class="small">'+esc(word)+' <span class="mute">('+t('запущен из другой сессии или роутером','started from another session or by the router')+')</span> <button class="btn sm ghost" data-act="speedcancel">'+t('Остановить','Stop')+'</button></div>';}
  var res=((V.st.speed_tests||{}).results||[]).filter(function(x){return x&&Number.isFinite(x.time);}).sort(function(a,b){return b.time-a.time;})[0];
  if(!res)return '<span class="mute small">'+t('Тест ещё не запускали. Тест расходует трафик, Auto на это время ставится на паузу.','No test yet. A test uses traffic; Auto pauses during it.')+'</span>';
  var down=res.download&&Number.isFinite(res.download.mbps)?Math.round(res.download.mbps):'—',up=res.upload&&Number.isFinite(res.upload.mbps)?Math.round(res.upload.mbps):'—';
  var who=V.src&&res.id===V.src.id?roleName('primary'):V.tgt&&res.id===V.tgt.id?roleName('reserve'):(res.name||res.id);
  if(codeOk(res.code)&&down==='—')return '<span class="small">'+t('Последний тест ','Last test ')+fmtTime(res.time)+': <a class="code" href="#" data-act="code" data-code="'+esc(res.code)+'">'+esc(res.code)+'</a></span>';
  return '<div><b class="fs125">'+down+' / '+up+'</b> '+t('Мбит/с (загрузка / отдача)','Mbit/s (down / up)')+' · '+esc(who)+'<div class="tiny mute">'+fmtTime(res.time)+'</div></div>';
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
      V=snap();if(HV.busy.fault||faultActive())return;  // the window may have been open while another press or session started a test
      var dur=Number(($('#fdur',bg)||{}).value)||150,now=faultCurrentBinding(HV.st,HV.inv);
      if(!now.ready||!now.source||now.source.id!==b.source.id||now.certificate!==b.certificate)return failModal(t('Тест не запущен','Test not started'),'FAULT-NOT-CURRENT-SOURCE',t('VPN изменился, пока окно было открыто','the VPN changed while this window was open'));
      HV.busy.fault=true;rpcCall('fault_start',['profile','scope','duration'])(now.source.id,'channel',dur).then(function(r){if(r&&codeOk(r.code)&&r.code!=='FAULT-ACTIVE')failModal(t('Тест сбоя','Failure test'),r.code);else toast(t('Тест сбоя запущен','Failure test started'));})
        .catch(function(){failModal(t('Тест сбоя','Failure test'),'FAULT-RPC-UNCONFIRMED');}).finally(function(){refreshNow().then(function(){HV.busy.fault=false;paintLive();});});
    }}]});
}
function stopFault(){if(HV.busy.faultStop)return;HV.busy.faultStop=true;rpcCall('fault_cancel')().then(function(r){toast(codeOk(r&&r.code)?r.code:t('Запрос отправлен','Request sent'));}).catch(function(){failModal(t('Тест сбоя','Failure test'),'FAULT-CANCEL-UNKNOWN');}).finally(function(){refreshNow().then(function(){HV.busy.faultStop=false;});});}
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
  return '<ul class="evl" data-help-list>'+topics.map(function(h){return '<li class="row sbnw"><a href="#" data-act="help" data-h="'+esc(h.id)+'">'+esc(t(h.title[1],h.title[0]))+'</a>'+(h.id!=='diagnose-all'&&h.id!=='ai-prompt'&&h.id!=='ai-lan-prompt'?'<button class="btn sm ghost" data-act="prompt" data-h="'+esc(h.id)+'" title="'+t('Скопировать промпт для ИИ-помощника','Copy a prompt for an AI assistant')+'">'+t('Промпт для ИИ','AI prompt')+'</button>':'')+'</li>';}).join('')+'</ul>';
}
function helpCount(){return LAZY_HELP.api?LAZY_HELP.api.helpTopics().length:null;}
function fillHelpLists(r){helpApi(r).catch(function(){}).then(function(){$$('[data-help-list]',HV.root).forEach(function(n){n.outerHTML=helpListHTML();});$$('[data-cb]',HV.root).forEach(function(n){n.outerHTML=codeBody(n.dataset.cb);});$$('[data-help-count]',HV.root).forEach(function(n){var c=helpCount();if(c)n.textContent=c+' '+t('тем','topics')+' · '+n.getAttribute('data-sub');});refreshCodePanels();if(r&&LAZY_HELP.api&&!$('.modal-bg',HV.root))render();});}
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
  return LAZY_HELP.api&&LAZY_HELP.api.codeCatalogueHTML?LAZY_HELP.api.codeCatalogueHTML(ERROR_ROWS,q,HV.codePage||0,locale):'<p role="status">'+(LAZY_HELP.failed?helpFail():t('Загрузка справочника…','Loading the code reference…'))+'</p>';
}
function codesPanelHTML(){return '<div data-code-panel>'+(LAZY_HELP.api&&LAZY_HELP.api.codeCataloguePanel?LAZY_HELP.api.codeCataloguePanel(ERROR_ROWS,HV.codeQ,HV.codePage||0,locale):codesHTML(HV.codeQ))+'</div>';}
function refreshCodePanels(){
  $$('[data-code-panel]',HV.root).forEach(function(p){var input=$('[data-act="codeq"]',p);
    if(!input&&LAZY_HELP.api&&LAZY_HELP.api.codeCataloguePanel){p.innerHTML=LAZY_HELP.api.codeCataloguePanel(ERROR_ROWS,HV.codeQ,HV.codePage||0,locale);return;}
    var box=$('[data-codes]',p);if(box)box.innerHTML=codesHTML(HV.codeQ);if(input&&input.value!==HV.codeQ)input.value=HV.codeQ;
  });
}
function moveCodes(value,node){var panel=node.closest('[data-code-panel]');HV.codePage=value==='all'?'all':Math.max(0,Number(value)||0);refreshCodePanels();var count=panel&&$('[data-code-count]',panel);if(count)count.focus();}
function codeBody(code){return LAZY_HELP.api&&LAZY_HELP.api.codeBody?LAZY_HELP.api.codeBody(errorRow(code),code,locale):'<div data-cb="'+esc(code)+'"><p role="status">'+(LAZY_HELP.failed?helpFail():t('Загрузка объяснения…','Loading the explanation…'))+'</p></div>';}
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
