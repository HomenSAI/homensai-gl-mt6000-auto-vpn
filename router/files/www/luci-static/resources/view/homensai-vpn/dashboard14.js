// HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
'use strict';
'require view';
'require form';
'require rpc';
'require poll';
'require ui';

var locale = localStorage.getItem('homensai-vpn-language') || 'en';
var translations = {"Туннель не подключён": "Tunnel disconnected", "HTTPS через VPN не проходит": "HTTPS through VPN failed", "DNS не отвечает": "DNS unavailable", "Маршрут не соответствует VPN": "Route does not match VPN", "Путь проверки не подтверждён": "Probe path unverified", "Ошибка службы или зависимости": "Service or dependency error", "Ошибка сохранения статистики": "Statistics storage error", "Статистика восстановлена из резервной копии": "Statistics restored from backup", "Время роутера ещё не установлено": "Router clock is not set", "Профиль сейчас не подключён": "Profile currently inactive", "Профиль вне лимита текущего раунда": "Profile outside this round's limit", "Служба остановлена": "Service unavailable", "График появится после двух успешных измерений. Искусственных данных здесь нет.": "The chart appears after two successful measurements. No synthetic data is used.", "История HTTPS-задержки подключённых серверов в миллисекундах": "HTTPS latency history of connected servers in milliseconds", "HTTPS, мс · последние доступные измерения за час. Разрывы длиннее 90 секунд не соединяются.": "HTTPS, ms · available samples from the last hour. Gaps longer than 90 seconds are not connected.", "Нативный монитор alpha: реальные IPv4 HTTPS/DNS-проверки на роутере. Автоматическое изменение маршрутов пока недоступно.": "Native alpha monitor: real IPv4 HTTPS/DNS probes on the router. Automatic route switching is unavailable.", "Служба наблюдения": "Monitoring service", "Включить наблюдение": "Enable monitoring", "Интервал, секунд": "Probe interval, seconds", "Лимит подключённых профилей за раунд": "Connected profile limit per round", "Сохранение статистики во flash, секунд": "Flash checkpoint interval, seconds", "Отправлять отчёты в Telegram": "Send Telegram reports", "Интервал Telegram-отчётов, минут": "Telegram report interval, minutes", "Токен бота · настройка Telegram": "Bot token · Telegram setup", "Проверьте формат токена BotFather": "Check the BotFather token format", "Оставьте пустым, чтобы сохранить действующий токен.": "Leave empty to keep the current token.", "Токен сохранится на роутере; в отчёты и статус не включается.": "The token stays on the router and is excluded from reports and status.", "Каналы и существующие профили": "Channels and existing profiles", "Ваше название": "Display name", "Профиль роутера": "Router profile", "Ваш канал": "Channel name", "Приоритет": "Priority", "Наблюдать": "Monitor", "Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.": "Monitoring is active. Native controller state is shown below. Router probes do not certify the LAN client path; a trial requires separate client confirmation.", "включён · интервал ": "enabled · interval ", " мин · последняя отправка ": " min · last sent ", "ожидается": "pending", "отключён": "disabled", "Подключённые серверы": "Connected servers", "Остальные профили не запускаются": "Other profiles are not started", "Проверки сейчас": "Current probes", " из ": " of ", "HTTPS и DNS с роутера · IPv4": "Router HTTPS and DNS · IPv4", "Трафик месяца": "Monthly traffic", "Нет данных": "No data", "Неполный период · с начала наблюдения": "Partial period · since monitoring started", "Ошибка": "Error", "Каждые ": "Every ", " мин": " min", "Отключён": "Disabled", "Отправлен ": "Sent ", "Нет подтверждённой отправки": "No confirmed delivery", "Подключённые VPN-серверы": "Connected VPN servers", " мс · HTTPS": " ms · HTTPS", "Измерено ": "Measured ", "нет данных": "no data", "Подключённые серверы не обнаружены.": "No connected servers detected.", "Задержка серверов во времени": "Server latency over time", "Сервер": "Server", "Канал": "Channel", "Протокол": "Protocol", "Интерфейс": "Interface", "Результат": "Result", "HTTPS, мс": "HTTPS, ms", "Время проверки": "Probe time", "Текущие проверки серверов": "Current server probes", "Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.": "Inactive profiles are listed without being started. Testing one requires a separate approved connection window.", "Рейтинг измеренных профилей": "Measured profile ranking", "Успех проверок": "Probe success", "Средняя HTTPS-задержка": "Average HTTPS latency", " мс": " ms", "Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.": "Ranking uses hourly aggregates from up to seven days of monitoring. This is not a bandwidth test; priorities are not applied automatically.", "VPN-трафик по календарным месяцам · Europe/Berlin": "VPN traffic by calendar month · Europe/Berlin", "Месяц": "Month", "Входящий": "Received", "Исходящий": "Sent", "Всего": "Total", "Наблюдение": "Observation", " интерфейс-часов": " interface-hours", " · граница оценена": " · estimated month boundary", "Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ": "Unique VPN interfaces are counted once, including protocol overhead. Observation gaps: ", ". После потери питания возможна потеря последнего интервала checkpoint.": ". A power loss may lose the latest checkpoint interval.", "Монитор служб": "Service monitor", "Скачать журнал": "Export events", "Серверы, качество связи и трафик — реальные измерения на роутере": "Servers, connection quality and traffic — real router measurements", "Запрошен раунд проверок подключённых профилей.": "A probe round for connected profiles was requested.", "Проверить сейчас": "Probe now", "Настроить Telegram": "Set up Telegram", "Мастер подключения Telegram": "Telegram setup wizard", "Настройки мониторинга, Telegram и названия серверов": "Monitoring settings, Telegram and server names", "Подключение Telegram": "Connect Telegram", "Создайте бота через @BotFather и скопируйте токен.": "Create a bot with @BotFather and copy its token.", "Отправьте боту /start. Введите свой Chat ID и токен ниже.": "Send /start to your bot. Enter your own chat ID and bot token below.", "Включите отправку, выберите интервал и нажмите Save & Apply. Роутер отправит первый отчёт; результат появится в статусе Telegram сверху.": "Enable reports, select an interval and click Save & Apply. The router sends its first report; delivery status appears above.", "Токен — секрет. После сохранения он не показывается; повторная настройка открывается отдельной кнопкой.": "The token is secret. It is not displayed after saving. Use the separate setup button to replace it."};
function tr(value){return locale==='ru'?value:(translations[value]||value);}
function bi(en,ru){return locale==='ru'?ru:en;}
function diagnosticText(value){return translations[value]||value;}


var statusCall=rpc.declare({object:'homensai-vpn',method:'status',expect:{}});
var inventoryCall=rpc.declare({object:'homensai-vpn',method:'inventory',expect:{}});
var scanCall=rpc.declare({object:'homensai-vpn',method:'scan',expect:{}});
var codes={
  'VPN-001':diagnosticText("Туннель не подключён"), 'VPN-003':diagnosticText("HTTPS через VPN не проходит"),
  'DNS-001':diagnosticText("DNS не отвечает"), 'ROUTE-001':diagnosticText("Маршрут не соответствует VPN"),
  'CHECK-001':diagnosticText("Путь проверки не подтверждён"), 'SYSTEM-001':diagnosticText("Ошибка службы или зависимости"),
  'STORAGE-001':diagnosticText("Ошибка сохранения статистики"), 'STORAGE-RECOVERED':diagnosticText("Статистика восстановлена из резервной копии"), 'CLOCK-001':diagnosticText("Время роутера ещё не установлено"), 'PROFILE-INACTIVE':diagnosticText("Профиль сейчас не подключён"),
  'CHECK-LIMIT':diagnosticText("Профиль вне лимита текущего раунда"), 'SERVICE-STOPPED':diagnosticText("Служба остановлена")
};
function text(value){return value==null?'—':String(value);}
function bytes(value){return Number.isFinite(value)?(value/1000000000).toFixed(3)+' GB':'—';}
function cell(value){return E('td',{},text(value));}
function badge(code){return E('strong',{'class':'hv-badge '+(!code?'hv-ok':code==='PROFILE-INACTIVE'?'hv-idle':'hv-warn')},code?(codes[code]||code):'OK');}
function metric(label,value,detail){return E('div',{'class':'hv-metric'},[E('span',{},label),E('strong',{},text(value)),E('small',{},detail)]);}
function chart(samples,rows){
  var colors=['var(--accent)','var(--teal)','var(--gold)','var(--bad)'],ns='http://www.w3.org/2000/svg';
  function svgNode(name,attrs,content){var n=document.createElementNS(ns,name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});if(content)n.textContent=content;return n;}
  var good=samples.filter(function(s){return Number.isFinite(s.rtt_ms)&&!s.code&&s.time;});
  if(good.length<2)return E('div',{'class':'hv-empty'},tr("График появится после двух успешных измерений. Искусственных данных здесь нет."));
  var end=Math.max.apply(null,good.map(function(s){return s.time;})),start=Math.max(end-3600,Math.min.apply(null,good.map(function(s){return s.time;})));
  good=good.filter(function(s){return s.time>=start;});
  var max=Math.max(100,Math.ceil(Math.max.apply(null,good.map(function(s){return s.rtt_ms;}))/100)*100);
  var svg=svgNode('svg',{viewBox:'0 0 820 260',role:'img','aria-label':tr("История HTTPS-задержки подключённых серверов в миллисекундах")});
  [0,0.5,1].forEach(function(f){var y=215-f*180;svg.appendChild(svgNode('line',{x1:55,x2:800,y1:y,y2:y,stroke:'var(--line)'}));svg.appendChild(svgNode('text',{x:5,y:y+4,fill:'var(--muted)','font-size':12},String(Math.round(max*f))));});
  var legend=E('div',{'class':'hv-legend'});
  rows.filter(function(p){return good.some(function(s){return s.id===p.id;});}).forEach(function(p,i){
    var points=good.filter(function(s){return s.id===p.id;}).sort(function(a,b){return a.time-b.time;}),path='',previous;
    points.forEach(function(s){var x=55+(s.time-start)/Math.max(1,end-start)*745,y=215-s.rtt_ms/max*180;path+=(previous&&s.time-previous<=90?' L':' M')+x.toFixed(1)+','+y.toFixed(1);previous=s.time;});
    svg.appendChild(svgNode('path',{d:path,fill:'none',stroke:colors[i%colors.length],'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'}));
    legend.appendChild(E('span',{},[E('i',{'class':'hv-series-'+(i%colors.length)}),p.name]));
  });
  svg.appendChild(svgNode('text',{x:55,y:247,fill:'var(--muted)','font-size':12},new Date(start*1000).toLocaleTimeString()));
  svg.appendChild(svgNode('text',{x:800,y:247,fill:'var(--muted)','font-size':12,'text-anchor':'end'},new Date(end*1000).toLocaleTimeString()));
  return E('div',{'class':'hv-chart'},[svg,legend,E('small',{},tr("HTTPS, мс · последние доступные измерения за час. Разрывы длиннее 90 секунд не соединяются."))]);
}

function histogram(accounting,onPeriod,period){
  function dateKey(date){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);}
  var today=dateKey(new Date()),parts=today.split('-').map(Number),weekStart=new Date(Date.UTC(parts[0],parts[1]-1,parts[2]-6)).toISOString().slice(0,10);
  var section=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Server uptime and failures','Работа серверов и сбои'))]);
  section.appendChild(E('select',{'aria-label':bi('Statistics period','Период статистики'),'change':function(ev){onPeriod(ev.target.value);}},[
    E('option',{value:'day',selected:period==='day'},bi('Today','Сегодня')),E('option',{value:'week',selected:period==='week'},bi('Last 7 calendar days','Последние 7 календарных дней')),E('option',{value:'month',selected:period==='month'},bi('Current calendar month','Текущий календарный месяц'))]));
  var profiles=Object.keys(accounting.activity||{}).map(function(key){var p=accounting.activity[key],totals={up:0,down:0,unknown:0,connections:0,failures:0};Object.keys(p.days||{}).forEach(function(day){if(period==='day'?day!==today:period==='week'?day<weekStart||day>today:day.slice(0,7)!==today.slice(0,7))return;Object.keys(totals).forEach(function(k){totals[k]+=p.days[day][k]||0;});});return {p:p,t:totals};});
  if(!profiles.length)section.appendChild(E('p',{},bi('History starts with this release. No earlier observations are invented.','История начинается с этой версии. Предыдущие измерения не придумываются.')));
  ['openvpn','wireguard'].forEach(function(protocol){
    section.appendChild(E('h4',{},protocol==='openvpn'?'OpenVPN':'WireGuard'));
    var group=E('div',{'class':'hv-histograms'});
    profiles.filter(function(r){return r.p.protocol===protocol;}).sort(function(a,b){return b.t.up-a.t.up;}).forEach(function(r){
      var total=r.t.up+r.t.down+r.t.unknown,bar=document.createElementNS('http://www.w3.org/2000/svg','svg'),offset=160;bar.setAttribute('class','hv-stack');bar.setAttribute('viewBox','0 0 68 160');
      [['up','var(--ok)'],['down','var(--bad)'],['unknown','var(--muted)']].forEach(function(entry){var value=r.t[entry[0]],percent=total?100*value/total:0;if(value){var ns='http://www.w3.org/2000/svg',rect=document.createElementNS(ns,'rect'),title=document.createElementNS(ns,'title');var height=percent*1.6;offset-=height;rect.setAttribute('x','0');rect.setAttribute('y',offset);rect.setAttribute('width','68');rect.setAttribute('height',height);rect.setAttribute('fill',entry[1]);title.textContent=entry[0]+': '+(value/3600).toFixed(2)+' h · '+percent.toFixed(1)+'%';rect.appendChild(title);bar.appendChild(rect);if(percent>=12){var label=document.createElementNS(ns,'text');label.setAttribute('x','34');label.setAttribute('y',offset+height/2+4);label.setAttribute('text-anchor','middle');label.setAttribute('class','hv-stack-label');label.textContent=percent.toFixed(0)+'%';bar.appendChild(label);}}});
      group.appendChild(E('div',{'class':'hv-histogram'},[E('strong',{},(r.t.up/3600).toFixed(2)+' h'),bar,E('b',{},r.p.name),E('small',{},bi('Connections: ','Подключений: ')+r.t.connections+' · '+bi('Failures: ','Сбоев: ')+r.t.failures),!total?E('small',{},bi('No active observation','Нет активных измерений')):null]));
    });section.appendChild(group);
  });
  section.appendChild(E('p',{},bi('Green: confirmed healthy time · red: confirmed failure time · grey: unobserved time. Inactive reserves are excluded. Connections count observed inactive → active transitions; startup is not a new connection. Duration is estimated between probes; checkpoint gaps remain unknown.','Зелёный — подтверждённая работа, красный — сбой, серый — без измерений. Неактивные резервы исключены. Подключения — наблюдаемые переходы из неактивного состояния; запуск монитора не считается подключением. Время оценено между проверками; пропуски checkpoint остаются неизвестными.')));
  return section;
}

function loadBrand(){
  return ['brand','robot','brand-ui'].reduce(function(ready,name){return ready.then(function(){
    return new Promise(function(resolve,reject){
      var path=L.resource('view/homensai-vpn/style/js/'+name+'.js');
      if(document.querySelector('script[data-homensai-style="'+name+'"]')){resolve();return;}
      var script=document.createElement('script');script.src=path;script.setAttribute('data-homensai-style',name);
      script.onload=resolve;script.onerror=function(){script.remove();reject(new Error('Brand resource unavailable'));};document.head.appendChild(script);
    });
  });},Promise.resolve());
}

return view.extend({
  load:function(){return Promise.all([inventoryCall().catch(function(){return {profiles:[]};}),statusCall().catch(function(){return {error:'SERVICE-STOPPED'};}),loadBrand()]);},
  render:function(data){
    var configured=!!((data[0].settings||{}).telegram_configured);
    var setup=!configured||new URLSearchParams(window.location.search).get('setup')==='telegram';
    var inventory=data[0],m=new form.Map('homensai_vpn','HomenS.AI Auto VPN',
      tr("Нативный монитор alpha: реальные IPv4 HTTPS/DNS-проверки на роутере. Автоматическое изменение маршрутов пока недоступно."));
    var main=m.section(form.NamedSection,'main','main',tr("Служба наблюдения"));
    main.option(form.Flag,'enabled',tr("Включить наблюдение")).default='0';
    var interval=main.option(form.Value,'interval',tr("Интервал, секунд"));interval.datatype='range(10,300)';interval.default='30';
    var limit=main.option(form.Value,'probe_limit',tr("Лимит подключённых профилей за раунд"));limit.datatype='range(1,32)';limit.default='16';
    var checkpoint=main.option(form.Value,'checkpoint',tr("Сохранение статистики во flash, секунд"));checkpoint.datatype='range(300,3600)';checkpoint.default='900';
    main.option(form.Flag,'telegram_enabled',tr("Отправлять отчёты в Telegram")).default='0';
    var telegramInterval=main.option(form.Value,'telegram_interval',tr("Интервал Telegram-отчётов, минут"));telegramInterval.datatype='range(5,10080)';telegramInterval.default='60';
    var telegramChat=main.option(form.Value,'telegram_chat','Telegram Chat ID');telegramChat.datatype='integer';
    if(setup){
      var telegramToken=main.option(form.Value,'telegram_token',tr("Токен бота · настройка Telegram"));telegramToken.password=true;telegramToken.rmempty=configured;
      telegramToken.cfgvalue=function(){return '';};
      telegramToken.write=function(section,value){if(value)return this.map.data.set('homensai_vpn',section,'telegram_token',value);};
      telegramToken.remove=function(){};
      telegramToken.validate=function(section,value){return !value&&configured||/^[0-9]+:[A-Za-z0-9_-]{20,}$/.test(value)?true:tr("Проверьте формат токена BotFather");};
      telegramToken.description=configured?tr("Оставьте пустым, чтобы сохранить действующий токен."):tr("Токен сохранится на роутере; в отчёты и статус не включается.");
    }

    main.option(form.Flag,'native_session_loss',bi('Allow calls and sessions to reconnect during a trial','Разрешить переподключение звонков и сессий во время теста')).default='0';
    var duration=main.option(form.Value,'native_duration',bi('Trial window, minutes (1–240)','Окно испытания, минут (1–240)'));duration.default='10';duration.datatype='range(1,240)';
    main.option(form.Flag,'plan_enabled',bi('Enable dry-run failover planning','Включить планирование переключения без применения')).default='0';
    var planSource=main.option(form.ListValue,'plan_source',bi('Primary VPN profile','Основной VPN-профиль'));
    var planTarget=main.option(form.ListValue,'plan_target',bi('Reserve VPN profile','Резервный VPN-профиль'));
    [planSource,planTarget].forEach(function(option){option.value('',bi('Select an existing profile','Выберите существующий профиль'));(inventory.profiles||[]).forEach(function(p){option.value(p.id,p.name+' · '+p.protocol);});});

    var servers=m.section(form.GridSection,'server',tr("Каналы и существующие профили"));servers.anonymous=true;servers.addremove=true;
    var name=servers.option(form.Value,'name',tr("Ваше название"));name.datatype='maxlength(64)';
    var profile=servers.option(form.ListValue,'profile',tr("Профиль роутера"));profile.rmempty=false;
    (inventory.profiles||[]).forEach(function(p){profile.value(p.id,p.name+' · '+p.protocol+(p.interface?' · '+p.interface:''));});
    var channel=servers.option(form.Value,'channel',tr("Ваш канал"));channel.default='main';channel.datatype='maxlength(64)';
    var priority=servers.option(form.Value,'priority',tr("Приоритет"));priority.datatype='range(1,1000)';priority.default='100';
    servers.option(form.Flag,'enabled',tr("Наблюдать")).default='1';
    var panel=E('div',{'class':'hv-panel'}),self=this,period='day';
    function draw(status){
      while(panel.firstChild)panel.removeChild(panel.firstChild);
      panel.appendChild(E('p',{'class':'alert-message warning'},
        tr("Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.")));
      if(status.error)panel.appendChild(E('p',{},badge(status.error)));
      var tg=status.telegram||{};panel.appendChild(E('p',{},'Telegram: '+(tg.enabled?(tg.code||(tr("включён · интервал ")+tg.interval_minutes+tr(" мин · последняя отправка ")+(tg.last_sent?new Date(tg.last_sent*1000).toLocaleString():tr("ожидается")))):tr("отключён"))));
      var rows=status.profiles||[];
      var active=rows.filter(function(p){return p.interface;}),healthy=active.filter(function(p){return !p.code;});
      var monthKeys=Object.keys((status.accounting||{}).months||{}).sort(),month=monthKeys.length?(status.accounting.months[monthKeys[monthKeys.length-1]]):null;
      panel.appendChild(E('div',{'class':'hv-metrics'},[
        metric(tr("Подключённые серверы"),active.length+' / '+rows.length,tr("Остальные профили не запускаются")),
        metric(tr("Проверки сейчас"),healthy.length+tr(" из ")+active.length+' OK',tr("HTTPS и DNS с роутера · IPv4")),
        metric(tr("Трафик месяца"),month?bytes(month.rx+month.tx):tr("Нет данных"),tr("Неполный период · с начала наблюдения")),
        metric('Telegram',tg.enabled?(tg.code?tr("Ошибка"):tr("Каждые ")+tg.interval_minutes+tr(" мин")):tr("Отключён"),tg.last_sent?tr("Отправлен ")+new Date(tg.last_sent*1000).toLocaleTimeString():tr("Нет подтверждённой отправки"))
      ]));
      panel.appendChild(E('h3',{},tr("Подключённые VPN-серверы")));
      var cards=E('div',{'class':'hv-server-grid'});
      active.forEach(function(p){cards.appendChild(E('article',{'class':'hv-server '+(p.code?'hv-degraded':'')},[
        E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-protocol'},p.protocol==='wireguard'?'WireGuard':'OpenVPN'),badge(p.code)]),
        E('h4',{},p.name),E('p',{},p.channel+' · '+p.interface),
        E('div',{'class':'hv-latency'},[E('strong',{},Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'),E('span',{},tr(" мс · HTTPS"))]),
        E('small',{},tr("Измерено ")+(p.time?new Date(p.time*1000).toLocaleTimeString():tr("нет данных")))
      ]));});
      if(!active.length)cards.appendChild(E('div',{'class':'hv-empty'},tr("Подключённые серверы не обнаружены.")));
      panel.appendChild(cards);
      panel.appendChild(E('section',{'class':'hv-chart-card'},[E('h3',{},tr("Задержка серверов во времени")),chart(status.samples||[],active)]));
      panel.appendChild(histogram(status.accounting||{},function(value){period=value;draw(status);},period));

      var fp=status.failover_plan||{state:'DISABLED',blockers:[]};
      var states={'DISABLED':bi('Dry-run planner disabled','Планировщик выключен'),'PLAN-CONFIG':bi('Select two different existing profiles in settings','Выберите два разных профиля в настройках'),'TARGET-INACTIVE':bi('Reserve is inactive; it will not be started automatically','Резерв неактивен; автоматически не запускается'),'TARGET-NOT-READY':bi('Waiting for two successful reserve probes','Ожидание двух успешных проверок резерва'),'OBSERVE':bi('Observing; no confirmed switch trigger','Наблюдение: подтверждённого повода переключать нет'),'SWITCH-RECOMMENDED':bi('Reserve recommended; live application is blocked','Резерв рекомендован; настоящее применение заблокировано')};
      var planning=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Failover plan · dry-run','План переключения · без применения')),E('strong',{},states[fp.state]||fp.state),E('p',{},bi('Three confirmed failures on the source and two successful HTTPS/DNS reserve checks are required. Unknown/stale samples do not trigger a switch. This panel never changes VPN, routes or firewall.','Нужны три подтверждённых сбоя источника и две успешные HTTPS/DNS-проверки резерва. Неизвестные и устаревшие данные не запускают переключение. Эта панель не меняет VPN, маршруты или firewall.'))]);
      if(fp.recommendation)planning.appendChild(E('p',{},bi('Proposed target: ','Предложенный резерв: ')+(rows.filter(function(p){return p.id===fp.target;})[0]||{}).name));
      planning.appendChild(E('p',{},bi('Before live use the adapter must verify worker coordination, LAN/DNS paths, Kill Switch, IPv6, special rules, scoped conntrack and an independent rollback watchdog.','Перед эксплуатацией адаптер должен подтвердить согласование workers, пути LAN/DNS, Kill Switch, IPv6, специальные правила, адресную очистку conntrack и независимый watchdog отката.')));
      planning.appendChild(E('code',{},(fp.blockers||[]).join(' · ')));
      panel.appendChild(planning);


      var ns=status.native_failover||{state:'SERVICE-STOPPED'};
      var descriptions={
        'HARDWARE-ACCELERATOR-UNVERIFIED':'Hardware acceleration is not proven disabled',
        'SOFTWARE-ACCELERATOR-UNVERIFIED':'Software acceleration is not proven disabled',
        'SOURCE-RESERVE-NOT-CONFIGURED':'Select and save primary and reserve profiles',
        'POLICY-ORDER-DIRECTION-UNVERIFIED':'The LAN helper must verify policy order',
        'HISTORY-001':'Persistent history storage needs repair; switching is blocked',
        'CLIENT-CONFIRMATION-TIMEOUT':'No valid LAN confirmation; rollback required',
        'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':'Another writer changed policy; traffic guard retained'
      };
      var nativePanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Native failover · controlled trial','Нативное переключение · контролируемый тест')),E('strong',{},ns.state||'UNKNOWN'),E('p',{},bi('1. Save a primary and reserve profile below. 2. Accept session reconnection. 3. Run the downloaded helper on a Windows LAN client with PowerShell 7. It checks the gateway, router DNS, HTTPS and VPN exit, and asks before starting. Browser checks alone do not certify router DNS.','1. Сохраните основной и резервный профили ниже. 2. Разрешите переподключение сессий. 3. Запустите скачанный помощник на Windows-клиенте LAN с PowerShell 7. Он проверит шлюз, DNS роутера, HTTPS и VPN-выход, затем спросит перед запуском. Проверка только браузером не подтверждает DNS роутера.'))]);
      var reasons=E('ul',{});(ns.blockers||[]).forEach(function(code){reasons.appendChild(E('li',{},code+' · '+(descriptions[code]||bi('See diagnostic code in the work log','Смотрите код диагностики в журнале работ'))));});nativePanel.appendChild(reasons);
      nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN test helper','Скачать помощник LAN-теста')));
      nativePanel.appendChild(E('button',{'class':'cbi-button cbi-button-negative','type':'button','click':function(){return rpc.declare({object:'homensai-vpn',method:'native_stop',expect:{}})().then(function(){ui.addNotification(null,E('p',{},bi('Stop requested. Wait for verified rollback status.','Остановка запрошена. Дождитесь подтверждённого состояния отката.')));}).catch(function(){ui.addNotification(null,E('p',{},bi('Stop request failed; recovery is not confirmed.','Запрос остановки не прошёл; восстановление не подтверждено.')));});}},bi('Stop trial and restore','Остановить тест и восстановить')));
      panel.appendChild(nativePanel);
      var nh=status.native_history||{};
      var historyPanel=E('section',{'class':'hv-chart-card'},[E('h3',{},'Persistent controller history'),E('p',{},'Controller events, not measurements of LAN uptime. Trial results and automatic commits are counted separately.')]);
      if(nh.error)historyPanel.appendChild(badge(nh.error));
      if(nh.restored_from_backup)historyPanel.appendChild(E('p',{},'History loaded from the previous valid backup; the latest event may be missing.'));
      var historyTable=E('table',{'class':'table'},[E('tr',{},[E('th',{},'Time · Berlin'),E('th',{},'State'),E('th',{},'Profiles'),E('th',{},'Reason')])]);
      (nh.events||[]).slice().reverse().forEach(function(event){var names=[event.source,event.target].filter(Boolean).map(function(id){return (rows.filter(function(p){return p.id===id;})[0]||{}).name||id;});historyTable.appendChild(E('tr',{},[cell(new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})),cell(event.state+(event.trial?' · '+'trial':'')),cell(names.join(' → ')),cell((event.codes||[]).join(' · '))]));});historyPanel.appendChild(historyTable);
      var monthly=E('table',{'class':'table'},[E('tr',{},[E('th',{},'Month'),E('th',{},'Attempts'),E('th',{},'Trials passed'),E('th',{},'Automatic commits'),E('th',{},'Rollbacks'),E('th',{},'Blocked episodes')])]);
      Object.keys(nh.months||{}).sort().reverse().forEach(function(month){var c=nh.months[month];monthly.appendChild(E('tr',{},[cell(month),cell(c.attempts),cell(c.trials_passed),cell(c.committed),cell(c.rollbacks),cell(c.blocked_episodes)]));});historyPanel.appendChild(monthly);panel.appendChild(historyPanel);

      var table=E('table',{'class':'table'},[E('tr',{'class':'tr table-titles'},[tr("Сервер"),tr("Канал"),tr("Протокол"),tr("Интерфейс"),tr("Результат"),tr("HTTPS, мс"),tr("Время проверки")].map(function(t){return E('th',{},t);} ))]);
      rows.forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[cell(p.name),cell(p.channel),cell(p.protocol),cell(p.interface),E('td',{},badge(p.code)),cell(p.rtt_ms),cell(p.time?new Date(p.time*1000).toLocaleTimeString():'—')]));});
      panel.appendChild(E('h3',{},tr("Текущие проверки серверов")));panel.appendChild(table);
      panel.appendChild(E('p',{},tr("Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.")));
      var samples=status.samples||[],rank={};samples.forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
      Object.keys((status.accounting||{}).quality||{}).forEach(function(id){var q=status.accounting.quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
      var ranked=rows.map(function(p){return {p:p,r:rank[p.id]||{n:0,good:0,sum:0}};}).sort(function(a,b){return (b.r.n?b.r.good/b.r.n:-1)-(a.r.n?a.r.good/a.r.n:-1)||(a.r.good?a.r.sum/a.r.good:Infinity)-(b.r.good?b.r.sum/b.r.good:Infinity);});
      var ranking=E('table',{'class':'table'},[E('tr',{},[tr("Рейтинг измеренных профилей"),tr("Успех проверок"),tr("Средняя HTTPS-задержка")].map(function(t){return E('th',{},t);}))]);
      ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(item.p.name),cell(item.r.n?(100*item.r.good/item.r.n).toFixed(1)+'%':tr("Нет данных")),cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+tr(" мс"):'—')]));});
      panel.appendChild(ranking);panel.appendChild(E('p',{},tr("Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.")));
      var accounting=status.accounting||{},months=accounting.months||{};
      panel.appendChild(E('h3',{},tr("VPN-трафик по календарным месяцам · Europe/Berlin")));
      var traffic=E('table',{'class':'table'},[E('tr',{},[tr("Месяц"),tr("Входящий"),tr("Исходящий"),tr("Всего"),tr("Наблюдение")].map(function(t){return E('th',{},t);}))]);
      Object.keys(months).sort().reverse().forEach(function(key){var v=months[key];traffic.appendChild(E('tr',{},[cell(key),cell(bytes(v.rx)),cell(bytes(v.tx)),cell(bytes(v.rx+v.tx)),cell((v.seconds/3600).toFixed(1)+tr(" интерфейс-часов")+(v.boundary_estimated?tr(" · граница оценена"):''))]));});
      panel.appendChild(traffic);panel.appendChild(E('p',{},tr("Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ")+text(accounting.gaps||0)+tr(". После потери питания возможна потеря последнего интервала checkpoint.")));
      panel.appendChild(E('h3',{},tr("Монитор служб")));
      var terminal=E('pre',{},[]);rows.slice(0,20).forEach(function(p){terminal.appendChild(E('div',{'class':p.code?'error':'notice'},[E('span',{'class':'hv-log-time'},p.time?new Date(p.time*1000).toLocaleTimeString():'—:—:—'),E('strong',{},'  '+p.protocol+' / '+p.name+': '),badge(p.code)]));});panel.appendChild(terminal);
      panel.appendChild(E('button',{'class':'btn','click':function(){var blob=new Blob([JSON.stringify({mode:'router-monitor',events:status.events||[]},null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),link=E('a',{href:url,download:'homensai-vpn-events.json'});link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}},tr("Скачать журнал")));
    }
    draw(data[1]);
    poll.add(function(){return statusCall().then(draw).catch(function(){draw({error:'SERVICE-STOPPED'});});},10);
    return m.render().then(function(form){var robotHost=E('div',{'class':'robo','aria-label':bi('HomenS.AI author robot','Робот автора HomenS.AI')}),footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');setTimeout(function(){var robot=window.HomenS.robot.tvRobot(robotHost);robot.play();robotHost.addEventListener('click',function(){robot.play();});},0);return E('div',{'class':'hv-app'},[
      E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/charts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui12.css')}),
      E('header',{'class':'hv-hero'},[E('div',{'class':'hv-brand-mark'},[robotHost,E('p',{'class':'robo-word'},['HomenS',E('span',{'class':'ai'},'.AI')])]),
        E('div',{},[E('div',{'class':'hv-eyebrow'},'GL.iNet GL-MT6000 · LIVE MONITOR'),E('h2',{},E('a',{href:'https://homensai.com',target:'_blank',rel:'noopener noreferrer'},['HomenS',E('span',{'class':'ai'},'.AI'),E('small',{'class':'hv-product'},' Auto VPN')])),E('p',{},tr("Серверы, качество связи и трафик — реальные измерения на роутере"))]),
        E('div',{'class':'hv-hero-actions'},[E('span',{'class':'hv-version'},'v'+(data[1].version||'unknown')),E('small',{},'HomenS.AI Style 1.14.3'),E('select',{'aria-label':'Language','change':function(ev){localStorage.setItem('homensai-vpn-language',ev.target.value);window.location.reload();}},[E('option',{value:'en',selected:locale==='en'?'':null},'English'),E('option',{value:'ru',selected:locale==='ru'?'':null},'Русский')]),E('button',{'class':'btn hv-test','click':function(){return scanCall().then(function(){ui.addNotification(null,E('p',{},tr("Запрошен раунд проверок подключённых профилей.")));});}},tr("Проверить сейчас"))])
      ]),E('p',{'class':'hv-developer'},[bi('Developer: ','Разработчик: '),E('a',{href:'https://homensai.com',target:'_blank',rel:'noopener noreferrer'},'Serhii Khomenko · HomenS.AI')]),panel,E('a',{'class':'btn',href:L.url('admin/services/homensai-vpn')+'?setup=telegram'},tr("Настроить Telegram")),
      E('details',{'class':'hv-settings',open:setup?'':null},[E('summary',{},setup?tr("Мастер подключения Telegram"):tr("Настройки мониторинга, Telegram и названия серверов")),
        setup?E('div',{'class':'hv-setup'},[E('h3',{},tr("Подключение Telegram")),
          E('ol',{},[E('li',{},tr("Создайте бота через @BotFather и скопируйте токен.")),E('li',{},tr("Отправьте боту /start. Введите свой Chat ID и токен ниже.")),E('li',{},tr("Включите отправку, выберите интервал и нажмите Save & Apply. Роутер отправит первый отчёт; результат появится в статусе Telegram сверху."))]),
          E('p',{},tr("Токен — секрет. После сохранения он не показывается; повторная настройка открывается отдельной кнопкой."))]):null,form]),footer]);});
  }
});
