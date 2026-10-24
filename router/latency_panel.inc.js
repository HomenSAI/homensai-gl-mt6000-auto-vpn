/* HTTPS latency is a measurement, never permission to reorder or switch VPNs. */
var LATENCY_VIEW={hours:1,end:null};
function latencyCurrent(status,inventory,now){
  if(status.rpc_error||status.error)return [null,null];
  var ids=rolePairIds(status,inventory,now),rows=Array.isArray(status.profiles)?status.profiles:[];
  return ids.map(function(id){var p=rows.find(function(p){return p&&p.id===id;});return p&&profileHealth(p,now).state==='healthy'&&p.vendor_state==='SETTLED'&&p.dns_ok===true&&Number.isInteger(p.https_success)&&p.https_success>=2&&Number.isFinite(p.rtt_ms)&&p.rtt_ms>=0&&p.rtt_ms<=600000?p:null;});
}
function latencyRecommendation(status,inventory,now){
  var rows=latencyCurrent(status,inventory,now);
  if(rows.some(function(p){return !p;}))return {index:null,text:bi('A comparison needs fresh successful measurements for both channels.','Для сравнения нужны свежие успешные проверки обоих каналов.')};
  if(Math.abs(rows[0].rtt_ms-rows[1].rtt_ms)<.1)return {index:null,text:bi('The current measured delays are equal.','Сейчас измеренные задержки одинаковы.')};
  var index=rows[0].rtt_ms<rows[1].rtt_ms?0:1;
  return {index:index,text:bi('For current use, recommend ','Для текущей работы рекомендую ')+(index===0?bi('the primary channel','основной канал'):bi('the reserve channel','резервный канал'))+': '+rows[index].rtt_ms.toFixed(1)+' '+bi('ms versus ','мс против ')+rows[1-index].rtt_ms.toFixed(1)+' '+bi('ms. Its measured delay is lower by ','мс. Его задержка меньше на ')+(rows[1-index].rtt_ms-rows[index].rtt_ms).toFixed(1)+' '+bi('ms.','мс.')+' · '+serverTitle(rows[index])+' · '+protocolLabel(rows[index])};
}
function renderLatencyRecommendation(status,inventory){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,recommend=latencyRecommendation(status,inventory,now),current=latencyCurrent(status,inventory,now),ids=rolePairIds(status,inventory,now);
  var selected=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):null,path=status.channel_path||{};
  if(typeof vendorDisplaySelected!=='function'&&!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90&&path.confirmed===true&&Number.isFinite(path.time)&&now-path.time>=-5&&now-path.time<=30)selected=path.active_profile_id;
  var role=selected===ids[0]?bi('primary','основной'):selected===ids[1]?bi('reserve','резервный'):null;
  return E('aside',{'class':'hv-latency-recommendation','data-latency-recommendation':'1','role':'status'},[
    E('strong',{},bi('Recommendation by current delay','Рекомендация по текущей задержке')),E('p',{},recommend.text),
    recommend.index===null?null:E('small',{},endpointText(current[recommend.index],now)),
    E('small',{},role?bi('Traffic currently uses the ','Сейчас трафик использует ')+role+bi(' channel.',' канал.'):bi('Current traffic channel is not confirmed.','Текущий канал трафика не подтверждён.')),
    E('small',{},bi('HTTPS measurements, not ICMP ping. Recommendation only; select a channel in the Manual channel switch block on Overview.','Измерения HTTPS, не ICMP-пинг. Это рекомендация; выбрать канал можно в блоке «Ручное переключение канала» на «Обзоре».'))].filter(Boolean));
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
function renderLatencyStatistics(rows,start,end){
  var stats=latencyStatistics(rows,start,end);
  function ms(v){return v===null?'—':v.toFixed(1)+' '+bi('ms','мс');}
  return E('table',{'class':'table hv-latency-statistics','data-hv-no-sort':'1'},[
    E('tr',{},[bi('Channel','Канал'),bi('Mean','Средняя'),bi('Minimum minute mean','Мин. за минуту'),bi('Maximum minute mean','Макс. за минуту'),bi('Successful checks','Успешных проверок')].map(function(t){return E('th',{'scope':'col'},t);})),
    ...stats.map(function(s,i){return E('tr',{},[E('th',{'scope':'row'},i===0?bi('Primary','Основной'):bi('Reserve','Резервный')),E('td',{},ms(s.mean)),E('td',{},ms(s.min)),E('td',{},ms(s.max)),E('td',{},String(s.count))]);})]);
}
function latencyHistoryRows(status,inventory,now){
  var h=status.latency_history||{},ids=rolePairIds(status,inventory,now);
  if(h.version!==1||h.metric!=='https-rtt-ms'||!Array.isArray(h.pair)||h.pair.length!==2||h.pair[0]!==ids[0]||h.pair[1]!==ids[1]||!Array.isArray(h.rows)||h.rows.length>1441)return [];
  return h.rows.filter(function(r){return Array.isArray(r)&&r.length===6&&Number.isFinite(r[0])&&r[0]>=now-86400&&r[0]<=now+5&&[1,2].every(function(i){return Number.isInteger(r[i+2])&&r[i+2]>=0&&r[i+2]<=120&&(r[i+2]===0?r[i]===null:Number.isFinite(r[i])&&r[i]>=0&&r[i]<=600000);})&&['source','target','unknown','off','switching'].indexOf(r[5])>=0;}).slice().sort(function(a,b){return a[0]-b[0];});
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
  var maxY=Math.max(1,...values)*1.15,svg=latencySvg('svg',{viewBox:'0 0 1000 270',role:'img','aria-label':bi('Primary and reserve HTTPS delay history in milliseconds','История HTTPS-задержки основного и резервного каналов в миллисекундах'),style:'width:100%;height:auto;min-height:180px;display:block'});
  for(var i=0;i<=4;i++){
    var y=220-i/4*185,line=latencySvg('line',{x1:52,x2:956,y1:y,y2:y,stroke:'#d8d9d8','stroke-width':1});svg.appendChild(line);
    var label=latencySvg('text',{x:45,y:y+4,'text-anchor':'end','font-size':12,fill:'currentColor'});label.textContent=String(Math.round(maxY*i/4));svg.appendChild(label);
    var stamp=start+(end-start)*i/4,tick=latencySvg('text',{x:52+904*i/4,y:246,'text-anchor':i===0?'start':i===4?'end':'middle','font-size':12,fill:'currentColor'});tick.textContent=new Date(stamp*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit'});svg.appendChild(tick);
  }
  [0,1].forEach(function(index){latencySegments(rows,index,start,end,maxY).forEach(function(segment){
    var path=latencySvg('polyline',{points:segment.points.map(function(p){return p[0].toFixed(2)+','+p[1].toFixed(2);}).join(' '),fill:'none',stroke:segment.color,'stroke-width':index===0?3:2,'stroke-dasharray':index===0?'none':'5 3'});svg.appendChild(path);
    segment.points.forEach(function(p){var dot=latencySvg('circle',{cx:p[0],cy:p[1],r:2,fill:segment.color}),title=latencySvg('title');title.textContent=(index===0?bi('Primary','Основной'):bi('Reserve','Резервный'))+' · '+new Date(p[2]*1000).toLocaleString()+' · '+p[3].toFixed(1)+' ms';dot.appendChild(title);svg.appendChild(dot);});
  });});return svg;
}
function renderLatencyPanel(status,inventory){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,history=latencyHistoryRows(status,inventory,now),current=latencyCurrent(status,inventory,now),plot=E('div',{'class':'hv-latency-history'}),statistics=E('div',{'class':'hv-latency-statistics-wrap'}),caption=E('p',{'role':'status'});
  var hours=E('input',{'type':'range',min:'1',max:'24',step:'1','aria-label':bi('Delay history window, hours','Период истории задержек, часов'),'input':function(ev){LATENCY_VIEW.hours=Math.max(1,Math.min(24,Math.round(Number(ev.target.value)||1)));draw();}});hours.value=String(LATENCY_VIEW.hours);
  var pan=E('input',{'type':'range',min:'0',max:String((24-LATENCY_VIEW.hours)*60),step:'1','aria-label':bi('Minutes back from live','Минут назад от текущего времени'),'input':function(ev){var offset=Math.max(0,Math.min((24-LATENCY_VIEW.hours)*60,Number(ev.target.value)||0));LATENCY_VIEW.end=offset?now-offset*60:null;draw();}});
  var live=E('button',{'type':'button','class':'cbi-button','click':function(){LATENCY_VIEW.end=null;draw();}},bi('Live','Сейчас'));
  function draw(){
    var end=LATENCY_VIEW.end===null?now:Math.min(now,LATENCY_VIEW.end),start=end-LATENCY_VIEW.hours*3600;
    if(start<now-86400){start=now-86400;end=start+LATENCY_VIEW.hours*3600;LATENCY_VIEW.end=end>=now?null:end;}
    while(plot.firstChild)plot.removeChild(plot.firstChild);
    plot.appendChild(renderLatencyGraph(history,start,end));caption.textContent=LATENCY_VIEW.hours+' '+bi('hour(s)','ч')+' · '+new Date(start*1000).toLocaleString()+' — '+new Date(end*1000).toLocaleString();
    while(statistics.firstChild)statistics.removeChild(statistics.firstChild);statistics.appendChild(renderLatencyStatistics(history,start,end));
    pan.max=String((24-LATENCY_VIEW.hours)*60);pan.value=String(Math.max(0,Math.round((now-end)/60)));
  }
  draw();
  return E('section',{'class':'hv-chart-card','data-latency-panel':'1'},[
    E('h3',{},bi('Delay of the two VPN channels','Задержка двух VPN-каналов')),renderLatencyRecommendation(status,inventory),
    E('div',{'class':'hv-latency-values'},[0,1].map(function(i){return E('p',{},[E('strong',{},i===0?bi('Primary: ','Основной: '):bi('Reserve: ','Резервный: ')),current[i]?current[i].rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS'):bi('No fresh measurement','Нет свежего измерения')]);})),
    E('p',{},bi('Solid line: primary. Dashed line: reserve. Green: selected route; yellow: standby; grey: route unconfirmed.','Сплошная линия — основной, пунктир — резервный. Зелёный — выбранный маршрут, жёлтый — ожидание, серый — маршрут не подтверждён.')),
    plot,caption,E('div',{'class':'hv-latency-controls'},[
      E('label',{'class':'hv-latency-slider'},[hours,E('span',{},bi('Window: 1–24 hours','Период: 1–24 часа'))]),
      E('label',{'class':'hv-latency-slider'},[pan,E('span',{},bi('View earlier in the last day','Просмотр прошедших суток'))]),live]),statistics,
    E('small',{},bi('Statistics follow the selected graph window. Mean is weighted by successful checks; minimum and maximum describe observed minute means. Missing periods are not filled.','Статистика соответствует выбранному периоду графика. Средняя учитывает число успешных проверок; минимум и максимум относятся к наблюдённым минутным средним. Пропуски не заполняются.')),
    E('small',{},bi('Current values are real HTTPS checks, not ICMP ping. History contains observed minute means, with gaps for failures or missing samples; it starts when recording starts and is checkpointed at the configured interval.','Текущие значения — реальные проверки HTTPS, не ICMP-пинг. История содержит наблюдённые минутные средние; ошибки и пропуски не дорисовываются. Запись начинается с её включения и сохраняется с настроенным интервалом checkpoint.')),
    (status.latency_history||{}).notice?E('p',{'role':'status'},status.latency_history.notice):null].filter(Boolean));
}
