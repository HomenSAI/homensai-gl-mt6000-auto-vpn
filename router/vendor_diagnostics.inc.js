/* Two levels of recovery: observe configured vendor tunnels; explain the application's
   read-only inter-tunnel planning gate. Labels never establish tunnel identity or cause. */
var VENDOR_COORDINATION_TEXT={
  'CROSS-TUNNEL-READY':['Candidate for verification','Кандидат для проверки'],
  'VENDOR-SAME-TUNNEL':['Within one router tunnel: the application holds its own proposal','Один туннель роутера: приложение удерживает собственное предложение'],
  'VENDOR-SETTLING':['Waiting for the configured identity observation window','Ожидание окна наблюдения за конфигурацией'],
  'VENDOR-IDENTITY-UNKNOWN':['Router tunnel identity is unknown','Идентичность туннеля роутера неизвестна'],
  'OBSERVATION-STALE':['Observations are stale','Наблюдения устарели'],
  'PROFILE-IDENTITY-CHANGED':['Profile binding changed; fresh checks are needed','Привязка профиля изменилась; нужны новые проверки'],
  'UPLINK-LINK-DOWN':['Uplink reports link down; VPN switching is held','Uplink сообщает об отключении; переключение VPN удерживается'],
  'PLAN-CONFIG':['The selected tunnel pair needs review','Выбранную пару туннелей нужно проверить']
};
function vendorTunnelId(value){return typeof value==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.-]{1,64}$/.test(value)?value:null;}
function vendorProfileId(value){return typeof value==='string'&&/^[A-Za-z0-9_.:-]{1,96}$/.test(value)?value:null;}
function vendorLabel(value){return typeof value==='string'&&Array.from(value).length<=64&&value.trim()&&!/[\p{C}\p{Zl}\p{Zp}]/u.test(value)?value:null;}
function vendorProtocol(value){return value==='openvpn'?'OpenVPN':value==='wireguard'?'WireGuard':bi('Unknown protocol','Неизвестный протокол');}
function vendorFresh(stamp,now,age){return typeof stamp==='number'&&Number.isFinite(stamp)&&stamp>=0&&stamp<=now&&now-stamp<=age;}
function vendorDiagnosticsModel(status,inventory,now){
  status=status&&typeof status==='object'?status:{};inventory=inventory&&typeof inventory==='object'?inventory:{};
  var settings=inventory.settings||{},interval=Number(settings.interval),age=Number.isInteger(interval)&&interval>=10&&interval<=300?Math.max(30,interval*3):90;
  var observation=status.vendor_observation,available=!!observation&&observation.version===1&&Array.isArray(observation.groups);
  var fresh=available&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(observation.time,now,age);
  var profiles=Array.isArray(status.profiles)?status.profiles.slice(0,400):[],metadata=Array.isArray(inventory.servers)?inventory.servers.slice(0,400):[],profileMap=Object.create(null),metadataMap=Object.create(null);
  profiles.forEach(function(p){if(p&&vendorProfileId(p.id))profileMap[p.id]=Object.prototype.hasOwnProperty.call(profileMap,p.id)?null:p;});
  metadata.forEach(function(p){if(p&&vendorProfileId(p.profile))metadataMap[p.profile]=Object.prototype.hasOwnProperty.call(metadataMap,p.profile)?null:p;});
  function profileName(id){var row=metadataMap[id],measured=profileMap[id],configured=(Array.isArray(inventory.profiles)?inventory.profiles:[]).filter(function(p){return p&&p.id===id;})[0];return row&&vendorLabel(row.name)||measured&&vendorLabel(measured.name)||measured&&vendorLabel(measured.router_name)||configured&&vendorLabel(configured.name)||id||bi('Unknown','Неизвестно');}
  var groups=[],seen={};
  (available?observation.groups.slice(0,400):[]).forEach(function(raw){
    if(!raw||typeof raw!=='object')return;
    var id=vendorTunnelId(raw.id);if(!id||raw.protocol!==id.split(':')[0])return;
    if(seen[id]){seen[id].state='unknown';seen[id].health='unknown';seen[id].current=null;return;}
    var ids=Array.isArray(raw.profiles)?raw.profiles.slice(0,8).filter(function(v,i,a){return vendorProfileId(v)&&a.indexOf(v)===i;}):[];
    var active=Array.isArray(raw.active_profiles)?raw.active_profiles.slice(0,2).filter(function(v,i,a){return vendorProfileId(v)&&ids.indexOf(v)>=0&&a.indexOf(v)===i;}):[];
    var current=vendorProfileId(raw.current_profile),generation=typeof raw.generation==='string'&&/^[0-9a-f]{32}$/.test(raw.generation)?raw.generation:null;
    var coherent=!!generation&&!!current&&Array.isArray(raw.profiles)&&raw.profiles.length===ids.length&&Array.isArray(raw.active_profiles)&&raw.active_profiles.length===1&&active.length===1&&active[0]===current;
    var stable=fresh&&vendorFresh(raw.time,now,age)&&raw.state==='SETTLED'&&Number.isInteger(raw.stable_samples)&&raw.stable_samples>=2&&raw.stable_samples<=1000000&&coherent;
    var state=!fresh||!vendorFresh(raw.time,now,age)?'unknown':stable?'stable':raw.state==='PENDING'&&coherent&&raw.stable_samples===1?'pending':'unknown';
    var row=profileMap[current],health='unknown';
    // Health belongs only to this exact configured identity, never the previous member.
    var member=stable&&row&&!(metadataMap[current]&&metadataMap[current].enabled===false)&&row.protocol===raw.protocol&&row.interface===id.split(':')[1]&&row.vendor_state==='SETTLED'&&row.vendor_tunnel_id===id&&row.vendor_generation===generation&&vendorFresh(row.time,now,age)&&vendorFresh(raw.changed_at,now,now)&&row.vendor_changed_at===raw.changed_at&&raw.changed_at<=row.time&&raw.changed_at<=raw.time?row:null;
    if(member){
      if(row.code===null&&row.dns_ok===true&&Number.isInteger(row.https_success)&&row.https_success>=2)health='healthy';
      else if(['VPN-001','VPN-003','DNS-001','ROUTE-001'].indexOf(row.code)>=0)health='failed';
    }
    var labels=[];ids.forEach(function(profile){var measured=profileMap[profile],saved=metadataMap[profile],label=vendorLabel(saved&&saved.channel)||vendorLabel(measured&&measured.channel);if(label&&labels.indexOf(label)<0)labels.push(label);});
    var profileGroup=typeof raw.profile_group_id==='string'&&/^(openvpn|wireguard):[0-9]{1,20}$/.test(raw.profile_group_id)&&raw.profile_group_id.split(':')[0]===raw.protocol?raw.profile_group_id:null;
    var group={id:id,protocol:raw.protocol,profileGroup:profileGroup,current:state!=='unknown'&&current&&ids.indexOf(current)>=0?current:null,member:member,name:profileName(current),state:state,health:health,labels:labels,changedAt:vendorFresh(raw.changed_at,now,now)?raw.changed_at:null};seen[id]=group;groups.push(group);
  });
  var rawCoord=(status.failover_plan||{}).coordination,coordination={known:false,code:null,state:'UNKNOWN',source:null,target:null,transition:null,settleUntil:null};
  if(rawCoord&&rawCoord.version===1&&!status.rpc_error&&!status.error&&vendorFresh(status.time,now,age)&&vendorFresh(rawCoord.time,now,age)&&rawCoord.can_apply===false&&rawCoord.vendor_attempts_exhausted===null&&rawCoord.vendor_reason==='UNOBSERVED'&&Object.prototype.hasOwnProperty.call(VENDOR_COORDINATION_TEXT,rawCoord.code)&&['READY','HOLD','UNKNOWN'].indexOf(rawCoord.state)>=0){
    var source=vendorTunnelId(rawCoord.source_tunnel),target=vendorTunnelId(rawCoord.target_tunnel);
    var sourceGroup=groups.filter(function(g){return g.id===source;})[0],targetGroup=groups.filter(function(g){return g.id===target;})[0];
    var transition=source&&target&&(source.split(':')[0]===target.split(':')[0]?'channel':'protocol');
    var ready=rawCoord.code!=='CROSS-TUNNEL-READY'||rawCoord.state==='READY'&&source&&target&&source!==target&&rawCoord.transition===transition&&sourceGroup&&sourceGroup.state==='stable'&&sourceGroup.health!=='unknown'&&targetGroup&&targetGroup.state==='stable'&&targetGroup.health==='healthy';
    if(ready)coordination={known:true,code:rawCoord.code,state:rawCoord.state,source:source,target:target,transition:['channel','protocol'].indexOf(rawCoord.transition)>=0?rawCoord.transition:null,settleUntil:typeof rawCoord.settle_until==='number'&&Number.isFinite(rawCoord.settle_until)&&rawCoord.settle_until>now?rawCoord.settle_until:null};
  }
  var events=[];
  (available&&Array.isArray(observation.events)?observation.events.slice(-50):[]).forEach(function(event){
    if(!event||event.cause!=='UNOBSERVED'||!vendorFresh(event.time,now,now)||!vendorTunnelId(event.tunnel))return;
    if(['VENDOR-PROFILE-CHANGED','VENDOR-BINDING-CHANGED','VENDOR-BINDING-UNKNOWN','VENDOR-FIRST-OBSERVATION'].indexOf(event.code)<0)return;
    var before=vendorProfileId(event.previous_profile),after=vendorProfileId(event.current_profile);
    if(event.code==='VENDOR-PROFILE-CHANGED'&&(!before||!after||before===after))return;
    events.push({time:event.time,tunnel:event.tunnel,before:before,after:after,code:event.code});
  });
  events.sort(function(a,b){return b.time-a.time;});
  return {available:available,fresh:fresh,groups:groups,coordination:coordination,events:events.slice(0,8),source:vendorTunnelId(settings.plan_source_tunnel),target:vendorTunnelId(settings.plan_target_tunnel)};
}
function vendorDisplayMember(status,inventory,role,now,legacyId){
  if(role!=='source'&&role!=='target')return null;
  var settings=(inventory||{}).settings||{},anchor=settings['plan_'+role+'_tunnel'];
  if(anchor!=null&&anchor!==''){
    if(!vendorTunnelId(anchor))return null;
    var group=vendorDiagnosticsModel(status,inventory,now).groups.filter(function(g){return g.id===anchor;})[0];
    return group&&group.state==='stable'&&group.member||null;
  }
  var id=legacyId||settings['plan_'+role],rows=Array.isArray((status||{}).profiles)?status.profiles.filter(function(p){return p&&p.id===id;}):[];
  return rows.length===1?rows[0]:null;
}
function vendorDisplaySelected(status,inventory,now){
  var route=(status||{}).channel_path;
  if(route){if(!(status||{}).rpc_error&&vendorFresh((status||{}).time,now,90)&&vendorFresh(route.time,now,30)&&route.confirmed===true&&(route.active_profile_id===route.source_profile_id||route.active_profile_id===route.target_profile_id))return route.active_profile_id;return null;}
  var native=(status||{}).native_failover||{},role=null;
  if((status||{}).rpc_error||!vendorFresh(native.time,now,30))return null;
  if(['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(native.state)>=0)role='target';
  else if(native.state==='OBSERVING'&&(native.certified===true||native.mode==='continuous-pair'&&native.readiness_verified===true))role='source';
  var row=role?vendorDisplayMember(status,inventory,role,now,native[role]):null;
  return row?row.id:null;
}
function vendorLamp(tone,label){return E('span',{},[E('span',{'class':'hv-check-lamp hv-check-'+({healthy:'green',failed:'red',pending:'yellow'}[tone]||'grey'),'aria-hidden':'true'}),label]);}
function vendorIdentityText(group){return group.state==='stable'?bi('Observed configuration stable','Наблюдаемая конфигурация стабильна'):group.state==='pending'?bi('Configuration observation is settling','Окно наблюдения за конфигурацией ещё не завершено'):bi('Configured identity unknown or stale','Идентичность конфигурации неизвестна или устарела');}
function vendorCoordinationText(model){var row=model.coordination.known?VENDOR_COORDINATION_TEXT[model.coordination.code]:null;return row?bi(row[0],row[1]):bi('Current application planning reason is unknown','Текущая причина решения планировщика неизвестна');}
function vendorDetailsLink(){return E('a',{'href':'#channels','click':function(event){if(typeof goToSection==='function'){event.preventDefault();goToSection('channels','hv-vendor-observation');}}},bi('Router tunnel observations and editable labels','Наблюдения туннелей роутера и редактируемые метки'));}
function renderProbeChecks(profile,now){
  if(!profile||!Array.isArray(profile.probe_checks)||!profile.probe_checks.length||!vendorFresh(profile.time,now,90))return null;
  var n=profile.https_success,headline=Number.isInteger(n)?n>=2?bi('Availability threshold met','Условие доступности выполнено'):n>0?bi('Partial HTTPS availability','Частичная HTTPS-доступность'):bi('HTTPS availability not confirmed','HTTPS-доступность не подтверждена'):bi('No saved HTTPS count','Число HTTPS-ответов не сохранено');
  var names={'ok':['Passed','Прошла'],'http-unsupported':['Check endpoint uses an incompatible HTTP version','Несовместимая версия HTTP у проверочного адреса'],'http-error':['HTTP error from check endpoint','Ошибка HTTP проверочного адреса'],'timeout':['Check endpoint did not respond in time','Проверочный адрес не ответил в срок'],'tls-error':['TLS validation or connection error','Ошибка TLS-проверки или соединения'],'transport-error':['Check request transport error','Сетевая ошибка проверочного запроса'],'invalid-response':['Response did not pass validation','Ответ не прошёл проверку'],'unknown':['Details not recorded','Подробности не сохранены']};
  var rows=profile.probe_checks.slice(0,3).filter(function(r){return r&&['one.one.one.one','dns.google','dns.quad9.net'].indexOf(r.target)>=0&&names[r.result];});
  return E('details',{'class':'hv-probe-details','data-probe-profile':profile.id},[E('summary',{},(profile.name||profile.id)+' · '+headline+(Number.isInteger(n)?' · HTTPS '+n+'/3':'')),E('p',{},profile.dns_ok===true?bi('DNS check passed.','DNS-проверка прошла.'):profile.dns_ok===false?bi('DNS check failed.','DNS-проверка не прошла.'):bi('DNS result not recorded.','Результат DNS не сохранён.')),E('ul',{},rows.map(function(r){return E('li',{},r.target+' · '+bi.apply(null,names[r.result])+(Number.isInteger(r.http_status)?' · HTTP '+r.http_status:''));})),E('p',{},bi('An error at a check endpoint does not by itself prove complete loss of VPN traffic.','Ошибка проверочного адреса сама по себе не доказывает полное отсутствие трафика через VPN.'))]);
}
function renderVendorChannels(status,inventory){
  var m=vendorDiagnosticsModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  function value(label,text){return E('p',{},[E('strong',{},label+': '),String(text)]);}
  function anchor(id){var group=m.groups.filter(function(g){return g.id===id;})[0];return id?(id+' · '+bi('current configured profile: ','текущий наблюдаемый профиль: ')+(group&&group.current||bi('unknown','неизвестно'))):bi('Unknown — no trusted saved binding','Неизвестно — нет доверенной сохранённой привязки');}
  var body=[E('summary',{},bi('Router tunnels and application labels','Туннели роутера и метки приложения')),E('p',{},bi('Tunnel IDs are observed from exact router configuration bindings. Provider profile groups and editable app labels are descriptive metadata, not channel identity.','ID туннелей наблюдаются по точным привязкам конфигурации роутера. Группы профилей провайдера и редактируемые метки приложения — описательные метаданные, а не идентичность канала.')),value(bi('Selected source tunnel','Выбранный основной туннель'),anchor(m.source)),value(bi('Selected reserve tunnel','Выбранный резервный туннель'),anchor(m.target))];
  var probeDetails=(status.profiles||[]).map(function(p){return renderProbeChecks(p,typeof statusNow==='function'?statusNow(status):Date.now()/1000);}).filter(Boolean);if(probeDetails.length)body.push(E('details',{'class':'hv-probe-summary'},[E('summary',{},bi('HTTPS/DNS check details','Подробности проверок HTTPS/DNS'))].concat(probeDetails)));
  if(!m.source||!m.target)body.push(E('p',{},[bi('Choose an active profile for each required tunnel in Settings and save the selection; the bindings will be saved. ','Выберите активный профиль каждого нужного туннеля в настройках и сохраните выбор; привязки будут сохранены. '),E('a',{'href':'#settings'},bi('Open Settings','Открыть настройки'))]));
  if(!m.groups.length)body.push(E('p',{},bi('No verified router tunnel binding is available. Editable labels cannot fill this gap.','Проверенной привязки туннеля роутера пока нет. Редактируемые метки не заменяют эти данные.')));
  m.groups.slice().sort(function(a,b){function rank(g){return g.id===m.source?0:g.id===m.target?1:2;}return rank(a)-rank(b);}).slice(0,32).forEach(function(g){
    var health=g.health==='healthy'?bi('Healthy router HTTPS/DNS probe','Успешная проверка HTTPS/DNS с роутера'):g.health==='failed'?bi('Router probe failed','Проверка с роутера не прошла'):bi('Current profile health unknown','Здоровье текущего профиля неизвестно');
    body.push(E('section',{'data-vendor-tunnel':g.id,'data-vendor-state':g.state,'data-vendor-health':g.health,'style':'border-top:1px solid currentColor;padding-top:8px;margin-top:12px;min-width:0;overflow-wrap:anywhere'},[
      E('h4',{},vendorProtocol(g.protocol)+' · '+g.id),E('p',{},vendorLamp(g.state==='pending'?'pending':'unknown',vendorIdentityText(g))),value(bi('Observed configured profile','Наблюдаемый профиль конфигурации'),g.current?g.name+' · '+g.current:bi('Unknown or ambiguous','Неизвестно или неоднозначно')),value(bi('Provider profile group (metadata only)','Группа профилей провайдера (только метаданные)'),g.profileGroup||bi('Unknown','Неизвестно')),value(bi('App channel labels (editable)','Метки каналов приложения (редактируемые)'),g.labels.join(', ')||bi('No saved label observed','Сохранённая метка не наблюдалась')),E('p',{},vendorLamp(g.health,health)),E('p',{'data-vendor-reason':'unobserved'},bi('Reason for the change was not observed. Whether firmware finished all server attempts: unknown.','Причина смены не наблюдалась. Завершены ли все попытки прошивки: неизвестно.'))]));
  });
  if(m.groups.length>32)body.push(E('p',{},bi('Showing the first 32 observed tunnels.','Показаны первые 32 наблюдаемых туннеля.')));
  body.push(E('p',{'data-app-coordination':m.coordination.code||'UNKNOWN'},[E('strong',{},m.coordination.known?bi('Known app planning reason: ','Известная причина решения планировщика: '):bi('App planning reason: ','Причина решения планировщика: ')),vendorCoordinationText(m)]));
  if(m.coordination.settleUntil)body.push(value(bi('Identity observation window until (Europe/Berlin)','Окно наблюдения за конфигурацией до (Europe/Berlin)'),new Date(m.coordination.settleUntil*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})));
  body.push(E('p',{},bi('Read-only planning; this does not enable Auto, authorize route changes or certify GL-MT3000. Router probes do not establish LAN DNS, HTTPS, exit, IPv6 or Kill Switch acceptance.','Планирование без применения: оно не включает Auto, не разрешает изменения маршрутов и не подтверждает GL-MT3000. Проверки с роутера не подтверждают LAN DNS, HTTPS, выход, IPv6 и Kill Switch.')));
  return E('details',{'class':'hv-chart-card','id':'hv-vendor-observation','data-vendor-diagnostics':'channels','style':'min-width:0;overflow-wrap:anywhere'},body);
}
function renderVendorEvents(status,inventory){
  var m=vendorDiagnosticsModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),names={'VENDOR-PROFILE-CHANGED':bi('Configured profile changed','Наблюдаемая конфигурация профиля изменилась'),'VENDOR-BINDING-CHANGED':bi('Configured tunnel binding changed','Наблюдаемая привязка туннеля изменилась'),'VENDOR-BINDING-UNKNOWN':bi('Configured binding became unknown','Привязка конфигурации стала неизвестной'),'VENDOR-FIRST-OBSERVATION':bi('First configured identity observed','Первое наблюдение конфигурации')};
  var content=m.events.length?E('ol',{},m.events.map(function(event){return E('li',{'data-vendor-event':event.code},[E('strong',{},names[event.code]),E('span',{},' · '+new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})+' · '+event.tunnel),E('p',{},(event.before||'—')+' → '+(event.after||'—')),E('small',{},bi('Reason for the change was not observed.','Причина смены не наблюдалась.'))]);})):E('p',{},bi('No recorded profile identity changes yet. This does not prove that the firmware made no attempts.','Записей о смене конфигурации профиля пока нет. Это не доказывает отсутствие попыток штатной прошивки.'));
  return E('details',{'class':'hv-chart-card','data-vendor-diagnostics':'events','style':'min-width:0;overflow-wrap:anywhere'},[E('summary',{},bi('Recent router configuration observations','Последние наблюдения конфигурации роутера')),!m.fresh?E('p',{},bi('Retained observations only; current router tunnel state is unknown.','Показаны только сохранённые наблюдения; текущее состояние туннеля роутера неизвестно.')):null,content,E('small',{},bi('At most 8 recent observations. Profile identity changes are not proof of automatic failover, its cause, or a verified LAN outcome.','Не более 8 последних наблюдений. Изменение профиля не доказывает автоматическое переключение, его причину или подтверждённый результат в LAN.'))].filter(Boolean));
}
