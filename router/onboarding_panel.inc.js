/* One reviewed transaction for first entry and Settings. Drafts live only in this page session;
   router completion is independent of browser storage, terms acceptance and profile setup. */
var ONBOARDING_VERSION=1,ONBOARDING_SESSION=null,HV_ROUTER_DISPLAY=null;
// A saved provider profile is not a second client tunnel. Match inventory's
// exact configured binding; ambiguous/missing bindings never become choices.
function onboardingPairChannels(profiles,settings){
  var ids=Object.create(null),logicals=Object.create(null),rows=[];
  (Array.isArray(profiles)?profiles:[]).slice(0,400).forEach(function(p){
    if(!p||typeof p.id!=='string')return;ids[p.id]=(ids[p.id]||0)+1;
    if(['wireguard','openvpn'].indexOf(p.protocol)<0||!p.id.startsWith(p.protocol+':')||!/^[A-Za-z0-9_.:-]{1,96}$/.test(p.id)||typeof p.interface!=='string'||!/^[A-Za-z0-9_.-]{1,64}$/.test(p.interface)||p.vendor_tunnel_id!==p.protocol+':'+p.interface||p.section!==undefined&&p.id!==p.protocol+':'+p.section)return;
    logicals[p.interface]=(logicals[p.interface]||0)+1;rows.push(p);
  });
  var mt3000=(settings||{}).detected_router_model==='mt3000'||(settings||{}).pair_auto_mode==='router-probed-ipv4';
  return rows.filter(function(p){return ids[p.id]===1&&logicals[p.interface]===1&&(!mt3000||(p.protocol==='wireguard'&&p.interface==='wgclient1'||p.protocol==='openvpn'&&p.interface==='ovpnclient1'));});
}
function onboardingPairChannelLabel(p){return (p.protocol==='wireguard'?'WireGuard':'OpenVPN')+' · '+(p.name||p.id);}
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
// The wizard exposes the same Auto power button, independent of its save lock.
function onboardingAutoControl(status,inventory){
  var power=renderAutoPowerControl(status||{},inventory).button;
  power.setAttribute('data-onboarding-action','auto-power');
  return E('div',{'class':'hv-onboarding-auto'},[power,E('span',{},bi('Auto · press to stop or cancel startup','Auto · нажмите для остановки или отмены запуска'))]);
}
var ONBOARDING_STEPS=['appearance','monitor','system','servers','recovery','speed','telegram','review'];
// Three user-facing groups retain every existing internal validation stage.
function onboardingGroup(step){return step<2?0:step<7?1:2;}
function onboardingGroupLabel(step){var labels=[bi('Compatibility and preferences','Совместимость и предпочтения'),bi('VPN pair and optional settings','Пара VPN и дополнительные настройки'),bi('Review and save','Проверка и сохранение')];return labels[onboardingGroup(step)];}
// The aggregate editor preserves the monitor's existing 1–32 profile capacity.
// The older independent monitor wizard intentionally retains its own 1–16 contract.
FOOL_RANGES['onboarding.probe_limit']=[1,32,'',''];
function onboardingComplete(inventory){
  var s=inventory&&inventory.settings;
  return !!s&&!inventory.error&&s.onboarding_complete===true&&s.onboarding_version===ONBOARDING_VERSION;
}
function onboardingDisplayDefaults(inventory){
  var s=inventory&&inventory.settings||{};
  HV_DETECTED_ROUTER_MODEL=s.detected_router_model||'unknown';
  HV_ROUTER_DISPLAY={language:s.appearance_language,theme:s.appearance_theme,design:'b'};
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
    appearance:{language:s.appearance_language||locale,theme:s.appearance_theme||storedTheme(),design:'b',router_model:s.router_model||'auto'},
    monitor:{interval:value('interval',30),checkpoint:value('checkpoint',900),probe_limit:value('probe_limit',16),planning_enabled:!!s.plan_enabled,live_log_limit:value('live_log_limit',2000),history_days:value('history_days',7)},
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
  var monitor={interval:Number(draft.monitor.interval),checkpoint:Number(draft.monitor.checkpoint),probe_limit:Number(draft.monitor.probe_limit),planning_enabled:draft.monitor.planning_enabled,live_log_limit:Number(draft.monitor.live_log_limit),history_days:Number(draft.monitor.history_days)};
  var recovery={},speed={},telegram={configure:false};
  ['failures','successes','cooldown','min_dwell','primary_successes','primary_stable'].forEach(function(k){recovery[k]=Number(draft.recovery[k]);});recovery.return_policy=draft.recovery.return_policy;
  ['enabled','auto_new'].forEach(function(k){speed[k]=draft.speed[k];});['budget_mib','duration','streams','daily_mib','busy_mbps'].forEach(function(k){speed[k]=Number(draft.speed[k]);});
  if(draft.telegram.configure){telegram={configure:true,token:draft.telegram.token,chat:draft.telegram.chat,enabled:draft.telegram.enabled,interval:Number(draft.telegram.interval),schedule:draft.telegram.schedule,hour:Number(draft.telegram.hour),weekly:draft.telegram.weekly,monthly:draft.telegram.monthly,items:tgItemsToSetting(draft.telegram.items)};}
  return [system,monitor,recovery,speed,telegram,{language:draft.appearance.language,theme:draft.appearance.theme,design:'b',router_model:draft.appearance.router_model}];
}
function onboardingApplyAppearance(appearance){
  HV_ROUTER_DISPLAY=appearance;locale=appearance.language;
  try{window.localStorage.setItem('homensai-vpn-language',appearance.language);window.localStorage.setItem('homensai-vpn-theme',appearance.theme);}catch(e){}
  saveDesign(appearance.design);applyTheme(appearance.theme);
  try{var url=new URL(window.location.href);if(url.searchParams.has('lang')){url.searchParams.set('lang',appearance.language);window.history.replaceState(null,'',url.toString());}}catch(e){}
}
function renderOnboardingIntro(proceed){
  function diagram(mode){
    var primary=mode==='failover'?'#bd152b':'#12833b',reserve=mode==='failover'?'#12833b':'#a16a00';
    var picture=E('div',{'class':'hv-intro-diagram','role':'img','aria-label':mode==='observe'?bi('Monitoring checks both channels without changing routes','Мониторинг проверяет оба канала без изменения маршрутов'):mode==='failover'?bi('Primary failure: traffic uses the healthy reserve','Отказ основного: трафик идёт через исправный резерв'):bi('Primary restored: traffic can return according to settings','Основной восстановлен: возврат выполняется по настройкам')});
    picture.innerHTML='<svg viewBox="0 0 340 168" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'+
      '<rect x="8" y="65" width="38" height="26" rx="3"/><path d="M27 91v9m-11 0h22M47 78h24"/>'+
      '<rect x="72" y="66" width="40" height="25" rx="5"/><path d="M102 66V51M79 79h3m5 0h3"/>'+
      '<path d="M113 78h20V36h33" stroke="'+primary+'"'+(mode==='failover'?' stroke-dasharray="5 4"':'')+'/>'+
      '<path d="M113 78h20v43h33" stroke="'+reserve+'"'+(mode==='failover'?'':' stroke-dasharray="3 4"')+'/>'+
      '<rect x="167" y="19" width="88" height="34" rx="7" fill="'+primary+'" fill-opacity=".13" stroke="'+primary+'"/>'+
      '<rect x="167" y="104" width="88" height="34" rx="7" fill="'+reserve+'" fill-opacity=".13" stroke="'+reserve+'"/>'+
      '<path d="M256 36h24v42h12" stroke="'+primary+'"'+(mode==='failover'?' stroke-dasharray="5 4"':'')+'/>'+
      '<path d="M256 121h24V78h12" stroke="'+reserve+'"'+(mode==='failover'?'':' stroke-dasharray="3 4"')+'/>'+
      '<circle cx="310" cy="78" r="17"/><path d="M294 78h32m-16-17c-9 9-9 25 0 34m0-34c9 9 9 25 0 34"/>'+
      '<g fill="currentColor" stroke="none" font-family="inherit" font-size="15" text-anchor="middle">'+
      '<text x="27" y="121">'+bi('PC','ПК')+'</text><text x="92" y="121">'+bi('Router','Роутер')+'</text>'+
      '<text x="211" y="42">'+bi('Primary','Основной')+'</text><text x="211" y="127">'+bi('Reserve','Резерв')+'</text>'+
      '<text x="307" y="112">'+bi('Internet','Интернет')+'</text></g>'+
      (mode==='failover'?'<path d="M141 27l14 16m0-16l-14 16" stroke="#bd152b" stroke-width="3"/>':'')+'</svg>';
    return picture;
  }
  var modes=[['observe',bi('1 · Monitoring','1 · Наблюдение'),bi('Checks only; routes stay unchanged','Только проверки, без изменения маршрута')],['failover',bi('2 · Switch to reserve','2 · Переход на резерв'),bi('Primary failed; healthy reserve carries traffic','Основной отказал; трафик идёт через исправный резерв')],['return',bi('3 · Return to primary','3 · Возврат на основной'),bi('Primary is stable again; return follows settings','Основной снова стабилен; возврат — по настройкам')]];
  return E('section',{'class':'hv-chart-card hv-intro','data-onboarding-intro':'1'},[
    E('h1',{},bi('How Auto VPN works','Как работает Auto VPN')),
    E('p',{},bi('Monitoring checks the primary and reserve VPN channels and shows Internet availability. With Auto off, it only observes and never changes the channel on its own. With Auto on, ordinary traffic uses one selected channel while the other stays ready.','Мониторинг проверяет основной и резервный VPN-каналы и показывает доступность Интернета. При выключенном Auto он только наблюдает и самостоятельно не меняет канал. При включённом Auto обычный трафик идёт через один выбранный канал, а второй остаётся готовым.')),
    E('p',{},bi('Repeated primary failures can trigger a switch to a healthy reserve. After stable primary recovery, return follows your settings. A brief failure need not cause a switch. You can also choose a channel manually while Auto remains on; a healthy operator choice stays preferred.','Повторные отказы основного могут вызвать переход на исправный резерв. После устойчивого восстановления основного возврат выполняется по вашим настройкам. Краткий сбой не обязательно вызывает переключение. При работающем Auto можно выбрать канал вручную; исправный выбор оператора сохраняет приоритет.')),
    E('div',{'class':'hv-intro-grid'},modes.map(function(row){return E('figure',{'class':'hv-intro-mode','data-intro-mode':row[0]},[E('h2',{},row[1]),diagram(row[0]),E('figcaption',{},row[2])]);})),
    E('button',{'type':'button','class':'cbi-button cbi-button-action','data-onboarding-action':'intro-ok','click':proceed},bi('OK — open setup','OK — перейти к настройке'))
  ]);
}
function renderOnboarding(inventory,status,firstRun,requestedStep){
  var profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],settings=inventory.settings||{};
  // An inventory change discards only a closed, stale draft. Pending writes are always one shared session.
  var identity=JSON.stringify([settings,inventory.servers||[],profiles]);
  if(!ONBOARDING_SESSION||ONBOARDING_SESSION.identity!==identity&&!ONBOARDING_SESSION.busy)ONBOARDING_SESSION={identity:identity,draft:onboardingDraft(inventory),step:0,paused:false,busy:false,error:''};
  var session=ONBOARDING_SESSION,draft=session.draft,host=E('div',{'class':'hv-app hv-onboarding','data-hv-onboarding':'1','data-hv-design':currentDesign(),'style':'width:100%;min-width:0;box-sizing:border-box;overflow-wrap:anywhere'});
  if(!firstRun&&!session.busy&&ONBOARDING_STEPS.indexOf(requestedStep)>=0){session.step=ONBOARDING_STEPS.indexOf(requestedStep);session.paused=false;}
  function notify(code){ui.addNotification(null,E('p',{},code));}
  function clear(){while(host.firstChild)host.removeChild(host.firstChild);}
  function show(){
    var headings=[bi('Language and appearance','Язык и оформление'),bi('Monitoring','Мониторинг'),bi('Existing VPN profiles and trial preferences','Существующие VPN и параметры теста'),bi('Server names and priorities','Названия и приоритеты серверов'),bi('Recovery rules','Правила восстановления'),bi('Optional speed tests','Необязательные тесты скорости'),bi('Optional Telegram reports','Необязательные отчёты Telegram'),bi('Review all settings','Проверьте все настройки')];
    var recoveryLabels={failures:bi('Failures before switching','Сбоев до переключения'),successes:bi('Reserve successes required','Успешных проверок резерва'),cooldown:bi('Cooldown, seconds','Пауза, секунд'),min_dwell:bi('Minimum dwell, seconds','Минимальное время работы, секунд'),primary_successes:bi('Primary successes before return','Успешных проверок основного перед возвратом'),primary_stable:bi('Primary stable interval, seconds','Период стабильности основного, секунд')};
    var speedLabels={enabled:bi('Speed-test feature enabled','Функция тестов скорости включена'),auto_new:bi('Automatic tests for new profiles','Автоматические тесты новых профилей'),budget_mib:bi('Traffic per test, MiB','Трафик на тест, МиБ'),duration:bi('Test duration, seconds','Длительность теста, секунд'),streams:bi('Parallel streams','Параллельных потоков'),daily_mib:bi('Daily traffic budget, MiB','Суточный лимит трафика, МиБ'),busy_mbps:bi('Busy threshold, Mbps','Порог занятости, Мбит/с')};
    clear();host.setAttribute('data-step',session.paused?'paused':ONBOARDING_STEPS[session.step]);
    if(firstRun&&!session.introSeen&&!onboardingComplete(inventory)){
      host.setAttribute('data-step','intro');host.appendChild(renderOnboardingIntro(function(){session.introSeen=true;show();}));host.appendChild(renderAttribution(status||{}));
      var introFooter=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(introFooter,locale,'platform');host.appendChild(introFooter);return;
    }
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
    function toggle(title,obj,key,path,after){var n=E('input',{'type':'checkbox','data-onboarding-field':path,'aria-label':title});n.checked=obj[key]===true;captures.push(function(){obj[key]=n.checked;});n.addEventListener('change',function(){obj[key]=n.checked;if(after)after(n.checked);gate();});card.appendChild(E('label',{'class':'hv-wizard-field hv-wizard-toggle'},[n,E('span',{},title)]));return n;}
    function select(title,obj,key,path,options){var n=E('select',{'data-onboarding-field':path,'aria-label':title,'style':'max-width:100%'});options.forEach(function(o){n.appendChild(E('option',{value:o[0]},o[1]));});if(!options.some(function(o){return o[0]===obj[key];}))n.appendChild(E('option',{value:obj[key]},bi('Saved value needs review: ','Сохранённое значение требует проверки: ')+obj[key]));n.value=obj[key];captures.push(function(){obj[key]=n.value;});n.addEventListener('change',gate);checks.push(function(){return options.some(function(o){return o[0]===n.value;});});card.appendChild(field(title,n));return n;}
    function note(en,ru){card.appendChild(E('p',{},bi(en,ru)));}
    function action(key,label,fn){return E('button',{'type':'button','class':'cbi-button'+(key==='next'||key==='save'?' cbi-button-action':''),'data-onboarding-action':key,'click':fn},label);}
    var model=identityModel(status||{});
    card.appendChild(E('header',{'class':'hv-page-header','style':'flex-wrap:wrap;gap:12px'},[E('p',{'class':'hv-eyebrow'},bi('HomenS.AI Auto VPN · complete setup','HomenS.AI Auto VPN · общая настройка')),E('span',{'class':'hv-version'},'v'+(model.agent||model.uiAgent))]));
    card.appendChild(E('h1',{},session.paused?bi('Setup paused — draft kept','Настройка приостановлена — черновик сохранён'):headings[session.step]));
    var helpUrl=new URL(window.location.href);helpUrl.searchParams.set('onboarding','defer');helpUrl.searchParams.set('lang',locale);helpUrl.searchParams.set('setup_help','1');helpUrl.hash='help';
    card.appendChild(E('p',{},E('a',{'href':helpUrl.toString(),'target':'_blank','rel':'noopener noreferrer','data-onboarding-action':'setup-help','class':'cbi-button'},bi('Setup help: steps 1–8 with examples','Помощь по настройке: шаги 1–8 с примерами'))));
    if(session.paused||session.step!==0)card.appendChild(onboardingAutoControl(status,inventory));
    if(session.paused){
      note('Nothing was saved. This draft stays in this page only; closing or reloading the page discards it. Setup will open again until a complete reviewed save succeeds.','Ничего не сохранено. Черновик остаётся только на этой странице; закрытие или обновление страницы удалит его. Мастер откроется снова до успешного сохранения всех настроек.');
      card.appendChild(action('resume',bi('Resume setup','Продолжить настройку'),function(){session.paused=false;show();}));
    }else{
      card.appendChild(E('p',{'class':'hv-eyebrow','data-onboarding-group':String(onboardingGroup(session.step)+1)},bi('Group ','Группа ')+(onboardingGroup(session.step)+1)+' / 3 · '+onboardingGroupLabel(session.step)));
      card.appendChild(E('small',{'class':'hv-onboarding-substep'},bi('Section ','Раздел ')+(session.step+1)+' / '+ONBOARDING_STEPS.length));
      if(session.step===0){
        select(bi('Router model','Модель роутера'),draft.appearance,'router_model','appearance.router_model',[['auto',bi('Automatic detection (recommended)','Автоопределение (рекомендуется)')],['mt6000','GL-MT6000 · Flint 2'],['mt3000','GL-MT3000 · Beryl AX']]);
        var detected=settings.detected_router_model||'unknown',modelLabels={mt6000:'GL-MT6000 · Flint 2',mt3000:'GL-MT3000 · Beryl AX'};
        card.appendChild(E('p',{'data-onboarding-device':'detected'},bi('Detected router: ','Обнаружен роутер: ')+(modelLabels[detected]||bi('Unknown','Не определён'))));
        var modelError=E('p',{'role':'alert','data-onboarding-device':'error'});card.appendChild(modelError);
        checks.push(function(){var ok=draft.appearance.router_model==='auto'||draft.appearance.router_model===detected;modelError.textContent=ok?'':bi('The selected model does not match this router. Choose automatic detection or the detected model.','Выбранная модель не соответствует роутеру. Выберите автоопределение или обнаруженную модель.');return ok;});
        note('The model choice is checked against the router hardware. It does not enable Auto or change network settings.','Модель сверяется с оборудованием роутера. Выбор не включает Auto и не меняет сеть.');
        note('These defaults are saved on the router. The language and theme controls in Settings can override them in one browser. Language is previewed immediately. Theme, router defaults apply after the final save.','Эти значения сохраняются на роутере. Отдельные переключатели языка и темы в настройках могут переопределить их в одном браузере. Язык отображается сразу. Тема и настройки роутера применяются после общего сохранения.');
        var languagePreview=select(bi('Default language','Язык по умолчанию'),draft.appearance,'language','appearance.language',[['en','English'],['ru','Русский']]);
        languagePreview.addEventListener('change',function(){if(session.busy)return;capture();locale=draft.appearance.language==='ru'?'ru':'en';show();});
        select(bi('Default theme','Тема по умолчанию'),draft.appearance,'theme','appearance.theme',[['system',bi('Follow system','Как в системе')],['light',bi('Light','Светлая')],['dark',bi('Dark','Тёмная')]]);
        draft.appearance.design='b'; // One accepted design; language/theme remain configurable.
        note('Reporting timezone: Europe/Berlin. Router WAN, Wi-Fi and VPN keys are edited on the router VPN/network pages.','Часовой пояс отчётов: Europe/Berlin. WAN, Wi-Fi и ключи VPN изменяются на страницах сети и VPN роутера.');
      }else if(session.step===1){
        note('Monitoring service on/off remains a separate action. These preferences do not start Auto, a speed test or an inactive VPN. Checkpoints write statistics to flash.','Включение службы мониторинга остаётся отдельным действием. Эти параметры не запускают Auto, тест скорости или неактивный VPN. Checkpoint записывает статистику во flash.');
        number(bi('Probe interval, seconds','Интервал проверки, секунд'),draft.monitor,'interval','monitor.interval','monitor.interval');
        number(bi('Checkpoint interval, seconds','Интервал checkpoint, секунд'),draft.monitor,'checkpoint','monitor.checkpoint','monitor.checkpoint');
        number(bi('Profile limit per round','Лимит профилей за раунд'),draft.monitor,'probe_limit','monitor.probe_limit','onboarding.probe_limit');
        number(bi('Live journal observations (1–2000)','Наблюдений в живом журнале (1–2000)'),draft.monitor,'live_log_limit','monitor.live_log_limit','monitor.live_log_limit');
        number(bi('Detailed history, days (1–7)','Подробная история, дней (1–7)'),draft.monitor,'history_days','monitor.history_days','monitor.history_days');
        note('Reducing retention removes old detail during normal cleanup. Increasing it cannot restore deleted observations; monthly and lifetime counters remain separate.','Уменьшение срока удаляет старые подробности при штатной очистке. Увеличение не возвращает удалённые наблюдения; месячные и общие счётчики хранятся отдельно.');
        toggle(bi('Enable read-only planning','Включить планирование без применения'),draft.monitor,'planning_enabled','monitor.planning_enabled');
      }else if(session.step===2){
        note('Choose the roles of two configured VPN client tunnels, not arbitrary saved server profiles. Primary is preferred; reserve is a different client. Saving this step changes only Auto VPN settings and does not switch traffic.','Выберите роли двух настроенных VPN-клиентов, а не произвольные профили из каталога серверов. Основной — предпочтительный, резервный — другой клиент. Сохранение этого шага меняет только настройки Auto VPN и не переключает трафик.');
        card.appendChild(E('details',{'data-onboarding-pair-help':'1'},[E('summary',{},bi('How this relates to the router VPN application','Как это связано с VPN-приложением роутера')),E('p',{},bi('On the supported MT3000 pair, one client is WireGuard and the other OpenVPN. Either can be primary. Create/edit profiles and assign a server to each client in the stock router VPN application; this selector does not change server addresses or VPN keys. Auto later starts/stops prepared tunnels and changes the selected traffic policy, with rollback on Stop.','В поддерживаемой паре MT3000 один клиент — WireGuard, другой — OpenVPN. Любой из них может быть основным. Профили и назначение сервера клиенту меняются в штатном VPN-приложении роутера; этот список не меняет адреса серверов и ключи VPN. Auto затем включает/выключает подготовленные туннели и выбирает политику трафика, с восстановлением при остановке.')),E('p',{},bi('Trial preferences do not run a trial or certify Auto. Configured does not mean connected or healthy.','Параметры теста не запускают тест и не подтверждают Auto. Настроен не означает подключён или исправен.'))]));
        var vpnUrl=resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);
        if(vpnUrl)card.appendChild(E('p',{},[E('a',{'href':vpnUrl,'target':'_blank','rel':'noopener noreferrer','data-onboarding-link':'router-vpn'},bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗')),bi(' · Add profiles there, then reload this page. Reloading discards this unsaved draft.',' · Добавьте профили там, затем обновите эту страницу. При обновлении несохранённый черновик будет удалён.')]));
        var pairChannels=onboardingPairChannels(profiles,settings);
        if(pairChannels.length<2)note('Fewer than two distinct configured clients were found. Saved server profiles alone are not enough. Assign profiles to clients in the stock VPN application or defer this pair. A configured client is not yet proof of connection or Auto readiness.','Найдено меньше двух разных настроенных клиентов. Одного наличия серверов в каталоге недостаточно. Назначьте профили клиентам в штатном VPN-приложении или отложите пару. Настроенный клиент ещё не означает подключение или готовность Auto.');
        card.appendChild(E('p',{'data-onboarding-pair-count':'1'},bi('Configured client choices: ','Доступно настроенных клиентов: ')+pairChannels.length+' · '+bi('Saved profiles in catalog: ','Профилей в каталоге: ')+profiles.length));
        var pairNote=E('p',{'role':'status'});card.appendChild(pairNote);
        toggle(bi('Defer the VPN pair and turn off read-only planning','Отложить пару VPN и выключить планирование'),draft.system,'defer_pair','system.defer_pair',function(on){if(on)draft.monitor.planning_enabled=false;pairNote.textContent=on?bi('Pair deferred; planning will be off. Existing router profiles are retained.','Пара отложена; планирование будет выключено. Существующие профили роутера сохраняются.'):'';});
        var placeholder=['',bi('Choose a configured VPN client','Выберите настроенный VPN-клиент')],choices=[placeholder].concat(pairChannels.map(function(p){return [p.id,onboardingPairChannelLabel(p)];}));
        var sourceSelect=select(bi('Primary VPN client','Основной VPN-клиент'),draft.system,'source','system.source',choices);
        var reserveChoices=choices.filter(function(o){return !o[0]||o[0]!==draft.system.source;});
        var targetSelect=select(bi('Reserve VPN client','Резервный VPN-клиент'),draft.system,'target','system.target',reserveChoices);
        sourceSelect.addEventListener('change',function(){
          var keep=targetSelect.value;reserveChoices.splice(0,reserveChoices.length,placeholder);
          pairChannels.forEach(function(p){if(p.id!==sourceSelect.value)reserveChoices.push([p.id,onboardingPairChannelLabel(p)]);});
          while(targetSelect.firstChild)targetSelect.removeChild(targetSelect.firstChild);
          reserveChoices.forEach(function(o){targetSelect.appendChild(E('option',{value:o[0]},o[1]));});
          targetSelect.value=reserveChoices.some(function(o){return o[0]===keep;})?keep:'';draft.system.target=targetSelect.value;gate();
        });
        checks.push(function(){var ok=draft.system.defer_pair?draft.monitor.planning_enabled===false:!!draft.system.source&&draft.system.source!==draft.system.target&&pairChannels.some(function(p){return p.id===draft.system.source;})&&pairChannels.some(function(p){return p.id===draft.system.target;});pairNote.textContent=ok?'':bi('Choose two different configured clients, or defer the pair. A saved but unassigned server cannot be a channel in this pair.','Выберите два разных настроенных клиента или отложите пару. Сохранённый сервер, не назначенный клиенту, не является каналом этой пары.');return ok;});
        // Missing saved IDs must not block an explicitly deferred pair.
        checks=checks.slice(-1);
        number(bi('Bounded trial duration, minutes','Длительность ограниченного теста, минут'),draft.system,'duration','system.duration','system.duration');
        toggle(bi('Allow calls/sessions to reconnect during a later trial','Разрешить переподключение звонков/сессий при будущем тесте'),draft.system,'session_loss','system.session_loss');
      }else if(session.step===3){
        note('These names, groups and priorities are application metadata. They do not alter live VPN routes. Every installed profile is listed.','Эти названия, группы и приоритеты — метаданные приложения. Они не изменяют текущие маршруты VPN. Показаны все установленные профили.');
        if(!draft.system.servers.length)note('No profiles yet. Metadata can be edited here after profiles are added on the router.','Профилей пока нет. Метаданные можно будет изменить здесь после добавления профилей на роутере.');
        draft.system.servers.forEach(function(row,i){
          card.appendChild(E('h3',{},row.profile));
          text(bi('Display name','Название'),row,'name','servers.'+i+'.name','name');text(bi('Display group (not a VPN client)','Группа списка (не VPN-клиент)'),row,'channel','servers.'+i+'.channel','channel');
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
        review(headings[0],[[bi('Router model / detected','Модель роутера / обнаружено'),draft.appearance.router_model+' / '+(settings.detected_router_model||bi('Unknown','Не определён'))],[bi('Language / theme','Язык / тема'),draft.appearance.language+' / '+draft.appearance.theme],[bi('Reporting timezone','Часовой пояс отчётов'),'Europe/Berlin']]);
        review(headings[1],[[bi('Probe / checkpoint (seconds) / profiles per round','Проверка / checkpoint (секунд) / профилей за раунд'),draft.monitor.interval+' / '+draft.monitor.checkpoint+' / '+draft.monitor.probe_limit],[bi('Live observations / detail days','Наблюдений в журнале / дней истории'),draft.monitor.live_log_limit+' / '+draft.monitor.history_days],[bi('Planning enabled','Планирование включено'),yes(draft.monitor.planning_enabled)]]);
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
    if(firstRun){
      var dashboardUrl=new URL(window.location.href);dashboardUrl.searchParams.set('onboarding','defer');dashboardUrl.searchParams.set('lang',locale);dashboardUrl.searchParams.delete('setup_help');dashboardUrl.hash='overview';
      card.appendChild(E('div',{'class':'hv-onboarding-skip','data-onboarding-skip':'1'},[
        E('a',{'href':dashboardUrl.toString(),'target':'_blank','rel':'noopener noreferrer','class':'cbi-button hv-onboarding-recovery-link','data-onboarding-action':'open-dashboard','style':'white-space:normal;display:inline-block;max-width:100%;box-sizing:border-box'},bi('Open dashboard and recovery controls — setup remains incomplete','Открыть панель и средства восстановления — настройка не завершена')),
        E('p',{},bi('Continue with the router’s existing settings and saved defaults. This button saves no draft, resets nothing and does not enable Auto. You can finish the eight steps here, or open Settings → All application settings later. The dashboard opens in a new tab and this draft stays here.','Перейти с текущими настройками роутера и сохранёнными значениями по умолчанию. Кнопка не сохраняет черновик, ничего не сбрасывает и не включает Auto. Вы можете пройти восемь шагов здесь либо позже открыть «Настройки → Все настройки приложения». Панель откроется в новой вкладке; черновик останется здесь.'))
      ]));
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
function openOnboardingSettings(inventory,status,requestedStep){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE'));return;}
  if(ONBOARDING_SESSION&&ONBOARDING_SESSION.busy)return;
  if(ONBOARDING_SESSION)ONBOARDING_SESSION.paused=false;
  ui.showModal(bi('All application settings','Все настройки приложения'),[renderOnboarding(inventory,status,false,requestedStep)]);
}
