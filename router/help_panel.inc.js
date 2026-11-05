/* Built-in help: what to do when something is wrong. Data are [English, Russian] pairs; commands are never translated. */
var HELP_TOPICS=[
  {"id": "probe-boost", "open": false, "title": ["Probe level and automatic boost: how it works", "Уровень опроса и автоматическое ускорение: как это работает"], "when": ["You want to know exactly when the router checks more often and when it returns to the chosen level.", "Вы хотите точно знать, когда роутер начинает проверять чаще и когда возвращается к выбранному уровню."], "steps": [{"t": ["Probe level 1-5 sets two cadences. Channel health check (is internet working through the VPN): level 1 every 60 s, 2 every 30 s, 3 every 20 s, 4 every 15 s, 5 every 10 s. Three-site response measurement: 300, 120, 60, 45 and 30 s. The probe level is set in Settings → Router load (Console: Auto tab). The ping has its own interval in Router load → How response is measured: once a minute by default, from every 10 s to every 5 min. A failure is confirmed after 3 failed health checks in a row, so level 1 confirms in about 3 minutes and level 5 in about 30 s.", "Уровень опроса 1–5 задаёт два интервала. Проверка канала (работает ли интернет через VPN): уровень 1 — раз в 60 с, 2 — раз в 30 с, 3 — раз в 20 с, 4 — раз в 15 с, 5 — раз в 10 с. Замер отклика по трём сайтам: 300, 120, 60, 45 и 30 с. Уровень опроса задаётся в «Настройки → Нагрузка на роутер» (в «Пульте» — вкладка «Auto»). У пинга свой интервал в «Нагрузка на роутер» → «Как измеряется отклик»: по умолчанию раз в минуту, от раза в 10 с до раза в 5 мин. Сбой подтверждается после 3 неудачных проверок подряд, поэтому на уровне 1 это около 3 минут, на уровне 5 — около 30 с."]}, {"t": ["Automatic boost starts when Auto is running and watching (OBSERVING, COMMITTED or working on the reserve) and the primary or reserve channel fails one health check. From that moment the router checks every 10 s and measures the three-site response every 30 s, whatever level you chose (the ping keeps its own interval). Nothing is switched by the boost itself: it only makes the checks frequent so that a real failure is confirmed in about 30 s.", "Автоматическое ускорение включается, когда Auto работает и наблюдает (OBSERVING, COMMITTED или работа на резерве), а основной или резервный канал не прошёл одну проверку. С этого момента роутер проверяет каналы раз в 10 с и замеряет отклик трёх сайтов раз в 30 с, независимо от выбранного уровня (пинг сохраняет свой интервал). Само ускорение ничего не переключает: оно только учащает проверки, чтобы настоящий сбой подтвердился примерно за 30 с."]}, {"t": ["An episode lasts 10 minutes from the last failed check, but never longer than 20 minutes in total. It ends earlier in effect when its job is done: after Auto switched the channel, or after the failure was confirmed (3 failed checks), further failures no longer extend it.", "Эпизод длится 10 минут от последней неудачной проверки, но всего не дольше 20 минут. Как только задача выполнена — Auto переключил канал или сбой подтверждён (3 неудачные проверки), — новые неудачи его больше не продлевают."]}, {"t": ["When the episode ends, the router returns to your level and writes the result to the decision log: switched (Auto changed the channel), failure-confirmed (the channel really failed), false-alarm (one check failed, then the channel worked) or disabled (you turned the boost off). Then there is a 10-minute rest: no new episode starts, and the same channel cannot start one again until it has passed a check. A channel that stays down therefore cannot keep the router at the fast cadence forever.", "Когда эпизод закончился, роутер возвращается к вашему уровню и записывает итог в журнал решений: switched (Auto переключил канал), failure-confirmed (канал действительно отказал), false-alarm (одна проверка не прошла, потом канал работал) или disabled (вы выключили ускорение). Затем 10 минут отдыха: новый эпизод не начинается, а тот же канал не может начать его снова, пока не пройдёт проверку. Поэтому канал, который лежит долго, не держит роутер на частых проверках бесконечно."]}, {"t": ["The decision log lists every level change and every episode: time, level, what happened, which channel and its error code. Open it with the link «Decision log: levels and boost» in Router load → How response is measured, or in the Console on the Log tab. The Router load summary shows the chosen level and «· boost on» when the boost is enabled.", "Журнал решений перечисляет каждую смену уровня и каждый эпизод: время, уровень, что произошло, какой канал и код ошибки. Он открывается ссылкой «Журнал решений: уровни и ускорение» в «Нагрузка на роутер» → «Как измеряется отклик», а в «Пульте» — на вкладке «Журнал». В заголовке «Нагрузки на роутер» видны выбранный уровень и пометка «· ускорение вкл.», когда ускорение включено."]}, {"t": ["If the router refuses a level change (for example while a switch is running), the settings are not saved and a window shows the code; press Save again after the switch. A manual channel switch does not turn Auto off: Auto keeps watching the channel you chose, so the boost works the same way after a manual switch.", "Если роутер отклоняет смену уровня (например, во время переключения), настройки не сохраняются и окно показывает код; нажмите «Сохранить» ещё раз после переключения. Ручное переключение канала не выключает Auto: Auto продолжает следить за выбранным вами каналом, поэтому ускорение работает так же и после ручного переключения."]}]},
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
          "The method is chosen in Settings → Router load → How response is measured (Console: Auto tab → Router load). Default: ping (ICMP echo to 1.1.1.1, or 8.8.8.8 / 9.9.9.9) through each tunnel: small numbers, almost no router load, best for comparing the channels. Alternative: three websites. The router itself measures through each VPN tunnel, not your computer. Three websites are opened fresh: Google, Cloudflare and Wikipedia. Each time includes the DNS lookup, the TCP connection, the TLS encryption handshake and the complete HTTP headers.",
          "Способ выбирается в «Настройки → Нагрузка на роутер → Как измеряется отклик» (в «Пульте» — вкладка «Auto» → «Нагрузка на роутер»). По умолчанию — пинг (ICMP-запрос к 1.1.1.1, либо 8.8.8.8 / 9.9.9.9) через каждый туннель: небольшие числа, почти без нагрузки на роутер, лучше всего для сравнения каналов. Другой вариант — три сайта. Измеряет сам роутер через каждый VPN-туннель, а не ваш компьютер. Он заново открывает три сайта: Google, Cloudflare и Wikipedia. Каждое время включает поиск адреса (DNS), TCP-соединение, установку шифрования TLS и получение полных HTTP-заголовков."
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
          "How often: the ping has its own setting, Ping interval, in the same place (Router load → How response is measured): from every 10 s to every 5 min, once a minute by default. More frequent pings give fresher numbers but cost the router a little more CPU and traffic. The ping is sent during a channel check, so it is never more frequent than the checks of the probe level. The three websites follow the probe level in Router load (every 30 s at level 5, every 5 min at level 1, every 30 s during automatic boost). Each channel card shows the last value in ms and how long ago the channel was checked, for example 42 ms, checked 12 s ago; a dash means the router has no value for that channel yet. An old ping is only old: it never means the VPN is down. The response is information only: Auto decides on DNS and HTTPS health checks, not on the response time.",
          "Как часто: у пинга своя настройка «Интервал пинга» там же («Нагрузка на роутер» → «Как измеряется отклик»): от раза в 10 с до раза в 5 мин, по умолчанию раз в минуту. Чаще — свежее числа, но немного больше нагрузка на процессор роутера и трафик. Пинг отправляется во время проверки каналов, поэтому не бывает чаще проверок уровня опроса. Три сайта следуют уровню опроса в «Нагрузке на роутер» (раз в 30 с на уровне 5, раз в 5 мин на уровне 1, раз в 30 с во время автоускорения). Каждая карточка канала показывает последнее значение в мс и сколько времени назад канал проверялся, например 42 мс, проверено 12 с назад; прочерк означает, что значения от роутера для этого канала ещё нет. Старый пинг — просто старый: он не означает, что VPN не работает. Отклик — только информация: Auto решает по проверкам DNS и HTTPS, а не по времени отклика."
        ]
      },
      {
        "t": [
          "The delay chart and the statistics follow the method you chose; the ping history is kept separately. The option \"Measure all methods (comparison)\" makes every check also ping the other DNS addresses and open the three websites; the router collects these extra values for comparison, while the page shows the chosen method. Switching still uses only the chosen method.",
          "График задержки и статистика следуют выбранному способу; история пинга хранится отдельно. Параметр «Мерить все способы (сравнение)» заставляет каждую проверку дополнительно пинговать остальные DNS-адреса и открывать три сайта; роутер собирает эти дополнительные значения для сравнения, а страница показывает выбранный способ. Переключение по-прежнему использует только выбранный способ."
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
      "You want to know what Auto does after you turn its switch on and what the router checks.",
      "Вы хотите знать, что делает Auto после включения переключателя Auto и что проверяет роутер."
    ],
    "steps": [
      {
        "t": [
          "Auto starts the saved primary and reserve, checks IPv4 DNS/HTTPS, switches after repeated failures and returns after stable recovery according to your settings. The Auto switch is on «Home» in the Simple view and in the top strip of the Console view; you can turn Auto off during startup too. Auto that you turned on comes back by itself after a reboot or power cut, with every start check; turning it off cancels that.",
          "Auto запускает сохранённые основной и резервный VPN, проверяет IPv4 DNS/HTTPS, переключается после повторных отказов и возвращается после устойчивого восстановления по вашим настройкам. Переключатель Auto находится на «Главной» в виде «Простой» и в верхней полосе вида «Пульт»; выключить Auto можно и во время запуска. Auto, который вы включили сами, после перезагрузки или отключения питания включается снова сам, со всеми проверками запуска; выключение Auto это отменяет."
        ]
      },
      {
        "t": [
          "About these checks: two selected VPN channels; the router checks them itself through each tunnel. How often is set by the probe level in Settings → Router load, Console: Auto tab (every 60 s at level 1 down to every 10 s at level 5); a failure is confirmed after 3 failed checks.",
          "Об этих проверках: два выбранных VPN-канала; проверку делает сам роутер через каждый туннель. Как часто — задаёт уровень опроса в «Настройки → Нагрузка на роутер», в «Пульте» — вкладка «Auto» (от раза в 60 с на уровне 1 до раза в 10 с на уровне 5); сбой подтверждается после 3 неудачных проверок."
        ]
      },
      {
        "t": [
          "Lamp colours are the same in both views (Simple and Console). A channel lamp: green — the channel works (the chip \"Traffic here\" marks the one carrying your traffic, \"Standing by\" the other); yellow — it is being checked or a switch is under way; red — it does not respond or its tunnel is off (with the code); grey — no fresh data from the router. The big lamp next to the status line shows the whole VPN: green — the VPN works on the primary; yellow — the reserve is in use, a switch or a check is under way; red — the current channel or both channels fail; grey — no fresh data. The Auto switch says its state in words: Auto is on, Turning Auto on…, Auto is off and so on. \"Switch here\" appears only on the card of the channel that does not carry traffic.",
          "Цвета ламп одинаковы в обоих видах («Простой» и «Пульт»). Лампа канала: зелёный — канал работает (метка «Трафик здесь» отмечает канал, который несёт ваш трафик, «Ждёт в резерве» — другой); жёлтый — идёт проверка или переключение; красный — канал не отвечает или его туннель отключён (с кодом); серый — нет свежих данных от роутера. Большая лампа рядом со строкой состояния показывает VPN целиком: зелёный — VPN работает через основной; жёлтый — работает резерв, идёт переключение или проверка; красный — не отвечает текущий канал или оба канала; серый — нет свежих данных. Переключатель Auto пишет своё состояние словами: «Auto включён», «Включение Auto…», «Auto выключен» и т. д. Кнопка «Переключить сюда» есть только на карточке канала, который не несёт трафик."
        ]
      },
      {
        "t": [
          "No internet? Open the Help topic \"I have no internet\" for the recovery steps (Simple view: \"? Help\" in the top menu; Console: System tab → Help, codes, training).",
          "Нет интернета? Откройте в «Помощи» тему «У меня пропал интернет» — там порядок восстановления (вид «Простой»: «? Помощь» в верхнем меню; «Пульт»: вкладка «Система» → «Помощь, коды, обучение»)."
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
          "The current Auto state and the channel carrying traffic are on Home (Simple view) or the Channels tab (Console). The sequence of decisions and their reasons is in Events and reasons on Home, the Log tab of the Console, and the live log (Settings → System and diagnostics → Live log; Console: Log → Live log). If observations are stale, press Check now; it refreshes checks without choosing a channel for you.",
          "Текущее состояние Auto и канал, который несёт трафик, видны на «Главной» (вид «Простой») или на вкладке «Каналы» («Пульт»). Последовательность решений и их причины — в «Событиях и причинах» на «Главной», на вкладке «Журнал» в «Пульте» и в живом журнале («Настройки → Система и диагностика → Живой журнал»; в «Пульте» — «Журнал» → «Живой журнал»). Если наблюдения устарели, нажмите «Проверить сейчас»: это обновляет проверки без выбора канала за вас."
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
          "On Home (Console: Channels tab) check which channel carries traffic and whether both channel cards have fresh results. A working reserve is a normal state. Select another channel only when its readiness is confirmed; do not return to a failed primary just because it is called primary.",
          "На «Главной» (в «Пульте» — вкладка «Каналы») проверьте, какой канал несёт трафик и свежие ли данные на обеих карточках каналов. Исправный резерв — нормальное состояние. Выбирайте другой канал только при подтверждённой готовности; не возвращайтесь на неисправный основной лишь из-за его названия."
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
          "A router reboot is a last recovery step when you still control the device. It interrupts connectivity and does not repair a bad VPN configuration. Auto that you turned on comes back by itself after the reboot, with every start check; if you turned Auto off, it stays off.",
          "Перезагрузка — последний шаг восстановления, если управление устройством сохранено. Она прерывает связь и не исправляет неверную VPN-конфигурацию. После неё Auto, который вы включили сами, включается снова сам со всеми проверками запуска; если вы выключили Auto, он останется выключенным."
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
      "The reserve carries traffic, you want to return, or turning Auto off left the router on the reserve.",
      "Трафик идёт через исправный резерв, нужен возврат либо после выключения Auto остался резерв."
    ],
    "steps": [
      {
        "t": [
          "Check both channel cards on Home (Console: Channels tab): which one shows \"Traffic here\" and whether both have fresh checks. Being on reserve does not by itself mean an error.",
          "Проверьте обе карточки каналов на «Главной» (в «Пульте» — вкладка «Каналы»): на какой стоит «Трафик здесь» и свежие ли проверки у обеих. Работа на резерве сама по себе не означает ошибку."
        ]
      },
      {
        "t": [
          "For an intentional return, press \"Switch here\" on the Primary card when the primary is confirmed working and the button is available. A manual switch never turns Auto off: Auto keeps watching the channel you chose and moves traffic to the other one if it fails (there is no separate Resume Auto button). If turning Auto off left the router on the reserve, use the same \"Switch here\" on the Primary card and verify its actual result.",
          "Для осознанного возврата нажмите «Переключить сюда» на карточке «Основной», когда основной подтверждённо работает и кнопка доступна. Ручное переключение никогда не выключает Auto: Auto продолжает следить за выбранным вами каналом и переносит трафик на другой, если этот откажет (отдельной кнопки «Возобновить Auto» нет). Если после выключения Auto остался резерв, используйте ту же кнопку «Переключить сюда» на карточке «Основной» и проверьте фактический итог."
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
      "Turning the Auto switch on shows a message with a code.",
      "При включении переключателя Auto появляется сообщение с кодом."
    ],
    "steps": [
      {
        "t": [
          "Open Router readiness (Settings → System and diagnostics; Console: System tab) and read the Auto status line on Home or in the Console strip. Press the code in the message: its explanation names the exact refused condition. A green dry-run forecast is not a separate permission to start.",
          "Откройте «Готовность роутера» («Настройки → Система и диагностика»; в «Пульте» — вкладка «Система») и прочитайте строку состояния Auto на «Главной» или в полосе «Пульта». Нажмите код в сообщении: его объяснение называет конкретное условие отказа. Зелёный прогноз не является отдельным разрешением запуска."
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
          "Wait for current observations after changing profiles. Turning the switch on again and again does not repair an identity, worker or policy mismatch. The Auto switch remains available to turn Auto off or cancel startup.",
          "После смены профилей дождитесь текущих наблюдений. Повторные включения переключателя не исправляют несовпадение идентичности, служб или политики. Переключатель Auto остаётся доступным, чтобы выключить Auto или отменить запуск."
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
          "Download client-test.ps1 and start-lan-helper.ps1 into one folder: Settings → System and diagnostics → \"Download LAN helper\" and the launcher link next to it (Console: System tab → Help, codes, training). The optional start-lan-helper.cmd shortcut needs both of those files.",
          "Скачайте client-test.ps1 и start-lan-helper.ps1 в одну папку: «Настройки → Система и диагностика» → «Скачать LAN-помощник» и ссылка на скрипт запуска рядом (в «Пульте» — вкладка «Система» → «Помощь, коды, обучение»). Необязательный ярлык start-lan-helper.cmd требует наличия обоих файлов."
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
      "After an update, the page looks old, shows errors, or the status is stale.",
      "После обновления страница выглядит по-старому, показывает ошибки или статус устарел."
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
          "Check the Monitoring service lamp (Settings → System and diagnostics; Console: System tab). If it offers \"Restore monitoring\", press it; if the monitor services stay stopped, start those services over SSH and wait for a fresh timestamp; this is separate from turning Auto on.",
          "Проверьте лампу «Служба мониторинга» («Настройки → Система и диагностика»; в «Пульте» — вкладка «Система»). Если там есть кнопка «Восстановить мониторинг», нажмите её; если службы остаются остановленными, запустите их по SSH и дождитесь свежей даты; это отдельно от запуска Auto."
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
      "The page says the VPN rules were changed by someone else.",
      "Страница пишет, что правила VPN изменил кто-то другой."
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
          "Check the current selected pair and the stock VPN configuration. If you intend to edit stock profiles, turn Auto off and wait for the managed recovery first.",
          "Проверьте текущую пару и штатную VPN-конфигурацию. Если намерены менять штатные профили, сначала выключите Auto и дождитесь управляемого восстановления."
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
      "The page shows a Telegram error code, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.",
      "Страница показывает код ошибки Telegram, тестовое сообщение не приходит или вы настраиваете Telegram впервые. Нужны три вещи: бот, его токен и ID чата."
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
          "On the router open Settings → Telegram notifications (Console: System tab → Telegram notifications; in the first-run wizard it is step 3, Behaviour). Tick Send reports, enter the token privately and the verified chat ID or channel username as Recipient, choose when and what to send and press Save. An empty token field keeps the stored token.",
          "На роутере откройте «Настройки → Уведомления в Telegram» (в «Пульте» — вкладка «Система» → «Уведомления в Telegram»; в мастере первой настройки — шаг 3 «Поведение»). Включите «Присылать отчёты», приватно введите токен и проверенный ID чата или имя канала в поле «Получатель», выберите, когда и что присылать, и нажмите «Сохранить». Пустое поле токена оставляет сохранённый токен."
        ]
      },
      {
        "t": [
          "Press “Send a test message”. A message should arrive within a few seconds. If a code is shown instead: TELEGRAM-… with “401” or “Unauthorized” means a wrong token; “400”, “chat not found” or “Forbidden” means a wrong Chat ID or you never pressed Start; a timeout means the router has no internet or a wrong clock.",
          "Нажмите «Отправить тестовое сообщение». Сообщение должно прийти за несколько секунд. Если показан код TELEGRAM-…: «401» или «Unauthorized» — неверный токен; «400», «chat not found» или «Forbidden» — неверный ID чата или вы не нажали Start; тайм-аут — у роутера нет интернета или неверные часы."
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
          "Turn Auto off and verify the actual managed recovery and guard state before removing the package. If turning Auto off retained a reserve or recovery is unconfirmed, resolve the recorded condition first; do not force a return to an unhealthy primary. Then remove normally over SSH.",
          "Перед удалением выключите Auto и проверьте фактическое управляемое восстановление и блокировки. Если остался резерв либо итог не подтверждён, сначала разберите записанное условие; не форсируйте возврат на неисправный основной. Затем удаляйте штатно по SSH."
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
          "Settings → History and memory (Console: System tab): set Live log entries from 1 to 2000 and Keep detailed history from 1 to 7 days. These two change with Auto off. Save and verify the values.",
          "«Настройки → История и память» (в «Пульте» — вкладка «Система»): задайте «Записей в живом журнале» от 1 до 2000 и «Хранить подробную историю» от 1 до 7 дней. Эти два значения меняются при выключенном Auto. Сохраните и проверьте значения."
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
          "Open the failure test: Home → Tests → Failure test, button \"Check that Auto rescues\" (Console: Auto tab → \"Run failure test\"). Auto must be on. The channel carrying traffic is selected automatically; primary and reserve are both supported.",
          "Откройте тест сбоя: «Главная» → «Проверки» → «Тест сбоя», кнопка «Проверить, что Auto спасёт» (в «Пульте» — вкладка «Auto» → «Запустить тест сбоя»). Auto должен быть включён. Канал, который несёт трафик, выбирается автоматически: поддержаны основной и резервный."
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
          "The test temporarily drops IPv4 traffic on that tunnel device, not the VPN process or another server selected by name. It waits for failure thresholds and a fresh confirmed alternate route. \"Stop and remove fault\" removes the artificial fault early.",
          "Тест временно блокирует IPv4-трафик устройства туннеля, а не VPN-процесс и не другой сервер по имени. Он ожидает пороги ошибок и свежий подтверждённый другой маршрут. «Остановить и снять сбой» досрочно снимает искусственную блокировку."
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
    E('p',{'class':'hv-schematic-note'},bi('When automatic return is enabled and the reserve fails, a verified primary may be restored earlier than the normal reserve dwell. These values are changed in Settings → How fast to switch → Custom values (Console: Auto tab). A dash means the router did not provide a value.','Если автоматический возврат включён и резерв отказал, проверенный основной может быть возвращён раньше обычной паузы пребывания на резерве. Значения меняются в «Настройки → Как быстро переключать → Свои значения» (в «Пульте» — вкладка «Auto»). Прочерк означает, что роутер не передал значение.')),
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
    ['Router','Роутер',
     'The router model, firmware and required parts are detected automatically and shown with lamps (Python, ubus · uci · ip · Lua · rpcd, certificates, settings storage, router preparation). A model cannot be chosen by hand: readiness checks are mandatory. A red row names its code; press it for the explanation. Nothing is changed in this step. Example: GL-MT3000, firmware 4.11.0, all rows green.',
     'Модель роутера, прошивка и нужные части определяются автоматически и показываются лампами (Python, ubus · uci · ip · Lua · rpcd, сертификаты, хранилище настроек, подготовка роутера). Выбрать модель вручную нельзя: проверки готовности обязательны. Красная строка называет свой код; нажмите его, чтобы прочитать объяснение. На этом шаге ничего не меняется. Пример: GL-MT3000, прошивка 4.11.0, все строки зелёные.'],
    ['Channels','Каналы',
     'The wizard lists the VPN clients already configured in the GL.iNet panel → VPN, with protocol and response. Choose Primary (used always) and Reserve (used on a failure); they must be two different clients. The prepared MT3000 uses one WireGuard and one OpenVPN client; either can be primary. Missing one? Add a profile in GL.iNet → VPN first and open the wizard again. Example: primary WireGuard Germany, reserve OpenVPN Netherlands.',
     'Мастер показывает VPN-клиенты, уже настроенные в панели GL.iNet → VPN, с протоколом и откликом. Выберите «Основной» (используется всегда) и «Резерв» (используется при сбое): это должны быть два разных клиента. На подготовленном MT3000 это один клиент WireGuard и один OpenVPN; любой может быть основным. Нужного нет? Сначала добавьте профиль в GL.iNet → VPN и откройте мастер снова. Пример: основной WireGuard Германия, резерв OpenVPN Нидерланды.'],
    ['Behaviour','Поведение',
     'You can keep the defaults: they were verified on a router. How fast to switch: Calm, Normal (default: 3 failures, 60 s pause, return after 2 checks over 30 s) or Fast; when the primary is healthy again, return automatically or stay on the working reserve; allow a brief drop of calls and downloads, otherwise Auto does not switch during an active session. Router load: probe level 1–5 (Balanced = a check every 20 s) and automatic boost. Telegram is optional: tick Send switch reports, enter the bot token and the recipient. Example: Normal, level 3, Telegram off.',
     'Можно оставить как есть: значения по умолчанию проверены на роутере. «Как быстро переключать»: «Спокойно», «Обычно» (по умолчанию: 3 ошибки, пауза 60 с, возврат после 2 проверок за 30 с) или «Быстро»; когда основной снова здоров — вернуться на него автоматически или оставаться на работающем резерве; разрешить короткий обрыв звонков и загрузок, иначе Auto не переключит во время активной сессии. «Нагрузка на роутер»: уровень опроса 1–5 («Сбалансировано» — проверка раз в 20 с) и автоматическое ускорение. Telegram необязателен: включите «Присылать отчёты о переходах», укажите токен бота и получателя. Пример: «Обычно», уровень 3, Telegram выключен.'],
    ['Terms and start','Условия и запуск',
     'Review the summary: primary, reserve, switching, load and Telegram. If the terms are not accepted yet, read them and tick both boxes yourself; they are never pre-ticked. Save without starting writes the settings and leaves Auto off. Accept terms and turn Auto on (or Turn Auto on, when the terms are already accepted) saves and then starts Auto with its usual readiness checks. Back corrects a value; Next alone saves nothing. Later the same settings are in Settings, and Settings → Language and look → Run the wizard again opens this wizard again (Console: System tab).',
     'Проверьте сводку: основной, резерв, переключение, нагрузка и Telegram. Если условия ещё не приняты, прочитайте их и сами отметьте обе галочки: они никогда не ставятся заранее. «Сохранить без запуска» записывает настройки и оставляет Auto выключенным. «Принять условия и включить Auto» (или «Включить Auto», если условия уже приняты) сохраняет настройки и затем включает Auto с обычными проверками готовности. «Назад» позволяет исправить значение; «Далее» само ничего не сохраняет. Позже те же настройки есть в «Настройках», а «Настройки → Язык и вид → Пройти мастер заново» открывает этот мастер снова (в «Пульте» — вкладка «Система»).']
  ];
  return E('div',{'class':'hv-setup-guide','data-setup-guide':'1'},[
    E('p',{},bi('The wizard opens by itself on the first visit: Router → Channels → Behaviour → Terms and start, about 2 minutes. The experimental-software agreement and the license terms (HomenSAI Personal & Commercial Source License v1.0) are shown at the last step; previously accepted terms are remembered on this router and are not asked again. Close the wizard without changes (shown once setup is complete) keeps the router settings as they are. Saving never starts Auto by itself; only the start button of the last step or the Auto switch does.','Мастер открывается сам при первом входе: «Роутер → Каналы → Поведение → Условия и запуск», около 2 минут. Соглашение об экспериментальном ПО и условия лицензии (HomenSAI Personal & Commercial Source License v1.0) показываются на последнем шаге; ранее принятые условия сохраняются на этом роутере и повторно не запрашиваются. «Закрыть мастер без изменений» (появляется, когда настройка уже завершена) оставляет настройки роутера как есть. Сохранение само никогда не включает Auto: его включает только кнопка запуска на последнем шаге или переключатель Auto.')),
    E('ol',{'class':'hv-help-steps'},steps.map(function(row,index){return E('li',{'data-setup-guide-step':String(index+1)},[E('h3',{},bi(row[0],row[1])),E('p',{},bi(row[2],row[3]))]);}))
  ]);
}
HELP_TOPICS.push({id:'setup-guide',open:false,title:['First setup: four steps with examples','Первая настройка: четыре шага с примерами'],when:['Help for the first-run wizard (Router → Channels → Behaviour → Terms and start). Reading it saves nothing.','Помощь по мастеру первой настройки («Роутер → Каналы → Поведение → Условия и запуск»). Чтение ничего не сохраняет.'],steps:[],custom:renderOnboardingGuide});
// Specific readiness links land on their own explanation, never an unrelated generic topic.
if(typeof READINESS_GUIDES!=='undefined'){
  Object.keys(READINESS_GUIDES).forEach(function(code){var label=READINESS_CHECKS[code];
    HELP_TOPICS.push({id:'dependency-'+code,title:[label[0]+': install or repair',label[1]+': установка или исправление'],when:['A required router check failed or is unknown.','Нужный компонент отсутствует или его состояние неизвестно.'],steps:[],custom:function(){return renderReadinessHelp(code);}});
  });
}
HELP_TOPICS.push({id:'router-preparation',title:['Persistent router preparation: inspect before changing','Постоянная подготовка роутера: проверка до изменений'],when:['The row Router preparation (acceleration) in Router readiness is not done, or a PREP-… code is red or unverified. This is separate from installing application dependencies.','Строка «Подготовка роутера (ускорение)» в «Готовности роутера» не выполнена либо код PREP-… красный или не проверен. Это отдельная задача от установки зависимостей приложения.'],steps:[
  {t:['Read the actual model, firmware and the row Router preparation (acceleration) in Router readiness (Settings → System and diagnostics; Console: System tab); open each PREP-… code shown. The current profile is for prepared MT3000/4.11.0. Saved settings and loaded modules alone do not prove runtime readiness.','Проверьте реальную модель, прошивку и строку «Подготовка роутера (ускорение)» в «Готовности роутера» («Настройки → Система и диагностика»; в «Пульте» — вкладка «Система»); откройте каждый показанный код PREP-…. Текущая проверенная конфигурация относится к MT3000/4.11.0. Сохранённые флаги и загруженные модули сами по себе не доказывают готовность.']},
  {t:['Before changing acceleration, stock VPN startup or DNS, preserve a verified private backup and the exact original values/files. Establish the specific preparation scope and undo procedure; do not copy another device\'s commands blindly.','Перед изменением ускорения, штатного запуска VPN или DNS сохраните проверенную приватную копию и исходные значения/файлы. Определите конкретный объём подготовки и отмену; не копируйте команды другого роутера вслепую.']},
  {t:['Do not force-unload modules, remove drivers, disable a working DNS owner or alter computer networking. Recheck fresh status after the approved changes. A green preparation row does not start Auto or prove external LAN connectivity. The full operation/undo record is docs/ROUTER-PREPARATION.md in the project repository.','Не выгружайте модули принудительно, не удаляйте драйверы, не отключайте работающего DNS-владельца и не меняйте сеть компьютера. После разрешённых изменений перепроверьте свежие данные. Зелёная подготовка не запускает Auto и не доказывает связь LAN. Полная инструкция с отменой — docs/ROUTER-PREPARATION.md в репозитории проекта.']}
]});
HELP_TOPICS.push({id:'diagnose-all',title:['Cannot find the cause: complete AI diagnosis','Причина неизвестна: полная диагностика с ИИ'],when:['No Help topic explains your symptoms or several parts fail together.','Подходящий ответ не найден либо одновременно не работают несколько частей.'],steps:[],custom:function(){return renderDiagnosticPrompt(null,true);}});
HELP_TOPICS.push({id:'network-acceleration',title:['Auto blocked: hardware and network acceleration','Auto заблокирован: аппаратное и сетевое ускорение'],when:['Start reports HNAT, hardware acceleration or PREP-HNAT-CONFIG.','Запуск сообщает об HNAT, аппаратном ускорении или PREP-HNAT-CONFIG.'],steps:[],custom:function(){return renderAutoRemedy('HARDWARE-ACCELERATOR-UNVERIFIED');}});
// Statistics storage (owner, 31 Oct 2026; page 03 Nov 2026): Settings → History and memory (router/ui/settings.js).
HELP_TOPICS.push({id:'stats-retention',open:false,title:['How long statistics are kept and how much memory they use','Сколько хранить статистику и сколько она занимает'],
  when:['You want charts and rankings to remember more or fewer days, or you worry about flash and memory.','Нужно, чтобы графики и рейтинги помнили больше или меньше дней, или беспокоят флеш и память.'],
  steps:[{t:['Open Settings → History and memory (in the Expert group; Console: System tab).','Откройте «Настройки → История и память» (группа «Для эксперта»; в «Пульте» — вкладка «Система»).']},
    {t:['Statistics collection: Work keeps only what is needed and saves flash; Diagnostics records in detail for a chosen period (24 h, 72 h, 7 or 14 days) and returns to Work by itself. Keep detailed history: 1 to 7 days; Live log entries: 1 to 2000.','«Сбор статистики»: «Работа» хранит только нужное и бережёт флеш; «Диагностика» записывает подробно на выбранный срок (24 ч, 72 ч, 7 или 14 дней) и сама возвращается в «Работу». «Хранить подробную историю»: от 1 до 7 дней; «Записей в живом журнале»: от 1 до 2000.']},
    {t:['Read the line below the fields: how much RAM and flash the statistics use now and how much flash is free.','Посмотрите строку под полями: сколько сейчас занимает статистика в ОЗУ и на флеше и сколько флеша свободно.']},
    {t:['Press Save. The history period and the live log change only with Auto off; saving then offers to stop Auto and never starts it again by itself. The router deletes statistics older than the period. Switching and Auto do not depend on this setting. Reset statistics… in the same section clears the counters and charts; old data is archived on the router.','Нажмите «Сохранить». Срок истории и живой журнал меняются только при выключенном Auto: при сохранении программа предложит остановить Auto и сама его снова не включит. Роутер удалит статистику старше срока. Переключение и Auto от этой настройки не зависят. «Сбросить статистику…» в том же разделе обнуляет счётчики и графики; старые данные архивируются на роутере.']}]});
HELP_TOPICS.push({id:'preparation-buttons',title:['Router preparation when Auto is turned on','Подготовка роутера при включении Auto'],when:['Router readiness shows «Router preparation (acceleration)» as needed, or turning Auto on reports a PREP-… or PREPARATION-… code.','«Готовность роутера» показывает, что нужна «Подготовка роутера (ускорение)», или при включении Auto появляется код PREP-… либо PREPARATION-….'],steps:[
 {t:['Where: Settings → System and diagnostics → Router readiness (Console: System tab). The page has no separate Disable buttons: turning the Auto switch on is your consent to the preparation Auto needs, and the router performs it itself before starting.','Где: «Настройки → Система и диагностика → Готовность роутера» (в «Пульте» — вкладка «Система»). Отдельных кнопок отключения на странице нет: включение переключателя Auto — ваше согласие на нужную ему подготовку, и роутер выполняет её сам перед запуском.']},
 {t:['Each failed check that can be repaired without a router restart is fixed with the same reviewed writer as before: the app first preserves the original value privately, then changes only that setting and reads the result again. No VPN reconnect or automatic reboot occurs.','Каждая непройденная проверка, которую можно исправить без перезагрузки роутера, исправляется тем же проверенным способом, что и раньше: приложение сначала приватно сохраняет исходное значение, затем меняет только эту настройку и читает результат заново. VPN не переподключается, автоматической перезагрузки нет.']},
 {t:['Startup switches do not stop a running service. SFE module autoload preserves the exact original file; live modules are not forcibly unloaded. Firewall offloading is saved without a firewall reload. When restart is required, Auto refuses with PREPARATION-RESTART-REQUIRED and remains blocked until a separate deliberate router reboot and fresh checks. Firewall flow offloading is not changed automatically: switch it off yourself as its code explains.','Переключатели автозапуска не останавливают работающую службу. При отключении автозагрузки SFE точный исходный файл сохраняется; работающие модули принудительно не выгружаются. Flow offloading сохраняется без перезапуска firewall. Если нужна перезагрузка, Auto отказывает с кодом PREPARATION-RESTART-REQUIRED и остаётся заблокирован до отдельной осознанной перезагрузки роутера и свежих проверок. Flow offloading межсетевого экрана автоматически не меняется: выключите его сами, как объясняет его код.']},
 {t:['An uncertain reply is not success. Keep /etc/homensai-vpn/preparation-changes for recovery and inspect the actual state before another attempt. Unknown firmware, bindings, saved files or active recovery cannot be bypassed by turning Auto on again.','Неопределённый ответ не означает успех. Сохраните /etc/homensai-vpn/preparation-changes для восстановления и проверьте реальное состояние до новой попытки. Неизвестную прошивку, привязки, сохранённые файлы или активное восстановление повторное включение Auto не обходит.']}
]});
// The terms can be re-read at any time (same points as the first-run screen).

HELP_TOPICS.push({"id":"website-response","open":false,"title":["Three-site response: method and history","Ответ трёх сайтов: метод и история"],"when":["You want to understand the single displayed VPN response metric and gaps.","Вы хотите понять единую показанную метрику ответа VPN и пропуски."],"steps":[{"t":["Every selected VPN checks the same three ordinary HTTPS addresses: Google generate_204, Cloudflare cdn-cgi/trace and Wikipedia. Fresh DNS, TCP, TLS and all HTTP response headers are timed. This is not full webpage rendering, ICMP, or the separate technical DNS/HTTPS health probe.","Каждый выбранный VPN проверяет те же три обычных HTTPS-адреса: Google generate_204, Cloudflare cdn-cgi/trace и Wikipedia. Измеряются новый DNS, TCP, TLS и полные HTTP-заголовки ответа. Это не загрузка полной страницы, не ICMP и не отдельная техническая проверка DNS/HTTPS."]},{"t":["The displayed value is the arithmetic mean only when all three sites pass. A partial check shows coverage and no number; failures and timeouts are never zero and old metrics are never substituted. The value is fresh for at most45 seconds and is bound to the VPN generation.","Показанное число — среднее арифметическое только при успехе всех трёх сайтов. Неполная проверка показывает полноту без числа; ошибки и тайм-ауты никогда не считаются нулём, старые метрики не подставляются. Значение свежее не дольше45 секунд и привязано к поколению VPN."]},{"t":["Statistics follow the selected graph window. Mean is weighted by complete three-site cycles; minimum and maximum describe observed minute means. Missing periods and incomplete checks are not filled.","Статистика соответствует выбранному периоду графика. Средняя учитывает число полных проверок трёх сайтов; минимум и максимум относятся к наблюдённым минутным средним. Пропуски и неполные проверки не дорисовываются."]},{"t":["Storage follows the configured1–7 days. Older deleted measurements cannot be restored. Wide views sample markers; lines and statistics use retained measurements. History starts when recording begins and is saved at the configured checkpoint interval.","Хранение соответствует настройке1–7 дней. Удалённые старые замеры не восстанавливаются. В широком периоде метки выбираются, линии и статистика используют сохранённые измерения. История начинается с записи и сохраняется с заданным интервалом checkpoint."]},{"t":["Quality and ranking use these same complete website cycles. Resetting statistics sets a new counting boundary while preserving graph history. A lower mean is a recommendation, never permission to alter routes or enable Auto. Old event HTTPS measurements remain explicitly technical.","Качество и рейтинг используют те же полные проверки сайтов. Сброс статистики задаёт новую границу подсчёта, сохраняя историю графика. Меньшая средняя — рекомендация, а не разрешение менять маршруты или включать Auto. Старые HTTPS-замеры событий явно названы техническими."]}]});
