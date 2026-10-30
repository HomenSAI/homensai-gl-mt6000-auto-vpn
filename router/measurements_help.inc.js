/* Help: measured Auto behaviour on the dedicated GL-MT3000 (controlled faults of the primary WireGuard). Data are
   seconds from the start of the fault: first failed check, switch started, traffic on reserve, return started, back on primary. */
var AUTO_MEASUREMENTS=[
  {id:'night-2026-10-30',version:'0.9.1-alpha82',level:1,boost:true,fault:180,
   title:['Night 30 Oct 2026 · level 1 + boost · 8 faults of 180 s, once an hour','Ночь 30.10.2026 · уровень 1 + ускорение · 8 сбоев по 180 с, раз в час'],
   rows:[['00:26',71,114,160,230,273],['01:26',73,119,175,237,283],['02:26',67,118,183,248,286],['03:26',61,112,174,241,281],
         ['04:26',54,103,168,237,279],['05:26',47,99,165,233,286],['06:27',48,101,169,235,288],['07:27',48,116,174,247,292]]},
  {id:'level3-2026-10-30',version:'0.9.1-alpha82',level:3,boost:true,fault:150,
   title:['Morning 30 Oct 2026 · level 3 + boost · 4 faults of 150 s, every 5 min','Утро 30.10.2026 · уровень 3 + ускорение · 4 сбоя по 150 с, каждые 5 мин'],
   rows:[['08:29',34,91,150,215,267],['08:34',28,80,150,209,266],['08:39',27,92,150,229,272],['08:44',29,108,163,228,276]]},
  {id:'level4-2026-10-30',version:'0.9.1-alpha82',level:4,boost:true,fault:150,
   title:['Morning 30 Oct 2026 · level 4 + boost · 4 faults of 150 s, every 5 min','Утро 30.10.2026 · уровень 4 + ускорение · 4 сбоя по 150 с, каждые 5 мин'],
   rows:[['08:50',38,98,158,217,271],['08:55',28,83,159,210,254],['09:00',27,78,140,204,252],['09:05',26,97,159,216,269]]},
  {id:'level5-2026-10-30',version:'0.9.1-alpha82',level:5,boost:true,fault:150,
   title:['Morning 30 Oct 2026 · level 5 + boost · 3 of 4 faults of 150 s (one refused by the switch budget)','Утро 30.10.2026 · уровень 5 + ускорение · 3 из 4 сбоев по 150 с (один остановлен лимитом переключений)'],
   rows:[['09:11',32,91,162,220,273],['09:16',33,88,152,219,273],['09:26',27,91,157,218,271]]},
  {id:'beta5-level3-2026-10-30',version:'1.0.0-beta5',level:3,boost:true,fault:150,
   title:['Afternoon 30 Oct 2026 · fast switch · level 3 + boost · 3 of 4 faults of 150 s (one rolled back: GL worker busy, fixed in beta7)','День 30.10.2026 · быстрое переключение · уровень 3 + ускорение · 3 из 4 сбоев по 150 с (один откат: занят обработчик GL, исправлено в beta7)'],
   rows:[['15:26',31,79,123,203,228],['15:40',33,98,140,213,236],['15:47',20,78,124,204,227]]},
  {id:'beta7-level3-2026-10-30',version:'1.0.0-beta7',level:3,boost:true,fault:150,
   title:['Afternoon 30 Oct 2026 · fast switch · level 3 + boost · 3 faults of 150 s','День 30.10.2026 · быстрое переключение · уровень 3 + ускорение · 3 сбоя по 150 с'],
   rows:[['16:09',36,104,145,201,226],['16:16',20,83,123,200,227],['16:23',29,103,140,216,240]]}
];
// Speed by program version (MT3000, 30 Oct 2026; means of the runs above and of the manual-button measurements).
// Each bar: stages in seconds, in order. Auto: from the fault start to traffic on the reserve. Manual: from the click to done.
var VERSION_STAGES={
  auto:[['Fault not yet noticed','Сбой ещё не замечен','#9aa3ad'],['Confirming the failure','Подтверждение сбоя','#e0b100'],['Switch itself','Само переключение','#e07800']],
  manual:[['Button request','Запрос кнопки','#7c3aed'],['Waiting for Auto','Ожидание Auto','#9aa3ad'],['Checks before','Проверки до','#e0b100'],
          ['Route change','Смена маршрута','#2f9e57'],['Checks after and confirmation','Проверки после и подтверждение','#e07800'],['Saving and display','Запись и отображение','#2563eb']]};
var VERSION_HISTORY={
  auto:[{version:'0.9.1-alpha82',how:['GL rebuild (rtp2)','перестройка GL (rtp2)'],runs:4,stages:[29.5,63.3,60.5],ret:50},
        {version:'1.0.0-beta5',how:['fast switch','быстрое переключение'],runs:3,stages:[28,57,44],ret:23.7},
        {version:'1.0.0-beta7',how:['fast switch','быстрое переключение'],runs:3,stages:[28.3,68.3,39.3],ret:25.3}],
  manual:[{version:'1.0.0-beta7',how:['full guarded transaction','полная защищённая транзакция'],runs:1,stages:[4.6,2.8,12.1,5.5,15.7,1.5],moved:25},
          {version:'1.0.0-beta8',how:['instant manual switch','мгновенное ручное переключение'],runs:6,stages:[3.5,1.7,5.3,0.3,3.7,2.1],moved:10.8}]};
function versionHistoryChart(kind){
  var stages=VERSION_STAGES[kind];
  return phaseChart(VERSION_HISTORY[kind].map(function(v){var at=0;
    return {label:v.version.replace('0.9.1-','').replace('1.0.0-',''),segs:v.stages.map(function(s,k){var seg={k:k,from:at,to:at+s,tip:Math.round(s*10)/10+bi(' s',' с'),label:Math.round(s*10)/10+bi(' s',' с')};at+=s;return seg;})};}),
    {title:kind==='auto'?bi('Auto: fault to traffic on the reserve, by version','Auto: от сбоя до трафика на резерве, по версиям'):bi('Manual button: click to done, by version','Ручная кнопка: от нажатия до готово, по версиям'),phases:stages,left:84});
}
function versionHistoryTable(kind){
  var stages=VERSION_STAGES[kind],rows=VERSION_HISTORY[kind];
  var head=[bi('Version','Версия'),bi('How','Как')].concat(stages.map(function(s){return bi(s[0],s[1]);})).concat([bi('Total','Итого'),kind==='auto'?bi('Return','Возврат'):bi('Traffic moved at','Трафик перешёл через')]);
  var t=E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1'},[E('tr',{},head.map(function(c){return E('th',{'scope':'col'},c);}))]);
  rows.forEach(function(v){var total=v.stages.reduce(function(a,b){return a+b;},0);
    t.appendChild(E('tr',{},[v.version+' ('+v.runs+')',bi(v.how[0],v.how[1])].concat(v.stages.map(function(s){return Math.round(s*10)/10+bi(' s',' с');})).concat([Math.round(total*10)/10+bi(' s',' с'),(kind==='auto'?v.ret:v.moved)+bi(' s',' с')]).map(function(c){return E('td',{},c);})));});
  return t;
}
function renderVersionHistory(){
  function legend(kind){return E('p',{'class':'hv-measure-legend'},VERSION_STAGES[kind].map(function(p){return E('span',{},[E('i',{'style':'background:'+p[2]}),' '+bi(p[0],p[1])]);}));}
  return E('section',{'class':'hv-measure-set','data-measure-set':'versions'},[
    E('h4',{},bi('Speed by version','Скорость по версиям')),
    E('p',{},bi('The same MT3000 and the same controlled faults, from the first experiments to the current version. The number after the version is how many runs were averaged.','Тот же MT3000 и те же контролируемые сбои, от первых экспериментов до текущей версии. Число после версии — сколько прогонов усреднено.')),
    legend('auto'),versionHistoryChart('auto'),versionHistoryTable('auto'),
    E('p',{},bi('The switch itself became about a third shorter with the fast switch and the return twice as fast; most of the time is now the detection and confirmation of the failure, set by the probe level.','Само переключение стало примерно на треть короче с быстрым переключением, возврат — вдвое быстрее; основное время теперь — обнаружение и подтверждение сбоя, оно задаётся уровнем опроса.')),
    legend('manual'),versionHistoryChart('manual'),versionHistoryTable('manual'),
    E('p',{},bi('Manual button with Auto on: 42 s to done in beta7, 14.5-20.2 s in beta8; the route change itself takes about 0.3 s.','Ручная кнопка при включённом Auto: 42 с до готово в beta7, 14,5–20,2 с в beta8; сама смена маршрута — около 0,3 с.'))]);
}
// Guaranteed ranges for the 1.0.0 beta description: fault start -> traffic already on the reserve (min / mean / max, s).
var AUTO_MEASURED_RANGES=[[1,160,171,183],[3,150,153,163],[4,140,154,159],[5,152,157,162]];
var MEASURE_PHASES=[['Fault not yet noticed','Сбой ещё не замечен','#9aa3ad'],['Confirming the failure','Подтверждение сбоя','#e0b100'],
  ['Switching to the reserve','Переключение на резерв','#e07800'],['Traffic on the reserve','Трафик на резерве','#2f9e57'],['Returning to the primary','Возврат на основной','#2563eb']];
function measureMean(values){values=values.filter(Number.isFinite);return values.length?values.reduce(function(a,b){return a+b;},0)/values.length:null;}
function measureSvg(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});return n;}
// Shared stacked phase chart (Help measurements and Advanced > Switch statistics). Each row: {label,segs:[{k,from,to,tip}]},
// from/to are seconds on the chart axis; k indexes MEASURE_PHASES. A marker draws a dashed vertical line.
function phaseChart(rows,opts){
  opts=opts||{};if(typeof document==='undefined'||!document.createElementNS)return E('p',{},'');
  var phases=opts.phases||MEASURE_PHASES;
  var ends=[30,opts.marker?opts.marker.at:0];rows.forEach(function(r){r.segs.forEach(function(s){ends.push(s.to);});});
  var max=Math.max.apply(null,ends)*1.05,row=26,top=26,left=opts.left||64,width=964-left,h=top+Math.max(1,rows.length)*row+34;
  var step=[10,15,30,60,120,300,600,1800,3600,7200,21600].find(function(v){return max/v<=12;})||43200;
  var svg=measureSvg('svg',{viewBox:'0 0 1000 '+h,role:'img','aria-label':opts.title||'',style:'width:100%;height:auto;display:block'});
  for(var t=0;t<=max;t+=step){var x=left+t/max*width;svg.appendChild(measureSvg('line',{x1:x,x2:x,y1:top-6,y2:h-28,stroke:'#d8d9d8','stroke-width':1}));var lab=measureSvg('text',{x:x,y:h-12,'text-anchor':'middle','font-size':11,fill:'currentColor'});lab.textContent=t<600?t+bi(' s',' с'):Math.round(t/60)+bi(' min',' мин');svg.appendChild(lab);}
  if(opts.marker){var fx=left+opts.marker.at/max*width;svg.appendChild(measureSvg('line',{x1:fx,x2:fx,y1:top-10,y2:h-28,stroke:'#c0392b','stroke-width':2,'stroke-dasharray':'5 3'}));
    var fl=measureSvg('text',{x:fx+4,y:top-12,'font-size':11,fill:'#c0392b'});fl.textContent=opts.marker.label;svg.appendChild(fl);}
  rows.forEach(function(r,i){
    var y=top+i*row,name=measureSvg('text',{x:left-6,y:y+15,'text-anchor':'end','font-size':11,fill:'currentColor'});name.textContent=r.label;svg.appendChild(name);
    r.segs.forEach(function(sg){var a=left+sg.from/max*width,b=left+sg.to/max*width,rect=measureSvg('rect',{x:a,y:y+3,width:Math.max(1,b-a),height:row-8,fill:phases[sg.k][2],'data-phase':sg.k}),tip=measureSvg('title');
      if(sg.open)rect.setAttribute('fill-opacity','0.55');tip.textContent=bi(phases[sg.k][0],phases[sg.k][1])+': '+sg.tip;rect.appendChild(tip);svg.appendChild(rect);
      if(sg.label&&b-a>=46){var lt=measureSvg('text',{x:(a+b)/2,y:y+15,'text-anchor':'middle','font-size':10,fill:'#fff'});lt.textContent=sg.label;svg.appendChild(lt);}});
  });
  return svg;
}
function measureChart(set){
  return phaseChart(set.rows.map(function(r){var edges=[0,r[1],r[2],r[3],r[4],r[5]];
    return {label:r[0],segs:[0,1,2,3,4].map(function(k){return {k:k,from:edges[k],to:edges[k+1],tip:edges[k]+'–'+edges[k+1]+bi(' s',' с')};})};}),
    {title:bi(set.title[0],set.title[1]),marker:{at:set.fault,label:bi('fault ends','конец сбоя')}});
}
function measureTable(set){
  var cols=[bi('Time','Время'),bi('Noticed','Замечен'),bi('Switch started','Начало перехода'),bi('On reserve','На резерве'),bi('Return started','Начало возврата'),bi('Back on primary','Снова на основном'),bi('Switch itself','Само переключение'),bi('Return itself','Сам возврат')];
  var t=E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1'},[E('tr',{},cols.map(function(c){return E('th',{'scope':'col'},c);}))]);
  set.rows.forEach(function(r){t.appendChild(E('tr',{},[r[0],r[1],r[2],r[3],r[4],r[5],r[3]-r[2],r[5]-r[4]].map(function(v,i){return E('td',{},i?v+bi(' s',' с'):v);})));});
  var mean=[1,2,3,4,5].map(function(i){return measureMean(set.rows.map(function(r){return r[i];}));});
  var sw=measureMean(set.rows.map(function(r){return r[3]-r[2];})),rt=measureMean(set.rows.map(function(r){return r[5]-r[4];}));
  t.appendChild(E('tr',{'class':'hv-measure-mean'},[E('th',{'scope':'row'},bi('Mean','Среднее'))].concat(mean.concat([sw,rt]).map(function(v){return E('td',{},Math.round(v)+bi(' s',' с'));}))));
  return t;
}
function renderMeasurements(){
  var legend=E('p',{'class':'hv-measure-legend'},MEASURE_PHASES.map(function(p){return E('span',{},[E('i',{'style':'background:'+p[2]}),' '+bi(p[0],p[1])]);}));
  return E('div',{'class':'hv-measurements'},[
    E('p',{},bi('Controlled faults made with the Tests page function: the traffic of the primary WireGuard was blocked for a fixed time; Auto had to notice it, switch to the reserve OpenVPN and return when the primary recovered. Every bar is one fault; seconds from its start.','Контролируемые сбои через функцию страницы «Тесты»: трафик основного WireGuard блокировался на заданное время; Auto должен был заметить сбой, переключить на резервный OpenVPN и вернуться, когда основной восстановился. Каждая полоса — один сбой; секунды от его начала.')),
    renderVersionHistory(),
    legend].concat(AUTO_MEASUREMENTS.map(function(set){return E('section',{'class':'hv-measure-set','data-measure-set':set.id},[
      E('h4',{},bi(set.title[0],set.title[1])+' · '+set.version),measureChart(set),measureTable(set)]);})).concat([
    E('h4',{},bi('Range: from the fault to traffic on the reserve','Диапазон: от поломки до работы через резерв')),
    E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1'},[E('tr',{},[bi('Probe level','Уровень опроса'),bi('Fastest','Быстрее всего'),bi('Mean','Среднее'),bi('Slowest','Дольше всего')].map(function(c){return E('th',{'scope':'col'},c);}))].concat(
      AUTO_MEASURED_RANGES.map(function(r){return E('tr',{},[String(r[0])+(r[0]<=2?bi(' (boost always on)',' (ускорение всегда)'):''),r[1]+bi(' s',' с'),r[2]+bi(' s',' с'),r[3]+bi(' s',' с')].map(function(v){return E('td',{},v);}));}))),
    E('p',{},bi('Observed limits: the switch itself took 46-76 s (mean 63 s) and the return to the primary 38-57 s (mean 48 s) in all 19 measured switches. At levels 3-5 a failure is noticed in about 30 s, at level 1 in about 60 s; then about 55 s go to confirming the failure (three checks) and proving the reserve. When faults repeat every 5 minutes, the switch budget (attempt limit per window) refused one switch on purpose: this protects against endless flapping.','Наблюдаемые пределы: само переключение заняло 46–76 с (в среднем 63 с), возврат на основной — 38–57 с (в среднем 48 с) во всех 19 измеренных переключениях. На уровнях 3–5 сбой замечается примерно за 30 с, на уровне 1 — примерно за 60 с; затем около 55 с уходит на подтверждение сбоя (три проверки) и проверку резерва. При сбоях каждые 5 минут лимит переключений (число попыток за окно) намеренно отклонил одно переключение: это защита от бесконечных переключений туда-обратно.')),
    E('p',{},bi('What it shows: these runs used the GL rebuild, so the switch itself took about a minute (the GL firmware rebuilds its VPN routing, rtp2). Since 1.0.0-beta3 the MT3000 normally uses the fast switch instead: the rule change measured 8-33 ms and new connections used the new channel within 0.5 s (30 Oct 2026); the GL rebuild stays as the fallback. The time from a fault is then dominated by detection (about 105 s) and depends on the probe level; the countdown during a switch uses the measured average plus 25%.','Что видно: в этих прогонах использовалась перестройка GL, поэтому само переключение занимало около минуты (прошивка GL перестраивает маршрутизацию VPN, rtp2). Начиная с 1.0.0-beta3 MT3000 обычно использует быстрое переключение: смена правил занимала 8–33 мс, а новые соединения шли по новому каналу в пределах 0,5 с (замер 30.10.2026); перестройка GL остаётся запасным путём. Тогда время от сбоя определяется обнаружением (около 105 с) и зависит от уровня опроса; обратный отсчёт во время переключения берёт измеренное среднее плюс 25%.'))]));
}
HELP_TOPICS.push({id:'auto-measurements',open:false,title:['Measured results of Auto mode','Результаты замеров работы в автоматическом режиме'],
  when:['You want to know how fast Auto notices a failure, switches and returns on a real router.','Вы хотите знать, как быстро Auto замечает сбой, переключает и возвращается на реальном роутере.'],
  steps:[{t:['Night of 30 Oct 2026, alpha82, probe level 1 with boost, 8 faults of 180 s: noticed after 59 s on average, traffic on the reserve after 171 s (160-183 s), the switch itself 61 s, back on the primary after 284 s.','Ночь 30.10.2026, alpha82, уровень опроса 1 с ускорением, 8 сбоев по 180 с: сбой замечен в среднем через 59 с, трафик на резерве через 171 с (160–183 с), само переключение 61 с, снова на основном через 284 с.']},
         {t:['Morning of 30 Oct 2026, levels 3, 4 and 5 with boost, faults of 150 s every 5 min: noticed after about 30 s, traffic on the reserve after 140-163 s (mean 153-157 s), the switch itself 55-76 s.','Утро 30.10.2026, уровни 3, 4 и 5 с ускорением, сбои по 150 с каждые 5 минут: сбой замечен примерно через 30 с, трафик на резерве через 140–163 с (в среднем 153–157 с), само переключение 55–76 с.']}],
  custom:renderMeasurements});
// Help: how Auto decides, as a diagram (defaults of Settings -> Auto switching rules; the owner can change the numbers).
function autoLogicDiagram(){
  if(typeof document==='undefined'||!document.createElementNS)return E('p',{},'');
  var svg=measureSvg('svg',{viewBox:'0 0 1000 560',role:'img','aria-label':bi('Auto decision diagram','Схема решений Auto'),style:'width:100%;height:auto;display:block'});
  var defs=measureSvg('defs'),marker=measureSvg('marker',{id:'hv-arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});
  marker.appendChild(measureSvg('path',{d:'M0,0 L10,5 L0,10 z',fill:'currentColor'}));defs.appendChild(marker);svg.appendChild(defs);
  function box(x,y,w,h,fill,lines){
    svg.appendChild(measureSvg('rect',{x:x,y:y,width:w,height:h,rx:14,fill:fill,stroke:'currentColor','stroke-opacity':.35}));
    lines.forEach(function(t,i){var n=measureSvg('text',{x:x+w/2,y:y+24+i*19,'text-anchor':'middle','font-size':i?13:15,'font-weight':i?400:700,fill:'#14212e'});n.textContent=t;svg.appendChild(n);});
  }
  function arrow(x1,y1,x2,y2,label,lx,ly){
    svg.appendChild(measureSvg('line',{x1:x1,y1:y1,x2:x2,y2:y2,stroke:'currentColor','stroke-width':2,'marker-end':'url(#hv-arrow)'}));
    if(label)label.forEach(function(t,i){var n=measureSvg('text',{x:lx,y:ly+i*16,'text-anchor':'middle','font-size':12,fill:'currentColor'});n.textContent=t;svg.appendChild(n);});
  }
  box(40,40,280,96,'#b7efc5',[bi('1. Primary carries traffic','1. Работает основной'),bi('both channels are checked','проверяются оба канала'),bi('every 10-60 s (probe level)','раз в 10–60 с (уровень опроса)')]);
  box(680,40,280,96,'#ffd9a8',[bi('2. Switching to reserve','2. Переключение на резерв'),bi('rules written in one step','правила записываются за один шаг'),bi('fast: about 1 s; fallback: 46-76 s','быстро: около 1 с; запасной: 46–76 с')]);
  box(680,300,280,96,'#ffe9a8',[bi('3. Reserve carries traffic','3. Работает резерв'),bi('primary keeps being checked','основной продолжает проверяться'),'']);
  box(40,300,280,96,'#bcd7ff',[bi('4. Return to primary','4. Возврат на основной'),bi('about 38-57 s','около 38–57 с'),'']);
  arrow(320,88,676,88,[bi('primary: 3 failed checks in a row','основной: 3 неудачные проверки подряд'),bi('and reserve: 2 good checks in a row','и резерв: 2 удачные проверки подряд')],498,60);
  arrow(820,136,820,296,[bi('switch confirmed','переключение'),bi('by the router','подтверждено роутером')],890,210);
  arrow(676,348,324,348,[bi('primary: 2 good checks + stable 30 s,','основной: 2 удачные проверки + стабилен 30 с,'),bi('at least 60 s on reserve, <= 3 switches / 15 min','не меньше 60 с на резерве, не больше 3 переключений за 15 мин')],498,320);
  arrow(180,300,180,140,[bi('return','возврат'),bi('confirmed','подтверждён')],120,220);
  box(40,440,280,100,'#f6c6c6',[bi('Both channels fail','Оба канала не работают'),bi('Auto stays and waits:','Auto остаётся и ждёт:'),bi('there is nowhere to switch','переключаться некуда')]);
  box(360,440,280,100,'#e6e2f7',[bi('Reserve fails, primary healthy','Отказал резерв, основной здоров'),bi('Auto returns to the primary','Auto сразу возвращает'),bi('without waiting','трафик на основной')]);
  box(680,440,280,100,'#e2e8ee',[bi('You chose the reserve by hand','Вы вручную выбрали резерв'),bi('no automatic return;','без автовозврата;'),bi('if it fails, Auto switches back','при его отказе Auto вернёт')]);
  return svg;
}
function renderAutoLogic(){
  return E('div',{'class':'hv-auto-logic'},[autoLogicDiagram(),
    E('ol',{'class':'hv-help-steps'},[
      [bi('Primary carries traffic. The router checks both channels itself (DNS + three HTTPS sites through each tunnel) every 10-60 s, depending on the probe level.','Работает основной канал. Роутер сам проверяет оба канала (DNS и три HTTPS-сайта через каждый туннель) раз в 10–60 с — по уровню опроса.')],
      [bi('Failure: after 3 failed checks of the primary in a row (on levels 1-2 the boost then checks every 10 s) and 2 good checks of the reserve in a row, Auto switches to the reserve.','Сбой: после 3 неудачных проверок основного подряд (на уровнях 1–2 ускорение тогда проверяет раз в 10 с) и 2 удачных проверок резерва подряд Auto переключает на резерв.')],
      [bi('Switch: the router writes the committed channel order straight into its firewall rules in one atomic step (fast switch, no firewall reload, no DNS restart). The rule change measured 8-33 ms and new connections used the new channel within 0.5 s (MT3000, 30 Oct 2026); the whole switch takes about 1 s. If anything looks unexpected, or you turned fast switch off in Settings, the GL firmware rebuilds its VPN routing instead (fallback, measured 46-76 s). The router confirms the new route either way.','Переключение: роутер записывает утверждённый порядок каналов прямо в правила межсетевого экрана одним атомарным шагом (быстрое переключение: без перезагрузки межсетевого экрана и без перезапуска DNS). Смена правил занимала 8–33 мс, а новые соединения шли по новому каналу в пределах 0,5 с (MT3000, 30.10.2026); всё переключение занимает около 1 с. Если что-то выглядит неожиданно или вы выключили быстрое переключение в настройках, вместо этого прошивка GL перестраивает маршрутизацию VPN (запасной путь, замерено 46–76 с). Новый маршрут роутер подтверждает в обоих случаях.')],
      [bi('On the reserve: traffic stays on the reserve while the primary is down. The primary keeps being checked.','На резерве: трафик остаётся на резерве, пока основной не работает. Основной продолжает проверяться.')],
      [bi('Return: when the primary passed 2 checks in a row and is stable for 30 s, at least 60 s were spent on the reserve and no more than 3 switches happened in 15 minutes, Auto returns to the primary (measured 38-57 s).','Возврат: когда основной прошёл 2 проверки подряд и стабилен 30 с, на резерве провели не меньше 60 с и было не больше 3 переключений за 15 минут, Auto возвращает трафик на основной (замерено 38–57 с).')],
      [bi('If the reserve fails while the primary is healthy, Auto returns at once. If both fail, Auto stays and waits. If you chose the reserve by hand, there is no automatic return, but Auto still switches back if the reserve fails.','Если отказал резерв, а основной здоров, Auto возвращается сразу. Если не работают оба, Auto остаётся и ждёт. Если вы вручную выбрали резерв, автовозврата нет, но при отказе резерва Auto переключит обратно.')],
      [bi('All numbers are the defaults of Settings → Auto switching rules; there you can also choose "stay on the reserve" instead of returning.','Все числа — значения по умолчанию в «Настройки → Правила автопереключения»; там же можно выбрать «оставаться на резерве» вместо возврата.')]
    ].map(function(t){return E('li',{},E('p',{},t[0]));}))]);
}
HELP_TOPICS.unshift({id:'auto-logic',open:false,title:['How Auto works: switching and return','Логика работы Auto: переключение и возврат'],
  when:['You want to know when Auto switches to the reserve and when it returns to the primary.','Вы хотите знать, когда Auto переключает на резерв и когда возвращает на основной.'],
  steps:[{t:['Primary works; after 3 failed checks of the primary and 2 good checks of the reserve Auto switches to the reserve (fast switch about 1 s; fallback to the GL rebuild 46-76 s); it returns when the primary passed 2 checks, is stable 30 s, at least 60 s were spent on the reserve and the switch budget allows (return 38-57 s).','Работает основной; после 3 неудачных проверок основного и 2 удачных проверок резерва Auto переключает на резерв (быстрое переключение около 1 с; запасной путь через перестройку GL 46–76 с); возвращает, когда основной прошёл 2 проверки, стабилен 30 с, на резерве провели не меньше 60 с и позволяет лимит переключений (возврат 38–57 с).']}],
  custom:renderAutoLogic});
