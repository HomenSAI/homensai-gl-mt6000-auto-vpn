<!-- doc-role: current-generated-codes -->
# События, состояния и диагностика / Events, states and diagnostics

Generated from the merged active error catalogue, including prefix families. / Сформировано из объединённого справочника приложения, включая семейства кодов.

A listed code may describe a legacy mode or a guarded refusal; it does not prove that a route changed. Global service errors are not falsely assigned to a VPN role. / Наличие кода не доказывает выполненный переход. Общие ошибки службы не приписываются каналу.

[Current scope](CURRENT-STATUS.md) · [History/provenance](CHANNEL-ATTRIBUTION.md)

## CLIENT-CONTROL-PATH-MISMATCH

Управление идёт через другой интерфейс / Management route uses another interface

**RU:** Путь управления ОС отличается от выбранного интерфейса проверки, например при одинаковой подсети двух роутеров.

**EN:** The OS management route differs from the selected client witness, for example when two routers share the same private subnet.

**Что делать:** Помощник отказывает до отправки пароля/сессии. Подтвердите идентичность и однозначный путь управления; не меняйте сеть компьютера автоматически.

**Action:** The helper refuses before credentials/session are sent. Establish the target identity and an unambiguous management path; do not change host networking automatically.

## WAN-001

Нет интернета на роутере / Internet is down at the router

**RU:** Сам роутер не достаёт до интернета, а не только VPN.

**EN:** The router itself cannot reach the internet, not only the VPN.

**Что делать:** Сначала различите WAN, DNS и VPN по независимым данным. Перезапуск модема — отдельное осознанное действие, а не автоматическое исправление приложения.

**Action:** Inspect independent WAN, DNS and VPN evidence before blaming the provider. A modem restart is a separate deliberate action, not an automatic application fix.

## DNS-001

DNS-проверка не прошла / DNS check did not pass

**RU:** Контрольный DNS-запрос через этот VPN не дал подтверждённого ответа. Другой DNS, кэшированные имена или прямые HTTPS-запросы могут работать; сам код не устанавливает причину.

**EN:** The control DNS query through this VPN did not produce a validated answer. Other DNS paths, cached names or direct HTTPS may still work; the code alone does not identify the cause.

**Что делать:** Повторите проверку и изучите сохранённые результаты DNS/HTTPS, доступность DNS-сервера, маршрутизацию и фильтрацию. Перезапуск профиля согласуйте со штатным Stop/восстановлением Auto.

**Action:** Repeat the check and inspect the saved DNS/HTTPS results, resolver reachability, routing and filtering. Coordinate any profile restart with managed Auto Stop/recovery.

## VPN-001

VPN не подключился / VPN did not connect

**RU:** Не удалось установить соединение VPN. Причина может остаться неизвестной.

**EN:** The VPN connection could not be established. The cause may stay unknown.

**Что делать:** Изучите точный отказ туннеля/доступа/сервера. До правки или переподключения штатного профиля завершите управляемый Stop/восстановление; не перезапускайте рабочий клиент ради статуса.

**Action:** Inspect the exact tunnel/credential/endpoint failure. Before editing or reconnecting stock profiles, complete managed Stop/recovery; do not restart a working client just to change its status.

## VPN-002

VPN отклонил вход / VPN login rejected

**RU:** VPN-сервер отклонил логин или ключ.

**EN:** The VPN server rejected the login or the key.

**Что делать:** Откройте профиль в GL.iNet и заново введите логин и пароль или импортируйте конфиг. Проверьте, что подписка активна.

**Action:** Open the profile in GL.iNet and re-enter the login and password or import the config again. Check that the subscription is active.

## VPN-003

Недостаточно успешных HTTPS-проверок / HTTPS availability below threshold

**RU:** Через подключённый VPN успешно прошли менее двух из трёх HTTPS-проверок. Часть трафика может проходить. Сам код не доказывает полное отсутствие доступа в Интернет.

**EN:** Fewer than two of three HTTPS checks succeeded through the connected VPN. Some traffic may still pass. This code alone does not establish complete loss of Internet access.

**Что делать:** Посмотрите сохранённое число успешных HTTPS-проверок, результат DNS и сведения об адресах проверки. Повторите проверку; перед переподключением работающего VPN выясните причину повторяющихся сбоев.

**Action:** Read the saved HTTPS success count, DNS result and endpoint details. Retry the check; investigate repeated failures before reconnecting a working VPN.

## VPN-004

Имя VPN-сервера не находится / VPN server name does not resolve

**RU:** Имя VPN-сервера не удаётся превратить в адрес.

**EN:** The name of the VPN server cannot be resolved to an address.

**Что делать:** Проверьте DNS на роутере и имя сервера в профиле. Если провайдер даёт IP-адрес сервера, используйте его.

**Action:** Check DNS on the router and the server name in the profile. Use the server IP address if the provider gives one.

## TLS-001

Ошибка проверки сертификата / Certificate check failed

**RU:** Сертификат HTTPS не принят. Программа никогда не отключает проверку сама.

**EN:** The HTTPS certificate was not accepted. The program never turns the check off by itself.

**Что делать:** Проверьте дату и время на роутере (неверные часы ломают сертификаты) и что установлен пакет ca-bundle.

**Action:** Check the router date and time (a wrong clock breaks certificates) and that the package ca-bundle is installed.

## ROUTE-001

Трафик идёт другим путём / Traffic goes another way

**RU:** Реальный маршрут отличается от выбранного.

**EN:** The real route differs from the selected one.

**Что делать:** Откройте GL.iNet → VPN Dashboard и проверьте порядок правил VPN. Не меняйте правила, пока работает Auto.

**Action:** Open GL.iNet → VPN Dashboard and check the order of the VPN rules. Do not change rules while Auto is working.

## CHECK-001

Проверка не подтверждена / Check not confirmed

**RU:** Пока недостаточно данных; состояние остаётся «неизвестно». Показывается, пока VPN ещё проверяется.

**EN:** There is not enough evidence yet; the state stays “unknown”. It is shown while a VPN is still being checked.

**Что делать:** Подождите один-два интервала проверки. Если не проходит, нажмите «Проверить VPN сейчас» на «Обзоре».

**Action:** Wait one or two check intervals. If it stays, press “Check the VPNs now” on the Overview.

## SWITCH-001

Нет готового резерва / No ready reserve

**RU:** Нет резервного VPN, прошедшего проверки, поэтому переключаться некуда.

**EN:** There is no reserve VPN that passed its checks, so there is nowhere to switch.

**Что делать:** Подключите ещё один VPN-профиль в GL.iNet и выберите его резервным в «Настройки → Все настройки приложения → 3 · Существующие VPN».

**Action:** Connect another VPN profile in GL.iNet and select it as the reserve in Settings → All application settings → 3 · Existing VPNs.

## AUTO-CONTROL-UNVERIFIED

Запрос Auto не подтверждён / Auto request not confirmed

**RU:** Роутер ответил, но не ясным «принято». Ничего не предполагается.

**EN:** The router answered, but not with a clear “accepted”. Nothing is assumed.

**Что делать:** Посмотрите на лампу и «Техническое состояние» в блоке Auto; повторите нажатие, только если за минуту ничего не изменилось.

**Action:** Look at the lamp and the Technical state in the Auto card; repeat the press only if nothing changed after a minute.

## AUTO-CONTROL-FAILED

Запрос Auto остался без ответа / Auto request got no answer

**RU:** Роутер вообще не ответил на запрос «Включить» или «Выключить».

**EN:** The router did not answer the Start or Stop request at all.

**Что делать:** Обновите страницу и проверьте лампу мониторинга. Если роутер недоступен, используйте аварийный возврат из «Помощи».

**Action:** Reload the page and check the monitor lamp. If the router is unreachable, use the emergency return in Help.

## AUTO-START-REFUSED

Запуск Auto отклонён / Auto start refused

**RU:** Роутер отказался запускать Auto; причины перечислены с кодами.

**EN:** The router refused to start Auto; the reasons are listed with their codes.

**Что делать:** Прочитайте текущие причины своего режима. Подготовленный непрерывный режим использует собственные данные роутера; соответствующий LAN-сертификат нужен клиентскому тесту. Повторные нажатия не исправляют условия.

**Action:** Read the current mode-specific blockers. Prepared continuous mode uses its own router evidence; only a client-confirmed trial requires its matching LAN certificate. Repeated clicks do not repair prerequisites.

## ROLLBACK-GIVEN-UP

Автоматический возврат остановлен / Automatic return stopped

**RU:** Возврат на основной не удался дважды. Программа перестала пытаться, пропускает только трафик через VPN и выключила Auto.

**EN:** The return to the primary failed twice. The program stopped trying, keeps only VPN traffic allowed and turned Auto off.

**Что делать:** Проверьте порядок VPN-правил на роутере («Помощь» → аварийный возврат), восстановите его вручную и закройте журнал аварийной командой.

**Action:** Check the VPN rule order in the router (Help → emergency return), restore it by hand, then close the journal with the emergency command.

## EXIT-TRACE-FAILED

Не удалось прочитать внешний адрес / Exit address could not be read

**RU:** Проверка адреса, который видит интернет через VPN, не получила ясного ответа (оборван, искажён или не IPv4). По такому ответу ничего не переключается.

**EN:** The check of the address the internet sees through the VPN got no clear answer (cut, garbled or not IPv4). Nothing is switched on such an answer.

**Что делать:** Обычно временно. Если повторяется, проверьте VPN-сервер и что через него работает IPv4.

**Action:** Usually temporary. If it repeats, check the VPN server and that IPv4 works through it.

## STOP-UNCONFIRMED

Остановка не подтверждена / Stop not confirmed

**RU:** Запрос остановки не удалось сохранить на роутере. Запущенный тест сбоя всё равно убран.

**EN:** The Stop request could not be saved on the router. A running failure test was still cleaned up.

**Что делать:** Нажмите «Стоп» ещё раз. Если повторяется, используйте аварийный возврат из «Помощи» или остановите службу в «Система» → «Автозапуск».

**Action:** Press Stop again. If it repeats, use the emergency return in Help, or stop the service in System → Startup.

## SWITCH-002

Интернет не вернулся после переключения / Internet not restored after the switch

**RU:** Переключение выполнено, но последующие проверки не прошли.

**EN:** The switch was applied but the following checks failed.

**Что делать:** Проверьте итог восстановления и оба пути. Запрошенный откат не является подтверждённым возвратом; не начинайте другой тест до выяснения текущего состояния.

**Action:** Inspect the recovery result and both paths. A requested rollback is not confirmed restoration; do not start another test until the current state is understood.

## SWITCH-003

Переключение не удалось применить / Switch could not be applied

**RU:** Сама смена маршрута не удалась (это не то же самое, что SWITCH-002).

**EN:** The route change itself failed (not the same as SWITCH-002).

**Что делать:** Откройте «Помощь» → «Роутер остаётся на резервном VPN» и проверьте порядок правил VPN в GL.iNet.

**Action:** Open Help → “The router stays on the reserve VPN” and check the VPN rule order in GL.iNet.

## CONFIG-001

Автоматика на паузе после ручного изменения / Automation paused after manual change

**RU:** Кто-то изменил настройки VPN вручную, поэтому автоматика отошла в сторону.

**EN:** Someone changed the VPN settings by hand, so automation stepped aside.

**Что делать:** Изучите внешнюю правку и фактическую очистку. Перепроверьте идентичность/политику своего режима; не навязывайте LAN-тест подготовленному router-probed режиму и не конкурируйте с правкой оператора.

**Action:** Inspect the external edit and actual cleanup result. Revalidate identities/policy for the selected mode; do not impose a LAN trial on prepared router-probed mode or compete with the operator edit.

## SYSTEM-001

Неподдерживаемая прошивка или нет программы / Unsupported firmware or missing tool

**RU:** Версия прошивки или нужная программа не поддерживается.

**EN:** The firmware version or a required tool is not supported.

**Что делать:** Сравните с проверенной прошивкой (GL.iNet 4.11.0) на странице «Готовность системы». Мониторинг работает, а для Auto нужна поддерживаемая прошивка.

**Action:** Compare with the tested firmware (GL.iNet 4.11.0) on the Readiness page. Monitoring still works; Auto needs the supported firmware.

## MONITOR-START-REQUESTED

Запуск запрошен / Start requested

**RU:** Мониторинг включён. Это ещё не доказательство, что он работает.

**EN:** The monitor was switched on. This is not yet proof that it runs.

**Что делать:** Подождите до минуты свежих данных; светофор станет зелёным.

**Action:** Wait up to a minute for fresh data; the traffic light turns green.

## MONITOR-STOP-REQUESTED

Остановка запрошена / Stop requested

**RU:** Мониторингу отправлена команда остановиться.

**EN:** The monitor was asked to stop.

**Что делать:** Делать ничего не нужно. Это не значит, что интернет восстановился.

**Action:** Nothing to do. It does not mean the internet recovered.

## MONITOR-STOP-AUTO-FIRST

Сначала остановите Auto / Stop Auto first

**RU:** Auto или удерживаемый резерв мешают остановить мониторинг.

**EN:** Auto or a retained reserve prevents stopping the monitor.

**Что делать:** Нажмите «Стоп» у Auto, дождитесь возврата на основной, затем остановите мониторинг.

**Action:** Press Stop on Auto, wait until it returns to the primary, then stop the monitor.

## MONITOR-JOURNAL-UNVERIFIED

Журнал не читается / Journal cannot be read

**RU:** Журнал транзакций повреждён или не читается.

**EN:** The transaction journal is damaged or unreadable.

**Что делать:** Не удаляйте его. Следуйте «Помощи» → «У меня пропал интернет» и router-test-kit/EMERGENCY.md.

**Action:** Do not delete it. Follow Help → “I have no internet” and router-test-kit/EMERGENCY.md.

## MONITOR-SAVE-FAILED

Настройка не сохранилась / Setting not saved

**RU:** Роутер не подтвердил сохранение настройки.

**EN:** The router did not confirm the saved setting.

**Что делать:** Повторите. Если снова, проверьте свободное место (df -h /etc) и системный журнал (logread).

**Action:** Try again. If it repeats, check free space (df -h /etc) and the system log (logread).

## MONITOR-SERVICE-UNCONFIRMED

Смена состояния службы не подтверждена / Service change not confirmed

**RU:** Настройка могла сохраниться, но служба не подтвердила запуск или остановку.

**EN:** The setting may be saved but the service did not confirm the start or stop.

**Что делать:** Через минуту посмотрите блок «Мониторинг» на «Обзоре»; если лампа не зелёная, нажмите там «Запустить мониторинг».

**Action:** After a minute check the Monitoring block on the Overview; if its lamp is not green, press “Start monitoring” there.

## MONITOR-INVALID

Неверный запрос / Invalid request

**RU:** В запросе неверные поля. Ничего не записано.

**EN:** The request had wrong fields. Nothing was written.

**Что делать:** Обновите страницу (Ctrl+F5). Если повторяется, версии страницы и программы различаются: см. сообщение на «Обзоре».

**Action:** Reload the page (Ctrl+F5). If it repeats, the page and the program versions differ: see the notice on the Overview.

## MONITOR-RPC-UNCONFIRMED

Нет подтверждённого ответа / No confirmed answer

**RU:** Браузер не получил подтверждённого ответа от роутера.

**EN:** The browser did not get a confirmed answer from the router.

**Что делать:** Обновите статус. Не считайте, что мониторинг остановился.

**Action:** Reload the status. Do not assume the monitor stopped.

## RPC-UNAVAILABLE

Роутер не отвечает / Router does not answer

**RU:** Страница не получает статус от роутера; показаны старые значения.

**EN:** The page cannot get the status from the router; old values are shown.

**Что делать:** Обновите страницу и войдите в LuCI снова. Затем «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».

**Action:** Reload the page and sign in to LuCI again. Then Help → “The page is old, empty or says the monitor is not running”.

## STATUS-STALE

Статус устарел / Status is old

**RU:** Мониторинг включён, но его данные старше 90 секунд.

**EN:** The monitor is switched on but its data is older than 90 seconds.

**Что делать:** Подождите минуту и обновите страницу; если лампа красная, нажмите «Запустить мониторинг» в блоке «Мониторинг». Если не помогло, см. «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».

**Action:** Wait a minute and reload the page; if the lamp is red press “Start monitoring” in the Monitoring block. If it stays, see Help → “The page is old, empty or says the monitor is not running”.

## RPC-PLUGIN

Нет модуля программы / Program plugin missing

**RU:** На роутере нет модуля, который связывает страницу с программой.

**EN:** The plugin that connects the page to the program is missing on the router.

**Что делать:** Переустановите пакет (opkg install) и выйдите из LuCI и войдите снова.

**Action:** Reinstall the package (opkg install) and sign out of LuCI and in again.

## RPC-INPUT-SIZE

Слишком большой запрос / Request too large

**RU:** Запрос отклонён: он слишком большой или сложный.

**EN:** The request was rejected because it was too large or too complex.

**Что делать:** Обновите страницу и повторите. С обычной страницей этого не бывает.

**Action:** Reload the page and repeat. This normally does not happen with the standard page.

## CLIENT-CABLE-LINK-DOWN

Кабельный адаптер не подключён / Cable adapter is down

**RU:** Выбранный кабельный адаптер не поднят.

**EN:** The cable adapter you chose is not up.

**Что делать:** Вставьте кабель в LAN-порт роутера и запустите помощника снова с правильным номером адаптера (Get-NetAdapter).

**Action:** Plug the cable into a LAN port of the router and run the helper again with the right adapter number (Get-NetAdapter).

## CLIENT-CABLE-ADDRESS-AMBIGUOUS

Неоднозначный IPv4-адрес кабеля / Cable IPv4 address is ambiguous

**RU:** На выбранном кабеле нет единственного предпочтительного IPv4-адреса.

**EN:** The selected cable has no single preferred IPv4 address.

**Что делать:** Проверьте реальную LAN-подсеть и адреса адаптера только чтением; заводской пример 192.168.8.x не универсален.

**Action:** Inspect the real LAN subnet and adapter addresses read-only; the factory 192.168.8.x example is not universal.

## CLIENT-CABLE-NOT-LOCAL

Выбранный кабель не ведёт к роутеру локально / Selected cable does not reach this router locally

**RU:** Явно выбранный кабельный маршрут к адресу управления не является прямым локальным путём.

**EN:** The explicit cable route to the management address is not a direct local path.

**Что делать:** Проверьте нужный роутер, кабель и подсеть. Не отключайте Wi-Fi и не меняйте маршруты компьютера автоматически.

**Action:** Verify the correct router, cable and subnet. Do not automatically disable Wi-Fi or alter computer routes.

## CLIENT-CABLE-PROBE-ROUTE-MISMATCH

Маршрут кабельной проверки не совпадает / Cable probe route differs

**RU:** Выбранный интерфейс не направляет проверочные запросы через ожидаемый роутер.

**EN:** The chosen interface cannot route the probe destinations through the expected router.

**Что делать:** Изучите интерфейс и владельца шлюза. Текущий помощник не создаёт временных маршрутов; не удаляйте посторонние маршруты ради обхода отказа.

**Action:** Inspect interface/gateway ownership. The current helper creates no temporary routes; do not delete unrelated routes to bypass this refusal.

## CLIENT-CABLE-HTTPS-FAILED

Привязанная HTTPS-проверка не прошла / Bound HTTPS check failed

**RU:** HTTPS-запросы с привязкой к выбранному кабелю не завершились успешно.

**EN:** The source-bound HTTPS requests through the selected cable did not succeed.

**Что делать:** Проверьте роутер, фактический маршрут и программы клиента. Исправление сети компьютера — отдельное осознанное действие, а не автоматический ремонт помощником.

**Action:** Inspect router health, actual route and competing client software. Any host-network correction is a separate deliberate action, not an automatic helper repair.

## CLIENT-GATEWAY-MISMATCH

Клиентский путь использует другой шлюз / Client path uses another gateway

**RU:** Наблюдаемый обычный путь клиента не проходит через указанный роутер.

**EN:** The observed default client path is not through the named router.

**Что делать:** Проверьте нужную сеть и интерфейс либо выберите явную кабельную проверку. Не останавливайте другой VPN и не меняйте его маршруты незаметно.

**Action:** Verify the intended network and interface, or choose an explicit cable witness. Do not silently stop another VPN or change its routes.

## CLIENT-DNS-CONFIG-UNVERIFIED

Настройки DNS не подтверждены / DNS settings unverified

**RU:** Компьютер использует DNS-сервер, отличный от роутера.

**EN:** The computer uses a DNS server other than the router.

**Что делать:** Установите DNS на компьютере автоматически (от роутера) на время теста.

**Action:** Set the DNS of the computer to automatic (from the router) for the test.

## CLIENT-IPV6-DEFAULT-UNVERIFIED

Маршрут IPv6 не подтверждён / IPv6 route unverified

**RU:** У компьютера есть маршрут IPv6 по умолчанию, который помощник не может проверить.

**EN:** The computer has an IPv6 default route that the helper cannot verify.

**Что делать:** Эта проверка не исключила другой IPv6-путь. Сохраните текущие настройки и выберите поддерживаемую явную IPv4-проверку либо отдельно разрешённую коррекцию; помощник не отключает IPv6.

**Action:** This witness has not excluded another IPv6 path. Preserve its current settings and choose a supported explicit IPv4 witness or a separately authorized correction; the helper does not disable IPv6.

## CLIENT-PROBE-ROUTE-CONFLICT

Конфликт проверочных маршрутов старой версии / Legacy probe-route conflict

**RU:** Код относится к старому помощнику, добавлявшему маршруты; текущий маршруты не создаёт.

**EN:** This code belongs to an older route-adding helper; the current helper is route-free.

**Что делать:** Изучите владельцев маршрутов и сохраните данные. Удаляйте старый собственный маршрут лишь после отдельной проверки; не удаляйте произвольные маршруты.

**Action:** Read the current route owners and preserve evidence. Remove an old owned route only as a separately verified cleanup; never delete arbitrary routes.

## CLIENT-CANCELLED

Отменено / Cancelled

**RU:** Вы не ввели TEST, поэтому тест не начался.

**EN:** You did not type TEST, so the trial did not start.

**Что делать:** Запустите снова и вводите TEST, только когда готовы к короткому разрыву.

**Action:** Run again and type TEST only when you are ready for a short interruption.

## CLIENT-TRIAL-UNCONFIRMED

Тест не подтверждён / Trial not confirmed

**RU:** Роутер не получил вовремя верное подтверждение от компьютера.

**EN:** The router did not get a valid confirmation from the computer in time.

**Что делать:** Роутер вернулся на прежний маршрут. Проверьте кабель и запустите снова.

**Action:** The router returned to the previous route. Check the cable and run again.

## CLIENT-RESERVE-NOT-VERIFIED

Резерв не подтверждён / Reserve not verified

**RU:** Компьютер не увидел выход через резервный VPN.

**EN:** The computer did not see the reserve VPN exit.

**Что делать:** Проверьте, что резервный VPN действительно работает («Обзор»), и повторите.

**Action:** Check that the reserve VPN really works (Overview) and try again.

## POWERSHELL-7-REQUIRED

Нужен PowerShell 7 / PowerShell 7 needed

**RU:** Помощнику нужен PowerShell 7 (pwsh).

**EN:** The helper needs PowerShell 7 (pwsh).

**Что делать:** Установите: winget install Microsoft.PowerShell, затем запускайте помощника через pwsh.

**Action:** Install it: winget install Microsoft.PowerShell, then start the helper with pwsh.

## PRIVATE-LAN-ROUTER-REQUIRED

Адрес роутера не частный / Router address is not private

**RU:** Помощник принимает только частный адрес локальной сети.

**EN:** The helper accepts only a private LAN address.

**Что делать:** Укажите адрес роутера вида http://192.168.8.1:8080/.

**Action:** Use the router address such as http://192.168.8.1:8080/.

## TELEGRAM-TOKEN-REQUIRED

Нет токена бота / Bot token missing

**RU:** Токен бота не сохранён.

**EN:** No bot token is stored.

**Что делать:** Введите токен в «Настройки» → «2 · Telegram» (см. «Помощь» → «Отчёты в Telegram не приходят»).

**Action:** Enter the token in Settings → 2 · Telegram (see Help → “Telegram reports do not arrive”).

## TELEGRAM-TOKEN-FORMAT

Токен выглядит неверно / Token looks wrong

**RU:** Токен не похож на 123456789:AAH….

**EN:** The token does not have the form 123456789:AAH… .

**Что делать:** Скопируйте токен из @BotFather заново целиком, без пробелов.

**Action:** Copy the whole token from @BotFather again, without spaces.

## TELEGRAM-TOKEN-REJECTED

Telegram отклонил токен / Token rejected by Telegram

**RU:** Telegram сообщает, что токен недействителен.

**EN:** Telegram says the token is not valid.

**Что делать:** Создайте новый токен в @BotFather (/token) и введите заново.

**Action:** Create a new token in @BotFather (/token) and enter it again.

## TELEGRAM-DESTINATION-FORMAT

ID чата выглядит неверно / Chat ID looks wrong

**RU:** У ID чата неверный вид.

**EN:** The chat ID has a wrong form.

**Что делать:** Используйте цифры (123456789 или -100… для группы) или @имя_канала.

**Action:** Use digits (123456789, or -100… for a group) or @channel_name.

## TELEGRAM-PERMISSION

Бот не может туда писать / Bot cannot write there

**RU:** У бота нет права писать в этот чат.

**EN:** The bot has no right to write to this chat.

**Что делать:** Нажмите Start в чате с ботом или сделайте бота администратором группы/канала.

**Action:** Press Start in the bot chat, or make the bot an administrator of the group/channel.

## TELEGRAM-RATE-LIMIT

Слишком много сообщений / Too many messages

**RU:** Telegram просит подождать перед следующим сообщением.

**EN:** Telegram asks to wait before the next message.

**Что делать:** Подождите; программа повторит сама. Поставьте более длинный интервал отчётов.

**Action:** Wait; the program retries by itself. Use a longer report interval.

## TELEGRAM-DNS

Адрес Telegram не найден / Telegram address not found

**RU:** Роутер не может найти адрес Telegram.

**EN:** The router cannot resolve the Telegram address.

**Что делать:** Проверьте интернет и DNS на роутере.

**Action:** Check the internet and DNS on the router.

## TELEGRAM-TLS

Защищённое соединение не удалось / Secure connection failed

**RU:** Защищённое соединение с Telegram не удалось.

**EN:** The secure connection to Telegram failed.

**Что делать:** Проверьте дату и время на роутере и пакет ca-bundle.

**Action:** Check the router date and time and the ca-bundle package.

## TELEGRAM-DELIVERY-UNKNOWN

Доставка не подтверждена / Delivery not confirmed

**RU:** Отчёт отправлен, но Telegram не подтвердил доставку.

**EN:** A report was sent but Telegram did not confirm it.

**Что делать:** Проверьте чат. Программа не отправляет дубликат автоматически.

**Action:** Check the chat. The program does not send a duplicate automatically.

## TELEGRAM-DELIVERED

Доставлено / Delivered

**RU:** Отчёт доставлен.

**EN:** A report was delivered.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## TELEGRAM-TEST-DELIVERED

Тест доставлен / Test delivered

**RU:** Тестовое сообщение доставлено.

**EN:** The test message was delivered.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## TELEGRAM-CONFIG

Настройка Telegram неполная / Telegram setup incomplete

**RU:** Настройки Telegram неполные или неверные.

**EN:** The Telegram settings are incomplete or invalid.

**Что делать:** Откройте «Настройки» → «2 · Telegram» и заполните токен и ID чата заново.

**Action:** Open Settings → 2 · Telegram and fill in the token and the chat ID again.

## TELEGRAM-CLOCK-BACKWARD

Часы пошли назад / Clock went back

**RU:** Часы роутера пошли назад, поэтому отчёты приостановлены.

**EN:** The router clock went back, so reports are paused.

**Что делать:** Проверьте дату и время роутера (NTP).

**Action:** Check the router date and time (NTP).

## TELEGRAM-STATE-CORRUPT

Состояние отчётов повреждено / Report state damaged

**RU:** Сохранённое состояние отчётов повреждено.

**EN:** The saved report state is damaged.

**Что делать:** Программа восстанавливает его сама; если не прошло, сохраните настройки Telegram заново.

**Action:** The program recovers it by itself; save the Telegram settings again if it stays.

## SETUP-INVALID

Неверный ввод / Invalid input

**RU:** В поле мастера неверное значение.

**EN:** A wizard field has an invalid value.

**Что делать:** Исправьте выделенные поля и проверьте ещё раз.

**Action:** Correct the highlighted fields and review again.

## SETUP-RANGE

Значение вне диапазона / Value out of range

**RU:** Число вне допустимого диапазона.

**EN:** A number is outside the allowed range.

**Что делать:** Укажите значение в диапазоне, показанном рядом с полем.

**Action:** Use a value inside the range shown next to the field.

## SETUP-SAVE-FAILED

Настройки не сохранены / Settings not saved

**RU:** Роутер не подтвердил сохранение настроек.

**EN:** The router did not confirm the saved settings.

**Что делать:** Повторите. Если снова, проверьте свободное место и журнал (logread).

**Action:** Try again. Check free space and the log (logread) if it repeats.

## SETUP-STOP-FIRST

Сначала остановите Auto / Stop Auto first

**RU:** Изменение недопустимо, пока работает Auto.

**EN:** The change is not allowed while Auto is running.

**Что делать:** Остановите Auto, дождитесь возврата на основной и меняйте настройки.

**Action:** Stop Auto, wait for the return to the primary, then change the settings.

## SETUP-SAVE-UNCONFIRMED

Сохранение не подтверждено / Save not confirmed

**RU:** Роутер не ответил на сохранение вовремя. Изменение могло записаться, а могло и нет.

**EN:** The router did not answer the save in time. The change may or may not have been written.

**Что делать:** Обновите страницу и посмотрите настройку. Если она неверная, сохраните ещё раз. Если роутер сообщает о несохранённых изменениях, см. «Помощь».

**Action:** Reload the page and look at the setting. If it is wrong, save again. If the router reports unsaved changes, see Help.

## SETUP-PENDING-DELTA

Есть несохранённые изменения роутера / Unsaved router changes

**RU:** На роутере есть неприменённые изменения настроек этой программы.

**EN:** The router has uncommitted changes of this program’s settings.

**Что делать:** Откройте LuCI → «Несохранённые изменения», примените или отмените их и повторите.

**Action:** Open LuCI → Unsaved changes and apply or revert them, then repeat.

## SETUP-PRIMARY-RESERVE-DISABLED

Основной или резервный отключён / Primary or reserve is off

**RU:** Выбранный основной или резервный профиль не включён для наблюдения.

**EN:** The chosen primary or reserve profile is not enabled for monitoring.

**Что делать:** Включите оба профиля в мастере «Система».

**Action:** Enable both profiles in the System wizard.

## SETUP-PROFILES

Профили не найдены / Profiles not found

**RU:** Выбранного профиля больше нет на роутере.

**EN:** A selected profile no longer exists on the router.

**Что делать:** Выберите существующие профили заново в мастере «Система».

**Action:** Choose existing profiles again in the System wizard.

## SPEED-DISABLED

Тесты скорости выключены / Speed tests are off

**RU:** Тесты скорости выключены.

**EN:** Speed tests are switched off.

**Что делать:** Включите их в «Расширенные настройки» → «Тесты» → «Настройки тестов скорости».

**Action:** Turn them on in Advanced settings → Tests → Speed test settings.

## SPEED-DAILY-LIMIT

Суточная квота исчерпана / Daily quota used

**RU:** Суточная квота данных для тестов исчерпана.

**EN:** The daily data quota for tests is used up.

**Что делать:** Дождитесь завтра или увеличьте квоту в настройках тестов скорости.

**Action:** Wait for tomorrow or raise the quota in the speed test settings.

## SPEED-COOLDOWN

Нужна пауза / Please wait

**RU:** Этот сервер тестировали недавно.

**EN:** A test of this server ran recently.

**Что делать:** Повторите позже.

**Action:** Try again later.

## SPEED-BUSY

Уже идёт другой тест / Another test is running

**RU:** Уже выполняется другой тест.

**EN:** Another test is running.

**Что делать:** Дождитесь его окончания или отмените.

**Action:** Wait until it finishes or cancel it.

## SPEED-TRAFFIC-BUSY

VPN сейчас занят / VPN is busy

**RU:** Через VPN идёт трафика больше лимита, поэтому тест пропущен.

**EN:** The VPN carries more traffic than the limit, so the test was skipped.

**Что делать:** Запустите тест, когда VPN менее загружен, или поднимите лимит.

**Action:** Run the test when the VPN is less busy or raise the limit.

## SPEED-ROUTE-UNVERIFIED

Путь теста не подтверждён / Test route unverified

**RU:** Не доказано, что тест идёт через выбранный VPN.

**EN:** It is not proven that the test goes through the chosen VPN.

**Что делать:** Убедитесь, что VPN подключён, и повторите.

**Action:** Make sure the VPN is connected and try again.

## SPEED-PROFILE-INACTIVE

VPN не подключён / VPN not connected

**RU:** VPN для теста не подключён.

**EN:** The VPN to test is not connected.

**Что делать:** Сначала подключите профиль в GL.iNet; эта программа VPN не подключает.

**Action:** Connect the profile in GL.iNet first; this program never connects VPNs.

## SPEED-NETWORK

Сетевая ошибка теста / Test network error

**RU:** Тесту не удалось соединиться.

**EN:** The test could not connect.

**Что делать:** Проверьте VPN и интернет и повторите.

**Action:** Check the VPN and the internet and try again.

## SPEED-CANCELLED

Отменено / Cancelled

**RU:** Тест отменён.

**EN:** The test was cancelled.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SCAN-DEADLINE-EXCEEDED

Проверка заняла слишком много времени / Check took too long

**RU:** Запрос «Проверить VPN сейчас» не завершился вовремя.

**EN:** The “Check the VPNs now” request did not finish in time.

**Что делать:** Нажмите кнопку ещё раз через минуту. Проверьте, что мониторинг работает.

**Action:** Press the button again after a minute. Check that the monitor is running.

## SCAN-STATE-CORRUPT

Состояние проверки повреждено / Check state damaged

**RU:** Сохранённое состояние проверки повреждено.

**EN:** The saved state of the check is damaged.

**Что делать:** Нажмите «Проверить VPN сейчас» ещё раз; создастся новое состояние.

**Action:** Press “Check the VPNs now” again; it creates a new state.

## CLOCK-001

Неверная дата на роутере / Wrong router date

**RU:** Дата роутера невозможна или скачет.

**EN:** The router date is impossible or jumped.

**Что делать:** Задайте часовой пояс и включите NTP в LuCI → «Система» → «Система». Статистика ждёт верных часов.

**Action:** Set the time zone and enable NTP in LuCI → System → System. Statistics wait for a correct clock.

## HISTORY-001

История недоступна / History unavailable

**RU:** Сохранённую историю контроллера не удаётся прочитать.

**EN:** The saved controller history cannot be read.

**Что делать:** Сохраните основной/резервный журнал и проверьте checksum, время, права и хранилище. Не удаляйте его и не обещайте автоматическое создание новой истории; повреждённые данные восстановления могут блокировать переходы.

**Action:** Preserve primary/backup history and inspect checksums, clock, permissions and storage. Do not delete it or promise an automatic fresh history; corrupt recovery evidence can block switching.

## FAULT-CERTIFIED-AUTO-REQUIRED

Для теста перехода нужен работающий Auto / Transition test needs running Auto

**RU:** Тесту нужны свежие подтверждения текущего канала и исправного второго. Подготовленный непрерывный Auto использует собственное закрытое состояние; прежнему ограниченному режиму по-прежнему нужен LAN-сертификат.

**EN:** The test needs fresh confirmation of the current channel and a healthy alternative. Prepared continuous pair Auto uses its own private state; the legacy bounded mode still needs its LAN certificate.

**Что делать:** Проверьте оба VPN и включите Auto на «Обзоре». Вернитесь к тесту перехода после свежих наблюдений.

**Action:** Check both VPN channels and start Auto on Overview. Reopen the transition test after fresh observations arrive.

## FAULT-UNVERIFIED

Сбой не подтверждён / Failure test not confirmed

**RU:** Роутер не подтвердил, что имитация сбоя применена или снята.

**EN:** The router did not confirm that the simulated failure was applied or removed.

**Что делать:** Нажмите «Отменить сбой сейчас», проверьте на «Обзоре», что трафик идёт, и повторите.

**Action:** Press “Cancel fault now”, check the Overview that traffic works, then try again.

## FAULT-UNKNOWN

Итог теста сбоя неизвестен / Failure test result unknown

**RU:** Итог запроса на сбой неизвестен.

**EN:** The result of the failure request is unknown.

**Что делать:** Обновите страницу. Если через VPN нет трафика, нажмите «Отменить сбой сейчас».

**Action:** Reload the page. If the VPN has no traffic, press “Cancel fault now”.

## FAULT-CANCEL-UNKNOWN

Отмена не подтверждена / Cancel not confirmed

**RU:** Запрос на отмену отправлен, но не подтверждён.

**EN:** The cancel request was sent but not confirmed.

**Что делать:** Проверьте страницу «Тесты» через минуту. Сбой также заканчивается сам по истечении времени (таймаут в роутере).

**Action:** Check the Tests page after a minute. The failure also ends by itself when its time is over (a timeout in the router).

## FAULT-RPC-UNCONFIRMED

Нет ответа от роутера / No answer from the router

**RU:** Страница не получила подтверждённого ответа на запрос сбоя.

**EN:** The page did not get a confirmed answer to the failure request.

**Что делать:** Обновите страницу и посмотрите состояние теста, прежде чем повторять.

**Action:** Reload the page and look at the state of the test before repeating.

## FAULT-FIELDS

Неверный запрос / Invalid request

**RU:** В запросе сбоя неверные поля.

**EN:** The failure request had wrong fields.

**Что делать:** Обновите страницу (Ctrl+F5) и повторите.

**Action:** Reload the page (Ctrl+F5) and try again.

## FAULT-HISTORY-UNAVAILABLE

История сбоев недоступна / Failure history unavailable

**RU:** Сохранённую историю тестов сбоя не удаётся прочитать.

**EN:** The saved history of failure tests cannot be read.

**Что делать:** Сохраните файлы истории тестов и проверьте чтение/запись/целостность. Очистка и итог теста проверяются отдельно; новая история сама по себе не гарантируется.

**Action:** Keep the stored fault-history files and inspect read/write/integrity errors. Cleanup and test outcome must be checked separately; a new history is not guaranteed automatically.

## FAULT-STATE-CORRUPT

Состояние сбоя повреждено / Failure state damaged

**RU:** Сохранённое состояние теста сбоя повреждено.

**EN:** The saved state of a failure test is damaged.

**Что делать:** Нажмите «Отменить сбой сейчас»; программа уберёт собственное правило трафика.

**Action:** Press “Cancel fault now”; the program cleans up its own traffic rule.

## FAULT-NFT-QUERY-FAILED

Не удаётся прочитать правило межсетевого экрана / Cannot read the firewall rule

**RU:** Роутер не ответил на запрос о собственном временном правиле программы.

**EN:** The router did not answer a query about the program’s own temporary rule.

**Что делать:** Дождитесь таймаута теста (до 3 минут) и повторите; больше ничего не меняется.

**Action:** Wait for the timeout of the test (up to 3 minutes) and try again; nothing else is changed.

## FAULT-TABLE-ALREADY-EXISTS

Предыдущий тест ещё активен / A previous test is still active

**RU:** Собственное временное правило программы от прошлого теста ещё существует.

**EN:** The program’s own temporary rule from a previous test still exists.

**Что делать:** Нажмите «Отменить сбой сейчас» или дождитесь таймаута.

**Action:** Press “Cancel fault now” or wait for its timeout.

## HISTORY-PARTIAL

История частично объединена / History partly aggregated

**RU:** Старые измерения объединены или удалены, чтобы хранилище и ответ роутера оставались небольшими.

**EN:** Older measurements were aggregated or pruned to keep the storage and the answer size small.

**Что делать:** Исправлять нечего. Недавние дни полные; очень старые подробности сведены в итоги.

**Action:** Nothing to fix. Recent days are complete; very old details are summarised.

## SPEED-HISTORY-TRUNCATED

История скорости сокращена / Speed history shortened

**RU:** Хранятся только новейшие результаты скорости; старые удалены.

**EN:** Only the newest speed results are kept; older ones were dropped.

**Что делать:** Исправлять нечего. Сохраните нужное до удаления.

**Action:** Nothing to fix. Export what you need before it is dropped.

## JOURNAL-INTEGRITY-FAILED

Журнал не прошёл проверку / Journal failed its check

**RU:** У журнала транзакций неверная контрольная сумма.

**EN:** The transaction journal has a wrong checksum.

**Что делать:** Не удаляйте его. Следуйте router-test-kit/EMERGENCY.md и просите помощи, приложив вывод show.

**Action:** Do not delete it. Follow router-test-kit/EMERGENCY.md and ask for help with the output of show.

## WEBSITE-*

Подробность замера сайтов / Website measurement detail

**RU:** Результат проверки сайтов или его архив не подтверждены. Эта подробность сама по себе не доказывает отказ VPN; старая метрика не подставляется.

**EN:** A website result or its archive could not be verified. This detail alone does not establish a VPN failure; no older metric is substituted.

**Что делать:** Дождитесь новой проверки. Сохраните код и посмотрите метод и историю ответов сайтов в «Помощи».

**Action:** Wait for a fresh check. Preserve the code and inspect the website-response method and history in Help.

## WEBSITE-IDENTITY-CHANGED

Изменилась привязка VPN / VPN identity changed

**RU:** Поколение или туннель замера не совпадает с показанным каналом. Старое значение не подставляется.

**EN:** The measured VPN generation or tunnel no longer matches the displayed channel. No old value is substituted.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-DNS-FAILED

Не прошёл DNS сайта / Website DNS failed

**RU:** Имя одного из выбранных обычных сайтов не разрешилось через этот VPN. Это отдельный результат, не техническая проверка здоровья.

**EN:** A selected ordinary website name could not be resolved through this VPN. This is separate from the technical health probes.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-HTTP-FAILED

Не прошёл HTTP сайта / Website HTTP failed

**RU:** Сайт не вернул ожидаемый HTTP-статус и полные заголовки. Полного среднего трёх сайтов нет.

**EN:** The website did not return its expected HTTP status and complete headers. There is no complete three-site mean.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-TIMEOUT

Истекло время ответа сайта / Website response timed out

**RU:** Новая проверка сайта превысила ограниченное время. Отсутствующий замер не считается нулём миллисекунд.

**EN:** A fresh website check exceeded its bounded deadline. Missing time is not a zero-millisecond response.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-TLS-FAILED

Не прошёл TLS сайта / Website TLS failed

**RU:** Новое HTTPS-соединение не смогло установить проверенный TLS с выбранным сайтом.

**EN:** The fresh HTTPS connection could not establish verified TLS to the selected website.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-RESPONSE-FAILED

Не получен ответ сайта / Website response failed

**RU:** Отдельная проверка трёх сайтов не прошла. Она не даёт значение задержки и не меняет здоровье Auto или маршрутизацию.

**EN:** The independent three-site check failed. It supplies no delay value and does not change Auto health or routing.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-UNAVAILABLE

Замер сайтов недоступен / Website measurement unavailable

**RU:** Свежего полного замера трёх сайтов с проверенной привязкой к VPN нет. ICMP и технический HTTPS его не заменяют.

**EN:** No fresh complete identity-bound three-site result is available. ICMP and technical HTTPS times cannot replace it.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-PARTIAL

Ответили не все сайты / Only some websites answered

**RU:** Успешно ответили менее трёх выбранных сайтов. Показана полнота проверки; для среднего нужны все три.

**EN:** Fewer than three selected websites answered successfully. Coverage is shown; an average requires all three.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-CHECK-PENDING

Ожидается проверка сайтов / Website check pending

**RU:** Фоновый замер трёх сайтов ещё выполняется. Открытие страницы не запускает дополнительный запрос.

**EN:** The background three-site measurement is still being collected. Opening this page starts no extra request.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-NOT-SELECTED

VPN вне измеряемой пары / VPN is outside the measured pair

**RU:** Ограниченный замер трёх сайтов выполняется только для двух выбранных каналов. Страница не подключает другие профили.

**EN:** Only the two selected VPN channels receive the bounded three-site measurement. No other profile is connected by this page.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-DATA-STALE

Замер сайтов устарел / Website result is old

**RU:** Исходное время завершения вышло за срок свежести. Повторная выдача кеша не обновляет замер.

**EN:** The original completion time exceeds its freshness window. Publication of cached data does not renew a measurement.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-HISTORY-WRITE-FAILED

История сайтов не сохранена / Website history was not saved

**RU:** Отдельный архив ответов сайтов не удалось безопасно записать. Текущие проверки могут продолжаться; пропуски не дорисовываются.

**EN:** The separate website-response archive could not be safely written. Current checks can continue; missing history stays empty.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-HISTORY-UNAVAILABLE

История сайтов недоступна / Website history unavailable

**RU:** Архив ответов сайтов или его контрольная сумма не подтверждены. Старая история технического HTTPS не подставляется.

**EN:** The website-response archive or its checksum could not be verified. Old technical HTTPS history is not substituted.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## WEBSITE-HISTORY-PAIR-LIMIT

Достигнут лимит пар истории / Website history pair limit reached

**RU:** Ограниченный архив не может добавить ещё одну пару каналов в пределах лимита. Профили и старые значения не переименовываются.

**EN:** The bounded archive cannot add another channel pair while preserving its limits. No profile or historical value is silently relabelled.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## PING-HISTORY-WRITE-FAILED

История пинга не сохранена / Ping history was not saved

**RU:** Отдельный архив ответов сайтов не удалось безопасно записать. Текущие проверки могут продолжаться; пропуски не дорисовываются.

**EN:** The separate ping-response archive could not be safely written. Current checks can continue; missing history stays empty.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## PING-HISTORY-UNAVAILABLE

История пинга недоступна / Ping history unavailable

**RU:** Архив ответов сайтов или его контрольная сумма не подтверждены. Старая история технического HTTPS не подставляется.

**EN:** The ping-response archive or its checksum could not be verified. Old technical HTTPS history is not substituted.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## PING-HISTORY-PAIR-LIMIT

Достигнут лимит пар истории / Ping history pair limit reached

**RU:** Ограниченный архив не может добавить ещё одну пару каналов в пределах лимита. Профили и старые значения не переименовываются.

**EN:** The bounded archive cannot add another channel pair while preserving its limits. No profile or historical value is silently relabelled.

**Что делать:** Дождитесь новой фоновой проверки. Метод и полнота описаны в «Помощь → Ответ трёх сайтов».

**Action:** Wait for a fresh background check. Read Help → Three-site response for method and coverage.

## KNOWN-STOCK-DERIVED-RECOVERY

Служебные изменения учтены / Known stock changes reconciled

**RU:** Остановленная неудачная операция сверена с точной проверенной копией и действующими служебными полями. Исходные журнал и состояние заархивированы, штатный защищённый Stop завершён. Это не выполненное переключение VPN и не разрешение принимать другие изменения.

**EN:** The stopped failed operation was reconciled with the exact verified backup and current stock-derived fields. Original journal/state bytes were archived and ordinary guarded Stop completed. This is not a completed VPN switch or permission to accept other changes.

**Что делать:** Завершите проверенное обновление и посмотрите свежий статус. Для Auto по-прежнему нужны штатные проверки готовности и разрешённый Старт. Сохраните доказательства неудачной операции.

**Action:** Complete the reviewed update and inspect fresh status. Auto still needs its normal readiness checks and an explicit authorized Start. Keep the failed evidence.

## RTP-BOOT-PRECONDITION-UNVERIFIED

Не подтверждена штатная подготовка VPN / Router VPN runtime preparation is not confirmed

**RU:** Штатному VPN-скрипту нужны известные временные каталоги и пустой служебный флаг. Не удалось подтвердить их подготовку, принадлежность или точный контракт прошивки. Успешное завершение скрипта само по себе не подтверждает наличие kernel-правил.

**EN:** The pinned stock VPN script needs known runtime directories and an empty gate file before it can apply rules. Their preparation, ownership or exact firmware contract could not be confirmed. A successful script exit alone never proves that kernel rules exist.

**Что делать:** Используйте проверенное обновление и штатный Старт. Приложение готовит только известные безопасные временные объекты в рамках текущей команды, затем проверяет действующие kernel-правила. Не запускайте полный штатный boot и не создавайте файлы поверх неизвестных путей вручную.

**Action:** Use the reviewed update and normal Start procedure. The application prepares only the known safe runtime prefix under the current command, then checks actual kernel rules. Do not run full stock boot or create files over unknown paths manually.

## KERNEL-POLICY-VERIFIED

Правила выбора VPN проверены / Router VPN rules verified

**RU:** Применённые правила меток пакетов и маршрутизации ядра соответствуют выбранным правилам VPN. Проверены только действующие правила; это не подтверждает доступ к интернету, итог переключения или независимую проверку клиента LAN.

**EN:** The applied kernel packet-mark and routing rules match the selected VPN policy. This verifies the compiled rules only; it does not prove internet availability, a route-switch result or independent LAN-client acceptance.

**Что делать:** Доступность связи и состояние Auto проверяйте по отдельным текущим результатам HTTPS/DNS и выбора канала. Для этого подтверждённого результата дополнительное изменение правил не нужно.

**Action:** Use the separate current HTTPS/DNS and channel-selection results for connectivity and Auto state. No extra policy change is needed for this verified result.

## KERNEL-POLICY-UNVERIFIED

Действующие правила выбора VPN не подтверждены / Applied VPN selection rules are unverified

**RU:** Действующие правила ядра не подтверждают ожидаемый выбор VPN для трафика. Подключение туннеля само по себе не доказывает, какой канал несёт трафик.

**EN:** The current kernel rules do not confirm the expected VPN traffic selection. Tunnel connectivity alone cannot prove which channel carries traffic.

**Что делать:** Проверьте текущие правила VPN и сохранённую причину отказа. Применяйте правила штатным проверенным способом и подтвердите результат перед повтором.

**Action:** Inspect the current VPN policy and the recorded refusal. Use the normal reviewed policy application and verify its readback before retrying.

## PAIR-POLICY-UNVERIFIED

Правила основного и резервного VPN не подтверждены / Primary and reserve VPN policy is unverified

**RU:** Приложение не может подтвердить соответствие выбранных основного и резервного VPN правилам роутера. Порядок списка не считается доказательством действующего маршрута.

**EN:** The application cannot verify how the selected primary and reserve roles map to the router VPN rules. It does not assume that list order proves the active traffic route.

**Что делать:** Проверьте выбранную пару и фактически применённые правила VPN. Сохраните причину отказа и повторяйте только после подтверждения привязки роутером.

**Action:** Review the selected pair and the actual applied VPN policy. Keep the refusal evidence and retry only after the router confirms that binding.

## PROBE-SETTINGS-FIELDS

Неполный запрос уровня опроса / Probe level request is incomplete

**RU:** Страница отправила запрос уровня опроса без нужных полей уровня и ускорения.

**EN:** The page sent a probe-level request without the expected level and boost fields.

**Что делать:** Обновите страницу (Ctrl+F5) и примените уровень ещё раз.

**Action:** Reload the page (Ctrl+F5) and apply the level again.

## PROBE-SETTINGS-RANGE

Неизвестный уровень опроса / Unknown probe level

**RU:** Существуют только уровни от 1 до 5.

**EN:** Only levels 1 to 5 exist.

**Что делать:** Выберите уровень ползунком и примените ещё раз.

**Action:** Choose a level with the slider and apply it again.

## PROBE-SETTINGS-BUSY

Идёт переключение / A switch is in progress

**RU:** Уровень опроса не меняется, пока идёт переключение или восстановление канала.

**EN:** The probe level is not changed while a channel switch or recovery is running.

**Что делать:** Дождитесь окончания переключения и примените уровень ещё раз.

**Action:** Wait until the switch finishes, then apply the level again.

## PROBE-POLICY-UNAVAILABLE

Состояние уровня опроса недоступно / Probe level state unavailable

**RU:** Мониторинг не смог опубликовать текущий уровень опроса в этом цикле. Сам мониторинг продолжается.

**EN:** The monitor could not publish the current probe level this cycle. Monitoring itself continues.

**Что делать:** Дождитесь следующей проверки; если не проходит, обновите страницу.

**Action:** Wait for the next check; if it stays, reload the page.

## PROBE-HISTORY-UNAVAILABLE

Журнал решений недоступен / Decision log unavailable

**RU:** Роутер не вернул журнал решений уровня опроса.

**EN:** The router did not return the probe decision log.

**Что делать:** Закройте и снова откройте журнал через минуту.

**Action:** Close and open the log again in a minute.

## PING-PENDING

Пинг ещё не измерен / Ping not measured yet

**RU:** Роутер ещё не закончил первый пинг через этот канал после запуска или смены настройки.

**EN:** The router has not finished the first ping through this channel since it started or since the setting changed.

**Что делать:** Дождитесь следующей проверки (см. таймер под светофором).

**Action:** Wait for the next check (see the countdown under the traffic light).

## RESPONSE-METRIC-INVALID

Неизвестный способ измерения отклика / Unknown response measurement

**RU:** Страница отправила способ измерения, которого нет на роутере.

**EN:** The page sent a measurement the router does not offer.

**Что делать:** Обновите страницу (Ctrl+F5) и выберите снова.

**Action:** Reload the page (Ctrl+F5) and choose again.

## MANUAL-ALREADY-SELECTED

Этот канал уже выбран / This channel is already selected

**RU:** Запрошенный канал уже выбран, его маршрут трафика проверен. Повторное переключение не нужно; этот результат не включает Auto.

**EN:** The requested channel is already selected and its traffic path was verified. Another route switch is unnecessary; this result does not start Auto.

**Что делать:** Продолжайте работу через подтверждённый канал. Дождитесь обновления состояния; не повторяйте переключение только ради изменения индикатора.

**Action:** Continue using the verified channel. Wait for the current status to refresh; do not repeat a switch merely to change the indicator.

## PING-FAILED

Нет ответа ICMP / No ICMP reply

**RU:** Отдельная ICMP-проверка через этот VPN не прошла. Это не меняет результаты HTTPS/DNS, выбранный маршрут или решение Auto.

**EN:** The separate ICMP echo through this VPN did not complete successfully. This does not change its HTTPS/DNS health, selected route or Auto decision.

**Что делать:** Дождитесь следующей Ping-проверки. Некоторые сети блокируют ICMP при работающем HTTPS; сравните отдельные результаты HTTPS/DNS.

**Action:** Wait for the next Ping check. Some networks block ICMP even when HTTPS works; compare the independent HTTPS/DNS results.

## PING-DATA-STALE

ICMP-результат устарел / ICMP result is old

**RU:** Сохранённый ICMP-результат старше допустимого срока. Прежние миллисекунды не показываются как текущее измерение.

**EN:** The saved ICMP result is older than its permitted freshness window. Its old milliseconds are not shown as a current measurement.

**Что делать:** Дождитесь фоновой проверки. Если данные остаются старыми, проверьте мониторинг и связь с роутером.

**Action:** Wait for the next background check. If results remain old, inspect Monitoring and the router connection.

## PING-CHECK-PENDING

Ожидается ICMP-проверка / Waiting for an ICMP check

**RU:** Текущее ICMP-измерение этого VPN ещё собирается. Миллисекунды не подставляются из HTTPS или прежнего подключения.

**EN:** A current ICMP measurement for this VPN is still being collected. No milliseconds are invented from HTTPS or an earlier connection.

**Что делать:** Дождитесь фоновой проверки: открытие страницы не отправляет дополнительный Ping-запрос.

**Action:** Wait for the background check; opening the page sends no additional Ping request.

## PING-UNAVAILABLE

ICMP-измерение недоступно / ICMP measurement is unavailable

**RU:** Для этого канала нет подтверждённого ICMP-измерения. Этот результат отделён от HTTPS/DNS и выбора канала трафика.

**EN:** No verified ICMP measurement is available for this channel. The result is separate from HTTPS/DNS connectivity and traffic selection.

**Что делать:** Проверьте мониторинг роутера и выбранную пару VPN. Не смешивайте этот результат с HTTPS/DNS; отсутствие Ping не считается измеренным отказом.

**Action:** Inspect the router monitoring state and the selected VPN pair. Keep the HTTPS/DNS result separate; do not treat missing Ping as a measured outage.

## PING-INACTIVE

ICMP-проверка не выполняется / ICMP check is inactive

**RU:** Этот VPN отключён или не подключён, поэтому текущее ICMP-измерение через него не выполняется.

**EN:** This VPN is disabled or not connected, so no current ICMP measurement is taken through it.

**Что делать:** Проверьте существующее VPN-подключение на роутере. Строка Ping не подключает туннель и не меняет Auto.

**Action:** Review the existing VPN connection on the router. The Ping display does not connect a tunnel or change Auto.

## PING-IDENTITY-CHANGED

ICMP-результат относится к другому подключению / ICMP result belongs to another VPN connection

**RU:** Изменились интерфейс, туннель или поколение VPN-подключения. Прежний ICMP-результат отброшен, а не приписан текущему подключению.

**EN:** The VPN interface, tunnel or connection generation changed. The previous ICMP result is discarded instead of being attributed to the current connection.

**Что делать:** Дождитесь, пока роутер подтвердит новое VPN-подключение и выполнит отдельную ICMP-проверку.

**Action:** Wait until the router observes the new VPN connection and completes its own ICMP check.

## PING-NOT-SELECTED

VPN не входит в измеряемую пару / VPN is outside the measured pair

**RU:** Фоновые ICMP-проверки выполняются для выбранных основного и резервного VPN. Этот профиль не входит в эту пару.

**EN:** The background ICMP checks cover the selected primary and reserve VPNs. This profile is outside that pair.

**Что делать:** Если вы хотели наблюдать этот VPN, проверьте выбранную пару. Открытие его информации не запускает проверку.

**Action:** Review the selected pair if this is the VPN you intended to monitor. Opening its information does not start a probe.

## UI-HELP-LOAD-FAILED

Не удалось загрузить справку / Help could not be loaded

**RU:** Не удалось загрузить модуль справки, обучения и каталога. Другие страницы продолжают работать.

**EN:** The optional Help, Training and catalogue module could not be loaded. Other pages keep working.

**Что делать:** Нажмите «Повторить». Если ошибка остаётся, обновите страницу и проверьте связь с роутером.

**Action:** Press Retry. If the failure continues, reload the page and check the router connection.

## PUBLICATION-RECORD-SCOPE

Запись выпуска отличается от проверенного исходника / Release record differs from the tested source

**RU:** Запись выпуска содержит изменения вне разрешённых файлов либо не подтверждены родительский коммит или хеш пакета.

**EN:** The release record contains changes outside the allowed package record, or its parent or package hash could not be verified.

**Что делать:** Запустите полный CI на этом коммите либо создайте прямой дочерний коммит только с проверенным пакетом, контрольной суммой, новыми заметками выпуска и соответствующими полями хеша и размера.

**Action:** Run the full CI on this commit, or create a direct child record containing only the verified package, checksum, new release notes and matching hash and size fields.

## PUBLICATION-CI-LUA

Квитанция CI не подтверждает проверку Lua / The CI receipt does not prove Lua tests ran

**RU:** Квитанция среды проверки инструментов не подтверждает наличие Lua и выполнение хотя бы одного теста с Lua.

**EN:** The tools runtime receipt does not confirm Lua availability and at least one completed Lua-backed test.

**Что делать:** Используйте проверенный образ CI с Lua и lua-cjson, повторите проверки обеих сред и сохраните неудачную квитанцию.

**Action:** Use the reviewed CI image with Lua and lua-cjson, run both runtime checks again, and keep the failed receipt as evidence.

## SPEED-PAUSE-UNVERIFIED

Не удалось проверить паузу / Pause could not be verified

**RU:** Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.

**EN:** The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.

**Что делать:** Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется.

**Action:** Wait for the current operation to finish and retry. A manual Stop is never undone.

## SPEED-PAUSE-BUSY

Пауза ещё завершается / Pause recovery in progress

**RU:** Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.

**EN:** The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.

**Что делать:** Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется.

**Action:** Wait for the current operation to finish and retry. A manual Stop is never undone.

## SPEED-PAUSE-LOST

Условия паузы изменились / Pause ownership changed

**RU:** Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.

**EN:** The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.

**Что делать:** Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется.

**Action:** Wait for the current operation to finish and retry. A manual Stop is never undone.

## SPEED-PAUSE-TIMEOUT

Нет подтверждения паузы / Pause acknowledgement timed out

**RU:** Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.

**EN:** The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.

**Что делать:** Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется.

**Action:** Wait for the current operation to finish and retry. A manual Stop is never undone.

## SPEED-PAUSE-MODE

Состояние Auto не готово к паузе / Auto transition is not ready for pause

**RU:** Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.

**EN:** The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.

**Что делать:** Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется.

**Action:** Wait for the current operation to finish and retry. A manual Stop is never undone.

## SPEED-CPU-UNKNOWN

Загрузка CPU не прочитана / CPU observation unavailable

**RU:** Тест скорости не может продолжаться при текущих условиях паузы. VPN остаются подключёнными.

**EN:** The speed test cannot continue under the current quiet-window conditions. Existing VPNs stay connected.

**Что делать:** Дождитесь завершения текущей операции и повторите. Ручной Stop не отменяется.

**Action:** Wait for the current operation to finish and retry. A manual Stop is never undone.

## DEVICE-MODEL-INVALID

Выберите поддерживаемую модель / Choose a supported router model

**RU:** Сохранённая или выбранная модель не входит в список: авто, MT6000, MT3000.

**EN:** The saved or requested model is not Automatic, MT6000 or MT3000.

**Что делать:** Откройте настройки и проверьте модель роутера на первом шаге мастера.

**Action:** Open Settings and review the router model on the first setup step.

## DEVICE-MODEL-MISMATCH

Модель роутера не совпадает / Router model does not match

**RU:** Выбранная модель отличается от обнаруженного оборудования либо оборудование не удалось проверить.

**EN:** The selected model differs from detected hardware, or hardware could not be verified.

**Что делать:** Выберите автоопределение или обнаруженную модель; выбор модели не включает неподдерживаемое переключение.

**Action:** Choose automatic detection or the actual detected model; model selection never enables unsupported switching.

## MANUAL-FIELDS

Форма ручного запроса изменилась / Manual request form changed

**RU:** В запросе отсутствуют поля либо есть лишние.

**EN:** The request contains missing or unexpected fields.

**Что делать:** Обновите страницу и выберите одну из двух кнопок ручного переключения.

**Action:** Reload the page and choose one of the two manual switch buttons.

## MANUAL-DIRECTION-INVALID

Выберите допустимое направление / Choose a supported direction

**RU:** Запрошено направление, отличное от сохранённого основного или резервного.

**EN:** The requested direction is neither the saved primary nor the reserve.

**Что делать:** Обновите страницу и используйте переключение на основной либо резервный.

**Action:** Reload the page and use Switch to primary or Switch to reserve.

## MANUAL-STATE-UNVERIFIED

Состояние ручного управления неизвестно / Manual control state is unknown

**RU:** Не удалось проверить запись запроса или остановки; новое переключение заблокировано.

**EN:** The request or Stop records could not be verified; a new switch is blocked.

**Что делать:** Обновите состояние. Используйте аварийную остановку и доступное восстановление; не удаляйте записи состояния.

**Action:** Refresh the status. Keep Emergency Stop and trusted recovery available; do not delete the state records.

## MANUAL-ALREADY-CLAIMED

Запрос уже принят в работу / Request was already taken

**RU:** Контроллер уже принял или завершил этот запрос; повторное выполнение недопустимо.

**EN:** The controller has already taken or finished this request; it must not run it twice.

**Что делать:** Дождитесь свежего состояния и проверьте фактический путь перед новым явным запросом.

**Action:** Wait for fresh status and review the actual path before making another explicit request.

## MANUAL-REQUEST-EXPIRED

Время ручного запроса истекло / Manual request expired

**RU:** Запрос не принят в течение короткого срока действия. Это не подтверждает текущий путь трафика.

**EN:** The request was not taken within its short validity window. This does not confirm the current traffic path.

**Что делать:** Обновите состояние роутера и повторите только при необходимости переключения.

**Action:** Refresh the router state and repeat only if the switch is still needed.

## STOP-SUPERSEDED-MANUAL

Остановка отменила ожидающее переключение / Stop cancelled the pending switch

**RU:** Аварийная остановка поступила после ручного запроса, поэтому ожидающий запрос не выполнится.

**EN:** An Emergency Stop arrived after this manual request, so the pending request cannot run.

**Что делать:** Проверьте текущий путь. Для последующего переключения нужен новый явный запрос.

**Action:** Review the current path. A later switch requires a new explicit request.

## MANUAL-CONFIG-CHANGED

Настройки изменились во время запроса / Settings changed during the request

**RU:** Выбранная пара, окно теста или политика больше не соответствует запросу.

**EN:** The selected pair, trial window or policy no longer matches the request.

**Что делать:** Обновите страницу, проверьте пару и необходимые проверки перед новым запросом.

**Action:** Refresh and review the pair and required checks before requesting again.

## MANUAL-SUPERVISOR-UNAVAILABLE

Нет свежего состояния контроллера / No fresh controller state

**RU:** Контроллер переключений не предоставил недавнего проверенного состояния.

**EN:** The switching controller has not supplied a recent verified status.

**Что делать:** Проверьте службу мониторинга и дождитесь свежего состояния. Установка только для мониторинга не выполняет нативных переключений.

**Action:** Check Service monitor and wait for fresh status. A monitor-only installation cannot perform native switches.

## MANUAL-STOP-AUTO-FIRST

Остановите Auto перед ручным переключением / Stop Auto before manual switching

**RU:** Auto активен; отдельное ручное переключение не должно с ним конкурировать.

**EN:** Auto is active; a separate manual switch cannot compete with it.

**Что делать:** Нажмите аварийную остановку и проверьте получившийся путь перед ручным переключением.

**Action:** Press the Auto power button to stop and review the resulting path before trying manual switching.

## MANUAL-SELECTION-UNVERIFIED

Выбранная пара не проверена / Selected pair is not verified

**RU:** Контроллер не может подтвердить выбранные основной и резервный профили либо их политику маршрутизации.

**EN:** The controller cannot prove the selected primary and reserve or their routing policy.

**Что делать:** Проверьте сохранённую пару в настройках и дождитесь свежих согласованных проверок.

**Action:** Review the saved pair in Settings and obtain fresh matching checks.

## MANUAL-REQUEST-PENDING

Другой ручной запрос ещё выполняется / Another manual request is pending

**RU:** Ручное переключение уже ожидает выполнения или выполняется.

**EN:** A manual switch is already queued or running.

**Что делать:** Дождитесь результата либо используйте аварийную остановку; не отправляйте дубликаты.

**Action:** Wait for its result or press the Auto power button to stop; do not submit duplicates.

## MANUAL-REQUEST-UNCONFIRMED

Запрос не подтверждён / Request was not confirmed

**RU:** Надёжное подтверждение не получено. Запрос мог сохраниться.

**EN:** No reliable acknowledgement was received. The request may have been stored.

**Что делать:** Обновите состояние и проверьте фактический путь перед решением о повторе.

**Action:** Refresh status and inspect the actual path before deciding whether to retry.

## MANUAL-RESULT-INVALID

Запись результата некорректна / Result record is invalid

**RU:** Запись результата не соответствует формату ручного запроса. Она не доказывает успех.

**EN:** The result record does not match the supported manual request format. It does not prove success.

**Что делать:** Сохраните диагностику и проверьте текущий путь; не принуждайте завершение и не стирайте записи восстановления.

**Action:** Keep the diagnostics and check the current path; do not force completion or erase recovery records.

## MANUAL-COMPLETION-UNVERIFIED

Завершение переключения не доказано / Switch completion is not proved

**RU:** Контроллер не смог проверить данные транзакции, необходимые для подтверждения завершения запроса.

**EN:** The controller could not verify the transaction evidence required to mark this request complete.

**Что делать:** Проверьте свежие данные маршрута и доступности. При необходимости используйте описанные средства восстановления.

**Action:** Review fresh route and connectivity status. Use the documented recovery controls if needed.

## RETURN-UNCONFIRMED

Возврат на основной не подтверждён / Return to primary is unconfirmed

**RU:** У запроса возврата нет проверенного успешного результата. Резерв может ещё использоваться.

**EN:** The return request has no verified successful result. The reserve may still be in use.

**Что делать:** Проверьте фактический путь и доступность основного перед повторным возвратом.

**Action:** Inspect the actual path and primary health before requesting another return.

## MANUAL-RESULT-UNCONFIRMED

Результат ручного переключения неизвестен / Manual result is unknown

**RU:** Запрос не дал доверенного конечного результата. Подтверждение очереди не подтверждает маршрут.

**EN:** The request did not produce a trusted final result. A queue acknowledgement is not route confirmation.

**Что делать:** Обновите состояние и проверьте средства остановки или восстановления перед повторным действием.

**Action:** Refresh status and review Stop or recovery controls before repeating any action.

## MANUAL-SUPERVISOR-RECOVERED

Контроллер восстановился после незавершённого запроса / Controller recovered an unfinished request

**RU:** После перезапуска контроллер обнаружил незавершённый запрос без достаточного подтверждения результата. Автоматически он не повторяется.

**EN:** After restarting, the controller found an unfinished request without sufficient proof of completion. It is not replayed automatically.

**Что делать:** Проверьте текущий путь и состояние восстановления перед новым запросом.

**Action:** Review the current path and recovery status before issuing a new request.

## MANUAL-TRANSACTION-STATE-UNVERIFIED

Прошлое переключение не завершилось / The previous switch did not finish

**RU:** Не удалось подтвердить отсутствие прежней транзакции или защитной блокировки приложения.

**EN:** The absence of an earlier transaction or application safety guard could not be verified.

**Что делать:** Используйте доступные остановку и восстановление. Завершите прежнюю транзакцию по описанной процедуре перед новой.

**Action:** Keep Stop and recovery available. Resolve the existing transaction through the documented recovery procedure before starting another.

## MANUAL-REQUEST-INVALID

Ручному запросу нельзя доверять / Manual request could not be trusted

**RU:** Последняя проверка контроллера отклонила идентификатор либо формат ручного запроса.

**EN:** The final controller boundary rejected the manual request identity or format.

**Что делать:** Обновите приложение и проверьте текущее состояние перед новым явным запросом.

**Action:** Refresh the application and review current status before making a new explicit request.

## OPERATOR-MANUAL

Команда ручного выбора канала / Manual-channel control command

**RU:** Это семейство команд ручного управления, а не доказательство нажатия человеком. Сохранённый инициатор различает оператора, автоматику, тест или программный доступ.

**EN:** This is the manual-control command family, not proof that a human clicked. The recorded initiator distinguishes operator, automation, test or programmatic access.

**Что делать:** Посмотрите последующий итог транзакции и текущий подтверждённый путь, чтобы узнать результат.

**Action:** Read the later transaction outcome and current confirmed path to see whether it succeeded.

## MT3000-MANUAL-ADAPTER-NOT-CERTIFIED

Ручное переключение MT3000 не подтверждено / MT3000 manual switching is not certified

**RU:** Адаптер ручного переключения GL-MT3000 не прошёл необходимое подтверждение. Отдельные успешные наблюдения не разрешают переключение.

**EN:** The GL-MT3000 manual adapter has not passed the required certification. Passing individual observations does not authorize a switch.

**Что делать:** Продолжайте мониторинг; завершите описанные проверки роутера и LAN перед включением адаптера.

**Action:** Continue monitoring; complete the documented router and LAN acceptance before enabling this adapter.

## MT3000-COLLECTION-DEADLINE

Проверка готовности заняла слишком много времени / Readiness check took too long

**RU:** Сбор данных роутера превысил ограниченное время; неполный снимок не разрешает переключение.

**EN:** The bounded collection of router evidence exceeded its deadline; the incomplete snapshot cannot authorize a switch.

**Что делать:** Дождитесь спокойного состояния роутера и запросите свежие данные. Если повторяется, проверьте нагрузку.

**Action:** Wait for the router to settle and request fresh status. If it repeats, inspect router load.

## MT3000-COLLECTION-CLOCK-CHANGED

Часы роутера изменились во время проверок / Router clock changed during checks

**RU:** При сборе данных готовности нарушилась непрерывность времени. Их временным отметкам нельзя доверять.

**EN:** Clock continuity was lost while readiness evidence was collected. Its timing cannot be trusted.

**Что делать:** Проверьте часы роутера и дождитесь стабильного времени перед новым сбором данных.

**Action:** Review the router clock and wait for stable time before collecting new evidence.

## MT3000-READ-TIMEOUT

Чтение данных роутера превысило время / Router read timed out

**RU:** Команда чтения готовности не завершилась за разрешённое время.

**EN:** A read-only readiness command did not finish in its allowed time.

**Что делать:** Подождите и обновите данные. Если повторяется, проверьте отзывчивость роутера.

**Action:** Wait and refresh. Inspect router responsiveness if this continues.

## MT3000-READ-FAILED

Не удалось прочитать данные роутера / Router evidence could not be read

**RU:** Команда сбора данных готовности завершилась ошибкой.

**EN:** A command used to collect readiness evidence failed.

**Что делать:** Сохраните код диагностики и проверьте службы и необходимые программы роутера перед повтором.

**Action:** Keep the diagnostic code and check the router services and required tools before retrying.

## MT3000-READ-UNVERIFIED

Чтение данных роутера не проверено / Router read could not be validated

**RU:** Ответ проверки готовности неполон, слишком велик либо имеет неожиданный формат.

**EN:** A readiness response was incomplete, oversized or did not match the expected format.

**Что делать:** Обновите данные после стабилизации роутера. Если повторяется, проверьте совместимость прошивки.

**Action:** Refresh once the router is stable. If repeated, have the firmware compatibility checked.

## MT3000-PLATFORM-UNVERIFIED

Модель роутера не проверена / Router model is not verified

**RU:** Собранные данные платы не соответствуют поддерживаемому варианту GL-MT3000.

**EN:** The collected board identity does not match the supported GL-MT3000 platform contract.

**Что делать:** Проверьте фактическую модель роутера. Мониторинг не означает поддержку ручного переключения.

**Action:** Check the actual router model. Monitoring does not grant manual switching support.

## MT3000-FIRMWARE-UNVERIFIED

Прошивка роутера не проверена / Router firmware is not verified

**RU:** Прошивка, ядро или архитектура отличается от проверенного сочетания GL-MT3000.

**EN:** The firmware, kernel or architecture differs from the inspected GL-MT3000 combination.

**Что делать:** Оставьте нативное переключение выключенным до проверки именно этого сочетания прошивки.

**Action:** Keep native switching disabled until this exact firmware combination has been reviewed.

## MT3000-FIREWALL-UNVERIFIED

Тип firewall не проверен / Firewall type is not verified

**RU:** Firewall роутера не соответствует варианту, необходимому этому адаптеру.

**EN:** The router firewall does not match the firewall arrangement required by this adapter.

**Что делать:** Сохраните текущие маршруты и проверьте совместимость firewall; не включайте адаптер принудительно.

**Action:** Keep current routes and have firewall compatibility reviewed; do not force the adapter on.

## FW3-INCLUDE-CONTRACT-UNVERIFIED

Интеграция firewall прошивки не проверена / Firmware firewall integration is unverified

**RU:** Настройки подключаемого скрипта firewall отличаются от проверенного варианта; безопасная координация перезагрузки не доказана.

**EN:** The firmware firewall include settings differ from the inspected contract; safe reload coordination is not proved.

**Что делать:** Сохраните текущие маршруты и проверьте интеграцию firewall прошивки перед переключением.

**Action:** Keep current routes and have the firmware firewall integration checked before switching.

## FW3-RUNTIME-STATE-UNVERIFIED

Рабочее состояние firewall неизвестно / Live firewall state is unknown

**RU:** Не удалось прочитать и проверить текущие зоны firewall.

**EN:** The current firewall zones could not be read and validated.

**Что делать:** Дождитесь завершения изменений firewall и обновите данные. Одни сохранённые настройки не доказывают готовность.

**Action:** Wait for any firewall changes to finish, then refresh. Do not infer readiness from saved settings alone.

## VENDOR-WORKER-QUIET-UNVERIFIED

Изменение VPN роутером может ещё выполняться / Router VPN changes may still be running

**RU:** Повторные наблюдения не подтвердили, что процессы VPN штатной прошивки свободны.

**EN:** Repeated observations did not prove that the firmware VPN workers are idle.

**Что делать:** Дождитесь завершения операции VPN роутера перед новым изменением.

**Action:** Wait for the router VPN operation to finish before requesting another change.

## NATIVE-CONTROLLER-STATE-UNVERIFIED

Выключение контроллера Auto не подтверждено / Auto controller is not confirmed off

**RU:** Сохранённая настройка нативного контроллера не подтверждает выключение, поэтому ручной адаптер не может получить исключительное управление.

**EN:** The saved native controller setting is not explicitly off, so the manual adapter cannot claim exclusive control.

**Что делать:** Остановите Auto и проверьте его свежее состояние перед ручным переключением.

**Action:** Stop Auto and review its fresh status before manual switching.

## SELECTED-RULES-NOT-ADJACENT

Правила выбранных VPN не соседние / Selected VPN rules are not adjacent

**RU:** Правила сохранённых основного и резервного разделены в политике роутера; ограниченный адаптер не может безопасно переставить эту пару.

**EN:** The saved primary and reserve rules are separated in the router policy; the bounded adapter cannot safely reorder this pair.

**Что делать:** Проверьте политику VPN с администратором; не меняйте порядок правил во время активной транзакции.

**Action:** Review the VPN policy with the administrator; do not change rule order while a transaction is active.

## EXISTING-TUNNEL-BINDING-UNVERIFIED

Рабочий VPN не проверен / Working VPN not checked

**RU:** Выбранный туннель отключён, изменяется либо больше не соответствует наблюдавшимся интерфейсу, устройству и маршрутизации.

**EN:** A selected tunnel is down, changing or no longer matches its observed interface, device and routing identity.

**Что делать:** Дождитесь стабильной работы нужных VPN и свежих согласованных проверок.

**Action:** Wait for the intended VPNs to settle and obtain fresh matching checks.

## FW3-SELECTED-ZONE-UNVERIFIED

Зона firewall VPN не проверена / VPN firewall zone is unverified

**RU:** Выбранный интерфейс VPN отсутствует в текущих проверенных зонах firewall.

**EN:** A selected VPN interface is missing from the current verified firewall zones.

**Что делать:** Проверьте привязку зоны firewall VPN перед переключением; сохраните действующие защитные правила.

**Action:** Have the VPN firewall zone binding checked before switching; preserve existing protection rules.

## SHARED-KERNEL-BINDING

Выбранные VPN используют общий ресурс маршрутизации / VPN choices share the same routing resource

**RU:** Два выбранных VPN используют общее устройство, идентичность интерфейса либо метку и таблицу маршрутизации; независимость путей не доказана.

**EN:** The two choices share a device, interface identity or routing mark/table, so independent paths cannot be proved.

**Что делать:** Выберите действительно разные туннели и повторите проверки привязки. Разных названий недостаточно.

**Action:** Choose truly distinct tunnels and repeat the identity checks. Different display names are not sufficient.

## TARGET-ROUTER-PATH-UNVERIFIED

Резерв не прошёл проверки с роутера / Reserve router checks have not passed

**RU:** Для текущего целевого VPN нет свежих согласованных успешных проверок DNS и HTTPS. Это отдельно от подтверждения пути LAN.

**EN:** The current target has no fresh matching successful DNS and HTTPS evidence. This is separate from LAN path confirmation.

**Что делать:** Проверьте доступность резерва и дождитесь свежих измерений роутера; Для режима внешнего LAN нужно отдельное подтверждение клиента; у подготовленного router-probed режима собственные проверки.

**Action:** Check reserve connectivity and wait for fresh router measurements; An external-LAN mode still needs its separate client confirmation; prepared router-probed mode has its own guards.

## MT3000-EVIDENCE-UNVERIFIED

Данные готовности MT3000 неполны / MT3000 readiness evidence is incomplete

**RU:** Собранный снимок готовности несогласован либо не проходит проверку. Он не разрешает ручное переключение.

**EN:** The collected readiness snapshot is inconsistent or cannot be validated. No manual switch is authorized by it.

**Что делать:** Проверьте диагностику и получите свежий полный снимок после стабилизации роутера.

**Action:** Review diagnostics and obtain a fresh complete snapshot after the router is stable.

## MONITOR-ONLY-DEPLOYMENT

Установка ограничена мониторингом / Installation is limited to monitoring

**RU:** Эта установка разрешает только мониторинг. Нативное переключение выключено; результаты мониторинга не подтверждают координацию с прошивкой или путь LAN.

**EN:** This deployment permits monitoring only. Native switching is disabled; monitor results do not certify firmware coordination or the LAN path.

**Что делать:** Продолжайте мониторинг в согласованном объёме. Нативные действия в этой установке остаются недоступны.

**Action:** Continue monitoring within the agreed scope. Native actions remain unavailable in this deployment.

## MONITOR-ONLY-INVALID

Не удалось проверить режим установки / Deployment mode could not be verified

**RU:** Внутренний параметр установки повреждён или не проверен. Нативные действия отклоняются.

**EN:** The internal deployment setting is malformed or unverified. Native actions are refused.

**Что делать:** Проверьте параметры установки по проверенной процедуре установки. Это состояние не означает готовность нативного переключения.

**Action:** Have the deployment settings checked against the verified installation procedure. Do not treat this state as native readiness.

## NATIVE-PROGRESS-UNVERIFIED

Записи состояния контроллера не проверены / Controller progress records are unverified

**RU:** Сохранённым записям хода работы или состояния контроллера нельзя доверять. Новые действия отклоняются; остановка и восстановление по доверенному журналу остаются доступны.

**EN:** Saved native progress or state records cannot be trusted. New controller actions are refused; Stop and recovery from a trusted journal remain available.

**Что делать:** Используйте доступные средства остановки и восстановления. Проверьте диагностику и восстановите записи состояния по описанной процедуре восстановления.

**Action:** Keep the Stop and recovery controls available. Inspect diagnostics and restore progress records through the documented recovery procedure.

## VENDOR-IDENTITY-UNKNOWN

Не удаётся найти этот VPN на роутере / Cannot find this VPN on the router

**RU:** Не удалось однозначно сопоставить профиль с текущим туннелем роутера.

**EN:** The configured profile cannot be matched unambiguously to a current router tunnel.

**Что делать:** Дождитесь свежих наблюдений. Если пара не привязана, выберите активные профили в настройках и сохраните пару.

**Action:** Wait for fresh observations. If the saved pair is unbound, choose active profiles in Settings and save the pair.

## VENDOR-IDENTITY-CHANGED

VPN изменился во время проверки / VPN changed during a check

**RU:** Привязка туннеля изменилась во время измерений; результаты доступности и адреса выхода отброшены.

**EN:** The tunnel binding changed while measurements were running; their health and exit results were discarded.

**Что делать:** Дождитесь новых проверок этого VPN.

**Action:** Wait for new checks of this VPN.

## PROFILE-IDENTITY-CHANGED

VPN-профиль изменился / VPN profile changed

**RU:** Текущий профиль или поколение туннеля не соответствует данным, использованным для решения.

**EN:** The current profile or tunnel generation no longer matches the evidence used for this decision.

**Что делать:** Дождитесь текущих наблюдений; перед запуском Auto может потребоваться новый подтверждённый тест.

**Action:** Wait for current observations; a new verified trial may be needed before Auto can run.

## PAIR-EXTERNAL-POLICY-CHANGE

Правила маршрутов отличаются от сохранённой сессии / Route rules differ from the saved session

**RU:** Порядок или содержимое правил маршрутов VPN больше не совпадает с сохранённой сессией Auto. Кто или что их изменил, не установлено: их может менять и правка в штатной странице VPN, и штатные службы роутера. Простое переименование туннеля не считается.

**EN:** The order or content of the VPN route rules no longer matches the saved Auto session. Who or what changed them is not established: an edit in the stock VPN page and the stock router services can both change them. Renaming a tunnel alone does not count.

**Что делать:** Нажмите Start: Auto сам архивирует старую сессию и примет текущие правила. Если в течение 15 минут отказ повторяется, правила ещё меняются: подождите и повторите.

**Action:** Press Start: Auto archives the old session and adopts the current rules by itself. If it refuses again within 15 minutes, the rules are still changing: wait and try again.

## PAIR-EXTERNAL-NETWORK-CHANGE

Сетевые настройки отличаются от сохранённой сессии / Network settings differ from the saved session

**RU:** Сетевой интерфейс выбранной пары или другой интерфейс изменился после запуска Auto (не остановленный лишний клиент). Сравнение не показывает, кто или что его изменил.

**EN:** A network interface of the selected pair, or another interface, changed after Auto started (not a stopped leftover client). The comparison does not show who or what changed it.

**Что делать:** Нажмите Start: Auto сам примет текущие настройки. Повторные отказы значат, что настройки ещё меняются.

**Action:** Press Start: Auto adopts the current settings by itself. Repeated refusals mean the settings are still changing.

## PAIR-EXTERNAL-CONFIG-CHANGE

Защищённая конфигурация роутера отличается / Protected router configuration differs

**RU:** Защищённая конфигурация (файрвол, DNS, Wi-Fi или профили VPN) отличается от той, которую Auto видел при запуске. Сравнение не показывает, кто или что её изменил: её могут менять и штатные службы роутера.

**EN:** A protected configuration (firewall, DNS, Wi-Fi or the VPN profiles) differs from the one Auto saw when it started. The comparison does not show who or what changed it: the stock router services can change it too.

**Что делать:** Нажмите Start: Auto архивирует старую сессию и сам примет текущую конфигурацию.

**Action:** Press Start: Auto archives the old session and adopts the current configuration by itself.

## PAIR-RECOVERY-REQUIRED

Незавершённое переключение требует восстановления / Unfinished switch needs recovery

**RU:** Предыдущее переключение или сессия Auto не завершились, сейчас их ничто не выполняет, и принять их автоматически нельзя (например роутер удерживается на резерве или автоматический приём уже выполнялся три раза за 15 минут). Журнал и защита сохранены; канал трафика не подтверждён. Это не означает, что вы меняли настройки.

**EN:** An earlier switch or Auto session did not finish, nothing is running it now, and it cannot be taken over automatically (for example the router is held on the reserve, or the automatic takeover already ran three times in 15 minutes). The journal and safety guard are kept; the traffic channel is not verified. This does not mean that you changed any settings.

**Что делать:** Не повторяйте Start и ручное переключение: они отклоняются до завершения восстановления. Если роутер удерживается на резерве, дождитесь восстановления основного. Сохраните журнал; если состояние не меняется, роутеру нужна проверенная процедура восстановления.

**Action:** Do not repeat Start or manual switching: they are refused until recovery completes. If the router is held on the reserve, wait for the primary to recover. Keep the journal; if the state does not change, the router needs its guarded recovery procedure.

## PAIR-READOPTED

Auto заново прочитал изменённые настройки / Auto re-read changed settings

**RU:** Защищённые настройки отличались от сохранённой сессии. Auto архивировал старую сессию, принял текущие настройки и сам запустился заново.

**EN:** Protected settings differed from the saved session. Auto archived the old session, adopted the current settings and started again by itself.

**Что делать:** Делать ничего не нужно. Старая сессия сохранена в папке восстановления роутера.

**Action:** Nothing to do. The old session is kept in the router recovery folder.

## SWITCH-RESULT-UNCONFIRMED

Результат переключения не подтверждён вовремя / Switch result not confirmed in time

**RU:** Страница видела фазу переключения, но роутер не сообщил о его завершении до предельного срока (не более 2 минут и короткая проверка). Канал трафика не подтверждён; страница не показывает успех и не продолжает отсчёт.

**EN:** The page saw a switch phase, but the router did not report its end before the switch deadline (at most 2 minutes plus a short check). The traffic channel is not verified; the page does not show success or keep counting.

**Что делать:** Не повторяйте переключение. Дождитесь следующего состояния роутера; Stop остаётся доступен. Если состояние не меняется, незавершённое переключение требует восстановления.

**Action:** Do not repeat the switch. Wait for the next router state; Stop remains available. If it stays like this, the unfinished switch needs recovery.

## VENDOR-REASON-UNOBSERVED

Выбор сервера прошивкой не виден / Firmware server choice is not visible

**RU:** Штатная прошивка сама выбирает сервер внутри канала и не сообщает, почему и сколько раз пыталась. Приложение проверяет только, работает ли канал сейчас.

**EN:** The stock firmware chooses the server inside a channel and does not report why or how many times it tried. The app checks only whether the channel works now.

**Что делать:** Делать ничего не нужно. Чтобы выбрать другой сервер, откройте «Каналы и серверы».

**Action:** Nothing to do. To pick a different server use Channels and servers.

## AUTOMATIC-EXTERNAL-CHANGE-READOPT

Старая сессия Auto архивирована автоматически / Old Auto session archived automatically

**RU:** Запись в архивной сессии Auto: защищённые настройки отличались от неё, и Auto сам принял текущие настройки.

**EN:** Recorded in the archived Auto session when protected settings differed from it and Auto adopted the current settings by itself.

**Что делать:** Делать ничего не нужно. Архивная копия остаётся в папке восстановления роутера.

**Action:** Nothing to do. The archived copy stays in the router recovery folder.

## STATUS-REQUEST-FAILED

Нет ответа от программы на роутере / No answer from the router program

**RU:** Страница запросила у роутера текущее состояние и не получила ответа (тайм-аут, роутер занят или ошибка страницы). Пока ответа нет, ничего не показывается как рабочее.

**EN:** The page asked the router for the current state and got no answer (timeout, a busy router or a page error). Nothing is shown as working until it answers.

**Что делать:** Подождите несколько секунд и обновите страницу (Ctrl+F5). Если повторяется, откройте «Настройки» и проверьте, что мониторинг запущен.

**Action:** Wait a few seconds; reload the page with Ctrl+F5. If it repeats, open Settings and check that monitoring is running.

## MONITOR-DATA-STALE

Данные роутера устарели / Router data is old

**RU:** Программа роутера ответила, но её последнее измерение старше 90 секунд, поэтому оно не описывает каналы сейчас.

**EN:** The router program answered, but its last measurement is older than 90 seconds, so it cannot describe the channels now.

**Что делать:** Проверьте, что мониторинг запущен («Настройки»). Тест скорости приостанавливает измерения до минуты.

**Action:** Check that monitoring is running (Settings). A speed test pauses measurements for up to a minute.

## VENDOR-OBSERVATION-PENDING

Канал ещё не наблюдался / Channel not observed yet

**RU:** Мониторинг собирает первые наблюдения этого канала после запуска или изменения настроек.

**EN:** Monitoring is collecting the first observations of this channel after a start or a settings change.

**Что делать:** Подождите до минуты; результат появится сам.

**Action:** Wait up to a minute; the result appears by itself.

## AUTO-CONTROL-UNCONFIRMED

Auto не подтвердил команду / Auto did not confirm the command

**RU:** Страница отправила «Старт» или «Стоп», но роутер не сообщил результат за две минуты. Кнопка снова доступна, можно повторить.

**EN:** The page sent Start or Stop, but the router did not report the result within two minutes. The button is released so you can try again.

**Что делать:** Посмотрите на лампу Auto и состояние через минуту. Если ничего не изменилось, нажмите кнопку ещё раз; если повторяется, проверьте, что мониторинг запущен («Настройки»).

**Action:** Check the Auto lamp and the status in a minute. If nothing changed, press the button again; if it repeats, check that monitoring is running (Settings).

## UI-ACTION-FAILED

Страница не смогла выполнить действие / The page could not finish the action

**RU:** Страница отправила запрос, но он не прошёл до ответа роутера (связь пропала или ошибка страницы). Это нажатие ничего не изменило.

**EN:** The page sent a request, but it failed before the router answered (connection lost or a page error). Nothing was changed by this press.

**Что делать:** Обновите страницу (Ctrl+F5) и повторите действие.

**Action:** Reload the page (Ctrl+F5) and repeat the action.

## UI-RENDER-FAILED

Часть страницы не удалось показать / Part of the page could not be drawn

**RU:** Роутер ответил, но одна часть страницы не отрисовалась; остальная страница работает.

**EN:** The router answered, but one part of the page failed while drawing; the rest of the page keeps working.

**Что делать:** Обновите страницу (Ctrl+F5). Если повторяется, отправьте код и снимок экрана разработчику.

**Action:** Reload the page (Ctrl+F5). If it repeats, send the code and a screenshot to the developer.

## MANUAL-SWITCH-UNCONFIRMED

Ручное переключение не подтверждено / Manual switch not confirmed

**RU:** Роутер не подтвердил ручное переключение и не назвал другой причины. Маршрут остаётся таким, как сообщает роутер.

**EN:** The router did not confirm the manual switch and gave no other reason. The route stays as the router reports it.

**Что делать:** Дождитесь следующей проверки роутера (около 10 секунд) и при необходимости нажмите канал ещё раз.

**Action:** Wait for the next router check (about 10 seconds) and press the channel again if needed.

## STATS-RESET-ARCHIVE-UNVERIFIED

Архив не прочитался обратно / Archive could not be read back

**RU:** Роутер записал архив старых данных, но проверка чтением не совпала, поэтому ничего не сброшено.

**EN:** The router wrote the archive of the old data, but reading it back did not match, so it reset nothing.

**Что делать:** Проверьте свободное место на роутере и снова нажмите «Сброс графика».

**Action:** Check free space on the router and press Reset chart again.

## STATS-RESET-FIELDS

Запрос сброса не принят / Reset request not accepted

**RU:** Страница попросила сбросить график, который роутер не знает. Ничего не сброшено.

**EN:** The page asked to reset a chart the router does not know. Nothing was reset.

**Что делать:** Обновите страницу (Ctrl+F5) и снова нажмите «Сброс графика».

**Action:** Reload the page (Ctrl+F5) and press Reset chart again.

## STATS-RESET-FAILED

Сброс не выполнен / Reset not completed

**RU:** Роутер не смог сохранить архив старых данных и поэтому оставил данные без изменений.

**EN:** The router could not save the archive of the old data, so it kept the data unchanged.

**Что делать:** Проверьте свободное место на роутере (System → Software или df -h) и повторите.

**Action:** Check free space on the router (System → Software or df -h) and try again.

## STATS-RESET-ARCHIVE-PATH

Папка архива небезопасна / Archive folder is not safe

**RU:** Папка архива на роутере является ссылкой, а не папкой, поэтому сброс отклонён.

**EN:** The archive folder on the router is a link, not a folder, so the reset was refused.

**Что делать:** Удалите /etc/homensai-vpn/stats-archive на роутере и повторите.

**Action:** Remove /etc/homensai-vpn/stats-archive on the router and try again.

## STATS-RESET-UNCONFIRMED

Сброс не подтверждён вовремя / Reset not confirmed in time

**RU:** Роутер принял запрос, но мониторинг не сообщил результат за 45 секунд (он может быть остановлен или на паузе из-за теста скорости).

**EN:** The router accepted the request but its monitoring did not report the result within 45 seconds (it may be stopped or paused by a speed test).

**Что делать:** Проверьте, что мониторинг запущен («Настройки»), подождите минуту и посмотрите на график; при необходимости нажмите «Сброс» ещё раз.

**Action:** Check that monitoring is running (Settings), wait a minute and look at the chart; press Reset again if needed.

## RESERVE-ALREADY-FIRST

Резерв уже стоит первым у роутера / The reserve is already the router first choice

**RU:** Основной канал не работает, но в списке приоритетов VPN роутера резерв уже стоит первым, поэтому трафик уже идёт через резерв. Auto продолжает наблюдение и ничего не переключает.

**EN:** The primary fails, but the router VPN priority list already puts the reserve first, so traffic already goes through the reserve. Auto keeps watching and does not switch.

**Что делать:** Делать ничего не нужно. Если хотите снова поставить основной первым, когда он заработает, переместите его на Priority 1 в VPN Dashboard роутера.

**Action:** Nothing to do. If you want the primary first again, move it to Priority 1 in the router VPN Dashboard when it works.

## CHANNEL-UNRELIABLE

Проблема с надёжностью канала / Channel reliability problem

**RU:** За последние 5 минут собственные проверки роутера через этот канал не прошли минимум в 20% циклов (цикл не пройден, если не работает DNS или проходит меньше двух из трёх HTTPS-проверок). Туннель при этом может быть «подключён». Это измеренная доля непройденных проверок, а не ICMP-потеря пакетов; настройки она не меняет.

**EN:** Over the last 5 minutes the router's own checks through this channel failed in at least 20% of the cycles (a cycle fails when DNS fails or fewer than two of three HTTPS checks pass). The tunnel can still show as connected. This is a measured share of failed checks, not an ICMP packet-loss figure, and it changes no setting.

**Что делать:** Следуйте рекомендации: держите трафик на канале с меньшими потерями и замените сервер ненадёжного в «Каналы и серверы»; если теряют оба, сначала проверьте подключение роутера. Запустите тест скорости, чтобы измерить другие серверы.

**Action:** Follow the recommendation: keep traffic on the channel with the lower loss and replace the server of the unreliable one in Channels and servers; if both lose checks, test the router uplink first. Run a speed test to measure other servers.

## RESERVE-NOT-CONNECTED

Резервный канал не подключён / Reserve channel is not connected

**RU:** Резервный клиент включён, но роутер не видит работающего туннеля. Auto не может на него переключиться, основной канал продолжает работать.

**EN:** The reserve client is enabled but the router reports no running tunnel. Auto cannot switch to it, and the primary keeps carrying traffic.

**Что делать:** Auto сам запускает остановленный включённый резерв: не чаще раза в две минуты и четырёх раз за 15 минут. Если он не подключается, проверьте сервер резерва на странице VPN роутера или выберите другой сервер резерва в «Каналы и серверы».

**Action:** Auto starts a stopped enabled reserve itself, at most once per two minutes and four times per 15 minutes. If it still does not connect, check the reserve server in the router VPN page or choose another reserve server in Channels and servers.

## VENDOR-SAME-TUNNEL

Сервер выбирает штатная прошивка / Server selection belongs to the router

**RU:** Оба выбора относятся к одному наблюдаемому туннелю. Приложение не запускает конкурирующий перебор серверов.

**EN:** Both choices refer to one observed tunnel. The application does not run a competing server switch loop.

**Что делать:** Для резервирования приложением выберите другой туннель.

**Action:** Choose a different tunnel for application reserve switching.

## SETUP-SAME-TUNNEL

Выберите два разных туннеля / Choose two different tunnels

**RU:** Выбранные основной и резервный профили привязаны к одному туннелю роутера.

**EN:** The selected primary and reserve resolve to the same router tunnel.

**Что делать:** Выберите активный профиль другого туннеля либо отложите пару.

**Action:** Select an active profile on another tunnel, or defer the pair.

## VENDOR-SETTLING

Роутер ещё проверяет настройки VPN / The router is still checking VPN settings

**RU:** Окно наблюдения за идентичностью ещё не завершено. Это не показывает, исчерпала ли прошивка попытки подключения серверов.

**EN:** The identity observation window has not finished. This does not reveal whether the firmware exhausted its server attempts.

**Что делать:** Дождитесь повторных свежих наблюдений.

**Action:** Wait for repeated fresh observations.

## CROSS-TUNNEL-READY

Эта пара VPN подходит для Auto / This VPN pair is suitable for Auto

**RU:** Текущие привязки туннелей подходят для планирования без применения; изменение маршрутов требует отдельных проверок.

**EN:** The current configured tunnel identities are eligible for read-only planning; route changes remain separately guarded.

**Что делать:** Это согласованное наблюдение туннелей, а не разрешение переключать или сертификат LAN. Используйте действующую готовность контроллера выбранного режима.

**Action:** This is consistent tunnel observation, not switching permission or LAN certification. Use the actual controller readiness for the chosen proof mode.

## CURRENT-PROFILE-FAILURE-STREAK

Текущий профиль не прошёл несколько проверок / Current profile failed repeated checks

**RU:** У текущего привязанного профиля накопилась заданная серия неудачных проверок. Это не доказывает отказ всех серверов его туннеля.

**EN:** The current bound profile has the configured failure streak. This does not prove that all servers in its tunnel have failed.

**Что делать:** Проверьте наблюдения туннеля и данные о резерве.

**Action:** Review tunnel observations and reserve evidence.

## RESERVE-IDENTITY-UNKNOWN

Не удаётся найти этот VPN на роутере / Cannot find this VPN on the router

**RU:** Контроллер не может безопасно отнести старые проверки резерва к текущему профилю туннеля.

**EN:** The controller cannot safely attach old reserve health to its current tunnel member.

**Что делать:** Используйте доступные средства восстановления и дождитесь свежих наблюдений перед новым переключением.

**Action:** Keep the recovery controls available and obtain fresh observations before a new forward action.

## VENDOR-FIRST-OBSERVATION

VPN замечен впервые / VPN seen for the first time

**RU:** Монитор впервые увидел этот профиль в конфигурации туннеля. Причина выбора не предполагается.

**EN:** The monitor first observed this configured tunnel member. No switch cause is inferred.

**Что делать:** Действий не требуется; дождитесь свежих проверок.

**Action:** No action is required; wait for fresh checks.

## VENDOR-PROFILE-CHANGED

Профиль в конфигурации туннеля изменился / Configured tunnel member changed

**RU:** В том же туннеле наблюдался другой профиль конфигурации. Причина и фактический результат для LAN не установлены.

**EN:** A different configured profile was observed on the same tunnel. The cause and actual LAN outcome remain unobserved.

**Что делать:** Посмотрите проверки текущего профиля.

**Action:** Inspect the current profile checks.

## VENDOR-BINDING-CHANGED

Настройки VPN изменились / VPN settings changed

**RU:** Монитор увидел новое поколение привязки; старые проверки не подтверждают его готовность.

**EN:** The monitor observed a new binding generation; earlier health cannot make it ready.

**Что делать:** Дождитесь проверок с новыми настройками.

**Action:** Wait for checks with the new settings.

## VENDOR-BINDING-UNKNOWN

VPN-профиль изменён или удалён на роутере / VPN profile changed or removed on the router

**RU:** Предыдущий профиль конфигурации туннеля больше не определяется однозначно.

**EN:** The previous configured tunnel member can no longer be identified unambiguously.

**Что делать:** Проверьте текущую конфигурацию роутера и свежие наблюдения.

**Action:** Inspect current router configuration and fresh observations.

## VENDOR-OBSERVATION-TIME

Некорректное время наблюдения / Invalid observation clock

**RU:** Время проверки неверно, поэтому неизвестно, какой VPN работает.

**EN:** The check time is invalid, so it is unknown which VPN is in use.

**Что делать:** Проверьте часы роутера и дождитесь нового наблюдения.

**Action:** Check the router clock and retry observation.

## ONBOARDING-FIELDS

Форма настройки изменилась / Setup form changed

**RU:** В запросе общей настройки отсутствуют разделы или есть лишние.

**EN:** The complete setup request has missing or unexpected sections.

**Что делать:** Обновите приложение и снова проверьте общую настройку.

**Action:** Reload the application and review the complete setup again.

## ONBOARDING-SYSTEM-FIELDS

Проверьте настройку VPN / Check VPN setup

**RU:** Поля настройки VPN не соответствуют поддерживаемой форме.

**EN:** The VPN setup fields do not match the supported form.

**Что делать:** Обновите страницу и выберите существующие профили либо явно отложите пару.

**Action:** Reload and choose existing profiles or explicitly defer the pair.

## ONBOARDING-PAIR-DEFERRED

Проверьте отложенную пару VPN / Review deferred VPN pair

**RU:** При отложенной паре VPN планирование должно быть выключено.

**EN:** A deferred VPN pair must have read-only planning switched off.

**Что делать:** Вернитесь к шагу VPN и выберите откладывание пары либо два разных существующих профиля.

**Action:** Go Back to the VPN step and choose the defer option, or choose two different existing profiles.

## ONBOARDING-APPEARANCE

Проверьте оформление по умолчанию / Check appearance defaults

**RU:** Выбран неподдерживаемый язык, тема или оформление по умолчанию.

**EN:** The saved default language, theme or design is unsupported.

**Что делать:** Выберите значение в каждом списке на первом шаге.

**Action:** Choose a value from each list in the first step.

## ONBOARDING-TELEGRAM-FIELDS

Проверьте необязательную настройку Telegram / Check optional Telegram setup

**RU:** Раздел Telegram не соответствует поддерживаемой форме.

**EN:** The Telegram section does not match the supported form.

**Что делать:** Оставьте существующие настройки либо включите раздел настройки Telegram и проверьте его поля.

**Action:** Keep existing settings, or enable the Telegram setup section and review its fields.

## ONBOARDING-TOO-LARGE

Запрос настройки слишком большой / Setup request is too large

**RU:** Полная конфигурация превышает допустимый размер запроса сохранения. Запрос не передан записи настроек.

**EN:** The complete configuration exceeds the bounded save request size. Nothing was sent to the configuration writer.

**Что делать:** Сократите названия серверов и групп каналов и проверьте снова.

**Action:** Shorten display names and channel groups, then review again.

## ONBOARDING-SAVE-UNCONFIRMED

Сохранение настройки не подтверждено / Setup save not confirmed

**RU:** Роутер не подтвердил общее сохранение. Страница сохраняет черновик; параметры уже могли записаться на роутере.

**EN:** The router did not confirm the complete setup save. The page keeps your draft; the router may already have committed the settings.

**Что делать:** Обновите страницу, чтобы прочитать состояние роутера перед повтором.

**Action:** Reload to read the router state before trying again.

## CONTROL-REVISION-STALE

Управление Auto изменилось / Auto controls changed

**RU:** Запрос запуска относится к прежнему состоянию управления Auto и отклонён.

**EN:** The Start request belongs to older Auto controls and was refused.

**Что делать:** Обновите данные перед новым запуском.

**Action:** Refresh the current state before starting again.

## START-STATE-UNVERIFIED

Состояние Auto не проверено / Saved Auto state unverified

**RU:** Не удалось проверить сохранённое состояние Auto. Запуск заблокирован.

**EN:** Saved Auto state could not be verified. Starting is blocked.

**Что делать:** Остановите Auto, проверьте настройки и повторите попытку.

**Action:** Stop Auto, review the settings, then try again.

## STOP-SUPERSEDED-START

Ожидающий запуск отменён / Pending Start cancelled

**RU:** Остановка отменила ожидающий запуск.

**EN:** Stop cancelled this pending Start.

**Что делать:** При необходимости нажмите «Запустить» снова.

**Action:** Press Start again when ready.

## START-CONFIG-CHANGED

Настройки изменились при запуске / Settings changed during Start

**RU:** Настройки изменились во время проверки запуска. Запрос отклонён.

**EN:** The settings changed while Start was checking them. The request was refused.

**Что делать:** Проверьте настройки и повторите запуск.

**Action:** Review the settings and try Start again.

## GUARD-RELEASE-ARM-FAILED

Аварийный таймер недоступен / Safety timer unavailable

**RU:** Независимый таймер очистки не запустился. Новая блокировка трафика не установлена.

**EN:** The independent cleanup timer could not start. No new traffic block was installed.

**Что делать:** Проверьте ресурсы роутера и повторите позже.

**Action:** Check router resources and retry later.

## GUARD-RELEASE-UNCONFIRMED

Снятие блокировки не подтверждено / Safety block removal unconfirmed

**RU:** Снятие блокировки трафика не подтверждено; восстановление ещё не завершено.

**EN:** Removal of the traffic block is unverified; recovery remains pending.

**Что делать:** См. «Помощь» → аварийный возврат; остановка ещё не подтверждена.

**Action:** See Help → emergency return; do not assume Stop completed.

## RELEASE-PENDING

Ожидается снятие блокировки / Waiting for block removal

**RU:** Новые переключения запрещены, пока снимается прежняя блокировка.

**EN:** No new switching is allowed while the old block is being removed.

**Что делать:** Проверьте очистку; при повторении используйте аварийное восстановление.

**Action:** Check cleanup; use emergency recovery if it persists.

## RETURN-TRANSACTION-MISMATCH

Старый запрос возврата отклонён / Old return request rejected

**RU:** Запрос относится к другой транзакции. Ничего не изменено.

**EN:** The request belongs to another transaction. Nothing changed.

**Что делать:** Обновите страницу и при необходимости запросите возврат ещё раз.

**Action:** Refresh and request return again if needed.

## RETURN-REQUEST-EXPIRED

Запрос возврата устарел / Return request expired

**RU:** Запрос находится вне транзакции или минутного срока действия.

**EN:** The request is outside the transaction or its one-minute validity window.

**Что делать:** Обновите страницу и запросите возврат ещё раз.

**Action:** Refresh and request return again.

## JOURNAL-PHASE-INVALID

Неверная фаза восстановления / Invalid recovery phase

**RU:** Фаза журнала отсутствует или неизвестна. Auto не продолжает работу.

**EN:** The journal phase is missing or unknown. Auto refuses to proceed.

**Что делать:** Используйте «Помощь» → аварийный возврат; проверьте восстановление до перезапуска.

**Action:** Use Help → emergency return; inspect recovery before restarting.

## OBSERVING

Слежу за основным / Watching the primary

**RU:** Auto включён и следит за основным VPN. Сейчас ничего не переключается.

**EN:** Auto is on and watches the primary VPN. Nothing is switched now.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

**Пример / Example:** Если в строке OBSERVING и лампа Auto зелёная — всё в порядке. / If the line says OBSERVING and the Auto lamp is green, everything is normal.

## ARMED

Готов к переключению / Ready to switch

**RU:** Контроллер подготовил переключение (сохранил прежний порядок и запустил страхующий таймер), но пока ничего не менял.

**EN:** The controller has prepared a switch (saved the old order and started its safety timer) but has not changed anything yet.

**Что делать:** Делать ничего не нужно; следующее состояние наступит через секунды.

**Action:** Nothing to do; the next state follows within seconds.

**Пример / Example:** В инциденте: ARMED → APPLYING → WAIT-CLIENT → COMMITTED — обычное успешное переключение. / In an incident: ARMED → APPLYING → WAIT-CLIENT → COMMITTED is a normal successful switch.

## APPLYING

Идёт переключение / Switching now

**RU:** Контроллер прямо сейчас меняет порядок VPN-правил на роутере.

**EN:** The controller is changing the order of the VPN rules on the router right now.

**Что делать:** Подождите. Если состояние держится больше минуты, нажмите «Стоп» в блоке Auto.

**Action:** Wait. If it stays here for more than a minute, press Stop in the Auto card.

**Пример / Example:** Видите APPLYING, затем ROLLED-BACK с VENDOR-APPLY-FAILED: GL.iNet не принял изменение, роутер вернулся назад. / You see APPLYING, then ROLLED-BACK with VENDOR-APPLY-FAILED: GL.iNet did not accept the change and the router went back.

## WAIT-CLIENT

Ждём ваш компьютер / Waiting for your computer

**RU:** Маршрут переключён, контроллер до 2 минут ждёт, пока LAN-помощник на вашем компьютере подтвердит, что интернет работает.

**EN:** The route is switched and the controller waits up to 2 minutes for the LAN helper on your computer to confirm that the internet works.

**Что делать:** Ожидайте данные своего режима доказательства. Внешний LAN использует помощник, router-probed — внутренние проверки. При таймауте проверьте фактическое восстановление, а не только запрос.

**Action:** Wait for the evidence required by this proof mode. External LAN uses its helper; router-probed mode has internal checks. On timeout verify the actual recovery, not merely the request.

**Пример / Example:** За WAIT-CLIENT следует ROLLED-BACK и CLIENT-CONFIRMATION-TIMEOUT: вовремя никто не подтвердил. / WAIT-CLIENT followed by ROLLED-BACK and CLIENT-CONFIRMATION-TIMEOUT: nobody confirmed in time.

## COMMITTED

Резерв подтверждён / Reserve confirmed

**RU:** Переключение удалось и ваш компьютер его подтвердил: трафик идёт через резервный VPN.

**EN:** The switch worked and your computer confirmed it: traffic goes through the reserve VPN.

**Что делать:** Делать ничего не нужно. Auto вернётся на основной сам, когда он восстановится, либо нажмите «Вернуться на основной».

**Action:** Nothing to do. Auto returns to the primary by itself when it has recovered, or press “Return to primary”.

**Пример / Example:** На «Обзоре» «Работаю на резерве», состояние COMMITTED — норма после отказа основного. / The overview says “Working on the reserve” and the state is COMMITTED: normal after a failure of the primary.

## ROLLED-BACK

Возврат на прежний маршрут / Returned to the previous route

**RU:** Контроллер вернул VPN-правила в исходный порядок. Причина указана рядом.

**EN:** The controller put the VPN rules back to the original order. The reason is in the next column or in the code beside it.

**Что делать:** Прочитайте код причины рядом: он говорит, почему переключение не осталось.

**Action:** Read the reason code beside it; it tells why the switch did not stay.

**Пример / Example:** ROLLED-BACK + TRIAL-ENDED: окно теста закончилось и роутер вернулся на основной. Это норма. / ROLLED-BACK + TRIAL-ENDED: the test window ended and the router returned to the primary. That is normal.

## ROLLING-BACK

Возвращаюсь / Returning now

**RU:** Контроллер прямо сейчас возвращает исходный порядок.

**EN:** The controller is putting the original order back right now.

**Что делать:** Подождите минуту.

**Action:** Wait a minute.

## RESTORING

Восстанавливаю маршрут / Restoring the route

**RU:** То же, что возврат: исходный маршрут восстанавливается и проверяется.

**EN:** Same as returning: the original route is being restored and verified.

**Что делать:** Подождите минуту; если не заканчивается, см. «Помощь» → «Нет интернета».

**Action:** Wait a minute; if it does not end, see Help → “No internet”.

## TRIAL-REQUIRED

Нужен LAN-тест / LAN trial needed

**RU:** Auto пока не может переключать: для текущих настроек не пройден LAN-тест.

**EN:** Auto may not switch yet: no LAN trial has passed for the current settings.

**Что делать:** Для клиентского пути выполните его отдельно разрешённый соответствующий тест. Подготовленный непрерывный режим использует свою готовность; не подделывайте и не переносите сертификат другой пары.

**Action:** For the client-confirmed path run its separately authorized matching trial. Prepared continuous mode uses its own readiness; do not forge or reuse another pair certificate.

**Пример / Example:** После смены основного или резервного это состояние появляется снова: прежний тест относился к прежней паре. / After you change the primary or reserve, this state appears again: the old trial belongs to the old pair.

## BLOCKED

Заблокировано / Blocked

**RU:** Контроллер отказывается действовать, потому что не выполнено условие безопасности; условия перечислены рядом кодами.

**EN:** The controller refuses to act because a safety condition is not met; the conditions are listed next to it as codes.

**Что делать:** Откройте каждый код рядом и устраните перечисленное условие.

**Action:** Open each code beside it and fix the listed condition.

**Пример / Example:** BLOCKED с HARDWARE-ACCELERATOR-UNVERIFIED: аппаратное ускорение GL.iNet не подтверждено как выключенное. / BLOCKED with HARDWARE-ACCELERATOR-UNVERIFIED: GL.iNet hardware acceleration is not proven off.

## STOPPED

Остановлен / Stopped

**RU:** Auto выключен, контроллер ничего не делает.

**EN:** Auto is off and the controller does nothing.

**Что делать:** Включите Auto, когда нужно.

**Action:** Turn Auto on when you want it.

## STOPPED-ON-RESERVE

Остановлен на резерве / Stopped on the reserve

**RU:** Auto остановлен, пока трафик шёл через резерв. Исходный маршрут пока не восстановлен.

**EN:** Auto was stopped while traffic was on the reserve. The original route is not restored yet.

**Что делать:** Когда основной снова работает, нажмите «Вернуться на основной» в блоке Auto.

**Action:** When the primary works again press “Return to primary” in the Auto card.

## DEGRADED-ON-RESERVE

Резерв тоже не работает / Reserve is failing too

**RU:** Трафик идёт через резерв, и резерв тоже не проходит проверки.

**EN:** Traffic is on the reserve and the reserve fails its checks as well.

**Что делать:** Проверьте оба VPN-профиля в GL.iNet. Auto вернётся на основной, когда он пройдёт проверку.

**Action:** Check both VPN profiles in GL.iNet. Auto returns to the primary when it passes its check.

## HELD-ON-RESERVE

Остаюсь на резерве; Auto продолжает наблюдать / Staying on the reserve; Auto keeps watching

**RU:** Трафик намеренно остаётся на резерве (по вашему правилу возврата или ручному выбору), пока резерв работает. Auto остаётся включённым: если резерв откажет, он сам переведёт трафик на другой канал.

**EN:** Traffic stays on the reserve on purpose (your return rule or your manual choice) while the reserve works. Auto is still on: if the reserve fails, it moves traffic to the other channel by itself.

**Что делать:** Делать ничего не нужно. Если хотите вернуть трафик на основной, нажмите «Вернуться на основной».

**Action:** Nothing to do. If you want traffic back on the primary, press “Return to primary”.

## DISABLED

Auto выключен / Auto disabled

**RU:** Auto выключен в настройках.

**EN:** Auto is switched off in the settings.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## EXPIRED

Окно теста закончилось / Test window ended

**RU:** Окно времени текущего теста закончилось; вне его Auto не действует.

**EN:** The time window of the current trial is over; Auto does not act outside it.

**Что делать:** Ограниченное окно завершилось. Сначала проверьте Stop/восстановление; новому запуску нужны текущая готовность и выбранный режим, а не сброс старых сроков/бюджетов.

**Action:** The bounded window ended. Verify Stop/recovery first; any new run requires current readiness and the requested mode, not a reset of old deadlines or budgets.

## SERVICE-STOPPED

Служба мониторинга не работает / Monitor service is not running

**RU:** Страница не находит работающий мониторинг на роутере.

**EN:** The page cannot find a running monitor on the router.

**Что делать:** Нажмите «Запустить мониторинг» в блоке «Мониторинг» или выполните homensai-vpn-emergency start по SSH.

**Action:** Press “Start monitoring” in the Monitoring block, or run homensai-vpn-emergency start over SSH.

## WAIT-CONFIRM

Ожидание подтверждения / Waiting for confirmation

**RU:** Ожидается подтверждение нового маршрута с компьютера.

**EN:** Waiting for the computer to confirm the new route.

**Что делать:** См. WAIT-CLIENT.

**Action:** See WAIT-CLIENT.

## CLIENT-CONFIRMED

Компьютер подтвердил / Your computer confirmed

**RU:** LAN-помощник на вашем компьютере подтвердил, что DNS, HTTPS и внешний адрес после переключения верны.

**EN:** The LAN helper on your computer confirmed that DNS, HTTPS and the exit address are right after the switch.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## TRIAL-PASSED

Тест пройден / Trial passed

**RU:** LAN-тест удался: переключение подтверждено и роутер вернулся на основной.

**EN:** The LAN trial worked: the switch was confirmed and the router returned to the primary.

**Что делать:** Теперь можно включить Auto.

**Action:** Now you can turn Auto on.

## TRIAL-ENDED

Окно теста закончилось / Test window ended

**RU:** Окно времени теста закончилось, роутер вернулся на основной.

**EN:** The time window of the trial ended and the router returned to the primary.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SOURCE-FAILED

Основной отказал / The primary failed

**RU:** Основной VPN не прошёл заданное число проверок подряд.

**EN:** The primary VPN failed the configured number of checks in a row.

**Что делать:** Проверьте профиль основного VPN в GL.iNet.

**Action:** Check the primary VPN profile in GL.iNet.

## SOURCE-HEALTH-UNKNOWN

Состояние основного неизвестно / Primary state unknown

**RU:** Не хватило свежих данных об основном.

**EN:** There was not enough fresh data about the primary.

**Что делать:** Дождитесь следующих проверок; посмотрите на лампу мониторинга.

**Action:** Wait for the next checks; check the monitor lamp.

## OPERATOR-TRIAL

Запущено вами / Started by you

**RU:** Переключение было тестом, который вы запустили LAN-помощником.

**EN:** The switch was a trial that you started with the LAN helper.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## OPERATOR-HOLD-RESERVE

Удержание по вашему правилу / Held by your rule

**RU:** Ваше правило восстановления говорит оставаться на резерве, пока вы не вернётесь вручную.

**EN:** Your recovery rule says to stay on the reserve until you return manually.

**Что делать:** Нажмите «Вернуться на основной», когда захотите вернуться.

**Action:** Press “Return to primary” when you want to go back.

## PRIMARY-STABLY-RECOVERED

Основной стабильно восстановился / Primary recovered for good

**RU:** Основной прошёл достаточно проверок подряд, и трафик вернулся на него.

**EN:** The primary passed enough checks in a row and traffic returned to it.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## RESERVE-FAILED

Резерв отказал / The reserve failed

**RU:** Резервный VPN не прошёл проверки, пока трафик шёл через него.

**EN:** The reserve VPN failed its checks while traffic was on it.

**Что делать:** Проверьте оба VPN-профиля в GL.iNet.

**Action:** Check both VPN profiles in GL.iNet.

## RESERVE-FAILED-PRIMARY-VERIFIED

Резерв отказал, основной исправен / Reserve failed, primary is fine

**RU:** Резерв отказал, основной проверен, поэтому трафик вернулся на основной.

**EN:** The reserve failed and the primary was verified, so traffic returned to the primary.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## RESERVE-HEALTH-UNKNOWN

Состояние резерва неизвестно / Reserve state unknown

**RU:** Живая проверка резерва не дала ясного ответа.

**EN:** The live check of the reserve gave no clear answer.

**Что делать:** Подождите; посмотрите резерв в «Каналах и серверах».

**Action:** Wait; check the reserve in Channels and servers.

## SOURCE-NOT-VERIFIED

Основной не проверен / Primary not verified

**RU:** Роутер остаётся на резерве, потому что основной не прошёл свежую проверку.

**EN:** The router stays on the reserve because the primary has not passed a fresh check.

**Что делать:** Проверьте основной VPN; затем нажмите «Вернуться на основной».

**Action:** Check the primary VPN; then press “Return to primary”.

## SUPERVISOR-RECOVERY

Восстановление после перезапуска / Recovery after a restart

**RU:** Контроллер перезапустился посреди переключения и вернул маршрут.

**EN:** The controller restarted in the middle of a switch and put the route back.

**Что делать:** Делать ничего не нужно, если не повторяется.

**Action:** Nothing to do unless it repeats.

## TRANSACTION-FAILED

Переключение не удалось / The switch failed

**RU:** Что-то пошло не так во время переключения; роутер вернулся на прежний маршрут.

**EN:** Something went wrong during the switch; the router returned to the previous route.

**Что делать:** Посмотрите на код рядом: там причина.

**Action:** Look at the code beside it for the cause.

## FAILED-BEFORE-APPLY

Сбой до изменений / Failed before any change

**RU:** Переключение не удалось до каких-либо изменений на роутере.

**EN:** The switch failed before anything was changed on the router.

**Что делать:** Ничего не менялось; посмотрите на код рядом.

**Action:** Nothing was changed; look at the code beside it.

## TIMEOUT-ELAPSED

Время вышло / Time ran out

**RU:** Отведённое на шаг время закончилось.

**EN:** The allowed time for the step ended.

**Что делать:** Повторите позже; если повторяется, проверьте мониторинг.

**Action:** Repeat later; if it repeats, check the monitor.

## SELECTED-BY-CONTROLLER

Выбран контроллером / Chosen by the controller

**RU:** Этот сервер сейчас пропускает ваш трафик.

**EN:** This server carries your traffic now.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## EDGE-NOT-CERTIFIED

Работает, переключение не подтверждено / Works, switch not certified

**RU:** Сервер работает и мог бы подхватить трафик, но переключение на него на этом роутере ещё не подтверждено.

**EN:** The server works and could take over, but switching to it is not certified on this router yet.

**Что делать:** Предлагаемому переходу не хватает доказательства своего режима. Кандидат чтения не является применённым маршрутом; используйте соответствующий контроллер/тест, не принудительное общее подтверждение LAN.

**Action:** The proposed edge lacks evidence for its mode. A read-only candidate is not an applied route; use the matching controller/test workflow, not a generic forced LAN confirmation.

## THREE-CONFIRMED-FAILURES

Три сбоя подряд / Three failures in a row

**RU:** Основной не прошёл три проверки подряд.

**EN:** The primary failed three checks in a row.

**Что делать:** Проверьте основной VPN.

**Action:** Check the primary VPN.

## CONFIGURED-FAILURE-STREAK

Достигнут порог сбоев / Failure streak reached

**RU:** Основной не прошёл столько проверок подряд, сколько требуют ваши правила восстановления.

**EN:** The primary failed as many checks in a row as your recovery rules require.

**Что делать:** Проверьте основной VPN.

**Action:** Check the primary VPN.

## RESTORE-PRIMARY

Возврат на основной / Return to the primary

**RU:** Контроллер решил вернуться на основной.

**EN:** The controller decided to go back to the primary.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SWITCH-RECOMMENDED

Рекомендуется переключение / A switch is recommended

**RU:** Прогноз говорит, что сейчас было бы выбрано переключение. Прогноз ничего не меняет.

**EN:** The forecast says a switch would be chosen now. The forecast changes nothing.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## TARGET-INACTIVE

Резерв не подключён / Reserve not connected

**RU:** Резервный VPN не подключён в GL.iNet; Auto сам его не подключает.

**EN:** The reserve VPN is not connected in GL.iNet; Auto never connects it for you.

**Что делать:** Подключите профиль резерва в VPN Dashboard GL.iNet.

**Action:** Connect the reserve profile in the GL.iNet VPN Dashboard.

## TARGET-NOT-READY

Резерв не готов / Reserve not ready

**RU:** Резерв пока не прошёл достаточно проверок подряд.

**EN:** The reserve has not passed enough checks in a row yet.

**Что делать:** Подождите; посмотрите резерв в «Каналах и серверах».

**Action:** Wait; check the reserve in Channels and servers.

## PLAN-CONFIG

Основной и резерв не выбраны / Primary and reserve not chosen

**RU:** Для прогноза нужны основной и другой, резервный VPN.

**EN:** The forecast needs a primary and a different reserve.

**Что делать:** «Настройки → Все настройки приложения → 3 · Существующие VPN».

**Action:** Settings → All application settings → 3 · Existing VPNs.

## UPLINK-DOWN

Линия провайдера не работает / Provider line is down

**RU:** Роутер видит, что линия от провайдера отключена; переключение VPN не поможет.

**EN:** The router sees the line from your provider down; switching VPNs cannot help.

**Что делать:** Проверьте кабель и провайдера.

**Action:** Check the cable and the provider.

## STOPPED-NO-HEALTHY-PATH

Нет исправного пути / No healthy path

**RU:** Ни один VPN не прошёл проверки, поэтому контроллер остановился.

**EN:** No VPN passed its checks, so the controller stopped.

**Что делать:** Проверьте VPN-профили в GL.iNet.

**Action:** Check the VPN profiles in GL.iNet.

## GUARD-RETAINED

Защитная блокировка сохранена / Safety block kept

**RU:** Программа сохранила защитную блокировку (разрешён только трафик через VPN), потому что возврат не подтверждён.

**EN:** The program kept its safety block (only VPN traffic allowed) because the return was not verified.

**Что делать:** См. «Помощь» → аварийный возврат.

**Action:** See Help → emergency return.

## WATCHDOG-DID-NOT-ARM

Страхующий таймер не запустился / Safety timer did not start

**RU:** Вспомогательный процесс, гарантирующий возврат, не запустился вовремя, поэтому переключение не выполнено.

**EN:** The helper process that guarantees the return did not start in time, so the switch was not made.

**Что делать:** Не применяйте новый переход до подтверждения независимого восстановления. Изучите точный отказ; перезапуск службы — осознанное действие после безопасного Stop/восстановления.

**Action:** Do not apply another transition before the independent recovery worker is confirmed. Inspect its exact refusal; a service restart is deliberate and follows safe Stop/recovery.

## TRANSACTION-EXPIRED

Переключение не уложилось по времени / The switch ran out of time

**RU:** Время, отведённое на это переключение, уже закончилось.

**EN:** The time allowed for this switch had already ended.

**Что делать:** Начните заново.

**Action:** Start again.

## DNS-FAILED

Не работает поиск адресов / Name lookup fails

**RU:** VPN подключён, но поиск имени через него не работает.

**EN:** The VPN is connected but looking up a name through it fails.

**Что делать:** См. DNS-001.

**Action:** See DNS-001.

## HTTPS-FAILED

HTTPS-проверки ниже порога / HTTPS checks below threshold

**RU:** VPN не прошёл достаточное число HTTPS-проверок. Возможна частичная доступность; смотрите сохранённое число ответов и результат DNS.

**EN:** The VPN did not pass enough HTTPS checks. This may be partial availability; read the saved count and DNS result.

**Что делать:** См. VPN-003.

**Action:** See VPN-003.

## TUNNEL-DISCONNECTED

Туннель не подключён / Tunnel not connected

**RU:** VPN-туннель не поднят.

**EN:** The VPN tunnel is not up.

**Что делать:** Проверьте назначенный профиль и штатный клиент. Осознанный перезапуск/правка должны учитывать владение Auto и сначала завершённое восстановление.

**Action:** Inspect the configured binding and stock client state. Any deliberate profile restart/edit must respect current Auto ownership and completed recovery first.

## ROUTE-MISMATCH

Проверка шла не через VPN / Check did not go through the VPN

**RU:** Проверка роутера шла не через этот VPN, поэтому ничего не доказывает.

**EN:** The router’s check did not travel through this VPN, so it proves nothing.

**Что делать:** См. ROUTE-001.

**Action:** See ROUTE-001.

## PATH-UNVERIFIED

Путь проверки не подтверждён / Check path unconfirmed

**RU:** Роутер ещё не подтвердил, каким путём прошла проверка.

**EN:** The router has not yet confirmed which way its check went.

**Что делать:** Дождитесь следующей проверки.

**Action:** Wait for the next check.

## VPN-PROBE-HEALTHY

VPN работает / VPN works

**RU:** Проверки DNS и HTTPS через этот VPN прошли.

**EN:** DNS and HTTPS checks through this VPN passed.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## OBSERVATION-STALE

Измерения устарели / Measurements are old

**RU:** Последнее измерение слишком старое, чтобы что-то решать.

**EN:** The latest measurement is too old to decide anything.

**Что делать:** Проверьте, что мониторинг работает.

**Action:** Check that the monitor runs.

## OBSERVATION-UNKNOWN

Мало измерений / Not enough measurements

**RU:** Измерений пока недостаточно.

**EN:** There are not enough measurements yet.

**Что делать:** Подождите несколько минут.

**Action:** Wait a few minutes.

## LINK-UP

Линия поднята / Link is up

**RU:** Кабель или линия провайдера подняты. Это не доказательство интернета.

**EN:** The uplink cable or line is up. It is not proof of internet.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## CHECK-LIMIT

Достигнут лимит проверок / Check limit reached

**RU:** Чтобы не нагружать роутер, мониторинг проверяет за круг ограниченное число VPN; этот ждёт своей очереди.

**EN:** To stay light the monitor checks only a limited number of VPNs per round; this one waits for its turn.

**Что делать:** Дождитесь следующего круга или увеличьте лимит профилей в «Параметрах мониторинга».

**Action:** Wait for the next round or raise the profile limit in Monitoring preferences.

## FOREIGN-GUARD-TABLE

Чужая таблица с нашим именем / Foreign table with our name

**RU:** Существует таблица брандмауэра с именем защитного блока программы, но она не наша. Программа её не трогает.

**EN:** A firewall table with the name of the program’s guard exists but is not the program’s. The program never touches it.

**Что делать:** Сохраните чужую таблицу и изучите владельца только чтением. Приложение не должно удалять её ради обхода отказа; исправление постороннего firewall — отдельный проверенный объём работ.

**Action:** Keep the foreign table and inspect its owner read-only. The application must not delete it to bypass a refusal; unrelated firewall correction is a separate verified scope.

## GUARD-CHECK-FAILED

Защитная блокировка отклонена / Safety block rejected

**RU:** Брандмауэр отклонил защитную блокировку при проверке; ничего не применено.

**EN:** The firewall refused the program’s safety block when it was tested; nothing was applied.

**Что делать:** Проверьте, что nft работает на роутере; «Помощь» → аварийный возврат.

**Action:** Check that nft works on the router; Help → emergency return.

## GUARD-INSTALL-FAILED

Защитная блокировка не установлена / Safety block not installed

**RU:** Программа не смогла установить защитную блокировку, поэтому не переключала.

**EN:** The program could not install its safety block, so it did not switch.

**Что делать:** Проверьте nft; повторите позже.

**Action:** Check nft; repeat later.

## GUARD-QUERY-FAILED

Защитная блокировка не читается / Safety block cannot be read

**RU:** Программа не смогла прочитать состояние своей защитной блокировки.

**EN:** The program could not read the state of its own safety block.

**Что делать:** Проверьте nft; см. «Помощь» → аварийный возврат.

**Action:** Check nft; see Help → emergency return.

## POLICY-DUPLICATE-IDENTITY

Два одинаковых VPN-правила / Two identical VPN rules

**RU:** Два правила роутера выглядят одинаково, поэтому надёжно их различить нельзя.

**EN:** Two rules of the router look identical, so they cannot be told apart safely.

**Что делать:** Установите владельца дублей и сохраните исходную политику. Исправьте конкретную штатную конфигурацию после управляемого Stop; не удаляйте правила массово ради зелёного статуса.

**Action:** Identify duplicate ownership and preserve the original policy. Resolve the specific stock configuration after managed Stop; never mass-delete rules to obtain a green status.

## POLICY-GENERATION-CHANGED

Правила изменились / Rules changed meanwhile

**RU:** Правила VPN на роутере изменились после подготовки переключения, поэтому оно отменено.

**EN:** The router’s VPN rules changed after the switch was prepared, so it was cancelled.

**Что делать:** Не меняйте VPN-правила, пока Auto работает.

**Action:** Do not edit the VPN rules while Auto works.

## POLICY-IDENTITY-CHANGED

Правило изменилось / Rule identity changed

**RU:** Правило, участвовавшее в переключении, изменилось или исчезло.

**EN:** A rule that was part of the switch changed or disappeared.

**Что делать:** Не меняйте VPN-правила, пока Auto работает.

**Action:** Do not edit the VPN rules while Auto works.

## POLICY-REORDER-UNVERIFIED

Новый порядок не подтверждён / New order not confirmed

**RU:** После перестановки правила оказались не в ожидаемом порядке; роутер вернулся назад.

**EN:** After reordering, the rules were not in the expected order; the router went back.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## SOURCE-ORDER-MISMATCH

Порядок правил не тот / Rule order is not as expected

**RU:** Правила основного и резервного стоят не в том порядке, который ожидает программа.

**EN:** The primary and reserve rules are not in the order the program expects.

**Что делать:** «Настройки» → «Настройка» → проверьте основной и резерв.

**Action:** Settings → Setup → check the primary and reserve.

## EXIT-CHANGED

Внешний адрес изменился / The exit address changed

**RU:** Адрес, который видит интернет, изменился между двумя проверками одного VPN.

**EN:** The address the internet sees changed between two checks of the same VPN.

**Что делать:** Повторите тест; такое бывает у провайдера с ротацией адресов.

**Action:** Repeat the trial; a provider that rotates addresses can cause this.

## EXIT-IP-NOT-GLOBAL

Внешний адрес не публичный / Exit address is private

**RU:** Адрес, ответивший на проверку, частный, поэтому проверка ничего не доказывает.

**EN:** The exit address answered by the check is a private one, so the check proves nothing.

**Что делать:** Проверьте, что VPN действительно выходит в интернет.

**Action:** Check that the VPN really reaches the internet.

## JOURNAL-ORDER-INVALID

Порядок в журнале неверен / Journal order invalid

**RU:** Сохранённый порядок в журнале переключения противоречив.

**EN:** The saved order in the switch journal is inconsistent.

**Что делать:** Заархивируйте журнал командой homensai-vpn-emergency close-journal, проверив правила.

**Action:** Archive the journal with homensai-vpn-emergency close-journal after checking the rules.

## JOURNAL-SECTION-INVALID

Журнал называет неверное правило / Journal names an invalid rule

**RU:** Журнал называет правило, которое недопустимо.

**EN:** The journal names a rule that is not valid.

**Что делать:** То же, что JOURNAL-ORDER-INVALID.

**Action:** Same as JOURNAL-ORDER-INVALID.

## DEADLINE-TIMEZONE-REQUIRED

Для срока нужен часовой пояс / Deadline needs a time zone

**RU:** Срок окна теста записан без часового пояса.

**EN:** The deadline of the test window was written without a time zone.

**Что делать:** Задайте ограниченный срок с явным часовым поясом для своего режима. Проверьте фактическое время; не переопределяйте истёкшее окно переводом часов.

**Action:** Supply the intended bounded deadline with an explicit timezone for that mode. Verify actual time; do not reinterpret an expired window by changing the clock.

## INVALID-ACCELERATION-REQUEST

Неверный запрос / Invalid request

**RU:** Запрос на подготовку роутера имел неверный вид.

**EN:** The request to prepare the router had a wrong form.

**Что делать:** Используйте кнопку на странице, а не ручную команду.

**Action:** Use the page button, not a manual command.

## ACCELERATION-PREPARE-ATTEMPT-LIMIT

Слишком много попыток подготовки / Too many preparation attempts

**RU:** Подготовка роутера (отключение аппаратного ускорения) не удалась трижды.

**EN:** The preparation of the router (hardware acceleration off) failed three times.

**Что делать:** Сохраните отказы подготовки и проверьте фактическую поддержку/runtime. Отдельной коррекции нужна отмена; не выгружайте драйверы принудительно и не сбрасывайте попытки ради повтора.

**Action:** Retain failed preparation evidence and inspect actual runtime/vendor support. A separate approved correction needs undo; never force-unload drivers or reset attempt metadata to retry.

## ACCELERATION-PREPARE-DURING-TRANSACTION

Подготовка во время переключения / Preparation during a switch

**RU:** Подготовка роутера запрошена во время переключения; отказано.

**EN:** The router preparation was requested while a switch was running; refused.

**Что делать:** Дождитесь окончания переключения.

**Action:** Wait until the switch ends.

## HNAT-DISABLE-UNVERIFIED

Аппаратное ускорение не подтверждено как выключенное / Hardware acceleration not confirmed off

**RU:** После попытки аппаратное ускорение (HNAT) всё ещё не подтверждено как выключенное.

**EN:** After the attempt, the hardware acceleration (HNAT) is still not proven off.

**Что делать:** Одной сохранённой галочки недостаточно. Изучите подготовку/runtime этой прошивки и только применимое обратимое исправление; не удаляйте модули принудительно.

**Action:** A saved checkbox is insufficient. Read the preparation/runtime evidence for this firmware and plan only the applicable reversible correction; do not force module removal.

## SFE-DISABLE-UNVERIFIED

Программное ускорение не подтверждено как выключенное / Software acceleration not confirmed off

**RU:** Модуль программного ускорения всё ещё загружен.

**EN:** The software acceleration module is still loaded.

**Что делать:** Проверьте точные модули, исходный запуск и сохранённые файлы. Используйте проверенную подготовку/отмену вместо слепого переключения или принудительной выгрузки драйвера.

**Action:** Check the exact loaded modules, saved boot ownership and preserved original files. Use reviewed preparation/undo rather than blindly forcing a toggle or unloading a driver.

## UNEXPECTED-DEBUGFS-PATH

Неожиданный системный путь / Unexpected system path

**RU:** Системный путь, который должен быть обычной папкой, оказался ссылкой; программа отказывается его использовать.

**EN:** A system path that should be a normal folder is a link; the program refuses to use it.

**Что делать:** Обратитесь в поддержку с кодом; ничего не менялось.

**Action:** Contact support with the code; nothing was changed.

## UNEXPECTED-HNAT-PATH

Неожиданный системный путь / Unexpected system path

**RU:** То же, что UNEXPECTED-DEBUGFS-PATH для файла переключателя ускорения.

**EN:** Same as UNEXPECTED-DEBUGFS-PATH for the acceleration switch file.

**Что делать:** Обратитесь в поддержку с кодом.

**Action:** Contact support with the code.

## UNSAFE-FIREWALL-SECTION

Небезопасное имя секции брандмауэра / Unsafe firewall section name

**RU:** У секции брандмауэра имя, которое программа не решается трогать.

**EN:** A firewall section has a name the program does not dare to touch.

**Что делать:** Обратитесь в поддержку с кодом.

**Action:** Contact support with the code.

## UNSAFE-GUARD-DEVICE

Небезопасное имя интерфейса / Unsafe interface name

**RU:** В имени сетевого интерфейса странные символы; программа отказывается вносить его в правило брандмауэра.

**EN:** A network interface name has odd characters; the program refuses to put it into a firewall rule.

**Что делать:** Обратитесь в поддержку с кодом.

**Action:** Contact support with the code.

## UNSAFE-SECTION

Небезопасное имя правила / Unsafe rule name

**RU:** У VPN-правила имя, которое программа отказывается использовать.

**EN:** A VPN rule has a name the program refuses to use.

**Что делать:** Обратитесь в поддержку с кодом.

**Action:** Contact support with the code.

## FAULT-ACTIVE

Тест сбоя выполняется / Failure test is running

**RU:** Преднамеренная блокировка трафика теста сбоя включена.

**EN:** The deliberate traffic block of the failure test is on.

**Что делать:** Дождитесь окончания или нажмите «Отменить сбой сейчас».

**Action:** Wait for its end or press “Cancel fault now”.

## FAULT-ALREADY-ACTIVE

Тест сбоя уже идёт / Failure test already runs

**RU:** Одновременно может идти только один тест сбоя.

**EN:** Only one failure test can run at a time.

**Что делать:** Дождитесь или отмените идущий.

**Action:** Wait or cancel the running one.

## FAULT-CANCELLED

Тест сбоя отменён / Failure test cancelled

**RU:** Вы отменили тест сбоя, блокировка снята.

**EN:** You cancelled the failure test and the block was removed.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## FAULT-TRANSITION-CONFIRMED

Тест перехода пройден / Transition test passed

**RU:** На другом канале получены свежие успешные проверки и подтверждён маршрут. Искусственная блокировка снята.

**EN:** The other channel has fresh successful checks and its route is confirmed. The artificial traffic block was removed.

**Что делать:** Результат смотрите в истории теста.

**Action:** Review the test history.

## FAULT-TRANSITION-NOT-CONFIRMED

Переход не подтверждён / Transition not confirmed

**RU:** Время теста истекло без подтверждённого перехода. Искусственная блокировка снята.

**EN:** The test time elapsed without a confirmed transition. The artificial traffic block was removed.

**Что делать:** Проверьте состояние Auto и события: пороги проверок, паузу между переходами и исправность каналов.

**Action:** Inspect Auto state and events, including thresholds, cooldown and channel health.

## FAULT-CLEANED

Тест сбоя убран / Failure test cleaned up

**RU:** Тест сбоя закончился, его блокировка снята.

**EN:** The failure test ended and its block was removed.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## FAULT-NOT-ACTIVE

Тест сбоя не идёт / No failure test is running

**RU:** Отменять нечего.

**EN:** There is nothing to cancel.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## FAULT-NATIVE-PREREQUISITES

Проверки роутера не пройдены / Router checks not passed

**RU:** Часть проверок роутера, перечисленных на «Обзоре», не пройдена.

**EN:** Some of the router checks listed on the Overview are not passed.

**Что делать:** Исправьте перечисленное («Обзор» → «Что нужно перед запуском Auto»).

**Action:** Fix the listed items (Overview → Before you can start Auto).

## FAULT-SESSION-CONSENT-REQUIRED

Переподключение не разрешено / Reconnection not allowed

**RU:** Вы не разрешили короткое переподключение звонков и сессий.

**EN:** You have not allowed a short reconnection of calls and sessions.

**Что делать:** «Настройки → Все настройки приложения → 3 · Существующие VPN»: поставьте разрешение.

**Action:** Settings → All application settings → 3 · Existing VPNs: tick the permission.

## FAULT-WINDOW-TOO-SHORT

Окно теста слишком короткое / Test window too short

**RU:** Остаток окна теста короче, чем тест сбоя вместе с возвратом.

**EN:** The remaining time of the trial window is shorter than the failure test plus its return.

**Что делать:** В ограниченном сертифицированном режиме выберите длительность внутри текущего окна либо подготовьте отдельно разрешённый новый тест. У непрерывной пары собственные проверки; не сбрасывайте lease для их обхода.

**Action:** In the bounded certified mode choose a duration fitting its current window, or prepare a separately authorized new trial. Continuous pair mode has its own guards; do not reset a lease to evade them.

## FAULT-NOT-CURRENT-SOURCE

Это не текущий основной / Not the current primary

**RU:** Тест сбоя может ломать только VPN, который сейчас основной.

**EN:** The failure test can only break the VPN that is currently the primary.

**Что делать:** Выберите текущий основной.

**Action:** Choose the current primary.

## FAULT-HEALTHY-RESERVE-REQUIRED

Нужен исправный резерв / Reserve must be healthy

**RU:** Для теста нужно, чтобы и основной, и резерв сейчас работали.

**EN:** The test needs both the primary and the reserve to work right now.

**Что делать:** Проверьте оба в «Каналах и серверах».

**Action:** Check both in Channels and servers.

## FAULT-WOULD-REMOVE-RESERVE

Тест сломал бы и резерв / The test would also break the reserve

**RU:** Выбранная область (вся группа канала) содержит и резерв.

**EN:** The chosen scope (the whole channel group) contains the reserve too.

**Что делать:** Выберите «Текущий основной сервер».

**Action:** Choose “Current primary server”.

## FAULT-PATH-UNVERIFIED

Путь VPN не подтверждён / Path of the VPN not confirmed

**RU:** Программа не смогла подтвердить, какое сетевое устройство принадлежит VPN, поэтому ничего не блокирует.

**EN:** The program could not confirm which network device belongs to the VPN, so it will not block anything.

**Что делать:** Дождитесь следующей проверки и повторите.

**Action:** Wait for the next check and repeat.

## FAULT-WATCHDOG-NOT-READY

Страхующий таймер не готов / Safety timer not ready

**RU:** Помощник, который сам снимает блокировку, не запустился; тест не начат.

**EN:** The helper that removes the block by itself did not start; the test was not started.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## FAULT-UNSAFE-SCOPE

Небезопасная область / Unsafe scope

**RU:** Запрошенная область недопустима.

**EN:** The requested scope is not allowed.

**Что делать:** Пользуйтесь элементами страницы.

**Action:** Use the page controls.

## FAULT-FOREIGN-TABLE

Чужая таблица брандмауэра / Foreign firewall table

**RU:** Существует таблица брандмауэра с именем теста, но она не наша.

**EN:** A firewall table with the test’s name exists but is not the program’s.

**Что делать:** Проверьте nft по SSH.

**Action:** Check nft over SSH.

## FAULT-TIMEOUT-RULE-FAILED

Автоматическое окончание не задано / Automatic end could not be set

**RU:** Брандмауэр не смог задать таймер, который снимает блокировку сам; ничего не блокировалось.

**EN:** The firewall could not set the timer that removes the block by itself; nothing was blocked.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## FAULT-APPLY-UNCONFIRMED

Блокировка не подтверждена / Block not confirmed

**RU:** Не подтверждено, что блокировка теста применена; для безопасности она снята.

**EN:** It is not confirmed that the test block was applied; it was removed to be safe.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## FAULT-CLEANUP-UNCONFIRMED

Снятие не подтверждено / Removal not confirmed

**RU:** Не подтверждено, что блокировка теста снята. Она всё равно закончится по таймеру ядра.

**EN:** It is not confirmed that the test block was removed. It still ends by its own kernel timer.

**Что делать:** Подождите до 3 минут; затем проверьте интернет; «Помощь» → аварийный возврат.

**Action:** Wait up to 3 minutes; then check the internet; Help → emergency return.

## FAULT-STATE-UNVERIFIED

Состояние теста не подтверждено / Test state unverified

**RU:** Сохранённому состоянию теста сбоя нельзя доверять.

**EN:** The saved state of the failure test cannot be trusted.

**Что делать:** Нажмите «Отменить сбой сейчас».

**Action:** Press “Cancel fault now”.

## FAULT-HISTORY-CORRUPT

История тестов повреждена / Test history damaged

**RU:** Запись прошлых тестов сбоя не читается.

**EN:** The record of earlier failure tests cannot be read.

**Что делать:** Делать ничего не нужно; новые тесты работают.

**Action:** Nothing to do; new tests still work.

## FAULT-WORKER-INVALID

Вспомогательный процесс недействителен / Helper process invalid

**RU:** Вспомогательный процесс теста неверно представился.

**EN:** The helper process of the test did not identify itself correctly.

**Что делать:** Отмените тест и повторите.

**Action:** Cancel the test and repeat.

## FAULT-WORKER-STALE

Вспомогательный процесс устарел / Helper process stale

**RU:** Вспомогательный процесс теста устарел; тест завершён.

**EN:** The helper process of the test is old; the test was ended.

**Что делать:** Повторите.

**Action:** Repeat.

## TELEGRAM-FORMAT-FAILED

Отчёт не сформирован / Report could not be formed

**RU:** Программа не смогла собрать текст отчёта.

**EN:** The program could not build the report text.

**Что делать:** Повторите позже; если повторяется, сообщите в поддержку.

**Action:** Repeat later; if it repeats, tell support.

## TELEGRAM-REPORT-UNAVAILABLE

Данные для отчёта недоступны / Report data not available

**RU:** У мониторинга пока нет данных для отчёта.

**EN:** The monitor has no data for the report yet.

**Что делать:** Подождите несколько минут после запуска мониторинга.

**Action:** Wait a few minutes after the monitor starts.

## TELEGRAM-REQUEST-REJECTED

Telegram отклонил запрос / Telegram rejected the request

**RU:** Telegram ответил, что не принимает сообщение (неверный токен, неверный чат или бот заблокирован).

**EN:** Telegram answered that it will not take the message (wrong token, wrong chat or the bot is blocked).

**Что делать:** Проверьте токен и Chat ID в мастере Telegram; нажмите Start в боте.

**Action:** Check the token and the chat ID in the Telegram wizard; press Start in the bot.

**Пример / Example:** 401 или «Unauthorized» → токен неверный. 400 или «chat not found» → неверный Chat ID либо вы не нажали Start. / 401 or “Unauthorized” → the token is wrong. 400 or “chat not found” → the chat ID is wrong or you did not press Start.

## TELEGRAM-RETRY

Повторю отправку / Will retry

**RU:** Сообщение сейчас не отправилось; программа попробует позже.

**EN:** The message could not be sent now; the program tries again later.

**Что делать:** Проверьте, что у роутера есть интернет.

**Action:** Check that the router has internet.

## TELEGRAM-SCHEDULE

Неверное расписание / Invalid schedule

**RU:** В расписании отчётов неверное значение.

**EN:** The report schedule has a wrong value.

**Что делать:** Откройте мастер Telegram и выберите расписание заново.

**Action:** Open the Telegram wizard and choose the schedule again.

## TELEGRAM-SETUP-FIELDS

Неверные поля / Wrong fields

**RU:** В форме Telegram оказались неожиданные поля.

**EN:** The Telegram form had unexpected fields.

**Что делать:** Обновите страницу и заполните мастер заново.

**Action:** Reload the page and fill the wizard again.

## TELEGRAM-STATE-RECOVERED

Состояние отчётов восстановлено / Report state recovered

**RU:** Сохранённое состояние отчётов было повреждено и восстановлено; один отчёт может повториться или пропуститься.

**EN:** The saved report state was damaged and was rebuilt; one report may repeat or be skipped.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## TELEGRAM-STATE-WRITE-FAILED

Состояние отчётов не сохранено / Report state not saved

**RU:** Программа не смогла сохранить время последнего отчёта; отчёты могут повторяться.

**EN:** The program could not save the time of the last report; reports may repeat.

**Что делать:** Проверьте свободное место (см. «Хранилище»).

**Action:** Check the free space (see “Storage”).

## TELEGRAM-TEST-RATE-LIMIT

Тестовое сообщение слишком часто / Test message too often

**RU:** Тестовое сообщение можно отправлять не чаще, чем раз в короткое время.

**EN:** A test message can be sent only once in a short time.

**Что делать:** Подождите минуту.

**Action:** Wait a minute.

## SETUP-FIELDS

Неверные поля формы / Wrong fields in the form

**RU:** В форме настройки оказались неожиданные поля.

**EN:** The setup form had unexpected fields.

**Что делать:** Обновите страницу и снова пользуйтесь мастером.

**Action:** Reload the page and use the wizard again.

## SETUP-KIND

Неизвестный вид настройки / Unknown setup kind

**RU:** Запрос назвал несуществующую настройку.

**EN:** The request named a setup that does not exist.

**Что делать:** Обновите страницу.

**Action:** Reload the page.

## SETUP-NAME

Неверное название / Invalid name

**RU:** Название пустое, длиннее 64 символов или содержит управляющие символы.

**EN:** A name is empty, longer than 64 characters or has control characters.

**Что делать:** Используйте короткое простое название.

**Action:** Use a short plain name.

## SETUP-SERVER

Неверная строка сервера / Invalid server row

**RU:** Строка сервера в форме неполная.

**EN:** A server row of the form is incomplete.

**Что делать:** Заполните название, группу, приоритет и галочку «Наблюдать».

**Action:** Fill name, group, priority and the Monitor box.

## SETUP-DELTA-UNVERIFIED

Несохранённые изменения не проверить / Unsaved changes unverifiable

**RU:** Программа не смогла проверить, есть ли на роутере другие несохранённые изменения её настроек.

**EN:** The program could not check whether the router has other unsaved changes of its own settings.

**Что делать:** Обновите страницу и попробуйте снова.

**Action:** Reload the page and try again.

## SETUP-CHECK-OK

Запись настроек работает / Settings writer works

**RU:** Установленная запись настроек прошла изолированную самопроверку.

**EN:** The installed writer passed its isolated self-check.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SETUP-CHECK-FAILED

Самопроверка записи настроек не прошла / Settings writer self-check failed

**RU:** Сохранение заблокировано, потому что запись настроек не прошла самопроверку (часто после обновления).

**EN:** Saving is blocked because the writer failed its self-check (often after an upgrade).

**Что делать:** Выйдите из LuCI и войдите снова, затем обновите Ctrl+F5.

**Action:** Sign out of LuCI and in again, then reload with Ctrl+F5.

## TERMS-VERSION

Версия условий не совпадает / Terms version mismatch

**RU:** Страница прислала другую версию условий, чем знает роутер.

**EN:** The page sent a different version of the terms than the router knows.

**Что делать:** Обновите Ctrl+F5 и примите условия заново.

**Action:** Reload with Ctrl+F5 and accept again.

## MONITOR-PREFERENCES-FIELDS

Неверные поля / Wrong fields

**RU:** В форме параметров мониторинга оказались неожиданные поля.

**EN:** The monitoring preferences form had unexpected fields.

**Что делать:** Обновите страницу.

**Action:** Reload the page.

## PRIORITY-SAVED

Приоритеты сохранены / Priorities saved

**RU:** Новый порядок серверов сохранён. Маршрут не менялся.

**EN:** The new order of the servers was saved. No route changed.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## PRIORITY-SAVE-FAILED

Приоритеты не сохранены / Priorities not saved

**RU:** Роутер отказал в новом порядке.

**EN:** The router refused the new order.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## PRIORITY-STALE-REVIEW

Просмотр устарел / The review is outdated

**RU:** Список изменился после вашего просмотра; ничего не сохранено.

**EN:** The list changed after you reviewed it; nothing was saved.

**Что делать:** Просмотрите порядок заново и сохраните.

**Action:** Review the order again and save.

## PRIORITY-FIELDS

Неверные поля / Wrong fields

**RU:** В форме приоритетов оказались неожиданные поля.

**EN:** The priorities form had unexpected fields.

**Что делать:** Обновите страницу.

**Action:** Reload the page.

## PRIORITY-INVALID-SELECTION

Неверный выбор / Invalid selection

**RU:** Выбранные серверы нельзя упорядочить так.

**EN:** The chosen servers cannot be ordered this way.

**Что делать:** Выберите подходящие серверы заново.

**Action:** Choose the eligible servers again.

## PRIORITY-PROFILE-INELIGIBLE

Сервер не подходит / Server not eligible

**RU:** Выбранный сервер не подключён или не наблюдается.

**EN:** A chosen server is not connected or not monitored.

**Что делать:** Подключите его или включите ему «Наблюдать».

**Action:** Connect it or turn on “Monitor” for it.

## RECOVERY-FIELDS

Неверные поля / Wrong fields

**RU:** В форме правил восстановления оказались неожиданные поля.

**EN:** The recovery rules form had unexpected fields.

**Что делать:** Обновите страницу.

**Action:** Reload the page.

## RECOVERY-RANGE

Значение вне диапазона / Value out of range

**RU:** Число в правилах восстановления вне допустимого диапазона.

**EN:** A number in the recovery rules is outside its allowed range.

**Что делать:** Используйте значения, которые предлагает мастер.

**Action:** Use the values the wizard offers.

## RECOVERY-REQUIRED

Нужны правила восстановления / Recovery rules required

**RU:** Правила восстановления ни разу не сохранялись.

**EN:** The recovery rules were never saved.

**Что делать:** «Настройки» → «Расширенные» → «Правила восстановления».

**Action:** Settings → Advanced settings → Recovery rules.

## RECOVERY-RETURN-POLICY

Неверное правило возврата / Invalid return rule

**RU:** У правила возврата неизвестное значение.

**EN:** The return rule has an unknown value.

**Что делать:** Выберите одно из предложенных правил.

**Action:** Choose one of the offered rules.

## CONFIG-STOP-AUTO-FIRST

Сначала остановите Auto / Stop Auto first

**RU:** Эту настройку нельзя менять, пока Auto работает.

**EN:** This setting cannot change while Auto works.

**Что делать:** Остановите Auto на «Обзоре», дождитесь возврата, затем меняйте.

**Action:** Stop Auto on the Overview, wait for the return, then change it.

## CONFIG-RECOVERY-UNVERIFIED

Конфигурацию не подтвердить / Configuration cannot be confirmed

**RU:** Программа не смогла подтвердить конфигурацию, поэтому отказывается её менять.

**EN:** The program could not confirm the configuration, so it refuses to change it.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## CONFIG-STORAGE-FREE

Мало свободного места / Not enough free space

**RU:** На роутере слишком мало места, чтобы безопасно сохранить настройки.

**EN:** The router has too little free space to save settings safely.

**Что делать:** Освободите место; см. «Помощь» → «Хранилище».

**Action:** Free some space; see Help → Storage.

## LIFECYCLE-STOP-AUTO-FIRST

Сначала остановите Auto / Stop Auto first

**RU:** Для обновления или остановки службы нужно, чтобы Auto был выключен и исходный маршрут восстановлен.

**EN:** An upgrade or stop of the service needs Auto to be off and the original route restored.

**Что делать:** Нажмите «Стоп» в блоке Auto и дождитесь подтверждения.

**Action:** Press Stop in the Auto card and wait for the confirmation.

## STORAGE-001

Проблема с хранилищем роутера / Router storage problem

**RU:** Программа не смогла сохранить свои данные (нет места или хранилище только для чтения).

**EN:** The program could not save its data (no space or the storage is read-only).

**Что делать:** Освободите место на роутере; см. «Помощь» → «Хранилище».

**Action:** Free space on the router; see Help → Storage.

## STORAGE-RECOVERED

Хранилище восстановлено / Storage recovered

**RU:** Повреждённые данные восстановлены из последней исправной копии.

**EN:** The damaged data was restored from the last good copy.

**Что делать:** Делать ничего не нужно; последние минуты могут отсутствовать.

**Action:** Nothing to do; the newest minutes may be missing.

## SCAN-MEASUREMENT-FAILED

Запрос проверки не удался / Check request failed

**RU:** Запрос «Проверить VPN сейчас» не получил измерения.

**EN:** The “Check the VPNs now” request got no measurement.

**Что делать:** Посмотрите на лампу мониторинга и повторите.

**Action:** Check the Monitoring lamp and repeat.

## SCAN-SNAPSHOT-MISMATCH

Измерение не совпало / Measurement does not match

**RU:** Измерение не относится к этому запросу.

**EN:** The measurement does not belong to this request.

**Что делать:** Нажмите кнопку проверки ещё раз.

**Action:** Press the check button again.

## SCAN-STORAGE

Запрос не сохранён / Request not saved

**RU:** Роутер не смог сохранить запрос проверки.

**EN:** The router could not save the check request.

**Что делать:** Освободите место; повторите.

**Action:** Free space; repeat.

## RPC-DUPLICATE-FIELD

Повтор поля в запросе / Duplicate field in a request

**RU:** Запрос к роутеру дважды назвал одно поле; он отклонён.

**EN:** A request to the router named the same field twice; it was refused.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## RPC-INPUT-COMPLEXITY

Запрос слишком сложный / Request too complex

**RU:** Запрос был слишком большим или слишком вложенным.

**EN:** The request was too big or too deeply nested.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## RPC-INPUT-DEPTH

Запрос слишком вложенный / Request too deep

**RU:** Запрос вложен слишком глубоко.

**EN:** The request nests too deeply.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## RPC-INPUT-OBJECT

Запрос неверного вида / Request has a wrong form

**RU:** Запрос был не в ожидаемом виде.

**EN:** The request was not in the expected form.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## RPC-UNCONFIRMED

Результат кнопки не подтверждён / Button result not confirmed

**RU:** Служба роутера приняла нажатие, но не смогла подтвердить результат. Нажатие не повторялось, поэтому ничего не выполнилось дважды.

**EN:** The router service accepted the button but could not confirm its result. It was not repeated, so nothing happened twice.

**Что делать:** Посмотрите состояние на странице; нажмите кнопку ещё раз, только если ничего не изменилось.

**Action:** Look at the state on the page; press the button again only if nothing changed.

## RPC-NONFINITE-NUMBER

Неверное число / Invalid number

**RU:** Запрос содержал недопустимое число.

**EN:** The request contained a number that is not valid.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## OFFLINE-FIXTURE

Тестовые данные офлайн-просмотра / Test data of the offline preview

**RU:** Этот код есть только в офлайн-просмотре для разработки. На настоящем роутере его не бывает.

**EN:** This code exists only in the offline preview used for development. It never appears on a real router.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## AUTO-STOP-QUEUED

Остановка поставлена в очередь / Stop was queued

**RU:** Роутер принял запрос остановки.

**EN:** The router accepted the Stop request.

**Что делать:** Дождитесь, пока лампа изменится.

**Action:** Wait for the lamp to change.

## RETURN-REFUSED

Возврат отклонён / Return refused

**RU:** Роутер отклонил запрос «Вернуться на основной» (обычно потому, что основной ещё не исправен).

**EN:** The router refused the “Return to primary” request (usually because the primary is not healthy yet).

**Что делать:** Проверьте основной в «Каналах и серверах» и нажмите снова.

**Action:** Check the primary in Channels and servers and press again.

## RECOVERY-SAVED

Правила восстановления сохранены / Recovery rules saved

**RU:** Сохранено.

**EN:** Saved.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## RECOVERY-SAVE-FAILED

Правила восстановления не сохранены / Recovery rules not saved

**RU:** Роутер отказал в сохранении.

**EN:** The router refused to save them.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## RECOVERY-SAVE-UNCONFIRMED

Сохранение не подтверждено / Save not confirmed

**RU:** Роутер не ответил на сохранение вовремя; оно могло записаться, а могло и нет.

**EN:** The router did not answer the save in time; it may or may not be saved.

**Что делать:** Обновите страницу и посмотрите настройку.

**Action:** Reload the page and look at the setting.

## SPEED-CONFIG-SAVED

Настройки скорости сохранены / Speed settings saved

**RU:** Сохранено.

**EN:** Saved.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SPEED-CONFIG-FAILED

Настройки скорости не сохранены / Speed settings not saved

**RU:** Роутер отказал в сохранении.

**EN:** The router refused to save them.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## SPEED-QUEUED

Тест скорости поставлен в очередь / Speed test queued

**RU:** Роутер принял тест скорости; он начнётся через секунды.

**EN:** The router accepted the speed test; it starts within seconds.

**Что делать:** Дождитесь результата в таблице.

**Action:** Wait for the result in the table.

## SPEED-START-FAILED

Тест скорости не запустился / Speed test did not start

**RU:** Роутер не принял тест скорости.

**EN:** The router did not accept the speed test.

**Что делать:** Посмотрите на код рядом: там причина.

**Action:** Look at the code beside it for the reason.

## SPEED-CANCEL-QUEUED

Отмена поставлена в очередь / Cancel queued

**RU:** Роутер принял запрос отменить тест скорости.

**EN:** The router accepted the request to cancel the speed test.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SCAN-ACK-UNCONFIRMED

Запрос проверки не подтверждён / Check request not confirmed

**RU:** Роутер не подтвердил запрос проверки ясно.

**EN:** The router did not clearly confirm the check request.

**Что делать:** Убедитесь, что мониторинг работает, и нажмите снова.

**Action:** Make sure the monitor runs and press again.

## SCAN-SNAPSHOT-UNCONFIRMED

Результат не подтверждён / Result not confirmed

**RU:** Измерение после запроса не удалось подтвердить.

**EN:** The measurement after the request could not be confirmed.

**Что делать:** Нажмите кнопку проверки ещё раз.

**Action:** Press the check button again.

## MONITOR-PREFERENCES-SAVED

Параметры мониторинга сохранены / Monitoring preferences saved

**RU:** Сохранено.

**EN:** Saved.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## MONITOR-PREFERENCES-FAILED

Параметры мониторинга не сохранены / Monitoring preferences not saved

**RU:** Роутер отказал в сохранении.

**EN:** The router refused to save them.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## MONITOR-PREFERENCES-UNCONFIRMED

Сохранение не подтверждено / Save not confirmed

**RU:** Роутер не ответил на сохранение вовремя.

**EN:** The router did not answer the save in time.

**Что делать:** Обновите страницу и посмотрите настройку.

**Action:** Reload the page and look at the setting.

## MONITOR-UNKNOWN

Ответ мониторинга неизвестен / Monitor answer unknown

**RU:** Служба мониторинга ответила без ясного кода.

**EN:** The monitor service answered without a clear code.

**Что делать:** Обновите и посмотрите на лампу мониторинга.

**Action:** Reload and look at the Monitoring lamp.

## PRIORITY-PREVIEW-FAILED

Просмотр не удался / Preview failed

**RU:** Роутер не смог подготовить просмотр нового порядка.

**EN:** The router could not prepare the preview of the new order.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## PRIORITY-PREVIEW-UNCONFIRMED

Просмотр не подтверждён / Preview not confirmed

**RU:** Нет ясного ответа на запрос просмотра.

**EN:** No clear answer to the preview request.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## PRIORITY-RPC-UNCONFIRMED

Ответ не подтверждён / Answer not confirmed

**RU:** Нет ясного ответа от роутера.

**EN:** No clear answer from the router.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## PRIORITY-SELECT-ELIGIBLE-SERVERS

Сначала выберите серверы / Choose servers first

**RU:** Выберите хотя бы серверы, которые можно упорядочить.

**EN:** Choose at least the servers that can be ordered.

**Что делать:** Отметьте серверы, которые нужно упорядочить.

**Action:** Tick the servers you want to order.

## PRIORITY-UNKNOWN

Ответ по приоритетам неизвестен / Priority answer unknown

**RU:** Роутер ответил без ясного кода.

**EN:** The router answered without a clear code.

**Что делать:** Обновите и попробуйте снова.

**Action:** Reload and try again.

## RECOVERY-PERIOD

Неверный период / Invalid period

**RU:** Период в правилах восстановления недопустим.

**EN:** A period in the recovery rules is not valid.

**Что делать:** Используйте значения мастера.

**Action:** Use the values the wizard offers.

## RPC-INVENTORY-INVALID

Список роутера нечитаем / Router list unreadable

**RU:** Список VPN-профилей от роутера имел неожиданный вид.

**EN:** The list of VPN profiles from the router had an unexpected form.

**Что делать:** Обновите Ctrl+F5; если не помогло, выйдите из LuCI и войдите снова.

**Action:** Reload with Ctrl+F5; if it stays, sign out of LuCI and in again.

## RPC-INVENTORY-UNAVAILABLE

Список роутера недоступен / Router list unavailable

**RU:** Страница не получила список VPN-профилей; настройки не показываются и ничего не сохраняется.

**EN:** The page could not get the list of VPN profiles; settings are not shown and nothing is saved.

**Что делать:** Подождите минуту и обновите; проверьте, что вы вошли в LuCI.

**Action:** Wait a minute and reload; check that you are signed in to LuCI.

## TELEGRAM-FORGET-UNCONFIRMED

Удаление токена не подтверждено / Token removal not confirmed

**RU:** Роутер не подтвердил, что сохранённый токен бота удалён.

**EN:** The router did not confirm that the stored bot token was deleted.

**Что делать:** Обновите и проверьте состояние Telegram.

**Action:** Reload and check the Telegram status.

## TERMS-SAVE-FAILED

Условия не сохранены / Terms not saved

**RU:** Принятие условий не удалось сохранить.

**EN:** The acceptance of the terms could not be saved.

**Что делать:** Обновите и примите снова.

**Action:** Reload and accept again.

## TERMS-SAVE-UNCONFIRMED

Принятие не подтверждено / Acceptance not confirmed

**RU:** Роутер не подтвердил принятие вовремя.

**EN:** The router did not confirm the acceptance in time.

**Что делать:** Обновите и проверьте.

**Action:** Reload and check.

## CAUSE-UNKNOWN

Причина неизвестна / Cause not known

**RU:** Программа увидела сбой, но у неё нет доказательств причины. Она не гадает.

**EN:** The program saw a failure but has no evidence for its cause. It never guesses.

**Что делать:** Посмотрите на другие коды рядом.

**Action:** Look at the other codes beside it.

## UNKNOWN-FUTURE-TIMESTAMP

Время из будущего / Time in the future

**RU:** У записи время позже текущего (часы роутера в тот момент были неверны).

**EN:** A record has a time later than now (the clock of the router was wrong at that moment).

**Что делать:** Проверьте часы роутера («Помощь» → «Неверные даты»).

**Action:** Check the router clock (Help → Dates are wrong).

## EXPORT-KIND

Неизвестный экспорт / Unknown export

**RU:** Страница запросила экспорт несуществующей таблицы.

**EN:** The page asked to export a table that does not exist.

**Что делать:** Обновите страницу.

**Action:** Reload the page.

## DEPENDENCY-IP

Нет программы «ip» / Program “ip” missing

**RU:** На роутере нет инструмента «ip», нужного мониторингу.

**EN:** The router lacks the “ip” tool the monitor needs.

**Что делать:** Установите недостающий пакет (opkg install ip-full).

**Action:** Install the missing package (opkg install ip-full).

## DEPENDENCY-LUA

Нет Lua / Lua missing

**RU:** На роутере нет Lua.

**EN:** The router lacks Lua.

**Что делать:** Установите lua.

**Action:** Install lua.

## DEPENDENCY-UBUS

Нет ubus / ubus missing

**RU:** На роутере нет ubus.

**EN:** The router lacks ubus.

**Что делать:** Установите ubus.

**Action:** Install ubus.

## DEPENDENCY-UCI

Нет UCI / UCI missing

**RU:** На роутере нет UCI (libuci-lua).

**EN:** The router lacks UCI (libuci-lua).

**Что делать:** Установите libuci-lua.

**Action:** Install libuci-lua.

## SPEED-COMPLETE

Тест скорости завершён / Speed test finished

**RU:** Тест скорости сервера завершён.

**EN:** The speed test of a server finished.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SPEED-NOT-RUNNING

Тест скорости не идёт / No speed test is running

**RU:** Отменять нечего.

**EN:** There is nothing to cancel.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SPEED-NO-SAMPLE

Нет измерения / No measurement

**RU:** Тест скорости не получил пригодного измерения.

**EN:** The speed test got no usable measurement.

**Что делать:** Повторите позже; проверьте VPN.

**Action:** Repeat later; check the VPN.

## SPEED-CPU-BUSY

Роутер занят / Router is busy

**RU:** Процессор роутера занят, поэтому тест отложен, чтобы не мешать трафику.

**EN:** The router’s processor is busy, so the test is postponed to avoid disturbing the traffic.

**Что делать:** Попробуйте позже.

**Action:** Try later.

## SPEED-TRAFFIC-UNKNOWN

Трафик неизвестен / Traffic unknown

**RU:** Программа не может определить, занят ли VPN, поэтому не тестирует его.

**EN:** The program cannot tell whether the VPN is busy, so it does not test it.

**Что делать:** Дождитесь новых измерений.

**Action:** Wait for new measurements.

## SPEED-SWITCH-IN-PROGRESS

Идёт переключение / A switch is running

**RU:** Пока маршрут переключается, тест скорости не идёт.

**EN:** No speed test runs while the route is being switched.

**Что делать:** Дождитесь окончания переключения.

**Action:** Wait until the switch ends.

## SPEED-PROFILES

Сервер не выбран / No server chosen

**RU:** Для теста скорости нужен хотя бы один подключённый сервер.

**EN:** The speed test needs at least one connected server.

**Что делать:** Выберите подключённые серверы.

**Action:** Choose connected servers.

## SPEED-PROFILES-CHANGED

Список серверов изменился / Server list changed

**RU:** Серверы изменились после вашего выбора.

**EN:** The servers changed after you chose them.

**Что делать:** Выберите заново.

**Action:** Choose again.

## SPEED-CONFIG-LIMIT

Лимит превышен / Limit exceeded

**RU:** Тест превысил бы заданный вами бюджет или суточный лимит.

**EN:** The test would exceed the budget or daily limit you set.

**Что делать:** Увеличьте лимит под таблицей или проверьте позже.

**Action:** Raise the limit below the table or test later.

## AUTO-OPTIONS-NOT-CLEARED

Настройки Auto не удалось сбросить / Auto settings could not be reset

**RU:** Программа остановила Auto, но не смогла сбросить собственные настройки окна теста, потому что на роутере есть другие несохранённые изменения.

**EN:** The program stopped Auto but could not clear its own test-window settings because other unsaved router changes exist.

**Что делать:** Откройте несохранённые изменения роутера и примените либо отмените их; затем ещё раз нажмите «Стоп» в блоке Auto. Auto сам не запустится: остановка зафиксирована.

**Action:** Open the router’s unsaved changes and apply or revert them; then press Stop in the Auto card once more. Auto does not restart by itself: the stop is latched.

## BOARD-OVERSIZE

Данные о плате роутера слишком велики / Router board data too big

**RU:** Описание платы роутера больше, чем принимает программа, поэтому оно не прочитано.

**EN:** The router’s board description was bigger than the program accepts, so it was not read.

**Что делать:** Обратитесь в поддержку с кодом; ничего не менялось.

**Action:** Contact support with the code; nothing was changed.

## CA-BUNDLE

Нет пакета сертификатов / Certificates package missing

**RU:** На роутере нет набора сертификатов, поэтому защищённые (HTTPS) проверки и Telegram работать не могут.

**EN:** The router has no certificate bundle, so secure (HTTPS) checks and Telegram cannot work.

**Что делать:** Установите ca-bundle (opkg install ca-bundle).

**Action:** Install ca-bundle (opkg install ca-bundle).

## LUCI-CACHE-ROOT

Папка кэша страниц неверна / Page cache folder is wrong

**RU:** При обновлении программа не смогла безопасно очистить кэш страниц LuCI.

**EN:** During an upgrade the program could not safely clear LuCI’s page cache.

**Что делать:** Выйдите из LuCI и войдите снова, затем Ctrl+F5.

**Action:** Sign out of LuCI and in again, then Ctrl+F5.

## PYTHON-39-MINIMUM

Python слишком старый / Python is too old

**RU:** Программе нужен Python 3.9 или новее на роутере.

**EN:** The program needs Python 3.9 or newer on the router.

**Что делать:** Используйте прошивку с Python 3.9+ (в GL.iNet 4.11.0 он есть).

**Action:** Use a firmware with Python 3.9+ (GL.iNet 4.11.0 has it).

## SPEED-WORKER-TIMEOUT

Тест шёл слишком долго / Test took too long

**RU:** Тест не закончился вовремя и был остановлен.

**EN:** The test did not finish in time and was stopped.

**Что делать:** Повторите; попробуйте меньшую длительность.

**Action:** Repeat; try a shorter duration.

## PAIR-WATCHING

Auto наблюдает за обоими каналами / Auto is watching both channels

**RU:** Обычное рабочее состояние. Трафик идёт через рабочий канал, второй проверяется в фоне, и Auto готов сам переключиться, если рабочий канал откажет.

**EN:** Normal working state. Traffic goes through the channel that works, the other one is checked in the background, and Auto is ready to switch by itself if the working channel fails.

**Что делать:** Делать ничего не нужно, это нормально.

**Action:** Nothing to do, this is normal.

## PAIR-WAITING-PROBES

Auto собирает первые проверки / Auto is collecting the first checks

**RU:** Auto только что запущен и собирает первые свежие проверки обоих каналов (обычно до 3 минут). Пока их нет, он не переключает.

**EN:** Auto has just started and is collecting the first fresh checks of both channels (usually up to 3 minutes). It does not switch before they arrive.

**Что делать:** Подождите несколько минут: лампа сама станет зелёной.

**Action:** Wait a few minutes; the lamp turns green by itself.

## PAIR-CONNECTING

Подключаю второй канал / Connecting the second channel

**RU:** Auto поднимает VPN-каналы, за которыми ему нужно следить. Это короткий шаг, поэтому лампа жёлтая.

**EN:** Auto is bringing up the VPN channels it needs to watch. This is a short step, so the lamp is yellow.

**Что делать:** Подождите минуту. Если длится дольше 5 минут, проверьте оба VPN-профиля в роутере.

**Action:** Wait a minute. If it lasts longer than 5 minutes, check both VPN profiles in the router.

## PAIR-CLEANUP

Привожу маршрут в порядок / Putting the route back in order

**RU:** Auto останавливает или восстанавливает VPN-каналы и проверяет, что исходный маршрут на месте. Короткий шаг, лампа жёлтая.

**EN:** Auto is stopping or restoring the VPN channels and checking that the original route is back. Short step, yellow lamp.

**Что делать:** Подождите минуту; не нажимайте Start и Stop повторно.

**Action:** Wait a minute; do not press Start or Stop again.

## PAIR-WAITING-VENDOR

Жду данные VPN от роутера / Waiting for the router VPN data

**RU:** Роутер пока не отдал текущее состояние своих VPN, поэтому Auto не может оценить каналы. Лампа серая: программа ждёт роутер, это не доказанный отказ VPN.

**EN:** The router did not give the current state of its own VPN yet, so Auto cannot judge the channels. The lamp is grey: the program is waiting for the router, this is not a proven VPN failure.

**Что делать:** Подождите минуту. Если не проходит, откройте VPN-страницу роутера и проверьте, что профили включены.

**Action:** Wait a minute. If it stays, open the VPN page of the router and check that the profiles are on.

## PAIR-MANUAL-HOLD-RESERVE

Резерв выбран вручную; Auto продолжает наблюдать / Reserve chosen manually; Auto keeps watching

**RU:** Вы сами перевели трафик на резерв. Auto остаётся включённым и наблюдает: пока резерв работает, трафик остаётся на нём и сам на основной не возвращается. Если резерв откажет, Auto сам переведёт трафик на другой канал.

**EN:** You switched traffic to the reserve yourself. Auto is still on and keeps watching: while the reserve works, traffic stays on it and does not return to the primary automatically. If the reserve fails, Auto moves traffic to the other channel by itself.

**Что делать:** Делать ничего не нужно. Чтобы вернуться, переключите на основной канал вручную.

**Action:** Nothing to do. To go back, switch to the primary channel manually.

## PAIR-MANUAL-HOLD-PRIMARY

Основной выбран вручную; Auto продолжает наблюдать / Primary chosen manually; Auto keeps watching

**RU:** Вы сами выбрали основной канал. Auto остаётся включённым и наблюдает: пока основной работает, трафик остаётся на нём. Если он откажет, Auto сам переведёт трафик на резерв.

**EN:** You chose the primary channel yourself. Auto is still on and keeps watching: traffic stays on the primary while it works. If it fails, Auto moves traffic to the reserve by itself.

**Что делать:** Делать ничего не нужно, это нормально.

**Action:** Nothing to do, this is normal.

## PAIR-MANUAL-HOLD-UNVERIFIED

Ручной выбор не удалось подтвердить / Manual choice could not be confirmed

**RU:** Auto не смог доказать, что выбранный вами вручную канал по-прежнему несёт трафик, поэтому снял ручной выбор и снова работает обычным образом.

**EN:** Auto could not prove that the channel you chose manually is still the one carrying traffic, so it dropped the manual choice and works normally again.

**Что делать:** Посмотрите в блоке Auto текущий канал и при необходимости выберите заново.

**Action:** Check the Auto card for the current channel and choose again if needed.

## PAIR-MANUAL-RECOVERED

Прерванное ручное переключение снято / Interrupted manual switch cleared

**RU:** Запрос на ручное переключение был прерван (например, перезапуском). Он не повторялся, поэтому канал может отличаться от выбранного вами.

**EN:** A manual switch request was interrupted (for example by a restart). It was not repeated, so the channel may be different from what you asked for.

**Что делать:** Посмотрите текущий канал в блоке Auto и повторите ручной выбор, если он ещё нужен.

**Action:** Look at the current channel in the Auto card and repeat the manual choice if you still want it.

## PAIR-MANUAL-BUSY

Уже идёт другое переключение / Another switch is in progress

**RU:** Прямо сейчас идёт переключение, поэтому новый ручной запрос не принят.

**EN:** A switch is running right now, so the new manual request was not accepted.

**Что делать:** Дождитесь окончания текущего переключения (около минуты) и повторите.

**Action:** Wait for the current switch to finish (about a minute) and try again.

## PAIR-MANUAL-COOLDOWN

Короткая пауза между ручными переключениями / Short pause between manual switches

**RU:** Ручные переключения ограничены по частоте, чтобы не раскачивать связь. Запрос не выполнен.

**EN:** Manual switches are limited in frequency, so the line is not shaken by repeated switching. The request was not executed.

**Что делать:** Подождите минуту и повторите.

**Action:** Wait a minute and try again.

## PAIR-MANUAL-EXPIRED

Ручной запрос устарел / Manual request expired

**RU:** Ручной запрос ждал дольше 60 секунд, поэтому был отменён, чтобы не выполнять старую команду.

**EN:** The manual request waited longer than 60 seconds before it could be run, so it was cancelled to avoid doing an old command.

**Что делать:** Нажмите ручное переключение ещё раз, если оно ещё нужно.

**Action:** Press the manual switch again if you still need it.

## PAIR-MANUAL-FIELDS

Ручной запрос составлен неверно / Manual request was malformed

**RU:** Роутер отклонил ручной запрос с неполными или неожиданными полями. Ничего не изменено.

**EN:** The router refused a manual request whose fields were incomplete or unexpected. Nothing was changed.

**Что делать:** Обновите страницу (Ctrl+F5) и повторите.

**Action:** Reload the page (Ctrl+F5) and try again.

## PAIR-MANUAL-NOT-AVAILABLE

Ручное переключение сейчас недоступно / Manual switch is not available now

**RU:** Роутер сейчас не может выполнить это ручное переключение (например, выбранный канал уже текущий или Auto не готов).

**EN:** The router cannot do this manual switch at the moment (for example the current channel is already the chosen one, or Auto is not ready).

**Что делать:** Откройте блок Auto: там указано, чего не хватает. Повторите, когда он будет готов.

**Action:** Open the Auto card: it lists what is missing. Try again when it is ready.

## PAIR-MANUAL-REQUEST-UNCONFIRMED

Ручной запрос не подтверждён / Manual request not confirmed

**RU:** Роутер не подтвердил, что принял ручной запрос. Не считайте его выполненным.

**EN:** The router did not confirm that it accepted the manual request. Do not assume it was done.

**Что делать:** Подождите минуту, посмотрите текущий канал в блоке Auto и при необходимости повторите.

**Action:** Wait a minute, look at the current channel in the Auto card, then repeat if needed.

## PAIR-MANUAL-STALE

Данные роутера устарели для ручного переключения / Router data is too old for a manual switch

**RU:** Последнее состояние роутера старше 30 секунд, поэтому ручное переключение недоступно до свежих данных.

**EN:** The newest state of the router is older than 30 seconds, so the manual switch is not offered until fresh data arrives.

**Что делать:** Подождите следующего обновления (несколько секунд).

**Action:** Wait for the next refresh (a few seconds).

## PAIR-MANUAL-STATE-UNVERIFIED

Не удаётся подтвердить состояние для ручного переключения / Cannot confirm the state for a manual switch

**RU:** Auto не смог прочитать или проверить состояние, нужное для ручного переключения. Ничего не изменено.

**EN:** Auto could not read or verify the state it needs for a manual switch. Nothing was changed.

**Что делать:** Подождите минуту и повторите. Если повторяется, сохраните код и загляните в «Помощь».

**Action:** Wait a minute and try again. If it repeats, keep the code and see Help.

## PAIR-MANUAL-TARGET-UNHEALTHY

Выбранный канал не проходит проверки / The chosen channel does not pass its checks

**RU:** Ручное переключение на канал, который сейчас нездоров, отклонено, чтобы вы не потеряли связь.

**EN:** A manual switch to a channel that is not healthy right now was refused, so you do not lose the connection.

**Что делать:** Выберите другой канал или подождите, пока выбранный станет зелёным.

**Action:** Choose the other channel, or wait until the chosen one is green.

## PAIR-MANUAL-UNCONFIRMED

Ручное переключение не подтверждено / Manual switch not confirmed

**RU:** Роутер начал ручное переключение, но не смог доказать результат. Канал, несущий трафик, не подтверждён.

**EN:** The router started the manual switch but could not prove its result. The channel carrying traffic is not verified.

**Что делать:** Не повторяйте сразу. Подождите минуту: Auto продолжает наблюдать и сам исправит отказавший канал.

**Action:** Do not repeat at once. Wait a minute; Auto keeps watching and will fix a failed channel itself.

## PAIR-RATE-LIMIT

Слишком много переключений; Auto делает паузу / Too many switches; Auto is pausing

**RU:** Auto ограничивает частоту переключений, чтобы не раскачивать нестабильную связь. До конца паузы трафик остаётся на текущем канале.

**EN:** Auto limits how often it switches so an unstable line is not shaken further. Traffic stays on the current channel until the pause ends.

**Что делать:** Делать ничего не нужно. Если переключений много, проверьте оба VPN-сервера по «Помощи».

**Action:** Nothing to do. If switching is frequent, check both VPN servers in Help.

## PAIR-MODE-NOT-CONFIGURED

Авторежим двух каналов не настроен / Two-channel Auto is not set up

**RU:** Основной и резервный каналы не выбраны и не сохранены вместе, поэтому Auto двух каналов не может запуститься или переключаться вручную.

**EN:** The primary and reserve channels are not both chosen and saved, so the two-channel Auto cannot start or switch manually.

**Что делать:** Выберите основной и резервный VPN в настройках и сохраните пару.

**Action:** Choose the primary and the reserve VPN in Settings and save the pair.

## PAIR-PLATFORM-UNVERIFIED

Платформа роутера не подтверждена / Router platform not confirmed

**RU:** Auto не смог подтвердить, что эта модель роутера и прошивка поддерживаются для непрерывного переключения, поэтому не запускается.

**EN:** Auto could not confirm that this router model and firmware are supported for continuous switching, so it does not run.

**Что делать:** Посмотрите в «Готовности системы» точный недостающий пункт.

**Action:** Check System readiness for the exact missing item.

## PAIR-READINESS-CHANGED

Готовность изменилась во время работы Auto / Readiness changed while Auto was working

**RU:** Изменилось то, на что опирается Auto (состояние роутера или подготовка), поэтому он остановился и перепроверит перед продолжением.

**EN:** Something Auto relies on (router state or preparation) changed, so it stopped and will re-check before continuing.

**Что делать:** Подождите минуту; если Auto не перезапустился, нажмите Start.

**Action:** Wait a minute; if Auto does not restart, press Start.

## PAIR-STOPPED

Auto остановлен, маршрут восстановлен / Auto was stopped and the route restored

**RU:** Auto выключен, исходный маршрут возвращён. Это обычный результат нажатия Stop.

**EN:** Auto was switched off and the original route was put back. This is the normal result of pressing Stop.

**Что делать:** Делать ничего не нужно. Нажмите Start, когда Auto снова понадобится.

**Action:** Nothing to do. Press Start when you want Auto again.

## PAIR-SYSTEM-001

Неожиданная внутренняя ошибка Auto / Unexpected internal error in Auto

**RU:** Auto встретил ошибку без отдельного кода. Он безопасно остановился; сама по себе эта ошибка маршрут не меняет.

**EN:** Auto met an error that has no specific code. It stopped safely; the route is not changed by this error alone.

**Что делать:** Нажмите Start ещё раз. Если повторяется, сохраните журнал и время события для разработчика.

**Action:** Press Start again. If it repeats, keep the journal and the time of the event for the maintainer.

## PAIR-BUDGET-UNVERIFIED

Запись о лимите переключений нечитаема / Switch limit record is unreadable

**RU:** Auto не может прочитать сохранённый счётчик недавних переключений, поэтому не переключает, пока не докажет, что лимит соблюдён.

**EN:** Auto cannot read its saved count of recent switches, so it does not switch until it can prove the limit is respected.

**Что делать:** Подождите: запись восстановится сама. Если не проходит, нажмите Stop и Start.

**Action:** Wait; the record rebuilds itself. If it stays, press Stop and Start.

## PAIR-CONFIG-UNVERIFIED

Сохранённые настройки Auto не подтверждены / Saved Auto settings not confirmed

**RU:** Сохранённую пару или настройки Auto не удалось прочитать и проверить.

**EN:** The saved pair or Auto settings could not be read back and verified.

**Что делать:** Откройте настройки, проверьте основной и резервный и сохраните снова.

**Action:** Open Settings, check the primary and reserve, and save again.

## PAIR-INTENT-UNVERIFIED

Запись о незавершённом переключении не подтверждена / Unfinished switch record not confirmed

**RU:** Запись о переключении в процессе не удалось проверить, поэтому Auto не продолжает его на веру.

**EN:** The record of a switch in progress could not be verified, so Auto does not continue it on trust.

**Что делать:** Подождите минуту; если не проходит, см. PAIR-RECOVERY-REQUIRED.

**Action:** Wait a minute; if it stays, see PAIR-RECOVERY-REQUIRED.

## PAIR-NETWORK-UNVERIFIED

Состояние сети не подтверждено / Network state not confirmed

**RU:** Auto не смог прочитать сетевые настройки двух каналов, поэтому не действует.

**EN:** Auto could not read the network settings of the two channels, so it does not act.

**Что делать:** Подождите минуту и нажмите Start снова.

**Action:** Wait a minute and press Start again.

## PAIR-NETWORK-WRITE-FAILED

Не удалось записать сетевые настройки / Could not write the network settings

**RU:** Роутер отказался сохранить сетевые настройки, нужные Auto. Прежние настройки остаются.

**EN:** The router refused to save the network settings Auto needs. The previous settings stay.

**Что делать:** Нажмите Start снова через минуту. Если повторяется, проверьте свободное место и страницу роутера.

**Action:** Press Start again after a minute. If it repeats, check free space and the router page.

## PAIR-NETWORK-WRITE-UNVERIFIED

Запись сетевых настроек не подтверждена / Network settings write not confirmed

**RU:** Auto записал сетевые настройки, но не смог прочитать их обратно, поэтому не полагается на них.

**EN:** Auto wrote network settings but could not read them back to prove them, so it does not rely on them.

**Что делать:** Нажмите Start снова. Если повторяется, сохраните код для разработчика.

**Action:** Press Start again. If it repeats, keep the code for the maintainer.

## PAIR-PROFILE-STOP-UNVERIFIED

Не удалось подтвердить остановку лишнего VPN / Could not confirm the extra VPN stopped

**RU:** При остановке Auto не смог доказать, что неиспользуемый VPN-клиент выключен.

**EN:** When stopping, Auto could not prove that the unused VPN client is off.

**Что делать:** Проверьте VPN-страницу роутера и выключите неиспользуемый профиль.

**Action:** Check the VPN page of the router and switch the unused profile off.

## RESPONSE-COMPARE-UNAVAILABLE

Сравнение способов недоступно / Method comparison is unavailable

**RU:** Сохранённое сравнение всех способов отклика сейчас нельзя использовать. Переключение и выбранный способ отклика не затронуты.

**EN:** The saved comparison of all response methods cannot be used right now. Switching and the chosen response method are not affected.

**Что делать:** Делать ничего не нужно. Если не проходит, выключите и снова включите «замерять все способы».

**Action:** Nothing to do. Turn “measure all methods” off and on again if it stays.

## RESPONSE-COMPARE-WRITE-FAILED

Сравнение способов не сохранено / Method comparison was not saved

**RU:** Роутер не смог сохранить последнее сравнение способов отклика (например, мало места). Последняя хорошая копия остаётся.

**EN:** The router could not save the latest comparison of response methods (for example not enough free space). The last good copy stays.

**Что делать:** Освободите место на роутере или подождите; Auto и лампы не затронуты.

**Action:** Free some space on the router or wait; Auto and the lamps are not affected.

## RESPONSE-COMPARE-SCHEMA

Файл сравнения способов в неверном виде / Method comparison file has the wrong form

**RU:** Сохранённое сравнение имеет неожиданную структуру и проигнорировано.

**EN:** The saved comparison has an unexpected structure and was ignored.

**Что делать:** Делать ничего не нужно: новое сравнение соберётся само.

**Action:** Nothing to do; a new comparison is collected by itself.

## RESPONSE-COMPARE-SIZE

Файл сравнения способов слишком велик / Method comparison file is too large

**RU:** Сохранённое сравнение больше допустимого и проигнорировано.

**EN:** The saved comparison is bigger than allowed and was ignored.

**Что делать:** Делать ничего не нужно: оно пересоберётся само.

**Action:** Nothing to do; it is rebuilt by itself.

## RESPONSE-COMPARE-VALUE

В сравнении способов неверное значение / Method comparison has a wrong value

**RU:** Одно сохранённое значение сравнения вне допустимого диапазона, файл проигнорирован.

**EN:** One saved value of the comparison is outside the allowed range and the file was ignored.

**Что делать:** Делать ничего не нужно: оно пересоберётся само.

**Action:** Nothing to do; it is rebuilt by itself.

## PING-HISTORY

Проблема истории пинга / Ping history problem

**RU:** Сохранённую историю пинга нельзя использовать. Текущие пинги и переключение продолжаются.

**EN:** The saved ping history could not be used. Current pings and switching continue.

**Что делать:** Делать ничего не нужно: история соберётся заново.

**Action:** Nothing to do; the history is collected again.

## LATENCY-HISTORY-UNAVAILABLE

История задержки недоступна / Delay history is unavailable

**RU:** Сохранённую историю задержки сейчас нельзя прочитать. Графики могут какое-то время быть пустыми; текущие показания и Auto не затронуты.

**EN:** The saved delay history cannot be read right now. The charts may be empty for a while; current readings and Auto are not affected.

**Что делать:** Делать ничего не нужно: она заполнится снова сама.

**Action:** Nothing to do; it fills again by itself.

## LATENCY-HISTORY-WRITE-FAILED

История задержки не сохранена / Delay history was not saved

**RU:** Роутер не смог сохранить новые замеры задержки. Прежние сохранённые данные остаются.

**EN:** The router could not save the newest delay readings. Older saved data stays.

**Что делать:** Если повторяется, освободите место на роутере.

**Action:** Free some space on the router if it repeats.

## LIFECYCLE-READY

Проверка перед обновлением пройдена / Ready for an upgrade check passed

**RU:** Auto выключен, исходный маршрут на месте, поэтому обновление или остановка безопасны.

**EN:** Auto is off and the original route is in place, so an upgrade or stop is safe.

**Что делать:** Делать ничего не нужно, это хороший результат.

**Action:** Nothing to do, this is a good result.

## LIFECYCLE-UPGRADE-READY

Готово к обновлению / Ready to upgrade

**RU:** Все проверки перед обновлением пройдены.

**EN:** All checks before an upgrade passed.

**Что делать:** Можно продолжать обновление.

**Action:** You can continue with the upgrade.

## LIFECYCLE-AUTO-DISABLED

Auto выключен на время обновления / Auto was switched off for the upgrade

**RU:** Перед обновлением программа выключила Auto и проверила маршрут.

**EN:** Before the upgrade the program switched Auto off and checked the route.

**Что делать:** После обновления нажмите Start, когда Auto снова понадобится.

**Action:** After the upgrade press Start when you want Auto again.

## LIFECYCLE-AUTO-DISABLE-FAILED

Не удалось выключить Auto / Could not switch Auto off

**RU:** Программа не смогла доказать, что Auto выключен, поэтому шаг обновления остановлен.

**EN:** The program could not prove that Auto is off, so the upgrade step stopped.

**Что делать:** Нажмите Stop в блоке Auto, дождитесь исходного маршрута и повторите.

**Action:** Press Stop in the Auto card, wait for the original route, and repeat.

## LIFECYCLE-ACTION

Неизвестное действие службы / Unknown service action

**RU:** Скрипт службы вызван с неизвестным действием. Ничего не изменено.

**EN:** The service script was called with an action it does not know. Nothing was changed.

**Что делать:** Используйте обычную команду установки или обновления.

**Action:** Use the normal install or upgrade command.

## LIFECYCLE-CONFIG-UNVERIFIED

Настройки не подтверждены перед обновлением / Settings not confirmed before the upgrade

**RU:** Сохранённые настройки не удалось прочитать и проверить, поэтому шаг обновления не продолжен.

**EN:** The saved settings could not be read and checked, so the upgrade step did not go on.

**Что делать:** Подождите минуту и повторите. Если не проходит, сохраните код.

**Action:** Wait a minute and repeat. Keep the code if it stays.

## LIFECYCLE-CONTROL-BUSY

Выполняется другое управляющее действие / Another control action is running

**RU:** Управляющая блокировка занята другим действием, поэтому шаг подождал и отказался.

**EN:** The control lock is held by another action, so this step waited and then gave up.

**Что делать:** Дождитесь окончания другого действия и повторите.

**Action:** Wait for the other action to finish and repeat.

## LIFECYCLE-CONTROL-UNVERIFIED

Состояние управления не подтверждено / Control state not confirmed

**RU:** Сохранённое состояние управления не удалось проверить.

**EN:** The saved control state could not be verified.

**Что делать:** Подождите минуту и повторите.

**Action:** Wait a minute and repeat.

## LIFECYCLE-JOURNAL-ACTIVE

Переключение ещё не завершено / A switch is still unfinished

**RU:** Журнал переключений показывает незавершённое переключение, поэтому обновление ждёт.

**EN:** The switch journal shows an unfinished switch, so the upgrade waits.

**Что делать:** Дождитесь окончания переключения или восстановления и повторите.

**Action:** Wait until the switch ends or recovery completes, then repeat.

## LIFECYCLE-JOURNAL-UNVERIFIED

Журнал переключений не подтверждён / Switch journal not confirmed

**RU:** Журнал переключений не удалось проверить, поэтому шаг обновления остановлен.

**EN:** The switch journal could not be verified, so the upgrade step stopped.

**Что делать:** Сохраните журнал и обратитесь к разработчику; не удаляйте его.

**Action:** Keep the journal and ask the maintainer; do not delete it.

## LIFECYCLE-PENDING-UCI-CHANGES

Есть неприменённые настройки роутера / Unsaved router settings exist

**RU:** В роутере есть изменённые, но не применённые настройки, поэтому шаг обновления остановлен.

**EN:** The router has settings that are changed but not applied yet, so the upgrade step stopped.

**Что делать:** Примените или отмените ожидающие настройки в интерфейсе роутера и повторите.

**Action:** Apply or discard the pending settings in the router interface and repeat.

## LIFECYCLE-STATE-UNVERIFIED

Состояние программы не подтверждено / Program state not confirmed

**RU:** Текущее состояние программы не удалось проверить перед обновлением.

**EN:** The current state of the program could not be verified before the upgrade.

**Что делать:** Подождите минуту и повторите.

**Action:** Wait a minute and repeat.

## PREPARATION-VERIFIED

Подготовка роутера подтверждена / Router preparation verified

**RU:** Сохранённая подготовка роутера проверена и верна.

**EN:** The saved preparation of the router was checked and is correct.

**Что делать:** Делать ничего не нужно, это хороший результат.

**Action:** Nothing to do, this is a good result.

## PREPARATION-UNVERIFIED

Подготовка роутера не подтверждена / Router preparation not confirmed

**RU:** Хотя бы одно условие подготовки роутера не удалось доказать.

**EN:** At least one prerequisite of the router preparation could not be proven.

**Что делать:** Откройте «Готовность системы» → «Подготовка роутера» и посмотрите, какого пункта не хватает.

**Action:** Open System readiness → Router preparation and read which item is missing.

## PREPARATION-STOP-AUTO-FIRST

Остановите Auto перед сменой подготовки / Stop Auto before changing the preparation

**RU:** Подготовку можно менять только при выключенном Auto, чтобы не мешать работающему Auto.

**EN:** The preparation can be changed only while Auto is off, so a running Auto is not disturbed.

**Что делать:** Нажмите Stop в блоке Auto, дождитесь исходного маршрута и повторите.

**Action:** Press Stop in the Auto card, wait for the original route, then repeat.

## PREPARATION-STALE-REVIEW

Проверка устарела / The review is out of date

**RU:** Роутер изменился после вашего просмотра подготовки, поэтому действие отклонено.

**EN:** The router changed after you reviewed the preparation, so the action was refused.

**Что делать:** Откройте подготовку заново, прочитайте свежую проверку и подтвердите снова.

**Action:** Open the preparation again, read the fresh review, and confirm again.

## PREPARATION-EXTERNAL-CHANGE

Настройки роутера изменены снаружи / Router settings changed from outside

**RU:** Что-то другое изменило настройку роутера, на которую опирается подготовка.

**EN:** Something else changed a router setting that the preparation relies on.

**Что делать:** Откройте подготовку, посмотрите, что изменилось, и примените снова, если согласны.

**Action:** Open the preparation, review what changed, and apply it again if you agree.

## PREPARATION-PENDING-OR-UNREADABLE

Настройки роутера ожидают применения или нечитаемы / Router settings pending or unreadable

**RU:** В роутере есть неприменённые изменения или настройку не удалось прочитать, поэтому подготовка не продолжается.

**EN:** The router has unapplied changes or the setting could not be read, so the preparation does not go on.

**Что делать:** Примените или отмените ожидающие изменения в интерфейсе роутера и повторите.

**Action:** Apply or discard pending changes in the router interface and repeat.

## PREPARATION-WRITE-UNCONFIRMED

Запись подготовки не подтверждена / Preparation write not confirmed

**RU:** Настройка подготовки записана, но не удалось прочитать её обратно и доказать.

**EN:** A preparation setting was written but could not be read back and proven.

**Что делать:** Проверьте подготовку заново, прежде чем полагаться на неё.

**Action:** Review the preparation again before relying on it.

## PREPARATION-AUTOLOAD-UNVERIFIED

Автозагрузка не подтверждена / Startup loading not confirmed

**RU:** Не доказано, что нужный модуль загружается при старте роутера.

**EN:** It was not proven that the needed module is loaded at router start.

**Что делать:** Посмотрите «Готовность системы» → «Подготовка роутера».

**Action:** Review System readiness → Router preparation.

## PREPARATION-BACKUP-UNVERIFIED

Резервная копия не подтверждена / Backup copy not confirmed

**RU:** Резервную копию исходных настроек не удалось доказать, поэтому изменение не сделано.

**EN:** The backup of the original settings could not be proven, so the change was not made.

**Что делать:** Повторите подготовку через минуту; если не проходит, сохраните код.

**Action:** Repeat the preparation after a minute; keep the code if it stays.

## PREPARATION-BINDING-UNVERIFIED

Подготовка не соответствует этому роутеру / Preparation does not match this router

**RU:** Сохранённая подготовка относится к другому состоянию или версии роутера.

**EN:** The saved preparation belongs to a different router state or version.

**Что делать:** Запустите проверку подготовки заново.

**Action:** Run the preparation review again.

## PREPARATION-BOOT-UNVERIFIED

Запуск при загрузке не подтверждён / Start-at-boot not confirmed

**RU:** Не доказано, что программа запускается при загрузке роутера.

**EN:** It was not proven that the program starts when the router boots.

**Что делать:** Посмотрите «Готовность системы» → «Подготовка роутера».

**Action:** Review System readiness → Router preparation.

## PREPARATION-FIELDS

Запрос подготовки составлен неверно / Preparation request was malformed

**RU:** В запросе подготовки были лишние или недостающие поля, он отклонён. Ничего не изменено.

**EN:** The preparation request had missing or extra fields and was refused. Nothing was changed.

**Что делать:** Обновите страницу (Ctrl+F5) и повторите.

**Action:** Reload the page (Ctrl+F5) and repeat.

## PREPARATION-FILE-UNVERIFIED

Файл программы не подтверждён / A program file is not confirmed

**RU:** Файл подготовки отсутствует или отличается от ожидаемого.

**EN:** A file of the preparation is missing or differs from the expected one.

**Что делать:** Переустановите пакет и повторите проверку.

**Action:** Reinstall the package, then repeat the review.

## PREPARATION-FIREWALL-UNVERIFIED

Правила файрвола не подтверждены / Firewall rules not confirmed

**RU:** Состояние файрвола, нужное для безопасной работы, не удалось доказать.

**EN:** The firewall state needed for safe work could not be proven.

**Что делать:** Посмотрите «Готовность системы» → «Подготовка роутера».

**Action:** Review System readiness → Router preparation.

## PREPARATION-HISTORY-LIMIT

Слишком много записей подготовки / Too many preparation records

**RU:** Журнал прошлых действий подготовки достиг предела; новые действия не принимаются, пока он не очищен.

**EN:** The record of past preparation actions reached its limit; no further action is accepted until it is cleaned.

**Что делать:** Сохраните код и попросите разработчика очистить журнал.

**Action:** Keep the code and ask the maintainer to clean the record.

## PREPARATION-HNAT-UNVERIFIED

Аппаратное ускорение не подтверждено выключенным / Hardware acceleration not confirmed off

**RU:** Не доказано, что аппаратное ускорение роутера выключено, а оно нужно Auto для безопасного переключения.

**EN:** It was not proven that the router hardware acceleration is off, which Auto needs for safe switching.

**Что делать:** Посмотрите «Готовность системы» → «Подготовка роутера».

**Action:** Review System readiness → Router preparation.

## PREPARATION-PLATFORM-UNVERIFIED

Модель роутера не подтверждена / Router model not confirmed

**RU:** Модель или прошивка этого роутера не подтверждены для подготовки.

**EN:** This router model or firmware was not confirmed for the preparation.

**Что делать:** Посмотрите «Готовность системы» для точного пункта.

**Action:** Check System readiness for the exact item.

## PREPARATION-VALUE-UNVERIFIED

Значение настройки не подтверждено / A setting value is not confirmed

**RU:** У настройки подготовки неожиданное значение.

**EN:** A setting of the preparation has a value that was not expected.

**Что делать:** Запустите проверку подготовки заново.

**Action:** Run the preparation review again.

## FAULT-CERTIFICATE-STALE

Разрешение теста сбоя устарело / Failure test approval expired

**RU:** Разрешение на тест сбоя устарело или не совпадает с текущим состоянием, поэтому тест не запущен.

**EN:** The approval for the failure test is old or does not match the current state, so the test did not start.

**Что делать:** Подготовьте тест заново на странице «Тесты».

**Action:** Prepare the test again from the Tests page.

## FAULT-CLAIM-STALE

Запрос теста сбоя устарел / Failure test request expired

**RU:** Запрос теста сбоя ждал слишком долго и был сброшен.

**EN:** The failure test request waited too long and was dropped.

**Что делать:** Запустите тест заново.

**Action:** Start the test again.

## FAULT-COMMAND-UNCONFIRMED

Команда теста не подтверждена / Test command not confirmed

**RU:** Роутер не подтвердил команду теста сбоя. Не считайте тест запущенным.

**EN:** The router did not confirm the failure test command. Do not assume the test is running.

**Что делать:** Проверьте на странице «Тесты», что сбой выключен и маршрут обычный.

**Action:** Check that the fault is off in the Tests page and the route is normal.

## FAULT-CONTROL-CHANGED

Управление тестом изменилось / Test control changed meanwhile

**RU:** Другое действие изменило состояние управления, пока готовился тест сбоя.

**EN:** Another action changed the control state while the failure test was being prepared.

**Что делать:** Повторите тест с начала.

**Action:** Repeat the test from the start.

## FAULT-IDENTITY-GONE

Проверяемый VPN исчез / Tested VPN disappeared

**RU:** VPN, выбранный для теста сбоя, больше не найден.

**EN:** The VPN that was chosen for the failure test is no longer present.

**Что делать:** Выберите VPN заново и повторите.

**Action:** Choose the VPN again and repeat.

## FAULT-IDENTITY-UNVERIFIED

Проверяемый VPN не подтверждён / Tested VPN not confirmed

**RU:** Не доказано, на какой VPN действует тест сбоя, поэтому он не запущен.

**EN:** It was not proven which VPN the failure test affects, so it was not run.

**Что делать:** Дождитесь свежих наблюдений и повторите.

**Action:** Wait for fresh observations and repeat.

## FAULT-START-UNCONFIRMED

Запуск теста не подтверждён / Test start not confirmed

**RU:** Роутер не подтвердил, что тест сбоя запущен.

**EN:** The router did not confirm that the failure test started.

**Что делать:** Проверьте страницу «Тесты»; остановите тест, если он показан как идущий.

**Action:** Check the Tests page; stop the test if it shows as running.

## RPC-RATE-LIMIT

Слишком много запросов, подождите / Too many requests, wait a moment

**RU:** Страница обращалась к роутеру слишком часто, поэтому запрос отклонён для защиты роутера. Ничего не изменено.

**EN:** The page asked the router too often, so this request was refused to protect the router. Nothing was changed.

**Что делать:** Подождите несколько секунд и повторите.

**Action:** Wait a few seconds and repeat.

## RPC-INPUT-INVALID

В запросе неверное значение / Request has a wrong value

**RU:** Роутер отклонил запрос со значением вне допустимого вида или размера. Ничего не изменено.

**EN:** The router refused a request whose value was outside the allowed form or size. Nothing was changed.

**Что делать:** Проверьте введённое и повторите; если не проходит, обновите страницу.

**Action:** Check what you entered and repeat; reload the page if it stays.

## RPC-UNKNOWN-METHOD

Роутер не знает такой запрос / The router does not know this request

**RU:** Страница и программа на роутере разных версий.

**EN:** The page and the program on the router are of different versions.

**Что делать:** Обновите страницу (Ctrl+F5); если не проходит, переустановите пакет.

**Action:** Reload the page (Ctrl+F5); reinstall the package if it stays.

## RPC-UNEXPECTED-ARGS

В запросе лишние данные / Request has extra data

**RU:** Роутер отклонил запрос с неожиданными полями. Ничего не изменено.

**EN:** The router refused a request with unexpected fields. Nothing was changed.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## RPC-CONFIRM-NO-PENDING

Нечего подтверждать / Nothing is waiting for confirmation

**RU:** Подтверждение пришло, но ни одно переключение его не ждёт (возможно, время вышло).

**EN:** The confirmation arrived but no switch is waiting for it (it may have expired).

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## RPC-CONFIRM-EXPIRED

Подтверждение пришло слишком поздно / Confirmation came too late

**RU:** Время подтверждения переключения вышло, поэтому подтверждение не принято.

**EN:** The time for confirming the switch is over, so the confirmation was not accepted.

**Что делать:** Делать ничего не нужно: Auto сам вернётся на безопасный маршрут.

**Action:** Nothing to do; Auto returns to a safe route by itself.

## RPC-CONFIRM-ADDRESS

Подтверждение пришло с другого адреса / Confirmation came from another address

**RU:** Подтверждение пришло не с того компьютера, который должен подтверждать.

**EN:** The confirmation did not come from the computer that is expected to confirm.

**Что делать:** Подтвердите с выбранного компьютера.

**Action:** Confirm from the chosen computer.

## RPC-CONFIRM-FIELDS

Подтверждение составлено неверно / Confirmation was malformed

**RU:** В подтверждении были лишние или недостающие поля, оно отклонено.

**EN:** The confirmation had missing or extra fields and was refused.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## RPC-CONFIRM-TRANSACTION

Подтверждение относится к другому переключению / Confirmation is for another switch

**RU:** Подтверждение не относится к переключению, которое ожидает.

**EN:** The confirmation does not belong to the switch that is waiting.

**Что делать:** Делать ничего не нужно; дождитесь текущего переключения.

**Action:** Nothing to do; wait for the current switch.

## RPC-CONFIRM-TRIAL

Подтверждение относится к другому тесту / Confirmation is for another test

**RU:** Подтверждение не относится к текущему тесту.

**EN:** The confirmation does not belong to the current trial.

**Что делать:** Повторите подтверждение для текущего теста.

**Action:** Repeat the confirmation for the current test.

## RPC-CONFIRM-UNVERIFIED

Подтверждение не проверено / Confirmation not verified

**RU:** Роутер не смог проверить подтверждение.

**EN:** The router could not verify the confirmation.

**Что делать:** Повторите через минуту.

**Action:** Repeat after a minute.

## SPEED-ADDRESS

Адрес сервера теста скорости отклонён / Speed test server address refused

**RU:** Адрес теста скорости не был публичным интернет-адресом, поэтому не использован.

**EN:** The speed test address was not a public internet address, so it was not used.

**Что делать:** Делать ничего не нужно; запустите тест заново.

**Action:** Nothing to do; try the test again.

## SPEED-AUTO-DISABLED

Тест скорости недоступен при таком состоянии Auto / Speed test needs Auto off or ready

**RU:** Тест скорости не запускается, пока состояние Auto этого не позволяет.

**EN:** The speed test is not run while Auto state does not allow it.

**Что делать:** Дождитесь окончания шага Auto и повторите.

**Action:** Wait for Auto to finish its step and repeat.

## SPEED-CANCEL-UNVERIFIED

Отмена теста не подтверждена / Test cancel not confirmed

**RU:** Не доказано, что тест скорости остановлен.

**EN:** It was not proven that the speed test stopped.

**Что делать:** Подождите минуту и проверьте, что тест не идёт.

**Action:** Wait a minute and check that the test is not running.

## SPEED-CLOCK-BACKWARD

Часы роутера пошли назад / Router clock went back

**RU:** Часы роутера скакнули назад во время теста, поэтому результат ненадёжен.

**EN:** The router clock jumped back during the test, so the result is not reliable.

**Что делать:** Повторите тест позже.

**Action:** Repeat the test later.

## SPEED-CLOCK-UNSET

Часы роутера не установлены / Router clock is not set

**RU:** Роутер ещё не знает точное время, поэтому лимиты теста скорости нельзя посчитать.

**EN:** The router does not know the real time yet, so the speed test limits cannot be counted.

**Что делать:** Подождите, пока роутер получит время из интернета.

**Action:** Wait until the router gets the time from the internet.

## SPEED-CONFIG

Настройки теста скорости вне диапазона / Speed test settings are out of range

**RU:** У настройки теста скорости недопустимое значение.

**EN:** A speed test setting has a value that is not allowed.

**Что делать:** Откройте настройки теста скорости и введите значение в допустимом диапазоне.

**Action:** Open the speed test settings and enter a value in the allowed range.

## SPEED-CONFIG-FIELDS

Настройки теста скорости составлены неверно / Speed test settings were malformed

**RU:** В настройках теста скорости были лишние или недостающие поля.

**EN:** The speed test settings had missing or extra fields.

**Что делать:** Обновите страницу (Ctrl+F5) и сохраните снова.

**Action:** Reload the page (Ctrl+F5) and save again.

## SPEED-DNS

Имя сервера теста скорости не найдено / Speed test name not resolved

**RU:** Имя сервера теста скорости не удалось разрешить через VPN.

**EN:** The speed test server name could not be resolved through the VPN.

**Что делать:** Повторите позже; если повторяется, проверьте DNS этого VPN.

**Action:** Repeat later; if it repeats check the DNS of this VPN.

## SPEED-HISTORY-CORRUPT

История скорости нечитаема / Speed history unreadable

**RU:** Сохранённые результаты скорости не удалось прочитать, они проигнорированы.

**EN:** The saved speed results could not be read and were ignored.

**Что делать:** Делать ничего не нужно: новые тесты заполнят её снова.

**Action:** Nothing to do; new tests fill it again.

## SPEED-HTTP

Сервер теста скорости ответил ошибкой / Speed test server answered with an error

**RU:** Скачивание для теста скорости завершилось ошибкой HTTP.

**EN:** The speed test download failed with an HTTP error.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## SPEED-MONITOR-UNAVAILABLE

Мониторинг недоступен для теста скорости / Monitor is not available for the speed test

**RU:** Для теста скорости нужен работающий мониторинг, он не отвечает.

**EN:** The speed test needs the running monitor, which does not answer.

**Что делать:** Запустите мониторинг и повторите.

**Action:** Start monitoring and repeat.

## SPEED-QUOTA-CORRUPT

Запись лимита теста скорости нечитаема / Speed test limit record unreadable

**RU:** Сохранённый счётчик трафика тестов скорости не удалось прочитать, поэтому тест не запускается.

**EN:** The saved count of speed test traffic could not be read, so the test is not run.

**Что делать:** Подождите: запись восстановится сама.

**Action:** Wait; the record rebuilds itself.

## SPEED-REQUEST

Запрос теста скорости неверен / Speed test request is wrong

**RU:** В запросе были неверные или лишние значения, он отклонён.

**EN:** The request had wrong or extra values and was refused.

**Что делать:** Обновите страницу (Ctrl+F5) и повторите.

**Action:** Reload the page (Ctrl+F5) and repeat.

## SPEED-RESPONSE-LIMIT

Достигнут лимит скачивания теста / Speed test download limit reached

**RU:** Тест скачал больше допустимого и был остановлен.

**EN:** The test downloaded more than allowed and was stopped.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## SPEED-SHORT-RESPONSE

Ответ сервера теста слишком короткий / Speed test answer too short

**RU:** Сервер отдал меньше данных, чем нужно для надёжного результата.

**EN:** The server gave less data than needed for a reliable result.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## SPEED-STATUS-UNAVAILABLE

Состояние теста скорости недоступно / Speed test status unavailable

**RU:** Роутер не отдал состояние теста скорости.

**EN:** The router did not give the speed test status.

**Что делать:** Обновите страницу и проверьте снова.

**Action:** Reload the page and check again.

## SPEED-SYSTEM

Системная ошибка теста скорости / Speed test system error

**RU:** Роутеру не удалось выполнить шаг теста скорости.

**EN:** The router failed to run a step of the speed test.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## SPEED-WORKER-LOST

Исполнитель теста скорости остановился / Speed test worker stopped

**RU:** Фоновая часть теста остановилась, не закончив работу.

**EN:** The background part of the test stopped before finishing.

**Что делать:** Повторите тест.

**Action:** Repeat the test.

## SPEED-WORKER-START

Тест скорости не удалось запустить / Speed test could not start

**RU:** Роутер не смог запустить фоновую часть теста.

**EN:** The router could not start the background part of the test.

**Что делать:** Повторите позже.

**Action:** Repeat later.

## POLICY-CHANGED-DURING-PREFLIGHT

Правила VPN изменились во время проверки / VPN rules changed during the check

**RU:** Правила маршрутов VPN изменились во время проверки готовности, поэтому её результат не используется.

**EN:** The VPN route rules changed while the readiness check was running, so its result is not used.

**Что делать:** Повторите проверку, когда никто не правит настройки VPN.

**Action:** Repeat the check when nothing edits the VPN settings.

## RECOVERY-ACTION

Неизвестное действие восстановления / Unknown recovery action

**RU:** Скрипт восстановления вызван с неизвестным действием. Ничего не изменено.

**EN:** The recovery script was called with an action it does not know. Nothing was changed.

**Что делать:** Используйте документированную команду восстановления.

**Action:** Use the documented recovery command.

## TELEGRAM-ITEMS

Состав отчёта Telegram неверен / Telegram report items are wrong

**RU:** Список пунктов отчёта Telegram недопустим.

**EN:** The list of items chosen for the Telegram report is not valid.

**Что делать:** Откройте мастер Telegram и выберите пункты заново.

**Action:** Open the Telegram wizard and choose the items again.

## ENDPOINT-ADDRESS

Адрес сервера недопустим / Server address not valid

**RU:** Адрес сервера или порт пусты, слишком длинны или непригодны.

**EN:** The server address or port is empty, too long or not usable.

**Что делать:** Делать ничего не нужно: скрывается только показ адреса.

**Action:** Nothing to do; this only hides the address shown.

## ENDPOINT-PROC

Адрес сервера не удалось прочитать / Server address could not be read

**RU:** Таблицу ядра с текущим адресом сервера не удалось прочитать.

**EN:** The kernel table with the current server address could not be read.

**Что делать:** Делать ничего не нужно: попытка повторится.

**Action:** Nothing to do; it is tried again.

## ENDPOINT-PROCESS-EPOCH

Адрес сервера изменился при чтении / Server address changed while reading

**RU:** Туннель перезапустился во время чтения адреса, значение отброшено.

**EN:** The tunnel restarted while its address was read, so the value was dropped.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## ENDPOINT-READ-LIMIT

Таблица адреса сервера слишком велика / Server address table too large

**RU:** Таблица ядра больше допустимого и не прочитана.

**EN:** The kernel table was larger than allowed and was not read.

**Что делать:** Делать ничего не нужно.

**Action:** Nothing to do.

## FAST-*

Быстрое переключение не применено / Fast switch not used

**RU:** Роутер не смог применить порядок каналов напрямую (неожиданные цепочки firewall или изменение не подтвердилось) и использовал медленную перестройку GL либо отказался от переключения.

**EN:** The router could not apply the channel order directly (unexpected firewall chains or the change was not confirmed) and used the slower GL rebuild instead, or refused the switch.

**Что делать:** Ничего делать не нужно: переключение работает через перестройку GL. Если повторяется, отправьте код разработчику.

**Action:** Nothing to do: the switch still works through the GL rebuild. If it repeats, send the code to the developer.

## RESPONSE-COMPARE*

Сравнение способов отклика / Comparison of response methods

**RU:** Сохранённое сравнение всех способов отклика не удалось безопасно прочитать или записать. Переключение и выбранный способ не затронуты.

**EN:** The saved comparison of all response methods could not be read or written safely. Switching and the chosen metric are not affected.

**Что делать:** Делать ничего не нужно. Выключение и включение «мерить все способы» начинает новое сравнение; старый файл сохраняется.

**Action:** No action is needed. Turning "measure all methods" off and on starts a new comparison; the old file is kept.

## PING-HISTORY*

Проверка истории пинга / Ping history check

**RU:** Сохранённую историю пинга не удалось безопасно прочитать или записать. Текущие пинги и переключение продолжают работать.

**EN:** The saved ping history could not be read or written safely. Current pings and switching continue.

**Что делать:** Для переключения ничего делать не нужно. Если повторяется, сбросьте график или переустановите пакет; старый файл сохраняется.

**Action:** No action is needed for switching. If it repeats, reset the chart or reinstall the package; the old file is kept.

## PREPARATION-*

Действие подготовки роутера / Router preparation action

**RU:** Проверенное действие подготовки выполнено либо отклонено с указанным кодом. Запись настройки не запускает Auto и не доказывает выполнение всех условий.

**EN:** A reviewed preparation action was verified or refused with this specific code. A successful setting write does not start Auto or prove all prerequisites.

**Что делать:** Прочитайте конкретную причину у кнопки. До изменений остановите Auto и завершите восстановление. После неподтверждённой записи сохраните приватный журнал preparation-changes; не удаляйте его и не повторяйте вслепую. Restart-required означает отдельную осознанную перезагрузку роутера перед Auto.

**Action:** Read the exact reason shown beside the button. Stop and complete recovery before edits. After an unconfirmed write retain the private preparation-changes record; do not delete it or repeat blindly. Restart-required means a separate deliberate router reboot before Auto.

## LATENCY-*

История задержки недоступна / Delay history unavailable

**RU:** Не удалось проверить запись, файл или контрольную сумму истории задержки. Это само по себе не означает отказ VPN.

**EN:** A bounded delay-history sample, file or checksum could not be verified. This does not establish a VPN failure.

**Что делать:** Сохраните файл и проверьте хранилище. Текущие проверки могут продолжаться; не дорисовывайте историю и не сбрасывайте VPN ради графика.

**Action:** Preserve the file and inspect storage. Current checks can continue; do not invent missing history or reset the VPN to repair a graph.

## ENDPOINT-*

Текущий адрес сервера не получен / Current server address not observed

**RU:** Чтение адреса соединения из ядра недоступно, неоднозначно или соединение изменилось во время проверки. Название профиля не доказывает текущий адрес.

**EN:** The read-only kernel peer lookup was unavailable, ambiguous or changed during observation. A configured name is not proof of the current peer.

**Что делать:** Дождитесь свежей согласованной проверки. Проверьте соответствующий процесс и интерфейс только чтением; не перезапускайте рабочий туннель ради заполнения адреса.

**Action:** Wait for a fresh settled observation. Inspect the matching VPN process/interface read-only; do not restart a working tunnel merely to fill in its address.

## STATISTICS-*

Проверка сохранённой статистики / Saved statistics check

**RU:** Сохранённые счётчики, события или позиция выгрузки не прошли проверку. Непроверенные данные не считаются успешным наблюдением.

**EN:** The saved counters, incident details or download cursor failed validation. Unverified data is not presented as a successful observation.

**Что делать:** Повторите выгрузку. Если ошибка повторяется, сохраните оба файла контрольных точек и проверьте хранилище; не сбрасывайте счётчики.

**Action:** Retry the download. If the error persists, preserve both checkpoint files and inspect storage; do not reset the counters.

**Пример / Example:** STATISTICS-CURSOR: начните выгрузку с первой страницы. / STATISTICS-CURSOR: restart the download from the first page.

## PREP-*

Постоянная подготовка роутера (PREP-…) / Persistent router preparation (PREP-…)

**RU:** Постоянная настройка запуска или ускорения отсутствует, изменена либо не проверена. Наличия зависимостей недостаточно для безопасного переключения.

**EN:** A saved startup or acceleration prerequisite is missing, changed or unverified. A passing dependency check alone does not establish safe native operation.

**Что делать:** Проверьте карточку подготовки и инструкцию с исходными значениями и отменой изменений. Не отключайте рабочий DNS и не выгружайте драйверы принудительно.

**Action:** Review the preparation card and the documented original values/undo procedure. Do not disable a working DNS owner or force-unload drivers.

## PAIR-*

Авторежим двух каналов (PAIR-…) / Two-channel Auto (PAIR-…)

**RU:** Контроллер двух каналов готовит профили либо отклонил непроверенное действие. Проверки роутера не подтверждают внешний LAN-клиент.

**EN:** The two-channel controller is preparing profiles or refused an unverified operation. Router probes do not certify an external LAN client.

**Что делать:** Прочитайте текущий этап и причину. Остановка остаётся доступной; сохраните запись восстановления и не удаляйте её ради обхода отказа.

**Action:** Read the current phase and reason. Stop remains available; keep the recovery record and do not delete it to bypass a refusal.

## CASCADE-*

Внутренняя проверка модели каскада (CASCADE-…) / Internal check of the fallback model (CASCADE-…)

**RU:** Защитная проверка модели, планирующей переключение сервер → канал → протокол, отклонила шаг. Эти проверки нужны, чтобы остановить неверный или устаревший шаг; в этой версии модель на роутер не применяется.

**EN:** A safety check of the model that plans server → channel → protocol switching refused a step. These checks exist to stop a wrong or stale step; the model is not applied to the router in this version.

**Что делать:** Обычному пользователю делать ничего не нужно. Если код появился на настоящем роутере, отправьте его полностью в поддержку.

**Action:** Nothing to do for a normal user. Send the full code to support if it appears on a real router.

**Пример / Example:** CASCADE-PROOF-EXPIRED: подтверждение пришло слишком поздно и было проигнорировано. / CASCADE-PROOF-EXPIRED: a confirmation arrived too late and was ignored.

## CANDIDATE-*

Внутренняя проверка пробы кандидатов (CANDIDATE-…) / Internal check of candidate probing (CANDIDATE-…)

**RU:** Защитная проверка модели, проверяющей замену серверов, отклонила шаг (лимиты, время или принадлежность).

**EN:** A safety check of the model that tests replacement servers refused a step (limits, timing or ownership).

**Что делать:** Обычному пользователю делать ничего не нужно. Если код появился на настоящем роутере, отправьте его полностью в поддержку.

**Action:** Nothing to do for a normal user. Send the full code to support if it appears on a real router.

**Пример / Example:** CANDIDATE-BUDGET-EXCEEDED: тест использовал бы больше трафика, чем разрешено, поэтому не запускался. / CANDIDATE-BUDGET-EXCEEDED: the test would have used more traffic than allowed, so it was not run.

## MODEL-*

Внутренняя проверка модели переключения (MODEL-…) / Internal check of the switching model (MODEL-…)

**RU:** Правило модели процесса переключения (она используется в тестах) отклонило или отметило шаг.

**EN:** A rule of the model of the switch process (used in tests) refused or reported a step.

**Что делать:** Обычному пользователю делать ничего не нужно.

**Action:** Nothing to do for a normal user.

## CHECKPOINT-*

Проверка файла сохранённой статистики (CHECKPOINT-…) / Saved statistics file check (CHECKPOINT-…)

**RU:** Файл сохранённой статистики не прошёл проверку (неверная структура, число или дата). Он не используется, остаётся прежняя исправная копия.

**EN:** The saved statistics file failed a validation (wrong structure, number or date). It is not used and the previous good copy stays.

**Что делать:** Делать ничего не нужно; если статистика пустая, см. «Помощь» → «Неверные даты или история заблокирована».

**Action:** Nothing to do; if the statistics look empty, see Help → Dates are wrong or history is blocked.

**Пример / Example:** CHECKPOINT-DAY: в файле несуществующий день, поэтому файл отклонён. / CHECKPOINT-DAY: a day in the file does not exist, so the file was refused.

## MIGRATION-*

Проверка обновления настроек (MIGRATION-…) / Settings upgrade check (MIGRATION-…)

**RU:** При переносе настроек из старой версии не прошла проверка. Если проверка не пройдена, ничего не меняется.

**EN:** While moving settings from an older version, a check failed. Nothing was changed when a check fails.

**Что делать:** Сохраните резервную копию настроек и переустановите ту же версию; отправьте код в поддержку.

**Action:** Keep the settings backup and reinstall the same version; send the code to support.

**Пример / Example:** MIGRATION-EXTERNAL-EDIT: во время обновления кто-то правил файл вручную. / MIGRATION-EXTERNAL-EDIT: someone edited the file by hand during the upgrade.

## HISTORY-*

Проверка истории контроллера (HISTORY-…) / Controller history check (HISTORY-…)

**RU:** Запись о переключениях не прошла проверку (размер, порядок или контрольная сумма). Тогда контроллер отказывается действовать, потому что не может доказать, что делал раньше.

**EN:** The record of switches failed a check (size, order or checksum). The controller then refuses to act, because it cannot prove what it did before.

**Что делать:** Если повторяется, заархивируйте историю по SSH («Помощь» → аварийный возврат) и начните заново.

**Action:** If it repeats, archive the history over SSH (Help → emergency return) and start again.

**Пример / Example:** HISTORY-CHECKSUM: файл изменён или повреждён. / HISTORY-CHECKSUM: the file was changed or damaged.

## LIFECYCLE-*

Проверка безопасности обновления и службы (LIFECYCLE-…) / Upgrade and service safety check (LIFECYCLE-…)

**RU:** Перед обновлением или остановкой программа проверяет, что Auto выключен и исходный маршрут восстановлен. Одна из проверок не прошла.

**EN:** Before an upgrade or a stop, the program checks that Auto is off and the original route is restored. One of the checks did not pass.

**Что делать:** Остановите Auto на «Обзоре», дождитесь возврата и повторите.

**Action:** Stop Auto on the Overview, wait for the return, then repeat.

**Пример / Example:** LIFECYCLE-STOP-AUTO-FIRST: Auto всё ещё включён. / LIFECYCLE-STOP-AUTO-FIRST: Auto is still on.

## SPEED-*

Код теста скорости (SPEED-…) / Speed test code (SPEED-…)

**RU:** Шаг теста скорости сообщил это состояние (сеть, лимиты, часы или нагрузка роутера). Остальное не затронуто.

**EN:** A speed test step reported this condition (network, limits, clock or the router’s load). Nothing else is affected.

**Что делать:** Повторите позже. Если повторяется, проверьте VPN и свободное место.

**Action:** Repeat later. If it repeats, check the VPN and the free space.

**Пример / Example:** SPEED-DNS: имя тестового сервера не удалось найти через этот VPN. / SPEED-DNS: the name of the test server could not be resolved through that VPN.

## FAULT-*

Код теста сбоя (FAULT-…) / Failure test code (FAULT-…)

**RU:** Тест сбоя сообщил это состояние.

**EN:** The failure test reported this condition.

**Что делать:** См. панель теста сбоя на странице «Тесты».

**Action:** See the failure test panel on the Tests page.

## TELEGRAM-*

Код Telegram (TELEGRAM-…) / Telegram code (TELEGRAM-…)

**RU:** Шаг Telegram сообщил это состояние.

**EN:** A Telegram step reported this condition.

**Что делать:** Откройте мастер Telegram; «Помощь» → «Отчёты в Telegram не приходят».

**Action:** Open the Telegram wizard; Help → Telegram reports do not arrive.

## SETUP-*

Код настроек (SETUP-…) / Settings code (SETUP-…)

**RU:** Шаг настроек сообщил это состояние.

**EN:** A settings step reported this condition.

**Что делать:** Обновите страницу (Ctrl+F5) и повторите.

**Action:** Reload the page (Ctrl+F5) and repeat.

## PRIORITY-*

Код приоритетов (PRIORITY-…) / Priorities code (PRIORITY-…)

**RU:** Шаг приоритетов серверов сообщил это состояние.

**EN:** A step of the server priorities reported this condition.

**Что делать:** Обновите и повторите.

**Action:** Reload and repeat.

## RECOVERY-*

Код правил восстановления (RECOVERY-…) / Recovery rules code (RECOVERY-…)

**RU:** Шаг правил восстановления сообщил это состояние.

**EN:** A step of the recovery rules reported this condition.

**Что делать:** Обновите и повторите.

**Action:** Reload and repeat.

## RPC-*

Запрос к роутеру (RPC-…) / Request to the router (RPC-…)

**RU:** Запрос страницы к роутеру отклонён из-за вида или размера.

**EN:** A request from the page to the router was refused because of its form or size.

**Что делать:** Обновите страницу (Ctrl+F5).

**Action:** Reload the page (Ctrl+F5).

## SCAN-*

Код запроса проверки (SCAN-…) / Check request code (SCAN-…)

**RU:** Шаг запроса «Проверить VPN сейчас» сообщил это состояние.

**EN:** A step of the “Check the VPNs now” request reported this condition.

**Что делать:** Убедитесь, что мониторинг работает, и нажмите снова.

**Action:** Make sure the monitor runs and press again.

## DEPENDENCY-*

Не хватает программы (DEPENDENCY-…) / Missing program (DEPENDENCY-…)

**RU:** На роутере не хватает программы, нужной мониторингу.

**EN:** A program the monitor needs is missing on the router.

**Что делать:** Переустановите пакет; «Помощь» → установка.

**Action:** Reinstall the package; Help → install.

## GUARD-*

Код защитной блокировки (GUARD-…) / Safety block code (GUARD-…)

**RU:** Защитная блокировка программы сообщила это состояние.

**EN:** The program’s safety block reported this condition.

**Что делать:** «Помощь» → аварийный возврат.

**Action:** Help → emergency return.

## POLICY-*

Код VPN-правил (POLICY-…) / VPN rules code (POLICY-…)

**RU:** VPN-правила роутера не такие, как ожидает программа.

**EN:** The VPN rules of the router are not as the program expects.

**Что делать:** Не меняйте VPN-правила, пока Auto работает.

**Action:** Do not edit the VPN rules while Auto works.

## JOURNAL-*

Код журнала переключения (JOURNAL-…) / Switch journal code (JOURNAL-…)

**RU:** Сохранённая запись последнего переключения не прошла проверку.

**EN:** The saved record of the last switch failed a check.

**Что делать:** «Помощь» → аварийный возврат (close-journal).

**Action:** Help → emergency return (close-journal).

## UNSAFE-*

Небезопасное имя (UNSAFE-…) / Unsafe name (UNSAFE-…)

**RU:** Имя от роутера содержит странные символы; программа отказывается использовать его в команде.

**EN:** A name from the router has odd characters; the program refuses to use it in a command.

**Что делать:** Обратитесь в поддержку с кодом.

**Action:** Contact support with the code.

## GUARD-DEVICE-UNVERIFIED

Состояние VPN-интерфейса недоступно / VPN interface state unavailable

**RU:** Не удалось прочитать рабочее состояние включённого VPN-интерфейса. Проверьте выбранные клиенты в «Сеть → Интерфейсы»; удалённые и отключённые профили исключаются.

**EN:** An enabled VPN interface has no readable live state. Check Network → Interfaces for the selected clients; deleted or disabled profiles are excluded.

**Что делать:** Не удалось прочитать рабочее состояние включённого VPN-интерфейса. Проверьте выбранные клиенты в «Сеть → Интерфейсы»; удалённые и отключённые профили исключаются. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** An enabled VPN interface has no readable live state. Check Network → Interfaces for the selected clients; deleted or disabled profiles are excluded. If it is still unclear, open Help → “The Auto button refuses to start”.

## LAN-TRIAL-REQUIRED

Нужен LAN-тест / LAN trial required

**RU:** Выбранному клиентскому режиму нужен соответствующий LAN-тест. Подготовленный непрерывный router-probed режим этот сертификат не использует.

**EN:** This selected client-confirmed mode requires its matching LAN trial. Prepared continuous router-probed mode does not use this certificate.

**Что делать:** Выбранному клиентскому режиму нужен соответствующий LAN-тест. Подготовленный непрерывный router-probed режим этот сертификат не использует. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** This selected client-confirmed mode requires its matching LAN trial. Prepared continuous router-probed mode does not use this certificate. If it is still unclear, open Help → “The Auto button refuses to start”.

## BOUNDED-DEADLINE-REQUIRED

Нет окна теста / Test window missing

**RU:** Для выбранного теста нет действующего ограниченного окна. До нового разрешённого запуска проверьте фактическое восстановление и время.

**EN:** A bounded window is missing/expired for the selected trial. Verify actual recovery and time before a new authorized run.

**Что делать:** Для выбранного теста нет действующего ограниченного окна. До нового разрешённого запуска проверьте фактическое восстановление и время. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** A bounded window is missing/expired for the selected trial. Verify actual recovery and time before a new authorized run. If it is still unclear, open Help → “The Auto button refuses to start”.

## SESSION-LOSS-NOT-ACCEPTED

Не разрешён разрыв сессий / Reconnection not accepted

**RU:** Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим.

**EN:** Confirm in Settings that a short reconnection of calls and sessions is acceptable.

**Что делать:** Подтвердите в настройках, что кратковременный разрыв звонков и сессий допустим. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Confirm in Settings that a short reconnection of calls and sessions is acceptable. If it is still unclear, open Help → “The Auto button refuses to start”.

## TRANSACTION-IN-PROGRESS

Переключение идёт / Switch in progress

**RU:** На роутере открыта запись незавершённого переключения. Если переключение выполняется, дождитесь его или нажмите «Стоп»; без выполняющегося переключения нужно восстановление.

**EN:** An unfinished switch record is open on the router. If a switch is running, wait for it or press Stop; without a running switch, recovery is needed.

**Что делать:** На роутере открыта запись незавершённого переключения. Если переключение выполняется, дождитесь его или нажмите «Стоп»; без выполняющегося переключения нужно восстановление. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** An unfinished switch record is open on the router. If a switch is running, wait for it or press Stop; without a running switch, recovery is needed. If it is still unclear, open Help → “The Auto button refuses to start”.

## TRIAL-ATTEMPT-LIMIT

Лимит попыток теста / Trial attempt limit

**RU:** Бюджет попыток теста исчерпан. Сохраните отказы и соблюдайте бюджет/паузу; не сбрасывайте nonce или журнал ради обхода.

**EN:** The trial attempt budget is exhausted. Preserve failures and respect the budget/cooldown; never reset a nonce or ledger to bypass it.

**Что делать:** Бюджет попыток теста исчерпан. Сохраните отказы и соблюдайте бюджет/паузу; не сбрасывайте nonce или журнал ради обхода. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The trial attempt budget is exhausted. Preserve failures and respect the budget/cooldown; never reset a nonce or ledger to bypass it. If it is still unclear, open Help → “The Auto button refuses to start”.

## UNSUPPORTED-BOARD

Неподдерживаемая модель роутера / Unsupported router model

**RU:** Нативное переключение требует проверенного профиля прошивки GL-MT6000 или GL-MT3000. Выбор модели не отменяет эти проверки.

**EN:** Native switching requires a verified GL-MT6000 or GL-MT3000 firmware profile. Choosing a model does not bypass these checks.

**Что делать:** Нативное переключение требует проверенного профиля прошивки GL-MT6000 или GL-MT3000. Выбор модели не отменяет эти проверки. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Native switching requires a verified GL-MT6000 or GL-MT3000 firmware profile. Choosing a model does not bypass these checks. If it is still unclear, open Help → “The Auto button refuses to start”.

## UNSUPPORTED-FIRMWARE

Неподдерживаемая прошивка / Unsupported firmware

**RU:** Переключение проверено только для прошивки GL.iNet 4.11.0.

**EN:** Switching is verified only for GL.iNet firmware 4.11.0.

**Что делать:** Переключение проверено только для прошивки GL.iNet 4.11.0. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Switching is verified only for GL.iNet firmware 4.11.0. If it is still unclear, open Help → “The Auto button refuses to start”.

## FIRMWARE-UNKNOWN

Прошивка неизвестна / Firmware unknown

**RU:** Не удалось определить модель или прошивку роутера.

**EN:** The router model or firmware could not be read.

**Что делать:** Не удалось определить модель или прошивку роутера. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router model or firmware could not be read. If it is still unclear, open Help → “The Auto button refuses to start”.

## VENDOR-CODE-CHANGED

Код GL.iNet изменился / GL.iNet code changed

**RU:** Системные скрипты GL.iNet отличаются от проверенных. Переключение заблокировано.

**EN:** GL.iNet system scripts differ from the audited ones. Switching stays blocked.

**Что делать:** Системные скрипты GL.iNet отличаются от проверенных. Переключение заблокировано. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** GL.iNet system scripts differ from the audited ones. Switching stays blocked. If it is still unclear, open Help → “The Auto button refuses to start”.

## VENDOR-CODE-UNVERIFIED

Код GL.iNet не проверен / GL.iNet code unverified

**RU:** Не удалось проверить системные скрипты GL.iNet.

**EN:** GL.iNet system scripts could not be verified.

**Что делать:** Не удалось проверить системные скрипты GL.iNet. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** GL.iNet system scripts could not be verified. If it is still unclear, open Help → “The Auto button refuses to start”.

## VENDOR-WORKER-BUSY

Программа GL.iNet занята / GL.iNet program is busy

**RU:** Роутер сейчас сам применяет изменение VPN. Повторите через минуту.

**EN:** The router is applying its own VPN change right now. Try again in a minute.

**Что делать:** Роутер сейчас сам применяет изменение VPN. Повторите через минуту. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router is applying its own VPN change right now. Try again in a minute. If it is still unclear, open Help → “The Auto button refuses to start”.

## HARDWARE-ACCELERATOR-UNVERIFIED

Аппаратное ускорение не проверено / Hardware acceleration unverified

**RU:** Аппаратное ускорение (HNAT) не подтверждено как выключенное. Для достоверной проверки оно должно быть выключено.

**EN:** Hardware acceleration (HNAT) is not confirmed disabled. It must be off for the LAN check to be trustworthy.

**Что делать:** Аппаратное ускорение (HNAT) не подтверждено как выключенное. Для достоверной проверки оно должно быть выключено. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Hardware acceleration (HNAT) is not confirmed disabled. It must be off for the LAN check to be trustworthy. If it is still unclear, open Help → “The Auto button refuses to start”.

## SOFTWARE-ACCELERATOR-UNVERIFIED

Программное ускорение не проверено / Software acceleration unverified

**RU:** Загружен модуль программного ускорения, его отключение не подтверждено.

**EN:** A software acceleration module is loaded and not confirmed disabled.

**Что делать:** Загружен модуль программного ускорения, его отключение не подтверждено. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** A software acceleration module is loaded and not confirmed disabled. If it is still unclear, open Help → “The Auto button refuses to start”.

## FLOW-OFFLOAD-ENABLED

Включён flow offload / Flow offload is on

**RU:** Включён flow offloading в firewall. Выключите его в настройках firewall роутера.

**EN:** Firewall flow offloading is on. Turn it off in the router firewall settings.

**Что делать:** Включён flow offloading в firewall. Выключите его в настройках firewall роутера. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Firewall flow offloading is on. Turn it off in the router firewall settings. If it is still unclear, open Help → “The Auto button refuses to start”.

## IPV6-NOT-EXPLICITLY-DISABLED

IPv6 не отключён / IPv6 not disabled

**RU:** IPv6 на роутере должен быть явно выключен (утечки IPv6 не контролируются).

**EN:** IPv6 must be explicitly turned off on the router (IPv6 leaks are not covered).

**Что делать:** IPv6 на роутере должен быть явно выключен (утечки IPv6 не контролируются). Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** IPv6 must be explicitly turned off on the router (IPv6 leaks are not covered). If it is still unclear, open Help → “The Auto button refuses to start”.

## KILLSWITCH-NOT-ENABLED

Kill Switch выключен / Kill Switch is off

**RU:** Kill Switch должен быть включён для каждого активного VPN-правила.

**EN:** Kill Switch must be on for every active VPN rule.

**Что делать:** Kill Switch должен быть включён для каждого активного VPN-правила. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Kill Switch must be on for every active VPN rule. If it is still unclear, open Help → “The Auto button refuses to start”.

## DIRECT-WAN-FALLBACK

Возможен выход мимо VPN / Direct exit without VPN possible

**RU:** Роутеру разрешён выход мимо VPN. Отключите прямой выход в интернет в настройках VPN GL.iNet.

**EN:** The router is allowed to bypass the VPN. Disable the direct-internet fallback in GL.iNet VPN settings.

**Что делать:** Роутеру разрешён выход мимо VPN. Отключите прямой выход в интернет в настройках VPN GL.iNet. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router is allowed to bypass the VPN. Disable the direct-internet fallback in GL.iNet VPN settings. If it is still unclear, open Help → “The Auto button refuses to start”.

## VPN-POLICY-DISABLED

Политика VPN выключена / VPN policy is off

**RU:** Глобальная VPN-политика выключена в настройках роутера.

**EN:** The global VPN policy is off in the router settings.

**Что делать:** Глобальная VPN-политика выключена в настройках роутера. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The global VPN policy is off in the router settings. If it is still unclear, open Help → “The Auto button refuses to start”.

## TWO-TO-SIXTEEN-GENERIC-RULES-REQUIRED

Нужно от 2 до 16 правил VPN / Two to sixteen rules needed

**RU:** Нужно два или больше общих VPN-правил (для всего трафика).

**EN:** Two or more general (all-traffic) VPN rules are required.

**Что делать:** Нужно два или больше общих VPN-правил (для всего трафика). Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Two or more general (all-traffic) VPN rules are required. If it is still unclear, open Help → “The Auto button refuses to start”.

## GENERIC-RULES-NOT-ADJACENT

Правила идут не подряд / Rules not adjacent

**RU:** Общие VPN-правила должны идти подряд, без специальных правил между ними.

**EN:** The general VPN rules must follow one another without special rules between them.

**Что делать:** Общие VPN-правила должны идти подряд, без специальных правил между ними. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The general VPN rules must follow one another without special rules between them. If it is still unclear, open Help → “The Auto button refuses to start”.

## GENERIC-DUPLICATE-INTERFACE

Повтор интерфейса / Duplicate interface

**RU:** Два общих правила используют один и тот же VPN-интерфейс.

**EN:** Two general rules use the same VPN interface.

**Что делать:** Два общих правила используют один и тот же VPN-интерфейс. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Two general rules use the same VPN interface. If it is still unclear, open Help → “The Auto button refuses to start”.

## SPECIAL-RULES-MUST-PRECEDE-GENERIC

Особые правила в неверном порядке / Special rules in wrong order

**RU:** Специальные правила (по устройствам или назначениям) должны стоять до общих.

**EN:** Special rules (by device or destination) must be placed before the general rules.

**Что делать:** Специальные правила (по устройствам или назначениям) должны стоять до общих. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Special rules (by device or destination) must be placed before the general rules. If it is still unclear, open Help → “The Auto button refuses to start”.

## SOURCE-RESERVE-NOT-CONFIGURED

Основной или резерв не заданы / Primary or reserve not set

**RU:** Выберите в настройках основной и другой, резервный профиль.

**EN:** Choose a primary and a different reserve profile in Settings.

**Что делать:** Выберите в настройках основной и другой, резервный профиль. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Choose a primary and a different reserve profile in Settings. If it is still unclear, open Help → “The Auto button refuses to start”.

## PROFILE-INACTIVE

Профиль не подключён / Profile not connected

**RU:** Основной или резервный туннель не подключён. Подключите оба в VPN Dashboard GL.iNet.

**EN:** The primary or the reserve tunnel is not connected. Connect both in GL.iNet VPN Dashboard.

**Что делать:** Основной или резервный туннель не подключён. Подключите оба в VPN Dashboard GL.iNet. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The primary or the reserve tunnel is not connected. Connect both in GL.iNet VPN Dashboard. If it is still unclear, open Help → “The Auto button refuses to start”.

## PROFILES-NOT-GENERIC-RULES

Профили не в общих правилах / Profiles not in general rules

**RU:** Выбранные профили не являются общими VPN-правилами в политике роутера.

**EN:** The chosen profiles are not general VPN rules in the router policy.

**Что делать:** Выбранные профили не являются общими VPN-правилами в политике роутера. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The chosen profiles are not general VPN rules in the router policy. If it is still unclear, open Help → “The Auto button refuses to start”.

## SAME-INTERFACE

Один интерфейс дважды / Same interface twice

**RU:** Основной и резервный профили используют один интерфейс.

**EN:** Primary and reserve use the same interface.

**Что делать:** Основной и резервный профили используют один интерфейс. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Primary and reserve use the same interface. If it is still unclear, open Help → “The Auto button refuses to start”.

## POLICY-ORDER-DIRECTION-UNVERIFIED

Направление порядка правил не проверено / Rule order direction unverified

**RU:** Направление политики для этого режима ещё не установлено. У клиентского помощника и подготовленного непрерывного режима разные данные настройки.

**EN:** Policy-order direction has not been established for this mode. The client-confirmed helper and prepared continuous workflow have different setup evidence.

**Что делать:** Направление политики для этого режима ещё не установлено. У клиентского помощника и подготовленного непрерывного режима разные данные настройки. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Policy-order direction has not been established for this mode. The client-confirmed helper and prepared continuous workflow have different setup evidence. If it is still unclear, open Help → “The Auto button refuses to start”.

## LAN-LAYOUT-UNSUPPORTED

Неподдерживаемая схема LAN / Unsupported LAN layout

**RU:** Локальная сеть не на стандартном мосту br-lan.

**EN:** The LAN is not on the standard br-lan bridge.

**Что делать:** Локальная сеть не на стандартном мосту br-lan. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The LAN is not on the standard br-lan bridge. If it is still unclear, open Help → “The Auto button refuses to start”.

## PROFILE-NOT-MONITORED

Профиль не наблюдается / Profile not monitored

**RU:** Включите наблюдение для обоих выбранных профилей в настройках.

**EN:** Enable monitoring for both chosen profiles in Settings.

**Что делать:** Включите наблюдение для обоих выбранных профилей в настройках. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Enable monitoring for both chosen profiles in Settings. If it is still unclear, open Help → “The Auto button refuses to start”.

## NFT-GUARD-UNAVAILABLE

Страхующая блокировка недоступна / Safety block unavailable

**RU:** Недоступен инструмент firewall роутера (nft).

**EN:** The router firewall tool (nft) is unavailable.

**Что делать:** Недоступен инструмент firewall роутера (nft). Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router firewall tool (nft) is unavailable. If it is still unclear, open Help → “The Auto button refuses to start”.

## POLICY-READ-FAILED

Не удаётся прочитать правила VPN / Cannot read VPN rules

**RU:** Не удалось прочитать VPN-политику роутера.

**EN:** The router VPN policy could not be read.

**Что делать:** Не удалось прочитать VPN-политику роутера. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router VPN policy could not be read. If it is still unclear, open Help → “The Auto button refuses to start”.

## UPLINK-LINK-DOWN

Внешний канал отключён / Uplink is down

**RU:** Нет связи с интернет-провайдером; смена VPN не поможет.

**EN:** The internet cable/uplink is down; changing VPN would not help.

**Что делать:** Нет связи с интернет-провайдером; смена VPN не поможет. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The internet cable/uplink is down; changing VPN would not help. If it is still unclear, open Help → “The Auto button refuses to start”.

## LEASE-INTEGRITY-FAILED

Аренда повреждена / Lease damaged

**RU:** Запись ограниченного окна не прошла целостность. Сохраните её и проверьте восстановление/хранилище; не удаляйте и не создавайте другое окно как обход.

**EN:** The bounded lease record failed integrity checks. Preserve it and inspect recovery/storage; do not delete it or create another lease as a bypass.

**Что делать:** Запись ограниченного окна не прошла целостность. Сохраните её и проверьте восстановление/хранилище; не удаляйте и не создавайте другое окно как обход. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The bounded lease record failed integrity checks. Preserve it and inspect recovery/storage; do not delete it or create another lease as a bypass. If it is still unclear, open Help → “The Auto button refuses to start”.

## LEASE-STORAGE-FAILED

Аренда не сохраняется / Lease cannot be saved

**RU:** Не удалось сохранить окно теста на роутере.

**EN:** The test window could not be stored on the router.

**Что делать:** Не удалось сохранить окно теста на роутере. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The test window could not be stored on the router. If it is still unclear, open Help → “The Auto button refuses to start”.

## LEGACY-LEASE-RECOVERY

Восстановлена старая аренда / Old lease recovered

**RU:** Старая транзакция требует восстановления; подождите или нажмите «Стоп».

**EN:** An old transaction needs recovery; wait or press Stop.

**Что делать:** Старая транзакция требует восстановления; подождите или нажмите «Стоп». Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** An old transaction needs recovery; wait or press Stop. If it is still unclear, open Help → “The Auto button refuses to start”.

## EXTERNAL-POLICY-CHANGE-GUARD-RETAINED

Изменение извне, блокировка сохранена / Outside change, block kept

**RU:** Политику VPN роутера изменили во время переключения; трафик LAN удерживается. Проверьте порядок правил, см. router-test-kit/EMERGENCY.md.

**EN:** The router VPN policy was changed by someone else during a switch; LAN traffic is held. Check the rule order and see router-test-kit/EMERGENCY.md.

**Что делать:** Политику VPN роутера изменили во время переключения; трафик LAN удерживается. Проверьте порядок правил, см. router-test-kit/EMERGENCY.md. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router VPN policy was changed by someone else during a switch; LAN traffic is held. Check the rule order and see router-test-kit/EMERGENCY.md. If it is still unclear, open Help → “The Auto button refuses to start”.

## ROLLBACK-UNVERIFIED-GUARD-RETAINED

Возврат не подтверждён, блокировка сохранена / Return unverified, block kept

**RU:** Откат не удалось подтвердить; трафик LAN удерживается. См. router-test-kit/EMERGENCY.md.

**EN:** The rollback could not be verified; LAN traffic is held. See router-test-kit/EMERGENCY.md.

**Что делать:** Откат не удалось подтвердить; трафик LAN удерживается. См. router-test-kit/EMERGENCY.md. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The rollback could not be verified; LAN traffic is held. See router-test-kit/EMERGENCY.md. If it is still unclear, open Help → “The Auto button refuses to start”.

## CLIENT-CONFIRMATION-TIMEOUT

Компьютер не подтвердил / Computer did not confirm

**RU:** Нужное подтверждение клиента не пришло вовремя. Восстановление запрошено; проверьте, вернулся ли исходный маршрут или сохранён резерв.

**EN:** Required client confirmation did not arrive in time. Recovery was requested; verify whether the original route returned or reserve was retained.

**Что делать:** Нужное подтверждение клиента не пришло вовремя. Восстановление запрошено; проверьте, вернулся ли исходный маршрут или сохранён резерв. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Required client confirmation did not arrive in time. Recovery was requested; verify whether the original route returned or reserve was retained. If it is still unclear, open Help → “The Auto button refuses to start”.

## CLIENT-STOP

Остановлено помощником / Stopped by the helper

**RU:** Остановлено по запросу.

**EN:** Stopped by request.

**Что делать:** Остановлено по запросу. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Stopped by request. If it is still unclear, open Help → “The Auto button refuses to start”.

## TARGET-HTTPS-DNS-FAILED

Проверка резерва не прошла / Reserve check failed

**RU:** Резерв не прошёл проверку DNS/HTTPS.

**EN:** The reserve did not pass the DNS/HTTPS check.

**Что делать:** Резерв не прошёл проверку DNS/HTTPS. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The reserve did not pass the DNS/HTTPS check. If it is still unclear, open Help → “The Auto button refuses to start”.

## LAN-BASELINE-NOT-SOURCE

Компьютер был не на основном / Computer was not on the primary

**RU:** Компьютер в LAN сейчас не использует основной маршрут.

**EN:** The LAN computer is not currently using the primary route.

**Что делать:** Компьютер в LAN сейчас не использует основной маршрут. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The LAN computer is not currently using the primary route. If it is still unclear, open Help → “The Auto button refuses to start”.

## RESERVE-EXIT-NOT-DISTINCT

Выход резерва совпал с основным / Reserve exit equals primary

**RU:** У основного и резервного одинаковый внешний IP; переключение невозможно доказать.

**EN:** Primary and reserve have the same external IP; the switch could not be proven.

**Что делать:** У основного и резервного одинаковый внешний IP; переключение невозможно доказать. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Primary and reserve have the same external IP; the switch could not be proven. If it is still unclear, open Help → “The Auto button refuses to start”.

## VENDOR-APPLY-FAILED

GL.iNet не применил изменение / GL.iNet did not apply the change

**RU:** Роутер не смог применить изменение; выполнен откат.

**EN:** The router failed to apply the change; it was rolled back.

**Что делать:** Роутер не смог применить изменение; выполнен откат. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router failed to apply the change; it was rolled back. If it is still unclear, open Help → “The Auto button refuses to start”.

## POLICY-CHANGED-DURING-APPLY

Правила изменились во время переключения / Rules changed during the switch

**RU:** Политика изменилась во время переключения; выполнен откат.

**EN:** The policy changed while switching; it was rolled back.

**Что делать:** Политика изменилась во время переключения; выполнен откат. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The policy changed while switching; it was rolled back. If it is still unclear, open Help → “The Auto button refuses to start”.

## NATIVE-SYSTEM-001

Проверка системы не прошла / System check failed

**RU:** Внутренняя ошибка контроллера. См. «Службу мониторинга».

**EN:** Internal controller error. See the Service monitor.

**Что делать:** Внутренняя ошибка контроллера. См. «Службу мониторинга». Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Internal controller error. See the Service monitor. If it is still unclear, open Help → “The Auto button refuses to start”.

## TERMS-NOT-ACCEPTED

Условия не приняты / Terms not accepted

**RU:** Условия использования ещё не приняты. Откройте эту страницу в LuCI и примите их на первом экране.

**EN:** The terms of use are not accepted yet. Open this page in LuCI and accept them on the first screen.

**Что делать:** Условия использования ещё не приняты. Откройте эту страницу в LuCI и примите их на первом экране. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The terms of use are not accepted yet. Open this page in LuCI and accept them on the first screen. If it is still unclear, open Help → “The Auto button refuses to start”.

## RETURN-NOT-APPLICABLE

Возвращать нечего / Nothing to return

**RU:** Возвращаться не откуда: Auto не удерживает резерв.

**EN:** There is nothing to return from: Auto is not holding the reserve.

**Что делать:** Возвращаться не откуда: Auto не удерживает резерв. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** There is nothing to return from: Auto is not holding the reserve. If it is still unclear, open Help → “The Auto button refuses to start”.

## SOURCE-NOT-HEALTHY

Основной ещё не исправен / Primary not healthy yet

**RU:** Основной VPN сейчас не проходит проверку, роутер остаётся на резерве. Повторите, когда основной заработает.

**EN:** The primary does not pass its check right now, so the router stays on the reserve. Try again when the primary works.

**Что делать:** Основной VPN сейчас не проходит проверку, роутер остаётся на резерве. Повторите, когда основной заработает. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The primary does not pass its check right now, so the router stays on the reserve. Try again when the primary works. If it is still unclear, open Help → “The Auto button refuses to start”.

## JOURNAL-UNVERIFIED

Журнал не проверен / Journal unverified

**RU:** Журнал транзакций не удалось проверить. Используйте аварийные шаги из router-test-kit/EMERGENCY.md.

**EN:** The transaction journal could not be verified. Use the emergency steps in router-test-kit/EMERGENCY.md.

**Что делать:** Журнал транзакций не удалось проверить. Используйте аварийные шаги из router-test-kit/EMERGENCY.md. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The transaction journal could not be verified. Use the emergency steps in router-test-kit/EMERGENCY.md. If it is still unclear, open Help → “The Auto button refuses to start”.

## EXTERNAL-POLICY-CHANGE

Изменено извне / Changed from outside

**RU:** Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.

**EN:** The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.

**Что делать:** Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet. If it is still unclear, open Help → “The Auto button refuses to start”.

## EXTERNAL-POLICY-CHANGE-RELEASED

Изменено извне, блокировка снята / Changed from outside, block removed

**RU:** Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet.

**EN:** The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet.

**Что делать:** Правила VPN на роутере изменил кто-то другой. Auto остановлен и снял свою блокировку трафика; проверьте правила VPN в GL.iNet. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router VPN rules were changed by someone else. Auto stopped and released its traffic block; check the VPN rules in GL.iNet. If it is still unclear, open Help → “The Auto button refuses to start”.

## ROLLBACK-UNVERIFIED

Возврат не подтверждён / Return unverified

**RU:** Возврат на прежний маршрут не удалось подтвердить. Трафик разрешён только через VPN-туннели; проверьте порядок правил VPN в GL.iNet.

**EN:** The return to the previous route could not be verified. Traffic is allowed only through VPN tunnels; check the VPN rule order in GL.iNet.

**Что делать:** Возврат на прежний маршрут не удалось подтвердить. Трафик разрешён только через VPN-туннели; проверьте порядок правил VPN в GL.iNet. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The return to the previous route could not be verified. Traffic is allowed only through VPN tunnels; check the VPN rule order in GL.iNet. If it is still unclear, open Help → “The Auto button refuses to start”.

## ENVIRONMENT-EVIDENCE-UNAVAILABLE

Нет данных о роутере / No data about the router

**RU:** Роутер ещё не сообщил, из чего он состоит (модель, прошивка, установленные программы). Мониторинг запускается сам: подождите минуту и обновите страницу.

**EN:** The router has not yet reported what it is made of (model, firmware, installed tools). Monitoring starts by itself: wait a minute and reload the page.

**Что делать:** Роутер ещё не сообщил, из чего он состоит (модель, прошивка, установленные программы). Мониторинг запускается сам: подождите минуту и обновите страницу. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The router has not yet reported what it is made of (model, firmware, installed tools). Monitoring starts by itself: wait a minute and reload the page. If it is still unclear, open Help → “The Auto button refuses to start”.

## MONITOR-EVIDENCE-STALE

Данные мониторинга устарели / Monitor data is old

**RU:** Нет свежих данных от мониторинга. Запустите его в блок «Мониторинг» на «Обзоре»; без него Auto использовать нельзя.

**EN:** There is no fresh data from the monitor. Monitoring starts by itself; wait a minute and reload. If it stays, see Help → “The page is old, empty or says the monitor is not running”.

**Что делать:** Нет свежих данных от мониторинга. Запустите его в блок «Мониторинг» на «Обзоре»; без него Auto использовать нельзя. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** There is no fresh data from the monitor. Monitoring starts by itself; wait a minute and reload. If it stays, see Help → “The page is old, empty or says the monitor is not running”. If it is still unclear, open Help → “The Auto button refuses to start”.

## NATIVE-START-CERTIFICATION-REQUIRED

Повторная проверка при запуске / Checked again at Start

**RU:** Здесь ничто не мешает, но роутер всё равно перепроверит всё в момент нажатия «Старт» (текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат).

**EN:** Nothing blocks you here, but the router itself still checks everything again at the moment you press Start (current device, time window, your computer’s confirmation, safe return).

**Что делать:** Здесь ничто не мешает, но роутер всё равно перепроверит всё в момент нажатия «Старт» (текущее устройство, окно времени, подтверждение вашего компьютера, безопасный возврат). Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Nothing blocks you here, but the router itself still checks everything again at the moment you press Start (current device, time window, your computer’s confirmation, safe return). If it is still unclear, open Help → “The Auto button refuses to start”.

## OPERATOR-RETURN

Команда возврата маршрута / Return-control command

**RU:** Это семейство команд ручного управления, а не доказательство нажатия человеком. Сохранённый инициатор различает оператора, автоматику, тест или программный доступ.

**EN:** This is the manual-control command family, not proof that a human clicked. The recorded initiator distinguishes operator, automation, test or programmatic access.

**Что делать:** Возврат на основной выполнен по вашему запросу. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Returned to the primary on your request. If it is still unclear, open Help → “The Auto button refuses to start”.

## PRIMARY-RECOVERED

Основной восстановился / Primary recovered

**RU:** Основной восстановился, Auto вернулся на него.

**EN:** The primary recovered and Auto returned to it.

**Что делать:** Основной восстановился, Auto вернулся на него. Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** The primary recovered and Auto returned to it. If it is still unclear, open Help → “The Auto button refuses to start”.

## PAIR-STATE-UNVERIFIED

Незавершённое переключение требует восстановления / Unfinished switch needs recovery

**RU:** Незавершённое переключение требует восстановления

**EN:** Unfinished switch needs recovery

**Что делать:** Незавершённое переключение требует восстановления Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Unfinished switch needs recovery If it is still unclear, open Help → “The Auto button refuses to start”.

## PAIR-PROFILES-UNVERIFIED

Проверьте текущую пару VPN / Review the current VPN pair

**RU:** Проверьте текущую пару VPN

**EN:** Review the current VPN pair

**Что делать:** Проверьте текущую пару VPN Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Review the current VPN pair If it is still unclear, open Help → “The Auto button refuses to start”.

## PAIR-PREPARATION-REQUIRED

Завершите подготовку роутера / Complete router preparation

**RU:** Завершите подготовку роутера

**EN:** Complete router preparation

**Что делать:** Завершите подготовку роутера Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Complete router preparation If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-HNAT-CONFIG

Отключите сетевое ускорение / Disable network acceleration

**RU:** Отключите сетевое ускорение

**EN:** Disable network acceleration

**Что делать:** Отключите сетевое ускорение Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable network acceleration If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-WGCLIENT1-AUTOSTART

Проверьте автозапуск wgclient1 / Review wgclient1 startup

**RU:** Проверьте автозапуск wgclient1

**EN:** Review wgclient1 startup

**Что делать:** Проверьте автозапуск wgclient1 Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Review wgclient1 startup If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-OVPNCLIENT1-AUTOSTART

Проверьте автозапуск ovpnclient1 / Review ovpnclient1 startup

**RU:** Проверьте автозапуск ovpnclient1

**EN:** Review ovpnclient1 startup

**Что делать:** Проверьте автозапуск ovpnclient1 Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Review ovpnclient1 startup If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-STOCK-VPN-BOOT

Отключите конкурирующий автозапуск VPN / Disable competing VPN startup

**RU:** Отключите конкурирующий автозапуск VPN

**EN:** Disable competing VPN startup

**Что делать:** Отключите конкурирующий автозапуск VPN Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable competing VPN startup If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-SFE-BOOT

Отключите сетевое ускорение / Disable network acceleration

**RU:** Отключите сетевое ускорение

**EN:** Disable network acceleration

**Что делать:** Отключите сетевое ускорение Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable network acceleration If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-SFE-AUTOLOAD

Отключите сетевое ускорение / Disable network acceleration

**RU:** Отключите сетевое ускорение

**EN:** Disable network acceleration

**Что делать:** Отключите сетевое ускорение Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable network acceleration If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-SFE-RUNTIME

Отключите сетевое ускорение / Disable network acceleration

**RU:** Отключите сетевое ускорение

**EN:** Disable network acceleration

**Что делать:** Отключите сетевое ускорение Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable network acceleration If it is still unclear, open Help → “The Auto button refuses to start”.

## PREPARATION-RESTART-REQUIRED

Нужна перезагрузка роутера / Router restart required

**RU:** Нужна перезагрузка роутера

**EN:** Router restart required

**Что делать:** Нужна перезагрузка роутера Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Router restart required If it is still unclear, open Help → “The Auto button refuses to start”.

## PREPARATION-RECOVERY-REQUIRED

Завершите подготовку роутера / Complete router preparation

**RU:** Изменение подготовки требует восстановления

**EN:** A preparation change needs recovery

**Что делать:** Изменение подготовки требует восстановления Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** A preparation change needs recovery If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-SOURCE-AUTOSTART

Отключите автозапуск основного VPN / Disable primary VPN boot startup

**RU:** Отключите автозапуск основного VPN

**EN:** Disable primary VPN boot startup

**Что делать:** Отключите автозапуск основного VPN Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable primary VPN boot startup If it is still unclear, open Help → “The Auto button refuses to start”.

## PREP-TARGET-AUTOSTART

Отключите автозапуск резервного VPN / Disable reserve VPN boot startup

**RU:** Отключите автозапуск резервного VPN

**EN:** Disable reserve VPN boot startup

**Что делать:** Отключите автозапуск резервного VPN Если всё ещё непонятно, откройте «Помощь» → «Кнопка Auto отказывается запускаться».

**Action:** Disable reserve VPN boot startup If it is still unclear, open Help → “The Auto button refuses to start”.

## GL-ADAPTER-UNVERIFIED

Менеджер VPN GL.iNet / GL.iNet VPN manager

**RU:** Не доказано, что способ переключения этой программы работает вместе со встроенным менеджером VPN именно этой прошивки GL.iNet.

**EN:** Not proven that this program’s way of switching works together with the VPN manager built into this exact GL.iNet firmware.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## WORKER-COORDINATION-UNVERIFIED

Фоновые программы GL.iNet / GL.iNet background programs

**RU:** GL.iNet запускает свои фоновые программы, которые тоже подключают и переподключают VPN. Не проверено, что они не мешают этой программе.

**EN:** GL.iNet runs its own background programs that also connect and reconnect VPNs. Not tested that they do not fight with this program.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## LAN-PATH-UNVERIFIED

Путь домашнего компьютера / Path of a home computer

**RU:** Не подтверждено с компьютера в вашей сети, что его трафик действительно идёт через выбранный VPN. Это проверяет LAN-помощник.

**EN:** Not confirmed from a computer in your network that its traffic really goes through the chosen VPN. This is what the LAN helper checks.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## DNS-POLICY-UNVERIFIED

Поиск адресов (DNS) / Name lookups (DNS)

**RU:** Не подтверждено, что DNS-запросы ваших устройств идут через VPN и не утекают мимо него во время и после переключения.

**EN:** Not confirmed that DNS requests of your devices follow the VPN and do not leak outside it during and after a switch.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## KILLSWITCH-UNVERIFIED

Kill Switch / Kill Switch

**RU:** Не подтверждено, что Kill Switch GL.iNet блокирует интернет, а не пропускает трафик мимо VPN, когда VPN обрывается во время переключения.

**EN:** Not confirmed that the GL.iNet Kill Switch blocks the internet, instead of leaking, when a VPN drops during a switch.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## IPV6-POLICY-UNVERIFIED

Трафик IPv6 / IPv6 traffic

**RU:** Не подтверждено, что трафик IPv6 не может обойти VPN.

**EN:** Not confirmed that IPv6 traffic cannot bypass the VPN.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## WATCHDOG-UNVERIFIED

Страхующий таймер / Safety timer

**RU:** Не подтверждено на этом роутере, что независимый таймер, который снимает собственную блокировку трафика и возвращает безопасное состояние при зависании, всегда срабатывает.

**EN:** Not confirmed on this router that the independent timer, which releases the program’s traffic block and returns to a safe state if something hangs, always fires.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## SCOPED-CONNTRACK-UNVERIFIED

Открытые соединения / Open connections

**RU:** Не подтверждено, что при переключении сбрасываются только нужные соединения (таблица соединений роутера), а не все.

**EN:** Not confirmed that a switch resets only the connections it must (the router’s connection table), not all of them.

**Что делать:** Это диагностика прежней прогнозной модели, не действующий сертификат. Используйте готовность своего режима; независимые LAN/DNS/IPv6/KillSwitch проверяются отдельно.

**Action:** This legacy planning diagnostic is not a live certification. Use actual mode-specific System readiness; independent LAN/DNS/IPv6/KillSwitch proof remains separate.

## EVENT-CHECK-OK

Проверка прошла / Check passed

**RU:** Монитор получил результат без диагностической ошибки. Это наблюдение доступности канала в тот момент; оно не означает переключение трафика или включение Auto.

**EN:** The monitor received a result without a diagnostic error. This records channel availability at that observation; it does not mean traffic switched or that Auto was activated.

**Что делать:** Условие доступности канала выполнено. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Channel availability threshold was met. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-CHECK-FAILED

Ошибка проверки / Check failed

**RU:** Зафиксирована неудачная проверка канала. Причину наблюдаемого отказа смотрите в сохранённом диагностическом коде. Сама запись не доказывает смену маршрута.

**EN:** A failed channel check was recorded. Open the saved diagnostic code for the observed failure. It does not by itself prove a route switch.

**Что делать:** Ошибка проверки соединения. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Connection check failed. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-CONNECTION-RECOVERED

Доступность восстановлена / Availability restored

**RU:** Ранее отказавший канал снова стал доступен по наблюдениям. Это восстановление доступности, а не доказательство, что через него уже идёт трафик.

**EN:** A previously failed channel became available again in observations. This is recovery of availability, not proof that it became the traffic route.

**Что делать:** Доступность соединения восстановлена. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Connection availability recovered. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-PROFILE-DISABLED

Профиль отключён / Profile disabled

**RU:** Профиль административно отключён или неактивен. Это отличается от ошибки проверки Интернета.

**EN:** The profile is administratively disabled or inactive. This is distinct from a failed Internet check.

**Что делать:** VPN-профиль отключён. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** VPN profile was disabled. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-OBSERVATION-GAP

Перерыв наблюдений / No observation interval

**RU:** За интервал нет достоверных измерений. Пропуск не превращается ни в исправность, ни в выдуманный отказ.

**EN:** There were no trusted measurements for an interval. Neither successful connectivity nor failure is invented for the missing period.

**Что делать:** Зафиксирован перерыв наблюдений. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** A gap in observations was recorded. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-MONITORING

Наблюдение за каналами / Observing channels

**RU:** Контроллер проверяет каналы. Само это состояние не означает только что выполненное переключение трафика; выбор маршрута подтверждается отдельно.

**EN:** The controller is checking the channels. This state alone does not describe a newly completed traffic switch; channel selection has separate confirmation.

**Что делать:** Контроллер наблюдает за VPN-каналами. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The controller is observing the VPN channels. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-START-CONFIRMATION-PENDING

Запуск ожидает подтверждения / Start awaiting confirmation

**RU:** Запрос Start сохранён, пока ещё видно прежнее остановленное состояние. Это ожидание запуска, а не новая команда Stop.

**EN:** The Start request is recorded while the previous stopped state is still visible. This is not another Stop command.

**Что делать:** Запрос включения принят; ожидается подтверждение контроллера. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Start accepted; waiting for the controller. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-CHANNEL-PREPARATION

Подготовка каналов / Preparing channels

**RU:** Зафиксирован подготовительный этап. Связность и маршрут ещё могут проверяться; это не завершённое переключение.

**EN:** A preparation stage was recorded. Connectivity and routing may still be checked; this is not a completed switch.

**Что делать:** Подготавливаются и проверяются условия работы каналов. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Channel prerequisites are being prepared and checked. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-ROUTE-APPLYING

Выбор маршрута / Selecting route

**RU:** Операция применяет запланированный выбор трафика. Итог должен быть подтверждён следующим событием.

**EN:** The operation is applying the planned traffic selection. Its final outcome must be confirmed by a later event.

**Что делать:** Выполняется команда выбора маршрута. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** A route-selection command is being applied. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-PATH-CONFIRMATION

Подтверждение пути / Verifying path

**RU:** Изменение ещё не принято как подтверждённый маршрут. Требуемое доказательство зависит от сохранённого режима: наблюдения роутера либо отдельный клиентский тест.

**EN:** The change is not yet accepted as a confirmed route. The required evidence depends on the recorded operating mode: router observations or a separate client witness.

**Что делать:** Ожидается подтверждение выбранного пути. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The selected path is awaiting verification. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RESERVE-SELECTED

Резерв выбран / Reserve selected

**RU:** Операция подтвердила выбор резерва. Это не означает неисправность основного: его состояние проверяется отдельно.

**EN:** The recorded operation confirmed reserve selection. This does not imply that the primary is broken; its health is a separate observation.

**Что делать:** Выбор резервного маршрута подтверждён. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Reserve traffic selection was confirmed. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RESERVE-HELD

Резерв удержан / Reserve retained

**RU:** Операция сохранила резервный маршрут. В непрерывном сеансе Auto может продолжать работать; это состояние транзакции не доказывает глобальное выключение Auto.

**EN:** The operation retained reserve routing. In a continuous session Auto may remain on; this transaction state is not proof of a global Auto shutdown.

**Что делать:** Операция завершилась с сохранением резерва. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The operation ended while retaining the reserve. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RETURN-IN-PROGRESS

Возврат маршрута / Returning route

**RU:** Восстановление выполняется. Прежде чем считать исходный маршрут восстановленным, требуется последующее подтверждение.

**EN:** Restoration is in progress. A later verified outcome is required before describing the original route as restored.

**Что делать:** Восстанавливается исходный маршрут. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The original route is being restored. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-ROLLBACK-RECORDED

Записан откат / Rollback recorded

**RU:** Старая запись содержит этап отката. Если подтверждение original_restored в ней отсутствует, успешное восстановление не приписывается.

**EN:** This old record names a rollback. If it lacks an original_restored confirmation, successful restoration must not be invented.

**Что делать:** Зафиксирован этап отката. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** A rollback stage was recorded. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-ORIGINAL-RESTORED

Исходный маршрут восстановлен / Original route restored

**RU:** В событии есть явное подтверждение восстановления. Это отличается от запроса возврата или незавершённого восстановления.

**EN:** The event includes explicit verified restoration evidence. This is separate from a request to return or a restoration-in-progress stage.

**Что делать:** Восстановление исходного маршрута подтверждено. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Restoration of the original route was confirmed. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-OPERATION-STOPPED

Операция остановлена / Operation stopped

**RU:** Операция завершена. Общее состояние Auto и итоговый маршрут определяются по собственным подтверждениям, а не выводятся только из этого слова.

**EN:** The operation ended. A global Auto state and the resulting route must be read from their own recorded confirmations, not inferred from this word alone.

**Что делать:** Управляющая операция остановлена. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The controller operation was stopped. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-AUTO-RUNNING

Auto работает / Auto running

**RU:** Зафиксирован работающий сеанс контроллера. Каналам по-прежнему нужны свежие проверки; это не гарантия каждого клиентского пути.

**EN:** A running controller session was recorded. Each channel still needs fresh connectivity checks; it is not a guarantee of every client path.

**Что делать:** Сеанс Auto работает. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The Auto session is running. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-AUTO-START-REQUESTED

Запрошен запуск / Start requested

**RU:** Это запрос с сохранённым инициатором. Запуск не подтверждён до последующего завершённого состояния.

**EN:** This is the request, including its recorded initiator. Startup is not confirmed until a later completed state.

**Что делать:** Запрошено включение Auto. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Auto activation requested. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-AUTO-STOP-REQUESTED

Запрошена остановка / Stop requested

**RU:** Это запрос остановки, а не доказательство восстановления маршрута или завершения остановки контроллера.

**EN:** This is a stop request, not proof that routing was restored or the controller finished stopping.

**Что делать:** Запрошено выключение Auto. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Auto deactivation requested. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-OPERATION-BLOCKED

Действие отклонено / Action refused

**RU:** Успех не предполагается. Прочитайте сохранённый код причины; не обходите условие и не считайте очередь выполненным выбором маршрута.

**EN:** No success is inferred. Read the saved reason code; do not bypass the gate or treat a queued request as applied routing.

**Что делать:** Действие отклонено из-за невыполненного условия. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** A required prerequisite blocked the action. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-OPERATION-FAILED

Операция не выполнена / Operation failed

**RU:** Прочитайте конкретную сохранённую причину и итог восстановления. Неудачное применение или откат не выдаётся за успешное переключение.

**EN:** Read the specific recorded reason and recovery outcome. Failed application or rollback is not reported as successful switching.

**Что делать:** Операция завершилась ошибкой. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The operation ended with an error. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-WINDOW-EXPIRED

Окно теста завершено / Test window ended

**RU:** Истёк заданный предел времени. Итог маршрутизации или восстановления подтверждается отдельно.

**EN:** A configured time boundary ended. The final routing/recovery outcome is a separate confirmation.

**Что делать:** Закончилось ограниченное окно операции. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The bounded operation window expired. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RECOVERY-PENDING

Восстановление ожидается / Recovery pending

**RU:** Завершение восстановления ещё не проверено. Смотрите сохранённый код; попытка очистки не равна итоговому результату.

**EN:** Recovery has not yet been verified complete. Read the saved recovery code; an attempted cleanup is not the final result.

**Что делать:** Ожидается подтверждение снятия блокировки. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Traffic-block release is awaiting confirmation. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RESERVE-DEGRADED

Проблема на резерве / Reserve check failed

**RU:** На резерве наблюдается проблема. Возврат на основной по-прежнему требует актуальных доказательств и применимой политики.

**EN:** A problem was observed on the reserve. Returning to primary still requires current evidence and the applicable policy.

**Что делать:** На выбранном резерве тоже выявлена проблема связи. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The selected reserve also has a connectivity problem. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-TRIAL-PREREQUISITE

Не выполнено условие режима / Mode prerequisite missing

**RU:** Сохранённая причина описывает условие конкретного режима. Отказ прежнего LAN-теста не означает, что любой подготовленный router-probed сеанс требует клиентский сертификат.

**EN:** The saved reason describes the mode-specific prerequisite. A legacy LAN trial refusal does not imply every prepared router-probed session needs a client certificate.

**Что делать:** Для выбранного режима нужно дополнительное условие. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The chosen mode needs an additional prerequisite. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-DETAILS-NOT-SAVED

Подробности не сохранены / Record lacks detail

**RU:** Объясняются только сохранённые поля. Отсутствующие инициатор, роль или итог не заменяются сегодняшним маршрутом или выдуманным успешным переключением.

**EN:** Only the saved fields can be explained. A missing initiator, role or final outcome is not replaced with today's route or an invented successful switch.

**Что делать:** В старой записи не сохранено полное описание события. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** An older record did not retain a full event description. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RECORD-CONFLICT

Ошибка данных записи / Record data conflict

**RU:** Одновременно записаны успех и ошибка. Это не считается успешной проверкой или подтверждённым переходом; проверьте сохранённые диагностические данные.

**EN:** Success and failure were both recorded. Do not treat this as a successful channel or confirmed switch; inspect the saved diagnostic data.

**Что делать:** В сохранённом событии противоречивые результаты. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The saved event contains conflicting results. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-COMMAND-CANCELLED

Команда отменена / Command cancelled

**RU:** Зафиксирована отмена. Итоговый маршрут или завершение очистки подтверждаются отдельно.

**EN:** Cancellation was recorded. The resulting route or cleanup still requires its own confirmation.

**Что делать:** Запрошенная операция отменена. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The requested operation was cancelled. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-COMMAND-ACCEPTED

Команда принята / Command accepted

**RU:** Исполнитель принял команду. Это ещё не доказывает завершение действия с маршрутом.

**EN:** The worker accepted this command. It has not yet proved that the routing action completed.

**Что делать:** Контроллер принял команду в обработку. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The controller accepted the command for processing. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-COMMAND-QUEUED

Команда в очереди / Command queued

**RU:** Принятие в очередь отличается от выполнения и подтверждённого завершения.

**EN:** Queue acceptance is separate from execution and verified completion.

**Что делать:** Команда ожидает выполнения в очереди. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The command is waiting in the queue. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-CONTROLLER-IDLE

Ожидание команды / Waiting for a command

**RU:** У этого исполнителя нет активной операции. Это само по себе не доказывает выключение общего Auto или неисправность канала.

**EN:** This handler has no active operation. It does not alone prove that global Auto is off or either channel is unhealthy.

**Что делать:** Исполнитель операций ожидает команду. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The operation handler is idle. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-RESULT-NEEDS-VERIFICATION

Нужна проверка результата / Verify the result

**RU:** Сохранённые данные не подтверждают фактическое выполнение. Перед повтором сверьте текущее состояние; успешная маршрутизация не предполагается.

**EN:** The saved data does not confirm actual completion. Inspect current state before repeating the action; do not invent successful routing.

**Что делать:** Фактический результат операции ещё не проверен. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The operation result has not been verified. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-CHANNEL-SELECTION

Запись выбора канала / Channel selection record

**RU:** Сохранённые направление и завершение описывают эту операцию. Сам этап контроллера не доказывает выбранный маршрут или доступность независимого клиента LAN.

**EN:** The saved direction and completion describe this operation. A controller phase alone does not prove the selected route or independent LAN availability.

**Что делать:** Роутер сохранил операцию выбора канала. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The router recorded a channel selection operation. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-POLICY-REAPPLY

Повторное применение правил VPN / VPN rules applied again

**RU:** Это применение правил, а не переключение канала или результат проверки интернета. Завершение и сохранённая причина проверки правил указываются отдельно.

**EN:** This is a rule application, not a channel switch or an internet availability result. Completion and the saved policy reason are separate facts.

**Что делать:** Роутер повторно применил правила VPN без изменения порядка каналов. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The router applied VPN rules without changing channel order. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-ROUTER-OBSERVATION

Состояние Auto / Auto state

**RU:** В этом наблюдении смена порядка каналов не записана. Используйте сохранённое подтверждение выбора на момент события; этап контроллера не считается новым переключением.

**EN:** This observation did not record a channel-order change. Use the saved event-time selection evidence rather than interpreting the controller phase as a new switch.

**Что делать:** Записано состояние Auto; канал не менялся. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Auto state was recorded; the channel did not change. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-DIRECTION-NOT-SAVED

Направление перехода не сохранено / Switch direction not recorded

**RU:** В событии нет корректно сохранённых исходного канала или назначения. Текущая пара и этап контроллера не используются для выдумывания направления.

**EN:** The event lacks valid explicit source or destination metadata. The current pair and controller phase are not used to invent the missing direction.

**Что делать:** Сохранённые данные не подтверждают направление этой операции. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** The saved data does not establish the direction of this operation. Read the separate saved reason code if present; observation and a confirmed route change are different.

## EVENT-VENDOR-WAIT

Ожидание операции роутера / Waiting for router operation

**RU:** Обнаружен обработчик или блокировка GL.iNet. Контроллер временно откладывает решения о переключении; сама запись не подтверждает отказ VPN. Конкретный обработчик мог не сохраниться в истории.

**EN:** A GL.iNet worker or lock was observed. The controller defers switching decisions until it clears; the record alone does not establish a VPN outage. The exact worker may not have been retained.

**Что делать:** Ожидание завершения штатной сетевой операции или снятия её блокировки. При наличии смотрите отдельный сохранённый код причины; наблюдение и подтверждённая смена маршрута различаются.

**Action:** Waiting for the stock network operation or lock to clear. Read the separate saved reason code if present; observation and a confirmed route change are different.
