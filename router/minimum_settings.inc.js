/* Persistent editor for the selected pair. Navigation/polling never writes.
   setup_system remains the authoritative, locked writer and never starts Auto. */
var MINIMUM_SETTINGS_SESSION=null;
var MINIMUM_SETTINGS_GUARD=null;
function installMinimumSettingsGuard(root){
  if(MINIMUM_SETTINGS_GUARD)MINIMUM_SETTINGS_GUARD();
  if(typeof window==='undefined'||typeof window.addEventListener!=='function')return;
  function beforeUnload(event){
    if(root&&root.isConnected===false||minimumSettingsCanLeave())return;
    event.preventDefault();event.returnValue='';return '';
  }
  window.addEventListener('beforeunload',beforeUnload);
  MINIMUM_SETTINGS_GUARD=function(){window.removeEventListener('beforeunload',beforeUnload);MINIMUM_SETTINGS_GUARD=null;};
  return MINIMUM_SETTINGS_GUARD;
}
function minimumSettingsPair(inventory){
  var s=inventory&&inventory.settings||{};
  return {source:s.plan_source||'',target:s.plan_target||'',session_loss:s.native_session_loss===true};
}
function minimumSettingsPairKey(pair){return JSON.stringify([pair.source,pair.target,pair.session_loss===true]);}
function minimumSettingsPayload(draft,inventory){
  if(!inventory||inventory.error||!inventory.settings)throw new Error('RPC-INVENTORY-UNAVAILABLE');
  var profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],settings=inventory.settings;
  var available=onboardingPairChannels(profiles,settings),ids=available.map(function(p){return p.id;});
  if(!draft.source||draft.source===draft.target||ids.indexOf(draft.source)<0||ids.indexOf(draft.target)<0)throw new Error('SETUP-PROFILES');
  var custom=Array.isArray(inventory.servers)?inventory.servers:[];
  var servers=profiles.map(function(p){
    var row=custom.filter(function(r){return r.profile===p.id;})[0]||{};
    return {profile:p.id,name:row.name==null?p.name:row.name,channel:row.channel==null?'default':row.channel,priority:row.priority==null?100:Number(row.priority),enabled:row.enabled!==false};
  });
  if(!servers.some(function(p){return p.profile===draft.source&&p.enabled;})||!servers.some(function(p){return p.profile===draft.target&&p.enabled;}))throw new Error('SETUP-PRIMARY-RESERVE-DISABLED');
  var interval=settings.interval==null?30:Number(settings.interval),duration=settings.native_duration==null?10:Number(settings.native_duration);
  if(!Number.isInteger(interval)||interval<10||interval>300||!Number.isInteger(duration)||duration<1||duration>240)throw new Error('SETUP-RANGE');
  return {source:draft.source,target:draft.target,interval:interval,duration:duration,session_loss:draft.session_loss===true,servers:servers};
}
function minimumSettingsDirty(){
  var s=MINIMUM_SETTINGS_SESSION;return !!s&&minimumSettingsPairKey(s.draft)!==s.baseline;
}
function minimumSettingsBusy(){return !!MINIMUM_SETTINGS_SESSION&&MINIMUM_SETTINGS_SESSION.busy;}
function minimumSettingsCanLeave(){return !minimumSettingsDirty()&&!minimumSettingsBusy();}
/* Always invokes proceed for an allowed transition; callers must not invoke it twice. */
function minimumSettingsRequestLeave(proceed){
  var session=MINIMUM_SETTINGS_SESSION;
  if(!session||minimumSettingsCanLeave()){proceed();return true;}
  if(session.busy){session.error=bi('Settings are being saved. Wait for confirmation.','Настройки сохраняются. Дождитесь подтверждения.');session.sync();return false;}
  ui.showModal(bi('Unsaved settings','Несохранённые настройки'),[
    E('p',{},bi('Save the selected pair, discard changes or stay on this page.','Сохранить выбранную пару, отбросить изменения или остаться на странице.')),
    E('div',{'class':'hv-wizard-actions'},[
      E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Stay','Остаться')),
      E('button',{'type':'button','class':'cbi-button','click':function(){session.discard();ui.hideModal();proceed();}},bi('Discard changes','Отбросить изменения')),
      E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':session.canSave()?null:'','click':function(){session.reviewSave(proceed);}},bi('Save changes','Сохранить изменения'))
    ])
  ]);return false;
}
function renderMinimumSettings(inventory,status,getLatest){
  if(MINIMUM_SETTINGS_SESSION){
    var existing=MINIMUM_SETTINGS_SESSION;existing.status=status;existing.getLatest=getLatest;
    if(!minimumSettingsDirty()&&!existing.busy){existing.inventory=inventory;existing.draft=minimumSettingsPair(inventory);existing.baseline=minimumSettingsPairKey(existing.draft);existing.resetFields();}
    return existing.host;
  }
  var session={inventory:inventory,status:status,getLatest:getLatest,draft:minimumSettingsPair(inventory),busy:false,error:''};
  session.baseline=minimumSettingsPairKey(session.draft);MINIMUM_SETTINGS_SESSION=session;
  var host=E('section',{'class':'hv-minimum-settings','data-minimum-settings':'1','data-hv-page':'settings'});session.host=host;
  var source=E('select',{'data-minimum-field':'source'}),target=E('select',{'data-minimum-field':'target'}),consent=E('input',{'type':'checkbox','data-minimum-field':'session_loss'});
  function field(title,node){node.setAttribute('aria-label',title);return E('label',{'class':'hv-wizard-field'},[E('span',{},title),node]);}
  host.appendChild(field(bi('Primary VPN client','Основной VPN-клиент'),source));
  host.appendChild(field(bi('Reserve VPN client','Резервный VPN-клиент'),target));
  host.appendChild(E('label',{'class':'hv-wizard-field hv-wizard-toggle'},[consent,E('span',{},bi('Allow calls and sessions to reconnect when switching','Разрешить переподключение звонков и сессий при переключении'))]));
  consent.setAttribute('aria-label',bi('Allow sessions to reconnect','Разрешить переподключение сессий'));
  var validation=E('p',{'role':'status','data-minimum-validation':'1'}),error=E('p',{'role':'alert','data-minimum-save-error':'1'}),progress=E('p',{'role':'status','aria-live':'polite','data-minimum-save-progress':'1'});
  host.appendChild(validation);host.appendChild(error);host.appendChild(progress);
  var save=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-minimum-action':'save','click':function(){return session.reviewSave();}},bi('Save changes','Сохранить изменения'));
  var cancel=E('button',{'type':'button','class':'cbi-button','data-minimum-action':'cancel','click':function(){if(!session.busy)session.discard();}},bi('Cancel changes','Отменить изменения'));
  host.appendChild(E('div',{'class':'hv-wizard-actions'},[save,cancel]));
  host.appendChild(E('p',{'class':'hv-minimum-settings-note'},bi('Saving does not start Auto. Updated readiness is checked before the next Start.','Сохранение не запускает Auto. Перед следующим запуском готовность проверяется заново.')));
  var advanced=E('details',{'class':'hv-minimum-settings-advanced'},[E('summary',{},bi('Additional settings','Дополнительно'))]);
  [
    ['system','Existing profiles, names and priorities','Существующие профили, названия и приоритеты'],
    ['monitor','Monitoring and history retention','Мониторинг и хранение истории'],
    ['recovery','Recovery preferences','Параметры восстановления'],
    ['speed','Speed-test preferences','Параметры тестов скорости'],
    ['telegram','Telegram reports','Отчёты Telegram'],
    ['appearance','Language and theme','Язык и тема']
  ].forEach(function(row){advanced.appendChild(E('p',{},E('button',{'type':'button','class':'cbi-button','data-minimum-settings-open':row[0],'click':function(){
    minimumSettingsRequestLeave(function(){openOnboardingSettings(session.inventory,session.status||{},row[0]);});
  }},bi(row[1],row[2]))));});host.appendChild(advanced);
  function validationMessage(){
    try{minimumSettingsPayload(session.draft,session.inventory);return '';}
    catch(e){return e.message==='RPC-INVENTORY-UNAVAILABLE'?bi('Current settings are unavailable. Refresh the router connection before saving.','Текущие настройки недоступны. Восстановите связь с роутером перед сохранением.'):e.message==='SETUP-PRIMARY-RESERVE-DISABLED'?bi('Both selected profiles must be monitored. Open additional profile settings.','Оба выбранных профиля должны участвовать в мониторинге. Откройте дополнительные настройки профилей.'):e.message==='SETUP-RANGE'?bi('Stored intervals need review in additional settings.','Проверьте сохранённые интервалы в дополнительных настройках.'):bi('Choose two different configured VPN clients.','Выберите два разных настроенных VPN-клиента.');}
  }
  session.canSave=function(){return !session.busy&&minimumSettingsDirty()&&!validationMessage();};
  session.sync=function(){
    var message=validationMessage(),dirty=minimumSettingsDirty();validation.textContent=message;error.textContent=session.error;
    save.disabled=session.busy||!dirty||!!message;cancel.disabled=session.busy||!dirty;
    [source,target,consent].forEach(function(n){n.disabled=session.busy;});host.setAttribute('aria-busy',session.busy?'true':'false');
    progress.textContent=session.busy?bi('Saving settings…','Сохранение настроек…'):'';
  };
  session.resetFields=function(){
    var choices=onboardingPairChannels(session.inventory&&session.inventory.profiles,session.inventory&&session.inventory.settings);
    [source,target].forEach(function(n){while(n.firstChild)n.removeChild(n.firstChild);n.appendChild(E('option',{value:''},bi('Choose a configured client','Выберите настроенного клиента')));choices.forEach(function(p){n.appendChild(E('option',{value:p.id},onboardingPairChannelLabel(p)));});});
    [['source',source],['target',target]].forEach(function(row){var value=session.draft[row[0]];if(value&&!choices.some(function(p){return p.id===value;}))row[1].appendChild(E('option',{value:value},bi('Saved client unavailable: ','Сохранённый клиент недоступен: ')+value));row[1].value=value;});
    consent.checked=session.draft.session_loss;session.sync();
  };
  session.discard=function(){session.draft=minimumSettingsPair(session.inventory);session.baseline=minimumSettingsPairKey(session.draft);session.error='';session.resetFields();};
  function changed(){if(session.busy)return;session.draft={source:source.value,target:target.value,session_loss:consent.checked===true};session.error='';session.sync();}
  [source,target,consent].forEach(function(n){n.addEventListener('change',changed);});
  session.reviewSave=function(afterSave){
    if(session.busy||!minimumSettingsDirty()||validationMessage())return Promise.resolve(false);
    var reviewed={source:session.draft.source,target:session.draft.target,session_loss:session.draft.session_loss},reviewedKey=minimumSettingsPairKey(reviewed);
    function name(id){var p=(session.inventory.profiles||[]).filter(function(p){return p.id===id;})[0];return p&&p.name||id;}
    var confirm=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-minimum-action':'confirm-save','click':function(){
      if(session.busy||reviewedKey!==minimumSettingsPairKey(session.draft))return;
      session.busy=true;session.error='';session.sync();confirm.disabled=true;
      var freshInventory;
      return Promise.resolve().then(function(){return setupCheckRequest();}).then(function(result){
        if(!result||result.passed!==true)throw new Error('SETUP-CHECK-FAILED');
        return typeof inventoryCall==='function'?inventoryCall():rpc.declare({object:'homensai-vpn',reject:true,method:'inventory',expect:{}})();
      }).then(function(fresh){
        freshInventory=fresh;
        if(!fresh||fresh.error||!fresh.settings)throw new Error('RPC-INVENTORY-UNAVAILABLE');
        if(minimumSettingsPairKey(minimumSettingsPair(fresh))!==session.baseline)throw new Error('SETUP-CONFIG-CHANGED');
        var payload=minimumSettingsPayload(reviewed,fresh);
        return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_system',params:['source','target','interval','duration','session_loss','servers'],expect:{}})(payload.source,payload.target,payload.interval,payload.duration,payload.session_loss,payload.servers);
      }).then(function(result){
        if(!result||result.saved!==true)throw new Error(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code)?result.code:'SETUP-SAVE-UNCONFIRMED');
        session.inventory=freshInventory;session.draft=reviewed;session.baseline=reviewedKey;session.busy=false;ui.hideModal();session.sync();
        if(typeof afterSave==='function')afterSave();
        window.location.reload();return true;
      }).catch(function(e){
        var code=e&&typeof e.message==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(e.message)?e.message:'SETUP-SAVE-UNCONFIRMED';
        session.error=code+' · '+bi('The save was not confirmed. Your changes remain here; refresh the router state before retrying.','Сохранение не подтверждено. Изменения сохранены в форме; проверьте состояние роутера перед повтором.');
        session.busy=false;ui.hideModal();session.sync();return false;
      });
    }},bi('Save selected pair','Сохранить выбранную пару'));
    ui.showModal(bi('Review changes','Проверьте изменения'),[
      E('p',{},bi('Primary: ','Основной: ')+name(reviewed.source)),E('p',{},bi('Reserve: ','Резервный: ')+name(reviewed.target)),
      E('p',{},bi('Sessions may reconnect: ','Сессии могут переподключаться: ')+(reviewed.session_loss?bi('Allowed','Разрешено'):bi('Not allowed','Не разрешено'))),
      E('p',{},bi('Other application settings and VPN keys are retained. Auto is not started.','Остальные настройки приложения и ключи VPN сохраняются. Auto не запускается.')),
      E('div',{'class':'hv-wizard-actions'},[E('button',{'type':'button','class':'cbi-button','click':function(){if(!session.busy)ui.hideModal();}},bi('Back','Назад')),confirm])
    ]);return Promise.resolve(false);
  };
  session.resetFields();return host;
}
