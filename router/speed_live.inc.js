/* Current measured payload progress, separate from completed-test history. */
var SPEED_LIVE_CACHE=null,SPEED_LIVE_REQUESTED=null,SPEED_LIVE_HOSTS=[],SPEED_LIVE_BUSY=false;
function speedLiveRunning(data){return !!data&&['QUEUED','RUNNING'].indexOf(data.state)>=0;}
function speedLiveNumber(n,max){return Number.isFinite(n)&&n>=0&&n<=max;}
function speedLiveSnapshot(raw){
  if(!raw||!['IDLE','QUEUED','RUNNING','DONE','FAILED','CANCELLED'].includes(raw.state)||!Array.isArray(raw.profiles)||raw.profiles.length>8||!speedLiveNumber(raw.server_time,4102444800))return null;
  if(raw.state!=='IDLE'&&(typeof raw.run_id!=='string'||!/^[a-f0-9]{32}$/.test(raw.run_id)))return null;
  var rows=[],seen={};
  raw.profiles.forEach(function(r){
    if(!r||typeof r.id!=='string'||!/^[A-Za-z0-9_.:-]{1,96}$/.test(r.id)||seen[r.id]||!Array.isArray(r.samples)||r.samples.length>128)return;
    seen[r.id]=true;var last=-1,samples=[];
    r.samples.forEach(function(p){if(!Array.isArray(p)||p.length!==3||!speedLiveNumber(p[0],300)||p[0]<last||p.slice(1).some(function(v){return v!==null&&!speedLiveNumber(v,10000000);})||p.slice(1).filter(function(v){return v!==null;}).length!==1)return;last=p[0];samples.push(p.slice());});
    rows.push({id:r.id,phase:['waiting','resolving','latency','download','upload','done','failed','cancelled'].includes(r.phase)?r.phase:'failed',samples:samples,updated:r.updated,download_mbps:speedLiveNumber(r.download_mbps,10000000)?r.download_mbps:null,upload_mbps:speedLiveNumber(r.upload_mbps,10000000)?r.upload_mbps:null,code:typeof r.code==='string'&&/^SPEED-[A-Z0-9-]{1,64}$/.test(r.code)?r.code:null});
  });
  return {run_id:raw.run_id||null,state:raw.state,profiles:rows,server_time:raw.server_time,code:raw.code};
}
function speedLiveAccept(raw){
  var data=speedLiveSnapshot(raw);if(!data)return false;
  if(SPEED_LIVE_REQUESTED&&data.run_id!==SPEED_LIVE_REQUESTED.run_id)return false;
  if(SPEED_LIVE_CACHE&&data.server_time<SPEED_LIVE_CACHE.server_time)return false;
  SPEED_LIVE_CACHE=data;
  if(SPEED_LIVE_REQUESTED&&data.run_id===SPEED_LIVE_REQUESTED.run_id&&!speedLiveRunning(data))SPEED_LIVE_REQUESTED=null;
  SPEED_LIVE_HOSTS=SPEED_LIVE_HOSTS.filter(function(host){return host.isConnected;});
  SPEED_LIVE_HOSTS.forEach(function(host){host.updateSpeedLive(data);if(host.setSpeedConnection)host.setSpeedConnection(true);});return true;
}
function speedLiveQueued(result,ids){
  if(!result||result.accepted!==true||typeof result.run_id!=='string'||!/^[a-f0-9]{32}$/.test(result.run_id))return;
  SPEED_LIVE_REQUESTED={run_id:result.run_id,state:'QUEUED',server_time:Date.now()/1000,profiles:ids.map(function(id){return {id:id,phase:'waiting',samples:[]};})};
  SPEED_LIVE_CACHE=null;SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;}).forEach(function(h){h.updateSpeedLive(SPEED_LIVE_REQUESTED);});
}
function speedLivePhase(row,data){
  if(!row)return bi('Not selected for this test','Не выбран для этого теста');
  if(data.state==='CANCELLED'&&row.phase!=='done')return bi('Test cancelled','Тест отменён');
  if(data.state==='FAILED'&&row.phase!=='done')return bi('Test interrupted','Тест прерван');
  var names={waiting:bi('Waiting for its turn','Ожидает своей очереди'),resolving:bi('Connecting to the test endpoint','Подключение к тестовому серверу'),latency:bi('Checking latency','Проверка задержки'),download:bi('Measuring download','Измеряется скачивание'),upload:bi('Measuring upload','Измеряется отдача'),done:bi('Test completed','Тест завершён'),failed:bi('Test failed','Ошибка теста'),cancelled:bi('Test cancelled','Тест отменён')};
  return names[row.phase]||bi('Waiting for progress','Ожидание результатов');
}
function speedLiveGraph(row,name){
  var points=row&&row.samples||[],values=[];points.forEach(function(p){p.slice(1).forEach(function(v){if(v!==null)values.push(v);});});
  if(!values.length)return E('p',{'class':'hv-speed-live-empty'},bi('Measured transfer rates will appear when this channel is tested.','Замеры скорости появятся, когда начнётся тест этого канала.'));
  var end=Math.max(2,Math.ceil(points[points.length-1][0])),maximum=Math.max(1,Math.ceil(Math.max.apply(null,values)*1.12));
  var x=function(t){return 55+t/end*520;},y=function(v){return 205-v/maximum*170;};
  var svg=speedChartSvg('svg',{'viewBox':'0 0 610 250','role':'img','aria-label':name+' · '+bi('Live download and upload, Mbps','Скачивание и отдача в реальном времени, Мбит/с'),'class':'hv-speed-live-svg'});
  for(var i=0;i<=4;i++){var value=maximum*i/4,line=y(value);svg.appendChild(speedChartSvg('line',{x1:55,y1:line,x2:575,y2:line,stroke:'#b8c3cd','stroke-width':.6}));svg.appendChild(speedChartSvg('text',{x:48,y:line+4,'text-anchor':'end',fill:'currentColor','font-size':11},value.toFixed(value<10?1:0)));}
  svg.appendChild(speedChartSvg('text',{x:55,y:18,fill:'currentColor','font-size':11},bi('Mbps','Мбит/с')));
  [0,.5,1].forEach(function(k){svg.appendChild(speedChartSvg('text',{x:x(end*k),y:229,'text-anchor':'middle',fill:'currentColor','font-size':11},(end*k).toFixed(1)+' '+bi('s','с')));});
  [[1,'download','#139c75',bi('Download','Скачивание')],[2,'upload','#386af2',bi('Upload','Отдача')]].forEach(function(series){
    var segment=[];
    function flush(){if(segment.length>1)svg.appendChild(speedChartSvg('polyline',{points:segment.join(' '),fill:'none',stroke:series[2],'stroke-width':2.5,'data-speed-live-series':series[1]}));segment=[];}
    points.forEach(function(p){var v=p[series[0]];if(v===null){flush();return;}segment.push(x(p[0])+','+y(v));var dot=speedChartSvg('circle',{cx:x(p[0]),cy:y(v),r:2.5,fill:series[2],'data-speed-live-point':series[1]});dot.appendChild(speedChartSvg('title',{},series[3]+': '+v.toFixed(2)+' '+bi('Mbps','Мбит/с')+' · '+p[0].toFixed(1)+' '+bi('s since channel test started','с от начала теста канала')));svg.appendChild(dot);});flush();
  });return svg;
}
function renderSpeedLive(status,inventory,onLive){
  var profiles=status.profiles||[],settings=inventory.settings||{},now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var ids=typeof rolePairIds==='function'?rolePairIds(status,inventory,now):[settings.native_source,settings.native_target];
  var root=E('section',{'class':'hv-speed-live','data-speed-live-root':'1'}),cards=E('div',{'class':'hv-speed-live-grid'}),state=E('p',{'class':'hv-speed-live-state','role':'status'}),connection=E('p',{'class':'hv-speed-live-connection','role':'status'});
  connection.hidden=true;root.setSpeedConnection=function(ok){connection.hidden=ok;connection.textContent=ok?'':bi('Progress unavailable; last received measurements are retained.','Обновление недоступно; показаны последние полученные замеры.');};
  root.appendChild(E('h4',{},bi('Current test · download and upload','Текущий тест · скачивание и отдача')));root.appendChild(state);root.appendChild(connection);root.appendChild(cards);
  var panels=['source','target'].map(function(role,index){
    var id=ids[index],p=profiles.find(function(p){return p.id===id;}),label=index===0?bi('Primary channel','Основной канал'):bi('Reserve channel','Резервный канал'),phase=E('p',{'class':'hv-speed-live-phase'}),rates=E('div',{'class':'hv-speed-live-rates'}),plot=E('div',{'class':'hv-speed-live-plot'});
    cards.appendChild(E('article',{'class':'hv-speed-live-channel','data-speed-live-role':role},[E('h4',{},label),E('strong',{},p?serverTitle(p):bi('Select a VPN pair in Settings','Выберите пару VPN в настройках')),p&&typeof endpointText==='function'?E('small',{'class':'hv-server-address'},endpointText(p,now)):null,phase,rates,plot].filter(Boolean)));
    return {id:id,profile:p,label:label,phase:phase,rates:rates,plot:plot};
  });
  root.appendChild(E('small',{},bi('Channels are measured in sequence. Download is green, upload is blue. The horizontal axis is seconds since that channel test started. Each point is measured test payload transferred during an interval; missing directions and errors are not zero speed.','Каналы измеряются по очереди. Скачивание — зелёным, отдача — синим. По горизонтали — секунды от начала теста канала. Точки показывают скорость передачи тестовых данных за интервал; отсутствие измерения и ошибки не означают нулевую скорость.')));
  root.updateSpeedLive=function(data){
    data=data||{state:'IDLE',profiles:[]};root.setAttribute('data-speed-live-state',data.state);
    state.textContent=speedLiveRunning(data)?bi('Live test · refresh every second','Текущий тест · обновление каждую секунду'):data.state==='DONE'?bi('Latest test completed · measured interval rates below','Последний тест завершён · ниже скорости измеренных интервалов'):data.state==='CANCELLED'?bi('Test cancelled · received measurements retained','Тест отменён · полученные замеры сохранены'):data.state==='FAILED'?bi('Test interrupted · see the diagnostic code','Тест прерван · смотрите код диагностики'):bi('Press Test speed to see live measurements for the selected channels.','Нажмите «Тестировать скорость», чтобы увидеть текущие замеры выбранных каналов.');
    panels.forEach(function(panel){
      var row=(data.profiles||[]).find(function(r){return r.id===panel.id;});panel.phase.textContent=panel.profile?speedLivePhase(row,data):bi('Channel is not configured','Канал не настроен');if(row&&row.code)panel.phase.appendChild(E('span',{},' · '+row.code));
      while(panel.rates.firstChild)panel.rates.removeChild(panel.rates.firstChild);
      ['download','upload'].forEach(function(key){var value=row&&row[key+'_mbps'];panel.rates.appendChild(E('span',{'class':'hv-speed-live-'+key},[E('b',{},key==='download'?bi('Download: ','Скачивание: '):bi('Upload: ','Отдача: ')),value!=null&&Number.isFinite(value)?value.toFixed(2)+' '+bi('Mbps','Мбит/с'):'—']));});
      while(panel.plot.firstChild)panel.plot.removeChild(panel.plot.firstChild);panel.plot.appendChild(speedLiveGraph(row,panel.label));
    });if(onLive)onLive(data);
  };
  var snapshot=speedLiveSnapshot((status.speed_tests||{}).live);
  if(snapshot&&(!SPEED_LIVE_REQUESTED||snapshot.run_id===SPEED_LIVE_REQUESTED.run_id)&&(!SPEED_LIVE_CACHE||snapshot.server_time>=SPEED_LIVE_CACHE.server_time))SPEED_LIVE_CACHE=snapshot;
  root.updateSpeedLive(SPEED_LIVE_REQUESTED||SPEED_LIVE_CACHE||snapshot||{state:(status.speed_tests||{}).state||'IDLE',profiles:[]});SPEED_LIVE_HOSTS=SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;});SPEED_LIVE_HOSTS.push(root);return root;
}
function installSpeedLive(root,getPage){
  var call=rpc.declare({object:'homensai-vpn',method:'speed_live',expect:{}}),timer=window.setInterval(function(){
    if(!root.isConnected){window.clearInterval(timer);return;}
    if(SPEED_LIVE_BUSY||!['tests','ranking'].includes(getPage())||!SPEED_LIVE_REQUESTED&&!speedLiveRunning(SPEED_LIVE_CACHE))return;
    SPEED_LIVE_BUSY=true;
    Promise.resolve().then(call).then(speedLiveAccept).catch(function(){SPEED_LIVE_HOSTS.filter(function(h){return h.isConnected;}).forEach(function(h){h.setSpeedConnection(false);});}).finally(function(){SPEED_LIVE_BUSY=false;});
  },1000);
}
