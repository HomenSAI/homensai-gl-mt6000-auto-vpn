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
source=source.replace("      if(heading)heading.textContent=", "      if(appRoot){var checks=appRoot.querySelector('.hv-connectivity-control');if(checks)checks.hidden=key!=='overview';}\n      if(heading)heading.textContent=")
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

source=source.replace('ui15.css','ui21.css')
(root/'dashboard40.js').write_text(source,encoding='utf8')
print('Generated dashboard40.js with sidebar, language persistence and sortable tables')

controller=Path(__file__).parent/'files/usr/lib/lua/luci/controller/homensai_vpn.lua'
import re
controller.write_text(re.sub(r'homensai-vpn/dashboard[0-9]+','homensai-vpn/dashboard40',controller.read_text(encoding='utf8')).replace('0.7.0-alpha4','0.7.0-alpha7'),encoding='utf8')
