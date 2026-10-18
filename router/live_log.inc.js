/* Live log: the same lines as before, now alive: a pulsing LIVE dot, a seconds counter, a bar that fills until the next check
   and a small blinking lamp on every line (green = works, yellow = checking, red = failure, grey = not connected). */
var liveLogTimer=null;
function liveLampKind(profile,now){var s=profileHealth(profile,now).state;return s==='healthy'?'green':s==='checking'?'yellow':s==='failed'?'red':'grey';}
function renderLiveLog(status,rows,ns,inventory,stateNames){stateNames=stateNames||{};
  var now=Date.now()/1000,interval=Number(((inventory||{}).settings||{}).interval)||30;
  var fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  var light=autoLightModel(status,inventory||{},now);
  function lamp(kind,title){return E('span',{'class':'hv-live-lamp hv-live-lamp-'+kind,'role':'img','aria-label':title,'title':title});}
  function time(t,fallback){return E('span',{'class':'hv-log-time'},t?new Date(t*1000).toLocaleTimeString():fallback);}
  var counter=E('span',{'class':'hv-live-age'}),bar=E('span',{'class':'hv-live-bar-fill'}),next=E('span',{'class':'hv-live-next'});
  var head=E('div',{'class':'hv-live-head'},[E('span',{'class':'hv-live-dot hv-live-dot-'+(fresh?'on':'off'),'aria-hidden':'true'}),E('strong',{},fresh?bi('LIVE','В ЭФИРЕ'):bi('NO DATA','НЕТ ДАННЫХ')),counter,E('span',{'class':'hv-live-bar','aria-hidden':'true'},bar),next]);
  function tick(){
    var t=Date.now()/1000,age=Number.isFinite(status.time)?Math.max(0,t-status.time):null;
    counter.textContent=age==null?'':bi('updated '+Math.round(age)+' s ago','обновлено '+Math.round(age)+' с назад');
    var share=age==null?0:Math.min(1,age/interval);bar.style.width=Math.round(share*100)+'%';
    next.textContent=age==null?'':(age>=interval?bi('check is due…','проверка вот-вот…'):bi('next check in about '+Math.max(1,Math.round(interval-age))+' s','следующая проверка через ~'+Math.max(1,Math.round(interval-age))+' с'));
  }
  tick();if(liveLogTimer)clearInterval(liveLogTimer);liveLogTimer=setInterval(function(){if(!document.body.contains(head)){clearInterval(liveLogTimer);liveLogTimer=null;return;}tick();},1000);
  var monitorKind=fresh?'green':status.rpc_error?'red':'yellow';
  var lines=[
    E('div',{},[time(status.time,'—'),lamp(monitorKind,fresh?bi('Monitoring works','Мониторинг работает'):bi('No fresh data','Нет свежих данных')),E('strong',{},'  HomenS.AI monitor: '),badge(status.error)]),
    E('div',{},[time(ns.time,'—'),lamp(light.lamp==='orange'?'yellow':(light.lamp||'grey'),light.title),E('strong',{},'  Auto VPN: '),stateNames[ns.state]||ns.state||'UNKNOWN'])
  ];
  var terminal=E('pre',{'class':'hv-live-terminal'},lines);
  rows.slice(0,20).forEach(function(p){
    terminal.appendChild(E('div',{'class':p.code?'error':'notice'},[time(p.time,'—:—:—'),lamp(liveLampKind(p,now),profileHealth(p,now).label),E('strong',{},'  '+p.protocol+' / '+serverTitle(p)+': '),healthBadge(p)]));
  });
  return E('div',{'class':'hv-live'},[head,terminal]);
}
