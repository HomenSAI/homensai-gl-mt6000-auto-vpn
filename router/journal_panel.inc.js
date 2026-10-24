/* Shared real-event vocabulary for the live terminal and persisted history. */
var EVENT_VIEW={query:'',sort:'time',desc:true,expanded:false,page:0,stored:null,busy:false,error:null,request:0};
function journalHistoryDays(status){
  var values=[((status.accounting||{}).reliability||{}).detail_days,(status.native_history||{}).detail_days].filter(function(n){return Number.isInteger(n)&&n>=1&&n<=7;});
  return values.length?Math.min.apply(Math,values):7;
}
function renderChannelBadge(model){
  if(!model)return null;
  var main=bi('Main channel','Основной канал'),reserve=bi('Reserve channel','Резервный канал');
  var label=model.phase==='confirmed'?bi('Confirmed transition: ','Подтверждённый переход: '):model.phase==='pending'?bi('Transition stage, awaiting confirmation: ','Этап перехода, ожидается подтверждение: '):model.phase==='failed'?bi('Connection failed: ','Ошибка соединения: '):bi('Connection recovered: ','Соединение восстановлено: ');
  label+=model.from?(model.from==='source'?main:reserve)+' → '+(model.to==='source'?main:reserve):(model.to==='source'?main:reserve);
  var colors={source:'neutral',target:'neutral'};
  if(model.phase==='pending'){colors.source='pending';colors.target='pending';}
  else if(model.phase==='confirmed'){colors[model.from]='failed';colors[model.to]='working';}
  else colors[model.to]=model.phase==='failed'?'failed':'working';
  function circle(role,letter,title){return E('span',{'class':'hv-channel-dot hv-channel-'+colors[role],'data-channel-role':role,'aria-hidden':'true','title':title},letter);}
  var reverse=model.from==='target',moving=model.phase==='pending';
  return E('span',{'class':'hv-channel-badge'+(moving?' hv-channel-moving':'')+(reverse?' hv-channel-reverse':''),'data-channel-phase':model.phase,'role':'img','aria-label':label,'title':label},[
    circle('source','M',main),E('span',{'class':'hv-channel-arrow','aria-hidden':'true'},model.from?(reverse?'←':'→'):'·'),circle('target','R',reserve)]);
}
function journalChannelModel(entry){
  var pair=entry.source&&entry.target&&entry.source!==entry.target;
  if(pair&&['APPLYING','WAIT-CLIENT','ARMED'].indexOf(entry.state)>=0)return {phase:'pending',from:'source',to:'target'};
  if(pair&&entry.state==='RESTORING')return {phase:'pending',from:'target',to:'source'};
  if(pair&&['COMMITTED','STOPPED-ON-RESERVE'].indexOf(entry.state)>=0)return {phase:'confirmed',from:'source',to:'target'};
  if(pair&&(entry.return_primary===true||entry.state==='ROLLED-BACK'&&entry.original_restored===true))return {phase:'confirmed',from:'target',to:'source'};
  if(['source','target'].indexOf(entry.role)>=0){
    if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')return {phase:'recovered',to:entry.role};
    if(entry.state==='FAILURE'||entry.kind==='FAILURE'||entry.level==='error')return {phase:'failed',to:entry.role};
  }
  return null;
}
function renderJournalChannelBadge(entry){return renderChannelBadge(journalChannelModel(entry));}
function journalSourceLabel(source){
  return source==='manual'?bi('operator command','оператор — вручную'):source==='automatic'?bi('automatic controller','контроллер — автоматически'):source==='test'?bi('programmatic test','тестовая программа — автоматически'):source==='programmatic'?bi('programmatic command','программа — программная команда'):bi('source not recorded','источник не указан');
}
function journalToken(value,fallback){return typeof value==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(value)?value.toUpperCase():fallback;}
function journalLatencySample(raw,profile,eventTime){
  if(typeof profile!=='string'||!/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(profile)||!raw||typeof raw!=='object'||raw.profile!==profile||raw.metric!=='https-rtt-ms'||!Number.isFinite(eventTime)||!Number.isFinite(raw.time)||raw.time<eventTime-90||raw.time>eventTime+5||!Number.isFinite(raw.rtt_ms)||raw.rtt_ms<0||raw.rtt_ms>600000||typeof raw.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(raw.interface)||(profile.indexOf('wireguard:')===0)!==(raw.interface.indexOf('wgclient')===0)||typeof raw.generation!=='string'||!/^[a-f0-9]{32}$/.test(raw.generation))return null;
  return {profile:profile,metric:'https-rtt-ms',time:raw.time,rtt_ms:raw.rtt_ms,interface:raw.interface,generation:raw.generation};
}
function journalLatencyText(entry){
  var reverse=['RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0||entry.return_primary===true,profile=reverse?entry.source:entry.target;
  var sample=journalLatencySample(entry.latency,profile,entry.time);
  return sample?bi('Delay: ','Задержка: ')+sample.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')+' · '+bi('measured ','замер ')+new Date(sample.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):bi('Delay: no saved measurement at this event','Задержка: нет сохранённого замера на момент события');
}
function journalCurrentLatency(p,status,now){
  if(!p||status.rpc_error||status.error||!Number.isFinite(status.time)||status.time<now-90||status.time>now+5||p.vendor_state!=='SETTLED'||p.vendor_tunnel_id!==p.protocol+':'+p.interface||p.code!=null||p.dns_ok!==true||!Number.isInteger(p.https_success)||p.https_success<2)return null;
  return journalLatencySample({profile:p.id,metric:'https-rtt-ms',time:p.time,rtt_ms:p.rtt_ms,interface:p.interface,generation:p.vendor_generation},p.id,now);
}
function journalMessage(entry,status){
  var names={COMMITTED:['Reserve selected','Выбран резерв'],OBSERVING:['Primary selected','Выбран основной'],'ROLLED-BACK':['Returned to primary','Возврат на основной'],FAILURE:['Connection failed','Ошибка соединения'],RECOVERY:['Connection recovered','Соединение восстановлено'],GAP:['Observation gap','Пропуск наблюдений'],STARTING:['Auto starting','Auto запускается'],STOPPED:['Auto stopped','Auto остановлен']};
  var label=names[entry.state]||names[entry.kind],text=label?bi(label[0],label[1]):entry.state;
  var profiles=Array.isArray(status.profiles)?status.profiles:[],p=profiles.find(function(p){return p.id===entry.profile;});
  if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')text=entry.role==='source'?bi('Connection restored on the primary channel','Соединение восстановлено на основном канале'):entry.role==='target'?bi('Connection restored on the reserve channel','Соединение восстановлено на резервном канале'):bi('Connection restored · channel was not saved in this record','Соединение восстановлено · канал не сохранён в этой записи');
  else if(entry.profile)text=(entry.role==='source'?bi('Primary channel','Основной канал'):entry.role==='target'?bi('Reserve channel','Резервный канал'):bi('Channel not saved in this record','Канал не сохранён в этой записи'))+' — '+text;
  if(entry.state==='AUTO-START-REQUESTED')text=bi('Auto: activation requested','Auto: запрошено включение');
  if(entry.state==='AUTO-STOP-REQUESTED')text=bi('Auto: deactivation requested','Auto: запрошено выключение');
  if(entry.state==='APPLYING')text=bi('Switch: primary → reserve','Переход: основной → резервный');
  if(entry.state==='RESTORING')text=bi('Switch: reserve → primary','Переход: резервный → основной');
  if(entry.return_primary)text=bi('Returned: reserve → primary','Возврат: резервный → основной');
  var sourced=entry.origin==='control'||entry.action_source||['APPLYING','RESTORING','COMMITTED','ROLLED-BACK','STOPPED'].indexOf(entry.state)>=0;
  var switching=entry.return_primary===true||['APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE','RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0;
  return text+(entry.profile?' · '+(p?serverTitle(p):entry.profile):'')+(sourced?' · '+journalSourceLabel(entry.action_source):'')+(switching?' · '+journalLatencyText(entry):'')+(entry.code?' · '+entry.code:'');
}
function journalRows(status,stored,now){
  var retainedSeconds=journalHistoryDays(status)*86400;
  var groups=[['controller',stored?stored.controller.events:(status.native_history||{}).events||[]],['failures',stored?stored.failures.events:((status.accounting||{}).reliability||{}).events||[]],['monitor',stored?[]:status.events||[]]],result=[],seen=Object.create(null);
  function control(action,stamp,source){
    if(['start','stop'].indexOf(action)<0||!Number.isFinite(stamp)||stamp<=0||stamp<now-retainedSeconds||stamp>now+5)return;
    var key='control:'+action+':'+stamp;if(seen[key])return;seen[key]=true;
    result.push({key:key,time:stamp,state:action==='start'?'AUTO-START-REQUESTED':'AUTO-STOP-REQUESTED',kind:'CONTROL',profile:null,code:null,level:'ok',origin:'control',action_source:['manual','automatic','test','programmatic'].indexOf(source)>=0?source:'unknown'});
  }
  groups.forEach(function(group){if(!Array.isArray(group[1]))return;
    group[1].slice(-10000).forEach(function(e){
      if(!e||!Number.isFinite(e.time)||e.time<now-retainedSeconds||e.time>now+5)return;
      control(e.control_action,e.control_time,e.control_source);
      var state=journalToken(e.state||e.kind||e.code,'OBSERVATION'),code=typeof e.code==='string'&&safeCode(e.code)?e.code:Array.isArray(e.codes)?e.codes.find(safeCode)||null:null;
      var profile=typeof(e.profile||e.id)==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e.profile||e.id)?e.profile||e.id:null;
      var key=group[0]+':'+(Number.isSafeInteger(e.sequence)?e.sequence:[e.time,profile,state,code].join(':'));
      if(seen[key])return;seen[key]=true;
      var failed=/FAIL|REFUS|ERROR|DEGRADED/.test(state)||!!code&&/^(DNS-|VPN-|SYSTEM-|CHECK-)|FAILED|ERROR|REFUSED/.test(code),level=failed?'error':/GAP|UNKNOWN|UNCONFIRMED|CANCEL|INACTIVE/.test(state)?'warning':'ok';
      var pair={};['source','target'].forEach(function(k){pair[k]=typeof e[k]==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e[k])?e[k]:null;});
      var actionSource=['manual','automatic','test','programmatic','unknown'].indexOf(e.transition_source)>=0?e.transition_source:e.manual===true?'unknown':e.trial===true?'test':null;
      if(!actionSource&&Array.isArray(e.codes)){
        if(e.codes.some(function(c){return c==='OPERATOR-MANUAL'||c==='OPERATOR-RETURN';}))actionSource='unknown';
        else if(e.codes.some(function(c){return c==='OPERATOR-TRIAL'||c==='TRIAL-PASSED';}))actionSource='test';
        else if(e.codes.some(function(c){return ['SOURCE-FAILED','PRIMARY-STABLY-RECOVERED','RESERVE-FAILED-PRIMARY-VERIFIED'].indexOf(c)>=0;}))actionSource='automatic';
      }
      if(!actionSource&&state==='STOPPED'&&e.control_action==='stop')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      var returnPrimary=state==='STOPPED'&&Array.isArray(e.codes)&&e.codes.indexOf('OPERATOR-RETURN')>=0;
      var delayProfile=(returnPrimary||['RESTORING','ROLLED-BACK'].indexOf(state)>=0)?pair.source:pair.target;
      var role=['source','target'].indexOf(e.role)>=0?e.role:null;
      if(!role&&profile&&pair.source&&pair.target&&pair.source!==pair.target)role=profile===pair.source?'source':profile===pair.target?'target':null;
      result.push({key:key,time:e.time,state:state,kind:journalToken(e.kind,'OBSERVATION'),code:code,profile:profile,role:role,source:pair.source,target:pair.target,original_restored:e.original_restored===true,return_primary:returnPrimary,latency:journalLatencySample(e.latency,delayProfile,e.time),action_source:actionSource,level:level,origin:group[0]});
    });
  });
  var request=status.auto_control||{};
  if(request.requested==='on'||request.requested==='off')control(request.request_action,request.requested_at,request.request_source);
  return result.sort(function(a,b){return b.time-a.time||a.key.localeCompare(b.key);});
}
function filteredJournalRows(rows,status,query,sort,desc){
  var needle=String(query||'').trim().toLocaleLowerCase();
  return rows.filter(function(row){return !needle||[row.state,row.kind,row.code,row.profile,row.origin,journalMessage(row,status),new Date(row.time*1000).toLocaleString()].join(' ').toLocaleLowerCase().includes(needle);}).sort(function(a,b){var compared=sort==='state'?a.state.localeCompare(b.state):a.time-b.time;return (desc?-compared:compared)||b.time-a.time||a.key.localeCompare(b.key);});
}
function renderEventHistory(status){
  EVENT_VIEW.status=status;
  if(EVENT_VIEW.root&&EVENT_VIEW.language===locale){if(!EVENT_VIEW.stored&&!EVENT_VIEW.expanded&&!EVENT_VIEW.query)EVENT_VIEW.draw();return EVENT_VIEW.root;}
  EVENT_VIEW.language=locale;
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,host=E('section',{'class':'hv-chart-card','data-event-history':'1'}),tableHost=E('div'),note=E('p',{'role':'status'});
  var query=E('input',{'type':'search','class':'hv-search','maxlength':'256','aria-label':bi('Search all retained events','Поиск по всем сохранённым событиям'),'placeholder':bi('Search words, state or error code','Поиск по словам, состоянию или коду'),'input':function(ev){EVENT_VIEW.query=ev.target.value.slice(0,256);EVENT_VIEW.page=0;if(!EVENT_VIEW.stored)load();draw();}});query.value=EVENT_VIEW.query;
  var order=E('select',{'aria-label':bi('Sort event history','Сортировка истории'),'change':function(ev){EVENT_VIEW.sort=ev.target.value==='state'?'state':'time';EVENT_VIEW.page=0;draw();}},[E('option',{value:'time'},bi('Date and time','Дата и время')),E('option',{value:'state'},bi('State','Состояние'))]);order.value=EVENT_VIEW.sort;
  var direction=E('button',{'type':'button','class':'cbi-button','click':function(){EVENT_VIEW.desc=!EVENT_VIEW.desc;draw();}});
  var more=E('button',{'type':'button','class':'cbi-button','aria-expanded':EVENT_VIEW.expanded?'true':'false','click':function(){EVENT_VIEW.expanded=!EVENT_VIEW.expanded;EVENT_VIEW.page=0;if(EVENT_VIEW.expanded&&!EVENT_VIEW.stored)load();draw();}});
  async function load(){
    if(EVENT_VIEW.busy)return;EVENT_VIEW.busy=true;EVENT_VIEW.error=null;var request=++EVENT_VIEW.request;draw();
    try{
      var call=rpc.declare({object:'homensai-vpn',method:'statistics',params:['kind','after','until'],expect:{}});
      var records=await Promise.all([fetchStoredStatistics('controller',call),fetchStoredStatistics('failures',call)]);
      if(request===EVENT_VIEW.request)EVENT_VIEW.stored={controller:records[0],failures:records[1]};
    }catch(error){if(request===EVENT_VIEW.request)EVENT_VIEW.error='STATISTICS-READ-FAILED';}
    finally{if(request===EVENT_VIEW.request){EVENT_VIEW.busy=false;draw();}}
  }
  function draw(){
    var status=EVENT_VIEW.status,now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
    while(tableHost.firstChild)tableHost.removeChild(tableHost.firstChild);
    var rows=filteredJournalRows(journalRows(status,EVENT_VIEW.stored,now),status,EVENT_VIEW.query,EVENT_VIEW.sort,EVENT_VIEW.desc),size=EVENT_VIEW.expanded?500:20;
    EVENT_VIEW.page=Math.max(0,Math.min(EVENT_VIEW.page,Math.max(0,Math.ceil(rows.length/size)-1)));
    var selected=rows.slice(EVENT_VIEW.page*size,(EVENT_VIEW.page+1)*size),table=E('table',{'class':'table hv-event-history','data-hv-no-sort':'1'},[
      E('thead',{},E('tr',{},[bi('Date and time','Дата и время'),bi('State','Состояние'),bi('Event','Событие')].map(function(label){return E('th',{},label);}))),
      E('tbody',{},selected.map(function(row){return E('tr',{'data-event-key':row.key},[E('td',{},new Date(row.time*1000).toLocaleString()),E('td',{},[renderJournalChannelBadge(row),row.state].filter(Boolean)),E('td',{},journalMessage(row,status))]);}))]);
    tableHost.appendChild(E('div',{'class':'hv-dv-tablewrap'},table));
    if(EVENT_VIEW.expanded&&rows.length>size){
      tableHost.appendChild(E('div',{'class':'hv-native-actions'},[
        E('button',{'type':'button','class':'cbi-button','disabled':EVENT_VIEW.page===0?'':null,'click':function(){EVENT_VIEW.page--;draw();}},bi('Previous','Назад')),
        E('span',{},String(EVENT_VIEW.page+1)+' / '+Math.ceil(rows.length/size)),
        E('button',{'type':'button','class':'cbi-button','disabled':(EVENT_VIEW.page+1)*size>=rows.length?'':null,'click':function(){EVENT_VIEW.page++;draw();}},bi('Next','Далее'))]));
    }
    direction.textContent=EVENT_VIEW.desc?bi('Descending ↓','По убыванию ↓'):bi('Ascending ↑','По возрастанию ↑');
    more.textContent=(EVENT_VIEW.expanded?'▾ ':'▸ ')+(EVENT_VIEW.expanded?bi('Show 20 rows','Свернуть до 20 строк'):bi('More history','Остальная история'))+' · '+rows.length;more.setAttribute('aria-expanded',EVENT_VIEW.expanded?'true':'false');
    more.disabled=EVENT_VIEW.busy;
    note.textContent=EVENT_VIEW.busy?bi('Reading saved history…','Чтение сохранённой истории…'):EVENT_VIEW.error||(!EVENT_VIEW.stored?bi('Showing the latest status snapshot. More/search reads all retained records; it does not create missing history.','Показан последний снимок событий. Раскрытие/поиск прочитает всю сохранённую историю; отсутствующие записи не создаются.'):bi('Search and sorting cover the full downloaded retained snapshot. Storage/count limits and unobserved gaps remain explicit.','Поиск и сортировка охватывают весь загруженный снимок за выбранный срок. Ограничения хранения и пропуски сохраняются.'));
    if(EVENT_VIEW.stored){
      var records=[EVENT_VIEW.stored.controller,EVENT_VIEW.stored.failures],limited=records.some(function(r){var s=r.summary||{};return r.storage_notice||s.details_dropped>0||s.detail_budget_dropped>0||s.weekly_detail_complete===false;});
      if(limited)note.textContent+=' '+bi('Some saved details are unavailable or were dropped by the storage limit. This is not a complete record of every event.','Часть сохранённых подробностей недоступна или удалена по лимиту хранилища. Это не полный список всех произошедших событий.');
    }
  }
  host.appendChild(E('h3',{},bi('Events and errors: saved history','События и ошибки: сохранённая история')));host.appendChild(E('div',{'class':'hv-native-actions'},[query,order,direction]));host.appendChild(note);host.appendChild(tableHost);host.appendChild(more);
  host.appendChild(E('small',{},bi('The live terminal shows these real observations as they arrive. Its one-second screen heartbeat is not a persisted router event. Detailed controller/failure records are retained for the configured 1–7 days within bounded stores.','Живой терминал показывает эти реальные наблюдения по мере получения. Секундный heartbeat экрана не является сохранённым событием роутера. Подробности контроллера/сбоев хранятся выбранные 1–7 дней в ограниченных журналах.')));EVENT_VIEW.root=host;EVENT_VIEW.draw=draw;draw();return host;
}
