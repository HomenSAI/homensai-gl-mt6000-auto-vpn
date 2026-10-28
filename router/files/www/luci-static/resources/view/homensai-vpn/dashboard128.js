// HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
'use strict';
'require view';

'require rpc';
'require poll';
'require ui';
'require baseclass';
'require request';
/* Module-local E: LuCI renders null array children as text. Keep attributes intact. */
function hvElementChildren(value){
  if(value===null||value===undefined)return [];
  if(!Array.isArray(value))return value;
  var result=[];
  value.forEach(function(child){
    if(child===null||child===undefined)return;
    if(Array.isArray(child)){var nested=hvElementChildren(child);Array.prototype.push.apply(result,nested);}
    else result.push(child);
  });return result;
}
var E=(function(nativeElement){
  nativeElement=nativeElement&&nativeElement.__homensaiRawElement||nativeElement;
  if(typeof nativeElement!=='function')throw new Error('DOM element factory unavailable');
  function element(){
    var args=Array.prototype.slice.call(arguments);
    if(Array.isArray(args[0]))args[0]=hvElementChildren(args[0]);
    if(args.length>2)args[2]=hvElementChildren(args[2]);
    else if(args.length===2&&Array.isArray(args[1]))args[1]=hvElementChildren(args[1]);
    return nativeElement.apply(null,args);
  }
  Object.defineProperty(element,'__homensaiRawElement',{value:nativeElement});return element;
})(typeof L!=='undefined'&&L.dom&&typeof L.dom.create==='function'?L.dom.create.bind(L.dom):typeof globalThis!=='undefined'?globalThis.E:window.E);


var savedLanguage='en';
try { savedLanguage=localStorage.getItem('homensai-vpn-language')||'en'; } catch(e) {}
var requestedLanguage=new URLSearchParams(window.location.search).get('lang');
var locale=(requestedLanguage||savedLanguage)==='ru'?'ru':'en';
var translations = {"Туннель не подключён": "Tunnel disconnected", "HTTPS через VPN не проходит": "HTTPS through VPN failed", "DNS не отвечает": "DNS unavailable", "Маршрут не соответствует VPN": "Route does not match VPN", "Путь проверки не подтверждён": "Probe path unverified", "Ошибка службы или зависимости": "Service or dependency error", "Ошибка сохранения статистики": "Statistics storage error", "Статистика восстановлена из резервной копии": "Statistics restored from backup", "Время роутера ещё не установлено": "Router clock is not set", "Профиль сейчас не подключён": "This VPN is not connected", "Профиль вне лимита текущего раунда": "Skipped this round (check limit reached)", "Служба остановлена": "Service unavailable", "График появится после двух успешных измерений. Искусственных данных здесь нет.": "The chart appears after two successful checks. Nothing is made up.", "История HTTPS-задержки подключённых серверов в миллисекундах": "Response time of connected servers, milliseconds", "HTTPS, мс · последние доступные измерения за час. Разрывы длиннее 90 секунд не соединяются.": "Response time of each connected VPN over the last hour, in milliseconds. The line breaks where there was no data for 90 seconds.", "Нативный монитор alpha: реальные IPv4 HTTPS/DNS-проверки на роутере. Контролируемое переключение требует клиентской проверки.": "Experimental monitor. It checks every connected VPN from the router over IPv4 (HTTPS and DNS). Automatic switching needs the LAN helper to confirm.", "Служба наблюдения": "Monitoring service", "Включить наблюдение": "Enable monitoring", "Интервал, секунд": "How often to check each VPN, seconds", "Лимит подключённых профилей за раунд": "Most VPNs checked per round", "Сохранение статистики во flash, секунд": "Save statistics every, seconds", "Отправлять отчёты в Telegram": "Send Telegram reports", "Интервал Telegram-отчётов, минут": "Telegram report interval, minutes", "Токен бота · настройка Telegram": "Bot token · Telegram setup", "Проверьте формат токена BotFather": "Check the BotFather token format", "Оставьте пустым, чтобы сохранить действующий токен.": "Leave empty to keep the current token.", "Токен сохранится на роутере; в отчёты и статус не включается.": "The token stays on the router and is excluded from reports and status.", "Каналы и существующие профили": "Channels and existing profiles", "Ваше название": "Display name", "Профиль роутера": "VPN profile on the router", "Ваш канал": "Channel name", "Приоритет": "Priority", "Наблюдать": "Monitor", "Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.": "Monitoring is active. Native controller state is shown below. Router probes do not certify the LAN client path; a trial requires separate client confirmation.", "включён · интервал ": "enabled · interval ", " мин · последняя отправка ": " min · last sent ", "ожидается": "pending", "отключён": "disabled", "Подключённые серверы": "Connected servers", "Остальные профили не запускаются": "Other VPNs are switched off", "Проверки сейчас": "Checks now", " из ": " of ", "HTTPS и DNS с роутера · IPv4": "HTTPS and DNS from the router, IPv4", "Трафик месяца": "Monthly traffic", "Нет данных": "No data", "Неполный период · с начала наблюдения": "Partial period · since monitoring started", "Ошибка": "Error", "Каждые ": "Every ", " мин": " min", "Отключён": "Disabled", "Отправлен ": "Sent ", "Нет подтверждённой отправки": "No confirmed delivery", "Подключённые VPN-серверы": "Connected VPN servers", " мс · HTTPS": " ms · HTTPS", "Измерено ": "Measured ", "нет данных": "no data", "Подключённые серверы не обнаружены.": "No connected servers detected.", "Задержка серверов во времени": "Server latency over time", "Сервер": "Server", "Канал": "Channel", "Протокол": "Protocol", "Интерфейс": "Interface", "Результат": "Result", "HTTPS, мс": "HTTPS, ms", "Время проверки": "Checked at", "Текущие проверки серверов": "Current check per server", "Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.": "VPNs that are not connected are listed but never started by this program. To test one, connect it yourself in the GL.iNet VPN Dashboard.", "Рейтинг измеренных профилей": "Ranking of measured servers", "Успех проверок": "Checks passed", "Средняя HTTPS-задержка": "Average HTTPS latency", " мс": " ms", "Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.": "The ranking uses hourly averages from up to seven days of checks. It is not a speed test and changes no priorities by itself.", "VPN-трафик по календарным месяцам · Europe/Berlin": "VPN traffic by calendar month · Europe/Berlin", "Месяц": "Month", "Входящий": "Received", "Исходящий": "Sent", "Всего": "Total", "Наблюдение": "Observation", " интерфейс-часов": " interface-hours", " · граница оценена": " · estimated month boundary", "Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ": "Unique VPN interfaces are counted once, including protocol overhead. Observation gaps: ", ". После потери питания возможна потеря последнего интервала checkpoint.": ". A power loss may lose the latest checkpoint interval.", "Монитор служб": "Service monitor", "Скачать журнал": "Export events", "Серверы, качество связи и трафик — реальные измерения на роутере": "Servers, connection quality and traffic — real router measurements", "Запрошен раунд проверок подключённых профилей.": "A probe round for connected profiles was requested.", "Проверить сейчас": "Probe now", "Настроить Telegram": "Set up Telegram", "Мастер подключения Telegram": "Telegram setup wizard", "Настройки мониторинга, Telegram и названия серверов": "Monitoring settings, Telegram and server names", "Подключение Telegram": "Connect Telegram", "Создайте бота через @BotFather и скопируйте токен.": "Create a bot with @BotFather and copy its token.", "Отправьте боту /start. Введите свой Chat ID и токен ниже.": "Send /start to your bot. Enter your own chat ID and bot token below.", "Включите отправку, выберите интервал и нажмите Save & Apply. Роутер отправит первый отчёт; результат появится в статусе Telegram сверху.": "Enable reports, select an interval and click Save & Apply. The router sends its first report; delivery status appears above.", "Токен — секрет. После сохранения он не показывается; повторная настройка открывается отдельной кнопкой.": "The token is secret. It is not displayed after saving. Use the separate setup button to replace it."};
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
    legend.appendChild(E('span',{},[E('i',{'class':'hv-series-'+(i%colors.length)}),serverTitle(p)]));
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
  if(!profiles.length)section.appendChild(E('p',{},bi('History starts when monitoring started; nothing is guessed for earlier time.','История начинается с запуска мониторинга; за более раннее время ничего не придумывается.')));
  ['openvpn','wireguard'].forEach(function(protocol){
    section.appendChild(E('h4',{},protocol==='openvpn'?'OpenVPN':'WireGuard'));
    var group=E('div',{'class':'hv-histograms'});
    profiles.filter(function(r){return r.p.protocol===protocol;}).sort(function(a,b){return b.t.up-a.t.up;}).forEach(function(r){
      var total=r.t.up+r.t.down+r.t.unknown,bar=document.createElementNS('http://www.w3.org/2000/svg','svg'),offset=160;bar.setAttribute('class','hv-stack');bar.setAttribute('viewBox','0 0 68 160');
      [['up','var(--ok)'],['down','var(--bad)'],['unknown','var(--muted)']].forEach(function(entry){var value=r.t[entry[0]],percent=total?100*value/total:0;if(value){var ns='http://www.w3.org/2000/svg',rect=document.createElementNS(ns,'rect'),title=document.createElementNS(ns,'title');var height=percent*1.6;offset-=height;rect.setAttribute('x','0');rect.setAttribute('y',offset);rect.setAttribute('width','68');rect.setAttribute('height',height);rect.setAttribute('fill',entry[1]);title.textContent=entry[0]+': '+(value/3600).toFixed(2)+' h · '+percent.toFixed(1)+'%';rect.appendChild(title);bar.appendChild(rect);if(percent>=12){var label=document.createElementNS(ns,'text');label.setAttribute('x','34');label.setAttribute('y',offset+height/2+4);label.setAttribute('text-anchor','middle');label.setAttribute('class','hv-stack-label');label.textContent=percent.toFixed(0)+'%';bar.appendChild(label);}}});
      group.appendChild(E('div',{'class':'hv-histogram'},[E('strong',{},(r.t.up/3600).toFixed(2)+' h'),bar,E('b',{},serverTitle(r.p)),E('small',{},bi('Connections: ','Подключений: ')+r.t.connections+' · '+bi('Failures: ','Сбоев: ')+r.t.failures),!total?E('small',{},bi('No active observation','Нет активных измерений')):null]));
    });section.appendChild(group);
  });
  section.appendChild(E('p',{},bi('Green: time it worked. Red: time it failed. Grey: not observed. Connections: how many times the VPN came up.','Зелёный: время работы. Красный: время сбоя. Серый: не наблюдалось. Подключения: сколько раз VPN поднимался.')));
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

/* Fool-proofing helpers shared by every page and wizard (owner decision 18 Oct 2026, "clueless grandfather" user).
   1. ONE table of allowed number ranges (FOOL_RANGES). The backend bounds are authoritative; qa tests compare this table with them.
   2. Number fields: the allowed range is printed under the field, a wrong value turns the field red with a plain message and
      the Save/Next button stays disabled until it is fixed. The typed value is never changed silently.
   3. guardedAction(button,fn,opts): a button that sends an RPC is disabled while it works ("Working…"), then stays disabled
      for 10 seconds with a visible countdown ("Wait 7 s"). Extra clicks are ignored (no second RPC).
   4. confirmAction(): "Are you sure?" dialog (ui.showModal, never window.confirm) that gates the RPC. */
var FOOL_PAUSE_SECONDS=10;
// key -> [min, max, unit EN, unit RU, label EN, label RU]; unit is '' for plain counts.
var FOOL_RANGES={
  'system.interval':[10,300,'seconds','секунд'],
  'system.duration':[1,240,'minutes','минут'],
  'system.priority':[1,1000,'','' ],
  'telegram.interval':[5,10080,'minutes','минут'],
  'telegram.hour':[0,23,'','' ],
  'monitor.interval':[10,300,'seconds','секунд'],
  'monitor.checkpoint':[300,3600,'seconds','секунд'],
  'monitor.live_log_limit':[1,2000,'observations','наблюдений'],
  'monitor.history_days':[1,7,'days','дней'],
  'monitor.probe_limit':[1,16,'','' ],
  'speed.budget_mib':[1,32,'MiB','МиБ'],
  'speed.duration':[2,15,'seconds','секунд'],
  'speed.streams':[1,4,'','' ],
  'speed.daily_mib':[1,1024,'MiB','МиБ'],
  'speed.busy_mbps':[1,1000,'Mbps','Мбит/с'],
  // mirrors recovery_settings.py RANGES
  'recovery.failures':[3,10,'','' ],
  'recovery.successes':[2,10,'','' ],
  'recovery.cooldown':[60,1800,'seconds','секунд'],
  'recovery.min_dwell':[60,3600,'seconds','секунд'],
  'recovery.primary_successes':[2,10,'','' ],
  'recovery.primary_stable':[30,600,'seconds','секунд'],
  'recovery.attempt_limit':[1,10,'attempts','попыток'],
  'recovery.attempt_window':[1,15,'minutes','минут'],
  'recovery.interval':[10,300,'seconds','секунд']
};
// Text limits that match the backend (names and channel groups 1-64 characters; chat id; bot token).
var FOOL_TEXT={name:[1,64],channel:[1,64],chat:[1,33],token:[0,120]};
function foolRangeText(key){
  var r=FOOL_RANGES[key];
  return bi('from '+r[0]+' to '+r[1]+(r[2]?' '+r[2]:''),'от '+r[0]+' до '+r[1]+(r[3]?' '+r[3]:''));
}
// Check one raw value of a number field. Returns {ok, value, message}; message is plain words (bilingual), never a code.
function foolCheckNumber(key,raw){
  var r=FOOL_RANGES[key],text=String(raw==null?'':raw),range=foolRangeText(key);
  if(text==='')return {ok:false,message:bi('This field is empty. Type a whole number '+range+'.','Поле пустое. Введите целое число '+range+'.')};
  if(!/^-?[0-9]+$/.test(text))return {ok:false,message:bi('“'+text.slice(0,20)+'” is not a whole number. Use digits only, no letters, spaces, commas or decimals. Allowed: '+range+'.','«'+text.slice(0,20)+'» — не целое число. Только цифры, без букв, пробелов, запятых и дробей. Допустимо: '+range+'.')};
  var n=Number(text);
  if(n<r[0])return {ok:false,message:bi('This number is too small. Allowed: '+range+'.','Число слишком маленькое. Допустимо: '+range+'.')};
  if(n>r[1])return {ok:false,message:bi('This number is too big. Allowed: '+range+'.','Число слишком большое. Допустимо: '+range+'.')};
  return {ok:true,value:n,message:''};
}
// Text field check (names, channel). Returns {ok,message}.
function foolCheckText(kind,raw){
  var lim=FOOL_TEXT[kind],rawText=String(raw==null?'':raw),text=rawText.trim();
  if(/[\x00-\x1f\x7f]/.test(rawText))return {ok:false,message:bi('Line breaks and control characters are not allowed.','Переносы строк и управляющие символы не допускаются.')};
  if(text.length<lim[0])return {ok:false,message:bi('This field cannot be empty. Type '+lim[0]+' to '+lim[1]+' characters.','Поле не может быть пустым. Введите от '+lim[0]+' до '+lim[1]+' символов.')};
  if(text.length>lim[1])return {ok:false,message:bi('Too long. At most '+lim[1]+' characters.','Слишком длинно. Не больше '+lim[1]+' символов.')};
  if(kind==='chat'&&!/^(?:-?[0-9]{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$/.test(rawText))return {ok:false,message:bi('Enter a numeric chat ID or a channel name such as @channel_name.','Введите числовой ID чата или имя канала, например @channel_name.')};
  if(kind==='token'&&text!==''&&!/^[0-9]{6,15}:[A-Za-z0-9_-]{30,100}$/.test(rawText))return {ok:false,message:bi('Use the complete bot token from BotFather, without spaces.','Введите полный токен бота из BotFather, без пробелов.')};
  return {ok:true,message:''};
}
function foolSetText(node,text){node.textContent=text;}
/* Wrap a number input: sets min/max/step, prints the range under it, validates on every input.
   Returns {row, check}: row = <label> to append; check() re-validates, updates the red message, returns true/false.
   onChange() is called after each input so the caller can enable/disable its Save/Next button. */
function foolNumberRow(title,node,key,onChange){
  var r=FOOL_RANGES[key];
  node.setAttribute('min',String(r[0]));node.setAttribute('max',String(r[1]));node.setAttribute('step','1');node.setAttribute('inputmode','numeric');
  node.setAttribute('aria-label',title);
  var hint=E('small',{'class':'hv-fool-hint'},bi('Allowed: ','Допустимо: ')+foolRangeText(key)+'.');
  var error=E('small',{'class':'hv-fool-error','role':'alert','aria-live':'polite'},'');
  function check(){
    var res=foolCheckNumber(key,node.value);
    foolSetText(error,res.message);
    node.setAttribute('aria-invalid',res.ok?'false':'true');
    if(node.classList){if(res.ok)node.classList.remove('hv-fool-invalid');else node.classList.add('hv-fool-invalid');}
    node.fool_ok=res.ok;
    return res.ok;
  }
  function handler(){check();if(onChange)onChange();}
  if(typeof node.addEventListener==='function'){node.addEventListener('input',handler);node.addEventListener('change',handler);}
  var row=E('label',{'class':'hv-wizard-field hv-fool-field'},[E('span',{},title),node,hint,error]);
  check();
  return {row:row,check:check,node:node,error:error};
}
// The same for a text input (name, channel).
function foolTextRow(title,node,kind,onChange,required){
  var lim=FOOL_TEXT[kind];
  node.setAttribute('maxlength',String(lim[1]));node.setAttribute('aria-label',title);
  var hint=E('small',{'class':'hv-fool-hint'},bi(lim[0]+' to '+lim[1]+' characters.','от '+lim[0]+' до '+lim[1]+' символов.'));
  var error=E('small',{'class':'hv-fool-error','role':'alert','aria-live':'polite'},'');
  function check(){
    var res=foolCheckText(kind,node.value);
    if(required&&String(node.value||'').trim()==='')res={ok:false,message:bi('Paste the bot token from BotFather. No stored token is available.','Вставьте токен бота из BotFather. Сохранённого токена нет.')};
    foolSetText(error,res.message);node.setAttribute('aria-invalid',res.ok?'false':'true');
    if(node.classList){if(res.ok)node.classList.remove('hv-fool-invalid');else node.classList.add('hv-fool-invalid');}
    return res.ok;
  }
  function handler(){check();if(onChange)onChange();}
  if(typeof node.addEventListener==='function'){node.addEventListener('input',handler);node.addEventListener('change',handler);}
  var row=E('label',{'class':'hv-wizard-field hv-fool-field'},[E('span',{},title),node,hint,error]);
  check();
  return {row:row,check:check,node:node,error:error};
}
// Disable or enable a Save/Next button from a list of checks (every check also paints its own red message).
function foolGate(button,checks){
  var ok=true;checks.forEach(function(check){if(!check())ok=false;});
  if(button){button.fool_checks=checks;button.disabled=!ok||!!button.fool_lock;if(button.setAttribute)button.setAttribute('aria-disabled',button.disabled?'true':'false');}
  return ok;
}

/* ---- guardedAction ---- */
var FOOL_LOCKS=Object.create(null);
function foolLabelTarget(button,opts){return opts&&opts.status?opts.status:button;}
function foolShow(button,opts,text){
  var target=foolLabelTarget(button,opts);
  if(!button.fool_saved){
    button.fool_saved={snapshot:target.childNodes?Array.prototype.slice.call(target.childNodes):null,text:target.textContent,title:button.getAttribute?button.getAttribute('title'):null,aria:button.getAttribute?button.getAttribute('aria-label'):null};
  }
  target.textContent=text;
  if(opts&&opts.status){button.setAttribute('title',text);}
}
function foolRestore(button,opts){
  var saved=button.fool_saved,target=foolLabelTarget(button,opts);
  if(!saved)return;
  if(saved.snapshot&&saved.snapshot.length&&typeof target.appendChild==='function'){target.textContent='';saved.snapshot.forEach(function(n){target.appendChild(n);});}
  else target.textContent=saved.text==null?'':saved.text;
  if(opts&&opts.status){if(saved.title==null){if(button.removeAttribute)button.removeAttribute('title');}else button.setAttribute('title',saved.title);}
  button.fool_saved=null;
}
function foolPause(button,lock,opts){
  lock.left=FOOL_PAUSE_SECONDS;
  button.disabled=true;
  function tick(){
    if(lock.left>0){
      lock.display=lock.left;
      lock.watchers.forEach(function(w){foolShow(w.button,w.opts,bi('Wait '+lock.left+' s','Подождите '+lock.left+' с'));});
      lock.left--;
      lock.timer=setTimeout(tick,1000);
      return;
    }
    lock.timer=null;lock.phase='idle';
    if(lock.key)delete FOOL_LOCKS[lock.key];
    lock.watchers.forEach(function(w){
      w.button.fool_lock=null;foolRestore(w.button,w.opts);
      if(w.button.fool_checks)foolGate(w.button,w.button.fool_checks);else w.button.disabled=w.disabled;
    });
    lock.watchers=[];
  }
  lock.phase='pause';tick();
}
/* guardedAction(button, fn, opts): fn() must return a promise (the RPC). opts: key (shared lock for re-created buttons),
   status (node that shows the text instead of the button, for icon-only buttons), failCode (shown as a link on rejection). */
function guardedAction(button,fn,opts){
  opts=opts||{};
  var key=opts.key||null,existing=key?FOOL_LOCKS[key]:button.fool_lock;
  if(existing){guardResume(button,key,opts);return Promise.resolve(undefined);}
  var lock={key:key,phase:'work',left:0,timer:null,watchers:[]};
  if(key)FOOL_LOCKS[key]=lock;
  foolWatch(button,lock,opts);
  var promise;
  try{promise=Promise.resolve(fn());}catch(error){promise=Promise.reject(error);}
  function finish(){foolPause(button,lock,opts);}
  return promise.then(function(value){finish();return value;},function(error){
    var code=error&&safeCode(error.code)?error.code:(opts.failCode||'UI-ACTION-FAILED');
    ui.addNotification(null,E('p',{},[errorCodeLink(code),' · ',bi('The request did not finish. Wait a moment and try again.','Запрос не завершился. Подождите немного и повторите.')]));
    finish();
  });
}
/* A button that was re-created while its lock is still running (the page redraws after each refresh) continues the pause. */
function guardResume(button,key,opts){
  var lock=key?FOOL_LOCKS[key]:button.fool_lock;
  if(!lock)return button;
  foolWatch(button,lock,opts||{});
  return button;
}
function foolWatch(button,lock,opts){
  if(!lock.watchers.some(function(w){return w.button===button;}))lock.watchers.push({button:button,opts:opts,disabled:!!button.disabled});
  button.disabled=true;button.fool_lock=lock;
  foolShow(button,opts,lock.phase==='pause'?bi('Wait '+lock.display+' s','Подождите '+lock.display+' с'):bi('Working…','Выполняется…'));
}
/* Confirm dialog. Cancel closes it and nothing is sent; Confirm closes it and then calls onConfirm(). */
function confirmAction(title,paragraphs,confirmLabel,onConfirm,danger,onCancel){
  var confirmed=false;
  var body=(paragraphs||[]).map(function(text){return E('p',{},text);});
  body.unshift(E('p',{'class':'hv-fool-ask'},bi('Are you sure?','Вы уверены?')));
  var buttons=E('div',{'class':'hv-wizard-actions'},[
    E('button',{'type':'button','class':'cbi-button hv-confirm-cancel','click':function(){if(confirmed)return;confirmed=true;ui.hideModal();if(onCancel)return onCancel();}},bi('Cancel','Отмена')),
    E('button',{'type':'button','class':'cbi-button '+(danger?'cbi-button-negative hv-danger-action':'cbi-button-action hv-primary-action')+' hv-confirm-ok','click':function(){if(confirmed)return;confirmed=true;ui.hideModal();return onConfirm();}},confirmLabel)]);
  ui.showModal(title,body.concat([buttons]));
}

/* Explicit one-shot manual intent. Queue acknowledgements never select a route or enable Auto. */
var MANUAL_SWITCH_PENDING=false,MANUAL_SWITCH_DIRECTION=null;
function manualFresh(time,now,limit){return Number.isFinite(time)&&now-time>=-5&&now-time<=limit;}
function manualConfirmedPath(status,source,target,now){
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
  if(proof.authoritative){
    if(proof.moving)return {source:'checking',target:'checking',direction:'forward',moving:true,selected:null};
    if(!proof.selected)return Object.assign({},neutral,{code:proof.code});
    var selected=source&&proof.selected===source.id?'source':target&&proof.selected===target.id?'target':null;
    return {source:selected?'ready':'neutral',target:selected?'ready':'neutral',direction:selected==='target'?'forward':'none',moving:false,selected:selected,code:proof.code};
  }
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90))return neutral;
  // Legacy native confirmation remains usable only with fresh monitor/controller evidence.
  var ns=status.native_failover||{};
  if(!source||!target||ns.source&&ns.source!==source.id||ns.target&&ns.target!==target.id)return neutral;
  var path=autoPathModel(status,source,target,now),model=autoControlModel(status,now);
  if(model.fresh&&model.off&&ns.original_restored===true&&source&&target&&source.id!==target.id)path.selected='source';
  if(model.fresh&&ns.state==='STOPPED-ON-RESERVE'&&source&&target&&source.id!==target.id&&ns.original_restored===false)path.selected='target';
  return path;
}
function manualChannelTone(profile,key,path,now,autoRuns){
  var health=profile?profileHealth(profile,now).state:'unknown',selected=path.selected===key;
  var waitText=key==='target'||key==='reserve'?bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную'):bi('Primary channel: Alive; you can switch to it manually','Основной канал: Живой, можно переключиться на него вручную');
  if(!profile)return {color:'grey',text:bi('Not chosen','Не выбран'),carrier:false};
  if(path.moving)return {color:'grey',text:bi('Switching · waiting for the router','Переключение · ждём роутер'),carrier:false};
  // Owner colour rule: green works in Auto, yellow alive and available for manual switching, grey waiting for the router, red error.
  if(!path.selected&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Not working','Не работает'):bi('Not connected','Не подключён'),carrier:false};
  if(path.code&&!path.selected)return {color:'grey',text:bi('Traffic selection is not verified','Выбор канала трафика не подтверждён')+' · '+path.code,carrier:false};
  if(health==='healthy'&&autoRuns===false)return {color:'yellow',text:waitText,carrier:selected};
  if(!path.selected||health==='unknown'||health==='checking')return {color:'grey',text:bi('Waiting for the router\'s answer','Ждём ответа роутера'),carrier:false};
  if(selected&&health==='healthy')return {color:'green',text:bi('Works in Auto · carries your traffic','Работает в автомате · несёт трафик'),carrier:true};
  if(selected)return {color:'red',text:health==='failed'?bi('In use · connectivity failed','Используется · ошибка доступности'):bi('Selected tunnel is not connected','Выбранный туннель не подключён'),carrier:true};
  if(health==='healthy')return {color:'yellow',text:waitText,carrier:false};
  return {color:'red',text:health==='failed'?bi('Not in use · connectivity failed','Не используется · ошибка доступности'):health==='inactive'?bi('Not in use · not connected','Не используется · не подключён'):bi('Not in use · available','Не используется · доступен'),carrier:false};
}
function manualControlModel(status,now){
  var control=status.manual_switch_control||{},request=status.manual_switch||{},revision=control.control_revision;
  var fresh=!status.rpc_error&&!status.error&&manualFresh(status.time,now,90)&&manualFresh(control.time,now,30);
  var busy=MANUAL_SWITCH_PENDING||(manualFresh(request.updated_at,now,90)&&['QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'].indexOf(request.state)>=0);
  function direction(key){var row=control[key]||{},codes=Array.isArray(row.blockers)?row.blockers:Array.isArray(control.blockers)?control.blockers:[];
    return {allowed:fresh&&!busy&&control.available===true&&row.allowed===true&&typeof revision==='string'&&/^[a-f0-9]{32}$/.test(revision),blockers:codes.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);})};}
  return {fresh:fresh,busy:busy,revision:revision,mode:control.mode||'legacy',hold:control.hold||null,reserve:direction('reserve'),primary:direction('primary'),resume:direction('resume')};
}
function manualReason(codes){
  if(!codes.length)return bi('Manual switching is unavailable until the router confirms that it is ready.','Ручное переключение недоступно, пока роутер не подтвердит готовность.');
  return codes.map(function(code){
    var pairNotes={
      'PAIR-MANUAL-COOLDOWN':['Wait for the minimum dwell/cooldown interval before another forward switch.','Дождитесь окончания минимального интервала между переключениями.'],
      'PAIR-RATE-LIMIT':['The configured number of forward attempts has been used for the selected period. Wait; Stop and return remain available.','Достигнут заданный лимит попыток за выбранный период. Подождите; Stop и возврат остаются доступны.'],
      'PAIR-MANUAL-TARGET-UNHEALTHY':['The reserve has no fresh successful DNS/HTTPS confirmation. It will not be selected.','У резерва нет свежего успешного подтверждения DNS/HTTPS. Он не будет выбран.'],
      'PAIR-MANUAL-BUSY':['A transition or request is already in progress. The Auto power button remains available to stop or cancel startup.','Переключение или запрос уже выполняется. Кнопка Auto остаётся доступной для остановки.']};
    if(Object.prototype.hasOwnProperty.call(pairNotes,code))return bi(pairNotes[code][0],pairNotes[code][1]);
    var row=typeof ERROR_EXTRA_ROWS!=='undefined'?ERROR_EXTRA_ROWS.filter(function(item){return item[0]===code;})[0]:null;
    if(!row&&typeof ERROR_ROWS!=='undefined')row=ERROR_ROWS.filter(function(item){return item[0]===code;})[0];
    if(row)return row.length>=8?bi(row[4],row[5])+(row[6]?' '+bi(row[6],row[7]):''):code+' · '+bi(row[2],row[3]);
    return typeof AUTO_BLOCKERS!=='undefined'&&Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?autoBlockerText(code):bi('Switching is currently unavailable.','Переключение сейчас недоступно.');}).filter(function(text,index,all){return all.indexOf(text)===index;}).join(' ');
}
function manualSelectionModel(status,source,target,now){
  var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
  if(proof.authoritative)return {selected:source&&proof.selected===source.id?'primary':target&&proof.selected===target.id?'reserve':null,moving:proof.moving,code:proof.code};
  var native=status.native_failover||{};
  if(!status.rpc_error&&manualFresh(status.time,now,90)&&manualFresh(native.time,now,30)&&['STOPPED','DISABLED','EXPIRED'].indexOf(native.state)>=0&&source&&target&&profileHealth(source,now).state==='inactive'&&profileHealth(target,now).state==='inactive')return {selected:null,moving:false,off:true};
  var path=manualConfirmedPath(status,source,target,now);
  return {selected:path.selected==='source'?'primary':path.selected==='target'?'reserve':null,moving:path.moving};
}
function manualRecordedResult(status,now){
  var request=status.manual_switch||{};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90)||!manualFresh(request.updated_at,now,300)||request.state!=='COMPLETED'||request.completed!==true||request.code!=='MANUAL-ALREADY-SELECTED')return null;
  return E('p',{'data-manual-result':'already-selected'},[typeof errorCodeLink==='function'?errorCodeLink(request.code):request.code,' · ',bi('Last manual request: the channel was already selected and verified; no additional switch was needed.','Последний ручной запрос: канал уже был выбран и проверен; повторное переключение не потребовалось.')]);
}
function renderManualSwitch(status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=manualControlModel(status,now),buttons=[],labels={},actionMarks={},signals={},settings=(inventory||{}).settings||{},ns=status.native_failover||{},route=status.channel_path||{},profiles=status.profiles||[];
  var source=profiles.filter(function(p){return p.id===(settings.plan_source||route.source_profile_id||ns.source);})[0],target=profiles.filter(function(p){return p.id===(settings.plan_target||route.target_profile_id||ns.target);})[0];
  var selection=manualSelectionModel(status,source,target,now);
  var pendingDirection=MANUAL_SWITCH_PENDING?MANUAL_SWITCH_DIRECTION:model.busy?(status.manual_switch||{}).direction:selection.moving?(ns.state==='RESTORING'||ns.reason==='PAIR-CONNECTING'||ns.reason==='PAIR-WAITING-PROBES'?'primary':'reserve'):null;
  function notice(text){ui.addNotification(null,E('p',{},text));}
  function button(direction,label){
    var enabled=model[direction].allowed,n=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-manual-direction':direction,'disabled':enabled?null:'','click':function(){
      if(MANUAL_SWITCH_PENDING||!enabled||!manualControlModel(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000))[direction].allowed)return;
      MANUAL_SWITCH_PENDING=true;MANUAL_SWITCH_DIRECTION=direction;buttons.forEach(function(node){node.disabled=true;var key=node.hvManualDirection;if(key==='primary'||key==='reserve'){node.setAttribute('class','hv-manual-channel hv-manual-'+(key===direction?'yellow':'red'));if(labels[key])labels[key].textContent=key===direction?bi('Switching','Переключение'):'';if(actionMarks[key])actionMarks[key].hidden=true;if(signals[key])signals[key].setAttribute('data-active','false');}});var request;
      try{var call=model.mode==='continuous-pair'?rpc.declare({object:'homensai-vpn',reject:true,reject:true,method:'pair_manual',params:['direction','control_revision','request_source'],expect:{}}):rpc.declare({object:'homensai-vpn',reject:true,reject:true,method:'manual_switch',params:['direction','control_revision','request_source'],expect:{}});request=call(direction,model.revision,'manual');}catch(e){request=Promise.reject(e);}
      return Promise.resolve(request).then(function(result){
        if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id))notice(model.mode==='continuous-pair'?bi('Request queued. Wait for confirmed completion. Auto stays on and keeps protecting the selected channel.','Запрос поставлен в очередь. Дождитесь подтверждения. Auto остаётся включённым и продолжает защищать выбранный канал.'):bi('Manual switch requested. Wait for the router to confirm the active path. This request does not enable Auto.','Ручное переключение запрошено. Дождитесь подтверждения активного пути роутером. Этот запрос не включает Auto.'));
        else notice(manualReason(result&&Array.isArray(result.blockers)?result.blockers.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}):[]));
      }).catch(function(){notice(bi('The request was not confirmed. Refresh the router state before trying again.','Запрос не подтверждён. Обновите состояние роутера перед повтором.'));}).finally(function(){MANUAL_SWITCH_PENDING=false;MANUAL_SWITCH_DIRECTION=null;buttons.forEach(function(node){node.disabled=true;});});
    }},label);n.hvManualDirection=direction;buttons.push(n);return n;
  }
  function signal(direction,active){
    var icons=[
      '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
      '<rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 18h.01M10 18h.01M17 14V2M2 6a16 16 0 0 1 20 0M5 9a11 11 0 0 1 9-1"/>',
      '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><path d="M6 6h.01M6 18h.01"/>'
    ];
    var names=[bi('Computer','Компьютер'),bi('Router','Роутер'),bi('VPN server','VPN-сервер')],parts=[];
    icons.forEach(function(paths,index){
      if(index)parts.push(E('span',{'class':'hv-signal-wire','aria-hidden':'true'},[E('i',{}),E('i',{}),E('i',{})]));
      var icon=E('span',{'class':'hv-signal-device','aria-hidden':'true'});
      icon.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+paths+'</svg>';
      parts.push(E('span',{'class':'hv-signal-node'},[icon,E('span',{},names[index])]));
    });
    var diagram=E('span',{'class':'hv-channel-signal','data-active':active?'true':'false','role':'img','aria-label':bi('Computer connected through the router to the VPN server','Компьютер подключён через роутер к VPN-серверу')},parts);
    signals[direction]=diagram;return diagram;
  }
  function choice(direction,profile,role){
    var selected=selection.selected===direction,pending=model.busy||selection.moving;
    var health=profile?profileHealth(profile,now).state:'unknown';
    var autoRuns=typeof autoWorking!=='function'||typeof autoLightModel!=='function'||autoWorking(autoLightModel(status,inventory,now));
    var stale=!!status.rpc_error||!Number.isFinite(status.time)||now-status.time>90||now-status.time< -5;
    if(stale||selection.code&&health==='healthy')health='unknown';
    var waiting=!pending&&health==='healthy'&&(!autoRuns||!selected);
    var color=waiting?'yellow':health==='failed'||health==='inactive'?'red':pending||!selection.selected||selection.off?'grey':selected&&health==='healthy'?'green':'grey';
    var protocol=profile?(typeof protocolLabel==='function'?protocolLabel(profile):profile.protocol==='wireguard'?'WireGuard':'OpenVPN'):bi('Profile not chosen','Профиль не выбран');
    var healthText=selection.code?bi('Traffic selection is not verified','Выбор канала трафика не подтверждён')+' · '+selection.code:waiting?(direction==='primary'?bi('Primary channel: Alive; you can switch to it manually','Основной канал: Живой, можно переключиться на него вручную'):bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную')):pending?(pendingDirection===direction?bi('Switching','Переключение'):''):!selected?(health==='healthy'?bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную'):bi('Internet channel not in use','Интернет-канал не задействован')):health==='healthy'?(direction==='primary'?bi('Internet: primary channel in use','Интернет: задействован основной канал'):bi('Internet: reserve in use','Интернет: задействован резерв')):health==='failed'?bi('Internet: connection check failed','Интернет: ошибка проверки соединения')+(profile&&profile.code?' · '+profile.code:''):health==='inactive'?bi('Internet: VPN tunnel disconnected','Интернет: VPN-туннель отключён'):bi('Internet: checking the connection','Интернет: выполняется проверка соединения');
    var country=profile&&typeof countryLabel==='function'?countryLabel(profile):null;
    var indicator=E('strong',{'class':'hv-manual-health hv-health-'+health},healthText);labels[direction]=indicator;
    var action=!selected&&model[direction].allowed&&!pending?E('b',{'class':'hv-manual-enable'},bi('Turn on','Включить')):null;actionMarks[direction]=action;
    var card=button(direction,[E('small',{},role),E('strong',{'class':'hv-manual-protocol'},protocol),country?E('span',{},country):null,typeof endpointText==='function'?E('small',{},endpointText(profile,now)):null,typeof renderChannelPing==='function'?renderChannelPing(profile,status,now):null,signal(direction,selected&&health==='healthy'&&!pending),indicator,
      action].filter(Boolean));
    card.setAttribute('class','hv-manual-channel hv-manual-'+color);card.setAttribute('aria-pressed',selected?'true':'false');card.setAttribute('data-selected',selected?'true':'false');
    if(selected&&!pending)card.disabled=true;
    var reason=false&&!selected&&!model[direction].allowed&&!pending?E('details',{'class':'hv-manual-diagnostic','data-manual-diagnostic':direction},[E('summary',{},bi('Why this channel is not available','Почему канал недоступен')),E('p',{},manualReason(model[direction].blockers))]):null;
    if(reason&&typeof rememberDisclosure==='function')rememberDisclosure(reason,'manual-'+direction);
    return E('div',{'class':'hv-manual-choice'},[card,reason].filter(Boolean));
  }
  return E('section',{'class':'hv-chart-card hv-manual-switch','data-manual-controls':'1'},[
    E('h3',{},bi('Manual channel switch','Ручное переключение канала')),
    typeof renderLatencyRecommendation==='function'?renderLatencyRecommendation(status,inventory,'manual'):null,
    E('div',{'class':'hv-manual-channel-grid'},[choice('primary',source,bi('Primary channel','Основной канал')),choice('reserve',target,bi('Reserve channel','Резервный канал'))]),
    manualRecordedResult(status,now),
    E('p',{},bi('Green: works in Auto. Yellow: Alive; you can switch to it manually. Grey: waiting for the router\'s answer. Red: error, does not work.','Зелёный — работает в автомате. Жёлтый — Живой, можно переключиться на него вручную. Серый — ждём ответа роутера. Красный — ошибка, не работает.')),
    false&&!selection.selected&&!selection.moving&&!selection.off?E('p',{'role':'status'},bi('The router has not returned a verified channel selection yet. Updating its policy state; no channel is assumed active from a button press.','Роутер ещё не передал проверенный выбор канала. Обновляем состояние маршрутизации; нажатие кнопки само по себе не означает, что канал выбран.')):null,
    !model.busy&&manualFresh((status.manual_switch||{}).updated_at,now,300)&&['REFUSED','UNCONFIRMED'].indexOf((status.manual_switch||{}).state)>=0?E('details',{'class':'hv-manual-error','data-manual-diagnostic':'last-request'},[E('summary',{'role':'alert'},bi('Switch not completed: ','Переключение не выполнено: ')+((status.manual_switch||{}).code||'MANUAL-SWITCH-UNCONFIRMED')),E('p',{},manualReason([(status.manual_switch||{}).code]))]):null,
    model.busy?E('p',{'role':'status'},bi('A switch request is pending. Wait for confirmation or press the Auto power button to stop.','Запрос переключения ожидает подтверждения. Дождитесь результата или нажмите кнопку Auto для остановки.')):null
  ].filter(Boolean));
}

/* Live selected-route timeline. It does not invent throughput or LAN health. */
var autoLivePoints=[],autoLiveKey='',autoLiveContext=null,autoLivePollAdded=false,autoLiveCall=null;
var AUTO_LIVE_COLORS={source:'#16a34a',target:'#2563eb',off:'#64748b',down:'#dc2626',blocked:'#9333ea'};
// Both channels failing their router checks is a state of its own, never an empty line.
function autoLiveBothDown(status,inventory,now){
  var rows=(status||{}).profiles;if(!Array.isArray(rows)||!rows.length||!(Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90))return false;
  var ids=typeof rolePairIds==='function'?rolePairIds(status,inventory||{},now):[];
  if(ids.length!==2||!ids[0]||!ids[1]||ids[0]===ids[1])return false;
  return ids.every(function(id){var p=rows.filter(function(r){return r&&r.id===id;})[0];return p&&Number.isFinite(p.time)&&now-p.time>=-5&&now-p.time<=90&&!(p.code==null&&p.dns_ok===true&&p.https_success>=2);});
}
function autoLiveSample(status,now,inventory){
  status=status||{};
  var ns=(status||{}).native_failover||{},valid=Number.isFinite(now)&&!status.rpc_error&&!(status.speed_pause&&status.speed_pause.active)&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var kind='unknown',state=String(ns.state||'UNKNOWN');
  var path=typeof channelPathSelection==='function'?channelPathSelection(status,now,ns.source,ns.target):{authoritative:ns.mode==='continuous-pair',selected:null,moving:false,code:ns.mode==='continuous-pair'?'KERNEL-POLICY-UNVERIFIED':null};
  if(valid){
    var intent=status.auto_control||{},pairRunning=intent.requested==='on'&&intent.pair_phase==='RUNNING';
    if(['DISABLED','STOPPED','EXPIRED'].indexOf(state)>=0||state==='ROLLED-BACK'&&!pairRunning)kind='off';
    else if(path.authoritative)kind=path.moving?'switching':path.selected?(path.selected===(status.channel_path||{}).source_profile_id?'source':'target'):state==='BLOCKED'||state==='FAILED'?'blocked':'unknown';
    else if(state==='OBSERVING'&&ns.certified===true)kind='source';
    else if(['COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE'].indexOf(state)>=0)kind='target';
    else if(['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(state)>=0)kind='switching';
    else if(['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(state)>=0)kind='off';
    else if(['BLOCKED','FAILED'].indexOf(state)>=0)kind='blocked';
  }
  if(Number.isFinite(now)&&!status.rpc_error&&autoLiveBothDown(status,inventory,now))kind='down';
  var codes=Array.isArray(ns.blockers)?ns.blockers.slice(0,3):[];if(path.code&&codes.indexOf(path.code)<0)codes.push(path.code);
  return {time:now,stamp:valid?ns.time:null,kind:kind,state:state,selected_profile_id:path.selected,codes:codes};
}
function autoLiveAppend(points,sample){
  var rows=points.slice(-599),last=rows[rows.length-1];
  if(!Number.isFinite(sample.time)||last&&sample.time<last.time)return rows;
  if(last&&sample.time===last.time){rows[rows.length-1]=sample;return rows;}
  if(last&&sample.stamp!==null&&last.stamp!==null&&sample.stamp<last.stamp)return rows;
  rows.push(sample);
  return rows.filter(function(p){return sample.time-p.time<=1800;});
}
function autoLiveSegments(points){
  var rows=[];
  for(var i=1;i<points.length;i++){
    var a=points[i-1],b=points[i],gap=b.time-a.time;
    rows.push({a:a,b:b,kind:a.kind,gap:gap>15||!AUTO_LIVE_COLORS[a.kind]||!AUTO_LIVE_COLORS[b.kind]});
  }
  return rows;
}
function autoLiveDisplayPoints(points){
  var last=null,previous=null;
  return points.map(function(point){
    if(previous&&point.time-previous.time>15)last=null;
    var kind=point.kind;
    if(kind==='switching')kind=last||'unknown';
    else if(!AUTO_LIVE_COLORS[kind])last=null;
    if(AUTO_LIVE_COLORS[kind])last=kind;
    previous=point;return Object.assign({},point,{kind:kind});
  });
}
function autoLiveLabel(kind){return kind==='source'?bi('Primary selected','Выбран основной'):kind==='target'?bi('Reserve selected','Выбран резерв'):kind==='switching'?bi('Starting / switching / restoring','Запуск / переключение / восстановление'):kind==='off'?bi('Auto off','Auto выключен'):kind==='down'?bi('No working channel: both channels fail the router checks','Нет работающего канала: оба канала не проходят проверки роутера'):kind==='blocked'?bi('Auto is blocked, the route is not being managed','Auto заблокирован, маршрутом никто не управляет'):bi('No fresh confirmation: Auto is not running or the data is old','Нет свежего подтверждения: Auto не работает или данные устарели');}
function autoLiveSvg(tag,attributes,text){
  var node=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.keys(attributes||{}).forEach(function(key){node.setAttribute(key,String(attributes[key]));});
  if(text!==undefined)node.textContent=text;
  return node;
}
function drawAutoLive(root,status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),settings=(inventory||{}).settings||{},ns=(status||{}).native_failover||{};
  var key=[settings.plan_source||ns.source||'',settings.plan_target||ns.target||''].join('|');
  if(key!==autoLiveKey){autoLivePoints=[];autoLiveKey=key;}
  var sample=autoLiveSample(status,now,inventory);autoLivePoints=autoLiveAppend(autoLivePoints,sample);
  var width=Math.max(280,Math.min(720,root.clientWidth||document.documentElement.clientWidth-80||720));
  var points=autoLiveDisplayPoints(autoLivePoints),from=Math.max(now-1800,Math.min(now-60,points.length?points[0].time:now-60)),span=now-from,left=width<480?88:122,right=width-16;
  var displayed=points.length?points[points.length-1]:sample;
  var x=function(t){return left+(t-from)/span*(right-left);};
  var y=function(kind){return kind==='source'?44:kind==='target'?91:132;};
  var svg=autoLiveSvg('svg',{viewBox:'0 0 '+width+' 168',width:'100%',height:'168',role:'img','aria-label':bi('Live selected VPN route over time','Выбранный VPN-маршрут в реальном времени')});
  [['source',bi('Primary','Основной')],['target',bi('Reserve','Резерв')],['off',bi('Off / no channel','Выкл. / нет канала')]].forEach(function(row){var yy=y(row[0]);svg.appendChild(autoLiveSvg('line',{x1:left,y1:yy,x2:right,y2:yy,stroke:'#cbd5e1','stroke-dasharray':'3 5'}));svg.appendChild(autoLiveSvg('text',{x:6,y:yy+4,fill:'currentColor','font-size':12},row[1]));});
  autoLiveSegments(points).forEach(function(segment){if(segment.gap)return;var a=segment.a,b=segment.b;svg.appendChild(autoLiveSvg('path',{d:'M '+x(a.time)+' '+y(a.kind)+' H '+x(b.time)+' V '+y(b.kind),fill:'none',stroke:AUTO_LIVE_COLORS[segment.kind],'stroke-width':3}));});
  var lastRoute=null,changes=[];
  points.forEach(function(point){if(point.kind==='source'||point.kind==='target'){if(lastRoute&&lastRoute.kind!==point.kind)changes.push(point);lastRoute=point;}});
  changes.slice(-5).forEach(function(point){var xx=x(point.time);svg.appendChild(autoLiveSvg('line',{x1:xx,y1:23,x2:xx,y2:106,stroke:AUTO_LIVE_COLORS[point.kind],'stroke-dasharray':'2 3'}));svg.appendChild(autoLiveSvg('text',{x:Math.max(left,Math.min(right-54,xx+3)),y:17,fill:'currentColor','font-size':10},new Date(point.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB')));});
  if(points.length&&AUTO_LIVE_COLORS[displayed.kind])svg.appendChild(autoLiveSvg('circle',{cx:x(displayed.time),cy:y(displayed.kind),r:5,fill:AUTO_LIVE_COLORS[displayed.kind]}));
  [from,from+span/2,from+span].forEach(function(stamp){svg.appendChild(autoLiveSvg('text',{x:x(stamp),y:157,'text-anchor':stamp===from?'start':stamp===from+span?'end':'middle',fill:'currentColor','font-size':10},new Date(stamp*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB')));});
  while(root.firstChild)root.removeChild(root.firstChild);
  root.appendChild(E('h3',{},bi('Live channel switching','Переключение каналов в реальном времени')));
  root.appendChild(E('p',{'class':'hv-auto-live-state'},autoLiveLabel(sample.kind)+' · '+new Date(now*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB')));
  root.appendChild(svg);
  root.appendChild(E('p',{'class':'hv-muted'},bi('Green: primary · Blue: reserve · Grey: off · Purple: Auto blocked · Red: no working channel. During a transition the last confirmed route is held until a new one is confirmed; missing observations leave a gap. Updated every 2 seconds while open. This shows confirmed route selection, not bandwidth or external-LAN verification.','Зелёный: основной · Синий: резерв · Серый: выключено · Фиолетовый: Auto заблокирован · Красный: нет работающего канала. При переходе остаётся последний подтверждённый маршрут до подтверждения нового; отсутствие данных показано разрывом. Обновление каждые 2 секунды, пока страница открыта. График показывает подтверждённый выбор маршрута, а не скорость или проверку внешнего LAN.')));
}
function renderAutoLive(status,inventory){
  var root=E('div',{'id':'hv-auto-live-chart','class':'hv-auto-live-chart'});
  autoLiveContext={status:status,inventory:inventory};drawAutoLive(root,status,inventory);
  if(!autoLivePollAdded&&typeof poll!=='undefined'){
    autoLivePollAdded=true;
    poll.add(function(){
      var node=document.getElementById('hv-auto-live-chart');
      if(!node||!node.getClientRects().length||typeof document!=='undefined'&&document.hidden)return Promise.resolve();
      if(!autoLiveCall)autoLiveCall=rpc.declare({object:'homensai-vpn',reject:true,method:'auto_live',expect:{}});
      return autoLiveCall().then(function(live){if(document.getElementById('hv-auto-live-chart')===node)drawAutoLive(node,live,autoLiveContext.inventory);}).catch(function(){if(document.getElementById('hv-auto-live-chart')===node)drawAutoLive(node,{rpc_error:true},autoLiveContext.inventory);});
    },2);
  }
  return root;
}
var autoDayHours=24;
function autoDayWindow(value){var n=Number(value);return Number.isInteger(n)&&n>=1&&n<=24?n:24;}
try{if(typeof window!=='undefined'&&window.sessionStorage)autoDayHours=autoDayWindow(window.sessionStorage.getItem('homensai-vpn-day-hours'));}catch(e){}
function autoDaySegments(history,now,hours){
  if(!history||!Array.isArray(history.segments)||!Number.isFinite(now))return [];
  var from=now-autoDayWindow(hours)*3600,last=null,previousEnd=null,rows=[];
  history.segments.slice(-4096).forEach(function(row){
    if(!row||['source','target','off','unknown','switching','blocked','down'].indexOf(row.kind)<0||!Number.isFinite(row.start)||!Number.isFinite(row.end)||row.start>row.end||row.start>now||row.end>now+5){last=null;previousEnd=null;return;}
    if(previousEnd!==row.start)last=null;
    var kind=row.kind==='switching'?last:row.kind;
    previousEnd=row.end;
    if(!AUTO_LIVE_COLORS[kind]){last=null;return;}
    last=kind;if(row.end>from)rows.push({start:Math.max(from,row.start),end:Math.min(now,row.end),kind:kind});
  });return rows;
}
function autoDayFailures(history,now,hours){
  var from=now-autoDayWindow(hours)*3600,bins=[],totals={source:0,target:0},excluded=0;
  function routes(){return {source:0,target:0,off:0,unrecorded:0};}
  for(var i=0;i<autoDayWindow(hours);i++)bins.push({start:from+i*3600,source:0,target:0,selected:routes(),routes:{source:routes(),target:routes()}});
  ((history||{}).events||[]).forEach(function(row){
    if(!Array.isArray(row)||!Number.isFinite(row[0])||row[0]<from||row[0]>now)return;
    if(['source','target'].indexOf(row[1])<0){excluded++;return;}
    var bin=bins[Math.min(bins.length-1,Math.floor((row[0]-from)/3600))],selected=['source','target','off'].indexOf(row[2])>=0?row[2]:'unrecorded';
    bin[row[1]]++;totals[row[1]]++;bin.selected[selected]++;bin.routes[row[1]][selected]++;
  });return {bins:bins,totals:totals,excluded:excluded};
}
function drawAutoFailures(plot,history,now,hours,width,left,right){
  while(plot.firstChild)plot.removeChild(plot.firstChild);
  var data=autoDayFailures(history,now,hours),max=Math.max(1,...data.bins.map(function(b){return Math.max(b.source,b.target);}));
  var labels={source:bi('Primary','Основной'),target:bi('Reserve','Резервный')},colors={source:'#2563eb',target:'#e07816'};
  var routeLabels={source:bi('primary','основной'),target:bi('reserve','резерв'),off:bi('Auto off','Auto выключен'),unrecorded:bi('route not recorded','маршрут не записан')};
  plot.appendChild(E('h3',{},bi('Failure episodes · last '+hours+' h','Отказы каналов · последние '+hours+' ч')));
  plot.appendChild(E('div',{'class':'hv-failure-legend'},['source','target'].map(function(role){return E('span',{'class':'hv-failure-key','data-failure-role':role},[E('span',{'aria-hidden':'true','style':'background:'+colors[role]}),labels[role]+': '+data.totals[role]]);})));
  var svg=autoLiveSvg('svg',{viewBox:'0 0 '+width+' 175',width:'100%',height:175,role:'img','aria-label':bi('Primary failures in blue; reserve failures in orange; episodes per hour','Отказы основного — синим, резервного — оранжевым; эпизоды по часам')});
  [0,max].forEach(function(n){var y=135-n/max*100;svg.appendChild(autoLiveSvg('line',{x1:left,x2:right,y1:y,y2:y,stroke:'#cbd5e1'}));svg.appendChild(autoLiveSvg('text',{x:left-8,y:y+4,'text-anchor':'end',fill:'currentColor','font-size':11},String(n)));});
  var step=(right-left)/hours;
  data.bins.forEach(function(bin,index){
    ['source','target'].forEach(function(role,j){
      if(!bin[role])return;
      var bar=autoLiveSvg('rect',{x:left+index*step+j*step/2,y:135-bin[role]/max*100,width:Math.max(.5,step/2-1),height:bin[role]/max*100,fill:colors[role],'data-failure-role':role});
      var routes=Object.keys(routeLabels).filter(function(k){return bin.routes[role][k]>0;}).map(function(k){return routeLabels[k]+': '+bin.routes[role][k];}).join(', ');
      bar.appendChild(autoLiveSvg('title',{},new Date(bin.start*1000).toLocaleString()+' — '+new Date((bin.start+3600)*1000).toLocaleTimeString()+' · '+labels[role]+': '+bin[role]+' · '+bi('Traffic route during these failures: ','Маршрут при этих отказах: ')+routes));svg.appendChild(bar);
    });
  });
  [0,.5,1].forEach(function(f){svg.appendChild(autoLiveSvg('text',{x:left+(right-left)*f,y:160,'text-anchor':f===0?'start':f===1?'end':'middle',fill:'currentColor','font-size':10},new Date((now-hours*3600+f*hours*3600)*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit'})));});
  plot.appendChild(svg);
  if(!data.totals.source&&!data.totals.target)plot.appendChild(E('p',{'class':'hv-muted'},bi('No failure episodes with saved channel roles in this window.','В этом окне пока нет отказов с сохранённой ролью.')));
  plot.appendChild(E('p',{'class':'hv-muted'},bi('One outage is counted once until recovery. Blue: primary. Orange: reserve. Hover over a bar for the recorded traffic route.','Один отказ считается один раз до восстановления. Синий — основной, оранжевый — резервный. Наведите на столбец, чтобы увидеть записанный маршрут.')));
  if(!history||history.details_dropped||!Number.isFinite(history.since)||history.since>now-hours*3600)plot.appendChild(E('p',{'class':'hv-muted'},bi('Incomplete history: only what was saved is shown.','История неполная: показано только то, что сохранилось.')));
}
function renderAutoDay(status){
  var root=E('section',{'id':'hv-auto-day-chart','class':'hv-auto-live-chart hv-auto-day-chart'});
  var failures=E('div',{'class':'hv-auto-failures'});
  var heading=E('h3'),plot=E('div',{'class':'hv-auto-day-plot'}),value=E('output',{'for':'hv-auto-day-range','class':'hv-auto-day-window-value'});
  var slider=E('input',{'type':'range','id':'hv-auto-day-range','min':1,'max':24,'step':1,'value':autoDayHours,'aria-label':bi('Graph window, 1 to 24 hours','Окно графика, от 1 до 24 часов'),'input':function(event){
    autoDayHours=autoDayWindow(event.target.value);slider.value=autoDayHours;
    try{window.sessionStorage.setItem('homensai-vpn-day-hours',String(autoDayHours));}catch(e){}
    drawPlot();
  }});
  function drawPlot(){
    var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),hours=autoDayWindow(autoDayHours),span=hours*3600;
    var history=(((status||{}).accounting||{}).reliability||{}).route_history||{},segments=autoDaySegments(history,now,hours);
    var width=Math.max(280,Math.min(720,document.documentElement.clientWidth-80||720)),left=width<480?88:122,right=width-16;
    var from=now-span,x=function(t){return left+(t-from)/span*(right-left);},y=function(kind){return kind==='source'?44:kind==='target'?91:132;};
    var svg=autoLiveSvg('svg',{viewBox:'0 0 '+width+' 168',width:'100%',height:'168',role:'img','aria-label':bi('Saved selected VPN route over the last '+hours+' hours','Сохранённый VPN-маршрут за последние '+hours+' ч')});
    [['source',bi('Primary','Основной')],['target',bi('Reserve','Резерв')],['off',bi('Off / no channel','Выкл. / нет канала')]].forEach(function(row){
      svg.appendChild(autoLiveSvg('line',{x1:left,x2:right,y1:y(row[0]),y2:y(row[0]),stroke:'#cbd5e1','stroke-dasharray':'3 5'}));
      svg.appendChild(autoLiveSvg('text',{x:6,y:y(row[0])+4,fill:'currentColor','font-size':12},row[1]));
    });
    var previous=null;
    segments.forEach(function(row){
      if(previous&&previous.end===row.start&&previous.kind!==row.kind)svg.appendChild(autoLiveSvg('line',{x1:x(row.start),x2:x(row.start),y1:y(previous.kind),y2:y(row.kind),stroke:AUTO_LIVE_COLORS[row.kind],'stroke-width':2}));
      var path=autoLiveSvg('line',{x1:x(row.start),x2:x(row.end),y1:y(row.kind),y2:y(row.kind),stroke:AUTO_LIVE_COLORS[row.kind],'stroke-width':3});
      path.appendChild(autoLiveSvg('title',{},autoLiveLabel(row.kind)+' · '+new Date(row.start*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB')+' — '+new Date(row.end*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB')));svg.appendChild(path);previous=row;
    });
    [0,.25,.5,.75,1].forEach(function(fraction,index){var stamp=from+fraction*span;svg.appendChild(autoLiveSvg('text',{x:x(stamp),y:157,'text-anchor':index===0?'start':index===4?'end':'middle',fill:'currentColor','font-size':10},new Date(stamp*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit'})));});
    while(plot.firstChild)plot.removeChild(plot.firstChild);plot.appendChild(svg);
    drawAutoFailures(failures,(((status||{}).accounting||{}).reliability||{}).failure_history,now,hours,width,left,right);
    heading.textContent=bi('Channel switching · last '+hours+' h','Переключение каналов · последние '+hours+' ч');
    value.textContent=hours+' '+bi('h','ч');slider.setAttribute('aria-valuetext',hours+' '+bi('hours','ч'));
  }
  root.appendChild(heading);root.appendChild(plot);
  root.appendChild(E('div',{'class':'hv-auto-day-window'},[E('label',{'for':'hv-auto-day-range'},[bi('Graph window: ','Окно графика: '),value]),slider,E('div',{'class':'hv-auto-day-range-labels'},[E('span',{},bi('1 h','1 ч')),E('span',{},bi('24 h','24 ч'))])]));
  root.appendChild(E('p',{'class':'hv-muted'},bi('History is saved on the router. Three levels: primary, reserve, off. During a transition the last confirmed route remains; missing data leaves a gap.','История хранится на роутере. Три уровня: основной, резерв, выключено. При переходе остаётся последний подтверждённый маршрут; отсутствие данных показано разрывом.')));
  root.appendChild(failures);drawPlot();return root;
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
  var paused=!!status.speed_pause&&status.speed_pause.active===true&&status.speed_pause.auto_paused===true;
  var monitorFresh=Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var fresh=!status.rpc_error&&monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var runningPair=(ns.mode==='continuous-pair'||ns.proof_scope==='router-probed-ipv4'||(status.channel_path||{}).mode==='continuous-pair')&&intent.requested==='on'&&intent.pair_phase==='RUNNING';
  var on=!paused&&fresh&&((ns.state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true))||ns.state==='COMMITTED'||ns.state==='ROLLED-BACK'&&runningPair);
  var transitioning=fresh&&['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0;
  var off=fresh&&!on&&['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(ns.state)>=0;
  var awaiting=fresh&&intent.requested_at>ns.time;
  return {fresh:fresh,on:on,paused:paused,transitioning:transitioning,off:off,awaiting:awaiting,
    stop:on||transitioning||intent.requested==='on'||['DEGRADED-ON-RESERVE','COMMITTED','ARMED','APPLYING','WAIT-CLIENT','RESTORING','STOPPED-ON-RESERVE'].indexOf(ns.state)>=0,
    returned:off&&ns.original_restored===true,
    color:paused?'pending':!fresh?'unknown':awaiting||transitioning?'pending':on?'on':off?'off':'error'};
}
function autoPathModel(status,source,target,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{};
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
  if(proof.authoritative){
    var picked=source&&proof.selected===source.id?'source':target&&proof.selected===target.id?'target':null;
    function tone(p,key){var h=p?profileHealth(p,now).state:'unknown';return h==='failed'?'failed':h==='inactive'?'inactive':h==='unknown'?'neutral':proof.moving||h==='checking'?'checking':picked===key?'healthy':picked?'ready':'neutral';}
    return {source:tone(source,'source'),target:tone(target,'target'),direction:proof.moving?'forward':picked==='target'?'forward':'none',moving:proof.moving,selected:picked,code:proof.code};
  }
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

function autoNoInternetLink(){
  return E('a',{'href':'#help','click':function(ev){if(typeof openHelpTopic==='function'){ev.preventDefault();openHelpTopic('no-internet');}}},bi('Help: no internet?','Справка: нет интернета?'));
}
var AUTO_BLOCKERS={
  'GUARD-DEVICE-UNVERIFIED':['An enabled VPN interface has no readable live state. Check Network → Interfaces for the selected clients; deleted or disabled profiles are excluded.','Не удалось прочитать рабочее состояние включённого VPN-интерфейса. Проверьте выбранные клиенты в «Сеть → Интерфейсы»; удалённые и отключённые профили исключаются.'],
  'EXISTING-TUNNEL-BINDING-UNVERIFIED':['The two selected VPN clients need distinct, confirmed live interfaces, routing tables and marks. Check the selected pair and current tunnel state.','У двух выбранных VPN-клиентов должны быть разные подтверждённые интерфейсы, таблицы маршрутизации и метки. Проверьте выбранную пару и текущее состояние туннелей.'],
  'MT3000-FIRMWARE-UNVERIFIED':['The actual MT3000 firmware, kernel or architecture does not match the verified profile. Keep monitoring and check the router facts.','Фактическая прошивка, ядро или архитектура MT3000 не совпадает с проверенным профилем. Оставьте мониторинг и проверьте данные роутера.'],
  'MT3000-FIREWALL-UNVERIFIED':['This MT3000 firewall arrangement is not verified. Native switching remains blocked.','Этот вариант firewall MT3000 не проверен. Нативное переключение остаётся заблокировано.'],
  'FW3-INCLUDE-CONTRACT-UNVERIFIED':['The stock FW3 VPN include differs from the verified configuration. Review it before switching.','VPN include штатного FW3 отличается от проверенной конфигурации. Проверьте его перед переключением.'],
  'FW3-RUNTIME-STATE-UNVERIFIED':['The running FW3 state cannot be verified. A connected VPN alone is insufficient.','Не удалось проверить рабочее состояние FW3. Одного подключённого VPN недостаточно.'],
  'FW3-SELECTED-ZONE-UNVERIFIED':['The running firewall does not contain both verified VPN zones.','Рабочий firewall не содержит обе проверенные VPN-зоны.'],
  'VENDOR-WORKER-QUIET-UNVERIFIED':['Completion of the router background work is unconfirmed. New switching stays blocked.','Завершение фоновой работы роутера не подтверждено. Новое переключение заблокировано.'],
  'MONITOR-ONLY-DEPLOYMENT':['This installation is limited to monitoring. Native switching is disabled; monitoring does not certify router firmware coordination or the LAN path.','Эта установка ограничена мониторингом. Нативное переключение выключено; мониторинг не подтверждает координацию с прошивкой роутера и путь LAN.'],
  'MONITOR-ONLY-INVALID':['The deployment mode could not be verified. Native actions remain blocked until the deployment settings are checked.','Не удалось проверить режим установки. Нативные действия остаются заблокированы до проверки параметров установки.'],
  'NATIVE-PROGRESS-UNVERIFIED':['Controller progress records cannot be trusted. New actions are blocked; Stop and recovery from a trusted journal remain available. Review the diagnostics before retrying.','Записям состояния контроллера нельзя доверять. Новые действия заблокированы; остановка и восстановление по доверенному журналу остаются доступны. Перед повтором проверьте диагностику.'],
  'RESERVE-IDENTITY-UNKNOWN':['Current reserve identity could not be matched to comparable observations. Its health and any automatic return remain unconfirmed.','Не удалось сопоставить текущий резерв с подходящими наблюдениями. Его здоровье и автоматический возврат остаются неподтверждёнными.'],
  'OBSERVATION-STALE':['Current tunnel or probe observations are missing or stale. Wait for fresh matching observations; old measurements cannot authorize a change.','Текущие наблюдения туннеля или проверок отсутствуют либо устарели. Дождитесь свежих согласованных данных; старые измерения не разрешают изменение.'],
  'VENDOR-IDENTITY-UNKNOWN':['The router tunnel binding is unknown or ambiguous. Save an active source and reserve in Settings after their exact bindings are observed.','Привязка туннеля роутера неизвестна или неоднозначна. Сохраните активный основной и резервный профили в настройках после наблюдения точных привязок.'],
  'VENDOR-SAME-TUNNEL':['Both profiles belong to one router tunnel. Server selection inside it belongs to the router firmware; this app does not switch that pair.','Оба профиля относятся к одному туннелю роутера. Выбор серверов внутри него относится к штатной прошивке; приложение не переключает такую пару.'],
  'RESERVE-NOT-CONNECTED':['The reserve channel is enabled but not connected. Auto tries to start it by itself (at most every two minutes); the primary keeps working meanwhile. If it stays down, check or replace the reserve server.','Резервный канал включён, но не подключён. Auto сам пытается его запустить (не чаще раза в две минуты); основной канал пока работает. Если резерв не поднимается, проверьте или замените сервер резерва.'],
  'PROFILE-IDENTITY-CHANGED':['The configured profile or tunnel binding changed. Old checks no longer describe the current member; wait for fresh observations and repeat validation.','Профиль или привязка туннеля изменились. Старые проверки больше не описывают текущий сервер; дождитесь свежих наблюдений и повторите проверку.'],
  'VENDOR-SETTLING':['The configured tunnel identity observation window is still pending. This does not establish whether firmware retries have finished.','Окно наблюдения за конфигурацией туннеля ещё не завершено. Это не устанавливает, закончились ли повторные попытки прошивки.'],
  'CONTROL-REVISION-STALE':['Auto controls changed. Refresh the current state before starting again.','Состояние управления Auto изменилось. Обновите данные перед новым запуском.'],
  'START-STATE-UNVERIFIED':['Saved Auto state could not be verified. Stop Auto, review the settings, then try again.','Не удалось проверить сохранённое состояние Auto. Остановите Auto, проверьте настройки и повторите попытку.'],
  'STOP-SUPERSEDED-START':['Stop cancelled this pending Start. Press Start again when ready.','Остановка отменила ожидающий запуск. При необходимости нажмите «Запустить» снова.'],
  'START-CONFIG-CHANGED':['Settings changed while checking. Review them and try Start again.','Настройки изменились во время проверки. Проверьте их и повторите запуск.'],
  "LAN-TRIAL-REQUIRED":["This selected client-confirmed mode requires its matching LAN trial. Prepared continuous router-probed mode does not use this certificate.", "Выбранному клиентскому режиму нужен соответствующий LAN-тест. Подготовленный непрерывный router-probed режим этот сертификат не использует."],
  "BOUNDED-DEADLINE-REQUIRED":["A bounded window is missing/expired for the selected trial. Verify actual recovery and time before a new authorized run.", "Для выбранного теста нет действующего ограниченного окна. До нового разрешённого запуска проверьте фактическое восстановление и время."],
  'SESSION-LOSS-NOT-ACCEPTED':['Confirm in Settings that a short reconnection of calls and sessions is acceptable.','Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим.'],
  'TRANSACTION-IN-PROGRESS':['A switch is already in progress. Wait for it to finish or press Stop.','Переключение уже идёт. Дождитесь окончания или нажмите «Стоп».'],
  "TRIAL-ATTEMPT-LIMIT":["The trial attempt budget is exhausted. Preserve failures and respect the budget/cooldown; never reset a nonce or ledger to bypass it.", "Бюджет попыток теста исчерпан. Сохраните отказы и соблюдайте бюджет/паузу; не сбрасывайте nonce или журнал ради обхода."],
  'UNSUPPORTED-BOARD':['Native switching requires a verified GL-MT6000 or GL-MT3000 firmware profile. Choosing a model does not bypass these checks.','Нативное переключение требует проверенного профиля прошивки GL-MT6000 или GL-MT3000. Выбор модели не отменяет эти проверки.'],
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
  "POLICY-ORDER-DIRECTION-UNVERIFIED":["Policy-order direction has not been established for this mode. The client-confirmed helper and prepared continuous workflow have different setup evidence.", "Направление политики для этого режима ещё не установлено. У клиентского помощника и подготовленного непрерывного режима разные данные настройки."],
  'LAN-LAYOUT-UNSUPPORTED':['The LAN is not on the standard br-lan bridge.','Локальная сеть не на стандартном мосту br-lan.'],
  'PROFILE-NOT-MONITORED':['Enable monitoring for both chosen profiles in Settings.','Включите наблюдение для обоих выбранных профилей в настройках.'],
  'NFT-GUARD-UNAVAILABLE':['The router firewall tool (nft) is unavailable.','Недоступен инструмент firewall роутера (nft).'],
  'POLICY-READ-FAILED':['The router VPN policy could not be read.','Не удалось прочитать VPN-политику роутера.'],
  'UPLINK-LINK-DOWN':['The internet cable/uplink is down; changing VPN would not help.','Нет связи с интернет-провайдером; смена VPN не поможет.'],
  "LEASE-INTEGRITY-FAILED":["The bounded lease record failed integrity checks. Preserve it and inspect recovery/storage; do not delete it or create another lease as a bypass.", "Запись ограниченного окна не прошла целостность. Сохраните её и проверьте восстановление/хранилище; не удаляйте и не создавайте другое окно как обход."],
  'LEASE-STORAGE-FAILED':['The test window could not be stored on the router.','Не удалось сохранить окно теста на роутере.'],
  'LEGACY-LEASE-RECOVERY':['An old transaction needs recovery; wait or press Stop.','Старая транзакция требует восстановления; подождите или нажмите «Стоп».'],
  'JOURNAL-INTEGRITY-FAILED':['The transaction journal is damaged. Switching is blocked and LAN traffic may be held; see the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций повреждён. Переключение заблокировано, трафик LAN может удерживаться; см. аварийные шаги в router-test-kit/EMERGENCY.md.'],
  'HISTORY-001':['The history file is damaged or the router clock went backwards.','Файл истории повреждён или часы роутера пошли назад.'],
  'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':['The router VPN policy was changed by someone else during a switch; LAN traffic is held. Check the rule order and see router-test-kit/EMERGENCY.md.','Политику VPN роутера изменили во время переключения; трафик LAN удерживается. Проверьте порядок правил, см. router-test-kit/EMERGENCY.md.'],
  'ROLLBACK-UNVERIFIED-GUARD-RETAINED':['The rollback could not be verified; LAN traffic is held. See router-test-kit/EMERGENCY.md.','Откат не удалось подтвердить; трафик LAN удерживается. См. router-test-kit/EMERGENCY.md.'],
  "CLIENT-CONFIRMATION-TIMEOUT":["Required client confirmation did not arrive in time. Recovery was requested; verify whether the original route returned or reserve was retained.", "Нужное подтверждение клиента не пришло вовремя. Восстановление запрошено; проверьте, вернулся ли исходный маршрут или сохранён резерв."],
  'CLIENT-STOP':['Stopped by request.','Остановлено по запросу.'],
  'TARGET-HTTPS-DNS-FAILED':['The reserve did not pass the DNS/HTTPS check.','Резерв не прошёл проверку DNS/HTTPS.'],
  'LAN-BASELINE-NOT-SOURCE':['The LAN computer is not currently using the primary route.','Компьютер в LAN сейчас не использует основной маршрут.'],
  'RESERVE-EXIT-NOT-DISTINCT':['Primary and reserve have the same external IP; the switch could not be proven.','У основного и резервного одинаковый внешний IP; переключение невозможно доказать.'],
  'VENDOR-APPLY-FAILED':['The router failed to apply the change; it was rolled back.','Роутер не смог применить изменение; выполнен откат.'],
  'POLICY-CHANGED-DURING-APPLY':['The policy changed while switching; it was rolled back.','Политика изменилась во время переключения; выполнен откат.'],
  'NATIVE-SYSTEM-001':['Internal controller error. See the Service monitor.','Внутренняя ошибка контроллера. См. «Службу мониторинга».'],
  'TERMS-NOT-ACCEPTED':['The terms of use are not accepted yet. Open this page in LuCI and accept them on the first screen.','Условия использования ещё не приняты. Откройте эту страницу в LuCI и примите их на первом экране.'],
  'RETURN-NOT-APPLICABLE':['There is nothing to return from: Auto is not holding the reserve.','Возвращаться не откуда: Auto не удерживает резерв.'],
  'SOURCE-NOT-HEALTHY':['The primary does not pass its check right now, so the router stays on the reserve. Try again when the primary works.','Основной VPN сейчас не проходит проверку, роутер остаётся на резерве. Повторите, когда основной заработает.'],
  'JOURNAL-UNVERIFIED':['The transaction journal could not be verified. Use the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций не удалось проверить. Используйте аварийные шаги из router-test-kit/EMERGENCY.md.'],
  'EXTERNAL-POLICY-CHANGE':['The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.','Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.'],
  'EXTERNAL-POLICY-CHANGE-RELEASED':['The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.','Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.'],
  'ROLLBACK-UNVERIFIED':['The return to the previous route could not be verified. Traffic is allowed only through VPN tunnels; check the VPN rule order in GL.iNet.','Возврат на прежний маршрут не удалось подтвердить. Трафик разрешён только через VPN-туннели; проверьте порядок правил VPN в GL.iNet.'],
  'ENVIRONMENT-EVIDENCE-UNAVAILABLE':['The router has not yet reported what it is made of (model, firmware, installed tools). Monitoring starts by itself: wait a minute and reload the page.','Роутер ещё не сообщил, из чего он состоит (модель, прошивка, установленные программы). Мониторинг запускается сам: подождите минуту и обновите страницу.'],
  'MONITOR-EVIDENCE-STALE':['There is no fresh data from the monitor. Monitoring starts by itself; wait a minute and reload. If it stays, see Help → “The page is old, empty or says the monitor is not running”.','Нет свежих данных от мониторинга. Запустите его в блок «Мониторинг» на «Обзоре»; без него Auto использовать нельзя.'],
  'NATIVE-START-CERTIFICATION-REQUIRED':['Nothing blocks you here, but the router itself still checks everything again at the moment you press Start (current device, time window, your computer’s confirmation, safe return).','Здесь ничто не мешает, но роутер всё равно перепроверит всё в момент нажатия «Старт» (текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат).'],
  'OPERATOR-RETURN':['Returned to the primary on your request.','Возврат на основной выполнен по вашему запросу.'],
  'PRIMARY-RECOVERED':['The primary recovered and Auto returned to it.','Основной восстановился, Auto вернулся на него.']
};
function autoBlockerText(code){
  var row=Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?AUTO_BLOCKERS[code]:null;
  var guide=typeof AUTO_REMEDIES!=='undefined'&&AUTO_REMEDIES[autoRemedyKey(code)];
  if(!row&&!/^[A-Z][A-Z0-9-]{1,95}$/.test(String(code)))return bi('Unrecognised controller code; see the Service monitor.','Неизвестный код контроллера; см. «Службу мониторинга».');
  var table=!row&&!guide&&typeof ERROR_ROWS!=='undefined'?ERROR_ROWS.filter(function(r){return r[0]===code;})[0]:null;
  return row?bi(row[0],row[1]):guide?bi(guide.title[0],guide.title[1]):table?bi(table[2],table[3]):bi('Code '+code+': see its row in Events and errors.','Код '+code+': описание в «События и ошибки».');
}
var AUTO_REMEDIES={
  'acceleration':{
    title:['Disable network acceleration','Отключите сетевое ускорение'],path:['GL.iNet → NETWORK → Network Acceleration','GL.iNet → Сеть → Сетевое ускорение (Network Acceleration)'],
    text:['Turn Enable off and click Apply. Selecting Auto, Hardware or Software mode does not disable acceleration. Return here and check readiness again; Auto VPN needs a separate Start. Older firmware calls this menu Hardware Acceleration.','Выключите переключатель Enable («Включить») и нажмите Apply («Применить»). Выбор режима Auto, Hardware или Software не отключает ускорение. Вернитесь сюда и обновите готовность; Auto VPN запускается отдельно. В старых прошивках пункт называется Hardware Acceleration.'],
    route:'/#/netnat',docs:'https://docs.gl-inet.com/router/en/4/interface_guide/network_acceleration/'},
  'offload':{
    title:['Disable firewall flow offloading','Отключите flow offloading в firewall'],path:['LuCI → Network → Firewall → General Settings → Routing/NAT Offloading','LuCI → Сеть → Межсетевой экран → Общие настройки → Routing/NAT Offloading'],
    text:['Clear Software flow offloading and Hardware flow offloading, then Save & Apply. Return here and check readiness again.','Снимите Software flow offloading и Hardware flow offloading, затем нажмите Save & Apply («Сохранить и применить»). Вернитесь сюда и обновите готовность.'],route:'/cgi-bin/luci/admin/network/firewall'},
  'pair':{
    title:['Review the current VPN pair','Проверьте текущую пару VPN'],path:['Advanced menu → Settings → Primary and reserve VPN','Расширенное меню → Настройки → Основной и резервный VPN'],
    text:['The selected channel was removed, rebound or is not supported by this controller. Review the actual tunnel bindings in GL.iNet → VPN → VPN Dashboard, then explicitly save a supported pair here. On the prepared MT3000 mode these are wgclient1 and ovpnclient1; a server catalogue entry is not a second tunnel.','Выбранный канал удалён, перепривязан или не поддерживается этим контроллером. Проверьте привязки в GL.iNet → VPN → VPN Dashboard, затем явно сохраните здесь поддерживаемую пару. Для подготовленного режима MT3000 это wgclient1 и ovpnclient1; запись каталога серверов не является вторым туннелем.'],route:'#settings'},
  'recovery':{
    title:['Settings were changed outside the app','Настройки изменены вне приложения'],path:['Overview → Auto button','Обзор → кнопка Auto'],
    text:['The router settings no longer match the saved Auto session, for example a tunnel was renamed or reordered in the stock page. Auto keeps your changes: when you press Start it archives the old session and adopts the new settings by itself, nothing has to be reconciled by hand. If it refuses again within 15 minutes, the settings are still changing: finish editing and press Start once more.','Настройки роутера отличаются от сохранённой сессии Auto, например в штатной панели переименовали или переставили туннель. Auto сохраняет ваши изменения: при нажатии Start он сам архивирует старую сессию и принимает новые настройки, вручную ничего согласовывать не нужно. Если в течение 15 минут отказ повторяется, настройки ещё меняются: закончите правки и нажмите Start ещё раз.'],route:'#settings'}
};
AUTO_REMEDIES.preparation={title:['Complete router preparation','Завершите подготовку роутера'],path:['System readiness → Persistent router preparation','Готовность системы → Постоянная подготовка роутера'],text:['Open the preparation table, find the failed row and follow its instructions. A failed boot or runtime check remains separate from the hardware acceleration switch.','Откройте таблицу подготовки, найдите непрошедший пункт и выполните его инструкцию. Ошибки автозапуска и работающих модулей проверяются отдельно от переключателя аппаратного ускорения.'],route:'#readiness'};
['wgclient1','ovpnclient1'].forEach(function(name){AUTO_REMEDIES['autostart-'+name]={title:['Review '+name+' startup','Проверьте автозапуск '+name],path:['LuCI → Network → Interfaces → '+name+' → Edit → General Setup','LuCI → Сеть → Интерфейсы → '+name+' → Изменить → Основные настройки'],text:['After stopping Auto and verifying completed recovery, clear Bring up on boot for this interface, then Save & Apply. Auto manages its startup separately. This is a startup check, not a hardware acceleration failure.','После остановки Auto и подтверждённого завершения восстановления снимите Bring up on boot («Поднимать при загрузке») у этого интерфейса, затем Save & Apply («Сохранить и применить»). Auto управляет запуском отдельно. Это проверка автозапуска, а не ошибка аппаратного ускорения.'],route:'/cgi-bin/luci/admin/network/network'};});
AUTO_REMEDIES.stockboot={title:['Disable competing VPN startup','Отключите конкурирующий автозапуск VPN'],path:['LuCI → System → Startup → vpn-client','LuCI → Система → Автозагрузка → vpn-client'],text:['After stopping Auto and verifying completed recovery, use Disable for vpn-client in the startup list. Disable changes startup; Stop is a different action and disconnects the running service. Return here and check preparation again.','После остановки Auto и подтверждённого завершения восстановления нажмите Disable («Отключить») у vpn-client в списке автозапуска. Это отключает запуск при загрузке. Кнопка Stop («Остановить») выполняет другое действие и останавливает работающую службу. Вернитесь сюда и повторите проверку подготовки.'],route:'/cgi-bin/luci/admin/system/startup'};
function autoRemedyKey(code){
  if(code==='PREP-SOURCE-AUTOSTART')return 'sourceboot';
  if(code==='PREP-TARGET-AUTOSTART')return 'targetboot';
  if(code==='PREPARATION-RESTART-REQUIRED')return 'restart';
  if(/^PREPARATION-/.test(code||''))return 'preparation';
  if(code==='PREP-WGCLIENT1-AUTOSTART')return 'autostart-wgclient1';
  if(code==='PREP-OVPNCLIENT1-AUTOSTART')return 'autostart-ovpnclient1';
  if(code==='PREP-STOCK-VPN-BOOT')return 'stockboot';
  if(['HARDWARE-ACCELERATOR-UNVERIFIED','SOFTWARE-ACCELERATOR-UNVERIFIED','PREP-HNAT-CONFIG','PREP-SFE-BOOT','PREP-SFE-AUTOLOAD','PREP-SFE-RUNTIME'].indexOf(code)>=0)return 'acceleration';
  if(code==='FLOW-OFFLOAD-ENABLED')return 'offload';
  if(code==='PAIR-PREPARATION-REQUIRED'||/^PREP-/.test(code||''))return 'preparation';
  if(['SOURCE-RESERVE-NOT-CONFIGURED','VENDOR-IDENTITY-UNKNOWN','PROFILE-IDENTITY-CHANGED','RESERVE-NOT-CONNECTED','EXISTING-TUNNEL-BINDING-UNVERIFIED','PAIR-PROFILES-UNVERIFIED'].indexOf(code)>=0)return 'pair';
  if(/^PAIR-(EXTERNAL-|RECOVERY-REQUIRED|STATE-UNVERIFIED)/.test(code||''))return 'recovery';
  return null;
}
function autoRemedyHref(guide){
  if(guide.route==='/#/netnat'){
    var loc=typeof window!=='undefined'&&window.location;
    return loc&&loc.hostname?(loc.protocol==='https:'?'https:':'http:')+'//'+loc.hostname+guide.route:guide.docs;
  }
  return guide.route;
}
function renderAutoRemedy(code){
  var g=AUTO_REMEDIES[autoRemedyKey(code)];if(!g)return null;
  var nodes=[E('strong',{},bi(g.title[0],g.title[1])),E('p',{},bi(g.path[0],g.path[1])),E('p',{},bi(g.text[0],g.text[1])),E('a',{'href':autoRemedyHref(g),'class':'cbi-button','target':g.route.charAt(0)==='#'?null:'_blank','rel':'noopener noreferrer','click':function(event){if(g.route.charAt(0)==='#'&&typeof minimumNavigate==='function'&&minimumNavigate){event.preventDefault();minimumNavigate(g.route.slice(1));}}},bi('Open settings','Открыть настройки'))];
  if(g.docs)nodes.push(E('p',{},E('a',{'href':g.docs,'target':'_blank','rel':'noopener noreferrer'},bi('GL.iNet instructions','Инструкция GL.iNet'))));
  if(typeof renderPreparationButtons==='function'){var preparationButtons=renderPreparationButtons(code);if(preparationButtons)nodes.splice(1,0,preparationButtons);}
  if(autoRemedyKey(code)==='acceleration')nodes.push(E('p',{},bi('If it is already off but the check still fails, open System readiness → Persistent router preparation for the exact failed check. Saved configuration and loaded runtime acceleration are checked separately.','Если уже выключено, а ошибка остаётся, откройте «Готовность системы → Постоянная подготовка роутера»: там указан конкретный непрошедший пункт. Сохранённые настройки и фактически работающее ускорение проверяются отдельно.')));
  return E('div',{'class':'hv-chart-card hv-auto-remedy','data-auto-remedy':code},nodes);
}
['PAIR-EXTERNAL-POLICY-CHANGE','PAIR-EXTERNAL-NETWORK-CHANGE','PAIR-EXTERNAL-CONFIG-CHANGE','PAIR-RECOVERY-REQUIRED','PAIR-STATE-UNVERIFIED','PAIR-PROFILES-UNVERIFIED','EXISTING-TUNNEL-BINDING-UNVERIFIED','PAIR-PREPARATION-REQUIRED','PREP-HNAT-CONFIG','PREP-WGCLIENT1-AUTOSTART','PREP-OVPNCLIENT1-AUTOSTART','PREP-STOCK-VPN-BOOT','PREP-SFE-BOOT','PREP-SFE-AUTOLOAD','PREP-SFE-RUNTIME'].forEach(function(code){
  if(!Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)){var guide=AUTO_REMEDIES[autoRemedyKey(code)];AUTO_BLOCKERS[code]=guide.title.slice();}
});
AUTO_REMEDIES.restart={title:['Router restart required','Нужна перезагрузка роутера'],path:['LuCI → System → Reboot','LuCI → Система → Перезагрузка'],text:['The boot/acceleration setting is saved and verified. Restart this router deliberately, then wait for fresh preparation checks before a separate Auto Start. The preparation button never reboots the router itself.','Настройка автозапуска/ускорения сохранена и проверена. Отдельно перезагрузите этот роутер, дождитесь новых проверок подготовки и затем явно запустите Auto. Кнопка подготовки сама роутер не перезагружает.'],route:'/cgi-bin/luci/admin/system/reboot'};
AUTO_BLOCKERS['PREPARATION-RESTART-REQUIRED']=AUTO_REMEDIES.restart.title.slice();
AUTO_BLOCKERS['PREPARATION-RECOVERY-REQUIRED']=AUTO_REMEDIES.recovery.title.slice();
['source','target'].forEach(function(role){
 var primary=role==='source',key=primary?'sourceboot':'targetboot';
 AUTO_REMEDIES[key]={title:primary?['Disable primary VPN boot startup','Отключите автозапуск основного VPN']:['Disable reserve VPN boot startup','Отключите автозапуск резервного VPN'],path:['LuCI → Network → Interfaces → selected '+(primary?'primary':'reserve')+' VPN → Edit → General Setup','LuCI → Сеть → Интерфейсы → выбранный '+(primary?'основной':'резервный')+' VPN → Изменить → Основные настройки'],text:['Disable Bring up on boot for the selected client. Auto manages startup separately; the current connection is preserved.','Выключите «Поднимать при загрузке» для выбранного клиента. Auto управляет запуском отдельно; текущее подключение сохраняется.'],route:'/cgi-bin/luci/admin/network/network'};
 AUTO_BLOCKERS['PREP-'+role.toUpperCase()+'-AUTOSTART']=AUTO_REMEDIES[key].title.slice();
});
// What must be true before Start can be accepted, in the order the owner can fix it.
var AUTO_LAN_ONLY=['LAN-TRIAL-REQUIRED','BOUNDED-DEADLINE-REQUIRED','SESSION-LOSS-NOT-ACCEPTED'];
function autoReadiness(status,inventory,now){
  var ns=status.native_failover||{},settings=(inventory&&inventory.settings)||{},rows=status.profiles||[];
  var monitorFresh=!status.rpc_error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var controllerFresh=monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  function find(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):find(settings.plan_source),target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):find(settings.plan_target);
  var configured=!!(settings.setup_complete&&source&&target&&source.id!==target.id);
  var bothHealthy=configured&&profileHealth(source,now).state==='healthy'&&profileHealth(target,now).state==='healthy';
  var technical=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  var certified=controllerFresh&&(ns.certified===true||ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE');
  var steps=[
    {key:'monitor',done:monitorFresh,
     title:bi('Monitor is running','Мониторинг работает'),
     hint:bi('The router status is missing or stale. Monitoring starts by itself; wait a minute and reload the page.','Статус роутера отсутствует или устарел. Мониторинг запускается сам: подождите минуту и обновите страницу.')},
    {key:'profiles',done:bothHealthy,
     title:bi('Primary and reserve are chosen and healthy','Основной и резервный профили выбраны и работают'),
     hint:!configured?bi('Choose a primary and a different reserve in Settings → All application settings → 3 · Existing VPNs.','Выберите основной и другой, резервный профиль: «Настройки → Все настройки приложения → 3 · Существующие VPN».'):bi('Both tunnels must be connected and pass the DNS/HTTPS check. Connect them in GL.iNet VPN Dashboard.','Оба туннеля должны быть подключены и проходить проверку DNS/HTTPS. Подключите их в VPN Dashboard GL.iNet.')},
    {key:'session',done:settings.native_session_loss===true,
     title:bi('You accepted a brief call drop when switching','Вы согласились на короткий обрыв звонков при переключении'),
     hint:bi('A switch can interrupt calls and downloads for a few seconds. Confirm this in Settings (System setup).','Переключение может на несколько секунд прервать звонки и загрузки. Подтвердите это в «Настройках» (мастер системы).')},
    {key:'router',done:controllerFresh&&technical.length===0,codes:technical,
     title:bi('Router is ready for switching','Роутер готов к переключению'),
     hint:!controllerFresh?bi('The switching controller is not reporting. Check the Live log (Advanced menu).','Контроллер переключения не отвечает. Проверьте «Живой журнал» (меню «Расширенные настройки»).'):bi('The router reports conditions that block switching (listed below).','Роутер сообщает условия, блокирующие переключение (перечислены ниже).')},
    {key:'trial',done:certified,
     title:bi('LAN trial passed for this pair','LAN-тест для этой пары пройден'),
     hint:bi('On a computer connected by cable run the LAN helper: it briefly switches to the reserve and back and proves DNS, HTTPS and the exit IP from the LAN. Only then Start is accepted.','На компьютере, подключённом кабелем, запустите LAN-помощник: он кратко переключит на резерв и обратно и докажет работу DNS, HTTPS и внешнего IP из LAN. Только после этого «Старт» будет принят.')}
  ];
  var next=steps.filter(function(step){return !step.done;})[0]||null;
  return {steps:steps,next:next,ready:!next};
}

// Traffic light: one lamp says what Auto is doing. The round button only starts or stops it.
var AUTO_LIGHTS=[
  {lamp:'green',key:'ok',icon:'✓',legend:['Green: Auto is on and watching the primary','Зелёный: Auto включён и следит за основным']},
  {lamp:'yellow',key:'switching',icon:'⟳',legend:['Yellow: starting, stopping or switching the route','Жёлтый: запускается, останавливается или переключает маршрут']},
  {lamp:'orange',key:'reserve',icon:'⇄',legend:['Orange: the reserve route is selected; primary health is separate','Оранжевый: выбран резерв; исправность основного показана отдельно']},
  {lamp:'red',key:'problem',icon:'!',legend:['Red: needs your attention','Красный: нужно ваше внимание']}
];
function autoLightModel(status,inventory,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{},intent=status.auto_control||{},state=ns.state;
  var blockers=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  var sessionRuns=intent.requested==='on'&&['RUNNING','HELD'].indexOf(intent.pair_phase)>=0&&!model.awaiting;
  function out(key,title,hint,code,running){return {running:running===true,key:key,lamp:(AUTO_LIGHTS.filter(function(l){return l.key===key;})[0]||{}).lamp||null,
    icon:key==='off'?'○':key==='unknown'?'?':(AUTO_LIGHTS.filter(function(l){return l.key===key;})[0]||{}).icon,title:title,hint:hint,code:code||null};}
  if(model.paused)return out('switching',bi('Auto paused for speed test','Auto на паузе для теста скорости'),bi('Background checks are paused. They resume before Auto; a manual Stop stays in force.','Фоновые проверки приостановлены. Они возобновятся перед Auto; ручной Stop сохраняет силу.'));
  if(!model.fresh)return out('unknown',bi('No data from the router','Нет данных от роутера'),bi('The status is missing or old. Open Settings and make sure the monitor is running.','Статус отсутствует или устарел. Откройте «Настройки» и проверьте, что мониторинг запущен.'));
  if(ns.proof_scope==='router-probed-ipv4'&&ns.mode==='continuous-pair'){
    var scopeHint='';
    if(model.awaiting)return out('switching',bi('Starting or stopping Auto','Запуск или остановка Auto'),scopeHint);
    if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),scopeHint,null,sessionRuns);
    if((model.on||sessionRuns)&&['OBSERVING','COMMITTED','DEGRADED-ON-RESERVE','ROLLED-BACK'].indexOf(state)>=0){
      var route=channelPathSelection(status,now,ns.source,ns.target);
      if(!route.selected)return out('unknown',bi('The traffic channel is not verified','Канал трафика не подтверждён'),bi('Waiting for verified router VPN rules.','Ждём подтверждения действующих правил VPN роутером.'),route.code||'KERNEL-POLICY-UNVERIFIED');
      if(route.selected===ns.target)return out('reserve',bi('Working on the reserve','Работаю на резерве'),scopeHint);
      return out('ok',bi('Two-channel Auto is on','Авторежим двух каналов включён'),scopeHint);
    }
    var failedCode=blockers[0]||(intent.failure&&intent.failure.code&&intent.requested!=='on'?intent.failure.code:null);
    if(model.off&&!failedCode)return out('off',bi('Auto is off','Auto выключен'),scopeHint);
    return out('problem',bi('Auto needs attention','Auto требует внимания'),failedCode?autoBlockerText(failedCode):scopeHint,failedCode);
  }
  if(ns.proof_scope==='router-hosted-ipv4')return out('problem',bi('Checked by the router itself','Проверку делает сам роутер'),bi('This trial checks IPv4 forwarding with a client inside the router. It does not certify traffic from a separate LAN computer.','Этот тест проверяет пересылку IPv4 клиентом внутри роутера. Трафик отдельного компьютера LAN им не подтверждён.'));
  if(model.awaiting)return out('switching',intent.requested==='off'?bi('Stopping Auto','Auto останавливается'):bi('Starting Auto','Auto запускается'),bi('Waiting for the router to confirm. The lamp changes when it does.','Ожидается подтверждение роутера. Лампа изменится, когда оно придёт.'));
  if(state==='RESTORING')return out('switching',bi('Returning to the previous route','Возврат на прежний маршрут'),bi('The router is putting the original route back and checking it.','Роутер возвращает исходный маршрут и проверяет его.'));
  if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),bi('The router is changing the route and waits for a LAN computer to confirm it. This takes up to 90 seconds.','Роутер меняет маршрут и ждёт подтверждения от компьютера в LAN. Это занимает до 90 секунд.'));
  if(state==='OBSERVING'&&ns.certified===true)return out('ok',bi('Auto is on','Auto включён'),bi('Watching the primary. If it fails, the router switches to the reserve after a LAN computer confirms the new route.','Следит за основным. При его отказе роутер переключится на резерв после подтверждения нового маршрута компьютером в LAN.'));
  if(state==='COMMITTED')return out('reserve',bi('Working on the reserve','Работаю на резерве'),bi('The reserve route is selected. Primary health is shown separately; return depends on policy, fresh evidence and operator hold.','Выбран резервный маршрут. Исправность основного показана отдельно; возврат зависит от политики, свежих данных и ручного удержания.'));
  if(state==='DEGRADED-ON-RESERVE')return out('problem',bi('The reserve is failing too','Резерв тоже не работает'),bi('The selected reserve has problems. Check both VPNs; any return must satisfy the current mode, saved policy and fresh primary readiness.','На выбранном резерве есть проблемы. Проверьте оба VPN; возврат должен соответствовать текущему режиму, политике и свежей готовности основного.'));
  if(state==='STOPPED-ON-RESERVE')return out('problem',bi('Stopped, but still on the reserve','Остановлен, но роутер всё ещё на резерве'),bi('The original route is not restored. Press Return to primary when the primary works.','Исходный маршрут не восстановлен. Нажмите «Вернуться на основной», когда основной заработает.'));
  if(state==='RELEASE-PENDING'||blockers.indexOf('GUARD-RELEASE-UNCONFIRMED')>=0)return out('problem',bi('Internet may be blocked: the return has not finished','Интернет может быть заблокирован: возврат не закончился'),bi('Recovery is still pending. See Help → emergency return; Stop has not completed.','Восстановление ещё не завершено. См. «Помощь» → аварийный возврат; остановка не завершена.'),'GUARD-RELEASE-UNCONFIRMED');
  if(state==='BLOCKED'&&intent.requested==='on'&&blockers.length===1&&blockers[0]==='VENDOR-WORKER-BUSY')return out('switching',bi('The router is busy; Auto will continue by itself','Роутер занят, Auto продолжит сам'),bi('A stock network worker or lock is busy. Auto continues after it clears.','Штатный сетевой обработчик или блокировка заняты. Auto продолжит работу после их завершения.'));
  if(state==='BLOCKED'&&intent.requested==='on')return out('problem',bi('Auto is blocked','Auto заблокирован'),blockers.length?autoBlockerText(blockers[0]):bi('The router reports a condition that blocks Auto. See the list below.','Роутер сообщает условие, блокирующее Auto. См. список ниже.'),blockers[0]);
  if(state==='TRIAL-REQUIRED')return out('problem',bi('A LAN trial is required','Нужен LAN-тест'),autoBlockerText('LAN-TRIAL-REQUIRED'),'LAN-TRIAL-REQUIRED');
  if(state==='EXPIRED')return out('off',bi('Auto is off: the test window ended','Auto выключен: окно теста закончилось'),autoBlockerText('BOUNDED-DEADLINE-REQUIRED'));
  if(state==='STOPPED'&&ns.original_restored===true)return out('off',bi('Auto is off','Auto выключен'),bi('Control is back with the router; the original route is verified.','Управление вернулось роутеру; исходный маршрут проверен.'));
  return out('off',bi('Auto is off','Auto выключен'),bi('Monitoring continues; nothing is switched while Auto is off.','Мониторинг продолжается; пока Auto выключен, ничего не переключается.'));
}
// The card's lamp has two states only: green = automatic switching is working (watching, switching or holding the
// reserve), red = it is not (off, blocked, needs attention or no fresh data). The detailed state stays in the text.
function autoWorking(light){return !!light&&(light.key==='ok'||light.key==='reserve'||light.key==='switching'&&light.running===true);}
function renderAutoLight(light,technicalCode){
  var working=autoWorking(light);
  var lamps=[E('span',{'class':'hv-lamp hv-lamp-red'+(working?'':' hv-lamp-lit'),'aria-hidden':'true'}),E('span',{'class':'hv-lamp hv-lamp-green'+(working?' hv-lamp-lit':''),'aria-hidden':'true'})];
  var housing=E('div',{'class':'hv-light hv-light-two hv-light-'+(working?'on':'off'),'role':'img','aria-label':working?bi('Automatic switching works','Автопереключение работает'):bi('Automatic switching does not work','Автопереключение не работает')},lamps);
  var legend=E('ul',{'class':'hv-light-legend','aria-label':bi('What the lamps mean','Что означают лампы')},[
    E('li',{'class':working?'hv-legend-current':''},[E('span',{'class':'hv-dot hv-dot-green','aria-hidden':'true'}),bi('Green: automatic switching works. It watches the primary and moves traffic to the reserve if the primary fails.','Зелёный: автопереключение работает. Оно следит за основным и при его отказе переводит трафик на резерв.')]),
    E('li',{'class':working?'':'hv-legend-current'},[E('span',{'class':'hv-dot hv-dot-red','aria-hidden':'true'}),bi('Red: automatic switching does not work: it is off, blocked, needs your attention, or the router sends no fresh data. Traffic then stays where it is.','Красный: автопереключение не работает: выключено, заблокировано, требует внимания или роутер не присылает свежих данных. Трафик тогда остаётся там, где есть.')]),
    E('li',{},[E('span',{'class':'hv-dot hv-dot-green','aria-hidden':'true'}),' / ',E('span',{'class':'hv-dot hv-dot-red','aria-hidden':'true'}),bi(' Primary and Reserve: green works in Auto, yellow: Alive; you can switch to it manually, grey is waiting for the router answer, red is an error.',' Основной и Резерв: зелёный — работает в автомате, жёлтый — Живой, можно переключиться на него вручную, серый — ждём ответа роутера, красный — ошибка.')])]);
  return E('div',{'class':'hv-light-block'},[housing,E('div',{'class':'hv-light-text'},[E('strong',{'class':'hv-auto-label hv-light-title'},[E('span',{'class':'hv-light-icon','aria-hidden':'true'},light.icon+' '),light.title]),E('p',autoHintLive(light.hint),light.hint),E('small',{'class':'hv-auto-tech'},[bi('Technical state: ','Техническое состояние: ')+technicalCode,light.code&&typeof errorCodeLink==='function'?' · ':null,light.code&&typeof errorCodeLink==='function'?errorCodeLink(light.code):null].filter(Boolean)),E('details',{'class':'hv-light-help'},[E('summary',{},bi('What do the colours mean?','Что означают цвета?')),legend])])]);
}

// Reply of the Auto button: the code of the answer is shown as a link to its row in the error table, with its short meaning.
function autoCodeNotice(code,extra){
  var row=(typeof ERROR_ROWS!=='undefined'?ERROR_ROWS:[]).filter(function(r){return r[0]===code;})[0];
  return E('div',{},[E('p',{},[errorCodeLink(code),row?' · '+bi(row[2],row[3]):' · '+autoBlockerText(code),extra?' · '+extra:'']),renderAutoRemedy(code)].filter(Boolean));
}
var AUTO_FAILURE_SHOWN=null;
/* A rebuilt live region is read again by screen readers; only a changed hint is marked live. */
var AUTO_HINT_LAST=null;
function autoHintLive(text){var changed=text!==AUTO_HINT_LAST;AUTO_HINT_LAST=text;return changed?{'role':'status','aria-live':'polite'}:{'aria-live':'off'};}
function autoShowError(title,node){
  if(typeof ui!=='undefined'&&ui&&typeof ui.showModal==='function')ui.showModal(title,[node,E('div',{'class':'right'},E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть')))]);
  else if(typeof ui!=='undefined'&&ui&&typeof ui.addNotification==='function')ui.addNotification(null,node);
}
var autoRequestBusy=false,autoStopBusy=false,autoStartPending=false;
var autoCommandPending=null,autoControlRefresh=function(){};
/* Countdown on the Auto button: the expected time is the median of the last measured starts/stops in this browser. */
var AUTO_COUNTDOWN=null,AUTO_COUNTDOWN_TIMER=null,AUTO_COUNTDOWN_NODES=null,AUTO_DURATION_KEY='hv-auto-durations';
function autoDurations(){try{var v=JSON.parse(window.localStorage.getItem(AUTO_DURATION_KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(error){return {};}}
function autoDurationEstimate(kind){
  var rows=(autoDurations()[kind]||[]).filter(function(n){return Number.isFinite(n)&&n>0&&n<600;}).sort(function(a,b){return a-b;});
  if(!rows.length)return kind==='stop'?10:30;
  var mid=Math.floor(rows.length/2),median=rows.length%2?rows[mid]:(rows[mid-1]+rows[mid])/2;
  return Math.max(3,Math.ceil(median));
}
function autoDurationRecord(kind,seconds){
  if(!(Number.isFinite(seconds)&&seconds>0&&seconds<600))return;
  var all=autoDurations();all[kind]=(Array.isArray(all[kind])?all[kind]:[]).concat([Math.round(seconds*10)/10]).slice(-5);
  try{window.localStorage.setItem(AUTO_DURATION_KEY,JSON.stringify(all));}catch(error){}
}
function autoCountdownText(){
  if(!AUTO_COUNTDOWN)return '';
  var left=AUTO_COUNTDOWN.estimate-(Date.now()-AUTO_COUNTDOWN.t0)/1000;
  return left>0?Math.ceil(left)+bi(' s',' с'):'+'+Math.floor(-left)+bi(' s',' с');
}
function autoCountdownTick(){
  var n=AUTO_COUNTDOWN_NODES;if(!n)return;
  function hide(on){if(on){if(n.root.setAttribute)n.root.setAttribute('hidden','');}else if(n.root.removeAttribute)n.root.removeAttribute('hidden');}
  if(!AUTO_COUNTDOWN){hide(true);return;}
  var left=AUTO_COUNTDOWN.estimate-(Date.now()-AUTO_COUNTDOWN.t0)/1000,part=Math.max(0,Math.min(1,left/AUTO_COUNTDOWN.estimate));
  hide(false);n.text.textContent=autoCountdownText();
  if(n.root.style&&n.root.style.setProperty)n.root.style.setProperty('--hv-countdown',String(part));
  if(n.root.classList&&n.root.classList.toggle)n.root.classList.toggle('hv-auto-countdown-over',left<=0);
}
function autoCountdownBegin(kind){
  if(AUTO_COUNTDOWN&&AUTO_COUNTDOWN.kind===kind)return;
  AUTO_COUNTDOWN={kind:kind,t0:Date.now(),estimate:autoDurationEstimate(kind)};
  if(!AUTO_COUNTDOWN_TIMER&&typeof setInterval==='function')AUTO_COUNTDOWN_TIMER=setInterval(autoCountdownTick,250);
  autoCountdownTick();
}
function autoCountdownEnd(success){
  if(!AUTO_COUNTDOWN)return;
  if(success)autoDurationRecord(AUTO_COUNTDOWN.kind,(Date.now()-AUTO_COUNTDOWN.t0)/1000);
  AUTO_COUNTDOWN=null;if(AUTO_COUNTDOWN_TIMER&&typeof clearInterval==='function'){clearInterval(AUTO_COUNTDOWN_TIMER);AUTO_COUNTDOWN_TIMER=null;}
  autoCountdownTick();
}
function autoCommandOperation(status,now){
  var model=autoControlModel(status,now),intent=status.auto_control||{},phase=intent.pair_phase;
  var failedStart=model.fresh&&(status.native_failover||{}).state==='BLOCKED'&&!model.awaiting&&!model.on&&!model.transitioning;
  if(autoCommandPending&&autoCommandPending.acknowledged&&model.fresh&&intent.requested_at>autoCommandPending.baseline){
    var terminal=['FAILED','STOPPED','HELD'].indexOf(phase)>=0||!autoCommandPending.stop&&failedStart;
    var done=autoCommandPending.stop?terminal:terminal||phase==='RUNNING'&&model.on&&!model.awaiting&&!model.transitioning;
    var legacyDone=!phase&&!model.awaiting&&!model.transitioning&&
      (autoCommandPending.stop?model.off:model.on||model.off||model.color==='error');
    if(done||legacyDone)autoCommandPending=null;
  }
  if(autoCommandPending&&Number.isFinite(autoCommandPending.t0)&&Date.now()-autoCommandPending.t0>Math.max(120000,2000*autoDurationEstimate(autoCommandPending.stop?'stop':'start'))){
    autoCommandPending=null;
    if(typeof ui!=='undefined'&&ui&&typeof ui.addNotification==='function')ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNCONFIRMED'));
  }
  if(autoCommandPending)return autoCommandPending.stop?'stopping':'starting';
  if(phase==='STARTING')return failedStart?null:'starting';
  if(phase==='STOPPING')return 'stopping';
  if(phase==='UNKNOWN')return 'unknown';
  if(model.awaiting)return intent.requested==='off'?'stopping':'starting';
  if(model.transitioning)return intent.requested==='off'?'stopping':['RUNNING','HELD'].indexOf(phase)>=0?null:'starting';
  return null;
}
function renderAutoPowerControl(status,inventory){
  var ns=status.native_failover||{},intent=status.auto_control||{},model=autoControlModel(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  var light=autoLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),controlRevision=intent.control_revision;
  var monitorReady=typeof monitorLightModel!=='function'||monitorLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000),false).key==='ok';
  var actionLabel=E('span',{'class':'hv-auto-action'},'');
  var countdownText=E('span',{'class':'hv-auto-countdown-text'},''),countdown=E('span',{'class':'hv-auto-countdown','aria-hidden':'true','hidden':''},[E('span',{'class':'hv-auto-countdown-ring'}),countdownText]);
  var countdownNodes={root:countdown,text:countdownText};
  function currentControl(){
    var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
    model=autoControlModel(status,now);
    monitorReady=typeof monitorLightModel!=='function'||monitorLightModel(status,inventory,now,false).key==='ok';
  }
  function syncButton(){
    currentControl();
    var operation=autoCommandOperation(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),stop=model.stop||autoStartPending||operation==='starting'||!model.fresh;
    button.disabled=!!(autoStopBusy||operation==='stopping'||!stop&&(operation||autoRequestBusy||inventory.error||!model.fresh||!monitorReady));
    if(button.classList&&button.classList.toggle){button.classList.toggle('hv-auto-stop-requested',operation==='stopping');
      // The button shows "on" only when Auto is confirmed working and no command is still pending.
      var confirmedOn=!operation&&autoWorking(autoLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)));
      button.classList.toggle('hv-auto-lit-on',confirmedOn);button.classList.toggle('hv-auto-lit-off',!confirmedOn);}
    AUTO_COUNTDOWN_NODES=countdownNodes;
    if(operation==='starting'||operation==='stopping')autoCountdownBegin(operation==='starting'?'start':'stop');
    else if(AUTO_COUNTDOWN){var nowOn=autoWorking(autoLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)));autoCountdownEnd(AUTO_COUNTDOWN.kind==='start'?nowOn:!nowOn);}
    button.setAttribute('data-auto-operation',operation||'idle');
    var label=operation==='starting'?bi('Turning Auto on…','Включение Auto…'):operation==='stopping'?bi('Turning Auto off…','Выключение Auto…'):operation==='unknown'?bi('Awaiting controller state…','Ожидание состояния контроллера…'):stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим');
    button.setAttribute('aria-label',label);button.setAttribute('aria-busy',operation?'true':'false');
    actionLabel.textContent=operation?label+(AUTO_COUNTDOWN?' '+bi('about ','примерно ')+autoDurationEstimate(AUTO_COUNTDOWN.kind)+bi(' s',' с'):''):stop?bi('Press to turn Auto off','Нажмите, чтобы выключить Auto'):bi('Press to turn Auto on','Нажмите, чтобы включить Auto');
  }
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-neutral'+(autoWorking(light)?' hv-auto-lit-on':' hv-auto-lit-off')+(model.stop?' hv-auto-armed':''),'aria-label':model.stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим'),'aria-pressed':model.on?'true':'false','disabled':(model.stop?autoStopBusy:autoRequestBusy||autoStopBusy||(inventory.error||!model.fresh))?'':null,'click':function(){
    currentControl();
    var operation=autoCommandOperation(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),stop=model.stop||autoStartPending||operation==='starting'||!model.fresh;if(autoStopBusy||operation==='stopping'||!stop&&(operation||autoRequestBusy||!monitorReady))return;
    if(!stop&&(typeof controlRevision!=='string'||!/^[0-9a-f]{32}$/.test(controlRevision))){ui.addNotification(null,autoCodeNotice('CONTROL-REVISION-STALE'));window.location.reload();return;}
    autoCommandPending={stop:stop,baseline:intent.requested_at||0,acknowledged:false,t0:Date.now()};autoCountdownBegin(stop?'stop':'start');
    if(stop)autoStopBusy=true;else{autoRequestBusy=true;autoStartPending=true;}autoControlRefresh();
    var call=rpc.declare({object:'homensai-vpn',reject:true,method:stop?'native_stop':'native_start',params:stop?['request_source']:['control_revision','request_source'],expect:{}});
    return (stop?call('manual'):call(controlRevision,'manual')).then(function(result){
      if(autoCommandPending&&autoCommandPending.stop===stop){if(autoRequestAcknowledged(result,stop))autoCommandPending.acknowledged=true;else autoCommandPending=null;}
      if(!stop&&result&&result.accepted===false&&(result.code==='CONTROL-REVISION-STALE'||Array.isArray(result.blockers)&&result.blockers.indexOf('CONTROL-REVISION-STALE')>=0)){ui.addNotification(null,autoCodeNotice('CONTROL-REVISION-STALE'));window.location.reload();return;}
      if(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9-]{2,95}$/.test(result.code)&&(result.accepted===false||result.queued===false))ui.addNotification(null,autoCodeNotice(result.code,result.settings_unverified?bi('router settings could not be read','настройки роутера не прочитаны'):''));
      else if(result&&result.accepted===false){autoShowError(bi('Auto did not start','Auto не запустился'),E('div',{},[autoCodeNotice('AUTO-START-REFUSED'),E('ul',{},(result.blockers||[]).map(function(code){return E('li',{},[code+' · '+autoBlockerText(code),renderAutoRemedy(code)].filter(Boolean));}))]));}
      else if(!autoRequestAcknowledged(result,stop))ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
    }).catch(function(){if(autoCommandPending&&autoCommandPending.stop===stop){if(stop)autoCommandPending=null;else autoCommandPending.acknowledged=true;}ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){if(stop)autoStopBusy=false;else{autoRequestBusy=false;autoStartPending=false;}autoControlRefresh();});
  }},[E('span',{'class':'hv-power-symbol','aria-hidden':'true'}),countdown]);
  autoControlRefresh=syncButton;syncButton();
  return {button:button,actionLabel:actionLabel,model:model,light:light};
}
function renderAutoControl(status,inventory,refresh){
  var power=renderAutoPowerControl(status,inventory),button=power.button,actionLabel=power.actionLabel,model=power.model,light=power.light;
  var ns=status.native_failover||{},intent=status.auto_control||{};
  var rows=status.profiles||[],settings=inventory.settings||{};
  function profile(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',(typeof statusNow==='function'?statusNow(status):Date.now()/1000),ns.source):profile(ns.source||settings.plan_source),target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',(typeof statusNow==='function'?statusNow(status):Date.now()/1000),ns.target):profile(ns.target||settings.plan_target);
  var path=typeof manualConfirmedPath==='function'?manualConfirmedPath(status,source,target,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)):autoPathModel(status,source,target,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  var pathLabels={neutral:bi('No recent check','Нет свежей проверки'),healthy:bi('Carries your traffic','Пропускает ваш трафик'),ready:bi('Ready for automatic mode','Готов к работе в автомате'),inactive:bi('Not connected','Не подключён'),failed:bi('Not working','Не работает'),checking:bi('Checking…','Идёт проверка…')};
  // Channel selection is separate from probe health: an idle healthy reserve is not a failure.
  function nodeTone(p,key){
    if(typeof manualChannelTone==='function')return manualChannelTone(p,key,path,(typeof statusNow==='function'?statusNow(status):Date.now()/1000),autoWorking(light));
    return {color:'grey',text:bi('No recent check','Нет свежей проверки'),carrier:false};
  }
  function box(p,label,key){var state=path[key],tone=nodeTone(p,key);var attributes={'class':'hv-auto-node hv-node-two hv-node-'+tone.color+(tone.carrier?' hv-node-carrier':''),'data-path-node':key,'data-path-state':state,'data-node-tone':tone.color};
    // The address the internet sees is not printed on screen; it is available as a tooltip only.
    if(p&&p.exit_ip&&profileHealth(p,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='healthy')attributes.title=bi('Exit IP: ','Внешний IP: ')+p.exit_ip;
    return E('div',attributes,[E('small',{},label),E('strong',{'class':'hv-node-protocol'},p?protocolLabel(p):'—'),E('b',{},p?countryLabel(p):bi('Choose in Settings','Выберите в настройках')),p?E('span',{'title':bi('Group: a label you can set in Settings → All application settings → 3 · Existing VPNs. It does not change how the VPN works.','Группа: метка, которую можно задать в «Настройки → Все настройки приложения → 3 · Существующие VPN». Она не влияет на работу VPN.')},(customName(p)?customName(p)+' · ':'')+bi('Group: ','Группа: ')+(p.channel||'default')):null,E('span',{'class':'hv-path-label','title':pathLabels[state]},[E('span',{'class':'hv-node-dot','aria-hidden':'true'}),tone.text])].filter(Boolean));}
  var diagram=E('div',{'class':'hv-auto-diagram hv-path-diagram'+(path.moving?' hv-path-moving':'')+(path.direction==='back'?' hv-path-back':''),'aria-label':bi('Configured failover path','Настроенная схема переключения')},[box(source,bi('Primary','Основной'),'source'),E('span',{'class':'hv-auto-arrow '+(path.direction!=='none'?'hv-arrow-on':''),'aria-label':path.moving?bi('Switching in progress','Выполняется переключение'):path.direction!=='none'?bi('Reserve selected','Выбран резерв'):bi('Automatic transition inactive','Автопереход неактивен')},path.direction==='back'?'←':path.direction==='forward'?'→':'⋯'),box(target,bi('Reserve','Резерв'),'target')]);
  var pairMode=settings.pair_auto_mode==='router-probed-ipv4';
  var until=pairMode?0:autoWindowDeadline(intent,settings);
  var readiness=autoReadiness(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  var checklist=null;
  if(pairMode){
    checklist=null&&E('details',{'class':'hv-auto-readiness','data-auto-explanation':'mode'},[E('summary',{},bi('How two-channel Auto works','Как работает Auto двух каналов')),E('p',{'class':'hv-step-note'},bi('Auto starts the saved primary and reserve, checks IPv4 DNS/HTTPS, switches after repeated failures and returns after stable recovery according to your settings. Stop remains available during startup. Auto needs an explicit Start after restart.','Auto запускает сохранённые основной и резервный VPN, проверяет IPv4 DNS/HTTPS, переключается после повторных отказов и возвращается после устойчивого восстановления по вашим настройкам. Stop доступен при запуске. После перезапуска нужен явный Start.'))]);
  }else if(!model.on&&!model.transitioning&&!model.stop){
    checklist=E('div',{'class':'hv-auto-readiness'},[E('p',{'class':'hv-step-note'},bi('Step 2 · Turn on Auto. Do it after step 1 (“Check the VPNs now”, at the top of this page) shows that your VPNs work and the list below is complete.','Шаг 2 · Включите Auto. Делайте это после шага 1 («Проверить VPN сейчас», вверху страницы), когда проверка показала, что ваши VPN работают, и список ниже выполнен.')),E('h3',{},readiness.ready?bi('Ready to start','Готово к запуску'):bi('Before you can start Auto','Что нужно перед запуском Auto')),E('ol',{'class':'hv-req-list'},readiness.steps.map(function(step){
      var isNext=readiness.next&&readiness.next.key===step.key;
      var extra=step.key==='router'&&!step.done&&step.codes&&step.codes.length?E('ul',{'class':'hv-req-codes'},step.codes.map(function(code){return E('li',{},[safeCode(code)?errorCodeLink(code):E('code',{},code),' · '+autoBlockerText(code),renderAutoRemedy(code)].filter(Boolean));})):null;
      return E('li',{'class':'hv-req hv-req-'+(step.done?'done':isNext?'next':'todo')},[E('span',{'class':'hv-req-mark','aria-hidden':'true'},step.done?'✓':isNext?'→':'·'),E('div',{},[E('strong',{},step.title),step.done?null:E('p',{},step.hint),extra].filter(Boolean)),E('span',{'class':'hv-visually-hidden'},step.done?bi('done','выполнено'):bi('not done','не выполнено'))]);
    })),E('p',{'class':'hv-req-actions'},[E('a',{'class':'cbi-button','href':'#settings'},bi('Open Settings','Открыть настройки')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/start-lan-helper.ps1'),'download':'start-lan-helper.ps1'},bi('Download launcher','Скачать запуск'))])]);
  }
  var holdReturn=null;
  // Return to the primary belongs to this card: it is offered whenever traffic is on the reserve (also while Auto is on).
  if(!pairMode&&model.fresh&&['STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE','COMMITTED'].indexOf(ns.state)>=0){
    var answer=intent.return_result,answerText=answer&&Number.isFinite(answer.time)&&(typeof statusNow==='function'?statusNow(status):Date.now()/1000)-answer.time<600?(answer.ok?autoBlockerText('OPERATOR-RETURN'):autoBlockerText(answer.code)):'';
    var returnButton=guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':autoRequestBusy||autoStopBusy?'':null,'click':function(){
      if(autoRequestBusy||autoStopBusy)return;return guardedAction(returnButton,function(){autoRequestBusy=true;
      return rpc.declare({object:'homensai-vpn',reject:true,method:'native_return',expect:{}})().then(function(result){
        if(result&&result.accepted===false)ui.addNotification(null,E('p',{},(result.code||'RETURN-REFUSED')+' · '+autoBlockerText(result.code)));
        else if(!autoRequestAcknowledged(result,false))ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
        else ui.addNotification(null,E('p',{},bi('Return requested. The router checks the primary first and reports the result here.','Возврат запрошен. Роутер сначала проверит основной и покажет результат здесь.')));
      }).catch(function(){ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){autoRequestBusy=false;});},{key:'auto-return'});
    }},bi('Return to primary','Вернуться на основной')),'auto-return');
    holdReturn=E('details',{'class':'hv-auto-hold'},[E('summary',{},bi('Legacy-mode recovery','Восстановление прежнего режима')),returnButton,autoNoInternetLink(),answerText?E('p',{'role':'status'},answerText):null].filter(Boolean));
  }
  var technicalCode=ns.state?ns.state+(ns.reason?' · '+ns.reason:'')+(model.fresh?'':' · STATUS-STALE'):'UNKNOWN';
  var liveChart=typeof renderAutoLive==='function'?renderAutoLive(status,inventory):null;
  var dayChart=typeof renderAutoDay==='function'?renderAutoDay(status):null;
  var statistics=(liveChart||dayChart)?E('details',{'class':'hv-chart-card hv-auto-details hv-auto-statistics','data-auto-disclosure':'live-statistics','data-stats-reset':'auto'},[E('summary',{},bi('Real-time channel switching','Переключение каналов в реальном времени')),liveChart,dayChart].filter(Boolean)):null;
  if(statistics&&typeof rememberDisclosure==='function')rememberDisclosure(statistics,'auto-live-statistics');
  var header=E('div',{'class':'hv-auto-header','id':'hv-auto-vpn'},[E('h2',{},bi('Automatic VPN failover','Автоматическое переключение VPN')),typeof renderMonitorBlock==='function'?renderMonitorBlock(status,inventory):null].filter(Boolean));
  var failureInfo=intent.failure&&intent.failure.code&&!model.on?intent.failure.code:null;
  // A failed Start is shown once per failure in its own window, so the card layout never changes.
  if(failureInfo&&typeof ui!=='undefined'&&ui&&typeof ui.showModal==='function'){
    var failureKey=failureInfo+'@'+(intent.failure.time||0),shownKey=null;
    try{shownKey=window.sessionStorage.getItem('homensai-vpn-auto-failure');}catch(e){shownKey=AUTO_FAILURE_SHOWN;}
    if(shownKey!==failureKey&&AUTO_FAILURE_SHOWN!==failureKey){
      AUTO_FAILURE_SHOWN=failureKey;try{window.sessionStorage.setItem('homensai-vpn-auto-failure',failureKey);}catch(e){}
      ui.showModal(bi('Auto did not start','Auto не запустился'),[E('p',{},bi('Reason:','Причина:')),autoCodeNotice(failureInfo),E('div',{'class':'right'},E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть')))]);
    }
  }
  var automatic=E('section',{'class':'hv-chart-card hv-auto-control'},[header,E('div',{'class':'hv-auto-controls'},[E('div',{'class':'hv-auto-switch'},[E('div',{'class':'hv-auto-power-unit'},[E('strong',{'class':'hv-auto-state hv-auto-state-'+(autoWorking(light)?'on':'off'),'role':'status'},autoWorking(light)?bi('Auto works','Auto работает'):bi('Auto does not work','Auto не работает')),button,actionLabel]),renderAutoLight(light,technicalCode)]),typeof renderConnectivityCheck==='function'&&typeof refresh==='function'?renderConnectivityCheck(status,refresh,inventory):null].filter(Boolean)),holdReturn,checklist,pairMode?null:E('details',{'class':'hv-auto-scope','data-auto-explanation':'scope'},[E('summary',{},bi('About these checks','Об этих проверках')),E('p',{'class':'hv-auto-limit'},(pairMode?bi('Two selected VPN channels. The router checks it itself.','Два выбранных VPN-канала. Проверку делает сам роутер.'):bi('Experimental: each automatic switch must be confirmed by the LAN helper running on a computer in your network. Without it the router goes back to the previous route after 90 seconds.','Экспериментально: каждое автоматическое переключение должен подтвердить LAN-помощник на компьютере в вашей сети. Без него роутер через 90 секунд вернётся на прежний маршрут.'))+(Number.isFinite(until)&&until>0?' '+bi('Window ends: ','Окно действует до: ')+new Date(until*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB')+'.':''))])].filter(Boolean));
  return E('div',{'class':'hv-auto-sections'},[automatic,statistics,typeof renderManualSwitch==='function'?renderManualSwitch(status,inventory):null].filter(Boolean));
}

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
function telegramTestDelivery(button){
  return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,reject:true,method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result&&safeCode(result.code)?result.code:'TELEGRAM-TEST-UNKNOWN'));});},{key:'telegram-test'});
}
// A readiness check is expensive on a router. Share one pending request and reuse its result for ten seconds.
var setupCheckCache=null,setupWizardGeneration=0;
function setupCheckNow(){return typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now():Date.now();}
function setupCheckRequest(){
  var now=setupCheckNow();
  if(setupCheckCache&&(setupCheckCache.pending||now>=setupCheckCache.finished&&now-setupCheckCache.finished<10000))return setupCheckCache.promise;
  var entry={pending:true,finished:0,promise:null};setupCheckCache=entry;
  try{entry.promise=Promise.resolve(rpc.declare({object:'homensai-vpn',reject:true,method:'setup_check',expect:{}})());}catch(error){entry.promise=Promise.reject(error);}
  entry.promise=entry.promise.then(function(result){entry.pending=false;entry.finished=setupCheckNow();return result;},function(error){entry.pending=false;entry.finished=setupCheckNow();throw error;});
  return entry.promise;
}
function setupWizard(inventory,kind){
  // Every system/pair entry in the full application uses the same configured
  // client chooser. Keep the standalone legacy renderer for its isolated use.
  if(kind==='system'&&typeof openOnboardingSettings==='function')return openOnboardingSettings(inventory,{},'system');
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var setupCheck=kind==='system'?'pending':'passed',wizardGeneration=++setupWizardGeneration;
  var step=0,busy=false,closed=false,settings=inventory.settings||{},profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],custom=Array.isArray(inventory.servers)?inventory.servers:[];
  var draft={source:settings.plan_source||'',target:settings.plan_target||'',interval:settings.interval==null?10:settings.interval,duration:settings.native_duration==null?10:settings.native_duration,session_loss:!!settings.native_session_loss,servers:profiles.map(function(p){var saved=custom.filter(function(s){return s.profile===p.id;})[0]||{};return {profile:p.id,name:saved.name||p.name,channel:saved.channel||'default',priority:saved.priority==null?100:saved.priority,enabled:saved.enabled!==false};})};
  var tg={token:'',chat:settings.telegram_destination||'',enabled:!!settings.telegram_enabled,interval:settings.telegram_interval==null?60:settings.telegram_interval,schedule:settings.telegram_schedule||'interval',hour:settings.telegram_hour==null?7:settings.telegram_hour,weekly:settings.telegram_weekly!==false,monthly:settings.telegram_monthly!==false,items:tgItemsFromSetting(settings.telegram_items)};
  function field(title,node){node.setAttribute('aria-label',title);return E('label',{'class':'hv-wizard-field'},[E('span',{},title),node]);}
  function input(value,type){var node=E('input',{'type':type||'text'});node.value=value;return node;}
  function choice(value){var node=E('select',{},[E('option',{value:''},bi('Choose existing profile','Выберите существующий профиль'))].concat(profiles.map(function(p){return E('option',{value:p.id},p.name+' · '+p.protocol);})));node.value=value;return node;}
  function notify(code){ui.addNotification(null,E('p',{},code));}
  function live(){return !closed&&wizardGeneration===setupWizardGeneration;}
  function show(){
    if(!live())return;
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;},checks=[],nextButton;
    function updateGate(){if(nextButton)foolGate(nextButton,checks.concat([function(){return !busy&&(kind!=='system'||setupCheck==='passed');}]));}
    function numberField(title,node,key){var item=foolNumberRow(title,node,key,updateGate);checks.push(item.check);return item.row;}
    function textField(title,node,key){var item=foolTextRow(title,node,key,updateGate,key==='token'&&!settings.telegram_configured);checks.push(item.check);return item.row;}
    body.appendChild(E('p',{'class':'hv-eyebrow'},bi('Step ','Шаг ')+(step+1)+' / 3'));
    if(kind==='system'){
      body.appendChild(E('p',{'role':'status'},setupCheck==='passed'?'SETUP-CHECK-OK: installed UCI writer passed isolated check.':setupCheck==='pending'?'Checking installed UCI writer…':'SETUP-CHECK-FAILED: saving is blocked. After an upgrade, sign out and sign in to refresh application permissions.'));
      if(step===0){
        var primary=choice(draft.source),reserve=choice(draft.target),interval=input(draft.interval,'number'),duration=input(draft.duration,'number'),consent=input('','checkbox');consent.checked=draft.session_loss;
        [field(bi('Primary VPN','Основной VPN'),primary),field(bi('Reserve VPN','Резервный VPN'),reserve),numberField(bi('How often to check each VPN, seconds (10–300)','Как часто проверять каждый VPN, секунд (10–300)'),interval,'system.interval'),numberField(bi('Test window, minutes (1–240)','Окно теста, минут (1–240)'),duration,'system.duration'),field(bi('Allow a short interruption of calls and downloads while switching','Разрешить кратковременный разрыв звонков и загрузок при переключении'),consent)].forEach(function(n){body.appendChild(n);});
        body.appendChild(E('p',{},bi('Existing router profiles are reused. This wizard never imports, displays or replaces VPN keys.','Используются существующие профили роутера. Мастер не импортирует, не показывает и не заменяет VPN-ключи.')));
        read=function(){draft.source=primary.value;draft.target=reserve.value;draft.interval=Number(interval.value);draft.duration=Number(duration.value);draft.session_loss=consent.checked;return !!draft.source&&!!draft.target&&draft.source!==draft.target&&Number.isInteger(draft.interval)&&draft.interval>=10&&draft.interval<=300&&Number.isInteger(draft.duration)&&draft.duration>=1&&draft.duration<=240;};
      }else if(step===1){
        body.appendChild(E('p',{},bi('Names and order are only for convenience; they do not affect the VPN.','Названия и порядок нужны только для удобства, на работу VPN не влияют.')));
        var editors=draft.servers.map(function(row){var name=input(row.name),channel=input(row.channel),priority=input(row.priority,'number'),enabled=input('','checkbox');enabled.checked=row.enabled;body.appendChild(E('fieldset',{},[E('legend',{},row.profile),textField(bi('Display name','Название'),name,'name'),textField(bi('Channel group','Группа канала'),channel,'channel'),numberField(bi('Priority (1–1000)','Приоритет (1–1000)'),priority,'system.priority'),field(bi('Check this VPN','Проверять этот VPN'),enabled)]));return {row:row,name:name,channel:channel,priority:priority,enabled:enabled};});
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
      if(step===0){var token=input(tg.token,'password');token.autocomplete='off';body.appendChild(E('p',{},bi('Create a bot with BotFather. For a channel, add it as an administrator with permission to post. A token is secret and is never returned by the router.','Создайте бота через BotFather. В канале добавьте его администратором с правом публикации. Токен секретный и не возвращается роутером.')));body.appendChild(telegramTokenHelp());body.appendChild(textField(bi('Bot token (leave blank to keep the stored token)','Токен бота (пусто — сохранить имеющийся)'),token,'token'));if(settings.telegram_configured)body.appendChild(E('p',{},E('button',{'type':'button','class':'cbi-button cbi-button-negative','click':function(ev){
          var button=ev.currentTarget||ev.target;tg.token=token.value;
          if(FOOL_LOCKS['telegram-forget']){guardResume(button,'telegram-forget');return;}
          confirmAction(bi('Delete the stored token','Удалить сохранённый токен'),[bi('Telegram reports will be turned off.','Отчёты в Telegram будут выключены.')],bi('Delete token','Удалить токен'),function(){
            return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'telegram_forget',expect:{}})().then(function(result){
              if(result&&result.saved===true){closed=true;ui.hideModal();ui.addNotification(null,E('p',{},bi('The bot token was deleted and Telegram reports are off.','Токен бота удалён, отчёты в Telegram выключены.')));window.location.reload();}
              else ui.addNotification(null,E('p',{},result&&safeCode(result.code)?result.code:'SETUP-SAVE-FAILED'));
            });},{key:'telegram-forget'});
          },true,show);
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
    actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){if(busy||!live())return;closed=true;ui.hideModal();}},bi('Cancel','Отмена')));
    if(step>0)actions.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){if(busy||!live()||!foolGate(null,checks))return;read();step--;show();}},bi('Back','Назад')));
    actions.appendChild(nextButton=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':kind==='system'&&setupCheck!=='passed'?'':null,'click':function(ev){
      if(busy||!live()||kind==='system'&&setupCheck!=='passed')return;if(!foolGate(null,checks)||!read()){notify(bi('Check the highlighted fields, choose different primary and reserve profiles, and keep both monitored.','Проверьте выделенные поля, выберите разные основной и резервный профили и включите наблюдение за обоими.'));updateGate();return;}
      if(step<2){step++;show();return;}
      busy=true;body.setAttribute('aria-busy','true');progress.textContent=bi('Saving settings…','Сохранение настроек…');Array.from(actions.children).forEach(function(node){node.disabled=true;});
      var save=kind==='system'?rpc.declare({object:'homensai-vpn',reject:true,method:'setup_system',params:['source','target','interval','duration','session_loss','servers'],expect:{}})(draft.source,draft.target,draft.interval,draft.duration,draft.session_loss,draft.servers):rpc.declare({object:'homensai-vpn',reject:true,method:'setup_telegram',params:['token','chat','enabled','interval','schedule','hour','weekly','monthly','items'],expect:{}})(tg.token,tg.chat,tg.enabled,tg.interval,tg.schedule,tg.hour,tg.weekly,tg.monthly,tgItemsToSetting(tg.items));
      return save.then(function(result){if(!result||result.saved!==true){notify(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code)?result.code:'SETUP-SAVE-FAILED');return;}tg.token='';closed=true;ui.hideModal();notify('SETUP-SAVED: settings stored; automatic switching was not started.');window.location.reload();}).catch(function(){notify('SETUP-SAVE-FAILED: no confirmed result.');}).finally(function(){busy=false;body.setAttribute('aria-busy','false');progress.textContent='';Array.from(actions.children).forEach(function(node){node.disabled=false;});updateGate();});
    }},step<2?bi('Next','Далее'):bi('Save configuration','Сохранить настройки')));
    if(kind==='system'&&setupCheck!=='passed')body.querySelectorAll('input,select').forEach(function(node){node.disabled=true;});
    body.appendChild(actions);updateGate();ui.showModal(kind==='system'?bi('System setup wizard','Мастер настройки системы'):bi('Telegram channel wizard','Мастер Telegram-канала'),[body]);
  }
  show();
  if(kind==='system')setupCheckRequest().then(function(result){if(!live())return;setupCheck=result&&result.passed===true?'passed':'failed';show();}).catch(function(){if(!live())return;setupCheck='failed';show();});
}

var prioritySelections={};
function speedSettings(inventory){
  var s=inventory.settings||{},enabled=E('input',{type:'checkbox'}),auto=E('input',{type:'checkbox'}),checks=[],saveButton;enabled.checked=!!s.speed_enabled;auto.checked=!!s.speed_auto_new;
  function field(text,node){node.setAttribute('aria-label',text);return E('label',{'class':'hv-wizard-field'},[E('span',{},text),node]);}
  var nodes=[E('h3',{},bi('Speed test settings','Настройки тестов скорости')),E('p',{},bi('Tests use HTTPS through the chosen VPN and consume bandwidth. Payload quota excludes protocol overhead. Failed attempts keep their quota reservation.','HTTPS-тесты идут через выбранный VPN и расходуют трафик. Квота полезных данных не включает служебный трафик. Резерв квоты сохраняется и при ошибке.')),field(bi('Enable speed tests (off by default)','Включить тесты скорости (по умолчанию выключено)'),enabled),field(bi('Test after a new server connects','Тестировать после подключения нового сервера'),auto)];
  function updateGate(){if(saveButton)foolGate(saveButton,checks);}
  function number(key,fallback,label){var node=E('input',{type:'number'});node.value=s['speed_'+key]==null?fallback:s['speed_'+key];var item=foolNumberRow(label,node,'speed.'+key,updateGate);checks.push(item.check);nodes.push(item.row);return node;}
  var budget=number('budget_mib',8,bi('Payload budget per server, MiB','Лимит полезного трафика на сервер, МиБ')),duration=number('duration',5,bi('Measurement seconds per direction','Секунд измерения на направление')),streams=number('streams',2,bi('Parallel streams','Параллельные потоки')),daily=number('daily_mib',128,bi('Daily reserved quota, MiB','Суточная резервируемая квота, МиБ')),busy=number('busy_mbps',2,bi('Skip above current VPN traffic, Mbps','Не запускать при текущем VPN-трафике выше, Мбит/с'));
  saveButton=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(){
    if(!foolGate(saveButton,checks))return;
    return guardedAction(saveButton,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_speed',params:['enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'],expect:{}})(enabled.checked,auto.checked,Number(budget.value),Number(duration.value),Number(streams.value),Number(daily.value),Number(busy.value)).then(function(result){if(!result||result.saved!==true){ui.addNotification(null,E('p',{},result&&result.code||'SPEED-CONFIG-FAILED'));return;}ui.addNotification(null,E('p',{},'SPEED-CONFIG-SAVED'));window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-CONFIG-FAILED: no confirmed response.'));});},{key:'setup-speed'});
  }},bi('Save speed settings','Сохранить настройки скорости'));
  updateGate();guardResume(saveButton,'setup-speed');nodes.push(saveButton);
  return E('section',{'class':'hv-chart-card hv-speed-settings'},nodes);
}
function speedPanel(status,inventory,period,onPeriod){
  var history=status.speed_tests||{},s=inventory.settings||{},profiles=status.profiles||[],active=profiles.filter(function(p){return p.interface;}).slice(0,8);
  var chooser=E('select',{'aria-label':bi('Speed test server','Сервер для теста скорости')},[E('option',{value:'all'},bi('All listed interfaces (up to 8)','Все перечисленные интерфейсы (до 8)'))].concat(active.map(function(p){return E('option',{value:p.id},p.name+' · '+p.protocol);}))),section=E('section',{'class':'hv-chart-card hv-speed-panel'},[E('h3',{},bi('VPN server speed tests','Тесты скорости VPN-серверов')),E('p',{},bi('Bounded HTTPS payload goodput to Cloudflare. This is a sampled application-level result, not an Ookla score or a guarantee of current capacity. Inactive profiles are not started.','Ограниченное измерение полезной скорости HTTPS до Cloudflare. Это выборочный результат на уровне приложения, не оценка Ookla и не гарантия текущей пропускной способности. Неактивные профили не запускаются.'))]);
  var controls=E('div',{'class':'hv-native-actions'},[chooser,E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':s.speed_enabled&&active.length?null:'','click':function(){
    var selected=chooser.value==='all'?active.map(function(p){return p.id;}):[chooser.value],mib=s.speed_budget_mib||8,duration=s.speed_duration||5,streams=s.speed_streams||2;
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('p',{'data-speed-pause-review':'1'},bi('Auto and background monitoring pause for the test. VPN connections remain up. Afterwards monitoring resumes before Auto; a manual Stop is respected.','На время теста Auto и фоновый мониторинг приостанавливаются. VPN остаются подключёнными. Затем возобновляется мониторинг и после него Auto; ручной Stop учитывается.')),E('ul',{},selected.map(function(id){return E('li',{},(profiles.filter(function(p){return p.id===id;})[0]||{}).name||id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams).then(function(result){ui.addNotification(null,E('p',{},result.accepted?'SPEED-QUEUED':result.code||'SPEED-START-FAILED'));ui.hideModal();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-START-FAILED: no confirmed response.'));});},{key:'speed-start'});}},bi('Run test','Запустить тест')),'speed-start')]);
  }},bi('Test speed','Тестировать скорость')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'speed_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.queued?'SPEED-CANCEL-QUEUED':result.code||'SPEED-NOT-RUNNING'));});}},bi('Cancel current test','Отменить текущий тест'))]);
  section.appendChild(controls);
  section.appendChild(E('p',{},bi('Speed test: ','Тест скорости: ')+(history.state||'IDLE')+(history.code?' · '+history.code:'')+' · '+bi('Completed: ','Завершено: ')+(history.completed||0)));
  if(!s.speed_enabled)section.appendChild(E('p',{},E('a',{href:'#settings'},bi('Enable optional tests in Settings','Включите необязательные тесты в настройках'))));
  var select=E('select',{'aria-label':bi('Speed statistics period','Период статистики скорости'),'change':function(ev){onPeriod(ev.target.value);}},[['latest',bi('Latest test','Последний тест')],['day',bi('Today','Сегодня')],['week',bi('Last 7 days','Последние 7 дней')],['month',bi('Current calendar month','Текущий календарный месяц')]].map(function(row){return E('option',{value:row[0]},row[1]);}));select.value=period;section.appendChild(select);
  var now=Date.now()/1000,dateKey=function(t){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t*1000));},today=dateKey(now),rows=(history.results||[]).filter(function(row){return Number.isFinite(row.time)&&row.time<=now+5;});
  rows=rows.filter(function(row){return period==='latest'||period==='day'&&dateKey(row.time)===today||period==='week'&&row.time>=now-7*86400||period==='month'&&dateKey(row.time).slice(0,7)===today.slice(0,7);});
  var grouped={};rows.sort(function(a,b){return b.time-a.time;}).forEach(function(row){var group=grouped[row.id]||(grouped[row.id]={last:row,good:[],count:0});group.count++;if(!row.code&&Number.isFinite((row.download||{}).mbps)&&Number.isFinite((row.upload||{}).mbps))group.good.push(row);});
  var ranked=Object.keys(grouped).map(function(id){var g=grouped[id],good=period==='latest'?(g.good[0]===g.last?[g.last]:[]):g.good;function mean(key){return good.length?good.reduce(function(sum,row){return sum+(row[key]||{}).mbps;},0)/good.length:null;}return {id:id,g:g,down:mean('download'),up:mean('upload'),n:good.length};}).sort(function(a,b){return (b.down===null?-1:b.down)-(a.down===null?-1:a.down);});
  var table=E('table',{'class':'table'},[E('tr',{},[bi('Use','Выбрать'),bi('Server','Сервер'),bi('Protocol / channel','Протокол / канал'),bi('Download, Mbps','Скачивание, Мбит/с'),bi('Upload, Mbps','Отдача, Мбит/с'),bi('Successful / total tests','Успешных / всего тестов'),bi('Latest result','Последний результат'),bi('Last measured · Berlin','Последнее измерение · Берлин')].map(function(label){return E('th',{},label);} ))]);
  ranked.forEach(function(row){var current=profiles.filter(function(p){return p.id===row.id;})[0],last=row.g.last;var eligible=row.n>0&&!last.code&&current&&current.interface&&current.code==null;var checkbox=E('input',{'type':'checkbox','aria-label':bi('Recommend ','Рекомендовать ')+(current?current.name:last.name),'disabled':eligible?null:'','change':function(){prioritySelections[row.id]=checkbox.checked;}});checkbox.checked=eligible&&!!prioritySelections[row.id];var cells=[current?current.name:last.name,(last.protocol||bi('unknown','неизвестно'))+' / '+(last.channel||bi('default','по умолчанию')),row.down===null?'—':row.down.toFixed(2),row.up===null?'—':row.up.toFixed(2),row.n+' / '+row.g.count,last.code||'OK',new Date(last.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})].map(function(value){return E('td',{},value);});cells.unshift(E('td',{},checkbox));table.appendChild(E('tr',{},cells));});
  section.appendChild(table);
  section.appendChild(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(){var selected=ranked.filter(function(row){var current=profiles.filter(function(p){return p.id===row.id;})[0];return prioritySelections[row.id]&&row.n>0&&!row.g.last.code&&current&&current.interface&&current.code==null;}).map(function(row){return row.id;});if(!selected.length){ui.addNotification(null,E('p',{},'PRIORITY-SELECT-ELIGIBLE-SERVERS'));return;}return reviewPriorities(selected);}},bi('Review recommended priorities','Проверить рекомендуемые приоритеты')));
  if(!ranked.length)section.appendChild(E('p',{},bi('No real speed measurements for this period.','Реальных измерений скорости за этот период нет.')));
  section.appendChild(E('small',{},bi('Average of successful tests. Failed or cancelled tests are not counted as zero speed.','Среднее по успешным тестам. Неудачные и отменённые тесты не считаются нулевой скоростью.')));
  if(history.history_error)section.appendChild(E('p',{},history.history_error));
  if(history.history_truncated)section.appendChild(E('p',{},'SPEED-HISTORY-TRUNCATED: '+history.history_truncated));
  return section;
}

function trafficHistoryPanel(accounting){
  function dateKey(date){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);}
  var today=dateKey(new Date()),section=E('section',{'class':'hv-chart-card','data-stats-reset':'traffic'},[E('h3',{},bi('Daily WAN and VPN traffic','Суточный трафик WAN и VPN'))]);
  var wan=accounting.wan||{},vpnDays=accounting.days||{},wanDays=wan.days||{},days=Array.from(new Set(Object.keys(vpnDays).concat(Object.keys(wanDays)))).filter(function(day){return day<=today;}).sort().reverse();
  var table=E('table',{'class':'table'},[E('tr',{},[bi('Date','Дата'),'WAN ↓','WAN ↑','VPN ↓','VPN ↑',bi('Observation gaps','Пропуски измерений')].map(function(title){return E('th',{},title);}))]);
  function value(row,key){return row&&row.observed===true?E('td',{'data-sort-value':Number(row[key]||0)},bytes(Number(row[key]||0))):E('td',{},'—');}
  days.slice(0,90).forEach(function(day){var w=wanDays[day],v=vpnDays[day];table.appendChild(E('tr',{},[E('td',{},day),value(w,'rx'),value(w,'tx'),value(v,'rx'),value(v,'tx'),E('td',{},String((w&&w.gaps||0)+(v&&v.gaps||0)))]));});
  section.appendChild(table);
  if(!days.length)section.appendChild(E('p',{},bi('No daily observations yet. Missing measurements are not zero traffic.','Суточных измерений пока нет. Отсутствие измерений не означает нулевой трафик.')));
  section.appendChild(E('p',{},bi('WAN and VPN counters overlap, so do not add them together. A dash means there was no valid data that day. Up to 90 days are kept.','Счётчики WAN и VPN пересекаются, их нельзя складывать. Прочерк означает, что за этот день нет достоверных данных. Хранится до 90 дней.')));
  if(accounting.rpc_aggregated||accounting.retention&&Object.keys(accounting.retention).length)section.appendChild(E('p',{'class':'alert-message warning'},'HISTORY-PARTIAL: older measurements were aggregated or pruned to limit storage and RPC size.'));
  return section;
}

var RECOVERY_PRESETS={"fast_recovery": {"attempt_limit": 3, "attempt_window": 15, "cooldown": 60, "failures": 3, "min_dwell": 60, "primary_stable": 60, "primary_successes": 3, "return_policy": "healthy_primary", "successes": 2}, "hold_reserve": {"attempt_limit": 3, "attempt_window": 15, "cooldown": 180, "failures": 3, "min_dwell": 180, "primary_stable": 60, "primary_successes": 3, "return_policy": "hold_reserve", "successes": 2}, "stability": {"attempt_limit": 3, "attempt_window": 15, "cooldown": 300, "failures": 5, "min_dwell": 300, "primary_stable": 120, "primary_successes": 5, "return_policy": "healthy_primary", "successes": 3}};
function reviewPriorities(ordered){
  return rpc.declare({object:'homensai-vpn',reject:true,method:'priority_preview',params:['ordered'],expect:{}})(ordered).then(function(result){
    if(!result.accepted){ui.addNotification(null,E('p',{},result.code||'PRIORITY-PREVIEW-FAILED'));return;}
    ui.showModal(bi('Review server priorities','Проверьте приоритеты серверов'),[
      E('p',{},bi('Only this program’s priorities are saved. No route is changed.','Сохраняются только приоритеты этой программы. Маршрут не меняется.')),
      E('ol',{},result.rows.map(function(row){return E('li',{},row.name+' · '+row.protocol+' / '+row.channel+(row.enabled?'':' · disabled'));})),
      E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),
      guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'priority_apply',params:['ordered','revision'],expect:{}})(ordered,result.revision).then(function(saved){ui.addNotification(null,E('p',{},saved.code||'PRIORITY-UNKNOWN'));if(saved.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'PRIORITY-RPC-UNCONFIRMED'));});},{key:'priority-apply'});}},bi('Apply priorities','Применить приоритеты')),'priority-apply')
    ]);
  }).catch(function(){ui.addNotification(null,E('p',{},'PRIORITY-PREVIEW-UNCONFIRMED'));});
}
function recoveryWizard(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},step=0,presetName='';
  var labels={interval:bi('Check interval, seconds (10–300)','Интервал проверки, секунд (10–300)'),attempt_limit:bi('Maximum switching attempts (1–10)','Максимум попыток переключения (1–10)'),attempt_window:bi('Attempt counting window, minutes (1–15)','Период подсчёта попыток, минут (1–15)'),failures:bi('Consecutive failures before switching (3–10)','Сбоев подряд до переключения (3–10)'),successes:bi('Reserve checks that must pass (2–10)','Проверок резерва, которые должны пройти (2–10)'),cooldown:bi('Pause between switch attempts, seconds (60–1800)','Пауза между попытками переключения, секунд (60–1800)'),min_dwell:bi('Minimum time to stay on a route, seconds (60–3600)','Минимальное время на маршруте, секунд (60–3600)'),primary_successes:bi('Primary checks that must pass before returning (2–10)','Проверок основного, которые должны пройти перед возвратом (2–10)'),primary_stable:bi('The primary must stay healthy for, seconds (30–600)','Основной должен оставаться исправным, секунд (30–600)')};
  var defaults={interval:10,failures:3,successes:2,cooldown:60,min_dwell:60,return_policy:'healthy_primary',primary_successes:2,primary_stable:30,attempt_limit:3,attempt_window:15},draft={};
  Object.keys(defaults).forEach(function(key){var saved=key==='interval'?settings.interval:settings['recovery_'+key];draft[key]=saved==null?defaults[key]:saved;});
  // The requested defaults reset all fields; other presets change only recovery thresholds.
  if(Object.keys(defaults).every(function(key){return String(draft[key])===String(defaults[key]);}))presetName='defaults';
  Object.keys(RECOVERY_PRESETS).forEach(function(name){var row=RECOVERY_PRESETS[name];if(!presetName&&Object.keys(row).every(function(key){return String(row[key])===String(draft[key]);}))presetName=name;});
  function show(){
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;},checks=[],nextButton;
    function updateGate(){if(nextButton)foolGate(nextButton,checks);}
    body.appendChild(E('p',{},bi('These rules control the selected two-channel Auto. Stop Auto before saving, review the values, then start it again. Existing VPN profiles and routes are not edited by this form.','Эти правила управляют Auto двух выбранных каналов. Перед сохранением выключите Auto, проверьте значения и затем включите его снова. Форма не изменяет VPN-профили и маршруты.')));
    body.appendChild(E('p',{},bi('The attempt limit uses a rolling window; changing it does not erase earlier attempts. The separate cooldown also applies. Stop and return remain available.','Лимит попыток считается за скользящий период; изменение не стирает предыдущие попытки. Отдельная пауза также действует. Stop и возврат остаются доступны.')));
    if(step===0){
      var presetSelect=E('select',{'aria-label':bi('Recovery preset','Профиль восстановления')},[
        E('option',{value:''},bi('Custom settings','Свои настройки')),E('option',{value:'defaults'},bi('Default values','Значения по умолчанию')),E('option',{value:'stability'},bi('Stability','Стабильность')),E('option',{value:'fast_recovery'},bi('Fast recovery','Быстрое восстановление')),E('option',{value:'hold_reserve'},bi('Hold healthy reserve','Сохранять работающий резерв'))]);
      presetSelect.value=presetName;
      presetSelect.addEventListener('change',function(){presetName=presetSelect.value;var preset=presetName==='defaults'?defaults:RECOVERY_PRESETS[presetName];if(!preset)return;Object.keys(preset).forEach(function(key){if(presetName==='defaults'||['attempt_limit','attempt_window'].indexOf(key)<0)draft[key]=preset[key];});show();});
      body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Preset (defaults reset all fields; other presets change recovery thresholds)','Профиль (по умолчанию сбрасывает все поля; остальные меняют пороги)')),presetSelect]));
      var editors={};Object.keys(labels).forEach(function(key){var node=E('input',{type:'number','aria-label':labels[key]});node.value=draft[key];node.addEventListener('input',function(){draft[key]=node.value;presetName='';presetSelect.value='';});editors[key]=node;var item=foolNumberRow(labels[key],node,'recovery.'+key,updateGate);checks.push(item.check);body.appendChild(item.row);});
      var policy=E('select',{'aria-label':bi('Return policy','Политика возврата')},[E('option',{value:'healthy_primary'},bi('Return to the primary once it has been healthy for a while','Вернуться на основной, когда он некоторое время исправен')),E('option',{value:'hold_reserve'},bi('Stay on the working reserve until you decide','Оставаться на рабочем резерве, пока вы не решите иначе'))]);policy.value=draft.return_policy;policy.addEventListener('change',function(){draft.return_policy=policy.value;presetName='';presetSelect.value='';});body.appendChild(policy);
      read=function(){if(!foolGate(null,checks))return false;var limits={interval:[10,300],attempt_limit:[1,10],attempt_window:[1,15],failures:[3,10],successes:[2,10],cooldown:[60,1800],min_dwell:[60,3600],primary_successes:[2,10],primary_stable:[30,600]};var valid=Object.keys(editors).every(function(key){draft[key]=Number(editors[key].value);return Number.isInteger(draft[key])&&draft[key]>=limits[key][0]&&draft[key]<=limits[key][1];});draft.return_policy=policy.value;return valid;};
    }else{
      body.appendChild(E('h3',{},bi('Review recovery settings','Проверьте настройки восстановления')));
      body.appendChild(E('ul',{},Object.keys(labels).map(function(key){return E('li',{},labels[key]+': '+draft[key]);})));
      body.appendChild(E('p',{},bi('Return policy: ','Политика возврата: ')+draft.return_policy));
      body.appendChild(E('p',{},bi('Saving does not start Auto. The router-probed mode checks its own readiness; a separate LAN trial is required only for a mode that uses it.','Сохранение не запускает Auto. Режим с проверками роутера проверяет свою готовность; отдельный LAN-тест нужен только режиму, который его использует.')));
    }
    var actions=[E('button',{'type':'button','class':'cbi-button','click':function(){if(FOOL_LOCKS['setup-recovery']&&FOOL_LOCKS['setup-recovery'].phase==='work')return;ui.hideModal();}},bi('Cancel','Отмена'))];
    if(step)actions.push(E('button',{'type':'button','class':'cbi-button','click':function(){if(FOOL_LOCKS['setup-recovery']&&FOOL_LOCKS['setup-recovery'].phase==='work')return;step=0;show();}},bi('Back','Назад')));
    actions.push(nextButton=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){if(!read()){ui.addNotification(null,E('p',{},'RECOVERY-RANGE'));return;}if(!step){step=1;show();return;}var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_recovery',params:['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','interval'],expect:{}})(draft.failures,draft.successes,draft.cooldown,draft.min_dwell,draft.return_policy,draft.primary_successes,draft.primary_stable,draft.attempt_limit,draft.attempt_window,draft.interval).then(function(result){ui.addNotification(null,E('p',{},result.saved?'RECOVERY-SAVED':result.code||'RECOVERY-SAVE-FAILED'));if(result.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'RECOVERY-SAVE-UNCONFIRMED'));});},{key:'setup-recovery'});}},step?bi('Save recovery settings','Сохранить настройки восстановления'):bi('Next','Далее')));
    updateGate();guardResume(nextButton,'setup-recovery');body.appendChild(E('div',{'class':'hv-wizard-actions'},actions));ui.showModal(bi('Recovery setup wizard','Мастер восстановления'),[body]);
  }
  show();
}

function monitorPreferences(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},saveButton,checks=[];
  var planning=E('input',{type:'checkbox','aria-label':bi('Show what Auto would do (no switching)','Показывать, что сделал бы Auto (без переключения)')});planning.checked=!!settings.plan_enabled;
  var body=E('div',{'class':'hv-wizard'},[E('p',{},bi('Only this program’s own settings change. Saving statistics more often wears the router flash memory faster. This does not start Auto or connect any VPN.','Меняются только настройки этой программы. Частое сохранение статистики быстрее изнашивает флеш-память роутера. Auto не запускается, VPN не подключаются.'))]);
  function updateGate(){if(saveButton)foolGate(saveButton,checks);}
  function number(label,key,value,ariaLabel){var node=E('input',{type:'number'});node.value=value;var item=foolNumberRow(label,node,key,updateGate);node.setAttribute('aria-label',ariaLabel);checks.push(item.check);body.appendChild(item.row);return node;}
  var interval=number(bi('How often to check each VPN (10–300 seconds)','Как часто проверять каждый VPN (10–300 секунд)'),'monitor.interval',settings.interval==null?10:settings.interval,bi('How often to check each VPN, seconds','Как часто проверять каждый VPN, секунд')),checkpoint=number(bi('Save statistics every (300–3600 seconds)','Сохранять статистику каждые (300–3600 секунд)'),'monitor.checkpoint',settings.checkpoint==null?900:settings.checkpoint,bi('Save statistics every, seconds','Сохранять статистику каждые, секунд')),limit=number(bi('Most VPNs checked per round (1–16)','Максимум VPN за один раунд проверки (1–16)'),'monitor.probe_limit',settings.probe_limit==null?16:settings.probe_limit,bi('Most VPNs checked per round','Максимум VPN за один раунд проверки'));
  var logLimit=number(bi('Live journal observations (1–2000)','Наблюдений в живом журнале (1–2000)'),'monitor.live_log_limit',settings.live_log_limit==null?2000:settings.live_log_limit,bi('Live journal observations','Наблюдений в живом журнале'));
  var historyDays=number(bi('Detailed history, days (1–7)','Подробная история, дней (1–7)'),'monitor.history_days',settings.history_days==null?7:settings.history_days,bi('Detailed history, days','Подробная история, дней'));
  body.appendChild(E('p',{},bi('The journal limit controls browser memory. The history period controls saved incident details and observations. Monthly and lifetime counters are kept separately. Reducing the period removes old details at the next cleanup/checkpoint; increasing it cannot recover removed history.','Лимит журнала ограничивает память браузера. Срок истории ограничивает сохранённые подробности событий и наблюдений. Месячные и общие счётчики хранятся отдельно. Уменьшение срока удаляет старые подробности при очередной очистке/checkpoint; увеличение не восстанавливает удалённую историю.')));
  body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Show what Auto would do (no switching)','Показывать, что сделал бы Auto (без переключения)')),planning]));
  saveButton=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
    if(!foolGate(saveButton,checks))return;
    return guardedAction(saveButton,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_monitor',params:['interval','checkpoint','probe_limit','planning_enabled','live_log_limit','history_days'],expect:{}})(Number(interval.value),Number(checkpoint.value),Number(limit.value),planning.checked,Number(logLimit.value),Number(historyDays.value)).then(function(result){ui.addNotification(null,E('p',{},result&&result.saved===true?'MONITOR-PREFERENCES-SAVED':result&&result.code||'MONITOR-PREFERENCES-FAILED'));if(result&&result.saved===true){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-PREFERENCES-UNCONFIRMED'));});},{key:'setup-monitor'});
  }},bi('Save monitoring preferences','Сохранить параметры мониторинга'));
  updateGate();guardResume(saveButton,'setup-monitor');
  body.appendChild(E('div',{'class':'hv-wizard-actions'},[E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),saveButton]));
  ui.showModal(bi('Monitoring and history retention','Мониторинг и хранение истории'),[body]);
}

var FAULT_UI_CONTEXT=null;
function faultCurrentBinding(status,inventory){
  status=status||{};inventory=inventory||{};
  var now=(typeof routerWall==='function'?routerWall():Date.now()/1000),native=(status||{}).native_failover||{},settings=(inventory||{}).settings||{};
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):null,target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):null;
  var model=typeof vendorDiagnosticsModel==='function'?vendorDiagnosticsModel(status,inventory,now):null,coord=model&&model.coordination;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&0<=now-status.time&&now-status.time<=90&&Number.isFinite(native.time)&&0<=now-native.time&&now-native.time<=30;
  var healthy=source&&target&&Number.isFinite(source.time)&&0<=now-source.time&&now-source.time<=90&&Number.isFinite(target.time)&&0<=now-target.time&&now-target.time<=90&&source.code===null&&target.code===null&&source.dns_ok===true&&target.dns_ok===true&&Number.isInteger(source.https_success)&&source.https_success>=2&&Number.isInteger(target.https_success)&&target.https_success>=2;
  var ready=!!(fresh&&native.state==='OBSERVING'&&native.certified===true&&settings.native_session_loss===true&&source&&target&&healthy&&native.source===source.id&&native.target===target.id&&typeof native.vendor_identity==='string'&&/^[0-9a-f]{64}$/.test(native.vendor_identity)&&native.source_generation===source.vendor_generation&&native.target_generation===target.vendor_generation&&coord&&coord.known&&coord.state==='READY'&&coord.code==='CROSS-TUNNEL-READY'&&coord.source===source.vendor_tunnel_id&&coord.target===target.vendor_tunnel_id);
  var pairMode=settings.pair_auto_mode==='router-probed-ipv4';
  if(pairMode){
    var running=(status.auto_control||{}).pair_phase==='RUNNING';
    var path=typeof channelPathSelection==='function'?channelPathSelection(status,now,source&&source.id,target&&target.id):null;
    var selected=path&&path.selected&&source&&path.selected===source.id?'source':path&&path.selected&&target&&path.selected===target.id?'target':null;
    ready=!!(fresh&&running&&selected&&healthy&&settings.native_session_loss===true&&native.mode==='continuous-pair'&&native.proof_scope==='router-probed-ipv4'&&source&&target&&native.source===source.id&&native.target===target.id&&coord&&coord.known&&coord.state==='READY'&&coord.code==='CROSS-TUNNEL-READY');
    if(selected==='target'){var original=source;source=target;target=original;}
  }
  return {ready:ready,source:source,target:target,pairMode:pairMode,certificate:pairMode&&source&&target?source.vendor_generation+target.vendor_generation:native.vendor_identity||null};
}
function faultChannelName(profile,settings){
  if(!profile)return bi('no working channel is selected now','сейчас не выбран рабочий канал');
  var role=profile.id===settings.plan_source?bi('Primary channel','Основной канал'):profile.id===settings.plan_target?bi('Reserve channel','Резервный канал'):bi('Channel outside the pair','Канал вне пары');
  var name=[typeof countryName==='function'?countryName(profile):null,typeof protocolLabel==='function'?protocolLabel(profile):profile.protocol].filter(Boolean).join(' · ');
  var tunnel=String(profile.vendor_tunnel_id||profile.interface||'').replace(/^[a-z]+:/,'');
  return role+(name?' — '+name:'')+(tunnel?' ('+tunnel+')':'');
}
function faultPanel(status,inventory,refresh){
  var state=status.operator_fault||{},active=['PREPARING','ARMED','ACTIVE','TIMEOUT-ELAPSED','UNKNOWN'].indexOf(state.state)>=0||state.cleaned===false,native=status.native_failover||{},settings=inventory.settings||{},binding=faultCurrentBinding(status,inventory),source=binding.source,ready=binding.ready;
  FAULT_UI_CONTEXT={status:status,inventory:inventory};
  var section=E('section',{'class':'hv-chart-card hv-fault-panel'},[E('h2',{},bi('Controlled VPN tunnel traffic fault','Контролируемый сбой трафика VPN-туннеля')),E('p',{},bi('This temporarily blocks IPv4 traffic through the whole current VPN tunnel device, keeping its process connected. It cannot isolate one upstream server inside the tunnel. Router INPUT, management routes and Kill Switch are unchanged.','Временно блокируется IPv4-трафик всего устройства текущего VPN-туннеля, сам процесс остаётся подключённым. Это не позволяет изолировать один сервер внутри туннеля. INPUT роутера, маршруты управления и Kill Switch не меняются.'))]);
  section.appendChild(E('p',{'role':'status'},bi('Test state: ','Состояние теста: ')+(active?bi('Testing transition to the other channel','Тестируется переход на другой канал'):state.transition_confirmed===true?bi('Transition confirmed; artificial fault removed','Переход подтверждён; искусственный сбой снят'):state.code==='FAULT-TRANSITION-NOT-CONFIRMED'?bi('Transition was not confirmed in time; artificial fault removed','Переход не подтверждён за отведённое время; искусственный сбой снят'):state.code==='FAULT-CANCELLED'?bi('Test stopped; artificial fault removed','Тест остановлен; искусственный сбой снят'):state.code?bi('Last test: ','Последний тест: ')+state.code:bi('Ready to check the current channel','Готов к проверке текущего канала'))+(state.until?' · '+bi('Remaining about ','Осталось примерно ')+(state.remaining_seconds==null?Math.max(0,Math.ceil(state.until-(typeof routerWall==='function'?routerWall():Date.now()/1000))):state.remaining_seconds)+' s':'')));
  var duration=E('select',{'aria-label':bi('Fault duration','Длительность сбоя')},[30,60,120,150,180].map(function(value){return E('option',{value:String(value)},value+' s');}));duration.value='150';
  section.appendChild(E('p',{},[bi('Channel to interrupt: ','Канал для имитации сбоя: '),E('strong',{},faultChannelName(source,settings))]));
  section.appendChild(E('div',{'class':'hv-native-actions'},[duration,E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','disabled':active?'':null,'click':function(){
    if(active)return;
    if(!ready||!source){
      ui.showModal(bi('Prepare the transition test','Подготовка теста перехода'),[
        E('p',{},bi('The router must confirm a working current channel, a healthy alternative and running Auto before interrupting traffic.','Перед прерыванием трафика роутер должен подтвердить текущий рабочий канал, исправный второй канал и включённый Auto.')),
        E('ul',{},faultBlockers(status,inventory,source).map(function(r){return E('li',{},[bi(r.en,r.ru)].concat(Array.isArray(r.link)?r.link:[r.link]).filter(Boolean));})),
        E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();return refresh();}},bi('Refresh current checks','Обновить текущие проверки')),
        E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть'))]);return;
    }
    if(['30','60','120','150','180'].indexOf(duration.value)<0)return;
    var reviewedScope='channel',reviewedDuration=Number(duration.value),reviewedId=source.id,reviewedTunnel=source.vendor_tunnel_id,reviewedGeneration=source.vendor_generation,reviewedTarget=binding.target.id,reviewedTargetGeneration=binding.target.vendor_generation,reviewedCertificate=binding.certificate;
    ui.showModal(bi('Review deliberate tunnel traffic interruption','Подтвердите прерывание трафика туннеля'),[E('p',{},bi('Calls and sessions can reconnect. This affects the whole tunnel device, not an isolated provider server or profiles sharing an editable label. The router checks the current channel and the healthy alternative again before applying the bounded fault. Auto must confirm the transition; a click alone is not a successful test.','Звонки и сессии могут переподключиться. Затрагивается всё устройство туннеля, а не отдельный сервер провайдера и не профили с одинаковой редактируемой меткой. Перед ограниченным сбоем роутер повторно проверяет текущий канал и исправность второго. Auto должен подтвердить переход; само нажатие не означает успешного теста.')),E('ul',{},[E('li',{},reviewedTunnel+' · '+reviewedId)]),E('p',{},bi('Maximum fault duration: ','Максимальная длительность сбоя: ')+reviewedDuration+' s'),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','click':function(ev){
      var current=FAULT_UI_CONTEXT&&faultCurrentBinding(FAULT_UI_CONTEXT.status,FAULT_UI_CONTEXT.inventory);
      if(!current||!current.ready||current.source.id!==reviewedId||current.source.vendor_tunnel_id!==reviewedTunnel||current.source.vendor_generation!==reviewedGeneration||current.target.id!==reviewedTarget||current.target.vendor_generation!==reviewedTargetGeneration||current.certificate!==reviewedCertificate){ui.addNotification(null,E('p',{},bi('FAULT-NOT-CURRENT-SOURCE: the VPN changed while this window was open. Close it and check again.','FAULT-NOT-CURRENT-SOURCE: VPN изменился, пока окно было открыто. Закройте его и проверьте снова.')));return;}
      var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'fault_start',params:['profile','scope','duration'],expect:{}})(reviewedId,reviewedScope,reviewedDuration).then(function(result){ui.addNotification(null,E('p',{},result&&safeCode(result.code)?result.code:'FAULT-UNKNOWN'));ui.hideModal();return refresh();}).catch(function(){ui.addNotification(null,E('p',{},'FAULT-RPC-UNCONFIRMED: inspect actual test state.'));});},{key:'fault-start'});
    }},bi('Start transition test','Запустить тест перехода')),'fault-start')]);
  }},bi('Simulate traffic failure','Имитировать сбой трафика')),active?E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'fault_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'FAULT-CANCEL-UNKNOWN'));return refresh();});}},bi('Stop test and restore traffic','Остановить тест и снять сбой')):null].filter(Boolean)));
  section.appendChild(E('small',{},bi('Inactive profiles are not started. This is a traffic fault, not a VPN service stop. Auto mode Stop also requests fault cleanup.','Неактивные профили не запускаются. Это сбой трафика, а не остановка VPN-службы. Остановка авторежима также запрашивает очистку сбоя.')));
  if(state.history&&state.history.length){var table=E('table',{'class':'table'},[E('tr',{},[bi('Time · Berlin','Время · Берлин'),bi('Code','Код'),bi('Profiles','Профили'),bi('Scope','Область')].map(function(text){return E('th',{},text);} ))]);state.history.slice().reverse().forEach(function(row){table.appendChild(E('tr',{},[new Date(row.time*1000).toLocaleString('en-GB',{timeZone:'Europe/Berlin'}),(safeCode(row.code)?errorCodeLink(row.code):row.code),(row.profiles||[]).join(', '),row.scope].map(function(value){return E('td',{},value);})));});section.appendChild(table);}
  return section;
}

// Every reason why the failure test cannot start, in plain words, each with the place to fix it (mirrors the router-side checks).
function faultBlockers(status,inventory,source){
  var native=status.native_failover||{},settings=(inventory||{}).settings||{},profiles=status.profiles||[],now=(typeof routerWall==='function'?routerWall():Date.now()/1000);
  var reasons=[],hash=function(tab,label){return E('a',{'class':'cbi-button','href':'#'+tab},label);};
  var target=faultCurrentBinding(status,inventory).target;
  if(!settings.plan_source||!settings.plan_target||!source)reasons.push({en:'No primary and reserve VPN are chosen.',ru:'Не выбраны основной и резервный VPN.',link:hash('settings',bi('Go to Settings → All application settings → 3 · Existing VPNs','Перейти в «Настройки → Все настройки приложения → 3 · Существующие VPN»'))});
  if(status.rpc_error||!(0<=now-status.time&&now-status.time<=90))reasons.push({en:'The router sends no fresh data, so the monitor may not be running.',ru:'Роутер не присылает свежих данных, возможно, мониторинг не работает.',link:hash('overview',bi('Go to the Overview and check the Monitoring block','Перейти на «Обзор» и проверить блок «Мониторинг»'))});
  var current=faultCurrentBinding(status,inventory);
  if(!current.ready&&!current.pairMode)reasons.push({en:'The current tunnel identity, fresh coordination and a certificate for exactly these current profiles must agree. The router independently rechecks the private certificate.',ru:'Текущая идентичность туннеля, свежая координация и сертификат именно этих текущих профилей должны совпадать. Роутер независимо перепроверяет закрытый сертификат.',link:hash('channels',bi('Review current tunnel observations','Проверить текущие наблюдения туннелей'))});
  if(settings.native_session_loss===false||settings.native_session_loss==='0')reasons.push({en:'You have not allowed a short reconnection of calls and sessions.',ru:'Вы не разрешили короткое переподключение звонков и сессий.',link:hash('settings',bi('Go to Settings → All application settings → 3 · Existing VPNs and tick the permission','Перейти в «Настройки → Все настройки приложения → 3 · Существующие VPN» и поставить разрешение'))});
  if(target&&profileHealth(target,now).state!=='healthy')reasons.push({en:'The reserve VPN does not work now; the test needs a healthy reserve.',ru:'Резервный VPN сейчас не работает; для теста нужен исправный резерв.',link:hash('channels',bi('Go to Channels and servers','Перейти в «Каналы и серверы»'))});
  var running=['OBSERVING','COMMITTED'].indexOf(native.state)>=0;
  if(!running)reasons.push({en:'Auto is not on. The test requires a confirmed current channel and running Auto.',ru:'Auto не включён. Для теста нужен подтверждённый текущий канал и работающий Auto.',link:hash('overview',bi('Go to the Overview and turn Auto on (button in “Automatic VPN failover”)','Перейти на «Обзор» и включить Auto (кнопка в блоке «Автоматическое переключение VPN»)'))});
  else if(!current.pairMode&&native.certified!==true)reasons.push({en:'This fault trial requires an independent client-confirmed certificate. Router-probed Auto may already be running; this is a separate permission for deliberate interruption.',ru:'Для этого теста сбоя нужен отдельный сертификат с подтверждением LAN-клиента. Router-probed Auto при этом может уже работать; это отдельное разрешение на преднамеренное прерывание.',link:[hash('settings',bi('Go to Settings → LAN trial','Перейти в «Настройки» → LAN-тест')),' ',helpLink('helper-what',bi('Help: how to run the LAN helper','Помощь: как запустить LAN-помощник'))]});
  else if(!(0<=now-native.time&&now-native.time<=30))reasons.push({en:'The controller status is old.',ru:'Статус контроллера устарел.',link:hash('overview',bi('Go to the Overview and check the Auto card','Перейти на «Обзор» и посмотреть блок Auto'))});
  if(current.pairMode&&!current.ready&&!reasons.length)reasons.push({en:'The current pair is not ready yet. Refresh observations and check both channels on Overview.',ru:'Текущая пара ещё не готова. Обновите наблюдения и проверьте оба канала на «Обзоре».',link:hash('overview',bi('Overview','Обзор'))});
  if(!reasons.length)reasons.push({en:'The router refused to start the test.',ru:'Роутер отказался запускать тест.',link:errorCodeLink('FAULT-CERTIFIED-AUTO-REQUIRED')});
  return reasons;
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

var UI_STATUS_CLOCKS=new WeakMap();
var UI_CLOCK_SKEW=0;
// Router time as the browser sees it; a PC clock a few seconds off must not turn fresh data into "waiting".
function routerWall(){return Date.now()/1000+UI_CLOCK_SKEW;}
function statusNow(status){
  var wall=Date.now()/1000;
  if(!status||typeof status!=='object'||!Number.isFinite(status.server_time)||status.server_time<=0||status.server_time>253370764799)return wall;
  var tick=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now()/1000:wall;
  var saved=UI_STATUS_CLOCKS.get(status);
  if(!saved){saved={server:status.server_time,tick:tick};UI_STATUS_CLOCKS.set(status,saved);}
  var value=saved.server+Math.max(0,tick-saved.tick);UI_CLOCK_SKEW=value-wall;return value;
}
// The latest router check of a channel in words. A failed check is a result too: it shows what failed and when.
function channelCheckText(profile,now){
  if(!profile)return bi('No VPN selected','VPN не выбран');
  if(!Number.isFinite(profile.time))return bi('The first router check is being collected','Первая проверка роутера выполняется');
  var when=new Date(profile.time*1000).toLocaleTimeString(typeof locale!=='undefined'&&locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}),age=Math.max(0,Math.round(now-profile.time));
  var old=age>90?' · '+bi(age+' s ago',age+' с назад'):'',https=Number.isInteger(profile.https_success)?profile.https_success:0;
  if(!profile.interface||profile.code==='VPN-001')return bi('Tunnel is not connected','Туннель не подключён')+' · '+when+old;
  if(profile.code==null&&profile.dns_ok===true&&https>=2)return (Number.isFinite(profile.rtt_ms)&&profile.rtt_ms>=0?profile.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS'):bi('Check passed: HTTPS ','Проверка пройдена: HTTPS ')+https+'/3')+' · '+when+old;
  return bi('Check failed: ','Проверка не прошла: ')+'HTTPS '+https+'/3'+(profile.dns_ok===false?', '+bi('DNS failed','DNS не прошёл'):'')+' · '+when+old;
}
// Independent, identity-bound ICMP timing. HTTPS measurements never supply a Ping value.
function channelPingModel(profile,status,now){
  function result(state,text,code,value){return {state:state,text:text,code:code,rtt_ms:value==null?null:value};}
  function pending(){return result('checking',bi('Waiting for the first ICMP check','Ждём первую ICMP-проверку'),'PING-CHECK-PENDING');}
  function unavailable(code){return result('unavailable',code==='PING-NOT-SELECTED'?bi('Not measured: this VPN is outside the selected pair','Не измеряется: этот VPN не входит в выбранную пару'):bi('ICMP measurement is unavailable','ICMP-измерение недоступно'),code||'PING-UNAVAILABLE');}
  if(!profile)return unavailable('PING-UNAVAILABLE');
  if(!status||status.rpc_error||status.error)return result('unavailable',bi('Waiting for the router answer','Ждём ответа роутера'),'STATUS-REQUEST-FAILED');
  if(!Number.isFinite(now)||!Number.isFinite(status.time)||now-status.time< -5||now-status.time>90)return result('stale',bi('Router data is old; waiting for a new check','Данные роутера устарели; ждём новую проверку'),'MONITOR-DATA-STALE');
  if(!profile.interface||profile.administrative_state==='disabled')return result('inactive',bi('VPN is not connected; ICMP is not measured','VPN не подключён; ICMP не измеряется'),'PING-INACTIVE');
  var ping=profile.ping;
  if(!ping||typeof ping!=='object'||Array.isArray(ping))return pending();
  if(ping.state==='checking')return pending();
  if(ping.state==='inactive')return result('inactive',bi('ICMP check is inactive','ICMP-проверка не выполняется'),'PING-INACTIVE');
  if(ping.code==='PING-IDENTITY-CHANGED')return result('checking',bi('VPN settings changed; waiting for a new ICMP check','Настройки VPN изменились; ждём новую ICMP-проверку'),'PING-IDENTITY-CHANGED');
  if(ping.state==='unavailable')return unavailable(ping.code==='PING-NOT-SELECTED'?'PING-NOT-SELECTED':'PING-UNAVAILABLE');
  var bound=ping.metric==='icmp-rtt-ms'&&ping.target==='1.1.1.1'&&typeof profile.vendor_generation==='string'&&/^[a-f0-9]{32}$/.test(profile.vendor_generation)&&ping.generation===profile.vendor_generation&&typeof profile.vendor_tunnel_id==='string'&&ping.vendor_tunnel_id===profile.vendor_tunnel_id&&ping.interface===profile.interface&&profile.vendor_state==='SETTLED';
  if(!bound)return result('checking',bi('VPN settings changed; waiting for a new ICMP check','Настройки VPN изменились; ждём новую ICMP-проверку'),'PING-IDENTITY-CHANGED');
  if(!Number.isFinite(ping.time)||!Number.isFinite(ping.valid_for)||ping.valid_for<=0||ping.valid_for>45||now-ping.time< -5)return unavailable('PING-UNAVAILABLE');
  if(ping.state==='stale'||now-ping.time>ping.valid_for)return result('stale',bi('ICMP result is old; waiting for a new check','ICMP-результат устарел; ждём новую проверку'),'PING-DATA-STALE');
  if(ping.state==='failed')return result('failed',bi('No ICMP reply; this does not change the VPN verdict','Нет ответа ICMP; это не меняет оценку VPN'),'PING-FAILED');
  if(ping.state!=='ok'||ping.code!=null||!Number.isFinite(ping.rtt_ms)||ping.rtt_ms<0||ping.rtt_ms>60000)return unavailable('PING-UNAVAILABLE');
  return result('ok',ping.rtt_ms.toFixed(1)+' '+bi('ms','мс'),null,ping.rtt_ms);
}
function renderChannelPing(profile,status,now){
  var model=channelPingModel(profile,status,now);
  return E('small',{'class':'hv-channel-ping','data-ping-state':model.state,'title':bi('An independent ICMP check through this VPN to 1.1.1.1. HTTPS and DNS checks keep their own results.','Отдельная ICMP-проверка через этот VPN до 1.1.1.1. Результаты HTTPS и DNS остаются отдельными.')},'Ping (ICMP) → 1.1.1.1: '+model.text+(model.code?' · '+model.code:''));
}
var UI_DATA_CAUSE=null;
function dataCause(status,now){
  if(!status||status.rpc_error)return {code:'STATUS-REQUEST-FAILED',text:bi('the page got no answer from the router program','страница не получила ответ от программы на роутере')};
  if(!Number.isFinite(status.time)||now-status.time>90)return {code:'MONITOR-DATA-STALE',text:bi('the router has not sent fresh data'+(Number.isFinite(status.time)?' for '+Math.round(now-status.time)+' s':''),'роутер не присылает свежие данные'+(Number.isFinite(status.time)?' уже '+Math.round(now-status.time)+' с':''))};
  return {code:'VENDOR-OBSERVATION-PENDING',text:bi('the monitor has not finished observing this channel yet (up to a minute after a start or change)','мониторинг ещё не закончил наблюдение этого канала (до минуты после запуска или изменения)')};
}
function dataCauseText(prefix){var c=UI_DATA_CAUSE||dataCause(null,0);return (prefix||bi('Not available: ','Нет данных: '))+c.text+' ('+c.code+')';}
function profileHealth(profile,now){
  if(!profile.interface||profile.administrative_state==='disabled')return {state:'inactive',label:bi('Inactive','Неактивен')};
  if(!Number.isFinite(profile.time)||now-profile.time< -5||now-profile.time>90)return {state:'unknown',label:bi('Check data unavailable','Нет данных проверки')};
  if(['CHECK-001','CHECK-LIMIT'].indexOf(profile.code)>=0)return {state:'checking',label:bi('Checking','Проверяется')};
  if(profile.code)return {state:'failed',label:bi('Failed','Сбой')};
  if(profile.dns_ok===true&&profile.https_success>=2)return {state:'healthy',label:bi('Healthy','Работает')};
  return {state:'checking',label:bi('Checking','Проверяется')};
}
// Policy selection is independent of controller phase and VPN health.
function channelPathSelection(status,now,sourceId,targetId){
  status=status||{};var native=status.native_failover||{},path=status.channel_path;
  var required=native.mode==='continuous-pair'||native.proof_scope==='router-probed-ipv4'||!!(path&&(path.mode==='continuous-pair'||path.selection_proof==='fw3-kernel-marking')),authoritative=required||Object.prototype.hasOwnProperty.call(status,'channel_path');
  var result={authoritative:authoritative,selected:null,moving:false,code:authoritative?'KERNEL-POLICY-UNVERIFIED':null};
  if(!authoritative)return result;
  if(status.rpc_error||status.error){result.code='STATUS-REQUEST-FAILED';return result;}
  if(!Number.isFinite(status.time)||now-status.time< -5||now-status.time>90){result.code='MONITOR-DATA-STALE';return result;}
  if(!path||typeof path!=='object'||Array.isArray(path))return result;
  if(required&&(path.mode!=='continuous-pair'||path.selection_proof!=='fw3-kernel-marking'||!Number.isFinite(path.valid_for)||path.valid_for<=0||path.valid_for>15||!Number.isFinite(path.checked_at)||path.time!==path.checked_at))return result;
  var maxAge=required?path.valid_for:30;
  var checkedAt=required?path.checked_at:path.time;
  if(!Number.isFinite(checkedAt)||now-checkedAt< -5||now-checkedAt>maxAge){result.code=required?'KERNEL-POLICY-UNVERIFIED':'MONITOR-DATA-STALE';return result;}
  var source=path.source_profile_id,target=path.target_profile_id;
  if(typeof source!=='string'||!source||typeof target!=='string'||!target||source===target||sourceId&&source!==sourceId||targetId&&target!==targetId){result.code='PAIR-POLICY-UNVERIFIED';return result;}
  result.moving=path.transitioning===true;
  if(result.moving){result.code=null;return result;}
  if(path.confirmed!==true||required&&path.kernel_policy_verified!==true)return result;
  if(path.active_profile_id!==source&&path.active_profile_id!==target){result.code='PAIR-POLICY-UNVERIFIED';return result;}
  result.selected=path.active_profile_id;result.code=null;return result;
}
function savedTransition(entry){
  entry=entry||{};
  var fields=['from_role','from_profile_id','destination_role','destination_profile_id','route_changed','transition_completed','transition_outcome','activation_reapply','before_policy_role'];
  var present=Object.prototype.hasOwnProperty.call(entry,'transition_metadata_present')||fields.some(function(key){return Object.prototype.hasOwnProperty.call(entry,key);});
  if(!present)return {present:false};
  function role(key,idKey){var value=entry[key],identifier=entry[idKey];return (value==='source'||value==='target')&&typeof identifier==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(identifier)&&entry.source!==entry.target&&identifier===entry[value]?value:null;}
  var from=role('from_role','from_profile_id'),to=role('destination_role','destination_profile_id'),changed=entry.route_changed===true,unchanged=entry.route_changed===false;
  var outcome=['committed','restored','refused','policy-verified'].indexOf(entry.transition_outcome)>=0?entry.transition_outcome:null;
  var invalid=changed&&from&&to&&from===to||unchanged&&from&&to&&from!==to&&outcome!=='refused';
  if(invalid){from=null;to=null;}
  return {present:true,from:from,to:to,changed:changed,unchanged:unchanged,completed:entry.transition_completed===true,outcome:outcome,reapply:entry.activation_reapply===true,invalid:!!invalid};
}

function selectedProfile(status,now){
  var native=status.native_failover||{};
  var path=channelPathSelection(status,now,native.source,native.target);
  if(path.authoritative)return path.selected;
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
  var health=profileHealth(profile,routerWall());
  // The code is a link to its row in the error table (when that helper exists on the page).
  var linked=profile.code&&typeof errorCodeLink==='function'&&typeof safeCode==='function'&&safeCode(profile.code);
  return E('strong',{'class':'hv-badge hv-health-'+health.state,'title':profile.code||health.label},linked?[health.label+' · ',errorCodeLink(profile.code)]:health.label+(profile.code?' · '+profile.code:''));
}
function compareTableValues(a,b,direction){
  var unknown=function(value){return value==null||/^(?:\s*|—|No data|Нет данных)$/.test(String(value).trim());};
  if(unknown(a)!==unknown(b))return unknown(a)?1:-1;
  var x=String(a==null?'':a).trim(),y=String(b==null?'':b).trim(),nx=Number(x.replace(/%$/,'')),ny=Number(y.replace(/%$/,''));
  var result=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});
  return direction==='desc'?-result:result;
}
// Ranking trust: a handful of checks is not enough to name a leader.
function rankEnough(count){return count>=20?1:0;}
function rankConfidence(count){return count+' · '+(count>=100?bi('good','высокая'):count>=20?bi('fair','средняя'):bi('too few to rank','мало для рейтинга'));}

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
    group.servers.push({id:p.id,name:p.name||p.id,state:state,selected:p.id===selected,reason:reason,profile:p});
    if(current&&p.id!==selected&&enabled&&state==='healthy')candidates.push({id:p.id,
      tier:p.protocol!==current.protocol?2:p.channel!==current.channel?1:0,
      priority:Number.isFinite(Number(p.priority))?Number(p.priority):Infinity});
  });
  candidates.sort(function(a,b){return a.tier-b.tier||a.priority-b.priority||String(a.id).localeCompare(String(b.id));});
  groups.forEach(function(g){g.servers.sort(function(a,b){return Number(b.selected)-Number(a.selected);});});
  groups.sort(function(a,b){return Number(b.servers.some(function(s){return s.selected;}))-Number(a.servers.some(function(s){return s.selected;}));});
  return {selected:selected,groups:groups,next:candidates.length?candidates[0].id:null,fresh:fresh};
}
// What each note on a server means, in plain words. These are descriptions, not errors; real error codes are shown as links.
var CASCADE_NOTES={
  'SELECTED-BY-CONTROLLER':['Carries your traffic now.','Сейчас пропускает ваш трафик.'],
  'EDGE-NOT-CERTIFIED':['Works and could take over, but switching to it is not certified on this router yet (the LAN trial has not passed).','Работает и мог бы подхватить трафик, но переключение на него на этом роутере ещё не подтверждено (LAN-тест не пройден).'],
  'DISABLED':['Switched off in Settings, so it is not monitored and will not be used.','Выключен в «Настройках», поэтому не проверяется и использоваться не будет.'],
  'FAILED':['Failed its last check.','Не прошёл последнюю проверку.'],
  'CHECKING':['Being checked right now.','Проверяется прямо сейчас.'],
  'INACTIVE':['The VPN tunnel is not connected in GL.iNet.','VPN-туннель не подключён в GL.iNet.'],
  'UNKNOWN':['No fresh result yet.','Свежего результата пока нет.']
};
function renderCascadePath(status,inventory){
  if(typeof renderCompactCascade==='function')return renderCompactCascade(status,inventory);
  var model=cascadePathModel(status,(typeof routerWall==='function'?routerWall():Date.now()/1000));
  var rows=status.profiles||[],nextRow=rows.filter(function(p){return p.id===model.next;})[0];
  var legendKeys=[];
  var groups=model.groups.map(function(g){
    return E('section',{'class':'hv-auto-node hv-cascade-group'},[
      E('div',{'class':'hv-cascade-head'},[E('strong',{},g.protocol),E('span',{},bi('Group: ','Группа: ')+g.channel)]),
      E('ul',{'class':'hv-cascade-list'},g.servers.map(function(s){
        var p=s.profile,h=profileHealth(p,(typeof routerWall==='function'?routerWall():Date.now()/1000));
        var kind=s.state==='healthy'?'green':s.state==='checking'?'yellow':s.state==='failed'?'red':'grey';
        if(legendKeys.indexOf(s.reason)<0)legendKeys.push(s.reason);
        var note=ownGet(CASCADE_NOTES,s.reason)||CASCADE_NOTES.UNKNOWN;
        return E('li',{'class':'hv-cascade-item'+(s.selected?' hv-cascade-selected':'')},[
          E('span',{'class':'hv-check-lamp hv-check-'+kind,'role':'img','aria-label':h.label}),
          E('div',{},[
            E('div',{'class':'hv-cascade-line'},[E('b',{},serverTitle(p)),s.selected?E('span',{'class':'hv-chip-note hv-chip-now'},bi('Carries traffic','Пропускает трафик')):null,s.id===model.next?E('span',{'class':'hv-chip-note hv-chip-next'},bi('Next in line','Следующий в очереди')):null].filter(Boolean)),
            E('div',{'class':'hv-cascade-note'},[bi(note[0],note[1]),(p&&safeCode(p.code))?' ':null,(p&&safeCode(p.code))?errorCodeLink(p.code):null].filter(Boolean))])]);
      }))]);
  });
  return E('section',{'class':'hv-chart-card hv-cascade'},[
    E('h2',{},bi('Which VPN carries your traffic and which one is next','Какой VPN пропускает ваш трафик и какой следующий')),
    E('p',{},bi('If the VPN in use fails, Auto looks for a replacement in this order: first another server of the same group and protocol, then another group, and only then another VPN protocol. There is never an automatic exit straight to the provider (no VPN).','Если используемый VPN откажет, Auto ищет замену в таком порядке: сначала другой сервер той же группы и протокола, потом другая группа и только затем другой протокол VPN. Автоматического выхода напрямую к провайдеру (без VPN) никогда не бывает.')),
    E('p',{'class':'hv-cascade-next'},[E('strong',{},bi('Next in line: ','Следующий в очереди: ')),nextRow?serverTitle(nextRow):bi('nobody yet (no other working VPN)','пока никого (нет другого работающего VPN)'),bi('. This only shows who would be chosen; it does not switch anything.','. Это лишь показывает, кого выберут; ничего не переключается.')]),
    E('div',{'class':'hv-cascade-grid'},groups),
    E('details',{'class':'hv-cascade-legend'},[E('summary',{},bi('What the notes mean','Что означают пометки')),E('ul',{},legendKeys.map(function(k){var n=ownGet(CASCADE_NOTES,k)||CASCADE_NOTES.UNKNOWN;return E('li',{},[E('b',{},bi(n[0],n[1]))]);}).concat([E('li',{},bi('A code such as DNS-001 next to a server is a real error: press it to read what it means and how to fix it.','Код вроде DNS-001 рядом с сервером — настоящая ошибка: нажмите на него, чтобы прочитать, что он значит и как исправить.'))]))])
  ]);
}
function retainedTransitions(history){
  var events=(history.events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}),rows=[],open=null,last=null,lastTime=null;
  function close(outcome,event,reason){if(!open)return;open.outcome=outcome;open.close_reason=reason||null;open.terminal_state=event&&event.state||null;
    if(event&&Number.isFinite(event.time)&&event.time>=open.start){open.end=event.time;open.duration=open.applied_at==null?null:event.time-open.applied_at;}
    rows.push(open);open=null;
  }
  function identifier(value){return Number.isSafeInteger(value)&&value>0?value:null;}
  function begin(e){var transition=savedTransition(e);open={id:identifier(e.attempt_id)||e.sequence,retry_episode_id:identifier(e.retry_episode_id),
    prepared_at:e.state==='ARMED'?e.time:null,applied_at:e.state==='APPLYING'?e.time:null,start:e.time,end:null,duration:null,
    pair_source:e.source||'unknown',pair_target:e.target||'unknown',
    source:transition.present?(transition.from?e[transition.from]:'unknown'):e.source||'unknown',target:transition.present?(transition.to?e[transition.to]:'unknown'):e.target||'unknown',
    source_role:transition.present?transition.from:'source',target_role:transition.present?transition.to:'target',transition_metadata_present:transition.present,
    kind:['server','channel','protocol'].indexOf(e.transition_kind)>=0?e.transition_kind:'unknown',
    trial:e.trial===true,outcome:'pending',phases:[],codes:[],probe_evidence:{}};}
  events.forEach(function(e){
    if(!Number.isFinite(e.time)||e.time<0||e.time>253402300799||!Number.isSafeInteger(e.sequence)||e.sequence<1)return;
    if(last!==null&&e.sequence<=last)return;
    if(lastTime!==null&&e.time<lastTime){close('unknown',null,'clock-order');last=e.sequence;return;}
    lastTime=e.time;
    if(last!==null&&e.sequence!==last+1)close('unknown',null,'missing-events');
    last=e.sequence;
    var transition=savedTransition(e),refused=transition.present&&transition.completed&&transition.outcome==='refused';
    if(transition.present&&(!transition.changed||transition.unchanged||transition.reapply)&&!refused)return;
    var restoration=transition.present&&transition.completed&&transition.outcome==='restored';
    if(restoration&&(!open||identifier(e.attempt_id)&&e.attempt_id!==open.id||e.source&&e.source!==open.pair_source||e.target&&e.target!==open.pair_target)){
      close('unknown',null,'next-operation');begin(e);open.operation='restoration';open.applied_at=null;
    }
    var trialPassed=(e.codes||[]).indexOf('TRIAL-PASSED')>=0;
    var starting=e.state==='APPLYING'||e.state==='ARMED'&&!trialPassed;
    if(starting){
      var same=open&&open.applied_at==null&&(e.state==='APPLYING'||!identifier(e.attempt_id)||identifier(e.attempt_id)===open.id)&&
        (!e.attempt_id||e.attempt_id===open.id)&&(!e.source||e.source===open.pair_source)&&(!e.target||e.target===open.pair_target);
      if(!same){close('unknown',null,'next-attempt');begin(e);}
      else if(e.state==='APPLYING'){open.applied_at=e.time;open.start=e.time;if(['server','channel','protocol'].indexOf(e.transition_kind)>=0)open.kind=e.transition_kind;}
    }
    if(!open)return;
    if(e.trial===true)open.trial=true;
    if((identifier(e.attempt_id)&&e.attempt_id!==open.id)||(e.source&&e.source!==open.pair_source)||(e.target&&e.target!==open.pair_target)){close('unknown',null,'pair-changed');return;}
    open.phases.push({state:e.state,time:e.time});
    (e.codes||[]).forEach(function(code){if(typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)&&open.codes.indexOf(code)<0)open.codes.push(code);});
    var evidence=e.probe_evidence||{};
    ['source_streak_met','reserve_streak_met'].forEach(function(key){if(typeof evidence[key]==='boolean')open.probe_evidence[key]=evidence[key];});
    ['required_failures','required_successes'].forEach(function(key){if(Number.isInteger(evidence[key])&&evidence[key]>=2&&evidence[key]<=10)open.probe_evidence[key]=evidence[key];});
    if(Array.isArray(e.phase_evidence)){
      var phases=e.phase_evidence.filter(function(p){return p&&/^[A-Z0-9_-]{1,96}$/.test(p.phase)&&Number.isFinite(p.time)&&p.time<=e.time;});
      if(phases.length){open.phases=phases.map(function(p){return {state:p.phase,time:p.time};});if(open.phases[open.phases.length-1].state!==e.state)open.phases.push({state:e.state,time:e.time});}
    }
    if(transition.present&&transition.completed){
      if(transition.outcome==='committed'&&transition.to)close('committed',e);
      else if(transition.outcome==='restored'&&transition.to)close(open.operation==='restoration'?'restored':'rolled_back',e);
      else if(transition.outcome==='refused')close('refused',e);
      else close('unknown',e,'metadata-unverified');
    }
    else if(!transition.present&&e.state==='COMMITTED')close('committed',e);
    else if(!transition.present&&trialPassed)close('trial_passed',e);
    else if(!transition.present&&e.state==='ROLLED-BACK')close('rolled_back',e);
    else if(!transition.present&&['BLOCKED','STOPPED','STOPPED-ON-RESERVE','EXPIRED'].indexOf(e.state)>=0)close('held',e);
  });
  close('pending',null);
  return rows;
}

function recoverySummary(rows,start,end){
  var selected=rows.filter(function(r){return r.start>=start&&r.start<end&&r.operation!=='restoration';}),durations=[],known=0,committed=0,trialsPassed=0;
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
function recoveryPreparation(row){return row.operation!=='restoration'&&row.applied_at==null&&(!row.source||row.source==='unknown'||!row.target||row.target==='unknown');}
function recoveryOutcomeText(row){
  if(recoveryPreparation(row))return row.close_reason==='next-attempt'?bi('Preparation ended; a new attempt followed','Подготовка завершена; началась новая попытка'):row.close_reason?bi('Preparation record interrupted','Запись подготовки прервана'):bi('Waiting for the VPN pair and checks','Ожидание пары VPN и проверок');
  if(row.outcome==='committed')return row.transition_metadata_present?bi('Channel selection confirmed','Выбор канала подтверждён'):bi('Switch confirmed','Переключение подтверждено');
  if(row.outcome==='refused')return bi('Request refused; no switch confirmed','Запрос отклонён; переключение не подтверждено');
  if(row.outcome==='restored')return bi('VPN rule restoration confirmed','Восстановление правил VPN подтверждено');
  if(row.outcome==='trial_passed')return bi('Test passed; original channel restored','Тест пройден; исходный канал восстановлен');
  if(row.outcome==='rolled_back')return row.transition_metadata_present?bi('VPN rule restoration confirmed','Восстановление правил VPN подтверждено'):bi('Returned to the original channel','Возврат на исходный канал');
  if(row.outcome==='held')return row.terminal_state==='STOPPED-ON-RESERVE'?bi('Reserve retained after Stop','После остановки оставлен резерв'):row.terminal_state==='BLOCKED'?bi('Switch blocked','Переключение заблокировано'):row.terminal_state==='EXPIRED'?bi('Attempt expired','Срок попытки истёк'):bi('Attempt stopped','Попытка остановлена');
  if(row.outcome==='pending')return bi('Awaiting completion confirmation','Ожидается подтверждение завершения');
  var reasons={'missing-events':['Result not recorded: missing history events','Результат не записан: пропуск событий истории'],'pair-changed':['Record interrupted by a VPN pair change','Запись прервана сменой пары VPN'],'clock-order':['Record interrupted by clock order mismatch','Запись прервана нарушением порядка времени'],'next-attempt':['Completion not recorded before the next attempt','Завершение не записано до следующей попытки']},reason=reasons[row.close_reason];
  return reason?bi(reason[0],reason[1]):bi('Completion absent from saved history','В сохранённой истории нет завершения');
}
function recoveryChannelText(row,key,profiles,inventory){
  var id=row[key];if(!id||id==='unknown')return recoveryPreparation(row)?bi('Pair not selected during preparation','На этапе подготовки пара ещё не выбрана'):bi('Channel profile absent from event','Профиль канала не записан в событии');
  var identity=recoveryIdentity(id,profiles,inventory);
  var channel=recoveryEventRole(row,key)||(identity.channel===bi('Channel not recorded','Канал не записан')?(key==='source'?bi('Original channel','Исходный канал'):bi('Destination channel','Канал назначения')):identity.channel);
  return channel+' · '+identity.server;
}
function recoveryEventRole(row,key){
  if(row.transition_metadata_present){var role=row[key+'_role'];return role==='source'?bi('Primary channel','Основной канал'):role==='target'?bi('Reserve channel','Резервный канал'):null;}
  var valid=function(id){return typeof id==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(id);};
  if(!valid(row.source)||!valid(row.target)||row.source===row.target)return null;
  return key==='source'?bi('Primary channel','Основной канал'):key==='target'?bi('Reserve channel','Резервный канал'):null;
}
function recoveryIdentity(identifier,profiles,inventory){
  profiles=Array.isArray(profiles)?profiles:[];
  var valid=typeof identifier==='string'&&identifier!=='unknown'&&identifier!=='default',p=valid?profiles.find(function(p){return p.id===identifier;}):null;
  var configured=((inventory||{}).profiles||[]);if(!Array.isArray(configured))configured=[];
  if(!p&&valid)p=configured.find(function(p){return p.id===identifier;});p=p||{};
  function meaningful(value){return typeof value==='string'&&value.trim()&&['unknown','default','null','undefined'].indexOf(value.trim().toLowerCase())<0;}
  var protocol=valid&&identifier.indexOf('openvpn:')===0?'openvpn':valid&&identifier.indexOf('wireguard:')===0?'wireguard':p.protocol==='openvpn'||p.protocol==='wireguard'?p.protocol:null;
  var protocolName=protocol==='openvpn'?'OpenVPN':protocol==='wireguard'?'WireGuard':bi('Protocol not recorded','Протокол не записан');
  var name=meaningful(p.router_name)?p.router_name:meaningful(p.name)&&p.name!==identifier?p.name:null;
  var server=name?name+' · '+protocolName+' · '+bi('current profile','текущий профиль'):valid?bi('Archived profile: ','Архивный профиль: ')+identifier+' · '+protocolName:bi('Server not recorded in event','Сервер не записан в событии');
  if(name&&typeof endpointText==='function'){var endpoint=endpointText(p,(typeof routerWall==='function'?routerWall():Date.now()/1000));if(endpoint!==bi('Server address: not observed','Адрес сервера: не получен'))server+=' · '+endpoint;}
  var settings=(inventory||{}).settings||{},role=valid&&identifier===settings.plan_source?bi('Primary channel (current pair)','Основной канал (текущая пара)'):valid&&identifier===settings.plan_target?bi('Reserve channel (current pair)','Резервный канал (текущая пара)'):meaningful(p.channel)?bi('Current group: ','Текущая группа: ')+p.channel:bi('Channel not recorded','Канал не записан');
  return {server:server,channel:role,protocol:protocolName};
}
function recoveryGroups(rows,profiles,start,end,inventory){
  var result={server:{},channel:{},protocol:{}};
  rows.filter(function(row){return row.start>=start&&row.start<end;}).forEach(function(row){var identity=recoveryIdentity(row.target,profiles,inventory);
    var role=recoveryEventRole(row,'target');if(role){identity.server=role+' · '+identity.server;identity.channel=role;identity.protocol=role+' · '+identity.protocol;}
    [['server',identity.server],['channel',identity.channel],['protocol',identity.protocol]].forEach(function(pair){
      var key='group:'+pair[1];if(!result[pair[0]][key])result[pair[0]][key]={name:pair[1],rows:[]};result[pair[0]][key].rows.push(row);
    });
  });
  Object.keys(result).forEach(function(kind){result[kind]=Object.keys(result[kind]).map(function(key){var g=result[kind][key];return {name:g.name,metrics:recoverySummary(g.rows,start,end)};});});
  return result;
}
function recoveryTableWrap(table){return E('div',{'class':'hv-recovery-scroll'},table);}
var exportSchemas={
  ranking:['server','name','protocol','channel','latency_ms','state'],
  traffic:['month','rx_bytes','tx_bytes','scope'],
  failures:['start_utc','source','target','source_role','target_role','outcome','codes','attempt_id','retry_episode_id'],
  transitions:['start_utc','source','target','source_role','target_role','kind','outcome','duration_seconds','trial','attempt_id','retry_episode_id','source_streak_met','reserve_streak_met','required_failures','required_successes']
};
function analyticsCSV(kind,rows){
  var columns=exportSchemas[kind];if(!columns)throw new Error('EXPORT-KIND');
  function cell(value){var text=value==null?'':String(value);
    if(/^[\s\u0000-\u001f\u007f\ufeff\u200b-\u200f\u202a-\u202e\u2060-\u206f]*[=+@-]/.test(text)||/^[\t\r\n]/.test(text))text="'"+text;
    return '"'+text.replace(/"/g,'""')+'"';}
  return '\ufeff'+[columns.map(cell).join(',')].concat(rows.map(function(row){return columns.map(function(key){return cell(row[key]);}).join(',');})).join('\r\n')+'\r\n';
}
function analyticsExportRows(kind,status,transitions){
  if(kind==='ranking')return (status.profiles||[]).map(function(p){return {server:p.id,name:p.name,protocol:p.protocol,channel:p.role==='source'?'primary':p.role==='target'?'reserve':p.channel,
    latency_ms:p.rtt_ms,state:status.rpc_error?'unknown':profileHealth(p,(typeof routerWall==='function'?routerWall():Date.now()/1000)).state};});
  if(kind==='traffic')return Object.keys((status.accounting||{}).months||{}).sort().map(function(month){var r=status.accounting.months[month];return {month:month,rx_bytes:r.rx,tx_bytes:r.tx,scope:'Observed interface counters; partial collection; overhead included'};});
  var rows=kind==='failures'?transitions.filter(function(r){return ['rolled_back','held'].indexOf(r.outcome)>=0;}):transitions;
  return rows.map(function(r){return {start_utc:new Date(r.start*1000).toISOString(),source:r.source,target:r.target,kind:r.kind,
    source_role:recoveryEventRole(r,'source')?(r.transition_metadata_present?(r.source_role==='source'?'primary':'reserve'):'primary'):null,target_role:recoveryEventRole(r,'target')?(r.transition_metadata_present?(r.target_role==='source'?'primary':'reserve'):'reserve'):null,
    outcome:r.outcome,duration_seconds:r.duration,trial:r.trial,codes:r.codes.join(' | '),attempt_id:r.id,retry_episode_id:r.retry_episode_id,
    source_streak_met:r.probe_evidence.source_streak_met,reserve_streak_met:r.probe_evidence.reserve_streak_met,
    required_failures:r.probe_evidence.required_failures,required_successes:r.probe_evidence.required_successes};});
}
var recoveryAnalyticsPeriod='day';
try {var savedRecoveryPeriod=localStorage.getItem('homensai-vpn-recovery-period');if(['day','week','month'].indexOf(savedRecoveryPeriod)>=0)recoveryAnalyticsPeriod=savedRecoveryPeriod;}catch(error){}
function controllerTransitionMarks(events){
  var marks=Object.create(null),committed=Object.create(null),attempted=Object.create(null),returned=Object.create(null);
  (events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}).forEach(function(event){
    var id=event.attempt_id||event.sequence;
    if(event.trial)return;
    var transition=savedTransition(event);
    if(transition.present){
      if(!transition.to||!transition.changed||transition.unchanged||transition.reapply||transition.outcome==='refused')return;
      var forward=transition.from==='source'?1:transition.from==='target'?2:null,destination=transition.to==='source'?1:2;
      if(transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0){var terminal=id+':'+transition.outcome+':'+transition.to;if(!committed[terminal]){committed[terminal]=true;marks[event.sequence]={from:forward,to:destination,confirmed:true};}}
      else if(!transition.completed&&['APPLYING','RESTORING'].indexOf(event.state)>=0){var pending=id+':'+event.state+':'+transition.to;if(!attempted[pending]){attempted[pending]=true;marks[event.sequence]={from:forward,to:destination,confirmed:false};}}
      return;
    }
    if(event.state==='APPLYING'&&!attempted[id]){attempted[id]=true;marks[event.sequence]={from:1,to:2,confirmed:false};}
    if(event.state==='COMMITTED'&&!committed[id]){committed[id]=true;marks[event.sequence]={from:1,to:2,confirmed:true};}
    if(event.state==='ROLLED-BACK'&&event.original_restored===true&&committed[id]&&!returned[id]){returned[id]=true;marks[event.sequence]={from:2,to:1,confirmed:true};}
  });
  return marks;
}
function renderTransitionBadge(event,marks){
  var mark=marks[event.sequence];if(!mark)return null;
  if(typeof renderChannelBadge==='function')return renderChannelBadge({phase:mark.confirmed?'confirmed':'pending',from:mark.from==null?null:mark.from===1?'source':'target',to:mark.to===1?'source':'target'});
  var label=(mark.confirmed?bi('Confirmed switch: ','Подтверждённый переход: '):bi('Switch attempt: ','Попытка перехода: '))+(mark.from==null?'?':mark.from)+' → '+mark.to;
  return E('span',{'class':'hv-transition-badge'+(mark.confirmed?'':' hv-transition-pending'),'aria-label':label,'title':label},[
    E('span',{'class':'hv-transition-from','aria-hidden':'true'},String(mark.from)),E('span',{'aria-hidden':'true'},'→'),E('span',{'class':'hv-transition-to','aria-hidden':'true'},String(mark.to))]);
}
function storedStatisticsRows(status){
  var history=status.native_history||{},health=(status.accounting||{}).reliability||{};
  var months=Array.from(new Set(Object.keys(history.months||{}).concat(Object.keys(health.months||{})))).sort().reverse();
  function row(period,checks,control){return {period:period,outages:checks.outages,failed_checks:checks.failed_checks,
    attempts:control.attempts,switches:control.committed,automatic:control.automatic_committed,manual:control.manual_committed,returns:control.returns,
    auto_seconds:checks.auto_observed_seconds};}
  return [row(bi('All recorded time','За всё время записи'),health.totals||{},history.totals||{}),
    row(bi('Retained detailed period','Сохранённый подробный период'),health.weekly||{},history.weekly||{})].concat(months.map(function(month){
      return row(month,(health.months||{})[month]||{},(history.months||{})[month]||{});
    }));
}
async function fetchStoredStatistics(kind,call){
  var after=0,until=0,events=[],summary=null,asOf=null,notice=null;
  for(var page=0;page<101;page++){
    var response=await call(kind,after,until);
    if(!response||response.kind!==kind||!Array.isArray(response.events)||response.events.length>100||
       !Number.isSafeInteger(response.until)||response.until<0||typeof response.has_more!=='boolean')throw new Error('STATISTICS-REPLY');
    if(summary===null){summary=response.summary;until=response.until;asOf=response.as_of;}
    if(response.until!==until||!Number.isSafeInteger(response.next_after)||response.next_after<after||response.next_after>until)throw new Error('STATISTICS-CURSOR');
    var previous=after;
    response.events.forEach(function(event){if(!Number.isSafeInteger(event.sequence)||event.sequence<=previous||event.sequence>until)throw new Error('STATISTICS-SEQUENCE');previous=event.sequence;});
    if(response.events.length&&response.next_after!==previous)throw new Error('STATISTICS-CURSOR');
    events=events.concat(response.events);if(response.storage_notice)notice=response.storage_notice;
    if(!response.has_more)return {kind:kind,as_of:asOf,detail_days:7,summary:summary,events:events,storage_notice:notice};
    if(response.next_after<=after)throw new Error('STATISTICS-CURSOR');after=response.next_after;
  }
  throw new Error('STATISTICS-PAGE-LIMIT');
}
function renderStoredStatistics(status){
  var history=status.native_history||{},health=(status.accounting||{}).reliability||{},rows=storedStatisticsRows(status);
  var headings=[bi('Period','Период'),bi('Outages','Эпизоды отказа'),bi('Failed checks','Неудачные проверки'),
    bi('Attempts','Попытки'),bi('Confirmed switches','Подтверждённые переключения'),bi('Automatic','Автоматические'),bi('Manual','Ручные'),bi('Returns since update','Возвраты с обновления'),bi('Auto observed, hours','Наблюдение Auto, часов')];
  var table=E('table',{'class':'table hv-recovery-table hv-recovery-counters'},[E('tr',{},headings.map(function(label){return E('th',{'scope':'col'},label);}))].concat(rows.map(function(row){
    var values=[row.period,row.outages,row.failed_checks,row.attempts,row.switches,row.automatic,row.manual,row.returns,
      Number.isFinite(row.auto_seconds)?(row.auto_seconds/3600).toFixed(2):null];
    return E('tr',{},values.map(function(value){return E('td',{},value==null?'—':String(value));}));
  })));
  var note=E('p'),button=E('button',{'type':'button','class':'cbi-button','click':async function(){
    button.disabled=true;note.textContent=bi('Reading saved weekly detail…','Чтение сохранённых событий недели…');
    try{
      var call=rpc.declare({object:'homensai-vpn',method:'statistics',params:['kind','after','until'],expect:{}});
      var failures=await fetchStoredStatistics('failures',call),controller=await fetchStoredStatistics('controller',call);
      var data={schema:1,failures:failures,controller:controller};
      var url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json;charset=utf-8'}));
      var link=document.createElement('a');link.href=url;link.download='homensai-vpn-week-and-months.json';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
      note.textContent=bi('Saved detail downloaded. Unobserved intervals remain unknown.','Сохранённые события выгружены. Интервалы без наблюдений остаются неизвестными.');
    }catch(error){note.textContent=bi('Statistics could not be read. Try again; counters were not reset.','Не удалось прочитать статистику. Повторите выгрузку; счётчики не сброшены.');}
    finally{button.disabled=false;}
  }},bi('Download weekly detail and monthly summaries (JSON)','Скачать подробности недели и сводки по месяцам (JSON)'));
  return E('section',{'class':'hv-chart-card','data-stats-reset':'auto'},[E('h3',{},bi('Saved outage and switching statistics','Сохранённая статистика сбоев и переключений')),
    E('p',{},bi('Detailed incidents: configured retention of 1–7 days. Monthly and lifetime counters survive detail expiry and service restart. A repeated status of one transaction is counted once. Missing data is shown as —.','Подробные события: выбранный срок хранения 1–7 дней. Месячные и общие счётчики сохраняются после удаления старых подробностей и перезапуска службы. Повторные статусы одной транзакции считаются один раз. Нет данных — прочерк.')),
    E('p',{},bi('Outages are observed failure episodes; several failed probes may belong to one outage. Auto time includes only observed intervals. Old missing events and outage durations are not reconstructed.','Сбой — наблюдаемый эпизод отказа; в нём может быть несколько неудачных проверок. Время Auto включает только наблюдавшиеся интервалы. Утраченные старые события и длительность сбоев не восстанавливаются.')),
    E('p',{},bi('Counter coverage: ','Покрытие счётчиков: ')+(history.counter_accuracy||bi('No saved controller counters','Нет сохранённых счётчиков контроллера'))),
    (health.details_dropped||history.detail_budget_dropped)?E('p',{'role':'status'},bi('Detail storage limit was reached; aggregate counters are retained.','Достигнут предел подробных событий; сводные счётчики сохранены.')):null,
    E('div',{'class':'hv-dv-tablewrap'},[table]),button,note].filter(Boolean));
}
function renderTransitionAnalytics(status,inventory){
  var history=status.native_history||{},allRows=retainedTransitions(history),preparations=allRows.filter(recoveryPreparation),rows=allRows.filter(function(r){return !recoveryPreparation(r);}),now=Date.now()/1000;
  var summaryHost=E('div',{'class':'hv-recovery-scroll'}),groupHost=E('div',{'class':'hv-recovery-scroll'}),period=E('select',{'aria-label':bi('Recovery period','Период восстановления')},[
    E('option',{'value':'day'},bi('Day','Сутки')),E('option',{'value':'week'},bi('Week','Неделя')),E('option',{'value':'month'},bi('Month','Месяц'))]);
  var selectedRows=rows,table;
  period.value=recoveryAnalyticsPeriod;
  function update(){var window;
    try {window=recoveryWindow(period.value||'day',now,history.timezone||'Europe/Berlin');}
    catch(error){summaryHost.textContent='RECOVERY-TIMEZONE-UNKNOWN: metrics unavailable';return;}
    var s=recoverySummary(rows,window.start,window.end);
    selectedRows=rows.filter(function(r){return r.start>=window.start&&r.start<window.end;});
    if(table)table.querySelectorAll('tr[data-recovery-start]').forEach(function(row){var at=Number(row.getAttribute('data-recovery-start'));row.hidden=!(at>=window.start&&at<window.end);});
    var fmt=function(v){return v==null?'—':v.toFixed(1);};
    while(summaryHost.firstChild)summaryHost.removeChild(summaryHost.firstChild);
    summaryHost.appendChild(E('table',{'class':'table hv-recovery-table'},[
      E('tr',{'class':'tr table-titles'},[E('th',{'scope':'col'},bi('Measure','Показатель')),E('th',{'scope':'col'},bi('Value','Значение'))]),
      [[bi('Attempts','Попытки'),s.attempts],
       [bi('Known outcome','Известный результат'),s.known_outcomes],
       [bi('No result','Без итога'),s.unknown_or_pending],
       [bi('Trial attempts','Тестовые попытки'),s.trial_attempts],
       [bi('Automatic attempts','Автоматические попытки'),s.automatic_attempts],
       [bi('Verified outcome ratio (including trials)','Доля подтверждённых результатов (включая тесты)'),s.success_ratio==null?'—':(s.success_ratio*100).toFixed(1)+'%'],
       [bi('Recovery time, median (s)','Время восстановления, медиана (с)'),fmt(s.median)],
       [bi('Recovery time, P95 (s)','Время восстановления, P95 (с)'),fmt(s.p95)],
       [bi('Recovery time, worst (s)','Время восстановления, максимум (с)'),fmt(s.worst)]].map(function(r){return E('tr',{'class':'tr'},[E('td',{'class':'td'},r[0]),E('td',{'class':'td'},String(r[1]))]);})].reduce(function(a,b){return a.concat(b);},[])));
    while(groupHost.firstChild)groupHost.removeChild(groupHost.firstChild);
    var groups=recoveryGroups(rows,status.profiles||[],window.start,window.end,inventory);
    var kindTitle={server:bi('By server','По серверам'),channel:bi('By group (channel)','По группам (каналам)'),protocol:bi('By protocol','По протоколам')};
    Object.keys(groups).forEach(function(kind){
      if(!groups[kind].length)return;
      groupHost.appendChild(E('h4',{},ownGet(kindTitle,kind)||kind));
      groupHost.appendChild(E('table',{'class':'table hv-recovery-table'},[E('tr',{'class':'tr table-titles'},[kind==='server'?bi('VPN server / protocol','VPN-сервер / протокол'):kind==='channel'?bi('Channel','Канал'):bi('Protocol','Протокол'),bi('Successful / known','Удачных / известных'),bi('P95, s','P95, с'),bi('Failures in a row','Сбоев подряд')].map(function(t){return E('th',{'scope':'col'},t);}))].concat(groups[kind].map(function(g){var m=g.metrics;
        return E('tr',{'class':'tr'},[E('td',{'class':'td hv-recovery-identity'},g.name),E('td',{'class':'td'},(m.committed+m.trials_passed)+' / '+m.known_outcomes),E('td',{'class':'td'},m.p95==null?'—':m.p95.toFixed(1)),E('td',{'class':'td'},String(m.max_consecutive_failures))]);}))));
    });
    groupHost.appendChild(E('div',{'class':'hv-recovery-legend'},[E('strong',{},bi('How to read these tables','Как читать эти таблицы')),E('p',{},bi('There is one table per kind of grouping (server, group of servers, protocol). Example row: b · 1 / 1 · 5.0 · 0.','Для каждого вида группировки своя таблица (сервер, группа серверов, протокол). Пример строки: b · 1 / 1 · 5.0 · 0.')),
      E('ul',{},[
        E('li',{},bi('Name (b, Main, openvpn): the server, the group (channel) or the protocol these numbers belong to.','Имя (b, Main, openvpn): сервер, группа (канал) или протокол, к которым относятся цифры.')),
        E('li',{},bi('1/1: successful switches / switches whose result is known. 1/1 = every known switch to it succeeded; 0/1 = the only known switch failed; 1/2 = one of two worked. Pending or unknown results are not counted.','1/1: удачные переключения / переключения с известным результатом. 1/1 — все известные переключения на него удались; 0/1 — единственное известное не удалось; 1/2 — одно из двух удалось. Ожидающие и неизвестные результаты не считаются.')),
        E('li',{},bi('P95 5.0 s: 95 % of recoveries on this server took no longer than 5 seconds (the slowest 5 % are excluded). “—” means no timing yet. Smaller is better.','P95 5.0 с: 95 % восстановлений на этом сервере заняли не больше 5 секунд (самые медленные 5 % не учитываются). «—» — времени ещё нет. Чем меньше, тем лучше.')),
        E('li',{},bi('Consecutive failures: the longest run of failed attempts one after another in the chosen period. 0 = none; 1 = one failure, 2 or more = the server repeatedly failed to take over and deserves attention.','Сбоев подряд: самая длинная серия неудачных попыток подряд за выбранный период. 0 — не было; 1 — одна неудача; 2 и больше — сервер несколько раз подряд не смог принять трафик, на него стоит обратить внимание.'))]),
      E('p',{},bi('Example: “d · 0/1 · P95 8.0 s · consecutive failures: 1” = the only known switch to d failed (took 8 s), so d is a weak reserve for now; “b · 1/1” is a reliable one.','Пример: «d · 0/1 · P95 8.0 с · сбоев подряд: 1» — единственное известное переключение на d не удалось (8 с), значит d пока слабый резерв; «b · 1/1» — надёжный.'))]));
  }
  period.addEventListener('change',function(){recoveryAnalyticsPeriod=period.value;try{localStorage.setItem('homensai-vpn-recovery-period',recoveryAnalyticsPeriod);}catch(error){}update();});update();
  var exports=E('div',{'class':'hv-wizard-launch'},Object.keys(exportSchemas).map(function(kind){return E('button',{'type':'button','class':'cbi-button','click':function(){
    var text=analyticsCSV(kind,analyticsExportRows(kind,status,selectedRows)),url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
    var link=document.createElement('a');link.href=url;link.download='homensai-vpn-'+kind+'.csv';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
  }},'CSV · '+kind);}));
  exports.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){downloadIncidentReport(selectedRows);}},bi('Printable incident report','Отчёт об инцидентах для печати')));
  function stamp(t){return new Date(t*1000).toISOString().replace('T',' ').replace(/\.[0-9]+Z$/,'');}
  table=E('table',{'class':'table hv-recovery-table'},[E('tr',{},[bi('Time (UTC)','Время (UTC)'),'№',bi('Original channel','Исходный канал'),bi('Destination channel','Канал назначения'),bi('Outcome','Итог'),bi('Seconds','Секунд'),bi('Stages','Этапы'),bi('Codes','Коды'),''].map(function(h){return E('th',{'scope':'col'},h);}))]);
  rows.forEach(function(r){
    var detail=E('button',{'type':'button','class':'cbi-button','click':function(){showIncident(r,status,inventory);}},bi('Details','Подробности'));
    var evidence=r.probe_evidence&&typeof r.probe_evidence==='object'&&Object.keys(r.probe_evidence).length?' · '+Object.keys(r.probe_evidence).map(function(k){return k+'='+String(r.probe_evidence[k]);}).join(', '):'';
    table.appendChild(E('tr',{'data-recovery-start':String(r.start)},[stamp(r.start),String(r.id),recoveryChannelText(r,'source',status.profiles||[],inventory),recoveryChannelText(r,'target',status.profiles||[],inventory),recoveryOutcomeText(r),r.duration==null?'—':r.duration.toFixed(1),
      r.phases.map(function(p){return p.state;}).join(' → ')||'—',(r.codes.join(' · ')||'—')+evidence].map(function(v){return E('td',{},v);}).concat([E('td',{},detail)])));
  });
  update();
  var stamps=(history.events||[]).map(function(e){return e.time;}).filter(function(at){return Number.isFinite(at)&&at>=0&&at<=253402300799;});
  var latest=stamps.length?Math.max.apply(null,stamps):null;
  var age=latest==null?bi('No retained event timestamp','Нет сохранённых отметок времени событий'):latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' '+bi('s since the latest retained event','с прошло с последнего сохранённого события');
  return E('section',{'class':'hv-chart-card','data-stats-reset':'auto'},[E('h2',{},bi('Transition evidence and recovery','Подтверждения переходов и восстановления')),
    E('p',{},bi('Based only on the events the router kept. Gaps are shown as unknown, never guessed.','Основано только на событиях, которые сохранил роутер. Пропуски показываются как неизвестные, а не угадываются.')),
    E('p',{},bi('Not all history for this period was saved.','Сохранена не вся история за этот период.')),
    E('p',{},age),
    E('p',{'class':'hv-ready-intro'},bi('Calendar boundaries: ','Границы дней: ')+(history.timezone||'Europe/Berlin')+bi('. Event times are in UTC. Durations are measured from the retained APPLYING event to the event that confirmed the outcome, not the full outage. Retry episode numbers describe what the controller saw, not certified LAN outages. Categories overlap and must not be added up.','. Время событий указано в UTC. Длительность считается от сохранённого события APPLYING до события, подтвердившего результат, а не как полный простой. Номера повторных эпизодов описывают то, что видел контроллер, а не подтверждённые сбои LAN. Категории пересекаются, их нельзя суммировать.')),
    renderStoredStatistics(status),period,summaryHost,groupHost,E('p',{'class':'hv-muted'},bi('Names and channel roles marked current refer to today’s saved profiles. Older events without a profile cannot be assigned a server.','Названия и роли с пометкой «текущий» относятся к сохранённым сейчас профилям. Старым событиям без профиля нельзя достоверно назначить сервер.')),exports,recoveryTableWrap(table),preparations.length?E('details',{'class':'hv-recovery-preparations'},[E('summary',{},bi('Preparation before channel selection','Подготовка до выбора каналов')+' ('+preparations.length+')'),E('p',{},bi('No route application was recorded for these entries. They are separate from the switch-attempt table.','Для этих записей не зафиксировано применение маршрута. Они вынесены отдельно от таблицы попыток переключения.')),E('ul',{},preparations.map(function(r){return E('li',{},stamp(r.start)+' · '+recoveryOutcomeText(r)+' · '+r.codes.join(' · '));}))]):null].filter(Boolean));
}

function renderDecisionExplanation(status,inventory){
  status=status||{};inventory=inventory||{};
  var explanation=status.decision_explanation||{},diagnosis=explanation.diagnosis||{},native=status.native_failover||{},settings=inventory.settings||{};
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var interval=Number(settings.interval),age=Number.isInteger(interval)&&interval>=10&&interval<=300?Math.max(30,interval*3):90;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=0&&now-status.time<=age;
  var nativeFresh=fresh&&Number.isFinite(native.time)&&now-native.time>=0&&now-native.time<=30;
  var vendor=typeof vendorDiagnosticsModel==='function'?vendorDiagnosticsModel(status,inventory,now):null;
  // What the router sees on the VPN in use, in plain words, with a lamp colour.
  var seen={
    'VPN-PROBE-HEALTHY':['green','The VPN in use works: the router opened a website and looked up a name through it.','VPN в использовании работает: роутер открыл сайт и нашёл адрес через него.'],
    'DNS-FAILED':['red','The VPN is connected, but name lookup (DNS) through it fails.','VPN подключён, но поиск адресов (DNS) через него не работает.'],
    'HTTPS-FAILED':['red','The VPN is connected, but websites do not open through it.','VPN подключён, но сайты через него не открываются.'],
    'TUNNEL-DISCONNECTED':['red','The VPN tunnel is not connected.','VPN-туннель не подключён.'],
    'ROUTE-MISMATCH':['red','The check did not go through this VPN (the route does not match), so it proves nothing.','Проверка шла не через этот VPN (маршрут не совпал), поэтому она ничего не доказывает.'],
    'PATH-UNVERIFIED':['yellow','The router has not yet confirmed which way its check went.','Роутер ещё не подтвердил, каким путём прошла его проверка.'],
    'UPLINK-LINK-DOWN':['red','The configured uplink reports link down. This does not establish why the router firmware changed a profile.','Настроенный uplink сообщает об отключении. Это не устанавливает причину смены профиля штатной прошивкой.'],
    'OBSERVATION-STALE':['grey','The measurements are too old to decide anything.','Измерения слишком старые, чтобы что-то решать.'],
    'OBSERVATION-UNKNOWN':['grey','There are not enough measurements yet.','Измерений пока недостаточно.']
  };
  var row=ownGet(seen,diagnosis.code)||seen['OBSERVATION-UNKNOWN'];if(!fresh)row=['grey','The router sends no fresh data right now.','Роутер сейчас не присылает свежих данных.'];
  var selectedPath=channelPathSelection(status,now,native.source,native.target);
  if(selectedPath.authoritative){
    var selectedRow=(status.profiles||[]).find(function(profile){return profile.id===selectedPath.selected;}),health=selectedRow?profileHealth(selectedRow,now).state:'unknown';
    row=!selectedPath.selected?['grey','The applied VPN traffic selection is not verified.','Действующий выбор VPN для трафика не подтверждён.']:health==='healthy'?seen['VPN-PROBE-HEALTHY']:health==='inactive'?seen['TUNNEL-DISCONNECTED']:health==='failed'?(selectedRow.code==='DNS-001'?seen['DNS-FAILED']:seen['HTTPS-FAILED']):seen['OBSERVATION-UNKNOWN'];
  }
  var needFail=explanation.required_failures,needGood=explanation.required_successes;
  var failMet=fresh&&explanation.source_failure_streak_met===true,goodMet=fresh&&explanation.reserve_success_streak_met===true;
  function line(kind,title,text){return E('li',{'class':'hv-why-line'},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('div',{},[E('b',{},title),E('p',{},text)])]);}
  var state=native.state;
  var next;
  if(!fresh)next=bi('Current control and measurements are unknown. No switch or automatic return can be predicted from stale data.','Текущее управление и измерения неизвестны. По устаревшим данным нельзя предсказывать переключение или автоматический возврат.');
  else if(selectedPath.authoritative){
    if(!selectedPath.selected)next=bi('The traffic channel is not verified; wait for the router VPN rule check.','Канал трафика не подтверждён; дождитесь проверки действующих правил VPN роутером.')+' ('+(selectedPath.code||'KERNEL-POLICY-UNVERIFIED')+')';
    else next=(selectedPath.selected===(status.channel_path||{}).source_profile_id?bi('The primary channel is selected.','Сейчас выбран основной канал.'):bi('The reserve channel is selected.','Сейчас выбран резервный канал.'))+' '+bi('Applied VPN rules are verified; HTTPS/DNS health and Auto enablement remain separate checks.','Действующие правила VPN проверены; результаты HTTPS/DNS и включение Auto проверяются отдельно.');
  }
  else if((state==='STOPPED-ON-RESERVE'||state==='HELD-ON-RESERVE')&&!nativeFresh)next=bi('The last controller report retained the reserve after Stop, but current controller state is unknown. Review the explicit return control or a new validated trial; no automatic return is confirmed.','Последний отчёт контроллера указывал на сохранение резерва после остановки, но текущее состояние контроллера неизвестно. Проверьте отдельное действие возврата или новый подтверждённый тест; автоматический возврат не подтверждён.');
  else if(state==='STOPPED-ON-RESERVE'||state==='HELD-ON-RESERVE')next=bi('Auto is stopped with the reserve retained. Use the explicit “Return to primary” control, or a new validated trial. Stop does not promise an automatic return.','Auto остановлен с сохранением резерва. Используйте отдельное действие «Вернуться на основной» или новый подтверждённый тест. Остановка не обещает автоматического возврата.');
  else if((status.auto_control||{}).requested==='off'&&['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(state)>=0)next=bi('Stop was requested; recovery confirmation is still required. Review the Auto card and its explicit return control. No automatic return is confirmed.','Запрошена остановка; подтверждение восстановления ещё необходимо. Проверьте блок Auto и отдельное действие возврата. Автоматический возврат не подтверждён.');
  else if(state==='DEGRADED-ON-RESERVE')next=bi('The last report retained the reserve with a recovery issue. Review the Auto card and the explicit return control; no automatic return is confirmed.','Последний отчёт указывает на сохранение резерва с проблемой восстановления. Проверьте блок Auto и отдельное действие возврата; автоматический возврат не подтверждён.');
  else if(state==='COMMITTED'&&!nativeFresh)next=bi('The reserve was reported in use, but controller data is stale. A current route or automatic return is not confirmed.','Ранее сообщалось об использовании резерва, но данные контроллера устарели. Текущий маршрут и автоматический возврат не подтверждены.');
  else if(state==='COMMITTED'&&settings.recovery_return_policy==='hold_reserve')next=bi('The hold-reserve policy keeps a healthy reserve for operator review. Use the explicit return control when appropriate; this policy does not promise automatic return.','Политика сохранения резерва оставляет работающий резерв до решения оператора. При необходимости используйте отдельное действие возврата; эта политика не обещает автоматического возврата.');
  else if(state==='COMMITTED'&&settings.recovery_return_policy==='healthy_primary')next=bi('The healthy-primary policy may consider return only in an enabled, validated trial with fresh primary checks. LAN verification and recovery guards still apply; return is not promised.','Политика здорового основного может рассматривать возврат только во включённом подтверждённом тесте со свежими проверками основного. Проверка LAN и ограничения восстановления остаются обязательными; возврат не обещан.');
  else if(state==='COMMITTED')next=bi('The return policy is unknown. Review Settings and the Auto card; no automatic return is confirmed.','Политика возврата неизвестна. Проверьте настройки и блок Auto; автоматический возврат не подтверждён.');
  else if(failMet&&goodMet)next=bi('The router probe quorum is met: a candidate can be reviewed. These checks do not authorize a route change; router firmware coordination, native capability, Stop state, the bounded trial and LAN verification remain separate gates.','Порог проверок с роутера достигнут: можно рассмотреть кандидата. Эти проверки не разрешают изменение маршрута; координация со штатной прошивкой, нативные возможности, состояние Stop, ограниченный тест и проверка LAN остаются отдельными условиями.');
  else if(failMet)next=bi('Router failures were observed, but reserve health is not yet confirmed. This card does not authorize a route change.','Наблюдались ошибки проверок с роутера, но здоровье резерва ещё не подтверждено. Эта карточка не разрешает изменение маршрута.');
  else next=bi('The retained router checks do not meet the failure threshold. This card does not authorize a route change.','Сохранённые проверки с роутера не достигают порога сбоев. Эта карточка не разрешает изменение маршрута.');
  if(vendor)next+=' '+bi('Why Auto will switch or wait: ','Почему Auto переключит или подождёт: ')+vendorCoordinationText(vendor)+'.';
  var code=native.reason||native.state,techCode=typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)?code:null;
  return E('section',{'class':'hv-chart-card hv-why'},[
    E('h3',{},bi('Why Auto will switch or wait','Почему Auto переключит или подождёт')),
    E('p',{},bi('Failure and success thresholds describe router probe evidence. They do not prove firmware attempts are exhausted or authorize Auto. Tunnel identity, coordination, controller policy and independent LAN verification remain separate conditions.','Пороги сбоев и успешных проверок описывают результаты проверок с роутера. Они не доказывают завершение попыток прошивки и не разрешают Auto. Идентичность туннеля, координация, политика контроллера и независимая проверка LAN остаются отдельными условиями.')),
    E('ul',{'class':'hv-why-list'},[
      line(row[0],bi('What the router sees on the VPN in use','Что роутер видит на используемом VPN'),bi(row[1],row[2])),
      line(!fresh?'grey':failMet?'red':'green',bi('Has the VPN in use failed enough times?','Отказал ли используемый VPN достаточное число раз?'),(failMet?bi('Yes.','Да.'):bi('No.','Нет.'))+' '+bi('Auto needs '+(needFail||'—')+' failed checks in a row.','Auto нужно '+(needFail||'—')+' неудачных проверок подряд.')),
      line(!fresh?'grey':goodMet?'green':'yellow',bi('Has the reserve met the router probe threshold?','Достигнут ли порог проверок резерва с роутера?'),(goodMet?bi('Yes.','Да.'):bi('Not yet.','Пока нет.'))+' '+bi('Auto needs '+(needGood||'—')+' good checks in a row.','Auto нужно '+(needGood||'—')+' успешных проверок подряд.'))]),
    E('p',{'class':'hv-why-next'},[E('strong',{},bi('Evidence and next review: ','Данные и дальнейшая проверка: ')),next]),
    E('p',{'class':'hv-why-note'},bi('These checks are made by the router itself, so they show whether the VPN tunnels work, not what your computer sees. A separate LAN helper can verify a real client path; current prepared-MT3000 router-probed IPv4 Auto does not require it.','Эти проверки делает сам роутер, поэтому они показывают, работают ли VPN-туннели, а не то, что видит ваш компьютер. Отдельный LAN-помощник проверяет путь реального клиента; для router-probed IPv4 Auto подготовленного MT3000 он не обязателен.')),
    techCode?E('small',{'class':'hv-why-tech'},[bi('Technical state: ','Техническое состояние: '),errorCodeLink(techCode)]):null
  ].filter(Boolean));
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
function connectivityProfiles(status){return (status.profiles||[]).filter(function(p){return p.interface&&p.administrative_state!=='disabled';});}
function connectivityRoleId(rows,settings,role,fallback){
  var anchor=settings['plan_'+role+'_tunnel'];
  if(anchor){var matches=rows.filter(function(p){return p.vendor_tunnel_id===anchor;});return matches.length===1?matches[0].id:null;}
  return settings['plan_'+role]||fallback;
}
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
  var model=connectivityModel(status,connectivityRequest,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  if(connectivityFailure)model={state:'UNAVAILABLE',busy:false};
  var clock=function(seconds){return new Date(seconds*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'});};
  // The idle line shows the latest automatic check, so it always says something true.
  var rows=connectivityProfiles(status),working=rows.filter(function(p){return profileHealth(p,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='healthy';}).length;
  var latest=rows.reduce(function(newest,p){return Number.isFinite(p.time)&&p.time>newest?p.time:newest;},0);
  var summary=function(time,total,ok){return bi('Last check ','Последняя проверка ')+clock(time)+'\n'+ok+' '+bi('of','из')+' '+total+' '+bi('VPNs work','VPN работают');};
  var text;
  if(model.state==='EMPTY')text=bi('No VPN is connected right now, so there was nothing to check.','Сейчас ни один VPN не подключён, проверять нечего.');
  else if(model.state==='COMPLETED'&&model.checked!=null&&model.time)text=latest>=model.time?summary(latest,rows.length,working):model.checked!==rows.length?bi('Channels changed. Check the VPNs again.','Состав каналов изменился. Повторите проверку VPN.'):summary(model.time,model.checked,model.checked-model.failed);
  else if(model.state==='IDLE')text=rows.length&&latest?summary(latest,rows.length,working):bi('No VPN is connected right now.','Сейчас ни один VPN не подключён.');
  else text={QUEUED:bi('Request sent. Waiting for the router…','Запрос отправлен. Ждём роутер…'),RUNNING:bi('Checking now…','Идёт проверка…'),FAILED:bi('The check could not run. Make sure the monitor is running.','Проверку выполнить не удалось. Убедитесь, что мониторинг запущен.'),UNAVAILABLE:bi('No answer from the router, so no result.','Роутер не ответил, результата нет.')}[model.state]||'';
  connectivityControl.button.disabled=connectivityBusy||model.busy||status.error==='SERVICE-STOPPED';
  connectivityControl.message.textContent=text+(model.code?' · '+model.code:'');
  connectivityControl.message.setAttribute('data-check-state',model.state);
  // A cell belongs to a named channel; do not sort healthy cells ahead of failed ones.
  if(connectivityControl.bar){
    var bar=connectivityControl.bar;while(bar.firstChild)bar.removeChild(bar.firstChild);
    var ids=connectivityControl.settings||{},native=status.native_failover||{},path=status.channel_path||{};
    var primary=connectivityRoleId(rows,ids,'source',path.source_profile_id||native.source),reserve=connectivityRoleId(rows,ids,'target',path.target_profile_id||native.target);
    var cells=rows.slice(0,16).map(function(p,index){return {profile:p,label:p.id===primary?bi('Primary channel','Основной канал'):p.id===reserve?bi('Reserve channel','Резервный канал'):bi('VPN channel ','VPN-канал ')+(index+1)};});
    cells.sort(function(a,b){return (a.profile.id===primary?0:a.profile.id===reserve?1:2)-(b.profile.id===primary?0:b.profile.id===reserve?1:2);});
    cells.forEach(function(cell){var healthy=profileHealth(cell.profile,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='healthy';bar.appendChild(E('span',{'class':'hv-check-channel'},[E('small',{},cell.label),E('span',{'class':'hv-check-cell'+(healthy?' hv-check-cell-ok':''),'title':cell.label+' · '+(healthy?bi('Internet available','Интернет доступен'):bi('Internet check not passed','Проверка Интернета не пройдена'))})]));});
    bar.hidden=!cells.length;bar.setAttribute('aria-label',working+' '+bi('of','из')+' '+rows.length+' '+bi('VPNs work','VPN работают'));
  }
  if(connectivityControl.next){
    connectivityControl.next.hidden=!rows.length;
    connectivityControl.next.textContent=working?bi('Step 2: turn on Auto with the button in this card.','Шаг 2: включите Auto кнопкой в этом блоке.'):bi('No VPN works right now. Check the VPN profiles in GL.iNet, then press the button again.','Сейчас ни один VPN не работает. Проверьте VPN-профили в GL.iNet и нажмите кнопку ещё раз.');
  }
  connectivityControl.button.setAttribute('aria-busy',model.busy?'true':'false');
}
function renderConnectivityCheck(status,refresh,inventory){
  var message=E('p',{'role':'status','aria-live':'polite'});
  var button=E('button',{'type':'button','class':'hv-connectivity-action','click':function(){
    if(connectivityBusy||button.disabled)return;
    connectivityBusy=true;connectivityFailure=false;button.disabled=true;message.textContent=bi('Sending the request…','Отправляется запрос…');
    return scanCall().then(function(result){
      if(!result||result.queued!==true||!/^([a-f0-9]{32})$/.test(result.request_id)||!Number.isFinite(result.requested_at))throw new Error('SCAN-ACK-UNCONFIRMED');
      connectivityRequest={request_id:result.request_id,requested_at:result.requested_at};
      message.textContent=bi('Request sent; waiting for the router to measure','Запрос отправлен; роутер выполняет измерение');
      return refresh();
    }).catch(function(){connectivityFailure=true;message.textContent=bi('The router did not confirm the request. Make sure the monitor is running (Settings → Start monitor) and try again.','Роутер не подтвердил запрос. Убедитесь, что мониторинг запущен («Настройки» → «Запустить мониторинг»), и повторите.');}).finally(function(){connectivityBusy=false;updateConnectivityCheck(connectivityLatest);});
  }},E('span',{'class':'hv-check-icon','aria-hidden':'true'},'↻'));
  button.setAttribute('aria-label',bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас'));button.setAttribute('title',bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас'));
  var bar=E('div',{'class':'hv-check-bar','role':'img'}),next=E('p',{'class':'hv-check-next'});
  connectivityControl={button:button,message:message,bar:bar,next:next,settings:(inventory||{}).settings||{}};
  var node=E('section',{'class':'hv-connectivity-control'},[button,E('div',{'class':'hv-check-text'},[E('strong',{},bi('Step 1 · Check the VPNs now','Шаг 1 · Проверить VPN сейчас')),E('small',{},bi('First you need to check your VPNs. Press this button: it shows which VPNs give internet right now. The router also repeats this check by itself all the time.','Сначала нужно проверить VPN. Нажмите эту кнопку: она покажет, какие VPN сейчас дают интернет. Роутер и сам постоянно повторяет эту проверку.')),message,bar,next])]);
  updateConnectivityCheck(status);return node;
}

// Viewport-only layout; never reads router state or changes navigation policy.
function sidebarGeometry(height,top,header,width){
  if(width<=760)return {mobile:true,top:0,height:0,tiny:false};
  var sticky=Math.max(12,Math.ceil(header)+12);
  var available=Math.max(80,Math.floor(height-Math.max(sticky,top)-12));
  return {mobile:false,top:sticky,height:available,tiny:available<320};
}
// An explicit Events menu click starts at its top. Code links may scroll to a row
// afterwards; Go back keeps the position it is restoring.
function sidebarMenuViewport(event,root){
  if(typeof PAGE_BACK_GOING!=='undefined'&&PAGE_BACK_GOING)return;
  var target=event&&event.target,link=target&&typeof target.closest==='function'?target.closest('[data-hv-tab]'):null;
  var nav=root&&root.querySelector('.hv-sidebar nav');
  if(!link||!nav||!nav.contains(link)||link.getAttribute('data-hv-tab')!=='events')return;
  if(typeof resetPageViewport==='function')resetPageViewport(root,'events');
  else window.scrollTo(0,0);
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
  var menu=root.querySelector('.hv-sidebar nav');
  if(menu&&!menu.hvMenuViewport){menu.hvMenuViewport=true;menu.addEventListener('click',function(event){sidebarMenuViewport(event,root);});}
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
function showIncident(row,status,inventory){
  var f=incidentFields(row);ui.showModal(bi('Incident evidence','Подтверждения инцидента'),[
    E('p',{},(status&&typeof recoveryChannelText==='function'?recoveryChannelText(row,'source',status.profiles||[],inventory):f.source)+' → '+(status&&typeof recoveryChannelText==='function'?recoveryChannelText(row,'target',status.profiles||[],inventory):f.target)+' · '+(typeof recoveryOutcomeText==='function'?recoveryOutcomeText(row):f.outcome)),E('p',{},f.codes.join(' · ')||bi('No reason recorded','Причина не записана')),
    E('ol',{},f.phases.map(function(phase){return E('li',{},phase);})),E('p',{},f.scope),
    E('button',{'type':'button','class':'cbi-button','click':function(){downloadIncidentReport([row]);}},bi('Download printable report','Скачать отчёт для печати')),
    E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть'))
  ]);
}

/* Read-only readiness; missing evidence never grants Auto permission. Missing information is shown as "waiting", never as a blank. */
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
var READINESS_CHECKS={
  'PYTHON-39-MINIMUM':['Python 3.9 or newer','Python 3.9 или новее','Runs the program','Запускает программу','🐍'],
  'DEPENDENCY-UBUS':['ubus','ubus','Talks to the router system','Связь с системой роутера','⇄'],
  'DEPENDENCY-UCI':['uci','uci','Reads and saves settings','Чтение и сохранение настроек','⚙'],
  'DEPENDENCY-LUA':['Lua','Lua','Settings helper','Помощник настроек','λ'],
  'DEPENDENCY-IP':['ip','ip','Network tool','Сетевой инструмент','⛓'],
  'RPC-PLUGIN':['Program plugin','Модуль программы','Connects this page to the program','Связывает эту страницу с программой','🔌'],
  'CA-BUNDLE':['Certificates','Сертификаты','For HTTPS checks','Для проверок HTTPS','🔒'],
  'CONFIG-STORAGE-FREE':['Writable configuration storage','Записываемое хранилище настроек','Writable filesystem and at least 1 MB free','Доступная запись и не менее 1 МБ свободно','💾']
};
var READINESS_TESTED_FIRMWARE='4.11.0';
// Allowlisted remedies only. Never derive a shell command from RPC/user text.
var READINESS_GUIDES={
  'PYTHON-39-MINIMUM':{packages:'python3',install:'opkg install python3',verify:'python3 --version',en:'Runs the application. Version 3.9 or newer is required; installing an older vendor Python is not a pass.',ru:'Выполняет программу. Нужен Python 3.9 или новее; установка более старой версии из feeds не означает готовность.'},
  'DEPENDENCY-UBUS':{packages:'ubus',install:'opkg install ubus',verify:'ubus call system board',en:'Connects the application to router services. A missing command and a stopped ubus service need different diagnoses.',ru:'Обеспечивает связь со службами роутера. Отсутствующая команда и остановленная служба ubus — разные причины.'},
  'DEPENDENCY-UCI':{packages:'uci',install:'opkg install uci',verify:'command -v uci',en:'Reads and saves router settings. Never delete configuration or reset the router to repair this check.',ru:'Читает и сохраняет настройки. Не удаляйте конфигурацию и не сбрасывайте роутер ради исправления проверки.'},
  'DEPENDENCY-LUA':{packages:'lua lua-cjson libuci-lua',install:'opkg install lua lua-cjson libuci-lua',verify:'lua -e "require(\'cjson\'); require(\'uci\')"',en:'Runs the settings helper. Both the interpreter and its JSON/UCI modules must load.',ru:'Запускает помощник настроек. Должны работать интерпретатор и модули JSON/UCI.'},
  'DEPENDENCY-IP':{packages:'ip-full',install:'opkg install ip-full',verify:'ip -Version',en:'Inspects interfaces and policy routes. Keep the matching vendor package; do not remove networking packages to force a replacement.',ru:'Проверяет интерфейсы и маршруты. Нужен пакет этой прошивки; не удаляйте сетевые компоненты ради принудительной замены.'},
  'RPC-PLUGIN':{packages:'application / rpcd',install:'',verify:'ubus -v list homensai-vpn',en:'Connects this page to the installed application. Check the verified application package and rpcd registration; a Python package alone cannot repair it. Follow the installation prompt for a verified repair, without force flags.',ru:'Связывает страницу с приложением. Проверьте проверенный пакет программы и регистрацию в rpcd: установка Python сама по себе это не исправит. Для восстановления используйте установочный промпт без force-флагов.'},
  'CA-BUNDLE':{packages:'ca-bundle',install:'opkg install ca-bundle',verify:'test -s /etc/ssl/certs/ca-certificates.crt',en:'Supplies trusted certificate authorities for HTTPS. Also check the router clock; never disable TLS verification to make a probe pass.',ru:'Содержит доверенные центры сертификатов HTTPS. Проверьте и часы роутера; не отключайте проверку TLS ради зелёного результата.'},
  'CONFIG-STORAGE-FREE':{packages:'none',install:'',verify:'df -k /etc/config; cat /proc/mounts',en:'Settings need a writable filesystem and at least 1 MiB free; installation preflight separately needs 20 MiB. Read-only storage can have plenty of space but cannot save settings. Diagnose filesystem/recovery first; never automatically remount a production router, delete arbitrary files or reset it.',ru:'Для настроек нужна записываемая файловая система и минимум 1 МиБ; установочный preflight отдельно требует 20 МиБ. Read-only хранилище может иметь много места, но не сохранять настройки. Сначала диагностика файловой системы/восстановления; не перемонтируйте рабочий роутер автоматически, не удаляйте произвольные файлы и не сбрасывайте его.'}
};
function readinessRepairPrompt(code){
  var g=READINESS_GUIDES[code],r=READINESS_CHECKS[code];if(!g||!r)return '';
  return bi('On the specific router I identify, diagnose and repair this failed application check: ','На указанном мной роутере проверь и исправь этот пункт готовности приложения: ')+code+' — '+bi(r[0],r[1])+'.\n'+
    bi('Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.\n','Сначала только чтением: модель/прошивка, штатные feeds, фактическая причина и место. Сохрани проверенную приватную копию. Используй разрешённый доступ; не запрашивай секреты в чат.\n')+
    bi('Purpose: ','Назначение: ')+bi(g.en,g.ru)+'\n'+
    (g.install?bi('After checking compatibility, install only from this firmware\'s original vendor feeds. Example: ','После проверки совместимости устанавливай только из штатных feeds этой прошивки. Пример: ')+g.install+'\n':'')+
    bi('Verify using: ','Проверь командой: ')+g.verify+'\n'+
    bi('Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.\n','Без force, массового обновления, чужих feeds, прошивки, сброса firewall и изменений сети компьютера. Не запускай Auto и не принимай соглашение за меня. Обнови готовность и проверь свежий результат, не только exit установщика. Отчитайся PASS/FAIL/BLOCKED/UNKNOWN и перечисли непроверенное.\n')+
    'https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.'+(locale==='ru'?'ru':'en')+'.md';
}
function renderReadinessHelp(code){
  var g=READINESS_GUIDES[code],r=READINESS_CHECKS[code];
  var prompt=E('textarea',{'readonly':'readonly','rows':'12','style':'width:100%;box-sizing:border-box','aria-label':bi('AI repair prompt','Промпт исправления с ИИ')});prompt.value=readinessRepairPrompt(code);
  var copy=E('button',{'type':'button','class':'cbi-button','click':function(){
    function select(){prompt.focus();prompt.select();}
    if(typeof navigator!=='undefined'&&navigator.clipboard)return navigator.clipboard.writeText(prompt.value).then(function(){copy.textContent=bi('Copied','Скопировано');}).catch(select);
    select();
  }},bi('Copy repair prompt','Скопировать промпт исправления'));
  return E('div',{'data-readiness-help':code},[
    E('h3',{},bi(r[0],r[1])+' · '+code),E('p',{},bi(g.en,g.ru)),
    E('h4',{},bi('Install manually','Установить самостоятельно')),
    E('p',{},bi('Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.','Подключитесь к нужному роутеру, проверьте прошивку/место и сохраните проверенную приватную копию. Используйте только штатные feeds этой прошивки. Выполняйте opkg update лишь для обновления списка пакетов. Не запускайте opkg upgrade и не используйте force.')),
    g.install?E('pre',{'class':'hv-cmd'},g.install):E('p',{},bi('This needs diagnosis/recovery, not an arbitrary additional package.','Здесь нужна диагностика/восстановление, а не произвольный дополнительный пакет.')),
    E('h4',{},bi('Verify the result','Проверить результат')),E('pre',{'class':'hv-cmd'},g.verify),
    E('p',{},bi('Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.','Обновите «Готовность системы» и дождитесь свежих данных. Ошибка или устаревшая проверка остаётся непроверенной даже после успешной команды установки.')),
    E('h4',{},bi('Let ChatGPT/Codex or Claude do it','Поручить ChatGPT/Codex или Claude')),E('p',{},bi('Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.','Нужен агент с терминалом и доступом к роутеру. Промпт относится только к этому пункту и не разрешает другие сетевые изменения.')),copy,prompt
  ].filter(Boolean));
}
function readinessCheckState(state){return state==='pass'?'ok':state==='fail'?'bad':state==='waiting'?'waiting':'unknown';}
function readinessTile(code,state){
  var r=Object.prototype.hasOwnProperty.call(READINESS_CHECKS,code)?READINESS_CHECKS[code]:[code,code,'',' ','•'];
  var st=readinessCheckState(state);
  var word=st==='ok'?bi('OK','Есть'):st==='bad'?bi('Missing','Нет'):st==='waiting'?bi('Waiting…','Ожидается…'):bi('Not reported by the router','Роутер не сообщил');
  var mark=st==='ok'?'✓':st==='bad'?'✗':st==='waiting'?'…':'?';
  return E('div',{'class':'hv-rd-tile hv-rd-'+st},[E('span',{'class':'hv-rd-mark','aria-hidden':'true'},mark),E('div',{'class':'hv-rd-tile-text'},[E('strong',{},bi(r[0],r[1])),E('small',{},bi(r[2],r[3])),typeof helpLink==='function'?helpLink('dependency-'+code,bi('Help','Помощь')):null].filter(Boolean)),E('b',{'class':'hv-rd-word'},word)]);
}
function readinessInfo(icon,label,value,waiting){
  return E('div',{'class':'hv-rd-info'+(waiting?' hv-rd-info-waiting':'')},[E('span',{'class':'hv-rd-info-icon','aria-hidden':'true'},icon),E('small',{},label),waiting?E('span',{'class':'hv-rd-skeleton'},bi('waiting for data…','ожидаются данные…')):E('strong',{},value)]);
}
var PREPARATION_CHECKS={
  'PREP-HNAT-CONFIG':['Hardware acceleration stays disabled','Аппаратное ускорение остаётся выключенным'],
  'PREP-WGCLIENT1-AUTOSTART':['WireGuard startup control','Управление запуском WireGuard'],
  'PREP-OVPNCLIENT1-AUTOSTART':['OpenVPN startup control','Управление запуском OpenVPN'],
  'PREP-STOCK-VPN-BOOT':['Stock VPN startup does not compete','Штатный автозапуск VPN не конкурирует'],
  'PREP-SFE-BOOT':['SFE startup is disabled','Автозапуск SFE выключен'],
  'PREP-SFE-AUTOLOAD':['SFE autoload is preserved outside startup','Автозагрузка SFE сохранена вне запуска'],
  'PREP-SFE-RUNTIME':['Software acceleration is not loaded','Программное ускорение не загружено']
};
var PREPARATION_ROLE_CHECKS={'PREP-SOURCE-AUTOSTART':['Primary VPN startup control','Управление автозапуском основного VPN'],'PREP-TARGET-AUTOSTART':['Reserve VPN startup control','Управление автозапуском резервного VPN']};
function preparationModel(status,now){
  var ready=readinessModel(status,now),data=(status&&status.system_readiness||{}).preparation;
  if(!ready.environmentFresh||!data||data.scope!=='persistent-mt3000-preparation')return {state:'unknown',checks:[]};
  var rows=Array.isArray(data.checks)?data.checks:[],seen={},valid=true;
  rows.forEach(function(row){if(!row||!(Object.prototype.hasOwnProperty.call(PREPARATION_CHECKS,row.code)||Object.prototype.hasOwnProperty.call(PREPARATION_ROLE_CHECKS,row.code))||seen[row.code]||['pass','fail','unknown'].indexOf(row.state)<0)valid=false;else seen[row.code]=row.state;});
  if(data.state==='unsupported'&&!rows.length)return {state:'unsupported',checks:[]};
  var roles=seen['PREP-SOURCE-AUTOSTART']!==undefined||seen['PREP-TARGET-AUTOSTART']!==undefined;
  var expected=Object.keys(PREPARATION_CHECKS).filter(function(code){return !roles||code!=='PREP-WGCLIENT1-AUTOSTART'&&code!=='PREP-OVPNCLIENT1-AUTOSTART';}).concat(roles?Object.keys(PREPARATION_ROLE_CHECKS):[]);
  if(!valid||rows.length!==expected.length||expected.some(function(code){return seen[code]===undefined;}))return {state:'unknown',checks:[]};
  return {state:Object.keys(seen).every(function(code){return seen[code]==='pass';})?'pass':'incomplete',checks:rows};
}
function renderPreparation(status,now){
  var m=preparationModel(status,now);
  var explanation=m.state==='unsupported'?bi('These persistent checks apply to the tested MT3000 setup. This is not a compatibility verdict for another model.','Эти постоянные настройки проверяются для испытанной конфигурации MT3000. Это не заключение о совместимости другой модели.'):
    m.state==='unknown'?bi('Fresh preparation evidence is not available.','Свежие сведения о подготовке отсутствуют.'):
    bi('These settings keep the tested MT3000 preparation across reboot. A passing check does not start a VPN or authorize Auto.','Эти настройки сохраняют проверенную подготовку MT3000 после перезагрузки. Успешная проверка не запускает VPN и не разрешает Auto.');
  var meaning={
    'PREP-HNAT-CONFIG':['Keeps hardware acceleration from bypassing the checked path.','Не даёт аппаратному ускорению обходить проверяемый путь.'],
    'PREP-WGCLIENT1-AUTOSTART':['Auto starts the selected WireGuard VPN. Independent startup at router boot is disabled so the two mechanisms do not compete.','Выбранный WireGuard VPN запускает Auto. Отдельный запуск при загрузке роутера отключён, чтобы два механизма не мешали друг другу.'],
    'PREP-OVPNCLIENT1-AUTOSTART':['Auto starts the selected OpenVPN VPN. Independent startup at router boot is disabled so the two mechanisms do not compete.','Выбранный OpenVPN VPN запускает Auto. Отдельный запуск при загрузке роутера отключён, чтобы два механизма не мешали друг другу.'],
    'PREP-STOCK-VPN-BOOT':['Avoids two competing VPN startup controllers.','Предотвращает конкуренцию двух механизмов запуска VPN.'],
    'PREP-SFE-BOOT':['Prevents software acceleration restarting at boot.','Не позволяет программному ускорению вернуться при загрузке.'],
    'PREP-SFE-AUTOLOAD':['Keeps original autoload bytes available for deliberate recovery.','Сохраняет исходный файл автозагрузки для осознанного восстановления.'],
    'PREP-SFE-RUNTIME':['Checks loaded software acceleration separately from saved settings.','Проверяет загруженное ускорение отдельно от сохранённых настроек.']
  };
  var rows=m.checks.map(function(row){
    var label=PREPARATION_CHECKS[row.code]||PREPARATION_ROLE_CHECKS[row.code],detail=meaning[row.code]||['Auto manages startup of the selected VPN; independent boot startup must not compete.','Auto управляет запуском выбранного VPN; отдельный запуск при загрузке не должен конкурировать.'],pass=row.state==='pass';
    return E('tr',{'data-preparation-code':row.code},[
      E('td',{},[E('strong',{},bi(label[0],label[1])),E('small',{'style':'display:block;overflow-wrap:anywhere'},row.code)]),
      E('td',{},[E('span',{'class':'hv-check-lamp hv-check-'+(pass?'green':row.state==='fail'?'red':'grey'),'aria-hidden':'true'}),' '+(pass?bi('Ready','Готово'):row.state==='fail'?bi('Needs preparation','Нужна подготовка'):bi('Not verified','Не проверено'))]),
      E('td',{},bi(detail[0],detail[1])),
      E('td',{},[typeof helpLink==='function'?helpLink('router-preparation',bi('Help','Помощь')):bi('See router preparation instructions.','См. инструкцию подготовки роутера.'),!pass&&typeof renderAutoRemedy==='function'?renderAutoRemedy(row.code):null].filter(Boolean))]);
  });
  var table=E('div',{'class':'hv-dv-tablewrap','style':'overflow-x:auto'},E('table',{'class':'table hv-preparation-table','data-preparation-table':'1'},[
    E('thead',{},E('tr',{},[bi('Check','Проверка'),bi('State','Состояние'),bi('Meaning','Что означает'),bi('Help','Помощь')].map(function(label){return E('th',{'scope':'col'},label);}))),E('tbody',{},rows)]));
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Persistent router preparation','Постоянная подготовка роутера')),E('p',{},explanation),table,E('p',{'class':'hv-ready-note'},bi('Review DNS, runtime acceleration, supported firmware and recovery instructions before changing settings. Restoring stock startup or acceleration invalidates native readiness.','Перед изменениями проверьте DNS, текущее ускорение, поддерживаемую прошивку и инструкцию восстановления. Возврат штатного автозапуска или ускорения отменяет готовность к переключению.'))]);
}
function renderReadiness(status,inventory){
  var now=(typeof routerWall==='function'?routerWall():Date.now()/1000),m=readinessModel(status,now),b=m.board||{};
  function known(v){return v&&v!=='unknown';}
  var order=Object.keys(READINESS_CHECKS),byCode={};
  m.checks.forEach(function(c){byCode[String(c.code)]=String(c.state);});
  var waiting=!m.environmentFresh;
  var passCount=order.filter(function(code){return byCode[code]==='pass';}).length;
  var failCount=order.filter(function(code){return byCode[code]==='fail';}).length;
  var auto=autoReadiness(status,inventory||{},now);
  // Ring: share of verified parts. Grey and "…" while the router has not reported anything yet.
  var share=waiting?0:Math.round(100*passCount/order.length);
  var verdictKey=waiting?'waiting':failCount?'bad':passCount===order.length?(auto.ready?'ready':'parts'):'partial';
  var verdict={
    waiting:[bi('Waiting for the router','Ожидаем ответ роутера'),bi('The router has not reported its parts yet. This appears by itself within a minute after monitoring starts; reload the page if it does not.','Роутер ещё не прислал сведения о своих частях. Это появится само в течение минуты после запуска мониторинга; если нет, обновите страницу.')],
    bad:[bi('Something is missing','Чего-то не хватает'),bi('At least one required part is missing on the router (red below). Monitoring may still work, but Auto needs all of them.','На роутере не хватает хотя бы одной нужной части (красным ниже). Мониторинг может работать, но Auto нужны все.')],
    partial:[bi('Almost there','Почти готово'),bi('The router is still checking some items — wait a minute.','Роутер ещё проверяет часть пунктов — подождите минуту.')],
    parts:[bi('The router has everything it needs','У роутера есть всё необходимое'),bi('All required parts are present. Auto still needs the steps below.','Все нужные части есть. Для Auto ещё нужны шаги ниже.')],
    ready:[bi('Ready for Auto','Готово к запуску Auto'),bi('Everything is in place. The router will still check it again when you press Start.','Всё на месте. Роутер всё равно проверит ещё раз при нажатии «Старт».')]
  }[verdictKey];
  var ring=E('div',{'class':'hv-rd-ring hv-rd-ring-'+verdictKey,'style':'--share:'+share+'%','role':'img','aria-label':waiting?bi('waiting','ожидается'):passCount+' / '+order.length},[E('div',{'class':'hv-rd-ring-inner'},[E('strong',{},waiting?'…':passCount+'/'+order.length),E('small',{},waiting?bi('waiting','ожидается'):bi('parts ready','частей готово'))])]);
  var hero=E('section',{'class':'hv-chart-card hv-rd-hero'},[ring,E('div',{'class':'hv-rd-hero-text'},[E('h2',{},verdict[0]),E('p',{},verdict[1]),E('p',{'class':'hv-ready-intro'},bi('This page only reads; it changes nothing.','Эта страница только читает и ничего не меняет.'))])]);
  var tested=known(b.firmware)?(String(b.firmware).indexOf(READINESS_TESTED_FIRMWARE)===0||String(b.firmware)===READINESS_TESTED_FIRMWARE):null;
  var router=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Your router','Ваш роутер')),E('div',{'class':'hv-rd-info-grid'},[
    readinessInfo('▣',bi('Model','Модель'),b.model,waiting||!known(b.model)),
    readinessInfo('▦',bi('Board','Плата'),b.board_name,waiting||!known(b.board_name)),
    readinessInfo('⚑',bi('GL.iNet firmware','Прошивка GL.iNet'),b.firmware,waiting||!known(b.firmware)),
    readinessInfo('⚑','OpenWrt',b.openwrt,waiting||!known(b.openwrt))]),
    waiting?E('p',{'class':'hv-ready-intro'},bi('Waiting for router information.','Ожидаются данные роутера.')):null
  ].filter(Boolean));
  var monitor=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Data from the monitor','Данные от мониторинга')),E('div',{'class':'hv-rd-tile hv-rd-'+(m.fresh?'ok':'waiting')},[E('span',{'class':'hv-rd-mark','aria-hidden':'true'},m.fresh?'✓':'…'),E('div',{'class':'hv-rd-tile-text'},[E('strong',{},m.fresh?bi('Fresh data','Свежие данные'):bi('Waiting for data','Ожидаем данные')),E('small',{},m.fresh?bi('The monitor is running and sends data.','Мониторинг работает и присылает данные.'):bi('Monitoring starts by itself; wait a minute and reload the page.','Мониторинг запускается сам; подождите минуту и обновите страницу.'))]),E('b',{'class':'hv-rd-word'},m.fresh?bi('OK','Есть'):bi('Waiting…','Ожидается…'))])]);
  var parts=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Required parts on the router','Нужные части на роутере')+(waiting?'':' ('+passCount+' / '+order.length+')')),
    E('div',{'class':'hv-rd-grid'},order.map(function(code){return readinessTile(code,waiting?'waiting':(byCode[code]||'unknown'));}))]);
  // Auto steps as a stepper; blocker codes open their row in the error table.
  var stepper=E('ol',{'class':'hv-rd-steps'},auto.steps.map(function(step,i){
    var current=auto.next&&auto.next.key===step.key;
    var state=step.done?'done':current?'next':'todo';
    var codes=(step.codes&&step.codes.length&&!step.done)?E('div',{'class':'hv-rd-codes'},step.codes.map(function(code){return E('span',{},[errorCodeLink(code),' · '+autoBlockerText(code)]);})):null;
    return E('li',{'class':'hv-rd-step hv-rd-step-'+state},[E('span',{'class':'hv-rd-step-mark','aria-hidden':'true'},step.done?'✓':current?'→':String(i+1)),E('div',{},[E('strong',{},step.title),step.done?null:E('p',{},step.hint),codes].filter(Boolean))]);
  }));
  var autoCard=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('What Auto still needs','Чего ещё не хватает для Auto')),stepper,
    E('p',{'class':'hv-ready-note'},bi('A tick here does not give permission to switch. At Start the router checks the current device, the time window, your computer’s confirmation, the safe return and the transaction lease again. The router never restarts by itself to enable Auto.','Галочка здесь не разрешает переключение. При запуске роутер заново проверит текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат и блокировку транзакции. Роутер сам никогда не перезагружается ради включения Auto.'))]);
  return E('div',{'class':'hv-rd'},[hero,router,monitor,parts,renderPreparation(status,now),autoCard]);
}

// Top of the System readiness page: what it is, that nothing needs to be pressed, how to read the colours.
function readinessIntro(){
  return E('section',{'class':'hv-chart-card hv-rd-intro'},[
    E('h3',{},bi('Is the router ready for Auto VPN?','Готов ли роутер к работе Auto VPN?')),
    E('p',{},bi('Here the router checks by itself whether it has everything Auto VPN needs: the required programs, the VPN settings, both channels (primary and reserve) and fresh measurements. You do not need to press anything: the page only shows the result and updates by itself.','Здесь роутер сам проверяет, есть ли у него всё, что нужно Auto VPN: нужные программы, настройки VPN, оба канала (основной и резервный) и свежие измерения. Нажимать ничего не нужно: страница только показывает результат и обновляется сама.')),
    E('p',{},bi('All lines green: everything is in order, turn Auto on with the button on the Overview page. Some red lines (VPN start and acceleration settings) are fixed by the Auto button itself when you turn it on. If a line stays red, press its code: you will see what happened and what to do.','Все строки зелёные — всё в порядке, включайте Auto кнопкой на странице «Обзор». Часть красных строк (настройки запуска VPN и ускорения) кнопка Auto исправит сама при включении. Если строка остаётся красной, нажмите на её код: откроется объяснение, что случилось и что сделать.')),
    E('ul',{'class':'hv-plan-legend'},[
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-green','aria-hidden':'true'}),bi(' Green ✓: checked, everything is in order.',' Зелёная ✓ — проверено, всё в порядке.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-grey','aria-hidden':'true'}),bi(' Grey …: the check is still running, the router has not sent the result yet. Usually up to a minute after the router or monitoring starts.',' Серая … — проверка ещё идёт, роутер пока не прислал результат. Обычно это до минуты после включения роутера или запуска мониторинга.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-red','aria-hidden':'true'}),bi(' Red ✗: a problem was found. Press the code next to it to see the cause and how to fix it.',' Красная ✗ — найдена проблема. Нажмите на код рядом, чтобы увидеть причину и как её исправить.')])])]);
}

/* Expandable "what is this and how to fill it in" guides for the Settings cards and the Tests page.
   Data are [English, Russian] pairs; each field has what it is, an example and the allowed range. */
var SETUP_GUIDES={
  system:{
    what:['Tells the program which two of your router VPN profiles are the main one and the reserve, and how they are named.','Говорит программе, какие два из ваших VPN-профилей роутера основной и резервный, и как они называются.'],
    why:['Auto and the reports need to know which VPN is preferred and which one takes over when the preferred one fails.','Auto и отчёты должны знать, какой VPN предпочтителен и какой подхватывает работу, когда он отказывает.'],
    fields:[
      [['Primary profile','Основной профиль'],['The VPN you normally want to use. Pick it from the list; the list comes from GL.iNet → VPN.','VPN, которым вы обычно хотите пользоваться. Выберите из списка; список берётся из GL.iNet → VPN.'],['Germany · WireGuard','Германия · WireGuard']],
      [['Reserve profile','Резервный профиль'],['The VPN used when the primary does not work. Choose a different country or provider, so one outage does not stop both.','VPN на случай, когда основной не работает. Выберите другую страну или другого провайдера, чтобы один сбой не остановил оба.'],['Netherlands · OpenVPN','Нидерланды · OpenVPN']],
      [['Name','Название'],['Your own short name shown in the tables and in reports. Optional.','Ваше короткое название в таблицах и отчётах. Необязательно.'],['Main (home)','Основной (дом)']],
      [['Priority','Приоритет'],['1 is the most preferred. The reserve gets a larger number.','1 — самый предпочтительный. У резерва число больше.'],['Primary 1, reserve 2','Основной 1, резерв 2']],
      [['Allow a brief drop of calls and downloads when switching','Разрешить короткий обрыв звонков и загрузок при переключении'],['Switching to another VPN breaks open connections for a few seconds (calls, downloads). Tick it only if you accept that.','При переходе на другой VPN открытые соединения рвутся на несколько секунд (звонки, загрузки). Отметьте, только если вас это устраивает.'],['Tick it','Отметить']]
    ]},
  recovery:{
    what:['The rules for when the router switches to the reserve and when it goes back.','Правила: когда роутер переходит на резерв и когда возвращается обратно.'],
    why:['Too sensitive rules switch on every short glitch; too lazy rules leave you without internet for long. Presets are tested starting points.','Слишком чувствительные правила переключаются при каждом сбое; слишком ленивые надолго оставляют без интернета. Пресеты — проверенные точки старта.'],
    fields:[
      [['Preset “Stability”','Пресет «Стабильность»'],['Recommended. Switches only after 5 failed checks in a row, waits 5 minutes between switches, returns after 5 good checks and 2 minutes of calm.','Рекомендуется. Переключается только после 5 неудачных проверок подряд, ждёт 5 минут между переключениями, возвращается после 5 удачных проверок и 2 минут спокойствия.'],['failures 5 · pause 300 s','сбоев 5 · пауза 300 с']],
      [['Preset “Fast recovery”','Пресет «Быстрое восстановление»'],['Switches after 3 failures, pause 1 minute, returns after 3 good checks. Reacts quickly, but may switch more often.','Переключается после 3 сбоев, пауза 1 минута, возврат после 3 удачных проверок. Реагирует быстро, но может переключаться чаще.'],['failures 3 · pause 60 s','сбоев 3 · пауза 60 с']],
      [['Preset “Hold reserve”','Пресет «Держать резерв»'],['After a switch stays on the reserve until you press “Return to primary”. Fewer surprises, but you return by hand.','После переключения остаётся на резерве, пока вы не нажмёте «Вернуться на основной». Меньше неожиданностей, но возвращаться нужно вручную.'],['pause 180 s · stay on reserve','пауза 180 с · остаться на резерве']],
      [['Failures before switching','Сбоев до переключения'],['How many failed checks in a row count as a real outage. Range 3–10.','Сколько неудачных проверок подряд считать настоящим сбоем. Диапазон 3–10.'],['5','5']],
      [['Good checks on the reserve','Удачных проверок резерва'],['How many good checks the reserve needs before the switch. Range 2–10.','Сколько удачных проверок нужно резерву перед переключением. Диапазон 2–10.'],['3','3']],
      [['Attempt limit and window','Лимит попыток и период'],['Maximum forward attempts in a rolling window of 1–15 minutes. The pause between attempts still applies; changing the values does not erase the recorded history.','Максимум попыток перехода за скользящий период 1–15 минут. Отдельная пауза между попытками сохраняется; изменение значений не стирает историю.'],['3 attempts · 15 min','3 попытки · 15 минут']],
      [['Cooldown, seconds','Пауза, секунд'],['Minimum time between two switches. Range 60–1800.','Минимальное время между двумя переключениями. Диапазон 60–1800.'],['300','300']],
      [['Minimum stay, seconds','Минимальное пребывание, секунд'],['How long to stay on the new VPN before another switch is allowed. Range 60–3600.','Сколько оставаться на новом VPN, прежде чем разрешить следующее переключение. Диапазон 60–3600.'],['300','300']],
      [['Return rule and checks','Правило возврата и проверки'],['Return when the primary is healthy (needs 2–10 good checks and 30–600 s of calm), or hold the reserve.','Возвращаться, когда основной исправен (нужно 2–10 удачных проверок и 30–600 с спокойствия), или держать резерв.'],['5 checks · 120 s','5 проверок · 120 с']]
    ]},
  monitoring:{
    what:['How often the program checks your VPNs and how much it keeps.','Как часто программа проверяет ваши VPN и сколько хранит.'],
    why:['Checks are what the statistics and Auto rely on. More frequent checks react faster but use a little more traffic and router time.','На проверках основаны статистика и Auto. Частые проверки реагируют быстрее, но чуть больше нагружают трафик и роутер.'],
    fields:[
      [['Check interval, seconds','Интервал проверок, секунд'],['Pause between checks of each connected VPN. Range 10–300.','Пауза между проверками каждого подключённого VPN. Диапазон 10–300.'],['10 (default)','10 (по умолчанию)']],
      [['Statistics saving, seconds','Сохранение статистики, секунд'],['How often the collected data is written to the router’s storage. Range 300–3600. Rarer saves wear flash less.','Как часто собранные данные пишутся в память роутера. Диапазон 300–3600. Реже — меньше износ флеш-памяти.'],['900','900']],
      [['Profile limit','Лимит профилей'],['How many connected VPNs are checked at one time. Range 1–16.','Сколько подключённых VPN проверяется одновременно. Диапазон 1–16.'],['4','4']]
    ]},
  telegram:{
    what:['Sends reports and alerts about your VPNs to a Telegram chat.','Отправляет отчёты и уведомления о ваших VPN в чат Telegram.'],
    why:['You learn about a switch or an outage without opening the router page. Optional.','Вы узнаёте о переключении или сбое, не открывая страницу роутера. Необязательно.'],
    fields:[
      [['Bot token','Токен бота'],['A secret from @BotFather (https://t.me/BotFather): send /newbot, choose a name, copy the line it gives you. It never leaves the router and is never shown again.','Секрет от @BotFather (https://t.me/BotFather): отправьте /newbot, выберите имя, скопируйте выданную строку. Он остаётся на роутере и больше не показывается.'],['123456789:AAH… (digits, colon, 30–100 characters)','123456789:AAH… (цифры, двоеточие, 30–100 символов)']],
      [['Chat ID','ID чата'],['Where to send. For yourself: write to @userinfobot (https://t.me/userinfobot) and copy “Id”. For a group the number starts with −. A public channel can be @channelname.','Куда слать. Для себя: напишите @userinfobot (https://t.me/userinfobot) и скопируйте «Id». Для группы число начинается с −. Публичный канал можно указать как @имя_канала.'],['123456789 · -1001234567890 · @my_channel','123456789 · -1001234567890 · @my_channel']],
      [['Report every, minutes','Отчёт каждые, минут'],['How often a report is sent. Range 5–10080 (one week).','Как часто слать отчёт. Диапазон 5–10080 (неделя).'],['1440 (once a day)','1440 (раз в сутки)']],
      [['Daily hour','Час суток'],['The hour of the day for daily reports, 0–23 router time.','Час суток для ежедневных отчётов, 0–23 по времени роутера.'],['9','9']]
    ],
    tail:['Then press “Test Telegram delivery”. If nothing arrives, open Help → “Telegram reports do not arrive”.','Затем нажмите «Проверить доставку Telegram». Если ничего не пришло, откройте «Помощь» → «Отчёты в Telegram не приходят».']},
  speed:{
    what:['A speed test downloads and uploads a small amount of data through one VPN and shows how fast it is.','Тест скорости скачивает и отдаёт небольшой объём данных через один VPN и показывает его скорость.'],
    why:['It helps to compare servers. It is not needed for failover, uses your traffic, and is off by default. Run it when you choose a server, not all the time.','Помогает сравнить серверы. Для переключения не нужен, расходует трафик и по умолчанию выключен. Запускайте при выборе сервера, а не постоянно.'],
    fields:[
      [['Enable speed tests','Включить тесты скорости'],['Master switch. Nothing is measured while it is off.','Главный выключатель. Пока он выключен, ничего не измеряется.'],['Off (default)','Выключено (по умолчанию)']],
      [['Test after a new server connects','Тестировать после подключения нового сервера'],['Measures a server once when it first appears connected.','Один раз измеряет сервер, когда он впервые оказался подключён.'],['On, if you often add servers','Включить, если часто добавляете серверы']],
      [['Payload budget per server, MiB','Лимит на сервер, МиБ'],['The most data one test of one server may use.','Максимум данных на один тест одного сервера.'],['8','8']],
      [['Seconds per direction · Parallel streams','Секунд на направление · Потоки'],['How long to measure download and upload, and how many connections to use.','Сколько измерять скачивание и отдачу и сколько соединений использовать.'],['5 s · 2 streams','5 с · 2 потока']],
      [['Daily quota, MiB','Суточная квота, МиБ'],['The total data all tests together may use in a day.','Сколько данных могут использовать все тесты вместе за сутки.'],['128','128']],
      [['Skip above current VPN traffic, Mbps','Не запускать при трафике выше, Мбит/с'],['No test starts while you are actively using the VPN above this speed.','Тест не стартует, пока вы активно пользуетесь VPN быстрее этого значения.'],['2','2']]
    ]}
};
function setupGuide(key){
  var g=SETUP_GUIDES[key];if(!g)return null;
  var fields=g.fields.map(function(f){return E('li',{},[E('strong',{},bi(f[0][0],f[0][1])),E('span',{},' — '+bi(f[1][0],f[1][1])),E('em',{'class':'hv-guide-example'},' '+bi('Example: ','Пример: ')+bi(f[2][0],f[2][1]))]);});
  return E('details',{'class':'hv-setup-guide'},[E('summary',{},bi('What is this and how to fill it in','Что это и как заполнить')),
    E('p',{},[E('strong',{},bi('What it is. ','Что это. ')),bi(g.what[0],g.what[1])]),
    E('p',{},[E('strong',{},bi('What it is for. ','Для чего. ')),bi(g.why[0],g.why[1])]),
    E('ul',{'class':'hv-guide-fields'},fields),
    g.tail?E('p',{},bi(g.tail[0],g.tail[1])):null].filter(Boolean));
}
/* Monitoring is always on. The Overview shows a block next to "Check the VPNs now": lamp, title and a few numbers.
   monitorLightModel() decides running / catching up / stopped; the block has a button only when monitoring is not running. */
var monitorBlockHost=null,monitorBusy=false;
var MONITOR_LAMPS=['green','yellow','red'];
function monitorStartedRecently(now){
  try{var at=Number(window.sessionStorage.getItem('homensai-vpn-monitor-requested'));return Number.isFinite(at)&&at>0&&now-at>=0&&now-at<=90;}catch(e){return false;}
}
function monitorLightModel(status,inventory,now,recent){
  var settings=(inventory||{}).settings||{},enabled=settings.enabled===true;
  var age=Number.isFinite(status.time)?now-status.time:Infinity;
  var fresh=!status.rpc_error&&!status.error&&age>=-5&&age<=90;
  function out(key,lamp,icon,title,hint,code){return {key:key,lamp:lamp,icon:icon,title:title,hint:hint,code:code||null,enabled:enabled};}
  if(!status.rpc_error&&status.speed_pause&&status.speed_pause.active&&status.speed_pause.monitor_paused)return out('transition','yellow','Ⅱ',bi('Monitoring paused for speed test','Мониторинг на паузе для теста скорости'),bi('A fresh check runs after the test, before Auto continues.','После теста выполнится свежая проверка, затем продолжит работу Auto.'));
  if(status.rpc_error)return out('problem','red','!',bi('Cannot read the monitor','Не удаётся прочитать мониторинг'),bi('The page could not get the status from the router. Reload the page and sign in again; see Help → “The page is old, empty or says the monitor is not running”.','Страница не смогла получить статус от роутера. Обновите страницу и войдите снова; см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'),'RPC-UNAVAILABLE');
  if(!status.rpc_error&&status.speed_pause&&status.speed_pause.active&&status.speed_pause.phase==='RESUMING')return out('transition','yellow','⟳',bi('Monitoring is resuming','Мониторинг возобновляется'),bi('Waiting for the first post-test observation.','Ожидается первая проверка после теста.'));
  if(enabled&&fresh)return out('ok','green','✓',bi('Monitor is running','Мониторинг работает'),bi('Fresh data arrived '+Math.max(0,Math.round(age))+' s ago. Each connected VPN is checked about every '+(Number(settings.interval)||10)+' seconds.','Свежие данные пришли '+Math.max(0,Math.round(age))+' с назад. Каждый подключённый VPN проверяется примерно раз в '+(Number(settings.interval)||10)+' с.'));
  if(enabled&&(recent||(!status.error&&age<=300)))return out('transition','yellow','⟳',bi('Starting or catching up','Запускается или догоняет'),bi('The monitor is switched on and the first fresh data is not here yet. This takes up to a minute.','Мониторинг включён, первых свежих данных ещё нет. Это занимает до минуты.'));
  if(enabled)return out('problem','red','!',bi('Switched on, but not running','Включён, но не работает'),bi('The router program is not producing data.','Программа на роутере не выдаёт данные.'),status.error||'STATUS-STALE');
  return out('problem','red','!',bi('Monitoring must be running','Мониторинг должен работать'),bi('Monitoring is required for Auto. Restore monitoring before starting automatic control.','Мониторинг необходим для Auto. Восстановите мониторинг перед запуском автоматического управления.'),'SERVICE-STOPPED');
}
// Numbers for the block: checks and failures of the last hour from the samples the monitor keeps.
function monitorNumbers(status,now){
  var samples=Array.isArray(status.samples)?status.samples:[];
  var recent=samples.filter(function(s){return Number.isFinite(s.time)&&now-s.time<=3600&&now-s.time>=-5;});
  var failed=recent.filter(function(s){return s.code;}).length;
  return {checks:recent.length,failed:failed,percent:recent.length?Math.round(100*(recent.length-failed)/recent.length):null};
}
function fillMonitorBlock(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),light=monitorLightModel(status,inventory,now,monitorStartedRecently(now)),n=monitorNumbers(status,now);
  var tone=light.key==='ok'?'green':light.key==='transition'?'yellow':light.key==='problem'?'red':'grey';
  var title=light.key==='ok'?bi('Monitoring is on','Мониторинг включён'):light.title;
  var stats=light.key==='ok'||n.checks
    ?bi(n.checks+' checks in the last hour · '+n.failed+' failed'+(n.percent==null?'':' · '+n.percent+'% passed'),n.checks+' проверок за час · не прошло '+n.failed+(n.percent==null?'':' · прошло '+n.percent+'%'))
    :light.hint;
  var button=null;
  if(light.key==='problem'||light.key==='off'){
    button=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
      if(monitorBusy)return;monitorBusy=true;button.disabled=true;
      return rpc.declare({object:'homensai-vpn',reject:true,method:'monitor_control',params:['enabled'],expect:{}})(true).then(function(result){
        if(result&&result.accepted===true){try{window.sessionStorage.setItem('homensai-vpn-monitor-requested',String((typeof statusNow==='function'?statusNow(status):Date.now()/1000)));}catch(e){}window.location.reload();return;}
        ui.addNotification(null,E('p',{},(result&&result.code)||'MONITOR-UNKNOWN'));
      }).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){monitorBusy=false;button.disabled=false;});
    }},bi('Restore monitoring','Восстановить мониторинг'));
  }
  host.appendChild(E('span',{'class':'hv-monitor-lamp hv-monitor-lamp-'+tone,'role':'img','aria-label':title}));
  host.appendChild(E('div',{'class':'hv-check-text'},[E('strong',{},title),E('small',{},stats),light.key==='ok'?E('small',{'class':'hv-check-status'},bi('Checks every '+(Number((inventory.settings||{}).interval)||10)+' s · last data '+Math.max(0,Math.round(now-status.time))+' s ago','Проверка каждые '+(Number((inventory.settings||{}).interval)||10)+' с · последние данные '+Math.max(0,Math.round(now-status.time))+' с назад')):null,button].filter(Boolean)));
}
function renderMonitorBlock(status,inventory){
  monitorBlockHost=E('section',{'class':'hv-connectivity-control hv-monitor-block'});
  fillMonitorBlock(monitorBlockHost,status,inventory);
  return monitorBlockHost;
}
// "About the statistics" card on the Statistics page: what is collected and where it is stored.
function renderMonitorInfo(status,inventory){
  var settings=(inventory||{}).settings||{};
  var every=Number(settings.checkpoint)>0?Math.round(Number(settings.checkpoint)/60):null;
  return E('section',{'class':'hv-chart-card'},[
    E('h3',{},bi('Where this statistics comes from','Откуда эта статистика')),
    E('p',{},bi('Monitoring is always on. About every '+(Number(settings.interval)||10)+' seconds it checks each connected VPN (can it open a website and resolve a name through it). From these checks the charts above are built: how fast each server answers, and how long each one worked or failed. History starts when monitoring first started; nothing is guessed for earlier time.','Мониторинг всегда включён. Примерно каждые '+(Number(settings.interval)||10)+' с он проверяет каждый подключённый VPN (может ли он открыть сайт и найти адрес). Из этих проверок построены графики выше: как быстро отвечает каждый сервер и сколько времени он работал или не работал. История начинается с первого запуска мониторинга; за более раннее время ничего не придумывается.')),
    E('p',{'class':'hv-ready-intro'},bi('Where it is stored: on the router itself, in /etc/homensai-vpn (saved '+(every?'about every '+every+' min':'periodically')+'; the interval can be changed in Settings → Advanced settings → Monitoring parameters). Nothing leaves the router.','Где хранится: на самом роутере, в /etc/homensai-vpn (сохраняется '+(every?'примерно раз в '+every+' мин':'периодически')+'; интервал можно изменить в «Настройки» → «Расширенные настройки» → «Параметры мониторинга»). Ничего не уходит с роутера.'))]);
}

var ADVANCED_KEYS=['tests','statistics','traffic','services','events'];
var PAGE_SUBTITLES={
  overview:['Your VPNs, how healthy they are, and what the router did about it.','Ваши VPN, насколько они исправны и что сделал роутер.'],
  channels:['Every VPN profile on the router and whether it works right now.','Все VPN-профили роутера и работают ли они прямо сейчас.'],
  statistics:['How your VPNs behaved over time.','Как вели себя ваши VPN со временем.'],
  settings:['Set up the monitor, your two VPNs, reports and recovery rules.','Настройка мониторинга, двух VPN, отчётов и правил восстановления.'],
  start:['Setup, training and checks. The simplified interface is available whenever Auto is on.','Настройка, обучение и проверки. При включённом Auto упрощённый интерфейс доступен всегда.'],
  learn:['A short interactive training: what the system is, how to use it and what to do when something goes wrong.','Короткое интерактивное обучение: что это за система, как ею пользоваться и что делать, если что-то пошло не так.'],
  help:['What to do when something is wrong.','Что делать, если что-то не так.'],
  tests:['How the failover decides, and a test that simulates a failure.','Как принимается решение о переключении, и тест с имитацией сбоя.'],
  ranking:['Which servers worked best over the last days.','Какие серверы работали лучше всего за последние дни.'],
  traffic:['How much data went through each VPN.','Сколько данных прошло через каждый VPN.'],
  services:['A live log of what the router sees.','Живой журнал того, что видит роутер.'],
  events:['Everything that happened: switches, failures, recoveries.','Всё, что происходило: переключения, сбои, восстановления.'],
  readiness:['Look at the items below: when all of them are green, your system is ready for Auto.','Посмотрите на пункты ниже: когда все они зелёные, ваша система готова к Auto.']
};
/* Server labels: protocol and country instead of host names or addresses. The country is read from the profile name the
   VPN provider gave (for example de1459.nordvpn.com or "Germany Berlin"); it is never looked up from an IP address. */
var COUNTRIES={
  al:['Albania','Албания'],ar:['Argentina','Аргентина'],am:['Armenia','Армения'],au:['Australia','Австралия'],at:['Austria','Австрия'],az:['Azerbaijan','Азербайджан'],
  bd:['Bangladesh','Бангладеш'],be:['Belgium','Бельгия'],ba:['Bosnia and Herzegovina','Босния и Герцеговина'],br:['Brazil','Бразилия'],bg:['Bulgaria','Болгария'],
  by:['Belarus','Беларусь'],ca:['Canada','Канада'],ch:['Switzerland','Швейцария'],cl:['Chile','Чили'],co:['Colombia','Колумбия'],cr:['Costa Rica','Коста-Рика'],
  hr:['Croatia','Хорватия'],cy:['Cyprus','Кипр'],cz:['Czechia','Чехия'],dk:['Denmark','Дания'],de:['Germany','Германия'],ee:['Estonia','Эстония'],es:['Spain','Испания'],
  fi:['Finland','Финляндия'],fr:['France','Франция'],gb:['United Kingdom','Великобритания'],ge:['Georgia','Грузия'],gr:['Greece','Греция'],hk:['Hong Kong','Гонконг'],
  hu:['Hungary','Венгрия'],is:['Iceland','Исландия'],in:['India','Индия'],id:['Indonesia','Индонезия'],ie:['Ireland','Ирландия'],il:['Israel','Израиль'],it:['Italy','Италия'],
  jp:['Japan','Япония'],kz:['Kazakhstan','Казахстан'],kr:['South Korea','Южная Корея'],lv:['Latvia','Латвия'],lt:['Lithuania','Литва'],lu:['Luxembourg','Люксембург'],
  md:['Moldova','Молдова'],me:['Montenegro','Черногория'],mk:['North Macedonia','Северная Македония'],mx:['Mexico','Мексика'],my:['Malaysia','Малайзия'],nl:['Netherlands','Нидерланды'],
  nz:['New Zealand','Новая Зеландия'],no:['Norway','Норвегия'],pa:['Panama','Панама'],pe:['Peru','Перу'],ph:['Philippines','Филиппины'],pl:['Poland','Польша'],pt:['Portugal','Португалия'],
  ro:['Romania','Румыния'],rs:['Serbia','Сербия'],ru:['Russia','Россия'],sg:['Singapore','Сингапур'],sk:['Slovakia','Словакия'],si:['Slovenia','Словения'],za:['South Africa','Южная Африка'],
  se:['Sweden','Швеция'],th:['Thailand','Таиланд'],tr:['Turkey','Турция'],tw:['Taiwan','Тайвань'],ua:['Ukraine','Украина'],ae:['United Arab Emirates','ОАЭ'],us:['United States','США'],
  uy:['Uruguay','Уругвай'],uz:['Uzbekistan','Узбекистан'],vn:['Vietnam','Вьетнам']
};
var COUNTRY_ALIASES={uk:'gb',usa:'us',uae:'ae',holland:'nl','czech republic':'cz','south korea':'kr',korea:'kr'};
function countryCodeFromName(text){
  if(typeof text!=='string'||!text)return null;
  var name=text.toLowerCase().slice(0,96),code;
  // 1. A country written out (English or Russian), longest name first so "south africa" never reads as "africa".
  var words=[];Object.keys(COUNTRIES).forEach(function(key){words.push([COUNTRIES[key][0].toLowerCase(),key]);words.push([COUNTRIES[key][1].toLowerCase(),key]);});
  Object.keys(COUNTRY_ALIASES).forEach(function(alias){words.push([alias,COUNTRY_ALIASES[alias]]);});
  words.sort(function(a,b){return b[0].length-a[0].length;});
  for(var i=0;i<words.length;i++){
    var at=name.indexOf(words[i][0]);
    if(at>=0&&words[i][0].length>=3&&!/[a-zа-я]/.test(name.charAt(at-1)||' ')&&!/[a-zа-я]/.test(name.charAt(at+words[i][0].length)||' '))return words[i][1];
  }
  // 2. Provider host names and short names: de1459.nordvpn.com, ua68.nordvpn.com.udp, de-fra-001, us_ny_2, "DE Berlin".
  var match=/^([a-z]{2})(?:[0-9]{1,5}(?=[._-]|$)|[-_ ])/.exec(name)||/^([a-z]{2})$/.exec(name);
  if(match){code=COUNTRY_ALIASES[match[1]]||match[1];if(COUNTRIES[code])return code;}
  return null;
}
function countryOf(profile){
  if(!profile)return null;
  var code=countryCodeFromName(profile.router_name)||countryCodeFromName(profile.name)||countryCodeFromName(profile.channel);
  return code?{code:code,en:COUNTRIES[code][0],ru:COUNTRIES[code][1]}:null;
}
function countryName(profile){var country=countryOf(profile);return country?bi(country.en,country.ru):'';}
function countryLabel(profile){return bi('Country: ','Страна: ')+(countryName(profile)||bi('unknown','не определена'));}
function protocolLabel(profile){return profile&&profile.protocol==='wireguard'?'WireGuard':'OpenVPN';}
// A name the owner chose; the provider's host name is never repeated on screen.
function customName(profile){return profile&&profile.router_name&&profile.name&&profile.name!==profile.router_name?String(profile.name):'';}
function serverTitle(profile){
  var country=countryName(profile);
  return country?country+' · '+protocolLabel(profile)+(customName(profile)?' · '+customName(profile):''):(customName(profile)||(profile&&profile.name)||'—');
}

/* Explains the Channels page: where the list comes from, why it has N entries, and when the number changes. */
function serverCounts(status,inventory,rows,now){
  var onRouter=Array.isArray((inventory||{}).profiles)?inventory.profiles.length:rows.length;
  var shown=rows.length;
  var connected=rows.filter(function(p){return p.interface;});
  var working=connected.filter(function(p){return profileHealth(p,now).state==='healthy';}).length;
  return {onRouter:Math.max(onRouter,shown),shown:shown,connected:connected.length,working:working,hidden:Math.max(0,onRouter-shown)};
}
function renderServerSummary(status,inventory,rows){
  var c=serverCounts(status,inventory,rows,(typeof routerWall==='function'?routerWall():Date.now()/1000));
  function tile(value,label,hint){return E('div',{'class':'hv-count'},[E('strong',{},String(value)),E('span',{},label),hint?E('small',{},hint):null].filter(Boolean));}
  var tiles=[
    tile(c.onRouter,bi('VPN profiles on the router','VPN-профилей на роутере'),bi('Added in GL.iNet → VPN','Добавлены в GL.iNet → VPN')),
    tile(c.connected,bi('Connected now','Подключено сейчас'),bi('Only these are checked','Проверяются только они')),
    tile(c.working+' / '+c.connected,bi('Work (internet passes)','Работают (интернет проходит)'),bi('From the latest check','По последней проверке'))
  ];
  var note=bi('This list is read from your router. A VPN profile you add in GL.iNet (VPN → VPN Dashboard) appears here by itself within about a minute, and a removed one disappears, so the numbers can change at any time. Profiles that are not connected are listed so you can see them; this program never connects them. To add, remove or connect servers use the router’s VPN page (button below).','Список берётся с вашего роутера. VPN-профиль, добавленный в GL.iNet (VPN → VPN Dashboard), появляется здесь сам примерно за минуту, а удалённый исчезает, поэтому числа могут меняться в любой момент. Неподключённые профили показаны, чтобы вы их видели; эта программа их никогда не подключает. Чтобы добавить, убрать или подключить серверы, используйте страницу VPN на роутере (кнопка ниже).');
  var hidden=c.hidden>0?E('p',{'class':'hv-count-note'},c.hidden+' '+bi('profile(s) are hidden because you chose which servers to monitor (Settings → All application settings → 3 · Existing VPNs).','профилей скрыто, потому что вы выбрали, какие серверы наблюдать («Настройки → Все настройки приложения → 3 · Существующие VPN»).')):null;
  return E('section',{'class':'hv-chart-card hv-server-summary'},[E('h3',{},bi('Your VPN servers','Ваши VPN-серверы')),E('div',{'class':'hv-counts'},tiles),E('p',{},note),hidden].filter(Boolean));
}

/* Two levels of recovery: observe configured vendor tunnels; explain the application's
   read-only inter-tunnel planning gate. Labels never establish tunnel identity or cause. */
var VENDOR_COORDINATION_TEXT={
  'CROSS-TUNNEL-READY':['Ready: if the primary fails, the reserve can take over. This is only a plan; this line switches nothing.','Готово: если основной откажет, резерв сможет принять трафик. Это только план, эта строка ничего не переключает.'],
  'VENDOR-SAME-TUNNEL':['Both choices are the same router tunnel. The router picks its server itself; the app does not switch inside it.','Выбран один и тот же туннель роутера. Сервер в нём выбирает сам роутер, приложение внутри него не переключает.'],
  'VENDOR-SETTLING':['Watching: the app waits until the channel settings stop changing.','Идёт наблюдение: приложение ждёт, пока настройки каналов перестанут меняться.'],
  'VENDOR-IDENTITY-UNKNOWN':['The app cannot tell which router tunnel this is yet.','Приложение пока не может определить, какой это туннель роутера.'],
  'OBSERVATION-STALE':['The latest checks are too old to rely on.','Последние проверки слишком старые, на них нельзя опираться.'],
  'PROFILE-IDENTITY-CHANGED':['The channel profile changed; new checks are needed.','Профиль канала изменился; нужны новые проверки.'],
  'UPLINK-LINK-DOWN':['The router has no internet cable or Wi-Fi uplink; switching VPN would not help, so it is paused.','У роутера нет интернета (кабель или Wi-Fi). Переключение VPN не поможет, поэтому оно приостановлено.'],
  'PLAN-CONFIG':['The chosen pair of tunnels needs to be reviewed in Channels and servers.','Выбранную пару туннелей нужно проверить в «Каналы и серверы».']
};
function vendorTunnelId(value){return typeof value==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.-]{1,64}$/.test(value)?value:null;}
function vendorProfileId(value){return typeof value==='string'&&/^[A-Za-z0-9_.:-]{1,96}$/.test(value)?value:null;}
function vendorLabel(value){return typeof value==='string'&&Array.from(value).length<=64&&value.trim()&&!/[\p{C}\p{Zl}\p{Zp}]/u.test(value)?value:null;}
function vendorProtocol(value){return value==='openvpn'?'OpenVPN':value==='wireguard'?'WireGuard':bi('Unknown protocol','Неизвестный протокол');}
function vendorFresh(stamp,now,age){return typeof stamp==='number'&&Number.isFinite(stamp)&&stamp>=0&&stamp<=now&&now-stamp<=age;}
function vendorDiagnosticsModel(status,inventory,now){
  if(typeof dataCause==='function')UI_DATA_CAUSE=dataCause(status,now);
  status=status&&typeof status==='object'?status:{};inventory=inventory&&typeof inventory==='object'?inventory:{};
  var settings=inventory.settings||{},interval=Number(settings.interval),age=Number.isInteger(interval)&&interval>=10&&interval<=300?Math.max(30,interval*3):90;
  var observation=status.vendor_observation,available=!!observation&&observation.version===1&&Array.isArray(observation.groups);
  var fresh=available&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(observation.time,now,age);
  var profiles=Array.isArray(status.profiles)?status.profiles.slice(0,400):[],metadata=Array.isArray(inventory.servers)?inventory.servers.slice(0,400):[],profileMap=Object.create(null),metadataMap=Object.create(null);
  profiles.forEach(function(p){if(p&&vendorProfileId(p.id))profileMap[p.id]=Object.prototype.hasOwnProperty.call(profileMap,p.id)?null:p;});
  metadata.forEach(function(p){if(p&&vendorProfileId(p.profile))metadataMap[p.profile]=Object.prototype.hasOwnProperty.call(metadataMap,p.profile)?null:p;});
  function profileName(id){var row=metadataMap[id],measured=profileMap[id],configured=(Array.isArray(inventory.profiles)?inventory.profiles:[]).filter(function(p){return p&&p.id===id;})[0];return row&&vendorLabel(row.name)||measured&&vendorLabel(measured.name)||measured&&vendorLabel(measured.router_name)||configured&&vendorLabel(configured.name)||id||bi('Not reported by the router','Роутер не сообщил');}
  var groups=[],seen={};
  (available?observation.groups.slice(0,400):[]).forEach(function(raw){
    if(!raw||typeof raw!=='object')return;
    var id=vendorTunnelId(raw.id);if(!id||raw.protocol!==id.split(':')[0])return;
    if(seen[id]){seen[id].state='unknown';seen[id].health='unknown';seen[id].current=null;return;}
    var ids=Array.isArray(raw.profiles)?raw.profiles.slice(0,8).filter(function(v,i,a){return vendorProfileId(v)&&a.indexOf(v)===i;}):[];
    var active=Array.isArray(raw.active_profiles)?raw.active_profiles.slice(0,2).filter(function(v,i,a){return vendorProfileId(v)&&ids.indexOf(v)>=0&&a.indexOf(v)===i;}):[];
    var current=vendorProfileId(raw.current_profile),generation=typeof raw.generation==='string'&&/^[0-9a-f]{32}$/.test(raw.generation)?raw.generation:null;
    var coherent=!!generation&&!!current&&Array.isArray(raw.profiles)&&raw.profiles.length===ids.length&&Array.isArray(raw.active_profiles)&&raw.active_profiles.length===1&&active.length===1&&active[0]===current;
    var stable=fresh&&vendorFresh(raw.time,now,age)&&raw.state==='SETTLED'&&Number.isInteger(raw.stable_samples)&&raw.stable_samples>=2&&raw.stable_samples<=1000000&&coherent;
    var state=!fresh||!vendorFresh(raw.time,now,age)?'unknown':stable?'stable':raw.state==='PENDING'&&coherent&&raw.stable_samples===1?'pending':'unknown';
    var row=profileMap[current],health='unknown';
    // Health belongs only to this exact configured identity, never the previous member.
    var member=stable&&row&&!(metadataMap[current]&&metadataMap[current].enabled===false)&&row.protocol===raw.protocol&&row.interface===id.split(':')[1]&&row.vendor_state==='SETTLED'&&row.vendor_tunnel_id===id&&row.vendor_generation===generation&&vendorFresh(row.time,now,age)&&vendorFresh(raw.changed_at,now,now)&&row.vendor_changed_at===raw.changed_at&&raw.changed_at<=row.time&&raw.changed_at<=raw.time?row:null;
    if(member){
      if(row.code===null&&row.dns_ok===true&&Number.isInteger(row.https_success)&&row.https_success>=2)health='healthy';
      else if(['VPN-001','VPN-003','DNS-001','ROUTE-001'].indexOf(row.code)>=0)health='failed';
    }
    var labels=[];ids.forEach(function(profile){var measured=profileMap[profile],saved=metadataMap[profile],label=vendorLabel(saved&&saved.channel)||vendorLabel(measured&&measured.channel);if(label&&labels.indexOf(label)<0)labels.push(label);});
    var profileGroup=typeof raw.profile_group_id==='string'&&/^(openvpn|wireguard):[0-9]{1,20}$/.test(raw.profile_group_id)&&raw.profile_group_id.split(':')[0]===raw.protocol?raw.profile_group_id:null;
    var group={id:id,protocol:raw.protocol,profileGroup:profileGroup,current:state!=='unknown'&&current&&ids.indexOf(current)>=0?current:null,member:member,name:profileName(current),state:state,health:health,labels:labels,changedAt:vendorFresh(raw.changed_at,now,now)?raw.changed_at:null};seen[id]=group;groups.push(group);
  });
  var rawCoord=(status.failover_plan||{}).coordination,coordination={known:false,code:null,state:'UNKNOWN',source:null,target:null,transition:null,settleUntil:null};
  if(rawCoord&&rawCoord.version===1&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(rawCoord.time,now,age)&&rawCoord.can_apply===false&&rawCoord.vendor_attempts_exhausted===null&&rawCoord.vendor_reason==='UNOBSERVED'&&Object.prototype.hasOwnProperty.call(VENDOR_COORDINATION_TEXT,rawCoord.code)&&['READY','HOLD','UNKNOWN'].indexOf(rawCoord.state)>=0){
    var source=vendorTunnelId(rawCoord.source_tunnel),target=vendorTunnelId(rawCoord.target_tunnel);
    var sourceGroup=groups.filter(function(g){return g.id===source;})[0],targetGroup=groups.filter(function(g){return g.id===target;})[0];
    var transition=source&&target&&(source.split(':')[0]===target.split(':')[0]?'channel':'protocol');
    var ready=rawCoord.code!=='CROSS-TUNNEL-READY'||rawCoord.state==='READY'&&source&&target&&source!==target&&rawCoord.transition===transition&&sourceGroup&&sourceGroup.state==='stable'&&sourceGroup.health!=='unknown'&&targetGroup&&targetGroup.state==='stable'&&targetGroup.health==='healthy';
    if(ready)coordination={known:true,code:rawCoord.code,state:rawCoord.state,source:source,target:target,transition:['channel','protocol'].indexOf(rawCoord.transition)>=0?rawCoord.transition:null,settleUntil:typeof rawCoord.settle_until==='number'&&Number.isFinite(rawCoord.settle_until)&&rawCoord.settle_until>now?rawCoord.settle_until:null};
  }
  var events=[];
  (available&&Array.isArray(observation.events)?observation.events.slice(-50):[]).forEach(function(event){
    if(!event||event.cause!=='UNOBSERVED'||!vendorFresh(event.time,now,now)||!vendorTunnelId(event.tunnel))return;
    if(['VENDOR-PROFILE-CHANGED','VENDOR-BINDING-CHANGED','VENDOR-BINDING-UNKNOWN','VENDOR-FIRST-OBSERVATION'].indexOf(event.code)<0)return;
    var before=vendorProfileId(event.previous_profile),after=vendorProfileId(event.current_profile);
    if(event.code==='VENDOR-PROFILE-CHANGED'&&(!before||!after||before===after))return;
    events.push({time:event.time,tunnel:event.tunnel,before:before,after:after,code:event.code});
  });
  events.sort(function(a,b){return b.time-a.time;});
  return {available:available,fresh:fresh,groups:groups,coordination:coordination,events:events.slice(0,8),source:vendorTunnelId(settings.plan_source_tunnel),target:vendorTunnelId(settings.plan_target_tunnel)};
}
function vendorDisplayMember(status,inventory,role,now,legacyId){
  if(role!=='source'&&role!=='target')return null;
  var settings=(inventory||{}).settings||{},anchor=settings['plan_'+role+'_tunnel'];
  if(anchor!=null&&anchor!==''){
    if(!vendorTunnelId(anchor))return null;
    var group=vendorDiagnosticsModel(status,inventory,now).groups.filter(function(g){return g.id===anchor;})[0];
    return group&&group.state==='stable'&&group.member||null;
  }
  var id=legacyId||settings['plan_'+role],rows=Array.isArray((status||{}).profiles)?status.profiles.filter(function(p){return p&&p.id===id;}):[];
  return rows.length===1?rows[0]:null;
}
function vendorDisplaySelected(status,inventory,now){
  if(typeof channelPathSelection==='function'){
    var source=vendorDisplayMember(status,inventory,'source',now),target=vendorDisplayMember(status,inventory,'target',now);
    var proof=channelPathSelection(status,now,source&&source.id,target&&target.id);
    if(proof.authoritative)return proof.selected;
  }
  var route=(status||{}).channel_path;
  if(route)return null;
  var native=(status||{}).native_failover||{},role=null;
  if(native.mode==='continuous-pair'||native.proof_scope==='router-probed-ipv4')return null;
  if((status||{}).rpc_error||!vendorFresh(native.time,now,30))return null;
  if(['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(native.state)>=0)role='target';
  else if(native.state==='OBSERVING'&&native.certified===true)role='source';
  var row=role?vendorDisplayMember(status,inventory,role,now,native[role]):null;
  return row?row.id:null;
}
function vendorLamp(tone,label){return E('span',{},[E('span',{'class':'hv-check-lamp hv-check-'+({healthy:'green',failed:'red',pending:'yellow'}[tone]||'grey'),'aria-hidden':'true'}),label]);}
function vendorIdentityText(group){return group.state==='stable'?bi('VPN settings unchanged','Настройки VPN не менялись'):group.state==='pending'?bi('The router is still checking VPN settings (up to a minute)','Роутер ещё проверяет настройки VPN (до минуты)'):(typeof dataCauseText==='function'?dataCauseText(bi('Configuration not observed: ','Конфигурация не получена: ')):bi('Configuration not observed','Конфигурация не получена'));}
function vendorCoordinationText(model){var row=model.coordination.known?VENDOR_COORDINATION_TEXT[model.coordination.code]:null;return row?bi(row[0],row[1]):(typeof dataCauseText==='function'?dataCauseText(bi('No plan yet: ','Плана пока нет: ')):bi('No plan yet','Плана пока нет'));}
function vendorDetailsLink(){return E('a',{'href':'#channels'},bi('Channels and servers','Каналы и серверы'));}
function renderProbeChecks(profile,now){
  if(!profile||!Array.isArray(profile.probe_checks)||!profile.probe_checks.length||!vendorFresh(profile.time,now,90))return null;
  var n=profile.https_success,headline=Number.isInteger(n)?n>=2?bi('Availability threshold met','Условие доступности выполнено'):n>0?bi('Partial HTTPS availability','Частичная HTTPS-доступность'):bi('HTTPS availability not confirmed','HTTPS-доступность не подтверждена'):bi('No saved HTTPS count','Число HTTPS-ответов не сохранено');
  var names={'ok':['Passed','Прошла'],'http-unsupported':['Check endpoint uses an incompatible HTTP version','Несовместимая версия HTTP у проверочного адреса'],'http-error':['HTTP error from check endpoint','Ошибка HTTP проверочного адреса'],'timeout':['Check endpoint did not respond in time','Проверочный адрес не ответил в срок'],'tls-error':['TLS validation or connection error','Ошибка TLS-проверки или соединения'],'transport-error':['Check request transport error','Сетевая ошибка проверочного запроса'],'invalid-response':['Response did not pass validation','Ответ не прошёл проверку'],'unknown':['Details not recorded','Подробности не сохранены']};
  var rows=profile.probe_checks.slice(0,3).filter(function(r){return r&&['one.one.one.one','dns.google','dns.quad9.net'].indexOf(r.target)>=0&&names[r.result];});
  return E('details',{'class':'hv-probe-details','data-probe-profile':profile.id},[E('summary',{},(profile.name||profile.id)+' · '+headline+(Number.isInteger(n)?' · HTTPS '+n+'/3':'')),E('p',{},profile.dns_ok===true?bi('DNS check passed.','DNS-проверка прошла.'):profile.dns_ok===false?bi('DNS check failed.','DNS-проверка не прошла.'):bi('DNS result not recorded.','Результат DNS не сохранён.')),E('ul',{},rows.map(function(r){return E('li',{},r.target+' · '+bi.apply(null,names[r.result])+(Number.isInteger(r.http_status)?' · HTTP '+r.http_status:''));})),E('p',{},bi('An error at a check endpoint does not by itself prove complete loss of VPN traffic.','Ошибка проверочного адреса сама по себе не доказывает полное отсутствие трафика через VPN.'))]);
}
// Owner removed this complete disclosure from Channels; keep the builder call harmless.
function renderVendorChannels(){return E([]);}
function renderVendorEvents(status,inventory){
  var m=vendorDiagnosticsModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),names={'VENDOR-PROFILE-CHANGED':bi('VPN profile changed','VPN-профиль изменился'),'VENDOR-BINDING-CHANGED':bi('VPN settings changed','Настройки VPN изменились'),'VENDOR-BINDING-UNKNOWN':bi('VPN profile changed or removed on the router','VPN-профиль изменён или удалён на роутере'),'VENDOR-FIRST-OBSERVATION':bi('VPN seen for the first time','VPN замечен впервые')};
  var content=m.events.length?E('ol',{},m.events.map(function(event){return E('li',{'data-vendor-event':event.code},[E('strong',{},names[event.code]),E('span',{},' · '+new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})+' · '+event.tunnel),E('p',{},(event.before||'—')+' → '+(event.after||'—')),E('small',{},bi('Reason for the change was not observed.','Причина смены не наблюдалась.'))]);})):E('p',{},bi('No recorded profile identity changes yet. This does not prove that the firmware made no attempts.','Записей о смене конфигурации профиля пока нет. Это не доказывает отсутствие попыток штатной прошивки.'));
  return E('details',{'class':'hv-chart-card','data-vendor-diagnostics':'events','style':'min-width:0;overflow-wrap:anywhere'},[E('summary',{},bi('Recent router configuration observations','Последние наблюдения конфигурации роутера')),!m.fresh?E('p',{},bi('Retained observations only; current router tunnel state is unknown.','Показаны только сохранённые наблюдения; текущее состояние туннеля роутера неизвестно.')):null,content,E('small',{},bi('At most 8 recent observations. Profile identity changes are not proof of automatic failover, its cause, or a verified LAN outcome.','Не более 8 последних наблюдений. Изменение профиля не доказывает автоматическое переключение, его причину или подтверждённый результат в LAN.'))].filter(Boolean));
}


var ERROR_ROWS=[["CLIENT-CONTROL-PATH-MISMATCH","helper","Management route uses another interface","Управление идёт через другой интерфейс"],["WAN-001","monitor","Internet is down at the router","Нет интернета на роутере"],["DNS-001","monitor","DNS check did not pass","DNS-проверка не прошла"],["VPN-001","monitor","VPN did not connect","VPN не подключился"],["VPN-002","monitor","VPN login rejected","VPN отклонил вход"],["VPN-003","monitor","HTTPS availability below threshold","Недостаточно успешных HTTPS-проверок"],["VPN-004","monitor","VPN server name does not resolve","Имя VPN-сервера не находится"],["TLS-001","monitor","Certificate check failed","Ошибка проверки сертификата"],["ROUTE-001","monitor","Traffic goes another way","Трафик идёт другим путём"],["CHECK-001","monitor","Check not confirmed","Проверка не подтверждена"],["SWITCH-001","switch","No ready reserve","Нет готового резерва"],["AUTO-CONTROL-UNVERIFIED","switch","Auto request not confirmed","Запрос Auto не подтверждён"],["AUTO-CONTROL-FAILED","switch","Auto request got no answer","Запрос Auto остался без ответа"],["AUTO-START-REFUSED","switch","Auto start refused","Запуск Auto отклонён"],["ROLLBACK-GIVEN-UP","switch","Automatic return stopped","Автоматический возврат остановлен"],["EXIT-TRACE-FAILED","switch","Exit address could not be read","Не удалось прочитать внешний адрес"],["STOP-UNCONFIRMED","switch","Stop not confirmed","Остановка не подтверждена"],["SWITCH-002","switch","Internet not restored after the switch","Интернет не вернулся после переключения"],["SWITCH-003","switch","Switch could not be applied","Переключение не удалось применить"],["CONFIG-001","switch","Automation paused after manual change","Автоматика на паузе после ручного изменения"],["SYSTEM-001","service","Unsupported firmware or missing tool","Неподдерживаемая прошивка или нет программы"],["MONITOR-START-REQUESTED","service","Start requested","Запуск запрошен"],["MONITOR-STOP-REQUESTED","service","Stop requested","Остановка запрошена"],["MONITOR-STOP-AUTO-FIRST","service","Stop Auto first","Сначала остановите Auto"],["MONITOR-JOURNAL-UNVERIFIED","service","Journal cannot be read","Журнал не читается"],["MONITOR-SAVE-FAILED","service","Setting not saved","Настройка не сохранилась"],["MONITOR-SERVICE-UNCONFIRMED","service","Service change not confirmed","Смена состояния службы не подтверждена"],["MONITOR-INVALID","service","Invalid request","Неверный запрос"],["MONITOR-RPC-UNCONFIRMED","service","No confirmed answer","Нет подтверждённого ответа"],["RPC-UNAVAILABLE","service","Router does not answer","Роутер не отвечает"],["STATUS-STALE","service","Status is old","Статус устарел"],["RPC-PLUGIN","service","Program plugin missing","Нет модуля программы"],["RPC-INPUT-SIZE","service","Request too large","Слишком большой запрос"],["CLIENT-CABLE-LINK-DOWN","helper","Cable adapter is down","Кабельный адаптер не подключён"],["CLIENT-CABLE-ADDRESS-AMBIGUOUS","helper","Cable IPv4 address is ambiguous","Неоднозначный IPv4-адрес кабеля"],["CLIENT-CABLE-NOT-LOCAL","helper","Selected cable does not reach this router locally","Выбранный кабель не ведёт к роутеру локально"],["CLIENT-CABLE-PROBE-ROUTE-MISMATCH","helper","Cable probe route differs","Маршрут кабельной проверки не совпадает"],["CLIENT-CABLE-HTTPS-FAILED","helper","Bound HTTPS check failed","Привязанная HTTPS-проверка не прошла"],["CLIENT-GATEWAY-MISMATCH","helper","Client path uses another gateway","Клиентский путь использует другой шлюз"],["CLIENT-DNS-CONFIG-UNVERIFIED","helper","DNS settings unverified","Настройки DNS не подтверждены"],["CLIENT-IPV6-DEFAULT-UNVERIFIED","helper","IPv6 route unverified","Маршрут IPv6 не подтверждён"],["CLIENT-PROBE-ROUTE-CONFLICT","helper","Legacy probe-route conflict","Конфликт проверочных маршрутов старой версии"],["CLIENT-CANCELLED","helper","Cancelled","Отменено"],["CLIENT-TRIAL-UNCONFIRMED","helper","Trial not confirmed","Тест не подтверждён"],["CLIENT-RESERVE-NOT-VERIFIED","helper","Reserve not verified","Резерв не подтверждён"],["POWERSHELL-7-REQUIRED","helper","PowerShell 7 needed","Нужен PowerShell 7"],["PRIVATE-LAN-ROUTER-REQUIRED","helper","Router address is not private","Адрес роутера не частный"],["TELEGRAM-TOKEN-REQUIRED","telegram","Bot token missing","Нет токена бота"],["TELEGRAM-TOKEN-FORMAT","telegram","Token looks wrong","Токен выглядит неверно"],["TELEGRAM-TOKEN-REJECTED","telegram","Token rejected by Telegram","Telegram отклонил токен"],["TELEGRAM-DESTINATION-FORMAT","telegram","Chat ID looks wrong","ID чата выглядит неверно"],["TELEGRAM-PERMISSION","telegram","Bot cannot write there","Бот не может туда писать"],["TELEGRAM-RATE-LIMIT","telegram","Too many messages","Слишком много сообщений"],["TELEGRAM-DNS","telegram","Telegram address not found","Адрес Telegram не найден"],["TELEGRAM-TLS","telegram","Secure connection failed","Защищённое соединение не удалось"],["TELEGRAM-DELIVERY-UNKNOWN","telegram","Delivery not confirmed","Доставка не подтверждена"],["TELEGRAM-DELIVERED","telegram","Delivered","Доставлено"],["TELEGRAM-TEST-DELIVERED","telegram","Test delivered","Тест доставлен"],["TELEGRAM-CONFIG","telegram","Telegram setup incomplete","Настройка Telegram неполная"],["TELEGRAM-CLOCK-BACKWARD","telegram","Clock went back","Часы пошли назад"],["TELEGRAM-STATE-CORRUPT","telegram","Report state damaged","Состояние отчётов повреждено"],["SETUP-INVALID","setup","Invalid input","Неверный ввод"],["SETUP-RANGE","setup","Value out of range","Значение вне диапазона"],["SETUP-SAVE-FAILED","setup","Settings not saved","Настройки не сохранены"],["SETUP-STOP-FIRST","setup","Stop Auto first","Сначала остановите Auto"],["SETUP-SAVE-UNCONFIRMED","setup","Save not confirmed","Сохранение не подтверждено"],["SETUP-PENDING-DELTA","setup","Unsaved router changes","Есть несохранённые изменения роутера"],["SETUP-PRIMARY-RESERVE-DISABLED","setup","Primary or reserve is off","Основной или резервный отключён"],["SETUP-PROFILES","setup","Profiles not found","Профили не найдены"],["SPEED-DISABLED","speed","Speed tests are off","Тесты скорости выключены"],["SPEED-DAILY-LIMIT","speed","Daily quota used","Суточная квота исчерпана"],["SPEED-COOLDOWN","speed","Please wait","Нужна пауза"],["SPEED-BUSY","speed","Another test is running","Уже идёт другой тест"],["SPEED-TRAFFIC-BUSY","speed","VPN is busy","VPN сейчас занят"],["SPEED-ROUTE-UNVERIFIED","speed","Test route unverified","Путь теста не подтверждён"],["SPEED-PROFILE-INACTIVE","speed","VPN not connected","VPN не подключён"],["SPEED-NETWORK","speed","Test network error","Сетевая ошибка теста"],["SPEED-CANCELLED","speed","Cancelled","Отменено"],["SCAN-DEADLINE-EXCEEDED","speed","Check took too long","Проверка заняла слишком много времени"],["SCAN-STATE-CORRUPT","speed","Check state damaged","Состояние проверки повреждено"],["CLOCK-001","data","Wrong router date","Неверная дата на роутере"],["HISTORY-001","data","History unavailable","История недоступна"],["FAULT-CERTIFIED-AUTO-REQUIRED","switch","Transition test needs running Auto","Для теста перехода нужен работающий Auto"],["FAULT-UNVERIFIED","switch","Failure test not confirmed","Сбой не подтверждён"],["FAULT-UNKNOWN","switch","Failure test result unknown","Итог теста сбоя неизвестен"],["FAULT-CANCEL-UNKNOWN","switch","Cancel not confirmed","Отмена не подтверждена"],["FAULT-RPC-UNCONFIRMED","switch","No answer from the router","Нет ответа от роутера"],["FAULT-FIELDS","switch","Invalid request","Неверный запрос"],["FAULT-HISTORY-UNAVAILABLE","data","Failure history unavailable","История сбоев недоступна"],["FAULT-STATE-CORRUPT","switch","Failure state damaged","Состояние сбоя повреждено"],["FAULT-NFT-QUERY-FAILED","switch","Cannot read the firewall rule","Не удаётся прочитать правило межсетевого экрана"],["FAULT-TABLE-ALREADY-EXISTS","switch","A previous test is still active","Предыдущий тест ещё активен"],["HISTORY-PARTIAL","data","History partly aggregated","История частично объединена"],["SPEED-HISTORY-TRUNCATED","speed","Speed history shortened","История скорости сокращена"],["JOURNAL-INTEGRITY-FAILED","switch","Journal failed its check","Журнал не прошёл проверку"],["RTP-BOOT-PRECONDITION-UNVERIFIED","platform","Router VPN runtime preparation is not confirmed","Не подтверждена штатная подготовка VPN"],["KERNEL-POLICY-VERIFIED","platform","Router VPN rules verified","Правила выбора VPN проверены"],["KERNEL-POLICY-UNVERIFIED","platform","Applied VPN selection rules are unverified","Действующие правила выбора VPN не подтверждены"],["PAIR-POLICY-UNVERIFIED","switch","Primary and reserve VPN policy is unverified","Правила основного и резервного VPN не подтверждены"],["MANUAL-ALREADY-SELECTED","manual","This channel is already selected","Этот канал уже выбран"],["PING-FAILED","monitor","No ICMP reply","Нет ответа ICMP"],["PING-DATA-STALE","monitor","ICMP result is old","ICMP-результат устарел"],["PING-CHECK-PENDING","monitor","Waiting for an ICMP check","Ожидается ICMP-проверка"],["PING-UNAVAILABLE","monitor","ICMP measurement is unavailable","ICMP-измерение недоступно"],["PING-INACTIVE","monitor","ICMP check is inactive","ICMP-проверка не выполняется"],["PING-IDENTITY-CHANGED","monitor","ICMP result belongs to another VPN connection","ICMP-результат относится к другому подключению"],["PING-NOT-SELECTED","monitor","VPN is outside the measured pair","VPN не входит в измеряемую пару"],["UI-HELP-LOAD-FAILED","service","Help could not be loaded","Не удалось загрузить справку"],["PUBLICATION-RECORD-SCOPE","internal","Release record differs from the tested source","Запись выпуска отличается от проверенного исходника"],["PUBLICATION-CI-LUA","internal","The CI receipt does not prove Lua tests ran","Квитанция CI не подтверждает проверку Lua"],["SPEED-PAUSE-UNVERIFIED","speed","Pause could not be verified","Не удалось проверить паузу"],["SPEED-PAUSE-BUSY","speed","Pause recovery in progress","Пауза ещё завершается"],["SPEED-PAUSE-LOST","speed","Pause ownership changed","Условия паузы изменились"],["SPEED-PAUSE-TIMEOUT","speed","Pause acknowledgement timed out","Нет подтверждения паузы"],["SPEED-PAUSE-MODE","speed","Auto transition is not ready for pause","Состояние Auto не готово к паузе"],["SPEED-CPU-UNKNOWN","speed","CPU observation unavailable","Загрузка CPU не прочитана"],["DEVICE-MODEL-INVALID","platform","Choose a supported router model","Выберите поддерживаемую модель"],["DEVICE-MODEL-MISMATCH","platform","Router model does not match","Модель роутера не совпадает"],["MANUAL-FIELDS","manual","Manual request form changed","Форма ручного запроса изменилась"],["MANUAL-DIRECTION-INVALID","manual","Choose a supported direction","Выберите допустимое направление"],["MANUAL-STATE-UNVERIFIED","manual","Manual control state is unknown","Состояние ручного управления неизвестно"],["MANUAL-ALREADY-CLAIMED","manual","Request was already taken","Запрос уже принят в работу"],["MANUAL-REQUEST-EXPIRED","manual","Manual request expired","Время ручного запроса истекло"],["STOP-SUPERSEDED-MANUAL","manual","Stop cancelled the pending switch","Остановка отменила ожидающее переключение"],["MANUAL-CONFIG-CHANGED","manual","Settings changed during the request","Настройки изменились во время запроса"],["MANUAL-SUPERVISOR-UNAVAILABLE","manual","No fresh controller state","Нет свежего состояния контроллера"],["MANUAL-STOP-AUTO-FIRST","manual","Stop Auto before manual switching","Остановите Auto перед ручным переключением"],["MANUAL-SELECTION-UNVERIFIED","manual","Selected pair is not verified","Выбранная пара не проверена"],["MANUAL-REQUEST-PENDING","manual","Another manual request is pending","Другой ручной запрос ещё выполняется"],["MANUAL-REQUEST-UNCONFIRMED","manual","Request was not confirmed","Запрос не подтверждён"],["MANUAL-RESULT-INVALID","manual","Result record is invalid","Запись результата некорректна"],["MANUAL-COMPLETION-UNVERIFIED","manual","Switch completion is not proved","Завершение переключения не доказано"],["RETURN-UNCONFIRMED","manual","Return to primary is unconfirmed","Возврат на основной не подтверждён"],["MANUAL-RESULT-UNCONFIRMED","manual","Manual result is unknown","Результат ручного переключения неизвестен"],["MANUAL-SUPERVISOR-RECOVERED","manual","Controller recovered an unfinished request","Контроллер восстановился после незавершённого запроса"],["MANUAL-TRANSACTION-STATE-UNVERIFIED","manual","The previous switch did not finish","Прошлое переключение не завершилось"],["MANUAL-REQUEST-INVALID","manual","Manual request could not be trusted","Ручному запросу нельзя доверять"],["OPERATOR-MANUAL","manual","Manual-channel control command","Команда ручного выбора канала"],["MT3000-MANUAL-ADAPTER-NOT-CERTIFIED","platform","MT3000 manual switching is not certified","Ручное переключение MT3000 не подтверждено"],["MT3000-COLLECTION-DEADLINE","platform","Readiness check took too long","Проверка готовности заняла слишком много времени"],["MT3000-COLLECTION-CLOCK-CHANGED","platform","Router clock changed during checks","Часы роутера изменились во время проверок"],["MT3000-READ-TIMEOUT","platform","Router read timed out","Чтение данных роутера превысило время"],["MT3000-READ-FAILED","platform","Router evidence could not be read","Не удалось прочитать данные роутера"],["MT3000-READ-UNVERIFIED","platform","Router read could not be validated","Чтение данных роутера не проверено"],["MT3000-PLATFORM-UNVERIFIED","platform","Router model is not verified","Модель роутера не проверена"],["MT3000-FIRMWARE-UNVERIFIED","platform","Router firmware is not verified","Прошивка роутера не проверена"],["MT3000-FIREWALL-UNVERIFIED","platform","Firewall type is not verified","Тип firewall не проверен"],["FW3-INCLUDE-CONTRACT-UNVERIFIED","platform","Firmware firewall integration is unverified","Интеграция firewall прошивки не проверена"],["FW3-RUNTIME-STATE-UNVERIFIED","platform","Live firewall state is unknown","Рабочее состояние firewall неизвестно"],["VENDOR-WORKER-QUIET-UNVERIFIED","platform","Router VPN changes may still be running","Изменение VPN роутером может ещё выполняться"],["NATIVE-CONTROLLER-STATE-UNVERIFIED","platform","Auto controller is not confirmed off","Выключение контроллера Auto не подтверждено"],["SELECTED-RULES-NOT-ADJACENT","platform","Selected VPN rules are not adjacent","Правила выбранных VPN не соседние"],["EXISTING-TUNNEL-BINDING-UNVERIFIED","platform","Working VPN not checked","Рабочий VPN не проверен"],["FW3-SELECTED-ZONE-UNVERIFIED","platform","VPN firewall zone is unverified","Зона firewall VPN не проверена"],["SHARED-KERNEL-BINDING","platform","VPN choices share the same routing resource","Выбранные VPN используют общий ресурс маршрутизации"],["TARGET-ROUTER-PATH-UNVERIFIED","platform","Reserve router checks have not passed","Резерв не прошёл проверки с роутера"],["MT3000-EVIDENCE-UNVERIFIED","platform","MT3000 readiness evidence is incomplete","Данные готовности MT3000 неполны"],["MONITOR-ONLY-DEPLOYMENT","switch","Installation is limited to monitoring","Установка ограничена мониторингом"],["MONITOR-ONLY-INVALID","switch","Deployment mode could not be verified","Не удалось проверить режим установки"],["NATIVE-PROGRESS-UNVERIFIED","switch","Controller progress records are unverified","Записи состояния контроллера не проверены"],["VENDOR-IDENTITY-UNKNOWN","switch","Cannot find this VPN on the router","Не удаётся найти этот VPN на роутере"],["VENDOR-IDENTITY-CHANGED","monitor","VPN changed during a check","VPN изменился во время проверки"],["PROFILE-IDENTITY-CHANGED","switch","VPN profile changed","VPN-профиль изменился"],["PAIR-EXTERNAL-POLICY-CHANGE","switch","Route rules changed outside the app","Правила маршрутов изменены вне приложения"],["PAIR-EXTERNAL-NETWORK-CHANGE","switch","Network settings changed outside the app","Сетевые настройки изменены вне приложения"],["PAIR-EXTERNAL-CONFIG-CHANGE","switch","Router configuration changed outside the app","Конфигурация роутера изменена вне приложения"],["PAIR-RECOVERY-REQUIRED","switch","Previous Auto session is being taken over","Предыдущая сессия Auto передаётся заново"],["PAIR-READOPTED","state","Auto re-read changed settings","Auto заново прочитал изменённые настройки"],["VENDOR-REASON-UNOBSERVED","monitor","Firmware server choice is not visible","Выбор сервера прошивкой не виден"],["AUTOMATIC-EXTERNAL-CHANGE-READOPT","state","Old Auto session archived automatically","Старая сессия Auto архивирована автоматически"],["STATUS-REQUEST-FAILED","monitor","No answer from the router program","Нет ответа от программы на роутере"],["MONITOR-DATA-STALE","monitor","Router data is old","Данные роутера устарели"],["VENDOR-OBSERVATION-PENDING","monitor","Channel not observed yet","Канал ещё не наблюдался"],["AUTO-CONTROL-UNCONFIRMED","switch","Auto did not confirm the command","Auto не подтвердил команду"],["UI-ACTION-FAILED","monitor","The page could not finish the action","Страница не смогла выполнить действие"],["UI-RENDER-FAILED","monitor","Part of the page could not be drawn","Часть страницы не удалось показать"],["MANUAL-SWITCH-UNCONFIRMED","switch","Manual switch not confirmed","Ручное переключение не подтверждено"],["STATS-RESET-ARCHIVE-UNVERIFIED","monitor","Archive could not be read back","Архив не прочитался обратно"],["STATS-RESET-FIELDS","monitor","Reset request not accepted","Запрос сброса не принят"],["STATS-RESET-FAILED","monitor","Reset not completed","Сброс не выполнен"],["STATS-RESET-ARCHIVE-PATH","monitor","Archive folder is not safe","Папка архива небезопасна"],["STATS-RESET-UNCONFIRMED","monitor","Reset not confirmed in time","Сброс не подтверждён вовремя"],["RESERVE-ALREADY-FIRST","state","The reserve is already the router first choice","Резерв уже стоит первым у роутера"],["CHANNEL-UNRELIABLE","monitor","Channel reliability problem","Проблема с надёжностью канала"],["RESERVE-NOT-CONNECTED","switch","Reserve channel is not connected","Резервный канал не подключён"],["VENDOR-SAME-TUNNEL","switch","Server selection belongs to the router","Сервер выбирает штатная прошивка"],["SETUP-SAME-TUNNEL","setup","Choose two different tunnels","Выберите два разных туннеля"],["VENDOR-SETTLING","switch","The router is still checking VPN settings","Роутер ещё проверяет настройки VPN"],["CROSS-TUNNEL-READY","switch","This VPN pair is suitable for Auto","Эта пара VPN подходит для Auto"],["CURRENT-PROFILE-FAILURE-STREAK","switch","Current profile failed repeated checks","Текущий профиль не прошёл несколько проверок"],["RESERVE-IDENTITY-UNKNOWN","switch","Cannot find this VPN on the router","Не удаётся найти этот VPN на роутере"],["VENDOR-FIRST-OBSERVATION","data","VPN seen for the first time","VPN замечен впервые"],["VENDOR-PROFILE-CHANGED","data","Configured tunnel member changed","Профиль в конфигурации туннеля изменился"],["VENDOR-BINDING-CHANGED","data","VPN settings changed","Настройки VPN изменились"],["VENDOR-BINDING-UNKNOWN","data","VPN profile changed or removed on the router","VPN-профиль изменён или удалён на роутере"],["VENDOR-OBSERVATION-TIME","data","Invalid observation clock","Некорректное время наблюдения"],["ONBOARDING-FIELDS","setup","Setup form changed","Форма настройки изменилась"],["ONBOARDING-SYSTEM-FIELDS","setup","Check VPN setup","Проверьте настройку VPN"],["ONBOARDING-PAIR-DEFERRED","setup","Review deferred VPN pair","Проверьте отложенную пару VPN"],["ONBOARDING-APPEARANCE","setup","Check appearance defaults","Проверьте оформление по умолчанию"],["ONBOARDING-TELEGRAM-FIELDS","setup","Check optional Telegram setup","Проверьте необязательную настройку Telegram"],["ONBOARDING-TOO-LARGE","setup","Setup request is too large","Запрос настройки слишком большой"],["ONBOARDING-SAVE-UNCONFIRMED","setup","Setup save not confirmed","Сохранение настройки не подтверждено"],["CONTROL-REVISION-STALE","switch","Auto controls changed","Управление Auto изменилось"],["START-STATE-UNVERIFIED","switch","Saved Auto state unverified","Состояние Auto не проверено"],["STOP-SUPERSEDED-START","switch","Pending Start cancelled","Ожидающий запуск отменён"],["START-CONFIG-CHANGED","switch","Settings changed during Start","Настройки изменились при запуске"],["GUARD-RELEASE-ARM-FAILED","switch","Safety timer unavailable","Аварийный таймер недоступен"],["GUARD-RELEASE-UNCONFIRMED","switch","Safety block removal unconfirmed","Снятие блокировки не подтверждено"],["RELEASE-PENDING","state","Waiting for block removal","Ожидается снятие блокировки"],["RETURN-TRANSACTION-MISMATCH","switch","Old return request rejected","Старый запрос возврата отклонён"],["RETURN-REQUEST-EXPIRED","switch","Return request expired","Запрос возврата устарел"],["JOURNAL-PHASE-INVALID","switch","Invalid recovery phase","Неверная фаза восстановления"],["OBSERVING","state","Watching the primary","Слежу за основным"],["ARMED","state","Ready to switch","Готов к переключению"],["APPLYING","state","Switching now","Идёт переключение"],["WAIT-CLIENT","state","Waiting for your computer","Ждём ваш компьютер"],["COMMITTED","state","Reserve confirmed","Резерв подтверждён"],["ROLLED-BACK","state","Returned to the previous route","Возврат на прежний маршрут"],["ROLLING-BACK","state","Returning now","Возвращаюсь"],["RESTORING","state","Restoring the route","Восстанавливаю маршрут"],["TRIAL-REQUIRED","state","LAN trial needed","Нужен LAN-тест"],["BLOCKED","state","Blocked","Заблокировано"],["STOPPED","state","Stopped","Остановлен"],["STOPPED-ON-RESERVE","state","Stopped on the reserve","Остановлен на резерве"],["DEGRADED-ON-RESERVE","state","Reserve is failing too","Резерв тоже не работает"],["HELD-ON-RESERVE","state","Held on the reserve","Удерживаю на резерве"],["DISABLED","state","Auto disabled","Auto выключен"],["EXPIRED","state","Test window ended","Окно теста закончилось"],["SERVICE-STOPPED","state","Monitor service is not running","Служба мониторинга не работает"],["WAIT-CONFIRM","state","Waiting for confirmation","Ожидание подтверждения"],["CLIENT-CONFIRMED","switch","Your computer confirmed","Компьютер подтвердил"],["TRIAL-PASSED","switch","Trial passed","Тест пройден"],["TRIAL-ENDED","switch","Test window ended","Окно теста закончилось"],["SOURCE-FAILED","switch","The primary failed","Основной отказал"],["SOURCE-HEALTH-UNKNOWN","switch","Primary state unknown","Состояние основного неизвестно"],["OPERATOR-TRIAL","switch","Started by you","Запущено вами"],["OPERATOR-HOLD-RESERVE","switch","Held by your rule","Удержание по вашему правилу"],["PRIMARY-STABLY-RECOVERED","switch","Primary recovered for good","Основной стабильно восстановился"],["RESERVE-FAILED","switch","The reserve failed","Резерв отказал"],["RESERVE-FAILED-PRIMARY-VERIFIED","switch","Reserve failed, primary is fine","Резерв отказал, основной исправен"],["RESERVE-HEALTH-UNKNOWN","switch","Reserve state unknown","Состояние резерва неизвестно"],["SOURCE-NOT-VERIFIED","switch","Primary not verified","Основной не проверен"],["SUPERVISOR-RECOVERY","switch","Recovery after a restart","Восстановление после перезапуска"],["TRANSACTION-FAILED","switch","The switch failed","Переключение не удалось"],["FAILED-BEFORE-APPLY","switch","Failed before any change","Сбой до изменений"],["TIMEOUT-ELAPSED","switch","Time ran out","Время вышло"],["SELECTED-BY-CONTROLLER","switch","Chosen by the controller","Выбран контроллером"],["EDGE-NOT-CERTIFIED","switch","Works, switch not certified","Работает, переключение не подтверждено"],["THREE-CONFIRMED-FAILURES","switch","Three failures in a row","Три сбоя подряд"],["CONFIGURED-FAILURE-STREAK","switch","Failure streak reached","Достигнут порог сбоев"],["RESTORE-PRIMARY","switch","Return to the primary","Возврат на основной"],["SWITCH-RECOMMENDED","switch","A switch is recommended","Рекомендуется переключение"],["TARGET-INACTIVE","switch","Reserve not connected","Резерв не подключён"],["TARGET-NOT-READY","switch","Reserve not ready","Резерв не готов"],["PLAN-CONFIG","switch","Primary and reserve not chosen","Основной и резерв не выбраны"],["UPLINK-DOWN","switch","Provider line is down","Линия провайдера не работает"],["STOPPED-NO-HEALTHY-PATH","switch","No healthy path","Нет исправного пути"],["GUARD-RETAINED","switch","Safety block kept","Защитная блокировка сохранена"],["WATCHDOG-DID-NOT-ARM","switch","Safety timer did not start","Страхующий таймер не запустился"],["TRANSACTION-EXPIRED","switch","The switch ran out of time","Переключение не уложилось по времени"],["DNS-FAILED","monitor","Name lookup fails","Не работает поиск адресов"],["HTTPS-FAILED","monitor","HTTPS checks below threshold","HTTPS-проверки ниже порога"],["TUNNEL-DISCONNECTED","monitor","Tunnel not connected","Туннель не подключён"],["ROUTE-MISMATCH","monitor","Check did not go through the VPN","Проверка шла не через VPN"],["PATH-UNVERIFIED","monitor","Check path unconfirmed","Путь проверки не подтверждён"],["VPN-PROBE-HEALTHY","monitor","VPN works","VPN работает"],["OBSERVATION-STALE","monitor","Measurements are old","Измерения устарели"],["OBSERVATION-UNKNOWN","monitor","Not enough measurements","Мало измерений"],["LINK-UP","monitor","Link is up","Линия поднята"],["CHECK-LIMIT","monitor","Check limit reached","Достигнут лимит проверок"],["FOREIGN-GUARD-TABLE","switch","Foreign table with our name","Чужая таблица с нашим именем"],["GUARD-CHECK-FAILED","switch","Safety block rejected","Защитная блокировка отклонена"],["GUARD-INSTALL-FAILED","switch","Safety block not installed","Защитная блокировка не установлена"],["GUARD-QUERY-FAILED","switch","Safety block cannot be read","Защитная блокировка не читается"],["POLICY-DUPLICATE-IDENTITY","switch","Two identical VPN rules","Два одинаковых VPN-правила"],["POLICY-GENERATION-CHANGED","switch","Rules changed meanwhile","Правила изменились"],["POLICY-IDENTITY-CHANGED","switch","Rule identity changed","Правило изменилось"],["POLICY-REORDER-UNVERIFIED","switch","New order not confirmed","Новый порядок не подтверждён"],["SOURCE-ORDER-MISMATCH","switch","Rule order is not as expected","Порядок правил не тот"],["EXIT-CHANGED","switch","The exit address changed","Внешний адрес изменился"],["EXIT-IP-NOT-GLOBAL","switch","Exit address is private","Внешний адрес не публичный"],["JOURNAL-ORDER-INVALID","switch","Journal order invalid","Порядок в журнале неверен"],["JOURNAL-SECTION-INVALID","switch","Journal names an invalid rule","Журнал называет неверное правило"],["DEADLINE-TIMEZONE-REQUIRED","switch","Deadline needs a time zone","Для срока нужен часовой пояс"],["INVALID-ACCELERATION-REQUEST","switch","Invalid request","Неверный запрос"],["ACCELERATION-PREPARE-ATTEMPT-LIMIT","switch","Too many preparation attempts","Слишком много попыток подготовки"],["ACCELERATION-PREPARE-DURING-TRANSACTION","switch","Preparation during a switch","Подготовка во время переключения"],["HNAT-DISABLE-UNVERIFIED","switch","Hardware acceleration not confirmed off","Аппаратное ускорение не подтверждено как выключенное"],["SFE-DISABLE-UNVERIFIED","switch","Software acceleration not confirmed off","Программное ускорение не подтверждено как выключенное"],["UNEXPECTED-DEBUGFS-PATH","switch","Unexpected system path","Неожиданный системный путь"],["UNEXPECTED-HNAT-PATH","switch","Unexpected system path","Неожиданный системный путь"],["UNSAFE-FIREWALL-SECTION","switch","Unsafe firewall section name","Небезопасное имя секции брандмауэра"],["UNSAFE-GUARD-DEVICE","switch","Unsafe interface name","Небезопасное имя интерфейса"],["UNSAFE-SECTION","switch","Unsafe rule name","Небезопасное имя правила"],["FAULT-ACTIVE","switch","Failure test is running","Тест сбоя выполняется"],["FAULT-ALREADY-ACTIVE","switch","Failure test already runs","Тест сбоя уже идёт"],["FAULT-CANCELLED","switch","Failure test cancelled","Тест сбоя отменён"],["FAULT-TRANSITION-CONFIRMED","switch","Transition test passed","Тест перехода пройден"],["FAULT-TRANSITION-NOT-CONFIRMED","switch","Transition not confirmed","Переход не подтверждён"],["FAULT-CLEANED","switch","Failure test cleaned up","Тест сбоя убран"],["FAULT-NOT-ACTIVE","switch","No failure test is running","Тест сбоя не идёт"],["FAULT-NATIVE-PREREQUISITES","switch","Router checks not passed","Проверки роутера не пройдены"],["FAULT-SESSION-CONSENT-REQUIRED","switch","Reconnection not allowed","Переподключение не разрешено"],["FAULT-WINDOW-TOO-SHORT","switch","Test window too short","Окно теста слишком короткое"],["FAULT-NOT-CURRENT-SOURCE","switch","Not the current primary","Это не текущий основной"],["FAULT-HEALTHY-RESERVE-REQUIRED","switch","Reserve must be healthy","Нужен исправный резерв"],["FAULT-WOULD-REMOVE-RESERVE","switch","The test would also break the reserve","Тест сломал бы и резерв"],["FAULT-PATH-UNVERIFIED","switch","Path of the VPN not confirmed","Путь VPN не подтверждён"],["FAULT-WATCHDOG-NOT-READY","switch","Safety timer not ready","Страхующий таймер не готов"],["FAULT-UNSAFE-SCOPE","switch","Unsafe scope","Небезопасная область"],["FAULT-FOREIGN-TABLE","switch","Foreign firewall table","Чужая таблица брандмауэра"],["FAULT-TIMEOUT-RULE-FAILED","switch","Automatic end could not be set","Автоматическое окончание не задано"],["FAULT-APPLY-UNCONFIRMED","switch","Block not confirmed","Блокировка не подтверждена"],["FAULT-CLEANUP-UNCONFIRMED","switch","Removal not confirmed","Снятие не подтверждено"],["FAULT-STATE-UNVERIFIED","switch","Test state unverified","Состояние теста не подтверждено"],["FAULT-HISTORY-CORRUPT","switch","Test history damaged","История тестов повреждена"],["FAULT-WORKER-INVALID","switch","Helper process invalid","Вспомогательный процесс недействителен"],["FAULT-WORKER-STALE","switch","Helper process stale","Вспомогательный процесс устарел"],["TELEGRAM-FORMAT-FAILED","telegram","Report could not be formed","Отчёт не сформирован"],["TELEGRAM-REPORT-UNAVAILABLE","telegram","Report data not available","Данные для отчёта недоступны"],["TELEGRAM-REQUEST-REJECTED","telegram","Telegram rejected the request","Telegram отклонил запрос"],["TELEGRAM-RETRY","telegram","Will retry","Повторю отправку"],["TELEGRAM-SCHEDULE","telegram","Invalid schedule","Неверное расписание"],["TELEGRAM-SETUP-FIELDS","telegram","Wrong fields","Неверные поля"],["TELEGRAM-STATE-RECOVERED","telegram","Report state recovered","Состояние отчётов восстановлено"],["TELEGRAM-STATE-WRITE-FAILED","telegram","Report state not saved","Состояние отчётов не сохранено"],["TELEGRAM-TEST-RATE-LIMIT","telegram","Test message too often","Тестовое сообщение слишком часто"],["SETUP-FIELDS","setup","Wrong fields in the form","Неверные поля формы"],["SETUP-KIND","setup","Unknown setup kind","Неизвестный вид настройки"],["SETUP-NAME","setup","Invalid name","Неверное название"],["SETUP-SERVER","setup","Invalid server row","Неверная строка сервера"],["SETUP-DELTA-UNVERIFIED","setup","Unsaved changes unverifiable","Несохранённые изменения не проверить"],["SETUP-CHECK-OK","setup","Settings writer works","Запись настроек работает"],["SETUP-CHECK-FAILED","setup","Settings writer self-check failed","Самопроверка записи настроек не прошла"],["TERMS-VERSION","setup","Terms version mismatch","Версия условий не совпадает"],["MONITOR-PREFERENCES-FIELDS","setup","Wrong fields","Неверные поля"],["PRIORITY-SAVED","setup","Priorities saved","Приоритеты сохранены"],["PRIORITY-SAVE-FAILED","setup","Priorities not saved","Приоритеты не сохранены"],["PRIORITY-STALE-REVIEW","setup","The review is outdated","Просмотр устарел"],["PRIORITY-FIELDS","setup","Wrong fields","Неверные поля"],["PRIORITY-INVALID-SELECTION","setup","Invalid selection","Неверный выбор"],["PRIORITY-PROFILE-INELIGIBLE","setup","Server not eligible","Сервер не подходит"],["RECOVERY-FIELDS","setup","Wrong fields","Неверные поля"],["RECOVERY-RANGE","setup","Value out of range","Значение вне диапазона"],["RECOVERY-REQUIRED","setup","Recovery rules required","Нужны правила восстановления"],["RECOVERY-RETURN-POLICY","setup","Invalid return rule","Неверное правило возврата"],["CONFIG-STOP-AUTO-FIRST","setup","Stop Auto first","Сначала остановите Auto"],["CONFIG-RECOVERY-UNVERIFIED","setup","Configuration cannot be confirmed","Конфигурацию не подтвердить"],["CONFIG-STORAGE-FREE","data","Not enough free space","Мало свободного места"],["LIFECYCLE-STOP-AUTO-FIRST","service","Stop Auto first","Сначала остановите Auto"],["STORAGE-001","data","Router storage problem","Проблема с хранилищем роутера"],["STORAGE-RECOVERED","data","Storage recovered","Хранилище восстановлено"],["SCAN-MEASUREMENT-FAILED","speed","Check request failed","Запрос проверки не удался"],["SCAN-SNAPSHOT-MISMATCH","speed","Measurement does not match","Измерение не совпало"],["SCAN-STORAGE","speed","Request not saved","Запрос не сохранён"],["RPC-DUPLICATE-FIELD","service","Duplicate field in a request","Повтор поля в запросе"],["RPC-INPUT-COMPLEXITY","service","Request too complex","Запрос слишком сложный"],["RPC-INPUT-DEPTH","service","Request too deep","Запрос слишком вложенный"],["RPC-INPUT-OBJECT","service","Request has a wrong form","Запрос неверного вида"],["RPC-NONFINITE-NUMBER","service","Invalid number","Неверное число"],["OFFLINE-FIXTURE","data","Test data of the offline preview","Тестовые данные офлайн-просмотра"],["AUTO-STOP-QUEUED","switch","Stop was queued","Остановка поставлена в очередь"],["RETURN-REFUSED","switch","Return refused","Возврат отклонён"],["RECOVERY-SAVED","setup","Recovery rules saved","Правила восстановления сохранены"],["RECOVERY-SAVE-FAILED","setup","Recovery rules not saved","Правила восстановления не сохранены"],["RECOVERY-SAVE-UNCONFIRMED","setup","Save not confirmed","Сохранение не подтверждено"],["SPEED-CONFIG-SAVED","speed","Speed settings saved","Настройки скорости сохранены"],["SPEED-CONFIG-FAILED","speed","Speed settings not saved","Настройки скорости не сохранены"],["SPEED-QUEUED","speed","Speed test queued","Тест скорости поставлен в очередь"],["SPEED-START-FAILED","speed","Speed test did not start","Тест скорости не запустился"],["SPEED-CANCEL-QUEUED","speed","Cancel queued","Отмена поставлена в очередь"],["SCAN-ACK-UNCONFIRMED","speed","Check request not confirmed","Запрос проверки не подтверждён"],["SCAN-SNAPSHOT-UNCONFIRMED","speed","Result not confirmed","Результат не подтверждён"],["MONITOR-PREFERENCES-SAVED","setup","Monitoring preferences saved","Параметры мониторинга сохранены"],["MONITOR-PREFERENCES-FAILED","setup","Monitoring preferences not saved","Параметры мониторинга не сохранены"],["MONITOR-PREFERENCES-UNCONFIRMED","setup","Save not confirmed","Сохранение не подтверждено"],["MONITOR-UNKNOWN","service","Monitor answer unknown","Ответ мониторинга неизвестен"],["PRIORITY-PREVIEW-FAILED","setup","Preview failed","Просмотр не удался"],["PRIORITY-PREVIEW-UNCONFIRMED","setup","Preview not confirmed","Просмотр не подтверждён"],["PRIORITY-RPC-UNCONFIRMED","setup","Answer not confirmed","Ответ не подтверждён"],["PRIORITY-SELECT-ELIGIBLE-SERVERS","setup","Choose servers first","Сначала выберите серверы"],["PRIORITY-UNKNOWN","setup","Priority answer unknown","Ответ по приоритетам неизвестен"],["RECOVERY-PERIOD","setup","Invalid period","Неверный период"],["RPC-INVENTORY-INVALID","service","Router list unreadable","Список роутера нечитаем"],["RPC-INVENTORY-UNAVAILABLE","service","Router list unavailable","Список роутера недоступен"],["TELEGRAM-FORGET-UNCONFIRMED","telegram","Token removal not confirmed","Удаление токена не подтверждено"],["TERMS-SAVE-FAILED","setup","Terms not saved","Условия не сохранены"],["TERMS-SAVE-UNCONFIRMED","setup","Acceptance not confirmed","Принятие не подтверждено"],["CAUSE-UNKNOWN","data","Cause not known","Причина неизвестна"],["UNKNOWN-FUTURE-TIMESTAMP","data","Time in the future","Время из будущего"],["EXPORT-KIND","data","Unknown export","Неизвестный экспорт"],["DEPENDENCY-IP","service","Program “ip” missing","Нет программы «ip»"],["DEPENDENCY-LUA","service","Lua missing","Нет Lua"],["DEPENDENCY-UBUS","service","ubus missing","Нет ubus"],["DEPENDENCY-UCI","service","UCI missing","Нет UCI"],["SPEED-COMPLETE","speed","Speed test finished","Тест скорости завершён"],["SPEED-NOT-RUNNING","speed","No speed test is running","Тест скорости не идёт"],["SPEED-NO-SAMPLE","speed","No measurement","Нет измерения"],["SPEED-CPU-BUSY","speed","Router is busy","Роутер занят"],["SPEED-TRAFFIC-UNKNOWN","speed","Traffic unknown","Трафик неизвестен"],["SPEED-SWITCH-IN-PROGRESS","speed","A switch is running","Идёт переключение"],["SPEED-PROFILES","speed","No server chosen","Сервер не выбран"],["SPEED-PROFILES-CHANGED","speed","Server list changed","Список серверов изменился"],["SPEED-CONFIG-LIMIT","speed","Limit exceeded","Лимит превышен"],["AUTO-OPTIONS-NOT-CLEARED","switch","Auto settings could not be reset","Настройки Auto не удалось сбросить"],["BOARD-OVERSIZE","service","Router board data too big","Данные о плате роутера слишком велики"],["CA-BUNDLE","service","Certificates package missing","Нет пакета сертификатов"],["LUCI-CACHE-ROOT","service","Page cache folder is wrong","Папка кэша страниц неверна"],["PYTHON-39-MINIMUM","service","Python is too old","Python слишком старый"],["SPEED-WORKER-TIMEOUT","speed","Test took too long","Тест шёл слишком долго"],["PREPARATION-*","setup","Router preparation action","Действие подготовки роутера"],["LATENCY-*","data","Delay history unavailable","История задержки недоступна"],["ENDPOINT-*","data","Current server address not observed","Текущий адрес сервера не получен"],["STATISTICS-*","data","Saved statistics check","Проверка сохранённой статистики"],["PREP-*","platform","Persistent router preparation (PREP-…)","Постоянная подготовка роутера (PREP-…)"],["PAIR-*","internal","Two-channel Auto (PAIR-…)","Авторежим двух каналов (PAIR-…)"],["CASCADE-*","internal","Internal check of the fallback model (CASCADE-…)","Внутренняя проверка модели каскада (CASCADE-…)"],["CANDIDATE-*","internal","Internal check of candidate probing (CANDIDATE-…)","Внутренняя проверка пробы кандидатов (CANDIDATE-…)"],["MODEL-*","internal","Internal check of the switching model (MODEL-…)","Внутренняя проверка модели переключения (MODEL-…)"],["CHECKPOINT-*","data","Saved statistics file check (CHECKPOINT-…)","Проверка файла сохранённой статистики (CHECKPOINT-…)"],["MIGRATION-*","data","Settings upgrade check (MIGRATION-…)","Проверка обновления настроек (MIGRATION-…)"],["HISTORY-*","data","Controller history check (HISTORY-…)","Проверка истории контроллера (HISTORY-…)"],["LIFECYCLE-*","service","Upgrade and service safety check (LIFECYCLE-…)","Проверка безопасности обновления и службы (LIFECYCLE-…)"],["SPEED-*","speed","Speed test code (SPEED-…)","Код теста скорости (SPEED-…)"],["FAULT-*","switch","Failure test code (FAULT-…)","Код теста сбоя (FAULT-…)"],["TELEGRAM-*","telegram","Telegram code (TELEGRAM-…)","Код Telegram (TELEGRAM-…)"],["SETUP-*","setup","Settings code (SETUP-…)","Код настроек (SETUP-…)"],["PRIORITY-*","setup","Priorities code (PRIORITY-…)","Код приоритетов (PRIORITY-…)"],["RECOVERY-*","setup","Recovery rules code (RECOVERY-…)","Код правил восстановления (RECOVERY-…)"],["RPC-*","service","Request to the router (RPC-…)","Запрос к роутеру (RPC-…)"],["SCAN-*","speed","Check request code (SCAN-…)","Код запроса проверки (SCAN-…)"],["DEPENDENCY-*","service","Missing program (DEPENDENCY-…)","Не хватает программы (DEPENDENCY-…)"],["GUARD-*","switch","Safety block code (GUARD-…)","Код защитной блокировки (GUARD-…)"],["POLICY-*","switch","VPN rules code (POLICY-…)","Код VPN-правил (POLICY-…)"],["JOURNAL-*","switch","Switch journal code (JOURNAL-…)","Код журнала переключения (JOURNAL-…)"],["UNSAFE-*","switch","Unsafe name (UNSAFE-…)","Небезопасное имя (UNSAFE-…)"],["GUARD-DEVICE-UNVERIFIED","switch","VPN interface state unavailable","Состояние VPN-интерфейса недоступно"],["LAN-TRIAL-REQUIRED","switch","LAN trial required","Нужен LAN-тест"],["BOUNDED-DEADLINE-REQUIRED","switch","Test window missing","Нет окна теста"],["SESSION-LOSS-NOT-ACCEPTED","switch","Reconnection not accepted","Не разрешён разрыв сессий"],["TRANSACTION-IN-PROGRESS","switch","Switch in progress","Переключение идёт"],["TRIAL-ATTEMPT-LIMIT","switch","Trial attempt limit","Лимит попыток теста"],["UNSUPPORTED-BOARD","switch","Unsupported router model","Неподдерживаемая модель роутера"],["UNSUPPORTED-FIRMWARE","switch","Unsupported firmware","Неподдерживаемая прошивка"],["FIRMWARE-UNKNOWN","switch","Firmware unknown","Прошивка неизвестна"],["VENDOR-CODE-CHANGED","switch","GL.iNet code changed","Код GL.iNet изменился"],["VENDOR-CODE-UNVERIFIED","switch","GL.iNet code unverified","Код GL.iNet не проверен"],["VENDOR-WORKER-BUSY","switch","GL.iNet program is busy","Программа GL.iNet занята"],["HARDWARE-ACCELERATOR-UNVERIFIED","switch","Hardware acceleration unverified","Аппаратное ускорение не проверено"],["SOFTWARE-ACCELERATOR-UNVERIFIED","switch","Software acceleration unverified","Программное ускорение не проверено"],["FLOW-OFFLOAD-ENABLED","switch","Flow offload is on","Включён flow offload"],["IPV6-NOT-EXPLICITLY-DISABLED","switch","IPv6 not disabled","IPv6 не отключён"],["KILLSWITCH-NOT-ENABLED","switch","Kill Switch is off","Kill Switch выключен"],["DIRECT-WAN-FALLBACK","switch","Direct exit without VPN possible","Возможен выход мимо VPN"],["VPN-POLICY-DISABLED","switch","VPN policy is off","Политика VPN выключена"],["TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED","switch","Two to sixteen rules needed","Нужно от 2 до 16 правил VPN"],["GENERIC-RULES-NOT-ADJACENT","switch","Rules not adjacent","Правила идут не подряд"],["GENERIC-DUPLICATE-INTERFACE","switch","Duplicate interface","Повтор интерфейса"],["SPECIAL-RULES-MUST-PRECEDE-GENERIC","switch","Special rules in wrong order","Особые правила в неверном порядке"],["SOURCE-RESERVE-NOT-CONFIGURED","switch","Primary or reserve not set","Основной или резерв не заданы"],["PROFILE-INACTIVE","switch","Profile not connected","Профиль не подключён"],["PROFILES-NOT-GENERIC-RULES","switch","Profiles not in general rules","Профили не в общих правилах"],["SAME-INTERFACE","switch","Same interface twice","Один интерфейс дважды"],["POLICY-ORDER-DIRECTION-UNVERIFIED","switch","Rule order direction unverified","Направление порядка правил не проверено"],["LAN-LAYOUT-UNSUPPORTED","switch","Unsupported LAN layout","Неподдерживаемая схема LAN"],["PROFILE-NOT-MONITORED","switch","Profile not monitored","Профиль не наблюдается"],["NFT-GUARD-UNAVAILABLE","switch","Safety block unavailable","Страхующая блокировка недоступна"],["POLICY-READ-FAILED","switch","Cannot read VPN rules","Не удаётся прочитать правила VPN"],["UPLINK-LINK-DOWN","switch","Uplink is down","Внешний канал отключён"],["LEASE-INTEGRITY-FAILED","switch","Lease damaged","Аренда повреждена"],["LEASE-STORAGE-FAILED","switch","Lease cannot be saved","Аренда не сохраняется"],["LEGACY-LEASE-RECOVERY","switch","Old lease recovered","Восстановлена старая аренда"],["EXTERNAL-POLICY-CHANGE-GUARD-RETAINED","switch","Outside change, block kept","Изменение извне, блокировка сохранена"],["ROLLBACK-UNVERIFIED-GUARD-RETAINED","switch","Return unverified, block kept","Возврат не подтверждён, блокировка сохранена"],["CLIENT-CONFIRMATION-TIMEOUT","switch","Computer did not confirm","Компьютер не подтвердил"],["CLIENT-STOP","switch","Stopped by the helper","Остановлено помощником"],["TARGET-HTTPS-DNS-FAILED","switch","Reserve check failed","Проверка резерва не прошла"],["LAN-BASELINE-NOT-SOURCE","switch","Computer was not on the primary","Компьютер был не на основном"],["RESERVE-EXIT-NOT-DISTINCT","switch","Reserve exit equals primary","Выход резерва совпал с основным"],["VENDOR-APPLY-FAILED","switch","GL.iNet did not apply the change","GL.iNet не применил изменение"],["POLICY-CHANGED-DURING-APPLY","switch","Rules changed during the switch","Правила изменились во время переключения"],["NATIVE-SYSTEM-001","switch","System check failed","Проверка системы не прошла"],["TERMS-NOT-ACCEPTED","switch","Terms not accepted","Условия не приняты"],["RETURN-NOT-APPLICABLE","switch","Nothing to return","Возвращать нечего"],["SOURCE-NOT-HEALTHY","switch","Primary not healthy yet","Основной ещё не исправен"],["JOURNAL-UNVERIFIED","switch","Journal unverified","Журнал не проверен"],["EXTERNAL-POLICY-CHANGE","switch","Changed from outside","Изменено извне"],["EXTERNAL-POLICY-CHANGE-RELEASED","switch","Changed from outside, block removed","Изменено извне, блокировка снята"],["ROLLBACK-UNVERIFIED","switch","Return unverified","Возврат не подтверждён"],["ENVIRONMENT-EVIDENCE-UNAVAILABLE","switch","No data about the router","Нет данных о роутере"],["MONITOR-EVIDENCE-STALE","switch","Monitor data is old","Данные мониторинга устарели"],["NATIVE-START-CERTIFICATION-REQUIRED","switch","Checked again at Start","Повторная проверка при запуске"],["OPERATOR-RETURN","switch","Return-control command","Команда возврата маршрута"],["PRIMARY-RECOVERED","switch","Primary recovered","Основной восстановился"],["PAIR-STATE-UNVERIFIED","switch","Settings were changed outside the app","Настройки изменены вне приложения"],["PAIR-PROFILES-UNVERIFIED","switch","Review the current VPN pair","Проверьте текущую пару VPN"],["PAIR-PREPARATION-REQUIRED","switch","Complete router preparation","Завершите подготовку роутера"],["PREP-HNAT-CONFIG","switch","Disable network acceleration","Отключите сетевое ускорение"],["PREP-WGCLIENT1-AUTOSTART","switch","Review wgclient1 startup","Проверьте автозапуск wgclient1"],["PREP-OVPNCLIENT1-AUTOSTART","switch","Review ovpnclient1 startup","Проверьте автозапуск ovpnclient1"],["PREP-STOCK-VPN-BOOT","switch","Disable competing VPN startup","Отключите конкурирующий автозапуск VPN"],["PREP-SFE-BOOT","switch","Disable network acceleration","Отключите сетевое ускорение"],["PREP-SFE-AUTOLOAD","switch","Disable network acceleration","Отключите сетевое ускорение"],["PREP-SFE-RUNTIME","switch","Disable network acceleration","Отключите сетевое ускорение"],["PREPARATION-RESTART-REQUIRED","switch","Router restart required","Нужна перезагрузка роутера"],["PREPARATION-RECOVERY-REQUIRED","switch","Complete router preparation","Завершите подготовку роутера"],["PREP-SOURCE-AUTOSTART","switch","Disable primary VPN boot startup","Отключите автозапуск основного VPN"],["PREP-TARGET-AUTOSTART","switch","Disable reserve VPN boot startup","Отключите автозапуск резервного VPN"],["GL-ADAPTER-UNVERIFIED","switch","GL.iNet VPN manager","Менеджер VPN GL.iNet"],["WORKER-COORDINATION-UNVERIFIED","switch","GL.iNet background programs","Фоновые программы GL.iNet"],["LAN-PATH-UNVERIFIED","switch","Path of a home computer","Путь домашнего компьютера"],["DNS-POLICY-UNVERIFIED","switch","Name lookups (DNS)","Поиск адресов (DNS)"],["KILLSWITCH-UNVERIFIED","switch","Kill Switch","Kill Switch"],["IPV6-POLICY-UNVERIFIED","switch","IPv6 traffic","Трафик IPv6"],["WATCHDOG-UNVERIFIED","switch","Safety timer","Страхующий таймер"],["SCOPED-CONNTRACK-UNVERIFIED","switch","Open connections","Открытые соединения"],["EVENT-CHECK-OK","journal","Check passed","Проверка прошла"],["EVENT-CHECK-FAILED","journal","Check failed","Ошибка проверки"],["EVENT-CONNECTION-RECOVERED","journal","Availability restored","Доступность восстановлена"],["EVENT-PROFILE-DISABLED","journal","Profile disabled","Профиль отключён"],["EVENT-OBSERVATION-GAP","journal","No observation interval","Перерыв наблюдений"],["EVENT-MONITORING","journal","Observing channels","Наблюдение за каналами"],["EVENT-START-CONFIRMATION-PENDING","journal","Start awaiting confirmation","Запуск ожидает подтверждения"],["EVENT-CHANNEL-PREPARATION","journal","Preparing channels","Подготовка каналов"],["EVENT-ROUTE-APPLYING","journal","Selecting route","Выбор маршрута"],["EVENT-PATH-CONFIRMATION","journal","Verifying path","Подтверждение пути"],["EVENT-RESERVE-SELECTED","journal","Reserve selected","Резерв выбран"],["EVENT-RESERVE-HELD","journal","Reserve retained","Резерв удержан"],["EVENT-RETURN-IN-PROGRESS","journal","Returning route","Возврат маршрута"],["EVENT-ROLLBACK-RECORDED","journal","Rollback recorded","Записан откат"],["EVENT-ORIGINAL-RESTORED","journal","Original route restored","Исходный маршрут восстановлен"],["EVENT-OPERATION-STOPPED","journal","Operation stopped","Операция остановлена"],["EVENT-AUTO-RUNNING","journal","Auto running","Auto работает"],["EVENT-AUTO-START-REQUESTED","journal","Start requested","Запрошен запуск"],["EVENT-AUTO-STOP-REQUESTED","journal","Stop requested","Запрошена остановка"],["EVENT-OPERATION-BLOCKED","journal","Action refused","Действие отклонено"],["EVENT-OPERATION-FAILED","journal","Operation failed","Операция не выполнена"],["EVENT-WINDOW-EXPIRED","journal","Test window ended","Окно теста завершено"],["EVENT-RECOVERY-PENDING","journal","Recovery pending","Восстановление ожидается"],["EVENT-RESERVE-DEGRADED","journal","Reserve check failed","Проблема на резерве"],["EVENT-TRIAL-PREREQUISITE","journal","Mode prerequisite missing","Не выполнено условие режима"],["EVENT-DETAILS-NOT-SAVED","journal","Record lacks detail","Подробности не сохранены"],["EVENT-RECORD-CONFLICT","journal","Record data conflict","Ошибка данных записи"],["EVENT-COMMAND-CANCELLED","journal","Command cancelled","Команда отменена"],["EVENT-COMMAND-ACCEPTED","journal","Command accepted","Команда принята"],["EVENT-COMMAND-QUEUED","journal","Command queued","Команда в очереди"],["EVENT-CONTROLLER-IDLE","journal","Waiting for a command","Ожидание команды"],["EVENT-RESULT-NEEDS-VERIFICATION","journal","Verify the result","Нужна проверка результата"],["EVENT-CHANNEL-SELECTION","journal","Channel selection record","Запись выбора канала"],["EVENT-POLICY-REAPPLY","journal","VPN rules applied again","Повторное применение правил VPN"],["EVENT-ROUTER-OBSERVATION","journal","Router state observation","Наблюдение состояния роутера"],["EVENT-DIRECTION-NOT-SAVED","journal","Switch direction not recorded","Направление перехода не сохранено"],["EVENT-VENDOR-WAIT","journal","Waiting for router operation","Ожидание операции роутера"]];
var HELP_TOPICS=[{"id":"telegram","steps":[{"t":["Open the official https://t.me/BotFather in Telegram and send /newbot there, not in a terminal. Follow its current instructions.","Откройте официальный https://t.me/BotFather в Telegram и отправьте /newbot именно в его чат, а не в терминал. Следуйте его текущим указаниям."],"c":"/newbot"},{"t":["BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).","BotFather спросит имя (показывается в чате, любой текст, например «Мой VPN роутер») и затем username, который должен заканчиваться на «bot» (например my_router_vpn_bot)."],"c":null},{"t":["BotFather provides the bot token. Treat it as a password and paste it only into the dedicated private token field. Do not put it into a browser URL, chat, Git or diagnostic output.","BotFather выдаёт токен бота. Храните его как пароль и вставляйте только в специальное приватное поле токена. Не помещайте его в адрес браузера, чат, Git или диагностический вывод."],"c":null},{"t":["Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.","Откройте нового бота (ссылка в конце сообщения BotFather, https://t.me/<username_вашего_бота>) и нажмите Start или отправьте /start. Бот не может написать вам первым."],"c":null},{"t":["To read chat.id without adding a third-party bot, send /start or a message to your own bot, then use this PowerShell recipe locally. It asks for the token privately and prints only IDs. Do not record a transcript or share raw updates. If another bot program consumes updates, stop and inspect that configuration rather than invent an ID.","Чтобы узнать chat.id без стороннего бота, отправьте /start или сообщение своему боту и выполните этот PowerShell-пример локально. Токен вводится скрыто, выводятся только ID. Не ведите transcript и не передавайте полный ответ. Если обновления забирает другая программа бота, сначала разберитесь с её настройкой, не придумывайте ID."],"c":"$privateKey = Read-Host 'Bot token' -AsSecureString\n$botKey = [Net.NetworkCredential]::new('', $privateKey).Password\ntry {\n    $updates = Invoke-RestMethod -Uri ('https://api.telegram.org/bot' + $botKey + '/getUpdates') -TimeoutSec 15 -ErrorAction Stop\n    $ids = foreach ($item in $updates.result) {\n        foreach ($kind in @('message','channel_post','edited_message','my_chat_member')) {\n            if ($null -ne $item.$kind.chat.id) { [string]$item.$kind.chat.id }\n        }\n    }\n    $ids | Sort-Object -Unique\n} catch { Write-Output 'CHAT-ID-NOT-READ: check the bot token, a fresh /start and other update consumers.' }\nfinally { Remove-Variable privateKey,botKey,updates,ids -ErrorAction SilentlyContinue }"}]}];
function richText(text){return String(text).split('`').map(function(part,i){return i%2?E('code',{'class':'hv-code'},part):part;});}
function helpCommand(command){
  var button=E('button',{'type':'button','class':'cbi-button','click':function(){
    try{navigator.clipboard.writeText(command).then(function(){button.textContent=bi('Copied','Скопировано');}).catch(function(){});}catch(error){}
  }},bi('Copy','Копировать'));
  return E('div',{'class':'hv-cmd-row'},[E('pre',{'class':'hv-cmd'},command),button]);
}

// Opens a Help topic from anywhere (used by the LAN trial card in Settings).
function openHelpTopic(id){
  var link=document.querySelector('[data-hv-tab="help"]');if(link)link.click();
  LAZY_HELP.pendingTopic=id;return ensureLazyPage('help').then(function(){lazyHelpDeepLink('help');});
}
function helpLink(id,label){return E('a',{'href':'#help','class':'hv-help-link','click':function(ev){ev.preventDefault();openHelpTopic(id);}},label);}
// Settings > Automatic switching: why the LAN helper exists, how to get it, where the full guide and the AI prompt are.
function lanHelperExplain(){
  return E('div',{'class':'hv-lan-explain'},[
    E('h4',{},bi('Optional check from a LAN device','Дополнительная проверка с устройства в LAN')),
    E('p',{},bi('Prepared MT3000 two-channel Auto checks DNS/HTTPS on the router and does not require a continuously running LAN helper. A separate LAN test measures what a real computer receives through the router. An AI agent can run the same test if it has tools on that computer; a hosted chat alone cannot replace this measurement.','Auto двух каналов на подготовленном MT3000 проверяет DNS/HTTPS самим роутером и не требует постоянно запущенного LAN-помощника. Отдельный LAN-тест проверяет связь реального компьютера через роутер. ИИ-агент может выполнить тот же тест, если у него есть инструменты на этом компьютере; облачный чат сам по себе это измерение не заменяет.')),
    E('p',{},bi('Choose manual instructions or an AI prompt below. Start with check-only mode. A full client-confirmed trial is a separate bounded mode that can interrupt sessions; it is not a prerequisite for router-probed IPv4 Auto.','Выберите ручную инструкцию или промпт для ИИ ниже. Начните с режима проверки без переключения. Полный тест с подтверждением клиента — отдельный ограниченный режим с возможным обрывом сеансов; для router-probed IPv4 Auto он не обязателен.')),
    E('p',{},[helpLink('helper-what',bi('Manual LAN check instructions','Проверить LAN самостоятельно')),' · ',helpLink('ai-lan-prompt',bi('Copy an AI testing prompt','Промпт для проверки с ИИ')),' · ',helpLink('ai-prompt',bi('AI installation and setup','Установка и настройка с ИИ')),' · ',helpLink('helper',bi('Help with a failed check','Помощь при ошибке проверки'))])]);
}

/* Versioned optional pages. Hosts are synchronous; module acquisition starts only on navigation. */
var LAZY_HELP_NAME='homensai-vpn.help128';
var LAZY_HELP={api:null,promise:null,failed:false,attempt:0,hosts:Object.create(null),inventory:null,pendingTopic:null,pendingCode:null};
var helpNode=null,learnNode=null,errorTable=null,ERROR_GROUP_OF={},ERROR_GROUPS=[],ERROR_TABLE_STATE={query:'',open:Object.create(null),selected:null};
var ERROR_FAMILIES=ERROR_ROWS.filter(function(row){return row[0].endsWith('*');}).map(function(row){return [row[0].slice(0,-1)].concat(row.slice(1));});
ERROR_ROWS.forEach(function(row){ERROR_GROUP_OF[row[0]]=row[1];if(!ERROR_GROUPS.some(function(g){return g[0]===row[1];}))ERROR_GROUPS.push([row[1],[row[1],row[1]]]);});
function errorFamilyOf(code){return ERROR_FAMILIES.find(function(row){return code.indexOf(row[0])===0;})||null;}
function persistErrorTableState(){try{sessionStorage.setItem('homensai-vpn-error-table',JSON.stringify(ERROR_TABLE_STATE));}catch(error){}}
function lazyHelpRoute(route){
  if(typeof route!=='string')return;
  if(route.indexOf('help/topic/')===0&&/^[a-zA-Z0-9_-]{1,96}$/.test(route.slice(11)))LAZY_HELP.pendingTopic=route.slice(11);
}
function lazyHelpDeepLink(key){
  if(!LAZY_HELP.api||typeof document==='undefined')return;
  if(typeof pageKeyNow==='function'&&pageKeyNow()!==key)return;
  if(key==='help'&&LAZY_HELP.pendingTopic){var topic=document.getElementById('help-'+LAZY_HELP.pendingTopic);if(topic){LAZY_HELP.pendingTopic=null;topic.open=true;try{topic.scrollIntoView({block:'start'});}catch(error){}}}
  if(key==='events'&&LAZY_HELP.pendingCode){var code=LAZY_HELP.pendingCode;LAZY_HELP.pendingCode=null;showErrorCode(code);}
}
function lazyHelpStatus(host,failed){
  while(host.firstChild)host.removeChild(host.firstChild);
  host.appendChild(E('p',{'role':failed?'alert':'status'},failed?['UI-HELP-LOAD-FAILED: ',bi('Help could not be loaded. Try again.','Не удалось загрузить справку. Повторите попытку.')]:bi('Loading…','Загрузка…')));
  if(failed)host.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){return loadLazyHelp(true).then(function(){lazyHelpDeepLink(typeof pageKeyNow==='function'?pageKeyNow():'');});}},bi('Retry','Повторить')));
}
function renderLazyPage(key,inventory){
  if(inventory)LAZY_HELP.inventory=inventory;
  if(!LAZY_HELP.hosts[key]){var host=E('div',{'data-hv-lazy-page':key});LAZY_HELP.hosts[key]={node:host,ready:false,requested:false};lazyHelpStatus(host,LAZY_HELP.failed);}
  return LAZY_HELP.hosts[key].node;
}
function renderHelp(inventory){return renderLazyPage('help',inventory);}
function renderLearn(){return renderLazyPage('learn');}
function renderErrorTable(){return renderLazyPage('events');}
function mountLazyHelp(){
  if(!LAZY_HELP.api)return;
  Object.keys(LAZY_HELP.hosts).forEach(function(key){var item=LAZY_HELP.hosts[key];if(item.ready||!item.requested)return;
    var renderer={help:'renderHelp',learn:'renderLearn',events:'renderErrorTable'}[key],node=LAZY_HELP.api[renderer](LAZY_HELP.inventory);
    while(item.node.firstChild)item.node.removeChild(item.node.firstChild);item.node.appendChild(node);item.ready=true;
  });
}
function lazyHelpContext(){return {E:E,bi:bi,locale:locale,richText:richText,helpCommand:helpCommand,
  READINESS_GUIDES:READINESS_GUIDES,READINESS_CHECKS:READINESS_CHECKS,renderReadinessHelp:renderReadinessHelp,
  renderAutoRemedy:renderAutoRemedy,AUTO_BLOCKERS:AUTO_BLOCKERS,AUTO_REMEDIES:AUTO_REMEDIES,autoRemedyKey:autoRemedyKey,
  PLAN_BLOCKERS:PLAN_BLOCKERS,errorCodeLink:errorCodeLink,ensureJournalDictionary:ensureJournalDictionary,extraHelpTopics:HELP_TOPICS,
  // The catalogue restored its validated session state. Eager defaults must not overwrite it;
  // an explicit code clicked while loading is applied afterwards by lazyHelpDeepLink.
  installCatalogue:function(value){ERROR_ROWS=value.rows;ERROR_GROUPS=value.groups;ERROR_GROUP_OF=value.groupOf;ERROR_TABLE_STATE=value.state;persistErrorTableState=value.persist;}
};}
function lazyHelpRequire(retry){
  if(!retry)return L.require(LAZY_HELP_NAME);
  // LuCI 23.05 caches rejected require promises. Retry the same pinned class with its factory contract.
  var path=LAZY_HELP_NAME.replace(/\./g,'/')+'.js';
  return request.get(L.resource(path)+'?retry='+LAZY_HELP.attempt,{cache:false}).then(function(response){
    if(!response.ok)throw new Error('UI-HELP-LOAD-FAILED');
    var klass=new Function('window','document','L','baseclass',response.text())(window,document,L,baseclass);
    if(!klass||typeof klass.instantiate!=='function')throw new Error('UI-HELP-LOAD-FAILED');
    // The installed 4.11.0 Class.instantiate forwards an explicit arguments array.
    return klass.instantiate([]);
  });
}
function loadLazyHelp(retry){
  if(LAZY_HELP.api){mountLazyHelp();return Promise.resolve(LAZY_HELP.api);}
  if(LAZY_HELP.promise)return LAZY_HELP.promise;
  if(LAZY_HELP.failed&&!retry)return Promise.resolve(null);
  LAZY_HELP.failed=false;LAZY_HELP.attempt++;
  Object.keys(LAZY_HELP.hosts).forEach(function(key){lazyHelpStatus(LAZY_HELP.hosts[key].node,false);});
  LAZY_HELP.promise=Promise.resolve().then(function(){return lazyHelpRequire(retry);}).then(function(module){
    if(!module||typeof module.create!=='function')throw new Error('UI-HELP-LOAD-FAILED');
    LAZY_HELP.api=module.create(lazyHelpContext());mountLazyHelp();return LAZY_HELP.api;
  }).catch(function(){LAZY_HELP.api=null;LAZY_HELP.failed=true;Object.keys(LAZY_HELP.hosts).forEach(function(key){LAZY_HELP.hosts[key].ready=false;lazyHelpStatus(LAZY_HELP.hosts[key].node,true);});return null;
  }).then(function(value){LAZY_HELP.promise=null;return value;});return LAZY_HELP.promise;
}
function ensureLazyPage(key,inventory){
  if(['help','learn','events'].indexOf(key)<0)return Promise.resolve(null);
  renderLazyPage(key,inventory);LAZY_HELP.hosts[key].requested=true;return loadLazyHelp(false);
}

/* First-run terms. The same points are in DISCLAIMER.md / DISCLAIMER.ru.md. Acceptance is stored on the router
   (terms_version, terms_time); the controller refuses to switch and Auto refuses to start until it is stored. */
var TERMS_VERSION='1';
// BEGIN GENERATED LEGAL REFERENCE
var TERMS_FULL_EN="# Experimental software: terms of use\n\n[Русский](DISCLAIMER.ru.md)\n\n**HomenS.AI Auto VPN is experimental software (alpha).** Read this before you install or use it. The same text is shown in the program the first time you open it, and Auto cannot be started until you accept it.\n\n1. **It is experimental.** This is an early release. It has been tested only in a limited way, on a GL.iNet GL-MT6000 (firmware 4.11.0) and in a virtual OpenWrt, never on a wide range of devices, firmware versions or networks. It is not production software and must not be treated as such.\n2. **It can interrupt your internet.** Switching a VPN route can drop calls, downloads and sessions for seconds or longer. A fault, a bug or an unexpected router state can leave devices on your network without internet until you repair the router by hand. Keep another way to reach the internet and the router, and make a private backup first (see the Help page and `router-test-kit/`).\n3. **It changes router settings.** The program reorders your existing VPN rules and can add a temporary firewall rule. It does not edit your VPN keys. You can remove it at any time (`opkg remove homensai-auto-vpn`; see the Help page).\n4. **No warranty.** The software is provided \"AS IS\" under the MIT License, without warranty of any kind, express or implied. The author and contributors are not liable for any damage, loss of data, loss of service, cost or other consequence of installing or using it.\n5. **You are responsible.** You install and use it at your own risk. You are responsible for your router, your network, your VPN accounts, for following your VPN provider's terms and for the law that applies to you. Do not use it where an interruption could endanger people or property.\n6. **Optional reports.** If you configure Telegram reports, summaries are sent through Telegram's servers with a bot token stored on your router. Nothing is sent unless you configure it.\n7. **No promise of support.** Features, behaviour and these terms may change or be withdrawn in later versions; accepting them again may be required.\n\nThis text is not legal advice. If you need certainty about your obligations, ask a qualified lawyer.\n\n## How acceptance works\n\nWhen you open the program in LuCI for the first time, a full-page screen shows these terms. Two boxes must be ticked before the Continue button works. The acceptance (terms version and time) is stored on the router in the program's own configuration. Until it is stored, the controller refuses to switch anything (`TERMS-NOT-ACCEPTED`) and the Start button for Auto is refused. If the terms change, their version number changes and you accept again.\n\nIf you do not accept, remove the package and leave your router as it was. Your VPN rules are not changed by the monitor itself.\n\nTerms version: 1.\n";
var TERMS_FULL_RU="# Экспериментальное ПО: условия использования\n\n[English](DISCLAIMER.md)\n\n**HomenS.AI Auto VPN — экспериментальное программное обеспечение (alpha).** Прочитайте это до установки и использования. Тот же текст показывается в программе при первом открытии, и Auto нельзя запустить, пока вы его не примете.\n\n1. **Это экспериментальная версия.** Ранний выпуск. Он проверялся лишь ограниченно, на GL.iNet GL-MT6000 (прошивка 4.11.0) и в виртуальном OpenWrt, но не на широком круге устройств, версий прошивок и сетей. Это не промышленное ПО, и относиться к нему как к такому нельзя.\n2. **Оно может прервать ваш интернет.** Переключение маршрута VPN может на секунды и дольше оборвать звонки, загрузки и сессии. Сбой, ошибка или неожиданное состояние роутера могут оставить устройства в вашей сети без интернета, пока вы не исправите роутер вручную. Держите другой способ выхода в интернет и доступа к роутеру и заранее сделайте приватную резервную копию (см. страницу «Помощь» и `router-test-kit/`).\n3. **Оно меняет настройки роутера.** Программа переставляет существующие правила VPN и может добавить временное правило firewall. Ключи VPN она не редактирует. Удалить её можно в любой момент (`opkg remove homensai-auto-vpn`; см. «Помощь»).\n4. **Гарантий нет.** ПО предоставляется «КАК ЕСТЬ» (AS IS) по лицензии MIT, без каких-либо гарантий, явных или подразумеваемых. Автор и участники не отвечают за ущерб, потерю данных, потерю связи, расходы и иные последствия установки или использования.\n5. **Ответственность на вас.** Вы устанавливаете и используете его на свой риск. Вы отвечаете за свой роутер, сеть, аккаунты VPN, за соблюдение условий вашего провайдера VPN и применимого к вам законодательства. Не используйте его там, где перерыв связи может угрожать людям или имуществу.\n6. **Необязательные отчёты.** Если вы настроите отчёты в Telegram, сводки отправляются через серверы Telegram с токеном бота, хранящимся на вашем роутере. Без вашей настройки ничего не отправляется.\n7. **Поддержка не обещана.** Возможности, поведение и эти условия могут измениться или быть отозваны в следующих версиях; может потребоваться принять их снова.\n\nЭтот текст не является юридической консультацией. Если вам нужна определённость в своих обязанностях, обратитесь к квалифицированному юристу.\n\n## Как работает принятие условий\n\nПри первом открытии программы в LuCI на весь экран показываются эти условия. Чтобы кнопка «Продолжить» заработала, нужно отметить два флажка. Принятие (версия условий и время) сохраняется на роутере в собственной конфигурации программы. Пока оно не сохранено, контроллер отказывается что-либо переключать (`TERMS-NOT-ACCEPTED`), а кнопка запуска Auto отклоняется. Если условия изменятся, изменится и номер версии, и их нужно будет принять снова.\n\nЕсли вы не принимаете условия, удалите пакет, и роутер останется как был. Сам монитор правила VPN не меняет.\n\nВерсия условий: 1.\n";
// END GENERATED LEGAL REFERENCE
var TERMS_POINTS=[
  {h:["It is experimental","Это экспериментальная версия"],t:["This is an early alpha release. It has been tested only in a limited way, on a GL.iNet GL-MT6000 (firmware 4.11.0) and in a virtual OpenWrt. It is not production software.","Это ранняя версия alpha. Она проверялась лишь ограниченно, на GL.iNet GL-MT6000 (прошивка 4.11.0) и в виртуальном OpenWrt. Это не промышленное ПО."]},
  {h:["It can interrupt your internet","Оно может прервать ваш интернет"],t:["Switching a VPN route can drop calls, downloads and sessions. A fault or bug can leave devices on your network without internet until you repair the router by hand. Keep another way to reach the internet and the router, and make a backup first.","Переключение маршрута VPN может оборвать звонки, загрузки и сессии. Сбой или ошибка могут оставить устройства без интернета, пока вы не исправите роутер вручную. Держите другой способ выхода в интернет и доступа к роутеру и сначала сделайте резервную копию."]},
  {h:["It changes router settings","Оно меняет настройки роутера"],t:["It reorders your existing VPN rules and can add a temporary firewall rule. It does not edit your VPN keys. You can remove it at any time (see Help).","Оно переставляет ваши существующие правила VPN и может добавить временное правило firewall. Ключи VPN оно не редактирует. Удалить его можно в любой момент (см. «Помощь»)."]},
  {h:["No warranty","Гарантий нет"],t:["Provided “AS IS” under the MIT License, without warranty of any kind. The author and contributors are not liable for any damage, loss of data, loss of service, cost or other consequence of installing or using it.","Предоставляется «КАК ЕСТЬ» (AS IS) по лицензии MIT, без каких-либо гарантий. Автор и участники не отвечают за ущерб, потерю данных, потерю связи, расходы и иные последствия установки или использования."]},
  {h:["You are responsible","Ответственность на вас"],t:["You use it at your own risk. You are responsible for your router, your network, your VPN accounts, your VPN provider’s terms and the law that applies to you. Do not use it where an interruption could endanger people or property.","Вы используете его на свой риск. Вы отвечаете за свой роутер, сеть, аккаунты VPN, условия провайдера VPN и применимое к вам законодательство. Не используйте его там, где перерыв связи может угрожать людям или имуществу."]},
  {h:["Optional reports","Необязательные отчёты"],t:["If you set up Telegram reports, summaries are sent through Telegram’s servers with a bot token stored on your router. Nothing is sent unless you set it up.","Если вы настроите отчёты в Telegram, сводки отправляются через серверы Telegram с токеном бота, хранящимся на вашем роутере. Без вашей настройки ничего не отправляется."]},
  {h:["No promise of support","Поддержка не обещана"],t:["Features, behaviour and these terms may change in later versions; you may be asked to accept them again.","Возможности, поведение и эти условия могут измениться в следующих версиях; вас могут попросить принять их снова."]}
];
if(typeof HELP_TOPICS!=='undefined'){HELP_TOPICS.push({id:'terms',title:["Terms of use (experimental software)","Условия использования (экспериментальное ПО)"],when:["What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.","Что вы приняли на первом экране. Полный текст — DISCLAIMER.ru.md в репозитории проекта."],steps:[],custom:renderTermsReference});}
var TERMS_CHECKS=[
  ["I understand that this software is experimental and may interrupt my internet connection.","Я понимаю, что это ПО экспериментальное и может прервать моё подключение к интернету."],
  ["I have read the terms above and accept full responsibility for installing and using it.","Я прочитал условия выше и принимаю полную ответственность за установку и использование."]
];
function renderTermsReference(){
  return E('section',{'class':'hv-terms-reference'},[
    E('p',{'class':'hv-terms-note'},bi('The unchanged versioned terms are reproduced below. Their early test description is historical; current hardware/mode qualification is determined by System readiness and the current guide. Removing the package still requires normal lifecycle/recovery checks.','Ниже приведены неизменённые условия своей версии. Описание первоначальных испытаний в них — исторический контекст; текущий допуск модели/режима определяют «Готовность системы» и актуальное руководство. Удаление пакета по-прежнему требует штатных проверок восстановления.')),
    E('div',{'class':'hv-terms-fulltext','style':'white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6'},locale==='ru'?TERMS_FULL_RU:TERMS_FULL_EN)
  ]);
}
function termsAccepted(inventory){
  return !!inventory&&!inventory.error&&!!inventory.settings&&inventory.settings.terms_version===TERMS_VERSION;
}
function renderTermsGate(inventory,status){
  var boxes=TERMS_CHECKS.map(function(){return E('input',{'type':'checkbox'});});
  var busy=false,button=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-terms-accept','click':function(){
    if(busy||!boxes.every(function(box){return box.checked===true;}))return;
    busy=true;button.disabled=true;
    return rpc.declare({object:'homensai-vpn',method:'terms_accept',params:['version'],expect:{}})(TERMS_VERSION).then(function(result){
      if(result&&result.saved===true){window.location.reload();return;}
      busy=false;sync();ui.addNotification(null,E('p',{},(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(result.code))?result.code:'TERMS-SAVE-FAILED'));
    }).catch(function(){busy=false;sync();ui.addNotification(null,E('p',{},'TERMS-SAVE-UNCONFIRMED'));});
  }},bi('Accept and continue','Принять и продолжить'));
  function sync(){button.disabled=busy||!boxes.every(function(box){return box.checked===true;});}
  boxes.forEach(function(box){box.addEventListener('change',sync);});
  button.disabled=true;
  var other=locale==='ru'?'en':'ru';
  var language=E('a',{'href':'#','click':function(ev){ev.preventDefault();var next=new URL(window.location.href);next.searchParams.set('lang',other);window.location.assign(next.toString());}},other==='ru'?'Русский':'English');
  var model=identityModel(status||{});
  var versionBadge=E('span',{'class':'hv-version','aria-label':bi('Program version','Версия программы')},'v'+(model.agent||model.uiAgent));
  var attribution=E('div',{'class':'hv-terms-attribution'},[renderAttribution(status||{})]);
  var footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');
  applyTheme(storedTheme());
  var gate=E('div',{'class':'hv-app hv-terms','data-terms-gate':TERMS_VERSION,'data-hv-design':currentDesign(),'style':'width:100%;box-sizing:border-box;overflow-wrap:anywhere'},[
    E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui94.css')}),
    E('section',{'class':'hv-chart-card hv-terms-card'},[
      E('header',{'class':'hv-page-header','style':'flex-wrap:wrap;gap:12px'},[E('p',{'class':'hv-eyebrow'},bi('HomenS.AI Auto VPN · first start','HomenS.AI Auto VPN · первый запуск')),versionBadge]),
      E('h1',{},bi('Experimental software: please read','Экспериментальное ПО: прочитайте, пожалуйста')),
      E('p',{'class':'hv-terms-license'},bi('MIT License · experimental alpha software · use at your own risk','Лицензия MIT · экспериментальная alpha-версия · использование на свой риск')),
      E('p',{},bi('Read the agreement, tick both confirmations and press Accept and continue. Next comes a short illustrated explanation, then the eight-step setup.','Прочитайте соглашение, отметьте оба подтверждения и нажмите «Принять и продолжить». Затем откроется краткое объяснение со схемами, а после него — настройка из восьми шагов.')),
      E('p',{},[bi('Language: ','Язык: '),language]),
      E('p',{'class':'hv-terms-note'},bi('The accepted terms are retained. Their test-device description is historical; use current System readiness for supported mode/hardware, and normal lifecycle checks before removal.','Принятые условия сохраняются. Описание первоначальных испытаний историческое; допуск модели/режима проверяйте по актуальной готовности, а удаление — по штатным условиям восстановления.')),
      E('ol',{'class':'hv-terms-list'},TERMS_POINTS.map(function(point){return E('li',{},[E('strong',{},bi(point.h[0],point.h[1])),E('p',{},bi(point.t[0],point.t[1]))]);})),
      E('p',{'class':'hv-terms-note'},bi('This is not legal advice. The full text is in DISCLAIMER.md in the project repository and on the Help page.','Это не юридическая консультация. Полный текст — в DISCLAIMER.ru.md в репозитории проекта и на странице «Помощь».')),
      E('div',{'class':'hv-terms-checks'},TERMS_CHECKS.map(function(text,index){return E('label',{'class':'hv-terms-check'},[boxes[index],' ',bi(text[0],text[1])]);})),
      E('p',{},button),
      E('div',{'class':'hv-terms-note'},[E('p',{},bi('If you do not accept, remove the package and your router stays as it was:','Если вы не принимаете условия, удалите пакет, и роутер останется как был:')),helpCommand('opkg remove homensai-auto-vpn')])
    ]),attribution,footer
  ]);
  return gate;
}

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
  return rows.filter(function(p){return ids[p.id]===1&&logicals[p.interface]===1&&(!mt3000||(p.protocol==='wireguard'&&/^wgclient[1-9][0-9]{0,3}$/.test(p.interface)||p.protocol==='openvpn'&&/^ovpnclient[1-9][0-9]{0,3}$/.test(p.interface)));});
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
  var recoveryDefaults={failures:3,successes:2,cooldown:60,min_dwell:60,return_policy:'healthy_primary',primary_successes:2,primary_stable:30,attempt_limit:3,attempt_window:15};
  Object.keys(recoveryDefaults).forEach(function(k){recovery[k]=value('recovery_'+k,recoveryDefaults[k]);});
  var speedDefaults={budget_mib:8,duration:5,streams:2,daily_mib:128,busy_mbps:2};
  Object.keys(speedDefaults).forEach(function(k){speed[k]=value('speed_'+k,speedDefaults[k]);});
  return {
    appearance:{language:s.appearance_language||locale,theme:s.appearance_theme||storedTheme(),design:'b',router_model:s.router_model||'auto'},
    monitor:{interval:value('interval',10),checkpoint:value('checkpoint',900),probe_limit:value('probe_limit',16),planning_enabled:!!s.plan_enabled,live_log_limit:value('live_log_limit',2000),history_days:value('history_days',7)},
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
  ['failures','successes','cooldown','min_dwell','primary_successes','primary_stable','attempt_limit','attempt_window'].forEach(function(k){recovery[k]=Number(draft.recovery[k]);});recovery.return_policy=draft.recovery.return_policy;
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
    var recoveryLabels={attempt_limit:bi('Maximum attempts','Максимум попыток'),attempt_window:bi('Attempt window, minutes','Период попыток, минут'),failures:bi('Failures before switching','Сбоев до переключения'),successes:bi('Reserve successes required','Успешных проверок резерва'),cooldown:bi('Cooldown, seconds','Пауза, секунд'),min_dwell:bi('Minimum dwell, seconds','Минимальное время работы, секунд'),primary_successes:bi('Primary successes before return','Успешных проверок основного перед возвратом'),primary_stable:bi('Primary stable interval, seconds','Период стабильности основного, секунд')};
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
        number(bi('How often to check each VPN, seconds','Как часто проверять каждый VPN, секунд'),draft.monitor,'interval','monitor.interval','monitor.interval');
        number(bi('Save statistics every, seconds','Сохранять статистику каждые, секунд'),draft.monitor,'checkpoint','monitor.checkpoint','monitor.checkpoint');
        number(bi('Most VPNs checked per round','Максимум VPN за один раунд проверки'),draft.monitor,'probe_limit','monitor.probe_limit','onboarding.probe_limit');
        number(bi('Live journal observations (1–2000)','Наблюдений в живом журнале (1–2000)'),draft.monitor,'live_log_limit','monitor.live_log_limit','monitor.live_log_limit');
        number(bi('Detailed history, days (1–7)','Подробная история, дней (1–7)'),draft.monitor,'history_days','monitor.history_days','monitor.history_days');
        note('Reducing retention removes old detail during normal cleanup. Increasing it cannot restore deleted observations; monthly and lifetime counters remain separate.','Уменьшение срока удаляет старые подробности при штатной очистке. Увеличение не возвращает удалённые наблюдения; месячные и общие счётчики хранятся отдельно.');
        toggle(bi('Show what Auto would do (no switching)','Показывать, что сделал бы Auto (без переключения)'),draft.monitor,'planning_enabled','monitor.planning_enabled');
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
        review(headings[1],[[bi('Probe / checkpoint (seconds) / profiles per round','Проверка / checkpoint (секунд) / профилей за раунд'),draft.monitor.interval+' / '+draft.monitor.checkpoint+' / '+draft.monitor.probe_limit],[bi('Live observations / detail days','Наблюдений в журнале / дней истории'),draft.monitor.live_log_limit+' / '+draft.monitor.history_days],[bi('Show what Auto would do','Показывать, что сделал бы Auto'),yes(draft.monitor.planning_enabled)]]);
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
  if(firstRun){['style/css/tokens.css','style/css/fonts.css','style/css/author.css','ui94.css'].forEach(function(path){host.appendChild(E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/'+path)}));});}
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

/* Installed identity and part-mismatch diagnosis. The router program and this page are shipped together; they can differ after
   an interrupted upgrade or a cached page. Build values are written by the page generator. */
var UI_BUILD='dashboard128',UI_AGENT='0.9.1-alpha53';
var HV_DETECTED_ROUTER_MODEL='unknown';
function routerModelLabel(){
  return {mt6000:'GL.iNet GL-MT6000 · Flint 2',mt3000:'GL.iNet GL-MT3000 · Beryl AX'}[HV_DETECTED_ROUTER_MODEL]||'GL.iNet GL-MT6000 · Flint 2 / GL-MT3000 · Beryl AX';
}
function identityModel(status){
  var agent=typeof status.version==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(status.version)?status.version:null;
  var pkg=typeof status.package==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(status.package)?status.package:null;
  var known=!status.rpc_error&&!!agent;
  return {agent:agent,pkg:pkg,ui:UI_BUILD,uiAgent:UI_AGENT,
    pageOld:known&&agent!==UI_AGENT,
    // The package version starts with the agent version; anything else means a mixed or partial upgrade.
    packageMismatch:known&&!!pkg&&pkg.indexOf(agent)!==0};
}
function renderIdentityNotice(status){
  var model=identityModel(status);
  if(!model.pageOld&&!model.packageMismatch)return null;
  var text=model.packageMismatch
    ?bi('The installed package ('+model.pkg+') and the running program ('+model.agent+') differ. The upgrade may be unfinished: reload the page and wait a minute, or see Help → “The page is old, empty or says the monitor is not running”.','Установленный пакет ('+model.pkg+') и работающая программа ('+model.agent+') различаются. Возможно, обновление не завершено: обновите страницу и подождите минуту или откройте «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».')
    :bi('This page belongs to version '+model.uiAgent+' but the router runs '+model.agent+'. Press Ctrl+F5 to reload the page. If it stays, sign out of LuCI and in again; then see Help.','Эта страница относится к версии '+model.uiAgent+', а на роутере работает '+model.agent+'. Нажмите Ctrl+F5, чтобы обновить страницу. Если не помогло, выйдите из LuCI и войдите снова; затем см. «Помощь».');
  return E('p',{'class':'alert-message warning','role':'status'},text);
}
function identityLine(status){
  var model=identityModel(status);
  return bi('Version ','Версия ')+(model.agent||model.uiAgent);
}



/* Overview summary: one sentence and one colour for the whole system, plus a short "getting started" checklist. */
function learnDone(){try{return window.localStorage.getItem('homensai-vpn-learn-done')==='1';}catch(e){return false;}}
function summaryTone(light){return light.lamp==='green'?'ok':(light.lamp==='yellow'||light.lamp==='orange')?'warn':light.lamp==='red'?'bad':'off';}
function startSteps(status,inventory,now){
  var settings=(inventory||{}).settings||{},monitor=monitorLightModel(status,inventory,now,false),ready=autoReadiness(status,inventory,now),model=autoControlModel(status,now);
  return [
    {key:'terms',done:true,title:bi('Accept the terms','Принять условия'),hint:bi('Done on the first screen.','Сделано на первом экране.')},
    {key:'learn',done:learnDone(),title:bi('Take the 5-minute training','Пройти обучение на 5 минут'),hint:bi('What the system is, how to use it and what to do if the internet is gone.','Что это за система, как ею пользоваться и что делать, если пропал интернет.'),href:'#learn',action:bi('Open training','Открыть обучение')},
    {key:'monitor',done:monitor.key==='ok',title:bi('Monitoring is on','Мониторинг включён'),hint:bi('It starts by itself. Look at the Monitoring block at the top of this page: the lamp must be green. If it is not, press “Start monitoring” there.','Он запускается сам. Посмотрите на блок «Мониторинг» вверху этой страницы: лампа должна быть зелёной. Если нет, нажмите там «Запустить мониторинг».')},
    {key:'profiles',done:!!(settings.setup_complete&&settings.plan_source&&settings.plan_target),title:bi('Choose the primary and the reserve VPN','Выбрать основной и резервный VPN'),hint:bi('Primary is your preferred everyday VPN. Reserve is a different saved VPN used when the primary fails. Open the pair fields directly, or Settings → All application settings → 3 · Existing VPNs.','Основной — предпочитаемый VPN для обычной работы. Резервный — другой сохранённый VPN на случай отказа основного. Кнопка откроет нужные поля; они также доступны: «Настройки → Все настройки приложения → 3 · Существующие VPN».'),href:'#settings',action:bi('Choose the VPN pair','Выбрать пару VPN')},
    {key:'auto',done:!!model.on,title:bi('Check the VPNs and start Auto','Проверить VPN и включить Auto'),hint:ready.ready?bi('Everything is ready: press the Auto button below.','Всё готово: нажмите кнопку Auto ниже.'):bi('The list under the Auto button shows what is still missing. A separate LAN test checks a real client; it is not required for prepared-MT3000 router-probed IPv4 mode.','Список под кнопкой Auto показывает, чего ещё не хватает. Отдельный LAN-тест проверяет реального клиента; для проверки самого роутера на подготовленном MT3000 он не обязателен.')}
  ];
}
function renderSummary(status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),rows=status.profiles||[],light=autoLightModel(status,inventory,now),tone=summaryTone(light),c=serverCounts(status,inventory,rows,now);
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
/* A drawing error is shown as its own catalogued code, at most once a minute; the rest of the page keeps working. */
var UI_RENDER_FAILED_AT=0;
function uiRenderFailed(error){
  if(typeof console!=='undefined'&&console.error)console.error('UI-RENDER-FAILED',error);
  if(Date.now()-UI_RENDER_FAILED_AT<60000)return;UI_RENDER_FAILED_AT=Date.now();
  if(typeof ui!=='undefined'&&ui&&typeof ui.addNotification==='function')ui.addNotification(null,typeof autoCodeNotice==='function'?autoCodeNotice('UI-RENDER-FAILED'):E('p',{},'UI-RENDER-FAILED'));
}
/* "Reset chart" on every chart and statistics card. The router archives the old data first, then measures from zero. */
var STATS_RESET_NAMES={latency:['latency chart and table','график и таблицу задержки'],auto:['switching charts and outage statistics','графики переключений и статистику сбоев'],traffic:['traffic chart and counters','график и счётчики трафика'],ranking:['speed tests and server ranking','тесты скорости и рейтинг серверов'],quality:['server quality statistics','статистику качества серверов'],speed:['speed test history','историю тестов скорости'],all:['all charts and statistics','все графики и статистику']};
function statsResetError(code){
  var node=typeof autoCodeNotice==='function'?autoCodeNotice(code):E('p',{},code);
  if(typeof ui!=='undefined'&&ui&&typeof ui.showModal==='function')ui.showModal(bi('Reset did not complete','Сброс не выполнен'),[node,E('div',{'class':'right'},E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть')))]);
}
function statsResetRun(scope,button){
  var call=rpc.declare({object:'homensai-vpn',method:'stats_reset',params:['scope'],expect:{}}),status=rpc.declare({object:'homensai-vpn',method:'status',expect:{}});
  button.disabled=true;var label=button.textContent;button.textContent=bi('Resetting…','Сбрасываю…');
  function done(){button.disabled=false;button.textContent=label;}
  return Promise.resolve(call(scope)).then(function(result){
    if(!result||result.queued!==true){done();statsResetError(result&&result.code||'STATS-RESET-FAILED');return;}
    var deadline=Date.now()+45000;
    function wait(){
      return Promise.resolve(status()).then(function(s){
        var r=s&&s.stats_reset;
        if(r&&r.nonce===result.nonce){
          done();
          if(r.done!==true){statsResetError(r.code||'STATS-RESET-FAILED');return;}
          if((scope==='auto'||scope==='all')&&typeof autoLivePoints!=='undefined')autoLivePoints=[];
          if(typeof ui!=='undefined'&&ui&&typeof ui.addNotification==='function')ui.addNotification(null,E('p',{},bi('Reset done: the old data is archived on the router, measurements start again from zero.','Сброс выполнен: старые данные сохранены в архив на роутере, измерения начались заново.')),'info');
          return;
        }
        if(Date.now()>deadline){done();statsResetError('STATS-RESET-UNCONFIRMED');return;}
        return new Promise(function(resolve){setTimeout(resolve,3000);}).then(wait);
      },function(){if(Date.now()>deadline){done();statsResetError('STATS-RESET-UNCONFIRMED');return;}return new Promise(function(resolve){setTimeout(resolve,3000);}).then(wait);});
    }
    return wait();
  },function(){done();statsResetError('STATUS-REQUEST-FAILED');});
}
function statsResetButton(scope){
  var name=STATS_RESET_NAMES[scope]||STATS_RESET_NAMES.all;
  var button=E('button',{'type':'button','class':'cbi-button hv-stats-reset','data-stats-reset-button':scope,'click':function(event){
    if(event&&event.preventDefault)event.preventDefault();
    var self=event&&event.currentTarget||button;
    if(typeof ui==='undefined'||!ui||typeof ui.showModal!=='function')return statsResetRun(scope,self);
    ui.showModal(bi('Reset the chart?','Сбросить график?'),[
      E('p',{},bi('This resets the ','Будет сброшено: ')+bi(name[0],name[1])+'. '+bi('The current data is first saved to an archive on the router (the last 10 resets are kept), then measurements start again from zero.','Текущие данные сначала сохраняются в архив на роутере (хранятся 10 последних сбросов), затем измерения начинаются заново с нуля.')),
      E('div',{'class':'right'},[E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),' ',
        E('button',{'type':'button','class':'cbi-button cbi-button-negative','click':function(){ui.hideModal();statsResetRun(scope,self);}},bi('Reset','Сбросить'))])]);
  }},bi('Reset chart','Сброс графика'));
  return button;
}
function attachStatsResets(root){
  if(!root||typeof root.querySelectorAll!=='function')return 0;var added=0;
  root.querySelectorAll('[data-stats-reset]').forEach(function(card){
    if(card.querySelector('[data-stats-reset-button]'))return;
    card.appendChild(E('div',{'class':'hv-stats-reset-row'},statsResetButton(card.getAttribute('data-stats-reset'))));added++;
  });
  return added;
}
/* The Overview menu opens at the top of the Automatic VPN failover card, below the router's own header bar. */
function overviewToAuto(){
  var anchor=document.getElementById('hv-auto-vpn');if(!anchor)return false;
  var card=anchor.closest?anchor.closest('.hv-auto-control')||anchor:anchor,bar=document.querySelector('header');
  var offset=bar&&bar.getBoundingClientRect?Math.max(0,bar.getBoundingClientRect().bottom):0;
  window.scrollTo(0,Math.max(0,card.getBoundingClientRect().top+(window.pageYOffset||0)-offset-12));return true;
}
/* "Go back" at the bottom of every page: the previous page and the scroll position where the owner was. */
var PAGE_BACK_STACK=[],PAGE_BACK_GOING=false,pageBackButton=null;
function pageBackRemember(page,y){
  if(PAGE_BACK_GOING||typeof page!=='string'||!page)return;
  var last=PAGE_BACK_STACK[PAGE_BACK_STACK.length-1];
  if(last&&last.page===page)last.y=y;else PAGE_BACK_STACK.push({page:page,y:y});
  if(PAGE_BACK_STACK.length>30)PAGE_BACK_STACK.shift();
}
function pageBackGo(){
  var previous=PAGE_BACK_STACK.pop();
  if(!previous){var home=document.querySelector('[data-hv-tab="overview"]');if(home&&typeof pageKeyNow==='function'&&pageKeyNow()!=='overview'){home.click();return true;}if(typeof overviewToAuto==='function')overviewToAuto();return false;}
  var link=document.querySelector('[data-hv-tab="'+previous.page+'"]');if(!link){PAGE_BACK_STACK.push(previous);return false;}
  PAGE_BACK_GOING=true;try{link.click();}finally{PAGE_BACK_GOING=false;}
  setTimeout(function(){window.scrollTo(0,previous.y||0);},60);return true;
}
function pageBackPlace(root,page){
  var host=typeof document!=='undefined'&&document.body?document.body:root&&root.querySelector('[data-hv-page="'+page+'"]');if(!host)return null;
  if(!pageBackButton)pageBackButton=E('button',{'type':'button','class':'hv-back-float','click':function(){pageBackGo();}},bi('← Go back','← Вернуться назад'));
  if(pageBackButton.parentNode!==host)host.appendChild(pageBackButton);
  return pageBackButton;
}
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
  if(pageKeyNow()&&pageKeyNow()!=='events')errorReturn={tab:pageKeyNow(),y:window.pageYOffset||0};
  if(typeof ensureLazyPage==='function'&&!LAZY_HELP.api){LAZY_HELP.pendingCode=code;var lazyLink=document.querySelector('[data-hv-tab="events"]');if(lazyLink)lazyLink.click();return ensureLazyPage('events').then(function(){lazyHelpDeepLink('events');});}
  if(!errorReturn&&pageKeyNow())errorReturn={tab:pageKeyNow(),y:window.pageYOffset||0};
  var link=document.querySelector('[data-hv-tab="events"]');if(link&&pageKeyNow()!=='events')link.click();
  setTimeout(showErrorBack,300);
  setTimeout(function(){
    var key=Object.prototype.hasOwnProperty.call(ERROR_GROUP_OF,code)?code:((typeof errorFamilyOf==='function'&&errorFamilyOf(code))?errorFamilyOf(code)[0]+'*':code);
    if(!/^[A-Z][A-Z0-9*-]{1,95}$/.test(key))return;
    if(typeof ERROR_TABLE_STATE!=='undefined'){ERROR_TABLE_STATE.selected=key;persistErrorTableState();}
    var search=errorTable&&errorTable.querySelector('input[type="search"]');
    if(search){search.value=key;search.dispatchEvent(new Event('input',{bubbles:true}));}
    var row=document.querySelector('[data-error-code="'+key+'"]');if(!row)return;
    var fix=row.nextElementSibling;if(fix&&fix.classList&&fix.classList.contains('hv-errfix')&&fix.hidden){var b=row.querySelector('button');if(b)b.click();}
    document.querySelectorAll('.hv-err-selected').forEach(function(old){old.classList.remove('hv-err-selected');});row.classList.add('hv-err-selected');row.scrollIntoView({block:'center'});
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
  var steps=startSteps(status||{},inventory||{},(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  if(startAllDone(steps)){try{window.localStorage.setItem(START_DONE_KEY,'1');}catch(e){}return 'overview';}
  return 'start';
}
function renderStartPage(status,inventory){
  var steps=startSteps(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),open=steps.filter(function(s){return !s.done;}),next=open[0];
  if(!open.length){try{window.localStorage.setItem(START_DONE_KEY,'1');}catch(e){}}
  var targets={learn:['#learn',bi('Open training','Открыть обучение')],monitor:['#overview',bi('Open the Overview','Открыть «Обзор»')],profiles:['#settings',bi('Choose the VPN pair','Выбрать пару VPN')],auto:['#overview',bi('Open the Overview','Открыть «Обзор»')]};
  var list=E('ol',{'class':'hv-start-list hv-start-page-list'},steps.map(function(s,i){
    var current=next&&next.key===s.key,target=targets[s.key];
    return E('li',{'class':'hv-start-step hv-start-'+(s.done?'done':current?'next':'todo')},[
      E('span',{'class':'hv-start-mark','aria-hidden':'true'},s.done?'✓':String(i+1)),
      E('div',{},[E('strong',{},s.title),E('p',{},s.done?bi('Done.','Готово.'):s.hint)]),
      (!s.done&&target)?E('a',{'class':'cbi-button'+(current?' cbi-button-action':''),'href':target[0],'click':s.key==='profiles'?function(ev){ev.preventDefault();openOnboardingSettings(inventory,status,'system');}:null},target[1]):E('span',{'class':'hv-visually-hidden'},s.done?bi('done','выполнено'):bi('not done','не выполнено'))]);
  }));
  return E('section',{'class':'hv-chart-card hv-start-page'},[
    E('h3',{},open.length?bi('Step ','Шаг ')+(steps.indexOf(next)+1)+bi(' of ',' из ')+steps.length:bi('All steps are done','Все шаги выполнены')),
    E('p',{},open.length?bi('The simplified interface is available whenever Auto is on, even if steps remain here. If Auto cannot start, complete system setup.','Упрощённый интерфейс доступен всегда, когда включён Auto, даже если здесь остались незавершённые шаги. Если Auto не включается, завершите настройку системы.'):bi('Use the simplified interface whenever Auto is on, or continue in the full Overview.','При включённом Auto можно перейти в упрощённый интерфейс или продолжить работу в полном «Обзоре».')),
    list,
    E('p',{},E('a',{'class':'cbi-button'+(open.length?'':' cbi-button-action'),'href':'#overview'},bi('Go to the Overview','Перейти на «Обзор»')))]);
}

/* Colour theme: follow the system (default), light or dark. Stored only in this browser. */
function applyTheme(mode){
  var root=document.documentElement;
  if(mode==='light'||mode==='dark')root.setAttribute('data-theme',mode);else root.removeAttribute('data-theme');
}
function storedTheme(){var fallback=typeof HV_ROUTER_DISPLAY!=='undefined'&&HV_ROUTER_DISPLAY&&HV_ROUTER_DISPLAY.theme;fallback=fallback==='light'||fallback==='dark'?fallback:'system';try{var v=window.localStorage.getItem('homensai-vpn-theme');return v==='light'||v==='dark'||v==='system'?v:fallback;}catch(e){return fallback;}}
function renderThemeSelect(){
  var mode=storedTheme();applyTheme(mode);
  var select=E('select',{'aria-label':bi('Colour theme','Цветовая тема'),'change':function(){var v=select.value;try{window.localStorage.setItem('homensai-vpn-theme',v);}catch(e){}applyTheme(v);}},[
    E('option',{'value':'system'},bi('Theme: system','Тема: как в системе')),E('option',{'value':'light'},bi('Theme: light','Тема: светлая')),E('option',{'value':'dark'},bi('Theme: dark','Тема: тёмная'))]);
  select.value=mode;
  return select;
}



/* Page design: A Control room, B Calm (default), C Instrument panel. Router defaults come from setup;
   an explicit choice in Settings overrides them in this browser without changing other saved choices. */
var HV_DESIGNS=[
  {key:'a',name:['A · Control room','A · Пульт'],
   about:['Sections as tabs across the top, full width for the content. Status, failover path and servers stay where they are now.','Разделы вкладками сверху, вся ширина отдана содержимому. Статус, путь переключения и серверы на привычных местах.'],
   suits:['Everyone who prefers the full control-room layout.','Всем, кто предпочитает полный вид пульта.']},
  {key:'b',name:['B · Calm','B · Спокойный'],
   about:['Larger text and more space. Administrator sections are hidden behind “Advanced”; on a phone the sections sit at the bottom of the screen.','Крупнее текст и больше воздуха. Разделы для администратора спрятаны за «Расширенные настройки»; на телефоне разделы внизу экрана.'],
   suits:['The default. People who only want to know that the internet works, and phone users.','Вариант по умолчанию. Тем, кому важно только знать, что интернет работает, и для телефона.']},
  {key:'c',name:['C · Instrument panel','C · Приборная панель'],
   about:['A narrow icon column, compact cards, numbers and tables in a monospaced font. All sections, including administrator ones, are always visible.','Узкая колонка иконок, компактные карточки, цифры и таблицы моноширинным шрифтом. Все разделы, включая администраторские, видны всегда.'],
   suits:['The owner and testers: diagnostics, error codes, router tests.','Владельцу и тестировщикам: диагностика, коды ошибок, тесты на роутере.']}
];
var HV_DESIGN_KEY='homensai-vpn-design';
function validDesign(key){return HV_DESIGNS.some(function(d){return d.key===key;});}
function storedDesign(){var fallback=typeof HV_ROUTER_DISPLAY!=='undefined'&&HV_ROUTER_DISPLAY&&HV_ROUTER_DISPLAY.design;fallback=validDesign(fallback)?fallback:'b';try{var v=window.localStorage.getItem(HV_DESIGN_KEY);return validDesign(v)?v:fallback;}catch(e){return fallback;}}
/* The design chosen in this page session; it wins over storage, so a browser that refuses storage still keeps the choice until reload. */
var HV_DESIGN_NOW=null;
function currentDesign(){return validDesign(HV_DESIGN_NOW)?HV_DESIGN_NOW:storedDesign();}
function saveDesign(key){if(!validDesign(key))return false;HV_DESIGN_NOW=key;try{window.localStorage.setItem(HV_DESIGN_KEY,key);return true;}catch(e){return false;}}
function applyDesign(root,key){if(!root)return;root.setAttribute('data-hv-design',validDesign(key)?key:'b');}
function renderDesignPicker(getRoot,onApplied){
  var current=currentDesign(),note=E('p',{'class':'hv-design-note','role':'status','aria-live':'polite'},'');
  var options=HV_DESIGNS.map(function(d){
    var input=E('input',{'type':'radio','name':'hv-design','value':d.key,'id':'hv-design-'+d.key,'checked':d.key===current?'':null,'change':function(){
      var stored=saveDesign(d.key);applyDesign(getRoot(),d.key);if(onApplied)onApplied(d.key);
      note.textContent=stored?bi(d.name[0]+' is on. It opens again next time in this browser.',d.name[1]+' включён. Он откроется и в следующий раз в этом браузере.'):bi(d.name[0]+' is on for now. This browser does not allow saving it, so it resets after a reload.',d.name[1]+' включён сейчас. Этот браузер не разрешает его сохранить, после перезагрузки он сбросится.');
    }});
    input.checked=d.key===current;
    return E('label',{'class':'hv-design-option','for':'hv-design-'+d.key},[
      input,
      E('span',{'class':'hv-design-preview hv-design-preview-'+d.key,'aria-hidden':'true'},[E('i'),E('i'),E('i'),E('i')]),
      E('strong',{},bi(d.name[0],d.name[1])),
      E('span',{'class':'hv-design-about'},bi(d.about[0],d.about[1])),
      E('span',{'class':'hv-design-suits'},[E('b',{},bi('Suits: ','Подходит: ')),bi(d.suits[0],d.suits[1])])
    ]);
  });
  return E('section',{'class':'hv-chart-card hv-design-card'},[
    E('h3',{},bi('Page design','Оформление страницы')),
    E('p',{},bi('Choose how this page looks. The data and the buttons are the same in every design. The choice is kept in this browser and opens every time you come back.','Выберите, как выглядит эта страница. Данные и кнопки одинаковые во всех вариантах. Выбор хранится в этом браузере и открывается при каждом входе.')),
    E('div',{'class':'hv-design-options','role':'radiogroup','aria-label':bi('Page design','Оформление страницы')},options),
    note
  ]);
}

/* Wizards open in LuCI's modal outside the page root; give the modal the page's design, palette and fonts. */
function installModalStyle(){
  if(typeof ui==='undefined'||!ui||ui.__hvModalStyle||typeof ui.showModal!=='function')return;
  var original=ui.showModal;ui.__hvModalStyle=true;
  ui.showModal=function(){
    var node=original.apply(ui,arguments);
    try{var dialog=node&&node.classList?node:document.querySelector('#modal_overlay .modal')||document.getElementById('qa-modal');if(dialog){dialog.classList.add('hv-app','hv-modal');dialog.setAttribute('data-hv-design',currentDesign());}}catch(e){}
    return node;
  };
}

/* "Top" button in the bottom-right corner of every page and design: appears after the page is scrolled, jumps back up. */
function installTopButton(root){
  var button=E('button',{'type':'button','class':'hv-top-button','hidden':'','aria-label':bi('Back to top','Наверх'),'click':function(){
    try{window.scrollTo({top:0,behavior:window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}catch(e){window.scrollTo(0,0);}
    try{if(document.scrollingElement)document.scrollingElement.scrollTop=0;}catch(e){}
  }},[E('span',{'aria-hidden':'true'},'↑'),E('span',{'class':'hv-top-label'},bi('Top','Вверх'))]);
  Array.prototype.slice.call(document.querySelectorAll('.hv-top-button')).forEach(function(old){if(old.parentNode)old.parentNode.removeChild(old);});
  document.body.appendChild(button);  /* on the body: an ancestor with a transform would otherwise become the containing block of a fixed button */
  function update(){
    if(!root.isConnected){button.setAttribute('hidden','');return;}  /* not attached yet (or gone): stay hidden, keep listening */
    var y=window.pageYOffset||(document.scrollingElement&&document.scrollingElement.scrollTop)||0;
    if(y>240)button.removeAttribute('hidden');else button.setAttribute('hidden','');
  }
  window.addEventListener('scroll',update,{passive:true});update();
  return button;
}

/* Owner attributes: product name, device, developer and application version. Shown at the bottom of every page in every design; no design may hide it. */
var HV_STYLE_VERSION='HomenS.AI Style 1.14.3';
function renderAttribution(status){
  return E('div',{'class':'hv-attribution','data-hv-attribution':'1','aria-label':bi('About this program','О программе')},[
    E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI'),' Auto VPN']),
    E('span',{},routerModelLabel()),
    E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),
    E('span',{'class':'hv-attribution-version'},identityLine(status||{})),
    attributionVersionWarning(status)
  ].filter(Boolean));
}
// Page and router program differ (old cached page or unfinished upgrade): a quiet link to the Help topic that explains it.
function attributionVersionWarning(status){
  var model=identityModel(status||{});
  if(!model.pageOld&&!model.packageMismatch)return null;
  return E('span',{'class':'hv-attribution-warn'},[helpLink('stale',bi('Page and router versions differ: press Ctrl+F5 (details)','Версии страницы и роутера различаются: нажмите Ctrl+F5 (подробнее)'))]);
}

/* Overview layouts of the three page designs (A Control room, B Calm, C Instrument panel), built from the real status.
   Everything shown here is read from the router status; nothing is invented. The Auto control stays the real, working card. */
var DV_STATE_TEXT={
  'APPLYING':['Switching to the reserve','Переключение на резерв'],'WAIT-CLIENT':['Waiting for a LAN computer to confirm','Ожидание подтверждения с компьютера в сети'],
  'COMMITTED':['Reserve confirmed','Резерв подтверждён'],'ROLLED-BACK':['Rolled back to the previous route','Откат на прежний маршрут'],
  'ARMED':['Ready to switch','Готов к переключению'],'STOPPED':['Auto stopped','Auto остановлен'],'OBSERVING':['Watching the primary','Слежу за основным'],
  'BLOCKED':['Switch blocked','Переключение заблокировано'],'RESTORING':['Returning to the previous route','Возврат на прежний маршрут'],
  'DEGRADED-ON-RESERVE':['The reserve is failing too','Резерв тоже не работает'],'DISABLED':['Auto disabled','Auto выключен'],'EXPIRED':['Test window ended','Окно теста закончилось']
};
function dvStateText(state){var t=ownGet(DV_STATE_TEXT,state);return t?bi(t[0],t[1]):String(state==null?'—':state);}
function dvLocale(){return locale==='ru'?'ru-RU':'en-GB';}
function dvClock(time,seconds){return Number.isFinite(time)?new Date(time*1000).toLocaleTimeString(dvLocale(),seconds?{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',second:'2-digit'}:{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit'}):'—';}
function dvDay(time){if(!Number.isFinite(time))return '';var d=new Date(time*1000),n=new Date(),f=function(x){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin'}).format(x);};return f(d)===f(n)?bi('today','сегодня'):new Intl.DateTimeFormat(dvLocale(),{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit'}).format(d);}
function dvProfile(rows,id){return rows.filter(function(p){return p.id===id;})[0]||null;}
function dvName(rows,id){var p=dvProfile(rows,id);return p?serverTitle(p):'—';}
function dvShortName(rows,id){var p=dvProfile(rows,id);return p?(countryName(p)||customName(p)||protocolLabel(p)):'—';}
function dvSvg(name,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});return n;}
function dvSeries(status,id,count){
  return (status.samples||[]).filter(function(s){return s.id===id&&Number.isFinite(s.rtt_ms)&&!s.code&&Number.isFinite(s.time);}).sort(function(a,b){return a.time-b.time;}).slice(-count).map(function(s){return s.rtt_ms;});
}
function dvSpark(values){
  var svg=dvSvg('svg',{'class':'hv-dv-spark','viewBox':'0 0 110 28','role':'img','aria-label':bi('Recent response times','Последние времена ответа')});
  if(values.length<2){svg.appendChild(dvSvg('line',{x1:4,x2:106,y1:14,y2:14,stroke:'var(--dv-line)','stroke-dasharray':'3 4'}));return svg;}
  var lo=Math.min.apply(null,values),hi=Math.max.apply(null,values);if(hi-lo<10){var mid=(hi+lo)/2;lo=mid-5;hi=mid+5;}
  var pts=values.map(function(v,i){return [4+i*102/(values.length-1),25-(v-lo)/(hi-lo)*22];});
  var d=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1);}).join(' ');
  svg.appendChild(dvSvg('path',{d:d+' L'+pts[pts.length-1][0].toFixed(1)+' 28 L4 28 Z',fill:'var(--dv-accent)',opacity:'.12'}));
  svg.appendChild(dvSvg('path',{d:d,fill:'none',stroke:'var(--dv-accent)','stroke-width':'1.6','stroke-linejoin':'round'}));
  var e=pts[pts.length-1];svg.appendChild(dvSvg('circle',{cx:e[0].toFixed(1),cy:e[1].toFixed(1),r:'2.6',fill:'var(--dv-accent)'}));
  return svg;
}
// Checks per server: recent samples first, replaced by the hourly aggregates when the router kept them (same rule as the ranking table).
function dvRank(status){
  var rank={};
  (status.samples||[]).forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
  var quality=(status.accounting||{}).quality||{};
  Object.keys(quality).forEach(function(id){var q=quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
  return rank;
}
function dvConfidence(n){return n>=100?bi('good','высокая'):n>=20?bi('fair','средняя'):n>0?bi('low','низкая'):bi('none','нет');}
function dvPercent(r){return r&&r.n?(100*r.good/r.n):null;}
function dvPercentText(value){return value==null?'—':(value>=99.95?'100':value.toFixed(1))+'%';}
function dvEvents(status,rows,limit){
  return ((status.native_history||{}).events||[]).slice().sort(function(a,b){return b.time-a.time;}).slice(0,limit).map(function(e){
    var route=e.source&&e.target?': '+dvShortName(rows,e.source)+' → '+dvShortName(rows,e.target):'';
    return {time:e.time,text:dvStateText(e.state)+(e.trial?' ('+bi('trial','тест')+')':'')+route,codes:(e.codes||[]).slice(0,3)};
  });
}
function dvLamp(profile,now){var h=profileHealth(profile,now);return E('span',{'class':'hv-server-lamp hv-lamp-'+h.state,'role':'img','aria-label':h.label,'title':h.label});}
function dvChannelUse(profile,m,status){
  var h=profileHealth(profile,m.now),settings=m.settings||{},primary=m.primary&&m.primary.id===profile.id||settings.plan_source===profile.id||settings.plan_source_tunnel&&settings.plan_source_tunnel===profile.vendor_tunnel_id;
  var reserve=m.reserve&&m.reserve.id===profile.id||settings.plan_target===profile.id||settings.plan_target_tunnel&&settings.plan_target_tunnel===profile.vendor_tunnel_id;
  var role=primary?bi('Primary channel','Основной канал'):reserve?bi('Reserve channel','Резервный канал'):bi('Other VPN','Другой VPN');
  var result={role:role,label:h.label,kind:'grey',state:'unknown'};
  if(status.rpc_error||!Number.isFinite(status.time)||m.now-status.time< -5||m.now-status.time>90){result.kind='red';result.state='failed';result.kind='grey';result.state='waiting';result.label=status.rpc_error?bi('No answer from the router','Нет ответа от роутера'):bi('Router data is old','Данные роутера устарели');result.code=status.rpc_error?'STATUS-REQUEST-FAILED':'MONITOR-DATA-STALE';return result;}
  var rel=typeof channelReliability==='function'&&profile.interface&&profile.code!=='VPN-001'?channelReliability(profile,status,m.now):null;
  if(h.state==='failed'){
    result.kind='red';result.state='failed';
    if(rel&&rel.unreliable){result.label=bi('Reliability problem: ','Проблема с надёжностью: ')+reliabilityText(rel);result.code='CHANNEL-UNRELIABLE';result.reliability=rel;}
    return result;
  }
  if(h.state==='inactive'){result.label=bi('Off','Отключён');result.kind='red';result.state='off';return result;}
  if(h.state==='checking'){result.kind='grey';result.state='checking';result.label=bi('Waiting for the router\'s answer','Ждём ответа роутера');return result;}
  var route=channelPathSelection(status,m.now,m.primary&&m.primary.id||settings.plan_source,m.reserve&&m.reserve.id||settings.plan_target);
  if(route.authoritative&&!route.selected&&!route.moving&&route.code){result.kind='grey';result.state='waiting';result.label=bi('Traffic selection is not verified','Выбор канала трафика не подтверждён');result.code=route.code;return result;}
  var ns=status.native_failover||{};
  if(['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0&&Number.isFinite(ns.time)&&m.now-ns.time>=0&&m.now-ns.time<=30){result.kind='grey';result.state='switching';result.label=bi('Switching, waiting for the router','Переключение, ждём роутер');return result;}
  var autoRuns=!m.light||typeof autoWorking!=='function'||autoWorking(m.light);
  if(h.state==='healthy'&&!autoRuns){result.kind='yellow';result.state='ready';result.label=m.settings&&profile.id!==m.settings.plan_source&&profile.id!==m.settings.plan_target?bi('Other VPN: works, Auto does not use it','Другой VPN: работает, Auto его не использует'):m.settings&&profile.id===m.settings.plan_target?bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную'):bi('Primary channel: Alive; you can switch to it manually','Основной канал: Живой, можно переключиться на него вручную');}
  else if(h.state==='healthy'){
    if(m.selected===profile.id){result.kind='green';result.state='selected';result.label=bi('Working','Работает');}
    else if(m.selected){result.kind='yellow';result.state='standby';result.label=m.settings&&profile.id!==m.settings.plan_source&&profile.id!==m.settings.plan_target?bi('Other VPN: works, Auto does not use it','Другой VPN: работает, Auto его не использует'):m.settings&&profile.id===m.settings.plan_source?bi('Primary channel: Alive; you can switch to it manually','Основной канал: Живой, можно переключиться на него вручную'):bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную');}
    else{result.kind='grey';result.state='waiting';result.label=bi('Waiting for the router\'s answer which channel carries traffic','Ждём ответа роутера, какой канал несёт трафик');}
  }
  if(h.state==='unknown'){result.kind='grey';result.state='waiting';result.label=bi('Waiting for the router\'s answer','Ждём ответа роутера');}
  if(h.state==='healthy'&&rel&&rel.unreliable){result.kind='yellow';result.label=bi('Works, but reliability problem: ','Работает, но проблема с надёжностью: ')+reliabilityText(rel);result.code='CHANNEL-UNRELIABLE';result.reliability=rel;}
  if((result.state==='ready'||result.state==='standby')&&!result.reliability)result.badgeLabel=primary||reserve?bi('Alive; you can switch to it manually','Живой, можно переключиться на него вручную'):bi('Works; Auto does not use it','Работает; Auto его не использует');
  return result;
}
function dvChannelLamp(use){return E('span',{'class':'hv-check-lamp hv-check-'+use.kind,'role':'img','aria-label':use.label,'title':use.label});}
function channelDisplayUse(profile,status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),settings=(inventory||{}).settings||{},m={now:now,settings:settings,
    primary:vendorDisplayMember(status,inventory,'source',now),reserve:vendorDisplayMember(status,inventory,'target',now),selected:vendorDisplaySelected(status,inventory,now),
    light:typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null};
  return dvChannelUse(profile,m,status);
}
function renderChannelHeader(profile,status,inventory){
  var use=channelDisplayUse(profile,status,inventory);
  return E('div',{'class':'hv-server-top'},[E('div',{'class':'hv-channel-heading'},[dvChannelLamp(use),E('div',{'class':'hv-channel-heading-text'},[E('strong',{'class':'hv-protocol'},use.role),E('span',{'class':'hv-channel-protocol'},protocolLabel(profile))])]),
    E('span',{'class':'hv-route-badge hv-route-'+use.kind+(use.reliability?' hv-route-badge-long':''),'data-route-state':use.state},(use.badgeLabel||use.label)+(safeCode(use.code)?' · '+use.code:safeCode(profile.code)?' · '+profile.code:'')),
    typeof renderChannelPing==='function'?renderChannelPing(profile,status,typeof statusNow==='function'?statusNow(status):Date.now()/1000):null,
    E('span',{'class':'hv-profile-detail'},(use.code==='STATUS-REQUEST-FAILED'||use.code==='MONITOR-DATA-STALE')?bi('The page shows nothing as working until the router answers again. Reload the page (Ctrl+F5); if it repeats, check Monitoring in Settings.','Пока роутер не ответит, страница ничего не считает рабочим. Обновите страницу (Ctrl+F5); если повторяется, проверьте мониторинг в «Настройках».'):(profile.interface?bi('VPN server connection: established','Соединение с VPN-сервером: установлено'):bi('VPN server connection: none','Соединение с VPN-сервером: нет'))+' · '+(use.state==='selected'?bi('your internet goes through this channel','ваш интернет идёт через этот канал'):use.state==='standby'?bi('spare channel, your internet does not use it now','запасной канал, ваш интернет сейчас через него не идёт'):use.state==='failed'?bi('router checks fail: internet through this channel does not work','проверки роутера не проходят: интернет через этот канал не работает'):use.state==='switching'?bi('the route is being switched','маршрут переключается'):use.kind==='green'?bi('internet works through it; it takes over as soon as Auto is on','интернет через него работает; включится в работу, как только вы включите Auto'):bi('waiting for the first router check','ждём первую проверку роутера')))]);
}
function dvCodes(codes){codes=codes.filter(safeCode);return codes.length?E('code',{'class':'hv-dv-code'},codes.join(' · ')):null;}
// One model for all designs: what the page says about the system right now.
function dvModel(status,inventory,rows,month){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),settings=(inventory||{}).settings||{},light=autoLightModel(status,inventory,now),counts=serverCounts(status,inventory,rows,now);
  var selected=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):selectedProfile(status,now),selectedRow=dvProfile(rows,selected),primary=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):dvProfile(rows,settings.plan_source),reserve=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):dvProfile(rows,settings.plan_target);
  var active=rows.filter(function(p){return p.interface;}),good=0,total=0;
  var rank=dvRank(status);active.forEach(function(p){var r=rank[p.id];if(r){good+=r.good;total+=r.n;}});
  var tone,headline;
  if(status.rpc_error){tone='bad';headline=bi('No data from the router','Нет данных от роутера');}
  else if(!counts.connected){tone='off';headline=bi('No VPN is connected','Ни один VPN не подключён');}
  else if(light.key==='problem'){tone='bad';headline=light.title;}
  else if(light.key==='reserve'){tone='warn';headline=bi('Working on the reserve','Работаю на резерве');}
  else if(counts.working===counts.connected){tone='ok';headline=bi('Everything works.','Всё работает.');}
  else if(counts.working===0){tone='bad';headline=bi('No VPN works right now.','Сейчас ни один VPN не работает.');}
  else{tone='warn';headline=bi('Some VPNs do not work.','Часть VPN не работает.');}
  var age=Number.isFinite(status.time)?Math.max(0,Math.round(now-status.time)):null;
  var via=selectedRow?bi('Traffic goes through ','Трафик идёт через сервер ')+serverTitle(selectedRow)+'. ':'';
  var sub=via+(age==null?bi('No fresh check.','Нет свежей проверки.'):bi('Last check '+age+' s ago.','Последняя проверка '+age+' с назад.'));
  return {now:now,settings:settings,light:light,counts:counts,selected:selected,selectedRow:selectedRow,primary:primary,reserve:reserve,active:active,tone:tone,headline:headline,sub:sub,
    passPercent:total?100*good/total:null,traffic:month?bytes(month.rx+month.tx):bi('No data','Нет данных'),rank:rank};
}
function dvKpi(label,value){return E('div',{},[E('small',{},label),E('b',{},value)]);}
function dvCard(title,children,cls){return E('section',{'class':'hv-dv-card'+(cls?' '+cls:'')},[title?E('h3',{},title):null].concat(children).filter(Boolean));}

/* ---------- A · Control room ---------- */
function dvServerRows(status,rows,m){
  var sorted=sortServerCards(rows,m.selected,m.now);
  if(!sorted.length)return E('p',{'class':'hv-dv-empty'},bi('No VPN profiles found on the router.','На роутере не найдено VPN-профилей.'));
  return E('div',{'class':'hv-dv-rows'},sorted.map(function(p){
    var h=profileHealth(p,m.now),use=dvChannelUse(p,m,status),r=m.rank[p.id],pct=dvPercent(r);
    return E('div',{'class':'hv-dv-row','data-profile':p.id,'data-route-state':use.state},[dvChannelLamp(use),
      E('div',{'class':'hv-dv-name'},[E('b',{},countryName(p)||customName(p)||protocolLabel(p)),E('small',{},use.role+' · '+protocolLabel(p)+' · '+use.label)]),
      dvSpark(dvSeries(status,p.id,12)),
      E('span',{'class':'hv-dv-num'},h.state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0)+' '+bi('ms','мс'):'—'),
      E('span',{'class':'hv-dv-num'},dvPercentText(pct))]);
  }));
}
function dvEventList(status,rows,limit){
  var list=dvEvents(status,rows,limit);
  if(!list.length)return E('p',{'class':'hv-dv-empty'},bi('No switches or failures are recorded on the router.','На роутере не записано ни переключений, ни сбоев.'));
  return E('ul',{'class':'hv-dv-events'},list.map(function(e){return E('li',{},[E('time',{},dvDay(e.time)+' '+dvClock(e.time)),E('span',{},e.text),dvCodes(e.codes)].filter(Boolean));}));
}
function renderDesignA(ctx,m){
  var strip=E('section',{'class':'hv-dv-strip hv-dv-tone-'+m.tone,'role':'region','aria-label':bi('Status summary','Сводка состояния')},[
    E('div',{},[E('strong',{},m.headline),E('p',{},m.sub)]),
    E('div',{'class':'hv-dv-kpis'},[dvKpi(bi('VPN links ready','Доступные VPN-подключения'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
      dvKpi(bi('Checks passed','Проверок успешно'),dvPercentText(m.passPercent)),dvKpi(bi('Traffic this month','Трафик за месяц'),m.traffic)])]);
  var control=E('div',{'class':'hv-dv-control'},[ctx.controlCard]);
  var servers=dvCard(bi('Servers','Серверы'),[E('div',{'class':'hv-dv-rowhead','aria-hidden':'true'},[E('span'),E('span',{},bi('Server','Сервер')),E('span'),E('span',{'class':'hv-dv-num'},bi('HTTPS','HTTPS')),E('span',{'class':'hv-dv-num'},bi('Passed','Успех'))]),dvServerRows(ctx.status,ctx.rows,m)]);
  var events=dvCard(bi('Recent events','Последние события'),[dvEventList(ctx.status,ctx.rows,6),E('a',{'class':'hv-dv-more','href':'#events'},bi('All events and errors','Все события и ошибки'))]);
  return E('div',{'class':'hv-dv hv-dv-a'},[control,strip,E('div',{'class':'hv-dv-cols'},[E('div',{'class':'hv-dv-stack'},[servers]),events])]);
}

/* ---------- B · Calm ---------- */
var DV_OTHER_VPNS_EXPANDED=false;
function dvProfileIdentity(p){
  // Only metadata already exposed by the inventory; never fetch raw VPN files.
  var names=[p.router_name,p.name].filter(function(v){return typeof v==='string'&&v.trim()&&v.trim()!==countryName(p);}).map(function(v){return v.trim().slice(0,240);});
  return names.filter(function(v,i){return names.indexOf(v)===i;}).join(' · ')||bi('Profile identity unavailable','Название профиля недоступно');
}
function renderDesignB(ctx,m){
  var stats=E('div',{'class':'hv-dv-three'},[dvKpi(bi('VPN links ready','Доступные VPN-подключения'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
    dvKpi(bi('Problems today','Проблемы сегодня'),m.passPercent==null?bi('No data','Нет данных'):m.passPercent>=99.5?bi('None','Нет'):bi('Some','Есть')),dvKpi(bi('Used this month','Использовано за месяц'),m.traffic)]);
  var links=E('p',{'class':'hv-dv-links'},[E('a',{'href':'#statistics'},bi('Statistics','Статистика')),E('a',{'href':'#help'},bi('Help','Помощь')),E('a',{'href':'#learn'},bi('Training','Обучение')),E('a',{'href':'#events'},bi('Details for technicians →','Подробности для техников →'))]);
  // The state sentence block was removed (owner): the Primary/Reserve boxes in the Auto card already show it.
  return E('div',{'class':'hv-dv hv-dv-b'},[E('div',{'class':'hv-dv-control'},[ctx.controlCard]),stats,links].filter(Boolean));
}

/* ---------- C · Instrument panel ---------- */
function dvKv(key,value,cls){return E('span',{},[key+' ',E('b',{'class':cls||null},value)]);}
function dvLogLine(time,kind,text,codes){
  return E('div',{'class':'hv-dv-log-line hv-dv-log-'+kind},[E('time',{},dvClock(time,true)),E('b',{},kind==='ok'?'OK  ':kind==='warn'?'WARN':'FAIL'),E('span',{},text),codes&&codes.length?E('code',{'class':'hv-dv-code'},codes.join(' '))
    :null].filter(Boolean));
}
function renderDesignC(ctx,m){
  var ns=ctx.status.native_failover||{},agentVersion=(ctx.status.version||'—'),pkg=ctx.status.package||'—';
  var autoOn=m.light.key==='ok'||m.light.key==='reserve'||m.light.key==='switching';
  var bar=E('div',{'class':'hv-dv-status'},[dvKv('ctrl',String(ns.state||'UNKNOWN'),'hv-dv-k'),dvKv('auto',autoOn?'ON':'OFF'),dvKv('monitor',ctx.status.rpc_error?'?':(m.tone==='bad'&&!m.counts.connected?'?':'ON')),
    dvKv('active',m.selectedRow?(m.selectedRow.interface||m.selectedRow.id):'—'),dvKv('reserve',m.reserve?(m.reserve.interface||m.reserve.id):'—'),dvKv('pkg',String(pkg)),dvKv('ui',UI_BUILD)]);
  var chartCard=dvCard(bi('HTTPS latency, ms','HTTPS-задержка, мс'),[chart(ctx.status.samples||[],m.active)],'hv-dv-chart');
  var lines=[];
  (ctx.status.samples||[]).filter(function(s){return Number.isFinite(s.time);}).forEach(function(s){var failed=!!s.code&&s.code!=='CHECK-001';lines.push({time:s.time,kind:failed?'fail':(s.code?'warn':'ok'),text:dvShortName(ctx.rows,s.id)+' '+(Number.isFinite(s.rtt_ms)&&!s.code?'https '+Math.round(s.rtt_ms)+'ms '+(s.dns_ok?'dns ok':'dns fail'):(s.code?'':'dns '+(s.dns_ok?'ok':'fail'))),codes:s.code?[s.code]:[]});});
  dvEvents(ctx.status,ctx.rows,10).forEach(function(e){lines.push({time:e.time,kind:'warn',text:e.text,codes:e.codes});});
  lines.sort(function(a,b){return b.time-a.time;});
  var log=dvCard(bi('Event log','Журнал'),[lines.length?E('div',{'class':'hv-dv-log'},lines.slice(0,10).map(function(l){return dvLogLine(l.time,l.kind,l.text,l.codes);})):E('p',{'class':'hv-dv-empty'},bi('No checks recorded yet.','Проверок пока нет.'))],'hv-dv-logcard');
  var head=['St','Server','Proto','Group','HTTPS ms','Passed','Checks','Confidence'].map(function(h,i){return E('th',{'scope':'col','class':i>=4&&i<=6?'n':null},[bi(h,{'St':'Ст.','Server':'Сервер','Proto':'Прот.','Group':'Группа','HTTPS ms':'HTTPS, мс','Passed':'Успех','Checks':'Проверок','Confidence':'Достоверность'}[h])]);});
  var body=sortServerCards(ctx.rows,m.selected,m.now).map(function(p){
    var h=profileHealth(p,m.now),use=dvChannelUse(p,m,ctx.status),r=m.rank[p.id]||{n:0},mark=use.label;
    return E('tr',{'class':m.selected===p.id?'hv-dv-active':null,'data-profile':p.id,'data-route-state':use.state},[E('td',{'class':'hv-dv-st'},[dvChannelLamp(use),mark]),E('td',{},[countryName(p)||customName(p)||'—',E('small',{},use.role)]),E('td',{},p.protocol==='wireguard'?'wg':'ovpn'),E('td',{},p.channel||'—'),
      E('td',{'class':'n'},h.state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'),E('td',{'class':'n'},dvPercentText(dvPercent(r))),E('td',{'class':'n'},String(r.n||0)),E('td',{},dvConfidence(r.n||0))]);});
  var table=dvCard(bi('Servers','Серверы'),[E('div',{'class':'hv-dv-tablewrap'},E('table',{},[E('thead',{},E('tr',{},head)),E('tbody',{},body)]))],'hv-dv-servers');
  var keys=E('div',{'class':'hv-dv-keys'},[E('span',{},[E('kbd',{},'1'),'–',E('kbd',{},'9'),bi('sections','разделы')]),E('span',{},[E('kbd',{},'/'),bi('search','поиск')]),E('span',{},bi('Error codes are links to the error table','Коды ошибок — ссылки на таблицу ошибок'))]);
  return E('div',{'class':'hv-dv hv-dv-c'},[E('div',{'class':'hv-dv-control'},[ctx.controlCard]),bar,E('div',{'class':'hv-dv-grid'},[chartCard,log]),table,keys]);
}
function renderDesignOverview(design,ctx){
  var m=dvModel(ctx.status,ctx.inventory,ctx.rows,ctx.month);
  return design==='a'?renderDesignA(ctx,m):design==='c'?renderDesignC(ctx,m):renderDesignB(ctx,m);
}
// Keys of design C: 1..9 open the sections, "/" focuses the search box. Ignored while typing and with modifier keys.
function installDesignKeys(root,keys,go){
  if(!root||root.getAttribute('data-hv-keys'))return;root.setAttribute('data-hv-keys','1');
  document.addEventListener('keydown',function(event){
    if(root.getAttribute('data-hv-design')!=='c'||!root.isConnected||event.ctrlKey||event.metaKey||event.altKey)return;
    var el=event.target||{},tag=(el.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||tag==='select'||el.isContentEditable)return;
    if(event.key==='/'){var box=root.querySelector('.hv-page:not([hidden]) .hv-search')||root.querySelector('.hv-search');if(box){event.preventDefault();box.focus();}return;}
    var n=Number(event.key);if(n>=1&&n<=keys.length&&/^[1-9]$/.test(event.key)){event.preventDefault();go(keys[n-1]);}
  });
}

function checkLampCell(p,status,inventory){
  var h=profileHealth(p,Date.now()/1000),rank={healthy:1,checking:2,unknown:3,inactive:4,failed:5}[h.state]||9;
  var use=channelDisplayUse(p,status,inventory),kind=use.kind;h.label=use.label;
  return E('td',{'class':'hv-check-status','data-sort-value':String(rank)},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-check-word'},h.label)]);
}
var speedCardNode=null;
/* Bottom-left of the sidebar: two small lamps in one row (Auto, Monitoring) and the program version. Always visible. */
function fillSideStatus(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var light=typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null;
  var state=!model.fresh?'unknown':light&&typeof autoWorking==='function'?(autoWorking(light)?'on':light.key==='switching'||light.key==='unknown'?'unknown':'off'):(model.on||model.transitioning)?'on':'off';
  var autoText=state==='on'?bi('Auto ON','Auto вкл.'):state==='off'?bi('Auto OFF','Auto выкл.'):bi('Auto: no connection','Auto: нет связи');
  var autoHint=state==='on'?bi('Auto is on: it can switch to the reserve VPN.','Auto включён: он может переключить на резервный VPN.'):state==='off'?bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.'):bi('No fresh data from the router, so the state is not known.','Нет свежих данных от роутера, поэтому состояние неизвестно.');
  if(state==='unknown'&&model.fresh&&light&&light.code){autoText=bi('Auto: route not verified','Auto: маршрут не подтверждён');autoHint=light.hint+' · '+light.code;}
  var monText=bi('Monitoring','Мониторинг');
  var monHint=monitorFresh?bi('Monitoring works: fresh data from the router.','Мониторинг работает: свежие данные от роутера.'):status.rpc_error?bi('The router does not answer.','Роутер не отвечает.'):bi('Monitoring is not sending data.','Мониторинг не присылает данные.');
  function lamp(kind,text,hint){return E('span',{'class':'hv-side-lamp','role':'status','title':hint},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+hint)]);}
  function openAuto(event){if(event&&event.type==='keydown'&&event.key!=='Enter'&&event.key!==' ')return;if(event&&event.preventDefault)event.preventDefault();var link=document.querySelector('[data-hv-tab="overview"]');if(link&&typeof pageKeyNow==='function'&&pageKeyNow()!=='overview')link.click();else if(typeof overviewToAuto==='function')overviewToAuto();else if(typeof goToSection==='function')goToSection('overview','hv-auto-vpn');}
  var autoTitle=autoHint+' '+bi('Click to open Automatic VPN failover.','Нажмите, чтобы открыть «Автоматическое переключение VPN».');
  var autoLamp=E('span',{'class':'hv-side-lamp hv-side-lamp-link','role':'link','tabindex':'0','title':autoTitle,'click':openAuto,'keydown':openAuto},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+state,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},autoText),E('span',{'class':'hv-visually-hidden'},' — '+autoTitle)]);
  host.appendChild(E('div',{'class':'hv-side-lamps'},[autoLamp,lamp(monitorFresh?'on':'off',monText,monHint)]));
  var path=status.channel_path||{},ns=status.native_failover||{},selected=selectedProfile(status,now);
  var settings=(inventory||{}).settings||{},rows=status.profiles||[];
  function channel(role,label){
    var key=role==='source'?'source_profile_id':'target_profile_id',id=path[key]||ns[role]||settings['plan_'+role];
    var row=rows.filter(function(p){return p.id===id;})[0],health=row?profileHealth(row,now).state:'unknown',active=id&&selected===id;
    var rel=row&&health==='healthy'&&typeof channelReliability==='function'?channelReliability(row,status,now):null;
    var color,why;
    if(!monitorFresh){color='unknown';why=typeof dataCause==='function'?dataCause(status,now).text:bi('no router data','нет данных роутера');}
    else if(!row){color='off';why=bi('no channel is chosen for this role (Channels and servers)','для этой роли не выбран канал («Каналы и серверы»)');}
    else if(health==='inactive'){color='off';why=bi('switched off in the router','выключен в роутере');}
    else if(health==='failed'){color='off';why=typeof channelCheckText==='function'?channelCheckText(row,now):bi('router check failed','проверка роутера не прошла');}
    else if(rel&&rel.unreliable){color='switching';why=bi('works, but unreliable: ','работает, но ненадёжно: ')+reliabilityText(rel);}
    else if(health==='healthy'&&state==='unknown'){color='unknown';why=bi('waiting for the router\'s answer','ждём ответа роутера');}
    else if(light&&light.key==='unknown'&&light.code){color='unknown';why=light.title+' · '+light.code;}
    else if(health==='healthy'&&state!=='on'){color='switching';why=role==='source'?bi('Primary channel: Alive; you can switch to it manually','Основной канал: Живой, можно переключиться на него вручную'):bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную');}
    else if(health==='healthy'&&selected&&!active){color='switching';why=role==='source'?bi('Primary channel: Alive; you can switch to it manually','Основной канал: Живой, можно переключиться на него вручную'):bi('Reserve channel: Alive; you can switch to it manually','Запасной канал: Живой, можно переключиться на него вручную');}
    else if(health==='healthy'&&active){color='on';why=bi('works in Auto and carries your traffic','работает в автомате и несёт ваш трафик');}
    else{color='unknown';why=bi('waiting for the router\'s answer','ждём ответа роутера');}
    return lamp(color,label,label+': '+why);
    var hint=active&&health==='healthy'?bi('Selected channel; Internet works','Выбранный канал; Интернет работает'):active?bi('Selected channel; Internet check failed or pending','Выбранный канал; проверка Интернета не пройдена или ещё выполняется'):selected?bi('Channel not in use','Канал не задействован'):bi('The router has not reported which VPN is in use yet','Роутер ещё не сообщил, какой VPN работает');
    return lamp(color,label,hint);
  }
  host.appendChild(E('div',{'class':'hv-side-channel-lamps'},[channel('source',bi('Primary','Основной')),channel('target',bi('Reserve','Резерв'))]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}


/* Server answer time over the last hour: one line per server in its own colour; hovering a line or its legend entry
   highlights it and names the server. Replaces the older single-palette chart (later function declaration wins). */
var CHART_COLORS=['#2a6fd0','#e0832b','#2e9d4f','#d64545','#8b5cf6','#0ea5b7','#b8960b','#e0529c'];
function chart(samples,rows){
  var ns='http://www.w3.org/2000/svg';
  function svgNode(name,attrs,content){var n=document.createElementNS(ns,name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});if(content)n.textContent=content;return n;}
  var good=samples.filter(function(s){return Number.isFinite(s.rtt_ms)&&!s.code&&s.time;});
  if(good.length<2)return E('div',{'class':'hv-empty'},bi('The chart appears after two successful measurements. There is no artificial data here.','График появится после двух успешных измерений. Искусственных данных здесь нет.'));
  var end=Math.max.apply(null,good.map(function(s){return s.time;})),start=Math.max(end-3600,Math.min.apply(null,good.map(function(s){return s.time;})));
  good=good.filter(function(s){return s.time>=start;});
  var max=Math.max(100,Math.ceil(Math.max.apply(null,good.map(function(s){return s.rtt_ms;}))/100)*100);
  var svg=svgNode('svg',{viewBox:'0 0 820 260',role:'img','class':'hv-latency','aria-label':bi('HTTPS answer time of the connected servers, milliseconds','История HTTPS-задержки подключённых серверов в миллисекундах')});
  [0,0.5,1].forEach(function(f){var y=215-f*180;svg.appendChild(svgNode('line',{x1:55,x2:800,y1:y,y2:y,stroke:'var(--line)'}));svg.appendChild(svgNode('text',{x:5,y:y+4,fill:'var(--muted)','font-size':12},String(Math.round(max*f))+' '+(f===1?bi('ms','мс'):'')));});
  var tip=E('div',{'class':'hv-chart-tip','hidden':'hidden','role':'status'});
  var legend=E('div',{'class':'hv-legend hv-legend-interactive'});
  var wrap=E('div',{'class':'hv-chart'},[]);
  var entries=[];
  function focus(id){
    entries.forEach(function(e){var on=id===null||id===e.id;e.path.setAttribute('class',on?'hv-line hv-line-on':'hv-line hv-line-off');e.dot.setAttribute('class',on?'hv-dot-end':'hv-dot-end hv-line-off');e.item.className='hv-legend-item'+(id===e.id?' hv-legend-active':id!==null?' hv-legend-dim':'');});
  }
  rows.filter(function(p){return good.some(function(s){return s.id===p.id;});}).forEach(function(p,i){
    var color=CHART_COLORS[i%CHART_COLORS.length],name=serverTitle(p);
    var points=good.filter(function(s){return s.id===p.id;}).sort(function(a,b){return a.time-b.time;}),path='',previous;
    points.forEach(function(s){var x=55+(s.time-start)/Math.max(1,end-start)*745,y=215-s.rtt_ms/max*180;path+=(previous&&s.time-previous<=90?' L':' M')+x.toFixed(1)+','+y.toFixed(1);previous=s.time;});
    var line=svgNode('path',{d:path,fill:'none',stroke:color,'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round','class':'hv-line hv-line-on'});
    var title=svgNode('title',{},name);line.appendChild(title);
    var hit=svgNode('path',{d:path,fill:'none',stroke:'transparent','stroke-width':16,'class':'hv-line-hit'});
    var last=points[points.length-1],lx=55+(last.time-start)/Math.max(1,end-start)*745,ly=215-last.rtt_ms/max*180;
    var dot=svgNode('circle',{cx:lx.toFixed(1),cy:ly.toFixed(1),r:4.5,fill:color,'class':'hv-dot-end'});
    var avg=points.reduce(function(a,s){return a+s.rtt_ms;},0)/points.length;
    var item=E('button',{'type':'button','class':'hv-legend-item','mouseenter':function(){focus(p.id);},'mouseleave':function(){focus(null);},'focus':function(){focus(p.id);},'blur':function(){focus(null);}},[E('i',{'style':'background:'+color}),E('span',{},name),E('small',{},Math.round(avg)+' '+bi('ms avg','мс в среднем'))]);
    function showTip(ev){
      var box=wrap.getBoundingClientRect(),x=ev.clientX-box.left,y=ev.clientY-box.top;
      var rect=svg.getBoundingClientRect(),vx=(ev.clientX-rect.left)/rect.width*820,t=start+Math.max(0,Math.min(1,(vx-55)/745))*(end-start);
      var near=points.reduce(function(b,s){return Math.abs(s.time-t)<Math.abs(b.time-t)?s:b;},points[0]);
      tip.hidden=false;tip.style.left=Math.min(Math.max(8,x+12),Math.max(8,box.width-190))+'px';tip.style.top=Math.max(4,y-48)+'px';
      tip.textContent=name+' · '+Math.round(near.rtt_ms)+' '+bi('ms','мс')+' · '+new Date(near.time*1000).toLocaleTimeString();
      tip.style.borderColor=color;
    }
    hit.addEventListener('mousemove',function(ev){focus(p.id);showTip(ev);});
    hit.addEventListener('mouseleave',function(){focus(null);tip.hidden=true;});
    line.addEventListener('mouseenter',function(){focus(p.id);});
    svg.appendChild(hit);svg.appendChild(line);svg.appendChild(dot);
    legend.appendChild(item);entries.push({id:p.id,path:line,dot:dot,item:item});
  });
  svg.appendChild(svgNode('text',{x:55,y:247,fill:'var(--muted)','font-size':12},new Date(start*1000).toLocaleTimeString()));
  svg.appendChild(svgNode('text',{x:800,y:247,fill:'var(--muted)','font-size':12,'text-anchor':'end'},new Date(end*1000).toLocaleTimeString()));
  [svg,tip,legend,E('small',{},bi('HTTPS answer time, ms, last hour. Each server has its own colour; point at a line or at a name to highlight it. Gaps longer than 90 seconds are not joined.','HTTPS, мс · последний час. У каждого сервера свой цвет; наведите курсор на линию или на название, чтобы выделить. Разрывы длиннее 90 секунд не соединяются.'))].forEach(function(n){wrap.appendChild(n);});
  return wrap;
}

/* Current measured payload progress, separate from completed-test history. */
var SPEED_LIVE_CACHE=null,SPEED_LIVE_REQUESTED=null,SPEED_LIVE_HOSTS=[],SPEED_LIVE_BUSY=false;
function speedLiveRunning(data){return !!data&&['QUEUED','RUNNING'].indexOf(data.state)>=0;}
function speedLiveNumber(n,max){return Number.isFinite(n)&&n>=0&&n<=max;}
function speedLiveSnapshot(raw){
  if(!raw||!['IDLE','QUEUED','RUNNING','DONE','FAILED','CANCELLED'].includes(raw.state)||!Array.isArray(raw.profiles)||raw.profiles.length>8||!speedLiveNumber(raw.server_time,4102444800))return null;
  if(raw.state!=='IDLE'&&(typeof raw.run_id!=='string'||!/^[a-f0-9]{32}$/.test(raw.run_id)))return null;
  var rows=[],seen={};
  raw.profiles.forEach(function(r){
    if(!r||typeof r.id!=='string'||!/^[A-Za-z0-9_.:-]{1,96}$/.test(r.id)||seen[r.id]||!Array.isArray(r.samples)||r.samples.length>128)return;
    seen[r.id]=true;var last=-1,samples=[];
    r.samples.forEach(function(p){if(!Array.isArray(p)||p.length!==3||!speedLiveNumber(p[0],300)||p[0]<last||p.slice(1).some(function(v){return v!==null&&!speedLiveNumber(v,10000000);})||p.slice(1).filter(function(v){return v!==null;}).length!==1)return;last=p[0];samples.push(p.slice());});
    rows.push({id:r.id,phase:['waiting','resolving','latency','download','upload','done','failed','cancelled'].includes(r.phase)?r.phase:'failed',samples:samples,updated:r.updated,download_mbps:speedLiveNumber(r.download_mbps,10000000)?r.download_mbps:null,upload_mbps:speedLiveNumber(r.upload_mbps,10000000)?r.upload_mbps:null,code:typeof r.code==='string'&&/^SPEED-[A-Z0-9-]{1,64}$/.test(r.code)?r.code:null});
  });
  return {run_id:raw.run_id||null,state:raw.state,profiles:rows,server_time:raw.server_time,code:raw.code};
}
function speedLiveAccept(raw){
  var data=speedLiveSnapshot(raw);if(!data)return false;
  if(SPEED_LIVE_REQUESTED&&data.run_id!==SPEED_LIVE_REQUESTED.run_id)return false;
  if(SPEED_LIVE_CACHE&&data.server_time<SPEED_LIVE_CACHE.server_time)return false;
  SPEED_LIVE_CACHE=data;
  if(SPEED_LIVE_REQUESTED&&data.run_id===SPEED_LIVE_REQUESTED.run_id&&!speedLiveRunning(data))SPEED_LIVE_REQUESTED=null;
  SPEED_LIVE_HOSTS=SPEED_LIVE_HOSTS.filter(function(host){return host.isConnected;});
  SPEED_LIVE_HOSTS.forEach(function(host){host.updateSpeedLive(data);if(host.setSpeedConnection)host.setSpeedConnection(true);});return true;
}
function speedLiveQueued(result,ids){
  if(!result||result.accepted!==true||typeof result.run_id!=='string'||!/^[a-f0-9]{32}$/.test(result.run_id))return;
  SPEED_LIVE_REQUESTED={run_id:result.run_id,state:'QUEUED',server_time:Date.now()/1000,profiles:ids.map(function(id){return {id:id,phase:'waiting',samples:[]};})};
  SPEED_LIVE_CACHE=null;SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;}).forEach(function(h){h.updateSpeedLive(SPEED_LIVE_REQUESTED);});
}
function speedLivePhase(row,data){
  if(!row)return bi('Not selected for this test','Не выбран для этого теста');
  if(data.state==='CANCELLED'&&row.phase!=='done')return bi('Test cancelled','Тест отменён');
  if(data.state==='FAILED'&&row.phase!=='done')return bi('Test interrupted','Тест прерван');
  var names={waiting:bi('Waiting for its turn','Ожидает своей очереди'),resolving:bi('Connecting to the test endpoint','Подключение к тестовому серверу'),latency:bi('Checking latency','Проверка задержки'),download:bi('Measuring download','Измеряется скачивание'),upload:bi('Measuring upload','Измеряется отдача'),done:bi('Test completed','Тест завершён'),failed:bi('Test failed','Ошибка теста'),cancelled:bi('Test cancelled','Тест отменён')};
  return names[row.phase]||bi('Waiting for progress','Ожидание результатов');
}
function speedLiveGraph(row,name){
  var points=row&&row.samples||[],values=[];points.forEach(function(p){p.slice(1).forEach(function(v){if(v!==null)values.push(v);});});
  if(!values.length)return E('p',{'class':'hv-speed-live-empty'},bi('Measured transfer rates will appear when this channel is tested.','Замеры скорости появятся, когда начнётся тест этого канала.'));
  var end=Math.max(2,Math.ceil(points[points.length-1][0])),maximum=Math.max(1,Math.ceil(Math.max.apply(null,values)*1.12));
  var x=function(t){return 55+t/end*520;},y=function(v){return 205-v/maximum*170;};
  var svg=speedChartSvg('svg',{'viewBox':'0 0 610 250','role':'img','aria-label':name+' · '+bi('Live download and upload, Mbps','Скачивание и отдача в реальном времени, Мбит/с'),'class':'hv-speed-live-svg'});
  for(var i=0;i<=4;i++){var value=maximum*i/4,line=y(value);svg.appendChild(speedChartSvg('line',{x1:55,y1:line,x2:575,y2:line,stroke:'#b8c3cd','stroke-width':.6}));svg.appendChild(speedChartSvg('text',{x:48,y:line+4,'text-anchor':'end',fill:'currentColor','font-size':11},value.toFixed(value<10?1:0)));}
  svg.appendChild(speedChartSvg('text',{x:55,y:18,fill:'currentColor','font-size':11},bi('Mbps','Мбит/с')));
  [0,.5,1].forEach(function(k){svg.appendChild(speedChartSvg('text',{x:x(end*k),y:229,'text-anchor':'middle',fill:'currentColor','font-size':11},(end*k).toFixed(1)+' '+bi('s','с')));});
  [[1,'download','#139c75',bi('Download','Скачивание')],[2,'upload','#386af2',bi('Upload','Отдача')]].forEach(function(series){
    var segment=[];
    function flush(){if(segment.length>1)svg.appendChild(speedChartSvg('polyline',{points:segment.join(' '),fill:'none',stroke:series[2],'stroke-width':2.5,'data-speed-live-series':series[1]}));segment=[];}
    points.forEach(function(p){var v=p[series[0]];if(v===null){flush();return;}segment.push(x(p[0])+','+y(v));var dot=speedChartSvg('circle',{cx:x(p[0]),cy:y(v),r:2.5,fill:series[2],'data-speed-live-point':series[1]});dot.appendChild(speedChartSvg('title',{},series[3]+': '+v.toFixed(2)+' '+bi('Mbps','Мбит/с')+' · '+p[0].toFixed(1)+' '+bi('s since channel test started','с от начала теста канала')));svg.appendChild(dot);});flush();
  });return svg;
}
function renderSpeedLive(status,inventory,onLive){
  var profiles=status.profiles||[],settings=inventory.settings||{},now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var ids=typeof rolePairIds==='function'?rolePairIds(status,inventory,now):[settings.native_source,settings.native_target];
  var root=E('section',{'class':'hv-speed-live','data-speed-live-root':'1'}),cards=E('div',{'class':'hv-speed-live-grid'}),state=E('p',{'class':'hv-speed-live-state','role':'status'}),connection=E('p',{'class':'hv-speed-live-connection','role':'status'});
  connection.hidden=true;root.setSpeedConnection=function(ok){connection.hidden=ok;connection.textContent=ok?'':bi('Progress unavailable; last received measurements are retained.','Обновление недоступно; показаны последние полученные замеры.');};
  root.appendChild(E('h4',{},bi('Current test · download and upload','Текущий тест · скачивание и отдача')));root.appendChild(state);root.appendChild(connection);root.appendChild(cards);
  var panels=['source','target'].map(function(role,index){
    var id=ids[index],p=profiles.find(function(p){return p.id===id;}),label=index===0?bi('Primary channel','Основной канал'):bi('Reserve channel','Резервный канал'),phase=E('p',{'class':'hv-speed-live-phase'}),rates=E('div',{'class':'hv-speed-live-rates'}),plot=E('div',{'class':'hv-speed-live-plot'});
    cards.appendChild(E('article',{'class':'hv-speed-live-channel','data-speed-live-role':role},[E('h4',{},label),E('strong',{},p?serverTitle(p):bi('Select a VPN pair in Settings','Выберите пару VPN в настройках')),p&&typeof endpointText==='function'?E('small',{'class':'hv-server-address'},endpointText(p,now)):null,phase,rates,plot].filter(Boolean)));
    return {id:id,profile:p,label:label,phase:phase,rates:rates,plot:plot};
  });
  root.appendChild(E('small',{},bi('Channels are measured in sequence. Download is green, upload is blue. The horizontal axis is seconds since that channel test started. Each point is measured test payload transferred during an interval; missing directions and errors are not zero speed.','Каналы измеряются по очереди. Скачивание — зелёным, отдача — синим. По горизонтали — секунды от начала теста канала. Точки показывают скорость передачи тестовых данных за интервал; отсутствие измерения и ошибки не означают нулевую скорость.')));
  root.updateSpeedLive=function(data){
    data=data||{state:'IDLE',profiles:[]};root.setAttribute('data-speed-live-state',data.state);
    state.textContent=speedLiveRunning(data)?bi('Live test · refresh every second','Текущий тест · обновление каждую секунду'):data.state==='DONE'?bi('Latest test completed · measured interval rates below','Последний тест завершён · ниже скорости измеренных интервалов'):data.state==='CANCELLED'?bi('Test cancelled · received measurements retained','Тест отменён · полученные замеры сохранены'):data.state==='FAILED'?bi('Test interrupted · see the diagnostic code','Тест прерван · смотрите код диагностики'):bi('Press Test speed to see live measurements for the selected channels.','Нажмите «Тестировать скорость», чтобы увидеть текущие замеры выбранных каналов.');
    panels.forEach(function(panel){
      var row=(data.profiles||[]).find(function(r){return r.id===panel.id;});panel.phase.textContent=panel.profile?speedLivePhase(row,data):bi('Channel is not configured','Канал не настроен');if(row&&row.code)panel.phase.appendChild(E('span',{},' · '+row.code));
      while(panel.rates.firstChild)panel.rates.removeChild(panel.rates.firstChild);
      ['download','upload'].forEach(function(key){var value=row&&row[key+'_mbps'];panel.rates.appendChild(E('span',{'class':'hv-speed-live-'+key},[E('b',{},key==='download'?bi('Download: ','Скачивание: '):bi('Upload: ','Отдача: ')),value!=null&&Number.isFinite(value)?value.toFixed(2)+' '+bi('Mbps','Мбит/с'):'—']));});
      while(panel.plot.firstChild)panel.plot.removeChild(panel.plot.firstChild);panel.plot.appendChild(speedLiveGraph(row,panel.label));
    });if(onLive)onLive(data);
  };
  var snapshot=speedLiveSnapshot((status.speed_tests||{}).live);
  if(snapshot&&(!SPEED_LIVE_REQUESTED||snapshot.run_id===SPEED_LIVE_REQUESTED.run_id)&&(!SPEED_LIVE_CACHE||snapshot.server_time>=SPEED_LIVE_CACHE.server_time))SPEED_LIVE_CACHE=snapshot;
  root.updateSpeedLive(SPEED_LIVE_REQUESTED||SPEED_LIVE_CACHE||snapshot||{state:(status.speed_tests||{}).state||'IDLE',profiles:[]});SPEED_LIVE_HOSTS=SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;});SPEED_LIVE_HOSTS.push(root);return root;
}
function installSpeedLive(root,getPage){
  var call=rpc.declare({object:'homensai-vpn',method:'speed_live',expect:{}}),timer=window.setInterval(function(){
    if(!root.isConnected){window.clearInterval(timer);return;}
    if(SPEED_LIVE_BUSY||!['tests','ranking'].includes(getPage())||!SPEED_LIVE_REQUESTED&&!speedLiveRunning(SPEED_LIVE_CACHE))return;
    SPEED_LIVE_BUSY=true;
    Promise.resolve().then(call).then(speedLiveAccept).catch(function(){SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;}).forEach(function(h){h.setSpeedConnection(false);});}).finally(function(){SPEED_LIVE_BUSY=false;});
  },1000);
}

/* One table for the speed tests: tick servers, press "Test speed" (or cancel), and the same table shows the results.
   Replaces the older panel that had a drop-down, a second table of results and a "recommended priorities" button
   (later function declaration wins). */
var speedSelected={};
var speedFeedback=null;
function speedStartRequest(s,selected,mib,duration,streams){
  function start(){return rpc.declare({object:'homensai-vpn',method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams);}
  if(s.speed_enabled)return start();
  // Explicit review enables manual tests; do not unexpectedly enable stored auto-new preferences.
  return rpc.declare({object:'homensai-vpn',method:'setup_speed',params:['enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'],expect:{}})(true,false,mib,duration,streams,s.speed_daily_mib==null?128:s.speed_daily_mib,s.speed_busy_mbps==null?2:s.speed_busy_mbps).then(function(result){
    if(!result||result.saved!==true)return {accepted:false,code:result&&result.code||'SPEED-CONFIG-UNCONFIRMED'};
    s.speed_enabled=true;s.speed_auto_new=false;return start();
  });
}
function speedReason(code){
  var messages={
    'SPEED-BUSY':['A speed test is already running.','Тест скорости уже выполняется.'],
    'SPEED-CPU-BUSY':['Router CPU is busy even after pausing Auto and monitoring; retry later.','Процессор роутера занят даже после паузы Auto и мониторинга; повторите позже.'],
    'SPEED-TRAFFIC-BUSY':['VPN traffic is above the configured limit; retry when it is quieter.','VPN-трафик выше заданного порога; повторите, когда нагрузка снизится.'],
    'SPEED-TRAFFIC-UNKNOWN':['Waiting for fresh traffic observations.','Ожидание свежих наблюдений за трафиком.'],
    'SPEED-COOLDOWN':['Wait at least 60 seconds between manual tests.','Между ручными тестами нужно подождать не менее 60 секунд.'],
    'SPEED-DAILY-LIMIT':['The daily test quota has been reached.','Достигнута суточная квота тестов.'],
    'SPEED-SWITCH-IN-PROGRESS':['A channel switch is in progress; wait until it finishes.','Идёт переключение канала; дождитесь его завершения.']
  };
  return messages[code]?bi.apply(null,messages[code]):bi('Test not started. See diagnostic code: ','Тест не запущен. Код диагностики: ')+code;
}
function speedStateText(history){
  var state=history.state||'IDLE';
  if(state==='QUEUED'&&history.preparation==='pausing')return bi('Pausing Auto and monitoring before the test…','Приостанавливаем Auto и мониторинг перед тестом…');
  if(state==='IDLE'||state==='COMPLETED'||state==='COMPLETE'||state==='DONE')return bi('No test is running.','Сейчас тест не идёт.');
  if(state==='RUNNING'||state==='QUEUED'||state==='STARTING')return bi('A test is running; the table fills in as results arrive.','Идёт тест; таблица заполняется по мере поступления результатов.');
  return bi('State: ','Состояние: ')+state;
}
function speedPanel(status,inventory,period,onPeriod){
  var history=status.speed_tests||{},s=inventory.settings||{},profiles=status.profiles||[];
  var active=profiles.filter(function(p){return p.interface;}).slice(0,8);
  var running=['RUNNING','QUEUED','STARTING'].indexOf(history.state)>=0||!!SPEED_LIVE_REQUESTED||speedLiveRunning(SPEED_LIVE_CACHE);
  if(!Object.keys(speedSelected).length)active.forEach(function(p){speedSelected[p.id]=true;});
  var now=Date.now()/1000;
  function dateKey(t){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t*1000));}
  var today=dateKey(now);
  var rows=(history.results||[]).filter(function(row){return Number.isFinite(row.time)&&row.time<=now+5;});
  rows=rows.filter(function(row){return period==='latest'||period==='day'&&dateKey(row.time)===today||period==='week'&&row.time>=now-7*86400||period==='month'&&dateKey(row.time).slice(0,7)===today.slice(0,7);});
  var grouped={};
  rows.sort(function(a,b){return b.time-a.time;}).forEach(function(row){var g=grouped[row.id]||(grouped[row.id]={last:row,good:[],count:0});g.count++;if(!row.code&&Number.isFinite((row.download||{}).mbps)&&Number.isFinite((row.upload||{}).mbps))g.good.push(row);});
  function mean(good,key){return good.length?good.reduce(function(sum,row){return sum+(row[key]||{}).mbps;},0)/good.length:null;}
  // Connected servers first (they can be ticked), then servers that only have history.
  var ids=active.map(function(p){return p.id;});
  Object.keys(grouped).forEach(function(id){if(ids.indexOf(id)<0)ids.push(id);});
  ids=ids.map(function(id,i){return {id:id,i:i,time:grouped[id]&&grouped[id].last.time||0};}).sort(function(a,b){return b.time-a.time||a.i-b.i;}).map(function(row){return row.id;});
  var section=E('section',{'class':'hv-chart-card hv-speed-panel','data-stats-reset':'ranking'},[
    E('h3',{},bi('VPN server speed tests','Тесты скорости VPN-серверов')),
    E('p',{},bi('Tick the servers you want to measure and press “Test speed”. The same table fills in with the results. A test downloads and uploads a small amount of data through the VPN to Cloudflare; it is a sample of what the application sees, not an Ookla score. VPNs that are not connected cannot be ticked: this program never connects them.','Отметьте серверы, которые хотите измерить, и нажмите «Тестировать скорость». Эта же таблица заполнится результатами. Тест скачивает и отдаёт небольшой объём данных через VPN до Cloudflare; это выборочный результат на уровне приложения, а не оценка Ookla. Неподключённые VPN отметить нельзя: эта программа их не подключает.'))]);
  var table=E('table',{'class':'table hv-speed-table'},[]);
  var boxes=[];
  var all=E('input',{'type':'checkbox','aria-label':bi('Select all connected servers','Выбрать все подключённые серверы'),'change':function(){boxes.forEach(function(b){if(!b.disabled){b.checked=all.checked;speedSelected[b.getAttribute('data-id')]=all.checked;}});}});
  table.appendChild(E('tr',{},[E('th',{},all),E('th',{},bi('Server','Сервер')),E('th',{},bi('Download, Mbps','Скачивание, Мбит/с')),E('th',{},bi('Upload, Mbps','Отдача, Мбит/с')),E('th',{},bi('Last test','Последний тест')),E('th',{},bi('Successful / all','Успешных / всего'))]));
  ids.forEach(function(id){
    var p=profiles.filter(function(x){return x.id===id;})[0],g=grouped[id],connected=!!(p&&p.interface);
    var good=g?(period==='latest'?(g.good[0]===g.last?[g.last]:[]):g.good):[];
    var box=E('input',{'type':'checkbox','data-id':id,'aria-label':bi('Test ','Тестировать ')+(p?serverTitle(p):id),'disabled':connected?null:'','change':function(){speedSelected[id]=box.checked;}});
    box.checked=connected&&!!speedSelected[id];boxes.push(box);
    var down=mean(good,'download'),up=mean(good,'upload');
    var lastCell=g?[g.last.code?E('a',{'href':'#events','class':'hv-errlink','click':function(ev){ev.preventDefault();showErrorCode(g.last.code);}},g.last.code):E('span',{'class':'hv-speed-ok'},'✓ OK'),E('small',{},' '+new Date(g.last.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}))]:[E('span',{'class':'hv-muted'},bi('not tested yet','ещё не тестировался'))];
    table.appendChild(E('tr',{'class':connected?'':'hv-speed-off'},[E('td',{},box),E('td',{},[E('strong',{},p?serverTitle(p):id),typeof endpointText==='function'?E('small',{'class':'hv-server-address'},endpointText(p,now)):null,connected?null:E('small',{},' '+bi('(not connected)','(не подключён)'))].filter(Boolean)),E('td',{},down==null?'—':down.toFixed(1)),E('td',{},up==null?'—':up.toFixed(1)),E('td',{},lastCell),E('td',{},g?good.length+' / '+g.count:'—')]));
  });
  if(!ids.length)table.appendChild(E('tr',{},[E('td',{'colspan':'6'},bi('No connected VPN servers yet. Connect one in the GL.iNet VPN Dashboard.','Подключённых VPN-серверов пока нет. Подключите сервер в GL.iNet → VPN Dashboard.'))]));
  var test=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':running?'':null,'click':function(){
    var selected=active.filter(function(p){return speedSelected[p.id];}).map(function(p){return p.id;}),mib=s.speed_budget_mib==null?8:s.speed_budget_mib,duration=s.speed_duration==null?5:s.speed_duration,streams=s.speed_streams==null?2:s.speed_streams;
    if(running)return;
    if(!selected.length){ui.addNotification(null,E('p',{},bi('Tick at least one connected server in the table first.','Сначала отметьте в таблице хотя бы один подключённый сервер.')));return;}
    if(![['speed.budget_mib',mib],['speed.duration',duration],['speed.streams',streams]].every(function(row){return foolCheckNumber(row[0],row[1]).ok;})){ui.addNotification(null,E('p',{},bi('Check the speed test limits in the settings first.','Сначала проверьте ограничения теста скорости в настройках.')));return;}
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[!s.speed_enabled?E('p',{},bi('This will enable manual speed tests with the current limits and run the selected test. Automatic tests after connection remain off.','Будут включены ручные тесты с текущими лимитами и запущено выбранное измерение. Автотесты после подключения останутся выключены.')):null,E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('p',{'data-speed-pause-review':'1'},bi('Auto and background monitoring pause for the test. VPN connections remain up. Afterwards monitoring resumes before Auto; a manual Stop is respected.','На время теста Auto и фоновый мониторинг приостанавливаются. VPN остаются подключёнными. Затем возобновляется мониторинг и после него Auto; ручной Stop учитывается.')),E('ul',{},selected.map(function(id){var q=profiles.filter(function(p){return p.id===id;})[0];return E('li',{},q?serverTitle(q):id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return speedStartRequest(s,selected,mib,duration,streams).then(function(result){speedLiveQueued(result,selected);speedFeedback=result&&result.accepted===true?null:(result&&safeCode(result.code)?result.code:'SPEED-START-FAILED');ui.addNotification(null,E('p',{},result&&result.accepted===true?bi('The test is queued; results appear in the table.','Тест поставлен в очередь; результаты появятся в таблице.'):(result&&safeCode(result.code)?result.code:'SPEED-START-FAILED')));ui.hideModal();}).catch(function(){speedFeedback='SPEED-START-FAILED';ui.addNotification(null,E('p',{},'SPEED-START-FAILED'));});},{key:'speed-start'});}},(s.speed_enabled?bi('Run test','Запустить тест'):bi('Enable and run test','Включить и запустить тест'))),'speed-start')].filter(Boolean));
  }},bi('Test speed','Тестировать скорость'));
  var cancel=E('button',{'type':'button','class':'cbi-button','disabled':running?null:'','click':function(){return rpc.declare({object:'homensai-vpn',method:'speed_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.queued?bi('Cancel requested.','Отмена запрошена.'):bi('No test is running.','Сейчас тест не идёт.')));});}},bi('Cancel current test','Отменить текущий тест'));
  var periodSelect=E('select',{'aria-label':bi('Show results for','Показать результаты за'),'change':function(ev){onPeriod(ev.target.value);}},[['latest',bi('Latest test','Последний тест')],['day',bi('Today','Сегодня')],['week',bi('Last 7 days','Последние 7 дней')],['month',bi('Current calendar month','Текущий календарный месяц')]].map(function(row){return E('option',{value:row[0]},row[1]);}));periodSelect.value=period;
  section.appendChild(E('div',{'class':'hv-native-actions'},[test,cancel,E('label',{'class':'hv-speed-period'},[bi('Results for: ','Результаты за: '),periodSelect])]));
  section.appendChild(E('p',{'role':'status'},speedStateText(history)+' '+bi('Finished tests: ','Завершено тестов: ')+(history.completed||0)));
  if(!s.speed_enabled)section.appendChild(E('p',{'class':'hv-muted'},bi('Press Test speed to review enabling manual tests and their traffic budget.','Нажмите «Тестировать скорость»: откроется проверка включения ручных тестов и расхода трафика.')));
  if(speedFeedback)section.appendChild(E('p',{'class':'alert-message warning','role':'status'},speedReason(speedFeedback)+' · '+speedFeedback));
  section.appendChild(typeof limitTableRows==='function'?limitTableRows(table,5,'speed-other'):table);
  section.appendChild(renderSpeedLive(status,inventory,function(data){running=speedLiveRunning(data);test.disabled=running;cancel.disabled=!running;}));
  var oldChart=E('details',{'class':'hv-speed-completed-history','data-auto-disclosure':'speed-completed-history'},[E('summary',{},bi('Completed test history','История завершённых тестов')),renderSpeedChart(rows,profiles,period)]);
  if(typeof rememberDisclosure==='function')rememberDisclosure(oldChart,'speed-completed-history');section.appendChild(oldChart);
  section.appendChild(E('small',{},bi('Mean of successful tests; failed or cancelled tests are not counted as zero speed. History is sampled and bounded.','Среднее по успешным тестам; ошибки и отмены не считаются нулевой скоростью. История выборочная и ограниченная.')));
  if(history.history_error)section.appendChild(E('p',{},history.history_error));
  if(history.history_truncated)section.appendChild(E('p',{},'SPEED-HISTORY-TRUNCATED: '+history.history_truncated));
  return section;
}
/* Stored bounded HTTPS goodput samples. Failed measurements break the line. */
var SPEED_CHART_PROFILE=null;
function speedChartSamples(rows,id,period){
  var result=rows.filter(function(r){return r&&r.id===id&&Number.isFinite(r.time)&&r.time>0;}).slice().sort(function(a,b){return a.time-b.time;});
  return period==='latest'?result.slice(-1):result;
}
function speedChartValue(row,key){
  var value=row&&row[key]&&row[key].mbps;
  return !row.code&&Number.isFinite(value)&&value>=0&&value<=10000000?value:null;
}
function speedChartSvg(tag,attrs,text){
  var n=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});
  if(text!==undefined)n.textContent=text;return n;
}
function renderSpeedChart(rows,profiles,period){
  var ids=[];profiles.filter(function(p){return p.interface;}).forEach(function(p){if(ids.indexOf(p.id)<0)ids.push(p.id);});
  rows.forEach(function(r){if(r&&typeof r.id==='string'&&ids.indexOf(r.id)<0)ids.push(r.id);});
  if(ids.indexOf(SPEED_CHART_PROFILE)<0)SPEED_CHART_PROFILE=ids[0]||null;
  function name(id){var p=profiles.find(function(p){return p.id===id;}),last=rows.find(function(r){return r.id===id;});return p?serverTitle(p):last&&last.name||id;}
  var host=E('div',{'class':'hv-speed-chart-plot','style':'width:100%;overflow:hidden'}),summary=E('p',{'class':'hv-muted','role':'status'});
  function draw(){
    while(host.firstChild)host.removeChild(host.firstChild);
    var samples=speedChartSamples(rows,SPEED_CHART_PROFILE,period),values=[];
    samples.forEach(function(r){['download','upload'].forEach(function(k){var v=speedChartValue(r,k);if(v!==null)values.push(v);});});
    summary.textContent=bi('Measured tests only; gaps and errors are not zero speed.','Только выполненные измерения; пропуски и ошибки не означают нулевую скорость.');
    if(!values.length){host.appendChild(E('p',{},bi('Run a test: its download and upload results will appear here.','Запустите тест: здесь появятся результаты скачивания и отдачи.')));return;}
    var start=samples[0].time,end=samples[samples.length-1].time;
    if(end===start){start-=30;end+=30;}
    var maximum=Math.max(1,Math.ceil(Math.max.apply(null,values)*1.15));
    var x=function(t){return 65+(t-start)/(end-start)*810;},y=function(v){return 240-v/maximum*205;};
    var svg=speedChartSvg('svg',{'viewBox':'0 0 910 290','role':'img','aria-label':bi('Download and upload speed history in Mbps','История скорости скачивания и отдачи в Мбит/с'),'style':'display:block;width:100%;height:auto;min-height:180px'});
    for(var i=0;i<=4;i++){
      var value=maximum*i/4,lineY=y(value);
      svg.appendChild(speedChartSvg('line',{x1:65,y1:lineY,x2:875,y2:lineY,stroke:'#b8c3cd','stroke-width':.6}));
      svg.appendChild(speedChartSvg('text',{x:57,y:lineY+4,'text-anchor':'end',fill:'currentColor','font-size':12},value.toFixed(value<10?1:0)));
    }
    svg.appendChild(speedChartSvg('text',{x:65,y:18,fill:'currentColor','font-size':12},bi('Mbps','Мбит/с')));
    [0,.5,1].forEach(function(part){var t=start+(end-start)*part;svg.appendChild(speedChartSvg('text',{x:x(t),y:268,'text-anchor':'middle',fill:'currentColor','font-size':12},new Date(t*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})));});
    [['download','#139c75',bi('Download','Скачивание')],['upload','#386af2',bi('Upload','Отдача')]].forEach(function(series){
      var segment=[];
      function flush(){if(segment.length>1)svg.appendChild(speedChartSvg('polyline',{points:segment.join(' '),fill:'none',stroke:series[1],'stroke-width':2.5,'data-speed-series':series[0]}));segment=[];}
      samples.forEach(function(row){var v=speedChartValue(row,series[0]);if(v===null){flush();return;}segment.push(x(row.time)+','+y(v));
        var dot=speedChartSvg('circle',{cx:x(row.time),cy:y(v),r:4,fill:series[1],'data-speed-point':series[0]});
        dot.appendChild(speedChartSvg('title',{},name(row.id)+' · '+series[2]+': '+v.toFixed(2)+' '+bi('Mbps','Мбит/с')+' · '+new Date(row.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})));svg.appendChild(dot);
      });flush();
    });
    host.appendChild(svg);
  }
  var choose=E('select',{'aria-label':bi('Server for speed graph','Сервер графика скорости'),'style':'max-width:100%;min-height:42px;','change':function(ev){SPEED_CHART_PROFILE=ev.target.value;draw();}},ids.map(function(id){return E('option',{value:id},name(id));}));choose.value=SPEED_CHART_PROFILE||'';
  draw();
  return E('section',{'class':'hv-speed-history','style':'margin-top:24px;border-top:1px solid #d9dfe5;padding-top:16px;'},[
    E('h4',{},bi('Completed test averages','Средние скорости завершённых тестов')),choose,
    E('p',{},[E('span',{'style':'color:#139c75'},'● '+bi('Download','Скачивание')),' · ',E('span',{'style':'color:#386af2'},'● '+bi('Upload','Отдача'))]),host,summary
  ]);
}

/* Monthly traffic page: a day-by-day bar chart above the daily table. Replaces the older table-only panel
   (later function declaration wins). Bars: download and upload per calendar day (Berlin), VPN or WAN. */
var trafficScope='vpn';
function trafficUnit(maxBytes){return maxBytes>=1e9?{div:1e9,name:'GB'}:{div:1e6,name:'MB'};}
function trafficDayChart(vpnDays,wanDays,days,scope,onScope){
  var ns='http://www.w3.org/2000/svg';
  function svgNode(name,attrs,content){var n=document.createElementNS(ns,name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});if(content)n.textContent=content;return n;}
  var source=scope==='wan'?wanDays:vpnDays;
  var series=days.map(function(day){var row=source[day];var ok=row&&row.observed===true;return {day:day,ok:ok,rx:ok?Number(row.rx||0):0,tx:ok?Number(row.tx||0):0};});
  var maxBytes=Math.max.apply(null,[1].concat(series.map(function(d){return Math.max(d.rx,d.tx);})));
  var unit=trafficUnit(maxBytes),top=maxBytes/unit.div;
  var nice=top<=1?1:top<=2?2:top<=5?5:top<=10?10:Math.ceil(top/10)*10;
  var W=820,H=260,left=55,right=800,base=215,height=180,n=series.length,slot=(right-left)/Math.max(1,n),bar=Math.max(2,Math.min(9,slot/2-1));
  var svg=svgNode('svg',{viewBox:'0 0 '+W+' '+H,role:'img','class':'hv-latency','aria-label':bi('Daily traffic by day','Суточный трафик по дням')});
  [0,0.5,1].forEach(function(f){var y=base-f*height;svg.appendChild(svgNode('line',{x1:left,x2:right,y1:y,y2:y,stroke:'var(--line)'}));svg.appendChild(svgNode('text',{x:5,y:y+4,fill:'var(--muted)','font-size':12},(nice*f).toFixed(f&&nice<5?1:0)+' '+(f===1?unit.name:'')));});
  var wrap=E('div',{'class':'hv-chart'},[]),tip=E('div',{'class':'hv-chart-tip','hidden':'hidden','role':'status'});
  var DOWN='#2a6fd0',UP='#e0832b';
  series.forEach(function(d,i){
    var cx=left+slot*(i+0.5);
    var group=svgNode('g',{'class':'hv-bar-group'});
    if(d.ok){
      var hd=Math.max(1,d.rx/unit.div/nice*height),hu=Math.max(1,d.tx/unit.div/nice*height);
      group.appendChild(svgNode('rect',{x:(cx-bar).toFixed(1),y:(base-hd).toFixed(1),width:bar.toFixed(1),height:hd.toFixed(1),fill:DOWN,rx:2}));
      group.appendChild(svgNode('rect',{x:cx.toFixed(1),y:(base-hu).toFixed(1),width:bar.toFixed(1),height:hu.toFixed(1),fill:UP,rx:2}));
    }else group.appendChild(svgNode('rect',{x:(cx-bar).toFixed(1),y:base-3,width:(2*bar).toFixed(1),height:3,fill:'var(--line)',rx:1}));
    var hit=svgNode('rect',{x:(left+slot*i).toFixed(1),y:base-height,width:slot.toFixed(1),height:height+4,fill:'transparent'});
    hit.addEventListener('mousemove',function(ev){
      var box=wrap.getBoundingClientRect(),x=ev.clientX-box.left,y=ev.clientY-box.top;
      tip.hidden=false;tip.style.left=Math.min(Math.max(8,x+12),Math.max(8,box.width-230))+'px';tip.style.top=Math.max(4,y-52)+'px';
      tip.textContent=d.day+' · '+(d.ok?'↓ '+bytes(d.rx)+' · ↑ '+bytes(d.tx):bi('no valid data','нет достоверных данных'));
      group.setAttribute('class','hv-bar-group hv-bar-hot');
    });
    hit.addEventListener('mouseleave',function(){tip.hidden=true;group.setAttribute('class','hv-bar-group');});
    svg.appendChild(group);svg.appendChild(hit);
    if((i%Math.max(1,Math.ceil(n/7))===0&&(n-1-i)>=Math.ceil(n/7)/2)||i===n-1)svg.appendChild(svgNode('text',{x:cx.toFixed(1),y:240,fill:'var(--muted)','font-size':11,'text-anchor':'middle'},d.day.slice(5)));
  });
  var legend=E('div',{'class':'hv-legend hv-legend-interactive'},[E('span',{'class':'hv-legend-item'},[E('i',{'style':'background:'+DOWN}),bi('Download ↓','Скачивание ↓')]),E('span',{'class':'hv-legend-item'},[E('i',{'style':'background:'+UP}),bi('Upload ↑','Отдача ↑')])]);
  var select=E('select',{'class':'hv-traffic-scope','aria-label':bi('Traffic to show','Какой трафик показать'),'change':function(ev){onScope(ev.target.value);}},[E('option',{value:'vpn'},bi('Through the VPNs','Через VPN')),E('option',{value:'wan'},bi('Through the WAN (provider)','Через WAN (провайдер)'))]);select.value=scope;
  [svg,tip,legend].forEach(function(node){wrap.appendChild(node);});
  return E('div',{},[E('div',{'class':'hv-native-actions'},[select]),wrap,E('small',{},bi('Last '+n+' days, Europe/Berlin. A grey dash means there was no valid data that day (not zero traffic). Point at a day to see the numbers.','Последние '+n+' дней, Europe/Berlin. Серая черта означает, что за этот день нет достоверных данных (это не нулевой трафик). Наведите курсор на день, чтобы увидеть числа.'))]);
}
function trafficHistoryPanel(accounting){
  function dateKey(date){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);}
  var today=dateKey(new Date()),section=E('section',{'class':'hv-chart-card','data-stats-reset':'traffic'},[E('h3',{},bi('Daily WAN and VPN traffic','Суточный трафик WAN и VPN'))]);
  var wan=accounting.wan||{},vpnDays=accounting.days||{},wanDays=wan.days||{},days=Array.from(new Set(Object.keys(vpnDays).concat(Object.keys(wanDays)))).filter(function(day){return day<=today;}).sort().reverse();
  // Chart: the last 30 calendar days up to today, oldest on the left.
  var parts=today.split('-').map(Number),span=[];
  for(var back=29;back>=0;back--)span.push(new Date(Date.UTC(parts[0],parts[1]-1,parts[2]-back)).toISOString().slice(0,10));
  var chartHost=E('div',{});
  function drawChart(){while(chartHost.firstChild)chartHost.removeChild(chartHost.firstChild);chartHost.appendChild(trafficDayChart(vpnDays,wanDays,span,trafficScope,function(value){trafficScope=value;drawChart();}));}
  if(days.length){drawChart();section.appendChild(chartHost);}
  var table=E('table',{'class':'table'},[E('tr',{},[bi('Date','Дата'),'WAN ↓','WAN ↑','VPN ↓','VPN ↑',bi('Observation gaps','Пропуски измерений')].map(function(title){return E('th',{},title);}))]);
  function value(row,key){return row&&row.observed===true?E('td',{'data-sort-value':Number(row[key]||0)},bytes(Number(row[key]||0))):E('td',{},'—');}
  days.slice(0,90).forEach(function(day){var w=wanDays[day],v=vpnDays[day];table.appendChild(E('tr',{},[E('td',{},day),value(w,'rx'),value(w,'tx'),value(v,'rx'),value(v,'tx'),E('td',{},String((w&&w.gaps||0)+(v&&v.gaps||0)))]));});
  section.appendChild(table);
  if(!days.length)section.appendChild(E('p',{},bi('No daily observations yet. Missing measurements are not zero traffic.','Суточных измерений пока нет. Отсутствие измерений не означает нулевой трафик.')));
  section.appendChild(E('p',{},bi('WAN and VPN counters overlap, so do not add them together. A dash means there was no valid data that day. Up to 90 days are kept.','Счётчики WAN и VPN пересекаются, их нельзя складывать. Прочерк означает, что за этот день нет достоверных данных. Хранится до 90 дней.')));
  if(accounting.rpc_aggregated||accounting.retention&&Object.keys(accounting.retention).length)section.appendChild(E('p',{'class':'alert-message warning'},[bi('Older measurements were aggregated or pruned to limit storage and RPC size. ','Старые измерения объединены или удалены, чтобы ограничить объём хранилища. '),errorCodeLink('HISTORY-PARTIAL')]));
  return section;
}

/* Live log: the same lines as before, now alive: a pulsing LIVE dot, a seconds counter, a bar that fills until the next check
   and a small blinking lamp on every line (green = works, yellow = checking, red = failure, grey = not connected). */
var liveLogTimer=null;
function liveLampKind(profile,now){var s=profileHealth(profile,now).state;return s==='healthy'?'green':s==='checking'?'yellow':s==='failed'?'red':'grey';}
function renderLiveLog(status,rows,ns,inventory,stateNames){stateNames=stateNames||{};
  if(typeof renderLiveTerminal==='function')return renderLiveTerminal(status,inventory);
  var now=(typeof routerWall==='function'?routerWall():Date.now()/1000),interval=Number(((inventory||{}).settings||{}).interval)||10;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var light=autoLightModel(status,inventory||{},now);
  function lamp(kind,title){return E('span',{'class':'hv-live-lamp hv-live-lamp-'+kind,'role':'img','aria-label':title,'title':title});}
  function time(t,fallback){return E('span',{'class':'hv-log-time'},t?new Date(t*1000).toLocaleTimeString():fallback);}
  var counter=E('span',{'class':'hv-live-age'}),bar=E('span',{'class':'hv-live-bar-fill'}),next=E('span',{'class':'hv-live-next'});
  var head=E('div',{'class':'hv-live-head'},[E('span',{'class':'hv-live-dot hv-live-dot-'+(fresh?'on':'off'),'aria-hidden':'true'}),E('strong',{},fresh?bi('LIVE','В ЭФИРЕ'):bi('NO DATA','НЕТ ДАННЫХ')),counter,E('span',{'class':'hv-live-bar','aria-hidden':'true'},bar),next]);
  function tick(){
    var t=(typeof routerWall==='function'?routerWall():Date.now()/1000),age=Number.isFinite(status.time)?Math.max(0,t-status.time):null;
    counter.textContent=age==null?'':bi('updated '+Math.round(age)+' s ago','обновлено '+Math.round(age)+' с назад');
    var share=age==null?0:Math.min(1,age/interval);bar.style.width=Math.round(share*100)+'%';
    next.textContent=age==null?'':(age>=interval?bi('check is due…','проверка вот-вот…'):bi('next check in about '+Math.max(1,Math.round(interval-age))+' s','следующая проверка через ~'+Math.max(1,Math.round(interval-age))+' с'));
  }
  tick();if(liveLogTimer)clearInterval(liveLogTimer);liveLogTimer=setInterval(function(){if(!document.body.contains(head)){clearInterval(liveLogTimer);liveLogTimer=null;return;}tick();},1000);
  var monitorKind=fresh?'green':status.rpc_error?'red':'yellow';
  function pill(kind,text){return E('strong',{'class':'hv-badge hv-health-'+kind},text);}
  function row(cls,t,fallback,lampNode,name,status){return E('div',{'class':cls||'notice'},[time(t,fallback),lampNode,E('strong',{'class':'hv-log-name'},name),E('span',{'class':'hv-log-status'},status)]);}
  var monitorKind=fresh?'green':status.rpc_error?'red':'yellow';
  var kindToHealth={green:'healthy',yellow:'checking',red:'failed',grey:'unknown'};
  var autoKind=light.lamp==='orange'?'yellow':(light.lamp||'grey');
  var terminal=E('pre',{'class':'hv-live-terminal'},[
    E('div',{'class':'hv-live-colnames','aria-hidden':'true'},[E('span',{},bi('Time','Время')),E('span',{},''),E('span',{},bi('What','Что')),E('span',{},bi('Status','Статус'))]),
    row('notice',status.time,'—',lamp(monitorKind,fresh?bi('Monitoring works','Мониторинг работает'):bi('No fresh data','Нет свежих данных')),'HomenS.AI monitor',status.error?badge(status.error):pill(kindToHealth[monitorKind],fresh?'OK':bi('No fresh data','Нет свежих данных'))),
    row('notice',ns.time,'—',lamp(autoKind,light.title),'Auto VPN',pill(kindToHealth[autoKind]||'unknown',stateNames[ns.state]||ns.state||'UNKNOWN'))]);
  rows.slice(0,20).forEach(function(p){
    terminal.appendChild(row(p.code?'error':'notice',p.time,'—:—:—',lamp(liveLampKind(p,now),profileHealth(p,now).label),p.protocol+' / '+serverTitle(p),healthBadge(p)));
  });
  return E('div',{'class':'hv-live'},[head,terminal]);
}

/* Every known diagnostic code anywhere on the page becomes a link to its row in the error table (name, meaning, how to fix). */
var errorLinkObserver=null,errorLinkTimer=null;
var ERROR_LINK_SKIP='a,button,script,style,textarea,input,select,option,.hv-errtable,.hv-ai-prompt,.hv-cmd,.hv-errlink';
/* Known codes inside a text, as [{code,index}]. A code is capital letters, digits and hyphens (DNS-001, OFFLINE-FIXTURE, COMMITTED). */
function findErrorCodes(text){
  var pattern=/\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*\b/g,match,found=[];
  while((match=pattern.exec(text))){
    var code=match[0];
    if(code.length<5||!(Object.prototype.hasOwnProperty.call(ERROR_GROUP_OF,code)||(typeof errorFamilyOf==='function'&&errorFamilyOf(code))))continue;
    found.push({code:code,index:match.index});
  }
  return found;
}
function linkifyErrorCodes(root){
  if(!root||typeof ERROR_GROUP_OF==='undefined')return;
  var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),nodes=[],node;
  while((node=walker.nextNode())){
    if(!node.nodeValue||node.nodeValue.length<5)continue;
    var parent=node.parentElement;if(!parent||parent.closest(ERROR_LINK_SKIP))continue;
    if(findErrorCodes(node.nodeValue).length)nodes.push(node);
  }
  if(!nodes.length)return;
  if(errorLinkObserver)errorLinkObserver.disconnect();
  nodes.forEach(function(textNode){
    var text=textNode.nodeValue,last=0,frag=document.createDocumentFragment(),changed=false;
    findErrorCodes(text).forEach(function(hit){
      var code=hit.code;
      if(hit.index>last)frag.appendChild(document.createTextNode(text.slice(last,hit.index)));
      var link=document.createElement('a');link.href='#events';link.className='hv-errlink hv-errlink-inline';link.textContent=code;link.title=bi('Open the description of this code','Открыть описание этого кода');
      (function(c){link.addEventListener('click',function(ev){ev.preventDefault();showErrorCode(c);});})(code);
      frag.appendChild(link);last=hit.index+code.length;changed=true;
    });
    if(!changed)return;
    if(last<text.length)frag.appendChild(document.createTextNode(text.slice(last)));
    textNode.parentNode.replaceChild(frag,textNode);
  });
  if(errorLinkObserver)errorLinkObserver.observe(root,{childList:true,subtree:true});
}
function installErrorLinks(root){
  if(!root||typeof MutationObserver==='undefined')return;
  if(errorLinkObserver)errorLinkObserver.disconnect();
  errorLinkObserver=new MutationObserver(function(){if(errorLinkTimer)clearTimeout(errorLinkTimer);errorLinkTimer=setTimeout(function(){linkifyErrorCodes(root);},120);});
  errorLinkObserver.observe(root,{childList:true,subtree:true});
  linkifyErrorCodes(root);
}

/* Preserve reading position across synchronous redraws and page round trips. */
var pageViewportStates=Object.create(null);
function capturePageViewport(root,page){
  if(!root||!root.isConnected)return null;
  var section=root.querySelector('[data-hv-page="'+page+'"]')||root;
  var saved={page:page,x:window.scrollX||0,y:window.scrollY||window.pageYOffset||0,anchor:null,details:[]};
  var candidates=section.querySelectorAll('#hv-auto-live-chart,#hv-auto-day-chart,[data-error-code]');
  for(var i=0;i<candidates.length;i++){
    var node=candidates[i],rect=node.getBoundingClientRect();
    if(rect.bottom>0&&rect.top<(window.innerHeight||800)){
      saved.anchor={id:node.id||null,code:node.getAttribute('data-error-code'),top:rect.top};break;
    }
  }
  section.querySelectorAll('details').forEach(function(node,index){saved.details.push({index:index,key:typeof node.getAttribute==='function'?node.getAttribute('data-auto-disclosure'):null,open:node.open});});
  return saved;
}
function restorePageViewport(root,saved){
  if(!root||!root.isConnected||!saved||!Number.isFinite(saved.y))return;
  var section=root.querySelector('[data-hv-page="'+saved.page+'"]')||root;
  var details=section.querySelectorAll('details');
  (Array.isArray(saved.details)?saved.details.slice(0,1000):[]).forEach(function(item){
    if(!item)return;var node=null;
    if(typeof item.key==='string'&&/^[a-z][a-z0-9-]{0,63}$/.test(item.key))node=section.querySelector('details[data-auto-disclosure="'+item.key+'"]');
    else if(Number.isSafeInteger(item.index)&&item.index>=0)node=details[item.index];
    if(node)node.open=item.open===true;
  });
  var top=saved.y,anchor=saved.anchor,node=null;
  if(anchor&&Number.isFinite(anchor.top)){
    if(anchor.id==='hv-auto-live-chart'||anchor.id==='hv-auto-day-chart')node=section.querySelector('#'+anchor.id);
    else if(typeof anchor.code==='string'&&/^[A-Z0-9*-]{1,96}$/.test(anchor.code))node=section.querySelector('[data-error-code="'+anchor.code+'"]');
    if(node)top=(window.scrollY||window.pageYOffset||0)+node.getBoundingClientRect().top-anchor.top;
  }
  window.scrollTo({left:Number.isFinite(saved.x)?saved.x:0,top:Math.max(0,top),behavior:'instant'});
}
function rememberPageViewport(root,page){var saved=capturePageViewport(root,page);if(saved)pageViewportStates[page]=saved;return saved;}
function revisitPageViewport(root,page){restorePageViewport(root,pageViewportStates[page]||{page:page,x:0,y:0,details:[]});}
/* Focusable things a refresh may rebuild; restored by tag, aria-label and text. Text fields are not rebuilt under focus. */
var PAGE_FOCUS_SELECTOR='button,a[href],summary,input[type=checkbox],input[type=radio],input[type=range],select';
function restorePageControlFocus(pages,saved){
  if(!saved||!pages[saved.page])return;
  var page=pages[saved.page],node=saved.node;
  // Cached Help/training nodes are moved, not rebuilt. Restore the exact control,
  // rather than the first checkbox with the same empty text/aria-label.
  if(!node||!page.contains(node))node=Array.from(page.querySelectorAll(PAGE_FOCUS_SELECTOR)).find(function(el){return el.tagName===saved.tag&&el.getAttribute('aria-label')===saved.label&&el.textContent===saved.text;});
  if(node)node.focus({preventScroll:true});
}
function installViewportPersistence(root,getPage){
  window.addEventListener('pagehide',function(){
    try{rememberPageViewport(root,getPage());sessionStorage.setItem('homensai-vpn-viewports',JSON.stringify({path:window.location.pathname,time:Date.now(),pages:pageViewportStates}));}catch(error){}
  });
  try{
    var navigation=performance.getEntriesByType('navigation')[0];
    if(!navigation||['reload','back_forward'].indexOf(navigation.type)<0)return;
    var old=JSON.parse(sessionStorage.getItem('homensai-vpn-viewports')||'null');
    if(!old||old.path!==window.location.pathname||Date.now()-old.time>86400000)return;
    Object.keys(old.pages||{}).slice(0,20).forEach(function(key){
      var value=old.pages[key];
      if(/^[a-z]+$/.test(key)&&value&&value.page===key&&Number.isFinite(value.y)&&value.y>=0&&value.y<10000000)pageViewportStates[key]=value;
    });
    requestAnimationFrame(function(){revisitPageViewport(root,getPage());});
  }catch(error){}
}

// An explicit shortcut entry starts at the card top; polling preserves reading position.
function resetPageViewport(root,page){
  pageViewportStates[page]={page:page,x:0,y:0,details:[]};
  revisitPageViewport(root,page);
}

var JOURNAL_TYPES={
  "OK": {
    "code": "EVENT-CHECK-OK",
    "label": [
      "Check passed",
      "Проверка прошла"
    ],
    "message": [
      "Channel availability threshold was met",
      "Условие доступности канала выполнено"
    ],
    "meaning": [
      "The monitor received a result without a diagnostic error. This records channel availability at that observation; it does not mean traffic switched or that Auto was activated.",
      "Монитор получил результат без диагностической ошибки. Это наблюдение доступности канала в тот момент; оно не означает переключение трафика или включение Auto."
    ],
    "level": "ok"
  },
  "FAILURE": {
    "code": "EVENT-CHECK-FAILED",
    "label": [
      "Check failed",
      "Ошибка проверки"
    ],
    "message": [
      "Connection check failed",
      "Ошибка проверки соединения"
    ],
    "meaning": [
      "A failed channel check was recorded. Open the saved diagnostic code for the observed failure. It does not by itself prove a route switch.",
      "Зафиксирована неудачная проверка канала. Причину наблюдаемого отказа смотрите в сохранённом диагностическом коде. Сама запись не доказывает смену маршрута."
    ],
    "level": "error"
  },
  "RECOVERY": {
    "code": "EVENT-CONNECTION-RECOVERED",
    "label": [
      "Availability restored",
      "Доступность восстановлена"
    ],
    "message": [
      "Connection availability recovered",
      "Доступность соединения восстановлена"
    ],
    "meaning": [
      "A previously failed channel became available again in observations. This is recovery of availability, not proof that it became the traffic route.",
      "Ранее отказавший канал снова стал доступен по наблюдениям. Это восстановление доступности, а не доказательство, что через него уже идёт трафик."
    ],
    "level": "ok"
  },
  "DISABLED": {
    "code": "EVENT-PROFILE-DISABLED",
    "label": [
      "Profile disabled",
      "Профиль отключён"
    ],
    "message": [
      "VPN profile was disabled",
      "VPN-профиль отключён"
    ],
    "meaning": [
      "The profile is administratively disabled or inactive. This is distinct from a failed Internet check.",
      "Профиль административно отключён или неактивен. Это отличается от ошибки проверки Интернета."
    ],
    "level": "warning"
  },
  "GAP": {
    "code": "EVENT-OBSERVATION-GAP",
    "label": [
      "No observation interval",
      "Перерыв наблюдений"
    ],
    "message": [
      "A gap in observations was recorded",
      "Зафиксирован перерыв наблюдений"
    ],
    "meaning": [
      "There were no trusted measurements for an interval. Neither successful connectivity nor failure is invented for the missing period.",
      "За интервал нет достоверных измерений. Пропуск не превращается ни в исправность, ни в выдуманный отказ."
    ],
    "level": "warning"
  },
  "OBSERVING": {
    "code": "EVENT-MONITORING",
    "label": [
      "Observing channels",
      "Наблюдение за каналами"
    ],
    "message": [
      "The controller is observing the VPN channels",
      "Контроллер наблюдает за VPN-каналами"
    ],
    "meaning": [
      "The controller is checking the channels. This state alone does not describe a newly completed traffic switch; channel selection has separate confirmation.",
      "Контроллер проверяет каналы. Само это состояние не означает только что выполненное переключение трафика; выбор маршрута подтверждается отдельно."
    ],
    "level": "ok"
  },
  "STARTING": {
    "code": "EVENT-AUTO-STARTING",
    "label": [
      "Auto starting",
      "Запуск Auto"
    ],
    "message": [
      "Auto startup is in progress",
      "Выполняется запуск Auto"
    ],
    "meaning": [
      "Startup was accepted and is still being prepared. Wait for its actual completion or a specific refusal; a request is not a running session.",
      "Запуск принят и ещё подготавливается. Дождитесь фактического завершения или конкретного отказа; запрос не равен работающему сеансу."
    ],
    "level": "warning"
  },
  "ARMED": {
    "code": "EVENT-CHANNEL-PREPARATION",
    "label": [
      "Preparing channels",
      "Подготовка каналов"
    ],
    "message": [
      "Channel prerequisites are being prepared and checked",
      "Подготавливаются и проверяются условия работы каналов"
    ],
    "meaning": [
      "A preparation stage was recorded. Connectivity and routing may still be checked; this is not a completed switch.",
      "Зафиксирован подготовительный этап. Связность и маршрут ещё могут проверяться; это не завершённое переключение."
    ],
    "level": "warning"
  },
  "APPLYING": {
    "code": "EVENT-ROUTE-APPLYING",
    "label": [
      "Selecting route",
      "Выбор маршрута"
    ],
    "message": [
      "A route-selection command is being applied",
      "Выполняется команда выбора маршрута"
    ],
    "meaning": [
      "The operation is applying the planned traffic selection. Its final outcome must be confirmed by a later event.",
      "Операция применяет запланированный выбор трафика. Итог должен быть подтверждён следующим событием."
    ],
    "level": "warning"
  },
  "WAIT-CLIENT": {
    "code": "EVENT-PATH-CONFIRMATION",
    "label": [
      "Verifying path",
      "Подтверждение пути"
    ],
    "message": [
      "The selected path is awaiting verification",
      "Ожидается подтверждение выбранного пути"
    ],
    "meaning": [
      "The change is not yet accepted as a confirmed route. The required evidence depends on the recorded operating mode: router observations or a separate client witness.",
      "Изменение ещё не принято как подтверждённый маршрут. Требуемое доказательство зависит от сохранённого режима: наблюдения роутера либо отдельный клиентский тест."
    ],
    "level": "warning"
  },
  "COMMITTED": {
    "code": "EVENT-RESERVE-SELECTED",
    "label": [
      "Reserve selected",
      "Резерв выбран"
    ],
    "message": [
      "Reserve traffic selection was confirmed",
      "Выбор резервного маршрута подтверждён"
    ],
    "meaning": [
      "The recorded operation confirmed reserve selection. This does not imply that the primary is broken; its health is a separate observation.",
      "Операция подтвердила выбор резерва. Это не означает неисправность основного: его состояние проверяется отдельно."
    ],
    "level": "ok"
  },
  "STOPPED-ON-RESERVE": {
    "code": "EVENT-RESERVE-HELD",
    "label": [
      "Reserve retained",
      "Резерв удержан"
    ],
    "message": [
      "The operation ended while retaining the reserve",
      "Операция завершилась с сохранением резерва"
    ],
    "meaning": [
      "The operation retained reserve routing. In a continuous session Auto may remain on; this transaction state is not proof of a global Auto shutdown.",
      "Операция сохранила резервный маршрут. В непрерывном сеансе Auto может продолжать работать; это состояние транзакции не доказывает глобальное выключение Auto."
    ],
    "level": "ok"
  },
  "RESTORING": {
    "code": "EVENT-RETURN-IN-PROGRESS",
    "label": [
      "Returning route",
      "Возврат маршрута"
    ],
    "message": [
      "The original route is being restored",
      "Восстанавливается исходный маршрут"
    ],
    "meaning": [
      "Restoration is in progress. A later verified outcome is required before describing the original route as restored.",
      "Восстановление выполняется. Прежде чем считать исходный маршрут восстановленным, требуется последующее подтверждение."
    ],
    "level": "warning"
  },
  "ROLLED-BACK": {
    "code": "EVENT-ROLLBACK-RECORDED",
    "label": [
      "Rollback recorded",
      "Записан откат"
    ],
    "message": [
      "A rollback stage was recorded",
      "Зафиксирован этап отката"
    ],
    "meaning": [
      "This old record names a rollback. If it lacks an original_restored confirmation, successful restoration must not be invented.",
      "Старая запись содержит этап отката. Если подтверждение original_restored в ней отсутствует, успешное восстановление не приписывается."
    ],
    "level": "warning"
  },
  "RETURNED": {
    "code": "EVENT-ORIGINAL-RESTORED",
    "label": [
      "Original route restored",
      "Исходный маршрут восстановлен"
    ],
    "message": [
      "Restoration of the original route was confirmed",
      "Восстановление исходного маршрута подтверждено"
    ],
    "meaning": [
      "The event includes explicit verified restoration evidence. This is separate from a request to return or a restoration-in-progress stage.",
      "В событии есть явное подтверждение восстановления. Это отличается от запроса возврата или незавершённого восстановления."
    ],
    "level": "ok"
  },
  "STOPPED": {
    "code": "EVENT-OPERATION-STOPPED",
    "label": [
      "Operation stopped",
      "Операция остановлена"
    ],
    "message": [
      "The controller operation was stopped",
      "Управляющая операция остановлена"
    ],
    "meaning": [
      "The operation ended. A global Auto state and the resulting route must be read from their own recorded confirmations, not inferred from this word alone.",
      "Операция завершена. Общее состояние Auto и итоговый маршрут определяются по собственным подтверждениям, а не выводятся только из этого слова."
    ],
    "level": "warning"
  },
  "RUNNING": {
    "code": "EVENT-AUTO-RUNNING",
    "label": [
      "Auto running",
      "Auto работает"
    ],
    "message": [
      "The Auto session is running",
      "Сеанс Auto работает"
    ],
    "meaning": [
      "A running controller session was recorded. Each channel still needs fresh connectivity checks; it is not a guarantee of every client path.",
      "Зафиксирован работающий сеанс контроллера. Каналам по-прежнему нужны свежие проверки; это не гарантия каждого клиентского пути."
    ],
    "level": "ok"
  },
  "AUTO-START-REQUESTED": {
    "code": "EVENT-AUTO-START-REQUESTED",
    "label": [
      "Start requested",
      "Запрошен запуск"
    ],
    "message": [
      "Auto activation requested",
      "Запрошено включение Auto"
    ],
    "meaning": [
      "This is the request, including its recorded initiator. Startup is not confirmed until a later completed state.",
      "Это запрос с сохранённым инициатором. Запуск не подтверждён до последующего завершённого состояния."
    ],
    "level": "warning"
  },
  "AUTO-STOP-REQUESTED": {
    "code": "EVENT-AUTO-STOP-REQUESTED",
    "label": [
      "Stop requested",
      "Запрошена остановка"
    ],
    "message": [
      "Auto deactivation requested",
      "Запрошено выключение Auto"
    ],
    "meaning": [
      "This is a stop request, not proof that routing was restored or the controller finished stopping.",
      "Это запрос остановки, а не доказательство восстановления маршрута или завершения остановки контроллера."
    ],
    "level": "warning"
  },
  "BLOCKED": {
    "code": "EVENT-OPERATION-BLOCKED",
    "label": [
      "Action refused",
      "Действие отклонено"
    ],
    "message": [
      "A required prerequisite blocked the action",
      "Действие отклонено из-за невыполненного условия"
    ],
    "meaning": [
      "No success is inferred. Read the saved reason code; do not bypass the gate or treat a queued request as applied routing.",
      "Успех не предполагается. Прочитайте сохранённый код причины; не обходите условие и не считайте очередь выполненным выбором маршрута."
    ],
    "level": "error"
  },
  "FAILED": {
    "code": "EVENT-OPERATION-FAILED",
    "label": [
      "Operation failed",
      "Операция не выполнена"
    ],
    "message": [
      "The operation ended with an error",
      "Операция завершилась ошибкой"
    ],
    "meaning": [
      "Read the specific recorded reason and recovery outcome. Failed application or rollback is not reported as successful switching.",
      "Прочитайте конкретную сохранённую причину и итог восстановления. Неудачное применение или откат не выдаётся за успешное переключение."
    ],
    "level": "error"
  },
  "EXPIRED": {
    "code": "EVENT-WINDOW-EXPIRED",
    "label": [
      "Test window ended",
      "Окно теста завершено"
    ],
    "message": [
      "The bounded operation window expired",
      "Закончилось ограниченное окно операции"
    ],
    "meaning": [
      "A configured time boundary ended. The final routing/recovery outcome is a separate confirmation.",
      "Истёк заданный предел времени. Итог маршрутизации или восстановления подтверждается отдельно."
    ],
    "level": "warning"
  },
  "RELEASE-PENDING": {
    "code": "EVENT-RECOVERY-PENDING",
    "label": [
      "Recovery pending",
      "Восстановление ожидается"
    ],
    "message": [
      "Traffic-block release is awaiting confirmation",
      "Ожидается подтверждение снятия блокировки"
    ],
    "meaning": [
      "Recovery has not yet been verified complete. Read the saved recovery code; an attempted cleanup is not the final result.",
      "Завершение восстановления ещё не проверено. Смотрите сохранённый код; попытка очистки не равна итоговому результату."
    ],
    "level": "warning"
  },
  "DEGRADED-ON-RESERVE": {
    "code": "EVENT-RESERVE-DEGRADED",
    "label": [
      "Reserve check failed",
      "Проблема на резерве"
    ],
    "message": [
      "The selected reserve also has a connectivity problem",
      "На выбранном резерве тоже выявлена проблема связи"
    ],
    "meaning": [
      "A problem was observed on the reserve. Returning to primary still requires current evidence and the applicable policy.",
      "На резерве наблюдается проблема. Возврат на основной по-прежнему требует актуальных доказательств и применимой политики."
    ],
    "level": "error"
  },
  "TRIAL-REQUIRED": {
    "code": "EVENT-TRIAL-PREREQUISITE",
    "label": [
      "Mode prerequisite missing",
      "Не выполнено условие режима"
    ],
    "message": [
      "The chosen mode needs an additional prerequisite",
      "Для выбранного режима нужно дополнительное условие"
    ],
    "meaning": [
      "The saved reason describes the mode-specific prerequisite. A legacy LAN trial refusal does not imply every prepared router-probed session needs a client certificate.",
      "Сохранённая причина описывает условие конкретного режима. Отказ прежнего LAN-теста не означает, что любой подготовленный router-probed сеанс требует клиентский сертификат."
    ],
    "level": "warning"
  },
  "LEGACY": {
    "code": "EVENT-DETAILS-NOT-SAVED",
    "label": [
      "Record lacks detail",
      "Подробности не сохранены"
    ],
    "message": [
      "An older record did not retain a full event description",
      "В старой записи не сохранено полное описание события"
    ],
    "meaning": [
      "Only the saved fields can be explained. A missing initiator, role or final outcome is not replaced with today's route or an invented successful switch.",
      "Объясняются только сохранённые поля. Отсутствующие инициатор, роль или итог не заменяются сегодняшним маршрутом или выдуманным успешным переключением."
    ],
    "level": "warning"
  }
};
JOURNAL_TYPES.CONFLICT={code:'EVENT-RECORD-CONFLICT',label:['Record data conflict','Ошибка данных записи'],message:['The saved event contains conflicting results','В сохранённом событии противоречивые результаты'],meaning:['Success and failure were both recorded. Do not treat this as a successful channel or confirmed switch; inspect the saved diagnostic data.','Одновременно записаны успех и ошибка. Это не считается успешной проверкой или подтверждённым переходом; проверьте сохранённые диагностические данные.'],level:'error'};
Object.assign(JOURNAL_TYPES,{"CANCELLED": {"code": "EVENT-COMMAND-CANCELLED", "label": ["Command cancelled", "Команда отменена"], "message": ["The requested operation was cancelled", "Запрошенная операция отменена"], "meaning": ["Cancellation was recorded. The resulting route or cleanup still requires its own confirmation.", "Зафиксирована отмена. Итоговый маршрут или завершение очистки подтверждаются отдельно."], "level": "warning"}, "CLAIMED": {"code": "EVENT-COMMAND-ACCEPTED", "label": ["Command accepted", "Команда принята"], "message": ["The controller accepted the command for processing", "Контроллер принял команду в обработку"], "meaning": ["The worker accepted this command. It has not yet proved that the routing action completed.", "Исполнитель принял команду. Это ещё не доказывает завершение действия с маршрутом."], "level": "warning"}, "QUEUED": {"code": "EVENT-COMMAND-QUEUED", "label": ["Command queued", "Команда в очереди"], "message": ["The command is waiting in the queue", "Команда ожидает выполнения в очереди"], "meaning": ["Queue acceptance is separate from execution and verified completion.", "Принятие в очередь отличается от выполнения и подтверждённого завершения."], "level": "warning"}, "IDLE": {"code": "EVENT-CONTROLLER-IDLE", "label": ["Waiting for a command", "Ожидание команды"], "message": ["The operation handler is idle", "Исполнитель операций ожидает команду"], "meaning": ["This handler has no active operation. It does not alone prove that global Auto is off or either channel is unhealthy.", "У этого исполнителя нет активной операции. Это само по себе не доказывает выключение общего Auto или неисправность канала."], "level": "ok"}, "UNCONFIRMED": {"code": "EVENT-RESULT-NEEDS-VERIFICATION", "label": ["Verify the result", "Нужна проверка результата"], "message": ["The operation result has not been verified", "Фактический результат операции ещё не проверен"], "meaning": ["The saved data does not confirm actual completion. Inspect current state before repeating the action; do not invent successful routing.", "Сохранённые данные не подтверждают фактическое выполнение. Перед повтором сверьте текущее состояние; успешная маршрутизация не предполагается."], "level": "warning"}});
JOURNAL_TYPES["HELD-ON-RESERVE"]=JOURNAL_TYPES["STOPPED-ON-RESERVE"];
JOURNAL_TYPES.CHANNEL_SELECTION={code:'EVENT-CHANNEL-SELECTION',label:['Channel selection record','Запись выбора канала'],message:['The router recorded a channel selection operation','Роутер сохранил операцию выбора канала'],meaning:['The saved direction and completion describe this operation. A controller phase alone does not prove the selected route or independent LAN availability.','Сохранённые направление и завершение описывают эту операцию. Сам этап контроллера не доказывает выбранный маршрут или доступность независимого клиента LAN.'],level:'warning'};
JOURNAL_TYPES.POLICY_REAPPLY={code:'EVENT-POLICY-REAPPLY',label:['VPN rules applied again','Повторное применение правил VPN'],message:['The router applied VPN rules without changing channel order','Роутер повторно применил правила VPN без изменения порядка каналов'],meaning:['This is a rule application, not a channel switch or an internet availability result. Completion and the saved policy reason are separate facts.','Это применение правил, а не переключение канала или результат проверки интернета. Завершение и сохранённая причина проверки правил указываются отдельно.'],level:'warning'};
JOURNAL_TYPES.ROUTER_OBSERVATION={code:'EVENT-ROUTER-OBSERVATION',label:['Router state observation','Наблюдение состояния роутера'],message:['Router control state was recorded; no channel switch is claimed','Сохранено состояние управления роутера; переключение канала не заявлено'],meaning:['This observation did not record a channel-order change. Use the saved event-time selection evidence rather than interpreting the controller phase as a new switch.','В этом наблюдении смена порядка каналов не записана. Используйте сохранённое подтверждение выбора на момент события; этап контроллера не считается новым переключением.'],level:'ok'};
JOURNAL_TYPES.DIRECTION_NOT_SAVED={code:'EVENT-DIRECTION-NOT-SAVED',label:['Switch direction not recorded','Направление перехода не сохранено'],message:['The saved data does not establish the direction of this operation','Сохранённые данные не подтверждают направление этой операции'],meaning:['The event lacks valid explicit source or destination metadata. The current pair and controller phase are not used to invent the missing direction.','В событии нет корректно сохранённых исходного канала или назначения. Текущая пара и этап контроллера не используются для выдумывания направления.'],level:'warning'};
function journalCodeRow(code){
  if(typeof ERROR_ROWS==='undefined'||typeof code!=='string')return null;
  return ERROR_ROWS.find(function(r){return r[0]===code;})||ERROR_ROWS.find(function(r){return r[0].endsWith('*')&&code.indexOf(r[0].slice(0,-1))===0;})||null;
}
JOURNAL_TYPES.STARTING={code:'EVENT-START-CONFIRMATION-PENDING',label:['Start awaiting confirmation','Запуск ожидает подтверждения'],message:['Start accepted; waiting for the controller','Запрос включения принят; ожидается подтверждение контроллера'],meaning:['The Start request is recorded while the previous stopped state is still visible. This is not another Stop command.','Запрос Start сохранён, пока ещё видно прежнее остановленное состояние. Это ожидание запуска, а не новая команда Stop.'],level:'warning'};
JOURNAL_TYPES.VENDOR_WAIT={code:'EVENT-VENDOR-WAIT',label:['Waiting for router operation','Ожидание операции роутера'],message:['Waiting for the stock network operation or lock to clear','Ожидание завершения штатной сетевой операции или снятия её блокировки'],meaning:['A GL.iNet worker or lock was observed. The controller defers switching decisions until it clears; the record alone does not establish a VPN outage. The exact worker may not have been retained.','Обнаружен обработчик или блокировка GL.iNet. Контроллер временно откладывает решения о переключении; сама запись не подтверждает отказ VPN. Конкретный обработчик мог не сохраниться в истории.'],level:'warning'};
function journalDefinition(entry){
  var transition=savedTransition(entry);
  if(transition.present){
    if(transition.outcome==='refused')return Object.assign({},JOURNAL_TYPES.CHANNEL_SELECTION,{level:'warning'});
    if(transition.reapply)return JOURNAL_TYPES.POLICY_REAPPLY;
    if(transition.unchanged)return JOURNAL_TYPES.ROUTER_OBSERVATION;
    if(!transition.to)return JOURNAL_TYPES.DIRECTION_NOT_SAVED;
    return Object.assign({},JOURNAL_TYPES.CHANNEL_SELECTION,{level:transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0?'ok':'warning'});
  }
  if(entry.state==='BLOCKED'&&entry.code==='VENDOR-WORKER-BUSY')return JOURNAL_TYPES.VENDOR_WAIT;
  if((entry.state==='OK'||entry.code==='OK')&&(entry.state==='FAILURE'||entry.kind==='FAILURE'||entry.state==='OK'&&entry.code&&entry.code!=='OK'&&entry.level==='error'))return JOURNAL_TYPES.CONFLICT;
  if(entry.return_primary===true||entry.state==='ROLLED-BACK'&&entry.original_restored===true)return JOURNAL_TYPES.RETURNED;
  if(JOURNAL_TYPES[entry.state])return JOURNAL_TYPES[entry.state];
  if(JOURNAL_TYPES[entry.kind])return JOURNAL_TYPES[entry.kind];
  if(entry.code==='OK')return JOURNAL_TYPES.OK;
  var r=journalCodeRow(entry.code||entry.state);
  return r?{code:r[0],label:[r[2],r[3]],message:[r[2],r[3]],meaning:[r[4]||'Open this code to load its detailed explanation.',r[5]||'Откройте этот код для загрузки подробного объяснения.'],level:entry.level}:JOURNAL_TYPES.LEGACY;
}
function journalStateText(entry){var t=journalDefinition(entry);return bi(t.label[0],t.label[1]);}
function ensureJournalDictionary(){
  if(typeof ERROR_ROWS==='undefined'||typeof ERROR_GROUPS==='undefined'||typeof ERROR_GROUP_OF==='undefined')return;
  if(!ERROR_GROUPS.some(function(g){return g[0]==='journal';}))ERROR_GROUPS.unshift(['journal',['Events and states','События и состояния']]);
  Object.keys(JOURNAL_TYPES).forEach(function(key){var t=JOURNAL_TYPES[key];if(!ERROR_ROWS.some(function(r){return r[0]===t.code;}))ERROR_ROWS.push([t.code,'journal',t.label[0],t.label[1],t.meaning[0],t.meaning[1],t.message[0]+'. Read the separate saved reason code if present; observation and a confirmed route change are different.',t.message[1]+'. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.']);ERROR_GROUP_OF[t.code]='journal';});
  ['OPERATOR-MANUAL','OPERATOR-RETURN'].forEach(function(code){var r=ERROR_ROWS.find(function(r){return r[0]===code;});if(r){r[2]=code==='OPERATOR-MANUAL'?'Manual-channel control command':'Return-control command';r[3]=code==='OPERATOR-MANUAL'?'Команда ручного выбора канала':'Команда возврата маршрута';r[4]='This is the manual-control command family, not proof that a human clicked. The recorded initiator distinguishes operator, automation, test or programmatic access.';r[5]='Это семейство команд ручного управления, а не доказательство нажатия человеком. Сохранённый инициатор различает оператора, автоматику, тест или программный доступ.';}});
}
function journalDescriptionLink(entry,status,stateOnly,extra){
  var t=journalDefinition(entry),code=t.code;
  if(!stateOnly)return E('span',{'class':'hv-journal-description'},journalMessage(entry,status,true)+(extra||''));
  return E('a',{'href':'#events','class':'hv-errlink hv-journal-state','data-journal-description':code,'data-original-state':entry.state,'title':bi('Open the event explanation','Открыть расшифровку события'),'click':function(ev){ev.preventDefault();ensureJournalDictionary();showErrorCode(code);}},(stateOnly?journalStateText(entry):journalMessage(entry,status,true))+(extra||''));
}
/* Shared real-event vocabulary for the live terminal and persisted history. */
var EVENT_VIEW={query:'',sort:'time',desc:true,expanded:false,page:0,stored:null,busy:false,error:null,request:0};
function journalHistoryDays(status){
  var values=[((status.accounting||{}).reliability||{}).detail_days,(status.native_history||{}).detail_days].filter(function(n){return Number.isInteger(n)&&n>=1&&n<=7;});
  return values.length?Math.min.apply(Math,values):7;
}
function renderChannelBadge(model){
  if(!model)return null;
  var main=bi('Main channel','Основной канал'),reserve=bi('Reserve channel','Резервный канал');
  var label=model.phase==='confirmed'?bi('Confirmed transition: ','Подтверждённый переход: '):model.phase==='pending'?bi('Switching in progress: ','Идёт переключение: '):model.phase==='failed'?bi('Connection failed: ','Ошибка соединения: '):bi('Connection recovered: ','Соединение восстановлено: ');
  label+=model.from?(model.from==='source'?main:reserve)+' → '+(model.to==='source'?main:reserve):(model.to==='source'?main:reserve);
  var colors={source:'neutral',target:'neutral'};
  if(model.phase==='pending'){colors.source='pending';colors.target='pending';}
  else if(model.phase==='confirmed'){colors[model.from]='failed';colors[model.to]='working';}
  else colors[model.to]=model.phase==='failed'?'failed':'working';
  function circle(role,letter,title){return E('span',{'class':'hv-channel-dot hv-channel-'+colors[role],'data-channel-role':role,'aria-hidden':'true','title':title},letter);}
  var reverse=model.from==='target',moving=model.phase==='pending';
  return E('span',{'class':'hv-channel-badge'+(moving?' hv-channel-moving':'')+(reverse?' hv-channel-reverse':''),'data-channel-phase':model.phase,'role':'img','aria-label':label,'title':label},[
    circle('source','M',main),E('span',{'class':'hv-channel-arrow','aria-hidden':'true'},model.from?(reverse?'←':'→'):'·'),circle('target','R',reserve)]);
}
function journalChannelModel(entry){
  var transition=savedTransition(entry);
  if(transition.present){
    if(!transition.to||!transition.changed||transition.unchanged||transition.reapply||transition.outcome==='refused')return null;
    if(transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0)return {phase:'confirmed',from:transition.from,to:transition.to};
    if(!transition.completed&&['APPLYING','WAIT-CLIENT','ARMED','RESTORING'].indexOf(entry.state)>=0)return {phase:'pending',from:transition.from,to:transition.to};
    return null;
  }
  var pair=entry.source&&entry.target&&entry.source!==entry.target;
  if(pair&&['APPLYING','WAIT-CLIENT','ARMED'].indexOf(entry.state)>=0)return {phase:'pending',from:'source',to:'target'};
  if(pair&&entry.state==='RESTORING')return {phase:'pending',from:'target',to:'source'};
  if(pair&&(entry.return_primary===true||entry.state==='ROLLED-BACK'&&entry.original_restored===true))return {phase:'confirmed',from:'target',to:'source'};
  if(pair&&['COMMITTED','STOPPED-ON-RESERVE'].indexOf(entry.state)>=0)return {phase:'confirmed',from:'source',to:'target'};
  if(['source','target'].indexOf(entry.role)>=0){
    if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')return {phase:'recovered',to:entry.role};
    if(entry.state==='FAILURE'||entry.kind==='FAILURE'||entry.level==='error')return {phase:'failed',to:entry.role};
  }
  return null;
}
function renderJournalChannelBadge(entry){return renderChannelBadge(journalChannelModel(entry));}
function journalSourceLabel(source){
  return source==='manual'?bi('you, manually','вы, вручную'):source==='automatic'?bi('Auto, automatically','Auto, автоматически'):source==='test'?bi('programmatic test','тестовая программа — автоматически'):source==='programmatic'?bi('program command','команда программы'):bi('source not recorded','источник не указан');
}
function journalToken(value,fallback){return typeof value==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(value)?value.toUpperCase():fallback;}
function journalLatencySample(raw,profile,eventTime){
  if(typeof profile!=='string'||!/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(profile)||!raw||typeof raw!=='object'||raw.profile!==profile||raw.metric!=='https-rtt-ms'||!Number.isFinite(eventTime)||!Number.isFinite(raw.time)||raw.time<eventTime-90||raw.time>eventTime+5||!Number.isFinite(raw.rtt_ms)||raw.rtt_ms<0||raw.rtt_ms>600000||typeof raw.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(raw.interface)||(profile.indexOf('wireguard:')===0)!==(raw.interface.indexOf('wgclient')===0)||typeof raw.generation!=='string'||!/^[a-f0-9]{32}$/.test(raw.generation))return null;
  return {profile:profile,metric:'https-rtt-ms',time:raw.time,rtt_ms:raw.rtt_ms,interface:raw.interface,generation:raw.generation};
}
function journalLatencyText(entry){
  var transition=savedTransition(entry),reverse=['RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0||entry.return_primary===true,profile=transition.present?(transition.changed&&!transition.reapply&&transition.to?entry[transition.to]:null):reverse?entry.source:entry.target;
  var sample=journalLatencySample(entry.latency,profile,entry.time);
  return sample?bi('Delay: ','Задержка: ')+sample.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')+' · '+bi('measured ','замер ')+new Date(sample.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):bi('Delay: no saved measurement at this event','Задержка: нет сохранённого замера на момент события');
}
function journalCurrentLatency(p,status,now){
  if(!p||status.rpc_error||status.error||!Number.isFinite(status.time)||status.time<now-90||status.time>now+5||p.vendor_state!=='SETTLED'||p.vendor_tunnel_id!==p.protocol+':'+p.interface||p.code!=null||p.dns_ok!==true||!Number.isInteger(p.https_success)||p.https_success<2)return null;
  return journalLatencySample({profile:p.id,metric:'https-rtt-ms',time:p.time,rtt_ms:p.rtt_ms,interface:p.interface,generation:p.vendor_generation},p.id,now);
}
function journalMessage(entry,status,hideCode){
  var t=journalDefinition(entry),text=bi(t.message[0],t.message[1]);
  var profiles=Array.isArray(status.profiles)?status.profiles:[],p=profiles.find(function(p){return p.id===entry.profile;});
  if(entry.code==='VPN-003'&&entry.probe)text=entry.probe.https_success>0?bi('HTTPS checks passed partially; some traffic is passing','HTTPS-проверки прошли частично; часть трафика проходит'):bi('HTTPS availability was not confirmed by this check','Эта проверка не подтвердила HTTPS-доступность');
  if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')text=entry.role==='source'?bi('Connection restored on the primary channel','Соединение восстановлено на основном канале'):entry.role==='target'?bi('Connection restored on the reserve channel','Соединение восстановлено на резервном канале'):bi('Connection restored · channel was not saved in this record','Соединение восстановлено · канал не сохранён в этой записи');
  else if(entry.profile)text=(entry.role==='source'?bi('Primary channel','Основной канал'):entry.role==='target'?bi('Reserve channel','Резервный канал'):bi('VPN profile','VPN-профиль'))+' — '+text;
  var transition=savedTransition(entry);
  if(transition.present){
    var names={source:bi('primary','основной'),target:bi('reserve','резервный')},direction=transition.to?(transition.changed&&transition.from?names[transition.from]+' → '+names[transition.to]:names[transition.to]):null;
    if(transition.outcome==='refused')text=bi('Channel selection request was refused','Запрос выбора канала отклонён')+(transition.to?' · '+names[transition.to]:'');
    else if(transition.reapply)text=transition.completed&&transition.outcome==='policy-verified'?bi('VPN rules verified; channel order unchanged','Правила VPN проверены; порядок каналов не изменился'):bi('Applying VPN rules again; no channel switch is claimed','Повторное применение правил VPN; переключение канала не заявлено');
    else if(transition.unchanged)text=bi('Router state observation; no channel switch recorded','Наблюдение состояния роутера; переключение канала не записано');
    else if(!direction)text=bi('Switch direction was not saved; see the recorded reason','Направление перехода не сохранено; смотрите записанную причину');
    else if(transition.completed&&transition.outcome==='restored')text=bi('Return confirmed: ','Возврат подтверждён: ')+direction;
    else if(transition.completed&&transition.outcome==='committed')text=(transition.changed&&transition.from?bi('Switch confirmed: ','Переход подтверждён: '):bi('Channel selected: ','Выбран канал: '))+direction;
    else text=(transition.changed&&transition.from?bi('Switch requested: ','Запрошен переход: '):bi('Channel selection requested: ','Запрошен выбор канала: '))+direction;
  }else{
    if(entry.state==='APPLYING')text=bi('Switch: primary → reserve','Переход: основной → резервный');
    if(entry.state==='RESTORING')text=bi('Switch: reserve → primary','Переход: резервный → основной');
    if(entry.return_primary)text=bi('Returned: reserve → primary','Возврат: резервный → основной');
  }
  var sourced=transition.present&&transition.changed||entry.origin==='control'||entry.action_source||['APPLYING','RESTORING','COMMITTED','ROLLED-BACK','STOPPED'].indexOf(entry.state)>=0;
  var switching=transition.present?transition.changed&&!transition.reapply&&transition.outcome!=='refused':entry.return_primary===true||['APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE','RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0;
  var code=!hideCode&&entry.code&&entry.code!=='OK'&&entry.code!==entry.state?' · '+entry.code:'';
  if(entry.probe){
    text+=' · HTTPS '+entry.probe.https_success+'/3 · '+(entry.probe.dns_ok===true?bi('DNS passed','DNS прошёл'):entry.probe.dns_ok===false?bi('DNS failed','DNS не прошёл'):bi('DNS result unavailable','Результат DNS не сохранён'));
    entry.probe.checks.filter(function(c){return c.result==='http-unsupported';}).forEach(function(c){text+=' · '+bi('Check endpoint incompatible: ','Несовместимый проверочный адрес: ')+c.target+(c.http_status?' (HTTP '+c.http_status+')':'');});
  }
  return text+(entry.profile?' · '+(p?serverTitle(p):entry.profile):'')+(sourced?' · '+journalSourceLabel(entry.action_source):'')+(switching?' · '+journalLatencyText(entry):'')+code;
}
function journalDescriptionContent(entry,status,extra){
  var nodes=[journalDescriptionLink(entry,status,false,extra),' · ',E('a',{'href':'#events','class':'hv-errlink','data-journal-code':journalDefinition(entry).code,'title':bi('Open the event explanation','Открыть расшифровку события'),'click':function(ev){ev.preventDefault();ensureJournalDictionary();showErrorCode(journalDefinition(entry).code);}},journalDefinition(entry).code)];
  if(entry.code&&entry.code!=='OK'&&entry.code!==journalDefinition(entry).code){
    var known=journalCodeRow(entry.code),target=known?known[0]:journalDefinition(entry).code;
    nodes.push(' · ',E('a',{'href':'#events','class':'hv-errlink','data-journal-cause':target,'title':bi('Explain the recorded diagnostic code','Расшифровать сохранённый диагностический код'),'click':function(ev){ev.preventDefault();ensureJournalDictionary();showErrorCode(target);}},entry.code));
  }
  return E('span',{'class':'hv-journal-description-content'},nodes);
}
function journalProbeSnapshot(e,profile,status,code){
  if(!code&&(e.kind==='FAILURE'||e.state==='FAILURE'))return null;
  if(!profile||['VPN-001','VPN-003','DNS-001','OK',null].indexOf(code)<0)return null;
  var expected=code==='OK'?null:code;
  function sameCode(r){return (r.code==='OK'?null:r.code||null)===expected;}
  function count(r){return Number.isInteger(r.https_success)&&r.https_success>=0&&r.https_success<=3;}
  var stamp=Number.isFinite(e.measurement_time)&&e.measurement_time>0&&e.measurement_time<=e.time+5?e.measurement_time:null;
  var row=stamp!==null&&count(e)?e:null;
  if(!row){
    var snapshots=(status.events||[]).filter(function(r){return r.profile===profile&&sameCode(r)&&count(r)&&Number.isFinite(r.measurement_time)&&Math.abs(r.measurement_time-(stamp===null?e.time:stamp))<.001;});
    if(snapshots.length===1){row=snapshots[0];stamp=row.measurement_time;}
  }
  if(!row){
    var samples=(status.samples||[]).filter(function(r){return r.id===profile&&sameCode(r)&&count(r)&&Number.isFinite(r.time)&&(stamp!==null?Math.abs(r.time-stamp)<.001:r.time<=e.time+.001&&e.time-r.time<=10);});
    var exact=samples.filter(function(r){return Math.abs(r.time-e.time)<.001;});if(exact.length===1)samples=exact;
    if(samples.length===1){row=samples[0];stamp=row.time;}
  }
  if(!row)return null;
  var checks=(Array.isArray(row.probe_checks)?row.probe_checks:[]).slice(0,3).filter(function(r){return r&&['one.one.one.one','dns.google','dns.quad9.net'].indexOf(r.target)>=0&&['ok','http-unsupported','http-error','timeout','tls-error','transport-error','invalid-response','unknown'].indexOf(r.result)>=0;}).map(function(r){return {target:r.target,result:r.result,http_status:Number.isInteger(r.http_status)&&r.http_status>=100&&r.http_status<=599?r.http_status:null};});
  return {time:stamp,https_success:row.https_success,dns_ok:typeof row.dns_ok==='boolean'?row.dns_ok:null,checks:checks};
}
function journalRows(status,stored,now){
  var retainedSeconds=journalHistoryDays(status)*86400;
  var groups=[['controller',stored?stored.controller.events:(status.native_history||{}).events||[]],['failures',stored?stored.failures.events:((status.accounting||{}).reliability||{}).events||[]],['monitor',stored?[]:status.events||[]]],result=[],seen=Object.create(null);
  function control(action,stamp,source){
    if(['start','stop'].indexOf(action)<0||!Number.isFinite(stamp)||stamp<=0||stamp<now-retainedSeconds||stamp>now+5)return;
    var key='control:'+action+':'+stamp;if(seen[key])return;seen[key]=true;
    result.push({key:key,time:stamp,state:action==='start'?'AUTO-START-REQUESTED':'AUTO-STOP-REQUESTED',kind:'CONTROL',profile:null,code:null,level:'warning',origin:'control',action_source:['manual','automatic','test','programmatic'].indexOf(source)>=0?source:'unknown'});
  }
  groups.forEach(function(group){if(!Array.isArray(group[1]))return;
    group[1].slice(-10000).forEach(function(e){
      if(!e||!Number.isFinite(e.time)||e.time<now-retainedSeconds||e.time>now+5)return;
      control(e.control_action,e.control_time,e.control_source);
      var state=journalToken(e.state||e.kind||e.code,'OBSERVATION'),code=typeof e.code==='string'&&safeCode(e.code)?e.code:Array.isArray(e.codes)?e.codes.find(safeCode)||null:null;
      var profile=typeof(e.profile||e.id)==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e.profile||e.id)?e.profile||e.id:null;
      if(state==='STOPPED'&&e.control_action==='start'&&Number.isFinite(e.control_time)&&e.control_time<=e.time&&e.time-e.control_time<=30){state='STARTING';if(code==='CLIENT-STOP')code=Array.isArray(e.codes)?e.codes.find(function(c){return c!=='CLIENT-STOP'&&safeCode(c);})||null:null;}
      var probe=journalProbeSnapshot(e,profile,status,code);
      var family=state==='FAILURE'||['VPN-001','VPN-003','DNS-001'].indexOf(code)>=0?'failure':state==='RECOVERY'||code==='OK'?'recovery':null;
      var key=probe&&family?'measurement:'+profile+':'+probe.time+':'+family:group[0]+':'+(Number.isSafeInteger(e.sequence)?e.sequence:[e.time,profile,state,code].join(':'));
      if(seen[key])return;seen[key]=true;
      var failed=/FAIL|REFUS|ERROR|DEGRADED/.test(state)||!!code&&/^(DNS-|VPN-|SYSTEM-|CHECK-)|FAILED|ERROR|REFUSED/.test(code),level=failed?'error':/GAP|UNKNOWN|UNCONFIRMED|UNAVAILABLE|UNVERIFIED|CANCEL|INACTIVE/.test(state+' '+(code||''))?'warning':'ok';
      var pair={};['source','target'].forEach(function(k){pair[k]=typeof e[k]==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e[k])?e[k]:null;});
      var actionSource=['manual','automatic','test','programmatic','unknown'].indexOf(e.transition_source)>=0?e.transition_source:e.manual===true?'unknown':e.trial===true?'test':null;
      if(!actionSource&&Array.isArray(e.codes)){
        if(e.codes.some(function(c){return c==='OPERATOR-MANUAL'||c==='OPERATOR-RETURN';}))actionSource='unknown';
        else if(e.codes.some(function(c){return c==='OPERATOR-TRIAL'||c==='TRIAL-PASSED';}))actionSource='test';
        else if(e.codes.some(function(c){return ['SOURCE-FAILED','PRIMARY-STABLY-RECOVERED','RESERVE-FAILED-PRIMARY-VERIFIED'].indexOf(c)>=0;}))actionSource='automatic';
      }
      if(!actionSource&&state==='STOPPED'&&e.control_action==='stop')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      if(!actionSource&&state==='STARTING'&&e.control_action==='start')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      var returnPrimary=state==='STOPPED'&&Array.isArray(e.codes)&&e.codes.indexOf('OPERATOR-RETURN')>=0;
      var transition=savedTransition(e),delayProfile=transition.present?(transition.changed&&!transition.reapply&&transition.to?pair[transition.to]:null):(returnPrimary||['RESTORING','ROLLED-BACK'].indexOf(state)>=0)?pair.source:pair.target;
      var role=['source','target'].indexOf(e.role)>=0?e.role:null;
      if(!role&&profile&&pair.source&&pair.target&&pair.source!==pair.target)role=profile===pair.source?'source':profile===pair.target?'target':null;
      var record={key:key,time:e.time,state:state,kind:journalToken(e.kind,'OBSERVATION'),code:code,profile:profile,role:role,source:pair.source,target:pair.target,original_restored:e.original_restored===true,return_primary:returnPrimary,latency:journalLatencySample(e.latency,delayProfile,e.time),action_source:actionSource,level:level,origin:group[0],probe:probe};
      if(transition.present){
        record.transition_metadata_present=true;
        ['from_role','destination_role','before_policy_role'].forEach(function(key){if(e[key]==='source'||e[key]==='target')record[key]=e[key];});
        ['from_profile_id','destination_profile_id'].forEach(function(key){if(typeof e[key]==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(e[key]))record[key]=e[key];});
        ['route_changed','transition_completed','activation_reapply'].forEach(function(key){if(typeof e[key]==='boolean')record[key]=e[key];});
        if(['committed','restored','refused','policy-verified'].indexOf(e.transition_outcome)>=0)record.transition_outcome=e.transition_outcome;
        record.return_primary=transition.completed&&transition.outcome==='restored'&&transition.to==='source';
      }
      var definition=journalDefinition(record);if(!(definition.code==='EVENT-DETAILS-NOT-SAVED'&&record.level==='error'))record.level=definition.level||record.level;result.push(record);
    });
  });
  var request=status.auto_control||{};
  if(request.requested==='on'||request.requested==='off')control(request.request_action,request.requested_at,request.request_source);
  return result.sort(function(a,b){return b.time-a.time||a.key.localeCompare(b.key);});
}
function filteredJournalRows(rows,status,query,sort,desc){
  var needle=String(query||'').trim().toLocaleLowerCase();
  return rows.filter(function(row){return !needle||[row.state,journalStateText(row),row.kind,row.code,row.profile,row.origin,journalMessage(row,status),new Date(row.time*1000).toLocaleString()].join(' ').toLocaleLowerCase().includes(needle);}).sort(function(a,b){var compared=sort==='state'?journalStateText(a).localeCompare(journalStateText(b)):a.time-b.time;return (desc?-compared:compared)||b.time-a.time||a.key.localeCompare(b.key);});
}
function renderEventHistory(status){
  EVENT_VIEW.status=status;
  if(EVENT_VIEW.root&&EVENT_VIEW.language===locale){if(!EVENT_VIEW.stored&&!EVENT_VIEW.expanded&&!EVENT_VIEW.query)EVENT_VIEW.draw();return EVENT_VIEW.root;}
  EVENT_VIEW.language=locale;
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,host=E('section',{'class':'hv-chart-card','data-event-history':'1'}),tableHost=E('div'),note=E('p',{'role':'status'});
  var query=E('input',{'type':'search','class':'hv-search','maxlength':'256','aria-label':bi('Search all retained events','Поиск по всем сохранённым событиям'),'placeholder':bi('Search words, state or error code','Поиск по словам, состоянию или коду'),'input':function(ev){EVENT_VIEW.query=ev.target.value.slice(0,256);EVENT_VIEW.page=0;if(!EVENT_VIEW.stored)load();draw();}});query.value=EVENT_VIEW.query;
  var order=E('select',{'aria-label':bi('Sort event history','Сортировка истории'),'change':function(ev){EVENT_VIEW.sort=ev.target.value==='state'?'state':'time';EVENT_VIEW.page=0;draw();}},[E('option',{value:'time'},bi('Date and time','Дата и время')),E('option',{value:'state'},bi('State','Состояние'))]);order.value=EVENT_VIEW.sort;
  var direction=E('button',{'type':'button','class':'cbi-button','click':function(){EVENT_VIEW.desc=!EVENT_VIEW.desc;draw();}});
  var more=E('button',{'type':'button','class':'cbi-button','aria-expanded':EVENT_VIEW.expanded?'true':'false','click':function(){EVENT_VIEW.expanded=!EVENT_VIEW.expanded;EVENT_VIEW.page=0;if(EVENT_VIEW.expanded&&!EVENT_VIEW.stored)load();draw();}});
  async function load(){
    if(EVENT_VIEW.busy)return;EVENT_VIEW.busy=true;EVENT_VIEW.error=null;var request=++EVENT_VIEW.request;draw();
    try{
      var call=rpc.declare({object:'homensai-vpn',method:'statistics',params:['kind','after','until'],expect:{}});
      var records=await Promise.all([fetchStoredStatistics('controller',call),fetchStoredStatistics('failures',call)]);
      if(request===EVENT_VIEW.request)EVENT_VIEW.stored={controller:records[0],failures:records[1]};
    }catch(error){if(request===EVENT_VIEW.request)EVENT_VIEW.error='STATISTICS-READ-FAILED';}
    finally{if(request===EVENT_VIEW.request){EVENT_VIEW.busy=false;draw();}}
  }
  function draw(){
    var status=EVENT_VIEW.status,now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
    while(tableHost.firstChild)tableHost.removeChild(tableHost.firstChild);
    var rows=filteredJournalRows(journalRows(status,EVENT_VIEW.stored,now),status,EVENT_VIEW.query,EVENT_VIEW.sort,EVENT_VIEW.desc),size=EVENT_VIEW.expanded?500:20;
    EVENT_VIEW.page=Math.max(0,Math.min(EVENT_VIEW.page,Math.max(0,Math.ceil(rows.length/size)-1)));
    var selected=rows.slice(EVENT_VIEW.page*size,(EVENT_VIEW.page+1)*size),table=E('table',{'class':'table hv-event-history','data-hv-no-sort':'1'},[
      E('thead',{},E('tr',{},[bi('Date and time','Дата и время'),bi('State','Состояние'),bi('Event','Событие')].map(function(label){return E('th',{},label);}))),
      E('tbody',{},selected.map(function(row){return E('tr',{'data-event-key':row.key},[E('td',{},new Date(row.time*1000).toLocaleString()),E('td',{},[renderJournalChannelBadge(row),journalDescriptionLink(row,status,true)].filter(Boolean)),E('td',{},journalDescriptionContent(row,status))]);}))]);
    tableHost.appendChild(E('div',{'class':'hv-dv-tablewrap'},table));
    if(EVENT_VIEW.expanded&&rows.length>size){
      tableHost.appendChild(E('div',{'class':'hv-native-actions'},[
        E('button',{'type':'button','class':'cbi-button','disabled':EVENT_VIEW.page===0?'':null,'click':function(){EVENT_VIEW.page--;draw();}},bi('Previous','Назад')),
        E('span',{},String(EVENT_VIEW.page+1)+' / '+Math.ceil(rows.length/size)),
        E('button',{'type':'button','class':'cbi-button','disabled':(EVENT_VIEW.page+1)*size>=rows.length?'':null,'click':function(){EVENT_VIEW.page++;draw();}},bi('Next','Далее'))]));
    }
    direction.textContent=EVENT_VIEW.desc?bi('Descending ↓','По убыванию ↓'):bi('Ascending ↑','По возрастанию ↑');
    more.textContent=(EVENT_VIEW.expanded?'▾ ':'▸ ')+(EVENT_VIEW.expanded?bi('Show 20 rows','Свернуть до 20 строк'):bi('More history','Остальная история'))+' · '+rows.length;more.setAttribute('aria-expanded',EVENT_VIEW.expanded?'true':'false');
    more.disabled=EVENT_VIEW.busy;
    note.textContent=EVENT_VIEW.busy?bi('Reading saved history…','Чтение сохранённой истории…'):EVENT_VIEW.error||(!EVENT_VIEW.stored?bi('Showing recent events. Press "More history" to see all.','Показаны последние события. Чтобы увидеть все, нажмите «Остальная история».'):bi('Search and sorting cover the full downloaded retained snapshot. Storage/count limits and unobserved gaps remain explicit.','Поиск и сортировка охватывают весь загруженный снимок за выбранный срок. Ограничения хранения и пропуски сохраняются.'));
    if(EVENT_VIEW.stored){
      var records=[EVENT_VIEW.stored.controller,EVENT_VIEW.stored.failures],limited=records.some(function(r){var s=r.summary||{};return r.storage_notice||s.details_dropped>0||s.detail_budget_dropped>0||s.weekly_detail_complete===false;});
      if(limited)note.textContent+=' '+bi('Some saved details are unavailable or were dropped by the storage limit. This is not a complete record of every event.','Часть сохранённых подробностей недоступна или удалена по лимиту хранилища. Это не полный список всех произошедших событий.');
    }
  }
  host.appendChild(E('h3',{},bi('Events and errors: saved history','События и ошибки: сохранённая история')));host.appendChild(E('div',{'class':'hv-native-actions'},[query,order,direction]));host.appendChild(note);host.appendChild(tableHost);host.appendChild(more);
  host.appendChild(E('small',{},bi('The live terminal shows these real observations as they arrive. Its one-second screen heartbeat is not a persisted router event. Detailed controller/failure records are retained for the configured 1–7 days within bounded stores.','Живой терминал показывает эти реальные наблюдения по мере получения. Секундный heartbeat экрана не является сохранённым событием роутера. Подробности контроллера/сбоев хранятся выбранные 1–7 дней в ограниченных журналах.')));EVENT_VIEW.root=host;EVENT_VIEW.draw=draw;draw();return host;
}

/* One-second pinned clock; scrollback contains real event runs, never timer spam. */
var LIVE_TERMINAL={root:null,pinned:null,body:null,clock:null,followButton:null,frame:null,inventory:null,entries:[],seen:new Set(),following:true,scrollTop:0,anchor:null,restorePending:false,timer:null,language:null};
function terminalLimit(){var n=((LIVE_TERMINAL.inventory||{}).settings||{}).live_log_limit;return Number.isInteger(n)&&n>=1&&n<=2000?n:2000;}
function terminalTime(stamp){return new Date(stamp*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});}
function terminalLine(entry,status){
  var node=E('div',{'class':'hv-terminal-line hv-terminal-'+(entry.level||'info'),'data-log-key':entry.key},[E('time'),E('span')]);
  terminalUpdateLine(node,entry,status);return node;
}
function terminalUpdateLine(node,entry,status){
  var first=Number.isFinite(entry.firstTime)?entry.firstTime:entry.time,count=entry.count||1;
  node.children[0].setAttribute('datetime',new Date(first*1000).toISOString());
  node.children[0].textContent=terminalTime(first)+(first===entry.time?'':' — '+terminalTime(entry.time));
  var content=node.children[1];content.textContent='';
  var badge=renderJournalChannelBadge(entry);if(badge)content.appendChild(badge);
  content.appendChild(journalDescriptionContent(entry,status,count>1?' · '+bi('repeated ','повторено ')+count+' '+bi('times','раз'):''));
  node.setAttribute('data-repeat-count',String(count));
}
function terminalSignature(entry){
  return JSON.stringify([entry.origin||'',entry.profile||'',entry.role||'',entry.state||'',entry.kind||'',entry.code||'',entry.level||'',entry.source||'',entry.target||'',entry.original_restored===true,entry.return_primary===true,entry.action_source||'']);
}
function terminalGroups(entries){
  var groups=[];
  entries.forEach(function(entry){
    if(entry.heartbeat)return;
    var signature=terminalSignature(entry),last=groups[groups.length-1];
    if(last&&last.signature===signature){last.firstTime=entry.time;last.count++;last.key=entry.key;}
    else groups.push(Object.assign({},entry,{firstTime:entry.time,count:1,signature:signature}));
  });return groups;
}
function terminalRenderRuns(){
  var state=LIVE_TERMINAL,body=state.body,groups=terminalGroups(state.entries),existing=new Map(),keep=new Set();
  Array.from(body.children).forEach(function(node){existing.set(node.getAttribute('data-log-key'),node);});
  groups.forEach(function(entry,index){
    var node=existing.get(entry.key);
    if(node)terminalUpdateLine(node,entry,state.frame);else node=terminalLine(entry,state.frame);
    keep.add(node);if(body.children[index]!==node)body.insertBefore(node,body.children[index]||null);
  });
  Array.from(body.children).forEach(function(node){if(!keep.has(node))body.removeChild(node);});
}
function terminalLaidOut(body){return body&&body.isConnected!==false&&body.clientHeight>0;}
function terminalAnchor(body){
  var top=body.scrollTop||0,measured=typeof body.getBoundingClientRect==='function',bodyTop=measured?body.getBoundingClientRect().top:0,y=0,result=null;
  Array.from(body.children).some(function(node){
    var height=node.offsetHeight||0,start=measured?node.getBoundingClientRect().top-bodyTop+top:y;y+=height;
    if(start+height>top){result={key:node.getAttribute('data-log-key'),offset:top-start};return true;}return false;
  });return result;
}
function terminalRestoreView(){
  var state=LIVE_TERMINAL,body=state.body;if(!terminalLaidOut(body))return;
  var node=state.anchor&&Array.from(body.children).find(function(n){return n.getAttribute('data-log-key')===state.anchor.key;}),top=state.scrollTop;
  if(state.following)top=0;
  else if(node){
    var start=0;if(typeof body.getBoundingClientRect==='function')start=node.getBoundingClientRect().top-body.getBoundingClientRect().top+body.scrollTop;
    else Array.from(body.children).some(function(n){if(n===node)return true;start+=n.offsetHeight||0;return false;});
    top=start+state.anchor.offset;
  }
  body.scrollTop=Math.max(0,top);state.scrollTop=body.scrollTop;state.restorePending=false;
  state.anchor=state.following?null:terminalAnchor(body);
}
function terminalAppend(entry,deferRender){
  var state=LIVE_TERMINAL,body=state.body;if(!body||entry.heartbeat)return;
  if(!deferRender){
    if(state.restorePending)terminalRestoreView();
    if(!state.following&&terminalLaidOut(body)){state.anchor=terminalAnchor(body);state.scrollTop=body.scrollTop;}
  }
  // Merge by observation time; late history stays below fresher observations.
  var index=0;while(index<state.entries.length&&state.entries[index].time>entry.time)index++;
  if(index>=terminalLimit())return;
  state.entries.splice(index,0,entry);
  while(state.entries.length>terminalLimit())state.entries.pop();
  // Retain bounded raw observations so a late intervening event can split a run
  // accurately. Reuse keyed nodes and the existing reading anchor after grouping.
  if(deferRender)return true;
  terminalRenderRuns();
  // Polling temporarily detaches the whole panel. Preserve the keyed reading
  // anchor until layout returns instead of reading a detached scrollTop of 0.
  state.restorePending=true;terminalRestoreView();return true;
}
function terminalPinned(now){
  var state=LIVE_TERMINAL,status=state.frame||{},inventory=state.inventory||{},rows=status.profiles||[],fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  while(state.pinned.firstChild)state.pinned.removeChild(state.pinned.firstChild);
  state.clock.textContent=terminalTime(now);
  function line(kind,name,text){return E('div',{'class':'hv-terminal-status'},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('strong',{},name),E('span',{},text)]);}
  var speedPaused=status.speed_pause&&status.speed_pause.active;
  state.pinned.appendChild(line(speedPaused?'yellow':fresh?'green':'red','HomenS.AI monitor',speedPaused?bi('Paused for speed test','Пауза для теста скорости'):fresh?'OK · '+bi('last router observation ','последнее наблюдение роутера ')+terminalTime(status.time):bi('No fresh verified data','Нет свежих проверенных данных')));
  var light=autoLightModel(status,inventory,now),running=autoWorking(light),autoKind=speedPaused||light.key==='switching'?'yellow':running?'green':light.key==='off'?'grey':'red';
  state.pinned.appendChild(line(autoKind,'Auto VPN',(speedPaused?bi('PAUSED','ПАУЗА'):running?'OK · '+bi('ON','ВКЛ'):bi('OFF or unconfirmed','ВЫКЛ или не подтверждено'))+' · '+light.title+(running?' · '+bi('Activation: ','Активация: ')+journalSourceLabel((status.auto_control||{}).activation_source):'')));
  rolePairIds(status,inventory,now).map(function(id,index){
    var p=rows.find(function(p){return p.id===id;}),use=p?channelDisplayUse(p,status,inventory):null;
    var rank=use&&use.kind==='green'?0:use&&use.kind==='yellow'?1:use&&use.kind==='red'?3:2;
    return {p:p,use:use,index:index,rank:rank};
  }).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).forEach(function(row){
    var p=row.p,use=row.use,index=row.index;
    var sample=journalCurrentLatency(p,status,now),delay=sample?sample.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS'):(typeof channelCheckText==='function'?channelCheckText(p,now):bi('No fresh measurement','Нет свежего измерения'));
    state.pinned.appendChild(line(use?use.kind:'grey',index===0?bi('Primary channel','Основной канал'):bi('Reserve channel','Резервный канал'),p?use.label+(use.code?' · '+use.code:'')+' · '+endpointText(p,now)+' · '+delay:bi('No VPN selected','VPN не выбран')));
  });
  state.followButton.textContent=state.following?bi('Newest records on top','Новые записи сверху'):bi('Return to live ↑','К текущим событиям ↑');state.followButton.setAttribute('aria-pressed',state.following?'true':'false');
}
function terminalTick(){
  var state=LIVE_TERMINAL;
  if(!state.root||!document.body.contains(state.root)){if(state.timer){clearInterval(state.timer);state.timer=null;}return;}
  var section=typeof state.root.closest==='function'?state.root.closest('[data-hv-page]'):null;if(section&&section.hidden)return;
  if(state.restorePending)terminalRestoreView();
  var now=typeof statusNow==='function'?statusNow(state.frame):Date.now()/1000;terminalPinned(now);
}
function renderLiveTerminal(status,inventory){
  var state=LIVE_TERMINAL,now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  if(state.restorePending)terminalRestoreView();
  if(!state.following&&terminalLaidOut(state.body)){state.anchor=terminalAnchor(state.body);state.scrollTop=state.body.scrollTop;}
  state.frame=status;state.inventory=inventory||{};
  var oldCount=state.entries.length;
  state.entries=state.entries.filter(function(e){return e.time>=now-journalHistoryDays(status)*86400;}).slice(0,terminalLimit());
  if(!state.root||state.language!==locale){
    state.language=locale;state.pinned=E('div',{'class':'hv-terminal-pinned','data-terminal-pinned':'1'});state.clock=E('time');
    state.body=E('div',{'class':'hv-terminal-scrollback','role':'log','aria-label':bi('Live observations, repeated states grouped, newest first','Живые наблюдения, повторы объединены, новые сверху'),'tabindex':'0','scroll':function(){if(state.restorePending||!terminalLaidOut(state.body))return;state.following=state.body.scrollTop<28;state.scrollTop=state.body.scrollTop;state.anchor=state.following?null:terminalAnchor(state.body);}});
    state.followButton=E('button',{'type':'button','class':'cbi-button','click':function(){state.following=true;state.anchor=null;state.restorePending=true;terminalRestoreView();terminalPinned(typeof statusNow==='function'?statusNow(state.frame):Date.now()/1000);}});
    state.root=E('div',{'class':'hv-live','data-live-terminal':'1'},[
      E('div',{'class':'hv-live-head'},[state.clock,state.followButton]),
      E('div',{'class':'hv-linux-terminal'},[state.pinned,state.body]),
      E('small',{},[bi('Clock: 1 second; no timer messages. Consecutive identical events share a time range and repeat count. The buffer size is set in Monitoring and history retention (1–2000 observations). Network checks retain their configured cadence; recorded events are in ','Часы: 1 секунда, без сообщений таймера. Подряд повторяющиеся события объединены: диапазон времени и число повторов. Размер буфера задаётся в «Мониторинг и хранение истории» (1–2000 наблюдений). Интервал сетевых проверок не меняется; сохранённые события — в '),E('a',{'href':'#events'},bi('Events and errors','Событиях и ошибках'))])]);
    terminalRenderRuns();
  }
  var changed=oldCount!==state.entries.length;
  journalRows(status,null,now).forEach(function(entry){if(!state.seen.has(entry.key)){state.seen.add(entry.key);if(terminalAppend(entry,true))changed=true;}});
  if(changed)terminalRenderRuns();
  if(state.seen.size>terminalLimit()*2)state.seen=new Set(state.entries.filter(function(e){return !e.heartbeat;}).map(function(e){return e.key;}));
  terminalPinned(now);
  if(!state.timer)state.timer=setInterval(terminalTick,1000);
  state.restorePending=true;setTimeout(function(){if(document.body.contains(state.root))terminalRestoreView();},0);
  return state.root;
}

/* HTTPS latency is a measurement, never permission to reorder or switch VPNs. */
var LATENCY_VIEW={hours:1,end:null};
var LATENCY_HISTORY_HOURS=168;
var LATENCY_HISTORY_SECONDS=7*86400;
function latencyCurrent(status,inventory,now){
  if(status.rpc_error||status.error)return [null,null];
  var ids=rolePairIds(status,inventory,now),rows=Array.isArray(status.profiles)?status.profiles:[];
  return ids.map(function(id){var p=rows.find(function(p){return p&&p.id===id;});return p&&profileHealth(p,now).state==='healthy'&&p.vendor_state==='SETTLED'&&p.dns_ok===true&&Number.isInteger(p.https_success)&&p.https_success>=2&&Number.isFinite(p.rtt_ms)&&p.rtt_ms>=0&&p.rtt_ms<=600000?p:null;});
}
// What carries traffic when no switch is confirmed: a defined statement, never "not confirmed".
function latencyRouteText(status){
  var now=typeof routerWall==='function'?routerWall():Date.now()/1000;
  if(!status||status.rpc_error||!Number.isFinite(status.time)){var c=typeof dataCause==='function'?dataCause(status,now):{code:'STATUS-REQUEST-FAILED',text:bi('the page got no answer from the router program','страница не получила ответ от программы на роутере')};return bi('Current route is not shown: ','Текущий маршрут не показан: ')+c.text+' ('+c.code+').';}
  var on=((status||{}).auto_control||{}).requested==='on';
  return on?bi('Auto is on; the router is confirming which channel carries traffic (a few seconds).','Auto включён; роутер подтверждает, какой канал несёт трафик (несколько секунд).')
    :bi('Auto is off: traffic follows the VPN priority list of the router.','Auto выключен: трафик идёт по списку приоритетов VPN роутера.');
}
function latencyRecommendation(status,inventory,now){
  var rows=latencyCurrent(status,inventory,now);
  if(rows.filter(Boolean).length===1){
    // One channel works and the other fails: that is the recommendation, not a missing comparison.
    var ids=rolePairIds(status,inventory,now),k=rows[0]?0:1,other=(status.profiles||[]).filter(function(p){return p&&p.id===ids[1-k];})[0];
    return {index:k,single:true,text:(k===0?bi('Only the primary channel works now','Сейчас работает только основной канал'):bi('Only the reserve channel works now','Сейчас работает только резервный канал'))+' ('+rows[k].rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')+'). '+(k===0?bi('Reserve: ','Резервный: '):bi('Primary: ','Основной: '))+(typeof channelCheckText==='function'?channelCheckText(other,now):bi('check failed','проверка не прошла'))};
  }
  if(rows.some(function(p){return !p;}))return {index:null,text:bi('A comparison needs fresh successful measurements for both channels.','Для сравнения нужны свежие успешные проверки обоих каналов.')};
  if(Math.abs(rows[0].rtt_ms-rows[1].rtt_ms)<.1)return {index:null,text:bi('The current measured delays are equal.','Сейчас измеренные задержки одинаковы.')};
  var index=rows[0].rtt_ms<rows[1].rtt_ms?0:1;
  return {index:index,text:bi('For current use, recommend ','Для текущей работы рекомендую ')+(index===0?bi('the primary channel','основной канал'):bi('the reserve channel','резервный канал'))+': '+rows[index].rtt_ms.toFixed(1)+' '+bi('ms versus ','мс против ')+rows[1-index].rtt_ms.toFixed(1)+' '+bi('ms. Its measured delay is lower by ','мс. Его задержка меньше на ')+(rows[1-index].rtt_ms-rows[index].rtt_ms).toFixed(1)+' '+bi('ms.','мс.')+' · '+serverTitle(rows[index])};
}
function renderLatencyRecommendation(status,inventory,context){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,recommend=latencyRecommendation(status,inventory,now),current=latencyCurrent(status,inventory,now),ids=rolePairIds(status,inventory,now);
  var selected=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):null,path=status.channel_path||{};
  if(typeof vendorDisplaySelected!=='function'&&!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90&&path.confirmed===true&&Number.isFinite(path.time)&&now-path.time>=-5&&now-path.time<=30)selected=path.active_profile_id;
  var role=selected===ids[0]?bi('primary','основной'):selected===ids[1]?bi('reserve','резервный'):null;
  var body=[];
  function line(label,value){return E('p',{'class':'hv-recommendation-line'},[E('strong',{},label),String(value)]);}
  if(recommend.index===null||recommend.single)body.push(E('p',{},recommend.text));
  else{
    var chosen=current[recommend.index],other=current[1-recommend.index];
    var country=typeof countryName==='function'?countryName(chosen):typeof chosen.country==='string'?chosen.country:'';
    var name=chosen.router_name||chosen.name||chosen.id;
    var endpoint=endpointText(chosen,now);
    if(endpoint===bi('Server address: not observed','Адрес сервера: не получен'))endpoint=bi('No fresh address observation','Нет свежих данных об адресе');
    else endpoint=endpoint.replace(/^(?:Server: |Сервер: )/,'');
    body.push(line(bi('Recommended for current use: ','Для текущей работы рекомендую: '),recommend.index===0?bi('Primary channel','Основной канал'):bi('Reserve channel','Резервный канал')));
    body.push(line(bi('Its delay: ','Его задержка: '),chosen.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')));
    body.push(line(bi('Other channel delay: ','Задержка другого канала: '),other.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')));
    body.push(line(bi('Lower by: ','Меньше на: '),(other.rtt_ms-chosen.rtt_ms).toFixed(1)+' '+bi('ms','мс')));
    body.push(line(bi('Country: ','Страна: '),country||bi('Not recorded','Не указана')));
    body.push(line(bi('Protocol: ','Протокол: '),protocolLabel(chosen)));
    body.push(line(bi('Server: ','Сервер: '),name));
    body.push(line(bi('Connection address: ','Адрес подключения: '),endpoint));
  }
  body.push(E('p',{},role?bi('Traffic currently uses the ','Сейчас трафик использует ')+role+bi(' channel.',' канал.'):latencyRouteText(status)));
  var key='latency-recommendation-'+(context||'default');
  var node=E('details',{'class':'hv-latency-recommendation','data-latency-recommendation':'1','data-latency-disclosure':key},[
    E('summary',{},bi('Recommendation by current delay','Рекомендация по текущей задержке')),
    E('div',{'class':'hv-recommendation-body'},body)]);
  return typeof rememberDisclosure==='function'?rememberDisclosure(node,key):node;

}
function latencyStatistics(rows,start,end){
  return [0,1].map(function(index){
    var count=0,total=0,min=null,max=null,buckets=0;
    rows.forEach(function(row){var value=row[index+1],n=row[index+3];if(row[0]<start||row[0]>end||value===null||!n)return;
      count+=n;total+=value*n;buckets++;min=min===null?value:Math.min(min,value);max=max===null?value:Math.max(max,value);
    });
    return {count:count,buckets:buckets,mean:count?total/count:null,min:min,max:max};
  });
}
function renderLatencyStatistics(rows,start,end,status,inventory,now){
  var stats=latencyStatistics(rows,start,end);
  var ids=status&&typeof rolePairIds==='function'?rolePairIds(status,inventory||{},now):[];
  function loss(i){var p=status?(status.profiles||[]).filter(function(r){return r&&r.id===ids[i];})[0]:null,r=p&&typeof channelReliability==='function'?channelReliability(p,status,now):null;return r?Math.round(r.loss)+'% ('+r.bad+' '+bi('of','из')+' '+r.n+')':'—';}
  function ms(v){return v===null?'—':v.toFixed(1)+' '+bi('ms','мс');}
  return E('table',{'class':'table hv-latency-statistics','data-hv-no-sort':'1'},[
    E('tr',{},[bi('Channel','Канал'),bi('Mean','Средняя'),bi('Minimum minute mean','Мин. за минуту'),bi('Maximum minute mean','Макс. за минуту'),bi('Successful checks','Успешных проверок'),bi('Check loss, last 5 min','Потери проверок за 5 мин')].map(function(t){return E('th',{'scope':'col'},t);})),
    ...stats.map(function(s,i){return E('tr',{},[E('th',{'scope':'row'},i===0?bi('Primary','Основной'):bi('Reserve','Резервный')),E('td',{},ms(s.mean)),E('td',{},ms(s.min)),E('td',{},ms(s.max)),E('td',{},String(s.count)),E('td',{},loss(i))]);})]);
}
function latencyHistoryRows(status,inventory,now){
  var h=status.latency_history||{},ids=rolePairIds(status,inventory,now);
  if(h.version!==1||h.metric!=='https-rtt-ms'||!Array.isArray(h.pair)||h.pair.length!==2||h.pair[0]!==ids[0]||h.pair[1]!==ids[1])return [];
  var rows=h.rows;
  if(h.rows_json!==undefined){
    if(typeof h.rows_json!=='string'||h.rows_json.length>850000)return [];
    try{rows=JSON.parse(h.rows_json);}catch(error){return [];}
  }
  if(!Array.isArray(rows)||rows.length>10081||h.rows_count!==undefined&&(!Number.isInteger(h.rows_count)||h.rows_count!==rows.length))return [];
  return rows.filter(function(r){return Array.isArray(r)&&r.length===6&&Number.isFinite(r[0])&&r[0]>=now-LATENCY_HISTORY_SECONDS&&r[0]<=now+5&&[1,2].every(function(i){return Number.isInteger(r[i+2])&&r[i+2]>=0&&r[i+2]<=120&&(r[i+2]===0?r[i]===null:Number.isFinite(r[i])&&r[i]>=0&&r[i]<=600000);})&&['source','target','unknown','off','switching'].indexOf(r[5])>=0;}).slice().sort(function(a,b){return a[0]-b[0];});
}
function latencySegments(rows,index,start,end,maxY){
  var segments=[],points=[],color=null,last=null;
  function finish(){if(points.length)segments.push({color:color,points:points});points=[];}
  rows.forEach(function(row){
    if(row[0]<start||row[0]>end)return;
    var value=row[index+1];
    if(value===null){finish();color=null;last=null;return;}
    var selected=row[5]==='source'?'source':row[5]==='target'?'target':null;
    var nextColor=selected?selected===(index===0?'source':'target')?'#16a765':'#c49500':'#8a929d';
    if(color!==nextColor||last!==null&&row[0]-last>90)finish();
    color=nextColor;last=row[0];points.push([52+(row[0]-start)/(end-start)*904,220-value/maxY*185,row[0],value]);
  });finish();return segments;
}
function latencySvg(tag,attributes){var node=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attributes||{}).forEach(function(k){node.setAttribute(k,String(attributes[k]));});return node;}
function renderLatencyGraph(rows,start,end){
  var values=[];rows.forEach(function(r){if(r[0]>=start&&r[0]<=end)[r[1],r[2]].forEach(function(v){if(v!==null)values.push(v);});});
  var markerStride=Math.max(1,Math.ceil(rows.filter(function(r){return r[0]>=start&&r[0]<=end;}).length/720));
  var maxY=Math.max(1,...values)*1.15,svg=latencySvg('svg',{viewBox:'0 0 1000 270',role:'img','aria-label':bi('Primary and reserve HTTPS delay history in milliseconds','История HTTPS-задержки основного и резервного каналов в миллисекундах'),style:'width:100%;height:auto;min-height:180px;display:block'});
  for(var i=0;i<=4;i++){
    var y=220-i/4*185,line=latencySvg('line',{x1:52,x2:956,y1:y,y2:y,stroke:'#d8d9d8','stroke-width':1});svg.appendChild(line);
    var label=latencySvg('text',{x:45,y:y+4,'text-anchor':'end','font-size':12,fill:'currentColor'});label.textContent=String(Math.round(maxY*i/4));svg.appendChild(label);
    var stamp=start+(end-start)*i/4,tick=latencySvg('text',{x:52+904*i/4,y:246,'text-anchor':i===0?'start':i===4?'end':'middle','font-size':12,fill:'currentColor'});tick.textContent=new Date(stamp*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',end-start>86400?{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}:{hour:'2-digit',minute:'2-digit'});svg.appendChild(tick);
  }
  [0,1].forEach(function(index){var pointIndex=0,markers=0;latencySegments(rows,index,start,end,maxY).forEach(function(segment){
    var path=latencySvg('polyline',{points:segment.points.map(function(p){return p[0].toFixed(2)+','+p[1].toFixed(2);}).join(' '),fill:'none',stroke:segment.color,'stroke-width':index===0?3:2,'stroke-dasharray':index===0?'none':'5 3'});if(segment.points.length>1)svg.appendChild(path);
    segment.points.forEach(function(p){if(pointIndex++%markerStride!==0||markers>=720)return;markers++;var dot=latencySvg('circle',{cx:p[0],cy:p[1],r:2,fill:segment.color}),title=latencySvg('title');title.textContent=(index===0?bi('Primary','Основной'):bi('Reserve','Резервный'))+' · '+new Date(p[2]*1000).toLocaleString()+' · '+p[3].toFixed(1)+' ms';dot.appendChild(title);svg.appendChild(dot);});
  });});return svg;
}
function renderLatencyPanel(status,inventory){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,history=latencyHistoryRows(status,inventory,now),current=latencyCurrent(status,inventory,now),plot=E('div',{'class':'hv-latency-history'}),statistics=E('div',{'class':'hv-latency-statistics-wrap'}),caption=E('p',{'role':'status'});
  var hours=E('input',{'type':'range',min:'1',max:String(LATENCY_HISTORY_HOURS),step:'1','aria-label':bi('Delay history window, hours','Период истории задержек, часов'),'input':function(ev){LATENCY_VIEW.hours=Math.max(1,Math.min(LATENCY_HISTORY_HOURS,Math.round(Number(ev.target.value)||1)));draw();}});hours.value=String(LATENCY_VIEW.hours);
  var pan=E('input',{'type':'range',min:'0',max:String((LATENCY_HISTORY_HOURS-LATENCY_VIEW.hours)*60),step:'1','aria-label':bi('Browse the last seven days, minutes back','Просмотр последних 7 суток, минут назад'),'input':function(ev){var offset=Math.max(0,Math.min((LATENCY_HISTORY_HOURS-LATENCY_VIEW.hours)*60,Number(ev.target.value)||0));LATENCY_VIEW.end=offset?now-offset*60:null;draw();}});
  var live=E('button',{'type':'button','class':'cbi-button','click':function(){LATENCY_VIEW.end=null;draw();}},bi('Live','Сейчас'));
  function draw(){
    var end=LATENCY_VIEW.end===null?now:Math.min(now,LATENCY_VIEW.end),start=end-LATENCY_VIEW.hours*3600;
    if(start<now-LATENCY_HISTORY_SECONDS){start=now-LATENCY_HISTORY_SECONDS;end=start+LATENCY_VIEW.hours*3600;LATENCY_VIEW.end=end>=now?null:end;}
    while(plot.firstChild)plot.removeChild(plot.firstChild);
    plot.appendChild(renderLatencyGraph(history,start,end));var windowLabel=LATENCY_VIEW.hours>=24&&LATENCY_VIEW.hours%24===0?(LATENCY_VIEW.hours/24)+' '+bi('day(s)','сут'):LATENCY_VIEW.hours+' '+bi('hour(s)','ч');caption.textContent=windowLabel+' · '+new Date(start*1000).toLocaleString()+' — '+new Date(end*1000).toLocaleString();
    while(statistics.firstChild)statistics.removeChild(statistics.firstChild);statistics.appendChild(renderLatencyStatistics(history,start,end,status,inventory,now));
    pan.max=String((LATENCY_HISTORY_HOURS-LATENCY_VIEW.hours)*60);pan.disabled=Number(pan.max)===0;pan.value=String(Math.max(0,Math.round((now-end)/60)));
  }
  draw();
  var notes=E('details',{'class':'hv-latency-notes','data-auto-disclosure':'latency-statistics'},[E('summary',{},bi('How statistics are calculated','Как считается статистика'))]);
  if(typeof rememberDisclosure==='function')rememberDisclosure(notes,'latency-statistics');
  var selectedId=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):null,roleIds=rolePairIds(status,inventory,now);
  var selected=selectedId&&selectedId===roleIds[0]?'source':selectedId&&selectedId===roleIds[1]?'target':null;
  return E('section',{'class':'hv-chart-card','data-latency-panel':'1','data-stats-reset':'latency'},[
    E('h3',{},bi('Delay of the two VPN channels','Задержка двух VPN-каналов')),renderLatencyRecommendation(status,inventory,'channels'),
    E('div',{'class':'hv-latency-values'},[0,1].map(function(i){return E('p',{},[E('strong',{},i===0?bi('Primary: ','Основной: '):bi('Reserve: ','Резервный: ')),current[i]?current[i].rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS'):(typeof channelCheckText==='function'?channelCheckText((status.profiles||[]).filter(function(p){return p&&p.id===rolePairIds(status,inventory,now)[i];})[0],now):bi('No fresh measurement','Нет свежего измерения'))]);})),
    E('div',{'class':'hv-latency-series'},[
      E('span',{},[E('i',{'class':'hv-latency-sample','aria-hidden':'true'}),bi('Primary · solid line','Основной · сплошная линия')]),
      E('span',{},[E('i',{'class':'hv-latency-sample hv-latency-dashed','aria-hidden':'true'}),bi('Reserve · dashed line','Резервный · пунктирная линия')])]),
    E('p',{'class':'hv-latency-current-route'},selected==='source'?bi('Currently in use: primary channel','Сейчас задействован основной канал'):selected==='target'?bi('Currently in use: reserve channel','Сейчас задействован резервный канал'):latencyRouteText(status)),
    plot,caption,E('div',{'class':'hv-latency-controls'},[
      E('label',{'class':'hv-latency-slider'},[hours,E('span',{},bi('Window: 1 hour–7 days','Период: 1 час–7 суток'))]),
      E('label',{'class':'hv-latency-slider'},[pan,E('span',{},bi('Browse the last 7 days','Просмотр последних 7 суток'))]),live]),statistics,
    (function(){[
      E('p',{},bi('Statistics follow the selected graph window.','Статистика соответствует выбранному периоду графика.')),
      E('p',{},bi('Mean is weighted by successful checks.','Средняя учитывает число успешных проверок.')),
      E('p',{},bi('Minimum and maximum describe observed minute means.','Минимум и максимум относятся к наблюдённым минутным средним.')),
      E('p',{},bi('Missing periods and failed measurements are not filled.','Пропуски и неудачные измерения не дорисовываются.')),
      E('p',{},bi('Storage follows the configured 1–7 days. Deleted older measurements cannot be restored.','Хранение соответствует настройке 1–7 дней. Уже удалённые старые замеры не восстанавливаются.')),
      E('p',{},bi('In wide views markers are sampled; lines and statistics use retained measurements.','В широком периоде метки показаны выборочно; линии и статистика используют сохранённые измерения.')),
      E('p',{},bi('History starts when recording is enabled.','История начинается с включения записи.')),
      E('p',{},bi('History is saved at the configured checkpoint interval.','История сохраняется с настроенным интервалом checkpoint.'))].forEach(function(node){notes.appendChild(node);});return notes;})(),
    (status.latency_history||{}).notice?E('p',{'role':'status'},status.latency_history.notice):null].filter(Boolean));
}

/* Read-only role layout and disclosures. Never changes configured priority or routes. */
var HV_DISCLOSURES=Object.create(null);
function rememberDisclosure(node,key){
  if(HV_DISCLOSURES[key]===true)node.setAttribute('open','open');
  node.addEventListener('toggle',function(){HV_DISCLOSURES[key]=node.open===true;});return node;
}
function rolePairIds(status,inventory,now){
  var settings=(inventory||{}).settings||{},rows=(status||{}).profiles||[];
  function member(role,key){
    var p=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,role,now):null;
    return p&&p.id||settings[key]||(status.native_failover||{})[role]||null;
  }
  return [member('source','plan_source'),member('target','plan_target')];
}
function roleOrderedRows(rows,status,inventory,now){
  var ids=rolePairIds(status,inventory,now);
  return rows.map(function(p,i){var role=ids.indexOf(p.id);return {p:p,i:i,rank:role<0?2:role};}).sort(function(a,b){return a.rank-b.rank||a.i-b.i;}).map(function(row){return row.p;});
}
function currentCheckOrderedRows(rows,status,inventory,now){
  return roleOrderedRows(rows,status,inventory,now).map(function(p,i){
    var use=typeof channelDisplayUse==='function'?channelDisplayUse(p,status,inventory):{state:'unknown',kind:'grey'};
    var rank=use.state==='selected'&&use.kind==='green'?0:use.state==='standby'?1:['checking','switching'].indexOf(use.state)>=0?2:use.state==='unknown'?3:4;
    return {p:p,index:i,rank:rank};
  }).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).map(function(row){return row.p;});
}
function splitRoleRows(rows,status,inventory,now){
  var ids=rolePairIds(status,inventory,now),ordered=roleOrderedRows(rows,status,inventory,now),pair=ordered.filter(function(p){return ids.indexOf(p.id)>=0;});
  if(!pair.length)pair=ordered.slice(0,2);
  return {pair:pair,other:ordered.filter(function(p){return !pair.some(function(q){return p.id===q.id;});})};
}
function channelCardHosts(rows,status,inventory,cards){
  var split=splitRoleRows(rows,status,inventory,(typeof routerWall==='function'?routerWall():Date.now()/1000)),ids=split.pair.map(function(p){return p.id;}),other=E('div',{'class':'hv-server-grid'});
  var details=rememberDisclosure(E('details',{'class':'hv-channel-more','data-channel-more':'1'},[
    E('summary',{},bi('More VPN servers','Ещё VPN-серверы')+' ('+split.other.length+')'),other]),'channels-other');
  return {get:function(p){return ids.indexOf(p.id)>=0?cards:other;},finish:function(){if(split.other.length)cards.appendChild(details);}};
}
function roleDescription(p,status,inventory){
  var ids=rolePairIds(status,inventory,(typeof routerWall==='function'?routerWall():Date.now()/1000)),role=p&&p.id===ids[0]?bi('Primary channel','Основной канал'):p&&p.id===ids[1]?bi('Reserve channel','Резервный канал'):bi('Other VPN','Другой VPN');
  return role;
}
function endpointText(p,now){
  var e=p&&p.server_endpoint;
  if(!e||typeof e!=='object'||e.source!=='live-kernel-peer'||p.vendor_state!=='SETTLED'||!Number.isFinite(p.time)||now-p.time< -5||now-p.time>90||typeof p.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(p.interface)||e.profile!==p.id||e.interface!==p.interface||!Number.isFinite(e.time)||now-e.time< -5||now-e.time>90||typeof e.host!=='string'||!/^[A-Fa-f0-9.:-]{1,100}$/.test(e.host)||!Number.isInteger(e.port)||e.port<1||e.port>65535||['tcp','udp'].indexOf(e.transport)<0)return bi('Server address: not observed','Адрес сервера: не получен');
  var host=e.host.indexOf(':')>=0?'['+e.host+']':e.host;
  return bi('Server: ','Сервер: ')+host+':'+e.port+' · '+e.transport.toUpperCase();
}
function limitTableRows(table,limit,key){
  var expanded=HV_DISCLOSURES[key]===true,button=E('button',{'type':'button','class':'cbi-button hv-more-rows','aria-expanded':expanded?'true':'false','click':function(){expanded=!expanded;HV_DISCLOSURES[key]=expanded;apply();}});
  function apply(){
    if(typeof table.querySelectorAll!=='function')return;
    var rows=Array.from(table.querySelectorAll('tr')).filter(function(row){return row.querySelector('td')&&!row.hidden;});
    rows.forEach(function(row,i){if(!expanded&&i>=limit)row.setAttribute('data-over-limit','true');else row.removeAttribute('data-over-limit');});
    table.setAttribute('data-limited-table','1');button.setAttribute('aria-expanded',expanded?'true':'false');
    button.textContent=(expanded?'▾ ':'▸ ')+(expanded?bi('Show fewer','Свернуть'):bi('More entries','Ещё записи'))+' ('+Math.max(0,rows.length-limit)+')';button.hidden=rows.length<=limit;
  }
  apply();
  if(typeof MutationObserver!=='undefined')new MutationObserver(apply).observe(table,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden']});
  return E('div',{'class':'hv-limited-table'},[table,button]);
}
function currentCheckServerCell(p,now){
  return E('td',{},[E('strong',{},serverTitle(p)),E('br'),E('small',{'class':'hv-server-address'},endpointText(p,now))]);
}
function renderCompactCascade(status,inventory){
  var now=(typeof routerWall==='function'?routerWall():Date.now()/1000),split=splitRoleRows(status.profiles||[],status,inventory||{},now),recommendation=reliabilityRecommendation(status,inventory||{},now);
  function row(p){var use=channelDisplayUse(p,status,inventory||{});return E('div',{'class':'hv-cascade-item','data-profile':p.id},[
    E('span',{'class':'hv-check-lamp hv-check-'+use.kind,'aria-hidden':'true'}),
    E('div',{},[E('strong',{},roleDescription(p,status,inventory||{})),E('p',{},serverTitle(p)),E('small',{},endpointText(p,now)),E('p',{},use.label)])]);}
  var other=rememberDisclosure(E('details',{'class':'hv-channel-more','data-cascade-more':'1'},[E('summary',{},bi('Other VPN profiles','Другие VPN-профили')+' ('+split.other.length+')'),E('div',{'class':'hv-cascade-grid'},split.other.map(row))]),'cascade-other');
  return E('section',{'class':'hv-chart-card hv-cascade'},[
    E('h2',{},bi('Which VPN carries your traffic and which one is next','Какой VPN пропускает ваш трафик и какой следующий')),
    E('p',{},bi('The saved primary/reserve pair is shown in fixed role order. The selected route and health are separate; the recommendation does not change your settings.','Сохранённая пара показана в постоянном порядке: основной, затем резервный. Выбранный маршрут и состояние связи — разные сведения; рекомендация не меняет ваши настройки.')),
    E('div',{'class':'hv-cascade-grid'},split.pair.map(row)),
    recommendation?E('p',{'class':'hv-reliability-note','data-reliability':'1'},[E('strong',{},bi('Recommendation: ','Рекомендация: ')),recommendation.text+' ',typeof errorCodeLink==='function'?errorCodeLink(recommendation.code):recommendation.code]):null,
    split.other.length?other:null].filter(Boolean));
}

/* Channel reliability from the router's own check history. Display only: it changes no setting, priority or route. */
var RELIABILITY_WINDOW=300,RELIABILITY_MIN=6,RELIABILITY_LIMIT=20,ALTERNATIVE_MIN_CHECKS=20,ALTERNATIVE_MIN_SUCCESS=95;
function channelReliability(profile,status,now){
  if(!profile||!status||!Array.isArray(status.samples)||!Number.isFinite(now))return null;
  var rows=status.samples.filter(function(s){return s&&s.id===profile.id&&Number.isFinite(s.time)&&now-s.time>=-5&&now-s.time<=RELIABILITY_WINDOW&&['CHECK-001','CHECK-LIMIT','PROFILE-INACTIVE'].indexOf(s.code)<0;});
  if(rows.length<RELIABILITY_MIN)return null;
  var bad=rows.filter(function(s){return !(s.code==null&&s.dns_ok===true&&s.https_success>=2);}).length,loss=100*bad/rows.length;
  return {n:rows.length,bad:bad,loss:loss,minutes:Math.round(RELIABILITY_WINDOW/60),unreliable:loss>=RELIABILITY_LIMIT};
}
function reliabilityText(r){
  return bi('check loss ','потери проверок ')+Math.round(r.loss)+'% ('+r.bad+' '+bi('of ','из ')+r.n+' '+bi('in ','за ')+r.minutes+' '+bi('min','мин')+')';
}
function bestMeasuredAlternative(status,excludedIds){
  var rank=typeof dvRank==='function'?dvRank(status):{},best=null;
  ((status||{}).profiles||[]).forEach(function(p){
    var r=rank[p.id];if(!r||excludedIds.indexOf(p.id)>=0||r.n<ALTERNATIVE_MIN_CHECKS)return;
    var percent=100*r.good/r.n,rtt=r.good?r.sum/r.good:Infinity;
    if(percent<ALTERNATIVE_MIN_SUCCESS)return;
    if(!best||percent>best.percent||percent===best.percent&&rtt<best.rtt)best={p:p,percent:percent,n:r.n,rtt:rtt};
  });
  return best;
}
// The recommendation is computed from the loss statistics of the saved pair and of the measured profiles.
function reliabilityRecommendation(status,inventory,now){
  var ids=rolePairIds(status,inventory,now),rows=(status||{}).profiles||[];
  var pair=ids.map(function(id){return rows.filter(function(p){return p.id===id;})[0]||null;});
  var rel=pair.map(function(p){return p?channelReliability(p,status,now):null;}),bad=rel.map(function(r){return !!(r&&r.unreliable);});
  if(!bad[0]&&!bad[1])return null;
  var best=bestMeasuredAlternative(status,ids),other=bad[0]?rel[1]:rel[0];
  var tail=best?bi(' Best spare by statistics: ',' Лучший запасной по статистике: ')+serverTitle(best.p)+' ('+bi('success ','успех ')+Math.round(best.percent)+'% '+bi('over ','по ')+best.n+' '+bi('checks','проверкам')+').'
    :bi(' No other server has enough measurements yet: run a speed test in Tests.',' У других серверов пока мало измерений: запустите тест скорости в разделе «Тесты».');
  var text;
  if(bad[0]&&bad[1])text=bi('Both channels lose many checks (primary '+Math.round(rel[0].loss)+'%, reserve '+Math.round(rel[1].loss)+'%). Check the internet uplink first; then replace the worse server.','Оба канала теряют много проверок (основной '+Math.round(rel[0].loss)+'%, резерв '+Math.round(rel[1].loss)+'%). Сначала проверьте интернет-подключение роутера, затем замените худший сервер.');
  else if(bad[0])text=bi('The primary has a reliability problem ('+reliabilityText(rel[0])+'). '+(other?'Keep traffic on the reserve (loss '+Math.round(other.loss)+'%) and replace the primary server.':'Replace the primary server; the reserve has too few measurements to compare.'),'У основного канала проблема с надёжностью ('+reliabilityText(rel[0])+'). '+(other?'Держите трафик на резерве (потери '+Math.round(other.loss)+'%) и замените сервер основного.':'Замените сервер основного; у резерва мало измерений для сравнения.'));
  else text=bi('The reserve has a reliability problem ('+reliabilityText(rel[1])+'). '+(other?'Keep traffic on the primary (loss '+Math.round(other.loss)+'%) and replace the reserve server.':'Replace the reserve server; the primary has too few measurements to compare.'),'У резервного канала проблема с надёжностью ('+reliabilityText(rel[1])+'). '+(other?'Держите трафик на основном (потери '+Math.round(other.loss)+'%) и замените сервер резерва.':'Замените сервер резерва; у основного мало измерений для сравнения.'));
  return {code:'CHANNEL-UNRELIABLE',text:text+tail};
}

/* One-reload UI context only. No settings, Auto command or cross-tab storage. */
function languageViewContext(href){
  try{var values=new URL(href).searchParams.getAll('hv_view');return values.length===1&&['full','home'].indexOf(values[0])>=0?values[0]:null;}catch(error){return null;}
}
function clearLanguageViewUrl(href){var url=new URL(href);url.searchParams.delete('hv_view');return url.toString();}
function languageNavigationUrl(href,language,page){
  var url=new URL(href),key=typeof page==='string'?page:'home';
  if(typeof minimumRoute==='function'){
    var requested=minimumRoute(key),current=minimumRoute(url.hash);
    // A caller with only the current top-level page must not lose its subview.
    if(key===requested.page&&current.recognized&&current.page===requested.page)requested=current;
    key=requested.hash;
  }else if(!/^[a-z][a-z-]{0,39}$/.test(key))key='home';
  url.searchParams.set('lang',language==='ru'?'ru':'en');
  url.searchParams.set('hv_view',key==='home'?'home':'full');
  url.hash=key;
  // A stale settings-entry shortcut must not override the page being translated.
  if(key!=='settings'&&key!=='settings/setup')url.searchParams.delete('setup');
  return url.toString();
}

/* Display access is unconditional. Evidence describes what may be displayed;
   only the existing controller can authorize Start/Stop. No RPC or acceptance. */
function simpleHomeEntry(evidence){
  var e=evidence&&typeof evidence==='object'?evidence:{};
  var fresh=e.statusFresh===true&&e.controllerFresh===true;
  return {page:'home',showCard:true,
    reason:!fresh?'CURRENT-STATUS-REQUIRED':e.autoRunning===true?'AUTO-READY-RUNNING':'AUTO-NOT-CONFIRMED-RUNNING',
    statusFresh:e.statusFresh===true,controllerFresh:e.controllerFresh===true,
    autoRunning:fresh&&e.autoRunning===true};
}

/* Display only. The existing Auto control remains the sole owner of commands. */
function simpleHomeShortcutReason(){return '';}
function simpleHomeAutoEnabled(status,now){
  status=status||{};var ns=status.native_failover||{},intent=status.auto_control||{};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90)||!manualFresh(ns.time,now,30))return false;
  if(intent.requested==='off')return false;
  var control=autoControlModel(status,now);
  if(intent.pair_phase)return intent.pair_phase==='RUNNING'&&intent.requested==='on'&&(control.on||control.transitioning);
  return control.fresh&&!control.awaiting&&(control.on||control.transitioning&&intent.requested==='on');
}
function renderSimpleHomeShortcut(getModel,goHome){
  var button=E('button',{'type':'button','class':'cbi-button hv-simple-shortcut-button','data-simple-shortcut':'1','aria-label':bi('Return to minimum','Вернуться к минимуму'),'click':function(){goHome();}},bi('← To minimum','← К минимуму'));
  var host=E('div',{'class':'hv-simple-shortcut-group','data-simple-home-available':'true'},button);
  host.update=function(){button.disabled=false;button.setAttribute('aria-disabled','false');};host.update();return host;
}
function simpleHomeHealth(profile,now,unavailable){
  if(unavailable||!profile)return {state:'unknown',label:bi('No fresh data','Нет свежих данных')};
  var health=profileHealth(profile,now);
  return {state:health.state,label:health.state==='healthy'?bi('Available','Доступен'):health.state==='failed'?bi('Unavailable','Недоступен'):health.state==='inactive'?bi('Tunnel is off','Туннель отключён'):bi('No fresh data','Нет свежих данных')};
}
function simpleHomeModel(status,inventory,now){
  status=status||{};inventory=inventory||{};
  var ns=status.native_failover||{},control=autoControlModel(status,now);
  var source=vendorDisplayMember(status,inventory,'source',now,ns.source),target=vendorDisplayMember(status,inventory,'target',now,ns.target);
  var path=manualConfirmedPath(status,source,target,now);
  var unavailable=!!status.error||!!status.rpc_error||!manualFresh(status.time,now,90)||!control.fresh;
  var decision=simpleHomeEntry({statusFresh:!status.error&&!status.rpc_error&&manualFresh(status.time,now,90),controllerFresh:control.fresh,autoRunning:simpleHomeAutoEnabled(status,now)});
  var operation=typeof autoCommandOperation==='function'?autoCommandOperation(status,now):null;
  var sourceHealth=simpleHomeHealth(source,now,unavailable),targetHealth=simpleHomeHealth(target,now,unavailable);
  var selected=unavailable?null:path.selected,activeHealth=selected==='source'?sourceHealth:selected==='target'?targetHealth:null;
  decision.source=source;decision.target=target;decision.selectedRole=selected;
  decision.sourceHealth=sourceHealth;decision.targetHealth=targetHealth;
  decision.activeHealthy=!!activeHealth&&activeHealth.state==='healthy';
  decision.moving=!unavailable&&(!!path.moving||control.transitioning);
  decision.dataUnavailable=unavailable;decision.control=control;decision.operation=operation;
  decision.enabled=simpleHomeAutoEnabled(status,now);decision.actionStop=control.stop||operation==='starting'||!control.fresh;
  decision.blockers=control.fresh&&Array.isArray(ns.blockers)?ns.blockers.slice(0,4):[];
  if(path.code&&decision.blockers.indexOf(path.code)<0)decision.blockers.push(path.code);
  decision.setupRequired=!unavailable&&control.off&&!decision.moving&&!operation&&(!source||!target||!source.id||!target.id||source.id===target.id);
  if(control.paused){decision.state='pending';decision.title=bi('Auto paused for speed test','Auto на паузе для теста скорости');decision.summary=bi('Monitoring resumes first, then Auto. Your VPNs stay connected.','Сначала возобновится мониторинг, затем Auto. VPN остаются подключёнными.');}
  else if(unavailable){decision.state='unknown';decision.title=bi('No fresh data','Нет свежих данных');decision.summary=bi('Check the connection to the router.','Проверьте связь с роутером.');}
  else if(operation==='stopping'){decision.state='pending';decision.title=bi('Turning Auto off…','Выключение Auto…');decision.summary=bi('The router is carrying out the command, wait a few seconds.','Роутер выполняет команду, подождите несколько секунд.');}
  else if(operation==='starting'){decision.state='pending';decision.title=bi('Turning Auto on…','Включение Auto…');decision.summary=bi('The router is carrying out the command, wait a few seconds.','Роутер выполняет команду, подождите несколько секунд.');}
  else if(decision.moving){decision.state='pending';decision.title=bi('Switching channel','Переключение канала');decision.summary=bi('The active channel is being confirmed.','Рабочий канал уточняется.');}
  else if(control.on&&path.code){decision.state='unknown';decision.title=bi('The traffic channel is not verified','Канал трафика не подтверждён');decision.summary=bi('Waiting for verified router VPN rules.','Ждём подтверждения действующих правил VPN роутером.')+' ('+path.code+')';}
  else if(control.on&&decision.activeHealthy){decision.state='on';decision.title=selected==='target'?bi('Reserve is working','Работает резерв'):bi('Auto works','Auto работает');decision.summary=selected==='target'?bi('Reserve channel is in use.','Задействован резервный канал.'):bi('Primary channel is in use.','Задействован основной канал.');}
  else if(control.on){decision.state=activeHealth&&['failed','inactive'].indexOf(activeHealth.state)>=0?'error':'unknown';decision.title=bi('Internet through the VPN has not been checked recently','Давно не проверялось, есть ли интернет через VPN');decision.summary=bi('Press "Check connection".','Нажмите «Проверить соединение».');}
  else if(ns.state==='BLOCKED'){decision.state='error';decision.title=bi('Auto is blocked','Auto заблокирован');decision.summary=decision.blockers.length?autoBlockerText(decision.blockers[0]):bi('Open diagnostics for the current reason.','Откройте диагностику для уточнения причины.');}
  else if(decision.setupRequired){decision.state='setup';decision.title=bi('Finish setup','Завершите настройку');decision.summary=bi('Choose a primary and a different reserve profile.','Выберите основной и другой, резервный профиль.');}
  else if(control.off){decision.state='off';decision.title=bi('Auto is off','Auto выключен');decision.summary=selected==='target'?bi('Automatic switching is stopped; reserve remains selected.','Автопереключение остановлено; выбран резерв.'):bi('Automatic switching is stopped.','Автоматическое переключение остановлено.');}
  else{decision.state='error';decision.title=bi('Auto cannot run','Auto не может работать');decision.summary=bi('Press to see why.','Нажмите, чтобы узнать почему.');}
  return decision;
}
function renderSimpleHome(status,inventory,model,controlCard,openMenu){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var original=controlCard&&controlCard.querySelector('.hv-auto-power');
  // Mount the original element and action label: pending Start remains cancellable,
  // and async completion updates the same controls without a second command path.
  var power=original||E('span',{'class':'hv-simple-control-unavailable'},bi('Auto control unavailable','Управление Auto недоступно'));
  if(original)original.setAttribute('data-simple-home-auto','1');
  var actionLabel=controlCard&&controlCard.querySelector('.hv-auto-action')||E('span',{'class':'hv-simple-action'},bi('Open diagnostics','Откройте диагностику'));
  if(actionLabel.classList&&actionLabel.classList.add)actionLabel.classList.add('hv-simple-action');
  function member(profile,role){
    var health=role==='source'?model.sourceHealth:model.targetHealth,selected=model.selectedRole===role;
    var latency=health.state==='healthy'&&profile&&Number.isFinite(profile.rtt_ms)&&profile.rtt_ms>=0?profile.rtt_ms.toFixed(0)+' '+bi('ms','мс'):(typeof channelCheckText==='function'?channelCheckText(profile,now):bi('No fresh measurement','Нет свежего измерения'));
    var title=profile&&(profile.name||profile.router_name)||bi('No VPN selected','VPN не выбран');
    return E('div',{'class':'hv-simple-channel hv-simple-channel-'+health.state,'data-simple-role':role},[
      E('div',{'class':'hv-simple-channel-top'},[E('strong',{},role==='source'?bi('Primary','Основной'):bi('Reserve','Резервный')),E('span',{},health.label)]),
      E('div',{'class':'hv-simple-profile'},title),E('div',{'class':'hv-simple-selection'},selected?bi('In use','Используется'):model.selectedRole?bi('Not in use','Не используется'):bi('The router has not reported which VPN is in use yet','Роутер ещё не сообщил, какой VPN работает')),
      E('div',{'class':'hv-simple-server'},endpointText(profile,now)),E('div',{},profile&&['wireguard','openvpn'].indexOf(profile.protocol)>=0?protocolLabel(profile):bi('Not reported by the router','Роутер не сообщил')),
      profile&&countryName(profile)?E('div',{},countryName(profile)):null,E('div',{'class':'hv-simple-latency'},bi('Delay: ','Задержка: ')+latency)
    ].filter(Boolean));
  }
  var monitor=model.dataUnavailable?bi('No connection to the router','Нет связи с роутером'):model.state==='error'?bi('Needs attention','Нужно внимание'):model.enabled?bi('Auto is on','Auto включён'):model.control&&model.control.off?bi('Auto is off','Auto выключен'):bi('Being confirmed','Уточняется');
  return E('section',{'class':'hv-simple-home','data-simple-home':model.state},[
    E('div',{'class':'hv-simple-card'},[
      E('div',{'class':'hv-simple-top'},[E('strong',{},'Auto VPN'),E('span',{'class':'hv-simple-monitor hv-simple-monitor-'+model.state},monitor)]),
      E('h2',{'class':'hv-simple-state','role':'status'},model.title),
      E('div',{'class':'hv-simple-power-unit'},[E('div',{'class':'hv-simple-power'},power),actionLabel]),
      E('p',{'class':'hv-simple-route'},model.summary),
      typeof renderAutoRemedy==='function'?E('div',{},(model.blockers||[]).map(renderAutoRemedy).filter(Boolean)):null,
      model.setupRequired?E('p',{'class':'hv-simple-setup-action'},E('a',{'class':'cbi-button hv-minimum-action','href':'#settings','data-simple-setup':'1'},bi('Configure pair','Настроить пару'))):null,
      E('div',{'class':'hv-simple-reserve'},[E('span',{},bi('Reserve channel','Резервный канал')),E('strong',{},model.targetHealth.label)]),
      E('details',{'class':'hv-simple-details','data-home-details':'channels'},[E('summary',{},bi('Connection details','Подробности соединения')),E('div',{'class':'hv-simple-pair'},[member(model.source,'source'),member(model.target,'target')]),E('p',{},bi('Checks originate from the router over IPv4.','Проверки выполняются с роутера по IPv4.'))]),
      E('button',{'type':'button','class':'cbi-button hv-simple-open-menu','data-simple-open-menu':'1','click':openMenu},bi('Advanced menu →','Расширенное меню →')),
      E('p',{'class':'hv-simple-menu-hint'},bi('Overview · channels · checks · settings','Обзор · каналы · проверки · настройки'))
    ].filter(Boolean))
  ]);
}

/* Only an explicit reviewed click invokes the narrowly scoped writer. */
var preparationPreviewCall=rpc.declare({object:'homensai-vpn',method:'preparation_preview',params:['action']});
var preparationApplyCall=rpc.declare({object:'homensai-vpn',method:'preparation_apply',params:['action','revision','control_revision']});
var preparationBusy=false,preparationDialog=0;
var PREPARATION_ACTIONS={
 'source-autostart':['Disable primary VPN startup','Отключить автозапуск основного VPN','Disable Bring up on boot for the currently selected primary VPN. The running VPN stays connected.','Отключить «Поднимать при загрузке» для текущего выбранного основного VPN. Работающий VPN остаётся подключённым.'],
 'target-autostart':['Disable reserve VPN startup','Отключить автозапуск резервного VPN','Disable Bring up on boot for the currently selected reserve VPN. The running VPN stays connected.','Отключить «Поднимать при загрузке» для текущего выбранного резервного VPN. Работающий VPN остаётся подключённым.'],
 'wg-autostart':['Disable WireGuard startup','Отключить автозапуск WireGuard','Disable Bring up on boot for WireGuard (wgclient1). The running VPN stays connected.','Отключить «Поднимать при загрузке» для WireGuard (wgclient1). Работающий VPN остаётся подключённым.'],
 'ovpn-autostart':['Disable OpenVPN startup','Отключить автозапуск OpenVPN','Disable Bring up on boot for OpenVPN (ovpnclient1). The running VPN stays connected.','Отключить «Поднимать при загрузке» для OpenVPN (ovpnclient1). Работающий VPN остаётся подключённым.'],
 'vpn-boot':['Disable stock VPN startup','Отключить штатный автозапуск VPN','Disable vpn-client startup when the router boots. The running service is not stopped.','Отключить запуск службы vpn-client при включении роутера. Работающая служба не останавливается.'],
 'sfe-boot':['Disable SFE startup','Отключить автозапуск SFE','Disable shortcut-fe startup when the router boots. Loaded acceleration remains until a deliberate router restart.','Отключить запуск shortcut-fe при включении роутера. Работающее ускорение сохранится до отдельной перезагрузки роутера.'],
 'hnat':['Disable hardware acceleration','Отключить аппаратное ускорение','Disable hardware acceleration in the saved settings and the running system. No network/firewall restart or module removal.','Выключить аппаратное ускорение в сохранённых настройках и в работающей системе. Без перезапуска сети/firewall и удаления модулей.'],
 'flow-offload':['Disable firewall offloading','Отключить ускорение firewall','Save both flow-offloading flags as 0. This does not reload the firewall. Auto remains blocked until a separate deliberate router restart applies the setting to live flows.','Сохранить оба флага flow offloading=0. Firewall не перезапускается. Auto останется заблокирован до отдельной перезагрузки роутера, которая применит настройку к действующим потокам.'],
 'sfe-autoload':['Disable SFE module autoload','Отключить автозагрузку модулей SFE','Disable loading SFE modules when the router boots and preserve the verified original startup file. Loaded modules are not forcibly removed.','Отключить загрузку модулей SFE при включении роутера и сохранить проверенный исходный файл запуска. Загруженные модули принудительно не удаляются.']
};
var PREPARATION_REASONS={
 'PREPARATION-STOP-AUTO-FIRST':['Stop Auto and wait for completed recovery before changing preparation.','Сначала остановите Auto и дождитесь завершения восстановления.'],
 'PREPARATION-RECOVERY-REQUIRED':['The previous session or an unconfirmed preparation write needs recovery. Existing changes and backups are retained.','Предыдущая сессия или неподтверждённое изменение подготовки требует восстановления. Изменения и исходные значения сохранены.'],
 'PREPARATION-STALE-REVIEW':['Settings or Auto controls changed after review. Review this action again.','Настройки или управление Auto изменились после просмотра. Проверьте действие заново.'],
 'PREPARATION-PLATFORM-UNVERIFIED':['This button requires a verified GL-MT3000/GL-MT6000 with firmware 4.11.0.','Кнопке нужен проверенный GL-MT3000/GL-MT6000 с прошивкой 4.11.0.'],
 'PREPARATION-HNAT-UNVERIFIED':['The hardware acceleration runtime hook cannot be safely verified. Use the linked GL.iNet settings.','Не удалось безопасно проверить работающий HNAT hook. Используйте ссылку на настройки GL.iNet.'],
 'PREPARATION-PENDING-OR-UNREADABLE':['There are unsaved router changes or settings cannot be read. Resolve them in the router panel first.','Есть несохранённые изменения роутера или настройки не читаются. Сначала проверьте их в панели роутера.'],
 'PREPARATION-WRITE-UNCONFIRMED':['The change could not be confirmed. Do not repeat it blindly; inspect recovery and the saved original values.','Изменение не подтверждено. Не повторяйте его вслепую; проверьте восстановление и сохранённые исходные значения.']
};
PREPARATION_REASONS['PREPARATION-RESTART-REQUIRED']=['The boot setting is saved. Restart this router deliberately before starting Auto; existing live flows/modules are not proof of the new state.','Настройка сохранена. Перед запуском Auto отдельно перезагрузите этот роутер: действующие потоки/модули ещё не подтверждают новое состояние.'];
Object.assign(PREPARATION_REASONS,{
 'PREPARATION-BACKUP-UNVERIFIED':['The original setting could not be safely preserved. Nothing new is applied.','Не удалось безопасно сохранить исходное значение. Новое изменение не применяется.'],
 'PREPARATION-BINDING-UNVERIFIED':['The named VPN interface is missing or has another protocol. Review its actual binding first.','Указанный VPN-интерфейс отсутствует или использует другой протокол. Сначала проверьте его привязку.'],
 'PREPARATION-BOOT-UNVERIFIED':['The startup link differs from the known service. It has not been removed.','Ссылка автозапуска не соответствует известной службе. Она не удалена.'],
 'PREPARATION-AUTOLOAD-UNVERIFIED':['The SFE file differs from the verified original, is missing, or a preserved copy already exists. Nothing is overwritten.','Файл SFE отличается от проверенного исходника, отсутствует либо сохранённая копия уже существует. Перезаписи нет.'],
 'PREPARATION-HISTORY-LIMIT':['The private preparation history is full. Preserve and review it before another change.','Приватная история подготовки заполнена. Сохраните и проверьте её до следующего изменения.'],
 'PREPARATION-EXTERNAL-CHANGE':['Another router configuration changed during this action. The result needs recovery review.','Во время действия изменилась другая конфигурация роутера. Результат требует проверки восстановления.']
});
function preparationReason(code){var row=PREPARATION_REASONS[code];return row?bi(row[0],row[1]):bi('The router refused this change; inspect the code and use the linked settings.','Роутер отказал в изменении; проверьте код и используйте ссылку на настройки.');}
function preparationActionsForCode(code){
 if(code==='PREP-SOURCE-AUTOSTART')return ['source-autostart'];
 if(code==='PREP-TARGET-AUTOSTART')return ['target-autostart'];
 var single={'PREP-WGCLIENT1-AUTOSTART':'wg-autostart','PREP-OVPNCLIENT1-AUTOSTART':'ovpn-autostart','PREP-STOCK-VPN-BOOT':'vpn-boot','PREP-SFE-BOOT':'sfe-boot','PREP-SFE-AUTOLOAD':'sfe-autoload','PREP-HNAT-CONFIG':'hnat','HARDWARE-ACCELERATOR-UNVERIFIED':'hnat','FLOW-OFFLOAD-ENABLED':'flow-offload'};
 if(code==='SOFTWARE-ACCELERATOR-UNVERIFIED'||code==='PREP-SFE-RUNTIME')return ['sfe-boot','sfe-autoload'];
 return Object.prototype.hasOwnProperty.call(single,code)?[single[code]]:[];
}
function preparationNotice(code,uncertain){
 ui.addNotification(null,E('p',{'role':'status'},[E('strong',{},code+' · '),preparationReason(code),uncertain?' '+bi('Some settings may already have changed; the durable recovery record is retained.','Часть настроек уже могла измениться; запись восстановления сохранена.'):'']));
}
function preparationReview(action,button){
 if(preparationBusy)return Promise.resolve();
 preparationBusy=true;button.disabled=true;button.setAttribute('aria-busy','true');
 var token=++preparationDialog;
 return preparationPreviewCall(action).then(function(plan){
  if(token!==preparationDialog)return;
  if(!plan||plan.accepted!==true){preparationNotice(plan&&plan.code||'PREPARATION-UNVERIFIED');return;}
  if(plan.action!==action||typeof plan.revision!=='string'||typeof plan.control_revision!=='string'||typeof plan.already_done!=='boolean'||!/^([a-f0-9]{64})$/.test(plan.revision)||!/^([a-f0-9]{32})$/.test(plan.control_revision)||['mt3000','mt6000'].indexOf(plan.board)<0)throw Error('PREPARATION-REPLY-INVALID');
  var description=PREPARATION_ACTIONS[action];
  var cancel=E('button',{'type':'button','class':'cbi-button','click':function(){preparationDialog++;ui.hideModal();}},bi('Cancel','Отмена'));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-preparation-confirm':action,'click':function(){
   if(preparationBusy||token!==preparationDialog)return;
   preparationBusy=true;apply.disabled=true;cancel.disabled=true;apply.setAttribute('aria-busy','true');
   return preparationApplyCall(action,plan.revision,plan.control_revision).then(function(reply){
    if(!reply||reply.applied!==true||reply.verified!==true||reply.action!==action||reply.auto_started!==false){preparationNotice(reply&&reply.code||'PREPARATION-WRITE-UNCONFIRMED',reply&&reply.change_may_have_applied);return;}
    ui.addNotification(null,E('p',{'role':'status'},bi('The setting was read back and verified. Auto has not been started. Other prerequisites remain separate.','Настройка прочитана заново и проверена. Auto не запускался. Остальные условия проверяются отдельно.')+(reply.restart_required?' '+bi('Loaded acceleration/active flows still need a separate deliberate restart or apply.','Загруженному ускорению/действующим потокам ещё нужно отдельное применение или перезагрузка.') :'')));
   }).catch(function(){preparationNotice('PREPARATION-WRITE-UNCONFIRMED',true);}).finally(function(){preparationBusy=false;preparationDialog++;ui.hideModal();});
  }},bi('Apply this change','Применить это изменение'));
  ui.showModal(bi('Review router change','Проверьте изменение роутера'),[
   E('p',{},bi('This router: GL-','Этот роутер: GL-')+plan.board.toUpperCase()),E('h3',{},bi(description[0],description[1])),E('p',{},bi(description[2],description[3])),plan.interface?E('p',{},bi('Interface: ','Интерфейс: ')+plan.interface):null,
   E('p',{},bi('The original setting is saved privately on this router before writing. A changed review, active Auto or unfinished recovery refuses the write. Auto requires its own explicit Start.','Исходное значение сохраняется приватно в этом роутере до записи. Изменившиеся данные, активный Auto или незавершённое восстановление запрещают запись. Auto требует отдельного явного запуска.')),
   plan.already_done?E('p',{},bi('Already disabled; verified by a fresh read.','Уже отключено; подтверждено свежим чтением.')):null,
   E('div',{'class':'hv-wizard-actions'},[cancel,plan.already_done?null:apply].filter(Boolean))
  ].filter(Boolean));
 }).catch(function(){preparationNotice('PREPARATION-UNVERIFIED');}).finally(function(){preparationBusy=false;button.disabled=false;button.setAttribute('aria-busy','false');});
}
function renderPreparationButtons(code){
 var buttons=preparationActionsForCode(code).map(function(action){var text=PREPARATION_ACTIONS[action];var button=E('button',{'type':'button','class':'cbi-button','data-preparation-action':action,'click':function(){return preparationReview(action,button);}},bi(text[0],text[1]));return button;});
 return buttons.length?E('div',{'class':'hv-preparation-actions'},buttons):null;
}

return view.extend({
  handleSave:null,handleSaveApply:null,handleReset:null,
  load:function(){return Promise.all([loadInventory(0),statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};}),loadBrand()]);},
  render:function(data){
    var configured=!!((data[0].settings||{}).telegram_configured);
    var setup=new URLSearchParams(window.location.search).get('setup')==='telegram';
    var inventory=data[0];
    onboardingDisplayDefaults(inventory);
    if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory,data[1]);
    // Minimum remains accessible; terms and backend Start checks still apply.
    var panel=E('div',{'class':'hv-panel'}),self=this,period='day',speedPeriod='week';
    var lastGoodStatus=data[1];
    var pointerHeld=false,deferredStatus=null;
    var subtitle=null,advancedBox=null,advancedToggle=null,appRoot=null,settingsHost=null,heading=null,sideState=null,versionBadge=null,pages={},sortStates={},searchTerms={};
    var tabs=[['start','▶',bi('Getting started','Начало работы')],['overview','◉',bi('Overview','Обзор')],['channels','⇄',bi('Channels and servers','Каналы и серверы')],['tests','⏻',bi('Tests','Тесты')],['statistics','▥',bi('Statistics','Статистика')],['traffic','◷',bi('Monthly traffic','Трафик за месяц')],['services','▣',bi('Live log','Живой журнал')],['events','≡',bi('Events and errors','События и ошибки')],['readiness','✓',bi('System readiness','Готовность системы')],['settings','⚙',bi('Settings','Настройки')],['learn','🎓',bi('Training','Обучение')],['help','?',bi('Help','Помощь')]];
    function routerVpnUrl(){return resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);}
    function vpnSetupCard(){return E('section',{'class':'hv-chart-card hv-vpn-setup'},[E('div',{'class':'hv-auto-power-unit'},[E('a',{'class':'hv-auto-power hv-vpn-configure','href':routerVpnUrl()||null,'aria-disabled':routerVpnUrl()?null:'true','title':routerVpnUrl()?null:bi('Router address unavailable in this preview','Адрес роутера недоступен в этом просмотре'),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('Open router VPN settings (opens a new tab)','Открыть настройки VPN роутера (новая вкладка)')},E('span',{'aria-hidden':'true','class':'hv-configure-symbol'},'⚙')),E('strong',{'class':'hv-auto-action'},bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗'))]),E('p',{},[bi('Add servers and connection keys on the router page ','Добавляйте серверы и ключи на странице роутера '),routerVpnUrl()?E('a',{'class':'hv-vpn-profile-link','href':routerVpnUrl(),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('VPN Client Profile (opens the router VPN settings in a new tab)','VPN Client Profile (открывает настройки VPN роутера в новой вкладке)')},'VPN Client Profile ↗'):E('span',{},'VPN Client Profile'),'.',E('br'),bi('Monitoring and failover priorities are set in this program (not on the router page): ','Мониторинг и приоритеты переключения настраиваются в этой программе (не на странице роутера): '),E('a',{'href':'#settings'},bi('Settings → All application settings → 3 · Existing VPNs','Настройки → Все настройки приложения → 3 · Существующие VPN')),'.'])]);}
    function validTab(key){return tabs.some(function(t){return t[0]===key;});}
    var homeLatest=data[1],homeMenuRequested=false;
    var homeShortcut=null,hybridControls=null,hybridRenderedState='';
    function hybridPage(key){
      var aliases={'diagnostics':'tests','diagnostics/checks':'tests','diagnostics/speed':'tests','diagnostics/recovery':'overview','diagnostics/technical':'services','diagnostics/readiness':'readiness','events/journal':'events','events/statistics':'statistics','events/traffic':'traffic','settings/main':'settings','settings/setup':'settings','help/topics':'help','help/training':'learn','help/about':'help'};
      if(typeof key==='string'&&key.indexOf('help/topic/')===0)return 'help';
      return Object.prototype.hasOwnProperty.call(aliases,key)?aliases[key]:key;
    }
    function placeHybridControls(page){
      if(appRoot)appRoot.setAttribute('data-hv-design',page==='home'?'b':currentDesign());
      if(!hybridControls)return;
      ['power','action'].forEach(function(key){
        var item=hybridControls[key];if(!item||!item.node)return;
        var target=page==='home'?item.home:item.parent;
        if(target&&item.node.parentNode!==target){
          if(page!=='home'&&item.next&&item.next.parentNode===target)target.insertBefore(item.node,item.next);
          else target.appendChild(item.node);
        }
      });
    }

    var restoredInterface=languageViewContext(window.location.href);
    if(restoredInterface){homeMenuRequested=restoredInterface==='full';try{window.history.replaceState(null,'',clearLanguageViewUrl(window.location.href));}catch(error){}}
    tabs.push(['home','',bi('Home','Главная')]);
    lazyHelpRoute(window.location.hash.slice(1));var requestedTab=hybridPage(window.location.hash.slice(1));
    if(setup||validTab(requestedTab)&&requestedTab!=='home')homeMenuRequested=true;
    var activeTab=setup?'settings':requestedTab;
    if(!setup&&!homeMenuRequested&&(!validTab(activeTab)||activeTab==='overview'||activeTab==='home'))activeTab=simpleHomeModel(data[1],inventory,statusNow(data[1])).showCard?'home':startLanding(data[1],inventory);
    if(!validTab(activeTab))activeTab='overview';
    function openHomeMenu(){homeMenuRequested=true;window.location.hash='overview';showPage('overview');}
    function goSimpleHome(){
      var model=simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));
      if(homeShortcut)homeShortcut.update(model);
      if(!model.showCard)return false;
      homeMenuRequested=false;window.location.hash='home';showPage('home');resetPageViewport(appRoot||panel,'home');return true;
    }

    var visibleRenderers=null,pageGeneration=0,pageFresh=Object.create(null),visibleAutoCard=null;
    function ensureVisiblePage(key){
      if(!visibleRenderers||!visibleRenderers[key]||pageFresh[key]===pageGeneration)return false;
      var page=pages[key];
      if(!page){page=pages[key]=E('section',{'class':'hv-page','data-hv-page':key});panel.appendChild(page);}
      while(page.firstChild)page.removeChild(page.firstChild);
      visibleRenderers[key]();
      sortableTables(page);attachStatsResets(page);
      pageFresh[key]=pageGeneration;
      return true;
    }
    function showPage(key){
      lazyHelpRoute(key);key=hybridPage(key);if(activeTab==='events'&&key!=='events')hideErrorBack();
      if(activeTab&&key!==activeTab)pageBackRemember(activeTab,window.pageYOffset||0);
      if(key==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)key=startLanding(homeLatest,inventory);

      var oldTab=activeTab;if(oldTab!==key)rememberPageViewport(appRoot||panel,oldTab);if(!validTab(key))key='overview';activeTab=key;ensureVisiblePage(key);placeHybridControls(key);if(appRoot)appRoot.setAttribute('data-hv-active',key);ensureLazyPage(key,inventory).then(function(){lazyHelpDeepLink(key);});
      var scope=appRoot||panel;scope.querySelectorAll('[data-hv-page]').forEach(function(node){node.hidden=node.getAttribute('data-hv-page')!==key;});
      if(appRoot)appRoot.querySelectorAll('[data-hv-tab]').forEach(function(node){node.setAttribute('aria-current',node.getAttribute('data-hv-tab')===key?'page':'false');});
      if(appRoot){appRoot.querySelectorAll('.hv-connectivity-control').forEach(function(node){node.hidden=key!=='overview';});}
      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);
      pageBackPlace(appRoot||panel,key);attachStatsResets(appRoot||panel);
      if(key==='overview'&&oldTab!=='overview'&&!PAGE_BACK_GOING)setTimeout(overviewToAuto,80);
      if(oldTab!==key)revisitPageViewport(appRoot||panel,key);
      if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];
      if(oldTab!==key&&heading&&document.body.contains(heading)){try{heading.focus({preventScroll:true});}catch(focusError){}}
      if(subtitle&&PAGE_SUBTITLES[key])subtitle.textContent=bi(PAGE_SUBTITLES[key][0],PAGE_SUBTITLES[key][1]);
      if(oldTab!==key&&advancedBox&&ADVANCED_KEYS.indexOf(key)>=0&&advancedBox.hidden){advancedBox.hidden=false;if(advancedToggle)advancedToggle.setAttribute('aria-expanded','true');}
    }
    function put(key,node){
      if(!pages[key]){pages[key]=E('section',{'class':'hv-page','data-hv-page':key});panel.appendChild(pages[key]);}
      pages[key].appendChild(node);return node;
    }
    function sortableTables(scope){
      (scope||panel).querySelectorAll('table').forEach(function(table,index){if(table.closest('.hv-errtable')||table.hasAttribute('data-hv-no-sort'))return;
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
      var refreshViewport=rememberPageViewport(appRoot||panel,activeTab);
      try {
      if(pointerHeld){deferredStatus=status;updateConnectivityCheck(status);return;}
      homeLatest=status;
      var controlFocus=panel.contains(document.activeElement)&&document.activeElement.matches(PAGE_FOCUS_SELECTOR)?{node:document.activeElement,page:(document.activeElement.closest('[data-hv-page]')||{dataset:{hvPage:activeTab}}).dataset.hvPage,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.textContent,tag:document.activeElement.tagName}:null;
      var focused=panel.contains(document.activeElement)&&document.activeElement.classList.contains('hv-search')?{key:document.activeElement.closest('[data-hv-page]').dataset.hvPage,start:document.activeElement.selectionStart,end:document.activeElement.selectionEnd}:null;
      updateConnectivityCheck(status);
      if(!status.rpc_error)lastGoodStatus=status;
      var rows=status.profiles||[];
      var active=rows.filter(function(p){return p.interface;}),healthy=active.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';});
      var currentMonth=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit'}).format(new Date()),month=((status.accounting||{}).months||{})[currentMonth]||null;
      var ns=status.native_failover||{state:'UNKNOWN'};
      var stateNames={'OBSERVING':bi('Automatic monitoring','Автоматический контроль'),'ARMED':bi('Ready','Готов'),'COMMITTED':bi('Reserve confirmed','Резерв подтверждён'),'STOPPED':bi('Stopped','Остановлен'),'DISABLED':bi('Disabled','Выключен'),'EXPIRED':bi('Window ended','Окно завершено'),'WAIT-CLIENT':bi('Waiting for client','Ожидание клиента'),'APPLYING':bi('Switching','Переключение'),'BLOCKED':bi('Blocked','Заблокирован')};

      if(versionBadge)versionBadge.textContent='v'+(status.version||'unknown');
      if(sideState)fillSideStatus(sideState,status,inventory);if(monitorBlockHost)fillMonitorBlock(monitorBlockHost,status,inventory);


      var homeModel=simpleHomeModel(status,inventory,statusNow(status));
      if(homeShortcut)homeShortcut.update(homeModel);
      if(homeModel.showCard){if(!setup&&!homeMenuRequested&&['start','overview','home'].indexOf(activeTab)>=0)activeTab='home';}
      else if(activeTab==='home')activeTab=startLanding(status,inventory);
      // Return the old shared buttons before replacing their card, including on Minimum.
      placeHybridControls('overview');hybridControls=null;
      var controlCard=renderAutoControl(status,inventory,function(){return statusCall().then(draw);});
      var oldAuto=visibleAutoCard;visibleAutoCard=controlCard;
      if(oldAuto&&oldAuto.parentNode)oldAuto.parentNode.replaceChild(controlCard,oldAuto);
      else put('overview',controlCard);
      var homeControl=controlCard;
      pageGeneration++;
      visibleRenderers={
        'overview':function(){
if(status.rpc_error)put('overview',E('p',{'class':'alert-message warning'},'RPC-UNAVAILABLE: displaying last known measurements. Connectivity and service state are unconfirmed.'));
      if(status.error)put('overview',E('p',{},badge(status.error)));
      var tg=status.telegram||{};if(tg.enabled&&tg.code)put('overview',E('p',{'class':'alert-message warning'},'Telegram: '+tg.code));
      put('overview',E('div',{'class':'hv-metrics'},[
        metricInfo(bi('Connected VPNs','Подключённые VPN'),active.length+bi(' of ',' из ')+rows.length,bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Your router has '+rows.length+' VPN profile(s) in this list and '+active.length+' of them are connected right now. Only connected VPNs are checked. The other ones are listed but this program never connects them.','В этом списке на роутере '+rows.length+' VPN-профилей, из них сейчас подключено '+active.length+'. Проверяются только подключённые. Остальные показаны в списке, но эта программа их никогда не подключает.')),
        metricInfo(bi('VPNs that work','VPN, которые работают'),healthy.length+bi(' of ',' из ')+active.length,bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Of the connected VPNs, this many passed the latest check: the router could open a website and resolve a name through them. This is the same number as in the coloured card at the top.','Из подключённых VPN столько прошли последнюю проверку: роутер смог открыть сайт и найти адрес через них. Это то же число, что в цветной карточке вверху.')),
        metricInfo(bi('Traffic this month','Трафик за месяц'),month?bytes(month.rx+month.tx):bi('No data','Нет данных'),bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Data that went through your VPNs since the monitor was started. It is counted from the first measurement, so the month may be incomplete.','Данные, прошедшие через ваши VPN с запуска мониторинга. Считаются с первого измерения, поэтому месяц может быть неполным.')),
        metric('Telegram',tg.enabled?(tg.code?tr("Ошибка"):tr("Каждые ")+tg.interval_minutes+tr(" мин")):tr("Отключён"),tg.last_sent?tr("Отправлен ")+new Date(tg.last_sent*1000).toLocaleTimeString():tr("Нет подтверждённой отправки"))
      ]));

put('overview',controlCard);
pages.overview.insertBefore(controlCard,pages.overview.firstChild);pages.overview.insertBefore(renderSummary(status,inventory),controlCard.nextSibling);var identityNotice=renderIdentityNotice(status);try{pages.overview.insertBefore(renderDesignOverview(currentDesign(),{status:status,inventory:inventory,rows:rows,month:month,controlCard:controlCard}),pages.overview.firstChild);pages.overview.setAttribute('data-hv-dv','1');}catch(designError){pages.overview.insertBefore(controlCard,pages.overview.firstChild);pages.overview.insertBefore(E('p',{'class':'alert-message warning'},'DESIGN-VIEW-ERROR: '+String(designError&&designError.message||designError).slice(0,120)),pages.overview.firstChild);}
      if(inventory.error)put('overview',E('p',{'class':'alert-message warning','role':'alert'},'RPC-INVENTORY-UNAVAILABLE: configuration is unknown. Reload after RPC recovery; empty defaults are not saved.'));

if(homeModel.showCard){        if(pages.overview)pages.overview.insertBefore(E('button',{'type':'button','class':'cbi-button hv-simple-return','click':goSimpleHome},bi('Return to home','На главный экран')),pages.overview.firstChild);}

        },
        'channels':function(){
      put('channels',vpnSetupCard());put('channels',renderServerSummary(status,inventory,rows));put('channels',renderVendorChannels(status,inventory));
      var cards=E('div',{'class':'hv-server-grid'}),cardHosts=channelCardHosts(rows,status,inventory,cards);
      roleOrderedRows(rows,status,inventory,Date.now()/1000).forEach(function(p){var channelUse=channelDisplayUse(p,status,inventory);cardHosts.get(p).appendChild(E('article',{'class':'hv-server hv-health-'+profileHealth(p,Date.now()/1000).state,'data-profile':p.id,'data-health':profileHealth(p,Date.now()/1000).state,'data-route-state':channelUse.state},[
        renderChannelHeader(p,status,inventory),
        E('h4',{'class':'hv-server-country'},countryLabel(p)),E('p',{'class':'hv-server-address'},endpointText(p,Date.now()/1000)),E('p',{},roleDescription(p,status,inventory)),
        E('div',{'class':'hv-latency'},[E('strong',{},profileHealth(p,Date.now()/1000).state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'),E('span',{},tr(" мс · HTTPS"))]),
        E('small',{},tr("Измерено ")+(p.time?new Date(p.time*1000).toLocaleTimeString():tr("нет данных")))
      ]));});
      if(!rows.length)cards.appendChild(E('div',{'class':'hv-empty'},tr("Подключённые серверы не обнаружены.")));
      cardHosts.finish();put('channels',cards);put('channels',renderLatencyPanel(status,inventory));
      var table=E('table',{'class':'table hv-check-table'},[E('tr',{'class':'tr table-titles'},[bi('Status','Статус'),tr("Сервер"),tr("Канал"),tr("Протокол"),tr("Интерфейс"),tr("Результат"),tr("HTTPS, мс"),tr("Время проверки")].map(function(t){return E('th',{},t);} ))]);
      currentCheckOrderedRows(rows,status,inventory,Date.now()/1000).forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[checkLampCell(p,status,inventory),currentCheckServerCell(p,Date.now()/1000),cell(roleDescription(p,status,inventory)),cell(protocolLabel(p)),cell(p.interface),E('td',{},healthBadge(p)),cell(profileHealth(p,Date.now()/1000).state==='healthy'?p.rtt_ms:null),cell(p.time?new Date(p.time*1000).toLocaleTimeString():'—')]));});
      put('channels',E('h3',{},tr("Текущие проверки серверов")));addSearch('channels',table);put('channels',limitTableRows(table,5,'current-checks-other'));
      put('channels',E('p',{},tr("Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.")));

        },
        'statistics':function(){
      put('statistics',E('section',{'class':'hv-chart-card'},[E('h3',{},tr("Задержка серверов во времени")),chart(status.samples||[],active)]));
      put('statistics',histogram(status.accounting||{},function(value){period=value;draw(status);},period));

put('statistics',renderMonitorInfo(status,inventory));

        },
        'tests':function(){
put('tests',renderCascadePath(status,inventory));
      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));
      put('tests',E('h2',{'class':'hv-speed-heading'},bi('Speed tests and server ranking','Тесты скорости и рейтинг серверов')));put('tests',E('p',{},bi('Which servers are fastest and most reliable, and the button to measure speed. If a server needs settings (budget, duration, streams), they are right below the table: change them and press the test button here.','Какие серверы быстрее и надёжнее, и кнопка замера скорости. Если нужны настройки (бюджет, длительность, потоки), они сразу под таблицей: измените их и нажмите кнопку теста здесь.')));      var samples=status.samples||[],rank={};samples.forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
      Object.keys((status.accounting||{}).quality||{}).forEach(function(id){var q=status.accounting.quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
      var ranked=rows.map(function(p){return {p:p,r:rank[p.id]||{n:0,good:0,sum:0}};}).sort(function(a,b){return (rankEnough(b.r.n)-rankEnough(a.r.n))||(b.r.n?b.r.good/b.r.n:-1)-(a.r.n?a.r.good/a.r.n:-1)||(a.r.good?a.r.sum/a.r.good:Infinity)-(b.r.good?b.r.sum/b.r.good:Infinity);});
      var ranking=E('table',{'class':'table'},[E('tr',{},[tr("Рейтинг измеренных профилей"),tr("Успех проверок"),tr("Средняя HTTPS-задержка"),bi("Checks","Проверок")].map(function(t){return E('th',{},t);}))]);
      ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(serverTitle(item.p)),cell(item.r.n?(100*item.r.good/item.r.n).toFixed(1)+'%':tr("Нет данных")),cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+tr(" мс"):'—'),cell(rankConfidence(item.r.n))]));});
      addSearch('tests',ranking);put('tests',limitTableRows(ranking,5,'server-ranking-other'));put('tests',E('p',{},bi('Servers with fewer than 20 checks are listed last: one lucky check does not make a leader.','Серверы с менее чем 20 проверками стоят в конце: одна удачная проверка не делает лидера.')));put('tests',E('p',{},tr("Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.")));

      put('tests',speedPanel(status,inventory,speedPeriod,function(value){speedPeriod=value;draw(status);}));
if(speedCardNode){put('tests',E('h3',{},bi('Speed test settings','Настройки тестов скорости')));put('tests',setupGuide('speed'));put('tests',speedCardNode);}

        },
        'traffic':function(){
      var accounting=status.accounting||{},months=accounting.months||{};
      put('traffic',E('h3',{},tr("VPN-трафик по календарным месяцам · Europe/Berlin")));
      var traffic=E('table',{'class':'table'},[E('tr',{},[tr("Месяц"),tr("Входящий"),tr("Исходящий"),tr("Всего"),tr("Наблюдение")].map(function(t){return E('th',{},t);}))]);
      Object.keys(months).sort().reverse().forEach(function(key){var v=months[key];traffic.appendChild(E('tr',{},[cell(key),cell(bytes(v.rx)),cell(bytes(v.tx)),cell(bytes(v.rx+v.tx)),cell((v.seconds/3600).toFixed(1)+tr(" интерфейс-часов")+(v.boundary_estimated?tr(" · граница оценена"):''))]));});
      put('traffic',traffic);put('traffic',E('p',{},tr("Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ")+text(accounting.gaps||0)+tr(". После потери питания возможна потеря последнего интервала checkpoint.")));
      put('traffic',trafficHistoryPanel(status.accounting||{}));

        },
        'services':function(){
      put('services',E('h3',{},tr("Монитор служб")));

      put('services',renderLiveLog(status,rows,ns,inventory,stateNames));
      var terminalExplanation=E('details',{'class':'hv-chart-card','data-live-explanation':'scope'},[
        E('summary',{},bi('About router observations and the LAN test','О наблюдениях роутера и LAN-тесте')),
        E('p',{},bi('The terminal shows real router observations. A separate optional LAN-helper test checks what a client sees; it is not required for prepared router-probed Auto mode.','Терминал показывает реальные наблюдения роутера. Отдельный необязательный LAN-тест проверяет связь клиента; для подготовленного router-probed авторежима он не обязателен.'))]);
      if(typeof rememberDisclosure==='function')rememberDisclosure(terminalExplanation,'live-terminal-explanation');
      put('services',terminalExplanation);

        },
        'events':function(){
put('events',renderEventHistory(status));
put('events',renderTransitionAnalytics(status,inventory));
put('events',renderVendorEvents(status,inventory));      put('events',E('button',{'class':'btn','click':function(){var blob=new Blob([JSON.stringify({mode:'router-monitor',events:status.events||[]},null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),link=E('a',{href:url,download:'homensai-vpn-events.json'});link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}},tr("Скачать журнал")));
put('events',errorTable||(errorTable=renderErrorTable()));

        },
        'settings':function(){
      var nativePanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Automatic switching · LAN trial','Автопереключение · LAN-тест')),E('strong',{},stateNames[ns.state]||ns.state||'UNKNOWN'),E('p',{},bi('Auto can be started only after a passed LAN trial. The Overview page shows exactly which step is missing. The helper runs on a Windows computer with PowerShell 7 connected to the LAN; it checks the gateway, router DNS, HTTPS and the VPN exit, and asks before it starts. Browser checks alone do not certify the LAN path.','Авторежим можно запустить только после успешного LAN-теста. Страница «Обзор» показывает, какого именно шага не хватает. Помощник запускается на компьютере Windows с PowerShell 7 в локальной сети: он проверяет шлюз, DNS роутера, HTTPS и VPN-выход и спрашивает подтверждение перед началом. Проверка только браузером не подтверждает путь LAN.'))]);
      var reasons=E('ul',{});(ns.blockers||[]).forEach(function(code){reasons.appendChild(E('li',{},code+' · '+autoBlockerText(code)));});nativePanel.appendChild(reasons);
      nativePanel.appendChild(lanHelperExplain());nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')));nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/start-lan-helper.ps1'),'download':'start-lan-helper.ps1'},bi('Download launcher','Скачать запуск')));
      nativePanel.appendChild(E('p',{},[bi('Stop Auto or return to the primary on the Overview, in the Automatic VPN failover card. ','Остановить Auto или вернуться на основной можно на «Обзоре», в блоке «Автоматическое переключение VPN». '),E('a',{'href':'#overview'},bi('Open the Overview','Открыть «Обзор»'))]));
      put('settings',nativePanel);

        },
        'home':function(){
      if(homeModel.showCard){
        var power=homeControl&&homeControl.querySelector('.hv-auto-power'),action=homeControl&&homeControl.querySelector('.hv-auto-action');
        var powerParent=power&&power.parentNode,powerNext=power&&document.createComment('Auto power position'),actionParent=action&&action.parentNode,actionNext=action&&document.createComment('Auto action position');
        if(powerParent)powerParent.insertBefore(powerNext,power);if(actionParent)actionParent.insertBefore(actionNext,action);
        var homeView=renderSimpleHome(status,inventory,homeModel,homeControl,openHomeMenu);
        put('home',homeView);
        hybridControls={power:{node:power,parent:powerParent,next:powerNext,home:homeView.querySelector('.hv-simple-power')},action:{node:action,parent:actionParent,next:actionNext,home:homeView.querySelector('.hv-simple-power-unit')}};
        hybridRenderedState=JSON.stringify([homeModel.state,homeModel.title,homeModel.summary,homeModel.selectedRole,homeModel.targetHealth.state]);


      }
        },
        'readiness':function(){
put('readiness',readinessIntro());
put('readiness',renderReadiness(status,inventory));
        },
        'help':function(){
put('help',helpNode||(helpNode=renderHelp(inventory)));
        },
        'learn':function(){
put('learn',learnNode||(learnNode=renderLearn()));
        },
        'start':function(){
put('start',renderStartPage(status,inventory));
        }
      };
      showPage(activeTab);
      restorePageControlFocus(pages,controlFocus);
      if(focused){var input=pages[focused.key]&&pages[focused.key].querySelector('.hv-search');if(input){input.focus();input.setSelectionRange(focused.start,focused.end);}}
      } finally {if(refreshViewport&&refreshViewport.page===activeTab)restorePageViewport(appRoot||panel,refreshViewport);}
    }
    draw(data[1]);
    var hvStatusTick=function(){if(typeof document!=='undefined'&&document.hidden)return Promise.resolve();return statusCall().then(function(fresh){try{draw(fresh);}catch(error){uiRenderFailed(error);}},function(){try{draw(Object.assign({},lastGoodStatus,{rpc_error:'RPC-UNAVAILABLE',server_time:typeof routerWall==='function'?routerWall():Date.now()/1000}));}catch(error){uiRenderFailed(error);}});};poll.add(hvStatusTick,10);if(typeof document!=='undefined'&&typeof document.addEventListener==='function')document.addEventListener('visibilitychange',function(){if(!document.hidden)hvStatusTick();});
    return Promise.resolve(E('p',{},bi('Use the setup wizards below. Settings are validated before saving; stored tokens are never loaded into this page.','Используйте мастера ниже. Настройки проверяются до сохранения; сохранённые токены не загружаются на эту страницу.'))).then(function(formNode){
      var robotHost=E('div',{'class':'robo','aria-label':bi('HomenS.AI author robot','Робот автора HomenS.AI')});
      var footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');
      setTimeout(function(){var robot=window.HomenS.robot.tvRobot(robotHost);robot.play();},0);
      var language=E('select',{'aria-label':bi('Language','Язык')},[E('option',{value:'en',selected:locale==='en'?'':null},'English'),E('option',{value:'ru',selected:locale==='ru'?'':null},'Русский')]);language.value=locale;
      language.addEventListener('change',function(){var chosen=language.value==='ru'?'ru':'en';try{localStorage.setItem('homensai-vpn-language',chosen);}catch(e){}window.location.assign(languageNavigationUrl(window.location.href,chosen,activeTab));});
      versionBadge=E('span',{'class':'hv-version','aria-label':bi('Program version','Версия программы')},'v'+(data[1].version||'unknown'));
      heading=E('h1',{'tabindex':'-1'},bi('Your internet under control','Ваш интернет под контролем'));
      sideState=E('div',{'class':'hv-side-status'});fillSideStatus(sideState,data[1],inventory);
      settingsHost=E('section',{'class':'hv-settings','data-hv-page':'settings'},[E('h3',{},bi('Monitoring, Telegram and profile names','Мониторинг, Telegram и названия профилей')),E('a',{'href':L.url('admin/services/homensai-vpn')+'?setup=telegram&lang='+locale+'#settings'},bi('Telegram setup wizard','Мастер настройки Telegram')),setup?E('p',{},bi('Create a bot with BotFather, send /start, then enter its token and your Chat ID. The token stays on the router and is never returned in status.','Создайте бота через BotFather, отправьте /start, затем введите токен и свой Chat ID. Токен хранится на роутере и не возвращается в статусе.')):null,formNode].filter(function(node){return node!=null;}));
      function tabLink(key){var tab=tabs.filter(function(t){return t[0]===key;})[0];return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'title':tab[2],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);}
      var advancedOpen=false;try{advancedOpen=localStorage.getItem('homensai-vpn-advanced')==='1';}catch(e){}
      if(ADVANCED_KEYS.indexOf(activeTab)>=0)advancedOpen=true;
      advancedBox=E('div',{'class':'hv-advanced-links','id':'hv-advanced-links'},ADVANCED_KEYS.map(tabLink));advancedBox.hidden=!advancedOpen;
      advancedToggle=E('button',{'type':'button','class':'hv-advanced-toggle','aria-controls':'hv-advanced-links','aria-expanded':advancedOpen?'true':'false','aria-label':bi('Advanced settings','Расширенные настройки'),'title':bi('Advanced settings','Расширенные настройки'),'click':function(){var open=advancedBox.hidden;advancedBox.hidden=!open;advancedToggle.setAttribute('aria-expanded',open?'true':'false');try{localStorage.setItem('homensai-vpn-advanced',open?'1':'0');}catch(e){}}},[E('span',{'class':'hv-advanced-icon','aria-hidden':'true'},'☰'),E('span',{'class':'hv-advanced-label'},bi('Advanced settings','Расширенные настройки'))]);
      var links=['start','readiness','overview','channels','settings','help','learn'].map(tabLink).concat([advancedToggle,advancedBox]);
      appRoot=E('div',{'class':'hv-app hv-workspace hv-hybrid-release','data-hv-design':currentDesign()},[E('a',{'class':'hv-skip','href':'#','click':function(ev){ev.preventDefault();var m=appRoot.querySelector('main');if(m){m.setAttribute('tabindex','-1');m.focus();}}},bi('Skip to content','К содержимому')),
        E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/charts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui94.css')+'?build=080-alpha8'}),
        E('aside',{'class':'hv-sidebar'},[E('a',{'class':'hv-side-brand','href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer','aria-label':bi('HomenS.AI website','Сайт HomenS.AI')},[robotHost,E('span',{},[E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI')]),E('small',{},'Auto VPN')])]),E('p',{'class':'hv-model'},routerModelLabel()),E('nav',{'id':'hv-expanded-nav','aria-label':bi('VPN sections','Разделы VPN')},links),E('div',{'class':'hv-side-footer'},[sideState,E('small',{},bi('Real IPv4 router measurements','Реальные IPv4-измерения роутера')),E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),E('small',{'class':'hv-identity'},identityLine(data[1]))])]),
        E('main',{'class':'hv-main'},[E('header',{'class':'hv-page-header'},[E('div',{'class':'hv-header-main','style':'min-width:0;max-width:100%'},[E('div',{'class':'hv-eyebrow'},bi('AVAILABILITY CONTROL','УПРАВЛЕНИЕ ДОСТУПНОСТЬЮ')),E('div',{'class':'hv-heading-row'},[heading,(homeShortcut=renderSimpleHomeShortcut(function(){return simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));},goSimpleHome))]),(subtitle=E('p',{},bi('Your VPNs, how healthy they are, and what the router did about it.','Ваши VPN, насколько они исправны и что сделал роутер.')))].filter(function(node){return node!=null;})),E('div',{'class':'hv-page-actions'},[versionBadge,language,renderThemeSelect()])]),panel,settingsHost,renderAttribution(data[1]),footer])
      ]);
      settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-card-monitor'},[E('h3',{},bi('Monitor service','Служба мониторинга')),E('p',{},bi('Turns the background checks on or off. Stop Auto and wait for it to hand control back before turning the checks off. The real state is confirmed by fresh results.','Включает или выключает фоновые проверки. Перед выключением остановите Auto и дождитесь, пока он вернёт управление. Реальное состояние подтверждают свежие результаты.')),E('button',{'type':'button','class':'cbi-button','click':function(ev){ev.target.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'monitor_control',params:['enabled'],expect:{}})(!(inventory.settings||{}).enabled).then(function(result){ui.addNotification(null,E('p',{},result.code||'MONITOR-UNKNOWN'));if(result.accepted)window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){ev.target.disabled=false;});}},(inventory.settings||{}).enabled?bi('Stop monitor','Остановить мониторинг'):bi('Start monitor','Запустить мониторинг'))]));
      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){recoveryWizard(inventory);}},bi('Recovery setup wizard','Мастер восстановления')));
      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){monitorPreferences(inventory);}},bi('Monitoring and history retention','Мониторинг и хранение истории')));
      settingsHost.appendChild(speedSettings(inventory));
      settingsHost.insertBefore(E('div',{'class':'hv-wizard-launch'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){setupWizard(inventory,'system');}},bi('System setup wizard','Мастер настройки системы')),E('button',{'type':'button','class':'cbi-button','click':function(){setupWizard(inventory,'telegram');}},bi('Telegram channel wizard','Мастер Telegram-канала')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'TELEGRAM-TEST-UNKNOWN'));});}},bi('Test Telegram delivery','Проверить доставку Telegram'))]),settingsHost.firstChild);
      (function(){
        var monitorCard=settingsHost.querySelector('.hv-card-monitor'),speedCard=settingsHost.querySelector('.hv-speed-settings');
        while(settingsHost.firstChild)settingsHost.removeChild(settingsHost.firstChild);
        function launcher(label,hint,action,primary,guide,lockKey){return E('div',{'class':'hv-setup-item'},[guardResume(E('button',{'type':'button','class':'cbi-button'+(primary?' cbi-button-action':''),'click':action},label),lockKey),E('p',{},hint),guide?setupGuide(guide):null].filter(Boolean));}
        var testDelivery=function(ev){return telegramTestDelivery(ev.currentTarget||ev.target);};
        settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-setup-card'},[
          E('h3',{},bi('Setup','Настройка')),
          E('button',{'type':'button','class':'cbi-button cbi-button-action','data-onboarding-action':'open','click':function(){openOnboardingSettings(inventory,lastGoodStatus||data[1]);}},bi('All application settings','Все настройки приложения')),
          E('button',{'type':'button','class':'cbi-button','data-onboarding-action':'open-pair','click':function(){openOnboardingSettings(inventory,lastGoodStatus||data[1],'system');}},bi('Choose primary and reserve VPN','Выбрать основной и резервный VPN')),
          !onboardingComplete(inventory)?E('p',{'class':'alert-message warning','data-onboarding-incomplete':'1'},bi('Initial setup is incomplete. Open All application settings to review and save it. Stop and recovery controls remain available.','Первоначальная настройка не завершена. Откройте «Все настройки приложения», проверьте и сохраните её. Остановка и средства восстановления остаются доступны.')):null,
          E('p',{},bi('Simple settings for every user. Every wizard validates your input and shows a review before saving. Stored tokens are never shown again. Open “What is this and how to fill it in” under a step for examples.','Простые настройки для любого пользователя. Каждый мастер проверяет ввод и показывает обзор перед сохранением. Сохранённые токены больше не показываются. Под каждым шагом есть «Что это и как заполнить» с примерами.')),
          E('p',{'class':'hv-setup-path','aria-label':bi('Order of the steps','Порядок шагов')},[E('b',{},bi('1 · System setup','1 · Настройка системы')),E('span',{'aria-hidden':'true'},' → '),E('b',{},bi('2 · Telegram','2 · Telegram')),E('span',{'aria-hidden':'true'},' → '),E('b',{},bi('3 · Test delivery','3 · Проверка доставки')),E('small',{},bi('Press a button below to open its wizard.','Нажмите кнопку ниже, чтобы открыть мастер.'))]),
          E('div',{'class':'hv-setup-grid hv-setup-steps'},[
            launcher(bi('Auto switching rules','Правила переключения Auto'),bi('Check interval, failures, reserve readiness, attempt limit and return conditions. Stop Auto before saving.','Интервал проверок, ошибки, готовность резерва, лимит попыток и условия возврата. Перед сохранением выключите Auto.'),function(){recoveryWizard(inventory);},false,'recovery'),
            launcher(bi('1 · System setup','1 · Настройка системы'),bi('Press to open the wizard: primary and reserve VPN, names, groups, priorities and whether a short reconnection is acceptable.','Нажмите, чтобы открыть мастер: основной и резервный VPN, названия, группы, приоритеты и допустимость короткого переподключения.'),function(){setupWizard(inventory,'system');},true,'system'),
            launcher(bi('2 · Telegram channel','2 · Канал Telegram'),bi('Press to open the wizard: bot token and chat for reports. The wizard explains how to get both.','Нажмите, чтобы открыть мастер: токен бота и чат для отчётов. Мастер объясняет, как получить и то и другое.'),function(){setupWizard(inventory,'telegram');},false,'telegram'),
            launcher(bi('3 · Test Telegram delivery','3 · Проверить доставку Telegram'),bi('Press to send one test message with the saved settings. It should arrive within a few seconds.','Нажмите, чтобы отправить одно тестовое сообщение с сохранёнными настройками. Оно должно прийти за несколько секунд.'),testDelivery,false,null,'telegram-test')
          ])].filter(function(node){return node!=null;})));
        settingsHost.appendChild(renderDesignPicker(function(){return appRoot;},function(){updateSidebarLayout(appRoot,true);draw(lastGoodStatus||data[1]);}));
        settingsHost.appendChild(E('details',{'class':'hv-chart-card hv-admin-settings'},[
          E('summary',{},bi('Advanced settings','Расширенные настройки')),
          E('p',{},bi('Fine-tuning of the switching rules and of the checks. The defaults are safe; change them only if you know why. Open the guide under each step for examples.','Тонкая настройка правил переключения и проверок. Значения по умолчанию безопасны; меняйте их, только если понимаете зачем. Под каждым шагом есть руководство с примерами.')),
          E('div',{'class':'hv-setup-grid'},[
            launcher(bi('Recovery rules','Правила восстановления'),bi('Failures before switching, reserve checks, cooldown and return policy.','Сколько сбоев до переключения, проверки резерва, пауза и политика возврата.'),function(){recoveryWizard(inventory);},false,'recovery'),
            launcher(bi('Monitoring parameters','Параметры мониторинга'),bi('Check interval, profile limit and statistics saving.','Интервал проверок, лимит профилей и сохранение статистики.'),function(){monitorPreferences(inventory);},false,'monitoring')
          ])]));
        if(speedCard){speedCardNode=speedCard;speedCard.setAttribute('id','hv-speed-settings');put('tests',E('h3',{},bi('Speed test settings','Настройки тестов скорости')));put('tests',setupGuide('speed'));put('tests',speedCard);}
      })();
      panel.addEventListener('pointerdown',function(){pointerHeld=true;});
      ['pointerup','pointercancel'].forEach(function(event){window.addEventListener(event,function(){if(!pointerHeld)return;setTimeout(function(){pointerHeld=false;if(deferredStatus){var next=deferredStatus;deferredStatus=null;draw(next);}},0);});});
      var homeFreshTimer=window.setInterval(function(){
        if(!appRoot||!appRoot.isConnected){window.clearInterval(homeFreshTimer);return;}
        if(homeShortcut)homeShortcut.update();
        if(activeTab==='home'){var timed=simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));var key=JSON.stringify([timed.state,timed.title,timed.summary,timed.selectedRole,timed.targetHealth.state]);if(key!==hybridRenderedState)draw(homeLatest);}
      },1000);
      if(homeShortcut)homeShortcut.update();
      showPage(activeTab);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});
      initSidebarLayout(appRoot);installViewportPersistence(appRoot,function(){return activeTab;});installSpeedLive(appRoot,function(){return activeTab;});installErrorLinks(appRoot);installModalStyle();installTopButton(appRoot);installDesignKeys(appRoot,tabs.map(function(t){return t[0];}),function(k){window.location.hash=k;showPage(k);});
      return appRoot;
    });
  }
});