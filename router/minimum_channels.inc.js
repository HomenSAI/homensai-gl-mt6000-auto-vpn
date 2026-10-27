/* Concise channel inventory. Rendering and filtering never connect a profile. */
var minimumProfileSearch='';
function minimumProfileName(profile,inventory){
  if(!profile)return bi('Profile not selected','Профиль не выбран');
  var saved=(Array.isArray((inventory||{}).servers)?inventory.servers:[]).filter(function(row){return row&&row.profile===profile.id;})[0];
  var configured=(Array.isArray((inventory||{}).profiles)?inventory.profiles:[]).filter(function(row){return row&&row.id===profile.id;})[0];
  return saved&&saved.name||profile.name||profile.router_name||configured&&configured.name||profile.id||bi('Profile name unavailable','Название профиля недоступно');
}
function renderMinimumChannels(status,inventory,routerUrl){
  status=status||{};inventory=inventory||{};
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var model=simpleHomeModel(status,inventory,now),selectedIds=[model.source&&model.source.id,model.target&&model.target.id];
  function details(profile){
    var health=simpleHomeHealth(profile,now,model.dataUnavailable),known=!!profile;
    var measured=health.state==='healthy'&&known&&Number.isFinite(profile.rtt_ms)&&profile.rtt_ms>=0;
    var stamp=known&&Number.isFinite(profile.time)&&manualFresh(profile.time,now,90)?new Date(profile.time*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}):(typeof channelCheckText==='function'?channelCheckText(profile,now):bi('No fresh measurement','Нет свежего измерения'));
    return E('details',{'class':'hv-minimum-details'},[
      E('summary',{},bi('Details','Подробнее')),
      E('dl',{'class':'hv-minimum-profile-details'},[
        E('dt',{},bi('Server','Сервер')),E('dd',{},endpointText(profile,now)),
        E('dt',{},bi('Protocol','Протокол')),E('dd',{},known&&['wireguard','openvpn'].indexOf(profile.protocol)>=0?protocolLabel(profile):bi('Not reported by the router','Роутер не сообщил')),
        E('dt',{},bi('Country','Страна')),E('dd',{},known&&countryName(profile)||bi('Not reported by the router','Роутер не сообщил')),
        E('dt',{},bi('Delay','Задержка')),E('dd',{},measured?profile.rtt_ms.toFixed(0)+' '+bi('ms','мс'):(typeof channelCheckText==='function'?channelCheckText(profile,now):bi('No fresh measurement','Нет свежего измерения'))),
        E('dt',{},bi('Checked · Europe/Berlin','Проверено · Europe/Berlin')),E('dd',{},stamp)
      ])
    ]);
  }
  function card(profile,role){
    var health=role==='source'?model.sourceHealth:model.targetHealth;
    var used=model.selectedRole===role,selection=used?bi('In use','Используется'):model.selectedRole?bi('Not in use','Не используется'):model.moving?bi('Selection is changing','Выбор меняется'):bi('The router has not reported which VPN is in use yet','Роутер ещё не сообщил, какой VPN работает');
    return E('article',{'class':'hv-minimum-channel hv-minimum-health-'+health.state+(used?' hv-minimum-channel-selected':''),'data-minimum-channel':role},[
      E('div',{'class':'hv-minimum-channel-heading'},[E('span',{'class':'hv-minimum-role'},role==='source'?bi('Primary','Основной'):bi('Reserve','Резервный')),E('span',{'class':'hv-minimum-health'},health.label)]),
      E('h3',{},minimumProfileName(profile,inventory)),E('p',{'class':'hv-minimum-selection'},selection),details(profile)
    ]);
  }
  var profiles=[],seen=Object.create(null),measured=Array.isArray(status.profiles)?status.profiles:[];
  (Array.isArray(inventory.profiles)?inventory.profiles:[]).concat(measured).slice(0,800).forEach(function(profile){
    if(!profile||typeof profile.id!=='string'||seen[profile.id]||selectedIds.indexOf(profile.id)>=0)return;
    seen[profile.id]=true;profiles.push(measured.filter(function(row){return row&&row.id===profile.id;})[0]||profile);
  });
  var list=E('div',{'class':'hv-minimum-other-profiles'}),entries=[];
  profiles.forEach(function(profile){
    var health=simpleHomeHealth(profile,now,model.dataUnavailable);
    var name=minimumProfileName(profile,inventory);
    var entry=E('div',{'class':'hv-minimum-profile-row'},[E('strong',{},name),E('span',{},health.label)]);
    entries.push({node:entry,text:(String(name)+' '+health.label).toLocaleLowerCase(locale)});list.appendChild(entry);
  });
  var noMatches=E('p',{'class':'hv-minimum-empty'},bi('No matching profiles','Подходящих профилей нет'));
  var search=E('input',{'type':'search','class':'hv-search hv-minimum-search','aria-label':bi('Search other profiles','Поиск других профилей'),'placeholder':bi('Profile name','Название профиля'),'input':function(){minimumProfileSearch=search.value;filter();}});
  search.value=minimumProfileSearch;
  function filter(){var query=minimumProfileSearch.trim().toLocaleLowerCase(locale),matches=0;entries.forEach(function(entry){entry.node.hidden=!!query&&entry.text.indexOf(query)<0;if(!entry.node.hidden)matches++;});noMatches.hidden=matches>0;}
  var others=E('details',{'class':'hv-minimum-details','data-minimum-details':'other-profiles'},[
    E('summary',{},bi('Other profiles','Другие профили')),
    profiles.length?search:null,profiles.length?list:E('p',{'class':'hv-minimum-empty'},bi('No other profiles found.','Другие профили не найдены.')),profiles.length?noMatches:null
  ].filter(Boolean));filter();
  var actions=[E('a',{'class':'cbi-button hv-minimum-action','href':'#settings'},bi('Change pair','Изменить пару'))];
  if(typeof routerUrl==='string'&&routerUrl)actions.push(E('a',{'class':'cbi-button hv-minimum-action','href':routerUrl,'target':'_blank','rel':'noopener noreferrer','aria-label':bi('Router profiles (opens a new tab)','Профили роутера (новая вкладка)')},bi('Router profiles ↗','Профили роутера ↗')));
  return E('section',{'class':'hv-minimum-section hv-minimum-channels'},[
    E('div',{'class':'hv-minimum-channel-grid'},[card(model.source,'source'),card(model.target,'target')]),
    E('div',{'class':'hv-minimum-actions'},actions),others
  ]);
}
