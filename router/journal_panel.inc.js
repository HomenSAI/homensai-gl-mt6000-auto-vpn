var JOURNAL_TYPES={
  "OK": {
    "code": "EVENT-CHECK-OK",
    "label": [
      "Check passed",
      "Проверка прошла"
    ],
    "message": [
      "Channel availability threshold was met",
      "Условие доступности канала выполнено"
    ],
    "meaning": [
      "The monitor received a result without a diagnostic error. This records channel availability at that observation; it does not mean traffic switched or that Auto was activated.",
      "Монитор получил результат без диагностической ошибки. Это наблюдение доступности канала в тот момент; оно не означает переключение трафика или включение Auto."
    ],
    "level": "ok"
  },
  "FAILURE": {
    "code": "EVENT-CHECK-FAILED",
    "label": [
      "Check failed",
      "Ошибка проверки"
    ],
    "message": [
      "Connection check failed",
      "Ошибка проверки соединения"
    ],
    "meaning": [
      "A failed channel check was recorded. Open the saved diagnostic code for the observed failure. It does not by itself prove a route switch.",
      "Зафиксирована неудачная проверка канала. Причину наблюдаемого отказа смотрите в сохранённом диагностическом коде. Сама запись не доказывает смену маршрута."
    ],
    "level": "error"
  },
  "RECOVERY": {
    "code": "EVENT-CONNECTION-RECOVERED",
    "label": [
      "Availability restored",
      "Доступность восстановлена"
    ],
    "message": [
      "Connection availability recovered",
      "Доступность соединения восстановлена"
    ],
    "meaning": [
      "A previously failed channel became available again in observations. This is recovery of availability, not proof that it became the traffic route.",
      "Ранее отказавший канал снова стал доступен по наблюдениям. Это восстановление доступности, а не доказательство, что через него уже идёт трафик."
    ],
    "level": "ok"
  },
  "DISABLED": {
    "code": "EVENT-PROFILE-DISABLED",
    "label": [
      "Profile disabled",
      "Профиль отключён"
    ],
    "message": [
      "VPN profile was disabled",
      "VPN-профиль отключён"
    ],
    "meaning": [
      "The profile is administratively disabled or inactive. This is distinct from a failed Internet check.",
      "Профиль административно отключён или неактивен. Это отличается от ошибки проверки Интернета."
    ],
    "level": "warning"
  },
  "GAP": {
    "code": "EVENT-OBSERVATION-GAP",
    "label": [
      "No observation interval",
      "Перерыв наблюдений"
    ],
    "message": [
      "A gap in observations was recorded",
      "Зафиксирован перерыв наблюдений"
    ],
    "meaning": [
      "There were no trusted measurements for an interval. Neither successful connectivity nor failure is invented for the missing period.",
      "За интервал нет достоверных измерений. Пропуск не превращается ни в исправность, ни в выдуманный отказ."
    ],
    "level": "warning"
  },
  "OBSERVING": {
    "code": "EVENT-MONITORING",
    "label": [
      "Observing channels",
      "Наблюдение за каналами"
    ],
    "message": [
      "The controller is observing the VPN channels",
      "Контроллер наблюдает за VPN-каналами"
    ],
    "meaning": [
      "The controller is checking the channels. This state alone does not describe a newly completed traffic switch; channel selection has separate confirmation.",
      "Контроллер проверяет каналы. Само это состояние не означает только что выполненное переключение трафика; выбор маршрута подтверждается отдельно."
    ],
    "level": "ok"
  },
  "STARTING": {
    "code": "EVENT-AUTO-STARTING",
    "label": [
      "Auto starting",
      "Запуск Auto"
    ],
    "message": [
      "Auto startup is in progress",
      "Выполняется запуск Auto"
    ],
    "meaning": [
      "Startup was accepted and is still being prepared. Wait for its actual completion or a specific refusal; a request is not a running session.",
      "Запуск принят и ещё подготавливается. Дождитесь фактического завершения или конкретного отказа; запрос не равен работающему сеансу."
    ],
    "level": "warning"
  },
  "ARMED": {
    "code": "EVENT-CHANNEL-PREPARATION",
    "label": [
      "Preparing channels",
      "Подготовка каналов"
    ],
    "message": [
      "Channel prerequisites are being prepared and checked",
      "Подготавливаются и проверяются условия работы каналов"
    ],
    "meaning": [
      "A preparation stage was recorded. Connectivity and routing may still be checked; this is not a completed switch.",
      "Зафиксирован подготовительный этап. Связность и маршрут ещё могут проверяться; это не завершённое переключение."
    ],
    "level": "warning"
  },
  "APPLYING": {
    "code": "EVENT-ROUTE-APPLYING",
    "label": [
      "Selecting route",
      "Выбор маршрута"
    ],
    "message": [
      "A route-selection command is being applied",
      "Выполняется команда выбора маршрута"
    ],
    "meaning": [
      "The operation is applying the planned traffic selection. Its final outcome must be confirmed by a later event.",
      "Операция применяет запланированный выбор трафика. Итог должен быть подтверждён следующим событием."
    ],
    "level": "warning"
  },
  "WAIT-CLIENT": {
    "code": "EVENT-PATH-CONFIRMATION",
    "label": [
      "Verifying path",
      "Подтверждение пути"
    ],
    "message": [
      "The selected path is awaiting verification",
      "Ожидается подтверждение выбранного пути"
    ],
    "meaning": [
      "The change is not yet accepted as a confirmed route. The required evidence depends on the recorded operating mode: router observations or a separate client witness.",
      "Изменение ещё не принято как подтверждённый маршрут. Требуемое доказательство зависит от сохранённого режима: наблюдения роутера либо отдельный клиентский тест."
    ],
    "level": "warning"
  },
  "COMMITTED": {
    "code": "EVENT-RESERVE-SELECTED",
    "label": [
      "Reserve selected",
      "Резерв выбран"
    ],
    "message": [
      "Reserve traffic selection was confirmed",
      "Выбор резервного маршрута подтверждён"
    ],
    "meaning": [
      "The recorded operation confirmed reserve selection. This does not imply that the primary is broken; its health is a separate observation.",
      "Операция подтвердила выбор резерва. Это не означает неисправность основного: его состояние проверяется отдельно."
    ],
    "level": "ok"
  },
  "STOPPED-ON-RESERVE": {
    "code": "EVENT-RESERVE-HELD",
    "label": [
      "Reserve retained",
      "Резерв удержан"
    ],
    "message": [
      "The operation ended while retaining the reserve",
      "Операция завершилась с сохранением резерва"
    ],
    "meaning": [
      "The operation retained reserve routing. In a continuous session Auto may remain on; this transaction state is not proof of a global Auto shutdown.",
      "Операция сохранила резервный маршрут. В непрерывном сеансе Auto может продолжать работать; это состояние транзакции не доказывает глобальное выключение Auto."
    ],
    "level": "ok"
  },
  "RESTORING": {
    "code": "EVENT-RETURN-IN-PROGRESS",
    "label": [
      "Returning route",
      "Возврат маршрута"
    ],
    "message": [
      "The original route is being restored",
      "Восстанавливается исходный маршрут"
    ],
    "meaning": [
      "Restoration is in progress. A later verified outcome is required before describing the original route as restored.",
      "Восстановление выполняется. Прежде чем считать исходный маршрут восстановленным, требуется последующее подтверждение."
    ],
    "level": "warning"
  },
  "ROLLED-BACK": {
    "code": "EVENT-ROLLBACK-RECORDED",
    "label": [
      "Rollback recorded",
      "Записан откат"
    ],
    "message": [
      "A rollback stage was recorded",
      "Зафиксирован этап отката"
    ],
    "meaning": [
      "This old record names a rollback. If it lacks an original_restored confirmation, successful restoration must not be invented.",
      "Старая запись содержит этап отката. Если подтверждение original_restored в ней отсутствует, успешное восстановление не приписывается."
    ],
    "level": "warning"
  },
  "RETURNED": {
    "code": "EVENT-ORIGINAL-RESTORED",
    "label": [
      "Original route restored",
      "Исходный маршрут восстановлен"
    ],
    "message": [
      "Restoration of the original route was confirmed",
      "Восстановление исходного маршрута подтверждено"
    ],
    "meaning": [
      "The event includes explicit verified restoration evidence. This is separate from a request to return or a restoration-in-progress stage.",
      "В событии есть явное подтверждение восстановления. Это отличается от запроса возврата или незавершённого восстановления."
    ],
    "level": "ok"
  },
  "STOPPED": {
    "code": "EVENT-OPERATION-STOPPED",
    "label": [
      "Operation stopped",
      "Операция остановлена"
    ],
    "message": [
      "The controller operation was stopped",
      "Управляющая операция остановлена"
    ],
    "meaning": [
      "The operation ended. A global Auto state and the resulting route must be read from their own recorded confirmations, not inferred from this word alone.",
      "Операция завершена. Общее состояние Auto и итоговый маршрут определяются по собственным подтверждениям, а не выводятся только из этого слова."
    ],
    "level": "warning"
  },
  "RUNNING": {
    "code": "EVENT-AUTO-RUNNING",
    "label": [
      "Auto running",
      "Auto работает"
    ],
    "message": [
      "The Auto session is running",
      "Сеанс Auto работает"
    ],
    "meaning": [
      "A running controller session was recorded. Each channel still needs fresh connectivity checks; it is not a guarantee of every client path.",
      "Зафиксирован работающий сеанс контроллера. Каналам по-прежнему нужны свежие проверки; это не гарантия каждого клиентского пути."
    ],
    "level": "ok"
  },
  "AUTO-START-REQUESTED": {
    "code": "EVENT-AUTO-START-REQUESTED",
    "label": [
      "Start requested",
      "Запрошен запуск"
    ],
    "message": [
      "Auto activation requested",
      "Запрошено включение Auto"
    ],
    "meaning": [
      "This is the request, including its recorded initiator. Startup is not confirmed until a later completed state.",
      "Это запрос с сохранённым инициатором. Запуск не подтверждён до последующего завершённого состояния."
    ],
    "level": "warning"
  },
  "AUTO-STOP-REQUESTED": {
    "code": "EVENT-AUTO-STOP-REQUESTED",
    "label": [
      "Stop requested",
      "Запрошена остановка"
    ],
    "message": [
      "Auto deactivation requested",
      "Запрошено выключение Auto"
    ],
    "meaning": [
      "This is a stop request, not proof that routing was restored or the controller finished stopping.",
      "Это запрос остановки, а не доказательство восстановления маршрута или завершения остановки контроллера."
    ],
    "level": "warning"
  },
  "BLOCKED": {
    "code": "EVENT-OPERATION-BLOCKED",
    "label": [
      "Action refused",
      "Действие отклонено"
    ],
    "message": [
      "A required prerequisite blocked the action",
      "Действие отклонено из-за невыполненного условия"
    ],
    "meaning": [
      "No success is inferred. Read the saved reason code; do not bypass the gate or treat a queued request as applied routing.",
      "Успех не предполагается. Прочитайте сохранённый код причины; не обходите условие и не считайте очередь выполненным выбором маршрута."
    ],
    "level": "error"
  },
  "FAILED": {
    "code": "EVENT-OPERATION-FAILED",
    "label": [
      "Operation failed",
      "Операция не выполнена"
    ],
    "message": [
      "The operation ended with an error",
      "Операция завершилась ошибкой"
    ],
    "meaning": [
      "Read the specific recorded reason and recovery outcome. Failed application or rollback is not reported as successful switching.",
      "Прочитайте конкретную сохранённую причину и итог восстановления. Неудачное применение или откат не выдаётся за успешное переключение."
    ],
    "level": "error"
  },
  "EXPIRED": {
    "code": "EVENT-WINDOW-EXPIRED",
    "label": [
      "Test window ended",
      "Окно теста завершено"
    ],
    "message": [
      "The bounded operation window expired",
      "Закончилось ограниченное окно операции"
    ],
    "meaning": [
      "A configured time boundary ended. The final routing/recovery outcome is a separate confirmation.",
      "Истёк заданный предел времени. Итог маршрутизации или восстановления подтверждается отдельно."
    ],
    "level": "warning"
  },
  "RELEASE-PENDING": {
    "code": "EVENT-RECOVERY-PENDING",
    "label": [
      "Recovery pending",
      "Восстановление ожидается"
    ],
    "message": [
      "Traffic-block release is awaiting confirmation",
      "Ожидается подтверждение снятия блокировки"
    ],
    "meaning": [
      "Recovery has not yet been verified complete. Read the saved recovery code; an attempted cleanup is not the final result.",
      "Завершение восстановления ещё не проверено. Смотрите сохранённый код; попытка очистки не равна итоговому результату."
    ],
    "level": "warning"
  },
  "DEGRADED-ON-RESERVE": {
    "code": "EVENT-RESERVE-DEGRADED",
    "label": [
      "Reserve check failed",
      "Проблема на резерве"
    ],
    "message": [
      "The selected reserve also has a connectivity problem",
      "На выбранном резерве тоже выявлена проблема связи"
    ],
    "meaning": [
      "A problem was observed on the reserve. Returning to primary still requires current evidence and the applicable policy.",
      "На резерве наблюдается проблема. Возврат на основной по-прежнему требует актуальных доказательств и применимой политики."
    ],
    "level": "error"
  },
  "TRIAL-REQUIRED": {
    "code": "EVENT-TRIAL-PREREQUISITE",
    "label": [
      "Mode prerequisite missing",
      "Не выполнено условие режима"
    ],
    "message": [
      "The chosen mode needs an additional prerequisite",
      "Для выбранного режима нужно дополнительное условие"
    ],
    "meaning": [
      "The saved reason describes the mode-specific prerequisite. A legacy LAN trial refusal does not imply every prepared router-probed session needs a client certificate.",
      "Сохранённая причина описывает условие конкретного режима. Отказ прежнего LAN-теста не означает, что любой подготовленный router-probed сеанс требует клиентский сертификат."
    ],
    "level": "warning"
  },
  "LEGACY": {
    "code": "EVENT-DETAILS-NOT-SAVED",
    "label": [
      "Record lacks detail",
      "Подробности не сохранены"
    ],
    "message": [
      "An older record did not retain a full event description",
      "В старой записи не сохранено полное описание события"
    ],
    "meaning": [
      "Only the saved fields can be explained. A missing initiator, role or final outcome is not replaced with today's route or an invented successful switch.",
      "Объясняются только сохранённые поля. Отсутствующие инициатор, роль или итог не заменяются сегодняшним маршрутом или выдуманным успешным переключением."
    ],
    "level": "warning"
  }
};
JOURNAL_TYPES.CONFLICT={code:'EVENT-RECORD-CONFLICT',label:['Record data conflict','Ошибка данных записи'],message:['The saved event contains conflicting results','В сохранённом событии противоречивые результаты'],meaning:['Success and failure were both recorded. Do not treat this as a successful channel or confirmed switch; inspect the saved diagnostic data.','Одновременно записаны успех и ошибка. Это не считается успешной проверкой или подтверждённым переходом; проверьте сохранённые диагностические данные.'],level:'error'};
Object.assign(JOURNAL_TYPES,{"CANCELLED": {"code": "EVENT-COMMAND-CANCELLED", "label": ["Command cancelled", "Команда отменена"], "message": ["The requested operation was cancelled", "Запрошенная операция отменена"], "meaning": ["Cancellation was recorded. The resulting route or cleanup still requires its own confirmation.", "Зафиксирована отмена. Итоговый маршрут или завершение очистки подтверждаются отдельно."], "level": "warning"}, "CLAIMED": {"code": "EVENT-COMMAND-ACCEPTED", "label": ["Command accepted", "Команда принята"], "message": ["The controller accepted the command for processing", "Контроллер принял команду в обработку"], "meaning": ["The worker accepted this command. It has not yet proved that the routing action completed.", "Исполнитель принял команду. Это ещё не доказывает завершение действия с маршрутом."], "level": "warning"}, "QUEUED": {"code": "EVENT-COMMAND-QUEUED", "label": ["Command queued", "Команда в очереди"], "message": ["The command is waiting in the queue", "Команда ожидает выполнения в очереди"], "meaning": ["Queue acceptance is separate from execution and verified completion.", "Принятие в очередь отличается от выполнения и подтверждённого завершения."], "level": "warning"}, "IDLE": {"code": "EVENT-CONTROLLER-IDLE", "label": ["Waiting for a command", "Ожидание команды"], "message": ["The operation handler is idle", "Исполнитель операций ожидает команду"], "meaning": ["This handler has no active operation. It does not alone prove that global Auto is off or either channel is unhealthy.", "У этого исполнителя нет активной операции. Это само по себе не доказывает выключение общего Auto или неисправность канала."], "level": "ok"}, "UNCONFIRMED": {"code": "EVENT-RESULT-NEEDS-VERIFICATION", "label": ["Verify the result", "Нужна проверка результата"], "message": ["The operation result has not been verified", "Фактический результат операции ещё не проверен"], "meaning": ["The saved data does not confirm actual completion. Inspect current state before repeating the action; do not invent successful routing.", "Сохранённые данные не подтверждают фактическое выполнение. Перед повтором сверьте текущее состояние; успешная маршрутизация не предполагается."], "level": "warning"}});
JOURNAL_TYPES["HELD-ON-RESERVE"]=JOURNAL_TYPES["STOPPED-ON-RESERVE"];
JOURNAL_TYPES.CHANNEL_SELECTION={code:'EVENT-CHANNEL-SELECTION',label:['Channel selection record','Запись выбора канала'],message:['The router recorded a channel selection operation','Роутер сохранил операцию выбора канала'],meaning:['The saved direction and completion describe this operation. A controller phase alone does not prove the selected route or independent LAN availability.','Сохранённые направление и завершение описывают эту операцию. Сам этап контроллера не доказывает выбранный маршрут или доступность независимого клиента LAN.'],level:'warning'};
JOURNAL_TYPES.POLICY_REAPPLY={code:'EVENT-POLICY-REAPPLY',label:['VPN rules applied again','Повторное применение правил VPN'],message:['The router applied VPN rules without changing channel order','Роутер повторно применил правила VPN без изменения порядка каналов'],meaning:['This is a rule application, not a channel switch or an internet availability result. Completion and the saved policy reason are separate facts.','Это применение правил, а не переключение канала или результат проверки интернета. Завершение и сохранённая причина проверки правил указываются отдельно.'],level:'warning'};
JOURNAL_TYPES.ROUTER_OBSERVATION={code:'EVENT-ROUTER-OBSERVATION',label:['Router state observation','Наблюдение состояния роутера'],message:['Router control state was recorded; no channel switch is claimed','Сохранено состояние управления роутера; переключение канала не заявлено'],meaning:['This observation did not record a channel-order change. Use the saved event-time selection evidence rather than interpreting the controller phase as a new switch.','В этом наблюдении смена порядка каналов не записана. Используйте сохранённое подтверждение выбора на момент события; этап контроллера не считается новым переключением.'],level:'ok'};
JOURNAL_TYPES.DIRECTION_NOT_SAVED={code:'EVENT-DIRECTION-NOT-SAVED',label:['Switch direction not recorded','Направление перехода не сохранено'],message:['The saved data does not establish the direction of this operation','Сохранённые данные не подтверждают направление этой операции'],meaning:['The event lacks valid explicit source or destination metadata. The current pair and controller phase are not used to invent the missing direction.','В событии нет корректно сохранённых исходного канала или назначения. Текущая пара и этап контроллера не используются для выдумывания направления.'],level:'warning'};
function journalCodeRow(code){
  if(typeof ERROR_ROWS==='undefined'||typeof code!=='string')return null;
  return ERROR_ROWS.find(function(r){return r[0]===code;})||ERROR_ROWS.find(function(r){return r[0].endsWith('*')&&code.indexOf(r[0].slice(0,-1))===0;})||null;
}
JOURNAL_TYPES.STARTING={code:'EVENT-START-CONFIRMATION-PENDING',label:['Start awaiting confirmation','Запуск ожидает подтверждения'],message:['Start accepted; waiting for the controller','Запрос включения принят; ожидается подтверждение контроллера'],meaning:['The Start request is recorded while the previous stopped state is still visible. This is not another Stop command.','Запрос Start сохранён, пока ещё видно прежнее остановленное состояние. Это ожидание запуска, а не новая команда Stop.'],level:'warning'};
JOURNAL_TYPES.VENDOR_WAIT={code:'EVENT-VENDOR-WAIT',label:['Waiting for router operation','Ожидание операции роутера'],message:['Waiting for the stock network operation or lock to clear','Ожидание завершения штатной сетевой операции или снятия её блокировки'],meaning:['A GL.iNet worker or lock was observed. The controller defers switching decisions until it clears; the record alone does not establish a VPN outage. The exact worker may not have been retained.','Обнаружен обработчик или блокировка GL.iNet. Контроллер временно откладывает решения о переключении; сама запись не подтверждает отказ VPN. Конкретный обработчик мог не сохраниться в истории.'],level:'warning'};
function journalDefinition(entry){
  var transition=savedTransition(entry);
  if(transition.present){
    if(transition.outcome==='refused')return Object.assign({},JOURNAL_TYPES.CHANNEL_SELECTION,{level:'warning'});
    if(transition.reapply)return JOURNAL_TYPES.POLICY_REAPPLY;
    if(transition.unchanged)return JOURNAL_TYPES.ROUTER_OBSERVATION;
    if(!transition.to)return JOURNAL_TYPES.DIRECTION_NOT_SAVED;
    return Object.assign({},JOURNAL_TYPES.CHANNEL_SELECTION,{level:transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0?'ok':'warning'});
  }
  if(entry.state==='BLOCKED'&&entry.code==='VENDOR-WORKER-BUSY')return JOURNAL_TYPES.VENDOR_WAIT;
  if((entry.state==='OK'||entry.code==='OK')&&(entry.state==='FAILURE'||entry.kind==='FAILURE'||entry.state==='OK'&&entry.code&&entry.code!=='OK'&&entry.level==='error'))return JOURNAL_TYPES.CONFLICT;
  if(entry.return_primary===true||entry.state==='ROLLED-BACK'&&entry.original_restored===true)return JOURNAL_TYPES.RETURNED;
  if(JOURNAL_TYPES[entry.state])return JOURNAL_TYPES[entry.state];
  if(JOURNAL_TYPES[entry.kind])return JOURNAL_TYPES[entry.kind];
  if(entry.code==='OK')return JOURNAL_TYPES.OK;
  var r=journalCodeRow(entry.code||entry.state);
  return r?{code:r[0],label:[r[2],r[3]],message:[r[2],r[3]],meaning:[r[4]||'Open this code to load its detailed explanation.',r[5]||'Откройте этот код для загрузки подробного объяснения.'],level:entry.level}:JOURNAL_TYPES.LEGACY;
}
function journalStateText(entry){var t=journalDefinition(entry);return bi(t.label[0],t.label[1]);}
function ensureJournalDictionary(){
  if(typeof ERROR_ROWS==='undefined'||typeof ERROR_GROUPS==='undefined'||typeof ERROR_GROUP_OF==='undefined')return;
  if(!ERROR_GROUPS.some(function(g){return g[0]==='journal';}))ERROR_GROUPS.unshift(['journal',['Events and states','События и состояния']]);
  Object.keys(JOURNAL_TYPES).forEach(function(key){var t=JOURNAL_TYPES[key];if(!ERROR_ROWS.some(function(r){return r[0]===t.code;}))ERROR_ROWS.push([t.code,'journal',t.label[0],t.label[1],t.meaning[0],t.meaning[1],t.message[0]+'. Read the separate saved reason code if present; observation and a confirmed route change are different.',t.message[1]+'. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.']);ERROR_GROUP_OF[t.code]='journal';});
  ['OPERATOR-MANUAL','OPERATOR-RETURN'].forEach(function(code){var r=ERROR_ROWS.find(function(r){return r[0]===code;});if(r){r[2]=code==='OPERATOR-MANUAL'?'Manual-channel control command':'Return-control command';r[3]=code==='OPERATOR-MANUAL'?'Команда ручного выбора канала':'Команда возврата маршрута';r[4]='This is the manual-control command family, not proof that a human clicked. The recorded initiator distinguishes operator, automation, test or programmatic access.';r[5]='Это семейство команд ручного управления, а не доказательство нажатия человеком. Сохранённый инициатор различает оператора, автоматику, тест или программный доступ.';}});
}
function journalDescriptionLink(entry,status,stateOnly,extra){
  var t=journalDefinition(entry),code=t.code;
  if(!stateOnly)return E('span',{'class':'hv-journal-description'},journalMessage(entry,status,true)+(extra||''));
  return E('a',{'href':'#events','class':'hv-errlink hv-journal-state','data-journal-description':code,'data-original-state':entry.state,'title':bi('Open the event explanation','Открыть расшифровку события'),'click':function(ev){ev.preventDefault();ensureJournalDictionary();showErrorCode(code);}},(stateOnly?journalStateText(entry):journalMessage(entry,status,true))+(extra||''));
}
/* Shared real-event vocabulary for the live terminal and persisted history. */
var EVENT_VIEW={query:'',sort:'time',desc:true,expanded:false,page:0,stored:null,busy:false,error:null,request:0};
function journalHistoryDays(status){
  var values=[((status.accounting||{}).reliability||{}).detail_days,(status.native_history||{}).detail_days].filter(function(n){return Number.isInteger(n)&&n>=1&&n<=7;});
  return values.length?Math.min.apply(Math,values):7;
}
function renderChannelBadge(model){
  if(!model)return null;
  var main=bi('Main channel','Основной канал'),reserve=bi('Reserve channel','Резервный канал');
  var label=model.phase==='confirmed'?bi('Confirmed transition: ','Подтверждённый переход: '):model.phase==='pending'?bi('Switching in progress: ','Идёт переключение: '):model.phase==='failed'?bi('Connection failed: ','Ошибка соединения: '):bi('Connection recovered: ','Соединение восстановлено: ');
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
  var transition=savedTransition(entry);
  if(transition.present){
    if(!transition.to||!transition.changed||transition.unchanged||transition.reapply||transition.outcome==='refused')return null;
    if(transition.completed&&['committed','restored'].indexOf(transition.outcome)>=0)return {phase:'confirmed',from:transition.from,to:transition.to};
    if(!transition.completed&&['APPLYING','WAIT-CLIENT','ARMED','RESTORING'].indexOf(entry.state)>=0)return {phase:'pending',from:transition.from,to:transition.to};
    return null;
  }
  var pair=entry.source&&entry.target&&entry.source!==entry.target;
  if(pair&&['APPLYING','WAIT-CLIENT','ARMED'].indexOf(entry.state)>=0)return {phase:'pending',from:'source',to:'target'};
  if(pair&&entry.state==='RESTORING')return {phase:'pending',from:'target',to:'source'};
  if(pair&&(entry.return_primary===true||entry.state==='ROLLED-BACK'&&entry.original_restored===true))return {phase:'confirmed',from:'target',to:'source'};
  if(pair&&['COMMITTED','STOPPED-ON-RESERVE'].indexOf(entry.state)>=0)return {phase:'confirmed',from:'source',to:'target'};
  if(['source','target'].indexOf(entry.role)>=0){
    if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')return {phase:'recovered',to:entry.role};
    if(entry.state==='FAILURE'||entry.kind==='FAILURE'||entry.level==='error')return {phase:'failed',to:entry.role};
  }
  return null;
}
function renderJournalChannelBadge(entry){return renderChannelBadge(journalChannelModel(entry));}
function journalSourceLabel(source){
  return source==='manual'?bi('you, manually','вы, вручную'):source==='automatic'?bi('Auto, automatically','Auto, автоматически'):source==='test'?bi('programmatic test','тестовая программа — автоматически'):source==='programmatic'?bi('program command','команда программы'):bi('source not recorded','источник не указан');
}
function journalToken(value,fallback){return typeof value==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,95}$/.test(value)?value.toUpperCase():fallback;}
function journalLatencySample(raw,profile,eventTime){
  if(typeof profile!=='string'||!/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(profile)||!raw||typeof raw!=='object'||raw.profile!==profile||raw.metric!=='https-rtt-ms'||!Number.isFinite(eventTime)||!Number.isFinite(raw.time)||raw.time<eventTime-90||raw.time>eventTime+5||!Number.isFinite(raw.rtt_ms)||raw.rtt_ms<0||raw.rtt_ms>600000||typeof raw.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(raw.interface)||(profile.indexOf('wireguard:')===0)!==(raw.interface.indexOf('wgclient')===0)||typeof raw.generation!=='string'||!/^[a-f0-9]{32}$/.test(raw.generation))return null;
  return {profile:profile,metric:'https-rtt-ms',time:raw.time,rtt_ms:raw.rtt_ms,interface:raw.interface,generation:raw.generation};
}
function journalWebsiteSample(raw,profile,time){
  if(typeof profile!=='string'||!/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(profile)||!raw||raw.profile!==profile||raw.metric!==WEBSITE_METRIC||raw.target_set!==WEBSITE_TARGET_SET||['ok','partial','failed'].indexOf(raw.state)<0||!Number.isInteger(raw.successes)||raw.successes<0||raw.successes>3||raw.attempted!==3||!Number.isFinite(raw.time)||!Number.isFinite(time)||time-raw.time< -5||time-raw.time>45||typeof raw.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(raw.interface)||(profile.indexOf('wireguard:')===0)!==(raw.interface.indexOf('wgclient')===0)||typeof raw.generation!=='string'||!/^[a-f0-9]{32}$/.test(raw.generation)||raw.vendor_tunnel_id!==(raw.interface.indexOf('wgclient')===0?'wireguard:':'openvpn:')+raw.interface||!Array.isArray(raw.site_ms)||raw.site_ms.length!==3||!raw.site_ms.every(function(v){return v===null||Number.isFinite(v)&&v>=0&&v<=6000;})||raw.site_ms.filter(function(v){return v!==null;}).length!==raw.successes)return null;
  if(raw.successes===3){if(raw.state!=='ok'||!Number.isFinite(raw.avg_ms)||raw.avg_ms<0||raw.avg_ms>6000||Math.abs(raw.avg_ms-raw.site_ms.reduce(function(a,b){return a+b;},0)/3)>.051)return null;}
  else if(raw.avg_ms!=null||raw.state!==(raw.successes?'partial':'failed'))return null;
  return {rtt_ms:raw.successes===3?raw.avg_ms:null,time:raw.time,successes:raw.successes};
}
function journalLatencyText(entry){
  var transition=savedTransition(entry),reverse=['RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0||entry.return_primary===true,profile=transition.present?(transition.changed&&!transition.reapply&&transition.to?entry[transition.to]:null):reverse?entry.source:entry.target;
  if(entry.website_response){var web=journalWebsiteSample(entry.website_response,profile,entry.time);return web&&web.rtt_ms!==null?bi('Three-site response: ','Ответ трёх сайтов: ')+websiteMs(web.rtt_ms)+' '+bi('ms','мс'):bi('Three-site response: —','Ответ трёх сайтов: —')+(web?' · '+web.successes+'/3':'');}
  var sample=journalLatencySample(entry.latency,profile,entry.time);
  return sample?bi('Technical health HTTPS: ','Техническая HTTPS-проверка: ')+sample.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS')+' · '+bi('measured ','замер ')+new Date(sample.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit'}):bi('Delay: no saved measurement at this event','Задержка: нет сохранённого замера на момент события');
}
function journalCurrentLatency(p,status,now){var model=channelPingModel(p,status,now);return model.rtt_ms===null?null:{profile:p.id,metric:WEBSITE_METRIC,time:p.website_response.time,rtt_ms:model.rtt_ms,interface:p.interface,generation:p.vendor_generation};}
function journalMessage(entry,status,hideCode){
  var t=journalDefinition(entry),text=bi(t.message[0],t.message[1]);
  var profiles=Array.isArray(status.profiles)?status.profiles:[],p=profiles.find(function(p){return p.id===entry.profile;});
  if(entry.code==='VPN-003'&&entry.probe)text=entry.probe.https_success>0?bi('HTTPS checks passed partially; some traffic is passing','HTTPS-проверки прошли частично; часть трафика проходит'):bi('HTTPS availability was not confirmed by this check','Эта проверка не подтвердила HTTPS-доступность');
  if(entry.state==='RECOVERY'||entry.kind==='RECOVERY')text=entry.role==='source'?bi('Connection restored on the primary channel','Соединение восстановлено на основном канале'):entry.role==='target'?bi('Connection restored on the reserve channel','Соединение восстановлено на резервном канале'):bi('Connection restored · channel was not saved in this record','Соединение восстановлено · канал не сохранён в этой записи');
  else if(entry.profile)text=(entry.role==='source'?bi('Primary channel','Основной канал'):entry.role==='target'?bi('Reserve channel','Резервный канал'):bi('VPN profile','VPN-профиль'))+' — '+text;
  var transition=savedTransition(entry);
  if(transition.present){
    var names={source:bi('primary','основной'),target:bi('reserve','резервный')},direction=transition.to?(transition.changed&&transition.from?names[transition.from]+' → '+names[transition.to]:names[transition.to]):null;
    if(transition.outcome==='refused')text=bi('Channel selection request was refused','Запрос выбора канала отклонён')+(transition.to?' · '+names[transition.to]:'');
    else if(transition.reapply)text=transition.completed&&transition.outcome==='policy-verified'?bi('VPN rules verified; channel order unchanged','Правила VPN проверены; порядок каналов не изменился'):bi('Applying VPN rules again; no channel switch is claimed','Повторное применение правил VPN; переключение канала не заявлено');
    else if(transition.unchanged)text=bi('Router state observation; no channel switch recorded','Наблюдение состояния роутера; переключение канала не записано');
    else if(!direction)text=bi('Switch direction was not saved; see the recorded reason','Направление перехода не сохранено; смотрите записанную причину');
    else if(transition.completed&&transition.outcome==='restored')text=bi('Return confirmed: ','Возврат подтверждён: ')+direction;
    else if(transition.completed&&transition.outcome==='committed')text=(transition.changed&&transition.from?bi('Switch confirmed: ','Переход подтверждён: '):bi('Channel selected: ','Выбран канал: '))+direction;
    else text=(transition.changed&&transition.from?bi('Switch requested: ','Запрошен переход: '):bi('Channel selection requested: ','Запрошен выбор канала: '))+direction;
  }else{
    if(entry.state==='APPLYING')text=bi('Switch: primary → reserve','Переход: основной → резервный');
    if(entry.state==='RESTORING')text=bi('Switch: reserve → primary','Переход: резервный → основной');
    if(entry.return_primary)text=bi('Returned: reserve → primary','Возврат: резервный → основной');
  }
  var sourced=transition.present&&transition.changed||entry.origin==='control'||entry.action_source||['APPLYING','RESTORING','COMMITTED','ROLLED-BACK','STOPPED'].indexOf(entry.state)>=0;
  var switching=transition.present?transition.changed&&!transition.reapply&&transition.outcome!=='refused':entry.return_primary===true||['APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE','RESTORING','ROLLED-BACK'].indexOf(entry.state)>=0;
  var code=!hideCode&&entry.code&&entry.code!=='OK'&&entry.code!==entry.state?' · '+entry.code:'';
  if(entry.probe){
    text+=' · HTTPS '+entry.probe.https_success+'/3 · '+(entry.probe.dns_ok===true?bi('DNS passed','DNS прошёл'):entry.probe.dns_ok===false?bi('DNS failed','DNS не прошёл'):bi('DNS result unavailable','Результат DNS не сохранён'));
    entry.probe.checks.filter(function(c){return c.result==='http-unsupported';}).forEach(function(c){text+=' · '+bi('Check endpoint incompatible: ','Несовместимый проверочный адрес: ')+c.target+(c.http_status?' (HTTP '+c.http_status+')':'');});
  }
  return text+(entry.profile?' · '+(p?serverTitle(p):entry.profile):'')+(sourced?' · '+journalSourceLabel(entry.action_source):'')+(switching?' · '+journalLatencyText(entry):'')+code;
}
function journalDescriptionContent(entry,status,extra){
  var nodes=[journalDescriptionLink(entry,status,false,extra),' · ',E('a',{'href':'#events','class':'hv-errlink','data-journal-code':journalDefinition(entry).code,'title':bi('Open the event explanation','Открыть расшифровку события'),'click':function(ev){ev.preventDefault();ensureJournalDictionary();showErrorCode(journalDefinition(entry).code);}},journalDefinition(entry).code)];
  if(entry.code&&entry.code!=='OK'&&entry.code!==journalDefinition(entry).code){
    var known=journalCodeRow(entry.code),target=known?known[0]:journalDefinition(entry).code;
    nodes.push(' · ',E('a',{'href':'#events','class':'hv-errlink','data-journal-cause':target,'title':bi('Explain the recorded diagnostic code','Расшифровать сохранённый диагностический код'),'click':function(ev){ev.preventDefault();ensureJournalDictionary();showErrorCode(target);}},entry.code));
  }
  return E('span',{'class':'hv-journal-description-content'},nodes);
}
function journalProbeSnapshot(e,profile,status,code){
  if(!code&&(e.kind==='FAILURE'||e.state==='FAILURE'))return null;
  if(!profile||['VPN-001','VPN-003','DNS-001','OK',null].indexOf(code)<0)return null;
  var expected=code==='OK'?null:code;
  function sameCode(r){return (r.code==='OK'?null:r.code||null)===expected;}
  function count(r){return Number.isInteger(r.https_success)&&r.https_success>=0&&r.https_success<=3;}
  var stamp=Number.isFinite(e.measurement_time)&&e.measurement_time>0&&e.measurement_time<=e.time+5?e.measurement_time:null;
  var row=stamp!==null&&count(e)?e:null;
  if(!row){
    var snapshots=(status.events||[]).filter(function(r){return r.profile===profile&&sameCode(r)&&count(r)&&Number.isFinite(r.measurement_time)&&Math.abs(r.measurement_time-(stamp===null?e.time:stamp))<.001;});
    if(snapshots.length===1){row=snapshots[0];stamp=row.measurement_time;}
  }
  if(!row){
    var samples=(status.samples||[]).filter(function(r){return r.id===profile&&sameCode(r)&&count(r)&&Number.isFinite(r.time)&&(stamp!==null?Math.abs(r.time-stamp)<.001:r.time<=e.time+.001&&e.time-r.time<=10);});
    var exact=samples.filter(function(r){return Math.abs(r.time-e.time)<.001;});if(exact.length===1)samples=exact;
    if(samples.length===1){row=samples[0];stamp=row.time;}
  }
  if(!row)return null;
  var checks=(Array.isArray(row.probe_checks)?row.probe_checks:[]).slice(0,3).filter(function(r){return r&&['one.one.one.one','dns.google','dns.quad9.net'].indexOf(r.target)>=0&&['ok','http-unsupported','http-error','timeout','tls-error','transport-error','invalid-response','unknown'].indexOf(r.result)>=0;}).map(function(r){return {target:r.target,result:r.result,http_status:Number.isInteger(r.http_status)&&r.http_status>=100&&r.http_status<=599?r.http_status:null};});
  return {time:stamp,https_success:row.https_success,dns_ok:typeof row.dns_ok==='boolean'?row.dns_ok:null,checks:checks};
}
function journalRows(status,stored,now){
  var retainedSeconds=journalHistoryDays(status)*86400;
  var groups=[['controller',stored?stored.controller.events:(status.native_history||{}).events||[]],['failures',stored?stored.failures.events:((status.accounting||{}).reliability||{}).events||[]],['monitor',stored?[]:status.events||[]]],result=[],seen=Object.create(null);
  function control(action,stamp,source){
    if(['start','stop'].indexOf(action)<0||!Number.isFinite(stamp)||stamp<=0||stamp<now-retainedSeconds||stamp>now+5)return;
    var key='control:'+action+':'+stamp;if(seen[key])return;seen[key]=true;
    result.push({key:key,time:stamp,state:action==='start'?'AUTO-START-REQUESTED':'AUTO-STOP-REQUESTED',kind:'CONTROL',profile:null,code:null,level:'warning',origin:'control',action_source:['manual','automatic','test','programmatic'].indexOf(source)>=0?source:'unknown'});
  }
  groups.forEach(function(group){if(!Array.isArray(group[1]))return;
    group[1].slice(-10000).forEach(function(e){
      if(!e||!Number.isFinite(e.time)||e.time<now-retainedSeconds||e.time>now+5)return;
      control(e.control_action,e.control_time,e.control_source);
      var state=journalToken(e.state||e.kind||e.code,'OBSERVATION'),code=typeof e.code==='string'&&safeCode(e.code)?e.code:Array.isArray(e.codes)?e.codes.find(safeCode)||null:null;
      var profile=typeof(e.profile||e.id)==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e.profile||e.id)?e.profile||e.id:null;
      if(state==='STOPPED'&&e.control_action==='start'&&Number.isFinite(e.control_time)&&e.control_time<=e.time&&e.time-e.control_time<=30){state='STARTING';if(code==='CLIENT-STOP')code=Array.isArray(e.codes)?e.codes.find(function(c){return c!=='CLIENT-STOP'&&safeCode(c);})||null:null;}
      var probe=journalProbeSnapshot(e,profile,status,code);
      var family=state==='FAILURE'||['VPN-001','VPN-003','DNS-001'].indexOf(code)>=0?'failure':state==='RECOVERY'||code==='OK'?'recovery':null;
      var key=probe&&family?'measurement:'+profile+':'+probe.time+':'+family:group[0]+':'+(Number.isSafeInteger(e.sequence)?e.sequence:[e.time,profile,state,code].join(':'));
      if(seen[key])return;seen[key]=true;
      var failed=/FAIL|REFUS|ERROR|DEGRADED/.test(state)||!!code&&/^(DNS-|VPN-|SYSTEM-|CHECK-)|FAILED|ERROR|REFUSED/.test(code),level=failed?'error':/GAP|UNKNOWN|UNCONFIRMED|UNAVAILABLE|UNVERIFIED|CANCEL|INACTIVE/.test(state+' '+(code||''))?'warning':'ok';
      var pair={};['source','target'].forEach(function(k){pair[k]=typeof e[k]==='string'&&/^(openvpn|wireguard):[A-Za-z0-9_.:-]{1,80}$/.test(e[k])?e[k]:null;});
      var actionSource=['manual','automatic','test','programmatic','unknown'].indexOf(e.transition_source)>=0?e.transition_source:e.manual===true?'unknown':e.trial===true?'test':null;
      if(!actionSource&&Array.isArray(e.codes)){
        if(e.codes.some(function(c){return c==='OPERATOR-MANUAL'||c==='OPERATOR-RETURN';}))actionSource='unknown';
        else if(e.codes.some(function(c){return c==='OPERATOR-TRIAL'||c==='TRIAL-PASSED';}))actionSource='test';
        else if(e.codes.some(function(c){return ['SOURCE-FAILED','PRIMARY-STABLY-RECOVERED','RESERVE-FAILED-PRIMARY-VERIFIED'].indexOf(c)>=0;}))actionSource='automatic';
      }
      if(!actionSource&&state==='STOPPED'&&e.control_action==='stop')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      if(!actionSource&&state==='STARTING'&&e.control_action==='start')actionSource=['manual','test','programmatic'].indexOf(e.control_source)>=0?e.control_source:'unknown';
      var returnPrimary=state==='STOPPED'&&Array.isArray(e.codes)&&e.codes.indexOf('OPERATOR-RETURN')>=0;
      var transition=savedTransition(e),delayProfile=transition.present?(transition.changed&&!transition.reapply&&transition.to?pair[transition.to]:null):(returnPrimary||['RESTORING','ROLLED-BACK'].indexOf(state)>=0)?pair.source:pair.target;
      var role=['source','target'].indexOf(e.role)>=0?e.role:null;
      if(!role&&profile&&pair.source&&pair.target&&pair.source!==pair.target)role=profile===pair.source?'source':profile===pair.target?'target':null;
      var record={key:key,time:e.time,state:state,kind:journalToken(e.kind,'OBSERVATION'),code:code,profile:profile,role:role,source:pair.source,target:pair.target,original_restored:e.original_restored===true,return_primary:returnPrimary,latency:journalLatencySample(e.latency,delayProfile,e.time),action_source:actionSource,level:level,origin:group[0],probe:probe};
      if(Object.prototype.hasOwnProperty.call(e,'website_response')){
        record.website_response={};if(journalWebsiteSample(e.website_response,delayProfile,e.time)){['profile','metric','target_set','state','time','avg_ms','successes','attempted','interface','generation','vendor_tunnel_id'].forEach(function(k){record.website_response[k]=e.website_response[k];});record.website_response.site_ms=e.website_response.site_ms.slice();}
      }
      if(transition.present){
        record.transition_metadata_present=true;
        ['from_role','destination_role','before_policy_role'].forEach(function(key){if(e[key]==='source'||e[key]==='target')record[key]=e[key];});
        ['from_profile_id','destination_profile_id'].forEach(function(key){if(typeof e[key]==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(e[key]))record[key]=e[key];});
        ['route_changed','transition_completed','activation_reapply'].forEach(function(key){if(typeof e[key]==='boolean')record[key]=e[key];});
        if(['committed','restored','refused','policy-verified'].indexOf(e.transition_outcome)>=0)record.transition_outcome=e.transition_outcome;
        record.return_primary=transition.completed&&transition.outcome==='restored'&&transition.to==='source';
      }
      var definition=journalDefinition(record);if(!(definition.code==='EVENT-DETAILS-NOT-SAVED'&&record.level==='error'))record.level=definition.level||record.level;result.push(record);
    });
  });
  var request=status.auto_control||{};
  if(request.requested==='on'||request.requested==='off')control(request.request_action,request.requested_at,request.request_source);
  return result.sort(function(a,b){return b.time-a.time||a.key.localeCompare(b.key);});
}
function filteredJournalRows(rows,status,query,sort,desc){
  var needle=String(query||'').trim().toLocaleLowerCase();
  return rows.filter(function(row){return !needle||[row.state,journalStateText(row),row.kind,row.code,row.profile,row.origin,journalMessage(row,status),new Date(row.time*1000).toLocaleString()].join(' ').toLocaleLowerCase().includes(needle);}).sort(function(a,b){var compared=sort==='state'?journalStateText(a).localeCompare(journalStateText(b)):a.time-b.time;return (desc?-compared:compared)||b.time-a.time||a.key.localeCompare(b.key);});
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
      E('tbody',{},selected.map(function(row){return E('tr',{'data-event-key':row.key},[E('td',{},new Date(row.time*1000).toLocaleString()),E('td',{},[renderJournalChannelBadge(row),journalDescriptionLink(row,status,true)].filter(Boolean)),E('td',{},journalDescriptionContent(row,status))]);}))]);
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
    note.textContent=EVENT_VIEW.busy?bi('Reading saved history…','Чтение сохранённой истории…'):EVENT_VIEW.error||(!EVENT_VIEW.stored?bi('Showing recent events. Press "More history" to see all.','Показаны последние события. Чтобы увидеть все, нажмите «Остальная история».'):bi('Search and sorting cover the full downloaded retained snapshot. Storage/count limits and unobserved gaps remain explicit.','Поиск и сортировка охватывают весь загруженный снимок за выбранный срок. Ограничения хранения и пропуски сохраняются.'));
    if(EVENT_VIEW.stored){
      var records=[EVENT_VIEW.stored.controller,EVENT_VIEW.stored.failures],limited=records.some(function(r){var s=r.summary||{};return r.storage_notice||s.details_dropped>0||s.detail_budget_dropped>0||s.weekly_detail_complete===false;});
      if(limited)note.textContent+=' '+bi('Some saved details are unavailable or were dropped by the storage limit. This is not a complete record of every event.','Часть сохранённых подробностей недоступна или удалена по лимиту хранилища. Это не полный список всех произошедших событий.');
    }
  }
  host.appendChild(E('h3',{},bi('Events and errors: saved history','События и ошибки: сохранённая история')));host.appendChild(E('div',{'class':'hv-native-actions'},[query,order,direction]));host.appendChild(note);host.appendChild(tableHost);host.appendChild(more);
  host.appendChild(E('small',{},bi('The live terminal shows these real observations as they arrive. Its one-second screen heartbeat is not a persisted router event. Detailed controller/failure records are retained for the configured 1–7 days within bounded stores.','Живой терминал показывает эти реальные наблюдения по мере получения. Секундный heartbeat экрана не является сохранённым событием роутера. Подробности контроллера/сбоев хранятся выбранные 1–7 дней в ограниченных журналах.')));EVENT_VIEW.root=host;EVENT_VIEW.draw=draw;draw();return host;
}
