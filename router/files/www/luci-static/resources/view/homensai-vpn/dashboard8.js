'use strict';
'require view';
'require form';
'require rpc';
'require poll';
'require ui';

var statusCall=rpc.declare({object:'homensai-vpn',method:'status',expect:{}});
var inventoryCall=rpc.declare({object:'homensai-vpn',method:'inventory',expect:{}});
var scanCall=rpc.declare({object:'homensai-vpn',method:'scan',expect:{}});
var codes={
  'VPN-001':'Туннель не подключён', 'VPN-003':'HTTPS через VPN не проходит',
  'DNS-001':'DNS не отвечает', 'ROUTE-001':'Маршрут не соответствует VPN',
  'CHECK-001':'Путь проверки не подтверждён', 'SYSTEM-001':'Ошибка службы или зависимости',
  'STORAGE-001':'Ошибка сохранения статистики', 'STORAGE-RECOVERED':'Статистика восстановлена из резервной копии', 'CLOCK-001':'Время роутера ещё не установлено', 'PROFILE-INACTIVE':'Профиль сейчас не подключён',
  'CHECK-LIMIT':'Профиль вне лимита текущего раунда', 'SERVICE-STOPPED':'Служба остановлена'
};
function text(value){return value==null?'—':String(value);}
function bytes(value){return Number.isFinite(value)?(value/1000000000).toFixed(3)+' GB':'—';}
function cell(value){return E('td',{},text(value));}
function badge(code){return E('strong',{'class':'hv-badge '+(!code?'hv-ok':code==='PROFILE-INACTIVE'?'hv-idle':'hv-warn')},code?(codes[code]||code):'OK');}
function metric(label,value,detail){return E('div',{'class':'hv-metric'},[E('span',{},label),E('strong',{},text(value)),E('small',{},detail)]);}
function chart(samples,rows){
  var colors=['#5268f4','#16a892','#f3a64b','#e674a3'],ns='http://www.w3.org/2000/svg';
  function svgNode(name,attrs,content){var n=document.createElementNS(ns,name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});if(content)n.textContent=content;return n;}
  var good=samples.filter(function(s){return Number.isFinite(s.rtt_ms)&&!s.code&&s.time;});
  if(good.length<2)return E('div',{'class':'hv-empty'},'График появится после двух успешных измерений. Искусственных данных здесь нет.');
  var end=Math.max.apply(null,good.map(function(s){return s.time;})),start=Math.max(end-3600,Math.min.apply(null,good.map(function(s){return s.time;})));
  good=good.filter(function(s){return s.time>=start;});
  var max=Math.max(100,Math.ceil(Math.max.apply(null,good.map(function(s){return s.rtt_ms;}))/100)*100);
  var svg=svgNode('svg',{viewBox:'0 0 820 260',role:'img','aria-label':'История HTTPS-задержки подключённых серверов в миллисекундах'});
  [0,0.5,1].forEach(function(f){var y=215-f*180;svg.appendChild(svgNode('line',{x1:55,x2:800,y1:y,y2:y,stroke:'#e8edf5'}));svg.appendChild(svgNode('text',{x:5,y:y+4,fill:'#7b899f','font-size':12},String(Math.round(max*f))));});
  var legend=E('div',{'class':'hv-legend'});
  rows.filter(function(p){return good.some(function(s){return s.id===p.id;});}).forEach(function(p,i){
    var points=good.filter(function(s){return s.id===p.id;}).sort(function(a,b){return a.time-b.time;}),path='',previous;
    points.forEach(function(s){var x=55+(s.time-start)/Math.max(1,end-start)*745,y=215-s.rtt_ms/max*180;path+=(previous&&s.time-previous<=90?' L':' M')+x.toFixed(1)+','+y.toFixed(1);previous=s.time;});
    svg.appendChild(svgNode('path',{d:path,fill:'none',stroke:colors[i%colors.length],'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'}));
    legend.appendChild(E('span',{},[E('i',{style:'background:'+colors[i%colors.length]}),p.name]));
  });
  svg.appendChild(svgNode('text',{x:55,y:247,fill:'#7b899f','font-size':12},new Date(start*1000).toLocaleTimeString()));
  svg.appendChild(svgNode('text',{x:800,y:247,fill:'#7b899f','font-size':12,'text-anchor':'end'},new Date(end*1000).toLocaleTimeString()));
  return E('div',{'class':'hv-chart'},[svg,legend,E('small',{},'HTTPS, мс · последние доступные измерения за час. Разрывы длиннее 90 секунд не соединяются.')]);
}

return view.extend({
  load:function(){return Promise.all([inventoryCall().catch(function(){return {profiles:[]};}),statusCall().catch(function(){return {error:'SERVICE-STOPPED'};})]);},
  render:function(data){
    var inventory=data[0],m=new form.Map('homensai_vpn','HomenSAI Auto VPN',
      'Нативный монитор alpha: реальные IPv4 HTTPS/DNS-проверки на роутере. Автоматическое изменение маршрутов пока недоступно.');
    var main=m.section(form.NamedSection,'main','main','Служба наблюдения');
    main.option(form.Flag,'enabled','Включить наблюдение').default='0';
    var interval=main.option(form.Value,'interval','Интервал, секунд');interval.datatype='range(10,300)';interval.default='30';
    var limit=main.option(form.Value,'probe_limit','Лимит подключённых профилей за раунд');limit.datatype='range(1,32)';limit.default='16';
    var checkpoint=main.option(form.Value,'checkpoint','Сохранение статистики во flash, секунд');checkpoint.datatype='range(300,3600)';checkpoint.default='900';
    main.option(form.Flag,'telegram_enabled','Отправлять отчёты в Telegram').default='0';
    var telegramInterval=main.option(form.Value,'telegram_interval','Интервал Telegram-отчётов, минут');telegramInterval.datatype='range(5,10080)';telegramInterval.default='60';
    var telegramChat=main.option(form.Value,'telegram_chat','Telegram Chat ID');telegramChat.datatype='integer';
    var telegramToken=main.option(form.Value,'telegram_token','Токен Telegram-бота');telegramToken.password=true;
    var servers=m.section(form.GridSection,'server','Каналы и существующие профили');servers.anonymous=true;servers.addremove=true;
    var name=servers.option(form.Value,'name','Ваше название');name.datatype='maxlength(64)';
    var profile=servers.option(form.ListValue,'profile','Профиль роутера');profile.rmempty=false;
    (inventory.profiles||[]).forEach(function(p){profile.value(p.id,p.name+' · '+p.protocol+(p.interface?' · '+p.interface:''));});
    var channel=servers.option(form.Value,'channel','Ваш канал');channel.default='main';channel.datatype='maxlength(64)';
    var priority=servers.option(form.Value,'priority','Приоритет');priority.datatype='range(1,1000)';priority.default='100';
    servers.option(form.Flag,'enabled','Наблюдать').default='1';
    var panel=E('div',{'class':'hv-panel'}),self=this;
    function draw(status){
      while(panel.firstChild)panel.removeChild(panel.firstChild);
      panel.appendChild(E('p',{'class':'alert-message warning'},
        'Режим: наблюдение. Ни профили VPN, ни firewall не изменяются. Проверки процесса роутера ещё не подтверждают путь LAN-клиента. IPv6 здесь не проверяется.'));
      if(status.error)panel.appendChild(E('p',{},badge(status.error)));
      var tg=status.telegram||{};panel.appendChild(E('p',{},'Telegram: '+(tg.enabled?(tg.code||('включён · интервал '+tg.interval_minutes+' мин · последняя отправка '+(tg.last_sent?new Date(tg.last_sent*1000).toLocaleString():'ожидается'))):'отключён')));
      var rows=status.profiles||[];
      var active=rows.filter(function(p){return p.interface;}),healthy=active.filter(function(p){return !p.code;});
      var monthKeys=Object.keys((status.accounting||{}).months||{}).sort(),month=monthKeys.length?(status.accounting.months[monthKeys[monthKeys.length-1]]):null;
      panel.appendChild(E('div',{'class':'hv-metrics'},[
        metric('Подключённые серверы',active.length+' / '+rows.length,'Остальные профили не запускаются'),
        metric('Проверки сейчас',healthy.length+' из '+active.length+' OK','HTTPS и DNS с роутера · IPv4'),
        metric('Трафик месяца',month?bytes(month.rx+month.tx):'Нет данных','Неполный период · с начала наблюдения'),
        metric('Telegram',tg.enabled?(tg.code?'Ошибка':'Каждые '+tg.interval_minutes+' мин'):'Отключён',tg.last_sent?'Отправлен '+new Date(tg.last_sent*1000).toLocaleTimeString():'Нет подтверждённой отправки')
      ]));
      panel.appendChild(E('h3',{},'Подключённые VPN-серверы'));
      var cards=E('div',{'class':'hv-server-grid'});
      active.forEach(function(p){cards.appendChild(E('article',{'class':'hv-server '+(p.code?'hv-degraded':'')},[
        E('div',{'class':'hv-server-top'},[E('span',{'class':'hv-protocol'},p.protocol==='wireguard'?'WireGuard':'OpenVPN'),badge(p.code)]),
        E('h4',{},p.name),E('p',{},p.channel+' · '+p.interface),
        E('div',{'class':'hv-latency'},[E('strong',{},Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'),E('span',{},' мс · HTTPS')]),
        E('small',{},'Измерено '+(p.time?new Date(p.time*1000).toLocaleTimeString():'нет данных'))
      ]));});
      if(!active.length)cards.appendChild(E('div',{'class':'hv-empty'},'Подключённые серверы не обнаружены.'));
      panel.appendChild(cards);
      panel.appendChild(E('section',{'class':'hv-chart-card'},[E('h3',{},'Задержка серверов во времени'),chart(status.samples||[],active)]));
      var table=E('table',{'class':'table'},[E('tr',{'class':'tr table-titles'},['Сервер','Канал','Протокол','Интерфейс','Результат','HTTPS, мс','Время проверки'].map(function(t){return E('th',{},t);} ))]);
      rows.forEach(function(p){table.appendChild(E('tr',{'class':'tr'},[cell(p.name),cell(p.channel),cell(p.protocol),cell(p.interface),E('td',{},badge(p.code)),cell(p.rtt_ms),cell(p.time?new Date(p.time*1000).toLocaleTimeString():'—')]));});
      panel.appendChild(E('h3',{},'Текущие проверки серверов'));panel.appendChild(table);
      panel.appendChild(E('p',{},'Неактивные профили перечислены без запуска: тестирование такого сервера требует отдельного согласованного окна подключения.'));
      var samples=status.samples||[],rank={};samples.forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
      Object.keys((status.accounting||{}).quality||{}).forEach(function(id){var q=status.accounting.quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
      var ranked=rows.map(function(p){return {p:p,r:rank[p.id]||{n:0,good:0,sum:0}};}).sort(function(a,b){return (b.r.n?b.r.good/b.r.n:-1)-(a.r.n?a.r.good/a.r.n:-1)||(a.r.good?a.r.sum/a.r.good:Infinity)-(b.r.good?b.r.sum/b.r.good:Infinity);});
      var ranking=E('table',{'class':'table'},[E('tr',{},['Рейтинг измеренных профилей','Успех проверок','Средняя HTTPS-задержка'].map(function(t){return E('th',{},t);}))]);
      ranked.forEach(function(item){ranking.appendChild(E('tr',{},[cell(item.p.name),cell(item.r.n?(100*item.r.good/item.r.n).toFixed(1)+'%':'Нет данных'),cell(item.r.good?(item.r.sum/item.r.good).toFixed(1)+' мс':'—')]));});
      panel.appendChild(ranking);panel.appendChild(E('p',{},'Это рейтинг по часовым агрегатам до семи дней наблюдения, не тест пропускной способности. Приоритеты не применяются автоматически.'));
      var accounting=status.accounting||{},months=accounting.months||{};
      panel.appendChild(E('h3',{},'VPN-трафик по календарным месяцам · Europe/Berlin'));
      var traffic=E('table',{'class':'table'},[E('tr',{},['Месяц','Входящий','Исходящий','Всего','Наблюдение'].map(function(t){return E('th',{},t);}))]);
      Object.keys(months).sort().reverse().forEach(function(key){var v=months[key];traffic.appendChild(E('tr',{},[cell(key),cell(bytes(v.rx)),cell(bytes(v.tx)),cell(bytes(v.rx+v.tx)),cell((v.seconds/3600).toFixed(1)+' интерфейс-часов'+(v.boundary_estimated?' · граница оценена':''))]));});
      panel.appendChild(traffic);panel.appendChild(E('p',{},'Уникальные VPN-интерфейсы считаются один раз. Это объёмы интерфейсов, включая служебный трафик. Пропуски наблюдения: '+text(accounting.gaps||0)+'. После потери питания возможна потеря последнего интервала checkpoint.'));
      panel.appendChild(E('h3',{},'Монитор служб'));
      var terminal=E('pre',{},[]);rows.slice(0,20).forEach(function(p){terminal.appendChild(E('div',{'class':p.code?'error':'notice'},[E('strong',{},p.protocol+' / '+p.name+': '),badge(p.code)]));});panel.appendChild(terminal);
      panel.appendChild(E('button',{'class':'btn','click':function(){var blob=new Blob([JSON.stringify({mode:'router-monitor',events:status.events||[]},null,2)],{type:'application/json'});var url=URL.createObjectURL(blob),link=E('a',{href:url,download:'homensai-vpn-events.json'});link.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}},'Скачать журнал'));
    }
    draw(data[1]);
    poll.add(function(){return statusCall().then(draw).catch(function(){draw({error:'SERVICE-STOPPED'});});},10);
    return m.render().then(function(form){return E('div',{'class':'hv-app'},[
      E('link',{rel:'stylesheet',href:L.resource('view/homensai-vpn/ui8.css')}),
      E('header',{'class':'hv-hero'},[
        E('div',{},[E('div',{'class':'hv-eyebrow'},'GL.iNet GL-MT6000 · LIVE MONITOR'),E('h2',{},E('a',{href:'https://homensai.com',target:'_blank',rel:'noopener noreferrer'},'HomenSAI Auto VPN')),E('p',{},'Серверы, качество связи и трафик — реальные измерения на роутере')]),
        E('button',{'class':'btn hv-test','click':function(){return scanCall().then(function(){ui.addNotification(null,E('p',{},'Запрошен раунд проверок подключённых профилей.'));});}},'Проверить сейчас')
      ]),panel,E('details',{'class':'hv-settings'},[E('summary',{},'Настройки мониторинга, Telegram и названия серверов'),form])]);});
  }
});
