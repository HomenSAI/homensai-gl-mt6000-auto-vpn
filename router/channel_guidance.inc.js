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
function splitRoleRows(rows,status,inventory,now){
  var ids=rolePairIds(status,inventory,now),ordered=roleOrderedRows(rows,status,inventory,now),pair=ordered.filter(function(p){return ids.indexOf(p.id)>=0;});
  if(!pair.length)pair=ordered.slice(0,2);
  return {pair:pair,other:ordered.filter(function(p){return !pair.some(function(q){return p.id===q.id;});})};
}
function channelCardHosts(rows,status,inventory,cards){
  var split=splitRoleRows(rows,status,inventory,Date.now()/1000),ids=split.pair.map(function(p){return p.id;}),other=E('div',{'class':'hv-server-grid'});
  var details=rememberDisclosure(E('details',{'class':'hv-channel-more','data-channel-more':'1'},[
    E('summary',{},bi('More VPN servers','Ещё VPN-серверы')+' ('+split.other.length+')'),other]),'channels-other');
  return {get:function(p){return ids.indexOf(p.id)>=0?cards:other;},finish:function(){if(split.other.length)cards.appendChild(details);}};
}
function roleDescription(p,status,inventory){
  var ids=rolePairIds(status,inventory,Date.now()/1000),role=p&&p.id===ids[0]?bi('Primary channel','Основной канал'):p&&p.id===ids[1]?bi('Reserve channel','Резервный канал'):bi('Other VPN','Другой VPN');
  return role;
}
function endpointText(p,now){
  var e=p&&p.server_endpoint;
  if(!e||typeof e!=='object'||e.source!=='live-kernel-peer'||p.vendor_state!=='SETTLED'||!Number.isFinite(p.time)||now-p.time< -5||now-p.time>90||typeof p.interface!=='string'||!/^(wgclient|ovpnclient)[0-9]{1,4}$/.test(p.interface)||e.profile!==p.id||e.interface!==p.interface||!Number.isFinite(e.time)||now-e.time< -5||now-e.time>90||typeof e.host!=='string'||!/^[A-Fa-f0-9.:-]{1,100}$/.test(e.host)||!Number.isInteger(e.port)||e.port<1||e.port>65535||['tcp','udp'].indexOf(e.transport)<0)return bi('Server address: not observed','Адрес сервера: не получен');
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
  var now=Date.now()/1000,split=splitRoleRows(status.profiles||[],status,inventory||{},now);
  function row(p){var use=channelDisplayUse(p,status,inventory||{});return E('div',{'class':'hv-cascade-item','data-profile':p.id},[
    E('span',{'class':'hv-check-lamp hv-check-'+use.kind,'aria-hidden':'true'}),
    E('div',{},[E('strong',{},roleDescription(p,status,inventory||{})),E('p',{},serverTitle(p)),E('small',{},endpointText(p,now)),E('p',{},use.label)])]);}
  var other=rememberDisclosure(E('details',{'class':'hv-channel-more','data-cascade-more':'1'},[E('summary',{},bi('Other VPN profiles','Другие VPN-профили')+' ('+split.other.length+')'),E('div',{'class':'hv-cascade-grid'},split.other.map(row))]),'cascade-other');
  return E('section',{'class':'hv-chart-card hv-cascade'},[
    E('h2',{},bi('Which VPN carries your traffic and which one is next','Какой VPN пропускает ваш трафик и какой следующий')),
    E('p',{},bi('The saved primary/reserve pair is shown in fixed role order. The selected route and health are separate; the recommendation does not change your settings.','Сохранённая пара показана в постоянном порядке: основной, затем резервный. Выбранный маршрут и состояние связи — разные сведения; рекомендация не меняет ваши настройки.')),
    E('div',{'class':'hv-cascade-grid'},split.pair.map(row)),split.other.length?other:null].filter(Boolean));
}
