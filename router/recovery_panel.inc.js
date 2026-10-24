function reviewPriorities(ordered){
  return rpc.declare({object:'homensai-vpn',method:'priority_preview',params:['ordered'],expect:{}})(ordered).then(function(result){
    if(!result.accepted){ui.addNotification(null,E('p',{},result.code||'PRIORITY-PREVIEW-FAILED'));return;}
    ui.showModal(bi('Review server priorities','Проверьте приоритеты серверов'),[
      E('p',{},bi('Only application priorities are saved. This does not switch a live route. Unselected profiles follow the selected servers in their existing order.','Сохраняются только приоритеты приложения. Текущий маршрут не переключается. Неотмеченные профили следуют за выбранными в прежнем порядке.')),
      E('ol',{},result.rows.map(function(row){return E('li',{},row.name+' · '+row.protocol+' / '+row.channel+(row.enabled?'':' · disabled'));})),
      E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),
      guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',method:'priority_apply',params:['ordered','revision'],expect:{}})(ordered,result.revision).then(function(saved){ui.addNotification(null,E('p',{},saved.code||'PRIORITY-UNKNOWN'));if(saved.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'PRIORITY-RPC-UNCONFIRMED'));});},{key:'priority-apply'});}},bi('Apply priorities','Применить приоритеты')),'priority-apply')
    ]);
  }).catch(function(){ui.addNotification(null,E('p',{},'PRIORITY-PREVIEW-UNCONFIRMED'));});
}
function recoveryWizard(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},step=0,presetName='';
  var labels={failures:bi('Consecutive failures before switching (3–10)','Сбоев подряд до переключения (3–10)'),successes:bi('Reserve successes required (2–10)','Успешных проверок резерва (2–10)'),cooldown:bi('Cooldown between attempts, seconds (60–1800)','Пауза между попытками, секунд (60–1800)'),min_dwell:bi('Minimum dwell time, seconds (60–3600)','Минимальное время работы, секунд (60–3600)'),primary_successes:bi('Primary successes before return (2–10)','Успешных проверок основного перед возвратом (2–10)'),primary_stable:bi('Primary stable interval, seconds (30–600)','Период стабильности основного, секунд (30–600)')};
  var defaults={failures:3,successes:2,cooldown:180,min_dwell:180,return_policy:'healthy_primary',primary_successes:3,primary_stable:60},draft={};
  Object.keys(defaults).forEach(function(key){draft[key]=settings['recovery_'+key]==null?defaults[key]:settings['recovery_'+key];});
  // A saved set that equals a reviewed preset is shown as that preset; any other set is Custom.
  Object.keys(RECOVERY_PRESETS).forEach(function(name){var row=RECOVERY_PRESETS[name];if(!presetName&&Object.keys(defaults).every(function(key){return String(row[key])===String(draft[key]);}))presetName=name;});
  function show(){
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;},checks=[],nextButton;
    function updateGate(){if(nextButton)foolGate(nextButton,checks);}
    body.appendChild(E('p',{},bi('Recovery settings apply only within a certified bounded trial. Wi-Fi/Ethernet are uplinks, not VPN protocols. IPv6/native activation of inactive profiles remain blocked where unsupported.','Настройки действуют только в подтверждённом ограниченном тесте. Wi-Fi/Ethernet — подключения, не протоколы VPN. IPv6 и запуск неактивных профилей блокируются, если не поддерживаются.')));
    if(step===0){
      var presetSelect=E('select',{'aria-label':bi('Recovery preset','Профиль восстановления')},[
        E('option',{value:''},bi('Custom settings','Свои настройки')),E('option',{value:'stability'},bi('Stability','Стабильность')),E('option',{value:'fast_recovery'},bi('Fast recovery','Быстрое восстановление')),E('option',{value:'hold_reserve'},bi('Hold healthy reserve','Сохранять работающий резерв'))]);
      presetSelect.value=presetName;
      presetSelect.addEventListener('change',function(){presetName=presetSelect.value;var preset=RECOVERY_PRESETS[presetName];if(!preset)return;Object.keys(preset).forEach(function(key){draft[key]=preset[key];});show();});
      body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Preset (review before saving)','Профиль (проверьте перед сохранением)')),presetSelect]));
      var editors={};Object.keys(labels).forEach(function(key){var node=E('input',{type:'number','aria-label':labels[key]});node.value=draft[key];node.addEventListener('input',function(){presetName='';presetSelect.value='';});editors[key]=node;var item=foolNumberRow(labels[key],node,'recovery.'+key,updateGate);checks.push(item.check);body.appendChild(item.row);});
      var policy=E('select',{'aria-label':bi('Return policy','Политика возврата')},[E('option',{value:'healthy_primary'},bi('Return only after stable primary health','Возврат после подтверждения стабильности основного')),E('option',{value:'hold_reserve'},bi('Keep healthy reserve until operator review','Сохранять резерв до решения оператора'))]);policy.value=draft.return_policy;policy.addEventListener('change',function(){presetName='';presetSelect.value='';});body.appendChild(policy);
      read=function(){if(!foolGate(null,checks))return false;var limits={failures:[3,10],successes:[2,10],cooldown:[60,1800],min_dwell:[60,3600],primary_successes:[2,10],primary_stable:[30,600]};var valid=Object.keys(editors).every(function(key){draft[key]=Number(editors[key].value);return Number.isInteger(draft[key])&&draft[key]>=limits[key][0]&&draft[key]<=limits[key][1];});draft.return_policy=policy.value;return valid;};
    }else{
      body.appendChild(E('h3',{},bi('Review recovery settings','Проверьте настройки восстановления')));
      body.appendChild(E('ul',{},Object.keys(labels).map(function(key){return E('li',{},labels[key]+': '+draft[key]);})));
      body.appendChild(E('p',{},bi('Return policy: ','Политика возврата: ')+draft.return_policy));
      body.appendChild(E('p',{},bi('Changes invalidate previous recovery certification. Auto remains off; run the LAN helper again before enabling it.','Изменения требуют повторной проверки восстановления. Авторежим остаётся выключенным; перед включением снова запустите LAN-помощник.')));
    }
    var actions=[E('button',{'type':'button','class':'cbi-button','click':function(){if(FOOL_LOCKS['setup-recovery']&&FOOL_LOCKS['setup-recovery'].phase==='work')return;ui.hideModal();}},bi('Cancel','Отмена'))];
    if(step)actions.push(E('button',{'type':'button','class':'cbi-button','click':function(){if(FOOL_LOCKS['setup-recovery']&&FOOL_LOCKS['setup-recovery'].phase==='work')return;step=0;show();}},bi('Back','Назад')));
    actions.push(nextButton=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){if(!read()){ui.addNotification(null,E('p',{},'RECOVERY-RANGE'));return;}if(!step){step=1;show();return;}var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',method:'setup_recovery',params:['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable'],expect:{}})(draft.failures,draft.successes,draft.cooldown,draft.min_dwell,draft.return_policy,draft.primary_successes,draft.primary_stable).then(function(result){ui.addNotification(null,E('p',{},result.saved?'RECOVERY-SAVED':result.code||'RECOVERY-SAVE-FAILED'));if(result.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'RECOVERY-SAVE-UNCONFIRMED'));});},{key:'setup-recovery'});}},step?bi('Save recovery settings','Сохранить настройки восстановления'):bi('Next','Далее')));
    updateGate();guardResume(nextButton,'setup-recovery');body.appendChild(E('div',{'class':'hv-wizard-actions'},actions));ui.showModal(bi('Recovery setup wizard','Мастер восстановления'),[body]);
  }
  show();
}

function monitorPreferences(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},saveButton,checks=[];
  var planning=E('input',{type:'checkbox','aria-label':bi('Enable read-only planning','Включить планирование без применения')});planning.checked=!!settings.plan_enabled;
  var body=E('div',{'class':'hv-wizard'},[E('p',{},bi('Only own monitor settings are changed. Short checkpoints increase flash writes. This does not enable Auto or start inactive VPNs.','Меняются только настройки мониторинга. Частые checkpoint увеличивают записи во flash. Авторежим и неактивные VPN не запускаются.'))]);
  function updateGate(){if(saveButton)foolGate(saveButton,checks);}
  function number(label,key,value,ariaLabel){var node=E('input',{type:'number'});node.value=value;var item=foolNumberRow(label,node,key,updateGate);node.setAttribute('aria-label',ariaLabel);checks.push(item.check);body.appendChild(item.row);return node;}
  var interval=number(bi('Probe interval (10–300 seconds)','Интервал проверки (10–300 секунд)'),'monitor.interval',settings.interval==null?30:settings.interval,bi('Probe interval, seconds','Интервал проверки, секунд')),checkpoint=number(bi('Checkpoint (300–3600 seconds)','Checkpoint (300–3600 секунд)'),'monitor.checkpoint',settings.checkpoint==null?900:settings.checkpoint,bi('Checkpoint interval, seconds','Интервал checkpoint, секунд')),limit=number(bi('Profile limit (1–16)','Лимит профилей (1–16)'),'monitor.probe_limit',settings.probe_limit==null?16:settings.probe_limit,bi('Profile limit per round','Лимит профилей за раунд'));
  var logLimit=number(bi('Live journal observations (1–2000)','Наблюдений в живом журнале (1–2000)'),'monitor.live_log_limit',settings.live_log_limit==null?2000:settings.live_log_limit,bi('Live journal observations','Наблюдений в живом журнале'));
  var historyDays=number(bi('Detailed history, days (1–7)','Подробная история, дней (1–7)'),'monitor.history_days',settings.history_days==null?7:settings.history_days,bi('Detailed history, days','Подробная история, дней'));
  body.appendChild(E('p',{},bi('The journal limit controls browser memory. The history period controls saved incident details and observations. Monthly and lifetime counters are kept separately. Reducing the period removes old details at the next cleanup/checkpoint; increasing it cannot recover removed history.','Лимит журнала ограничивает память браузера. Срок истории ограничивает сохранённые подробности событий и наблюдений. Месячные и общие счётчики хранятся отдельно. Уменьшение срока удаляет старые подробности при очередной очистке/checkpoint; увеличение не восстанавливает удалённую историю.')));
  body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Read-only failover planning','Планирование без применения')),planning]));
  saveButton=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
    if(!foolGate(saveButton,checks))return;
    return guardedAction(saveButton,function(){return rpc.declare({object:'homensai-vpn',method:'setup_monitor',params:['interval','checkpoint','probe_limit','planning_enabled','live_log_limit','history_days'],expect:{}})(Number(interval.value),Number(checkpoint.value),Number(limit.value),planning.checked,Number(logLimit.value),Number(historyDays.value)).then(function(result){ui.addNotification(null,E('p',{},result&&result.saved===true?'MONITOR-PREFERENCES-SAVED':result&&result.code||'MONITOR-PREFERENCES-FAILED'));if(result&&result.saved===true){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-PREFERENCES-UNCONFIRMED'));});},{key:'setup-monitor'});
  }},bi('Save monitoring preferences','Сохранить параметры мониторинга'));
  updateGate();guardResume(saveButton,'setup-monitor');
  body.appendChild(E('div',{'class':'hv-wizard-actions'},[E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),saveButton]));
  ui.showModal(bi('Monitoring and history retention','Мониторинг и хранение истории'),[body]);
}
