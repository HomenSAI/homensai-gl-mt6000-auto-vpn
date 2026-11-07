/* Pure teaching scenes: no RPC, credentials, route writes or readiness side effects. */
var LEARN_SCENES=[
 [['Observe the pair','Наблюдаем пару'],['Repeated primary failures','Повторные отказы основного'],['Reserve passes checks','Резерв прошёл проверки'],['Select reserve traffic policy','Выбираем маршрут резерва']],
 [['Cable access to the router','Кабельный доступ к роутеру'],['Wi-Fi client access','Доступ клиента по Wi-Fi'],['Separate mobile connection','Независимая мобильная связь'],['Keep router access during tests','Сохраняем доступ на время тестов']],
 [['Router check: model and parts','Проверка роутера: модель и части'],['Choose two channels','Выбираем два канала'],['Behaviour, then the terms','Поведение, затем условия'],['Save; Auto still stays off','Сохраняем; Auto остаётся выключенным']],
 [['Configure profiles in stock VPN app','Настраиваем профили в штатном VPN'],['Bind a profile to each client','Назначаем профиль каждому клиенту'],['Assign primary and reserve roles','Выбираем роли основного и резерва'],['Save two distinct clients','Сохраняем два разных клиента']],
 [['Check current DNS and HTTPS','Проверяем свежие DNS и HTTPS'],['Check the VPN and routes','Проверяем VPN и маршруты'],['Client trial needs its own helper','Для клиентского теста нужен помощник'],['Turn Auto on when ready','Включаем Auto после готовности']],
 [['Selected route and health differ','Маршрут и исправность — разные данные'],['Compare HTTPS delays','Сравниваем HTTPS-задержки'],['Explore the saved 1–24h window','Просматриваем историю 1–24 ч'],['One outage, several failed checks','Один отказ, несколько плохих проверок']],
 [['Inspect fresh observations','Смотрим свежие наблюдения'],['Keep the working reserve','Сохраняем работающий резерв'],['Diagnose the failed primary','Проверяем неисправный основной'],['Return only under valid policy/readiness','Возвращаемся по политике и готовности']],
 [['Keep keys and backups private','Храним ключи и копии приватно'],['Use the permitted existing pair','Используем разрешённую пару'],['Missing data stays unconfirmed','Нет данных — нет подтверждения'],['Training is not router certification','Обучение не заменяет проверку роутера']]
];
function renderLearnScene(lesson){
 var frames=LEARN_SCENES[lesson]||LEARN_SCENES[0],index=0,timer=null,disposed=false;
 var root=E('figure',{'class':'hv-learn-scene','data-learn-scene':String(lesson)}),drawing=E('div',{'class':'hv-learn-drawing'}),caption=E('figcaption',{'role':'status','aria-live':'polite'});
 function svg(tag,attrs,text){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});if(text!=null)n.textContent=text;return n;}
 function pause(){if(timer!==null){clearTimeout(timer);timer=null;}play.textContent=bi('Play','Запустить');play.setAttribute('aria-pressed','false');}
 function visible(){return root.isConnected!==false&&(!root.getClientRects||root.getClientRects().length>0);}
 function schedule(){timer=setTimeout(function(){timer=null;if(disposed||!visible()){pause();return;}index=Math.min(frames.length-1,index+1);draw();if(index===frames.length-1)pause();else schedule();},1800);}
 function action(name,label,fn){return E('button',{'type':'button','class':'cbi-button','data-scene-action':name,'click':function(){if(!disposed)fn();}},label);}
 var back=action('back',bi('Previous step','Шаг назад'),function(){pause();index=Math.max(0,index-1);draw();});
 var play=action('play',bi('Play','Запустить'),function(){if(timer!==null){pause();return;}if(index===frames.length-1){index=0;draw();}play.textContent=bi('Pause','Пауза');play.setAttribute('aria-pressed','true');schedule();});play.setAttribute('aria-pressed','false');
 var next=action('next',bi('Next step','Шаг вперёд'),function(){pause();index=Math.min(frames.length-1,index+1);draw();});
 var reset=action('reset',bi('Reset scene','Сначала'),function(){pause();index=0;draw();});
 function renderFrame(){
  while(drawing.firstChild)drawing.removeChild(drawing.firstChild);
  var reserve=(lesson===0&&index===3)||(lesson===6&&index>0),failed=(lesson===0&&index>0)||(lesson===6&&index>0);
  var image=svg('svg',{viewBox:'0 0 640 270',role:'img','aria-label':bi(frames[index][0],frames[index][1])});
  if(lesson!==0&&lesson!==6){
   frames.forEach(function(frame,i){
    var x=12+i*158,color=i===index?'#2563eb':i<index?'#13986c':'#8a929d';
    if(i<3)image.appendChild(svg('path',{d:'M'+(x+140)+' 124 h18',stroke:i<index?'#13986c':'#8a929d','stroke-width':3}));
    image.appendChild(svg('rect',{x:x,y:44,width:140,height:164,rx:14,fill:'var(--surface,#fff)',stroke:color,'stroke-width':i===index?3:1}));
    image.appendChild(svg('circle',{cx:x+70,cy:76,r:17,fill:color}));image.appendChild(svg('text',{x:x+70,y:81,'text-anchor':'middle',fill:'#fff','font-size':14},String(i+1)));
    var lines=[],line='';bi(frame[0],frame[1]).split(' ').forEach(function(word){if(line&&(line+' '+word).length>18){lines.push(line);line=word;}else line+=(line?' ':'')+word;});if(line)lines.push(line);
    lines.forEach(function(text,j){image.appendChild(svg('text',{x:x+70,y:115+j*18,'text-anchor':'middle','font-size':12,fill:'currentColor'},text));});
   });
  }else{
  var nodes=[{x:8,y:90,w:125,label:bi('Your device','Ваше устройство')},{x:174,y:90,w:125,label:bi('Router','Роутер')},{x:342,y:20,w:136,label:bi('Primary VPN','Основной VPN')},{x:342,y:170,w:136,label:bi('Reserve VPN','Резервный VPN')},{x:518,y:90,w:114,label:bi('Internet','Интернет')}];
  function link(path,active){image.appendChild(svg('path',{d:path,fill:'none',stroke:active?'#13986c':'#8a929d','stroke-width':active?5:2,'stroke-dasharray':active?'none':'6 5'}));}
  link('M133 127 H174',true);link('M299 127 H320 V57 H342',!reserve);link('M299 127 H320 V207 H342',reserve);link('M478 57 H498 V127 H518',!reserve);link('M478 207 H498 V127 H518',reserve);
  nodes.forEach(function(n,i){var selected=i===2?!reserve:i===3?reserve:true,color=i===2&&failed?'#c33b4d':selected?'#13986c':'#a16207';
   image.appendChild(svg('rect',{x:n.x,y:n.y,width:n.w,height:74,rx:13,fill:'var(--surface, #fff)',stroke:color,'stroke-width':2}));
   image.appendChild(svg('rect',{x:n.x+n.w/2-12,y:n.y+10,width:24,height:17,rx:3,fill:'none',stroke:color,'stroke-width':2}));
   image.appendChild(svg('path',{d:'M'+(n.x+n.w/2-7)+' '+(n.y+32)+' h14',stroke:color,'stroke-width':2}));
   image.appendChild(svg('text',{x:n.x+n.w/2,y:n.y+52,'text-anchor':'middle','font-size':12,fill:'currentColor'},n.label));
   if(i===2||i===3)image.appendChild(svg('text',{x:n.x+n.w/2,y:n.y+66,'text-anchor':'middle','font-size':10,fill:'currentColor'},i===2&&failed?bi('Failure in this example','Отказ в этом примере'):selected?bi('Selected','Выбран'):bi('Standby','Ожидает')));
  });
  }
  drawing.appendChild(image);caption.textContent=(index+1)+' / '+frames.length+' · '+bi(frames[index][0],frames[index][1]);
  back.disabled=index===0;next.disabled=index===frames.length-1;
  root.setAttribute('data-scene-step',String(index));
 }
 function draw(){return typeof learnKeepViewport==='function'?learnKeepViewport(root,renderFrame):renderFrame();}
 root.hvDispose=function(){disposed=true;pause();};
 root.appendChild(E('p',{'class':'hv-muted'},bi('Interactive illustration — changes only this example, never the router.','Интерактивная схема — меняется только пример, настройки роутера не затрагиваются.')));
 root.appendChild(drawing);root.appendChild(caption);root.appendChild(E('div',{'class':'hv-scene-controls'},[back,play,next,reset]));
 root.appendChild(E('ol',{'class':'hv-scene-outline'},frames.map(function(f){return E('li',{},bi(f[0],f[1]));})));
 draw();return root;
}
/* 2.1.0-alpha9: the 5-step training of the auto-adaptation and the master slider (main page: advTour; owner mockup
   private/math/master-slider #tour). Rows: {h:[EN,RU],b:[EN,RU]}; the bodies are fixed HTML, no router data. The main
   page adds the live curve to step 2. */
var ADV_TOUR=[
 {h:['Two goals that pull apart','Две цели, которые тянут в разные стороны'],
  b:['<p><b>Fast reaction</b> — leave for the reserve as early as possible when the primary fails: fewer seconds without internet in a real outage.</p><p><b>No unnecessary switches</b> — do not react to short blips that would pass by themselves: every switch costs a short stall and breaks connections.</p><p>Both at once are impossible: the earlier we leave, the more often we leave for nothing.</p>',
     '<p><b>Быстрая реакция</b> — уйти на резерв как можно раньше, когда основной канал упал: меньше секунд без интернета при настоящем обрыве.</p><p><b>Без лишних переключений</b> — не дёргаться из-за коротких сбоев, которые прошли бы сами: каждое переключение само стоит короткого подвисания и рвёт соединения.</p><p>Обе цели сразу недостижимы: чем раньше уходим, тем чаще уходим зря.</p>']},
 {h:['What the curve is','Что такое кривая'],
  b:['<p>Every point is a combination of six detector and return settings run through a model day (outages, losses, flapping, a failed reserve). The curve is 11 anchors chosen in a simulator near the border of the best combinations. Independent checking did not confirm a smooth monotone trade-off (several positions are dominated by others), so the position is a guide, not a guarantee. On the chart fast reaction is at the bottom right (less downtime, more unnecessary switches), no unnecessary switches at the top left; on the slider it is the other way round: fast reaction on the left.</p>',
     '<p>Каждая точка — сочетание шести настроек детектора и возврата, прогнанное через модель суток (обрывы, потери, дребезг, отказ резерва). Кривая — 11 опорных точек, выбранных в симуляторе у границы лучших сочетаний. Независимая проверка не подтвердила гладкий монотонный компромисс (часть положений доминируется другими), поэтому положение — ориентир, не гарантия. На графике быстрая реакция — справа внизу (меньше простоя, больше лишних переключений), без лишних переключений — слева вверху; на ползунке наоборот: быстрая реакция слева.</p>']},
 {h:['The dot and the table','Точка и таблица'],
  b:['<p>Move the slider: the blue dot travels along the curve and the table shows every variable at that point. <b>Yellow</b> is what changes when you apply it, the arrow shows where. The green ring is what the router runs now.</p><p>The <b>Expected</b> line says it plainly: when we leave, which outages we ride out, how many unnecessary switches and how much downtime per day.</p>',
     '<p>Двигаете ползунок — синяя точка едет по кривой, а таблица показывает все переменные в этой точке. <b>Жёлтым</b> — что изменится при применении, стрелка показывает куда. Зелёное кольцо — то, с чем роутер работает сейчас.</p><p>Строка <b>«Ожидаемо»</b> переводит это на человеческий язык: через сколько секунд уйдём, какие обрывы переждём, сколько лишних переключений и простоя в сутки.</p>']},
 {h:['How the adaptation decides','Как решает автоподстройка'],
  b:['<p>The router keeps a network journal and counts the events of the window (7 days by default): short and long outages, losses, flapping, reserve failures.</p><p>Every night at 03:30 it estimates the cost of each point of the curve (downtime + 20 s per unnecessary switch) and looks for the cheapest. Fewer than 5 events change nothing ("not enough data"); a move needs a saving of at least 5 %. In mode Auto it moves by at most 0.1 a day and never during an outage or a switch.</p>',
     '<p>Роутер ведёт журнал сети и считает события за окно (по умолчанию 7 дней): короткие и долгие обрывы, потери, дребезг, отказы резерва.</p><p>Каждую ночь в 03:30 он оценивает цену каждой точки кривой (простой + 20 с за каждое лишнее переключение) и ищет самую дешёвую. Меньше 5 событий — ничего не меняется («мало данных»); сдвиг — только при экономии не меньше 5 %. В режиме «Авто» — не больше 0,1 в сутки и никогда во время обрыва или переключения.</p>']},
 {h:['How to override and return to automatic','Как вмешаться и вернуть автоматику'],
  b:['<p><b>Manual</b>: move the slider yourself and press "Apply the position". <b>Advice + Apply</b>: the system only suggests. <b>Fine tuning</b> opens θ, the short-outage length and P(G) separately — that is "Custom"; <b>Attach to the slider</b> returns to the curve.</p><p>To let the system decide again choose <b>Auto</b>. The router checks the safety rules at every change and never starts Auto by itself.</p>',
     '<p><b>«Вручную»</b> — двигаете ползунок сами и жмёте «Применить положение». <b>«Совет + Применить»</b> — система только подсказывает. <b>«Тонкая настройка»</b> открывает θ, длину короткого обрыва и P(G) по отдельности — это «Пользовательская»; <b>«Привязать к ползунку»</b> возвращает на кривую.</p><p>Чтобы снова решала система — выберите <b>«Авто»</b>. Роутер проверяет правила безопасности при каждом изменении и никогда не включает Auto сам.</p>']}];
/* 2.1.0-alpha9 (04.11.2026): the expert group «Для эксперта → Детектор и датчики» of the settings page. Data only; the main
   page renders and saves it (settings.js: xdBody, xdSave) once this module is loaded. Texts are [EN, RU]. Field: k = UCI
   option, g = group, ty = b (switch) | s (choice) | n (whole number), d = the default (what inventory.lua reads when the
   option is absent; nothing here changes a default), min/max/z (z: 0 is also allowed), u = unit, stop = changed only with
   Auto off (the backend asks for it: configuration_guard, CONFIG-STOP-AUTO-FIRST), dep = [option, value] it depends on. */
var EXPERT_GROUPS=[
 {h:['Flapping: pause before the return','Качели: пауза возврата'],b:['When the primary fails and recovers again and again, the return to it is delayed. Leaving a failed primary is never blocked by this.','Если основной канал снова и снова падает и оживает, возврат на него откладывается. Уход с упавшего основного это никогда не блокирует.']},
 {h:['Auto loop: pauses and waking','Цикл Auto: паузы и пробуждение'],b:['Auto itself reads these, so they change only with Auto off. Saving never starts Auto.','Эти настройки читает сам Auto, поэтому они меняются только при выключенном Auto. Сохранение никогда не включает Auto.']},
 {h:['Monitor checks','Проверки монитора'],b:['Applied by the monitor at its next pass; Auto does not need to stop.','Монитор применяет их со следующего прохода; Auto останавливать не нужно.']},
 {h:['Sensors','Датчики'],b:['Sensors only give hints or hold a switch back; none of them can prove a failure alone.','Датчики дают только подсказки или удерживают переключение; ни один сам по себе не доказывает отказ.']},
 {h:['Server keys','Ключи серверов'],b:['Applied at the next check of the servers.','Применяется со следующей проверки серверов.']}];
var EXPERT_FIELDS=[
 {k:'recovery_flap_model',g:0,ty:'s',d:'double',stop:1,l:['Return pause model','Модель паузы возврата'],
  h:['How the wait before the return grows after repeated departures. Doubling: twice as long for every departure over the limit. Half-life: every departure adds a penalty that fades with time (RFC 2439). The pause never exceeds 600 s.','Как растёт ожидание возврата после повторных уходов. «Удвоение» — вдвое за каждый уход сверх лимита. «Полураспад» — каждый уход добавляет штраф, который со временем затухает (RFC 2439). Пауза не больше 600 с.'],
  o:[['double',['Doubling','Удвоение']],['halflife',['Half-life','Полураспад']]]},
 {k:'recovery_flap_limit',g:0,ty:'n',d:2,min:1,max:10,stop:1,l:['Departures before the pause grows','Уходов до удлинения паузы'],
  h:['How many departures to the reserve within the window are normal before the return starts to wait longer. 1 is the strictest. Experimental: the default 2 per 60 min was chosen in simulation, not validated on hardware.','Сколько уходов на резерв в окне считается обычным, прежде чем возврат начнёт ждать дольше. 1 — самый строгий. Экспериментально: умолчание 2 за 60 мин выбрано в симуляции, на железе не проверено.']},
 {k:'recovery_flap_window',g:0,ty:'n',d:60,min:1,max:120,u:['min','мин'],stop:1,l:['Window for counting departures','Окно подсчёта уходов'],
  h:['The time over which departures are counted; older ones no longer lengthen the pause. Experimental: the 60 min default was chosen in simulation, not validated on hardware.','За какое время считаются уходы; более старые паузу уже не удлиняют. Экспериментально: умолчание 60 мин выбрано в симуляции, на железе не проверено.']},
 {k:'recovery_flap_halflife',g:0,ty:'n',d:1800,min:600,max:3600,u:['s','с'],stop:1,dep:['recovery_flap_model','halflife'],l:['Penalty half-life','Полураспад штрафа'],
  h:['Half-life model only: in how many seconds a penalty fades by half.','Только для «Полураспада»: за сколько секунд штраф убывает вдвое.']},
 {k:'recovery_flap_suppress',g:0,ty:'n',d:1500,min:1000,max:3000,stop:1,dep:['recovery_flap_model','halflife'],l:['Suppress threshold','Порог удлинения'],
  h:['Half-life model only: above this penalty the return waits longer. One departure adds 1000.','Только для «Полураспада»: при штрафе выше этого возврат ждёт дольше. Один уход добавляет 1000.']},
 {k:'recovery_flap_reuse',g:0,ty:'n',d:500,min:200,max:1000,stop:1,dep:['recovery_flap_model','halflife'],l:['Release threshold','Порог снятия'],
  h:['Half-life model only: the longer wait ends when the penalty has fallen below this.','Только для «Полураспада»: удлинение снимается, когда штраф упал ниже этого.']},
 {k:'retry_backoff',g:1,ty:'s',d:'fibonacci',stop:1,l:['Pause after a failed Auto pass','Пауза после неудачного прохода Auto'],
  h:['Fibonacci: 2, 2, 4, 6, 10, 15 s with jitter, so a failure that clears at once costs a second and routers do not retry together. Fixed: the former 5 s. Experimental: chosen in simulation, not proven better than a fixed 5 s with jitter, not validated on hardware.','Фибоначчи: 2, 2, 4, 6, 10, 15 с с разбросом — сбой, который прошёл сам, стоит секунду, а роутеры не повторяют все разом. «Фиксированная»: прежние 5 с. Экспериментально: выбрано в симуляции, не доказано, что лучше фиксированных 5 с с разбросом, на железе не проверено.'],
  o:[['fibonacci',['Fibonacci, 2 to 15 s','Фибоначчи, 2…15 с']],['fixed',['Fixed, 5 s','Фиксированная, 5 с']]]},
 {k:'auto_event_wake',g:1,ty:'b',d:true,stop:1,l:['Wake Auto on an event','Будить Auto по событию'],
  h:['After a check in which a channel failed, Auto wakes at once (within 0.2 s) instead of at its next 2 s tick. Off: the tick only.','После проверки, в которой канал отказал, Auto просыпается сразу (за 0,2 с), а не на очередном тике раз в 2 с. Выключено: только тик.']},
 {k:'parallel_recheck',g:1,ty:'b',d:false,stop:1,l:['Re-check next to the preparation','Перепроверка рядом с подготовкой'],
  h:['The live check before a departure runs while the switch is being prepared: about 1 s faster. The price, by the simulator: about 0.15 more unnecessary departures a day. Off by default until it is measured on a router: the check runs after the preparation.','Живая проверка перед уходом идёт одновременно с подготовкой переключения: примерно на 1 с быстрее. Цена по симулятору: около 0,15 лишних уходов в сутки. Выключено: проверка после подготовки.']},
 {k:'probe_spread',g:2,ty:'b',d:true,l:['Spread the checks in time','Разносить проверки по времени'],
  h:['The checks of one pass start with a small offset (up to 3 s) and the carrying primary is measured last, so its data is as fresh as before. Off: all at once. Experimental: chosen in simulation, not validated on hardware (the process peak on the router is not measured).','Проверки одного прохода стартуют с небольшим сдвигом (до 3 с), а основной канал меряется последним — его данные так же свежи. Выключено: все сразу. Экспериментально: выбрано в симуляции, на железе не проверено (пик процессов на роутере не измерен).']},
 {k:'reserve_probe_interval',g:2,ty:'n',d:0,min:20,max:120,z:1,u:['s','с'],l:['Rarer checks of the reserve','Редкие проверки резерва'],
  h:['0 = the reserve is checked in every pass. 20 to 120: while everything is calm it is checked once in that many seconds, and at the slightest doubt at once. Less load; its data stays within the validity limit.','0 — резерв проверяется в каждом проходе. 20…120: пока всё спокойно, он проверяется раз в столько секунд, а при малейшем сомнении сразу. Меньше нагрузки; данные резерва остаются в пределах срока годности.']},
 {k:'probe_target_log',g:2,ty:'b',d:true,l:['Log of answers per probe target','Журнал ответов по целям проб'],
  h:['Keeps in RAM what each probe target answered in each check, for studying the sensors. Nothing is written to flash. Off: no log.','Хранит в ОЗУ, что ответила каждая цель в каждой проверке, — для изучения датчиков. Во флеш ничего не пишется. Выключено: журнала нет.']},
 {k:'wan_sensor',g:3,ty:'b',d:true,l:['Diagnosis «no internet from the provider»','Диагноз «нет интернета у провайдера»'],
  h:['Its own echo through the WAN port, past the VPN, and the GL verdict. When the WAN is proven down Auto does not switch (WAN-DOWN); when the WAN is fine but the primary is down it checks the primary more often. Off: no diagnosis.','Свой эхо-запрос через порт WAN мимо VPN и вердикт GL. Если WAN доказанно лежит, Auto не переключает каналы (WAN-DOWN); если WAN жив, а основной упал, основной проверяется чаще. Выключено: диагноза нет.']},
 {k:'wan_recover_grace',g:3,ty:'n',d:30,min:0,max:120,u:['s','с'],dep:['wan_sensor',true],l:['Wait after the WAN returns','Ожидание после возврата WAN'],
  h:['How long Auto waits after the internet is back for the primary to confirm before it decides. 0 = do not wait. Works with the WAN diagnosis on.','Сколько Auto ждёт после возврата интернета, пока основной канал подтвердит связь, прежде чем решать. 0 — не ждать. Действует при включённом диагнозе WAN.']},
 {k:'wg_events',g:3,ty:'b',d:true,l:['WireGuard events of the GL kernel','События WireGuard от ядра GL'],
  h:['Listens to the GL hook (REKEY-TIMEOUT, REKEY-GIVEUP). A reason to check more often, never proof of a failure. Off: not listened to.','Слушает хук GL (REKEY-TIMEOUT, REKEY-GIVEUP). Повод проверять чаще, но не доказательство отказа. Выключено: не слушает.']},
 {k:'stall_sensor',g:3,ty:'b',d:true,l:['«Silent tunnel» sensor','Датчик «тихого» туннеля'],
  h:['Passive: the tunnel sends bytes, but nothing comes back for 3 s or more. Only a reason to check more often.','Пассивный: туннель отправляет байты, а ответных нет 3 с и дольше. Только повод проверять чаще.']},
 {k:'stall_veto',g:3,ty:'b',d:true,dep:['stall_sensor',true],l:['Veto of a false heartbeat alarm','Вето ложной тревоги пульса'],
  h:['If traffic still comes in through the tunnel (10 kbit/s or more), lost heartbeat echoes do not count as a failure. Needs the silent-tunnel sensor.','Если по туннелю ещё идёт входящий трафик (10 кбит/с и больше), потерянные эхо пульса не считаются отказом. Нужен датчик «тихого» туннеля.']},
 {k:'heartbeat_quorum',g:3,ty:'b',d:false,l:['Heartbeat «2 of 3 targets»','Пульс «2 из 3 целей»'],
  h:['The fast heartbeat asks 3 targets of 8 in turn; a beat is lost when fewer than two answer. By the study it is not better on every measure, so it is off unless you want it.','Быстрый пульс опрашивает 3 цели из 8 по очереди; удар потерян, если ответили меньше двух. По исследованию он не лучше по всем показателям, поэтому выключен, пока вы не захотите.']},
 {k:'server_key_pin',g:4,ty:'s',d:'warn',l:['Check of the VPN server keys','Проверка ключей VPN-серверов'],
  h:['The key of every server is remembered at the first connection. Warn: a changed key is shown. Block: Auto does not use a channel whose server key changed until you accept the new key (a provider that rotates keys then blocks the channel). Off: not checked.','Ключ каждого сервера запоминается при первом подключении. «Предупреждать» — смена ключа показывается. «Не использовать канал» — Auto не берёт канал со сменившимся ключом, пока вы не примете новый (провайдер, который меняет ключи, при этом заблокирует канал). «Выключено» — не проверяется.'],
  o:[['warn',['Warn only','Только предупреждать']],['enforce',['Block the channel','Не использовать канал']],['off',['Off','Выключено']]]}];
/* The renderer and the saver of the expert group «Детектор и датчики» and of the fast end of the master slider (positions
   t < 0, administrator switch, turbo opt-in). They live here, next to their texts, so that the first screen stays small; the
   page calls them once this module is loaded (api.expertUI(env)). env = the page's own helpers and state (settings.js,
   advisor.js): t, esc, HV, XD (the edited values), ADV, saveBar, needsStop, rpcCall, draft (draftFromInventory), modal, toast,
   codeNotice, $$, advNum, advRpc, advChart, advLegend, VER (the training modal tour(i) uses the last three). Flap damping is saved with setup_recovery, the rest with setup_detector; the fields marked
   stop need Auto off, and the page offers to stop it instead of failing. Only changed fields are sent. */
var EXPERT_ACK=['минимум простоя, допускаю до ~8 лишних уходов в сутки','minimum downtime, i accept up to ~8 extra switches a day'];
var EXPERT_ACK_CODE='minimum-downtime-up-to-8-extra-switches-a-day';  /* what the router wants in turbo_ack (advisor_control.TURBO_ACK) */
/* the explanations of the table of all variables (main page: advRows): [EN, RU] */
var EXPERT_HINTS={fine:['Any change detaches the values from the slider ("Custom") and selects mode "Manual". Primary stability and the return after a failed reserve are in "How fast to switch".','Любое изменение отвязывает значения от ползунка («Пользовательская») и включает режим «Вручную». Стабильность основного и возврат после отказа резерва — в «Как быстро переключать».'],theta:['Model confidence that the outage lasts ≥ 20 s more. Higher leaves later, errs less.','Уверенность модели, что сбой продлится ещё ≥ 20 с. Выше — уходит позже, реже ошибается.'],dur_b:['Mean length of an outage the model treats as passing. Longer rides out longer.','Средняя длина обрыва, который модель считает переходящим. Больше — дольше пережидает.'],pg:['How sure the model must be that the primary is healthy before returning.','Насколько модель должна быть уверена, что основной здоров, чтобы вернуться.'],primary_stable:['Seconds the primary must be stable before the planned return.','Сколько секунд основной должен быть стабилен до планового возврата.'],rescue_stable:['If the reserve itself fails: return to the primary after this many stable seconds.','Если упал сам резерв: вернуться на основной после стольких секунд его стабильности.']};
var EXPERT_UI=function(env){
  var t=env.t,esc=env.esc,HV=env.HV,XD=env.XD,ADV=env.ADV,$$=env.$$,advNum=env.advNum,F=EXPERT_FIELDS;
  function by(k){return F.filter(function(f){return f.k===k;})[0];}
  function cur(f){var v=(HV.inv.settings||{})[f.k];return v===undefined||v===null?f.d:v;}
  function val(f){return Object.prototype.hasOwnProperty.call(XD.ed,f.k)?XD.ed[f.k]:cur(f);}
  function on(f){return !f.dep||val(by(f.dep[0]))===f.dep[1];}
  function changed(){return F.filter(function(f){return Object.prototype.hasOwnProperty.call(XD.ed,f.k)&&XD.ed[f.k]!==cur(f);});}
  function ok(f,v){return f.ty!=='n'||(Number.isInteger(v)&&(v>=f.min&&v<=f.max||(f.z&&v===0)));}
  function unit(f){return f.u?' '+t(f.u[1],f.u[0]):'';}
  function range(f){return f.ty==='n'?(f.z?'0 '+t('или','or')+' ':'')+f.min+'–'+f.max+unit(f):f.ty==='b'?t('вкл / выкл','on / off'):f.o.map(function(o){return t(o[1][1],o[1][0]);}).join(' / ');}
  function txt(f,v){var o=f.ty==='s'?f.o.filter(function(x){return x[0]===v;})[0]:null;return f.ty==='b'?(v?t('вкл','on'):t('выкл','off')):o?t(o[1][1],o[1][0]):v+unit(f);}
  function field(f){
    var v=val(f),id='xd-'+f.k,off=!on(f),c,dm=v===f.d?t('по умолчанию','default'):t('по умолчанию: ','default: ')+txt(f,f.d);
    if(f.ty==='b')c='<input class="tg" type="checkbox" id="'+id+'" data-xd="'+f.k+'"'+(v?' checked':'')+(off?' disabled':'')+'>';
    else if(f.ty==='s')c='<select id="'+id+'" data-xd="'+f.k+'">'+f.o.map(function(o){return '<option value="'+o[0]+'"'+(v===o[0]?' selected':'')+'>'+esc(t(o[1][1],o[1][0])+(o[0]===f.d?' ('+t('по умолчанию','default')+')':''))+'</option>';}).join('')+'</select>';
    else c='<span><input type="number" id="'+id+'" data-xd="'+f.k+'" min="'+(f.z?0:f.min)+'" max="'+f.max+'" step="1" value="'+(Number.isFinite(v)?v:'')+'"'+(off?' disabled':'')+'><span class="small mute">'+esc(unit(f))+'</span></span>';
    return '<div class="f xdf" data-k="'+f.k+'"><label for="'+id+'">'+esc(t(f.l[1],f.l[0]))+' <span class="dm'+(v===f.d?'':' chg')+'">'+esc(dm)+'</span></label>'+c+
      '<div class="h">'+esc(t(f.h[1],f.h[0]))+' · '+t('допустимо: ','allowed: ')+esc(range(f))+(f.stop?' · <b>'+t('нужен выключенный Auto','needs Auto off')+'</b>':'')+'</div></div>';
  }
  function sum(){var n=F.filter(function(f){return cur(f)!==f.d;}).length;
    return n?t('отличается от умолчаний: '+n+' из '+F.length,n+' of '+F.length+' differ from the defaults'):t('все '+F.length+' настроек по умолчанию','all '+F.length+' settings at their defaults');}
  function body(){
    return '<p class="small">'+t('Тонкие настройки детектора и датчиков. Значения по умолчанию подобраны исследованием; меняйте, только понимая зачем. Отправляются только изменённые поля; сохранение Auto не включает.','Fine settings of the detector and the sensors. The defaults come from the research; change them only knowing why. Only the fields you changed are sent; saving does not turn Auto on.')+'</p>'+
      (env.needsStop()?'<p class="note warn">'+t('Auto сейчас работает. Поля с пометкой «нужен выключенный Auto» при сохранении потребуют его остановить: программа предложит это сама, а включать Auto обратно вы будете сами.','Auto is running now. Fields marked "needs Auto off" require stopping it when saved: the page offers that itself, and you turn Auto back on yourself.')+'</p>':'')+
      EXPERT_GROUPS.map(function(g,i){return '<h3 class="xdh">'+esc(t(g.h[1],g.h[0]))+'</h3><p class="tiny mute">'+esc(t(g.b[1],g.b[0]))+'</p>'+F.filter(function(f){return f.g===i;}).map(field).join('');}).join('')+
      env.saveBar('xdet',t('Поля с пометкой «нужен выключенный Auto» сохраняются при остановленном Auto: при сохранении программа предложит его остановить.','Fields marked "needs Auto off" are saved with Auto stopped: saving offers to stop it.'));
  }
  function input(el,ev){
    var k=el.dataset.xd,f=by(k);if(!f)return;
    XD.ed[k]=f.ty==='b'?el.checked:f.ty==='n'?(el.value===''?NaN:Number(el.value)):el.value;
    var dirty=changed().length>0;HV.dirty.xdet=dirty;$$('[data-dirty="xdet"]',HV.root).forEach(function(x){x.hidden=!dirty;});
    if(ev&&ev.type==='change'){env.fill();if(f.ty!=='n'){var n=document.getElementById('xd-'+k);if(n)n.focus();}}
  }
  function prep(){
    var ch=changed();if(!ch.length){env.toast(t('Нечего сохранять: все поля такие, как на роутере.','Nothing to save: every field is as on the router.'));return null;}
    var bad=ch.filter(function(f){return !ok(f,XD.ed[f.k]);}).map(function(f){return [f,range(f)];});
    if(bad.length){env.modal({title:t('Не сохранено','Not saved'),body:'<p>'+t('Эти значения недопустимы, на роутер ничего не отправлено:','These values are not allowed; nothing was sent to the router:')+'</p><ul>'+bad.map(function(b){return '<li>'+esc(t(b[0].l[1],b[0].l[0]))+' — '+esc(b[1])+'</li>';}).join('')+'</ul>'+env.codeNotice('SETUP-RANGE')});return null;}
    return ch;
  }
  function send(ch){
    var d=env.draft(),good=function(r){if(!(r&&r.saved===true))throw {code:(r&&r.code)||'SETUP-SAVE-FAILED'};},
      FK=F.filter(function(f){return f.g===0;}),fl=ch.filter(function(f){return f.g===0;}),dt=ch.filter(function(f){return f.g>0;});
    var a=fl.length?env.rpcCall('setup_recovery',['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','rescue_stable','interval','failure_model'].concat(FK.map(function(f){return f.k.replace('recovery_','');})))
      .apply(null,[Number(d.fails),Number(d.resOk),Number(d.cooldown),Number(d.dwell),d.returnPolicy,Number(d.retOk),Number(d.stab),Number(d.attempts),Number(d.window),Number(d.rescue),Number(d.interval),d.failModel].concat(FK.map(val))).then(good):Promise.resolve();
    return a.then(function(){return dt.length?env.rpcCall('setup_detector',dt.map(function(f){return f.k;})).apply(null,dt.map(val)).then(good):0;});
  }
  /* ---- the fast end of the master slider ---- */
  function norm(s){return String(s).toLowerCase().replace(/ё/g,'е').replace(/[^a-zа-я0-9]+/g,' ').trim();}
  function ackOk(v){var n=norm(v);return EXPERT_ACK.some(function(p){return norm(p)===n;});}
  function fastRow(c,dis,td){
    var A=(ADV.curve&&ADV.curve.fast_anchors)||[];if(!A.length)return '';
    return '<div class="advseg fastseg" role="group" aria-label="'+t('Положения быстрее нуля','Positions faster than zero')+'"><span class="small mute">'+t('Быстрее «0»:','Faster than "0":')+'</span>'+
      A.map(function(a){var o=a.t<-0.25?c.turbo:c.fast;
        return '<button class="btn sm'+(o?'':' lock')+'" data-act="'+(o?'advpos':'advlock')+'" data-t="'+esc(String(Number(a.t)))+'"'+(o?' aria-pressed="'+(Math.abs(td-a.t)<0.005)+'"'+(dis?' disabled':''):' aria-label="'+advNum(a.t,1)+' · '+t('закрыто','locked')+'"')+'>'+(o?'':'🔒 ')+advNum(a.t,1)+'</button>';}).join('')+'</div>';
  }
  function fastAdmin(c){
    return '<div class="fastadm"><button class="tgl" role="switch" data-act="advfast" aria-checked="'+!!c.fast+'"><span class="trk"></span>'+t('Быстрый сегмент −0,1 … −0,2 (администратор)','Fast segment −0.1 … −0.2 (administrator)')+'</button>'+
      '<p class="small mute">'+t('Открывает два положения быстрее «0»: уход при 3 или 2 ошибках подряд. Сам позицию не меняет — выбираете вы. В симуляторе быстрые положения прошли зарегистрированные проверки; числа 18–29 % независимо не подтверждены. На роутере не проверено. Выключение вернёт ползунок к новому пределу, но только в спокойный момент.','Opens two positions faster than "0": leave after 3 or 2 failures in a row. It does not move the position itself — you choose. In the simulator the fast positions passed the registered checks; the 18–29 % figures are not independently confirmed. Not validated on the router. Turning it off moves the slider back to the new limit, but only in a calm moment.')+'</p>'+
      (c.turbo?'<p class="note warn">'+t('Турбо включено: доступны −0,3 … −0,7 (до ~8 лишних уходов в сутки, оценка ещё не измерена на роутере).','Turbo is on: −0.3 … −0.7 are available (up to ~8 unnecessary switches a day, an estimate not yet measured on a router).')+' <button class="btn sm" data-act="advturbooff">'+t('Выключить турбо','Turn turbo off')+'</button></p>':
        '<p class="row"><button class="btn sm" data-act="advturbo">🔒 '+t('Разблокировать турбо (−0,3 … −0,7)…','Unlock turbo (−0.3 … −0.7)…')+'</button></p>')+'</div>';
  }
  function note(p){
    return p&&p.cons_f!=null?'<p class="small mute">'+t('Быстрый сегмент: уход при ','Fast segment: leave after ')+esc(advNum(p.cons_f,0))+t(' ошибках подряд',' failures in a row')+(p.beat_k!=null?' · '+t('пульс: ','heartbeat: ')+esc(advNum(p.beat_k,0))+t(' потерянных ударов',' lost beats'):'')+' · '+t('плотная проба ','dense probe ')+esc(advNum(p.dense_interval,0))+' '+t('с','s')+'.</p>':'';
  }
  function turbo(s){
    env.modal({title:t('Разблокировать турбо?','Unlock turbo?'),body:'<p>'+t('Турбо уходит на резерв ещё раньше, но платой за это — лишние переключения: до ~8 в сутки. Это предварительная оценка, на роутере она ещё не измерена (симулятор: −0,3: ≈1,3; −0,5: ≈3,1; −0,7: ≈4,7; на «0» ≈0,5). Каждое лишнее переключение — короткая заминка и разрыв части соединений.','Turbo leaves for the reserve even earlier, and the price is unnecessary switches: up to ~8 a day. This is an exploratory estimate, not yet measured on a router (simulator: −0.3: ≈1.3; −0.5: ≈3.1; −0.7: ≈4.7; at "0" ≈0.5). Every unnecessary switch is a short stall and breaks some connections.')+'</p><p>'+t('Советник турбо никогда не рекомендует и сам в него не выходит. Чтобы разблокировать, наберите свою фразу точно:','The advisor never recommends turbo and never moves into it. To unlock, type your phrase exactly:')+'</p><p class="mono small">'+esc(t(EXPERT_ACK[0],EXPERT_ACK[1]))+'</p><input type="text" class="inp" id="adv-ack" autocomplete="off" spellcheck="false" aria-label="'+t('Фраза подтверждения','Confirmation phrase')+'">',
      buttons:[{t:t('Отмена','Cancel'),cls:'ghost'},{t:t('Разблокировать турбо','Unlock turbo'),cls:'pri',id:'adv-ackgo',disabled:true,fn:function(){
        env.advRpc(function(){return env.rpcCall('advisor_settings',['mode','window','turbo','turbo_ack'])(s.mode,s.window_days,true,EXPERT_ACK_CODE);},t('Турбо разблокировано. Положения −0,3 … −0,7 доступны.','Turbo unlocked. Positions −0.3 … −0.7 are available.'));}}]});
  }
  function act(name,a,s){
    var c=s.current,set=function(args,msg){return env.advRpc(function(){return env.rpcCall('advisor_settings',['mode','window'].concat(Object.keys(args))).apply(null,[s.mode,s.window_days].concat(Object.keys(args).map(function(k){return args[k];})));},msg);};
    if(name==='advturbo'||(name==='advlock'&&Number(a.dataset.t)<-0.25)){turbo(s);return;}
    if(name==='advlock'){env.toast(t('Сначала включите «Быстрый сегмент» (переключатель ниже).','First turn on "Fast segment" (the switch below).'));return;}
    if(name==='advfast')return set({fast:!c.fast},c.fast?t('Быстрый сегмент выключен. Роутер подтвердил.','Fast segment turned off. Confirmed by the router.'):t('Быстрый сегмент включён. Положение выберите сами. Роутер подтвердил.','Fast segment turned on. Choose a position yourself. Confirmed by the router.'));
    if(name==='advturbooff')return set({turbo:false},t('Турбо выключено. Роутер подтвердил.','Turbo turned off. Confirmed by the router.'));
  }
  function hint(k){var h=EXPERT_HINTS[k];return h?t(h[1],h[0]):'';}
  /* Labels of the master-slider chart (P: points {x,y,n}; k:1 = the default marker, labelled here). The default marker comes first (it keeps
     its place beside the diamond), the named positions stack upwards around it. Each label takes the first free place: its preferred side and row, then the other side, then
     rows above and below; a label never covers another one nor leaves the chart. Width ~5.8 px per character at 10 px. */
  function chartLabels(P,W){
    var B=[],g='';
    P.forEach(function(p){
      var n=p.k?t('по умолчанию','default'):p.n,w=n.length*5.8,s0=p.k||p.x<=W/2?1:-1,C=[];
      (p.k?[0,-12,12,-24,24,36]:[0,-12,-24,-36,12,24,36]).forEach(function(o){[s0,-s0].forEach(function(s){var x=p.x+s*(p.k?9:8),x0=s>0?x:x-w;C.push([x,p.y+(p.k?4:-14)+o,s>0?'start':'end',x0,x0+w]);});});
      var q=C.filter(function(c){return c[3]>=50&&c[4]<=W-4&&c[1]>=14&&!B.some(function(b){return c[3]<b[1]&&c[4]>b[0]&&Math.abs(c[1]-b[2])<11;});})[0]||C[0];
      B.push([q[3],q[4],q[1]]);
      g+='<text class="lbl" x="'+q[0]+'" y="'+q[1]+'" text-anchor="'+q[2]+'">'+esc(n)+'</text>';
    });
    return g;
  }
  /* the 5-step training modal of the master slider (the page keeps only the call; step 2 draws the live curve) */
  function tour(i){
    var S=ADV_TOUR,s=S[i],v=env.VER();if(!s)throw new Error('UI-HELP-LOAD-FAILED');
    var body='<p class="tiny mute">'+t('Шаг ','Step ')+(i+1)+t(' из ',' of ')+S.length+'</p>'+t(s.b[1],s.b[0])+(i===1&&ADV.curve?env.advChart(0.5,0.3,true)+env.advLegend():'')+'<div class="dots" aria-hidden="true">'+S.map(function(_,j){return '<i class="'+(j===i?'on':'')+'"></i>';}).join('')+'</div><p class="tiny mute">HomenS.AI Auto VPN · '+esc(v.model)+' · <a href="https://homensai.com" target="_blank" rel="noopener noreferrer">'+t('Разработчик · Serhii Khomenko','Developer · Serhii Khomenko')+'</a> · '+esc(v.app)+' · '+esc(v.style)+'</p>';
    var b=[{t:t('Закрыть','Close')}];
    if(i>0)b.push({t:t('Назад','Back'),fn:function(){tour(i-1);}});
    b.push(i<S.length-1?{t:t('Дальше','Next'),cls:'pri',fn:function(){tour(i+1);}}:{t:t('Готово','Done'),cls:'pri'});
    env.modal({title:esc(t(s.h[1],s.h[0])),body:'<div class="advtour">'+body+'</div>',buttons:b});
  }
  // The recovery disclosure is optional; statistics and P95 calculations stay in the page.
  function recoveryStats(s){
  var f=function(v){return v==null?'—':advNum(v,1)+' '+t('с','s');},n=s.recovered_samples;
  return '<div class="filters" role="group" aria-label="'+t('Период','Period')+'">'+[['day',t('Сутки','Day')],['week',t('Неделя','Week')],['month',t('Месяц','Month')]].map(function(p){return '<button data-act="recper" data-p="'+p[0]+'" aria-pressed="'+(ADV.per===p[0])+'">'+p[1]+'</button>';}).join('')+'</div>'+
   '<div class="scrollx"><table class="tbl"><tbody>'+[[t('Попыток','Attempts'),s.attempts],[t('С известным итогом','Known outcome'),s.known_outcomes],[t('Измерений времени восстановления (n)','Recovery-time samples (n)'),n],[t('Медиана','Median'),f(s.median)],[n>=env.P95_MIN_N?t('P95 (оценка)','P95 (estimate)'):t('≈P95 (оценка)','≈P95 (estimate)'),env.p95Text(s.p95,n,f)],[t('Верхняя граница P95, уверенность 95 %','P95 upper bound, 95 % confidence'),env.p95UpperText(s.p95_upper,n,f)],[t('Максимум','Maximum'),env.p95MaxText(s.worst,n,f)]].map(function(r){return '<tr><td>'+esc(r[0])+'</td><td class="num">'+esc(String(r[1]))+'</td></tr>';}).join('')+'</tbody></table></div>'+
   (env.p95MaxClaim(s.worst,n,f)?'<p class="small" role="note">'+esc(env.p95MaxClaim(s.worst,n,f))+'</p>':'')+
   '<p class="tiny mute">'+t('P95 (оценка) — 95-й процентиль самой выборки, а не гарантия. Верхняя граница P95 с уверенностью 95 % считается отдельно и есть только при n ≥ 59. При меньшем n честно сказать можно лишь про максимум: с 95 % уверенностью он покрывает не меньше указанной доли случаев (≈P95 при n ≤ 19 — просто максимум).','P95 (estimate) is the 95th percentile of the sample itself, not a guarantee. The P95 upper bound with 95 % confidence is computed separately and exists only with n ≥ 59. With fewer samples only the maximum can be stated honestly: with 95 % confidence it covers at least the stated share of cases (≈P95 for n ≤ 19 is just the maximum).')+'</p>';
  }
  return {recoveryStats:recoveryStats,tour:tour,chartLabels:chartLabels,sum:sum,body:body,input:input,prep:prep,send:send,changed:changed,fastRow:fastRow,fastAdmin:fastAdmin,note:note,ackOk:ackOk,act:act,hint:hint};
};