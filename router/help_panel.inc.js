/* Built-in help: what to do when something is wrong. Data are [English, Russian] pairs; commands are never translated. */
var HELP_TOPICS=[
  {id:'no-internet',open:true,
   title:["I have no internet","У меня пропал интернет"],
   when:["Devices on your network cannot open sites after Auto ran or after you changed VPN settings.","Устройства в сети не открывают сайты после работы Auto или после смены настроек VPN."],
   steps:[
    {t:["Use another connection to read this page (a phone with mobile data), or open this Help page on a device that still reaches the router address.","Откройте эту страницу через другое подключение (телефон с мобильным интернетом) или с устройства, которое ещё открывает адрес роутера."]},
    {t:["Open the router in the browser, go to Services → HomenS.AI Auto VPN → Overview. If the card says the router is still on the reserve, press “Return to primary”. The router checks the primary first and shows the result there.","Откройте роутер в браузере: «Службы» → HomenS.AI Auto VPN → «Обзор». Если в карточке написано, что роутер всё ещё на резерве, нажмите «Вернуться на основной». Роутер сначала проверит основной и покажет результат там же."]},
    {t:["If that does not help, connect to the router by SSH (see “How to connect by SSH”) and show its state. This only reads:","Если не помогло, подключитесь к роутеру по SSH (см. «Как подключиться по SSH») и посмотрите состояние. Эта команда только читает:"],c:"homensai-vpn-emergency show"},
    {t:["Stop the program’s own services (this changes no network settings):","Остановите собственные службы программы (сетевые настройки не меняются):"],c:"homensai-vpn-emergency stop-auto"},
    {t:["Remove only the program’s own traffic block. It prints what it removes. VPN rules and the GL.iNet Kill Switch stay:","Снимите только собственную блокировку трафика программы. Команда сообщает, что удалила. Правила VPN и Kill Switch GL.iNet остаются:"],c:"homensai-vpn-emergency remove-guard"},
    {t:["Test the internet on a computer. Then open the GL.iNet panel → VPN → VPN Dashboard and check that your primary VPN rule is first and the tunnels are connected.","Проверьте интернет на компьютере. Затем откройте панель GL.iNet → VPN → VPN Dashboard и убедитесь, что основной VPN стоит первым и туннели подключены."]},
    {t:["Still nothing? Reboot the router from the GL.iNet panel (System → Reboot). The program’s traffic block is not kept after a reboot.","Всё равно нет? Перезагрузите роутер из панели GL.iNet («Система» → «Перезагрузка»). Блокировка трафика программы после перезагрузки не сохраняется."]},
    {t:["After the internet is back, start the monitor again:","Когда интернет вернулся, снова запустите мониторинг:"],c:"homensai-vpn-emergency start"}
   ]},
  {id:"ssh",
   title:["How to connect by SSH","Как подключиться по SSH"],
   when:["You need a command line on the router for the steps in this Help.","Командная строка на роутере нужна для шагов в этой справке."],
   steps:[
    {t:["Make sure SSH is on. In the GL.iNet admin panel (usually http://192.168.8.1) open System → Security and check that SSH access from the local network is enabled. In LuCI it is System → Administration → SSH Access, interface lan. Menu names can differ slightly between firmware versions.","Убедитесь, что SSH включён. В панели GL.iNet (обычно http://192.168.8.1) откройте «Система» → «Безопасность» и проверьте, что SSH из локальной сети включён. В LuCI это «System» → «Administration» → «SSH Access», интерфейс lan. Названия пунктов могут немного отличаться в разных версиях прошивки."]},
    {t:["Windows: press the Windows key, type PowerShell and press Enter. Linux or macOS: open Terminal.","Windows: нажмите клавишу Windows, введите PowerShell и нажмите Enter. Linux или macOS: откройте «Терминал»."]},
    {t:["Type the command and press Enter (192.168.8.1 is the default router address; if yours differs, use the “Default gateway” from ipconfig on Windows or ip route on Linux):","Введите команду и нажмите Enter (192.168.8.1 — адрес роутера по умолчанию; если у вас другой, возьмите «Основной шлюз» из ipconfig в Windows или ip route в Linux):"],c:"ssh root@192.168.8.1"},
    {t:["Windows says ssh is not recognised? Install “OpenSSH Client” (Settings → Apps → Optional features → Add a feature), or, if Git is installed, run it by its full path:","Windows пишет, что ssh не распознан? Установите «Клиент OpenSSH» («Параметры» → «Приложения» → «Дополнительные компоненты» → «Добавить»), либо, если установлен Git, запустите по полному пути:"],c:"& \"C:\\Program Files\\Git\\usr\\bin\\ssh.exe\" root@192.168.8.1"},
    {t:["First time only: the program shows the router key and asks “Are you sure you want to continue connecting?”. Type yes and press Enter.","Только в первый раз: программа покажет ключ роутера и спросит «Are you sure you want to continue connecting?». Введите yes и нажмите Enter."]},
    {t:["Enter the router root password (the same as for the GL.iNet panel). The characters are not shown while you type; this is normal. When you see root@GL-MT6000:~# you are on the router.","Введите пароль root роутера (тот же, что в панели GL.iNet). Символы при вводе не отображаются, это нормально. Когда появится root@GL-MT6000:~#, вы на роутере."]},
    {t:["To leave, type:","Чтобы выйти, введите:"],c:"exit"},
    {t:["Prefer a window program? In PuTTY set Host Name 192.168.8.1, Port 22, Connection type SSH, then log in as root.","Удобнее программа с окном? В PuTTY укажите Host Name 192.168.8.1, Port 22, Connection type SSH и войдите как root."]}
   ]},
  {id:"reserve",
   title:["The router stays on the reserve VPN","Роутер остаётся на резервном VPN"],
   when:["The Overview says Auto is stopped but the router is still on the reserve, or the reserve is failing.","На «Обзоре» написано, что Auto остановлен, но роутер всё ещё на резерве, или что резерв не работает."],
   steps:[
    {t:["Check the primary VPN: GL.iNet panel → VPN → VPN Dashboard. It must be connected. If not, connect it.","Проверьте основной VPN: панель GL.iNet → VPN → VPN Dashboard. Он должен быть подключён. Если нет, подключите."]},
    {t:["On the Overview press “Return to primary”. If the answer is “the primary does not pass its check”, wait a minute and press again. The router only returns to a primary that works.","На «Обзоре» нажмите «Вернуться на основной». Если ответ «основной не проходит проверку», подождите минуту и нажмите снова. Роутер возвращается только на основной, который работает."]},
    {t:["Auto may also return by itself when the primary has been healthy for a while (return policy “Return to the primary once it has been healthy for a while”, Settings → Recovery rules).","Auto может вернуться и сам, когда основной некоторое время исправен (политика «Вернуться на основной, когда он некоторое время исправен», «Настройки» → «Правила восстановления»)."]},
    {t:["If the button is missing or does nothing, use the steps of “I have no internet”.","Если кнопки нет или она ничего не делает, выполните шаги раздела «У меня пропал интернет»."]}
   ]},
  {id:"auto-refuses",
   title:["The Auto button refuses to start","Кнопка Auto не запускается"],
   when:["Pressing Start shows a message with a code.","После нажатия «Старт» появляется сообщение с кодом."],
   steps:[
    {t:["Open the Overview and read “Before you can start Auto”. The first step that is not green is what to do next; every router condition has a plain explanation.","Откройте «Обзор» и прочитайте «Что нужно перед запуском Auto». Первый не зелёный шаг и есть то, что делать дальше; у каждого условия роутера есть понятное объяснение."]},
    {t:["Hardware acceleration must be off: GL.iNet panel → Network → Network Acceleration, switch it off. Flow offloading in the firewall must be off as well.","Аппаратное ускорение должно быть выключено: панель GL.iNet → «Сеть» → «Сетевое ускорение», выключите. Flow offloading в firewall тоже должен быть выключен."]},
    {t:["IPv6 must be off: GL.iNet panel → Network → IPv6, switch it off.","IPv6 должен быть выключен: панель GL.iNet → «Сеть» → IPv6, выключите."]},
    {t:["The primary and the reserve must be two general (all-traffic) VPN rules with Kill Switch on and the direct-internet fallback off: GL.iNet panel → VPN → VPN Dashboard.","Основной и резервный должны быть двумя общими VPN-правилами (для всего трафика) с включённым Kill Switch и выключенным прямым выходом в интернет: панель GL.iNet → VPN → VPN Dashboard."]},
    {t:["The last step is always the LAN trial. Run the LAN helper (see “The LAN helper fails”).","Последний шаг всегда LAN-тест. Запустите LAN-помощник (см. «LAN-помощник не работает»)."]}
   ]},
  {id:"helper-what",
   title:["What is the LAN helper and how do I start it","Что такое LAN-помощник и как его запустить"],
   when:["Auto asks for a passed LAN trial and you do not know what that is.","Auto требует пройденный LAN-тест, а вы не знаете, что это."],
   steps:[
    {t:["The LAN helper is a small script for Windows, written in PowerShell 7 (a plain text file, client-test.ps1, about 325 lines; you can open it in Notepad and read it). It runs on your computer, not on the router, and checks from the computer’s side that the internet really works through the router before and after a switch. It does not install anything and changes no network settings of the computer.","LAN-помощник — небольшой скрипт для Windows на PowerShell 7 (обычный текстовый файл client-test.ps1, около 325 строк; его можно открыть в Блокноте и прочитать). Он запускается на вашем компьютере, а не на роутере, и со стороны компьютера проверяет, что интернет действительно работает через роутер до и после переключения. Он ничего не устанавливает и не меняет сетевых настроек компьютера."]},
    {t:["Install PowerShell 7 once (Windows 10/11):","Один раз установите PowerShell 7 (Windows 10/11):"],c:"winget install Microsoft.PowerShell"},
    {t:["On the Overview press “Download LAN helper” and “Download launcher”. Put both files in one folder. The launcher only asks questions (router address, cable adapter, mode) and starts the helper.","На «Обзоре» нажмите «Скачать LAN-помощник» и «Скачать запуск». Положите оба файла в одну папку. Запуск лишь задаёт вопросы (адрес роутера, кабельный адаптер, режим) и запускает помощник."]},
    {t:["Open PowerShell 7 in that folder (in Explorer type pwsh in the address bar) and start the launcher:","Откройте PowerShell 7 в этой папке (в Проводнике введите pwsh в адресной строке) и запустите:"],c:"pwsh -NoProfile -File .\\start-lan-helper.ps1"},
    {t:["Choose mode 1 (check only) first: it only reads and changes nothing. If it passes, run it again with mode 3 (full trial): it asks for the router password (typed privately, never saved) and the word TEST, switches to the reserve for a few minutes, checks the internet from your computer and then confirms the result to the router. Use a LAN cable if you can.","Сначала выберите режим 1 (только проверка): он только читает и ничего не меняет. Если прошёл, запустите снова в режиме 3 (полный тест): он спросит пароль роутера (вводится скрыто, нигде не сохраняется) и слово TEST, на несколько минут переключится на резерв, проверит интернет с вашего компьютера и подтвердит результат роутеру. По возможности используйте кабель LAN."]},
    {t:["If it stops with a code in capital letters, open Help → “The LAN helper fails”.","Если он остановился с кодом заглавными буквами, откройте «Помощь» → «LAN-помощник не работает»."]}
   ]},
  {id:"helper",
   title:["The LAN helper fails","LAN-помощник не работает"],
   when:["client-test.ps1 stops with a code before or during the trial.","client-test.ps1 останавливается с кодом до теста или во время него."],
   steps:[
    {t:["POWERSHELL-7-REQUIRED: install PowerShell 7 and start it with pwsh:","POWERSHELL-7-REQUIRED: установите PowerShell 7 и запускайте через pwsh:"],c:"winget install Microsoft.PowerShell"},
    {t:["Run a read-only check first (it changes nothing). Replace 3 by the number of your cable adapter (Get-NetAdapter shows it):","Сначала запустите проверку только для чтения (ничего не меняет). Замените 3 на номер вашего кабельного адаптера (его показывает Get-NetAdapter):"],c:"pwsh -NoProfile -File .\\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly"},
    {t:["CLIENT-CABLE-ADDRESS-AMBIGUOUS or the cable has no address: plug the cable into a LAN port of the router and wait until the adapter has one 192.168.8.x address.","CLIENT-CABLE-ADDRESS-AMBIGUOUS или у кабеля нет адреса: вставьте кабель в LAN-порт роутера и дождитесь, пока у адаптера появится один адрес 192.168.8.x."]},
    {t:["CLIENT-CABLE-HTTPS-FAILED or Windows error 10051 on the cable: allow default routes on that adapter (use your adapter number):","CLIENT-CABLE-HTTPS-FAILED или ошибка Windows 10051 на кабеле: разрешите маршруты по умолчанию на этом адаптере (подставьте номер адаптера):"],c:"Set-NetIPInterface -InterfaceIndex 3 -AddressFamily IPv4 -IgnoreDefaultRoutes Disabled"},
    {t:["DNS fails while a VPN program is running on the computer (for example NordVPN DNS protection): stop that program for the minutes of the test and start it again afterwards.","DNS не отвечает, пока на компьютере работает программа VPN (например, защита DNS в NordVPN): остановите её на время теста и потом запустите снова."]},
    {t:["CLIENT-PROBE-ROUTE-CONFLICT: a previous run left temporary routes. List them and remove the ones for 1.1.1.1 and 1.0.0.1 on the cable adapter:","CLIENT-PROBE-ROUTE-CONFLICT: прошлый запуск оставил временные маршруты. Посмотрите их и удалите маршруты для 1.1.1.1 и 1.0.0.1 на кабельном адаптере:"],c:"Get-NetRoute -DestinationPrefix 1.1.1.1/32,1.0.0.1/32"},
    {t:["The helper asks for the router password and for the word TEST. A short interruption of calls and downloads is possible during the switch.","Помощник спрашивает пароль роутера и слово TEST. Во время переключения возможен короткий разрыв звонков и загрузок."]}
   ]},
  {id:"stale",
   title:["The page is old, empty or says the monitor is not running","Страница старая, пустая или пишет, что мониторинг не работает"],
   when:["After an update, the Overview looks old, shows errors, or the status is stale.","После обновления «Обзор» выглядит по-старому, показывает ошибки или статус устарел."],
   steps:[
    {t:["Press Ctrl+F5 to reload without cache, then sign out of LuCI and sign in again (new permissions after an update).","Нажмите Ctrl+F5 (обновление без кэша), затем выйдите из LuCI и войдите снова (после обновления права обновляются)."]},
    {t:["Settings → Monitor service → Start monitor. Or from SSH:","«Настройки» → «Служба мониторинга» → «Запустить мониторинг». Или через SSH:"],c:"homensai-vpn-emergency start"},
    {t:["If the page still says the status is unavailable, reload the router’s RPC service and sign in again:","Если страница всё ещё пишет, что статус недоступен, перезапустите RPC-службу роутера и войдите снова:"],c:"/etc/init.d/rpcd reload"},
    {t:["Check that exactly one monitor is running:","Проверьте, что запущен ровно один монитор:"],c:"ps w | grep homensai-vpn"}
   ]},
  {id:"outside-change",
   title:["I changed VPN rules in the GL.iNet panel and Auto stopped","Я изменил правила VPN в панели GL.iNet, и Auto остановился"],
   when:["The Overview says the VPN rules were changed by someone else.","На «Обзоре» написано, что правила VPN изменил кто-то другой."],
   steps:[
    {t:["This is intended: Auto never fights your changes. It stopped and removed its own traffic block; your internet is not held.","Так задумано: Auto не спорит с вашими изменениями. Он остановился и снял свою блокировку трафика; интернет не удерживается."]},
    {t:["Check GL.iNet panel → VPN → VPN Dashboard: the primary should be first, the reserve second, all with Kill Switch.","Проверьте панель GL.iNet → VPN → VPN Dashboard: основной должен быть первым, резервный вторым, у всех включён Kill Switch."]},
    {t:["To use Auto again, run a new LAN trial (the earlier test belongs to the old rules).","Чтобы снова использовать Auto, пройдите новый LAN-тест (прежний тест относится к старым правилам)."]}
   ]},
  {id:"telegram",
   title:["Telegram reports do not arrive","Отчёты в Telegram не приходят"],
   when:["The Overview shows a Telegram error, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.","На «Обзоре» ошибка Telegram, тестовое сообщение не приходит или вы настраиваете Telegram впервые. Нужны три вещи: бот, его токен и ID чата."],
   steps:[
    {t:["Create the bot. In Telegram open https://t.me/BotFather (or search for @BotFather; the real one has a blue check mark). Send: /newbot","Создайте бота. В Telegram откройте https://t.me/BotFather (или найдите @BotFather; у настоящего есть синяя галочка). Отправьте: /newbot"],c:"/newbot"},
    {t:["BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).","BotFather спросит имя (показывается в чате, любой текст, например «Мой VPN роутер») и затем username, который должен заканчиваться на «bot» (например my_router_vpn_bot)."]},
    {t:["BotFather answers with “Use this token to access the HTTP API:” and a line like 123456789:AAH-secret-part-of-the-token. This line is the bot token (digits, a colon, then 30–100 letters, digits, - or _). Copy it. It is a secret: do not post it anywhere.","BotFather ответит «Use this token to access the HTTP API:» и строкой вида 123456789:AAH-secret-part-of-the-token. Эта строка и есть токен бота: цифры, двоеточие, затем 30–100 букв, цифр, - или _. Скопируйте её. Это секрет: не публикуйте его."]},
    {t:["Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.","Откройте нового бота (ссылка в конце сообщения BotFather, https://t.me/<username_вашего_бота>) и нажмите Start или отправьте /start. Бот не может написать вам первым."]},
    {t:["Find your Chat ID. For reports to yourself: open https://t.me/userinfobot (@userinfobot), press Start and copy the number after “Id:”, e.g. 123456789. For a group: add your bot to the group, add @userinfobot or @getidsbot as well, and take the number that starts with a minus, e.g. -1001234567890. For a public channel: add your bot as an administrator and use the channel name with @, e.g. @my_channel.","Узнайте ID чата. Для отчётов себе: откройте https://t.me/userinfobot (@userinfobot), нажмите Start и скопируйте число после «Id:», например 123456789. Для группы: добавьте бота в группу, добавьте также @userinfobot или @getidsbot и возьмите число с минусом, например -1001234567890. Для публичного канала: добавьте бота администратором и укажите имя канала с @, например @my_channel."]},
    {t:["On the router page: Settings → Setup → 2 · Telegram. Paste the token into “Bot token” and the number or @name into “Chat ID”, choose how often to send, review and save. After saving the token is never shown again; to change it, enter it again; to remove it, use the delete button.","На странице роутера: «Настройки» → «Настройка» → 2 · Telegram. Вставьте токен в «Токен бота», число или @имя в «ID чата», выберите частоту отправки, проверьте обзор и сохраните. После сохранения токен больше не показывается; чтобы изменить — введите заново; чтобы убрать — кнопка удаления."]},
    {t:["Press “Test Telegram delivery”. A message should arrive within a few seconds. If a code is shown instead: TELEGRAM-… with “401” or “Unauthorized” means a wrong token; “400”, “chat not found” or “Forbidden” means a wrong Chat ID or you never pressed Start; a timeout means the router has no internet or a wrong clock.","Нажмите «Проверить доставку Telegram». Сообщение должно прийти за несколько секунд. Если показан код TELEGRAM-…: «401» или «Unauthorized» — неверный токен; «400», «chat not found» или «Forbidden» — неверный ID чата или вы не нажали Start; тайм-аут — у роутера нет интернета или неверные часы."]},
    {t:["Still nothing? Create the token again in BotFather (/token or /revoke) and enter the new one. Never send the token to anyone, including in a support chat.","Всё равно нет? Создайте токен заново в BotFather (/token или /revoke) и введите новый. Никому не отправляйте токен, в том числе в чат поддержки."]}
   ]},
  {id:"clock",
   title:["Dates are wrong, history or statistics are blocked","Неверные даты, история или статистика заблокированы"],
   when:["Codes like CLOCK-001 or HISTORY-001, or events with impossible dates.","Коды вроде CLOCK-001 или HISTORY-001, либо события с невозможными датами."],
   steps:[
    {t:["The router clock must be correct. GL.iNet panel → System → Time: enable time synchronisation (NTP) and pick your time zone.","Часы роутера должны быть верными. Панель GL.iNet → «Система» → «Время»: включите синхронизацию времени (NTP) и выберите часовой пояс."]},
    {t:["Check the clock over SSH:","Проверьте часы по SSH:"],c:"date"},
    {t:["After the clock is right, statistics continue by themselves. Gaps are shown as unobserved time and are never filled with invented numbers.","После исправления часов статистика продолжится сама. Пропуски показываются как ненаблюдаемое время и никогда не заполняются выдуманными числами."]}
   ]},
  {id:"backup",
   title:["Make a backup before changes","Резервная копия перед изменениями"],
   when:["Before an update, a LAN trial or any manual repair.","Перед обновлением, LAN-тестом или любым ручным исправлением."],
   steps:[
    {t:["On Windows run this in PowerShell (cmd /c keeps the file binary). The file contains secrets, so keep it private and never upload it:","В Windows выполните в PowerShell (cmd /c сохраняет файл без искажений). В файле есть секреты: храните его приватно и никуда не загружайте:"],c:"cmd /c \"ssh root@192.168.8.1 \"\"tar czf - /etc/config /etc/homensai-vpn\"\" > router-backup.tgz\""},
    {t:["On Linux or macOS:","В Linux или macOS:"],c:"ssh root@192.168.8.1 'tar czf - /etc/config /etc/homensai-vpn' > router-backup.tgz"}
   ]},
  {id:"remove",
   title:["Remove or roll back the program","Удалить программу или откатить версию"],
   when:["You want the router without this program, or you need an older version.","Нужен роутер без этой программы или более старая версия."],
   steps:[
    {t:["Stop Auto first and make sure the router is back on the primary (Overview). Then, by SSH:","Сначала остановите Auto и убедитесь, что роутер вернулся на основной («Обзор»). Затем по SSH:"],c:"opkg remove homensai-auto-vpn"},
    {t:["Your settings and history stay in `/etc/config/homensai_vpn` and `/etc/homensai-vpn`. Installing again keeps them.","Ваши настройки и история остаются в `/etc/config/homensai_vpn` и `/etc/homensai-vpn`. При повторной установке они сохраняются."]},
    {t:["If the removal is refused, the program tells why (for example a transaction is active). Do not force it: first use “I have no internet”.","Если удаление отклонено, программа объяснит причину (например, активна транзакция). Не форсируйте: сначала выполните раздел «У меня пропал интернет»."]}
   ]},
  {id:"report",
   title:["What to send when asking for help","Что отправить, когда просите о помощи"],
   when:["You report a problem and want it solved quickly.","Вы сообщаете о проблеме и хотите решить её быстро."],
   steps:[
    {t:["These commands print no passwords or keys. Send their output and the time of the problem:","Эти команды не печатают паролей и ключей. Отправьте их вывод и время проблемы:"],c:"homensai-vpn-emergency show"},
    {t:["Installed version:","Установленная версия:"],c:"opkg status homensai-auto-vpn | grep Version"},
    {t:["Latest system log lines about the program:","Последние строки системного журнала о программе:"],c:"logread | grep -i homensai | tail -30"},
    {t:["Never send the router password, the Telegram token, VPN files or backups.","Никогда не отправляйте пароль роутера, токен Telegram, файлы VPN и резервные копии."]}
   ]}
];

// Text with `inline code` pieces: the same dark monospace style everywhere.
function richText(text){return String(text).split('`').map(function(part,i){return i%2?E('code',{'class':'hv-code'},part):part;});}
function helpCommand(command){
  var button=E('button',{'type':'button','class':'cbi-button','click':function(){
    try{navigator.clipboard.writeText(command).then(function(){button.textContent=bi('Copied','Скопировано');}).catch(function(){});}catch(error){}
  }},bi('Copy','Копировать'));
  return E('div',{'class':'hv-cmd-row'},[E('pre',{'class':'hv-cmd'},command),button]);
}
function renderHelp(){
  var topics=HELP_TOPICS.map(function(topic){
    var steps=topic.custom?topic.custom():E('ol',{'class':'hv-help-steps'},topic.steps.map(function(step){
      return E('li',{},[E('p',{},richText(bi(step.t[0],step.t[1]))),step.c?helpCommand(step.c):null].filter(Boolean));
    }));
    var attributes={'class':'hv-help-topic','id':'help-'+topic.id};
    if(topic.open)attributes.open='open';
    return E('details',attributes,[E('summary',{},bi(topic.title[0],topic.title[1])),E('p',{'class':'hv-help-when'},bi(topic.when[0],topic.when[1])),steps]);
  });
  return E('section',{'class':'hv-chart-card hv-help'},[
    E('h2',{},bi('Help and recovery','Помощь и восстановление')),
    E('p',{},bi('Pick the situation that matches. Commands are typed on the router over SSH (see “How to connect by SSH”); the Copy button copies a command so you can paste it.','Выберите подходящую ситуацию. Команды вводятся на роутере по SSH (см. «Как подключиться по SSH»); кнопка «Копировать» копирует команду, чтобы вставить её в терминал.'))
  ].concat(topics));
}

var helpNode=null;
// The terms can be re-read at any time (same points as the first-run screen).
if(typeof TERMS_POINTS!=='undefined'){HELP_TOPICS.push({id:'terms',title:["Terms of use (experimental software)","Условия использования (экспериментальное ПО)"],when:["What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.","Что вы приняли на первом экране. Полный текст — DISCLAIMER.ru.md в репозитории проекта."],steps:TERMS_POINTS.map(function(point){return {t:[point.h[0]+'. '+point.t[0],point.h[1]+'. '+point.t[1]]};})});}
