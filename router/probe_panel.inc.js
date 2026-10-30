var PROBE_FORCED_BOOST=[1,2];  // probe_policy.FORCED_BOOST_LEVELS
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
  if(row.kind==='suspicion-start'||row.kind==='suspicion-end'){
    // Passive suspicion (probe_policy.Booster.suspect): only dense full checks, never a switch by itself.
    var ev=row.evidence||{},why={'rx-stall':bi('sends data but receives nothing','отправляет данные, но ничего не получает')+(ev.stalled_s!=null?bi(' for '+Math.round(ev.stalled_s)+' s',' '+Math.round(ev.stalled_s)+' с'):''),
      'wg-handshake-stale':bi('WireGuard handshake is older than 3 min while sending','рукопожатие WireGuard старше 3 мин при отправке данных'),
      'link-missing':bi('the tunnel interface disappeared','интерфейс туннеля пропал')}[row.reason]||String(row.reason||'');
    if(row.kind==='suspicion-start')return [bi('Suspicion: dense checks','Подозрение: частые проверки'),role+' '+why+bi('; full checks every ','; полные проверки раз в ')+row.dense_interval+bi(' s. A suspicion alone never switches.',' с. Одно подозрение никогда не переключает.')];
    var ended={'false-alarm':bi('Suspicion cleared: checks passed','Подозрение снято: проверки пройдены'),'failure-confirmed':bi('Suspicion confirmed by failed checks','Подозрение подтверждено неудачными проверками'),'switched':bi('Suspicion ended: Auto switched','Подозрение завершено: Auto переключил канал'),'expired':bi('Suspicion ended without confirmation','Подозрение завершено без подтверждения'),'cancelled':bi('Suspicion ended: Auto is not watching','Подозрение завершено: Auto не наблюдает')};
    return [ended[row.result]||row.result,role+'; '+(row.failures||0)+bi(' failed of ',' неудачных из ')+(row.checks||0)+bi(' checks in ',' проверок за ')+(row.duration||0)+bi(' s; back to ',' с; возврат на ')+level];
  }
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
var PROBE_LOG_AT=0;
function renderProbeLog(host){
  PROBE_LOG_AT=Date.now();
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
  var forcedNote=E('p',{'class':'hv-probe-forced','role':'note'},bi('Levels 1 and 2 always use the boost: a rare check alone cannot confirm a short failure in time.','На уровнях 1 и 2 ускорение включено всегда: редкие проверки сами по себе не успевают подтвердить короткий сбой.'));
  var text=E('p',{'class':'hv-probe-text','role':'status'},probeLevelText(draft.level,draft.boost));
  var apply=E('button',{'type':'button','class':'cbi-button cbi-button-action'},bi('Apply','Применить'));
  var active=E('p',{'class':'hv-probe-active','role':'status'},probeBoostActiveText(policy,now));
  var refused=E('p',{'class':'hv-probe-refused','role':'status','hidden':''});
  // Busy codes (a switch or speed test is running) keep the owner's choice and retry every 10 s for 2 minutes.
  function probeRefused(choice,code){
    var busy=['PROBE-SETTINGS-BUSY','SPEED-BUSY','RPC-RATE-LIMIT','SETUP-SAVE-UNCONFIRMED'].indexOf(code)>=0;
    PROBE_DRAFT={level:choice.level,boost:choice.boost};refused.hidden=false;
    refused.textContent=bi('Not saved yet: ','Пока не сохранено: ')+code+(busy?bi(' · a switch is running, retrying automatically',' · идёт переключение, повторяем автоматически'):'');
    if(!busy)return;
    choice.tries=(choice.tries||0)+1;if(choice.tries>12)return;
    window.setTimeout(function(){if(PROBE_DRAFT&&PROBE_DRAFT.level===choice.level&&PROBE_DRAFT.boost===choice.boost&&!PROBE_BUSY)send(choice);},10000);
  }
  function paint(){
    var shown=PROBE_DRAFT||saved;
    if(!dragging)slider.value=String(shown.level);
    var forced=PROBE_FORCED_BOOST.indexOf(shown.level)>=0;box.checked=forced||shown.boost;box.disabled=forced;forcedNote.hidden=!forced;levelLabel.textContent=bi('Level ','Уровень ')+shown.level;text.textContent=probeLevelText(shown.level,shown.boost);
    for(var i=0;i<ticks.children.length;i++){var t=ticks.children[i];if(t.classList&&t.getAttribute)t.classList.toggle('hv-probe-tick-current',Number(t.getAttribute('data-level'))===shown.level);}
    var same=shown.level===saved.level&&shown.boost===saved.boost;
    if(PROBE_BUSY||same)apply.setAttribute('disabled','');else apply.removeAttribute('disabled');
  }
  function change(){var lvl=Number(slider.value);PROBE_DRAFT={level:lvl,boost:PROBE_FORCED_BOOST.indexOf(lvl)>=0||box.checked};if(PROBE_DRAFT.level===saved.level&&PROBE_DRAFT.boost===saved.boost)PROBE_DRAFT=null;paint();}
  slider.addEventListener('input',change);slider.addEventListener('change',change);box.addEventListener('change',change);
  slider.addEventListener('pointerdown',function(){dragging=true;});slider.addEventListener('pointerup',function(){dragging=false;});
  slider.addEventListener('mousedown',function(){dragging=true;});slider.addEventListener('mouseup',function(){dragging=false;});
  slider.addEventListener('touchstart',function(){dragging=true;});slider.addEventListener('touchend',function(){dragging=false;});
  apply.addEventListener('click',function(){
    var choice={level:Number(slider.value),boost:PROBE_FORCED_BOOST.indexOf(Number(slider.value))>=0||box.checked};  // what the owner sees, read at the click
    if(PROBE_BUSY||choice.level===saved.level&&choice.boost===saved.boost)return;send(choice);
  });
  function send(choice){
    PROBE_BUSY=true;apply.setAttribute('disabled','');
    rpc.declare({object:PROBE_RPC,reject:true,method:'setup_probe',params:['level','boost'],expect:{}})(choice.level,choice.boost).then(function(result){
      if(result&&result.saved){PROBE_APPLIED={level:choice.level,boost:choice.boost,at:Date.now()};PROBE_DRAFT=null;saved={level:choice.level,boost:choice.boost};refused.hidden=true;probeCheckSchedule(null);
        ui.addNotification(null,E('p',{},bi('Level ','Уровень ')+choice.level+bi(' saved. The router applies it now.',' сохранён. Роутер применяет его сразу.')));}
      else probeRefused(choice,(result&&result.code)||'SETUP-SAVE-FAILED');
    }).catch(function(){probeRefused(choice,'SETUP-SAVE-UNCONFIRMED');}).finally(function(){PROBE_BUSY=false;paint();});
  }
  if(PROBE_LOG_OPEN===false){try{PROBE_LOG_OPEN=window.localStorage.getItem(PROBE_LOG_KEY)==='1';}catch(e){}}
  var logHost=E('div',{'class':'hv-probe-log-host'});
  var log=E('details',{'class':'hv-probe-log-details','open':PROBE_LOG_OPEN?'':null},[E('summary',{},bi('Decision log: levels and boost','Журнал решений: уровни и ускорение')),logHost]);
  log.addEventListener('toggle',function(){PROBE_LOG_OPEN=log.open;try{window.localStorage.setItem(PROBE_LOG_KEY,log.open?'1':'0');}catch(e){}if(log.open)renderProbeLog(logHost);});
  if(PROBE_LOG_OPEN)renderProbeLog(logHost);
  var section=E('section',{'class':'hv-chart-card hv-probe-control','data-probe-level':String(policy.level)},[
    E('h3',{},bi('Probe level: router load ↔ reliability','Уровень опроса: нагрузка ↔ надёжность')),
    E('div',{'class':'hv-probe-scale'},[E('span',{},bi('Fewer checks, lower load','Меньше опросов, ниже нагрузка')),E('div',{'class':'hv-probe-slider-box'},[slider,ticks]),E('span',{},bi('More checks, faster switching','Больше опросов, быстрее переключение'))]),
    E('p',{'class':'hv-probe-text-row'},[levelLabel,' · ',text]),
    E('label',{'class':'hv-probe-boost-label'},[box,' ',E('strong',{},bi('Automatic boost','Автоматическое ускорение'))]),forcedNote,
    E('p',{'class':'hv-step-note'},[bi('If a channel fails a check, the router checks every 10 s for 10 minutes, then returns to the chosen level. Rare checks at rest, a quick answer when something breaks. Every episode is written to the log below.','Если канал не прошёл проверку, роутер 10 минут проверяет раз в 10 с, затем возвращается к выбранному уровню. В покое проверок мало, при сбое ответ быстрый. Каждый эпизод записывается в журнал ниже.')+' ',typeof helpLink==='function'?helpLink('probe-boost',bi('How it works in detail','Подробно, как это работает')):null]),
    active,E('p',{'class':'hv-req-actions'},[apply]),refused,log]);
  section.hvUpdate=function(policyNow,nowSeconds){
    saved=probeSavedChoice(policyNow);section.setAttribute('data-probe-level',String(policyNow.level));
    active.textContent=probeBoostActiveText(policyNow,nowSeconds);active.hidden=!active.textContent;
    if(log.open&&!PROBE_BUSY&&Date.now()-PROBE_LOG_AT>8000)renderProbeLog(logHost);
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
  PROBE_SCHEDULE.lastStatus=status.time;PROBE_SCHEDULE.interval=interval;PROBE_SCHEDULE.deadline=deadline;PROBE_SCHEDULE.boost=p.boost_active===true;
}
var PROBE_PULSE_BEFORE=1000,PROBE_PULSE_AFTER=3000;
function probeCheckPulse(){
  var s=PROBE_SCHEDULE,nowMs=Date.now();
  if(!Number.isFinite(s.deadline))return false;
  return nowMs>=s.deadline-PROBE_PULSE_BEFORE&&nowMs<s.deadline+PROBE_PULSE_AFTER;
}
function probePaintPulse(){
  if(typeof document==='undefined'||!document.querySelectorAll)return;
  var on=probeCheckPulse(),housings=document.querySelectorAll('.hv-light-three[data-signal="green"]');
  for(var i=0;i<housings.length;i++){var lamps=housings[i].querySelectorAll('.hv-lamp');for(var j=0;j<lamps.length;j++){var l=lamps[j];
    if(l.classList.contains('hv-lamp-green'))l.classList.toggle('hv-lamp-lit',!on);if(l.classList.contains('hv-lamp-yellow'))l.classList.toggle('hv-lamp-lit',on);}}
}
function probeCountdownText(node){
  var s=PROBE_SCHEDULE;if(!Number.isFinite(s.deadline)){node.textContent='';return;}
  var period=s.interval*1000,late=Date.now()-s.deadline;
  if(late>=PROBE_PULSE_AFTER&&period>0)s.deadline+=Math.ceil((late-PROBE_PULSE_AFTER+1)/period)*period;
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
  var compareNow=((inventory||{}).settings||{}).response_compare===true,compareBox=E('input',{'type':'checkbox','class':'hv-response-compare'});compareBox.checked=compareNow;
  var fastNow=((inventory||{}).settings||{}).fast_switch!==false,fastBox=E('input',{'type':'checkbox','class':'hv-fast-switch'});fastBox.checked=fastNow;
  function dirty(){return chosen!==current||compareBox.checked!==compareNow||fastBox.checked!==fastNow;}
  compareBox.addEventListener('change',function(){if(dirty())save.removeAttribute('disabled');else save.setAttribute('disabled','');});
  fastBox.addEventListener('change',function(){if(dirty())save.removeAttribute('disabled');else save.setAttribute('disabled','');});
  var save=E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':''},bi('Save','Сохранить'));
  var list=E('div',{'class':'hv-response-choices'},RESPONSE_CHOICES.map(function(c){
    var input=E('input',{'type':'radio','name':'hv-response-metric','value':c[0]});input.checked=c[0]===current;
    input.addEventListener('change',function(){chosen=c[0];if(dirty())save.removeAttribute('disabled');else save.setAttribute('disabled','');});
    return E('label',{'class':'hv-response-choice'},[input,' ',bi(c[1],c[2])]);}));
  save.addEventListener('click',function(){
    if(busy||!dirty())return;busy=true;save.setAttribute('disabled','');var compare=compareBox.checked,fast=fastBox.checked;
    rpc.declare({object:PROBE_RPC,reject:true,method:'setup_response',params:['metric','compare','fast_switch'],expect:{}})(chosen,compare,fast).then(function(r){
      if(r&&r.saved){current=chosen;compareNow=compare;fastNow=fast;ui.addNotification(null,E('p',{},bi('Saved. The router uses it from its next check.','Сохранено. Роутер применит со следующей проверки.')));}
      else ui.addNotification(null,E('p',{},(r&&r.code)||'SETUP-SAVE-FAILED'));
    }).catch(function(){ui.addNotification(null,E('p',{},'SETUP-SAVE-UNCONFIRMED'));}).finally(function(){busy=false;if(dirty())save.removeAttribute('disabled');});
  });
  return E('section',{'class':'hv-chart-card hv-response-settings'},[E('h3',{},bi('How the response is measured','Как измеряется отклик')),
    E('p',{'class':'hv-step-note'},bi('Ping is a short echo through each VPN to a public DNS address. It shows which channel is faster, gives small numbers and barely loads the router; recommended. Three websites over HTTPS measure opening real pages (DNS, connection, encryption, headers); the numbers are closer to what you feel but larger, and each check costs the router three encrypted connections per channel. The response is information only: Auto decides on its own health checks either way.','Пинг — короткий запрос через каждый VPN к публичному DNS-адресу. Он показывает, какой канал быстрее, даёт небольшие числа и почти не нагружает роутер; рекомендуется. Три сайта по HTTPS измеряют открытие настоящих страниц (DNS, соединение, шифрование, заголовки): числа ближе к ощущениям, но больше, и каждая проверка стоит роутеру трёх зашифрованных соединений на канал. Отклик — только информация: Auto в любом случае решает по своим проверкам исправности.')),
    list,
    E('label',{'class':'hv-response-compare-label'},[compareBox,' ',E('strong',{},bi('Measure all methods (comparison)','Мерить все способы (сравнение)'))]),
    E('p',{'class':'hv-step-note'},bi('Each check also pings the other two DNS addresses and opens the three websites through both channels. The ranking on the Tests page then shows every method side by side. Switching still uses only the method chosen above. Costs a little more router load and traffic.','Каждая проверка дополнительно пингует два других DNS-адреса и открывает три сайта через оба канала. Тогда рейтинг на странице «Тесты» показывает все способы рядом. Переключение по-прежнему использует только способ, выбранный выше. Немного больше нагрузка на роутер и трафик.')),
    E('label',{'class':'hv-fast-switch-label'},[fastBox,' ',E('strong',{},bi('Fast switch (without the GL rebuild)','Быстрое переключение (без перестройки GL)'))]),
    E('p',{'class':'hv-step-note'},bi('On the GL-iNet MT3000 the router writes the new channel order straight into its firewall rules in one step: the change itself takes tens of milliseconds and new connections use the new channel within about half a second, without the 20-60 second GL rebuild. If anything looks unexpected it falls back to the GL rebuild on its own. With Auto on, the manual channel buttons then switch at once (a few seconds) to a channel that passed its last check, without waits or extra confirmations; Auto keeps watching that channel afterwards. Turn this off to always use the GL rebuild.','На GL-iNet MT3000 роутер записывает новый порядок каналов прямо в правила межсетевого экрана одним шагом: сама смена занимает десятки миллисекунд, а новые соединения идут по новому каналу примерно за полсекунды, без перестройки GL на 20-60 секунд. Если что-то выглядит неожиданно, роутер сам откатывается к перестройке GL. При включённом Auto ручные кнопки каналов тогда переключают сразу (за несколько секунд) на канал, прошедший последнюю проверку, без ожиданий и дополнительных подтверждений; после этого Auto продолжает следить за этим каналом. Выключите, чтобы всегда использовать перестройку GL.')),
    E('p',{'class':'hv-req-actions'},[save])]);
}
// Statistics mode (owner, 30 Oct 2026): "work" keeps only what switching needs; "diagnostic" records everything for 1 h-7 days.
function statsModeModel(source,now){
  var s=(source&&source.stats_mode&&typeof source.stats_mode==='object')?source.stats_mode:null;
  if(s)return {diagnostic:s.mode==='diagnostic',until:Number(s.until)||0};
  var settings=(source&&source.settings)||{},until=Number(settings.stats_until)||0;
  return {diagnostic:settings.stats_mode==='diagnostic'&&until>now,until:until};
}
// One note for the statistics surfaces while the router is in work mode; nothing in diagnostics.
function statsWorkNote(status){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,model=statsModeModel(status||{},now);
  if(model.diagnostic||!(status&&status.stats_mode))return '';
  return E('p',{'class':'hv-step-note hv-stats-work-note','data-stats-work':'1'},[bi('Statistics collection is off (Work mode): the router keeps only what switching needs. To record charts and statistics for 1 to 14 days, turn on Diagnostics: ','Сбор статистики выключен (режим «Работа»): роутер хранит только нужное для переключения. Чтобы записывать графики и статистику на срок от 1 до 14 дней, включите «Диагностику»: '),
    E('a',{'href':'#collection'},bi('Advanced → Statistics collection','Расширенные → Сбор статистики'))]);
}
// Advanced > Statistics collection: the page itself is optional (lazy); this model gives it the router call.
function collectionModel(status){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,m=statsModeModel(status||{},now);
  return {diagnostic:m.diagnostic,until:m.until,storage:(status&&status.stats_mode&&status.stats_mode.storage)||{},
    save:function(mode,hours){return mode==='work'?rpc.declare({object:PROBE_RPC,reject:true,method:'setup_stats',params:['mode'],expect:{}})('work')
      :rpc.declare({object:PROBE_RPC,reject:true,method:'setup_stats',params:['mode','hours'],expect:{}})('diagnostic',hours);},
    notify:function(text){ui.addNotification(null,E('p',{},text));}};
}
function renderCollectionStats(status){
  LAZY_HELP.collectionStatus=status;var host=renderLazyPage('collection'),item=LAZY_HELP.hosts.collection;
  // Rendered once per load: the form must not reset while the owner is choosing.
  if(LAZY_HELP.api&&item.requested&&!item.ready){while(host.firstChild)host.removeChild(host.firstChild);host.appendChild(LAZY_HELP.api.renderCollectionPage(collectionModel(status)));item.ready=true;}
  return host;
}
// Ranking columns for "measure all methods": one column per method the router compared.
var COMPARE_LABELS={'icmp-1.1.1.1':['Ping 1.1.1.1','Пинг 1.1.1.1'],'icmp-8.8.8.8':['Ping 8.8.8.8','Пинг 8.8.8.8'],'icmp-9.9.9.9':['Ping 9.9.9.9','Пинг 9.9.9.9'],'websites':['Three websites','Три сайта']};
function compareColumns(status){var c=(status||{}).response_compare;return c&&Array.isArray(c.methods)?c.methods.filter(function(m){return COMPARE_LABELS[m];}):[];}
function compareHeader(method){return bi(COMPARE_LABELS[method][0],COMPARE_LABELS[method][1]);}
function compareCell(status,method,id){
  var r=((((status||{}).response_compare||{}).profiles||{})[id]||{})[method];
  if(!r||!(r.ok+r.failed))return '—';
  var loss=r.failed?' · '+Math.round(100*r.failed/(r.ok+r.failed))+'% '+bi('lost','потерь'):'';
  return (r.avg_ms===null?'—':websiteMs(r.avg_ms)+' '+bi('ms','мс'))+loss;
}
