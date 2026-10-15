function histogram(accounting,onPeriod,period){
  function dateKey(date){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);}
  var today=dateKey(new Date()),parts=today.split('-').map(Number),weekStart=new Date(Date.UTC(parts[0],parts[1]-1,parts[2]-6)).toISOString().slice(0,10);
  var section=E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Server uptime and failures','Работа серверов и сбои'))]);
  section.appendChild(E('select',{'aria-label':bi('Statistics period','Период статистики'),'change':function(ev){onPeriod(ev.target.value);}},[
    E('option',{value:'day',selected:period==='day'},bi('Today','Сегодня')),E('option',{value:'week',selected:period==='week'},bi('Last 7 calendar days','Последние 7 календарных дней')),E('option',{value:'month',selected:period==='month'},bi('Current calendar month','Текущий календарный месяц'))]));
  var profiles=Object.keys(accounting.activity||{}).map(function(key){var p=accounting.activity[key],totals={up:0,down:0,unknown:0,connections:0,failures:0};Object.keys(p.days||{}).forEach(function(day){if(period==='day'?day!==today:period==='week'?day<weekStart||day>today:day.slice(0,7)!==today.slice(0,7))return;Object.keys(totals).forEach(function(k){totals[k]+=p.days[day][k]||0;});});return {p:p,t:totals};});
  if(!profiles.length)section.appendChild(E('p',{},bi('History starts with this release. No earlier observations are invented.','История начинается с этой версии. Предыдущие измерения не придумываются.')));
  ['openvpn','wireguard'].forEach(function(protocol){
    section.appendChild(E('h4',{},protocol==='openvpn'?'OpenVPN':'WireGuard'));
    var group=E('div',{'class':'hv-histograms'});
    profiles.filter(function(r){return r.p.protocol===protocol;}).sort(function(a,b){return b.t.up-a.t.up;}).forEach(function(r){
      var total=r.t.up+r.t.down+r.t.unknown,bar=E('div',{'class':'hv-stack'});
      [['up','#16a892'],['down','#e46673'],['unknown','#a8b3c6']].forEach(function(entry){var value=r.t[entry[0]],percent=total?100*value/total:0;if(value)bar.appendChild(E('span',{style:'height:'+percent+'%;background:'+entry[1],title:entry[0]+': '+(value/3600).toFixed(2)+' h · '+percent.toFixed(1)+'%'},percent>=12?percent.toFixed(0)+'%':''));});
      group.appendChild(E('div',{'class':'hv-histogram'},[E('strong',{},(r.t.up/3600).toFixed(2)+' h'),bar,E('b',{},r.p.name),E('small',{},bi('Connections: ','Подключений: ')+r.t.connections+' · '+bi('Failures: ','Сбоев: ')+r.t.failures),!total?E('small',{},bi('No active observation','Нет активных измерений')):null]));
    });section.appendChild(group);
  });
  section.appendChild(E('p',{},bi('Green: confirmed healthy time · red: confirmed failure time · grey: unobserved time. Inactive reserves are excluded. Connections count observed inactive → active transitions; startup is not a new connection. Duration is estimated between probes; checkpoint gaps remain unknown.','Зелёный — подтверждённая работа, красный — сбой, серый — без измерений. Неактивные резервы исключены. Подключения — наблюдаемые переходы из неактивного состояния; запуск монитора не считается подключением. Время оценено между проверками; пропуски checkpoint остаются неизвестными.')));
  return section;
}
