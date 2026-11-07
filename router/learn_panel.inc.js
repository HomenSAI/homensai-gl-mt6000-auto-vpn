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
        "On the first visit the first-run wizard opens: Router → Channels → Behaviour → Terms and start. The current terms are shown at its last step (or when you first turn Auto on) until you accept them yourself on this router; training can be opened at any time.",
        "При первом входе открывается мастер первой настройки: «Роутер → Каналы → Поведение → Условия и запуск». Условия текущей версии показываются на его последнем шаге (или при первом включении Auto), пока вы сами не примете их на этом роутере; обучение можно открыть в любой момент."
      ],
      [
        "Monitoring runs independently of Auto. «Check now» is next to the Auto switch on Home (Console: Channels tab); the Monitoring service lamp is in Settings → System and diagnostics (Console: System tab). A fresh monitor report is not proof that a client has internet.",
        "Мониторинг работает отдельно от Auto. «Проверить сейчас» находится рядом с переключателем Auto на «Главной» (в «Пульте» — вкладка «Каналы»); лампа «Служба мониторинга» — в «Настройки → Система и диагностика» (в «Пульте» — вкладка «Система»). Свежий отчёт монитора ещё не доказывает доступность интернета у клиента."
      ]
    ],
    "example": [
      "A green monitoring lamp means fresh observations; Auto is still turned on separately with its switch.",
      "Зелёный индикатор мониторинга означает свежие наблюдения; Auto всё равно включается отдельно своим переключателем."
    ],
    "tip": [
      "Grey means waiting for the router, red means a proven failure: open Help (\"? Help\" in the Simple view; Console: System tab).",
      "Серый — ждём ответа роутера, красный — доказанный сбой: откройте «Помощь» («? Помощь» в виде «Простой»; в «Пульте» — вкладка «Система»)."
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
        "Wizard step 2 «Channels», later Settings → Channels: primary and reserve (Console: Channels → Change the channel pair): choose two different configured clients. Each choice represents the profile already assigned to that client; two servers of one client are not two independent channels.",
        "Шаг 2 мастера «Каналы», позже «Настройки → Каналы: основной и резерв» (в «Пульте» — «Каналы» → «Изменить пару каналов»): выберите два разных настроенных клиента. Каждый вариант — уже назначенный этому клиенту профиль; два сервера одного клиента не являются двумя независимыми каналами."
      ],
      [
        "To change a VPN server or protocol binding, use the stock VPN page and refresh Auto VPN. Saving the pair changes application metadata; it does not import keys or change server credentials.",
        "Для смены VPN-сервера или привязки протокола используйте штатную VPN-страницу и обновите Auto VPN. Сохранение пары меняет метаданные приложения, не импортирует ключи и не меняет данные провайдера."
      ],
      [
        "How fast to switch, Router load and the optional Telegram reports are wizard step 3 «Behaviour»; speed test parameters are in Settings → Speed test: parameters. Review in step 4 «Terms and start»; Save without starting never starts Auto.",
        "«Как быстро переключать», «Нагрузка на роутер» и необязательные отчёты Telegram — шаг 3 мастера «Поведение»; параметры теста скорости — в «Настройки → Тест скорости: параметры». Итог проверьте на шаге 4 «Условия и запуск»; «Сохранить без запуска» не включает Auto."
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
        "On Home (Console: Channels tab) press “Check now”. It tests right away which connected VPNs give internet. Fix problems first.",
        "На «Главной» (в «Пульте» — вкладка «Каналы») нажмите «Проверить сейчас». Сразу проверит, какие подключённые VPN дают интернет. Сначала устраните проблемы."
      ],
      [
        "Step 2: use the readiness list for your actual mode. Prepared-MT3000 router-probed IPv4 Auto checks the two channels on the router; a LAN helper is optional for additional client-path proof. A separate client-confirmed trial requires its own helper. Turn Auto on only when your mode is ready.",
        "Шаг 2: выполните список готовности своего режима. Router-probed IPv4 Auto подготовленного MT3000 проверяет два канала самим роутером; LAN-помощник нужен только для дополнительной проверки пути клиента. Отдельный тест с подтверждением клиента требует помощника. Включайте Auto после готовности своего режима."
      ],
      [
        "What is the LAN helper? A small PowerShell 7 script (plain text, you can read it) that runs on your Windows computer, not on the router. Install PowerShell 7 once, put the two downloaded files in one folder and start the launcher, then choose mode 1 (check only) first:",
        "Что такое LAN-помощник? Небольшой скрипт PowerShell 7 (обычный текст, его можно прочитать), который запускается на вашем компьютере с Windows, а не на роутере. Один раз установите PowerShell 7, положите два скачанных файла в одну папку и запустите, сначала выберите режим 1 (только проверка):"
      ],
      [
        "The Auto switch says whether Auto is on or off. The chip «Traffic here» marks the channel carrying your traffic, «Standing by» the other one. A green channel lamp means the channel works, not independent proof of Internet for every client; yellow means a check or a switch; red means it does not respond; grey means no fresh data. Inspect fresh channel checks for availability.",
        "Переключатель Auto показывает, включён Auto или выключен. Метка «Трафик здесь» отмечает канал, который несёт ваш трафик, «Ждёт в резерве» — другой. Зелёная лампа канала означает, что канал работает, а не отдельное доказательство Интернета для каждого клиента; жёлтая — идёт проверка или переключение; красная — канал не отвечает; серая — нет свежих данных. Доступность смотрите в свежих проверках канала."
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
      "Reading the two views",
      "Как читать два вида страницы"
    ],
    "body": [
      [
        "Simple view: Home starts with the status and the Auto switch, then the two channel cards with «Switch here», Events and reasons, Last 24 hours and Tests; Settings holds everything needed rarely. Console view: the status strip with the Auto switch stays on top, and the tabs Channels, Auto, Servers, Log and System show the same readings in more detail. Switch views with ☰ / ▦ next to the language button. A queued command remains pending until the router confirms it.",
        "Вид «Простой»: «Главная» начинается с состояния и переключателя Auto, дальше две карточки каналов с кнопкой «Переключить сюда», «События и причины», «За 24 часа» и «Проверки»; в «Настройках» — всё, что нужно редко. Вид «Пульт»: полоса состояния с переключателем Auto всегда сверху, а вкладки «Каналы», «Auto», «Серверы», «Журнал» и «Система» показывают те же данные подробнее. Вид переключается значками ☰ / ▦ рядом с кнопкой языка. Команда в очереди ожидает подтверждения роутера."
      ],
      [
        "The channel cards show primary first and reserve second with protocol, server and country where observed and the response (ping by default, or the three-site HTTPS mean); the 6-hour response chart is under Last 24 hours on Home and on the Channels tab of the Console. The Servers tab lists the servers of each channel with their ping (measured while Pick the best server is on). History is kept within the configured 1–7 days. A lower-delay server shown there does not switch the channel by itself.",
        "Карточки каналов показывают сначала основной, затем резервный: протокол, сервер и страну при наличии наблюдения и отклик (по умолчанию пинг, либо среднее трёх сайтов по HTTPS); график отклика за 6 часов — в «За 24 часа» на «Главной» и на вкладке «Каналы» в «Пульте». Вкладка «Серверы» перечисляет серверы каждого канала с пингом (он меряется, пока включён «Подбирать лучший сервер»). История хранится в пределах настроенных 1–7 дней. Более быстрый сервер в этом списке сам канал не переключает."
      ],
      [
        "Events and reasons on Home shows the latest 5 or 20 rows with the filters All, Switches, Problems and My actions; tap a row to read «why». The Log tab of the Console shows 20 rows and the live log; in the Simple view the live log is in Settings → System and diagnostics. Network checks keep their configured cadence. Settings → History and memory selects 1–2000 live log entries and 1–7 days of detail. Your own actions are marked «(you)»; missing historical outcomes are explained, not invented.",
        "«События и причины» на «Главной» показывает последние 5 или 20 строк с фильтрами «Все», «Переходы», «Проблемы» и «Мои действия»; нажмите строку, чтобы прочитать «почему». Вкладка «Журнал» в «Пульте» показывает 20 строк и живой журнал; в виде «Простой» живой журнал находится в «Настройки → Система и диагностика». Сетевые проверки сохраняют свой интервал. В «Настройки → История и память» выбираются 1–2000 записей живого журнала и 1–7 дней подробностей. Ваши собственные действия отмечены «(вы)»; для потерянных итогов указана причина, результат не выдумывается."
      ]
    ],
    "example": [
      "One outage may contain many failed checks. The failure chart counts the episode once.",
      "Один отказ может содержать много неудачных проверок. График отказов считает эпизод один раз."
    ],
    "tip": [
      "Speed tests are optional and use traffic: Home → Tests → Speed test (Console: Servers tab); parameters in Settings → Speed test: parameters.",
      "Тесты скорости необязательны и расходуют трафик: «Главная» → «Проверки» → «Тест скорости» (в «Пульте» — вкладка «Серверы»); параметры — в «Настройки → Тест скорости: параметры»."
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
        "Keep access to the router by cable or Wi-Fi and inspect the selected channel, current measurements and the recorded reason. Open Help → “I have no internet”.",
        "Сохраните доступ к роутеру по кабелю или Wi-Fi и проверьте выбранный канал, свежие измерения и записанную причину. Откройте «Помощь» → «У меня пропал интернет»."
      ],
      [
        "Switch manually only when the requested channel is confirmed ready and its action is available. Working on reserve alone is not a reason to force a return to a failed primary. Manual selection never turns Auto off: Auto keeps watching the channel you chose and moves traffic to the other one if it fails.",
        "Переключайте вручную только при подтверждённой готовности нужного канала и доступной команде. Работа на резерве сама по себе не повод возвращаться на неисправный основной. Ручной выбор никогда не выключает Auto: Auto продолжает следить за выбранным вами каналом и переносит трафик на другой, если этот откажет."
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
      "You can come back to this training at any time: Settings → Reference → Help and training (Console: System tab → Help, codes, training).",
      "К этому обучению можно вернуться в любой момент: «Настройки → Справка → Помощь и обучение» (в «Пульте» — вкладка «Система» → «Помощь, коды, обучение»)."
    ]
  }
];
var LEARN_QUIZ=[
  {q:['What does the system do when Auto is OFF?','Что делает система при выключенном Auto?'],o:[['Only watches and shows the state of your VPNs','Только наблюдает и показывает состояние ваших VPN',true],['Switches to the reserve VPN by itself','Сама переключается на резервный VPN',false],['Creates new VPN profiles','Создаёт новые VPN-профили',false]]},
  {q:['Which ways to connect should you prepare for the first tests? (several answers)','Какие способы подключения нужно подготовить для первых тестов? (несколько ответов)'],o:[['A laptop on a LAN cable','Ноутбук на кабеле LAN',true],['A device on Wi-Fi','Устройство по Wi-Fi',true],['Only one device that you cannot lose','Только одно устройство, которое нельзя потерять',false],['Mobile data on the phone','Мобильный интернет на телефоне',true]]},
  {q:['What is the right order to start working?','Каков правильный порядок начала работы?'],o:[['Accept the terms, start the monitor, check the VPNs, then turn on Auto','Принять условия, запустить мониторинг, проверить VPN, затем включить Auto',true],['Turn on Auto first, check later','Сначала включить Auto, проверить потом',false],['Skip the terms and start Auto','Пропустить условия и сразу запустить Auto',false]]},
  {q:['What must pass before Auto can be started?','Что должно пройти перед запуском Auto?'],o:[['The readiness checks for the selected mode; the helper is mandatory only for a client-confirmed trial','Проверки готовности выбранного режима; помощник обязателен только для теста с подтверждением клиента',true],['A speed test','Тест скорости',false],['A Telegram message','Сообщение в Telegram',false]]},
  {q:['What does the status Works via the reserve confirm?','Что подтверждает статус «Работает через резерв»?'],o:[['The reserve route is selected; primary health is checked separately','Выбран резервный маршрут; исправность основного проверяется отдельно',true],['Everything is on the primary','Всё идёт через основной',false],['Auto is off','Auto выключен',false]]},
  {q:['Which of these is a secret that you never send to anyone? (several answers)','Что из этого — секрет, который никому нельзя отправлять? (несколько ответов)'],o:[['The Telegram bot token','Токен Telegram-бота',true],['The router password','Пароль роутера',true],['The country of a VPN server','Страна VPN-сервера',false]]},
  {q:['The internet is gone. What do you do first?','Интернета нет. Что делаете сначала?'],o:[['Open the router page, inspect fresh checks and follow the Help topic I have no internet','Открываете страницу роутера, проверяете свежие данные и справку «У меня пропал интернет»',true],['Flash the router firmware','Прошиваете роутер',false],['Delete all VPN profiles','Удаляете все VPN-профили',false]]},
  {q:['Which command only reads the state and is always safe?','Какая команда только читает состояние и всегда безопасна?'],o:[['homensai-vpn-emergency show','homensai-vpn-emergency show',true],['homensai-vpn-emergency stop-auto','homensai-vpn-emergency stop-auto',false],['homensai-vpn-emergency remove-guard','homensai-vpn-emergency remove-guard',false]]}
];
LEARN_LESSONS[4].body.push(
 ['To choose a route manually, press Switch here on the Primary or Reserve card (Home, or the Channels tab of the Console) when the button is available, then wait for confirmed selection. A queued request is not completion; the status shows the switch until the router confirms it. Manual selection never turns Auto off: Auto keeps watching the chosen channel and moves traffic to the other one if it fails.','Для ручного выбора нажмите «Переключить сюда» на карточке «Основной» или «Резерв» («Главная» или вкладка «Каналы» в «Пульте»), когда кнопка доступна, затем дождитесь подтверждённого выбора. Очередь запроса не означает завершение; состояние показывает переключение, пока роутер его не подтвердит. Ручной выбор никогда не выключает Auto: Auto продолжает следить за выбранным каналом и переносит трафик на другой, если этот откажет.'],
 ['Use the Auto switch to request startup or shutdown. Wait for the actual final state. Turning Auto off does not stop monitoring; managed shutdown may restore the original routing/interface settings. If a working reserve is retained, press Switch here on the Primary card when the primary works; a retained reserve that itself fails (proven by a fresh check) is rescued to a healthy primary by Auto after a short stability wait.','Переключатель Auto запрашивает включение или выключение. Дождитесь фактического итогового состояния. Выключение Auto не прекращает мониторинг; управляемая остановка может восстановить исходные правила и флаги интерфейсов. Если удержан работающий резерв, нажмите «Переключить сюда» на карточке «Основной», когда основной работает; удержанный резерв, который сам отказал (это доказала свежая проверка), Auto спасает на исправный основной после короткого ожидания стабильности.']
);
LEARN_LESSONS[0].body.push(
 ['Why this project has so much mathematics, physics and biology. These experiments exist because the author, Serhii Khomenko, has always loved these sciences, even though they never came easily to him. That is why every idea is tested honestly: compared with the previous method in the simulator and on the router, and only what is really better is kept.','Почему в проекте столько математики, физики и биологии. Эти эксперименты появились потому, что автор проекта, Serhii Khomenko, всегда любил эти науки, хотя они всегда давались ему непросто. Поэтому каждая идея проверяется честно: сравнением со старым способом на симуляторе и на роутере, и остаётся только то, что действительно лучше.'],
 ['New in the 2.1.0-alpha9 line: Auto no longer leaves the primary on every hiccup (a probability model decides, not three failed checks in a row; experimental: chosen in simulation, not validated on hardware); an advisor can suggest, once a night, how fast to react through one slider (modes Advice, Auto, Manual; Advice is the default); Auto tells a router without internet (WAN-DOWN) from a failed tunnel; a changed VPN-server key is reported and accepted only by you; the first-run wizard can be skipped. All of this is tested on a PC and not yet verified on the router.','Новое в линии 2.1.0-alpha9: Auto больше не уходит с основного при каждом «чихе» (решает вероятностная модель, а не три неудачные проверки подряд; экспериментально: выбрано в симуляции, на железе не проверено); советник раз в сутки может подсказать, насколько быстро реагировать, одним ползунком (режимы «Совет», «Авто», «Вручную»; по умолчанию «Совет»); Auto отличает роутер без интернета (WAN-DOWN) от упавшего туннеля; изменившийся ключ VPN-сервера показывается, принять его можете только вы; мастер первой настройки можно пропустить. Всё это проверено на ПК и ещё не проверено на роутере.']
);
LEARN_QUIZ.push(
 {q:['Can you select a channel while Auto is on?','Можно ли выбрать канал при включённом Auto?'],o:[['Yes, when the manual control is available and the target passes its checks; Auto continues observing','Да, если ручное управление доступно и целевой канал прошёл проверки; Auto продолжает наблюдать',true],['Always stop Auto before any channel selection','Всегда выключать Auto перед любым выбором канала',false],['Channel selection deletes VPN profiles','Выбор канала удаляет VPN-профили',false]]},
 {q:['Does a successful channel check prove that traffic switched?','Означает ли успешная проверка канала, что трафик переключился?'],o:[['No. A check and a confirmed route change are separate events','Нет. Проверка и подтверждённая смена маршрута — разные события',true],['Yes, every successful check is a switch','Да, каждая успешная проверка — переключение',false],['A successful check means Auto was enabled by the operator','Успешная проверка означает, что оператор включил Auto',false]]},
 {q:['Does the VPN protocol decide which channel is primary?','Определяет ли протокол VPN, какой канал основной?'],o:[['No. Primary and reserve are saved roles of the selected pair; configure server credentials in the stock VPN app','Нет. Основной и резервный — сохранённые роли выбранной пары; серверы и ключи настраиваются в штатном VPN-приложении',true],['WireGuard must always be primary','WireGuard всегда должен быть основным',false],['OpenVPN must always be primary','OpenVPN всегда должен быть основным',false]]}
);
var LEARN_QUESTION_LESSONS=[0,1,2,4,4,7,6,6,4,5,3];
var LEARN_QUESTION_GUIDANCE=[
 ['With Auto off, the monitor still checks VPNs and records observations. It does not automatically choose another route.','При выключенном Auto монитор продолжает проверки и запись наблюдений. Автоматически другой маршрут он не выбирает.'],
 ['Keep a verified cable path and a second way to reach the intended router, plus mobile Internet for recovery. Two equal private IPs can identify different routers.','Подготовьте проверенный кабельный путь и второй способ попасть именно на нужный роутер, а также мобильный интернет для восстановления. Один частный IP может вести к разным роутерам.'],
 ['Read and accept the terms yourself, follow the explanation/setup, choose an existing pair and inspect fresh readiness before explicitly starting Auto.','Сами прочитайте и примите условия, пройдите объяснение/настройку, выберите существующую пару и проверьте свежую готовность перед явным запуском Auto.'],
 ['Readiness is mode-specific. Prepared router-probed Auto and a separate client-confirmed LAN trial require different evidence.','Готовность зависит от режима. Подготовленный router-probed Auto и отдельный LAN-тест с подтверждением клиента требуют разных доказательств.'],
 ['The green status Works via the reserve means there is internet and the reserve route carries traffic; there is no spare channel until the primary is back. It does not by itself prove the primary is broken; its card shows its own checks.','Зелёный статус «Работает через резерв» означает, что интернет есть и трафик идёт через резервный маршрут; запасного канала нет, пока основной не вернётся. Это само по себе не доказывает неисправность основного: его карточка показывает его собственные проверки.'],
 ['Passwords, bot tokens, VPN keys and complete backups are secrets. Server country is a display label, not an authentication secret.','Пароли, токены бота, VPN-ключи и полные резервные копии — секреты. Страна сервера является подписью, а не секретом доступа.'],
 ['First inspect the router and fresh checks, then use the Help topic I have no internet. Reflashing and deleting profiles are not first diagnostic steps.','Сначала откройте роутер и свежие проверки, затем помощь «У меня пропал интернет». Прошивка и удаление профилей не являются первым шагом диагностики.'],
 ['The show command reads the state. Stop-auto can change managed routing during recovery; remove-guard changes the owned traffic block.','Команда show читает состояние. Stop-auto при восстановлении может менять управляемый маршрут; remove-guard изменяет собственную блокировку трафика.'],
 ['Available manual controls can choose a verified channel while continuous Auto stays on. A queued command is not yet confirmed traffic selection.','Доступное ручное управление позволяет выбрать проверенный канал при работающем Auto. Поставленная в очередь команда ещё не означает подтверждённого выбора трафика.'],
 ['A successful check is an observation of a channel. Route changes have their own requested, pending and confirmed events.','Успешная проверка — наблюдение за каналом. Для смены маршрута есть отдельные события запроса, выполнения и подтверждения.'],
 ['Primary and reserve are roles, not protocol names. The application uses an existing pair and does not invent or import VPN credentials.','Основной и резервный — роли, а не названия протоколов. Приложение использует существующую пару и не создаёт или импортирует VPN-ключи.']
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
function learnKeepViewport(root,update){
  if(!root||!root.isConnected||!root.style||typeof root.getBoundingClientRect!=='function'||typeof window.scrollTo!=='function')return update();
  var doc=typeof document==='undefined'?null:document,x=window.scrollX||0,y=window.scrollY||window.pageYOffset||0,active=doc&&doc.activeElement;
  function key(node){
    if(!node)return null;
    var names=['data-learn-action','data-learn-question','data-result-question','data-learn-retry-wrong','data-scene-action','aria-label'];
    for(var i=0;i<names.length;i++){var value=node.getAttribute&&node.getAttribute(names[i]);if(value!==null&&value!==undefined)return names[i]+':'+value;}
    return node.tagName+':'+node.textContent;
  }
  var focused=active&&root.contains(active)?{node:active,key:key(active)}:null;
  var state=root.hvLearnViewportStyle;
  if(!state||root.style.minHeight!==state.last)state={base:root.style.minHeight||'',last:root.style.minHeight||''};
  root.hvLearnViewportStyle=state;
  var height=root.getBoundingClientRect().height;
  if(Number.isFinite(height)&&height>0)root.style.minHeight=Math.ceil(height)+'px';
  try{return update();}finally{
    root.style.minHeight=state.base;
    var scrolling=doc&&doc.scrollingElement;
    if(scrolling&&Number.isFinite(scrolling.scrollHeight)&&Number.isFinite(window.innerHeight)){
      var maximum=Math.max(0,scrolling.scrollHeight-window.innerHeight);
      if(y>maximum)root.style.minHeight=Math.ceil(root.getBoundingClientRect().height+y-maximum)+'px';
    }
    state.last=root.style.minHeight;
    if(focused&&(!root.contains(focused.node)||focused.node.disabled)){
      var replacement=Array.from(root.querySelectorAll('button,a,input,select,textarea')).find(function(node){return key(node)===focused.key;});
      if(replacement&&replacement.disabled)replacement=null;
      if(!replacement&&root.querySelector){replacement=root.querySelector('h2,h3');if(replacement)replacement.setAttribute('tabindex','-1');}
      if(replacement&&replacement.focus)replacement.focus({preventScroll:true});
    }
    window.scrollTo({left:x,top:y,behavior:'instant'});
  }
}
function renderLearn(){
  var host=E('section',{'class':'hv-chart-card hv-learn'});
  var scene=null;
  var mode=learnSeen()?'toc':'flow',visited=[],step=0,answers=[],graded=[],firstGrades=[],attempts=[],reviewQueue=null,reviewIndex=0,checked=false,generation=0,total=LEARN_LESSONS.length+LEARN_QUIZ.length+1;
  function clear(){if(scene&&scene.hvDispose)scene.hvDispose();scene=null;while(host.firstChild)host.removeChild(host.firstChild);}
  function inline(text){return richText(text);}
  function progress(){return E('div',{'class':'hv-learn-progress','role':'progressbar','aria-valuemin':'0','aria-valuemax':String(total),'aria-valuenow':String(step+1)},[E('span',{'style':'width:'+Math.round((step+1)*100/total)+'%'}),E('small',{},bi('Step ','Шаг ')+(step+1)+' / '+total)]);}
  function nav(back,next,nextLabel,nextDisabled){
    var shown=generation,used=false;
    function isDisabled(value){return typeof value==='function'?value():value;}
    function action(fn,disabled){return function(){if(isDisabled(disabled)||used||generation!==shown)return;used=true;return fn();};}
    var nextButton=next?E('button',{'type':'button','class':'cbi-button cbi-button-action','data-learn-action':'forward','disabled':isDisabled(nextDisabled)?'disabled':null,'click':action(next,nextDisabled)},nextLabel):E('span');
    var controls=E('div',{'class':'hv-learn-nav'},[back?E('button',{'type':'button','class':'cbi-button','data-learn-action':'back','click':action(back,false)},bi('Back','Назад')):E('span'),nextButton]);
    controls.hvLearnNext=nextButton;return controls;
  }
  function go(index,keepReview){if(!Number.isInteger(index)||index<0||index>=total)return;if(!keepReview)reviewQueue=null;mode='flow';step=index;checked=false;draw();}
  function once(fn){var shown=generation,used=false;return function(){if(used||generation!==shown)return;used=true;return fn();};}
  function reset(){visited=[];answers=[];graded=[];firstGrades=[];attempts=[];reviewQueue=null;reviewIndex=0;checked=false;}
  function missed(){return LEARN_QUIZ.map(function(q,i){return i;}).filter(function(i){return !graded[i]||!learnGrade(LEARN_QUIZ[i],answers[i]||[]).ok;});}
  function retryWrong(){var queue=missed();if(!queue.length)return;queue.forEach(function(i){answers[i]=[];graded[i]=false;});reviewQueue=queue;reviewIndex=0;go(LEARN_LESSONS.length+queue[0],true);}
  function chips(){
    var items=LEARN_LESSONS.map(function(l,i){return E('button',{'type':'button','class':'hv-chip'+(step===i?' hv-chip-current':'')+(visited[i]?' hv-chip-visited':''),'title':bi(l.title[0],l.title[1]),'aria-label':bi(l.title[0],l.title[1]),'click':once(function(){go(i);})},String(i+1));});
    items.push(E('button',{'type':'button','class':'hv-chip hv-chip-quiz'+(step>=LEARN_LESSONS.length?' hv-chip-current':''),'title':bi('Questions','Вопросы'),'click':once(function(){go(LEARN_LESSONS.length);})},'?'));
    LEARN_QUIZ.forEach(function(q,i){items.push(E('button',{'type':'button','class':'hv-chip hv-chip-question'+(step===LEARN_LESSONS.length+i?' hv-chip-current':''),'data-learn-question':String(i),'aria-label':bi('Question ','Вопрос ')+(i+1)+': '+bi(q.q[0],q.q[1]),'click':once(function(){go(LEARN_LESSONS.length+i);})},bi('Q','В')+(i+1)));});
    items.push(E('button',{'type':'button','class':'hv-chip','click':once(function(){go(total-1);})},bi('Results','Результаты')));
    return E('div',{'class':'hv-chips'},[E('button',{'type':'button','class':'cbi-button hv-chip-contents','click':once(function(){mode='toc';draw();})},bi('☰ Contents','☰ Оглавление'))].concat(items));
  }
  function toc(){
    host.appendChild(chips());
    var rows=LEARN_LESSONS.map(function(l,i){return E('button',{'type':'button','class':'hv-toc-item'+(visited[i]?' hv-toc-visited':''),'click':once(function(){go(i);})},[E('span',{'class':'hv-toc-num','aria-hidden':'true'},String(i+1)),E('span',{'class':'hv-toc-text'},[E('strong',{},bi(l.title[0],l.title[1])),E('small',{},bi(l.body[0][0].split('. ')[0]+'.',l.body[0][1].split('. ')[0]+'.'))])]);});
    rows.push(E('button',{'type':'button','class':'hv-toc-item hv-toc-quiz','click':once(function(){go(LEARN_LESSONS.length);})},[E('span',{'class':'hv-toc-num','aria-hidden':'true'},'?'),E('span',{'class':'hv-toc-text'},[E('strong',{},bi('Questions and your score','Вопросы и ваша оценка')),E('small',{},bi('Check what you remember.','Проверьте, что вы запомнили.'))])]));
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('h2',{},bi('Contents','Оглавление')),E('p',{'class':'hv-learn-intro'},learnSeen()?bi('You can reopen any topic or question in any order.','Можно открыть любую тему или вопрос, в любом порядке.'):bi('Open any topic, or read them one after another starting with 1. The first full pass takes about 5 minutes.','Откройте любую тему или читайте по порядку, начиная с 1. Первый полный проход занимает около 5 минут.')),E('div',{'class':'hv-toc'},rows)]));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':once(function(){reset();go(0);})},bi('Start from the beginning','Начать с самого начала')),E('span')]));
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
    var grade=checked?learnGrade(q,chosen):null,answerButton=null;
    host.appendChild(chips());host.appendChild(progress());
    var lessonIndex=Array.isArray(LEARN_QUESTION_LESSONS)?LEARN_QUESTION_LESSONS[index]:Math.min(index,LEARN_LESSONS.length-1),context=LEARN_LESSONS[lessonIndex]||LEARN_LESSONS[0];
    host.appendChild(E('section',{'class':'hv-learn-question-context'},[E('h3',{},bi('Before the question','Перед вопросом')),E('p',{},inline(LEARN_QUESTION_GUIDANCE[index]?bi(LEARN_QUESTION_GUIDANCE[index][0],LEARN_QUESTION_GUIDANCE[index][1]):bi(context.body[0][0],context.body[0][1]))),E('p',{},inline(bi(context.example[0],context.example[1])))]));
    if(reviewQueue)host.appendChild(E('p',{'role':'status'},bi('Review missed questions: ','Повтор ошибок: ')+(reviewIndex+1)+' / '+reviewQueue.length));
    var options=q.o.map(function(option,i){
      var mark=grade?grade.marks[i]:'none';
      var box=E('input',{'type':'checkbox','disabled':checked?'disabled':null,'change':function(){if(checked||generation!==shown)return;var at=chosen.indexOf(i);if(box.checked&&at<0)chosen.push(i);if(!box.checked&&at>=0)chosen.splice(at,1);if(answerButton)answerButton.disabled=chosen.length===0;}});
      box.checked=chosen.indexOf(i)>=0;
      var note=mark==='right'?bi('Correct','Верно'):mark==='wrong'?bi('Wrong choice','Неверный выбор'):mark==='missed'?bi('This was a correct answer','Это был правильный ответ'):'';
      return E('label',{'class':'hv-quiz-option hv-quiz-'+mark},[box,(/^homensai-vpn-emergency /.test(option[0])?E('code',{'class':'hv-code'},option[0]):E('span',{},bi(option[0],option[1]))),note?E('small',{},note):null].filter(Boolean));
    });
    host.appendChild(E('div',{'class':'hv-learn-card'},[E('div',{'class':'hv-learn-icon','aria-hidden':'true'},'?'),E('h2',{},bi('Question ','Вопрос ')+(index+1)+' / '+LEARN_QUIZ.length),E('p',{'class':'hv-quiz-question'},bi(q.q[0],q.q[1])),E('div',{'class':'hv-quiz-options'},options),
      grade?E('p',{'class':'hv-quiz-result hv-quiz-result-'+(grade.ok?'ok':'bad'),'role':'status'},grade.ok?bi('Correct!','Верно!'):bi('Not quite. Red is your wrong choice, green is the right answer.','Не совсем. Красным отмечен ваш неверный выбор, зелёным — правильный ответ.')):null].filter(Boolean)));
    var last=index===LEARN_QUIZ.length-1;
    var controls=nav(index>0?function(){go(LEARN_LESSONS.length+index-1);}:null,function(){if(!checked){graded[index]=true;attempts[index]=(attempts[index]||0)+1;if(firstGrades[index]===undefined)firstGrades[index]=learnGrade(q,chosen).ok;checked=true;draw();}else if(reviewQueue){reviewIndex++;if(reviewIndex<reviewQueue.length)go(LEARN_LESSONS.length+reviewQueue[reviewIndex],true);else{reviewQueue=null;go(total-1);}}else{checked=false;step++;draw();}},checked?((reviewQueue?reviewIndex===reviewQueue.length-1:last)?bi('See my result','Узнать результат'):bi('Next question','Следующий вопрос')):bi('Check the answer','Проверить ответ'),function(){return !checked&&chosen.length===0;});
    answerButton=controls.hvLearnNext;host.appendChild(controls);
  }
  function result(){
    var s=learnScore(LEARN_QUIZ,answers.map(function(a,i){return graded[i]?a:[];})),wrong=missed(),answered=graded.filter(Boolean).length,firstCorrect=firstGrades.filter(function(v){return v===true;}).length;learnMarkSeen();
    if(answered===LEARN_QUIZ.length&&s.percent>=80){try{window.localStorage.setItem('homensai-vpn-learn-done','1');}catch(e){}}
    host.appendChild(chips());host.appendChild(progress());
    host.appendChild(E('div',{'class':'hv-learn-card hv-learn-final'},[E('div',{'class':'hv-learn-score hv-learn-score-'+(s.percent>=80?'good':s.percent>=50?'mid':'low'),'aria-hidden':'true'},s.percent+'%'),
      E('h2',{},bi('Your knowledge: ','Ваши знания: ')+s.percent+bi(' out of 100',' из 100')),
      E('p',{},bi(s.correct+' of '+s.total+' answers were fully correct.',s.correct+' из '+s.total+' ответов полностью верны.')),
      E('p',{},bi('Correct on first attempt: ','Верно с первой попытки: ')+firstCorrect+' / '+s.total),E('p',{},bi('Checked questions: ','Проверено вопросов: ')+answered+' / '+s.total),E('p',{},bi('Total answer checks: ','Всего проверок ответов: ')+attempts.reduce(function(a,n){return a+(n||0);},0)),E('p',{'class':'hv-learn-verdict'},answered<s.total?bi('Some questions are still unanswered. Review the remaining questions below.','На часть вопросов вы ещё не ответили. Пройдите оставшиеся вопросы ниже.'):learnVerdict(s.percent))]));
    host.appendChild(E('div',{'class':'hv-dv-tablewrap'},E('table',{'class':'table hv-learn-results','data-hv-no-sort':'1'},[E('thead',{},E('tr',{},[bi('Question','Вопрос'),bi('Result','Результат'),bi('Attempts','Попытки')].map(function(t){return E('th',{},t);}))),E('tbody',{},LEARN_QUIZ.map(function(q,i){var ok=graded[i]&&learnGrade(q,answers[i]||[]).ok;return E('tr',{},[E('td',{},E('button',{'type':'button','class':'cbi-button','data-result-question':String(i),'click':once(function(){go(LEARN_LESSONS.length+i);})},String(i+1)+'. '+bi(q.q[0],q.q[1]))),E('td',{},!graded[i]?bi('Not checked','Не проверено'):ok?bi('Correct','Верно'):bi('Review needed','Нужно повторить')),E('td',{},String(attempts[i]||0))]);}))])));
    if(wrong.length)host.appendChild(E('button',{'type':'button','class':'cbi-button cbi-button-action','data-learn-retry-wrong':'1','click':once(retryWrong)},(answered<s.total?bi('Answer remaining questions','Пройти оставшиеся вопросы'):bi('Review missed questions','Повторить ошибки'))+' ('+wrong.length+')'));
    host.appendChild(E('div',{'class':'hv-learn-nav'},[E('button',{'type':'button','class':'cbi-button cbi-button-action','click':once(function(){reset();step=0;mode='flow';draw();})},bi('Take the training again','Пройти обучение заново')),E('button',{'type':'button','class':'cbi-button','click':once(function(){mode='toc';draw();})},bi('☰ Contents','☰ Оглавление')),E('a',{'class':'cbi-button','href':'#help'},bi('Open Help','Открыть помощь'))]));
  }
  function renderStep(){generation++;if(!Number.isInteger(step)||step<0||step>=total){step=0;mode='toc';checked=false;}clear();if(mode==='flow'&&step>=LEARN_LESSONS.length&&step<LEARN_LESSONS.length+LEARN_QUIZ.length)checked=graded[step-LEARN_LESSONS.length]===true;if(mode==='toc')toc();else if(step<LEARN_LESSONS.length)lesson();else if(step<LEARN_LESSONS.length+LEARN_QUIZ.length)question();else result();}
  function draw(){return learnKeepViewport(host,renderStep);}
  draw();
  return host;
}
