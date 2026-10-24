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
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),settings=(inventory||{}).settings||{},ns=(status||{}).native_failover||{};
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
      if(!autoLiveCall)autoLiveCall=rpc.declare({object:'homensai-vpn',method:'auto_live',expect:{}});
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
    if(!row||['source','target','off','unknown','switching'].indexOf(row.kind)<0||!Number.isFinite(row.start)||!Number.isFinite(row.end)||row.start>row.end||row.start>now||row.end>now+5){last=null;previousEnd=null;return;}
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
  if(data.excluded){var archive=E('details',{'class':'hv-failure-archive'},[E('summary',{},bi('Archive without saved role: ','Архив без сохранённой роли: ')+data.excluded),E('p',{},bi('Excluded from both series. These records have no event-time role; today’s pair cannot be used to rewrite them.','Не включён в две серии. В этих записях роль не сохранялась; сегодняшняя пара не используется для переписывания истории.'))]);if(typeof rememberDisclosure==='function')rememberDisclosure(archive,'failure-archive');plot.appendChild(archive);}
  if(!history||history.details_dropped||!Number.isFinite(history.since)||history.since>now-hours*3600)plot.appendChild(E('p',{'class':'hv-muted'},bi('Incomplete history: counts cover saved observations only; no observations is not proof of availability.','История неполная: учитываются только сохранённые наблюдения; их отсутствие не доказывает исправность.')));
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
    [['source',bi('Primary','Основной')],['target',bi('Reserve','Резерв')],['off',bi('Off','Выключено')]].forEach(function(row){
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
