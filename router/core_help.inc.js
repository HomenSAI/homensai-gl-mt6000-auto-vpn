// Help: the program core as a pyramid (Python base, Lua, C plan) and the fallback steps between the levels.
// Lazy Help module only. Facts and thresholds: docs/architecture/CORE-LEVELS-2026-10-31.ru.md (from the code).
function coreSvg(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});return n;}
function coreLevelsDiagram(){
  if(typeof document==='undefined'||!document.createElementNS)return E('p',{},'');
  var svg=coreSvg('svg',{viewBox:'0 0 1100 530',role:'img','aria-label':bi('Program core levels and fallback steps','Уровни ядра программы и переходы при сбое'),style:'width:100%;height:auto;display:block'});
  var defs=coreSvg('defs'),marker=coreSvg('marker',{id:'hv-core-arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});
  marker.appendChild(coreSvg('path',{d:'M0,0 L10,5 L0,10 z',fill:'#c0392b'}));defs.appendChild(marker);svg.appendChild(defs);
  function text(x,y,value,size,weight,fill,anchor){var n=coreSvg('text',{x:x,y:y,'text-anchor':anchor||'middle','font-size':size||13,'font-weight':weight||400,fill:fill||'currentColor'});n.textContent=value;svg.appendChild(n);}
  function tier(points,fill,dashed,lines,y){
    var attrs={points:points,fill:fill,stroke:'currentColor','stroke-opacity':.45};if(dashed)attrs['stroke-dasharray']='6 4';
    svg.appendChild(coreSvg('polygon',attrs));
    lines.forEach(function(t,i){text(420,y+i*23,t,i?14:18,i?400:700,'#14212e');});
  }
  function arrow(d,dashed){var attrs={d:d,fill:'none',stroke:'#c0392b','stroke-width':2,'marker-end':'url(#hv-core-arrow)'};if(dashed)attrs['stroke-dasharray']='6 4';svg.appendChild(coreSvg('path',attrs));}
  function note(x,y,lines,first){lines.forEach(function(t,i){text(x,y+i*18,t,i||!first?14:15,i||!first?400:700,i||!first?'currentColor':'#c0392b','start');});}
  tier('360,20 480,20 550,110 290,110','#e6e2f7',true,[bi('C · hv-core','C · hv-core'),bi('plan, not installed','план, не установлен')],64);
  tier('290,110 550,110 620,200 220,200','#bcd7ff',false,[bi('Lua · hv-core','Lua · hv-core'),bi('one process (lua_core_process)','один процесс (lua_core_process)')],150);
  tier('220,200 620,200 690,290 150,290','#b7efc5',false,[bi('Lua 5.1 · monitor + Auto','Lua 5.1 · монитор + Auto'),bi('two processes · ~20 MB, ~19 % CPU','два процесса · ~20 МБ, ~19 % ядра')],240);
  tier('150,290 690,290 760,380 80,380','#ffe9a8',false,[bi('Python 3.9 · the proven base','Python 3.9 · проверенное основание'),bi('agent.py · native_switch.py · ~78 MB, ~60 % CPU','agent.py · native_switch.py · ~78 МБ, ~60 % ядра')],330);
  arrow('M 322 66 C 200 66, 110 245, 180 245',true);
  note(14,88,[bi('plan: 3 crashes in 10 min','план: 3 падения за 10 мин'),bi('→ Lua Auto','→ Lua Auto')],false);
  arrow('M 590 155 C 700 155, 720 245, 662 245');
  note(780,122,['HV-CORE-FALLBACK',bi('3 failures in 600 s →','3 сбоя за 600 с →'),bi('two Lua processes','два Lua-процесса'),bi('watchdog: loop silent 120 s','сторож: цикл молчит 120 с')],true);
  arrow('M 660 245 C 770 245, 790 335, 732 335');
  note(780,226,['LUA-AUTO-FALLBACK',bi('Auto: 3 errors in 600 s','Auto: 3 ошибки за 600 с'),bi('→ native_switch.py','→ native_switch.py'),bi('no Lua answer to the page','страница без ответа Lua'),bi('→ agent.py answers','→ отвечает agent.py')],true);
  note(780,346,[bi('Python fails → procd','Python упал → procd'),bi('restarts it in 5 s','перезапустит за 5 с')],false);
  svg.appendChild(coreSvg('line',{x1:30,y1:362,x2:30,y2:214,stroke:'currentColor','stroke-width':2,'marker-end':'url(#hv-core-arrow)'}));
  text(14,204,bi('faster, lighter','быстрее, легче'),14,400,'currentColor','start');
  text(14,400,bi('tested longer','дольше проверено'),14,400,'currentColor','start');
  svg.appendChild(coreSvg('rect',{x:14,y:418,width:1072,height:104,rx:12,fill:'#f3f5f7',stroke:'currentColor','stroke-opacity':.35}));
  text(550,445,bi('Under every level: journal + rollback · VPN-only guard','Под всеми уровнями: журнал + откат · защита «только VPN»'),17,700,'#14212e');
  text(550,470,bi('Auto resumes after a power cut · homensai-vpn-emergency','Auto возвращается после обесточивания · homensai-vpn-emergency'),17,700,'#14212e');
  text(550,503,bi('The levels share one journal and the same files, so a lower level can take over at any moment.','Уровни ведут один журнал и одни файлы, поэтому нижний уровень может подхватить работу в любой момент.'),15,400,'#14212e');
  return svg;
}
function renderCoreLevels(){
  return E('div',{'class':'hv-core-levels'},[coreLevelsDiagram(),
    E('p',{},bi('Faster levels sit on top of slower, longer-tested ones. When a level fails, the work moves one step down. Every step leaves a code in the system log (logread -e homensai).','Быстрые уровни стоят на медленных, но дольше проверенных. Если уровень отказал, работа переходит на ступень ниже. Каждый переход оставляет код в журнале системы (logread -e homensai).')),
    E('ol',{'class':'hv-help-steps'},[
      [bi('Python 3.9 (base): agent.py checks the channels and answers the page, native_switch.py runs Auto. This is the released, longest-tested code; Lua and C are checked against it in tests with the same inputs. It is always installed and is the last step.','Python 3.9 (основание): agent.py проверяет каналы и отвечает странице, native_switch.py ведёт Auto. Это выпущенный и дольше всех проверенный код; Lua и C сверяются с ним в тестах на одних и тех же данных. Он всегда установлен и это последняя ступень.')],
      [bi('Lua 5.1 (two processes, options lua_monitor and lua_auto): the same files and codes with about 20 MB and 19 % of a core instead of about 78 MB and 60 % (MT3000).','Lua 5.1 (два процесса, параметры lua_monitor и lua_auto): те же файлы и коды, около 20 МБ и 19 % ядра вместо примерно 78 МБ и 60 % (MT3000).')],
      [bi('Lua hv-core (option lua_core_process): monitor and Auto in one process. 3 failures in 600 s → HV-CORE-FALLBACK, back to two Lua processes until the service restarts. If its loop is silent for 120 s, the watchdog restarts it (HV-CORE-WATCHDOG). Tested on a PC, not yet on the router.','Lua hv-core (параметр lua_core_process): монитор и Auto в одном процессе. 3 сбоя за 600 с → HV-CORE-FALLBACK, снова два Lua-процесса до перезапуска службы. Если цикл молчит 120 с, сторож перезапускает процесс (HV-CORE-WATCHDOG). Проверено на ПК, на роутере ещё нет.')],
      [bi('Lua Auto: 3 errors in 600 s → LUA-AUTO-FALLBACK, the Python native_switch.py takes over until the service restarts. A page request the Lua monitor cannot answer is answered by agent.py.','Lua Auto: 3 ошибки за 600 с → LUA-AUTO-FALLBACK, работу берёт Python native_switch.py до перезапуска службы. Запрос страницы, на который Lua-монитор не ответил, выполняет agent.py.')],
      [bi('One-call fallbacks: a Lua live check that fails internally is repeated by lua_bridge.py; the manual-switch field of the page comes from status_bridge.py, and until it answers the manual buttons stay blocked (PAIR-MANUAL-STATE-UNVERIFIED).','Запасные пути на один вызов: живая проверка, упавшая в Lua, повторяется через lua_bridge.py; поле ручного переключения на странице даёт status_bridge.py, а пока он не ответил, кнопки ручного переключения заблокированы (PAIR-MANUAL-STATE-UNVERIFIED).')],
      [bi('Exception: an instant manual switch written by Lua (option lua_core) is not retried in Python. It is refused and rolled back (LUA-CORE-UNAVAILABLE); press again or turn the option off.','Исключение: мгновенное ручное переключение, которое пишет Lua (параметр lua_core), не повторяется на Python. Оно отклоняется и откатывается (LUA-CORE-UNAVAILABLE); нажмите ещё раз или выключите параметр.')],
      [bi('C hv-core is a plan: built and checked read-only on the MT3000 (18 of 20 values equal to Lua), not installed. Planned rule: 3 crashes in 10 minutes → Lua Auto, which can then go to Python.','C hv-core — план: собран и проверен на MT3000 только чтением (18 из 20 значений совпали с Lua), не установлен. Задуманное правило: 3 падения за 10 минут → Lua Auto, а он при сбоях — на Python.')],
      [bi('Return to the faster level: /etc/init.d/homensai-vpn restart starts the levels chosen in the options again (the error count in RAM remembers the last 10 minutes). To stay on Python, set the Lua option to 0.','Возврат на быстрый уровень: /etc/init.d/homensai-vpn restart снова запускает уровни, выбранные в параметрах (счётчик ошибок в ОЗУ помнит последние 10 минут). Чтобы остаться на Python, поставьте параметр Lua в 0.')]
    ].map(function(t){return E('li',{},E('p',{},t[0]));}))]);
}
HELP_TOPICS.push({id:'program-core',open:false,title:['Program core: Python, Lua and C levels','Ядро программы: уровни Python, Lua и C'],
  when:['You want to know which language runs the router part and what happens when a faster level fails.','Вы хотите знать, на чём работает часть программы на роутере и что происходит, если быстрый уровень отказал.'],
  steps:[{t:['Python 3.9 is the proven base; Lua runs on top of it (two processes, or one hv-core process); C is planned. On a failure the work moves one level down: hv-core 3 failures in 600 s → HV-CORE-FALLBACK (two Lua processes); Lua Auto 3 errors in 600 s → LUA-AUTO-FALLBACK (Python native_switch.py); a page request without a Lua answer → agent.py. Journal, rollback, the VPN-only guard and Auto resume work on every level.','Python 3.9 — проверенное основание; над ним Lua (два процесса или один процесс hv-core); C — в плане. При сбое работа переходит на уровень ниже: hv-core 3 сбоя за 600 с → HV-CORE-FALLBACK (два Lua-процесса); Lua Auto 3 ошибки за 600 с → LUA-AUTO-FALLBACK (Python native_switch.py); запрос страницы без ответа Lua → agent.py. Журнал, откат, защита «только VPN» и возобновление Auto работают на любом уровне.']}],
  custom:renderCoreLevels});
