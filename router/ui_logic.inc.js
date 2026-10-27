var UI_STATUS_CLOCKS=new WeakMap();
var UI_CLOCK_SKEW=0;
// Router time as the browser sees it; a PC clock a few seconds off must not turn fresh data into "waiting".
function routerWall(){return Date.now()/1000+UI_CLOCK_SKEW;}
function statusNow(status){
  var wall=Date.now()/1000;
  if(!status||typeof status!=='object'||!Number.isFinite(status.server_time)||status.server_time<=0||status.server_time>253370764799)return wall;
  var tick=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now()/1000:wall;
  var saved=UI_STATUS_CLOCKS.get(status);
  if(!saved){saved={server:status.server_time,tick:tick};UI_STATUS_CLOCKS.set(status,saved);}
  var value=saved.server+Math.max(0,tick-saved.tick);UI_CLOCK_SKEW=value-wall;return value;
}
// The latest router check of a channel in words. A failed check is a result too: it shows what failed and when.
function channelCheckText(profile,now){
  if(!profile)return bi('No VPN selected','VPN не выбран');
  if(!Number.isFinite(profile.time))return bi('The first router check is being collected','Первая проверка роутера выполняется');
  var when=new Date(profile.time*1000).toLocaleTimeString(typeof locale!=='undefined'&&locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'}),age=Math.max(0,Math.round(now-profile.time));
  var old=age>90?' · '+bi(age+' s ago',age+' с назад'):'',https=Number.isInteger(profile.https_success)?profile.https_success:0;
  if(!profile.interface||profile.code==='VPN-001')return bi('Tunnel is not connected','Туннель не подключён')+' · '+when+old;
  if(profile.code==null&&profile.dns_ok===true&&https>=2)return (Number.isFinite(profile.rtt_ms)&&profile.rtt_ms>=0?profile.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS'):bi('Check passed: HTTPS ','Проверка пройдена: HTTPS ')+https+'/3')+' · '+when+old;
  return bi('Check failed: ','Проверка не прошла: ')+'HTTPS '+https+'/3'+(profile.dns_ok===false?', '+bi('DNS failed','DNS не прошёл'):'')+' · '+when+old;
}
var UI_DATA_CAUSE=null;
function dataCause(status,now){
  if(!status||status.rpc_error)return {code:'STATUS-REQUEST-FAILED',text:bi('the page got no answer from the router program','страница не получила ответ от программы на роутере')};
  if(!Number.isFinite(status.time)||now-status.time>90)return {code:'MONITOR-DATA-STALE',text:bi('the router has not sent fresh data'+(Number.isFinite(status.time)?' for '+Math.round(now-status.time)+' s':''),'роутер не присылает свежие данные'+(Number.isFinite(status.time)?' уже '+Math.round(now-status.time)+' с':''))};
  return {code:'VENDOR-OBSERVATION-PENDING',text:bi('the monitor has not finished observing this channel yet (up to a minute after a start or change)','мониторинг ещё не закончил наблюдение этого канала (до минуты после запуска или изменения)')};
}
function dataCauseText(prefix){var c=UI_DATA_CAUSE||dataCause(null,0);return (prefix||bi('Not available: ','Нет данных: '))+c.text+' ('+c.code+')';}
function profileHealth(profile,now){
  if(!profile.interface||profile.administrative_state==='disabled')return {state:'inactive',label:bi('Inactive','Неактивен')};
  if(!Number.isFinite(profile.time)||now-profile.time< -5||now-profile.time>90)return {state:'unknown',label:bi('Check data unavailable','Нет данных проверки')};
  if(['CHECK-001','CHECK-LIMIT'].indexOf(profile.code)>=0)return {state:'checking',label:bi('Checking','Проверяется')};
  if(profile.code)return {state:'failed',label:bi('Failed','Сбой')};
  if(profile.dns_ok===true&&profile.https_success>=2)return {state:'healthy',label:bi('Healthy','Работает')};
  return {state:'checking',label:bi('Checking','Проверяется')};
}
function selectedProfile(status,now){
  var native=status.native_failover||{};
  if(status.rpc_error||!Number.isFinite(native.time)||now-native.time<0||now-native.time>30)return null;
  if(['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(native.state)>=0)return native.target||null;
  if(native.state==='OBSERVING'&&(native.certified===true||native.mode==='continuous-pair'&&native.readiness_verified===true))return native.source||null;
  return null;
}
function sortServerCards(rows,selected,now){
  var ranks={healthy:1,checking:2,unknown:3,inactive:4,failed:5};
  return rows.map(function(row,index){var state=profileHealth(row,now).state;return {row:row,index:index,rank:state==='healthy'&&row.id===selected?0:ranks[state]};}).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).map(function(entry){return entry.row;});
}
function healthBadge(profile){
  var health=profileHealth(profile,routerWall());
  // The code is a link to its row in the error table (when that helper exists on the page).
  var linked=profile.code&&typeof errorCodeLink==='function'&&typeof safeCode==='function'&&safeCode(profile.code);
  return E('strong',{'class':'hv-badge hv-health-'+health.state,'title':profile.code||health.label},linked?[health.label+' · ',errorCodeLink(profile.code)]:health.label+(profile.code?' · '+profile.code:''));
}
function compareTableValues(a,b,direction){
  var unknown=function(value){return value==null||/^(?:\s*|—|No data|Нет данных)$/.test(String(value).trim());};
  if(unknown(a)!==unknown(b))return unknown(a)?1:-1;
  var x=String(a==null?'':a).trim(),y=String(b==null?'':b).trim(),nx=Number(x.replace(/%$/,'')),ny=Number(y.replace(/%$/,''));
  var result=Number.isFinite(nx)&&Number.isFinite(ny)?nx-ny:x.localeCompare(y,locale,{numeric:true,sensitivity:'base'});
  return direction==='desc'?-result:result;
}
// Ranking trust: a handful of checks is not enough to name a leader.
function rankEnough(count){return count>=20?1:0;}
function rankConfidence(count){return count+' · '+(count>=100?bi('good','высокая'):count>=20?bi('fair','средняя'):bi('too few to rank','мало для рейтинга'));}
