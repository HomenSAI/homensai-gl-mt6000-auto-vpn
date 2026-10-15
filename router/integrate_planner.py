"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/"""
from pathlib import Path

root=Path(__file__).parent/'files/www/luci-static/resources/view/homensai-vpn'
source=(root/'dashboard11.js').read_text(encoding='utf8').replace('v0.2.0-alpha2','v0.3.0-alpha1')
settings="""
    main.option(form.Flag,'plan_enabled',bi('Enable dry-run failover planning','Включить планирование переключения без применения')).default='0';
    var planSource=main.option(form.ListValue,'plan_source',bi('Observed source profile','Наблюдаемый исходный профиль'));
    var planTarget=main.option(form.ListValue,'plan_target',bi('Proposed reserve profile','Предлагаемый резервный профиль'));
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
(root/'dashboard12.js').write_text(source,encoding='utf8')
