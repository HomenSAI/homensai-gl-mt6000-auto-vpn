/* Three-site response time never grants permission to switch VPNs. */
var LATENCY_VIEW={hours:1,end:null};
var LATENCY_HISTORY_HOURS=168;
var LATENCY_HISTORY_SECONDS=7*86400;
function latencyCurrent(status,inventory,now){
  if(status.rpc_error||status.error)return [null,null];
  var ids=rolePairIds(status,inventory,now),rows=Array.isArray(status.profiles)?status.profiles:[];
  return ids.map(function(id){var p=rows.find(function(p){return p&&p.id===id;});var value=channelPingModel(p,status,now).rtt_ms;return value===null?null:Object.assign({},p,{rtt_ms:value});});
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
  var measured=latencyCurrent(status,inventory,now),rows=measured.map(function(p){return p&&profileHealth(p,now).state==='healthy'?p:null;});
  if(rows.filter(Boolean).length===1){
    var ids=rolePairIds(status,inventory,now),k=rows[0]?0:1,other=(status.profiles||[]).filter(function(p){return p&&p.id===ids[1-k];})[0];
    return {index:k,single:true,text:(measured.every(Boolean)?(k===0?bi('Only the primary is eligible for this recommendation','Для этой рекомендации сейчас подходит только основной канал'):bi('Only the reserve is eligible for this recommendation','Для этой рекомендации сейчас подходит только резервный канал')):(k===0?bi('Only the primary has a complete three-site measurement','Полный замер трёх сайтов есть только у основного канала'):bi('Only the reserve has a complete three-site measurement','Полный замер трёх сайтов есть только у резервного канала')))+' ('+websiteMs(rows[k].rtt_ms)+' '+bi('ms','мс')+'). '+(k===0?bi('Reserve: ','Резервный: '):bi('Primary: ','Основной: '))+(other&&profileHealth(other,now).state!=='healthy'?channelCheckText(other,now):channelPingModel(other,status,now).text)};
  }
  if(rows.some(function(p){return !p;}))return {index:null,text:bi('A comparison needs complete three-site results and confirmed healthy channels.','Для сравнения нужны полные замеры трёх сайтов и подтверждённо работающие каналы.')};
  if(Math.abs(rows[0].rtt_ms-rows[1].rtt_ms)<.1)return {index:null,text:bi('The current measured delays are equal.','Сейчас измеренные задержки одинаковы.')};
  var index=rows[0].rtt_ms<rows[1].rtt_ms?0:1;
  return {index:index,text:bi('Lower measured website response: ','Меньший измеренный ответ сайтов: ')+(index===0?bi('the primary channel','основной канал'):bi('the reserve channel','резервный канал'))+': '+websiteMs(rows[index].rtt_ms)+' '+bi('ms versus ','мс против ')+websiteMs(rows[1-index].rtt_ms)+' '+bi('ms. Its measured delay is lower by ','мс. Его задержка меньше на ')+websiteMs(rows[1-index].rtt_ms-rows[index].rtt_ms)+' '+bi('ms.','мс.')+' · '+serverTitle(rows[index])};
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
    body.push(line(bi('Lower measured response: ','Меньший измеренный ответ: '),recommend.index===0?bi('Primary channel','Основной канал'):bi('Reserve channel','Резервный канал')));
    body.push(line(bi('Its delay: ','Его задержка: '),websiteMs(chosen.rtt_ms)+' '+bi('ms','мс')));
    body.push(line(bi('Other channel delay: ','Задержка другого канала: '),websiteMs(other.rtt_ms)+' '+bi('ms','мс')));
    body.push(line(bi('Lower by: ','Меньше на: '),websiteMs(other.rtt_ms-chosen.rtt_ms)+' '+bi('ms','мс')));
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
      count+=n;total+=Math.round(value*n*10);buckets++;min=min===null?value:Math.min(min,value);max=max===null?value:Math.max(max,value);
    });
    return {count:count,buckets:buckets,mean:count?total/(count*10):null,min:min,max:max};
  });
}
function renderLatencyStatistics(rows,start,end,status,inventory,now){
  var h=status&&status.website_response_history||{};start=Math.max(start,Number.isFinite(h.stats_since)?h.stats_since:0);
  var stats=latencyStatistics(rows,start,end),coverage=h.coverage_rows;
  if(typeof h.coverage_rows_json==='string'&&h.coverage_rows_json.length<=850000){try{coverage=JSON.parse(h.coverage_rows_json);}catch(error){coverage=null;}}
  var ids=status&&typeof rolePairIds==='function'?rolePairIds(status,inventory||{},now):[];
  function loss(i){if(!Array.isArray(coverage)||coverage.length>10081)return '—';var attempts=0;coverage.forEach(function(r){if(Array.isArray(r)&&r.length===7&&Number.isFinite(r[0])&&r[0]>=start&&r[0]<=end&&r.slice(1).every(function(v){return Number.isInteger(v)&&v>=0&&v<=360;}))attempts+=r[i+3]/3;});return Number.isInteger(attempts)&&attempts>=stats[i].count&&attempts?Math.round(100*(attempts-stats[i].count)/attempts)+'% ('+(attempts-stats[i].count)+' '+bi('of','из')+' '+attempts+')':'—';}
  function ms(v){return v===null?'—':websiteMs(v)+' '+bi('ms','мс');}
  return E('table',{'class':'table hv-latency-statistics','data-hv-no-sort':'1'},[
    E('tr',{},[bi('Channel','Канал'),bi('Mean','Средняя'),bi('Minimum minute mean','Мин. за минуту'),bi('Maximum minute mean','Макс. за минуту'),bi('Complete cycles (3/3)','Полные проверки (3/3)'),bi('Incomplete three-site checks','Неполные проверки трёх сайтов')].map(function(t){return E('th',{'scope':'col'},t);})),
    ...stats.map(function(s,i){return E('tr',{},[E('th',{'scope':'row'},i===0?bi('Primary','Основной'):bi('Reserve','Резервный')),E('td',{},ms(s.mean)),E('td',{},ms(s.min)),E('td',{},ms(s.max)),E('td',{},String(s.count)),E('td',{},loss(i))]);})]);
}
function latencyHistoryRows(status,inventory,now){
  var h=status.website_response_history||{},ids=rolePairIds(status,inventory,now);
  if(h.version!==1||h.metric!==WEBSITE_METRIC||h.target_set!==WEBSITE_TARGET_SET||h.row_encoding!=='sum-tenths'||!Array.isArray(h.pair)||h.pair.length!==2||h.pair[0]!==ids[0]||h.pair[1]!==ids[1])return [];
  var rows=h.rows;
  if(h.rows_json!==undefined){
    if(typeof h.rows_json!=='string'||h.rows_json.length>850000)return [];
    try{rows=JSON.parse(h.rows_json);}catch(error){return [];}
  }
  if(!Array.isArray(rows)||rows.length>10081||h.rows_count!==undefined&&(!Number.isInteger(h.rows_count)||h.rows_count!==rows.length))return [];
  return rows.filter(function(r){return Array.isArray(r)&&r.length===6&&Number.isFinite(r[0])&&r[0]>=now-LATENCY_HISTORY_SECONDS&&r[0]<=now+5&&[1,2].every(function(i){return Number.isInteger(r[i+2])&&r[i+2]>=0&&r[i+2]<=120&&(r[i+2]===0?r[i]===null:Number.isInteger(r[i])&&r[i]>=0&&r[i]<=60000*r[i+2]);})&&['source','target','unknown','off','switching'].indexOf(r[5])>=0;}).map(function(r){var decoded=r.slice();[1,2].forEach(function(i){decoded[i]=r[i+2]?r[i]/(10*r[i+2]):null;});return decoded;}).sort(function(a,b){return a[0]-b[0];});
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
  var maxY=Math.max(1,...values)*1.15,svg=latencySvg('svg',{viewBox:'0 0 1000 270',role:'img','aria-label':bi('Primary and reserve three-site response history in milliseconds','История среднего ответа трёх сайтов через основной и резервный VPN в миллисекундах'),style:'width:100%;height:auto;min-height:180px;display:block'});
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
  var notes=E('details',{'class':'hv-latency-notes','data-auto-disclosure':'latency-statistics'},[E('summary',{},bi('How statistics are calculated','Как считается статистика')),helpLink('website-response',bi('Three sites, coverage and history gaps','Три сайта, полнота проверки и пропуски истории'))]);
  if(typeof rememberDisclosure==='function')rememberDisclosure(notes,'latency-statistics');
  var selectedId=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):null,roleIds=rolePairIds(status,inventory,now);
  var selected=selectedId&&selectedId===roleIds[0]?'source':selectedId&&selectedId===roleIds[1]?'target':null;
  return E('section',{'class':'hv-chart-card','data-latency-panel':'1','data-stats-reset':'latency'},[
    E('h3',{},bi('Delay of the two VPN channels','Задержка двух VPN-каналов')),renderLatencyRecommendation(status,inventory,'channels'),
    E('div',{'class':'hv-latency-values'},[0,1].map(function(i){return E('p',{},[E('strong',{},i===0?bi('Primary: ','Основной: '):bi('Reserve: ','Резервный: ')),renderChannelPing((status.profiles||[]).find(function(p){return p&&p.id===roleIds[i];}),status,now)]);})),
    E('div',{'class':'hv-latency-series'},[
      E('span',{},[E('i',{'class':'hv-latency-sample','aria-hidden':'true'}),bi('Primary · solid line','Основной · сплошная линия')]),
      E('span',{},[E('i',{'class':'hv-latency-sample hv-latency-dashed','aria-hidden':'true'}),bi('Reserve · dashed line','Резервный · пунктирная линия')])]),
    E('p',{'class':'hv-latency-current-route'},selected==='source'?bi('Currently in use: primary channel','Сейчас задействован основной канал'):selected==='target'?bi('Currently in use: reserve channel','Сейчас задействован резервный канал'):latencyRouteText(status)),
    plot,caption,E('div',{'class':'hv-latency-controls'},[
      E('label',{'class':'hv-latency-slider'},[hours,E('span',{},bi('Window: 1 hour–7 days','Период: 1 час–7 суток'))]),
      E('label',{'class':'hv-latency-slider'},[pan,E('span',{},bi('Browse the last 7 days','Просмотр последних 7 суток'))]),live]),statistics,
    notes,
    (status.website_response_history||{}).notice?E('p',{'role':'status'},status.website_response_history.notice):null].filter(Boolean));
}
