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
   rows:[['09:11',32,91,162,220,273],['09:16',33,88,152,219,273],['09:26',27,91,157,218,271]]}
];
// Guaranteed ranges for the 1.0.0 beta description: fault start -> traffic already on the reserve (min / mean / max, s).
var AUTO_MEASURED_RANGES=[[1,160,171,183],[3,150,153,163],[4,140,154,159],[5,152,157,162]];
var MEASURE_PHASES=[['Fault not yet noticed','Сбой ещё не замечен','#9aa3ad'],['Confirming the failure','Подтверждение сбоя','#e0b100'],
  ['Switching to the reserve','Переключение на резерв','#e07800'],['Traffic on the reserve','Трафик на резерве','#2f9e57'],['Returning to the primary','Возврат на основной','#2563eb']];
function measureMean(values){values=values.filter(Number.isFinite);return values.length?values.reduce(function(a,b){return a+b;},0)/values.length:null;}
function measureSvg(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});return n;}
function measureChart(set){
  var max=Math.max.apply(null,set.rows.map(function(r){return r[5];}))*1.05,row=26,top=26,left=64,width=900,h=top+set.rows.length*row+34;
  if(typeof document==='undefined'||!document.createElementNS)return E('p',{},'');
  var svg=measureSvg('svg',{viewBox:'0 0 1000 '+h,role:'img','aria-label':bi(set.title[0],set.title[1]),style:'width:100%;height:auto;display:block'});
  for(var t=0;t<=max;t+=30){var x=left+t/max*width;svg.appendChild(measureSvg('line',{x1:x,x2:x,y1:top-6,y2:h-28,stroke:'#d8d9d8','stroke-width':1}));var lab=measureSvg('text',{x:x,y:h-12,'text-anchor':'middle','font-size':11,fill:'currentColor'});lab.textContent=t+bi(' s',' с');svg.appendChild(lab);}
  var fx=left+set.fault/max*width;svg.appendChild(measureSvg('line',{x1:fx,x2:fx,y1:top-10,y2:h-28,stroke:'#c0392b','stroke-width':2,'stroke-dasharray':'5 3'}));
  var fl=measureSvg('text',{x:fx+4,y:top-12,'font-size':11,fill:'#c0392b'});fl.textContent=bi('fault ends','конец сбоя');svg.appendChild(fl);
  set.rows.forEach(function(r,i){
    var y=top+i*row,edges=[0,r[1],r[2],r[3],r[4],r[5]],name=measureSvg('text',{x:left-6,y:y+15,'text-anchor':'end','font-size':11,fill:'currentColor'});name.textContent=r[0];svg.appendChild(name);
    for(var k=0;k<5;k++){var a=left+edges[k]/max*width,b=left+edges[k+1]/max*width,rect=measureSvg('rect',{x:a,y:y+3,width:Math.max(1,b-a),height:row-8,fill:MEASURE_PHASES[k][2]}),tip=measureSvg('title');
      tip.textContent=bi(MEASURE_PHASES[k][0],MEASURE_PHASES[k][1])+': '+edges[k]+'–'+edges[k+1]+bi(' s',' с');rect.appendChild(tip);svg.appendChild(rect);}
  });
  return svg;
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
    legend].concat(AUTO_MEASUREMENTS.map(function(set){return E('section',{'class':'hv-measure-set','data-measure-set':set.id},[
      E('h4',{},bi(set.title[0],set.title[1])+' · '+set.version),measureChart(set),measureTable(set)]);})).concat([
    E('h4',{},bi('Range: from the fault to traffic on the reserve','Диапазон: от поломки до работы через резерв')),
    E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1'},[E('tr',{},[bi('Probe level','Уровень опроса'),bi('Fastest','Быстрее всего'),bi('Mean','Среднее'),bi('Slowest','Дольше всего')].map(function(c){return E('th',{'scope':'col'},c);}))].concat(
      AUTO_MEASURED_RANGES.map(function(r){return E('tr',{},[String(r[0])+(r[0]<=2?bi(' (boost always on)',' (ускорение всегда)'):''),r[1]+bi(' s',' с'),r[2]+bi(' s',' с'),r[3]+bi(' s',' с')].map(function(v){return E('td',{},v);}));}))),
    E('p',{},bi('Observed limits: the switch itself took 46-76 s (mean 63 s) and the return to the primary 38-57 s (mean 48 s) in all 19 measured switches. At levels 3-5 a failure is noticed in about 30 s, at level 1 in about 60 s; then about 55 s go to confirming the failure (three checks) and proving the reserve. When faults repeat every 5 minutes, the switch budget (attempt limit per window) refused one switch on purpose: this protects against endless flapping.','Наблюдаемые пределы: само переключение заняло 46–76 с (в среднем 63 с), возврат на основной — 38–57 с (в среднем 48 с) во всех 19 измеренных переключениях. На уровнях 3–5 сбой замечается примерно за 30 с, на уровне 1 — примерно за 60 с; затем около 55 с уходит на подтверждение сбоя (три проверки) и проверку резерва. При сбоях каждые 5 минут лимит переключений (число попыток за окно) намеренно отклонил одно переключение: это защита от бесконечных переключений туда-обратно.')),
    E('p',{},bi('What it shows: the switch itself takes about a minute because the GL firmware rebuilds its VPN routing (rtp2); detection depends on the probe level; the countdown during a switch uses the measured average plus 25%.','Что видно: само переключение занимает около минуты, потому что прошивка GL перестраивает маршрутизацию VPN (rtp2); время обнаружения зависит от уровня опроса; обратный отсчёт во время переключения берёт измеренное среднее плюс 25%.'))]));
}
HELP_TOPICS.push({id:'auto-measurements',open:false,title:['Measured results of Auto mode','Результаты замеров работы в автоматическом режиме'],
  when:['You want to know how fast Auto notices a failure, switches and returns on a real router.','Вы хотите знать, как быстро Auto замечает сбой, переключает и возвращается на реальном роутере.'],
  steps:[{t:['Night of 30 Oct 2026, alpha82, probe level 1 with boost, 8 faults of 180 s: noticed after 59 s on average, traffic on the reserve after 171 s (160-183 s), the switch itself 61 s, back on the primary after 284 s.','Ночь 30.10.2026, alpha82, уровень опроса 1 с ускорением, 8 сбоев по 180 с: сбой замечен в среднем через 59 с, трафик на резерве через 171 с (160–183 с), само переключение 61 с, снова на основном через 284 с.']},
         {t:['Morning of 30 Oct 2026, levels 3, 4 and 5 with boost, faults of 150 s every 5 min: noticed after about 30 s, traffic on the reserve after 140-163 s (mean 153-157 s), the switch itself 55-76 s.','Утро 30.10.2026, уровни 3, 4 и 5 с ускорением, сбои по 150 с каждые 5 минут: сбой замечен примерно через 30 с, трафик на резерве через 140–163 с (в среднем 153–157 с), само переключение 55–76 с.']}],
  custom:renderMeasurements});
