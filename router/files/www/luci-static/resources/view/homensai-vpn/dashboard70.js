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
  'recovery.primary_stable':[30,600,'seconds','секунд']
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
var MANUAL_SWITCH_PENDING=false;
function manualFresh(time,now,limit){return Number.isFinite(time)&&now-time>=-5&&now-time<=limit;}
function manualConfirmedPath(status,source,target,now){
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  if(status.rpc_error||status.error||!manualFresh(status.time,now,90))return neutral;
  var pairNative=status.native_failover||{};
  if(pairNative.mode==='continuous-pair'&&pairNative.proof_scope==='router-probed-ipv4'&&source&&target&&source.id!==target.id&&pairNative.source===source.id&&pairNative.target===target.id&&manualFresh(pairNative.time,now,30)){
    var moving=['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(pairNative.state)>=0;
    var pairSelected=pairNative.state==='OBSERVING'&&pairNative.readiness_verified===true?'source':['COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE'].indexOf(pairNative.state)>=0?'target':null;
    if(moving)return {source:'checking',target:'checking',direction:'forward',moving:true,selected:null};
    if(pairSelected)return {source:'ready',target:'ready',direction:pairSelected==='target'?'forward':'none',moving:false,selected:pairSelected};
  }
  var route=status.channel_path;
  if(route){
    if(!manualFresh(route.time,now,30)||!source||!target||source.id===target.id||route.source_profile_id!==source.id||route.target_profile_id!==target.id)return neutral;
    if(route.transitioning===true)return {source:'checking',target:'checking',direction:'forward',moving:true,selected:null};
    var selected=route.confirmed===true?(route.active_profile_id===source.id?'source':route.active_profile_id===target.id?'target':null):null;
    return {source:selected?'ready':'neutral',target:selected?'ready':'neutral',direction:selected==='target'?'forward':'none',moving:false,selected:selected};
  }
  // Legacy native confirmation remains usable only with fresh monitor/controller evidence.
  var ns=status.native_failover||{};
  if(!source||!target||ns.source&&ns.source!==source.id||ns.target&&ns.target!==target.id)return neutral;
  var path=autoPathModel(status,source,target,now),model=autoControlModel(status,now);
  if(model.fresh&&model.off&&ns.original_restored===true&&source&&target&&source.id!==target.id)path.selected='source';
  if(model.fresh&&ns.state==='STOPPED-ON-RESERVE'&&source&&target&&source.id!==target.id&&ns.original_restored===false)path.selected='target';
  return path;
}
function manualChannelTone(profile,key,path,now){
  var health=profile?profileHealth(profile,now).state:'unknown',selected=path.selected===key;
  if(!profile)return {color:'grey',text:bi('Not chosen','Не выбран'),carrier:false};
  if(path.moving)return {color:'yellow',text:bi('Switching · awaiting confirmation','Переключение · ожидается подтверждение'),carrier:false};
  if(!path.selected&&(health==='failed'||health==='inactive'))return {color:'red',text:health==='failed'?bi('Not working','Не работает'):bi('Not connected','Не подключён'),carrier:false};
  if(!path.selected||health==='unknown'||health==='checking')return {color:'grey',text:bi('No fresh path confirmation','Нет свежего подтверждения пути'),carrier:false};
  if(selected&&health==='healthy')return {color:'green',text:bi('In use · works','Используется · работает'),carrier:true};
  if(selected)return {color:'red',text:health==='failed'?bi('In use · connectivity failed','Используется · ошибка доступности'):bi('Selected tunnel is not connected','Выбранный туннель не подключён'),carrier:true};
  if(health==='healthy')return {color:'yellow',text:bi('Waiting · ready','Ожидает · готов'),carrier:false};
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
      'PAIR-RATE-LIMIT':['Three forward attempts per 15 minutes have been used. Wait; Stop and return remain available.','Использованы три попытки за 15 минут. Подождите; Stop и возврат остаются доступны.'],
      'PAIR-MANUAL-TARGET-UNHEALTHY':['The reserve has no fresh successful DNS/HTTPS confirmation. It will not be selected.','У резерва нет свежего успешного подтверждения DNS/HTTPS. Он не будет выбран.'],
      'PAIR-MANUAL-BUSY':['A transition or request is already in progress. Emergency Stop remains available.','Переключение или запрос уже выполняется. Аварийный стоп остаётся доступен.']};
    if(Object.prototype.hasOwnProperty.call(pairNotes,code))return bi(pairNotes[code][0],pairNotes[code][1]);
    var row=typeof ERROR_EXTRA_ROWS!=='undefined'?ERROR_EXTRA_ROWS.filter(function(item){return item[0]===code;})[0]:null;
    if(row)return bi(row[4],row[5])+(row[6]?' '+bi(row[6],row[7]):'');
    return typeof AUTO_BLOCKERS!=='undefined'&&Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?autoBlockerText(code):bi('Switching is currently unavailable.','Переключение сейчас недоступно.');}).filter(function(text,index,all){return all.indexOf(text)===index;}).join(' ');
}
function manualSelectionModel(status,source,target,now){
  var native=status.native_failover||{};
  if(!status.rpc_error&&manualFresh(status.time,now,90)&&manualFresh(native.time,now,30)&&['STOPPED','DISABLED','EXPIRED'].indexOf(native.state)>=0&&source&&target&&profileHealth(source,now).state==='inactive'&&profileHealth(target,now).state==='inactive')return {selected:null,moving:false,off:true};
  var route=status.channel_path;
  if(route){
    var valid=!status.rpc_error&&!status.error&&manualFresh(status.time,now,90)&&manualFresh(route.time,now,30)&&source&&target&&source.id!==target.id&&route.source_profile_id===source.id&&route.target_profile_id===target.id;
    return {selected:valid&&route.confirmed===true?(route.active_profile_id===source.id?'primary':route.active_profile_id===target.id?'reserve':null):null,moving:valid&&route.transitioning===true};
  }
  var path=manualConfirmedPath(status,source,target,now);
  return {selected:path.selected==='source'?'primary':path.selected==='target'?'reserve':null,moving:path.moving};
}
function renderManualSwitch(status,inventory){
  var now=Date.now()/1000,model=manualControlModel(status,now),buttons=[],settings=(inventory||{}).settings||{},ns=status.native_failover||{},route=status.channel_path||{},profiles=status.profiles||[];
  var source=profiles.filter(function(p){return p.id===(settings.plan_source||route.source_profile_id||ns.source);})[0],target=profiles.filter(function(p){return p.id===(settings.plan_target||route.target_profile_id||ns.target);})[0];
  var selection=manualSelectionModel(status,source,target,now);
  function notice(text){ui.addNotification(null,E('p',{},text));}
  function button(direction,label){
    var enabled=model[direction].allowed,n=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-manual-direction':direction,'disabled':enabled?null:'','click':function(){
      if(MANUAL_SWITCH_PENDING||!enabled||!manualControlModel(status,Date.now()/1000)[direction].allowed)return;
      MANUAL_SWITCH_PENDING=true;buttons.forEach(function(node){node.disabled=true;});var request;
      try{var call=model.mode==='continuous-pair'?rpc.declare({object:'homensai-vpn',reject:true,reject:true,method:'pair_manual',params:['direction','control_revision'],expect:{}}):rpc.declare({object:'homensai-vpn',reject:true,reject:true,method:'manual_switch',params:['direction','control_revision'],expect:{}});request=call(direction,model.revision);}catch(e){request=Promise.reject(e);}
      return Promise.resolve(request).then(function(result){
        if(result&&result.accepted===true&&result.queued===true&&result.completed===false&&typeof result.request_id==='string'&&/^[a-f0-9]{32}$/.test(result.request_id))notice(model.mode==='continuous-pair'?bi('Request queued. Wait for confirmed completion. Auto stays on; a manual channel choice is held until Resume Auto or a confirmed failure requires recovery.','Запрос поставлен в очередь. Дождитесь подтверждения. Auto остаётся включённым; выбранный канал удерживается до возврата к Auto либо подтверждённого отказа, требующего восстановления.'):bi('Manual switch requested. Wait for the router to confirm the active path. This request does not enable Auto.','Ручное переключение запрошено. Дождитесь подтверждения активного пути роутером. Этот запрос не включает Auto.'));
        else notice(manualReason(result&&Array.isArray(result.blockers)?result.blockers.filter(function(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}):[]));
      }).catch(function(){notice(bi('The request was not confirmed. Refresh the router state before trying again.','Запрос не подтверждён. Обновите состояние роутера перед повтором.'));}).finally(function(){MANUAL_SWITCH_PENDING=false;buttons.forEach(function(node){node.disabled=true;});});
    }},label);buttons.push(n);return n;
  }
  function choice(direction,profile,role){
    var selected=selection.selected===direction,pending=model.busy||selection.moving;
    var color=pending?'yellow':selection.off?'red':selection.selected?(selected?'green':'red'):'yellow';
    var protocol=profile?(typeof protocolLabel==='function'?protocolLabel(profile):profile.protocol==='wireguard'?'WireGuard':'OpenVPN'):bi('Profile not chosen','Профиль не выбран');
    var health=profile?profileHealth(profile,now).state:'unknown';
    var healthText=health==='healthy'?bi('Internet: available','Интернет: доступен'):health==='failed'?bi('Internet: check failed','Интернет: проверка не пройдена'):health==='inactive'?bi('VPN tunnel: disconnected','VPN-туннель: отключён'):bi('Internet: awaiting check','Интернет: ожидается проверка');
    var text=pending?bi('Switching…','Переключение…'):selection.off?bi('Off','Выключено'):selected?bi('Selected channel','Выбранный канал'):selection.selected?bi('Not selected','Не выбран'):bi('Router selection is being checked','Проверяется выбор канала роутера');
    var country=profile&&typeof countryLabel==='function'?countryLabel(profile):null;
    var card=button(direction,[E('small',{},role),E('strong',{'class':'hv-manual-protocol'},protocol),country?E('span',{},country):null,E('span',{'class':'hv-manual-selection'},text),E('small',{'class':'hv-manual-health hv-health-'+health},healthText),E('b',{'class':'hv-manual-enable'},bi('Turn on','Включить'))].filter(Boolean));
    card.setAttribute('class','hv-manual-channel hv-manual-'+color);card.setAttribute('aria-pressed',selected?'true':'false');card.setAttribute('data-selected',selected?'true':'false');
    if(selected&&!pending)card.disabled=true;
    return E('div',{'class':'hv-manual-choice'},[card,!selected&&!model[direction].allowed&&!model.busy?E('p',{'class':'hv-step-note'},manualReason(model[direction].blockers)):null].filter(Boolean));
  }
  return E('section',{'class':'hv-chart-card hv-manual-switch','data-manual-controls':'1'},[
    E('h3',{},bi('Manual channel switch','Ручное переключение канала')),
    E('p',{},model.mode==='continuous-pair'?bi('Choose a channel even while Auto is on. Green is selected, red is not selected, yellow is a command in progress or selection check. Internet health is shown separately. A healthy manual choice is held until Resume Auto; confirmed failure can release the hold.','Выбирайте канал и при включённом Auto. Зелёный — выбран, красный — не выбран, жёлтый — выполняется команда или уточняется выбор. Проверка Интернета показана отдельно. Исправный ручной выбор удерживается до возврата к Auto; подтверждённый отказ может снять удержание.'):bi('Choose the primary or reserve channel. Green is selected, red is not selected, yellow means awaiting the router. Internet health is separate.','Выберите основной или резервный канал. Зелёный — выбран, красный — не выбран, жёлтый — ожидается ответ роутера. Проверка Интернета показана отдельно.')),
    E('div',{'class':'hv-manual-channel-grid'},[choice('primary',source,bi('Primary channel','Основной канал')),choice('reserve',target,bi('Reserve channel','Резервный канал'))]),
    !selection.selected&&!selection.moving&&!selection.off?E('p',{'role':'status'},bi('The router has not returned a verified channel selection yet. Updating its policy state; no channel is assumed active from a button press.','Роутер ещё не передал проверенный выбор канала. Обновляем состояние маршрутизации; нажатие кнопки само по себе не означает, что канал выбран.')):null,
    model.mode==='continuous-pair'?E('div',{'class':'hv-wizard-actions'},[button('resume',bi('Resume automatic control','Вернуться к автоматическому управлению')),E('p',{},model.hold==='target'?bi('Manual hold: reserve','Ручное удержание: резерв'):model.hold==='source'?bi('Manual hold: primary','Ручное удержание: основной'):bi('Automatic control is active','Автоматическое управление активно'))]):null,
    model.busy?E('p',{'role':'status'},bi('A switch request is pending. Wait for confirmation or use Emergency Stop.','Запрос переключения ожидает подтверждения. Дождитесь результата или нажмите «Аварийный стоп».')):null
  ].filter(Boolean));
}

/* Live selected-route timeline. It does not invent throughput or LAN health. */
var autoLivePoints=[],autoLiveKey='',autoLiveContext=null,autoLivePollAdded=false,autoLiveCall=null;
var AUTO_LIVE_COLORS={source:'#16a34a',target:'#2563eb',off:'#64748b'};
function autoLiveSample(status,now){
  status=status||{};
  var ns=(status||{}).native_failover||{},valid=Number.isFinite(now)&&!status.rpc_error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var kind='unknown',state=String(ns.state||'UNKNOWN');
  if(valid){
    if(state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true))kind='source';
    else if(['COMMITTED','DEGRADED-ON-RESERVE','STOPPED-ON-RESERVE'].indexOf(state)>=0)kind='target';
    else if(['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(state)>=0)kind='switching';
    else if(['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(state)>=0)kind='off';
  }
  return {time:now,stamp:valid?ns.time:null,kind:kind,state:state};
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
function autoLiveLabel(kind){return kind==='source'?bi('Primary selected','Выбран основной'):kind==='target'?bi('Reserve selected','Выбран резерв'):kind==='switching'?bi('Starting / switching / restoring','Запуск / переключение / восстановление'):kind==='off'?bi('Auto off','Auto выключен'):bi('No fresh confirmation','Нет свежего подтверждения');}
function autoLiveSvg(tag,attributes,text){
  var node=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.keys(attributes||{}).forEach(function(key){node.setAttribute(key,String(attributes[key]));});
  if(text!==undefined)node.textContent=text;
  return node;
}
function drawAutoLive(root,status,inventory){
  var now=Date.now()/1000,settings=(inventory||{}).settings||{},ns=(status||{}).native_failover||{};
  var key=[settings.plan_source||ns.source||'',settings.plan_target||ns.target||''].join('|');
  if(key!==autoLiveKey){autoLivePoints=[];autoLiveKey=key;}
  var sample=autoLiveSample(status,now);autoLivePoints=autoLiveAppend(autoLivePoints,sample);
  var width=Math.max(280,Math.min(720,root.clientWidth||document.documentElement.clientWidth-80||720));
  var points=autoLiveDisplayPoints(autoLivePoints),from=Math.max(now-1800,Math.min(now-60,points.length?points[0].time:now-60)),span=now-from,left=width<480?88:122,right=width-16;
  var displayed=points.length?points[points.length-1]:sample;
  var x=function(t){return left+(t-from)/span*(right-left);};
  var y=function(kind){return kind==='source'?44:kind==='target'?91:132;};
  var svg=autoLiveSvg('svg',{viewBox:'0 0 '+width+' 168',width:'100%',height:'168',role:'img','aria-label':bi('Live selected VPN route over time','Выбранный VPN-маршрут в реальном времени')});
  [['source',bi('Primary','Основной')],['target',bi('Reserve','Резерв')],['off',bi('Off','Выключено')]].forEach(function(row){var yy=y(row[0]);svg.appendChild(autoLiveSvg('line',{x1:left,y1:yy,x2:right,y2:yy,stroke:'#cbd5e1','stroke-dasharray':'3 5'}));svg.appendChild(autoLiveSvg('text',{x:6,y:yy+4,fill:'currentColor','font-size':12},row[1]));});
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
  root.appendChild(E('p',{'class':'hv-muted'},bi('Green: primary · Blue: reserve · Grey: off. During a transition the last confirmed route is held until a new one is confirmed; missing observations leave a gap. Updated every 2 seconds while open. This shows confirmed route selection, not bandwidth or external-LAN verification.','Зелёный: основной · Синий: резерв · Серый: выключено. При переходе остаётся последний подтверждённый маршрут до подтверждения нового; отсутствие данных показано разрывом. Обновление каждые 2 секунды, пока страница открыта. График показывает подтверждённый выбор маршрута, а не скорость или проверку внешнего LAN.')));
}
function renderAutoLive(status,inventory){
  var root=E('div',{'id':'hv-auto-live-chart','class':'hv-auto-live-chart'});
  autoLiveContext={status:status,inventory:inventory};drawAutoLive(root,status,inventory);
  if(!autoLivePollAdded&&typeof poll!=='undefined'){
    autoLivePollAdded=true;
    poll.add(function(){
      var node=document.getElementById('hv-auto-live-chart');
      if(!node||!node.getClientRects().length)return Promise.resolve();
      if(!autoLiveCall)autoLiveCall=rpc.declare({object:'homensai-vpn',reject:true,method:'auto_live',expect:{}});
      return autoLiveCall().then(function(live){if(document.getElementById('hv-auto-live-chart')===node)drawAutoLive(node,live,autoLiveContext.inventory);}).catch(function(){if(document.getElementById('hv-auto-live-chart')===node)drawAutoLive(node,{rpc_error:true},autoLiveContext.inventory);});
    },2);
  }
  return root;
}
function autoDaySegments(history,now){
  if(!history||!Array.isArray(history.segments)||!Number.isFinite(now))return [];
  var last=null,previousEnd=null,rows=[];
  history.segments.slice(-4096).forEach(function(row){
    if(!row||['source','target','off','unknown','switching'].indexOf(row.kind)<0||!Number.isFinite(row.start)||!Number.isFinite(row.end)||row.start>row.end||row.end<=now-86400||row.start>now||row.end>now+5){last=null;previousEnd=null;return;}
    if(previousEnd!==row.start)last=null;
    var kind=row.kind==='switching'?last:row.kind;
    previousEnd=row.end;
    if(!AUTO_LIVE_COLORS[kind]){last=null;return;}
    last=kind;rows.push({start:Math.max(now-86400,row.start),end:Math.min(now,row.end),kind:kind});
  });return rows;
}
function renderAutoDay(status){
  var root=E('section',{'id':'hv-auto-day-chart','class':'hv-auto-live-chart hv-auto-day-chart'}),now=Date.now()/1000;
  var history=(((status||{}).accounting||{}).reliability||{}).route_history||{},segments=autoDaySegments(history,now);
  var width=Math.max(280,Math.min(720,document.documentElement.clientWidth-80||720)),left=width<480?88:122,right=width-16;
  var from=now-86400,x=function(t){return left+(t-from)/86400*(right-left);},y=function(kind){return kind==='source'?44:kind==='target'?91:132;};
  var svg=autoLiveSvg('svg',{viewBox:'0 0 '+width+' 168',width:'100%',height:'168',role:'img','aria-label':bi('Saved selected VPN route over the last 24 hours','Сохранённый VPN-маршрут за последние 24 часа')});
  [['source',bi('Primary','Основной')],['target',bi('Reserve','Резерв')],['off',bi('Off','Выключено')]].forEach(function(row){
    svg.appendChild(autoLiveSvg('line',{x1:left,x2:right,y1:y(row[0]),y2:y(row[0]),stroke:'#cbd5e1','stroke-dasharray':'3 5'}));
    svg.appendChild(autoLiveSvg('text',{x:6,y:y(row[0])+4,fill:'currentColor','font-size':12},row[1]));
  });
  var previous=null;
  segments.forEach(function(row){
    if(previous&&previous.end===row.start&&previous.kind!==row.kind)svg.appendChild(autoLiveSvg('line',{x1:x(row.start),x2:x(row.start),y1:y(previous.kind),y2:y(row.kind),stroke:AUTO_LIVE_COLORS[row.kind],'stroke-width':2}));
    var path=autoLiveSvg('line',{x1:x(row.start),x2:x(row.end),y1:y(row.kind),y2:y(row.kind),stroke:AUTO_LIVE_COLORS[row.kind],'stroke-width':3,'stroke-dasharray':row.kind==='unknown'?'3 5':'none'});
    path.appendChild(autoLiveSvg('title',{},autoLiveLabel(row.kind)+' · '+new Date(row.start*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB')+' — '+new Date(row.end*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB')));svg.appendChild(path);previous=row;
  });
  [0,6,12,18,24].forEach(function(hours,index){var stamp=from+hours*3600;svg.appendChild(autoLiveSvg('text',{x:x(stamp),y:157,'text-anchor':index===0?'start':index===4?'end':'middle',fill:'currentColor','font-size':10},new Date(stamp*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit'})));});
  root.appendChild(E('h3',{},bi('Channel switching · last 24 hours','Переключение каналов · последние 24 часа')));root.appendChild(svg);
  root.appendChild(E('p',{'class':'hv-muted'},bi('Saved on the router; survives page reload. Three levels: primary, reserve, off. Transition intervals retain the last confirmed route; gaps mean no observations. Earlier hours are not reconstructed.','История хранится на роутере и сохраняется при обновлении страницы. Три уровня: основной, резерв, выключено. При переходе остаётся последний подтверждённый маршрут; разрыв означает отсутствие данных. Прошлые часы без наблюдений не восстанавливаются.')));
  return root;
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
  var on=fresh&&((ns.state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true))||ns.state==='COMMITTED');
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
  var selected=ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE'?'target':ns.state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true)?'source':null;
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
  'EXISTING-TUNNEL-BINDING-UNVERIFIED':['This MT3000 profile supports the verified wgclient1 and ovpnclient1 pair. Other tunnel bindings remain blocked.','Этот профиль MT3000 поддерживает проверенную пару wgclient1 и ovpnclient1. Другие привязки туннелей остаются заблокированы.'],
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
  'PROFILE-IDENTITY-CHANGED':['The configured profile or tunnel binding changed. Old checks no longer describe the current member; wait for fresh observations and repeat validation.','Профиль или привязка туннеля изменились. Старые проверки больше не описывают текущий сервер; дождитесь свежих наблюдений и повторите проверку.'],
  'VENDOR-SETTLING':['The configured tunnel identity observation window is still pending. This does not establish whether firmware retries have finished.','Окно наблюдения за конфигурацией туннеля ещё не завершено. Это не устанавливает, закончились ли повторные попытки прошивки.'],
  'CONTROL-REVISION-STALE':['Auto controls changed. Refresh the current state before starting again.','Состояние управления Auto изменилось. Обновите данные перед новым запуском.'],
  'START-STATE-UNVERIFIED':['Saved Auto state could not be verified. Stop Auto, review the settings, then try again.','Не удалось проверить сохранённое состояние Auto. Остановите Auto, проверьте настройки и повторите попытку.'],
  'STOP-SUPERSEDED-START':['Stop cancelled this pending Start. Press Start again when ready.','Остановка отменила ожидающий запуск. При необходимости нажмите «Запустить» снова.'],
  'START-CONFIG-CHANGED':['Settings changed while checking. Review them and try Start again.','Настройки изменились во время проверки. Проверьте их и повторите запуск.'],
  'LAN-TRIAL-REQUIRED':['Auto needs a passed LAN trial first: run the LAN helper from a computer on the LAN.','Нужен успешный LAN-тест: запустите LAN-помощник на компьютере в локальной сети.'],
  'BOUNDED-DEADLINE-REQUIRED':['The test window is missing or has expired. Start a new LAN trial.','Окно теста не задано или истекло. Запустите новый LAN-тест.'],
  'SESSION-LOSS-NOT-ACCEPTED':['Confirm in Settings that a short reconnection of calls and sessions is acceptable.','Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим.'],
  'TRANSACTION-IN-PROGRESS':['A switch is already in progress. Wait for it to finish or press Stop.','Переключение уже идёт. Дождитесь окончания или нажмите «Стоп».'],
  'TRIAL-ATTEMPT-LIMIT':['The attempt limit for this window is used up. Start a new LAN trial.','Лимит попыток этого окна исчерпан. Запустите новый LAN-тест.'],
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
  return row?bi(row[0],row[1]):bi('Unrecognised controller code; see the Service monitor.','Неизвестный код контроллера; см. «Службу мониторинга».');
}
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
     hint:!configured?bi('Choose a primary and a different reserve in Settings (System setup).','Выберите основной и другой, резервный профиль в «Настройках» (мастер системы).'):bi('Both tunnels must be connected and pass the DNS/HTTPS check. Connect them in GL.iNet VPN Dashboard.','Оба туннеля должны быть подключены и проходить проверку DNS/HTTPS. Подключите их в VPN Dashboard GL.iNet.')},
    {key:'session',done:settings.native_session_loss===true,
     title:bi('Short reconnection of sessions is accepted','Кратковременный разрыв сессий принят'),
     hint:bi('A switch can interrupt calls and downloads for a few seconds. Confirm this in Settings (System setup).','Переключение может на несколько секунд прервать звонки и загрузки. Подтвердите это в «Настройках» (мастер системы).')},
    {key:'router',done:controllerFresh&&technical.length===0,codes:technical,
     title:bi('Router is ready for switching','Роутер готов к переключению'),
     hint:!controllerFresh?bi('The switching controller is not reporting. Check the Live log (Advanced menu).','Контроллер переключения не отвечает. Проверьте «Живой журнал» (меню «Расширенное»).'):bi('The router reports conditions that block switching (listed below).','Роутер сообщает условия, блокирующие переключение (перечислены ниже).')},
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
  {lamp:'orange',key:'reserve',icon:'⇄',legend:['Orange: working on the reserve, the primary is out','Оранжевый: работаю на резерве, основной не работает']},
  {lamp:'red',key:'problem',icon:'!',legend:['Red: needs your attention','Красный: нужно ваше внимание']}
];
function autoLightModel(status,inventory,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{},intent=status.auto_control||{},state=ns.state;
  var blockers=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  function out(key,title,hint,code){return {key:key,lamp:(AUTO_LIGHTS.filter(function(l){return l.key===key;})[0]||{}).lamp||null,
    icon:key==='off'?'○':key==='unknown'?'?':(AUTO_LIGHTS.filter(function(l){return l.key===key;})[0]||{}).icon,title:title,hint:hint,code:code||null};}
  if(!model.fresh)return out('unknown',bi('No data from the router','Нет данных от роутера'),bi('The status is missing or old. Open Settings and make sure the monitor is running.','Статус отсутствует или устарел. Откройте «Настройки» и проверьте, что мониторинг запущен.'));
  if(ns.proof_scope==='router-probed-ipv4'&&ns.mode==='continuous-pair'){
    var scopeHint=bi('Two selected VPN channels; verified by router IPv4 probes. External LAN is not independently verified.','Два выбранных VPN-канала; проверяются IPv4-запросами роутера. Внешний LAN независимо не проверен.');
    if(model.awaiting)return out('switching',bi('Starting or stopping Auto','Запуск или остановка Auto'),scopeHint);
    if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),scopeHint);
    if(state==='OBSERVING'&&ns.readiness_verified===true)return out('ok',bi('Two-channel Auto is on','Авторежим двух каналов включён'),scopeHint);
    if(state==='COMMITTED')return out('reserve',bi('Working on the reserve','Работаю на резерве'),scopeHint);
    if(state==='STOPPED')return out('off',bi('Auto is off','Auto выключен'),scopeHint);
    return out('problem',bi('Auto needs attention','Auto требует внимания'),scopeHint,blockers[0]);
  }
  if(ns.proof_scope==='router-hosted-ipv4')return out('problem',bi('Router test: external LAN unverified','Тест роутера: внешний LAN не проверен'),bi('This trial checks IPv4 forwarding with a client inside the router. It does not certify traffic from a separate LAN computer.','Этот тест проверяет пересылку IPv4 клиентом внутри роутера. Трафик отдельного компьютера LAN им не подтверждён.'));
  if(model.awaiting)return out('switching',intent.requested==='off'?bi('Stopping Auto','Auto останавливается'):bi('Starting Auto','Auto запускается'),bi('Waiting for the router to confirm. The lamp changes when it does.','Ожидается подтверждение роутера. Лампа изменится, когда оно придёт.'));
  if(state==='RESTORING')return out('switching',bi('Returning to the previous route','Возврат на прежний маршрут'),bi('The router is putting the original route back and checking it.','Роутер возвращает исходный маршрут и проверяет его.'));
  if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),bi('The router is changing the route and waits for a LAN computer to confirm it. This takes up to 90 seconds.','Роутер меняет маршрут и ждёт подтверждения от компьютера в LAN. Это занимает до 90 секунд.'));
  if(state==='OBSERVING'&&ns.certified===true)return out('ok',bi('Auto is on','Auto включён'),bi('Watching the primary. If it fails, the router switches to the reserve after a LAN computer confirms the new route.','Следит за основным. При его отказе роутер переключится на резерв после подтверждения нового маршрута компьютером в LAN.'));
  if(state==='COMMITTED')return out('reserve',bi('Working on the reserve','Работаю на резерве'),bi('The primary is out, traffic goes through the reserve. Auto returns to the primary when it has recovered.','Основной не работает, трафик идёт через резерв. Auto вернётся на основной, когда он восстановится.'));
  if(state==='DEGRADED-ON-RESERVE')return out('problem',bi('The reserve is failing too','Резерв тоже не работает'),bi('Auto stays on the reserve and returns to the primary when it passes its check. Check both VPNs in GL.iNet.','Auto остаётся на резерве и вернётся на основной, когда тот пройдёт проверку. Проверьте оба VPN в GL.iNet.'));
  if(state==='STOPPED-ON-RESERVE')return out('problem',bi('Stopped, but still on the reserve','Остановлен, но роутер всё ещё на резерве'),bi('The original route is not restored. Press Return to primary when the primary works.','Исходный маршрут не восстановлен. Нажмите «Вернуться на основной», когда основной заработает.'));
  if(state==='RELEASE-PENDING'||blockers.indexOf('GUARD-RELEASE-UNCONFIRMED')>=0)return out('problem',bi('Traffic block removal is not confirmed','Снятие блокировки трафика не подтверждено'),bi('Recovery is still pending. See Help → emergency return; Stop has not completed.','Восстановление ещё не завершено. См. «Помощь» → аварийный возврат; остановка не завершена.'),'GUARD-RELEASE-UNCONFIRMED');
  if(state==='BLOCKED'&&intent.requested==='on')return out('problem',bi('Auto is blocked','Auto заблокирован'),blockers.length?autoBlockerText(blockers[0]):bi('The router reports a condition that blocks Auto. See the list below.','Роутер сообщает условие, блокирующее Auto. См. список ниже.'),blockers[0]);
  if(state==='TRIAL-REQUIRED')return out('problem',bi('A LAN trial is required','Нужен LAN-тест'),autoBlockerText('LAN-TRIAL-REQUIRED'),'LAN-TRIAL-REQUIRED');
  if(state==='EXPIRED')return out('off',bi('Auto is off: the test window ended','Auto выключен: окно теста закончилось'),autoBlockerText('BOUNDED-DEADLINE-REQUIRED'));
  if(state==='STOPPED'&&ns.original_restored===true)return out('off',bi('Auto is off','Auto выключен'),bi('Control is back with the router; the original route is verified.','Управление вернулось роутеру; исходный маршрут проверен.'));
  return out('off',bi('Auto is off','Auto выключен'),bi('Monitoring continues; nothing is switched while Auto is off.','Мониторинг продолжается; пока Auto выключен, ничего не переключается.'));
}
// The card's lamp has two states only: green = automatic switching is working (watching, switching or holding the
// reserve), red = it is not (off, blocked, needs attention or no fresh data). The detailed state stays in the text.
function autoWorking(light){return ['ok','switching','reserve'].indexOf(light&&light.key)>=0;}
function renderAutoLight(light,technicalCode){
  var working=autoWorking(light);
  var lamps=[E('span',{'class':'hv-lamp hv-lamp-red'+(working?'':' hv-lamp-lit'),'aria-hidden':'true'}),E('span',{'class':'hv-lamp hv-lamp-green'+(working?' hv-lamp-lit':''),'aria-hidden':'true'})];
  var housing=E('div',{'class':'hv-light hv-light-two hv-light-'+(working?'on':'off'),'role':'img','aria-label':working?bi('Automatic switching works','Автопереключение работает'):bi('Automatic switching does not work','Автопереключение не работает')},lamps);
  var legend=E('ul',{'class':'hv-light-legend','aria-label':bi('What the lamps mean','Что означают лампы')},[
    E('li',{'class':working?'hv-legend-current':''},[E('span',{'class':'hv-dot hv-dot-green','aria-hidden':'true'}),bi('Green: automatic switching works. It watches the primary and moves traffic to the reserve if the primary fails.','Зелёный: автопереключение работает. Оно следит за основным и при его отказе переводит трафик на резерв.')]),
    E('li',{'class':working?'':'hv-legend-current'},[E('span',{'class':'hv-dot hv-dot-red','aria-hidden':'true'}),bi('Red: automatic switching does not work: it is off, blocked, needs your attention, or the router sends no fresh data. Traffic then stays where it is.','Красный: автопереключение не работает: выключено, заблокировано, требует внимания или роутер не присылает свежих данных. Трафик тогда остаётся там, где есть.')]),
    E('li',{},[E('span',{'class':'hv-dot hv-dot-green','aria-hidden':'true'}),' / ',E('span',{'class':'hv-dot hv-dot-red','aria-hidden':'true'}),bi(' Primary and Reserve below: green carries your traffic and works, red does not carry traffic or does not work.',' Основной и Резерв ниже: зелёный пропускает ваш трафик и работает, красный трафик не пропускает или не работает.')])]);
  return E('div',{'class':'hv-light-block'},[housing,E('div',{'class':'hv-light-text'},[E('strong',{'class':'hv-auto-label hv-light-title'},[E('span',{'class':'hv-light-icon','aria-hidden':'true'},light.icon+' '),light.title]),E('p',{'role':'status','aria-live':'polite'},light.hint),E('small',{'class':'hv-auto-tech'},bi('Technical state: ','Техническое состояние: ')+technicalCode),E('details',{'class':'hv-light-help'},[E('summary',{},bi('What do the colours mean?','Что означают цвета?')),legend])])]);
}

// Reply of the Auto button: the code of the answer is shown as a link to its row in the error table, with its short meaning.
function autoCodeNotice(code,extra){
  var row=(typeof ERROR_ROWS!=='undefined'?ERROR_ROWS:[]).filter(function(r){return r[0]===code;})[0];
  return E('p',{},[errorCodeLink(code),row?' · '+bi(row[2],row[3]):'',extra?' · '+extra:'']);
}
var autoRequestBusy=false,autoStopBusy=false,autoStartPending=false;
var autoCommandPending=null,autoControlRefresh=function(){};
function autoCommandOperation(status,now){
  var model=autoControlModel(status,now),intent=status.auto_control||{},phase=intent.pair_phase;
  if(autoCommandPending&&autoCommandPending.acknowledged&&model.fresh&&intent.requested_at>autoCommandPending.baseline){
    var terminal=['FAILED','STOPPED','HELD'].indexOf(phase)>=0;
    var done=autoCommandPending.stop?terminal:terminal||phase==='RUNNING'&&model.on&&!model.awaiting&&!model.transitioning;
    var legacyDone=!phase&&!model.awaiting&&!model.transitioning&&
      (autoCommandPending.stop?model.off:model.on||model.off||model.color==='error');
    if(done||legacyDone)autoCommandPending=null;
  }
  if(autoCommandPending)return autoCommandPending.stop?'stopping':'starting';
  if(phase==='STARTING')return 'starting';
  if(phase==='STOPPING')return 'stopping';
  if(phase==='UNKNOWN')return 'unknown';
  if(model.awaiting||model.transitioning)return intent.requested==='off'?'stopping':'starting';
  return null;
}
function renderAutoControl(status,inventory){
  var ns=status.native_failover||{},intent=status.auto_control||{},model=autoControlModel(status,Date.now()/1000);
  var light=autoLightModel(status,inventory,Date.now()/1000),controlRevision=intent.control_revision;
  var actionLabel=E('span',{'class':'hv-auto-action'},'');
  function syncButton(){
    var operation=autoCommandOperation(status,Date.now()/1000),stop=model.stop||autoStartPending;
    button.disabled=!!(operation||autoRequestBusy||autoStopBusy||inventory.error||!model.fresh);
    if(emergencyButton)emergencyButton.disabled=autoStopBusy||operation==='stopping';
    var label=operation==='starting'?bi('Turning Auto on…','Включение Auto…'):operation==='stopping'?bi('Turning Auto off…','Выключение Auto…'):operation==='unknown'?bi('Awaiting controller state…','Ожидание состояния контроллера…'):stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим');
    button.setAttribute('aria-label',label);button.setAttribute('aria-busy',operation?'true':'false');
    actionLabel.textContent=operation?label:stop?bi('Press to turn Auto off','Нажмите, чтобы выключить Auto'):bi('Press to turn Auto on','Нажмите, чтобы включить Auto');
  }
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-neutral'+(autoWorking(light)?' hv-auto-lit-on':' hv-auto-lit-off')+(model.stop?' hv-auto-armed':''),'aria-label':model.stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим'),'aria-pressed':model.on?'true':'false','disabled':(model.stop?autoStopBusy:autoRequestBusy||autoStopBusy||(inventory.error||!model.fresh))?'':null,'click':function(){
    var stop=model.stop||autoStartPending;if(autoCommandOperation(status,Date.now()/1000)||autoRequestBusy||autoStopBusy)return;
    if(!stop&&(typeof controlRevision!=='string'||!/^[0-9a-f]{32}$/.test(controlRevision))){ui.addNotification(null,autoCodeNotice('CONTROL-REVISION-STALE'));window.location.reload();return;}
    autoCommandPending={stop:stop,baseline:intent.requested_at||0,acknowledged:false};
    if(stop)autoStopBusy=true;else{autoRequestBusy=true;autoStartPending=true;}autoControlRefresh();
    var call=rpc.declare({object:'homensai-vpn',reject:true,method:stop?'native_stop':'native_start',params:stop?[]:['control_revision'],expect:{}});
    return (stop?call():call(controlRevision)).then(function(result){
      if(autoCommandPending&&autoCommandPending.stop===stop){if(autoRequestAcknowledged(result,stop))autoCommandPending.acknowledged=true;else autoCommandPending=null;}
      if(!stop&&result&&result.accepted===false&&(result.code==='CONTROL-REVISION-STALE'||Array.isArray(result.blockers)&&result.blockers.indexOf('CONTROL-REVISION-STALE')>=0)){ui.addNotification(null,autoCodeNotice('CONTROL-REVISION-STALE'));window.location.reload();return;}
      if(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9-]{2,95}$/.test(result.code)&&(result.accepted===false||result.queued===false))ui.addNotification(null,autoCodeNotice(result.code,result.settings_unverified?bi('router settings could not be read','настройки роутера не прочитаны'):''));
      else if(result&&result.accepted===false){ui.addNotification(null,E('div',{},[autoCodeNotice('AUTO-START-REFUSED'),E('ul',{},(result.blockers||[]).map(function(code){return E('li',{},code+' · '+autoBlockerText(code));}))]));}
      else if(!autoRequestAcknowledged(result,stop))ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
      else ui.addNotification(null,E('p',{},bi('Request sent. The button changes only when the router confirms it.','Запрос отправлен. Кнопка изменится, только когда роутер подтвердит.')));
    }).catch(function(){if(autoCommandPending&&autoCommandPending.stop===stop)autoCommandPending.acknowledged=true;ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){if(stop)autoStopBusy=false;else{autoRequestBusy=false;autoStartPending=false;}autoControlRefresh();});
  }},E('span',{'class':'hv-power-symbol','aria-hidden':'true'}));
  var emergencyButton=E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','click':function(){
    if(autoStopBusy||autoCommandOperation(status,Date.now()/1000)==='stopping')return;
    autoCommandPending={stop:true,baseline:intent.requested_at||0,acknowledged:false};autoStopBusy=true;autoControlRefresh();
    return rpc.declare({object:'homensai-vpn',reject:true,method:'native_stop',expect:{}})().then(function(result){
      if(autoCommandPending&&autoCommandPending.stop){if(autoRequestAcknowledged(result,true))autoCommandPending.acknowledged=true;else autoCommandPending=null;}
      ui.addNotification(null,autoRequestAcknowledged(result,true)?E('p',{},bi('Stop requested. Monitoring continues.','Остановка запрошена. Мониторинг продолжается.')):autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
    }).catch(function(){if(autoCommandPending&&autoCommandPending.stop)autoCommandPending.acknowledged=true;ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){autoStopBusy=false;autoControlRefresh();});
  }},bi('Emergency Stop','Аварийный стоп'));
  var emergencyControl=E('div',{'class':'hv-auto-emergency'},[emergencyButton,E('small',{},bi('Cancels Auto and pending starts. Monitoring continues.','Отменяет Auto и ожидающие запросы запуска. Мониторинг продолжается.'))]);
  autoControlRefresh=syncButton;syncButton();
  var rows=status.profiles||[],settings=inventory.settings||{};
  function profile(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',Date.now()/1000,ns.source):profile(ns.source||settings.plan_source),target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',Date.now()/1000,ns.target):profile(ns.target||settings.plan_target);
  var path=typeof manualConfirmedPath==='function'?manualConfirmedPath(status,source,target,Date.now()/1000):autoPathModel(status,source,target,Date.now()/1000);
  var pathLabels={neutral:bi('No fresh check','Нет свежей проверки'),healthy:bi('Carries your traffic','Пропускает ваш трафик'),ready:bi('Ready, on standby','Готов, в резерве'),inactive:bi('Not connected','Не подключён'),failed:bi('Not working','Не работает'),checking:bi('Being checked','Проверяется')};
  // Channel selection is separate from probe health: an idle healthy reserve is not a failure.
  function nodeTone(p,key){
    if(typeof manualChannelTone==='function')return manualChannelTone(p,key,path,Date.now()/1000);
    return {color:'grey',text:bi('No fresh path confirmation','Нет свежего подтверждения пути'),carrier:false};
  }
  function box(p,label,key){var state=path[key],tone=nodeTone(p,key);var attributes={'class':'hv-auto-node hv-node-two hv-node-'+tone.color+(tone.carrier?' hv-node-carrier':''),'data-path-node':key,'data-path-state':state,'data-node-tone':tone.color};
    // The address the internet sees is not printed on screen; it is available as a tooltip only.
    if(p&&p.exit_ip&&profileHealth(p,Date.now()/1000).state==='healthy')attributes.title=bi('Exit IP: ','Внешний IP: ')+p.exit_ip;
    return E('div',attributes,[E('small',{},label),E('strong',{'class':'hv-node-protocol'},p?protocolLabel(p):'—'),E('b',{},p?countryLabel(p):bi('Choose in Settings','Выберите в настройках')),p?E('span',{'title':bi('Group: a label you can set in Settings → System. It does not change how the VPN works.','Группа: метка, которую можно задать в «Настройки» → «Система». Она не влияет на работу VPN.')},(customName(p)?customName(p)+' · ':'')+bi('Group: ','Группа: ')+(p.channel||'default')):null,E('span',{'class':'hv-path-label','title':pathLabels[state]},[E('span',{'class':'hv-node-dot','aria-hidden':'true'}),tone.text])].filter(Boolean));}
  var diagram=E('div',{'class':'hv-auto-diagram hv-path-diagram'+(path.moving?' hv-path-moving':'')+(path.direction==='back'?' hv-path-back':''),'aria-label':bi('Configured failover path','Настроенная схема переключения')},[box(source,bi('Primary','Основной'),'source'),E('span',{'class':'hv-auto-arrow '+(path.direction!=='none'?'hv-arrow-on':''),'aria-label':path.moving?bi('Switching in progress','Выполняется переключение'):path.direction!=='none'?bi('Reserve selected','Выбран резерв'):bi('Automatic transition inactive','Автопереход неактивен')},path.direction==='back'?'←':path.direction==='forward'?'→':'⋯'),box(target,bi('Reserve','Резерв'),'target')]);
  var pairMode=settings.pair_auto_mode==='router-probed-ipv4';
  var until=pairMode?0:autoWindowDeadline(intent,settings);
  var readiness=autoReadiness(status,inventory,Date.now()/1000);
  var checklist=null;
  if(pairMode){
    checklist=E('div',{'class':'hv-auto-readiness'},[E('p',{'class':'hv-step-note'},bi('Two-channel Auto starts the saved primary and reserve, watches their IPv4 DNS/HTTPS checks, switches on repeated failure and returns after stable recovery. Stop remains available during startup. This mode uses router probes; external LAN is not independently verified. Auto stays off after a router or service restart.','Авторежим двух каналов запускает сохранённые основной и резервный VPN, проверяет IPv4 DNS/HTTPS, переключается при повторных отказах и возвращается после устойчивого восстановления. Stop доступен и во время запуска. Проверки выполняет роутер; внешний LAN независимо не проверен. После перезапуска роутера или службы Auto остаётся выключенным.'))]);
  }else if(!model.on&&!model.transitioning&&!model.stop){
    checklist=E('div',{'class':'hv-auto-readiness'},[E('p',{'class':'hv-step-note'},bi('Step 2 · Turn on Auto. Do it after step 1 (“Check the VPNs now”, at the top of this page) shows that your VPNs work and the list below is complete.','Шаг 2 · Включите Auto. Делайте это после шага 1 («Проверить VPN сейчас», вверху страницы), когда проверка показала, что ваши VPN работают, и список ниже выполнен.')),E('h3',{},readiness.ready?bi('Ready to start','Готово к запуску'):bi('Before you can start Auto','Что нужно перед запуском Auto')),E('ol',{'class':'hv-req-list'},readiness.steps.map(function(step){
      var isNext=readiness.next&&readiness.next.key===step.key;
      var extra=step.key==='router'&&!step.done&&step.codes&&step.codes.length?E('ul',{'class':'hv-req-codes'},step.codes.map(function(code){return E('li',{},[safeCode(code)?errorCodeLink(code):E('code',{},code),' · '+autoBlockerText(code)]);})):null;
      return E('li',{'class':'hv-req hv-req-'+(step.done?'done':isNext?'next':'todo')},[E('span',{'class':'hv-req-mark','aria-hidden':'true'},step.done?'✓':isNext?'→':'·'),E('div',{},[E('strong',{},step.title),step.done?null:E('p',{},step.hint),extra].filter(Boolean)),E('span',{'class':'hv-visually-hidden'},step.done?bi('done','выполнено'):bi('not done','не выполнено'))]);
    })),E('p',{'class':'hv-req-actions'},[E('a',{'class':'cbi-button','href':'#settings'},bi('Open Settings','Открыть настройки')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/start-lan-helper.ps1'),'download':'start-lan-helper.ps1'},bi('Download launcher','Скачать запуск'))])]);
  }
  var holdReturn=null;
  // Return to the primary belongs to this card: it is offered whenever traffic is on the reserve (also while Auto is on).
  if(model.fresh&&['STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE','COMMITTED'].indexOf(ns.state)>=0){
    var answer=intent.return_result,answerText=answer&&Number.isFinite(answer.time)&&Date.now()/1000-answer.time<600?(answer.ok?autoBlockerText('OPERATOR-RETURN'):autoBlockerText(answer.code)):'';
    var returnButton=guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':autoRequestBusy||autoStopBusy?'':null,'click':function(){
      if(autoRequestBusy||autoStopBusy)return;return guardedAction(returnButton,function(){autoRequestBusy=true;
      return rpc.declare({object:'homensai-vpn',reject:true,method:'native_return',expect:{}})().then(function(result){
        if(result&&result.accepted===false)ui.addNotification(null,E('p',{},(result.code||'RETURN-REFUSED')+' · '+autoBlockerText(result.code)));
        else if(!autoRequestAcknowledged(result,false))ui.addNotification(null,E('p',{},'AUTO-CONTROL-UNVERIFIED: no confirmed acceptance; check controller state.'));
        else ui.addNotification(null,E('p',{},bi('Return requested. The router checks the primary first and reports the result here.','Возврат запрошен. Роутер сначала проверит основной и покажет результат здесь.')));
      }).catch(function(){ui.addNotification(null,E('p',{},'AUTO-CONTROL-FAILED: no confirmed response; check controller state.'));}).finally(function(){autoRequestBusy=false;});},{key:'auto-return'});
    }},bi('Return to primary','Вернуться на основной')),'auto-return');
    holdReturn=E('div',{'class':'hv-auto-hold'},[E('p',{},bi('The router is using the reserve. When the primary works again, send traffic back to it.','Роутер использует резерв. Когда основной снова заработает, верните трафик на него.')),returnButton,E('a',{'href':'#help'},bi('Help: no internet?','Справка: нет интернета?')),answerText?E('p',{'role':'status'},answerText):null].filter(Boolean));
  }
  var technicalCode=ns.state?ns.state+(ns.reason?' · '+ns.reason:'')+(model.fresh?'':' · STATUS-STALE'):'UNKNOWN';
  var liveChart=typeof renderAutoLive==='function'?renderAutoLive(status,inventory):null;
  var dayChart=typeof renderAutoDay==='function'?renderAutoDay(status):null;
  var automatic=E('section',{'class':'hv-chart-card hv-auto-control'},[E('h2',{},bi('Automatic VPN failover','Автоматическое переключение VPN')),E('div',{'class':'hv-auto-switch'},[E('div',{'class':'hv-auto-power-unit'},[E('strong',{'class':'hv-auto-state hv-auto-state-'+(autoWorking(light)?'on':'off'),'role':'status'},autoWorking(light)?bi('Auto works','Auto работает'):bi('Auto does not work','Auto не работает')),button,actionLabel]),renderAutoLight(light,technicalCode)]),emergencyControl,liveChart,dayChart,holdReturn,checklist,E('p',{'class':'hv-auto-limit'},(pairMode?bi('Two selected VPN channels. Each switch is checked by the router. External LAN remains unverified.','Два выбранных VPN-канала. Каждый переход проверяет роутер. Внешний LAN остаётся непроверенным.'):bi('Experimental: each automatic switch must be confirmed by the LAN helper running on a computer in your network. Without it the router goes back to the previous route after 90 seconds.','Экспериментально: каждое автоматическое переключение должен подтвердить LAN-помощник на компьютере в вашей сети. Без него роутер через 90 секунд вернётся на прежний маршрут.'))+(Number.isFinite(until)&&until>0?' '+bi('Window ends: ','Окно действует до: ')+new Date(until*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB')+'.':''))].filter(Boolean));
  return E('div',{'class':'hv-auto-sections'},[automatic,typeof renderManualSwitch==='function'?renderManualSwitch(status,inventory):null].filter(Boolean));
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
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var setupCheck=kind==='system'?'pending':'passed',wizardGeneration=++setupWizardGeneration;
  var step=0,busy=false,closed=false,settings=inventory.settings||{},profiles=Array.isArray(inventory.profiles)?inventory.profiles:[],custom=Array.isArray(inventory.servers)?inventory.servers:[];
  var draft={source:settings.plan_source||'',target:settings.plan_target||'',interval:settings.interval==null?30:settings.interval,duration:settings.native_duration==null?10:settings.native_duration,session_loss:!!settings.native_session_loss,servers:profiles.map(function(p){var saved=custom.filter(function(s){return s.profile===p.id;})[0]||{};return {profile:p.id,name:saved.name||p.name,channel:saved.channel||'default',priority:saved.priority==null?100:saved.priority,enabled:saved.enabled!==false};})};
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
        body.appendChild(E('p',{},bi('Names, channels and priorities are used for display and ranking only. Real route changes happen only after the LAN trial.','Названия, каналы и приоритеты нужны только для отображения и рейтинга. Реальная смена маршрута возможна только после LAN-теста.')));
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
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('ul',{},selected.map(function(id){return E('li',{},(profiles.filter(function(p){return p.id===id;})[0]||{}).name||id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams).then(function(result){ui.addNotification(null,E('p',{},result.accepted?'SPEED-QUEUED':result.code||'SPEED-START-FAILED'));ui.hideModal();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-START-FAILED: no confirmed response.'));});},{key:'speed-start'});}},bi('Run test','Запустить тест')),'speed-start')]);
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
  var today=dateKey(new Date()),section=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Daily WAN and VPN traffic','Суточный трафик WAN и VPN'))]);
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

var RECOVERY_PRESETS={"fast_recovery": {"cooldown": 60, "failures": 3, "min_dwell": 60, "primary_stable": 60, "primary_successes": 3, "return_policy": "healthy_primary", "successes": 2}, "hold_reserve": {"cooldown": 180, "failures": 3, "min_dwell": 180, "primary_stable": 60, "primary_successes": 3, "return_policy": "hold_reserve", "successes": 2}, "stability": {"cooldown": 300, "failures": 5, "min_dwell": 300, "primary_stable": 120, "primary_successes": 5, "return_policy": "healthy_primary", "successes": 3}};
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
  var labels={failures:bi('Consecutive failures before switching (3–10)','Сбоев подряд до переключения (3–10)'),successes:bi('Reserve checks that must pass (2–10)','Проверок резерва, которые должны пройти (2–10)'),cooldown:bi('Pause between switch attempts, seconds (60–1800)','Пауза между попытками переключения, секунд (60–1800)'),min_dwell:bi('Minimum time to stay on a route, seconds (60–3600)','Минимальное время на маршруте, секунд (60–3600)'),primary_successes:bi('Primary checks that must pass before returning (2–10)','Проверок основного, которые должны пройти перед возвратом (2–10)'),primary_stable:bi('The primary must stay healthy for, seconds (30–600)','Основной должен оставаться исправным, секунд (30–600)')};
  var defaults={failures:3,successes:2,cooldown:180,min_dwell:180,return_policy:'healthy_primary',primary_successes:3,primary_stable:60},draft={};
  Object.keys(defaults).forEach(function(key){draft[key]=settings['recovery_'+key]==null?defaults[key]:settings['recovery_'+key];});
  // A saved set that equals a reviewed preset is shown as that preset; any other set is Custom.
  Object.keys(RECOVERY_PRESETS).forEach(function(name){var row=RECOVERY_PRESETS[name];if(!presetName&&Object.keys(defaults).every(function(key){return String(row[key])===String(draft[key]);}))presetName=name;});
  function show(){
    var body=E('div',{'class':'hv-wizard'}),read=function(){return true;},checks=[],nextButton;
    function updateGate(){if(nextButton)foolGate(nextButton,checks);}
    body.appendChild(E('p',{},bi('These rules decide when Auto switches to the reserve and when it returns. They apply only inside a LAN-tested time window. Auto never connects a VPN that is switched off.','Эти правила определяют, когда Auto переходит на резерв и когда возвращается. Они действуют только внутри окна, прошедшего LAN-тест. Auto никогда не подключает выключенный VPN.')));
    if(step===0){
      var presetSelect=E('select',{'aria-label':bi('Recovery preset','Профиль восстановления')},[
        E('option',{value:''},bi('Custom settings','Свои настройки')),E('option',{value:'stability'},bi('Stability','Стабильность')),E('option',{value:'fast_recovery'},bi('Fast recovery','Быстрое восстановление')),E('option',{value:'hold_reserve'},bi('Hold healthy reserve','Сохранять работающий резерв'))]);
      presetSelect.value=presetName;
      presetSelect.addEventListener('change',function(){presetName=presetSelect.value;var preset=RECOVERY_PRESETS[presetName];if(!preset)return;Object.keys(preset).forEach(function(key){draft[key]=preset[key];});show();});
      body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Preset (review before saving)','Профиль (проверьте перед сохранением)')),presetSelect]));
      var editors={};Object.keys(labels).forEach(function(key){var node=E('input',{type:'number','aria-label':labels[key]});node.value=draft[key];node.addEventListener('input',function(){presetName='';presetSelect.value='';});editors[key]=node;var item=foolNumberRow(labels[key],node,'recovery.'+key,updateGate);checks.push(item.check);body.appendChild(item.row);});
      var policy=E('select',{'aria-label':bi('Return policy','Политика возврата')},[E('option',{value:'healthy_primary'},bi('Return to the primary once it has been healthy for a while','Вернуться на основной, когда он некоторое время исправен')),E('option',{value:'hold_reserve'},bi('Stay on the working reserve until you decide','Оставаться на рабочем резерве, пока вы не решите иначе'))]);policy.value=draft.return_policy;policy.addEventListener('change',function(){presetName='';presetSelect.value='';});body.appendChild(policy);
      read=function(){if(!foolGate(null,checks))return false;var limits={failures:[3,10],successes:[2,10],cooldown:[60,1800],min_dwell:[60,3600],primary_successes:[2,10],primary_stable:[30,600]};var valid=Object.keys(editors).every(function(key){draft[key]=Number(editors[key].value);return Number.isInteger(draft[key])&&draft[key]>=limits[key][0]&&draft[key]<=limits[key][1];});draft.return_policy=policy.value;return valid;};
    }else{
      body.appendChild(E('h3',{},bi('Review recovery settings','Проверьте настройки восстановления')));
      body.appendChild(E('ul',{},Object.keys(labels).map(function(key){return E('li',{},labels[key]+': '+draft[key]);})));
      body.appendChild(E('p',{},bi('Return policy: ','Политика возврата: ')+draft.return_policy));
      body.appendChild(E('p',{},bi('Changing these rules cancels the earlier LAN test. Auto stays off; run the LAN helper again before you start Auto.','Изменение правил отменяет прежний LAN-тест. Auto остаётся выключенным; перед запуском Auto снова запустите LAN-помощник.')));
    }
    var actions=[E('button',{'type':'button','class':'cbi-button','click':function(){if(FOOL_LOCKS['setup-recovery']&&FOOL_LOCKS['setup-recovery'].phase==='work')return;ui.hideModal();}},bi('Cancel','Отмена'))];
    if(step)actions.push(E('button',{'type':'button','class':'cbi-button','click':function(){if(FOOL_LOCKS['setup-recovery']&&FOOL_LOCKS['setup-recovery'].phase==='work')return;step=0;show();}},bi('Back','Назад')));
    actions.push(nextButton=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(ev){if(!read()){ui.addNotification(null,E('p',{},'RECOVERY-RANGE'));return;}if(!step){step=1;show();return;}var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_recovery',params:['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable'],expect:{}})(draft.failures,draft.successes,draft.cooldown,draft.min_dwell,draft.return_policy,draft.primary_successes,draft.primary_stable).then(function(result){ui.addNotification(null,E('p',{},result.saved?'RECOVERY-SAVED':result.code||'RECOVERY-SAVE-FAILED'));if(result.saved){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'RECOVERY-SAVE-UNCONFIRMED'));});},{key:'setup-recovery'});}},step?bi('Save recovery settings','Сохранить настройки восстановления'):bi('Next','Далее')));
    updateGate();guardResume(nextButton,'setup-recovery');body.appendChild(E('div',{'class':'hv-wizard-actions'},actions));ui.showModal(bi('Recovery setup wizard','Мастер восстановления'),[body]);
  }
  show();
}

function monitorPreferences(inventory){
  if(inventory.error){ui.addNotification(null,E('p',{},'RPC-INVENTORY-UNAVAILABLE: setup is blocked.'));return;}
  var settings=inventory.settings||{},saveButton,checks=[];
  var planning=E('input',{type:'checkbox','aria-label':bi('Show the failover forecast on the Overview','Показывать прогноз переключения на странице «Обзор»')});planning.checked=!!settings.plan_enabled;
  var body=E('div',{'class':'hv-wizard'},[E('p',{},bi('Only this program’s own settings change. Saving statistics more often wears the router flash memory faster. This does not start Auto or connect any VPN.','Меняются только настройки этой программы. Частое сохранение статистики быстрее изнашивает флеш-память роутера. Auto не запускается, VPN не подключаются.'))]);
  function updateGate(){if(saveButton)foolGate(saveButton,checks);}
  function number(label,key,value,ariaLabel){var node=E('input',{type:'number'});node.value=value;var item=foolNumberRow(label,node,key,updateGate);node.setAttribute('aria-label',ariaLabel);checks.push(item.check);body.appendChild(item.row);return node;}
  var interval=number(bi('How often to check each VPN (10–300 seconds)','Как часто проверять каждый VPN (10–300 секунд)'),'monitor.interval',settings.interval==null?30:settings.interval,bi('How often to check each VPN, seconds','Как часто проверять каждый VPN, секунд')),checkpoint=number(bi('Save statistics every (300–3600 seconds)','Сохранять статистику каждые (300–3600 секунд)'),'monitor.checkpoint',settings.checkpoint==null?900:settings.checkpoint,bi('Save statistics every, seconds','Сохранять статистику каждые, секунд')),limit=number(bi('Most VPNs checked per round (1–16)','Максимум VPN за один раунд проверки (1–16)'),'monitor.probe_limit',settings.probe_limit==null?16:settings.probe_limit,bi('Most VPNs checked per round','Максимум VPN за один раунд проверки'));
  body.appendChild(E('label',{'class':'hv-wizard-field'},[E('span',{},bi('Show the failover forecast','Показывать прогноз переключения')),planning]));
  saveButton=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
    if(!foolGate(saveButton,checks))return;
    return guardedAction(saveButton,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'setup_monitor',params:['interval','checkpoint','probe_limit','planning_enabled'],expect:{}})(Number(interval.value),Number(checkpoint.value),Number(limit.value),planning.checked).then(function(result){ui.addNotification(null,E('p',{},result&&result.saved===true?'MONITOR-PREFERENCES-SAVED':result&&result.code||'MONITOR-PREFERENCES-FAILED'));if(result&&result.saved===true){ui.hideModal();window.location.reload();}}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-PREFERENCES-UNCONFIRMED'));});},{key:'setup-monitor'});
  }},bi('Save monitoring preferences','Сохранить параметры мониторинга'));
  updateGate();guardResume(saveButton,'setup-monitor');
  body.appendChild(E('div',{'class':'hv-wizard-actions'},[E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),saveButton]));
  ui.showModal(bi('Monitoring preferences','Параметры мониторинга'),[body]);
}

var FAULT_UI_CONTEXT=null;
function faultCurrentBinding(status,inventory){
  status=status||{};inventory=inventory||{};
  var now=Date.now()/1000,native=(status||{}).native_failover||{},settings=(inventory||{}).settings||{};
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):null,target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):null;
  var model=typeof vendorDiagnosticsModel==='function'?vendorDiagnosticsModel(status,inventory,now):null,coord=model&&model.coordination;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&0<=now-status.time&&now-status.time<=90&&Number.isFinite(native.time)&&0<=now-native.time&&now-native.time<=30;
  var healthy=source&&target&&Number.isFinite(source.time)&&0<=now-source.time&&now-source.time<=90&&Number.isFinite(target.time)&&0<=now-target.time&&now-target.time<=90&&source.code===null&&target.code===null&&source.dns_ok===true&&target.dns_ok===true&&Number.isInteger(source.https_success)&&source.https_success>=2&&Number.isInteger(target.https_success)&&target.https_success>=2;
  var ready=!!(fresh&&native.state==='OBSERVING'&&native.certified===true&&settings.native_session_loss===true&&source&&target&&healthy&&native.source===source.id&&native.target===target.id&&typeof native.vendor_identity==='string'&&/^[0-9a-f]{64}$/.test(native.vendor_identity)&&native.source_generation===source.vendor_generation&&native.target_generation===target.vendor_generation&&coord&&coord.known&&coord.state==='READY'&&coord.code==='CROSS-TUNNEL-READY'&&coord.source===source.vendor_tunnel_id&&coord.target===target.vendor_tunnel_id);
  return {ready:ready,source:source,target:target,certificate:native.vendor_identity||null};
}
function faultPanel(status,inventory,refresh){
  var state=status.operator_fault||{},native=status.native_failover||{},settings=inventory.settings||{},binding=faultCurrentBinding(status,inventory),source=binding.source,ready=binding.ready;
  FAULT_UI_CONTEXT={status:status,inventory:inventory};
  var section=E('section',{'class':'hv-chart-card'},[E('h2',{},bi('Controlled VPN tunnel traffic fault','Контролируемый сбой трафика VPN-туннеля')),E('p',{},bi('This temporarily blocks IPv4 traffic through the whole current VPN tunnel device, keeping its process connected. It cannot isolate one upstream server inside the tunnel. Router INPUT, management routes and Kill Switch are unchanged.','Временно блокируется IPv4-трафик всего устройства текущего VPN-туннеля, сам процесс остаётся подключённым. Это не позволяет изолировать один сервер внутри туннеля. INPUT роутера, маршруты управления и Kill Switch не меняются.'))]);
  section.appendChild(E('p',{'role':'status'},bi('Test state: ','Состояние теста: ')+(state.code||state.state||'IDLE')+(state.until?' · '+bi('Remaining about ','Осталось примерно ')+(state.remaining_seconds==null?Math.max(0,Math.ceil(state.until-Date.now()/1000)):state.remaining_seconds)+' s':'')));
  var scope=E('select',{'aria-label':bi('Failure scope','Область сбоя')},[E('option',{value:'channel'},bi('Current primary VPN tunnel (IPv4 traffic)','Текущий основной VPN-туннель (IPv4-трафик)'))]);scope.value='channel';
  var duration=E('select',{'aria-label':bi('Fault duration','Длительность сбоя')},[30,60,120,150,180].map(function(value){return E('option',{value:String(value)},value+' s');}));duration.value='150';
  section.appendChild(E('p',{},bi('Selected source tunnel: ','Выбранный основной туннель: ')+(source?source.vendor_tunnel_id+' · '+source.id:'—')));
  section.appendChild(E('div',{'class':'hv-native-actions'},[scope,duration,E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','disabled':ready&&source?null:'','aria-describedby':ready&&source?null:'hv-fault-why','title':ready&&source?null:bi('Not available: see the reasons below.','Недоступно: причины ниже.'),'click':function(){
    if(!ready||!source||scope.value!=='channel'||['30','60','120','150','180'].indexOf(duration.value)<0)return;
    var reviewedScope='channel',reviewedDuration=Number(duration.value),reviewedId=source.id,reviewedTunnel=source.vendor_tunnel_id,reviewedGeneration=source.vendor_generation,reviewedTarget=binding.target.id,reviewedTargetGeneration=binding.target.vendor_generation,reviewedCertificate=binding.certificate;
    ui.showModal(bi('Review deliberate tunnel traffic interruption','Подтвердите прерывание трафика туннеля'),[E('p',{},bi('Calls and sessions can reconnect. This affects the whole tunnel device, not an isolated provider server or profiles sharing an editable label. Use only during an agreed local test. A healthy reserve and enough certified-window time are required; the router rechecks the private certificate before applying anything.','Звонки и сессии могут переподключиться. Затрагивается всё устройство туннеля, а не отдельный сервер провайдера и не профили с одинаковой редактируемой меткой. Используйте только в согласованном локальном тесте. Нужен исправный резерв и достаточный остаток подтверждённого окна; перед применением роутер перепроверяет закрытый сертификат.')),E('ul',{},[E('li',{},reviewedTunnel+' · '+reviewedId)]),E('p',{},bi('Maximum fault duration: ','Максимальная длительность сбоя: ')+reviewedDuration+' s'),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-negative hv-danger-action','click':function(ev){
      var current=FAULT_UI_CONTEXT&&faultCurrentBinding(FAULT_UI_CONTEXT.status,FAULT_UI_CONTEXT.inventory);
      if(!current||!current.ready||current.source.id!==reviewedId||current.source.vendor_tunnel_id!==reviewedTunnel||current.source.vendor_generation!==reviewedGeneration||current.target.id!==reviewedTarget||current.target.vendor_generation!==reviewedTargetGeneration||current.certificate!==reviewedCertificate){ui.addNotification(null,E('p',{},bi('FAULT-NOT-CURRENT-SOURCE: the reviewed identity is no longer confirmed. Close this review and check the current tunnel again.','FAULT-NOT-CURRENT-SOURCE: идентичность из обзора больше не подтверждена. Закройте обзор и снова проверьте текущий туннель.')));return;}
      var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'fault_start',params:['profile','scope','duration'],expect:{}})(reviewedId,reviewedScope,reviewedDuration).then(function(result){ui.addNotification(null,E('p',{},result&&safeCode(result.code)?result.code:'FAULT-UNKNOWN'));ui.hideModal();return refresh();}).catch(function(){ui.addNotification(null,E('p',{},'FAULT-RPC-UNCONFIRMED: inspect actual test state.'));});},{key:'fault-start'});
    }},bi('Start bounded fault','Запустить ограниченный сбой')),'fault-start')]);
  }},bi('Simulate tunnel traffic failure','Имитировать сбой трафика туннеля')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'fault_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'FAULT-CANCEL-UNKNOWN'));return refresh();});}},bi('Cancel fault now','Отменить сбой сейчас'))]));
  if(!ready||!source){
    var reasons=faultBlockers(status,inventory,source);
    var why=E('div',{'class':'hv-fault-why alert-message warning','id':'hv-fault-why','role':'status'},[
      E('strong',{},bi('The “Simulate tunnel traffic failure” button is not available right now.','Кнопка «Имитировать сбой трафика туннеля» сейчас недоступна.')),
      E('p',{},bi('Reason'+(reasons.length>1?'s':'')+' and where to fix '+(reasons.length>1?'them':'it')+':','Причин'+(reasons.length>1?'ы':'а')+' и где '+(reasons.length>1?'их':'это')+' исправить:')),
      E('ul',{},reasons.map(function(r){return E('li',{},[bi(r.en,r.ru),' ',r.link]);}))]);
    section.appendChild(why);
  }
  section.appendChild(E('small',{},bi('Inactive profiles are not started. This is a traffic fault, not a VPN service stop. Auto mode Stop also requests fault cleanup.','Неактивные профили не запускаются. Это сбой трафика, а не остановка VPN-службы. Остановка авторежима также запрашивает очистку сбоя.')));
  if(state.history&&state.history.length){var table=E('table',{'class':'table'},[E('tr',{},[bi('Time · Berlin','Время · Берлин'),bi('Code','Код'),bi('Profiles','Профили'),bi('Scope','Область')].map(function(text){return E('th',{},text);} ))]);state.history.slice().reverse().forEach(function(row){table.appendChild(E('tr',{},[new Date(row.time*1000).toLocaleString('en-GB',{timeZone:'Europe/Berlin'}),(safeCode(row.code)?errorCodeLink(row.code):row.code),(row.profiles||[]).join(', '),row.scope].map(function(value){return E('td',{},value);})));});section.appendChild(table);}
  return section;
}

// Every reason why the failure test cannot start, in plain words, each with the place to fix it (mirrors the router-side checks).
function faultBlockers(status,inventory,source){
  var native=status.native_failover||{},settings=(inventory||{}).settings||{},profiles=status.profiles||[],now=Date.now()/1000;
  var reasons=[],hash=function(tab,label){return E('a',{'class':'cbi-button','href':'#'+tab},label);};
  var target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):null;
  if(!settings.plan_source||!settings.plan_target||!source)reasons.push({en:'No primary and reserve VPN are chosen.',ru:'Не выбраны основной и резервный VPN.',link:hash('settings',bi('Go to Settings → Setup → 1 · System setup','Перейти в «Настройки» → «Настройка» → 1 · Настройка системы'))});
  if(status.rpc_error||!(0<=now-status.time&&now-status.time<=90))reasons.push({en:'The router sends no fresh data, so the monitor may not be running.',ru:'Роутер не присылает свежих данных, возможно, мониторинг не работает.',link:hash('overview',bi('Go to the Overview and check the Monitoring block','Перейти на «Обзор» и проверить блок «Мониторинг»'))});
  var current=faultCurrentBinding(status,inventory);
  if(!current.ready)reasons.push({en:'The current tunnel identity, fresh coordination and a certificate for exactly these current profiles must agree. The router independently rechecks the private certificate.',ru:'Текущая идентичность туннеля, свежая координация и сертификат именно этих текущих профилей должны совпадать. Роутер независимо перепроверяет закрытый сертификат.',link:hash('channels',bi('Review current tunnel observations','Проверить текущие наблюдения туннелей'))});
  if(settings.native_session_loss===false||settings.native_session_loss==='0')reasons.push({en:'You have not allowed a short reconnection of calls and sessions.',ru:'Вы не разрешили короткое переподключение звонков и сессий.',link:hash('settings',bi('Go to Settings → Setup → 1 · System setup and tick the permission','Перейти в «Настройки» → «Настройка» → 1 · Настройка системы и поставить разрешение'))});
  if(target&&profileHealth(target,now).state!=='healthy')reasons.push({en:'The reserve VPN does not work now; the test needs a healthy reserve.',ru:'Резервный VPN сейчас не работает; для теста нужен исправный резерв.',link:hash('channels',bi('Go to Channels and servers','Перейти в «Каналы и серверы»'))});
  var running=['OBSERVING','ARMED','APPLYING','WAIT-CLIENT','COMMITTED'].indexOf(native.state)>=0;
  if(!running)reasons.push({en:'Auto is not on. The test works only while Auto is watching the primary.',ru:'Auto не включён. Тест работает только пока Auto следит за основным.',link:hash('overview',bi('Go to the Overview and turn Auto on (button in “Automatic VPN failover”)','Перейти на «Обзор» и включить Auto (кнопка в блоке «Автоматическое переключение VPN»)'))});
  else if(native.certified!==true)reasons.push({en:'The LAN trial has not passed yet, so Auto is not certified.',ru:'LAN-тест ещё не пройден, поэтому Auto не подтверждён.',link:[hash('settings',bi('Go to Settings → LAN trial','Перейти в «Настройки» → LAN-тест')),' ',helpLink('helper-what',bi('Help: how to run the LAN helper','Помощь: как запустить LAN-помощник'))]});
  else if(!(0<=now-native.time&&now-native.time<=30))reasons.push({en:'The controller status is old.',ru:'Статус контроллера устарел.',link:hash('overview',bi('Go to the Overview and check the Auto card','Перейти на «Обзор» и посмотреть блок Auto'))});
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

function profileHealth(profile,now){
  if(!profile.interface||profile.administrative_state==='disabled')return {state:'inactive',label:bi('Inactive','Неактивен')};
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
  if(native.state==='OBSERVING'&&(native.certified===true||native.mode==='continuous-pair'&&native.readiness_verified===true))return native.source||null;
  return null;
}
function sortServerCards(rows,selected,now){
  var ranks={healthy:1,checking:2,unknown:3,inactive:4,failed:5};
  return rows.map(function(row,index){var state=profileHealth(row,now).state;return {row:row,index:index,rank:state==='healthy'&&row.id===selected?0:ranks[state]};}).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).map(function(entry){return entry.row;});
}
function healthBadge(profile){
  var health=profileHealth(profile,Date.now()/1000);
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
function renderCascadePath(status){
  var model=cascadePathModel(status,Date.now()/1000);
  var rows=status.profiles||[],nextRow=rows.filter(function(p){return p.id===model.next;})[0];
  var legendKeys=[];
  var groups=model.groups.map(function(g){
    return E('section',{'class':'hv-auto-node hv-cascade-group'},[
      E('div',{'class':'hv-cascade-head'},[E('strong',{},g.protocol),E('span',{},bi('Group: ','Группа: ')+g.channel)]),
      E('ul',{'class':'hv-cascade-list'},g.servers.map(function(s){
        var p=s.profile,h=profileHealth(p,Date.now()/1000);
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
function controllerTransitionMarks(events){
  var marks=Object.create(null),committed=Object.create(null),attempted=Object.create(null),returned=Object.create(null);
  (events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}).forEach(function(event){
    var id=event.attempt_id||event.sequence;
    if(event.trial)return;
    if(event.state==='APPLYING'&&!attempted[id]){attempted[id]=true;marks[event.sequence]={from:1,to:2,confirmed:false};}
    if(event.state==='COMMITTED'&&!committed[id]){committed[id]=true;marks[event.sequence]={from:1,to:2,confirmed:true};}
    if(event.state==='ROLLED-BACK'&&event.original_restored===true&&committed[id]&&!returned[id]){returned[id]=true;marks[event.sequence]={from:2,to:1,confirmed:true};}
  });
  return marks;
}
function renderTransitionBadge(event,marks){
  var mark=marks[event.sequence];if(!mark)return null;
  var label=(mark.confirmed?bi('Confirmed switch: ','Подтверждённый переход: '):bi('Switch attempt: ','Попытка перехода: '))+mark.from+' → '+mark.to;
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
    row(bi('Last 7 days','Последние 7 дней'),health.weekly||{},history.weekly||{})].concat(months.map(function(month){
      return row(month,(health.months||{})[month]||{},(history.months||{})[month]||{});
    }));
}
async function fetchStoredStatistics(kind,call){
  var after=0,until=0,events=[],summary=null,asOf=null;
  for(var page=0;page<101;page++){
    var response=await call(kind,after,until);
    if(!response||response.kind!==kind||!Array.isArray(response.events)||response.events.length>100||
       !Number.isSafeInteger(response.until)||response.until<0||typeof response.has_more!=='boolean')throw new Error('STATISTICS-REPLY');
    if(summary===null){summary=response.summary;until=response.until;asOf=response.as_of;}
    if(response.until!==until||!Number.isSafeInteger(response.next_after)||response.next_after<after||response.next_after>until)throw new Error('STATISTICS-CURSOR');
    var previous=after;
    response.events.forEach(function(event){if(!Number.isSafeInteger(event.sequence)||event.sequence<=previous||event.sequence>until)throw new Error('STATISTICS-SEQUENCE');previous=event.sequence;});
    if(response.events.length&&response.next_after!==previous)throw new Error('STATISTICS-CURSOR');
    events=events.concat(response.events);
    if(!response.has_more)return {kind:kind,as_of:asOf,detail_days:7,summary:summary,events:events};
    if(response.next_after<=after)throw new Error('STATISTICS-CURSOR');after=response.next_after;
  }
  throw new Error('STATISTICS-PAGE-LIMIT');
}
function renderStoredStatistics(status){
  var history=status.native_history||{},health=(status.accounting||{}).reliability||{},rows=storedStatisticsRows(status);
  var headings=[bi('Period','Период'),bi('Outages','Эпизоды отказа'),bi('Failed checks','Неудачные проверки'),
    bi('Attempts','Попытки'),bi('Confirmed switches','Подтверждённые переключения'),bi('Automatic','Автоматические'),bi('Manual','Ручные'),bi('Returns since update','Возвраты с обновления'),bi('Auto observed, hours','Наблюдение Auto, часов')];
  var table=E('table',{'class':'table hv-recovery-table'},[E('tr',{},headings.map(function(label){return E('th',{'scope':'col'},label);}))].concat(rows.map(function(row){
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
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Saved outage and switching statistics','Сохранённая статистика сбоев и переключений')),
    E('p',{},bi('Detailed incidents: last 7 days. Monthly and lifetime counters survive detail expiry and service restart. A repeated status of one transaction is counted once. Missing data is shown as —.','Подробные события: последние 7 дней. Месячные и общие счётчики сохраняются после удаления старых подробностей и перезапуска службы. Повторные статусы одной транзакции считаются один раз. Нет данных — прочерк.')),
    E('p',{},bi('Outages are observed failure episodes; several failed probes may belong to one outage. Auto time includes only observed intervals. Old missing events and outage durations are not reconstructed.','Сбой — наблюдаемый эпизод отказа; в нём может быть несколько неудачных проверок. Время Auto включает только наблюдавшиеся интервалы. Утраченные старые события и длительность сбоев не восстанавливаются.')),
    E('p',{},bi('Counter coverage: ','Покрытие счётчиков: ')+(history.counter_accuracy||bi('No saved controller counters','Нет сохранённых счётчиков контроллера'))),
    (health.details_dropped||history.detail_budget_dropped)?E('p',{'role':'status'},bi('Detail storage limit was reached; aggregate counters are retained.','Достигнут предел подробных событий; сводные счётчики сохранены.')):null,
    E('div',{'class':'hv-dv-tablewrap'},[table]),button,note].filter(Boolean));
}
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
    var fmt=function(v){return v==null?'—':v.toFixed(1);};
    while(summaryHost.firstChild)summaryHost.removeChild(summaryHost.firstChild);
    summaryHost.appendChild(E('table',{'class':'table hv-recovery-table'},[
      E('tr',{'class':'tr table-titles'},[E('th',{'scope':'col'},bi('Measure','Показатель')),E('th',{'scope':'col'},bi('Value','Значение'))]),
      [[bi('Attempts','Попытки'),s.attempts],
       [bi('Known outcome','Известный результат'),s.known_outcomes],
       [bi('Pending or unknown','Ожидание или неизвестно'),s.unknown_or_pending],
       [bi('Trial attempts','Тестовые попытки'),s.trial_attempts],
       [bi('Automatic attempts','Автоматические попытки'),s.automatic_attempts],
       [bi('Verified outcome ratio (including trials)','Доля подтверждённых результатов (включая тесты)'),s.success_ratio==null?'—':(s.success_ratio*100).toFixed(1)+'%'],
       [bi('Recovery time, median (s)','Время восстановления, медиана (с)'),fmt(s.median)],
       [bi('Recovery time, P95 (s)','Время восстановления, P95 (с)'),fmt(s.p95)],
       [bi('Recovery time, worst (s)','Время восстановления, максимум (с)'),fmt(s.worst)]].map(function(r){return E('tr',{'class':'tr'},[E('td',{'class':'td'},r[0]),E('td',{'class':'td'},String(r[1]))]);})].reduce(function(a,b){return a.concat(b);},[])));
    while(groupHost.firstChild)groupHost.removeChild(groupHost.firstChild);
    var groups=recoveryGroups(rows,status.profiles||[],window.start,window.end);
    var kindTitle={server:bi('By server','По серверам'),channel:bi('By group (channel)','По группам (каналам)'),protocol:bi('By protocol','По протоколам')};
    Object.keys(groups).forEach(function(kind){
      if(!groups[kind].length)return;
      groupHost.appendChild(E('h4',{},ownGet(kindTitle,kind)||kind));
      groupHost.appendChild(E('table',{'class':'table hv-recovery-table'},[E('tr',{'class':'tr table-titles'},[bi('Name','Имя'),bi('Successful / known','Удачных / известных'),bi('P95, s','P95, с'),bi('Failures in a row','Сбоев подряд')].map(function(t){return E('th',{'scope':'col'},t);}))].concat(groups[kind].map(function(g){var m=g.metrics;
        return E('tr',{'class':'tr'},[E('td',{'class':'td'},g.name),E('td',{'class':'td'},(m.committed+m.trials_passed)+' / '+m.known_outcomes),E('td',{'class':'td'},m.p95==null?'—':m.p95.toFixed(1)),E('td',{'class':'td'},String(m.max_consecutive_failures))]);}))));
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
  table=E('table',{'class':'table hv-recovery-table'},[E('tr',{},[bi('Time (UTC)','Время (UTC)'),'№',bi('From','Откуда'),bi('To','Куда'),bi('Outcome','Итог'),bi('Seconds','Секунд'),bi('Stages','Этапы'),bi('Codes','Коды'),''].map(function(h){return E('th',{'scope':'col'},h);}))]);
  rows.forEach(function(r){
    var detail=E('button',{'type':'button','class':'cbi-button','click':function(){showIncident(r);}},bi('Details','Подробности'));
    var evidence=r.probe_evidence&&typeof r.probe_evidence==='object'&&Object.keys(r.probe_evidence).length?' · '+Object.keys(r.probe_evidence).map(function(k){return k+'='+String(r.probe_evidence[k]);}).join(', '):'';
    table.appendChild(E('tr',{'data-recovery-start':String(r.start)},[stamp(r.start),String(r.id),r.source,r.target,r.outcome,r.duration==null?'—':String(r.duration),
      r.phases.map(function(p){return p.state;}).join(' → ')||'—',(r.codes.join(' · ')||'—')+evidence].map(function(v){return E('td',{},v);}).concat([E('td',{},detail)])));
  });
  update();
  var stamps=(history.events||[]).map(function(e){return e.time;}).filter(function(at){return Number.isFinite(at)&&at>=0&&at<=253402300799;});
  var latest=stamps.length?Math.max.apply(null,stamps):null;
  var age=latest==null?bi('No retained event timestamp','Нет сохранённых отметок времени событий'):latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' '+bi('s since the latest retained event','с прошло с последнего сохранённого события');
  return E('section',{'class':'hv-chart-card'},[E('h2',{},bi('Transition evidence and recovery','Подтверждения переходов и восстановления')),
    E('p',{},bi('Based only on the events the router kept. Gaps are shown as unknown, never guessed.','Основано только на событиях, которые сохранил роутер. Пропуски показываются как неизвестные, а не угадываются.')),
    E('p',{},bi('Covers only the events kept on the router. This is not a measure of home-network uptime.','Охватывает только события, сохранённые на роутере. Это не показатель доступности домашней сети.')),
    E('p',{},age),
    E('p',{'class':'hv-ready-intro'},bi('Calendar boundaries: ','Границы дней: ')+(history.timezone||'Europe/Berlin')+bi('. Event times are in UTC. Durations are measured from the retained APPLYING event to the event that confirmed the outcome, not the full outage. Retry episode numbers describe what the controller saw, not certified LAN outages. Categories overlap and must not be added up.','. Время событий указано в UTC. Длительность считается от сохранённого события APPLYING до события, подтвердившего результат, а не как полный простой. Номера повторных эпизодов описывают то, что видел контроллер, а не подтверждённые сбои LAN. Категории пересекаются, их нельзя суммировать.')),
    renderStoredStatistics(status),period,summaryHost,groupHost,exports,table]);
}

function renderDecisionExplanation(status,inventory){
  status=status||{};inventory=inventory||{};
  var explanation=status.decision_explanation||{},diagnosis=explanation.diagnosis||{},native=status.native_failover||{},settings=inventory.settings||{};
  var now=Date.now()/1000;
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
  var needFail=explanation.required_failures,needGood=explanation.required_successes;
  var failMet=fresh&&explanation.source_failure_streak_met===true,goodMet=fresh&&explanation.reserve_success_streak_met===true;
  function line(kind,title,text){return E('li',{'class':'hv-why-line'},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('div',{},[E('b',{},title),E('p',{},text)])]);}
  var state=native.state;
  var next;
  if(!fresh)next=bi('Current control and measurements are unknown. No switch or automatic return can be predicted from stale data.','Текущее управление и измерения неизвестны. По устаревшим данным нельзя предсказывать переключение или автоматический возврат.');
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
  if(vendor)next+=' '+bi('Application planning gate: ','Условие планировщика приложения: ')+vendorCoordinationText(vendor)+'.';
  var code=native.reason||native.state,techCode=typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)?code:null;
  return E('section',{'class':'hv-chart-card hv-why'},[
    E('h3',{},bi('Why the planner proposes or waits','Почему планировщик предлагает или ждёт')),
    E('p',{},bi('Failure and success thresholds describe router probe evidence. They do not prove firmware attempts are exhausted or authorize Auto. Tunnel identity, coordination, controller policy and independent LAN verification remain separate conditions.','Пороги сбоев и успешных проверок описывают результаты проверок с роутера. Они не доказывают завершение попыток прошивки и не разрешают Auto. Идентичность туннеля, координация, политика контроллера и независимая проверка LAN остаются отдельными условиями.')),
    E('ul',{'class':'hv-why-list'},[
      line(row[0],bi('What the router sees on the VPN in use','Что роутер видит на используемом VPN'),bi(row[1],row[2])),
      line(!fresh?'grey':failMet?'red':'green',bi('Has the VPN in use failed enough times?','Отказал ли используемый VPN достаточное число раз?'),(failMet?bi('Yes.','Да.'):bi('No.','Нет.'))+' '+bi('Auto needs '+(needFail||'—')+' failed checks in a row.','Auto нужно '+(needFail||'—')+' неудачных проверок подряд.')),
      line(!fresh?'grey':goodMet?'green':'yellow',bi('Has the reserve met the router probe threshold?','Достигнут ли порог проверок резерва с роутера?'),(goodMet?bi('Yes.','Да.'):bi('Not yet.','Пока нет.'))+' '+bi('Auto needs '+(needGood||'—')+' good checks in a row.','Auto нужно '+(needGood||'—')+' успешных проверок подряд.'))]),
    E('p',{'class':'hv-why-next'},[E('strong',{},bi('Evidence and next review: ','Данные и дальнейшая проверка: ')),next]),
    E('p',{'class':'hv-why-note'},bi('These checks are made by the router itself, so they show whether the VPN tunnels work, not what your computer sees. That is why every switch also needs the LAN helper to confirm it.','Эти проверки делает сам роутер, поэтому они показывают, работают ли VPN-туннели, а не то, что видит ваш компьютер. Поэтому каждое переключение дополнительно подтверждает LAN-помощник.')),
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
  var clock=function(seconds){return new Date(seconds*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'});};
  // The idle line shows the latest automatic check, so it always says something true.
  var rows=(status.profiles||[]).filter(function(p){return p.interface;}),working=rows.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';}).length;
  var latest=rows.reduce(function(newest,p){return Number.isFinite(p.time)&&p.time>newest?p.time:newest;},0);
  var summary=function(time,total,ok){return bi('Last check ','Последняя проверка ')+clock(time)+'\n'+ok+' '+bi('of','из')+' '+total+' '+bi('VPNs work','VPN работают');};
  var text;
  if(model.state==='EMPTY')text=bi('No VPN is connected right now, so there was nothing to check.','Сейчас ни один VPN не подключён, проверять нечего.');
  else if(model.state==='COMPLETED'&&model.checked!=null&&model.time)text=summary(model.time,model.checked,model.checked-model.failed);
  else if(model.state==='IDLE')text=rows.length&&latest?summary(latest,rows.length,working):bi('No VPN is connected right now.','Сейчас ни один VPN не подключён.');
  else text={QUEUED:bi('Request sent. Waiting for the router…','Запрос отправлен. Ждём роутер…'),RUNNING:bi('Checking now…','Идёт проверка…'),FAILED:bi('The check could not run. Make sure the monitor is running.','Проверку выполнить не удалось. Убедитесь, что мониторинг запущен.'),UNAVAILABLE:bi('No answer from the router, so no result.','Роутер не ответил, результата нет.')}[model.state]||'';
  connectivityControl.button.disabled=connectivityBusy||model.busy||status.error==='SERVICE-STOPPED';
  connectivityControl.message.textContent=text+(model.code?' · '+model.code:'');
  connectivityControl.message.setAttribute('data-check-state',model.state);
  // A cell belongs to a named channel; do not sort healthy cells ahead of failed ones.
  if(connectivityControl.bar){
    var bar=connectivityControl.bar;while(bar.firstChild)bar.removeChild(bar.firstChild);
    var ids=connectivityControl.settings||{},native=status.native_failover||{},path=status.channel_path||{};
    var primary=ids.plan_source||path.source_profile_id||native.source,reserve=ids.plan_target||path.target_profile_id||native.target;
    var cells=rows.slice(0,16).map(function(p,index){return {profile:p,label:p.id===primary?bi('Primary channel','Основной канал'):p.id===reserve?bi('Reserve channel','Резервный канал'):bi('VPN channel ','VPN-канал ')+(index+1)};});
    cells.sort(function(a,b){return (a.profile.id===primary?0:a.profile.id===reserve?1:2)-(b.profile.id===primary?0:b.profile.id===reserve?1:2);});
    cells.forEach(function(cell){var healthy=profileHealth(cell.profile,Date.now()/1000).state==='healthy';bar.appendChild(E('span',{'class':'hv-check-channel'},[E('small',{},cell.label),E('span',{'class':'hv-check-cell'+(healthy?' hv-check-cell-ok':''),'title':cell.label+' · '+(healthy?bi('Internet available','Интернет доступен'):bi('Internet check not passed','Проверка Интернета не пройдена'))})]));});
    bar.hidden=!cells.length;bar.setAttribute('aria-label',working+' '+bi('of','из')+' '+rows.length+' '+bi('VPNs work','VPN работают'));
  }
  if(connectivityControl.next){
    connectivityControl.next.hidden=!rows.length;
    connectivityControl.next.textContent=working?bi('Step 2: turn on Auto with the button in “Automatic VPN failover” below.','Шаг 2: включите Auto кнопкой в блоке «Автоматическое переключение VPN» ниже.'):bi('No VPN works right now. Check the VPN profiles in GL.iNet, then press the button again.','Сейчас ни один VPN не работает. Проверьте VPN-профили в GL.iNet и нажмите кнопку ещё раз.');
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
  'CONFIG-STORAGE-FREE':['Free storage','Свободное место','At least 1 MB for settings','Не менее 1 МБ для настроек','💾']
};
var READINESS_TESTED_FIRMWARE='4.11.0';
function readinessCheckState(state){return state==='pass'?'ok':state==='fail'?'bad':state==='waiting'?'waiting':'unknown';}
function readinessTile(code,state){
  var r=Object.prototype.hasOwnProperty.call(READINESS_CHECKS,code)?READINESS_CHECKS[code]:[code,code,'',' ','•'];
  var st=readinessCheckState(state);
  var word=st==='ok'?bi('OK','Есть'):st==='bad'?bi('Missing','Нет'):st==='waiting'?bi('Waiting…','Ожидается…'):bi('Not known','Неизвестно');
  var mark=st==='ok'?'✓':st==='bad'?'✗':st==='waiting'?'…':'?';
  return E('div',{'class':'hv-rd-tile hv-rd-'+st},[E('span',{'class':'hv-rd-mark','aria-hidden':'true'},mark),E('div',{'class':'hv-rd-tile-text'},[E('strong',{},bi(r[0],r[1])),E('small',{},bi(r[2],r[3]))]),E('b',{'class':'hv-rd-word'},word)]);
}
function readinessInfo(icon,label,value,waiting){
  return E('div',{'class':'hv-rd-info'+(waiting?' hv-rd-info-waiting':'')},[E('span',{'class':'hv-rd-info-icon','aria-hidden':'true'},icon),E('small',{},label),waiting?E('span',{'class':'hv-rd-skeleton'},bi('waiting for data…','ожидаются данные…')):E('strong',{},value)]);
}
var PREPARATION_CHECKS={
  'PREP-HNAT-CONFIG':['Hardware acceleration stays disabled','Аппаратное ускорение остаётся выключенным'],
  'PREP-WGCLIENT1-AUTOSTART':['WireGuard automatic startup is disabled','Автозапуск WireGuard выключен'],
  'PREP-OVPNCLIENT1-AUTOSTART':['OpenVPN automatic startup is disabled','Автозапуск OpenVPN выключен'],
  'PREP-STOCK-VPN-BOOT':['Stock VPN startup does not compete','Штатный автозапуск VPN не конкурирует'],
  'PREP-SFE-BOOT':['SFE startup is disabled','Автозапуск SFE выключен'],
  'PREP-SFE-AUTOLOAD':['SFE autoload is preserved outside startup','Автозагрузка SFE сохранена вне запуска'],
  'PREP-SFE-RUNTIME':['Software acceleration is not loaded','Программное ускорение не загружено']
};
function preparationModel(status,now){
  var ready=readinessModel(status,now),data=(status&&status.system_readiness||{}).preparation;
  if(!ready.environmentFresh||!data||data.scope!=='persistent-mt3000-preparation')return {state:'unknown',checks:[]};
  var rows=Array.isArray(data.checks)?data.checks:[],seen={},valid=true;
  rows.forEach(function(row){if(!row||!Object.prototype.hasOwnProperty.call(PREPARATION_CHECKS,row.code)||seen[row.code]||['pass','fail','unknown'].indexOf(row.state)<0)valid=false;else seen[row.code]=row.state;});
  if(data.state==='unsupported'&&!rows.length)return {state:'unsupported',checks:[]};
  if(!valid||rows.length!==Object.keys(PREPARATION_CHECKS).length)return {state:'unknown',checks:[]};
  return {state:Object.keys(seen).every(function(code){return seen[code]==='pass';})?'pass':'incomplete',checks:rows};
}
function renderPreparation(status,now){
  var m=preparationModel(status,now);
  var explanation=m.state==='unsupported'?bi('These persistent checks apply to the tested MT3000 setup. This is not a compatibility verdict for another model.','Эти постоянные настройки проверяются для испытанной конфигурации MT3000. Это не заключение о совместимости другой модели.'):
    m.state==='unknown'?bi('Fresh preparation evidence is not available.','Свежие сведения о подготовке отсутствуют.'):
    bi('These settings keep the tested MT3000 preparation across reboot. A passing check does not start a VPN or authorize Auto.','Эти настройки сохраняют проверенную подготовку MT3000 после перезагрузки. Успешная проверка не запускает VPN и не разрешает Auto.');
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Persistent router preparation','Постоянная подготовка роутера')),E('p',{},explanation),E('ul',{},m.checks.map(function(row){var label=PREPARATION_CHECKS[row.code],word=row.state==='pass'?bi('OK','Готово'):row.state==='fail'?bi('Needs preparation','Нужна подготовка'):bi('Not verified','Не проверено');return E('li',{},bi(label[0],label[1])+': '+word+' · '+row.code);})),E('p',{'class':'hv-ready-note'},bi('Review DNS, runtime acceleration, supported firmware and recovery instructions before changing settings. Restoring stock startup or acceleration invalidates native readiness.','Перед изменениями проверьте DNS, текущее ускорение, поддерживаемую прошивку и инструкцию восстановления. Возврат штатного автозапуска или ускорения отменяет готовность к переключению.'))]);
}
function renderReadiness(status,inventory){
  var now=Date.now()/1000,m=readinessModel(status,now),b=m.board||{};
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
    partial:[bi('Almost there','Почти готово'),bi('Some parts are not confirmed yet.','Часть пунктов ещё не подтверждена.')],
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
    E('h3',{},bi('Is the system ready? Look for green.','Готова ли система? Ищите зелёный.')),
    E('p',{},bi('This page checks that your router has everything the program needs. It only shows the result: you do not need to press or start anything. When every item below is green, your system is ready to work; Auto itself is turned on later with the button on the Overview.','Эта страница проверяет, что на роутере есть всё, что нужно программе. Она только показывает результат: нажимать и запускать ничего не нужно. Когда все пункты ниже зелёные, ваша система готова к работе; сам Auto включается позже кнопкой на «Обзоре».')),
    E('ul',{'class':'hv-plan-legend'},[
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-green','aria-hidden':'true'}),bi(' Green ✓: this part is there and works.',' Зелёный ✓: эта часть есть и работает.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-grey','aria-hidden':'true'}),bi(' Grey …: the router has not reported yet. Wait a minute; it appears by itself after monitoring starts.',' Серый …: роутер ещё не сообщил. Подождите минуту; после запуска мониторинга это появится само.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-red','aria-hidden':'true'}),bi(' Red ✗: something is missing. Press its code to read what to do.',' Красный ✗: чего-то не хватает. Нажмите на его код, чтобы прочитать, что делать.')])])]);
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
      [['Allow session reconnection','Разрешить переподключение сессий'],['Switching to another VPN breaks open connections for a few seconds (calls, downloads). Tick it only if you accept that.','При переходе на другой VPN открытые соединения рвутся на несколько секунд (звонки, загрузки). Отметьте, только если вас это устраивает.'],['Tick it','Отметить']]
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
      [['Cooldown, seconds','Пауза, секунд'],['Minimum time between two switches. Range 60–1800.','Минимальное время между двумя переключениями. Диапазон 60–1800.'],['300','300']],
      [['Minimum stay, seconds','Минимальное пребывание, секунд'],['How long to stay on the new VPN before another switch is allowed. Range 60–3600.','Сколько оставаться на новом VPN, прежде чем разрешить следующее переключение. Диапазон 60–3600.'],['300','300']],
      [['Return rule and checks','Правило возврата и проверки'],['Return when the primary is healthy (needs 2–10 good checks and 30–600 s of calm), or hold the reserve.','Возвращаться, когда основной исправен (нужно 2–10 удачных проверок и 30–600 с спокойствия), или держать резерв.'],['5 checks · 120 s','5 проверок · 120 с']]
    ]},
  monitoring:{
    what:['How often the program checks your VPNs and how much it keeps.','Как часто программа проверяет ваши VPN и сколько хранит.'],
    why:['Checks are what the statistics and Auto rely on. More frequent checks react faster but use a little more traffic and router time.','На проверках основаны статистика и Auto. Частые проверки реагируют быстрее, но чуть больше нагружают трафик и роутер.'],
    fields:[
      [['Check interval, seconds','Интервал проверок, секунд'],['Pause between checks of each connected VPN. Range 10–300.','Пауза между проверками каждого подключённого VPN. Диапазон 10–300.'],['30 (default)','30 (по умолчанию)']],
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
  if(status.rpc_error)return out('problem','red','!',bi('Cannot read the monitor','Не удаётся прочитать мониторинг'),bi('The page could not get the status from the router. Reload the page and sign in again; see Help → “The page is old, empty or says the monitor is not running”.','Страница не смогла получить статус от роутера. Обновите страницу и войдите снова; см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'),'RPC-UNAVAILABLE');
  if(enabled&&fresh)return out('ok','green','✓',bi('Monitor is running','Мониторинг работает'),bi('Fresh data arrived '+Math.max(0,Math.round(age))+' s ago. Each connected VPN is checked about every '+(Number(settings.interval)||30)+' seconds.','Свежие данные пришли '+Math.max(0,Math.round(age))+' с назад. Каждый подключённый VPN проверяется примерно раз в '+(Number(settings.interval)||30)+' с.'));
  if(enabled&&(recent||(!status.error&&age<=300)))return out('transition','yellow','⟳',bi('Starting or catching up','Запускается или догоняет'),bi('The monitor is switched on and the first fresh data is not here yet. This takes up to a minute.','Мониторинг включён, первых свежих данных ещё нет. Это занимает до минуты.'));
  if(enabled)return out('problem','red','!',bi('Switched on, but not running','Включён, но не работает'),bi('The router program is not producing data.','Программа на роутере не выдаёт данные.'),status.error||'STATUS-STALE');
  if(fresh)return out('transition','yellow','⟳',bi('Stopping','Останавливается'),bi('The monitor is switched off; the last data is still on screen. It stops within a minute.','Мониторинг выключен; на экране ещё последние данные. Он остановится в течение минуты.'));
  return out('off',null,'○',bi('Monitor is off','Мониторинг выключен'),bi('Nothing is being checked and no statistics are collected. Auto cannot work without the monitor.','Ничего не проверяется и статистика не собирается. Без мониторинга Auto работать не может.'));
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
  var now=Date.now()/1000,light=monitorLightModel(status,inventory,now,monitorStartedRecently(now)),n=monitorNumbers(status,now);
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
        if(result&&result.accepted===true){try{window.sessionStorage.setItem('homensai-vpn-monitor-requested',String(Date.now()/1000));}catch(e){}window.location.reload();return;}
        ui.addNotification(null,E('p',{},(result&&result.code)||'MONITOR-UNKNOWN'));
      }).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){monitorBusy=false;button.disabled=false;});
    }},bi('Start monitoring','Запустить мониторинг'));
  }
  host.appendChild(E('span',{'class':'hv-monitor-lamp hv-monitor-lamp-'+tone,'role':'img','aria-label':title}));
  host.appendChild(E('div',{'class':'hv-check-text'},[E('strong',{},title),E('small',{},stats),light.key==='ok'?E('small',{'class':'hv-check-status'},bi('Checks every '+(Number((inventory.settings||{}).interval)||30)+' s · last data '+Math.max(0,Math.round(now-status.time))+' s ago','Проверка каждые '+(Number((inventory.settings||{}).interval)||30)+' с · последние данные '+Math.max(0,Math.round(now-status.time))+' с назад')):null,button].filter(Boolean)));
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
    E('p',{},bi('Monitoring is always on. About every '+(Number(settings.interval)||30)+' seconds it checks each connected VPN (can it open a website and resolve a name through it). From these checks the charts above are built: how fast each server answers, and how long each one worked or failed. History starts when monitoring first started; nothing is guessed for earlier time.','Мониторинг всегда включён. Примерно каждые '+(Number(settings.interval)||30)+' с он проверяет каждый подключённый VPN (может ли он открыть сайт и найти адрес). Из этих проверок построены графики выше: как быстро отвечает каждый сервер и сколько времени он работал или не работал. История начинается с первого запуска мониторинга; за более раннее время ничего не придумывается.')),
    E('p',{'class':'hv-ready-intro'},bi('Where it is stored: on the router itself, in /etc/homensai-vpn (saved '+(every?'about every '+every+' min':'periodically')+'; the interval can be changed in Settings → Advanced settings → Monitoring parameters). Nothing leaves the router.','Где хранится: на самом роутере, в /etc/homensai-vpn (сохраняется '+(every?'примерно раз в '+every+' мин':'периодически')+'; интервал можно изменить в «Настройки» → «Расширенные настройки» → «Параметры мониторинга»). Ничего не уходит с роутера.'))]);
}

var ADVANCED_KEYS=['tests','traffic','services','events'];
var PAGE_SUBTITLES={
  overview:['Your VPNs, how healthy they are, and what the router did about it.','Ваши VPN, насколько они исправны и что сделал роутер.'],
  channels:['Every VPN profile on the router and whether it works right now.','Все VPN-профили роутера и работают ли они прямо сейчас.'],
  statistics:['How your VPNs behaved over time.','Как вели себя ваши VPN со временем.'],
  settings:['Set up the monitor, your two VPNs, reports and recovery rules.','Настройка мониторинга, двух VPN, отчётов и правил восстановления.'],
  start:['First steps: terms, training, monitoring, your two VPNs and Auto. This page opens first until they are done.','Первые шаги: условия, обучение, мониторинг, два ваших VPN и Auto. Эта страница открывается первой, пока они не выполнены.'],
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
  var c=serverCounts(status,inventory,rows,Date.now()/1000);
  function tile(value,label,hint){return E('div',{'class':'hv-count'},[E('strong',{},String(value)),E('span',{},label),hint?E('small',{},hint):null].filter(Boolean));}
  var tiles=[
    tile(c.onRouter,bi('VPN profiles on the router','VPN-профилей на роутере'),bi('Added in GL.iNet → VPN','Добавлены в GL.iNet → VPN')),
    tile(c.connected,bi('Connected now','Подключено сейчас'),bi('Only these are checked','Проверяются только они')),
    tile(c.working+' / '+c.connected,bi('Work (internet passes)','Работают (интернет проходит)'),bi('From the latest check','По последней проверке'))
  ];
  var note=bi('This list is read from your router. A VPN profile you add in GL.iNet (VPN → VPN Dashboard) appears here by itself within about a minute, and a removed one disappears, so the numbers can change at any time. Profiles that are not connected are listed so you can see them; this program never connects them. To add, remove or connect servers use the router’s VPN page (button below).','Список берётся с вашего роутера. VPN-профиль, добавленный в GL.iNet (VPN → VPN Dashboard), появляется здесь сам примерно за минуту, а удалённый исчезает, поэтому числа могут меняться в любой момент. Неподключённые профили показаны, чтобы вы их видели; эта программа их никогда не подключает. Чтобы добавить, убрать или подключить серверы, используйте страницу VPN на роутере (кнопка ниже).');
  var hidden=c.hidden>0?E('p',{'class':'hv-count-note'},c.hidden+' '+bi('profile(s) are hidden because you chose which servers to monitor (Settings → System).','профилей скрыто, потому что вы выбрали, какие серверы наблюдать («Настройки» → «Система»).')):null;
  return E('section',{'class':'hv-chart-card hv-server-summary'},[E('h3',{},bi('Your VPN servers','Ваши VPN-серверы')),E('div',{'class':'hv-counts'},tiles),E('p',{},note),hidden].filter(Boolean));
}

/* Two levels of recovery: observe configured vendor tunnels; explain the application's
   read-only inter-tunnel planning gate. Labels never establish tunnel identity or cause. */
var VENDOR_COORDINATION_TEXT={
  'CROSS-TUNNEL-READY':['Candidate for verification','Кандидат для проверки'],
  'VENDOR-SAME-TUNNEL':['Within one router tunnel: the application holds its own proposal','Один туннель роутера: приложение удерживает собственное предложение'],
  'VENDOR-SETTLING':['Waiting for the configured identity observation window','Ожидание окна наблюдения за конфигурацией'],
  'VENDOR-IDENTITY-UNKNOWN':['Router tunnel identity is unknown','Идентичность туннеля роутера неизвестна'],
  'OBSERVATION-STALE':['Observations are stale','Наблюдения устарели'],
  'PROFILE-IDENTITY-CHANGED':['Profile binding changed; fresh checks are needed','Привязка профиля изменилась; нужны новые проверки'],
  'UPLINK-LINK-DOWN':['Uplink reports link down; VPN switching is held','Uplink сообщает об отключении; переключение VPN удерживается'],
  'PLAN-CONFIG':['The selected tunnel pair needs review','Выбранную пару туннелей нужно проверить']
};
function vendorTunnelId(value){return typeof value==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.-]{1,64}$/.test(value)?value:null;}
function vendorProfileId(value){return typeof value==='string'&&/^[A-Za-z0-9_.:-]{1,96}$/.test(value)?value:null;}
function vendorLabel(value){return typeof value==='string'&&Array.from(value).length<=64&&value.trim()&&!/[\p{C}\p{Zl}\p{Zp}]/u.test(value)?value:null;}
function vendorProtocol(value){return value==='openvpn'?'OpenVPN':value==='wireguard'?'WireGuard':bi('Unknown protocol','Неизвестный протокол');}
function vendorFresh(stamp,now,age){return typeof stamp==='number'&&Number.isFinite(stamp)&&stamp>=0&&stamp<=now&&now-stamp<=age;}
function vendorDiagnosticsModel(status,inventory,now){
  status=status&&typeof status==='object'?status:{};inventory=inventory&&typeof inventory==='object'?inventory:{};
  var settings=inventory.settings||{},interval=Number(settings.interval),age=Number.isInteger(interval)&&interval>=10&&interval<=300?Math.max(30,interval*3):90;
  var observation=status.vendor_observation,available=!!observation&&observation.version===1&&Array.isArray(observation.groups);
  var fresh=available&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(observation.time,now,age);
  var profiles=Array.isArray(status.profiles)?status.profiles.slice(0,400):[],metadata=Array.isArray(inventory.servers)?inventory.servers.slice(0,400):[],profileMap=Object.create(null),metadataMap=Object.create(null);
  profiles.forEach(function(p){if(p&&vendorProfileId(p.id))profileMap[p.id]=Object.prototype.hasOwnProperty.call(profileMap,p.id)?null:p;});
  metadata.forEach(function(p){if(p&&vendorProfileId(p.profile))metadataMap[p.profile]=Object.prototype.hasOwnProperty.call(metadataMap,p.profile)?null:p;});
  function profileName(id){var row=metadataMap[id],measured=profileMap[id],configured=(Array.isArray(inventory.profiles)?inventory.profiles:[]).filter(function(p){return p&&p.id===id;})[0];return row&&vendorLabel(row.name)||measured&&vendorLabel(measured.name)||measured&&vendorLabel(measured.router_name)||configured&&vendorLabel(configured.name)||id||bi('Unknown','Неизвестно');}
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
  var native=(status||{}).native_failover||{},role=null;
  if((status||{}).rpc_error||!vendorFresh(native.time,now,30))return null;
  if(['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(native.state)>=0)role='target';
  else if(native.state==='OBSERVING'&&(native.certified===true||native.mode==='continuous-pair'&&native.readiness_verified===true))role='source';
  var row=role?vendorDisplayMember(status,inventory,role,now,native[role]):null;
  return row?row.id:null;
}
function vendorLamp(tone,label){return E('span',{},[E('span',{'class':'hv-check-lamp hv-check-'+({healthy:'green',failed:'red',pending:'yellow'}[tone]||'grey'),'aria-hidden':'true'}),label]);}
function vendorIdentityText(group){return group.state==='stable'?bi('Observed configuration stable','Наблюдаемая конфигурация стабильна'):group.state==='pending'?bi('Configuration observation is settling','Окно наблюдения за конфигурацией ещё не завершено'):bi('Configured identity unknown or stale','Идентичность конфигурации неизвестна или устарела');}
function vendorCoordinationText(model){var row=model.coordination.known?VENDOR_COORDINATION_TEXT[model.coordination.code]:null;return row?bi(row[0],row[1]):bi('Current application planning reason is unknown','Текущая причина решения планировщика неизвестна');}
function vendorDetailsLink(){return E('a',{'href':'#channels','click':function(event){if(typeof goToSection==='function'){event.preventDefault();goToSection('channels','hv-vendor-observation');}}},bi('Router tunnel observations and editable labels','Наблюдения туннелей роутера и редактируемые метки'));}
function renderVendorOverview(status,inventory){
  var m=vendorDiagnosticsModel(status,inventory,Date.now()/1000),stable=m.groups.filter(function(g){return g.state==='stable';}).length,pending=m.groups.some(function(g){return g.state==='pending';});
  var line=!m.available||!m.groups.length?bi('Router tunnel identity has not been observed yet.','Идентичность туннеля роутера пока не наблюдалась.'):!m.fresh?bi('Router configuration observations are stale; current identity is unknown.','Наблюдения конфигурации роутера устарели; текущая идентичность неизвестна.'):bi('Stable configured tunnel identities: ','Стабильных наблюдаемых конфигураций туннелей: ')+stable+' / '+m.groups.length;
  return E('section',{'class':'hv-chart-card','data-vendor-diagnostics':'overview'},[E('h3',{},bi('Two levels of VPN recovery','Два уровня восстановления VPN')),E('p',{},vendorLamp(pending?'pending':'unknown',line)),E('p',{'data-app-coordination':m.coordination.code||'UNKNOWN'},bi('App coordination: ','Координация приложения: ')+vendorCoordinationText(m)),E('small',{},bi('Within-tunnel server selection belongs to the router firmware. This app plans between tunnels/channels or OpenVPN and WireGuard. A stable configuration does not prove the firmware finished its attempts.','Выбор серверов внутри туннеля относится к штатной прошивке роутера. Приложение планирует переходы между туннелями/каналами либо OpenVPN и WireGuard. Стабильная конфигурация не доказывает завершение попыток прошивки.')),E('p',{},vendorDetailsLink())]);
}
function renderVendorChannels(status,inventory){
  var m=vendorDiagnosticsModel(status,inventory,Date.now()/1000);
  function value(label,text){return E('p',{},[E('strong',{},label+': '),String(text)]);}
  function anchor(id){var group=m.groups.filter(function(g){return g.id===id;})[0];return id?(id+' · '+bi('current configured profile: ','текущий наблюдаемый профиль: ')+(group&&group.current||bi('unknown','неизвестно'))):bi('Unknown — no trusted saved binding','Неизвестно — нет доверенной сохранённой привязки');}
  var body=[E('summary',{},bi('Router tunnels and application labels','Туннели роутера и метки приложения')),E('p',{},bi('Tunnel IDs are observed from exact router configuration bindings. Provider profile groups and editable app labels are descriptive metadata, not channel identity.','ID туннелей наблюдаются по точным привязкам конфигурации роутера. Группы профилей провайдера и редактируемые метки приложения — описательные метаданные, а не идентичность канала.')),value(bi('Selected source tunnel','Выбранный основной туннель'),anchor(m.source)),value(bi('Selected reserve tunnel','Выбранный резервный туннель'),anchor(m.target))];
  if(!m.source||!m.target)body.push(E('p',{},[bi('Choose an active profile for each required tunnel in Settings and save the selection; the bindings will be saved. ','Выберите активный профиль каждого нужного туннеля в настройках и сохраните выбор; привязки будут сохранены. '),E('a',{'href':'#settings'},bi('Open Settings','Открыть настройки'))]));
  if(!m.groups.length)body.push(E('p',{},bi('No verified router tunnel binding is available. Editable labels cannot fill this gap.','Проверенной привязки туннеля роутера пока нет. Редактируемые метки не заменяют эти данные.')));
  m.groups.slice().sort(function(a,b){function rank(g){return g.id===m.source?0:g.id===m.target?1:2;}return rank(a)-rank(b);}).slice(0,32).forEach(function(g){
    var health=g.health==='healthy'?bi('Healthy router HTTPS/DNS probe','Успешная проверка HTTPS/DNS с роутера'):g.health==='failed'?bi('Router probe failed','Проверка с роутера не прошла'):bi('Current profile health unknown','Здоровье текущего профиля неизвестно');
    body.push(E('section',{'data-vendor-tunnel':g.id,'data-vendor-state':g.state,'data-vendor-health':g.health,'style':'border-top:1px solid currentColor;padding-top:8px;margin-top:12px;min-width:0;overflow-wrap:anywhere'},[
      E('h4',{},vendorProtocol(g.protocol)+' · '+g.id),E('p',{},vendorLamp(g.state==='pending'?'pending':'unknown',vendorIdentityText(g))),value(bi('Observed configured profile','Наблюдаемый профиль конфигурации'),g.current?g.name+' · '+g.current:bi('Unknown or ambiguous','Неизвестно или неоднозначно')),value(bi('Provider profile group (metadata only)','Группа профилей провайдера (только метаданные)'),g.profileGroup||bi('Unknown','Неизвестно')),value(bi('App channel labels (editable)','Метки каналов приложения (редактируемые)'),g.labels.join(', ')||bi('No saved label observed','Сохранённая метка не наблюдалась')),E('p',{},vendorLamp(g.health,health)),E('p',{'data-vendor-reason':'unobserved'},bi('Reason for the change was not observed. Whether firmware finished all server attempts: unknown.','Причина смены не наблюдалась. Завершены ли все попытки прошивки: неизвестно.'))]));
  });
  if(m.groups.length>32)body.push(E('p',{},bi('Showing the first 32 observed tunnels.','Показаны первые 32 наблюдаемых туннеля.')));
  body.push(E('p',{'data-app-coordination':m.coordination.code||'UNKNOWN'},[E('strong',{},m.coordination.known?bi('Known app planning reason: ','Известная причина решения планировщика: '):bi('App planning reason: ','Причина решения планировщика: ')),vendorCoordinationText(m)]));
  if(m.coordination.settleUntil)body.push(value(bi('Identity observation window until (Europe/Berlin)','Окно наблюдения за конфигурацией до (Europe/Berlin)'),new Date(m.coordination.settleUntil*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})));
  body.push(E('p',{},bi('Read-only planning; this does not enable Auto, authorize route changes or certify GL-MT3000. Router probes do not establish LAN DNS, HTTPS, exit, IPv6 or Kill Switch acceptance.','Планирование без применения: оно не включает Auto, не разрешает изменения маршрутов и не подтверждает GL-MT3000. Проверки с роутера не подтверждают LAN DNS, HTTPS, выход, IPv6 и Kill Switch.')));
  return E('details',{'class':'hv-chart-card','id':'hv-vendor-observation','data-vendor-diagnostics':'channels','style':'min-width:0;overflow-wrap:anywhere'},body);
}
function renderVendorEvents(status,inventory){
  var m=vendorDiagnosticsModel(status,inventory,Date.now()/1000),names={'VENDOR-PROFILE-CHANGED':bi('Configured profile changed','Наблюдаемая конфигурация профиля изменилась'),'VENDOR-BINDING-CHANGED':bi('Configured tunnel binding changed','Наблюдаемая привязка туннеля изменилась'),'VENDOR-BINDING-UNKNOWN':bi('Configured binding became unknown','Привязка конфигурации стала неизвестной'),'VENDOR-FIRST-OBSERVATION':bi('First configured identity observed','Первое наблюдение конфигурации')};
  var content=m.events.length?E('ol',{},m.events.map(function(event){return E('li',{'data-vendor-event':event.code},[E('strong',{},names[event.code]),E('span',{},' · '+new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})+' · '+event.tunnel),E('p',{},(event.before||'—')+' → '+(event.after||'—')),E('small',{},bi('Reason for the change was not observed.','Причина смены не наблюдалась.'))]);})):E('p',{},bi('No recorded profile identity changes yet. This does not prove that the firmware made no attempts.','Записей о смене конфигурации профиля пока нет. Это не доказывает отсутствие попыток штатной прошивки.'));
  return E('details',{'class':'hv-chart-card','data-vendor-diagnostics':'events','style':'min-width:0;overflow-wrap:anywhere'},[E('summary',{},bi('Recent router configuration observations','Последние наблюдения конфигурации роутера')),!m.fresh?E('p',{},bi('Retained observations only; current router tunnel state is unknown.','Показаны только сохранённые наблюдения; текущее состояние туннеля роутера неизвестно.')):null,content,E('small',{},bi('At most 8 recent observations. Profile identity changes are not proof of automatic failover, its cause, or a verified LAN outcome.','Не более 8 последних наблюдений. Изменение профиля не доказывает автоматическое переключение, его причину или подтверждённый результат в LAN.'))].filter(Boolean));
}

/* Built-in help: what to do when something is wrong. Data are [English, Russian] pairs; commands are never translated. */
var HELP_TOPICS=[
  {id:'no-internet',open:true,
   title:["I have no internet","У меня пропал интернет"],
   when:["Devices on your network cannot open sites after Auto ran or after you changed VPN settings.","Устройства в сети не открывают сайты после работы Auto или после смены настроек VPN."],
   steps:[
    {t:["Use another connection to read this page (a phone with mobile data), or open this Help page on a device that still reaches the router address.","Откройте эту страницу через другое подключение (телефон с мобильным интернетом) или с устройства, которое ещё открывает адрес роутера."]},
    {t:["Open the router in the browser, go to Services → HomenS.AI Auto VPN → Overview. If the card says the router is still on the reserve, press “Return to primary”. The router checks the primary first and shows the result there.","Откройте роутер в браузере: «Службы» → HomenS.AI Auto VPN → «Обзор». Если в карточке написано, что роутер всё ещё на резерве, нажмите «Вернуться на основной». Роутер сначала проверит основной и покажет результат там же."]},
    {t:["If that does not help, connect to the router by SSH (see “How to connect by SSH”) and show its state. This only reads:","Если не помогло, подключитесь к роутеру по SSH (см. «Как подключиться по SSH») и посмотрите состояние. Эта команда только читает:"],c:"homensai-vpn-emergency show"},
    {t:["Stop the program’s own services (this changes no network settings):","Остановите собственные службы программы (сетевые настройки не меняются):"],c:"homensai-vpn-emergency stop-auto"},
    {t:["Remove only the program’s own traffic block. It prints what it removes. VPN rules and the GL.iNet Kill Switch stay:","Снимите только собственную блокировку трафика программы. Команда сообщает, что удалила. Правила VPN и Kill Switch GL.iNet остаются:"],c:"homensai-vpn-emergency remove-guard"},
    {t:["Test the internet on a computer. Then open the GL.iNet panel → VPN → VPN Dashboard and check that your primary VPN rule is first and the tunnels are connected.","Проверьте интернет на компьютере. Затем откройте панель GL.iNet → VPN → VPN Dashboard и убедитесь, что основной VPN стоит первым и туннели подключены."]},
    {t:["Still nothing? Reboot the router from the GL.iNet panel (System → Reboot). The program’s traffic block is not kept after a reboot.","Всё равно нет? Перезагрузите роутер из панели GL.iNet («Система» → «Перезагрузка»). Блокировка трафика программы после перезагрузки не сохраняется."]},
    {t:["After the internet is back, start the monitor again:","Когда интернет вернулся, снова запустите мониторинг:"],c:"homensai-vpn-emergency start"}
   ]},
  {id:"ssh",
   title:["How to connect by SSH","Как подключиться по SSH"],
   when:["You need a command line on the router for the steps in this Help.","Командная строка на роутере нужна для шагов в этой справке."],
   steps:[
    {t:["Make sure SSH is on. In the GL.iNet admin panel (usually http://192.168.8.1) open System → Security and check that SSH access from the local network is enabled. In LuCI it is System → Administration → SSH Access, interface lan. Menu names can differ slightly between firmware versions.","Убедитесь, что SSH включён. В панели GL.iNet (обычно http://192.168.8.1) откройте «Система» → «Безопасность» и проверьте, что SSH из локальной сети включён. В LuCI это «System» → «Administration» → «SSH Access», интерфейс lan. Названия пунктов могут немного отличаться в разных версиях прошивки."]},
    {t:["Windows: press the Windows key, type PowerShell and press Enter. Linux or macOS: open Terminal.","Windows: нажмите клавишу Windows, введите PowerShell и нажмите Enter. Linux или macOS: откройте «Терминал»."]},
    {t:["Type the command and press Enter (192.168.8.1 is the default router address; if yours differs, use the “Default gateway” from ipconfig on Windows or ip route on Linux):","Введите команду и нажмите Enter (192.168.8.1 — адрес роутера по умолчанию; если у вас другой, возьмите «Основной шлюз» из ipconfig в Windows или ip route в Linux):"],c:"ssh root@192.168.8.1"},
    {t:["Windows says ssh is not recognised? Install “OpenSSH Client” (Settings → Apps → Optional features → Add a feature), or, if Git is installed, run it by its full path:","Windows пишет, что ssh не распознан? Установите «Клиент OpenSSH» («Параметры» → «Приложения» → «Дополнительные компоненты» → «Добавить»), либо, если установлен Git, запустите по полному пути:"],c:"& \"C:\\Program Files\\Git\\usr\\bin\\ssh.exe\" root@192.168.8.1"},
    {t:["First time only: the program shows the router key and asks “Are you sure you want to continue connecting?”. Type yes and press Enter.","Только в первый раз: программа покажет ключ роутера и спросит «Are you sure you want to continue connecting?». Введите yes и нажмите Enter."]},
    {t:["Enter the router root password (the same as for the GL.iNet panel). The characters are not shown while you type; this is normal. When you see root@GL-MT6000:~# you are on the router.","Введите пароль root роутера (тот же, что в панели GL.iNet). Символы при вводе не отображаются, это нормально. Когда появится root@GL-MT6000:~#, вы на роутере."]},
    {t:["To leave, type:","Чтобы выйти, введите:"],c:"exit"},
    {t:["Prefer a window program? In PuTTY set Host Name 192.168.8.1, Port 22, Connection type SSH, then log in as root.","Удобнее программа с окном? В PuTTY укажите Host Name 192.168.8.1, Port 22, Connection type SSH и войдите как root."]}
   ]},
  {id:"reserve",
   title:["The router stays on the reserve VPN","Роутер остаётся на резервном VPN"],
   when:["The Overview says Auto is stopped but the router is still on the reserve, or the reserve is failing.","На «Обзоре» написано, что Auto остановлен, но роутер всё ещё на резерве, или что резерв не работает."],
   steps:[
    {t:["Check the primary VPN: GL.iNet panel → VPN → VPN Dashboard. It must be connected. If not, connect it.","Проверьте основной VPN: панель GL.iNet → VPN → VPN Dashboard. Он должен быть подключён. Если нет, подключите."]},
    {t:["On the Overview press “Return to primary”. If the answer is “the primary does not pass its check”, wait a minute and press again. The router only returns to a primary that works.","На «Обзоре» нажмите «Вернуться на основной». Если ответ «основной не проходит проверку», подождите минуту и нажмите снова. Роутер возвращается только на основной, который работает."]},
    {t:["Auto may also return by itself when the primary has been healthy for a while (return policy “Return to the primary once it has been healthy for a while”, Settings → Recovery rules).","Auto может вернуться и сам, когда основной некоторое время исправен (политика «Вернуться на основной, когда он некоторое время исправен», «Настройки» → «Правила восстановления»)."]},
    {t:["If the button is missing or does nothing, use the steps of “I have no internet”.","Если кнопки нет или она ничего не делает, выполните шаги раздела «У меня пропал интернет»."]}
   ]},
  {id:"auto-refuses",
   title:["The Auto button refuses to start","Кнопка Auto не запускается"],
   when:["Pressing Start shows a message with a code.","После нажатия «Старт» появляется сообщение с кодом."],
   steps:[
    {t:["Open the Overview and read “Before you can start Auto”. The first step that is not green is what to do next; every router condition has a plain explanation.","Откройте «Обзор» и прочитайте «Что нужно перед запуском Auto». Первый не зелёный шаг и есть то, что делать дальше; у каждого условия роутера есть понятное объяснение."]},
    {t:["Hardware acceleration must be off: GL.iNet panel → Network → Network Acceleration, switch it off. Flow offloading in the firewall must be off as well.","Аппаратное ускорение должно быть выключено: панель GL.iNet → «Сеть» → «Сетевое ускорение», выключите. Flow offloading в firewall тоже должен быть выключен."]},
    {t:["IPv6 must be off: GL.iNet panel → Network → IPv6, switch it off.","IPv6 должен быть выключен: панель GL.iNet → «Сеть» → IPv6, выключите."]},
    {t:["The primary and the reserve must be two general (all-traffic) VPN rules with Kill Switch on and the direct-internet fallback off: GL.iNet panel → VPN → VPN Dashboard.","Основной и резервный должны быть двумя общими VPN-правилами (для всего трафика) с включённым Kill Switch и выключенным прямым выходом в интернет: панель GL.iNet → VPN → VPN Dashboard."]},
    {t:["The last step is always the LAN trial. Run the LAN helper (see “The LAN helper fails”).","Последний шаг всегда LAN-тест. Запустите LAN-помощник (см. «LAN-помощник не работает»)."]}
   ]},
  {id:"helper-what",
   title:["What is the LAN helper and how do I start it","Что такое LAN-помощник и как его запустить"],
   when:["Auto asks for a passed LAN trial and you do not know what that is.","Auto требует пройденный LAN-тест, а вы не знаете, что это."],
   steps:[
    {t:["The LAN helper is a small script for Windows, written in PowerShell 7 (a plain text file, client-test.ps1, about 325 lines; you can open it in Notepad and read it). It runs on your computer, not on the router, and checks from the computer’s side that the internet really works through the router before and after a switch. It does not install anything and changes no network settings of the computer.","LAN-помощник — небольшой скрипт для Windows на PowerShell 7 (обычный текстовый файл client-test.ps1, около 325 строк; его можно открыть в Блокноте и прочитать). Он запускается на вашем компьютере, а не на роутере, и со стороны компьютера проверяет, что интернет действительно работает через роутер до и после переключения. Он ничего не устанавливает и не меняет сетевых настроек компьютера."]},
    {t:["Install PowerShell 7 once (Windows 10/11):","Один раз установите PowerShell 7 (Windows 10/11):"],c:"winget install Microsoft.PowerShell"},
    {t:["On the Overview press “Download LAN helper” and “Download launcher”. Put both files in one folder. The launcher only asks questions (router address, cable adapter, mode) and starts the helper.","На «Обзоре» нажмите «Скачать LAN-помощник» и «Скачать запуск». Положите оба файла в одну папку. Запуск лишь задаёт вопросы (адрес роутера, кабельный адаптер, режим) и запускает помощник."]},
    {t:["Open PowerShell 7 in that folder (in Explorer type pwsh in the address bar) and start the launcher:","Откройте PowerShell 7 в этой папке (в Проводнике введите pwsh в адресной строке) и запустите:"],c:"pwsh -NoProfile -File .\\start-lan-helper.ps1"},
    {t:["Choose mode 1 (check only) first: it only reads and changes nothing. If it passes, run it again with mode 3 (full trial): it asks for the router password (typed privately, never saved) and the word TEST, switches to the reserve for a few minutes, checks the internet from your computer and then confirms the result to the router. Use a LAN cable if you can.","Сначала выберите режим 1 (только проверка): он только читает и ничего не меняет. Если прошёл, запустите снова в режиме 3 (полный тест): он спросит пароль роутера (вводится скрыто, нигде не сохраняется) и слово TEST, на несколько минут переключится на резерв, проверит интернет с вашего компьютера и подтвердит результат роутеру. По возможности используйте кабель LAN."]},
    {t:["If it stops with a code in capital letters, open Help → “The LAN helper fails”.","Если он остановился с кодом заглавными буквами, откройте «Помощь» → «LAN-помощник не работает»."]}
   ]},
  {id:"helper",
   title:["The LAN helper fails","LAN-помощник не работает"],
   when:["client-test.ps1 stops with a code before or during the trial.","client-test.ps1 останавливается с кодом до теста или во время него."],
   steps:[
    {t:["POWERSHELL-7-REQUIRED: install PowerShell 7 and start it with pwsh:","POWERSHELL-7-REQUIRED: установите PowerShell 7 и запускайте через pwsh:"],c:"winget install Microsoft.PowerShell"},
    {t:["Run a read-only check first (it changes nothing). Replace 3 by the number of your cable adapter (Get-NetAdapter shows it):","Сначала запустите проверку только для чтения (ничего не меняет). Замените 3 на номер вашего кабельного адаптера (его показывает Get-NetAdapter):"],c:"pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly"},
    {t:["CLIENT-CABLE-ADDRESS-AMBIGUOUS or the cable has no address: plug the cable into a LAN port of the router and wait until the adapter has one 192.168.8.x address.","CLIENT-CABLE-ADDRESS-AMBIGUOUS или у кабеля нет адреса: вставьте кабель в LAN-порт роутера и дождитесь, пока у адаптера появится один адрес 192.168.8.x."]},
    {t:["CLIENT-CABLE-HTTPS-FAILED or Windows error 10051 on the cable: allow default routes on that adapter (use your adapter number):","CLIENT-CABLE-HTTPS-FAILED или ошибка Windows 10051 на кабеле: разрешите маршруты по умолчанию на этом адаптере (подставьте номер адаптера):"],c:"Set-NetIPInterface -InterfaceIndex 3 -AddressFamily IPv4 -IgnoreDefaultRoutes Disabled"},
    {t:["DNS fails while a VPN program is running on the computer (for example NordVPN DNS protection): stop that program for the minutes of the test and start it again afterwards.","DNS не отвечает, пока на компьютере работает программа VPN (например, защита DNS в NordVPN): остановите её на время теста и потом запустите снова."]},
    {t:["CLIENT-PROBE-ROUTE-CONFLICT: a previous run left temporary routes. List them and remove the ones for 1.1.1.1 and 1.0.0.1 on the cable adapter:","CLIENT-PROBE-ROUTE-CONFLICT: прошлый запуск оставил временные маршруты. Посмотрите их и удалите маршруты для 1.1.1.1 и 1.0.0.1 на кабельном адаптере:"],c:"Get-NetRoute -DestinationPrefix 1.1.1.1/32,1.0.0.1/32"},
    {t:["The helper asks for the router password and for the word TEST. A short interruption of calls and downloads is possible during the switch.","Помощник спрашивает пароль роутера и слово TEST. Во время переключения возможен короткий разрыв звонков и загрузок."]}
   ]},
  {id:"stale",
   title:["The page is old, empty or says the monitor is not running","Страница старая, пустая или пишет, что мониторинг не работает"],
   when:["After an update, the Overview looks old, shows errors, or the status is stale.","После обновления «Обзор» выглядит по-старому, показывает ошибки или статус устарел."],
   steps:[
    {t:["Press Ctrl+F5 to reload without cache, then sign out of LuCI and sign in again (new permissions after an update).","Нажмите Ctrl+F5 (обновление без кэша), затем выйдите из LuCI и войдите снова (после обновления права обновляются)."]},
    {t:["Overview → the Monitoring block → “Start monitoring” (shown only when monitoring is not running). Or from SSH:","«Обзор» → блок «Мониторинг» → «Запустить мониторинг» (показан только когда мониторинг не работает). Или через SSH:"],c:"homensai-vpn-emergency start"},
    {t:["If the page still says the status is unavailable, reload the router’s RPC service and sign in again:","Если страница всё ещё пишет, что статус недоступен, перезапустите RPC-службу роутера и войдите снова:"],c:"/etc/init.d/rpcd reload"},
    {t:["Check that exactly one monitor is running:","Проверьте, что запущен ровно один монитор:"],c:"ps w | grep homensai-vpn"}
   ]},
  {id:"outside-change",
   title:["I changed VPN rules in the GL.iNet panel and Auto stopped","Я изменил правила VPN в панели GL.iNet, и Auto остановился"],
   when:["The Overview says the VPN rules were changed by someone else.","На «Обзоре» написано, что правила VPN изменил кто-то другой."],
   steps:[
    {t:["This is intended: Auto never fights your changes. It stopped and removed its own traffic block; your internet is not held.","Так задумано: Auto не спорит с вашими изменениями. Он остановился и снял свою блокировку трафика; интернет не удерживается."]},
    {t:["Check GL.iNet panel → VPN → VPN Dashboard: the primary should be first, the reserve second, all with Kill Switch.","Проверьте панель GL.iNet → VPN → VPN Dashboard: основной должен быть первым, резервный вторым, у всех включён Kill Switch."]},
    {t:["To use Auto again, run a new LAN trial (the earlier test belongs to the old rules).","Чтобы снова использовать Auto, пройдите новый LAN-тест (прежний тест относится к старым правилам)."]}
   ]},
  {id:"telegram",
   title:["Telegram reports do not arrive","Отчёты в Telegram не приходят"],
   when:["The Overview shows a Telegram error, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.","На «Обзоре» ошибка Telegram, тестовое сообщение не приходит или вы настраиваете Telegram впервые. Нужны три вещи: бот, его токен и ID чата."],
   steps:[
    {t:["Create the bot. In Telegram open https://t.me/BotFather (or search for @BotFather; the real one has a blue check mark). Send: /newbot","Создайте бота. В Telegram откройте https://t.me/BotFather (или найдите @BotFather; у настоящего есть синяя галочка). Отправьте: /newbot"],c:"/newbot"},
    {t:["BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).","BotFather спросит имя (показывается в чате, любой текст, например «Мой VPN роутер») и затем username, который должен заканчиваться на «bot» (например my_router_vpn_bot)."]},
    {t:["BotFather answers with “Use this token to access the HTTP API:” and a line like 123456789:AAH-secret-part-of-the-token. This line is the bot token (digits, a colon, then 30–100 letters, digits, - or _). Copy it. It is a secret: do not post it anywhere.","BotFather ответит «Use this token to access the HTTP API:» и строкой вида 123456789:AAH-secret-part-of-the-token. Эта строка и есть токен бота: цифры, двоеточие, затем 30–100 букв, цифр, - или _. Скопируйте её. Это секрет: не публикуйте его."]},
    {t:["Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.","Откройте нового бота (ссылка в конце сообщения BotFather, https://t.me/<username_вашего_бота>) и нажмите Start или отправьте /start. Бот не может написать вам первым."]},
    {t:["Find your Chat ID. For reports to yourself: open https://t.me/userinfobot (@userinfobot), press Start and copy the number after “Id:”, e.g. 123456789. For a group: add your bot to the group, add @userinfobot or @getidsbot as well, and take the number that starts with a minus, e.g. -1001234567890. For a public channel: add your bot as an administrator and use the channel name with @, e.g. @my_channel.","Узнайте ID чата. Для отчётов себе: откройте https://t.me/userinfobot (@userinfobot), нажмите Start и скопируйте число после «Id:», например 123456789. Для группы: добавьте бота в группу, добавьте также @userinfobot или @getidsbot и возьмите число с минусом, например -1001234567890. Для публичного канала: добавьте бота администратором и укажите имя канала с @, например @my_channel."]},
    {t:["On the router page: Settings → Setup → 2 · Telegram. Paste the token into “Bot token” and the number or @name into “Chat ID”, choose how often to send, review and save. After saving the token is never shown again; to change it, enter it again; to remove it, use the delete button.","На странице роутера: «Настройки» → «Настройка» → 2 · Telegram. Вставьте токен в «Токен бота», число или @имя в «ID чата», выберите частоту отправки, проверьте обзор и сохраните. После сохранения токен больше не показывается; чтобы изменить — введите заново; чтобы убрать — кнопка удаления."]},
    {t:["Press “Test Telegram delivery”. A message should arrive within a few seconds. If a code is shown instead: TELEGRAM-… with “401” or “Unauthorized” means a wrong token; “400”, “chat not found” or “Forbidden” means a wrong Chat ID or you never pressed Start; a timeout means the router has no internet or a wrong clock.","Нажмите «Проверить доставку Telegram». Сообщение должно прийти за несколько секунд. Если показан код TELEGRAM-…: «401» или «Unauthorized» — неверный токен; «400», «chat not found» или «Forbidden» — неверный ID чата или вы не нажали Start; тайм-аут — у роутера нет интернета или неверные часы."]},
    {t:["Still nothing? Create the token again in BotFather (/token or /revoke) and enter the new one. Never send the token to anyone, including in a support chat.","Всё равно нет? Создайте токен заново в BotFather (/token или /revoke) и введите новый. Никому не отправляйте токен, в том числе в чат поддержки."]}
   ]},
  {id:"clock",
   title:["Dates are wrong, history or statistics are blocked","Неверные даты, история или статистика заблокированы"],
   when:["Codes like CLOCK-001 or HISTORY-001, or events with impossible dates.","Коды вроде CLOCK-001 или HISTORY-001, либо события с невозможными датами."],
   steps:[
    {t:["The router clock must be correct. GL.iNet panel → System → Time: enable time synchronisation (NTP) and pick your time zone.","Часы роутера должны быть верными. Панель GL.iNet → «Система» → «Время»: включите синхронизацию времени (NTP) и выберите часовой пояс."]},
    {t:["Check the clock over SSH:","Проверьте часы по SSH:"],c:"date"},
    {t:["After the clock is right, statistics continue by themselves. Gaps are shown as unobserved time and are never filled with invented numbers.","После исправления часов статистика продолжится сама. Пропуски показываются как ненаблюдаемое время и никогда не заполняются выдуманными числами."]}
   ]},
  {id:"backup",
   title:["Make a backup before changes","Резервная копия перед изменениями"],
   when:["Before an update, a LAN trial or any manual repair.","Перед обновлением, LAN-тестом или любым ручным исправлением."],
   steps:[
    {t:["On Windows run this in PowerShell (cmd /c keeps the file binary). The file contains secrets, so keep it private and never upload it:","В Windows выполните в PowerShell (cmd /c сохраняет файл без искажений). В файле есть секреты: храните его приватно и никуда не загружайте:"],c:"cmd /c \"ssh root@192.168.8.1 \"\"tar czf - /etc/config /etc/homensai-vpn\"\" > router-backup.tgz\""},
    {t:["On Linux or macOS:","В Linux или macOS:"],c:"ssh root@192.168.8.1 'tar czf - /etc/config /etc/homensai-vpn' > router-backup.tgz"}
   ]},
  {id:"remove",
   title:["Remove or roll back the program","Удалить программу или откатить версию"],
   when:["You want the router without this program, or you need an older version.","Нужен роутер без этой программы или более старая версия."],
   steps:[
    {t:["Stop Auto first and make sure the router is back on the primary (Overview). Then, by SSH:","Сначала остановите Auto и убедитесь, что роутер вернулся на основной («Обзор»). Затем по SSH:"],c:"opkg remove homensai-auto-vpn"},
    {t:["Your settings and history stay in `/etc/config/homensai_vpn` and `/etc/homensai-vpn`. Installing again keeps them.","Ваши настройки и история остаются в `/etc/config/homensai_vpn` и `/etc/homensai-vpn`. При повторной установке они сохраняются."]},
    {t:["If the removal is refused, the program tells why (for example a transaction is active). Do not force it: first use “I have no internet”.","Если удаление отклонено, программа объяснит причину (например, активна транзакция). Не форсируйте: сначала выполните раздел «У меня пропал интернет»."]}
   ]},
  {id:"report",
   title:["What to send when asking for help","Что отправить, когда просите о помощи"],
   when:["You report a problem and want it solved quickly.","Вы сообщаете о проблеме и хотите решить её быстро."],
   steps:[
    {t:["These commands print no passwords or keys. Send their output and the time of the problem:","Эти команды не печатают паролей и ключей. Отправьте их вывод и время проблемы:"],c:"homensai-vpn-emergency show"},
    {t:["Installed version:","Установленная версия:"],c:"opkg status homensai-auto-vpn | grep Version"},
    {t:["Latest system log lines about the program:","Последние строки системного журнала о программе:"],c:"logread | grep -i homensai | tail -30"},
    {t:["Never send the router password, the Telegram token, VPN files or backups.","Никогда не отправляйте пароль роутера, токен Telegram, файлы VPN и резервные копии."]}
   ]}
];

// Text with `inline code` pieces: the same dark monospace style everywhere.
function richText(text){return String(text).split('`').map(function(part,i){return i%2?E('code',{'class':'hv-code'},part):part;});}
function helpCommand(command){
  var button=E('button',{'type':'button','class':'cbi-button','click':function(){
    try{navigator.clipboard.writeText(command).then(function(){button.textContent=bi('Copied','Скопировано');}).catch(function(){});}catch(error){}
  }},bi('Copy','Копировать'));
  return E('div',{'class':'hv-cmd-row'},[E('pre',{'class':'hv-cmd'},command),button]);
}
function renderHelp(){
  var topics=HELP_TOPICS.map(function(topic){
    var steps=topic.custom?topic.custom():E('ol',{'class':'hv-help-steps'},topic.steps.map(function(step){
      return E('li',{},[E('p',{},richText(bi(step.t[0],step.t[1]))),step.c?helpCommand(step.c):null].filter(Boolean));
    }));
    var attributes={'class':'hv-help-topic','id':'help-'+topic.id};
    if(topic.open)attributes.open='open';
    return E('details',attributes,[E('summary',{},bi(topic.title[0],topic.title[1])),E('p',{'class':'hv-help-when'},bi(topic.when[0],topic.when[1])),steps]);
  });
  return E('section',{'class':'hv-chart-card hv-help'},[
    E('h2',{},bi('Help and recovery','Помощь и восстановление')),
    E('p',{},bi('Pick the situation that matches. Commands are typed on the router over SSH (see “How to connect by SSH”); the Copy button copies a command so you can paste it.','Выберите подходящую ситуацию. Команды вводятся на роутере по SSH (см. «Как подключиться по SSH»); кнопка «Копировать» копирует команду, чтобы вставить её в терминал.'))
  ].concat(topics));
}

var helpNode=null,learnNode=null;
// The terms can be re-read at any time (same points as the first-run screen).
if(typeof TERMS_POINTS!=='undefined'){HELP_TOPICS.push({id:'terms',title:["Terms of use (experimental software)","Условия использования (экспериментальное ПО)"],when:["What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.","Что вы приняли на первом экране. Полный текст — DISCLAIMER.ru.md в репозитории проекта."],steps:TERMS_POINTS.map(function(point){return {t:[point.h[0]+'. '+point.t[0],point.h[1]+'. '+point.t[1]]};})});}

/* First-run terms. The same points are in DISCLAIMER.md / DISCLAIMER.ru.md. Acceptance is stored on the router
   (terms_version, terms_time); the controller refuses to switch and Auto refuses to start until it is stored. */
var TERMS_VERSION='1';
var TERMS_POINTS=[
  {h:["It is experimental","Это экспериментальная версия"],t:["This is an early alpha release. It has been tested only in a limited way, on a GL.iNet GL-MT6000 (firmware 4.11.0) and in a virtual OpenWrt. It is not production software.","Это ранняя версия alpha. Она проверялась лишь ограниченно, на GL.iNet GL-MT6000 (прошивка 4.11.0) и в виртуальном OpenWrt. Это не промышленное ПО."]},
  {h:["It can interrupt your internet","Оно может прервать ваш интернет"],t:["Switching a VPN route can drop calls, downloads and sessions. A fault or bug can leave devices on your network without internet until you repair the router by hand. Keep another way to reach the internet and the router, and make a backup first.","Переключение маршрута VPN может оборвать звонки, загрузки и сессии. Сбой или ошибка могут оставить устройства без интернета, пока вы не исправите роутер вручную. Держите другой способ выхода в интернет и доступа к роутеру и сначала сделайте резервную копию."]},
  {h:["It changes router settings","Оно меняет настройки роутера"],t:["It reorders your existing VPN rules and can add a temporary firewall rule. It does not edit your VPN keys. You can remove it at any time (see Help).","Оно переставляет ваши существующие правила VPN и может добавить временное правило firewall. Ключи VPN оно не редактирует. Удалить его можно в любой момент (см. «Помощь»)."]},
  {h:["No warranty","Гарантий нет"],t:["Provided “AS IS” under the MIT License, without warranty of any kind. The author and contributors are not liable for any damage, loss of data, loss of service, cost or other consequence of installing or using it.","Предоставляется «КАК ЕСТЬ» (AS IS) по лицензии MIT, без каких-либо гарантий. Автор и участники не отвечают за ущерб, потерю данных, потерю связи, расходы и иные последствия установки или использования."]},
  {h:["You are responsible","Ответственность на вас"],t:["You use it at your own risk. You are responsible for your router, your network, your VPN accounts, your VPN provider’s terms and the law that applies to you. Do not use it where an interruption could endanger people or property.","Вы используете его на свой риск. Вы отвечаете за свой роутер, сеть, аккаунты VPN, условия провайдера VPN и применимое к вам законодательство. Не используйте его там, где перерыв связи может угрожать людям или имуществу."]},
  {h:["Optional reports","Необязательные отчёты"],t:["If you set up Telegram reports, summaries are sent through Telegram’s servers with a bot token stored on your router. Nothing is sent unless you set it up.","Если вы настроите отчёты в Telegram, сводки отправляются через серверы Telegram с токеном бота, хранящимся на вашем роутере. Без вашей настройки ничего не отправляется."]},
  {h:["No promise of support","Поддержка не обещана"],t:["Features, behaviour and these terms may change in later versions; you may be asked to accept them again.","Возможности, поведение и эти условия могут измениться в следующих версиях; вас могут попросить принять их снова."]}
];
var TERMS_CHECKS=[
  ["I understand that this software is experimental and may interrupt my internet connection.","Я понимаю, что это ПО экспериментальное и может прервать моё подключение к интернету."],
  ["I have read the terms above and accept full responsibility for installing and using it.","Я прочитал условия выше и принимаю полную ответственность за установку и использование."]
];
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
    E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui47.css')}),
    E('section',{'class':'hv-chart-card hv-terms-card'},[
      E('header',{'class':'hv-page-header','style':'flex-wrap:wrap;gap:12px'},[E('p',{'class':'hv-eyebrow'},bi('HomenS.AI Auto VPN · first start','HomenS.AI Auto VPN · первый запуск')),versionBadge]),
      E('h1',{},bi('Experimental software: please read','Экспериментальное ПО: прочитайте, пожалуйста')),
      E('p',{},[bi('Language: ','Язык: '),language]),
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
  HV_DETECTED_ROUTER_MODEL=s.detected_router_model||'unknown';
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
    appearance:{language:s.appearance_language||locale,theme:s.appearance_theme||storedTheme(),design:s.appearance_design||currentDesign(),router_model:s.router_model||'auto'},
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
  return [system,monitor,recovery,speed,telegram,{language:draft.appearance.language,theme:draft.appearance.theme,design:draft.appearance.design,router_model:draft.appearance.router_model}];
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
        select(bi('Router model','Модель роутера'),draft.appearance,'router_model','appearance.router_model',[['auto',bi('Automatic detection (recommended)','Автоопределение (рекомендуется)')],['mt6000','GL-MT6000 · Flint 2'],['mt3000','GL-MT3000 · Beryl AX']]);
        var detected=settings.detected_router_model||'unknown',modelLabels={mt6000:'GL-MT6000 · Flint 2',mt3000:'GL-MT3000 · Beryl AX'};
        card.appendChild(E('p',{'data-onboarding-device':'detected'},bi('Detected router: ','Обнаружен роутер: ')+(modelLabels[detected]||bi('Unknown','Не определён'))));
        var modelError=E('p',{'role':'alert','data-onboarding-device':'error'});card.appendChild(modelError);
        checks.push(function(){var ok=draft.appearance.router_model==='auto'||draft.appearance.router_model===detected;modelError.textContent=ok?'':bi('The selected model does not match this router. Choose automatic detection or the detected model.','Выбранная модель не соответствует роутеру. Выберите автоопределение или обнаруженную модель.');return ok;});
        note('The model choice is checked against the router hardware. It does not enable Auto or change network settings. MT3000 currently supports monitoring; channel switching is not yet supported.','Модель сверяется с оборудованием роутера. Выбор не включает Auto и не меняет сеть. Сейчас MT3000 поддерживает мониторинг; переключение каналов ещё не поддерживается.');
        note('These defaults are saved on the router. The language, theme and design controls in Settings can override them in one browser. Your current appearance changes only after the final save.','Эти значения сохраняются на роутере. Отдельные переключатели языка, темы и оформления в настройках могут переопределить их в одном браузере. Текущее оформление изменится только после общего сохранения.');
        select(bi('Default language','Язык по умолчанию'),draft.appearance,'language','appearance.language',[['en','English'],['ru','Русский']]);
        select(bi('Default theme','Тема по умолчанию'),draft.appearance,'theme','appearance.theme',[['system',bi('Follow system','Как в системе')],['light',bi('Light','Светлая')],['dark',bi('Dark','Тёмная')]]);
        select(bi('Default design','Оформление по умолчанию'),draft.appearance,'design','appearance.design',HV_DESIGNS.map(function(d){return [d.key,bi(d.name[0],d.name[1])];}));
        note('Reporting timezone: Europe/Berlin. Router WAN, Wi-Fi and VPN keys are edited on the router VPN/network pages.','Часовой пояс отчётов: Europe/Berlin. WAN, Wi-Fi и ключи VPN изменяются на страницах сети и VPN роутера.');
      }else if(session.step===1){
        note('Monitoring service on/off remains a separate action. These preferences do not start Auto, a speed test or an inactive VPN. Checkpoints write statistics to flash.','Включение службы мониторинга остаётся отдельным действием. Эти параметры не запускают Auto, тест скорости или неактивный VPN. Checkpoint записывает статистику во flash.');
        number(bi('How often to check each VPN, seconds','Как часто проверять каждый VPN, секунд'),draft.monitor,'interval','monitor.interval','monitor.interval');
        number(bi('Save statistics every, seconds','Сохранять статистику каждые, секунд'),draft.monitor,'checkpoint','monitor.checkpoint','monitor.checkpoint');
        number(bi('Most VPNs checked per round','Максимум VPN за один раунд проверки'),draft.monitor,'probe_limit','monitor.probe_limit','onboarding.probe_limit');
        toggle(bi('Show the failover forecast on the Overview','Показывать прогноз переключения на странице «Обзор»'),draft.monitor,'planning_enabled','monitor.planning_enabled');
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
        review(headings[0],[[bi('Router model / detected','Модель роутера / обнаружено'),draft.appearance.router_model+' / '+(settings.detected_router_model||bi('Unknown','Не определён'))],[bi('Language / theme / design','Язык / тема / оформление'),draft.appearance.language+' / '+draft.appearance.theme+' / '+draft.appearance.design],[bi('Reporting timezone','Часовой пояс отчётов'),'Europe/Berlin']]);
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
  if(firstRun){['style/css/tokens.css','style/css/fonts.css','style/css/author.css','ui47.css'].forEach(function(path){host.appendChild(E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/'+path)}));});}
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

/* Installed identity and part-mismatch diagnosis. The router program and this page are shipped together; they can differ after
   an interrupted upgrade or a cached page. Build values are written by the page generator. */
var UI_BUILD='dashboard70',UI_AGENT='0.9.0-alpha40';
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
  return bi('Version ','Версия ')+(model.agent||model.uiAgent)+' · '+bi('package ','пакет ')+(model.pkg||'—')+' · '+bi('page ','страница ')+model.ui;
}

/* Interactive training: lesson cards, then a quiz with checkboxes, a score and "take again". Data are [English, Russian] pairs. */
var LEARN_LESSONS=[
  {icon:'①',title:['What this system is','Что это за система'],
   body:[['HomenS.AI Auto VPN is a page on your GL.iNet router. It watches the VPN connections you already created in GL.iNet and shows which of them give internet right now.','HomenS.AI Auto VPN — страница на вашем роутере GL.iNet. Она следит за VPN-подключениями, которые вы уже создали в GL.iNet, и показывает, какие из них сейчас дают интернет.'],['If you switch Auto on, it can also move your traffic from the main VPN to a reserve VPN when the main one fails, and back when it recovers.','Если включить Auto, она ещё может переводить трафик с основного VPN на резервный, когда основной отказывает, и возвращать обратно, когда он восстановился.']],
   example:['Example: your main VPN is Germany · WireGuard, the reserve is Netherlands · OpenVPN. Germany stops working at night; Auto moves you to the Netherlands, and back in the morning.','Пример: основной VPN — Германия · WireGuard, резерв — Нидерланды · OpenVPN. Ночью Германия перестала работать; Auto переводит вас на Нидерланды, а утром возвращает.'],
   tip:['It does not create VPN profiles and does not connect VPNs you did not connect.','Она не создаёт VPN-профили и не подключает VPN, которые вы не подключали.']},
  {icon:'②',title:['Before you start: two ways to connect','Перед началом: два способа подключения'],
   body:[['Prepare two ways to reach the router: a laptop connected by a LAN cable, and a device on Wi-Fi (a phone or the same laptop). Keep both during the first tests.','Подготовьте два способа попасть на роутер: ноутбук, подключённый кабелем LAN, и устройство по Wi-Fi (телефон или тот же ноутбук). Держите оба на время первых тестов.'],['The cable is the reliable path for tests: it does not depend on Wi-Fi. Wi-Fi shows what your family devices will really experience. If the internet disappears, you can still open the router from the other path.','Кабель — надёжный путь для тестов: он не зависит от Wi-Fi. Wi-Fi показывает, что реально увидят устройства домашних. Если интернет пропадёт, вы всё равно сможете открыть роутер другим путём.'],['Also keep mobile data on your phone: it works even when the router VPN is broken.','Также держите мобильный интернет на телефоне: он работает, даже если VPN роутера сломан.']],
   example:['Example: laptop on the cable runs the check; the phone on Wi-Fi opens a site to confirm that Wi-Fi users have internet too.','Пример: ноутбук на кабеле запускает проверку; телефон по Wi-Fi открывает сайт, чтобы подтвердить, что интернет есть и у пользователей Wi-Fi.'],
   tip:['Never test only from one device that you cannot afford to lose.','Не тестируйте только с одного устройства, которое нельзя потерять.']},
  {icon:'③',title:['First start','Первый запуск'],
   body:[['Open Services → HomenS.AI Auto VPN. On the first screen read the terms and tick both boxes: this is experimental software that you use at your own risk.','Откройте «Службы» → HomenS.AI Auto VPN. На первом экране прочитайте условия и отметьте оба флажка: это экспериментальное ПО, вы используете его на свой риск.'],['Monitoring starts by itself. On the Overview the Monitoring block shows a green lamp when fresh data arrives (up to a minute). Auto stays off.','Мониторинг запускается сам. На «Обзоре» блок «Мониторинг» покажет зелёную лампу, когда придут свежие данные (до минуты). Auto остаётся выключенным.']],
   example:['Example: after pressing Start the light is yellow “Starting”, then green “Monitor is running”.','Пример: после «Старт» светофор жёлтый «Запускается», затем зелёный «Мониторинг работает».'],
   tip:['Grey means switched off, red means switched on but not working: open Help.','Серый — выключен, красный — включён, но не работает: откройте «Помощь».']},
  {icon:'④',title:['Setup','Настройка'],
   body:[['Settings → Setup → 1 · System: choose the primary and the reserve profile. Choose a different country or provider for the reserve.','«Настройки» → «Настройка» → 1 · Система: выберите основной и резервный профили. Для резерва берите другую страну или другого провайдера.'],['2 · Telegram is optional: create a bot with @BotFather, press Start in it, enter the token and your Chat ID, then press “Test Telegram delivery”. Under each step open “What is this and how to fill it in” for examples.','2 · Telegram — по желанию: создайте бота через @BotFather, нажмите в нём Start, введите токен и свой ID чата и нажмите «Проверить доставку Telegram». Под каждым шагом откройте «Что это и как заполнить» — там примеры.'],['Rules for switching and check intervals are in “Advanced settings”. The defaults are safe.','Правила переключения и интервалы проверок — в «Расширенных настройках». Значения по умолчанию безопасны.']],
   example:['Example: primary 1 = Germany · WireGuard, reserve 2 = Netherlands · OpenVPN.','Пример: основной 1 = Германия · WireGuard, резерв 2 = Нидерланды · OpenVPN.'],
   tip:['The bot token is a secret. Never post it or send it to anyone.','Токен бота — секрет. Никому не публикуйте и не отправляйте его.']},
  {icon:'⑤',title:['Step 1: check the VPNs, Step 2: turn on Auto','Шаг 1: проверить VPN, шаг 2: включить Auto'],
   body:[['On Overview press “Step 1 · Check the VPNs now”. It tests right away which connected VPNs give internet. Fix problems first.','На «Обзоре» нажмите «Шаг 1 · Проверить VPN сейчас». Сразу проверит, какие подключённые VPN дают интернет. Сначала устраните проблемы.'],['Step 2: Auto can be started only after a passed LAN trial. Download the LAN helper and run it on a Windows computer in your network, preferably on the cable. The page lists exactly which step is missing. Then press the Auto button.','Шаг 2: Auto можно запустить только после успешного LAN-теста. Скачайте LAN-помощник и запустите его на компьютере с Windows в вашей сети, лучше по кабелю. Страница показывает, какого шага не хватает. Затем нажмите кнопку Auto.'],['What is the LAN helper? A small PowerShell 7 script (plain text, you can read it) that runs on your Windows computer, not on the router. Install PowerShell 7 once, put the two downloaded files in one folder and start the launcher, then choose mode 1 (check only) first:','Что такое LAN-помощник? Небольшой скрипт PowerShell 7 (обычный текст, его можно прочитать), который запускается на вашем компьютере с Windows, а не на роутере. Один раз установите PowerShell 7, положите два скачанных файла в одну папку и запустите, сначала выберите режим 1 (только проверка):'],['The Auto light: green — watching the primary; yellow — switching; orange — working on the reserve; red — needs your attention; grey — off.','Светофор Auto: зелёный — следит за основным; жёлтый — переключается; оранжевый — работает на резерве; красный — нужно ваше внимание; серый — выключен.']],
   cmds:[['winget install Microsoft.PowerShell',['Once: installs PowerShell 7 (Windows 10/11).','Один раз: устанавливает PowerShell 7 (Windows 10/11).']],['pwsh -NoProfile -File .\\start-lan-helper.ps1',['In the folder with the two downloaded files: starts the launcher.','В папке с двумя скачанными файлами: запускает программу запуска.']]],
   example:['Example: green Auto light and “2 of 2 VPNs work” means everything is fine.','Пример: зелёный светофор Auto и «работают 2 из 2 VPN» — всё в порядке.'],
   tip:['Do not turn Auto on when you cannot afford a short interruption (a call, a download).','Не включайте Auto, когда нельзя терпеть короткий перерыв (звонок, загрузка).']},
  {icon:'⑥',title:['Reading the pages','Как читать страницы'],
   body:[['Overview: the Auto control and the state of your VPNs. Channels and servers: every VPN profile with its country and protocol (OpenVPN or WireGuard); the list comes from your router and changes when you add or remove profiles there.','«Обзор»: управление Auto и состояние ваших VPN. «Каналы и серверы»: каждый VPN-профиль со страной и протоколом (OpenVPN или WireGuard); список берётся с роутера и меняется, когда вы добавляете или удаляете профили.'],['Statistics shows how the VPNs behaved over time. “Advanced” (for administrators) holds the tests, rankings, traffic, service log, events and readiness.','«Статистика» показывает, как вели себя VPN со временем. «Расширенное» (для администраторов) содержит тесты, рейтинги, трафик, журнал службы, события и готовность.']],
   example:['Example: a server with only 3 checks is not a leader yet: the ranking needs at least 20 checks.','Пример: сервер всего с 3 проверками ещё не лидер: рейтингу нужно не меньше 20 проверок.'],
   tip:['Speed tests are optional and use traffic; they live under Advanced → Tests.','Тесты скорости необязательны и расходуют трафик; они в «Расширенное» → «Тесты».']},
  {icon:'⑦',title:['If the internet is gone','Если пропал интернет'],
   body:[['First stay calm: use mobile data on your phone to read Help. Open the router page by the cable or Wi-Fi and look at Overview.','Сначала спокойно: откройте «Помощь» на телефоне через мобильный интернет. Откройте страницу роутера по кабелю или Wi-Fi и посмотрите «Обзор».'],['If the router is on the reserve, press “Return to primary”. Still no internet? Connect to the router by SSH and run the helper commands below.','Если роутер на резерве, нажмите «Вернуться на основной». Интернета всё нет? Подключитесь к роутеру по SSH и выполните команды помощника ниже.'],['Then check GL.iNet → VPN → VPN Dashboard: the primary first, tunnels connected. Help → “I have no internet” has every step.','Затем проверьте GL.iNet → VPN → VPN Dashboard: основной первым, туннели подключены. В «Помощи» → «У меня пропал интернет» — все шаги.']],
   cmds:[['homensai-vpn-emergency show',['Only reads the state. Always safe.','Только читает состояние. Всегда безопасно.']],['homensai-vpn-emergency stop-auto',['Stops the program’s own services. Network settings are not changed.','Останавливает собственные службы программы. Сетевые настройки не меняются.']],['homensai-vpn-emergency remove-guard',['Removes only the program’s own traffic block.','Снимает только собственную блокировку трафика программы.']]],
   example:['Example: the page says “on reserve” and the internet is slow: press “Return to primary”; the router checks the primary first.','Пример: страница пишет «на резерве», интернет медленный: нажмите «Вернуться на основной»; роутер сначала проверит основной.'],
   tip:['Reading with `show` is always safe; run the other commands only when you need to.','Чтение командой `show` всегда безопасно; остальные команды запускайте, только когда нужно.']},
  {icon:'⑧',title:['Safety rules','Правила безопасности'],
   body:[['This is experimental software: it can interrupt your internet. You use it at your own risk and keep another way to reach the router.','Это экспериментальное ПО: оно может прервать интернет. Вы используете его на свой риск и сохраняете другой способ попасть на роутер.'],['Never share the router password, the Telegram token, VPN files or backups with anyone, including chats and support. After tests, change the router password if you typed it anywhere.','Никому не передавайте пароль роутера, токен Telegram, VPN-файлы и резервные копии, в том числе в чатах и поддержке. После тестов смените пароль роутера, если вводили его где-либо.'],['When unsure: leave Auto off. The monitor alone is read-only and safe.','Когда не уверены — оставьте Auto выключенным. Один только мониторинг только читает и безопасен.']],
   example:['Example: a person asks in a chat for your token “to help”. Do not send it.','Пример: в чате просят ваш токен «чтобы помочь». Не отправляйте.'],
   tip:['You can come back to this training at any time from the menu.','К этому обучению можно вернуться в любой момент из меню.']}
];
var LEARN_QUIZ=[
  {q:['What does the system do when Auto is OFF?','Что делает система при выключенном Auto?'],o:[['Only watches and shows the state of your VPNs','Только наблюдает и показывает состояние ваших VPN',true],['Switches to the reserve VPN by itself','Сама переключается на резервный VPN',false],['Creates new VPN profiles','Создаёт новые VPN-профили',false]]},
  {q:['Which ways to connect should you prepare for the first tests? (several answers)','Какие способы подключения нужно подготовить для первых тестов? (несколько ответов)'],o:[['A laptop on a LAN cable','Ноутбук на кабеле LAN',true],['A device on Wi-Fi','Устройство по Wi-Fi',true],['Only one device that you cannot lose','Только одно устройство, которое нельзя потерять',false],['Mobile data on the phone','Мобильный интернет на телефоне',true]]},
  {q:['What is the right order to start working?','Каков правильный порядок начала работы?'],o:[['Accept the terms, start the monitor, check the VPNs, then turn on Auto','Принять условия, запустить мониторинг, проверить VPN, затем включить Auto',true],['Turn on Auto first, check later','Сначала включить Auto, проверить потом',false],['Skip the terms and start Auto','Пропустить условия и сразу запустить Auto',false]]},
  {q:['What must pass before Auto can be started?','Что должно пройти перед запуском Auto?'],o:[['The LAN trial with the helper on a computer in your network','LAN-тест с помощником на компьютере в вашей сети',true],['A speed test','Тест скорости',false],['A Telegram message','Сообщение в Telegram',false]]},
  {q:['The Auto light is orange. What does it mean?','Светофор Auto оранжевый. Что это значит?'],o:[['Traffic works on the reserve','Трафик идёт через резерв',true],['Everything is on the primary','Всё идёт через основной',false],['Auto is off','Auto выключен',false]]},
  {q:['Which of these is a secret that you never send to anyone? (several answers)','Что из этого — секрет, который никому нельзя отправлять? (несколько ответов)'],o:[['The Telegram bot token','Токен Telegram-бота',true],['The router password','Пароль роутера',true],['The country of a VPN server','Страна VPN-сервера',false]]},
  {q:['The internet is gone. What do you do first?','Интернета нет. Что делаете сначала?'],o:[['Open the router page by cable or Wi-Fi and press “Return to primary” if it is on the reserve','Открываете страницу роутера по кабелю или Wi-Fi и нажимаете «Вернуться на основной», если он на резерве',true],['Flash the router firmware','Прошиваете роутер',false],['Delete all VPN profiles','Удаляете все VPN-профили',false]]},
  {q:['Which command only reads the state and is always safe?','Какая команда только читает состояние и всегда безопасна?'],o:[['homensai-vpn-emergency show','homensai-vpn-emergency show',true],['homensai-vpn-emergency stop-auto','homensai-vpn-emergency stop-auto',false],['homensai-vpn-emergency remove-guard','homensai-vpn-emergency remove-guard',false]]}
];
// A question is correct only when the chosen set equals the set of right options.
function learnGrade(question,chosen){
  var ok=true;
  var marks=question.o.map(function(option,index){
    var picked=chosen.indexOf(index)>=0,right=option[2]===true;
    if(picked!==right)ok=false;
    return picked&&right?'right':picked&&!right?'wrong':!picked&&right?'missed':'none';
  });
  return {ok:ok&&chosen.length>0,marks:marks};
}
function learnScore(quiz,answers){
  var correct=0;
  quiz.forEach(function(question,index){if(learnGrade(question,answers[index]||[]).ok)correct++;});
  return {correct:correct,total:quiz.length,percent:quiz.length?Math.round(correct*100/quiz.length):0};
}
function learnVerdict(percent){
  if(percent>=80)return bi('Well done. You know enough to use the system.','Отлично. Вы знаете достаточно, чтобы пользоваться системой.');
  if(percent>=50)return bi('Almost there. Read the cards again before you turn on Auto.','Почти. Перечитайте карточки, прежде чем включать Auto.');
  return bi('Please go through the cards again before you use the system.','Пожалуйста, пройдите карточки ещё раз, прежде чем пользоваться системой.');
}
function learnSeen(){try{return window.localStorage.getItem('homensai-vpn-learn-seen')==='1';}catch(e){return false;}}
function learnMarkSeen(){try{window.localStorage.setItem('homensai-vpn-learn-seen','1');}catch(e){}}
function renderLearn(){
  var host=E('section',{'class':'hv-chart-card hv-learn'});
  var mode=learnSeen()?'toc':'flow',visited=[],step=0,answers=[],checked=false,generation=0,total=LEARN_LESSONS.length+LEARN_QUIZ.length+1;
  function clear(){while(host.firstChild)host.removeChild(host.firstChild);}
  function inline(text){return richText(text);}
  function progress(){return E('div',{'class':'hv-learn-progress','role':'progressbar','aria-valuemin':'0','aria-valuemax':String(total),'aria-valuenow':String(step+1)},[E('span',{'style':'width:'+Math.round((step+1)*100/total)+'%'}),E('small',{},bi('Step ','Шаг ')+(step+1)+' / '+total)]);}
  function nav(back,next,nextLabel,nextDisabled){
    var shown=generation,used=false;
    function action(fn,disabled){return function(){if(disabled||used||generation!==shown)return;used=true;return fn();};}
    return E('div',{'class':'hv-learn-nav'},[back?E('button',{'type':'button','class':'cbi-button','click':action(back,false)},bi('Back','Назад')):E('span'),next?E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':nextDisabled?'disabled':null,'click':action(next,nextDisabled)},nextLabel):E('span')]);
  }
  function go(index){if(!Number.isInteger(index)||index<0||index>=total)return;mode='flow';step=index;checked=false;draw();}
  function chips(){
    var items=LEARN_LESSONS.map(function(l,i){return E('button',{'type':'button','class':'hv-chip'+(step===i?' hv-chip-current':'')+(visited[i]?' hv-chip-visited':''),'title':bi(l.title[0],l.title[1]),'aria-label':bi(l.title[0],l.title[1]),'click':function(){go(i);}},String(i+1));});
    items.push(E('button',{'type':'button','class':'hv-chip hv-chip-quiz'+(step>=LEARN_LESSONS.length?' hv-chip-current':''),'title':bi('Questions','Вопросы'),'click':function(){go(LEARN_LESSONS.length);}},'?'));
    return E('div',{'class':'hv-chips'},[E('button',{'type':'button','class':'cbi-button hv-chip-contents','click':function(){mode='toc';draw();}},bi('☰ Contents','☰ Оглавление'))].concat(items));
  }
  function toc(){
    var rows=LEARN_LESSONS.map(function(l,i){return E('button',{'type':'button','class':'hv-toc-item'+(visited[i]?' hv-toc-visited':''),'click':function(){go(i);}},[E('span',{'class':'hv-toc-num','aria-hidden':'true'},String(i+1)),E('span',{'class':'hv-toc-text'},[E('strong',{},bi(l.title[0],l.title[1])),E('small',{},bi(l.body[0][0].split('. ')[0]+'.',l.body[0][1].split('. ')[0]+'.'))])]);});
    rows.push(E('button',{'type':'button','class':'hv-toc-item hv-toc-quiz','click':function(){answers=[];go(LEARN_LESSONS.length);}},[E('span',{'class':'hv-toc-num','aria-hidden':'true'},'?'),E('span',{'class':'hv-toc-text'},[E('strong',{},bi('Questions and your score','Вопросы и ваша оценка')),E('small',{},bi('Check what you remember.','Проверьте, что вы запомнили.'))])]));
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('h2',{},bi('Contents','Оглавление')),E('p',{'class':'hv-learn-intro'},learnSeen()?bi('You have finished the training once. Open any topic you need, in any order.','Вы уже прошли обучение один раз. Открывайте любую тему, в любом порядке.'):bi('Open any topic, or read them one after another starting with 1. The first full pass takes about 5 minutes.','Откройте любую тему или читайте по порядку, начиная с 1. Первый полный проход занимает около 5 минут.')),E('div',{'class':'hv-toc'},rows)]));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){visited=[];answers=[];go(0);}},bi('Start from the beginning','Начать с самого начала')),E('span')]));
  }
  function lesson(){
    var l=LEARN_LESSONS[step];visited[step]=true;
    host.appendChild(chips());host.appendChild(progress());
    if(step===0)host.appendChild(E('p',{'class':'hv-learn-intro'},bi('A short training, about 5 minutes: what the system is, how to set it up and use it, and what to do when something goes wrong. At the end there are questions.','Короткое обучение, около 5 минут: что это за система, как её настроить и использовать и что делать, если что-то пошло не так. В конце — вопросы.')));
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},l.icon),E('h2',{},bi(l.title[0],l.title[1])),
      E('div',{'class':'hv-learn-body'},l.body.map(function(p){return E('p',{},inline(bi(p[0],p[1])));})),
      l.cmds?E('div',{'class':'hv-learn-cmds'},l.cmds.map(function(c){return E('div',{'class':'hv-learn-cmd'},[E('p',{},bi(c[1][0],c[1][1])),helpCommand(c[0])]);})):null,
      E('p',{'class':'hv-learn-example'},inline(bi(l.example[0],l.example[1]))),
      E('p',{'class':'hv-learn-tip'},[E('strong',{},bi('Remember: ','Запомните: ')),inline(bi(l.tip[0],l.tip[1]))])]));
    host.appendChild(nav(step>0?function(){step--;draw();}:null,function(){step++;draw();},step===LEARN_LESSONS.length-1?bi('To the questions','К вопросам'):bi('Next','Дальше')));
  }
  function question(){
    var index=step-LEARN_LESSONS.length,q=LEARN_QUIZ[index],chosen=answers[index]||(answers[index]=[]),shown=generation;
    var grade=checked?learnGrade(q,chosen):null;
    host.appendChild(chips());host.appendChild(progress());
    var options=q.o.map(function(option,i){
      var mark=grade?grade.marks[i]:'none';
      var box=E('input',{'type':'checkbox','disabled':checked?'disabled':null,'change':function(){if(checked||generation!==shown)return;var at=chosen.indexOf(i);if(box.checked&&at<0)chosen.push(i);if(!box.checked&&at>=0)chosen.splice(at,1);draw();}});
      box.checked=chosen.indexOf(i)>=0;
      var note=mark==='right'?bi('Correct','Верно'):mark==='wrong'?bi('Wrong choice','Неверный выбор'):mark==='missed'?bi('This was a correct answer','Это был правильный ответ'):'';
      return E('label',{'class':'hv-quiz-option hv-quiz-'+mark},[box,(/^homensai-vpn-emergency /.test(option[0])?E('code',{'class':'hv-code'},option[0]):E('span',{},bi(option[0],option[1]))),note?E('small',{},note):null].filter(Boolean));
    });
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},'?'),E('h2',{},bi('Question ','Вопрос ')+(index+1)+' / '+LEARN_QUIZ.length),E('p',{'class':'hv-quiz-question'},bi(q.q[0],q.q[1])),E('div',{'class':'hv-quiz-options'},options),
      grade?E('p',{'class':'hv-quiz-result hv-quiz-result-'+(grade.ok?'ok':'bad'),'role':'status'},grade.ok?bi('Correct!','Верно!'):bi('Not quite. Red is your wrong choice, green is the right answer.','Не совсем. Красным отмечен ваш неверный выбор, зелёным — правильный ответ.')):null].filter(Boolean)));
    var last=index===LEARN_QUIZ.length-1;
    host.appendChild(nav(null,function(){if(!checked){checked=true;draw();}else{checked=false;step++;draw();}},checked?(last?bi('See my result','Узнать результат'):bi('Next question','Следующий вопрос')):bi('Check the answer','Проверить ответ'),!checked&&chosen.length===0));
  }
  function result(){
    var s=learnScore(LEARN_QUIZ,answers);learnMarkSeen();
    if(s.percent>=80){try{window.localStorage.setItem('homensai-vpn-learn-done','1');}catch(e){}}
    host.appendChild(progress());
    host.appendChild(E('div',{'class':'hv-learn-card hv-learn-final'},[E('div',{'class':'hv-learn-score hv-learn-score-'+(s.percent>=80?'good':s.percent>=50?'mid':'low'),'aria-hidden':'true'},s.percent+'%'),
      E('h2',{},bi('Your knowledge: ','Ваши знания: ')+s.percent+bi(' out of 100',' из 100')),
      E('p',{},bi(s.correct+' of '+s.total+' answers were fully correct.',s.correct+' из '+s.total+' ответов полностью верны.')),
      E('p',{'class':'hv-learn-verdict'},learnVerdict(s.percent))]));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){visited=[];step=0;answers=[];checked=false;mode='flow';draw();}},bi('Take the training again','Пройти обучение заново')),E('button',{'type':'button','class':'cbi-button','click':function(){mode='toc';draw();}},bi('☰ Contents','☰ Оглавление')),E('a',{'class':'cbi-button','href':'#help'},bi('Open Help','Открыть помощь'))]));
  }
  function draw(){generation++;if(!Number.isInteger(step)||step<0||step>=total){step=0;mode='toc';checked=false;}clear();if(mode==='toc')toc();else if(step<LEARN_LESSONS.length)lesson();else if(step<LEARN_LESSONS.length+LEARN_QUIZ.length)question();else result();}
  draw();
  return host;
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

/* Extra rows of the error table: controller states, reasons, diagnosis words, fault-test, Telegram, setup and speed codes,
   notices of the page, and families of internal codes. Row: [code, group, name EN, name RU, meaning EN, meaning RU, fix EN, fix RU, example EN, example RU].
   Nothing here is a promise about a real router: a code tells what was observed, the cause may stay unknown. */
var ERROR_EXTRA_GROUPS=[['manual',['Manual requests and recovery','Ручные запросы и восстановление']],['platform',['Manual platform readiness','Готовность платформы к ручному переключению']],['state',['Controller states and phases','Состояния и этапы контроллера']],['internal',['Internal checks and safety stops','Внутренние проверки и защитные остановки']]];
var ERROR_EXTRA_ROWS=[
 ["DEVICE-MODEL-INVALID","platform","Choose a supported router model","Выберите поддерживаемую модель","The saved or requested model is not Automatic, MT6000 or MT3000.","Сохранённая или выбранная модель не входит в список: авто, MT6000, MT3000.","Open Settings and review the router model on the first setup step.","Откройте настройки и проверьте модель роутера на первом шаге мастера."],
 ["DEVICE-MODEL-MISMATCH","platform","Router model does not match","Модель роутера не совпадает","The selected model differs from detected hardware, or hardware could not be verified.","Выбранная модель отличается от обнаруженного оборудования либо оборудование не удалось проверить.","Choose automatic detection or the actual detected model; model selection never enables unsupported switching.","Выберите автоопределение или обнаруженную модель; выбор модели не включает неподдерживаемое переключение."],
 ["MANUAL-FIELDS","manual","Manual request form changed","Форма ручного запроса изменилась","The request contains missing or unexpected fields.","В запросе отсутствуют поля либо есть лишние.","Reload the page and choose one of the two manual switch buttons.","Обновите страницу и выберите одну из двух кнопок ручного переключения."],
 ["MANUAL-DIRECTION-INVALID","manual","Choose a supported direction","Выберите допустимое направление","The requested direction is neither the saved primary nor the reserve.","Запрошено направление, отличное от сохранённого основного или резервного.","Reload the page and use Switch to primary or Switch to reserve.","Обновите страницу и используйте переключение на основной либо резервный."],
 ["MANUAL-STATE-UNVERIFIED","manual","Manual control state is unknown","Состояние ручного управления неизвестно","The request or Stop records could not be verified; a new switch is blocked.","Не удалось проверить запись запроса или остановки; новое переключение заблокировано.","Refresh the status. Keep Emergency Stop and trusted recovery available; do not delete the state records.","Обновите состояние. Используйте аварийную остановку и доступное восстановление; не удаляйте записи состояния."],
 ["MANUAL-ALREADY-CLAIMED","manual","Request was already taken","Запрос уже принят в работу","The controller has already taken or finished this request; it must not run it twice.","Контроллер уже принял или завершил этот запрос; повторное выполнение недопустимо.","Wait for fresh status and review the actual path before making another explicit request.","Дождитесь свежего состояния и проверьте фактический путь перед новым явным запросом."],
 ["MANUAL-REQUEST-EXPIRED","manual","Manual request expired","Время ручного запроса истекло","The request was not taken within its short validity window. This does not confirm the current traffic path.","Запрос не принят в течение короткого срока действия. Это не подтверждает текущий путь трафика.","Refresh the router state and repeat only if the switch is still needed.","Обновите состояние роутера и повторите только при необходимости переключения."],
 ["STOP-SUPERSEDED-MANUAL","manual","Stop cancelled the pending switch","Остановка отменила ожидающее переключение","An Emergency Stop arrived after this manual request, so the pending request cannot run.","Аварийная остановка поступила после ручного запроса, поэтому ожидающий запрос не выполнится.","Review the current path. A later switch requires a new explicit request.","Проверьте текущий путь. Для последующего переключения нужен новый явный запрос."],
 ["MANUAL-CONFIG-CHANGED","manual","Settings changed during the request","Настройки изменились во время запроса","The selected pair, trial window or policy no longer matches the request.","Выбранная пара, окно теста или политика больше не соответствует запросу.","Refresh and review the pair and required checks before requesting again.","Обновите страницу, проверьте пару и необходимые проверки перед новым запросом."],
 ["MANUAL-SUPERVISOR-UNAVAILABLE","manual","No fresh controller state","Нет свежего состояния контроллера","The switching controller has not supplied a recent verified status.","Контроллер переключений не предоставил недавнего проверенного состояния.","Check Service monitor and wait for fresh status. A monitor-only installation cannot perform native switches.","Проверьте службу мониторинга и дождитесь свежего состояния. Установка только для мониторинга не выполняет нативных переключений."],
 ["MANUAL-STOP-AUTO-FIRST","manual","Stop Auto before manual switching","Остановите Auto перед ручным переключением","Auto is active; a separate manual switch cannot compete with it.","Auto активен; отдельное ручное переключение не должно с ним конкурировать.","Press Emergency Stop and review the resulting path before trying manual switching.","Нажмите аварийную остановку и проверьте получившийся путь перед ручным переключением."],
 ["MANUAL-SELECTION-UNVERIFIED","manual","Selected pair is not verified","Выбранная пара не проверена","The controller cannot prove the selected primary and reserve or their routing policy.","Контроллер не может подтвердить выбранные основной и резервный профили либо их политику маршрутизации.","Review the saved pair in Settings and obtain fresh matching checks.","Проверьте сохранённую пару в настройках и дождитесь свежих согласованных проверок."],
 ["MANUAL-REQUEST-PENDING","manual","Another manual request is pending","Другой ручной запрос ещё выполняется","A manual switch is already queued or running.","Ручное переключение уже ожидает выполнения или выполняется.","Wait for its result or use Emergency Stop; do not submit duplicates.","Дождитесь результата либо используйте аварийную остановку; не отправляйте дубликаты."],
 ["MANUAL-REQUEST-UNCONFIRMED","manual","Request was not confirmed","Запрос не подтверждён","No reliable acknowledgement was received. The request may have been stored.","Надёжное подтверждение не получено. Запрос мог сохраниться.","Refresh status and inspect the actual path before deciding whether to retry.","Обновите состояние и проверьте фактический путь перед решением о повторе."],
 ["MANUAL-RESULT-INVALID","manual","Result record is invalid","Запись результата некорректна","The result record does not match the supported manual request format. It does not prove success.","Запись результата не соответствует формату ручного запроса. Она не доказывает успех.","Keep the diagnostics and check the current path; do not force completion or erase recovery records.","Сохраните диагностику и проверьте текущий путь; не принуждайте завершение и не стирайте записи восстановления."],
 ["MANUAL-COMPLETION-UNVERIFIED","manual","Switch completion is not proved","Завершение переключения не доказано","The controller could not verify the transaction evidence required to mark this request complete.","Контроллер не смог проверить данные транзакции, необходимые для подтверждения завершения запроса.","Review fresh route and connectivity status. Use the documented recovery controls if needed.","Проверьте свежие данные маршрута и доступности. При необходимости используйте описанные средства восстановления."],
 ["RETURN-UNCONFIRMED","manual","Return to primary is unconfirmed","Возврат на основной не подтверждён","The return request has no verified successful result. The reserve may still be in use.","У запроса возврата нет проверенного успешного результата. Резерв может ещё использоваться.","Inspect the actual path and primary health before requesting another return.","Проверьте фактический путь и доступность основного перед повторным возвратом."],
 ["MANUAL-RESULT-UNCONFIRMED","manual","Manual result is unknown","Результат ручного переключения неизвестен","The request did not produce a trusted final result. A queue acknowledgement is not route confirmation.","Запрос не дал доверенного конечного результата. Подтверждение очереди не подтверждает маршрут.","Refresh status and review Stop or recovery controls before repeating any action.","Обновите состояние и проверьте средства остановки или восстановления перед повторным действием."],
 ["MANUAL-SUPERVISOR-RECOVERED","manual","Controller recovered an unfinished request","Контроллер восстановился после незавершённого запроса","After restarting, the controller found an unfinished request without sufficient proof of completion. It is not replayed automatically.","После перезапуска контроллер обнаружил незавершённый запрос без достаточного подтверждения результата. Автоматически он не повторяется.","Review the current path and recovery status before issuing a new request.","Проверьте текущий путь и состояние восстановления перед новым запросом."],
 ["MANUAL-TRANSACTION-STATE-UNVERIFIED","manual","Previous transaction may need recovery","Предыдущей транзакции может требоваться восстановление","The absence of an earlier transaction or application safety guard could not be verified.","Не удалось подтвердить отсутствие прежней транзакции или защитной блокировки приложения.","Keep Stop and recovery available. Resolve the existing transaction through the documented recovery procedure before starting another.","Используйте доступные остановку и восстановление. Завершите прежнюю транзакцию по описанной процедуре перед новой."],
 ["MANUAL-REQUEST-INVALID","manual","Manual request could not be trusted","Ручному запросу нельзя доверять","The final controller boundary rejected the manual request identity or format.","Последняя проверка контроллера отклонила идентификатор либо формат ручного запроса.","Refresh the application and review current status before making a new explicit request.","Обновите приложение и проверьте текущее состояние перед новым явным запросом."],
 ["OPERATOR-MANUAL","manual","Operator requested a manual switch","Оператор запросил ручное переключение","This event belongs to one explicit manual switch. It does not imply primary failure or that Auto was enabled.","Это событие относится к одному явному ручному переключению. Оно не означает отказ основного или включение Auto.","Read the later transaction outcome and current confirmed path to see whether it succeeded.","Посмотрите последующий итог транзакции и текущий подтверждённый путь, чтобы узнать результат."],
 ["MT3000-MANUAL-ADAPTER-NOT-CERTIFIED","platform","MT3000 manual switching is not certified","Ручное переключение MT3000 не подтверждено","The GL-MT3000 manual adapter has not passed the required certification. Passing individual observations does not authorize a switch.","Адаптер ручного переключения GL-MT3000 не прошёл необходимое подтверждение. Отдельные успешные наблюдения не разрешают переключение.","Continue monitoring; complete the documented router and LAN acceptance before enabling this adapter.","Продолжайте мониторинг; завершите описанные проверки роутера и LAN перед включением адаптера."],
 ["MT3000-COLLECTION-DEADLINE","platform","Readiness check took too long","Проверка готовности заняла слишком много времени","The bounded collection of router evidence exceeded its deadline; the incomplete snapshot cannot authorize a switch.","Сбор данных роутера превысил ограниченное время; неполный снимок не разрешает переключение.","Wait for the router to settle and request fresh status. If it repeats, inspect router load.","Дождитесь спокойного состояния роутера и запросите свежие данные. Если повторяется, проверьте нагрузку."],
 ["MT3000-COLLECTION-CLOCK-CHANGED","platform","Router clock changed during checks","Часы роутера изменились во время проверок","Clock continuity was lost while readiness evidence was collected. Its timing cannot be trusted.","При сборе данных готовности нарушилась непрерывность времени. Их временным отметкам нельзя доверять.","Review the router clock and wait for stable time before collecting new evidence.","Проверьте часы роутера и дождитесь стабильного времени перед новым сбором данных."],
 ["MT3000-READ-TIMEOUT","platform","Router read timed out","Чтение данных роутера превысило время","A read-only readiness command did not finish in its allowed time.","Команда чтения готовности не завершилась за разрешённое время.","Wait and refresh. Inspect router responsiveness if this continues.","Подождите и обновите данные. Если повторяется, проверьте отзывчивость роутера."],
 ["MT3000-READ-FAILED","platform","Router evidence could not be read","Не удалось прочитать данные роутера","A command used to collect readiness evidence failed.","Команда сбора данных готовности завершилась ошибкой.","Keep the diagnostic code and check the router services and required tools before retrying.","Сохраните код диагностики и проверьте службы и необходимые программы роутера перед повтором."],
 ["MT3000-READ-UNVERIFIED","platform","Router read could not be validated","Чтение данных роутера не проверено","A readiness response was incomplete, oversized or did not match the expected format.","Ответ проверки готовности неполон, слишком велик либо имеет неожиданный формат.","Refresh once the router is stable. If repeated, have the firmware compatibility checked.","Обновите данные после стабилизации роутера. Если повторяется, проверьте совместимость прошивки."],
 ["MT3000-PLATFORM-UNVERIFIED","platform","Router model is not verified","Модель роутера не проверена","The collected board identity does not match the supported GL-MT3000 platform contract.","Собранные данные платы не соответствуют поддерживаемому варианту GL-MT3000.","Check the actual router model. Monitoring does not grant manual switching support.","Проверьте фактическую модель роутера. Мониторинг не означает поддержку ручного переключения."],
 ["MT3000-FIRMWARE-UNVERIFIED","platform","Router firmware is not verified","Прошивка роутера не проверена","The firmware, kernel or architecture differs from the inspected GL-MT3000 combination.","Прошивка, ядро или архитектура отличается от проверенного сочетания GL-MT3000.","Keep native switching disabled until this exact firmware combination has been reviewed.","Оставьте нативное переключение выключенным до проверки именно этого сочетания прошивки."],
 ["MT3000-FIREWALL-UNVERIFIED","platform","Firewall type is not verified","Тип firewall не проверен","The router firewall does not match the firewall arrangement required by this adapter.","Firewall роутера не соответствует варианту, необходимому этому адаптеру.","Keep current routes and have firewall compatibility reviewed; do not force the adapter on.","Сохраните текущие маршруты и проверьте совместимость firewall; не включайте адаптер принудительно."],
 ["FW3-INCLUDE-CONTRACT-UNVERIFIED","platform","Firmware firewall integration is unverified","Интеграция firewall прошивки не проверена","The firmware firewall include settings differ from the inspected contract; safe reload coordination is not proved.","Настройки подключаемого скрипта firewall отличаются от проверенного варианта; безопасная координация перезагрузки не доказана.","Keep current routes and have the firmware firewall integration checked before switching.","Сохраните текущие маршруты и проверьте интеграцию firewall прошивки перед переключением."],
 ["FW3-RUNTIME-STATE-UNVERIFIED","platform","Live firewall state is unknown","Рабочее состояние firewall неизвестно","The current firewall zones could not be read and validated.","Не удалось прочитать и проверить текущие зоны firewall.","Wait for any firewall changes to finish, then refresh. Do not infer readiness from saved settings alone.","Дождитесь завершения изменений firewall и обновите данные. Одни сохранённые настройки не доказывают готовность."],
 ["VENDOR-WORKER-QUIET-UNVERIFIED","platform","Router VPN changes may still be running","Изменение VPN роутером может ещё выполняться","Repeated observations did not prove that the firmware VPN workers are idle.","Повторные наблюдения не подтвердили, что процессы VPN штатной прошивки свободны.","Wait for the router VPN operation to finish before requesting another change.","Дождитесь завершения операции VPN роутера перед новым изменением."],
 ["NATIVE-CONTROLLER-STATE-UNVERIFIED","platform","Auto controller is not confirmed off","Выключение контроллера Auto не подтверждено","The saved native controller setting is not explicitly off, so the manual adapter cannot claim exclusive control.","Сохранённая настройка нативного контроллера не подтверждает выключение, поэтому ручной адаптер не может получить исключительное управление.","Stop Auto and review its fresh status before manual switching.","Остановите Auto и проверьте его свежее состояние перед ручным переключением."],
 ["SELECTED-RULES-NOT-ADJACENT","platform","Selected VPN rules are not adjacent","Правила выбранных VPN не соседние","The saved primary and reserve rules are separated in the router policy; the bounded adapter cannot safely reorder this pair.","Правила сохранённых основного и резервного разделены в политике роутера; ограниченный адаптер не может безопасно переставить эту пару.","Review the VPN policy with the administrator; do not change rule order while a transaction is active.","Проверьте политику VPN с администратором; не меняйте порядок правил во время активной транзакции."],
 ["EXISTING-TUNNEL-BINDING-UNVERIFIED","platform","Live VPN binding is unverified","Рабочая привязка VPN не проверена","A selected tunnel is down, changing or no longer matches its observed interface, device and routing identity.","Выбранный туннель отключён, изменяется либо больше не соответствует наблюдавшимся интерфейсу, устройству и маршрутизации.","Wait for the intended VPNs to settle and obtain fresh matching checks.","Дождитесь стабильной работы нужных VPN и свежих согласованных проверок."],
 ["FW3-SELECTED-ZONE-UNVERIFIED","platform","VPN firewall zone is unverified","Зона firewall VPN не проверена","A selected VPN interface is missing from the current verified firewall zones.","Выбранный интерфейс VPN отсутствует в текущих проверенных зонах firewall.","Have the VPN firewall zone binding checked before switching; preserve existing protection rules.","Проверьте привязку зоны firewall VPN перед переключением; сохраните действующие защитные правила."],
 ["SHARED-KERNEL-BINDING","platform","VPN choices share the same routing resource","Выбранные VPN используют общий ресурс маршрутизации","The two choices share a device, interface identity or routing mark/table, so independent paths cannot be proved.","Два выбранных VPN используют общее устройство, идентичность интерфейса либо метку и таблицу маршрутизации; независимость путей не доказана.","Choose truly distinct tunnels and repeat the identity checks. Different display names are not sufficient.","Выберите действительно разные туннели и повторите проверки привязки. Разных названий недостаточно."],
 ["TARGET-ROUTER-PATH-UNVERIFIED","platform","Reserve router checks have not passed","Резерв не прошёл проверки с роутера","The current target has no fresh matching successful DNS and HTTPS evidence. This is separate from LAN path confirmation.","Для текущего целевого VPN нет свежих согласованных успешных проверок DNS и HTTPS. Это отдельно от подтверждения пути LAN.","Check reserve connectivity and wait for fresh router measurements; LAN confirmation is still required separately.","Проверьте доступность резерва и дождитесь свежих измерений роутера; подтверждение LAN по-прежнему требуется отдельно."],
 ["MT3000-EVIDENCE-UNVERIFIED","platform","MT3000 readiness evidence is incomplete","Данные готовности MT3000 неполны","The collected readiness snapshot is inconsistent or cannot be validated. No manual switch is authorized by it.","Собранный снимок готовности несогласован либо не проходит проверку. Он не разрешает ручное переключение.","Review diagnostics and obtain a fresh complete snapshot after the router is stable.","Проверьте диагностику и получите свежий полный снимок после стабилизации роутера."],

 ['MONITOR-ONLY-DEPLOYMENT','switch','Installation is limited to monitoring','Установка ограничена мониторингом','This deployment permits monitoring only. Native switching is disabled; monitor results do not certify firmware coordination or the LAN path.','Эта установка разрешает только мониторинг. Нативное переключение выключено; результаты мониторинга не подтверждают координацию с прошивкой или путь LAN.','Continue monitoring within the agreed scope. Native actions remain unavailable in this deployment.','Продолжайте мониторинг в согласованном объёме. Нативные действия в этой установке остаются недоступны.'],
 ['MONITOR-ONLY-INVALID','switch','Deployment mode could not be verified','Не удалось проверить режим установки','The internal deployment setting is malformed or unverified. Native actions are refused.','Внутренний параметр установки повреждён или не проверен. Нативные действия отклоняются.','Have the deployment settings checked against the verified installation procedure. Do not treat this state as native readiness.','Проверьте параметры установки по проверенной процедуре установки. Это состояние не означает готовность нативного переключения.'],
 ['NATIVE-PROGRESS-UNVERIFIED','switch','Controller progress records are unverified','Записи состояния контроллера не проверены','Saved native progress or state records cannot be trusted. New controller actions are refused; Stop and recovery from a trusted journal remain available.','Сохранённым записям хода работы или состояния контроллера нельзя доверять. Новые действия отклоняются; остановка и восстановление по доверенному журналу остаются доступны.','Keep the Stop and recovery controls available. Inspect diagnostics and restore progress records through the documented recovery procedure.','Используйте доступные средства остановки и восстановления. Проверьте диагностику и восстановите записи состояния по описанной процедуре восстановления.'],
 ['VENDOR-IDENTITY-UNKNOWN','switch','Tunnel identity is unknown','Идентичность туннеля неизвестна','The configured profile cannot be matched unambiguously to a current router tunnel.','Не удалось однозначно сопоставить профиль с текущим туннелем роутера.','Wait for fresh observations. If the saved pair is unbound, choose active profiles in Settings and save the pair.','Дождитесь свежих наблюдений. Если пара не привязана, выберите активные профили в настройках и сохраните пару.'],
 ['VENDOR-IDENTITY-CHANGED','monitor','Binding changed during a check','Привязка изменилась во время проверки','The tunnel binding changed while measurements were running; their health and exit results were discarded.','Привязка туннеля изменилась во время измерений; результаты доступности и адреса выхода отброшены.','Wait for new checks on the current binding.','Дождитесь новых проверок текущей привязки.'],
 ['PROFILE-IDENTITY-CHANGED','switch','Profile evidence changed','Данные о привязке профиля изменились','The current profile or tunnel generation no longer matches the evidence used for this decision.','Текущий профиль или поколение туннеля не соответствует данным, использованным для решения.','Wait for current observations; a new verified trial may be needed before Auto can run.','Дождитесь текущих наблюдений; перед запуском Auto может потребоваться новый подтверждённый тест.'],
 ['VENDOR-SAME-TUNNEL','switch','Server selection belongs to the router','Сервер выбирает штатная прошивка','Both choices refer to one observed tunnel. The application does not run a competing server switch loop.','Оба выбора относятся к одному наблюдаемому туннелю. Приложение не запускает конкурирующий перебор серверов.','Choose a different tunnel for application reserve switching.','Для резервирования приложением выберите другой туннель.'],
 ['SETUP-SAME-TUNNEL','setup','Choose two different tunnels','Выберите два разных туннеля','The selected primary and reserve resolve to the same router tunnel.','Выбранные основной и резервный профили привязаны к одному туннелю роутера.','Select an active profile on another tunnel, or defer the pair.','Выберите активный профиль другого туннеля либо отложите пару.'],
 ['VENDOR-SETTLING','switch','Observing the current configuration','Идёт наблюдение текущей конфигурации','The identity observation window has not finished. This does not reveal whether the firmware exhausted its server attempts.','Окно наблюдения за идентичностью ещё не завершено. Это не показывает, исчерпала ли прошивка попытки подключения серверов.','Wait for repeated fresh observations.','Дождитесь повторных свежих наблюдений.'],
 ['CROSS-TUNNEL-READY','switch','Candidate for verification','Кандидат для проверки','The current configured tunnel identities are eligible for read-only planning; route changes remain separately guarded.','Текущие привязки туннелей подходят для планирования без применения; изменение маршрутов требует отдельных проверок.','Review the candidate and the required native/LAN checks.','Проверьте кандидата и необходимые проверки контроллера и LAN.'],
 ['CURRENT-PROFILE-FAILURE-STREAK','switch','Current profile failed repeated checks','Текущий профиль не прошёл несколько проверок','The current bound profile has the configured failure streak. This does not prove that all servers in its tunnel have failed.','У текущего привязанного профиля накопилась заданная серия неудачных проверок. Это не доказывает отказ всех серверов его туннеля.','Review tunnel observations and reserve evidence.','Проверьте наблюдения туннеля и данные о резерве.'],
 ['RESERVE-IDENTITY-UNKNOWN','switch','Current reserve identity is unknown','Текущая привязка резерва неизвестна','The controller cannot safely attach old reserve health to its current tunnel member.','Контроллер не может безопасно отнести старые проверки резерва к текущему профилю туннеля.','Keep the recovery controls available and obtain fresh observations before a new forward action.','Используйте доступные средства восстановления и дождитесь свежих наблюдений перед новым переключением.'],
 ['VENDOR-FIRST-OBSERVATION','data','First configured binding observed','Впервые наблюдалась привязка конфигурации','The monitor first observed this configured tunnel member. No switch cause is inferred.','Монитор впервые увидел этот профиль в конфигурации туннеля. Причина выбора не предполагается.','No action is required; wait for fresh checks.','Действий не требуется; дождитесь свежих проверок.'],
 ['VENDOR-PROFILE-CHANGED','data','Configured tunnel member changed','Профиль в конфигурации туннеля изменился','A different configured profile was observed on the same tunnel. The cause and actual LAN outcome remain unobserved.','В том же туннеле наблюдался другой профиль конфигурации. Причина и фактический результат для LAN не установлены.','Inspect the current profile checks.','Посмотрите проверки текущего профиля.'],
 ['VENDOR-BINDING-CHANGED','data','Tunnel binding generation changed','Поколение привязки туннеля изменилось','The monitor observed a new binding generation; earlier health cannot make it ready.','Монитор увидел новое поколение привязки; старые проверки не подтверждают его готовность.','Wait for new generation-scoped checks.','Дождитесь проверок нового поколения привязки.'],
 ['VENDOR-BINDING-UNKNOWN','data','Configured binding became unknown','Привязка конфигурации стала неизвестной','The previous configured tunnel member can no longer be identified unambiguously.','Предыдущий профиль конфигурации туннеля больше не определяется однозначно.','Inspect current router configuration and fresh observations.','Проверьте текущую конфигурацию роутера и свежие наблюдения.'],
 ['VENDOR-OBSERVATION-TIME','data','Invalid observation clock','Некорректное время наблюдения','The observation time is invalid; no current identity is asserted.','Время наблюдения некорректно; текущая идентичность не подтверждена.','Check the router clock and retry observation.','Проверьте часы роутера и дождитесь нового наблюдения.'],
 ['ONBOARDING-FIELDS','setup','Setup form changed','Форма настройки изменилась','The complete setup request has missing or unexpected sections.','В запросе общей настройки отсутствуют разделы или есть лишние.','Reload the application and review the complete setup again.','Обновите приложение и снова проверьте общую настройку.'],
 ['ONBOARDING-SYSTEM-FIELDS','setup','Check VPN setup','Проверьте настройку VPN','The VPN setup fields do not match the supported form.','Поля настройки VPN не соответствуют поддерживаемой форме.','Reload and choose existing profiles or explicitly defer the pair.','Обновите страницу и выберите существующие профили либо явно отложите пару.'],
 ['ONBOARDING-PAIR-DEFERRED','setup','Review deferred VPN pair','Проверьте отложенную пару VPN','A deferred VPN pair must have read-only planning switched off.','При отложенной паре VPN планирование должно быть выключено.','Go Back to the VPN step and choose the defer option, or choose two different existing profiles.','Вернитесь к шагу VPN и выберите откладывание пары либо два разных существующих профиля.'],
 ['ONBOARDING-APPEARANCE','setup','Check appearance defaults','Проверьте оформление по умолчанию','The saved default language, theme or design is unsupported.','Выбран неподдерживаемый язык, тема или оформление по умолчанию.','Choose a value from each list in the first step.','Выберите значение в каждом списке на первом шаге.'],
 ['ONBOARDING-TELEGRAM-FIELDS','setup','Check optional Telegram setup','Проверьте необязательную настройку Telegram','The Telegram section does not match the supported form.','Раздел Telegram не соответствует поддерживаемой форме.','Keep existing settings, or enable the Telegram setup section and review its fields.','Оставьте существующие настройки либо включите раздел настройки Telegram и проверьте его поля.'],
 ['ONBOARDING-TOO-LARGE','setup','Setup request is too large','Запрос настройки слишком большой','The complete configuration exceeds the bounded save request size. Nothing was sent to the configuration writer.','Полная конфигурация превышает допустимый размер запроса сохранения. Запрос не передан записи настроек.','Shorten display names and channel groups, then review again.','Сократите названия серверов и групп каналов и проверьте снова.'],
 ['ONBOARDING-SAVE-UNCONFIRMED','setup','Setup save not confirmed','Сохранение настройки не подтверждено','The router did not confirm the complete setup save. The page keeps your draft; the router may already have committed the settings.','Роутер не подтвердил общее сохранение. Страница сохраняет черновик; параметры уже могли записаться на роутере.','Reload to read the router state before trying again.','Обновите страницу, чтобы прочитать состояние роутера перед повтором.'],
 ['CONTROL-REVISION-STALE','switch','Auto controls changed','Управление Auto изменилось','The Start request belongs to older Auto controls and was refused.','Запрос запуска относится к прежнему состоянию управления Auto и отклонён.','Refresh the current state before starting again.','Обновите данные перед новым запуском.'],
 ['START-STATE-UNVERIFIED','switch','Saved Auto state unverified','Состояние Auto не проверено','Saved Auto state could not be verified. Starting is blocked.','Не удалось проверить сохранённое состояние Auto. Запуск заблокирован.','Stop Auto, review the settings, then try again.','Остановите Auto, проверьте настройки и повторите попытку.'],
 ['STOP-SUPERSEDED-START','switch','Pending Start cancelled','Ожидающий запуск отменён','Stop cancelled this pending Start.','Остановка отменила ожидающий запуск.','Press Start again when ready.','При необходимости нажмите «Запустить» снова.'],
 ['START-CONFIG-CHANGED','switch','Settings changed during Start','Настройки изменились при запуске','The settings changed while Start was checking them. The request was refused.','Настройки изменились во время проверки запуска. Запрос отклонён.','Review the settings and try Start again.','Проверьте настройки и повторите запуск.'],
 ['GUARD-RELEASE-ARM-FAILED','switch','Safety timer unavailable','Аварийный таймер недоступен','The independent cleanup timer could not start. No new traffic block was installed.','Независимый таймер очистки не запустился. Новая блокировка трафика не установлена.','Check router resources and retry later.','Проверьте ресурсы роутера и повторите позже.'],
 ['GUARD-RELEASE-UNCONFIRMED','switch','Safety block removal unconfirmed','Снятие блокировки не подтверждено','Removal of the traffic block is unverified; recovery remains pending.','Снятие блокировки трафика не подтверждено; восстановление ещё не завершено.','See Help → emergency return; do not assume Stop completed.','См. «Помощь» → аварийный возврат; остановка ещё не подтверждена.'],
 ['RELEASE-PENDING','state','Waiting for block removal','Ожидается снятие блокировки','No new switching is allowed while the old block is being removed.','Новые переключения запрещены, пока снимается прежняя блокировка.','Check cleanup; use emergency recovery if it persists.','Проверьте очистку; при повторении используйте аварийное восстановление.'],
 ['RETURN-TRANSACTION-MISMATCH','switch','Old return request rejected','Старый запрос возврата отклонён','The request belongs to another transaction. Nothing changed.','Запрос относится к другой транзакции. Ничего не изменено.','Refresh and request return again if needed.','Обновите страницу и при необходимости запросите возврат ещё раз.'],
 ['RETURN-REQUEST-EXPIRED','switch','Return request expired','Запрос возврата устарел','The request is outside the transaction or its one-minute validity window.','Запрос находится вне транзакции или минутного срока действия.','Refresh and request return again.','Обновите страницу и запросите возврат ещё раз.'],
 ['JOURNAL-PHASE-INVALID','switch','Invalid recovery phase','Неверная фаза восстановления','The journal phase is missing or unknown. Auto refuses to proceed.','Фаза журнала отсутствует или неизвестна. Auto не продолжает работу.','Use Help → emergency return; inspect recovery before restarting.','Используйте «Помощь» → аварийный возврат; проверьте восстановление до перезапуска.'],
 // ---- states and phases (not errors) ----
 ['OBSERVING','state','Watching the primary','Слежу за основным','Auto is on and watches the primary VPN. Nothing is switched now.','Auto включён и следит за основным VPN. Сейчас ничего не переключается.','Nothing to do.','Делать ничего не нужно.','If the line says OBSERVING and the Auto lamp is green, everything is normal.','Если в строке OBSERVING и лампа Auto зелёная — всё в порядке.'],
 ['ARMED','state','Ready to switch','Готов к переключению','The controller has prepared a switch (saved the old order and started its safety timer) but has not changed anything yet.','Контроллер подготовил переключение (сохранил прежний порядок и запустил страхующий таймер), но пока ничего не менял.','Nothing to do; the next state follows within seconds.','Делать ничего не нужно; следующее состояние наступит через секунды.','In an incident: ARMED → APPLYING → WAIT-CLIENT → COMMITTED is a normal successful switch.','В инциденте: ARMED → APPLYING → WAIT-CLIENT → COMMITTED — обычное успешное переключение.'],
 ['APPLYING','state','Switching now','Идёт переключение','The controller is changing the order of the VPN rules on the router right now.','Контроллер прямо сейчас меняет порядок VPN-правил на роутере.','Wait. If it stays here for more than a minute, press Stop in the Auto card.','Подождите. Если состояние держится больше минуты, нажмите «Стоп» в блоке Auto.','You see APPLYING, then ROLLED-BACK with VENDOR-APPLY-FAILED: GL.iNet did not accept the change and the router went back.','Видите APPLYING, затем ROLLED-BACK с VENDOR-APPLY-FAILED: GL.iNet не принял изменение, роутер вернулся назад.'],
 ['WAIT-CLIENT','state','Waiting for your computer','Ждём ваш компьютер','The route is switched and the controller waits up to 90 seconds for the LAN helper on your computer to confirm that the internet works.','Маршрут переключён, контроллер до 90 секунд ждёт, пока LAN-помощник на вашем компьютере подтвердит, что интернет работает.','Make sure the LAN helper is running. Without its confirmation the router goes back by itself.','Убедитесь, что LAN-помощник запущен. Без его подтверждения роутер вернётся сам.','WAIT-CLIENT followed by ROLLED-BACK and CLIENT-CONFIRMATION-TIMEOUT: nobody confirmed in time.','За WAIT-CLIENT следует ROLLED-BACK и CLIENT-CONFIRMATION-TIMEOUT: вовремя никто не подтвердил.'],
 ['COMMITTED','state','Reserve confirmed','Резерв подтверждён','The switch worked and your computer confirmed it: traffic goes through the reserve VPN.','Переключение удалось и ваш компьютер его подтвердил: трафик идёт через резервный VPN.','Nothing to do. Auto returns to the primary by itself when it has recovered, or press “Return to primary”.','Делать ничего не нужно. Auto вернётся на основной сам, когда он восстановится, либо нажмите «Вернуться на основной».','The overview says “Working on the reserve” and the state is COMMITTED: normal after a failure of the primary.','На «Обзоре» «Работаю на резерве», состояние COMMITTED — норма после отказа основного.'],
 ['ROLLED-BACK','state','Returned to the previous route','Возврат на прежний маршрут','The controller put the VPN rules back to the original order. The reason is in the next column or in the code beside it.','Контроллер вернул VPN-правила в исходный порядок. Причина указана рядом.','Read the reason code beside it; it tells why the switch did not stay.','Прочитайте код причины рядом: он говорит, почему переключение не осталось.','ROLLED-BACK + TRIAL-ENDED: the test window ended and the router returned to the primary. That is normal.','ROLLED-BACK + TRIAL-ENDED: окно теста закончилось и роутер вернулся на основной. Это норма.'],
 ['ROLLING-BACK','state','Returning now','Возвращаюсь','The controller is putting the original order back right now.','Контроллер прямо сейчас возвращает исходный порядок.','Wait a minute.','Подождите минуту.'],
 ['RESTORING','state','Restoring the route','Восстанавливаю маршрут','Same as returning: the original route is being restored and verified.','То же, что возврат: исходный маршрут восстанавливается и проверяется.','Wait a minute; if it does not end, see Help → “No internet”.','Подождите минуту; если не заканчивается, см. «Помощь» → «Нет интернета».'],
 ['TRIAL-REQUIRED','state','LAN trial needed','Нужен LAN-тест','Auto may not switch yet: no LAN trial has passed for the current settings.','Auto пока не может переключать: для текущих настроек не пройден LAN-тест.','Run the LAN helper (Settings → LAN trial → Help).','Запустите LAN-помощник («Настройки» → LAN-тест → Помощь).','After you change the primary or reserve, this state appears again: the old trial belongs to the old pair.','После смены основного или резервного это состояние появляется снова: прежний тест относился к прежней паре.'],
 ['BLOCKED','state','Blocked','Заблокировано','The controller refuses to act because a safety condition is not met; the conditions are listed next to it as codes.','Контроллер отказывается действовать, потому что не выполнено условие безопасности; условия перечислены рядом кодами.','Open each code beside it and fix the listed condition.','Откройте каждый код рядом и устраните перечисленное условие.','BLOCKED with HARDWARE-ACCELERATOR-UNVERIFIED: GL.iNet hardware acceleration is not proven off.','BLOCKED с HARDWARE-ACCELERATOR-UNVERIFIED: аппаратное ускорение GL.iNet не подтверждено как выключенное.'],
 ['STOPPED','state','Stopped','Остановлен','Auto is off and the controller does nothing.','Auto выключен, контроллер ничего не делает.','Turn Auto on when you want it.','Включите Auto, когда нужно.'],
 ['STOPPED-ON-RESERVE','state','Stopped on the reserve','Остановлен на резерве','Auto was stopped while traffic was on the reserve. The original route is not restored yet.','Auto остановлен, пока трафик шёл через резерв. Исходный маршрут пока не восстановлен.','When the primary works again press “Return to primary” in the Auto card.','Когда основной снова работает, нажмите «Вернуться на основной» в блоке Auto.'],
 ['DEGRADED-ON-RESERVE','state','Reserve is failing too','Резерв тоже не работает','Traffic is on the reserve and the reserve fails its checks as well.','Трафик идёт через резерв, и резерв тоже не проходит проверки.','Check both VPN profiles in GL.iNet. Auto returns to the primary when it passes its check.','Проверьте оба VPN-профиля в GL.iNet. Auto вернётся на основной, когда он пройдёт проверку.'],
 ['HELD-ON-RESERVE','state','Held on the reserve','Удерживаю на резерве','The controller stays on the reserve on purpose: your return rule says “hold” or the primary is not verified yet.','Контроллер осознанно остаётся на резерве: ваше правило возврата «удерживать» либо основной ещё не проверен.','Press “Return to primary” when you want traffic back.','Нажмите «Вернуться на основной», когда нужно вернуть трафик.'],
 ['DISABLED','state','Auto disabled','Auto выключен','Auto is switched off in the settings.','Auto выключен в настройках.','Nothing to do.','Делать ничего не нужно.'],
 ['EXPIRED','state','Test window ended','Окно теста закончилось','The time window of the current trial is over; Auto does not act outside it.','Окно времени текущего теста закончилось; вне его Auto не действует.','Start a new LAN trial if you want to continue.','Запустите новый LAN-тест, если хотите продолжить.'],
 ['SERVICE-STOPPED','state','Monitor service is not running','Служба мониторинга не работает','The page cannot find a running monitor on the router.','Страница не находит работающий мониторинг на роутере.','Press “Start monitoring” in the Monitoring block, or run homensai-vpn-emergency start over SSH.','Нажмите «Запустить мониторинг» в блоке «Мониторинг» или выполните homensai-vpn-emergency start по SSH.'],
 ['WAIT-CONFIRM','state','Waiting for confirmation','Ожидание подтверждения','Waiting for the computer to confirm the new route.','Ожидается подтверждение нового маршрута с компьютера.','See WAIT-CLIENT.','См. WAIT-CLIENT.'],
 // ---- reasons (why something happened; mostly not faults) ----
 ['CLIENT-CONFIRMED','switch','Your computer confirmed','Компьютер подтвердил','The LAN helper on your computer confirmed that DNS, HTTPS and the exit address are right after the switch.','LAN-помощник на вашем компьютере подтвердил, что DNS, HTTPS и внешний адрес после переключения верны.','Nothing to do.','Делать ничего не нужно.'],
 ['TRIAL-PASSED','switch','Trial passed','Тест пройден','The LAN trial worked: the switch was confirmed and the router returned to the primary.','LAN-тест удался: переключение подтверждено и роутер вернулся на основной.','Now you can turn Auto on.','Теперь можно включить Auto.'],
 ['TRIAL-ENDED','switch','Test window ended','Окно теста закончилось','The time window of the trial ended and the router returned to the primary.','Окно времени теста закончилось, роутер вернулся на основной.','Nothing to do.','Делать ничего не нужно.'],
 ['SOURCE-FAILED','switch','The primary failed','Основной отказал','The primary VPN failed the configured number of checks in a row.','Основной VPN не прошёл заданное число проверок подряд.','Check the primary VPN profile in GL.iNet.','Проверьте профиль основного VPN в GL.iNet.'],
 ['SOURCE-HEALTH-UNKNOWN','switch','Primary state unknown','Состояние основного неизвестно','There was not enough fresh data about the primary.','Не хватило свежих данных об основном.','Wait for the next checks; check the monitor lamp.','Дождитесь следующих проверок; посмотрите на лампу мониторинга.'],
 ['OPERATOR-TRIAL','switch','Started by you','Запущено вами','The switch was a trial that you started with the LAN helper.','Переключение было тестом, который вы запустили LAN-помощником.','Nothing to do.','Делать ничего не нужно.'],
 ['OPERATOR-HOLD-RESERVE','switch','Held by your rule','Удержание по вашему правилу','Your recovery rule says to stay on the reserve until you return manually.','Ваше правило восстановления говорит оставаться на резерве, пока вы не вернётесь вручную.','Press “Return to primary” when you want to go back.','Нажмите «Вернуться на основной», когда захотите вернуться.'],
 ['PRIMARY-STABLY-RECOVERED','switch','Primary recovered for good','Основной стабильно восстановился','The primary passed enough checks in a row and traffic returned to it.','Основной прошёл достаточно проверок подряд, и трафик вернулся на него.','Nothing to do.','Делать ничего не нужно.'],
 ['RESERVE-FAILED','switch','The reserve failed','Резерв отказал','The reserve VPN failed its checks while traffic was on it.','Резервный VPN не прошёл проверки, пока трафик шёл через него.','Check both VPN profiles in GL.iNet.','Проверьте оба VPN-профиля в GL.iNet.'],
 ['RESERVE-FAILED-PRIMARY-VERIFIED','switch','Reserve failed, primary is fine','Резерв отказал, основной исправен','The reserve failed and the primary was verified, so traffic returned to the primary.','Резерв отказал, основной проверен, поэтому трафик вернулся на основной.','Nothing to do.','Делать ничего не нужно.'],
 ['RESERVE-HEALTH-UNKNOWN','switch','Reserve state unknown','Состояние резерва неизвестно','The live check of the reserve gave no clear answer.','Живая проверка резерва не дала ясного ответа.','Wait; check the reserve in Channels and servers.','Подождите; посмотрите резерв в «Каналах и серверах».'],
 ['SOURCE-NOT-VERIFIED','switch','Primary not verified','Основной не проверен','The router stays on the reserve because the primary has not passed a fresh check.','Роутер остаётся на резерве, потому что основной не прошёл свежую проверку.','Check the primary VPN; then press “Return to primary”.','Проверьте основной VPN; затем нажмите «Вернуться на основной».'],
 ['SUPERVISOR-RECOVERY','switch','Recovery after a restart','Восстановление после перезапуска','The controller restarted in the middle of a switch and put the route back.','Контроллер перезапустился посреди переключения и вернул маршрут.','Nothing to do unless it repeats.','Делать ничего не нужно, если не повторяется.'],
 ['TRANSACTION-FAILED','switch','The switch failed','Переключение не удалось','Something went wrong during the switch; the router returned to the previous route.','Что-то пошло не так во время переключения; роутер вернулся на прежний маршрут.','Look at the code beside it for the cause.','Посмотрите на код рядом: там причина.'],
 ['FAILED-BEFORE-APPLY','switch','Failed before any change','Сбой до изменений','The switch failed before anything was changed on the router.','Переключение не удалось до каких-либо изменений на роутере.','Nothing was changed; look at the code beside it.','Ничего не менялось; посмотрите на код рядом.'],
 ['TIMEOUT-ELAPSED','switch','Time ran out','Время вышло','The allowed time for the step ended.','Отведённое на шаг время закончилось.','Repeat later; if it repeats, check the monitor.','Повторите позже; если повторяется, проверьте мониторинг.'],
 ['SELECTED-BY-CONTROLLER','switch','Chosen by the controller','Выбран контроллером','This server carries your traffic now.','Этот сервер сейчас пропускает ваш трафик.','Nothing to do.','Делать ничего не нужно.'],
 ['EDGE-NOT-CERTIFIED','switch','Works, switch not certified','Работает, переключение не подтверждено','The server works and could take over, but switching to it is not certified on this router yet.','Сервер работает и мог бы подхватить трафик, но переключение на него на этом роутере ещё не подтверждено.','Run the LAN trial. This is not a fault.','Пройдите LAN-тест. Это не неисправность.'],
 ['THREE-CONFIRMED-FAILURES','switch','Three failures in a row','Три сбоя подряд','The primary failed three checks in a row.','Основной не прошёл три проверки подряд.','Check the primary VPN.','Проверьте основной VPN.'],
 ['CONFIGURED-FAILURE-STREAK','switch','Failure streak reached','Достигнут порог сбоев','The primary failed as many checks in a row as your recovery rules require.','Основной не прошёл столько проверок подряд, сколько требуют ваши правила восстановления.','Check the primary VPN.','Проверьте основной VPN.'],
 ['RESTORE-PRIMARY','switch','Return to the primary','Возврат на основной','The controller decided to go back to the primary.','Контроллер решил вернуться на основной.','Nothing to do.','Делать ничего не нужно.'],
 ['SWITCH-RECOMMENDED','switch','A switch is recommended','Рекомендуется переключение','The forecast says a switch would be chosen now. The forecast changes nothing.','Прогноз говорит, что сейчас было бы выбрано переключение. Прогноз ничего не меняет.','Nothing to do.','Делать ничего не нужно.'],
 ['TARGET-INACTIVE','switch','Reserve not connected','Резерв не подключён','The reserve VPN is not connected in GL.iNet; Auto never connects it for you.','Резервный VPN не подключён в GL.iNet; Auto сам его не подключает.','Connect the reserve profile in the GL.iNet VPN Dashboard.','Подключите профиль резерва в VPN Dashboard GL.iNet.'],
 ['TARGET-NOT-READY','switch','Reserve not ready','Резерв не готов','The reserve has not passed enough checks in a row yet.','Резерв пока не прошёл достаточно проверок подряд.','Wait; check the reserve in Channels and servers.','Подождите; посмотрите резерв в «Каналах и серверах».'],
 ['PLAN-CONFIG','switch','Primary and reserve not chosen','Основной и резерв не выбраны','The forecast needs a primary and a different reserve.','Для прогноза нужны основной и другой, резервный VPN.','Settings → Setup → 1 · System setup.','«Настройки» → «Настройка» → 1 · Настройка системы.'],
 ['UPLINK-DOWN','switch','Provider line is down','Линия провайдера не работает','The router sees the line from your provider down; switching VPNs cannot help.','Роутер видит, что линия от провайдера отключена; переключение VPN не поможет.','Check the cable and the provider.','Проверьте кабель и провайдера.'],
 ['STOPPED-NO-HEALTHY-PATH','switch','No healthy path','Нет исправного пути','No VPN passed its checks, so the controller stopped.','Ни один VPN не прошёл проверки, поэтому контроллер остановился.','Check the VPN profiles in GL.iNet.','Проверьте VPN-профили в GL.iNet.'],
 ['GUARD-RETAINED','switch','Safety block kept','Защитная блокировка сохранена','The program kept its safety block (only VPN traffic allowed) because the return was not verified.','Программа сохранила защитную блокировку (разрешён только трафик через VPN), потому что возврат не подтверждён.','See Help → emergency return.','См. «Помощь» → аварийный возврат.'],
 ['WATCHDOG-DID-NOT-ARM','switch','Safety timer did not start','Страхующий таймер не запустился','The helper process that guarantees the return did not start in time, so the switch was not made.','Вспомогательный процесс, гарантирующий возврат, не запустился вовремя, поэтому переключение не выполнено.','Repeat later; if it repeats, restart the service.','Повторите позже; если повторяется, перезапустите службу.'],
 ['TRANSACTION-EXPIRED','switch','The switch ran out of time','Переключение не уложилось по времени','The time allowed for this switch had already ended.','Время, отведённое на это переключение, уже закончилось.','Start again.','Начните заново.'],
 // ---- diagnosis words ----
 ['DNS-FAILED','monitor','Name lookup fails','Не работает поиск адресов','The VPN is connected but looking up a name through it fails.','VPN подключён, но поиск имени через него не работает.','See DNS-001.','См. DNS-001.'],
 ['HTTPS-FAILED','monitor','Websites do not open','Сайты не открываются','The VPN is connected but opening a website through it fails.','VPN подключён, но открыть сайт через него не получается.','See VPN-003.','См. VPN-003.'],
 ['TUNNEL-DISCONNECTED','monitor','Tunnel not connected','Туннель не подключён','The VPN tunnel is not up.','VPN-туннель не поднят.','Turn the profile off and on in GL.iNet.','Выключите и включите профиль в GL.iNet.'],
 ['ROUTE-MISMATCH','monitor','Check did not go through the VPN','Проверка шла не через VPN','The router’s check did not travel through this VPN, so it proves nothing.','Проверка роутера шла не через этот VPN, поэтому ничего не доказывает.','See ROUTE-001.','См. ROUTE-001.'],
 ['PATH-UNVERIFIED','monitor','Check path unconfirmed','Путь проверки не подтверждён','The router has not yet confirmed which way its check went.','Роутер ещё не подтвердил, каким путём прошла проверка.','Wait for the next check.','Дождитесь следующей проверки.'],
 ['VPN-PROBE-HEALTHY','monitor','VPN works','VPN работает','DNS and HTTPS checks through this VPN passed.','Проверки DNS и HTTPS через этот VPN прошли.','Nothing to do.','Делать ничего не нужно.'],
 ['OBSERVATION-STALE','monitor','Measurements are old','Измерения устарели','The latest measurement is too old to decide anything.','Последнее измерение слишком старое, чтобы что-то решать.','Check that the monitor runs.','Проверьте, что мониторинг работает.'],
 ['OBSERVATION-UNKNOWN','monitor','Not enough measurements','Мало измерений','There are not enough measurements yet.','Измерений пока недостаточно.','Wait a few minutes.','Подождите несколько минут.'],
 ['LINK-UP','monitor','Link is up','Линия поднята','The uplink cable or line is up. It is not proof of internet.','Кабель или линия провайдера подняты. Это не доказательство интернета.','Nothing to do.','Делать ничего не нужно.'],
 ['CHECK-LIMIT','monitor','Check limit reached','Достигнут лимит проверок','To stay light the monitor checks only a limited number of VPNs per round; this one waits for its turn.','Чтобы не нагружать роутер, мониторинг проверяет за круг ограниченное число VPN; этот ждёт своей очереди.','Wait for the next round or raise the profile limit in Monitoring preferences.','Дождитесь следующего круга или увеличьте лимит профилей в «Параметрах мониторинга».'],
 // ---- safety guard and policy ----
 ['FOREIGN-GUARD-TABLE','switch','Foreign table with our name','Чужая таблица с нашим именем','A firewall table with the name of the program’s guard exists but is not the program’s. The program never touches it.','Существует таблица брандмауэра с именем защитного блока программы, но она не наша. Программа её не трогает.','Check the firewall rules over SSH (nft list tables); remove the foreign table only if you know where it came from.','Проверьте правила брандмауэра по SSH (nft list tables); удаляйте чужую таблицу, только если знаете, откуда она.'],
 ['GUARD-CHECK-FAILED','switch','Safety block rejected','Защитная блокировка отклонена','The firewall refused the program’s safety block when it was tested; nothing was applied.','Брандмауэр отклонил защитную блокировку при проверке; ничего не применено.','Check that nft works on the router; Help → emergency return.','Проверьте, что nft работает на роутере; «Помощь» → аварийный возврат.'],
 ['GUARD-INSTALL-FAILED','switch','Safety block not installed','Защитная блокировка не установлена','The program could not install its safety block, so it did not switch.','Программа не смогла установить защитную блокировку, поэтому не переключала.','Check nft; repeat later.','Проверьте nft; повторите позже.'],
 ['GUARD-QUERY-FAILED','switch','Safety block cannot be read','Защитная блокировка не читается','The program could not read the state of its own safety block.','Программа не смогла прочитать состояние своей защитной блокировки.','Check nft; see Help → emergency return.','Проверьте nft; см. «Помощь» → аварийный возврат.'],
 ['POLICY-DUPLICATE-IDENTITY','switch','Two identical VPN rules','Два одинаковых VPN-правила','Two rules of the router look identical, so they cannot be told apart safely.','Два правила роутера выглядят одинаково, поэтому надёжно их различить нельзя.','Remove the duplicate rule in GL.iNet.','Удалите дубль правила в GL.iNet.'],
 ['POLICY-GENERATION-CHANGED','switch','Rules changed meanwhile','Правила изменились','The router’s VPN rules changed after the switch was prepared, so it was cancelled.','Правила VPN на роутере изменились после подготовки переключения, поэтому оно отменено.','Do not edit the VPN rules while Auto works.','Не меняйте VPN-правила, пока Auto работает.'],
 ['POLICY-IDENTITY-CHANGED','switch','Rule identity changed','Правило изменилось','A rule that was part of the switch changed or disappeared.','Правило, участвовавшее в переключении, изменилось или исчезло.','Do not edit the VPN rules while Auto works.','Не меняйте VPN-правила, пока Auto работает.'],
 ['POLICY-REORDER-UNVERIFIED','switch','New order not confirmed','Новый порядок не подтверждён','After reordering, the rules were not in the expected order; the router went back.','После перестановки правила оказались не в ожидаемом порядке; роутер вернулся назад.','Repeat later.','Повторите позже.'],
 ['SOURCE-ORDER-MISMATCH','switch','Rule order is not as expected','Порядок правил не тот','The primary and reserve rules are not in the order the program expects.','Правила основного и резервного стоят не в том порядке, который ожидает программа.','Settings → Setup → check the primary and reserve.','«Настройки» → «Настройка» → проверьте основной и резерв.'],
 ['EXIT-CHANGED','switch','The exit address changed','Внешний адрес изменился','The address the internet sees changed between two checks of the same VPN.','Адрес, который видит интернет, изменился между двумя проверками одного VPN.','Repeat the trial; a provider that rotates addresses can cause this.','Повторите тест; такое бывает у провайдера с ротацией адресов.'],
 ['EXIT-IP-NOT-GLOBAL','switch','Exit address is private','Внешний адрес не публичный','The exit address answered by the check is a private one, so the check proves nothing.','Адрес, ответивший на проверку, частный, поэтому проверка ничего не доказывает.','Check that the VPN really reaches the internet.','Проверьте, что VPN действительно выходит в интернет.'],
 ['JOURNAL-ORDER-INVALID','switch','Journal order invalid','Порядок в журнале неверен','The saved order in the switch journal is inconsistent.','Сохранённый порядок в журнале переключения противоречив.','Archive the journal with homensai-vpn-emergency close-journal after checking the rules.','Заархивируйте журнал командой homensai-vpn-emergency close-journal, проверив правила.'],
 ['JOURNAL-SECTION-INVALID','switch','Journal names an invalid rule','Журнал называет неверное правило','The journal names a rule that is not valid.','Журнал называет правило, которое недопустимо.','Same as JOURNAL-ORDER-INVALID.','То же, что JOURNAL-ORDER-INVALID.'],
 ['DEADLINE-TIMEZONE-REQUIRED','switch','Deadline needs a time zone','Для срока нужен часовой пояс','The deadline of the test window was written without a time zone.','Срок окна теста записан без часового пояса.','Start a new LAN trial.','Запустите новый LAN-тест.'],
 ['INVALID-ACCELERATION-REQUEST','switch','Invalid request','Неверный запрос','The request to prepare the router had a wrong form.','Запрос на подготовку роутера имел неверный вид.','Use the page button, not a manual command.','Используйте кнопку на странице, а не ручную команду.'],
 ['ACCELERATION-PREPARE-ATTEMPT-LIMIT','switch','Too many preparation attempts','Слишком много попыток подготовки','The preparation of the router (hardware acceleration off) failed three times.','Подготовка роутера (отключение аппаратного ускорения) не удалась трижды.','Disable acceleration in GL.iNet by hand; see Help.','Отключите ускорение в GL.iNet вручную; см. «Помощь».'],
 ['ACCELERATION-PREPARE-DURING-TRANSACTION','switch','Preparation during a switch','Подготовка во время переключения','The router preparation was requested while a switch was running; refused.','Подготовка роутера запрошена во время переключения; отказано.','Wait until the switch ends.','Дождитесь окончания переключения.'],
 ['HNAT-DISABLE-UNVERIFIED','switch','Hardware acceleration not confirmed off','Аппаратное ускорение не подтверждено как выключенное','After the attempt, the hardware acceleration (HNAT) is still not proven off.','После попытки аппаратное ускорение (HNAT) всё ещё не подтверждено как выключенное.','Turn acceleration off in GL.iNet and repeat.','Выключите ускорение в GL.iNet и повторите.'],
 ['SFE-DISABLE-UNVERIFIED','switch','Software acceleration not confirmed off','Программное ускорение не подтверждено как выключенное','The software acceleration module is still loaded.','Модуль программного ускорения всё ещё загружен.','Turn acceleration off in GL.iNet and repeat.','Выключите ускорение в GL.iNet и повторите.'],
 ['UNEXPECTED-DEBUGFS-PATH','switch','Unexpected system path','Неожиданный системный путь','A system path that should be a normal folder is a link; the program refuses to use it.','Системный путь, который должен быть обычной папкой, оказался ссылкой; программа отказывается его использовать.','Contact support with the code; nothing was changed.','Обратитесь в поддержку с кодом; ничего не менялось.'],
 ['UNEXPECTED-HNAT-PATH','switch','Unexpected system path','Неожиданный системный путь','Same as UNEXPECTED-DEBUGFS-PATH for the acceleration switch file.','То же, что UNEXPECTED-DEBUGFS-PATH для файла переключателя ускорения.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['UNSAFE-FIREWALL-SECTION','switch','Unsafe firewall section name','Небезопасное имя секции брандмауэра','A firewall section has a name the program does not dare to touch.','У секции брандмауэра имя, которое программа не решается трогать.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['UNSAFE-GUARD-DEVICE','switch','Unsafe interface name','Небезопасное имя интерфейса','A network interface name has odd characters; the program refuses to put it into a firewall rule.','В имени сетевого интерфейса странные символы; программа отказывается вносить его в правило брандмауэра.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['UNSAFE-SECTION','switch','Unsafe rule name','Небезопасное имя правила','A VPN rule has a name the program refuses to use.','У VPN-правила имя, которое программа отказывается использовать.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 // ---- failure test ----
 ['FAULT-ACTIVE','switch','Failure test is running','Тест сбоя выполняется','The deliberate traffic block of the failure test is on.','Преднамеренная блокировка трафика теста сбоя включена.','Wait for its end or press “Cancel fault now”.','Дождитесь окончания или нажмите «Отменить сбой сейчас».'],
 ['FAULT-ALREADY-ACTIVE','switch','Failure test already runs','Тест сбоя уже идёт','Only one failure test can run at a time.','Одновременно может идти только один тест сбоя.','Wait or cancel the running one.','Дождитесь или отмените идущий.'],
 ['FAULT-CANCELLED','switch','Failure test cancelled','Тест сбоя отменён','You cancelled the failure test and the block was removed.','Вы отменили тест сбоя, блокировка снята.','Nothing to do.','Делать ничего не нужно.'],
 ['FAULT-CLEANED','switch','Failure test cleaned up','Тест сбоя убран','The failure test ended and its block was removed.','Тест сбоя закончился, его блокировка снята.','Nothing to do.','Делать ничего не нужно.'],
 ['FAULT-NOT-ACTIVE','switch','No failure test is running','Тест сбоя не идёт','There is nothing to cancel.','Отменять нечего.','Nothing to do.','Делать ничего не нужно.'],
 ['FAULT-CERTIFIED-AUTO-REQUIRED','switch','Auto must be on and certified','Нужен включённый и подтверждённый Auto','The failure test works only while Auto watches the primary after a passed LAN trial.','Тест сбоя работает, только пока Auto следит за основным после пройденного LAN-теста.','Pass the LAN trial and turn Auto on.','Пройдите LAN-тест и включите Auto.','The panel says which of these is missing and links to where to fix it.','Панель пишет, чего именно не хватает, и даёт ссылку, где это исправить.'],
 ['FAULT-NATIVE-PREREQUISITES','switch','Router checks not passed','Проверки роутера не пройдены','Some of the router checks listed on the Overview are not passed.','Часть проверок роутера, перечисленных на «Обзоре», не пройдена.','Fix the listed items (Overview → Before you can start Auto).','Исправьте перечисленное («Обзор» → «Что нужно перед запуском Auto»).'],
 ['FAULT-SESSION-CONSENT-REQUIRED','switch','Reconnection not allowed','Переподключение не разрешено','You have not allowed a short reconnection of calls and sessions.','Вы не разрешили короткое переподключение звонков и сессий.','Settings → Setup → 1 · System setup: tick the permission.','«Настройки» → «Настройка» → 1 · Настройка системы: поставьте разрешение.'],
 ['FAULT-WINDOW-TOO-SHORT','switch','Test window too short','Окно теста слишком короткое','The remaining time of the trial window is shorter than the failure test plus its return.','Остаток окна теста короче, чем тест сбоя вместе с возвратом.','Start a new LAN trial or choose a shorter failure.','Запустите новый LAN-тест или выберите более короткий сбой.'],
 ['FAULT-NOT-CURRENT-SOURCE','switch','Not the current primary','Это не текущий основной','The failure test can only break the VPN that is currently the primary.','Тест сбоя может ломать только VPN, который сейчас основной.','Choose the current primary.','Выберите текущий основной.'],
 ['FAULT-HEALTHY-RESERVE-REQUIRED','switch','Reserve must be healthy','Нужен исправный резерв','The test needs both the primary and the reserve to work right now.','Для теста нужно, чтобы и основной, и резерв сейчас работали.','Check both in Channels and servers.','Проверьте оба в «Каналах и серверах».'],
 ['FAULT-WOULD-REMOVE-RESERVE','switch','The test would also break the reserve','Тест сломал бы и резерв','The chosen scope (the whole channel group) contains the reserve too.','Выбранная область (вся группа канала) содержит и резерв.','Choose “Current primary server”.','Выберите «Текущий основной сервер».'],
 ['FAULT-PATH-UNVERIFIED','switch','Path of the VPN not confirmed','Путь VPN не подтверждён','The program could not confirm which network device belongs to the VPN, so it will not block anything.','Программа не смогла подтвердить, какое сетевое устройство принадлежит VPN, поэтому ничего не блокирует.','Wait for the next check and repeat.','Дождитесь следующей проверки и повторите.'],
 ['FAULT-WATCHDOG-NOT-READY','switch','Safety timer not ready','Страхующий таймер не готов','The helper that removes the block by itself did not start; the test was not started.','Помощник, который сам снимает блокировку, не запустился; тест не начат.','Repeat later.','Повторите позже.'],
 ['FAULT-UNSAFE-SCOPE','switch','Unsafe scope','Небезопасная область','The requested scope is not allowed.','Запрошенная область недопустима.','Use the page controls.','Пользуйтесь элементами страницы.'],
 ['FAULT-FOREIGN-TABLE','switch','Foreign firewall table','Чужая таблица брандмауэра','A firewall table with the test’s name exists but is not the program’s.','Существует таблица брандмауэра с именем теста, но она не наша.','Check nft over SSH.','Проверьте nft по SSH.'],
 ['FAULT-TIMEOUT-RULE-FAILED','switch','Automatic end could not be set','Автоматическое окончание не задано','The firewall could not set the timer that removes the block by itself; nothing was blocked.','Брандмауэр не смог задать таймер, который снимает блокировку сам; ничего не блокировалось.','Repeat later.','Повторите позже.'],
 ['FAULT-APPLY-UNCONFIRMED','switch','Block not confirmed','Блокировка не подтверждена','It is not confirmed that the test block was applied; it was removed to be safe.','Не подтверждено, что блокировка теста применена; для безопасности она снята.','Repeat later.','Повторите позже.'],
 ['FAULT-CLEANUP-UNCONFIRMED','switch','Removal not confirmed','Снятие не подтверждено','It is not confirmed that the test block was removed. It still ends by its own kernel timer.','Не подтверждено, что блокировка теста снята. Она всё равно закончится по таймеру ядра.','Wait up to 3 minutes; then check the internet; Help → emergency return.','Подождите до 3 минут; затем проверьте интернет; «Помощь» → аварийный возврат.'],
 ['FAULT-STATE-UNVERIFIED','switch','Test state unverified','Состояние теста не подтверждено','The saved state of the failure test cannot be trusted.','Сохранённому состоянию теста сбоя нельзя доверять.','Press “Cancel fault now”.','Нажмите «Отменить сбой сейчас».'],
 ['FAULT-HISTORY-CORRUPT','switch','Test history damaged','История тестов повреждена','The record of earlier failure tests cannot be read.','Запись прошлых тестов сбоя не читается.','Nothing to do; new tests still work.','Делать ничего не нужно; новые тесты работают.'],
 ['FAULT-WORKER-INVALID','switch','Helper process invalid','Вспомогательный процесс недействителен','The helper process of the test did not identify itself correctly.','Вспомогательный процесс теста неверно представился.','Cancel the test and repeat.','Отмените тест и повторите.'],
 ['FAULT-WORKER-STALE','switch','Helper process stale','Вспомогательный процесс устарел','The helper process of the test is old; the test was ended.','Вспомогательный процесс теста устарел; тест завершён.','Repeat.','Повторите.'],
 // ---- Telegram, setup, priority, recovery ----
 ['TELEGRAM-FORMAT-FAILED','telegram','Report could not be formed','Отчёт не сформирован','The program could not build the report text.','Программа не смогла собрать текст отчёта.','Repeat later; if it repeats, tell support.','Повторите позже; если повторяется, сообщите в поддержку.'],
 ['TELEGRAM-REPORT-UNAVAILABLE','telegram','Report data not available','Данные для отчёта недоступны','The monitor has no data for the report yet.','У мониторинга пока нет данных для отчёта.','Wait a few minutes after the monitor starts.','Подождите несколько минут после запуска мониторинга.'],
 ['TELEGRAM-REQUEST-REJECTED','telegram','Telegram rejected the request','Telegram отклонил запрос','Telegram answered that it will not take the message (wrong token, wrong chat or the bot is blocked).','Telegram ответил, что не принимает сообщение (неверный токен, неверный чат или бот заблокирован).','Check the token and the chat ID in the Telegram wizard; press Start in the bot.','Проверьте токен и Chat ID в мастере Telegram; нажмите Start в боте.','401 or “Unauthorized” → the token is wrong. 400 or “chat not found” → the chat ID is wrong or you did not press Start.','401 или «Unauthorized» → токен неверный. 400 или «chat not found» → неверный Chat ID либо вы не нажали Start.'],
 ['TELEGRAM-RETRY','telegram','Will retry','Повторю отправку','The message could not be sent now; the program tries again later.','Сообщение сейчас не отправилось; программа попробует позже.','Check that the router has internet.','Проверьте, что у роутера есть интернет.'],
 ['TELEGRAM-SCHEDULE','telegram','Invalid schedule','Неверное расписание','The report schedule has a wrong value.','В расписании отчётов неверное значение.','Open the Telegram wizard and choose the schedule again.','Откройте мастер Telegram и выберите расписание заново.'],
 ['TELEGRAM-SETUP-FIELDS','telegram','Wrong fields','Неверные поля','The Telegram form had unexpected fields.','В форме Telegram оказались неожиданные поля.','Reload the page and fill the wizard again.','Обновите страницу и заполните мастер заново.'],
 ['TELEGRAM-STATE-RECOVERED','telegram','Report state recovered','Состояние отчётов восстановлено','The saved report state was damaged and was rebuilt; one report may repeat or be skipped.','Сохранённое состояние отчётов было повреждено и восстановлено; один отчёт может повториться или пропуститься.','Nothing to do.','Делать ничего не нужно.'],
 ['TELEGRAM-STATE-WRITE-FAILED','telegram','Report state not saved','Состояние отчётов не сохранено','The program could not save the time of the last report; reports may repeat.','Программа не смогла сохранить время последнего отчёта; отчёты могут повторяться.','Check the free space (see “Storage”).','Проверьте свободное место (см. «Хранилище»).'],
 ['TELEGRAM-TEST-RATE-LIMIT','telegram','Test message too often','Тестовое сообщение слишком часто','A test message can be sent only once in a short time.','Тестовое сообщение можно отправлять не чаще, чем раз в короткое время.','Wait a minute.','Подождите минуту.'],
 ['SETUP-FIELDS','setup','Wrong fields in the form','Неверные поля формы','The setup form had unexpected fields.','В форме настройки оказались неожиданные поля.','Reload the page and use the wizard again.','Обновите страницу и снова пользуйтесь мастером.'],
 ['SETUP-KIND','setup','Unknown setup kind','Неизвестный вид настройки','The request named a setup that does not exist.','Запрос назвал несуществующую настройку.','Reload the page.','Обновите страницу.'],
 ['SETUP-NAME','setup','Invalid name','Неверное название','A name is empty, longer than 64 characters or has control characters.','Название пустое, длиннее 64 символов или содержит управляющие символы.','Use a short plain name.','Используйте короткое простое название.'],
 ['SETUP-SERVER','setup','Invalid server row','Неверная строка сервера','A server row of the form is incomplete.','Строка сервера в форме неполная.','Fill name, group, priority and the Monitor box.','Заполните название, группу, приоритет и галочку «Наблюдать».'],
 ['SETUP-DELTA-UNVERIFIED','setup','Unsaved changes unverifiable','Несохранённые изменения не проверить','The program could not check whether the router has other unsaved changes of its own settings.','Программа не смогла проверить, есть ли на роутере другие несохранённые изменения её настроек.','Reload the page and try again.','Обновите страницу и попробуйте снова.'],
 ['SETUP-CHECK-OK','setup','Settings writer works','Запись настроек работает','The installed writer passed its isolated self-check.','Установленная запись настроек прошла изолированную самопроверку.','Nothing to do.','Делать ничего не нужно.'],
 ['SETUP-CHECK-FAILED','setup','Settings writer self-check failed','Самопроверка записи настроек не прошла','Saving is blocked because the writer failed its self-check (often after an upgrade).','Сохранение заблокировано, потому что запись настроек не прошла самопроверку (часто после обновления).','Sign out of LuCI and in again, then reload with Ctrl+F5.','Выйдите из LuCI и войдите снова, затем обновите Ctrl+F5.'],
 ['TERMS-VERSION','setup','Terms version mismatch','Версия условий не совпадает','The page sent a different version of the terms than the router knows.','Страница прислала другую версию условий, чем знает роутер.','Reload with Ctrl+F5 and accept again.','Обновите Ctrl+F5 и примите условия заново.'],
 ['MONITOR-PREFERENCES-FIELDS','setup','Wrong fields','Неверные поля','The monitoring preferences form had unexpected fields.','В форме параметров мониторинга оказались неожиданные поля.','Reload the page.','Обновите страницу.'],
 ['PRIORITY-SAVED','setup','Priorities saved','Приоритеты сохранены','The new order of the servers was saved. No route changed.','Новый порядок серверов сохранён. Маршрут не менялся.','Nothing to do.','Делать ничего не нужно.'],
 ['PRIORITY-SAVE-FAILED','setup','Priorities not saved','Приоритеты не сохранены','The router refused the new order.','Роутер отказал в новом порядке.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-STALE-REVIEW','setup','The review is outdated','Просмотр устарел','The list changed after you reviewed it; nothing was saved.','Список изменился после вашего просмотра; ничего не сохранено.','Review the order again and save.','Просмотрите порядок заново и сохраните.'],
 ['PRIORITY-FIELDS','setup','Wrong fields','Неверные поля','The priorities form had unexpected fields.','В форме приоритетов оказались неожиданные поля.','Reload the page.','Обновите страницу.'],
 ['PRIORITY-INVALID-SELECTION','setup','Invalid selection','Неверный выбор','The chosen servers cannot be ordered this way.','Выбранные серверы нельзя упорядочить так.','Choose the eligible servers again.','Выберите подходящие серверы заново.'],
 ['PRIORITY-PROFILE-INELIGIBLE','setup','Server not eligible','Сервер не подходит','A chosen server is not connected or not monitored.','Выбранный сервер не подключён или не наблюдается.','Connect it or turn on “Monitor” for it.','Подключите его или включите ему «Наблюдать».'],
 ['RECOVERY-FIELDS','setup','Wrong fields','Неверные поля','The recovery rules form had unexpected fields.','В форме правил восстановления оказались неожиданные поля.','Reload the page.','Обновите страницу.'],
 ['RECOVERY-RANGE','setup','Value out of range','Значение вне диапазона','A number in the recovery rules is outside its allowed range.','Число в правилах восстановления вне допустимого диапазона.','Use the values the wizard offers.','Используйте значения, которые предлагает мастер.'],
 ['RECOVERY-REQUIRED','setup','Recovery rules required','Нужны правила восстановления','The recovery rules were never saved.','Правила восстановления ни разу не сохранялись.','Settings → Advanced → Recovery rules.','«Настройки» → «Расширенные» → «Правила восстановления».'],
 ['RECOVERY-RETURN-POLICY','setup','Invalid return rule','Неверное правило возврата','The return rule has an unknown value.','У правила возврата неизвестное значение.','Choose one of the offered rules.','Выберите одно из предложенных правил.'],
 ['CONFIG-STOP-AUTO-FIRST','setup','Stop Auto first','Сначала остановите Auto','This setting cannot change while Auto works.','Эту настройку нельзя менять, пока Auto работает.','Stop Auto on the Overview, wait for the return, then change it.','Остановите Auto на «Обзоре», дождитесь возврата, затем меняйте.'],
 ['CONFIG-RECOVERY-UNVERIFIED','setup','Configuration cannot be confirmed','Конфигурацию не подтвердить','The program could not confirm the configuration, so it refuses to change it.','Программа не смогла подтвердить конфигурацию, поэтому отказывается её менять.','Reload and try again.','Обновите и попробуйте снова.'],
 ['CONFIG-STORAGE-FREE','data','Not enough free space','Мало свободного места','The router has too little free space to save settings safely.','На роутере слишком мало места, чтобы безопасно сохранить настройки.','Free some space; see Help → Storage.','Освободите место; см. «Помощь» → «Хранилище».'],
 // ---- lifecycle and service ----
 ['LIFECYCLE-STOP-AUTO-FIRST','service','Stop Auto first','Сначала остановите Auto','An upgrade or stop of the service needs Auto to be off and the original route restored.','Для обновления или остановки службы нужно, чтобы Auto был выключен и исходный маршрут восстановлен.','Press Stop in the Auto card and wait for the confirmation.','Нажмите «Стоп» в блоке Auto и дождитесь подтверждения.'],
 ['MONITOR-STOP-AUTO-FIRST','service','Stop Auto first','Сначала остановите Auto','Monitoring cannot be turned off while Auto works.','Мониторинг нельзя выключить, пока Auto работает.','Stop Auto first.','Сначала остановите Auto.'],
 ['MONITOR-JOURNAL-UNVERIFIED','service','Journal unverified','Журнал не проверен','The switch journal cannot be read, so monitoring is not turned off.','Журнал переключения не читается, поэтому мониторинг не выключается.','See JOURNAL-INTEGRITY-FAILED.','См. JOURNAL-INTEGRITY-FAILED.'],
 ['MONITOR-SERVICE-UNCONFIRMED','service','Service answer not confirmed','Ответ службы не подтверждён','The setting was saved but the service did not confirm that it started or stopped.','Настройка сохранена, но служба не подтвердила запуск или остановку.','Reload the page and look at the Monitoring lamp.','Обновите страницу и посмотрите на лампу мониторинга.'],
 // ---- storage, history, rpc, scan ----
 ['STORAGE-001','data','Router storage problem','Проблема с хранилищем роутера','The program could not save its data (no space or the storage is read-only).','Программа не смогла сохранить свои данные (нет места или хранилище только для чтения).','Free space on the router; see Help → Storage.','Освободите место на роутере; см. «Помощь» → «Хранилище».'],
 ['STORAGE-RECOVERED','data','Storage recovered','Хранилище восстановлено','The damaged data was restored from the last good copy.','Повреждённые данные восстановлены из последней исправной копии.','Nothing to do; the newest minutes may be missing.','Делать ничего не нужно; последние минуты могут отсутствовать.'],
 ['SCAN-MEASUREMENT-FAILED','speed','Check request failed','Запрос проверки не удался','The “Check the VPNs now” request got no measurement.','Запрос «Проверить VPN сейчас» не получил измерения.','Check the Monitoring lamp and repeat.','Посмотрите на лампу мониторинга и повторите.'],
 ['SCAN-SNAPSHOT-MISMATCH','speed','Measurement does not match','Измерение не совпало','The measurement does not belong to this request.','Измерение не относится к этому запросу.','Press the check button again.','Нажмите кнопку проверки ещё раз.'],
 ['SCAN-STORAGE','speed','Request not saved','Запрос не сохранён','The router could not save the check request.','Роутер не смог сохранить запрос проверки.','Free space; repeat.','Освободите место; повторите.'],
 ['RPC-DUPLICATE-FIELD','service','Duplicate field in a request','Повтор поля в запросе','A request to the router named the same field twice; it was refused.','Запрос к роутеру дважды назвал одно поле; он отклонён.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-INPUT-COMPLEXITY','service','Request too complex','Запрос слишком сложный','The request was too big or too deeply nested.','Запрос был слишком большим или слишком вложенным.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-INPUT-DEPTH','service','Request too deep','Запрос слишком вложенный','The request nests too deeply.','Запрос вложен слишком глубоко.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-INPUT-OBJECT','service','Request has a wrong form','Запрос неверного вида','The request was not in the expected form.','Запрос был не в ожидаемом виде.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-NONFINITE-NUMBER','service','Invalid number','Неверное число','The request contained a number that is not valid.','Запрос содержал недопустимое число.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 // ---- test data of the offline preview ----
 ['OFFLINE-FIXTURE','data','Test data of the offline preview','Тестовые данные офлайн-просмотра','This code exists only in the offline preview used for development. It never appears on a real router.','Этот код есть только в офлайн-просмотре для разработки. На настоящем роутере его не бывает.','Nothing to do.','Делать ничего не нужно.'],
 // ---- notices of the page ----
 ['AUTO-STOP-QUEUED','switch','Stop was queued','Остановка поставлена в очередь','The router accepted the Stop request.','Роутер принял запрос остановки.','Wait for the lamp to change.','Дождитесь, пока лампа изменится.'],
 ['RETURN-REFUSED','switch','Return refused','Возврат отклонён','The router refused the “Return to primary” request (usually because the primary is not healthy yet).','Роутер отклонил запрос «Вернуться на основной» (обычно потому, что основной ещё не исправен).','Check the primary in Channels and servers and press again.','Проверьте основной в «Каналах и серверах» и нажмите снова.'],
 ['RECOVERY-SAVED','setup','Recovery rules saved','Правила восстановления сохранены','Saved.','Сохранено.','Nothing to do.','Делать ничего не нужно.'],
 ['RECOVERY-SAVE-FAILED','setup','Recovery rules not saved','Правила восстановления не сохранены','The router refused to save them.','Роутер отказал в сохранении.','Reload and try again.','Обновите и попробуйте снова.'],
 ['RECOVERY-SAVE-UNCONFIRMED','setup','Save not confirmed','Сохранение не подтверждено','The router did not answer the save in time; it may or may not be saved.','Роутер не ответил на сохранение вовремя; оно могло записаться, а могло и нет.','Reload the page and look at the setting.','Обновите страницу и посмотрите настройку.'],
 ['SPEED-CONFIG-SAVED','speed','Speed settings saved','Настройки скорости сохранены','Saved.','Сохранено.','Nothing to do.','Делать ничего не нужно.'],
 ['SPEED-CONFIG-FAILED','speed','Speed settings not saved','Настройки скорости не сохранены','The router refused to save them.','Роутер отказал в сохранении.','Reload and try again.','Обновите и попробуйте снова.'],
 ['SPEED-QUEUED','speed','Speed test queued','Тест скорости поставлен в очередь','The router accepted the speed test; it starts within seconds.','Роутер принял тест скорости; он начнётся через секунды.','Wait for the result in the table.','Дождитесь результата в таблице.'],
 ['SPEED-START-FAILED','speed','Speed test did not start','Тест скорости не запустился','The router did not accept the speed test.','Роутер не принял тест скорости.','Look at the code beside it for the reason.','Посмотрите на код рядом: там причина.'],
 ['SPEED-CANCEL-QUEUED','speed','Cancel queued','Отмена поставлена в очередь','The router accepted the request to cancel the speed test.','Роутер принял запрос отменить тест скорости.','Nothing to do.','Делать ничего не нужно.'],
 ['SCAN-ACK-UNCONFIRMED','speed','Check request not confirmed','Запрос проверки не подтверждён','The router did not clearly confirm the check request.','Роутер не подтвердил запрос проверки ясно.','Make sure the monitor runs and press again.','Убедитесь, что мониторинг работает, и нажмите снова.'],
 ['SCAN-SNAPSHOT-UNCONFIRMED','speed','Result not confirmed','Результат не подтверждён','The measurement after the request could not be confirmed.','Измерение после запроса не удалось подтвердить.','Press the check button again.','Нажмите кнопку проверки ещё раз.'],
 ['MONITOR-PREFERENCES-SAVED','setup','Monitoring preferences saved','Параметры мониторинга сохранены','Saved.','Сохранено.','Nothing to do.','Делать ничего не нужно.'],
 ['MONITOR-PREFERENCES-FAILED','setup','Monitoring preferences not saved','Параметры мониторинга не сохранены','The router refused to save them.','Роутер отказал в сохранении.','Reload and try again.','Обновите и попробуйте снова.'],
 ['MONITOR-PREFERENCES-UNCONFIRMED','setup','Save not confirmed','Сохранение не подтверждено','The router did not answer the save in time.','Роутер не ответил на сохранение вовремя.','Reload the page and look at the setting.','Обновите страницу и посмотрите настройку.'],
 ['MONITOR-UNKNOWN','service','Monitor answer unknown','Ответ мониторинга неизвестен','The monitor service answered without a clear code.','Служба мониторинга ответила без ясного кода.','Reload and look at the Monitoring lamp.','Обновите и посмотрите на лампу мониторинга.'],
 ['PRIORITY-PREVIEW-FAILED','setup','Preview failed','Просмотр не удался','The router could not prepare the preview of the new order.','Роутер не смог подготовить просмотр нового порядка.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-PREVIEW-UNCONFIRMED','setup','Preview not confirmed','Просмотр не подтверждён','No clear answer to the preview request.','Нет ясного ответа на запрос просмотра.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-RPC-UNCONFIRMED','setup','Answer not confirmed','Ответ не подтверждён','No clear answer from the router.','Нет ясного ответа от роутера.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-SELECT-ELIGIBLE-SERVERS','setup','Choose servers first','Сначала выберите серверы','Choose at least the servers that can be ordered.','Выберите хотя бы серверы, которые можно упорядочить.','Tick the servers you want to order.','Отметьте серверы, которые нужно упорядочить.'],
 ['PRIORITY-UNKNOWN','setup','Priority answer unknown','Ответ по приоритетам неизвестен','The router answered without a clear code.','Роутер ответил без ясного кода.','Reload and try again.','Обновите и попробуйте снова.'],
 ['RECOVERY-PERIOD','setup','Invalid period','Неверный период','A period in the recovery rules is not valid.','Период в правилах восстановления недопустим.','Use the values the wizard offers.','Используйте значения мастера.'],
 ['RPC-INVENTORY-INVALID','service','Router list unreadable','Список роутера нечитаем','The list of VPN profiles from the router had an unexpected form.','Список VPN-профилей от роутера имел неожиданный вид.','Reload with Ctrl+F5; if it stays, sign out of LuCI and in again.','Обновите Ctrl+F5; если не помогло, выйдите из LuCI и войдите снова.'],
 ['RPC-INVENTORY-UNAVAILABLE','service','Router list unavailable','Список роутера недоступен','The page could not get the list of VPN profiles; settings are not shown and nothing is saved.','Страница не получила список VPN-профилей; настройки не показываются и ничего не сохраняется.','Wait a minute and reload; check that you are signed in to LuCI.','Подождите минуту и обновите; проверьте, что вы вошли в LuCI.'],
 ['TELEGRAM-FORGET-UNCONFIRMED','telegram','Token removal not confirmed','Удаление токена не подтверждено','The router did not confirm that the stored bot token was deleted.','Роутер не подтвердил, что сохранённый токен бота удалён.','Reload and check the Telegram status.','Обновите и проверьте состояние Telegram.'],
 ['TERMS-SAVE-FAILED','setup','Terms not saved','Условия не сохранены','The acceptance of the terms could not be saved.','Принятие условий не удалось сохранить.','Reload and accept again.','Обновите и примите снова.'],
 ['TERMS-SAVE-UNCONFIRMED','setup','Acceptance not confirmed','Принятие не подтверждено','The router did not confirm the acceptance in time.','Роутер не подтвердил принятие вовремя.','Reload and check.','Обновите и проверьте.'],
 ['CAUSE-UNKNOWN','data','Cause not known','Причина неизвестна','The program saw a failure but has no evidence for its cause. It never guesses.','Программа увидела сбой, но у неё нет доказательств причины. Она не гадает.','Look at the other codes beside it.','Посмотрите на другие коды рядом.'],
 ['UNKNOWN-FUTURE-TIMESTAMP','data','Time in the future','Время из будущего','A record has a time later than now (the clock of the router was wrong at that moment).','У записи время позже текущего (часы роутера в тот момент были неверны).','Check the router clock (Help → Dates are wrong).','Проверьте часы роутера («Помощь» → «Неверные даты»).'],
 ['EXPORT-KIND','data','Unknown export','Неизвестный экспорт','The page asked to export a table that does not exist.','Страница запросила экспорт несуществующей таблицы.','Reload the page.','Обновите страницу.'],
 ['DEPENDENCY-IP','service','Program “ip” missing','Нет программы «ip»','The router lacks the “ip” tool the monitor needs.','На роутере нет инструмента «ip», нужного мониторингу.','Install the missing package (opkg install ip-full).','Установите недостающий пакет (opkg install ip-full).'],
 ['DEPENDENCY-LUA','service','Lua missing','Нет Lua','The router lacks Lua.','На роутере нет Lua.','Install lua.','Установите lua.'],
 ['DEPENDENCY-UBUS','service','ubus missing','Нет ubus','The router lacks ubus.','На роутере нет ubus.','Install ubus.','Установите ubus.'],
 ['DEPENDENCY-UCI','service','UCI missing','Нет UCI','The router lacks UCI (libuci-lua).','На роутере нет UCI (libuci-lua).','Install libuci-lua.','Установите libuci-lua.'],
 ['SPEED-COMPLETE','speed','Speed test finished','Тест скорости завершён','The speed test of a server finished.','Тест скорости сервера завершён.','Nothing to do.','Делать ничего не нужно.'],
 ['SPEED-NOT-RUNNING','speed','No speed test is running','Тест скорости не идёт','There is nothing to cancel.','Отменять нечего.','Nothing to do.','Делать ничего не нужно.'],
 ['SPEED-NO-SAMPLE','speed','No measurement','Нет измерения','The speed test got no usable measurement.','Тест скорости не получил пригодного измерения.','Repeat later; check the VPN.','Повторите позже; проверьте VPN.'],
 ['SPEED-CPU-BUSY','speed','Router is busy','Роутер занят','The router’s processor is busy, so the test is postponed to avoid disturbing the traffic.','Процессор роутера занят, поэтому тест отложен, чтобы не мешать трафику.','Try later.','Попробуйте позже.'],
 ['SPEED-TRAFFIC-UNKNOWN','speed','Traffic unknown','Трафик неизвестен','The program cannot tell whether the VPN is busy, so it does not test it.','Программа не может определить, занят ли VPN, поэтому не тестирует его.','Wait for new measurements.','Дождитесь новых измерений.'],
 ['SPEED-SWITCH-IN-PROGRESS','speed','A switch is running','Идёт переключение','No speed test runs while the route is being switched.','Пока маршрут переключается, тест скорости не идёт.','Wait until the switch ends.','Дождитесь окончания переключения.'],
 ['SPEED-PROFILES','speed','No server chosen','Сервер не выбран','The speed test needs at least one connected server.','Для теста скорости нужен хотя бы один подключённый сервер.','Choose connected servers.','Выберите подключённые серверы.'],
 ['SPEED-PROFILES-CHANGED','speed','Server list changed','Список серверов изменился','The servers changed after you chose them.','Серверы изменились после вашего выбора.','Choose again.','Выберите заново.'],
 ['SPEED-CONFIG-LIMIT','speed','Limit exceeded','Лимит превышен','The test would exceed the budget or daily limit you set.','Тест превысил бы заданный вами бюджет или суточный лимит.','Raise the limit below the table or test later.','Увеличьте лимит под таблицей или проверьте позже.'],
 ['AUTO-OPTIONS-NOT-CLEARED','switch','Auto settings could not be reset','Настройки Auto не удалось сбросить','The program stopped Auto but could not clear its own test-window settings because other unsaved router changes exist.','Программа остановила Auto, но не смогла сбросить собственные настройки окна теста, потому что на роутере есть другие несохранённые изменения.','Open the router’s unsaved changes and apply or revert them; then press Stop in the Auto card once more. Auto does not restart by itself: the stop is latched.','Откройте несохранённые изменения роутера и примените либо отмените их; затем ещё раз нажмите «Стоп» в блоке Auto. Auto сам не запустится: остановка зафиксирована.'],
 ['BOARD-OVERSIZE','service','Router board data too big','Данные о плате роутера слишком велики','The router’s board description was bigger than the program accepts, so it was not read.','Описание платы роутера больше, чем принимает программа, поэтому оно не прочитано.','Contact support with the code; nothing was changed.','Обратитесь в поддержку с кодом; ничего не менялось.'],
 ['CA-BUNDLE','service','Certificates package missing','Нет пакета сертификатов','The router has no certificate bundle, so secure (HTTPS) checks and Telegram cannot work.','На роутере нет набора сертификатов, поэтому защищённые (HTTPS) проверки и Telegram работать не могут.','Install ca-bundle (opkg install ca-bundle).','Установите ca-bundle (opkg install ca-bundle).'],
 ['LUCI-CACHE-ROOT','service','Page cache folder is wrong','Папка кэша страниц неверна','During an upgrade the program could not safely clear LuCI’s page cache.','При обновлении программа не смогла безопасно очистить кэш страниц LuCI.','Sign out of LuCI and in again, then Ctrl+F5.','Выйдите из LuCI и войдите снова, затем Ctrl+F5.'],
 ['PYTHON-39-MINIMUM','service','Python is too old','Python слишком старый','The program needs Python 3.9 or newer on the router.','Программе нужен Python 3.9 или новее на роутере.','Use a firmware with Python 3.9+ (GL.iNet 4.11.0 has it).','Используйте прошивку с Python 3.9+ (в GL.iNet 4.11.0 он есть).'],
 ['SPEED-WORKER-TIMEOUT','speed','Test took too long','Тест шёл слишком долго','The test did not finish in time and was stopped.','Тест не закончился вовремя и был остановлен.','Repeat; try a shorter duration.','Повторите; попробуйте меньшую длительность.']
];
// Families: any code that starts with the prefix gets this explanation (internal checks of the offline models and storage formats).
var ERROR_FAMILIES=[
 ['STATISTICS-','data','Saved statistics check','Проверка сохранённой статистики','The saved counters, incident details or download cursor failed validation. Unverified data is not presented as a successful observation.','Сохранённые счётчики, события или позиция выгрузки не прошли проверку. Непроверенные данные не считаются успешным наблюдением.','Retry the download. If the error persists, preserve both checkpoint files and inspect storage; do not reset the counters.','Повторите выгрузку. Если ошибка повторяется, сохраните оба файла контрольных точек и проверьте хранилище; не сбрасывайте счётчики.','STATISTICS-CURSOR: restart the download from the first page.','STATISTICS-CURSOR: начните выгрузку с первой страницы.'],
 ['PREP-','platform','Persistent router preparation (PREP-…)','Постоянная подготовка роутера (PREP-…)','A saved startup or acceleration prerequisite is missing, changed or unverified. A passing dependency check alone does not establish safe native operation.','Постоянная настройка запуска или ускорения отсутствует, изменена либо не проверена. Наличия зависимостей недостаточно для безопасного переключения.','Review the preparation card and the documented original values/undo procedure. Do not disable a working DNS owner or force-unload drivers.','Проверьте карточку подготовки и инструкцию с исходными значениями и отменой изменений. Не отключайте рабочий DNS и не выгружайте драйверы принудительно.'],
 ['PAIR-','internal','Two-channel Auto (PAIR-…)','Авторежим двух каналов (PAIR-…)','The two-channel controller is preparing profiles or refused an unverified operation. Router probes do not certify an external LAN client.','Контроллер двух каналов готовит профили либо отклонил непроверенное действие. Проверки роутера не подтверждают внешний LAN-клиент.','Read the current phase and reason. Stop remains available; keep the recovery record and do not delete it to bypass a refusal.','Прочитайте текущий этап и причину. Остановка остаётся доступной; сохраните запись восстановления и не удаляйте её ради обхода отказа.'],
 ['CASCADE-','internal','Internal check of the fallback model (CASCADE-…)','Внутренняя проверка модели каскада (CASCADE-…)','A safety check of the model that plans server → channel → protocol switching refused a step. These checks exist to stop a wrong or stale step; the model is not applied to the router in this version.','Защитная проверка модели, планирующей переключение сервер → канал → протокол, отклонила шаг. Эти проверки нужны, чтобы остановить неверный или устаревший шаг; в этой версии модель на роутер не применяется.','Nothing to do for a normal user. Send the full code to support if it appears on a real router.','Обычному пользователю делать ничего не нужно. Если код появился на настоящем роутере, отправьте его полностью в поддержку.','CASCADE-PROOF-EXPIRED: a confirmation arrived too late and was ignored.','CASCADE-PROOF-EXPIRED: подтверждение пришло слишком поздно и было проигнорировано.'],
 ['CANDIDATE-','internal','Internal check of candidate probing (CANDIDATE-…)','Внутренняя проверка пробы кандидатов (CANDIDATE-…)','A safety check of the model that tests replacement servers refused a step (limits, timing or ownership).','Защитная проверка модели, проверяющей замену серверов, отклонила шаг (лимиты, время или принадлежность).','Nothing to do for a normal user. Send the full code to support if it appears on a real router.','Обычному пользователю делать ничего не нужно. Если код появился на настоящем роутере, отправьте его полностью в поддержку.','CANDIDATE-BUDGET-EXCEEDED: the test would have used more traffic than allowed, so it was not run.','CANDIDATE-BUDGET-EXCEEDED: тест использовал бы больше трафика, чем разрешено, поэтому не запускался.'],
 ['MODEL-','internal','Internal check of the switching model (MODEL-…)','Внутренняя проверка модели переключения (MODEL-…)','A rule of the model of the switch process (used in tests) refused or reported a step.','Правило модели процесса переключения (она используется в тестах) отклонило или отметило шаг.','Nothing to do for a normal user.','Обычному пользователю делать ничего не нужно.'],
 ['CHECKPOINT-','data','Saved statistics file check (CHECKPOINT-…)','Проверка файла сохранённой статистики (CHECKPOINT-…)','The saved statistics file failed a validation (wrong structure, number or date). It is not used and the previous good copy stays.','Файл сохранённой статистики не прошёл проверку (неверная структура, число или дата). Он не используется, остаётся прежняя исправная копия.','Nothing to do; if the statistics look empty, see Help → Dates are wrong or history is blocked.','Делать ничего не нужно; если статистика пустая, см. «Помощь» → «Неверные даты или история заблокирована».','CHECKPOINT-DAY: a day in the file does not exist, so the file was refused.','CHECKPOINT-DAY: в файле несуществующий день, поэтому файл отклонён.'],
 ['MIGRATION-','data','Settings upgrade check (MIGRATION-…)','Проверка обновления настроек (MIGRATION-…)','While moving settings from an older version, a check failed. Nothing was changed when a check fails.','При переносе настроек из старой версии не прошла проверка. Если проверка не пройдена, ничего не меняется.','Keep the settings backup and reinstall the same version; send the code to support.','Сохраните резервную копию настроек и переустановите ту же версию; отправьте код в поддержку.','MIGRATION-EXTERNAL-EDIT: someone edited the file by hand during the upgrade.','MIGRATION-EXTERNAL-EDIT: во время обновления кто-то правил файл вручную.'],
 ['HISTORY-','data','Controller history check (HISTORY-…)','Проверка истории контроллера (HISTORY-…)','The record of switches failed a check (size, order or checksum). The controller then refuses to act, because it cannot prove what it did before.','Запись о переключениях не прошла проверку (размер, порядок или контрольная сумма). Тогда контроллер отказывается действовать, потому что не может доказать, что делал раньше.','If it repeats, archive the history over SSH (Help → emergency return) and start again.','Если повторяется, заархивируйте историю по SSH («Помощь» → аварийный возврат) и начните заново.','HISTORY-CHECKSUM: the file was changed or damaged.','HISTORY-CHECKSUM: файл изменён или повреждён.'],
 ['LIFECYCLE-','service','Upgrade and service safety check (LIFECYCLE-…)','Проверка безопасности обновления и службы (LIFECYCLE-…)','Before an upgrade or a stop, the program checks that Auto is off and the original route is restored. One of the checks did not pass.','Перед обновлением или остановкой программа проверяет, что Auto выключен и исходный маршрут восстановлен. Одна из проверок не прошла.','Stop Auto on the Overview, wait for the return, then repeat.','Остановите Auto на «Обзоре», дождитесь возврата и повторите.','LIFECYCLE-STOP-AUTO-FIRST: Auto is still on.','LIFECYCLE-STOP-AUTO-FIRST: Auto всё ещё включён.'],
 ['SPEED-','speed','Speed test code (SPEED-…)','Код теста скорости (SPEED-…)','A speed test step reported this condition (network, limits, clock or the router’s load). Nothing else is affected.','Шаг теста скорости сообщил это состояние (сеть, лимиты, часы или нагрузка роутера). Остальное не затронуто.','Repeat later. If it repeats, check the VPN and the free space.','Повторите позже. Если повторяется, проверьте VPN и свободное место.','SPEED-DNS: the name of the test server could not be resolved through that VPN.','SPEED-DNS: имя тестового сервера не удалось найти через этот VPN.'],
 ['FAULT-','switch','Failure test code (FAULT-…)','Код теста сбоя (FAULT-…)','The failure test reported this condition.','Тест сбоя сообщил это состояние.','See the failure test panel on the Tests page.','См. панель теста сбоя на странице «Тесты».'],
 ['TELEGRAM-','telegram','Telegram code (TELEGRAM-…)','Код Telegram (TELEGRAM-…)','A Telegram step reported this condition.','Шаг Telegram сообщил это состояние.','Open the Telegram wizard; Help → Telegram reports do not arrive.','Откройте мастер Telegram; «Помощь» → «Отчёты в Telegram не приходят».'],
 ['SETUP-','setup','Settings code (SETUP-…)','Код настроек (SETUP-…)','A settings step reported this condition.','Шаг настроек сообщил это состояние.','Reload the page (Ctrl+F5) and repeat.','Обновите страницу (Ctrl+F5) и повторите.'],
 ['PRIORITY-','setup','Priorities code (PRIORITY-…)','Код приоритетов (PRIORITY-…)','A step of the server priorities reported this condition.','Шаг приоритетов серверов сообщил это состояние.','Reload and repeat.','Обновите и повторите.'],
 ['RECOVERY-','setup','Recovery rules code (RECOVERY-…)','Код правил восстановления (RECOVERY-…)','A step of the recovery rules reported this condition.','Шаг правил восстановления сообщил это состояние.','Reload and repeat.','Обновите и повторите.'],
 ['RPC-','service','Request to the router (RPC-…)','Запрос к роутеру (RPC-…)','A request from the page to the router was refused because of its form or size.','Запрос страницы к роутеру отклонён из-за вида или размера.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['SCAN-','speed','Check request code (SCAN-…)','Код запроса проверки (SCAN-…)','A step of the “Check the VPNs now” request reported this condition.','Шаг запроса «Проверить VPN сейчас» сообщил это состояние.','Make sure the monitor runs and press again.','Убедитесь, что мониторинг работает, и нажмите снова.'],
 ['DEPENDENCY-','service','Missing program (DEPENDENCY-…)','Не хватает программы (DEPENDENCY-…)','A program the monitor needs is missing on the router.','На роутере не хватает программы, нужной мониторингу.','Reinstall the package; Help → install.','Переустановите пакет; «Помощь» → установка.'],
 ['GUARD-','switch','Safety block code (GUARD-…)','Код защитной блокировки (GUARD-…)','The program’s safety block reported this condition.','Защитная блокировка программы сообщила это состояние.','Help → emergency return.','«Помощь» → аварийный возврат.'],
 ['POLICY-','switch','VPN rules code (POLICY-…)','Код VPN-правил (POLICY-…)','The VPN rules of the router are not as the program expects.','VPN-правила роутера не такие, как ожидает программа.','Do not edit the VPN rules while Auto works.','Не меняйте VPN-правила, пока Auto работает.'],
 ['JOURNAL-','switch','Switch journal code (JOURNAL-…)','Код журнала переключения (JOURNAL-…)','The saved record of the last switch failed a check.','Сохранённая запись последнего переключения не прошла проверку.','Help → emergency return (close-journal).','«Помощь» → аварийный возврат (close-journal).'],
 ['UNSAFE-','switch','Unsafe name (UNSAFE-…)','Небезопасное имя (UNSAFE-…)','A name from the router has odd characters; the program refuses to use it in a command.','Имя от роутера содержит странные символы; программа отказывается использовать его в команде.','Contact support with the code.','Обратитесь в поддержку с кодом.']
];
function errorFamilyOf(code){
  for(var i=0;i<ERROR_FAMILIES.length;i++)if(code.indexOf(ERROR_FAMILIES[i][0])===0)return ERROR_FAMILIES[i];
  return null;
}
// "If you see this, then that": worked examples above the table; every code in them opens its row.
function errorExamples(){
  var C=errorCodeLink;
  var items=[
    [[bi('You see ','Вы видите '),C('DNS-001'),bi(' next to a server (red lamp).',' рядом с сервером (красная лампа).')],bi('The VPN is connected but name lookup fails, so websites do not open. Turn the profile off and on in GL.iNet; if it repeats, change the DNS server of the profile. If the reserve works, Auto can switch to it.','VPN подключён, но поиск адресов не работает, поэтому сайты не открываются. Выключите и включите профиль в GL.iNet; если повторяется, смените DNS-сервер профиля. Если резерв работает, Auto сможет переключиться на него.')],
    [[bi('The history says ','В истории написано '),C('ROLLED-BACK'),bi(' and beside it ',' и рядом '),C('CLIENT-CONFIRMATION-TIMEOUT'),'.'],bi('The router switched to the reserve, but your computer did not confirm in 90 seconds, so the router went back by itself. Nothing is broken. Start the LAN helper before the trial and keep its window open.','Роутер переключился на резерв, но ваш компьютер не подтвердил за 90 секунд, поэтому роутер вернулся сам. Ничего не сломано. Запустите LAN-помощник перед тестом и не закрывайте его окно.')],
    [[bi('The state is ','Состояние '),C('COMMITTED'),bi(' and the Overview says “Working on the reserve”.',' и на «Обзоре» «Работаю на резерве».')],bi('The primary failed, the switch worked and your computer confirmed it. Traffic is on the reserve. Auto returns by itself when the primary recovers, or press “Return to primary”.','Основной отказал, переключение удалось и ваш компьютер его подтвердил. Трафик идёт через резерв. Auto вернётся сам, когда основной восстановится, либо нажмите «Вернуться на основной».')],
    [[bi('The state is ','Состояние '),C('BLOCKED'),bi(' with ',' с '),C('HARDWARE-ACCELERATOR-UNVERIFIED'),'.'],bi('Auto refuses to switch because GL.iNet hardware acceleration is not proven off; with it on, traffic can bypass the rules. Turn it off in GL.iNet and wait a minute.','Auto отказывается переключать, потому что аппаратное ускорение GL.iNet не подтверждено как выключенное; при включённом трафик может обходить правила. Выключите его в GL.iNet и подождите минуту.')],
    [[bi('You see ','Вы видите '),C('EDGE-NOT-CERTIFIED'),bi(' beside a server.',' рядом с сервером.')],bi('This is not an error. The server works and could take over, but the switch itself has not been certified on this router: run the LAN trial.','Это не ошибка. Сервер работает и мог бы подхватить трафик, но само переключение на этом роутере не подтверждено: пройдите LAN-тест.')],
    [[bi('Telegram shows ','Telegram показывает '),C('TELEGRAM-REQUEST-REJECTED'),'.'],bi('“401” or “Unauthorized” means the bot token is wrong; “400” or “chat not found” means the chat ID is wrong or you did not press Start in the bot. Open the Telegram wizard: it explains how to get both.','«401» или «Unauthorized» значит, что токен бота неверный; «400» или «chat not found» — неверный Chat ID либо вы не нажали Start в боте. Откройте мастер Telegram: он объясняет, как получить и то и другое.')],
    [[bi('The Auto button answered ','Кнопка Auto ответила '),C('STOP-UNCONFIRMED'),'.'],bi('The Stop request could not be saved on the router, but a running failure test was still cleaned up. Press Stop again; if it repeats, use the emergency return in Help.','Запрос остановки не удалось сохранить на роутере, но запущенный тест сбоя всё равно убран. Нажмите «Стоп» ещё раз; если повторяется, используйте аварийный возврат из «Помощи».')]
  ];
  return E('details',{'class':'hv-errexamples','open':''},[E('summary',{},bi('How to read it: examples (if you see this, then that)','Как читать: примеры (если видите это — то это)')),
    E('ul',{},items.map(function(i){return E('li',{},[E('p',{},[E('b',{},i[0])]),E('p',{},i[1])]);})),
    E('p',{'class':'hv-muted'},bi('Every code on this page and on the other pages is a link: press it and you land on its row here, with what it means, how to fix it and an example. A word in capitals that is not a link is not a code of this program.','Любой код на этой и на других страницах — ссылка: нажмите, и вы окажетесь на его строке здесь, с тем, что он значит, как исправить и с примером. Слово заглавными буквами, не являющееся ссылкой, не код этой программы.'))]);
}

/* Table of diagnostic codes for the Events page: code, name, meaning and a collapsed "how to fix".
   Row: [code, group, name EN, name RU, meaning EN, meaning RU, fix EN, fix RU]. Codes and technical terms stay English. */
var ERROR_GROUPS=[['monitor',['Monitoring checks','Проверки мониторинга']],['switch',['Switching and Auto','Переключение и Auto']],['service',['Monitor service and page','Служба мониторинга и страница']],['helper',['LAN helper','LAN-помощник']],['telegram',['Telegram','Telegram']],['setup',['Settings and wizards','Настройки и мастера']],['speed',['Speed tests and scans','Тесты скорости и сканирование']],['data',['Data, clock and history','Данные, часы и история']]];
var ERROR_ROWS=[
 ['WAN-001','monitor','Internet is down at the router','Нет интернета на роутере','The router itself cannot reach the internet, not only the VPN.','Сам роутер не достаёт до интернета, а не только VPN.','Check the cable to the provider and the provider’s status. Restart the modem. If the internet is back, the monitor recovers by itself.','Проверьте кабель к провайдеру и статус провайдера. Перезапустите модем. Когда интернет вернётся, мониторинг восстановится сам.'],
 ['DNS-001','monitor','Name lookup fails','Не работает поиск адресов (DNS)','Name lookup (DNS) fails while connections by IP address work.','Поиск адресов (DNS) не работает, а соединения по IP-адресу работают.','Check the DNS server of the VPN profile or of the router. Another DNS (for example 1.1.1.1) in the VPN profile usually helps. If a VPN program runs on a computer, stop it for the test.','Проверьте DNS-сервер VPN-профиля или роутера. Обычно помогает другой DNS (например 1.1.1.1) в VPN-профиле. Если на компьютере работает программа VPN, остановите её на время теста.'],
 ['VPN-001','monitor','VPN did not connect','VPN не подключился','The VPN connection could not be established. The cause may stay unknown.','Не удалось установить соединение VPN. Причина может остаться неизвестной.','In GL.iNet → VPN Dashboard turn the profile off and on. If it fails again, try another server of the same provider or check the account and the subscription.','В GL.iNet → VPN Dashboard выключите и включите профиль. Если снова не вышло, возьмите другой сервер того же провайдера или проверьте аккаунт и подписку.'],
 ['VPN-002','monitor','VPN login rejected','VPN отклонил вход','The VPN server rejected the login or the key.','VPN-сервер отклонил логин или ключ.','Open the profile in GL.iNet and re-enter the login and password or import the config again. Check that the subscription is active.','Откройте профиль в GL.iNet и заново введите логин и пароль или импортируйте конфиг. Проверьте, что подписка активна.'],
 ['VPN-003','monitor','Tunnel is up but carries nothing','Туннель поднят, но трафика нет','The tunnel is connected but the check traffic does not pass through it. It does not always mean a bad server: routing or filtering may be the cause.','Туннель подключён, но проверочный трафик через него не проходит. Это не всегда вина сервера: причиной может быть маршрутизация или фильтрация.','Wait a few minutes (the monitor repeats the check). Then reconnect the profile or use another server. If all VPNs show it, check the WAN.','Подождите несколько минут (мониторинг повторяет проверку). Затем переподключите профиль или возьмите другой сервер. Если так у всех VPN, проверьте WAN.'],
 ['VPN-004','monitor','VPN server name does not resolve','Имя VPN-сервера не находится','The name of the VPN server cannot be resolved to an address.','Имя VPN-сервера не удаётся превратить в адрес.','Check DNS on the router and the server name in the profile. Use the server IP address if the provider gives one.','Проверьте DNS на роутере и имя сервера в профиле. Если провайдер даёт IP-адрес сервера, используйте его.'],
 ['TLS-001','monitor','Certificate check failed','Ошибка проверки сертификата','The HTTPS certificate was not accepted. The program never turns the check off by itself.','Сертификат HTTPS не принят. Программа никогда не отключает проверку сама.','Check the router date and time (a wrong clock breaks certificates) and that the package ca-bundle is installed.','Проверьте дату и время на роутере (неверные часы ломают сертификаты) и что установлен пакет ca-bundle.'],
 ['ROUTE-001','monitor','Traffic goes another way','Трафик идёт другим путём','The real route differs from the selected one.','Реальный маршрут отличается от выбранного.','Open GL.iNet → VPN Dashboard and check the order of the VPN rules. Do not change rules while Auto is working.','Откройте GL.iNet → VPN Dashboard и проверьте порядок правил VPN. Не меняйте правила, пока работает Auto.'],
 ['CHECK-001','monitor','Check not confirmed','Проверка не подтверждена','There is not enough evidence yet; the state stays “unknown”. It is shown while a VPN is still being checked.','Пока недостаточно данных; состояние остаётся «неизвестно». Показывается, пока VPN ещё проверяется.','Wait one or two check intervals. If it stays, press “Check the VPNs now” on the Overview.','Подождите один-два интервала проверки. Если не проходит, нажмите «Проверить VPN сейчас» на «Обзоре».'],
 ['SWITCH-001','switch','No ready reserve','Нет готового резерва','There is no reserve VPN that passed its checks, so there is nowhere to switch.','Нет резервного VPN, прошедшего проверки, поэтому переключаться некуда.','Connect another VPN profile in GL.iNet and select it as the reserve in Settings → System.','Подключите ещё один VPN-профиль в GL.iNet и выберите его резервным в «Настройки» → «Система».'],
['AUTO-CONTROL-UNVERIFIED','switch','Auto request not confirmed','Запрос Auto не подтверждён','The router answered, but not with a clear “accepted”. Nothing is assumed.','Роутер ответил, но не ясным «принято». Ничего не предполагается.','Look at the lamp and the Technical state in the Auto card; repeat the press only if nothing changed after a minute.','Посмотрите на лампу и «Техническое состояние» в блоке Auto; повторите нажатие, только если за минуту ничего не изменилось.'],
 ['AUTO-CONTROL-FAILED','switch','Auto request got no answer','Запрос Auto остался без ответа','The router did not answer the Start or Stop request at all.','Роутер вообще не ответил на запрос «Включить» или «Выключить».','Reload the page and check the monitor lamp. If the router is unreachable, use the emergency return in Help.','Обновите страницу и проверьте лампу мониторинга. Если роутер недоступен, используйте аварийный возврат из «Помощи».'],
 ['AUTO-START-REFUSED','switch','Auto start refused','Запуск Auto отклонён','The router refused to start Auto; the reasons are listed with their codes.','Роутер отказался запускать Auto; причины перечислены с кодами.','Fix the listed reasons (usually the LAN trial or a missing setting) and press again.','Устраните перечисленные причины (обычно LAN-тест или не заданная настройка) и нажмите снова.'],
 ['ROLLBACK-GIVEN-UP','switch','Automatic return stopped','Автоматический возврат остановлен','The return to the primary failed twice. The program stopped trying, keeps only VPN traffic allowed and turned Auto off.','Возврат на основной не удался дважды. Программа перестала пытаться, пропускает только трафик через VPN и выключила Auto.','Check the VPN rule order in the router (Help → emergency return), restore it by hand, then close the journal with the emergency command.','Проверьте порядок VPN-правил на роутере («Помощь» → аварийный возврат), восстановите его вручную и закройте журнал аварийной командой.'],
  ['EXIT-TRACE-FAILED','switch','Exit address could not be read','Не удалось прочитать внешний адрес','The check of the address the internet sees through the VPN got no clear answer (cut, garbled or not IPv4). Nothing is switched on such an answer.','Проверка адреса, который видит интернет через VPN, не получила ясного ответа (оборван, искажён или не IPv4). По такому ответу ничего не переключается.','Usually temporary. If it repeats, check the VPN server and that IPv4 works through it.','Обычно временно. Если повторяется, проверьте VPN-сервер и что через него работает IPv4.'],
 ['STOP-UNCONFIRMED','switch','Stop not confirmed','Остановка не подтверждена','The Stop request could not be saved on the router. A running failure test was still cleaned up.','Запрос остановки не удалось сохранить на роутере. Запущенный тест сбоя всё равно убран.','Press Stop again. If it repeats, use the emergency return in Help, or stop the service in System → Startup.','Нажмите «Стоп» ещё раз. Если повторяется, используйте аварийный возврат из «Помощи» или остановите службу в «Система» → «Автозапуск».'],
 ['SWITCH-002','switch','Internet not restored after the switch','Интернет не вернулся после переключения','The switch was applied but the following checks failed.','Переключение выполнено, но последующие проверки не прошли.','The router returns to the previous route by itself. Check the reserve VPN and run the LAN helper again.','Роутер сам возвращается на прежний маршрут. Проверьте резервный VPN и запустите LAN-помощник снова.'],
 ['SWITCH-003','switch','Switch could not be applied','Переключение не удалось применить','The route change itself failed (not the same as SWITCH-002).','Сама смена маршрута не удалась (это не то же самое, что SWITCH-002).','Open Help → “The router stays on the reserve VPN” and check the VPN rule order in GL.iNet.','Откройте «Помощь» → «Роутер остаётся на резервном VPN» и проверьте порядок правил VPN в GL.iNet.'],
 ['CONFIG-001','switch','Automation paused after manual change','Автоматика на паузе после ручного изменения','Someone changed the VPN settings by hand, so automation stepped aside.','Кто-то изменил настройки VPN вручную, поэтому автоматика отошла в сторону.','Check the VPN rule order in GL.iNet. Run a new LAN trial before starting Auto again.','Проверьте порядок правил VPN в GL.iNet. Перед новым запуском Auto пройдите LAN-тест заново.'],
 ['SYSTEM-001','service','Unsupported firmware or missing tool','Неподдерживаемая прошивка или нет программы','The firmware version or a required tool is not supported.','Версия прошивки или нужная программа не поддерживается.','Compare with the tested firmware (GL.iNet 4.11.0) on the Readiness page. Monitoring still works; Auto needs the supported firmware.','Сравните с проверенной прошивкой (GL.iNet 4.11.0) на странице «Готовность системы». Мониторинг работает, а для Auto нужна поддерживаемая прошивка.'],
 ['MONITOR-START-REQUESTED','service','Start requested','Запуск запрошен','The monitor was switched on. This is not yet proof that it runs.','Мониторинг включён. Это ещё не доказательство, что он работает.','Wait up to a minute for fresh data; the traffic light turns green.','Подождите до минуты свежих данных; светофор станет зелёным.'],
 ['MONITOR-STOP-REQUESTED','service','Stop requested','Остановка запрошена','The monitor was asked to stop.','Мониторингу отправлена команда остановиться.','Nothing to do. It does not mean the internet recovered.','Делать ничего не нужно. Это не значит, что интернет восстановился.'],
 ['MONITOR-STOP-AUTO-FIRST','service','Stop Auto first','Сначала остановите Auto','Auto or a retained reserve prevents stopping the monitor.','Auto или удерживаемый резерв мешают остановить мониторинг.','Press Stop on Auto, wait until it returns to the primary, then stop the monitor.','Нажмите «Стоп» у Auto, дождитесь возврата на основной, затем остановите мониторинг.'],
 ['MONITOR-JOURNAL-UNVERIFIED','service','Journal cannot be read','Журнал не читается','The transaction journal is damaged or unreadable.','Журнал транзакций повреждён или не читается.','Do not delete it. Follow Help → “I have no internet” and router-test-kit/EMERGENCY.md.','Не удаляйте его. Следуйте «Помощи» → «У меня пропал интернет» и router-test-kit/EMERGENCY.md.'],
 ['MONITOR-SAVE-FAILED','service','Setting not saved','Настройка не сохранилась','The router did not confirm the saved setting.','Роутер не подтвердил сохранение настройки.','Try again. If it repeats, check free space (df -h /etc) and the system log (logread).','Повторите. Если снова, проверьте свободное место (df -h /etc) и системный журнал (logread).'],
 ['MONITOR-SERVICE-UNCONFIRMED','service','Service change not confirmed','Смена состояния службы не подтверждена','The setting may be saved but the service did not confirm the start or stop.','Настройка могла сохраниться, но служба не подтвердила запуск или остановку.','After a minute check the Monitoring block on the Overview; if its lamp is not green, press “Start monitoring” there.','Через минуту посмотрите блок «Мониторинг» на «Обзоре»; если лампа не зелёная, нажмите там «Запустить мониторинг».'],
 ['MONITOR-INVALID','service','Invalid request','Неверный запрос','The request had wrong fields. Nothing was written.','В запросе неверные поля. Ничего не записано.','Reload the page (Ctrl+F5). If it repeats, the page and the program versions differ: see the notice on the Overview.','Обновите страницу (Ctrl+F5). Если повторяется, версии страницы и программы различаются: см. сообщение на «Обзоре».'],
 ['MONITOR-RPC-UNCONFIRMED','service','No confirmed answer','Нет подтверждённого ответа','The browser did not get a confirmed answer from the router.','Браузер не получил подтверждённого ответа от роутера.','Reload the status. Do not assume the monitor stopped.','Обновите статус. Не считайте, что мониторинг остановился.'],
 ['RPC-UNAVAILABLE','service','Router does not answer','Роутер не отвечает','The page cannot get the status from the router; old values are shown.','Страница не получает статус от роутера; показаны старые значения.','Reload the page and sign in to LuCI again. Then Help → “The page is old, empty or says the monitor is not running”.','Обновите страницу и войдите в LuCI снова. Затем «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'],
 ['STATUS-STALE','service','Status is old','Статус устарел','The monitor is switched on but its data is older than 90 seconds.','Мониторинг включён, но его данные старше 90 секунд.','Wait a minute and reload the page; if the lamp is red press “Start monitoring” in the Monitoring block. If it stays, see Help → “The page is old, empty or says the monitor is not running”.','Подождите минуту и обновите страницу; если лампа красная, нажмите «Запустить мониторинг» в блоке «Мониторинг». Если не помогло, см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'],
 ['RPC-PLUGIN','service','Program plugin missing','Нет модуля программы','The plugin that connects the page to the program is missing on the router.','На роутере нет модуля, который связывает страницу с программой.','Reinstall the package (opkg install) and sign out of LuCI and in again.','Переустановите пакет (opkg install) и выйдите из LuCI и войдите снова.'],
 ['RPC-INPUT-SIZE','service','Request too large','Слишком большой запрос','The request was rejected because it was too large or too complex.','Запрос отклонён: он слишком большой или сложный.','Reload the page and repeat. This normally does not happen with the standard page.','Обновите страницу и повторите. С обычной страницей этого не бывает.'],
 ['CLIENT-CABLE-LINK-DOWN','helper','Cable adapter is down','Кабельный адаптер не подключён','The cable adapter you chose is not up.','Выбранный кабельный адаптер не поднят.','Plug the cable into a LAN port of the router and run the helper again with the right adapter number (Get-NetAdapter).','Вставьте кабель в LAN-порт роутера и запустите помощника снова с правильным номером адаптера (Get-NetAdapter).'],
 ['CLIENT-CABLE-ADDRESS-AMBIGUOUS','helper','Cable has no single address','У кабеля нет одного адреса','The cable adapter has no address or several.','У кабельного адаптера нет адреса или их несколько.','Wait until the adapter gets one 192.168.8.x address, then run again.','Дождитесь, пока адаптер получит один адрес 192.168.8.x, и запустите снова.'],
 ['CLIENT-CABLE-NOT-LOCAL','helper','Router is not on the cable','Роутер не через кабель','The route to the router does not go through the cable adapter.','Маршрут до роутера идёт не через кабельный адаптер.','Disable Wi-Fi on the computer for the test and use the cable only.','На время теста отключите Wi-Fi на компьютере и используйте только кабель.'],
 ['CLIENT-CABLE-PROBE-ROUTE-MISMATCH','helper','Probe route does not match','Проверочный маршрут не совпал','The probe routes do not go through the router on the cable.','Проверочные маршруты идут не через роутер по кабелю.','Run the helper again; if it repeats, remove the leftover probe routes (see CLIENT-PROBE-ROUTE-CONFLICT).','Запустите помощника снова; если повторяется, удалите оставшиеся проверочные маршруты (см. CLIENT-PROBE-ROUTE-CONFLICT).'],
 ['CLIENT-CABLE-HTTPS-FAILED','helper','HTTPS check on the cable failed','Проверка HTTPS по кабелю не прошла','The HTTPS test through the cable did not pass.','Проверка HTTPS через кабель не прошла.','Allow default routes on that adapter (Help → “The LAN helper fails”) and check that the router has internet.','Разрешите маршруты по умолчанию на этом адаптере («Помощь» → «LAN-помощник не работает») и проверьте, что у роутера есть интернет.'],
 ['CLIENT-GATEWAY-MISMATCH','helper','Wrong gateway','Не тот шлюз','The computer does not use the router as its gateway.','Компьютер не использует роутер как шлюз.','Connect the computer to the router’s network (or use the cable) and turn off other VPN or network programs.','Подключите компьютер к сети роутера (или кабелем) и отключите другие программы VPN и сетевые программы.'],
 ['CLIENT-DNS-CONFIG-UNVERIFIED','helper','DNS settings unverified','Настройки DNS не подтверждены','The computer uses a DNS server other than the router.','Компьютер использует DNS-сервер, отличный от роутера.','Set the DNS of the computer to automatic (from the router) for the test.','Установите DNS на компьютере автоматически (от роутера) на время теста.'],
 ['CLIENT-IPV6-DEFAULT-UNVERIFIED','helper','IPv6 route unverified','Маршрут IPv6 не подтверждён','The computer has an IPv6 default route that the helper cannot verify.','У компьютера есть маршрут IPv6 по умолчанию, который помощник не может проверить.','Turn off IPv6 on the test adapter for the minutes of the test.','Отключите IPv6 на тестовом адаптере на время теста.'],
 ['CLIENT-PROBE-ROUTE-CONFLICT','helper','Leftover probe routes','Остались проверочные маршруты','A previous run left temporary routes for 1.1.1.1 and 1.0.0.1.','Прошлый запуск оставил временные маршруты для 1.1.1.1 и 1.0.0.1.','Remove them (Help → “The LAN helper fails” shows the command) and run again.','Удалите их (команда есть в «Помощи» → «LAN-помощник не работает») и запустите снова.'],
 ['CLIENT-CANCELLED','helper','Cancelled','Отменено','You did not type TEST, so the trial did not start.','Вы не ввели TEST, поэтому тест не начался.','Run again and type TEST only when you are ready for a short interruption.','Запустите снова и вводите TEST, только когда готовы к короткому разрыву.'],
 ['CLIENT-TRIAL-UNCONFIRMED','helper','Trial not confirmed','Тест не подтверждён','The router did not get a valid confirmation from the computer in time.','Роутер не получил вовремя верное подтверждение от компьютера.','The router returned to the previous route. Check the cable and run again.','Роутер вернулся на прежний маршрут. Проверьте кабель и запустите снова.'],
 ['CLIENT-RESERVE-NOT-VERIFIED','helper','Reserve not verified','Резерв не подтверждён','The computer did not see the reserve VPN exit.','Компьютер не увидел выход через резервный VPN.','Check that the reserve VPN really works (Overview) and try again.','Проверьте, что резервный VPN действительно работает («Обзор»), и повторите.'],
 ['POWERSHELL-7-REQUIRED','helper','PowerShell 7 needed','Нужен PowerShell 7','The helper needs PowerShell 7 (pwsh).','Помощнику нужен PowerShell 7 (pwsh).','Install it: winget install Microsoft.PowerShell, then start the helper with pwsh.','Установите: winget install Microsoft.PowerShell, затем запускайте помощника через pwsh.'],
 ['PRIVATE-LAN-ROUTER-REQUIRED','helper','Router address is not private','Адрес роутера не частный','The helper accepts only a private LAN address.','Помощник принимает только частный адрес локальной сети.','Use the router address such as http://192.168.8.1:8080/.','Укажите адрес роутера вида http://192.168.8.1:8080/.'],
 ['TELEGRAM-TOKEN-REQUIRED','telegram','Bot token missing','Нет токена бота','No bot token is stored.','Токен бота не сохранён.','Enter the token in Settings → 2 · Telegram (see Help → “Telegram reports do not arrive”).','Введите токен в «Настройки» → «2 · Telegram» (см. «Помощь» → «Отчёты в Telegram не приходят»).'],
 ['TELEGRAM-TOKEN-FORMAT','telegram','Token looks wrong','Токен выглядит неверно','The token does not have the form 123456789:AAH… .','Токен не похож на 123456789:AAH….','Copy the whole token from @BotFather again, without spaces.','Скопируйте токен из @BotFather заново целиком, без пробелов.'],
 ['TELEGRAM-TOKEN-REJECTED','telegram','Token rejected by Telegram','Telegram отклонил токен','Telegram says the token is not valid.','Telegram сообщает, что токен недействителен.','Create a new token in @BotFather (/token) and enter it again.','Создайте новый токен в @BotFather (/token) и введите заново.'],
 ['TELEGRAM-DESTINATION-FORMAT','telegram','Chat ID looks wrong','ID чата выглядит неверно','The chat ID has a wrong form.','У ID чата неверный вид.','Use digits (123456789, or -100… for a group) or @channel_name.','Используйте цифры (123456789 или -100… для группы) или @имя_канала.'],
 ['TELEGRAM-PERMISSION','telegram','Bot cannot write there','Бот не может туда писать','The bot has no right to write to this chat.','У бота нет права писать в этот чат.','Press Start in the bot chat, or make the bot an administrator of the group/channel.','Нажмите Start в чате с ботом или сделайте бота администратором группы/канала.'],
 ['TELEGRAM-RATE-LIMIT','telegram','Too many messages','Слишком много сообщений','Telegram asks to wait before the next message.','Telegram просит подождать перед следующим сообщением.','Wait; the program retries by itself. Use a longer report interval.','Подождите; программа повторит сама. Поставьте более длинный интервал отчётов.'],
 ['TELEGRAM-DNS','telegram','Telegram address not found','Адрес Telegram не найден','The router cannot resolve the Telegram address.','Роутер не может найти адрес Telegram.','Check the internet and DNS on the router.','Проверьте интернет и DNS на роутере.'],
 ['TELEGRAM-TLS','telegram','Secure connection failed','Защищённое соединение не удалось','The secure connection to Telegram failed.','Защищённое соединение с Telegram не удалось.','Check the router date and time and the ca-bundle package.','Проверьте дату и время на роутере и пакет ca-bundle.'],
 ['TELEGRAM-DELIVERY-UNKNOWN','telegram','Delivery not confirmed','Доставка не подтверждена','A report was sent but Telegram did not confirm it.','Отчёт отправлен, но Telegram не подтвердил доставку.','Check the chat. The program does not send a duplicate automatically.','Проверьте чат. Программа не отправляет дубликат автоматически.'],
 ['TELEGRAM-DELIVERED','telegram','Delivered','Доставлено','A report was delivered.','Отчёт доставлен.','Nothing to do.','Делать ничего не нужно.'],
 ['TELEGRAM-TEST-DELIVERED','telegram','Test delivered','Тест доставлен','The test message was delivered.','Тестовое сообщение доставлено.','Nothing to do.','Делать ничего не нужно.'],
 ['TELEGRAM-CONFIG','telegram','Telegram setup incomplete','Настройка Telegram неполная','The Telegram settings are incomplete or invalid.','Настройки Telegram неполные или неверные.','Open Settings → 2 · Telegram and fill in the token and the chat ID again.','Откройте «Настройки» → «2 · Telegram» и заполните токен и ID чата заново.'],
 ['TELEGRAM-CLOCK-BACKWARD','telegram','Clock went back','Часы пошли назад','The router clock went back, so reports are paused.','Часы роутера пошли назад, поэтому отчёты приостановлены.','Check the router date and time (NTP).','Проверьте дату и время роутера (NTP).'],
 ['TELEGRAM-STATE-CORRUPT','telegram','Report state damaged','Состояние отчётов повреждено','The saved report state is damaged.','Сохранённое состояние отчётов повреждено.','The program recovers it by itself; save the Telegram settings again if it stays.','Программа восстанавливает его сама; если не прошло, сохраните настройки Telegram заново.'],
 ['SETUP-INVALID','setup','Invalid input','Неверный ввод','A wizard field has an invalid value.','В поле мастера неверное значение.','Correct the highlighted fields and review again.','Исправьте выделенные поля и проверьте ещё раз.'],
 ['SETUP-RANGE','setup','Value out of range','Значение вне диапазона','A number is outside the allowed range.','Число вне допустимого диапазона.','Use a value inside the range shown next to the field.','Укажите значение в диапазоне, показанном рядом с полем.'],
 ['SETUP-SAVE-FAILED','setup','Settings not saved','Настройки не сохранены','The router did not confirm the saved settings.','Роутер не подтвердил сохранение настроек.','Try again. Check free space and the log (logread) if it repeats.','Повторите. Если снова, проверьте свободное место и журнал (logread).'],
 ['SETUP-STOP-FIRST','setup','Stop Auto first','Сначала остановите Auto','The change is not allowed while Auto is running.','Изменение недопустимо, пока работает Auto.','Stop Auto, wait for the return to the primary, then change the settings.','Остановите Auto, дождитесь возврата на основной и меняйте настройки.'],
 ['SETUP-SAVE-UNCONFIRMED','setup','Save not confirmed','Сохранение не подтверждено','The router did not answer the save in time. The change may or may not have been written.','Роутер не ответил на сохранение вовремя. Изменение могло записаться, а могло и нет.','Reload the page and look at the setting. If it is wrong, save again. If the router reports unsaved changes, see Help.','Обновите страницу и посмотрите настройку. Если она неверная, сохраните ещё раз. Если роутер сообщает о несохранённых изменениях, см. «Помощь».'],
 ['SETUP-PENDING-DELTA','setup','Unsaved router changes','Есть несохранённые изменения роутера','The router has uncommitted changes of this program’s settings.','На роутере есть неприменённые изменения настроек этой программы.','Open LuCI → Unsaved changes and apply or revert them, then repeat.','Откройте LuCI → «Несохранённые изменения», примените или отмените их и повторите.'],
 ['SETUP-PRIMARY-RESERVE-DISABLED','setup','Primary or reserve is off','Основной или резервный отключён','The chosen primary or reserve profile is not enabled for monitoring.','Выбранный основной или резервный профиль не включён для наблюдения.','Enable both profiles in the System wizard.','Включите оба профиля в мастере «Система».'],
 ['SETUP-PROFILES','setup','Profiles not found','Профили не найдены','A selected profile no longer exists on the router.','Выбранного профиля больше нет на роутере.','Choose existing profiles again in the System wizard.','Выберите существующие профили заново в мастере «Система».'],
 ['SPEED-DISABLED','speed','Speed tests are off','Тесты скорости выключены','Speed tests are switched off.','Тесты скорости выключены.','Turn them on in Advanced → Tests → Speed test settings.','Включите их в «Расширенное» → «Тесты» → «Настройки тестов скорости».'],
 ['SPEED-DAILY-LIMIT','speed','Daily quota used','Суточная квота исчерпана','The daily data quota for tests is used up.','Суточная квота данных для тестов исчерпана.','Wait for tomorrow or raise the quota in the speed test settings.','Дождитесь завтра или увеличьте квоту в настройках тестов скорости.'],
 ['SPEED-COOLDOWN','speed','Please wait','Нужна пауза','A test of this server ran recently.','Этот сервер тестировали недавно.','Try again later.','Повторите позже.'],
 ['SPEED-BUSY','speed','Another test is running','Уже идёт другой тест','Another test is running.','Уже выполняется другой тест.','Wait until it finishes or cancel it.','Дождитесь его окончания или отмените.'],
 ['SPEED-TRAFFIC-BUSY','speed','VPN is busy','VPN сейчас занят','The VPN carries more traffic than the limit, so the test was skipped.','Через VPN идёт трафика больше лимита, поэтому тест пропущен.','Run the test when the VPN is less busy or raise the limit.','Запустите тест, когда VPN менее загружен, или поднимите лимит.'],
 ['SPEED-ROUTE-UNVERIFIED','speed','Test route unverified','Путь теста не подтверждён','It is not proven that the test goes through the chosen VPN.','Не доказано, что тест идёт через выбранный VPN.','Make sure the VPN is connected and try again.','Убедитесь, что VPN подключён, и повторите.'],
 ['SPEED-PROFILE-INACTIVE','speed','VPN not connected','VPN не подключён','The VPN to test is not connected.','VPN для теста не подключён.','Connect the profile in GL.iNet first; this program never connects VPNs.','Сначала подключите профиль в GL.iNet; эта программа VPN не подключает.'],
 ['SPEED-NETWORK','speed','Test network error','Сетевая ошибка теста','The test could not connect.','Тесту не удалось соединиться.','Check the VPN and the internet and try again.','Проверьте VPN и интернет и повторите.'],
 ['SPEED-CANCELLED','speed','Cancelled','Отменено','The test was cancelled.','Тест отменён.','Nothing to do.','Делать ничего не нужно.'],
 ['SCAN-DEADLINE-EXCEEDED','speed','Check took too long','Проверка заняла слишком много времени','The “Check the VPNs now” request did not finish in time.','Запрос «Проверить VPN сейчас» не завершился вовремя.','Press the button again after a minute. Check that the monitor is running.','Нажмите кнопку ещё раз через минуту. Проверьте, что мониторинг работает.'],
 ['SCAN-STATE-CORRUPT','speed','Check state damaged','Состояние проверки повреждено','The saved state of the check is damaged.','Сохранённое состояние проверки повреждено.','Press “Check the VPNs now” again; it creates a new state.','Нажмите «Проверить VPN сейчас» ещё раз; создастся новое состояние.'],
 ['CLOCK-001','data','Wrong router date','Неверная дата на роутере','The router date is impossible or jumped.','Дата роутера невозможна или скачет.','Set the time zone and enable NTP in LuCI → System → System. Statistics wait for a correct clock.','Задайте часовой пояс и включите NTP в LuCI → «Система» → «Система». Статистика ждёт верных часов.'],
 ['HISTORY-001','data','History unavailable','История недоступна','The saved controller history cannot be read.','Сохранённую историю контроллера не удаётся прочитать.','Do not delete files. The program starts a new history; keep a copy of /etc/homensai-vpn if you need the old one.','Не удаляйте файлы. Программа начнёт новую историю; сохраните копию /etc/homensai-vpn, если нужна старая.'],
 ['FAULT-CERTIFIED-AUTO-REQUIRED','switch','Failure test not available yet','Тест сбоя пока недоступен','The failure simulation (Tests page) needs a passed LAN trial of the configured primary and reserve first, so that the router knows a safe return exists.','Имитации сбоя (страница «Тесты») сначала нужен пройденный LAN-тест настроенных основного и резервного, чтобы роутер знал, что безопасный возврат существует.','Choose the primary and the reserve (Settings → System), run the LAN helper from a computer on the cable (Help → “What is the LAN helper”), then start a bounded trial. Come back to this page afterwards.','Выберите основной и резервный («Настройки» → «Система»), запустите LAN-помощника с компьютера по кабелю («Помощь» → «Что такое LAN-помощник») и начните тест в ограниченном окне. Потом вернитесь на эту страницу.'],
 ['FAULT-UNVERIFIED','switch','Failure test not confirmed','Сбой не подтверждён','The router did not confirm that the simulated failure was applied or removed.','Роутер не подтвердил, что имитация сбоя применена или снята.','Press “Cancel fault now”, check the Overview that traffic works, then try again.','Нажмите «Отменить сбой сейчас», проверьте на «Обзоре», что трафик идёт, и повторите.'],
 ['FAULT-UNKNOWN','switch','Failure test result unknown','Итог теста сбоя неизвестен','The result of the failure request is unknown.','Итог запроса на сбой неизвестен.','Reload the page. If the VPN has no traffic, press “Cancel fault now”.','Обновите страницу. Если через VPN нет трафика, нажмите «Отменить сбой сейчас».'],
 ['FAULT-CANCEL-UNKNOWN','switch','Cancel not confirmed','Отмена не подтверждена','The cancel request was sent but not confirmed.','Запрос на отмену отправлен, но не подтверждён.','Check the Tests page after a minute. The failure also ends by itself when its time is over (a timeout in the router).','Проверьте страницу «Тесты» через минуту. Сбой также заканчивается сам по истечении времени (таймаут в роутере).'],
 ['FAULT-RPC-UNCONFIRMED','switch','No answer from the router','Нет ответа от роутера','The page did not get a confirmed answer to the failure request.','Страница не получила подтверждённого ответа на запрос сбоя.','Reload the page and look at the state of the test before repeating.','Обновите страницу и посмотрите состояние теста, прежде чем повторять.'],
 ['FAULT-FIELDS','switch','Invalid request','Неверный запрос','The failure request had wrong fields.','В запросе сбоя неверные поля.','Reload the page (Ctrl+F5) and try again.','Обновите страницу (Ctrl+F5) и повторите.'],
 ['FAULT-HISTORY-UNAVAILABLE','data','Failure history unavailable','История сбоев недоступна','The saved history of failure tests cannot be read.','Сохранённую историю тестов сбоя не удаётся прочитать.','Do not delete files. A new history starts by itself.','Не удаляйте файлы. Новая история начнётся сама.'],
 ['FAULT-STATE-CORRUPT','switch','Failure state damaged','Состояние сбоя повреждено','The saved state of a failure test is damaged.','Сохранённое состояние теста сбоя повреждено.','Press “Cancel fault now”; the program cleans up its own traffic rule.','Нажмите «Отменить сбой сейчас»; программа уберёт собственное правило трафика.'],
 ['FAULT-NFT-QUERY-FAILED','switch','Cannot read the firewall rule','Не удаётся прочитать правило межсетевого экрана','The router did not answer a query about the program’s own temporary rule.','Роутер не ответил на запрос о собственном временном правиле программы.','Wait for the timeout of the test (up to 3 minutes) and try again; nothing else is changed.','Дождитесь таймаута теста (до 3 минут) и повторите; больше ничего не меняется.'],
 ['FAULT-TABLE-ALREADY-EXISTS','switch','A previous test is still active','Предыдущий тест ещё активен','The program’s own temporary rule from a previous test still exists.','Собственное временное правило программы от прошлого теста ещё существует.','Press “Cancel fault now” or wait for its timeout.','Нажмите «Отменить сбой сейчас» или дождитесь таймаута.'],
 ['HISTORY-PARTIAL','data','History partly aggregated','История частично объединена','Older measurements were aggregated or pruned to keep the storage and the answer size small.','Старые измерения объединены или удалены, чтобы хранилище и ответ роутера оставались небольшими.','Nothing to fix. Recent days are complete; very old details are summarised.','Исправлять нечего. Недавние дни полные; очень старые подробности сведены в итоги.'],
 ['SPEED-HISTORY-TRUNCATED','speed','Speed history shortened','История скорости сокращена','Only the newest speed results are kept; older ones were dropped.','Хранятся только новейшие результаты скорости; старые удалены.','Nothing to fix. Export what you need before it is dropped.','Исправлять нечего. Сохраните нужное до удаления.'],
 ['JOURNAL-INTEGRITY-FAILED','switch','Journal failed its check','Журнал не прошёл проверку','The transaction journal has a wrong checksum.','У журнала транзакций неверная контрольная сумма.','Do not delete it. Follow router-test-kit/EMERGENCY.md and ask for help with the output of show.','Не удаляйте его. Следуйте router-test-kit/EMERGENCY.md и просите помощи, приложив вывод show.']
];
var AUTO_NAMES={
 'EXISTING-TUNNEL-BINDING-UNVERIFIED':['Tunnel binding unverified','Привязка туннеля не проверена'],
 'MT3000-FIRMWARE-UNVERIFIED':['MT3000 firmware unverified','Прошивка MT3000 не проверена'],
 'MT3000-FIREWALL-UNVERIFIED':['MT3000 firewall unverified','Firewall MT3000 не проверен'],
 'FW3-INCLUDE-CONTRACT-UNVERIFIED':['FW3 include unverified','Include FW3 не проверен'],
 'FW3-RUNTIME-STATE-UNVERIFIED':['Running FW3 unverified','Рабочий FW3 не проверен'],
 'FW3-SELECTED-ZONE-UNVERIFIED':['VPN firewall zone unverified','VPN-зона firewall не проверена'],
 'VENDOR-WORKER-QUIET-UNVERIFIED':['Background completion unverified','Завершение фоновых операций не проверено'],
  'MONITOR-ONLY-DEPLOYMENT':['Monitoring-only installation','Установка только для мониторинга'],
  'MONITOR-ONLY-INVALID':['Deployment mode unverified','Режим установки не проверен'],
  'NATIVE-PROGRESS-UNVERIFIED':['Controller progress records unverified','Записи состояния контроллера не проверены'],
  'RESERVE-IDENTITY-UNKNOWN':['Current reserve identity unknown','Текущая идентичность резерва неизвестна'],
  'OBSERVATION-STALE':['Tunnel observations stale','Наблюдения туннелей устарели'],
  'VENDOR-IDENTITY-UNKNOWN':['Router tunnel identity unknown','Идентичность туннеля роутера неизвестна'],
  'VENDOR-SAME-TUNNEL':['Profiles share one router tunnel','Профили относятся к одному туннелю'],
  'PROFILE-IDENTITY-CHANGED':['Current profile binding changed','Текущая привязка профиля изменилась'],
  'VENDOR-SETTLING':['Waiting for configuration observations','Ожидание наблюдений конфигурации'],
  'CONTROL-REVISION-STALE':['Auto controls changed','Управление Auto изменилось'],
  'START-STATE-UNVERIFIED':['Saved Auto state unverified','Состояние Auto не проверено'],
  'STOP-SUPERSEDED-START':['Pending Start cancelled','Ожидающий запуск отменён'],
  'START-CONFIG-CHANGED':['Settings changed during Start','Настройки изменились при запуске'],
'LAN-TRIAL-REQUIRED':['LAN trial required','Нужен LAN-тест'],'BOUNDED-DEADLINE-REQUIRED':['Test window missing','Нет окна теста'],'SESSION-LOSS-NOT-ACCEPTED':['Reconnection not accepted','Не разрешён разрыв сессий'],
'TRANSACTION-IN-PROGRESS':['Switch in progress','Переключение идёт'],'TRIAL-ATTEMPT-LIMIT':['Trial attempt limit','Лимит попыток теста'],'UNSUPPORTED-BOARD':['Unsupported router model','Неподдерживаемая модель роутера'],
'UNSUPPORTED-FIRMWARE':['Unsupported firmware','Неподдерживаемая прошивка'],'FIRMWARE-UNKNOWN':['Firmware unknown','Прошивка неизвестна'],'VENDOR-CODE-CHANGED':['GL.iNet code changed','Код GL.iNet изменился'],
'VENDOR-CODE-UNVERIFIED':['GL.iNet code unverified','Код GL.iNet не проверен'],'VENDOR-WORKER-BUSY':['GL.iNet program is busy','Программа GL.iNet занята'],'HARDWARE-ACCELERATOR-UNVERIFIED':['Hardware acceleration unverified','Аппаратное ускорение не проверено'],
'SOFTWARE-ACCELERATOR-UNVERIFIED':['Software acceleration unverified','Программное ускорение не проверено'],'FLOW-OFFLOAD-ENABLED':['Flow offload is on','Включён flow offload'],'IPV6-NOT-EXPLICITLY-DISABLED':['IPv6 not disabled','IPv6 не отключён'],
'KILLSWITCH-NOT-ENABLED':['Kill Switch is off','Kill Switch выключен'],'DIRECT-WAN-FALLBACK':['Direct exit without VPN possible','Возможен выход мимо VPN'],'VPN-POLICY-DISABLED':['VPN policy is off','Политика VPN выключена'],
'TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED':['Two to sixteen rules needed','Нужно от 2 до 16 правил VPN'],'GENERIC-RULES-NOT-ADJACENT':['Rules not adjacent','Правила идут не подряд'],'GENERIC-DUPLICATE-INTERFACE':['Duplicate interface','Повтор интерфейса'],
'SPECIAL-RULES-MUST-PRECEDE-GENERIC':['Special rules in wrong order','Особые правила в неверном порядке'],'SOURCE-RESERVE-NOT-CONFIGURED':['Primary or reserve not set','Основной или резерв не заданы'],'PROFILE-INACTIVE':['Profile not connected','Профиль не подключён'],
'PROFILES-NOT-GENERIC-RULES':['Profiles not in general rules','Профили не в общих правилах'],'SAME-INTERFACE':['Same interface twice','Один интерфейс дважды'],'POLICY-ORDER-DIRECTION-UNVERIFIED':['Rule order direction unverified','Направление порядка правил не проверено'],
'LAN-LAYOUT-UNSUPPORTED':['Unsupported LAN layout','Неподдерживаемая схема LAN'],'PROFILE-NOT-MONITORED':['Profile not monitored','Профиль не наблюдается'],'NFT-GUARD-UNAVAILABLE':['Safety block unavailable','Страхующая блокировка недоступна'],
'POLICY-READ-FAILED':['Cannot read VPN rules','Не удаётся прочитать правила VPN'],'UPLINK-LINK-DOWN':['Uplink is down','Внешний канал отключён'],'LEASE-INTEGRITY-FAILED':['Lease damaged','Аренда повреждена'],
'LEASE-STORAGE-FAILED':['Lease cannot be saved','Аренда не сохраняется'],'LEGACY-LEASE-RECOVERY':['Old lease recovered','Восстановлена старая аренда'],'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':['Outside change, block kept','Изменение извне, блокировка сохранена'],
'ROLLBACK-UNVERIFIED-GUARD-RETAINED':['Return unverified, block kept','Возврат не подтверждён, блокировка сохранена'],'CLIENT-CONFIRMATION-TIMEOUT':['Computer did not confirm','Компьютер не подтвердил'],'CLIENT-STOP':['Stopped by the helper','Остановлено помощником'],
'TARGET-HTTPS-DNS-FAILED':['Reserve check failed','Проверка резерва не прошла'],'LAN-BASELINE-NOT-SOURCE':['Computer was not on the primary','Компьютер был не на основном'],'RESERVE-EXIT-NOT-DISTINCT':['Reserve exit equals primary','Выход резерва совпал с основным'],
'VENDOR-APPLY-FAILED':['GL.iNet did not apply the change','GL.iNet не применил изменение'],'POLICY-CHANGED-DURING-APPLY':['Rules changed during the switch','Правила изменились во время переключения'],'NATIVE-SYSTEM-001':['System check failed','Проверка системы не прошла'],
'TERMS-NOT-ACCEPTED':['Terms not accepted','Условия не приняты'],'RETURN-NOT-APPLICABLE':['Nothing to return','Возвращать нечего'],'SOURCE-NOT-HEALTHY':['Primary not healthy yet','Основной ещё не исправен'],
'JOURNAL-UNVERIFIED':['Journal unverified','Журнал не проверен'],'EXTERNAL-POLICY-CHANGE':['Changed from outside','Изменено извне'],'EXTERNAL-POLICY-CHANGE-RELEASED':['Changed from outside, block removed','Изменено извне, блокировка снята'],
'ROLLBACK-UNVERIFIED':['Return unverified','Возврат не подтверждён'],'ENVIRONMENT-EVIDENCE-UNAVAILABLE':['No data about the router','Нет данных о роутере'],'MONITOR-EVIDENCE-STALE':['Monitor data is old','Данные мониторинга устарели'],
'NATIVE-START-CERTIFICATION-REQUIRED':['Checked again at Start','Повторная проверка при запуске'],'OPERATOR-RETURN':['Returned on request','Возврат по запросу'],'PRIMARY-RECOVERED':['Primary recovered','Основной восстановился']
};
// Extra rows (states, reasons, notices, families) come from error_rows_extra.inc.js, which is loaded first.
(function(){
  var have={};ERROR_ROWS.forEach(function(r){have[r[0]]=true;});
  if(typeof ERROR_EXTRA_GROUPS!=='undefined')ERROR_EXTRA_GROUPS.forEach(function(g){ERROR_GROUPS.splice(g[0]==='state'?2:ERROR_GROUPS.length,0,g);});
  if(typeof ERROR_EXTRA_ROWS!=='undefined')ERROR_EXTRA_ROWS.forEach(function(r){if(!have[r[0]]){ERROR_ROWS.push(r);have[r[0]]=true;}});
  if(typeof ERROR_FAMILIES!=='undefined')ERROR_FAMILIES.forEach(function(f){var code=f[0]+'*';if(!have[code]){ERROR_ROWS.push([code].concat(f.slice(1)));have[code]=true;}});
})();
var ERROR_GROUP_OF={},errorTable=null,ERROR_TABLE_STATE={query:'',open:Object.create(null),selected:null};
try{
  var savedErrorState=JSON.parse(sessionStorage.getItem('homensai-vpn-error-table')||'null');
  if(savedErrorState&&typeof savedErrorState.query==='string'&&savedErrorState.query.length<=128){
    ERROR_TABLE_STATE.query=savedErrorState.query;
    Object.keys(savedErrorState.open||{}).slice(0,500).forEach(function(code){if(/^[A-Z0-9*-]{1,96}$/.test(code))ERROR_TABLE_STATE.open[code]=savedErrorState.open[code]===true;});
    if(typeof savedErrorState.selected==='string'&&/^[A-Z0-9*-]{1,96}$/.test(savedErrorState.selected))ERROR_TABLE_STATE.selected=savedErrorState.selected;
  }
}catch(error){}
function persistErrorTableState(){try{sessionStorage.setItem('homensai-vpn-error-table',JSON.stringify(ERROR_TABLE_STATE));}catch(error){}}
(function(){
  // Auto start blockers come from the dictionary of the Auto panel; they get a readable name and are grouped under Switching.
  var seen={};ERROR_ROWS.forEach(function(r){seen[r[0]]=true;});
  Object.keys(AUTO_BLOCKERS).forEach(function(code){
    if(seen[code])return;
    var nm=AUTO_NAMES[code]||(function(){var w=code.toLowerCase().split('-').join(' ');w=w.charAt(0).toUpperCase()+w.slice(1);return [w,w];})();
    ERROR_ROWS.push([code,'switch',nm[0],nm[1],AUTO_BLOCKERS[code][0],AUTO_BLOCKERS[code][1],AUTO_BLOCKERS[code][0]+' If it is still unclear, open Help → “The Auto button refuses to start”.',AUTO_BLOCKERS[code][1]+' Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».']);
  });
  // The eight pre-switch checks (Tests page) are explained here too, so their codes can be opened from there.
  Object.keys(PLAN_BLOCKERS).forEach(function(code){
    if(seen[code])return;var r=PLAN_BLOCKERS[code];
    ERROR_ROWS.push([code,'switch',r[0],r[1],r[2],r[3],'This is not a fault: the check has not been proven for this router yet. It turns green only after it is verified on this router (for the path of a computer: run the LAN helper). Monitoring does not need it.','Это не неисправность: проверка для этого роутера ещё не доказана. Она станет зелёной только после проверки именно на этом роутере (для пути компьютера: запустите LAN-помощник). Для мониторинга она не нужна.']);
  });
  ERROR_ROWS.forEach(function(r){ERROR_GROUP_OF[r[0]]=r[1];});
})();
function renderErrorTable(){
  var search=E('input',{'type':'search','class':'hv-search','placeholder':bi('Search a code or a word','Поиск по коду или слову'),'aria-label':bi('Search error codes','Поиск по кодам ошибок')});
  var host=E('div',{'class':'hv-errtable'});
  search.value=ERROR_TABLE_STATE.query;
  function matches(r,q){return !q||(r.join(' ')).toLowerCase().indexOf(q)>=0;}
  function draw(){
    while(host.firstChild)host.removeChild(host.firstChild);
    var q=search.value.trim().toLowerCase();
    ERROR_TABLE_STATE.query=search.value;
    persistErrorTableState();
    ERROR_GROUPS.forEach(function(g){
      var rows=ERROR_ROWS.filter(function(r){return r[1]===g[0]&&matches(r,q);});
      if(!rows.length)return;
      host.appendChild(E('h4',{},bi(g[1][0],g[1][1])+' ('+rows.length+')'));
      var table=E('table',{'class':'table hv-errors'},[E('tr',{},[E('th',{},bi('Code','Код')),E('th',{},bi('Name','Название')),E('th',{},bi('What it means','Что означает')),E('th',{},bi('What to do','Что делать'))])]);
      rows.forEach(function(r){
        var fixRow=null;
        var expanded=ERROR_TABLE_STATE.open[r[0]]===true;
        var button=(r[6]||r[8])?E('button',{'type':'button','class':'cbi-button','aria-expanded':expanded?'true':'false','click':function(){var open=fixRow.hidden;fixRow.hidden=!open;ERROR_TABLE_STATE.open[r[0]]=open;persistErrorTableState();button.setAttribute('aria-expanded',open?'true':'false');button.textContent=open?bi('Hide','Скрыть'):bi('How to fix','Как исправить');}},expanded?bi('Hide','Скрыть'):bi('How to fix','Как исправить')):null;
        table.appendChild(E('tr',{'data-error-code':r[0],'class':ERROR_TABLE_STATE.selected===r[0]?'hv-err-selected':null},[E('td',{},E('code',{},r[0])),E('td',{},E('strong',{},bi(r[2],r[3]))),E('td',{},bi(r[4],r[5])),E('td',{},button||E('span',{'class':'hv-muted'},bi('See the message','См. сообщение')))]));
        if(r[6]||r[8]){fixRow=E('tr',{'class':'hv-errfix'},[E('td',{'colspan':'4'},[r[6]?E('p',{},[E('strong',{},bi('How to fix: ','Как исправить: ')),bi(r[6],r[7])]):null,r[8]?E('p',{'class':'hv-errexample'},[E('strong',{},bi('Example: ','Пример: ')),bi(r[8],r[9])]):null].filter(Boolean))]);fixRow.hidden=!expanded;table.appendChild(fixRow);}
      });
      host.appendChild(table);
    });
    if(!host.firstChild)host.appendChild(E('p',{},bi('No code matches. Try a shorter word.','Ничего не найдено. Попробуйте более короткое слово.')));
  }
  search.addEventListener('input',draw);draw();
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Error code table','Таблица кодов ошибок')),E('p',{},bi('Every code the program can show: its name, what it means and, under the button, how to fix it. A code tells what was observed; the cause may stay unknown.','Все коды, которые может показать программа: название, что означает и, под кнопкой, как исправить. Код говорит о том, что наблюдалось; причина может остаться неизвестной.')),(typeof errorExamples==='function'?errorExamples():null),search,host].filter(Boolean));
}

/* Page design: A Control room, B Calm (default), C Instrument panel. Router defaults come from setup;
   an explicit choice in Settings overrides them in this browser without changing other saved choices. */
var HV_DESIGNS=[
  {key:'a',name:['A · Control room','A · Пульт'],
   about:['Sections as tabs across the top, full width for the content. Status, failover path and servers stay where they are now.','Разделы вкладками сверху, вся ширина отдана содержимому. Статус, путь переключения и серверы на привычных местах.'],
   suits:['Everyone who prefers the full control-room layout.','Всем, кто предпочитает полный вид пульта.']},
  {key:'b',name:['B · Calm','B · Спокойный'],
   about:['Larger text and more space. Administrator sections are hidden behind “Advanced”; on a phone the sections sit at the bottom of the screen.','Крупнее текст и больше воздуха. Разделы для администратора спрятаны за «Расширенное»; на телефоне разделы внизу экрана.'],
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

/* Owner attributes: product name, device, developer, version/package/page and style. Shown at the bottom of every page in every design; no design may hide it. */
var HV_STYLE_VERSION='HomenS.AI Style 1.14.3';
function renderAttribution(status){
  return E('div',{'class':'hv-attribution','data-hv-attribution':'1','aria-label':bi('About this program','О программе')},[
    E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI'),' Auto VPN']),
    E('span',{},routerModelLabel()),
    E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),
    E('span',{'class':'hv-attribution-version'},identityLine(status||{})),
    E('span',{},HV_STYLE_VERSION),
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
  if(status.rpc_error||!Number.isFinite(status.time)||m.now-status.time<0||m.now-status.time>90){result.label=bi('No fresh confirmation','Нет свежего подтверждения');return result;}
  if(h.state==='failed'){result.kind='red';result.state='failed';return result;}
  if(h.state==='inactive'){result.label=bi('Off','Отключён');result.kind='red';result.state='off';return result;}
  if(h.state==='checking'){result.kind='yellow';result.state='checking';return result;}
  var ns=status.native_failover||{};
  if(['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0&&Number.isFinite(ns.time)&&m.now-ns.time>=0&&m.now-ns.time<=30){result.kind='yellow';result.state='switching';result.label=bi('Switching','Переключение');return result;}
  if(h.state==='healthy'){
    if(m.selected===profile.id){result.kind='green';result.state='selected';result.label=bi('Working','Работает');}
    else if(m.selected){result.kind='yellow';result.state='standby';result.label=bi('Waiting','Ожидает');}
    else result.label=bi('Connected; route unconfirmed','Подключён; путь не подтверждён');
  }
  return result;
}
function dvChannelLamp(use){return E('span',{'class':'hv-check-lamp hv-check-'+use.kind,'role':'img','aria-label':use.label,'title':use.label});}
function channelDisplayUse(profile,status,inventory){
  var now=Date.now()/1000,settings=(inventory||{}).settings||{},m={now:now,settings:settings,
    primary:vendorDisplayMember(status,inventory,'source',now),reserve:vendorDisplayMember(status,inventory,'target',now),selected:vendorDisplaySelected(status,inventory,now)};
  return dvChannelUse(profile,m,status);
}
function renderChannelHeader(profile,status,inventory){
  var use=channelDisplayUse(profile,status,inventory);
  return E('div',{'class':'hv-server-top'},[dvChannelLamp(use),E('strong',{'class':'hv-protocol'},use.role+' · '+protocolLabel(profile)),
    E('span',{'class':'hv-route-badge hv-route-'+use.kind,'data-route-state':use.state},use.label+(safeCode(profile.code)?' · '+profile.code:'')),
    E('span',{'class':'hv-profile-detail'},bi('Tunnel: ','Туннель: ')+(profile.interface?bi('Connected','Подключён'):bi('Off','Отключён'))+' · '+bi('Traffic: ','Трафик: ')+(use.state==='selected'?bi('Selected channel','Выбранный канал'):use.state==='standby'?bi('Standby','Ожидание'):bi('Unconfirmed','Не подтверждён')))]);
}
function dvCodes(codes){codes=codes.filter(safeCode);return codes.length?E('code',{'class':'hv-dv-code'},codes.join(' · ')):null;}
// One model for all designs: what the page says about the system right now.
function dvModel(status,inventory,rows,month){
  var now=Date.now()/1000,settings=(inventory||{}).settings||{},light=autoLightModel(status,inventory,now),counts=serverCounts(status,inventory,rows,now);
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
  return E('div',{'class':'hv-dv hv-dv-a'},[strip,E('div',{'class':'hv-dv-cols'},[E('div',{'class':'hv-dv-stack'},[control,servers]),events])]);
}

/* ---------- B · Calm ---------- */
function renderDesignB(ctx,m){
  var stats=E('div',{'class':'hv-dv-three'},[dvKpi(bi('VPN links ready','Доступные VPN-подключения'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
    dvKpi(bi('Problems today','Проблемы сегодня'),m.passPercent==null?bi('No data','Нет данных'):m.passPercent>=99.5?bi('None','Нет'):bi('Some','Есть')),dvKpi(bi('Used this month','Использовано за месяц'),m.traffic)]);
  var list=E('div',{'class':'hv-dv-list'},sortServerCards(ctx.rows,m.selected,m.now).map(function(p){
    var h=profileHealth(p,m.now),country=countryOf(p),use=dvChannelUse(p,m,ctx.status),role=use.role,kind=use.kind;
    return E('div',{'class':'hv-dv-item','data-profile':p.id},[E('span',{'class':'hv-dv-flag','aria-hidden':'true'},country?country.code.toUpperCase():'··'),
      E('div',{},[E('b',{},countryName(p)||customName(p)||protocolLabel(p)),E('small',{},role+' · '+protocolLabel(p))]),
      E('span',{'class':'hv-dv-statuscol','data-health':h.state,'data-route-state':use.state},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('span',{},use.label)])]);
  }));
  var autoOn=m.light.key==='ok';
  var q1=m.primary?E('div',{'class':'hv-dv-q'},[E('b',{},bi('What happens if '+(countryName(m.primary)||'the primary')+' stops working?','Что будет, если '+(countryName(m.primary)||'основной')+' перестанет работать?')),
    E('p',{},autoOn?bi('The app can consider a reserve only within a validated bounded trial, with router firmware coordination and independent LAN confirmation. Router probes alone do not authorize a switch.','Приложение может рассматривать резерв только в подтверждённом ограниченном тесте, с координацией со штатной прошивкой и независимым подтверждением LAN. Одних проверок с роутера недостаточно для разрешения переключения.'):bi('Automatic inter-tunnel switching by this app is off. The router firmware may still select servers within its own tunnel.','Автоматическое переключение между туннелями этим приложением выключено. Штатная прошивка по-прежнему может выбирать серверы внутри своего туннеля.'))]):null;
  var last=dvEvents(ctx.status,ctx.rows,1)[0];
  var q2=E('div',{'class':'hv-dv-q'},[E('b',{},bi('Last thing that happened','Последнее событие')),E('p',{},last?dvDay(last.time)+' '+dvClock(last.time)+' · '+last.text:bi('No switches or failures are recorded on the router.','На роутере не записано ни переключений, ни сбоев.'))]);
  var links=E('p',{'class':'hv-dv-links'},[E('a',{'href':'#statistics'},bi('Statistics','Статистика')),E('a',{'href':'#help'},bi('Help','Помощь')),E('a',{'href':'#learn'},bi('Training','Обучение')),E('a',{'href':'#events'},bi('Details for technicians →','Подробности для техников →'))]);
  // The state sentence block was removed (owner): the Primary/Reserve boxes in the Auto card already show it.
  return E('div',{'class':'hv-dv hv-dv-b'},[E('div',{'class':'hv-dv-control'},[ctx.controlCard]),stats,E('h3',{'class':'hv-dv-h'},bi('Your VPNs','Ваши VPN')),list,q1,q2,links].filter(Boolean));
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
  return E('div',{'class':'hv-dv hv-dv-c'},[bar,E('div',{'class':'hv-dv-grid'},[chartCard,log]),E('div',{'class':'hv-dv-control'},[ctx.controlCard]),table,keys]);
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
  var now=Date.now()/1000,model=autoControlModel(status,now),id=identityModel(status);
  var monitorFresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var state=!model.fresh?'unknown':(model.on||model.transitioning)?'on':'off';
  var autoText=state==='on'?bi('Auto ON','Auto вкл.'):state==='off'?bi('Auto OFF','Auto выкл.'):bi('Auto: ?','Auto: ?');
  var autoHint=state==='on'?bi('Auto is on: it can switch to the reserve VPN.','Auto включён: он может переключить на резервный VPN.'):state==='off'?bi('Auto is off: nothing is switched, the program only watches.','Auto выключен: ничего не переключается, программа только наблюдает.'):bi('No fresh data from the router, so the state is not known.','Нет свежих данных от роутера, поэтому состояние неизвестно.');
  var monText=bi('Monitoring','Мониторинг');
  var monHint=monitorFresh?bi('Monitoring works: fresh data from the router.','Мониторинг работает: свежие данные от роутера.'):status.rpc_error?bi('The router does not answer.','Роутер не отвечает.'):bi('Monitoring is not sending data.','Мониторинг не присылает данные.');
  function lamp(kind,text,hint){return E('span',{'class':'hv-side-lamp','role':'status','title':hint},[E('span',{'class':'hv-auto-pill-knob hv-lamp-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-auto-pill-text'},text),E('span',{'class':'hv-visually-hidden'},' — '+hint)]);}
  host.appendChild(E('div',{'class':'hv-side-lamps'},[lamp(state,autoText,autoHint),lamp(monitorFresh?'on':'off',monText,monHint)]));
  host.appendChild(E('p',{'class':'hv-side-version'},[bi('Version ','Версия '),E('strong',{},id.agent||id.uiAgent)]));
}

/* Help topic "Prompt for your AI agent": one complete prompt the owner copies into any AI agent that has a terminal.
   The text is written for the agent. It must never contain a secret. No template placeholders with dollar-brace and no backticks inside. */
var AI_PROMPT_EN=`You are an installation engineer. Install, verify and start MONITORING of the experimental software "HomenS.AI Auto VPN" on the owner's GL.iNet GL-MT6000 (Flint 2) or GL-MT3000 (Beryl AX) router, step by step, and report honestly. The owner is not a specialist: explain each step in one or two plain sentences, do the work yourself, and ask the owner only for the things listed in "ASK THE OWNER".

PROJECT: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (MIT license, experimental alpha). It is a LuCI page and a small program (Python + Lua) on the router. It watches the VPN profiles the owner already created in GL.iNet and, only if the owner turns Auto on later, can move traffic from a primary VPN to a reserve VPN and back. In this task you install it in MONITOR mode only.

=== 0. HARD RULES (never break them) ===
0.1 Experimental software: it can interrupt the internet and it changes router VPN settings when Auto is on. BEFORE anything else show the owner this notice and ask them to answer exactly "I accept the risk": the software is experimental, provided "AS IS" without warranty, used at the owner's own risk; the owner has a backup plan and another way to reach the internet (for example a phone with mobile data). Full text: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/DISCLAIMER.md . If the owner does not accept, stop.
0.2 MONITOR mode only. NEVER enable Auto, never set native_enabled=1, never run the LAN trial yourself, never type the word TEST for the owner in this default installation. A separate explicit repair/switch-test authorization may be exercised within its exact scope after the real platform and bounded proof checks. The owner themselves accept the terms in the web page and, much later and only if they want, run the LAN helper.
0.3 In monitor-only installation do not change router routes, DNS, firewall, network, Wi-Fi, DHCP, VPN profiles or keys. A separately authorized dedicated-router repair/test window may change only necessary router parameters, with backup, reason, before/after and actual verification recorded. Host/primary-router changes need separate scope. Never force package/module removal, factory reset, expose administration or flash firmware without specific recovery/image approval.
0.4 SECRETS: never print, log, store in a file inside any project folder, or send anywhere the router password, SSH keys, Telegram bot token, VPN keys or config files. Never ask the owner to paste a password or a token into this chat. If the owner already pasted one, tell them to change it afterwards. When showing configuration use redaction, for example: uci show homensai_vpn | sed "s/telegram_token=.*/telegram_token=<hidden>/".
0.5 At a FAIL/refusal stop dependent writes, preserve evidence and diagnose/repair within the approved scope. Report exact observed codes and distinguish verified causes from hypotheses. Never repeat risky commands blindly or relabel failed/partial evidence PASS.
0.6 Obtain authorization for a new scope; do not ask again for changes already explicitly authorized in this session. Read-only checks need no extra permission. After every critical/long operation save a Git checkpoint and current done/not-done state, evidence, causes, corrections and limits. Never commit private data.

=== 1. ASK THE OWNER (one question at a time) ===
1.1 Do they accept the notice in 0.1? (answer "I accept the risk")
1.2 The router address (default 192.168.8.1) and confirmation that the owner is connected to this router by cable or Wi-Fi.
1.3 Which operating system is the computer you work on (Windows / macOS / Linux) and may you create a private working folder outside any Git repository, for example ~/homensai-install-private (Windows: C:\\Users\\<name>\\homensai-install-private).
1.4 Is SSH enabled on the router? If not, guide them: GL.iNet admin panel (http://192.168.8.1) -> System -> Security -> allow SSH from the local network; or LuCI (http://192.168.8.1:8080/cgi-bin/luci/) -> System -> Administration -> SSH Access (interface lan). The login is root and the password is the same as for the GL.iNet panel. Menu names can differ a little between firmware versions.

=== 2. ACCESS TO THE ROUTER WITHOUT EXPOSING THE PASSWORD ===
Preferred (key login):
2.1 In the private folder create a key: ssh-keygen -t ed25519 -f ./router_key -N "" . Show the owner ONLY the public key file router_key.pub.
2.2 Ask the owner to add that public key in LuCI -> System -> Administration -> SSH-Keys (paste, Save). This is the one moment the owner types the router password, in their own browser.
2.3 Test: ssh -i ./router_key -o StrictHostKeyChecking=accept-new root@ROUTER_IP "echo connected". Pin the host key in a known_hosts file inside the private folder (-o UserKnownHostsFile=./known_hosts). Remember: OpenWrt scp needs the -O flag (scp -O).
Fallback (password): the owner creates a text file in the private folder containing only the password, and you use it through an SSH_ASKPASS helper (SSH_ASKPASS_REQUIRE=force) with PubkeyAuthentication=no. Never print that file. Delete it when the task ends and remind the owner to change the router password if it was ever visible to anyone.

=== 3. READ-ONLY CHECKS OF THE ROUTER ===
Run and record the results (no secrets in them):
3.1 ubus call system board   (MT6000: glinet,gl-mt6000; MT3000: glinet,mt3000-snand). Record actual model, firmware and board; a selected label is not hardware evidence.
3.2 cat /etc/glversion   (observed firmware4.11.0). Monitoring is available for these two detected boards. MT3000 switching stays gated until its actual adapter/trial passes. Choose Automatic detection or the matching model in the first setup step. Unknown board/firmware stays unverified.
3.3 opkg status homensai-auto-vpn   (installed version or none)
3.4 for p in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do opkg status $p | grep -q "^Status:.*installed" && echo "ok $p" || echo "MISSING $p"; done   (if something is missing, install ONLY from the original vendor feeds with: opkg update && opkg install <package>, after asking the owner; never force)
3.5 df -k /overlay ; awk "/MemAvailable/{print}" /proc/meminfo   (need at least 20 MB free storage; Python is the largest part)
3.6 nft list table inet homensai_vpn_guard   (should say it does not exist; if it exists, STOP and show EMERGENCY.md from the kit)
3.7 uci -q get homensai_vpn.main.native_enabled   (must be empty or 0)
3.8 ls /etc/homensai-vpn/native-transaction.json   (if it exists the router was used for an earlier switching trial: read it carefully, see 5.3)
3.9 uci show route_policy | grep -E "=rule|name=|via=|enabled="   (only to understand how many VPN profiles/rules exist; do not change anything)

3.10 Before an authorized switching trial verify disabled HNAT configuration AND runtime hook, and absent software acceleration. Loaded HNAT alone proves neither state. Recovery first; inspect/pin stock controls; no forced module removal. Record before/after and why each change was needed.
3.11 Stock MT3000 FW3 needs complete fw3.state and vpnclient.reload=0. Normal reload is not restart/start; no lock deletion or arbitrary worker kills. Connected/empty queues do not prove DNS/HTTPS or service success. See docs/MT3000-OPERATIONS-2026-10-22.md.
3.12 The LAN helper binds DNS/HTTPS to interface/source without host route edits. CheckOnly is read-only. Windows IgnoreDefaultRoutes can block cable tests despite a reachable router; do not change Windows/Wi-Fi/routes without separate permission. Hosted namespace checks cannot become an external-LAN certificate.

3.13 If DNS fails while HTTPS works, inspect every actual upstream/listener and DNS-owner state. An enabled but nonrunning AdGuardHome with DNS disabled can still cause DNS_BUSY and leave dnsmasq pointing to absent localhost3053. Under explicit repair authority, resolve only that inactive owner and save DNS via the stock API in memory; verify VPN DNS override choice and real DNS/HTTPS. Preserve a working filtering owner. Do not equate flags/API exit with repaired traffic.

3.14 Audited MT3000 native profile requires board glinet,mt3000-snand, target mediatek/mt7981, kernel5.4.211/aarch64, firmware4.11.0, exact stock sources, complete FW3 zones/include and quiet workers. Monitor-only remains a separate deployment choice; choosing a model grants no route rights.
3.15 RTP derives gl_process_vpn via/mark from the first enabled VPN rule, and backgrounds firewall reload plus DNS restart even with not_reload_network. Bind only the exact selected pair in policy/journal; wait for real quiet and DNS/HTTPS. A router-hosted IPv4 trial is explicitly scoped and never an external-LAN certificate. The LAN helper starts a fresh private calibration through native_trial_start so an old Stop is not erased or silently bypassed.

3.16 Before a separately authorized OpenVPN cold start, inspect any PID-file residue against fresh inode/mtime/process identity. A stale numeric PID can belong to an unrelated process. Never kill by that file blindly; quarantine only the exact proven-dead owned residue, preserve the evidence and verify both clients/configuration. Monitoring installation never performs this repair automatically.

=== 4. DOWNLOAD AND VERIFY THE PACKAGE ===
4.1 Open https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases and choose the newest pre-release (the highest "alpha" number). Call its tag TAG (for example v0.8.0-alpha15) and its version VERSION (for example 0.8.0-alpha15). Confirm the tag page exists: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/TAG
4.2 Download into the private folder:
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk.sha256
  and the kit scripts of the SAME tag (raw files): https://raw.githubusercontent.com/HomenSAI/homensai-gl-mt6000-auto-vpn/TAG/router-test-kit/01-preflight.sh , 02-install.sh , 03-verify.sh , 05-emergency.sh , EMERGENCY.md in the same folder.
4.3 Verify: compute the SHA256 of the .ipk (sha256sum, shasum -a 256, or Windows: Get-FileHash -Algorithm SHA256) and compare with the .sha256 file AND with EXPECTED_SHA inside 02-install.sh. They must be identical. If anything differs or is missing, STOP.
4.4 Read the scripts you are going to run (01, 02, 03, 05) and tell the owner in one paragraph what they do: preflight is read-only; install is "opkg install" of this one verified package with no force flags; verify is read-only.

=== 5. BACKUP, PREFLIGHT, INSTALL (ask the owner first) ===
5.1 Capture a supported configuration export in process memory, validate archive entries, encrypt immediately with authenticated encryption and an OS-protected key, then independently decrypt/read in memory. Persist only ciphertext and the protected key outside Git. Record hashes and recovery scope. Never write a plaintext configuration/key/password backup or treat file size as recovery proof.
5.2 Copy to the router: scp -O 01-preflight.sh 02-install.sh 03-verify.sh 05-emergency.sh homensai-auto-vpn_VERSION-1_all.ipk root@ROUTER_IP:/tmp/
5.3 Run: ssh ... "cd /tmp && sh 01-preflight.sh" . It must end with "READY to continue". If its only FAIL is an old transaction journal (native journal phase HELD-ON-RESERVE or similar) from an earlier trial: show the owner the journal phase, ask whether they restored their VPN rule order by hand in the GL.iNet panel, and only after a clear YES archive (MOVE, never delete) the journal: mv /etc/homensai-vpn/native-transaction.json /etc/homensai-vpn/native-transaction.closed-DATE.json . Then run preflight again. Any other FAIL: STOP and report.
5.4 Install: ssh ... "cd /tmp && sh 02-install.sh /tmp/homensai-auto-vpn_VERSION-1_all.ipk"
5.5 Verify: ssh ... "cd /tmp && sh 03-verify.sh wait" . It must end with "RESULT: PASS" (package version, agent version, fresh status, Auto OFF, no owned guard, one monitor process, network/firewall/route fingerprint unchanged). If not, STOP, show the output, and offer the recovery in router-test-kit/EMERGENCY.md. Uninstall, if the owner wants it: opkg remove homensai-auto-vpn (settings stay).

=== 6. START MONITORING ===
6.1 Monitoring is meant to be always on and starts by itself after installation. Check: uci -q get homensai_vpn.main.enabled . If it is not 1 start it: ubus call homensai-vpn monitor_control "{\\"enabled\\":true}" (or the owner presses "Start monitoring" in the Monitoring block on the Overview page, which is shown only when monitoring is not running). Wait up to 90 seconds.
6.2 Confirm with evidence, not hope: ps w | grep "[a]gent.py daemon" shows one process; ubus call homensai-vpn status | jsonfilter -e "@.version" -e "@.time" shows the new version and a time within the last 90 seconds; ubus call homensai-vpn status | jsonfilter -e "@.profiles[*].name" lists the VPN profiles the monitor sees. A queued or "accepted" request alone is NOT proof that it runs.
6.3 Auto must remain OFF: uci -q get homensai_vpn.main.native_enabled must be 0 or empty.

=== 7. THE OWNER'S PART IN THE BROWSER (guide them, do not do it for them) ===
7.1 Open http://ROUTER_IP:8080/cgi-bin/luci/ -> sign in as root -> Services -> HomenS.AI Auto VPN. Hard refresh with Ctrl+F5 (after an upgrade also sign out and in once).
7.2 The first screen shows the terms of use. The owner reads them and ticks both boxes themselves. You never accept the terms for them.
7.3 Left menu -> Training: a 5-minute interactive course (what it is, how to use it, what to do if the internet is gone). Recommend it.
7.4 Overview: the block next to "Check the VPNs now" must say "Monitoring is on" with a green lamp and numbers of checks; the charts appear on the Statistics page after a few minutes.
7.5 Settings -> Setup -> 1 System (the wizard): read the profile list from the router (step 6.2), suggest a primary and a reserve in DIFFERENT countries or providers, and let the owner choose and press Save after the review. Do not ask for VPN keys and do not start inactive profiles. Saving settings does NOT give permission to switch.
7.6 TELEGRAM (optional, report every 60 minutes; failures and switches are included): the owner does it, you only guide: (a) in Telegram open https://t.me/BotFather and send /newbot, choose a name and a username ending in "bot", and copy the token that BotFather gives (digits, a colon, then letters); (b) open the new bot and press Start (a bot cannot write first); (c) find the chat ID: write to https://t.me/userinfobot and copy the number after "Id" (a group id starts with a minus sign, a public channel can be @channelname); (d) in the router page: Settings -> Setup -> 2 Telegram: paste the token and the chat ID, choose the interval (60 minutes is good) and a daily hour (for example 8), review, Save; (e) press "Test Telegram delivery" and confirm the message arrived. The token goes ONLY into that form, never into this chat. If the test fails the page shows a TELEGRAM-... code; see the "Error code table" on the Events and errors page (Advanced menu).

=== 8. FINAL REPORT ===
Write a short report with three lists: VERIFIED (with the command output or the screen you saw), NOT VERIFIED (be explicit: for example hardware switching, the LAN path of a computer, DNS and Kill Switch behaviour, IPv6, power loss, 24-hour stability), and THE OWNER'S NEXT STEPS. Include: package version, the sha256, monitor status, the profiles seen, Telegram delivery result, where the private backup is, how to stop only this program (ssh ... "sh /tmp/05-emergency.sh stop-auto" or opkg remove homensai-auto-vpn), how to start it again, and the emergency document router-test-kit/EMERGENCY.md. Remind the owner to change the router password if it was ever shared, and to delete the private working folder when no longer needed.

=== 9. IF SOMETHING GOES WRONG ===
9.1 No internet after any step: tell the owner to use their phone; the monitor mode does not change routes, so first check the GL.iNet panel VPN Dashboard (primary rule first, tunnels connected). Then run read-only: ssh ... "sh /tmp/05-emergency.sh show" (copy the kit again if /tmp was cleared by a reboot).
9.2 The page shows 403, is empty or old: try a private browser window, press Ctrl+F5, sign out of LuCI and in again. Do not weaken security and do not restart rpcd again and again.
9.3 The web Help page on the router (Help in the left menu) has step-by-step topics for the same situations.

=== 10. LATER, ONLY IF THE OWNER ASKS FOR AUTOMATIC SWITCHING ===
Explain, do not perform: Auto switches between exactly two VPN profiles (primary and reserve). It needs a passed LAN trial: the owner runs the LAN helper (a PowerShell 7 script, see https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/LAN-HELPER.en.md) from a computer connected by a LAN cable, first in check-only mode, and types the word TEST themselves. Every automatic switch must be confirmed by that helper, otherwise the router returns after 90 seconds. Unattended Auto is not supported yet. Hardware acceptance of the switching on a real GL-MT6000 is still incomplete: say so plainly.

Begin now with 0.1.`;
var AI_PROMPT_RU=`Вы — инженер по установке. Установите, проверьте и запустите МОНИТОРИНГ экспериментальной программы «HomenS.AI Auto VPN» на роутере владельца GL.iNet GL-MT6000 (Flint 2) или GL-MT3000 (Beryl AX) шаг за шагом и честно отчитайтесь. Владелец не специалист: объясняйте каждый шаг одним-двумя простыми предложениями, всю работу делайте сами и спрашивайте владельца только о том, что перечислено в разделе «СПРОСИТЕ ВЛАДЕЛЬЦА».

ПРОЕКТ: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (лицензия MIT, экспериментальная альфа). Это страница LuCI и небольшая программа (Python + Lua) на роутере. Она следит за VPN-профилями, которые владелец уже создал в GL.iNet, и только если владелец позже включит Auto, может переводить трафик с основного VPN на резервный и обратно. В этой задаче вы ставите её только в режиме МОНИТОРИНГА.

=== 0. ЖЁСТКИЕ ПРАВИЛА (не нарушать никогда) ===
0.1 Экспериментальное ПО: может прервать интернет и при включённом Auto меняет настройки VPN роутера. ПЕРВЫМ ДЕЛОМ покажите владельцу это уведомление и попросите ответить ровно: «Я принимаю риск»: программа экспериментальная, предоставляется «КАК ЕСТЬ» без гарантий, используется на собственный риск; у владельца есть план отката и другой способ выйти в интернет (например, телефон с мобильным интернетом). Полный текст: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/DISCLAIMER.ru.md . Если владелец не принимает, остановитесь.
0.2 ТОЛЬКО режим мониторинга. НИКОГДА не включайте Auto, не ставьте native_enabled=1, не запускайте LAN-тест сами, не вводите слово TEST вместо владельца. Условия использования в веб-странице принимает сам владелец, а LAN-помощника он запускает позже и только если захочет.
0.3 При установке только мониторинга не меняйте маршруты, DNS, firewall, сеть, Wi-Fi, DHCP, VPN-профили и ключи. В отдельно разрешённом окне ремонта/испытаний выделенного роутера меняйте только необходимые параметры, записывая backup, причину, состояние до/после и проверку. Компьютер и основной роутер требуют отдельной области разрешения. Без отдельного согласования восстановления/образа не применяйте принудительное удаление пакетов/модулей, заводской сброс, внешнее управление или прошивку.
0.4 СЕКРЕТЫ: никогда не выводите, не журналируйте, не сохраняйте в файлах внутри папок проекта и никуда не отправляйте пароль роутера, SSH-ключи, токен Telegram-бота, VPN-ключи и конфиги. Никогда не просите владельца вставить пароль или токен в этот чат. Если владелец уже вставил, скажите сменить его потом. Показывая настройки, скрывайте секреты, например: uci show homensai_vpn | sed "s/telegram_token=.*/telegram_token=<hidden>/".
0.5 При FAIL/отказе остановите зависимые записи, сохраните доказательства и исследуйте/исправьте причину в разрешённых границах. Записывайте наблюдаемые коды, отделяйте доказанные причины от гипотез. Не повторяйте рискованные команды вслепую и не называйте неудачные/частичные проверки PASS.
0.6 Получайте разрешение на новую область; повторно не спрашивайте об изменениях, уже явно разрешённых в сессии. Чтение дополнительного разрешения не требует. После каждой важной/длительной операции сохраняйте коммит Git и состояние: сделано/не сделано, доказательства, причины, исправления и ограничения. Закрытые данные в Git не включайте.

=== 1. СПРОСИТЕ ВЛАДЕЛЬЦА (по одному вопросу) ===
1.1 Принимает ли он уведомление из 0.1? (ответ «Я принимаю риск»)
1.2 Адрес роутера (по умолчанию 192.168.8.1) и подтверждение, что владелец подключён к этому роутеру кабелем или по Wi-Fi.
1.3 Какая операционная система на компьютере, где вы работаете (Windows / macOS / Linux), и можно ли создать закрытую рабочую папку вне любого Git-репозитория, например ~/homensai-install-private (Windows: C:\\Users\\<имя>\\homensai-install-private).
1.4 Включён ли SSH на роутере? Если нет, проведите владельца: панель GL.iNet (http://192.168.8.1) -> Система -> Безопасность -> разрешить SSH из локальной сети; либо LuCI (http://192.168.8.1:8080/cgi-bin/luci/) -> System -> Administration -> SSH Access (интерфейс lan). Логин root, пароль тот же, что для панели GL.iNet. Названия меню могут немного отличаться в разных версиях прошивки.

=== 2. ДОСТУП К РОУТЕРУ БЕЗ РАСКРЫТИЯ ПАРОЛЯ ===
Предпочтительно (вход по ключу):
2.1 В закрытой папке создайте ключ: ssh-keygen -t ed25519 -f ./router_key -N "" . Показывайте владельцу ТОЛЬКО публичный ключ router_key.pub.
2.2 Попросите владельца добавить этот публичный ключ в LuCI -> System -> Administration -> SSH-Keys (вставить, Save). Это единственный момент, когда владелец вводит пароль роутера, в своём браузере.
2.3 Проверка: ssh -i ./router_key -o StrictHostKeyChecking=accept-new root@АДРЕС_РОУТЕРА "echo connected". Закрепите ключ хоста в файле known_hosts внутри закрытой папки (-o UserKnownHostsFile=./known_hosts). Помните: для scp на OpenWrt нужен флаг -O (scp -O).
Запасной путь (пароль): владелец сам создаёт в закрытой папке текстовый файл только с паролем, а вы используете его через помощник SSH_ASKPASS (SSH_ASKPASS_REQUIRE=force) с PubkeyAuthentication=no. Никогда не выводите этот файл. Удалите его в конце задачи и напомните владельцу сменить пароль роутера, если его кто-либо видел.

=== 3. ПРОВЕРКИ РОУТЕРА ТОЛЬКО НА ЧТЕНИЕ ===
Выполните и запишите результаты (без секретов):
3.1 ubus call system board   (MT6000: glinet,gl-mt6000; MT3000: glinet,mt3000-snand). Запишите фактическую плату, модель и прошивку; выбранное название не доказывает модель оборудования.
3.2 cat /etc/glversion   (наблюдалась прошивка4.11.0). Мониторинг доступен для двух обнаруженных плат. Переключение MT3000 заблокировано до проверки реального адаптера и теста. На первом шаге выберите автоопределение или совпадающую модель. Неизвестная плата/прошивка остаётся непроверенной.
3.3 opkg status homensai-auto-vpn   (установленная версия или нет)
3.4 for p in python3 lua lua-cjson libuci-lua ip-full ubus rpcd luci-base ca-bundle; do opkg status $p | grep -q "^Status:.*installed" && echo "ok $p" || echo "MISSING $p"; done   (если чего-то нет, ставьте ТОЛЬКО из оригинальных источников производителя: opkg update && opkg install <пакет>, после вопроса владельцу; никогда не принудительно)
3.5 df -k /overlay ; awk "/MemAvailable/{print}" /proc/meminfo   (нужно не менее 20 МБ свободного места; самый большой компонент — Python)
3.6 nft list table inet homensai_vpn_guard   (должно быть «не существует»; если существует, ОСТАНОВИТЕСЬ и покажите EMERGENCY.md из набора)
3.7 uci -q get homensai_vpn.main.native_enabled   (должно быть пусто или 0)
3.8 ls /etc/homensai-vpn/native-transaction.json   (если файл есть, роутер использовался для прежнего теста переключения: прочитайте внимательно, см. 5.3)
3.9 uci show route_policy | grep -E "=rule|name=|via=|enabled="   (только чтобы понять, сколько VPN-профилей и правил есть; ничего не меняйте)

3.10 Перед разрешённым переключением подтвердите выключенные конфигурацию И реальный hook HNAT, отсутствие программного ускорения. Загруженный HNAT не доказывает состояние ускорения. Сначала backup и проверка штатных скриптов; без принудительного удаления модулей. Записывайте состояние до/после и причину изменения.
3.11 Штатный FW3 на MT3000 требует полного fw3.state и vpnclient.reload=0. Обычный reload не равен restart/start; не удаляйте блокировки и не завершайте произвольные процессы. Connected и пустая очередь не доказывают DNS/HTTPS и успешную работу служб. См. docs/MT3000-OPERATIONS-2026-10-22.md.
3.12 LAN-помощник привязывает DNS/HTTPS к интерфейсу и адресу без изменения маршрутов компьютера. CheckOnly только читает. Windows IgnoreDefaultRoutes может блокировать тест при доступном роутере; не меняйте Windows/Wi-Fi/маршруты без отдельного разрешения. Тест namespace на роутере не подтверждает внешний LAN-клиент.

3.13 Если HTTPS работает, а DNS нет, проверьте реальные upstream/слушающие порты и владельца DNS. Включённый в настройках, но неработающий AdGuardHome с выключенным DNS может выдавать DNS_BUSY и оставлять dnsmasq на отсутствующем localhost3053. При явном разрешении ремонта устраните только неактивного владельца и сохраните DNS штатным API в памяти; проверьте подмену VPN DNS и реальные DNS/HTTPS. Работающий фильтр сохраняйте. Флаги и код выхода API не доказывают восстановление трафика.

3.14 Проверенный нативный профиль MT3000 требует плату glinet,mt3000-snand, target mediatek/mt7981, kernel5.4.211/aarch64, прошивку4.11.0, точные штатные исходники, полные зоны/include FW3 и завершение фоновой работы. Monitor-only остаётся отдельным режимом установки; выбор модели не даёт права менять маршруты.
3.15 RTP выводит via/mark gl_process_vpn из первого включённого VPN-правила и запускает фоновые firewall reload и DNS restart даже при not_reload_network. Привязывайте к хешу/журналу только точную выбранную пару; ждите реального покоя и DNS/HTTPS. Внутренний IPv4 тест роутера имеет отдельную область и не заменяет сертификат внешнего LAN. LAN-помощник начинает свежую приватную калибровку через native_trial_start, сохраняя прежний Stop и его защиту от запоздалого запуска.

3.16 Перед отдельно разрешённым холодным запуском OpenVPN сопоставьте остаточный PID-файл со свежими inode/mtime и процессом. Старый числовой PID может принадлежать чужому процессу. Не убивайте процесс вслепую; изолируйте только точный доказанно мёртвый остаток, сохраните доказательства и проверьте клиенты/конфигурацию. Обычная установка мониторинга не выполняет этот ремонт автоматически.

=== 4. СКАЧАТЬ И ПРОВЕРИТЬ ПАКЕТ ===
4.1 Откройте https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases и выберите самый новый пре-релиз (с наибольшим номером «alpha»). Назовите его тег TAG (например v0.8.0-alpha15), а версию VERSION (например 0.8.0-alpha15). Убедитесь, что страница тега существует: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/TAG
4.2 Скачайте в закрытую папку:
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk
  https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/download/TAG/homensai-auto-vpn_VERSION-1_all.ipk.sha256
  и скрипты набора ТОГО ЖЕ тега (сырые файлы): https://raw.githubusercontent.com/HomenSAI/homensai-gl-mt6000-auto-vpn/TAG/router-test-kit/01-preflight.sh , 02-install.sh , 03-verify.sh , 05-emergency.sh , EMERGENCY.md в ту же папку.
4.3 Проверка: вычислите SHA256 файла .ipk (sha256sum, shasum -a 256 или в Windows Get-FileHash -Algorithm SHA256) и сравните с файлом .sha256 И с EXPECTED_SHA внутри 02-install.sh. Они должны совпасть. Если что-то отличается или отсутствует, ОСТАНОВИТЕСЬ.
4.4 Прочитайте скрипты, которые будете запускать (01, 02, 03, 05), и одним абзацем объясните владельцу, что они делают: предварительная проверка только читает; установка — это «opkg install» одного проверенного пакета без флагов принуждения; проверка только читает.

=== 5. РЕЗЕРВНАЯ КОПИЯ, ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА, УСТАНОВКА (сначала спросите владельца) ===
5.1 Получите штатный экспорт конфигурации в память процесса, проверьте архив, сразу зашифруйте с проверкой подлинности и ключом под защитой ОС, затем независимо расшифруйте/прочитайте в памяти. Сохраняйте только шифротекст и защищённый ключ вне Git. Запишите хеши и границы восстановления. Открытый backup конфигурации/ключей/паролей не создавайте; размер не доказывает восстановимость.
5.2 Копирование на роутер: scp -O 01-preflight.sh 02-install.sh 03-verify.sh 05-emergency.sh homensai-auto-vpn_VERSION-1_all.ipk root@АДРЕС_РОУТЕРА:/tmp/
5.3 Запуск: ssh ... "cd /tmp && sh 01-preflight.sh" . Он должен закончиться строкой «READY to continue». Если единственный FAIL — старый журнал транзакции (native journal phase HELD-ON-RESERVE или похожий) от прежнего теста: покажите владельцу фазу журнала, спросите, вернул ли он порядок VPN-правил вручную в панели GL.iNet, и только после ясного «ДА» архивируйте журнал (ПЕРЕМЕСТИТЕ, не удаляйте): mv /etc/homensai-vpn/native-transaction.json /etc/homensai-vpn/native-transaction.closed-ДАТА.json . Затем запустите проверку снова. Любой другой FAIL: ОСТАНОВИТЕСЬ и сообщите.
5.4 Установка: ssh ... "cd /tmp && sh 02-install.sh /tmp/homensai-auto-vpn_VERSION-1_all.ipk"
5.5 Проверка: ssh ... "cd /tmp && sh 03-verify.sh wait" . Должно закончиться «RESULT: PASS» (версия пакета, версия программы, свежий статус, Auto выключен, нет собственной блокировки, один процесс мониторинга, отпечаток сети/файрвола/маршрутов не изменился). Если нет, ОСТАНОВИТЕСЬ, покажите вывод и предложите восстановление из router-test-kit/EMERGENCY.md. Удаление, если захочет владелец: opkg remove homensai-auto-vpn (настройки сохраняются).

=== 6. ЗАПУСК МОНИТОРИНГА ===
6.1 Мониторинг должен быть всегда включён и стартует сам после установки. Проверьте: uci -q get homensai_vpn.main.enabled . Если не 1, запустите: ubus call homensai-vpn monitor_control "{\\"enabled\\":true}" (или владелец нажимает «Запустить мониторинг» в блоке «Мониторинг» на странице «Обзор», он показан только когда мониторинг не работает). Подождите до 90 секунд.
6.2 Подтвердите доказательствами, а не надеждой: ps w | grep "[a]gent.py daemon" показывает один процесс; ubus call homensai-vpn status | jsonfilter -e "@.version" -e "@.time" показывает новую версию и время не старше 90 секунд; ubus call homensai-vpn status | jsonfilter -e "@.profiles[*].name" перечисляет VPN-профили, которые видит мониторинг. Одна лишь принятая в очередь команда НЕ доказывает, что программа работает.
6.3 Auto должен остаться ВЫКЛЮЧЕННЫМ: uci -q get homensai_vpn.main.native_enabled должно быть 0 или пусто.

=== 7. ЧАСТЬ ВЛАДЕЛЬЦА В БРАУЗЕРЕ (направляйте, не делайте за него) ===
7.1 Откройте http://АДРЕС_РОУТЕРА:8080/cgi-bin/luci/ -> войдите как root -> Services -> HomenS.AI Auto VPN. Обновите страницу с Ctrl+F5 (после обновления версии ещё раз выйдите и войдите).
7.2 На первом экране условия использования. Владелец сам читает и отмечает оба флажка. Вы никогда не принимаете условия за него.
7.3 Левое меню -> «Обучение»: интерактивный курс на 5 минут (что это, как пользоваться, что делать, если пропал интернет). Рекомендуйте его.
7.4 «Обзор»: блок рядом с «Проверить VPN сейчас» должен писать «Мониторинг включён» с зелёной лампой и числом проверок; графики появятся на странице «Статистика» через несколько минут.
7.5 «Настройки» -> «Настройка» -> 1 · Система (мастер): прочитайте список профилей с роутера (шаг 6.2), предложите основной и резервный в РАЗНЫХ странах или у разных провайдеров, а выбрать и нажать «Сохранить» после обзора должен владелец. Не просите VPN-ключи и не запускайте неактивные профили. Сохранение настроек НЕ даёт разрешения на переключение.
7.6 TELEGRAM (по желанию, отчёт каждые 60 минут; отказы и переключения включены): делает владелец, вы только направляете: (а) в Telegram откройте https://t.me/BotFather и отправьте /newbot, выберите имя и username, оканчивающийся на «bot», и скопируйте токен, который выдаст BotFather (цифры, двоеточие, затем буквы); (б) откройте нового бота и нажмите Start (бот не может написать первым); (в) узнайте ID чата: напишите https://t.me/userinfobot и скопируйте число после «Id» (у группы ID начинается с минуса, публичный канал можно указать как @имя_канала); (г) на странице роутера «Настройки» -> «Настройка» -> 2 · Telegram вставьте токен и ID чата, выберите интервал (хорошо 60 минут) и час суток (например 8), проверьте обзор, «Сохранить»; (д) нажмите «Проверить доставку Telegram» и убедитесь, что сообщение пришло. Токен вводится ТОЛЬКО в эту форму, никогда в этот чат. Если тест не прошёл, страница покажет код TELEGRAM-...; см. «Таблицу кодов ошибок» на странице «События и ошибки» (меню «Расширенное»).

=== 8. ИТОГОВЫЙ ОТЧЁТ ===
Напишите короткий отчёт из трёх списков: ПРОВЕРЕНО (с выводом команды или экраном, который вы видели), НЕ ПРОВЕРЕНО (скажите прямо: например переключение на реальном железе, путь компьютера в LAN, DNS и Kill Switch, IPv6, потеря питания, устойчивость 24 часа) и СЛЕДУЮЩИЕ ШАГИ ВЛАДЕЛЬЦА. Включите: версию пакета, sha256, состояние мониторинга, увиденные профили, результат доставки в Telegram, где лежит закрытая копия, как остановить только эту программу (ssh ... "sh /tmp/05-emergency.sh stop-auto" или opkg remove homensai-auto-vpn), как запустить снова и аварийный документ router-test-kit/EMERGENCY.md. Напомните владельцу сменить пароль роутера, если его кто-либо видел, и удалить закрытую рабочую папку, когда она больше не нужна.

=== 9. ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК ===
9.1 Нет интернета после любого шага: скажите владельцу использовать телефон; режим мониторинга маршруты не меняет, поэтому сначала проверьте в панели GL.iNet VPN Dashboard (основное правило первым, туннели подключены). Затем только чтение: ssh ... "sh /tmp/05-emergency.sh show" (скопируйте набор снова, если /tmp очистился после перезагрузки).
9.2 Страница показывает 403, пустая или старая: откройте приватное окно браузера, нажмите Ctrl+F5, выйдите из LuCI и войдите снова. Не ослабляйте защиту и не перезапускайте rpcd снова и снова.
9.3 На странице роутера «Помощь» (в левом меню) есть пошаговые темы для тех же ситуаций.

=== 10. ПОЗЖЕ, ТОЛЬКО ЕСЛИ ВЛАДЕЛЕЦ ПРОСИТ АВТОМАТИЧЕСКОЕ ПЕРЕКЛЮЧЕНИЕ ===
Объясните, но не выполняйте: Auto переключает ровно между двумя VPN-профилями (основной и резервный). Ему нужен пройденный LAN-тест: владелец сам запускает LAN-помощника (скрипт PowerShell 7, см. https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/LAN-HELPER.ru.md) с компьютера, подключённого кабелем LAN, сначала в режиме «только проверка», и сам вводит слово TEST. Каждое автоматическое переключение должно быть подтверждено этим помощником, иначе роутер вернётся через 90 секунд. Работа Auto без присмотра пока не поддерживается. Приёмка переключения на реальном GL-MT6000 ещё не завершена: скажите об этом прямо.

Начните сейчас с пункта 0.1.`;
var AI_LAN_PROMPT_EN=`You are an assistant that helps the owner run the "LAN helper" of the experimental software "HomenS.AI Auto VPN" (GL.iNet GL-MT6000 / Flint 2). The helper is a small PowerShell 7 script that runs on the owner's Windows computer and checks, from the computer's side, that the internet really works through the router before and after a switch to the reserve VPN. Project: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (MIT, experimental alpha). Do the technical work yourself, step by step, and explain each step in plain language.

HARD RULES
1. Experimental software: the full trial switches the router to the reserve VPN for a few minutes and can interrupt the internet. Before step 5 tell the owner this and get an explicit "yes, run the full trial" from them in this chat.
2. SECRETS: never ask for, read, print, log or store the router password, SSH keys, Telegram token, VPN keys or configs. The helper asks for the router password itself and takes it privately; the owner types it in the terminal. Never put a password on a command line.
3. You never type the word TEST for the owner and never press the confirmation for them. The owner types TEST and the password themselves.
4. Change nothing on the computer except downloading the two helper files into one new folder and installing PowerShell 7 if it is missing (ask first). No network, VPN, DNS, firewall or router settings. Never turn Auto on; the owner does that in the web page after the trial passed.
5. Stop at the first error or surprise. Show the exact message and the capital-letter code, say what is known and not known, and open the page Help -> "The LAN helper fails" for that code. Do not invent workarounds.

STEPS
1. Ask for the router address (usually 192.168.8.1) and whether the computer is connected by LAN cable (recommended). Check that the web page http://ROUTER_ADDRESS/ answers.
2. Check PowerShell 7: run "pwsh -v". If it is missing, tell the owner and, with their consent, run "winget install Microsoft.PowerShell", then open a new terminal.
3. Download the two files from the program page (Overview or Settings -> "Download LAN helper" and "Download launcher") or from the router at /luci-static/resources/view/homensai-vpn/client-test.ps1 and start-lan-helper.ps1. Put both into a new folder, for example %USERPROFILE%\homensai-lan-helper. Tell the owner they are plain text files and can be read in Notepad.
4. In that folder run: pwsh -NoProfile -File .\start-lan-helper.ps1 . Choose mode 1 (check only). It reads and changes nothing. Report the result.
5. Only if mode 1 passed and the owner said yes in this chat: run the launcher again and choose mode 3 (full trial). Tell the owner they will now be asked for the router password and for the word TEST, and that they must type both themselves. Do not look at the keyboard input. Wait until the helper finishes.
6. Read the result. If it says the trial passed, tell the owner to open the web page and press the Auto button in the "Automatic VPN failover" block. If it failed, follow rule 5.

FINAL REPORT with three lists: DONE (with the real output), NOT DONE, NOT VERIFIED. Never claim the LAN path is proven unless the helper said so.`;
var AI_LAN_PROMPT_RU=`Вы — помощник, который помогает владельцу запустить «LAN-помощник» экспериментальной программы «HomenS.AI Auto VPN» (GL.iNet GL-MT6000 / Flint 2). LAN-помощник — небольшой скрипт PowerShell 7 на компьютере владельца с Windows: со стороны компьютера он проверяет, что интернет действительно работает через роутер до и после переключения на резервный VPN. Проект: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn (MIT, экспериментальная alpha). Техническую работу делайте сами, шаг за шагом, и простыми словами объясняйте каждый шаг.

ЖЁСТКИЕ ПРАВИЛА
1. Экспериментальная программа: полный тест на несколько минут переключает роутер на резервный VPN и может прервать интернет. Перед шагом 5 скажите это владельцу и получите в этом чате явное «да, запускай полный тест».
2. СЕКРЕТЫ: никогда не спрашивайте, не читайте, не печатайте, не логируйте и не сохраняйте пароль роутера, SSH-ключи, токен Telegram, ключи и конфиги VPN. Помощник сам спрашивает пароль роутера и принимает его скрыто; владелец вводит его в терминале сам. Никогда не ставьте пароль в командную строку.
3. Вы никогда не вводите слово TEST за владельца и не нажимаете подтверждение за него. TEST и пароль вводит сам владелец.
4. Ничего не меняйте на компьютере, кроме скачивания двух файлов помощника в одну новую папку и установки PowerShell 7, если его нет (сначала спросите). Никаких настроек сети, VPN, DNS, брандмауэра или роутера. Никогда не включайте Auto: это делает владелец в веб-странице после успешного теста.
5. Остановитесь на первой ошибке или неожиданности. Покажите точное сообщение и код заглавными буквами, скажите, что известно и что неизвестно, и откройте страницу «Помощь» → «LAN-помощник не работает» для этого кода. Не придумывайте обходных путей.

ШАГИ
1. Спросите адрес роутера (обычно 192.168.8.1) и подключён ли компьютер кабелем (рекомендуется). Проверьте, что страница http://АДРЕС_РОУТЕРА/ отвечает.
2. Проверьте PowerShell 7: «pwsh -v». Если его нет, скажите владельцу и с его согласия выполните «winget install Microsoft.PowerShell», затем откройте новый терминал.
3. Скачайте два файла со страницы программы («Обзор» или «Настройки» → «Скачать LAN-помощник» и «Скачать запуск») либо с роутера по адресу /luci-static/resources/view/homensai-vpn/client-test.ps1 и start-lan-helper.ps1. Положите оба в новую папку, например %USERPROFILE%\homensai-lan-helper. Скажите владельцу, что это обычные текстовые файлы, их можно прочитать в Блокноте.
4. В этой папке выполните: pwsh -NoProfile -File .\start-lan-helper.ps1 . Выберите режим 1 (только проверка). Он ничего не меняет. Сообщите результат.
5. Только если режим 1 прошёл и владелец сказал «да» в этом чате: запустите запуск снова и выберите режим 3 (полный тест). Скажите владельцу, что сейчас у него спросят пароль роутера и слово TEST и что оба он вводит сам. Не смотрите на ввод с клавиатуры. Дождитесь окончания работы помощника.
6. Прочитайте результат. Если тест пройден, скажите владельцу открыть веб-страницу и нажать кнопку Auto в блоке «Автоматическое переключение VPN». Если не пройден — действуйте по правилу 5.

ИТОГОВЫЙ ОТЧЁТ тремя списками: СДЕЛАНО (с реальным выводом), НЕ СДЕЛАНО, НЕ ПРОВЕРЕНО. Никогда не утверждайте, что путь в LAN доказан, если помощник этого не сказал.`;
function renderAiPrompt(which){
  var lan=which==='lan';
  var text=lan?bi(AI_LAN_PROMPT_EN,AI_LAN_PROMPT_RU):bi(AI_PROMPT_EN,AI_PROMPT_RU);
  var copy=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
    try{navigator.clipboard.writeText(text).then(function(){copy.textContent=bi('Prompt copied','Промпт скопирован');setTimeout(function(){copy.textContent=bi('Copy the prompt','Скопировать промпт');},3000);}).catch(function(){selectPrompt();});}catch(error){selectPrompt();}
  }},bi('Copy the prompt','Скопировать промпт'));
  var pre=E('pre',{'class':'hv-cmd hv-prompt','tabindex':'0'},text);
  function selectPrompt(){try{var range=document.createRange();range.selectNodeContents(pre);var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);}catch(e){}}
  return E('div',{'class':'hv-ai-prompt'},[
    lan?E('p',{},bi('Do not want to run the LAN helper by hand? Press “Copy the prompt” and paste it into your AI agent (one that can run commands on your computer). It checks PowerShell 7, downloads the two helper files, runs the check-only mode by itself and explains the result. The full trial, the router password and the word TEST stay with you.','Не хотите запускать LAN-помощник вручную? Нажмите «Скопировать промпт» и вставьте его в вашего ИИ-агента (того, что может выполнять команды на вашем компьютере). Он проверит PowerShell 7, скачает два файла помощника, сам запустит режим проверки и объяснит результат. Полный тест, пароль роутера и слово TEST остаются за вами.')):E('p',{},bi('Want the result faster? Use your own AI agent (one that can run commands on your computer). Press “Copy the prompt”, paste it into the agent, and it will check the router, install the program, verify it, start the monitor and guide you through the Telegram setup, step by step. You only answer its questions and do the few things that must be done by you: accept the risk and the terms, type secrets into the router page, and press Save in the wizards.','Хотите получить результат быстрее? Используйте своего ИИ-агента (того, который умеет выполнять команды на вашем компьютере). Нажмите «Скопировать промпт», вставьте его агенту, и он проверит роутер, установит программу, проверит её, запустит мониторинг и проведёт вас по настройке Telegram шаг за шагом. Вам нужно только отвечать на его вопросы и сделать то немногое, что можете сделать только вы: принять риск и условия, ввести секреты на странице роутера и нажать «Сохранить» в мастерах.')),
    lan?E('p',{'class':'hv-ready-intro'},bi('The prompt forbids the agent to ask for or type your password or the word TEST, and to turn Auto on; it must get your explicit yes before the full trial and stop at the first error. Read it before you paste it; the text below is exactly what is copied.','Промпт запрещает агенту спрашивать или вводить ваш пароль и слово TEST и включать Auto; перед полным тестом он обязан получить ваше явное «да» и остановиться на первой ошибке. Прочитайте его перед вставкой; ниже ровно тот текст, который копируется.')):E('p',{'class':'hv-ready-intro'},bi('The prompt asks the agent to protect your secrets, to work in monitor mode only (Auto stays off), to stop at the first problem and to report honestly what was verified and what was not. Read it before you paste it; the text below is exactly what is copied.','Промпт просит агента беречь ваши секреты, работать только в режиме мониторинга (Auto остаётся выключенным), останавливаться на первой проблеме и честно сообщать, что проверено, а что нет. Прочитайте его перед вставкой; ниже ровно тот текст, который копируется.')),
    E('div',{'class':'hv-ai-actions'},[copy]),pre]);
}

// A separate Help topic, shown first: its body is the copyable prompt instead of numbered steps.
HELP_TOPICS.unshift({id:'ai-prompt',title:['Prompt for your AI agent','Промпт для вашего ИИ-агента'],when:['You would rather let an AI agent install, check and configure everything for you.','Вы хотите, чтобы установку, проверку и настройку полностью сделал ИИ-агент.'],steps:[],custom:function(){return renderAiPrompt();}});

// Second prompt: an AI agent runs the LAN helper with the owner (check-only mode by itself; the full trial only with the owner's yes and their own password).
HELP_TOPICS.splice(1,0,{id:'ai-lan-prompt',title:['Prompt for your AI agent: run the LAN helper','Промпт для ИИ-агента: запустить LAN-помощник'],when:['You do not want to run the LAN helper by hand: an AI agent that can run commands on your computer does the steps and asks you only for what it must not do itself.','Вы не хотите запускать LAN-помощник вручную: ИИ-агент, который может выполнять команды на вашем компьютере, делает шаги сам и спрашивает вас только о том, что не имеет права делать сам.'],steps:[],custom:function(){return renderAiPrompt('lan');}});

// Opens a Help topic from anywhere (used by the LAN trial card in Settings).
function openHelpTopic(id){
  var link=document.querySelector('[data-hv-tab="help"]');if(link)link.click();
  setTimeout(function(){var topic=document.getElementById('help-'+id);if(topic){topic.open=true;try{topic.scrollIntoView({block:'start'});}catch(e){}}},200);
}
function helpLink(id,label){return E('a',{'href':'#help','class':'hv-help-link','click':function(ev){ev.preventDefault();openHelpTopic(id);}},label);}
// Settings > Automatic switching: why the LAN helper exists, how to get it, where the full guide and the AI prompt are.
function lanHelperExplain(){
  return E('div',{'class':'hv-lan-explain'},[
    E('h4',{},bi('Why a LAN helper is needed','Зачем нужен LAN-помощник')),
    E('p',{},bi('The router can see its VPN tunnels, but it cannot see what your own computer or phone gets. Whether DNS, the Kill Switch and the real internet work for a device at home through the reserve VPN can only be proven from that device. The LAN helper is a small program that runs on a Windows computer in your home network, sends the same kind of traffic through the router before and after a switch and tells the router “confirmed”. Without that confirmation the router goes back to the previous route after 90 seconds. That is why Auto stays locked until one trial has passed.','Роутер видит свои VPN-туннели, но не видит, что получает ваш компьютер или телефон. Работают ли DNS, Kill Switch и настоящий интернет у устройства дома через резервный VPN, можно доказать только с самого устройства. LAN-помощник — небольшая программа на компьютере с Windows в вашей домашней сети: она пропускает такой же трафик через роутер до и после переключения и сообщает роутеру «подтверждаю». Без этого подтверждения роутер через 90 секунд возвращается на прежний маршрут. Поэтому Auto заблокирован, пока не пройден один тест.')),
    E('p',{},bi('It runs only when you start it, installs nothing and changes no network settings of the computer. Mode 1 only reads; the full trial asks for the router password (typed privately, never saved) and the word TEST.','Он запускается только когда вы его запускаете, ничего не устанавливает и не меняет сетевые настройки компьютера. Режим 1 только читает; полный тест спрашивает пароль роутера (вводится скрыто, нигде не сохраняется) и слово TEST.')),
    E('ol',{},[E('li',{},bi('Press “Download LAN helper” and “Download launcher” below and put both files into one folder.','Нажмите «Скачать LAN-помощник» и «Скачать запуск» ниже и положите оба файла в одну папку.')),
      E('li',{},bi('Install PowerShell 7 once, open it in that folder and start the launcher; first choose mode 1 (check only), then mode 3 (full trial).','Один раз установите PowerShell 7, откройте его в этой папке и запустите; сначала выберите режим 1 (только проверка), затем режим 3 (полный тест).')),
      E('li',{},bi('When the trial has passed, press the Auto button on the Overview.','Когда тест пройден, нажмите кнопку Auto на «Обзоре».'))]),
    E('p',{},[helpLink('helper-what',bi('Help: full guide, step by step','Помощь: полная инструкция по шагам')),' · ',helpLink('ai-lan-prompt',bi('Help: prompt for your AI agent to run it for you','Помощь: промпт для вашего ИИ-агента, чтобы он запустил всё за вас')),' · ',helpLink('helper',bi('Help: the helper fails','Помощь: помощник не работает'))])]);
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

/* One table for the speed tests: tick servers, press "Test speed" (or cancel), and the same table shows the results.
   Replaces the older panel that had a drop-down, a second table of results and a "recommended priorities" button
   (later function declaration wins). */
var speedSelected={};
function speedStateText(history){
  var state=history.state||'IDLE';
  if(state==='IDLE'||state==='COMPLETED'||state==='COMPLETE')return bi('No test is running.','Сейчас тест не идёт.');
  if(state==='RUNNING'||state==='QUEUED'||state==='STARTING')return bi('A test is running; the table fills in as results arrive.','Идёт тест; таблица заполняется по мере поступления результатов.');
  return bi('State: ','Состояние: ')+state;
}
function speedPanel(status,inventory,period,onPeriod){
  var history=status.speed_tests||{},s=inventory.settings||{},profiles=status.profiles||[];
  var active=profiles.filter(function(p){return p.interface;}).slice(0,8);
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
  var section=E('section',{'class':'hv-chart-card hv-speed-panel'},[
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
    table.appendChild(E('tr',{'class':connected?'':'hv-speed-off'},[E('td',{},box),E('td',{},[E('strong',{},p?serverTitle(p):id),connected?null:E('small',{},' '+bi('(not connected)','(не подключён)'))].filter(Boolean)),E('td',{},down==null?'—':down.toFixed(1)),E('td',{},up==null?'—':up.toFixed(1)),E('td',{},lastCell),E('td',{},g?good.length+' / '+g.count:'—')]));
  });
  if(!ids.length)table.appendChild(E('tr',{},[E('td',{'colspan':'6'},bi('No connected VPN servers yet. Connect one in the GL.iNet VPN Dashboard.','Подключённых VPN-серверов пока нет. Подключите сервер в GL.iNet → VPN Dashboard.'))]));
  var test=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':s.speed_enabled&&active.length?null:'','click':function(){
    var selected=active.filter(function(p){return speedSelected[p.id];}).map(function(p){return p.id;}),mib=s.speed_budget_mib==null?8:s.speed_budget_mib,duration=s.speed_duration==null?5:s.speed_duration,streams=s.speed_streams==null?2:s.speed_streams;
    if(!s.speed_enabled||!active.length)return;
    if(!selected.length){ui.addNotification(null,E('p',{},bi('Tick at least one connected server in the table first.','Сначала отметьте в таблице хотя бы один подключённый сервер.')));return;}
    if(![['speed.budget_mib',mib],['speed.duration',duration],['speed.streams',streams]].every(function(row){return foolCheckNumber(row[0],row[1]).ok;})){ui.addNotification(null,E('p',{},bi('Check the speed test limits in the settings first.','Сначала проверьте ограничения теста скорости в настройках.')));return;}
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('ul',{},selected.map(function(id){var q=profiles.filter(function(p){return p.id===id;})[0];return E('li',{},q?serverTitle(q):id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams).then(function(result){ui.addNotification(null,E('p',{},result&&result.accepted===true?bi('The test is queued; results appear in the table.','Тест поставлен в очередь; результаты появятся в таблице.'):(result&&safeCode(result.code)?result.code:'SPEED-START-FAILED')));ui.hideModal();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-START-FAILED'));});},{key:'speed-start'});}},bi('Run test','Запустить тест')),'speed-start')]);
  }},bi('Test speed','Тестировать скорость'));
  var cancel=E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',method:'speed_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.queued?bi('Cancel requested.','Отмена запрошена.'):bi('No test is running.','Сейчас тест не идёт.')));});}},bi('Cancel current test','Отменить текущий тест'));
  var periodSelect=E('select',{'aria-label':bi('Show results for','Показать результаты за'),'change':function(ev){onPeriod(ev.target.value);}},[['latest',bi('Latest test','Последний тест')],['day',bi('Today','Сегодня')],['week',bi('Last 7 days','Последние 7 дней')],['month',bi('Current calendar month','Текущий календарный месяц')]].map(function(row){return E('option',{value:row[0]},row[1]);}));periodSelect.value=period;
  section.appendChild(E('div',{'class':'hv-native-actions'},[test,cancel,E('label',{'class':'hv-speed-period'},[bi('Results for: ','Результаты за: '),periodSelect])]));
  section.appendChild(E('p',{'role':'status'},speedStateText(history)+' '+bi('Finished tests: ','Завершено тестов: ')+(history.completed||0)));
  if(!s.speed_enabled)section.appendChild(E('p',{'class':'alert-message warning'},[bi('Speed tests are switched off. ','Тесты скорости выключены. '),E('a',{'href':'#tests','click':function(ev){ev.preventDefault();goToSection('tests','hv-speed-settings');}},bi('Turn them on in Advanced → Tests → Speed test settings.','Включите их в «Расширенное» → «Тесты» → «Настройки тестов скорости».'))]));
  section.appendChild(table);
  section.appendChild(E('small',{},bi('Mean of successful tests; failed or cancelled tests are not counted as zero speed. History is sampled and bounded.','Среднее по успешным тестам; ошибки и отмены не считаются нулевой скоростью. История выборочная и ограниченная.')));
  if(history.history_error)section.appendChild(E('p',{},history.history_error));
  if(history.history_truncated)section.appendChild(E('p',{},'SPEED-HISTORY-TRUNCATED: '+history.history_truncated));
  return section;
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
  var today=dateKey(new Date()),section=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Daily WAN and VPN traffic','Суточный трафик WAN и VPN'))]);
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
  var now=Date.now()/1000,interval=Number(((inventory||{}).settings||{}).interval)||30;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var light=autoLightModel(status,inventory||{},now);
  function lamp(kind,title){return E('span',{'class':'hv-live-lamp hv-live-lamp-'+kind,'role':'img','aria-label':title,'title':title});}
  function time(t,fallback){return E('span',{'class':'hv-log-time'},t?new Date(t*1000).toLocaleTimeString():fallback);}
  var counter=E('span',{'class':'hv-live-age'}),bar=E('span',{'class':'hv-live-bar-fill'}),next=E('span',{'class':'hv-live-next'});
  var head=E('div',{'class':'hv-live-head'},[E('span',{'class':'hv-live-dot hv-live-dot-'+(fresh?'on':'off'),'aria-hidden':'true'}),E('strong',{},fresh?bi('LIVE','В ЭФИРЕ'):bi('NO DATA','НЕТ ДАННЫХ')),counter,E('span',{'class':'hv-live-bar','aria-hidden':'true'},bar),next]);
  function tick(){
    var t=Date.now()/1000,age=Number.isFinite(status.time)?Math.max(0,t-status.time):null;
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
  section.querySelectorAll('details').forEach(function(node,index){saved.details.push({index:index,open:node.open});});
  return saved;
}
function restorePageViewport(root,saved){
  if(!root||!root.isConnected||!saved||!Number.isFinite(saved.y))return;
  var section=root.querySelector('[data-hv-page="'+saved.page+'"]')||root;
  var details=section.querySelectorAll('details');
  (Array.isArray(saved.details)?saved.details.slice(0,1000):[]).forEach(function(item){if(item&&Number.isSafeInteger(item.index)&&item.index>=0&&details[item.index])details[item.index].open=item.open===true;});
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

return view.extend({
  handleSave:null,handleSaveApply:null,handleReset:null,
  load:function(){return Promise.all([loadInventory(0),statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};}),loadBrand()]);},
  render:function(data){
    var configured=!!((data[0].settings||{}).telegram_configured);
    var setup=new URLSearchParams(window.location.search).get('setup')==='telegram';
    var inventory=data[0];
    onboardingDisplayDefaults(inventory);
    if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory,data[1]);
    if(!inventory.error&&!onboardingComplete(inventory)&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);
    var panel=E('div',{'class':'hv-panel'}),self=this,period='day',speedPeriod='week';
    var lastGoodStatus=data[1];
    var pointerHeld=false,deferredStatus=null;
    var subtitle=null,advancedBox=null,advancedToggle=null,appRoot=null,settingsHost=null,heading=null,sideState=null,versionBadge=null,pages={},sortStates={},searchTerms={};
    var tabs=[['start','▶',bi('Getting started','Начало работы')],['overview','◉',bi('Overview','Обзор')],['channels','⇄',bi('Channels and servers','Каналы и серверы')],['tests','⏻',bi('Tests','Тесты')],['statistics','▥',bi('Statistics','Статистика')],['traffic','◷',bi('Monthly traffic','Трафик за месяц')],['services','▣',bi('Live log','Живой журнал')],['events','≡',bi('Events and errors','События и ошибки')],['readiness','✓',bi('System readiness','Готовность системы')],['settings','⚙',bi('Settings','Настройки')],['learn','🎓',bi('Training','Обучение')],['help','?',bi('Help','Помощь')]];
    function routerVpnUrl(){return resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);}
    function vpnSetupCard(){return E('section',{'class':'hv-chart-card hv-vpn-setup'},[E('div',{'class':'hv-auto-power-unit'},[E('a',{'class':'hv-auto-power hv-vpn-configure','href':routerVpnUrl()||null,'aria-disabled':routerVpnUrl()?null:'true','title':routerVpnUrl()?null:bi('Router address unavailable in this preview','Адрес роутера недоступен в этом просмотре'),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('Open router VPN settings (opens a new tab)','Открыть настройки VPN роутера (новая вкладка)')},E('span',{'aria-hidden':'true','class':'hv-configure-symbol'},'⚙')),E('strong',{'class':'hv-auto-action'},bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗'))]),E('p',{},[bi('Add servers and connection keys on the router page ','Добавляйте серверы и ключи на странице роутера '),routerVpnUrl()?E('a',{'class':'hv-vpn-profile-link','href':routerVpnUrl(),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('VPN Client Profile (opens the router VPN settings in a new tab)','VPN Client Profile (открывает настройки VPN роутера в новой вкладке)')},'VPN Client Profile ↗'):E('span',{},'VPN Client Profile'),'.',E('br'),bi('Monitoring and failover priorities are set in this program (not on the router page): ','Мониторинг и приоритеты переключения настраиваются в этой программе (не на странице роутера): '),E('a',{'href':'#settings'},bi('Settings → Setup → 1 · System setup','Настройки → Настройка → 1 · Настройка системы')),'.'])]);}
    function validTab(key){return tabs.some(function(t){return t[0]===key;});}
    var activeTab=setup?'settings':window.location.hash.slice(1);if(!validTab(activeTab))activeTab=startLanding(data[1],data[0]);
    function showPage(key){
      var oldTab=activeTab;if(oldTab!==key)rememberPageViewport(appRoot||panel,oldTab);if(!validTab(key))key='overview';activeTab=key;if(appRoot)appRoot.setAttribute('data-hv-active',key);
      var scope=appRoot||panel;scope.querySelectorAll('[data-hv-page]').forEach(function(node){node.hidden=node.getAttribute('data-hv-page')!==key;});
      if(appRoot)appRoot.querySelectorAll('[data-hv-tab]').forEach(function(node){node.setAttribute('aria-current',node.getAttribute('data-hv-tab')===key?'page':'false');});
      if(appRoot){appRoot.querySelectorAll('.hv-connectivity-control').forEach(function(node){node.hidden=key!=='overview';});}
      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);
      if(oldTab!==key)revisitPageViewport(appRoot||panel,key);
      if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];
      if(oldTab!==key&&heading&&document.body.contains(heading)){try{heading.focus({preventScroll:true});}catch(focusError){}}
      if(subtitle&&PAGE_SUBTITLES[key])subtitle.textContent=bi(PAGE_SUBTITLES[key][0],PAGE_SUBTITLES[key][1]);
      if(advancedBox&&ADVANCED_KEYS.indexOf(key)>=0&&advancedBox.hidden){advancedBox.hidden=false;if(advancedToggle)advancedToggle.setAttribute('aria-expanded','true');}
    }
    function put(key,node){
      if(!pages[key]){pages[key]=E('section',{'class':'hv-page','data-hv-page':key});panel.appendChild(pages[key]);}
      pages[key].appendChild(node);return node;
    }
    function sortableTables(){
      panel.querySelectorAll('table').forEach(function(table,index){if(table.closest('.hv-errtable'))return;
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
      var controlFocus=panel.contains(document.activeElement)&&document.activeElement.matches('button,input[type=checkbox],select')?{page:(document.activeElement.closest('[data-hv-page]')||{dataset:{hvPage:activeTab}}).dataset.hvPage,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.textContent,tag:document.activeElement.tagName}:null;
      updateConnectivityCheck(status);
      if(!status.rpc_error)lastGoodStatus=status;
      var focused=panel.contains(document.activeElement)&&document.activeElement.classList.contains('hv-search')?{key:document.activeElement.closest('[data-hv-page]').dataset.hvPage,start:document.activeElement.selectionStart,end:document.activeElement.selectionEnd}:null;
      while(panel.firstChild)panel.removeChild(panel.firstChild);pages={};
      put('services',E('p',{'class':'alert-message warning'},
        bi('Monitoring is on. The checks run from the router and show whether each VPN works; they cannot prove what a computer on your network sees. That is confirmed separately by the LAN helper before Auto may switch.','Мониторинг включён. Проверки выполняет сам роутер и показывают, работает ли каждый VPN; они не доказывают, что видит компьютер в вашей сети. Это отдельно подтверждает LAN-помощник перед включением Auto.')));
      if(status.rpc_error)put('overview',E('p',{'class':'alert-message warning'},'RPC-UNAVAILABLE: displaying last known measurements. Connectivity and service state are unconfirmed.'));
      if(status.error)put('overview',E('p',{},badge(status.error)));
      var tg=status.telegram||{};if(tg.enabled&&tg.code)put('overview',E('p',{'class':'alert-message warning'},'Telegram: '+tg.code));
      var rows=status.profiles||[];
      var active=rows.filter(function(p){return p.interface;}),healthy=active.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';});
      var currentMonth=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit'}).format(new Date()),month=((status.accounting||{}).months||{})[currentMonth]||null;
      put('overview',E('div',{'class':'hv-metrics'},[
        metricInfo(bi('Connected VPNs','Подключённые VPN'),active.length+bi(' of ',' из ')+rows.length,bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Your router has '+rows.length+' VPN profile(s) in this list and '+active.length+' of them are connected right now. Only connected VPNs are checked. The other ones are listed but this program never connects them.','В этом списке на роутере '+rows.length+' VPN-профилей, из них сейчас подключено '+active.length+'. Проверяются только подключённые. Остальные показаны в списке, но эта программа их никогда не подключает.')),
        metricInfo(bi('VPNs that work','VPN, которые работают'),healthy.length+bi(' of ',' из ')+active.length,bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Of the connected VPNs, this many passed the latest check: the router could open a website and resolve a name through them. This is the same number as in the coloured card at the top.','Из подключённых VPN столько прошли последнюю проверку: роутер смог открыть сайт и найти адрес через них. Это то же число, что в цветной карточке вверху.')),
        metricInfo(bi('Traffic this month','Трафик за месяц'),month?bytes(month.rx+month.tx):bi('No data','Нет данных'),bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Data that went through your VPNs since the monitor was started. It is counted from the first measurement, so the month may be incomplete.','Данные, прошедшие через ваши VPN с запуска мониторинга. Считаются с первого измерения, поэтому месяц может быть неполным.')),
        metric('Telegram',tg.enabled?(tg.code?tr("Ошибка"):tr("Каждые ")+tg.interval_minutes+tr(" мин")):tr("Отключён"),tg.last_sent?tr("Отправлен ")+new Date(tg.last_sent*1000).toLocaleTimeString():tr("Нет подтверждённой отправки"))
      ]));
      put('channels',vpnSetupCard());put('channels',renderServerSummary(status,inventory,rows));put('channels',renderVendorChannels(status,inventory));
      var cards=E('div',{'class':'hv-server-grid'});
      sortServerCards(rows,vendorDisplaySelected(status,inventory,Date.now()/1000),Date.now()/1000).forEach(function(p){var channelUse=channelDisplayUse(p,status,inventory);cards.appendChild(E('article',{'class':'hv-server hv-health-'+profileHealth(p,Date.now()/1000).state,'data-profile':p.id,'data-health':profileHealth(p,Date.now()/1000).state,'data-route-state':channelUse.state},[
        renderChannelHeader(p,status,inventory),
        E('h4',{'class':'hv-server-country'},countryLabel(p)),E('p',{},(customName(p)?customName(p)+' · ':'')+bi('Group: ','Группа: ')+(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён'))),
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
      planning.appendChild(renderPlanBlockers(fp.blockers||[],status));
      put('tests',planning);


      var ns=status.native_failover||{state:'UNKNOWN'};
      var controlCard=renderAutoControl(status,inventory);put('overview',controlCard);put('overview',renderVendorOverview(status,inventory));put('tests',renderCascadePath(status));put('tests',renderDecisionExplanation(status,inventory));put('readiness',readinessIntro());put('readiness',renderReadiness(status,inventory));put('help',helpNode||(helpNode=renderHelp()));put('learn',learnNode||(learnNode=renderLearn()));put('start',renderStartPage(status,inventory));pages.overview.insertBefore(controlCard,pages.overview.firstChild);pages.overview.insertBefore(renderSummary(status,inventory),controlCard.nextSibling);var identityNotice=renderIdentityNotice(status);try{pages.overview.insertBefore(renderDesignOverview(currentDesign(),{status:status,inventory:inventory,rows:rows,month:month,controlCard:controlCard}),pages.overview.firstChild);pages.overview.setAttribute('data-hv-dv','1');}catch(designError){pages.overview.insertBefore(controlCard,pages.overview.firstChild);pages.overview.insertBefore(E('p',{'class':'alert-message warning'},'DESIGN-VIEW-ERROR: '+String(designError&&designError.message||designError).slice(0,120)),pages.overview.firstChild);}
      var stateNames={'OBSERVING':bi('Automatic monitoring','Автоматический контроль'),'ARMED':bi('Ready','Готов'),'COMMITTED':bi('Reserve confirmed','Резерв подтверждён'),'STOPPED':bi('Stopped','Остановлен'),'DISABLED':bi('Disabled','Выключен'),'EXPIRED':bi('Window ended','Окно завершено'),'WAIT-CLIENT':bi('Waiting for client','Ожидание клиента'),'APPLYING':bi('Switching','Переключение'),'BLOCKED':bi('Blocked','Заблокирован')};
      var stale=!ns.time||Date.now()/1000-ns.time>30;
      if(versionBadge)versionBadge.textContent='v'+(status.version||'unknown');
      if(sideState)fillSideStatus(sideState,status,inventory);if(monitorBlockHost)fillMonitorBlock(monitorBlockHost,status,inventory);

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
      nativePanel.appendChild(lanHelperExplain());nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')));nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/start-lan-helper.ps1'),'download':'start-lan-helper.ps1'},bi('Download launcher','Скачать запуск')));
      nativePanel.appendChild(E('p',{},[bi('Stop Auto or return to the primary on the Overview, in the Automatic VPN failover card. ','Остановить Auto или вернуться на основной можно на «Обзоре», в блоке «Автоматическое переключение VPN». '),E('a',{'href':'#overview'},bi('Open the Overview','Открыть «Обзор»'))]));
      put('settings',nativePanel);
      var nh=status.native_history||{};
      var historyPanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Controller history','История контроллера')),E('p',{},bi('Controller events, not measurements of LAN uptime. Trial results and automatic commits are counted separately.','События контроллера, а не измерение доступности LAN. Результаты тестов и автоматические переключения считаются отдельно.'))]);
      historyPanel.appendChild(E('p',{},bi('1 = primary, 2 = reserve. Yellow is the previous channel; green is the confirmed selected channel. Two yellow ends mark an unconfirmed attempt.','1 — основной, 2 — резерв. Жёлтый — прежний канал, зелёный — подтверждённый выбранный. Два жёлтых конца обозначают неподтверждённую попытку.')));if(nh.error)historyPanel.appendChild(badge(nh.error));
      if(nh.restored_from_backup)historyPanel.appendChild(E('p',{},'History loaded from the previous valid backup; the latest event may be missing.'));
      var historyTable=E('table',{'class':'table'},[E('tr',{},[E('th',{},bi('Time · Berlin','Время · Берлин')),E('th',{},bi('State','Состояние')),E('th',{},bi('Profiles','Профили')),E('th',{},bi('Reason','Причина'))])]);
      var transitionMarks=controllerTransitionMarks(nh.events||[]);
      (nh.events||[]).slice().reverse().forEach(function(event){var names=[event.source,event.target].filter(Boolean).map(function(id){return (rows.filter(function(p){return p.id===id;})[0]||{}).name||id;});historyTable.appendChild(E('tr',{},[E('td',{'data-sort-value':event.time},new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})),E('td',{},[renderTransitionBadge(event,transitionMarks),event.state+(event.trial?' · '+'trial':'')].filter(Boolean)),cell(names.join(' → ')),cell((event.codes||[]).join(' · '))]));});historyPanel.appendChild(historyTable);
      var monthly=E('table',{'class':'table'},[E('tr',{},[E('th',{},bi('Month','Месяц')),E('th',{},bi('Attempts','Попытки')),E('th',{},bi('Trials passed','Тестов пройдено')),E('th',{},bi('Automatic commits','Автопереключений')),E('th',{},bi('Rollbacks','Откатов')),E('th',{},bi('Blocked episodes','Заблокированных эпизодов'))])]);
      Object.keys(nh.months||{}).sort().reverse().forEach(function(month){var c=nh.months[month];monthly.appendChild(E('tr',{},[cell(month),cell(c.attempts),cell(c.trials_passed),cell(c.committed),cell(c.rollbacks),cell(c.blocked_episodes)]));});historyPanel.appendChild(monthly);put('events',historyPanel);put('events',renderTransitionAnalytics(status));put('events',renderVendorEvents(status,inventory));

      var table=E('table',{'class':'table hv-check-table'},[E('tr',{'class':'tr table-titles'},[bi('Status','Статус'),tr("Сервер"),tr("Канал"),tr("Протокол"),tr("Интерфейс"),tr("Результат"),tr("HTTPS, мс"),tr("Время проверки")].map(function(t){return E('th',{},t);} ))]);
      sortServerCards(rows,selectedProfile(status,Date.now()/1000),Date.now()/1000).forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[checkLampCell(p,status,inventory),cell(serverTitle(p)),cell(p.channel),cell(protocolLabel(p)),cell(p.interface),E('td',{},healthBadge(p)),cell(profileHealth(p,Date.now()/1000).state==='healthy'?p.rtt_ms:null),cell(p.time?new Date(p.time*1000).toLocaleTimeString():'—')]));});
      put('channels',E('h3',{},tr("Текущие проверки серверов")));addSearch('channels',table);put('channels',table);
      put('channels',E('p',{},tr("Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.")));
      var samples=status.samples||[],rank={};samples.forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
      Object.keys((status.accounting||{}).quality||{}).forEach(function(id){var q=status.accounting.quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
      var ranked=rows.map(function(p){return {p:p,r:rank[p.id]||{n:0,good:0,sum:0}};}).sort(function(a,b){return (rankEnough(b.r.n)-rankEnough(a.r.n))||(b.r.n?b.r.good/b.r.n:-1)-(a.r.n?a.r.good/a.r.n:-1)||(a.r.good?a.r.sum/a.r.good:Infinity)-(b.r.good?b.r.sum/b.r.good:Infinity);});
      var ranking=E('table',{'class':'table'},[E('tr',{},[tr("Рейтинг измеренных профилей"),tr("Успех проверок"),tr("Средняя HTTPS-задержка"),bi("Checks","Проверок")].map(function(t){return E('th',{},t);}))]);
      ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(serverTitle(item.p)),cell(item.r.n?(100*item.r.good/item.r.n).toFixed(1)+'%':tr("Нет данных")),cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+tr(" мс"):'—'),cell(rankConfidence(item.r.n))]));});
      addSearch('ranking',ranking);put('ranking',ranking);put('ranking',E('p',{},bi('Servers with fewer than 20 checks are listed last: one lucky check does not make a leader.','Серверы с менее чем 20 проверками стоят в конце: одна удачная проверка не делает лидера.')));put('ranking',E('p',{},tr("Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.")));
      var accounting=status.accounting||{},months=accounting.months||{};
      put('traffic',E('h3',{},tr("VPN-трафик по календарным месяцам · Europe/Berlin")));
      var traffic=E('table',{'class':'table'},[E('tr',{},[tr("Месяц"),tr("Входящий"),tr("Исходящий"),tr("Всего"),tr("Наблюдение")].map(function(t){return E('th',{},t);}))]);
      Object.keys(months).sort().reverse().forEach(function(key){var v=months[key];traffic.appendChild(E('tr',{},[cell(key),cell(bytes(v.rx)),cell(bytes(v.tx)),cell(bytes(v.rx+v.tx)),cell((v.seconds/3600).toFixed(1)+tr(" интерфейс-часов")+(v.boundary_estimated?tr(" · граница оценена"):''))]));});
      put('traffic',traffic);put('traffic',E('p',{},tr("Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: ")+text(accounting.gaps||0)+tr(". После потери питания возможна потеря последнего интервала checkpoint.")));
      put('services',E('h3',{},tr("Монитор служб")));
      put('services',E('p',{},bi('A live log of the router checks. “Connected” alone does not mean the internet works.','Живой журнал проверок роутера. Одного «подключено» мало, чтобы считать, что интернет работает.')));
      put('services',renderLiveLog(status,rows,ns,inventory,stateNames));
      put('events',E('button',{'class':'btn','click':function(){var blob=new Blob([JSON.stringify({mode:'router-monitor',events:status.events||[]},null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),link=E('a',{href:url,download:'homensai-vpn-events.json'});link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}},tr("Скачать журнал")));
      put('ranking',speedPanel(status,inventory,speedPeriod,function(value){speedPeriod=value;draw(status);}));
      put('traffic',trafficHistoryPanel(status.accounting||{}));
      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));
      put('tests',E('h2',{'class':'hv-speed-heading'},bi('Speed tests and server ranking','Тесты скорости и рейтинг серверов')));put('tests',E('p',{},bi('Which servers are fastest and most reliable, and the button to measure speed. If a server needs settings (budget, duration, streams), they are right below the table: change them and press the test button here.','Какие серверы быстрее и надёжнее, и кнопка замера скорости. Если нужны настройки (бюджет, длительность, потоки), они сразу под таблицей: измените их и нажмите кнопку теста здесь.')));if(pages.ranking){while(pages.ranking.firstChild)pages.tests.appendChild(pages.ranking.firstChild);}if(speedCardNode){put('tests',E('h3',{},bi('Speed test settings','Настройки тестов скорости')));put('tests',setupGuide('speed'));put('tests',speedCardNode);}
      if(controlFocus&&pages[controlFocus.page]){var options=pages[controlFocus.page].querySelectorAll('button,input[type=checkbox],select');var matching=Array.from(options).find(function(el){return el.tagName===controlFocus.tag&&el.getAttribute('aria-label')===controlFocus.label&&el.textContent===controlFocus.text;});if(matching)matching.focus({preventScroll:true});}
      if(inventory.error)put('overview',E('p',{'class':'alert-message warning','role':'alert'},'RPC-INVENTORY-UNAVAILABLE: configuration is unknown. Reload after RPC recovery; empty defaults are not saved.'));
      put('statistics',renderMonitorInfo(status,inventory));put('events',errorTable||(errorTable=renderErrorTable()));
      installErrorLinks(appRoot);sortableTables();showPage(activeTab);if(focused){var input=pages[focused.key]&&pages[focused.key].querySelector('.hv-search');if(input){input.focus();input.setSelectionRange(focused.start,focused.end);}}
      } finally {if(refreshViewport&&refreshViewport.page===activeTab)restorePageViewport(appRoot||panel,refreshViewport);}
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
      heading=E('h1',{'tabindex':'-1'},bi('Your internet under control','Ваш интернет под контролем'));
      sideState=E('div',{'class':'hv-side-status'});fillSideStatus(sideState,data[1],inventory);
      settingsHost=E('section',{'class':'hv-settings','data-hv-page':'settings'},[E('h3',{},bi('Monitoring, Telegram and profile names','Мониторинг, Telegram и названия профилей')),E('a',{'href':L.url('admin/services/homensai-vpn')+'?setup=telegram&lang='+locale+'#settings'},bi('Telegram setup wizard','Мастер настройки Telegram')),setup?E('p',{},bi('Create a bot with BotFather, send /start, then enter its token and your Chat ID. The token stays on the router and is never returned in status.','Создайте бота через BotFather, отправьте /start, затем введите токен и свой Chat ID. Токен хранится на роутере и не возвращается в статусе.')):null,formNode].filter(function(node){return node!=null;}));
      function tabLink(key){var tab=tabs.filter(function(t){return t[0]===key;})[0];return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'title':tab[2],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);}
      var advancedOpen=false;try{advancedOpen=localStorage.getItem('homensai-vpn-advanced')==='1';}catch(e){}
      if(ADVANCED_KEYS.indexOf(activeTab)>=0)advancedOpen=true;
      advancedBox=E('div',{'class':'hv-advanced-links'},ADVANCED_KEYS.map(tabLink));advancedBox.hidden=!advancedOpen;
      advancedToggle=E('button',{'type':'button','class':'hv-advanced-toggle','aria-expanded':advancedOpen?'true':'false','click':function(){var open=advancedBox.hidden;advancedBox.hidden=!open;advancedToggle.setAttribute('aria-expanded',open?'true':'false');try{localStorage.setItem('homensai-vpn-advanced',open?'1':'0');}catch(e){}}},[E('span',{},bi('Advanced','Расширенное')),E('small',{},bi('for administrators','для администраторов'))]);
      var links=['start','readiness','overview','channels','statistics','settings','help','learn'].map(tabLink).concat([advancedToggle,advancedBox]);
      appRoot=E('div',{'class':'hv-app hv-workspace','data-hv-design':currentDesign()},[E('a',{'class':'hv-skip','href':'#','click':function(ev){ev.preventDefault();var m=appRoot.querySelector('main');if(m){m.setAttribute('tabindex','-1');m.focus();}}},bi('Skip to content','К содержимому')),
        E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/charts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui47.css')+'?build=080-alpha8'}),
        E('aside',{'class':'hv-sidebar'},[E('a',{'class':'hv-side-brand','href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer','aria-label':bi('HomenS.AI website','Сайт HomenS.AI')},[robotHost,E('span',{},[E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI')]),E('small',{},'Auto VPN')])]),E('p',{'class':'hv-model'},routerModelLabel()),E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')},links),E('div',{'class':'hv-side-footer'},[sideState,E('small',{},bi('Real IPv4 router measurements','Реальные IPv4-измерения роутера')),E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),E('small',{},'HomenS.AI Style 1.14.3'),E('small',{'class':'hv-identity'},identityLine(data[1]))])]),
        E('main',{'class':'hv-main'},[E('header',{'class':'hv-page-header'},[E('div',{'class':'hv-header-main','style':'min-width:0;max-width:100%'},[E('div',{'class':'hv-eyebrow'},bi('AVAILABILITY CONTROL','УПРАВЛЕНИЕ ДОСТУПНОСТЬЮ')),heading,(subtitle=E('p',{},bi('Your VPNs, how healthy they are, and what the router did about it.','Ваши VPN, насколько они исправны и что сделал роутер.'))),E('div',{'class':'hv-tools-row'},[renderConnectivityCheck(data[1],function(){return statusCall().then(draw);},inventory),renderMonitorBlock(data[1],inventory)])]),E('div',{'class':'hv-page-actions'},[versionBadge,language,renderThemeSelect()])]),panel,settingsHost,renderAttribution(data[1]),footer])
      ]);
      settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-card-monitor'},[E('h3',{},bi('Monitor service','Служба мониторинга')),E('p',{},bi('Turns the background checks on or off. Stop Auto and wait for it to hand control back before turning the checks off. The real state is confirmed by fresh results.','Включает или выключает фоновые проверки. Перед выключением остановите Auto и дождитесь, пока он вернёт управление. Реальное состояние подтверждают свежие результаты.')),E('button',{'type':'button','class':'cbi-button','click':function(ev){ev.target.disabled=true;return rpc.declare({object:'homensai-vpn',reject:true,method:'monitor_control',params:['enabled'],expect:{}})(!(inventory.settings||{}).enabled).then(function(result){ui.addNotification(null,E('p',{},result.code||'MONITOR-UNKNOWN'));if(result.accepted)window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){ev.target.disabled=false;});}},(inventory.settings||{}).enabled?bi('Stop monitor','Остановить мониторинг'):bi('Start monitor','Запустить мониторинг'))]));
      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){recoveryWizard(inventory);}},bi('Recovery setup wizard','Мастер восстановления')));
      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){monitorPreferences(inventory);}},bi('Monitoring preferences','Параметры мониторинга')));
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
          !onboardingComplete(inventory)?E('p',{'class':'alert-message warning','data-onboarding-incomplete':'1'},bi('Initial setup is incomplete. Open All application settings to review and save it. Stop and recovery controls remain available.','Первоначальная настройка не завершена. Откройте «Все настройки приложения», проверьте и сохраните её. Остановка и средства восстановления остаются доступны.')):null,
          E('p',{},bi('Simple settings for every user. Every wizard validates your input and shows a review before saving. Stored tokens are never shown again. Open “What is this and how to fill it in” under a step for examples.','Простые настройки для любого пользователя. Каждый мастер проверяет ввод и показывает обзор перед сохранением. Сохранённые токены больше не показываются. Под каждым шагом есть «Что это и как заполнить» с примерами.')),
          E('p',{'class':'hv-setup-path','aria-label':bi('Order of the steps','Порядок шагов')},[E('b',{},bi('1 · System setup','1 · Настройка системы')),E('span',{'aria-hidden':'true'},' → '),E('b',{},bi('2 · Telegram','2 · Telegram')),E('span',{'aria-hidden':'true'},' → '),E('b',{},bi('3 · Test delivery','3 · Проверка доставки')),E('small',{},bi('Press a button below to open its wizard.','Нажмите кнопку ниже, чтобы открыть мастер.'))]),
          E('div',{'class':'hv-setup-grid hv-setup-steps'},[
            launcher(bi('1 · System setup','1 · Настройка системы'),bi('Press to open the wizard: primary and reserve VPN, names, groups, priorities and whether a short reconnection is acceptable.','Нажмите, чтобы открыть мастер: основной и резервный VPN, названия, группы, приоритеты и допустимость короткого переподключения.'),function(){setupWizard(inventory,'system');},true,'system'),
            launcher(bi('2 · Telegram channel','2 · Канал Telegram'),bi('Press to open the wizard: bot token and chat for reports. The wizard explains how to get both.','Нажмите, чтобы открыть мастер: токен бота и чат для отчётов. Мастер объясняет, как получить и то и другое.'),function(){setupWizard(inventory,'telegram');},false,'telegram'),
            launcher(bi('3 · Test Telegram delivery','3 · Проверить доставку Telegram'),bi('Press to send one test message with the saved settings. It should arrive within a few seconds.','Нажмите, чтобы отправить одно тестовое сообщение с сохранёнными настройками. Оно должно прийти за несколько секунд.'),testDelivery,false,null,'telegram-test')
          ])].filter(function(node){return node!=null;})));
        settingsHost.appendChild(renderDesignPicker(function(){return appRoot;},function(){updateSidebarLayout(appRoot,true);draw(lastGoodStatus||data[1]);}));
        settingsHost.appendChild(E('details',{'class':'hv-chart-card hv-admin-settings'},[
          E('summary',{},bi('Advanced settings (for administrators)','Расширенные настройки (для администратора)')),
          E('p',{},bi('Fine-tuning of the switching rules and of the checks. The defaults are safe; change them only if you know why. Open the guide under each step for examples.','Тонкая настройка правил переключения и проверок. Значения по умолчанию безопасны; меняйте их, только если понимаете зачем. Под каждым шагом есть руководство с примерами.')),
          E('div',{'class':'hv-setup-grid'},[
            launcher(bi('Recovery rules','Правила восстановления'),bi('Failures before switching, reserve checks, cooldown and return policy.','Сколько сбоев до переключения, проверки резерва, пауза и политика возврата.'),function(){recoveryWizard(inventory);},false,'recovery'),
            launcher(bi('Monitoring parameters','Параметры мониторинга'),bi('Check interval, profile limit and statistics saving.','Интервал проверок, лимит профилей и сохранение статистики.'),function(){monitorPreferences(inventory);},false,'monitoring')
          ])]));
        if(speedCard){speedCardNode=speedCard;speedCard.setAttribute('id','hv-speed-settings');put('tests',E('h3',{},bi('Speed test settings','Настройки тестов скорости')));put('tests',setupGuide('speed'));put('tests',speedCard);}
      })();
      panel.addEventListener('pointerdown',function(){pointerHeld=true;});
      ['pointerup','pointercancel'].forEach(function(event){window.addEventListener(event,function(){if(!pointerHeld)return;setTimeout(function(){pointerHeld=false;if(deferredStatus){var next=deferredStatus;deferredStatus=null;draw(next);}},0);});});
      showPage(activeTab);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});
      initSidebarLayout(appRoot);installViewportPersistence(appRoot,function(){return activeTab;});installErrorLinks(appRoot);installModalStyle();installTopButton(appRoot);installDesignKeys(appRoot,tabs.map(function(t){return t[0];}),function(k){window.location.hash=k;showPage(k);});
      return appRoot;
    });
  }
});