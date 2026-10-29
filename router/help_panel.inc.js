/* Built-in help: what to do when something is wrong. Data are [English, Russian] pairs; commands are never translated. */
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

// Text with `inline code` pieces: the same dark monospace style everywhere.
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

var helpNode=null;
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
// Specific readiness links land on their own explanation, never an unrelated generic topic.
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
// The terms can be re-read at any time (same points as the first-run screen).

HELP_TOPICS.push({"id":"website-response","open":false,"title":["Three-site response: method and history","Ответ трёх сайтов: метод и история"],"when":["You want to understand the single displayed VPN response metric and gaps.","Вы хотите понять единую показанную метрику ответа VPN и пропуски."],"steps":[{"t":["Every selected VPN checks the same three ordinary HTTPS addresses: Google generate_204, Cloudflare cdn-cgi/trace and Wikipedia. Fresh DNS, TCP, TLS and all HTTP response headers are timed. This is not full webpage rendering, ICMP, or the separate technical DNS/HTTPS health probe.","Каждый выбранный VPN проверяет те же три обычных HTTPS-адреса: Google generate_204, Cloudflare cdn-cgi/trace и Wikipedia. Измеряются новый DNS, TCP, TLS и полные HTTP-заголовки ответа. Это не загрузка полной страницы, не ICMP и не отдельная техническая проверка DNS/HTTPS."]},{"t":["The displayed value is the arithmetic mean only when all three sites pass. A partial check shows coverage and no number; failures and timeouts are never zero and old metrics are never substituted. The value is fresh for at most45 seconds and is bound to the VPN generation.","Показанное число — среднее арифметическое только при успехе всех трёх сайтов. Неполная проверка показывает полноту без числа; ошибки и тайм-ауты никогда не считаются нулём, старые метрики не подставляются. Значение свежее не дольше45 секунд и привязано к поколению VPN."]},{"t":["Statistics follow the selected graph window. Mean is weighted by complete three-site cycles; minimum and maximum describe observed minute means. Missing periods and incomplete checks are not filled.","Статистика соответствует выбранному периоду графика. Средняя учитывает число полных проверок трёх сайтов; минимум и максимум относятся к наблюдённым минутным средним. Пропуски и неполные проверки не дорисовываются."]},{"t":["Storage follows the configured1–7 days. Older deleted measurements cannot be restored. Wide views sample markers; lines and statistics use retained measurements. History starts when recording begins and is saved at the configured checkpoint interval.","Хранение соответствует настройке1–7 дней. Удалённые старые замеры не восстанавливаются. В широком периоде метки выбираются, линии и статистика используют сохранённые измерения. История начинается с записи и сохраняется с заданным интервалом checkpoint."]},{"t":["Quality and ranking use these same complete website cycles. Resetting statistics sets a new counting boundary while preserving graph history. A lower mean is a recommendation, never permission to alter routes or enable Auto. Old event HTTPS measurements remain explicitly technical.","Качество и рейтинг используют те же полные проверки сайтов. Сброс статистики задаёт новую границу подсчёта, сохраняя историю графика. Меньшая средняя — рекомендация, а не разрешение менять маршруты или включать Auto. Старые HTTPS-замеры событий явно названы техническими."]}]});
