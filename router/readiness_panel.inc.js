/* Read-only readiness; missing evidence never grants Auto permission. */
function readinessModel(status,now){
  var data=status.system_readiness||{},native=status.native_failover||{};
  var fresh=!status.rpc_error&&Number.isFinite(status.time)&&now>=status.time&&now-status.time<=90;
  var environmentFresh=fresh&&Number.isFinite(data.time)&&now>=data.time&&now-data.time<=90;
  var blockers=Array.isArray(native.blockers)?native.blockers.slice(0,32):[];
  if(!environmentFresh)blockers.push('ENVIRONMENT-EVIDENCE-UNAVAILABLE');
  if(!fresh)blockers.push('MONITOR-EVIDENCE-STALE');
  if(!blockers.length)blockers.push('NATIVE-START-CERTIFICATION-REQUIRED');
  return {fresh:fresh,environmentFresh:environmentFresh,board:environmentFresh?data.board||{}:{},
    checks:environmentFresh&&Array.isArray(data.checks)?data.checks.slice(0,16):[],blockers:blockers,
    auto:(status.auto_control||{}).requested==='on'&&fresh?'requested':'off_or_unknown'};
}
function renderReadiness(status){
  var m=readinessModel(status,Date.now()/1000);
  return E('section',{'class':'hv-chart-card'},[
    E('h2',{},bi('System readiness','Готовность системы')),
    E('p',{},bi('Actual environment: ','Фактическая среда: ')+(m.board.model||'unknown')+' · '+(m.board.board_name||'unknown')+' · '+(m.board.firmware||'unknown')),
    E('p',{},bi('Monitor evidence: ','Измерения монитора: ')+(m.fresh?bi('Fresh','Свежие'):bi('Unavailable or stale','Недоступны или устарели'))),
    E('ul',{'class':'hv-readiness-list'},m.checks.map(function(c){return E('li',{},String(c.code)+' · '+String(c.state));})),
    E('h3',{},bi('Auto activation checks','Проверки включения Auto')),
    E('ul',{'class':'hv-readiness-list'},m.blockers.map(function(c){return E('li',{},String(c));})),
    E('p',{},bi('Dependency checks do not authorize switching. Start validates the current device, bounded deadline, client witness, rollback certificate and transaction lease. No automatic reboot activation.','Проверка зависимостей не разрешает переключение. Запуск проверяет устройство, срок теста, LAN-клиента, сертификат отката и блокировку транзакции. После перезагрузки Auto сам не включается.'))
  ]);
}
