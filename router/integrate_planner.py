"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/"""
from pathlib import Path

root=Path(__file__).parent/'files/www/luci-static/resources/view/homensai-vpn'
source=(root/'dashboard11.js').read_text(encoding='utf8').replace('v0.2.0-alpha2','v0.5.0-alpha1')
source=source.replace("Режим: наблюдение. Ни профили VPN, ни firewall не изменяются. Проверки процесса роутера ещё не подтверждают путь LAN-клиента. IPv6 здесь не проверяется.","Мониторинг активен. Состояние нативного контроллера показано ниже. Проверки роутера не подтверждают путь LAN-клиента; испытание требует отдельного клиентского подтверждения.")
source=source.replace("Monitor mode. VPN profiles and firewall remain unchanged. Router probes do not verify a LAN client's path. IPv6 is not tested.","Monitoring is active. Native controller state is shown below. Router probes do not certify the LAN client path; a trial requires separate client confirmation.")
source=source.replace("ui11.css","ui12.css")
settings="""
    main.option(form.Flag,'native_session_loss',bi('Allow calls and sessions to reconnect during a trial','Разрешить переподключение звонков и сессий во время теста')).default='0';
    var duration=main.option(form.Value,'native_duration',bi('Trial window, minutes (1–240)','Окно испытания, минут (1–240)'));duration.default='10';duration.datatype='range(1,240)';
    main.option(form.Flag,'plan_enabled',bi('Enable dry-run failover planning','Включить планирование переключения без применения')).default='0';
    var planSource=main.option(form.ListValue,'plan_source',bi('Primary VPN profile','Основной VPN-профиль'));
    var planTarget=main.option(form.ListValue,'plan_target',bi('Reserve VPN profile','Резервный VPN-профиль'));
    [planSource,planTarget].forEach(function(option){option.value('',bi('Select an existing profile','Выберите существующий профиль'));(inventory.profiles||[]).forEach(function(p){option.value(p.id,p.name+' · '+p.protocol);});});
"""
source=source.replace("    var servers=m.section(",settings+"\n    var servers=m.section(",1)
panel="""
      var fp=status.failover_plan||{state:'DISABLED',blockers:[]};
      var states={'DISABLED':bi('Dry-run planner disabled','Планировщик выключен'),'PLAN-CONFIG':bi('Select two different existing profiles in settings','Выберите два разных профиля в настройках'),'TARGET-INACTIVE':bi('Reserve is inactive; it will not be started automatically','Резерв неактивен; автоматически не запускается'),'TARGET-NOT-READY':bi('Waiting for two successful reserve probes','Ожидание двух успешных проверок резерва'),'OBSERVE':bi('Observing; no confirmed switch trigger','Наблюдение: подтверждённого повода переключать нет'),'SWITCH-RECOMMENDED':bi('Reserve recommended; live application is blocked','Резерв рекомендован; настоящее применение заблокировано')};
      var planning=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Failover plan · dry-run','План переключения · без применения')),E('strong',{},states[fp.state]||fp.state),E('p',{},bi('Three confirmed failures on the source and two successful HTTPS/DNS reserve checks are required. Unknown/stale samples do not trigger a switch. This panel never changes VPN, routes or firewall.','Нужны три подтверждённых сбоя источника и две успешные HTTPS/DNS-проверки резерва. Неизвестные и устаревшие данные не запускают переключение. Эта панель не меняет VPN, маршруты или firewall.'))]);
      if(fp.recommendation)planning.appendChild(E('p',{},bi('Proposed target: ','Предложенный резерв: ')+(rows.filter(function(p){return p.id===fp.target;})[0]||{}).name));
      planning.appendChild(E('p',{},bi('Before live use the adapter must verify worker coordination, LAN/DNS paths, Kill Switch, IPv6, special rules, scoped conntrack and an independent rollback watchdog.','Перед эксплуатацией адаптер должен подтвердить согласование workers, пути LAN/DNS, Kill Switch, IPv6, специальные правила, адресную очистку conntrack и независимый watchdog отката.')));
      planning.appendChild(E('code',{},(fp.blockers||[]).join(' · ')));
      panel.appendChild(planning);
"""
source=source.replace("      var table=E('table'",panel+"\n      var table=E('table'",1)
native="""
      var ns=status.native_failover||{state:'SERVICE-STOPPED'};
      var nativeStates={'DISABLED':bi('Disabled','Выключено'),'OBSERVING':bi('Observing','Наблюдение'),'TRIAL-REQUIRED':bi('Client trial required','Нужен клиентский тест'),'ARMED':bi('Trial passed; observing for failure','Тест пройден; наблюдение за отказом'),'APPLYING':bi('Applying trial','Применение теста'),'WAIT-CLIENT':bi('Waiting for client verification','Ожидание проверки клиента'),'COMMITTED':bi('Client-confirmed reserve selected','Выбран подтверждённый клиентом резерв'),'STOPPED':bi('Stopped','Остановлено'),'EXPIRED':bi('Trial window ended','Окно испытания завершено'),'BLOCKED':bi('Blocked','Заблокировано'),'STOPPED-ON-RESERVE':bi('Stopped on reserve; original path not restored','Остановлено на резерве; исходный путь не восстановлен'),'SERVICE-STOPPED':bi('Controller unavailable','Контроллер недоступен')};
      var descriptions={
        'HARDWARE-ACCELERATOR-UNVERIFIED':bi('Hardware acceleration is not proven disabled','Отключение аппаратного ускорения не подтверждено'),
        'SOFTWARE-ACCELERATOR-UNVERIFIED':bi('Software acceleration is not proven disabled','Отключение программного ускорения не подтверждено'),
        'SOURCE-RESERVE-NOT-CONFIGURED':bi('Select and save primary and reserve profiles','Выберите и сохраните основной и резервный профили'),
        'POLICY-ORDER-DIRECTION-UNVERIFIED':bi('The LAN helper must verify policy order','LAN-помощник должен проверить порядок правил'),
        'HISTORY-001':bi('Persistent history storage needs repair; switching is blocked','Нужно восстановить хранилище истории; переключение заблокировано'),
        'CLIENT-CONFIRMATION-TIMEOUT':bi('No valid LAN confirmation; rollback required','Нет подтверждения LAN; требуется откат'),
        'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':bi('Another writer changed policy; traffic guard retained','Другая служба изменила политику; защита трафика сохранена')
      };
      var nativePanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Native failover · controlled trial','Нативное переключение · контролируемый тест')),E('strong',{},nativeStates[ns.state]||ns.state||'UNKNOWN'),E('p',{},bi('1. Save a primary and reserve profile below. 2. Accept session reconnection. 3. Run the downloaded helper on a Windows LAN client with PowerShell 7. It checks the gateway, router DNS, HTTPS and VPN exit, and asks before starting. Browser checks alone do not certify router DNS.','1. Сохраните основной и резервный профили ниже. 2. Разрешите переподключение сессий. 3. Запустите скачанный помощник на Windows-клиенте LAN с PowerShell 7. Он проверит шлюз, DNS роутера, HTTPS и VPN-выход, затем спросит перед запуском. Проверка только браузером не подтверждает DNS роутера.'))]);
      nativePanel.appendChild(E('p',{},bi('Controller update: ','Обновление контроллера: ')+(ns.time?new Date(ns.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}):'—')));if(ns.original_restored===false)nativePanel.appendChild(E('p',{},bi('The reserve policy was retained to avoid returning to an unverified source. Current connectivity must be checked separately.','Резервная политика сохранена, чтобы не возвращаться на неподтверждённый источник. Текущую связь нужно проверять отдельно.')));
      var reasons=E('ul',{});(ns.blockers||[]).forEach(function(code){reasons.appendChild(E('li',{},code+' · '+(descriptions[code]||bi('See diagnostic code in the work log','Смотрите код диагностики в журнале работ'))));});nativePanel.appendChild(reasons);
      var nativeActions=E('div',{'class':'hv-native-actions'});
      nativeActions.appendChild(E('a',{'class':'cbi-button','href':L.resource('view/homensai-vpn/client-test.ps1'),'download':'homensai-vpn-client-test.ps1'},bi('Download LAN test helper','Скачать помощник LAN-теста')));
      nativeActions.appendChild(E('button',{'class':'cbi-button cbi-button-negative','type':'button','click':function(){return rpc.declare({object:'homensai-vpn',method:'native_stop',expect:{}})().then(function(){ui.addNotification(null,E('p',{},bi('Stop requested. Wait for verified rollback status.','Остановка запрошена. Дождитесь подтверждённого состояния отката.')));}).catch(function(){ui.addNotification(null,E('p',{},bi('Stop request failed; recovery is not confirmed.','Запрос остановки не прошёл; восстановление не подтверждено.')));});}},bi('Stop trial and restore','Остановить тест и восстановить')));
      nativePanel.appendChild(nativeActions);panel.appendChild(nativePanel);
      var nh=status.native_history||{};
      var historyPanel=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Persistent controller history','Постоянная история контроллера')),E('p',{},bi('Controller events, not measurements of LAN uptime. Trial results and automatic commits are counted separately.','События контроллера, а не измерения доступности LAN. Результаты тестов и автоматические переходы считаются отдельно.'))]);
      if(nh.error)historyPanel.appendChild(badge(nh.error));
      if(nh.restored_from_backup)historyPanel.appendChild(E('p',{},bi('History loaded from the previous valid backup; the latest event may be missing.','История прочитана из предыдущей исправной копии; последнее событие может отсутствовать.')));
      var historyTable=E('table',{'class':'table'},[E('tr',{},[E('th',{},bi('Time · Berlin','Время · Берлин')),E('th',{},bi('State','Состояние')),E('th',{},bi('Profiles','Профили')),E('th',{},bi('Reason','Причина'))])]);
      (nh.events||[]).slice().reverse().forEach(function(event){var names=[event.source,event.target].filter(Boolean).map(function(id){return (rows.filter(function(p){return p.id===id;})[0]||{}).name||id;});historyTable.appendChild(E('tr',{},[cell(new Date(event.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'})),cell(event.state+(event.trial?' · '+bi('trial','тест'):'')),cell(names.join(' → ')),cell((event.codes||[]).join(' · '))]));});historyPanel.appendChild(E('div',{'class':'hv-history-scroll'},historyTable));if(!(nh.events||[]).length)historyPanel.appendChild(E('p',{},bi('No persisted transitions yet. History begins when this controller version starts.','Постоянных событий пока нет. История начнётся после запуска этой версии контроллера.')));
      var monthly=E('table',{'class':'table'},[E('tr',{},[E('th',{},bi('Month','Месяц')),E('th',{},bi('Attempts','Попытки')),E('th',{},bi('Trials passed','Тесты пройдены')),E('th',{},bi('Automatic commits','Автопереходы')),E('th',{},bi('Rollbacks','Откаты')),E('th',{},bi('Blocked episodes','Эпизоды блокировки'))])]);
      Object.keys(nh.months||{}).sort().reverse().forEach(function(month){var c=nh.months[month];monthly.appendChild(E('tr',{},[cell(month),cell(c.attempts),cell(c.trials_passed),cell(c.committed),cell(c.rollbacks),cell(c.blocked_episodes)]));});historyPanel.appendChild(monthly);panel.appendChild(historyPanel);
"""
source=source.replace("      var table=E('table'",native+"\n      var table=E('table'",1)
(root/'dashboard14.js').write_text(source,encoding='utf8')
