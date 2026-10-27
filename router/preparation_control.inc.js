/* Only an explicit reviewed click invokes the narrowly scoped writer. */
var preparationPreviewCall=rpc.declare({object:'homensai-vpn',method:'preparation_preview',params:['action']});
var preparationApplyCall=rpc.declare({object:'homensai-vpn',method:'preparation_apply',params:['action','revision','control_revision']});
var preparationBusy=false,preparationDialog=0;
var PREPARATION_ACTIONS={
 'source-autostart':['Disable primary VPN startup','Отключить автозапуск основного VPN','Disable Bring up on boot for the currently selected primary VPN. The running VPN stays connected.','Отключить «Поднимать при загрузке» для текущего выбранного основного VPN. Работающий VPN остаётся подключённым.'],
 'target-autostart':['Disable reserve VPN startup','Отключить автозапуск резервного VPN','Disable Bring up on boot for the currently selected reserve VPN. The running VPN stays connected.','Отключить «Поднимать при загрузке» для текущего выбранного резервного VPN. Работающий VPN остаётся подключённым.'],
 'wg-autostart':['Disable WireGuard startup','Отключить автозапуск WireGuard','Disable Bring up on boot for WireGuard (wgclient1). The running VPN stays connected.','Отключить «Поднимать при загрузке» для WireGuard (wgclient1). Работающий VPN остаётся подключённым.'],
 'ovpn-autostart':['Disable OpenVPN startup','Отключить автозапуск OpenVPN','Disable Bring up on boot for OpenVPN (ovpnclient1). The running VPN stays connected.','Отключить «Поднимать при загрузке» для OpenVPN (ovpnclient1). Работающий VPN остаётся подключённым.'],
 'vpn-boot':['Disable stock VPN startup','Отключить штатный автозапуск VPN','Disable vpn-client startup when the router boots. The running service is not stopped.','Отключить запуск службы vpn-client при включении роутера. Работающая служба не останавливается.'],
 'sfe-boot':['Disable SFE startup','Отключить автозапуск SFE','Disable shortcut-fe startup when the router boots. Loaded acceleration remains until a deliberate router restart.','Отключить запуск shortcut-fe при включении роутера. Работающее ускорение сохранится до отдельной перезагрузки роутера.'],
 'hnat':['Disable hardware acceleration','Отключить аппаратное ускорение','Disable hardware acceleration in the saved settings and the running system. No network/firewall restart or module removal.','Выключить аппаратное ускорение в сохранённых настройках и в работающей системе. Без перезапуска сети/firewall и удаления модулей.'],
 'flow-offload':['Disable firewall offloading','Отключить ускорение firewall','Save both flow-offloading flags as 0. This does not reload the firewall. Auto remains blocked until a separate deliberate router restart applies the setting to live flows.','Сохранить оба флага flow offloading=0. Firewall не перезапускается. Auto останется заблокирован до отдельной перезагрузки роутера, которая применит настройку к действующим потокам.'],
 'sfe-autoload':['Disable SFE module autoload','Отключить автозагрузку модулей SFE','Disable loading SFE modules when the router boots and preserve the verified original startup file. Loaded modules are not forcibly removed.','Отключить загрузку модулей SFE при включении роутера и сохранить проверенный исходный файл запуска. Загруженные модули принудительно не удаляются.']
};
var PREPARATION_REASONS={
 'PREPARATION-STOP-AUTO-FIRST':['Stop Auto and wait for completed recovery before changing preparation.','Сначала остановите Auto и дождитесь завершения восстановления.'],
 'PREPARATION-RECOVERY-REQUIRED':['The previous session or an unconfirmed preparation write needs recovery. Existing changes and backups are retained.','Предыдущая сессия или неподтверждённое изменение подготовки требует восстановления. Изменения и исходные значения сохранены.'],
 'PREPARATION-STALE-REVIEW':['Settings or Auto controls changed after review. Review this action again.','Настройки или управление Auto изменились после просмотра. Проверьте действие заново.'],
 'PREPARATION-PLATFORM-UNVERIFIED':['This button requires a verified GL-MT3000/GL-MT6000 with firmware 4.11.0.','Кнопке нужен проверенный GL-MT3000/GL-MT6000 с прошивкой 4.11.0.'],
 'PREPARATION-HNAT-UNVERIFIED':['The hardware acceleration runtime hook cannot be safely verified. Use the linked GL.iNet settings.','Не удалось безопасно проверить работающий HNAT hook. Используйте ссылку на настройки GL.iNet.'],
 'PREPARATION-PENDING-OR-UNREADABLE':['There are unsaved router changes or settings cannot be read. Resolve them in the router panel first.','Есть несохранённые изменения роутера или настройки не читаются. Сначала проверьте их в панели роутера.'],
 'PREPARATION-WRITE-UNCONFIRMED':['The change could not be confirmed. Do not repeat it blindly; inspect recovery and the saved original values.','Изменение не подтверждено. Не повторяйте его вслепую; проверьте восстановление и сохранённые исходные значения.']
};
PREPARATION_REASONS['PREPARATION-RESTART-REQUIRED']=['The boot setting is saved. Restart this router deliberately before starting Auto; existing live flows/modules are not proof of the new state.','Настройка сохранена. Перед запуском Auto отдельно перезагрузите этот роутер: действующие потоки/модули ещё не подтверждают новое состояние.'];
Object.assign(PREPARATION_REASONS,{
 'PREPARATION-BACKUP-UNVERIFIED':['The original setting could not be safely preserved. Nothing new is applied.','Не удалось безопасно сохранить исходное значение. Новое изменение не применяется.'],
 'PREPARATION-BINDING-UNVERIFIED':['The named VPN interface is missing or has another protocol. Review its actual binding first.','Указанный VPN-интерфейс отсутствует или использует другой протокол. Сначала проверьте его привязку.'],
 'PREPARATION-BOOT-UNVERIFIED':['The startup link differs from the known service. It has not been removed.','Ссылка автозапуска не соответствует известной службе. Она не удалена.'],
 'PREPARATION-AUTOLOAD-UNVERIFIED':['The SFE file differs from the verified original, is missing, or a preserved copy already exists. Nothing is overwritten.','Файл SFE отличается от проверенного исходника, отсутствует либо сохранённая копия уже существует. Перезаписи нет.'],
 'PREPARATION-HISTORY-LIMIT':['The private preparation history is full. Preserve and review it before another change.','Приватная история подготовки заполнена. Сохраните и проверьте её до следующего изменения.'],
 'PREPARATION-EXTERNAL-CHANGE':['Another router configuration changed during this action. The result needs recovery review.','Во время действия изменилась другая конфигурация роутера. Результат требует проверки восстановления.']
});
function preparationReason(code){var row=PREPARATION_REASONS[code];return row?bi(row[0],row[1]):bi('The router refused this change; inspect the code and use the linked settings.','Роутер отказал в изменении; проверьте код и используйте ссылку на настройки.');}
function preparationActionsForCode(code){
 if(code==='PREP-SOURCE-AUTOSTART')return ['source-autostart'];
 if(code==='PREP-TARGET-AUTOSTART')return ['target-autostart'];
 var single={'PREP-WGCLIENT1-AUTOSTART':'wg-autostart','PREP-OVPNCLIENT1-AUTOSTART':'ovpn-autostart','PREP-STOCK-VPN-BOOT':'vpn-boot','PREP-SFE-BOOT':'sfe-boot','PREP-SFE-AUTOLOAD':'sfe-autoload','PREP-HNAT-CONFIG':'hnat','HARDWARE-ACCELERATOR-UNVERIFIED':'hnat','FLOW-OFFLOAD-ENABLED':'flow-offload'};
 if(code==='SOFTWARE-ACCELERATOR-UNVERIFIED'||code==='PREP-SFE-RUNTIME')return ['sfe-boot','sfe-autoload'];
 return Object.prototype.hasOwnProperty.call(single,code)?[single[code]]:[];
}
function preparationNotice(code,uncertain){
 ui.addNotification(null,E('p',{'role':'status'},[E('strong',{},code+' · '),preparationReason(code),uncertain?' '+bi('Some settings may already have changed; the durable recovery record is retained.','Часть настроек уже могла измениться; запись восстановления сохранена.'):'']));
}
function preparationReview(action,button){
 if(preparationBusy)return Promise.resolve();
 preparationBusy=true;button.disabled=true;button.setAttribute('aria-busy','true');
 var token=++preparationDialog;
 return preparationPreviewCall(action).then(function(plan){
  if(token!==preparationDialog)return;
  if(!plan||plan.accepted!==true){preparationNotice(plan&&plan.code||'PREPARATION-UNVERIFIED');return;}
  if(plan.action!==action||typeof plan.revision!=='string'||typeof plan.control_revision!=='string'||typeof plan.already_done!=='boolean'||!/^([a-f0-9]{64})$/.test(plan.revision)||!/^([a-f0-9]{32})$/.test(plan.control_revision)||['mt3000','mt6000'].indexOf(plan.board)<0)throw Error('PREPARATION-REPLY-INVALID');
  var description=PREPARATION_ACTIONS[action];
  var cancel=E('button',{'type':'button','class':'cbi-button','click':function(){preparationDialog++;ui.hideModal();}},bi('Cancel','Отмена'));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action','data-preparation-confirm':action,'click':function(){
   if(preparationBusy||token!==preparationDialog)return;
   preparationBusy=true;apply.disabled=true;cancel.disabled=true;apply.setAttribute('aria-busy','true');
   return preparationApplyCall(action,plan.revision,plan.control_revision).then(function(reply){
    if(!reply||reply.applied!==true||reply.verified!==true||reply.action!==action||reply.auto_started!==false){preparationNotice(reply&&reply.code||'PREPARATION-WRITE-UNCONFIRMED',reply&&reply.change_may_have_applied);return;}
    ui.addNotification(null,E('p',{'role':'status'},bi('The setting was read back and verified. Auto has not been started. Other prerequisites remain separate.','Настройка прочитана заново и проверена. Auto не запускался. Остальные условия проверяются отдельно.')+(reply.restart_required?' '+bi('Loaded acceleration/active flows still need a separate deliberate restart or apply.','Загруженному ускорению/действующим потокам ещё нужно отдельное применение или перезагрузка.') :'')));
   }).catch(function(){preparationNotice('PREPARATION-WRITE-UNCONFIRMED',true);}).finally(function(){preparationBusy=false;preparationDialog++;ui.hideModal();});
  }},bi('Apply this change','Применить это изменение'));
  ui.showModal(bi('Review router change','Проверьте изменение роутера'),[
   E('p',{},bi('This router: GL-','Этот роутер: GL-')+plan.board.toUpperCase()),E('h3',{},bi(description[0],description[1])),E('p',{},bi(description[2],description[3])),plan.interface?E('p',{},bi('Interface: ','Интерфейс: ')+plan.interface):null,
   E('p',{},bi('The original setting is saved privately on this router before writing. A changed review, active Auto or unfinished recovery refuses the write. Auto requires its own explicit Start.','Исходное значение сохраняется приватно в этом роутере до записи. Изменившиеся данные, активный Auto или незавершённое восстановление запрещают запись. Auto требует отдельного явного запуска.')),
   plan.already_done?E('p',{},bi('Already disabled; verified by a fresh read.','Уже отключено; подтверждено свежим чтением.')):null,
   E('div',{'class':'hv-wizard-actions'},[cancel,plan.already_done?null:apply].filter(Boolean))
  ].filter(Boolean));
 }).catch(function(){preparationNotice('PREPARATION-UNVERIFIED');}).finally(function(){preparationBusy=false;button.disabled=false;button.setAttribute('aria-busy','false');});
}
function renderPreparationButtons(code){
 var buttons=preparationActionsForCode(code).map(function(action){var text=PREPARATION_ACTIONS[action];var button=E('button',{'type':'button','class':'cbi-button','data-preparation-action':action,'click':function(){return preparationReview(action,button);}},bi(text[0],text[1]));return button;});
 return buttons.length?E('div',{'class':'hv-preparation-actions'},buttons):null;
}
