/* One reviewed transaction for first entry and Settings. Drafts live only in this page session;
   router completion is independent of browser storage, terms acceptance and profile setup. */
var ONBOARDING_VERSION=1,ONBOARDING_SESSION=null,HV_ROUTER_DISPLAY=null;
var ONBOARDING_DEFER_USED=false;
function onboardingEntryDeferred(){
  // An explicit recovery link bypasses only this entry, never router completion or terms.
  // Scrub before rendering so a normal reload offers the unfinished wizard again.
  if(ONBOARDING_DEFER_USED)return false;
  try{
    var url=new URL(window.location.href),values=url.searchParams.getAll('onboarding');
    if(values.length!==1||values[0]!=='defer')return false;
    url.searchParams.delete('onboarding');window.history.replaceState(null,'',url.toString());
    ONBOARDING_DEFER_USED=true;return true;
  }catch(e){return false;}
}
// Stop is independent of draft navigation and the configuration writer. Only its own
// pending RPC disables it; a recreated step must unlock when that same request settles.
var ONBOARDING_STOP={pending:false,button:null};
function onboardingEmergencyControl(){
  var button=E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','data-onboarding-action':'emergency-stop','click':function(){
    if(ONBOARDING_STOP.pending)return;
    ONBOARDING_STOP.pending=true;button.disabled=true;
    if(ONBOARDING_STOP.button)ONBOARDING_STOP.button.disabled=true;
    var request;
    try{request=rpc.declare({object:'homensai-vpn',method:'native_stop',expect:{}})();}catch(e){request=Promise.reject(e);}
    return Promise.resolve(request).then(function(result){
      ui.addNotification(null,autoRequestAcknowledged(result,true)?E('p',{},bi('Stop requested. Monitoring continues.','Остановка запрошена. Мониторинг продолжается.')):autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
    }).catch(function(){ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){
      ONBOARDING_STOP.pending=false;button.disabled=false;
      if(ONBOARDING_STOP.button)ONBOARDING_STOP.button.disabled=false;
    });
  }},bi('Emergency Stop Auto','Аварийный стоп Auto'));
  ONBOARDING_STOP.button=button;button.disabled=ONBOARDING_STOP.pending;
  return E('div',{'class':'hv-auto-emergency'},[button,E('small',{},bi('Cancels Auto and pending starts. Monitoring continues. Available on every setup step, including while saving.','Отменяет Auto и ожидающие запросы запуска. Мониторинг продолжается. Доступен на каждом шаге, в том числе при сохранении.'))]);
}
var ONBOARDING_STEPS=['appearance','monitor','system','servers','recovery','speed','telegram','review'];
// The aggregate editor preserves the monitor's existing 1–32 profile capacity.
// The older independent monitor wizard intentionally retains its own 1–16 contract.
FOOL_RANGES['onboarding.probe_limit']=[1,32,'',''];
function onboardingComplete(inventory){
  var s=inventory&&inventory.settings;
  return !!s&&!inventory.error&&s.onboarding_complete===true&&s.onboarding_version===ONBOARDING_VERSION;
}
function onboardingDisplayDefaults(inventory){
  var s=inventory&&inventory.settings||{};
  HV_ROUTER_DISPLAY={language:s.appearance_language,theme:s.appearance_theme,design:s.appearance_design};
  var browserLanguage=null;
  try{browserLanguage=window.localStorage.getItem('homensai-vpn-language');}catch(e){}
  if(!requestedLanguage&&browserLanguage!=='en'&&browserLanguage!=='ru'&&/^(en|ru)$/.test(s.appearance_language||''))locale=s.appearance_language;
}
function onboardingDraft(inventory){
  var s=inventory.settings||{},profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],servers=Array.isArray(inventory.servers)?inventory.servers:[];
  function value(key,fallback){return s[key]==null?fallback:s[key];}
  var recovery={},speed={enabled:!!s.speed_enabled,auto_new:!!s.speed_auto_new};
  var recoveryDefaults={failures:3,successes:2,cooldown:180,min_dwell:180,return_policy:'healthy_primary',primary_successes:3,primary_stable:60};
  Object.keys(recoveryDefaults).forEach(function(k){recovery[k]=value('recovery_'+k,recoveryDefaults[k]);});
  var speedDefaults={budget_mib:8,duration:5,streams:2,daily_mib:128,busy_mbps:2};
  Object.keys(speedDefaults).forEach(function(k){speed[k]=value('speed_'+k,speedDefaults[k]);});
  return {
    appearance:{language:s.appearance_language||locale,theme:s.appearance_theme||storedTheme(),design:s.appearance_design||currentDesign()},
    monitor:{interval:value('interval',30),checkpoint:value('checkpoint',900),probe_limit:value('probe_limit',16),planning_enabled:!!s.plan_enabled},
    system:{defer_pair:!!s.onboarding_pair_deferred,source:s.plan_source||'',target:s.plan_target||'',duration:value('native_duration',10),session_loss:!!s.native_session_loss,
      servers:profiles.map(function(p){var row=servers.filter(function(r){return r.profile===p.id;})[0]||{};return {profile:p.id,name:row.name==null?p.name:row.name,channel:row.channel==null?'default':row.channel,priority:row.priority==null?100:row.priority,enabled:row.enabled!==false};})},
    recovery:recovery,speed:speed,
    telegram:{configure:false,token:'',chat:s.telegram_destination||'',enabled:!!s.telegram_enabled,interval:value('telegram_interval',60),schedule:value('telegram_schedule','interval'),hour:value('telegram_hour',7),weekly:s.telegram_weekly!==false,monthly:s.telegram_monthly!==false,items:tgItemsFromSetting(s.telegram_items)}
  };
}
function onboardingPayload(draft){
  // Copy explicit allowlisted objects: neither secret drafts nor extra UI state become RPC fields.
  var system={defer_pair:draft.system.defer_pair,source:draft.system.defer_pair?'':draft.system.source,target:draft.system.defer_pair?'':draft.system.target,duration:Number(draft.system.duration),session_loss:draft.system.session_loss,
    servers:draft.system.servers.map(function(s){return {profile:s.profile,name:s.name,channel:s.channel,priority:Number(s.priority),enabled:s.enabled};})};
  var monitor={interval:Number(draft.monitor.interval),checkpoint:Number(draft.monitor.checkpoint),probe_limit:Number(draft.monitor.probe_limit),planning_enabled:draft.monitor.planning_enabled};
  var recovery={},speed={},telegram={configure:false};
  ['failures','successes','cooldown','min_dwell','primary_successes','primary_stable'].forEach(function(k){recovery[k]=Number(draft.recovery[k]);});recovery.return_policy=draft.recovery.return_policy;
  ['enabled','auto_new'].forEach(function(k){speed[k]=draft.speed[k];});['budget_mib','duration','streams','daily_mib','busy_mbps'].forEach(function(k){speed[k]=Number(draft.speed[k]);});
  if(draft.telegram.configure){telegram={configure:true,token:draft.telegram.token,chat:draft.telegram.chat,enabled:draft.telegram.enabled,interval:Number(draft.telegram.interval),schedule:draft.telegram.schedule,hour:Number(draft.telegram.hour),weekly:draft.telegram.weekly,monthly:draft.telegram.monthly,items:tgItemsToSetting(draft.telegram.items)};}
  return [system,monitor,recovery,speed,telegram,{language:draft.appearance.language,theme:draft.appearance.theme,design:draft.appearance.design}];
}
function onboardingApplyAppearance(appearance){
  HV_ROUTER_DISPLAY=appearance;locale=appearance.language;
  try{window.localStorage.setItem('homensai-vpn-language',appearance.language);window.localStorage.setItem('homensai-vpn-theme',appearance.theme);}catch(e){}
  saveDesign(appearance.design);applyTheme(appearance.theme);
  try{var url=new URL(window.location.href);if(url.searchParams.has('lang')){url.searchParams.set('lang',appearance.language);window.history.replaceState(null,'',url.toString());}}catch(e){}
}
function renderOnboarding(inventory,status,firstRun){
  var profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],settings=inventory.settings||{};
  // An inventory change discards only a closed, stale draft. Pending writes are always one shared session.
  var identity=JSON.stringify([settings,inventory.servers||[],profiles]);
  if(!ONBOARDING_SESSION||ONBOARDING_SESSION.identity!==identity&&!ONBOARDING_SESSION.busy)ONBOARDING_SESSION={identity:identity,draft:onboardingDraft(inventory),step:0,paused:false,busy:false,error:''};
  var session=ONBOARDING_SESSION,draft=session.draft,host=E('div',{'class':'hv-app hv-onboarding','data-hv-onboarding':'1','data-hv-design':currentDesign(),'style':'width:100%;min-width:0;box-sizing:border-box;overflow-wrap:anywhere'});
  var headings=[bi('Language and appearance','Язык и оформление'),bi('Monitoring','Мониторинг'),bi('Existing VPN profiles and trial preferences','Существующие VPN и параметры теста'),bi('Server names and priorities','Названия и приоритеты серверов'),bi('Recovery rules','Правила восстановления'),bi('Optional speed tests','Необязательные тесты скорости'),bi('Optional Telegram reports','Необязательные отчёты Telegram'),bi('Review all settings','Проверьте все настройки')];
  var recoveryLabels={failures:bi('Failures before switching','Сбоев до переключения'),successes:bi('Reserve successes required','Успешных проверок резерва'),cooldown:bi('Cooldown, seconds','Пауза, секунд'),min_dwell:bi('Minimum dwell, seconds','Минимальное время работы, секунд'),primary_successes:bi('Primary successes before return','Успешных проверок основного перед возвратом'),primary_stable:bi('Primary stable interval, seconds','Период стабильности основного, секунд')};
  var speedLabels={enabled:bi('Speed-test feature enabled','Функция тестов скорости включена'),auto_new:bi('Automatic tests for new profiles','Автоматические тесты новых профилей'),budget_mib:bi('Traffic per test, MiB','Трафик на тест, МиБ'),duration:bi('Test duration, seconds','Длительность теста, секунд'),streams:bi('Parallel streams','Параллельных потоков'),daily_mib:bi('Daily traffic budget, MiB','Суточный лимит трафика, МиБ'),busy_mbps:bi('Busy threshold, Mbps','Порог занятости, Мбит/с')};
  function notify(code){ui.addNotification(null,E('p',{},code));}
  function clear(){while(host.firstChild)host.removeChild(host.firstChild);}
  function show(){
    clear();host.setAttribute('data-step',session.paused?'paused':ONBOARDING_STEPS[session.step]);
    var card=E('section',{'class':'hv-chart-card hv-terms-card','style':'min-width:0;max-width:100%;box-sizing:border-box'}),checks=[],captures=[],next;
    function capture(){captures.forEach(function(f){f();});}
    function valid(){capture();return foolGate(null,checks);}
    function gate(){if(next)next.disabled=session.busy||!valid();}
    function field(title,node){return E('label',{'class':'hv-wizard-field'},[E('span',{},title),node]);}
    function input(obj,key,path,type){var n=E('input',{'type':type||'text','data-onboarding-field':path,'style':'max-width:100%;box-sizing:border-box'});n.value=obj[key];n.setAttribute('aria-label',path);captures.push(function(){obj[key]=n.value;});n.addEventListener('input',gate);n.addEventListener('change',gate);return n;}
    function number(title,obj,key,path,range){var n=input(obj,key,path,'number'),row=foolNumberRow(title,n,range,gate);checks.push(row.check);card.appendChild(row.row);return n;}
    function text(title,obj,key,path,kind,required){
      var n=input(obj,key,path,kind==='token'?'password':'text'),row=foolTextRow(title,n,kind,gate,required);
      n.setAttribute('autocomplete',kind==='token'?'new-password':'off');
      if(kind==='name'||kind==='channel'){
        // Backend labels count Unicode code points, whereas HTML maxlength counts UTF-16 units.
        n.setAttribute('maxlength','128');
        checks.push(function(){
          var length=Array.from(n.value).length,forbidden=/[\p{C}\p{Zl}\p{Zp}]/u.test(n.value),message='';
          if(forbidden)message=bi('Invisible, formatting and private-use characters are not allowed.','Невидимые, форматирующие и служебные символы не допускаются.');
          else if(!n.value.trim()||length>64)message=bi('Enter 1 to 64 characters, with at least one non-space character.','Введите от 1 до 64 символов, включая хотя бы один непробельный символ.');
          row.error.textContent=message;n.setAttribute('aria-invalid',message?'true':'false');
          if(n.classList){if(message)n.classList.add('hv-fool-invalid');else n.classList.remove('hv-fool-invalid');}
          return !message;
        });
      }else checks.push(row.check);
      card.appendChild(row.row);return n;
    }
    function toggle(title,obj,key,path,after){var n=E('input',{'type':'checkbox','data-onboarding-field':path,'aria-label':title});n.checked=obj[key]===true;captures.push(function(){obj[key]=n.checked;});n.addEventListener('change',function(){obj[key]=n.checked;if(after)after(n.checked);gate();});card.appendChild(field(title,n));return n;}
    function select(title,obj,key,path,options){var n=E('select',{'data-onboarding-field':path,'aria-label':title,'style':'max-width:100%'});options.forEach(function(o){n.appendChild(E('option',{value:o[0]},o[1]));});if(!options.some(function(o){return o[0]===obj[key];}))n.appendChild(E('option',{value:obj[key]},bi('Saved value needs review: ','Сохранённое значение требует проверки: ')+obj[key]));n.value=obj[key];captures.push(function(){obj[key]=n.value;});n.addEventListener('change',gate);checks.push(function(){return options.some(function(o){return o[0]===n.value;});});card.appendChild(field(title,n));return n;}
    function note(en,ru){card.appendChild(E('p',{},bi(en,ru)));}
    function action(key,label,fn){return E('button',{'type':'button','class':'cbi-button'+(key==='next'||key==='save'?' cbi-button-action':''),'data-onboarding-action':key,'click':fn},label);}
    var model=identityModel(status||{});
    card.appendChild(E('header',{'class':'hv-page-header','style':'flex-wrap:wrap;gap:12px'},[E('p',{'class':'hv-eyebrow'},bi('HomenS.AI Auto VPN · complete setup','HomenS.AI Auto VPN · общая настройка')),E('span',{'class':'hv-version'},'v'+(model.agent||model.uiAgent))]));
    card.appendChild(E('h1',{},session.paused?bi('Setup paused — draft kept','Настройка приостановлена — черновик сохранён'):headings[session.step]));
    card.appendChild(onboardingEmergencyControl());
    if(firstRun){
      var dashboardUrl=new URL(window.location.href);dashboardUrl.searchParams.set('onboarding','defer');dashboardUrl.hash='overview';
      card.appendChild(E('p',{},E('a',{'href':dashboardUrl.toString(),'target':'_blank','rel':'noopener noreferrer','class':'cbi-button','data-onboarding-action':'open-dashboard','style':'white-space:normal;display:inline-block;max-width:100%;box-sizing:border-box'},bi('Open dashboard and recovery controls — setup remains incomplete','Открыть панель и средства восстановления — настройка не завершена'))));
      note('Opens in a new tab with Stop and return-to-primary controls. This draft stays here. The link saves no settings; a normal reload offers unfinished setup again.','Откроется новая вкладка с остановкой и возвратом на основной VPN. Черновик останется здесь. Ссылка не сохраняет настройки; обычное обновление страницы снова предложит незавершённый мастер.');
    }
    if(session.paused){
      note('Nothing was saved. This draft stays in this page only; closing or reloading the page discards it. Setup will open again until a complete reviewed save succeeds.','Ничего не сохранено. Черновик остаётся только на этой странице; закрытие или обновление страницы удалит его. Мастер откроется снова до успешного сохранения всех настроек.');
      card.appendChild(action('resume',bi('Resume setup','Продолжить настройку'),function(){session.paused=false;show();}));
    }else{
      card.appendChild(E('p',{'class':'hv-eyebrow'},bi('Step ','Шаг ')+(session.step+1)+' / '+ONBOARDING_STEPS.length));
      if(session.step===0){
        note('These defaults are saved on the router. The language, theme and design controls in Settings can override them in one browser. Your current appearance changes only after the final save.','Эти значения сохраняются на роутере. Отдельные переключатели языка, темы и оформления в настройках могут переопределить их в одном браузере. Текущее оформление изменится только после общего сохранения.');
        select(bi('Default language','Язык по умолчанию'),draft.appearance,'language','appearance.language',[['en','English'],['ru','Русский']]);
        select(bi('Default theme','Тема по умолчанию'),draft.appearance,'theme','appearance.theme',[['system',bi('Follow system','Как в системе')],['light',bi('Light','Светлая')],['dark',bi('Dark','Тёмная')]]);
        select(bi('Default design','Оформление по умолчанию'),draft.appearance,'design','appearance.design',HV_DESIGNS.map(function(d){return [d.key,bi(d.name[0],d.name[1])];}));
        note('Reporting timezone: Europe/Berlin. Router WAN, Wi-Fi and VPN keys are edited on the router VPN/network pages.','Часовой пояс отчётов: Europe/Berlin. WAN, Wi-Fi и ключи VPN изменяются на страницах сети и VPN роутера.');
      }else if(session.step===1){
        note('Monitoring service on/off remains a separate action. These preferences do not start Auto, a speed test or an inactive VPN. Checkpoints write statistics to flash.','Включение службы мониторинга остаётся отдельным действием. Эти параметры не запускают Auto, тест скорости или неактивный VPN. Checkpoint записывает статистику во flash.');
        number(bi('Probe interval, seconds','Интервал проверки, секунд'),draft.monitor,'interval','monitor.interval','monitor.interval');
        number(bi('Checkpoint interval, seconds','Интервал checkpoint, секунд'),draft.monitor,'checkpoint','monitor.checkpoint','monitor.checkpoint');
        number(bi('Profile limit per round','Лимит профилей за раунд'),draft.monitor,'probe_limit','monitor.probe_limit','onboarding.probe_limit');
        toggle(bi('Enable read-only planning','Включить планирование без применения'),draft.monitor,'planning_enabled','monitor.planning_enabled');
      }else if(session.step===2){
        note('Choose two distinct installed profiles, or explicitly defer the pair. No VPN credentials are imported or displayed. Trial preferences do not start a trial or certify Auto.','Выберите два разных установленных профиля или явно отложите пару. Ключи VPN не импортируются и не показываются. Параметры теста не запускают тест и не подтверждают готовность Auto.');
        var vpnUrl=resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);
        if(vpnUrl)card.appendChild(E('p',{},[E('a',{'href':vpnUrl,'target':'_blank','rel':'noopener noreferrer','data-onboarding-link':'router-vpn'},bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗')),bi(' · Add profiles there, then reload this page. Reloading discards this unsaved draft.',' · Добавьте профили там, затем обновите эту страницу. При обновлении несохранённый черновик будет удалён.')]));
        if(profiles.length<2)note('Fewer than two profiles are installed. Defer the pair to finish other settings; add profiles later on the router and return to Settings.','Установлено меньше двух профилей. Отложите пару, чтобы закончить остальные настройки; затем добавьте профили на роутере и вернитесь в настройки.');
        var pairNote=E('p',{'role':'status'});card.appendChild(pairNote);
        toggle(bi('Defer the VPN pair and turn off read-only planning','Отложить пару VPN и выключить планирование'),draft.system,'defer_pair','system.defer_pair',function(on){if(on)draft.monitor.planning_enabled=false;pairNote.textContent=on?bi('Pair deferred; planning will be off. Existing router profiles are retained.','Пара отложена; планирование будет выключено. Существующие профили роутера сохраняются.'):'';});
        var choices=[['',bi('Choose an existing profile','Выберите существующий профиль')]].concat(profiles.map(function(p){return [p.id,p.name+' · '+p.protocol];}));
        select(bi('Primary VPN','Основной VPN'),draft.system,'source','system.source',choices);
        select(bi('Reserve VPN','Резервный VPN'),draft.system,'target','system.target',choices);
        checks.push(function(){var ok=draft.system.defer_pair?draft.monitor.planning_enabled===false:!!draft.system.source&&draft.system.source!==draft.system.target&&profiles.some(function(p){return p.id===draft.system.source;})&&profiles.some(function(p){return p.id===draft.system.target;});pairNote.textContent=ok?'':bi('Choose two different installed profiles, or defer the pair and disable planning.','Выберите два разных установленных профиля или отложите пару и выключите планирование.');return ok;});
        // Missing saved IDs must not block an explicitly deferred pair.
        checks=checks.slice(-1);
        number(bi('Bounded trial duration, minutes','Длительность ограниченного теста, минут'),draft.system,'duration','system.duration','system.duration');
        toggle(bi('Allow calls/sessions to reconnect during a later trial','Разрешить переподключение звонков/сессий при будущем тесте'),draft.system,'session_loss','system.session_loss');
      }else if(session.step===3){
        note('These names, groups and priorities are application metadata. They do not alter live VPN routes. Every installed profile is listed.','Эти названия, группы и приоритеты — метаданные приложения. Они не изменяют текущие маршруты VPN. Показаны все установленные профили.');
        if(!draft.system.servers.length)note('No profiles yet. Metadata can be edited here after profiles are added on the router.','Профилей пока нет. Метаданные можно будет изменить здесь после добавления профилей на роутере.');
        draft.system.servers.forEach(function(row,i){
          card.appendChild(E('h3',{},row.profile));
          text(bi('Display name','Название'),row,'name','servers.'+i+'.name','name');text(bi('Channel group','Группа канала'),row,'channel','servers.'+i+'.channel','channel');
          number(bi('Priority','Приоритет'),row,'priority','servers.'+i+'.priority','system.priority');toggle(bi('Monitor this profile','Наблюдать этот профиль'),row,'enabled','servers.'+i+'.enabled');
        });
        var metadataError=E('p',{'role':'alert'});card.appendChild(metadataError);checks.push(function(){var ok=(!draft.system.defer_pair?draft.system.servers.some(function(r){return r.profile===draft.system.source&&r.enabled;})&&draft.system.servers.some(function(r){return r.profile===draft.system.target&&r.enabled;}):true);metadataError.textContent=ok?'':bi('Both selected profiles must be enabled for monitoring. Go Back to defer or change the pair.','Оба выбранных профиля должны участвовать в мониторинге. Вернитесь назад, чтобы изменить или отложить пару.');return ok;});
      }else if(session.step===4){
        Object.keys(recoveryLabels).forEach(function(k){number(recoveryLabels[k],draft.recovery,k,'recovery.'+k,'recovery.'+k);});
        select(bi('Return policy','Политика возврата'),draft.recovery,'return_policy','recovery.return_policy',[['healthy_primary',bi('Return after stable primary health','Возврат после стабильной работы основного')],['hold_reserve',bi('Keep healthy reserve for operator review','Сохранять работающий резерв до решения оператора')]]);
        note('Changing recovery preferences may require a fresh LAN certification before Auto can be started separately.','После изменения правил восстановления может потребоваться новая проверка LAN перед отдельным запуском Auto.');
      }else if(session.step===5){
        note('Optional future speed tests consume traffic. Enabling these preferences does not run a test now.','Необязательные будущие тесты скорости расходуют трафик. Эти настройки не запускают тест сейчас.');
        toggle(bi('Enable speed-test feature','Включить функцию тестов скорости'),draft.speed,'enabled','speed.enabled');toggle(bi('Allow automatic tests for new profiles','Разрешить автоматические тесты новых профилей'),draft.speed,'auto_new','speed.auto_new');
        ['budget_mib','duration','streams','daily_mib','busy_mbps'].forEach(function(k){number(speedLabels[k],draft.speed,k,'speed.'+k,'speed.'+k);});
        var budgetError=E('p',{'role':'alert'});card.appendChild(budgetError);checks.push(function(){var ok=Number(draft.speed.budget_mib)<=Number(draft.speed.daily_mib);budgetError.textContent=ok?'':bi('The daily budget must cover at least one test.','Суточный лимит должен быть не меньше трафика на один тест.');return ok;});
      }else if(session.step===6){
        note('Telegram is optional. Keep existing settings to leave all saved reporting settings and the stored token unchanged. Tokens are never returned or included in the review.','Telegram необязателен. Сохраните существующие параметры, чтобы не менять отчёты и сохранённый токен. Токены не возвращаются и не включаются в обзор.');
        var configure=toggle(bi('Configure Telegram in this save','Настроить Telegram при этом сохранении'),draft.telegram,'configure','telegram.configure',function(){capture();show();});
        if(draft.telegram.configure){
          toggle(bi('Enable Telegram reporting','Включить отчёты Telegram'),draft.telegram,'enabled','telegram.enabled');
          text(bi('Bot token (blank keeps stored token)','Токен бота (пустое поле сохраняет токен)'),draft.telegram,'token','telegram.token','token',false);
          // Empty chat is valid only for a disabled, completely empty optional configuration.
          var chat=input(draft.telegram,'chat','telegram.chat');card.appendChild(field(bi('Chat ID or @channel_name','Chat ID или @channel_name'),chat));
          var telegramError=E('p',{'role':'alert'});card.appendChild(telegramError);checks.push(function(){var tg=draft.telegram,empty=!tg.enabled&&tg.chat===''&&tg.token==='',ok=empty||foolCheckText('chat',tg.chat).ok&&(!tg.enabled||tg.token!==''||settings.telegram_configured===true);telegramError.textContent=ok?'':bi('Enter a valid chat and a new or stored token for enabled reports. To skip setup, disable reports and leave both fields empty.','Для включённых отчётов укажите корректный чат и новый или сохранённый токен. Для пропуска выключите отчёты и оставьте оба поля пустыми.');return ok;});
          number(bi('Report interval, minutes','Интервал отчётов, минут'),draft.telegram,'interval','telegram.interval','telegram.interval');
          select(bi('Report schedule','Расписание отчётов'),draft.telegram,'schedule','telegram.schedule',[['interval',bi('At intervals','По интервалу')],['daily',bi('Daily','Ежедневно')]]);
          number(bi('Daily report hour (Europe/Berlin)','Час ежедневного отчёта (Europe/Berlin)'),draft.telegram,'hour','telegram.hour','telegram.hour');
          toggle(bi('Weekly summary','Недельная сводка'),draft.telegram,'weekly','telegram.weekly');toggle(bi('Monthly summary','Месячная сводка'),draft.telegram,'monthly','telegram.monthly');
          TG_ITEMS.forEach(function(item){var ref={on:draft.telegram.items.indexOf(item[0])>=0};toggle(bi(item[1],item[2]),ref,'on','telegram.items.'+item[0],function(on){draft.telegram.items=draft.telegram.items.filter(function(id){return id!==item[0];});if(on)draft.telegram.items.push(item[0]);});captures.push(function(){draft.telegram.items=draft.telegram.items.filter(function(id){return id!==item[0];});if(ref.on)draft.telegram.items.push(item[0]);});});
          card.appendChild(telegramTokenHelp());
        }
      }else{
        note('Review every section. One save writes application preferences and the first-run completion marker together on the router. This does not start Auto; legal terms remain a separate decision.','Проверьте каждый раздел. Одно сохранение записывает параметры приложения и отметку первого запуска вместе на роутере. Это не запускает Auto; условия использования принимаются отдельно.');
        function review(title,rows){card.appendChild(E('h3',{},title));card.appendChild(E('dl',{'style':'margin:0;overflow-wrap:anywhere'},rows.reduce(function(nodes,row){return nodes.concat([E('dt',{},row[0]),E('dd',{},String(row[1]))]);},[])));}
        function yes(v){return v?bi('Yes','Да'):bi('No','Нет');}
        review(headings[0],[[bi('Language / theme / design','Язык / тема / оформление'),draft.appearance.language+' / '+draft.appearance.theme+' / '+draft.appearance.design],[bi('Reporting timezone','Часовой пояс отчётов'),'Europe/Berlin']]);
        review(headings[1],[[bi('Probe / checkpoint (seconds) / profiles per round','Проверка / checkpoint (секунд) / профилей за раунд'),draft.monitor.interval+' / '+draft.monitor.checkpoint+' / '+draft.monitor.probe_limit],[bi('Planning enabled','Планирование включено'),yes(draft.monitor.planning_enabled)]]);
        review(headings[2],[[bi('Primary / reserve','Основной / резерв'),draft.system.defer_pair?bi('Deferred; planning off','Отложено; планирование выключено'):draft.system.source+' / '+draft.system.target],[bi('Trial minutes / sessions may reconnect','Тест, минут / сессии могут переподключаться'),draft.system.duration+' / '+yes(draft.system.session_loss)]]);
        review(headings[3],draft.system.servers.map(function(s){return [s.profile,s.name+' / '+s.channel+' / '+s.priority+' / '+yes(s.enabled)];}));
        review(headings[4],Object.keys(recoveryLabels).map(function(k){return [recoveryLabels[k],draft.recovery[k]];}).concat([[bi('Return policy','Политика возврата'),draft.recovery.return_policy==='healthy_primary'?bi('Return after stable primary health','Возврат после стабильной работы основного'):bi('Keep healthy reserve for operator review','Сохранять работающий резерв до решения оператора')]]));
        review(headings[5],Object.keys(speedLabels).map(function(k){return [speedLabels[k],typeof draft.speed[k]==='boolean'?yes(draft.speed[k]):draft.speed[k]];}));
        review(headings[6],!draft.telegram.configure?[[bi('Telegram','Telegram'),bi('Keep all existing settings and token','Сохранить все существующие настройки и токен')]]:[[bi('Reports enabled','Отчёты включены'),yes(draft.telegram.enabled)],[bi('Destination','Получатель'),draft.telegram.chat||bi('Not configured','Не настроен')],[bi('Token','Токен'),draft.telegram.token?bi('New token entered (hidden)','Введён новый токен (скрыт)'):settings.telegram_configured?bi('Stored token retained (hidden)','Сохранённый токен остаётся (скрыт)'):bi('No new token','Новый токен не задан')],[bi('Interval (minutes) / schedule / daily hour','Интервал (минут) / расписание / час'),draft.telegram.interval+' / '+(draft.telegram.schedule==='daily'?bi('Daily','Ежедневно'):bi('At intervals','По интервалу'))+' / '+draft.telegram.hour],[bi('Weekly / monthly','Недельная / месячная'),yes(draft.telegram.weekly)+' / '+yes(draft.telegram.monthly)],[bi('Contents','Содержимое'),TG_ITEMS.filter(function(i){return draft.telegram.items.indexOf(i[0])>=0;}).map(function(i){return bi(i[1],i[2]);}).join(', ')||bi('None','Ничего')]]);
      }
      if(session.error)card.appendChild(E('p',{'role':'alert','data-onboarding-error':'1'},session.error));
      var actions=[action('cancel',bi('Cancel — keep draft','Отмена — оставить черновик'),function(){if(session.busy)return;capture();if(firstRun){session.paused=true;show();}else ui.hideModal();})];
      if(session.step)actions.push(action('back',bi('Back','Назад'),function(){if(session.busy)return;capture();session.step--;session.error='';show();}));
      next=action(session.step===7?'save':'next',session.step===7?bi('Save all settings','Сохранить все настройки'):bi('Next','Далее'),function(){
        if(session.busy||!valid())return;
        if(session.step<7){session.step++;session.error='';show();return;}
        session.busy=true;gate();actions.forEach(function(n){n.disabled=true;});
        var payload=onboardingPayload(draft),request;
        try{request=rpc.declare({object:'homensai-vpn',reject:true,method:'setup_onboarding',params:['system','monitor','recovery','speed','telegram','appearance'],expect:{}}).apply(null,payload);}catch(e){request=Promise.reject(e);}
        return Promise.resolve(request).then(function(result){
          if(result&&result.saved===true&&result.onboarding_complete===true&&result.onboarding_version===ONBOARDING_VERSION){
            draft.telegram.token='';onboardingApplyAppearance(draft.appearance);ONBOARDING_SESSION=null;if(!firstRun)ui.hideModal();window.location.reload();return;
          }
          session.error=(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code)?result.code:'ONBOARDING-SAVE-UNCONFIRMED')+' · '+bi('Settings were not confirmed. Your draft remains open. Review or refresh the current state before retrying.','Сохранение не подтверждено. Черновик остаётся открытым. Проверьте настройки или обновите текущее состояние перед повтором.');
        }).catch(function(){session.error='ONBOARDING-SAVE-UNCONFIRMED · '+bi('No confirmation received. Your draft remains open; refresh to check the router before retrying.','Подтверждение не получено. Черновик остаётся открытым; обновите страницу, чтобы проверить состояние роутера перед повтором.');}).then(function(){session.busy=false;if(ONBOARDING_SESSION===session)show();});
      });
      actions.push(next);gate();actions.forEach(function(n){if(session.busy)n.disabled=true;});card.appendChild(E('div',{'class':'hv-wizard-actions','style':'display:flex;flex-wrap:wrap;gap:8px'},actions));
    }
    host.appendChild(card);host.appendChild(renderAttribution(status||{}));
    var footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');host.appendChild(footer);
  }
  applyTheme(storedTheme());
  if(firstRun){['style/css/tokens.css','style/css/fonts.css','style/css/author.css','ui15.css'].forEach(function(path){host.appendChild(E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/'+path)}));});}
  // Stylesheet links belong outside the replaced step content.
  var shell=firstRun?E('div',{},[]):host;
  if(firstRun){while(host.firstChild)shell.appendChild(host.firstChild);shell.appendChild(host);}
  show();return shell;
}
function renderOnboardingGate(inventory,status){return renderOnboarding(inventory,status,true);}
function openOnboardingSettings(inventory,status){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE'));return;}
  if(ONBOARDING_SESSION&&ONBOARDING_SESSION.busy)return;
  if(ONBOARDING_SESSION)ONBOARDING_SESSION.paused=false;
  ui.showModal(bi('All application settings','Все настройки приложения'),[renderOnboarding(inventory,status,false)]);
}
