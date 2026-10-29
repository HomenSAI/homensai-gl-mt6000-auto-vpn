// Probe level 1-5 (router load vs. failure detection) and the automatic boost, under the Auto card.
// Values come from the router's own probe_policy; the page never derives a cadence itself.
var PROBE_APPLIED=null,PROBE_LOG_KEY='homensai-vpn-probe-log-open',PROBE_LOG_ROWS=null,PROBE_RPC='homensai-vpn',PROBE_LEVELS={1:[60,300],2:[30,120],3:[20,60],4:[15,45],5:[10,30]},PROBE_DRAFT=null,PROBE_BUSY=false,PROBE_LOG_OPEN=false;
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
function drawProbeLog(host,rows){
  if(!rows.length){host.textContent=bi('No decisions recorded yet.','Решений пока не записано.');return;}
  var clock=function(t){return new Date(t*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{timeZone:'Europe/Berlin'});};
  host.textContent='';host.appendChild(E('table',{'class':'table hv-probe-log'},[E('tr',{},[bi('Time','Время'),bi('Level','Уровень'),bi('Decision','Решение'),bi('Reason','Обоснование'),bi('Code','Код')].map(function(h){return E('th',{},h);}))].concat(rows.map(function(row){
    var d=probeDecision(row),code=typeof safeCode==='function'&&safeCode(row.code)?row.code:null;
    return E('tr',{'data-probe-kind':row.kind},[E('td',{},clock(row.time)),E('td',{},String(row.level)),E('td',{},d[0]),E('td',{},d[1]),E('td',{'class':'hv-probe-code'},code?(typeof errorCodeLink==='function'?errorCodeLink(code):code):'—')]);
  }))));
}
function renderProbeLog(host){
  // Rows already read stay on screen; the refresh runs in the background (no "Loading…" flash on every poll).
  if(PROBE_LOG_ROWS)drawProbeLog(host,PROBE_LOG_ROWS);else host.textContent=bi('Loading…','Загрузка…');
  var call=rpc.declare({object:PROBE_RPC,reject:true,method:'statistics',params:['kind','after','until'],expect:{}});
  return call('probe',0,0).then(function(page){
    var rows=(page&&page.events||[]).slice().reverse(),same=PROBE_LOG_ROWS&&JSON.stringify(rows)===JSON.stringify(PROBE_LOG_ROWS);
    PROBE_LOG_ROWS=rows;if(!same)drawProbeLog(host,rows);
  }).catch(function(){if(!PROBE_LOG_ROWS)host.textContent='PROBE-HISTORY-UNAVAILABLE';});
}
// One stable control: built once, updated in place on every poll. A re-created slider lost the owner's drag
// and applied a stale value (the "jump to the right"). The owner's choice always wins on screen: while a
// draft or an applied-but-not-yet-published choice exists, the router's published level never moves the knob.
var PROBE_SECTION=null;
function probeSavedChoice(policy){
  var saved={level:policy.level,boost:policy.boost_enabled!==false};
  if(PROBE_APPLIED&&(policy.level===PROBE_APPLIED.level&&saved.boost===PROBE_APPLIED.boost||Date.now()-PROBE_APPLIED.at>180000))PROBE_APPLIED=null;
  return PROBE_APPLIED?{level:PROBE_APPLIED.level,boost:PROBE_APPLIED.boost}:saved;
}
function probeBoostActiveText(policy,now){
  if(!policy.boost_active||!Number.isFinite(policy.boost_until))return '';
  var trigger=policy.boost_trigger||{},left=Math.max(0,Math.round((policy.boost_until-now)/60));
  return bi('Boost is active: checks every 10 s for about ','Ускорение включено: проверка раз в 10 с ещё примерно ')+left+bi(' min · ',' мин · ')+(trigger.role==='source'?bi('primary channel','основной канал'):trigger.role==='target'?bi('reserve channel','резервный канал'):bi('channel','канал'))+(trigger.code?' · '+trigger.code:'');
}
function renderProbeControl(status,inventory){
  var policy=status.probe_policy||{};
  if(!Number.isInteger(policy.level))return PROBE_SECTION;
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  if(PROBE_SECTION){PROBE_SECTION.hvUpdate(policy,now);return PROBE_SECTION;}
  var saved=probeSavedChoice(policy),draft=PROBE_DRAFT||saved,dragging=false;
  var slider=E('input',{'type':'range','min':'1','max':'5','step':'1','value':String(draft.level),'class':'hv-probe-slider','list':'hv-probe-ticks','aria-label':bi('Probe level','Уровень опроса')});
  var ticks=E('div',{'class':'hv-probe-ticks','aria-hidden':'true'},[1,2,3,4,5].map(function(n){return E('span',{'data-level':String(n)},String(n));}));
  var levelLabel=E('strong',{'class':'hv-probe-level-label'},bi('Level ','Уровень ')+draft.level);
  var box=E('input',{'type':'checkbox','class':'hv-probe-boost'});box.checked=draft.boost;
  var text=E('p',{'class':'hv-probe-text','role':'status'},probeLevelText(draft.level,draft.boost));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action'},bi('Apply','Применить'));
  var active=E('p',{'class':'hv-probe-active','role':'status'},probeBoostActiveText(policy,now));
  function paint(){
    var shown=PROBE_DRAFT||saved;
    if(!dragging)slider.value=String(shown.level);
    box.checked=shown.boost;levelLabel.textContent=bi('Level ','Уровень ')+shown.level;text.textContent=probeLevelText(shown.level,shown.boost);
    for(var i=0;i<ticks.children.length;i++){var t=ticks.children[i];if(t.classList&&t.getAttribute)t.classList.toggle('hv-probe-tick-current',Number(t.getAttribute('data-level'))===shown.level);}
    var same=shown.level===saved.level&&shown.boost===saved.boost;
    if(PROBE_BUSY||same)apply.setAttribute('disabled','');else apply.removeAttribute('disabled');
  }
  function change(){PROBE_DRAFT={level:Number(slider.value),boost:box.checked};if(PROBE_DRAFT.level===saved.level&&PROBE_DRAFT.boost===saved.boost)PROBE_DRAFT=null;paint();}
  slider.addEventListener('input',change);slider.addEventListener('change',change);box.addEventListener('change',change);
  slider.addEventListener('pointerdown',function(){dragging=true;});slider.addEventListener('pointerup',function(){dragging=false;});
  slider.addEventListener('mousedown',function(){dragging=true;});slider.addEventListener('mouseup',function(){dragging=false;});
  slider.addEventListener('touchstart',function(){dragging=true;});slider.addEventListener('touchend',function(){dragging=false;});
  apply.addEventListener('click',function(){
    var choice={level:Number(slider.value),boost:box.checked};  // what the owner sees, read at the click
    if(PROBE_BUSY||choice.level===saved.level&&choice.boost===saved.boost)return;PROBE_BUSY=true;apply.setAttribute('disabled','');
    rpc.declare({object:PROBE_RPC,reject:true,method:'setup_probe',params:['level','boost'],expect:{}})(choice.level,choice.boost).then(function(result){
      if(result&&result.saved){PROBE_APPLIED={level:choice.level,boost:choice.boost,at:Date.now()};PROBE_DRAFT=null;saved=choice;probeCheckSchedule(null);
        ui.addNotification(null,E('p',{},bi('Level ','Уровень ')+choice.level+bi(' saved. The router applies it now.',' сохранён. Роутер применяет его сразу.')));}
      else ui.addNotification(null,E('p',{},(result&&result.code)||'SETUP-SAVE-FAILED'));
    }).catch(function(){ui.addNotification(null,E('p',{},'SETUP-SAVE-UNCONFIRMED'));}).finally(function(){PROBE_BUSY=false;paint();});
  });
  if(PROBE_LOG_OPEN===false){try{PROBE_LOG_OPEN=window.localStorage.getItem(PROBE_LOG_KEY)==='1';}catch(e){}}
  var logHost=E('div',{'class':'hv-probe-log-host'});
  var log=E('details',{'class':'hv-probe-log-details','open':PROBE_LOG_OPEN?'':null},[E('summary',{},bi('Decision log: levels and boost','Журнал решений: уровни и ускорение')),logHost]);
  log.addEventListener('toggle',function(){PROBE_LOG_OPEN=log.open;try{window.localStorage.setItem(PROBE_LOG_KEY,log.open?'1':'0');}catch(e){}if(log.open)renderProbeLog(logHost);});
  if(PROBE_LOG_OPEN)renderProbeLog(logHost);
  var section=E('section',{'class':'hv-chart-card hv-probe-control','data-probe-level':String(policy.level)},[
    E('h3',{},bi('Probe level: router load ↔ reliability','Уровень опроса: нагрузка ↔ надёжность')),
    E('div',{'class':'hv-probe-scale'},[E('span',{},bi('Fewer checks, lower load','Меньше опросов, ниже нагрузка')),E('div',{'class':'hv-probe-slider-box'},[slider,ticks]),E('span',{},bi('More checks, faster switching','Больше опросов, быстрее переключение'))]),
    E('p',{'class':'hv-probe-text-row'},[levelLabel,' · ',text]),
    E('label',{'class':'hv-probe-boost-label'},[box,' ',E('strong',{},bi('Automatic boost','Автоматическое ускорение'))]),
    E('p',{'class':'hv-step-note'},bi('If a channel fails a check, the router checks every 10 s for 10 minutes, then returns to the chosen level. Rare checks at rest, a quick answer when something breaks. Every episode is written to the log below.','Если канал не прошёл проверку, роутер 10 минут проверяет раз в 10 с, затем возвращается к выбранному уровню. В покое проверок мало, при сбое ответ быстрый. Каждый эпизод записывается в журнал ниже.')),
    active,E('p',{'class':'hv-req-actions'},[apply]),log]);
  section.hvUpdate=function(policyNow,nowSeconds){
    saved=probeSavedChoice(policyNow);section.setAttribute('data-probe-level',String(policyNow.level));
    active.textContent=probeBoostActiveText(policyNow,nowSeconds);active.hidden=!active.textContent;
    if(log.open&&!PROBE_BUSY)renderProbeLog(logHost);
    paint();
  };
  active.hidden=!active.textContent;paint();
  PROBE_SECTION=section;return section;
}

// Countdown to the router's next scheduled channel check, and the yellow "checking" pulse on the traffic
// light: yellow one second before the scheduled check, through the check, until one second after the
// router's answer for that check has arrived. The base colour (green/red) then returns.
var PROBE_TICK=null,PROBE_SCHEDULE={deadline:null,interval:null,lastStatus:null,pulseUntil:0};
function probeCheckSchedule(status){
  if(!status){PROBE_SCHEDULE.deadline=null;return;}
  var p=status.probe_policy||{},interval=p.effective_interval;
  if(!Number.isFinite(interval)||interval<=0||!Number.isFinite(status.time))return;
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  if(PROBE_APPLIED&&PROBE_LEVELS[PROBE_APPLIED.level]&&p.boost_active!==true){interval=PROBE_LEVELS[PROBE_APPLIED.level][0];}
  var deadline=Date.now()+(status.time+interval-now)*1000;
  // A check we were waiting for has answered: keep yellow one more second, then the base colour.
  if(PROBE_SCHEDULE.lastStatus!==null&&status.time>PROBE_SCHEDULE.lastStatus&&PROBE_SCHEDULE.pulseUntil===Infinity)PROBE_SCHEDULE.pulseUntil=Date.now()+1000;
  PROBE_SCHEDULE.lastStatus=status.time;PROBE_SCHEDULE.interval=interval;PROBE_SCHEDULE.deadline=deadline;PROBE_SCHEDULE.boost=p.boost_active===true;
}
function probeCheckPulse(){
  var s=PROBE_SCHEDULE,nowMs=Date.now();
  if(!Number.isFinite(s.deadline))return false;
  if(nowMs>=s.deadline-1000&&s.pulseUntil!==Infinity&&nowMs<s.deadline+1000)s.pulseUntil=Infinity;  // checking: until the answer arrives
  if(s.pulseUntil===Infinity&&nowMs>s.deadline+30000)s.pulseUntil=nowMs;  // no answer for 30 s: the light logic takes over (late data)
  return s.pulseUntil===Infinity||nowMs<s.pulseUntil;
}
function probePaintPulse(){
  if(typeof document==='undefined'||!document.querySelectorAll)return;
  var on=probeCheckPulse(),housings=document.querySelectorAll('.hv-light-three[data-signal="green"]');
  for(var i=0;i<housings.length;i++){var lamps=housings[i].querySelectorAll('.hv-lamp');for(var j=0;j<lamps.length;j++){var l=lamps[j];
    if(l.classList.contains('hv-lamp-green'))l.classList.toggle('hv-lamp-lit',!on);if(l.classList.contains('hv-lamp-yellow'))l.classList.toggle('hv-lamp-lit',on);}}
  var knobs=document.querySelectorAll('.hv-side-lamp-link .hv-auto-pill-knob.hv-lamp-on,.hv-side-lamp-link .hv-auto-pill-knob.hv-lamp-pulse');
  for(var k=0;k<knobs.length;k++){knobs[k].classList.toggle('hv-lamp-switching',on);knobs[k].classList.toggle('hv-lamp-pulse',on);if(!on)knobs[k].classList.add('hv-lamp-on');else knobs[k].classList.remove('hv-lamp-on');}
}
function probeCountdownText(node){
  var s=PROBE_SCHEDULE;if(!Number.isFinite(s.deadline)){node.textContent='';return;}
  var period=s.interval*1000,late=Date.now()-s.deadline;
  if(late>=1000&&period>0&&s.pulseUntil!==Infinity)s.deadline+=Math.ceil(late/period)*period;
  var left=Math.round((s.deadline-Date.now())/1000);
  node.textContent=(probeCheckPulse()?bi('Checking','Проверка'):bi('Check in ','Проверка через ')+Math.max(0,left)+bi(' s',' с'))+(s.boost?bi(' · boost',' · ускорение'):'');
}
function probeCountdown(status){
  probeCheckSchedule(status);
  if(!Number.isFinite(PROBE_SCHEDULE.deadline))return null;
  var node=E('small',{'class':'hv-probe-countdown','role':'timer','aria-live':'off'},'');
  probeCountdownText(node);
  if(!PROBE_TICK&&typeof window!=='undefined'&&window.setInterval&&typeof document!=='undefined'&&document.querySelectorAll)
    PROBE_TICK=window.setInterval(function(){var nodes=document.querySelectorAll('.hv-probe-countdown');for(var i=0;i<nodes.length;i++)probeCountdownText(nodes[i]);probePaintPulse();},500);
  return node;
}

// Settings: what the "response" numbers measure. Ping is the default (light, compares channels);
// three websites over HTTPS are closer to opening real pages but cost the router more work.
var RESPONSE_CHOICES=[['icmp-1.1.1.1','Ping 1.1.1.1 (Cloudflare DNS) — recommended','Пинг 1.1.1.1 (Cloudflare DNS) — рекомендуется'],['icmp-8.8.8.8','Ping 8.8.8.8 (Google DNS)','Пинг 8.8.8.8 (Google DNS)'],['icmp-9.9.9.9','Ping 9.9.9.9 (Quad9)','Пинг 9.9.9.9 (Quad9)'],['websites','Three websites over HTTPS (Google, Cloudflare, Wikipedia)','Три сайта по HTTPS (Google, Cloudflare, Wikipedia)']];
function responseSettings(inventory){
  var current=((inventory||{}).settings||{}).response_metric||'icmp-1.1.1.1',chosen=current,busy=false;
  var save=E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':''},bi('Save','Сохранить'));
  var list=E('div',{'class':'hv-response-choices'},RESPONSE_CHOICES.map(function(c){
    var input=E('input',{'type':'radio','name':'hv-response-metric','value':c[0]});input.checked=c[0]===current;
    input.addEventListener('change',function(){chosen=c[0];if(chosen===current)save.setAttribute('disabled','');else save.removeAttribute('disabled');});
    return E('label',{'class':'hv-response-choice'},[input,' ',bi(c[1],c[2])]);}));
  save.addEventListener('click',function(){
    if(busy||chosen===current)return;busy=true;save.setAttribute('disabled','');
    rpc.declare({object:PROBE_RPC,reject:true,method:'setup_response',params:['metric'],expect:{}})(chosen).then(function(r){
      if(r&&r.saved){current=chosen;ui.addNotification(null,E('p',{},bi('Saved. The router uses it from its next check.','Сохранено. Роутер применит со следующей проверки.')));}
      else ui.addNotification(null,E('p',{},(r&&r.code)||'SETUP-SAVE-FAILED'));
    }).catch(function(){ui.addNotification(null,E('p',{},'SETUP-SAVE-UNCONFIRMED'));}).finally(function(){busy=false;if(chosen!==current)save.removeAttribute('disabled');});
  });
  return E('section',{'class':'hv-chart-card hv-response-settings'},[E('h3',{},bi('How the response is measured','Как измеряется отклик')),
    E('p',{'class':'hv-step-note'},bi('Ping is a short echo through each VPN to a public DNS address. It shows which channel is faster, gives small numbers and barely loads the router; recommended. Three websites over HTTPS measure opening real pages (DNS, connection, encryption, headers); the numbers are closer to what you feel but larger, and each check costs the router three encrypted connections per channel. The response is information only: Auto decides on its own health checks either way.','Пинг — короткий запрос через каждый VPN к публичному DNS-адресу. Он показывает, какой канал быстрее, даёт небольшие числа и почти не нагружает роутер; рекомендуется. Три сайта по HTTPS измеряют открытие настоящих страниц (DNS, соединение, шифрование, заголовки): числа ближе к ощущениям, но больше, и каждая проверка стоит роутеру трёх зашифрованных соединений на канал. Отклик — только информация: Auto в любом случае решает по своим проверкам исправности.')),
    list,E('p',{'class':'hv-req-actions'},[save])]);
}
