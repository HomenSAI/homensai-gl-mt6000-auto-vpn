/* Read-only readiness; missing evidence never grants Auto permission. Missing information is shown as "waiting", never as a blank. */
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
  'PYTHON-39-MINIMUM':['Python 3.9 or newer','Python 3.9 или новее','Runs the program','Запускает программу','🐍'],
  'DEPENDENCY-UBUS':['ubus','ubus','Talks to the router system','Связь с системой роутера','⇄'],
  'DEPENDENCY-UCI':['uci','uci','Reads and saves settings','Чтение и сохранение настроек','⚙'],
  'DEPENDENCY-LUA':['Lua','Lua','Settings helper','Помощник настроек','λ'],
  'DEPENDENCY-IP':['ip','ip','Network tool','Сетевой инструмент','⛓'],
  'RPC-PLUGIN':['Program plugin','Модуль программы','Connects this page to the program','Связывает эту страницу с программой','🔌'],
  'CA-BUNDLE':['Certificates','Сертификаты','For HTTPS checks','Для проверок HTTPS','🔒'],
  'CONFIG-STORAGE-FREE':['Writable configuration storage','Записываемое хранилище настроек','Writable filesystem and at least 1 MB free','Доступная запись и не менее 1 МБ свободно','💾']
};
var READINESS_TESTED_FIRMWARE='4.11.0';
// Allowlisted remedies only. Never derive a shell command from RPC/user text.
var READINESS_GUIDES={
  'PYTHON-39-MINIMUM':{packages:'python3',install:'opkg install python3',verify:'python3 --version',en:'Runs the application. Version 3.9 or newer is required; installing an older vendor Python is not a pass.',ru:'Выполняет программу. Нужен Python 3.9 или новее; установка более старой версии из feeds не означает готовность.'},
  'DEPENDENCY-UBUS':{packages:'ubus',install:'opkg install ubus',verify:'ubus call system board',en:'Connects the application to router services. A missing command and a stopped ubus service need different diagnoses.',ru:'Обеспечивает связь со службами роутера. Отсутствующая команда и остановленная служба ubus — разные причины.'},
  'DEPENDENCY-UCI':{packages:'uci',install:'opkg install uci',verify:'command -v uci',en:'Reads and saves router settings. Never delete configuration or reset the router to repair this check.',ru:'Читает и сохраняет настройки. Не удаляйте конфигурацию и не сбрасывайте роутер ради исправления проверки.'},
  'DEPENDENCY-LUA':{packages:'lua lua-cjson libuci-lua',install:'opkg install lua lua-cjson libuci-lua',verify:'lua -e "require(\'cjson\'); require(\'uci\')"',en:'Runs the settings helper. Both the interpreter and its JSON/UCI modules must load.',ru:'Запускает помощник настроек. Должны работать интерпретатор и модули JSON/UCI.'},
  'DEPENDENCY-IP':{packages:'ip-full',install:'opkg install ip-full',verify:'ip -Version',en:'Inspects interfaces and policy routes. Keep the matching vendor package; do not remove networking packages to force a replacement.',ru:'Проверяет интерфейсы и маршруты. Нужен пакет этой прошивки; не удаляйте сетевые компоненты ради принудительной замены.'},
  'RPC-PLUGIN':{packages:'application / rpcd',install:'',verify:'ubus -v list homensai-vpn',en:'Connects this page to the installed application. Check the verified application package and rpcd registration; a Python package alone cannot repair it. Follow the installation prompt for a verified repair, without force flags.',ru:'Связывает страницу с приложением. Проверьте проверенный пакет программы и регистрацию в rpcd: установка Python сама по себе это не исправит. Для восстановления используйте установочный промпт без force-флагов.'},
  'CA-BUNDLE':{packages:'ca-bundle',install:'opkg install ca-bundle',verify:'test -s /etc/ssl/certs/ca-certificates.crt',en:'Supplies trusted certificate authorities for HTTPS. Also check the router clock; never disable TLS verification to make a probe pass.',ru:'Содержит доверенные центры сертификатов HTTPS. Проверьте и часы роутера; не отключайте проверку TLS ради зелёного результата.'},
  'CONFIG-STORAGE-FREE':{packages:'none',install:'',verify:'df -k /etc/config; cat /proc/mounts',en:'Settings need a writable filesystem and at least 1 MiB free; installation preflight separately needs 20 MiB. Read-only storage can have plenty of space but cannot save settings. Diagnose filesystem/recovery first; never automatically remount a production router, delete arbitrary files or reset it.',ru:'Для настроек нужна записываемая файловая система и минимум 1 МиБ; установочный preflight отдельно требует 20 МиБ. Read-only хранилище может иметь много места, но не сохранять настройки. Сначала диагностика файловой системы/восстановления; не перемонтируйте рабочий роутер автоматически, не удаляйте произвольные файлы и не сбрасывайте его.'}
};
function readinessRepairPrompt(code){
  var g=READINESS_GUIDES[code],r=READINESS_CHECKS[code];if(!g||!r)return '';
  return bi('On the specific router I identify, diagnose and repair this failed application check: ','На указанном мной роутере проверь и исправь этот пункт готовности приложения: ')+code+' — '+bi(r[0],r[1])+'.\n'+
    bi('Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.\n','Сначала только чтением: модель/прошивка, штатные feeds, фактическая причина и место. Сохрани проверенную приватную копию. Используй разрешённый доступ; не запрашивай секреты в чат.\n')+
    bi('Purpose: ','Назначение: ')+bi(g.en,g.ru)+'\n'+
    (g.install?bi('After checking compatibility, install only from this firmware\'s original vendor feeds. Example: ','После проверки совместимости устанавливай только из штатных feeds этой прошивки. Пример: ')+g.install+'\n':'')+
    bi('Verify using: ','Проверь командой: ')+g.verify+'\n'+
    bi('Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.\n','Без force, массового обновления, чужих feeds, прошивки, сброса firewall и изменений сети компьютера. Не запускай Auto и не принимай соглашение за меня. Обнови готовность и проверь свежий результат, не только exit установщика. Отчитайся PASS/FAIL/BLOCKED/UNKNOWN и перечисли непроверенное.\n')+
    'https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.'+(locale==='ru'?'ru':'en')+'.md';
}
function renderReadinessHelp(code){
  var g=READINESS_GUIDES[code],r=READINESS_CHECKS[code];
  var prompt=E('textarea',{'readonly':'readonly','rows':'12','style':'width:100%;box-sizing:border-box','aria-label':bi('AI repair prompt','Промпт исправления с ИИ')});prompt.value=readinessRepairPrompt(code);
  var copy=E('button',{'type':'button','class':'cbi-button','click':function(){
    function select(){prompt.focus();prompt.select();}
    if(typeof navigator!=='undefined'&&navigator.clipboard)return navigator.clipboard.writeText(prompt.value).then(function(){copy.textContent=bi('Copied','Скопировано');}).catch(select);
    select();
  }},bi('Copy repair prompt','Скопировать промпт исправления'));
  return E('div',{'data-readiness-help':code},[
    E('h3',{},bi(r[0],r[1])+' · '+code),E('p',{},bi(g.en,g.ru)),
    E('h4',{},bi('Install manually','Установить самостоятельно')),
    E('p',{},bi('Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.','Подключитесь к нужному роутеру, проверьте прошивку/место и сохраните проверенную приватную копию. Используйте только штатные feeds этой прошивки. Выполняйте opkg update лишь для обновления списка пакетов. Не запускайте opkg upgrade и не используйте force.')),
    g.install?E('pre',{'class':'hv-cmd'},g.install):E('p',{},bi('This needs diagnosis/recovery, not an arbitrary additional package.','Здесь нужна диагностика/восстановление, а не произвольный дополнительный пакет.')),
    E('h4',{},bi('Verify the result','Проверить результат')),E('pre',{'class':'hv-cmd'},g.verify),
    E('p',{},bi('Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.','Обновите «Готовность системы» и дождитесь свежих данных. Ошибка или устаревшая проверка остаётся непроверенной даже после успешной команды установки.')),
    E('h4',{},bi('Let ChatGPT/Codex or Claude do it','Поручить ChatGPT/Codex или Claude')),E('p',{},bi('Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.','Нужен агент с терминалом и доступом к роутеру. Промпт относится только к этому пункту и не разрешает другие сетевые изменения.')),copy,prompt
  ].filter(Boolean));
}
function readinessCheckState(state){return state==='pass'?'ok':state==='fail'?'bad':state==='waiting'?'waiting':'unknown';}
function readinessTile(code,state){
  var r=Object.prototype.hasOwnProperty.call(READINESS_CHECKS,code)?READINESS_CHECKS[code]:[code,code,'',' ','•'];
  var st=readinessCheckState(state);
  var word=st==='ok'?bi('OK','Есть'):st==='bad'?bi('Missing','Нет'):st==='waiting'?bi('Waiting…','Ожидается…'):bi('Not known','Неизвестно');
  var mark=st==='ok'?'✓':st==='bad'?'✗':st==='waiting'?'…':'?';
  return E('div',{'class':'hv-rd-tile hv-rd-'+st},[E('span',{'class':'hv-rd-mark','aria-hidden':'true'},mark),E('div',{'class':'hv-rd-tile-text'},[E('strong',{},bi(r[0],r[1])),E('small',{},bi(r[2],r[3])),typeof helpLink==='function'?helpLink('dependency-'+code,bi('Help','Помощь')):null].filter(Boolean)),E('b',{'class':'hv-rd-word'},word)]);
}
function readinessInfo(icon,label,value,waiting){
  return E('div',{'class':'hv-rd-info'+(waiting?' hv-rd-info-waiting':'')},[E('span',{'class':'hv-rd-info-icon','aria-hidden':'true'},icon),E('small',{},label),waiting?E('span',{'class':'hv-rd-skeleton'},bi('waiting for data…','ожидаются данные…')):E('strong',{},value)]);
}
var PREPARATION_CHECKS={
  'PREP-HNAT-CONFIG':['Hardware acceleration stays disabled','Аппаратное ускорение остаётся выключенным'],
  'PREP-WGCLIENT1-AUTOSTART':['WireGuard automatic startup is disabled','Автозапуск WireGuard выключен'],
  'PREP-OVPNCLIENT1-AUTOSTART':['OpenVPN automatic startup is disabled','Автозапуск OpenVPN выключен'],
  'PREP-STOCK-VPN-BOOT':['Stock VPN startup does not compete','Штатный автозапуск VPN не конкурирует'],
  'PREP-SFE-BOOT':['SFE startup is disabled','Автозапуск SFE выключен'],
  'PREP-SFE-AUTOLOAD':['SFE autoload is preserved outside startup','Автозагрузка SFE сохранена вне запуска'],
  'PREP-SFE-RUNTIME':['Software acceleration is not loaded','Программное ускорение не загружено']
};
function preparationModel(status,now){
  var ready=readinessModel(status,now),data=(status&&status.system_readiness||{}).preparation;
  if(!ready.environmentFresh||!data||data.scope!=='persistent-mt3000-preparation')return {state:'unknown',checks:[]};
  var rows=Array.isArray(data.checks)?data.checks:[],seen={},valid=true;
  rows.forEach(function(row){if(!row||!Object.prototype.hasOwnProperty.call(PREPARATION_CHECKS,row.code)||seen[row.code]||['pass','fail','unknown'].indexOf(row.state)<0)valid=false;else seen[row.code]=row.state;});
  if(data.state==='unsupported'&&!rows.length)return {state:'unsupported',checks:[]};
  if(!valid||rows.length!==Object.keys(PREPARATION_CHECKS).length)return {state:'unknown',checks:[]};
  return {state:Object.keys(seen).every(function(code){return seen[code]==='pass';})?'pass':'incomplete',checks:rows};
}
function renderPreparation(status,now){
  var m=preparationModel(status,now);
  var explanation=m.state==='unsupported'?bi('These persistent checks apply to the tested MT3000 setup. This is not a compatibility verdict for another model.','Эти постоянные настройки проверяются для испытанной конфигурации MT3000. Это не заключение о совместимости другой модели.'):
    m.state==='unknown'?bi('Fresh preparation evidence is not available.','Свежие сведения о подготовке отсутствуют.'):
    bi('These settings keep the tested MT3000 preparation across reboot. A passing check does not start a VPN or authorize Auto.','Эти настройки сохраняют проверенную подготовку MT3000 после перезагрузки. Успешная проверка не запускает VPN и не разрешает Auto.');
  var meaning={
    'PREP-HNAT-CONFIG':['Keeps hardware acceleration from bypassing the checked path.','Не даёт аппаратному ускорению обходить проверяемый путь.'],
    'PREP-WGCLIENT1-AUTOSTART':['Auto coordinates the selected WireGuard client startup.','Запуск выбранного WireGuard координирует Auto.'],
    'PREP-OVPNCLIENT1-AUTOSTART':['Auto coordinates the selected OpenVPN client startup.','Запуск выбранного OpenVPN координирует Auto.'],
    'PREP-STOCK-VPN-BOOT':['Avoids two competing VPN startup controllers.','Предотвращает конкуренцию двух механизмов запуска VPN.'],
    'PREP-SFE-BOOT':['Prevents software acceleration restarting at boot.','Не позволяет программному ускорению вернуться при загрузке.'],
    'PREP-SFE-AUTOLOAD':['Keeps original autoload bytes available for deliberate recovery.','Сохраняет исходный файл автозагрузки для осознанного восстановления.'],
    'PREP-SFE-RUNTIME':['Checks loaded software acceleration separately from saved settings.','Проверяет загруженное ускорение отдельно от сохранённых настроек.']
  };
  var rows=m.checks.map(function(row){
    var label=PREPARATION_CHECKS[row.code],detail=meaning[row.code],pass=row.state==='pass';
    return E('tr',{'data-preparation-code':row.code},[
      E('td',{},[E('strong',{},bi(label[0],label[1])),E('small',{'style':'display:block;overflow-wrap:anywhere'},row.code)]),
      E('td',{},[E('span',{'class':'hv-check-lamp hv-check-'+(pass?'green':row.state==='fail'?'red':'grey'),'aria-hidden':'true'}),' '+(pass?bi('Ready','Готово'):row.state==='fail'?bi('Needs preparation','Нужна подготовка'):bi('Not verified','Не проверено'))]),
      E('td',{},bi(detail[0],detail[1])),
      E('td',{},pass?bi('Keep the verified setting.','Сохранить проверенное значение.'):bi('Inspect the actual state and reviewed undo procedure before changing anything.','Проверить фактическое состояние и инструкцию отмены до изменений.')),
      E('td',{},typeof helpLink==='function'?helpLink('router-preparation',bi('Help','Помощь')):bi('See router preparation instructions.','См. инструкцию подготовки роутера.'))]);
  });
  var table=E('div',{'class':'hv-dv-tablewrap','style':'overflow-x:auto'},E('table',{'class':'table hv-preparation-table','data-preparation-table':'1'},[
    E('thead',{},E('tr',{},[bi('Check','Проверка'),bi('State','Состояние'),bi('Meaning','Что означает'),bi('Next action','Что делать'),bi('Help','Помощь')].map(function(label){return E('th',{'scope':'col'},label);}))),E('tbody',{},rows)]));
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Persistent router preparation','Постоянная подготовка роутера')),E('p',{},explanation),table,E('p',{'class':'hv-ready-note'},bi('Review DNS, runtime acceleration, supported firmware and recovery instructions before changing settings. Restoring stock startup or acceleration invalidates native readiness.','Перед изменениями проверьте DNS, текущее ускорение, поддерживаемую прошивку и инструкцию восстановления. Возврат штатного автозапуска или ускорения отменяет готовность к переключению.'))]);
}
function renderReadiness(status,inventory){
  var now=Date.now()/1000,m=readinessModel(status,now),b=m.board||{};
  function known(v){return v&&v!=='unknown';}
  var order=Object.keys(READINESS_CHECKS),byCode={};
  m.checks.forEach(function(c){byCode[String(c.code)]=String(c.state);});
  var waiting=!m.environmentFresh;
  var passCount=order.filter(function(code){return byCode[code]==='pass';}).length;
  var failCount=order.filter(function(code){return byCode[code]==='fail';}).length;
  var auto=autoReadiness(status,inventory||{},now);
  // Ring: share of verified parts. Grey and "…" while the router has not reported anything yet.
  var share=waiting?0:Math.round(100*passCount/order.length);
  var verdictKey=waiting?'waiting':failCount?'bad':passCount===order.length?(auto.ready?'ready':'parts'):'partial';
  var verdict={
    waiting:[bi('Waiting for the router','Ожидаем ответ роутера'),bi('The router has not reported its parts yet. This appears by itself within a minute after monitoring starts; reload the page if it does not.','Роутер ещё не прислал сведения о своих частях. Это появится само в течение минуты после запуска мониторинга; если нет, обновите страницу.')],
    bad:[bi('Something is missing','Чего-то не хватает'),bi('At least one required part is missing on the router (red below). Monitoring may still work, but Auto needs all of them.','На роутере не хватает хотя бы одной нужной части (красным ниже). Мониторинг может работать, но Auto нужны все.')],
    partial:[bi('Almost there','Почти готово'),bi('Some parts are not confirmed yet.','Часть пунктов ещё не подтверждена.')],
    parts:[bi('The router has everything it needs','У роутера есть всё необходимое'),bi('All required parts are present. Auto still needs the steps below.','Все нужные части есть. Для Auto ещё нужны шаги ниже.')],
    ready:[bi('Ready for Auto','Готово к запуску Auto'),bi('Everything is in place. The router will still check it again when you press Start.','Всё на месте. Роутер всё равно проверит ещё раз при нажатии «Старт».')]
  }[verdictKey];
  var ring=E('div',{'class':'hv-rd-ring hv-rd-ring-'+verdictKey,'style':'--share:'+share+'%','role':'img','aria-label':waiting?bi('waiting','ожидается'):passCount+' / '+order.length},[E('div',{'class':'hv-rd-ring-inner'},[E('strong',{},waiting?'…':passCount+'/'+order.length),E('small',{},waiting?bi('waiting','ожидается'):bi('parts ready','частей готово'))])]);
  var hero=E('section',{'class':'hv-chart-card hv-rd-hero'},[ring,E('div',{'class':'hv-rd-hero-text'},[E('h2',{},verdict[0]),E('p',{},verdict[1]),E('p',{'class':'hv-ready-intro'},bi('This page only reads; it changes nothing.','Эта страница только читает и ничего не меняет.'))])]);
  var tested=known(b.firmware)?(String(b.firmware).indexOf(READINESS_TESTED_FIRMWARE)===0||String(b.firmware)===READINESS_TESTED_FIRMWARE):null;
  var router=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Your router','Ваш роутер')),E('div',{'class':'hv-rd-info-grid'},[
    readinessInfo('▣',bi('Model','Модель'),b.model,waiting||!known(b.model)),
    readinessInfo('▦',bi('Board','Плата'),b.board_name,waiting||!known(b.board_name)),
    readinessInfo('⚑',bi('GL.iNet firmware','Прошивка GL.iNet'),b.firmware,waiting||!known(b.firmware)),
    readinessInfo('⚑','OpenWrt',b.openwrt,waiting||!known(b.openwrt))]),
    waiting?E('p',{'class':'hv-ready-intro'},bi('Waiting for router information.','Ожидаются данные роутера.')):null
  ].filter(Boolean));
  var monitor=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Data from the monitor','Данные от мониторинга')),E('div',{'class':'hv-rd-tile hv-rd-'+(m.fresh?'ok':'waiting')},[E('span',{'class':'hv-rd-mark','aria-hidden':'true'},m.fresh?'✓':'…'),E('div',{'class':'hv-rd-tile-text'},[E('strong',{},m.fresh?bi('Fresh data','Свежие данные'):bi('Waiting for data','Ожидаем данные')),E('small',{},m.fresh?bi('The monitor is running and sends data.','Мониторинг работает и присылает данные.'):bi('Monitoring starts by itself; wait a minute and reload the page.','Мониторинг запускается сам; подождите минуту и обновите страницу.'))]),E('b',{'class':'hv-rd-word'},m.fresh?bi('OK','Есть'):bi('Waiting…','Ожидается…'))])]);
  var parts=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Required parts on the router','Нужные части на роутере')+(waiting?'':' ('+passCount+' / '+order.length+')')),
    E('div',{'class':'hv-rd-grid'},order.map(function(code){return readinessTile(code,waiting?'waiting':(byCode[code]||'unknown'));}))]);
  // Auto steps as a stepper; blocker codes open their row in the error table.
  var stepper=E('ol',{'class':'hv-rd-steps'},auto.steps.map(function(step,i){
    var current=auto.next&&auto.next.key===step.key;
    var state=step.done?'done':current?'next':'todo';
    var codes=(step.codes&&step.codes.length&&!step.done)?E('div',{'class':'hv-rd-codes'},step.codes.map(function(code){return E('span',{},[errorCodeLink(code),' · '+autoBlockerText(code)]);})):null;
    return E('li',{'class':'hv-rd-step hv-rd-step-'+state},[E('span',{'class':'hv-rd-step-mark','aria-hidden':'true'},step.done?'✓':current?'→':String(i+1)),E('div',{},[E('strong',{},step.title),step.done?null:E('p',{},step.hint),codes].filter(Boolean))]);
  }));
  var autoCard=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('What Auto still needs','Чего ещё не хватает для Auto')),stepper,
    E('p',{'class':'hv-ready-note'},bi('A tick here does not give permission to switch. At Start the router checks the current device, the time window, your computer’s confirmation, the safe return and the transaction lease again. The router never restarts by itself to enable Auto.','Галочка здесь не разрешает переключение. При запуске роутер заново проверит текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат и блокировку транзакции. Роутер сам никогда не перезагружается ради включения Auto.'))]);
  return E('div',{'class':'hv-rd'},[hero,router,monitor,parts,renderPreparation(status,now),autoCard]);
}

// Top of the System readiness page: what it is, that nothing needs to be pressed, how to read the colours.
function readinessIntro(){
  return E('section',{'class':'hv-chart-card hv-rd-intro'},[
    E('h3',{},bi('Is the system ready? Look for green.','Готова ли система? Ищите зелёный.')),
    E('p',{},bi('This page checks that your router has everything the program needs. It only shows the result: you do not need to press or start anything. When every item below is green, your system is ready to work; Auto itself is turned on later with the button on the Overview.','Эта страница проверяет, что на роутере есть всё, что нужно программе. Она только показывает результат: нажимать и запускать ничего не нужно. Когда все пункты ниже зелёные, ваша система готова к работе; сам Auto включается позже кнопкой на «Обзоре».')),
    E('ul',{'class':'hv-plan-legend'},[
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-green','aria-hidden':'true'}),bi(' Green ✓: this part is there and works.',' Зелёный ✓: эта часть есть и работает.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-grey','aria-hidden':'true'}),bi(' Grey …: the router has not reported yet. Wait a minute; it appears by itself after monitoring starts.',' Серый …: роутер ещё не сообщил. Подождите минуту; после запуска мониторинга это появится само.')]),
      E('li',{},[E('span',{'class':'hv-check-lamp hv-check-red','aria-hidden':'true'}),bi(' Red ✗: something is missing. Press its code to read what to do.',' Красный ✗: чего-то не хватает. Нажмите на его код, чтобы прочитать, что делать.')])])]);
}
