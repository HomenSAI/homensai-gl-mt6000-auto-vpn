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
  return E('div',{'class':'hv-summary-wrap'},[hero,guide]);
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
// Jump to the row of a code in the error table on the Events page, open its "how to fix" and highlight it.
function showErrorCode(code){
  var link=document.querySelector('[data-hv-tab="events"]');if(link)link.click();
  setTimeout(function(){
    var row=document.querySelector('[data-error-code="'+code+'"]');if(!row)return;
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
      E('td',{},E('span',{'class':'hv-checkbox hv-checkbox-'+st.state,'role':'img','aria-label':label},mark)),
      E('td',{},E('strong',{},bi(r[0],r[1]))),E('td',{},bi(r[2],r[3])),E('td',{},[E('div',{},label),codeCell])]);
  });
  return E('div',{'class':'hv-plan-blockers'},[
    E('h4',{},bi('Checks before a real switch','Проверки перед реальным переключением')),
    E('p',{},bi('Empty box: not checked yet. Green: verified. Red: failed, with the error code; press the code to open its description and how to fix it. Until all are green the forecast above never becomes a permission to switch: a real switch also needs the passed LAN trial and the checks on the Overview. This is normal for an experimental version.','Пустая клетка: ещё не проверено. Зелёная: подтверждено. Красная: не прошло, рядом код ошибки; нажмите на код, чтобы открыть описание и способ исправления. Пока не все клетки зелёные, прогноз выше никогда не становится разрешением на переключение: для реального переключения всегда нужны пройденный LAN-тест и проверки на «Обзоре». Для экспериментальной версии это нормально.')),
    E('table',{'class':'table hv-plan-table'},[E('tr',{},[E('th',{},''),E('th',{},bi('Check','Проверка')),E('th',{},bi('What it means','Что это значит')),E('th',{},bi('State and code','Состояние и код'))])].concat(rows))]);
}

// A code shown as a link: opens its row in the error table (name, meaning, how to fix).
function errorCodeLink(code){return E('a',{'href':'#events','class':'hv-errlink','click':function(ev){ev.preventDefault();showErrorCode(code);}},code);}
