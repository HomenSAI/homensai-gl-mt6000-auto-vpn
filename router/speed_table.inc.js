/* One table for the speed tests: tick servers, press "Test speed" (or cancel), and the same table shows the results.
   Replaces the older panel that had a drop-down, a second table of results and a "recommended priorities" button
   (later function declaration wins). */
var speedSelected={};
function speedStateText(history){
  var state=history.state||'IDLE';
  if(state==='IDLE'||state==='COMPLETED'||state==='COMPLETE')return bi('No test is running.','Сейчас тест не идёт.');
  if(state==='RUNNING'||state==='QUEUED'||state==='STARTING')return bi('A test is running; the table fills in as results arrive.','Идёт тест; таблица заполняется по мере поступления результатов.');
  return bi('State: ','Состояние: ')+state;
}
function speedPanel(status,inventory,period,onPeriod){
  var history=status.speed_tests||{},s=inventory.settings||{},profiles=status.profiles||[];
  var active=profiles.filter(function(p){return p.interface;}).slice(0,8);
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
  var section=E('section',{'class':'hv-chart-card hv-speed-panel'},[
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
  var test=E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','disabled':s.speed_enabled&&active.length?null:'','click':function(){
    var selected=active.filter(function(p){return speedSelected[p.id];}).map(function(p){return p.id;}),mib=s.speed_budget_mib==null?8:s.speed_budget_mib,duration=s.speed_duration==null?5:s.speed_duration,streams=s.speed_streams==null?2:s.speed_streams;
    if(!s.speed_enabled||!active.length)return;
    if(!selected.length){ui.addNotification(null,E('p',{},bi('Tick at least one connected server in the table first.','Сначала отметьте в таблице хотя бы один подключённый сервер.')));return;}
    if(![['speed.budget_mib',mib],['speed.duration',duration],['speed.streams',streams]].every(function(row){return foolCheckNumber(row[0],row[1]).ok;})){ui.addNotification(null,E('p',{},bi('Check the speed test limits in the settings first.','Сначала проверьте ограничения теста скорости в настройках.')));return;}
    ui.showModal(bi('Review speed test','Проверьте запуск теста'),[E('p',{},bi('Payload quota reservation: ','Резервируемая квота полезного трафика: ')+(selected.length*mib)+' MiB'),E('p',{},bi('Protocol overhead adds traffic; tests may slow other applications.','Служебный трафик расходуется дополнительно; тесты могут замедлить другие приложения.')),E('ul',{},selected.map(function(id){var q=profiles.filter(function(p){return p.id===id;})[0];return E('li',{},q?serverTitle(q):id);})),E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Cancel','Отмена')),guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action hv-primary-action','click':function(ev){var button=ev.currentTarget;return guardedAction(button,function(){return rpc.declare({object:'homensai-vpn',method:'speed_start',params:['profiles','budget_mib','duration','streams'],expect:{}})(selected,mib,duration,streams).then(function(result){ui.addNotification(null,E('p',{},result&&result.accepted===true?bi('The test is queued; results appear in the table.','Тест поставлен в очередь; результаты появятся в таблице.'):(result&&safeCode(result.code)?result.code:'SPEED-START-FAILED')));ui.hideModal();}).catch(function(){ui.addNotification(null,E('p',{},'SPEED-START-FAILED'));});},{key:'speed-start'});}},bi('Run test','Запустить тест')),'speed-start')]);
  }},bi('Test speed','Тестировать скорость'));
  var cancel=E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',method:'speed_cancel',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.queued?bi('Cancel requested.','Отмена запрошена.'):bi('No test is running.','Сейчас тест не идёт.')));});}},bi('Cancel current test','Отменить текущий тест'));
  var periodSelect=E('select',{'aria-label':bi('Show results for','Показать результаты за'),'change':function(ev){onPeriod(ev.target.value);}},[['latest',bi('Latest test','Последний тест')],['day',bi('Today','Сегодня')],['week',bi('Last 7 days','Последние 7 дней')],['month',bi('Current calendar month','Текущий календарный месяц')]].map(function(row){return E('option',{value:row[0]},row[1]);}));periodSelect.value=period;
  section.appendChild(E('div',{'class':'hv-native-actions'},[test,cancel,E('label',{'class':'hv-speed-period'},[bi('Results for: ','Результаты за: '),periodSelect])]));
  section.appendChild(E('p',{'role':'status'},speedStateText(history)+' '+bi('Finished tests: ','Завершено тестов: ')+(history.completed||0)));
  if(!s.speed_enabled)section.appendChild(E('p',{'class':'alert-message warning'},[bi('Speed tests are switched off. ','Тесты скорости выключены. '),E('a',{'href':'#tests','click':function(ev){ev.preventDefault();goToSection('tests','hv-speed-settings');}},bi('Turn them on in Advanced → Tests → Speed test settings.','Включите их в «Расширенное» → «Тесты» → «Настройки тестов скорости».'))]));
  section.appendChild(typeof limitTableRows==='function'?limitTableRows(table,5,'speed-other'):table);
  section.appendChild(E('small',{},bi('Mean of successful tests; failed or cancelled tests are not counted as zero speed. History is sampled and bounded.','Среднее по успешным тестам; ошибки и отмены не считаются нулевой скоростью. История выборочная и ограниченная.')));
  if(history.history_error)section.appendChild(E('p',{},history.history_error));
  if(history.history_truncated)section.appendChild(E('p',{},'SPEED-HISTORY-TRUNCATED: '+history.history_truncated));
  return section;
}
