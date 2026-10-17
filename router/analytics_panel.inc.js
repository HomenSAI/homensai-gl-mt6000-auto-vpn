/* HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT */
function cascadePathModel(status,now){
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&now>=status.time&&now-status.time<=90;
  var selected=fresh?selectedProfile(status,now):null,rows=status.profiles||[];
  var current=rows.find(function(p){return p.id===selected;});
  if(!current)selected=null;
  var groups=[],candidates=[];
  rows.forEach(function(p){
    var protocol=p.protocol==='wireguard'?'WireGuard':p.protocol==='openvpn'?'OpenVPN':'Unknown';
    var channel=String(p.channel||'default');
    var group=groups.find(function(g){return g.protocol===protocol&&g.channel===channel;});
    if(!group){group={protocol:protocol,channel:channel,servers:[]};groups.push(group);}
    var state=fresh?profileHealth(p,now).state:'unknown';
    var enabled=p.enabled!==false&&p.enabled!=='0';
    var reason=p.id===selected?'SELECTED-BY-CONTROLLER':!enabled?'DISABLED':state==='healthy'?'EDGE-NOT-CERTIFIED':state.toUpperCase();
    group.servers.push({id:p.id,name:p.name||p.id,state:state,selected:p.id===selected,reason:reason});
    if(current&&p.id!==selected&&enabled&&state==='healthy')candidates.push({id:p.id,
      tier:p.protocol!==current.protocol?2:p.channel!==current.channel?1:0,
      priority:Number.isFinite(Number(p.priority))?Number(p.priority):Infinity});
  });
  candidates.sort(function(a,b){return a.tier-b.tier||a.priority-b.priority||String(a.id).localeCompare(String(b.id));});
  groups.forEach(function(g){g.servers.sort(function(a,b){return Number(b.selected)-Number(a.selected);});});
  groups.sort(function(a,b){return Number(b.servers.some(function(s){return s.selected;}))-Number(a.servers.some(function(s){return s.selected;}));});
  return {selected:selected,groups:groups,next:candidates.length?candidates[0].id:null,fresh:fresh};
}
function renderCascadePath(status){
  var model=cascadePathModel(status,Date.now()/1000);
  return E('section',{'class':'hv-chart-card'},[
    E('h2',{},bi('Protocol / channel / server path','Путь: протокол / канал / сервер')),
    E('p',{},bi('Selected route requires fresh controller evidence. Candidate suggestions do not authorize switching.','Выбранный маршрут требует свежего подтверждения контроллера. Рекомендация кандидата не разрешает переключение.')),
    E('p',{},bi('Next healthy suggestion: ','Следующий работающий кандидат: ')+(model.next||'—')+' · EDGE-NOT-CERTIFIED'),
    E('div',{'class':'hv-cascade-grid'},model.groups.map(function(g){return E('section',{'class':'hv-auto-node'},[
      E('strong',{},g.protocol),E('b',{},g.channel),E('ul',{},g.servers.map(function(s){return E('li',{},[
        E('strong',{'class':'hv-badge hv-health-'+s.state},s.selected?bi('Selected','Выбран'):({healthy:bi('Healthy','Работает'),failed:bi('Failed','Сбой'),checking:bi('Checking','Проверяется'),inactive:bi('Inactive','Неактивен'),unknown:bi('Unknown','Неизвестно')}[s.state]||s.state)),
        E('span',{},' '+s.name+(s.id===model.next?' → '+bi('Candidate','Кандидат'):'')),
        E('small',{},s.reason)
      ]);} ))
    ]);})),
    E('small',{},bi('Hierarchy: another server → another channel → another VPN protocol. No implicit direct-WAN fallback.','Каскад: другой сервер → другой канал → другой протокол VPN. Автоматического выхода напрямую в WAN нет.'))
  ]);
}
function retainedTransitions(history){
  var events=(history.events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}),rows=[],open=null,last=null,lastTime=null;
  function close(outcome,event){if(!open)return;open.outcome=outcome;
    if(event&&Number.isFinite(event.time)&&event.time>=open.start){open.end=event.time;open.duration=open.applied_at==null?null:event.time-open.applied_at;}
    rows.push(open);open=null;
  }
  function identifier(value){return Number.isSafeInteger(value)&&value>0?value:null;}
  function begin(e){open={id:identifier(e.attempt_id)||e.sequence,retry_episode_id:identifier(e.retry_episode_id),
    prepared_at:e.state==='ARMED'?e.time:null,applied_at:e.state==='APPLYING'?e.time:null,start:e.time,end:null,duration:null,
    source:e.source||'unknown',target:e.target||'unknown',
    kind:['server','channel','protocol'].indexOf(e.transition_kind)>=0?e.transition_kind:'unknown',
    trial:e.trial===true,outcome:'pending',phases:[],codes:[],probe_evidence:{}};}
  events.forEach(function(e){
    if(!Number.isFinite(e.time)||e.time<0||e.time>253402300799||!Number.isSafeInteger(e.sequence)||e.sequence<1)return;
    if(last!==null&&e.sequence<=last)return;
    if(lastTime!==null&&e.time<lastTime){close('unknown',null);last=e.sequence;return;}
    lastTime=e.time;
    if(last!==null&&e.sequence!==last+1)close('unknown',null);
    last=e.sequence;
    var trialPassed=(e.codes||[]).indexOf('TRIAL-PASSED')>=0;
    var starting=e.state==='APPLYING'||e.state==='ARMED'&&!trialPassed;
    if(starting){
      var same=open&&open.applied_at==null&&(e.state==='APPLYING'||identifier(e.attempt_id)===open.id)&&
        (!e.attempt_id||e.attempt_id===open.id)&&(!e.source||e.source===open.source)&&(!e.target||e.target===open.target);
      if(!same){close('unknown',null);begin(e);}
      else if(e.state==='APPLYING'){open.applied_at=e.time;open.start=e.time;if(['server','channel','protocol'].indexOf(e.transition_kind)>=0)open.kind=e.transition_kind;}
    }
    if(!open)return;
    if(e.trial===true)open.trial=true;
    if((identifier(e.attempt_id)&&e.attempt_id!==open.id)||(e.source&&e.source!==open.source)||(e.target&&e.target!==open.target)){close('unknown',null);return;}
    open.phases.push({state:e.state,time:e.time});
    (e.codes||[]).forEach(function(code){if(typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)&&open.codes.indexOf(code)<0)open.codes.push(code);});
    var evidence=e.probe_evidence||{};
    ['source_streak_met','reserve_streak_met'].forEach(function(key){if(typeof evidence[key]==='boolean')open.probe_evidence[key]=evidence[key];});
    ['required_failures','required_successes'].forEach(function(key){if(Number.isInteger(evidence[key])&&evidence[key]>=2&&evidence[key]<=10)open.probe_evidence[key]=evidence[key];});
    if(Array.isArray(e.phase_evidence)){
      var phases=e.phase_evidence.filter(function(p){return p&&/^[A-Z0-9_-]{1,96}$/.test(p.phase)&&Number.isFinite(p.time)&&p.time<=e.time;});
      if(phases.length){open.phases=phases.map(function(p){return {state:p.phase,time:p.time};});if(open.phases[open.phases.length-1].state!==e.state)open.phases.push({state:e.state,time:e.time});}
    }
    if(e.state==='COMMITTED')close('committed',e);
    else if(trialPassed)close('trial_passed',e);
    else if(e.state==='ROLLED-BACK')close('rolled_back',e);
    else if(['BLOCKED','STOPPED','STOPPED-ON-RESERVE','EXPIRED'].indexOf(e.state)>=0)close('held',e);
  });
  close('pending',null);
  return rows;
}

function recoverySummary(rows,start,end){
  var selected=rows.filter(function(r){return r.start>=start&&r.start<end;}),durations=[],known=0,committed=0,trialsPassed=0;
  var streaks=Object.create(null),maxFailures=0;
  selected.slice().sort(function(a,b){return a.start-b.start;}).forEach(function(r){
    var outcome=r.end!=null&&r.end>=end?'pending':r.outcome;
    if(['committed','trial_passed','rolled_back','held'].indexOf(outcome)>=0)known++;
    if(outcome==='committed')committed++;
    if(outcome==='trial_passed')trialsPassed++;
    if(['committed','trial_passed','rolled_back'].indexOf(outcome)>=0&&Number.isFinite(r.duration)&&r.duration>=0)durations.push(r.duration);
    streaks[r.target]=['rolled_back','held'].indexOf(outcome)>=0?(streaks[r.target]||0)+1:0;
    maxFailures=Math.max(maxFailures,streaks[r.target]);
  });
  durations.sort(function(a,b){return a-b;});
  var n=durations.length;
  return {attempts:selected.length,known_outcomes:known,unknown_or_pending:selected.length-known,
    trial_attempts:selected.filter(function(r){return r.trial===true;}).length,
    automatic_attempts:selected.filter(function(r){return r.trial!==true;}).length,
    committed:committed,trials_passed:trialsPassed,success_ratio:known?(committed+trialsPassed)/known:null,recovered_samples:n,
    median:n?(durations[Math.floor((n-1)/2)]+durations[Math.floor(n/2)])/2:null,
    p95:n?durations[Math.ceil(n*0.95)-1]:null,worst:n?durations[n-1]:null,max_consecutive_failures:maxFailures};
}
function recoveryWindow(period,now,timezone){
  timezone=timezone||'Europe/Berlin';
  var formatter=new Intl.DateTimeFormat('en-GB',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  function localEpoch(stamp){var parts={};formatter.formatToParts(new Date(stamp)).forEach(function(p){parts[p.type]=p.value;});return Date.UTC(Number(parts.year),Number(parts.month)-1,Number(parts.day),Number(parts.hour),Number(parts.minute),Number(parts.second));}
  var d=new Date(localEpoch(now*1000));d.setUTCHours(0,0,0,0);
  if(period==='week')d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));
  else if(period==='month')d.setUTCDate(1);
  else if(period!=='day')throw new Error('RECOVERY-PERIOD');
  var desired=d.getTime(),candidate=desired;
  for(var i=0;i<3;i++)candidate=desired-(localEpoch(candidate)-candidate);
  return {start:candidate/1000,end:now,timezone:timezone};
}
function recoveryGroups(rows,profiles,start,end){
  var result={server:{},channel:{},protocol:{}};
  rows.forEach(function(row){var p=profiles.find(function(p){return p.id===row.target;})||{};
    [['server',row.target],['channel',p.channel||'unknown'],['protocol',p.protocol||'unknown']].forEach(function(pair){
      // Prefix untrusted labels, so '__proto__' is never an object prototype write.
      var key='group:'+pair[1];if(!result[pair[0]][key])result[pair[0]][key]={name:pair[1],rows:[]};result[pair[0]][key].rows.push(row);
    });
  });
  Object.keys(result).forEach(function(kind){result[kind]=Object.keys(result[kind]).map(function(key){var g=result[kind][key];return {name:g.name,metrics:recoverySummary(g.rows,start,end)};});});
  return result;
}
var exportSchemas={
  ranking:['server','name','protocol','channel','latency_ms','state'],
  traffic:['month','rx_bytes','tx_bytes','scope'],
  failures:['start_utc','source','target','outcome','codes','attempt_id','retry_episode_id'],
  transitions:['start_utc','source','target','kind','outcome','duration_seconds','trial','attempt_id','retry_episode_id','source_streak_met','reserve_streak_met','required_failures','required_successes']
};
function analyticsCSV(kind,rows){
  var columns=exportSchemas[kind];if(!columns)throw new Error('EXPORT-KIND');
  function cell(value){var text=value==null?'':String(value);
    if(/^[\s\u0000-\u001f\u007f\ufeff\u200b-\u200f\u202a-\u202e\u2060-\u206f]*[=+@-]/.test(text)||/^[\t\r\n]/.test(text))text="'"+text;
    return '"'+text.replace(/"/g,'""')+'"';}
  return '\ufeff'+[columns.map(cell).join(',')].concat(rows.map(function(row){return columns.map(function(key){return cell(row[key]);}).join(',');})).join('\r\n')+'\r\n';
}
function analyticsExportRows(kind,status,transitions){
  if(kind==='ranking')return (status.profiles||[]).map(function(p){return {server:p.id,name:p.name,protocol:p.protocol,channel:p.channel,
    latency_ms:p.rtt_ms,state:status.rpc_error?'unknown':profileHealth(p,Date.now()/1000).state};});
  if(kind==='traffic')return Object.keys((status.accounting||{}).months||{}).sort().map(function(month){var r=status.accounting.months[month];return {month:month,rx_bytes:r.rx,tx_bytes:r.tx,scope:'Observed interface counters; partial collection; overhead included'};});
  var rows=kind==='failures'?transitions.filter(function(r){return ['rolled_back','held'].indexOf(r.outcome)>=0;}):transitions;
  return rows.map(function(r){return {start_utc:new Date(r.start*1000).toISOString(),source:r.source,target:r.target,kind:r.kind,
    outcome:r.outcome,duration_seconds:r.duration,trial:r.trial,codes:r.codes.join(' | '),attempt_id:r.id,retry_episode_id:r.retry_episode_id,
    source_streak_met:r.probe_evidence.source_streak_met,reserve_streak_met:r.probe_evidence.reserve_streak_met,
    required_failures:r.probe_evidence.required_failures,required_successes:r.probe_evidence.required_successes};});
}
var recoveryAnalyticsPeriod='day';
try {var savedRecoveryPeriod=localStorage.getItem('homensai-vpn-recovery-period');if(['day','week','month'].indexOf(savedRecoveryPeriod)>=0)recoveryAnalyticsPeriod=savedRecoveryPeriod;}catch(error){}
function renderTransitionAnalytics(status){
  var history=status.native_history||{},rows=retainedTransitions(history),now=Date.now()/1000;
  var summaryHost=E('div'),groupHost=E('div'),period=E('select',{'aria-label':bi('Recovery period','Период восстановления')},[
    E('option',{'value':'day'},bi('Day','Сутки')),E('option',{'value':'week'},bi('Week','Неделя')),E('option',{'value':'month'},bi('Month','Месяц'))]);
  var selectedRows=rows,table;
  period.value=recoveryAnalyticsPeriod;
  function update(){var window;
    try {window=recoveryWindow(period.value||'day',now,history.timezone||'Europe/Berlin');}
    catch(error){summaryHost.textContent='RECOVERY-TIMEZONE-UNKNOWN: metrics unavailable';return;}
    var s=recoverySummary(rows,window.start,window.end);
    selectedRows=rows.filter(function(r){return r.start>=window.start&&r.start<window.end;});
    if(table)table.querySelectorAll('tr[data-recovery-start]').forEach(function(row){var at=Number(row.getAttribute('data-recovery-start'));row.hidden=!(at>=window.start&&at<window.end);});
    summaryHost.textContent=bi('Attempts / known outcomes / pending or unknown: ','Попытки / известный результат / ожидание или неизвестно: ')+s.attempts+' / '+s.known_outcomes+' / '+s.unknown_or_pending+
      ' · '+bi('Trial / automatic attempts: ','Тестовые / автоматические попытки: ')+s.trial_attempts+' / '+s.automatic_attempts+
      ' · '+bi('Verified outcome ratio (including trials): ','Доля подтверждённых результатов (включая тесты): ')+(s.success_ratio==null?'—':(s.success_ratio*100).toFixed(1)+'%')+
      ' · '+bi('Recovery median / P95 / worst (s): ','Восстановление: медиана / P95 / максимум (с): ')+[s.median,s.p95,s.worst].map(function(v){return v==null?'—':v.toFixed(1);}).join(' / ');
    while(groupHost.firstChild)groupHost.removeChild(groupHost.firstChild);
    var groups=recoveryGroups(rows,status.profiles||[],window.start,window.end);
    Object.keys(groups).forEach(function(kind){groupHost.appendChild(E('p',{},kind+': '+groups[kind].map(function(g){var m=g.metrics;return g.name+' · '+(m.committed+m.trials_passed)+'/'+m.known_outcomes+' · P95 '+(m.p95==null?'—':m.p95.toFixed(1))+' s · consecutive failures '+m.max_consecutive_failures;}).join(' | ')));});
  }
  period.addEventListener('change',function(){recoveryAnalyticsPeriod=period.value;try{localStorage.setItem('homensai-vpn-recovery-period',recoveryAnalyticsPeriod);}catch(error){}update();});update();
  var exports=E('div',{'class':'hv-wizard-launch'},Object.keys(exportSchemas).map(function(kind){return E('button',{'type':'button','class':'cbi-button','click':function(){
    var text=analyticsCSV(kind,analyticsExportRows(kind,status,selectedRows)),url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
    var link=document.createElement('a');link.href=url;link.download='homensai-vpn-'+kind+'.csv';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
  }},'CSV · '+kind);}));
  exports.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){downloadIncidentReport(selectedRows);}},bi('Printable incident report','Отчёт об инцидентах для печати')));
  table=E('table',{'class':'table'},[E('tr',{},['UTC','Source','Target','Outcome','Seconds','Codes','Details'].map(function(h){return E('th',{},h);}))]);
  rows.forEach(function(r){var detail=E('button',{'type':'button','class':'cbi-button','click':function(){showIncident(r);}},bi('Details','Подробности'));table.appendChild(E('tr',{'data-recovery-start':String(r.start)},[new Date(r.start*1000).toISOString(),r.source,r.target,r.outcome,
    r.duration==null?'—':String(r.duration),'Attempt #'+r.id+' / retry episode #'+(r.retry_episode_id||'unknown')+' · '+r.codes.join(' · ')+' · '+JSON.stringify(r.probe_evidence)+' · '+r.phases.map(function(p){return p.state+' @ '+new Date(p.time*1000).toISOString();}).join(' → ')].map(function(v){return E('td',{},v);}).concat([E('td',{},detail)])));
  });
  update();
  var stamps=(history.events||[]).map(function(e){return e.time;}).filter(function(at){return Number.isFinite(at)&&at>=0&&at<=253402300799;});
  var latest=stamps.length?Math.max.apply(null,stamps):null;
  var age=latest==null?'No retained event timestamp':latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' s since latest retained event';
  return E('section',{'class':'hv-chart-card'},[E('h2',{},bi('Transition evidence and recovery','Подтверждения переходов и восстановления')),
    E('p',{},bi('Retained controller events only. Missing sequences produce unknown outcomes. Probe/client details absent from this history remain unknown.','Только сохранённые события контроллера. Пропуски номеров дают неизвестный результат. Отсутствующие проверки сервера и клиента остаются неизвестными.')),
    E('p',{},bi('Coverage: incomplete retained window; not measured LAN availability.','Покрытие: неполное сохранённое окно; это не измерение доступности LAN.')),
    E('p',{},age),
    E('small',{},'Calendar boundaries: '+(history.timezone||'Europe/Berlin')+'. Event timestamps: UTC. Durations measure retained APPLYING → controller-confirmed outcome events, not full outage duration. Retry episode IDs describe controller evidence, not certified LAN outages. Categories overlap and must not be summed.'),
    period,summaryHost,groupHost,exports,table]);
}

function renderDecisionExplanation(status){
  var explanation=status.decision_explanation||{},diagnosis=explanation.diagnosis||{},native=status.native_failover||{};
  var codeNames={'OBSERVATION-UNKNOWN':bi('Insufficient observations','Недостаточно измерений'),'OBSERVATION-STALE':bi('Observations are stale','Измерения устарели'),'UPLINK-LINK-DOWN':bi('Configured uplink is down; VPN cycling is paused','Настроенный uplink отключён; перебор VPN приостановлен'),'TUNNEL-DISCONNECTED':bi('Tunnel disconnected','Туннель отключён'),'ROUTE-MISMATCH':bi('Route mismatch','Маршрут не соответствует VPN'),'PATH-UNVERIFIED':bi('Probe path unverified','Путь проверки не подтверждён'),'DNS-FAILED':bi('DNS failed','Отказ DNS'),'HTTPS-FAILED':bi('HTTPS failed','Отказ HTTPS'),'VPN-PROBE-HEALTHY':bi('VPN DNS/HTTPS checks passed','Проверки DNS/HTTPS через VPN успешны')};
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&Date.now()/1000-status.time>=0&&Date.now()/1000-status.time<=90;
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Why the controller acts','Почему контроллер принимает решение')),E('p',{},fresh?(codeNames[diagnosis.code]||bi('No current diagnosis','Нет текущего диагноза')):bi('Current evidence unavailable','Текущие измерения недоступны')),E('p',{},bi('Source failure threshold: ','Порог ошибок основного: ')+(explanation.required_failures||'—')+' · '+bi('Confirmed: ','Подтверждено: ')+(fresh&&explanation.source_failure_streak_met===true?bi('Yes','Да'):bi('No','Нет'))),E('p',{},bi('Reserve success threshold: ','Порог успешных проверок резерва: ')+(explanation.required_successes||'—')+' · '+bi('Confirmed: ','Подтверждено: ')+(fresh&&explanation.reserve_success_streak_met===true?bi('Yes','Да'):bi('No','Нет'))),E('p',{},bi('Order: server → channel → VPN protocol; operator priority within each level.','Порядок: сервер → канал → протокол VPN; внутри уровня — приоритет оператора.')),E('p',{},bi('Controller reason: ','Причина контроллера: ')+(native.reason||native.state||'UNKNOWN')),E('small',{},bi('Router-only probes do not confirm the LAN client path. Native transitions require separate certification.','Проверки с роутера не подтверждают путь LAN-клиента. Нативным переходам требуется отдельное подтверждение.'))]);
}
