/* Advanced > Switch statistics: episodes derived from saved events (switchTimeline in the main page), drawn with the shared phase chart.
   A recovery after a fault or restart (power cut, crashed supervisor, give-up) has its own kind, colour and outcome; it is never drawn
   as a switch and never enters the averages. */
var SWITCH_RESERVE_CAP=120;
function switchKindText(kind){return {auto:bi('Automatic','Автоматическое'),manual:bi('Manual','Ручное'),test:bi('Test','Тест'),recovery:bi('Recovery after a fault or restart','Восстановление после сбоя или перезапуска')}[kind]||bi('Not saved','Не сохранено');}
function switchPhases(){return MEASURE_PHASES.concat([['Recovery after a fault or restart (not a switch)','Восстановление после сбоя или перезапуска (не переключение)','#8e44ad']]);}
function switchWhen(t){return Number.isFinite(t)?new Date(t*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';}
function switchStatsOf(values){values=values.filter(Number.isFinite);if(!values.length)return null;return {n:values.length,mean:measureMean(values),min:Math.min.apply(null,values),max:Math.max.apply(null,values)};}
function switchResult(e,last,now){
  if(e.kind==='recovery'){
    var took=Number.isFinite(e.end)&&e.end>e.rec?' '+bi('after ','через ')+spanText(e.end-e.rec):'';
    if(e.outcome==='gave-up')return bi('Recovery given up','Восстановление прекращено')+took+' ('+e.code+'); '+bi('Auto stopped','Auto остановлен');
    if(e.outcome==='source')return bi('Recovered: traffic on the primary','Восстановлено: трафик на основном')+took;
    if(e.outcome==='target')return bi('Recovered: traffic on the reserve','Восстановлено: трафик на резерве')+took;
    if(e.outcome==='restart')return bi('Ended by a new start of Auto; the end of the recovery was not saved','Завершено новым запуском Auto; окончание восстановления не сохранено');
    return last&&!e.closed&&now-e.rec<900?bi('Recovering now','Идёт восстановление'):bi('End of the recovery not saved','Окончание восстановления не сохранено');
  }
  if(e.cut)return bi('Interrupted by a fault or restart','Прервано сбоем или перезапуском');
  if(e.rolledBack!==null)return bi('Attempt ended without a switch','Попытка завершилась без переключения');
  if(e.back!==null)return bi('Back on the primary','Снова на основном');
  if(e.returnStart!==null)return last?bi('Returning now','Идёт возврат'):bi('Return end not saved','Конец возврата не сохранён');
  if(e.reserve!==null)return last?bi('On the reserve now','Сейчас на резерве'):bi('Return not saved','Возврат не сохранён');
  return last&&Number.isFinite(e.start)&&now-e.start<900?bi('Switching now','Идёт переключение'):bi('End not saved','Окончание не сохранено');
}
function switchChartRows(episodes,now){
  return episodes.map(function(e,i){
    var last=i===episodes.length-1,o=e.time,segs=[],shift=0;
    // The reserve phase is shortened on the axis; later phases move left by the cut, labels keep the real length.
    function add(k,a,b,open){var real=b-a;if(!Number.isFinite(real)||real<0)return;var shown=k===3||k===5?Math.min(real,SWITCH_RESERVE_CAP):real,from=a-o-shift;
      segs.push({k:k,from:from,to:from+shown,tip:real||open?spanText(real)+(open?bi(' (still going)',' (продолжается)'):''):bi('length not saved','длительность не сохранена'),label:spanText(real),open:!!open});shift+=real-shown;}
    if(e.kind==='recovery'){var end=Number.isFinite(e.end)?e.end:last&&!e.closed&&now-e.rec<900?now:e.rec;add(5,e.rec,end,end===now&&end!==e.end);}
    if(e.failure!==null&&e.start!==null)add(1,e.failure,e.start);
    if(e.start!==null&&e.reserve!==null)add(2,e.start,e.reserve);else if(e.start!==null&&e.rolledBack!==null)add(2,e.start,e.rolledBack);else if(last&&!e.closed&&e.start!==null&&now-e.start<900)add(2,e.start,now,true);
    if(e.reserve!==null&&e.returnStart!==null)add(3,e.reserve,e.returnStart);else if(e.reserve!==null&&e.back!==null&&e.returnStart===null)add(3,e.reserve,e.back);else if(last&&!e.closed&&e.reserve!==null&&e.back===null)add(3,e.reserve,now,true);
    if(e.returnStart!==null&&e.back!==null)add(4,e.returnStart,e.back);else if(last&&!e.closed&&e.returnStart!==null&&e.back===null&&now-e.returnStart<900)add(4,e.returnStart,now,true);
    return {label:switchWhen(e.time)+' '+(e.kind==='manual'?'M':e.kind==='test'?'T':e.kind==='auto'?'A':e.kind==='recovery'?'R':'?'),segs:segs};
  });
}
function renderSwitchPage(model){
  model=model||{};var all=Array.isArray(model.episodes)?model.episodes:[],now=Number.isFinite(model.now)?model.now:Date.now()/1000,shown=all.slice(-20),timing=model.timing;
  var legend=E('p',{'class':'hv-measure-legend'},switchPhases().slice(1).map(function(p){return E('span',{},[E('i',{'style':'background:'+p[2]}),' '+bi(p[0],p[1])]);}));
  var intro=E('p',{},bi('Every switch is measured from the router events: the first failed check of the primary, the start of the switch, traffic confirmed on the reserve, the start of the return and traffic back on the primary. A dash means that moment was not saved; nothing is estimated. A recovery after a fault or restart (for example after a power cut, when the router puts the saved channel order back or gives up) is shown separately: it is not a switch and is not counted in the averages.','Каждое переключение измеряется по событиям роутера: первая неудачная проверка основного канала, начало перехода, трафик подтверждён на резерве, начало возврата и трафик снова на основном. Прочерк означает, что этот момент не сохранился; ничего не досчитывается. Восстановление после сбоя или перезапуска (например, после отключения питания, когда роутер возвращает сохранённый порядок каналов или прекращает попытки) показано отдельно: это не переключение, и в средние оно не входит.'));
  var phases=E('ul',{},[
    E('li',{},bi('Detection: from the first failed check to the start of the switch. Auto waits for several failed checks in a row so that one lost packet does not move your traffic.','Обнаружение: от первой неудачной проверки до начала перехода. Auto ждёт несколько неудачных проверок подряд, чтобы одна потеря пакета не переводила трафик.')),
    E('li',{},bi('Switching: from the start of the switch until traffic is confirmed on the reserve (the router rebuilds its VPN routing and checks the reserve).','Переключение: от начала перехода до подтверждения трафика на резерве (роутер перестраивает маршрутизацию VPN и проверяет резерв).')),
    E('li',{},bi('On the reserve: how long traffic stayed on the reserve. On the chart this phase is cut to '+SWITCH_RESERVE_CAP+' s; its real length is written on the bar and in the table.','На резерве: сколько трафик шёл через резерв. На графике эта фаза укорочена до '+SWITCH_RESERVE_CAP+' с; настоящая длительность написана на полосе и в таблице.')),
    E('li',{},bi('Return: from the start of the return until traffic is confirmed on the primary again.','Возврат: от начала возврата до подтверждения трафика снова на основном.')),
    E('li',{},bi('Recovery after a fault or restart: from the first saved recovery step (after a reboot, a power cut or a restart of the supervisor) to its saved result - traffic restored, or the recovery given up and Auto stopped. It is drawn in its own colour, cut to '+SWITCH_RESERVE_CAP+' s like the reserve phase, and is not a switch: the averages above do not include it.','Восстановление после сбоя или перезапуска: от первого сохранённого шага восстановления (после перезагрузки, отключения питания или перезапуска супервизора) до его сохранённого итога — трафик восстановлен, либо попытки прекращены и Auto остановлен. Оно нарисовано своим цветом, укорочено до '+SWITCH_RESERVE_CAP+' с, как фаза резерва, и не является переключением: средние выше его не учитывают.')),
    E('li',{},bi('The moment the fault really began is not known to the router: it can only see the first failed check. Help → Measured results of Auto mode shows controlled tests where the fault start was known.','Момент, когда сбой действительно начался, роутеру неизвестен: он видит только первую неудачную проверку. В «Помощи → Результаты замеров работы в автоматическом режиме» есть контролируемые тесты, где начало сбоя было известно.'))]);
  var nodes=[E('h3',{},bi('Switch statistics','Статистика переключений')),intro];
  var switched=all.filter(function(e){return e.reserve!==null;}),returned=all.filter(function(e){return e.back!==null;}),recovered=all.filter(function(e){return e.kind==='recovery';});
  var stats={detect:switchStatsOf(all.map(function(e){return e.detect;})),switching:switchStatsOf(all.map(function(e){return e.switching;})),total:switchStatsOf(all.map(function(e){return e.total;})),returning:switchStatsOf(all.map(function(e){return e.returning;}))};
  function card(label,value,detail){return E('div',{'class':'hv-switch-card'},[E('span',{},label),E('strong',{},value),E('small',{},detail)]);}
  function range(st){return st?bi('min ','мин. ')+spanText(st.min)+' · '+bi('max ','макс. ')+spanText(st.max)+' · n='+st.n:bi('No measurements yet','Замеров пока нет');}
  nodes.push(E('div',{'class':'hv-switch-cards','data-switch-cards':'1'},[
    card(bi('Switches to the reserve','Переключений на резерв'),String(switched.length),bi('automatic ','автоматических ')+switched.filter(function(e){return e.kind==='auto';}).length+' · '+bi('manual ','ручных ')+switched.filter(function(e){return e.kind==='manual';}).length+' · '+bi('returns ','возвратов ')+returned.length+(recovered.length?' · '+bi('recoveries after a fault ','восстановлений после сбоя ')+recovered.length:'')),
    card(bi('Detection (mean)','Обнаружение (среднее)'),stats.detect?spanText(stats.detect.mean):'—',range(stats.detect)),
    card(bi('Switching (mean)','Переключение (среднее)'),stats.switching?spanText(stats.switching.mean):'—',range(stats.switching)),
    card(bi('Failure → reserve (mean)','Сбой → резерв (среднее)'),stats.total?spanText(stats.total.mean):'—',range(stats.total)),
    card(bi('Return (mean)','Возврат (среднее)'),stats.returning?spanText(stats.returning.mean):'—',range(stats.returning)),
    card(bi('Router switch average','Среднее роутера'),timing&&Number.isFinite(timing.avg_seconds)?spanText(timing.avg_seconds):'—',timing&&Number.isFinite(timing.avg_seconds)?bi('switches counted ','учтено переключений ')+timing.count+(Number.isFinite(timing.last_seconds)?' · '+bi('last ','последнее ')+spanText(timing.last_seconds):'')+' · '+bi('used by the countdown','используется обратным отсчётом'):bi('No confirmed switch saved yet','Подтверждённых переключений ещё нет'))]));
  if(!all.length){
    nodes.push(E('p',{'class':'alert-message','data-switch-empty':'1'},model.history===false?bi('The event history has not arrived yet. It is loaded about once a minute while this page is open.','История событий ещё не загружена. Пока страница открыта, она загружается примерно раз в минуту.'):bi('No switches in the saved history yet. When Auto or you switch the channel, the measured times appear here.','В сохранённой истории пока нет переключений. Когда Auto или вы переключите канал, здесь появятся измеренные времена.')));
    nodes.push(E('h4',{},bi('Phases','Фазы')),phases);return E('div',{'class':'hv-switch-stats'},nodes);
  }
  nodes.push(E('h4',{},bi('The switching process over time','Процесс переключения во времени')+' · '+(shown.length<all.length?bi('last ','последние ')+shown.length+bi(' of ',' из ')+all.length:String(all.length))));
  nodes.push(legend,phaseChart(switchChartRows(shown,now),{phases:switchPhases(),title:bi('Switching phases per episode, seconds from the first known moment','Фазы каждого переключения, секунды от первого известного момента'),left:110}));
  nodes.push(E('p',{},bi('Each bar is one episode, the newest is at the bottom. A = automatic, M = manual, T = test, R = recovery after a fault or restart (purple, not a switch, not in the averages), ? = type not saved. The bar starts at the first failed check, or at the first saved moment if that check is not known.','Каждая полоса — один эпизод, новый внизу. A — автоматическое, M — ручное, T — тест, R — восстановление после сбоя или перезапуска (фиолетовая, не переключение, в средние не входит), ? — тип не сохранён. Полоса начинается с первой неудачной проверки или с первого сохранённого момента, если она неизвестна.')));
  var cols=[bi('Time','Время'),bi('Type','Тип'),bi('Detection','Обнаружение'),bi('Switching','Переключение'),bi('Failure → reserve','Сбой → резерв'),bi('On the reserve','На резерве'),bi('Return','Возврат'),bi('Primary was down','Основной не работал'),bi('Result','Итог')];
  var table=E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1','data-switch-table':'1'},[E('tr',{},cols.map(function(c){return E('th',{'scope':'col'},c);}))]);
  shown.slice().reverse().forEach(function(e,i){table.appendChild(E('tr',{'data-switch-key':e.key},[switchWhen(e.time),switchKindText(e.kind)+(e.returnKind&&e.returnKind!==e.kind&&e.back!==null?' / '+switchKindText(e.returnKind):''),spanText(e.detect),spanText(e.switching),spanText(e.total),spanText(e.onReserve),spanText(e.returning),spanText(e.down),switchResult(e,i===0,now)].map(function(v){return E('td',{},v);})));});
  var mean=['detect','switching','total','onReserve','returning','down'].map(function(k){var st=switchStatsOf(shown.map(function(e){return e[k];}));return st?spanText(st.mean):'—';});
  table.appendChild(E('tr',{'class':'hv-measure-mean'},[E('th',{'scope':'row'},bi('Mean','Среднее')),E('td',{},'')].concat(mean.map(function(v){return E('td',{},v);}),[E('td',{},'')])));
  nodes.push(E('div',{'class':'hv-dv-tablewrap'},table),E('h4',{},bi('Phases','Фазы')),phases);
  nodes.push(E('p',{},[bi('The same times are written in ','Те же времена записаны в '),E('a',{'href':'#events'},bi('Events and errors','Событиях и ошибках')),bi(' and in the ',' и в '),E('a',{'href':'#services'},bi('Live log','Живом журнале')),'.']));
  return E('div',{'class':'hv-switch-stats'},nodes);
}
