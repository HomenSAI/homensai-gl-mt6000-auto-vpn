/* Explains the Channels page: where the list comes from, why it has N entries, and when the number changes. */
function serverCounts(status,inventory,rows,now){
  var onRouter=Array.isArray((inventory||{}).profiles)?inventory.profiles.length:rows.length;
  var shown=rows.length;
  var connected=rows.filter(function(p){return p.interface;});
  var working=connected.filter(function(p){return profileHealth(p,now).state==='healthy';}).length;
  var stale=connected.filter(function(p){return profileHealth(p,now).state==='unknown';}).length;
  return {onRouter:Math.max(onRouter,shown),shown:shown,connected:connected.length,working:working,stale:stale,hidden:Math.max(0,onRouter-shown)};
}
function renderServerSummary(status,inventory,rows){
  var c=serverCounts(status,inventory,rows,(typeof statusNow==='function'?statusNow(status):Date.now()/1000));
  function tile(value,label,hint){return E('div',{'class':'hv-count'},[E('strong',{},String(value)),E('span',{},label),hint?E('small',{},hint):null].filter(Boolean));}
  var tiles=[
    tile(c.onRouter,bi('VPN profiles on the router','VPN-профилей на роутере'),bi('Added in GL.iNet → VPN','Добавлены в GL.iNet → VPN')),
    tile(c.connected,bi('Connected now','Подключено сейчас'),bi('Only these are checked','Проверяются только они')),
    tile(c.working+' / '+c.connected,bi('Work (internet passes)','Работают (интернет проходит)'),bi('From the latest check','По последней проверке'))
  ];
  var note=bi('This list is read from your router. A VPN profile you add in GL.iNet (VPN → VPN Dashboard) appears here by itself within about a minute, and a removed one disappears, so the numbers can change at any time. Profiles that are not connected are listed so you can see them; this program never connects them. To add, remove or connect servers use the router’s VPN page (button below).','Список берётся с вашего роутера. VPN-профиль, добавленный в GL.iNet (VPN → VPN Dashboard), появляется здесь сам примерно за минуту, а удалённый исчезает, поэтому числа могут меняться в любой момент. Неподключённые профили показаны, чтобы вы их видели; эта программа их никогда не подключает. Чтобы добавить, убрать или подключить серверы, используйте страницу VPN на роутере (кнопка ниже).');
  var hidden=c.hidden>0?E('p',{'class':'hv-count-note'},c.hidden+' '+bi('profile(s) are hidden because you chose which servers to monitor (Settings → All application settings → 3 · Existing VPNs).','профилей скрыто, потому что вы выбрали, какие серверы наблюдать («Настройки → Все настройки приложения → 3 · Существующие VPN»).')):null;
  return E('section',{'class':'hv-chart-card hv-server-summary'},[E('h3',{},bi('Your VPN servers','Ваши VPN-серверы')),E('div',{'class':'hv-counts'},tiles),E('p',{},note),hidden].filter(Boolean));
}
