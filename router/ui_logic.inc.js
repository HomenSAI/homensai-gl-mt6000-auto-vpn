// Monitor cadence is backend-derived; controller heartbeats, kernel proof and website results keep their own TTLs.
// Display tolerance on top of the router's freshness window: probe time (6 s) + UI poll (10 s) + a slow status call.
// Normal data must never blink to "stale"; a really stopped monitor still shows as stale within a minute.
var UI_DISPLAY_GRACE=25;
function observationValidFor(row){var n=row&&row.observation_valid_for;return (Number.isFinite(n)&&n>=30&&n<=900?n:90)+UI_DISPLAY_GRACE;}
function observationFresh(row,now){return !!row&&Number.isFinite(row.time)&&Number.isFinite(now)&&now-row.time>=-5&&now-row.time<=observationValidFor(row);}
// Order every status RPC by its browser dispatch sequence, never by the router's wall clock.
// NTP changes and router reboots may move server_time backwards; old page callbacks retain their original provenance.
var UI_STATUS_REQUEST_SEQUENCE=0,UI_STATUS_ORDER=new WeakMap();
// Long event lists come from the separate 'history' call and are merged into every status the page sees.
var UI_HISTORY=null,UI_HISTORY_AT=0,UI_HISTORY_BUSY=false;
function uiHistoryDue(){
  var page=typeof activeTab==='string'?activeTab:'';
  var every=['statistics','events','services','tests','analytics','switches'].indexOf(page)>=0?60000:300000;
  return !UI_HISTORY_BUSY&&Date.now()-UI_HISTORY_AT>=every;
}
function uiHistoryRefresh(){
  if(!uiHistoryDue()||typeof rpc==='undefined'||!rpc.declare)return;
  UI_HISTORY_BUSY=true;
  Promise.resolve().then(function(){return rpc.declare({object:'homensai-vpn',method:'history',expect:{}})();})
    .then(function(h){if(h&&typeof h==='object'&&!h.error){var first=!UI_HISTORY;UI_HISTORY=h;UI_HISTORY_AT=Date.now();if(first&&typeof UI_STATUS_REFRESH==='function')UI_STATUS_REFRESH();}})
    .catch(function(){UI_HISTORY_AT=Date.now()-240000;}).finally(function(){UI_HISTORY_BUSY=false;});
}
function uiMergeHistory(status){
  if(!status||typeof status!=='object'||!Array.isArray(status.history_split)||!UI_HISTORY)return status;
  status.history_split.forEach(function(path){
    var value=UI_HISTORY[path];if(value===undefined)return;
    var keys=path.split('.'),node=status;
    for(var i=0;i<keys.length-1;i++){if(!node[keys[i]]||typeof node[keys[i]]!=='object')return;node=node[keys[i]];}
    node[keys[keys.length-1]]=value;
  });
  return status;
}
function uiStatusRequest(call){
  uiHistoryRefresh();
  var order=++UI_STATUS_REQUEST_SEQUENCE,tick=typeof performance!=='undefined'&&typeof performance.now==='function'?performance.now()/1000:Date.now()/1000;
  // Charge the full request duration conservatively; transport cannot renew evidence TTLs.
  var promise=Promise.resolve().then(call).then(function(status){if(status&&typeof status==='object'){uiMergeHistory(status);UI_STATUS_ORDER.set(status,order);if(Number.isFinite(status.server_time))UI_STATUS_CLOCKS.set(status,{server:status.server_time,tick:tick});}return status;});
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
  var transition=uiTransitionModel(status,now),recovery=uiRecoveryModel(status,now);
  return JSON.stringify([light.key,light.title,light.code,op,transition.phase,recovery&&recovery.code,manual.busy,manual.uncertain,manual.direction,manual.primary.allowed,manual.reserve.allowed,manual.hold,manual.resume.allowed,path.selected,path.code,path.moving,Array.from(MANUAL_RESULT_SEEN.values()).map(function(t){return manualClockTick()-t<=300000;}),
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
// Owner rule: a channel always shows its delay. Without a current measurement the last known one is shown with
// its age (from this page or from the router's response history), never "out of date 0/3".
var UI_LAST_DELAY={};
function lastHistoryDelay(status,id){
  var h=(status||{}).website_response_history||{},side=Array.isArray(h.pair)?h.pair.indexOf(id):-1;
  if(side<0||!Array.isArray(h.rows))return null;
  for(var i=h.rows.length-1;i>=0;i--){var r=h.rows[i];if(Array.isArray(r)&&Number.isInteger(r[side+3])&&r[side+3]>0&&Number.isFinite(r[side+1]))return {rtt_ms:r[side+1]/(10*r[side+3]),time:r[0]+30,metric:h.metric};}
  return null;
}
function delayAge(seconds){seconds=Math.max(0,Math.round(seconds));return seconds<90?seconds+' '+bi('s ago','с назад'):Math.round(seconds/60)+' '+bi('min ago','мин назад');}
// The current measurement only (strict); channelDelayModel adds the last known delay for display.
function channelPingModel(p,status,now){
  if(status&&typeof status.response_metric==='string'&&status.response_metric.indexOf('icmp-')===0)return channelIcmpModel(p,status,now);
  return channelWebsiteModel(p,status,now);
}
function channelDelayModel(p,status,now){
  var ping=status&&typeof status.response_metric==='string'&&status.response_metric.indexOf('icmp-')===0;
  var model=channelPingModel(p,status,now),id=p&&p.id,metric=ping?status.response_metric:'websites';
  if(!id)return model;
  if(model.state==='ok'&&Number.isFinite(model.rtt_ms)){UI_LAST_DELAY[id+'|'+metric]={rtt_ms:model.rtt_ms,time:now};return model;}
  if(model.state==='inactive')return model;
  var last=UI_LAST_DELAY[id+'|'+metric],x=ping&&p.ping;
  if(!last&&x&&Number.isFinite(x.rtt_ms)&&Number.isFinite(x.time)&&x.target===String(status.response_metric).slice(5))last={rtt_ms:x.rtt_ms,time:x.time};
  if(!last){var h=lastHistoryDelay(status,id);if(h&&(ping?h.metric==='icmp-rtt-ms':h.metric===WEBSITE_METRIC))last=h;}
  if(!last)return model;
  var label=ping?bi('ping ','пинг ')+String(status.response_metric).slice(5):bi('three sites','три сайта');
  return {state:'last',code:model.code,rtt_ms:last.rtt_ms,successes:model.successes,kind:model.kind,
    text:websiteMs(last.rtt_ms)+' '+bi('ms','мс')+' · '+label+' · '+bi('last measured ','последний замер ')+delayAge(now-last.time)};
}
// Ping (ICMP echo through the tunnel to the chosen public DNS address): the owner's default response metric.
function channelIcmpModel(p,status,now){
  var x=p&&p.ping,target=String(status.response_metric).slice(5);
  function no(state,code){return {state:state,code:code,rtt_ms:null,successes:0,kind:'ping',text:bi('No fresh ping','Нет свежего пинга')};}
  if(!status||status.rpc_error||status.error)return no('unavailable','STATUS-REQUEST-FAILED');
  if(!observationFresh(status,now))return no('stale','MONITOR-DATA-STALE');
  if(!p||!p.interface||p.administrative_state==='disabled')return no('inactive','PING-UNAVAILABLE');
  if(!x||x.state==='checking')return no('checking','PING-PENDING');
  if(x.metric!=='icmp-rtt-ms'||x.target!==target||x.interface!==p.interface)return no('checking','PING-PENDING');
  if(!Number.isFinite(x.time)||!Number.isFinite(x.valid_for)||x.valid_for<=0||x.valid_for>465||now-x.time< -5||now-x.time>x.valid_for+(typeof UI_DISPLAY_GRACE==='number'?UI_DISPLAY_GRACE:0))return no('stale','PING-DATA-STALE');
  if(x.state!=='ok'||!Number.isFinite(x.rtt_ms))return no(x.state==='failed'?'failed':'unavailable',x.code||'PING-FAILED');
  return {state:'ok',code:null,rtt_ms:x.rtt_ms,successes:1,kind:'ping',text:websiteMs(x.rtt_ms)+' '+bi('ms','мс')+' · '+bi('ping ','пинг ')+target};
}
function channelWebsiteModel(p,status,now){
  var x=p&&p.website_response,n=x&&Number.isInteger(x.successes)&&x.successes>=0&&x.successes<=3?x.successes:0;
  function no(state,code){return {state:state,code:code,rtt_ms:null,successes:n,text:bi('No complete three-site check','Нет полной проверки трёх сайтов')+' · '+n+'/3'};}
  if(!status||status.rpc_error||status.error)return no('unavailable','STATUS-REQUEST-FAILED');
  if(!observationFresh(status,now))return no('stale','MONITOR-DATA-STALE');
  if(!p||!p.interface||p.administrative_state==='disabled')return no('inactive','WEBSITE-UNAVAILABLE');
  if(!x)return no('checking','WEBSITE-CHECK-PENDING');
  if(x.metric!==WEBSITE_METRIC||x.target_set!==WEBSITE_TARGET_SET||p.vendor_state!=='SETTLED'||typeof p.vendor_generation!=='string'||!/^[a-f0-9]{32}$/.test(p.vendor_generation)||x.generation!==p.vendor_generation||x.interface!==p.interface||typeof p.vendor_tunnel_id!=='string'||p.vendor_tunnel_id!==p.protocol+':'+p.interface||x.vendor_tunnel_id!==p.vendor_tunnel_id)return no('checking','WEBSITE-IDENTITY-CHANGED');
  if(x.state==='checking')return no('checking','WEBSITE-CHECK-PENDING');
  if(x.state==='inactive'||x.state==='unavailable')return no(x.state,'WEBSITE-UNAVAILABLE');
  if(!Number.isFinite(x.time)||!Number.isFinite(x.valid_for)||x.valid_for<=0||x.valid_for>465||now-x.time< -5||now-x.time>x.valid_for||x.state==='stale')return no('stale','WEBSITE-DATA-STALE');
  if(x.state!=='ok')return no(x.state==='partial'?'partial':'failed',x.state==='partial'?'WEBSITE-PARTIAL':'WEBSITE-RESPONSE-FAILED');
  var results=x.results,seen={},sum=0;
  if(x.successes!==3||x.attempted!==3||!Array.isArray(results)||results.length!==3)return no('unavailable','WEBSITE-UNAVAILABLE');
  if(!results.every(function(r){if(!r||!Object.prototype.hasOwnProperty.call(WEBSITE_URLS,r.id)||seen[r.id]||r.url!==WEBSITE_URLS[r.id]||r.state!=='ok'||r.code!=null||!Number.isFinite(r.elapsed_ms)||r.elapsed_ms<0||r.elapsed_ms>6000)return false;seen[r.id]=true;sum+=r.elapsed_ms;return true;})||!Number.isFinite(x.avg_ms)||x.avg_ms<0||x.avg_ms>6000||Math.abs(x.avg_ms-sum/3)>.051)return no('unavailable','WEBSITE-UNAVAILABLE');
  return {state:'ok',code:null,rtt_ms:x.avg_ms,successes:3,text:websiteMs(x.avg_ms)+' '+bi('ms','мс')};
}
function renderChannelPing(profile,status,now){
  var model=channelDelayModel(profile,status,now),detail=bi('Mean response of Google, Cloudflare and Wikipedia, all 3 required. Fresh DNS+TCP+TLS+HTTP headers; not a full page.','Средний ответ Google, Cloudflare и Wikipedia, нужны все 3. Новый DNS+TCP+TLS+HTTP-заголовки, не полная страница.')+' '+model.text+(model.code?' · '+model.code:'');
  var labels={checking:bi('Checking','Проверяется'),stale:bi('Check is out of date','Проверка устарела'),partial:bi('Incomplete check','Неполная проверка'),failed:bi('Check failed','Проверка не прошла'),inactive:bi('Tunnel is off','Туннель отключён'),unavailable:bi('No current result','Нет актуального результата')};
  var shown=model.rtt_ms==null?'— · '+(labels[model.state]||labels.unavailable)+(model.kind==='ping'?'':' · '+model.successes+'/3'):model.text;
  return E('small',{'class':'hv-channel-ping','data-ping-state':model.state,'data-latency-metric':WEBSITE_METRIC,'data-latency-state':model.state,'data-coverage':model.successes+'/3','title':detail,'aria-label':detail},shown);
}
// The response history follows the owner's metric: three websites or one ICMP echo (ping) per check.
function responseHistoryKind(h){return !h?null:h.metric===WEBSITE_METRIC&&h.target_set===WEBSITE_TARGET_SET?'websites':h.metric==='icmp-rtt-ms'&&h.target_set==='icmp-echo'?'ping':null;}
function websiteSamples(status,inventory){
  var h=status.website_response_history||{},out=[];
  latencyHistoryRows(status,inventory||{},routerWall()).forEach(function(r){[0,1].forEach(function(i){if(r[i+1]!==null)out.push({id:h.pair[i],time:r[0],rtt_ms:r[i+1],count:r[i+3],metric:WEBSITE_METRIC});});});out.stats_since=Number.isFinite(h.stats_since)?h.stats_since:0;out.kind=responseHistoryKind(h);return out;
}
function websiteQuality(status){
  var h=status.website_response_history||{},rank={};
  if(!responseHistoryKind(h))return rank;
  Object.keys(h.profile_statistics||{}).forEach(function(id){var s=h.profile_statistics[id];if(s.metric===h.metric&&s.target_set===h.target_set&&Number.isInteger(s.cycles)&&Number.isInteger(s.complete)&&s.cycles>=s.complete&&s.complete>=0&&Number.isFinite(s.sum_ms)&&s.sum_ms>=0)rank[id]={n:s.cycles,good:s.complete,sum:s.sum_ms};});return rank;
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
// A published transition phase stays authoritative only until the controller's own bounded deadline
// (journal deadline <= start + 120 s; the parent may finish up to 5 s later), then briefly "checking the result", then it is an unconfirmed result.
var UI_TRANSITION_STATES=['ARMED','APPLYING','WAIT-CLIENT','RESTORING'],UI_TRANSITION_GRACE=15;
function uiTransitionModel(status,now){
  status=status||{};var ns=status.native_failover||{};
  if(UI_TRANSITION_STATES.indexOf(ns.state)<0||Array.isArray(ns.blockers)&&ns.blockers.length||status.rpc_error||status.error||!observationFresh(status,now)||!Number.isFinite(ns.time)||now-ns.time< -5)return {live:false,overdue:false,state:null};
  var started=Number.isFinite(ns.started)&&ns.started<=ns.time+5&&ns.time-ns.started<=125?ns.started:null;
  var deadline=Number.isFinite(ns.deadline)&&ns.deadline>=ns.time-125&&ns.deadline<=(started||ns.time)+125?ns.deadline:(started||ns.time)+120;
  var phase=now<=deadline?'running':now<=deadline+UI_TRANSITION_GRACE?'checking':'overdue';
  // Guarded recovery of an interrupted switch restores the previous route; it is recovery in progress, never success.
  var state=ns.state==='RESTORING'&&(ns.restore_proof_source==='vendor-rebuild'||ns.reason==='SUPERVISOR-RECOVERY')?'RECOVERING':ns.state;
  return {live:phase!=='overdue',overdue:phase==='overdue',phase:phase,state:state,started:started,deadline:deadline};
}
// An unfinished journal without a live operation is a recovery state, never "switching".
var UI_RECOVERY_CODES=['PAIR-RECOVERY-REQUIRED','PAIR-STATE-UNVERIFIED','JOURNAL-INTEGRITY-FAILED'];
function uiRecoveryModel(status,now){
  status=status||{};if(status.rpc_error||status.error||!observationFresh(status,now))return null;
  var ns=status.native_failover||{},intent=status.auto_control||{},t=uiTransitionModel(status,now);
  if(t.overdue)return {code:'SWITCH-RESULT-UNCONFIRMED',stage:t.state,deadline:t.deadline};
  if(t.live)return null;
  var blockers=Array.isArray(ns.blockers)?ns.blockers:[],failure=intent.failure&&intent.failure.code;
  var code=blockers.filter(function(c){return UI_RECOVERY_CODES.indexOf(c)>=0;})[0]||(UI_RECOVERY_CODES.indexOf(failure)>=0&&intent.requested!=='on'?failure:null);
  return code?{code:code,stage:null,deadline:null}:null;
}
function uiRecoveryText(recovery){
  if(!recovery)return '';
  if(recovery.code==='SWITCH-RESULT-UNCONFIRMED')return bi('The router did not report the end of the switch by its deadline. The channel is not verified; do not repeat the switch. Stop remains available.','Роутер не сообщил о завершении переключения к предельному сроку. Канал не подтверждён; не повторяйте переключение. Stop остаётся доступен.');
  var text=typeof AUTO_REMEDIES!=='undefined'&&AUTO_REMEDIES.unfinished?AUTO_REMEDIES.unfinished.text:['A previous switch did not finish; recovery is needed.','Предыдущее переключение не завершилось; нужно восстановление.'];return bi(text[0],text[1]);
}
var UI_STAGE_TEXT={ARMED:['Preparing','Подготовка'],APPLYING:['Applying router rules','Применение правил роутера'],'WAIT-CLIENT':['Checking the new route','Проверка нового маршрута'],RESTORING:['Restoring the previous route','Возврат прежнего маршрута'],RECOVERING:['Recovery after an interrupted switch','Восстановление после прерванного переключения'],QUEUED:['Waiting for the controller','Ожидание контроллера'],CLAIMED:['Accepted by the controller','Принято контроллером'],SENT:['Sending the request','Отправка запроса']};
function uiClock(seconds){seconds=Math.max(0,Math.floor(seconds));return Math.floor(seconds/60)+':'+('0'+seconds%60).slice(-2);}
// One timer text for every surface: stage, elapsed since a known origin and the time left to the real backend deadline.
// Average confirmed switch time (manual and automatic share one transaction), kept by the router on flash.
var UI_SWITCH_AVG=null,UI_SWITCH_MEASURED=56;  // 30 Oct 2026 tests, 19 switches: switch 63 s, return 48 s
function uiOperationTimer(stage,elapsed,remaining,checking){
  var text=stage&&UI_STAGE_TEXT[stage]?bi(UI_STAGE_TEXT[stage][0],UI_STAGE_TEXT[stage][1]):'';
  if(Number.isFinite(elapsed))text+=(text?' · ':'')+uiClock(elapsed)+bi(' elapsed',' прошло');
  if(Number.isFinite(elapsed)&&!checking){
    // Expected time = measured average + 25% margin (router average, else the overnight MT3000 measurement).
    var expected=Math.round((Number.isFinite(UI_SWITCH_AVG)?UI_SWITCH_AVG:UI_SWITCH_MEASURED)*1.25),left=expected-elapsed;
    text+=(text?' · ':'')+(left>=1?bi('about ','ещё около ')+uiClock(left)+bi(' (expected ',' (ожидается ')+uiClock(expected)+')':bi('longer than expected (','дольше ожидаемого (')+uiClock(expected)+')');
    if(left<1&&Number.isFinite(remaining))text+=' · '+bi('limit in ','предел через ')+uiClock(remaining);
    return text;
  }
  if(checking)text+=(text?' · ':'')+bi('checking the result','проверяем результат');
  else if(Number.isFinite(remaining))text+=(text?' · ':'')+bi('limit in ','предел через ')+uiClock(remaining);
  return text;
}
// Owner wording for an available, unselected live channel; it promises a manual switch only when the router allows one now.
function channelAliveText(direction,status,now){var m=status&&typeof manualControlModel==='function'?manualControlModel(status,now):null;return m&&m[direction]&&m[direction].allowed?bi('Live, you can switch to it manually','Живой, можно переключиться на него вручную'):bi('Live; manual switching is unavailable now','Живой; ручное переключение сейчас недоступно');}
// Policy selection is independent of controller phase and VPN health.
// Freshness is judged once for the whole router answer (observationFresh); what the answer contains is judged
// at the time the router served it. The controller renews the kernel proof every ~5 s, but the page receives an
// answer only every 10-20 s; ageing the content by the page clock made a fresh proof look expired.
function statusServedAt(status,now){var t=status&&status.server_time;return Number.isFinite(t)&&t>0&&t<=now+5?Math.min(t,now):now;}
function channelPathSelection(status,now,sourceId,targetId){
  status=status||{};var native=status.native_failover||{},path=status.channel_path;
  var required=native.mode==='continuous-pair'||native.proof_scope==='router-probed-ipv4'||!!(path&&(path.mode==='continuous-pair'||path.selection_proof==='fw3-kernel-marking')),authoritative=required||Object.prototype.hasOwnProperty.call(status,'channel_path');
  var result={authoritative:authoritative,selected:null,moving:false,code:authoritative?'KERNEL-POLICY-UNVERIFIED':null};
  if(!authoritative)return result;
  if(status.rpc_error||status.error){result.code='STATUS-REQUEST-FAILED';return result;}
  if(!observationFresh(status,now)){result.code='MONITOR-DATA-STALE';return result;}
  if(!path||typeof path!=='object'||Array.isArray(path))return result;
  // A transition has no kernel proof yet; it is "moving" only while the controller's live operation is proven.
  if(required&&path.transitioning===true&&uiTransitionModel(status,now).live&&(!sourceId||!path.source_profile_id||path.source_profile_id===sourceId)&&(!targetId||!path.target_profile_id||path.target_profile_id===targetId)){result.moving=true;result.code=null;return result;}
  if(required&&(path.mode!=='continuous-pair'||path.selection_proof!=='fw3-kernel-marking'||!Number.isFinite(path.valid_for)||path.valid_for<=0||path.valid_for>15||!Number.isFinite(path.checked_at)||path.time!==path.checked_at))return result;
  var maxAge=required?path.valid_for:30;
  var checkedAt=required?path.checked_at:path.time;
  var servedAt=statusServedAt(status,now);
  if(!Number.isFinite(checkedAt)||servedAt-checkedAt< -5||servedAt-checkedAt>maxAge){result.code=required?'KERNEL-POLICY-UNVERIFIED':'MONITOR-DATA-STALE';result.expired=Number.isFinite(checkedAt)&&servedAt-checkedAt>maxAge;return result;}
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
// Fixed roles: primary first, reserve second, other servers after them. The active route never reorders rows.
function sortServerCards(rows,selected,now,roles){
  var ranks={healthy:1,checking:2,unknown:3,inactive:4,failed:5};roles=roles||[];
  return rows.map(function(row,index){var role=roles.indexOf(row.id);return {row:row,index:index,rank:role>=0&&row.id?role-10:ranks[profileHealth(row,now).state]};}).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).map(function(entry){return entry.row;});
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
// The only channel-lamp rule of the program. The sidebar, the Auto card, the manual cards, the channel cards,
// the server table, the Tests page and the live journal all ask this function, so they always show the same colour.
function channelLampPair(status,inventory){
  var path=status.channel_path||{},ns=status.native_failover||{},settings=(inventory||{}).settings||{},rows=status.profiles||[];
  var sourceId=settings.plan_source||path.source_profile_id||ns.source,targetId=settings.plan_target||path.target_profile_id||ns.target;
  return {source:rows.filter(function(p){return p.id===sourceId;})[0],target:rows.filter(function(p){return p.id===targetId;})[0]};
}
function channelLampRole(status,inventory,profile){
  var pair=channelLampPair(status,inventory);
  return profile&&pair.source&&profile.id===pair.source.id?'source':profile&&pair.target&&profile.id===pair.target.id?'target':null;
}
function channelLampTone(status,inventory,role,now,light){
  var pair=channelLampPair(status,inventory);
  if(status.rpc_error||status.error||!observationFresh(status,now))return {color:'grey',text:typeof dataCause==='function'?dataCause(status,now).text:bi('no router data','нет данных роутера'),carrier:false};
  light=light||(typeof autoLightModel==='function'?autoLightModel(status,inventory,now):null);
  var confirmed=(typeof heldConfirmedPath==='function'?heldConfirmedPath:manualConfirmedPath)(status,pair.source,pair.target,now);
  return manualChannelTone(pair[role],role,confirmed,now,!light||(typeof autoRuns==='function'?autoRuns(light):autoWorking(light)),status);
}
// Auto lamp colour, same rule as the sidebar: green while Auto runs (a manual choice never stops it).
function autoLampColor(light,paused){
  var signal=light&&typeof autoSignal==='function'?autoSignal(light):null;
  if(paused)return 'yellow';
  if(signal==='off')return 'grey';
  return (typeof autoRuns==='function'?autoRuns(light):typeof autoWorking==='function'&&autoWorking(light))?'green':signal==='yellow'?'yellow':'red';
}
