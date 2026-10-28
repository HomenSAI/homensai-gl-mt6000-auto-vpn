/* Read-only role layout and disclosures. Never changes configured priority or routes. */
var HV_DISCLOSURES=Object.create(null);
function rememberDisclosure(node,key){
  if(HV_DISCLOSURES[key]===true)node.setAttribute('open','open');
  node.addEventListener('toggle',function(){HV_DISCLOSURES[key]=node.open===true;});return node;
}
function rolePairIds(status,inventory,now){
  var settings=(inventory||{}).settings||{},rows=(status||{}).profiles||[];
  function member(role,key){
    var p=typeof vendorDisplayMember==='function'?vendorDisplayMember(status,inventory,role,now):null;
    return p&&p.id||settings[key]||(status.native_failover||{})[role]||null;
  }
  return [member('source','plan_source'),member('target','plan_target')];
}
function roleOrderedRows(rows,status,inventory,now){
  var ids=rolePairIds(status,inventory,now);
  return rows.map(function(p,i){var role=ids.indexOf(p.id);return {p:p,i:i,rank:role<0?2:role};}).sort(function(a,b){return a.rank-b.rank||a.i-b.i;}).map(function(row){return row.p;});
}
function currentCheckRole(p,status,inventory,now){var n=rolePairIds(status,inventory,now).indexOf(p.id);return n<0?2:n;}
function currentCheckRoleCell(p,status,inventory){var n=currentCheckRole(p,status,inventory,routerWall());return E('td',{'data-channel-role':['source','target','other'][n],'data-sort-value':String(n)},roleDescription(p,status,inventory));}
function currentCheckOrderedRows(rows,status,inventory,now){
  return roleOrderedRows(rows,status,inventory,now).map(function(p,i){
    var use=typeof channelDisplayUse==='function'?channelDisplayUse(p,status,inventory):{state:'unknown',kind:'grey'};
    var rank=use.state==='selected'&&use.kind==='green'?0:use.state==='standby'?1:['checking','switching'].indexOf(use.state)>=0?2:use.state==='unknown'?3:4;
    return {p:p,index:i,rank:rank,role:currentCheckRole(p,status,inventory,now)};
  }).sort(function(a,b){return a.role-b.role||a.rank-b.rank||a.index-b.index;}).map(function(row){return row.p;});
}
function splitRoleRows(rows,status,inventory,now){
  var ids=rolePairIds(status,inventory,now),ordered=roleOrderedRows(rows,status,inventory,now),pair=ordered.filter(function(p){return ids.indexOf(p.id)>=0;});
  if(!pair.length)pair=ordered.slice(0,2);
  return {pair:pair,other:ordered.filter(function(p){return !pair.some(function(q){return p.id===q.id;});})};
}
function channelCardHosts(rows,status,inventory,cards){
  var split=splitRoleRows(rows,status,inventory,(typeof routerWall==='function'?routerWall():Date.now()/1000)),ids=split.pair.map(function(p){return p.id;}),other=E('div',{'class':'hv-server-grid'});
  var details=rememberDisclosure(E('details',{'class':'hv-channel-more','data-channel-more':'1'},[
    E('summary',{},bi('More VPN servers','Ещё VPN-серверы')+' ('+split.other.length+')'),other]),'channels-other');
  return {get:function(p){return ids.indexOf(p.id)>=0?cards:other;},finish:function(){if(split.other.length)cards.appendChild(details);}};
}
function roleDescription(p,status,inventory){
  var ids=rolePairIds(status,inventory,(typeof routerWall==='function'?routerWall():Date.now()/1000)),role=p&&p.id===ids[0]?bi('Primary channel','Основной канал'):p&&p.id===ids[1]?bi('Reserve channel','Резервный канал'):bi('Other VPN','Другой VPN');
  return role;
}
function endpointText(p,now){
  var e=p&&p.server_endpoint;
  if(!e||typeof e!=='object'||e.source!=='live-kernel-peer'||p.vendor_state!=='SETTLED'||!observationFresh(p,now)||typeof p.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(p.interface)||e.profile!==p.id||e.interface!==p.interface||!Number.isFinite(e.time)||now-e.time< -5||now-e.time>observationValidFor(p)||typeof e.host!=='string'||!/^[A-Fa-f0-9.:-]{1,100}$/.test(e.host)||!Number.isInteger(e.port)||e.port<1||e.port>65535||['tcp','udp'].indexOf(e.transport)<0)return bi('Server address: not observed','Адрес сервера: не получен');
  var host=e.host.indexOf(':')>=0?'['+e.host+']':e.host;
  return bi('Server: ','Сервер: ')+host+':'+e.port+' · '+e.transport.toUpperCase();
}
function limitTableRows(table,limit,key){
  var expanded=HV_DISCLOSURES[key]===true,button=E('button',{'type':'button','class':'cbi-button hv-more-rows','aria-expanded':expanded?'true':'false','click':function(){expanded=!expanded;HV_DISCLOSURES[key]=expanded;apply();}});
  function apply(){
    if(typeof table.querySelectorAll!=='function')return;
    var rows=Array.from(table.querySelectorAll('tr')).filter(function(row){return row.querySelector('td')&&!row.hidden;});
    rows.forEach(function(row,i){if(!expanded&&i>=limit)row.setAttribute('data-over-limit','true');else row.removeAttribute('data-over-limit');});
    table.setAttribute('data-limited-table','1');button.setAttribute('aria-expanded',expanded?'true':'false');
    button.textContent=(expanded?'▾ ':'▸ ')+(expanded?bi('Show fewer','Свернуть'):bi('More entries','Ещё записи'))+' ('+Math.max(0,rows.length-limit)+')';button.hidden=rows.length<=limit;
  }
  apply();
  if(typeof MutationObserver!=='undefined')new MutationObserver(apply).observe(table,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden']});
  return E('div',{'class':'hv-limited-table'},[table,button]);
}
function currentCheckServerCell(p,now){
  return E('td',{},[E('strong',{},serverTitle(p)),E('br'),E('small',{'class':'hv-server-address'},endpointText(p,now))]);
}
function renderCompactCascade(status,inventory){
  var now=(typeof routerWall==='function'?routerWall():Date.now()/1000),split=splitRoleRows(status.profiles||[],status,inventory||{},now),recommendation=reliabilityRecommendation(status,inventory||{},now);
  function row(p){var use=channelDisplayUse(p,status,inventory||{});return E('div',{'class':'hv-cascade-item','data-profile':p.id},[
    E('span',{'class':'hv-check-lamp hv-check-'+use.kind,'aria-hidden':'true'}),
    E('div',{},[E('strong',{},roleDescription(p,status,inventory||{})),E('p',{},serverTitle(p)),E('small',{},endpointText(p,now)),E('p',{},use.label)])]);}
  var other=rememberDisclosure(E('details',{'class':'hv-channel-more','data-cascade-more':'1'},[E('summary',{},bi('Other VPN profiles','Другие VPN-профили')+' ('+split.other.length+')'),E('div',{'class':'hv-cascade-grid'},split.other.map(row))]),'cascade-other');
  return E('section',{'class':'hv-chart-card hv-cascade'},[
    E('h2',{},bi('Which VPN carries your traffic and which one is next','Какой VPN пропускает ваш трафик и какой следующий')),
    E('p',{},bi('The saved primary/reserve pair is shown in fixed role order. The selected route and health are separate; the recommendation does not change your settings.','Сохранённая пара показана в постоянном порядке: основной, затем резервный. Выбранный маршрут и состояние связи — разные сведения; рекомендация не меняет ваши настройки.')),
    E('div',{'class':'hv-cascade-grid'},split.pair.map(row)),
    recommendation?E('p',{'class':'hv-reliability-note','data-reliability':'1'},[E('strong',{},bi('Recommendation: ','Рекомендация: ')),recommendation.text+' ',typeof errorCodeLink==='function'?errorCodeLink(recommendation.code):recommendation.code]):null,
    split.other.length?other:null].filter(Boolean));
}

/* Channel reliability from the router's own check history. Display only: it changes no setting, priority or route. */
var RELIABILITY_WINDOW=300,RELIABILITY_MIN=6,RELIABILITY_LIMIT=20,ALTERNATIVE_MIN_CHECKS=20,ALTERNATIVE_MIN_SUCCESS=95;
function channelReliability(profile,status,now){
  if(!profile||!status||!Array.isArray(status.samples)||!Number.isFinite(now))return null;
  var rows=status.samples.filter(function(s){return s&&s.id===profile.id&&Number.isFinite(s.time)&&now-s.time>=-5&&now-s.time<=RELIABILITY_WINDOW&&['CHECK-001','CHECK-LIMIT','PROFILE-INACTIVE'].indexOf(s.code)<0;});
  if(rows.length<RELIABILITY_MIN)return null;
  var bad=rows.filter(function(s){return !(s.code==null&&s.dns_ok===true&&s.https_success>=2);}).length,loss=100*bad/rows.length;
  return {n:rows.length,bad:bad,loss:loss,minutes:Math.round(RELIABILITY_WINDOW/60),unreliable:loss>=RELIABILITY_LIMIT};
}
function reliabilityText(r){
  return bi('check loss ','потери проверок ')+Math.round(r.loss)+'% ('+r.bad+' '+bi('of ','из ')+r.n+' '+bi('in ','за ')+r.minutes+' '+bi('min','мин')+')';
}
function bestMeasuredAlternative(status,excludedIds){
  var rank=typeof dvRank==='function'?dvRank(status):{},best=null;
  ((status||{}).profiles||[]).forEach(function(p){
    var r=rank[p.id];if(!r||excludedIds.indexOf(p.id)>=0||r.n<ALTERNATIVE_MIN_CHECKS)return;
    var percent=100*r.good/r.n,rtt=r.good?r.sum/r.good:Infinity;
    if(percent<ALTERNATIVE_MIN_SUCCESS)return;
    if(!best||percent>best.percent||percent===best.percent&&rtt<best.rtt)best={p:p,percent:percent,n:r.n,rtt:rtt};
  });
  return best;
}
// The recommendation is computed from the loss statistics of the saved pair and of the measured profiles.
function reliabilityRecommendation(status,inventory,now){
  var ids=rolePairIds(status,inventory,now),rows=(status||{}).profiles||[];
  var pair=ids.map(function(id){return rows.filter(function(p){return p.id===id;})[0]||null;});
  var rel=pair.map(function(p){return p?channelReliability(p,status,now):null;}),bad=rel.map(function(r){return !!(r&&r.unreliable);});
  if(!bad[0]&&!bad[1])return null;
  var best=bestMeasuredAlternative(status,ids),other=bad[0]?rel[1]:rel[0];
  var tail=best?bi(' Best spare by statistics: ',' Лучший запасной по статистике: ')+serverTitle(best.p)+' ('+bi('success ','успех ')+Math.round(best.percent)+'% '+bi('over ','по ')+best.n+' '+bi('checks','проверкам')+').'
    :bi(' No other server has enough measurements yet: run a speed test in Tests.',' У других серверов пока мало измерений: запустите тест скорости в разделе «Тесты».');
  var text;
  if(bad[0]&&bad[1])text=bi('Both channels lose many checks (primary '+Math.round(rel[0].loss)+'%, reserve '+Math.round(rel[1].loss)+'%). Check the internet uplink first; then replace the worse server.','Оба канала теряют много проверок (основной '+Math.round(rel[0].loss)+'%, резерв '+Math.round(rel[1].loss)+'%). Сначала проверьте интернет-подключение роутера, затем замените худший сервер.');
  else if(bad[0])text=bi('The primary has a reliability problem ('+reliabilityText(rel[0])+'). '+(other?'Keep traffic on the reserve (loss '+Math.round(other.loss)+'%) and replace the primary server.':'Replace the primary server; the reserve has too few measurements to compare.'),'У основного канала проблема с надёжностью ('+reliabilityText(rel[0])+'). '+(other?'Держите трафик на резерве (потери '+Math.round(other.loss)+'%) и замените сервер основного.':'Замените сервер основного; у резерва мало измерений для сравнения.'));
  else text=bi('The reserve has a reliability problem ('+reliabilityText(rel[1])+'). '+(other?'Keep traffic on the primary (loss '+Math.round(other.loss)+'%) and replace the reserve server.':'Replace the reserve server; the primary has too few measurements to compare.'),'У резервного канала проблема с надёжностью ('+reliabilityText(rel[1])+'). '+(other?'Держите трафик на основном (потери '+Math.round(other.loss)+'%) и замените сервер резерва.':'Замените сервер резерва; у основного мало измерений для сравнения.'));
  return {code:'CHANNEL-UNRELIABLE',text:text+tail};
}
