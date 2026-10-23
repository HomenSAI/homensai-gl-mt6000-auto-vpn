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
  var root=E('section',{'id':'hv-auto-day-chart','class':'hv-auto-live-chart hv-auto-day-chart'}),now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000);
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
