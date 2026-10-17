"""HomenS.AI sidebar adapter over the pinned Style core and real LuCI monitor."""
from pathlib import Path

root=Path(__file__).parent/'files/www/luci-static/resources/view/homensai-vpn'
source=(root/'dashboard16.js').read_text(encoding='utf8')
source=source.replace("var locale = localStorage.getItem('homensai-vpn-language') || 'en';", """var savedLanguage='en';
try { savedLanguage=localStorage.getItem('homensai-vpn-language')||'en'; } catch(e) {}
var requestedLanguage=new URLSearchParams(window.location.search).get('lang');
var locale=(requestedLanguage||savedLanguage)==='ru'?'ru':'en';""")
source=source.replace('ui11.css','ui13.css').replace('ui12.css','ui13.css')
source=source.replace('Автоматическое изменение маршрутов пока недоступно.','Контролируемое переключение требует клиентской проверки.')
source=source.replace('Automatic route switching is unavailable.','Controlled failover requires client verification.')

anchor="    var panel=E('div',{'class':'hv-panel'}),self=this,period='day';"
assert anchor in source
source=source.replace(anchor,anchor+"""
    var appRoot=null,settingsHost=null,heading=null,sideState=null,versionBadge=null,pages={},sortStates={},searchTerms={};
    var tabs=[['overview','◉',bi('Overview','Обзор')],['channels','⇄',bi('Channels and servers','Каналы и серверы')],['statistics','▥',bi('Statistics','Статистика')],['ranking','↕',bi('Server ranking','Рейтинг серверов')],['traffic','◷',bi('Monthly traffic','Трафик за месяц')],['services','▣',bi('Service monitor','Монитор служб')],['events','≡',bi('Events and errors','События и ошибки')],['settings','⚙',bi('Settings','Настройки')]];
    function routerVpnUrl(){return resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);}
    function vpnSetupCard(){return E('section',{'class':'hv-chart-card hv-vpn-setup'},[E('div',{'class':'hv-auto-power-unit'},[E('a',{'class':'hv-auto-power hv-vpn-configure','href':routerVpnUrl()||null,'aria-disabled':routerVpnUrl()?null:'true','title':routerVpnUrl()?null:bi('Router address unavailable in this preview','Адрес роутера недоступен в этом просмотре'),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('Open router VPN settings (opens a new tab)','Открыть настройки VPN роутера (новая вкладка)')},E('span',{'aria-hidden':'true','class':'hv-configure-symbol'},'⚙')),E('strong',{'class':'hv-auto-action'},bi('Configure VPN','Настроить VPN'))]),E('p',{},bi('Add servers and connection keys in the router VPN Client Profile page. Monitoring and failover priorities are configured here.','Добавляйте серверы и ключи на странице VPN Client Profile роутера. Мониторинг и приоритеты переключения настраиваются здесь.'))]);}
    function validTab(key){return tabs.some(function(t){return t[0]===key;});}
    var activeTab=setup?'settings':window.location.hash.slice(1);if(!validTab(activeTab))activeTab='overview';
    function showPage(key){
      if(!validTab(key))key='overview';activeTab=key;
      var scope=appRoot||panel;scope.querySelectorAll('[data-hv-page]').forEach(function(node){node.hidden=node.getAttribute('data-hv-page')!==key;});
      if(appRoot)appRoot.querySelectorAll('[data-hv-tab]').forEach(function(node){node.setAttribute('aria-current',node.getAttribute('data-hv-tab')===key?'page':'false');});
      if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];
    }
    function put(key,node){
      if(!pages[key]){pages[key]=E('section',{'class':'hv-page','data-hv-page':key});panel.appendChild(pages[key]);}
      pages[key].appendChild(node);return node;
    }
    function sortableTables(){
      panel.querySelectorAll('table').forEach(function(table,index){
        var tableKey=(table.closest('[data-hv-page]')||{dataset:{hvPage:'overview'}}).dataset.hvPage+'-'+index,headers=table.querySelectorAll('tr:first-child th');
        function applySort(column,direction){
          var entries=Array.prototype.slice.call(table.querySelectorAll('tr')).slice(1).map(function(row,i){return {row:row,i:i,value:row.children[column]?(row.children[column].getAttribute('data-sort-value')||row.children[column].textContent||''):''};});
          function unknown(v){return !v||/^(—|No data|Нет данных)$/.test(v.trim());}
          entries.sort(function(a,b){if(unknown(a.value)!==unknown(b.value))return unknown(a.value)?1:-1;var x=a.value.trim(),y=b.value.trim(),nx=Number(x.replace(/%$/,'')),ny=Number(y.replace(/%$/,''));var c=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});return (direction==='asc'?c:-c)||a.i-b.i;});
          entries.forEach(function(entry){table.appendChild(entry.row);});
          headers.forEach(function(th,i){th.setAttribute('aria-sort',i===column?(direction==='asc'?'ascending':'descending'):'none');});
          sortStates[tableKey]={column:column,direction:direction};
        }
        headers.forEach(function(th,column){var label=th.textContent;th.setAttribute('scope','col');th.textContent='';th.appendChild(E('button',{'type':'button','class':'hv-sort','aria-label':bi('Sort by ','Сортировать по ')+label,'click':function(){var old=sortStates[tableKey];applySort(column,old&&old.column===column&&old.direction==='asc'?'desc':'asc');}},[label,E('span',{'aria-hidden':'true'},' ↕')]));});
        if(sortStates[tableKey])applySort(sortStates[tableKey].column,sortStates[tableKey].direction);
      });
    }
    function addSearch(key,table){
      var input=E('input',{'type':'search','class':'hv-search','placeholder':bi('Search servers, channels or protocol','Поиск сервера, канала или протокола'),'aria-label':bi('Search table','Поиск в таблице'),'input':function(){searchTerms[key]=input.value;filter();}});input.value=searchTerms[key]||'';
      function filter(){var q=input.value.toLocaleLowerCase(locale);Array.prototype.slice.call(table.querySelectorAll('tr')).slice(1).forEach(function(row){row.hidden=q&&row.textContent.toLocaleLowerCase(locale).indexOf(q)<0;});}
      put(key,input);filter();
    }
""")
source=source.replace('      while(panel.firstChild)panel.removeChild(panel.firstChild);','      while(panel.firstChild)panel.removeChild(panel.firstChild);pages={};')

replacements={
"panel.appendChild(E('h3',{},tr(\"Подключённые VPN-серверы\")))":"put('channels',E('h3',{},tr(\"Подключённые VPN-серверы\")))",
"panel.appendChild(cards)":"put('channels',cards)",
"panel.appendChild(E('section',{'class':'hv-chart-card'},[E('h3',{},tr(\"Задержка серверов во времени\")),chart(status.samples||[],active)]))":"put('statistics',E('section',{'class':'hv-chart-card'},[E('h3',{},tr(\"Задержка серверов во времени\")),chart(status.samples||[],active)]))",
"panel.appendChild(histogram(status.accounting||{},function(value){period=value;draw(status);},period))":"put('statistics',histogram(status.accounting||{},function(value){period=value;draw(status);},period))",
"panel.appendChild(planning)":"put('overview',planning)",
"panel.appendChild(nativePanel)":"put('settings',nativePanel)",
"panel.appendChild(historyPanel)":"put('events',historyPanel)",
"panel.appendChild(E('h3',{},tr(\"Текущие проверки серверов\")));panel.appendChild(table)":"put('channels',E('h3',{},tr(\"Текущие проверки серверов\")));addSearch('channels',table);put('channels',table)",
"panel.appendChild(E('p',{},tr(\"Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.\")))":"put('channels',E('p',{},tr(\"Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.\")))",
"panel.appendChild(ranking);panel.appendChild(E('p',{},tr(\"Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.\")))":"addSearch('ranking',ranking);put('ranking',ranking);put('ranking',E('p',{},tr(\"Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.\")))",
"panel.appendChild(E('h3',{},tr(\"VPN-трафик по календарным месяцам · Europe/Berlin\")))":"put('traffic',E('h3',{},tr(\"VPN-трафик по календарным месяцам · Europe/Berlin\")))",
"panel.appendChild(traffic);panel.appendChild(E('p',{},tr(\"Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: \")+text(accounting.gaps||0)+tr(\". После потери питания возможна потеря последнего интервала checkpoint.\")))":"put('traffic',traffic);put('traffic',E('p',{},tr(\"Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: \")+text(accounting.gaps||0)+tr(\". После потери питания возможна потеря последнего интервала checkpoint.\")))",
"panel.appendChild(E('h3',{},tr(\"Монитор служб\")))":"put('services',E('h3',{},tr(\"Монитор служб\")))",
"panel.appendChild(terminal)":"put('services',terminal)",
"panel.appendChild(E('button',{'class':'btn','click':function(){var blob":"put('events',E('button',{'class':'btn','click':function(){var blob",
}
for old,new in replacements.items():
    assert old in source,old
    source=source.replace(old,new)
# Remaining top-level content is the real-data overview.
source=source.replace("panel.appendChild(E(","put('overview',E(")
source=source.replace("var ns=status.native_failover||{state:'SERVICE-STOPPED'};", """var ns=status.native_failover||{state:'SERVICE-STOPPED'};
      var stateNames={'OBSERVING':bi('Automatic monitoring','Автоматический контроль'),'ARMED':bi('Ready','Готов'),'COMMITTED':bi('Reserve confirmed','Резерв подтверждён'),'STOPPED':bi('Stopped','Остановлен'),'DISABLED':bi('Disabled','Выключен'),'EXPIRED':bi('Window ended','Окно завершено'),'WAIT-CLIENT':bi('Waiting for client','Ожидание клиента'),'APPLYING':bi('Switching','Переключение'),'BLOCKED':bi('Blocked','Заблокирован')};
      var stale=!ns.time||Date.now()/1000-ns.time>30;
      put('overview',E('section',{'class':'hv-chart-card hv-control-summary'},[E('h3',{},bi('Automatic failover','Автоматическое переключение')),E('strong',{'class':stale?'hv-warn':'hv-control-state'},stale?bi('Controller status is stale','Статус контроллера устарел'):(stateNames[ns.state]||ns.state||bi('Unknown','Неизвестно'))),E('p',{},bi('Code: ','Код: ')+(ns.state||'UNKNOWN')),E('p',{},bi('Primary: ','Основной: ')+((rows.filter(function(p){return p.id===(inventory.settings||{}).plan_source;})[0]||{}).name||'—')),E('p',{},bi('Reserve: ','Резерв: ')+((rows.filter(function(p){return p.id===(inventory.settings||{}).plan_target;})[0]||{}).name||'—')),E('p',{},bi('Updated: ','Обновлено: ')+(ns.time?new Date(ns.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}):'—')),E('button',{'type':'button','class':'cbi-button','click':function(){window.location.hash='settings';showPage('settings');}},bi('Controls and setup','Управление и настройка'))]));
      if(versionBadge)versionBadge.textContent='v'+(status.version||'unknown');
      if(sideState)sideState.textContent=status.error?bi('Monitor unavailable','Монитор недоступен'):bi('Router monitor online','Монитор роутера доступен');
""")
source=source.replace("E('strong',{},ns.state||'UNKNOWN')","E('strong',{},stateNames[ns.state]||ns.state||'UNKNOWN')")
source=source.replace("      var terminal=E('pre',{},[]);", """      put('services',E('p',{},bi('Times are from the router measurements. A connected interface alone is not proof of internet access.','Время берётся из измерений роутера. Подключённый интерфейс сам по себе не доказывает доступность интернета.')));
      var terminal=E('pre',{},[E('div',{},[E('span',{'class':'hv-log-time'},status.time?new Date(status.time*1000).toLocaleTimeString():'—'),E('strong',{},'  HomenS.AI monitor: '),badge(status.error)]),E('div',{},[E('span',{'class':'hv-log-time'},ns.time?new Date(ns.time*1000).toLocaleTimeString():'—'),E('strong',{},'  Auto VPN: '),stateNames[ns.state]||ns.state||'UNKNOWN'])]);""")
source=source.replace("    }\n    draw(data[1]);", "      sortableTables();showPage(activeTab);\n    }\n    draw(data[1]);")

bottom=source.index('    return m.render().then(function(form)')
source=source[:bottom]+"""    return m.render().then(function(formNode){
      var robotHost=E('div',{'class':'robo','aria-label':bi('HomenS.AI author robot','Робот автора HomenS.AI')});
      var footer=E('footer',{'class':'hv-brand-footer'});window.HomenS.brandUi.renderFooter(footer,locale,'platform');
      setTimeout(function(){var robot=window.HomenS.robot.tvRobot(robotHost);robot.play();},0);
      var language=E('select',{'aria-label':bi('Language','Язык')},[E('option',{value:'en',selected:locale==='en'?'':null},'English'),E('option',{value:'ru',selected:locale==='ru'?'':null},'Русский')]);language.value=locale;
      language.addEventListener('change',function(){var chosen=language.value==='ru'?'ru':'en';try{localStorage.setItem('homensai-vpn-language',chosen);}catch(e){}var next=new URL(window.location.href);next.searchParams.set('lang',chosen);window.location.assign(next.toString());});
      versionBadge=E('span',{'class':'hv-version','aria-label':bi('Program version','Версия программы')},'v'+(data[1].version||'unknown'));
      heading=E('h1',{},bi('Your internet under control','Ваш интернет под контролем'));
      sideState=E('p',{'class':'hv-side-state'},data[1].error?bi('Monitor unavailable','Монитор недоступен'):bi('Router monitor online','Монитор роутера доступен'));
      settingsHost=E('section',{'class':'hv-settings','data-hv-page':'settings'},[E('h3',{},bi('Monitoring, Telegram and profile names','Мониторинг, Telegram и названия профилей')),E('a',{'href':L.url('admin/services/homensai-vpn')+'?setup=telegram&lang='+locale+'#settings'},bi('Telegram setup wizard','Мастер настройки Telegram')),setup?E('p',{},bi('Create a bot with BotFather, send /start, then enter its token and your Chat ID. The token stays on the router and is never returned in status.','Создайте бота через BotFather, отправьте /start, затем введите токен и свой Chat ID. Токен хранится на роутере и не возвращается в статусе.')):null,formNode].filter(function(node){return node!=null;}));
      var links=tabs.map(function(tab){return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);});
      appRoot=E('div',{'class':'hv-app hv-workspace'},[
        E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/tokens.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/fonts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/author.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/style/css/charts.css')}),E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui13.css')+'?build=060-alpha1'}),
        E('aside',{'class':'hv-sidebar'},[E('a',{'class':'hv-side-brand','href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer','aria-label':bi('HomenS.AI website','Сайт HomenS.AI')},[robotHost,E('span',{},[E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI')]),E('small',{},'Auto VPN')])]),E('p',{'class':'hv-model'},'GL.iNet GL-MT6000 · Flint 2'),E('nav',{'aria-label':bi('VPN sections','Разделы VPN')},links),E('div',{'class':'hv-side-footer'},[sideState,E('small',{},bi('Real IPv4 router measurements','Реальные IPv4-измерения роутера')),E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),E('small',{},'HomenS.AI Style 1.14.3')])]),
        E('main',{'class':'hv-main'},[E('header',{'class':'hv-page-header'},[E('div',{},[E('div',{'class':'hv-eyebrow'},bi('AVAILABILITY CONTROL','УПРАВЛЕНИЕ ДОСТУПНОСТЬЮ')),heading,E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.'))]),E('div',{'class':'hv-page-actions'},[versionBadge,language,E('button',{'type':'button','class':'btn hv-test','click':function(){return scanCall().then(function(){return statusCall().then(draw);}).catch(function(){ui.addNotification(null,E('p',{},bi('Probe request failed. See service status.','Запрос проверки не прошёл. Смотрите состояние службы.')));});}},bi('Probe now','Проверить сейчас'))])]),panel,settingsHost,footer])
      ]);
      showPage(activeTab);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});
      return appRoot;
    });
  }
});
"""
source=source.replace("active.forEach(function(p)", "active.sort(function(a,b){return Number(!!a.code)-Number(!!b.code);}).forEach(function(p)")
source=source.replace("      while(panel.firstChild)", "      var focused=panel.contains(document.activeElement)&&document.activeElement.classList.contains('hv-search')?{key:document.activeElement.closest('[data-hv-page]').dataset.hvPage,start:document.activeElement.selectionStart,end:document.activeElement.selectionEnd}:null;\n      while(panel.firstChild)")
source=source.replace("sortableTables();showPage(activeTab);", "sortableTables();showPage(activeTab);if(focused){var input=pages[focused.key]&&pages[focused.key].querySelector('.hv-search');if(input){input.focus();input.setSelectionRange(focused.start,focused.end);}}")
source='\n'.join(line for line in source.splitlines() if "put('overview',E('section',{'class':'hv-chart-card hv-control-summary'}" not in line)
source=source.replace("var ns=status.native_failover||{state:'SERVICE-STOPPED'};", "var ns=status.native_failover||{state:'SERVICE-STOPPED'};\n      var controlCard=renderAutoControl(status,inventory);put('overview',controlCard);pages.overview.insertBefore(controlCard,pages.overview.firstChild);")
source=source.replace('return view.extend({',(Path(__file__).parent/'auto_panel.inc.js').read_text(encoding='utf8')+'\n'+(Path(__file__).parent/'setup_wizard.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("      showPage(activeTab);window.addEventListener", "      settingsHost.insertBefore(E('div',{'class':'hv-wizard-launch'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){setupWizard(inventory,'system');}},bi('System setup wizard','Мастер настройки системы')),E('button',{'type':'button','class':'cbi-button','click':function(){setupWizard(inventory,'telegram');}},bi('Telegram channel wizard','Мастер Telegram-канала')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'TELEGRAM-TEST-UNKNOWN'));});}},bi('Test Telegram delivery','Проверить доставку Telegram'))]),settingsHost.firstChild);\n      showPage(activeTab);window.addEventListener")
source=source.replace("telegramChat.datatype='integer'","telegramChat.datatype='string'")
source=source.replace("var appRoot=null,settingsHost", "var lastGoodStatus=data[1];\n    var appRoot=null,settingsHost")
source=source.replace("function draw(status){", "function draw(status){\n      if(!status.rpc_error)lastGoodStatus=status;")
source=source.replace("poll.add(function(){return statusCall().then(draw).catch(function(){draw({error:'SERVICE-STOPPED'});});},10);", "poll.add(function(){return statusCall().then(draw).catch(function(){draw(Object.assign({},lastGoodStatus,{rpc_error:'RPC-UNAVAILABLE'}));});},10);")
source=source.replace("statusCall().catch(function(){return {error:'SERVICE-STOPPED'};})", "statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};})")
source=source.replace("data[1].error?bi('Monitor unavailable','Монитор недоступен')", "data[1].rpc_error?bi('Status RPC unavailable','RPC статуса недоступен'):data[1].error?bi('Monitor unavailable','Монитор недоступен')")
source=source.replace("sideState.textContent=status.error?", "sideState.textContent=status.rpc_error?bi('Status RPC unavailable','RPC статуса недоступен'):status.error?")
source=source.replace("var ns=status.native_failover||{state:'SERVICE-STOPPED'};", "var ns=status.native_failover||{state:'UNKNOWN'};")
source=source.replace("if(status.error)put('overview',E('p',{},badge(status.error)));", "if(status.rpc_error)put('overview',E('p',{'class':'alert-message warning'},'RPC-UNAVAILABLE: displaying last known measurements. Connectivity and service state are unconfirmed.'));\n      if(status.error)put('overview',E('p',{},badge(status.error)));")
source=source.replace('return view.extend({',(Path(__file__).parent/'speed_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("period='day';", "period='day',speedPeriod='week';")
source=source.replace("      sortableTables();showPage(activeTab);", "      put('ranking',speedPanel(status,inventory,speedPeriod,function(value){speedPeriod=value;draw(status);}));\n      sortableTables();showPage(activeTab);")
source=source.replace("      settingsHost.insertBefore", "      settingsHost.appendChild(speedSettings(inventory));\n      settingsHost.insertBefore")
source=source.replace("cell(new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}))","E('td',{'data-sort-value':event.time},new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}))")
source=source.replace('return view.extend({',(Path(__file__).parent/'traffic_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("      sortableTables();showPage(activeTab);", "      put('traffic',trafficHistoryPanel(status.accounting||{}));\n      sortableTables();showPage(activeTab);")
old="var monthKeys=Object.keys((status.accounting||{}).months||{}).sort(),month=monthKeys.length?(status.accounting.months[monthKeys[monthKeys.length-1]]):null;"
assert old in source
source=source.replace(old,"var currentMonth=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit'}).format(new Date()),month=((status.accounting||{}).months||{})[currentMonth]||null;")
old="Object.keys(p.days||{}).forEach(function(day){"
assert old in source
source=source.replace(old,"if(p.periods&&p.periods[period]){Object.keys(totals).forEach(function(k){totals[k]=p.periods[period][k]||0;});}else Object.keys(p.days||{}).forEach(function(day){")
source=source.replace("day.slice(0,7)!==today.slice(0,7)","day.slice(0,7)!==today.slice(0,7)||day>today")
source=source.replace('?build=060-alpha1','?build=070-alpha10')
source=source.replace("      settingsHost.appendChild(speedSettings(inventory));", "      settingsHost.appendChild(E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Monitor service','Служба мониторинга')),E('p',{},bi('Enables measurement only. Stop Auto mode and finish rollback before disabling the monitor. Actual service state is confirmed by fresh measurements.','Включает только измерения. Перед отключением остановите авторежим и дождитесь отката. Работа службы подтверждается свежими измерениями.')),E('button',{'type':'button','class':'cbi-button','click':function(ev){ev.target.disabled=true;return rpc.declare({object:'homensai-vpn',method:'monitor_control',params:['enabled'],expect:{}})(!(inventory.settings||{}).enabled).then(function(result){ui.addNotification(null,E('p',{},result.code||'MONITOR-UNKNOWN'));if(result.accepted)window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){ev.target.disabled=false;});}},(inventory.settings||{}).enabled?bi('Stop monitor','Остановить мониторинг'):bi('Start monitor','Запустить мониторинг'))]));\n      settingsHost.appendChild(speedSettings(inventory));")
import json
source=source.replace('return view.extend({','var RECOVERY_PRESETS='+json.dumps(json.loads((Path(__file__).parent/'files/usr/lib/homensai-vpn/recovery_presets.json').read_text(encoding='utf8')),sort_keys=True)+';\nreturn view.extend({')
source=source.replace('return view.extend({',(Path(__file__).parent/'recovery_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("      settingsHost.appendChild(speedSettings(inventory));", "      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){recoveryWizard(inventory);}},bi('Recovery setup wizard','Мастер восстановления')));\n      settingsHost.appendChild(speedSettings(inventory));")
source=source.replace("['statistics','▥'", "['tests','⏻',bi('Operator tests','Операторские тесты')],['statistics','▥'")
source=source.replace('return view.extend({',(Path(__file__).parent/'fault_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("      sortableTables();showPage(activeTab);", "      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));\n      sortableTables();showPage(activeTab);")
old="return m.render().then(function(formNode){"
assert old in source
source=source.replace(old,"return Promise.resolve(E('p',{},bi('Use the setup wizards below. Settings are validated before saving; stored tokens are never loaded into this page.','Используйте мастера ниже. Настройки проверяются до сохранения; сохранённые токены не загружаются на эту страницу.'))).then(function(formNode){")
source=source.replace('return view.extend({','return view.extend({\n  handleSave:null,handleSaveApply:null,handleReset:null,',1)
source=source.replace("      settingsHost.appendChild(speedSettings(inventory));", "      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){monitorPreferences(inventory);}},bi('Monitoring preferences','Параметры мониторинга')));\n      settingsHost.appendChild(speedSettings(inventory));")
start=source.index("    var inventory=data[0],m=new form.Map")
end=source.index("    var panel=E('div',{'class':'hv-panel'})",start)
source=source[:start]+"    var inventory=data[0];\n"+source[end:]
source=source.replace("'require form';",'')
source=source.replace("var setup=!configured||new URLSearchParams(window.location.search).get('setup')==='telegram';", "var setup=new URLSearchParams(window.location.search).get('setup')==='telegram';")
source=source.replace('return view.extend({',(Path(__file__).parent/'inventory_reliable.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
old="inventoryCall().catch(function(){return {profiles:[]};})"
assert old in source
source=source.replace(old,'loadInventory(0)')
source=source.replace("object:'homensai-vpn',", "object:'homensai-vpn',reject:true,")
source=source.replace("      sortableTables();showPage(activeTab);", "      if(inventory.error)put('overview',E('p',{'class':'alert-message warning','role':'alert'},'RPC-INVENTORY-UNAVAILABLE: configuration is unknown. Reload after RPC recovery; empty defaults are not saved.'));\n      sortableTables();showPage(activeTab);")
source=source.replace("settingsHost.insertBefore(E('div',{'class':'hv-wizard-launch'}", "settingsHost.insertBefore(E('div',{'class':'hv-wizard-launch'}")
source=source.replace('return view.extend({',(Path(__file__).parent/'ui_logic.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("active.sort(function(a,b){return Number(!!a.code)-Number(!!b.code);}).forEach", "sortServerCards(active,selectedProfile(status,Date.now()/1000),Date.now()/1000).forEach")
source=source.replace("'class':'hv-server '+(p.code?'hv-degraded':'')", "'class':'hv-server hv-health-'+profileHealth(p,Date.now()/1000).state,'data-profile':p.id,'data-health':profileHealth(p,Date.now()/1000).state")
source=source.replace('badge(p.code)','healthBadge(p)')
source=source.replace("sortServerCards(active,selectedProfile(status,Date.now()/1000),Date.now()/1000)","sortServerCards(rows,selectedProfile(status,Date.now()/1000),Date.now()/1000)")
source=source.replace("E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-protocol'}", "E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-server-lamp hv-lamp-'+profileHealth(p,Date.now()/1000).state,'role':'img','aria-label':profileHealth(p,Date.now()/1000).label,'title':profileHealth(p,Date.now()/1000).label}),E('span',{'class':'hv-protocol'}")

source=source.replace("var tableKey=(table.closest('[data-hv-page]')||{dataset:{hvPage:'overview'}}).dataset.hvPage+'-'+index,headers=table.querySelectorAll('tr:first-child th');", "var headers=table.querySelectorAll('tr:first-child th'),tableKey=(table.closest('[data-hv-page]')||{dataset:{hvPage:'overview'}}).dataset.hvPage+':'+Array.from(headers).map(function(th){return th.textContent;}).join('|');")
source=source.replace("var c=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});return (direction==='asc'?c:-c)||a.i-b.i;", "return compareTableValues(a.value,b.value,direction)||a.i-b.i;")
source=source.replace('return view.extend({',(Path(__file__).parent/'analytics_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("var controlCard=renderAutoControl(status,inventory);put('overview',controlCard);", "var controlCard=renderAutoControl(status,inventory);put('overview',vpnSetupCard());put('overview',controlCard);put('overview',renderCascadePath(status));")
source=source.replace("put('events',historyPanel)", "put('events',historyPanel);put('events',renderTransitionAnalytics(status))")
source=source.replace('ui13.css','ui15.css')
source=source.replace('put(\'channels\',E(\'h3\',{},tr("Подключённые VPN-серверы")))',"put('channels',vpnSetupCard());put('channels',E('h3',{},bi('Connected VPN server','Подключённый VPN-сервер')))")
source=source.replace('return view.extend({',(Path(__file__).parent/'router_link.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("p.channel+' · '+p.interface","(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён'))")
source=source.replace("Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'","profileHealth(p,Date.now()/1000).state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'")
source=source.replace("if(!active.length)cards.appendChild", "if(!rows.length)cards.appendChild")
source=source.replace("healthy=active.filter(function(p){return !p.code;})","healthy=active.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';})")
source=source.replace("cell(p.rtt_ms)","cell(profileHealth(p,Date.now()/1000).state==='healthy'?p.rtt_ms:null)")
# Approved interaction/visual review: request-correlated checks and explicit actions.
source=source.replace('return view.extend({',(Path(__file__).parent/'connectivity_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
old="E('button',{'type':'button','class':'btn hv-test','click':function(){return scanCall().then(function(){return statusCall().then(draw);}).catch(function(){ui.addNotification(null,E('p',{},bi('Probe request failed. See service status.','Запрос проверки не прошёл. Смотрите состояние службы.')));});}},bi('Probe now','Проверить сейчас'))"
assert old in source
source=source.replace(old,"renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})")
source=source.replace('function draw(status){','function draw(status){\n      updateConnectivityCheck(status);')
source=source.replace("      if(heading)heading.textContent=", "      if(appRoot){appRoot.querySelectorAll('.hv-connectivity-control').forEach(function(node){node.hidden=key!=='overview';});}\n      if(heading)heading.textContent=")
source=source.replace("bi('Configure VPN','Настроить VPN')", "bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗')")
source=source.replace("bi('Operator tests','Операторские тесты')", "bi('Diagnostics','Диагностика')")
source=source.replace("E('div',{'class':'hv-server-top'},", "E('div',{'class':'hv-server-top'},")
source=source.replace("healthBadge(p)]", "healthBadge(p),E('span',{'class':'hv-profile-detail'},bi('Connection: ','Подключение: ')+(p.interface?bi('Connected','Подключён'):bi('Inactive','Неактивен'))+' · '+bi('Traffic: ','Трафик: ')+(selectedProfile(status,Date.now()/1000)===p.id?bi('Selected','Выбран'):bi('Not confirmed as selected','Выбор не подтверждён'))+' · '+bi('Priority: ','Приоритет: ')+(p.priority||100))]",1)

source=source.replace("put('overview',renderCascadePath(status));","put('overview',renderCascadePath(status));put('overview',renderDecisionExplanation(status));")
source=source.replace("var appRoot=null,settingsHost", "var pointerHeld=false,deferredStatus=null;\n    var appRoot=null,settingsHost")
source=source.replace("function draw(status){", "function draw(status){\n      if(pointerHeld){deferredStatus=status;updateConnectivityCheck(status);return;}\n      var controlFocus=panel.contains(document.activeElement)&&document.activeElement.matches('button,input[type=checkbox],select')?{page:(document.activeElement.closest('[data-hv-page]')||{dataset:{hvPage:activeTab}}).dataset.hvPage,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.textContent,tag:document.activeElement.tagName}:null;")
source=source.replace("      if(inventory.error)put('overview'", "      if(controlFocus&&pages[controlFocus.page]){var options=pages[controlFocus.page].querySelectorAll('button,input[type=checkbox],select');var matching=Array.from(options).find(function(el){return el.tagName===controlFocus.tag&&el.getAttribute('aria-label')===controlFocus.label&&el.textContent===controlFocus.text;});if(matching)matching.focus({preventScroll:true});}\n      if(inventory.error)put('overview'")
source=source.replace("      showPage(activeTab);window.addEventListener", "      panel.addEventListener('pointerdown',function(){pointerHeld=true;});\n      ['pointerup','pointercancel'].forEach(function(event){window.addEventListener(event,function(){if(!pointerHeld)return;setTimeout(function(){pointerHeld=false;if(deferredStatus){var next=deferredStatus;deferredStatus=null;draw(next);}},0);});});\n      showPage(activeTab);window.addEventListener")

source=source.replace("put('overview',planning);","put('tests',planning);")
source=source.replace('return view.extend({',(Path(__file__).parent/'sidebar_layout.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("if(!validTab(key))key='overview';activeTab=key;", "var oldTab=activeTab;if(!validTab(key))key='overview';activeTab=key;")
source=source.replace("if(heading)heading.textContent=", "if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);\n      if(heading)heading.textContent=")
source=source.replace("E('nav',{'aria-label':bi('VPN sections','Разделы VPN')}", "E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')}")
source=source.replace('      return appRoot;', '      initSidebarLayout(appRoot);\n      return appRoot;')

source=source.replace('return view.extend({',(Path(__file__).parent/'incident_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace('return view.extend({',(Path(__file__).parent/'readiness_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
source=source.replace("['settings','⚙'","['readiness','✓',bi('System readiness','Готовность системы')],['settings','⚙'")
source=source.replace("put('overview',renderDecisionExplanation(status));","put('overview',renderDecisionExplanation(status));put('readiness',renderReadiness(status));")
# Settings page: one grouped Setup card instead of scattered wizard buttons; one blocker dictionary.
def must_replace(old,new):
    global source
    assert old in source,old[:80]
    source=source.replace(old,new,1)
must_replace("E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Monitor service'","E('section',{'class':'hv-chart-card hv-card-monitor'},[E('h3',{},bi('Monitor service'")
must_replace('return view.extend({',(Path(__file__).parent/'setup_guides.inc.js').read_text(encoding='utf8')+(Path(__file__).parent/'monitor_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("['tests','⏻',bi('Diagnostics','Диагностика')]","['tests','⏻',bi('Tests','Тесты')]")
must_replace("(descriptions[code]||bi('See diagnostic code in the work log','Смотрите код диагностики в журнале работ'))","autoBlockerText(code)")
must_replace("E('p',{},bi('1. Save a primary and reserve profile below. 2. Accept session reconnection. 3. Run the downloaded helper on a Windows LAN client with PowerShell 7. It checks the gateway, router DNS, HTTPS and VPN exit, and asks before starting. Browser checks alone do not certify router DNS.','1. Сохраните основной и резервный профили ниже. 2. Разрешите переподключение сессий. 3. Запустите скачанный помощник на Windows-клиенте LAN с PowerShell 7. Он проверит шлюз, DNS роутера, HTTPS и VPN-выход, затем спросит перед запуском. Проверка только браузером не подтверждает DNS роутера.'))",
 "E('p',{},bi('Auto can be started only after a passed LAN trial. The Overview page shows exactly which step is missing. The helper runs on a Windows computer with PowerShell 7 connected to the LAN; it checks the gateway, router DNS, HTTPS and the VPN exit, and asks before it starts. Browser checks alone do not certify the LAN path.','Авторежим можно запустить только после успешного LAN-теста. Страница «Обзор» показывает, какого именно шага не хватает. Помощник запускается на компьютере Windows с PowerShell 7 в локальной сети: он проверяет шлюз, DNS роутера, HTTPS и VPN-выход и спрашивает подтверждение перед началом. Проверка только браузером не подтверждает путь LAN.'))")
must_replace("E('h3',{},'Persistent controller history'),E('p',{},'Controller events, not measurements of LAN uptime. Trial results and automatic commits are counted separately.')",
 "E('h3',{},bi('Controller history','История контроллера')),E('p',{},bi('Controller events, not measurements of LAN uptime. Trial results and automatic commits are counted separately.','События контроллера, а не измерение доступности LAN. Результаты тестов и автоматические переключения считаются отдельно.'))")
reorganizer = """      (function(){
        var monitorCard=settingsHost.querySelector('.hv-card-monitor'),speedCard=settingsHost.querySelector('.hv-speed-settings');
        while(settingsHost.firstChild)settingsHost.removeChild(settingsHost.firstChild);
        function launcher(label,hint,action,primary,guide){return E('div',{'class':'hv-setup-item'},[E('button',{'type':'button','class':'cbi-button'+(primary?' cbi-button-action':''),'click':action},label),E('p',{},hint),guide?setupGuide(guide):null].filter(Boolean));}
        var testDelivery=function(){return rpc.declare({object:'homensai-vpn',reject:true,method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'TELEGRAM-TEST-UNKNOWN'));});};
        settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-setup-card'},[
          E('h3',{},bi('Setup','Настройка')),
          E('p',{},bi('Simple settings for every user. Every wizard validates your input and shows a review before saving. Stored tokens are never shown again. Open “What is this and how to fill it in” under a step for examples.','Простые настройки для любого пользователя. Каждый мастер проверяет ввод и показывает обзор перед сохранением. Сохранённые токены больше не показываются. Под каждым шагом есть «Что это и как заполнить» с примерами.')),
          E('div',{'class':'hv-setup-grid'},[
            launcher(bi('1 · System','1 · Система'),bi('Primary and reserve profiles, names, channels, priorities and accepted reconnection.','Основной и резервный профили, названия, каналы, приоритеты и допустимость переподключения.'),function(){setupWizard(inventory,'system');},true,'system'),
            launcher(bi('2 · Telegram','2 · Telegram'),bi('Bot token and destination for reports.','Токен бота и адресат отчётов.'),function(){setupWizard(inventory,'telegram');},false,'telegram'),
            launcher(bi('Test Telegram delivery','Проверить доставку Telegram'),bi('Sends one test message with the saved settings.','Отправляет одно тестовое сообщение с сохранёнными настройками.'),testDelivery)
          ])].filter(function(node){return node!=null;})));
        settingsHost.appendChild(E('details',{'class':'hv-chart-card hv-admin-settings'},[
          E('summary',{},bi('Advanced settings (for administrators)','Расширенные настройки (для администратора)')),
          E('p',{},bi('Fine-tuning of the switching rules and of the checks. The defaults are safe; change them only if you know why. Open the guide under each step for examples.','Тонкая настройка правил переключения и проверок. Значения по умолчанию безопасны; меняйте их, только если понимаете зачем. Под каждым шагом есть руководство с примерами.')),
          E('div',{'class':'hv-setup-grid'},[
            launcher(bi('Recovery rules','Правила восстановления'),bi('Failures before switching, reserve checks, cooldown and return policy.','Сколько сбоев до переключения, проверки резерва, пауза и политика возврата.'),function(){recoveryWizard(inventory);},false,'recovery'),
            launcher(bi('Monitoring parameters','Параметры мониторинга'),bi('Check interval, profile limit and statistics saving.','Интервал проверок, лимит профилей и сохранение статистики.'),function(){monitorPreferences(inventory);},false,'monitoring')
          ])]));
        if(speedCard){put('tests',E('h2',{},bi('VPN speed tests','Тесты скорости VPN')));put('tests',setupGuide('speed'));put('tests',speedCard);}
      })();
"""
must_replace("      panel.addEventListener('pointerdown',function(){pointerHeld=true;});", reorganizer+"      panel.addEventListener('pointerdown',function(){pointerHeld=true;});")
source=source.replace('070-alpha10','080-alpha8')
# Overview copy: one calm monitoring note; Telegram has its own tile, so only a real error is shown.
note_old='tr("Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.")'
assert note_old in source
source=source.replace(note_old,"bi('Monitoring is active. Router checks show tunnel health only; they do not prove the path of a computer on the LAN. Auto switching is confirmed separately by the LAN helper.','Мониторинг работает. Проверки роутера показывают только состояние туннелей и не доказывают путь компьютера в LAN. Автопереключение подтверждается отдельно LAN-помощником.')")
telegram_old="var tg=status.telegram||{};put('overview',E('p',{},'Telegram: '+(tg.enabled?(tg.code||(tr(\"включён · интервал \")+tg.interval_minutes+tr(\" мин · последняя отправка \")+(tg.last_sent?new Date(tg.last_sent*1000).toLocaleString():tr(\"ожидается\")))):tr(\"отключён\"))));"
assert telegram_old in source
source=source.replace(telegram_old,"var tg=status.telegram||{};if(tg.enabled&&tg.code)put('overview',E('p',{'class':'alert-message warning'},'Telegram: '+tg.code));")
# Simpler Overview and navigation: details move to Diagnostics / Service monitor; admin pages sit behind "Advanced".
import re as _r
must_replace("put('overview',vpnSetupCard());put('overview',controlCard);put('overview',renderCascadePath(status));put('overview',renderDecisionExplanation(status));","put('overview',controlCard);put('tests',renderCascadePath(status));put('tests',renderDecisionExplanation(status));")
source,_n=_r.subn(r"put\('overview',(E\('p',\{'class':'alert-message warning'\},\s*bi\('Monitoring is )",r"put('services',\1",source,count=1)
assert _n==1,'monitor note'
must_replace('return view.extend({',"""var ADVANCED_KEYS=['tests','ranking','traffic','services','events','readiness'];
var PAGE_SUBTITLES={
  overview:['Your VPNs, how healthy they are, and what the router did about it.','Ваши VPN, насколько они исправны и что сделал роутер.'],
  channels:['Every VPN profile on the router and whether it works right now.','Все VPN-профили роутера и работают ли они прямо сейчас.'],
  statistics:['How your VPNs behaved over time.','Как вели себя ваши VPN со временем.'],
  settings:['Set up the monitor, your two VPNs, reports and recovery rules.','Настройка мониторинга, двух VPN, отчётов и правил восстановления.'],
  help:['What to do when something is wrong.','Что делать, если что-то не так.'],
  tests:['How the failover decides, and a test that simulates a failure.','Как принимается решение о переключении, и тест с имитацией сбоя.'],
  ranking:['Which servers worked best over the last days.','Какие серверы работали лучше всего за последние дни.'],
  traffic:['How much data went through each VPN.','Сколько данных прошло через каждый VPN.'],
  services:['A live log of what the router sees.','Живой журнал того, что видит роутер.'],
  events:['Everything that happened: switches, failures, recoveries.','Всё, что происходило: переключения, сбои, восстановления.'],
  readiness:['Whether this router has everything Auto needs.','Есть ли на этом роутере всё, что нужно для Auto.']
};
return view.extend({""")
must_replace("var appRoot=null,settingsHost=null,heading=null,","var subtitle=null,advancedBox=null,advancedToggle=null,appRoot=null,settingsHost=null,heading=null,")
must_replace("heading,E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одком месте.'))".replace('одком','одном'),"heading,(subtitle=E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.')))")
must_replace("if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];","""if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];
      if(subtitle&&PAGE_SUBTITLES[key])subtitle.textContent=bi(PAGE_SUBTITLES[key][0],PAGE_SUBTITLES[key][1]);
      if(advancedBox&&ADVANCED_KEYS.indexOf(key)>=0&&advancedBox.hidden){advancedBox.hidden=false;if(advancedToggle)advancedToggle.setAttribute('aria-expanded','true');}""")
must_replace("var links=tabs.map(function(tab){return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);});","""function tabLink(key){var tab=tabs.filter(function(t){return t[0]===key;})[0];return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);}
      var advancedOpen=false;try{advancedOpen=localStorage.getItem('homensai-vpn-advanced')==='1';}catch(e){}
      if(ADVANCED_KEYS.indexOf(activeTab)>=0)advancedOpen=true;
      advancedBox=E('div',{'class':'hv-advanced-links'},ADVANCED_KEYS.map(tabLink));advancedBox.hidden=!advancedOpen;
      advancedToggle=E('button',{'type':'button','class':'hv-advanced-toggle','aria-expanded':advancedOpen?'true':'false','click':function(){var open=advancedBox.hidden;advancedBox.hidden=!open;advancedToggle.setAttribute('aria-expanded',open?'true':'false');try{localStorage.setItem('homensai-vpn-advanced',open?'1':'0');}catch(e){}}},[E('span',{},bi('Advanced','Расширенное')),E('small',{},bi('for administrators','для администраторов'))]);
      var links=['overview','channels','statistics','settings','help'].map(tabLink).concat([advancedToggle,advancedBox]);""")
# Ranking: number of checks and a confidence label; sparse servers never lead.
must_replace('tr("Успех проверок"),tr("Средняя HTTPS-задержка")].map(','tr("Успех проверок"),tr("Средняя HTTPS-задержка"),bi("Checks","Проверок")].map(')
must_replace("cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+tr(\" мс\"):'—')]));});","cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+tr(\" мс\"):'—'),cell(rankConfidence(item.r.n))]));});")
must_replace(".sort(function(a,b){return (b.r.n?",".sort(function(a,b){return (rankEnough(b.r.n)-rankEnough(a.r.n))||(b.r.n?")
must_replace("addSearch('ranking',ranking);put('ranking',ranking);","addSearch('ranking',ranking);put('ranking',ranking);put('ranking',E('p',{},bi('Servers with fewer than 20 checks are listed last: one lucky check does not make a leader.','Серверы с менее чем 20 проверками стоят в конце: одна удачная проверка не делает лидера.')));")
# Opening another page always starts at the top (the sidebar and the page share one window scroll).
must_replace("if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);","if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);\n      if(oldTab!==key){try{window.scrollTo(0,0);if(document.scrollingElement)document.scrollingElement.scrollTop=0;}catch(e){}}")
# Servers are named by protocol and country; host names and addresses are not shown.
must_replace('return view.extend({',(Path(__file__).parent/'country_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("E('h4',{},p.name),E('p',{},(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён'))),","E('h4',{'class':'hv-server-country'},countryLabel(p)),E('p',{},(customName(p)?customName(p)+' · ':'')+(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён'))),")
must_replace("E('span',{'class':'hv-protocol'},p.protocol==='wireguard'?'WireGuard':'OpenVPN')","E('strong',{'class':'hv-protocol'},protocolLabel(p))")
must_replace("[cell(p.name),cell(p.channel),cell(p.protocol),","[cell(serverTitle(p)),cell(p.channel),cell(protocolLabel(p)),")
must_replace("ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(item.p.name),","ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(serverTitle(item.p)),")
# Channels page: say where the list comes from and what the numbers mean.
must_replace('return view.extend({',(Path(__file__).parent/'servers_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("put('channels',vpnSetupCard());put('channels',E('h3',{},bi('Connected VPN server','Подключённый VPN-сервер')));","put('channels',vpnSetupCard());put('channels',renderServerSummary(status,inventory,rows));")
# Idle/active check control moves to the left of the page header, under the subtitle.
must_replace("E('div',{'class':'hv-page-actions'},[versionBadge,language,renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})])","E('div',{'class':'hv-page-actions'},[versionBadge,language])")
must_replace("(subtitle=E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.')))","(subtitle=E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.'))),renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})")
# Built-in Help page: static topics, created once so opened topics stay open while the status refreshes.
must_replace('return view.extend({',(Path(__file__).parent/'help_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("['settings','⚙',bi('Settings','Настройки')]];","['settings','⚙',bi('Settings','Настройки')],['help','?',bi('Help','Помощь')]];")
must_replace("put('readiness',renderReadiness(status));","put('readiness',renderReadiness(status));put('help',helpNode||(helpNode=renderHelp()));")
# First-run terms gate: nothing else is rendered until the terms version is stored on the router.
_terms_version=_r.search(r"^TERMS_VERSION = '([^']+)'",(Path(__file__).parent/'files/usr/lib/homensai-vpn/agent.py').read_text(encoding='utf8'),_r.M).group(1)
must_replace('return view.extend({',(Path(__file__).parent/'terms_panel.inc.js').read_text(encoding='utf8').replace('__TERMS_VERSION__',_terms_version)+'\nreturn view.extend({')
must_replace("    var inventory=data[0];\n","    var inventory=data[0];\n    if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory);\n")
# Installed identity (package/program/page) and part-mismatch notice.
_agent_version=_r.search(r"^VERSION = '([^']+)'",(Path(__file__).parent/'files/usr/lib/homensai-vpn/agent.py').read_text(encoding='utf8'),_r.M).group(1)
must_replace('return view.extend({',(Path(__file__).parent/'identity_panel.inc.js').read_text(encoding='utf8').replace('__UI_BUILD__','dashboard59').replace('__UI_AGENT__',_agent_version)+'\nreturn view.extend({')
must_replace("E('small',{},'HomenS.AI Style 1.14.3')","E('small',{},'HomenS.AI Style 1.14.3'),E('small',{'class':'hv-identity'},identityLine(data[1]))")
must_replace("pages.overview.insertBefore(controlCard,pages.overview.firstChild);","pages.overview.insertBefore(controlCard,pages.overview.firstChild);var identityNotice=renderIdentityNotice(status);if(identityNotice)pages.overview.insertBefore(identityNotice,pages.overview.firstChild);pages.overview.insertBefore(renderSummary(status,inventory),pages.overview.firstChild);")
# Plain-language copy (router/ui_copy.py): every row must match, so stale rows fail the build.
from ui_copy import COPY
import re as _re
for _old,_new_en,_new_ru in COPY:
    _pattern=_re.compile(r"bi\('"+_re.escape(_old)+r"','(?:[^'\\]|\\.)*'\)")
    assert _pattern.search(source),_old[:70]
    source=_pattern.sub(lambda _m:"bi('"+_new_en+"','"+_new_ru+"')",source)
from ui_copy import EN_VALUES
for _old,_new in EN_VALUES:
    assert ': "'+_old+'"' in source,_old[:70]
    source=source.replace(': "'+_old+'"',': "'+_new+'"')
source=source.replace('ui15.css','ui37.css')

controller=Path(__file__).parent/'files/usr/lib/lua/luci/controller/homensai_vpn.lua'
import re
controller.write_text(re.sub(r'homensai-vpn/dashboard[0-9]+','homensai-vpn/dashboard59',controller.read_text(encoding='utf8')).replace('0.7.0-alpha4','0.7.0-alpha7'),encoding='utf8')
# Interactive training page: lesson cards, quiz, score.
must_replace('return view.extend({',(Path(__file__).parent/'learn_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("['help','?',bi('Help','Помощь')]];","['learn','🎓',bi('Training','Обучение')],['help','?',bi('Help','Помощь')]];")
must_replace("['overview','channels','statistics','settings','help'].map(tabLink)","['overview','channels','statistics','settings','help','learn'].map(tabLink)")
must_replace("  help:['What to do when something is wrong.'","  learn:['A short interactive training: what the system is, how to use it and what to do when something goes wrong.','Короткое интерактивное обучение: что это за система, как ею пользоваться и что делать, если что-то пошло не так.'],\n  help:['What to do when something is wrong.'")
must_replace("put('help',helpNode||(helpNode=renderHelp()));","put('help',helpNode||(helpNode=renderHelp()));put('learn',learnNode||(learnNode=renderLearn()));")
must_replace("var helpNode=null;","var helpNode=null,learnNode=null;") if "var helpNode=null;" in source else None
must_replace('return view.extend({',(Path(__file__).parent/'summary_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace('return view.extend({',(Path(__file__).parent/'theme_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("E('div',{'class':'hv-page-actions'},[versionBadge,language])","E('div',{'class':'hv-page-actions'},[versionBadge,language,renderThemeSelect()])")
must_replace("E('i',{'class':'hv-series-'+(i%colors.length)}),p.name]","E('i',{'class':'hv-series-'+(i%colors.length)}),serverTitle(p)]")
must_replace("E('b',{},r.p.name)","E('b',{},serverTitle(r.p))")
must_replace("""metric(tr("Подключённые серверы"),active.length+' / '+rows.length,tr("Остальные профили не запускаются")),""","""metricInfo(bi('Connected VPNs','Подключённые VPN'),active.length+bi(' of ',' из ')+rows.length,bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Your router has '+rows.length+' VPN profile(s) in this list and '+active.length+' of them are connected right now. Only connected VPNs are checked. The other ones are listed but this program never connects them.','В этом списке на роутере '+rows.length+' VPN-профилей, из них сейчас подключено '+active.length+'. Проверяются только подключённые. Остальные показаны в списке, но эта программа их никогда не подключает.')),""")
must_replace("""metric(tr("Проверки сейчас"),healthy.length+tr(" из ")+active.length+' OK',tr("HTTPS и DNS с роутера · IPv4")),""","""metricInfo(bi('VPNs that work','VPN, которые работают'),healthy.length+bi(' of ',' из ')+active.length,bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Of the connected VPNs, this many passed the latest check: the router could open a website and resolve a name through them. This is the same number as in the coloured card at the top.','Из подключённых VPN столько прошли последнюю проверку: роутер смог открыть сайт и найти адрес через них. Это то же число, что в цветной карточке вверху.')),""")
must_replace("""metric(tr("Трафик месяца"),month?bytes(month.rx+month.tx):tr("Нет данных"),tr("Неполный период · с начала наблюдения")),""","""metricInfo(bi('Traffic this month','Трафик за месяц'),month?bytes(month.rx+month.tx):bi('No data','Нет данных'),bi('Tap for details','Нажмите, чтобы узнать больше'),bi('Data that went through your VPNs since the monitor was started. It is counted from the first measurement, so the month may be incomplete.','Данные, прошедшие через ваши VPN с запуска мониторинга. Считаются с первого измерения, поэтому месяц может быть неполным.')),""")
must_replace("+(p.channel||'default')+' · '+(p.interface||bi('Not connected'","+bi('Group: ','Группа: ')+(p.channel||'default')+' · '+(p.interface||bi('Not connected'")
must_replace("planning.appendChild(E('code',{},(fp.blockers||[]).join(' · ')));","planning.appendChild(renderPlanBlockers(fp.blockers||[],status));")
must_replace('return view.extend({',(Path(__file__).parent/'error_table.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("      sortableTables();showPage(activeTab);","      put('statistics',renderMonitorInfo(status,inventory));put('events',errorTable||(errorTable=renderErrorTable()));\n      sortableTables();showPage(activeTab);")
import localize_tables
source=localize_tables.apply(source)
import sidebar_patch
source=sidebar_patch.apply(source)
(root/'dashboard59.js').write_text(source,encoding='utf8')
print('Generated dashboard59.js with sidebar, language persistence and sortable tables')
