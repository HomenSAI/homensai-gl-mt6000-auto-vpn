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
