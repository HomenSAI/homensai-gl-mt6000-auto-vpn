/* Monitoring is always on. The Overview shows a block next to "Check the VPNs now": lamp, title and a few numbers.
   monitorLightModel() decides running / catching up / stopped; the block has a button only when monitoring is not running. */
var monitorBlockHost=null,monitorBusy=false;
var MONITOR_LAMPS=['green','yellow','red'];
function monitorStartedRecently(now){
  try{var at=Number(window.sessionStorage.getItem('homensai-vpn-monitor-requested'));return Number.isFinite(at)&&at>0&&now-at>=0&&now-at<=90;}catch(e){return false;}
}
function monitorLightModel(status,inventory,now,recent){
  var settings=(inventory||{}).settings||{},enabled=settings.enabled===true;
  var age=Number.isFinite(status.time)?now-status.time:Infinity;
  var fresh=!status.rpc_error&&!status.error&&(typeof observationFresh==='function'?observationFresh(status,now):age>=-5&&age<=90);
  function out(key,lamp,icon,title,hint,code){return {key:key,lamp:lamp,icon:icon,title:title,hint:hint,code:code||null,enabled:enabled};}
  if(!status.rpc_error&&status.speed_pause&&status.speed_pause.active&&status.speed_pause.monitor_paused)return out('transition','yellow','Ⅱ',bi('Monitoring paused for speed test','Мониторинг на паузе для теста скорости'),bi('A fresh check runs after the test, before Auto continues.','После теста выполнится свежая проверка, затем продолжит работу Auto.'));
  if(status.rpc_error)return out('problem','red','!',bi('Cannot read the monitor','Не удаётся прочитать мониторинг'),bi('The page could not get the status from the router. Reload the page and sign in again; see Help → “The page is old, empty or says the monitor is not running”.','Страница не смогла получить статус от роутера. Обновите страницу и войдите снова; см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'),'RPC-UNAVAILABLE');
  if(!status.rpc_error&&status.speed_pause&&status.speed_pause.active&&status.speed_pause.phase==='RESUMING')return out('transition','yellow','⟳',bi('Monitoring is resuming','Мониторинг возобновляется'),bi('Waiting for the first post-test observation.','Ожидается первая проверка после теста.'));
  if(enabled&&fresh)return out('ok','green','✓',bi('Monitor is running','Мониторинг работает'),bi('Fresh data arrived '+Math.max(0,Math.round(age))+' s ago. Each connected VPN is checked about every '+(Number(settings.interval)||10)+' seconds.','Свежие данные пришли '+Math.max(0,Math.round(age))+' с назад. Каждый подключённый VPN проверяется примерно раз в '+(Number(settings.interval)||10)+' с.'));
  if(enabled&&(recent||(!status.error&&age<=300)))return out('transition','yellow','⟳',bi('Starting or catching up','Запускается или догоняет'),bi('The monitor is switched on and the first fresh data is not here yet. This takes up to a minute.','Мониторинг включён, первых свежих данных ещё нет. Это занимает до минуты.'));
  if(enabled)return out('problem','red','!',bi('Switched on, but not running','Включён, но не работает'),bi('The router program is not producing data.','Программа на роутере не выдаёт данные.'),status.error||'STATUS-STALE');
  return out('problem','red','!',bi('Monitoring must be running','Мониторинг должен работать'),bi('Monitoring is required for Auto. Restore monitoring before starting automatic control.','Мониторинг необходим для Auto. Восстановите мониторинг перед запуском автоматического управления.'),'SERVICE-STOPPED');
}
// Numbers for the block: checks and failures of the last hour from the samples the monitor keeps.
function monitorNumbers(status,now){
  var samples=Array.isArray(status.samples)?status.samples:[];
  var recent=samples.filter(function(s){return Number.isFinite(s.time)&&now-s.time<=3600&&now-s.time>=-5;});
  var failed=recent.filter(function(s){return s.code;}).length;
  return {checks:recent.length,failed:failed,percent:recent.length?Math.round(100*(recent.length-failed)/recent.length):null};
}
function fillMonitorBlock(host,status,inventory){
  while(host.firstChild)host.removeChild(host.firstChild);
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),light=monitorLightModel(status,inventory,now,monitorStartedRecently(now)),n=monitorNumbers(status,now);
  var tone=light.key==='ok'?'green':light.key==='transition'?'yellow':light.key==='problem'?'red':'grey';
  var title=light.key==='ok'?bi('Monitoring is on','Мониторинг включён'):light.title;
  var stats=light.key==='ok'||n.checks
    ?bi(n.checks+' checks in the last hour · '+n.failed+' failed'+(n.percent==null?'':' · '+n.percent+'% passed'),n.checks+' проверок за час · не прошло '+n.failed+(n.percent==null?'':' · прошло '+n.percent+'%'))
    :light.hint;
  var button=null;
  if(light.key==='problem'||light.key==='off'){
    button=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
      if(monitorBusy)return;monitorBusy=true;button.disabled=true;
      return rpc.declare({object:'homensai-vpn',reject:true,method:'monitor_control',params:['enabled'],expect:{}})(true).then(function(result){
        if(result&&result.accepted===true){try{window.sessionStorage.setItem('homensai-vpn-monitor-requested',String((typeof statusNow==='function'?statusNow(status):Date.now()/1000)));}catch(e){}window.location.reload();return;}
        ui.addNotification(null,E('p',{},(result&&result.code)||'MONITOR-UNKNOWN'));
      }).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){monitorBusy=false;button.disabled=false;});
    }},bi('Restore monitoring','Восстановить мониторинг'));
  }
  host.appendChild(E('span',{'class':'hv-monitor-lamp hv-monitor-lamp-'+tone,'role':'img','aria-label':title}));
  host.appendChild(E('div',{'class':'hv-check-text'},[E('strong',{},title),E('small',{},stats),light.key==='ok'?E('small',{'class':'hv-check-status'},bi('Checks every '+(Number(((status||{}).probe_policy||{}).effective_interval)||Number((inventory.settings||{}).interval)||10)+' s · last data '+Math.max(0,Math.round(now-status.time))+' s ago','Проверка каждые '+(Number(((status||{}).probe_policy||{}).effective_interval)||Number((inventory.settings||{}).interval)||10)+' с · последние данные '+Math.max(0,Math.round(now-status.time))+' с назад')):null,button].filter(Boolean)));
}
function renderMonitorBlock(status,inventory){
  monitorBlockHost=E('section',{'class':'hv-connectivity-control hv-monitor-block'});
  fillMonitorBlock(monitorBlockHost,status,inventory);
  return monitorBlockHost;
}
// "About the statistics" card on the Statistics page: what is collected and where it is stored.
function renderMonitorInfo(status,inventory){
  var settings=(inventory||{}).settings||{};
  var every=Number(settings.checkpoint)>0?Math.round(Number(settings.checkpoint)/60):null;
  return E('section',{'class':'hv-chart-card'},[
    E('h3',{},bi('Where this statistics comes from','Откуда эта статистика')),
    E('p',{},bi('Monitoring is always on. About every '+(Number(settings.interval)||10)+' seconds it checks each connected VPN (can it open a website and resolve a name through it). From these checks the charts above are built: how fast each server answers, and how long each one worked or failed. History starts when monitoring first started; nothing is guessed for earlier time.','Мониторинг всегда включён. Примерно каждые '+(Number(settings.interval)||10)+' с он проверяет каждый подключённый VPN (может ли он открыть сайт и найти адрес). Из этих проверок построены графики выше: как быстро отвечает каждый сервер и сколько времени он работал или не работал. История начинается с первого запуска мониторинга; за более раннее время ничего не придумывается.')),
    E('p',{'class':'hv-ready-intro'},bi('Where it is stored: on the router itself, in /etc/homensai-vpn (saved '+(every?'about every '+every+' min':'periodically')+'; the interval can be changed in Settings → Advanced settings → Monitoring parameters). Nothing leaves the router.','Где хранится: на самом роутере, в /etc/homensai-vpn (сохраняется '+(every?'примерно раз в '+every+' мин':'периодически')+'; интервал можно изменить в «Настройки» → «Расширенные настройки» → «Параметры мониторинга»). Ничего не уходит с роутера.'))]);
}
// Monitoring page (opened from the sidebar lamp): small lamp, state, numbers of the last hour per channel.
function renderMonitorPage(status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),head=E('div',{'class':'hv-monitor-page-head'});
  fillMonitorBlock(head,status,inventory);
  var samples=Array.isArray(status.samples)?status.samples:[],ids=typeof rolePairIds==='function'?rolePairIds(status,inventory||{},now):[];
  var rows=ids.map(function(id,i){
    var mine=samples.filter(function(s){return s.id===id&&Number.isFinite(s.time)&&now-s.time<=3600&&now-s.time>=-5;}),bad=mine.filter(function(s){return s.code;}).length;
    var last=mine.length?mine[mine.length-1]:null;
    return E('tr',{},[E('th',{'scope':'row'},i===0?bi('Primary','Основной'):bi('Reserve','Резервный')),E('td',{},String(mine.length)),E('td',{},String(bad)),
      E('td',{},mine.length?Math.round(100*(mine.length-bad)/mine.length)+'%':'—'),E('td',{},last?new Date(last.time*1000).toLocaleTimeString():'—'),E('td',{},last&&last.code?last.code:bi('OK','OK'))]);
  });
  var p=status.probe_policy||{};
  return E('section',{'class':'hv-chart-card hv-monitor-page','data-monitor-page':'1'},[
    E('h3',{},bi('Monitoring','Мониторинг')),head,
    E('p',{'class':'hv-step-note'},bi('Probe level ','Уровень опроса ')+(p.level||'—')+' · '+bi('channel check every ','проверка каналов раз в ')+(p.effective_interval||'—')+bi(' s',' с')+' · '+bi('ping every ','пинг раз в ')+(p.effective_ping_interval||p.ping_interval||'—')+bi(' s',' с')+' · '+bi('websites every ','сайты раз в ')+(p.measure_interval||'—')+bi(' s',' с')+(p.boost_active?' · '+bi('boost active','идёт ускорение'):'')),
    E('table',{'class':'table hv-monitor-table','data-hv-no-sort':'1'},[E('tr',{},[bi('Channel','Канал'),bi('Checks in the last hour','Проверок за час'),bi('Failed','Не прошло'),bi('Passed','Прошло'),bi('Last check','Последняя проверка'),bi('Last result','Последний результат')].map(function(c){return E('th',{'scope':'col'},c);}))].concat(rows))]);
}
