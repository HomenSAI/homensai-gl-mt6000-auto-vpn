/* Overview layouts of the three page designs (A Control room, B Calm, C Instrument panel), built from the real status.
   Everything shown here is read from the router status; nothing is invented. The Auto control stays the real, working card. */
var DV_STATE_TEXT={
  'APPLYING':['Switching to the reserve','Переключение на резерв'],'WAIT-CLIENT':['Waiting for a LAN computer to confirm','Ожидание подтверждения с компьютера в сети'],
  'COMMITTED':['Reserve confirmed','Резерв подтверждён'],'ROLLED-BACK':['Rolled back to the previous route','Откат на прежний маршрут'],
  'ARMED':['Ready to switch','Готов к переключению'],'STOPPED':['Auto stopped','Auto остановлен'],'OBSERVING':['Watching the primary','Слежу за основным'],
  'BLOCKED':['Switch blocked','Переключение заблокировано'],'RESTORING':['Returning to the previous route','Возврат на прежний маршрут'],
  'DEGRADED-ON-RESERVE':['The reserve is failing too','Резерв тоже не работает'],'DISABLED':['Auto disabled','Auto выключен'],'EXPIRED':['Test window ended','Окно теста закончилось']
};
function dvStateText(state){var t=ownGet(DV_STATE_TEXT,state);return t?bi(t[0],t[1]):String(state==null?'—':state);}
function dvLocale(){return locale==='ru'?'ru-RU':'en-GB';}
function dvClock(time,seconds){return Number.isFinite(time)?new Date(time*1000).toLocaleTimeString(dvLocale(),seconds?{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',second:'2-digit'}:{timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit'}):'—';}
function dvDay(time){if(!Number.isFinite(time))return '';var d=new Date(time*1000),n=new Date(),f=function(x){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin'}).format(x);};return f(d)===f(n)?bi('today','сегодня'):new Intl.DateTimeFormat(dvLocale(),{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit'}).format(d);}
function dvProfile(rows,id){return rows.filter(function(p){return p.id===id;})[0]||null;}
function dvName(rows,id){var p=dvProfile(rows,id);return p?serverTitle(p):'—';}
function dvShortName(rows,id){var p=dvProfile(rows,id);return p?(countryName(p)||customName(p)||protocolLabel(p)):'—';}
function dvSvg(name,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',name);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,attrs[k]);});return n;}
function dvSeries(status,id,count){
  return (status.samples||[]).filter(function(s){return s.id===id&&Number.isFinite(s.rtt_ms)&&!s.code&&Number.isFinite(s.time);}).sort(function(a,b){return a.time-b.time;}).slice(-count).map(function(s){return s.rtt_ms;});
}
function dvSpark(values){
  var svg=dvSvg('svg',{'class':'hv-dv-spark','viewBox':'0 0 110 28','role':'img','aria-label':bi('Recent response times','Последние времена ответа')});
  if(values.length<2){svg.appendChild(dvSvg('line',{x1:4,x2:106,y1:14,y2:14,stroke:'var(--dv-line)','stroke-dasharray':'3 4'}));return svg;}
  var lo=Math.min.apply(null,values),hi=Math.max.apply(null,values);if(hi-lo<10){var mid=(hi+lo)/2;lo=mid-5;hi=mid+5;}
  var pts=values.map(function(v,i){return [4+i*102/(values.length-1),25-(v-lo)/(hi-lo)*22];});
  var d=pts.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1);}).join(' ');
  svg.appendChild(dvSvg('path',{d:d+' L'+pts[pts.length-1][0].toFixed(1)+' 28 L4 28 Z',fill:'var(--dv-accent)',opacity:'.12'}));
  svg.appendChild(dvSvg('path',{d:d,fill:'none',stroke:'var(--dv-accent)','stroke-width':'1.6','stroke-linejoin':'round'}));
  var e=pts[pts.length-1];svg.appendChild(dvSvg('circle',{cx:e[0].toFixed(1),cy:e[1].toFixed(1),r:'2.6',fill:'var(--dv-accent)'}));
  return svg;
}
// Checks per server: recent samples first, replaced by the hourly aggregates when the router kept them (same rule as the ranking table).
function dvRank(status){
  var rank={};
  (status.samples||[]).forEach(function(s){var r=rank[s.id]||(rank[s.id]={n:0,good:0,sum:0});if(s.code!=='CHECK-001'&&s.code!=='SYSTEM-001'){r.n++;if(!s.code){r.good++;r.sum+=s.rtt_ms||0;}}});
  var quality=(status.accounting||{}).quality||{};
  Object.keys(quality).forEach(function(id){var q=quality[id],r={n:0,good:0,sum:0};Object.keys(q.buckets||{}).forEach(function(k){var b=q.buckets[k];r.n+=b.n;r.good+=b.success;r.sum+=b.rtt_sum;});rank[id]=r;});
  return rank;
}
function dvConfidence(n){return n>=100?bi('good','высокая'):n>=20?bi('fair','средняя'):n>0?bi('low','низкая'):bi('none','нет');}
function dvPercent(r){return r&&r.n?(100*r.good/r.n):null;}
function dvPercentText(value){return value==null?'—':(value>=99.95?'100':value.toFixed(1))+'%';}
function dvEvents(status,rows,limit){
  return ((status.native_history||{}).events||[]).slice().sort(function(a,b){return b.time-a.time;}).slice(0,limit).map(function(e){
    var route=e.source&&e.target?': '+dvShortName(rows,e.source)+' → '+dvShortName(rows,e.target):'';
    return {time:e.time,text:dvStateText(e.state)+(e.trial?' ('+bi('trial','тест')+')':'')+route,codes:(e.codes||[]).slice(0,3)};
  });
}
function dvLamp(profile,now){var h=profileHealth(profile,now);return E('span',{'class':'hv-server-lamp hv-lamp-'+h.state,'role':'img','aria-label':h.label,'title':h.label});}
function dvCodes(codes){codes=codes.filter(safeCode);return codes.length?E('code',{'class':'hv-dv-code'},codes.join(' · ')):null;}
// One model for all designs: what the page says about the system right now.
function dvModel(status,inventory,rows,month){
  var now=Date.now()/1000,settings=(inventory||{}).settings||{},light=autoLightModel(status,inventory,now),counts=serverCounts(status,inventory,rows,now);
  var selected=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):selectedProfile(status,now),selectedRow=dvProfile(rows,selected),primary=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):dvProfile(rows,settings.plan_source),reserve=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):dvProfile(rows,settings.plan_target);
  var active=rows.filter(function(p){return p.interface;}),good=0,total=0;
  var rank=dvRank(status);active.forEach(function(p){var r=rank[p.id];if(r){good+=r.good;total+=r.n;}});
  var tone,headline;
  if(status.rpc_error){tone='bad';headline=bi('No data from the router','Нет данных от роутера');}
  else if(!counts.connected){tone='off';headline=bi('No VPN is connected','Ни один VPN не подключён');}
  else if(light.key==='problem'){tone='bad';headline=light.title;}
  else if(light.key==='reserve'){tone='warn';headline=bi('Working on the reserve','Работаю на резерве');}
  else if(counts.working===counts.connected){tone='ok';headline=bi('Everything works.','Всё работает.');}
  else if(counts.working===0){tone='bad';headline=bi('No VPN works right now.','Сейчас ни один VPN не работает.');}
  else{tone='warn';headline=bi('Some VPNs do not work.','Часть VPN не работает.');}
  var age=Number.isFinite(status.time)?Math.max(0,Math.round(now-status.time)):null;
  var via=selectedRow?bi('Traffic goes through ','Трафик идёт через сервер ')+serverTitle(selectedRow)+'. ':'';
  var sub=via+(age==null?bi('No fresh check.','Нет свежей проверки.'):bi('Last check '+age+' s ago.','Последняя проверка '+age+' с назад.'));
  return {now:now,settings:settings,light:light,counts:counts,selected:selected,selectedRow:selectedRow,primary:primary,reserve:reserve,active:active,tone:tone,headline:headline,sub:sub,
    passPercent:total?100*good/total:null,traffic:month?bytes(month.rx+month.tx):bi('No data','Нет данных'),rank:rank};
}
function dvKpi(label,value){return E('div',{},[E('small',{},label),E('b',{},value)]);}
function dvCard(title,children,cls){return E('section',{'class':'hv-dv-card'+(cls?' '+cls:'')},[title?E('h3',{},title):null].concat(children).filter(Boolean));}

/* ---------- A · Control room ---------- */
function dvServerRows(status,rows,m){
  var sorted=sortServerCards(rows,m.selected,m.now);
  if(!sorted.length)return E('p',{'class':'hv-dv-empty'},bi('No VPN profiles found on the router.','На роутере не найдено VPN-профилей.'));
  return E('div',{'class':'hv-dv-rows'},sorted.map(function(p){
    var h=profileHealth(p,m.now),r=m.rank[p.id],pct=dvPercent(r);
    return E('div',{'class':'hv-dv-row','data-profile':p.id},[dvLamp(p,m.now),
      E('div',{'class':'hv-dv-name'},[E('b',{},countryName(p)||customName(p)||protocolLabel(p)),E('small',{},protocolLabel(p)+' · '+(p.interface?bi('Group: ','Группа: ')+(p.channel||'default'):bi('not connected','не подключён')))]),
      dvSpark(dvSeries(status,p.id,12)),
      E('span',{'class':'hv-dv-num'},h.state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0)+' '+bi('ms','мс'):'—'),
      E('span',{'class':'hv-dv-num'},dvPercentText(pct))]);
  }));
}
function dvEventList(status,rows,limit){
  var list=dvEvents(status,rows,limit);
  if(!list.length)return E('p',{'class':'hv-dv-empty'},bi('No switches or failures are recorded on the router.','На роутере не записано ни переключений, ни сбоев.'));
  return E('ul',{'class':'hv-dv-events'},list.map(function(e){return E('li',{},[E('time',{},dvDay(e.time)+' '+dvClock(e.time)),E('span',{},e.text),dvCodes(e.codes)].filter(Boolean));}));
}
function renderDesignA(ctx,m){
  var strip=E('section',{'class':'hv-dv-strip hv-dv-tone-'+m.tone,'role':'region','aria-label':bi('Status summary','Сводка состояния')},[
    E('div',{},[E('strong',{},m.headline),E('p',{},m.sub)]),
    E('div',{'class':'hv-dv-kpis'},[dvKpi(bi('VPNs working','VPN работают'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
      dvKpi(bi('Checks passed','Проверок успешно'),dvPercentText(m.passPercent)),dvKpi(bi('Traffic this month','Трафик за месяц'),m.traffic)])]);
  var control=E('div',{'class':'hv-dv-control'},[ctx.controlCard]);
  var servers=dvCard(bi('Servers','Серверы'),[E('div',{'class':'hv-dv-rowhead','aria-hidden':'true'},[E('span'),E('span',{},bi('Server','Сервер')),E('span'),E('span',{'class':'hv-dv-num'},bi('HTTPS','HTTPS')),E('span',{'class':'hv-dv-num'},bi('Passed','Успех'))]),dvServerRows(ctx.status,ctx.rows,m)]);
  var events=dvCard(bi('Recent events','Последние события'),[dvEventList(ctx.status,ctx.rows,6),E('a',{'class':'hv-dv-more','href':'#events'},bi('All events and errors','Все события и ошибки'))]);
  return E('div',{'class':'hv-dv hv-dv-a'},[strip,E('div',{'class':'hv-dv-cols'},[E('div',{'class':'hv-dv-stack'},[control,servers]),events])]);
}

/* ---------- B · Calm ---------- */
function renderDesignB(ctx,m){
  var stats=E('div',{'class':'hv-dv-three'},[dvKpi(bi('Working VPNs','Работающие VPN'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
    dvKpi(bi('Problems today','Проблемы сегодня'),m.passPercent==null?bi('No data','Нет данных'):m.passPercent>=99.5?bi('None','Нет'):bi('Some','Есть')),dvKpi(bi('Used this month','Использовано за месяц'),m.traffic)]);
  var list=E('div',{'class':'hv-dv-list'},sortServerCards(ctx.rows,m.selected,m.now).map(function(p){
    var h=profileHealth(p,m.now),country=countryOf(p),role=m.selected===p.id?bi('In use','Используется'):m.reserve&&p.id===m.reserve.id?bi('Backup','Резерв'):p.interface?bi('Connected','Подключён'):bi('Not connected','Не подключён');
    var kind=h.state==='healthy'?'green':h.state==='checking'?'yellow':h.state==='failed'?'red':'grey';
    return E('div',{'class':'hv-dv-item','data-profile':p.id},[E('span',{'class':'hv-dv-flag','aria-hidden':'true'},country?country.code.toUpperCase():'··'),
      E('div',{},[E('b',{},countryName(p)||customName(p)||protocolLabel(p)),E('small',{},role+' · '+protocolLabel(p))]),
      E('span',{'class':'hv-dv-statuscol','data-health':h.state},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('span',{},h.state==='healthy'?bi('Works','Работает'):h.state==='inactive'?bi('Off','Выкл.'):h.label)])]);
  }));
  var autoOn=m.light.key==='ok';
  var q1=m.primary?E('div',{'class':'hv-dv-q'},[E('b',{},bi('What happens if '+(countryName(m.primary)||'the primary')+' stops working?','Что будет, если '+(countryName(m.primary)||'основной')+' перестанет работать?')),
    E('p',{},autoOn?bi('The app can consider a reserve only within a validated bounded trial, with router firmware coordination and independent LAN confirmation. Router probes alone do not authorize a switch.','Приложение может рассматривать резерв только в подтверждённом ограниченном тесте, с координацией со штатной прошивкой и независимым подтверждением LAN. Одних проверок с роутера недостаточно для разрешения переключения.'):bi('Automatic inter-tunnel switching by this app is off. The router firmware may still select servers within its own tunnel.','Автоматическое переключение между туннелями этим приложением выключено. Штатная прошивка по-прежнему может выбирать серверы внутри своего туннеля.'))]):null;
  var last=dvEvents(ctx.status,ctx.rows,1)[0];
  var q2=E('div',{'class':'hv-dv-q'},[E('b',{},bi('Last thing that happened','Последнее событие')),E('p',{},last?dvDay(last.time)+' '+dvClock(last.time)+' · '+last.text:bi('No switches or failures are recorded on the router.','На роутере не записано ни переключений, ни сбоев.'))]);
  var links=E('p',{'class':'hv-dv-links'},[E('a',{'href':'#statistics'},bi('Statistics','Статистика')),E('a',{'href':'#help'},bi('Help','Помощь')),E('a',{'href':'#learn'},bi('Training','Обучение')),E('a',{'href':'#events'},bi('Details for technicians →','Подробности для техников →'))]);
  // The state sentence block was removed (owner): the Primary/Reserve boxes in the Auto card already show it.
  return E('div',{'class':'hv-dv hv-dv-b'},[E('div',{'class':'hv-dv-control'},[ctx.controlCard]),stats,E('h3',{'class':'hv-dv-h'},bi('Your VPNs','Ваши VPN')),list,q1,q2,links].filter(Boolean));
}

/* ---------- C · Instrument panel ---------- */
function dvKv(key,value,cls){return E('span',{},[key+' ',E('b',{'class':cls||null},value)]);}
function dvLogLine(time,kind,text,codes){
  return E('div',{'class':'hv-dv-log-line hv-dv-log-'+kind},[E('time',{},dvClock(time,true)),E('b',{},kind==='ok'?'OK  ':kind==='warn'?'WARN':'FAIL'),E('span',{},text),codes&&codes.length?E('code',{'class':'hv-dv-code'},codes.join(' '))
    :null].filter(Boolean));
}
function renderDesignC(ctx,m){
  var ns=ctx.status.native_failover||{},agentVersion=(ctx.status.version||'—'),pkg=ctx.status.package||'—';
  var autoOn=m.light.key==='ok'||m.light.key==='reserve'||m.light.key==='switching';
  var bar=E('div',{'class':'hv-dv-status'},[dvKv('ctrl',String(ns.state||'UNKNOWN'),'hv-dv-k'),dvKv('auto',autoOn?'ON':'OFF'),dvKv('monitor',ctx.status.rpc_error?'?':(m.tone==='bad'&&!m.counts.connected?'?':'ON')),
    dvKv('active',m.selectedRow?(m.selectedRow.interface||m.selectedRow.id):'—'),dvKv('reserve',m.reserve?(m.reserve.interface||m.reserve.id):'—'),dvKv('pkg',String(pkg)),dvKv('ui',UI_BUILD)]);
  var chartCard=dvCard(bi('HTTPS latency, ms','HTTPS-задержка, мс'),[chart(ctx.status.samples||[],m.active)],'hv-dv-chart');
  var lines=[];
  (ctx.status.samples||[]).filter(function(s){return Number.isFinite(s.time);}).forEach(function(s){var failed=!!s.code&&s.code!=='CHECK-001';lines.push({time:s.time,kind:failed?'fail':(s.code?'warn':'ok'),text:dvShortName(ctx.rows,s.id)+' '+(Number.isFinite(s.rtt_ms)&&!s.code?'https '+Math.round(s.rtt_ms)+'ms '+(s.dns_ok?'dns ok':'dns fail'):(s.code?'':'dns '+(s.dns_ok?'ok':'fail'))),codes:s.code?[s.code]:[]});});
  dvEvents(ctx.status,ctx.rows,10).forEach(function(e){lines.push({time:e.time,kind:'warn',text:e.text,codes:e.codes});});
  lines.sort(function(a,b){return b.time-a.time;});
  var log=dvCard(bi('Event log','Журнал'),[lines.length?E('div',{'class':'hv-dv-log'},lines.slice(0,10).map(function(l){return dvLogLine(l.time,l.kind,l.text,l.codes);})):E('p',{'class':'hv-dv-empty'},bi('No checks recorded yet.','Проверок пока нет.'))],'hv-dv-logcard');
  var head=['St','Server','Proto','Group','HTTPS ms','Passed','Checks','Confidence'].map(function(h,i){return E('th',{'scope':'col','class':i>=4&&i<=6?'n':null},[bi(h,{'St':'Ст.','Server':'Сервер','Proto':'Прот.','Group':'Группа','HTTPS ms':'HTTPS, мс','Passed':'Успех','Checks':'Проверок','Confidence':'Достоверность'}[h])]);});
  var body=sortServerCards(ctx.rows,m.selected,m.now).map(function(p){
    var h=profileHealth(p,m.now),r=m.rank[p.id]||{n:0},mark=m.selected===p.id?'● use':h.state==='healthy'?'● ready':h.state==='inactive'?'○ off':'◐ '+h.state;
    return E('tr',{'class':m.selected===p.id?'hv-dv-active':null,'data-profile':p.id},[E('td',{'class':'hv-dv-st hv-dv-st-'+h.state},mark),E('td',{},countryName(p)||customName(p)||'—'),E('td',{},p.protocol==='wireguard'?'wg':'ovpn'),E('td',{},p.channel||'—'),
      E('td',{'class':'n'},h.state==='healthy'&&Number.isFinite(p.rtt_ms)?p.rtt_ms.toFixed(0):'—'),E('td',{'class':'n'},dvPercentText(dvPercent(r))),E('td',{'class':'n'},String(r.n||0)),E('td',{},dvConfidence(r.n||0))]);});
  var table=dvCard(bi('Servers','Серверы'),[E('div',{'class':'hv-dv-tablewrap'},E('table',{},[E('thead',{},E('tr',{},head)),E('tbody',{},body)]))],'hv-dv-servers');
  var keys=E('div',{'class':'hv-dv-keys'},[E('span',{},[E('kbd',{},'1'),'–',E('kbd',{},'9'),bi('sections','разделы')]),E('span',{},[E('kbd',{},'/'),bi('search','поиск')]),E('span',{},bi('Error codes are links to the error table','Коды ошибок — ссылки на таблицу ошибок'))]);
  return E('div',{'class':'hv-dv hv-dv-c'},[bar,E('div',{'class':'hv-dv-grid'},[chartCard,log]),E('div',{'class':'hv-dv-control'},[ctx.controlCard]),table,keys]);
}
function renderDesignOverview(design,ctx){
  var m=dvModel(ctx.status,ctx.inventory,ctx.rows,ctx.month);
  return design==='a'?renderDesignA(ctx,m):design==='c'?renderDesignC(ctx,m):renderDesignB(ctx,m);
}
// Keys of design C: 1..9 open the sections, "/" focuses the search box. Ignored while typing and with modifier keys.
function installDesignKeys(root,keys,go){
  if(!root||root.getAttribute('data-hv-keys'))return;root.setAttribute('data-hv-keys','1');
  document.addEventListener('keydown',function(event){
    if(root.getAttribute('data-hv-design')!=='c'||!root.isConnected||event.ctrlKey||event.metaKey||event.altKey)return;
    var el=event.target||{},tag=(el.tagName||'').toLowerCase();if(tag==='input'||tag==='textarea'||tag==='select'||el.isContentEditable)return;
    if(event.key==='/'){var box=root.querySelector('.hv-page:not([hidden]) .hv-search')||root.querySelector('.hv-search');if(box){event.preventDefault();box.focus();}return;}
    var n=Number(event.key);if(n>=1&&n<=keys.length&&/^[1-9]$/.test(event.key)){event.preventDefault();go(keys[n-1]);}
  });
}
