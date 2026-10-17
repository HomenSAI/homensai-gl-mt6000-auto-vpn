// HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
'use strict';
'require view';

'require rpc';
'require poll';
'require ui';

var savedLanguage='en';
try { savedLanguage=localStorage.getItem('homensai-vpn-language')||'en'; } catch(e) {}
var requestedLanguage=new URLSearchParams(window.location.search).get('lang');
var locale=(requestedLanguage||savedLanguage)==='ru'?'ru':'en';
var translations = {"Туннель не подключён": "Tunnel disconnected", "HTTPS через VPN не проходит": "HTTPS through VPN failed", "DNS не отвечает": "DNS unavailable", "Маршрут не соответствует VPN": "Route does not match VPN", "Путь проверки не подтверждён": "Probe path unverified", "Ошибка службы или зависимости": "Service or dependency error", "Ошибка сохранения статистики": "Statistics storage error", "Статистика восстановлена из резервной копии": "Statistics restored from backup", "Время роутера ещё не установлено": "Router clock is not set", "Профиль сейчас не подключён": "This VPN is not connected", "Профиль вне лимита текущего раунда": "Skipped this round (check limit reached)", "Служба остановлена": "Service unavailable", "График появится после двух успешных измерений. Искусственных данных здесь нет.": "The chart appears after two successful measurements. No synthetic data is used.", "История HTTPS-задержки подключённых серверов в миллисекундах": "HTTPS latency history of connected servers in milliseconds", "HTTPS, мс · последние доступные измерения за час. Разрывы длиннее 90 секунд не соединяются.": "HTTPS, ms · available samples from the last hour. Gaps longer than 90 seconds are not connected.", "Нативный монитор alpha: реальные IPv4 HTTPS/DNS-проверки на роутере. Контролируемое переключение требует клиентской проверки.": "Experimental monitor. It checks every connected VPN from the router over IPv4 (HTTPS and DNS). Automatic switching needs the LAN helper to confirm.", "Служба наблюдения": "Monitoring service", "Включить наблюдение": "Enable monitoring", "Интервал, секунд": "How often to check each VPN, seconds", "Лимит подключённых профилей за раунд": "Most VPNs checked per round", "Сохранение статистики во flash, секунд": "Save statistics every, seconds", "Отправлять отчёты в Telegram": "Send Telegram reports", "Интервал Telegram-отчётов, минут": "Telegram report interval, minutes", "Токен бота · настройка Telegram": "Bot token · Telegram setup", "Проверьте формат токена BotFather": "Check the BotFather token format", "Оставьте пустым, чтобы сохранить действующий токен.": "Leave empty to keep the current token.", "Токен сохранится на роутере; в отчёты и статус не включается.": "The token stays on the router and is excluded from reports and status.", "Каналы и существующие профили": "Channels and existing profiles", "Ваше название": "Display name", "Профиль роутера": "VPN profile on the router", "Ваш канал": "Channel name", "Приоритет": "Priority", "Наблюдать": "Monitor", "Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.": "Monitoring is active. Native controller state is shown below. Router probes do not certify the LAN client path; a trial requires separate client confirmation.", "включён · интервал ": "enabled · interval ", " мин · последняя отправка ": " min · last sent ", "ожидается": "pending", "отключён": "disabled", "Подключённые серверы": "Connected servers", "Остальные профили не запускаются": "Other VPNs are switched off", "Проверки сейчас": "Checks now", " из ": " of ", "HTTPS и DNS с роутера · IPv4": "HTTPS and DNS from the router, IPv4", "Трафик месяца": "Monthly traffic", "Нет данных": "No data", "Неполный период · с начала наблюдения": "Partial period · since monitoring started", "Ошибка": "Error", "Каждые ": "Every ", " мин": " min", "Отключён": "Disabled", "Отправлен ": "Sent ", "Нет подтверждённой отправки": "No confirmed delivery", "Подключённые VPN-серверы": "Connected VPN servers", " мс · HTTPS": " ms · HTTPS", "Измерено ": "Measured ", "нет данных": "no data", "Подключённые серверы не обнаружены.": "No connected servers detected.", "Задержка серверов во времени": "Server latency over time", "Сервер": "Server", "Канал": "Channel", "Протокол": "Protocol", "Интерфейс": "Interface", "Результат": "Result", "HTTPS, мс": "HTTPS, ms", "Время проверки": "Checked at", "Текущие проверки серверов": "Current check per server", "Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.": "VPNs that are not connected are listed but never started by this program. To test one, connect it yourself in the GL.iNet VPN Dashboard.", "Рейтинг измеренных профилей": "Ranking of measured servers", "Успех проверок": "Checks passed", "Средняя HTTPS-задержка": "Average HTTPS latency", " мс": " ms", "Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.": "The ranking uses hourly averages from up to seven days of checks. It is not a speed test and changes no priorities by itself.", "VPN-трафик по календарным месяцам · Europe/Berlin": "VPN traffic by calendar month · Europe/Berlin", "Месяц": "Month", "Входящий": "Received", "Исходящий": "Sent", "Всего": "Total", "Наблюдение": "Observation", " интерфейс-часов": " interface-hours", " · граница оценена": " · estimated month boundary", "Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ": "Unique VPN interfaces are counted once, including protocol overhead. Observation gaps: ", ". После потери питания возможна потеря последнего интервала checkpoint.": ". A power loss may lose the latest checkpoint interval.", "Монитор служб": "Service monitor", "Скачать журнал": "Export events", "Серверы, качество связи и трафик — реальные измерения на роутере": "Servers, connection quality and traffic — real router measurements", "Запрошен раунд проверок подключённых профилей.": "A probe round for connected profiles was requested.", "Проверить сейчас": "Probe now", "Настроить Telegram": "Set up Telegram", "Мастер подключения Telegram": "Telegram setup wizard", "Настройки мониторинга, Telegram и названия серверов": "Monitoring settings, Telegram and server names", "Подключение Telegram": "Connect Telegram", "Создайте бота через @BotFather и скопируйте токен.": "Create a bot with @BotFather and copy its token.", "Отправьте боту /start. Введите свой Chat ID и токен ниже.": "Send /start to your bot. Enter your own chat ID and bot token below.", "Включите отправку, выберите интервал и нажмите Save & Apply. Роутер отправит первый отчёт; результат появится в статусе Telegram сверху.": "Enable reports, select an interval and click Save & Apply. The router sends its first report; delivery status appears above.", "Токен — секрет. После сохранения он не показывается; повторная настройка открывается отдельной кнопкой.": "The token is secret. It is not displayed after saving. Use the separate setup button to replace it."};
function tr(value){return locale==='ru'?value:(translations[value]||value);}
function bi(en,ru){return locale==='ru'?ru:en;}
function diagnosticText(value){return translations[value]||value;}


var statusCall=rpc.declare({object:'homensai-vpn',reject:true,method:'status',expect:{}});
var inventoryCall=rpc.declare({object:'homensai-vpn',reject:true,method:'inventory',expect:{}});
var scanCall=rpc.declare({object:'homensai-vpn',reject:true,method:'scan',expect:{}});
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
  var profiles=Object.keys(accounting.activity||{}).map(function(key){var p=accounting.activity[key],totals={up:0,down:0,unknown:0,connections:0,failures:0};if(p.periods&&p.periods[period]){Object.keys(totals).forEach(function(k){totals[k]=p.periods[period][k]||0;});}else Object.keys(p.days||{}).forEach(function(day){if(period==='day'?day!==today:period==='week'?day<weekStart||day>today:day.slice(0,7)!==today.slice(0,7)||day>today)return;Object.keys(totals).forEach(function(k){totals[k]+=p.days[day][k]||0;});});return {p:p,t:totals};});
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

function autoRequestAcknowledged(result,stop){return !!result&&typeof result==='object'&&result.queued===true&&result.accepted!==false&&(stop||result.accepted===true);}
// Display-only parsing; the controller separately enforces bounded deadlines.
function autoWindowDeadline(intent,settings){
  function positive(raw){
    if(typeof raw==='number')return Number.isFinite(raw)&&raw>0?raw:0;
    if(typeof raw!=='string')return 0;
    raw=raw.trim();if(!raw)return 0;
    if(/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw)){var n=Number(raw);return Number.isFinite(n)&&n>0?n:0;}
    if(!/T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(raw))return 0;
    var parsed=Date.parse(raw)/1000;return Number.isFinite(parsed)&&parsed>0?parsed:0;
  }
  return positive((intent||{}).until)||positive((settings||{}).native_until);
}
function autoControlModel(status,now){
  var ns=status.native_failover||{}, intent=status.auto_control||{};
  var monitorFresh=Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var fresh=!status.rpc_error&&monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var on=fresh&&((ns.state==='OBSERVING'&&ns.certified===true)||ns.state==='COMMITTED');
  var transitioning=fresh&&['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0;
  var off=fresh&&['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(ns.state)>=0;
  var awaiting=fresh&&intent.requested_at>ns.time;
  return {fresh:fresh,on:on,transitioning:transitioning,off:off,awaiting:awaiting,
    stop:on||transitioning||intent.requested==='on'||['DEGRADED-ON-RESERVE','COMMITTED','ARMED','APPLYING','WAIT-CLIENT','RESTORING','STOPPED-ON-RESERVE'].indexOf(ns.state)>=0,
    returned:off&&ns.original_restored===true,
    color:!fresh?'unknown':awaiting||transitioning?'pending':on?'on':off?'off':'error'};
}
function autoPathModel(status,source,target,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{};
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  if(!model.fresh||model.off||model.awaiting)return neutral;
  if(source&&target&&source.id&&source.id===target.id)return neutral;
  var selected=ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE'?'target':ns.state==='OBSERVING'&&ns.certified===true?'source':null;
  if(!selected&&!model.transitioning)return neutral;
  var destination=model.transitioning?(ns.state==='RESTORING'?'source':'target'):null;
  function color(p,key){
    var state=p?profileHealth(p,now).state:'unknown';
    if(state==='failed')return 'failed';
    if(state==='inactive')return 'inactive';
    if(state==='unknown')return 'neutral';
    if(destination===key)return 'checking';
    if(state==='checking')return 'checking';
    return selected===key?'healthy':'ready';
  }
  return {source:color(source,'source'),target:color(target,'target'),direction:destination?(ns.state==='RESTORING'?'back':'forward'):selected==='target'?'forward':'none',moving:!!destination,selected:selected};
}

var AUTO_BLOCKERS={
  'LAN-TRIAL-REQUIRED':['Auto needs a passed LAN trial first: run the LAN helper from a computer on the LAN.','Нужен успешный LAN-тест: запустите LAN-помощник на компьютере в локальной сети.'],
  'BOUNDED-DEADLINE-REQUIRED':['The test window is missing or has expired. Start a new LAN trial.','Окно теста не задано или истекло. Запустите новый LAN-тест.'],
  'SESSION-LOSS-NOT-ACCEPTED':['Confirm in Settings that a short reconnection of calls and sessions is acceptable.','Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим.'],
  'TRANSACTION-IN-PROGRESS':['A switch is already in progress. Wait for it to finish or press Stop.','Переключение уже идёт. Дождитесь окончания или нажмите «Стоп».'],
  'TRIAL-ATTEMPT-LIMIT':['The attempt limit for this window is used up. Start a new LAN trial.','Лимит попыток этого окна исчерпан. Запустите новый LAN-тест.'],
  'UNSUPPORTED-BOARD':['Switching is supported only on GL.iNet GL-MT6000.','Переключение поддерживается только на GL.iNet GL-MT6000.'],
  'UNSUPPORTED-FIRMWARE':['Switching is verified only for GL.iNet firmware 4.11.0.','Переключение проверено только для прошивки GL.iNet 4.11.0.'],
  'FIRMWARE-UNKNOWN':['The router model or firmware could not be read.','Не удалось определить модель или прошивку роутера.'],
  'VENDOR-CODE-CHANGED':['GL.iNet system scripts differ from the audited ones. Switching stays blocked.','Системные скрипты GL.iNet отличаются от проверенных. Переключение заблокировано.'],
  'VENDOR-CODE-UNVERIFIED':['GL.iNet system scripts could not be verified.','Не удалось проверить системные скрипты GL.iNet.'],
  'VENDOR-WORKER-BUSY':['The router is applying its own VPN change right now. Try again in a minute.','Роутер сейчас сам применяет изменение VPN. Повторите через минуту.'],
  'HARDWARE-ACCELERATOR-UNVERIFIED':['Hardware acceleration (HNAT) is not confirmed disabled. It must be off for the LAN check to be trustworthy.','Аппаратное ускорение (HNAT) не подтверждено как выключенное. Для достоверной проверки оно должно быть выключено.'],
  'SOFTWARE-ACCELERATOR-UNVERIFIED':['A software acceleration module is loaded and not confirmed disabled.','Загружен модуль программного ускорения, его отключение не подтверждено.'],
  'FLOW-OFFLOAD-ENABLED':['Firewall flow offloading is on. Turn it off in the router firewall settings.','Включён flow offloading в firewall. Выключите его в настройках firewall роутера.'],
  'IPV6-NOT-EXPLICITLY-DISABLED':['IPv6 must be explicitly turned off on the router (IPv6 leaks are not covered).','IPv6 на роутере должен быть явно выключен (утечки IPv6 не контролируются).'],
  'KILLSWITCH-NOT-ENABLED':['Kill Switch must be on for every active VPN rule.','Kill Switch должен быть включён для каждого активного VPN-правила.'],
  'DIRECT-WAN-FALLBACK':['The router is allowed to bypass the VPN. Disable the direct-internet fallback in GL.iNet VPN settings.','Роутеру разрешён выход мимо VPN. Отключите прямой выход в интернет в настройках VPN GL.iNet.'],
  'VPN-POLICY-DISABLED':['The global VPN policy is off in the router settings.','Глобальная VPN-политика выключена в настройках роутера.'],
  'TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED':['Two or more general (all-traffic) VPN rules are required.','Нужно два или больше общих VPN-правил (для всего трафика).'],
  'GENERIC-RULES-NOT-ADJACENT':['The general VPN rules must follow one another without special rules between them.','Общие VPN-правила должны идти подряд, без специальных правил между ними.'],
  'GENERIC-DUPLICATE-INTERFACE':['Two general rules use the same VPN interface.','Два общих правила используют один и тот же VPN-интерфейс.'],
  'SPECIAL-RULES-MUST-PRECEDE-GENERIC':['Special rules (by device or destination) must be placed before the general rules.','Специальные правила (по устройствам или назначениям) должны стоять до общих.'],
  'SOURCE-RESERVE-NOT-CONFIGURED':['Choose a primary and a different reserve profile in Settings.','Выберите в настройках основной и другой, резервный профиль.'],
  'PROFILE-INACTIVE':['The primary or the reserve tunnel is not connected. Connect both in GL.iNet VPN Dashboard.','Основной или резервный туннель не подключён. Подключите оба в VPN Dashboard GL.iNet.'],
  'PROFILES-NOT-GENERIC-RULES':['The chosen profiles are not general VPN rules in the router policy.','Выбранные профили не являются общими VPN-правилами в политике роутера.'],
  'SAME-INTERFACE':['Primary and reserve use the same interface.','Основной и резервный профили используют один интерфейс.'],
  'POLICY-ORDER-DIRECTION-UNVERIFIED':['The rule order direction is not confirmed yet; the LAN helper sets it.','Направление порядка правил ещё не подтверждено; его задаёт LAN-помощник.'],
  'LAN-LAYOUT-UNSUPPORTED':['The LAN is not on the standard br-lan bridge.','Локальная сеть не на стандартном мосту br-lan.'],
  'PROFILE-NOT-MONITORED':['Enable monitoring for both chosen profiles in Settings.','Включите наблюдение для обоих выбранных профилей в настройках.'],
  'NFT-GUARD-UNAVAILABLE':['The router firewall tool (nft) is unavailable.','Недоступен инструмент firewall роутера (nft).'],
  'POLICY-READ-FAILED':['The router VPN policy could not be read.','Не удалось прочитать VPN-политику роутера.'],
  'UPLINK-LINK-DOWN':['The internet cable/uplink is down; changing VPN would not help.','Нет связи с интернет-провайдером; смена VPN не поможет.'],
  'LEASE-INTEGRITY-FAILED':['The test window record is damaged. Start a new LAN trial.','Запись окна теста повреждена. Запустите новый LAN-тест.'],
  'LEASE-STORAGE-FAILED':['The test window could not be stored on the router.','Не удалось сохранить окно теста на роутере.'],
  'LEGACY-LEASE-RECOVERY':['An old transaction needs recovery; wait or press Stop.','Старая транзакция требует восстановления; подождите или нажмите «Стоп».'],
  'JOURNAL-INTEGRITY-FAILED':['The transaction journal is damaged. Switching is blocked and LAN traffic may be held; see the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций повреждён. Переключение заблокировано, трафик LAN может удерживаться; см. аварийные шаги в router-test-kit/EMERGENCY.md.'],
  'HISTORY-001':['The history file is damaged or the router clock went backwards.','Файл истории повреждён или часы роутера пошли назад.'],
  'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':['The router VPN policy was changed by someone else during a switch; LAN traffic is held. Check the rule order and see router-test-kit/EMERGENCY.md.','Политику VPN роутера изменили во время переключения; трафик LAN удерживается. Проверьте порядок правил, см. router-test-kit/EMERGENCY.md.'],
  'ROLLBACK-UNVERIFIED-GUARD-RETAINED':['The rollback could not be verified; LAN traffic is held. See router-test-kit/EMERGENCY.md.','Откат не удалось подтвердить; трафик LAN удерживается. См. router-test-kit/EMERGENCY.md.'],
  'CLIENT-CONFIRMATION-TIMEOUT':['No confirmation from the LAN computer in time; the router rolled back.','Нет подтверждения от компьютера в LAN; роутер выполнил откат.'],
  'CLIENT-STOP':['Stopped by request.','Остановлено по запросу.'],
  'TARGET-HTTPS-DNS-FAILED':['The reserve did not pass the DNS/HTTPS check.','Резерв не прошёл проверку DNS/HTTPS.'],
  'LAN-BASELINE-NOT-SOURCE':['The LAN computer is not currently using the primary route.','Компьютер в LAN сейчас не использует основной маршрут.'],
  'RESERVE-EXIT-NOT-DISTINCT':['Primary and reserve have the same external IP; the switch could not be proven.','У основного и резервного одинаковый внешний IP; переключение невозможно доказать.'],
  'VENDOR-APPLY-FAILED':['The router failed to apply the change; it was rolled back.','Роутер не смог применить изменение; выполнен откат.'],
  'POLICY-CHANGED-DURING-APPLY':['The policy changed while switching; it was rolled back.','Политика изменилась во время переключения; выполнен откат.'],
  'NATIVE-SYSTEM-001':['Internal controller error. See the Service monitor.','Внутренняя ошибка контроллера. См. «Службу мониторинга».']
};
function autoBlockerText(code){
  var row=Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?AUTO_BLOCKERS[code]:null;
  return row?bi(row[0],row[1]):bi('Unrecognised controller code; see the Service monitor.','Неизвестный код контроллера; см. «Службу мониторинга».');
}
// What must be true before Start can be accepted, in the order the owner can fix it.
var AUTO_LAN_ONLY=['LAN-TRIAL-REQUIRED','BOUNDED-DEADLINE-REQUIRED','SESSION-LOSS-NOT-ACCEPTED'];
function autoReadiness(status,inventory,now){
  var ns=status.native_failover||{},settings=(inventory&&inventory.settings)||{},rows=status.profiles||[];
  var monitorFresh=!status.rpc_error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var controllerFresh=monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  function find(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=find(settings.plan_source),target=find(settings.plan_target);
  var configured=!!(settings.setup_complete&&settings.plan_source&&settings.plan_target&&settings.plan_source!==settings.plan_target&&source&&target);
  var bothHealthy=configured&&profileHealth(source,now).state==='healthy'&&profileHealth(target,now).state==='healthy';
  var technical=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  var certified=controllerFresh&&(ns.certified===true||ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE');
  var steps=[
    {key:'monitor',done:monitorFresh,
     title:bi('Monitor is running','Мониторинг работает'),
     hint:bi('The router status is missing or stale. Open Settings and press Start monitor.','Статус роутера отсутствует или устарел. Откройте «Настройки» и нажмите «Запустить мониторинг».')},
    {key:'profiles',done:bothHealthy,
     title:bi('Primary and reserve are chosen and healthy','Основной и резервный профили выбраны и работают'),
     hint:!configured?bi('Choose a primary and a different reserve in Settings (System setup).','Выберите основной и другой, резервный профиль в «Настройках» (мастер системы).'):bi('Both tunnels must be connected and pass the DNS/HTTPS check. Connect them in GL.iNet VPN Dashboard.','Оба туннеля должны быть подключены и проходить проверку DNS/HTTPS. Подключите их в VPN Dashboard GL.iNet.')},
    {key:'session',done:settings.native_session_loss===true,
     title:bi('Short reconnection of sessions is accepted','Кратковременный разрыв сессий принят'),
     hint:bi('A switch can interrupt calls and downloads for a few seconds. Confirm this in Settings (System setup).','Переключение может на несколько секунд прервать звонки и загрузки. Подтвердите это в «Настройках» (мастер системы).')},
    {key:'router',done:controllerFresh&&technical.length===0,codes:technical,
     title:bi('Router is ready for switching','Роутер готов к переключению'),
     hint:!controllerFresh?bi('The switching controller is not reporting. Check the Service monitor.','Контроллер переключения не отвечает. Проверьте «Службу мониторинга».'):bi('The router reports conditions that block switching (listed below).','Роутер сообщает условия, блокирующие переключение (перечислены ниже).')},
    {key:'trial',done:certified,
     title:bi('LAN trial passed for this pair','LAN-тест для этой пары пройден'),
     hint:bi('On a computer connected by cable run the LAN helper: it briefly switches to the reserve and back and proves DNS, HTTPS and the exit IP from the LAN. Only then Start is accepted.','На компьютере, подключённом кабелем, запустите LAN-помощник: он кратко переключит на резерв и обратно и докажет работу DNS, HTTPS и внешнего IP из LAN. Только после этого «Старт» будет принят.')}
  ];
  var next=steps.filter(function(step){return !step.done;})[0]||null;
  return {steps:steps,next:next,ready:!next};
}

var autoRequestBusy=false;
function renderAutoControl(status,inventory){
  var ns=status.native_failover||{},intent=status.auto_control||{},model=autoControlModel(status,Date.now()/1000);
  var names={on:bi('Auto mode is ON','Авторежим включён'),off:bi('Auto mode is OFF','Авторежим выключен'),pending:bi('Waiting for the router','Ожидание роутера'),error:bi('Auto mode needs attention','Авторежим требует внимания'),unknown:bi('No fresh status from the router','Нет свежего статуса от роутера')};
  var stateText=names[model.color];
  if(model.fresh&&ns.state==='RESTORING')stateText=bi('Restoring previous policy','Восстанавливается предыдущая политика');
  else if(model.awaiting)stateText=intent.requested==='off'?bi('Stopping Auto; waiting for confirmation','Останавливается авторежим: ожидается подтверждение'):bi('Starting Auto; waiting for confirmation','Запускается авторежим: ожидается подтверждение');
  else if(model.transitioning)stateText=bi('Switching; waiting for path confirmation','Переключение: ожидается подтверждение пути');
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-'+model.color,'aria-label':model.stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим'),'aria-pressed':model.on?'true':'false','disabled':autoRequestBusy||(inventory.error||!model.fresh)&&!model.stop?'':null,'click':function(){
    if(autoRequestBusy)return;autoRequestBusy=true;button.disabled=true;
    return rpc.declare({object:'homensai-vpn',reject:true,method:model.stop?'native_stop':'native_start',expect:{}})().then(function(result){
      if(result&&result.accepted===false){ui.addNotification(null,E('div',{},[E('strong',{},'AUTO-START-REFUSED'),E('ul',{},(result.blockers||[]).map(function(code){return E('li',{},code+' · '+autoBlockerText(code));}))]));}
      else if(!autoRequestAcknowledged(result,model.stop))ui.addNotification(null,E('p',{},'AUTO-CONTROL-UNVERIFIED: no confirmed acceptance; check controller state.'));
      else ui.addNotification(null,E('p',{},bi('Request sent. The button changes only when the router confirms it.','Запрос отправлен. Кнопка изменится, только когда роутер подтвердит.')));
    }).catch(function(){ui.addNotification(null,E('p',{},'AUTO-CONTROL-FAILED: no confirmed response; check controller state.'));}).finally(function(){autoRequestBusy=false;button.disabled=false;});
  }},E('span',{'class':'hv-power-symbol','aria-hidden':'true'}));
  var rows=status.profiles||[],settings=inventory.settings||{};
  function profile(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=profile(ns.source||settings.plan_source),target=profile(ns.target||settings.plan_target);
  var path=autoPathModel(status,source,target,Date.now()/1000);
  var pathLabels={neutral:bi('No fresh check','Нет свежей проверки'),healthy:bi('Carries your traffic','Пропускает ваш трафик'),ready:bi('Ready, on standby','Готов, в резерве'),inactive:bi('Not connected','Не подключён'),failed:bi('Not working','Не работает'),checking:bi('Being checked','Проверяется')};
  function box(p,label,key){var state=path[key];return E('div',{'class':'hv-auto-node hv-path-'+state+(path.selected===key?' hv-path-selected':''),'data-path-node':key,'data-path-state':state},[E('small',{},label),E('strong',{},p?(p.protocol==='wireguard'?'WireGuard':'OpenVPN'):'—'),E('span',{},p?p.channel||'default':'—'),E('b',{},p?p.name:bi('Choose in Settings','Выберите в настройках')),E('span',{'class':'hv-path-label'},pathLabels[state]+(path.selected===key&&state!=='healthy'?' · '+bi('Chosen route','Выбранный маршрут'):''))]);}
  var diagram=E('div',{'class':'hv-auto-diagram hv-path-diagram'+(path.moving?' hv-path-moving':'')+(path.direction==='back'?' hv-path-back':''),'aria-label':bi('Configured failover path','Настроенная схема переключения')},[box(source,bi('Primary','Основной'),'source'),E('span',{'class':'hv-auto-arrow '+(path.direction!=='none'?'hv-arrow-on':''),'aria-label':path.moving?bi('Switching in progress','Выполняется переключение'):path.direction!=='none'?bi('Reserve selected','Выбран резерв'):bi('Automatic transition inactive','Автопереход неактивен')},path.direction==='back'?'←':path.direction==='forward'?'→':'⋯'),box(target,bi('Reserve','Резерв'),'target')]);
  var handover=model.returned?bi('Auto is OFF. Control is back with the router; the original route is verified.','Авторежим выключен. Управление вернулось роутеру; исходный маршрут проверен.'):ns.state==='STOPPED-ON-RESERVE'?bi('Auto stopped on the reserve because the primary is not verified healthy. The original route is NOT restored.','Авторежим остановлен на резерве: работа основного не подтверждена. Исходный маршрут НЕ восстановлен.'):model.on?bi('Auto is watching the primary. If it fails, the router switches to the reserve after a LAN computer confirms the new route.','Авторежим следит за основным. При его отказе роутер переключится на резерв после подтверждения нового маршрута компьютером в LAN.'):bi('Monitoring continues; nothing is switched while Auto is OFF.','Мониторинг продолжается; пока авторежим выключен, ничего не переключается.');
  var until=autoWindowDeadline(intent,settings);
  var readiness=autoReadiness(status,inventory,Date.now()/1000);
  var checklist=null;
  if(!model.on&&!model.transitioning&&!model.stop){
    checklist=E('div',{'class':'hv-auto-readiness'},[E('h3',{},readiness.ready?bi('Ready to start','Готово к запуску'):bi('Before you can start Auto','Что нужно перед запуском Auto')),E('ol',{'class':'hv-req-list'},readiness.steps.map(function(step){
      var isNext=readiness.next&&readiness.next.key===step.key;
      var extra=step.key==='router'&&!step.done&&step.codes&&step.codes.length?E('ul',{'class':'hv-req-codes'},step.codes.map(function(code){return E('li',{},[E('code',{},code),' · '+autoBlockerText(code)]);})):null;
      return E('li',{'class':'hv-req hv-req-'+(step.done?'done':isNext?'next':'todo')},[E('span',{'class':'hv-req-mark','aria-hidden':'true'},step.done?'✓':isNext?'→':'·'),E('div',{},[E('strong',{},step.title),step.done?null:E('p',{},step.hint),extra].filter(Boolean)),E('span',{'class':'hv-visually-hidden'},step.done?bi('done','выполнено'):bi('not done','не выполнено'))]);
    })),E('p',{'class':'hv-req-actions'},[E('a',{'class':'cbi-button','href':'#settings'},bi('Open Settings','Открыть настройки')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник'))])]);
  }
  var technicalCode=ns.state?ns.state+(ns.reason?' · '+ns.reason:'')+(model.fresh?'':' · STATUS-STALE'):'UNKNOWN';
  return E('section',{'class':'hv-chart-card hv-auto-control'},[E('h2',{},bi('Automatic VPN failover','Автоматическое переключение VPN')),E('div',{'class':'hv-auto-switch'},[E('div',{'class':'hv-auto-power-unit'},[button,E('span',{'class':'hv-auto-action'},model.stop?bi('Stop','Стоп'):bi('Start','Старт'))]),E('div',{},[E('strong',{'class':'hv-auto-label'},stateText),E('p',{'role':'status','aria-live':'polite'},handover),E('small',{'class':'hv-auto-tech'},bi('Technical state: ','Техническое состояние: ')+technicalCode)])]),checklist,diagram,E('p',{'class':'hv-path-legend'},bi('Green: carries your traffic and works. Grey: on standby, or no fresh check. Yellow: being switched or checked. Red: not working. Both VPNs can stay connected; the diagram shows which one carries your traffic.','Зелёный: пропускает ваш трафик и работает. Серый: в резерве или нет свежей проверки. Жёлтый: переключается или проверяется. Красный: не работает. Оба VPN могут быть подключены; схема показывает, какой из них несёт ваш трафик.')),E('p',{'class':'hv-auto-limit'},bi('Experimental: each automatic switch must be confirmed by the LAN helper running on a computer in your network. Without it the router goes back to the previous route after 90 seconds.','Экспериментально: каждое автоматическое переключение должен подтвердить LAN-помощник на компьютере в вашей сети. Без него роутер через 90 секунд вернётся на прежний маршрут.')+(Number.isFinite(until)&&until>0?' '+bi('Window ends: ','Окно действует до: ')+new Date(until*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB')+'.':''))].filter(Boolean));
}

function setupWizard(inventory,kind){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var setupCheck=kind==='system'?'pending':'passed';
  var step=0,busy=false,closed=false,settings=inventory.settings||{},profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],custom=Array.isArray(inventory.servers)?inventory.servers:[];
  var draft={source:settings.plan_source||'',target:settings.plan_target||'',interval:settings.interval||30,duration:settings.native_duration||10,session_loss:!!settings.native_session_loss,servers:profiles.map(function(p){var saved=custom.filter(function(s){return s.profile===p.id;})[0]||{};return {profile:p.id,name:saved.name||p.name,channel:saved.channel||'default',priority:saved.priority||100,enabled:saved.enabled!==false};})};
  var tg={token:'',chat:settings.telegram_destination||'',enabled:!!settings.telegram_enabled,interval:settings.telegram_interval||60,schedule:settings.telegram_schedule||'interval',hour:settings.telegram_hour==null?7:settings.telegram_hour,weekly:settings.telegram_weekly!==false,monthly:settings.telegram_monthly!==false};
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
        [field(bi('Primary VPN','Основной VPN'),primary),field(bi('Reserve VPN','Резервный VPN'),reserve),field(bi('How often to check each VPN, seconds (10–300)','Как часто проверять каждый VPN, секунд (10–300)'),interval),field(bi('Test window, minutes (1–240)','Окно теста, минут (1–240)'),duration),field(bi('Allow a short interruption of calls and downloads while switching','Разрешить кратковременный разрыв звонков и загрузок при переключении'),consent)].forEach(function(n){body.appendChild(n);});
        body.appendChild(E('p',{},bi('Existing router profiles are reused. This wizard never imports, displays or replaces VPN keys.','Используются существующие профили роутера. Мастер не импортирует, не показывает и не заменяет VPN-ключи.')));
        read=function(){draft.source=primary.value;draft.target=reserve.value;draft.interval=Number(interval.value);draft.duration=Number(duration.value);draft.session_loss=consent.checked;return !!draft.source&&!!draft.target&&draft.source!==draft.target&&Number.isInteger(draft.interval)&&draft.interval>=10&&draft.interval<=300&&Number.isInteger(draft.duration)&&draft.duration>=1&&draft.duration<=240;};
      }else if(step===1){
        body.appendChild(E('p',{},bi('Names, channels and priorities are used for display and ranking only. Real route changes happen only after the LAN trial.','Названия, каналы и приоритеты нужны только для отображения и рейтинга. Реальная смена маршрута возможна только после LAN-теста.')));
        var editors=draft.servers.map(function(row){var name=input(row.name),channel=input(row.channel),priority=input(row.priority,'number'),enabled=input('','checkbox');enabled.checked=row.enabled;body.appendChild(E('fieldset',{},[E('legend',{},row.profile),field(bi('Display name','Название'),name),field(bi('Channel group','Группа канала'),channel),field(bi('Priority (1–1000)','Приоритет (1–1000)'),priority),field(bi('Check this VPN','Проверять этот VPN'),enabled)]));return {row:row,name:name,channel:channel,priority:priority,enabled:enabled};});
        read=function(){var valid=editors.every(function(e){e.row.name=e.name.value.trim();e.row.channel=e.channel.value.trim();e.row.priority=Number(e.priority.value);e.row.enabled=e.enabled.checked;return e.row.name.length>0&&e.row.name.length<=64&&!/[\x00-\x1f]/.test(e.row.name)&&e.row.channel.length>0&&e.row.channel.length<=64&&!/[\x00-\x1f]/.test(e.row.channel)&&Number.isInteger(e.row.priority)&&e.row.priority>=1&&e.row.priority<=1000;});return valid&&draft.servers.some(function(r){return r.profile===draft.source&&r.enabled;})&&draft.servers.some(function(r){return r.profile===draft.target&&r.enabled;});};
      }else{
        body.appendChild(E('h3',{},bi('Review monitoring configuration','Проверьте настройки мониторинга')));
        var source=draft.servers.filter(function(p){return p.profile===draft.source;})[0],target=draft.servers.filter(function(p){return p.profile===draft.target;})[0];
        body.appendChild(E('ul',{},[E('li',{},bi('Primary: ','Основной: ')+(source||{}).name),E('li',{},bi('Reserve: ','Резерв: ')+(target||{}).name),E('li',{},bi('Check interval: ','Интервал проверки: ')+draft.interval+' s'),E('li',{},bi('Test window: ','Окно теста: ')+draft.duration+' min'),E('li',{},bi('Profiles: ','Профилей: ')+draft.servers.length)]));
        body.appendChild(E('p',{},bi('Short interruption allowed: ','Короткий разрыв допустим: ')+(draft.session_loss?bi('Allowed','Разрешено'):bi('Not allowed','Не разрешено'))));
        body.appendChild(E('h3',{},bi('Server metadata to save','Данные серверов для сохранения')));
        var reviewRows=[E('tr',{},[bi('Profile','Профиль'),bi('Display name','Название'),bi('Channel','Канал'),bi('Priority','Приоритет'),bi('Monitor','Наблюдать')].map(function(label){return E('th',{},label);}))].concat(draft.servers.map(function(row){return E('tr',{},[row.profile,row.name,row.channel,String(row.priority),row.enabled?bi('Yes','Да'):bi('No','Нет')].map(function(value){return E('td',{},value);}));}));
        body.appendChild(E('div',{'class':'hv-table-scroll'},E('table',{'class':'hv-table'},reviewRows)));
        body.appendChild(E('p',{},bi('Saving does not start Auto. Next: run the LAN trial, then press Start on the Overview.','Сохранение не запускает Auto. Дальше: пройдите LAN-тест и нажмите «Старт» на странице «Обзор».')));
      }
    }else{
      if(step===0){var token=input(tg.token,'password');token.autocomplete='off';body.appendChild(E('p',{},bi('Create a bot with BotFather. For a channel, add it as an administrator with permission to post. A token is secret and is never returned by the router.','Создайте бота через BotFather. В канале добавьте его администратором с правом публикации. Токен секретный и не возвращается роутером.')));body.appendChild(field(bi('Bot token (leave blank to keep the stored token)','Токен бота (пусто — сохранить имеющийся)'),token));read=function(){tg.token=token.value.trim();return (!tg.token&&settings.telegram_configured)||/^[0-9]{6,15}:[A-Za-z0-9_-]{30,100}$/.test(tg.token);};
      }else if(step===1){
        var chat=input(tg.chat),interval=input(tg.interval,'number'),enabled=input('','checkbox'),hour=input(tg.hour,'number'),weekly=input('','checkbox'),monthly=input('','checkbox');
        var schedule=E('select',{},[E('option',{value:'interval'},bi('Every interval','Через интервал')),E('option',{value:'daily'},bi('Daily at selected hour','Ежедневно в выбранный час'))]);
        schedule.value=tg.schedule;enabled.checked=tg.enabled;weekly.checked=tg.weekly;monthly.checked=tg.monthly;
        chat.placeholder='@channel_name or -100…';
        [field(bi('Channel / destination ID','Канал / ID получателя'),chat),field(bi('Schedule','Расписание'),schedule),field(bi('Report interval, minutes (5–10080)','Интервал отчётов, минут (5–10080)'),interval),field(bi('Daily hour, Europe/Berlin (0–23)','Час отчёта, Europe/Berlin (0–23)'),hour),field(bi('Weekly summary on Monday','Недельная сводка в понедельник'),weekly),field(bi('Monthly summary on day 1','Месячная сводка первого числа'),monthly),field(bi('Enable scheduled reports','Включить отчёты по расписанию'),enabled)].forEach(function(n){body.appendChild(n);});
        read=function(){tg.chat=chat.value.trim();tg.interval=Number(interval.value);tg.enabled=enabled.checked;tg.schedule=schedule.value;tg.hour=Number(hour.value);tg.weekly=weekly.checked;tg.monthly=monthly.checked;return /^(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$/.test(tg.chat)&&Number.isInteger(tg.interval)&&tg.interval>=5&&tg.interval<=10080&&Number.isInteger(tg.hour)&&tg.hour>=0&&tg.hour<=23;};
      }else{
        body.appendChild(E('h3',{},bi('Review Telegram destination','Проверьте получателя Telegram')));
        body.appendChild(E('p',{},bi('Destination: ','Получатель: ')+tg.chat));
        body.appendChild(E('p',{},tg.schedule==='daily'?bi('Daily at ','Ежедневно в ')+String(tg.hour).padStart(2,'0')+':00 Europe/Berlin':bi('Reports every ','Отчёты каждые ')+tg.interval+' min'));
        body.appendChild(E('p',{},bi('Weekly / monthly summaries: ','Недельная / месячная сводка: ')+(tg.weekly?'✓':'—')+' / '+(tg.monthly?'✓':'—')));
        body.appendChild(E('p',{},bi('After saving, use the separate Test delivery button. The stored token is never shown.','После сохранения используйте отдельную кнопку проверки доставки. Сохранённый токен не показывается.')));
      }
    }
    var progress=E('p',{'class':'hv-wizard-progress','role':'status','aria-live':'polite'},'');body.appendChild(progress);
    var actions=E('div',{'class':'hv-wizard-actions'});
    actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){if(busy)return;closed=true;ui.hideModal();}},bi('Cancel','Отмена')));
    if(step>0)actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){if(busy)return;read();step--;show();}},bi('Back','Назад')));
    actions.appendChild(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':kind==='system'&&setupCheck!=='passed'?'':null,'click':function(ev){
      if(busy)return;if(!read()){notify('SETUP-VALIDATION: check profiles, names and numeric ranges.');return;}
      if(step<2){step++;show();return;}
      busy=true;body.setAttribute('aria-busy','true');progress.textContent=bi('Saving settings…','Сохранение настроек…');Array.from(actions.children).forEach(function(node){node.disabled=true;});
      var save=kind==='system'?rpc.declare({object:'homensai-vpn',reject:true,method:'setup_system',params:['source','target','interval','duration','session_loss','servers'],expect:{}})(draft.source,draft.target,draft.interval,draft.duration,draft.session_loss,draft.servers):rpc.declare({object:'homensai-vpn',reject:true,method:'setup_telegram',params:['token','chat','enabled','interval','schedule','hour','weekly','monthly'],expect:{}})(tg.token,tg.chat,tg.enabled,tg.interval,tg.schedule,tg.hour,tg.weekly,tg.monthly);
      return save.then(function(result){if(!result||result.saved!==true){notify(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code)?result.code:'SETUP-SAVE-FAILED');return;}tg.token='';closed=true;ui.hideModal();notify('SETUP-SAVED: settings stored; automatic switching was not started.');window.location.reload();}).catch(function(){notify('SETUP-SAVE-FAILED: no confirmed result.');}).finally(function(){busy=false;body.setAttribute('aria-busy','false');progress.textContent='';Array.from(actions.children).forEach(function(node){node.disabled=false;});});
    }},step<2?bi('Next','Далее'):bi('Save configuration','Сохранить настройки')));
    if(kind==='system'&&setupCheck!=='passed')body.querySelectorAll('input,select').forEach(function(node){node.disabled=true;});
    body.appendChild(actions);ui.showModal(kind==='system'?bi('System setup wizard','Мастер настройки системы'):bi('Telegram channel wizard','Мастер Telegram-канала'),[body]);
  }
  show();
  if(kind==='system')rpc.declare({object:'homensai-vpn',reject:true,method:'setup_check',expect:{}})().then(function(result){if(closed)return;setupCheck=result&&result.passed===true?'passed':'failed';show();}).catch(function(){if(closed)return;setupCheck='failed';show();});
}

var prioritySelections={};
function speedSettings(inventory){
  var s=inventory.settings||{},enabled=E('input',{type:'checkbox'}),auto=E('input',{type:'checkbox'});enabled.checked=!!s.speed_enabled;auto.checked=!!s.speed_auto_new;
  function number(value,label){var n=E('input',{type:'number','aria-label':label});n.value=value;return n;}
  var budget=number(s.speed_budget_mib||8,bi('Payload budget per server, MiB','Лимит полезного трафика на сервер, МиБ')),duration=number(s.speed_duration||5,bi('Measurement seconds per direction','Секунд измерения на направление')),streams=number(s.speed_streams||2,bi('Parallel streams','Параллельные потоки')),daily=number(s.speed_daily_mib||128,bi('Daily reserved quota, MiB','Суточная резервируемая квота, МиБ')),busy=number(s.speed_busy_mbps||2,bi('Skip above current VPN traffic, Mbps','Не запускать при текущем VPN-трафике выше, Мбит/с'));
  function field(text,node){node.setAttribute('aria-label',text);return E('label',{'class':'hv-wizard-field'},[E('span',{},text),node]);}
  var nodes=[E('h3',{},bi('Optional VPN speed tests','Необязательные тесты скорости VPN')),E('p',{},bi('Tests use HTTPS through the chosen VPN and consume bandwidth. Payload quota excludes protocol overhead. Failed attempts keep their quota reservation.','HTTPS-тесты идут через выбранный VPN и расходуют трафик. Квота полезных данных не включает служебный трафик. Резерв квоты сохраняется и при ошибке.')),field(bi('Enable speed tests (off by default)','Включить тесты скорости (по умолчанию выключено)'),enabled),field(bi('Test after a new server connects','Тестировать после подключения нового сервера'),auto),field(budget.getAttribute('aria-label'),budget),field(duration.getAttribute('aria-label'),duration),field(streams.getAttribute('aria-label'),streams),field(daily.getAttribute('aria-label'),daily),field(busy.getAttribute('aria-label'),busy)];
  nodes.push(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;button.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_speed',params:['enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'],expect:{}})(enabled.checked,auto.checked,Number(budget.value),Number(duration.value),Number(streams.value),Number(daily.value),Number(busy.value)).then(function(result){if(!result.saved){ui.addNotification(null,E('p',{},result.code||'SPEED-CONFIG-FAILED'));return;}ui.addNotification(null,E('p',{},'SPEED-CONFIG-SAVED'));window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-CONFIG-FAILED: no confirmed response.'));}).finally(function(){button.disabled=false;});}},bi('Save speed settings','Сохранить настройки скорости')));
  return E('section',{'class':'hv-chart-card hv-speed-settings'},nodes);
}
function speedPanel(status,inventory,period,onPeriod){
  var history=status.speed_tests||{},s=inventory.settings||{},profiles=status.profiles||[],active=profiles.filter(function(p){return p.interface;}).slice(0,8);
  var chooser=E('select',{'aria-label':bi('Speed test server','Сервер для теста скорости')},[E('option',{value:'all'},bi('All listed interfaces (up to 8)','Все перечисленные интерфейсы (до 8)'))].concat(active.map(function(p){return E('option',{value:p.id},p.name+' · '+p.protocol);}))),section=E('section',{'class':'hv-chart-card hv-speed-panel'},[E('h3',{},bi('VPN server speed tests','Тесты скорости VPN-серверов')),E('p',{},bi('Bounded HTTPS payload goodput to Cloudflare. This is a sampled application-level result, not an Ookla score or a guarantee of current capacity. Inactive profiles are not started.','Ограниченное измерение полезной скорости HTTPS до Cloudflare. Это выборочный результат на уровне приложения, не оценка Ookla и не гарантия текущей пропускной способности. Неактивные профили не запускаются.'))]);
  var controls=E('div',{'class':'hv-native-actions'},[chooser,E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':s.speed_enabled&&active.length?null:'','click':function(){
    var selected=chooser.value==='all'?active.map(function(p){return p.id;}):[chooser.value],mib=s.speed_budget_mib||8,duration=s.speed_duration||5,streams=s.speed_streams||2;
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('ul',{},selected.map(function(id){return E('li',{},(profiles.filter(function(p){return p.id===id;})[0]||{}).name||id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;button.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams).then(function(result){ui.addNotification(null,E('p',{},result.accepted?'SPEED-QUEUED':result.code||'SPEED-START-FAILED'));ui.hideModal();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-START-FAILED: no confirmed response.'));}).finally(function(){button.disabled=false;});}},bi('Run test','Запустить тест'))]);
  }},bi('Test speed','Тестировать скорость')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'speed_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.queued?'SPEED-CANCEL-QUEUED':result.code||'SPEED-NOT-RUNNING'));});}},bi('Cancel current test','Отменить текущий тест'))]);
  section.appendChild(controls);
  section.appendChild(E('p',{},bi('Speed test: ','Тест скорости: ')+(history.state||'IDLE')+(history.code?' · '+history.code:'')+' · '+bi('Completed: ','Завершено: ')+(history.completed||0)));
  if(!s.speed_enabled)section.appendChild(E('p',{},E('a',{href:'#settings'},bi('Enable optional tests in Settings','Включите необязательные тесты в настройках'))));
  var select=E('select',{'aria-label':bi('Speed statistics period','Период статистики скорости'),'change':function(ev){onPeriod(ev.target.value);}},[['latest',bi('Latest test','Последний тест')],['day',bi('Today','Сегодня')],['week',bi('Last 7 days','Последние 7 дней')],['month',bi('Current calendar month','Текущий календарный месяц')]].map(function(row){return E('option',{value:row[0]},row[1]);}));select.value=period;section.appendChild(select);
  var now=Date.now()/1000,dateKey=function(t){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t*1000));},today=dateKey(now),rows=(history.results||[]).filter(function(row){return Number.isFinite(row.time)&&row.time<=now+5;});
  rows=rows.filter(function(row){return period==='latest'||period==='day'&&dateKey(row.time)===today||period==='week'&&row.time>=now-7*86400||period==='month'&&dateKey(row.time).slice(0,7)===today.slice(0,7);});
  var grouped={};rows.sort(function(a,b){return b.time-a.time;}).forEach(function(row){var group=grouped[row.id]||(grouped[row.id]={last:row,good:[],count:0});group.count++;if(!row.code&&Number.isFinite((row.download||{}).mbps)&&Number.isFinite((row.upload||{}).mbps))group.good.push(row);});
  var ranked=Object.keys(grouped).map(function(id){var g=grouped[id],good=period==='latest'?(g.good[0]===g.last?[g.last]:[]):g.good;function mean(key){return good.length?good.reduce(function(sum,row){return sum+(row[key]||{}).mbps;},0)/good.length:null;}return {id:id,g:g,down:mean('download'),up:mean('upload'),n:good.length};}).sort(function(a,b){return (b.down===null?-1:b.down)-(a.down===null?-1:a.down);});
  var table=E('table',{'class':'table'},[E('tr',{},[bi('Use','Выбрать'),bi('Server','Сервер'),bi('Protocol / channel','Протокол / канал'),'Download, Mbps','Upload, Mbps',bi('Successful / total tests','Успешных / всего тестов'),bi('Latest result','Последний результат'),bi('Last measured · Berlin','Последнее измерение · Берлин')].map(function(label){return E('th',{},label);} ))]);
  ranked.forEach(function(row){var current=profiles.filter(function(p){return p.id===row.id;})[0],last=row.g.last;var eligible=row.n>0&&!last.code&&current&&current.interface&&current.code==null;var checkbox=E('input',{'type':'checkbox','aria-label':bi('Recommend ','Рекомендовать ')+(current?current.name:last.name),'disabled':eligible?null:'','change':function(){prioritySelections[row.id]=checkbox.checked;}});checkbox.checked=eligible&&!!prioritySelections[row.id];var cells=[current?current.name:last.name,(last.protocol||'unknown')+' / '+(last.channel||'default'),row.down===null?'—':row.down.toFixed(2),row.up===null?'—':row.up.toFixed(2),row.n+' / '+row.g.count,last.code||'OK',new Date(last.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})].map(function(value){return E('td',{},value);});cells.unshift(E('td',{},checkbox));table.appendChild(E('tr',{},cells));});
  section.appendChild(table);
  section.appendChild(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(){var selected=ranked.filter(function(row){var current=profiles.filter(function(p){return p.id===row.id;})[0];return prioritySelections[row.id]&&row.n>0&&!row.g.last.code&&current&&current.interface&&current.code==null;}).map(function(row){return row.id;});if(!selected.length){ui.addNotification(null,E('p',{},'PRIORITY-SELECT-ELIGIBLE-SERVERS'));return;}return reviewPriorities(selected);}},bi('Review recommended priorities','Проверить рекомендуемые приоритеты')));
  if(!ranked.length)section.appendChild(E('p',{},bi('No real speed measurements for this period.','Реальных измерений скорости за этот период нет.')));
  section.appendChild(E('small',{},bi('Mean of successful tests; failed/cancelled tests are not zero-speed samples. History is sampled, bounded and may be partial.','Среднее успешных тестов; ошибки и отмены не считаются нулевой скоростью. История выборочная, ограниченная и может быть неполной.')));
  if(history.history_error)section.appendChild(E('p',{},history.history_error));
  if(history.history_truncated)section.appendChild(E('p',{},'SPEED-HISTORY-TRUNCATED: '+history.history_truncated));
  return section;
}

function trafficHistoryPanel(accounting){
  function dateKey(date){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);}
  var today=dateKey(new Date()),section=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Daily WAN and VPN traffic','Суточный трафик WAN и VPN'))]);
  var wan=accounting.wan||{},vpnDays=accounting.days||{},wanDays=wan.days||{},days=Array.from(new Set(Object.keys(vpnDays).concat(Object.keys(wanDays)))).filter(function(day){return day<=today;}).sort().reverse();
  var table=E('table',{'class':'table'},[E('tr',{},[bi('Date','Дата'),'WAN ↓','WAN ↑','VPN ↓','VPN ↑',bi('Observation gaps','Пропуски измерений')].map(function(title){return E('th',{},title);}))]);
  function value(row,key){return row&&row.observed===true?E('td',{'data-sort-value':Number(row[key]||0)},bytes(Number(row[key]||0))):E('td',{},'—');}
  days.slice(0,90).forEach(function(day){var w=wanDays[day],v=vpnDays[day];table.appendChild(E('tr',{},[E('td',{},day),value(w,'rx'),value(w,'tx'),value(v,'rx'),value(v,'tx'),E('td',{},String((w&&w.gaps||0)+(v&&v.gaps||0)))]));});
  section.appendChild(table);
  if(!days.length)section.appendChild(E('p',{},bi('No daily observations yet. Missing measurements are not zero traffic.','Суточных измерений пока нет. Отсутствие измерений не означает нулевой трафик.')));
  section.appendChild(E('p',{},bi('WAN and VPN counters overlap: never add them together. VPN excludes unmonitored profiles. A dash means no valid counter interval; gaps can coexist with measured traffic. Daily boundary allocation is estimated between samples. Showing up to 90 retained days.','Счётчики WAN и VPN пересекаются: их нельзя складывать. VPN не включает исключённые профили. Прочерк — нет корректного интервала; измерения могут содержать пропуски. Разделение на границе суток оценочное. Показано до 90 сохранённых дней.')));
  if(accounting.rpc_aggregated||accounting.retention&&Object.keys(accounting.retention).length)section.appendChild(E('p',{'class':'alert-message warning'},'HISTORY-PARTIAL: older measurements were aggregated or pruned to limit storage and RPC size.'));
  return section;
}

var RECOVERY_PRESETS={"fast_recovery": {"cooldown": 60, "failures": 3, "min_dwell": 60, "primary_stable": 60, "primary_successes": 3, "return_policy": "healthy_primary", "successes": 2}, "hold_reserve": {"cooldown": 180, "failures": 3, "min_dwell": 180, "primary_stable": 60, "primary_successes": 3, "return_policy": "hold_reserve", "successes": 2}, "stability": {"cooldown": 300, "failures": 5, "min_dwell": 300, "primary_stable": 120, "primary_successes": 5, "return_policy": "healthy_primary", "successes": 3}};
function reviewPriorities(ordered){
  return rpc.declare({object:'homensai-vpn',reject:true,method:'priority_preview',params:['ordered'],expect:{}})(ordered).then(function(result){
    if(!result.accepted){ui.addNotification(null,E('p',{},result.code||'PRIORITY-PREVIEW-FAILED'));return;}
    ui.showModal(bi('Review server priorities','Проверьте приоритеты серверов'),[
      E('p',{},bi('Only application priorities are saved. This does not switch a live route. Unselected profiles follow the selected servers in their existing order.','Сохраняются только приоритеты приложения. Текущий маршрут не переключается. Неотмеченные профили следуют за выбранными в прежнем порядке.')),
      E('ol',{},result.rows.map(function(row){return E('li',{},row.name+' · '+row.protocol+' / '+row.channel+(row.enabled?'':' · disabled'));})),
      E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),
      E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){var button=ev.currentTarget;button.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'priority_apply',params:['ordered','revision'],expect:{}})(ordered,result.revision).then(function(saved){ui.addNotification(null,E('p',{},saved.code||'PRIORITY-UNKNOWN'));if(saved.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'PRIORITY-RPC-UNCONFIRMED'));}).finally(function(){button.disabled=false;});}},bi('Apply priorities','Применить приоритеты'))
    ]);
  }).catch(function(){ui.addNotification(null,E('p',{},'PRIORITY-PREVIEW-UNCONFIRMED'));});
}
function recoveryWizard(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},step=0,presetName='';
  var labels={failures:bi('Consecutive failures before switching (3–10)','Сбоев подряд до переключения (3–10)'),successes:bi('Reserve checks that must pass (2–10)','Проверок резерва, которые должны пройти (2–10)'),cooldown:bi('Pause between switch attempts, seconds (60–1800)','Пауза между попытками переключения, секунд (60–1800)'),min_dwell:bi('Minimum time to stay on a route, seconds (60–3600)','Минимальное время на маршруте, секунд (60–3600)'),primary_successes:bi('Primary checks that must pass before returning (2–10)','Проверок основного, которые должны пройти перед возвратом (2–10)'),primary_stable:bi('The primary must stay healthy for, seconds (30–600)','Основной должен оставаться исправным, секунд (30–600)')};
  var defaults={failures:3,successes:2,cooldown:180,min_dwell:180,return_policy:'healthy_primary',primary_successes:3,primary_stable:60},draft={};
  Object.keys(defaults).forEach(function(key){draft[key]=settings['recovery_'+key]==null?defaults[key]:settings['recovery_'+key];});
  // A saved set that equals a reviewed preset is shown as that preset; any other set is Custom.
  Object.keys(RECOVERY_PRESETS).forEach(function(name){var row=RECOVERY_PRESETS[name];if(!presetName&&Object.keys(defaults).every(function(key){return String(row[key])===String(draft[key]);}))presetName=name;});
  function show(){
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;};
    body.appendChild(E('p',{},bi('These rules decide when Auto switches to the reserve and when it returns. They apply only inside a LAN-tested time window. Auto never connects a VPN that is switched off.','Эти правила определяют, когда Auto переходит на резерв и когда возвращается. Они действуют только внутри окна, прошедшего LAN-тест. Auto никогда не подключает выключенный VPN.')));
    if(step===0){
      var presetSelect=E('select',{'aria-label':bi('Recovery preset','Профиль восстановления')},[
        E('option',{value:''},bi('Custom settings','Свои настройки')),E('option',{value:'stability'},bi('Stability','Стабильность')),E('option',{value:'fast_recovery'},bi('Fast recovery','Быстрое восстановление')),E('option',{value:'hold_reserve'},bi('Hold healthy reserve','Сохранять работающий резерв'))]);
      presetSelect.value=presetName;
      presetSelect.addEventListener('change',function(){presetName=presetSelect.value;var preset=RECOVERY_PRESETS[presetName];if(!preset)return;Object.keys(preset).forEach(function(key){draft[key]=preset[key];});show();});
      body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Preset (review before saving)','Профиль (проверьте перед сохранением)')),presetSelect]));
      var editors={};Object.keys(labels).forEach(function(key){var node=E('input',{type:'number','aria-label':labels[key]});node.value=draft[key];node.addEventListener('input',function(){presetName='';presetSelect.value='';});editors[key]=node;body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},labels[key]),node]));});
      var policy=E('select',{'aria-label':bi('Return policy','Политика возврата')},[E('option',{value:'healthy_primary'},bi('Return to the primary once it has been healthy for a while','Вернуться на основной, когда он некоторое время исправен')),E('option',{value:'hold_reserve'},bi('Stay on the working reserve until you decide','Оставаться на рабочем резерве, пока вы не решите иначе'))]);policy.value=draft.return_policy;policy.addEventListener('change',function(){presetName='';presetSelect.value='';});body.appendChild(policy);
      read=function(){var limits={failures:[3,10],successes:[2,10],cooldown:[60,1800],min_dwell:[60,3600],primary_successes:[2,10],primary_stable:[30,600]};var valid=Object.keys(editors).every(function(key){draft[key]=Number(editors[key].value);return Number.isInteger(draft[key])&&draft[key]>=limits[key][0]&&draft[key]<=limits[key][1];});draft.return_policy=policy.value;return valid;};
    }else{
      body.appendChild(E('h3',{},bi('Review recovery settings','Проверьте настройки восстановления')));
      body.appendChild(E('ul',{},Object.keys(labels).map(function(key){return E('li',{},labels[key]+': '+draft[key]);})));
      body.appendChild(E('p',{},bi('Return policy: ','Политика возврата: ')+draft.return_policy));
      body.appendChild(E('p',{},bi('Changing these rules cancels the earlier LAN test. Auto stays off; run the LAN helper again before you start Auto.','Изменение правил отменяет прежний LAN-тест. Auto остаётся выключенным; перед запуском Auto снова запустите LAN-помощник.')));
    }
    var actions=[E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена'))];
    if(step)actions.push(E('button',{'type':'button','class':'cbi-button','click':function(){step=0;show();}},bi('Back','Назад')));
    actions.push(E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){if(!read()){ui.addNotification(null,E('p',{},'RECOVERY-RANGE'));return;}if(!step){step=1;show();return;}var button=ev.currentTarget;button.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_recovery',params:['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable'],expect:{}})(draft.failures,draft.successes,draft.cooldown,draft.min_dwell,draft.return_policy,draft.primary_successes,draft.primary_stable).then(function(result){ui.addNotification(null,E('p',{},result.saved?'RECOVERY-SAVED':result.code||'RECOVERY-SAVE-FAILED'));if(result.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'RECOVERY-SAVE-UNCONFIRMED'));}).finally(function(){button.disabled=false;});}},step?bi('Save recovery settings','Сохранить настройки восстановления'):bi('Next','Далее')));
    body.appendChild(E('div',{'class':'hv-wizard-actions'},actions));ui.showModal(bi('Recovery setup wizard','Мастер восстановления'),[body]);
  }
  show();
}

function monitorPreferences(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},interval=E('input',{type:'number','aria-label':bi('How often to check each VPN, seconds','Как часто проверять каждый VPN, секунд')}),checkpoint=E('input',{type:'number','aria-label':bi('Save statistics every, seconds','Сохранять статистику каждые, секунд')}),limit=E('input',{type:'number','aria-label':bi('Most VPNs checked per round','Максимум VPN за один раунд проверки')}),planning=E('input',{type:'checkbox','aria-label':bi('Show the failover forecast on the Overview','Показывать прогноз переключения на странице «Обзор»')});
  interval.value=settings.interval||30;checkpoint.value=settings.checkpoint||900;limit.value=settings.probe_limit||16;planning.checked=!!settings.plan_enabled;
  var body=E('div',{'class':'hv-wizard'},[E('p',{},bi('Only this program’s own settings change. Saving statistics more often wears the router flash memory faster. This does not start Auto or connect any VPN.','Меняются только настройки этой программы. Частое сохранение статистики быстрее изнашивает флеш-память роутера. Auto не запускается, VPN не подключаются.'))]);
  [[bi('How often to check each VPN (10–300 seconds)','Как часто проверять каждый VPN (10–300 секунд)'),interval],[bi('Save statistics every (300–3600 seconds)','Сохранять статистику каждые (300–3600 секунд)'),checkpoint],[bi('Most VPNs checked per round (1–16)','Максимум VPN за один раунд проверки (1–16)'),limit],[bi('Show the failover forecast','Показывать прогноз переключения'),planning]].forEach(function(row){body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},row[0]),row[1]]));});
  body.appendChild(E('div',{'class':'hv-wizard-actions'},[E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){var button=ev.currentTarget;button.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_monitor',params:['interval','checkpoint','probe_limit','planning_enabled'],expect:{}})(Number(interval.value),Number(checkpoint.value),Number(limit.value),planning.checked).then(function(result){ui.addNotification(null,E('p',{},result.saved?'MONITOR-PREFERENCES-SAVED':result.code||'MONITOR-PREFERENCES-FAILED'));if(result.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-PREFERENCES-UNCONFIRMED'));}).finally(function(){button.disabled=false;});}},bi('Save monitoring preferences','Сохранить параметры мониторинга'))]));
  ui.showModal(bi('Monitoring preferences','Параметры мониторинга'),[body]);
}

function faultPanel(status,inventory,refresh){
  var state=status.operator_fault||{},native=status.native_failover||{},settings=inventory.settings||{},profiles=status.profiles||[],sourceId=native.source||settings.plan_source,source=profiles.filter(function(p){return p.id===sourceId;})[0];
  var ready=native.state==='OBSERVING'&&native.certified===true&&!status.rpc_error&&0<=Date.now()/1000-native.time&&Date.now()/1000-native.time<=30&&0<=Date.now()/1000-status.time&&Date.now()/1000-status.time<=90;
  var section=E('section',{'class':'hv-chart-card'},[E('h2',{},bi('Simulate a VPN failure (test)','Имитация сбоя VPN (тест)')),E('p',{},bi('This briefly blocks internet traffic through the chosen VPN while it stays connected, to reproduce “connected, but no internet”. Access to the router itself and the Kill Switch are not changed.','Временно блокирует интернет-трафик через выбранный VPN, не отключая его, чтобы воспроизвести «подключён, но интернета нет». Доступ к самому роутеру и Kill Switch не меняются.'))]);
  section.appendChild(E('p',{'role':'status'},'Operator test: '+(state.code||state.state||'IDLE')+(state.until?' · '+bi('Remaining about ','Осталось примерно ')+(state.remaining_seconds==null?Math.max(0,Math.ceil(state.until-Date.now()/1000)):state.remaining_seconds)+' s':'')));
  var scope=E('select',{'aria-label':bi('Failure scope','Область сбоя')},[E('option',{value:'profile'},bi('Current primary server','Текущий основной сервер')),E('option',{value:'channel'},bi('Its channel group','Его группа канала'))]);
  var duration=E('select',{'aria-label':bi('Fault duration','Длительность сбоя')},[30,60,120,150,180].map(function(value){return E('option',{value:String(value)},value+' s');}));duration.value='150';
  section.appendChild(E('p',{},bi('Selected source: ','Выбранный источник: ')+(source?source.name:'—')));
  section.appendChild(E('div',{'class':'hv-native-actions'},[scope,duration,E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','disabled':ready&&source?null:'','click':function(){
    var affected=scope.value==='profile'?[source]:profiles.filter(function(p){return p.interface&&p.channel===source.channel;});
    ui.showModal(bi('Review deliberate traffic interruption','Подтвердите прерывание трафика'),[E('p',{},bi('Calls and sessions can reconnect. Use only during an agreed local test. A kernel timeout limits the rule even if the watchdog stops. A healthy reserve and enough certified-window time are required.','Звонки и сессии могут переподключиться. Используйте только в согласованном локальном тесте. Правило ограничено таймером ядра даже при остановке watchdog. Нужен исправный резерв и достаточный остаток подтверждённого окна.')),E('ul',{},affected.map(function(p){return E('li',{},p.name+' · '+p.protocol+' / '+p.channel);})),E('p',{},bi('Maximum fault duration: ','Максимальная длительность сбоя: ')+duration.value+' s'),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','click':function(ev){var button=ev.currentTarget;button.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'fault_start',params:['profile','scope','duration'],expect:{}})(source.id,scope.value,Number(duration.value)).then(function(result){ui.addNotification(null,E('p',{},result.code||'FAULT-UNKNOWN'));ui.hideModal();return refresh();}).catch(function(){ui.addNotification(null,E('p',{},'FAULT-RPC-UNCONFIRMED: inspect actual test state.'));}).finally(function(){button.disabled=false;});}},bi('Start bounded fault','Запустить ограниченный сбой'))]);
  }},bi('Simulate server failure','Имитировать отказ сервера')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'fault_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'FAULT-CANCEL-UNKNOWN'));return refresh();});}},bi('Cancel fault now','Отменить сбой сейчас'))]));
  if(!ready)section.appendChild(E('p',{'class':'alert-message warning'},'FAULT-CERTIFIED-AUTO-REQUIRED: certify the configured source/reserve with the LAN helper and start a bounded trial first.'));
  section.appendChild(E('small',{},bi('Inactive profiles are not started. This is a traffic fault, not a VPN service stop. Auto mode Stop also requests fault cleanup.','Неактивные профили не запускаются. Это сбой трафика, а не остановка VPN-службы. Остановка авторежима также запрашивает очистку сбоя.')));
  if(state.history&&state.history.length){var table=E('table',{'class':'table'},[E('tr',{},['Time · Berlin','Code','Profiles','Scope'].map(function(text){return E('th',{},text);} ))]);state.history.slice().reverse().forEach(function(row){table.appendChild(E('tr',{},[new Date(row.time*1000).toLocaleString('en-GB',{timeZone:'Europe/Berlin'}),row.code,(row.profiles||[]).join(', '),row.scope].map(function(value){return E('td',{},value);})));});section.appendChild(table);}
  return section;
}

function loadInventory(attempt){
  return inventoryCall().then(function(data){
    if(!data||typeof data!=='object'||!Array.isArray(data.profiles)||!Array.isArray(data.servers)||!data.settings||typeof data.settings.enabled!=='boolean')throw new Error('RPC-INVENTORY-INVALID');
    return data;
  }).catch(function(){
    if(attempt<2)return new Promise(function(resolve){setTimeout(resolve,250*(attempt+1));}).then(function(){return loadInventory(attempt+1);});
    return {profiles:[],servers:[],settings:{},error:'RPC-INVENTORY-UNAVAILABLE'};
  });
}

function profileHealth(profile,now){
  if(!profile.interface)return {state:'inactive',label:bi('Inactive','Неактивен')};
  if(!Number.isFinite(profile.time)||now-profile.time<0||now-profile.time>90)return {state:'unknown',label:bi('Unknown / stale','Неизвестно / устарело')};
  if(['CHECK-001','CHECK-LIMIT'].indexOf(profile.code)>=0)return {state:'checking',label:bi('Checking','Проверяется')};
  if(profile.code)return {state:'failed',label:bi('Failed','Сбой')};
  if(profile.dns_ok===true&&profile.https_success>=2)return {state:'healthy',label:bi('Healthy','Работает')};
  return {state:'checking',label:bi('Checking','Проверяется')};
}
function selectedProfile(status,now){
  var native=status.native_failover||{};
  if(status.rpc_error||!Number.isFinite(native.time)||now-native.time<0||now-native.time>30)return null;
  if(['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(native.state)>=0)return native.target||null;
  if(native.state==='OBSERVING'&&native.certified===true)return native.source||null;
  return null;
}
function sortServerCards(rows,selected,now){
  var ranks={healthy:1,checking:2,unknown:3,inactive:4,failed:5};
  return rows.map(function(row,index){var state=profileHealth(row,now).state;return {row:row,index:index,rank:state==='healthy'&&row.id===selected?0:ranks[state]};}).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).map(function(entry){return entry.row;});
}
function healthBadge(profile){
  var health=profileHealth(profile,Date.now()/1000);
  return E('strong',{'class':'hv-badge hv-health-'+health.state,'title':profile.code||health.label},health.label+(profile.code?' · '+profile.code:''));
}
function compareTableValues(a,b,direction){
  var unknown=function(value){return value==null||/^(?:\s*|—|No data|Нет данных)$/.test(String(value).trim());};
  if(unknown(a)!==unknown(b))return unknown(a)?1:-1;
  var x=String(a==null?'':a).trim(),y=String(b==null?'':b).trim(),nx=Number(x.replace(/%$/,'')),ny=Number(y.replace(/%$/,''));
  var result=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});
  return direction==='desc'?-result:result;
}

/* HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT */
function cascadePathModel(status,now){
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&now>=status.time&&now-status.time<=90;
  var selected=fresh?selectedProfile(status,now):null,rows=status.profiles||[];
  var current=rows.find(function(p){return p.id===selected;});
  if(!current)selected=null;
  var groups=[],candidates=[];
  rows.forEach(function(p){
    var protocol=p.protocol==='wireguard'?'WireGuard':p.protocol==='openvpn'?'OpenVPN':'Unknown';
    var channel=String(p.channel||'default');
    var group=groups.find(function(g){return g.protocol===protocol&&g.channel===channel;});
    if(!group){group={protocol:protocol,channel:channel,servers:[]};groups.push(group);}
    var state=fresh?profileHealth(p,now).state:'unknown';
    var enabled=p.enabled!==false&&p.enabled!=='0';
    var reason=p.id===selected?'SELECTED-BY-CONTROLLER':!enabled?'DISABLED':state==='healthy'?'EDGE-NOT-CERTIFIED':state.toUpperCase();
    group.servers.push({id:p.id,name:p.name||p.id,state:state,selected:p.id===selected,reason:reason});
    if(current&&p.id!==selected&&enabled&&state==='healthy')candidates.push({id:p.id,
      tier:p.protocol!==current.protocol?2:p.channel!==current.channel?1:0,
      priority:Number.isFinite(Number(p.priority))?Number(p.priority):Infinity});
  });
  candidates.sort(function(a,b){return a.tier-b.tier||a.priority-b.priority||String(a.id).localeCompare(String(b.id));});
  groups.forEach(function(g){g.servers.sort(function(a,b){return Number(b.selected)-Number(a.selected);});});
  groups.sort(function(a,b){return Number(b.servers.some(function(s){return s.selected;}))-Number(a.servers.some(function(s){return s.selected;}));});
  return {selected:selected,groups:groups,next:candidates.length?candidates[0].id:null,fresh:fresh};
}
function renderCascadePath(status){
  var model=cascadePathModel(status,Date.now()/1000);
  return E('section',{'class':'hv-chart-card'},[
    E('h2',{},bi('Protocol / channel / server path','Путь: протокол / канал / сервер')),
    E('p',{},bi('Selected route requires fresh controller evidence. Candidate suggestions do not authorize switching.','Выбранный маршрут требует свежего подтверждения контроллера. Рекомендация кандидата не разрешает переключение.')),
    E('p',{},bi('Next healthy suggestion: ','Следующий работающий кандидат: ')+(model.next||'—')+' · EDGE-NOT-CERTIFIED'),
    E('div',{'class':'hv-cascade-grid'},model.groups.map(function(g){return E('section',{'class':'hv-auto-node'},[
      E('strong',{},g.protocol),E('b',{},g.channel),E('ul',{},g.servers.map(function(s){return E('li',{},[
        E('strong',{'class':'hv-badge hv-health-'+s.state},s.selected?bi('Selected','Выбран'):({healthy:bi('Healthy','Работает'),failed:bi('Failed','Сбой'),checking:bi('Checking','Проверяется'),inactive:bi('Inactive','Неактивен'),unknown:bi('Unknown','Неизвестно')}[s.state]||s.state)),
        E('span',{},' '+s.name+(s.id===model.next?' → '+bi('Candidate','Кандидат'):'')),
        E('small',{},s.reason)
      ]);} ))
    ]);})),
    E('small',{},bi('Hierarchy: another server → another channel → another VPN protocol. No implicit direct-WAN fallback.','Каскад: другой сервер → другой канал → другой протокол VPN. Автоматического выхода напрямую в WAN нет.'))
  ]);
}
function retainedTransitions(history){
  var events=(history.events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}),rows=[],open=null,last=null,lastTime=null;
  function close(outcome,event){if(!open)return;open.outcome=outcome;
    if(event&&Number.isFinite(event.time)&&event.time>=open.start){open.end=event.time;open.duration=open.applied_at==null?null:event.time-open.applied_at;}
    rows.push(open);open=null;
  }
  function identifier(value){return Number.isSafeInteger(value)&&value>0?value:null;}
  function begin(e){open={id:identifier(e.attempt_id)||e.sequence,retry_episode_id:identifier(e.retry_episode_id),
    prepared_at:e.state==='ARMED'?e.time:null,applied_at:e.state==='APPLYING'?e.time:null,start:e.time,end:null,duration:null,
    source:e.source||'unknown',target:e.target||'unknown',
    kind:['server','channel','protocol'].indexOf(e.transition_kind)>=0?e.transition_kind:'unknown',
    trial:e.trial===true,outcome:'pending',phases:[],codes:[],probe_evidence:{}};}
  events.forEach(function(e){
    if(!Number.isFinite(e.time)||e.time<0||e.time>253402300799||!Number.isSafeInteger(e.sequence)||e.sequence<1)return;
    if(last!==null&&e.sequence<=last)return;
    if(lastTime!==null&&e.time<lastTime){close('unknown',null);last=e.sequence;return;}
    lastTime=e.time;
    if(last!==null&&e.sequence!==last+1)close('unknown',null);
    last=e.sequence;
    var trialPassed=(e.codes||[]).indexOf('TRIAL-PASSED')>=0;
    var starting=e.state==='APPLYING'||e.state==='ARMED'&&!trialPassed;
    if(starting){
      var same=open&&open.applied_at==null&&(e.state==='APPLYING'||identifier(e.attempt_id)===open.id)&&
        (!e.attempt_id||e.attempt_id===open.id)&&(!e.source||e.source===open.source)&&(!e.target||e.target===open.target);
      if(!same){close('unknown',null);begin(e);}
      else if(e.state==='APPLYING'){open.applied_at=e.time;open.start=e.time;if(['server','channel','protocol'].indexOf(e.transition_kind)>=0)open.kind=e.transition_kind;}
    }
    if(!open)return;
    if(e.trial===true)open.trial=true;
    if((identifier(e.attempt_id)&&e.attempt_id!==open.id)||(e.source&&e.source!==open.source)||(e.target&&e.target!==open.target)){close('unknown',null);return;}
    open.phases.push({state:e.state,time:e.time});
    (e.codes||[]).forEach(function(code){if(typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)&&open.codes.indexOf(code)<0)open.codes.push(code);});
    var evidence=e.probe_evidence||{};
    ['source_streak_met','reserve_streak_met'].forEach(function(key){if(typeof evidence[key]==='boolean')open.probe_evidence[key]=evidence[key];});
    ['required_failures','required_successes'].forEach(function(key){if(Number.isInteger(evidence[key])&&evidence[key]>=2&&evidence[key]<=10)open.probe_evidence[key]=evidence[key];});
    if(Array.isArray(e.phase_evidence)){
      var phases=e.phase_evidence.filter(function(p){return p&&/^[A-Z0-9_-]{1,96}$/.test(p.phase)&&Number.isFinite(p.time)&&p.time<=e.time;});
      if(phases.length){open.phases=phases.map(function(p){return {state:p.phase,time:p.time};});if(open.phases[open.phases.length-1].state!==e.state)open.phases.push({state:e.state,time:e.time});}
    }
    if(e.state==='COMMITTED')close('committed',e);
    else if(trialPassed)close('trial_passed',e);
    else if(e.state==='ROLLED-BACK')close('rolled_back',e);
    else if(['BLOCKED','STOPPED','STOPPED-ON-RESERVE','EXPIRED'].indexOf(e.state)>=0)close('held',e);
  });
  close('pending',null);
  return rows;
}

function recoverySummary(rows,start,end){
  var selected=rows.filter(function(r){return r.start>=start&&r.start<end;}),durations=[],known=0,committed=0,trialsPassed=0;
  var streaks=Object.create(null),maxFailures=0;
  selected.slice().sort(function(a,b){return a.start-b.start;}).forEach(function(r){
    var outcome=r.end!=null&&r.end>=end?'pending':r.outcome;
    if(['committed','trial_passed','rolled_back','held'].indexOf(outcome)>=0)known++;
    if(outcome==='committed')committed++;
    if(outcome==='trial_passed')trialsPassed++;
    if(['committed','trial_passed','rolled_back'].indexOf(outcome)>=0&&Number.isFinite(r.duration)&&r.duration>=0)durations.push(r.duration);
    streaks[r.target]=['rolled_back','held'].indexOf(outcome)>=0?(streaks[r.target]||0)+1:0;
    maxFailures=Math.max(maxFailures,streaks[r.target]);
  });
  durations.sort(function(a,b){return a-b;});
  var n=durations.length;
  return {attempts:selected.length,known_outcomes:known,unknown_or_pending:selected.length-known,
    trial_attempts:selected.filter(function(r){return r.trial===true;}).length,
    automatic_attempts:selected.filter(function(r){return r.trial!==true;}).length,
    committed:committed,trials_passed:trialsPassed,success_ratio:known?(committed+trialsPassed)/known:null,recovered_samples:n,
    median:n?(durations[Math.floor((n-1)/2)]+durations[Math.floor(n/2)])/2:null,
    p95:n?durations[Math.ceil(n*0.95)-1]:null,worst:n?durations[n-1]:null,max_consecutive_failures:maxFailures};
}
function recoveryWindow(period,now,timezone){
  timezone=timezone||'Europe/Berlin';
  var formatter=new Intl.DateTimeFormat('en-GB',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  function localEpoch(stamp){var parts={};formatter.formatToParts(new Date(stamp)).forEach(function(p){parts[p.type]=p.value;});return Date.UTC(Number(parts.year),Number(parts.month)-1,Number(parts.day),Number(parts.hour),Number(parts.minute),Number(parts.second));}
  var d=new Date(localEpoch(now*1000));d.setUTCHours(0,0,0,0);
  if(period==='week')d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
  else if(period==='month')d.setUTCDate(1);
  else if(period!=='day')throw new Error('RECOVERY-PERIOD');
  var desired=d.getTime(),candidate=desired;
  for(var i=0;i<3;i++)candidate=desired-(localEpoch(candidate)-candidate);
  return {start:candidate/1000,end:now,timezone:timezone};
}
function recoveryGroups(rows,profiles,start,end){
  var result={server:{},channel:{},protocol:{}};
  rows.forEach(function(row){var p=profiles.find(function(p){return p.id===row.target;})||{};
    [['server',row.target],['channel',p.channel||'unknown'],['protocol',p.protocol||'unknown']].forEach(function(pair){
      // Prefix untrusted labels, so '__proto__' is never an object prototype write.
      var key='group:'+pair[1];if(!result[pair[0]][key])result[pair[0]][key]={name:pair[1],rows:[]};result[pair[0]][key].rows.push(row);
    });
  });
  Object.keys(result).forEach(function(kind){result[kind]=Object.keys(result[kind]).map(function(key){var g=result[kind][key];return {name:g.name,metrics:recoverySummary(g.rows,start,end)};});});
  return result;
}
var exportSchemas={
  ranking:['server','name','protocol','channel','latency_ms','state'],
  traffic:['month','rx_bytes','tx_bytes','scope'],
  failures:['start_utc','source','target','outcome','codes','attempt_id','retry_episode_id'],
  transitions:['start_utc','source','target','kind','outcome','duration_seconds','trial','attempt_id','retry_episode_id','source_streak_met','reserve_streak_met','required_failures','required_successes']
};
function analyticsCSV(kind,rows){
  var columns=exportSchemas[kind];if(!columns)throw new Error('EXPORT-KIND');
  function cell(value){var text=value==null?'':String(value);
    if(/^[\s\u0000-\u001f\u007f\ufeff\u200b-\u200f\u202a-\u202e\u2060-\u206f]*[=+@-]/.test(text)||/^[\t\r\n]/.test(text))text="'"+text;
    return '"'+text.replace(/"/g,'""')+'"';}
  return '\ufeff'+[columns.map(cell).join(',')].concat(rows.map(function(row){return columns.map(function(key){return cell(row[key]);}).join(',');})).join('\r\n')+'\r\n';
}
function analyticsExportRows(kind,status,transitions){
  if(kind==='ranking')return (status.profiles||[]).map(function(p){return {server:p.id,name:p.name,protocol:p.protocol,channel:p.channel,
    latency_ms:p.rtt_ms,state:status.rpc_error?'unknown':profileHealth(p,Date.now()/1000).state};});
  if(kind==='traffic')return Object.keys((status.accounting||{}).months||{}).sort().map(function(month){var r=status.accounting.months[month];return {month:month,rx_bytes:r.rx,tx_bytes:r.tx,scope:'Observed interface counters; partial collection; overhead included'};});
  var rows=kind==='failures'?transitions.filter(function(r){return ['rolled_back','held'].indexOf(r.outcome)>=0;}):transitions;
  return rows.map(function(r){return {start_utc:new Date(r.start*1000).toISOString(),source:r.source,target:r.target,kind:r.kind,
    outcome:r.outcome,duration_seconds:r.duration,trial:r.trial,codes:r.codes.join(' | '),attempt_id:r.id,retry_episode_id:r.retry_episode_id,
    source_streak_met:r.probe_evidence.source_streak_met,reserve_streak_met:r.probe_evidence.reserve_streak_met,
    required_failures:r.probe_evidence.required_failures,required_successes:r.probe_evidence.required_successes};});
}
var recoveryAnalyticsPeriod='day';
try {var savedRecoveryPeriod=localStorage.getItem('homensai-vpn-recovery-period');if(['day','week','month'].indexOf(savedRecoveryPeriod)>=0)recoveryAnalyticsPeriod=savedRecoveryPeriod;}catch(error){}
function renderTransitionAnalytics(status){
  var history=status.native_history||{},rows=retainedTransitions(history),now=Date.now()/1000;
  var summaryHost=E('div'),groupHost=E('div'),period=E('select',{'aria-label':bi('Recovery period','Период восстановления')},[
    E('option',{'value':'day'},bi('Day','Сутки')),E('option',{'value':'week'},bi('Week','Неделя')),E('option',{'value':'month'},bi('Month','Месяц'))]);
  var selectedRows=rows,table;
  period.value=recoveryAnalyticsPeriod;
  function update(){var window;
    try {window=recoveryWindow(period.value||'day',now,history.timezone||'Europe/Berlin');}
    catch(error){summaryHost.textContent='RECOVERY-TIMEZONE-UNKNOWN: metrics unavailable';return;}
    var s=recoverySummary(rows,window.start,window.end);
    selectedRows=rows.filter(function(r){return r.start>=window.start&&r.start<window.end;});
    if(table)table.querySelectorAll('tr[data-recovery-start]').forEach(function(row){var at=Number(row.getAttribute('data-recovery-start'));row.hidden=!(at>=window.start&&at<window.end);});
    summaryHost.textContent=bi('Attempts / known outcomes / pending or unknown: ','Попытки / известный результат / ожидание или неизвестно: ')+s.attempts+' / '+s.known_outcomes+' / '+s.unknown_or_pending+
      ' · '+bi('Trial / automatic attempts: ','Тестовые / автоматические попытки: ')+s.trial_attempts+' / '+s.automatic_attempts+
      ' · '+bi('Verified outcome ratio (including trials): ','Доля подтверждённых результатов (включая тесты): ')+(s.success_ratio==null?'—':(s.success_ratio*100).toFixed(1)+'%')+
      ' · '+bi('Recovery median / P95 / worst (s): ','Восстановление: медиана / P95 / максимум (с): ')+[s.median,s.p95,s.worst].map(function(v){return v==null?'—':v.toFixed(1);}).join(' / ');
    while(groupHost.firstChild)groupHost.removeChild(groupHost.firstChild);
    var groups=recoveryGroups(rows,status.profiles||[],window.start,window.end);
    Object.keys(groups).forEach(function(kind){groupHost.appendChild(E('p',{},kind+': '+groups[kind].map(function(g){var m=g.metrics;return g.name+' · '+(m.committed+m.trials_passed)+'/'+m.known_outcomes+' · P95 '+(m.p95==null?'—':m.p95.toFixed(1))+' s · consecutive failures '+m.max_consecutive_failures;}).join(' | ')));});
  }
  period.addEventListener('change',function(){recoveryAnalyticsPeriod=period.value;try{localStorage.setItem('homensai-vpn-recovery-period',recoveryAnalyticsPeriod);}catch(error){}update();});update();
  var exports=E('div',{'class':'hv-wizard-launch'},Object.keys(exportSchemas).map(function(kind){return E('button',{'type':'button','class':'cbi-button','click':function(){
    var text=analyticsCSV(kind,analyticsExportRows(kind,status,selectedRows)),url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
    var link=document.createElement('a');link.href=url;link.download='homensai-vpn-'+kind+'.csv';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
  }},'CSV · '+kind);}));
  exports.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){downloadIncidentReport(selectedRows);}},bi('Printable incident report','Отчёт об инцидентах для печати')));
  table=E('table',{'class':'table'},[E('tr',{},['UTC','Source','Target','Outcome','Seconds','Codes','Details'].map(function(h){return E('th',{},h);}))]);
  rows.forEach(function(r){var detail=E('button',{'type':'button','class':'cbi-button','click':function(){showIncident(r);}},bi('Details','Подробности'));table.appendChild(E('tr',{'data-recovery-start':String(r.start)},[new Date(r.start*1000).toISOString(),r.source,r.target,r.outcome,
    r.duration==null?'—':String(r.duration),'Attempt #'+r.id+' / retry episode #'+(r.retry_episode_id||'unknown')+' · '+r.codes.join(' · ')+' · '+JSON.stringify(r.probe_evidence)+' · '+r.phases.map(function(p){return p.state+' @ '+new Date(p.time*1000).toISOString();}).join(' → ')].map(function(v){return E('td',{},v);}).concat([E('td',{},detail)])));
  });
  update();
  var stamps=(history.events||[]).map(function(e){return e.time;}).filter(function(at){return Number.isFinite(at)&&at>=0&&at<=253402300799;});
  var latest=stamps.length?Math.max.apply(null,stamps):null;
  var age=latest==null?'No retained event timestamp':latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' s since latest retained event';
  return E('section',{'class':'hv-chart-card'},[E('h2',{},bi('Transition evidence and recovery','Подтверждения переходов и восстановления')),
    E('p',{},bi('Retained controller events only. Missing sequences produce unknown outcomes. Probe/client details absent from this history remain unknown.','Только сохранённые события контроллера. Пропуски номеров дают неизвестный результат. Отсутствующие проверки сервера и клиента остаются неизвестными.')),
    E('p',{},bi('Coverage: incomplete retained window; not measured LAN availability.','Покрытие: неполное сохранённое окно; это не измерение доступности LAN.')),
    E('p',{},age),
    E('small',{},'Calendar boundaries: '+(history.timezone||'Europe/Berlin')+'. Event timestamps: UTC. Durations measure retained APPLYING → controller-confirmed outcome events, not full outage duration. Retry episode IDs describe controller evidence, not certified LAN outages. Categories overlap and must not be summed.'),
    period,summaryHost,groupHost,exports,table]);
}

function renderDecisionExplanation(status){
  var explanation=status.decision_explanation||{},diagnosis=explanation.diagnosis||{},native=status.native_failover||{};
  var codeNames={'OBSERVATION-UNKNOWN':bi('Insufficient observations','Недостаточно измерений'),'OBSERVATION-STALE':bi('Observations are stale','Измерения устарели'),'UPLINK-LINK-DOWN':bi('Configured uplink is down; VPN cycling is paused','Настроенный uplink отключён; перебор VPN приостановлен'),'TUNNEL-DISCONNECTED':bi('Tunnel disconnected','Туннель отключён'),'ROUTE-MISMATCH':bi('Route mismatch','Маршрут не соответствует VPN'),'PATH-UNVERIFIED':bi('Probe path unverified','Путь проверки не подтверждён'),'DNS-FAILED':bi('DNS failed','Отказ DNS'),'HTTPS-FAILED':bi('HTTPS failed','Отказ HTTPS'),'VPN-PROBE-HEALTHY':bi('VPN DNS/HTTPS checks passed','Проверки DNS/HTTPS через VPN успешны')};
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&Date.now()/1000-status.time>=0&&Date.now()/1000-status.time<=90;
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Why the controller acts','Почему контроллер принимает решение')),E('p',{},fresh?(codeNames[diagnosis.code]||bi('No current diagnosis','Нет текущего диагноза')):bi('Current evidence unavailable','Текущие измерения недоступны')),E('p',{},bi('Source failure threshold: ','Порог ошибок основного: ')+(explanation.required_failures||'—')+' · '+bi('Confirmed: ','Подтверждено: ')+(fresh&&explanation.source_failure_streak_met===true?bi('Yes','Да'):bi('No','Нет'))),E('p',{},bi('Reserve success threshold: ','Порог успешных проверок резерва: ')+(explanation.required_successes||'—')+' · '+bi('Confirmed: ','Подтверждено: ')+(fresh&&explanation.reserve_success_streak_met===true?bi('Yes','Да'):bi('No','Нет'))),E('p',{},bi('Order: server → channel → VPN protocol; operator priority within each level.','Порядок: сервер → канал → протокол VPN; внутри уровня — приоритет оператора.')),E('p',{},bi('Controller reason: ','Причина контроллера: ')+(native.reason||native.state||'UNKNOWN')),E('small',{},bi('Router-only probes do not confirm the LAN client path. Native transitions require separate certification.','Проверки с роутера не подтверждают путь LAN-клиента. Нативным переходам требуется отдельное подтверждение.'))]);
}

function resolveRouterVpnUrl(pageUrl,previewOrigin){
  var page;try{page=new URL(pageUrl);}catch(e){return null;}
  if(['http:','https:'].indexOf(page.protocol)<0||page.username||page.password)return null;
  var local=['localhost','127.0.0.1','[::1]'].indexOf(page.hostname.toLowerCase())>=0;
  if(local){
    if(!previewOrigin)return null;
    var router;try{router=new URL(previewOrigin);}catch(e){return null;}
    if(['http:','https:'].indexOf(router.protocol)<0||router.username||router.password||router.search||router.hash||router.pathname!=='/'||['localhost','127.0.0.1','[::1]'].indexOf(router.hostname.toLowerCase())>=0)return null;
    return router.origin+'/#/vpndashboard';
  }
  // GL.iNet and LuCI use separate listeners. Never carry LuCI's port into GL UI.
  return page.protocol+'//'+page.hostname+'/#/vpndashboard';
}

// A queued RPC is never proof of a completed network measurement.
var connectivityRequest=null,connectivityBusy=false,connectivityControl=null,connectivityLatest={},connectivityFailure=false;
function connectivityModel(status,request,now){
  var row=status.scan||{},id=request&&request.request_id||row.request_id;
  var requested=request&&request.requested_at||row.requested_at;
  if(!id)return {state:status.rpc_error||status.error?'UNAVAILABLE':'IDLE',busy:false};
  if(status.rpc_error)return {state:'UNAVAILABLE',busy:true};
  if(!Number.isFinite(requested)||now<requested-5||(row.state!=='COMPLETED'&&now-requested>300))return {state:'FAILED',busy:false,code:'SCAN-DEADLINE-EXCEEDED'};
  if(row.request_id!==id)return {state:'QUEUED',busy:true};
  if(row.state==='COMPLETED'){
    if(row.measurement_request_id!==id||!Number.isFinite(row.measured_at)||row.measured_at<requested||!Number.isFinite(row.finished_at)||row.finished_at>now+5||!Number.isInteger(row.checked)||!Number.isInteger(row.failed)||row.checked<0||row.failed<0||row.failed>row.checked)return {state:'UNAVAILABLE',busy:false,code:'SCAN-SNAPSHOT-UNCONFIRMED'};
    return {state:row.checked?'COMPLETED':'EMPTY',busy:false,time:row.measured_at,checked:row.checked,failed:row.failed};
  }
  if(row.state==='FAILED')return {state:'FAILED',busy:false,code:row.code||'SCAN-MEASUREMENT-FAILED'};
  return {state:row.state==='RUNNING'?'RUNNING':'QUEUED',busy:true};
}
function updateConnectivityCheck(status){
  connectivityLatest=status;
  if(!connectivityControl)return;
  var model=connectivityModel(status,connectivityRequest,Date.now()/1000);
  if(connectivityFailure)model={state:'UNAVAILABLE',busy:false};
  var labels={EMPTY:bi('No VPN is connected, so there was nothing to check','Ни один VPN не подключён, проверять нечего'),IDLE:bi('Ready','Готово'),QUEUED:bi('Queued','В очереди'),RUNNING:bi('Checking DNS and HTTPS…','Проверяется DNS и HTTPS…'),COMPLETED:bi('Check finished','Проверка завершена'),FAILED:bi('The check could not run','Проверку выполнить не удалось'),UNAVAILABLE:bi('No result: the router did not confirm a new measurement','Результата нет: роутер не подтвердил новое измерение')};
  connectivityControl.button.disabled=connectivityBusy||model.busy||status.error==='SERVICE-STOPPED';
  connectivityControl.message.textContent=labels[model.state]+(model.time?' · '+new Date(model.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}):'')+(model.checked!=null?' · '+bi('VPNs checked: ','Проверено VPN: ')+model.checked+' · '+bi('with problems: ','с проблемами: ')+model.failed:'')+(model.code?' · '+model.code:'');
  connectivityControl.message.setAttribute('data-check-state',model.state);
  connectivityControl.button.setAttribute('aria-busy',model.busy?'true':'false');
}
function renderConnectivityCheck(status,refresh){
  var message=E('p',{'role':'status','aria-live':'polite'});
  var button=E('button',{'type':'button','class':'btn hv-primary-action hv-connectivity-action','click':function(){
    if(connectivityBusy||button.disabled)return;
    connectivityBusy=true;connectivityFailure=false;button.disabled=true;message.textContent=bi('Sending the request…','Отправляется запрос…');
    return scanCall().then(function(result){
      if(!result||result.queued!==true||!/^([a-f0-9]{32})$/.test(result.request_id)||!Number.isFinite(result.requested_at))throw new Error('SCAN-ACK-UNCONFIRMED');
      connectivityRequest={request_id:result.request_id,requested_at:result.requested_at};
      message.textContent=bi('Request sent; waiting for the router to measure','Запрос отправлен; роутер выполняет измерение');
      return refresh();
    }).catch(function(){connectivityFailure=true;message.textContent=bi('The router did not confirm the request. Make sure the monitor is running (Settings → Start monitor) and try again.','Роутер не подтвердил запрос. Убедитесь, что мониторинг запущен («Настройки» → «Запустить мониторинг»), и повторите.');}).finally(function(){connectivityBusy=false;updateConnectivityCheck(connectivityLatest);});
  }},bi('Check VPN now','Проверить VPN сейчас'));
  connectivityControl={button:button,message:message};
  var node=E('section',{'class':'hv-connectivity-control'},[button,E('small',{},bi('Runs one extra internet check through every connected VPN right now. The router already repeats it automatically; use this after you change something. Nothing is switched and no speed is measured.','Запускает одну внеочередную проверку интернета через каждый подключённый VPN. Роутер и так повторяет её сам; нажмите после изменений. Ничего не переключается, скорость не измеряется.')),message]);
  updateConnectivityCheck(status);return node;
}

// Viewport-only layout; never reads router state or changes navigation policy.
function sidebarGeometry(height,top,header,width){
  if(width<=760)return {mobile:true,top:0,height:0,tiny:false};
  var sticky=Math.max(12,Math.ceil(header)+12);
  var available=Math.max(80,Math.floor(height-Math.max(sticky,top)-12));
  return {mobile:false,top:sticky,height:available,tiny:available<320};
}
function updateSidebarLayout(root,reveal){
  if(!root||!root.isConnected)return;
  var sidebar=root.querySelector('.hv-sidebar'),nav=sidebar&&sidebar.querySelector('nav');if(!nav)return;
  var headerBottom=0;
  document.querySelectorAll('header,.navbar,#fixture-banner').forEach(function(el){
    if(root.contains(el))return;
    var style=getComputedStyle(el),r=el.getBoundingClientRect();
    if((style.position==='fixed'||style.position==='sticky')&&r.top<=2&&r.bottom>0&&r.height<window.innerHeight*.5)headerBottom=Math.max(headerBottom,r.bottom);
  });
  var geometry=sidebarGeometry(window.innerHeight,sidebar.getBoundingClientRect().top,headerBottom,window.innerWidth);
  if(geometry.mobile){sidebar.style.removeProperty('--hv-sidebar-top');sidebar.style.removeProperty('--hv-sidebar-height');}
  else{sidebar.style.setProperty('--hv-sidebar-top',geometry.top+'px');sidebar.style.setProperty('--hv-sidebar-height',geometry.height+'px');}
  sidebar.classList.toggle('hv-sidebar-tiny',geometry.tiny);
  if(reveal&&!geometry.mobile){var active=nav.querySelector('[aria-current=page]');if(active){var scroller=geometry.tiny?sidebar:nav,a=active.getBoundingClientRect(),n=scroller.getBoundingClientRect();if(a.bottom>n.bottom)scroller.scrollTop+=a.bottom-n.bottom+4;if(a.top<n.top)scroller.scrollTop-=n.top-a.top+4;}}
}
function initSidebarLayout(root){
  var scheduled=false,reveal=false;
  function schedule(event){reveal=reveal||!!(event&&event.type==='resize');if(scheduled)return;scheduled=true;requestAnimationFrame(function(){scheduled=false;var show=reveal;reveal=false;updateSidebarLayout(root,show);});}
  window.addEventListener('resize',schedule,{passive:true});window.addEventListener('scroll',schedule,{passive:true});
  if(window.ResizeObserver){var observer=new ResizeObserver(function(){schedule({type:'resize'});});document.querySelectorAll('.navbar,#fixture-banner').forEach(function(el){if(!root.contains(el))observer.observe(el);});var nav=root.querySelector('.hv-sidebar nav');if(nav)observer.observe(nav);}
  setTimeout(function(){updateSidebarLayout(root,true);},0);
}

/* Allowlisted evidence; safe printable HTML generated locally in the browser. */
function incidentText(value){
  return String(value==null?'unknown':value).slice(0,1000)
    .replace(/-----BEGIN[\s\S]*?-----END[^-]*-----/g,'[REDACTED]')
    .replace(/\b\d{6,12}:[A-Za-z0-9_-]{20,}\b/g,'[REDACTED]')
    .replace(/\b(?:ghp_|github_pat_)[A-Za-z0-9_]+/g,'[REDACTED]')
    .replace(/https?:\/\/[^\s]+/g,'[URL REDACTED]')
    .replace(/\b(?:token|password|secret|private[_ -]?key)\s*[:=]\s*[^\s,;]+/gi,'[REDACTED]');
}
function incidentFields(row){
  return {attempt:incidentText(row.id),source:incidentText(row.source),target:incidentText(row.target),
    outcome:incidentText(row.outcome),codes:(row.codes||[]).slice(0,32).map(incidentText),
    phases:(row.phases||[]).slice(0,64).map(function(p){return incidentText(p.state)+' @ '+(Number.isFinite(p.time)&&p.time>=0&&p.time<=253402300799?new Date(p.time*1000).toISOString():'unknown');}),
    scope:'Retained controller evidence; gaps and missing client/DNS evidence remain unknown. This is not measured LAN outage duration.'};
}
function incidentHTML(rows){
  function esc(v){return incidentText(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>HomenSAI incident report</title><style>body{font:16px sans-serif;max-width:900px;margin:2rem auto;padding:1rem}section{break-inside:avoid;border:1px solid #aaa;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{margin:0}}</style></head><body><h1>HomenSAI incident report</h1><p>Print this document and choose Save as PDF. No external resources or scripts.</p>'+rows.slice(0,100).map(function(row){var f=incidentFields(row);return '<section><h2>Attempt '+esc(f.attempt)+'</h2><p>'+esc(f.source)+' → '+esc(f.target)+' · '+esc(f.outcome)+'</p><pre>'+esc(f.codes.join(' | '))+'\n'+esc(f.phases.join('\n'))+'</pre><p>'+esc(f.scope)+'</p></section>';}).join('')+'</body></html>';
}
function downloadIncidentReport(rows){
  var url=URL.createObjectURL(new Blob([incidentHTML(rows)],{type:'text/html;charset=utf-8'}));
  var link=document.createElement('a');link.href=url;link.download='homensai-incidents.html';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
}
function showIncident(row){
  var f=incidentFields(row);ui.showModal(bi('Incident evidence','Подтверждения инцидента'),[
    E('p',{},f.source+' → '+f.target+' · '+f.outcome),E('p',{},f.codes.join(' · ')||'CAUSE-UNKNOWN'),
    E('ol',{},f.phases.map(function(phase){return E('li',{},phase);})),E('p',{},f.scope),
    E('button',{'type':'button','class':'cbi-button','click':function(){downloadIncidentReport([row]);}},bi('Download printable report','Скачать отчёт для печати')),
    E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть'))
  ]);
}

/* Read-only readiness; missing evidence never grants Auto permission. */
function readinessModel(status,now){
  var data=status.system_readiness||{},native=status.native_failover||{};
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&now>=status.time&&now-status.time<=90;
  var environmentFresh=fresh&&Number.isFinite(data.time)&&now>=data.time&&now-data.time<=90;
  var blockers=Array.isArray(native.blockers)?native.blockers.slice(0,32):[];
  if(!environmentFresh)blockers.push('ENVIRONMENT-EVIDENCE-UNAVAILABLE');
  if(!fresh)blockers.push('MONITOR-EVIDENCE-STALE');
  if(!blockers.length)blockers.push('NATIVE-START-CERTIFICATION-REQUIRED');
  return {fresh:fresh,environmentFresh:environmentFresh,board:environmentFresh?data.board||{}:{},
    checks:environmentFresh&&Array.isArray(data.checks)?data.checks.slice(0,16):[],blockers:blockers,
    auto:(status.auto_control||{}).requested==='on'&&fresh?'requested':'off_or_unknown'};
}
function renderReadiness(status){
  var m=readinessModel(status,Date.now()/1000);
  return E('section',{'class':'hv-chart-card'},[
    E('h2',{},bi('System readiness','Готовность системы')),
    E('p',{},bi('Actual environment: ','Фактическая среда: ')+(m.board.model||'unknown')+' · '+(m.board.board_name||'unknown')+' · '+(m.board.firmware||'unknown')),
    E('p',{},bi('Monitor evidence: ','Измерения монитора: ')+(m.fresh?bi('Fresh','Свежие'):bi('Unavailable or stale','Недоступны или устарели'))),
    E('ul',{'class':'hv-readiness-list'},m.checks.map(function(c){return E('li',{},String(c.code)+' · '+String(c.state));})),
    E('h3',{},bi('What Auto needs','Что нужно для Auto')),
    E('ul',{'class':'hv-readiness-list'},m.blockers.map(function(c){return E('li',{},String(c));})),
    E('p',{},bi('These checks only show whether the router has what the program needs. Pressing Start on the Overview repeats the real checks: device, test window, LAN confirmation and a safe way back. Auto never starts by itself after a reboot.','Эти проверки лишь показывают, есть ли на роутере всё нужное программе. Кнопка «Старт» на странице «Обзор» повторяет настоящие проверки: устройство, окно теста, подтверждение из LAN и безопасный путь назад. После перезагрузки Auto сам не запускается.'))
  ]);
}

return view.extend({
  handleSave:null,handleSaveApply:null,handleReset:null,
  load:function(){return Promise.all([loadInventory(0),statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};}),loadBrand()]);},
  render:function(data){
    var configured=!!((data[0].settings||{}).telegram_configured);
    var setup=new URLSearchParams(window.location.search).get('setup')==='telegram';
    var inventory=data[0];
    var panel=E('div',{'class':'hv-panel'}),self=this,period='day',speedPeriod='week';
    var lastGoodStatus=data[1];
    var pointerHeld=false,deferredStatus=null;
    var appRoot=null,settingsHost=null,heading=null,sideState=null,versionBadge=null,pages={},sortStates={},searchTerms={};
    var tabs=[['overview','◉',bi('Overview','Обзор')],['channels','⇄',bi('Channels and servers','Каналы и серверы')],['tests','⏻',bi('Diagnostics','Диагностика')],['statistics','▥',bi('Statistics','Статистика')],['ranking','↕',bi('Server ranking','Рейтинг серверов')],['traffic','◷',bi('Monthly traffic','Трафик за месяц')],['services','▣',bi('Service monitor','Монитор служб')],['events','≡',bi('Events and errors','События и ошибки')],['readiness','✓',bi('System readiness','Готовность системы')],['settings','⚙',bi('Settings','Настройки')]];
    function routerVpnUrl(){return resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);}
    function vpnSetupCard(){return E('section',{'class':'hv-chart-card hv-vpn-setup'},[E('div',{'class':'hv-auto-power-unit'},[E('a',{'class':'hv-auto-power hv-vpn-configure','href':routerVpnUrl()||null,'aria-disabled':routerVpnUrl()?null:'true','title':routerVpnUrl()?null:bi('Router address unavailable in this preview','Адрес роутера недоступен в этом просмотре'),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('Open router VPN settings (opens a new tab)','Открыть настройки VPN роутера (новая вкладка)')},E('span',{'aria-hidden':'true','class':'hv-configure-symbol'},'⚙')),E('strong',{'class':'hv-auto-action'},bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗'))]),E('p',{},bi('Add servers and connection keys in the router VPN Client Profile page. Monitoring and failover priorities are configured here.','Добавляйте серверы и ключи на странице VPN Client Profile роутера. Мониторинг и приоритеты переключения настраиваются здесь.'))]);}
    function validTab(key){return tabs.some(function(t){return t[0]===key;});}
    var activeTab=setup?'settings':window.location.hash.slice(1);if(!validTab(activeTab))activeTab='overview';
    function showPage(key){
      var oldTab=activeTab;if(!validTab(key))key='overview';activeTab=key;
      var scope=appRoot||panel;scope.querySelectorAll('[data-hv-page]').forEach(function(node){node.hidden=node.getAttribute('data-hv-page')!==key;});
      if(appRoot)appRoot.querySelectorAll('[data-hv-tab]').forEach(function(node){node.setAttribute('aria-current',node.getAttribute('data-hv-tab')===key?'page':'false');});
      if(appRoot){var checks=appRoot.querySelector('.hv-connectivity-control');if(checks)checks.hidden=key!=='overview';}
      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);
      if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];
    }
    function put(key,node){
      if(!pages[key]){pages[key]=E('section',{'class':'hv-page','data-hv-page':key});panel.appendChild(pages[key]);}
      pages[key].appendChild(node);return node;
    }
    function sortableTables(){
      panel.querySelectorAll('table').forEach(function(table,index){
        var headers=table.querySelectorAll('tr:first-child th'),tableKey=(table.closest('[data-hv-page]')||{dataset:{hvPage:'overview'}}).dataset.hvPage+':'+Array.from(headers).map(function(th){return th.textContent;}).join('|');
        function applySort(column,direction){
          var entries=Array.prototype.slice.call(table.querySelectorAll('tr')).slice(1).map(function(row,i){return {row:row,i:i,value:row.children[column]?(row.children[column].getAttribute('data-sort-value')||row.children[column].textContent||''):''};});
          function unknown(v){return !v||/^(—|No data|Нет данных)$/.test(v.trim());}
          entries.sort(function(a,b){if(unknown(a.value)!==unknown(b.value))return unknown(a.value)?1:-1;var x=a.value.trim(),y=b.value.trim(),nx=Number(x.replace(/%$/,'')),ny=Number(y.replace(/%$/,''));return compareTableValues(a.value,b.value,direction)||a.i-b.i;});
          entries.forEach(function(entry){table.appendChild(entry.row);});
          headers.forEach(function(th,i){th.setAttribute('aria-sort',i===column?(direction==='asc'?'ascending':'descending'):'none');});
          sortStates[tableKey]={column:column,direction:direction};
        }
        headers.forEach(function(th,column){var label=th.textContent;th.setAttribute('scope','col');th.textContent='';th.appendChild(E('button',{'type':'button','class':'hv-sort','aria-label':bi('Sort by ','Сортировать по ')+label,'click':function(){var old=sortStates[tableKey];applySort(column,old&&old.column===column&&old.direction==='asc'?'desc':'asc');}},[label,E('span',{'aria-hidden':'true'},' ↕')]));});
        if(sortStates[tableKey])applySort(sortStates[tableKey].column,sortStates[tableKey].direction);
      });
    }
    function addSearch(key,table){
      var input=E('input',{'type':'search','class':'hv-search','placeholder':bi('Search servers, channels or protocol','Поиск сервера, канала или протокола'),'aria-label':bi('Search table','Поиск в таблице'),'input':function(){searchTerms[key]=input.value;filter();}});input.value=searchTerms[key]||'';
      function filter(){var q=input.value.toLocaleLowerCase(locale);Array.prototype.slice.call(table.querySelectorAll('tr')).slice(1).forEach(function(row){row.hidden=q&&row.textContent.toLocaleLowerCase(locale).indexOf(q)<0;});}
      put(key,input);filter();
    }

    function draw(status){
      if(pointerHeld){deferredStatus=status;updateConnectivityCheck(status);return;}
      var controlFocus=panel.contains(document.activeElement)&&document.activeElement.matches('button,input[type=checkbox],select')?{page:(document.activeElement.closest('[data-hv-page]')||{dataset:{hvPage:activeTab}}).dataset.hvPage,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.textContent,tag:document.activeElement.tagName}:null;
      updateConnectivityCheck(status);
      if(!status.rpc_error)lastGoodStatus=status;
      var focused=panel.contains(document.activeElement)&&document.activeElement.classList.contains('hv-search')?{key:document.activeElement.closest('[data-hv-page]').dataset.hvPage,start:document.activeElement.selectionStart,end:document.activeElement.selectionEnd}:null;
      while(panel.firstChild)panel.removeChild(panel.firstChild);pages={};
      put('overview',E('p',{'class':'alert-message warning'},
        bi('Monitoring is on. The checks run from the router and show whether each VPN works; they cannot prove what a computer on your network sees. That is confirmed separately by the LAN helper before Auto may switch.','Мониторинг включён. Проверки выполняет сам роутер и показывают, работает ли каждый VPN; они не доказывают, что видит компьютер в вашей сети. Это отдельно подтверждает LAN-помощник перед включением Auto.')));
      if(status.rpc_error)put('overview',E('p',{'class':'alert-message warning'},'RPC-UNAVAILABLE: displaying last known measurements. Connectivity and service state are unconfirmed.'));
      if(status.error)put('overview',E('p',{},badge(status.error)));
      var tg=status.telegram||{};if(tg.enabled&&tg.code)put('overview',E('p',{'class':'alert-message warning'},'Telegram: '+tg.code));
      var rows=status.profiles||[];
      var active=rows.filter(function(p){return p.interface;}),healthy=active.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';});
      var currentMonth=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit'}).format(new Date()),month=((status.accounting||{}).months||{})[currentMonth]||null;
      put('overview',E('div',{'class':'hv-metrics'},[
        metric(tr("Подключённые серверы"),active.length+' / '+rows.length,tr("Остальные профили не запускаются")),
        metric(tr("Проверки сейчас"),healthy.length+tr(" из ")+active.length+' OK',tr("HTTPS и DNS с роутера · IPv4")),
        metric(tr("Трафик месяца"),month?bytes(month.rx+month.tx):tr("Нет данных"),tr("Неполный период · с начала наблюдения")),
        metric('Telegram',tg.enabled?(tg.code?tr("Ошибка"):tr("Каждые ")+tg.interval_minutes+tr(" мин")):tr("Отключён"),tg.last_sent?tr("Отправлен ")+new Date(tg.last_sent*1000).toLocaleTimeString():tr("Нет подтверждённой отправки"))
      ]));
      put('channels',vpnSetupCard());put('channels',E('h3',{},bi('Your VPN servers','Ваши VPN-серверы')));
      var cards=E('div',{'class':'hv-server-grid'});
      sortServerCards(rows,selectedProfile(status,Date.now()/1000),Date.now()/1000).forEach(function(p){cards.appendChild(E('article',{'class':'hv-server hv-health-'+profileHealth(p,Date.now()/1000).state,'data-profile':p.id,'data-health':profileHealth(p,Date.now()/1000).state},[
        E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-server-lamp hv-lamp-'+profileHealth(p,Date.now()/1000).state,'role':'img','aria-label':profileHealth(p,Date.now()/1000).label,'title':profileHealth(p,Date.now()/1000).label}),E('span',{'class':'hv-protocol'},p.protocol==='wireguard'?'WireGuard':'OpenVPN'),healthBadge(p),E('span',{'class':'hv-profile-detail'},bi('Tunnel: ','Туннель: ')+(p.interface?bi('Connected','Подключён'):bi('Inactive','Неактивен'))+' · '+bi('Traffic: ','Трафик: ')+(selectedProfile(status,Date.now()/1000)===p.id?bi('Selected','Выбран'):bi('Not confirmed as the active route','Не подтверждён как активный маршрут'))+' · '+bi('Priority: ','Приоритет: ')+(p.priority||100))]),
        E('h4',{},p.name),E('p',{},(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён'))),
        E('div',{'class':'hv-latency'},[E('strong',{},profileHealth(p,Date.now()/1000).state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'),E('span',{},tr(" мс · HTTPS"))]),
        E('small',{},tr("Измерено ")+(p.time?new Date(p.time*1000).toLocaleTimeString():tr("нет данных")))
      ]));});
      if(!rows.length)cards.appendChild(E('div',{'class':'hv-empty'},tr("Подключённые серверы не обнаружены.")));
      put('channels',cards);
      put('statistics',E('section',{'class':'hv-chart-card'},[E('h3',{},tr("Задержка серверов во времени")),chart(status.samples||[],active)]));
      put('statistics',histogram(status.accounting||{},function(value){period=value;draw(status);},period));

      var fp=status.failover_plan||{state:'DISABLED',blockers:[]};
      var states={'DISABLED':bi('The forecast is off (turn it on in Settings → Monitoring)','Прогноз выключен (включите в «Настройки» → «Мониторинг»)'),'PLAN-CONFIG':bi('Choose a primary and a different reserve in Settings → System','Выберите основной и другой, резервный профиль в «Настройки» → «Система»'),'TARGET-INACTIVE':bi('The reserve VPN is not connected. Auto never connects it for you; connect it in the GL.iNet VPN Dashboard','Резервный VPN не подключён. Auto сам его не подключает; подключите в VPN Dashboard GL.iNet'),'TARGET-NOT-READY':bi('Waiting for the reserve to pass its checks','Ожидание, пока резерв пройдёт проверки'),'OBSERVE':bi('Watching the primary; no switch needed','Наблюдение за основным; переключение не нужно'),'SWITCH-RECOMMENDED':bi('The reserve would be chosen now, but nothing is switched from this panel','Сейчас был бы выбран резерв, но из этой панели ничего не переключается')};
      var planning=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Failover forecast (changes nothing)','Прогноз переключения (ничего не меняет)')),E('strong',{},states[fp.state]||fp.state),E('p',{},bi('A switch is considered only after several confirmed failures of the primary and successful checks of the reserve (the numbers are set in Settings → Recovery rules). Missing or old results never trigger a switch. This panel only explains; it changes nothing.','Переключение рассматривается только после нескольких подтверждённых сбоев основного VPN и успешных проверок резерва (числа задаются в «Настройки» → «Правила восстановления»). Отсутствующие или старые результаты переключение не запускают. Эта панель только объясняет и ничего не меняет.'))]);
      if(fp.recommendation)planning.appendChild(E('p',{},bi('Suggested reserve: ','Предлагаемый резерв: ')+(rows.filter(function(p){return p.id===fp.target;})[0]||{}).name));
      planning.appendChild(E('p',{},bi('This is a forecast only. A real switch also needs the passed LAN trial and the router checks listed on the Overview.','Это только прогноз. Для реального переключения нужны пройденный LAN-тест и проверки роутера, перечисленные на странице «Обзор».')));
      planning.appendChild(E('code',{},(fp.blockers||[]).join(' · ')));
      put('tests',planning);


      var ns=status.native_failover||{state:'UNKNOWN'};
      var controlCard=renderAutoControl(status,inventory);put('overview',vpnSetupCard());put('overview',controlCard);put('overview',renderCascadePath(status));put('overview',renderDecisionExplanation(status));put('readiness',renderReadiness(status));pages.overview.insertBefore(controlCard,pages.overview.firstChild);
      var stateNames={'OBSERVING':bi('Automatic monitoring','Автоматический контроль'),'ARMED':bi('Ready','Готов'),'COMMITTED':bi('Reserve confirmed','Резерв подтверждён'),'STOPPED':bi('Stopped','Остановлен'),'DISABLED':bi('Disabled','Выключен'),'EXPIRED':bi('Window ended','Окно завершено'),'WAIT-CLIENT':bi('Waiting for client','Ожидание клиента'),'APPLYING':bi('Switching','Переключение'),'BLOCKED':bi('Blocked','Заблокирован')};
      var stale=!ns.time||Date.now()/1000-ns.time>30;
      if(versionBadge)versionBadge.textContent='v'+(status.version||'unknown');
      if(sideState)sideState.textContent=status.rpc_error?bi('Status RPC unavailable','RPC статуса недоступен'):status.error?bi('Monitor unavailable','Монитор недоступен'):bi('Router monitor online','Монитор роутера доступен');

      var descriptions={
        'HARDWARE-ACCELERATOR-UNVERIFIED':'Hardware acceleration is not proven disabled',
        'SOFTWARE-ACCELERATOR-UNVERIFIED':'Software acceleration is not proven disabled',
        'SOURCE-RESERVE-NOT-CONFIGURED':'Select and save primary and reserve profiles',
        'POLICY-ORDER-DIRECTION-UNVERIFIED':'The LAN helper must verify policy order',
        'HISTORY-001':'Persistent history storage needs repair; switching is blocked',
        'CLIENT-CONFIRMATION-TIMEOUT':'No valid LAN confirmation; rollback required',
        'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':'Another writer changed policy; traffic guard retained'
      };
      var nativePanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Automatic switching · LAN trial','Автопереключение · LAN-тест')),E('strong',{},stateNames[ns.state]||ns.state||'UNKNOWN'),E('p',{},bi('Auto can be started only after a passed LAN trial. The Overview page shows exactly which step is missing. The helper runs on a Windows computer with PowerShell 7 connected to the LAN; it checks the gateway, router DNS, HTTPS and the VPN exit, and asks before it starts. Browser checks alone do not certify the LAN path.','Авторежим можно запустить только после успешного LAN-теста. Страница «Обзор» показывает, какого именно шага не хватает. Помощник запускается на компьютере Windows с PowerShell 7 в локальной сети: он проверяет шлюз, DNS роутера, HTTPS и VPN-выход и спрашивает подтверждение перед началом. Проверка только браузером не подтверждает путь LAN.'))]);
      var reasons=E('ul',{});(ns.blockers||[]).forEach(function(code){reasons.appendChild(E('li',{},code+' · '+autoBlockerText(code)));});nativePanel.appendChild(reasons);
      nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')));
      nativePanel.appendChild(E('button',{'class':'cbi-button cbi-button-negative','type':'button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'native_stop',expect:{}})().then(function(){ui.addNotification(null,E('p',{},bi('Stop requested. Wait until the router confirms it went back to the primary.','Остановка запрошена. Дождитесь, пока роутер подтвердит возврат на основной.')));}).catch(function(){ui.addNotification(null,E('p',{},bi('The stop request failed and the return to the primary is not confirmed. Check the router by another route.','Запрос остановки не прошёл, возврат на основной не подтверждён. Проверьте роутер другим путём.')));});}},bi('Stop and return to the primary','Остановить и вернуться на основной')));
      put('settings',nativePanel);
      var nh=status.native_history||{};
      var historyPanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Controller history','История контроллера')),E('p',{},bi('Controller events, not measurements of LAN uptime. Trial results and automatic commits are counted separately.','События контроллера, а не измерение доступности LAN. Результаты тестов и автоматические переключения считаются отдельно.'))]);
      if(nh.error)historyPanel.appendChild(badge(nh.error));
      if(nh.restored_from_backup)historyPanel.appendChild(E('p',{},'History loaded from the previous valid backup; the latest event may be missing.'));
      var historyTable=E('table',{'class':'table'},[E('tr',{},[E('th',{},'Time · Berlin'),E('th',{},'State'),E('th',{},'Profiles'),E('th',{},'Reason')])]);
      (nh.events||[]).slice().reverse().forEach(function(event){var names=[event.source,event.target].filter(Boolean).map(function(id){return (rows.filter(function(p){return p.id===id;})[0]||{}).name||id;});historyTable.appendChild(E('tr',{},[E('td',{'data-sort-value':event.time},new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})),cell(event.state+(event.trial?' · '+'trial':'')),cell(names.join(' → ')),cell((event.codes||[]).join(' · '))]));});historyPanel.appendChild(historyTable);
      var monthly=E('table',{'class':'table'},[E('tr',{},[E('th',{},'Month'),E('th',{},'Attempts'),E('th',{},'Trials passed'),E('th',{},'Automatic commits'),E('th',{},'Rollbacks'),E('th',{},'Blocked episodes')])]);
      Object.keys(nh.months||{}).sort().reverse().forEach(function(month){var c=nh.months[month];monthly.appendChild(E('tr',{},[cell(month),cell(c.attempts),cell(c.trials_passed),cell(c.committed),cell(c.rollbacks),cell(c.blocked_episodes)]));});historyPanel.appendChild(monthly);put('events',historyPanel);put('events',renderTransitionAnalytics(status));

      var table=E('table',{'class':'table'},[E('tr',{'class':'tr table-titles'},[tr("Сервер"),tr("Канал"),tr("Протокол"),tr("Интерфейс"),tr("Результат"),tr("HTTPS, мс"),tr("Время проверки")].map(function(t){return E('th',{},t);} ))]);
      rows.forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[cell(p.name),cell(p.channel),cell(p.protocol),cell(p.interface),E('td',{},healthBadge(p)),cell(profileHealth(p,Date.now()/1000).state==='healthy'?p.rtt_ms:null),cell(p.time?new Date(p.time*1000).toLocaleTimeString():'—')]));});
      put('channels',E('h3',{},tr("Текущие проверки серверов")));addSearch('channels',table);put('channels',table);
      put('channels',E('p',{},tr("Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.")));
      var samples=status.samples||[],rank={};samples.forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
      Object.keys((status.accounting||{}).quality||{}).forEach(function(id){var q=status.accounting.quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
      var ranked=rows.map(function(p){return {p:p,r:rank[p.id]||{n:0,good:0,sum:0}};}).sort(function(a,b){return (b.r.n?b.r.good/b.r.n:-1)-(a.r.n?a.r.good/a.r.n:-1)||(a.r.good?a.r.sum/a.r.good:Infinity)-(b.r.good?b.r.sum/b.r.good:Infinity);});
      var ranking=E('table',{'class':'table'},[E('tr',{},[tr("Рейтинг измеренных профилей"),tr("Успех проверок"),tr("Средняя HTTPS-задержка")].map(function(t){return E('th',{},t);}))]);
      ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(item.p.name),cell(item.r.n?(100*item.r.good/item.r.n).toFixed(1)+'%':tr("Нет данных")),cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+tr(" мс"):'—')]));});
      addSearch('ranking',ranking);put('ranking',ranking);put('ranking',E('p',{},tr("Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.")));
      var accounting=status.accounting||{},months=accounting.months||{};
      put('traffic',E('h3',{},tr("VPN-трафик по календарным месяцам · Europe/Berlin")));
      var traffic=E('table',{'class':'table'},[E('tr',{},[tr("Месяц"),tr("Входящий"),tr("Исходящий"),tr("Всего"),tr("Наблюдение")].map(function(t){return E('th',{},t);}))]);
      Object.keys(months).sort().reverse().forEach(function(key){var v=months[key];traffic.appendChild(E('tr',{},[cell(key),cell(bytes(v.rx)),cell(bytes(v.tx)),cell(bytes(v.rx+v.tx)),cell((v.seconds/3600).toFixed(1)+tr(" интерфейс-часов")+(v.boundary_estimated?tr(" · граница оценена"):''))]));});
      put('traffic',traffic);put('traffic',E('p',{},tr("Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ")+text(accounting.gaps||0)+tr(". После потери питания возможна потеря последнего интервала checkpoint.")));
      put('services',E('h3',{},tr("Монитор служб")));
      put('services',E('p',{},bi('Times are from the router measurements. A connected interface alone is not proof of internet access.','Время берётся из измерений роутера. Подключённый интерфейс сам по себе не доказывает доступность интернета.')));
      var terminal=E('pre',{},[E('div',{},[E('span',{'class':'hv-log-time'},status.time?new Date(status.time*1000).toLocaleTimeString():'—'),E('strong',{},'  HomenS.AI monitor: '),badge(status.error)]),E('div',{},[E('span',{'class':'hv-log-time'},ns.time?new Date(ns.time*1000).toLocaleTimeString():'—'),E('strong',{},'  Auto VPN: '),stateNames[ns.state]||ns.state||'UNKNOWN'])]);rows.slice(0,20).forEach(function(p){terminal.appendChild(E('div',{'class':p.code?'error':'notice'},[E('span',{'class':'hv-log-time'},p.time?new Date(p.time*1000).toLocaleTimeString():'—:—:—'),E('strong',{},'  '+p.protocol+' / '+p.name+': '),healthBadge(p)]));});put('services',terminal);
      put('events',E('button',{'class':'btn','click':function(){var blob=new Blob([JSON.stringify({mode:'router-monitor',events:status.events||[]},null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),link=E('a',{href:url,download:'homensai-vpn-events.json'});link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}},tr("Скачать журнал")));
      put('ranking',speedPanel(status,inventory,speedPeriod,function(value){speedPeriod=value;draw(status);}));
      put('traffic',trafficHistoryPanel(status.accounting||{}));
      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));
      if(controlFocus&&pages[controlFocus.page]){var options=pages[controlFocus.page].querySelectorAll('button,input[type=checkbox],select');var matching=Array.from(options).find(function(el){return el.tagName===controlFocus.tag&&el.getAttribute('aria-label')===controlFocus.label&&el.textContent===controlFocus.text;});if(matching)matching.focus({preventScroll:true});}
      if(inventory.error)put('overview',E('p',{'class':'alert-message warning','role':'alert'},'RPC-INVENTORY-UNAVAILABLE: configuration is unknown. Reload after RPC recovery; empty defaults are not saved.'));
      sortableTables();showPage(activeTab);if(focused){var input=pages[focused.key]&&pages[focused.key].querySelector('.hv-search');if(input){input.focus();input.setSelectionRange(focused.start,focused.end);}}
    }
    draw(data[1]);
    poll.add(function(){return statusCall().then(draw).catch(function(){draw(Object.assign({},lastGoodStatus,{rpc_error:'RPC-UNAVAILABLE'}));});},10);
    return Promise.resolve(E('p',{},bi('Use the setup wizards below. Settings are validated before saving; stored tokens are never loaded into this page.','Используйте мастера ниже. Настройки проверяются до сохранения; сохранённые токены не загружаются на эту страницу.'))).then(function(formNode){
      var robotHost=E('div',{'class':'robo','aria-label':bi('HomenS.AI author robot','Робот автора HomenS.AI')});
      var footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');
      setTimeout(function(){var robot=window.HomenS.robot.tvRobot(robotHost);robot.play();},0);
      var language=E('select',{'aria-label':bi('Language','Язык')},[E('option',{value:'en',selected:locale==='en'?'':null},'English'),E('option',{value:'ru',selected:locale==='ru'?'':null},'Русский')]);language.value=locale;
      language.addEventListener('change',function(){var chosen=language.value==='ru'?'ru':'en';try{localStorage.setItem('homensai-vpn-language',chosen);}catch(e){}var next=new URL(window.location.href);next.searchParams.set('lang',chosen);window.location.assign(next.toString());});
      versionBadge=E('span',{'class':'hv-version','aria-label':bi('Program version','Версия программы')},'v'+(data[1].version||'unknown'));
      heading=E('h1',{},bi('Your internet under control','Ваш интернет под контролем'));
      sideState=E('p',{'class':'hv-side-state'},data[1].rpc_error?bi('Status RPC unavailable','RPC статуса недоступен'):data[1].error?bi('Monitor unavailable','Монитор недоступен'):bi('Router monitor online','Монитор роутера доступен'));
      settingsHost=E('section',{'class':'hv-settings','data-hv-page':'settings'},[E('h3',{},bi('Monitoring, Telegram and profile names','Мониторинг, Telegram и названия профилей')),E('a',{'href':L.url('admin/services/homensai-vpn')+'?setup=telegram&lang='+locale+'#settings'},bi('Telegram setup wizard','Мастер настройки Telegram')),setup?E('p',{},bi('Create a bot with BotFather, send /start, then enter its token and your Chat ID. The token stays on the router and is never returned in status.','Создайте бота через BotFather, отправьте /start, затем введите токен и свой Chat ID. Токен хранится на роутере и не возвращается в статусе.')):null,formNode].filter(function(node){return node!=null;}));
      var links=tabs.map(function(tab){return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);});
      appRoot=E('div',{'class':'hv-app hv-workspace'},[
        E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/charts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui23.css')+'?build=080-alpha4'}),
        E('aside',{'class':'hv-sidebar'},[E('a',{'class':'hv-side-brand','href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer','aria-label':bi('HomenS.AI website','Сайт HomenS.AI')},[robotHost,E('span',{},[E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI')]),E('small',{},'Auto VPN')])]),E('p',{'class':'hv-model'},'GL.iNet GL-MT6000 · Flint 2'),E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')},links),E('div',{'class':'hv-side-footer'},[sideState,E('small',{},bi('Real IPv4 router measurements','Реальные IPv4-измерения роутера')),E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),E('small',{},'HomenS.AI Style 1.14.3')])]),
        E('main',{'class':'hv-main'},[E('header',{'class':'hv-page-header'},[E('div',{},[E('div',{'class':'hv-eyebrow'},bi('AVAILABILITY CONTROL','УПРАВЛЕНИЕ ДОСТУПНОСТЬЮ')),heading,E('p',{},bi('Your VPNs, how healthy they are, and what the router did about it.','Ваши VPN, насколько они исправны и что сделал роутер.'))]),E('div',{'class':'hv-page-actions'},[versionBadge,language,renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})])]),panel,settingsHost,footer])
      ]);
      settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-card-monitor'},[E('h3',{},bi('Monitor service','Служба мониторинга')),E('p',{},bi('Turns the background checks on or off. Stop Auto and wait for it to hand control back before turning the checks off. The real state is confirmed by fresh results.','Включает или выключает фоновые проверки. Перед выключением остановите Auto и дождитесь, пока он вернёт управление. Реальное состояние подтверждают свежие результаты.')),E('button',{'type':'button','class':'cbi-button','click':function(ev){ev.target.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'monitor_control',params:['enabled'],expect:{}})(!(inventory.settings||{}).enabled).then(function(result){ui.addNotification(null,E('p',{},result.code||'MONITOR-UNKNOWN'));if(result.accepted)window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){ev.target.disabled=false;});}},(inventory.settings||{}).enabled?bi('Stop monitor','Остановить мониторинг'):bi('Start monitor','Запустить мониторинг'))]));
      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){recoveryWizard(inventory);}},bi('Recovery setup wizard','Мастер восстановления')));
      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){monitorPreferences(inventory);}},bi('Monitoring preferences','Параметры мониторинга')));
      settingsHost.appendChild(speedSettings(inventory));
      settingsHost.insertBefore(E('div',{'class':'hv-wizard-launch'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){setupWizard(inventory,'system');}},bi('System setup wizard','Мастер настройки системы')),E('button',{'type':'button','class':'cbi-button','click':function(){setupWizard(inventory,'telegram');}},bi('Telegram channel wizard','Мастер Telegram-канала')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'TELEGRAM-TEST-UNKNOWN'));});}},bi('Test Telegram delivery','Проверить доставку Telegram'))]),settingsHost.firstChild);
      (function(){
        var monitorCard=settingsHost.querySelector('.hv-card-monitor'),speedCard=settingsHost.querySelector('.hv-speed-settings');
        while(settingsHost.firstChild)settingsHost.removeChild(settingsHost.firstChild);
        function launcher(label,hint,action,primary){return E('div',{'class':'hv-setup-item'},[E('button',{'type':'button','class':'cbi-button'+(primary?' cbi-button-action':''),'click':action},label),E('p',{},hint)]);}
        var testDelivery=function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'TELEGRAM-TEST-UNKNOWN'));});};
        settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-setup-card'},[
          E('h3',{},bi('Setup','Настройка')),
          E('p',{},bi('Every wizard validates your input and shows a review before saving. Stored tokens are never shown again.','Каждый мастер проверяет ввод и показывает обзор перед сохранением. Сохранённые токены больше не показываются.')),
          setup?E('p',{},bi('Create a bot with BotFather, send /start, then enter its token and your Chat ID. The token stays on the router and is never returned in status.','Создайте бота через BotFather, отправьте /start, затем введите токен и свой Chat ID. Токен хранится на роутере и не возвращается в статусе.')):null,
          E('div',{'class':'hv-setup-grid'},[
            launcher(bi('1 · System','1 · Система'),bi('Primary and reserve profiles, names, channels, priorities and accepted reconnection.','Основной и резервный профили, названия, каналы, приоритеты и допустимость переподключения.'),function(){setupWizard(inventory,'system');},true),
            launcher(bi('2 · Recovery rules','2 · Правила восстановления'),bi('Failures before switching, reserve checks, cooldown and return policy.','Сколько сбоев до переключения, проверки резерва, пауза и политика возврата.'),function(){recoveryWizard(inventory);}),
            launcher(bi('3 · Monitoring','3 · Мониторинг'),bi('Check interval, profile limit and statistics saving.','Интервал проверок, лимит профилей и сохранение статистики.'),function(){monitorPreferences(inventory);}),
            launcher(bi('4 · Telegram','4 · Telegram'),bi('Bot token and destination for reports.','Токен бота и адресат отчётов.'),function(){setupWizard(inventory,'telegram');}),
            launcher(bi('Test Telegram delivery','Проверить доставку Telegram'),bi('Sends one test message with the saved settings.','Отправляет одно тестовое сообщение с сохранёнными настройками.'),testDelivery)
          ])].filter(function(node){return node!=null;})));
        if(monitorCard)settingsHost.appendChild(monitorCard);
        if(speedCard)settingsHost.appendChild(speedCard);
      })();
      panel.addEventListener('pointerdown',function(){pointerHeld=true;});
      ['pointerup','pointercancel'].forEach(function(event){window.addEventListener(event,function(){if(!pointerHeld)return;setTimeout(function(){pointerHeld=false;if(deferredStatus){var next=deferredStatus;deferredStatus=null;draw(next);}},0);});});
      showPage(activeTab);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});
      initSidebarLayout(appRoot);
      return appRoot;
    });
  }
});