/* Advanced > Statistics collection (owner, 30 Oct 2026): the mode switch and everything the router tracks, where and how often. */
// [id, router file, where it lives, title en/ru, what it is en/ru, in work mode en/ru, in diagnostics en/ru, shown on en/ru]
var COLLECTION_ROWS=[
  ['checks','status.json','ram',['Current channel checks','Текущие проверки каналов'],['DNS/HTTPS/ping result of every check of both VPNs; Auto decides on these.','Результат каждой проверки обоих VPN (DNS, HTTPS, пинг); по ним решает Auto.'],
    ['Always; rewritten every check. Probe samples for decisions: last 6 hours.','Всегда; перезаписывается каждую проверку. Пробы для решений: последние 6 часов.'],['Always; probe samples for the retention period (1–7 days).','Всегда; пробы за срок хранения (1–7 дней).'],['Overview, channel cards, lamps','Обзор, карточки каналов, лампы']],
  ['journal','native-transaction.json','flash',['Switch journal','Журнал переключения'],['The current switch transaction: what was changed, so a restart can finish or undo it safely.','Текущая транзакция переключения: что изменено, чтобы после перезапуска безопасно завершить или откатить.'],
    ['Always; written only during a switch.','Всегда; пишется только во время переключения.'],['The same.','То же.'],['Auto card, recovery','Карточка Auto, восстановление']],
  ['pair','pair-auto-state.json','flash',['Auto pair state and settings','Состояние пары Auto и настройки'],['The chosen primary/reserve, the started session and your settings.','Выбранные основной/резервный, запущенный сеанс и ваши настройки.'],
    ['Always; written on start, stop, manual choice and settings.','Всегда; пишется при старте, остановке, ручном выборе и настройках.'],['The same.','То же.'],['Settings, Auto card','Настройки, карточка Auto']],
  ['history','native-history.json','flash',['Event history','История событий'],['Every Auto transition with phase times, counters per day and month.','Каждый переход Auto со временем этапов, счётчики по дням и месяцам.'],
    ['Always written to flash, only when Auto changes state (switches are rare); read and shown, never kept in memory.','Всегда пишется на флеш, только когда Auto меняет состояние (переключения редки); читается и показывается, в памяти не держится.'],['The same, and the service keeps a copy in memory for faster writing.','То же, и служба держит копию в памяти для более быстрой записи.'],['Events, Statistics, switch statistics','События, Статистика, статистика переключений']],
  ['accounting','checkpoint.json','flash',['Traffic, quality and reliability accounting','Учёт трафика, качества и надёжности'],['Monthly traffic per VPN, check success, outages, observed Auto time.','Трафик за месяц по каждому VPN, успешность проверок, отказы, время наблюдения Auto.'],
    ['Counted in memory; saved to flash once a day and at shutdown.','Считается в памяти; на флеш раз в сутки и при остановке.'],['Saved every checkpoint interval (15 min by default) with a backup copy.','Сохраняется каждый интервал (по умолчанию 15 мин) с резервной копией.'],['Monthly traffic, Statistics, ranking','Трафик за месяц, Статистика, рейтинг']],
  ['latency','latency-history.json','flash',['Delay history','История задержек'],['Delay of both channels over time for the chart.','Задержка обоих каналов во времени для графика.'],
    ['Not recorded.','Не записывается.'],['Recorded every check, saved every checkpoint interval.','Записывается каждую проверку, сохраняется каждый интервал.'],['Channels: delay chart','Каналы: график задержки']],
  ['ping','ping-response-history.json','flash',['Ping response history','История отклика (пинг)'],['Ping response per channel for the response chart and ranking.','Отклик пинга по каналам для графика отклика и рейтинга.'],
    ['Not recorded.','Не записывается.'],['Recorded every check, saved every checkpoint interval.','Записывается каждую проверку, сохраняется каждый интервал.'],['Channels, Tests: ranking','Каналы, Тесты: рейтинг']],
  ['websites','website-response-history.json','flash',['Website response history','История отклика (сайты)'],['Opening three websites through each channel (only when that method is chosen).','Открытие трёх сайтов через каждый канал (только если выбран этот способ).'],
    ['Not recorded.','Не записывается.'],['Recorded when the website method or comparison is on.','Записывается, если выбран способ «сайты» или сравнение.'],['Channels, Tests: ranking','Каналы, Тесты: рейтинг']],
  ['compare','response-compare.json','flash',['All-methods comparison','Сравнение всех способов'],['Every response method side by side (only when comparison is on).','Все способы отклика рядом (только если включено сравнение).'],
    ['Not recorded.','Не записывается.'],['Recorded when comparison is on.','Записывается, если включено сравнение.'],['Tests: ranking','Тесты: рейтинг']],
  ['probe','probe-history.json','flash',['Probe level decisions','Решения уровня опроса'],['When the boost turned on or off and why.','Когда ускорение включалось или выключалось и почему.'],
    ['Always; small, written on a decision only.','Всегда; маленький, пишется только при решении.'],['The same.','То же.'],['Service monitor','Монитор служб']],
  ['timing','switch-timing.json','flash',['Average switch time','Среднее время переключения'],['One number for the countdown on the page.','Одно число для обратного отсчёта на странице.'],
    ['Always; a few bytes per switch.','Всегда; несколько байт на переключение.'],['The same.','То же.'],['Countdown during a switch','Обратный отсчёт при переключении']],
  ['speed','speed-history.json','flash',['Speed tests','Тесты скорости'],['Results of speed tests you start.','Результаты тестов скорости, которые запускаете вы.'],
    ['Only when you run a test.','Только когда вы запускаете тест.'],['The same.','То же.'],['Statistics: speed','Статистика: скорость']],
  ['faults','fault-history.json','flash',['Failure tests','Тесты сбоя'],['Failure simulations you start on the Tests page.','Имитации сбоя, которые вы запускаете на странице «Тесты».'],
    ['Only when you run a test.','Только когда вы запускаете тест.'],['The same.','То же.'],['Tests','Тесты']]
];
var COLLECTION_HOURS=[[24,'1 day','1 день'],[72,'3 days','3 дня'],[168,'7 days','7 дней'],[336,'2 weeks','2 недели']];
// Measured consequences of Diagnostics vs Work on the GL-MT3000 (480 MB RAM). null = not measured yet (shown as such).
// Each row: [key, title en/ru, work value, diagnostics value, unit, how it was measured en/ru].
var DIAGNOSTIC_IMPACT={measured:null,version:null,rows:[
  ['memory',['Memory of both services','Память обеих служб'],null,null,'MB',['Memory held (VmRSS) by the monitor and Auto services after 10 minutes','Занятая память (VmRSS) служб мониторинга и Auto через 10 минут']],
  ['flash',['Flash writing','Запись на флеш'],null,null,'MB/day',['Bytes of rewritten files in /etc/homensai-vpn over 10 minutes, per day','Объём перезаписанных файлов в /etc/homensai-vpn за 10 минут, в пересчёте на сутки']],
  ['cpu',['Processor load of both services','Нагрузка процессора обеими службами'],null,null,'%',['Average share of one core over 10 minutes','Средняя доля одного ядра за 10 минут']],
  ['switch',['Manual switch, click to done','Ручное переключение, от нажатия до готово'],null,null,'s',['Average of 3 switches to the reserve and 3 back','Среднее из 3 переключений на резерв и 3 обратно']],
  ['status',['Status reply time for the page','Время ответа статуса для страницы'],null,null,'s',['Average of 5 status requests','Среднее из 5 запросов статуса']]]};
function impactValue(value,unit){
  if(value===null||value===undefined||!Number.isFinite(value))return bi('not measured yet','ещё не измерено');
  var units={'MB':[' MB',' МБ'],'MB/day':[' MB/day',' МБ/сутки'],'%':['%',' %'],'s':[' s',' с']}[unit]||['',''];
  return (Math.round(value*10)/10)+bi(units[0],units[1]);
}
function impactChange(work,diagnostic){
  if(!Number.isFinite(work)||!Number.isFinite(diagnostic))return '—';
  if(work===0)return diagnostic===0?'0 %':'+'+impactValue(diagnostic,'');
  var pct=Math.round((diagnostic-work)/work*100);return (pct>0?'+':'')+pct+' %';
}
function renderImpactTable(){
  var head=[bi('What changes','Что меняется'),bi('Work','«Работа»'),bi('Diagnostics','«Диагностика»'),bi('Difference','Разница'),bi('How measured','Как измерено')];
  return E('table',{'class':'table hv-impact-table','data-hv-no-sort':'1'},[E('tr',{},head.map(function(c){return E('th',{'scope':'col'},c);}))].concat(DIAGNOSTIC_IMPACT.rows.map(function(r){
    return E('tr',{'data-impact':r[0]},[E('td',{},bi(r[1][0],r[1][1])),E('td',{},impactValue(r[2],r[4])),E('td',{},impactValue(r[3],r[4])),E('td',{},impactChange(r[2],r[3])),E('td',{},E('small',{},bi(r[5][0],r[5][1])))]);})));
}
function collectionSize(bytes){return Number.isFinite(bytes)?(bytes>=1048576?(bytes/1048576).toFixed(2)+' '+bi('MB','МБ'):bytes>=1024?Math.round(bytes/1024)+' '+bi('KB','КБ'):bytes+' '+bi('B','Б')):'—';}
function collectionLine(model){
  return model.diagnostic?bi('Diagnostics: everything is recorded until ','Диагностика: записывается всё до ')+new Date(model.until*1000).toLocaleString()+bi('; then the router returns to Work by itself.','; потом роутер сам вернётся в «Работу».')
    :bi('Work: only what switching needs is kept.','Работа: хранится только нужное для переключения.');
}
function renderCollectionPage(model){
  model=model||{};var mode=model.diagnostic?'diagnostic':'work',hours=24,busy=false,storage=model.storage||{};
  var line=E('p',{'class':'hv-stats-mode-line','role':'status'},collectionLine(model));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action'},bi('Apply','Применить'));
  // Diagnostics can be chosen only after the owner agreed to its measured consequences (owner decision, 30 Oct 2026).
  var consent=E('input',{'type':'checkbox','class':'hv-stats-consent'});consent.checked=mode==='diagnostic';
  var durations=COLLECTION_HOURS.map(function(h){
    var input=E('input',{'type':'radio','name':'hv-stats-hours','value':String(h[0])});input.checked=h[0]===hours;
    input.addEventListener('change',function(){hours=h[0];});
    return {input:input,label:E('label',{'class':'hv-stats-choice'},[input,' ',bi(h[1],h[2])])};});
  function sync(){
    mode=consent.checked?'diagnostic':'work';
    durations.forEach(function(d){if(consent.checked)d.input.removeAttribute('disabled');else d.input.setAttribute('disabled','');});
    apply.textContent=consent.checked?bi('Start diagnostics','Включить диагностику'):model.diagnostic?bi('Return to Work','Вернуться в «Работу»'):bi('Keep Work','Оставить «Работу»');
  }
  consent.addEventListener('change',sync);
  var choice=E('div',{'class':'hv-stats-choices'},[
    E('label',{'class':'hv-stats-consent-label'},[consent,' ',E('strong',{},bi('I understand the consequences above and want to turn on Diagnostics','Я понимаю последствия, описанные выше, и хочу включить «Диагностику»'))]),
    E('p',{},[E('span',{},bi('Diagnostics duration: ','Срок диагностики: '))].concat(durations.map(function(d){return d.label;}))),
    E('p',{'class':'hv-step-note'},bi('Without the checkbox the router stays in Work. When the chosen time ends it returns to Work by itself; you can also return earlier by clearing the checkbox and pressing the button.','Без галочки роутер остаётся в «Работе». Когда выбранный срок закончится, он сам вернётся в «Работу»; вернуться раньше можно, сняв галочку и нажав кнопку.'))]);
  sync();
  apply.addEventListener('click',function(){
    if(busy||typeof model.save!=='function')return;busy=true;apply.setAttribute('disabled','');
    model.save(mode,hours).then(function(r){
      if(r&&r.saved){line.textContent=collectionLine({diagnostic:mode==='diagnostic',until:Date.now()/1000+hours*3600});if(model.notify)model.notify(bi('Saved. The mode applies from the next check.','Сохранено. Режим применится со следующей проверки.'));}
      else if(model.notify)model.notify((r&&r.code)||'SETUP-SAVE-FAILED');
    },function(){if(model.notify)model.notify('SETUP-SAVE-FAILED');}).then(function(){busy=false;apply.removeAttribute('disabled');});
  });
  var head=[bi('What','Что'),bi('Where','Где'),bi('Size now','Размер сейчас'),bi('In Work','В режиме «Работа»'),bi('In Diagnostics','В режиме «Диагностика»'),bi('Shown on','Где видно')];
  var table=E('table',{'class':'table hv-collection-table','data-hv-no-sort':'1'},[E('tr',{},head.map(function(c){return E('th',{'scope':'col'},c);}))].concat(COLLECTION_ROWS.map(function(r){
    var key=(r[2]==='ram'?'ram:':'flash:')+r[1],size=storage[key];
    return E('tr',{'data-collection':r[0]},[E('td',{},[E('strong',{},bi(r[3][0],r[3][1])),E('br'),E('small',{},bi(r[4][0],r[4][1]))]),
      E('td',{},[r[2]==='ram'?bi('Memory (RAM)','Память (ОЗУ)'):bi('Flash','Флеш'),E('br'),E('small',{},r[1])]),E('td',{},collectionSize(size)),
      E('td',{},bi(r[5][0],r[5][1])),E('td',{},bi(r[6][0],r[6][1])),E('td',{},bi(r[7][0],r[7][1]))]);})));
  var total={ram:0,flash:0};Object.keys(storage).forEach(function(k){if(Number.isFinite(storage[k]))total[k.indexOf('ram:')===0?'ram':'flash']+=storage[k];});
  return E('div',{'class':'hv-collection-page'},[
    E('section',{'class':'hv-chart-card hv-stats-settings','data-stats-settings':'1'},[E('h3',{},bi('Statistics collection mode','Режим сбора статистики')),
      E('p',{},bi('Work is the normal mode: the router keeps only what switching needs. Diagnostics records charts, response history and saved incident and switching statistics for the chosen time, for testing and troubleshooting; then the router returns to Work by itself. Switch statistics are kept in both modes; the recorded charts stay on the router and are shown again the next time Diagnostics is on.','«Работа» — обычный режим: роутер хранит только нужное для переключения. «Диагностика» записывает графики, историю отклика и сохранённую статистику сбоев на выбранный срок — для тестов и разбора ошибок; потом роутер сам возвращается в «Работу». Статистика переключений ведётся в обоих режимах; записанные графики остаются на роутере и снова показываются при следующем включении «Диагностики».')),
      E('h4',{},bi('What Diagnostics costs the router','Чего стоит роутеру «Диагностика»')+(DIAGNOSTIC_IMPACT.measured?' · '+bi('measured ','замер ')+DIAGNOSTIC_IMPACT.measured+(DIAGNOSTIC_IMPACT.version?', '+DIAGNOSTIC_IMPACT.version:''):'')),
      renderImpactTable(),
      choice,line,E('p',{'class':'hv-req-actions'},[apply])]),
    renderRetention(model),
    E('section',{'class':'hv-chart-card'},[E('h3',{},bi('What the router tracks','Что отслеживает роутер')),
      E('p',{},bi('Memory (RAM) is lost when the router restarts and does not wear anything; flash keeps data across restarts and wears out with every write. With all statistics (1.0.0-beta10, 30 Oct 2026) the accounting alone wrote 2 × 477 KB every 15 minutes, about 92 MB per day.','Память (ОЗУ) очищается при перезапуске роутера и ничего не изнашивает; флеш хранит данные между перезапусками и изнашивается от каждой записи. Со всей статистикой (1.0.0-beta10, 30.10.2026) только учёт писал 2 × 477 КБ каждые 15 минут — около 92 МБ в сутки.')),
      E('p',{},bi('Now in use: ','Сейчас занято: ')+bi('memory ','память ')+collectionSize(total.ram)+' · '+bi('flash ','флеш ')+collectionSize(total.flash)),
      table])]);
}
/* Statistics storage (owner, 31 Oct 2026): keep statistics by time (1-7 days, 2 weeks, 1 month) or by a size limit in MB,
   with a live estimate of flash and RAM. Same model as retention_settings.py / lua/retention.lua; the router sends its
   constants in status.stats_mode.retention.model, this copy only serves an older router. */
var RETENTION_STOPS=[1,2,3,4,5,6,7,14,30],RETENTION_MIB=1048576;
var RETENTION_MODEL={latency_row_flash_fast:79,latency_row_flash_slow:57,response_row_flash:69,latency_row_ram:422,response_row_ram:548,
  accounting_day_flash:69778,accounting_cap:3145728,accounting_ram_ratio:7,compare_flash:36421,compare_ram:212753};
function retentionPerDay(r){
  var m=(r&&r.model)||RETENTION_MODEL,i=Number(r&&r.interval);if(!(Number.isInteger(i)&&i>=10&&i<=300))i=10;
  var rows=Math.floor(86400/Math.max(60,i));
  return {m:m,latency:[rows*(i<60?m.latency_row_flash_fast:m.latency_row_flash_slow),rows*m.latency_row_ram],response:[rows*m.response_row_flash,rows*m.response_row_ram],accounting:m.accounting_day_flash};
}
// retention_settings.estimate(settings, days)
function retentionEstimate(r,days){
  var p=retentionPerDay(r),m=p.m,compare=!!(r&&r.compare),acc=Math.min(m.accounting_cap,days*p.accounting);
  return {flash:days*(p.latency[0]+p.response[0])+2*acc+(compare?m.compare_flash:0),ram:days*(p.latency[1]+p.response[1])+acc*m.accounting_ram_ratio+(compare?m.compare_ram:0),
    work_flash:2*acc,work_ram:acc*m.accounting_ram_ratio};
}
// retention_settings.size_days(settings, mb)
function retentionSizeDays(r,mb){
  var p=retentionPerDay(r),budget=mb*RETENTION_MIB-(r&&r.compare?p.m.compare_flash:0);
  return Math.max(1,Math.min(30,Math.floor(budget/(p.latency[0]+p.response[0]+2*p.accounting))));
}
function retentionDays(n){
  if(n===14)return bi('2 weeks','2 недели');if(n===30)return bi('1 month','1 месяц');
  var ten=n%10,hundred=n%100,ru=ten===1&&hundred!==11?'день':ten>=2&&ten<=4&&(hundred<10||hundred>=20)?'дня':'дней';
  return n+' '+bi(n===1?'day':'days',ru);
}
function retentionMB(bytes){var v=bytes/RETENTION_MIB,t=v>=10?String(Math.round(v)):v>=.1?v.toFixed(1):'0.1';return bi(t+' MB',t.replace('.',',')+' МБ');}
function retentionFill(input,min,max){input.setAttribute('style','--hv-fill:'+Math.round((Number(input.value)-min)/(max-min)*100)+'%');}
function renderRetention(model){
  var r=Object.assign({},model.retention||{}),cap=model.capacity||{},storage=model.storage||{},busy=false;
  var savedMode=r.mode==='size'?'size':'time',savedDays=RETENTION_STOPS.indexOf(Number(r.days))>=0?Number(r.days):7;
  var mbMin=Number(r.mb_min)||1,mbMax=Number(r.mb_max)||32,savedMb=Number(r.mb)>=mbMin&&Number(r.mb)<=mbMax?Number(r.mb):4;
  var mode=savedMode,dayIndex=RETENTION_STOPS.indexOf(savedDays),mb=savedMb;
  // In time mode the MB slider starts at the size of the current period, so switching shows an equivalent choice.
  if(savedMode==='time')mb=Math.max(mbMin,Math.min(mbMax,Math.ceil(retentionEstimate(r,savedDays).flash/RETENTION_MIB)));
  var radios={},panels={};
  ['time','size'].forEach(function(key){
    var input=E('input',{'type':'radio','name':'hv-retention-mode','value':key,'class':'hv-retention-radio'});input.checked=key===mode;
    input.addEventListener('change',function(){if(input.checked){mode=key;update();}});radios[key]=input;
  });
  var days=E('input',{'type':'range','id':'hv-retention-days','class':'hv-retention-range','min':'0','max':String(RETENTION_STOPS.length-1),'step':'1'});days.value=String(dayIndex);
  var size=E('input',{'type':'range','id':'hv-retention-mb','class':'hv-retention-range','min':String(mbMin),'max':String(mbMax),'step':'1'});size.value=String(mb);
  var daysOut=E('output',{'class':'hv-retention-value','for':'hv-retention-days'}),sizeOut=E('output',{'class':'hv-retention-value','for':'hv-retention-mb'});
  days.addEventListener('input',function(){dayIndex=Number(days.value);update();});size.addEventListener('input',function(){mb=Number(size.value);update();});
  var stops=E('div',{'class':'hv-retention-stops','aria-hidden':'true'},RETENTION_STOPS.map(function(d){return E('span',{},d===14?bi('2 wk','2 нед'):d===30?bi('1 mo','1 мес'):String(d));}));
  var marks=E('div',{'class':'hv-retention-stops hv-retention-mb-stops','aria-hidden':'true'},[mbMin,Math.round(mbMax/4),Math.round(mbMax/2),Math.round(mbMax*3/4),mbMax].map(function(v){return E('span',{},String(v));}));
  panels.time=E('div',{'class':'hv-retention-panel','data-retention-panel':'time'},[E('div',{'class':'hv-retention-head'},[E('label',{'for':'hv-retention-days'},bi('Keep statistics for','Хранить статистику')),daysOut]),days,stops]);
  panels.size=E('div',{'class':'hv-retention-panel','data-retention-panel':'size'},[E('div',{'class':'hv-retention-head'},[E('label',{'for':'hv-retention-mb'},bi('Statistics may take up to','Статистика может занимать до')),sizeOut]),size,marks]);
  var holds=E('span',{}),flashText=E('span',{'class':'hv-retention-amount'}),ramText=E('span',{'class':'hv-retention-amount'});
  var flashBar=E('span',{'class':'hv-retention-bar-fill'}),ramBar=E('span',{'class':'hv-retention-bar-fill'});
  var flashRoom=E('span',{'class':'hv-retention-room'}),ramRoom=E('span',{'class':'hv-retention-room'});
  var work=E('p',{'class':'hv-step-note hv-retention-work'}),warn=E('p',{'class':'hv-retention-warn','role':'alert'}),current=E('p',{'class':'hv-retention-current'});
  function meter(key,label,text,bar,room){return E('div',{'class':'hv-retention-meter','data-retention-meter':key},[E('div',{'class':'hv-retention-meter-head'},[E('strong',{},label),text]),E('span',{'class':'hv-retention-bar'},bar),room]);}
  var save=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-retention-save','disabled':''},bi('Save','Сохранить'));
  // Room: free flash plus what the statistics files already take; available RAM plus what the current period already holds.
  var used=0;Object.keys(storage).forEach(function(k){if(k.indexOf('flash:')===0&&Number.isFinite(storage[k]))used+=storage[k];});
  var flashRoomBytes=Number.isFinite(cap.flash_free)?cap.flash_free+used:null;
  var ramRoomBytes=Number.isFinite(cap.ram_available)?cap.ram_available+retentionEstimate(r,Number(r.effective_days)||savedDays).ram:null;
  function chosenDays(){return mode==='time'?RETENTION_STOPS[dayIndex]:retentionSizeDays(r,mb);}
  function level(value,room,warnShare,badShare){return room===null?'unknown':value>room*badShare?'bad':value>room*warnShare?'warn':'ok';}
  function show(bar,room,value,state,node){
    bar.setAttribute('style','width:'+(room===null||room<=0?0:Math.min(100,Math.round(value/room*100)))+'%');bar.setAttribute('data-level',state);
    node.textContent=room===null?bi('free space unknown','свободное место неизвестно'):bi('of ','из ')+retentionMB(room)+bi(' available',' доступно');
  }
  function update(){
    ['time','size'].forEach(function(key){panels[key].hidden=key!==mode;radios[key].checked=key===mode;});
    var d=chosenDays(),e=retentionEstimate(r,d);
    daysOut.textContent=retentionDays(RETENTION_STOPS[dayIndex]);sizeOut.textContent=retentionMB(mb*RETENTION_MIB);
    days.setAttribute('aria-valuetext',retentionDays(RETENTION_STOPS[dayIndex]));size.setAttribute('aria-valuetext',retentionMB(mb*RETENTION_MIB));
    retentionFill(days,0,RETENTION_STOPS.length-1);retentionFill(size,mbMin,mbMax);
    holds.textContent=mode==='size'?bi('This holds about ','Этого хватит примерно на ')+retentionDays(d)+(d===30?bi(' (the maximum: more megabytes keep no longer)',' (максимум: больше мегабайт срок не продлят)'):'')+'.':'';
    flashText.textContent=' ≈ '+retentionMB(e.flash);ramText.textContent=' ≈ '+retentionMB(e.ram);
    var fs=level(e.flash,flashRoomBytes===null?null:Math.max(0,flashRoomBytes-RETENTION_MIB),.5,1),rs=level(e.ram,ramRoomBytes,.25,.5);
    show(flashBar,flashRoomBytes,e.flash,fs,flashRoom);show(ramBar,ramRoomBytes,e.ram,rs,ramRoom);
    work.textContent=bi('Estimate while Diagnostics records. In Work only the accounting grows: ≈ ','Оценка на время «Диагностики». В режиме «Работа» растёт только учёт: ≈ ')+retentionMB(e.work_flash)+bi(' on flash, ≈ ',' на флеше, ≈ ')+retentionMB(e.work_ram)+bi(' in RAM.',' в ОЗУ.');
    var notes=[];
    if(fs==='bad')notes.push(bi('The flash may run out: less than 1 MB would stay free. Choose a shorter period or a smaller size.','Флеш может закончиться: свободным останется меньше 1 МБ. Выберите срок короче или объём меньше.'));
    else if(fs==='warn')notes.push(bi('This would take more than half of the free flash.','Это займёт больше половины свободного флеша.'));
    if(rs==='bad')notes.push(bi('The monitor would hold more than half of the available RAM; the router may slow down or restart services.','Мониторинг будет держать больше половины доступной ОЗУ: роутер может замедлиться или перезапускать службы.'));
    else if(rs==='warn')notes.push(bi('The monitor would hold more than a quarter of the available RAM.','Мониторинг будет держать больше четверти доступной ОЗУ.'));
    warn.textContent=notes.join(' ');warn.hidden=!notes.length;
    var changed=!r.mode||mode!==savedMode||(mode==='time'?RETENTION_STOPS[dayIndex]!==savedDays:mb!==savedMb);
    if(changed&&!busy)save.removeAttribute('disabled');else save.setAttribute('disabled','');
  }
  function describe(){
    current.textContent=!r.mode?bi('The router has not reported this setting yet (an older version keeps 1–7 days).','Роутер ещё не сообщил эту настройку (старая версия хранит 1–7 дней).')
      :bi('Saved: ','Сохранено: ')+(savedMode==='size'?bi('up to ','до ')+retentionMB(savedMb*RETENTION_MIB)+' → '+retentionDays(Number(r.effective_days)||retentionSizeDays(r,savedMb)):retentionDays(savedDays))+'.';
  }
  save.addEventListener('click',function(){
    if(busy||typeof model.saveRetention!=='function')return;busy=true;save.setAttribute('disabled','');
    var value=mode==='time'?RETENTION_STOPS[dayIndex]:mb,chosen=mode;
    model.saveRetention(chosen,value).then(function(reply){
      if(reply&&reply.saved){savedMode=chosen;if(chosen==='time')savedDays=value;else savedMb=value;r.mode=chosen;r.effective_days=chosen==='time'?value:retentionSizeDays(r,value);describe();
        if(model.notify)model.notify(bi('Saved. The router applies the new period from its next check.','Сохранено. Роутер применит новый срок со следующей проверки.'));}
      else if(model.notify)model.notify((reply&&reply.code)||'SETUP-SAVE-FAILED');
    },function(){if(model.notify)model.notify('SETUP-SAVE-UNCONFIRMED');}).then(function(){busy=false;update();});
  });
  describe();update();
  return E('section',{'class':'hv-chart-card hv-retention','data-stats-retention':'1'},[
    E('h3',{},bi('How long statistics are kept','Сколько хранить статистику')),
    E('p',{},bi('Choose a period or a size limit. The router deletes the oldest statistics beyond it. Switching and Auto never depend on this: only charts, rankings and reports remember more or less.','Выберите срок или ограничение объёма. Роутер удаляет самую старую статистику сверх него. Переключение и Auto от этого не зависят: меняется только то, сколько помнят графики, рейтинги и отчёты.')),
    E('fieldset',{'class':'hv-retention-mode'},[E('legend',{},bi('Limit statistics','Ограничивать статистику')),
      E('label',{'class':'hv-retention-choice'},[radios.time,E('span',{},bi('by time','по времени'))]),
      E('label',{'class':'hv-retention-choice'},[radios.size,E('span',{},bi('by size (MB)','по объёму (МБ)'))])]),
    panels.time,panels.size,
    E('div',{'class':'hv-retention-estimate','role':'status','aria-live':'polite'},[E('p',{'class':'hv-retention-holds'},holds),
      E('div',{'class':'hv-retention-meters'},[meter('flash',bi('On flash','На флеше'),flashText,flashBar,flashRoom),meter('ram',bi('In RAM','В ОЗУ'),ramText,ramBar,ramRoom)]),work]),
    warn,current,E('p',{'class':'hv-req-actions'},[save]),
    E('details',{'class':'hv-retention-help'},[E('summary',{},bi('How the estimate is calculated','Как считается оценка')),
      E('p',{},bi('The numbers are an estimate, not a measurement of your router. The delay and response histories keep one row per observed minute: about 80 and 70 bytes on flash and 420 and 550 bytes in RAM per row (measured on the real file formats). The traffic and quality accounting grows by about 68 KB a day (measured: 477 KB for 7 days on the MT3000) and is kept twice on flash (with a backup copy), up to its own 3 MB limit. "Measure all methods" adds about 36 KB of hourly means.','Числа — оценка, а не замер вашего роутера. Истории задержки и отклика хранят одну строку на каждую наблюдаемую минуту: около 80 и 70 байт на флеше и 420 и 550 байт в ОЗУ на строку (замерено на настоящих форматах файлов). Учёт трафика и качества растёт примерно на 68 КБ в сутки (замер: 477 КБ за 7 дней на MT3000) и хранится на флеше дважды (с резервной копией), до своего предела 3 МБ. «Мерить все способы» добавляет около 36 КБ часовых средних.')),
      E('p',{},bi('By size: the router keeps as many whole days as fit the limit (1 to 30) and, if a history file still grows beyond its share, drops its oldest rows when saving. Warnings: flash when less than 1 MB would stay free or more than half of the free flash would be used; RAM when the monitor would hold more than a quarter (or half) of the available memory.','По объёму: роутер хранит столько целых дней, сколько помещается в предел (от 1 до 30), а если файл истории всё же вырастает сверх своей доли, при сохранении удаляет его самые старые строки. Предупреждения: флеш — если свободным останется меньше 1 МБ или будет занято больше половины свободного места; ОЗУ — если мониторинг будет держать больше четверти (или половины) доступной памяти.')),
      E('p',{},bi('Not included: the switch event history (switches are rare, at most 2 MB), the last 10,000 check samples in memory, speed and failure tests. The chart on the page shows at most the newest week; longer periods feed the statistics and rankings.','Не входит: история событий переключения (переключения редки, не больше 2 МБ), последние 10 000 проверок в памяти, тесты скорости и сбоя. График на странице показывает не больше последней недели; более долгий срок идёт в статистику и рейтинги.'))])]);
}
