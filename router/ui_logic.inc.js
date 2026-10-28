// Monitor cadence is backend-derived; controller heartbeats, kernel proof and website results keep their own TTLs.
function observationValidFor(row){var n=row&&row.observation_valid_for;return Number.isFinite(n)&&n>=30&&n<=900?n:90;}
function observationFresh(row,now){return !!row&&Number.isFinite(row.time)&&Number.isFinite(now)&&now-row.time>=-5&&now-row.time<=observationValidFor(row);}
// Order every status RPC by its browser dispatch sequence, never by the router's wall clock.
// NTP changes and router reboots may move server_time backwards; old page callbacks retain their original provenance.
var UI_STATUS_REQUEST_SEQUENCE=0,UI_STATUS_ORDER=new WeakMap();
function uiStatusRequest(call){
  var order=++UI_STATUS_REQUEST_SEQUENCE,promise=Promise.resolve().then(call).then(function(status){if(status&&typeof status==='object')UI_STATUS_ORDER.set(status,order);return status;});
  UI_STATUS_ORDER.set(promise,order);return promise;
}
function uiStatusOrder(value){return value&&typeof value==='object'?UI_STATUS_ORDER.get(value)||0:0;}
function uiStatusFailure(current,order){
  var failed=Object.assign({},current,{rpc_error:'RPC-UNAVAILABLE',server_time:typeof routerWall==='function'?routerWall():Date.now()/1000});
  UI_STATUS_ORDER.set(failed,order);return failed;
}
function uiNewestStatus(current,next){
  if(!current||current===next||!next)return next||current;
  var before=uiStatusOrder(current),after=uiStatusOrder(next);
  return before&&(!after||after<before)?current:next;
}
var UI_OPERATION_REFRESH=function(){},UI_STATUS_REFRESH=function(){};
function uiOperationRefresh(refresh){UI_OPERATION_REFRESH();if(refresh!==false)UI_STATUS_REFRESH();}
function uiStateSignature(status,inventory,now){
  var light=autoLightModel(status,inventory,now),manual=manualControlModel(status,now),op=autoCommandOperation(status,now),path=channelPathSelection(status,now);
  return JSON.stringify([light.key,light.title,light.code,op,manual.busy,manual.uncertain,manual.direction,manual.primary.allowed,manual.reserve.allowed,manual.hold,manual.resume.allowed,path.selected,path.code,path.moving,
    (status.profiles||[]).map(function(p){var ping=channelPingModel(p,status,now);return [p.id,profileHealth(p,now).state,ping.state,ping.code,ping.rtt_ms];})]);
}
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
  if(profile.code==null&&profile.dns_ok===true&&https>=2)return bi('Check passed: HTTPS ','Проверка пройдена: HTTPS ')+https+'/3'+' · '+when+old;
  return bi('Check failed: ','Проверка не прошла: ')+'HTTPS '+https+'/3'+(profile.dns_ok===false?', '+bi('DNS failed','DNS не прошёл'):'')+' · '+when+old;
}
function websiteMs(value){return (Math.floor(value*10+.5)/10).toFixed(1);}
var WEBSITE_METRIC='websites-https-mean-ms-v1',WEBSITE_TARGET_SET='google-cloudflare-wikipedia-v1';
var WEBSITE_URLS={google:'https://www.google.com/generate_204',cloudflare:'https://www.cloudflare.com/cdn-cgi/trace',wikipedia:'https://www.wikipedia.org/'};
function channelPingModel(p,status,now){
  var x=p&&p.website_response,n=x&&Number.isInteger(x.successes)&&x.successes>=0&&x.successes<=3?x.successes:0;
  function no(state,code){return {state:state,code:code,rtt_ms:null,successes:n,text:bi('No complete three-site check','Нет полной проверки трёх сайтов')+' · '+n+'/3'};}
  if(!status||status.rpc_error||status.error)return no('unavailable','STATUS-REQUEST-FAILED');
  if(!observationFresh(status,now))return no('stale','MONITOR-DATA-STALE');
  if(!p||!p.interface||p.administrative_state==='disabled')return no('inactive','WEBSITE-UNAVAILABLE');
  if(!x)return no('checking','WEBSITE-CHECK-PENDING');
  if(x.metric!==WEBSITE_METRIC||x.target_set!==WEBSITE_TARGET_SET||p.vendor_state!=='SETTLED'||typeof p.vendor_generation!=='string'||!/^[a-f0-9]{32}$/.test(p.vendor_generation)||x.generation!==p.vendor_generation||x.interface!==p.interface||typeof p.vendor_tunnel_id!=='string'||p.vendor_tunnel_id!==p.protocol+':'+p.interface||x.vendor_tunnel_id!==p.vendor_tunnel_id)return no('checking','WEBSITE-IDENTITY-CHANGED');
  if(x.state==='checking')return no('checking','WEBSITE-CHECK-PENDING');
  if(x.state==='inactive'||x.state==='unavailable')return no(x.state,'WEBSITE-UNAVAILABLE');
  if(!Number.isFinite(x.time)||!Number.isFinite(x.valid_for)||x.valid_for<=0||x.valid_for>45||now-x.time< -5||now-x.time>x.valid_for||x.state==='stale')return no('stale','WEBSITE-DATA-STALE');
  if(x.state!=='ok')return no(x.state==='partial'?'partial':'failed',x.state==='partial'?'WEBSITE-PARTIAL':'WEBSITE-RESPONSE-FAILED');
  var results=x.results,seen={},sum=0;
  if(x.successes!==3||x.attempted!==3||!Array.isArray(results)||results.length!==3)return no('unavailable','WEBSITE-UNAVAILABLE');
  if(!results.every(function(r){if(!r||!Object.prototype.hasOwnProperty.call(WEBSITE_URLS,r.id)||seen[r.id]||r.url!==WEBSITE_URLS[r.id]||r.state!=='ok'||r.code!=null||!Number.isFinite(r.elapsed_ms)||r.elapsed_ms<0||r.elapsed_ms>6000)return false;seen[r.id]=true;sum+=r.elapsed_ms;return true;})||!Number.isFinite(x.avg_ms)||x.avg_ms<0||x.avg_ms>6000||Math.abs(x.avg_ms-sum/3)>.051)return no('unavailable','WEBSITE-UNAVAILABLE');
  return {state:'ok',code:null,rtt_ms:x.avg_ms,successes:3,text:websiteMs(x.avg_ms)+' '+bi('ms','мс')};
}
function renderChannelPing(profile,status,now){
  var model=channelPingModel(profile,status,now),detail=bi('Mean response of Google, Cloudflare and Wikipedia, all 3 required. Fresh DNS+TCP+TLS+HTTP headers; not a full page.','Средний ответ Google, Cloudflare и Wikipedia, нужны все 3. Новый DNS+TCP+TLS+HTTP-заголовки, не полная страница.')+' '+model.text+(model.code?' · '+model.code:'');
  var labels={checking:bi('Checking','Проверяется'),stale:bi('Check is out of date','Проверка устарела'),partial:bi('Incomplete check','Неполная проверка'),failed:bi('Check failed','Проверка не прошла'),inactive:bi('Tunnel is off','Туннель отключён'),unavailable:bi('No current result','Нет актуального результата')};
  var shown=model.rtt_ms==null?'— · '+(labels[model.state]||labels.unavailable)+' · '+model.successes+'/3':model.text;
  return E('small',{'class':'hv-channel-ping','data-ping-state':model.state,'data-latency-metric':WEBSITE_METRIC,'data-latency-state':model.state,'data-coverage':model.successes+'/3','title':detail,'aria-label':detail},shown);
}
function websiteSamples(status,inventory){
  var h=status.website_response_history||{},out=[];
  latencyHistoryRows(status,inventory||{},routerWall()).forEach(function(r){[0,1].forEach(function(i){if(r[i+1]!==null)out.push({id:h.pair[i],time:r[0],rtt_ms:r[i+1],count:r[i+3],metric:WEBSITE_METRIC});});});out.stats_since=Number.isFinite(h.stats_since)?h.stats_since:0;return out;
}
function websiteQuality(status){
  var h=status.website_response_history||{},rank={};
  if(h.metric!==WEBSITE_METRIC||h.target_set!==WEBSITE_TARGET_SET)return rank;
  Object.keys(h.profile_statistics||{}).forEach(function(id){var s=h.profile_statistics[id];if(s.metric===WEBSITE_METRIC&&s.target_set===WEBSITE_TARGET_SET&&Number.isInteger(s.cycles)&&Number.isInteger(s.complete)&&s.cycles>=s.complete&&s.complete>=0&&Number.isFinite(s.sum_ms)&&s.sum_ms>=0)rank[id]={n:s.cycles,good:s.complete,sum:s.sum_ms};});return rank;
}
var UI_DATA_CAUSE=null;
function dataCause(status,now){
  if(!status||status.rpc_error)return {code:'STATUS-REQUEST-FAILED',text:bi('the page got no answer from the router program','страница не получила ответ от программы на роутере')};
  if(!observationFresh(status,now))return {code:'MONITOR-DATA-STALE',text:bi('the router has not sent fresh data'+(Number.isFinite(status.time)?' for '+Math.round(now-status.time)+' s':''),'роутер не присылает свежие данные'+(Number.isFinite(status.time)?' уже '+Math.round(now-status.time)+' с':''))};
  return {code:'VENDOR-OBSERVATION-PENDING',text:bi('the monitor has not finished observing this channel yet (up to a minute after a start or change)','мониторинг ещё не закончил наблюдение этого канала (до минуты после запуска или изменения)')};
}
function dataCauseText(prefix){var c=UI_DATA_CAUSE||dataCause(null,0);return (prefix||bi('Not available: ','Нет данных: '))+c.text+' ('+c.code+')';}
function profileHealth(profile,now){
  if(!profile.interface||profile.administrative_state==='disabled')return {state:'inactive',label:bi('Inactive','Неактивен')};
  if(!observationFresh(profile,now))return {state:'unknown',label:bi('Check data unavailable','Нет данных проверки')};
  if(['CHECK-001','CHECK-LIMIT'].indexOf(profile.code)>=0)return {state:'checking',label:bi('Checking','Проверяется')};
  if(profile.code)return {state:'failed',label:bi('Failed','Сбой')};
  if(profile.dns_ok===true&&profile.https_success>=2)return {state:'healthy',label:bi('Healthy','Работает')};
  return {state:'checking',label:bi('Checking','Проверяется')};
}
// Policy selection is independent of controller phase and VPN health.
function channelPathSelection(status,now,sourceId,targetId){
  status=status||{};var native=status.native_failover||{},path=status.channel_path;
  var required=native.mode==='continuous-pair'||native.proof_scope==='router-probed-ipv4'||!!(path&&(path.mode==='continuous-pair'||path.selection_proof==='fw3-kernel-marking')),authoritative=required||Object.prototype.hasOwnProperty.call(status,'channel_path');
  var result={authoritative:authoritative,selected:null,moving:false,code:authoritative?'KERNEL-POLICY-UNVERIFIED':null};
  if(!authoritative)return result;
  if(status.rpc_error||status.error){result.code='STATUS-REQUEST-FAILED';return result;}
  if(!observationFresh(status,now)){result.code='MONITOR-DATA-STALE';return result;}
  if(!path||typeof path!=='object'||Array.isArray(path))return result;
  if(required&&(path.mode!=='continuous-pair'||path.selection_proof!=='fw3-kernel-marking'||!Number.isFinite(path.valid_for)||path.valid_for<=0||path.valid_for>15||!Number.isFinite(path.checked_at)||path.time!==path.checked_at))return result;
  var maxAge=required?path.valid_for:30;
  var checkedAt=required?path.checked_at:path.time;
  if(!Number.isFinite(checkedAt)||now-checkedAt< -5||now-checkedAt>maxAge){result.code=required?'KERNEL-POLICY-UNVERIFIED':'MONITOR-DATA-STALE';return result;}
  var source=path.source_profile_id,target=path.target_profile_id;
  if(typeof source!=='string'||!source||typeof target!=='string'||!target||source===target||sourceId&&source!==sourceId||targetId&&target!==targetId){result.code='PAIR-POLICY-UNVERIFIED';return result;}
  result.moving=path.transitioning===true;
  if(result.moving){result.code=null;return result;}
  if(path.confirmed!==true||required&&path.kernel_policy_verified!==true)return result;
  if(path.active_profile_id!==source&&path.active_profile_id!==target){result.code='PAIR-POLICY-UNVERIFIED';return result;}
  result.selected=path.active_profile_id;result.code=null;return result;
}
function savedTransition(entry){
  entry=entry||{};
  var fields=['from_role','from_profile_id','destination_role','destination_profile_id','route_changed','transition_completed','transition_outcome','activation_reapply','before_policy_role'];
  var present=Object.prototype.hasOwnProperty.call(entry,'transition_metadata_present')||fields.some(function(key){return Object.prototype.hasOwnProperty.call(entry,key);});
  if(!present)return {present:false};
  function role(key,idKey){var value=entry[key],identifier=entry[idKey];return (value==='source'||value==='target')&&typeof identifier==='string'&&/^(openvpn:[0-9]+_[0-9]+|wireguard:peer_[0-9]+)$/.test(identifier)&&entry.source!==entry.target&&identifier===entry[value]?value:null;}
  var from=role('from_role','from_profile_id'),to=role('destination_role','destination_profile_id'),changed=entry.route_changed===true,unchanged=entry.route_changed===false;
  var outcome=['committed','restored','refused','policy-verified'].indexOf(entry.transition_outcome)>=0?entry.transition_outcome:null;
  var invalid=changed&&from&&to&&from===to||unchanged&&from&&to&&from!==to&&outcome!=='refused';
  if(invalid){from=null;to=null;}
  return {present:true,from:from,to:to,changed:changed,unchanged:unchanged,completed:entry.transition_completed===true,outcome:outcome,reapply:entry.activation_reapply===true,invalid:!!invalid};
}

function selectedProfile(status,now){
  var native=status.native_failover||{};
  var path=channelPathSelection(status,now,native.source,native.target);
  if(path.authoritative)return path.selected;
  if(status.rpc_error||!Number.isFinite(native.time)||now-native.time<0||now-native.time>30)return null;
  if(['COMMITTED','DEGRADED-ON-RESERVE'].indexOf(native.state)>=0)return native.target||null;
  if(native.state==='OBSERVING'&&native.certified===true)return native.source||null;
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
