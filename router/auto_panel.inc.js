function autoRequestAcknowledged(result,stop){return !!result&&typeof result==='object'&&result.queued===true&&result.accepted!==false&&(stop||result.accepted===true);}
// Display-only parsing; the controller separately enforces bounded deadlines.
function autoWindowDeadline(intent,settings){
  function positive(raw){
    if(typeof raw==='number')return Number.isFinite(raw)&&raw>0?raw:0;
    if(typeof raw!=='string')return 0;
    raw=raw.trim();if(!raw)return 0;
    if(/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw)){var n=Number(raw);return Number.isFinite(n)&&n>0?n:0;}
    if(!/T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(raw))return 0;
    var parsed=Date.parse(raw)/1000;return Number.isFinite(parsed)&&parsed>0?parsed:0;
  }
  return positive((intent||{}).until)||positive((settings||{}).native_until);
}
function autoControlModel(status,now){
  var ns=status.native_failover||{}, intent=status.auto_control||{};
  var paused=!!status.speed_pause&&status.speed_pause.active===true&&status.speed_pause.auto_paused===true;
  var monitorFresh=Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var fresh=!status.rpc_error&&monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  var on=!paused&&fresh&&((ns.state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true))||ns.state==='COMMITTED');
  var transitioning=fresh&&['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0;
  var off=fresh&&['DISABLED','STOPPED','EXPIRED','ROLLED-BACK'].indexOf(ns.state)>=0;
  var awaiting=fresh&&intent.requested_at>ns.time;
  return {fresh:fresh,on:on,paused:paused,transitioning:transitioning,off:off,awaiting:awaiting,
    stop:on||transitioning||intent.requested==='on'||['DEGRADED-ON-RESERVE','COMMITTED','ARMED','APPLYING','WAIT-CLIENT','RESTORING','STOPPED-ON-RESERVE'].indexOf(ns.state)>=0,
    returned:off&&ns.original_restored===true,
    color:paused?'pending':!fresh?'unknown':awaiting||transitioning?'pending':on?'on':off?'off':'error'};
}
function autoPathModel(status,source,target,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{};
  var neutral={source:'neutral',target:'neutral',direction:'none',moving:false,selected:null};
  if(!model.fresh||model.off||model.awaiting)return neutral;
  if(source&&target&&source.id&&source.id===target.id)return neutral;
  var selected=ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE'?'target':ns.state==='OBSERVING'&&(ns.certified===true||ns.mode==='continuous-pair'&&ns.readiness_verified===true)?'source':null;
  if(!selected&&!model.transitioning)return neutral;
  var destination=model.transitioning?(ns.state==='RESTORING'?'source':'target'):null;
  function color(p,key){
    var state=p?profileHealth(p,now).state:'unknown';
    if(state==='failed')return 'failed';
    if(state==='inactive')return 'inactive';
    if(state==='unknown')return 'neutral';
    if(destination===key)return 'checking';
    if(state==='checking')return 'checking';
    return selected===key?'healthy':'ready';
  }
  return {source:color(source,'source'),target:color(target,'target'),direction:destination?(ns.state==='RESTORING'?'back':'forward'):selected==='target'?'forward':'none',moving:!!destination,selected:selected};
}

function autoNoInternetLink(){
  return E('a',{'href':'#help','click':function(ev){if(typeof openHelpTopic==='function'){ev.preventDefault();openHelpTopic('no-internet');}}},bi('Help: no internet?','Справка: нет интернета?'));
}
var AUTO_BLOCKERS={
  'GUARD-DEVICE-UNVERIFIED':['An enabled VPN interface has no readable live state. Check Network → Interfaces for the selected clients; deleted or disabled profiles are excluded.','Не удалось прочитать рабочее состояние включённого VPN-интерфейса. Проверьте выбранные клиенты в «Сеть → Интерфейсы»; удалённые и отключённые профили исключаются.'],
  'EXISTING-TUNNEL-BINDING-UNVERIFIED':['The two selected VPN clients need distinct, confirmed live interfaces, routing tables and marks. Check the selected pair and current tunnel state.','У двух выбранных VPN-клиентов должны быть разные подтверждённые интерфейсы, таблицы маршрутизации и метки. Проверьте выбранную пару и текущее состояние туннелей.'],
  'MT3000-FIRMWARE-UNVERIFIED':['The actual MT3000 firmware, kernel or architecture does not match the verified profile. Keep monitoring and check the router facts.','Фактическая прошивка, ядро или архитектура MT3000 не совпадает с проверенным профилем. Оставьте мониторинг и проверьте данные роутера.'],
  'MT3000-FIREWALL-UNVERIFIED':['This MT3000 firewall arrangement is not verified. Native switching remains blocked.','Этот вариант firewall MT3000 не проверен. Нативное переключение остаётся заблокировано.'],
  'FW3-INCLUDE-CONTRACT-UNVERIFIED':['The stock FW3 VPN include differs from the verified configuration. Review it before switching.','VPN include штатного FW3 отличается от проверенной конфигурации. Проверьте его перед переключением.'],
  'FW3-RUNTIME-STATE-UNVERIFIED':['The running FW3 state cannot be verified. A connected VPN alone is insufficient.','Не удалось проверить рабочее состояние FW3. Одного подключённого VPN недостаточно.'],
  'FW3-SELECTED-ZONE-UNVERIFIED':['The running firewall does not contain both verified VPN zones.','Рабочий firewall не содержит обе проверенные VPN-зоны.'],
  'VENDOR-WORKER-QUIET-UNVERIFIED':['Completion of the router background work is unconfirmed. New switching stays blocked.','Завершение фоновой работы роутера не подтверждено. Новое переключение заблокировано.'],
  'MONITOR-ONLY-DEPLOYMENT':['This installation is limited to monitoring. Native switching is disabled; monitoring does not certify router firmware coordination or the LAN path.','Эта установка ограничена мониторингом. Нативное переключение выключено; мониторинг не подтверждает координацию с прошивкой роутера и путь LAN.'],
  'MONITOR-ONLY-INVALID':['The deployment mode could not be verified. Native actions remain blocked until the deployment settings are checked.','Не удалось проверить режим установки. Нативные действия остаются заблокированы до проверки параметров установки.'],
  'NATIVE-PROGRESS-UNVERIFIED':['Controller progress records cannot be trusted. New actions are blocked; Stop and recovery from a trusted journal remain available. Review the diagnostics before retrying.','Записям состояния контроллера нельзя доверять. Новые действия заблокированы; остановка и восстановление по доверенному журналу остаются доступны. Перед повтором проверьте диагностику.'],
  'RESERVE-IDENTITY-UNKNOWN':['Current reserve identity could not be matched to comparable observations. Its health and any automatic return remain unconfirmed.','Не удалось сопоставить текущий резерв с подходящими наблюдениями. Его здоровье и автоматический возврат остаются неподтверждёнными.'],
  'OBSERVATION-STALE':['Current tunnel or probe observations are missing or stale. Wait for fresh matching observations; old measurements cannot authorize a change.','Текущие наблюдения туннеля или проверок отсутствуют либо устарели. Дождитесь свежих согласованных данных; старые измерения не разрешают изменение.'],
  'VENDOR-IDENTITY-UNKNOWN':['The router tunnel binding is unknown or ambiguous. Save an active source and reserve in Settings after their exact bindings are observed.','Привязка туннеля роутера неизвестна или неоднозначна. Сохраните активный основной и резервный профили в настройках после наблюдения точных привязок.'],
  'VENDOR-SAME-TUNNEL':['Both profiles belong to one router tunnel. Server selection inside it belongs to the router firmware; this app does not switch that pair.','Оба профиля относятся к одному туннелю роутера. Выбор серверов внутри него относится к штатной прошивке; приложение не переключает такую пару.'],
  'RESERVE-NOT-CONNECTED':['The reserve channel is enabled but not connected. Auto tries to start it by itself (at most every two minutes); the primary keeps working meanwhile. If it stays down, check or replace the reserve server.','Резервный канал включён, но не подключён. Auto сам пытается его запустить (не чаще раза в две минуты); основной канал пока работает. Если резерв не поднимается, проверьте или замените сервер резерва.'],
  'PROFILE-IDENTITY-CHANGED':['The configured profile or tunnel binding changed. Old checks no longer describe the current member; wait for fresh observations and repeat validation.','Профиль или привязка туннеля изменились. Старые проверки больше не описывают текущий сервер; дождитесь свежих наблюдений и повторите проверку.'],
  'VENDOR-SETTLING':['The configured tunnel identity observation window is still pending. This does not establish whether firmware retries have finished.','Окно наблюдения за конфигурацией туннеля ещё не завершено. Это не устанавливает, закончились ли повторные попытки прошивки.'],
  'CONTROL-REVISION-STALE':['Auto controls changed. Refresh the current state before starting again.','Состояние управления Auto изменилось. Обновите данные перед новым запуском.'],
  'START-STATE-UNVERIFIED':['Saved Auto state could not be verified. Stop Auto, review the settings, then try again.','Не удалось проверить сохранённое состояние Auto. Остановите Auto, проверьте настройки и повторите попытку.'],
  'STOP-SUPERSEDED-START':['Stop cancelled this pending Start. Press Start again when ready.','Остановка отменила ожидающий запуск. При необходимости нажмите «Запустить» снова.'],
  'START-CONFIG-CHANGED':['Settings changed while checking. Review them and try Start again.','Настройки изменились во время проверки. Проверьте их и повторите запуск.'],
  "LAN-TRIAL-REQUIRED":["This selected client-confirmed mode requires its matching LAN trial. Prepared continuous router-probed mode does not use this certificate.", "Выбранному клиентскому режиму нужен соответствующий LAN-тест. Подготовленный непрерывный router-probed режим этот сертификат не использует."],
  "BOUNDED-DEADLINE-REQUIRED":["A bounded window is missing/expired for the selected trial. Verify actual recovery and time before a new authorized run.", "Для выбранного теста нет действующего ограниченного окна. До нового разрешённого запуска проверьте фактическое восстановление и время."],
  'SESSION-LOSS-NOT-ACCEPTED':['Confirm in Settings that a short reconnection of calls and sessions is acceptable.','Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим.'],
  'TRANSACTION-IN-PROGRESS':['A switch is already in progress. Wait for it to finish or press Stop.','Переключение уже идёт. Дождитесь окончания или нажмите «Стоп».'],
  "TRIAL-ATTEMPT-LIMIT":["The trial attempt budget is exhausted. Preserve failures and respect the budget/cooldown; never reset a nonce or ledger to bypass it.", "Бюджет попыток теста исчерпан. Сохраните отказы и соблюдайте бюджет/паузу; не сбрасывайте nonce или журнал ради обхода."],
  'UNSUPPORTED-BOARD':['Native switching requires a verified GL-MT6000 or GL-MT3000 firmware profile. Choosing a model does not bypass these checks.','Нативное переключение требует проверенного профиля прошивки GL-MT6000 или GL-MT3000. Выбор модели не отменяет эти проверки.'],
  'UNSUPPORTED-FIRMWARE':['Switching is verified only for GL.iNet firmware 4.11.0.','Переключение проверено только для прошивки GL.iNet 4.11.0.'],
  'FIRMWARE-UNKNOWN':['The router model or firmware could not be read.','Не удалось определить модель или прошивку роутера.'],
  'VENDOR-CODE-CHANGED':['GL.iNet system scripts differ from the audited ones. Switching stays blocked.','Системные скрипты GL.iNet отличаются от проверенных. Переключение заблокировано.'],
  'VENDOR-CODE-UNVERIFIED':['GL.iNet system scripts could not be verified.','Не удалось проверить системные скрипты GL.iNet.'],
  'VENDOR-WORKER-BUSY':['The router is applying its own VPN change right now. Try again in a minute.','Роутер сейчас сам применяет изменение VPN. Повторите через минуту.'],
  'HARDWARE-ACCELERATOR-UNVERIFIED':['Hardware acceleration (HNAT) is not confirmed disabled. It must be off for the LAN check to be trustworthy.','Аппаратное ускорение (HNAT) не подтверждено как выключенное. Для достоверной проверки оно должно быть выключено.'],
  'SOFTWARE-ACCELERATOR-UNVERIFIED':['A software acceleration module is loaded and not confirmed disabled.','Загружен модуль программного ускорения, его отключение не подтверждено.'],
  'FLOW-OFFLOAD-ENABLED':['Firewall flow offloading is on. Turn it off in the router firewall settings.','Включён flow offloading в firewall. Выключите его в настройках firewall роутера.'],
  'IPV6-NOT-EXPLICITLY-DISABLED':['IPv6 must be explicitly turned off on the router (IPv6 leaks are not covered).','IPv6 на роутере должен быть явно выключен (утечки IPv6 не контролируются).'],
  'KILLSWITCH-NOT-ENABLED':['Kill Switch must be on for every active VPN rule.','Kill Switch должен быть включён для каждого активного VPN-правила.'],
  'DIRECT-WAN-FALLBACK':['The router is allowed to bypass the VPN. Disable the direct-internet fallback in GL.iNet VPN settings.','Роутеру разрешён выход мимо VPN. Отключите прямой выход в интернет в настройках VPN GL.iNet.'],
  'VPN-POLICY-DISABLED':['The global VPN policy is off in the router settings.','Глобальная VPN-политика выключена в настройках роутера.'],
  'TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED':['Two or more general (all-traffic) VPN rules are required.','Нужно два или больше общих VPN-правил (для всего трафика).'],
  'GENERIC-RULES-NOT-ADJACENT':['The general VPN rules must follow one another without special rules between them.','Общие VPN-правила должны идти подряд, без специальных правил между ними.'],
  'GENERIC-DUPLICATE-INTERFACE':['Two general rules use the same VPN interface.','Два общих правила используют один и тот же VPN-интерфейс.'],
  'SPECIAL-RULES-MUST-PRECEDE-GENERIC':['Special rules (by device or destination) must be placed before the general rules.','Специальные правила (по устройствам или назначениям) должны стоять до общих.'],
  'SOURCE-RESERVE-NOT-CONFIGURED':['Choose a primary and a different reserve profile in Settings.','Выберите в настройках основной и другой, резервный профиль.'],
  'PROFILE-INACTIVE':['The primary or the reserve tunnel is not connected. Connect both in GL.iNet VPN Dashboard.','Основной или резервный туннель не подключён. Подключите оба в VPN Dashboard GL.iNet.'],
  'PROFILES-NOT-GENERIC-RULES':['The chosen profiles are not general VPN rules in the router policy.','Выбранные профили не являются общими VPN-правилами в политике роутера.'],
  'SAME-INTERFACE':['Primary and reserve use the same interface.','Основной и резервный профили используют один интерфейс.'],
  "POLICY-ORDER-DIRECTION-UNVERIFIED":["Policy-order direction has not been established for this mode. The client-confirmed helper and prepared continuous workflow have different setup evidence.", "Направление политики для этого режима ещё не установлено. У клиентского помощника и подготовленного непрерывного режима разные данные настройки."],
  'LAN-LAYOUT-UNSUPPORTED':['The LAN is not on the standard br-lan bridge.','Локальная сеть не на стандартном мосту br-lan.'],
  'PROFILE-NOT-MONITORED':['Enable monitoring for both chosen profiles in Settings.','Включите наблюдение для обоих выбранных профилей в настройках.'],
  'NFT-GUARD-UNAVAILABLE':['The router firewall tool (nft) is unavailable.','Недоступен инструмент firewall роутера (nft).'],
  'POLICY-READ-FAILED':['The router VPN policy could not be read.','Не удалось прочитать VPN-политику роутера.'],
  'UPLINK-LINK-DOWN':['The internet cable/uplink is down; changing VPN would not help.','Нет связи с интернет-провайдером; смена VPN не поможет.'],
  "LEASE-INTEGRITY-FAILED":["The bounded lease record failed integrity checks. Preserve it and inspect recovery/storage; do not delete it or create another lease as a bypass.", "Запись ограниченного окна не прошла целостность. Сохраните её и проверьте восстановление/хранилище; не удаляйте и не создавайте другое окно как обход."],
  'LEASE-STORAGE-FAILED':['The test window could not be stored on the router.','Не удалось сохранить окно теста на роутере.'],
  'LEGACY-LEASE-RECOVERY':['An old transaction needs recovery; wait or press Stop.','Старая транзакция требует восстановления; подождите или нажмите «Стоп».'],
  'JOURNAL-INTEGRITY-FAILED':['The transaction journal is damaged. Switching is blocked and LAN traffic may be held; see the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций повреждён. Переключение заблокировано, трафик LAN может удерживаться; см. аварийные шаги в router-test-kit/EMERGENCY.md.'],
  'HISTORY-001':['The history file is damaged or the router clock went backwards.','Файл истории повреждён или часы роутера пошли назад.'],
  'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':['The router VPN policy was changed by someone else during a switch; LAN traffic is held. Check the rule order and see router-test-kit/EMERGENCY.md.','Политику VPN роутера изменили во время переключения; трафик LAN удерживается. Проверьте порядок правил, см. router-test-kit/EMERGENCY.md.'],
  'ROLLBACK-UNVERIFIED-GUARD-RETAINED':['The rollback could not be verified; LAN traffic is held. See router-test-kit/EMERGENCY.md.','Откат не удалось подтвердить; трафик LAN удерживается. См. router-test-kit/EMERGENCY.md.'],
  "CLIENT-CONFIRMATION-TIMEOUT":["Required client confirmation did not arrive in time. Recovery was requested; verify whether the original route returned or reserve was retained.", "Нужное подтверждение клиента не пришло вовремя. Восстановление запрошено; проверьте, вернулся ли исходный маршрут или сохранён резерв."],
  'CLIENT-STOP':['Stopped by request.','Остановлено по запросу.'],
  'TARGET-HTTPS-DNS-FAILED':['The reserve did not pass the DNS/HTTPS check.','Резерв не прошёл проверку DNS/HTTPS.'],
  'LAN-BASELINE-NOT-SOURCE':['The LAN computer is not currently using the primary route.','Компьютер в LAN сейчас не использует основной маршрут.'],
  'RESERVE-EXIT-NOT-DISTINCT':['Primary and reserve have the same external IP; the switch could not be proven.','У основного и резервного одинаковый внешний IP; переключение невозможно доказать.'],
  'VENDOR-APPLY-FAILED':['The router failed to apply the change; it was rolled back.','Роутер не смог применить изменение; выполнен откат.'],
  'POLICY-CHANGED-DURING-APPLY':['The policy changed while switching; it was rolled back.','Политика изменилась во время переключения; выполнен откат.'],
  'NATIVE-SYSTEM-001':['Internal controller error. See the Service monitor.','Внутренняя ошибка контроллера. См. «Службу мониторинга».'],
  'TERMS-NOT-ACCEPTED':['The terms of use are not accepted yet. Open this page in LuCI and accept them on the first screen.','Условия использования ещё не приняты. Откройте эту страницу в LuCI и примите их на первом экране.'],
  'RETURN-NOT-APPLICABLE':['There is nothing to return from: Auto is not holding the reserve.','Возвращаться не откуда: Auto не удерживает резерв.'],
  'SOURCE-NOT-HEALTHY':['The primary does not pass its check right now, so the router stays on the reserve. Try again when the primary works.','Основной VPN сейчас не проходит проверку, роутер остаётся на резерве. Повторите, когда основной заработает.'],
  'JOURNAL-UNVERIFIED':['The transaction journal could not be verified. Use the emergency steps in router-test-kit/EMERGENCY.md.','Журнал транзакций не удалось проверить. Используйте аварийные шаги из router-test-kit/EMERGENCY.md.'],
  'EXTERNAL-POLICY-CHANGE':['The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.','Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.'],
  'EXTERNAL-POLICY-CHANGE-RELEASED':['The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.','Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.'],
  'ROLLBACK-UNVERIFIED':['The return to the previous route could not be verified. Traffic is allowed only through VPN tunnels; check the VPN rule order in GL.iNet.','Возврат на прежний маршрут не удалось подтвердить. Трафик разрешён только через VPN-туннели; проверьте порядок правил VPN в GL.iNet.'],
  'ENVIRONMENT-EVIDENCE-UNAVAILABLE':['The router has not yet reported what it is made of (model, firmware, installed tools). Monitoring starts by itself: wait a minute and reload the page.','Роутер ещё не сообщил, из чего он состоит (модель, прошивка, установленные программы). Мониторинг запускается сам: подождите минуту и обновите страницу.'],
  'MONITOR-EVIDENCE-STALE':['There is no fresh data from the monitor. Monitoring starts by itself; wait a minute and reload. If it stays, see Help → “The page is old, empty or says the monitor is not running”.','Нет свежих данных от мониторинга. Запустите его в блок «Мониторинг» на «Обзоре»; без него Auto использовать нельзя.'],
  'NATIVE-START-CERTIFICATION-REQUIRED':['Nothing blocks you here, but the router itself still checks everything again at the moment you press Start (current device, time window, your computer’s confirmation, safe return).','Здесь ничто не мешает, но роутер всё равно перепроверит всё в момент нажатия «Старт» (текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат).'],
  'OPERATOR-RETURN':['Returned to the primary on your request.','Возврат на основной выполнен по вашему запросу.'],
  'PRIMARY-RECOVERED':['The primary recovered and Auto returned to it.','Основной восстановился, Auto вернулся на него.']
};
function autoBlockerText(code){
  var row=Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)?AUTO_BLOCKERS[code]:null;
  var guide=typeof AUTO_REMEDIES!=='undefined'&&AUTO_REMEDIES[autoRemedyKey(code)];
  if(!row&&!/^[A-Z][A-Z0-9-]{1,95}$/.test(String(code)))return bi('Unrecognised controller code; see the Service monitor.','Неизвестный код контроллера; см. «Службу мониторинга».');
  var table=!row&&!guide&&typeof ERROR_ROWS!=='undefined'?ERROR_ROWS.filter(function(r){return r[0]===code;})[0]:null;
  return row?bi(row[0],row[1]):guide?bi(guide.title[0],guide.title[1]):table?bi(table[2],table[3]):bi('Code '+code+': see its row in Events and errors.','Код '+code+': описание в «События и ошибки».');
}
var AUTO_REMEDIES={
  'acceleration':{
    title:['Disable network acceleration','Отключите сетевое ускорение'],path:['GL.iNet → NETWORK → Network Acceleration','GL.iNet → Сеть → Сетевое ускорение (Network Acceleration)'],
    text:['Turn Enable off and click Apply. Selecting Auto, Hardware or Software mode does not disable acceleration. Return here and check readiness again; Auto VPN needs a separate Start. Older firmware calls this menu Hardware Acceleration.','Выключите переключатель Enable («Включить») и нажмите Apply («Применить»). Выбор режима Auto, Hardware или Software не отключает ускорение. Вернитесь сюда и обновите готовность; Auto VPN запускается отдельно. В старых прошивках пункт называется Hardware Acceleration.'],
    route:'/#/netnat',docs:'https://docs.gl-inet.com/router/en/4/interface_guide/network_acceleration/'},
  'offload':{
    title:['Disable firewall flow offloading','Отключите flow offloading в firewall'],path:['LuCI → Network → Firewall → General Settings → Routing/NAT Offloading','LuCI → Сеть → Межсетевой экран → Общие настройки → Routing/NAT Offloading'],
    text:['Clear Software flow offloading and Hardware flow offloading, then Save & Apply. Return here and check readiness again.','Снимите Software flow offloading и Hardware flow offloading, затем нажмите Save & Apply («Сохранить и применить»). Вернитесь сюда и обновите готовность.'],route:'/cgi-bin/luci/admin/network/firewall'},
  'pair':{
    title:['Review the current VPN pair','Проверьте текущую пару VPN'],path:['Advanced menu → Settings → Primary and reserve VPN','Расширенное меню → Настройки → Основной и резервный VPN'],
    text:['The selected channel was removed, rebound or is not supported by this controller. Review the actual tunnel bindings in GL.iNet → VPN → VPN Dashboard, then explicitly save a supported pair here. On the prepared MT3000 mode these are wgclient1 and ovpnclient1; a server catalogue entry is not a second tunnel.','Выбранный канал удалён, перепривязан или не поддерживается этим контроллером. Проверьте привязки в GL.iNet → VPN → VPN Dashboard, затем явно сохраните здесь поддерживаемую пару. Для подготовленного режима MT3000 это wgclient1 и ovpnclient1; запись каталога серверов не является вторым туннелем.'],route:'#settings'},
  'recovery':{
    title:['Settings were changed outside the app','Настройки изменены вне приложения'],path:['Overview → Auto button','Обзор → кнопка Auto'],
    text:['The router settings no longer match the saved Auto session, for example a tunnel was renamed or reordered in the stock page. Auto keeps your changes: when you press Start it archives the old session and adopts the new settings by itself, nothing has to be reconciled by hand. If it refuses again within 15 minutes, the settings are still changing: finish editing and press Start once more.','Настройки роутера отличаются от сохранённой сессии Auto, например в штатной панели переименовали или переставили туннель. Auto сохраняет ваши изменения: при нажатии Start он сам архивирует старую сессию и принимает новые настройки, вручную ничего согласовывать не нужно. Если в течение 15 минут отказ повторяется, настройки ещё меняются: закончите правки и нажмите Start ещё раз.'],route:'#settings'}
};
AUTO_REMEDIES.preparation={title:['Complete router preparation','Завершите подготовку роутера'],path:['System readiness → Persistent router preparation','Готовность системы → Постоянная подготовка роутера'],text:['Open the preparation table, find the failed row and follow its instructions. A failed boot or runtime check remains separate from the hardware acceleration switch.','Откройте таблицу подготовки, найдите непрошедший пункт и выполните его инструкцию. Ошибки автозапуска и работающих модулей проверяются отдельно от переключателя аппаратного ускорения.'],route:'#readiness'};
['wgclient1','ovpnclient1'].forEach(function(name){AUTO_REMEDIES['autostart-'+name]={title:['Review '+name+' startup','Проверьте автозапуск '+name],path:['LuCI → Network → Interfaces → '+name+' → Edit → General Setup','LuCI → Сеть → Интерфейсы → '+name+' → Изменить → Основные настройки'],text:['After stopping Auto and verifying completed recovery, clear Bring up on boot for this interface, then Save & Apply. Auto manages its startup separately. This is a startup check, not a hardware acceleration failure.','После остановки Auto и подтверждённого завершения восстановления снимите Bring up on boot («Поднимать при загрузке») у этого интерфейса, затем Save & Apply («Сохранить и применить»). Auto управляет запуском отдельно. Это проверка автозапуска, а не ошибка аппаратного ускорения.'],route:'/cgi-bin/luci/admin/network/network'};});
AUTO_REMEDIES.stockboot={title:['Disable competing VPN startup','Отключите конкурирующий автозапуск VPN'],path:['LuCI → System → Startup → vpn-client','LuCI → Система → Автозагрузка → vpn-client'],text:['After stopping Auto and verifying completed recovery, use Disable for vpn-client in the startup list. Disable changes startup; Stop is a different action and disconnects the running service. Return here and check preparation again.','После остановки Auto и подтверждённого завершения восстановления нажмите Disable («Отключить») у vpn-client в списке автозапуска. Это отключает запуск при загрузке. Кнопка Stop («Остановить») выполняет другое действие и останавливает работающую службу. Вернитесь сюда и повторите проверку подготовки.'],route:'/cgi-bin/luci/admin/system/startup'};
function autoRemedyKey(code){
  if(code==='PREP-SOURCE-AUTOSTART')return 'sourceboot';
  if(code==='PREP-TARGET-AUTOSTART')return 'targetboot';
  if(code==='PREPARATION-RESTART-REQUIRED')return 'restart';
  if(/^PREPARATION-/.test(code||''))return 'preparation';
  if(code==='PREP-WGCLIENT1-AUTOSTART')return 'autostart-wgclient1';
  if(code==='PREP-OVPNCLIENT1-AUTOSTART')return 'autostart-ovpnclient1';
  if(code==='PREP-STOCK-VPN-BOOT')return 'stockboot';
  if(['HARDWARE-ACCELERATOR-UNVERIFIED','SOFTWARE-ACCELERATOR-UNVERIFIED','PREP-HNAT-CONFIG','PREP-SFE-BOOT','PREP-SFE-AUTOLOAD','PREP-SFE-RUNTIME'].indexOf(code)>=0)return 'acceleration';
  if(code==='FLOW-OFFLOAD-ENABLED')return 'offload';
  if(code==='PAIR-PREPARATION-REQUIRED'||/^PREP-/.test(code||''))return 'preparation';
  if(['SOURCE-RESERVE-NOT-CONFIGURED','VENDOR-IDENTITY-UNKNOWN','PROFILE-IDENTITY-CHANGED','RESERVE-NOT-CONNECTED','EXISTING-TUNNEL-BINDING-UNVERIFIED','PAIR-PROFILES-UNVERIFIED'].indexOf(code)>=0)return 'pair';
  if(/^PAIR-(EXTERNAL-|RECOVERY-REQUIRED|STATE-UNVERIFIED)/.test(code||''))return 'recovery';
  return null;
}
function autoRemedyHref(guide){
  if(guide.route==='/#/netnat'){
    var loc=typeof window!=='undefined'&&window.location;
    return loc&&loc.hostname?(loc.protocol==='https:'?'https:':'http:')+'//'+loc.hostname+guide.route:guide.docs;
  }
  return guide.route;
}
function renderAutoRemedy(code){
  var g=AUTO_REMEDIES[autoRemedyKey(code)];if(!g)return null;
  var nodes=[E('strong',{},bi(g.title[0],g.title[1])),E('p',{},bi(g.path[0],g.path[1])),E('p',{},bi(g.text[0],g.text[1])),E('a',{'href':autoRemedyHref(g),'class':'cbi-button','target':g.route.charAt(0)==='#'?null:'_blank','rel':'noopener noreferrer','click':function(event){if(g.route.charAt(0)==='#'&&typeof minimumNavigate==='function'&&minimumNavigate){event.preventDefault();minimumNavigate(g.route.slice(1));}}},bi('Open settings','Открыть настройки'))];
  if(g.docs)nodes.push(E('p',{},E('a',{'href':g.docs,'target':'_blank','rel':'noopener noreferrer'},bi('GL.iNet instructions','Инструкция GL.iNet'))));
  if(typeof renderPreparationButtons==='function'){var preparationButtons=renderPreparationButtons(code);if(preparationButtons)nodes.splice(1,0,preparationButtons);}
  if(autoRemedyKey(code)==='acceleration')nodes.push(E('p',{},bi('If it is already off but the check still fails, open System readiness → Persistent router preparation for the exact failed check. Saved configuration and loaded runtime acceleration are checked separately.','Если уже выключено, а ошибка остаётся, откройте «Готовность системы → Постоянная подготовка роутера»: там указан конкретный непрошедший пункт. Сохранённые настройки и фактически работающее ускорение проверяются отдельно.')));
  return E('div',{'class':'hv-chart-card hv-auto-remedy','data-auto-remedy':code},nodes);
}
['PAIR-EXTERNAL-POLICY-CHANGE','PAIR-EXTERNAL-NETWORK-CHANGE','PAIR-EXTERNAL-CONFIG-CHANGE','PAIR-RECOVERY-REQUIRED','PAIR-STATE-UNVERIFIED','PAIR-PROFILES-UNVERIFIED','EXISTING-TUNNEL-BINDING-UNVERIFIED','PAIR-PREPARATION-REQUIRED','PREP-HNAT-CONFIG','PREP-WGCLIENT1-AUTOSTART','PREP-OVPNCLIENT1-AUTOSTART','PREP-STOCK-VPN-BOOT','PREP-SFE-BOOT','PREP-SFE-AUTOLOAD','PREP-SFE-RUNTIME'].forEach(function(code){
  if(!Object.prototype.hasOwnProperty.call(AUTO_BLOCKERS,code)){var guide=AUTO_REMEDIES[autoRemedyKey(code)];AUTO_BLOCKERS[code]=guide.title.slice();}
});
AUTO_REMEDIES.restart={title:['Router restart required','Нужна перезагрузка роутера'],path:['LuCI → System → Reboot','LuCI → Система → Перезагрузка'],text:['The boot/acceleration setting is saved and verified. Restart this router deliberately, then wait for fresh preparation checks before a separate Auto Start. The preparation button never reboots the router itself.','Настройка автозапуска/ускорения сохранена и проверена. Отдельно перезагрузите этот роутер, дождитесь новых проверок подготовки и затем явно запустите Auto. Кнопка подготовки сама роутер не перезагружает.'],route:'/cgi-bin/luci/admin/system/reboot'};
AUTO_BLOCKERS['PREPARATION-RESTART-REQUIRED']=AUTO_REMEDIES.restart.title.slice();
AUTO_BLOCKERS['PREPARATION-RECOVERY-REQUIRED']=AUTO_REMEDIES.recovery.title.slice();
['source','target'].forEach(function(role){
 var primary=role==='source',key=primary?'sourceboot':'targetboot';
 AUTO_REMEDIES[key]={title:primary?['Disable primary VPN boot startup','Отключите автозапуск основного VPN']:['Disable reserve VPN boot startup','Отключите автозапуск резервного VPN'],path:['LuCI → Network → Interfaces → selected '+(primary?'primary':'reserve')+' VPN → Edit → General Setup','LuCI → Сеть → Интерфейсы → выбранный '+(primary?'основной':'резервный')+' VPN → Изменить → Основные настройки'],text:['Disable Bring up on boot for the selected client. Auto manages startup separately; the current connection is preserved.','Выключите «Поднимать при загрузке» для выбранного клиента. Auto управляет запуском отдельно; текущее подключение сохраняется.'],route:'/cgi-bin/luci/admin/network/network'};
 AUTO_BLOCKERS['PREP-'+role.toUpperCase()+'-AUTOSTART']=AUTO_REMEDIES[key].title.slice();
});
// What must be true before Start can be accepted, in the order the owner can fix it.
var AUTO_LAN_ONLY=['LAN-TRIAL-REQUIRED','BOUNDED-DEADLINE-REQUIRED','SESSION-LOSS-NOT-ACCEPTED'];
function autoReadiness(status,inventory,now){
  var ns=status.native_failover||{},settings=(inventory&&inventory.settings)||{},rows=status.profiles||[];
  var monitorFresh=!status.rpc_error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var controllerFresh=monitorFresh&&Number.isFinite(ns.time)&&now-ns.time>=-5&&now-ns.time<=30;
  function find(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):find(settings.plan_source),target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):find(settings.plan_target);
  var configured=!!(settings.setup_complete&&source&&target&&source.id!==target.id);
  var bothHealthy=configured&&profileHealth(source,now).state==='healthy'&&profileHealth(target,now).state==='healthy';
  var technical=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  var certified=controllerFresh&&(ns.certified===true||ns.state==='COMMITTED'||ns.state==='DEGRADED-ON-RESERVE');
  var steps=[
    {key:'monitor',done:monitorFresh,
     title:bi('Monitor is running','Мониторинг работает'),
     hint:bi('The router status is missing or stale. Monitoring starts by itself; wait a minute and reload the page.','Статус роутера отсутствует или устарел. Мониторинг запускается сам: подождите минуту и обновите страницу.')},
    {key:'profiles',done:bothHealthy,
     title:bi('Primary and reserve are chosen and healthy','Основной и резервный профили выбраны и работают'),
     hint:!configured?bi('Choose a primary and a different reserve in Settings → All application settings → 3 · Existing VPNs.','Выберите основной и другой, резервный профиль: «Настройки → Все настройки приложения → 3 · Существующие VPN».'):bi('Both tunnels must be connected and pass the DNS/HTTPS check. Connect them in GL.iNet VPN Dashboard.','Оба туннеля должны быть подключены и проходить проверку DNS/HTTPS. Подключите их в VPN Dashboard GL.iNet.')},
    {key:'session',done:settings.native_session_loss===true,
     title:bi('You accepted a brief call drop when switching','Вы согласились на короткий обрыв звонков при переключении'),
     hint:bi('A switch can interrupt calls and downloads for a few seconds. Confirm this in Settings (System setup).','Переключение может на несколько секунд прервать звонки и загрузки. Подтвердите это в «Настройках» (мастер системы).')},
    {key:'router',done:controllerFresh&&technical.length===0,codes:technical,
     title:bi('Router is ready for switching','Роутер готов к переключению'),
     hint:!controllerFresh?bi('The switching controller is not reporting. Check the Live log (Advanced menu).','Контроллер переключения не отвечает. Проверьте «Живой журнал» (меню «Расширенные настройки»).'):bi('The router reports conditions that block switching (listed below).','Роутер сообщает условия, блокирующие переключение (перечислены ниже).')},
    {key:'trial',done:certified,
     title:bi('LAN trial passed for this pair','LAN-тест для этой пары пройден'),
     hint:bi('On a computer connected by cable run the LAN helper: it briefly switches to the reserve and back and proves DNS, HTTPS and the exit IP from the LAN. Only then Start is accepted.','На компьютере, подключённом кабелем, запустите LAN-помощник: он кратко переключит на резерв и обратно и докажет работу DNS, HTTPS и внешнего IP из LAN. Только после этого «Старт» будет принят.')}
  ];
  var next=steps.filter(function(step){return !step.done;})[0]||null;
  return {steps:steps,next:next,ready:!next};
}

// Traffic light: one lamp says what Auto is doing. The round button only starts or stops it.
var AUTO_LIGHTS=[
  {lamp:'green',key:'ok',icon:'✓',legend:['Green: Auto is on and watching the primary','Зелёный: Auto включён и следит за основным']},
  {lamp:'yellow',key:'switching',icon:'⟳',legend:['Yellow: starting, stopping or switching the route','Жёлтый: запускается, останавливается или переключает маршрут']},
  {lamp:'orange',key:'reserve',icon:'⇄',legend:['Orange: the reserve route is selected; primary health is separate','Оранжевый: выбран резерв; исправность основного показана отдельно']},
  {lamp:'red',key:'problem',icon:'!',legend:['Red: needs your attention','Красный: нужно ваше внимание']}
];
function autoLightModel(status,inventory,now){
  var model=autoControlModel(status,now),ns=status.native_failover||{},intent=status.auto_control||{},state=ns.state;
  var blockers=(Array.isArray(ns.blockers)?ns.blockers:[]).filter(function(code){return AUTO_LAN_ONLY.indexOf(code)<0;});
  var sessionRuns=intent.requested==='on'&&['RUNNING','HELD'].indexOf(intent.pair_phase)>=0&&!model.awaiting;
  function out(key,title,hint,code,running){return {running:running===true,key:key,lamp:(AUTO_LIGHTS.filter(function(l){return l.key===key;})[0]||{}).lamp||null,
    icon:key==='off'?'○':key==='unknown'?'?':(AUTO_LIGHTS.filter(function(l){return l.key===key;})[0]||{}).icon,title:title,hint:hint,code:code||null};}
  if(model.paused)return out('switching',bi('Auto paused for speed test','Auto на паузе для теста скорости'),bi('Background checks are paused. They resume before Auto; a manual Stop stays in force.','Фоновые проверки приостановлены. Они возобновятся перед Auto; ручной Stop сохраняет силу.'));
  if(!model.fresh)return out('unknown',bi('No data from the router','Нет данных от роутера'),bi('The status is missing or old. Open Settings and make sure the monitor is running.','Статус отсутствует или устарел. Откройте «Настройки» и проверьте, что мониторинг запущен.'));
  if(ns.proof_scope==='router-probed-ipv4'&&ns.mode==='continuous-pair'){
    var scopeHint='';
    if(model.awaiting)return out('switching',bi('Starting or stopping Auto','Запуск или остановка Auto'),scopeHint);
    if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),scopeHint,null,sessionRuns);
    if(state==='OBSERVING'&&ns.readiness_verified===true)return out('ok',bi('Two-channel Auto is on','Авторежим двух каналов включён'),scopeHint);
    if(state==='COMMITTED')return out('reserve',bi('Working on the reserve','Работаю на резерве'),scopeHint);
    var failedCode=blockers[0]||(intent.failure&&intent.failure.code&&intent.requested!=='on'?intent.failure.code:null);
    if(state==='STOPPED'&&!failedCode)return out('off',bi('Auto is off','Auto выключен'),scopeHint);
    return out('problem',bi('Auto needs attention','Auto требует внимания'),failedCode?autoBlockerText(failedCode):scopeHint,failedCode);
  }
  if(ns.proof_scope==='router-hosted-ipv4')return out('problem',bi('Checked by the router itself','Проверку делает сам роутер'),bi('This trial checks IPv4 forwarding with a client inside the router. It does not certify traffic from a separate LAN computer.','Этот тест проверяет пересылку IPv4 клиентом внутри роутера. Трафик отдельного компьютера LAN им не подтверждён.'));
  if(model.awaiting)return out('switching',intent.requested==='off'?bi('Stopping Auto','Auto останавливается'):bi('Starting Auto','Auto запускается'),bi('Waiting for the router to confirm. The lamp changes when it does.','Ожидается подтверждение роутера. Лампа изменится, когда оно придёт.'));
  if(state==='RESTORING')return out('switching',bi('Returning to the previous route','Возврат на прежний маршрут'),bi('The router is putting the original route back and checking it.','Роутер возвращает исходный маршрут и проверяет его.'));
  if(model.transitioning)return out('switching',bi('Switching the route','Переключение маршрута'),bi('The router is changing the route and waits for a LAN computer to confirm it. This takes up to 90 seconds.','Роутер меняет маршрут и ждёт подтверждения от компьютера в LAN. Это занимает до 90 секунд.'));
  if(state==='OBSERVING'&&ns.certified===true)return out('ok',bi('Auto is on','Auto включён'),bi('Watching the primary. If it fails, the router switches to the reserve after a LAN computer confirms the new route.','Следит за основным. При его отказе роутер переключится на резерв после подтверждения нового маршрута компьютером в LAN.'));
  if(state==='COMMITTED')return out('reserve',bi('Working on the reserve','Работаю на резерве'),bi('The reserve route is selected. Primary health is shown separately; return depends on policy, fresh evidence and operator hold.','Выбран резервный маршрут. Исправность основного показана отдельно; возврат зависит от политики, свежих данных и ручного удержания.'));
  if(state==='DEGRADED-ON-RESERVE')return out('problem',bi('The reserve is failing too','Резерв тоже не работает'),bi('The selected reserve has problems. Check both VPNs; any return must satisfy the current mode, saved policy and fresh primary readiness.','На выбранном резерве есть проблемы. Проверьте оба VPN; возврат должен соответствовать текущему режиму, политике и свежей готовности основного.'));
  if(state==='STOPPED-ON-RESERVE')return out('problem',bi('Stopped, but still on the reserve','Остановлен, но роутер всё ещё на резерве'),bi('The original route is not restored. Press Return to primary when the primary works.','Исходный маршрут не восстановлен. Нажмите «Вернуться на основной», когда основной заработает.'));
  if(state==='RELEASE-PENDING'||blockers.indexOf('GUARD-RELEASE-UNCONFIRMED')>=0)return out('problem',bi('Internet may be blocked: the return has not finished','Интернет может быть заблокирован: возврат не закончился'),bi('Recovery is still pending. See Help → emergency return; Stop has not completed.','Восстановление ещё не завершено. См. «Помощь» → аварийный возврат; остановка не завершена.'),'GUARD-RELEASE-UNCONFIRMED');
  if(state==='BLOCKED'&&intent.requested==='on'&&blockers.length===1&&blockers[0]==='VENDOR-WORKER-BUSY')return out('switching',bi('The router is busy; Auto will continue by itself','Роутер занят, Auto продолжит сам'),bi('A stock network worker or lock is busy. Auto continues after it clears.','Штатный сетевой обработчик или блокировка заняты. Auto продолжит работу после их завершения.'));
  if(state==='BLOCKED'&&intent.requested==='on')return out('problem',bi('Auto is blocked','Auto заблокирован'),blockers.length?autoBlockerText(blockers[0]):bi('The router reports a condition that blocks Auto. See the list below.','Роутер сообщает условие, блокирующее Auto. См. список ниже.'),blockers[0]);
  if(state==='TRIAL-REQUIRED')return out('problem',bi('A LAN trial is required','Нужен LAN-тест'),autoBlockerText('LAN-TRIAL-REQUIRED'),'LAN-TRIAL-REQUIRED');
  if(state==='EXPIRED')return out('off',bi('Auto is off: the test window ended','Auto выключен: окно теста закончилось'),autoBlockerText('BOUNDED-DEADLINE-REQUIRED'));
  if(state==='STOPPED'&&ns.original_restored===true)return out('off',bi('Auto is off','Auto выключен'),bi('Control is back with the router; the original route is verified.','Управление вернулось роутеру; исходный маршрут проверен.'));
  return out('off',bi('Auto is off','Auto выключен'),bi('Monitoring continues; nothing is switched while Auto is off.','Мониторинг продолжается; пока Auto выключен, ничего не переключается.'));
}
// The card's lamp has two states only: green = automatic switching is working (watching, switching or holding the
// reserve), red = it is not (off, blocked, needs attention or no fresh data). The detailed state stays in the text.
function autoWorking(light){return !!light&&(light.key==='ok'||light.key==='reserve'||light.key==='switching'&&light.running===true);}
function renderAutoLight(light,technicalCode){
  var working=autoWorking(light);
  var lamps=[E('span',{'class':'hv-lamp hv-lamp-red'+(working?'':' hv-lamp-lit'),'aria-hidden':'true'}),E('span',{'class':'hv-lamp hv-lamp-green'+(working?' hv-lamp-lit':''),'aria-hidden':'true'})];
  var housing=E('div',{'class':'hv-light hv-light-two hv-light-'+(working?'on':'off'),'role':'img','aria-label':working?bi('Automatic switching works','Автопереключение работает'):bi('Automatic switching does not work','Автопереключение не работает')},lamps);
  var legend=E('ul',{'class':'hv-light-legend','aria-label':bi('What the lamps mean','Что означают лампы')},[
    E('li',{'class':working?'hv-legend-current':''},[E('span',{'class':'hv-dot hv-dot-green','aria-hidden':'true'}),bi('Green: automatic switching works. It watches the primary and moves traffic to the reserve if the primary fails.','Зелёный: автопереключение работает. Оно следит за основным и при его отказе переводит трафик на резерв.')]),
    E('li',{'class':working?'':'hv-legend-current'},[E('span',{'class':'hv-dot hv-dot-red','aria-hidden':'true'}),bi('Red: automatic switching does not work: it is off, blocked, needs your attention, or the router sends no fresh data. Traffic then stays where it is.','Красный: автопереключение не работает: выключено, заблокировано, требует внимания или роутер не присылает свежих данных. Трафик тогда остаётся там, где есть.')]),
    E('li',{},[E('span',{'class':'hv-dot hv-dot-green','aria-hidden':'true'}),' / ',E('span',{'class':'hv-dot hv-dot-red','aria-hidden':'true'}),bi(' Primary and Reserve: green works in Auto, yellow is alive and waiting to be switched on by Auto, grey is waiting for the router answer, red is an error.',' Основной и Резерв: зелёный — работает в автомате, жёлтый — живой и ожидает включения в режиме автомат, серый — ждём ответа роутера, красный — ошибка.')])]);
  return E('div',{'class':'hv-light-block'},[housing,E('div',{'class':'hv-light-text'},[E('strong',{'class':'hv-auto-label hv-light-title'},[E('span',{'class':'hv-light-icon','aria-hidden':'true'},light.icon+' '),light.title]),E('p',autoHintLive(light.hint),light.hint),E('small',{'class':'hv-auto-tech'},[bi('Technical state: ','Техническое состояние: ')+technicalCode,light.code&&typeof errorCodeLink==='function'?' · ':null,light.code&&typeof errorCodeLink==='function'?errorCodeLink(light.code):null].filter(Boolean)),E('details',{'class':'hv-light-help'},[E('summary',{},bi('What do the colours mean?','Что означают цвета?')),legend])])]);
}

// Reply of the Auto button: the code of the answer is shown as a link to its row in the error table, with its short meaning.
function autoCodeNotice(code,extra){
  var row=(typeof ERROR_ROWS!=='undefined'?ERROR_ROWS:[]).filter(function(r){return r[0]===code;})[0];
  return E('div',{},[E('p',{},[errorCodeLink(code),row?' · '+bi(row[2],row[3]):' · '+autoBlockerText(code),extra?' · '+extra:'']),renderAutoRemedy(code)].filter(Boolean));
}
var AUTO_FAILURE_SHOWN=null;
/* A rebuilt live region is read again by screen readers; only a changed hint is marked live. */
var AUTO_HINT_LAST=null;
function autoHintLive(text){var changed=text!==AUTO_HINT_LAST;AUTO_HINT_LAST=text;return changed?{'role':'status','aria-live':'polite'}:{'aria-live':'off'};}
function autoShowError(title,node){
  if(typeof ui!=='undefined'&&ui&&typeof ui.showModal==='function')ui.showModal(title,[node,E('div',{'class':'right'},E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть')))]);
  else if(typeof ui!=='undefined'&&ui&&typeof ui.addNotification==='function')ui.addNotification(null,node);
}
var autoRequestBusy=false,autoStopBusy=false,autoStartPending=false;
var autoCommandPending=null,autoControlRefresh=function(){};
/* Countdown on the Auto button: the expected time is the median of the last measured starts/stops in this browser. */
var AUTO_COUNTDOWN=null,AUTO_COUNTDOWN_TIMER=null,AUTO_COUNTDOWN_NODES=null,AUTO_DURATION_KEY='hv-auto-durations';
function autoDurations(){try{var v=JSON.parse(window.localStorage.getItem(AUTO_DURATION_KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(error){return {};}}
function autoDurationEstimate(kind){
  var rows=(autoDurations()[kind]||[]).filter(function(n){return Number.isFinite(n)&&n>0&&n<600;}).sort(function(a,b){return a-b;});
  if(!rows.length)return kind==='stop'?10:30;
  var mid=Math.floor(rows.length/2),median=rows.length%2?rows[mid]:(rows[mid-1]+rows[mid])/2;
  return Math.max(3,Math.ceil(median));
}
function autoDurationRecord(kind,seconds){
  if(!(Number.isFinite(seconds)&&seconds>0&&seconds<600))return;
  var all=autoDurations();all[kind]=(Array.isArray(all[kind])?all[kind]:[]).concat([Math.round(seconds*10)/10]).slice(-5);
  try{window.localStorage.setItem(AUTO_DURATION_KEY,JSON.stringify(all));}catch(error){}
}
function autoCountdownText(){
  if(!AUTO_COUNTDOWN)return '';
  var left=AUTO_COUNTDOWN.estimate-(Date.now()-AUTO_COUNTDOWN.t0)/1000;
  return left>0?Math.ceil(left)+bi(' s',' с'):'+'+Math.floor(-left)+bi(' s',' с');
}
function autoCountdownTick(){
  var n=AUTO_COUNTDOWN_NODES;if(!n)return;
  function hide(on){if(on){if(n.root.setAttribute)n.root.setAttribute('hidden','');}else if(n.root.removeAttribute)n.root.removeAttribute('hidden');}
  if(!AUTO_COUNTDOWN){hide(true);return;}
  var left=AUTO_COUNTDOWN.estimate-(Date.now()-AUTO_COUNTDOWN.t0)/1000,part=Math.max(0,Math.min(1,left/AUTO_COUNTDOWN.estimate));
  hide(false);n.text.textContent=autoCountdownText();
  if(n.root.style&&n.root.style.setProperty)n.root.style.setProperty('--hv-countdown',String(part));
  if(n.root.classList&&n.root.classList.toggle)n.root.classList.toggle('hv-auto-countdown-over',left<=0);
}
function autoCountdownBegin(kind){
  if(AUTO_COUNTDOWN&&AUTO_COUNTDOWN.kind===kind)return;
  AUTO_COUNTDOWN={kind:kind,t0:Date.now(),estimate:autoDurationEstimate(kind)};
  if(!AUTO_COUNTDOWN_TIMER&&typeof setInterval==='function')AUTO_COUNTDOWN_TIMER=setInterval(autoCountdownTick,250);
  autoCountdownTick();
}
function autoCountdownEnd(success){
  if(!AUTO_COUNTDOWN)return;
  if(success)autoDurationRecord(AUTO_COUNTDOWN.kind,(Date.now()-AUTO_COUNTDOWN.t0)/1000);
  AUTO_COUNTDOWN=null;if(AUTO_COUNTDOWN_TIMER&&typeof clearInterval==='function'){clearInterval(AUTO_COUNTDOWN_TIMER);AUTO_COUNTDOWN_TIMER=null;}
  autoCountdownTick();
}
function autoCommandOperation(status,now){
  var model=autoControlModel(status,now),intent=status.auto_control||{},phase=intent.pair_phase;
  var failedStart=model.fresh&&(status.native_failover||{}).state==='BLOCKED'&&!model.awaiting&&!model.on&&!model.transitioning;
  if(autoCommandPending&&autoCommandPending.acknowledged&&model.fresh&&intent.requested_at>autoCommandPending.baseline){
    var terminal=['FAILED','STOPPED','HELD'].indexOf(phase)>=0||!autoCommandPending.stop&&failedStart;
    var done=autoCommandPending.stop?terminal:terminal||phase==='RUNNING'&&model.on&&!model.awaiting&&!model.transitioning;
    var legacyDone=!phase&&!model.awaiting&&!model.transitioning&&
      (autoCommandPending.stop?model.off:model.on||model.off||model.color==='error');
    if(done||legacyDone)autoCommandPending=null;
  }
  if(autoCommandPending&&Number.isFinite(autoCommandPending.t0)&&Date.now()-autoCommandPending.t0>Math.max(120000,2000*autoDurationEstimate(autoCommandPending.stop?'stop':'start'))){
    autoCommandPending=null;
    if(typeof ui!=='undefined'&&ui&&typeof ui.addNotification==='function')ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNCONFIRMED'));
  }
  if(autoCommandPending)return autoCommandPending.stop?'stopping':'starting';
  if(phase==='STARTING')return failedStart?null:'starting';
  if(phase==='STOPPING')return 'stopping';
  if(phase==='UNKNOWN')return 'unknown';
  if(model.awaiting)return intent.requested==='off'?'stopping':'starting';
  if(model.transitioning)return intent.requested==='off'?'stopping':['RUNNING','HELD'].indexOf(phase)>=0?null:'starting';
  return null;
}
function renderAutoPowerControl(status,inventory){
  var ns=status.native_failover||{},intent=status.auto_control||{},model=autoControlModel(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  var light=autoLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),controlRevision=intent.control_revision;
  var monitorReady=typeof monitorLightModel!=='function'||monitorLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000),false).key==='ok';
  var actionLabel=E('span',{'class':'hv-auto-action'},'');
  var countdownText=E('span',{'class':'hv-auto-countdown-text'},''),countdown=E('span',{'class':'hv-auto-countdown','aria-hidden':'true','hidden':''},[E('span',{'class':'hv-auto-countdown-ring'}),countdownText]);
  var countdownNodes={root:countdown,text:countdownText};
  function currentControl(){
    var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
    model=autoControlModel(status,now);
    monitorReady=typeof monitorLightModel!=='function'||monitorLightModel(status,inventory,now,false).key==='ok';
  }
  function syncButton(){
    currentControl();
    var operation=autoCommandOperation(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),stop=model.stop||autoStartPending||operation==='starting'||!model.fresh;
    button.disabled=!!(autoStopBusy||operation==='stopping'||!stop&&(operation||autoRequestBusy||inventory.error||!model.fresh||!monitorReady));
    if(button.classList&&button.classList.toggle){button.classList.toggle('hv-auto-stop-requested',operation==='stopping');
      // The button shows "on" only when Auto is confirmed working and no command is still pending.
      var confirmedOn=!operation&&autoWorking(autoLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)));
      button.classList.toggle('hv-auto-lit-on',confirmedOn);button.classList.toggle('hv-auto-lit-off',!confirmedOn);}
    AUTO_COUNTDOWN_NODES=countdownNodes;
    if(operation==='starting'||operation==='stopping')autoCountdownBegin(operation==='starting'?'start':'stop');
    else if(AUTO_COUNTDOWN){var nowOn=autoWorking(autoLightModel(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)));autoCountdownEnd(AUTO_COUNTDOWN.kind==='start'?nowOn:!nowOn);}
    button.setAttribute('data-auto-operation',operation||'idle');
    var label=operation==='starting'?bi('Turning Auto on…','Включение Auto…'):operation==='stopping'?bi('Turning Auto off…','Выключение Auto…'):operation==='unknown'?bi('Awaiting controller state…','Ожидание состояния контроллера…'):stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим');
    button.setAttribute('aria-label',label);button.setAttribute('aria-busy',operation?'true':'false');
    actionLabel.textContent=operation?label+(AUTO_COUNTDOWN?' '+bi('about ','примерно ')+autoDurationEstimate(AUTO_COUNTDOWN.kind)+bi(' s',' с'):''):stop?bi('Press to turn Auto off','Нажмите, чтобы выключить Auto'):bi('Press to turn Auto on','Нажмите, чтобы включить Auto');
  }
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-neutral'+(autoWorking(light)?' hv-auto-lit-on':' hv-auto-lit-off')+(model.stop?' hv-auto-armed':''),'aria-label':model.stop?bi('Stop auto mode','Выключить авторежим'):bi('Start auto mode','Включить авторежим'),'aria-pressed':model.on?'true':'false','disabled':(model.stop?autoStopBusy:autoRequestBusy||autoStopBusy||(inventory.error||!model.fresh))?'':null,'click':function(){
    currentControl();
    var operation=autoCommandOperation(status,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)),stop=model.stop||autoStartPending||operation==='starting'||!model.fresh;if(autoStopBusy||operation==='stopping'||!stop&&(operation||autoRequestBusy||!monitorReady))return;
    if(!stop&&(typeof controlRevision!=='string'||!/^[0-9a-f]{32}$/.test(controlRevision))){ui.addNotification(null,autoCodeNotice('CONTROL-REVISION-STALE'));window.location.reload();return;}
    autoCommandPending={stop:stop,baseline:intent.requested_at||0,acknowledged:false,t0:Date.now()};autoCountdownBegin(stop?'stop':'start');
    if(stop)autoStopBusy=true;else{autoRequestBusy=true;autoStartPending=true;}autoControlRefresh();
    var call=rpc.declare({object:'homensai-vpn',method:stop?'native_stop':'native_start',params:stop?['request_source']:['control_revision','request_source'],expect:{}});
    return (stop?call('manual'):call(controlRevision,'manual')).then(function(result){
      if(autoCommandPending&&autoCommandPending.stop===stop){if(autoRequestAcknowledged(result,stop))autoCommandPending.acknowledged=true;else autoCommandPending=null;}
      if(!stop&&result&&result.accepted===false&&(result.code==='CONTROL-REVISION-STALE'||Array.isArray(result.blockers)&&result.blockers.indexOf('CONTROL-REVISION-STALE')>=0)){ui.addNotification(null,autoCodeNotice('CONTROL-REVISION-STALE'));window.location.reload();return;}
      if(result&&typeof result.code==='string'&&/^[A-Z][A-Z0-9-]{2,95}$/.test(result.code)&&(result.accepted===false||result.queued===false))ui.addNotification(null,autoCodeNotice(result.code,result.settings_unverified?bi('router settings could not be read','настройки роутера не прочитаны'):''));
      else if(result&&result.accepted===false){autoShowError(bi('Auto did not start','Auto не запустился'),E('div',{},[autoCodeNotice('AUTO-START-REFUSED'),E('ul',{},(result.blockers||[]).map(function(code){return E('li',{},[code+' · '+autoBlockerText(code),renderAutoRemedy(code)].filter(Boolean));}))]));}
      else if(!autoRequestAcknowledged(result,stop))ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
    }).catch(function(){if(autoCommandPending&&autoCommandPending.stop===stop){if(stop)autoCommandPending=null;else autoCommandPending.acknowledged=true;}ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){if(stop)autoStopBusy=false;else{autoRequestBusy=false;autoStartPending=false;}autoControlRefresh();});
  }},[E('span',{'class':'hv-power-symbol','aria-hidden':'true'}),countdown]);
  autoControlRefresh=syncButton;syncButton();
  return {button:button,actionLabel:actionLabel,model:model,light:light};
}
function renderAutoControl(status,inventory,refresh){
  var power=renderAutoPowerControl(status,inventory),button=power.button,actionLabel=power.actionLabel,model=power.model,light=power.light;
  var ns=status.native_failover||{},intent=status.auto_control||{};
  var rows=status.profiles||[],settings=inventory.settings||{};
  function profile(id){return rows.filter(function(p){return p.id===id;})[0];}
  var source=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',(typeof statusNow==='function'?statusNow(status):Date.now()/1000),ns.source):profile(ns.source||settings.plan_source),target=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',(typeof statusNow==='function'?statusNow(status):Date.now()/1000),ns.target):profile(ns.target||settings.plan_target);
  var path=typeof manualConfirmedPath==='function'?manualConfirmedPath(status,source,target,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)):autoPathModel(status,source,target,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  var pathLabels={neutral:bi('No recent check','Нет свежей проверки'),healthy:bi('Active traffic path','Активный путь трафика'),ready:bi('Ready for automatic mode','Готов к работе в автомате'),inactive:bi('Tunnel not connected','Туннель не подключён'),failed:bi('Connectivity failed','Ошибка доступности'),checking:bi('Checking…','Идёт проверка…')};
  // Channel selection is separate from probe health: an idle healthy reserve is not a failure.
  function nodeTone(p,key){
    if(typeof manualChannelTone==='function')return manualChannelTone(p,key,path,(typeof statusNow==='function'?statusNow(status):Date.now()/1000),autoWorking(light));
    return {color:'grey',text:bi('No recent check','Нет свежей проверки'),carrier:false};
  }
  function box(p,label,key){var state=path[key],tone=nodeTone(p,key);var attributes={'class':'hv-auto-node hv-node-two hv-node-'+tone.color+(tone.carrier?' hv-node-carrier':''),'data-path-node':key,'data-path-state':state,'data-node-tone':tone.color};
    // The address the internet sees is not printed on screen; it is available as a tooltip only.
    if(p&&p.exit_ip&&profileHealth(p,(typeof statusNow==='function'?statusNow(status):Date.now()/1000)).state==='healthy')attributes.title=bi('Exit IP: ','Внешний IP: ')+p.exit_ip;
    return E('div',attributes,[E('small',{},label),E('strong',{'class':'hv-node-protocol'},p?protocolLabel(p):'—'),E('b',{},p?countryLabel(p):bi('Choose in Settings','Выберите в настройках')),p?E('span',{'title':bi('Group: a label you can set in Settings → All application settings → 3 · Existing VPNs. It does not change how the VPN works.','Группа: метка, которую можно задать в «Настройки → Все настройки приложения → 3 · Существующие VPN». Она не влияет на работу VPN.')},(customName(p)?customName(p)+' · ':'')+bi('Group: ','Группа: ')+(p.channel||'default')):null,E('span',{'class':'hv-path-label','title':pathLabels[state]},[E('span',{'class':'hv-node-dot','aria-hidden':'true'}),tone.text])].filter(Boolean));}
  var diagram=E('div',{'class':'hv-auto-diagram hv-path-diagram'+(path.moving?' hv-path-moving':'')+(path.direction==='back'?' hv-path-back':''),'aria-label':bi('Configured failover path','Настроенная схема переключения')},[box(source,bi('Primary','Основной'),'source'),E('span',{'class':'hv-auto-arrow '+(path.direction!=='none'?'hv-arrow-on':''),'aria-label':path.moving?bi('Switching in progress','Выполняется переключение'):path.direction!=='none'?bi('Reserve selected','Выбран резерв'):bi('Automatic transition inactive','Автопереход неактивен')},path.direction==='back'?'←':path.direction==='forward'?'→':'⋯'),box(target,bi('Reserve','Резерв'),'target')]);
  var pairMode=settings.pair_auto_mode==='router-probed-ipv4';
  var until=pairMode?0:autoWindowDeadline(intent,settings);
  var readiness=autoReadiness(status,inventory,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  var checklist=null;
  if(pairMode){
    checklist=null&&E('details',{'class':'hv-auto-readiness','data-auto-explanation':'mode'},[E('summary',{},bi('How two-channel Auto works','Как работает Auto двух каналов')),E('p',{'class':'hv-step-note'},bi('Auto starts the saved primary and reserve, checks IPv4 DNS/HTTPS, switches after repeated failures and returns after stable recovery according to your settings. Stop remains available during startup. Auto needs an explicit Start after restart.','Auto запускает сохранённые основной и резервный VPN, проверяет IPv4 DNS/HTTPS, переключается после повторных отказов и возвращается после устойчивого восстановления по вашим настройкам. Stop доступен при запуске. После перезапуска нужен явный Start.'))]);
  }else if(!model.on&&!model.transitioning&&!model.stop){
    checklist=E('div',{'class':'hv-auto-readiness'},[E('p',{'class':'hv-step-note'},bi('Step 2 · Turn on Auto. Do it after step 1 (“Check the VPNs now”, at the top of this page) shows that your VPNs work and the list below is complete.','Шаг 2 · Включите Auto. Делайте это после шага 1 («Проверить VPN сейчас», вверху страницы), когда проверка показала, что ваши VPN работают, и список ниже выполнен.')),E('h3',{},readiness.ready?bi('Ready to start','Готово к запуску'):bi('Before you can start Auto','Что нужно перед запуском Auto')),E('ol',{'class':'hv-req-list'},readiness.steps.map(function(step){
      var isNext=readiness.next&&readiness.next.key===step.key;
      var extra=step.key==='router'&&!step.done&&step.codes&&step.codes.length?E('ul',{'class':'hv-req-codes'},step.codes.map(function(code){return E('li',{},[safeCode(code)?errorCodeLink(code):E('code',{},code),' · '+autoBlockerText(code),renderAutoRemedy(code)].filter(Boolean));})):null;
      return E('li',{'class':'hv-req hv-req-'+(step.done?'done':isNext?'next':'todo')},[E('span',{'class':'hv-req-mark','aria-hidden':'true'},step.done?'✓':isNext?'→':'·'),E('div',{},[E('strong',{},step.title),step.done?null:E('p',{},step.hint),extra].filter(Boolean)),E('span',{'class':'hv-visually-hidden'},step.done?bi('done','выполнено'):bi('not done','не выполнено'))]);
    })),E('p',{'class':'hv-req-actions'},[E('a',{'class':'cbi-button','href':'#settings'},bi('Open Settings','Открыть настройки')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')),' ',E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/start-lan-helper.ps1'),'download':'start-lan-helper.ps1'},bi('Download launcher','Скачать запуск'))])]);
  }
  var holdReturn=null;
  // Return to the primary belongs to this card: it is offered whenever traffic is on the reserve (also while Auto is on).
  if(!pairMode&&model.fresh&&['STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE','COMMITTED'].indexOf(ns.state)>=0){
    var answer=intent.return_result,answerText=answer&&Number.isFinite(answer.time)&&(typeof statusNow==='function'?statusNow(status):Date.now()/1000)-answer.time<600?(answer.ok?autoBlockerText('OPERATOR-RETURN'):autoBlockerText(answer.code)):'';
    var returnButton=guardResume(E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':autoRequestBusy||autoStopBusy?'':null,'click':function(){
      if(autoRequestBusy||autoStopBusy)return;return guardedAction(returnButton,function(){autoRequestBusy=true;
      return rpc.declare({object:'homensai-vpn',method:'native_return',expect:{}})().then(function(result){
        if(result&&result.accepted===false)ui.addNotification(null,E('p',{},(result.code||'RETURN-REFUSED')+' · '+autoBlockerText(result.code)));
        else if(!autoRequestAcknowledged(result,false))ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-UNVERIFIED'));
        else ui.addNotification(null,E('p',{},bi('Return requested. The router checks the primary first and reports the result here.','Возврат запрошен. Роутер сначала проверит основной и покажет результат здесь.')));
      }).catch(function(){ui.addNotification(null,autoCodeNotice('AUTO-CONTROL-FAILED'));}).finally(function(){autoRequestBusy=false;});},{key:'auto-return'});
    }},bi('Return to primary','Вернуться на основной')),'auto-return');
    holdReturn=E('details',{'class':'hv-auto-hold'},[E('summary',{},bi('Legacy-mode recovery','Восстановление прежнего режима')),returnButton,autoNoInternetLink(),answerText?E('p',{'role':'status'},answerText):null].filter(Boolean));
  }
  var technicalCode=ns.state?ns.state+(ns.reason?' · '+ns.reason:'')+(model.fresh?'':' · STATUS-STALE'):'UNKNOWN';
  var liveChart=typeof renderAutoLive==='function'?renderAutoLive(status,inventory):null;
  var dayChart=typeof renderAutoDay==='function'?renderAutoDay(status):null;
  var statistics=(liveChart||dayChart)?E('details',{'class':'hv-chart-card hv-auto-details hv-auto-statistics','data-auto-disclosure':'live-statistics','data-stats-reset':'auto'},[E('summary',{},bi('Real-time channel switching','Переключение каналов в реальном времени')),liveChart,dayChart].filter(Boolean)):null;
  if(statistics&&typeof rememberDisclosure==='function')rememberDisclosure(statistics,'auto-live-statistics');
  var header=E('div',{'class':'hv-auto-header','id':'hv-auto-vpn'},[E('h2',{},bi('Automatic VPN failover','Автоматическое переключение VPN')),typeof renderMonitorBlock==='function'?renderMonitorBlock(status,inventory):null].filter(Boolean));
  var failureInfo=intent.failure&&intent.failure.code&&!model.on?intent.failure.code:null;
  // A failed Start is shown once per failure in its own window, so the card layout never changes.
  if(failureInfo&&typeof ui!=='undefined'&&ui&&typeof ui.showModal==='function'){
    var failureKey=failureInfo+'@'+(intent.failure.time||0),shownKey=null;
    try{shownKey=window.sessionStorage.getItem('homensai-vpn-auto-failure');}catch(e){shownKey=AUTO_FAILURE_SHOWN;}
    if(shownKey!==failureKey&&AUTO_FAILURE_SHOWN!==failureKey){
      AUTO_FAILURE_SHOWN=failureKey;try{window.sessionStorage.setItem('homensai-vpn-auto-failure',failureKey);}catch(e){}
      ui.showModal(bi('Auto did not start','Auto не запустился'),[E('p',{},bi('Reason:','Причина:')),autoCodeNotice(failureInfo),E('div',{'class':'right'},E('button',{'type':'button','class':'cbi-button','click':function(){ui.hideModal();}},bi('Close','Закрыть')))]);
    }
  }
  var automatic=E('section',{'class':'hv-chart-card hv-auto-control'},[header,E('div',{'class':'hv-auto-controls'},[E('div',{'class':'hv-auto-switch'},[E('div',{'class':'hv-auto-power-unit'},[E('strong',{'class':'hv-auto-state hv-auto-state-'+(autoWorking(light)?'on':'off'),'role':'status'},autoWorking(light)?bi('Auto works','Auto работает'):bi('Auto does not work','Auto не работает')),button,actionLabel]),renderAutoLight(light,technicalCode)]),typeof renderConnectivityCheck==='function'&&typeof refresh==='function'?renderConnectivityCheck(status,refresh,inventory):null].filter(Boolean)),holdReturn,checklist,pairMode?null:E('details',{'class':'hv-auto-scope','data-auto-explanation':'scope'},[E('summary',{},bi('About these checks','Об этих проверках')),E('p',{'class':'hv-auto-limit'},(pairMode?bi('Two selected VPN channels. The router checks it itself.','Два выбранных VPN-канала. Проверку делает сам роутер.'):bi('Experimental: every automatic switch must be confirmed by the LAN helper running on a computer, otherwise the router rolls back.','Экспериментально: каждое автоматическое переключение должно подтверждаться LAN-помощником на компьютере, иначе роутер откатится.'))+(Number.isFinite(until)&&until>0?' '+bi('Window ends: ','Окно действует до: ')+new Date(until*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB')+'.':''))])].filter(Boolean));
  return E('div',{'class':'hv-auto-sections'},[automatic,statistics,typeof renderManualSwitch==='function'?renderManualSwitch(status,inventory):null].filter(Boolean));
}
