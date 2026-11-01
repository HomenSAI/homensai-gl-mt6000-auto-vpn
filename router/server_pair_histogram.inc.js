// Statistics page, "Server uptime and failures" (owner 01.11.2026): only the servers of the configured Auto pair
// (plan source and target) and the servers that really have hours or failures in the selected period are shown;
// the rest stay behind a small "Show all (N)" toggle. The histogram itself is ui_histogram.js (unchanged).
var SERVER_PAIR_SHOW_ALL=false;
function serverPairPeriodKeep(day,period,today,weekStart){return period==='day'?day===today:period==='week'?day>=weekStart&&day<=today:day.slice(0,7)===today.slice(0,7);}
function serverPairActivity(accounting,period,settings,status,now){
  var activity=(accounting||{}).activity||{},native=(status||{}).native_failover||{},pair={};
  [settings&&settings.plan_source,settings&&settings.plan_target,native.source,native.target].forEach(function(id){if(id)pair[id]=true;});
  function key(date){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).format(date);}
  var today=key(now||new Date()),p=today.split('-').map(Number),weekStart=new Date(Date.UTC(p[0],p[1]-1,p[2]-6)).toISOString().slice(0,10);
  var shown={},hidden=0;
  Object.keys(activity).forEach(function(id){
    var days=(activity[id]||{}).days||{},used=pair[id];
    Object.keys(days).forEach(function(day){var d=days[day]||{};if(serverPairPeriodKeep(day,period,today,weekStart)&&((d.up||0)>0||(d.down||0)>0||(d.failures||0)>0))used=true;});
    if(used)shown[id]=activity[id];else hidden++;
  });
  return {shown:shown,hidden:hidden};
}
function serverPairHistogram(accounting,onPeriod,period,settings,status,redraw){
  var picked=serverPairActivity(accounting,period,settings,status),all=SERVER_PAIR_SHOW_ALL;
  var section=histogram(all?accounting:Object.assign({},accounting,{activity:picked.shown}),onPeriod,period);
  section.setAttribute('data-stats-reset','quality');  // accounting.activity: the 'quality' reset scope
  if(picked.hidden)section.appendChild(E('p',{'class':'hv-server-filter'},[
    all?bi('All servers are shown. ','Показаны все серверы. '):bi('Shown: the Auto pair and servers with hours or failures in this period. Hidden: ','Показаны: пара Auto и серверы с часами работы или сбоями за период. Скрыто: ')+picked.hidden+'. ',
    E('button',{'type':'button','class':'cbi-button','data-server-filter':all?'pair':'all','click':function(){SERVER_PAIR_SHOW_ALL=!all;if(redraw)redraw();}},
      all?bi('Only the pair and active servers','Только пара и активные'):bi('Show all (','Показать все (')+(Object.keys(picked.shown).length+picked.hidden)+')')]));
  return section;
}
