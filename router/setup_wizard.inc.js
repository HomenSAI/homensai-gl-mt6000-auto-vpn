function setupWizard(inventory,kind){
  var setupCheck=kind==='system'?'pending':'passed';
  var step=0,busy=false,closed=false,settings=inventory.settings||{},profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],custom=Array.isArray(inventory.servers)?inventory.servers:[];
  var draft={source:settings.plan_source||'',target:settings.plan_target||'',interval:settings.interval||30,duration:settings.native_duration||10,session_loss:!!settings.native_session_loss,servers:profiles.map(function(p){var saved=custom.filter(function(s){return s.profile===p.id;})[0]||{};return {profile:p.id,name:saved.name||p.name,channel:saved.channel||'default',priority:saved.priority||100,enabled:saved.enabled!==false};})};
  var tg={token:'',chat:'',enabled:true,interval:60};
  function field(title,node){node.setAttribute('aria-label',title);return E('label',{'class':'hv-wizard-field'},[E('span',{},title),node]);}
  function input(value,type){var node=E('input',{'type':type||'text'});node.value=value;return node;}
  function choice(value){var node=E('select',{},[E('option',{value:''},bi('Choose existing profile','Выберите существующий профиль'))].concat(profiles.map(function(p){return E('option',{value:p.id},p.name+' · '+p.protocol);})));node.value=value;return node;}
  function notify(code){ui.addNotification(null,E('p',{},code));}
  function show(){
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;};
    body.appendChild(E('p',{'class':'hv-eyebrow'},bi('Step ','Шаг ')+(step+1)+' / 3'));
    if(kind==='system'){
      body.appendChild(E('p',{'role':'status'},setupCheck==='passed'?'SETUP-CHECK-OK: installed UCI writer passed isolated check.':setupCheck==='pending'?'Checking installed UCI writer…':'SETUP-CHECK-FAILED: saving is blocked. After an upgrade, sign out and sign in to refresh application permissions.'));
      if(step===0){
        var primary=choice(draft.source),reserve=choice(draft.target),interval=input(draft.interval,'number'),duration=input(draft.duration,'number'),consent=input('','checkbox');consent.checked=draft.session_loss;
        [field(bi('Primary VPN','Основной VPN'),primary),field(bi('Reserve VPN','Резервный VPN'),reserve),field(bi('Probe interval, seconds (10–300)','Интервал проверки, секунд (10–300)'),interval),field(bi('Trial duration, minutes (1–240)','Длительность теста, минут (1–240)'),duration),field(bi('Allow calls/sessions to reconnect','Разрешить переподключение звонков/сессий'),consent)].forEach(function(n){body.appendChild(n);});
        body.appendChild(E('p',{},bi('Existing router profiles are reused. This wizard never imports, displays or replaces VPN keys.','Используются существующие профили роутера. Мастер не импортирует, не показывает и не заменяет VPN-ключи.')));
        read=function(){draft.source=primary.value;draft.target=reserve.value;draft.interval=Number(interval.value);draft.duration=Number(duration.value);draft.session_loss=consent.checked;return !!draft.source&&!!draft.target&&draft.source!==draft.target&&Number.isInteger(draft.interval)&&draft.interval>=10&&draft.interval<=300&&Number.isInteger(draft.duration)&&draft.duration>=1&&draft.duration<=240;};
      }else if(step===1){
        body.appendChild(E('p',{},bi('Names and priorities are monitoring metadata. Live route changes require a certified controller trial.','Названия и приоритеты — метаданные мониторинга. Изменение маршрутов требует подтверждённого теста контроллера.')));
        var editors=draft.servers.map(function(row){var name=input(row.name),channel=input(row.channel),priority=input(row.priority,'number');body.appendChild(E('fieldset',{},[E('legend',{},row.profile),field(bi('Display name','Название'),name),field(bi('Channel group','Группа канала'),channel),field(bi('Priority (1–1000)','Приоритет (1–1000)'),priority)]));return {row:row,name:name,channel:channel,priority:priority};});
        read=function(){return editors.every(function(e){e.row.name=e.name.value.trim();e.row.channel=e.channel.value.trim();e.row.priority=Number(e.priority.value);return e.row.name.length>0&&e.row.name.length<=64&&e.row.channel.length>0&&e.row.channel.length<=64&&Number.isInteger(e.row.priority)&&e.row.priority>=1&&e.row.priority<=1000;});};
      }else{
        body.appendChild(E('h3',{},bi('Review monitoring configuration','Проверьте настройки мониторинга')));
        var source=profiles.filter(function(p){return p.id===draft.source;})[0],target=profiles.filter(function(p){return p.id===draft.target;})[0];
        body.appendChild(E('ul',{},[E('li',{},bi('Primary: ','Основной: ')+(source||{}).name),E('li',{},bi('Reserve: ','Резерв: ')+(target||{}).name),E('li',{},bi('Probe interval: ','Интервал проверки: ')+draft.interval+' s'),E('li',{},bi('Trial duration: ','Длительность теста: ')+draft.duration+' min'),E('li',{},bi('Profiles: ','Профилей: ')+draft.servers.length)]));
        body.appendChild(E('p',{},bi('Saving does not start automatic switching. Use the Auto mode control after LAN certification.','Сохранение не запускает автопереключение. После LAN-проверки используйте кнопку авторежима.')));
      }
    }else{
      if(step===0){var token=input(tg.token,'password');token.autocomplete='off';body.appendChild(E('p',{},bi('Create a bot with BotFather. For a channel, add it as an administrator with permission to post. A token is secret and is never returned by the router.','Создайте бота через BotFather. В канале добавьте его администратором с правом публикации. Токен секретный и не возвращается роутером.')));body.appendChild(field(bi('Bot token (leave blank to keep the stored token)','Токен бота (пусто — сохранить имеющийся)'),token));read=function(){tg.token=token.value.trim();return (!tg.token&&settings.telegram_configured)||/^[0-9]{6,15}:[A-Za-z0-9_-]{30,100}$/.test(tg.token);};
      }else if(step===1){var chat=input(tg.chat),interval=input(tg.interval,'number'),enabled=input('','checkbox');enabled.checked=tg.enabled;chat.placeholder='@channel_name or -100…';body.appendChild(field(bi('Channel / destination ID','Канал / ID получателя'),chat));body.appendChild(field(bi('Report interval, minutes (5–10080)','Интервал отчётов, минут (5–10080)'),interval));body.appendChild(field(bi('Enable scheduled reports','Включить отчёты по расписанию'),enabled));read=function(){tg.chat=chat.value.trim();tg.interval=Number(interval.value);tg.enabled=enabled.checked;return /^(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$/.test(tg.chat)&&Number.isInteger(tg.interval)&&tg.interval>=5&&tg.interval<=10080;};
      }else{body.appendChild(E('h3',{},bi('Review Telegram destination','Проверьте получателя Telegram')));body.appendChild(E('p',{},bi('Destination: ','Получатель: ')+tg.chat));body.appendChild(E('p',{},bi('Reports every ','Отчёты каждые ')+tg.interval+' min'));body.appendChild(E('p',{},bi('After saving, use the separate Test delivery button. The stored token is never shown.','После сохранения используйте отдельную кнопку проверки доставки. Сохранённый токен не показывается.')));}
    }
    var actions=E('div',{'class':'hv-wizard-actions'});
    actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){closed=true;ui.hideModal();}},bi('Cancel','Отмена')));
    if(step>0)actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){read();step--;show();}},bi('Back','Назад')));
    actions.appendChild(E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':kind==='system'&&setupCheck!=='passed'?'':null,'click':function(ev){
      if(busy)return;if(!read()){notify('SETUP-VALIDATION: check profiles, names and numeric ranges.');return;}
      if(step<2){step++;show();return;}
      busy=true;ev.target.disabled=true;
      var save=kind==='system'?rpc.declare({object:'homensai-vpn',method:'setup_system',params:['source','target','interval','duration','session_loss','servers'],expect:{}})(draft.source,draft.target,draft.interval,draft.duration,draft.session_loss,draft.servers):rpc.declare({object:'homensai-vpn',method:'setup_telegram',params:['token','chat','enabled','interval'],expect:{}})(tg.token,tg.chat,tg.enabled,tg.interval);
      return save.then(function(result){if(!result.saved){notify(result.code||'SETUP-SAVE-FAILED');return;}tg.token='';closed=true;ui.hideModal();notify('SETUP-SAVED: settings stored; automatic switching was not started.');window.location.reload();}).catch(function(){notify('SETUP-SAVE-FAILED: no confirmed result.');}).finally(function(){busy=false;ev.target.disabled=false;});
    }},step<2?bi('Next','Далее'):bi('Save configuration','Сохранить настройки')));
    if(kind==='system'&&setupCheck!=='passed')body.querySelectorAll('input,select').forEach(function(node){node.disabled=true;});
    body.appendChild(actions);ui.showModal(kind==='system'?bi('System setup wizard','Мастер настройки системы'):bi('Telegram channel wizard','Мастер Telegram-канала'),[body]);
  }
  show();
  if(kind==='system')rpc.declare({object:'homensai-vpn',method:'setup_check',expect:{}})().then(function(result){if(closed)return;setupCheck=result.passed?'passed':'failed';show();}).catch(function(){if(closed)return;setupCheck='failed';show();});
}
