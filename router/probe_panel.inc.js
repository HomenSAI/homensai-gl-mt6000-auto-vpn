// Probe level 1-5 (router load vs. failure detection) and the automatic boost, under the Auto card.
// Values come from the router's own probe_policy; the page never derives a cadence itself.
var PROBE_RPC='homensai-vpn',PROBE_LEVELS={1:[60,300],2:[30,120],3:[20,60],4:[15,45],5:[10,30]},PROBE_DRAFT=null,PROBE_BUSY=false,PROBE_LOG_OPEN=false;
function probeLevelText(level,boost){
  var v=PROBE_LEVELS[level]||PROBE_LEVELS[5],detect=v[0]*3,fast=v[0]+20;
  var names={1:bi('Economy','Экономно'),2:bi('Light','Лёгкий'),3:bi('Balanced','Сбалансировано'),4:bi('Reliable','Надёжно'),5:bi('Maximum reliability','Максимальная надёжность')};
  return names[level]+' · '+bi('channel check every '+v[0]+' s, ping and websites every '+v[1]+' s. A failure is confirmed in about '+(boost?fast:detect)+' s','проверка каналов раз в '+v[0]+' с, пинг и сайты раз в '+v[1]+' с. Сбой подтверждается примерно за '+(boost?fast:detect)+' с')+(boost&&fast<detect?bi(' (without boost '+detect+' s).',' (без ускорения '+detect+' с).'):'.');
}
function probeDecision(row){
  var level=bi('level ','уровень ')+row.level,cadence=bi('check every ','проверка раз в ')+row.interval+bi(' s, ping/websites every ',' с, пинг/сайты раз в ')+row.measure_interval+bi(' s',' с');
  var role=row.role==='source'?bi('primary channel','основной канал'):row.role==='target'?bi('reserve channel','резервный канал'):bi('channel','канал');
  if(row.kind==='level')return [bi('Level ','Выбран уровень ')+row.level,cadence+'; '+(row.boost_enabled?bi('boost on','ускорение включено'):bi('boost off','ускорение выключено'))];
  if(row.kind==='boost-start')return [bi('Boost started','Ускорение включено'),role+bi(' failed a check; checks every ',' не прошёл проверку; проверка раз в ')+row.boost_interval+bi(' s for 10 min (',' с на 10 мин (')+level+')'];
  var results={'switched':bi('Boost ended: the channel was switched','Ускорение завершено: было переключение'),'failure-confirmed':bi('Boost ended: failure confirmed','Ускорение завершено: сбой подтверждён'),'false-alarm':bi('Boost ended: false alarm, the channel recovered','Ускорение завершено: ложная тревога, канал восстановился'),'disabled':bi('Boost turned off by the owner','Ускорение выключено владельцем')};
  return [results[row.result]||row.result,role+'; '+row.failures+bi(' failed checks in ',' неудачных проверок за ')+Math.round((row.duration||0)/60)+bi(' min; back to ',' мин; возврат на ')+level];
}
function renderProbeLog(host){
  var call=rpc.declare({object:PROBE_RPC,reject:true,method:'statistics',params:['kind','after','until'],expect:{}});
  host.textContent=bi('Loading…','Загрузка…');
  return call('probe',0,0).then(function(page){
    var rows=(page&&page.events||[]).slice().reverse();
    if(!rows.length){host.textContent=bi('No decisions recorded yet.','Решений пока не записано.');return;}
    var clock=function(t){return new Date(t*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'});};
    host.textContent='';host.appendChild(E('table',{'class':'table hv-probe-log'},[E('tr',{},[bi('Time','Время'),bi('Level','Уровень'),bi('Decision','Решение'),bi('Reason','Обоснование'),bi('Code','Код')].map(function(h){return E('th',{},h);}))].concat(rows.map(function(row){
      var d=probeDecision(row),code=typeof safeCode==='function'&&safeCode(row.code)?row.code:null;
      return E('tr',{'data-probe-kind':row.kind},[E('td',{},clock(row.time)),E('td',{},String(row.level)),E('td',{},d[0]),E('td',{},d[1]),E('td',{},code?(typeof errorCodeLink==='function'?errorCodeLink(code):code):'—')]);
    }))));
  }).catch(function(){host.textContent='PROBE-HISTORY-UNAVAILABLE';});
}
function renderProbeControl(status,inventory){
  var policy=status.probe_policy||{},settings=inventory.settings||{};
  if(!Number.isInteger(policy.level))return null;
  var saved={level:policy.level,boost:policy.boost_enabled!==false},draft=PROBE_DRAFT||saved;
  var slider=E('input',{'type':'range','min':'1','max':'5','step':'1','value':String(draft.level),'class':'hv-probe-slider','aria-label':bi('Probe level','Уровень опроса')});
  var box=E('input',{'type':'checkbox','class':'hv-probe-boost'});box.checked=draft.boost;
  var text=E('p',{'class':'hv-probe-text','role':'status'},probeLevelText(draft.level,draft.boost));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':(PROBE_BUSY||draft.level===saved.level&&draft.boost===saved.boost)?'':null},bi('Apply','Применить'));
  function change(){PROBE_DRAFT={level:Number(slider.value),boost:box.checked};text.textContent=probeLevelText(PROBE_DRAFT.level,PROBE_DRAFT.boost);
    if(PROBE_DRAFT.level===saved.level&&PROBE_DRAFT.boost===saved.boost){PROBE_DRAFT=null;apply.setAttribute('disabled','');}else apply.removeAttribute('disabled');}
  slider.addEventListener('input',change);box.addEventListener('change',change);
  apply.addEventListener('click',function(){
    if(PROBE_BUSY||!PROBE_DRAFT)return;PROBE_BUSY=true;apply.setAttribute('disabled','');
    rpc.declare({object:PROBE_RPC,reject:true,method:'setup_probe',params:['level','boost'],expect:{}})(PROBE_DRAFT.level,PROBE_DRAFT.boost).then(function(result){
      if(result&&result.saved){PROBE_DRAFT=null;ui.addNotification(null,E('p',{},bi('Probe level saved. The router applies it on its next check.','Уровень опроса сохранён. Роутер применит его со следующей проверки.')));}
      else ui.addNotification(null,E('p',{},(result&&result.code)||'SETUP-SAVE-FAILED'));
    }).catch(function(){ui.addNotification(null,E('p',{},'SETUP-SAVE-UNCONFIRMED'));}).finally(function(){PROBE_BUSY=false;});
  });
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,active=null;
  if(policy.boost_active&&Number.isFinite(policy.boost_until)){
    var trigger=policy.boost_trigger||{},left=Math.max(0,Math.round((policy.boost_until-now)/60));
    active=E('p',{'class':'hv-probe-active','role':'status'},[bi('Boost is active: checks every 10 s for about ','Ускорение сейчас включено: проверка раз в 10 с ещё примерно ')+left+bi(' min · ',' мин · ')+(trigger.role==='source'?bi('primary channel','основной канал'):trigger.role==='target'?bi('reserve channel','резервный канал'):bi('channel','канал'))+' · ',typeof safeCode==='function'&&safeCode(trigger.code)&&typeof errorCodeLink==='function'?errorCodeLink(trigger.code):(trigger.code||'')]);
  }
  var logHost=E('div',{'class':'hv-probe-log-host'});
  var log=E('details',{'class':'hv-probe-log-details','open':PROBE_LOG_OPEN?'':null},[E('summary',{},bi('Decision log: levels and boost','Журнал решений: уровни и ускорение')),logHost]);
  log.addEventListener('toggle',function(){PROBE_LOG_OPEN=log.open;if(log.open)renderProbeLog(logHost);});
  if(PROBE_LOG_OPEN)renderProbeLog(logHost);
  return E('section',{'class':'hv-chart-card hv-probe-control','data-probe-level':String(policy.level)},[
    E('h3',{},bi('Probe level: router load ↔ reliability','Уровень опроса: нагрузка ↔ надёжность')),
    E('div',{'class':'hv-probe-scale'},[E('span',{},bi('Fewer checks, lower load','Меньше опросов, ниже нагрузка')),slider,E('span',{},bi('More checks, faster switching','Больше опросов, быстрее переключение'))]),
    text,
    E('label',{'class':'hv-probe-boost-label'},[box,' ',E('strong',{},bi('Automatic boost','Автоматическое ускорение'))]),
    E('p',{'class':'hv-step-note'},bi('If the primary or reserve channel fails a check, the router checks every 10 s for 10 minutes to confirm the failure quickly or see that it was a one-off. After 10 minutes without failures it returns to the chosen level. A reliable pair is then checked rarely and a real failure is still caught fast. Every episode and its result are written to the log below.','Если основной или резервный канал не прошёл проверку, роутер на 10 минут переходит на проверку раз в 10 с: быстро подтверждает сбой или убеждается, что это случайность. Через 10 минут без сбоев возвращается к выбранному уровню. Так надёжные каналы проверяются редко, а настоящий сбой всё равно замечается быстро. Каждый эпизод и его итог записываются в журнал ниже.')),
    active,E('p',{'class':'hv-req-actions'},[apply]),log].filter(Boolean));
}
