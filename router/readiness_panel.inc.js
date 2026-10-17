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
var READINESS_CHECKS={
  'PYTHON-39-MINIMUM':['Python 3.9 or newer (runs the program)','Python 3.9 или новее (запускает программу)'],
  'DEPENDENCY-UBUS':['ubus (talks to the router system)','ubus (связь с системой роутера)'],
  'DEPENDENCY-UCI':['uci (reads and saves settings)','uci (чтение и сохранение настроек)'],
  'DEPENDENCY-LUA':['Lua (settings helper)','Lua (помощник настроек)'],
  'DEPENDENCY-IP':['ip (network tool)','ip (сетевой инструмент)'],
  'RPC-PLUGIN':['Program plugin for the web page','Модуль программы для веб-страницы'],
  'CA-BUNDLE':['Certificates for HTTPS checks','Сертификаты для проверок HTTPS'],
  'CONFIG-STORAGE-FREE':['At least 1 MB free for settings','Не менее 1 МБ свободно для настроек']
};
function readinessCheckRow(c){
  var code=String(c.code),row=Object.prototype.hasOwnProperty.call(READINESS_CHECKS,code)?READINESS_CHECKS[code]:null,state=String(c.state);
  var mark=state==='pass'?'✓':state==='fail'?'✗':'?';
  var word=state==='pass'?bi('OK','Есть'):state==='fail'?bi('Missing','Нет'):bi('Not known','Неизвестно');
  return E('li',{'class':'hv-ready-row hv-ready-'+(state==='pass'?'ok':state==='fail'?'bad':'unknown')},[E('span',{'class':'hv-ready-mark','aria-hidden':'true'},mark),E('span',{},row?bi(row[0],row[1]):code),E('strong',{},word)]);
}
function renderReadiness(status){
  var m=readinessModel(status,Date.now()/1000),b=m.board||{};
  function known(v){return v&&v!=='unknown';}
  var routerLine=m.environmentFresh&&(known(b.model)||known(b.board_name)||known(b.firmware))
    ?[known(b.model)?b.model:bi('model not reported','модель не сообщена'),known(b.board_name)?b.board_name:null,known(b.firmware)?bi('firmware ','прошивка ')+b.firmware:bi('firmware not reported','прошивка не сообщена')].filter(Boolean).join(' · ')
    :bi('Not reported yet. The router sends this information when the monitor is running. Start the monitor in Settings and reload the page.','Пока не получено. Роутер присылает эти сведения, когда работает мониторинг. Запустите мониторинг в «Настройках» и обновите страницу.');
  var pass=m.checks.filter(function(c){return c.state==='pass';}).length;
  return E('section',{'class':'hv-chart-card hv-readiness'},[
    E('h2',{},bi('System readiness','Готовность системы')),
    E('p',{'class':'hv-ready-intro'},bi('Here you see whether this router has everything the program needs, and what is still missing before Auto can be started. This page only reads; it changes nothing.','Здесь видно, есть ли на этом роутере всё, что нужно программе, и чего ещё не хватает, чтобы запустить Auto. Страница только читает и ничего не меняет.')),
    E('h3',{},bi('Your router','Ваш роутер')),
    E('p',{},routerLine),
    E('h3',{},bi('Data from the monitor','Данные от мониторинга')),
    E('p',{},m.fresh?bi('Fresh: the monitor is running and sends data.','Свежие: мониторинг работает и присылает данные.'):bi('No fresh data. Monitoring starts by itself; wait a minute and reload the page.','Свежих данных нет. Мониторинг запускается сам: подождите минуту и обновите страницу.')),
    E('h3',{},bi('Required parts on the router','Нужные части на роутере')+(m.checks.length?' ('+pass+' / '+m.checks.length+')':'')),
    m.checks.length?E('ul',{'class':'hv-readiness-list hv-ready-list'},m.checks.map(readinessCheckRow)):E('p',{},bi('The list appears when the router reports it (the monitor must be running).','Список появится, когда роутер его пришлёт (мониторинг должен работать).')),
    E('h3',{},bi('What Auto still needs','Чего ещё не хватает для Auto')),
    E('ul',{'class':'hv-readiness-list hv-ready-list'},m.blockers.map(function(c){return E('li',{'class':'hv-ready-row'},[E('span',{'class':'hv-ready-mark','aria-hidden':'true'},'→'),E('span',{},autoBlockerText(String(c))),E('small',{'class':'hv-auto-tech'},String(c))]);})),
    E('p',{'class':'hv-ready-note'},bi('A tick here does not give permission to switch. At Start the router checks the current device, the time window, your computer’s confirmation, the safe return and the transaction lease again. The router never restarts by itself to enable Auto.','Галочка здесь не разрешает переключение. При запуске роутер заново проверит текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат и блокировку транзакции. Роутер сам никогда не перезагружается ради включения Auto.'))
  ]);
}
