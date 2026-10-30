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
    E('section',{'class':'hv-chart-card'},[E('h3',{},bi('What the router tracks','Что отслеживает роутер')),
      E('p',{},bi('Memory (RAM) is lost when the router restarts and does not wear anything; flash keeps data across restarts and wears out with every write. With all statistics (1.0.0-beta10, 30 Oct 2026) the accounting alone wrote 2 × 477 KB every 15 minutes, about 92 MB per day.','Память (ОЗУ) очищается при перезапуске роутера и ничего не изнашивает; флеш хранит данные между перезапусками и изнашивается от каждой записи. Со всей статистикой (1.0.0-beta10, 30.10.2026) только учёт писал 2 × 477 КБ каждые 15 минут — около 92 МБ в сутки.')),
      E('p',{},bi('Now in use: ','Сейчас занято: ')+bi('memory ','память ')+collectionSize(total.ram)+' · '+bi('flash ','флеш ')+collectionSize(total.flash)),
      table])]);
}
