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
function dvSeries(status,id,count){var points=websiteSamples(status).filter(function(s){return s.id===id;}).slice(-count);return points.some(function(s,i){return i&&s.time-points[i-1].time>90;})?[]:points.map(function(s){return s.rtt_ms;});}
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
function dvRank(status){return websiteQuality(status);}
function dvConfidence(n){return n>=100?bi('good','высокая'):n>=20?bi('fair','средняя'):n>0?bi('low','низкая'):bi('none','нет');}
function dvPercent(r){return r&&r.n?(100*r.good/r.n):null;}
function dvPercentText(value){return value==null?'—':(value>=99.95?'100':value.toFixed(1))+'%';}
function dvEvents(status,rows,limit){
  return ((status.native_history||{}).events||[]).slice().sort(function(a,b){return b.time-a.time;}).slice(0,limit).map(function(e){
    var t=savedTransition(e),from=t.present?t.changed&&!t.reapply&&t.from:null,to=t.present?t.changed&&!t.reapply&&t.to:null;
    var route=t.present?(from&&to?': '+dvShortName(rows,e[from])+' → '+dvShortName(rows,e[to]):''):(e.source&&e.target?': '+dvShortName(rows,e.source)+' → '+dvShortName(rows,e.target):'');
    return {time:e.time,text:dvStateText(e.state)+(e.trial?' ('+bi('trial','тест')+')':'')+route,codes:(e.codes||[]).slice(0,3)};
  });
}
function dvLamp(profile,now){var h=profileHealth(profile,now);return E('span',{'class':'hv-server-lamp hv-lamp-'+h.state,'role':'img','aria-label':h.label,'title':h.label});}
function dvChannelUse(profile,m,status){
  var h=profileHealth(profile,m.now),settings=m.settings||{},primary=m.primary&&m.primary.id===profile.id||settings.plan_source===profile.id||settings.plan_source_tunnel&&settings.plan_source_tunnel===profile.vendor_tunnel_id;
  var reserve=m.reserve&&m.reserve.id===profile.id||settings.plan_target===profile.id||settings.plan_target_tunnel&&settings.plan_target_tunnel===profile.vendor_tunnel_id;
  var role=primary?bi('Primary channel','Основной канал'):reserve?bi('Reserve channel','Резервный канал'):bi('Other VPN','Другой VPN');
  var result={role:role,label:h.label,kind:'grey',state:'unknown'};
  if(status.rpc_error||status.error||!observationFresh(status,m.now)){result.kind='red';result.state='failed';result.kind='grey';result.state='waiting';result.label=status.rpc_error?bi('No answer from the router','Нет ответа от роутера'):bi('Router data is old','Данные роутера устарели');result.code=status.rpc_error?'STATUS-REQUEST-FAILED':'MONITOR-DATA-STALE';return result;}
  var pending=typeof manualOperationModel==='function'?manualOperationModel(status,m.now):null;
  if(pending&&pending.busy&&(primary||reserve)){result.kind='grey';result.state='switching';result.label=pending.uncertain?bi('Request not confirmed','Запрос не подтверждён'):bi('Switching, waiting for the router','Переключение, ждём роутер');return result;}
  var rel=typeof channelReliability==='function'&&profile.interface&&profile.code!=='VPN-001'?channelReliability(profile,status,m.now):null;
  if(h.state==='failed'){
    result.kind='red';result.state='failed';
    if(rel&&rel.unreliable){result.label=bi('Reliability problem: ','Проблема с надёжностью: ')+reliabilityText(rel);result.code='CHANNEL-UNRELIABLE';result.reliability=rel;}
    return result;
  }
  if(h.state==='inactive'){result.label=bi('Off','Отключён');result.kind='red';result.state='off';return result;}
  if(h.state==='checking'){result.kind='grey';result.state='checking';result.label=bi('Waiting for the router\'s answer','Ждём ответа роутера');return result;}
  var route=channelPathSelection(status,m.now,m.primary&&m.primary.id||settings.plan_source,m.reserve&&m.reserve.id||settings.plan_target);
  if(route.authoritative&&!route.selected&&!route.moving&&route.code){result.kind='grey';result.state='waiting';result.label=bi('Traffic selection is not verified','Выбор канала трафика не подтверждён');result.code=route.code;return result;}
  var ns=status.native_failover||{};
  if(['ARMED','APPLYING','WAIT-CLIENT','RESTORING'].indexOf(ns.state)>=0&&Number.isFinite(ns.time)&&m.now-ns.time>=0&&m.now-ns.time<=30){result.kind='grey';result.state='switching';result.label=bi('Switching, waiting for the router','Переключение, ждём роутер');return result;}
  var autoRuns=!m.light||typeof autoWorking!=='function'||autoWorking(m.light);
  if(h.state==='healthy'&&!autoRuns){result.kind='yellow';result.state='ready';result.label=m.settings&&profile.id!==m.settings.plan_source&&profile.id!==m.settings.plan_target?bi('Other VPN: works, Auto does not use it','Другой VPN: работает, Auto его не использует'):channelAliveText(m.settings&&profile.id===m.settings.plan_target?'reserve':'primary',status,m.now);}
  else if(h.state==='healthy'){
    if(m.selected===profile.id){result.kind='green';result.state='selected';result.label=bi('Working','Работает');}
    else if(m.selected){result.kind='yellow';result.state='standby';result.label=m.settings&&profile.id!==m.settings.plan_source&&profile.id!==m.settings.plan_target?bi('Other VPN: works, Auto does not use it','Другой VPN: работает, Auto его не использует'):channelAliveText(m.settings&&profile.id===m.settings.plan_source?'primary':'reserve',status,m.now);}
    else{result.kind='grey';result.state='waiting';result.label=bi('Waiting for the router\'s answer which channel carries traffic','Ждём ответа роутера, какой канал несёт трафик');}
  }
  if(h.state==='unknown'){result.kind='grey';result.state='waiting';result.label=bi('Waiting for the router\'s answer','Ждём ответа роутера');}
  if(h.state==='healthy'&&rel&&rel.unreliable){result.kind='yellow';result.label=bi('Works, but reliability problem: ','Работает, но проблема с надёжностью: ')+reliabilityText(rel);result.code='CHANNEL-UNRELIABLE';result.reliability=rel;}
  if((result.state==='ready'||result.state==='standby')&&!result.reliability)result.badgeLabel=primary||reserve?result.label:bi('Works; Auto does not use it','Работает; Auto его не использует');
  return result;
}
function dvChannelLamp(use){return E('span',{'class':'hv-check-lamp hv-check-'+use.kind,'role':'img','aria-label':use.label,'title':use.label});}
function channelDisplayUse(profile,status,inventory){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),settings=(inventory||{}).settings||{},m={now:now,settings:settings,
    primary:vendorDisplayMember(status,inventory,'source',now),reserve:vendorDisplayMember(status,inventory,'target',now),selected:vendorDisplaySelected(status,inventory,now),
    light:typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null};
  return dvChannelUse(profile,m,status);
}
function renderChannelHeader(profile,status,inventory){
  var use=channelDisplayUse(profile,status,inventory);
  return E('div',{'class':'hv-server-top'},[E('div',{'class':'hv-channel-heading'},[dvChannelLamp(use),E('div',{'class':'hv-channel-heading-text'},[E('strong',{'class':'hv-protocol'},use.role),E('span',{'class':'hv-channel-protocol'},protocolLabel(profile))])]),
    E('span',{'class':'hv-route-badge hv-route-'+use.kind+(use.reliability||String(use.badgeLabel||use.label).length>24?' hv-route-badge-long':''),'data-route-state':use.state},(use.badgeLabel||use.label)+(safeCode(use.code)?' · '+use.code:safeCode(profile.code)?' · '+profile.code:'')),
    typeof renderChannelPing==='function'?renderChannelPing(profile,status,typeof statusNow==='function'?statusNow(status):Date.now()/1000):null,
    E('span',{'class':'hv-profile-detail'},(use.code==='STATUS-REQUEST-FAILED'||use.code==='MONITOR-DATA-STALE')?bi('The page shows nothing as working until the router answers again. Reload the page (Ctrl+F5); if it repeats, check Monitoring in Settings.','Пока роутер не ответит, страница ничего не считает рабочим. Обновите страницу (Ctrl+F5); если повторяется, проверьте мониторинг в «Настройках».'):(profile.interface?bi('VPN server connection: established','Соединение с VPN-сервером: установлено'):bi('VPN server connection: none','Соединение с VPN-сервером: нет'))+' · '+(use.state==='selected'?bi('your internet goes through this channel','ваш интернет идёт через этот канал'):use.state==='standby'?bi('spare channel, your internet does not use it now','запасной канал, ваш интернет сейчас через него не идёт'):use.state==='failed'?bi('router checks fail: internet through this channel does not work','проверки роутера не проходят: интернет через этот канал не работает'):use.state==='switching'?bi('the route is being switched','маршрут переключается'):use.state==='ready'?bi('internet works through it; it takes over as soon as Auto is on','интернет через него работает; включится в работу, как только вы включите Auto'):profileHealth(profile,typeof statusNow==='function'?statusNow(status):Date.now()/1000).state==='healthy'?bi('router checks pass','проверки роутера проходят'):bi('waiting for the router check','ждём проверку роутера')))]);
}
function dvCodes(codes){codes=codes.filter(safeCode);return codes.length?E('code',{'class':'hv-dv-code'},codes.join(' · ')):null;}
// One model for all designs: what the page says about the system right now.
function dvModel(status,inventory,rows,month){
  var now=(typeof statusNow==='function'?statusNow(status):Date.now()/1000),settings=(inventory||{}).settings||{},light=autoLightModel(status,inventory,now),counts=serverCounts(status,inventory,rows,now);
  var selected=typeof vendorDisplaySelected==='function'?vendorDisplaySelected(status,inventory,now):selectedProfile(status,now),selectedRow=dvProfile(rows,selected),primary=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'source',now):dvProfile(rows,settings.plan_source),reserve=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,'target',now):dvProfile(rows,settings.plan_target);
  var active=rows.filter(function(p){return p.interface;}),good=0,total=0;
  var rank=dvRank(status);active.forEach(function(p){var r=rank[p.id];if(r){good+=r.good;total+=r.n;}});
  var tone,headline;
  if(status.rpc_error){tone='bad';headline=bi('No data from the router','Нет данных от роутера');}
  else if(!counts.connected){tone='off';headline=bi('No VPN is connected','Ни один VPN не подключён');}
  else if(light.key==='problem'){tone='bad';headline=light.title;}
  else if(light.key==='reserve'){tone='warn';headline=bi('Working on the reserve','Работаю на резерве');}
  else if(counts.working===counts.connected){tone='ok';headline=bi('Everything works.','Всё работает.');}
  else if(counts.working===0&&counts.stale){tone='off';headline=bi('Waiting for fresh router data.','Ждём свежие данные роутера.');}
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
  var sorted=sortServerCards(rows,m.selected,m.now,[m.primary&&m.primary.id,m.reserve&&m.reserve.id]);
  if(!sorted.length)return E('p',{'class':'hv-dv-empty'},bi('No VPN profiles found on the router.','На роутере не найдено VPN-профилей.'));
  return E('div',{'class':'hv-dv-rows'},sorted.map(function(p){
    var h=profileHealth(p,m.now),use=dvChannelUse(p,m,status),r=m.rank[p.id],pct=dvPercent(r);
    return E('div',{'class':'hv-dv-row','data-profile':p.id,'data-route-state':use.state},[dvChannelLamp(use),
      E('div',{'class':'hv-dv-name'},[E('b',{},countryName(p)||customName(p)||protocolLabel(p)),E('small',{},use.role+' · '+protocolLabel(p)+' · '+use.label)]),
      dvSpark(dvSeries(status,p.id,12)),
      E('span',{'class':'hv-dv-num'},renderChannelPing(p,status,m.now)),
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
    E('div',{'class':'hv-dv-kpis'},[dvKpi(bi('VPN links ready','Доступные VPN-подключения'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
      dvKpi(bi('Checks passed','Проверок успешно'),dvPercentText(m.passPercent)),dvKpi(bi('Traffic this month','Трафик за месяц'),m.traffic)])]);
  var control=E('div',{'class':'hv-dv-control'},[ctx.controlCard]);
  var servers=dvCard(bi('Servers','Серверы'),[E('div',{'class':'hv-dv-rowhead','aria-hidden':'true'},[E('span'),E('span',{},bi('Server','Сервер')),E('span'),E('span',{'class':'hv-dv-num'},bi('Websites, ms','Сайты, мс')),E('span',{'class':'hv-dv-num'},bi('Passed','Успех'))]),dvServerRows(ctx.status,ctx.rows,m)]);
  var events=dvCard(bi('Recent events','Последние события'),[dvEventList(ctx.status,ctx.rows,6),E('a',{'class':'hv-dv-more','href':'#events'},bi('All events and errors','Все события и ошибки'))]);
  return E('div',{'class':'hv-dv hv-dv-a'},[control,strip,E('div',{'class':'hv-dv-cols'},[E('div',{'class':'hv-dv-stack'},[servers]),events])]);
}

/* ---------- B · Calm ---------- */
var DV_OTHER_VPNS_EXPANDED=false;
function dvProfileIdentity(p){
  // Only metadata already exposed by the inventory; never fetch raw VPN files.
  var names=[p.router_name,p.name].filter(function(v){return typeof v==='string'&&v.trim()&&v.trim()!==countryName(p);}).map(function(v){return v.trim().slice(0,240);});
  return names.filter(function(v,i){return names.indexOf(v)===i;}).join(' · ')||bi('Profile identity unavailable','Название профиля недоступно');
}
function renderDesignB(ctx,m){
  var stats=E('div',{'class':'hv-dv-three'},[dvKpi(bi('VPN links ready','Доступные VPN-подключения'),m.counts.connected?m.counts.working+bi(' of ',' из ')+m.counts.connected:'—'),
    dvKpi(bi('Problems today','Проблемы сегодня'),m.passPercent==null?bi('No data','Нет данных'):m.passPercent>=99.5?bi('None','Нет'):bi('Some','Есть')),dvKpi(bi('Used this month','Использовано за месяц'),m.traffic)]);
  var links=E('p',{'class':'hv-dv-links'},[E('a',{'href':'#statistics'},bi('Statistics','Статистика')),E('a',{'href':'#help'},bi('Help','Помощь')),E('a',{'href':'#learn'},bi('Training','Обучение')),E('a',{'href':'#events'},bi('Details for technicians →','Подробности для техников →'))]);
  // The state sentence block was removed (owner): the Primary/Reserve boxes in the Auto card already show it.
  return E('div',{'class':'hv-dv hv-dv-b'},[E('div',{'class':'hv-dv-control'},[ctx.controlCard]),stats,links].filter(Boolean));
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
  var chartCard=dvCard(bi('Three-site response, ms','Ответ трёх сайтов, мс'),[chart(websiteSamples(ctx.status,ctx.inventory),m.active)],'hv-dv-chart');
  var lines=[];
  (ctx.status.samples||[]).filter(function(s){return Number.isFinite(s.time);}).forEach(function(s){var failed=!!s.code&&s.code!=='CHECK-001';lines.push({time:s.time,kind:failed?'fail':(s.code?'warn':'ok'),text:dvShortName(ctx.rows,s.id)+' '+(Number.isFinite(s.rtt_ms)&&!s.code?bi('technical HTTPS ','тех. HTTPS ')+Math.round(s.rtt_ms)+'ms '+(s.dns_ok?'dns ok':'dns fail'):(s.code?'':'dns '+(s.dns_ok?'ok':'fail'))),codes:s.code?[s.code]:[]});});
  dvEvents(ctx.status,ctx.rows,10).forEach(function(e){lines.push({time:e.time,kind:'warn',text:e.text,codes:e.codes});});
  lines.sort(function(a,b){return b.time-a.time;});
  var log=dvCard(bi('Event log','Журнал'),[lines.length?E('div',{'class':'hv-dv-log'},lines.slice(0,10).map(function(l){return dvLogLine(l.time,l.kind,l.text,l.codes);})):E('p',{'class':'hv-dv-empty'},bi('No checks recorded yet.','Проверок пока нет.'))],'hv-dv-logcard');
  var head=['Channel','Status','Proto','Group','Websites ms','Passed','Checks','Confidence'].map(function(h,i){return E('th',{'scope':'col','class':i>=4&&i<=6?'n':null},[bi(h,{'Channel':'Канал','Status':'Статус','Proto':'Прот.','Group':'Группа','Websites ms':'Сайты, мс','Passed':'Успех','Checks':'Проверок','Confidence':'Достоверность'}[h])]);});
  var body=sortServerCards(ctx.rows,m.selected,m.now,[m.primary&&m.primary.id,m.reserve&&m.reserve.id]).map(function(p){
    var h=profileHealth(p,m.now),use=dvChannelUse(p,m,ctx.status),r=m.rank[p.id]||{n:0},mark=use.label;
    return E('tr',{'class':m.selected===p.id?'hv-dv-active':null,'data-profile':p.id,'data-route-state':use.state},[E('td',{'data-channel-role':use.role},[E('b',{},use.role),E('small',{},countryName(p)||customName(p)||'—')]),E('td',{'class':'hv-dv-st'},[dvChannelLamp(use),mark]),E('td',{},p.protocol==='wireguard'?'wg':'ovpn'),E('td',{},p.channel||'—'),
      E('td',{'class':'n'},renderChannelPing(p,ctx.status,m.now)),E('td',{'class':'n'},dvPercentText(dvPercent(r))),E('td',{'class':'n'},String(r.n||0)),E('td',{},dvConfidence(r.n||0))]);});
  var table=dvCard(bi('Servers','Серверы'),[E('div',{'class':'hv-dv-tablewrap'},E('table',{},[E('thead',{},E('tr',{},head)),E('tbody',{},body)]))],'hv-dv-servers');
  var keys=E('div',{'class':'hv-dv-keys'},[E('span',{},[E('kbd',{},'1'),'–',E('kbd',{},'9'),bi('sections','разделы')]),E('span',{},[E('kbd',{},'/'),bi('search','поиск')]),E('span',{},bi('Error codes are links to the error table','Коды ошибок — ссылки на таблицу ошибок'))]);
  return E('div',{'class':'hv-dv hv-dv-c'},[E('div',{'class':'hv-dv-control'},[ctx.controlCard]),bar,E('div',{'class':'hv-dv-grid'},[chartCard,log]),table,keys]);
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
