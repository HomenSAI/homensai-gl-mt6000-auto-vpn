/* One table for the speed tests: tick servers, press "Test speed" (or cancel), and the same table shows the results.
   Replaces the older panel that had a drop-down, a second table of results and a "recommended priorities" button
   (later function declaration wins). */
var speedSelected={};
var speedFeedback=null;
function speedStartRequest(s,selected,mib,duration,streams){
  function start(){return rpc.declare({object:'homensai-vpn',method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams);}
  if(s.speed_enabled)return start();
  // Explicit review enables manual tests; do not unexpectedly enable stored auto-new preferences.
  return rpc.declare({object:'homensai-vpn',method:'setup_speed',params:['enabled','auto_new','budget_mib','duration','streams','daily_mib','busy_mbps'],expect:{}})(true,false,mib,duration,streams,s.speed_daily_mib==null?128:s.speed_daily_mib,s.speed_busy_mbps==null?2:s.speed_busy_mbps).then(function(result){
    if(!result||result.saved!==true)return {accepted:false,code:result&&result.code||'SPEED-CONFIG-UNCONFIRMED'};
    s.speed_enabled=true;s.speed_auto_new=false;return start();
  });
}
function speedReason(code){
  var messages={
    'SPEED-BUSY':['A speed test is already running.','Тест скорости уже выполняется.'],
    'SPEED-CPU-BUSY':['Router CPU is busy even after pausing Auto and monitoring; retry later.','Процессор роутера занят даже после паузы Auto и мониторинга; повторите позже.'],
    'SPEED-TRAFFIC-BUSY':['VPN traffic is above the configured limit; retry when it is quieter.','VPN-трафик выше заданного порога; повторите, когда нагрузка снизится.'],
    'SPEED-TRAFFIC-UNKNOWN':['Waiting for fresh traffic observations.','Ожидание свежих наблюдений за трафиком.'],
    'SPEED-COOLDOWN':['Wait at least 60 seconds between manual tests.','Между ручными тестами нужно подождать не менее 60 секунд.'],
    'SPEED-DAILY-LIMIT':['The daily test quota has been reached.','Достигнута суточная квота тестов.'],
    'SPEED-SWITCH-IN-PROGRESS':['A channel switch is in progress; wait until it finishes.','Идёт переключение канала; дождитесь его завершения.']
  };
  return messages[code]?bi.apply(null,messages[code]):bi('Test not started. See diagnostic code: ','Тест не запущен. Код диагностики: ')+code;
}
function speedStateText(history){
  var state=history.state||'IDLE';
  if(state==='QUEUED'&&history.preparation==='pausing')return bi('Pausing Auto and monitoring before the test…','Приостанавливаем Auto и мониторинг перед тестом…');
  if(state==='IDLE'||state==='COMPLETED'||state==='COMPLETE'||state==='DONE')return bi('No test is running.','Сейчас тест не идёт.');
  if(state==='RUNNING'||state==='QUEUED'||state==='STARTING')return bi('A test is running; the table fills in as results arrive.','Идёт тест; таблица заполняется по мере поступления результатов.');
  return bi('State: ','Состояние: ')+state;
}
function speedPanel(status,inventory,period,onPeriod){
  var history=status.speed_tests||{},s=inventory.settings||{},profiles=status.profiles||[];
  var active=profiles.filter(function(p){return p.interface;}).slice(0,8);
  var running=['RUNNING','QUEUED','STARTING'].indexOf(history.state)>=0||!!SPEED_LIVE_REQUESTED||speedLiveRunning(SPEED_LIVE_CACHE);
  if(!Object.keys(speedSelected).length)active.forEach(function(p){speedSelected[p.id]=true;});
  var now=Date.now()/1000;
  function dateKey(t){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(t*1000));}
  var today=dateKey(now);
  var rows=(history.results||[]).filter(function(row){return Number.isFinite(row.time)&&row.time<=now+5;});
  rows=rows.filter(function(row){return period==='latest'||period==='day'&&dateKey(row.time)===today||period==='week'&&row.time>=now-7*86400||period==='month'&&dateKey(row.time).slice(0,7)===today.slice(0,7);});
  var grouped={};
  rows.sort(function(a,b){return b.time-a.time;}).forEach(function(row){var g=grouped[row.id]||(grouped[row.id]={last:row,good:[],count:0});g.count++;if(!row.code&&Number.isFinite((row.download||{}).mbps)&&Number.isFinite((row.upload||{}).mbps))g.good.push(row);});
  function mean(good,key){return good.length?good.reduce(function(sum,row){return sum+(row[key]||{}).mbps;},0)/good.length:null;}
  // Connected servers first (they can be ticked), then servers that only have history.
  var ids=active.map(function(p){return p.id;});
  Object.keys(grouped).forEach(function(id){if(ids.indexOf(id)<0)ids.push(id);});
  ids=ids.map(function(id,i){return {id:id,i:i,time:grouped[id]&&grouped[id].last.time||0};}).sort(function(a,b){return b.time-a.time||a.i-b.i;}).map(function(row){return row.id;});
  var section=E('section',{'class':'hv-chart-card hv-speed-panel','data-stats-reset':'ranking'},[
    E('h3',{},bi('VPN server speed tests','Тесты скорости VPN-серверов')),
    E('p',{},bi('Tick the servers you want to measure and press “Test speed”. The same table fills in with the results. A test downloads and uploads a small amount of data through the VPN to Cloudflare; it is a sample of what the application sees, not an Ookla score. VPNs that are not connected cannot be ticked: this program never connects them.','Отметьте серверы, которые хотите измерить, и нажмите «Тестировать скорость». Эта же таблица заполнится результатами. Тест скачивает и отдаёт небольшой объём данных через VPN до Cloudflare; это выборочный результат на уровне приложения, а не оценка Ookla. Неподключённые VPN отметить нельзя: эта программа их не подключает.'))]);
  var table=E('table',{'class':'table hv-speed-table'},[]);
  var boxes=[];
  var all=E('input',{'type':'checkbox','aria-label':bi('Select all connected servers','Выбрать все подключённые серверы'),'change':function(){boxes.forEach(function(b){if(!b.disabled){b.checked=all.checked;speedSelected[b.getAttribute('data-id')]=all.checked;}});}});
  table.appendChild(E('tr',{},[E('th',{},all),E('th',{},bi('Server','Сервер')),E('th',{},bi('Download, Mbps','Скачивание, Мбит/с')),E('th',{},bi('Upload, Mbps','Отдача, Мбит/с')),E('th',{},bi('Last test','Последний тест')),E('th',{},bi('Successful / all','Успешных / всего'))]));
  ids.forEach(function(id){
    var p=profiles.filter(function(x){return x.id===id;})[0],g=grouped[id],connected=!!(p&&p.interface);
    var good=g?(period==='latest'?(g.good[0]===g.last?[g.last]:[]):g.good):[];
    var box=E('input',{'type':'checkbox','data-id':id,'aria-label':bi('Test ','Тестировать ')+(p?serverTitle(p):id),'disabled':connected?null:'','change':function(){speedSelected[id]=box.checked;}});
    box.checked=connected&&!!speedSelected[id];boxes.push(box);
    var down=mean(good,'download'),up=mean(good,'upload');
    var lastCell=g?[g.last.code?E('a',{'href':'#events','class':'hv-errlink','click':function(ev){ev.preventDefault();showErrorCode(g.last.code);}},g.last.code):E('span',{'class':'hv-speed-ok'},'✓ OK'),E('small',{},' '+new Date(g.last.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}))]:[E('span',{'class':'hv-muted'},bi('not tested yet','ещё не тестировался'))];
    table.appendChild(E('tr',{'class':connected?'':'hv-speed-off'},[E('td',{},box),E('td',{},[E('strong',{},p?serverTitle(p):id),typeof endpointText==='function'?E('small',{'class':'hv-server-address'},endpointText(p,now)):null,connected?null:E('small',{},' '+bi('(not connected)','(не подключён)'))].filter(Boolean)),E('td',{},down==null?'—':down.toFixed(1)),E('td',{},up==null?'—':up.toFixed(1)),E('td',{},lastCell),E('td',{},g?good.length+' / '+g.count:'—')]));
  });
  if(!ids.length)table.appendChild(E('tr',{},[E('td',{'colspan':'6'},bi('No connected VPN servers yet. Connect one in the GL.iNet VPN Dashboard.','Подключённых VPN-серверов пока нет. Подключите сервер в GL.iNet → VPN Dashboard.'))]));
  var test=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':running?'':null,'click':function(){
    var selected=active.filter(function(p){return speedSelected[p.id];}).map(function(p){return p.id;}),mib=s.speed_budget_mib==null?8:s.speed_budget_mib,duration=s.speed_duration==null?5:s.speed_duration,streams=s.speed_streams==null?2:s.speed_streams;
    if(running)return;
    if(!selected.length){ui.addNotification(null,E('p',{},bi('Tick at least one connected server in the table first.','Сначала отметьте в таблице хотя бы один подключённый сервер.')));return;}
    if(![['speed.budget_mib',mib],['speed.duration',duration],['speed.streams',streams]].every(function(row){return foolCheckNumber(row[0],row[1]).ok;})){ui.addNotification(null,E('p',{},bi('Check the speed test limits in the settings first.','Сначала проверьте ограничения теста скорости в настройках.')));return;}
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[!s.speed_enabled?E('p',{},bi('This will enable manual speed tests with the current limits and run the selected test. Automatic tests after connection remain off.','Будут включены ручные тесты с текущими лимитами и запущено выбранное измерение. Автотесты после подключения останутся выключены.')):null,E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('p',{'data-speed-pause-review':'1'},bi('Auto and background monitoring pause for the test. VPN connections remain up. Afterwards monitoring resumes before Auto; a manual Stop is respected.','На время теста Auto и фоновый мониторинг приостанавливаются. VPN остаются подключёнными. Затем возобновляется мониторинг и после него Auto; ручной Stop учитывается.')),E('ul',{},selected.map(function(id){var q=profiles.filter(function(p){return p.id===id;})[0];return E('li',{},q?serverTitle(q):id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return speedStartRequest(s,selected,mib,duration,streams).then(function(result){speedLiveQueued(result,selected);speedFeedback=result&&result.accepted===true?null:(result&&safeCode(result.code)?result.code:'SPEED-START-FAILED');ui.addNotification(null,E('p',{},result&&result.accepted===true?bi('The test is queued; results appear in the table.','Тест поставлен в очередь; результаты появятся в таблице.'):(result&&safeCode(result.code)?result.code:'SPEED-START-FAILED')));ui.hideModal();}).catch(function(){speedFeedback='SPEED-START-FAILED';ui.addNotification(null,E('p',{},'SPEED-START-FAILED'));});},{key:'speed-start'});}},(s.speed_enabled?bi('Run test','Запустить тест'):bi('Enable and run test','Включить и запустить тест'))),'speed-start')].filter(Boolean));
  }},bi('Test speed','Тестировать скорость'));
  var cancel=E('button',{'type':'button','class':'cbi-button','disabled':running?null:'','click':function(){return rpc.declare({object:'homensai-vpn',method:'speed_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.queued?bi('Cancel requested.','Отмена запрошена.'):bi('No test is running.','Сейчас тест не идёт.')));});}},bi('Cancel current test','Отменить текущий тест'));
  var periodSelect=E('select',{'aria-label':bi('Show results for','Показать результаты за'),'change':function(ev){onPeriod(ev.target.value);}},[['latest',bi('Latest test','Последний тест')],['day',bi('Today','Сегодня')],['week',bi('Last 7 days','Последние 7 дней')],['month',bi('Current calendar month','Текущий календарный месяц')]].map(function(row){return E('option',{value:row[0]},row[1]);}));periodSelect.value=period;
  section.appendChild(E('div',{'class':'hv-native-actions'},[test,cancel,E('label',{'class':'hv-speed-period'},[bi('Results for: ','Результаты за: '),periodSelect])]));
  section.appendChild(E('p',{'role':'status'},speedStateText(history)+' '+bi('Finished tests: ','Завершено тестов: ')+(history.completed||0)));
  if(!s.speed_enabled)section.appendChild(E('p',{'class':'hv-muted'},bi('Press Test speed to review enabling manual tests and their traffic budget.','Нажмите «Тестировать скорость»: откроется проверка включения ручных тестов и расхода трафика.')));
  if(speedFeedback)section.appendChild(E('p',{'class':'alert-message warning','role':'status'},speedReason(speedFeedback)+' · '+speedFeedback));
  section.appendChild(typeof limitTableRows==='function'?limitTableRows(table,5,'speed-other'):table);
  section.appendChild(renderSpeedLive(status,inventory,function(data){running=speedLiveRunning(data);test.disabled=running;cancel.disabled=!running;}));
  var oldChart=E('details',{'class':'hv-speed-completed-history','data-auto-disclosure':'speed-completed-history'},[E('summary',{},bi('Completed test history','История завершённых тестов')),renderSpeedChart(rows,profiles,period)]);
  if(typeof rememberDisclosure==='function')rememberDisclosure(oldChart,'speed-completed-history');section.appendChild(oldChart);
  section.appendChild(E('small',{},bi('Mean of successful tests; failed or cancelled tests are not counted as zero speed. History is sampled and bounded.','Среднее по успешным тестам; ошибки и отмены не считаются нулевой скоростью. История выборочная и ограниченная.')));
  if(history.history_error)section.appendChild(E('p',{},history.history_error));
  if(history.history_truncated)section.appendChild(E('p',{},'SPEED-HISTORY-TRUNCATED: '+history.history_truncated));
  return section;
}
/* Stored bounded HTTPS goodput samples. Failed measurements break the line. */
var SPEED_CHART_PROFILE=null;
function speedChartSamples(rows,id,period){
  var result=rows.filter(function(r){return r&&r.id===id&&Number.isFinite(r.time)&&r.time>0;}).slice().sort(function(a,b){return a.time-b.time;});
  return period==='latest'?result.slice(-1):result;
}
function speedChartValue(row,key){
  var value=row&&row[key]&&row[key].mbps;
  return !row.code&&Number.isFinite(value)&&value>=0&&value<=10000000?value:null;
}
function speedChartSvg(tag,attrs,text){
  var n=document.createElementNS('http://www.w3.org/2000/svg',tag);
  Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});
  if(text!==undefined)n.textContent=text;return n;
}
function renderSpeedChart(rows,profiles,period){
  var ids=[];profiles.filter(function(p){return p.interface;}).forEach(function(p){if(ids.indexOf(p.id)<0)ids.push(p.id);});
  rows.forEach(function(r){if(r&&typeof r.id==='string'&&ids.indexOf(r.id)<0)ids.push(r.id);});
  if(ids.indexOf(SPEED_CHART_PROFILE)<0)SPEED_CHART_PROFILE=ids[0]||null;
  function name(id){var p=profiles.find(function(p){return p.id===id;}),last=rows.find(function(r){return r.id===id;});return p?serverTitle(p):last&&last.name||id;}
  var host=E('div',{'class':'hv-speed-chart-plot','style':'width:100%;overflow:hidden'}),summary=E('p',{'class':'hv-muted','role':'status'});
  function draw(){
    while(host.firstChild)host.removeChild(host.firstChild);
    var samples=speedChartSamples(rows,SPEED_CHART_PROFILE,period),values=[];
    samples.forEach(function(r){['download','upload'].forEach(function(k){var v=speedChartValue(r,k);if(v!==null)values.push(v);});});
    summary.textContent=bi('Measured tests only; gaps and errors are not zero speed.','Только выполненные измерения; пропуски и ошибки не означают нулевую скорость.');
    if(!values.length){host.appendChild(E('p',{},bi('Run a test: its download and upload results will appear here.','Запустите тест: здесь появятся результаты скачивания и отдачи.')));return;}
    var start=samples[0].time,end=samples[samples.length-1].time;
    if(end===start){start-=30;end+=30;}
    var maximum=Math.max(1,Math.ceil(Math.max.apply(null,values)*1.15));
    var x=function(t){return 65+(t-start)/(end-start)*810;},y=function(v){return 240-v/maximum*205;};
    var svg=speedChartSvg('svg',{'viewBox':'0 0 910 290','role':'img','aria-label':bi('Download and upload speed history in Mbps','История скорости скачивания и отдачи в Мбит/с'),'style':'display:block;width:100%;height:auto;min-height:180px'});
    for(var i=0;i<=4;i++){
      var value=maximum*i/4,lineY=y(value);
      svg.appendChild(speedChartSvg('line',{x1:65,y1:lineY,x2:875,y2:lineY,stroke:'#b8c3cd','stroke-width':.6}));
      svg.appendChild(speedChartSvg('text',{x:57,y:lineY+4,'text-anchor':'end',fill:'currentColor','font-size':12},value.toFixed(value<10?1:0)));
    }
    svg.appendChild(speedChartSvg('text',{x:65,y:18,fill:'currentColor','font-size':12},bi('Mbps','Мбит/с')));
    [0,.5,1].forEach(function(part){var t=start+(end-start)*part;svg.appendChild(speedChartSvg('text',{x:x(t),y:268,'text-anchor':'middle',fill:'currentColor','font-size':12},new Date(t*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})));});
    [['download','#139c75',bi('Download','Скачивание')],['upload','#386af2',bi('Upload','Отдача')]].forEach(function(series){
      var segment=[];
      function flush(){if(segment.length>1)svg.appendChild(speedChartSvg('polyline',{points:segment.join(' '),fill:'none',stroke:series[1],'stroke-width':2.5,'data-speed-series':series[0]}));segment=[];}
      samples.forEach(function(row){var v=speedChartValue(row,series[0]);if(v===null){flush();return;}segment.push(x(row.time)+','+y(v));
        var dot=speedChartSvg('circle',{cx:x(row.time),cy:y(v),r:4,fill:series[1],'data-speed-point':series[0]});
        dot.appendChild(speedChartSvg('title',{},name(row.id)+' · '+series[2]+': '+v.toFixed(2)+' '+bi('Mbps','Мбит/с')+' · '+new Date(row.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})));svg.appendChild(dot);
      });flush();
    });
    host.appendChild(svg);
  }
  var choose=E('select',{'aria-label':bi('Server for speed graph','Сервер графика скорости'),'style':'max-width:100%;min-height:42px;','change':function(ev){SPEED_CHART_PROFILE=ev.target.value;draw();}},ids.map(function(id){return E('option',{value:id},name(id));}));choose.value=SPEED_CHART_PROFILE||'';
  draw();
  return E('section',{'class':'hv-speed-history','style':'margin-top:24px;border-top:1px solid #d9dfe5;padding-top:16px;'},[
    E('h4',{},bi('Completed test averages','Средние скорости завершённых тестов')),choose,
    E('p',{},[E('span',{'style':'color:#139c75'},'● '+bi('Download','Скачивание')),' · ',E('span',{'style':'color:#386af2'},'● '+bi('Upload','Отдача'))]),host,summary
  ]);
}
