/* Auto-adaptation (network advisor) and the master slider «Быстрая реакция ↔ Без лишних переключений» (2.1.0-alpha9,
   docs/architecture/NETWORK-ADVISOR-2026-11-04.ru.md; owner mockup private/math/master-slider). Also the recovery-time
   statistics with the honest P95 and the new sensors (WAN diagnosis, server key pins).
   Single source: every state value is the status field network_advisor (status RPC, each poll); the curve (the anchors of
   the offline study) is the only thing read from rpc advisor, once per page. Changes go through rpc advisor_settings /
   advisor_apply; the router checks every safety rule again and answers with a code. Nothing here starts Auto. */
var ADV={curve:null,load:null,err:null,t:null,fine:null,per:'week'};
var ADV_TOUR_KEY='homensai-vpn-advisor-tour';
var ADV_SAFE={theta:[0.5,0.99,0.01],dur_b:[1,15,0.5],pg:[0.5,0.99,0.01]};
var ADV_STEPS={theta:0.01,dur_b:0.5,losses:1,pg:0.01,primary_stable:5,rescue_stable:1};
function advSt(){var a=V&&V.st&&V.st.network_advisor;return a&&typeof a==='object'&&a.current&&typeof a.current==='object'?a:null;}
function advCurveOk(c){return !!(c&&Array.isArray(c.anchors)&&c.anchors.length>=2&&Array.isArray(c.params)&&Array.isArray(c.metrics)&&c.anchors.every(function(a){return a&&Number.isFinite(a.t)&&Array.isArray(a.p)&&Array.isArray(a.m);})&&
  (c.fast_anchors===undefined||Array.isArray(c.fast_anchors)&&c.fast_anchors.every(function(a){return a&&Number.isFinite(a.t)&&Array.isArray(a.p)&&Array.isArray(a.m);})));}
/* Numbers from the router reach the page's HTML only through these: a finite number inside its safe range, never text. */
function advSafeNum(k,v){var s=ADV_SAFE[k],d=advDefault(),n=typeof v==='number'?v:NaN;if(!Number.isFinite(n))n=d&&d.p&&Number.isFinite(d.p[k])?d.p[k]:s[0];return Math.min(s[1],Math.max(s[0],advStep(n,s[2])));}
function advLoad(){
  if(ADV.curve||ADV.load||ADV.err)return;
  ADV.load=rpcCall('advisor')().then(function(r){if(advCurveOk(r&&r.curve))ADV.curve=r.curve;else ADV.err=r&&codeOk(r.code)?r.code:'ADVISOR-CURVE-INVALID';},function(){ADV.err='ADVISOR-UNAVAILABLE';})
    .then(function(){ADV.load=null;if(HV.root)render();});
}
/* the same interpolation as advisor.interpolate: linear between anchors, every setting rounded to its step */
function advStep(x,s){var v=Math.floor(x/s+0.5)*s;return s>=1?Math.floor(v+0.5):Math.floor(v*100+0.5)/100;}
function advAt(t){
  var c=ADV.curve,A=c.anchors,i=0;
  if(t<-1e-9){  // fast segment: a step (advisor.fast_anchor)
    var q=null,p0={},m0={};(c.fast_anchors||[]).forEach(function(a){if(t<=a.t+1e-9)q=a;});
    if(q){c.params.concat(c.fast_params||[]).forEach(function(k,j){p0[k]=j<q.p.length?q.p[j]:q.x[j-q.p.length];});c.metrics.forEach(function(k,j){m0[k]=q.m[j];});return {t:q.t,p:p0,m:m0};}
    t=0;}
  t=Math.min(1,Math.max(0,t));
  while(i<A.length-2&&A[i+1].t<=t)i++;
  var a=A[i],b=A[i+1],f=(t-a.t)/(b.t-a.t),p={},m={};
  c.params.forEach(function(k,j){p[k]=advStep(a.p[j]+f*(b.p[j]-a.p[j]),(c.steps||ADV_STEPS)[k]||0.01);});
  c.metrics.forEach(function(k,j){var u=a.m[j],v=b.m[j];m[k]=u==null||v==null?null:u+f*(v-u);});
  return {t:Math.floor(t*100+0.5)/100,p:p,m:m};
}
function advDefault(){var c=ADV.curve,a=c&&c.alpha8,p={},m={};if(!a||!Array.isArray(a.p)||!Array.isArray(a.m))return null;c.params.forEach(function(k,j){p[k]=a.p[j];});c.metrics.forEach(function(k,j){m[k]=a.m[j];});return {p:p,m:m};}
function advNum(v,d){if(v==null||!Number.isFinite(Number(v)))return '—';var s=(Math.round(Number(v)*Math.pow(10,d||0))/Math.pow(10,d||0)).toFixed(d||0);return locale==='en'?s:s.replace('.',',');}
function advModeName(m){return {auto:t('Авто','Auto'),advice:t('Совет + «Применить»','Advice + "Apply"'),manual:t('Вручную','Manual')}[m]||m;}
function advWhere(a){var c=a.current;if(c.failure_model==='consecutive')return '<span class="chip">'+t('ползунок не действует','slider inactive')+'</span>';
  if(c.attached&&Number.isFinite(c.slider_t))return '<span class="chip acc">t = '+advNum(c.slider_t,2)+' · '+advZone(c.slider_t)+'</span>';
  if(c.label==='preset')return '<span class="chip warn">'+t('По умолчанию','Default')+'</span>';
  return '<span class="chip vio">'+t('Пользовательская','Custom')+'</span>';}
function advZone(x){return x<0?t('быстрый сегмент','fast segment'):x<0.2?t('быстрая реакция','fast reaction'):x>0.8?t('без лишних переключений','no unnecessary switches'):t('баланс','balance');}
function advReason(o){return o?(locale==='en'?o.reason_en:o.reason_ru)||'':'';}
function advFew(r){return !r||r.state==='no-data'||r.state==='few-data';}

/* ---------- the chart: losses per day against unnecessary switches per day, the slider curve and its point ---------- */
function advChart(tNow,tDraft,small,custom){
  var c=ADV.curve;if(!c)return '<p class="small mute">'+(ADV.err?codeNotice(ADV.err):t('Кривая загружается…','Loading the curve…'))+'</p>';
  var xi=c.metrics.indexOf('unnecessary_per_day'),yi=c.metrics.indexOf('downtime_s_day'),def=advDefault(),pts=c.anchors.map(function(a){return [a.m[xi],a.m[yi]];});
  if(def)pts.push([def.m.unnecessary_per_day,def.m.downtime_s_day]);
  var cc=(advSt()||{}).current||{},FA=(c.fast_anchors||[]).filter(function(a){return a.t>=(cc.turbo?-0.7:cc.fast?-0.2:0)-1e-9;});
  FA.forEach(function(a){pts.push([a.m[xi],a.m[yi]]);});
  pts=pts.filter(function(p){return Number.isFinite(p[0])&&Number.isFinite(p[1]);});
  var x0=Math.min.apply(null,pts.map(function(p){return p[0];})),x1=Math.max.apply(null,pts.map(function(p){return p[0];})),y0=Math.min.apply(null,pts.map(function(p){return p[1];})),y1=Math.max.apply(null,pts.map(function(p){return p[1];}));
  var dx=(x1-x0)||1,dy=(y1-y0)||1;x0=Math.max(0,x0-dx*0.12);x1+=dx*0.12;y0-=dy*0.18;y1+=dy*0.18;
  var W=small?320:640,H=small?190:300,PL=small?36:48,PR=small?10:16,PT=12,PB=small?30:40;
  var X=function(v){return (PL+(v-x0)/(x1-x0)*(W-PL-PR)).toFixed(1);},Y=function(v){return (PT+(y1-v)/(y1-y0)*(H-PT-PB)).toFixed(1);},s='';
  for(var i=0;i<=3;i++){var yv=y0+(y1-y0)*i/3,xv=x0+(x1-x0)*i/3;
    s+='<line class="ax" x1="'+PL+'" x2="'+(W-PR)+'" y1="'+Y(yv)+'" y2="'+Y(yv)+'"/><text x="'+(PL-4)+'" y="'+(Number(Y(yv))+3)+'" text-anchor="end">'+advNum(yv,0)+'</text>';
    s+='<line class="ax" y1="'+PT+'" y2="'+(H-PB)+'" x1="'+X(xv)+'" x2="'+X(xv)+'"/><text x="'+X(xv)+'" y="'+(H-PB+12)+'" text-anchor="middle">'+advNum(xv,2)+'</text>';}
  s+='<text x="'+((PL+W-PR)/2)+'" y="'+(H-4)+'" text-anchor="middle">'+t('лишних переключений в сутки →','unnecessary switches per day →')+'</text>';
  s+='<text transform="translate(10 '+((PT+H-PB)/2)+') rotate(-90)" text-anchor="middle">'+t('простой, с/сутки ↑','downtime, s/day ↑')+'</text>';
  s+='<polyline class="curve" points="'+c.anchors.map(function(a){return X(a.m[xi])+','+Y(a.m[yi]);}).join(' ')+'"/>';
  c.anchors.forEach(function(a){s+='<circle class="anc" cx="'+X(a.m[xi])+'" cy="'+Y(a.m[yi])+'" r="3"/>';});
  FA.forEach(function(a){s+='<circle class="anc fast" cx="'+X(a.m[xi])+'" cy="'+Y(a.m[yi])+'" r="3"/>';});
  var PRO=small?[]:[[0,t('«Быстрая реакция»','"Fast reaction"')],[0.5,t('«Баланс»','"Balance"')],[1,t('«Без лишних»','"No unnecessary"')]].map(function(q){var m=advAt(q[0]).m;return {t:q[0],n:q[1],x:Number(X(m.unnecessary_per_day)),y:Number(Y(m.downtime_s_day))};});
  if(def){var dxp=X(def.m.unnecessary_per_day),dyp=Y(def.m.downtime_s_day);s+='<rect class="mk def" x="'+(dxp-5)+'" y="'+(dyp-5)+'" width="10" height="10" transform="rotate(45 '+dxp+' '+dyp+')"><title>'+t('По умолчанию (alpha8)','Default (alpha8)')+'</title></rect>';PRO.unshift({x:Number(dxp),y:Number(dyp),k:1});}
  PRO.forEach(function(p){if(!p.k)s+='<path class="mk pro" d="M'+p.x+' '+(p.y-12)+'L'+(p.x+5)+' '+(p.y-3)+'L'+(p.x-5)+' '+(p.y-3)+'Z"><title>'+esc(p.n)+' t = '+p.t+'</title></path>';});
  if(!small&&xdU())s+=xdU().chartLabels(PRO,W);  /* the labels are placed without overlaps by the optional module */
  if(Number.isFinite(tNow)){var n=advAt(tNow).m;s+='<circle class="now'+(custom?' custom':'')+'" cx="'+X(n.unnecessary_per_day)+'" cy="'+Y(n.downtime_s_day)+'" r="'+(small?7:9)+'"><title>'+t('Сейчас на роутере','Now on the router')+'</title></circle>';}
  if(Number.isFinite(tDraft)){var d=advAt(tDraft).m;s+='<circle class="halo" cx="'+X(d.unnecessary_per_day)+'" cy="'+Y(d.downtime_s_day)+'" r="13"/><circle class="pt" cx="'+X(d.unnecessary_per_day)+'" cy="'+Y(d.downtime_s_day)+'" r="6"/>';}
  return '<svg class="advchart" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+t('Кривая ползунка: простой в сутки против лишних переключений в сутки; точка — положение','Slider curve: downtime per day against unnecessary switches per day; the dot is the position')+'">'+s+'</svg>';
}
function advLegend(){return '<div class="legend"><span><i class="lg-curve"></i>'+t('кривая ползунка (11 опорных точек)','slider curve (11 anchors)')+'</span><span><i class="lg-now"></i>'+t('сейчас на роутере','now on the router')+'</span><span><i class="lg-pt"></i>'+t('положение ползунка','slider position')+'</span><span><i class="lg-def"></i>'+t('по умолчанию (alpha8)','default (alpha8)')+'</span><span><i class="lg-pro"></i>'+t('готовые положения','named positions')+'</span></div><p class="tiny mute">'+t('Прогноз офлайн-модели (откалиброван по MT3000), не измерения этого роутера. Простой — секунды без интернета в сутки.','Forecast of the offline model (calibrated on the MT3000), not measurements of this router. Downtime is seconds without internet per day.')+'</p>';}
function advExpect(m,approx,p){return '<div class="expect" data-adv="expect"><b>'+t('Ожидаемо','Expected')+(approx?' ≈':'')+':</b> '+t('уход на резерв через ~','switch to the reserve after ~')+'<b>'+advNum(m.switch_after_s,0)+' '+t('с','s')+'</b> · '+t('пережидает обрывы до ~','rides out outages up to ~')+'<b>'+advNum(m.rides_out_s,0)+' '+t('с','s')+'</b> · '+t('лишних переключений ≈ ','unnecessary switches ≈ ')+'<b>'+advNum(m.unnecessary_per_day,2)+'</b> '+t('в сутки','per day')+' · '+t('простой ≈ ','downtime ≈ ')+'<b>'+advNum(m.downtime_s_day,0)+' '+t('с','s')+'</b> '+t('в сутки','per day')+'</div>'+(p&&xdU()?xdU().note(p):'');}

/* ---------- simple view: card «Автоподстройка» (live binding adv.card) ---------- */
function advCardHTML(){
  var a=advSt();
  if(!a)return '<div class="hline"><i class="lamp l n"></i><h2>'+t('Автоподстройка','Auto-adaptation')+'</h2></div><p class="small mute">'+t('Роутер пока не сообщает её состояние (служба мониторинга старой версии или остановлена).','The router does not report its state yet (an older or stopped monitoring service).')+'</p>';
  advLoad();
  var c=a.current,r=a.recommendation,few=advFew(r),off=c.failure_model==='consecutive',lamp=off?'n':few?'y':'g',lc=a.last_change,out='';
  out+='<div class="hline"><i class="lamp l '+lamp+'" role="img" aria-label="'+(lamp==='g'?t('зелёный','green'):lamp==='y'?t('жёлтый','yellow'):t('серый','grey'))+'"></i><h2>'+t('Автоподстройка','Auto-adaptation')+': '+esc(advModeName(a.mode))+'</h2></div>';
  out+='<p class="row small">'+advWhere(a)+'<span class="mute">'+t('окно данных ','data window ')+advNum(a.window_days,0)+' '+t(a.window_days===1?'день':'дней',a.window_days===1?'day':'days')+'</span></p>';
  if(off)out+='<p class="note">'+t('Детектор «ошибки подряд»: ползунок и автоподстройка на него не действуют.','Detector "failures in a row": the slider and the adaptation do not apply to it.')+'</p>';
  else if(few)out+='<p class="note warn">'+esc(advReason(r)||t('Мало данных — действуют текущие настройки.','Not enough data — the current settings stay.'))+'</p>';
  else if(r)out+='<p class="small">'+esc(advReason(r))+'</p>';
  out+='<dl class="kv"><dt>'+t('Последнее изменение','Last change')+'</dt><dd>'+(lc&&Number.isFinite(lc.time)?esc(fmtTime(lc.time,true))+' · '+(lc.to==null?t('свои значения','own values'):'t '+(lc.from==null?'—':advNum(lc.from,2))+' → '+advNum(lc.to,2))+' · '+esc({auto:t('автоматически','automatically'),owner:t('владелец','owner'),'owner-manual':t('владелец, вручную','owner, manual')}[lc.source]||lc.source||'')+'<br><span class="small mute">'+esc(advReason(lc))+'</span>':t('ещё не было','none yet'))+'</dd></dl>';
  if(!off&&ADV.curve){var tn=Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t;out+='<div class="advmini">'+advChart(tn,null,true,!c.attached)+'</div>'+advExpect(advAt(tn).m,!c.attached);}
  else if(!off)out+=advChart(null,null,true);
  out+='<p class="row mt8"><button class="btn sm" data-act="advopen">'+t('Настроить (для эксперта)','Adjust (expert)')+'</button>'+advOfferHTML()+'</p>';
  return out;
}
function advOfferHTML(){return store.get(ADV_TOUR_KEY,null)===null?'<button class="btn sm pri" data-act="advtour" data-i="0">🎓 '+t('Как это работает (5 шагов)','How it works (5 steps)')+'</button><button class="btn sm ghost" data-act="advnotour">'+t('Не сейчас','Not now')+'</button>':'';}

/* ---------- expert settings: section adv (simple view «Для эксперта», console tab Auto) ---------- */
function advCurParams(c){return {theta:c.theta,dur_b:c.dur_b,pg:c.pg,primary_stable:c.primary_stable,rescue_stable:c.rescue_stable};}
function advRows(a,draft,fine){
  var c=a.current,cur=advCurParams(c),def=advDefault()||{p:{},m:{}},tn=Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t,mNow=advAt(tn).m,h='';
  var P=[['theta',t('Порог ухода θ','Leave threshold θ'),'',2,''],
    ['dur_b',t('Длина «короткого обрыва» в модели','Short-outage length of the model'),'',1,' '+t('с','s')],
    ['pg',t('Порог возврата P(здоров)','Return threshold P(healthy)'),'',2,''],
    ['primary_stable',t('Стабильность основного перед возвратом','Primary stability before the return'),'',0,' '+t('с','s')],
    ['rescue_stable',t('Возврат с упавшего резерва через','Return from a failed reserve after'),'',0,' '+t('с','s')]];
  P.forEach(function(d){var v=fine&&fine[d[0]]!=null?fine[d[0]]:draft.p[d[0]],n=cur[d[0]],ch=Number.isFinite(v)&&Number.isFinite(n)&&Math.abs(v-n)>1e-9,ar=ch?(v>n?'↑':'↓'):'';
    var hint=xdU()?xdU().hint(d[0]):'';  // the long explanations load with the expert module (help<N>.js)
    h+='<tr><td>'+esc(d[1])+(hint?'<div class="tiny mute">'+esc(hint)+'</div>':'')+'</td><td class="num'+(ch?' chg':'')+'">'+advNum(v,d[3])+d[4]+(ar?'<span class="ar" aria-label="'+t('изменится','will change')+'">'+ar+'</span>':'')+'</td><td class="num">'+advNum(n,d[3])+d[4]+'</td><td class="num mute">'+advNum(def.p[d[0]],d[3])+d[4]+'</td></tr>';});
  var M=[['switch_after_s',t('Уход после долгого обрыва через','Leaves a long outage after'),0,' '+t('с','s')],['rides_out_s',t('Пережидает обрывы до','Rides out outages up to'),0,' '+t('с','s')],['unnecessary_per_day',t('Лишних переключений в сутки','Unnecessary switches per day'),2,''],['downtime_s_day',t('Простой в сутки','Downtime per day'),0,' '+t('с','s')],['return_after_40s_blackout_s',t('Возврат после обрыва 40 с через','Return after a 40 s outage in'),0,' '+t('с','s')],['reserve_failure_worst_downtime_s',t('Худший случай: упал и резерв (простой)','Worst case: the reserve fails too (downtime)'),0,' '+t('с','s')]];
  M.forEach(function(d){var v=fine?null:draft.m[d[0]],n=mNow[d[0]],ch=v!=null&&n!=null&&Math.abs(v-n)>1e-6;h+='<tr class="sub"><td>'+esc(d[1])+'</td><td class="num'+(ch?' chg':'')+'">'+(fine?'≈':'')+advNum(fine?n:v,d[2])+d[3]+'</td><td class="num">'+advNum(n,d[2])+d[3]+'</td><td class="num mute">'+(def.m[d[0]]==null?'—':advNum(def.m[d[0]],d[2])+d[3])+'</td></tr>';});
  [[t('Быстрое обнаружение: пингов подряд','Fast detection: pings in a row'),'2'],[t('Интервал и частота проверок','Check interval and boost'),t('ползунок «нагрузка ↔ надёжность»','the slider "load ↔ reliability"')],[t('Возврат без уверенности модели','Return without model confidence'),t('после 300 с без ошибок','after 300 s without errors')]].forEach(function(f){h+='<tr class="sub fixed"><td>'+esc(f[0])+'<div class="tiny mute">'+t('не меняется этим ползунком','not changed by this slider')+'</div></td><td class="num" colspan="3">'+esc(f[1])+'</td></tr>';});
  return '<div class="scrollx"><table class="tbl advtbl" data-adv="table"><thead><tr><th>'+t('Переменная','Variable')+'</th><th class="num">'+(fine?t('Свои значения','Own values'):t('Положение ползунка','Slider position'))+'</th><th class="num">'+t('Сейчас на роутере','Now on the router')+'</th><th class="num">'+t('По умолчанию','Default')+'</th></tr></thead><tbody>'+h+'</tbody></table></div><p class="tiny mute">'+t('Жёлтым — что изменится при применении (стрелка — куда). Нижние строки — прогноз модели, серые — не зависят от ползунка.','Yellow: what changes when applied (the arrow shows where). The lower rows are the model forecast, grey rows do not depend on the slider.')+'</p>';
}
function advDraftT(a){var c=a.current;return ADV.t!=null?ADV.t:c.attached&&Number.isFinite(c.slider_t)?c.slider_t:Number.isFinite(c.nearest_t)?c.nearest_t:0.5;}
/* Without the optional module the fast row and the switches are absent: their state stays visible and a failure offers Retry. */
function xdFast(c){var o=function(v){return v?t('вкл','on'):t('выкл','off');};return '<p class="note">'+t('Быстрый сегмент: ','Fast segment: ')+o(c.fast)+' · '+t('Турбо: ','Turbo: ')+o(c.turbo)+(LAZY_HELP.failed?' · '+helpFail():'')+'</p>';}
function advSectionBody(){
  var a=advSt();
  if(!a)return '<p class="small mute">'+t('Роутер пока не сообщает состояние автоподстройки (служба мониторинга старой версии или остановлена). Настройки недоступны.','The router does not report the auto-adaptation state yet (an older or stopped monitoring service). Settings unavailable.')+'</p>';
  advLoad();if(HV.open['sec-adv'])xdLoad();
  var c=a.current,r=a.recommendation,off=c.failure_model==='consecutive',auto=a.mode==='auto',fine=ADV.fine,custom=!!fine||c.label==='custom',out='';
  out+=advOfferHTML()?'<p class="note row">'+t('Новое: ползунок реакции на сбои и автоподстройка.','New: the failure-reaction slider and auto-adaptation.')+' '+advOfferHTML()+'</p>':'';
  out+='<div class="row advhead"><span>'+advWhere(a)+'</span><span class="small mute">'+t('режим: ','mode: ')+esc(advModeName(a.mode))+'</span></div>';
  out+='<div class="advseg" role="group" aria-label="'+t('Режим','Mode')+'">'+['auto','advice','manual'].map(function(m){return '<button class="btn sm" data-act="advmode" data-m="'+m+'" aria-pressed="'+(a.mode===m)+'">'+esc(advModeName(m))+(m==='auto'?' <span class="tiny">'+t('(система двигает сама)','(the system moves it)')+'</span>':'')+'</button>';}).join('')+'</div>';
  out+='<div class="advseg" role="group" aria-label="'+t('Окно данных','Data window')+'"><span class="small mute">'+t('Окно данных:','Data window:')+'</span>'+[1,7,30].map(function(w){return '<button class="btn sm" data-act="advwin" data-w="'+w+'" aria-pressed="'+(a.window_days===w)+'">'+w+' '+t(w===1?'день':'дней',w===1?'day':'days')+'</button>';}).join('')+'</div>';
  if(off)out+='<p class="note warn">'+t('Детектор сбоя — «ошибки подряд»: ползунок на него не действует. Выберите детектор HMM в «Эксперт: детектор сбоя», чтобы пользоваться ползунком.','The failure detector is "failures in a row": the slider does not apply to it. Choose the HMM detector in "Expert: failure detector" to use the slider.')+' <a class="code" href="#" data-act="code" data-code="ADVISOR-MODEL-CONSECUTIVE">ADVISOR-MODEL-CONSECUTIVE</a></p>';
  else if(advFew(r))out+='<p class="note warn">'+t('Мало данных: ','Not enough data: ')+esc(advReason(r)||t('расчёт ещё не выполнялся (ночью в 03:30).','no calculation yet (nightly at 03:30).'))+'</p>';
  else if(r&&r.state==='shift'&&!auto)out+='<p class="note">'+t('Совет: ','Advice: ')+esc(advReason(r))+' <button class="btn sm pri" data-act="advrec">'+t('Применить','Apply')+' t = '+advNum(r.t,2)+'</button></p>';
  else if(r)out+='<p class="note">'+(auto?t('Автоматически: ','Automatically: '):'')+esc(advReason(r))+'</p>';
  if(auto&&!off)out+='<p class="small mute">'+t('«Авто»: ползунок двигает система — не больше 0,1 в сутки, при ≥ 5 событиях и экономии ≥ 5 %. Двигать самому — «Вручную» или «Совет».','Auto: the system moves the slider — at most 0.1 a day, with ≥ 5 events and a saving ≥ 5 %. To move it yourself: Manual or Advice.')+'</p>';
  var td=advDraftT(a),draft=ADV.curve?advAt(td):null,dis=auto||off||custom;
  out+='<div class="advslider"><div class="ends"><span>'+t('Быстрая реакция','Fast reaction')+'</span><span>'+t('Без лишних переключений','No unnecessary switches')+'</span></div>'+
    '<input class="slider" type="range" id="adv-t" min="0" max="1" step="0.01" value="'+Math.max(0,td)+'" aria-label="'+t('Быстрая реакция — без лишних переключений','Fast reaction — no unnecessary switches')+'"'+(dis||!ADV.curve?' disabled':'')+'>'+
    '<div class="ticks"><span>0</span><span>'+advNum(0.25,2)+'</span><span>'+advNum(0.5,1)+'</span><span>'+advNum(0.75,2)+'</span><span>1</span></div>'+
    '<p class="row"><output data-adv="tval">t = '+advNum(td,2)+' · '+esc(advZone(td))+'</output>'+(!dis&&ADV.curve?'<button class="btn sm pri" data-act="advapply"'+(c.attached&&Math.abs(td-c.slider_t)<0.005?' disabled':'')+'>'+t('Применить положение','Apply the position')+'</button>':'')+(ADV.t!=null?'<button class="btn sm ghost" data-act="advreset">'+t('Вернуть как на роутере','Back to the router value')+'</button>':'')+'</p>'+(xdU()?xdU().fastRow(c,dis,td):xdFast(c))+
    (custom?'<p class="note warn">'+t('Ползунок отвязан: значения заданы вручную («Пользовательская»).','The slider is detached: values set by hand ("Custom").')+' <button class="btn sm" data-act="advrebind">'+t('Привязать к ползунку','Attach to the slider')+' (t = '+advNum(c.nearest_t,2)+')</button></p>':'')+'</div>';
  if(xdU()&&!off)out+=xdU().fastAdmin(c);
  if(draft){out+='<div data-adv="expectbox">'+advExpect(fine?advAt(c.nearest_t).m:draft.m,!!fine||custom,fine?null:draft.p)+'</div><div class="advchartbox" data-adv="chart">'+advChart(Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t,custom?null:td,false,custom)+'</div>'+advLegend();}
  else out+=advChart(null,null,false);
  if(draft)out+='<h3>'+t('Все переменные','All variables')+'</h3><div data-adv="tablebox">'+advRows(a,draft,fine)+'</div>';
  out+='<div class="row mt8"><button class="tgl" role="switch" data-act="advfine" aria-checked="'+(!!fine)+'"'+(off||!ADV.curve?' disabled':'')+'><span class="trk"></span>'+t('Тонкая настройка','Fine tuning')+'</button></div>'+(fine?advFineHTML(c):'');
  out+=more('advSafe',t('Правила безопасности (роутер проверяет при каждом изменении; код — объяснение)','Safety rules (checked by the router at every change; the code explains)'),'<ul class="small">'+[['ADVISOR-OUT-OF-BOUNDS',t('θ и P(G) 0,50–0,99; «короткий обрыв» 1–15 с; стабильность 30–600 с; возврат после отказа резерва 0–60 с','θ and P(G) 0.50–0.99; short outage 1–15 s; stability 30–600 s; return after a failed reserve 0–60 s')],['ADVISOR-PG-BELOW-THETA',t('P(G) не ниже θ','P(G) not below θ')],['ADVISOR-RIDE-NOT-BELOW-LEAVE',t('пережидаемый обрыв короче времени ухода','the ridden-out outage is shorter than the leave time')],['ADVISOR-RESCUE-ABOVE-STABLE',t('возврат после отказа резерва не дольше стабильности основного','the rescue return is not longer than the primary stability')],['ADVISOR-BUSY-SWITCH',t('ничего не меняется во время обрыва или переключения; Auto не включается','nothing changes during an outage or a switch; Auto is not started')]].map(function(r){return '<li>'+esc(r[1])+' <a class="code" href="#" data-act="code" data-code="'+r[0]+'">'+r[0]+'</a></li>';}).join('')+'</ul>');
  if(a.last_change)out+='<p class="small mute">'+t('Последнее изменение: ','Last change: ')+esc(fmtTime(a.last_change.time,true))+' · '+esc(advReason(a.last_change))+'</p>';
  return out;
}
function advFineHTML(c){
  var f=ADV.fine,rows=[['theta',t('Порог ухода θ','Leave threshold θ'),2],['dur_b',t('Длина «короткого обрыва»','Short-outage length'),1],['pg',t('Порог возврата P(G)','Return threshold P(G)'),2]];
  var note=xdU()?xdU().hint('fine'):'';
  return '<div class="advfine">'+(note?'<p class="note">'+esc(note)+'</p>':'')+
    rows.map(function(r){var s=ADV_SAFE[r[0]];return '<div class="fine"><label for="advf-'+r[0]+'">'+esc(r[1])+'</label><output data-adv="o-'+r[0]+'">'+advNum(f[r[0]],r[2])+(r[0]==='dur_b'?' '+t('с','s'):'')+'</output><input class="slider" type="range" id="advf-'+r[0]+'" data-advf="'+r[0]+'" min="'+s[0]+'" max="'+s[1]+'" step="'+s[2]+'" value="'+esc(String(advSafeNum(r[0],f[r[0]])))+'"><div class="h">'+advNum(s[0],r[2])+'–'+advNum(s[1],r[2])+'</div></div>';}).join('')+
    '<p class="small" data-adv="finewhy">'+esc(ADV.fineWhy||'')+'</p><div class="savebar"><button class="btn pri sm" data-act="advsave">'+t('Сохранить свои значения','Save own values')+'</button><button class="btn sm ghost" data-act="advfine">'+t('Отменить','Discard')+'</button></div></div>';
}
/* dragging: only the parts that depend on the position are repainted (point, expectation, table, value) */
function advPaint(){
  var a=advSt();if(!a||!ADV.curve||!HV.root)return;var c=a.current,td=advDraftT(a),d=advAt(td),custom=!!ADV.fine||c.label==='custom';
  var set=function(k,h){$$('[data-adv="'+k+'"]',HV.root).forEach(function(el){el.innerHTML=h;});};
  set('chart',advChart(Number.isFinite(c.t_ref)?c.t_ref:c.nearest_t,custom?null:td,false,custom));
  set('expectbox',advExpect(ADV.fine?advAt(c.nearest_t).m:d.m,custom,ADV.fine?null:d.p));set('tablebox',advRows(a,d,ADV.fine));set('tval','t = '+advNum(td,2)+' · '+esc(advZone(td)));
  if(ADV.fine){['theta','dur_b','pg'].forEach(function(k){set('o-'+k,advNum(ADV.fine[k],k==='dur_b'?1:2)+(k==='dur_b'?' '+t('с','s'):''));var i=$('#advf-'+k,HV.root);if(i&&Number(i.value)!==ADV.fine[k])i.value=ADV.fine[k];});set('finewhy',esc(ADV.fineWhy||''));}
  var ap=$('[data-act="advapply"]',HV.root);if(ap)ap.disabled=c.attached&&Math.abs(td-c.slider_t)<0.005;
}
function advInput(el){
  if(el.id==='adv-ack'){var g=$('#adv-ackgo',HV.root),u=xdU();if(g&&u)g.disabled=!u.ackOk(el.value);return true;}
  if(el.id==='adv-t'){ADV.t=Math.round(Number(el.value)*100)/100;advPaint();return true;}
  var k=el.dataset&&el.dataset.advf;if(!k||!ADV.fine)return false;
  var s=ADV_SAFE[k],v=Math.min(s[1],Math.max(s[0],advStep(Number(el.value),s[2])));ADV.fine[k]=v;ADV.fineWhy='';
  // safety in the page as on the router: P(G) never below θ
  if(k==='theta'&&ADV.fine.pg<v){ADV.fine.pg=v;ADV.fineWhy=t('P(G) поднят до θ: возврат не может требовать меньше уверенности, чем уход.','P(G) raised to θ: the return cannot need less confidence than leaving.');}
  if(k==='pg'&&v<ADV.fine.theta){ADV.fine.pg=ADV.fine.theta;ADV.fineWhy=t('P(G) не ниже θ (правило безопасности).','P(G) not below θ (safety rule).');}
  advPaint();return true;
}
/* p is a function that sends the request: the busy lock is taken first, so a second press sends nothing. */
function advRpc(p,ok){
  if(HV.busy.adv)return;HV.busy.adv=true;
  var sent;try{sent=Promise.resolve(typeof p==='function'?p():p);}catch(e){sent=Promise.reject(e);}
  return sent.then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};toast(ok);ADV.t=null;ADV.fine=null;return refreshNow();})
    .catch(function(e){failModal(t('Не применено','Not applied'),e&&codeOk(e.code)?e.code:'ADVISOR-APPLY-UNCONFIRMED');})
    .finally(function(){HV.busy.adv=false;render();});
}
function advClick(act,a){
  var s=advSt();
  if(act==='advopen'){go(function(){HV.open['sec-adv']=true;if(HV.view==='console')HV.tab='auto';else HV.page='settings';});setHash();return;}
  if(act==='advtour'){advTour(Number(a.dataset.i)||0);return;}
  if(act==='advnotour'){store.set(ADV_TOUR_KEY,'later');render();toast(t('Обучение есть в «Помощь и обучение».','The training is in "Help and training".'));return;}
  if(!s)return;var c=s.current;
  if(act==='advmode'){var m=a.dataset.m;if(m===s.mode)return;return advRpc(function(){return rpcCall('advisor_settings',['mode','window'])(m,s.window_days);},t('Режим сохранён: ','Mode saved: ')+advModeName(m));}
  if(act==='advwin'){var w=Number(a.dataset.w);if(w===s.window_days)return;return advRpc(function(){return rpcCall('advisor_settings',['mode','window'])(s.mode,w);},t('Окно данных сохранено. Пересчёт — в течение 10 минут.','Data window saved. Recalculated within 10 minutes.'));}
  if(act==='advrec')return advRpc(function(){return rpcCall('advisor_apply')();},t('Совет применён. Роутер подтвердил.','Advice applied. Confirmed by the router.'));
  if(act==='advapply')return advRpc(function(){return rpcCall('advisor_apply',['t'])(advDraftT(s));},t('Положение применено. Роутер подтвердил.','Position applied. Confirmed by the router.'));
  if(act==='advrebind')return advRpc(function(){return rpcCall('advisor_apply',['t'])(c.nearest_t);},t('Значения снова на ползунке.','Values are on the slider again.'));
  if(act==='advreset'){ADV.t=null;render();return;}
  if(act==='advpos'){ADV.t=Number(a.dataset.t);render();return;}
  if(/^adv(lock|fast|turbo)/.test(act)){var u=xdU();if(u)u.act(act,a,s);return;}
  if(act==='advfine'){ADV.fine=ADV.fine?null:{theta:advSafeNum('theta',c.theta),dur_b:advSafeNum('dur_b',c.dur_b),pg:advSafeNum('pg',c.pg)};ADV.fineWhy='';render();return;}
  if(act==='advsave'){var f=ADV.fine;if(!f)return;if(f.pg<f.theta){failModal(t('Не сохранено','Not saved'),'ADVISOR-PG-BELOW-THETA');return;}
    return advRpc(function(){return rpcCall('advisor_settings',['mode','window','theta','dur_b','pg'])('manual',s.window_days,f.theta,f.dur_b,f.pg);},t('Свои значения сохранены. Роутер подтвердил.','Own values saved. Confirmed by the router.'));}
}

/* ---------- training: 5 steps, offered once, reachable from help ---------- */
function advTour(i){
  store.set(ADV_TOUR_KEY,'seen');
  // the texts live in the optional help module (help<N>.js) like the other training; the curve of step 2 is live
  helpApi().then(function(){xdU().tour(i);}).catch(function(){failModal(t('Обучение','Training'),'UI-HELP-LOAD-FAILED');});
}

/* ---------- recovery time with the honest P95 (rules of scripts/honest_stats.py, analytics_panel.inc.js) ---------- */
function recStatsHTML(){
  var u=xdU();if(!u){xdLoad();return '<p class="small mute">'+(LAZY_HELP.failed?helpFail():t('Загрузка…','Loading…'))+'</p>';}
  var h=V.st.native_history||{},rows=[],s=null,w=null;
  try{rows=retainedTransitions(h).filter(function(r){return !recoveryPreparation(r);});w=recoveryWindow(ADV.per,V.now,h.timezone||'Europe/Berlin');s=recoverySummary(rows,w.start,w.end);}
  catch(e){return '<p class="small mute">'+codeNotice('RECOVERY-TIMEZONE-UNKNOWN')+'</p>';}
  return u.recoveryStats(s);
}

/* ---------- new sensors: WAN diagnosis and server key pins ---------- */
function sensorWan(){
  var w=V.st.wan_diagnosis;
  if(!w||typeof w!=='object')return {lamp:'n',text:t('WAN-диагностика: нет данных (старая служба мониторинга)','WAN diagnosis: no data (older monitoring service)'),code:null};
  // A diagnosis is a reading only while it is fresh. An old or missing one is not "all fine": grey, with its age.
  if(!observationFresh(w,V.now))return {lamp:'n',text:t('WAN-диагностика: нет свежих данных','WAN diagnosis: no fresh data')+(Number.isFinite(w.time)?' · '+t('последний диагноз ','last diagnosis ')+ageText(V.now-w.time)+t(' назад',' ago'):''),code:null};
  if(w.code==='WAN-DOWN')return {lamp:'r',text:t('Нет интернета у провайдера (WAN) — VPN тут ни при чём. Auto не переключает каналы, пока WAN не вернётся','No internet from the provider (WAN) — not a VPN problem. Auto does not switch channels until the WAN is back')+(Number.isFinite(w.down_since)?' · '+t('с ','since ')+fmtTime(w.down_since):''),code:'WAN-DOWN'};
  if(w.code==='WAN-RECOVERING')return {lamp:'y',text:t('Интернет провайдера вернулся; Auto ждёт, пока основной канал подтвердит связь, прежде чем решать','The provider internet is back; Auto waits for the primary channel to confirm before deciding'),code:'WAN-RECOVERING'};
  if(w.enabled===false)return {lamp:'n',text:t('WAN-диагностика выключена (option wan_sensor)','WAN diagnosis is off (option wan_sensor)'),code:null};
  if(codeOk(w.code))return {lamp:'y',text:t('Диагноз: ','Diagnosis: ')+(errorRow(w.code)?t(errorRow(w.code)[3],errorRow(w.code)[2]):w.code)+(Number.isFinite(w.confidence)?' · '+t('уверенность ','confidence ')+Math.round(w.confidence/10)+' %':''),code:w.code};
  // Green needs proof that the provider internet works (the underlay probe or the router's own WAN state), not the absence of a fault.
  var ev=w.evidence||{};
  if(ev.underlay==='ok'||ev.kmwan==='online')return {lamp:'g',text:t('WAN в порядке: интернет провайдера есть','WAN is fine: the provider internet works'),code:null};
  return {lamp:'n',text:t('WAN: датчики не подтвердили интернет провайдера (признаков сбоя нет, но и доказательства нет)','WAN: the sensors did not confirm the provider internet (no sign of a fault, but no proof either)'),code:null};
}
function sensorKeys(){var k=V.st.server_keys;return k&&typeof k==='object'?k:null;}
function sensorsHTML(){
  var w=sensorWan(),k=sensorKeys(),out='<p class="row small"><i class="lamp '+w.lamp+'"></i><span>'+esc(w.text)+(w.code?' <a class="code" href="#" data-act="code" data-code="'+esc(w.code)+'">'+esc(w.code)+'</a>':'')+'</span></p>';
  if(!k)out+='<p class="row small"><i class="lamp n"></i><span>'+t('Ключи серверов: нет данных','Server keys: no data')+'</span></p>';
  else if(k.mode==='off')out+='<p class="row small"><i class="lamp n"></i><span>'+t('Проверка ключей серверов выключена (server_key_pin off)','Server key check is off (server_key_pin off)')+'</span></p>';
  else{var ch=Array.isArray(k.changed)?k.changed:[],checked=Array.isArray(k.changed)&&Number(k.pinned)>0;
    // an empty list proves a match only when something is remembered to compare with
    out+='<p class="row small"><i class="lamp '+(ch.length?'r':checked?'g':'n')+'"></i><span>'+(ch.length?t('Ключ сервера изменился: ','Server key changed: ')+ch.length:checked?t('Ключи серверов совпадают с запомненными','Server keys match the remembered ones'):t('Ключи серверов: пока нечего сравнивать (ничего не запомнено)','Server keys: nothing to compare yet (none remembered)'))+' · '+t('запомнено ','remembered ')+(Number(k.pinned)||0)+' · '+t('режим ','mode ')+esc(k.mode)+(ch.length?' <a class="code" href="#" data-act="code" data-code="SERVER-KEY-CHANGED">SERVER-KEY-CHANGED</a>':'')+'</span></p>';
    ch.forEach(function(r){var p=((HV.inv||{}).profiles||[]).filter(function(x){return x.id===r.profile;})[0];
      out+='<div class="keychg"><b>'+esc(p?profileName(p):r.profile)+'</b> · '+esc(r.host)+(Number.isFinite(r.changed_at)?' · '+esc(fmtTime(r.changed_at,true)):'')+'<dl class="kv small"><dt>'+t('Был','Was')+'</dt><dd class="mono">'+esc(r.pinned)+'</dd><dt>'+t('Сейчас','Now')+'</dt><dd class="mono">'+esc(r.observed)+'</dd></dl><button class="btn sm" data-act="keyaccept" data-profile="'+esc(r.profile)+'" data-observed="'+esc(r.observed)+'">'+t('Принять новый ключ','Accept the new key')+'</button></div>';});}
  return out;
}
function sensorBanner(){
  var w=sensorWan(),k=sensorKeys(),out='';
  if(w.code==='WAN-DOWN'||w.code==='WAN-RECOVERING')out+='<p class="note '+(w.lamp==='r'?'bad':'warn')+' warnbar">'+esc(w.text)+' <a class="code" href="#" data-act="code" data-code="'+w.code+'">'+w.code+'</a></p>';
  if(k&&Array.isArray(k.changed)&&k.changed.length)out+='<p class="note bad warnbar">'+t('Ключ VPN-сервера изменился — проверьте его у провайдера. ','A VPN server key changed — check it with the provider. ')+'<a class="code" href="#" data-act="code" data-code="SERVER-KEY-CHANGED">SERVER-KEY-CHANGED</a> · <a href="#" data-act="gokeys">'+t('подробнее','details')+'</a></p>';
  return out;
}
function keyAccept(a){
  var profile=a.dataset.profile,observed=a.dataset.observed;
  modal({title:t('Принять новый ключ сервера?','Accept the new server key?'),body:'<p>'+t('Сменившийся ключ бывает при ротации ключей провайдером, но так же выглядит подменённый сервер. Принимайте только после сверки с провайдером (список серверов или заново скачанный конфиг).','A changed key happens when the provider rotates keys, but a substituted server looks the same. Accept only after checking it with the provider (server list or a freshly downloaded config).')+'</p><p class="mono small">'+esc(observed)+'</p>',
    buttons:[{t:t('Отмена','Cancel')},{t:t('Ключ сверен — принять','Key checked — accept'),cls:'pri',fn:function(){
      rpcCall('server_key_accept',['profile','observed'])(profile,observed).then(function(r){if(!(r&&r.queued===true))throw {code:r&&r.code};toast(t('Принято. Монитор применит при следующей проверке.','Accepted. The monitor applies it at its next check.'));refreshSoon();})
        .catch(function(e){failModal(t('Ключ не принят','Key not accepted'),e&&codeOk(e.code)?e.code:'SERVER-KEY-NOT-CHANGED');});}}]});
}
