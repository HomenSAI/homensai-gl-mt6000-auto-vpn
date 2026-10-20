/* Help inside the Telegram wizard: the same steps as Help -> "Telegram reports do not arrive", plus examples of both values. */
function telegramTokenHelp(){
  var topic=(typeof HELP_TOPICS!=='undefined'?HELP_TOPICS:[]).filter(function(t){return t.id==='telegram';})[0];
  var steps=topic?topic.steps.slice(0,5):[];
  return E('details',{'class':'hv-wizard-help','open':''},[E('summary',{},bi('How to get the bot token and the chat ID','Как получить токен бота и Chat ID')),
    E('ol',{},steps.map(function(s){return E('li',{},richText(bi(s.t[0],s.t[1])));})),
    E('p',{'class':'hv-wizard-example'},bi('Example token: 123456789:AAH… (digits, a colon, then 30–100 letters, digits, _ or -). Example chat ID: 123456789 for yourself, -1001234567890 for a group or channel, or @my_channel for a public channel.','Пример токена: 123456789:AAH… (цифры, двоеточие, затем 30–100 букв, цифр, _ или -). Пример Chat ID: 123456789 для себя, -1001234567890 для группы или канала, или @my_channel для публичного канала.'))]);
}
/* What a Telegram report contains: the owner ticks it. Header, report id and an ALARM line are always sent. */
var TG_ITEMS=[
  ['servers','Connected servers and their state','Подключённые серверы и их состояние','One line per server: name, protocol, OK or error code, response time. (Period reports: hours up/down per server.)','По строке на сервер: имя, протокол, OK или код ошибки, время ответа. (В сводках: часы работы и простоя сервера.)'],
  ['events','State changes','Изменения состояния','How many times a server changed state in the period, with the last ones listed.','Сколько раз сервер менял состояние за период, последние перечислены.'],
  ['traffic','VPN traffic','Трафик VPN','Gigabytes through the VPN this month (period reports: WAN and VPN traffic).','Гигабайты через VPN в этом месяце (в сводках: трафик WAN и VPN).'],
  ['delta','Traffic since the last report','Трафик с прошлого отчёта','How much traffic passed since the last confirmed report.','Сколько трафика прошло с прошлого подтверждённого отчёта.'],
  ['controller','Auto controller state','Состояние контроллера Auto','One line: what the automatic switching is doing now.','Одна строка: что сейчас делает автопереключение.'],
  ['controller_events','Controller events','События контроллера','Attempts, trials and switches during the period, with codes.','Попытки, тесты и переключения за период, с кодами.'],
  ['controller_totals','Controller monthly totals','Итоги контроллера за месяц','Attempts, passed trials, commits and rollbacks this month.','Попытки, пройденные тесты, переключения и откаты за месяц.'],
  ['gaps','Monitoring gaps and notes','Пропуски наблюдений и пометки','How often monitoring missed a check, plus the standard reading notes.','Сколько раз мониторинг пропустил проверку и стандартные пометки.']];
var TG_PRESETS={minimum:['servers'],standard:['servers','events','traffic','controller'],maximum:TG_ITEMS.map(function(i){return i[0];})};
function tgItemsFromSetting(value){
  if(typeof value!=='string'||value==='')return TG_PRESETS.maximum.slice();
  if(value==='none')return [];
  return value.split(',').filter(function(v){return TG_PRESETS.maximum.indexOf(v)>=0;});
}
function tgItemsToSetting(list){return list.length?TG_PRESETS.maximum.filter(function(i){return list.indexOf(i)>=0;}).join(','):'none';}
function tgItemsBlock(tg){
  var boxes={};
  function sync(){TG_ITEMS.forEach(function(i){boxes[i[0]].checked=tg.items.indexOf(i[0])>=0;});}
  var presets=E('div',{'class':'hv-tg-presets'},[['minimum','Minimum','Минимум'],['standard','Standard','Стандарт'],['maximum','Maximum','Максимум']].map(function(p){return E('button',{'type':'button','class':'cbi-button','click':function(){tg.items=TG_PRESETS[p[0]].slice();sync();}},bi(p[1],p[2]));}));
  var list=TG_ITEMS.map(function(i){var box=E('input',{'type':'checkbox','change':function(){tg.items=TG_PRESETS.maximum.filter(function(id){return id===i[0]?box.checked:tg.items.indexOf(id)>=0;});}});boxes[i[0]]=box;box.checked=tg.items.indexOf(i[0])>=0;return E('label',{},[box,' ',bi(i[1],i[2]),E('small',{},bi(i[3],i[4]))]);});
  return E('div',{'class':'hv-tg-items'},[E('strong',{},bi('What to send in Telegram','Что присылать в Telegram')),E('p',{},bi('Tick only what you need. Always sent: the report header and, if the controller stops automatic switching, an ALARM line. Presets: Minimum = servers only; Standard = servers, changes, traffic, controller; Maximum = everything.','Отметьте только нужное. Всегда приходит заголовок отчёта и, если контроллер остановил автопереключение, строка ALARM. Наборы: Минимум — только серверы; Стандарт — серверы, изменения, трафик, контроллер; Максимум — всё.')),presets].concat(list));
}
function setupWizard(inventory,kind){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var setupCheck=kind==='system'?'pending':'passed';
  var step=0,busy=false,closed=false,settings=inventory.settings||{},profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],custom=Array.isArray(inventory.servers)?inventory.servers:[];
  var draft={source:settings.plan_source||'',target:settings.plan_target||'',interval:settings.interval==null?30:settings.interval,duration:settings.native_duration==null?10:settings.native_duration,session_loss:!!settings.native_session_loss,servers:profiles.map(function(p){var saved=custom.filter(function(s){return s.profile===p.id;})[0]||{};return {profile:p.id,name:saved.name||p.name,channel:saved.channel||'default',priority:saved.priority==null?100:saved.priority,enabled:saved.enabled!==false};})};
  var tg={token:'',chat:settings.telegram_destination||'',enabled:!!settings.telegram_enabled,interval:settings.telegram_interval==null?60:settings.telegram_interval,schedule:settings.telegram_schedule||'interval',hour:settings.telegram_hour==null?7:settings.telegram_hour,weekly:settings.telegram_weekly!==false,monthly:settings.telegram_monthly!==false,items:tgItemsFromSetting(settings.telegram_items)};
  function field(title,node){node.setAttribute('aria-label',title);return E('label',{'class':'hv-wizard-field'},[E('span',{},title),node]);}
  function input(value,type){var node=E('input',{'type':type||'text'});node.value=value;return node;}
  function choice(value){var node=E('select',{},[E('option',{value:''},bi('Choose existing profile','Выберите существующий профиль'))].concat(profiles.map(function(p){return E('option',{value:p.id},p.name+' · '+p.protocol);})));node.value=value;return node;}
  function notify(code){ui.addNotification(null,E('p',{},code));}
  function show(){
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;},checks=[],nextButton;
    function updateGate(){if(nextButton)foolGate(nextButton,checks.concat([function(){return !busy&&(kind!=='system'||setupCheck==='passed');}]));}
    function numberField(title,node,key){var item=foolNumberRow(title,node,key,updateGate);checks.push(item.check);return item.row;}
    function textField(title,node,key){var item=foolTextRow(title,node,key,updateGate,key==='token'&&!settings.telegram_configured);checks.push(item.check);return item.row;}
    body.appendChild(E('p',{'class':'hv-eyebrow'},bi('Step ','Шаг ')+(step+1)+' / 3'));
    if(kind==='system'){
      body.appendChild(E('p',{'role':'status'},setupCheck==='passed'?'SETUP-CHECK-OK: installed UCI writer passed isolated check.':setupCheck==='pending'?'Checking installed UCI writer…':'SETUP-CHECK-FAILED: saving is blocked. After an upgrade, sign out and sign in to refresh application permissions.'));
      if(step===0){
        var primary=choice(draft.source),reserve=choice(draft.target),interval=input(draft.interval,'number'),duration=input(draft.duration,'number'),consent=input('','checkbox');consent.checked=draft.session_loss;
        [field(bi('Primary VPN','Основной VPN'),primary),field(bi('Reserve VPN','Резервный VPN'),reserve),numberField(bi('Probe interval, seconds (10–300)','Интервал проверки, секунд (10–300)'),interval,'system.interval'),numberField(bi('Trial duration, minutes (1–240)','Длительность теста, минут (1–240)'),duration,'system.duration'),field(bi('Allow calls/sessions to reconnect','Разрешить переподключение звонков/сессий'),consent)].forEach(function(n){body.appendChild(n);});
        body.appendChild(E('p',{},bi('Existing router profiles are reused. This wizard never imports, displays or replaces VPN keys.','Используются существующие профили роутера. Мастер не импортирует, не показывает и не заменяет VPN-ключи.')));
        read=function(){draft.source=primary.value;draft.target=reserve.value;draft.interval=Number(interval.value);draft.duration=Number(duration.value);draft.session_loss=consent.checked;return !!draft.source&&!!draft.target&&draft.source!==draft.target&&Number.isInteger(draft.interval)&&draft.interval>=10&&draft.interval<=300&&Number.isInteger(draft.duration)&&draft.duration>=1&&draft.duration<=240;};
      }else if(step===1){
        body.appendChild(E('p',{},bi('Names and priorities are monitoring metadata. Live route changes require a certified controller trial.','Названия и приоритеты — метаданные мониторинга. Изменение маршрутов требует подтверждённого теста контроллера.')));
        var editors=draft.servers.map(function(row){var name=input(row.name),channel=input(row.channel),priority=input(row.priority,'number'),enabled=input('','checkbox');enabled.checked=row.enabled;body.appendChild(E('fieldset',{},[E('legend',{},row.profile),textField(bi('Display name','Название'),name,'name'),textField(bi('Channel group','Группа канала'),channel,'channel'),numberField(bi('Priority (1–1000)','Приоритет (1–1000)'),priority,'system.priority'),field(bi('Monitor this server','Наблюдать этот сервер'),enabled)]));return {row:row,name:name,channel:channel,priority:priority,enabled:enabled};});
        read=function(){var valid=editors.every(function(e){e.row.name=e.name.value.trim();e.row.channel=e.channel.value.trim();e.row.priority=Number(e.priority.value);e.row.enabled=e.enabled.checked;return e.row.name.length>0&&e.row.name.length<=64&&!/[\x00-\x1f]/.test(e.row.name)&&e.row.channel.length>0&&e.row.channel.length<=64&&!/[\x00-\x1f]/.test(e.row.channel)&&Number.isInteger(e.row.priority)&&e.row.priority>=1&&e.row.priority<=1000;});return valid&&draft.servers.some(function(r){return r.profile===draft.source&&r.enabled;})&&draft.servers.some(function(r){return r.profile===draft.target&&r.enabled;});};
      }else{
        body.appendChild(E('h3',{},bi('Review monitoring configuration','Проверьте настройки мониторинга')));
        var source=draft.servers.filter(function(p){return p.profile===draft.source;})[0],target=draft.servers.filter(function(p){return p.profile===draft.target;})[0];
        body.appendChild(E('ul',{},[E('li',{},bi('Primary: ','Основной: ')+(source||{}).name),E('li',{},bi('Reserve: ','Резерв: ')+(target||{}).name),E('li',{},bi('Probe interval: ','Интервал проверки: ')+draft.interval+' s'),E('li',{},bi('Trial duration: ','Длительность теста: ')+draft.duration+' min'),E('li',{},bi('Profiles: ','Профилей: ')+draft.servers.length)]));
        body.appendChild(E('p',{},bi('Calls/sessions may reconnect: ','Переподключение звонков/сессий: ')+(draft.session_loss?bi('Allowed','Разрешено'):bi('Not allowed','Не разрешено'))));
        body.appendChild(E('h3',{},bi('Server metadata to save','Данные серверов для сохранения')));
        var reviewRows=[E('tr',{},[bi('Profile','Профиль'),bi('Display name','Название'),bi('Channel','Канал'),bi('Priority','Приоритет'),bi('Monitor','Наблюдать')].map(function(label){return E('th',{},label);}))].concat(draft.servers.map(function(row){return E('tr',{},[row.profile,row.name,row.channel,String(row.priority),row.enabled?bi('Yes','Да'):bi('No','Нет')].map(function(value){return E('td',{},value);}));}));
        body.appendChild(E('div',{'class':'hv-table-scroll'},E('table',{'class':'hv-table'},reviewRows)));
        body.appendChild(E('p',{},bi('Saving does not start automatic switching. Use the Auto mode control after LAN certification.','Сохранение не запускает автопереключение. После LAN-проверки используйте кнопку авторежима.')));
      }
    }else{
      if(step===0){var token=input(tg.token,'password');token.autocomplete='off';body.appendChild(E('p',{},bi('Create a bot with BotFather. For a channel, add it as an administrator with permission to post. A token is secret and is never returned by the router.','Создайте бота через BotFather. В канале добавьте его администратором с правом публикации. Токен секретный и не возвращается роутером.')));body.appendChild(telegramTokenHelp());body.appendChild(textField(bi('Bot token (leave blank to keep the stored token)','Токен бота (пусто — сохранить имеющийся)'),token,'token'));if(settings.telegram_configured)body.appendChild(E('p',{},E('button',{'type':'button','class':'cbi-button cbi-button-negative','click':function(ev){
          if(!window.confirm(bi('Delete the stored bot token? Telegram reports will be turned off.','Удалить сохранённый токен бота? Отчёты в Telegram будут выключены.')))return;
          ev.target.disabled=true;
          return rpc.declare({object:'homensai-vpn',method:'telegram_forget',expect:{}})().then(function(result){
            if(result&&result.saved===true){closed=true;ui.hideModal();ui.addNotification(null,E('p',{},bi('The bot token was deleted and Telegram reports are off.','Токен бота удалён, отчёты в Telegram выключены.')));window.location.reload();}
            else{ev.target.disabled=false;ui.addNotification(null,E('p',{},(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code))?result.code:'SETUP-SAVE-FAILED'));}
          }).catch(function(){ev.target.disabled=false;ui.addNotification(null,E('p',{},'TELEGRAM-FORGET-UNCONFIRMED'));});
        }},bi('Delete the stored token','Удалить сохранённый токен'))));read=function(){tg.token=token.value.trim();return (!tg.token&&settings.telegram_configured)||/^[0-9]{6,15}:[A-Za-z0-9_-]{30,100}$/.test(tg.token);};
      }else if(step===1){
        var chat=input(tg.chat),interval=input(tg.interval,'number'),enabled=input('','checkbox'),hour=input(tg.hour,'number'),weekly=input('','checkbox'),monthly=input('','checkbox');
        var schedule=E('select',{},[E('option',{value:'interval'},bi('Every interval','Через интервал')),E('option',{value:'daily'},bi('Daily at selected hour','Ежедневно в выбранный час'))]);
        schedule.value=tg.schedule;enabled.checked=tg.enabled;weekly.checked=tg.weekly;monthly.checked=tg.monthly;
        chat.placeholder='@channel_name or -100…';
        [textField(bi('Channel / destination ID','Канал / ID получателя'),chat,'chat'),field(bi('Schedule','Расписание'),schedule),numberField(bi('Report interval, minutes (5–10080)','Интервал отчётов, минут (5–10080)'),interval,'telegram.interval'),numberField(bi('Daily hour, Europe/Berlin (0–23)','Час отчёта, Europe/Berlin (0–23)'),hour,'telegram.hour'),field(bi('Weekly summary on Monday','Недельная сводка в понедельник'),weekly),field(bi('Monthly summary on day 1','Месячная сводка первого числа'),monthly),field(bi('Enable scheduled reports','Включить отчёты по расписанию'),enabled)].forEach(function(n){body.appendChild(n);});body.appendChild(tgItemsBlock(tg));
        read=function(){tg.chat=chat.value.trim();tg.interval=Number(interval.value);tg.enabled=enabled.checked;tg.schedule=schedule.value;tg.hour=Number(hour.value);tg.weekly=weekly.checked;tg.monthly=monthly.checked;return /^(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$/.test(tg.chat)&&Number.isInteger(tg.interval)&&tg.interval>=5&&tg.interval<=10080&&Number.isInteger(tg.hour)&&tg.hour>=0&&tg.hour<=23;};
      }else{
        body.appendChild(E('h3',{},bi('Review Telegram destination','Проверьте получателя Telegram')));
        body.appendChild(E('p',{},bi('Destination: ','Получатель: ')+tg.chat));
        body.appendChild(E('p',{},tg.schedule==='daily'?bi('Daily at ','Ежедневно в ')+String(tg.hour).padStart(2,'0')+':00 Europe/Berlin':bi('Reports every ','Отчёты каждые ')+tg.interval+' min'));
        body.appendChild(E('p',{},bi('Weekly / monthly summaries: ','Недельная / месячная сводка: ')+(tg.weekly?'✓':'—')+' / '+(tg.monthly?'✓':'—')));body.appendChild(E('p',{},bi('Contents: ','Содержимое: ')+(tg.items.length?TG_ITEMS.filter(function(i){return tg.items.indexOf(i[0])>=0;}).map(function(i){return bi(i[1],i[2]);}).join(', '):bi('header and alarms only','только заголовок и тревоги'))));
        body.appendChild(E('p',{},bi('After saving, use the separate Test delivery button. The stored token is never shown.','После сохранения используйте отдельную кнопку проверки доставки. Сохранённый токен не показывается.')));
      }
    }
    var progress=E('p',{'class':'hv-wizard-progress','role':'status','aria-live':'polite'},'');body.appendChild(progress);
    var actions=E('div',{'class':'hv-wizard-actions'});
    actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){if(busy)return;closed=true;ui.hideModal();}},bi('Cancel','Отмена')));
    if(step>0)actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){if(busy||!foolGate(null,checks))return;read();step--;show();}},bi('Back','Назад')));
    actions.appendChild(nextButton=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':kind==='system'&&setupCheck!=='passed'?'':null,'click':function(ev){
      if(busy||kind==='system'&&setupCheck!=='passed')return;if(!foolGate(null,checks)||!read()){notify(bi('Check the highlighted fields, choose different primary and reserve profiles, and keep both monitored.','Проверьте выделенные поля, выберите разные основной и резервный профили и включите наблюдение за обоими.'));updateGate();return;}
      if(step<2){step++;show();return;}
      busy=true;body.setAttribute('aria-busy','true');progress.textContent=bi('Saving settings…','Сохранение настроек…');Array.from(actions.children).forEach(function(node){node.disabled=true;});
      var save=kind==='system'?rpc.declare({object:'homensai-vpn',method:'setup_system',params:['source','target','interval','duration','session_loss','servers'],expect:{}})(draft.source,draft.target,draft.interval,draft.duration,draft.session_loss,draft.servers):rpc.declare({object:'homensai-vpn',method:'setup_telegram',params:['token','chat','enabled','interval','schedule','hour','weekly','monthly','items'],expect:{}})(tg.token,tg.chat,tg.enabled,tg.interval,tg.schedule,tg.hour,tg.weekly,tg.monthly,tgItemsToSetting(tg.items));
      return save.then(function(result){if(!result||result.saved!==true){notify(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code)?result.code:'SETUP-SAVE-FAILED');return;}tg.token='';closed=true;ui.hideModal();notify('SETUP-SAVED: settings stored; automatic switching was not started.');window.location.reload();}).catch(function(){notify('SETUP-SAVE-FAILED: no confirmed result.');}).finally(function(){busy=false;body.setAttribute('aria-busy','false');progress.textContent='';Array.from(actions.children).forEach(function(node){node.disabled=false;});updateGate();});
    }},step<2?bi('Next','Далее'):bi('Save configuration','Сохранить настройки')));
    if(kind==='system'&&setupCheck!=='passed')body.querySelectorAll('input,select').forEach(function(node){node.disabled=true;});
    body.appendChild(actions);updateGate();ui.showModal(kind==='system'?bi('System setup wizard','Мастер настройки системы'):bi('Telegram channel wizard','Мастер Telegram-канала'),[body]);
  }
  show();
  if(kind==='system')rpc.declare({object:'homensai-vpn',method:'setup_check',expect:{}})().then(function(result){if(closed)return;setupCheck=result&&result.passed===true?'passed':'failed';show();}).catch(function(){if(closed)return;setupCheck='failed';show();});
}
