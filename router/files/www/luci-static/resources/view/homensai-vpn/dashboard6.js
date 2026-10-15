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
function badge(code){return E('strong',{'class':code?'label warning':'label success'},code?(codes[code]||code):'OK');}

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
    var panel=E('div',{}),self=this;
    function draw(status){
      while(panel.firstChild)panel.removeChild(panel.firstChild);
      panel.appendChild(E('p',{'class':'alert-message warning'},
        'Режим: наблюдение. Ни профили VPN, ни firewall не изменяются. Проверки процесса роутера ещё не подтверждают путь LAN-клиента. IPv6 здесь не проверяется.'));
      if(status.error)panel.appendChild(E('p',{},badge(status.error)));
      var tg=status.telegram||{};panel.appendChild(E('p',{},'Telegram: '+(tg.enabled?(tg.code||('включён · интервал '+tg.interval_minutes+' мин · последняя отправка '+(tg.last_sent?new Date(tg.last_sent*1000).toLocaleString():'ожидается'))):'отключён')));
      var rows=status.profiles||[];
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
    return m.render().then(function(form){return E('div',{},[
      E('h2',{},E('a',{href:'https://homensai.com',target:'_blank',rel:'noopener noreferrer'},'HomenSAI Auto VPN')),
      E('button',{'class':'btn cbi-button-positive','click':function(){return scanCall().then(function(){ui.addNotification(null,E('p',{},'Запрошен раунд проверок подключённых профилей.'));});}},'Проверить подключённые серверы'),panel,form]);});
  }
});
