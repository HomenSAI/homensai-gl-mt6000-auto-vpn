/* Interactive training: lesson cards, then a quiz with checkboxes, a score and "take again". Data are [English, Russian] pairs. */
var LEARN_LESSONS=[
  {
    "icon": "①",
    "title": [
      "What this system is",
      "Что это за система"
    ],
    "body": [
      [
        "The application monitors existing OpenVPN/WireGuard clients. Primary and reserve are roles, not protocol names. Configure servers and keys in the stock GL.iNet VPN app.",
        "Приложение наблюдает за существующими клиентами OpenVPN/WireGuard. Основной и резервный — роли, а не названия протоколов. Серверы и ключи настраиваются в штатном VPN-приложении GL.iNet."
      ],
      [
        "On the prepared supported MT3000, explicit Auto Start can start the saved pair and select its traffic policy. It recovers after confirmed failure; primary return follows the saved policy and operator preference.",
        "На подготовленном поддерживаемом MT3000 явный запуск Auto может подключить сохранённую пару и выбрать политику её трафика. Восстановление происходит после подтверждённого отказа; возврат зависит от сохранённой политики и ручного предпочтения."
      ]
    ],
    "example": [
      "Example: primary fails repeatedly → healthy reserve is confirmed → its route is selected. Return follows policy.",
      "Пример: повторный отказ основного → подтверждён исправный резерв → выбран его маршрут. Возврат зависит от политики."
    ],
    "tip": [
      "Only a saved, validated pair is managed; no credentials are created.",
      "Управляется только сохранённая проверенная пара; учётные данные не создаются."
    ]
  },
  {
    "icon": "②",
    "title": [
      "Before you start: two ways to connect",
      "Перед началом: два способа подключения"
    ],
    "body": [
      [
        "Prepare two ways to reach the router: a laptop connected by a LAN cable, and a device on the same router’s Wi-Fi (preferably a separate phone). Verify both reach the intended device before the first tests.",
        "Подготовьте два способа попасть на роутер: ноутбук, подключённый кабелем LAN, и устройство в Wi-Fi того же роутера (лучше отдельный телефон). Перед первыми тестами проверьте, что оба пути ведут к нужному устройству."
      ],
      [
        "The cable is the reliable path for tests: it does not depend on Wi-Fi. Wi-Fi shows what your family devices will really experience. A second local path can help if the first fails, but does not guarantee access if the router itself is unavailable. Two adapters with the same subnet can reach different routers; do not send credentials until the management path is verified.",
        "Кабель — надёжный путь для тестов: он не зависит от Wi-Fi. Wi-Fi показывает, что реально увидят устройства домашних. Второй локальный путь помогает при отказе первого, но не гарантирует доступ при сбое самого роутера. Два адаптера с одинаковой подсетью могут вести к разным роутерам; до ввода пароля проверьте путь управления."
      ],
      [
        "Also keep mobile data on your phone: it works even when the router VPN is broken.",
        "Также держите мобильный интернет на телефоне: он работает, даже если VPN роутера сломан."
      ]
    ],
    "example": [
      "Example: laptop on the cable runs the check; the phone on Wi-Fi opens a site to confirm that Wi-Fi users have internet too.",
      "Пример: ноутбук на кабеле запускает проверку; телефон по Wi-Fi открывает сайт, чтобы подтвердить, что интернет есть и у пользователей Wi-Fi."
    ],
    "tip": [
      "Never test only from one device that you cannot afford to lose.",
      "Не тестируйте только с одного устройства, которое нельзя потерять."
    ]
  },
  {
    "icon": "③",
    "title": [
      "First start",
      "Первый запуск"
    ],
    "body": [
      [
        "The current terms appear until first acceptance on this router. Acceptance is followed by the introduction and the eight-step setup; training can be reopened later.",
        "Условия текущей версии показываются до первого принятия на этом роутере. Далее открываются объяснение и мастер из восьми шагов; к обучению можно вернуться позже."
      ],
      [
        "Monitoring runs independently of Auto. On Overview, monitoring and Check VPN now are inside the top Auto card. A fresh monitor report is not proof that a client has internet.",
        "Мониторинг работает отдельно от Auto. На «Обзоре» его индикатор и «Проверить VPN сейчас» находятся в верхнем блоке Auto. Свежий отчёт монитора ещё не доказывает доступность интернета у клиента."
      ]
    ],
    "example": [
      "A green monitoring lamp means fresh observations; Auto still needs an explicit Start.",
      "Зелёный индикатор мониторинга означает свежие наблюдения; для Auto нужен отдельный явный запуск."
    ],
    "tip": [
      "Grey means switched off, red means switched on but not working: open Help.",
      "Серый — выключен, красный — включён, но не работает: откройте «Помощь»."
    ]
  },
  {
    "icon": "④",
    "title": [
      "Setup",
      "Настройка"
    ],
    "body": [
      [
        "Settings → All application settings → 3 · Existing VPNs: choose two different configured clients. Each choice represents the profile already assigned to that client; two servers of one client are not two independent channels.",
        "«Настройки → Все настройки приложения → 3 · Существующие VPN»: выберите два разных настроенных клиента. Каждый вариант — уже назначенный этому клиенту профиль; два сервера одного клиента не являются двумя независимыми каналами."
      ],
      [
        "To change a VPN server or protocol binding, use the stock VPN page and refresh Auto VPN. Saving the pair changes application metadata; it does not import keys or change server credentials.",
        "Для смены VPN-сервера или привязки протокола используйте штатную VPN-страницу и обновите Auto VPN. Сохранение пары меняет метаданные приложения, не импортирует ключи и не меняет данные провайдера."
      ],
      [
        "Recovery policy is step 5. Speed tests (6) and Telegram (7) are optional. Review in step 8; saving never starts Auto.",
        "Правила восстановления — шаг 5. Тесты скорости (6) и Telegram (7) необязательны. Проверьте итог на шаге 8; сохранение не включает Auto."
      ]
    ],
    "example": [
      "Example: M (main) = Germany · WireGuard; R (reserve) = Netherlands · OpenVPN.",
      "Пример: M (основной) = Германия · WireGuard; R (резервный) = Нидерланды · OpenVPN."
    ],
    "tip": [
      "The bot token is a secret. Never post it or send it to anyone.",
      "Токен бота — секрет. Никому не публикуйте и не отправляйте его."
    ]
  },
  {
    "icon": "⑤",
    "title": [
      "Step 1: check the VPNs, Step 2: turn on Auto",
      "Шаг 1: проверить VPN, шаг 2: включить Auto"
    ],
    "body": [
      [
        "On Overview press “Step 1 · Check the VPNs now”. It tests right away which connected VPNs give internet. Fix problems first.",
        "На «Обзоре» нажмите «Шаг 1 · Проверить VPN сейчас». Сразу проверит, какие подключённые VPN дают интернет. Сначала устраните проблемы."
      ],
      [
        "Step 2: use the readiness list for your actual mode. Prepared-MT3000 router-probed IPv4 Auto checks the two channels on the router; a LAN helper is optional for additional client-path proof. A separate client-confirmed trial requires its own helper. Start Auto only when your mode is ready.",
        "Шаг 2: выполните список готовности своего режима. Router-probed IPv4 Auto подготовленного MT3000 проверяет два канала самим роутером; LAN-помощник нужен только для дополнительной проверки пути клиента. Отдельный тест с подтверждением клиента требует помощника. Включайте Auto после готовности своего режима."
      ],
      [
        "What is the LAN helper? A small PowerShell 7 script (plain text, you can read it) that runs on your Windows computer, not on the router. Install PowerShell 7 once, put the two downloaded files in one folder and start the launcher, then choose mode 1 (check only) first:",
        "Что такое LAN-помощник? Небольшой скрипт PowerShell 7 (обычный текст, его можно прочитать), который запускается на вашем компьютере с Windows, а не на роутере. Один раз установите PowerShell 7, положите два скачанных файла в одну папку и запустите, сначала выберите режим 1 (только проверка):"
      ],
      [
        "The Auto light: green — watching the primary; yellow — switching; orange — working on the reserve; red — needs your attention; grey — off.",
        "Светофор Auto: зелёный — следит за основным; жёлтый — переключается; оранжевый — работает на резерве; красный — нужно ваше внимание; серый — выключен."
      ]
    ],
    "cmds": [
      [
        "winget install Microsoft.PowerShell",
        [
          "Once: installs PowerShell 7 (Windows 10/11).",
          "Один раз: устанавливает PowerShell 7 (Windows 10/11)."
        ]
      ],
      [
        "pwsh -NoProfile -File .\\start-lan-helper.ps1",
        [
          "In the folder with the two downloaded files: starts the launcher.",
          "В папке с двумя скачанными файлами: запускает программу запуска."
        ]
      ]
    ],
    "example": [
      "Example: “2 of 2 VPNs work” confirms router observations for both paths; it does not certify every LAN client.",
      "Пример: «работают 2 из 2 VPN» подтверждает проверки обоих путей роутером, но не сертифицирует каждого клиента LAN."
    ],
    "tip": [
      "Do not turn Auto on when you cannot afford a short interruption (a call, a download).",
      "Не включайте Auto, когда нельзя терпеть короткий перерыв (звонок, загрузка)."
    ]
  },
  {
    "icon": "⑥",
    "title": [
      "Reading the pages",
      "Как читать страницы"
    ],
    "body": [
      [
        "Overview starts with Auto and the VPN check. Manual primary/reserve controls follow the collapsed technical and switching-statistics blocks. A queued command remains pending until the router confirms it.",
        "«Обзор» начинается с Auto и проверки VPN. Далее идут свёрнутые технические действия/статистика переключений и ручной выбор основного/резерва. Команда в очереди ожидает подтверждения роутера."
      ],
      [
        "Channels and servers shows primary first and reserve second, server names/IP where observed, HTTPS delay and a 1–24h history. Other servers and excess table rows expand with a triangle. A lower-delay recommendation does not switch traffic.",
        "«Каналы и серверы» показывает сначала основной, затем резервный, имена/IP при наличии наблюдения, HTTPS-задержку и историю 1–24 ч. Другие серверы и лишние строки раскрываются треугольником. Рекомендация меньшей задержки сама не переключает трафик."
      ],
      [
        "The live log groups repeated states into time ranges; its clock updates every second, network checks keep their configured cadence. Events shows the latest 20 rows, with expansion, search and sorting. Setup step 2 or Monitoring settings selects 1–2000 live observations and 1–7 days of detail. M/R identifies primary/reserve and who initiated a transition; missing historical outcomes are explained, not invented.",
        "Живой журнал объединяет повторы в диапазоны времени; часы обновляются раз в секунду, сетевые проверки сохраняют свой интервал. «События и ошибки» показывает последние 20 строк, раскрытие, поиск и сортировку. В шаге 2 мастера или настройках мониторинга выбираются 1–2000 наблюдений и 1–7 дней подробностей. M/R обозначает основной/резервный и инициатора перехода; для потерянных итогов указана причина, результат не выдумывается."
      ]
    ],
    "example": [
      "One outage may contain many failed checks. The failure chart counts the episode once.",
      "Один отказ может содержать много неудачных проверок. График отказов считает эпизод один раз."
    ],
    "tip": [
      "Speed tests are optional and use traffic; they live under Advanced settings → Tests.",
      "Тесты скорости необязательны и расходуют трафик; они в «Расширенные настройки» → «Тесты»."
    ]
  },
  {
    "icon": "⑦",
    "title": [
      "If the internet is gone",
      "Если пропал интернет"
    ],
    "body": [
      [
        "Keep access to the router by cable or Wi-Fi and inspect the selected channel, current measurements and the recorded reason. Use Help → No internet.",
        "Сохраните доступ к роутеру по кабелю или Wi-Fi и проверьте выбранный канал, свежие измерения и записанную причину. Откройте «Помощь» → «Нет интернета»."
      ],
      [
        "Switch manually only when the requested channel is confirmed ready and its action is available. Working on reserve alone is not a reason to force a return to a failed primary. Auto can remain on during normal manual selection.",
        "Переключайте вручную только при подтверждённой готовности нужного канала и доступной команде. Работа на резерве сама по себе не повод возвращаться на неисправный основной. При обычном ручном выборе Auto может оставаться включённым."
      ],
      [
        "Use emergency commands only for the documented recovery situation. Start with read-only show; removing the owned guard is a recovery action, not a general internet fix.",
        "Аварийные команды нужны только для описанного случая восстановления. Начните с чтения show; удаление собственной блокировки — восстановительное действие, а не универсальный ремонт интернета."
      ]
    ],
    "cmds": [
      [
        "homensai-vpn-emergency show",
        [
          "Only reads the state. Always safe.",
          "Только читает состояние. Всегда безопасно."
        ]
      ],
      [
        "homensai-vpn-emergency stop-auto",
        [
          "Stops own services; managed restoration may change the selected policy or owned interface flags.",
          "Останавливает собственные службы; управляемое восстановление может изменить выбранную политику и флаги собственных интерфейсов."
        ]
      ],
      [
        "homensai-vpn-emergency remove-guard",
        [
          "Removes only the program’s own traffic block.",
          "Снимает только собственную блокировку трафика программы."
        ]
      ]
    ],
    "example": [
      "Reserve works and primary is failing: keep the working route and diagnose the primary.",
      "Резерв работает, основной неисправен: сохраните работающий маршрут и проверьте основной."
    ],
    "tip": [
      "Reading with `show` is always safe; run the other commands only when you need to.",
      "Чтение командой `show` всегда безопасно; остальные команды запускайте, только когда нужно."
    ]
  },
  {
    "icon": "⑧",
    "title": [
      "Safety rules",
      "Правила безопасности"
    ],
    "body": [
      [
        "This is experimental software: it can interrupt your internet. You use it at your own risk and keep another way to reach the router.",
        "Это экспериментальное ПО: оно может прервать интернет. Вы используете его на свой риск и сохраняете другой способ попасть на роутер."
      ],
      [
        "Never share the router password, the Telegram token, VPN files or backups with anyone, including chats and support. After tests, change the router password if you typed it anywhere.",
        "Никому не передавайте пароль роутера, токен Telegram, VPN-файлы и резервные копии, в том числе в чатах и поддержке. После тестов смените пароль роутера, если вводили его где-либо."
      ],
      [
        "With Auto off, monitoring still probes and saves statistics; it does not automatically select another route. Training is not readiness certification.",
        "При выключенном Auto мониторинг продолжает проверки и запись статистики; автоматически другой маршрут не выбирается. Обучение не подтверждает техническую готовность."
      ]
    ],
    "example": [
      "Example: a person asks in a chat for your token “to help”. Do not send it.",
      "Пример: в чате просят ваш токен «чтобы помочь». Не отправляйте."
    ],
    "tip": [
      "You can come back to this training at any time from the menu.",
      "К этому обучению можно вернуться в любой момент из меню."
    ]
  }
];
var LEARN_QUIZ=[
  {q:['What does the system do when Auto is OFF?','Что делает система при выключенном Auto?'],o:[['Only watches and shows the state of your VPNs','Только наблюдает и показывает состояние ваших VPN',true],['Switches to the reserve VPN by itself','Сама переключается на резервный VPN',false],['Creates new VPN profiles','Создаёт новые VPN-профили',false]]},
  {q:['Which ways to connect should you prepare for the first tests? (several answers)','Какие способы подключения нужно подготовить для первых тестов? (несколько ответов)'],o:[['A laptop on a LAN cable','Ноутбук на кабеле LAN',true],['A device on Wi-Fi','Устройство по Wi-Fi',true],['Only one device that you cannot lose','Только одно устройство, которое нельзя потерять',false],['Mobile data on the phone','Мобильный интернет на телефоне',true]]},
  {q:['What is the right order to start working?','Каков правильный порядок начала работы?'],o:[['Accept the terms, start the monitor, check the VPNs, then turn on Auto','Принять условия, запустить мониторинг, проверить VPN, затем включить Auto',true],['Turn on Auto first, check later','Сначала включить Auto, проверить потом',false],['Skip the terms and start Auto','Пропустить условия и сразу запустить Auto',false]]},
  {q:['What must pass before Auto can be started?','Что должно пройти перед запуском Auto?'],o:[['The readiness checks for the selected mode; the helper is mandatory only for a client-confirmed trial','Проверки готовности выбранного режима; помощник обязателен только для теста с подтверждением клиента',true],['A speed test','Тест скорости',false],['A Telegram message','Сообщение в Telegram',false]]},
  {q:['The Auto light is orange. What does it mean?','Светофор Auto оранжевый. Что это значит?'],o:[['Traffic works on the reserve','Трафик идёт через резерв',true],['Everything is on the primary','Всё идёт через основной',false],['Auto is off','Auto выключен',false]]},
  {q:['Which of these is a secret that you never send to anyone? (several answers)','Что из этого — секрет, который никому нельзя отправлять? (несколько ответов)'],o:[['The Telegram bot token','Токен Telegram-бота',true],['The router password','Пароль роутера',true],['The country of a VPN server','Страна VPN-сервера',false]]},
  {q:['The internet is gone. What do you do first?','Интернета нет. Что делаете сначала?'],o:[['Open the router page, inspect fresh checks and follow No internet Help','Открываете страницу роутера, проверяете свежие данные и справку «Нет интернета»',true],['Flash the router firmware','Прошиваете роутер',false],['Delete all VPN profiles','Удаляете все VPN-профили',false]]},
  {q:['Which command only reads the state and is always safe?','Какая команда только читает состояние и всегда безопасна?'],o:[['homensai-vpn-emergency show','homensai-vpn-emergency show',true],['homensai-vpn-emergency stop-auto','homensai-vpn-emergency stop-auto',false],['homensai-vpn-emergency remove-guard','homensai-vpn-emergency remove-guard',false]]}
];
// A question is correct only when the chosen set equals the set of right options.
function learnGrade(question,chosen){
  var ok=true;
  var marks=question.o.map(function(option,index){
    var picked=chosen.indexOf(index)>=0,right=option[2]===true;
    if(picked!==right)ok=false;
    return picked&&right?'right':picked&&!right?'wrong':!picked&&right?'missed':'none';
  });
  return {ok:ok&&chosen.length>0,marks:marks};
}
function learnScore(quiz,answers){
  var correct=0;
  quiz.forEach(function(question,index){if(learnGrade(question,answers[index]||[]).ok)correct++;});
  return {correct:correct,total:quiz.length,percent:quiz.length?Math.round(correct*100/quiz.length):0};
}
function learnVerdict(percent){
  if(percent>=80)return bi('Training passed. Router readiness and permission to start Auto are checked separately.','Обучение пройдено. Готовность роутера и разрешение запуска Auto проверяются отдельно.');
  if(percent>=50)return bi('Almost there. Read the cards again before you turn on Auto.','Почти. Перечитайте карточки, прежде чем включать Auto.');
  return bi('Please go through the cards again before you use the system.','Пожалуйста, пройдите карточки ещё раз, прежде чем пользоваться системой.');
}
function learnSeen(){try{return window.localStorage.getItem('homensai-vpn-learn-seen')==='1';}catch(e){return false;}}
function learnMarkSeen(){try{window.localStorage.setItem('homensai-vpn-learn-seen','1');}catch(e){}}
function renderLearn(){
  var host=E('section',{'class':'hv-chart-card hv-learn'});
  var scene=null;
  var mode=learnSeen()?'toc':'flow',visited=[],step=0,answers=[],checked=false,generation=0,total=LEARN_LESSONS.length+LEARN_QUIZ.length+1;
  function clear(){if(scene&&scene.hvDispose)scene.hvDispose();scene=null;while(host.firstChild)host.removeChild(host.firstChild);}
  function inline(text){return richText(text);}
  function progress(){return E('div',{'class':'hv-learn-progress','role':'progressbar','aria-valuemin':'0','aria-valuemax':String(total),'aria-valuenow':String(step+1)},[E('span',{'style':'width:'+Math.round((step+1)*100/total)+'%'}),E('small',{},bi('Step ','Шаг ')+(step+1)+' / '+total)]);}
  function nav(back,next,nextLabel,nextDisabled){
    var shown=generation,used=false;
    function action(fn,disabled){return function(){if(disabled||used||generation!==shown)return;used=true;return fn();};}
    return E('div',{'class':'hv-learn-nav'},[back?E('button',{'type':'button','class':'cbi-button','click':action(back,false)},bi('Back','Назад')):E('span'),next?E('button',{'type':'button','class':'cbi-button cbi-button-action','disabled':nextDisabled?'disabled':null,'click':action(next,nextDisabled)},nextLabel):E('span')]);
  }
  function go(index){if(!Number.isInteger(index)||index<0||index>=total)return;mode='flow';step=index;checked=false;draw();}
  function chips(){
    var items=LEARN_LESSONS.map(function(l,i){return E('button',{'type':'button','class':'hv-chip'+(step===i?' hv-chip-current':'')+(visited[i]?' hv-chip-visited':''),'title':bi(l.title[0],l.title[1]),'aria-label':bi(l.title[0],l.title[1]),'click':function(){go(i);}},String(i+1));});
    items.push(E('button',{'type':'button','class':'hv-chip hv-chip-quiz'+(step>=LEARN_LESSONS.length?' hv-chip-current':''),'title':bi('Questions','Вопросы'),'click':function(){go(LEARN_LESSONS.length);}},'?'));
    return E('div',{'class':'hv-chips'},[E('button',{'type':'button','class':'cbi-button hv-chip-contents','click':function(){mode='toc';draw();}},bi('☰ Contents','☰ Оглавление'))].concat(items));
  }
  function toc(){
    var rows=LEARN_LESSONS.map(function(l,i){return E('button',{'type':'button','class':'hv-toc-item'+(visited[i]?' hv-toc-visited':''),'click':function(){go(i);}},[E('span',{'class':'hv-toc-num','aria-hidden':'true'},String(i+1)),E('span',{'class':'hv-toc-text'},[E('strong',{},bi(l.title[0],l.title[1])),E('small',{},bi(l.body[0][0].split('. ')[0]+'.',l.body[0][1].split('. ')[0]+'.'))])]);});
    rows.push(E('button',{'type':'button','class':'hv-toc-item hv-toc-quiz','click':function(){answers=[];go(LEARN_LESSONS.length);}},[E('span',{'class':'hv-toc-num','aria-hidden':'true'},'?'),E('span',{'class':'hv-toc-text'},[E('strong',{},bi('Questions and your score','Вопросы и ваша оценка')),E('small',{},bi('Check what you remember.','Проверьте, что вы запомнили.'))])]));
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('h2',{},bi('Contents','Оглавление')),E('p',{'class':'hv-learn-intro'},learnSeen()?bi('You have finished the training once. Open any topic you need, in any order.','Вы уже прошли обучение один раз. Открывайте любую тему, в любом порядке.'):bi('Open any topic, or read them one after another starting with 1. The first full pass takes about 5 minutes.','Откройте любую тему или читайте по порядку, начиная с 1. Первый полный проход занимает около 5 минут.')),E('div',{'class':'hv-toc'},rows)]));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){visited=[];answers=[];go(0);}},bi('Start from the beginning','Начать с самого начала')),E('span')]));
  }
  function lesson(){
    var l=LEARN_LESSONS[step];visited[step]=true;
    host.appendChild(chips());host.appendChild(progress());
    if(step===0)host.appendChild(E('p',{'class':'hv-learn-intro'},bi('A short training, about 5 minutes: what the system is, how to set it up and use it, and what to do when something goes wrong. At the end there are questions.','Короткое обучение, около 5 минут: что это за система, как её настроить и использовать и что делать, если что-то пошло не так. В конце — вопросы.')));
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},l.icon),E('h2',{},bi(l.title[0],l.title[1])),
      E('div',{'class':'hv-learn-body'},l.body.map(function(p){return E('p',{},inline(bi(p[0],p[1])));})),
      l.cmds?E('div',{'class':'hv-learn-cmds'},l.cmds.map(function(c){return E('div',{'class':'hv-learn-cmd'},[E('p',{},bi(c[1][0],c[1][1])),helpCommand(c[0])]);})):null,
      E('p',{'class':'hv-learn-example'},inline(bi(l.example[0],l.example[1]))),
      E('p',{'class':'hv-learn-tip'},[E('strong',{},bi('Remember: ','Запомните: ')),inline(bi(l.tip[0],l.tip[1]))])]));
    if(typeof renderLearnScene==='function'){scene=renderLearnScene(step);host.appendChild(scene);}
    host.appendChild(nav(step>0?function(){step--;draw();}:null,function(){step++;draw();},step===LEARN_LESSONS.length-1?bi('To the questions','К вопросам'):bi('Next','Дальше')));
  }
  function question(){
    var index=step-LEARN_LESSONS.length,q=LEARN_QUIZ[index],chosen=answers[index]||(answers[index]=[]),shown=generation;
    var grade=checked?learnGrade(q,chosen):null;
    host.appendChild(chips());host.appendChild(progress());
    var options=q.o.map(function(option,i){
      var mark=grade?grade.marks[i]:'none';
      var box=E('input',{'type':'checkbox','disabled':checked?'disabled':null,'change':function(){if(checked||generation!==shown)return;var at=chosen.indexOf(i);if(box.checked&&at<0)chosen.push(i);if(!box.checked&&at>=0)chosen.splice(at,1);draw();}});
      box.checked=chosen.indexOf(i)>=0;
      var note=mark==='right'?bi('Correct','Верно'):mark==='wrong'?bi('Wrong choice','Неверный выбор'):mark==='missed'?bi('This was a correct answer','Это был правильный ответ'):'';
      return E('label',{'class':'hv-quiz-option hv-quiz-'+mark},[box,(/^homensai-vpn-emergency /.test(option[0])?E('code',{'class':'hv-code'},option[0]):E('span',{},bi(option[0],option[1]))),note?E('small',{},note):null].filter(Boolean));
    });
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},'?'),E('h2',{},bi('Question ','Вопрос ')+(index+1)+' / '+LEARN_QUIZ.length),E('p',{'class':'hv-quiz-question'},bi(q.q[0],q.q[1])),E('div',{'class':'hv-quiz-options'},options),
      grade?E('p',{'class':'hv-quiz-result hv-quiz-result-'+(grade.ok?'ok':'bad'),'role':'status'},grade.ok?bi('Correct!','Верно!'):bi('Not quite. Red is your wrong choice, green is the right answer.','Не совсем. Красным отмечен ваш неверный выбор, зелёным — правильный ответ.')):null].filter(Boolean)));
    var last=index===LEARN_QUIZ.length-1;
    host.appendChild(nav(null,function(){if(!checked){checked=true;draw();}else{checked=false;step++;draw();}},checked?(last?bi('See my result','Узнать результат'):bi('Next question','Следующий вопрос')):bi('Check the answer','Проверить ответ'),!checked&&chosen.length===0));
  }
  function result(){
    var s=learnScore(LEARN_QUIZ,answers);learnMarkSeen();
    if(s.percent>=80){try{window.localStorage.setItem('homensai-vpn-learn-done','1');}catch(e){}}
    host.appendChild(progress());
    host.appendChild(E('div',{'class':'hv-learn-card hv-learn-final'},[E('div',{'class':'hv-learn-score hv-learn-score-'+(s.percent>=80?'good':s.percent>=50?'mid':'low'),'aria-hidden':'true'},s.percent+'%'),
      E('h2',{},bi('Your knowledge: ','Ваши знания: ')+s.percent+bi(' out of 100',' из 100')),
      E('p',{},bi(s.correct+' of '+s.total+' answers were fully correct.',s.correct+' из '+s.total+' ответов полностью верны.')),
      E('p',{'class':'hv-learn-verdict'},learnVerdict(s.percent))]));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){visited=[];step=0;answers=[];checked=false;mode='flow';draw();}},bi('Take the training again','Пройти обучение заново')),E('button',{'type':'button','class':'cbi-button','click':function(){mode='toc';draw();}},bi('☰ Contents','☰ Оглавление')),E('a',{'class':'cbi-button','href':'#help'},bi('Open Help','Открыть помощь'))]));
  }
  function draw(){generation++;if(!Number.isInteger(step)||step<0||step>=total){step=0;mode='toc';checked=false;}clear();if(mode==='toc')toc();else if(step<LEARN_LESSONS.length)lesson();else if(step<LEARN_LESSONS.length+LEARN_QUIZ.length)question();else result();}
  draw();
  return host;
}
