/* HomenS.AI Auto VPN page — shared core of the approved mockups (private/ui-variants-2026-11-03/_src/core.js), wired to
   the router. Markup, classes and wording follow the mockup; every reading comes from the router status through ONE
   snapshot (snap) built from the legacy display logic (simpleHomeModel, profileHealth, pingReading, autoLightModel,
   manualControlModel, ...), so all views show the same truth. Nothing here accepts terms or starts Auto by itself. */
var $=function(s,r){return (r||document).querySelector(s);},$$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s));};
var store={get:function(k,d){try{var v=window.localStorage.getItem(k);return v===null?d:v;}catch(e){return d;}},set:function(k,v){try{window.localStorage.setItem(k,v);}catch(e){}}};
var LANG_KEY='homensai-vpn-language',THEME_KEY='homensai-vpn-theme',VIEW_KEY='homensai-vpn-view';
function t(ru,en){return locale==='en'?(en===undefined?ru:en):ru;}
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
var NODATA=function(){return t('нет данных','no data');};
var HV={inv:{settings:{},profiles:[],servers:[]},st:{},root:null,view:'simple',page:'home',tab:'ch',wiz:false,step:1,open:{},dirty:{},draft:null,
  filters:{a:'all',d:'all'},all:false,evOpen:{},probeRows:null,speedRun:null,scan:null,busy:{},theme:'system',codeQ:''};
var V=null;  // the one snapshot of readings for the current paint

/* ---------------- Versions and identity (attribution on every view) ---------------- */
function VER(){
  var st=HV.st||{},s=(HV.inv||{}).settings||{};
  var okv=function(v){return typeof v==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(v);};
  var model=s.detected_router_model==='mt3000'?'GL.iNet GL-MT3000 · Beryl AX':s.detected_router_model==='mt6000'?'GL.iNet GL-MT6000 · Flint 2':'GL.iNet GL-MT6000 · Flint 2 / GL-MT3000 · Beryl AX';
  return {app:okv(st.version)?st.version:HV_AGENT,pkg:okv(st.package)?st.package:NODATA(),page:HV_BUILD,style:HV_STYLE,model:model,
    detected:s.detected_router_model==='mt3000'||s.detected_router_model==='mt6000',terms:TERMS_VERSION,mismatch:okv(st.version)&&st.version!==HV_AGENT};
}

/* ---------------- Router calls (the same RPCs and arguments as before) ---------------- */
function rpcCall(method,params){return rpc.declare({object:'homensai-vpn',reject:true,method:method,params:params||[],expect:{}});}
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
  var p=roleProfile(role),key=role==='primary'?'source':'target';
  if(!p)return {lamp:'n',state:'none',text:t('канал не выбран','channel not chosen'),ms:null,ageText:t('выберите пару в Настройках','choose the pair in Settings'),why:''};
  var h=profileHealth(p,V.now).state,tone=manualChannelTone(p,key,V.path,V.now,V.runs,V.st);
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
function selectedRole(){var r=V.d.selectedRole;return r==='source'?'primary':r==='target'?'reserve':null;}
function autoOn(){return V.control.on||V.light.key==='ok'||V.light.key==='reserve';}
function autoState(){
  var op=V.op,l=V.light;
  if(op==='starting')return {lamp:'y',text:t('Включение Auto…','Turning Auto on…'),sub:t('ждём подтверждения роутера','waiting for the router to confirm')};
  if(op==='stopping')return {lamp:'y',text:t('Выключение Auto…','Turning Auto off…'),sub:t('роутер возвращает обычный режим','the router restores normal mode')};
  if(op==='unconfirmed')return {lamp:'y',text:t('Команда Auto не подтверждена','Auto command not confirmed'),sub:t('нажмите, чтобы выключить','press to turn it off')};
  if(V.control.paused)return {lamp:'y',text:t('Auto на паузе для теста скорости','Auto paused for a speed test'),sub:t('продолжит сам после замера','resumes by itself after the test')};
  if(V.d.dataUnavailable&&!V.d.enabled)return {lamp:'n',text:t('Нет свежих данных об Auto','No fresh Auto data'),sub:l.title};
  if(l.key==='ok'||l.key==='reserve')return {lamp:'g',text:t('Auto включён','Auto is on'),sub:t('следит за каналами и переключит сам','watches both channels and switches by itself')};
  if(l.key==='switching')return {lamp:'y',text:l.title,sub:l.hint||''};
  if(l.key==='problem')return {lamp:'r',text:l.title,sub:(l.hint||'')+(codeOk(l.code)?' · '+l.code:'')};
  if(l.key==='unknown')return {lamp:l.stale?'y':'n',text:l.title,sub:l.hint||''};
  // rescue-tune 03.11.2026: Auto off and a pair tunnel down - the tunnels are brought up by Auto (legacy autoLightModel hint)
  if(l.code==='TUNNEL-DISCONNECTED'&&l.hint)return {lamp:'n',text:t('Auto выключен','Auto is off'),sub:l.hint+' · '+l.code};
  return {lamp:'n',text:t('Auto выключен','Auto is off'),sub:V.terms?t('при сбое переключать будет некому','nobody will switch on a failure'):t('нужно принять условия при включении','terms must be accepted when turning on')};
}
function overall(){
  var d=V.d,sr=selectedRole(),auto=autoOn();
  if(d.dataUnavailable&&(d.connectionLost||!observationFresh(V.st,V.now)))return {lamp:'n',title:t('Нет свежих данных','No fresh data'),sub:d.connectionLost?t('Нет связи с роутером. Проверьте подключение и обновите страницу.','No connection to the router. Check the connection and reload the page.'):t('Роутер давно не присылал измерений, состояние каналов неизвестно. Нажмите «Проверить сейчас».','The router has not sent measurements for a while; channel state is unknown. Press "Check now".')};
  if(d.dataUnavailable)return {lamp:'n',title:d.title,sub:d.summary};
  if(d.moving)return {lamp:'y',title:t('Переключение…','Switching…'),sub:d.summary};
  if(d.state==='setup')return {lamp:'n',title:d.title,sub:d.summary};
  var a=sr?reading(sr):null,o=sr?reading(sr==='primary'?'reserve':'primary'):null;
  if(!sr)return {lamp:d.state==='error'?'r':d.state==='on'?'g':'y',title:d.title,sub:d.summary};
  if(a.state==='ok'&&sr==='primary')return {lamp:'g',title:t('VPN работает','VPN works'),sub:t('Трафик идёт через основной канал','Traffic uses the primary channel')+(auto?'':t(' · Auto выключен',' · Auto is off'))};
  if(a.state==='ok'){var back=auto&&V.s.recovery_return_policy!=='hold_reserve';
    return {lamp:'y',title:t('Работает резерв','Reserve in use'),sub:o.state==='ok'?t('Основной снова здоров — '+(back?'Auto вернёт трафик по правилам.':'вернуть можно вручную.'),'Primary is healthy again — '+(back?'Auto will return by the rules.':'return manually.')):t('Основной не отвечает. Интернет есть через резерв.','Primary is not responding. Internet goes through the reserve.')};}
  if(a.state==='checking'||a.state==='stale')return {lamp:'y',title:d.title,sub:d.summary};
  if(o.state==='ok')return {lamp:'r',title:t('Текущий канал не отвечает','Current channel is not responding'),sub:auto?t('Auto переключит на '+roleName(sr==='primary'?'reserve':'primary').toLowerCase()+' после '+(Number(V.s.recovery_failures)||3)+' неудачных проверок.','Auto will switch after '+(Number(V.s.recovery_failures)||3)+' failed checks.'):t('Auto выключен. Включите Auto или переключитесь вручную.','Auto is off. Turn Auto on or switch manually.')};
  return {lamp:'r',title:t('Нет интернета через VPN','No internet through the VPN'),sub:t('Оба канала не отвечают. Откройте «Помощь → У меня пропал интернет».','Both channels fail. Open "Help → I have no internet".')};
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
    return '<li><div class="ev-h" data-act="evx" data-k="'+esc(evKey(e))+'" role="button" tabindex="0" aria-expanded="'+(op(e,i)?'true':'false')+'"><span class="tm">'+fmtTime(e.time)+'</span><i class="lamp '+k.lamp+'" style="margin-top:4px"></i><span class="tx">'+esc(evText(e))+(code?' <a class="code" href="#" data-act="code" data-code="'+esc(code)+'">'+esc(code)+'</a>':'')+'</span></div><div class="ev-why"'+(op(e,i)?'':' hidden')+'>'+t('Почему: ','Why: ')+esc(evWhy(e))+'</div></li>';}).join('')+'</ul>';
}
function filtersHTML(cur,id){return '<div class="filters" role="group" data-filters="'+id+'">'+[['all',t('Все','All')],['switch',t('Переходы','Switches')],['problem',t('Проблемы','Problems')],['mine',t('Мои действия','My actions')]].map(function(f){return '<button data-act="filter" data-f="'+f[0]+'" data-id="'+id+'" aria-pressed="'+(cur===f[0])+'">'+f[1]+'</button>';}).join('')+'</div>';}

/* ---------------- Statistics from the router's own records ---------------- */
function routeSegments(){var r=((V.st.accounting||{}).reliability||{}).route_history||{};return Array.isArray(r.segments)?r.segments:[];}
function sumKinds(kinds,from,to){var s=0;routeSegments().forEach(function(g){if(kinds.indexOf(g.kind)<0||!Number.isFinite(g.start))return;var a=Math.max(g.start,from),b=Math.min(Number.isFinite(g.end)?g.end:to,to);if(b>a)s+=b-a;});return s;}
function episodes(){try{return switchTimeline(eventRows().slice().reverse());}catch(e){return [];}}
function stats(){
  var now=V.now,from=now-86400,eps=episodes().filter(function(e){return e.kind!=='recovery';});
  var up=sumKinds(['source','target'],from,now),known=sumKinds(['source','target','switching','down','blocked'],from,now);
  var det=eps.map(function(e){return e.detect;}).filter(Number.isFinite),avg=function(a){return a.length?a.reduce(function(x,y){return x+y;},0)/a.length:null;};
  var timing=V.st.switch_timing||{},sw24=eps.filter(function(e){return Number.isFinite(e.reserve)&&e.reserve>=from;}).length;
  var onRes=sumKinds(['target'],from,now),num=function(x){return String(x).replace('.',locale==='en'?'.':',');};
  return {avail24:known>0?num((Math.floor(up/known*1000)/10).toFixed(1))+' %':NODATA(),sw24:V.d.dataUnavailable&&!eps.length?NODATA():String(sw24),
    swAvg:Number.isFinite(timing.avg_seconds)?fmtSpan(timing.avg_seconds):NODATA(),detect:avg(det)!=null?fmtSpan(avg(det)):NODATA(),
    onRes:routeSegments().length?ageText(onRes):NODATA(),eps:eps};
}
function statsTiles(){var s=stats();return '<div class="tiles"><div class="tile"><b>'+esc(s.avail24)+'</b><span>'+t('доступность за 24 ч','availability 24 h')+'</span></div><div class="tile"><b>'+esc(s.sw24)+'</b><span>'+t('переходов за 24 ч','switches 24 h')+'</span></div><div class="tile"><b>'+esc(s.swAvg)+'</b><span>'+t('среднее переключение','avg switch time')+'</span></div><div class="tile"><b>'+esc(s.detect)+'</b><span>'+t('обнаружение сбоя','failure detection')+'</span></div><div class="tile"><b>'+esc(s.onRes)+'</b><span>'+t('на резерве за 24 ч','on reserve 24 h')+'</span></div></div>';}
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
  var acc=V.st.accounting||{},days=acc.days||{},wan=(acc.wan||{}).days||{},keys=Object.keys(days).sort().slice(-3);
  if(!keys.length)return '<p class="mute">'+t('Нет данных о трафике.','No traffic data.')+'</p>';
  var gb=function(r){return r&&r.observed!==false&&Number.isFinite(r.rx)?((r.rx||0)+(r.tx||0))/1e9:null;};
  var vals=keys.map(function(k){return [k,gb(days[k]),gb(wan[k])];}),max=Math.max.apply(null,vals.map(function(v){return Math.max(v[1]||0,v[2]||0);}).concat([0.1])),W=320,H=120,sc=(H-34)/max;
  var month=function(m){var s=0,ok=false;Object.keys(days).forEach(function(k){if(k.slice(0,7)===m){var v=gb(days[k]);if(v!=null){s+=v;ok=true;}}});return ok?s:null;};
  var cur=keys[keys.length-1].slice(0,7),f=function(v){return v==null?t('неизвестно','unknown'):(Math.round(v*10)/10).toFixed(1).replace('.',locale==='en'?'.':',')+' '+t('ГБ','GB');};
  return '<svg class="chart" viewBox="0 0 '+W+' '+H+'" style="max-width:420px">'+vals.map(function(r,i){var h=(r[1]||0)*sc,h2=(r[2]||0)*sc;return '<rect class="bar" x="'+(30+i*90)+'" y="'+(H-20-h)+'" width="34" height="'+h+'"/><rect class="bar2" x="'+(66+i*90)+'" y="'+(H-20-h2)+'" width="14" height="'+h2+'"/><text x="'+(32+i*90)+'" y="'+(H-6)+'">'+r[0].slice(8,10)+'.'+r[0].slice(5,7)+' · '+(r[1]==null?'—':f(r[1]))+'</text>';}).join('')+'</svg><div class="legend"><span>▮ VPN</span><span style="color:#8e5bd8">▮ '+t('напрямую через WAN','direct via WAN')+'</span><span>'+t('Этот месяц: ','This month: ')+f(month(cur))+'</span></div>';
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
  // As in the mockup: the tool checks share one row (ubus · uci · ip · Lua · rpcd); the worst state wins.
  var GROUP=['DEPENDENCY-UBUS','DEPENDENCY-UCI','DEPENDENCY-IP','DEPENDENCY-LUA','RPC-PLUGIN'],rows=[],grp=null;
  (m.checks||[]).forEach(function(c){if(GROUP.indexOf(c.code)>=0){if(!grp){grp={code:'',state:'pass',stale:false,codes:[]};rows.push(grp);}grp.codes.push(c);if(c.state!=='pass'&&grp.state==='pass'||c.state==='fail')grp.state=c.state;grp.stale=grp.stale||!!c.stale;}else rows.push(c);});
  rows.forEach(function(c){var l=READY_LABELS[c.code],name=c.codes?'ubus · uci · ip · Lua · rpcd':Array.isArray(l)?t(l[0],l[1]):l||c.code,bad=c.codes?c.codes.filter(function(x){return x.state!=='pass';}).map(function(x){return x.code;}).join(', '):c.code;
    items.push([c.state==='pass'?(c.stale?'y':'g'):c.state==='fail'?'r':'y',name,(c.state==='pass'?t('есть','present'):c.state==='fail'?t('нет или повреждено','missing or broken'):c.state)+(c.stale&&m.age!=null?' · '+t('отчёт ','report ')+ageText(m.age)+t(' назад',' ago'):'')+(c.state!=='pass'?' · '+bad:'')]);});
  if(!(m.checks||[]).length)items.push(['n',t('Проверки роутера','Router checks'),t('нет свежих данных','no fresh data')]);
  var prep=(V.st.system_readiness||{}).preparation;
  if(prep&&typeof prep==='object')items.push([prep.state==='ready'||prep.ready===true?'g':'y',t('Подготовка роутера (ускорение)','Router preparation (acceleration)'),prep.ready===true||prep.state==='ready'?t('выполнена, исходные значения сохранены','done, original values saved'):t('требуется при запуске Auto (кнопка Auto выполнит её сама)','needed at Auto start (the Auto button does it itself)')]);
  if(V.s.detected_router_model!=='mt3000')items.push(['y',t('Непрерывный режим на этой модели','Continuous mode on this model'),t('GL-MT6000 ещё не прошёл отдельную приёмку непрерывного Auto; проверено на GL-MT3000 с прошивкой 4.11.0','GL-MT6000 has not yet passed the separate continuous-Auto acceptance; tested on GL-MT3000 with firmware 4.11.0')]);
  return '<ul class="evl">'+items.map(function(i){return '<li class="row" style="flex-wrap:nowrap;align-items:flex-start"><i class="lamp '+i[0]+'" style="margin-top:4px"></i><div><b>'+esc(i[1])+'</b><div class="small mute">'+esc(i[2])+'</div></div></li>';}).join('')+'</ul>';
}
function liveLogHTML(){
  var rows=eventRows().slice(0,Math.min(40,Number(V.s.live_log_limit)||40));
  if(!rows.length)return '<div class="log" aria-label="'+t('Живой журнал','Live log')+'">'+esc(t('нет данных','no data'))+'</div>';
  return '<div class="log" aria-label="'+t('Живой журнал','Live log')+'">'+rows.map(function(e){var k=evKind(e);return '<span class="'+(k.lamp==='r'?'e':k.lamp==='y'?'w':'o')+'">'+esc(fmtTime(e.time,true)+' '+(e.state||'')+'  '+evText(e))+'</span>';}).join('\n')+'</div>';
}
function monText(){var m=V.monitor;return m.title+(m.key==='ok'?' · '+t('проверка каждые ','check every ')+(Number(((V.st.probe_policy||{}).effective_interval))||Number(V.s.interval)||10)+' '+t('с','s'):(m.code?' · '+m.code:''));}
function monLamp(){return {green:'g',yellow:'y',red:'r'}[V.monitor.lamp]||'n';}
