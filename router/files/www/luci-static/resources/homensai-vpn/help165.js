'use strict';
'require baseclass';
return baseclass.extend({create:function(ctx){
var E=ctx.E;
var bi=ctx.bi;
var locale=ctx.locale;
var richText=ctx.richText;
var helpCommand=ctx.helpCommand;
var READINESS_GUIDES=ctx.READINESS_GUIDES;
var READINESS_CHECKS=ctx.READINESS_CHECKS;
var renderReadinessHelp=ctx.renderReadinessHelp;
var renderAutoRemedy=ctx.renderAutoRemedy;
var AUTO_BLOCKERS=ctx.AUTO_BLOCKERS;
var AUTO_REMEDIES=ctx.AUTO_REMEDIES;
var autoRemedyKey=ctx.autoRemedyKey;
var PLAN_BLOCKERS=ctx.PLAN_BLOCKERS;
var errorCodeLink=ctx.errorCodeLink;
var ensureJournalDictionary=ctx.ensureJournalDictionary;
var spanText=ctx.spanText;
var HELP_TOPICS=[
  {"id": "probe-boost", "open": false, "title": ["Probe level and automatic boost: how it works", "Уровень опроса и автоматическое ускорение: как это работает"], "when": ["You want to know exactly when the router checks more often and when it returns to the chosen level.", "Вы хотите точно знать, когда роутер начинает проверять чаще и когда возвращается к выбранному уровню."], "steps": [{"t": ["Probe level 1-5 sets two cadences. Channel health check (is internet working through the VPN): level 1 every 60 s, 2 every 30 s, 3 every 20 s, 4 every 15 s, 5 every 10 s. Response measurement (ping or the three sites): 300, 120, 60, 45 and 30 s. A failure is confirmed after 3 failed health checks in a row, so level 1 confirms in about 3 minutes and level 5 in about 30 s.", "Уровень опроса 1–5 задаёт два интервала. Проверка канала (работает ли интернет через VPN): уровень 1 — раз в 60 с, 2 — раз в 30 с, 3 — раз в 20 с, 4 — раз в 15 с, 5 — раз в 10 с. Замер отклика (пинг или три сайта): 300, 120, 60, 45 и 30 с. Сбой подтверждается после 3 неудачных проверок подряд, поэтому на уровне 1 это около 3 минут, на уровне 5 — около 30 с."]}, {"t": ["Automatic boost starts when Auto is running and watching (OBSERVING, COMMITTED or working on the reserve) and the primary or reserve channel fails one health check. From that moment the router checks every 10 s and measures the response every 30 s, whatever level you chose. Nothing is switched by the boost itself: it only makes the checks frequent so that a real failure is confirmed in about 30 s.", "Автоматическое ускорение включается, когда Auto работает и наблюдает (OBSERVING, COMMITTED или работа на резерве), а основной или резервный канал не прошёл одну проверку. С этого момента роутер проверяет каналы раз в 10 с и замеряет отклик раз в 30 с, независимо от выбранного уровня. Само ускорение ничего не переключает: оно только учащает проверки, чтобы настоящий сбой подтвердился примерно за 30 с."]}, {"t": ["An episode lasts 10 minutes from the last failed check, but never longer than 20 minutes in total. It ends earlier in effect when its job is done: after Auto switched the channel, or after the failure was confirmed (3 failed checks), further failures no longer extend it.", "Эпизод длится 10 минут от последней неудачной проверки, но всего не дольше 20 минут. Как только задача выполнена — Auto переключил канал или сбой подтверждён (3 неудачные проверки), — новые неудачи его больше не продлевают."]}, {"t": ["When the episode ends, the router returns to your level and writes the result to the decision log: switched (Auto changed the channel), failure-confirmed (the channel really failed), false-alarm (one check failed, then the channel worked) or disabled (you turned the boost off). Then there is a 10-minute rest: no new episode starts, and the same channel cannot start one again until it has passed a check. A channel that stays down therefore cannot keep the router at the fast cadence forever.", "Когда эпизод закончился, роутер возвращается к вашему уровню и записывает итог в журнал решений: switched (Auto переключил канал), failure-confirmed (канал действительно отказал), false-alarm (одна проверка не прошла, потом канал работал) или disabled (вы выключили ускорение). Затем 10 минут отдыха: новый эпизод не начинается, а тот же канал не может начать его снова, пока не пройдёт проверку. Поэтому канал, который лежит долго, не держит роутер на частых проверках бесконечно."]}, {"t": ["The decision log on Overview lists every level change and every episode: time, level, what happened, which channel and its error code. The countdown under the traffic light shows the current cadence, with «· boost» while an episode runs.", "Журнал решений на «Обзоре» перечисляет каждую смену уровня и каждый эпизод: время, уровень, что произошло, какой канал и код ошибки. Отсчёт под светофором показывает текущий интервал, во время эпизода — с пометкой «· ускорение»."]}, {"t": ["If the router refuses a level change while a switch is running, the reason is shown under the Apply button and the change is retried automatically for 2 minutes. A manual channel switch does not turn Auto off: Auto keeps watching the channel you chose, so the boost works the same way after a manual switch.", "Если роутер отклоняет смену уровня во время переключения, причина показывается под кнопкой «Применить», а смена автоматически повторяется в течение 2 минут. Ручное переключение канала не выключает Auto: Auto продолжает следить за выбранным вами каналом, поэтому ускорение работает так же и после ручного переключения."]}]},
  {
    "id": "response-measurement",
    "open": false,
    "title": [
      "How the response is measured",
      "Как измеряется отклик"
    ],
    "when": [
      "You want to know what the response numbers mean and why the reserve is slower.",
      "Вы хотите понять, что означают числа отклика и почему резерв медленнее."
    ],
    "steps": [
      {
        "t": [
          "Settings → How the response is measured chooses the method. Default: ping (ICMP echo to 1.1.1.1, or 8.8.8.8 / 9.9.9.9) through each tunnel: small numbers, almost no router load, best for comparing the channels. Alternative: three websites. The router itself measures through each VPN tunnel, not your computer. Three websites are opened fresh: Google, Cloudflare and Wikipedia. Each time includes the DNS lookup, the TCP connection, the TLS encryption handshake and the complete HTTP headers.",
          "Способ выбирается в «Настройки» → «Как измеряется отклик». По умолчанию — пинг (ICMP-запрос к 1.1.1.1, либо 8.8.8.8 / 9.9.9.9) через каждый туннель: небольшие числа, почти без нагрузки на роутер, лучше всего для сравнения каналов. Другой вариант — три сайта. Измеряет сам роутер через каждый VPN-туннель, а не ваш компьютер. Он заново открывает три сайта: Google, Cloudflare и Wikipedia. Каждое время включает поиск адреса (DNS), TCP-соединение, установку шифрования TLS и получение полных HTTP-заголовков."
        ]
      },
      {
        "t": [
          "The response shown is the average of the three sites and appears only when all three answered (3/3). A partial result is shown as coverage without an average, so a slow site that timed out cannot make the number look better.",
          "Показанный отклик — среднее трёх сайтов, и он появляется, только если ответили все три (3/3). Частичный результат показывается как охват без среднего, поэтому медленный сайт, не успевший ответить, не может «улучшить» число."
        ]
      },
      {
        "t": [
          "Opening a site needs 5-7 round trips, so the response is several times the ping. Example from the MT3000: WireGuard ping 53 ms gives about 430 ms; OpenVPN over TCP ping 241 ms gives about 2.4 s, because TCP inside TCP waits and resends on any loss and OpenVPN costs more router CPU.",
          "Открытие сайта требует 5–7 обменов «туда-обратно», поэтому отклик в несколько раз больше пинга. Пример с MT3000: у WireGuard пинг 53 мс даёт около 430 мс; у OpenVPN через TCP пинг 241 мс даёт около 2,4 с, потому что TCP внутри TCP ждёт и переотправляет при любой потере, а OpenVPN сильнее нагружает процессор роутера."
        ]
      },
      {
        "t": [
          "How often it is measured follows the probe level on Overview (every 30 s at level 5, every 5 min at level 1, every 30 s during automatic boost). The response is information only: Auto decides on DNS and HTTPS health checks, not on the response time.",
          "Как часто измеряется, задаёт уровень опроса на «Обзоре» (раз в 30 с на уровне 5, раз в 5 мин на уровне 1, раз в 30 с во время автоускорения). Отклик — только информация: Auto решает по проверкам DNS и HTTPS, а не по времени отклика."
        ]
      },
      {
        "t": [
          "The delay chart and the statistics follow the method you chose; the ping history is kept separately. The option \"Measure all methods (comparison)\" makes every check also ping the other DNS addresses and open the three websites; the server ranking on Tests then shows one column per method. Switching still uses only the chosen method.",
          "График задержки и статистика следуют выбранному способу; история пинга хранится отдельно. Параметр «Мерить все способы (сравнение)» заставляет каждую проверку дополнительно пинговать остальные DNS-адреса и открывать три сайта; рейтинг серверов на странице «Тесты» показывает по одному столбцу на каждый способ. Переключение по-прежнему использует только выбранный способ."
        ]
      }
    ]
  },
  {
    "id": "auto-two-channels",
    "open": false,
    "title": [
      "How two-channel Auto works",
      "Как работает Auto двух каналов"
    ],
    "when": [
      "You want to know what Auto does after you press its button and what the router checks.",
      "Вы хотите знать, что делает Auto после нажатия кнопки и что проверяет роутер."
    ],
    "steps": [
      {
        "t": [
          "Auto starts the saved primary and reserve, checks IPv4 DNS/HTTPS, switches after repeated failures and returns after stable recovery according to your settings. Stop remains available during startup. Auto needs an explicit Start after restart.",
          "Auto запускает сохранённые основной и резервный VPN, проверяет IPv4 DNS/HTTPS, переключается после повторных отказов и возвращается после устойчивого восстановления по вашим настройкам. Stop доступен при запуске. После перезапуска нужен явный Start."
        ]
      },
      {
        "t": [
          "About these checks: two selected VPN channels; the router checks them itself through each tunnel. How often is set by the probe level on Overview (every 60 s at level 1 down to every 10 s at level 5); a failure is confirmed after 3 failed checks.",
          "Об этих проверках: два выбранных VPN-канала; проверку делает сам роутер через каждый туннель. Как часто — задаёт уровень опроса на «Обзоре» (от раза в 60 с на уровне 1 до раза в 10 с на уровне 5); сбой подтверждается после 3 неудачных проверок."
        ]
      },
      {
        "t": [
          "Lamp colours are the same on every page: green means this channel carries your traffic; yellow means it is alive but not in use (only such a channel offers \"switch to it\") or is being checked for a moment; red means a proven failure; grey means we are waiting for the router. The Auto button, the traffic light, the sidebar Auto lamp and the live journal always show one colour: green while Auto runs, yellow only during a real switch, start or stop and in a short pulse around each scheduled check, red only for a proven failure (the selected channel failed, a controller alarm, or no router answer for 90 s), dark when you turned Auto off. During a manual switch the destination card blinks green.",
          "Цвета ламп одинаковы на всех страницах: зелёный — этот канал несёт ваш трафик; жёлтый — канал жив, но не используется (только к такому каналу предлагается «переключиться») или идёт короткая проверка; красный — доказанный сбой; серый — ждём ответа роутера. Кнопка Auto, светофор, лампа Auto в боковом меню и живой журнал всегда показывают один цвет: зелёный, пока Auto работает; жёлтый только во время реального переключения, запуска или остановки и короткой вспышкой вокруг каждой плановой проверки; красный только при доказанном сбое (выбранный канал отказал, тревога контроллера или нет ответа роутера 90 с); погашен, когда вы выключили Auto. При ручном переключении карточка назначения мигает зелёным."
        ]
      },
      {
        "t": [
          "No internet? Open the topic \"No internet\" below in Help for the recovery steps.",
          "Нет интернета? Откройте ниже в «Помощи» тему «Нет интернета» — там порядок восстановления."
        ]
      }
    ]
  },
  {
    "id": "planner-wait",
    "open": false,
    "title": [
      "Why Auto waits before switching",
      "Почему Auto ждёт перед переключением"
    ],
    "when": [
      "You want to understand why a single failed check does not immediately switch the channel.",
      "Вы хотите понять, почему после одной неудачной проверки канал не переключается сразу."
    ],
    "steps": [
      {
        "t": [
          "The planner compares consecutive failed checks of the channel in use with consecutive successful checks of the other channel. The configured thresholds help avoid switching because of a brief interruption.",
          "Планировщик сравнивает последовательные неудачные проверки используемого канала и успешные проверки другого канала. Настроенные пороги помогают не переключать канал из-за краткого сбоя."
        ]
      },
      {
        "t": [
          "A green observation describes a successful check or an unmet failure threshold. It is not a separate confirmation that Auto is ready or that a route change is allowed.",
          "Зелёный результат означает успешную проверку либо то, что порог сбоев ещё не достигнут. Это не отдельное подтверждение готовности Auto и не разрешение менять маршрут."
        ]
      },
      {
        "t": [
          "Auto also considers fresh observations, the selected VPN pair, controller state and the configured return policy. A recommendation alone does not switch traffic.",
          "Auto также учитывает свежесть наблюдений, выбранную пару VPN, состояние контроллера и настроенную политику возврата. Сама рекомендация трафик не переключает."
        ]
      },
      {
        "t": [
          "See Overview for the current Auto state and selected channel. Use Live log for the sequence of decisions and their reasons. If observations are stale, use Check VPN now; it refreshes checks without choosing a channel for you.",
          "Текущее состояние Auto и выбранный канал смотрите на «Обзоре». Последовательность решений и их причины — в «Живом журнале». Если наблюдения устарели, нажмите «Проверить VPN сейчас»: это обновляет проверки без выбора канала за вас."
        ]
      }
    ]
  },
  {
    "id": "no-internet",
    "open": true,
    "title": [
      "I have no internet",
      "У меня пропал интернет"
    ],
    "when": [
      "Devices on your network cannot open sites after Auto ran or after you changed VPN settings.",
      "Устройства в сети не открывают сайты после работы Auto или после смены настроек VPN."
    ],
    "steps": [
      {
        "t": [
          "Keep a working way to reach the router, such as the LAN cable and a phone with mobile data. Confirm that the page belongs to the intended router.",
          "Сохраните рабочий доступ к роутеру: например, кабель LAN и телефон с мобильным интернетом. Убедитесь, что открыта страница нужного роутера."
        ]
      },
      {
        "t": [
          "On Overview check the selected channel and fresh DNS/HTTPS results. A working reserve is a normal state. Select another channel only when its readiness is confirmed; do not return to a failed primary just because it is called primary.",
          "На «Обзоре» проверьте выбранный канал и свежие DNS/HTTPS-результаты. Исправный резерв — нормальное состояние. Выбирайте другой канал только при подтверждённой готовности; не возвращайтесь на неисправный основной лишь из-за его названия."
        ]
      },
      {
        "t": [
          "Read the local emergency summary over SSH. Keep it private until you remove addresses, policy identifiers and private transaction data.",
          "Прочитайте аварийную сводку локально по SSH. Перед передачей кому-либо удалите адреса, идентификаторы политик и приватные данные транзакций."
        ],
        "c": "homensai-vpn-emergency show"
      },
      {
        "t": [
          "If managed recovery is stuck, stop the application services. This can restore the managed policy/interface baseline and disable the saved Auto flag; it is not a read-only command. Pending application edits must be resolved separately.",
          "Если управляемое восстановление зависло, остановите службы приложения. Это может восстановить управляемые политики/интерфейсы и выключить сохранённый флаг Auto; команда не является чтением. Ожидающие правки приложения нужно разрешить отдельно."
        ],
        "c": "homensai-vpn-emergency stop-auto"
      },
      {
        "t": [
          "After services have stopped, remove only a verified application-owned traffic guard if it remains. Never delete vendor firewall tables or disable Kill Switch. Verify the resulting route and client Internet.",
          "После остановки служб удалите только оставшуюся подтверждённую блокировку приложения. Не удаляйте таблицы прошивки и не выключайте Kill Switch. Проверьте итоговый маршрут и Интернет клиента."
        ],
        "c": "homensai-vpn-emergency remove-guard"
      },
      {
        "t": [
          "If needed, inspect the stock VPN Dashboard. Choose a known working configuration deliberately; do not reorder unrelated rules or import new keys as an emergency shortcut.",
          "При необходимости проверьте штатную VPN Dashboard. Осознанно выберите заведомо рабочую конфигурацию; не переставляйте посторонние правила и не импортируйте новые ключи как аварийный обход."
        ]
      },
      {
        "t": [
          "A router reboot is a last recovery step when you still control the device. It interrupts connectivity and does not repair a bad VPN configuration. Auto needs an explicit Start afterwards.",
          "Перезагрузка — последний шаг восстановления, если управление устройством сохранено. Она прерывает связь и не исправляет неверную VPN-конфигурацию. После неё Auto требует явного запуска."
        ]
      },
      {
        "t": [
          "Once connectivity is restored, start the application services and confirm fresh monitoring. This command alone does not confirm Internet or start continuous Auto.",
          "После восстановления связи запустите службы приложения и дождитесь свежего мониторинга. Сама команда не подтверждает Интернет и не включает непрерывный Auto."
        ],
        "c": "homensai-vpn-emergency start"
      }
    ]
  },
  {
    "id": "ssh",
    "title": [
      "How to connect by SSH",
      "Как подключиться по SSH"
    ],
    "when": [
      "You need a command line on the router for the steps in this Help.",
      "Командная строка на роутере нужна для шагов в этой справке."
    ],
    "steps": [
      {
        "t": [
          "Use the real LAN address of the intended router. The address in the examples is a factory default, not an instruction to change your computer or router addresses.",
          "Используйте реальный LAN-адрес нужного роутера. Адрес в примерах — заводской, а не указание менять адреса компьютера или роутера."
        ]
      },
      {
        "t": [
          "Open a terminal. Windows may provide OpenSSH Client; otherwise use your installed SSH client. Replace the example address with the verified router address.",
          "Откройте терминал. В Windows может быть установлен «Клиент OpenSSH»; иначе используйте свой SSH-клиент. Замените адрес примера проверенным адресом роутера."
        ],
        "c": "ssh root@192.168.8.1"
      },
      {
        "t": [
          "If Git for Windows supplies your SSH client, its usual executable path is shown below. Use the actual path installed on your computer.",
          "Если SSH поставляется с Git for Windows, ниже показан обычный путь. Используйте фактически установленный на компьютере путь."
        ],
        "c": "& \"C:\\Program Files\\Git\\usr\\bin\\ssh.exe\" root@192.168.8.1"
      },
      {
        "t": [
          "At the first connection compare the host-key fingerprint with trusted router information before accepting it. If a saved key changes, stop and establish the device identity; do not disable host-key verification.",
          "При первом подключении сравните отпечаток ключа со сведениями из доверенного источника о роутере. Если сохранённый ключ изменился, сначала установите причину и идентичность устройства; не отключайте проверку ключа."
        ]
      },
      {
        "t": [
          "Enter the router root password only in the local hidden prompt, or use the already authorized SSH key. Do not paste credentials into chat or command text. The shell prompt can contain your router hostname.",
          "Введите пароль root только в локальном скрытом поле либо используйте уже разрешённый SSH-ключ. Не вставляйте пароль в чат или текст команды. В приглашении оболочки может быть имя вашего роутера."
        ]
      },
      {
        "t": [
          "If two adapters lead to different devices with the same private address, resolve which path reaches the target before logging in. The address-conflict topic explains this case.",
          "Если два адаптера ведут к разным устройствам с одинаковым частным адресом, сначала определите путь к нужному устройству. Этот случай описан в теме конфликта адресов."
        ]
      },
      {
        "t": [
          "Leave the SSH shell when finished.",
          "После работы выйдите из SSH-оболочки."
        ],
        "c": "exit"
      }
    ]
  },
  {
    "id": "reserve",
    "title": [
      "The router stays on the reserve VPN",
      "Роутер остаётся на резервном VPN"
    ],
    "when": [
      "The selected reserve is working, a return is requested, or Stop retained the reserve.",
      "Выбран исправный резерв, нужен возврат либо после остановки остался резерв."
    ],
    "steps": [
      {
        "t": [
          "Check both channel measurements and the selected route on Overview. Being on reserve does not by itself mean an error.",
          "Проверьте измерения обоих каналов и выбранный маршрут на «Обзоре». Работа на резерве сама по себе не означает ошибку."
        ]
      },
      {
        "t": [
          "For an intentional return, use Manual channel selection when Primary is confirmed ready and its command is available. A manual switch never turns Auto off: Auto keeps watching the channel you chose and moves traffic to the other one if it fails (there is no separate Resume Auto button). If Stop retained the reserve, use the offered Return to primary action and verify its actual result.",
          "Для осознанного возврата используйте «Ручное переключение канала», когда основной готов и действие доступно. Ручное переключение никогда не выключает Auto: Auto продолжает следить за выбранным вами каналом и переносит трафик на другой, если этот откажет (отдельной кнопки «Возобновить Auto» нет). Если Stop сохранил резерв, используйте предлагаемое действие возврата и проверьте фактический итог."
        ]
      },
      {
        "t": [
          "Automatic return depends on the saved return policy and fresh primary health. Hold-reserve preference does not promise automatic return merely because primary probes succeed. After an Auto restart or a package upgrade Auto returns to the primary when it is healthy.",
          "Автоматический возврат зависит от сохранённой политики и свежих проверок основного. Предпочтение оставаться на резерве не обещает автоматического возврата лишь после успешной проверки основного. После перезапуска Auto или обновления пакета Auto возвращается на основной, когда он исправен."
        ]
      },
      {
        "t": [
          "If neither channel works or a recovery command is refused, read its code and use No internet. Do not change stock VPN profiles while Auto owns a transition.",
          "Если не работает ни один канал либо восстановление отклонено, прочитайте код и тему «У меня пропал интернет». Не меняйте штатные профили, пока Auto управляет переходом."
        ]
      }
    ]
  },
  {
    "id": "auto-refuses",
    "title": [
      "The Auto button refuses to start",
      "Кнопка Auto не запускается"
    ],
    "when": [
      "Pressing Start shows a message with a code.",
      "После нажатия «Старт» появляется сообщение с кодом."
    ],
    "steps": [
      {
        "t": [
          "Open System readiness and the current Auto explanation on Overview. Use the exact refused condition; a green dry-run forecast is not a separate permission to start.",
          "Откройте «Готовность системы» и текущее объяснение Auto на «Обзоре». Разбирайте конкретное условие отказа; зелёный прогноз не является отдельным разрешением запуска."
        ]
      },
      {
        "t": [
          "Verify the actual model, firmware and saved pair. Model selection does not enable unsupported firmware or turn two profiles of one tunnel into two channels.",
          "Проверьте фактические модель, прошивку и сохранённую пару. Выбор модели не включает неподдерживаемую прошивку и не превращает два профиля одного туннеля в два канала."
        ]
      },
      {
        "t": [
          "Use the persistent-preparation help for acceleration, IPv6, stock workers and routing policy. Inspect before changing anything; one checkbox alone is not evidence that preparation is complete.",
          "Для ускорения, IPv6, штатных служб и политик используйте помощь постоянной подготовки. Сначала проверяйте состояние; одна галочка не доказывает завершение подготовки."
        ]
      },
      {
        "t": [
          "Prepared MT3000 router-probed IPv4 Auto uses fresh router evidence without a LAN certificate. A separate client-confirmed trial requires its own LAN helper and certificate. Keep these modes distinct.",
          "Router-probed IPv4 Auto подготовленного MT3000 использует свежие проверки роутера без LAN-сертификата. Отдельному тесту с подтверждением клиента нужны собственные LAN-помощник и сертификат. Не смешивайте эти режимы."
        ]
      },
      {
        "t": [
          "Wait for current observations after changing profiles. Repeated Start clicks do not repair an identity, worker or policy mismatch. The Auto power button remains available to stop or cancel startup.",
          "После смены профилей дождитесь текущих наблюдений. Повторные нажатия Start не исправляют несовпадение идентичности, служб или политики. Кнопка Auto остаётся доступной для остановки или отмены запуска."
        ]
      }
    ]
  },
  {
    "id": "helper-what",
    "title": [
      "What is the LAN helper and how do I start it",
      "Что такое LAN-помощник и как его запустить"
    ],
    "when": [
      "You want independent client evidence or a separate bounded LAN-confirmed trial.",
      "Нужны независимые проверки клиента либо отдельный ограниченный LAN-тест."
    ],
    "steps": [
      {
        "t": [
          "The Windows PowerShell helper runs on a separate computer. SelfTest is offline; CheckOnly checks path prerequisites; ProbeOnly sends real bound DNS/HTTPS probes without starting Auto. The full trial changes application trial settings and may switch router traffic.",
          "PowerShell-помощник работает на отдельном Windows-компьютере. SelfTest автономный; CheckOnly проверяет предпосылки пути; ProbeOnly выполняет реальные привязанные DNS/HTTPS-проверки без включения Auto. Полный тест меняет настройки тестового режима приложения и может переключать трафик роутера."
        ]
      },
      {
        "t": [
          "PowerShell 7 is required. Install the stable Microsoft package if it is missing; this is a computer software installation, not a router command.",
          "Нужен PowerShell 7. Если его нет, установите стабильный пакет Microsoft; это установка программы на компьютер, а не команда роутера."
        ],
        "c": "winget install --id Microsoft.PowerShell --exact"
      },
      {
        "t": [
          "In Settings, open the separate LAN-trial panel and download client-test.ps1 plus start-lan-helper.ps1 into one folder. The optional start-lan-helper.cmd shortcut needs both of those files.",
          "В «Настройках» откройте отдельный LAN-тест и скачайте client-test.ps1 и start-lan-helper.ps1 в одну папку. Необязательный ярлык start-lan-helper.cmd требует наличия обоих файлов."
        ]
      },
      {
        "t": [
          "Run the launcher from that folder and enter the real private router address and the verified cable adapter number. A loopback browser gateway is not a LAN-witness target.",
          "Запустите помощник из этой папки и укажите реальный частный адрес роутера и проверенный номер кабельного адаптера. Локальный loopback-переход браузера не является целью LAN-проверки."
        ],
        "c": "pwsh -NoProfile -File .\\start-lan-helper.ps1"
      },
      {
        "t": [
          "Start with mode 1. It does not authenticate or change router/network settings and does not prove Internet health. For real DNS/HTTPS without a switching trial use ProbeOnly explicitly.",
          "Начните с режима 1. Он не выполняет вход и не меняет настройки роутера/сети, но ещё не доказывает работоспособность Интернета. Для реальных DNS/HTTPS без теста переключения отдельно используйте ProbeOnly."
        ]
      },
      {
        "t": [
          "Choose mode 3 only for an authorized bounded client-confirmed trial. Enter credentials privately and type TEST yourself. Read the final restoration result; queued Stop is not proof that the original client path returned. Finish any continuous Auto session and verify its normal Stop/recovery before starting this separate trial.",
          "Режим 3 выбирайте только для разрешённого ограниченного теста с подтверждением клиента. Введите пароль приватно и сами напечатайте TEST. Прочитайте итог восстановления; Stop в очереди не доказывает возврат исходного пути клиента. Перед отдельным тестом завершите непрерывный Auto и проверьте штатный Stop/восстановление."
        ]
      },
      {
        "t": [
          "The helper does not add/remove routes, change DNS/NIC settings or disable another VPN. A conflicting control route is refused before credentials or a session are sent.",
          "Помощник не добавляет и не удаляет маршруты, не меняет DNS/адаптеры и не отключает другой VPN. Обнаруженное несовпадение пути управления отклоняется до отправки пароля или сессии."
        ]
      }
    ]
  },
  {
    "id": "helper",
    "title": [
      "The LAN helper fails",
      "LAN-помощник не работает"
    ],
    "when": [
      "client-test.ps1 stops with a code before or during the trial.",
      "client-test.ps1 останавливается с кодом до теста или во время него."
    ],
    "steps": [
      {
        "t": [
          "Use the real router address and your cable adapter number in this prerequisite check; the example values are not universal.",
          "Подставьте реальный адрес роутера и номер своего кабельного адаптера; значения примера не универсальны."
        ],
        "c": "pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly"
      },
      {
        "t": [
          "Inspect adapter names and addresses without changing them. The cable must reach the intended router rather than another device using the same private subnet.",
          "Посмотрите имена и адреса адаптеров без изменений. Кабель должен вести к нужному роутеру, а не другому устройству с той же частной подсетью."
        ],
        "c": "Get-NetAdapter | Select-Object InterfaceIndex,Name,Status"
      },
      {
        "t": [
          "CLIENT-CONTROL-PATH-MISMATCH means the normal management route differs from the selected witness interface. Stop before logging in; establish an unambiguous management path. Do not change computer routing automatically.",
          "CLIENT-CONTROL-PATH-MISMATCH означает, что обычный путь управления отличается от выбранного интерфейса проверки. Не выполняйте вход до выяснения; обеспечьте однозначный путь управления. Не меняйте маршруты компьютера автоматически."
        ]
      },
      {
        "t": [
          "CLIENT-CABLE-HTTPS-FAILED or error 10051 can indicate a missing usable route on the selected cable. Inspect IPv4 interface properties; this read-only command does not repair them.",
          "CLIENT-CABLE-HTTPS-FAILED или ошибка 10051 могут означать отсутствие подходящего маршрута выбранного кабеля. Изучите свойства IPv4-интерфейсов; команда чтения не исправляет их."
        ],
        "c": "Get-NetIPInterface -AddressFamily IPv4 | Select-Object InterfaceIndex,InterfaceAlias,ConnectionState,IgnoreDefaultRoutes"
      },
      {
        "t": [
          "The current helper never creates temporary probe routes. If an old version left routes, identify their owner and a specific approved cleanup; do not delete unrelated routes.",
          "Текущий помощник не создаёт временных маршрутов проверки. Если они остались от старой версии, определите владельца и отдельный разрешённый способ очистки; не удаляйте посторонние маршруты."
        ],
        "c": "Get-NetRoute -DestinationPrefix 1.1.1.1/32,1.0.0.1/32"
      },
      {
        "t": [
          "A computer VPN or DNS protection can conflict with the selected client path. Diagnose ownership first; the helper does not stop those programs. CheckOnly, ProbeOnly and a full trial have different scopes.",
          "VPN или защита DNS компьютера могут конфликтовать с выбранным путём клиента. Сначала установите владельца; помощник сам не останавливает эти программы. CheckOnly, ProbeOnly и полный тест имеют разный объём действий."
        ]
      },
      {
        "t": [
          "Exit 0 is successful completion for the selected mode, not proof of all networks. Exit 2 is refusal/unverified/failure; exit 3 means a verified retained reserve rather than successful original-path restoration.",
          "Код 0 означает успешное завершение выбранного режима, а не проверку всех сетей. Код 2 — отказ/нет подтверждения/ошибка; код 3 — подтверждённое сохранение резерва вместо успешного восстановления исходного пути."
        ]
      }
    ]
  },
  {
    "id": "stale",
    "title": [
      "The page is old, empty or says the monitor is not running",
      "Страница старая, пустая или пишет, что мониторинг не работает"
    ],
    "when": [
      "After an update, the Overview looks old, shows errors, or the status is stale.",
      "После обновления «Обзор» выглядит по-старому, показывает ошибки или статус устарел."
    ],
    "steps": [
      {
        "t": [
          "Press Ctrl+F5 to reload without cache, then sign out of LuCI and sign in again (new permissions after an update).",
          "Нажмите Ctrl+F5 (обновление без кэша), затем выйдите из LuCI и войдите снова (после обновления права обновляются)."
        ]
      },
      {
        "t": [
          "Check the Monitoring indicator on Overview. If the monitor services are stopped, start those services over SSH and wait for a fresh timestamp; this is separate from Auto Start.",
          "Проверьте индикатор мониторинга на «Обзоре». Если службы остановлены, запустите их по SSH и дождитесь свежей даты; это отдельно от запуска Auto."
        ],
        "c": "homensai-vpn-emergency start"
      },
      {
        "t": [
          "If an update left RPC registration stale, reload rpcd deliberately and sign in again. This restarts the router RPC service and may interrupt management sessions; it is not a read-only inspection.",
          "Если после обновления устарела регистрация RPC, осознанно перезагрузите rpcd и войдите снова. Это перезапуск RPC-службы роутера с возможным разрывом сеансов управления, а не команда чтения."
        ],
        "c": "/etc/init.d/rpcd reload"
      },
      {
        "t": [
          "Check that exactly one monitor is running:",
          "Проверьте, что запущен ровно один монитор:"
        ],
        "c": "ps w | grep homensai-vpn"
      }
    ]
  },
  {
    "id": "outside-change",
    "title": [
      "I changed VPN rules in the GL.iNet panel and Auto stopped",
      "Я изменил правила VPN в панели GL.iNet, и Auto остановился"
    ],
    "when": [
      "The Overview says the VPN rules were changed by someone else.",
      "На «Обзоре» написано, что правила VPN изменил кто-то другой."
    ],
    "steps": [
      {
        "t": [
          "Auto refuses to compete with an external policy/profile edit. Read the actual controller phase and cleanup result; do not assume that every refused operation already restored Internet.",
          "Auto не должен конкурировать с внешней правкой политики/профиля. Прочитайте фактический этап контроллера и результат очистки; не считайте любой отказ уже восстановленным Интернетом."
        ]
      },
      {
        "t": [
          "Check the current selected pair and the stock VPN configuration. If you intend to edit stock profiles, finish managed Stop/recovery first.",
          "Проверьте текущую пару и штатную VPN-конфигурацию. Если намерены менять штатные профили, сначала завершите управляемый Stop/восстановление."
        ]
      },
      {
        "t": [
          "Wait for fresh consistent identities and readiness. Prepared continuous-pair mode can then be started explicitly; a legacy client-confirmed mode needs a new matching trial/certificate after a relevant edit.",
          "Дождитесь свежих согласованных идентичностей и готовности. Подготовленный непрерывный режим затем запускается явно; прежнему клиентскому режиму после существенной правки нужен новый соответствующий тест/сертификат."
        ]
      },
      {
        "t": [
          "Keep failed attempts and unrelated edits. Do not forge a confirmation, erase the journal or remove a foreign firewall table to make a status green.",
          "Сохраните неудачные попытки и посторонние правки. Не подделывайте подтверждения, не стирайте журнал и не удаляйте чужую таблицу firewall ради зелёного статуса."
        ]
      }
    ]
  },
  {
    "id": "telegram",
    "title": [
      "Telegram reports do not arrive",
      "Отчёты в Telegram не приходят"
    ],
    "when": [
      "The Overview shows a Telegram error, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.",
      "На «Обзоре» ошибка Telegram, тестовое сообщение не приходит или вы настраиваете Telegram впервые. Нужны три вещи: бот, его токен и ID чата."
    ],
    "steps": [
      {
        "t": [
          "Open the official https://t.me/BotFather in Telegram and send /newbot there, not in a terminal. Follow its current instructions.",
          "Откройте официальный https://t.me/BotFather в Telegram и отправьте /newbot именно в его чат, а не в терминал. Следуйте его текущим указаниям."
        ],
        "c": "/newbot"
      },
      {
        "t": [
          "BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).",
          "BotFather спросит имя (показывается в чате, любой текст, например «Мой VPN роутер») и затем username, который должен заканчиваться на «bot» (например my_router_vpn_bot)."
        ]
      },
      {
        "t": [
          "BotFather provides the bot token. Treat it as a password and paste it only into the dedicated private token field. Do not put it into a browser URL, chat, Git or diagnostic output.",
          "BotFather выдаёт токен бота. Храните его как пароль и вставляйте только в специальное приватное поле токена. Не помещайте его в адрес браузера, чат, Git или диагностический вывод."
        ]
      },
      {
        "t": [
          "Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.",
          "Откройте нового бота (ссылка в конце сообщения BotFather, https://t.me/<username_вашего_бота>) и нажмите Start или отправьте /start. Бот не может написать вам первым."
        ]
      },
      {
        "t": [
          "To read chat.id without adding a third-party bot, send /start or a message to your own bot, then use this PowerShell recipe locally. It asks for the token privately and prints only IDs. Do not record a transcript or share raw updates. If another bot program consumes updates, stop and inspect that configuration rather than invent an ID.",
          "Чтобы узнать chat.id без стороннего бота, отправьте /start или сообщение своему боту и выполните этот PowerShell-пример локально. Токен вводится скрыто, выводятся только ID. Не ведите transcript и не передавайте полный ответ. Если обновления забирает другая программа бота, сначала разберитесь с её настройкой, не придумывайте ID."
        ],
        "c": "$privateKey = Read-Host 'Bot token' -AsSecureString\n$botKey = [Net.NetworkCredential]::new('', $privateKey).Password\ntry {\n    $updates = Invoke-RestMethod -Uri ('https://api.telegram.org/bot' + $botKey + '/getUpdates') -TimeoutSec 15 -ErrorAction Stop\n    $ids = foreach ($item in $updates.result) {\n        foreach ($kind in @('message','channel_post','edited_message','my_chat_member')) {\n            if ($null -ne $item.$kind.chat.id) { [string]$item.$kind.chat.id }\n        }\n    }\n    $ids | Sort-Object -Unique\n} catch { Write-Output 'CHAT-ID-NOT-READ: check the bot token, a fresh /start and other update consumers.' }\nfinally { Remove-Variable privateKey,botKey,updates,ids -ErrorAction SilentlyContinue }"
      },
      {
        "t": [
          "On the router open Settings → All application settings → step 7 · Telegram, or the Telegram setup shortcut. Enter the token privately and the verified chat ID or channel username, review and save. Configure off preserves the existing Telegram settings.",
          "На роутере откройте «Настройки» → «Все настройки приложения» → шаг 7 · Telegram либо отдельную настройку Telegram. Введите токен приватно и проверенный ID чата/имя канала, проверьте и сохраните. Выключенный Configure сохраняет прежние настройки Telegram."
        ]
      },
      {
        "t": [
          "Press “Test Telegram delivery”. A message should arrive within a few seconds. If a code is shown instead: TELEGRAM-… with “401” or “Unauthorized” means a wrong token; “400”, “chat not found” or “Forbidden” means a wrong Chat ID or you never pressed Start; a timeout means the router has no internet or a wrong clock.",
          "Нажмите «Проверить доставку Telegram». Сообщение должно прийти за несколько секунд. Если показан код TELEGRAM-…: «401» или «Unauthorized» — неверный токен; «400», «chat not found» или «Forbidden» — неверный ID чата или вы не нажали Start; тайм-аут — у роутера нет интернета или неверные часы."
        ]
      },
      {
        "t": [
          "Still nothing? Create the token again in BotFather (/token or /revoke) and enter the new one. Never send the token to anyone, including in a support chat.",
          "Всё равно нет? Создайте токен заново в BotFather (/token или /revoke) и введите новый. Никому не отправляйте токен, в том числе в чат поддержки."
        ]
      }
    ]
  },
  {
    "id": "clock",
    "title": [
      "Dates are wrong, history or statistics are blocked",
      "Неверные даты, история или статистика заблокированы"
    ],
    "when": [
      "Codes like CLOCK-001 or HISTORY-001, or events with impossible dates.",
      "Коды вроде CLOCK-001 или HISTORY-001, либо события с невозможными датами."
    ],
    "steps": [
      {
        "t": [
          "The router clock must be correct. GL.iNet panel → System → Time: enable time synchronisation (NTP) and pick your time zone.",
          "Часы роутера должны быть верными. Панель GL.iNet → «Система» → «Время»: включите синхронизацию времени (NTP) и выберите часовой пояс."
        ]
      },
      {
        "t": [
          "Check the clock over SSH:",
          "Проверьте часы по SSH:"
        ],
        "c": "date"
      },
      {
        "t": [
          "After the clock is right, statistics continue by themselves. Gaps are shown as unobserved time and are never filled with invented numbers.",
          "После исправления часов статистика продолжится сама. Пропуски показываются как ненаблюдаемое время и никогда не заполняются выдуманными числами."
        ]
      }
    ]
  },
  {
    "id": "backup",
    "title": [
      "Make a backup before changes",
      "Резервная копия перед изменениями"
    ],
    "when": [
      "Before an update, a LAN trial or any manual repair.",
      "Перед обновлением, LAN-тестом или любым ручным исправлением."
    ],
    "steps": [
      {
        "t": [
          "First verify the intended router and SSH host key. Replace the example address. On Windows use binary redirection through cmd so Windows PowerShell does not decode the compressed stream. sysupgrade -b exports a backup; it does not flash firmware.",
          "Сначала проверьте нужный роутер и SSH-ключ. Замените адрес примера. В Windows используйте двоичное перенаправление через cmd, чтобы Windows PowerShell не перекодировал сжатый поток. sysupgrade -b экспортирует копию, а не прошивает устройство."
        ],
        "c": "cmd /c \"ssh root@192.168.8.1 sysupgrade -b - > router-backup.tar.gz\""
      },
      {
        "t": [
          "On Linux or macOS, redirect the binary export to a private local file. Check the SSH command result and read the archive before using it as recovery evidence.",
          "В Linux/macOS сохраните двоичный экспорт в приватный локальный файл. Проверьте результат SSH-команды и чтение архива до того, как считать его средством восстановления."
        ],
        "c": "ssh root@192.168.8.1 'sysupgrade -b -' > router-backup.tar.gz"
      },
      {
        "t": [
          "The archive contains secrets and this export is not encrypted by itself. Store it in protected encrypted storage, outside Git, and verify your encryption key and recovery procedure independently. Never upload the raw export or its key.",
          "Архив содержит секреты и сам по себе этим экспортом не шифруется. Храните его в защищённом зашифрованном хранилище вне Git, отдельно проверьте ключ шифрования и способ восстановления. Не загружайте исходный экспорт или ключ."
        ]
      }
    ]
  },
  {
    "id": "remove",
    "title": [
      "Remove or roll back the program",
      "Удалить программу или откатить версию"
    ],
    "when": [
      "You want the router without this program, or you need an older version.",
      "Нужен роутер без этой программы или более старая версия."
    ],
    "steps": [
      {
        "t": [
          "Complete normal Stop and verify the actual managed recovery and guard state before removing the package. If Stop retained a reserve or recovery is unconfirmed, resolve the recorded condition first; do not force a return to an unhealthy primary. Then remove normally over SSH.",
          "Перед удалением завершите штатный Stop и проверьте фактическое управляемое восстановление и блокировки. Если остался резерв либо итог не подтверждён, сначала разберите записанное условие; не форсируйте возврат на неисправный основной. Затем удаляйте штатно по SSH."
        ],
        "c": "opkg remove homensai-auto-vpn"
      },
      {
        "t": [
          "Removal is not a complete data wipe. Preserve a private backup and check the actual conffile/history state before reinstalling; do not rely on unmodified defaults being retained by opkg.",
          "Удаление пакета не является полной очисткой данных. Сохраните приватную копию и проверьте фактическое состояние конфигурации/истории перед переустановкой; не полагайтесь на сохранение неизменённых значений opkg."
        ]
      },
      {
        "t": [
          "If the removal is refused, the program tells why (for example a transaction is active). Do not force it: first use “I have no internet”.",
          "Если удаление отклонено, программа объяснит причину (например, активна транзакция). Не форсируйте: сначала выполните раздел «У меня пропал интернет»."
        ]
      }
    ]
  },
  {
    "id": "report",
    "title": [
      "What to send when asking for help",
      "Что отправить, когда просите о помощи"
    ],
    "when": [
      "You report a problem and want it solved quickly.",
      "Вы сообщаете о проблеме и хотите решить её быстро."
    ],
    "steps": [
      {
        "t": [
          "Record the time, installed/running version, selected channel and the exact code. Keep command output local until addresses, policy names, tokens, session values and private transaction data are removed.",
          "Запишите время, установленную/работающую версию, выбранный канал и точный код. Храните вывод локально, пока не удалены адреса, имена политик, токены, сессии и приватные данные транзакций."
        ],
        "c": "homensai-vpn-emergency show"
      },
      {
        "t": [
          "Check the installed package version. It can differ from a cached browser page or running process after an interrupted update.",
          "Проверьте версию установленного пакета. После прерванного обновления она может отличаться от кешированной страницы или работающего процесса."
        ],
        "c": "opkg status homensai-auto-vpn | grep Version"
      },
      {
        "t": [
          "Read the relevant recent log locally. Share only a reviewed redacted excerpt, not the complete configuration or archive.",
          "Прочитайте относящийся к проблеме свежий журнал локально. Передавайте только проверенную обезличенную выборку, а не весь конфиг или архив."
        ],
        "c": "logread | grep -i homensai | tail -30"
      },
      {
        "t": [
          "Never send passwords, Telegram tokens, cookies, SSH/VPN keys, full backups or private certificate/transaction nonces. A screenshot can contain addresses and identifiers too.",
          "Не отправляйте пароли, токены Telegram, cookies, ключи SSH/VPN, полные копии и приватные значения сертификатов/транзакций. Скриншоты тоже могут содержать адреса и идентификаторы."
        ]
      }
    ]
  },
  {
    "id": "history-retention",
    "title": [
      "Journal size and retained history",
      "Размер журнала и срок истории"
    ],
    "when": [
      "You want less browser memory or fewer saved observation days.",
      "Нужно уменьшить память браузера или срок сохранённых наблюдений."
    ],
    "steps": [
      {
        "t": [
          "Settings → Monitoring and history retention: choose an integer live buffer from 1 to 2000 and detail retention from 1 to 7 days. Save and verify the values.",
          "«Настройки» → «Мониторинг и хранение истории»: выберите целый лимит от 1 до 2000 наблюдений и срок от 1 до 7 дней. Сохраните и проверьте значения."
        ]
      },
      {
        "t": [
          "The buffer limits browser observations; the period prunes stored details during processing/checkpoints. Monthly/lifetime counters remain separate. Increasing the period cannot restore removed detail.",
          "Буфер ограничивает наблюдения браузера; срок очищает сохранённые подробности при обработке/checkpoint. Месячные и общие счётчики остаются отдельно. Увеличение срока не возвращает удалённые подробности."
        ]
      },
      {
        "t": [
          "Events and errors initially shows the latest 20 rows, with a triangle for more. Search and sorting use the downloaded retained snapshot, not just the visible rows.",
          "«События и ошибки» сначала показывает 20 последних строк, остальные — под треугольником. Поиск и сортировка используют загруженную сохранённую историю, а не только видимые строки."
        ]
      }
    ]
  },
  {
    "id": "controlled-fault",
    "title": [
      "Test a transition from the current channel",
      "Проверить переход с текущего канала"
    ],
    "when": [
      "You want a deliberate bounded traffic fault and a verified alternate route.",
      "Нужен преднамеренный ограниченный сбой трафика с проверкой другого маршрута."
    ],
    "steps": [
      {
        "t": [
          "Open Advanced settings → Tests → Controlled VPN tunnel traffic fault. The current working channel is selected automatically; primary and reserve are both supported.",
          "Откройте «Расширенные настройки» → «Тесты» → «Контролируемый сбой трафика VPN-туннеля». Текущий рабочий канал выбирается автоматически: поддержаны основной и резервный."
        ]
      },
      {
        "t": [
          "The router rechecks running Auto, private current-pair identity/policy, both healthy paths and session-loss consent. A preparation explanation means the destructive action has not started. Do not bypass a refusal.",
          "Роутер повторно проверяет работающий Auto, закрытые данные текущей пары/политики, исправность обоих путей и согласие на разрыв сессий. Экран подготовки означает, что сбой ещё не запущен. Не обходите отказ."
        ]
      },
      {
        "t": [
          "The test temporarily drops IPv4 traffic on that tunnel device, not the VPN process or another server selected by name. It waits for failure thresholds and a fresh confirmed alternate route. Stop test and restore traffic removes the artificial fault early.",
          "Тест временно блокирует IPv4-трафик устройства туннеля, а не VPN-процесс и не другой сервер по имени. Он ожидает пороги ошибок и свежий подтверждённый другой маршрут. «Остановить тест и снять сбой» досрочно снимает искусственную блокировку."
        ]
      },
      {
        "t": [
          "Only a confirmed route with fresh successful observations is success. A timeout removes the artificial block but is not a passed transition; inspect the reason, cooldown, budget and both channels. Kernel expiry is a safety limit, not proof of Internet.",
          "Успех — только подтверждённый маршрут со свежими успешными наблюдениями. Таймаут снимает блокировку, но не означает пройденный переход: изучите причину, паузу, бюджет и оба канала. Истечение правила ядром — ограничение сбоя, а не доказательство Интернета."
        ]
      }
    ]
  },
  {
    "id": "address-conflict",
    "title": [
      "The router page opens the wrong device or refuses connection",
      "Открывается другой роутер или отказано в подключении"
    ],
    "when": [
      "Two networks use the same private address, or the browser chooses another adapter.",
      "Две сети используют один частный адрес либо браузер выбирает другой адаптер."
    ],
    "steps": [
      {
        "t": [
          "Verify the intended model and the physical management connection first. The same IPv4 address can identify different devices on different adapters; a responding web page is not sufficient identity.",
          "Сначала подтвердите модель и физический путь управления. Один IPv4-адрес может вести к разным устройствам через разные адаптеры; ответ веб-страницы ещё не доказывает идентичность."
        ]
      },
      {
        "t": [
          "Inspect IPv4 addresses and interface indexes read-only. Do not silently change Wi-Fi, adapter addresses, routes or another router to fix a page.",
          "Посмотрите IPv4-адреса и номера интерфейсов только чтением. Не меняйте незаметно Wi-Fi, адреса адаптеров, маршруты или другой роутер ради открытия страницы."
        ],
        "c": "Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceIndex,InterfaceAlias,IPAddress"
      },
      {
        "t": [
          "A separately verified fixed-target local gateway may provide browser access without network-setting changes. It is machine-local and temporary; it does not replace the real LAN router address for a client witness or remove router authentication.",
          "Отдельно проверенный локальный переход к фиксированному роутеру может дать доступ браузеру без изменения сетевых настроек. Он локален для компьютера и временный: не заменяет реальный LAN-адрес для клиентской проверки и не отменяет вход на роутер."
        ]
      }
    ]
  }
];

function richText(text){return String(text).split('`').map(function(part,i){return i%2?E('code',{'class':'hv-code'},part):part;});}
function helpCommand(command){
  var button=E('button',{'type':'button','class':'cbi-button','click':function(){
    try{navigator.clipboard.writeText(command).then(function(){button.textContent=bi('Copied','Скопировано');}).catch(function(){});}catch(error){}
  }},bi('Copy','Копировать'));
  return E('div',{'class':'hv-cmd-row'},[E('pre',{'class':'hv-cmd'},command),button]);
}
function helpDiagnosticPrompt(topic){
  var heading=bi(topic.title[0],topic.title[1]),context=bi(topic.when[0],topic.when[1]);
  return bi('Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: ','Проверь эту проблему HomenS.AI Auto VPN на конкретном указанном мной роутере: ')+heading+'.\n'+context+'\n'+
    bi('Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.\n','Уточни только недостающие симптомы, адрес устройства, ОС и защищённый доступ к инструментам. Начни только с чтения: реальная модель/прошивка, установленная/работающая версия, состояние монитора/Auto/пары и свежие данные этого раздела. Сопоставь ожидаемое поведение с наблюдениями и пошагово сузь причину. Сам используй терминал/браузер, если доступны; иначе честно укажи ограничения и запрашивай по одному полезному наблюдению.\n')+
    bi('Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.\n','Не запрашивай секреты в чат и не печатай полные конфигурации. Это только диагностика: без изменений сети/прошивки/пакетов/настроек, Start/Stop Auto, тестов сбоя, сообщений и принятия соглашения без отдельной команды на исправление. Не обходи отказы. Отчитайся: факты, гипотезы, точные коды, проверенное/непроверенное и минимальное подтверждённое исправление; сохрани точку остановки.\n')+
    'https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md';
}
function generalDiagnosticPrompt(){
  return bi('Find why HomenS.AI Auto VPN does not work, even if I cannot identify the right Help topic. Work systematically and perform available diagnostics yourself.','Найди, почему HomenS.AI Auto VPN не работает, даже если я не могу выбрать нужный раздел помощи. Действуй последовательно и сам выполняй доступную диагностику.')+'\n\n'+
    bi('1. Ask for the symptom, expected result, when it began, target router and tool access. Do not ask questions already answered by available evidence.\n2. Read project CURRENT-STATUS, installation and Help. Inventory actual model/firmware, installed/running versions, package integrity, services, logs, freshness and storage read-only.\n3. Separate monitor errors, missing dependencies, stale UI/RPC, unconfigured pair, tunnel connection, selected traffic route, DNS/HTTPS failure, platform refusal and client-LAN proof. Router probes alone do not prove client internet.\n4. Build a short hypothesis list. For each run the smallest read-only test that can support or reject it; retain timestamps/error codes and do not repeat irrelevant tests.\n5. Inspect the matching Help topic and copied diagnostic prompt. If tools are unavailable, explain the limit and ask for one safe observation; never invent command output.\n6. Produce a concrete minimal repair plan and rollback. Diagnosis does not authorize package/network/DNS/firewall/firmware changes, Auto Start/Stop, fault trials, Telegram messages or terms acceptance. Request the missing repair scope only when the evidence and concrete fix are ready.\n7. After an authorized repair, repeat its actual failing check and verify fresh service/UI/configuration state. Preserve failed attempts and unrelated owner settings.\n8. Report PASS/FAIL/PARTIAL/BLOCKED/UNKNOWN by area, known causes versus hypotheses, what changed, remaining limits and the next safe step. Never print credentials/full configs or claim a short/router-only test proves24hours/LAN/IPv6/hardware safety.\n','1. Уточни симптом, ожидаемый результат, время появления, нужный роутер и доступ к инструментам. Не переспрашивай то, что уже видно в данных.\n2. Прочитай CURRENT-STATUS, установку и помощь проекта. Только чтением проверь реальную модель/прошивку, установленную/работающую версии, целостность пакета, службы, журналы, свежесть и место.\n3. Разделяй ошибку мониторинга, зависимости, старый UI/RPC, ненастроенную пару, подключение туннеля, выбранный маршрут, DNS/HTTPS, отказ платформы и LAN-клиента. Проверки роутера не доказывают интернет клиента.\n4. Составь короткий список гипотез. Для каждой выполни минимальную проверку чтением, которая её подтверждает или исключает. Сохраняй время/коды, не повторяй бесполезные тесты.\n5. Используй соответствующий раздел помощи и его промпт. Без инструментов объясни ограничение и попроси одно безопасное наблюдение; не выдумывай вывод команд.\n6. Подготовь конкретное минимальное исправление и отмену. Диагностика не разрешает изменения пакетов/сети/DNS/firewall/прошивки, Start/Stop Auto, тесты сбоя, сообщения Telegram и принятие соглашения. Недостающий объём исправления уточни только после готового проверяемого решения.\n7. После разрешённого исправления повтори именно провалившуюся проверку и проверь свежие службы/UI/настройки. Сохрани неудачные попытки и чужие изменения владельца.\n8. Отчитайся PASS/FAIL/PARTIAL/BLOCKED/UNKNOWN по областям: подтверждённые причины отдельно от гипотез, что изменено, ограничения и безопасный следующий шаг. Не печатай секреты/конфиги и не выдавай короткий/router-only тест за сутки/LAN/IPv6/аппаратную безопасность.\n')+
    'https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn';
}
function renderDiagnosticPrompt(topic,all){
  var prompt=all?generalDiagnosticPrompt():helpDiagnosticPrompt(topic),field=E('textarea',{'readonly':'readonly','rows':all?'12':'6','class':'hv-diagnostic-prompt','aria-label':bi('Diagnostic prompt','Промпт диагностики'),'style':'width:100%;max-height:280px;box-sizing:border-box'});field.value=prompt;
  var button=E('button',{'type':'button','class':'cbi-button','data-diagnostic-copy':all?'all':topic.id,'click':function(){
    function select(){field.focus();field.select();}
    if(typeof navigator!=='undefined'&&navigator.clipboard)return navigator.clipboard.writeText(prompt).then(function(){button.textContent=bi('Copied','Скопировано');}).catch(select);
    select();
  }},bi('Copy diagnostic prompt','Скопировать промпт диагностики'));
  return E('div',{'class':'hv-help-diagnostic','data-diagnostic-topic':all?'all':topic.id},[E('h4',{},bi('Ask ChatGPT/Codex or Claude to diagnose','Проверить с помощью ChatGPT/Codex или Claude')),E('p',{},bi('The agent needs tools on your computer and router access. Copying runs no commands. Diagnosis does not authorize repairs.','Агенту нужны инструменты на компьютере и доступ к роутеру. Копирование не запускает команды. Диагностика не разрешает исправления.')),button,field]);
}
function renderHelpTraining(){
  var course=null,container=E('div',{'class':'hv-help-course','hidden':'hidden'}),open=false,section;
  function toggle(){
    open=!open;container.hidden=!open;button.setAttribute('aria-expanded',String(open));
    button.textContent=open?bi('Hide training','Свернуть обучение'):bi('Start or continue training','Начать или продолжить обучение');
    if(open&&!course){course=typeof renderLearn==='function'?renderLearn():E('a',{'href':'#learn'},bi('Open training','Открыть обучение'));container.appendChild(course);}
  }
  var button=E('button',{'type':'button','class':'cbi-button cbi-button-action','aria-expanded':'false','click':function(){return typeof learnKeepViewport==='function'?learnKeepViewport(section,toggle):toggle();}},bi('Start or continue training','Начать или продолжить обучение'));
  container.hidden=true;
  section=E('section',{'class':'hv-help-training','data-help-training':'1'},[E('h3',{},bi('Learn to use Auto VPN','Как пользоваться Auto VPN')),E('p',{},bi('Explanation, interactive diagrams and questions. Jump to any question, see your score and repeat only the answers you missed. Training never switches the router.','Объяснения, интерактивные схемы и вопросы. Можно перейти к любому вопросу, увидеть баллы и повторить только ошибки. Обучение не переключает роутер.')),button,container]);return section;
}
function renderAutoSchematic(inventory){
  var s=inventory&&inventory.settings||{};
  function value(k){var v=s[k];return typeof v==='number'&&Number.isFinite(v)&&v>=0?String(v):'—';}
  function box(title,text,kind){return E('div',{'class':'hv-schematic-box hv-schematic-'+kind},[E('strong',{},title),E('span',{},text)]);}
  function arrow(){return E('div',{'class':'hv-schematic-arrow','aria-hidden':'true'},'↓');}
  var sec=bi(' s',' с'),minutes=bi(' min',' мин');
  var hold=s.recovery_return_policy==='hold_reserve',knownPolicy=hold||s.recovery_return_policy==='healthy_primary';
  return E('section',{'class':'hv-auto-schematic','data-auto-schematic':'1','aria-label':bi('Auto operation diagram','Принципиальная схема работы Auto')},[
    E('h3',{},bi('Auto operation diagram','Принципиальная схема работы Auto')),
    E('p',{'class':'hv-schematic-intro'},bi('The controller observes the two selected VPN channels and switches only after the required checks and safeguards.','Контроллер наблюдает за двумя выбранными VPN-каналами и переключает их только после необходимых проверок и защитных условий.')),
    E('div',{'class':'hv-schematic-flow'},[
      box(bi('Primary and reserve VPN','Основной и резервный VPN'),bi('Existing VPN connections on the router','Существующие VPN-подключения роутера'),'channels'),arrow(),
      box(bi('Monitor','Мониторинг'),bi('DNS and HTTPS checks · interval: ','Проверки DNS и HTTPS · интервал: ')+value('interval')+sec,'monitor'),arrow(),
      box(bi('Decision to switch','Решение о переключении'),bi('Primary failures in a row: ','Сбоев основного подряд: ')+value('recovery_failures')+' · '+bi('successful reserve checks: ','успешных проверок резерва: ')+value('recovery_successes'),'decision'),arrow(),
      box(bi('Safety limits','Защитные ограничения'),bi('Cooldown between attempts: ','Пауза между попытками: ')+value('recovery_cooldown')+sec+' · '+bi('maximum attempts: ','максимум попыток: ')+value('recovery_attempt_limit')+' / '+value('recovery_attempt_window')+minutes,'limits'),arrow(),
      box(bi('Switch to reserve','Переключение на резерв'),bi('The controller changes the route and verifies the result. Minimum reserve dwell: ','Контроллер меняет маршрут и проверяет результат. Минимальное время на резерве: ')+value('recovery_min_dwell')+sec,'reserve'),arrow(),
      box(bi('Return to primary','Возврат на основной'),!knownPolicy?bi('Return policy unavailable.','Правило возврата недоступно.'):hold?bi('Automatic return is disabled by the selected hold-reserve policy.','Автоматический возврат отключён выбранным правилом удержания резерва.'):bi('Primary successes: ','Успешных проверок основного: ')+value('recovery_primary_successes')+' · '+bi('stable for at least: ','стабильность не менее: ')+value('recovery_primary_stable')+sec,'return')
    ]),
    E('p',{'class':'hv-schematic-note'},bi('When automatic return is enabled and the reserve fails, a verified primary may be restored earlier than the normal reserve dwell. Settings → Auto switching rules contains these values. A dash means the router did not provide a value.','Если автоматический возврат включён и резерв отказал, проверенный основной может быть возвращён раньше обычной паузы пребывания на резерве. Значения меняются в «Настройки → Правила переключения Auto». Прочерк означает, что роутер не передал значение.')),
    E('p',{'class':'hv-schematic-note'},bi('Router DNS/HTTPS checks do not independently prove the path of every LAN device.','DNS/HTTPS-проверки роутера отдельно не подтверждают работу каждого устройства в локальной сети.'))
  ]);
}
function renderHelp(inventory){
  var setupGuide=false;try{setupGuide=new URL(window.location.href).searchParams.get('setup_help')==='1';}catch(e){}
  var topics=(setupGuide?HELP_TOPICS.filter(function(topic){return topic.id==='setup-guide';}):HELP_TOPICS).map(function(topic){
    var steps=topic.custom?topic.custom():E('ol',{'class':'hv-help-steps'},topic.steps.map(function(step){
      return E('li',{},[E('p',{},richText(bi(step.t[0],step.t[1]))),step.c?helpCommand(step.c):null].filter(Boolean));
    }));
    var attributes={'class':'hv-help-topic','id':'help-'+topic.id};
    if(topic.open||setupGuide&&topic.id==='setup-guide')attributes.open='open';
    return E('details',attributes,[E('summary',{},bi(topic.title[0],topic.title[1])),E('p',{'class':'hv-help-when'},bi(topic.when[0],topic.when[1])),steps,topic.id!=='diagnose-all'?renderDiagnosticPrompt(topic,false):null].filter(Boolean));
  });
  return E('section',{'class':'hv-chart-card hv-help'},[
    E('h2',{},setupGuide?bi('First setup: steps 1–8','Первая настройка: шаги 1–8'):bi('Help and recovery','Помощь и восстановление')),
    !setupGuide?renderAutoSchematic(inventory):null,
    !setupGuide?renderHelpTraining():null,
    E('p',{},setupGuide?bi('Return to the setup tab after reading. This guide changes no settings and keeps your draft. Examples are starting points; keep suitable existing values.','После чтения вернитесь во вкладку мастера. Помощь ничего не меняет и сохраняет ваш черновик. Примеры — отправная точка; подходящие текущие значения можно оставить.'):bi('Pick the situation that matches. Commands are typed on the router over SSH (see “How to connect by SSH”); the Copy button copies a command so you can paste it.','Выберите подходящую ситуацию. Команды вводятся на роутере по SSH (см. «Как подключиться по SSH»); кнопка «Копировать» копирует команду, чтобы вставить её в терминал.'))
  ].concat(topics).filter(Boolean));
}

var helpNode=null,learnNode=null;
function renderOnboardingGuide(){
  var steps=[
    ['Language and appearance','Язык и оформление',
     'Keep Automatic detection for the router model. Choose English or Russian; the page translates immediately. Pick a readable theme and layout. Example: automatic model, English, system theme, Calm layout.',
     'Оставьте автоопределение модели роутера. Выберите русский или английский — страница переведётся сразу. Выберите удобную тему и оформление. Пример: автоопределение, русский, тема как в системе, спокойное оформление.'],
    ['Monitoring','Мониторинг',
     'The interval controls how often VPN Internet is checked. Example: 10 seconds, checkpoint 900 seconds, profile limit 2 for a selected pair. Checkpoints save statistics to flash. In Settings → Monitoring and history retention, choose 1–2000 live journal observations and 1–7 days of detailed history. Monthly and lifetime counters remain separate; increasing the period cannot restore deleted detail. Keep the current profile limit if you monitor more profiles. During Auto startup the monitor temporarily checks more frequently; saving this step does not start Auto.',
     'Интервал задаёт частоту проверки Интернета через VPN. Пример: 10 секунд, checkpoint 900 секунд, лимит 2 профиля для выбранной пары. Checkpoint сохраняет статистику во flash-память. В «Настройки» → «Мониторинг и хранение истории» задайте 1–2000 наблюдений живого журнала и 1–7 дней подробной истории. Месячные и общие счётчики хранятся отдельно; увеличение срока не восстанавливает удалённые подробности. Если наблюдаете больше профилей, оставьте подходящий текущий лимит. При запуске Auto проверки временно учащаются; сохранение этого шага не включает Auto.'],
    ['Existing VPN profiles and trial preferences','Существующие VPN и параметры теста',
     'Create and connect VPN profiles in the router VPN panel first. Assign profiles to two distinct client tunnels in the stock VPN app first. The prepared MT3000 uses one WireGuard and one OpenVPN client; either can be primary. The selector lists these configured clients, not every saved server. Names and countries are examples; choose your own working profiles. If either is missing, defer pair setup and return later. Trial duration is in minutes; acknowledge that calls and sessions may reconnect before running a trial. A trial is separate from ordinary Auto startup.',
     'Сначала создайте и подключите VPN-профили в VPN-панели роутера. Сначала назначьте профили двум разным клиентским туннелям в штатном VPN-приложении. На подготовленном MT3000 это один клиент WireGuard и один OpenVPN; любой может быть основным. Список показывает настроенные клиенты, а не весь каталог серверов. Названия и страны приведены для примера; выбирайте свои рабочие профили. Если профилей нет, отложите настройку пары и вернитесь позже. Длительность теста задаётся в минутах; перед тестом подтвердите, что звонки и сессии могут переподключиться. Тест выполняется отдельно от обычного запуска Auto.'],
    ['Server names and priorities','Названия и приоритеты серверов',
     'Use names you can recognize, for example Germany primary and Germany reserve. The channel field groups related profiles; default is suitable for one pair. Smaller priority numbers come first: for example 10 before 20. Priority does not replace the explicit primary/reserve choices in step 3. Enable monitoring only for profiles you want checked; saving names never connects an inactive VPN.',
     'Задайте понятные названия, например Германия основной и Германия резерв. Поле канала объединяет связанные профили; для одной пары подходит default. Меньшее число приоритета идёт раньше: например 10 перед 20. Приоритет не заменяет явный выбор основного и резерва на шаге 3. Включайте наблюдение для нужных профилей; сохранение названия не подключает неактивный VPN.'],
    ['Recovery rules','Правила восстановления',
     'Avoid switching after a single failed check. Example: 3 primary failures, 2 successful reserve checks, cooldown 180 seconds and minimum dwell 180 seconds. For automatic primary return: 3 successful primary checks and 60 seconds of stable primary health. Keep a healthy reserve for operator review if you do not want automatic return. Counts are checks, while cooldown and stability are time intervals.',
     'Не переключайте канал из-за одной неудачной проверки. Пример: 3 сбоя основного, 2 успешные проверки резерва, пауза 180 секунд и минимальное время работы 180 секунд. Для возврата на основной: 3 успешные проверки и 60 секунд устойчивой работы. Если автоматический возврат не нужен, выберите сохранение рабочего резерва до решения оператора. Счётчики означают проверки, а пауза и стабильность задаются временем.'],
    ['Optional speed tests','Необязательные тесты скорости',
     'Speed tests consume traffic and are not required for initial Auto setup. Below the table two live charts show primary/reserve download (green) and upload (blue), refreshed every second. Channels are tested in sequence and waiting is explicit. The horizontal axis is elapsed seconds; missing data/errors are not zero speed. Completed averages are separate collapsed history. You can leave them disabled at first. An example for later is 8 MiB per test, 5 seconds, 2 streams and a 128 MiB daily budget. Review your traffic allowance before enabling automatic tests for new profiles. Actual usage is limited by the configured budgets.',
     'Тесты скорости расходуют трафик и не обязательны для первого запуска Auto. Сначала их можно оставить выключенными. Пример на будущее: 8 МиБ на тест, 5 секунд, 2 потока, суточный бюджет 128 МиБ. Перед автоматическими тестами новых профилей проверьте свой лимит трафика. Расход ограничивается настроенными бюджетами. После запуска под таблицей видны два графика: основной и резервный VPN. Они обновляются каждую секунду по реальным переданным данным; скачивание зелёное, отдача синяя. Каналы тестируются по очереди: второй ожидает. По горизонтали — секунды от начала теста канала. Пропуски и ошибки не рисуются нулевой скоростью. Старые итоговые результаты находятся отдельно в свёрнутой истории.'],
    ['Optional Telegram reports','Необязательные отчёты Telegram',
     'You can skip Telegram. Leaving Configure off preserves an existing Telegram configuration. To configure it, create your bot with BotFather, send /start to the bot, enter its token and your destination, then choose the report contents and schedule. Example: a daily report at 07:00 Europe/Berlin. Never share the bot token in screenshots or reports.',
     'Telegram можно пропустить. Выключенная настройка Configure сохраняет уже существующую конфигурацию Telegram. Для подключения создайте своего бота через BotFather, отправьте боту /start, укажите токен и получателя, выберите содержание и расписание. Пример: ежедневный отчёт в 07:00 по Europe/Berlin. Не показывайте токен бота на снимках экрана и в отчётах.'],
    ['Review all settings','Проверьте все настройки',
     'Check the model, primary/reserve pair, intervals and optional features. Back lets you correct a value. Save all settings writes the reviewed configuration; Next alone only moves through the draft. If saving is refused while Auto is active, open the dashboard, turn Auto off and return to finish saving. Afterwards open Overview, check the two VPN channels and explicitly start Auto. To skip setup, use the green button below navigation: current router settings remain unchanged, the draft is not saved, and you can resume through Settings → All application settings.',
     'Проверьте модель, основной и резервный профили, интервалы и необязательные функции. Кнопка «Назад» позволяет исправить значения. «Сохранить все настройки» записывает проверенную конфигурацию; «Далее» только перемещает по черновику. Если сохранение запрещено при работающем Auto, откройте панель, выключите Auto и вернитесь для сохранения. Затем откройте «Обзор», проверьте оба VPN и явно включите Auto. Для пропуска мастера используйте зелёную кнопку под навигацией: текущие настройки роутера останутся прежними, черновик не сохранится, а продолжить можно через «Настройки → Все настройки приложения».']
  ];
  return E('div',{'class':'hv-setup-guide','data-setup-guide':'1'},[
    E('p',{},bi('Before step 1, first-time setup shows the experimental-software agreement and MIT License. Read it, tick the confirmations and accept to continue. Previously accepted terms are remembered on this router. Next comes a short explanation with three diagrams; press OK to open the wizard.','Перед шагом 1 при первом запуске показывается соглашение об экспериментальном ПО и лицензии MIT. Прочитайте его, отметьте подтверждения и примите условия. Ранее принятое соглашение сохраняется на этом роутере. Затем откроется краткое объяснение с тремя схемами; нажмите OK для перехода к мастеру.')),
    E('ol',{'class':'hv-help-steps'},steps.map(function(row,index){return E('li',{'data-setup-guide-step':String(index+1)},[E('h3',{},bi(row[0],row[1])),E('p',{},bi(row[2],row[3]))]);}))
  ]);
}
HELP_TOPICS.push({id:'setup-guide',open:false,title:['First setup: eight steps with examples','Первая настройка: восемь шагов с примерами'],when:['Help for the complete setup wizard. Reading it saves nothing.','Помощь по общему мастеру настройки. Чтение ничего не сохраняет.'],steps:[],custom:renderOnboardingGuide});
if(typeof READINESS_GUIDES!=='undefined'){
  Object.keys(READINESS_GUIDES).forEach(function(code){var label=READINESS_CHECKS[code];
    HELP_TOPICS.push({id:'dependency-'+code,title:[label[0]+': install or repair',label[1]+': установка или исправление'],when:['A required router check failed or is unknown.','Нужный компонент отсутствует или его состояние неизвестно.'],steps:[],custom:function(){return renderReadinessHelp(code);}});
  });
}
HELP_TOPICS.push({id:'router-preparation',title:['Persistent router preparation: inspect before changing','Постоянная подготовка роутера: проверка до изменений'],when:['A preparation row is red or unverified. This is separate from installing application dependencies.','Пункт подготовки красный или не проверен. Это отдельная задача от установки зависимостей приложения.'],steps:[
  {t:['Read the actual model, firmware and fresh preparation table. The current profile is for prepared MT3000/4.11.0. Saved settings and loaded modules alone do not prove runtime readiness.','Проверьте реальную модель, прошивку и свежую таблицу подготовки. Текущая проверенная конфигурация относится к MT3000/4.11.0. Сохранённые флаги и загруженные модули сами по себе не доказывают готовность.']},
  {t:['Before changing acceleration, stock VPN startup or DNS, preserve a verified private backup and the exact original values/files. Establish the specific preparation scope and undo procedure; do not copy another device\'s commands blindly.','Перед изменением ускорения, штатного запуска VPN или DNS сохраните проверенную приватную копию и исходные значения/файлы. Определите конкретный объём подготовки и отмену; не копируйте команды другого роутера вслепую.']},
  {t:['Do not force-unload modules, remove drivers, disable a working DNS owner or alter computer networking. Recheck fresh status after the approved changes. A green preparation table does not start Auto or prove external LAN connectivity. The full operation/undo record is docs/ROUTER-PREPARATION.md in the project repository.','Не выгружайте модули принудительно, не удаляйте драйверы, не отключайте работающего DNS-владельца и не меняйте сеть компьютера. После разрешённых изменений перепроверьте свежие данные. Зелёная подготовка не запускает Auto и не доказывает связь LAN. Полная инструкция с отменой — docs/ROUTER-PREPARATION.md в репозитории проекта.']}
]});
HELP_TOPICS.push({id:'diagnose-all',title:['Cannot find the cause: complete AI diagnosis','Причина неизвестна: полная диагностика с ИИ'],when:['No Help topic explains your symptoms or several parts fail together.','Подходящий ответ не найден либо одновременно не работают несколько частей.'],steps:[],custom:function(){return renderDiagnosticPrompt(null,true);}});
HELP_TOPICS.push({id:'network-acceleration',title:['Auto blocked: hardware and network acceleration','Auto заблокирован: аппаратное и сетевое ускорение'],when:['Start reports HNAT, hardware acceleration or PREP-HNAT-CONFIG.','Запуск сообщает об HNAT, аппаратном ускорении или PREP-HNAT-CONFIG.'],steps:[],custom:function(){return renderAutoRemedy('HARDWARE-ACCELERATOR-UNVERIFIED');}});
HELP_TOPICS.push({id:'preparation-buttons',title:['Disable a blocking router setting here','Отключить мешающую настройку прямо здесь'],when:['A preparation reason offers a Disable button next to the menu link.','Рядом с причиной подготовки и ссылкой на меню есть кнопка отключения.'],steps:[
 {t:['Press the button for that exact reason. The first request only reads the current router/model and prepares a review. Cancel leaves settings unchanged.','Нажмите кнопку у конкретной причины. Первый запрос только читает текущий роутер/модель и готовит обзор. «Отмена» сохраняет настройки без изменений.']},
 {t:['Apply only the displayed change. The app preserves its original values privately, checks that Auto is stopped and recovery is complete, rejects changed reviews, then reads the result again. No VPN reconnect, Auto Start or automatic reboot occurs.','Примените только показанное изменение. Приложение приватно сохраняет исходные значения, проверяет остановку Auto и завершение восстановления, отвергает изменившийся обзор и читает результат заново. VPN не переподключается, Auto не запускается, автоматической перезагрузки нет.']},
 {t:['Startup switches do not stop a running service. SFE module autoload preserves the exact original file; live modules are not forcibly unloaded. Firewall offloading is saved without a firewall reload. When restart is required, Auto remains blocked until a separate deliberate router reboot and fresh checks.','Переключатели автозапуска не останавливают работающую службу. При отключении автозагрузки SFE точный исходный файл сохраняется; работающие модули принудительно не выгружаются. Flow offloading сохраняется без перезапуска firewall. Если нужна перезагрузка, Auto остаётся заблокирован до отдельной осознанной перезагрузки роутера и свежих проверок.']},
 {t:['An uncertain reply is not success. Keep /etc/homensai-vpn/preparation-changes for recovery and inspect the actual state before another attempt. Unknown firmware, bindings, saved files or active recovery cannot be bypassed with this button.','Неопределённый ответ не означает успех. Сохраните /etc/homensai-vpn/preparation-changes для восстановления и проверьте реальное состояние до новой попытки. Неизвестную прошивку, привязки, сохранённые файлы или активное восстановление эта кнопка не обходит.']}
]});

HELP_TOPICS.push({"id":"website-response","open":false,"title":["Three-site response: method and history","Ответ трёх сайтов: метод и история"],"when":["You want to understand the single displayed VPN response metric and gaps.","Вы хотите понять единую показанную метрику ответа VPN и пропуски."],"steps":[{"t":["Every selected VPN checks the same three ordinary HTTPS addresses: Google generate_204, Cloudflare cdn-cgi/trace and Wikipedia. Fresh DNS, TCP, TLS and all HTTP response headers are timed. This is not full webpage rendering, ICMP, or the separate technical DNS/HTTPS health probe.","Каждый выбранный VPN проверяет те же три обычных HTTPS-адреса: Google generate_204, Cloudflare cdn-cgi/trace и Wikipedia. Измеряются новый DNS, TCP, TLS и полные HTTP-заголовки ответа. Это не загрузка полной страницы, не ICMP и не отдельная техническая проверка DNS/HTTPS."]},{"t":["The displayed value is the arithmetic mean only when all three sites pass. A partial check shows coverage and no number; failures and timeouts are never zero and old metrics are never substituted. The value is fresh for at most45 seconds and is bound to the VPN generation.","Показанное число — среднее арифметическое только при успехе всех трёх сайтов. Неполная проверка показывает полноту без числа; ошибки и тайм-ауты никогда не считаются нулём, старые метрики не подставляются. Значение свежее не дольше45 секунд и привязано к поколению VPN."]},{"t":["Statistics follow the selected graph window. Mean is weighted by complete three-site cycles; minimum and maximum describe observed minute means. Missing periods and incomplete checks are not filled.","Статистика соответствует выбранному периоду графика. Средняя учитывает число полных проверок трёх сайтов; минимум и максимум относятся к наблюдённым минутным средним. Пропуски и неполные проверки не дорисовываются."]},{"t":["Storage follows the configured1–7 days. Older deleted measurements cannot be restored. Wide views sample markers; lines and statistics use retained measurements. History starts when recording begins and is saved at the configured checkpoint interval.","Хранение соответствует настройке1–7 дней. Удалённые старые замеры не восстанавливаются. В широком периоде метки выбираются, линии и статистика используют сохранённые измерения. История начинается с записи и сохраняется с заданным интервалом checkpoint."]},{"t":["Quality and ranking use these same complete website cycles. Resetting statistics sets a new counting boundary while preserving graph history. A lower mean is a recommendation, never permission to alter routes or enable Auto. Old event HTTPS measurements remain explicitly technical.","Качество и рейтинг используют те же полные проверки сайтов. Сброс статистики задаёт новую границу подсчёта, сохраняя историю графика. Меньшая средняя — рекомендация, а не разрешение менять маршруты или включать Auto. Старые HTTPS-замеры событий явно названы техническими."]}]});

/* Help: measured Auto behaviour on the dedicated GL-MT3000 (controlled faults of the primary WireGuard). Data are
   seconds from the start of the fault: first failed check, switch started, traffic on reserve, return started, back on primary. */
var AUTO_MEASUREMENTS=[
  {id:'night-2026-10-30',version:'0.9.1-alpha82',level:1,boost:true,fault:180,
   title:['Night 30 Oct 2026 · level 1 + boost · 8 faults of 180 s, once an hour','Ночь 30.10.2026 · уровень 1 + ускорение · 8 сбоев по 180 с, раз в час'],
   rows:[['00:26',71,114,160,230,273],['01:26',73,119,175,237,283],['02:26',67,118,183,248,286],['03:26',61,112,174,241,281],
         ['04:26',54,103,168,237,279],['05:26',47,99,165,233,286],['06:27',48,101,169,235,288],['07:27',48,116,174,247,292]]},
  {id:'level3-2026-10-30',version:'0.9.1-alpha82',level:3,boost:true,fault:150,
   title:['Morning 30 Oct 2026 · level 3 + boost · 4 faults of 150 s, every 5 min','Утро 30.10.2026 · уровень 3 + ускорение · 4 сбоя по 150 с, каждые 5 мин'],
   rows:[['08:29',34,91,150,215,267],['08:34',28,80,150,209,266],['08:39',27,92,150,229,272],['08:44',29,108,163,228,276]]},
  {id:'level4-2026-10-30',version:'0.9.1-alpha82',level:4,boost:true,fault:150,
   title:['Morning 30 Oct 2026 · level 4 + boost · 4 faults of 150 s, every 5 min','Утро 30.10.2026 · уровень 4 + ускорение · 4 сбоя по 150 с, каждые 5 мин'],
   rows:[['08:50',38,98,158,217,271],['08:55',28,83,159,210,254],['09:00',27,78,140,204,252],['09:05',26,97,159,216,269]]},
  {id:'level5-2026-10-30',version:'0.9.1-alpha82',level:5,boost:true,fault:150,
   title:['Morning 30 Oct 2026 · level 5 + boost · 3 of 4 faults of 150 s (one refused by the switch budget)','Утро 30.10.2026 · уровень 5 + ускорение · 3 из 4 сбоев по 150 с (один остановлен лимитом переключений)'],
   rows:[['09:11',32,91,162,220,273],['09:16',33,88,152,219,273],['09:26',27,91,157,218,271]]}
];
var AUTO_MEASURED_RANGES=[[1,160,171,183],[3,150,153,163],[4,140,154,159],[5,152,157,162]];
var MEASURE_PHASES=[['Fault not yet noticed','Сбой ещё не замечен','#9aa3ad'],['Confirming the failure','Подтверждение сбоя','#e0b100'],
  ['Switching to the reserve','Переключение на резерв','#e07800'],['Traffic on the reserve','Трафик на резерве','#2f9e57'],['Returning to the primary','Возврат на основной','#2563eb']];
function measureMean(values){values=values.filter(Number.isFinite);return values.length?values.reduce(function(a,b){return a+b;},0)/values.length:null;}
function measureSvg(tag,attrs){var n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.keys(attrs||{}).forEach(function(k){n.setAttribute(k,String(attrs[k]));});return n;}
function phaseChart(rows,opts){
  opts=opts||{};if(typeof document==='undefined'||!document.createElementNS)return E('p',{},'');
  var ends=[30,opts.marker?opts.marker.at:0];rows.forEach(function(r){r.segs.forEach(function(s){ends.push(s.to);});});
  var max=Math.max.apply(null,ends)*1.05,row=26,top=26,left=opts.left||64,width=964-left,h=top+Math.max(1,rows.length)*row+34;
  var step=[10,15,30,60,120,300,600,1800,3600,7200,21600].find(function(v){return max/v<=12;})||43200;
  var svg=measureSvg('svg',{viewBox:'0 0 1000 '+h,role:'img','aria-label':opts.title||'',style:'width:100%;height:auto;display:block'});
  for(var t=0;t<=max;t+=step){var x=left+t/max*width;svg.appendChild(measureSvg('line',{x1:x,x2:x,y1:top-6,y2:h-28,stroke:'#d8d9d8','stroke-width':1}));var lab=measureSvg('text',{x:x,y:h-12,'text-anchor':'middle','font-size':11,fill:'currentColor'});lab.textContent=t<600?t+bi(' s',' с'):Math.round(t/60)+bi(' min',' мин');svg.appendChild(lab);}
  if(opts.marker){var fx=left+opts.marker.at/max*width;svg.appendChild(measureSvg('line',{x1:fx,x2:fx,y1:top-10,y2:h-28,stroke:'#c0392b','stroke-width':2,'stroke-dasharray':'5 3'}));
    var fl=measureSvg('text',{x:fx+4,y:top-12,'font-size':11,fill:'#c0392b'});fl.textContent=opts.marker.label;svg.appendChild(fl);}
  rows.forEach(function(r,i){
    var y=top+i*row,name=measureSvg('text',{x:left-6,y:y+15,'text-anchor':'end','font-size':11,fill:'currentColor'});name.textContent=r.label;svg.appendChild(name);
    r.segs.forEach(function(sg){var a=left+sg.from/max*width,b=left+sg.to/max*width,rect=measureSvg('rect',{x:a,y:y+3,width:Math.max(1,b-a),height:row-8,fill:MEASURE_PHASES[sg.k][2],'data-phase':sg.k}),tip=measureSvg('title');
      if(sg.open)rect.setAttribute('fill-opacity','0.55');tip.textContent=bi(MEASURE_PHASES[sg.k][0],MEASURE_PHASES[sg.k][1])+': '+sg.tip;rect.appendChild(tip);svg.appendChild(rect);
      if(sg.label&&b-a>=46){var lt=measureSvg('text',{x:(a+b)/2,y:y+15,'text-anchor':'middle','font-size':10,fill:'#fff'});lt.textContent=sg.label;svg.appendChild(lt);}});
  });
  return svg;
}
function measureChart(set){
  return phaseChart(set.rows.map(function(r){var edges=[0,r[1],r[2],r[3],r[4],r[5]];
    return {label:r[0],segs:[0,1,2,3,4].map(function(k){return {k:k,from:edges[k],to:edges[k+1],tip:edges[k]+'–'+edges[k+1]+bi(' s',' с')};})};}),
    {title:bi(set.title[0],set.title[1]),marker:{at:set.fault,label:bi('fault ends','конец сбоя')}});
}
function measureTable(set){
  var cols=[bi('Time','Время'),bi('Noticed','Замечен'),bi('Switch started','Начало перехода'),bi('On reserve','На резерве'),bi('Return started','Начало возврата'),bi('Back on primary','Снова на основном'),bi('Switch itself','Само переключение'),bi('Return itself','Сам возврат')];
  var t=E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1'},[E('tr',{},cols.map(function(c){return E('th',{'scope':'col'},c);}))]);
  set.rows.forEach(function(r){t.appendChild(E('tr',{},[r[0],r[1],r[2],r[3],r[4],r[5],r[3]-r[2],r[5]-r[4]].map(function(v,i){return E('td',{},i?v+bi(' s',' с'):v);})));});
  var mean=[1,2,3,4,5].map(function(i){return measureMean(set.rows.map(function(r){return r[i];}));});
  var sw=measureMean(set.rows.map(function(r){return r[3]-r[2];})),rt=measureMean(set.rows.map(function(r){return r[5]-r[4];}));
  t.appendChild(E('tr',{'class':'hv-measure-mean'},[E('th',{'scope':'row'},bi('Mean','Среднее'))].concat(mean.concat([sw,rt]).map(function(v){return E('td',{},Math.round(v)+bi(' s',' с'));}))));
  return t;
}
function renderMeasurements(){
  var legend=E('p',{'class':'hv-measure-legend'},MEASURE_PHASES.map(function(p){return E('span',{},[E('i',{'style':'background:'+p[2]}),' '+bi(p[0],p[1])]);}));
  return E('div',{'class':'hv-measurements'},[
    E('p',{},bi('Controlled faults made with the Tests page function: the traffic of the primary WireGuard was blocked for a fixed time; Auto had to notice it, switch to the reserve OpenVPN and return when the primary recovered. Every bar is one fault; seconds from its start.','Контролируемые сбои через функцию страницы «Тесты»: трафик основного WireGuard блокировался на заданное время; Auto должен был заметить сбой, переключить на резервный OpenVPN и вернуться, когда основной восстановился. Каждая полоса — один сбой; секунды от его начала.')),
    legend].concat(AUTO_MEASUREMENTS.map(function(set){return E('section',{'class':'hv-measure-set','data-measure-set':set.id},[
      E('h4',{},bi(set.title[0],set.title[1])+' · '+set.version),measureChart(set),measureTable(set)]);})).concat([
    E('h4',{},bi('Range: from the fault to traffic on the reserve','Диапазон: от поломки до работы через резерв')),
    E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1'},[E('tr',{},[bi('Probe level','Уровень опроса'),bi('Fastest','Быстрее всего'),bi('Mean','Среднее'),bi('Slowest','Дольше всего')].map(function(c){return E('th',{'scope':'col'},c);}))].concat(
      AUTO_MEASURED_RANGES.map(function(r){return E('tr',{},[String(r[0])+(r[0]<=2?bi(' (boost always on)',' (ускорение всегда)'):''),r[1]+bi(' s',' с'),r[2]+bi(' s',' с'),r[3]+bi(' s',' с')].map(function(v){return E('td',{},v);}));}))),
    E('p',{},bi('Observed limits: the switch itself took 46-76 s (mean 63 s) and the return to the primary 38-57 s (mean 48 s) in all 19 measured switches. At levels 3-5 a failure is noticed in about 30 s, at level 1 in about 60 s; then about 55 s go to confirming the failure (three checks) and proving the reserve. When faults repeat every 5 minutes, the switch budget (attempt limit per window) refused one switch on purpose: this protects against endless flapping.','Наблюдаемые пределы: само переключение заняло 46–76 с (в среднем 63 с), возврат на основной — 38–57 с (в среднем 48 с) во всех 19 измеренных переключениях. На уровнях 3–5 сбой замечается примерно за 30 с, на уровне 1 — примерно за 60 с; затем около 55 с уходит на подтверждение сбоя (три проверки) и проверку резерва. При сбоях каждые 5 минут лимит переключений (число попыток за окно) намеренно отклонил одно переключение: это защита от бесконечных переключений туда-обратно.')),
    E('p',{},bi('What it shows: these runs used the GL rebuild, so the switch itself took about a minute (the GL firmware rebuilds its VPN routing, rtp2). Since 1.0.0-beta3 the MT3000 normally uses the fast switch instead: the rule change measured 8-33 ms and new connections used the new channel within 0.5 s (30 Oct 2026); the GL rebuild stays as the fallback. The time from a fault is then dominated by detection (about 105 s) and depends on the probe level; the countdown during a switch uses the measured average plus 25%.','Что видно: в этих прогонах использовалась перестройка GL, поэтому само переключение занимало около минуты (прошивка GL перестраивает маршрутизацию VPN, rtp2). Начиная с 1.0.0-beta3 MT3000 обычно использует быстрое переключение: смена правил занимала 8–33 мс, а новые соединения шли по новому каналу в пределах 0,5 с (замер 30.10.2026); перестройка GL остаётся запасным путём. Тогда время от сбоя определяется обнаружением (около 105 с) и зависит от уровня опроса; обратный отсчёт во время переключения берёт измеренное среднее плюс 25%.'))]));
}
HELP_TOPICS.push({id:'auto-measurements',open:false,title:['Measured results of Auto mode','Результаты замеров работы в автоматическом режиме'],
  when:['You want to know how fast Auto notices a failure, switches and returns on a real router.','Вы хотите знать, как быстро Auto замечает сбой, переключает и возвращается на реальном роутере.'],
  steps:[{t:['Night of 30 Oct 2026, alpha82, probe level 1 with boost, 8 faults of 180 s: noticed after 59 s on average, traffic on the reserve after 171 s (160-183 s), the switch itself 61 s, back on the primary after 284 s.','Ночь 30.10.2026, alpha82, уровень опроса 1 с ускорением, 8 сбоев по 180 с: сбой замечен в среднем через 59 с, трафик на резерве через 171 с (160–183 с), само переключение 61 с, снова на основном через 284 с.']},
         {t:['Morning of 30 Oct 2026, levels 3, 4 and 5 with boost, faults of 150 s every 5 min: noticed after about 30 s, traffic on the reserve after 140-163 s (mean 153-157 s), the switch itself 55-76 s.','Утро 30.10.2026, уровни 3, 4 и 5 с ускорением, сбои по 150 с каждые 5 минут: сбой замечен примерно через 30 с, трафик на резерве через 140–163 с (в среднем 153–157 с), само переключение 55–76 с.']}],
  custom:renderMeasurements});
function autoLogicDiagram(){
  if(typeof document==='undefined'||!document.createElementNS)return E('p',{},'');
  var svg=measureSvg('svg',{viewBox:'0 0 1000 560',role:'img','aria-label':bi('Auto decision diagram','Схема решений Auto'),style:'width:100%;height:auto;display:block'});
  var defs=measureSvg('defs'),marker=measureSvg('marker',{id:'hv-arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});
  marker.appendChild(measureSvg('path',{d:'M0,0 L10,5 L0,10 z',fill:'currentColor'}));defs.appendChild(marker);svg.appendChild(defs);
  function box(x,y,w,h,fill,lines){
    svg.appendChild(measureSvg('rect',{x:x,y:y,width:w,height:h,rx:14,fill:fill,stroke:'currentColor','stroke-opacity':.35}));
    lines.forEach(function(t,i){var n=measureSvg('text',{x:x+w/2,y:y+24+i*19,'text-anchor':'middle','font-size':i?13:15,'font-weight':i?400:700,fill:'#14212e'});n.textContent=t;svg.appendChild(n);});
  }
  function arrow(x1,y1,x2,y2,label,lx,ly){
    svg.appendChild(measureSvg('line',{x1:x1,y1:y1,x2:x2,y2:y2,stroke:'currentColor','stroke-width':2,'marker-end':'url(#hv-arrow)'}));
    if(label)label.forEach(function(t,i){var n=measureSvg('text',{x:lx,y:ly+i*16,'text-anchor':'middle','font-size':12,fill:'currentColor'});n.textContent=t;svg.appendChild(n);});
  }
  box(40,40,280,96,'#b7efc5',[bi('1. Primary carries traffic','1. Работает основной'),bi('both channels are checked','проверяются оба канала'),bi('every 10-60 s (probe level)','раз в 10–60 с (уровень опроса)')]);
  box(680,40,280,96,'#ffd9a8',[bi('2. Switching to reserve','2. Переключение на резерв'),bi('rules written in one step','правила записываются за один шаг'),bi('fast: about 1 s; fallback: 46-76 s','быстро: около 1 с; запасной: 46–76 с')]);
  box(680,300,280,96,'#ffe9a8',[bi('3. Reserve carries traffic','3. Работает резерв'),bi('primary keeps being checked','основной продолжает проверяться'),'']);
  box(40,300,280,96,'#bcd7ff',[bi('4. Return to primary','4. Возврат на основной'),bi('about 38-57 s','около 38–57 с'),'']);
  arrow(320,88,676,88,[bi('primary: 3 failed checks in a row','основной: 3 неудачные проверки подряд'),bi('and reserve: 2 good checks in a row','и резерв: 2 удачные проверки подряд')],498,60);
  arrow(820,136,820,296,[bi('switch confirmed','переключение'),bi('by the router','подтверждено роутером')],890,210);
  arrow(676,348,324,348,[bi('primary: 2 good checks + stable 30 s,','основной: 2 удачные проверки + стабилен 30 с,'),bi('at least 60 s on reserve, <= 3 switches / 15 min','не меньше 60 с на резерве, не больше 3 переключений за 15 мин')],498,320);
  arrow(180,300,180,140,[bi('return','возврат'),bi('confirmed','подтверждён')],120,220);
  box(40,440,280,100,'#f6c6c6',[bi('Both channels fail','Оба канала не работают'),bi('Auto stays and waits:','Auto остаётся и ждёт:'),bi('there is nowhere to switch','переключаться некуда')]);
  box(360,440,280,100,'#e6e2f7',[bi('Reserve fails, primary healthy','Отказал резерв, основной здоров'),bi('Auto returns to the primary','Auto сразу возвращает'),bi('without waiting','трафик на основной')]);
  box(680,440,280,100,'#e2e8ee',[bi('You chose the reserve by hand','Вы вручную выбрали резерв'),bi('no automatic return;','без автовозврата;'),bi('if it fails, Auto switches back','при его отказе Auto вернёт')]);
  return svg;
}
function renderAutoLogic(){
  return E('div',{'class':'hv-auto-logic'},[autoLogicDiagram(),
    E('ol',{'class':'hv-help-steps'},[
      [bi('Primary carries traffic. The router checks both channels itself (DNS + three HTTPS sites through each tunnel) every 10-60 s, depending on the probe level.','Работает основной канал. Роутер сам проверяет оба канала (DNS и три HTTPS-сайта через каждый туннель) раз в 10–60 с — по уровню опроса.')],
      [bi('Failure: after 3 failed checks of the primary in a row (on levels 1-2 the boost then checks every 10 s) and 2 good checks of the reserve in a row, Auto switches to the reserve.','Сбой: после 3 неудачных проверок основного подряд (на уровнях 1–2 ускорение тогда проверяет раз в 10 с) и 2 удачных проверок резерва подряд Auto переключает на резерв.')],
      [bi('Switch: the router writes the committed channel order straight into its firewall rules in one atomic step (fast switch, no firewall reload, no DNS restart). The rule change measured 8-33 ms and new connections used the new channel within 0.5 s (MT3000, 30 Oct 2026); the whole switch takes about 1 s. If anything looks unexpected, or you turned fast switch off in Settings, the GL firmware rebuilds its VPN routing instead (fallback, measured 46-76 s). The router confirms the new route either way.','Переключение: роутер записывает утверждённый порядок каналов прямо в правила межсетевого экрана одним атомарным шагом (быстрое переключение: без перезагрузки межсетевого экрана и без перезапуска DNS). Смена правил занимала 8–33 мс, а новые соединения шли по новому каналу в пределах 0,5 с (MT3000, 30.10.2026); всё переключение занимает около 1 с. Если что-то выглядит неожиданно или вы выключили быстрое переключение в настройках, вместо этого прошивка GL перестраивает маршрутизацию VPN (запасной путь, замерено 46–76 с). Новый маршрут роутер подтверждает в обоих случаях.')],
      [bi('On the reserve: traffic stays on the reserve while the primary is down. The primary keeps being checked.','На резерве: трафик остаётся на резерве, пока основной не работает. Основной продолжает проверяться.')],
      [bi('Return: when the primary passed 2 checks in a row and is stable for 30 s, at least 60 s were spent on the reserve and no more than 3 switches happened in 15 minutes, Auto returns to the primary (measured 38-57 s).','Возврат: когда основной прошёл 2 проверки подряд и стабилен 30 с, на резерве провели не меньше 60 с и было не больше 3 переключений за 15 минут, Auto возвращает трафик на основной (замерено 38–57 с).')],
      [bi('If the reserve fails while the primary is healthy, Auto returns at once. If both fail, Auto stays and waits. If you chose the reserve by hand, there is no automatic return, but Auto still switches back if the reserve fails.','Если отказал резерв, а основной здоров, Auto возвращается сразу. Если не работают оба, Auto остаётся и ждёт. Если вы вручную выбрали резерв, автовозврата нет, но при отказе резерва Auto переключит обратно.')],
      [bi('All numbers are the defaults of Settings → Auto switching rules; there you can also choose "stay on the reserve" instead of returning.','Все числа — значения по умолчанию в «Настройки → Правила автопереключения»; там же можно выбрать «оставаться на резерве» вместо возврата.')]
    ].map(function(t){return E('li',{},E('p',{},t[0]));}))]);
}
HELP_TOPICS.unshift({id:'auto-logic',open:false,title:['How Auto works: switching and return','Логика работы Auto: переключение и возврат'],
  when:['You want to know when Auto switches to the reserve and when it returns to the primary.','Вы хотите знать, когда Auto переключает на резерв и когда возвращает на основной.'],
  steps:[{t:['Primary works; after 3 failed checks of the primary and 2 good checks of the reserve Auto switches to the reserve (fast switch about 1 s; fallback to the GL rebuild 46-76 s); it returns when the primary passed 2 checks, is stable 30 s, at least 60 s were spent on the reserve and the switch budget allows (return 38-57 s).','Работает основной; после 3 неудачных проверок основного и 2 удачных проверок резерва Auto переключает на резерв (быстрое переключение около 1 с; запасной путь через перестройку GL 46–76 с); возвращает, когда основной прошёл 2 проверки, стабилен 30 с, на резерве провели не меньше 60 с и позволяет лимит переключений (возврат 38–57 с).']}],
  custom:renderAutoLogic});

var SWITCH_RESERVE_CAP=120;
function switchKindText(kind){return {auto:bi('Automatic','Автоматическое'),manual:bi('Manual','Ручное'),test:bi('Test','Тест')}[kind]||bi('Not saved','Не сохранено');}
function switchWhen(t){return Number.isFinite(t)?new Date(t*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';}
function switchStatsOf(values){values=values.filter(Number.isFinite);if(!values.length)return null;return {n:values.length,mean:measureMean(values),min:Math.min.apply(null,values),max:Math.max.apply(null,values)};}
function switchResult(e,last,now){
  if(e.rolledBack!==null)return bi('Attempt ended without a switch','Попытка завершилась без переключения');
  if(e.back!==null)return bi('Back on the primary','Снова на основном');
  if(e.returnStart!==null)return last?bi('Returning now','Идёт возврат'):bi('Return end not saved','Конец возврата не сохранён');
  if(e.reserve!==null)return last?bi('On the reserve now','Сейчас на резерве'):bi('Return not saved','Возврат не сохранён');
  return last&&Number.isFinite(e.start)&&now-e.start<900?bi('Switching now','Идёт переключение'):bi('End not saved','Окончание не сохранено');
}
function switchChartRows(episodes,now){
  return episodes.map(function(e,i){
    var last=i===episodes.length-1,o=e.time,segs=[],shift=0;
    function add(k,a,b,open){var real=b-a;if(!Number.isFinite(real)||real<0)return;var shown=k===3?Math.min(real,SWITCH_RESERVE_CAP):real,from=a-o-shift;
      segs.push({k:k,from:from,to:from+shown,tip:spanText(real)+(open?bi(' (still going)',' (продолжается)'):''),label:spanText(real),open:!!open});shift+=real-shown;}
    if(e.failure!==null&&e.start!==null)add(1,e.failure,e.start);
    if(e.start!==null&&e.reserve!==null)add(2,e.start,e.reserve);else if(e.start!==null&&e.rolledBack!==null)add(2,e.start,e.rolledBack);else if(last&&e.start!==null&&now-e.start<900)add(2,e.start,now,true);
    if(e.reserve!==null&&e.returnStart!==null)add(3,e.reserve,e.returnStart);else if(e.reserve!==null&&e.back!==null&&e.returnStart===null)add(3,e.reserve,e.back);else if(last&&e.reserve!==null&&e.back===null)add(3,e.reserve,now,true);
    if(e.returnStart!==null&&e.back!==null)add(4,e.returnStart,e.back);else if(last&&e.returnStart!==null&&e.back===null&&now-e.returnStart<900)add(4,e.returnStart,now,true);
    return {label:switchWhen(e.time)+' '+(e.kind==='manual'?'M':e.kind==='test'?'T':e.kind==='auto'?'A':'?'),segs:segs};
  });
}
function renderSwitchPage(model){
  model=model||{};var all=Array.isArray(model.episodes)?model.episodes:[],now=Number.isFinite(model.now)?model.now:Date.now()/1000,shown=all.slice(-20),timing=model.timing;
  var legend=E('p',{'class':'hv-measure-legend'},MEASURE_PHASES.slice(1).map(function(p){return E('span',{},[E('i',{'style':'background:'+p[2]}),' '+bi(p[0],p[1])]);}));
  var intro=E('p',{},bi('Every switch is measured from the router events: the first failed check of the primary, the start of the switch, traffic confirmed on the reserve, the start of the return and traffic back on the primary. A dash means that moment was not saved; nothing is estimated.','Каждое переключение измеряется по событиям роутера: первая неудачная проверка основного канала, начало перехода, трафик подтверждён на резерве, начало возврата и трафик снова на основном. Прочерк означает, что этот момент не сохранился; ничего не досчитывается.'));
  var phases=E('ul',{},[
    E('li',{},bi('Detection: from the first failed check to the start of the switch. Auto waits for several failed checks in a row so that one lost packet does not move your traffic.','Обнаружение: от первой неудачной проверки до начала перехода. Auto ждёт несколько неудачных проверок подряд, чтобы одна потеря пакета не переводила трафик.')),
    E('li',{},bi('Switching: from the start of the switch until traffic is confirmed on the reserve (the router rebuilds its VPN routing and checks the reserve).','Переключение: от начала перехода до подтверждения трафика на резерве (роутер перестраивает маршрутизацию VPN и проверяет резерв).')),
    E('li',{},bi('On the reserve: how long traffic stayed on the reserve. On the chart this phase is cut to '+SWITCH_RESERVE_CAP+' s; its real length is written on the bar and in the table.','На резерве: сколько трафик шёл через резерв. На графике эта фаза укорочена до '+SWITCH_RESERVE_CAP+' с; настоящая длительность написана на полосе и в таблице.')),
    E('li',{},bi('Return: from the start of the return until traffic is confirmed on the primary again.','Возврат: от начала возврата до подтверждения трафика снова на основном.')),
    E('li',{},bi('The moment the fault really began is not known to the router: it can only see the first failed check. Help → Measured results of Auto mode shows controlled tests where the fault start was known.','Момент, когда сбой действительно начался, роутеру неизвестен: он видит только первую неудачную проверку. В «Помощи → Результаты замеров работы в автоматическом режиме» есть контролируемые тесты, где начало сбоя было известно.'))]);
  var nodes=[E('h3',{},bi('Switch statistics','Статистика переключений')),intro];
  var switched=all.filter(function(e){return e.reserve!==null;}),returned=all.filter(function(e){return e.back!==null;});
  var stats={detect:switchStatsOf(all.map(function(e){return e.detect;})),switching:switchStatsOf(all.map(function(e){return e.switching;})),total:switchStatsOf(all.map(function(e){return e.total;})),returning:switchStatsOf(all.map(function(e){return e.returning;}))};
  function card(label,value,detail){return E('div',{'class':'hv-switch-card'},[E('span',{},label),E('strong',{},value),E('small',{},detail)]);}
  function range(st){return st?bi('min ','мин. ')+spanText(st.min)+' · '+bi('max ','макс. ')+spanText(st.max)+' · n='+st.n:bi('No measurements yet','Замеров пока нет');}
  nodes.push(E('div',{'class':'hv-switch-cards','data-switch-cards':'1'},[
    card(bi('Switches to the reserve','Переключений на резерв'),String(switched.length),bi('automatic ','автоматических ')+switched.filter(function(e){return e.kind==='auto';}).length+' · '+bi('manual ','ручных ')+switched.filter(function(e){return e.kind==='manual';}).length+' · '+bi('returns ','возвратов ')+returned.length),
    card(bi('Detection (mean)','Обнаружение (среднее)'),stats.detect?spanText(stats.detect.mean):'—',range(stats.detect)),
    card(bi('Switching (mean)','Переключение (среднее)'),stats.switching?spanText(stats.switching.mean):'—',range(stats.switching)),
    card(bi('Failure → reserve (mean)','Сбой → резерв (среднее)'),stats.total?spanText(stats.total.mean):'—',range(stats.total)),
    card(bi('Return (mean)','Возврат (среднее)'),stats.returning?spanText(stats.returning.mean):'—',range(stats.returning)),
    card(bi('Router switch average','Среднее роутера'),timing&&Number.isFinite(timing.avg_seconds)?spanText(timing.avg_seconds):'—',timing&&Number.isFinite(timing.avg_seconds)?bi('switches counted ','учтено переключений ')+timing.count+(Number.isFinite(timing.last_seconds)?' · '+bi('last ','последнее ')+spanText(timing.last_seconds):'')+' · '+bi('used by the countdown','используется обратным отсчётом'):bi('No confirmed switch saved yet','Подтверждённых переключений ещё нет'))]));
  if(!all.length){
    nodes.push(E('p',{'class':'alert-message','data-switch-empty':'1'},model.history===false?bi('The event history has not arrived yet. It is loaded about once a minute while this page is open.','История событий ещё не загружена. Пока страница открыта, она загружается примерно раз в минуту.'):bi('No switches in the saved history yet. When Auto or you switch the channel, the measured times appear here.','В сохранённой истории пока нет переключений. Когда Auto или вы переключите канал, здесь появятся измеренные времена.')));
    nodes.push(E('h4',{},bi('Phases','Фазы')),phases);return E('div',{'class':'hv-switch-stats'},nodes);
  }
  nodes.push(E('h4',{},bi('The switching process over time','Процесс переключения во времени')+' · '+(shown.length<all.length?bi('last ','последние ')+shown.length+bi(' of ',' из ')+all.length:String(all.length))));
  nodes.push(legend,phaseChart(switchChartRows(shown,now),{title:bi('Switching phases per episode, seconds from the first known moment','Фазы каждого переключения, секунды от первого известного момента'),left:110}));
  nodes.push(E('p',{},bi('Each bar is one episode, the newest is at the bottom. A = automatic, M = manual, T = test. The bar starts at the first failed check, or at the first saved moment if that check is not known.','Каждая полоса — один эпизод, новый внизу. A — автоматическое, M — ручное, T — тест. Полоса начинается с первой неудачной проверки или с первого сохранённого момента, если она неизвестна.')));
  var cols=[bi('Time','Время'),bi('Type','Тип'),bi('Detection','Обнаружение'),bi('Switching','Переключение'),bi('Failure → reserve','Сбой → резерв'),bi('On the reserve','На резерве'),bi('Return','Возврат'),bi('Primary was down','Основной не работал'),bi('Result','Итог')];
  var table=E('table',{'class':'table hv-measure-table','data-hv-no-sort':'1','data-switch-table':'1'},[E('tr',{},cols.map(function(c){return E('th',{'scope':'col'},c);}))]);
  shown.slice().reverse().forEach(function(e,i){table.appendChild(E('tr',{'data-switch-key':e.key},[switchWhen(e.time),switchKindText(e.kind)+(e.returnKind&&e.returnKind!==e.kind&&e.back!==null?' / '+switchKindText(e.returnKind):''),spanText(e.detect),spanText(e.switching),spanText(e.total),spanText(e.onReserve),spanText(e.returning),spanText(e.down),switchResult(e,i===0,now)].map(function(v){return E('td',{},v);})));});
  var mean=['detect','switching','total','onReserve','returning','down'].map(function(k){var st=switchStatsOf(shown.map(function(e){return e[k];}));return st?spanText(st.mean):'—';});
  table.appendChild(E('tr',{'class':'hv-measure-mean'},[E('th',{'scope':'row'},bi('Mean','Среднее')),E('td',{},'')].concat(mean.map(function(v){return E('td',{},v);}),[E('td',{},'')])));
  nodes.push(E('div',{'class':'hv-dv-tablewrap'},table),E('h4',{},bi('Phases','Фазы')),phases);
  nodes.push(E('p',{},[bi('The same times are written in ','Те же времена записаны в '),E('a',{'href':'#events'},bi('Events and errors','Событиях и ошибках')),bi(' and in the ',' и в '),E('a',{'href':'#services'},bi('Live log','Живом журнале')),'.']));
  return E('div',{'class':'hv-switch-stats'},nodes);
}

var LEARN_SCENES=[
 [['Observe the pair','Наблюдаем пару'],['Repeated primary failures','Повторные отказы основного'],['Reserve passes checks','Резерв прошёл проверки'],['Select reserve traffic policy','Выбираем маршрут резерва']],
 [['Cable access to the router','Кабельный доступ к роутеру'],['Wi-Fi client access','Доступ клиента по Wi-Fi'],['Separate mobile connection','Независимая мобильная связь'],['Keep router access during tests','Сохраняем доступ на время тестов']],
 [['Accept the current terms once','Принимаем текущие условия один раз'],['Read introduction and training','Читаем объяснение и обучение'],['Review the eight setup steps','Проверяем восемь шагов настройки'],['Save; Auto still stays off','Сохраняем; Auto остаётся выключенным']],
 [['Configure profiles in stock VPN app','Настраиваем профили в штатном VPN'],['Bind a profile to each client','Назначаем профиль каждому клиенту'],['Assign primary and reserve roles','Выбираем роли основного и резерва'],['Save two distinct clients','Сохраняем два разных клиента']],
 [['Check current DNS and HTTPS','Проверяем свежие DNS и HTTPS'],['Check the VPN and routes','Проверяем VPN и маршруты'],['Client trial needs its own helper','Для клиентского теста нужен помощник'],['Explicit Start for the ready mode','Явно запускаем готовый режим']],
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
      "Grey means waiting for the router, red means a proven failure: open Help.",
      "Серый — ждём ответа роутера, красный — доказанный сбой: откройте «Помощь»."
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
        "The power button shows Auto ON/OFF. The route title and M/R diagram show the selected channel. Green means this channel carries your traffic, not independent proof of Internet; yellow means alive but not in use (or a short check or switch); red is a proven failure. During a manual switch the destination card blinks green. Inspect fresh channel checks for availability.",
        "Большая кнопка показывает включение/выключение Auto. Заголовок маршрута и схема M/R показывают выбранный канал. Зелёный означает, что этот канал несёт ваш трафик, а не отдельное доказательство Интернета; жёлтый — канал жив, но не используется (или идёт короткая проверка либо переключение); красный — доказанный сбой. При ручном переключении карточка назначения мигает зелёным. Доступность смотрите в свежих проверках канала."
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
        "Channels and servers shows primary first and reserve second, server names/IP where observed, the response (ping by default, or the three-site HTTPS mean) and a 1–168h history within configured 1–7-day retention. Other servers and excess table rows expand with a triangle. A lower-delay recommendation does not switch traffic.",
        "«Каналы и серверы» показывает сначала основной, затем резервный, имена/IP при наличии наблюдения, отклик (по умолчанию пинг, либо среднее трёх сайтов по HTTPS) и историю 1–168 ч в пределах настроенного хранения 1–7 дней. Другие серверы и лишние строки раскрываются треугольником. Рекомендация меньшей задержки сама не переключает трафик."
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
  {q:['What does Working on the reserve confirm?','Что подтверждает статус «Работаю на резерве»?'],o:[['The reserve route is selected; primary health is checked separately','Выбран резервный маршрут; исправность основного проверяется отдельно',true],['Everything is on the primary','Всё идёт через основной',false],['Auto is off','Auto выключен',false]]},
  {q:['Which of these is a secret that you never send to anyone? (several answers)','Что из этого — секрет, который никому нельзя отправлять? (несколько ответов)'],o:[['The Telegram bot token','Токен Telegram-бота',true],['The router password','Пароль роутера',true],['The country of a VPN server','Страна VPN-сервера',false]]},
  {q:['The internet is gone. What do you do first?','Интернета нет. Что делаете сначала?'],o:[['Open the router page, inspect fresh checks and follow No internet Help','Открываете страницу роутера, проверяете свежие данные и справку «Нет интернета»',true],['Flash the router firmware','Прошиваете роутер',false],['Delete all VPN profiles','Удаляете все VPN-профили',false]]},
  {q:['Which command only reads the state and is always safe?','Какая команда только читает состояние и всегда безопасна?'],o:[['homensai-vpn-emergency show','homensai-vpn-emergency show',true],['homensai-vpn-emergency stop-auto','homensai-vpn-emergency stop-auto',false],['homensai-vpn-emergency remove-guard','homensai-vpn-emergency remove-guard',false]]}
];
LEARN_LESSONS[4].body.push(
 ['To choose a route manually, open Overview → Manual channel selection. Choose Primary or Reserve when its control is available, then wait for confirmed selection. A queued request is not completion; the destination card blinks green during the switch. Manual selection never turns Auto off: Auto keeps watching the chosen channel and moves traffic to the other one if it fails.','Для ручного выбора откройте «Обзор» → «Ручное переключение канала». Выберите «Основной» или «Резервный», когда управление доступно, затем дождитесь подтверждённого выбора. Очередь запроса не означает завершение; во время переключения карточка назначения мигает зелёным. Ручной выбор никогда не выключает Auto: Auto продолжает следить за выбранным каналом и переносит трафик на другой, если этот откажет.'],
 ['Use the large Auto button to request startup or shutdown. Wait for the actual final state. Turning Auto off does not stop monitoring; managed shutdown may restore the original routing/interface settings. A retained-reserve outcome requires its separately offered recovery action.','Большая кнопка Auto запрашивает запуск или остановку. Дождитесь фактического итогового состояния. Выключение Auto не прекращает мониторинг; управляемая остановка может восстановить исходные правила и флаги интерфейсов. Если резерв удержан, используйте отдельно предложенное действие восстановления.']
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
 ['Orange in the Auto status means the reserve route is selected. It does not by itself prove the primary is broken; health is shown separately.','Оранжевый статус Auto означает выбранный резервный маршрут. Это само по себе не доказывает неисправность основного: его проверки показаны отдельно.'],
 ['Passwords, bot tokens, VPN keys and complete backups are secrets. Server country is a display label, not an authentication secret.','Пароли, токены бота, VPN-ключи и полные резервные копии — секреты. Страна сервера является подписью, а не секретом доступа.'],
 ['First inspect the router and fresh checks, then use the No internet help. Reflashing and deleting profiles are not first diagnostic steps.','Сначала откройте роутер и свежие проверки, затем помощь «Нет интернета». Прошивка и удаление профилей не являются первым шагом диагностики.'],
 ['The show command reads the state. Stop-auto can change managed routing during recovery; remove-guard changes the owned traffic block.','Команда show читает состояние. Stop-auto при восстановлении может менять управляемый маршрут; remove-guard изменяет собственную блокировку трафика.'],
 ['Available manual controls can choose a verified channel while continuous Auto stays on. A queued command is not yet confirmed traffic selection.','Доступное ручное управление позволяет выбрать проверенный канал при работающем Auto. Поставленная в очередь команда ещё не означает подтверждённого выбора трафика.'],
 ['A successful check is an observation of a channel. Route changes have their own requested, pending and confirmed events.','Успешная проверка — наблюдение за каналом. Для смены маршрута есть отдельные события запроса, выполнения и подтверждения.'],
 ['Primary and reserve are roles, not protocol names. The application uses an existing pair and does not invent or import VPN credentials.','Основной и резервный — роли, а не названия протоколов. Приложение использует существующую пару и не создаёт или импортирует VPN-ключи.']
];
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

/* Extra rows of the error table: controller states, reasons, diagnosis words, fault-test, Telegram, setup and speed codes,
   notices of the page, and families of internal codes. Row: [code, group, name EN, name RU, meaning EN, meaning RU, fix EN, fix RU, example EN, example RU].
   Nothing here is a promise about a real router: a code tells what was observed, the cause may stay unknown. */
var ERROR_EXTRA_GROUPS=[['manual',['Manual requests and recovery','Ручные запросы и восстановление']],['platform',['Manual platform readiness','Готовность платформы к ручному переключению']],['state',['Controller states and phases','Состояния и этапы контроллера']],['internal',['Internal checks and safety stops','Внутренние проверки и защитные остановки']]];
var ERROR_EXTRA_ROWS=[
 ["WEBSITE-*", "monitor", "Website measurement detail", "Подробность замера сайтов", "A website result or its archive could not be verified. This detail alone does not establish a VPN failure; no older metric is substituted.", "Результат проверки сайтов или его архив не подтверждены. Эта подробность сама по себе не доказывает отказ VPN; старая метрика не подставляется.", "Wait for a fresh check. Preserve the code and inspect the website-response method and history in Help.", "Дождитесь новой проверки. Сохраните код и посмотрите метод и историю ответов сайтов в «Помощи»."],
 ["WEBSITE-IDENTITY-CHANGED", "monitor", "VPN identity changed", "Изменилась привязка VPN", "The measured VPN generation or tunnel no longer matches the displayed channel. No old value is substituted.", "Поколение или туннель замера не совпадает с показанным каналом. Старое значение не подставляется.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-DNS-FAILED", "monitor", "Website DNS failed", "Не прошёл DNS сайта", "A selected ordinary website name could not be resolved through this VPN. This is separate from the technical health probes.", "Имя одного из выбранных обычных сайтов не разрешилось через этот VPN. Это отдельный результат, не техническая проверка здоровья.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-HTTP-FAILED", "monitor", "Website HTTP failed", "Не прошёл HTTP сайта", "The website did not return its expected HTTP status and complete headers. There is no complete three-site mean.", "Сайт не вернул ожидаемый HTTP-статус и полные заголовки. Полного среднего трёх сайтов нет.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-TIMEOUT", "monitor", "Website response timed out", "Истекло время ответа сайта", "A fresh website check exceeded its bounded deadline. Missing time is not a zero-millisecond response.", "Новая проверка сайта превысила ограниченное время. Отсутствующий замер не считается нулём миллисекунд.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-TLS-FAILED", "monitor", "Website TLS failed", "Не прошёл TLS сайта", "The fresh HTTPS connection could not establish verified TLS to the selected website.", "Новое HTTPS-соединение не смогло установить проверенный TLS с выбранным сайтом.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-RESPONSE-FAILED", "monitor", "Website response failed", "Не получен ответ сайта", "The independent three-site check failed. It supplies no delay value and does not change Auto health or routing.", "Отдельная проверка трёх сайтов не прошла. Она не даёт значение задержки и не меняет здоровье Auto или маршрутизацию.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-UNAVAILABLE", "monitor", "Website measurement unavailable", "Замер сайтов недоступен", "No fresh complete identity-bound three-site result is available. ICMP and technical HTTPS times cannot replace it.", "Свежего полного замера трёх сайтов с проверенной привязкой к VPN нет. ICMP и технический HTTPS его не заменяют.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-PARTIAL", "monitor", "Only some websites answered", "Ответили не все сайты", "Fewer than three selected websites answered successfully. Coverage is shown; an average requires all three.", "Успешно ответили менее трёх выбранных сайтов. Показана полнота проверки; для среднего нужны все три.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-CHECK-PENDING", "monitor", "Website check pending", "Ожидается проверка сайтов", "The background three-site measurement is still being collected. Opening this page starts no extra request.", "Фоновый замер трёх сайтов ещё выполняется. Открытие страницы не запускает дополнительный запрос.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-NOT-SELECTED", "monitor", "VPN is outside the measured pair", "VPN вне измеряемой пары", "Only the two selected VPN channels receive the bounded three-site measurement. No other profile is connected by this page.", "Ограниченный замер трёх сайтов выполняется только для двух выбранных каналов. Страница не подключает другие профили.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-DATA-STALE", "monitor", "Website result is old", "Замер сайтов устарел", "The original completion time exceeds its freshness window. Publication of cached data does not renew a measurement.", "Исходное время завершения вышло за срок свежести. Повторная выдача кеша не обновляет замер.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-HISTORY-WRITE-FAILED", "monitor", "Website history was not saved", "История сайтов не сохранена", "The separate website-response archive could not be safely written. Current checks can continue; missing history stays empty.", "Отдельный архив ответов сайтов не удалось безопасно записать. Текущие проверки могут продолжаться; пропуски не дорисовываются.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-HISTORY-UNAVAILABLE", "monitor", "Website history unavailable", "История сайтов недоступна", "The website-response archive or its checksum could not be verified. Old technical HTTPS history is not substituted.", "Архив ответов сайтов или его контрольная сумма не подтверждены. Старая история технического HTTPS не подставляется.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["WEBSITE-HISTORY-PAIR-LIMIT", "monitor", "Website history pair limit reached", "Достигнут лимит пар истории", "The bounded archive cannot add another channel pair while preserving its limits. No profile or historical value is silently relabelled.", "Ограниченный архив не может добавить ещё одну пару каналов в пределах лимита. Профили и старые значения не переименовываются.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["PING-HISTORY-WRITE-FAILED", "monitor", "Ping history was not saved", "История пинга не сохранена", "The separate ping-response archive could not be safely written. Current checks can continue; missing history stays empty.", "Отдельный архив ответов сайтов не удалось безопасно записать. Текущие проверки могут продолжаться; пропуски не дорисовываются.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["PING-HISTORY-UNAVAILABLE", "monitor", "Ping history unavailable", "История пинга недоступна", "The ping-response archive or its checksum could not be verified. Old technical HTTPS history is not substituted.", "Архив ответов сайтов или его контрольная сумма не подтверждены. Старая история технического HTTPS не подставляется.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["PING-HISTORY-PAIR-LIMIT", "monitor", "Ping history pair limit reached", "Достигнут лимит пар истории", "The bounded archive cannot add another channel pair while preserving its limits. No profile or historical value is silently relabelled.", "Ограниченный архив не может добавить ещё одну пару каналов в пределах лимита. Профили и старые значения не переименовываются.", "Wait for a fresh background check. Read Help → Three-site response for method and coverage.", "Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов»."],
 ["KNOWN-STOCK-DERIVED-RECOVERY","state","Known stock changes reconciled","Служебные изменения учтены","The stopped failed operation was reconciled with the exact verified backup and current stock-derived fields. Original journal/state bytes were archived and ordinary guarded Stop completed. This is not a completed VPN switch or permission to accept other changes.","Остановленная неудачная операция сверена с точной проверенной копией и действующими служебными полями. Исходные журнал и состояние заархивированы, штатный защищённый Stop завершён. Это не выполненное переключение VPN и не разрешение принимать другие изменения.","Complete the reviewed update and inspect fresh status. Auto still needs its normal readiness checks and an explicit authorized Start. Keep the failed evidence.","Завершите проверенное обновление и посмотрите свежий статус. Для Auto по-прежнему нужны штатные проверки готовности и разрешённый Старт. Сохраните доказательства неудачной операции."],
 ["RTP-BOOT-PRECONDITION-UNVERIFIED","platform","Router VPN runtime preparation is not confirmed","Не подтверждена штатная подготовка VPN","The pinned stock VPN script needs known runtime directories and an empty gate file before it can apply rules. Their preparation, ownership or exact firmware contract could not be confirmed. A successful script exit alone never proves that kernel rules exist.","Штатному VPN-скрипту нужны известные временные каталоги и пустой служебный флаг. Не удалось подтвердить их подготовку, принадлежность или точный контракт прошивки. Успешное завершение скрипта само по себе не подтверждает наличие kernel-правил.","Use the reviewed update and normal Start procedure. The application prepares only the known safe runtime prefix under the current command, then checks actual kernel rules. Do not run full stock boot or create files over unknown paths manually.","Используйте проверенное обновление и штатный Старт. Приложение готовит только известные безопасные временные объекты в рамках текущей команды, затем проверяет действующие kernel-правила. Не запускайте полный штатный boot и не создавайте файлы поверх неизвестных путей вручную."],
 ['KERNEL-POLICY-VERIFIED','platform','Router VPN rules verified','Правила выбора VPN проверены','The applied kernel packet-mark and routing rules match the selected VPN policy. This verifies the compiled rules only; it does not prove internet availability, a route-switch result or independent LAN-client acceptance.','Применённые правила меток пакетов и маршрутизации ядра соответствуют выбранным правилам VPN. Проверены только действующие правила; это не подтверждает доступ к интернету, итог переключения или независимую проверку клиента LAN.','Use the separate current HTTPS/DNS and channel-selection results for connectivity and Auto state. No extra policy change is needed for this verified result.','Доступность связи и состояние Auto проверяйте по отдельным текущим результатам HTTPS/DNS и выбора канала. Для этого подтверждённого результата дополнительное изменение правил не нужно.'],
 ['KERNEL-POLICY-UNVERIFIED','platform','Applied VPN selection rules are unverified','Действующие правила выбора VPN не подтверждены','The current kernel rules do not confirm the expected VPN traffic selection. Tunnel connectivity alone cannot prove which channel carries traffic.','Действующие правила ядра не подтверждают ожидаемый выбор VPN для трафика. Подключение туннеля само по себе не доказывает, какой канал несёт трафик.','Inspect the current VPN policy and the recorded refusal. Use the normal reviewed policy application and verify its readback before retrying.','Проверьте текущие правила VPN и сохранённую причину отказа. Применяйте правила штатным проверенным способом и подтвердите результат перед повтором.'],
 ['PAIR-POLICY-UNVERIFIED','switch','Primary and reserve VPN policy is unverified','Правила основного и резервного VPN не подтверждены','The application cannot verify how the selected primary and reserve roles map to the router VPN rules. It does not assume that list order proves the active traffic route.','Приложение не может подтвердить соответствие выбранных основного и резервного VPN правилам роутера. Порядок списка не считается доказательством действующего маршрута.','Review the selected pair and the actual applied VPN policy. Keep the refusal evidence and retry only after the router confirms that binding.','Проверьте выбранную пару и фактически применённые правила VPN. Сохраните причину отказа и повторяйте только после подтверждения привязки роутером.'],
 ['PROBE-SETTINGS-FIELDS','setup','Probe level request is incomplete','Неполный запрос уровня опроса','The page sent a probe-level request without the expected level and boost fields.','Страница отправила запрос уровня опроса без нужных полей уровня и ускорения.','Reload the page (Ctrl+F5) and apply the level again.','Обновите страницу (Ctrl+F5) и примените уровень ещё раз.'],
 ['PROBE-SETTINGS-RANGE','setup','Unknown probe level','Неизвестный уровень опроса','Only levels 1 to 5 exist.','Существуют только уровни от 1 до 5.','Choose a level with the slider and apply it again.','Выберите уровень ползунком и примените ещё раз.'],
 ['PROBE-SETTINGS-BUSY','setup','A switch is in progress','Идёт переключение','The probe level is not changed while a channel switch or recovery is running.','Уровень опроса не меняется, пока идёт переключение или восстановление канала.','Wait until the switch finishes, then apply the level again.','Дождитесь окончания переключения и примените уровень ещё раз.'],
 ['PROBE-POLICY-UNAVAILABLE','service','Probe level state unavailable','Состояние уровня опроса недоступно','The monitor could not publish the current probe level this cycle. Monitoring itself continues.','Мониторинг не смог опубликовать текущий уровень опроса в этом цикле. Сам мониторинг продолжается.','Wait for the next check; if it stays, reload the page.','Дождитесь следующей проверки; если не проходит, обновите страницу.'],
 ['PROBE-HISTORY-UNAVAILABLE','service','Decision log unavailable','Журнал решений недоступен','The router did not return the probe decision log.','Роутер не вернул журнал решений уровня опроса.','Close and open the log again in a minute.','Закройте и снова откройте журнал через минуту.'],
 ['PING-PENDING','service','Ping not measured yet','Пинг ещё не измерен','The router has not finished the first ping through this channel since it started or since the setting changed.','Роутер ещё не закончил первый пинг через этот канал после запуска или смены настройки.','Wait for the next check (see the countdown under the traffic light).','Дождитесь следующей проверки (см. таймер под светофором).'],
 ['WEBSITE-NOT-SELECTED','service','Website check not selected','Проверка сайтов не выбрана','Ping is selected as the response measurement, so the three-website check does not run.','В качестве измерения отклика выбран пинг, поэтому проверка трёх сайтов не выполняется.','Choose "Three websites over HTTPS" in Settings if you want it.','Выберите «Три сайта по HTTPS» в настройках, если она нужна.'],
 ['RESPONSE-METRIC-INVALID','setup','Unknown response measurement','Неизвестный способ измерения отклика','The page sent a measurement the router does not offer.','Страница отправила способ измерения, которого нет на роутере.','Reload the page (Ctrl+F5) and choose again.','Обновите страницу (Ctrl+F5) и выберите снова.'],
 ['MANUAL-ALREADY-SELECTED','manual','This channel is already selected','Этот канал уже выбран','The requested channel is already selected and its traffic path was verified. Another route switch is unnecessary; this result does not start Auto.','Запрошенный канал уже выбран, его маршрут трафика проверен. Повторное переключение не нужно; этот результат не включает Auto.','Continue using the verified channel. Wait for the current status to refresh; do not repeat a switch merely to change the indicator.','Продолжайте работу через подтверждённый канал. Дождитесь обновления состояния; не повторяйте переключение только ради изменения индикатора.'],
 ['PING-FAILED','monitor','No ICMP reply','Нет ответа ICMP','The separate ICMP echo through this VPN did not complete successfully. This does not change its HTTPS/DNS health, selected route or Auto decision.','Отдельная ICMP-проверка через этот VPN не прошла. Это не меняет результаты HTTPS/DNS, выбранный маршрут или решение Auto.','Wait for the next Ping check. Some networks block ICMP even when HTTPS works; compare the independent HTTPS/DNS results.','Дождитесь следующей Ping-проверки. Некоторые сети блокируют ICMP при работающем HTTPS; сравните отдельные результаты HTTPS/DNS.'],
 ['PING-DATA-STALE','monitor','ICMP result is old','ICMP-результат устарел','The saved ICMP result is older than its permitted freshness window. Its old milliseconds are not shown as a current measurement.','Сохранённый ICMP-результат старше допустимого срока. Прежние миллисекунды не показываются как текущее измерение.','Wait for the next background check. If results remain old, inspect Monitoring and the router connection.','Дождитесь фоновой проверки. Если данные остаются старыми, проверьте мониторинг и связь с роутером.'],
 ['PING-CHECK-PENDING','monitor','Waiting for an ICMP check','Ожидается ICMP-проверка','A current ICMP measurement for this VPN is still being collected. No milliseconds are invented from HTTPS or an earlier connection.','Текущее ICMP-измерение этого VPN ещё собирается. Миллисекунды не подставляются из HTTPS или прежнего подключения.','Wait for the background check; opening the page sends no additional Ping request.','Дождитесь фоновой проверки: открытие страницы не отправляет дополнительный Ping-запрос.'],
 ['PING-UNAVAILABLE','monitor','ICMP measurement is unavailable','ICMP-измерение недоступно','No verified ICMP measurement is available for this channel. The result is separate from HTTPS/DNS connectivity and traffic selection.','Для этого канала нет подтверждённого ICMP-измерения. Этот результат отделён от HTTPS/DNS и выбора канала трафика.','Inspect the router monitoring state and the selected VPN pair. Keep the HTTPS/DNS result separate; do not treat missing Ping as a measured outage.','Проверьте мониторинг роутера и выбранную пару VPN. Не смешивайте этот результат с HTTPS/DNS; отсутствие Ping не считается измеренным отказом.'],
 ['PING-INACTIVE','monitor','ICMP check is inactive','ICMP-проверка не выполняется','This VPN is disabled or not connected, so no current ICMP measurement is taken through it.','Этот VPN отключён или не подключён, поэтому текущее ICMP-измерение через него не выполняется.','Review the existing VPN connection on the router. The Ping display does not connect a tunnel or change Auto.','Проверьте существующее VPN-подключение на роутере. Строка Ping не подключает туннель и не меняет Auto.'],
 ['PING-IDENTITY-CHANGED','monitor','ICMP result belongs to another VPN connection','ICMP-результат относится к другому подключению','The VPN interface, tunnel or connection generation changed. The previous ICMP result is discarded instead of being attributed to the current connection.','Изменились интерфейс, туннель или поколение VPN-подключения. Прежний ICMP-результат отброшен, а не приписан текущему подключению.','Wait until the router observes the new VPN connection and completes its own ICMP check.','Дождитесь, пока роутер подтвердит новое VPN-подключение и выполнит отдельную ICMP-проверку.'],
 ['PING-NOT-SELECTED','monitor','VPN is outside the measured pair','VPN не входит в измеряемую пару','The background ICMP checks cover the selected primary and reserve VPNs. This profile is outside that pair.','Фоновые ICMP-проверки выполняются для выбранных основного и резервного VPN. Этот профиль не входит в эту пару.','Review the selected pair if this is the VPN you intended to monitor. Opening its information does not start a probe.','Если вы хотели наблюдать этот VPN, проверьте выбранную пару. Открытие его информации не запускает проверку.'],
 ['UI-HELP-LOAD-FAILED','service','Help could not be loaded','Не удалось загрузить справку','The optional Help, Training and catalogue module could not be loaded. Other pages keep working.','Не удалось загрузить модуль справки, обучения и каталога. Другие страницы продолжают работать.','Press Retry. If the failure continues, reload the page and check the router connection.','Нажмите «Повторить». Если ошибка остаётся, обновите страницу и проверьте связь с роутером.'],
 ["PUBLICATION-RECORD-SCOPE", "internal", "Release record differs from the tested source", "Запись выпуска отличается от проверенного исходника", "The release record contains changes outside the allowed package record, or its parent or package hash could not be verified.", "Запись выпуска содержит изменения вне разрешённых файлов либо не подтверждены родительский коммит или хеш пакета.", "Run the full CI on this commit, or create a direct child record containing only the verified package, checksum, new release notes and matching hash and size fields.", "Запустите полный CI на этом коммите либо создайте прямой дочерний коммит только с проверенным пакетом, контрольной суммой, новыми заметками выпуска и соответствующими полями хеша и размера."],
 ["PUBLICATION-CI-LUA", "internal", "The CI receipt does not prove Lua tests ran", "Квитанция CI не подтверждает проверку Lua", "The tools runtime receipt does not confirm Lua availability and at least one completed Lua-backed test.", "Квитанция среды проверки инструментов не подтверждает наличие Lua и выполнение хотя бы одного теста с Lua.", "Use the reviewed CI image with Lua and lua-cjson, run both runtime checks again, and keep the failed receipt as evidence.", "Используйте проверенный образ CI с Lua и lua-cjson, повторите проверки обеих сред и сохраните неудачную квитанцию."],

 ["SPEED-PAUSE-UNVERIFIED", "speed", "Pause could not be verified", "Не удалось проверить паузу", "The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.", "Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.", "Wait for the current operation to finish and retry. A manual Stop is never undone.", "Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется."],
 ["SPEED-PAUSE-BUSY", "speed", "Pause recovery in progress", "Пауза ещё завершается", "The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.", "Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.", "Wait for the current operation to finish and retry. A manual Stop is never undone.", "Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется."],
 ["SPEED-PAUSE-LOST", "speed", "Pause ownership changed", "Условия паузы изменились", "The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.", "Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.", "Wait for the current operation to finish and retry. A manual Stop is never undone.", "Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется."],
 ["SPEED-PAUSE-TIMEOUT", "speed", "Pause acknowledgement timed out", "Нет подтверждения паузы", "The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.", "Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.", "Wait for the current operation to finish and retry. A manual Stop is never undone.", "Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется."],
 ["SPEED-PAUSE-MODE", "speed", "Auto transition is not ready for pause", "Состояние Auto не готово к паузе", "The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.", "Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.", "Wait for the current operation to finish and retry. A manual Stop is never undone.", "Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется."],
 ["SPEED-CPU-UNKNOWN", "speed", "CPU observation unavailable", "Загрузка CPU не прочитана", "The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.", "Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.", "Wait for the current operation to finish and retry. A manual Stop is never undone.", "Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется."],
 ["DEVICE-MODEL-INVALID","platform","Choose a supported router model","Выберите поддерживаемую модель","The saved or requested model is not Automatic, MT6000 or MT3000.","Сохранённая или выбранная модель не входит в список: авто, MT6000, MT3000.","Open Settings and review the router model on the first setup step.","Откройте настройки и проверьте модель роутера на первом шаге мастера."],
 ["DEVICE-MODEL-MISMATCH","platform","Router model does not match","Модель роутера не совпадает","The selected model differs from detected hardware, or hardware could not be verified.","Выбранная модель отличается от обнаруженного оборудования либо оборудование не удалось проверить.","Choose automatic detection or the actual detected model; model selection never enables unsupported switching.","Выберите автоопределение или обнаруженную модель; выбор модели не включает неподдерживаемое переключение."],
 ["MANUAL-FIELDS","manual","Manual request form changed","Форма ручного запроса изменилась","The request contains missing or unexpected fields.","В запросе отсутствуют поля либо есть лишние.","Reload the page and choose one of the two manual switch buttons.","Обновите страницу и выберите одну из двух кнопок ручного переключения."],
 ["MANUAL-DIRECTION-INVALID","manual","Choose a supported direction","Выберите допустимое направление","The requested direction is neither the saved primary nor the reserve.","Запрошено направление, отличное от сохранённого основного или резервного.","Reload the page and use Switch to primary or Switch to reserve.","Обновите страницу и используйте переключение на основной либо резервный."],
 ["MANUAL-STATE-UNVERIFIED","manual","Manual control state is unknown","Состояние ручного управления неизвестно","The request or Stop records could not be verified; a new switch is blocked.","Не удалось проверить запись запроса или остановки; новое переключение заблокировано.","Refresh the status. Keep Emergency Stop and trusted recovery available; do not delete the state records.","Обновите состояние. Используйте аварийную остановку и доступное восстановление; не удаляйте записи состояния."],
 ["MANUAL-ALREADY-CLAIMED","manual","Request was already taken","Запрос уже принят в работу","The controller has already taken or finished this request; it must not run it twice.","Контроллер уже принял или завершил этот запрос; повторное выполнение недопустимо.","Wait for fresh status and review the actual path before making another explicit request.","Дождитесь свежего состояния и проверьте фактический путь перед новым явным запросом."],
 ["MANUAL-REQUEST-EXPIRED","manual","Manual request expired","Время ручного запроса истекло","The request was not taken within its short validity window. This does not confirm the current traffic path.","Запрос не принят в течение короткого срока действия. Это не подтверждает текущий путь трафика.","Refresh the router state and repeat only if the switch is still needed.","Обновите состояние роутера и повторите только при необходимости переключения."],
 ["STOP-SUPERSEDED-MANUAL","manual","Stop cancelled the pending switch","Остановка отменила ожидающее переключение","An Emergency Stop arrived after this manual request, so the pending request cannot run.","Аварийная остановка поступила после ручного запроса, поэтому ожидающий запрос не выполнится.","Review the current path. A later switch requires a new explicit request.","Проверьте текущий путь. Для последующего переключения нужен новый явный запрос."],
 ["MANUAL-CONFIG-CHANGED","manual","Settings changed during the request","Настройки изменились во время запроса","The selected pair, trial window or policy no longer matches the request.","Выбранная пара, окно теста или политика больше не соответствует запросу.","Refresh and review the pair and required checks before requesting again.","Обновите страницу, проверьте пару и необходимые проверки перед новым запросом."],
 ["MANUAL-SUPERVISOR-UNAVAILABLE","manual","No fresh controller state","Нет свежего состояния контроллера","The switching controller has not supplied a recent verified status.","Контроллер переключений не предоставил недавнего проверенного состояния.","Check Service monitor and wait for fresh status. A monitor-only installation cannot perform native switches.","Проверьте службу мониторинга и дождитесь свежего состояния. Установка только для мониторинга не выполняет нативных переключений."],
 ["MANUAL-STOP-AUTO-FIRST","manual","Stop Auto before manual switching","Остановите Auto перед ручным переключением","Auto is active; a separate manual switch cannot compete with it.","Auto активен; отдельное ручное переключение не должно с ним конкурировать.","Press the Auto power button to stop and review the resulting path before trying manual switching.","Нажмите аварийную остановку и проверьте получившийся путь перед ручным переключением."],
 ["MANUAL-SELECTION-UNVERIFIED","manual","Selected pair is not verified","Выбранная пара не проверена","The controller cannot prove the selected primary and reserve or their routing policy.","Контроллер не может подтвердить выбранные основной и резервный профили либо их политику маршрутизации.","Review the saved pair in Settings and obtain fresh matching checks.","Проверьте сохранённую пару в настройках и дождитесь свежих согласованных проверок."],
 ["MANUAL-REQUEST-PENDING","manual","Another manual request is pending","Другой ручной запрос ещё выполняется","A manual switch is already queued or running.","Ручное переключение уже ожидает выполнения или выполняется.","Wait for its result or press the Auto power button to stop; do not submit duplicates.","Дождитесь результата либо используйте аварийную остановку; не отправляйте дубликаты."],
 ["MANUAL-REQUEST-UNCONFIRMED","manual","Request was not confirmed","Запрос не подтверждён","No reliable acknowledgement was received. The request may have been stored.","Надёжное подтверждение не получено. Запрос мог сохраниться.","Refresh status and inspect the actual path before deciding whether to retry.","Обновите состояние и проверьте фактический путь перед решением о повторе."],
 ["MANUAL-RESULT-INVALID","manual","Result record is invalid","Запись результата некорректна","The result record does not match the supported manual request format. It does not prove success.","Запись результата не соответствует формату ручного запроса. Она не доказывает успех.","Keep the diagnostics and check the current path; do not force completion or erase recovery records.","Сохраните диагностику и проверьте текущий путь; не принуждайте завершение и не стирайте записи восстановления."],
 ["MANUAL-COMPLETION-UNVERIFIED","manual","Switch completion is not proved","Завершение переключения не доказано","The controller could not verify the transaction evidence required to mark this request complete.","Контроллер не смог проверить данные транзакции, необходимые для подтверждения завершения запроса.","Review fresh route and connectivity status. Use the documented recovery controls if needed.","Проверьте свежие данные маршрута и доступности. При необходимости используйте описанные средства восстановления."],
 ["RETURN-UNCONFIRMED","manual","Return to primary is unconfirmed","Возврат на основной не подтверждён","The return request has no verified successful result. The reserve may still be in use.","У запроса возврата нет проверенного успешного результата. Резерв может ещё использоваться.","Inspect the actual path and primary health before requesting another return.","Проверьте фактический путь и доступность основного перед повторным возвратом."],
 ["MANUAL-RESULT-UNCONFIRMED","manual","Manual result is unknown","Результат ручного переключения неизвестен","The request did not produce a trusted final result. A queue acknowledgement is not route confirmation.","Запрос не дал доверенного конечного результата. Подтверждение очереди не подтверждает маршрут.","Refresh status and review Stop or recovery controls before repeating any action.","Обновите состояние и проверьте средства остановки или восстановления перед повторным действием."],
 ["MANUAL-SUPERVISOR-RECOVERED","manual","Controller recovered an unfinished request","Контроллер восстановился после незавершённого запроса","After restarting, the controller found an unfinished request without sufficient proof of completion. It is not replayed automatically.","После перезапуска контроллер обнаружил незавершённый запрос без достаточного подтверждения результата. Автоматически он не повторяется.","Review the current path and recovery status before issuing a new request.","Проверьте текущий путь и состояние восстановления перед новым запросом."],
 ["MANUAL-TRANSACTION-STATE-UNVERIFIED","manual","The previous switch did not finish","Прошлое переключение не завершилось","The absence of an earlier transaction or application safety guard could not be verified.","Не удалось подтвердить отсутствие прежней транзакции или защитной блокировки приложения.","Keep Stop and recovery available. Resolve the existing transaction through the documented recovery procedure before starting another.","Используйте доступные остановку и восстановление. Завершите прежнюю транзакцию по описанной процедуре перед новой."],
 ["MANUAL-REQUEST-INVALID","manual","Manual request could not be trusted","Ручному запросу нельзя доверять","The final controller boundary rejected the manual request identity or format.","Последняя проверка контроллера отклонила идентификатор либо формат ручного запроса.","Refresh the application and review current status before making a new explicit request.","Обновите приложение и проверьте текущее состояние перед новым явным запросом."],
 ["OPERATOR-MANUAL","manual","Operator requested a manual switch","Оператор запросил ручное переключение","This event belongs to one explicit manual switch. It does not imply primary failure or that Auto was enabled.","Это событие относится к одному явному ручному переключению. Оно не означает отказ основного или включение Auto.","Read the later transaction outcome and current confirmed path to see whether it succeeded.","Посмотрите последующий итог транзакции и текущий подтверждённый путь, чтобы узнать результат."],
 ["MT3000-MANUAL-ADAPTER-NOT-CERTIFIED","platform","MT3000 manual switching is not certified","Ручное переключение MT3000 не подтверждено","The GL-MT3000 manual adapter has not passed the required certification. Passing individual observations does not authorize a switch.","Адаптер ручного переключения GL-MT3000 не прошёл необходимое подтверждение. Отдельные успешные наблюдения не разрешают переключение.","Continue monitoring; complete the documented router and LAN acceptance before enabling this adapter.","Продолжайте мониторинг; завершите описанные проверки роутера и LAN перед включением адаптера."],
 ["MT3000-COLLECTION-DEADLINE","platform","Readiness check took too long","Проверка готовности заняла слишком много времени","The bounded collection of router evidence exceeded its deadline; the incomplete snapshot cannot authorize a switch.","Сбор данных роутера превысил ограниченное время; неполный снимок не разрешает переключение.","Wait for the router to settle and request fresh status. If it repeats, inspect router load.","Дождитесь спокойного состояния роутера и запросите свежие данные. Если повторяется, проверьте нагрузку."],
 ["MT3000-COLLECTION-CLOCK-CHANGED","platform","Router clock changed during checks","Часы роутера изменились во время проверок","Clock continuity was lost while readiness evidence was collected. Its timing cannot be trusted.","При сборе данных готовности нарушилась непрерывность времени. Их временным отметкам нельзя доверять.","Review the router clock and wait for stable time before collecting new evidence.","Проверьте часы роутера и дождитесь стабильного времени перед новым сбором данных."],
 ["MT3000-READ-TIMEOUT","platform","Router read timed out","Чтение данных роутера превысило время","A read-only readiness command did not finish in its allowed time.","Команда чтения готовности не завершилась за разрешённое время.","Wait and refresh. Inspect router responsiveness if this continues.","Подождите и обновите данные. Если повторяется, проверьте отзывчивость роутера."],
 ["MT3000-READ-FAILED","platform","Router evidence could not be read","Не удалось прочитать данные роутера","A command used to collect readiness evidence failed.","Команда сбора данных готовности завершилась ошибкой.","Keep the diagnostic code and check the router services and required tools before retrying.","Сохраните код диагностики и проверьте службы и необходимые программы роутера перед повтором."],
 ["MT3000-READ-UNVERIFIED","platform","Router read could not be validated","Чтение данных роутера не проверено","A readiness response was incomplete, oversized or did not match the expected format.","Ответ проверки готовности неполон, слишком велик либо имеет неожиданный формат.","Refresh once the router is stable. If repeated, have the firmware compatibility checked.","Обновите данные после стабилизации роутера. Если повторяется, проверьте совместимость прошивки."],
 ["MT3000-PLATFORM-UNVERIFIED","platform","Router model is not verified","Модель роутера не проверена","The collected board identity does not match the supported GL-MT3000 platform contract.","Собранные данные платы не соответствуют поддерживаемому варианту GL-MT3000.","Check the actual router model. Monitoring does not grant manual switching support.","Проверьте фактическую модель роутера. Мониторинг не означает поддержку ручного переключения."],
 ["MT3000-FIRMWARE-UNVERIFIED","platform","Router firmware is not verified","Прошивка роутера не проверена","The firmware, kernel or architecture differs from the inspected GL-MT3000 combination.","Прошивка, ядро или архитектура отличается от проверенного сочетания GL-MT3000.","Keep native switching disabled until this exact firmware combination has been reviewed.","Оставьте нативное переключение выключенным до проверки именно этого сочетания прошивки."],
 ["MT3000-FIREWALL-UNVERIFIED","platform","Firewall type is not verified","Тип firewall не проверен","The router firewall does not match the firewall arrangement required by this adapter.","Firewall роутера не соответствует варианту, необходимому этому адаптеру.","Keep current routes and have firewall compatibility reviewed; do not force the adapter on.","Сохраните текущие маршруты и проверьте совместимость firewall; не включайте адаптер принудительно."],
 ["FW3-INCLUDE-CONTRACT-UNVERIFIED","platform","Firmware firewall integration is unverified","Интеграция firewall прошивки не проверена","The firmware firewall include settings differ from the inspected contract; safe reload coordination is not proved.","Настройки подключаемого скрипта firewall отличаются от проверенного варианта; безопасная координация перезагрузки не доказана.","Keep current routes and have the firmware firewall integration checked before switching.","Сохраните текущие маршруты и проверьте интеграцию firewall прошивки перед переключением."],
 ["FW3-RUNTIME-STATE-UNVERIFIED","platform","Live firewall state is unknown","Рабочее состояние firewall неизвестно","The current firewall zones could not be read and validated.","Не удалось прочитать и проверить текущие зоны firewall.","Wait for any firewall changes to finish, then refresh. Do not infer readiness from saved settings alone.","Дождитесь завершения изменений firewall и обновите данные. Одни сохранённые настройки не доказывают готовность."],
 ["VENDOR-WORKER-QUIET-UNVERIFIED","platform","Router VPN changes may still be running","Изменение VPN роутером может ещё выполняться","Repeated observations did not prove that the firmware VPN workers are idle.","Повторные наблюдения не подтвердили, что процессы VPN штатной прошивки свободны.","Wait for the router VPN operation to finish before requesting another change.","Дождитесь завершения операции VPN роутера перед новым изменением."],
 ["NATIVE-CONTROLLER-STATE-UNVERIFIED","platform","Auto controller is not confirmed off","Выключение контроллера Auto не подтверждено","The saved native controller setting is not explicitly off, so the manual adapter cannot claim exclusive control.","Сохранённая настройка нативного контроллера не подтверждает выключение, поэтому ручной адаптер не может получить исключительное управление.","Stop Auto and review its fresh status before manual switching.","Остановите Auto и проверьте его свежее состояние перед ручным переключением."],
 ["SELECTED-RULES-NOT-ADJACENT","platform","Selected VPN rules are not adjacent","Правила выбранных VPN не соседние","The saved primary and reserve rules are separated in the router policy; the bounded adapter cannot safely reorder this pair.","Правила сохранённых основного и резервного разделены в политике роутера; ограниченный адаптер не может безопасно переставить эту пару.","Review the VPN policy with the administrator; do not change rule order while a transaction is active.","Проверьте политику VPN с администратором; не меняйте порядок правил во время активной транзакции."],
 ["EXISTING-TUNNEL-BINDING-UNVERIFIED","platform","Working VPN not checked","Рабочий VPN не проверен","A selected tunnel is down, changing or no longer matches its observed interface, device and routing identity.","Выбранный туннель отключён, изменяется либо больше не соответствует наблюдавшимся интерфейсу, устройству и маршрутизации.","Wait for the intended VPNs to settle and obtain fresh matching checks.","Дождитесь стабильной работы нужных VPN и свежих согласованных проверок."],
 ["FW3-SELECTED-ZONE-UNVERIFIED","platform","VPN firewall zone is unverified","Зона firewall VPN не проверена","A selected VPN interface is missing from the current verified firewall zones.","Выбранный интерфейс VPN отсутствует в текущих проверенных зонах firewall.","Have the VPN firewall zone binding checked before switching; preserve existing protection rules.","Проверьте привязку зоны firewall VPN перед переключением; сохраните действующие защитные правила."],
 ["SHARED-KERNEL-BINDING","platform","VPN choices share the same routing resource","Выбранные VPN используют общий ресурс маршрутизации","The two choices share a device, interface identity or routing mark/table, so independent paths cannot be proved.","Два выбранных VPN используют общее устройство, идентичность интерфейса либо метку и таблицу маршрутизации; независимость путей не доказана.","Choose truly distinct tunnels and repeat the identity checks. Different display names are not sufficient.","Выберите действительно разные туннели и повторите проверки привязки. Разных названий недостаточно."],
 ["TARGET-ROUTER-PATH-UNVERIFIED","platform","Reserve router checks have not passed","Резерв не прошёл проверки с роутера","The current target has no fresh matching successful DNS and HTTPS evidence. This is separate from LAN path confirmation.","Для текущего целевого VPN нет свежих согласованных успешных проверок DNS и HTTPS. Это отдельно от подтверждения пути LAN.","Check reserve connectivity and wait for fresh router measurements; An external-LAN mode still needs its separate client confirmation; prepared router-probed mode has its own guards.","Проверьте доступность резерва и дождитесь свежих измерений роутера; Для режима внешнего LAN нужно отдельное подтверждение клиента; у подготовленного router-probed режима собственные проверки."],
 ["MT3000-EVIDENCE-UNVERIFIED","platform","MT3000 readiness evidence is incomplete","Данные готовности MT3000 неполны","The collected readiness snapshot is inconsistent or cannot be validated. No manual switch is authorized by it.","Собранный снимок готовности несогласован либо не проходит проверку. Он не разрешает ручное переключение.","Review diagnostics and obtain a fresh complete snapshot after the router is stable.","Проверьте диагностику и получите свежий полный снимок после стабилизации роутера."],

 ['MONITOR-ONLY-DEPLOYMENT','switch','Installation is limited to monitoring','Установка ограничена мониторингом','This deployment permits monitoring only. Native switching is disabled; monitor results do not certify firmware coordination or the LAN path.','Эта установка разрешает только мониторинг. Нативное переключение выключено; результаты мониторинга не подтверждают координацию с прошивкой или путь LAN.','Continue monitoring within the agreed scope. Native actions remain unavailable in this deployment.','Продолжайте мониторинг в согласованном объёме. Нативные действия в этой установке остаются недоступны.'],
 ['MONITOR-ONLY-INVALID','switch','Deployment mode could not be verified','Не удалось проверить режим установки','The internal deployment setting is malformed or unverified. Native actions are refused.','Внутренний параметр установки повреждён или не проверен. Нативные действия отклоняются.','Have the deployment settings checked against the verified installation procedure. Do not treat this state as native readiness.','Проверьте параметры установки по проверенной процедуре установки. Это состояние не означает готовность нативного переключения.'],
 ['NATIVE-PROGRESS-UNVERIFIED','switch','Controller progress records are unverified','Записи состояния контроллера не проверены','Saved native progress or state records cannot be trusted. New controller actions are refused; Stop and recovery from a trusted journal remain available.','Сохранённым записям хода работы или состояния контроллера нельзя доверять. Новые действия отклоняются; остановка и восстановление по доверенному журналу остаются доступны.','Keep the Stop and recovery controls available. Inspect diagnostics and restore progress records through the documented recovery procedure.','Используйте доступные средства остановки и восстановления. Проверьте диагностику и восстановите записи состояния по описанной процедуре восстановления.'],
 ['VENDOR-IDENTITY-UNKNOWN','switch','Cannot find this VPN on the router','Не удаётся найти этот VPN на роутере','The configured profile cannot be matched unambiguously to a current router tunnel.','Не удалось однозначно сопоставить профиль с текущим туннелем роутера.','Wait for fresh observations. If the saved pair is unbound, choose active profiles in Settings and save the pair.','Дождитесь свежих наблюдений. Если пара не привязана, выберите активные профили в настройках и сохраните пару.'],
 ['VENDOR-IDENTITY-CHANGED','monitor','VPN changed during a check','VPN изменился во время проверки','The tunnel binding changed while measurements were running; their health and exit results were discarded.','Привязка туннеля изменилась во время измерений; результаты доступности и адреса выхода отброшены.','Wait for new checks of this VPN.','Дождитесь новых проверок этого VPN.'],
 ['PROFILE-IDENTITY-CHANGED','switch','VPN profile changed','VPN-профиль изменился','The current profile or tunnel generation no longer matches the evidence used for this decision.','Текущий профиль или поколение туннеля не соответствует данным, использованным для решения.','Wait for current observations; a new verified trial may be needed before Auto can run.','Дождитесь текущих наблюдений; перед запуском Auto может потребоваться новый подтверждённый тест.'],
 ['PAIR-EXTERNAL-POLICY-CHANGE','switch','Route rules differ from the saved session','Правила маршрутов отличаются от сохранённой сессии','The order or content of the VPN route rules no longer matches the saved Auto session. Who or what changed them is not established: an edit in the stock VPN page and the stock router services can both change them. Renaming a tunnel alone does not count.','Порядок или содержимое правил маршрутов VPN больше не совпадает с сохранённой сессией Auto. Кто или что их изменил, не установлено: их может менять и правка в штатной странице VPN, и штатные службы роутера. Простое переименование туннеля не считается.','Press Start: Auto archives the old session and adopts the current rules by itself. If it refuses again within 15 minutes, the rules are still changing: wait and try again.','Нажмите Start: Auto сам архивирует старую сессию и примет текущие правила. Если в течение 15 минут отказ повторяется, правила ещё меняются: подождите и повторите.'],
 ['PAIR-EXTERNAL-NETWORK-CHANGE','switch','Network settings differ from the saved session','Сетевые настройки отличаются от сохранённой сессии','A network interface of the selected pair, or another interface, changed after Auto started (not a stopped leftover client). The comparison does not show who or what changed it.','Сетевой интерфейс выбранной пары или другой интерфейс изменился после запуска Auto (не остановленный лишний клиент). Сравнение не показывает, кто или что его изменил.','Press Start: Auto adopts the current settings by itself. Repeated refusals mean the settings are still changing.','Нажмите Start: Auto сам примет текущие настройки. Повторные отказы значат, что настройки ещё меняются.'],
 ['PAIR-EXTERNAL-CONFIG-CHANGE','switch','Protected router configuration differs','Защищённая конфигурация роутера отличается','A protected configuration (firewall, DNS, Wi-Fi or the VPN profiles) differs from the one Auto saw when it started. The comparison does not show who or what changed it: the stock router services can change it too.','Защищённая конфигурация (файрвол, DNS, Wi-Fi или профили VPN) отличается от той, которую Auto видел при запуске. Сравнение не показывает, кто или что её изменил: её могут менять и штатные службы роутера.','Press Start: Auto archives the old session and adopts the current configuration by itself.','Нажмите Start: Auto архивирует старую сессию и сам примет текущую конфигурацию.'],
 ['PAIR-RECOVERY-REQUIRED','switch','Unfinished switch needs recovery','Незавершённое переключение требует восстановления','An earlier switch or Auto session did not finish, nothing is running it now, and it cannot be taken over automatically (for example the router is held on the reserve, or the automatic takeover already ran three times in 15 minutes). The journal and safety guard are kept; the traffic channel is not verified. This does not mean that you changed any settings.','Предыдущее переключение или сессия Auto не завершились, сейчас их ничто не выполняет, и принять их автоматически нельзя (например роутер удерживается на резерве или автоматический приём уже выполнялся три раза за 15 минут). Журнал и защита сохранены; канал трафика не подтверждён. Это не означает, что вы меняли настройки.','Do not repeat Start or manual switching: they are refused until recovery completes. If the router is held on the reserve, wait for the primary to recover. Keep the journal; if the state does not change, the router needs its guarded recovery procedure.','Не повторяйте Start и ручное переключение: они отклоняются до завершения восстановления. Если роутер удерживается на резерве, дождитесь восстановления основного. Сохраните журнал; если состояние не меняется, роутеру нужна проверенная процедура восстановления.'],
 ['PAIR-READOPTED','state','Auto re-read changed settings','Auto заново прочитал изменённые настройки','Protected settings differed from the saved session. Auto archived the old session, adopted the current settings and started again by itself.','Защищённые настройки отличались от сохранённой сессии. Auto архивировал старую сессию, принял текущие настройки и сам запустился заново.','Nothing to do. The old session is kept in the router recovery folder.','Делать ничего не нужно. Старая сессия сохранена в папке восстановления роутера.'],
 ['SWITCH-RESULT-UNCONFIRMED','switch','Switch result not confirmed in time','Результат переключения не подтверждён вовремя','The page saw a switch phase, but the router did not report its end before the switch deadline (at most 2 minutes plus a short check). The traffic channel is not verified; the page does not show success or keep counting.','Страница видела фазу переключения, но роутер не сообщил о его завершении до предельного срока (не более 2 минут и короткая проверка). Канал трафика не подтверждён; страница не показывает успех и не продолжает отсчёт.','Do not repeat the switch. Wait for the next router state; Stop remains available. If it stays like this, the unfinished switch needs recovery.','Не повторяйте переключение. Дождитесь следующего состояния роутера; Stop остаётся доступен. Если состояние не меняется, незавершённое переключение требует восстановления.'],
 ['VENDOR-REASON-UNOBSERVED','monitor','Firmware server choice is not visible','Выбор сервера прошивкой не виден','The stock firmware chooses the server inside a channel and does not report why or how many times it tried. The app checks only whether the channel works now.','Штатная прошивка сама выбирает сервер внутри канала и не сообщает, почему и сколько раз пыталась. Приложение проверяет только, работает ли канал сейчас.','Nothing to do. To pick a different server use Channels and servers.','Делать ничего не нужно. Чтобы выбрать другой сервер, откройте «Каналы и серверы».'],
 ['AUTOMATIC-EXTERNAL-CHANGE-READOPT','state','Old Auto session archived automatically','Старая сессия Auto архивирована автоматически','Recorded in the archived Auto session when protected settings differed from it and Auto adopted the current settings by itself.','Запись в архивной сессии Auto: защищённые настройки отличались от неё, и Auto сам принял текущие настройки.','Nothing to do. The archived copy stays in the router recovery folder.','Делать ничего не нужно. Архивная копия остаётся в папке восстановления роутера.'],
 ['STATUS-REQUEST-FAILED','monitor','No answer from the router program','Нет ответа от программы на роутере','The page asked the router for the current state and got no answer (timeout, a busy router or a page error). Nothing is shown as working until it answers.','Страница запросила у роутера текущее состояние и не получила ответа (тайм-аут, роутер занят или ошибка страницы). Пока ответа нет, ничего не показывается как рабочее.','Wait a few seconds; reload the page with Ctrl+F5. If it repeats, open Settings and check that monitoring is running.','Подождите несколько секунд и обновите страницу (Ctrl+F5). Если повторяется, откройте «Настройки» и проверьте, что мониторинг запущен.'],
 ['MONITOR-DATA-STALE','monitor','Router data is old','Данные роутера устарели','The router program answered, but its last measurement is older than 90 seconds, so it cannot describe the channels now.','Программа роутера ответила, но её последнее измерение старше 90 секунд, поэтому оно не описывает каналы сейчас.','Check that monitoring is running (Settings). A speed test pauses measurements for up to a minute.','Проверьте, что мониторинг запущен («Настройки»). Тест скорости приостанавливает измерения до минуты.'],
 ['VENDOR-OBSERVATION-PENDING','monitor','Channel not observed yet','Канал ещё не наблюдался','Monitoring is collecting the first observations of this channel after a start or a settings change.','Мониторинг собирает первые наблюдения этого канала после запуска или изменения настроек.','Wait up to a minute; the result appears by itself.','Подождите до минуты; результат появится сам.'],
 ['AUTO-CONTROL-UNCONFIRMED','switch','Auto did not confirm the command','Auto не подтвердил команду','The page sent Start or Stop, but the router did not report the result within two minutes. The button is released so you can try again.','Страница отправила «Старт» или «Стоп», но роутер не сообщил результат за две минуты. Кнопка снова доступна, можно повторить.','Check the Auto lamp and the status in a minute. If nothing changed, press the button again; if it repeats, check that monitoring is running (Settings).','Посмотрите на лампу Auto и состояние через минуту. Если ничего не изменилось, нажмите кнопку ещё раз; если повторяется, проверьте, что мониторинг запущен («Настройки»).'],
 ['UI-ACTION-FAILED','monitor','The page could not finish the action','Страница не смогла выполнить действие','The page sent a request, but it failed before the router answered (connection lost or a page error). Nothing was changed by this press.','Страница отправила запрос, но он не прошёл до ответа роутера (связь пропала или ошибка страницы). Это нажатие ничего не изменило.','Reload the page (Ctrl+F5) and repeat the action.','Обновите страницу (Ctrl+F5) и повторите действие.'],
 ['UI-RENDER-FAILED','monitor','Part of the page could not be drawn','Часть страницы не удалось показать','The router answered, but one part of the page failed while drawing; the rest of the page keeps working.','Роутер ответил, но одна часть страницы не отрисовалась; остальная страница работает.','Reload the page (Ctrl+F5). If it repeats, send the code and a screenshot to the developer.','Обновите страницу (Ctrl+F5). Если повторяется, отправьте код и снимок экрана разработчику.'],
 ['MANUAL-SWITCH-UNCONFIRMED','switch','Manual switch not confirmed','Ручное переключение не подтверждено','The router did not confirm the manual switch and gave no other reason. The route stays as the router reports it.','Роутер не подтвердил ручное переключение и не назвал другой причины. Маршрут остаётся таким, как сообщает роутер.','Wait for the next router check (about 10 seconds) and press the channel again if needed.','Дождитесь следующей проверки роутера (около 10 секунд) и при необходимости нажмите канал ещё раз.'],
 ['STATS-RESET-ARCHIVE-UNVERIFIED','monitor','Archive could not be read back','Архив не прочитался обратно','The router wrote the archive of the old data, but reading it back did not match, so it reset nothing.','Роутер записал архив старых данных, но проверка чтением не совпала, поэтому ничего не сброшено.','Check free space on the router and press Reset chart again.','Проверьте свободное место на роутере и снова нажмите «Сброс графика».'],
 ['STATS-RESET-FIELDS','monitor','Reset request not accepted','Запрос сброса не принят','The page asked to reset a chart the router does not know. Nothing was reset.','Страница попросила сбросить график, который роутер не знает. Ничего не сброшено.','Reload the page (Ctrl+F5) and press Reset chart again.','Обновите страницу (Ctrl+F5) и снова нажмите «Сброс графика».'],
 ['STATS-RESET-FAILED','monitor','Reset not completed','Сброс не выполнен','The router could not save the archive of the old data, so it kept the data unchanged.','Роутер не смог сохранить архив старых данных и поэтому оставил данные без изменений.','Check free space on the router (System → Software or df -h) and try again.','Проверьте свободное место на роутере (System → Software или df -h) и повторите.'],
 ['STATS-RESET-ARCHIVE-PATH','monitor','Archive folder is not safe','Папка архива небезопасна','The archive folder on the router is a link, not a folder, so the reset was refused.','Папка архива на роутере является ссылкой, а не папкой, поэтому сброс отклонён.','Remove /etc/homensai-vpn/stats-archive on the router and try again.','Удалите /etc/homensai-vpn/stats-archive на роутере и повторите.'],
 ['STATS-RESET-UNCONFIRMED','monitor','Reset not confirmed in time','Сброс не подтверждён вовремя','The router accepted the request but its monitoring did not report the result within 45 seconds (it may be stopped or paused by a speed test).','Роутер принял запрос, но мониторинг не сообщил результат за 45 секунд (он может быть остановлен или на паузе из-за теста скорости).','Check that monitoring is running (Settings), wait a minute and look at the chart; press Reset again if needed.','Проверьте, что мониторинг запущен («Настройки»), подождите минуту и посмотрите на график; при необходимости нажмите «Сброс» ещё раз.'],
 ['RESERVE-ALREADY-FIRST','state','The reserve is already the router first choice','Резерв уже стоит первым у роутера','The primary fails, but the router VPN priority list already puts the reserve first, so traffic already goes through the reserve. Auto keeps watching and does not switch.','Основной канал не работает, но в списке приоритетов VPN роутера резерв уже стоит первым, поэтому трафик уже идёт через резерв. Auto продолжает наблюдение и ничего не переключает.','Nothing to do. If you want the primary first again, move it to Priority 1 in the router VPN Dashboard when it works.','Делать ничего не нужно. Если хотите снова поставить основной первым, когда он заработает, переместите его на Priority 1 в VPN Dashboard роутера.'],
 ['CHANNEL-UNRELIABLE','monitor','Channel reliability problem','Проблема с надёжностью канала','Over the last 5 minutes the router\'s own checks through this channel failed in at least 20% of the cycles (a cycle fails when DNS fails or fewer than two of three HTTPS checks pass). The tunnel can still show as connected. This is a measured share of failed checks, not an ICMP packet-loss figure, and it changes no setting.','За последние 5 минут собственные проверки роутера через этот канал не прошли минимум в 20% циклов (цикл не пройден, если не работает DNS или проходит меньше двух из трёх HTTPS-проверок). Туннель при этом может быть «подключён». Это измеренная доля непройденных проверок, а не ICMP-потеря пакетов; настройки она не меняет.','Follow the recommendation: keep traffic on the channel with the lower loss and replace the server of the unreliable one in Channels and servers; if both lose checks, test the router uplink first. Run a speed test to measure other servers.','Следуйте рекомендации: держите трафик на канале с меньшими потерями и замените сервер ненадёжного в «Каналы и серверы»; если теряют оба, сначала проверьте подключение роутера. Запустите тест скорости, чтобы измерить другие серверы.'],
 ['RESERVE-NOT-CONNECTED','switch','Reserve channel is not connected','Резервный канал не подключён','The reserve client is enabled but the router reports no running tunnel. Auto cannot switch to it, and the primary keeps carrying traffic.','Резервный клиент включён, но роутер не видит работающего туннеля. Auto не может на него переключиться, основной канал продолжает работать.','Auto starts a stopped enabled reserve itself, at most once per two minutes and four times per 15 minutes. If it still does not connect, check the reserve server in the router VPN page or choose another reserve server in Channels and servers.','Auto сам запускает остановленный включённый резерв: не чаще раза в две минуты и четырёх раз за 15 минут. Если он не подключается, проверьте сервер резерва на странице VPN роутера или выберите другой сервер резерва в «Каналы и серверы».'],
 ['VENDOR-SAME-TUNNEL','switch','Server selection belongs to the router','Сервер выбирает штатная прошивка','Both choices refer to one observed tunnel. The application does not run a competing server switch loop.','Оба выбора относятся к одному наблюдаемому туннелю. Приложение не запускает конкурирующий перебор серверов.','Choose a different tunnel for application reserve switching.','Для резервирования приложением выберите другой туннель.'],
 ['SETUP-SAME-TUNNEL','setup','Choose two different tunnels','Выберите два разных туннеля','The selected primary and reserve resolve to the same router tunnel.','Выбранные основной и резервный профили привязаны к одному туннелю роутера.','Select an active profile on another tunnel, or defer the pair.','Выберите активный профиль другого туннеля либо отложите пару.'],
 ['VENDOR-SETTLING','switch','The router is still checking VPN settings','Роутер ещё проверяет настройки VPN','The identity observation window has not finished. This does not reveal whether the firmware exhausted its server attempts.','Окно наблюдения за идентичностью ещё не завершено. Это не показывает, исчерпала ли прошивка попытки подключения серверов.','Wait for repeated fresh observations.','Дождитесь повторных свежих наблюдений.'],
 ["CROSS-TUNNEL-READY", "switch", "This VPN pair is suitable for Auto", "Эта пара VPN подходит для Auto", "The current configured tunnel identities are eligible for read-only planning; route changes remain separately guarded.", "Текущие привязки туннелей подходят для планирования без применения; изменение маршрутов требует отдельных проверок.", "This is consistent tunnel observation, not switching permission or LAN certification. Use the actual controller readiness for the chosen proof mode.", "Это согласованное наблюдение туннелей, а не разрешение переключать или сертификат LAN. Используйте действующую готовность контроллера выбранного режима."],
 ['CURRENT-PROFILE-FAILURE-STREAK','switch','Current profile failed repeated checks','Текущий профиль не прошёл несколько проверок','The current bound profile has the configured failure streak. This does not prove that all servers in its tunnel have failed.','У текущего привязанного профиля накопилась заданная серия неудачных проверок. Это не доказывает отказ всех серверов его туннеля.','Review tunnel observations and reserve evidence.','Проверьте наблюдения туннеля и данные о резерве.'],
 ['RESERVE-IDENTITY-UNKNOWN','switch','Cannot find this VPN on the router','Не удаётся найти этот VPN на роутере','The controller cannot safely attach old reserve health to its current tunnel member.','Контроллер не может безопасно отнести старые проверки резерва к текущему профилю туннеля.','Keep the recovery controls available and obtain fresh observations before a new forward action.','Используйте доступные средства восстановления и дождитесь свежих наблюдений перед новым переключением.'],
 ['VENDOR-FIRST-OBSERVATION','data','VPN seen for the first time','VPN замечен впервые','The monitor first observed this configured tunnel member. No switch cause is inferred.','Монитор впервые увидел этот профиль в конфигурации туннеля. Причина выбора не предполагается.','No action is required; wait for fresh checks.','Действий не требуется; дождитесь свежих проверок.'],
 ['VENDOR-PROFILE-CHANGED','data','Configured tunnel member changed','Профиль в конфигурации туннеля изменился','A different configured profile was observed on the same tunnel. The cause and actual LAN outcome remain unobserved.','В том же туннеле наблюдался другой профиль конфигурации. Причина и фактический результат для LAN не установлены.','Inspect the current profile checks.','Посмотрите проверки текущего профиля.'],
 ['VENDOR-BINDING-CHANGED','data','VPN settings changed','Настройки VPN изменились','The monitor observed a new binding generation; earlier health cannot make it ready.','Монитор увидел новое поколение привязки; старые проверки не подтверждают его готовность.','Wait for checks with the new settings.','Дождитесь проверок с новыми настройками.'],
 ['VENDOR-BINDING-UNKNOWN','data','VPN profile changed or removed on the router','VPN-профиль изменён или удалён на роутере','The previous configured tunnel member can no longer be identified unambiguously.','Предыдущий профиль конфигурации туннеля больше не определяется однозначно.','Inspect current router configuration and fresh observations.','Проверьте текущую конфигурацию роутера и свежие наблюдения.'],
 ['VENDOR-OBSERVATION-TIME','data','Invalid observation clock','Некорректное время наблюдения','The check time is invalid, so it is unknown which VPN is in use.','Время проверки неверно, поэтому неизвестно, какой VPN работает.','Check the router clock and retry observation.','Проверьте часы роутера и дождитесь нового наблюдения.'],
 ['ONBOARDING-FIELDS','setup','Setup form changed','Форма настройки изменилась','The complete setup request has missing or unexpected sections.','В запросе общей настройки отсутствуют разделы или есть лишние.','Reload the application and review the complete setup again.','Обновите приложение и снова проверьте общую настройку.'],
 ['ONBOARDING-SYSTEM-FIELDS','setup','Check VPN setup','Проверьте настройку VPN','The VPN setup fields do not match the supported form.','Поля настройки VPN не соответствуют поддерживаемой форме.','Reload and choose existing profiles or explicitly defer the pair.','Обновите страницу и выберите существующие профили либо явно отложите пару.'],
 ['ONBOARDING-PAIR-DEFERRED','setup','Review deferred VPN pair','Проверьте отложенную пару VPN','A deferred VPN pair must have read-only planning switched off.','При отложенной паре VPN планирование должно быть выключено.','Go Back to the VPN step and choose the defer option, or choose two different existing profiles.','Вернитесь к шагу VPN и выберите откладывание пары либо два разных существующих профиля.'],
 ['ONBOARDING-APPEARANCE','setup','Check appearance defaults','Проверьте оформление по умолчанию','The saved default language, theme or design is unsupported.','Выбран неподдерживаемый язык, тема или оформление по умолчанию.','Choose a value from each list in the first step.','Выберите значение в каждом списке на первом шаге.'],
 ['ONBOARDING-TELEGRAM-FIELDS','setup','Check optional Telegram setup','Проверьте необязательную настройку Telegram','The Telegram section does not match the supported form.','Раздел Telegram не соответствует поддерживаемой форме.','Keep existing settings, or enable the Telegram setup section and review its fields.','Оставьте существующие настройки либо включите раздел настройки Telegram и проверьте его поля.'],
 ['ONBOARDING-TOO-LARGE','setup','Setup request is too large','Запрос настройки слишком большой','The complete configuration exceeds the bounded save request size. Nothing was sent to the configuration writer.','Полная конфигурация превышает допустимый размер запроса сохранения. Запрос не передан записи настроек.','Shorten display names and channel groups, then review again.','Сократите названия серверов и групп каналов и проверьте снова.'],
 ['ONBOARDING-SAVE-UNCONFIRMED','setup','Setup save not confirmed','Сохранение настройки не подтверждено','The router did not confirm the complete setup save. The page keeps your draft; the router may already have committed the settings.','Роутер не подтвердил общее сохранение. Страница сохраняет черновик; параметры уже могли записаться на роутере.','Reload to read the router state before trying again.','Обновите страницу, чтобы прочитать состояние роутера перед повтором.'],
 ['CONTROL-REVISION-STALE','switch','Auto controls changed','Управление Auto изменилось','The Start request belongs to older Auto controls and was refused.','Запрос запуска относится к прежнему состоянию управления Auto и отклонён.','Refresh the current state before starting again.','Обновите данные перед новым запуском.'],
 ['START-STATE-UNVERIFIED','switch','Saved Auto state unverified','Состояние Auto не проверено','Saved Auto state could not be verified. Starting is blocked.','Не удалось проверить сохранённое состояние Auto. Запуск заблокирован.','Stop Auto, review the settings, then try again.','Остановите Auto, проверьте настройки и повторите попытку.'],
 ['STOP-SUPERSEDED-START','switch','Pending Start cancelled','Ожидающий запуск отменён','Stop cancelled this pending Start.','Остановка отменила ожидающий запуск.','Press Start again when ready.','При необходимости нажмите «Запустить» снова.'],
 ['START-CONFIG-CHANGED','switch','Settings changed during Start','Настройки изменились при запуске','The settings changed while Start was checking them. The request was refused.','Настройки изменились во время проверки запуска. Запрос отклонён.','Review the settings and try Start again.','Проверьте настройки и повторите запуск.'],
 ['GUARD-RELEASE-ARM-FAILED','switch','Safety timer unavailable','Аварийный таймер недоступен','The independent cleanup timer could not start. No new traffic block was installed.','Независимый таймер очистки не запустился. Новая блокировка трафика не установлена.','Check router resources and retry later.','Проверьте ресурсы роутера и повторите позже.'],
 ['GUARD-RELEASE-UNCONFIRMED','switch','Safety block removal unconfirmed','Снятие блокировки не подтверждено','Removal of the traffic block is unverified; recovery remains pending.','Снятие блокировки трафика не подтверждено; восстановление ещё не завершено.','See Help → emergency return; do not assume Stop completed.','См. «Помощь» → аварийный возврат; остановка ещё не подтверждена.'],
 ['RELEASE-PENDING','state','Waiting for block removal','Ожидается снятие блокировки','No new switching is allowed while the old block is being removed.','Новые переключения запрещены, пока снимается прежняя блокировка.','Check cleanup; use emergency recovery if it persists.','Проверьте очистку; при повторении используйте аварийное восстановление.'],
 ['RETURN-TRANSACTION-MISMATCH','switch','Old return request rejected','Старый запрос возврата отклонён','The request belongs to another transaction. Nothing changed.','Запрос относится к другой транзакции. Ничего не изменено.','Refresh and request return again if needed.','Обновите страницу и при необходимости запросите возврат ещё раз.'],
 ['RETURN-REQUEST-EXPIRED','switch','Return request expired','Запрос возврата устарел','The request is outside the transaction or its one-minute validity window.','Запрос находится вне транзакции или минутного срока действия.','Refresh and request return again.','Обновите страницу и запросите возврат ещё раз.'],
 ['JOURNAL-PHASE-INVALID','switch','Invalid recovery phase','Неверная фаза восстановления','The journal phase is missing or unknown. Auto refuses to proceed.','Фаза журнала отсутствует или неизвестна. Auto не продолжает работу.','Use Help → emergency return; inspect recovery before restarting.','Используйте «Помощь» → аварийный возврат; проверьте восстановление до перезапуска.'],
 ['OBSERVING','state','Watching the primary','Слежу за основным','Auto is on and watches the primary VPN. Nothing is switched now.','Auto включён и следит за основным VPN. Сейчас ничего не переключается.','Nothing to do.','Делать ничего не нужно.','If the line says OBSERVING and the Auto lamp is green, everything is normal.','Если в строке OBSERVING и лампа Auto зелёная — всё в порядке.'],
 ['ARMED','state','Ready to switch','Готов к переключению','The controller has prepared a switch (saved the old order and started its safety timer) but has not changed anything yet.','Контроллер подготовил переключение (сохранил прежний порядок и запустил страхующий таймер), но пока ничего не менял.','Nothing to do; the next state follows within seconds.','Делать ничего не нужно; следующее состояние наступит через секунды.','In an incident: ARMED → APPLYING → WAIT-CLIENT → COMMITTED is a normal successful switch.','В инциденте: ARMED → APPLYING → WAIT-CLIENT → COMMITTED — обычное успешное переключение.'],
 ['APPLYING','state','Switching now','Идёт переключение','The controller is changing the order of the VPN rules on the router right now.','Контроллер прямо сейчас меняет порядок VPN-правил на роутере.','Wait. If it stays here for more than a minute, press Stop in the Auto card.','Подождите. Если состояние держится больше минуты, нажмите «Стоп» в блоке Auto.','You see APPLYING, then ROLLED-BACK with VENDOR-APPLY-FAILED: GL.iNet did not accept the change and the router went back.','Видите APPLYING, затем ROLLED-BACK с VENDOR-APPLY-FAILED: GL.iNet не принял изменение, роутер вернулся назад.'],
 ["WAIT-CLIENT", "state", "Waiting for your computer", "Ждём ваш компьютер", "The route is switched and the controller waits up to 2 minutes for the LAN helper on your computer to confirm that the internet works.", "Маршрут переключён, контроллер до 2 минут ждёт, пока LAN-помощник на вашем компьютере подтвердит, что интернет работает.", "Wait for the evidence required by this proof mode. External LAN uses its helper; router-probed mode has internal checks. On timeout verify the actual recovery, not merely the request.", "Ожидайте данные своего режима доказательства. Внешний LAN использует помощник, router-probed — внутренние проверки. При таймауте проверьте фактическое восстановление, а не только запрос.", "WAIT-CLIENT followed by ROLLED-BACK and CLIENT-CONFIRMATION-TIMEOUT: nobody confirmed in time.", "За WAIT-CLIENT следует ROLLED-BACK и CLIENT-CONFIRMATION-TIMEOUT: вовремя никто не подтвердил."],
 ['COMMITTED','state','Reserve confirmed','Резерв подтверждён','The switch worked and your computer confirmed it: traffic goes through the reserve VPN.','Переключение удалось и ваш компьютер его подтвердил: трафик идёт через резервный VPN.','Nothing to do. Auto returns to the primary by itself when it has recovered, or press “Return to primary”.','Делать ничего не нужно. Auto вернётся на основной сам, когда он восстановится, либо нажмите «Вернуться на основной».','The overview says “Working on the reserve” and the state is COMMITTED: normal after a failure of the primary.','На «Обзоре» «Работаю на резерве», состояние COMMITTED — норма после отказа основного.'],
 ['ROLLED-BACK','state','Returned to the previous route','Возврат на прежний маршрут','The controller put the VPN rules back to the original order. The reason is in the next column or in the code beside it.','Контроллер вернул VPN-правила в исходный порядок. Причина указана рядом.','Read the reason code beside it; it tells why the switch did not stay.','Прочитайте код причины рядом: он говорит, почему переключение не осталось.','ROLLED-BACK + TRIAL-ENDED: the test window ended and the router returned to the primary. That is normal.','ROLLED-BACK + TRIAL-ENDED: окно теста закончилось и роутер вернулся на основной. Это норма.'],
 ['ROLLING-BACK','state','Returning now','Возвращаюсь','The controller is putting the original order back right now.','Контроллер прямо сейчас возвращает исходный порядок.','Wait a minute.','Подождите минуту.'],
 ['RESTORING','state','Restoring the route','Восстанавливаю маршрут','Same as returning: the original route is being restored and verified.','То же, что возврат: исходный маршрут восстанавливается и проверяется.','Wait a minute; if it does not end, see Help → “No internet”.','Подождите минуту; если не заканчивается, см. «Помощь» → «Нет интернета».'],
 ["TRIAL-REQUIRED", "state", "LAN trial needed", "Нужен LAN-тест", "Auto may not switch yet: no LAN trial has passed for the current settings.", "Auto пока не может переключать: для текущих настроек не пройден LAN-тест.", "For the client-confirmed path run its separately authorized matching trial. Prepared continuous mode uses its own readiness; do not forge or reuse another pair certificate.", "Для клиентского пути выполните его отдельно разрешённый соответствующий тест. Подготовленный непрерывный режим использует свою готовность; не подделывайте и не переносите сертификат другой пары.", "After you change the primary or reserve, this state appears again: the old trial belongs to the old pair.", "После смены основного или резервного это состояние появляется снова: прежний тест относился к прежней паре."],
 ['BLOCKED','state','Blocked','Заблокировано','The controller refuses to act because a safety condition is not met; the conditions are listed next to it as codes.','Контроллер отказывается действовать, потому что не выполнено условие безопасности; условия перечислены рядом кодами.','Open each code beside it and fix the listed condition.','Откройте каждый код рядом и устраните перечисленное условие.','BLOCKED with HARDWARE-ACCELERATOR-UNVERIFIED: GL.iNet hardware acceleration is not proven off.','BLOCKED с HARDWARE-ACCELERATOR-UNVERIFIED: аппаратное ускорение GL.iNet не подтверждено как выключенное.'],
 ['STOPPED','state','Stopped','Остановлен','Auto is off and the controller does nothing.','Auto выключен, контроллер ничего не делает.','Turn Auto on when you want it.','Включите Auto, когда нужно.'],
 ['STOPPED-ON-RESERVE','state','Stopped on the reserve','Остановлен на резерве','Auto was stopped while traffic was on the reserve. The original route is not restored yet.','Auto остановлен, пока трафик шёл через резерв. Исходный маршрут пока не восстановлен.','When the primary works again press “Return to primary” in the Auto card.','Когда основной снова работает, нажмите «Вернуться на основной» в блоке Auto.'],
 ['DEGRADED-ON-RESERVE','state','Reserve is failing too','Резерв тоже не работает','Traffic is on the reserve and the reserve fails its checks as well.','Трафик идёт через резерв, и резерв тоже не проходит проверки.','Check both VPN profiles in GL.iNet. Auto returns to the primary when it passes its check.','Проверьте оба VPN-профиля в GL.iNet. Auto вернётся на основной, когда он пройдёт проверку.'],
 ['HELD-ON-RESERVE','state','Staying on the reserve; Auto keeps watching','Остаюсь на резерве; Auto продолжает наблюдать','Traffic stays on the reserve on purpose (your return rule or your manual choice) while the reserve works. Auto is still on: if the reserve fails, it moves traffic to the other channel by itself.','Трафик намеренно остаётся на резерве (по вашему правилу возврата или ручному выбору), пока резерв работает. Auto остаётся включённым: если резерв откажет, он сам переведёт трафик на другой канал.','Nothing to do. If you want traffic back on the primary, press “Return to primary”.','Делать ничего не нужно. Если хотите вернуть трафик на основной, нажмите «Вернуться на основной».'],
 ['DISABLED','state','Auto disabled','Auto выключен','Auto is switched off in the settings.','Auto выключен в настройках.','Nothing to do.','Делать ничего не нужно.'],
 ["EXPIRED", "state", "Test window ended", "Окно теста закончилось", "The time window of the current trial is over; Auto does not act outside it.", "Окно времени текущего теста закончилось; вне его Auto не действует.", "The bounded window ended. Verify Stop/recovery first; any new run requires current readiness and the requested mode, not a reset of old deadlines or budgets.", "Ограниченное окно завершилось. Сначала проверьте Stop/восстановление; новому запуску нужны текущая готовность и выбранный режим, а не сброс старых сроков/бюджетов."],
 ['SERVICE-STOPPED','state','Monitor service is not running','Служба мониторинга не работает','The page cannot find a running monitor on the router.','Страница не находит работающий мониторинг на роутере.','Press “Start monitoring” in the Monitoring block, or run homensai-vpn-emergency start over SSH.','Нажмите «Запустить мониторинг» в блоке «Мониторинг» или выполните homensai-vpn-emergency start по SSH.'],
 ['WAIT-CONFIRM','state','Waiting for confirmation','Ожидание подтверждения','Waiting for the computer to confirm the new route.','Ожидается подтверждение нового маршрута с компьютера.','See WAIT-CLIENT.','См. WAIT-CLIENT.'],
 ['CLIENT-CONFIRMED','switch','Your computer confirmed','Компьютер подтвердил','The LAN helper on your computer confirmed that DNS, HTTPS and the exit address are right after the switch.','LAN-помощник на вашем компьютере подтвердил, что DNS, HTTPS и внешний адрес после переключения верны.','Nothing to do.','Делать ничего не нужно.'],
 ['TRIAL-PASSED','switch','Trial passed','Тест пройден','The LAN trial worked: the switch was confirmed and the router returned to the primary.','LAN-тест удался: переключение подтверждено и роутер вернулся на основной.','Now you can turn Auto on.','Теперь можно включить Auto.'],
 ['TRIAL-ENDED','switch','Test window ended','Окно теста закончилось','The time window of the trial ended and the router returned to the primary.','Окно времени теста закончилось, роутер вернулся на основной.','Nothing to do.','Делать ничего не нужно.'],
 ['SOURCE-FAILED','switch','The primary failed','Основной отказал','The primary VPN failed the configured number of checks in a row.','Основной VPN не прошёл заданное число проверок подряд.','Check the primary VPN profile in GL.iNet.','Проверьте профиль основного VPN в GL.iNet.'],
 ['SOURCE-HEALTH-UNKNOWN','switch','Primary state unknown','Состояние основного неизвестно','There was not enough fresh data about the primary.','Не хватило свежих данных об основном.','Wait for the next checks; check the monitor lamp.','Дождитесь следующих проверок; посмотрите на лампу мониторинга.'],
 ['OPERATOR-TRIAL','switch','Started by you','Запущено вами','The switch was a trial that you started with the LAN helper.','Переключение было тестом, который вы запустили LAN-помощником.','Nothing to do.','Делать ничего не нужно.'],
 ['OPERATOR-HOLD-RESERVE','switch','Held by your rule','Удержание по вашему правилу','Your recovery rule says to stay on the reserve until you return manually.','Ваше правило восстановления говорит оставаться на резерве, пока вы не вернётесь вручную.','Press “Return to primary” when you want to go back.','Нажмите «Вернуться на основной», когда захотите вернуться.'],
 ['PRIMARY-STABLY-RECOVERED','switch','Primary recovered for good','Основной стабильно восстановился','The primary passed enough checks in a row and traffic returned to it.','Основной прошёл достаточно проверок подряд, и трафик вернулся на него.','Nothing to do.','Делать ничего не нужно.'],
 ['RESERVE-FAILED','switch','The reserve failed','Резерв отказал','The reserve VPN failed its checks while traffic was on it.','Резервный VPN не прошёл проверки, пока трафик шёл через него.','Check both VPN profiles in GL.iNet.','Проверьте оба VPN-профиля в GL.iNet.'],
 ['RESERVE-FAILED-PRIMARY-VERIFIED','switch','Reserve failed, primary is fine','Резерв отказал, основной исправен','The reserve failed and the primary was verified, so traffic returned to the primary.','Резерв отказал, основной проверен, поэтому трафик вернулся на основной.','Nothing to do.','Делать ничего не нужно.'],
 ['RESERVE-HEALTH-UNKNOWN','switch','Reserve state unknown','Состояние резерва неизвестно','The live check of the reserve gave no clear answer.','Живая проверка резерва не дала ясного ответа.','Wait; check the reserve in Channels and servers.','Подождите; посмотрите резерв в «Каналах и серверах».'],
 ['SOURCE-NOT-VERIFIED','switch','Primary not verified','Основной не проверен','The router stays on the reserve because the primary has not passed a fresh check.','Роутер остаётся на резерве, потому что основной не прошёл свежую проверку.','Check the primary VPN; then press “Return to primary”.','Проверьте основной VPN; затем нажмите «Вернуться на основной».'],
 ['SUPERVISOR-RECOVERY','switch','Recovery after a restart','Восстановление после перезапуска','The controller restarted in the middle of a switch and put the route back.','Контроллер перезапустился посреди переключения и вернул маршрут.','Nothing to do unless it repeats.','Делать ничего не нужно, если не повторяется.'],
 ['TRANSACTION-FAILED','switch','The switch failed','Переключение не удалось','Something went wrong during the switch; the router returned to the previous route.','Что-то пошло не так во время переключения; роутер вернулся на прежний маршрут.','Look at the code beside it for the cause.','Посмотрите на код рядом: там причина.'],
 ['FAILED-BEFORE-APPLY','switch','Failed before any change','Сбой до изменений','The switch failed before anything was changed on the router.','Переключение не удалось до каких-либо изменений на роутере.','Nothing was changed; look at the code beside it.','Ничего не менялось; посмотрите на код рядом.'],
 ['TIMEOUT-ELAPSED','switch','Time ran out','Время вышло','The allowed time for the step ended.','Отведённое на шаг время закончилось.','Repeat later; if it repeats, check the monitor.','Повторите позже; если повторяется, проверьте мониторинг.'],
 ['SELECTED-BY-CONTROLLER','switch','Chosen by the controller','Выбран контроллером','This server carries your traffic now.','Этот сервер сейчас пропускает ваш трафик.','Nothing to do.','Делать ничего не нужно.'],
 ["EDGE-NOT-CERTIFIED", "switch", "Works, switch not certified", "Работает, переключение не подтверждено", "The server works and could take over, but switching to it is not certified on this router yet.", "Сервер работает и мог бы подхватить трафик, но переключение на него на этом роутере ещё не подтверждено.", "The proposed edge lacks evidence for its mode. A read-only candidate is not an applied route; use the matching controller/test workflow, not a generic forced LAN confirmation.", "Предлагаемому переходу не хватает доказательства своего режима. Кандидат чтения не является применённым маршрутом; используйте соответствующий контроллер/тест, не принудительное общее подтверждение LAN."],
 ['THREE-CONFIRMED-FAILURES','switch','Three failures in a row','Три сбоя подряд','The primary failed three checks in a row.','Основной не прошёл три проверки подряд.','Check the primary VPN.','Проверьте основной VPN.'],
 ['CONFIGURED-FAILURE-STREAK','switch','Failure streak reached','Достигнут порог сбоев','The primary failed as many checks in a row as your recovery rules require.','Основной не прошёл столько проверок подряд, сколько требуют ваши правила восстановления.','Check the primary VPN.','Проверьте основной VPN.'],
 ['RESTORE-PRIMARY','switch','Return to the primary','Возврат на основной','The controller decided to go back to the primary.','Контроллер решил вернуться на основной.','Nothing to do.','Делать ничего не нужно.'],
 ['SWITCH-RECOMMENDED','switch','A switch is recommended','Рекомендуется переключение','The forecast says a switch would be chosen now. The forecast changes nothing.','Прогноз говорит, что сейчас было бы выбрано переключение. Прогноз ничего не меняет.','Nothing to do.','Делать ничего не нужно.'],
 ['TARGET-INACTIVE','switch','Reserve not connected','Резерв не подключён','The reserve VPN is not connected in GL.iNet; Auto never connects it for you.','Резервный VPN не подключён в GL.iNet; Auto сам его не подключает.','Connect the reserve profile in the GL.iNet VPN Dashboard.','Подключите профиль резерва в VPN Dashboard GL.iNet.'],
 ['TARGET-NOT-READY','switch','Reserve not ready','Резерв не готов','The reserve has not passed enough checks in a row yet.','Резерв пока не прошёл достаточно проверок подряд.','Wait; check the reserve in Channels and servers.','Подождите; посмотрите резерв в «Каналах и серверах».'],
 ['PLAN-CONFIG','switch','Primary and reserve not chosen','Основной и резерв не выбраны','The forecast needs a primary and a different reserve.','Для прогноза нужны основной и другой, резервный VPN.','Settings → All application settings → 3 · Existing VPNs.','«Настройки → Все настройки приложения → 3 · Существующие VPN».'],
 ['UPLINK-DOWN','switch','Provider line is down','Линия провайдера не работает','The router sees the line from your provider down; switching VPNs cannot help.','Роутер видит, что линия от провайдера отключена; переключение VPN не поможет.','Check the cable and the provider.','Проверьте кабель и провайдера.'],
 ['STOPPED-NO-HEALTHY-PATH','switch','No healthy path','Нет исправного пути','No VPN passed its checks, so the controller stopped.','Ни один VPN не прошёл проверки, поэтому контроллер остановился.','Check the VPN profiles in GL.iNet.','Проверьте VPN-профили в GL.iNet.'],
 ['GUARD-RETAINED','switch','Safety block kept','Защитная блокировка сохранена','The program kept its safety block (only VPN traffic allowed) because the return was not verified.','Программа сохранила защитную блокировку (разрешён только трафик через VPN), потому что возврат не подтверждён.','See Help → emergency return.','См. «Помощь» → аварийный возврат.'],
 ["WATCHDOG-DID-NOT-ARM", "switch", "Safety timer did not start", "Страхующий таймер не запустился", "The helper process that guarantees the return did not start in time, so the switch was not made.", "Вспомогательный процесс, гарантирующий возврат, не запустился вовремя, поэтому переключение не выполнено.", "Do not apply another transition before the independent recovery worker is confirmed. Inspect its exact refusal; a service restart is deliberate and follows safe Stop/recovery.", "Не применяйте новый переход до подтверждения независимого восстановления. Изучите точный отказ; перезапуск службы — осознанное действие после безопасного Stop/восстановления."],
 ['TRANSACTION-EXPIRED','switch','The switch ran out of time','Переключение не уложилось по времени','The time allowed for this switch had already ended.','Время, отведённое на это переключение, уже закончилось.','Start again.','Начните заново.'],
 ['DNS-FAILED','monitor','Name lookup fails','Не работает поиск адресов','The VPN is connected but looking up a name through it fails.','VPN подключён, но поиск имени через него не работает.','See DNS-001.','См. DNS-001.'],
 ['HTTPS-FAILED','monitor','HTTPS checks below threshold','HTTPS-проверки ниже порога','The VPN did not pass enough HTTPS checks. This may be partial availability; read the saved count and DNS result.','VPN не прошёл достаточное число HTTPS-проверок. Возможна частичная доступность; смотрите сохранённое число ответов и результат DNS.','See VPN-003.','См. VPN-003.'],
 ["TUNNEL-DISCONNECTED", "monitor", "Tunnel not connected", "Туннель не подключён", "The VPN tunnel is not up.", "VPN-туннель не поднят.", "Inspect the configured binding and stock client state. Any deliberate profile restart/edit must respect current Auto ownership and completed recovery first.", "Проверьте назначенный профиль и штатный клиент. Осознанный перезапуск/правка должны учитывать владение Auto и сначала завершённое восстановление."],
 ['ROUTE-MISMATCH','monitor','Check did not go through the VPN','Проверка шла не через VPN','The router’s check did not travel through this VPN, so it proves nothing.','Проверка роутера шла не через этот VPN, поэтому ничего не доказывает.','See ROUTE-001.','См. ROUTE-001.'],
 ['PATH-UNVERIFIED','monitor','Check path unconfirmed','Путь проверки не подтверждён','The router has not yet confirmed which way its check went.','Роутер ещё не подтвердил, каким путём прошла проверка.','Wait for the next check.','Дождитесь следующей проверки.'],
 ['VPN-PROBE-HEALTHY','monitor','VPN works','VPN работает','DNS and HTTPS checks through this VPN passed.','Проверки DNS и HTTPS через этот VPN прошли.','Nothing to do.','Делать ничего не нужно.'],
 ['OBSERVATION-STALE','monitor','Measurements are old','Измерения устарели','The latest measurement is too old to decide anything.','Последнее измерение слишком старое, чтобы что-то решать.','Check that the monitor runs.','Проверьте, что мониторинг работает.'],
 ['OBSERVATION-UNKNOWN','monitor','Not enough measurements','Мало измерений','There are not enough measurements yet.','Измерений пока недостаточно.','Wait a few minutes.','Подождите несколько минут.'],
 ['LINK-UP','monitor','Link is up','Линия поднята','The uplink cable or line is up. It is not proof of internet.','Кабель или линия провайдера подняты. Это не доказательство интернета.','Nothing to do.','Делать ничего не нужно.'],
 ['CHECK-LIMIT','monitor','Check limit reached','Достигнут лимит проверок','To stay light the monitor checks only a limited number of VPNs per round; this one waits for its turn.','Чтобы не нагружать роутер, мониторинг проверяет за круг ограниченное число VPN; этот ждёт своей очереди.','Wait for the next round or raise the profile limit in Monitoring preferences.','Дождитесь следующего круга или увеличьте лимит профилей в «Параметрах мониторинга».'],
 ["FOREIGN-GUARD-TABLE", "switch", "Foreign table with our name", "Чужая таблица с нашим именем", "A firewall table with the name of the program’s guard exists but is not the program’s. The program never touches it.", "Существует таблица брандмауэра с именем защитного блока программы, но она не наша. Программа её не трогает.", "Keep the foreign table and inspect its owner read-only. The application must not delete it to bypass a refusal; unrelated firewall correction is a separate verified scope.", "Сохраните чужую таблицу и изучите владельца только чтением. Приложение не должно удалять её ради обхода отказа; исправление постороннего firewall — отдельный проверенный объём работ."],
 ['GUARD-CHECK-FAILED','switch','Safety block rejected','Защитная блокировка отклонена','The firewall refused the program’s safety block when it was tested; nothing was applied.','Брандмауэр отклонил защитную блокировку при проверке; ничего не применено.','Check that nft works on the router; Help → emergency return.','Проверьте, что nft работает на роутере; «Помощь» → аварийный возврат.'],
 ['GUARD-INSTALL-FAILED','switch','Safety block not installed','Защитная блокировка не установлена','The program could not install its safety block, so it did not switch.','Программа не смогла установить защитную блокировку, поэтому не переключала.','Check nft; repeat later.','Проверьте nft; повторите позже.'],
 ['GUARD-QUERY-FAILED','switch','Safety block cannot be read','Защитная блокировка не читается','The program could not read the state of its own safety block.','Программа не смогла прочитать состояние своей защитной блокировки.','Check nft; see Help → emergency return.','Проверьте nft; см. «Помощь» → аварийный возврат.'],
 ["POLICY-DUPLICATE-IDENTITY", "switch", "Two identical VPN rules", "Два одинаковых VPN-правила", "Two rules of the router look identical, so they cannot be told apart safely.", "Два правила роутера выглядят одинаково, поэтому надёжно их различить нельзя.", "Identify duplicate ownership and preserve the original policy. Resolve the specific stock configuration after managed Stop; never mass-delete rules to obtain a green status.", "Установите владельца дублей и сохраните исходную политику. Исправьте конкретную штатную конфигурацию после управляемого Stop; не удаляйте правила массово ради зелёного статуса."],
 ['POLICY-GENERATION-CHANGED','switch','Rules changed meanwhile','Правила изменились','The router’s VPN rules changed after the switch was prepared, so it was cancelled.','Правила VPN на роутере изменились после подготовки переключения, поэтому оно отменено.','Do not edit the VPN rules while Auto works.','Не меняйте VPN-правила, пока Auto работает.'],
 ['POLICY-IDENTITY-CHANGED','switch','Rule identity changed','Правило изменилось','A rule that was part of the switch changed or disappeared.','Правило, участвовавшее в переключении, изменилось или исчезло.','Do not edit the VPN rules while Auto works.','Не меняйте VPN-правила, пока Auto работает.'],
 ['POLICY-REORDER-UNVERIFIED','switch','New order not confirmed','Новый порядок не подтверждён','After reordering, the rules were not in the expected order; the router went back.','После перестановки правила оказались не в ожидаемом порядке; роутер вернулся назад.','Repeat later.','Повторите позже.'],
 ['SOURCE-ORDER-MISMATCH','switch','Rule order is not as expected','Порядок правил не тот','The primary and reserve rules are not in the order the program expects.','Правила основного и резервного стоят не в том порядке, который ожидает программа.','Settings → Setup → check the primary and reserve.','«Настройки» → «Настройка» → проверьте основной и резерв.'],
 ['EXIT-CHANGED','switch','The exit address changed','Внешний адрес изменился','The address the internet sees changed between two checks of the same VPN.','Адрес, который видит интернет, изменился между двумя проверками одного VPN.','Repeat the trial; a provider that rotates addresses can cause this.','Повторите тест; такое бывает у провайдера с ротацией адресов.'],
 ['EXIT-IP-NOT-GLOBAL','switch','Exit address is private','Внешний адрес не публичный','The exit address answered by the check is a private one, so the check proves nothing.','Адрес, ответивший на проверку, частный, поэтому проверка ничего не доказывает.','Check that the VPN really reaches the internet.','Проверьте, что VPN действительно выходит в интернет.'],
 ['JOURNAL-ORDER-INVALID','switch','Journal order invalid','Порядок в журнале неверен','The saved order in the switch journal is inconsistent.','Сохранённый порядок в журнале переключения противоречив.','Archive the journal with homensai-vpn-emergency close-journal after checking the rules.','Заархивируйте журнал командой homensai-vpn-emergency close-journal, проверив правила.'],
 ['JOURNAL-SECTION-INVALID','switch','Journal names an invalid rule','Журнал называет неверное правило','The journal names a rule that is not valid.','Журнал называет правило, которое недопустимо.','Same as JOURNAL-ORDER-INVALID.','То же, что JOURNAL-ORDER-INVALID.'],
 ["DEADLINE-TIMEZONE-REQUIRED", "switch", "Deadline needs a time zone", "Для срока нужен часовой пояс", "The deadline of the test window was written without a time zone.", "Срок окна теста записан без часового пояса.", "Supply the intended bounded deadline with an explicit timezone for that mode. Verify actual time; do not reinterpret an expired window by changing the clock.", "Задайте ограниченный срок с явным часовым поясом для своего режима. Проверьте фактическое время; не переопределяйте истёкшее окно переводом часов."],
 ['INVALID-ACCELERATION-REQUEST','switch','Invalid request','Неверный запрос','The request to prepare the router had a wrong form.','Запрос на подготовку роутера имел неверный вид.','Use the page button, not a manual command.','Используйте кнопку на странице, а не ручную команду.'],
 ["ACCELERATION-PREPARE-ATTEMPT-LIMIT", "switch", "Too many preparation attempts", "Слишком много попыток подготовки", "The preparation of the router (hardware acceleration off) failed three times.", "Подготовка роутера (отключение аппаратного ускорения) не удалась трижды.", "Retain failed preparation evidence and inspect actual runtime/vendor support. A separate approved correction needs undo; never force-unload drivers or reset attempt metadata to retry.", "Сохраните отказы подготовки и проверьте фактическую поддержку/runtime. Отдельной коррекции нужна отмена; не выгружайте драйверы принудительно и не сбрасывайте попытки ради повтора."],
 ['ACCELERATION-PREPARE-DURING-TRANSACTION','switch','Preparation during a switch','Подготовка во время переключения','The router preparation was requested while a switch was running; refused.','Подготовка роутера запрошена во время переключения; отказано.','Wait until the switch ends.','Дождитесь окончания переключения.'],
 ["HNAT-DISABLE-UNVERIFIED", "switch", "Hardware acceleration not confirmed off", "Аппаратное ускорение не подтверждено как выключенное", "After the attempt, the hardware acceleration (HNAT) is still not proven off.", "После попытки аппаратное ускорение (HNAT) всё ещё не подтверждено как выключенное.", "A saved checkbox is insufficient. Read the preparation/runtime evidence for this firmware and plan only the applicable reversible correction; do not force module removal.", "Одной сохранённой галочки недостаточно. Изучите подготовку/runtime этой прошивки и только применимое обратимое исправление; не удаляйте модули принудительно."],
 ["SFE-DISABLE-UNVERIFIED", "switch", "Software acceleration not confirmed off", "Программное ускорение не подтверждено как выключенное", "The software acceleration module is still loaded.", "Модуль программного ускорения всё ещё загружен.", "Check the exact loaded modules, saved boot ownership and preserved original files. Use reviewed preparation/undo rather than blindly forcing a toggle or unloading a driver.", "Проверьте точные модули, исходный запуск и сохранённые файлы. Используйте проверенную подготовку/отмену вместо слепого переключения или принудительной выгрузки драйвера."],
 ['UNEXPECTED-DEBUGFS-PATH','switch','Unexpected system path','Неожиданный системный путь','A system path that should be a normal folder is a link; the program refuses to use it.','Системный путь, который должен быть обычной папкой, оказался ссылкой; программа отказывается его использовать.','Contact support with the code; nothing was changed.','Обратитесь в поддержку с кодом; ничего не менялось.'],
 ['UNEXPECTED-HNAT-PATH','switch','Unexpected system path','Неожиданный системный путь','Same as UNEXPECTED-DEBUGFS-PATH for the acceleration switch file.','То же, что UNEXPECTED-DEBUGFS-PATH для файла переключателя ускорения.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['UNSAFE-FIREWALL-SECTION','switch','Unsafe firewall section name','Небезопасное имя секции брандмауэра','A firewall section has a name the program does not dare to touch.','У секции брандмауэра имя, которое программа не решается трогать.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['UNSAFE-GUARD-DEVICE','switch','Unsafe interface name','Небезопасное имя интерфейса','A network interface name has odd characters; the program refuses to put it into a firewall rule.','В имени сетевого интерфейса странные символы; программа отказывается вносить его в правило брандмауэра.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['UNSAFE-SECTION','switch','Unsafe rule name','Небезопасное имя правила','A VPN rule has a name the program refuses to use.','У VPN-правила имя, которое программа отказывается использовать.','Contact support with the code.','Обратитесь в поддержку с кодом.'],
 ['FAULT-ACTIVE','switch','Failure test is running','Тест сбоя выполняется','The deliberate traffic block of the failure test is on.','Преднамеренная блокировка трафика теста сбоя включена.','Wait for its end or press “Cancel fault now”.','Дождитесь окончания или нажмите «Отменить сбой сейчас».'],
 ['FAULT-ALREADY-ACTIVE','switch','Failure test already runs','Тест сбоя уже идёт','Only one failure test can run at a time.','Одновременно может идти только один тест сбоя.','Wait or cancel the running one.','Дождитесь или отмените идущий.'],
 ['FAULT-CANCELLED','switch','Failure test cancelled','Тест сбоя отменён','You cancelled the failure test and the block was removed.','Вы отменили тест сбоя, блокировка снята.','Nothing to do.','Делать ничего не нужно.'],
 ['FAULT-TRANSITION-CONFIRMED','switch','Transition test passed','Тест перехода пройден','The other channel has fresh successful checks and its route is confirmed. The artificial traffic block was removed.','На другом канале получены свежие успешные проверки и подтверждён маршрут. Искусственная блокировка снята.','Review the test history.','Результат смотрите в истории теста.'],
 ['FAULT-TRANSITION-NOT-CONFIRMED','switch','Transition not confirmed','Переход не подтверждён','The test time elapsed without a confirmed transition. The artificial traffic block was removed.','Время теста истекло без подтверждённого перехода. Искусственная блокировка снята.','Inspect Auto state and events, including thresholds, cooldown and channel health.','Проверьте состояние Auto и события: пороги проверок, паузу между переходами и исправность каналов.'],
 ['FAULT-CLEANED','switch','Failure test cleaned up','Тест сбоя убран','The failure test ended and its block was removed.','Тест сбоя закончился, его блокировка снята.','Nothing to do.','Делать ничего не нужно.'],
 ['FAULT-NOT-ACTIVE','switch','No failure test is running','Тест сбоя не идёт','There is nothing to cancel.','Отменять нечего.','Nothing to do.','Делать ничего не нужно.'],
 ['FAULT-CERTIFIED-AUTO-REQUIRED','switch','Transition test needs running Auto','Для теста перехода нужен работающий Auto','The test needs fresh confirmation of the current channel and a healthy alternative. Prepared continuous pair Auto uses its own private state; the legacy bounded mode still needs its LAN certificate.','Тесту нужны свежие подтверждения текущего канала и исправного второго. Подготовленный непрерывный Auto использует собственное закрытое состояние; прежнему ограниченному режиму по-прежнему нужен LAN-сертификат.','Check both VPN channels and start Auto on Overview. Reopen the transition test after fresh observations arrive.','Проверьте оба VPN и включите Auto на «Обзоре». Вернитесь к тесту перехода после свежих наблюдений.'],
 ['FAULT-NATIVE-PREREQUISITES','switch','Router checks not passed','Проверки роутера не пройдены','Some of the router checks listed on the Overview are not passed.','Часть проверок роутера, перечисленных на «Обзоре», не пройдена.','Fix the listed items (Overview → Before you can start Auto).','Исправьте перечисленное («Обзор» → «Что нужно перед запуском Auto»).'],
 ['FAULT-SESSION-CONSENT-REQUIRED','switch','Reconnection not allowed','Переподключение не разрешено','You have not allowed a short reconnection of calls and sessions.','Вы не разрешили короткое переподключение звонков и сессий.','Settings → All application settings → 3 · Existing VPNs: tick the permission.','«Настройки → Все настройки приложения → 3 · Существующие VPN»: поставьте разрешение.'],
 ["FAULT-WINDOW-TOO-SHORT", "switch", "Test window too short", "Окно теста слишком короткое", "The remaining time of the trial window is shorter than the failure test plus its return.", "Остаток окна теста короче, чем тест сбоя вместе с возвратом.", "In the bounded certified mode choose a duration fitting its current window, or prepare a separately authorized new trial. Continuous pair mode has its own guards; do not reset a lease to evade them.", "В ограниченном сертифицированном режиме выберите длительность внутри текущего окна либо подготовьте отдельно разрешённый новый тест. У непрерывной пары собственные проверки; не сбрасывайте lease для их обхода."],
 ['FAULT-NOT-CURRENT-SOURCE','switch','Not the current primary','Это не текущий основной','The failure test can only break the VPN that is currently the primary.','Тест сбоя может ломать только VPN, который сейчас основной.','Choose the current primary.','Выберите текущий основной.'],
 ['FAULT-HEALTHY-RESERVE-REQUIRED','switch','Reserve must be healthy','Нужен исправный резерв','The test needs both the primary and the reserve to work right now.','Для теста нужно, чтобы и основной, и резерв сейчас работали.','Check both in Channels and servers.','Проверьте оба в «Каналах и серверах».'],
 ['FAULT-WOULD-REMOVE-RESERVE','switch','The test would also break the reserve','Тест сломал бы и резерв','The chosen scope (the whole channel group) contains the reserve too.','Выбранная область (вся группа канала) содержит и резерв.','Choose “Current primary server”.','Выберите «Текущий основной сервер».'],
 ['FAULT-PATH-UNVERIFIED','switch','Path of the VPN not confirmed','Путь VPN не подтверждён','The program could not confirm which network device belongs to the VPN, so it will not block anything.','Программа не смогла подтвердить, какое сетевое устройство принадлежит VPN, поэтому ничего не блокирует.','Wait for the next check and repeat.','Дождитесь следующей проверки и повторите.'],
 ['FAULT-WATCHDOG-NOT-READY','switch','Safety timer not ready','Страхующий таймер не готов','The helper that removes the block by itself did not start; the test was not started.','Помощник, который сам снимает блокировку, не запустился; тест не начат.','Repeat later.','Повторите позже.'],
 ['FAULT-UNSAFE-SCOPE','switch','Unsafe scope','Небезопасная область','The requested scope is not allowed.','Запрошенная область недопустима.','Use the page controls.','Пользуйтесь элементами страницы.'],
 ['FAULT-FOREIGN-TABLE','switch','Foreign firewall table','Чужая таблица брандмауэра','A firewall table with the test’s name exists but is not the program’s.','Существует таблица брандмауэра с именем теста, но она не наша.','Check nft over SSH.','Проверьте nft по SSH.'],
 ['FAULT-TIMEOUT-RULE-FAILED','switch','Automatic end could not be set','Автоматическое окончание не задано','The firewall could not set the timer that removes the block by itself; nothing was blocked.','Брандмауэр не смог задать таймер, который снимает блокировку сам; ничего не блокировалось.','Repeat later.','Повторите позже.'],
 ['FAULT-APPLY-UNCONFIRMED','switch','Block not confirmed','Блокировка не подтверждена','It is not confirmed that the test block was applied; it was removed to be safe.','Не подтверждено, что блокировка теста применена; для безопасности она снята.','Repeat later.','Повторите позже.'],
 ['FAULT-CLEANUP-UNCONFIRMED','switch','Removal not confirmed','Снятие не подтверждено','It is not confirmed that the test block was removed. It still ends by its own kernel timer.','Не подтверждено, что блокировка теста снята. Она всё равно закончится по таймеру ядра.','Wait up to 3 minutes; then check the internet; Help → emergency return.','Подождите до 3 минут; затем проверьте интернет; «Помощь» → аварийный возврат.'],
 ['FAULT-STATE-UNVERIFIED','switch','Test state unverified','Состояние теста не подтверждено','The saved state of the failure test cannot be trusted.','Сохранённому состоянию теста сбоя нельзя доверять.','Press “Cancel fault now”.','Нажмите «Отменить сбой сейчас».'],
 ['FAULT-HISTORY-CORRUPT','switch','Test history damaged','История тестов повреждена','The record of earlier failure tests cannot be read.','Запись прошлых тестов сбоя не читается.','Nothing to do; new tests still work.','Делать ничего не нужно; новые тесты работают.'],
 ['FAULT-WORKER-INVALID','switch','Helper process invalid','Вспомогательный процесс недействителен','The helper process of the test did not identify itself correctly.','Вспомогательный процесс теста неверно представился.','Cancel the test and repeat.','Отмените тест и повторите.'],
 ['FAULT-WORKER-STALE','switch','Helper process stale','Вспомогательный процесс устарел','The helper process of the test is old; the test was ended.','Вспомогательный процесс теста устарел; тест завершён.','Repeat.','Повторите.'],
 ['TELEGRAM-FORMAT-FAILED','telegram','Report could not be formed','Отчёт не сформирован','The program could not build the report text.','Программа не смогла собрать текст отчёта.','Repeat later; if it repeats, tell support.','Повторите позже; если повторяется, сообщите в поддержку.'],
 ['TELEGRAM-REPORT-UNAVAILABLE','telegram','Report data not available','Данные для отчёта недоступны','The monitor has no data for the report yet.','У мониторинга пока нет данных для отчёта.','Wait a few minutes after the monitor starts.','Подождите несколько минут после запуска мониторинга.'],
 ['TELEGRAM-REQUEST-REJECTED','telegram','Telegram rejected the request','Telegram отклонил запрос','Telegram answered that it will not take the message (wrong token, wrong chat or the bot is blocked).','Telegram ответил, что не принимает сообщение (неверный токен, неверный чат или бот заблокирован).','Check the token and the chat ID in the Telegram wizard; press Start in the bot.','Проверьте токен и Chat ID в мастере Telegram; нажмите Start в боте.','401 or “Unauthorized” → the token is wrong. 400 or “chat not found” → the chat ID is wrong or you did not press Start.','401 или «Unauthorized» → токен неверный. 400 или «chat not found» → неверный Chat ID либо вы не нажали Start.'],
 ['TELEGRAM-RETRY','telegram','Will retry','Повторю отправку','The message could not be sent now; the program tries again later.','Сообщение сейчас не отправилось; программа попробует позже.','Check that the router has internet.','Проверьте, что у роутера есть интернет.'],
 ['TELEGRAM-SCHEDULE','telegram','Invalid schedule','Неверное расписание','The report schedule has a wrong value.','В расписании отчётов неверное значение.','Open the Telegram wizard and choose the schedule again.','Откройте мастер Telegram и выберите расписание заново.'],
 ['TELEGRAM-SETUP-FIELDS','telegram','Wrong fields','Неверные поля','The Telegram form had unexpected fields.','В форме Telegram оказались неожиданные поля.','Reload the page and fill the wizard again.','Обновите страницу и заполните мастер заново.'],
 ['TELEGRAM-STATE-RECOVERED','telegram','Report state recovered','Состояние отчётов восстановлено','The saved report state was damaged and was rebuilt; one report may repeat or be skipped.','Сохранённое состояние отчётов было повреждено и восстановлено; один отчёт может повториться или пропуститься.','Nothing to do.','Делать ничего не нужно.'],
 ['TELEGRAM-STATE-WRITE-FAILED','telegram','Report state not saved','Состояние отчётов не сохранено','The program could not save the time of the last report; reports may repeat.','Программа не смогла сохранить время последнего отчёта; отчёты могут повторяться.','Check the free space (see “Storage”).','Проверьте свободное место (см. «Хранилище»).'],
 ['TELEGRAM-TEST-RATE-LIMIT','telegram','Test message too often','Тестовое сообщение слишком часто','A test message can be sent only once in a short time.','Тестовое сообщение можно отправлять не чаще, чем раз в короткое время.','Wait a minute.','Подождите минуту.'],
 ['SETUP-FIELDS','setup','Wrong fields in the form','Неверные поля формы','The setup form had unexpected fields.','В форме настройки оказались неожиданные поля.','Reload the page and use the wizard again.','Обновите страницу и снова пользуйтесь мастером.'],
 ['SETUP-KIND','setup','Unknown setup kind','Неизвестный вид настройки','The request named a setup that does not exist.','Запрос назвал несуществующую настройку.','Reload the page.','Обновите страницу.'],
 ['SETUP-NAME','setup','Invalid name','Неверное название','A name is empty, longer than 64 characters or has control characters.','Название пустое, длиннее 64 символов или содержит управляющие символы.','Use a short plain name.','Используйте короткое простое название.'],
 ['SETUP-SERVER','setup','Invalid server row','Неверная строка сервера','A server row of the form is incomplete.','Строка сервера в форме неполная.','Fill name, group, priority and the Monitor box.','Заполните название, группу, приоритет и галочку «Наблюдать».'],
 ['SETUP-DELTA-UNVERIFIED','setup','Unsaved changes unverifiable','Несохранённые изменения не проверить','The program could not check whether the router has other unsaved changes of its own settings.','Программа не смогла проверить, есть ли на роутере другие несохранённые изменения её настроек.','Reload the page and try again.','Обновите страницу и попробуйте снова.'],
 ['SETUP-CHECK-OK','setup','Settings writer works','Запись настроек работает','The installed writer passed its isolated self-check.','Установленная запись настроек прошла изолированную самопроверку.','Nothing to do.','Делать ничего не нужно.'],
 ['SETUP-CHECK-FAILED','setup','Settings writer self-check failed','Самопроверка записи настроек не прошла','Saving is blocked because the writer failed its self-check (often after an upgrade).','Сохранение заблокировано, потому что запись настроек не прошла самопроверку (часто после обновления).','Sign out of LuCI and in again, then reload with Ctrl+F5.','Выйдите из LuCI и войдите снова, затем обновите Ctrl+F5.'],
 ['TERMS-VERSION','setup','Terms version mismatch','Версия условий не совпадает','The page sent a different version of the terms than the router knows.','Страница прислала другую версию условий, чем знает роутер.','Reload with Ctrl+F5 and accept again.','Обновите Ctrl+F5 и примите условия заново.'],
 ['MONITOR-PREFERENCES-FIELDS','setup','Wrong fields','Неверные поля','The monitoring preferences form had unexpected fields.','В форме параметров мониторинга оказались неожиданные поля.','Reload the page.','Обновите страницу.'],
 ['PRIORITY-SAVED','setup','Priorities saved','Приоритеты сохранены','The new order of the servers was saved. No route changed.','Новый порядок серверов сохранён. Маршрут не менялся.','Nothing to do.','Делать ничего не нужно.'],
 ['PRIORITY-SAVE-FAILED','setup','Priorities not saved','Приоритеты не сохранены','The router refused the new order.','Роутер отказал в новом порядке.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-STALE-REVIEW','setup','The review is outdated','Просмотр устарел','The list changed after you reviewed it; nothing was saved.','Список изменился после вашего просмотра; ничего не сохранено.','Review the order again and save.','Просмотрите порядок заново и сохраните.'],
 ['PRIORITY-FIELDS','setup','Wrong fields','Неверные поля','The priorities form had unexpected fields.','В форме приоритетов оказались неожиданные поля.','Reload the page.','Обновите страницу.'],
 ['PRIORITY-INVALID-SELECTION','setup','Invalid selection','Неверный выбор','The chosen servers cannot be ordered this way.','Выбранные серверы нельзя упорядочить так.','Choose the eligible servers again.','Выберите подходящие серверы заново.'],
 ['PRIORITY-PROFILE-INELIGIBLE','setup','Server not eligible','Сервер не подходит','A chosen server is not connected or not monitored.','Выбранный сервер не подключён или не наблюдается.','Connect it or turn on “Monitor” for it.','Подключите его или включите ему «Наблюдать».'],
 ['RECOVERY-FIELDS','setup','Wrong fields','Неверные поля','The recovery rules form had unexpected fields.','В форме правил восстановления оказались неожиданные поля.','Reload the page.','Обновите страницу.'],
 ['RECOVERY-RANGE','setup','Value out of range','Значение вне диапазона','A number in the recovery rules is outside its allowed range.','Число в правилах восстановления вне допустимого диапазона.','Use the values the wizard offers.','Используйте значения, которые предлагает мастер.'],
 ['RECOVERY-REQUIRED','setup','Recovery rules required','Нужны правила восстановления','The recovery rules were never saved.','Правила восстановления ни разу не сохранялись.','Settings → Advanced settings → Recovery rules.','«Настройки» → «Расширенные» → «Правила восстановления».'],
 ['RECOVERY-RETURN-POLICY','setup','Invalid return rule','Неверное правило возврата','The return rule has an unknown value.','У правила возврата неизвестное значение.','Choose one of the offered rules.','Выберите одно из предложенных правил.'],
 ['CONFIG-STOP-AUTO-FIRST','setup','Stop Auto first','Сначала остановите Auto','This setting cannot change while Auto works.','Эту настройку нельзя менять, пока Auto работает.','Stop Auto on the Overview, wait for the return, then change it.','Остановите Auto на «Обзоре», дождитесь возврата, затем меняйте.'],
 ['CONFIG-RECOVERY-UNVERIFIED','setup','Configuration cannot be confirmed','Конфигурацию не подтвердить','The program could not confirm the configuration, so it refuses to change it.','Программа не смогла подтвердить конфигурацию, поэтому отказывается её менять.','Reload and try again.','Обновите и попробуйте снова.'],
 ['CONFIG-STORAGE-FREE','data','Not enough free space','Мало свободного места','The router has too little free space to save settings safely.','На роутере слишком мало места, чтобы безопасно сохранить настройки.','Free some space; see Help → Storage.','Освободите место; см. «Помощь» → «Хранилище».'],
 ['LIFECYCLE-STOP-AUTO-FIRST','service','Stop Auto first','Сначала остановите Auto','An upgrade or stop of the service needs Auto to be off and the original route restored.','Для обновления или остановки службы нужно, чтобы Auto был выключен и исходный маршрут восстановлен.','Press Stop in the Auto card and wait for the confirmation.','Нажмите «Стоп» в блоке Auto и дождитесь подтверждения.'],
 ['MONITOR-STOP-AUTO-FIRST','service','Stop Auto first','Сначала остановите Auto','Monitoring cannot be turned off while Auto works.','Мониторинг нельзя выключить, пока Auto работает.','Stop Auto first.','Сначала остановите Auto.'],
 ['MONITOR-JOURNAL-UNVERIFIED','service','Journal unverified','Журнал не проверен','The switch journal cannot be read, so monitoring is not turned off.','Журнал переключения не читается, поэтому мониторинг не выключается.','See JOURNAL-INTEGRITY-FAILED.','См. JOURNAL-INTEGRITY-FAILED.'],
 ['MONITOR-SERVICE-UNCONFIRMED','service','Service answer not confirmed','Ответ службы не подтверждён','The setting was saved but the service did not confirm that it started or stopped.','Настройка сохранена, но служба не подтвердила запуск или остановку.','Reload the page and look at the Monitoring lamp.','Обновите страницу и посмотрите на лампу мониторинга.'],
 ['STORAGE-001','data','Router storage problem','Проблема с хранилищем роутера','The program could not save its data (no space or the storage is read-only).','Программа не смогла сохранить свои данные (нет места или хранилище только для чтения).','Free space on the router; see Help → Storage.','Освободите место на роутере; см. «Помощь» → «Хранилище».'],
 ['STORAGE-RECOVERED','data','Storage recovered','Хранилище восстановлено','The damaged data was restored from the last good copy.','Повреждённые данные восстановлены из последней исправной копии.','Nothing to do; the newest minutes may be missing.','Делать ничего не нужно; последние минуты могут отсутствовать.'],
 ['SCAN-MEASUREMENT-FAILED','speed','Check request failed','Запрос проверки не удался','The “Check the VPNs now” request got no measurement.','Запрос «Проверить VPN сейчас» не получил измерения.','Check the Monitoring lamp and repeat.','Посмотрите на лампу мониторинга и повторите.'],
 ['SCAN-SNAPSHOT-MISMATCH','speed','Measurement does not match','Измерение не совпало','The measurement does not belong to this request.','Измерение не относится к этому запросу.','Press the check button again.','Нажмите кнопку проверки ещё раз.'],
 ['SCAN-STORAGE','speed','Request not saved','Запрос не сохранён','The router could not save the check request.','Роутер не смог сохранить запрос проверки.','Free space; repeat.','Освободите место; повторите.'],
 ['RPC-DUPLICATE-FIELD','service','Duplicate field in a request','Повтор поля в запросе','A request to the router named the same field twice; it was refused.','Запрос к роутеру дважды назвал одно поле; он отклонён.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-INPUT-COMPLEXITY','service','Request too complex','Запрос слишком сложный','The request was too big or too deeply nested.','Запрос был слишком большим или слишком вложенным.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-INPUT-DEPTH','service','Request too deep','Запрос слишком вложенный','The request nests too deeply.','Запрос вложен слишком глубоко.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-INPUT-OBJECT','service','Request has a wrong form','Запрос неверного вида','The request was not in the expected form.','Запрос был не в ожидаемом виде.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['RPC-NONFINITE-NUMBER','service','Invalid number','Неверное число','The request contained a number that is not valid.','Запрос содержал недопустимое число.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['OFFLINE-FIXTURE','data','Test data of the offline preview','Тестовые данные офлайн-просмотра','This code exists only in the offline preview used for development. It never appears on a real router.','Этот код есть только в офлайн-просмотре для разработки. На настоящем роутере его не бывает.','Nothing to do.','Делать ничего не нужно.'],
 ['AUTO-STOP-QUEUED','switch','Stop was queued','Остановка поставлена в очередь','The router accepted the Stop request.','Роутер принял запрос остановки.','Wait for the lamp to change.','Дождитесь, пока лампа изменится.'],
 ['RETURN-REFUSED','switch','Return refused','Возврат отклонён','The router refused the “Return to primary” request (usually because the primary is not healthy yet).','Роутер отклонил запрос «Вернуться на основной» (обычно потому, что основной ещё не исправен).','Check the primary in Channels and servers and press again.','Проверьте основной в «Каналах и серверах» и нажмите снова.'],
 ['RECOVERY-SAVED','setup','Recovery rules saved','Правила восстановления сохранены','Saved.','Сохранено.','Nothing to do.','Делать ничего не нужно.'],
 ['RECOVERY-SAVE-FAILED','setup','Recovery rules not saved','Правила восстановления не сохранены','The router refused to save them.','Роутер отказал в сохранении.','Reload and try again.','Обновите и попробуйте снова.'],
 ['RECOVERY-SAVE-UNCONFIRMED','setup','Save not confirmed','Сохранение не подтверждено','The router did not answer the save in time; it may or may not be saved.','Роутер не ответил на сохранение вовремя; оно могло записаться, а могло и нет.','Reload the page and look at the setting.','Обновите страницу и посмотрите настройку.'],
 ['SPEED-CONFIG-SAVED','speed','Speed settings saved','Настройки скорости сохранены','Saved.','Сохранено.','Nothing to do.','Делать ничего не нужно.'],
 ['SPEED-CONFIG-FAILED','speed','Speed settings not saved','Настройки скорости не сохранены','The router refused to save them.','Роутер отказал в сохранении.','Reload and try again.','Обновите и попробуйте снова.'],
 ['SPEED-QUEUED','speed','Speed test queued','Тест скорости поставлен в очередь','The router accepted the speed test; it starts within seconds.','Роутер принял тест скорости; он начнётся через секунды.','Wait for the result in the table.','Дождитесь результата в таблице.'],
 ['SPEED-START-FAILED','speed','Speed test did not start','Тест скорости не запустился','The router did not accept the speed test.','Роутер не принял тест скорости.','Look at the code beside it for the reason.','Посмотрите на код рядом: там причина.'],
 ['SPEED-CANCEL-QUEUED','speed','Cancel queued','Отмена поставлена в очередь','The router accepted the request to cancel the speed test.','Роутер принял запрос отменить тест скорости.','Nothing to do.','Делать ничего не нужно.'],
 ['SCAN-ACK-UNCONFIRMED','speed','Check request not confirmed','Запрос проверки не подтверждён','The router did not clearly confirm the check request.','Роутер не подтвердил запрос проверки ясно.','Make sure the monitor runs and press again.','Убедитесь, что мониторинг работает, и нажмите снова.'],
 ['SCAN-SNAPSHOT-UNCONFIRMED','speed','Result not confirmed','Результат не подтверждён','The measurement after the request could not be confirmed.','Измерение после запроса не удалось подтвердить.','Press the check button again.','Нажмите кнопку проверки ещё раз.'],
 ['MONITOR-PREFERENCES-SAVED','setup','Monitoring preferences saved','Параметры мониторинга сохранены','Saved.','Сохранено.','Nothing to do.','Делать ничего не нужно.'],
 ['MONITOR-PREFERENCES-FAILED','setup','Monitoring preferences not saved','Параметры мониторинга не сохранены','The router refused to save them.','Роутер отказал в сохранении.','Reload and try again.','Обновите и попробуйте снова.'],
 ['MONITOR-PREFERENCES-UNCONFIRMED','setup','Save not confirmed','Сохранение не подтверждено','The router did not answer the save in time.','Роутер не ответил на сохранение вовремя.','Reload the page and look at the setting.','Обновите страницу и посмотрите настройку.'],
 ['MONITOR-UNKNOWN','service','Monitor answer unknown','Ответ мониторинга неизвестен','The monitor service answered without a clear code.','Служба мониторинга ответила без ясного кода.','Reload and look at the Monitoring lamp.','Обновите и посмотрите на лампу мониторинга.'],
 ['PRIORITY-PREVIEW-FAILED','setup','Preview failed','Просмотр не удался','The router could not prepare the preview of the new order.','Роутер не смог подготовить просмотр нового порядка.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-PREVIEW-UNCONFIRMED','setup','Preview not confirmed','Просмотр не подтверждён','No clear answer to the preview request.','Нет ясного ответа на запрос просмотра.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-RPC-UNCONFIRMED','setup','Answer not confirmed','Ответ не подтверждён','No clear answer from the router.','Нет ясного ответа от роутера.','Reload and try again.','Обновите и попробуйте снова.'],
 ['PRIORITY-SELECT-ELIGIBLE-SERVERS','setup','Choose servers first','Сначала выберите серверы','Choose at least the servers that can be ordered.','Выберите хотя бы серверы, которые можно упорядочить.','Tick the servers you want to order.','Отметьте серверы, которые нужно упорядочить.'],
 ['PRIORITY-UNKNOWN','setup','Priority answer unknown','Ответ по приоритетам неизвестен','The router answered without a clear code.','Роутер ответил без ясного кода.','Reload and try again.','Обновите и попробуйте снова.'],
 ['RECOVERY-PERIOD','setup','Invalid period','Неверный период','A period in the recovery rules is not valid.','Период в правилах восстановления недопустим.','Use the values the wizard offers.','Используйте значения мастера.'],
 ['RPC-INVENTORY-INVALID','service','Router list unreadable','Список роутера нечитаем','The list of VPN profiles from the router had an unexpected form.','Список VPN-профилей от роутера имел неожиданный вид.','Reload with Ctrl+F5; if it stays, sign out of LuCI and in again.','Обновите Ctrl+F5; если не помогло, выйдите из LuCI и войдите снова.'],
 ['RPC-INVENTORY-UNAVAILABLE','service','Router list unavailable','Список роутера недоступен','The page could not get the list of VPN profiles; settings are not shown and nothing is saved.','Страница не получила список VPN-профилей; настройки не показываются и ничего не сохраняется.','Wait a minute and reload; check that you are signed in to LuCI.','Подождите минуту и обновите; проверьте, что вы вошли в LuCI.'],
 ['TELEGRAM-FORGET-UNCONFIRMED','telegram','Token removal not confirmed','Удаление токена не подтверждено','The router did not confirm that the stored bot token was deleted.','Роутер не подтвердил, что сохранённый токен бота удалён.','Reload and check the Telegram status.','Обновите и проверьте состояние Telegram.'],
 ['TERMS-SAVE-FAILED','setup','Terms not saved','Условия не сохранены','The acceptance of the terms could not be saved.','Принятие условий не удалось сохранить.','Reload and accept again.','Обновите и примите снова.'],
 ['TERMS-SAVE-UNCONFIRMED','setup','Acceptance not confirmed','Принятие не подтверждено','The router did not confirm the acceptance in time.','Роутер не подтвердил принятие вовремя.','Reload and check.','Обновите и проверьте.'],
 ['CAUSE-UNKNOWN','data','Cause not known','Причина неизвестна','The program saw a failure but has no evidence for its cause. It never guesses.','Программа увидела сбой, но у неё нет доказательств причины. Она не гадает.','Look at the other codes beside it.','Посмотрите на другие коды рядом.'],
 ['UNKNOWN-FUTURE-TIMESTAMP','data','Time in the future','Время из будущего','A record has a time later than now (the clock of the router was wrong at that moment).','У записи время позже текущего (часы роутера в тот момент были неверны).','Check the router clock (Help → Dates are wrong).','Проверьте часы роутера («Помощь» → «Неверные даты»).'],
 ['EXPORT-KIND','data','Unknown export','Неизвестный экспорт','The page asked to export a table that does not exist.','Страница запросила экспорт несуществующей таблицы.','Reload the page.','Обновите страницу.'],
 ['DEPENDENCY-IP','service','Program “ip” missing','Нет программы «ip»','The router lacks the “ip” tool the monitor needs.','На роутере нет инструмента «ip», нужного мониторингу.','Install the missing package (opkg install ip-full).','Установите недостающий пакет (opkg install ip-full).'],
 ['DEPENDENCY-LUA','service','Lua missing','Нет Lua','The router lacks Lua.','На роутере нет Lua.','Install lua.','Установите lua.'],
 ['DEPENDENCY-UBUS','service','ubus missing','Нет ubus','The router lacks ubus.','На роутере нет ubus.','Install ubus.','Установите ubus.'],
 ['DEPENDENCY-UCI','service','UCI missing','Нет UCI','The router lacks UCI (libuci-lua).','На роутере нет UCI (libuci-lua).','Install libuci-lua.','Установите libuci-lua.'],
 ['SPEED-COMPLETE','speed','Speed test finished','Тест скорости завершён','The speed test of a server finished.','Тест скорости сервера завершён.','Nothing to do.','Делать ничего не нужно.'],
 ['SPEED-NOT-RUNNING','speed','No speed test is running','Тест скорости не идёт','There is nothing to cancel.','Отменять нечего.','Nothing to do.','Делать ничего не нужно.'],
 ['SPEED-NO-SAMPLE','speed','No measurement','Нет измерения','The speed test got no usable measurement.','Тест скорости не получил пригодного измерения.','Repeat later; check the VPN.','Повторите позже; проверьте VPN.'],
 ['SPEED-CPU-BUSY','speed','Router is busy','Роутер занят','The router’s processor is busy, so the test is postponed to avoid disturbing the traffic.','Процессор роутера занят, поэтому тест отложен, чтобы не мешать трафику.','Try later.','Попробуйте позже.'],
 ['SPEED-TRAFFIC-UNKNOWN','speed','Traffic unknown','Трафик неизвестен','The program cannot tell whether the VPN is busy, so it does not test it.','Программа не может определить, занят ли VPN, поэтому не тестирует его.','Wait for new measurements.','Дождитесь новых измерений.'],
 ['SPEED-SWITCH-IN-PROGRESS','speed','A switch is running','Идёт переключение','No speed test runs while the route is being switched.','Пока маршрут переключается, тест скорости не идёт.','Wait until the switch ends.','Дождитесь окончания переключения.'],
 ['SPEED-PROFILES','speed','No server chosen','Сервер не выбран','The speed test needs at least one connected server.','Для теста скорости нужен хотя бы один подключённый сервер.','Choose connected servers.','Выберите подключённые серверы.'],
 ['SPEED-PROFILES-CHANGED','speed','Server list changed','Список серверов изменился','The servers changed after you chose them.','Серверы изменились после вашего выбора.','Choose again.','Выберите заново.'],
 ['SPEED-CONFIG-LIMIT','speed','Limit exceeded','Лимит превышен','The test would exceed the budget or daily limit you set.','Тест превысил бы заданный вами бюджет или суточный лимит.','Raise the limit below the table or test later.','Увеличьте лимит под таблицей или проверьте позже.'],
 ['AUTO-OPTIONS-NOT-CLEARED','switch','Auto settings could not be reset','Настройки Auto не удалось сбросить','The program stopped Auto but could not clear its own test-window settings because other unsaved router changes exist.','Программа остановила Auto, но не смогла сбросить собственные настройки окна теста, потому что на роутере есть другие несохранённые изменения.','Open the router’s unsaved changes and apply or revert them; then press Stop in the Auto card once more. Auto does not restart by itself: the stop is latched.','Откройте несохранённые изменения роутера и примените либо отмените их; затем ещё раз нажмите «Стоп» в блоке Auto. Auto сам не запустится: остановка зафиксирована.'],
 ['BOARD-OVERSIZE','service','Router board data too big','Данные о плате роутера слишком велики','The router’s board description was bigger than the program accepts, so it was not read.','Описание платы роутера больше, чем принимает программа, поэтому оно не прочитано.','Contact support with the code; nothing was changed.','Обратитесь в поддержку с кодом; ничего не менялось.'],
 ['CA-BUNDLE','service','Certificates package missing','Нет пакета сертификатов','The router has no certificate bundle, so secure (HTTPS) checks and Telegram cannot work.','На роутере нет набора сертификатов, поэтому защищённые (HTTPS) проверки и Telegram работать не могут.','Install ca-bundle (opkg install ca-bundle).','Установите ca-bundle (opkg install ca-bundle).'],
 ['LUCI-CACHE-ROOT','service','Page cache folder is wrong','Папка кэша страниц неверна','During an upgrade the program could not safely clear LuCI’s page cache.','При обновлении программа не смогла безопасно очистить кэш страниц LuCI.','Sign out of LuCI and in again, then Ctrl+F5.','Выйдите из LuCI и войдите снова, затем Ctrl+F5.'],
 ['PYTHON-39-MINIMUM','service','Python is too old','Python слишком старый','The program needs Python 3.9 or newer on the router.','Программе нужен Python 3.9 или новее на роутере.','Use a firmware with Python 3.9+ (GL.iNet 4.11.0 has it).','Используйте прошивку с Python 3.9+ (в GL.iNet 4.11.0 он есть).'],
 ['SPEED-WORKER-TIMEOUT','speed','Test took too long','Тест шёл слишком долго','The test did not finish in time and was stopped.','Тест не закончился вовремя и был остановлен.','Repeat; try a shorter duration.','Повторите; попробуйте меньшую длительность.'],
 ["PAIR-WATCHING", "state", "Auto is watching both channels", "Auto наблюдает за обоими каналами", "Normal working state. Traffic goes through the channel that works, the other one is checked in the background, and Auto is ready to switch by itself if the working channel fails.", "Обычное рабочее состояние. Трафик идёт через рабочий канал, второй проверяется в фоне, и Auto готов сам переключиться, если рабочий канал откажет.", "Nothing to do, this is normal.", "Делать ничего не нужно, это нормально."],
 ["PAIR-WAITING-PROBES", "state", "Auto is collecting the first checks", "Auto собирает первые проверки", "Auto has just started and is collecting the first fresh checks of both channels (usually up to 3 minutes). It does not switch before they arrive.", "Auto только что запущен и собирает первые свежие проверки обоих каналов (обычно до 3 минут). Пока их нет, он не переключает.", "Wait a few minutes; the lamp turns green by itself.", "Подождите несколько минут: лампа сама станет зелёной."],
 ["PAIR-CONNECTING", "state", "Connecting the second channel", "Подключаю второй канал", "Auto is bringing up the VPN channels it needs to watch. This is a short step, so the lamp is yellow.", "Auto поднимает VPN-каналы, за которыми ему нужно следить. Это короткий шаг, поэтому лампа жёлтая.", "Wait a minute. If it lasts longer than 5 minutes, check both VPN profiles in the router.", "Подождите минуту. Если длится дольше 5 минут, проверьте оба VPN-профиля в роутере."],
 ["PAIR-CLEANUP", "state", "Putting the route back in order", "Привожу маршрут в порядок", "Auto is stopping or restoring the VPN channels and checking that the original route is back. Short step, yellow lamp.", "Auto останавливает или восстанавливает VPN-каналы и проверяет, что исходный маршрут на месте. Короткий шаг, лампа жёлтая.", "Wait a minute; do not press Start or Stop again.", "Подождите минуту; не нажимайте Start и Stop повторно."],
 ["PAIR-WAITING-VENDOR", "state", "Waiting for the router VPN data", "Жду данные VPN от роутера", "The router did not give the current state of its own VPN yet, so Auto cannot judge the channels. The lamp is grey: the program is waiting for the router, this is not a proven VPN failure.", "Роутер пока не отдал текущее состояние своих VPN, поэтому Auto не может оценить каналы. Лампа серая: программа ждёт роутер, это не доказанный отказ VPN.", "Wait a minute. If it stays, open the VPN page of the router and check that the profiles are on.", "Подождите минуту. Если не проходит, откройте VPN-страницу роутера и проверьте, что профили включены."],
 ["PAIR-MANUAL-HOLD-RESERVE", "state", "Reserve chosen manually; Auto keeps watching", "Резерв выбран вручную; Auto продолжает наблюдать", "You switched traffic to the reserve yourself. Auto is still on and keeps watching: while the reserve works, traffic stays on it and does not return to the primary automatically. If the reserve fails, Auto moves traffic to the other channel by itself.", "Вы сами перевели трафик на резерв. Auto остаётся включённым и наблюдает: пока резерв работает, трафик остаётся на нём и сам на основной не возвращается. Если резерв откажет, Auto сам переведёт трафик на другой канал.", "Nothing to do. To go back, switch to the primary channel manually.", "Делать ничего не нужно. Чтобы вернуться, переключите на основной канал вручную."],
 ["PAIR-MANUAL-HOLD-PRIMARY", "state", "Primary chosen manually; Auto keeps watching", "Основной выбран вручную; Auto продолжает наблюдать", "You chose the primary channel yourself. Auto is still on and keeps watching: traffic stays on the primary while it works. If it fails, Auto moves traffic to the reserve by itself.", "Вы сами выбрали основной канал. Auto остаётся включённым и наблюдает: пока основной работает, трафик остаётся на нём. Если он откажет, Auto сам переведёт трафик на резерв.", "Nothing to do, this is normal.", "Делать ничего не нужно, это нормально."],
 ["PAIR-MANUAL-HOLD-UNVERIFIED", "switch", "Manual choice could not be confirmed", "Ручной выбор не удалось подтвердить", "Auto could not prove that the channel you chose manually is still the one carrying traffic, so it dropped the manual choice and works normally again.", "Auto не смог доказать, что выбранный вами вручную канал по-прежнему несёт трафик, поэтому снял ручной выбор и снова работает обычным образом.", "Check the Auto card for the current channel and choose again if needed.", "Посмотрите в блоке Auto текущий канал и при необходимости выберите заново."],
 ["PAIR-MANUAL-RECOVERED", "switch", "Interrupted manual switch cleared", "Прерванное ручное переключение снято", "A manual switch request was interrupted (for example by a restart). It was not repeated, so the channel may be different from what you asked for.", "Запрос на ручное переключение был прерван (например, перезапуском). Он не повторялся, поэтому канал может отличаться от выбранного вами.", "Look at the current channel in the Auto card and repeat the manual choice if you still want it.", "Посмотрите текущий канал в блоке Auto и повторите ручной выбор, если он ещё нужен."],
 ["PAIR-MANUAL-BUSY", "switch", "Another switch is in progress", "Уже идёт другое переключение", "A switch is running right now, so the new manual request was not accepted.", "Прямо сейчас идёт переключение, поэтому новый ручной запрос не принят.", "Wait for the current switch to finish (about a minute) and try again.", "Дождитесь окончания текущего переключения (около минуты) и повторите."],
 ["PAIR-MANUAL-COOLDOWN", "switch", "Short pause between manual switches", "Короткая пауза между ручными переключениями", "Manual switches are limited in frequency, so the line is not shaken by repeated switching. The request was not executed.", "Ручные переключения ограничены по частоте, чтобы не раскачивать связь. Запрос не выполнен.", "Wait a minute and try again.", "Подождите минуту и повторите."],
 ["PAIR-MANUAL-EXPIRED", "switch", "Manual request expired", "Ручной запрос устарел", "The manual request waited longer than 60 seconds before it could be run, so it was cancelled to avoid doing an old command.", "Ручной запрос ждал дольше 60 секунд, поэтому был отменён, чтобы не выполнять старую команду.", "Press the manual switch again if you still need it.", "Нажмите ручное переключение ещё раз, если оно ещё нужно."],
 ["PAIR-MANUAL-FIELDS", "switch", "Manual request was malformed", "Ручной запрос составлен неверно", "The router refused a manual request whose fields were incomplete or unexpected. Nothing was changed.", "Роутер отклонил ручной запрос с неполными или неожиданными полями. Ничего не изменено.", "Reload the page (Ctrl+F5) and try again.", "Обновите страницу (Ctrl+F5) и повторите."],
 ["PAIR-MANUAL-NOT-AVAILABLE", "switch", "Manual switch is not available now", "Ручное переключение сейчас недоступно", "The router cannot do this manual switch at the moment (for example the current channel is already the chosen one, or Auto is not ready).", "Роутер сейчас не может выполнить это ручное переключение (например, выбранный канал уже текущий или Auto не готов).", "Open the Auto card: it lists what is missing. Try again when it is ready.", "Откройте блок Auto: там указано, чего не хватает. Повторите, когда он будет готов."],
 ["PAIR-MANUAL-REQUEST-UNCONFIRMED", "switch", "Manual request not confirmed", "Ручной запрос не подтверждён", "The router did not confirm that it accepted the manual request. Do not assume it was done.", "Роутер не подтвердил, что принял ручной запрос. Не считайте его выполненным.", "Wait a minute, look at the current channel in the Auto card, then repeat if needed.", "Подождите минуту, посмотрите текущий канал в блоке Auto и при необходимости повторите."],
 ["PAIR-MANUAL-STALE", "switch", "Router data is too old for a manual switch", "Данные роутера устарели для ручного переключения", "The newest state of the router is older than 30 seconds, so the manual switch is not offered until fresh data arrives.", "Последнее состояние роутера старше 30 секунд, поэтому ручное переключение недоступно до свежих данных.", "Wait for the next refresh (a few seconds).", "Подождите следующего обновления (несколько секунд)."],
 ["PAIR-MANUAL-STATE-UNVERIFIED", "switch", "Cannot confirm the state for a manual switch", "Не удаётся подтвердить состояние для ручного переключения", "Auto could not read or verify the state it needs for a manual switch. Nothing was changed.", "Auto не смог прочитать или проверить состояние, нужное для ручного переключения. Ничего не изменено.", "Wait a minute and try again. If it repeats, keep the code and see Help.", "Подождите минуту и повторите. Если повторяется, сохраните код и загляните в «Помощь»."],
 ["PAIR-MANUAL-TARGET-UNHEALTHY", "switch", "The chosen channel does not pass its checks", "Выбранный канал не проходит проверки", "A manual switch to a channel that is not healthy right now was refused, so you do not lose the connection.", "Ручное переключение на канал, который сейчас нездоров, отклонено, чтобы вы не потеряли связь.", "Choose the other channel, or wait until the chosen one is green.", "Выберите другой канал или подождите, пока выбранный станет зелёным."],
 ["PAIR-MANUAL-UNCONFIRMED", "switch", "Manual switch not confirmed", "Ручное переключение не подтверждено", "The router started the manual switch but could not prove its result. The channel carrying traffic is not verified.", "Роутер начал ручное переключение, но не смог доказать результат. Канал, несущий трафик, не подтверждён.", "Do not repeat at once. Wait a minute; Auto keeps watching and will fix a failed channel itself.", "Не повторяйте сразу. Подождите минуту: Auto продолжает наблюдать и сам исправит отказавший канал."],
 ["PAIR-RATE-LIMIT", "switch", "Too many switches; Auto is pausing", "Слишком много переключений; Auto делает паузу", "Auto limits how often it switches so an unstable line is not shaken further. Traffic stays on the current channel until the pause ends.", "Auto ограничивает частоту переключений, чтобы не раскачивать нестабильную связь. До конца паузы трафик остаётся на текущем канале.", "Nothing to do. If switching is frequent, check both VPN servers in Help.", "Делать ничего не нужно. Если переключений много, проверьте оба VPN-сервера по «Помощи»."],
 ["PAIR-MODE-NOT-CONFIGURED", "setup", "Two-channel Auto is not set up", "Авторежим двух каналов не настроен", "The primary and reserve channels are not both chosen and saved, so the two-channel Auto cannot start or switch manually.", "Основной и резервный каналы не выбраны и не сохранены вместе, поэтому Auto двух каналов не может запуститься или переключаться вручную.", "Choose the primary and the reserve VPN in Settings and save the pair.", "Выберите основной и резервный VPN в настройках и сохраните пару."],
 ["PAIR-PLATFORM-UNVERIFIED", "switch", "Router platform not confirmed", "Платформа роутера не подтверждена", "Auto could not confirm that this router model and firmware are supported for continuous switching, so it does not run.", "Auto не смог подтвердить, что эта модель роутера и прошивка поддерживаются для непрерывного переключения, поэтому не запускается.", "Check System readiness for the exact missing item.", "Посмотрите в «Готовности системы» точный недостающий пункт."],
 ["PAIR-READINESS-CHANGED", "switch", "Readiness changed while Auto was working", "Готовность изменилась во время работы Auto", "Something Auto relies on (router state or preparation) changed, so it stopped and will re-check before continuing.", "Изменилось то, на что опирается Auto (состояние роутера или подготовка), поэтому он остановился и перепроверит перед продолжением.", "Wait a minute; if Auto does not restart, press Start.", "Подождите минуту; если Auto не перезапустился, нажмите Start."],
 ["PAIR-STOPPED", "state", "Auto was stopped and the route restored", "Auto остановлен, маршрут восстановлен", "Auto was switched off and the original route was put back. This is the normal result of pressing Stop.", "Auto выключен, исходный маршрут возвращён. Это обычный результат нажатия Stop.", "Nothing to do. Press Start when you want Auto again.", "Делать ничего не нужно. Нажмите Start, когда Auto снова понадобится."],
 ["PAIR-SYSTEM-001", "internal", "Unexpected internal error in Auto", "Неожиданная внутренняя ошибка Auto", "Auto met an error that has no specific code. It stopped safely; the route is not changed by this error alone.", "Auto встретил ошибку без отдельного кода. Он безопасно остановился; сама по себе эта ошибка маршрут не меняет.", "Press Start again. If it repeats, keep the journal and the time of the event for the maintainer.", "Нажмите Start ещё раз. Если повторяется, сохраните журнал и время события для разработчика."],
 ["PAIR-BUDGET-UNVERIFIED", "internal", "Switch limit record is unreadable", "Запись о лимите переключений нечитаема", "Auto cannot read its saved count of recent switches, so it does not switch until it can prove the limit is respected.", "Auto не может прочитать сохранённый счётчик недавних переключений, поэтому не переключает, пока не докажет, что лимит соблюдён.", "Wait; the record rebuilds itself. If it stays, press Stop and Start.", "Подождите: запись восстановится сама. Если не проходит, нажмите Stop и Start."],
 ["PAIR-CONFIG-UNVERIFIED", "internal", "Saved Auto settings not confirmed", "Сохранённые настройки Auto не подтверждены", "The saved pair or Auto settings could not be read back and verified.", "Сохранённую пару или настройки Auto не удалось прочитать и проверить.", "Open Settings, check the primary and reserve, and save again.", "Откройте настройки, проверьте основной и резервный и сохраните снова."],
 ["PAIR-INTENT-UNVERIFIED", "internal", "Unfinished switch record not confirmed", "Запись о незавершённом переключении не подтверждена", "The record of a switch in progress could not be verified, so Auto does not continue it on trust.", "Запись о переключении в процессе не удалось проверить, поэтому Auto не продолжает его на веру.", "Wait a minute; if it stays, see PAIR-RECOVERY-REQUIRED.", "Подождите минуту; если не проходит, см. PAIR-RECOVERY-REQUIRED."],
 ["PAIR-NETWORK-UNVERIFIED", "internal", "Network state not confirmed", "Состояние сети не подтверждено", "Auto could not read the network settings of the two channels, so it does not act.", "Auto не смог прочитать сетевые настройки двух каналов, поэтому не действует.", "Wait a minute and press Start again.", "Подождите минуту и нажмите Start снова."],
 ["PAIR-NETWORK-WRITE-FAILED", "switch", "Could not write the network settings", "Не удалось записать сетевые настройки", "The router refused to save the network settings Auto needs. The previous settings stay.", "Роутер отказался сохранить сетевые настройки, нужные Auto. Прежние настройки остаются.", "Press Start again after a minute. If it repeats, check free space and the router page.", "Нажмите Start снова через минуту. Если повторяется, проверьте свободное место и страницу роутера."],
 ["PAIR-NETWORK-WRITE-UNVERIFIED", "switch", "Network settings write not confirmed", "Запись сетевых настроек не подтверждена", "Auto wrote network settings but could not read them back to prove them, so it does not rely on them.", "Auto записал сетевые настройки, но не смог прочитать их обратно, поэтому не полагается на них.", "Press Start again. If it repeats, keep the code for the maintainer.", "Нажмите Start снова. Если повторяется, сохраните код для разработчика."],
 ["PAIR-PROFILE-STOP-UNVERIFIED", "switch", "Could not confirm the extra VPN stopped", "Не удалось подтвердить остановку лишнего VPN", "When stopping, Auto could not prove that the unused VPN client is off.", "При остановке Auto не смог доказать, что неиспользуемый VPN-клиент выключен.", "Check the VPN page of the router and switch the unused profile off.", "Проверьте VPN-страницу роутера и выключите неиспользуемый профиль."],
 ["RESPONSE-COMPARE-UNAVAILABLE", "data", "Method comparison is unavailable", "Сравнение способов недоступно", "The saved comparison of all response methods cannot be used right now. Switching and the chosen response method are not affected.", "Сохранённое сравнение всех способов отклика сейчас нельзя использовать. Переключение и выбранный способ отклика не затронуты.", "Nothing to do. Turn “measure all methods” off and on again if it stays.", "Делать ничего не нужно. Если не проходит, выключите и снова включите «замерять все способы»."],
 ["RESPONSE-COMPARE-WRITE-FAILED", "data", "Method comparison was not saved", "Сравнение способов не сохранено", "The router could not save the latest comparison of response methods (for example not enough free space). The last good copy stays.", "Роутер не смог сохранить последнее сравнение способов отклика (например, мало места). Последняя хорошая копия остаётся.", "Free some space on the router or wait; Auto and the lamps are not affected.", "Освободите место на роутере или подождите; Auto и лампы не затронуты."],
 ["RESPONSE-COMPARE-SCHEMA", "data", "Method comparison file has the wrong form", "Файл сравнения способов в неверном виде", "The saved comparison has an unexpected structure and was ignored.", "Сохранённое сравнение имеет неожиданную структуру и проигнорировано.", "Nothing to do; a new comparison is collected by itself.", "Делать ничего не нужно: новое сравнение соберётся само."],
 ["RESPONSE-COMPARE-SIZE", "data", "Method comparison file is too large", "Файл сравнения способов слишком велик", "The saved comparison is bigger than allowed and was ignored.", "Сохранённое сравнение больше допустимого и проигнорировано.", "Nothing to do; it is rebuilt by itself.", "Делать ничего не нужно: оно пересоберётся само."],
 ["RESPONSE-COMPARE-VALUE", "data", "Method comparison has a wrong value", "В сравнении способов неверное значение", "One saved value of the comparison is outside the allowed range and the file was ignored.", "Одно сохранённое значение сравнения вне допустимого диапазона, файл проигнорирован.", "Nothing to do; it is rebuilt by itself.", "Делать ничего не нужно: оно пересоберётся само."],
 ["PING-HISTORY", "data", "Ping history problem", "Проблема истории пинга", "The saved ping history could not be used. Current pings and switching continue.", "Сохранённую историю пинга нельзя использовать. Текущие пинги и переключение продолжаются.", "Nothing to do; the history is collected again.", "Делать ничего не нужно: история соберётся заново."],
 ["LATENCY-HISTORY-UNAVAILABLE", "data", "Delay history is unavailable", "История задержки недоступна", "The saved delay history cannot be read right now. The charts may be empty for a while; current readings and Auto are not affected.", "Сохранённую историю задержки сейчас нельзя прочитать. Графики могут какое-то время быть пустыми; текущие показания и Auto не затронуты.", "Nothing to do; it fills again by itself.", "Делать ничего не нужно: она заполнится снова сама."],
 ["LATENCY-HISTORY-WRITE-FAILED", "data", "Delay history was not saved", "История задержки не сохранена", "The router could not save the newest delay readings. Older saved data stays.", "Роутер не смог сохранить новые замеры задержки. Прежние сохранённые данные остаются.", "Free some space on the router if it repeats.", "Если повторяется, освободите место на роутере."],
 ["LIFECYCLE-READY", "service", "Ready for an upgrade check passed", "Проверка перед обновлением пройдена", "Auto is off and the original route is in place, so an upgrade or stop is safe.", "Auto выключен, исходный маршрут на месте, поэтому обновление или остановка безопасны.", "Nothing to do, this is a good result.", "Делать ничего не нужно, это хороший результат."],
 ["LIFECYCLE-UPGRADE-READY", "service", "Ready to upgrade", "Готово к обновлению", "All checks before an upgrade passed.", "Все проверки перед обновлением пройдены.", "You can continue with the upgrade.", "Можно продолжать обновление."],
 ["LIFECYCLE-AUTO-DISABLED", "service", "Auto was switched off for the upgrade", "Auto выключен на время обновления", "Before the upgrade the program switched Auto off and checked the route.", "Перед обновлением программа выключила Auto и проверила маршрут.", "After the upgrade press Start when you want Auto again.", "После обновления нажмите Start, когда Auto снова понадобится."],
 ["LIFECYCLE-AUTO-DISABLE-FAILED", "service", "Could not switch Auto off", "Не удалось выключить Auto", "The program could not prove that Auto is off, so the upgrade step stopped.", "Программа не смогла доказать, что Auto выключен, поэтому шаг обновления остановлен.", "Press Stop in the Auto card, wait for the original route, and repeat.", "Нажмите Stop в блоке Auto, дождитесь исходного маршрута и повторите."],
 ["LIFECYCLE-ACTION", "service", "Unknown service action", "Неизвестное действие службы", "The service script was called with an action it does not know. Nothing was changed.", "Скрипт службы вызван с неизвестным действием. Ничего не изменено.", "Use the normal install or upgrade command.", "Используйте обычную команду установки или обновления."],
 ["LIFECYCLE-CONFIG-UNVERIFIED", "service", "Settings not confirmed before the upgrade", "Настройки не подтверждены перед обновлением", "The saved settings could not be read and checked, so the upgrade step did not go on.", "Сохранённые настройки не удалось прочитать и проверить, поэтому шаг обновления не продолжен.", "Wait a minute and repeat. Keep the code if it stays.", "Подождите минуту и повторите. Если не проходит, сохраните код."],
 ["LIFECYCLE-CONTROL-BUSY", "service", "Another control action is running", "Выполняется другое управляющее действие", "The control lock is held by another action, so this step waited and then gave up.", "Управляющая блокировка занята другим действием, поэтому шаг подождал и отказался.", "Wait for the other action to finish and repeat.", "Дождитесь окончания другого действия и повторите."],
 ["LIFECYCLE-CONTROL-UNVERIFIED", "service", "Control state not confirmed", "Состояние управления не подтверждено", "The saved control state could not be verified.", "Сохранённое состояние управления не удалось проверить.", "Wait a minute and repeat.", "Подождите минуту и повторите."],
 ["LIFECYCLE-JOURNAL-ACTIVE", "service", "A switch is still unfinished", "Переключение ещё не завершено", "The switch journal shows an unfinished switch, so the upgrade waits.", "Журнал переключений показывает незавершённое переключение, поэтому обновление ждёт.", "Wait until the switch ends or recovery completes, then repeat.", "Дождитесь окончания переключения или восстановления и повторите."],
 ["LIFECYCLE-JOURNAL-UNVERIFIED", "service", "Switch journal not confirmed", "Журнал переключений не подтверждён", "The switch journal could not be verified, so the upgrade step stopped.", "Журнал переключений не удалось проверить, поэтому шаг обновления остановлен.", "Keep the journal and ask the maintainer; do not delete it.", "Сохраните журнал и обратитесь к разработчику; не удаляйте его."],
 ["LIFECYCLE-PENDING-UCI-CHANGES", "service", "Unsaved router settings exist", "Есть неприменённые настройки роутера", "The router has settings that are changed but not applied yet, so the upgrade step stopped.", "В роутере есть изменённые, но не применённые настройки, поэтому шаг обновления остановлен.", "Apply or discard the pending settings in the router interface and repeat.", "Примените или отмените ожидающие настройки в интерфейсе роутера и повторите."],
 ["LIFECYCLE-STATE-UNVERIFIED", "service", "Program state not confirmed", "Состояние программы не подтверждено", "The current state of the program could not be verified before the upgrade.", "Текущее состояние программы не удалось проверить перед обновлением.", "Wait a minute and repeat.", "Подождите минуту и повторите."],
 ["PREPARATION-VERIFIED", "setup", "Router preparation verified", "Подготовка роутера подтверждена", "The saved preparation of the router was checked and is correct.", "Сохранённая подготовка роутера проверена и верна.", "Nothing to do, this is a good result.", "Делать ничего не нужно, это хороший результат."],
 ["PREPARATION-UNVERIFIED", "setup", "Router preparation not confirmed", "Подготовка роутера не подтверждена", "At least one prerequisite of the router preparation could not be proven.", "Хотя бы одно условие подготовки роутера не удалось доказать.", "Open System readiness → Router preparation and read which item is missing.", "Откройте «Готовность системы» → «Подготовка роутера» и посмотрите, какого пункта не хватает."],
 ["PREPARATION-STOP-AUTO-FIRST", "setup", "Stop Auto before changing the preparation", "Остановите Auto перед сменой подготовки", "The preparation can be changed only while Auto is off, so a running Auto is not disturbed.", "Подготовку можно менять только при выключенном Auto, чтобы не мешать работающему Auto.", "Press Stop in the Auto card, wait for the original route, then repeat.", "Нажмите Stop в блоке Auto, дождитесь исходного маршрута и повторите."],
 ["PREPARATION-STALE-REVIEW", "setup", "The review is out of date", "Проверка устарела", "The router changed after you reviewed the preparation, so the action was refused.", "Роутер изменился после вашего просмотра подготовки, поэтому действие отклонено.", "Open the preparation again, read the fresh review, and confirm again.", "Откройте подготовку заново, прочитайте свежую проверку и подтвердите снова."],
 ["PREPARATION-EXTERNAL-CHANGE", "setup", "Router settings changed from outside", "Настройки роутера изменены снаружи", "Something else changed a router setting that the preparation relies on.", "Что-то другое изменило настройку роутера, на которую опирается подготовка.", "Open the preparation, review what changed, and apply it again if you agree.", "Откройте подготовку, посмотрите, что изменилось, и примените снова, если согласны."],
 ["PREPARATION-PENDING-OR-UNREADABLE", "setup", "Router settings pending or unreadable", "Настройки роутера ожидают применения или нечитаемы", "The router has unapplied changes or the setting could not be read, so the preparation does not go on.", "В роутере есть неприменённые изменения или настройку не удалось прочитать, поэтому подготовка не продолжается.", "Apply or discard pending changes in the router interface and repeat.", "Примените или отмените ожидающие изменения в интерфейсе роутера и повторите."],
 ["PREPARATION-WRITE-UNCONFIRMED", "setup", "Preparation write not confirmed", "Запись подготовки не подтверждена", "A preparation setting was written but could not be read back and proven.", "Настройка подготовки записана, но не удалось прочитать её обратно и доказать.", "Review the preparation again before relying on it.", "Проверьте подготовку заново, прежде чем полагаться на неё."],
 ["PREPARATION-AUTOLOAD-UNVERIFIED", "setup", "Startup loading not confirmed", "Автозагрузка не подтверждена", "It was not proven that the needed module is loaded at router start.", "Не доказано, что нужный модуль загружается при старте роутера.", "Review System readiness → Router preparation.", "Посмотрите «Готовность системы» → «Подготовка роутера»."],
 ["PREPARATION-BACKUP-UNVERIFIED", "setup", "Backup copy not confirmed", "Резервная копия не подтверждена", "The backup of the original settings could not be proven, so the change was not made.", "Резервную копию исходных настроек не удалось доказать, поэтому изменение не сделано.", "Repeat the preparation after a minute; keep the code if it stays.", "Повторите подготовку через минуту; если не проходит, сохраните код."],
 ["PREPARATION-BINDING-UNVERIFIED", "setup", "Preparation does not match this router", "Подготовка не соответствует этому роутеру", "The saved preparation belongs to a different router state or version.", "Сохранённая подготовка относится к другому состоянию или версии роутера.", "Run the preparation review again.", "Запустите проверку подготовки заново."],
 ["PREPARATION-BOOT-UNVERIFIED", "setup", "Start-at-boot not confirmed", "Запуск при загрузке не подтверждён", "It was not proven that the program starts when the router boots.", "Не доказано, что программа запускается при загрузке роутера.", "Review System readiness → Router preparation.", "Посмотрите «Готовность системы» → «Подготовка роутера»."],
 ["PREPARATION-FIELDS", "setup", "Preparation request was malformed", "Запрос подготовки составлен неверно", "The preparation request had missing or extra fields and was refused. Nothing was changed.", "В запросе подготовки были лишние или недостающие поля, он отклонён. Ничего не изменено.", "Reload the page (Ctrl+F5) and repeat.", "Обновите страницу (Ctrl+F5) и повторите."],
 ["PREPARATION-FILE-UNVERIFIED", "setup", "A program file is not confirmed", "Файл программы не подтверждён", "A file of the preparation is missing or differs from the expected one.", "Файл подготовки отсутствует или отличается от ожидаемого.", "Reinstall the package, then repeat the review.", "Переустановите пакет и повторите проверку."],
 ["PREPARATION-FIREWALL-UNVERIFIED", "setup", "Firewall rules not confirmed", "Правила файрвола не подтверждены", "The firewall state needed for safe work could not be proven.", "Состояние файрвола, нужное для безопасной работы, не удалось доказать.", "Review System readiness → Router preparation.", "Посмотрите «Готовность системы» → «Подготовка роутера»."],
 ["PREPARATION-HISTORY-LIMIT", "setup", "Too many preparation records", "Слишком много записей подготовки", "The record of past preparation actions reached its limit; no further action is accepted until it is cleaned.", "Журнал прошлых действий подготовки достиг предела; новые действия не принимаются, пока он не очищен.", "Keep the code and ask the maintainer to clean the record.", "Сохраните код и попросите разработчика очистить журнал."],
 ["PREPARATION-HNAT-UNVERIFIED", "setup", "Hardware acceleration not confirmed off", "Аппаратное ускорение не подтверждено выключенным", "It was not proven that the router hardware acceleration is off, which Auto needs for safe switching.", "Не доказано, что аппаратное ускорение роутера выключено, а оно нужно Auto для безопасного переключения.", "Review System readiness → Router preparation.", "Посмотрите «Готовность системы» → «Подготовка роутера»."],
 ["PREPARATION-PLATFORM-UNVERIFIED", "setup", "Router model not confirmed", "Модель роутера не подтверждена", "This router model or firmware was not confirmed for the preparation.", "Модель или прошивка этого роутера не подтверждены для подготовки.", "Check System readiness for the exact item.", "Посмотрите «Готовность системы» для точного пункта."],
 ["PREPARATION-VALUE-UNVERIFIED", "setup", "A setting value is not confirmed", "Значение настройки не подтверждено", "A setting of the preparation has a value that was not expected.", "У настройки подготовки неожиданное значение.", "Run the preparation review again.", "Запустите проверку подготовки заново."],
 ["FAULT-CERTIFICATE-STALE", "switch", "Failure test approval expired", "Разрешение теста сбоя устарело", "The approval for the failure test is old or does not match the current state, so the test did not start.", "Разрешение на тест сбоя устарело или не совпадает с текущим состоянием, поэтому тест не запущен.", "Prepare the test again from the Tests page.", "Подготовьте тест заново на странице «Тесты»."],
 ["FAULT-CLAIM-STALE", "switch", "Failure test request expired", "Запрос теста сбоя устарел", "The failure test request waited too long and was dropped.", "Запрос теста сбоя ждал слишком долго и был сброшен.", "Start the test again.", "Запустите тест заново."],
 ["FAULT-COMMAND-UNCONFIRMED", "switch", "Test command not confirmed", "Команда теста не подтверждена", "The router did not confirm the failure test command. Do not assume the test is running.", "Роутер не подтвердил команду теста сбоя. Не считайте тест запущенным.", "Check that the fault is off in the Tests page and the route is normal.", "Проверьте на странице «Тесты», что сбой выключен и маршрут обычный."],
 ["FAULT-CONTROL-CHANGED", "switch", "Test control changed meanwhile", "Управление тестом изменилось", "Another action changed the control state while the failure test was being prepared.", "Другое действие изменило состояние управления, пока готовился тест сбоя.", "Repeat the test from the start.", "Повторите тест с начала."],
 ["FAULT-IDENTITY-GONE", "switch", "Tested VPN disappeared", "Проверяемый VPN исчез", "The VPN that was chosen for the failure test is no longer present.", "VPN, выбранный для теста сбоя, больше не найден.", "Choose the VPN again and repeat.", "Выберите VPN заново и повторите."],
 ["FAULT-IDENTITY-UNVERIFIED", "switch", "Tested VPN not confirmed", "Проверяемый VPN не подтверждён", "It was not proven which VPN the failure test affects, so it was not run.", "Не доказано, на какой VPN действует тест сбоя, поэтому он не запущен.", "Wait for fresh observations and repeat.", "Дождитесь свежих наблюдений и повторите."],
 ["FAULT-START-UNCONFIRMED", "switch", "Test start not confirmed", "Запуск теста не подтверждён", "The router did not confirm that the failure test started.", "Роутер не подтвердил, что тест сбоя запущен.", "Check the Tests page; stop the test if it shows as running.", "Проверьте страницу «Тесты»; остановите тест, если он показан как идущий."],
 ["RPC-RATE-LIMIT", "service", "Too many requests, wait a moment", "Слишком много запросов, подождите", "The page asked the router too often, so this request was refused to protect the router. Nothing was changed.", "Страница обращалась к роутеру слишком часто, поэтому запрос отклонён для защиты роутера. Ничего не изменено.", "Wait a few seconds and repeat.", "Подождите несколько секунд и повторите."],
 ["RPC-INPUT-INVALID", "service", "Request has a wrong value", "В запросе неверное значение", "The router refused a request whose value was outside the allowed form or size. Nothing was changed.", "Роутер отклонил запрос со значением вне допустимого вида или размера. Ничего не изменено.", "Check what you entered and repeat; reload the page if it stays.", "Проверьте введённое и повторите; если не проходит, обновите страницу."],
 ["RPC-UNKNOWN-METHOD", "service", "The router does not know this request", "Роутер не знает такой запрос", "The page and the program on the router are of different versions.", "Страница и программа на роутере разных версий.", "Reload the page (Ctrl+F5); reinstall the package if it stays.", "Обновите страницу (Ctrl+F5); если не проходит, переустановите пакет."],
 ["RPC-UNEXPECTED-ARGS", "service", "Request has extra data", "В запросе лишние данные", "The router refused a request with unexpected fields. Nothing was changed.", "Роутер отклонил запрос с неожиданными полями. Ничего не изменено.", "Reload the page (Ctrl+F5).", "Обновите страницу (Ctrl+F5)."],
 ["RPC-CONFIRM-NO-PENDING", "service", "Nothing is waiting for confirmation", "Нечего подтверждать", "The confirmation arrived but no switch is waiting for it (it may have expired).", "Подтверждение пришло, но ни одно переключение его не ждёт (возможно, время вышло).", "Nothing to do.", "Делать ничего не нужно."],
 ["RPC-CONFIRM-EXPIRED", "service", "Confirmation came too late", "Подтверждение пришло слишком поздно", "The time for confirming the switch is over, so the confirmation was not accepted.", "Время подтверждения переключения вышло, поэтому подтверждение не принято.", "Nothing to do; Auto returns to a safe route by itself.", "Делать ничего не нужно: Auto сам вернётся на безопасный маршрут."],
 ["RPC-CONFIRM-ADDRESS", "service", "Confirmation came from another address", "Подтверждение пришло с другого адреса", "The confirmation did not come from the computer that is expected to confirm.", "Подтверждение пришло не с того компьютера, который должен подтверждать.", "Confirm from the chosen computer.", "Подтвердите с выбранного компьютера."],
 ["RPC-CONFIRM-FIELDS", "service", "Confirmation was malformed", "Подтверждение составлено неверно", "The confirmation had missing or extra fields and was refused.", "В подтверждении были лишние или недостающие поля, оно отклонено.", "Reload the page (Ctrl+F5).", "Обновите страницу (Ctrl+F5)."],
 ["RPC-CONFIRM-TRANSACTION", "service", "Confirmation is for another switch", "Подтверждение относится к другому переключению", "The confirmation does not belong to the switch that is waiting.", "Подтверждение не относится к переключению, которое ожидает.", "Nothing to do; wait for the current switch.", "Делать ничего не нужно; дождитесь текущего переключения."],
 ["RPC-CONFIRM-TRIAL", "service", "Confirmation is for another test", "Подтверждение относится к другому тесту", "The confirmation does not belong to the current trial.", "Подтверждение не относится к текущему тесту.", "Repeat the confirmation for the current test.", "Повторите подтверждение для текущего теста."],
 ["RPC-CONFIRM-UNVERIFIED", "service", "Confirmation not verified", "Подтверждение не проверено", "The router could not verify the confirmation.", "Роутер не смог проверить подтверждение.", "Repeat after a minute.", "Повторите через минуту."],
 ["SPEED-ADDRESS", "speed", "Speed test server address refused", "Адрес сервера теста скорости отклонён", "The speed test address was not a public internet address, so it was not used.", "Адрес теста скорости не был публичным интернет-адресом, поэтому не использован.", "Nothing to do; try the test again.", "Делать ничего не нужно; запустите тест заново."],
 ["SPEED-AUTO-DISABLED", "speed", "Speed test needs Auto off or ready", "Тест скорости недоступен при таком состоянии Auto", "The speed test is not run while Auto state does not allow it.", "Тест скорости не запускается, пока состояние Auto этого не позволяет.", "Wait for Auto to finish its step and repeat.", "Дождитесь окончания шага Auto и повторите."],
 ["SPEED-CANCEL-UNVERIFIED", "speed", "Test cancel not confirmed", "Отмена теста не подтверждена", "It was not proven that the speed test stopped.", "Не доказано, что тест скорости остановлен.", "Wait a minute and check that the test is not running.", "Подождите минуту и проверьте, что тест не идёт."],
 ["SPEED-CLOCK-BACKWARD", "speed", "Router clock went back", "Часы роутера пошли назад", "The router clock jumped back during the test, so the result is not reliable.", "Часы роутера скакнули назад во время теста, поэтому результат ненадёжен.", "Repeat the test later.", "Повторите тест позже."],
 ["SPEED-CLOCK-UNSET", "speed", "Router clock is not set", "Часы роутера не установлены", "The router does not know the real time yet, so the speed test limits cannot be counted.", "Роутер ещё не знает точное время, поэтому лимиты теста скорости нельзя посчитать.", "Wait until the router gets the time from the internet.", "Подождите, пока роутер получит время из интернета."],
 ["SPEED-CONFIG", "speed", "Speed test settings are out of range", "Настройки теста скорости вне диапазона", "A speed test setting has a value that is not allowed.", "У настройки теста скорости недопустимое значение.", "Open the speed test settings and enter a value in the allowed range.", "Откройте настройки теста скорости и введите значение в допустимом диапазоне."],
 ["SPEED-CONFIG-FIELDS", "speed", "Speed test settings were malformed", "Настройки теста скорости составлены неверно", "The speed test settings had missing or extra fields.", "В настройках теста скорости были лишние или недостающие поля.", "Reload the page (Ctrl+F5) and save again.", "Обновите страницу (Ctrl+F5) и сохраните снова."],
 ["SPEED-DNS", "speed", "Speed test name not resolved", "Имя сервера теста скорости не найдено", "The speed test server name could not be resolved through the VPN.", "Имя сервера теста скорости не удалось разрешить через VPN.", "Repeat later; if it repeats check the DNS of this VPN.", "Повторите позже; если повторяется, проверьте DNS этого VPN."],
 ["SPEED-HISTORY-CORRUPT", "speed", "Speed history unreadable", "История скорости нечитаема", "The saved speed results could not be read and were ignored.", "Сохранённые результаты скорости не удалось прочитать, они проигнорированы.", "Nothing to do; new tests fill it again.", "Делать ничего не нужно: новые тесты заполнят её снова."],
 ["SPEED-HTTP", "speed", "Speed test server answered with an error", "Сервер теста скорости ответил ошибкой", "The speed test download failed with an HTTP error.", "Скачивание для теста скорости завершилось ошибкой HTTP.", "Repeat later.", "Повторите позже."],
 ["SPEED-MONITOR-UNAVAILABLE", "speed", "Monitor is not available for the speed test", "Мониторинг недоступен для теста скорости", "The speed test needs the running monitor, which does not answer.", "Для теста скорости нужен работающий мониторинг, он не отвечает.", "Start monitoring and repeat.", "Запустите мониторинг и повторите."],
 ["SPEED-QUOTA-CORRUPT", "speed", "Speed test limit record unreadable", "Запись лимита теста скорости нечитаема", "The saved count of speed test traffic could not be read, so the test is not run.", "Сохранённый счётчик трафика тестов скорости не удалось прочитать, поэтому тест не запускается.", "Wait; the record rebuilds itself.", "Подождите: запись восстановится сама."],
 ["SPEED-REQUEST", "speed", "Speed test request is wrong", "Запрос теста скорости неверен", "The request had wrong or extra values and was refused.", "В запросе были неверные или лишние значения, он отклонён.", "Reload the page (Ctrl+F5) and repeat.", "Обновите страницу (Ctrl+F5) и повторите."],
 ["SPEED-RESPONSE-LIMIT", "speed", "Speed test download limit reached", "Достигнут лимит скачивания теста", "The test downloaded more than allowed and was stopped.", "Тест скачал больше допустимого и был остановлен.", "Nothing to do.", "Делать ничего не нужно."],
 ["SPEED-SHORT-RESPONSE", "speed", "Speed test answer too short", "Ответ сервера теста слишком короткий", "The server gave less data than needed for a reliable result.", "Сервер отдал меньше данных, чем нужно для надёжного результата.", "Repeat later.", "Повторите позже."],
 ["SPEED-STATUS-UNAVAILABLE", "speed", "Speed test status unavailable", "Состояние теста скорости недоступно", "The router did not give the speed test status.", "Роутер не отдал состояние теста скорости.", "Reload the page and check again.", "Обновите страницу и проверьте снова."],
 ["SPEED-SYSTEM", "speed", "Speed test system error", "Системная ошибка теста скорости", "The router failed to run a step of the speed test.", "Роутеру не удалось выполнить шаг теста скорости.", "Repeat later.", "Повторите позже."],
 ["SPEED-WORKER-LOST", "speed", "Speed test worker stopped", "Исполнитель теста скорости остановился", "The background part of the test stopped before finishing.", "Фоновая часть теста остановилась, не закончив работу.", "Repeat the test.", "Повторите тест."],
 ["SPEED-WORKER-START", "speed", "Speed test could not start", "Тест скорости не удалось запустить", "The router could not start the background part of the test.", "Роутер не смог запустить фоновую часть теста.", "Repeat later.", "Повторите позже."],
 ["POLICY-CHANGED-DURING-PREFLIGHT", "switch", "VPN rules changed during the check", "Правила VPN изменились во время проверки", "The VPN route rules changed while the readiness check was running, so its result is not used.", "Правила маршрутов VPN изменились во время проверки готовности, поэтому её результат не используется.", "Repeat the check when nothing edits the VPN settings.", "Повторите проверку, когда никто не правит настройки VPN."],
 ["RECOVERY-ACTION", "service", "Unknown recovery action", "Неизвестное действие восстановления", "The recovery script was called with an action it does not know. Nothing was changed.", "Скрипт восстановления вызван с неизвестным действием. Ничего не изменено.", "Use the documented recovery command.", "Используйте документированную команду восстановления."],
 ["TELEGRAM-ITEMS", "telegram", "Telegram report items are wrong", "Состав отчёта Telegram неверен", "The list of items chosen for the Telegram report is not valid.", "Список пунктов отчёта Telegram недопустим.", "Open the Telegram wizard and choose the items again.", "Откройте мастер Telegram и выберите пункты заново."],
 ["ENDPOINT-ADDRESS", "data", "Server address not valid", "Адрес сервера недопустим", "The server address or port is empty, too long or not usable.", "Адрес сервера или порт пусты, слишком длинны или непригодны.", "Nothing to do; this only hides the address shown.", "Делать ничего не нужно: скрывается только показ адреса."],
 ["ENDPOINT-PROC", "data", "Server address could not be read", "Адрес сервера не удалось прочитать", "The kernel table with the current server address could not be read.", "Таблицу ядра с текущим адресом сервера не удалось прочитать.", "Nothing to do; it is tried again.", "Делать ничего не нужно: попытка повторится."],
 ["ENDPOINT-PROCESS-EPOCH", "data", "Server address changed while reading", "Адрес сервера изменился при чтении", "The tunnel restarted while its address was read, so the value was dropped.", "Туннель перезапустился во время чтения адреса, значение отброшено.", "Nothing to do.", "Делать ничего не нужно."],
 ["ENDPOINT-READ-LIMIT", "data", "Server address table too large", "Таблица адреса сервера слишком велика", "The kernel table was larger than allowed and was not read.", "Таблица ядра больше допустимого и не прочитана.", "Nothing to do.", "Делать ничего не нужно."],
];
var ERROR_FAMILIES=[
 ['FAST-','switch','Fast switch not used','Быстрое переключение не применено','The router could not apply the channel order directly (unexpected firewall chains or the change was not confirmed) and used the slower GL rebuild instead, or refused the switch.','Роутер не смог применить порядок каналов напрямую (неожиданные цепочки firewall или изменение не подтвердилось) и использовал медленную перестройку GL либо отказался от переключения.','Nothing to do: the switch still works through the GL rebuild. If it repeats, send the code to the developer.','Ничего делать не нужно: переключение работает через перестройку GL. Если повторяется, отправьте код разработчику.'],
 ['RESPONSE-COMPARE','data','Comparison of response methods','Сравнение способов отклика','The saved comparison of all response methods could not be read or written safely. Switching and the chosen metric are not affected.','Сохранённое сравнение всех способов отклика не удалось безопасно прочитать или записать. Переключение и выбранный способ не затронуты.','No action is needed. Turning "measure all methods" off and on starts a new comparison; the old file is kept.','Делать ничего не нужно. Выключение и включение «мерить все способы» начинает новое сравнение; старый файл сохраняется.'],
 ['PING-HISTORY','data','Ping history check','Проверка истории пинга','The saved ping history could not be read or written safely. Current pings and switching continue.','Сохранённую историю пинга не удалось безопасно прочитать или записать. Текущие пинги и переключение продолжают работать.','No action is needed for switching. If it repeats, reset the chart or reinstall the package; the old file is kept.','Для переключения ничего делать не нужно. Если повторяется, сбросьте график или переустановите пакет; старый файл сохраняется.'],
 ['PREPARATION-','setup','Router preparation action','Действие подготовки роутера','A reviewed preparation action was verified or refused with this specific code. A successful setting write does not start Auto or prove all prerequisites.','Проверенное действие подготовки выполнено либо отклонено с указанным кодом. Запись настройки не запускает Auto и не доказывает выполнение всех условий.','Read the exact reason shown beside the button. Stop and complete recovery before edits. After an unconfirmed write retain the private preparation-changes record; do not delete it or repeat blindly. Restart-required means a separate deliberate router reboot before Auto.','Прочитайте конкретную причину у кнопки. До изменений остановите Auto и завершите восстановление. После неподтверждённой записи сохраните приватный журнал preparation-changes; не удаляйте его и не повторяйте вслепую. Restart-required означает отдельную осознанную перезагрузку роутера перед Auto.'],
 ['LATENCY-','data','Delay history unavailable','История задержки недоступна','A bounded delay-history sample, file or checksum could not be verified. This does not establish a VPN failure.','Не удалось проверить запись, файл или контрольную сумму истории задержки. Это само по себе не означает отказ VPN.','Preserve the file and inspect storage. Current checks can continue; do not invent missing history or reset the VPN to repair a graph.','Сохраните файл и проверьте хранилище. Текущие проверки могут продолжаться; не дорисовывайте историю и не сбрасывайте VPN ради графика.'],
 ['ENDPOINT-','data','Current server address not observed','Текущий адрес сервера не получен','The read-only kernel peer lookup was unavailable, ambiguous or changed during observation. A configured name is not proof of the current peer.','Чтение адреса соединения из ядра недоступно, неоднозначно или соединение изменилось во время проверки. Название профиля не доказывает текущий адрес.','Wait for a fresh settled observation. Inspect the matching VPN process/interface read-only; do not restart a working tunnel merely to fill in its address.','Дождитесь свежей согласованной проверки. Проверьте соответствующий процесс и интерфейс только чтением; не перезапускайте рабочий туннель ради заполнения адреса.'],
 ['STATISTICS-','data','Saved statistics check','Проверка сохранённой статистики','The saved counters, incident details or download cursor failed validation. Unverified data is not presented as a successful observation.','Сохранённые счётчики, события или позиция выгрузки не прошли проверку. Непроверенные данные не считаются успешным наблюдением.','Retry the download. If the error persists, preserve both checkpoint files and inspect storage; do not reset the counters.','Повторите выгрузку. Если ошибка повторяется, сохраните оба файла контрольных точек и проверьте хранилище; не сбрасывайте счётчики.','STATISTICS-CURSOR: restart the download from the first page.','STATISTICS-CURSOR: начните выгрузку с первой страницы.'],
 ['PREP-','platform','Persistent router preparation (PREP-…)','Постоянная подготовка роутера (PREP-…)','A saved startup or acceleration prerequisite is missing, changed or unverified. A passing dependency check alone does not establish safe native operation.','Постоянная настройка запуска или ускорения отсутствует, изменена либо не проверена. Наличия зависимостей недостаточно для безопасного переключения.','Review the preparation card and the documented original values/undo procedure. Do not disable a working DNS owner or force-unload drivers.','Проверьте карточку подготовки и инструкцию с исходными значениями и отменой изменений. Не отключайте рабочий DNS и не выгружайте драйверы принудительно.'],
 ['PAIR-','internal','Two-channel Auto (PAIR-…)','Авторежим двух каналов (PAIR-…)','The two-channel controller is preparing profiles or refused an unverified operation. Router probes do not certify an external LAN client.','Контроллер двух каналов готовит профили либо отклонил непроверенное действие. Проверки роутера не подтверждают внешний LAN-клиент.','Read the current phase and reason. Stop remains available; keep the recovery record and do not delete it to bypass a refusal.','Прочитайте текущий этап и причину. Остановка остаётся доступной; сохраните запись восстановления и не удаляйте её ради обхода отказа.'],
 ['CASCADE-','internal','Internal check of the fallback model (CASCADE-…)','Внутренняя проверка модели каскада (CASCADE-…)','A safety check of the model that plans server → channel → protocol switching refused a step. These checks exist to stop a wrong or stale step; the model is not applied to the router in this version.','Защитная проверка модели, планирующей переключение сервер → канал → протокол, отклонила шаг. Эти проверки нужны, чтобы остановить неверный или устаревший шаг; в этой версии модель на роутер не применяется.','Nothing to do for a normal user. Send the full code to support if it appears on a real router.','Обычному пользователю делать ничего не нужно. Если код появился на настоящем роутере, отправьте его полностью в поддержку.','CASCADE-PROOF-EXPIRED: a confirmation arrived too late and was ignored.','CASCADE-PROOF-EXPIRED: подтверждение пришло слишком поздно и было проигнорировано.'],
 ['CANDIDATE-','internal','Internal check of candidate probing (CANDIDATE-…)','Внутренняя проверка пробы кандидатов (CANDIDATE-…)','A safety check of the model that tests replacement servers refused a step (limits, timing or ownership).','Защитная проверка модели, проверяющей замену серверов, отклонила шаг (лимиты, время или принадлежность).','Nothing to do for a normal user. Send the full code to support if it appears on a real router.','Обычному пользователю делать ничего не нужно. Если код появился на настоящем роутере, отправьте его полностью в поддержку.','CANDIDATE-BUDGET-EXCEEDED: the test would have used more traffic than allowed, so it was not run.','CANDIDATE-BUDGET-EXCEEDED: тест использовал бы больше трафика, чем разрешено, поэтому не запускался.'],
 ['MODEL-','internal','Internal check of the switching model (MODEL-…)','Внутренняя проверка модели переключения (MODEL-…)','A rule of the model of the switch process (used in tests) refused or reported a step.','Правило модели процесса переключения (она используется в тестах) отклонило или отметило шаг.','Nothing to do for a normal user.','Обычному пользователю делать ничего не нужно.'],
 ['CHECKPOINT-','data','Saved statistics file check (CHECKPOINT-…)','Проверка файла сохранённой статистики (CHECKPOINT-…)','The saved statistics file failed a validation (wrong structure, number or date). It is not used and the previous good copy stays.','Файл сохранённой статистики не прошёл проверку (неверная структура, число или дата). Он не используется, остаётся прежняя исправная копия.','Nothing to do; if the statistics look empty, see Help → Dates are wrong or history is blocked.','Делать ничего не нужно; если статистика пустая, см. «Помощь» → «Неверные даты или история заблокирована».','CHECKPOINT-DAY: a day in the file does not exist, so the file was refused.','CHECKPOINT-DAY: в файле несуществующий день, поэтому файл отклонён.'],
 ['MIGRATION-','data','Settings upgrade check (MIGRATION-…)','Проверка обновления настроек (MIGRATION-…)','While moving settings from an older version, a check failed. Nothing was changed when a check fails.','При переносе настроек из старой версии не прошла проверка. Если проверка не пройдена, ничего не меняется.','Keep the settings backup and reinstall the same version; send the code to support.','Сохраните резервную копию настроек и переустановите ту же версию; отправьте код в поддержку.','MIGRATION-EXTERNAL-EDIT: someone edited the file by hand during the upgrade.','MIGRATION-EXTERNAL-EDIT: во время обновления кто-то правил файл вручную.'],
 ['HISTORY-','data','Controller history check (HISTORY-…)','Проверка истории контроллера (HISTORY-…)','The record of switches failed a check (size, order or checksum). The controller then refuses to act, because it cannot prove what it did before.','Запись о переключениях не прошла проверку (размер, порядок или контрольная сумма). Тогда контроллер отказывается действовать, потому что не может доказать, что делал раньше.','If it repeats, archive the history over SSH (Help → emergency return) and start again.','Если повторяется, заархивируйте историю по SSH («Помощь» → аварийный возврат) и начните заново.','HISTORY-CHECKSUM: the file was changed or damaged.','HISTORY-CHECKSUM: файл изменён или повреждён.'],
 ['LIFECYCLE-','service','Upgrade and service safety check (LIFECYCLE-…)','Проверка безопасности обновления и службы (LIFECYCLE-…)','Before an upgrade or a stop, the program checks that Auto is off and the original route is restored. One of the checks did not pass.','Перед обновлением или остановкой программа проверяет, что Auto выключен и исходный маршрут восстановлен. Одна из проверок не прошла.','Stop Auto on the Overview, wait for the return, then repeat.','Остановите Auto на «Обзоре», дождитесь возврата и повторите.','LIFECYCLE-STOP-AUTO-FIRST: Auto is still on.','LIFECYCLE-STOP-AUTO-FIRST: Auto всё ещё включён.'],
 ['SPEED-','speed','Speed test code (SPEED-…)','Код теста скорости (SPEED-…)','A speed test step reported this condition (network, limits, clock or the router’s load). Nothing else is affected.','Шаг теста скорости сообщил это состояние (сеть, лимиты, часы или нагрузка роутера). Остальное не затронуто.','Repeat later. If it repeats, check the VPN and the free space.','Повторите позже. Если повторяется, проверьте VPN и свободное место.','SPEED-DNS: the name of the test server could not be resolved through that VPN.','SPEED-DNS: имя тестового сервера не удалось найти через этот VPN.'],
 ['FAULT-','switch','Failure test code (FAULT-…)','Код теста сбоя (FAULT-…)','The failure test reported this condition.','Тест сбоя сообщил это состояние.','See the failure test panel on the Tests page.','См. панель теста сбоя на странице «Тесты».'],
 ['TELEGRAM-','telegram','Telegram code (TELEGRAM-…)','Код Telegram (TELEGRAM-…)','A Telegram step reported this condition.','Шаг Telegram сообщил это состояние.','Open the Telegram wizard; Help → Telegram reports do not arrive.','Откройте мастер Telegram; «Помощь» → «Отчёты в Telegram не приходят».'],
 ['SETUP-','setup','Settings code (SETUP-…)','Код настроек (SETUP-…)','A settings step reported this condition.','Шаг настроек сообщил это состояние.','Reload the page (Ctrl+F5) and repeat.','Обновите страницу (Ctrl+F5) и повторите.'],
 ['PRIORITY-','setup','Priorities code (PRIORITY-…)','Код приоритетов (PRIORITY-…)','A step of the server priorities reported this condition.','Шаг приоритетов серверов сообщил это состояние.','Reload and repeat.','Обновите и повторите.'],
 ['RECOVERY-','setup','Recovery rules code (RECOVERY-…)','Код правил восстановления (RECOVERY-…)','A step of the recovery rules reported this condition.','Шаг правил восстановления сообщил это состояние.','Reload and repeat.','Обновите и повторите.'],
 ['RPC-','service','Request to the router (RPC-…)','Запрос к роутеру (RPC-…)','A request from the page to the router was refused because of its form or size.','Запрос страницы к роутеру отклонён из-за вида или размера.','Reload the page (Ctrl+F5).','Обновите страницу (Ctrl+F5).'],
 ['SCAN-','speed','Check request code (SCAN-…)','Код запроса проверки (SCAN-…)','A step of the “Check the VPNs now” request reported this condition.','Шаг запроса «Проверить VPN сейчас» сообщил это состояние.','Make sure the monitor runs and press again.','Убедитесь, что мониторинг работает, и нажмите снова.'],
 ['DEPENDENCY-','service','Missing program (DEPENDENCY-…)','Не хватает программы (DEPENDENCY-…)','A program the monitor needs is missing on the router.','На роутере не хватает программы, нужной мониторингу.','Reinstall the package; Help → install.','Переустановите пакет; «Помощь» → установка.'],
 ['GUARD-','switch','Safety block code (GUARD-…)','Код защитной блокировки (GUARD-…)','The program’s safety block reported this condition.','Защитная блокировка программы сообщила это состояние.','Help → emergency return.','«Помощь» → аварийный возврат.'],
 ['POLICY-','switch','VPN rules code (POLICY-…)','Код VPN-правил (POLICY-…)','The VPN rules of the router are not as the program expects.','VPN-правила роутера не такие, как ожидает программа.','Do not edit the VPN rules while Auto works.','Не меняйте VPN-правила, пока Auto работает.'],
 ['JOURNAL-','switch','Switch journal code (JOURNAL-…)','Код журнала переключения (JOURNAL-…)','The saved record of the last switch failed a check.','Сохранённая запись последнего переключения не прошла проверку.','Help → emergency return (close-journal).','«Помощь» → аварийный возврат (close-journal).'],
 ['UNSAFE-','switch','Unsafe name (UNSAFE-…)','Небезопасное имя (UNSAFE-…)','A name from the router has odd characters; the program refuses to use it in a command.','Имя от роутера содержит странные символы; программа отказывается использовать его в команде.','Contact support with the code.','Обратитесь в поддержку с кодом.']
];
function errorFamilyOf(code){
  for(var i=0;i<ERROR_FAMILIES.length;i++)if(code.indexOf(ERROR_FAMILIES[i][0])===0)return ERROR_FAMILIES[i];
  return null;
}
function errorExamples(){
  var C=errorCodeLink;
  var items=[
    [[bi('You see ','Вы видите '),C('DNS-001'),bi(' next to a server.',' рядом с сервером.')],bi('The DNS check through this VPN did not obtain a validated answer. Some websites or direct HTTPS requests may still work. Repeat the check and inspect DNS, routing and filtering before changing or reconnecting a working profile.','DNS-проверка через этот VPN не получила подтверждённого ответа. Некоторые сайты или прямые HTTPS-запросы могут работать. Повторите проверку и изучите DNS, маршрутизацию и фильтрацию перед изменением или переподключением работающего профиля.')],
    [[bi('The history says ','В истории написано '),C('ROLLED-BACK'),bi(' beside ',' рядом с '),C('CLIENT-CONFIRMATION-TIMEOUT'),'.'],bi('A client-confirmed trial did not receive its required LAN witness in time. Check the confirmed current channel and recovery outcome in Overview. A prepared router-probed Auto session uses its own mode and does not require this external witness.','LAN-тест не получил требуемого подтверждения внешнего клиента вовремя. Проверьте подтверждённый текущий канал и результат восстановления в «Обзоре». Подготовленный Auto по пробам роутера работает в своём режиме и не требует такого внешнего подтверждения.')],
    [[bi('The state is ','Состояние '),C('COMMITTED'),bi(' and Overview says “Working on the reserve”.',' и в «Обзоре» «Работаю на резерве».')],bi('The reserve transition was confirmed under the selected proof mode. It may follow Auto or a manual command; this state alone does not explain the cause. Read the proof mode to distinguish router probes from an external LAN witness. Return depends on the saved policy and fresh channel evidence.','Переход на резерв подтверждён в выбранном режиме проверки. Он мог быть автоматическим или ручным; сам статус не объясняет причину. По обозначению режима различайте пробы роутера и подтверждение внешнего LAN-клиента. Возврат зависит от сохранённой политики и свежих проверок каналов.')],
    [[bi('The state is ','Состояние '),C('BLOCKED'),bi(' with ',' с '),C('HARDWARE-ACCELERATOR-UNVERIFIED'),'.'],[bi('The running acceleration state could not be confirmed safe. This does not prove acceleration is enabled. Open System readiness → Persistent router preparation and review the specific condition and offered action before changing settings. ','Безопасное текущее состояние ускорения не подтверждено. Это не доказывает, что ускорение включено. Откройте «Готовность системы → Постоянная подготовка роутера», изучите конкретное условие и предложенное действие перед изменением настроек. '),E('a',{'href':'#readiness'},bi('Open System readiness','Открыть «Готовность системы»'))]],
    [[bi('You see ','Вы видите '),C('EDGE-NOT-CERTIFIED'),bi(' beside a server.',' рядом с сервером.')],bi('This legacy planning code records a missing transition prerequisite. It does not establish whether the server works. Read current health and readiness for the selected Auto mode; use a LAN trial only when that mode requires it.','Этот код прежней прогнозной модели указывает на недостающее условие перехода. Он не определяет исправность сервера. Смотрите текущую доступность и готовность выбранного режима Auto; LAN-тест нужен только режиму, который его требует.')],
    [[bi('Telegram shows ','Telegram показывает '),C('TELEGRAM-REQUEST-REJECTED'),'.'],bi('Read the exact Telegram response: 401 usually concerns bot authorization. “chat not found” can mean an incorrect chat ID or missing access, including a private bot chat not yet started. The wizard explains how to check both; a generic 400 has other possible causes.','Смотрите точный ответ Telegram: 401 обычно относится к авторизации бота. «chat not found» может означать неверный Chat ID или отсутствие доступа, в том числе ещё не начатый личный чат с ботом. Мастер объясняет проверку этих условий; у общего кода 400 возможны и другие причины.')],
    [[bi('The Auto button answered ','Кнопка Auto ответила '),C('STOP-UNCONFIRMED'),'.'],bi('Stop could not be confirmed. Do not assume Auto or a fault test has stopped or that the original route was restored. Refresh the status and retry Stop; if recovery remains unconfirmed, follow the emergency recovery instructions in Help.','Остановка не подтверждена. Не считайте Auto или тест сбоя остановленными и не предполагайте, что исходный маршрут восстановлен. Обновите статус и повторите Stop; если восстановление остаётся неподтверждённым, следуйте инструкции аварийного восстановления в «Помощи».')]
  ];
  return E('details',{'class':'hv-errexamples','open':''},[E('summary',{},bi('How to read it: examples and evidence limits','Как читать: примеры и границы подтверждения')),E('ul',{},items.map(function(i){return E('li',{},[E('p',{},E('b',{},i[0])),E('p',{},i[1])]);})),E('p',{'class':'hv-muted'},bi('Codes describe recorded observations and prerequisites. Missing cause, scope or recovery proof stays unknown; a link opens the detailed explanation.','Коды описывают сохранённые наблюдения и условия. Недостающие причина, область проверки или подтверждение восстановления остаются неизвестными; ссылка открывает подробную расшифровку.'))]);
}

/* Table of diagnostic codes for the Events page: code, name, meaning and a collapsed "how to fix".
   Row: [code, group, name EN, name RU, meaning EN, meaning RU, fix EN, fix RU]. Codes and technical terms stay English. */
var ERROR_GROUPS=[['monitor',['Monitoring checks','Проверки мониторинга']],['switch',['Switching and Auto','Переключение и Auto']],['service',['Monitor service and page','Служба мониторинга и страница']],['helper',['LAN helper','LAN-помощник']],['telegram',['Telegram','Telegram']],['setup',['Settings and wizards','Настройки и мастера']],['speed',['Speed tests and scans','Тесты скорости и сканирование']],['data',['Data, clock and history','Данные, часы и история']]];
var ERROR_ROWS=[
 ["CLIENT-CONTROL-PATH-MISMATCH", "helper", "Management route uses another interface", "Управление идёт через другой интерфейс", "The OS management route differs from the selected client witness, for example when two routers share the same private subnet.", "Путь управления ОС отличается от выбранного интерфейса проверки, например при одинаковой подсети двух роутеров.", "The helper refuses before credentials/session are sent. Establish the target identity and an unambiguous management path; do not change host networking automatically.", "Помощник отказывает до отправки пароля/сессии. Подтвердите идентичность и однозначный путь управления; не меняйте сеть компьютера автоматически."],
 ["WAN-001", "monitor", "Internet is down at the router", "Нет интернета на роутере", "The router itself cannot reach the internet, not only the VPN.", "Сам роутер не достаёт до интернета, а не только VPN.", "Inspect independent WAN, DNS and VPN evidence before blaming the provider. A modem restart is a separate deliberate action, not an automatic application fix.", "Сначала различите WAN, DNS и VPN по независимым данным. Перезапуск модема — отдельное осознанное действие, а не автоматическое исправление приложения."],
 ["DNS-001", "monitor", "DNS check did not pass", "DNS-проверка не прошла", "The control DNS query through this VPN did not produce a validated answer. Other DNS paths, cached names or direct HTTPS may still work; the code alone does not identify the cause.", "Контрольный DNS-запрос через этот VPN не дал подтверждённого ответа. Другой DNS, кэшированные имена или прямые HTTPS-запросы могут работать; сам код не устанавливает причину.", "Repeat the check and inspect the saved DNS/HTTPS results, resolver reachability, routing and filtering. Coordinate any profile restart with managed Auto Stop/recovery.", "Повторите проверку и изучите сохранённые результаты DNS/HTTPS, доступность DNS-сервера, маршрутизацию и фильтрацию. Перезапуск профиля согласуйте со штатным Stop/восстановлением Auto."],
 ["VPN-001", "monitor", "VPN did not connect", "VPN не подключился", "The VPN connection could not be established. The cause may stay unknown.", "Не удалось установить соединение VPN. Причина может остаться неизвестной.", "Inspect the exact tunnel/credential/endpoint failure. Before editing or reconnecting stock profiles, complete managed Stop/recovery; do not restart a working client just to change its status.", "Изучите точный отказ туннеля/доступа/сервера. До правки или переподключения штатного профиля завершите управляемый Stop/восстановление; не перезапускайте рабочий клиент ради статуса."],
 ['VPN-002','monitor','VPN login rejected','VPN отклонил вход','The VPN server rejected the login or the key.','VPN-сервер отклонил логин или ключ.','Open the profile in GL.iNet and re-enter the login and password or import the config again. Check that the subscription is active.','Откройте профиль в GL.iNet и заново введите логин и пароль или импортируйте конфиг. Проверьте, что подписка активна.'],
 ['VPN-003','monitor','HTTPS availability below threshold','Недостаточно успешных HTTPS-проверок','Fewer than two of three HTTPS checks succeeded through the connected VPN. Some traffic may still pass. This code alone does not establish complete loss of Internet access.','Через подключённый VPN успешно прошли менее двух из трёх HTTPS-проверок. Часть трафика может проходить. Сам код не доказывает полное отсутствие доступа в Интернет.','Read the saved HTTPS success count, DNS result and endpoint details. Retry the check; investigate repeated failures before reconnecting a working VPN.','Посмотрите сохранённое число успешных HTTPS-проверок, результат DNS и сведения об адресах проверки. Повторите проверку; перед переподключением работающего VPN выясните причину повторяющихся сбоев.'],
 ['VPN-004','monitor','VPN server name does not resolve','Имя VPN-сервера не находится','The name of the VPN server cannot be resolved to an address.','Имя VPN-сервера не удаётся превратить в адрес.','Check DNS on the router and the server name in the profile. Use the server IP address if the provider gives one.','Проверьте DNS на роутере и имя сервера в профиле. Если провайдер даёт IP-адрес сервера, используйте его.'],
 ['TLS-001','monitor','Certificate check failed','Ошибка проверки сертификата','The HTTPS certificate was not accepted. The program never turns the check off by itself.','Сертификат HTTPS не принят. Программа никогда не отключает проверку сама.','Check the router date and time (a wrong clock breaks certificates) and that the package ca-bundle is installed.','Проверьте дату и время на роутере (неверные часы ломают сертификаты) и что установлен пакет ca-bundle.'],
 ['ROUTE-001','monitor','Traffic goes another way','Трафик идёт другим путём','The real route differs from the selected one.','Реальный маршрут отличается от выбранного.','Open GL.iNet → VPN Dashboard and check the order of the VPN rules. Do not change rules while Auto is working.','Откройте GL.iNet → VPN Dashboard и проверьте порядок правил VPN. Не меняйте правила, пока работает Auto.'],
 ['CHECK-001','monitor','Check not confirmed','Проверка не подтверждена','There is not enough evidence yet; the state stays “unknown”. It is shown while a VPN is still being checked.','Пока недостаточно данных; состояние остаётся «неизвестно». Показывается, пока VPN ещё проверяется.','Wait one or two check intervals. If it stays, press “Check the VPNs now” on the Overview.','Подождите один-два интервала проверки. Если не проходит, нажмите «Проверить VPN сейчас» на «Обзоре».'],
 ['SWITCH-001','switch','No ready reserve','Нет готового резерва','There is no reserve VPN that passed its checks, so there is nowhere to switch.','Нет резервного VPN, прошедшего проверки, поэтому переключаться некуда.','Connect another VPN profile in GL.iNet and select it as the reserve in Settings → All application settings → 3 · Existing VPNs.','Подключите ещё один VPN-профиль в GL.iNet и выберите его резервным в «Настройки → Все настройки приложения → 3 · Существующие VPN».'],
['AUTO-CONTROL-UNVERIFIED','switch','Auto request not confirmed','Запрос Auto не подтверждён','The router answered, but not with a clear “accepted”. Nothing is assumed.','Роутер ответил, но не ясным «принято». Ничего не предполагается.','Look at the lamp and the Technical state in the Auto card; repeat the press only if nothing changed after a minute.','Посмотрите на лампу и «Техническое состояние» в блоке Auto; повторите нажатие, только если за минуту ничего не изменилось.'],
 ['AUTO-CONTROL-FAILED','switch','Auto request got no answer','Запрос Auto остался без ответа','The router did not answer the Start or Stop request at all.','Роутер вообще не ответил на запрос «Включить» или «Выключить».','Reload the page and check the monitor lamp. If the router is unreachable, use the emergency return in Help.','Обновите страницу и проверьте лампу мониторинга. Если роутер недоступен, используйте аварийный возврат из «Помощи».'],
 ["AUTO-START-REFUSED", "switch", "Auto start refused", "Запуск Auto отклонён", "The router refused to start Auto; the reasons are listed with their codes.", "Роутер отказался запускать Auto; причины перечислены с кодами.", "Read the current mode-specific blockers. Prepared continuous mode uses its own router evidence; only a client-confirmed trial requires its matching LAN certificate. Repeated clicks do not repair prerequisites.", "Прочитайте текущие причины своего режима. Подготовленный непрерывный режим использует собственные данные роутера; соответствующий LAN-сертификат нужен клиентскому тесту. Повторные нажатия не исправляют условия."],
 ['ROLLBACK-GIVEN-UP','switch','Automatic return stopped','Автоматический возврат остановлен','The return to the primary failed twice. The program stopped trying, keeps only VPN traffic allowed and turned Auto off.','Возврат на основной не удался дважды. Программа перестала пытаться, пропускает только трафик через VPN и выключила Auto.','Check the VPN rule order in the router (Help → emergency return), restore it by hand, then close the journal with the emergency command.','Проверьте порядок VPN-правил на роутере («Помощь» → аварийный возврат), восстановите его вручную и закройте журнал аварийной командой.'],
  ['EXIT-TRACE-FAILED','switch','Exit address could not be read','Не удалось прочитать внешний адрес','The check of the address the internet sees through the VPN got no clear answer (cut, garbled or not IPv4). Nothing is switched on such an answer.','Проверка адреса, который видит интернет через VPN, не получила ясного ответа (оборван, искажён или не IPv4). По такому ответу ничего не переключается.','Usually temporary. If it repeats, check the VPN server and that IPv4 works through it.','Обычно временно. Если повторяется, проверьте VPN-сервер и что через него работает IPv4.'],
 ['STOP-UNCONFIRMED','switch','Stop not confirmed','Остановка не подтверждена','The Stop request could not be saved on the router. A running failure test was still cleaned up.','Запрос остановки не удалось сохранить на роутере. Запущенный тест сбоя всё равно убран.','Press Stop again. If it repeats, use the emergency return in Help, or stop the service in System → Startup.','Нажмите «Стоп» ещё раз. Если повторяется, используйте аварийный возврат из «Помощи» или остановите службу в «Система» → «Автозапуск».'],
 ["SWITCH-002", "switch", "Internet not restored after the switch", "Интернет не вернулся после переключения", "The switch was applied but the following checks failed.", "Переключение выполнено, но последующие проверки не прошли.", "Inspect the recovery result and both paths. A requested rollback is not confirmed restoration; do not start another test until the current state is understood.", "Проверьте итог восстановления и оба пути. Запрошенный откат не является подтверждённым возвратом; не начинайте другой тест до выяснения текущего состояния."],
 ['SWITCH-003','switch','Switch could not be applied','Переключение не удалось применить','The route change itself failed (not the same as SWITCH-002).','Сама смена маршрута не удалась (это не то же самое, что SWITCH-002).','Open Help → “The router stays on the reserve VPN” and check the VPN rule order in GL.iNet.','Откройте «Помощь» → «Роутер остаётся на резервном VPN» и проверьте порядок правил VPN в GL.iNet.'],
 ["CONFIG-001", "switch", "Automation paused after manual change", "Автоматика на паузе после ручного изменения", "Someone changed the VPN settings by hand, so automation stepped aside.", "Кто-то изменил настройки VPN вручную, поэтому автоматика отошла в сторону.", "Inspect the external edit and actual cleanup result. Revalidate identities/policy for the selected mode; do not impose a LAN trial on prepared router-probed mode or compete with the operator edit.", "Изучите внешнюю правку и фактическую очистку. Перепроверьте идентичность/политику своего режима; не навязывайте LAN-тест подготовленному router-probed режиму и не конкурируйте с правкой оператора."],
 ['SYSTEM-001','service','Unsupported firmware or missing tool','Неподдерживаемая прошивка или нет программы','The firmware version or a required tool is not supported.','Версия прошивки или нужная программа не поддерживается.','Compare with the tested firmware (GL.iNet 4.11.0) on the Readiness page. Monitoring still works; Auto needs the supported firmware.','Сравните с проверенной прошивкой (GL.iNet 4.11.0) на странице «Готовность системы». Мониторинг работает, а для Auto нужна поддерживаемая прошивка.'],
 ['MONITOR-START-REQUESTED','service','Start requested','Запуск запрошен','The monitor was switched on. This is not yet proof that it runs.','Мониторинг включён. Это ещё не доказательство, что он работает.','Wait up to a minute for fresh data; the traffic light turns green.','Подождите до минуты свежих данных; светофор станет зелёным.'],
 ['MONITOR-STOP-REQUESTED','service','Stop requested','Остановка запрошена','The monitor was asked to stop.','Мониторингу отправлена команда остановиться.','Nothing to do. It does not mean the internet recovered.','Делать ничего не нужно. Это не значит, что интернет восстановился.'],
 ['MONITOR-STOP-AUTO-FIRST','service','Stop Auto first','Сначала остановите Auto','Auto or a retained reserve prevents stopping the monitor.','Auto или удерживаемый резерв мешают остановить мониторинг.','Press Stop on Auto, wait until it returns to the primary, then stop the monitor.','Нажмите «Стоп» у Auto, дождитесь возврата на основной, затем остановите мониторинг.'],
 ['MONITOR-JOURNAL-UNVERIFIED','service','Journal cannot be read','Журнал не читается','The transaction journal is damaged or unreadable.','Журнал транзакций повреждён или не читается.','Do not delete it. Follow Help → “I have no internet” and router-test-kit/EMERGENCY.md.','Не удаляйте его. Следуйте «Помощи» → «У меня пропал интернет» и router-test-kit/EMERGENCY.md.'],
 ['MONITOR-SAVE-FAILED','service','Setting not saved','Настройка не сохранилась','The router did not confirm the saved setting.','Роутер не подтвердил сохранение настройки.','Try again. If it repeats, check free space (df -h /etc) and the system log (logread).','Повторите. Если снова, проверьте свободное место (df -h /etc) и системный журнал (logread).'],
 ['MONITOR-SERVICE-UNCONFIRMED','service','Service change not confirmed','Смена состояния службы не подтверждена','The setting may be saved but the service did not confirm the start or stop.','Настройка могла сохраниться, но служба не подтвердила запуск или остановку.','After a minute check the Monitoring block on the Overview; if its lamp is not green, press “Start monitoring” there.','Через минуту посмотрите блок «Мониторинг» на «Обзоре»; если лампа не зелёная, нажмите там «Запустить мониторинг».'],
 ['MONITOR-INVALID','service','Invalid request','Неверный запрос','The request had wrong fields. Nothing was written.','В запросе неверные поля. Ничего не записано.','Reload the page (Ctrl+F5). If it repeats, the page and the program versions differ: see the notice on the Overview.','Обновите страницу (Ctrl+F5). Если повторяется, версии страницы и программы различаются: см. сообщение на «Обзоре».'],
 ['MONITOR-RPC-UNCONFIRMED','service','No confirmed answer','Нет подтверждённого ответа','The browser did not get a confirmed answer from the router.','Браузер не получил подтверждённого ответа от роутера.','Reload the status. Do not assume the monitor stopped.','Обновите статус. Не считайте, что мониторинг остановился.'],
 ['RPC-UNAVAILABLE','service','Router does not answer','Роутер не отвечает','The page cannot get the status from the router; old values are shown.','Страница не получает статус от роутера; показаны старые значения.','Reload the page and sign in to LuCI again. Then Help → “The page is old, empty or says the monitor is not running”.','Обновите страницу и войдите в LuCI снова. Затем «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'],
 ['STATUS-STALE','service','Status is old','Статус устарел','The monitor is switched on but its data is older than 90 seconds.','Мониторинг включён, но его данные старше 90 секунд.','Wait a minute and reload the page; if the lamp is red press “Start monitoring” in the Monitoring block. If it stays, see Help → “The page is old, empty or says the monitor is not running”.','Подождите минуту и обновите страницу; если лампа красная, нажмите «Запустить мониторинг» в блоке «Мониторинг». Если не помогло, см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».'],
 ['RPC-PLUGIN','service','Program plugin missing','Нет модуля программы','The plugin that connects the page to the program is missing on the router.','На роутере нет модуля, который связывает страницу с программой.','Reinstall the package (opkg install) and sign out of LuCI and in again.','Переустановите пакет (opkg install) и выйдите из LuCI и войдите снова.'],
 ['RPC-INPUT-SIZE','service','Request too large','Слишком большой запрос','The request was rejected because it was too large or too complex.','Запрос отклонён: он слишком большой или сложный.','Reload the page and repeat. This normally does not happen with the standard page.','Обновите страницу и повторите. С обычной страницей этого не бывает.'],
 ['CLIENT-CABLE-LINK-DOWN','helper','Cable adapter is down','Кабельный адаптер не подключён','The cable adapter you chose is not up.','Выбранный кабельный адаптер не поднят.','Plug the cable into a LAN port of the router and run the helper again with the right adapter number (Get-NetAdapter).','Вставьте кабель в LAN-порт роутера и запустите помощника снова с правильным номером адаптера (Get-NetAdapter).'],
 ["CLIENT-CABLE-ADDRESS-AMBIGUOUS", "helper", "Cable IPv4 address is ambiguous", "Неоднозначный IPv4-адрес кабеля", "The selected cable has no single preferred IPv4 address.", "На выбранном кабеле нет единственного предпочтительного IPv4-адреса.", "Inspect the real LAN subnet and adapter addresses read-only; the factory 192.168.8.x example is not universal.", "Проверьте реальную LAN-подсеть и адреса адаптера только чтением; заводской пример 192.168.8.x не универсален."],
 ["CLIENT-CABLE-NOT-LOCAL", "helper", "Selected cable does not reach this router locally", "Выбранный кабель не ведёт к роутеру локально", "The explicit cable route to the management address is not a direct local path.", "Явно выбранный кабельный маршрут к адресу управления не является прямым локальным путём.", "Verify the correct router, cable and subnet. Do not automatically disable Wi-Fi or alter computer routes.", "Проверьте нужный роутер, кабель и подсеть. Не отключайте Wi-Fi и не меняйте маршруты компьютера автоматически."],
 ["CLIENT-CABLE-PROBE-ROUTE-MISMATCH", "helper", "Cable probe route differs", "Маршрут кабельной проверки не совпадает", "The chosen interface cannot route the probe destinations through the expected router.", "Выбранный интерфейс не направляет проверочные запросы через ожидаемый роутер.", "Inspect interface/gateway ownership. The current helper creates no temporary routes; do not delete unrelated routes to bypass this refusal.", "Изучите интерфейс и владельца шлюза. Текущий помощник не создаёт временных маршрутов; не удаляйте посторонние маршруты ради обхода отказа."],
 ["CLIENT-CABLE-HTTPS-FAILED", "helper", "Bound HTTPS check failed", "Привязанная HTTPS-проверка не прошла", "The source-bound HTTPS requests through the selected cable did not succeed.", "HTTPS-запросы с привязкой к выбранному кабелю не завершились успешно.", "Inspect router health, actual route and competing client software. Any host-network correction is a separate deliberate action, not an automatic helper repair.", "Проверьте роутер, фактический маршрут и программы клиента. Исправление сети компьютера — отдельное осознанное действие, а не автоматический ремонт помощником."],
 ["CLIENT-GATEWAY-MISMATCH", "helper", "Client path uses another gateway", "Клиентский путь использует другой шлюз", "The observed default client path is not through the named router.", "Наблюдаемый обычный путь клиента не проходит через указанный роутер.", "Verify the intended network and interface, or choose an explicit cable witness. Do not silently stop another VPN or change its routes.", "Проверьте нужную сеть и интерфейс либо выберите явную кабельную проверку. Не останавливайте другой VPN и не меняйте его маршруты незаметно."],
 ['CLIENT-DNS-CONFIG-UNVERIFIED','helper','DNS settings unverified','Настройки DNS не подтверждены','The computer uses a DNS server other than the router.','Компьютер использует DNS-сервер, отличный от роутера.','Set the DNS of the computer to automatic (from the router) for the test.','Установите DNS на компьютере автоматически (от роутера) на время теста.'],
 ["CLIENT-IPV6-DEFAULT-UNVERIFIED", "helper", "IPv6 route unverified", "Маршрут IPv6 не подтверждён", "The computer has an IPv6 default route that the helper cannot verify.", "У компьютера есть маршрут IPv6 по умолчанию, который помощник не может проверить.", "This witness has not excluded another IPv6 path. Preserve its current settings and choose a supported explicit IPv4 witness or a separately authorized correction; the helper does not disable IPv6.", "Эта проверка не исключила другой IPv6-путь. Сохраните текущие настройки и выберите поддерживаемую явную IPv4-проверку либо отдельно разрешённую коррекцию; помощник не отключает IPv6."],
 ["CLIENT-PROBE-ROUTE-CONFLICT", "helper", "Legacy probe-route conflict", "Конфликт проверочных маршрутов старой версии", "This code belongs to an older route-adding helper; the current helper is route-free.", "Код относится к старому помощнику, добавлявшему маршруты; текущий маршруты не создаёт.", "Read the current route owners and preserve evidence. Remove an old owned route only as a separately verified cleanup; never delete arbitrary routes.", "Изучите владельцев маршрутов и сохраните данные. Удаляйте старый собственный маршрут лишь после отдельной проверки; не удаляйте произвольные маршруты."],
 ['CLIENT-CANCELLED','helper','Cancelled','Отменено','You did not type TEST, so the trial did not start.','Вы не ввели TEST, поэтому тест не начался.','Run again and type TEST only when you are ready for a short interruption.','Запустите снова и вводите TEST, только когда готовы к короткому разрыву.'],
 ['CLIENT-TRIAL-UNCONFIRMED','helper','Trial not confirmed','Тест не подтверждён','The router did not get a valid confirmation from the computer in time.','Роутер не получил вовремя верное подтверждение от компьютера.','The router returned to the previous route. Check the cable and run again.','Роутер вернулся на прежний маршрут. Проверьте кабель и запустите снова.'],
 ['CLIENT-RESERVE-NOT-VERIFIED','helper','Reserve not verified','Резерв не подтверждён','The computer did not see the reserve VPN exit.','Компьютер не увидел выход через резервный VPN.','Check that the reserve VPN really works (Overview) and try again.','Проверьте, что резервный VPN действительно работает («Обзор»), и повторите.'],
 ['POWERSHELL-7-REQUIRED','helper','PowerShell 7 needed','Нужен PowerShell 7','The helper needs PowerShell 7 (pwsh).','Помощнику нужен PowerShell 7 (pwsh).','Install it: winget install Microsoft.PowerShell, then start the helper with pwsh.','Установите: winget install Microsoft.PowerShell, затем запускайте помощника через pwsh.'],
 ['PRIVATE-LAN-ROUTER-REQUIRED','helper','Router address is not private','Адрес роутера не частный','The helper accepts only a private LAN address.','Помощник принимает только частный адрес локальной сети.','Use the router address such as http://192.168.8.1:8080/.','Укажите адрес роутера вида http://192.168.8.1:8080/.'],
 ['TELEGRAM-TOKEN-REQUIRED','telegram','Bot token missing','Нет токена бота','No bot token is stored.','Токен бота не сохранён.','Enter the token in Settings → 2 · Telegram (see Help → “Telegram reports do not arrive”).','Введите токен в «Настройки» → «2 · Telegram» (см. «Помощь» → «Отчёты в Telegram не приходят»).'],
 ['TELEGRAM-TOKEN-FORMAT','telegram','Token looks wrong','Токен выглядит неверно','The token does not have the form 123456789:AAH… .','Токен не похож на 123456789:AAH….','Copy the whole token from @BotFather again, without spaces.','Скопируйте токен из @BotFather заново целиком, без пробелов.'],
 ['TELEGRAM-TOKEN-REJECTED','telegram','Token rejected by Telegram','Telegram отклонил токен','Telegram says the token is not valid.','Telegram сообщает, что токен недействителен.','Create a new token in @BotFather (/token) and enter it again.','Создайте новый токен в @BotFather (/token) и введите заново.'],
 ['TELEGRAM-DESTINATION-FORMAT','telegram','Chat ID looks wrong','ID чата выглядит неверно','The chat ID has a wrong form.','У ID чата неверный вид.','Use digits (123456789, or -100… for a group) or @channel_name.','Используйте цифры (123456789 или -100… для группы) или @имя_канала.'],
 ['TELEGRAM-PERMISSION','telegram','Bot cannot write there','Бот не может туда писать','The bot has no right to write to this chat.','У бота нет права писать в этот чат.','Press Start in the bot chat, or make the bot an administrator of the group/channel.','Нажмите Start в чате с ботом или сделайте бота администратором группы/канала.'],
 ['TELEGRAM-RATE-LIMIT','telegram','Too many messages','Слишком много сообщений','Telegram asks to wait before the next message.','Telegram просит подождать перед следующим сообщением.','Wait; the program retries by itself. Use a longer report interval.','Подождите; программа повторит сама. Поставьте более длинный интервал отчётов.'],
 ['TELEGRAM-DNS','telegram','Telegram address not found','Адрес Telegram не найден','The router cannot resolve the Telegram address.','Роутер не может найти адрес Telegram.','Check the internet and DNS on the router.','Проверьте интернет и DNS на роутере.'],
 ['TELEGRAM-TLS','telegram','Secure connection failed','Защищённое соединение не удалось','The secure connection to Telegram failed.','Защищённое соединение с Telegram не удалось.','Check the router date and time and the ca-bundle package.','Проверьте дату и время на роутере и пакет ca-bundle.'],
 ['TELEGRAM-DELIVERY-UNKNOWN','telegram','Delivery not confirmed','Доставка не подтверждена','A report was sent but Telegram did not confirm it.','Отчёт отправлен, но Telegram не подтвердил доставку.','Check the chat. The program does not send a duplicate automatically.','Проверьте чат. Программа не отправляет дубликат автоматически.'],
 ['TELEGRAM-DELIVERED','telegram','Delivered','Доставлено','A report was delivered.','Отчёт доставлен.','Nothing to do.','Делать ничего не нужно.'],
 ['TELEGRAM-TEST-DELIVERED','telegram','Test delivered','Тест доставлен','The test message was delivered.','Тестовое сообщение доставлено.','Nothing to do.','Делать ничего не нужно.'],
 ['TELEGRAM-CONFIG','telegram','Telegram setup incomplete','Настройка Telegram неполная','The Telegram settings are incomplete or invalid.','Настройки Telegram неполные или неверные.','Open Settings → 2 · Telegram and fill in the token and the chat ID again.','Откройте «Настройки» → «2 · Telegram» и заполните токен и ID чата заново.'],
 ['TELEGRAM-CLOCK-BACKWARD','telegram','Clock went back','Часы пошли назад','The router clock went back, so reports are paused.','Часы роутера пошли назад, поэтому отчёты приостановлены.','Check the router date and time (NTP).','Проверьте дату и время роутера (NTP).'],
 ['TELEGRAM-STATE-CORRUPT','telegram','Report state damaged','Состояние отчётов повреждено','The saved report state is damaged.','Сохранённое состояние отчётов повреждено.','The program recovers it by itself; save the Telegram settings again if it stays.','Программа восстанавливает его сама; если не прошло, сохраните настройки Telegram заново.'],
 ['SETUP-INVALID','setup','Invalid input','Неверный ввод','A wizard field has an invalid value.','В поле мастера неверное значение.','Correct the highlighted fields and review again.','Исправьте выделенные поля и проверьте ещё раз.'],
 ['SETUP-RANGE','setup','Value out of range','Значение вне диапазона','A number is outside the allowed range.','Число вне допустимого диапазона.','Use a value inside the range shown next to the field.','Укажите значение в диапазоне, показанном рядом с полем.'],
 ['SETUP-SAVE-FAILED','setup','Settings not saved','Настройки не сохранены','The router did not confirm the saved settings.','Роутер не подтвердил сохранение настроек.','Try again. Check free space and the log (logread) if it repeats.','Повторите. Если снова, проверьте свободное место и журнал (logread).'],
 ['SETUP-STOP-FIRST','setup','Stop Auto first','Сначала остановите Auto','The change is not allowed while Auto is running.','Изменение недопустимо, пока работает Auto.','Stop Auto, wait for the return to the primary, then change the settings.','Остановите Auto, дождитесь возврата на основной и меняйте настройки.'],
 ['SETUP-SAVE-UNCONFIRMED','setup','Save not confirmed','Сохранение не подтверждено','The router did not answer the save in time. The change may or may not have been written.','Роутер не ответил на сохранение вовремя. Изменение могло записаться, а могло и нет.','Reload the page and look at the setting. If it is wrong, save again. If the router reports unsaved changes, see Help.','Обновите страницу и посмотрите настройку. Если она неверная, сохраните ещё раз. Если роутер сообщает о несохранённых изменениях, см. «Помощь».'],
 ['SETUP-PENDING-DELTA','setup','Unsaved router changes','Есть несохранённые изменения роутера','The router has uncommitted changes of this program’s settings.','На роутере есть неприменённые изменения настроек этой программы.','Open LuCI → Unsaved changes and apply or revert them, then repeat.','Откройте LuCI → «Несохранённые изменения», примените или отмените их и повторите.'],
 ['SETUP-PRIMARY-RESERVE-DISABLED','setup','Primary or reserve is off','Основной или резервный отключён','The chosen primary or reserve profile is not enabled for monitoring.','Выбранный основной или резервный профиль не включён для наблюдения.','Enable both profiles in the System wizard.','Включите оба профиля в мастере «Система».'],
 ['SETUP-PROFILES','setup','Profiles not found','Профили не найдены','A selected profile no longer exists on the router.','Выбранного профиля больше нет на роутере.','Choose existing profiles again in the System wizard.','Выберите существующие профили заново в мастере «Система».'],
 ['SPEED-DISABLED','speed','Speed tests are off','Тесты скорости выключены','Speed tests are switched off.','Тесты скорости выключены.','Turn them on in Advanced settings → Tests → Speed test settings.','Включите их в «Расширенные настройки» → «Тесты» → «Настройки тестов скорости».'],
 ['SPEED-DAILY-LIMIT','speed','Daily quota used','Суточная квота исчерпана','The daily data quota for tests is used up.','Суточная квота данных для тестов исчерпана.','Wait for tomorrow or raise the quota in the speed test settings.','Дождитесь завтра или увеличьте квоту в настройках тестов скорости.'],
 ['SPEED-COOLDOWN','speed','Please wait','Нужна пауза','A test of this server ran recently.','Этот сервер тестировали недавно.','Try again later.','Повторите позже.'],
 ['SPEED-BUSY','speed','Another test is running','Уже идёт другой тест','Another test is running.','Уже выполняется другой тест.','Wait until it finishes or cancel it.','Дождитесь его окончания или отмените.'],
 ['SPEED-TRAFFIC-BUSY','speed','VPN is busy','VPN сейчас занят','The VPN carries more traffic than the limit, so the test was skipped.','Через VPN идёт трафика больше лимита, поэтому тест пропущен.','Run the test when the VPN is less busy or raise the limit.','Запустите тест, когда VPN менее загружен, или поднимите лимит.'],
 ['SPEED-ROUTE-UNVERIFIED','speed','Test route unverified','Путь теста не подтверждён','It is not proven that the test goes through the chosen VPN.','Не доказано, что тест идёт через выбранный VPN.','Make sure the VPN is connected and try again.','Убедитесь, что VPN подключён, и повторите.'],
 ['SPEED-PROFILE-INACTIVE','speed','VPN not connected','VPN не подключён','The VPN to test is not connected.','VPN для теста не подключён.','Connect the profile in GL.iNet first; this program never connects VPNs.','Сначала подключите профиль в GL.iNet; эта программа VPN не подключает.'],
 ['SPEED-NETWORK','speed','Test network error','Сетевая ошибка теста','The test could not connect.','Тесту не удалось соединиться.','Check the VPN and the internet and try again.','Проверьте VPN и интернет и повторите.'],
 ['SPEED-CANCELLED','speed','Cancelled','Отменено','The test was cancelled.','Тест отменён.','Nothing to do.','Делать ничего не нужно.'],
 ['SCAN-DEADLINE-EXCEEDED','speed','Check took too long','Проверка заняла слишком много времени','The “Check the VPNs now” request did not finish in time.','Запрос «Проверить VPN сейчас» не завершился вовремя.','Press the button again after a minute. Check that the monitor is running.','Нажмите кнопку ещё раз через минуту. Проверьте, что мониторинг работает.'],
 ['SCAN-STATE-CORRUPT','speed','Check state damaged','Состояние проверки повреждено','The saved state of the check is damaged.','Сохранённое состояние проверки повреждено.','Press “Check the VPNs now” again; it creates a new state.','Нажмите «Проверить VPN сейчас» ещё раз; создастся новое состояние.'],
 ['CLOCK-001','data','Wrong router date','Неверная дата на роутере','The router date is impossible or jumped.','Дата роутера невозможна или скачет.','Set the time zone and enable NTP in LuCI → System → System. Statistics wait for a correct clock.','Задайте часовой пояс и включите NTP в LuCI → «Система» → «Система». Статистика ждёт верных часов.'],
 ["HISTORY-001", "data", "History unavailable", "История недоступна", "The saved controller history cannot be read.", "Сохранённую историю контроллера не удаётся прочитать.", "Preserve primary/backup history and inspect checksums, clock, permissions and storage. Do not delete it or promise an automatic fresh history; corrupt recovery evidence can block switching.", "Сохраните основной/резервный журнал и проверьте checksum, время, права и хранилище. Не удаляйте его и не обещайте автоматическое создание новой истории; повреждённые данные восстановления могут блокировать переходы."],
 ['FAULT-CERTIFIED-AUTO-REQUIRED','switch','Transition test needs running Auto','Для теста перехода нужен работающий Auto','The test needs fresh confirmation of the current channel and a healthy alternative. Prepared continuous pair Auto uses its own private state; the legacy bounded mode still needs its LAN certificate.','Тесту нужны свежие подтверждения текущего канала и исправного второго. Подготовленный непрерывный Auto использует собственное закрытое состояние; прежнему ограниченному режиму по-прежнему нужен LAN-сертификат.','Check both VPN channels and start Auto on Overview. Reopen the transition test after fresh observations arrive.','Проверьте оба VPN и включите Auto на «Обзоре». Вернитесь к тесту перехода после свежих наблюдений.'],
 ['FAULT-UNVERIFIED','switch','Failure test not confirmed','Сбой не подтверждён','The router did not confirm that the simulated failure was applied or removed.','Роутер не подтвердил, что имитация сбоя применена или снята.','Press “Cancel fault now”, check the Overview that traffic works, then try again.','Нажмите «Отменить сбой сейчас», проверьте на «Обзоре», что трафик идёт, и повторите.'],
 ['FAULT-UNKNOWN','switch','Failure test result unknown','Итог теста сбоя неизвестен','The result of the failure request is unknown.','Итог запроса на сбой неизвестен.','Reload the page. If the VPN has no traffic, press “Cancel fault now”.','Обновите страницу. Если через VPN нет трафика, нажмите «Отменить сбой сейчас».'],
 ['FAULT-CANCEL-UNKNOWN','switch','Cancel not confirmed','Отмена не подтверждена','The cancel request was sent but not confirmed.','Запрос на отмену отправлен, но не подтверждён.','Check the Tests page after a minute. The failure also ends by itself when its time is over (a timeout in the router).','Проверьте страницу «Тесты» через минуту. Сбой также заканчивается сам по истечении времени (таймаут в роутере).'],
 ['FAULT-RPC-UNCONFIRMED','switch','No answer from the router','Нет ответа от роутера','The page did not get a confirmed answer to the failure request.','Страница не получила подтверждённого ответа на запрос сбоя.','Reload the page and look at the state of the test before repeating.','Обновите страницу и посмотрите состояние теста, прежде чем повторять.'],
 ['FAULT-FIELDS','switch','Invalid request','Неверный запрос','The failure request had wrong fields.','В запросе сбоя неверные поля.','Reload the page (Ctrl+F5) and try again.','Обновите страницу (Ctrl+F5) и повторите.'],
 ["FAULT-HISTORY-UNAVAILABLE", "data", "Failure history unavailable", "История сбоев недоступна", "The saved history of failure tests cannot be read.", "Сохранённую историю тестов сбоя не удаётся прочитать.", "Keep the stored fault-history files and inspect read/write/integrity errors. Cleanup and test outcome must be checked separately; a new history is not guaranteed automatically.", "Сохраните файлы истории тестов и проверьте чтение/запись/целостность. Очистка и итог теста проверяются отдельно; новая история сама по себе не гарантируется."],
 ['FAULT-STATE-CORRUPT','switch','Failure state damaged','Состояние сбоя повреждено','The saved state of a failure test is damaged.','Сохранённое состояние теста сбоя повреждено.','Press “Cancel fault now”; the program cleans up its own traffic rule.','Нажмите «Отменить сбой сейчас»; программа уберёт собственное правило трафика.'],
 ['FAULT-NFT-QUERY-FAILED','switch','Cannot read the firewall rule','Не удаётся прочитать правило межсетевого экрана','The router did not answer a query about the program’s own temporary rule.','Роутер не ответил на запрос о собственном временном правиле программы.','Wait for the timeout of the test (up to 3 minutes) and try again; nothing else is changed.','Дождитесь таймаута теста (до 3 минут) и повторите; больше ничего не меняется.'],
 ['FAULT-TABLE-ALREADY-EXISTS','switch','A previous test is still active','Предыдущий тест ещё активен','The program’s own temporary rule from a previous test still exists.','Собственное временное правило программы от прошлого теста ещё существует.','Press “Cancel fault now” or wait for its timeout.','Нажмите «Отменить сбой сейчас» или дождитесь таймаута.'],
 ['HISTORY-PARTIAL','data','History partly aggregated','История частично объединена','Older measurements were aggregated or pruned to keep the storage and the answer size small.','Старые измерения объединены или удалены, чтобы хранилище и ответ роутера оставались небольшими.','Nothing to fix. Recent days are complete; very old details are summarised.','Исправлять нечего. Недавние дни полные; очень старые подробности сведены в итоги.'],
 ['SPEED-HISTORY-TRUNCATED','speed','Speed history shortened','История скорости сокращена','Only the newest speed results are kept; older ones were dropped.','Хранятся только новейшие результаты скорости; старые удалены.','Nothing to fix. Export what you need before it is dropped.','Исправлять нечего. Сохраните нужное до удаления.'],
 ['JOURNAL-INTEGRITY-FAILED','switch','Journal failed its check','Журнал не прошёл проверку','The transaction journal has a wrong checksum.','У журнала транзакций неверная контрольная сумма.','Do not delete it. Follow router-test-kit/EMERGENCY.md and ask for help with the output of show.','Не удаляйте его. Следуйте router-test-kit/EMERGENCY.md и просите помощи, приложив вывод show.']
];
var AUTO_NAMES={
  'GUARD-DEVICE-UNVERIFIED':['VPN interface state unavailable','Состояние VPN-интерфейса недоступно'],
 'EXISTING-TUNNEL-BINDING-UNVERIFIED':['Working VPN not checked','Рабочий VPN не проверен'],
 'MT3000-FIRMWARE-UNVERIFIED':['MT3000 firmware unverified','Прошивка MT3000 не проверена'],
 'MT3000-FIREWALL-UNVERIFIED':['MT3000 firewall unverified','Firewall MT3000 не проверен'],
 'FW3-INCLUDE-CONTRACT-UNVERIFIED':['FW3 include unverified','Include FW3 не проверен'],
 'FW3-RUNTIME-STATE-UNVERIFIED':['Running FW3 unverified','Рабочий FW3 не проверен'],
 'FW3-SELECTED-ZONE-UNVERIFIED':['VPN firewall zone unverified','VPN-зона firewall не проверена'],
 'VENDOR-WORKER-QUIET-UNVERIFIED':['Background completion unverified','Завершение фоновых операций не проверено'],
  'MONITOR-ONLY-DEPLOYMENT':['Monitoring-only installation','Установка только для мониторинга'],
  'MONITOR-ONLY-INVALID':['Deployment mode unverified','Режим установки не проверен'],
  'NATIVE-PROGRESS-UNVERIFIED':['Controller progress records unverified','Записи состояния контроллера не проверены'],
  'RESERVE-IDENTITY-UNKNOWN':['Cannot find this VPN on the router','Не удаётся найти этот VPN на роутере'],
  'OBSERVATION-STALE':['VPN checks are out of date','Проверки VPN устарели'],
  'VENDOR-IDENTITY-UNKNOWN':['Cannot find this VPN on the router','Не удаётся найти этот VPN на роутере'],
  'VENDOR-SAME-TUNNEL':['Profiles share one router tunnel','Профили относятся к одному туннелю'],
  'PROFILE-IDENTITY-CHANGED':['VPN profile changed','VPN-профиль изменился'],
  'RESERVE-NOT-CONNECTED':['Reserve channel is not connected','Резервный канал не подключён'],
  'CHANNEL-UNRELIABLE':['Channel reliability problem','Проблема с надёжностью канала'],
  'VENDOR-SETTLING':['The router is still checking VPN settings','Роутер ещё проверяет настройки VPN'],
  'CONTROL-REVISION-STALE':['Auto controls changed','Управление Auto изменилось'],
  'START-STATE-UNVERIFIED':['Saved Auto state unverified','Состояние Auto не проверено'],
  'STOP-SUPERSEDED-START':['Pending Start cancelled','Ожидающий запуск отменён'],
  'START-CONFIG-CHANGED':['Settings changed during Start','Настройки изменились при запуске'],
'LAN-TRIAL-REQUIRED':['LAN trial required','Нужен LAN-тест'],'BOUNDED-DEADLINE-REQUIRED':['Test window missing','Нет окна теста'],'SESSION-LOSS-NOT-ACCEPTED':['Reconnection not accepted','Не разрешён разрыв сессий'],
'TRANSACTION-IN-PROGRESS':['Switch in progress','Переключение идёт'],'TRIAL-ATTEMPT-LIMIT':['Trial attempt limit','Лимит попыток теста'],'UNSUPPORTED-BOARD':['Unsupported router model','Неподдерживаемая модель роутера'],
'UNSUPPORTED-FIRMWARE':['Unsupported firmware','Неподдерживаемая прошивка'],'FIRMWARE-UNKNOWN':['Firmware unknown','Прошивка неизвестна'],'VENDOR-CODE-CHANGED':['GL.iNet code changed','Код GL.iNet изменился'],
'VENDOR-CODE-UNVERIFIED':['GL.iNet code unverified','Код GL.iNet не проверен'],'VENDOR-WORKER-BUSY':['GL.iNet program is busy','Программа GL.iNet занята'],'HARDWARE-ACCELERATOR-UNVERIFIED':['Hardware acceleration unverified','Аппаратное ускорение не проверено'],
'SOFTWARE-ACCELERATOR-UNVERIFIED':['Software acceleration unverified','Программное ускорение не проверено'],'FLOW-OFFLOAD-ENABLED':['Flow offload is on','Включён flow offload'],'IPV6-NOT-EXPLICITLY-DISABLED':['IPv6 not disabled','IPv6 не отключён'],
'KILLSWITCH-NOT-ENABLED':['Kill Switch is off','Kill Switch выключен'],'DIRECT-WAN-FALLBACK':['Direct exit without VPN possible','Возможен выход мимо VPN'],'VPN-POLICY-DISABLED':['VPN policy is off','Политика VPN выключена'],
'TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED':['Two to sixteen rules needed','Нужно от 2 до 16 правил VPN'],'GENERIC-RULES-NOT-ADJACENT':['Rules not adjacent','Правила идут не подряд'],'GENERIC-DUPLICATE-INTERFACE':['Duplicate interface','Повтор интерфейса'],
'SPECIAL-RULES-MUST-PRECEDE-GENERIC':['Special rules in wrong order','Особые правила в неверном порядке'],'SOURCE-RESERVE-NOT-CONFIGURED':['Primary or reserve not set','Основной или резерв не заданы'],'PROFILE-INACTIVE':['Profile not connected','Профиль не подключён'],
'PROFILES-NOT-GENERIC-RULES':['Profiles not in general rules','Профили не в общих правилах'],'SAME-INTERFACE':['Same interface twice','Один интерфейс дважды'],'POLICY-ORDER-DIRECTION-UNVERIFIED':['Rule order direction unverified','Направление порядка правил не проверено'],
'LAN-LAYOUT-UNSUPPORTED':['Unsupported LAN layout','Неподдерживаемая схема LAN'],'PROFILE-NOT-MONITORED':['Profile not monitored','Профиль не наблюдается'],'NFT-GUARD-UNAVAILABLE':['Safety block unavailable','Страхующая блокировка недоступна'],
'POLICY-READ-FAILED':['Cannot read VPN rules','Не удаётся прочитать правила VPN'],'UPLINK-LINK-DOWN':['Uplink is down','Внешний канал отключён'],'LEASE-INTEGRITY-FAILED':['Lease damaged','Аренда повреждена'],
'LEASE-STORAGE-FAILED':['Lease cannot be saved','Аренда не сохраняется'],'LEGACY-LEASE-RECOVERY':['Old lease recovered','Восстановлена старая аренда'],'EXTERNAL-POLICY-CHANGE-GUARD-RETAINED':['Outside change, block kept','Изменение извне, блокировка сохранена'],
'ROLLBACK-UNVERIFIED-GUARD-RETAINED':['Return unverified, block kept','Возврат не подтверждён, блокировка сохранена'],'CLIENT-CONFIRMATION-TIMEOUT':['Computer did not confirm','Компьютер не подтвердил'],'CLIENT-STOP':['Stopped by the helper','Остановлено помощником'],
'TARGET-HTTPS-DNS-FAILED':['Reserve check failed','Проверка резерва не прошла'],'LAN-BASELINE-NOT-SOURCE':['Computer was not on the primary','Компьютер был не на основном'],'RESERVE-EXIT-NOT-DISTINCT':['Reserve exit equals primary','Выход резерва совпал с основным'],
'VENDOR-APPLY-FAILED':['GL.iNet did not apply the change','GL.iNet не применил изменение'],'POLICY-CHANGED-DURING-APPLY':['Rules changed during the switch','Правила изменились во время переключения'],'NATIVE-SYSTEM-001':['System check failed','Проверка системы не прошла'],
'TERMS-NOT-ACCEPTED':['Terms not accepted','Условия не приняты'],'RETURN-NOT-APPLICABLE':['Nothing to return','Возвращать нечего'],'SOURCE-NOT-HEALTHY':['Primary not healthy yet','Основной ещё не исправен'],
'JOURNAL-UNVERIFIED':['Journal unverified','Журнал не проверен'],'EXTERNAL-POLICY-CHANGE':['Changed from outside','Изменено извне'],'EXTERNAL-POLICY-CHANGE-RELEASED':['Changed from outside, block removed','Изменено извне, блокировка снята'],
'ROLLBACK-UNVERIFIED':['Return unverified','Возврат не подтверждён'],'ENVIRONMENT-EVIDENCE-UNAVAILABLE':['No data about the router','Нет данных о роутере'],'MONITOR-EVIDENCE-STALE':['Monitor data is old','Данные мониторинга устарели'],
'NATIVE-START-CERTIFICATION-REQUIRED':['Checked again at Start','Повторная проверка при запуске'],'OPERATOR-RETURN':['Returned on request','Возврат по запросу'],'PRIMARY-RECOVERED':['Primary recovered','Основной восстановился']
};
(function(){
  var have={};ERROR_ROWS.forEach(function(r){have[r[0]]=true;});
  if(typeof ERROR_EXTRA_GROUPS!=='undefined')ERROR_EXTRA_GROUPS.forEach(function(g){ERROR_GROUPS.splice(g[0]==='state'?2:ERROR_GROUPS.length,0,g);});
  if(typeof ERROR_EXTRA_ROWS!=='undefined')ERROR_EXTRA_ROWS.forEach(function(r){if(!have[r[0]]){ERROR_ROWS.push(r);have[r[0]]=true;}});
  if(typeof ERROR_FAMILIES!=='undefined')ERROR_FAMILIES.forEach(function(f){var code=f[0]+'*';if(!have[code]){ERROR_ROWS.push([code].concat(f.slice(1)));have[code]=true;}});
})();
var ERROR_GROUP_OF={},errorTable=null,ERROR_TABLE_STATE={query:'',open:Object.create(null),selected:null};
try{
  var savedErrorState=JSON.parse(sessionStorage.getItem('homensai-vpn-error-table')||'null');
  if(savedErrorState&&typeof savedErrorState.query==='string'&&savedErrorState.query.length<=128){
    ERROR_TABLE_STATE.query=savedErrorState.query;
    Object.keys(savedErrorState.open||{}).slice(0,500).forEach(function(code){if(/^[A-Z0-9*-]{1,96}$/.test(code))ERROR_TABLE_STATE.open[code]=savedErrorState.open[code]===true;});
    if(typeof savedErrorState.selected==='string'&&/^[A-Z0-9*-]{1,96}$/.test(savedErrorState.selected))ERROR_TABLE_STATE.selected=savedErrorState.selected;
  }
}catch(error){}
function persistErrorTableState(){try{sessionStorage.setItem('homensai-vpn-error-table',JSON.stringify(ERROR_TABLE_STATE));}catch(error){}}
(function(){
  var seen={};ERROR_ROWS.forEach(function(r){seen[r[0]]=true;});
  Object.keys(AUTO_BLOCKERS).forEach(function(code){
    if(seen[code])return;
    var guide=typeof autoRemedyKey==='function'&&AUTO_REMEDIES[autoRemedyKey(code)];
    if(!AUTO_NAMES[code]&&guide)AUTO_NAMES[code]=guide.title.slice();
    var nm=AUTO_NAMES[code]||(function(){var w=code.toLowerCase().split('-').join(' ');w=w.charAt(0).toUpperCase()+w.slice(1);return [w,w];})();
    ERROR_ROWS.push([code,'switch',nm[0],nm[1],AUTO_BLOCKERS[code][0],AUTO_BLOCKERS[code][1],AUTO_BLOCKERS[code][0]+' If it is still unclear, open Help → “The Auto button refuses to start”.',AUTO_BLOCKERS[code][1]+' Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».']);
  });
  Object.keys(PLAN_BLOCKERS).forEach(function(code){
    if(seen[code])return;var r=PLAN_BLOCKERS[code];
    ERROR_ROWS.push([code,'switch',r[0],r[1],r[2],r[3],'This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.','Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.']);
  });
  ERROR_ROWS.forEach(function(r){ERROR_GROUP_OF[r[0]]=r[1];});
})();
function renderErrorTable(){
  if(typeof ensureJournalDictionary==='function')ensureJournalDictionary();
  var search=E('input',{'type':'search','class':'hv-search','placeholder':bi('Search a code or a word','Поиск по коду или слову'),'aria-label':bi('Search error codes','Поиск по кодам ошибок')});
  var host=E('div',{'class':'hv-errtable'});
  search.value=ERROR_TABLE_STATE.query;
  function matches(r,q){return !q||(r.join(' ')).toLowerCase().indexOf(q)>=0;}
  function draw(){
    while(host.firstChild)host.removeChild(host.firstChild);
    var q=search.value.trim().toLowerCase();
    ERROR_TABLE_STATE.query=search.value;
    persistErrorTableState();
    ERROR_GROUPS.forEach(function(g){
      var rows=ERROR_ROWS.filter(function(r){return r[1]===g[0]&&matches(r,q);});
      if(!rows.length)return;
      host.appendChild(E('h4',{},bi(g[1][0],g[1][1])+' ('+rows.length+')'));
      var table=E('table',{'class':'table hv-errors','role':'table'},[E('tr',{'class':'hv-error-head'},[E('th',{},bi('Code','Код')),E('th',{},bi('Name','Название')),E('th',{},bi('What it means','Что означает')),E('th',{},bi('What to do','Что делать'))])]);
      rows.forEach(function(r){
        var fixRow=null;
        var expanded=ERROR_TABLE_STATE.open[r[0]]===true;
        var button=(r[6]||r[8])?E('button',{'type':'button','class':'cbi-button','aria-expanded':expanded?'true':'false','click':function(){var open=fixRow.hidden;fixRow.hidden=!open;ERROR_TABLE_STATE.open[r[0]]=open;persistErrorTableState();button.setAttribute('aria-expanded',open?'true':'false');button.textContent=open?bi('Hide','Скрыть'):(r[1]==='journal'?bi('Explanation','Расшифровка'):bi('How to fix','Как исправить'));}},expanded?bi('Hide','Скрыть'):(r[1]==='journal'?bi('Explanation','Расшифровка'):bi('How to fix','Как исправить'))):null;
        table.appendChild(E('tr',{'data-error-code':r[0],'class':ERROR_TABLE_STATE.selected===r[0]?'hv-err-selected':null},[E('td',{},E('code',{},r[0])),E('td',{},E('strong',{},bi(r[2],r[3]))),E('td',{},bi(r[4],r[5])),E('td',{},button||E('span',{'class':'hv-muted'},bi('See the message','См. сообщение')))]));
        if(r[6]||r[8]){fixRow=E('tr',{'class':'hv-errfix'},[E('td',{'colspan':'4'},[r[6]?E('p',{},[E('strong',{},bi('How to fix: ','Как исправить: ')),bi(r[6],r[7])]):null,typeof renderAutoRemedy==='function'?renderAutoRemedy(r[0]):null,r[8]?E('p',{'class':'hv-errexample'},[E('strong',{},bi('Example: ','Пример: ')),bi(r[8],r[9])]):null].filter(Boolean))]);fixRow.hidden=!expanded;table.appendChild(fixRow);}
      });
      host.appendChild(table);
    });
    if(!host.firstChild)host.appendChild(E('p',{},bi('No code matches. Try a shorter word.','Ничего не найдено. Попробуйте более короткое слово.')));
  }
  search.addEventListener('input',draw);draw();
  return E('section',{'class':'hv-chart-card'},[E('h3',{},bi('Events, states and diagnostic codes','События, состояния и диагностические коды')),E('p',{},bi('Every code the program can show: its name, what it means and, under the button, how to fix it. A code tells what was observed; the cause may stay unknown.','Все коды, которые может показать программа: название, что означает и, под кнопкой, как исправить. Код говорит о том, что наблюдалось; причина может остаться неизвестной.')),(typeof errorExamples==='function'?errorExamples():null),search,host].filter(Boolean));
}

/* Help topic "Prompt for your AI agent": one complete prompt the owner copies into any AI agent that has a terminal.
   The text is written for the agent. It must never contain a secret. No template placeholders with dollar-brace and no backticks inside. */
var AI_PROMPT_EN="Install and verify HomenS.AI Auto VPN on my specific router. Execute the available work yourself, explain results plainly and finish with a verified outcome rather than a plan. Do not ask me to repeat commands you can perform safely.\n\nMY PARAMETERS\nRouter address/model: [fill in]. Access: [existing SSH/key or secure access request; no secrets here].\nOutcome: [install and monitor / install, choose a pair and start Auto / upgrade preserving the existing pair and prior Auto/selected-channel state]. Default: monitor, Auto off.\nPrimary VPN: [existing configured client/tunnel or choose together]. Reserve: [another independent configured client/tunnel, not a second server in the same client].\nLanguage: English. Do not enable optional Telegram/speed tests without my selection. Backups: private folder outside Git.\nRelease: [stable 0.9.0 by default / explicitly named prerelease]. Preserve existing monitoring/retention settings unless I choose changes.\nReuse the authorization already expressed in my requested outcome; do not ask again for the same authorized step.\n\nSOURCE\nhttps://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn\nRead docs/INSTALL.en.md, docs/CURRENT-STATUS.md, docs/FIRST-RUN-SETUP.md, docs/ROUTER-PREPARATION.md and DISCLAIMER.md from the chosen source/tag; current guidance is not permission to execute old dated backlogs. Read scripts before running them.\nRelease: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0\nArtifact: homensai-auto-vpn_0.9.0-1_all.ipk,769849bytes.\nSHA256:7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a\nThe following size/hash/version/install commands pin the stable default. For an explicitly named prerelease, first replace every related expected value with that release's verified manifest, package, checksum and same-tag kit; never mix stable and prerelease artifacts.\nAlso obtain the matching.ipk.sha256 and release-v0.9.0-verification.json. This is an application, not firmware. Obtain router-test-kit scripts from this same tag, not mutable main. Do not downgrade a newer installed version; report the difference.\n\nVIRTUAL TEST SCOPE ONLY: if the owner explicitly requests the isolated x86/OpenWrt laboratory in lab/openwrt-qemu/README.md and /tmp/HOMENSAI_VIRTUAL_LAB exists, test the package in monitor-only mode with Auto/native off. Preserve the real x86 board identity. Record GL.iNet hardware/firmware preflight gates as unsupported for this VM, not PASS; do not run the GL installation kit past its refusal. After independently checking every non-hardware prerequisite, use ordinary opkg installation in the existing documented monitor-only VM deployment path. Never spoof a board, bypass a native guard, or turn that result into GL.iNet/LAN/Auto certification. This exception does not apply to a real unknown router.\n In that explicitly chosen VM monitor-only scope, check the application's own monitor_only option before upgrading an old release: if absent, set monitor_only=1 with ordinary UCI and verify native_enabled remains0. Do not change network configuration or manufacture hardware readiness.\n\n1. ACCESS AND SCOPE\nYou need a local terminal and access to the named router. Without tools, explain that a chat cannot install it. Bundle missing address/access questions. Reuse authorized SSH and verify its host key; establish identity for a new/changed key, never disable verification. If SSH is unavailable, offer supported LuCI installation and explain the necessary owner action.\nNever request secrets in chat or print/log/commit passwords, VPN keys, tokens or full configuration. Use secure tool input or the owner's own router page. Do not change computer networking/Wi-Fi/adapter addresses/routes, another router, WAN, DHCP or internet-facing management. No flashing, factory reset or unrelated services.\nBefore sending SSH/HTTP credentials, verify the management route and device identity. Two adapters may reach different routers with the same private IPv4 address. A cable-bound data probe does not establish which interface an unbound management request uses. Refuse a mismatch; do not fix it by silently changing host networking. A separately verified loopback gateway is browser access, not the LAN-witness target.\n\n2. READ-ONLY BASELINE\nInspect ubus call system board, /etc/glversion, opkg status homensai-auto-vpn, /overlay space, memory, original feeds and dependencies. Record actual board/model/firmware, installed/running versions, Auto state, selected pair/active channel and any other installer, unfinished transaction/rollback, owned guard or unsaved changes.\nArchitecture:all and a model selector do not prove compatibility. Current continuous Auto is qualified on a separately prepared GL-MT3000/GL.iNet4.11.0. Current MT6000 continuous mode/arbitrary firmware are not qualified. Never bypass actual platform/readiness refusals.\n Check the configuration filesystem itself (/etc/config, or its mounted overlay), not only free bytes: inspect statvfs/proc mounts and require writable storage. A read-only filesystem can have free space. Stop and diagnose it before settings/package writes; never automatically remount or repair a production filesystem.\n\n3. VERIFIED RECOVERY\nBefore changes obtain a supported configuration export and needed application settings/history. Encrypt it in a private folder outside Git; protect the key with the OS or a separate secure store. Check archive entries, required files, SHA256 and independent in-memory decrypt/read. Do not persist plaintext secret configuration in the project. Without verified recovery stop installation. A configuration export is not full flash/bootloader recovery.\n\n4. DEPENDENCIES AND ARTIFACT\nCheck python3,lua,lua-cjson,libuci-lua,ip-full,ubus,rpcd,luci-base,ca-bundle. Install missing dependencies only with ordinary opkg from this firmware's original vendor feeds. No mass opkg upgrade, feed replacement, foreign-release packages or force flags. Check space first; current preflight needs at least20MiB free writable storage. On ABI/signature/dependency conflicts stop dependent writes and explain the cause; do not remove system components to bypass it.\nDownload IPK/checksum/verification JSON from one HTTPS release. Verify name/size/SHA256 locally and after router transfer. Compare checksum, release evidence and same-tag02-install.sh EXPECTED_SHA/SIZE. Stop on mismatch. Never pipe a downloaded script directly into a shell.\n\n5. INSTALL\nFor an upgrade issue ordinary Auto Stop and await completed rollback/cleanup; ACK/queued is not completed. Never delete journals/guards or reset attempt budgets to bypass lifecycle checks. Read/run same-tag01-preflight.sh, which writes its report under/tmp. Resolve only permitted failures and rerun. Then use02-install.sh with the verified IPK or documented opkg install /tmp/homensai-auto-vpn_0.9.0-1_all.ipk. Never Flash Firmware; opkg exit0 alone is insufficient.\nRun03-verify.sh wait. Verify the chosen installed package and live RPC versions (stable default: installed0.9.0-1/live RPC0.9.0), fresh samples, no service errors, one monitor and expected services. Where accessible compare installed file bytes/modes and actually served dashboard/CSS with the verified IPK payload. List unperformed checks. Diagnose stale RPC/LuCI cache with the documented procedures rather than claiming success from opkg alone.\n\n6. FIRST ENTRY AND PAIR\nOpen Services → HomenS.AI Auto VPN, Ctrl+F5. Terms appear only until first acceptance of the current version. I tick the boxes and press Accept myself; never call terms_accept or write terms_version for me. Preserve existing acceptance; skipping the agreement on a later visit is expected.\nNext: three-diagram explanation → OK → eight steps: appearance, monitoring, existing VPNs, names/priorities, recovery, speed, Telegram, review. Choose the pair through Settings → All application settings → step3: Existing VPNs. Primary means preferred everyday channel; reserve is a different configured client for failure. A saved profile is not proof of health; wait for current identity-bound observations. Show choices before saving. Distinguish saved profile/Connected tunnel/selected traffic route. VPN profiles/keys are created in GL.iNet; never invent them. Without profiles report installed application/pair not configured.\nPreserve optional settings without my choice and do not send Telegram tests without my request. You may save authorized reviewed settings with tools; verify with a fresh read, not ACK alone. Save does not accept terms or start Auto. On releases supporting the options, review 1–2000 live observations and 1–7 detail days; preserve prior values by default. Do not send unsupported fields to an older RPC. The green escape opens the dashboard with current settings; no draft save, reset or Auto start. Deferral is not completed pair setup.\n\n7. AUTO AND TESTING\nInstallation and switching readiness differ. Read actual platform preparation and DNS/acceleration/vendor/rollback checks. A model, loaded module or saved flag is not proof. If DNS/acceleration/stock startup needs adjustment, first present exact scope/undo; ordinary installation does not authorize it. Do not disable a working DNS owner based on another router's example or force-unload modules.\nIf I selected start Auto, the platform is ready and I accepted terms, issue one ordinary Start. Await completed STARTING, confirmed selected channel and fresh DNS+twoHTTPS for both VPNs. Queue acceptance, green controls, interfaces and Connected alone do not prove traffic.\nPrepared-MT3000 router-probed-ipv4 mode does not require a LAN certificate or continuously running LAN helper. The separate client-confirmed trial must not compete with an active continuous session: complete normal Stop/recovery before its own trial setup. CheckOnly checks client path prerequisites; ProbeOnly performs actual bound DNS/HTTPS without starting Auto; neither is a passed switching trial. Additional LAN tests measure a real client's route through the router. An agent must run them from an actual device on that LAN; a hosted chat without access is no substitute. Never fabricate confirmation. Switching tests need a specified time/attempt bound, rollback and permission for session interruption; otherwise perform read-only/non-switching checks. Do not change computer networking to bypass binding failures.\n\n8. REPORT\nCompare protected settings before/after. Investigate unexpected changes and undo only your own verified edits, preserving newer owner changes. Never flush the whole firewall. Report actual board/firmware, installed/running versions, artifact source/size/hash, dependencies, verified backup/recovery, UI/monitor, pair/active channel, final Auto ON/OFF, changes, unverified areas, page URL and Stop/uninstall/recovery instructions. Separate PASS/FAIL/PARTIAL/BLOCKED/SKIPPED/UNKNOWN. Auto needs explicit Start after restart. When the requested outcome explicitly preserves a previously running Auto/channel during an upgrade, restore it through ordinary controls and verify the actual selection; do not leave it off merely because opkg succeeded. If guarded restoration fails, keep the refusal evidence, safe state and precise recovery status.\nDo not attribute other-version tests to this installation, router probes to LAN proof or short runs to24hours. Do not claim IPv6/currentMT6000continuous-mode/power-cut/unattended acceptance without testing. If blocked, save the precise stopping point and next safe step instead of inventing success.";
var AI_PROMPT_RU="Установи и проверь HomenS.AI Auto VPN на моём роутере. Сам выполняй доступные действия и доведи задачу до проверенного результата. Объясняй простыми словами; не ограничивайся планом и не проси меня повторять команды, которые можешь выполнить сам.\n\nМОИ ПАРАМЕТРЫ\nАдрес/модель: [указать адрес и модель, если известны].\nДоступ: [существующий SSH/ключ либо защищённый запрос доступа; секреты не вставлять].\nРезультат: [установка и мониторинг / установка, выбор пары и включение Auto / обновление с сохранением пары и прежнего состояния Auto/выбранного канала]. По умолчанию — мониторинг, Auto выключен.\nОсновной VPN: [существующий настроенный клиент/туннель или выбрать вместе].\nРезервный VPN: [другой независимый настроенный клиент, а не второй сервер того же клиента].\nЯзык: русский. Telegram и тесты скорости: не включать без моего выбора.\nРезервные копии: отдельная приватная папка вне Git.\nВыпуск: [stable 0.9.0 по умолчанию / явно названный предварительный выпуск]. Настройки мониторинга/хранения сохранять прежними без моего выбора.\nИспользуй уже данное разрешение на выбранный результат; не переспрашивай повторно про тот же разрешённый шаг.\n\nИСТОЧНИК\nhttps://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn\nПрочитай docs/INSTALL.ru.md, docs/CURRENT-STATUS.md, docs/FIRST-RUN-SETUP.md, docs/ROUTER-PREPARATION.md и DISCLAIMER.ru.md из выбранного исходника/тега. Текущее руководство не разрешает выполнять старые датированные планы. Не выполняй непрочитанные скрипты.\nВыпуск для этой инструкции: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0\nПакет: homensai-auto-vpn_0.9.0-1_all.ipk, 769849 байт.\nSHA256: 7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a\nРазмер/хеш/версии и команды ниже привязаны к stable по умолчанию. Для явно выбранного предварительного выпуска сначала согласованно замени все ожидаемые значения его проверенными manifest, пакетом, checksum и комплектом того же тега; не смешивай артефакты разных выпусков.\nСкачай также matching .ipk.sha256 и release-v0.9.0-verification.json. Это приложение, не прошивка. Скрипты router-test-kit бери из этого же тега, а не изменяемой main. Не заменяй более новую установленную версию старой: сообщи о различии.\n\nТОЛЬКО ВИРТУАЛЬНЫЕ ИСПЫТАНИЯ: если владелец явно запросил изолированный x86/OpenWrt-стенд из lab/openwrt-qemu/README.md и существует /tmp/HOMENSAI_VIRTUAL_LAB, проверяй пакет в режиме мониторинга, Auto/native выключены. Сохраняй реальную x86-идентичность. Аппаратные/firmware-пункты GL.iNet preflight отметь как неподдерживаемые в этой VM, не PASS; не запускай GL-установочный набор после его отказа. После независимой проверки всех остальных предпосылок используй обычный opkg в существующем документированном monitor-only пути VM. Не подделывай модель, не обходи native-guard и не выдавай это за приёмку GL.iNet/LAN/Auto. На реальный неизвестный роутер это исключение не распространяется.\n В этом явно выбранном VM monitor-only режиме перед обновлением старой версии проверь собственный параметр приложения monitor_only: если его нет, установи monitor_only=1 обычным UCI и проверь, что native_enabled остаётся0. Не меняй сетевую конфигурацию и не создавай фиктивную аппаратную готовность.\n\n1. ДОСТУП И ГРАНИЦЫ\nНужны терминал на компьютере и доступ к названному роутеру. Если инструментов нет, честно сообщи: обычный чат не может выполнить установку. Недостающие адрес и способ доступа уточни одним коротким вопросом. Используй существующий разрешённый SSH и проверенный host key; новый/изменившийся ключ сначала сверь с устройством. Не отключай проверку ключей. При отсутствии SSH предложи поддерживаемую установку через LuCI и объясни требуемое действие владельца.\nПароли, VPN-ключи, токены и полные конфигурации не запрашивай в чат, не печатай, не сохраняй в Git/журналы. Используй защищённый ввод инструмента либо ввод владельцем в его панели. Не меняй сеть компьютера, Wi-Fi, адреса/маршруты адаптеров, другой роутер, WAN, DHCP или доступ из интернета. Не прошивай, не делай factory reset, не запускай посторонние службы.\nДо отправки SSH/HTTP-пароля проверь путь управления и идентичность устройства: два адаптера могут вести к разным роутерам с одним частным IPv4. Привязанная к кабелю проверка данных не доказывает путь непривязанного запроса управления. При несовпадении откажись; не исправляй его скрытой сменой сети компьютера. Отдельно проверенный loopback-переход — доступ браузера, а не цель LAN-проверки.\n\n2. ИСХОДНОЕ СОСТОЯНИЕ — ТОЛЬКО ЧТЕНИЕ\nПроверь ubus call system board, /etc/glversion, opkg status homensai-auto-vpn, /overlay, свободную память, штатные feeds и зависимости. Зафиксируй реальный board_name/модель/прошивку, установленную и работающую версии, Auto ВКЛ/ВЫКЛ, выбранную пару/активный канал. Проверь отсутствие другого установщика, незавершённого rollback/транзакции, собственного guard и несохранённых изменений.\nArchitecture:all или выбор модели в UI не доказывают совместимость. Непрерывный Auto проверен на отдельно подготовленном GL-MT3000/GL.iNet4.11.0; текущая приёмка MT6000 continuous mode и произвольной прошивки не заявлена. Не обходи реальные platform/readiness-отказы.\n Проверь саму файловую систему настроек (/etc/config или её смонтированный overlay), а не только число свободных байт: изучи statvfs/proc mounts и доступность записи. Read-only система может иметь много места. До записи пакетов/настроек остановись и диагностируй её; не перемонтируй и не исправляй файловую систему рабочего роутера автоматически.\n\n3. ПРОВЕРЕННОЕ ВОССТАНОВЛЕНИЕ\nДо изменений получи поддерживаемый экспорт конфигурации и нужные настройки/историю приложения. Сохрани зашифрованную приватную копию вне Git, защити ключ средствами ОС либо отдельным защищённым хранилищем. Проверь состав архива, обязательные файлы, SHA256 и независимую расшифровку/чтение в памяти. Не сохраняй открытые секретные конфигурации в рабочем проекте. Без проверенного восстановления установку не продолжай. Конфигурационный экспорт не является полной копией flash/загрузчика.\n\n4. ЗАВИСИМОСТИ И ФАЙЛЫ\nПроверь python3, lua, lua-cjson, libuci-lua, ip-full, ubus, rpcd, luci-base, ca-bundle. Недостающее устанавливай обычным opkg только из исходных vendor feeds этой прошивки. Не запускай массовый opkg upgrade, не меняй feeds, не ставь пакеты чужого выпуска, не используй force. Сначала проверь место; текущий preflight требует минимум20МиБ свободного записываемого пространства. При конфликте ABI/подписей/зависимостей объясни точную причину и останови зависимые изменения, не удаляй системные компоненты ради обхода.\nСкачай пакет/checksum/verification JSON из одного HTTPS-релиза. Проверь имя, размер, SHA256 на компьютере и после передачи на роутер. Сверь с checksum, записью релиза и EXPECTED_SHA/SIZE в02-install.sh того же тега. При несовпадении не устанавливай. Не выполняй скачанный скрипт через pipe в shell.\n\n5. УСТАНОВКА\nПри обновлении штатно останови Auto и дождись завершённого rollback/очистки. ACK/queued не равно завершению. Не удаляй журналы/guard, не сбрасывай лимиты и не обходи lifecycle-отказ. Прочитай и выполни01-preflight.sh из того же тега; он пишет только свой отчёт в/tmp. Исправь допустимые причины отказа и перепроверь. Затем02-install.sh с проверенным IPK либо обычный opkg install /tmp/homensai-auto-vpn_0.9.0-1_all.ipk по инструкции. Это не Flash Firmware; exit0 от opkg недостаточно.\nВыполни03-verify.sh wait. Проверь установленную0.9.0-1, работающий RPC0.9.0, свежие данные, отсутствие service errors, единственный монитор и нужные службы. Где доступно, сравни установленные файлы/права и реально отдаваемые dashboard/CSS с payload проверенного пакета. Непроверенные области перечисли. Старый RPC/кеш LuCI диагностируй штатно; не делай вывод по одной версии opkg.\n\n6. ПЕРВЫЙ ВХОД И ПАРА\nОткрой Services → HomenS.AI Auto VPN, Ctrl+F5. Соглашение показывается только до первого принятия текущей версии. Галочки и «Принять» выбираю я; не вызывай terms_accept и не записывай terms_version за меня. Уже сохранённое принятие не сбрасывай: пропуск соглашения при повторном входе нормален.\nДалее объяснение с тремя схемами → OK → восемь шагов: язык/оформление, мониторинг, существующие VPN, имена/приоритеты, восстановление, скорость, Telegram, обзор. Пара выбирается в «Настройки → Все настройки приложения → шаг3: Существующие VPN». Основной — обычный предпочитаемый канал; резервный — другой настроенный клиент на случай отказа. Сохранённый профиль не доказывает исправность: дождись текущих наблюдений, привязанных к его идентичности. Покажи значения до сохранения. Не путай профиль, Connected-туннель и реально выбранный маршрут. Профили/ключи создаются в штатной панели GL.iNet: не выдумывай их. Если их нет, сохрани честный результат «приложение установлено, пара не настроена».\nНеобязательные настройки сохраняй прежними без моего выбора. Не отправляй Telegram-тест без запроса. Сохранять разрешённую проверенную конфигурацию можно инструментами; затем проверь чтением, а не только ACK. Save не принимает соглашение и не запускает Auto. Если выпуск поддерживает параметры, проверь лимит1–2000наблюдений и срок1–7дней; по умолчанию сохраняй прежние значения. Не отправляй неподдерживаемые поля старому RPC. Если я откладываю мастер, зелёная кнопка открывает панель с текущими настройками, не сохраняет черновик, не сбрасывает и не включает Auto; это не завершённая настройка пары.\n\n7. AUTO И ТЕСТЫ\nУстановка приложения не равна готовности переключать. Прочитай актуальную подготовку платформы и реальные проверки DNS/ускорения/vendor/rollback. Модель, загруженный модуль и сохранённый флаг не являются доказательством. Если нужны изменения DNS/ускорения/stock VPN startup, покажи конкретный объём и отмену: обычная установка их не разрешает. Не отключай работающего DNS-владельца по чужому примеру и не выгружай модули принудительно.\nЕсли я выбрал «включение Auto», текущая платформа готова и соглашение принято мной, выдай один обычный Start. Дождись завершения STARTING, подтверждённого выбранного канала и свежих DNS+двухHTTPS для обоих VPN. Очередь, зелёная кнопка, интерфейс туннеля и Connected сами по себе трафик не доказывают.\nВ router-probed-ipv4 режиме подготовленного MT3000 не нужны LAN-сертификат и постоянно запущенный LAN-помощник. Отдельный клиентский тест не должен конкурировать с непрерывным Auto: до его настройки заверши штатный Stop/восстановление. CheckOnly проверяет предпосылки пути; ProbeOnly выполняет реальные привязанные DNS/HTTPS без включения Auto; ни один не является пройденным тестом переключения. Дополнительная LAN-проверка доказывает путь реального компьютера через роутер. Агент может выполнить её лишь с устройства этой LAN; облачный ChatGPT/Claude без такого доступа не заменяет клиент. Не подделывай подтверждения. Испытание с переключением требует определённого времени/предела, возврата и разрешения на прерывание сеансов. Без этого выполняй только чтение/проверку без переключения. Не меняй сеть компьютера для обхода ошибки привязки.\n\n8. ИТОГ\nСравни защищённые настройки до/после. Неожиданные изменения расследуй; восстанавливай только свои подтверждённые изменения, не затирая новые правки владельца. Не сбрасывай firewall целиком. Отчёт: модель/прошивка; установленная/работающая версии; источник/размер/SHA256; зависимости; копия/проверка/восстановление; интерфейс/монитор; выбранная пара/активный канал; Auto ВКЛ/ВЫКЛ; изменения; непроверенное; URL панели; Stop/удаление/восстановление. Разделяй PASS/FAIL/PARTIAL/BLOCKED/SKIPPED/UNKNOWN по фактам. После перезапуска нужен явный Start.\nНе приписывай установленной версии чужие тесты, router-only проверке — LAN-доказательство, короткому прогону — сутки. Не обещай IPv6/MT6000 continuous mode/физическое питание/автономную эксплуатацию без реальной проверки. При блокере сохрани точку остановки и следующий безопасный шаг вместо выдуманного успеха.";
var AI_LAN_PROMPT_EN="Help me use the Windows LAN witness for HomenS.AI Auto VPN on the specific router I identify. Do the available technical work with real tools; do not pretend a hosted chat is a client on my LAN.\n\nPARAMETERS\nRouter application origin/private IP and port: [verified actual value]. Cable interface index: [verified value]. Mode: [SelfTest / CheckOnly by default / ProbeOnly / explicitly authorized full client-confirmed trial]. Requested time/session-loss scope: [fill only for a full trial]. Helper source: the same selected/installed release, not an unrelated mutable script.\n\nSCOPE\nPrepared continuous MT3000 router-probed Auto does not require this LAN trial or a LAN certificate. This is an optional separate client witness. A full client-confirmed trial edits application trial settings and can switch router traffic; it must not compete with a running continuous session. First finish its normal Stop/recovery and verify the actual baseline.\nReuse an explicit full-trial authorization already given for this same scope; do not ask again for it. Otherwise prepare a concrete bounded test/undo and ask once before the full mode. The owner enters the password and TEST privately themselves; never type those confirmations for them or accept terms for them.\nNo computer NIC/DNS/routes/firewall changes, no disabling another VPN, no firmware/feed replacement or resetting budgets. Diagnose refusals rather than inventing a bypass.\n\n1. Verify the intended device and management path, not just a responding private IP. Two adapters can reach different routers with the same address. Check the ordinary management route as well as the explicit cable path before any credential request. Current helpers refuse CLIENT-CONTROL-PATH-MISMATCH; an older release may lack that guard, so do not rely on the filename as proof. A browser loopback gateway is not the real LAN-witness address.\n2. Check pwsh -v. PowerShell7 is required; if installation is within my already authorized setup scope, use the official package: winget install --id Microsoft.PowerShell --exact. Otherwise explain the missing dependency and the specific required action.\n3. Download client-test.ps1 and start-lan-helper.ps1 from the verified application's own origin at /luci-static/resources/view/homensai-vpn/. Keep them together in one new private folder. Optional start-lan-helper.cmd requires both files. Preserve release/hash/source identity and inspect the script. Do not fetch from the other router merely because its private IP matches.\n4. In that folder use: pwsh -NoProfile -File .\\client-test.ps1 -SelfTest\nFor path prerequisites use: pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly\nReplace the example address and index with the verified parameters before running. CheckOnly is not an Internet or switching test and asks for no password.\n5. For actual bound DNS/HTTPS without starting Auto use: pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -ProbeOnly\nAgain substitute the real parameters. It measures that IPv4 client path, not every app/IPv6. It makes network requests but does not alter router settings.\n6. Only for the separately authorized full trial, verify that prior Auto/recovery is complete and the client-trial platform/pair is ready. Run: pwsh -NoProfile -File .\\start-lan-helper.ps1\nChoose mode3 with a bounded deadline/window. The owner enters the private password and TEST. Management HTTP is not encrypted; use only the intended trusted LAN or HTTPS with a properly trusted certificate. Do not disable certificate validation. Never inspect, print, log or save their password, session, token or full configuration.\n7. Wait for the actual final result. A queued Stop is not restoration. Exit0 applies to the selected mode; exit2 is refused/unverified/failure; exit3 means verified retained reserve, not a successful original-path return. Do not tell the owner that continuous Auto is ready merely because CheckOnly or a separate trial ended. Starting continuous Auto is its own requested outcome with current readiness.\n8. Report source/version, selected mode/path, exact diagnostic codes, final Auto/channel and verified/unverified areas. Keep original failed attempts, redact addresses/private transaction data from shared output, and save the stopping point. Do not turn recipes, short probes or SelfTest into physical LAN/IPv6/day-long/external-model certification.\n";
var AI_LAN_PROMPT_RU="Помоги использовать Windows LAN-помощник HomenS.AI Auto VPN на конкретном указанном мной роутере. Выполни доступную техническую работу реальными инструментами; облачный чат без доступа не считай клиентом моей LAN.\n\nПАРАМЕТРЫ\nАдрес приложения/реальный частный IP и порт: [проверенное значение]. Номер кабельного интерфейса: [проверенное значение]. Режим: [SelfTest / CheckOnly по умолчанию / ProbeOnly / отдельно разрешённый полный клиентский тест]. Время и разрешение на переподключение: [только для полного теста]. Источник помощника: тот же выбранный/установленный выпуск, не посторонний изменяемый скрипт.\n\nГРАНИЦЫ\nНепрерывному router-probed Auto подготовленного MT3000 не нужны этот LAN-тест или LAN-сертификат. Это отдельная необязательная проверка клиента. Полный тест меняет параметры теста приложения и может переключать трафик роутера; он не должен конкурировать с непрерывным Auto. Сначала заверши его штатный Stop/восстановление и проверь фактическое исходное состояние.\nИспользуй уже данное явное разрешение на такой же полный тест, не переспрашивай его повторно. Если его нет, подготовь конкретный ограниченный тест/отмену и уточни разрешение один раз до полного режима. Пароль и TEST владелец вводит приватно сам; не вводи подтверждения и не принимай условия вместо него.\nНе меняй NIC/DNS/маршруты/firewall компьютера, не отключай другой VPN, не подменяй прошивку/feeds и не сбрасывай бюджеты. Разбирай отказы, а не придумывай обход.\n\n1. Подтверди нужное устройство и путь управления, а не только ответ частного IP. Два адаптера могут вести к разным роутерам с одним адресом. До запроса пароля проверь обычный путь управления и явный кабельный путь. Текущий помощник отклоняет CLIENT-CONTROL-PATH-MISMATCH; в старом выпуске проверки может не быть, поэтому имя файла не доказательство. Browser-loopback переход не является реальным LAN-адресом проверки.\n2. Проверь pwsh -v. Нужен PowerShell7. Если установка уже входит в разрешённую настройку, используй официальный пакет: winget install --id Microsoft.PowerShell --exact. Иначе объясни недостающий компонент и конкретное требуемое действие.\n3. Скачай client-test.ps1 и start-lan-helper.ps1 с проверенного origin приложения, путь /luci-static/resources/view/homensai-vpn/. Сохрани вместе в новой приватной папке. Дополнительному start-lan-helper.cmd нужны оба файла. Зафиксируй выпуск/хеш/источник и прочитай скрипт. Не скачивай его с другого роутера лишь из-за совпадения IP.\n4. В этой папке выполни: pwsh -NoProfile -File .\\client-test.ps1 -SelfTest\nДля предпосылок пути: pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly\nДо запуска замени адрес и индекс примера проверенными параметрами. CheckOnly не проверяет Интернет/переключение и не спрашивает пароль.\n5. Для реальных привязанных DNS/HTTPS без включения Auto: pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -ProbeOnly\nПодставь реальные параметры. Измеряется этот IPv4-путь клиента, не все приложения/IPv6. Сетевые запросы выполняются, настройки роутера не меняются.\n6. Только для отдельно разрешённого полного теста проверь завершение прежнего Auto/восстановления и готовность платформы/пары клиентского режима. Выполни: pwsh -NoProfile -File .\\start-lan-helper.ps1\nВыбери режим3 с ограниченным сроком/окном. Владелец сам вводит приватный пароль и TEST. HTTP-управление не шифруется: нужна именно доверенная LAN либо HTTPS с правильно доверенным сертификатом. Не отключай TLS-проверку. Не читай, не печатай, не логируй и не сохраняй его пароль/сессию/токен/полную конфигурацию.\n7. Дождись фактического завершения. Stop в очереди не равен восстановлению. Код0 относится к выбранному режиму;2 — отказ/нет подтверждения/ошибка;3 — проверенный удержанный резерв, а не успешный возврат исходного пути. Не объявляй готовность непрерывного Auto лишь по CheckOnly или завершению отдельного теста. Его запуск — отдельный выбранный результат с текущей готовностью.\n8. Отчитайся об источнике/версии, режиме/пути, точных кодах, итоговом Auto/канале и проверенных/непроверенных областях. Сохраняй прежние неудачные попытки, обезличивай адреса/данные транзакций в общем отчёте и точку остановки. Рецепты, короткие пробы и SelfTest не являются приёмкой физического LAN/IPv6/суток или внешних ИИ-моделей.\n";
function renderAiPrompt(which){
  var lan=which==='lan';
  var text=lan?bi(AI_LAN_PROMPT_EN,AI_LAN_PROMPT_RU):bi(AI_PROMPT_EN,AI_PROMPT_RU);
  var copy=E('button',{'type':'button','class':'cbi-button cbi-button-action','click':function(){
    try{navigator.clipboard.writeText(text).then(function(){copy.textContent=bi('Prompt copied','Промпт скопирован');setTimeout(function(){copy.textContent=bi('Copy the prompt','Скопировать промпт');},3000);}).catch(function(){selectPrompt();});}catch(error){selectPrompt();}
  }},bi('Copy the prompt','Скопировать промпт'));
  var pre=E('pre',{'class':'hv-cmd hv-prompt','tabindex':'0'},text);
  function selectPrompt(){try{var range=document.createRange();range.selectNodeContents(pre);var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);}catch(e){}}
  return E('div',{'class':'hv-ai-prompt'},[
    E('p',{},lan?bi('Check the real client path yourself, or give this prompt to ChatGPT/Codex or Claude Code(Sonnet/Opus) with tools on a computer in this LAN. The helper is optional for prepared-MT3000 router-probed IPv4 Auto. A full switching trial is a separate operation.','Проверьте путь реального клиента самостоятельно или передайте этот промпт ChatGPT/Codex либо Claude Code(Sonnet/Opus) с инструментами на компьютере этой LAN. Для router-probed IPv4 Auto подготовленного MT3000 помощник необязателен. Полный тест с переключением — отдельная операция.'):bi('To have ChatGPT/Codex or Claude Code(Sonnet/Opus) install, configure and verify the application for you, copy the complete prompt below. The agent needs a terminal and access to your router. You provide secure access and personally accept first-use terms; the agent performs the authorized technical steps.','Если хотите, чтобы ChatGPT/Codex или Claude Code(Sonnet/Opus) установил, настроил и проверил программу за вас, скопируйте полный промпт ниже. Агенту нужны терминал и доступ к роутеру. Вы предоставляете защищённый доступ и лично принимаете первое соглашение; разрешённую техническую работу выполняет агент.')),
    lan?E('p',{'class':'hv-ready-intro'},bi('The prompt forbids the agent to ask for or type your password or the word TEST, and to turn Auto on; it must get your explicit yes before the full trial and stop at the first error. Read it before you paste it; the text below is exactly what is copied.','Промпт запрещает агенту спрашивать или вводить ваш пароль и слово TEST и включать Auto; перед полным тестом он обязан получить ваше явное «да» и остановиться на первой ошибке. Прочитайте его перед вставкой; ниже ровно тот текст, который копируется.')):E('p',{'class':'hv-ready-intro'},bi('The prompt covers installation, verified recovery, setup and checks. Auto is off by default and starts only if you select it and the platform is ready. It preserves your terms acceptance and reports unverified areas. Read it before you paste it; the text below is exactly what is copied.','Промпт охватывает установку, проверенную копию, настройку и проверки. Auto по умолчанию выключен; запускается только по вашему выбору и при готовой платформе. Принятие соглашения сохраняется, непроверенные области отмечаются явно. Прочитайте его перед вставкой; ниже ровно тот текст, который копируется.')),
    E('div',{'class':'hv-ai-actions'},[copy]),pre]);
}

HELP_TOPICS.unshift({id:'ai-prompt',title:['Prompt for your AI agent','Промпт для вашего ИИ-агента'],when:['You would rather let an AI agent install, check and configure everything for you.','Вы хотите, чтобы установку, проверку и настройку полностью сделал ИИ-агент.'],steps:[],custom:function(){return renderAiPrompt();}});

HELP_TOPICS.splice(1,0,{id:'ai-lan-prompt',title:['Prompt for your AI agent: run the LAN helper','Промпт для ИИ-агента: запустить LAN-помощник'],when:['You do not want to run the LAN helper by hand: an AI agent that can run commands on your computer does the steps and asks you only for what it must not do itself.','Вы не хотите запускать LAN-помощник вручную: ИИ-агент, который может выполнять команды на вашем компьютере, делает шаги сам и спрашивает вас только о том, что не имеет права делать сам.'],steps:[],custom:function(){return renderAiPrompt('lan');}});


ctx.extraHelpTopics.forEach(function(topic){if(topic.id!=='telegram'&&!HELP_TOPICS.some(function(t){return t.id===topic.id;}))HELP_TOPICS.push(topic);});
ctx.installCatalogue({rows:ERROR_ROWS,groups:ERROR_GROUPS,groupOf:ERROR_GROUP_OF,state:ERROR_TABLE_STATE,persist:persistErrorTableState});
ensureJournalDictionary();
return {renderHelp:renderHelp,renderLearn:renderLearn,renderErrorTable:renderErrorTable,renderSwitchPage:renderSwitchPage};
}});
