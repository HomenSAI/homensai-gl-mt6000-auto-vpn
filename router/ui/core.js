/* Shared readings for Simple and Console; Auto presentation comes from AUTO_SIGNAL_TABLE. */
var $=function(s,r){return (r||document).querySelector(s);},$$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));};
var store={get:function(k,d){try{var v=window.localStorage.getItem(k);return v===null?d:v;}catch(e){return d;}},set:function(k,v){try{window.localStorage.setItem(k,v);}catch(e){}}};
var LANG_KEY='homensai-vpn-language',THEME_KEY='homensai-vpn-theme',VIEW_KEY='homensai-vpn-view';
function t(ru,en){return locale==='en'?(en===undefined?ru:en):ru;}
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
var NODATA=function(){return t('нет данных','no data');};
var HV={inv:{settings:{},profiles:[],servers:[]},st:{},root:null,view:'simple',page:'home',tab:'ch',wiz:false,step:1,open:{},dirty:{},draft:null,
  filters:{a:'all',d:'all'},all:false,evOpen:{},probeRows:null,speedRun:null,scan:null,busy:{},theme:'system',codeQ:'',codePage:0};
var V=null;  // the one snapshot of readings for the current paint

/* ---------------- Versions and identity (attribution on every view) ---------------- */
function VER(){
  var st=HV.st||{},s=(HV.inv||{}).settings||{};
  var okv=function(v){return typeof v==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(v);};
  var model=s.detected_router_model==='mt3000'?'GL.iNet GL-MT3000 · Beryl AX':s.detected_router_model==='mt6000'?'GL.iNet GL-MT6000 · Flint 2':'GL.iNet GL-MT6000 · Flint 2 / GL-MT3000 · Beryl AX';
  return {app:okv(st.version)?st.version:HV_AGENT,style:HV_STYLE,model:model,
    detected:s.detected_router_model==='mt3000'||s.detected_router_model==='mt6000',terms:TERMS_VERSION,mismatch:okv(st.version)&&st.version!==HV_AGENT};
}

/* ---------------- Router calls (the same RPCs and arguments as before) ---------------- */
/* BH3-02: the rpcd dispatcher answers a button whose Lua outcome is unclear (ubus timeout, failed reply write) with
   RPC-BRIDGE-UNCONFIRMED instead of replaying the click through agent.py. That is a lost answer, not a refusal: the call
   rejects like a transport loss, so every button's lost-answer path runs (F-35: re-read the state, then offer Retry). */
function rpcBridgeLost(r){if(r&&r.code==='RPC-BRIDGE-UNCONFIRMED'){var e=new Error('RPC-BRIDGE-UNCONFIRMED');e.code='RPC-BRIDGE-UNCONFIRMED';throw e;}return r;}
function rpcCall(method,params){var f=rpc.declare({object:'homensai-vpn',reject:true,method:method,params:params||[],expect:{}});
  return function(){return Promise.resolve(f.apply(null,arguments)).then(rpcBridgeLost);};}
function codeOk(c){return typeof c==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(c);}

/* ---------------- ONE snapshot of readings ---------------- */
function snap(){
  var st=HV.st||{},inv=HV.inv||{},now=statusNow(st);
  var d=simpleHomeModel(st,inv,now),light=d.light;
  var sel=manualSelectionModel(st,d.source,d.target,now);
  var path=Object.assign({},d.path||{},{moving:!!d.moving});
  return {st:st,inv:inv,s:inv.settings||{},now:now,d:d,light:light,control:d.control,op:d.operation,src:d.source,tgt:d.target,sel:sel,path:path,
    manual:manualControlModel(st,now),runs:autoRuns(light),terms:termsAccepted(inv),monitor:monitorLightModel(st,inv,now,false)};
}
function roleProfile(role){return role==='primary'?V.src:V.tgt;}
function profileName(p){
  if(!p)return NODATA();
  var row=((HV.inv||{}).servers||[]).filter(function(r){return r&&r.profile===p.id;})[0];
  return (row&&row.name)||p.name||p.router_name||p.id;
}
function chName(role){var p=roleProfile(role);return p?profileName(p):t('не выбран','not chosen');}
function roleName(role){return role==='primary'?t('Основной','Primary'):t('Резерв','Reserve');}
function ageText(sec){sec=Math.max(0,Math.round(sec));return sec<90?sec+' '+t('с','s'):sec<5400?Math.round(sec/60)+' '+t('мин','min'):Math.round(sec/3600)+' '+t('ч','h');}
function reading(role){
  return readingOf(roleProfile(role),role==='primary'?'source':'target');
}
/* The one reading of a VPN channel: lamp, state word, response time, age. key is 'source' or 'target' for the pair's channels, null for a
   channel outside the pair (the wizard lists every VPN client; it must show a channel the way its card does). */
function readingOf(p,key){
  if(!p)return {lamp:'n',state:'none',text:t('канал не выбран','channel not chosen'),ms:null,ageText:t('выберите пару в Настройках','choose the pair in Settings'),why:''};
  var h=profileHealth(p,V.now).state,tone=key?manualChannelTone(p,key,V.path,V.now,V.runs,V.st):{text:'',switching:false};
  var stale=V.d.dataUnavailable||h==='unknown';
  if(stale)return {lamp:'n',state:'stale',text:t('нет свежих данных','no fresh data'),ms:null,ageText:t('нет свежих данных','no fresh data'),why:tone.text};
  var delay=channelDelayModel(p,V.st,V.now),ms=delay&&Number.isFinite(delay.rtt_ms)?Math.round(delay.rtt_ms):null;
  var age=t('проверено '+ageText(V.now-p.time)+' назад','checked '+ageText(V.now-p.time)+' ago');
  if(tone.switching&&V.d.moving)return {lamp:'y',state:'switching',text:t('переключение…','switching…'),ms:ms,ageText:age,why:tone.text};
  if(h==='failed')return {lamp:'r',state:'bad',text:t('не отвечает','not responding')+(codeOk(p.code)?' · '+p.code:''),ms:null,ageText:age,why:tone.text,code:p.code};
  if(h==='inactive')return {lamp:'r',state:'bad',text:t('туннель отключён','tunnel is off'),ms:null,ageText:age,why:tone.text};
  if(h==='checking')return {lamp:'y',state:'checking',text:t('проверяется','checking'),ms:ms,ageText:age,why:tone.text};
  return {lamp:'g',state:'ok',text:t('работает','works'),ms:ms,ageText:age,why:tone.text};
}
/* Inventory profile joined to its status row (by id, else GL tunnel id); the status row wins. */
function statusProfileOf(p){
  var rows=(V.st||{}).profiles||[];
  return rows.filter(function(x){return x&&x.id===p.id;})[0]||(p.vendor_tunnel_id?rows.filter(function(x){return x&&x.vendor_tunnel_id===p.vendor_tunnel_id;})[0]:null)||null;
}
function joinedProfile(p){return Object.assign({},p,statusProfileOf(p)||{});}
function pairKeyOf(p){return V.src&&V.src.id===p.id?'source':V.tgt&&V.tgt.id===p.id?'target':null;}
function stateWord(x){return x.state==='bad'?t('не отвечает','not responding'):x.state==='stale'?t('нет свежих данных','no fresh data'):x.state==='checking'?t('проверяется','checking'):x.state==='switching'?t('переключается','switching'):t('не определён','not determined');}
/* Speed test of another session: the router reports the pause in status.speed_pause. */
function speedPauseNow(){
  var p=V&&V.st&&V.st.speed_pause;
  // pause read from the status reply itself
  if(!p||p.active!==true||V.st.rpc_error||V.st.error)return null;
  return {phase:p.phase,auto:p.auto_paused===true,monitor:p.monitor_paused===true};
}
function selectedRole(){var r=V.d.selectedRole;return r==='source'?'primary':r==='target'?'reserve':null;}
function autoOn(){return autoEnabled(V.light);}
/* AUTO_SIGNAL_TABLE words (legacy page); this page shows autoIndicator(). */
function autoState(){
  var l=V.light;return {lamp:{green:'g',yellow:'y',red:'r',off:'n'}[autoSignal(l)],text:autoStateText(l),sub:[l.title,l.hint,codeOk(l.code)?l.code:''].filter(Boolean).join(' · ')};
}
/* Two indicators (owner 07.11.2026; contract: docs/OVERVIEW-PATH-COLOURS.md). overall() = internet only; autoIndicator() = Auto.
   Stale evidence is grey on both, never green or red. */
var FAIL_WINDOW=60;
/* No "failed since" in status: page-local timer from the first sight of the failure. */
function failAge(id){
  var f=HV.failSeen;
  if(!f||f.id!==id||!Number.isFinite(f.since)||V.now<f.since)f=HV.failSeen={id:id,since:V.now};
  return V.now-f.since;
}
/* Plan item 53: no answer from the router for FAIL_WINDOW s turns both lamps grey with the time of the last answer, never the last
   green or yellow. Page-local, no timer of its own (paintLive ticks): HV.answerAt is stamped on a good reply, HV.shownAt on page
   start and on return to the tab (time in a hidden tab does not count). */
function routerSilence(){
  var from=Math.max(HV.answerAt||0,HV.shownAt||0),wall=Date.now()/1000;
  if(!from||wall-from<FAIL_WINDOW)return null;
  return {age:wall-from,last:Number.isFinite(HV.answerAt)?t('последний ответ ','last answer ')+fmtTime(HV.answerAt):t('ответов роутера на этой странице ещё не было','no router answer on this page yet')};
}
/* BH2-03: the router answered, but with a monitor error (SERVICE-STOPPED, SYSTEM-001): not silence. It wins over the grey state; the
   main light stays grey (channel state unknown), the words name the error and the fix, the Auto indicator is red. */
function monitorDown(){var st=V.st||{};return !st.rpc_error&&typeof st.error==='string'&&monitorLightModel(st,V.inv,V.now,monitorStartedRecently(V.now)).key==='problem';}
function overall(){
  var d=V.d,l=V.light||{},sr=selectedRole(),auto=autoOn()&&l.key!=='off',w=V.st.wan_diagnosis,sil=routerSilence();
  var O=function(lamp,k,title,sub,icon){return {lamp:lamp,key:k,title:title,sub:sub,icon:icon||''};};
  if(monitorDown())return O('n','monitor-down',V.monitor.title,t('Роутер отвечает, но мониторинг не выдаёт данных ('+V.monitor.code+'), состояние каналов неизвестно. Нажмите «Восстановить мониторинг».','The router answers, but monitoring produces no data ('+V.monitor.code+'); channel state unknown. Press "Restore monitoring".'),'!');
  if(sil)return O('n','silent',t('Роутер не отвечает','Router not answering'),sil.last+t(' · нет ответа уже '+ageText(sil.age)+', состояние каналов неизвестно. Проверьте питание и сеть роутера.',' · no answer for '+ageText(sil.age)+'; channel state unknown. Check the router power and network.'),'?');
  // owner 07.11: internet works during a speed test: green; Auto indicator yellow
  if(speedPauseNow()&&!d.connectionLost)return O('g','speed',t('Интернет работает','Internet works'),t('Идёт тест скорости: Auto и фоновый мониторинг на паузе, VPN остаются подключёнными. Состояние вернётся само после теста.','Speed test running: Auto and background monitoring are paused; the VPNs stay connected. The state returns by itself after the test.'));
  if(!d.dataUnavailable&&w&&typeof w==='object'&&w.code==='WAN-DOWN'&&observationFresh(w,V.now))return O('r','wan-down',t('Нет интернета','No internet'),t('Роутер сам проверил: у провайдера (WAN) нет интернета, VPN тут ни при чём. Auto не переключает каналы, пока WAN не вернётся.','The router checked itself: the provider (WAN) has no internet; this is not a VPN problem. Auto does not switch channels until the WAN is back.'),'✕');
  if(d.dataUnavailable&&(d.connectionLost||!observationFresh(V.st,V.now)))return O('n','stale',t('Нет свежих данных','No fresh data'),d.connectionLost?t('Нет связи с роутером. Проверьте подключение и обновите страницу.','No connection to the router. Check the connection and reload the page.'):t('Роутер давно не присылал измерений, состояние каналов неизвестно. Нажмите «Проверить сейчас».','The router has not sent measurements for a while; channel state is unknown. Press "Check now".'),'?');
  if(d.dataUnavailable)return O('n','stale',d.title||t('Нет свежих данных','No fresh data'),d.summary,'?');
  var a=sr?reading(sr):null,o=sr?reading(sr==='primary'?'reserve':'primary'):null;
  if(!a||a.state!=='bad')HV.failSeen=null;
  if(a&&a.state==='bad'&&o.state==='bad')return O('r','both-down',t('Нет интернета через VPN','No internet through the VPN'),t('Оба канала не отвечают. Откройте «Помощь → У меня пропал интернет».','Both channels fail. Open "Help → I have no internet".'),'✕');
  // route switch = transition; Auto start/stop is not
  var ph=autoPhase(),routeMove=d.moving||l.key==='switching'&&!(V.op==='starting'||V.op==='stopping'||ph==='STARTING'||ph==='STOPPING'||V.control&&V.control.paused);
  if(routeMove)return O('y','moving',t('Переключение…','Switching…'),d.moving?d.summary:[l.title,l.hint].filter(Boolean).join(' · ')||d.summary);
  if(d.state==='setup')return O('n','setup',d.title,d.summary,'?');
  var other=sr?roleName(sr==='primary'?'reserve':'primary').toLowerCase():'';
  // failed traffic channel: transition while Auto acts (FAIL_WINDOW s), else no internet
  if(a&&a.state==='bad'){
    if(auto){
      var age=failAge(roleProfile(sr).id);
      if(age>=FAIL_WINDOW)return O('r','current-down-late',t('Нет интернета','No internet'),t('Текущий канал не отвечает уже '+ageText(age)+', Auto пока не переключил. Другой канал: '+stateWord(o)+'. Откройте «Помощь → У меня пропал интернет».','The current channel has not responded for '+ageText(age)+' and Auto has not switched yet. The other channel: '+stateWord(o)+'. Open "Help → I have no internet".'),'✕');
      if(o.state==='ok')return O('y','current-down',t('Текущий канал не отвечает','Current channel is not responding'),t('Auto переключит на '+other+' '+detectorPhrase(true)+'.','Auto will switch to the '+other+' '+detectorPhrase(false)+'.'));
      return O('y','current-down',t('Текущий канал не отвечает','Current channel is not responding'),t('Другой канал: '+stateWord(o)+'. Проверка не доказала, что интернета нет совсем. Нажмите «Проверить сейчас».','The other channel: '+stateWord(o)+'. The check has not proven that there is no internet at all. Press "Check now".'));
    }
    return O('r','current-down-off',t('Текущий канал не отвечает','Current channel is not responding'),o.state==='ok'?t('Ручной режим (Auto выключен). Включите Auto или переключитесь вручную.','Manual mode (Auto is off). Turn Auto on or switch manually.'):t('Ручной режим (Auto выключен). Другой канал: '+stateWord(o)+'.','Manual mode (Auto is off). The other channel: '+stateWord(o)+'.'),'✕');
  }
  if(a&&a.state==='stale')return O('n','stale',t('Нет свежих данных','No fresh data'),t('Нет свежей проверки канала, по которому идёт трафик. Нажмите «Проверить сейчас».','No fresh check of the channel that carries traffic. Press "Check now".'),'?');
  if(!sr||a.state!=='ok')return O('y','checking',t('Проверка канала','Checking the channel'),sr?t('Канал, по которому идёт трафик, проверяется.','The channel that carries traffic is being checked.'):t('Рабочий канал уточняется.','The working channel is being confirmed.'));
  var ai=autoIndicator(),autoWords=ai.key==='on'?t('Auto включён: при сбое переключит сам.','Auto is on: it switches by itself on a failure.'):ai.key==='off'?t('Ручной режим (Auto выключен): при сбое канала переключения не будет.','Manual mode (Auto is off): nothing switches if a channel fails.'):ai.key==='stuck'?t('Auto остановлен и сейчас не переключит: нужно восстановление.','Auto is stopped and will not switch now: recovery needed.'):ai.text+'.';
  if(sr==='primary')return O('g','primary',t('Интернет работает','Internet works'),t('Трафик идёт через основной канал. ','Traffic uses the primary channel. ')+autoWords);
  var back=V.s.recovery_return_policy!=='hold_reserve';
  return O('g','reserve',t('Работает через резерв','Works via the reserve'),t('Интернет есть, но запаса нет, пока основной не вернётся. ','There is internet, but no spare channel until the primary is back. ')+(o.state==='ok'?t('Основной снова здоров — '+(back&&ai.key==='on'?'Auto вернёт трафик по правилам.':'вернуть можно вручную.'),'Primary is healthy again — '+(back&&ai.key==='on'?'Auto will return by the rules.':'return manually.')):o.state==='bad'?t('Основной не отвечает.','Primary is not responding.'):t('Основной: '+stateWord(o)+'.','Primary: '+stateWord(o)+'.'))+' '+autoWords);
}
function autoPhase(){return ((V.st||{}).auto_control||{}).pair_phase||null;}
/* Stuck Auto: phase, controller state and codes for the line and tooltip. */
function stuckReason(){
  var ns=(V.st||{}).native_failover||{},l=V.light||{},out=[];
  var add=function(x){if(typeof x==='string'&&/^[A-Z][A-Z0-9_-]{0,95}$/.test(x)&&out.indexOf(x)<0)out.push(x);};
  if(autoPhase()==='HELD')add('HELD');
  if(['BLOCKED','RELEASE-PENDING','STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE','TRIAL-REQUIRED','EXPIRED'].indexOf(ns.state)>=0)add(ns.state);
  add(l.code);(Array.isArray(ns.blockers)?ns.blockers:[]).forEach(add);
  return out.join(' · ');
}
/* The line under the Auto indicator, without repeats. */
function autoDetail(){
  var ai=autoIndicator(),parts=[];
  if(ai.key==='silent'||ai.key==='monitor-down')return ai.reason;
  [ai.reason||''].concat(autoState().sub.split(' · ')).forEach(function(p){String(p).split(' · ').forEach(function(q){if(q&&parts.indexOf(q)<0)parts.push(q);});});
  return parts.join(' · ');
}
/* The Auto indicator and the switch track (data-sig). */
function autoIndicator(){
  var d=V.d,l=V.light||{},key=l.key,ph=autoPhase(),sr=selectedRole(),a=sr&&!d.dataUnavailable?reading(sr):null;
  var A=function(lamp,k,text,icon){return {lamp:lamp,key:k,text:text,icon:icon||''};},sil=routerSilence();
  if(monitorDown()){var m=A('r','monitor-down',t('Auto не работает: мониторинг остановлен','Auto not working: monitoring stopped'),'⚠');m.reason=V.monitor.title+' · '+V.monitor.code;return m;}
  if(sil){var z=A('n','silent',t('Auto: роутер не отвечает','Auto: router not answering'),'?');z.reason=sil.last;return z;}
  if(speedPauseNow()&&!d.connectionLost)return A('y','paused',t('Auto на паузе: тест скорости','Auto paused: speed test'));
  if(d.dataUnavailable||l.stale||V.op==='unconfirmed')return A('n','stale',t('Auto: нет свежих данных','Auto: no fresh data'),'?');
  if(V.op==='starting'||ph==='STARTING')return A('y','starting',t('Auto запускается','Auto is starting'));
  if(V.op==='stopping'||ph==='STOPPING')return A('y','stopping',t('Auto выключается','Auto is stopping'));
  if(V.control&&V.control.paused)return A('y','paused',t('Auto на паузе','Auto is paused'));
  var on=autoOn();
  // "the selected channel has failed" is Auto at work on a failure, not Auto stuck
  if(key==='problem'&&!(on&&a&&a.state==='bad')){var x=A('r','stuck',t('Auto остановлен: нужно восстановление','Auto stopped: recovery needed'),'⚠');x.reason=stuckReason();return x;}
  if(key==='off')return A('r','off',t('Ручной режим (Auto выключен)','Manual mode (Auto is off)'),'○');
  if(on)return A('g','on',t('Auto включён','Auto is on'));
  return A('n','pending',t('Состояние Auto подтверждается','Auto state is being confirmed'),'?');
}
/* Which rule makes Auto leave a failed channel (from the active settings). */
function failureModel(){var m=(V&&V.s||{}).failure_model;return ['hmm','hmm-fast','consecutive'].indexOf(m)>=0?m:'hmm';}
function detectorPhrase(ru){
  var m=failureModel(),s=(V&&V.s)||{},n=Number(s.recovery_failures)||3,or=Number.isInteger(s.hmm_or_failures)?s.hmm_or_failures:null;
  if(m==='consecutive')return ru?'после '+n+' неудачных проверок подряд':'after '+n+' failed checks in a row';
  var model=m==='hmm-fast'?(ru?'когда быстрая вероятностная модель (HMM) решит, что сбой не короткий':'when the fast probabilistic model (HMM) decides the outage is not a blip'):(ru?'когда вероятностная модель (HMM) решит, что сбой не короткий':'when the probabilistic model (HMM) decides the outage is not a blip');
  return or?model+(ru?', или после '+or+' неудачных проверок подряд':', or after '+or+' failed checks in a row'):model;
}

/* ---------------- Time ---------------- */
function fmtTime(sec,withDay){
  if(!Number.isFinite(sec))return '—';
  var opt={timeZone:'Europe/Berlin',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false};
  var day=function(x){return new Date(x*1000).toLocaleDateString('en-CA',{timeZone:'Europe/Berlin'});};
  var dd=new Date(sec*1000).toLocaleDateString('ru-RU',{timeZone:'Europe/Berlin',day:'2-digit',month:'2-digit'});
  return (withDay||day(sec)!==day(V?V.now:Date.now()/1000)?dd+' ':'')+new Date(sec*1000).toLocaleTimeString('ru-RU',opt);
}

/* ---------------- Events (journal of the router: one list for every view) ---------------- */
var SWITCH_STATES=['APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','ROLLED-BACK','RETURNED','STOPPED-ON-RESERVE','DEGRADED-ON-RESERVE'];
function eventRows(){
  var rows=[];try{rows=journalRows(V.st,null,V.now)||[];}catch(e){rows=[];}
  return rows.filter(function(r){return r&&Number.isFinite(r.time);}).sort(function(a,b){return b.time-a.time;});
}
function evKind(e){
  var tr=savedTransition(e),def=journalDefinition(e);
  var sw=tr.present?tr.changed&&!tr.reapply&&tr.outcome!=='refused':e.return_primary===true||SWITCH_STATES.indexOf(e.state)>=0;
  var lvl=def.level||e.level;
  // code-only low-severity event (planned reboot, clean restart): grey lamp
  if(!e.state&&!tr.present&&codeOk(e.code)&&typeof codeSeverity==='function'&&codeSeverity(e.code)==='low'&&e.level!=='error'&&e.level!=='warning')lvl=null;
  return {sw:sw,done:tr.present?tr.completed&&['committed','restored'].indexOf(tr.outcome)>=0:['COMMITTED','ROLLED-BACK','RETURNED'].indexOf(e.state)>=0||e.return_primary===true,
    problem:lvl==='error'||lvl==='warning'||e.level==='error'||e.level==='warning',mine:e.action_source==='manual',lamp:lvl==='error'||e.level==='error'?'r':lvl==='warning'||e.level==='warning'?'y':lvl==='ok'?'g':'n'};
}
var EVF={all:function(){return true;},switch:function(e){return evKind(e).sw;},problem:function(e){return evKind(e).problem;},mine:function(e){return evKind(e).mine;}};
function evKey(e){return e.key||e.time+':'+(e.state||'')+':'+(e.code||'');}
function evParts(e){var x='';try{x=journalMessage(e,V.st,true)||'';}catch(err){x=e.state||e.code||'';}return String(x).split(' · ');}
function evWhy(e){
  var def=journalDefinition(e),m=def.meaning||def.message||['',''],rest=evParts(e).slice(1).filter(Boolean);
  return t(m[1],m[0])+(rest.length?' '+rest.join(' · ')+'.':'');
}
function evText(e){return evParts(e)[0]+(e.action_source==='manual'?t(' (вы)',' (you)'):'');}
function fmtSpan(s){if(!Number.isFinite(s))return '—';if(s<60)return (Math.round(s*10)/10).toFixed(1).replace('.',locale==='en'?'.':',')+' '+t('с','s');var m=Math.round(s/60);return m<60?m+' '+t('мин','min'):Math.floor(m/60)+' '+t('ч','h')+' '+(m%60)+' '+t('мин','min');}
function lastSwitch(){return eventRows().filter(function(e){var k=evKind(e);return k.sw&&k.done;})[0]||null;}
function eventsHTML(n,filter,opts){
  opts=opts||{};var list=eventRows().filter(EVF[filter||'all']).slice(0,n);
  if(!list.length)return '<p class="mute">'+(V.d.dataUnavailable?t('Нет свежих данных','No fresh data'):t('Событий нет','No events'))+'</p>';
  var op=function(e,i){var k=evKey(e);if(HV.evOpen[k]!==undefined)return HV.evOpen[k];return opts.open||(opts.openFirst&&i===0)||(opts.openSwitch&&evKind(e).sw);};
  return '<ul class="evl">'+list.map(function(e,i){var k=evKind(e),code=codeOk(e.code)&&e.code!=='OK'?e.code:'';
    return '<li><div class="ev-h" data-act="evx" data-k="'+esc(evKey(e))+'" role="button" tabindex="0" aria-expanded="'+(op(e,i)?'true':'false')+'"><span class="tm">'+fmtTime(e.time)+'</span><i class="lamp '+k.lamp+' mt4"></i><span class="tx">'+esc(evText(e))+(code?' <a class="code" href="#" data-act="code" data-code="'+esc(code)+'">'+esc(code)+'</a>':'')+'</span></div><div class="ev-why"'+(op(e,i)?'':' hidden')+'>'+t('Почему: ','Why: ')+esc(evWhy(e))+'</div></li>';}).join('')+'</ul>';
}
function filtersHTML(cur,id){return '<div class="filters" role="group" data-filters="'+id+'">'+[['all',t('Все','All')],['switch',t('Переходы','Switches')],['problem',t('Проблемы','Problems')],['mine',t('Мои действия','My actions')]].map(function(f){return '<button data-act="filter" data-f="'+f[0]+'" data-id="'+id+'" aria-pressed="'+(cur===f[0])+'">'+f[1]+'</button>';}).join('')+'</div>';}

/* ---------------- Statistics from the router's own records ---------------- */
function routeSegments(){var r=((V.st.accounting||{}).reliability||{}).route_history||{};return Array.isArray(r.segments)?r.segments:[];}
function sumKinds(kinds,from,to){return segmentSeconds(routeSegments(),kinds,from,to);}
function segmentSeconds(segments,kinds,from,to){var s=0;segments.forEach(function(g){if(!g||kinds.indexOf(g.kind)<0||!Number.isFinite(g.start))return;var a=Math.max(g.start,from),b=Math.min(Number.isFinite(g.end)?g.end:to,to);if(b>a)s+=b-a;});return s;}
/* Route-selection share (review F-55): route_history records which channel carried the route, not whether it was healthy;
   a selected but failing channel still counts as selected. So this is "VPN route selected" over the observed time, shown
   with its coverage of the window; unobserved time stays unknown and is never counted as up or down. */
function routeShare(segments,from,to){
  var selected=segmentSeconds(segments,['source','target'],from,to),known=segmentSeconds(segments,['source','target','switching','down','blocked'],from,to);
  return {selected:selected,known:known,unknown:segmentSeconds(segments,['unknown'],from,to),window:to-from,share:known>0?selected/known:null,coverage:to>from?known/(to-from):null};
}
function episodes(){try{return switchTimeline(eventRows().slice().reverse());}catch(e){return [];}}
function stats(){
  var now=V.now,from=now-86400,eps=episodes().filter(function(e){return e.kind!=='recovery';});
  var share=routeShare(routeSegments(),from,now),known=share.known,pct=function(x,d){return num((Math.floor(x*Math.pow(10,d+2))/Math.pow(10,d)).toFixed(d));};
  var det=eps.map(function(e){return e.detect;}).filter(Number.isFinite),avg=function(a){return a.length?a.reduce(function(x,y){return x+y;},0)/a.length:null;};
  var timing=V.st.switch_timing||{},sw24=eps.filter(function(e){return Number.isFinite(e.reserve)&&e.reserve>=from;}).length;
  var onRes=sumKinds(['target'],from,now),num=function(x){return String(x).replace('.',locale==='en'?'.':',');};
  return {avail24:known>0?pct(share.share,1)+' %':NODATA(),cover24:known>0?pct(share.coverage,share.coverage<0.01?2:1)+' %':null,sw24:V.d.dataUnavailable&&!eps.length?NODATA():String(sw24),
    swAvg:Number.isFinite(timing.avg_seconds)?fmtSpan(timing.avg_seconds):NODATA(),detect:avg(det)!=null?fmtSpan(avg(det)):NODATA(),
    onRes:routeSegments().length?ageText(onRes):NODATA(),eps:eps};
}
function statsTiles(){var s=stats();return '<div class="tiles"><div class="tile" title="'+esc(t('Доля наблюдаемого времени, когда трафик шёл по выбранному VPN-маршруту. Это не здоровье канала: выбранный, но отказавший канал тоже считается. Ненаблюдаемое время не учитывается.','Share of the observed time in which traffic took the selected VPN route. This is not channel health: a selected but failing channel counts too. Unobserved time is not counted.'))+'"><b>'+esc(s.avail24)+'</b><span>'+t('маршрут через VPN выбран, 24 ч','VPN route selected, 24 h')+(s.cover24?' · '+t('наблюдалось ','observed ')+esc(s.cover24)+t(' суток',' of the day'):'')+'</span></div><div class="tile"><b>'+esc(s.sw24)+'</b><span>'+t('переходов за 24 ч','switches 24 h')+'</span></div><div class="tile"><b>'+esc(s.swAvg)+'</b><span>'+t('среднее переключение','avg switch time')+'</span></div><div class="tile"><b>'+esc(s.detect)+'</b><span>'+t('обнаружение сбоя','failure detection')+'</span></div><div class="tile"><b>'+esc(s.onRes)+'</b><span>'+t('на резерве за 24 ч','on reserve 24 h')+'</span></div></div>';}
function latencyChart(){
  var W=640,H=170,P=28,now=V.now,start=now-6*3600,rows=[];
  try{rows=latencyHistoryRows(V.st,V.inv,now).filter(function(r){return r[0]>=start;});}catch(e){rows=[];}
  if(rows.length<2)return '<p class="mute">'+t('Данных пока нет: роутер ещё не накопил историю отклика за 6 часов.','No data yet: the router has no 6-hour response history.')+'</p>';
  var max=0;rows.forEach(function(r){[1,2].forEach(function(i){if(r[i]!=null&&r[i]>max)max=r[i];});});max=Math.max(30,Math.ceil(max/30)*30);
  var x=function(ts){return P+(ts-start)/(now-start)*(W-P-6);},y=function(v){return H-20-(v/max)*(H-34);};
  var path=function(i){var d='',pen=false,prev=null;rows.forEach(function(r){var v=r[i];if(v==null||(prev!=null&&r[0]-prev>900)){pen=false;}if(v==null){prev=null;return;}d+=(pen?'L':'M')+x(r[0]).toFixed(1)+' '+y(v).toFixed(1)+' ';pen=true;prev=r[0];});return d;};
  var gaps='',outage=null;rows.forEach(function(r){if(r[5]==='down'||r[5]==='blocked'){gaps+='<rect class="gap" x="'+(x(r[0])-4).toFixed(1)+'" y="10" width="8" height="'+(H-30)+'"/>';outage=outage||r[0];}});
  var grid=[0,max/3,2*max/3,max].map(function(v){v=Math.round(v);return '<line class="axis" x1="'+P+'" x2="'+W+'" y1="'+y(v)+'" y2="'+y(v)+'"/><text x="2" y="'+(y(v)+3)+'">'+v+'</text>';}).join('');
  var lab=['−6 '+t('ч','h'),'−4 '+t('ч','h'),'−2 '+t('ч','h'),t('сейчас','now')].map(function(l,i){return '<text x="'+(P+i*(W-P-30)/3)+'" y="'+(H-4)+'">'+l+'</text>';}).join('');
  return '<svg class="chart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+t('Отклик двух каналов за 6 часов, мс','Response of both channels over 6 hours, ms')+'">'+gaps+grid+lab+'<path class="lr" d="'+path(2)+'"/><path class="lp" d="'+path(1)+'"/></svg><div class="legend"><span><i></i>'+t('основной, мс','primary, ms')+'</span><span><i class="r"></i>'+t('резерв, мс','reserve, ms')+'</span>'+(outage?'<span>▮ '+t('провал','outage')+' '+fmtTime(outage).slice(-8,-3)+'</span>':'')+'</div>';
}
function trafficChart(){
  var acc=V.st.accounting||{},days=acc.days||{},wan=(acc.wan||{}).days||{},keys=Object.keys(days).filter(function(k){return /^\d{4}-\d{2}-\d{2}$/.test(k);}).sort().slice(-3);
  if(!keys.length)return '<p class="mute">'+t('Нет данных о трафике.','No traffic data.')+'</p>';
  var gb=function(r){return r&&r.observed!==false&&Number.isFinite(r.rx)?((r.rx||0)+(r.tx||0))/1e9:null;};
  var vals=keys.map(function(k){return [k,gb(days[k]),gb(wan[k])];}),max=Math.max.apply(null,vals.map(function(v){return Math.max(v[1]||0,v[2]||0);}).concat([0.1])),W=320,H=120,sc=(H-34)/max;
  var month=function(m){var s=0,ok=false;Object.keys(days).forEach(function(k){if(k.slice(0,7)===m){var v=gb(days[k]);if(v!=null){s+=v;ok=true;}}});return ok?s:null;};
  var cur=keys[keys.length-1].slice(0,7),f=function(v){return v==null?t('неизвестно','unknown'):(Math.round(v*10)/10).toFixed(1).replace('.',locale==='en'?'.':',')+' '+t('ГБ','GB');};
  return '<svg class="chart mw420" viewBox="0 0 '+W+' '+H+'">'+vals.map(function(r,i){var h=(r[1]||0)*sc,h2=(r[2]||0)*sc;return '<rect class="bar" x="'+(30+i*90)+'" y="'+(H-20-h)+'" width="34" height="'+h+'"/><rect class="bar2" x="'+(66+i*90)+'" y="'+(H-20-h2)+'" width="14" height="'+h2+'"/><text x="'+(32+i*90)+'" y="'+(H-6)+'">'+esc(r[0].slice(8,10)+'.'+r[0].slice(5,7)+' · '+(r[1]==null?'—':f(r[1])))+'</text>';}).join('')+'</svg><div class="legend"><span>▮ VPN</span><span class="cwan">▮ '+t('напрямую через WAN','direct via WAN')+'</span><span>'+t('Этот месяц: ','This month: ')+f(month(cur))+'</span></div>';
}
function switchTimesTable(){
  var eps=episodes().slice(-5).reverse(),s=stats();
  if(!eps.length)return '<p class="mute">'+t('Переключений в сохранённой истории нет.','No switches in the retained history.')+'</p>';
  var sp=fmtSpan,kind={auto:t('Сбой → резерв','Failure → reserve'),manual:t('Ручное','Manual'),test:t('Тест','Test'),unknown:t('Переход','Switch'),recovery:t('Восстановление','Recovery')};
  return '<div class="scrollx"><table class="tbl"><thead><tr><th>'+t('Когда','When')+'</th><th>'+t('Тип','Type')+'</th><th class="num">'+t('Обнаружение','Detection')+'</th><th class="num">'+t('Переключение','Switch')+'</th><th class="num">'+t('На резерве','On reserve')+'</th><th class="num">'+t('Возврат','Return')+'</th></tr></thead><tbody>'+
    eps.map(function(e){return '<tr><td>'+fmtTime(e.time).slice(0,-3)+'</td><td>'+esc(kind[e.kind]||kind.unknown)+'</td><td class="num">'+sp(e.detect)+'</td><td class="num">'+sp(e.switching)+'</td><td class="num">'+sp(e.onReserve)+'</td><td class="num">'+sp(e.returning)+'</td></tr>';}).join('')+
    '</tbody><tfoot><tr><td colspan="2"><b>'+t('Среднее роутера','Router average')+'</b></td><td class="num">'+esc(s.detect)+'</td><td class="num">'+esc(s.swAvg)+'</td><td></td><td class="num">—</td></tr></tfoot></table></div>';
}
function serversHTML(role){
  var p=roleProfile(role),pick=V.st.server_pick,iface=p&&p.interface,tun=pick&&Array.isArray(pick.tunnels)?pick.tunnels.filter(function(x){return x&&x.interface&&x.interface===iface;})[0]:null;
  if(!tun)return '<p class="small mute">'+t('Данных о серверах от роутера пока нет.','No server data from the router yet.')+'</p>';
  var nm=function(c){return c.location?c.location+' ('+c.profile+')':c.profile;};
  var rows=(tun.candidates||[]).map(function(c){var ms=c.alive===true&&Number.isFinite(c.latency_ms)?c.latency_ms+' '+t('мс','ms'):c.alive===false?t('нет ответа','no answer'):t('не измерен','not measured');
    return '<tr><td><i class="lamp '+(c.alive===true?'g':c.alive===false?'r':'n')+'"></i></td><td class="mono">'+esc(nm(c))+'</td><td class="num">'+esc(ms)+'</td><td>'+(c.profile===tun.current?'<span class="chip ok">'+t('текущий','current')+'</span> ':'')+(c.profile===tun.best?'<span class="chip acc">'+t('лучший','best')+'</span>':'')+'</td></tr>';}).join('');
  var ch=tun.last_change;
  return '<table class="tbl"><thead><tr><th></th><th>'+t('Сервер','Server')+'</th><th class="num">'+t('Пинг','Ping')+'</th><th></th></tr></thead><tbody>'+rows+'</tbody></table>'+
    (ch&&Number.isFinite(ch.time)?'<p class="tiny mute">'+t('Последняя смена: ','Last change: ')+esc((ch.from_location||ch.from||'?')+' → '+(ch.to_location||ch.to||'?'))+', '+esc(ch.from_ms)+' → '+esc(ch.to_ms)+' '+t('мс','ms')+' · '+fmtTime(ch.time)+'</p>':'')+
    (pick.enabled?'':'<p class="tiny mute">'+t('Пинг серверов меряется, только когда подбор включён.','Server ping is measured only while the pick is on.')+'</p>')+
    (codeOk(tun.code)?'<p class="tiny"><a class="code" href="#" data-act="code" data-code="'+esc(tun.code)+'">'+esc(tun.code)+'</a></p>':'');
}
var READY_LABELS={'PYTHON-39-MINIMUM':'Python 3.9+','DEPENDENCY-UBUS':'ubus','DEPENDENCY-UCI':'uci','DEPENDENCY-LUA':'Lua','DEPENDENCY-IP':'ip','RPC-PLUGIN':['Модуль rpcd','rpcd plugin'],'CA-BUNDLE':['Сертификаты','Certificates'],'CONFIG-STORAGE-FREE':['Хранилище настроек','Settings storage']};
function readinessHTML(){
  var m=readinessModel(V.st,V.now),v=VER(),b=m.board||{},items=[];
  items.push([v.detected?'g':'y',t('Модель','Model'),v.model+(b.firmware?' · '+t('прошивка GL.iNet ','GL.iNet firmware ')+b.firmware:'')+(v.detected?'':' · '+t('модель не определена роутером','model not detected by the router'))]);
  // tool checks share one row; the worst state wins
  var GROUP=['DEPENDENCY-UBUS','DEPENDENCY-UCI','DEPENDENCY-IP','DEPENDENCY-LUA','RPC-PLUGIN'],rows=[],grp=null;
  (m.checks||[]).forEach(function(c){if(GROUP.indexOf(c.code)>=0){if(!grp){grp={code:'',state:'pass',stale:false,codes:[]};rows.push(grp);}grp.codes.push(c);if(c.state!=='pass'&&grp.state==='pass'||c.state==='fail')grp.state=c.state;grp.stale=grp.stale||!!c.stale;}else rows.push(c);});
  rows.forEach(function(c){var l=READY_LABELS[c.code],name=c.codes?'ubus · uci · ip · Lua · rpcd':Array.isArray(l)?t(l[0],l[1]):l||c.code,bad=c.codes?c.codes.filter(function(x){return x.state!=='pass';}).map(function(x){return x.code;}).join(', '):c.code;
    items.push([c.state==='pass'?(c.stale?'y':'g'):c.state==='fail'?'r':'y',name,(c.state==='pass'?t('есть','present'):c.state==='fail'?t('нет или повреждено','missing or broken'):c.state)+(c.stale&&m.age!=null?' · '+t('отчёт ','report ')+ageText(m.age)+t(' назад',' ago'):''),c.state!=='pass'?bad.split(', ').filter(Boolean):[]]);});
  if(!(m.checks||[]).length)items.push(['n',t('Проверки роутера','Router checks'),t('нет свежих данных','no fresh data')]);
  var prep=(V.st.system_readiness||{}).preparation;
  if(prep&&typeof prep==='object')items.push([prep.state==='ready'||prep.ready===true?'g':'y',t('Подготовка роутера (ускорение)','Router preparation (acceleration)'),prep.ready===true||prep.state==='ready'?t('выполнена, исходные значения сохранены','done, original values saved'):t('требуется при запуске Auto (кнопка Auto выполнит её сама)','needed at Auto start (the Auto button does it itself)')]);
  if(V.s.detected_router_model!=='mt3000')items.push(['y',t('Непрерывный режим на этой модели','Continuous mode on this model'),t('GL-MT6000 ещё не прошёл отдельную приёмку непрерывного Auto; проверено на GL-MT3000 с прошивкой 4.11.0','GL-MT6000 has not yet passed the separate continuous-Auto acceptance; tested on GL-MT3000 with firmware 4.11.0')]);
  // the codes of a failed check open the code window, as everywhere else on the page
  var codeLinks=function(list){return (list||[]).map(function(c){return codeOk(c)?'<a class="code" href="#" data-act="code" data-code="'+esc(c)+'">'+esc(c)+'</a>':esc(c);}).join(' ');};
  return '<ul class="evl">'+items.map(function(i){return '<li class="row nwtop"><i class="lamp '+i[0]+' mt4"></i><div><b>'+esc(i[1])+'</b><div class="small mute">'+esc(i[2])+(i[3]&&i[3].length?' · '+codeLinks(i[3]):'')+'</div></div></li>';}).join('')+'</ul>';
}
function liveLogHTML(){
  var rows=eventRows().slice(0,Math.min(40,Number(V.s.live_log_limit)||40));
  if(!rows.length)return '<div class="log" aria-label="'+t('Живой журнал','Live log')+'">'+esc(t('нет данных','no data'))+'</div>';
  return '<div class="log" aria-label="'+t('Живой журнал','Live log')+'">'+rows.map(function(e){var k=evKind(e);return '<span class="'+(k.lamp==='r'?'e':k.lamp==='y'?'w':'o')+'">'+esc(fmtTime(e.time,true)+' '+(e.state||'')+'  '+evText(e))+'</span>';}).join('\n')+'</div>';
}
function monText(){var m=V.monitor;return m.title+(m.key==='ok'?' · '+t('проверка каждые ','check every ')+(Number(((V.st.probe_policy||{}).effective_interval))||Number(V.s.interval)||10)+' '+t('с','s'):(m.code?' · '+m.code:''));}
function monLamp(){return {green:'g',yellow:'y',red:'r'}[V.monitor.lamp]||'n';}
