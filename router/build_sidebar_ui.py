"""HomenS.AI sidebar adapter over the pinned Style core and real LuCI monitor."""
from pathlib import Path
UI_MODULE='dashboard137'
from lazy_help_build import marked as lazy_marked

root=Path(__file__).parent/'files/www/luci-static/resources/view/homensai-vpn'
source=(root/'dashboard16.js').read_text(encoding='utf8')
def must_replace(old,new,expected=1,limit=None):
    """Apply a dashboard patch only when all intended anchors are present."""
    global source
    actual=source.count(old)
    if actual!=expected:
        raise ValueError('Sidebar anchor count: expected %d, got %d: %s' % (expected,actual,old[:100]))
    source=source.replace(old,new) if limit is None else source.replace(old,new,limit)

must_replace('return view.extend({',(Path(__file__).parent/'fool_guard.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("var locale = localStorage.getItem('homensai-vpn-language') || 'en';","""var savedLanguage='en';
try { savedLanguage=localStorage.getItem('homensai-vpn-language')||'en'; } catch(e) {}
var requestedLanguage=new URLSearchParams(window.location.search).get('lang');
var locale=(requestedLanguage||savedLanguage)==='ru'?'ru':'en';""")
must_replace('ui12.css','ui13.css')
must_replace('Автоматическое изменение маршрутов пока недоступно.','Контролируемое переключение требует клиентской проверки.',expected=2)
must_replace('Automatic route switching is unavailable.','Controlled failover requires client verification.')

anchor="    var panel=E('div',{'class':'hv-panel'}),self=this,period='day';"
assert anchor in source
must_replace(anchor,anchor+"""
    var appRoot=null,settingsHost=null,heading=null,sideState=null,versionBadge=null,pages={},sortStates={},searchTerms={};
    var tabs=[['overview','◉',bi('Overview','Обзор')],['channels','⇄',bi('Channels and servers','Каналы и серверы')],['statistics','▥',bi('Statistics','Статистика')],['traffic','◷',bi('Monthly traffic','Трафик за месяц')],['services','▣',bi('Service monitor','Монитор служб')],['events','≡',bi('Events and errors','События и ошибки')],['settings','⚙',bi('Settings','Настройки')]];
    function routerVpnUrl(){return resolveRouterVpnUrl(window.location.href,window.HOMENSAI_PREVIEW_ROUTER_ORIGIN);}
    function vpnSetupCard(){return E('section',{'class':'hv-chart-card hv-vpn-setup'},[E('div',{'class':'hv-auto-power-unit'},[E('a',{'class':'hv-auto-power hv-vpn-configure','href':routerVpnUrl()||null,'aria-disabled':routerVpnUrl()?null:'true','title':routerVpnUrl()?null:bi('Router address unavailable in this preview','Адрес роутера недоступен в этом просмотре'),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('Open router VPN settings (opens a new tab)','Открыть настройки VPN роутера (новая вкладка)')},E('span',{'aria-hidden':'true','class':'hv-configure-symbol'},'⚙')),E('strong',{'class':'hv-auto-action'},bi('Configure VPN','Настроить VPN'))]),E('p',{},[bi('Add servers and connection keys on the router page ','Добавляйте серверы и ключи на странице роутера '),routerVpnUrl()?E('a',{'class':'hv-vpn-profile-link','href':routerVpnUrl(),'target':'_blank','rel':'noopener noreferrer','aria-label':bi('VPN Client Profile (opens the router VPN settings in a new tab)','VPN Client Profile (открывает настройки VPN роутера в новой вкладке)')},'VPN Client Profile ↗'):E('span',{},'VPN Client Profile'),'.',E('br'),bi('Monitoring and failover priorities are set in this program (not on the router page): ','Мониторинг и приоритеты переключения настраиваются в этой программе (не на странице роутера): '),E('a',{'href':'#settings'},bi('Settings → All application settings → 3 · Existing VPNs','Настройки → Все настройки приложения → 3 · Существующие VPN')),'.'])]);}
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
          var entries=Array.prototype.slice.call(table.querySelectorAll('tr')).slice(1).map(function(row,i){return {row:row,i:i,role:Number(row.getAttribute('data-channel-rank')||0),value:row.children[column]?(row.children[column].getAttribute('data-sort-value')||row.children[column].textContent||''):''};});
          function unknown(v){return !v||/^(—|No data|Нет данных)$/.test(v.trim());}
          entries.sort(function(a,b){if(a.role!==b.role)return a.role-b.role;if(unknown(a.value)!==unknown(b.value))return unknown(a.value)?1:-1;var x=a.value.trim(),y=b.value.trim(),nx=Number(x.replace(/%$/,'')),ny=Number(y.replace(/%$/,''));var c=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});return (direction==='asc'?c:-c)||a.i-b.i;});
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
must_replace('      while(panel.firstChild)panel.removeChild(panel.firstChild);','      while(panel.firstChild)panel.removeChild(panel.firstChild);pages={};')

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
    must_replace(old,new)
# Remaining top-level content is the real-data overview.
must_replace("panel.appendChild(E(","put('overview',E(",expected=4)
must_replace("var ns=status.native_failover||{state:'SERVICE-STOPPED'};","""var ns=status.native_failover||{state:'SERVICE-STOPPED'};
      var stateNames={'OBSERVING':bi('Automatic monitoring','Автоматический контроль'),'ARMED':bi('Ready','Готов'),'COMMITTED':bi('Reserve confirmed','Резерв подтверждён'),'STOPPED':bi('Stopped','Остановлен'),'DISABLED':bi('Disabled','Выключен'),'EXPIRED':bi('Window ended','Окно завершено'),'WAIT-CLIENT':bi('Waiting for client','Ожидание клиента'),'APPLYING':bi('Switching','Переключение'),'BLOCKED':bi('Blocked','Заблокирован')};
      var stale=!ns.time||Date.now()/1000-ns.time>30;
      put('overview',E('section',{'class':'hv-chart-card hv-control-summary'},[E('h3',{},bi('Automatic failover','Автоматическое переключение')),E('strong',{'class':stale?'hv-warn':'hv-control-state'},stale?bi('Controller status is stale','Статус контроллера устарел'):(stateNames[ns.state]||ns.state||bi('Unknown','Неизвестно'))),E('p',{},bi('Code: ','Код: ')+(ns.state||'UNKNOWN')),E('p',{},bi('Primary: ','Основной: ')+((rows.filter(function(p){return p.id===(inventory.settings||{}).plan_source;})[0]||{}).name||'—')),E('p',{},bi('Reserve: ','Резерв: ')+((rows.filter(function(p){return p.id===(inventory.settings||{}).plan_target;})[0]||{}).name||'—')),E('p',{},bi('Updated: ','Обновлено: ')+(ns.time?new Date(ns.time*1000).toLocaleTimeString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}):'—')),E('button',{'type':'button','class':'cbi-button','click':function(){window.location.hash='settings';showPage('settings');}},bi('Controls and setup','Управление и настройка'))]));
      if(versionBadge)versionBadge.textContent='v'+(status.version||'unknown');
      if(sideState)sideState.textContent=status.error?bi('Monitor unavailable','Монитор недоступен'):bi('Router monitor online','Монитор роутера доступен');
""")
must_replace("E('strong',{},ns.state||'UNKNOWN')","E('strong',{},stateNames[ns.state]||ns.state||'UNKNOWN')")
must_replace("      var terminal=E('pre',{},[]);","""      put('services',E('p',{},bi('Times are from the router measurements. A connected interface alone is not proof of internet access.','Время берётся из измерений роутера. Подключённый интерфейс сам по себе не доказывает доступность интернета.')));
      var terminal=E('pre',{},[E('div',{},[E('span',{'class':'hv-log-time'},status.time?new Date(status.time*1000).toLocaleTimeString():'—'),E('strong',{},'  HomenS.AI monitor: '),badge(status.error)]),E('div',{},[E('span',{'class':'hv-log-time'},ns.time?new Date(ns.time*1000).toLocaleTimeString():'—'),E('strong',{},'  Auto VPN: '),stateNames[ns.state]||ns.state||'UNKNOWN'])]);""")
must_replace("    }\n    draw(data[1]);","      sortableTables();showPage(activeTab);\n    }\n    draw(data[1]);")

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
        E('aside',{'class':'hv-sidebar'},[E('a',{'class':'hv-side-brand','href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer','aria-label':bi('HomenS.AI website','Сайт HomenS.AI')},[robotHost,E('span',{},[E('strong',{},['HomenS',E('span',{'class':'ai'},'.AI')]),E('small',{},'Auto VPN')])]),E('p',{'class':'hv-model'},routerModelLabel()),E('nav',{'aria-label':bi('VPN sections','Разделы VPN')},links),E('div',{'class':'hv-side-footer'},[sideState,E('small',{},bi('Real IPv4 router measurements','Реальные IPv4-измерения роутера')),E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},bi('Developer · Serhii Khomenko','Разработчик · Serhii Khomenko')),E('small',{},'HomenS.AI Style 1.14.3')])]),
        E('main',{'class':'hv-main'},[E('header',{'class':'hv-page-header'},[E('div',{'class':'hv-header-main','style':'min-width:0;max-width:100%'},[E('div',{'class':'hv-eyebrow'},bi('AVAILABILITY CONTROL','УПРАВЛЕНИЕ ДОСТУПНОСТЬЮ')),heading,E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.'))]),E('div',{'class':'hv-page-actions'},[versionBadge,language,E('button',{'type':'button','class':'btn hv-test','click':function(){return scanCall().then(function(){return statusCall().then(draw);}).catch(function(){ui.addNotification(null,E('p',{},bi('Probe request failed. See service status.','Запрос проверки не прошёл. Смотрите состояние службы.')));});}},bi('Probe now','Проверить сейчас'))])]),panel,settingsHost,footer])
      ]);
      showPage(activeTab);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});
      return appRoot;
    });
  }
});
"""
must_replace("active.forEach(function(p)","active.sort(function(a,b){return Number(!!a.code)-Number(!!b.code);}).forEach(function(p)")
must_replace("      while(panel.firstChild)","      var focused=panel.contains(document.activeElement)&&document.activeElement.classList.contains('hv-search')?{key:document.activeElement.closest('[data-hv-page]').dataset.hvPage,start:document.activeElement.selectionStart,end:document.activeElement.selectionEnd}:null;\n      while(panel.firstChild)")
must_replace("sortableTables();showPage(activeTab);","sortableTables();showPage(activeTab);if(focused){var input=pages[focused.key]&&pages[focused.key].querySelector('.hv-search');if(input){input.focus();input.setSelectionRange(focused.start,focused.end);}}")
source='\n'.join(line for line in source.splitlines() if "put('overview',E('section',{'class':'hv-chart-card hv-control-summary'}" not in line)
must_replace("var ns=status.native_failover||{state:'SERVICE-STOPPED'};","var ns=status.native_failover||{state:'SERVICE-STOPPED'};\n      var controlCard=renderAutoControl(status,inventory);put('overview',controlCard);pages.overview.insertBefore(controlCard,pages.overview.firstChild);")
must_replace('return view.extend({',(Path(__file__).parent/'manual_panel.inc.js').read_text(encoding='utf8')+'\n'+(Path(__file__).parent/'auto_live_chart.inc.js').read_text(encoding='utf8')+'\n'+(Path(__file__).parent/'auto_panel.inc.js').read_text(encoding='utf8')+'\n'+(Path(__file__).parent/'setup_wizard.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("      showPage(activeTab);window.addEventListener","      settingsHost.insertBefore(E('div',{'class':'hv-wizard-launch'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){setupWizard(inventory,'system');}},bi('System setup wizard','Мастер настройки системы')),E('button',{'type':'button','class':'cbi-button','click':function(){setupWizard(inventory,'telegram');}},bi('Telegram channel wizard','Мастер Telegram-канала')),E('button',{'type':'button','class':'cbi-button','click':function(){return rpc.declare({object:'homensai-vpn',method:'telegram_test',expect:{}})().then(function(result){ui.addNotification(null,E('p',{},result.code||'TELEGRAM-TEST-UNKNOWN'));});}},bi('Test Telegram delivery','Проверить доставку Telegram'))]),settingsHost.firstChild);\n      showPage(activeTab);window.addEventListener")
must_replace("telegramChat.datatype='integer'","telegramChat.datatype='string'")
must_replace("var appRoot=null,settingsHost","var lastGoodStatus=data[1];\n    var appRoot=null,settingsHost")
must_replace("function draw(status){","function draw(status){\n      if(!status.rpc_error)lastGoodStatus=status;")
must_replace("poll.add(function(){return statusCall().then(draw).catch(function(){draw({error:'SERVICE-STOPPED'});});},10);","poll.add(function(){return statusCall().then(draw).catch(function(){draw(Object.assign({},lastGoodStatus,{rpc_error:'RPC-UNAVAILABLE'}));});},10);")
must_replace("statusCall().catch(function(){return {error:'SERVICE-STOPPED'};})","statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};})")
must_replace("data[1].error?bi('Monitor unavailable','Монитор недоступен')","data[1].rpc_error?bi('Status RPC unavailable','RPC статуса недоступен'):data[1].error?bi('Monitor unavailable','Монитор недоступен')")
must_replace("sideState.textContent=status.error?","sideState.textContent=status.rpc_error?bi('Status RPC unavailable','RPC статуса недоступен'):status.error?")
must_replace("var ns=status.native_failover||{state:'SERVICE-STOPPED'};","var ns=status.native_failover||{state:'UNKNOWN'};")
must_replace("if(status.error)put('overview',E('p',{},badge(status.error)));","if(status.rpc_error)put('overview',E('p',{'class':'alert-message warning'},'RPC-UNAVAILABLE: displaying last known measurements. Connectivity and service state are unconfirmed.'));\n      if(status.error)put('overview',E('p',{},badge(status.error)));")
must_replace('return view.extend({',(Path(__file__).parent/'speed_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("period='day';","period='day',speedPeriod='week';")
must_replace("      sortableTables();showPage(activeTab);","      put('ranking',speedPanel(status,inventory,speedPeriod,function(value){speedPeriod=value;draw(status);}));\n      sortableTables();showPage(activeTab);")
must_replace("      settingsHost.insertBefore","      settingsHost.appendChild(speedSettings(inventory));\n      settingsHost.insertBefore")
must_replace("cell(new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}))","E('td',{'data-sort-value':event.time},new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}))")
must_replace('return view.extend({',(Path(__file__).parent/'traffic_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("      sortableTables();showPage(activeTab);","      put('traffic',trafficHistoryPanel(status.accounting||{}));\n      sortableTables();showPage(activeTab);")
old="var monthKeys=Object.keys((status.accounting||{}).months||{}).sort(),month=monthKeys.length?(status.accounting.months[monthKeys[monthKeys.length-1]]):null;"
assert old in source
must_replace(old,"var currentMonth=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit'}).format(new Date()),month=((status.accounting||{}).months||{})[currentMonth]||null;")
old="Object.keys(p.days||{}).forEach(function(day){"
assert old in source
must_replace(old,"if(p.periods&&p.periods[period]){Object.keys(totals).forEach(function(k){totals[k]=p.periods[period][k]||0;});}else Object.keys(p.days||{}).forEach(function(day){")
must_replace("day.slice(0,7)!==today.slice(0,7)","day.slice(0,7)!==today.slice(0,7)||day>today")
must_replace('?build=060-alpha1','?build=070-alpha10')
must_replace("      settingsHost.appendChild(speedSettings(inventory));","      settingsHost.appendChild(E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Monitor service','Служба мониторинга')),E('p',{},bi('Enables measurement only. Stop Auto mode and finish rollback before disabling the monitor. Actual service state is confirmed by fresh measurements.','Включает только измерения. Перед отключением остановите авторежим и дождитесь отката. Работа службы подтверждается свежими измерениями.')),E('button',{'type':'button','class':'cbi-button','click':function(ev){ev.target.disabled=true;return rpc.declare({object:'homensai-vpn',method:'monitor_control',params:['enabled'],expect:{}})(!(inventory.settings||{}).enabled).then(function(result){ui.addNotification(null,E('p',{},result.code||'MONITOR-UNKNOWN'));if(result.accepted)window.location.reload();}).catch(function(){ui.addNotification(null,E('p',{},'MONITOR-RPC-UNCONFIRMED'));}).finally(function(){ev.target.disabled=false;});}},(inventory.settings||{}).enabled?bi('Stop monitor','Остановить мониторинг'):bi('Start monitor','Запустить мониторинг'))]));\n      settingsHost.appendChild(speedSettings(inventory));")
import json
must_replace('return view.extend({','var RECOVERY_PRESETS='+json.dumps(json.loads((Path(__file__).parent/'files/usr/lib/homensai-vpn/recovery_presets.json').read_text(encoding='utf8')),sort_keys=True)+';\nreturn view.extend({')
must_replace('return view.extend({',(Path(__file__).parent/'recovery_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("      settingsHost.appendChild(speedSettings(inventory));","      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){recoveryWizard(inventory);}},bi('Recovery setup wizard','Мастер восстановления')));\n      settingsHost.appendChild(speedSettings(inventory));")
must_replace("['statistics','▥'","['tests','⏻',bi('Operator tests','Операторские тесты')],['statistics','▥'")
must_replace('return view.extend({',(Path(__file__).parent/'fault_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("      sortableTables();showPage(activeTab);","      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));\n      sortableTables();showPage(activeTab);")
old="return m.render().then(function(formNode){"
assert old in source
must_replace(old,"return Promise.resolve(E('p',{},bi('Use the setup wizards below. Settings are validated before saving; stored tokens are never loaded into this page.','Используйте мастера ниже. Настройки проверяются до сохранения; сохранённые токены не загружаются на эту страницу.'))).then(function(formNode){")
must_replace('return view.extend({','return view.extend({\n  handleSave:null,handleSaveApply:null,handleReset:null,')
must_replace("      settingsHost.appendChild(speedSettings(inventory));","      settingsHost.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){monitorPreferences(inventory);}},bi('Monitoring and history retention','Мониторинг и хранение истории')));\n      settingsHost.appendChild(speedSettings(inventory));")
start=source.index("    var inventory=data[0],m=new form.Map")
end=source.index("    var panel=E('div',{'class':'hv-panel'})",start)
source=source[:start]+"    var inventory=data[0];\n"+source[end:]
must_replace("'require form';",'')
must_replace("var setup=!configured||new URLSearchParams(window.location.search).get('setup')==='telegram';","var setup=new URLSearchParams(window.location.search).get('setup')==='telegram';")
must_replace('return view.extend({',(Path(__file__).parent/'inventory_reliable.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
old="inventoryCall().catch(function(){return {profiles:[]};})"
assert old in source
must_replace(old,'loadInventory(0)')
must_replace("object:'homensai-vpn',","object:'homensai-vpn',reject:true,",expected=25)
must_replace("      sortableTables();showPage(activeTab);","      if(inventory.error)put('overview',E('p',{'class':'alert-message warning','role':'alert'},'RPC-INVENTORY-UNAVAILABLE: configuration is unknown. Reload after RPC recovery; empty defaults are not saved.'));\n      sortableTables();showPage(activeTab);")

must_replace('return view.extend({',(Path(__file__).parent/'ui_logic.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("active.sort(function(a,b){return Number(!!a.code)-Number(!!b.code);}).forEach","sortServerCards(active,selectedProfile(status,Date.now()/1000),Date.now()/1000).forEach")
must_replace("'class':'hv-server '+(p.code?'hv-degraded':'')","'class':'hv-server hv-health-'+profileHealth(p,Date.now()/1000).state,'data-profile':p.id,'data-health':profileHealth(p,Date.now()/1000).state")
must_replace('badge(p.code)','healthBadge(p)',expected=3)
must_replace("sortServerCards(active,selectedProfile(status,Date.now()/1000),Date.now()/1000)","sortServerCards(rows,selectedProfile(status,Date.now()/1000),Date.now()/1000)")
must_replace("E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-protocol'}","E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-server-lamp hv-lamp-'+profileHealth(p,Date.now()/1000).state,'role':'img','aria-label':profileHealth(p,Date.now()/1000).label,'title':profileHealth(p,Date.now()/1000).label}),E('span',{'class':'hv-protocol'}")

must_replace("var tableKey=(table.closest('[data-hv-page]')||{dataset:{hvPage:'overview'}}).dataset.hvPage+'-'+index,headers=table.querySelectorAll('tr:first-child th');","var headers=table.querySelectorAll('tr:first-child th'),tableKey=(table.closest('[data-hv-page]')||{dataset:{hvPage:'overview'}}).dataset.hvPage+':'+Array.from(headers).map(function(th){return th.textContent;}).join('|');")
must_replace("var c=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});return (direction==='asc'?c:-c)||a.i-b.i;","return compareTableValues(a.value,b.value,direction)||a.i-b.i;")
must_replace('return view.extend({',(Path(__file__).parent/'analytics_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("var controlCard=renderAutoControl(status,inventory);put('overview',controlCard);","var controlCard=renderAutoControl(status,inventory);put('overview',vpnSetupCard());put('overview',controlCard);put('overview',renderCascadePath(status));")
must_replace("put('events',historyPanel)","put('events',historyPanel);put('events',renderTransitionAnalytics(status))")
must_replace('ui13.css','ui15.css')
must_replace('put(\'channels\',E(\'h3\',{},tr("Подключённые VPN-серверы")))',"put('channels',vpnSetupCard());put('channels',E('h3',{},bi('Connected VPN server','Подключённый VPN-сервер')))")
must_replace('return view.extend({',(Path(__file__).parent/'router_link.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("p.channel+' · '+p.interface","(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён'))")
must_replace("Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'","profileHealth(p,Date.now()/1000).state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'")
must_replace("if(!active.length)cards.appendChild","if(!rows.length)cards.appendChild")
must_replace("healthy=active.filter(function(p){return !p.code;})","healthy=active.filter(function(p){return profileHealth(p,Date.now()/1000).state==='healthy';})")
must_replace("cell(p.rtt_ms)","cell(profileHealth(p,Date.now()/1000).state==='healthy'?p.rtt_ms:null)")
# Approved interaction/visual review: request-correlated checks and explicit actions.
must_replace('return view.extend({',(Path(__file__).parent/'connectivity_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
old="E('button',{'type':'button','class':'btn hv-test','click':function(){return scanCall().then(function(){return statusCall().then(draw);}).catch(function(){ui.addNotification(null,E('p',{},bi('Probe request failed. See service status.','Запрос проверки не прошёл. Смотрите состояние службы.')));});}},bi('Probe now','Проверить сейчас'))"
assert old in source
must_replace(old,"renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})")
must_replace('function draw(status){','function draw(status){\n      updateConnectivityCheck(status);')
must_replace("      if(heading)heading.textContent=","      if(appRoot){appRoot.querySelectorAll('.hv-connectivity-control').forEach(function(node){node.hidden=key!=='overview';});}\n      if(heading)heading.textContent=")
must_replace("bi('Configure VPN','Настроить VPN')","bi('Open router VPN settings ↗','Открыть настройки VPN роутера ↗')")
must_replace("bi('Operator tests','Операторские тесты')","bi('Diagnostics','Диагностика')")

must_replace("healthBadge(p)]","healthBadge(p),E('span',{'class':'hv-profile-detail'},bi('Connection: ','Подключение: ')+(p.interface?bi('Connected','Подключён'):bi('Inactive','Неактивен'))+' · '+bi('Traffic: ','Трафик: ')+(selectedProfile(status,Date.now()/1000)===p.id?bi('Selected','Выбран'):bi('Not confirmed as selected','Выбор не подтверждён'))+' · '+bi('Priority: ','Приоритет: ')+(p.priority||100))]",expected=2,limit=1)

must_replace("put('overview',renderCascadePath(status));","put('overview',renderCascadePath(status));put('overview',renderDecisionExplanation(status));")
must_replace("var appRoot=null,settingsHost","var pointerHeld=false,deferredStatus=null;\n    var appRoot=null,settingsHost")
must_replace("function draw(status){","function draw(status){\n      if(pointerHeld){deferredStatus=status;updateConnectivityCheck(status);return;}\n      var controlFocus=panel.contains(document.activeElement)&&document.activeElement.matches('button,input[type=checkbox],select')?{page:(document.activeElement.closest('[data-hv-page]')||{dataset:{hvPage:activeTab}}).dataset.hvPage,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.textContent,tag:document.activeElement.tagName}:null;")
must_replace("      if(inventory.error)put('overview'","      if(controlFocus&&pages[controlFocus.page]){var options=pages[controlFocus.page].querySelectorAll('button,input[type=checkbox],select');var matching=Array.from(options).find(function(el){return el.tagName===controlFocus.tag&&el.getAttribute('aria-label')===controlFocus.label&&el.textContent===controlFocus.text;});if(matching)matching.focus({preventScroll:true});}\n      if(inventory.error)put('overview'")
must_replace("      showPage(activeTab);window.addEventListener","      panel.addEventListener('pointerdown',function(){pointerHeld=true;});\n      ['pointerup','pointercancel'].forEach(function(event){window.addEventListener(event,function(){if(!pointerHeld)return;setTimeout(function(){pointerHeld=false;if(deferredStatus){var next=deferredStatus;deferredStatus=null;draw(next);}},0);});});\n      showPage(activeTab);window.addEventListener")

must_replace("put('overview',planning);","put('tests',planning);")
must_replace('return view.extend({',(Path(__file__).parent/'sidebar_layout.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("if(!validTab(key))key='overview';activeTab=key;","var oldTab=activeTab;if(!validTab(key))key='overview';activeTab=key;")
must_replace("if(heading)heading.textContent=","if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);\n      if(heading)heading.textContent=")
must_replace("E('nav',{'aria-label':bi('VPN sections','Разделы VPN')}","E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')}")
must_replace('      return appRoot;','      initSidebarLayout(appRoot);\n      return appRoot;')

must_replace('return view.extend({',(Path(__file__).parent/'incident_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace('return view.extend({',(Path(__file__).parent/'readiness_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("['settings','⚙'","['readiness','✓',bi('System readiness','Готовность системы')],['settings','⚙'")
must_replace("put('overview',renderDecisionExplanation(status));","put('overview',renderDecisionExplanation(status));put('readiness',renderReadiness(status,inventory));")
# Settings page: one grouped Setup card instead of scattered wizard buttons; one blocker dictionary.
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
        function launcher(label,hint,action,primary,guide,lockKey){return E('div',{'class':'hv-setup-item'},[guardResume(E('button',{'type':'button','class':'cbi-button'+(primary?' cbi-button-action':''),'click':action},label),lockKey),E('p',{},hint),guide?setupGuide(guide):null].filter(Boolean));}
        var testDelivery=function(ev){return telegramTestDelivery(ev.currentTarget||ev.target);};
        settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-setup-card'},[
          E('h3',{},bi('Setup','Настройка')),
          E('button',{'type':'button','class':'cbi-button cbi-button-action','data-onboarding-action':'open','click':function(){openOnboardingSettings(inventory,lastGoodStatus||data[1]);}},bi('All application settings','Все настройки приложения')),
          E('button',{'type':'button','class':'cbi-button','data-onboarding-action':'open-pair','click':function(){openOnboardingSettings(inventory,lastGoodStatus||data[1],'system');}},bi('Choose primary and reserve VPN','Выбрать основной и резервный VPN')),
          !onboardingComplete(inventory)?E('p',{'class':'alert-message warning','data-onboarding-incomplete':'1'},bi('Initial setup is incomplete. Open All application settings to review and save it. Stop and recovery controls remain available.','Первоначальная настройка не завершена. Откройте «Все настройки приложения», проверьте и сохраните её. Остановка и средства восстановления остаются доступны.')):null,
          E('p',{},bi('Simple settings for every user. Every wizard validates your input and shows a review before saving. Stored tokens are never shown again. Open “What is this and how to fill it in” under a step for examples.','Простые настройки для любого пользователя. Каждый мастер проверяет ввод и показывает обзор перед сохранением. Сохранённые токены больше не показываются. Под каждым шагом есть «Что это и как заполнить» с примерами.')),
          E('p',{'class':'hv-setup-path','aria-label':bi('Order of the steps','Порядок шагов')},[E('b',{},bi('1 · System setup','1 · Настройка системы')),E('span',{'aria-hidden':'true'},' → '),E('b',{},bi('2 · Telegram','2 · Telegram')),E('span',{'aria-hidden':'true'},' → '),E('b',{},bi('3 · Test delivery','3 · Проверка доставки')),E('small',{},bi('Press a button below to open its wizard.','Нажмите кнопку ниже, чтобы открыть мастер.'))]),
          E('div',{'class':'hv-setup-grid hv-setup-steps'},[
            launcher(bi('Auto switching rules','Правила переключения Auto'),bi('Check interval, failures, reserve readiness, attempt limit and return conditions. Stop Auto before saving.','Интервал проверок, ошибки, готовность резерва, лимит попыток и условия возврата. Перед сохранением выключите Auto.'),function(){recoveryWizard(inventory);},false,'recovery'),
            launcher(bi('1 · System setup','1 · Настройка системы'),bi('Press to open the wizard: primary and reserve VPN, names, groups, priorities and whether a short reconnection is acceptable.','Нажмите, чтобы открыть мастер: основной и резервный VPN, названия, группы, приоритеты и допустимость короткого переподключения.'),function(){setupWizard(inventory,'system');},true,'system'),
            launcher(bi('2 · Telegram channel','2 · Канал Telegram'),bi('Press to open the wizard: bot token and chat for reports. The wizard explains how to get both.','Нажмите, чтобы открыть мастер: токен бота и чат для отчётов. Мастер объясняет, как получить и то и другое.'),function(){setupWizard(inventory,'telegram');},false,'telegram'),
            launcher(bi('3 · Test Telegram delivery','3 · Проверить доставку Telegram'),bi('Press to send one test message with the saved settings. It should arrive within a few seconds.','Нажмите, чтобы отправить одно тестовое сообщение с сохранёнными настройками. Оно должно прийти за несколько секунд.'),testDelivery,false,null,'telegram-test')
          ])].filter(function(node){return node!=null;})));
        settingsHost.appendChild(E('details',{'class':'hv-chart-card hv-admin-settings'},[
          E('summary',{},bi('Advanced settings','Расширенные настройки')),
          E('p',{},bi('Fine-tuning of the switching rules and of the checks. The defaults are safe; change them only if you know why. Open the guide under each step for examples.','Тонкая настройка правил переключения и проверок. Значения по умолчанию безопасны; меняйте их, только если понимаете зачем. Под каждым шагом есть руководство с примерами.')),
          E('div',{'class':'hv-setup-grid'},[
            launcher(bi('Recovery rules','Правила восстановления'),bi('Failures before switching, reserve checks, cooldown and return policy.','Сколько сбоев до переключения, проверки резерва, пауза и политика возврата.'),function(){recoveryWizard(inventory);},false,'recovery'),
            launcher(bi('Monitoring parameters','Параметры мониторинга'),bi('Check interval, profile limit and statistics saving.','Интервал проверок, лимит профилей и сохранение статистики.'),function(){monitorPreferences(inventory);},false,'monitoring')
          ])]));
        if(speedCard){put('tests',E('h2',{},bi('VPN speed tests','Тесты скорости VPN')));put('tests',setupGuide('speed'));put('tests',speedCard);}
      })();
"""
must_replace("      panel.addEventListener('pointerdown',function(){pointerHeld=true;});", reorganizer+"      panel.addEventListener('pointerdown',function(){pointerHeld=true;});")
must_replace('070-alpha10','080-alpha8')
# Overview copy: one calm monitoring note; Telegram has its own tile, so only a real error is shown.
note_old='tr("Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.")'
assert note_old in source
must_replace(note_old,"bi('Monitoring is active. Router checks show tunnel health only; they do not prove the path of a computer on the LAN. Auto switching is confirmed separately by the LAN helper.','Мониторинг работает. Проверки роутера показывают только состояние туннелей и не доказывают путь компьютера в LAN. Автопереключение подтверждается отдельно LAN-помощником.')")
telegram_old="var tg=status.telegram||{};put('overview',E('p',{},'Telegram: '+(tg.enabled?(tg.code||(tr(\"включён · интервал \")+tg.interval_minutes+tr(\" мин · последняя отправка \")+(tg.last_sent?new Date(tg.last_sent*1000).toLocaleString():tr(\"ожидается\")))):tr(\"отключён\"))));"
assert telegram_old in source
must_replace(telegram_old,"var tg=status.telegram||{};if(tg.enabled&&tg.code)put('overview',E('p',{'class':'alert-message warning'},'Telegram: '+tg.code));")
# Simpler Overview and navigation: details move to Diagnostics / Service monitor; admin pages sit behind "Advanced".
import re as _r
must_replace("put('overview',vpnSetupCard());put('overview',controlCard);put('overview',renderCascadePath(status));put('overview',renderDecisionExplanation(status));","put('overview',controlCard);put('tests',renderCascadePath(status));put('tests',renderDecisionExplanation(status));")
source,_n=_r.subn(r"put\('overview',(E\('p',\{'class':'alert-message warning'\},\s*bi\('Monitoring is )",r"put('services',\1",source,count=1)
assert _n==1,'monitor note'
must_replace('return view.extend({',"""var ADVANCED_KEYS=['tests','statistics','traffic','services','events'];
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
  readiness:['Look at the items below: when all of them are green, your system is ready for Auto.','Посмотрите на пункты ниже: когда все они зелёные, ваша система готова к Auto.']
};
return view.extend({""")
must_replace("var appRoot=null,settingsHost=null,heading=null,","var subtitle=null,advancedBox=null,advancedToggle=null,appRoot=null,settingsHost=null,heading=null,")
must_replace("heading,E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одком месте.'))".replace('одком','одном'),"heading,(subtitle=E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.')))")
must_replace("if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];","""if(heading)heading.textContent=key==='overview'?bi('Your internet under control','Ваш интернет под контролем'):tabs.filter(function(t){return t[0]===key;})[0][2];
      if(subtitle&&PAGE_SUBTITLES[key])subtitle.textContent=bi(PAGE_SUBTITLES[key][0],PAGE_SUBTITLES[key][1]);
      if(oldTab!==key&&advancedBox&&ADVANCED_KEYS.indexOf(key)>=0&&advancedBox.hidden){advancedBox.hidden=false;if(advancedToggle)advancedToggle.setAttribute('aria-expanded','true');}""")
must_replace("var links=tabs.map(function(tab){return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);});","""function tabLink(key){var tab=tabs.filter(function(t){return t[0]===key;})[0];return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'click':function(){showPage(tab[0]);}},[E('span',{'aria-hidden':'true'},tab[1]),E('span',{},tab[2])]);}
      var advancedOpen=false;try{advancedOpen=localStorage.getItem('homensai-vpn-advanced')==='1';}catch(e){}
      if(ADVANCED_KEYS.indexOf(activeTab)>=0)advancedOpen=true;
      advancedBox=E('div',{'class':'hv-advanced-links','id':'hv-advanced-links'},ADVANCED_KEYS.map(tabLink));advancedBox.hidden=!advancedOpen;
      advancedToggle=E('button',{'type':'button','class':'hv-advanced-toggle','aria-controls':'hv-advanced-links','aria-expanded':advancedOpen?'true':'false','aria-label':bi('Advanced settings','Расширенные настройки'),'title':bi('Advanced settings','Расширенные настройки'),'click':function(){var open=advancedBox.hidden;advancedBox.hidden=!open;advancedToggle.setAttribute('aria-expanded',open?'true':'false');try{localStorage.setItem('homensai-vpn-advanced',open?'1':'0');}catch(e){}}},[E('span',{'class':'hv-advanced-icon','aria-hidden':'true'},'☰'),E('span',{'class':'hv-advanced-label'},bi('Advanced settings','Расширенные настройки'))]);
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
# Read-only vendor tunnel identity and inter-channel planning diagnostics.
must_replace('return view.extend({',(Path(__file__).parent/'vendor_diagnostics.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("put('channels',renderServerSummary(status,inventory,rows));","put('channels',renderServerSummary(status,inventory,rows));put('channels',renderVendorChannels(status,inventory));")
must_replace("put('events',renderTransitionAnalytics(status));","put('events',renderTransitionAnalytics(status));put('events',renderVendorEvents(status,inventory));")
# Technical threshold explanation lives in Help, away from the current controls.
must_replace("put('tests',renderDecisionExplanation(status));","")
# The old dry-run table is not a live certification display. Reuse the real
# readiness page and the current test's own prerequisites instead.
# Current display selection follows a trusted saved tunnel when firmware changes its member.
must_replace('selectedProfile(status,Date.now()/1000)','vendorDisplaySelected(status,inventory,Date.now()/1000)',expected=2)
# Idle/active check control moves to the left of the page header, under the subtitle.
must_replace("E('div',{'class':'hv-page-actions'},[versionBadge,language,renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})])","E('div',{'class':'hv-page-actions'},[versionBadge,language])")
must_replace("(subtitle=E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.')))","(subtitle=E('p',{},bi('Channels, servers and switching reasons in one place.','Каналы, серверы и причины переключений — в одном месте.'))),renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})")
# The shared subtitle can be followed by an absent connectivity widget. Never render that null child.
must_replace("renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})]),E('div',{'class':'hv-page-actions'}", "renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})].filter(function(node){return node!=null;})),E('div',{'class':'hv-page-actions'}")
# Built-in Help page: static topics, created once so opened topics stay open while the status refreshes.
must_replace('return view.extend({',lazy_marked('help_panel',(Path(__file__).parent/'help_panel.inc.js').read_text(encoding='utf8'))+'\nreturn view.extend({')
must_replace("['settings','⚙',bi('Settings','Настройки')]];","['settings','⚙',bi('Settings','Настройки')],['help','?',bi('Help','Помощь')]];")
must_replace("put('readiness',renderReadiness(status,inventory));","put('readiness',renderReadiness(status,inventory));put('help',helpNode||(helpNode=renderHelp(inventory)));")
# First-run terms gate: nothing else is rendered until the terms version is stored on the router.
_terms_version=_r.search(r"^TERMS_VERSION = '([^']+)'",(Path(__file__).parent/'files/usr/lib/homensai-vpn/agent.py').read_text(encoding='utf8'),_r.M).group(1)
must_replace('return view.extend({',(Path(__file__).parent/'terms_panel.inc.js').read_text(encoding='utf8').replace('__TERMS_VERSION__',_terms_version)+'\nreturn view.extend({')
must_replace("    var inventory=data[0];\n","    var inventory=data[0];\n    if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory,data[1]);\n")
# The complete first-entry editor follows explicit terms; the same renderer remains in Settings.
must_replace('return view.extend({',(Path(__file__).parent/'onboarding_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("    var inventory=data[0];\n","    var inventory=data[0];\n    onboardingDisplayDefaults(inventory);\n")
must_replace("    if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory,data[1]);\n","    if(!inventory.error&&!termsAccepted(inventory))return renderTermsGate(inventory,data[1]);\n    if(!inventory.error&&!onboardingComplete(inventory)&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);\n")
# Installed identity (package/program/page) and part-mismatch notice.
_agent_version=_r.search(r"^VERSION = '([^']+)'",(Path(__file__).parent/'files/usr/lib/homensai-vpn/agent.py').read_text(encoding='utf8'),_r.M).group(1)
must_replace('return view.extend({',(Path(__file__).parent/'identity_panel.inc.js').read_text(encoding='utf8').replace('__UI_BUILD__',UI_MODULE).replace('__UI_AGENT__',_agent_version)+'\nreturn view.extend({')
must_replace("E('small',{},'HomenS.AI Style 1.14.3')","E('small',{},'HomenS.AI Style 1.14.3'),E('small',{'class':'hv-identity'},identityLine(data[1]))")
must_replace("pages.overview.insertBefore(controlCard,pages.overview.firstChild);","pages.overview.insertBefore(controlCard,pages.overview.firstChild);pages.overview.insertBefore(renderSummary(status,inventory),controlCard.nextSibling);var identityNotice=renderIdentityNotice(status);if(identityNotice)pages.overview.insertBefore(identityNotice,pages.overview.firstChild);")
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
    must_replace(': "'+_old+'"',': "'+_new+'"')
must_replace('ui15.css','ui103.css',expected=3)

controller=Path(__file__).parent/'files/usr/lib/lua/luci/controller/homensai_vpn.lua'
import re
controller.write_text(re.sub(r'homensai-vpn/dashboard[0-9]+','homensai-vpn/'+UI_MODULE,controller.read_text(encoding='utf8')).replace('0.7.0-alpha4','0.7.0-alpha7'),encoding='utf8')
menu=Path(__file__).parent/'files/usr/share/luci/menu.d/luci-app-homensai-vpn.json'
menu_source,menu_count=re.subn(r'homensai-vpn/dashboard[0-9]+','homensai-vpn/'+UI_MODULE,menu.read_text(encoding='utf8'))
assert menu_count==1,'current dashboard menu path'
menu.write_text(menu_source,encoding='utf8')
# Interactive training page: lesson cards, quiz, score.
must_replace('return view.extend({',lazy_marked('learn_scenes',(Path(__file__).parent/'learn_scenes.inc.js').read_text(encoding='utf8'))+'\n'+lazy_marked('learn_panel',(Path(__file__).parent/'learn_panel.inc.js').read_text(encoding='utf8'))+'\nreturn view.extend({')
must_replace("['help','?',bi('Help','Помощь')]];","['learn','🎓',bi('Training','Обучение')],['help','?',bi('Help','Помощь')]];")
must_replace("['overview','channels','statistics','settings','help'].map(tabLink)","['overview','channels','statistics','settings','help','learn'].map(tabLink)")
must_replace("  help:['What to do when something is wrong.'","  learn:['A short interactive training: what the system is, how to use it and what to do when something goes wrong.','Короткое интерактивное обучение: что это за система, как ею пользоваться и что делать, если что-то пошло не так.'],\n  help:['What to do when something is wrong.'")
must_replace("put('help',helpNode||(helpNode=renderHelp(inventory)));","put('help',helpNode||(helpNode=renderHelp(inventory)));put('learn',learnNode||(learnNode=renderLearn()));")
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
must_replace("planning.appendChild(renderPlanBlockers(fp.blockers||[],status));","planning.appendChild(E('p',{},[E('a',{'href':'#readiness'},bi('Current system readiness','Текущая готовность системы')),bi('. Each test below checks its own current prerequisites before starting.','. Каждый тест ниже проверяет свои текущие условия перед запуском.')]));")
must_replace('return view.extend({',lazy_marked('error_rows_extra',(Path(__file__).parent/'error_rows_extra.inc.js').read_text(encoding='utf8'))+'\nreturn view.extend({')
must_replace('return view.extend({',lazy_marked('error_table',(Path(__file__).parent/'error_table.inc.js').read_text(encoding='utf8'))+'\nreturn view.extend({')
must_replace("      sortableTables();showPage(activeTab);","      put('statistics',renderMonitorInfo(status,inventory));put('events',errorTable||(errorTable=renderErrorTable()));\n      sortableTables();showPage(activeTab);")
# Page design A/B/C: chosen in Settings, stored in this browser, applied before the page is shown.
must_replace('return view.extend({',(Path(__file__).parent/'design_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("appRoot=E('div',{'class':'hv-app hv-workspace'},[","appRoot=E('div',{'class':'hv-app hv-workspace','data-hv-design':currentDesign()},[")
must_replace("        settingsHost.appendChild(E('details',{'class':'hv-chart-card hv-admin-settings'},[","        settingsHost.appendChild(renderDesignPicker(function(){return appRoot;},function(){updateSidebarLayout(appRoot,true);draw(lastGoodStatus||data[1]);}));\n        settingsHost.appendChild(E('details',{'class':'hv-chart-card hv-admin-settings'},[")
# The icon column of design C hides the labels, so every section link carries its name as a tooltip.
must_replace("return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],","return E('a',{'href':'#'+tab[0],'data-hv-tab':tab[0],'title':tab[2],")
# Owner attributes (name, device, developer, version/package/page, style) at the bottom of every page in every design.
must_replace('return view.extend({',(Path(__file__).parent/'attribution_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("panel,settingsHost,footer])","panel,settingsHost,renderAttribution(data[1]),footer])")
# Design overviews (A/B/C) built from the real status. A failure in them leaves the original overview in place (data-hv-dv marks success).
must_replace('return view.extend({',(Path(__file__).parent/'design_views.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("if(identityNotice)pages.overview.insertBefore(identityNotice,pages.overview.firstChild);","if(identityNotice)pages.overview.insertBefore(identityNotice,pages.overview.firstChild);try{pages.overview.insertBefore(renderDesignOverview(currentDesign(),{status:status,inventory:inventory,rows:rows,month:month,controlCard:controlCard}),identityNotice?identityNotice.nextSibling:pages.overview.firstChild);pages.overview.setAttribute('data-hv-dv','1');}catch(designError){pages.overview.insertBefore(controlCard,pages.overview.firstChild);pages.overview.insertBefore(E('p',{'class':'alert-message warning'},'DESIGN-VIEW-ERROR: '+String(designError&&designError.message||designError).slice(0,120)),pages.overview.firstChild);}")
must_replace("var oldTab=activeTab;if(!validTab(key))key='overview';activeTab=key;","var oldTab=activeTab;if(!validTab(key))key='overview';activeTab=key;if(appRoot)appRoot.setAttribute('data-hv-active',key);")
# Current server checks: a separate Status column with a live lamp (green works, yellow checking, red failure, grey
# off/unknown), and the rows that work come first. The lamp's rank is also its sort value.
must_replace("""var table=E('table',{'class':'table'},[E('tr',{'class':'tr table-titles'},[tr("Сервер"),""","""var table=E('table',{'class':'table hv-check-table'},[E('tr',{'class':'tr table-titles'},[bi('Status','Статус'),tr("Сервер"),""")
must_replace("rows.forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[cell(serverTitle(p)),","sortServerCards(rows,selectedProfile(status,Date.now()/1000),Date.now()/1000).forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[checkLampCell(p),cell(serverTitle(p)),")
must_replace('return view.extend({',"""function checkLampCell(p){
  var h=profileHealth(p,Date.now()/1000),rank={healthy:1,checking:2,unknown:3,inactive:4,failed:5}[h.state]||9;
  var kind=h.state==='healthy'?'green':h.state==='checking'?'yellow':h.state==='failed'?'red':'grey';
  return E('td',{'class':'hv-check-status','data-sort-value':String(rank)},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('span',{'class':'hv-check-word'},h.label)]);
}
return view.extend({""")
# Getting started is its own first section; new users land there until every step is done, then on the Overview.
must_replace("var tabs=[['overview','◉',bi('Overview','Обзор')],","var tabs=[['start','▶',bi('Getting started','Начало работы')],['overview','◉',bi('Overview','Обзор')],")
must_replace("['overview','channels','statistics','settings','help','learn'].map(tabLink)","['start','readiness','overview','channels','settings','help','learn'].map(tabLink)")
must_replace("if(!validTab(activeTab))activeTab='overview';","if(!validTab(activeTab))activeTab=startLanding(data[1],data[0]);")
must_replace("put('learn',learnNode||(learnNode=renderLearn()));","put('learn',learnNode||(learnNode=renderLearn()));put('start',renderStartPage(status,inventory));")
must_replace("  learn:['A short interactive training","  start:['First steps: terms, training, monitoring, your two VPNs and Auto. This page opens first until they are done.','Первые шаги: условия, обучение, мониторинг, два ваших VPN и Auto. Эта страница открывается первой, пока они не выполнены.'],\n  learn:['A short interactive training")
# Settings LAN trial card: why the helper exists, how to get it, links to the full guide and the AI prompt; launcher download too.
must_replace("nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')));","nativePanel.appendChild(lanHelperExplain());nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN helper','Скачать LAN-помощник')));nativePanel.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/start-lan-helper.ps1'),'download':'start-lan-helper.ps1'},bi('Download launcher','Скачать запуск')));")
# One place for speed: the Tests page shows the server ranking, the speed test button/results and, right under them, the speed settings.
must_replace("      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));","      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));\n      put('tests',E('h2',{'class':'hv-speed-heading'},bi('Speed tests and server ranking','Тесты скорости и рейтинг серверов')));put('tests',E('p',{},bi('Which servers are fastest and most reliable, and the button to measure speed. If a server needs settings (budget, duration, streams), they are right below the table: change them and press the test button here.','Какие серверы быстрее и надёжнее, и кнопка замера скорости. Если нужны настройки (бюджет, длительность, потоки), они сразу под таблицей: измените их и нажмите кнопку теста здесь.')));if(pages.ranking){while(pages.ranking.firstChild)pages.tests.appendChild(pages.ranking.firstChild);}if(speedCardNode){put('tests',E('h3',{},bi('Speed test settings','Настройки тестов скорости')));put('tests',setupGuide('speed'));put('tests',speedCardNode);}")
must_replace("if(speedCard){put('tests',E('h2',{},bi('VPN speed tests','Тесты скорости VPN')));put('tests',setupGuide('speed'));put('tests',speedCard);}","if(speedCard){speedCardNode=speedCard;speedCard.setAttribute('id','hv-speed-settings');put('tests',E('h3',{},bi('Speed test settings','Настройки тестов скорости')));put('tests',setupGuide('speed'));put('tests',speedCard);}")
must_replace('return view.extend({',"var speedCardNode=null;\nreturn view.extend({")
# Accessibility: skip link, focus moves to the page heading when the user opens another section, heading is focusable.
must_replace("appRoot=E('div',{'class':'hv-app hv-workspace','data-hv-design':currentDesign()},[","appRoot=E('div',{'class':'hv-app hv-workspace','data-hv-design':currentDesign()},[E('a',{'class':'hv-skip','href':'#','click':function(ev){ev.preventDefault();var m=appRoot.querySelector('main');if(m){m.setAttribute('tabindex','-1');m.focus();}}},bi('Skip to content','К содержимому')),")
must_replace("heading=E('h1',{},bi('Your internet under control','Ваш интернет под контролем'));","heading=E('h1',{'tabindex':'-1'},bi('Your internet under control','Ваш интернет под контролем'));")
must_replace("      if(subtitle&&PAGE_SUBTITLES[key])","      if(oldTab!==key&&heading&&document.body.contains(heading)){try{heading.focus({preventScroll:true});}catch(focusError){}}\n      if(subtitle&&PAGE_SUBTITLES[key])")
# Stop and Return belong to the Auto card on the Overview; the Settings LAN-trial card keeps the helper download and points there.
source,_stops=_r.subn(r"      nativePanel\.appendChild\(E\('button',\{'class':'cbi-button cbi-button-negative'[^\n]*\n","      nativePanel.appendChild(E('p',{},[bi('Stop Auto or return to the primary on the Overview, in the Automatic VPN failover card. ','Остановить Auto или вернуться на основной можно на «Обзоре», в блоке «Автоматическое переключение VPN». '),E('a',{'href':'#overview'},bi('Open the Overview','Открыть «Обзор»'))]));\n",source,count=1)
assert _stops==1,'settings stop button'
# The page/program version notice is not shown on any page any more (owner): only a quiet link in the attribution line opens its Help topic.
must_replace("if(identityNotice)pages.overview.insertBefore(identityNotice,pages.overview.firstChild);try{","try{")
must_replace("controlCard:controlCard}),identityNotice?identityNotice.nextSibling:pages.overview.firstChild);","controlCard:controlCard}),pages.overview.firstChild);")
must_replace("put('readiness',renderReadiness(status,inventory));","put('readiness',readinessIntro());put('readiness',renderReadiness(status,inventory));")
must_replace("put('tests',planning);","/* Forecast presentation removed; controller checks remain independent. */")
import localize_tables
source=localize_tables.apply(source)
import sidebar_patch
source=sidebar_patch.apply(source)
must_replace("fillSideStatus(sideState,status,inventory);","fillSideStatus(sideState,status,inventory);refreshAttribution(status);")
must_replace("initSidebarLayout(appRoot);installErrorLinks(appRoot);","initSidebarLayout(appRoot);installErrorLinks(appRoot);installModalStyle();installTopButton(appRoot);installDesignKeys(appRoot,tabs.map(function(t){return t[0];}),function(k){window.location.hash=k;showPage(k);});")
fool_css='\n.hv-fool-field .hv-fool-hint,.hv-fool-field .hv-fool-error{display:block;margin-top:.3rem}.hv-fool-error{color:#c32938}.hv-fool-error:empty{display:none}.hv-fool-invalid{border-color:#c32938!important;outline:1px solid #c32938}\n'
must_replace('return view.extend({',(Path(__file__).parent/'viewport_state.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace('var oldTab=activeTab;','var oldTab=activeTab;if(oldTab!==key)rememberPageViewport(appRoot||panel,oldTab);')
must_replace('if(oldTab!==key){try{window.scrollTo(0,0);if(document.scrollingElement)document.scrollingElement.scrollTop=0;}catch(e){}}',
             'if(oldTab!==key)revisitPageViewport(appRoot||panel,key);')
must_replace('function draw(status){','function draw(status){\n      var refreshViewport=rememberPageViewport(appRoot||panel,activeTab);\n      try {')
must_replace('    }\n    draw(data[1]);','      } finally {if(refreshViewport&&refreshViewport.page===activeTab)restorePageViewport(appRoot||panel,refreshViewport);}\n    }\n    draw(data[1]);')
must_replace('initSidebarLayout(appRoot);','initSidebarLayout(appRoot);installViewportPersistence(appRoot,function(){return activeTab;});installSpeedLive(appRoot,function(){return activeTab;});')
must_replace("panel.querySelectorAll('table').forEach(function(table,index){","panel.querySelectorAll('table').forEach(function(table,index){if(table.closest('.hv-errtable'))return;")
must_replace("(nh.events||[]).slice().reverse().forEach(function(event)","var transitionMarks=controllerTransitionMarks(nh.events||[]);\n      (nh.events||[]).slice().reverse().forEach(function(event)")
must_replace("cell(event.state+(event.trial?' · '+'trial':''))","E('td',{},[renderTransitionBadge(event,transitionMarks),event.state+(event.trial?' · '+'trial':'')].filter(Boolean))")
must_replace("if(nh.error)historyPanel.appendChild(badge(nh.error));","historyPanel.appendChild(E('p',{},bi('M = main, R = reserve. The arrow shows the direction. Yellow marks an unconfirmed transition; after confirmation green is selected and red is not selected.','M — основной, R — резервный. Стрелка показывает направление. Жёлтый — переход без подтверждения; после подтверждения зелёный — выбран, красный — не выбран.')));if(nh.error)historyPanel.appendChild(badge(nh.error));")
must_replace(".forEach(function(p){cards.appendChild(",".forEach(function(p){var channelUse=channelDisplayUse(p,status,inventory);cards.appendChild(")
source,_channel_headers=_r.subn(r"E\('div',\{'class':'hv-server-top'\},\[.*?\]\),\n        E\('h4'", "renderChannelHeader(p,status,inventory),\n        E('h4'",source,count=1)
assert _channel_headers==1,'channel role/status header'
must_replace("'data-health':profileHealth(p,Date.now()/1000).state}","'data-health':profileHealth(p,Date.now()/1000).state,'data-route-state':channelUse.state}")
must_replace('function checkLampCell(p){','function checkLampCell(p,status,inventory){')
must_replace('checkLampCell(p),cell(serverTitle(p))','checkLampCell(p,status,inventory),cell(serverTitle(p))')
must_replace("var kind=h.state==='healthy'?'green':h.state==='checking'?'yellow':h.state==='failed'?'red':'grey';\n  return E('td',{'class':'hv-check-status'", "var use=channelDisplayUse(p,status,inventory),kind=use.kind;h.label=use.label;\n  return E('td',{'class':'hv-check-status'")
must_replace('button,input[type=checkbox],select','button,input[type=checkbox],input[type=range],select',expected=2)
must_replace("?{page:(document.activeElement.closest", "?{node:document.activeElement,page:(document.activeElement.closest")
must_replace("if(controlFocus&&pages[controlFocus.page]){var options=pages[controlFocus.page].querySelectorAll('button,input[type=checkbox],input[type=range],select');var matching=Array.from(options).find(function(el){return el.tagName===controlFocus.tag&&el.getAttribute('aria-label')===controlFocus.label&&el.textContent===controlFocus.text;});if(matching)matching.focus({preventScroll:true});}","restorePageControlFocus(pages,controlFocus);")
must_replace('renderConnectivityCheck(data[1],function(){return statusCall().then(draw);})','renderConnectivityCheck(data[1],function(){return statusCall().then(draw);},inventory)')
# Owner follow-up: fixed roles and bounded disclosures, without routing writes.
must_replace('Monitoring is on. The checks run from the router and show whether each VPN works; they cannot prove what a computer on your network sees. That is confirmed separately by the LAN helper before Auto may switch.','The terminal shows real router observations. A separate optional LAN-helper test checks what a client sees; it is not required for prepared router-probed Auto mode.')
must_replace('Мониторинг включён. Проверки выполняет сам роутер и показывают, работает ли каждый VPN; они не доказывают, что видит компьютер в вашей сети. Это отдельно подтверждает LAN-помощник перед включением Auto.','Терминал показывает реальные наблюдения роутера. Отдельный необязательный LAN-тест проверяет связь клиента; для подготовленного router-probed авторежима он не обязателен.')
must_replace('return view.extend({',(Path(__file__).parent/'journal_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace('return view.extend({',(Path(__file__).parent/'live_terminal.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("put('events',historyPanel);","put('events',renderEventHistory(status));")
must_replace("if(table.closest('.hv-errtable'))return;","if(table.closest('.hv-errtable')||table.hasAttribute('data-hv-no-sort'))return;")
must_replace('return view.extend({',(Path(__file__).parent/'latency_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace('return view.extend({',(Path(__file__).parent/'channel_guidance.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
must_replace("var cards=E('div',{'class':'hv-server-grid'});","var cards=E('div',{'class':'hv-server-grid'}),cardHosts=channelCardHosts(rows,status,inventory,cards);")
must_replace("sortServerCards(rows,vendorDisplaySelected(status,inventory,Date.now()/1000),Date.now()/1000).forEach(function(p){var channelUse=channelDisplayUse(p,status,inventory);cards.appendChild(","roleOrderedRows(rows,status,inventory,Date.now()/1000).forEach(function(p){var channelUse=channelDisplayUse(p,status,inventory);cardHosts.get(p).appendChild(")
must_replace("put('channels',cards);","cardHosts.finish();put('channels',cards);put('channels',renderLatencyPanel(status,inventory));")
must_replace("addSearch('channels',table);put('channels',table)","addSearch('channels',table);put('channels',limitTableRows(table,5,'current-checks-other'))")
must_replace("addSearch('ranking',ranking);put('ranking',ranking);","addSearch('ranking',ranking);put('ranking',limitTableRows(ranking,5,'server-ranking-other'));")
must_replace("sortServerCards(rows,selectedProfile(status,Date.now()/1000),Date.now()/1000).forEach(function(p){table.appendChild", "currentCheckOrderedRows(rows,status,inventory,Date.now()/1000).forEach(function(p){table.appendChild")
must_replace("cell(serverTitle(p)),cell(p.channel),cell(protocolLabel(p))", "cell(serverTitle(p)),cell(roleDescription(p,status,inventory)),cell(protocolLabel(p))")
must_replace("checkLampCell(p,status,inventory),cell(serverTitle(p)),cell(roleDescription(p,status,inventory))", "checkLampCell(p,status,inventory),currentCheckServerCell(p,Date.now()/1000),cell(roleDescription(p,status,inventory))")
must_replace("checkLampCell(p,status,inventory),currentCheckServerCell(p,Date.now()/1000),cell(roleDescription(p,status,inventory))","currentCheckRoleCell(p,status,inventory),checkLampCell(p,status,inventory),currentCheckServerCell(p,Date.now()/1000)")
must_replace("[bi('Status','Статус'),tr(\"Сервер\"),tr(\"Канал\")","[tr(\"Канал\"),bi('Status','Статус'),tr(\"Сервер\")")
must_replace("currentCheckOrderedRows(rows,status,inventory,Date.now()/1000).forEach(function(p){table.appendChild(E('tr',{'class':'tr'},","currentCheckOrderedRows(rows,status,inventory,Date.now()/1000).forEach(function(p){table.appendChild(E('tr',{'class':'tr','data-channel-rank':String(currentCheckRole(p,status,inventory,routerWall()))},")
must_replace("E('h4',{'class':'hv-server-country'},countryLabel(p)),E('p',{},(customName(p)?customName(p)+' · ':'')+bi('Group: ','Группа: ')+(p.channel||'default')+' · '+(p.interface||bi('Not connected','Не подключён')))","E('h4',{'class':'hv-server-country'},countryLabel(p)),E('p',{'class':'hv-server-address'},endpointText(p,Date.now()/1000)),E('p',{},roleDescription(p,status,inventory))")
must_replace("renderCascadePath(status))","renderCascadePath(status,inventory))")
must_replace("E('small',{},'HomenS.AI Style 1.14.3'),",'')

# Overview tools belong to the first Auto card; retain the same RPC and freshness renderers.
must_replace("var controlCard=renderAutoControl(status,inventory);", "var controlCard=renderAutoControl(status,inventory,function(){return statusCall().then(draw);});")
must_replace(",E('div',{'class':'hv-tools-row'},[renderConnectivityCheck(data[1],function(){return statusCall().then(draw);},inventory),renderMonitorBlock(data[1],inventory)])", "")

# The monitor title and terminal already explain the live view.
must_replace("put('services',E('p',{},bi('A live log of the router checks. “Connected” alone does not mean the internet works.','Живой журнал проверок роутера. Одного «подключено» мало, чтобы считать, что интернет работает.')));", "")
# Keep the live monitor first; optional explanation belongs below its terminal.
source,_services_note=_r.subn(r"put\('services',E\('p',\{'class':'alert-message warning'\},\s*bi\('The terminal shows real router observations\..*?\)\)\);",'',source,count=1,flags=_r.S)
assert _services_note==1,'live terminal optional LAN explanation'
must_replace("put('services',renderLiveLog(status,rows,ns,inventory,stateNames));", """put('services',renderLiveLog(status,rows,ns,inventory,stateNames));
      var terminalExplanation=E('details',{'class':'hv-chart-card','data-live-explanation':'scope'},[
        E('summary',{},bi('About router observations and the LAN test','О наблюдениях роутера и LAN-тесте')),
        E('p',{},bi('The terminal shows real router observations. A separate optional LAN-helper test checks what a client sees; it is not required for prepared router-probed Auto mode.','Терминал показывает реальные наблюдения роутера. Отдельный необязательный LAN-тест проверяет связь клиента; для подготовленного router-probed авторежима он не обязателен.'))]);
      if(typeof rememberDisclosure==='function')rememberDisclosure(terminalExplanation,'live-terminal-explanation');
      put('services',terminalExplanation);""")

must_replace('renderTransitionAnalytics(status)','renderTransitionAnalytics(status,inventory)')

# Keep the LuCI dependency directives first. Scope the child guard to this module,
# covering every page/modal without modifying LuCI globals or meaningful text.
must_replace("'require ui';", "'require ui';\n"+(Path(__file__).parent/'element_guard.inc.js').read_text(encoding='utf8'))

from simple_home_patch import apply as apply_simple_home
source=apply_simple_home(source)
from hybrid_release_patch import apply as apply_hybrid_release
source=apply_hybrid_release(source)
must_replace('return view.extend({',(Path(__file__).parent/'preparation_control.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
(root/'ui103.css').write_text((root/'ui39.css').read_text(encoding='utf8').rstrip('\n')+'\n'+(Path(__file__).parent/'design_layer.css').read_text(encoding='utf8')+fool_css+'\n'+(Path(__file__).parent/'simple_home.css').read_text(encoding='utf8')+'\n'+(Path(__file__).parent/'hybrid_ui.css').read_text(encoding='utf8'),encoding='utf8',newline='')
from lazy_help_build import split as split_lazy_help
source=split_lazy_help(source,UI_MODULE)
# All headline delay/quality surfaces use the same complete three-site metric.
must_replace("chart(status.samples||[],active)","chart(websiteSamples(status,inventory),active)")
must_replace("cell(profileHealth(p,Date.now()/1000).state==='healthy'?p.rtt_ms:null)","cell(renderChannelPing(p,status,statusNow(status)))")
must_replace("profileHealth(p,Date.now()/1000).state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'","renderChannelPing(p,status,statusNow(status))")
must_replace('tr("HTTPS, мс")','bi("Response, ms","Ответ, мс")')
must_replace('tr("Средняя HTTPS-задержка")','bi("Mean three-site response","Средний ответ трёх сайтов")')
must_replace("(item.r.sum/item.r.good).toFixed(1)","websiteMs(item.r.sum/item.r.good)")
must_replace("var samples=status.samples||[],rank={};samples.forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});", "var samples=websiteSamples(status,inventory),rank=websiteQuality(status);")
must_replace("Object.keys((status.accounting||{}).quality||{}).forEach(function(id){var q=status.accounting.quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});", "")

from visible_refresh_patch import apply as apply_visible_refresh
source=apply_visible_refresh(source)
# The frozen legacy chart declaration is overwritten by the final renderer.
_dead_chart="function chart(samples,rows){\n  var colors="
assert source.count(_dead_chart)==1 and source.count('function chart(samples,rows){')==2,'DEAD-CHART-COUNT'
_dead_start=source.index(_dead_chart);_dead_end=source.index('\nfunction histogram(',_dead_start)
source=source[:_dead_start]+source[_dead_end+1:]
assert source.count('function chart(samples,rows){')==1 and 'var CHART_COLORS=' in source,'FINAL-CHART-COUNT'
(root/(UI_MODULE+'.js')).write_text(re.sub(r'(?m)^[ \t]+$','',source),encoding='utf8')
print('Generated '+UI_MODULE+'.js with sidebar, language persistence and sortable tables')
