/* Best server inside a channel (2.1.0, server_pick.lua/.py). An optional module: the Channels page loads it when the
   owner opens "Servers of the channels". Per channel: its current GL server, the servers of its GL list with the ping
   the router measured, the best one marked, the last change; and the owner switch (off by default). Read-only view of
   status.server_pick; the only write is setup_response {metric, server_pick}. */
function serverPickPanel(ctx){
  var E=ctx.E,bi=ctx.bi,status=ctx.status||{},settings=(ctx.inventory||{}).settings||{},pick=status.server_pick,busy=false;
  var now=Number.isFinite(status.server_time)?status.server_time:Number.isFinite(status.time)?status.time:Date.now()/1000;
  function name(c){return c&&(c.location?c.location+' ('+c.profile+')':c.profile)||'—';}
  function age(t){var s=Math.max(0,Math.round(now-t));return s<90?bi(s+' s ago',s+' с назад'):s<5400?bi(Math.round(s/60)+' min ago',Math.round(s/60)+' мин назад'):bi(Math.round(s/3600)+' h ago',Math.round(s/3600)+' ч назад');}
  function channel(t){
    var row=(Array.isArray(status.profiles)?status.profiles:[]).filter(function(p){return p&&p.interface&&p.interface===t.interface;})[0];
    return (row&&(row.name||row.router_name))||((t.protocol==='wireguard'?'WireGuard':'OpenVPN')+(t.interface?' · '+t.interface:''));
  }
  var box=E('input',{'type':'checkbox','class':'hv-server-pick-switch'});box.checked=settings.server_pick===true;
  box.addEventListener('change',function(){
    if(busy)return;busy=true;var want=box.checked;box.setAttribute('disabled','');
    ctx.rpc.declare({object:'homensai-vpn',reject:true,method:'setup_response',params:['metric','server_pick'],expect:{}})(settings.response_metric||'icmp-1.1.1.1',want).then(function(r){
      if(r&&r.saved){settings.server_pick=want;ctx.ui.addNotification(null,E('p',{},bi('Saved. The router uses it from its next server check.','Сохранено. Роутер применит со следующей проверки серверов.')));}
      else{box.checked=!want;ctx.ui.addNotification(null,E('p',{},(r&&r.code)||'SETUP-SAVE-FAILED'));}
    }).catch(function(){box.checked=!want;ctx.ui.addNotification(null,E('p',{},'SETUP-SAVE-UNCONFIRMED'));}).finally(function(){busy=false;box.removeAttribute('disabled');});
  });
  var parts=[E('label',{'class':'hv-server-pick-toggle'},[box,' ',E('strong',{},bi('Pick the best server','Подбирать лучший сервер'))]),
    E('p',{'class':'hv-step-note'},bi('When a channel fails and the traffic is already on the other one, the router measures the servers of the failed channel and puts the fastest working one into it, the way GL itself changes servers. The channel that carries the traffic is never touched; at most 4 changes per hour per channel; a working server is replaced only by one at least 20% faster. Off by default until it is checked on the router.',
      'Когда канал падает и трафик уже на другом канале, роутер меряет серверы упавшего канала и ставит в него самый быстрый рабочий — так же, как сервер меняет сама GL. Канал, который везёт трафик, не трогается никогда; не больше 4 смен в час на канал; рабочий сервер меняется только на сервер быстрее хотя бы на 20%. По умолчанию выключено до проверки на роутере.'))];
  if(!pick||!Array.isArray(pick.tunnels)){parts.push(E('p',{'role':'status'},bi('No server data from the router yet.','Данных о серверах от роутера пока нет.')));return E('div',{'class':'hv-server-pick'},parts);}
  if(Number.isFinite(pick.time))parts.push(E('p',{'class':'hv-step-note'},[bi('Servers read ','Серверы прочитаны '),age(pick.time),pick.enabled?'':bi('; ping is measured only while the switch is on.','; пинг меряется, только когда выключатель включён.')]));
  pick.tunnels.forEach(function(t){
    var current=(t.candidates||[]).filter(function(c){return c.profile===t.current;})[0];
    var list=E('ul',{'class':'hv-server-pick-list'},(t.candidates||[]).map(function(c){
      var ping=c.alive===true&&Number.isFinite(c.latency_ms)?c.latency_ms+' '+bi('ms','мс'):c.alive===false?bi('no answer','нет ответа'):bi('not measured','не измерен');
      return E('li',{'data-best':c.profile===t.best?'true':'false','data-current':c.profile===t.current?'true':'false'},[
        name(c),' — ',ping,c.profile===t.best?E('strong',{},bi(' · best',' · лучший')):'',c.profile===t.current?E('em',{},bi(' · current',' · текущий')):'']);
    }));
    var change=t.last_change,changed=change&&Number.isFinite(change.time)?E('p',{'class':'hv-step-note'},[bi('Last change: ','Последняя смена: '),
      (change.from_location||change.from||'?')+' → '+(change.to_location||change.to||'?')+', '+(Number.isFinite(change.from_ms)?change.from_ms:'?')+' → '+(Number.isFinite(change.to_ms)?change.to_ms:'?')+' '+bi('ms','мс')+', ',age(change.time)]):null;
    parts.push(E('section',{'class':'hv-server-pick-channel','data-interface':t.interface||''},[
      E('h4',{},channel(t)),E('p',{},[bi('Current server: ','Текущий сервер: '),E('strong',{},current?name(current):(t.current||'—'))]),list,changed,
      t.code?E('p',{'class':'hv-step-note'},[ctx.errorCodeLink?ctx.errorCodeLink(t.code):t.code]):null].filter(Boolean)));
  });
  return E('div',{'class':'hv-server-pick'},parts);
}
