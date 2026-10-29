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
function renderProbeControl(status,inventory){
  var policy=status.probe_policy||{},settings=inventory.settings||{};
  if(!Number.isInteger(policy.level))return null;
  var stored=Number(settings.probe_level),saved={level:stored>=1&&stored<=5?stored:policy.level,boost:settings.probe_boost===undefined?policy.boost_enabled!==false:settings.probe_boost!==false};
  if(PROBE_APPLIED&&(policy.level===PROBE_APPLIED.level&&policy.boost_enabled===PROBE_APPLIED.boost||Date.now()-PROBE_APPLIED.at>180000))PROBE_APPLIED=null;
  if(PROBE_APPLIED)saved={level:PROBE_APPLIED.level,boost:PROBE_APPLIED.boost};
  var draft=PROBE_DRAFT||saved;
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
      if(result&&result.saved){PROBE_APPLIED={level:PROBE_DRAFT.level,boost:PROBE_DRAFT.boost,at:Date.now()};PROBE_DRAFT=null;ui.addNotification(null,E('p',{},bi('Probe level saved. The router applies it on its next check.','Уровень опроса сохранён. Роутер применит его со следующей проверки.')));}
      else ui.addNotification(null,E('p',{},(result&&result.code)||'SETUP-SAVE-FAILED'));
    }).catch(function(){ui.addNotification(null,E('p',{},'SETUP-SAVE-UNCONFIRMED'));}).finally(function(){PROBE_BUSY=false;});
  });
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000,active=null;
  if(policy.boost_active&&Number.isFinite(policy.boost_until)){
    var trigger=policy.boost_trigger||{},left=Math.max(0,Math.round((policy.boost_until-now)/60));
    active=E('p',{'class':'hv-probe-active','role':'status'},[bi('Boost is active: checks every 10 s for about ','Ускорение сейчас включено: проверка раз в 10 с ещё примерно ')+left+bi(' min · ',' мин · ')+(trigger.role==='source'?bi('primary channel','основной канал'):trigger.role==='target'?bi('reserve channel','резервный канал'):bi('channel','канал'))+' · ',typeof safeCode==='function'&&safeCode(trigger.code)&&typeof errorCodeLink==='function'?errorCodeLink(trigger.code):(trigger.code||'')]);
  }
  if(PROBE_LOG_OPEN===false){try{PROBE_LOG_OPEN=window.localStorage.getItem(PROBE_LOG_KEY)==='1';}catch(e){}}
  var logHost=E('div',{'class':'hv-probe-log-host'});
  var log=E('details',{'class':'hv-probe-log-details','open':PROBE_LOG_OPEN?'':null},[E('summary',{},bi('Decision log: levels and boost','Журнал решений: уровни и ускорение')),logHost]);
  log.addEventListener('toggle',function(){PROBE_LOG_OPEN=log.open;try{window.localStorage.setItem(PROBE_LOG_KEY,log.open?'1':'0');}catch(e){}if(log.open)renderProbeLog(logHost);});
  if(PROBE_LOG_OPEN)renderProbeLog(logHost);
  return E('section',{'class':'hv-chart-card hv-probe-control','data-probe-level':String(policy.level)},[
    E('h3',{},bi('Probe level: router load ↔ reliability','Уровень опроса: нагрузка ↔ надёжность')),
    E('div',{'class':'hv-probe-scale'},[E('span',{},bi('Fewer checks, lower load','Меньше опросов, ниже нагрузка')),slider,E('span',{},bi('More checks, faster switching','Больше опросов, быстрее переключение'))]),
    text,
    E('label',{'class':'hv-probe-boost-label'},[box,' ',E('strong',{},bi('Automatic boost','Автоматическое ускорение'))]),
    E('p',{'class':'hv-step-note'},bi('If the primary or reserve channel fails a check, the router checks every 10 s for 10 minutes to confirm the failure quickly or see that it was a one-off. After 10 minutes without failures it returns to the chosen level. A reliable pair is then checked rarely and a real failure is still caught fast. Every episode and its result are written to the log below.','Если основной или резервный канал не прошёл проверку, роутер на 10 минут переходит на проверку раз в 10 с: быстро подтверждает сбой или убеждается, что это случайность. Через 10 минут без сбоев возвращается к выбранному уровню. Так надёжные каналы проверяются редко, а настоящий сбой всё равно замечается быстро. Каждый эпизод и его итог записываются в журнал ниже.')),
    active,E('p',{'class':'hv-req-actions'},[apply]),log].filter(Boolean));
}

// Countdown to the router's next scheduled channel check, from its published cadence (probe level or boost).
var PROBE_TICK=null;
function probeCountdownText(node){
  var period=node.hvInterval*1000,late=Date.now()-node.hvDeadline;
  if(late>=0&&period>0)node.hvDeadline+=Math.ceil((late+1)/period)*period;
  var left=Math.round((node.hvDeadline-Date.now())/1000);
  node.textContent=left>0?bi('Check in ','Проверка через ')+left+bi(' s',' с'):bi('Checking','Проверка');
}
function probeCountdown(status){
  var p=(status||{}).probe_policy||{},interval=p.effective_interval;
  if(!Number.isFinite(interval)||interval<=0||!Number.isFinite(status.time))return null;
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var node=E('small',{'class':'hv-probe-countdown','role':'timer','aria-live':'off'},'');
  node.hvDeadline=Date.now()+(status.time+interval-now)*1000;node.hvInterval=interval;
  if(typeof node.textContent!=='undefined'||true)probeCountdownText(node);
  if(!PROBE_TICK&&typeof window!=='undefined'&&window.setInterval&&typeof document!=='undefined'&&document.querySelectorAll)
    PROBE_TICK=window.setInterval(function(){var nodes=document.querySelectorAll('.hv-probe-countdown');for(var i=0;i<nodes.length;i++)if(Number.isFinite(nodes[i].hvDeadline))probeCountdownText(nodes[i]);},1000);
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
