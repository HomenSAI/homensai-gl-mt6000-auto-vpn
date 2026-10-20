/* Overview summary: one sentence and one colour for the whole system, plus a short "getting started" checklist. */
function learnDone(){try{return window.localStorage.getItem('homensai-vpn-learn-done')==='1';}catch(e){return false;}}
function summaryTone(light){return light.lamp==='green'?'ok':(light.lamp==='yellow'||light.lamp==='orange')?'warn':light.lamp==='red'?'bad':'off';}
function startSteps(status,inventory,now){
  var settings=(inventory||{}).settings||{},monitor=monitorLightModel(status,inventory,now,false),ready=autoReadiness(status,inventory,now),model=autoControlModel(status,now);
  return [
    {key:'terms',done:true,title:bi('Accept the terms','Принять условия'),hint:bi('Done on the first screen.','Сделано на первом экране.')},
    {key:'learn',done:learnDone(),title:bi('Take the 5-minute training','Пройти обучение на 5 минут'),hint:bi('What the system is, how to use it and what to do if the internet is gone.','Что это за система, как ею пользоваться и что делать, если пропал интернет.'),href:'#learn',action:bi('Open training','Открыть обучение')},
    {key:'monitor',done:monitor.key==='ok',title:bi('Monitoring is on','Мониторинг включён'),hint:bi('It starts by itself. Look at the Monitoring block at the top of this page: the lamp must be green. If it is not, press “Start monitoring” there.','Он запускается сам. Посмотрите на блок «Мониторинг» вверху этой страницы: лампа должна быть зелёной. Если нет, нажмите там «Запустить мониторинг».')},
    {key:'profiles',done:!!(settings.setup_complete&&settings.plan_source&&settings.plan_target),title:bi('Choose the primary and the reserve VPN','Выбрать основной и резервный VPN'),hint:bi('Settings → Setup → 1 · System.','«Настройки» → «Настройка» → 1 · Система.'),href:'#settings',action:bi('Open Settings','Открыть настройки')},
    {key:'auto',done:!!model.on,title:bi('Check the VPNs, run the LAN test, turn on Auto','Проверить VPN, пройти LAN-тест, включить Auto'),hint:ready.ready?bi('Everything is ready: press the Auto button below.','Всё готово: нажмите кнопку Auto ниже.'):bi('The list under the Auto button shows what is still missing.','Список под кнопкой Auto показывает, чего ещё не хватает.')}
  ];
}
function renderSummary(status,inventory){
  var now=Date.now()/1000,rows=status.profiles||[],light=autoLightModel(status,inventory,now),tone=summaryTone(light),c=serverCounts(status,inventory,rows,now);
  var headline=status.rpc_error?bi('No data from the router','Нет данных от роутера'):light.title;
  var line=c.connected?(c.working+' / '+c.connected+' '+bi('VPNs work','VPN работают')):bi('No VPN is connected','Ни один VPN не подключён');
  var steps=startSteps(status,inventory,now),open=steps.filter(function(s){return !s.done;}),next=open[0];
  var hero=E('section',{'class':'hv-summary hv-summary-'+tone,'role':'status'},[
    E('div',{'class':'hv-summary-mark','aria-hidden':'true'},tone==='ok'?'✓':tone==='warn'?'⇄':tone==='bad'?'!':'○'),
    E('div',{'class':'hv-summary-text'},[E('small',{},bi('Right now','Прямо сейчас')),E('h2',{},headline),E('p',{},light.hint)]),
    E('div',{'class':'hv-summary-count'},[E('strong',{},c.connected?String(c.working)+'/'+String(c.connected):'—'),E('span',{},line)])]);
  var list=E('ol',{'class':'hv-start-list'},steps.map(function(s,i){
    var current=next&&next.key===s.key;
    return E('li',{'class':'hv-start-step hv-start-'+(s.done?'done':current?'next':'todo')},[E('span',{'class':'hv-start-mark','aria-hidden':'true'},s.done?'✓':String(i+1)),E('div',{},[E('strong',{},s.title),s.done?null:E('p',{},s.hint)].filter(Boolean)),(!s.done&&current&&s.href)?E('a',{'class':'cbi-button cbi-button-action','href':s.href},s.action):null].filter(Boolean));
  }));
  var guide=E('details',{'class':'hv-chart-card hv-start-card'+(open.length?'':' hv-start-complete'),'open':open.length?'open':null},[E('summary',{},open.length?bi('Getting started: ','Начало работы: ')+(steps.length-open.length)+' / '+steps.length:bi('Getting started: all steps done','Начало работы: все шаги выполнены')),list]);
  // The checklist has its own first section now (Getting started); the Overview keeps only the state.
  return E('div',{'class':'hv-summary-wrap'},[hero]);
}

// A summary tile that opens to explain what the number means.
function metricInfo(label,value,detail,explain){
  return E('details',{'class':'hv-metric hv-metric-info'},[E('summary',{},[E('span',{},label),E('strong',{},text(value)),E('small',{},detail)]),E('p',{'class':'hv-metric-explain'},explain)]);
}

// The forecast panel lists checks that this router has not been certified for yet. Each code gets a plain explanation.
var PLAN_BLOCKERS={
  'GL-ADAPTER-UNVERIFIED':['GL.iNet VPN manager','Менеджер VPN GL.iNet','Not proven that this program’s way of switching works together with the VPN manager built into this exact GL.iNet firmware.','Не доказано, что способ переключения этой программы работает вместе со встроенным менеджером VPN именно этой прошивки GL.iNet.'],
  'WORKER-COORDINATION-UNVERIFIED':['GL.iNet background programs','Фоновые программы GL.iNet','GL.iNet runs its own background programs that also connect and reconnect VPNs. Not tested that they do not fight with this program.','GL.iNet запускает свои фоновые программы, которые тоже подключают и переподключают VPN. Не проверено, что они не мешают этой программе.'],
  'LAN-PATH-UNVERIFIED':['Path of a home computer','Путь домашнего компьютера','Not confirmed from a computer in your network that its traffic really goes through the chosen VPN. This is what the LAN helper checks.','Не подтверждено с компьютера в вашей сети, что его трафик действительно идёт через выбранный VPN. Это проверяет LAN-помощник.'],
  'DNS-POLICY-UNVERIFIED':['Name lookups (DNS)','Поиск адресов (DNS)','Not confirmed that DNS requests of your devices follow the VPN and do not leak outside it during and after a switch.','Не подтверждено, что DNS-запросы ваших устройств идут через VPN и не утекают мимо него во время и после переключения.'],
  'KILLSWITCH-UNVERIFIED':['Kill Switch','Kill Switch','Not confirmed that the GL.iNet Kill Switch blocks the internet, instead of leaking, when a VPN drops during a switch.','Не подтверждено, что Kill Switch GL.iNet блокирует интернет, а не пропускает трафик мимо VPN, когда VPN обрывается во время переключения.'],
  'IPV6-POLICY-UNVERIFIED':['IPv6 traffic','Трафик IPv6','Not confirmed that IPv6 traffic cannot bypass the VPN.','Не подтверждено, что трафик IPv6 не может обойти VPN.'],
  'WATCHDOG-UNVERIFIED':['Safety timer','Страхующий таймер','Not confirmed on this router that the independent timer, which releases the program’s traffic block and returns to a safe state if something hangs, always fires.','Не подтверждено на этом роутере, что независимый таймер, который снимает собственную блокировку трафика и возвращает безопасное состояние при зависании, всегда срабатывает.'],
  'SCOPED-CONNTRACK-UNVERIFIED':['Open connections','Открытые соединения','Not confirmed that a switch resets only the connections it must (the router’s connection table), not all of them.','Не подтверждено, что при переключении сбрасываются только нужные соединения (таблица соединений роутера), а не все.']
};
// Failure codes of the controller that prove a planning check has FAILED (not only that it is still unproven).
var PLAN_FAILURE_CODES={
  'GL-ADAPTER-UNVERIFIED':['UNSUPPORTED-BOARD','UNSUPPORTED-FIRMWARE','FIRMWARE-UNKNOWN','VENDOR-CODE-CHANGED','VENDOR-CODE-UNVERIFIED','VENDOR-APPLY-FAILED','POLICY-READ-FAILED'],
  'WORKER-COORDINATION-UNVERIFIED':['VENDOR-WORKER-BUSY'],
  'LAN-PATH-UNVERIFIED':['LAN-LAYOUT-UNSUPPORTED','CLIENT-CONFIRMATION-TIMEOUT','LAN-BASELINE-NOT-SOURCE'],
  'DNS-POLICY-UNVERIFIED':['TARGET-HTTPS-DNS-FAILED'],
  'KILLSWITCH-UNVERIFIED':['KILLSWITCH-NOT-ENABLED','DIRECT-WAN-FALLBACK'],
  'IPV6-POLICY-UNVERIFIED':['IPV6-NOT-EXPLICITLY-DISABLED'],
  'WATCHDOG-UNVERIFIED':['NFT-GUARD-UNAVAILABLE','LEASE-INTEGRITY-FAILED','LEASE-STORAGE-FAILED'],
  'SCOPED-CONNTRACK-UNVERIFIED':[]
};
// verified = the code is no longer listed as unproven; failed = a related failure code is reported; otherwise still empty.
function planCheckState(code,unproven,reported){
  var failure=(PLAN_FAILURE_CODES[code]||[]).filter(function(c){return reported.indexOf(c)>=0;})[0];
  if(failure)return {state:'failed',failure:failure};
  return {state:unproven.indexOf(code)>=0?'pending':'verified',failure:null};
}
/* Open a section and scroll to an element of it (by id), highlighting it. Works also when the section is already open, where a plain #hash link does nothing. */
function pageKeyNow(){var p=document.querySelector('[data-hv-page]:not([hidden])');return p?p.getAttribute('data-hv-page'):null;}
function goToSection(tab,id){
  var link=document.querySelector('[data-hv-tab="'+tab+'"]');if(link&&pageKeyNow()!==tab)link.click();
  setTimeout(function(){var n=id&&document.getElementById(id);if(!n){window.scrollTo(0,0);return;}n.scrollIntoView({block:'start'});n.classList.add('hv-errflash');setTimeout(function(){n.classList.remove('hv-errflash');},3000);},160);
}
/* "Back" after following an error link: returns to the page and scroll position where the link was clicked. */
var errorReturn=null,errorBackButton=null,errorBackTimer=null;
function hideErrorBack(){errorReturn=null;if(errorBackButton)errorBackButton.setAttribute('hidden','');if(errorBackTimer){clearInterval(errorBackTimer);errorBackTimer=null;}}
function showErrorBack(){
  if(!document.querySelector('.hv-app')||!errorReturn)return;
  if(!errorBackButton||!errorBackButton.isConnected){errorBackButton=E('button',{'type':'button','class':'hv-errback-button','click':function(){
    var r=errorReturn;hideErrorBack();if(!r||!r.tab)return;
    var l=document.querySelector('[data-hv-tab="'+r.tab+'"]');if(l&&pageKeyNow()!==r.tab)l.click();
    setTimeout(function(){window.scrollTo(0,r.y||0);},120);}},[E('span',{'aria-hidden':'true'},'←'),E('span',{},bi('Back to where you were','Вернуться назад'))]);document.body.appendChild(errorBackButton);}
  errorBackButton.removeAttribute('hidden');
  if(errorBackTimer)clearInterval(errorBackTimer);
  errorBackTimer=setInterval(function(){if(pageKeyNow()!=='events')hideErrorBack();},700);
}
// Jump to the row of a code in the error table on the Events page, open its "how to fix" and highlight it.
function showErrorCode(code){
  if(!errorReturn&&pageKeyNow())errorReturn={tab:pageKeyNow(),y:window.pageYOffset||0};
  var link=document.querySelector('[data-hv-tab="events"]');if(link&&pageKeyNow()!=='events')link.click();
  setTimeout(showErrorBack,300);
  setTimeout(function(){
    var key=Object.prototype.hasOwnProperty.call(ERROR_GROUP_OF,code)?code:((typeof errorFamilyOf==='function'&&errorFamilyOf(code))?errorFamilyOf(code)[0]+'*':code);
    if(!/^[A-Z][A-Z0-9*-]{1,95}$/.test(key))return;
    var row=document.querySelector('[data-error-code="'+key+'"]');if(!row)return;
    var fix=row.nextElementSibling;if(fix&&fix.classList&&fix.classList.contains('hv-errfix')&&fix.hidden){var b=row.querySelector('button');if(b)b.click();}
    row.scrollIntoView({block:'center'});row.classList.add('hv-errflash');setTimeout(function(){row.classList.remove('hv-errflash');},3000);
  },150);
}
function renderPlanBlockers(codes,status){
  var reported=Array.isArray(((status||{}).native_failover||{}).blockers)?status.native_failover.blockers:[];
  var rows=Object.keys(PLAN_BLOCKERS).map(function(code){
    var r=PLAN_BLOCKERS[code],st=planCheckState(code,codes,reported);
    var mark=st.state==='verified'?'✓':st.state==='failed'?'✗':'';
    var label=st.state==='verified'?bi('Verified','Подтверждено'):st.state==='failed'?bi('Failed','Не прошло'):bi('Not checked yet','Ещё не проверено');
    var codeCell=st.state==='failed'
      ?E('a',{'href':'#events','class':'hv-errlink','click':function(ev){ev.preventDefault();showErrorCode(st.failure);}},st.failure)
      :E('a',{'href':'#events','class':'hv-errlink hv-errlink-quiet','click':function(ev){ev.preventDefault();showErrorCode(code);}},code);
    return E('tr',{'class':'hv-plan-'+st.state},[
      E('td',{'class':'hv-plan-lamp'},[E('span',{'class':'hv-check-lamp hv-check-'+(st.state==='verified'?'green':st.state==='failed'?'red':'grey'),'role':'img','aria-label':label})]),
      E('td',{},E('strong',{},bi(r[0],r[1]))),E('td',{},bi(r[2],r[3])),E('td',{},[E('div',{},label),codeCell])]);
  });
  return E('div',{'class':'hv-plan-blockers'},[
    E('h4',{},bi('Checks before a real switch','Проверки перед реальным переключением')),
    E('p',{'class':'hv-plan-note'},[E('strong',{},bi('Display only: nothing here can be pressed.','Только показ: здесь ничего нельзя нажать.')),' ',bi('These are the eight things that must be certified on this router before the program may really switch traffic. The list is built by the program itself and updated with every status refresh.','Это восемь вещей, которые должны быть подтверждены на этом роутере, прежде чем программа сможет по-настоящему переключать трафик. Список строит сама программа и обновляет при каждом обновлении статуса.')]),
    E('ul',{'class':'hv-plan-legend'},[
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-green','aria-hidden':'true'}),bi(' Green: verified.',' Зелёный: подтверждено.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-red','aria-hidden':'true'}),bi(' Red: the switch controller reported a related failure; its code is shown, press the code to read how to fix it.',' Красный: контроллер переключения сообщил о связанной ошибке; её код показан, нажмите на код, чтобы прочитать, как исправить.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-grey','aria-hidden':'true'}),bi(' Grey: not certified yet. No button runs these checks; they are confirmed by the controller\'s own audit together with a passed LAN trial.',' Серый: ещё не подтверждено. Эти проверки не запускаются кнопкой; их подтверждает собственный аудит контроллера вместе с пройденным LAN-тестом.')])]),
    E('p',{'class':'hv-plan-source'},[E('strong',{},bi('Where the data comes from: ','Откуда данные: ')),bi('the list of eight checks is the forecast (failover_plan) computed by the monitor on the router; a red line appears when the controller (native_switch) puts a matching error code into its status. In this version the forecast is a dry run, so the eight lines stay grey until the controller reports a failure. The real permission to switch is decided by the controller after the LAN trial and the router checks listed on the Overview (Before you can start Auto).','список из восьми проверок — это прогноз (failover_plan), который считает монитор на роутере; красная строка появляется, когда контроллер (native_switch) кладёт в свой статус подходящий код ошибки. В этой версии прогноз — «сухой прогон», поэтому восемь строк остаются серыми, пока контроллер не сообщит об ошибке. Реальное разрешение на переключение решает контроллер после LAN-теста и проверок роутера, перечисленных на «Обзоре» («Что нужно перед запуском Auto»).')]),
    E('table',{'class':'table hv-plan-table'},[E('tr',{},[E('th',{},''),E('th',{},bi('Check','Проверка')),E('th',{},bi('What it means','Что это значит')),E('th',{},bi('State and code','Состояние и код'))])].concat(rows))]);
}

// A code shown as a link: opens its row in the error table (name, meaning, how to fix).
function ownGet(map,key){return typeof key==='string'&&Object.prototype.hasOwnProperty.call(map,key)?map[key]:undefined;}
function safeCode(code){return typeof code==='string'&&/^[A-Z][A-Z0-9-]{1,95}$/.test(code);}
function errorCodeLink(code){return E('a',{'href':'#events','class':'hv-errlink','click':function(ev){ev.preventDefault();showErrorCode(code);}},code);}

/* Getting started: its own first section. Until every step is done the page opens here; once all steps were done in this
   browser it always opens on the Overview (a later problem is shown on the Overview, not by sending the user back here). */
var START_DONE_KEY='homensai-vpn-start-done';
function startAllDone(steps){return steps.every(function(s){return s.done;});}
function startLanding(status,inventory){
  try{if(window.localStorage.getItem(START_DONE_KEY)==='1')return 'overview';}catch(e){}
  var steps=startSteps(status||{},inventory||{},Date.now()/1000);
  if(startAllDone(steps)){try{window.localStorage.setItem(START_DONE_KEY,'1');}catch(e){}return 'overview';}
  return 'start';
}
function renderStartPage(status,inventory){
  var steps=startSteps(status,inventory,Date.now()/1000),open=steps.filter(function(s){return !s.done;}),next=open[0];
  if(!open.length){try{window.localStorage.setItem(START_DONE_KEY,'1');}catch(e){}}
  var targets={learn:['#learn',bi('Open training','Открыть обучение')],monitor:['#overview',bi('Open the Overview','Открыть «Обзор»')],profiles:['#settings',bi('Open Settings','Открыть настройки')],auto:['#overview',bi('Open the Overview','Открыть «Обзор»')]};
  var list=E('ol',{'class':'hv-start-list hv-start-page-list'},steps.map(function(s,i){
    var current=next&&next.key===s.key,target=targets[s.key];
    return E('li',{'class':'hv-start-step hv-start-'+(s.done?'done':current?'next':'todo')},[
      E('span',{'class':'hv-start-mark','aria-hidden':'true'},s.done?'✓':String(i+1)),
      E('div',{},[E('strong',{},s.title),E('p',{},s.done?bi('Done.','Готово.'):s.hint)]),
      (!s.done&&target)?E('a',{'class':'cbi-button'+(current?' cbi-button-action':''),'href':target[0]},target[1]):E('span',{'class':'hv-visually-hidden'},s.done?bi('done','выполнено'):bi('not done','не выполнено'))]);
  }));
  return E('section',{'class':'hv-chart-card hv-start-page'},[
    E('h3',{},open.length?bi('Step ','Шаг ')+(steps.indexOf(next)+1)+bi(' of ',' из ')+steps.length:bi('All steps are done','Все шаги выполнены')),
    E('p',{},open.length?bi('Go through the steps in order. This page opens first until every step is done; after that the program opens on the Overview.','Пройдите шаги по порядку. Эта страница открывается первой, пока все шаги не выполнены; после этого программа открывается на «Обзоре».'):bi('From now on the program opens on the Overview. You can come back here at any time.','Теперь программа открывается на «Обзоре». Сюда можно вернуться в любое время.')),
    list,
    E('p',{},E('a',{'class':'cbi-button'+(open.length?'':' cbi-button-action'),'href':'#overview'},bi('Go to the Overview','Перейти на «Обзор»')))]);
}
