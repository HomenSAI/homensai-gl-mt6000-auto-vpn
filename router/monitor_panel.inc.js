/* Monitor service card: a neutral start/stop button and a traffic light that says what the monitor is doing. */
var monitorHost=null,monitorBusy=false;
var MONITOR_LAMPS=['green','yellow','red'];
var MONITOR_CODES={
  'MONITOR-STOP-AUTO-FIRST':['Stop Auto first and wait until the router is back on the primary, then stop the monitor.','Сначала остановите Auto и дождитесь, пока роутер вернётся на основной, затем остановите мониторинг.'],
  'MONITOR-JOURNAL-UNVERIFIED':['The transaction journal could not be verified, so the monitor was not stopped. See Help.','Журнал транзакций не удалось проверить, поэтому мониторинг не остановлен. См. «Помощь».'],
  'MONITOR-SAVE-FAILED':['The setting could not be saved on the router.','Не удалось сохранить настройку на роутере.'],
  'MONITOR-SERVICE-UNCONFIRMED':['The setting was saved but the router did not confirm the service change. Check again in a minute.','Настройка сохранена, но роутер не подтвердил смену состояния службы. Проверьте через минуту.']
};
function monitorStartedRecently(now){
  try{var at=Number(window.sessionStorage.getItem('homensai-vpn-monitor-requested'));return Number.isFinite(at)&&at>0&&now-at>=0&&now-at<=90;}catch(e){return false;}
}
function monitorLightModel(status,inventory,now,recent){
  var settings=(inventory||{}).settings||{},enabled=settings.enabled===true;
  var age=Number.isFinite(status.time)?now-status.time:Infinity;
  var fresh=!status.rpc_error&&!status.error&&age>=-5&&age<=90;
  function out(key,lamp,icon,title,hint,code){return {key:key,lamp:lamp,icon:icon,title:title,hint:hint,code:code||null,enabled:enabled};}
  if(status.rpc_error)return out('problem','red','!',bi('Cannot read the monitor','Не удаётся прочитать мониторинг'),bi('The page could not get the status from the router. Reload the page and sign in again; see Help → “The page is old, empty or says the monitor is not running”.','Страница не смогла получить статус от роутера. Обновите страницу и войдите снова; см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'),'RPC-UNAVAILABLE');
  if(enabled&&fresh)return out('ok','green','✓',bi('Monitor is running','Мониторинг работает'),bi('Fresh data arrived '+Math.max(0,Math.round(age))+' s ago. Each connected VPN is checked about every '+(Number(settings.interval)||30)+' seconds.','Свежие данные пришли '+Math.max(0,Math.round(age))+' с назад. Каждый подключённый VPN проверяется примерно раз в '+(Number(settings.interval)||30)+' с.'));
  if(enabled&&(recent||(!status.error&&age<=300)))return out('transition','yellow','⟳',bi('Starting or catching up','Запускается или догоняет'),bi('The monitor is switched on and the first fresh data is not here yet. This takes up to a minute.','Мониторинг включён, первых свежих данных ещё нет. Это занимает до минуты.'));
  if(enabled)return out('problem','red','!',bi('Switched on, but not running','Включён, но не работает'),bi('The router program is not producing data. Press Stop and then Start; if that does not help see Help → “The page is old, empty or says the monitor is not running”.','Программа на роутере не выдаёт данные. Нажмите «Стоп», затем «Старт»; если не помогло, см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'),status.error||'STATUS-STALE');
  if(fresh)return out('transition','yellow','⟳',bi('Stopping','Останавливается'),bi('The monitor is switched off; the last data is still on screen. It stops within a minute.','Мониторинг выключен; на экране ещё последние данные. Он остановится в течение минуты.'));
  return out('off',null,'○',bi('Monitor is off','Мониторинг выключен'),bi('Nothing is being checked and no statistics are collected. Auto cannot work without the monitor.','Ничего не проверяется и статистика не собирается. Без мониторинга Auto работать не может.'));
}
function renderMonitorLight(light){
  var lamps=MONITOR_LAMPS.map(function(color){return E('span',{'class':'hv-lamp hv-lamp-'+color+(light.lamp===color?' hv-lamp-lit':''),'aria-hidden':'true'});});
  var legend=[['green','Green: running with fresh data','Зелёный: работает, данные свежие'],['yellow','Yellow: starting, stopping or catching up','Жёлтый: запускается, останавливается или догоняет'],['red','Red: switched on but not working, or unreadable','Красный: включён, но не работает, или не читается']].map(function(row){return E('li',{'class':light.lamp===row[0]?'hv-legend-current':''},[E('span',{'class':'hv-dot hv-dot-'+row[0],'aria-hidden':'true'}),bi(row[1],row[2])]);}).concat([E('li',{'class':light.lamp?'':'hv-legend-current'},[E('span',{'class':'hv-dot hv-dot-grey','aria-hidden':'true'}),bi('Grey: switched off','Серый: выключен')])]);
  return E('div',{'class':'hv-light-block'},[E('div',{'class':'hv-light hv-light-three hv-light-'+light.key,'role':'img','aria-label':light.title},lamps),E('div',{'class':'hv-light-text'},[E('strong',{'class':'hv-auto-label hv-light-title'},[E('span',{'class':'hv-light-icon','aria-hidden':'true'},light.icon+' '),light.title]),E('p',{'role':'status','aria-live':'polite'},light.hint),light.code?E('small',{'class':'hv-auto-tech'},bi('Technical state: ','Техническое состояние: ')+light.code):null,E('details',{'class':'hv-light-help'},[E('summary',{},bi('What do the colours mean?','Что означают цвета?')),E('ul',{'class':'hv-light-legend'},legend)])].filter(Boolean))]);
}
function fillMonitorCard(status,inventory){
  while(monitorHost.firstChild)monitorHost.removeChild(monitorHost.firstChild);
  var now=Date.now()/1000,light=monitorLightModel(status,inventory,now,monitorStartedRecently(now));
  var on=light.enabled;
  var button=E('button',{'type':'button','class':'hv-auto-power hv-auto-neutral'+(on?' hv-auto-armed':''),'aria-pressed':on?'true':'false','aria-label':on?bi('Stop the monitor','Остановить мониторинг'):bi('Start the monitor','Запустить мониторинг'),'click':function(){
    if(monitorBusy)return;monitorBusy=true;button.disabled=true;
    return rpc.declare({object:'homensai-vpn',reject:true,method:'monitor_control',params:['enabled'],expect:{}})(!on).then(function(result){
      if(result&&result.accepted===true){try{window.sessionStorage.setItem('homensai-vpn-monitor-requested',String(Date.now()/1000));}catch(e){}window.location.reload();return;}
      var code=result&&typeof result.code==='string'?result.code:'MONITOR-UNKNOWN',text=Object.prototype.hasOwnProperty.call(MONITOR_CODES,code)?bi(MONITOR_CODES[code][0],MONITOR_CODES[code][1]):'';
      ui.addNotification(null,E('p',{},code+(text?' · '+text:'')));
    }).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){monitorBusy=false;button.disabled=false;});
  }},E('span',{'class':'hv-power-symbol','aria-hidden':'true'}));
  monitorHost.appendChild(E('h3',{},bi('Monitor service','Служба мониторинга')));
  monitorHost.appendChild(E('div',{'class':'hv-auto-switch'},[E('div',{'class':'hv-auto-power-unit'},[button,E('span',{'class':'hv-auto-action'},on?bi('Stop','Стоп'):bi('Start','Старт'))]),renderMonitorLight(light)]));
  monitorHost.appendChild(E('p',{'class':'hv-auto-limit'},bi('The monitor checks your VPNs in the background and collects the statistics. Stop Auto and wait for it to hand control back before stopping the monitor.','Мониторинг в фоне проверяет ваши VPN и собирает статистику. Перед остановкой мониторинга остановите Auto и дождитесь, пока он вернёт управление.')));
}
function renderMonitorCard(status,inventory){
  monitorHost=E('section',{'class':'hv-chart-card hv-card-monitor'});fillMonitorCard(status,inventory);return monitorHost;
}
function updateMonitorCard(status,inventory){if(monitorHost&&!monitorBusy)fillMonitorCard(status,inventory);}
