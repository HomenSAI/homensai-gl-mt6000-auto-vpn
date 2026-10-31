/* HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE */
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
    group.servers.push({id:p.id,name:p.name||p.id,state:state,selected:p.id===selected,reason:reason,profile:p});
    if(current&&p.id!==selected&&enabled&&state==='healthy')candidates.push({id:p.id,
      tier:p.protocol!==current.protocol?2:p.channel!==current.channel?1:0,
      priority:Number.isFinite(Number(p.priority))?Number(p.priority):Infinity});
  });
  candidates.sort(function(a,b){return a.tier-b.tier||a.priority-b.priority||String(a.id).localeCompare(String(b.id));});
  groups.forEach(function(g){g.servers.sort(function(a,b){return Number(b.selected)-Number(a.selected);});});
  groups.sort(function(a,b){return Number(b.servers.some(function(s){return s.selected;}))-Number(a.servers.some(function(s){return s.selected;}));});
  return {selected:selected,groups:groups,next:candidates.length?candidates[0].id:null,fresh:fresh};
}
// What each note on a server means, in plain words. These are descriptions, not errors; real error codes are shown as links.
var CASCADE_NOTES={
  'SELECTED-BY-CONTROLLER':['Carries your traffic now.','Сейчас пропускает ваш трафик.'],
  'EDGE-NOT-CERTIFIED':['Works and could take over, but switching to it is not certified on this router yet (the LAN trial has not passed).','Работает и мог бы подхватить трафик, но переключение на него на этом роутере ещё не подтверждено (LAN-тест не пройден).'],
  'DISABLED':['Switched off in Settings, so it is not monitored and will not be used.','Выключен в «Настройках», поэтому не проверяется и использоваться не будет.'],
  'FAILED':['Failed its last check.','Не прошёл последнюю проверку.'],
  'CHECKING':['Being checked right now.','Проверяется прямо сейчас.'],
  'INACTIVE':['The VPN tunnel is not connected in GL.iNet.','VPN-туннель не подключён в GL.iNet.'],
  'UNKNOWN':['No fresh result yet.','Свежего результата пока нет.']
};
function renderCascadePath(status,inventory){
  if(typeof renderCompactCascade==='function')return renderCompactCascade(status,inventory);
  var model=cascadePathModel(status,(typeof routerWall==='function'?routerWall():Date.now()/1000));
  var rows=status.profiles||[],nextRow=rows.filter(function(p){return p.id===model.next;})[0];
  var legendKeys=[];
  var groups=model.groups.map(function(g){
    return E('section',{'class':'hv-auto-node hv-cascade-group'},[
      E('div',{'class':'hv-cascade-head'},[E('strong',{},g.protocol),E('span',{},bi('Group: ','Группа: ')+g.channel)]),
      E('ul',{'class':'hv-cascade-list'},g.servers.map(function(s){
        var p=s.profile,h=profileHealth(p,(typeof routerWall==='function'?routerWall():Date.now()/1000));
        var kind=s.state==='healthy'?'green':s.state==='checking'?'yellow':s.state==='failed'?'red':'grey';
        if(legendKeys.indexOf(s.reason)<0)legendKeys.push(s.reason);
        var note=ownGet(CASCADE_NOTES,s.reason)||CASCADE_NOTES.UNKNOWN;
        return E('li',{'class':'hv-cascade-item'+(s.selected?' hv-cascade-selected':'')},[
          E('span',{'class':'hv-check-lamp hv-check-'+kind,'role':'img','aria-label':h.label}),
          E('div',{},[
            E('div',{'class':'hv-cascade-line'},[E('b',{},serverTitle(p)),s.selected?E('span',{'class':'hv-chip-note hv-chip-now'},bi('Carries traffic','Пропускает трафик')):null,s.id===model.next?E('span',{'class':'hv-chip-note hv-chip-next'},bi('Next in line','Следующий в очереди')):null].filter(Boolean)),
            E('div',{'class':'hv-cascade-note'},[bi(note[0],note[1]),(p&&safeCode(p.code))?' ':null,(p&&safeCode(p.code))?errorCodeLink(p.code):null].filter(Boolean))])]);
      }))]);
  });
  return E('section',{'class':'hv-chart-card hv-cascade'},[
    E('h2',{},bi('Which VPN carries your traffic and which one is next','Какой VPN пропускает ваш трафик и какой следующий')),
    E('p',{},bi('If the VPN in use fails, Auto looks for a replacement in this order: first another server of the same group and protocol, then another group, and only then another VPN protocol. There is never an automatic exit straight to the provider (no VPN).','Если используемый VPN откажет, Auto ищет замену в таком порядке: сначала другой сервер той же группы и протокола, потом другая группа и только затем другой протокол VPN. Автоматического выхода напрямую к провайдеру (без VPN) никогда не бывает.')),
    E('p',{'class':'hv-cascade-next'},[E('strong',{},bi('Next in line: ','Следующий в очереди: ')),nextRow?serverTitle(nextRow):bi('nobody yet (no other working VPN)','пока никого (нет другого работающего VPN)'),bi('. This only shows who would be chosen; it does not switch anything.','. Это лишь показывает, кого выберут; ничего не переключается.')]),
    E('div',{'class':'hv-cascade-grid'},groups),
    E('details',{'class':'hv-cascade-legend'},[E('summary',{},bi('What the notes mean','Что означают пометки')),E('ul',{},legendKeys.map(function(k){var n=ownGet(CASCADE_NOTES,k)||CASCADE_NOTES.UNKNOWN;return E('li',{},[E('b',{},bi(n[0],n[1]))]);}).concat([E('li',{},bi('A code such as DNS-001 next to a server is a real error: press it to read what it means and how to fix it.','Код вроде DNS-001 рядом с сервером — настоящая ошибка: нажмите на него, чтобы прочитать, что он значит и как исправить.'))]))])
  ]);
}
function retainedTransitions(history){
  var events=(history.events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}),rows=[],open=null,last=null,lastTime=null;
  function close(outcome,event,reason){if(!open)return;open.outcome=outcome;open.close_reason=reason||null;open.terminal_state=event&&event.state||null;
    if(event&&Number.isFinite(event.time)&&event.time>=open.start){open.end=event.time;open.duration=open.applied_at==null?null:event.time-open.applied_at;}
    rows.push(open);open=null;
  }
  function identifier(value){return Number.isSafeInteger(value)&&value>0?value:null;}
  function begin(e){var transition=savedTransition(e);open={id:identifier(e.attempt_id)||e.sequence,retry_episode_id:identifier(e.retry_episode_id),
    prepared_at:e.state==='ARMED'?e.time:null,applied_at:e.state==='APPLYING'?e.time:null,start:e.time,end:null,duration:null,
    pair_source:e.source||'unknown',pair_target:e.target||'unknown',
    source:transition.present?(transition.from?e[transition.from]:'unknown'):e.source||'unknown',target:transition.present?(transition.to?e[transition.to]:'unknown'):e.target||'unknown',
    source_role:transition.present?transition.from:'source',target_role:transition.present?transition.to:'target',transition_metadata_present:transition.present,
    kind:['server','channel','protocol'].indexOf(e.transition_kind)>=0?e.transition_kind:'unknown',
    trial:e.trial===true,outcome:'pending',phases:[],codes:[],probe_evidence:{}};}
  events.forEach(function(e){
    if(!Number.isFinite(e.time)||e.time<0||e.time>253402300799||!Number.isSafeInteger(e.sequence)||e.sequence<1)return;
    if(last!==null&&e.sequence<=last)return;
    if(lastTime!==null&&e.time<lastTime){close('unknown',null,'clock-order');last=e.sequence;return;}
    lastTime=e.time;
    if(last!==null&&e.sequence!==last+1)close('unknown',null,'missing-events');
    last=e.sequence;
    var transition=savedTransition(e),refused=transition.present&&transition.completed&&transition.outcome==='refused';
    if(transition.present&&(!transition.changed||transition.unchanged||transition.reapply)&&!refused)return;
    var restoration=transition.present&&transition.completed&&transition.outcome==='restored';
    if(restoration&&(!open||identifier(e.attempt_id)&&e.attempt_id!==open.id||e.source&&e.source!==open.pair_source||e.target&&e.target!==open.pair_target)){
      close('unknown',null,'next-operation');begin(e);open.operation='restoration';open.applied_at=null;
    }
    var trialPassed=(e.codes||[]).indexOf('TRIAL-PASSED')>=0;
    var starting=e.state==='APPLYING'||e.state==='ARMED'&&!trialPassed;
    if(starting){
      var same=open&&open.applied_at==null&&(e.state==='APPLYING'||!identifier(e.attempt_id)||identifier(e.attempt_id)===open.id)&&
        (!e.attempt_id||e.attempt_id===open.id)&&(!e.source||e.source===open.pair_source)&&(!e.target||e.target===open.pair_target);
      if(!same){close('unknown',null,'next-attempt');begin(e);}
      else if(e.state==='APPLYING'){open.applied_at=e.time;open.start=e.time;if(['server','channel','protocol'].indexOf(e.transition_kind)>=0)open.kind=e.transition_kind;}
    }
    if(!open)return;
    if(e.trial===true)open.trial=true;
    if((identifier(e.attempt_id)&&e.attempt_id!==open.id)||(e.source&&e.source!==open.pair_source)||(e.target&&e.target!==open.pair_target)){close('unknown',null,'pair-changed');return;}
    open.phases.push({state:e.state,time:e.time});
    (e.codes||[]).forEach(function(code){if(typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)&&open.codes.indexOf(code)<0)open.codes.push(code);});
    var evidence=e.probe_evidence||{};
    ['source_streak_met','reserve_streak_met'].forEach(function(key){if(typeof evidence[key]==='boolean')open.probe_evidence[key]=evidence[key];});
    ['required_failures','required_successes'].forEach(function(key){if(Number.isInteger(evidence[key])&&evidence[key]>=2&&evidence[key]<=10)open.probe_evidence[key]=evidence[key];});
    if(Array.isArray(e.phase_evidence)){
      var phases=e.phase_evidence.filter(function(p){return p&&/^[A-Z0-9_-]{1,96}$/.test(p.phase)&&Number.isFinite(p.time)&&p.time<=e.time;});
      if(phases.length){open.phases=phases.map(function(p){return {state:p.phase,time:p.time};});if(open.phases[open.phases.length-1].state!==e.state)open.phases.push({state:e.state,time:e.time});}
    }
    if(transition.present&&transition.completed){
      if(transition.outcome==='committed'&&transition.to)close('committed',e);
      else if(transition.outcome==='restored'&&transition.to)close(open.operation==='restoration'?'restored':'rolled_back',e);
      else if(transition.outcome==='refused')close('refused',e);
      else close('unknown',e,'metadata-unverified');
    }
    else if(!transition.present&&e.state==='COMMITTED')close('committed',e);
    else if(!transition.present&&trialPassed)close('trial_passed',e);
    else if(!transition.present&&e.state==='ROLLED-BACK')close('rolled_back',e);
    else if(!transition.present&&['BLOCKED','STOPPED','STOPPED-ON-RESERVE','EXPIRED'].indexOf(e.state)>=0)close('held',e);
  });
  close('pending',null);
  return rows;
}

function recoverySummary(rows,start,end){
  var selected=rows.filter(function(r){return r.start>=start&&r.start<end&&r.operation!=='restoration';}),durations=[],known=0,committed=0,trialsPassed=0;
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
function recoveryPreparation(row){return row.operation!=='restoration'&&row.applied_at==null&&(!row.source||row.source==='unknown'||!row.target||row.target==='unknown');}
function recoveryOutcomeText(row){
  if(recoveryPreparation(row))return row.close_reason==='next-attempt'?bi('Preparation ended; a new attempt followed','Подготовка завершена; началась новая попытка'):row.close_reason?bi('Preparation record interrupted','Запись подготовки прервана'):bi('Waiting for the VPN pair and checks','Ожидание пары VPN и проверок');
  if(row.outcome==='committed')return row.transition_metadata_present?bi('Channel selection confirmed','Выбор канала подтверждён'):bi('Switch confirmed','Переключение подтверждено');
  if(row.outcome==='refused')return bi('Request refused; no switch confirmed','Запрос отклонён; переключение не подтверждено');
  if(row.outcome==='restored')return bi('VPN rule restoration confirmed','Восстановление правил VPN подтверждено');
  if(row.outcome==='trial_passed')return bi('Test passed; original channel restored','Тест пройден; исходный канал восстановлен');
  if(row.outcome==='rolled_back')return row.transition_metadata_present?bi('VPN rule restoration confirmed','Восстановление правил VPN подтверждено'):bi('Returned to the original channel','Возврат на исходный канал');
  if(row.outcome==='held')return row.terminal_state==='STOPPED-ON-RESERVE'?bi('Reserve retained after Stop','После остановки оставлен резерв'):row.terminal_state==='BLOCKED'?bi('Switch blocked','Переключение заблокировано'):row.terminal_state==='EXPIRED'?bi('Attempt expired','Срок попытки истёк'):bi('Attempt stopped','Попытка остановлена');
  if(row.outcome==='pending')return bi('Awaiting completion confirmation','Ожидается подтверждение завершения');
  var reasons={'missing-events':['Result not recorded: missing history events','Результат не записан: пропуск событий истории'],'pair-changed':['Record interrupted by a VPN pair change','Запись прервана сменой пары VPN'],'clock-order':['Record interrupted by clock order mismatch','Запись прервана нарушением порядка времени'],'next-attempt':['Completion not recorded before the next attempt','Завершение не записано до следующей попытки']},reason=reasons[row.close_reason];
  return reason?bi(reason[0],reason[1]):bi('Completion absent from saved history','В сохранённой истории нет завершения');
}
function recoveryChannelText(row,key,profiles,inventory){
  var id=row[key];if(!id||id==='unknown')return recoveryPreparation(row)?bi('Pair not selected during preparation','На этапе подготовки пара ещё не выбрана'):bi('Channel profile absent from event','Профиль канала не записан в событии');
  var identity=recoveryIdentity(id,profiles,inventory);
  var channel=recoveryEventRole(row,key)||(identity.channel===bi('Channel not recorded','Канал не записан')?(key==='source'?bi('Original channel','Исходный канал'):bi('Destination channel','Канал назначения')):identity.channel);
  return channel+' · '+identity.server;
}
function recoveryEventRole(row,key){
  if(row.transition_metadata_present){var role=row[key+'_role'];return role==='source'?bi('Primary channel','Основной канал'):role==='target'?bi('Reserve channel','Резервный канал'):null;}
  var valid=function(id){return typeof id==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(id);};
  if(!valid(row.source)||!valid(row.target)||row.source===row.target)return null;
  return key==='source'?bi('Primary channel','Основной канал'):key==='target'?bi('Reserve channel','Резервный канал'):null;
}
function recoveryIdentity(identifier,profiles,inventory){
  profiles=Array.isArray(profiles)?profiles:[];
  var valid=typeof identifier==='string'&&identifier!=='unknown'&&identifier!=='default',p=valid?profiles.find(function(p){return p.id===identifier;}):null;
  var configured=((inventory||{}).profiles||[]);if(!Array.isArray(configured))configured=[];
  if(!p&&valid)p=configured.find(function(p){return p.id===identifier;});p=p||{};
  function meaningful(value){return typeof value==='string'&&value.trim()&&['unknown','default','null','undefined'].indexOf(value.trim().toLowerCase())<0;}
  var protocol=valid&&identifier.indexOf('openvpn:')===0?'openvpn':valid&&identifier.indexOf('wireguard:')===0?'wireguard':p.protocol==='openvpn'||p.protocol==='wireguard'?p.protocol:null;
  var protocolName=protocol==='openvpn'?'OpenVPN':protocol==='wireguard'?'WireGuard':bi('Protocol not recorded','Протокол не записан');
  var name=meaningful(p.router_name)?p.router_name:meaningful(p.name)&&p.name!==identifier?p.name:null;
  var server=name?name+' · '+protocolName+' · '+bi('current profile','текущий профиль'):valid?bi('Archived profile: ','Архивный профиль: ')+identifier+' · '+protocolName:bi('Server not recorded in event','Сервер не записан в событии');
  if(name&&typeof endpointText==='function'){var endpoint=endpointText(p,(typeof routerWall==='function'?routerWall():Date.now()/1000));if(endpoint!==bi('Server address: not observed','Адрес сервера: не получен'))server+=' · '+endpoint;}
  var settings=(inventory||{}).settings||{},role=valid&&identifier===settings.plan_source?bi('Primary channel (current pair)','Основной канал (текущая пара)'):valid&&identifier===settings.plan_target?bi('Reserve channel (current pair)','Резервный канал (текущая пара)'):meaningful(p.channel)?bi('Current group: ','Текущая группа: ')+p.channel:bi('Channel not recorded','Канал не записан');
  return {server:server,channel:role,protocol:protocolName};
}
function recoveryGroups(rows,profiles,start,end,inventory){
  var result={server:{},channel:{},protocol:{}};
  rows.filter(function(row){return row.start>=start&&row.start<end;}).forEach(function(row){var identity=recoveryIdentity(row.target,profiles,inventory);
    var role=recoveryEventRole(row,'target');if(role){identity.server=role+' · '+identity.server;identity.channel=role;identity.protocol=role+' · '+identity.protocol;}
    [['server',identity.server],['channel',identity.channel],['protocol',identity.protocol]].forEach(function(pair){
      var key='group:'+pair[1];if(!result[pair[0]][key])result[pair[0]][key]={name:pair[1],rows:[]};result[pair[0]][key].rows.push(row);
    });
  });
  Object.keys(result).forEach(function(kind){result[kind]=Object.keys(result[kind]).map(function(key){var g=result[kind][key];return {name:g.name,metrics:recoverySummary(g.rows,start,end)};});});
  return result;
}
function recoveryTableWrap(table){return E('div',{'class':'hv-recovery-scroll'},table);}
var exportSchemas={
  ranking:['server','name','protocol','channel','latency_ms','metric','state'],
  traffic:['month','rx_bytes','tx_bytes','scope'],
  failures:['start_utc','source','target','source_role','target_role','outcome','codes','attempt_id','retry_episode_id'],
  transitions:['start_utc','source','target','source_role','target_role','kind','outcome','duration_seconds','trial','attempt_id','retry_episode_id','source_streak_met','reserve_streak_met','required_failures','required_successes']
};
function analyticsCSV(kind,rows){
  var columns=exportSchemas[kind];if(!columns)throw new Error('EXPORT-KIND');
  function cell(value){var text=value==null?'':String(value);
    if(/^[\s\u0000-\u001f\u007f\ufeff\u200b-\u200f\u202a-\u202e\u2060-\u206f]*[=+@-]/.test(text)||/^[\t\r\n]/.test(text))text="'"+text;
    return '"'+text.replace(/"/g,'""')+'"';}
  return '\ufeff'+[columns.map(cell).join(',')].concat(rows.map(function(row){return columns.map(function(key){return cell(row[key]);}).join(',');})).join('\r\n')+'\r\n';
}
function analyticsExportRows(kind,status,transitions){
  if(kind==='ranking')return (status.profiles||[]).map(function(p){return {server:p.id,name:p.name,protocol:p.protocol,channel:p.role==='source'?'primary':p.role==='target'?'reserve':p.channel,
    latency_ms:channelPingModel(p,status,routerWall()).rtt_ms,metric:WEBSITE_METRIC,state:status.rpc_error?'unknown':profileHealth(p,(typeof routerWall==='function'?routerWall():Date.now()/1000)).state};});
  if(kind==='traffic')return Object.keys((status.accounting||{}).months||{}).sort().map(function(month){var r=status.accounting.months[month];return {month:month,rx_bytes:r.rx,tx_bytes:r.tx,scope:'Observed interface counters; partial collection; overhead included'};});
  var rows=kind==='failures'?transitions.filter(function(r){return ['rolled_back','held'].indexOf(r.outcome)>=0;}):transitions;
  return rows.map(function(r){return {start_utc:new Date(r.start*1000).toISOString(),source:r.source,target:r.target,kind:r.kind,
    source_role:recoveryEventRole(r,'source')?(r.transition_metadata_present?(r.source_role==='source'?'primary':'reserve'):'primary'):null,target_role:recoveryEventRole(r,'target')?(r.transition_metadata_present?(r.target_role==='source'?'primary':'reserve'):'reserve'):null,
    outcome:r.outcome,duration_seconds:r.duration,trial:r.trial,codes:r.codes.join(' | '),attempt_id:r.id,retry_episode_id:r.retry_episode_id,
    source_streak_met:r.probe_evidence.source_streak_met,reserve_streak_met:r.probe_evidence.reserve_streak_met,
    required_failures:r.probe_evidence.required_failures,required_successes:r.probe_evidence.required_successes};});
}
var recoveryAnalyticsPeriod='day';
try {var savedRecoveryPeriod=localStorage.getItem('homensai-vpn-recovery-period');if(['day','week','month'].indexOf(savedRecoveryPeriod)>=0)recoveryAnalyticsPeriod=savedRecoveryPeriod;}catch(error){}
function controllerTransitionMarks(events){
  var marks=Object.create(null),committed=Object.create(null),attempted=Object.create(null),returned=Object.create(null);
  (events||[]).slice().sort(function(a,b){return a.sequence-b.sequence;}).forEach(function(event){
    var id=event.attempt_id||event.sequence;
    if(event.trial)return;
    var transition=savedTransition(event);
    if(transition.present){
      if(!transition.to||!transition.changed||transition.unchanged||transition.reapply||transition.outcome==='refused')return;
      var forward=transition.from==='source'?1:transition.from==='target'?2:null,destination=transition.to==='source'?1:2;
      if(transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0){var terminal=id+':'+transition.outcome+':'+transition.to;if(!committed[terminal]){committed[terminal]=true;marks[event.sequence]={from:forward,to:destination,confirmed:true};}}
      else if(!transition.completed&&['APPLYING','RESTORING'].indexOf(event.state)>=0){var pending=id+':'+event.state+':'+transition.to;if(!attempted[pending]){attempted[pending]=true;marks[event.sequence]={from:forward,to:destination,confirmed:false};}}
      return;
    }
    if(event.state==='APPLYING'&&!attempted[id]){attempted[id]=true;marks[event.sequence]={from:1,to:2,confirmed:false};}
    if(event.state==='COMMITTED'&&!committed[id]){committed[id]=true;marks[event.sequence]={from:1,to:2,confirmed:true};}
    if(event.state==='ROLLED-BACK'&&event.original_restored===true&&committed[id]&&!returned[id]){returned[id]=true;marks[event.sequence]={from:2,to:1,confirmed:true};}
  });
  return marks;
}
function renderTransitionBadge(event,marks){
  var mark=marks[event.sequence];if(!mark)return null;
  if(typeof renderChannelBadge==='function')return renderChannelBadge({phase:mark.confirmed?'confirmed':'pending',from:mark.from==null?null:mark.from===1?'source':'target',to:mark.to===1?'source':'target'});
  var label=(mark.confirmed?bi('Confirmed switch: ','Подтверждённый переход: '):bi('Switch attempt: ','Попытка перехода: '))+(mark.from==null?'?':mark.from)+' → '+mark.to;
  return E('span',{'class':'hv-transition-badge'+(mark.confirmed?'':' hv-transition-pending'),'aria-label':label,'title':label},[
    E('span',{'class':'hv-transition-from','aria-hidden':'true'},String(mark.from)),E('span',{'aria-hidden':'true'},'→'),E('span',{'class':'hv-transition-to','aria-hidden':'true'},String(mark.to))]);
}
function storedStatisticsRows(status){
  var history=status.native_history||{},health=(status.accounting||{}).reliability||{};
  var months=Array.from(new Set(Object.keys(history.months||{}).concat(Object.keys(health.months||{})))).sort().reverse();
  function row(period,checks,control){return {period:period,outages:checks.outages,failed_checks:checks.failed_checks,
    attempts:control.attempts,switches:control.committed,automatic:control.automatic_committed,manual:control.manual_committed,returns:control.returns,
    auto_seconds:checks.auto_observed_seconds};}
  return [row(bi('All recorded time','За всё время записи'),health.totals||{},history.totals||{}),
    row(bi('Retained detailed period','Сохранённый подробный период'),health.weekly||{},history.weekly||{})].concat(months.map(function(month){
      return row(month,(health.months||{})[month]||{},(history.months||{})[month]||{});
    }));
}
async function fetchStoredStatistics(kind,call){
  var after=0,until=0,events=[],summary=null,asOf=null,notice=null;
  for(var page=0;page<101;page++){
    var response=await call(kind,after,until);
    if(!response||response.kind!==kind||!Array.isArray(response.events)||response.events.length>100||
       !Number.isSafeInteger(response.until)||response.until<0||typeof response.has_more!=='boolean')throw new Error('STATISTICS-REPLY');
    if(summary===null){summary=response.summary;until=response.until;asOf=response.as_of;}
    if(response.until!==until||!Number.isSafeInteger(response.next_after)||response.next_after<after||response.next_after>until)throw new Error('STATISTICS-CURSOR');
    var previous=after;
    response.events.forEach(function(event){if(!Number.isSafeInteger(event.sequence)||event.sequence<=previous||event.sequence>until)throw new Error('STATISTICS-SEQUENCE');previous=event.sequence;});
    if(response.events.length&&response.next_after!==previous)throw new Error('STATISTICS-CURSOR');
    events=events.concat(response.events);if(response.storage_notice)notice=response.storage_notice;
    if(!response.has_more)return {kind:kind,as_of:asOf,detail_days:7,summary:summary,events:events,storage_notice:notice};
    if(response.next_after<=after)throw new Error('STATISTICS-CURSOR');after=response.next_after;
  }
  throw new Error('STATISTICS-PAGE-LIMIT');
}
function renderStoredStatistics(status){
  var history=status.native_history||{},health=(status.accounting||{}).reliability||{},rows=storedStatisticsRows(status);
  var headings=[bi('Period','Период'),bi('Outages','Эпизоды отказа'),bi('Failed checks','Неудачные проверки'),
    bi('Attempts','Попытки'),bi('Confirmed switches','Подтверждённые переключения'),bi('Automatic','Автоматические'),bi('Manual','Ручные'),bi('Returns since update','Возвраты с обновления'),bi('Auto observed, hours','Наблюдение Auto, часов')];
  var table=E('table',{'class':'table hv-recovery-table hv-recovery-counters'},[E('tr',{},headings.map(function(label){return E('th',{'scope':'col'},label);}))].concat(rows.map(function(row){
    var values=[row.period,row.outages,row.failed_checks,row.attempts,row.switches,row.automatic,row.manual,row.returns,
      Number.isFinite(row.auto_seconds)?(row.auto_seconds/3600).toFixed(2):null];
    return E('tr',{},values.map(function(value){return E('td',{},value==null?'—':String(value));}));
  })));
  var note=E('p'),button=E('button',{'type':'button','class':'cbi-button','click':async function(){
    button.disabled=true;note.textContent=bi('Reading saved weekly detail…','Чтение сохранённых событий недели…');
    try{
      var call=rpc.declare({object:'homensai-vpn',method:'statistics',params:['kind','after','until'],expect:{}});
      var failures=await fetchStoredStatistics('failures',call),controller=await fetchStoredStatistics('controller',call);
      var data={schema:1,failures:failures,controller:controller};
      var url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json;charset=utf-8'}));
      var link=document.createElement('a');link.href=url;link.download='homensai-vpn-week-and-months.json';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
      note.textContent=bi('Saved detail downloaded. Unobserved intervals remain unknown.','Сохранённые события выгружены. Интервалы без наблюдений остаются неизвестными.');
    }catch(error){note.textContent=bi('Statistics could not be read. Try again; counters were not reset.','Не удалось прочитать статистику. Повторите выгрузку; счётчики не сброшены.');}
    finally{button.disabled=false;}
  }},bi('Download weekly detail and monthly summaries (JSON)','Скачать подробности недели и сводки по месяцам (JSON)'));
  return E('section',{'class':'hv-chart-card','data-stats-reset':'auto'},[E('h3',{},bi('Saved outage and switching statistics','Сохранённая статистика сбоев и переключений')),typeof statsWorkNote==='function'?statsWorkNote(status):'',
    E('p',{},bi('Detailed incidents: configured retention of 1–7 days. Monthly and lifetime counters survive detail expiry and service restart. A repeated status of one transaction is counted once. Missing data is shown as —.','Подробные события: выбранный срок хранения 1–7 дней. Месячные и общие счётчики сохраняются после удаления старых подробностей и перезапуска службы. Повторные статусы одной транзакции считаются один раз. Нет данных — прочерк.')),
    E('p',{},bi('Outages are observed failure episodes; several failed probes may belong to one outage. Auto time includes only observed intervals. Old missing events and outage durations are not reconstructed.','Сбой — наблюдаемый эпизод отказа; в нём может быть несколько неудачных проверок. Время Auto включает только наблюдавшиеся интервалы. Утраченные старые события и длительность сбоев не восстанавливаются.')),
    E('p',{},bi('Counter coverage: ','Покрытие счётчиков: ')+(history.counter_accuracy||bi('No saved controller counters','Нет сохранённых счётчиков контроллера'))),
    (health.details_dropped||history.detail_budget_dropped)?E('p',{'role':'status'},bi('Detail storage limit was reached; aggregate counters are retained.','Достигнут предел подробных событий; сводные счётчики сохранены.')):null,
    E('div',{'class':'hv-dv-tablewrap'},[table]),button,note].filter(Boolean));
}
function renderTransitionAnalytics(status,inventory){
  var history=status.native_history||{},allRows=retainedTransitions(history),preparations=allRows.filter(recoveryPreparation),rows=allRows.filter(function(r){return !recoveryPreparation(r);}),now=Date.now()/1000;
  var summaryHost=E('div',{'class':'hv-recovery-scroll'}),groupHost=E('div',{'class':'hv-recovery-scroll'}),period=E('select',{'aria-label':bi('Recovery period','Период восстановления')},[
    E('option',{'value':'day'},bi('Day','Сутки')),E('option',{'value':'week'},bi('Week','Неделя')),E('option',{'value':'month'},bi('Month','Месяц'))]);
  var selectedRows=rows,table;
  period.value=recoveryAnalyticsPeriod;
  function update(){var window;
    try {window=recoveryWindow(period.value||'day',now,history.timezone||'Europe/Berlin');}
    catch(error){summaryHost.textContent='RECOVERY-TIMEZONE-UNKNOWN: metrics unavailable';return;}
    var s=recoverySummary(rows,window.start,window.end);
    selectedRows=rows.filter(function(r){return r.start>=window.start&&r.start<window.end;});
    if(table)table.querySelectorAll('tr[data-recovery-start]').forEach(function(row){var at=Number(row.getAttribute('data-recovery-start'));row.hidden=!(at>=window.start&&at<window.end);});
    var fmt=function(v){return v==null?'—':v.toFixed(1);};
    while(summaryHost.firstChild)summaryHost.removeChild(summaryHost.firstChild);
    summaryHost.appendChild(E('table',{'class':'table hv-recovery-table'},[
      E('tr',{'class':'tr table-titles'},[E('th',{'scope':'col'},bi('Measure','Показатель')),E('th',{'scope':'col'},bi('Value','Значение'))]),
      [[bi('Attempts','Попытки'),s.attempts],
       [bi('Known outcome','Известный результат'),s.known_outcomes],
       [bi('No result','Без итога'),s.unknown_or_pending],
       [bi('Trial attempts','Тестовые попытки'),s.trial_attempts],
       [bi('Automatic attempts','Автоматические попытки'),s.automatic_attempts],
       [bi('Verified outcome ratio (including trials)','Доля подтверждённых результатов (включая тесты)'),s.success_ratio==null?'—':(s.success_ratio*100).toFixed(1)+'%'],
       [bi('Recovery time, median (s)','Время восстановления, медиана (с)'),fmt(s.median)],
       [bi('Recovery time, P95 (s)','Время восстановления, P95 (с)'),fmt(s.p95)],
       [bi('Recovery time, worst (s)','Время восстановления, максимум (с)'),fmt(s.worst)]].map(function(r){return E('tr',{'class':'tr'},[E('td',{'class':'td'},r[0]),E('td',{'class':'td'},String(r[1]))]);})].reduce(function(a,b){return a.concat(b);},[])));
    while(groupHost.firstChild)groupHost.removeChild(groupHost.firstChild);
    var groups=recoveryGroups(rows,status.profiles||[],window.start,window.end,inventory);
    var kindTitle={server:bi('By server','По серверам'),channel:bi('By group (channel)','По группам (каналам)'),protocol:bi('By protocol','По протоколам')};
    Object.keys(groups).forEach(function(kind){
      if(!groups[kind].length)return;
      groupHost.appendChild(E('h4',{},ownGet(kindTitle,kind)||kind));
      groupHost.appendChild(E('table',{'class':'table hv-recovery-table'},[E('tr',{'class':'tr table-titles'},[kind==='server'?bi('VPN server / protocol','VPN-сервер / протокол'):kind==='channel'?bi('Channel','Канал'):bi('Protocol','Протокол'),bi('Successful / known','Удачных / известных'),bi('P95, s','P95, с'),bi('Failures in a row','Сбоев подряд')].map(function(t){return E('th',{'scope':'col'},t);}))].concat(groups[kind].map(function(g){var m=g.metrics;
        return E('tr',{'class':'tr'},[E('td',{'class':'td hv-recovery-identity'},g.name),E('td',{'class':'td'},(m.committed+m.trials_passed)+' / '+m.known_outcomes),E('td',{'class':'td'},m.p95==null?'—':m.p95.toFixed(1)),E('td',{'class':'td'},String(m.max_consecutive_failures))]);}))));
    });
    groupHost.appendChild(E('div',{'class':'hv-recovery-legend'},[E('strong',{},bi('How to read these tables','Как читать эти таблицы')),E('p',{},bi('There is one table per kind of grouping (server, group of servers, protocol). Example row: b · 1 / 1 · 5.0 · 0.','Для каждого вида группировки своя таблица (сервер, группа серверов, протокол). Пример строки: b · 1 / 1 · 5.0 · 0.')),
      E('ul',{},[
        E('li',{},bi('Name (b, Main, openvpn): the server, the group (channel) or the protocol these numbers belong to.','Имя (b, Main, openvpn): сервер, группа (канал) или протокол, к которым относятся цифры.')),
        E('li',{},bi('1/1: successful switches / switches whose result is known. 1/1 = every known switch to it succeeded; 0/1 = the only known switch failed; 1/2 = one of two worked. Pending or unknown results are not counted.','1/1: удачные переключения / переключения с известным результатом. 1/1 — все известные переключения на него удались; 0/1 — единственное известное не удалось; 1/2 — одно из двух удалось. Ожидающие и неизвестные результаты не считаются.')),
        E('li',{},bi('P95 5.0 s: 95 % of recoveries on this server took no longer than 5 seconds (the slowest 5 % are excluded). “—” means no timing yet. Smaller is better.','P95 5.0 с: 95 % восстановлений на этом сервере заняли не больше 5 секунд (самые медленные 5 % не учитываются). «—» — времени ещё нет. Чем меньше, тем лучше.')),
        E('li',{},bi('Consecutive failures: the longest run of failed attempts one after another in the chosen period. 0 = none; 1 = one failure, 2 or more = the server repeatedly failed to take over and deserves attention.','Сбоев подряд: самая длинная серия неудачных попыток подряд за выбранный период. 0 — не было; 1 — одна неудача; 2 и больше — сервер несколько раз подряд не смог принять трафик, на него стоит обратить внимание.'))]),
      E('p',{},bi('Example: “d · 0/1 · P95 8.0 s · consecutive failures: 1” = the only known switch to d failed (took 8 s), so d is a weak reserve for now; “b · 1/1” is a reliable one.','Пример: «d · 0/1 · P95 8.0 с · сбоев подряд: 1» — единственное известное переключение на d не удалось (8 с), значит d пока слабый резерв; «b · 1/1» — надёжный.'))]));
  }
  period.addEventListener('change',function(){recoveryAnalyticsPeriod=period.value;try{localStorage.setItem('homensai-vpn-recovery-period',recoveryAnalyticsPeriod);}catch(error){}update();});update();
  var exports=E('div',{'class':'hv-wizard-launch'},Object.keys(exportSchemas).map(function(kind){return E('button',{'type':'button','class':'cbi-button','click':function(){
    var text=analyticsCSV(kind,analyticsExportRows(kind,status,selectedRows)),url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));
    var link=document.createElement('a');link.href=url;link.download='homensai-vpn-'+kind+'.csv';link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);
  }},'CSV · '+kind);}));
  exports.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){downloadIncidentReport(selectedRows);}},bi('Printable incident report','Отчёт об инцидентах для печати')));
  function stamp(t){return new Date(t*1000).toISOString().replace('T',' ').replace(/\.[0-9]+Z$/,'');}
  table=E('table',{'class':'table hv-recovery-table'},[E('tr',{},[bi('Time (UTC)','Время (UTC)'),'№',bi('Original channel','Исходный канал'),bi('Destination channel','Канал назначения'),bi('Outcome','Итог'),bi('Seconds','Секунд'),bi('Stages','Этапы'),bi('Codes','Коды'),''].map(function(h){return E('th',{'scope':'col'},h);}))]);
  rows.forEach(function(r){
    var detail=E('button',{'type':'button','class':'cbi-button','click':function(){showIncident(r,status,inventory);}},bi('Details','Подробности'));
    var evidence=r.probe_evidence&&typeof r.probe_evidence==='object'&&Object.keys(r.probe_evidence).length?' · '+Object.keys(r.probe_evidence).map(function(k){return k+'='+String(r.probe_evidence[k]);}).join(', '):'';
    table.appendChild(E('tr',{'data-recovery-start':String(r.start)},[stamp(r.start),String(r.id),recoveryChannelText(r,'source',status.profiles||[],inventory),recoveryChannelText(r,'target',status.profiles||[],inventory),recoveryOutcomeText(r),r.duration==null?'—':r.duration.toFixed(1),
      r.phases.map(function(p){return p.state;}).join(' → ')||'—',(r.codes.join(' · ')||'—')+evidence].map(function(v){return E('td',{},v);}).concat([E('td',{},detail)])));
  });
  update();
  var stamps=(history.events||[]).map(function(e){return e.time;}).filter(function(at){return Number.isFinite(at)&&at>=0&&at<=253402300799;});
  var latest=stamps.length?Math.max.apply(null,stamps):null;
  var age=latest==null?'No retained event timestamp':latest>now?'UNKNOWN-FUTURE-TIMESTAMP':Math.floor(now-latest)+' s since latest retained event';
  return E('section',{'class':'hv-chart-card','data-stats-reset':'auto'},[E('h2',{},bi('Transition evidence and recovery','Подтверждения переходов и восстановления')),
    E('p',{},bi('Retained controller events only. Missing sequences produce unknown outcomes. Probe/client details absent from this history remain unknown.','Только сохранённые события контроллера. Пропуски номеров дают неизвестный результат. Отсутствующие проверки сервера и клиента остаются неизвестными.')),
    E('p',{},bi('Not all history for this period was saved.','Сохранена не вся история за этот период.')),
    E('p',{},age),
    E('small',{},'Calendar boundaries: '+(history.timezone||'Europe/Berlin')+'. Event timestamps: UTC. Durations measure retained APPLYING → controller-confirmed outcome events, not full outage duration. Retry episode IDs describe controller evidence, not certified LAN outages. Categories overlap and must not be summed.'),
    renderStoredStatistics(status),period,summaryHost,groupHost,E('p',{'class':'hv-muted'},bi('Names and channel roles marked current refer to today’s saved profiles. Older events without a profile cannot be assigned a server.','Названия и роли с пометкой «текущий» относятся к сохранённым сейчас профилям. Старым событиям без профиля нельзя достоверно назначить сервер.')),exports,recoveryTableWrap(table),preparations.length?E('details',{'class':'hv-recovery-preparations'},[E('summary',{},bi('Preparation before channel selection','Подготовка до выбора каналов')+' ('+preparations.length+')'),E('p',{},bi('No route application was recorded for these entries. They are separate from the switch-attempt table.','Для этих записей не зафиксировано применение маршрута. Они вынесены отдельно от таблицы попыток переключения.')),E('ul',{},preparations.map(function(r){return E('li',{},stamp(r.start)+' · '+recoveryOutcomeText(r)+' · '+r.codes.join(' · '));}))]):null].filter(Boolean));
}

function renderDecisionExplanation(status,inventory){
  status=status||{};inventory=inventory||{};
  var explanation=status.decision_explanation||{},diagnosis=explanation.diagnosis||{},native=status.native_failover||{},settings=inventory.settings||{};
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var interval=Number(settings.interval),age=Number.isInteger(interval)&&interval>=10&&interval<=300?Math.max(30,interval*3):90;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=0&&now-status.time<=age;
  var nativeFresh=fresh&&Number.isFinite(native.time)&&now-native.time>=0&&now-native.time<=30;
  var vendor=typeof vendorDiagnosticsModel==='function'?vendorDiagnosticsModel(status,inventory,now):null;
  // What the router sees on the VPN in use, in plain words, with a lamp colour.
  var seen={
    'VPN-PROBE-HEALTHY':['green','The VPN in use works: the router opened a website and looked up a name through it.','VPN в использовании работает: роутер открыл сайт и нашёл адрес через него.'],
    'DNS-FAILED':['red','The VPN is connected, but name lookup (DNS) through it fails.','VPN подключён, но поиск адресов (DNS) через него не работает.'],
    'HTTPS-FAILED':['red','The VPN is connected, but websites do not open through it.','VPN подключён, но сайты через него не открываются.'],
    'TUNNEL-DISCONNECTED':['red','The VPN tunnel is not connected.','VPN-туннель не подключён.'],
    'ROUTE-MISMATCH':['red','The check did not go through this VPN (the route does not match), so it proves nothing.','Проверка шла не через этот VPN (маршрут не совпал), поэтому она ничего не доказывает.'],
    'PATH-UNVERIFIED':['yellow','The router has not yet confirmed which way its check went.','Роутер ещё не подтвердил, каким путём прошла его проверка.'],
    'UPLINK-LINK-DOWN':['red','The configured uplink reports link down. This does not establish why the router firmware changed a profile.','Настроенный uplink сообщает об отключении. Это не устанавливает причину смены профиля штатной прошивкой.'],
    'OBSERVATION-STALE':['grey','The measurements are too old to decide anything.','Измерения слишком старые, чтобы что-то решать.'],
    'OBSERVATION-UNKNOWN':['grey','There are not enough measurements yet.','Измерений пока недостаточно.']
  };
  var row=ownGet(seen,diagnosis.code)||seen['OBSERVATION-UNKNOWN'];if(!fresh)row=['grey','The router sends no fresh data right now.','Роутер сейчас не присылает свежих данных.'];
  var selectedPath=channelPathSelection(status,now,native.source,native.target);
  if(selectedPath.authoritative){
    var selectedRow=(status.profiles||[]).find(function(profile){return profile.id===selectedPath.selected;}),health=selectedRow?profileHealth(selectedRow,now).state:'unknown';
    row=!selectedPath.selected?['grey','The applied VPN traffic selection is not verified.','Действующий выбор VPN для трафика не подтверждён.']:health==='healthy'?seen['VPN-PROBE-HEALTHY']:health==='inactive'?seen['TUNNEL-DISCONNECTED']:health==='failed'?(selectedRow.code==='DNS-001'?seen['DNS-FAILED']:seen['HTTPS-FAILED']):seen['OBSERVATION-UNKNOWN'];
  }
  var needFail=explanation.required_failures,needGood=explanation.required_successes;
  var failMet=fresh&&explanation.source_failure_streak_met===true,goodMet=fresh&&explanation.reserve_success_streak_met===true;
  function line(kind,title,text){return E('li',{'class':'hv-why-line'},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('div',{},[E('b',{},title),E('p',{},text)])]);}
  var state=native.state;
  var next;
  if(!fresh)next=bi('Current control and measurements are unknown. No switch or automatic return can be predicted from stale data.','Текущее управление и измерения неизвестны. По устаревшим данным нельзя предсказывать переключение или автоматический возврат.');
  else if(selectedPath.authoritative){
    if(!selectedPath.selected)next=bi('The traffic channel is not verified; wait for the router VPN rule check.','Канал трафика не подтверждён; дождитесь проверки действующих правил VPN роутером.')+' ('+(selectedPath.code||'KERNEL-POLICY-UNVERIFIED')+')';
    else next=(selectedPath.selected===(status.channel_path||{}).source_profile_id?bi('The primary channel is selected.','Сейчас выбран основной канал.'):bi('The reserve channel is selected.','Сейчас выбран резервный канал.'))+' '+bi('Applied VPN rules are verified; HTTPS/DNS health and Auto enablement remain separate checks.','Действующие правила VPN проверены; результаты HTTPS/DNS и включение Auto проверяются отдельно.');
  }
  else if((state==='STOPPED-ON-RESERVE'||state==='HELD-ON-RESERVE')&&!nativeFresh)next=bi('The last controller report retained the reserve after Stop, but current controller state is unknown. Review the explicit return control or a new validated trial; no automatic return is confirmed.','Последний отчёт контроллера указывал на сохранение резерва после остановки, но текущее состояние контроллера неизвестно. Проверьте отдельное действие возврата или новый подтверждённый тест; автоматический возврат не подтверждён.');
  else if(state==='STOPPED-ON-RESERVE'||state==='HELD-ON-RESERVE')next=bi('Auto is stopped with the reserve retained. Use the explicit “Return to primary” control, or a new validated trial. Stop does not promise an automatic return.','Auto остановлен с сохранением резерва. Используйте отдельное действие «Вернуться на основной» или новый подтверждённый тест. Остановка не обещает автоматического возврата.');
  else if((status.auto_control||{}).requested==='off'&&['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(state)>=0)next=bi('Stop was requested; recovery confirmation is still required. Review the Auto card and its explicit return control. No automatic return is confirmed.','Запрошена остановка; подтверждение восстановления ещё необходимо. Проверьте блок Auto и отдельное действие возврата. Автоматический возврат не подтверждён.');
  else if(state==='DEGRADED-ON-RESERVE')next=bi('The last report retained the reserve with a recovery issue. Review the Auto card and the explicit return control; no automatic return is confirmed.','Последний отчёт указывает на сохранение резерва с проблемой восстановления. Проверьте блок Auto и отдельное действие возврата; автоматический возврат не подтверждён.');
  else if(state==='COMMITTED'&&!nativeFresh)next=bi('The reserve was reported in use, but controller data is stale. A current route or automatic return is not confirmed.','Ранее сообщалось об использовании резерва, но данные контроллера устарели. Текущий маршрут и автоматический возврат не подтверждены.');
  else if(state==='COMMITTED'&&settings.recovery_return_policy==='hold_reserve')next=bi('The hold-reserve policy keeps a healthy reserve for operator review. Use the explicit return control when appropriate; this policy does not promise automatic return.','Политика сохранения резерва оставляет работающий резерв до решения оператора. При необходимости используйте отдельное действие возврата; эта политика не обещает автоматического возврата.');
  else if(state==='COMMITTED'&&settings.recovery_return_policy==='healthy_primary')next=bi('The healthy-primary policy may consider return only in an enabled, validated trial with fresh primary checks. LAN verification and recovery guards still apply; return is not promised.','Политика здорового основного может рассматривать возврат только во включённом подтверждённом тесте со свежими проверками основного. Проверка LAN и ограничения восстановления остаются обязательными; возврат не обещан.');
  else if(state==='COMMITTED')next=bi('The return policy is unknown. Review Settings and the Auto card; no automatic return is confirmed.','Политика возврата неизвестна. Проверьте настройки и блок Auto; автоматический возврат не подтверждён.');
  else if(failMet&&goodMet)next=bi('The router probe quorum is met: a candidate can be reviewed. These checks do not authorize a route change; router firmware coordination, native capability, Stop state, the bounded trial and LAN verification remain separate gates.','Порог проверок с роутера достигнут: можно рассмотреть кандидата. Эти проверки не разрешают изменение маршрута; координация со штатной прошивкой, нативные возможности, состояние Stop, ограниченный тест и проверка LAN остаются отдельными условиями.');
  else if(failMet)next=bi('Router failures were observed, but reserve health is not yet confirmed. This card does not authorize a route change.','Наблюдались ошибки проверок с роутера, но здоровье резерва ещё не подтверждено. Эта карточка не разрешает изменение маршрута.');
  else next=bi('The retained router checks do not meet the failure threshold. This card does not authorize a route change.','Сохранённые проверки с роутера не достигают порога сбоев. Эта карточка не разрешает изменение маршрута.');
  if(vendor)next+=' '+bi('Why Auto will switch or wait: ','Почему Auto переключит или подождёт: ')+vendorCoordinationText(vendor)+'.';
  var code=native.reason||native.state,techCode=typeof code==='string'&&/^[A-Z0-9_-]{1,96}$/.test(code)?code:null;
  return E('section',{'class':'hv-chart-card hv-why'},[
    E('h3',{},bi('Why Auto will switch or wait','Почему Auto переключит или подождёт')),
    E('p',{},bi('Failure and success thresholds describe router probe evidence. They do not prove firmware attempts are exhausted or authorize Auto. Tunnel identity, coordination, controller policy and independent LAN verification remain separate conditions.','Пороги сбоев и успешных проверок описывают результаты проверок с роутера. Они не доказывают завершение попыток прошивки и не разрешают Auto. Идентичность туннеля, координация, политика контроллера и независимая проверка LAN остаются отдельными условиями.')),
    E('ul',{'class':'hv-why-list'},[
      line(row[0],bi('What the router sees on the VPN in use','Что роутер видит на используемом VPN'),bi(row[1],row[2])),
      line(!fresh?'grey':failMet?'red':'green',bi('Has the VPN in use failed enough times?','Отказал ли используемый VPN достаточное число раз?'),(failMet?bi('Yes.','Да.'):bi('No.','Нет.'))+' '+bi('Auto needs '+(needFail||'—')+' failed checks in a row.','Auto нужно '+(needFail||'—')+' неудачных проверок подряд.')),
      line(!fresh?'grey':goodMet?'green':'yellow',bi('Has the reserve met the router probe threshold?','Достигнут ли порог проверок резерва с роутера?'),(goodMet?bi('Yes.','Да.'):bi('Not yet.','Пока нет.'))+' '+bi('Auto needs '+(needGood||'—')+' good checks in a row.','Auto нужно '+(needGood||'—')+' успешных проверок подряд.'))]),
    E('p',{'class':'hv-why-next'},[E('strong',{},bi('Evidence and next review: ','Данные и дальнейшая проверка: ')),next]),
    E('p',{'class':'hv-why-note'},bi('These checks are made by the router itself, so they show whether the VPN tunnels work, not what your computer sees. A separate LAN helper can verify a real client path; current prepared-MT3000 router-probed IPv4 Auto does not require it.','Эти проверки делает сам роутер, поэтому они показывают, работают ли VPN-туннели, а не то, что видит ваш компьютер. Отдельный LAN-помощник проверяет путь реального клиента; для router-probed IPv4 Auto подготовленного MT3000 он не обязателен.')),
    techCode?E('small',{'class':'hv-why-tech'},[bi('Technical state: ','Техническое состояние: '),errorCodeLink(techCode)]):null
  ].filter(Boolean));
}
