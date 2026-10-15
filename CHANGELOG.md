# История изменений

## 0.2.0-alpha2 — HomenS.AI Style

- Repositories renamed to `homensai-gl-mt6000-auto-vpn`, local Gitea first, GitHub second.
- Embedded selected HomenS.AI Style 1.14.3 resources: Nordic tokens, original animated robot, author footer and local IBM Plex fonts with notices.
- Version shown top right, author robot in header, English/Russian UI retained. No private style repository history is copied.
- ipk builder preserves binary font bytes; regression added. 33 unit tests passed, EN/RU visual checks on an isolated synthetic fixture.
- Installed on GL-MT6000: agent version, three healthy active paths, 12 activity profiles and hourly Telegram settings verified. Full live LuCI UI verification remains limited by the browser-session issue.
- Native automatic VPN switching remains unavailable. Live disruption tests need an agreed window and rollback plan; none were performed for this release.


## 0.2.0-alpha1 — public alpha

- English UI by default, English/Russian selector, developer link and version badge.
- Persistent daily activity accounting: healthy/failed/unknown/idle durations, observed connections and distinct failure episodes. Grouped OpenVPN/WireGuard histograms: today, seven calendar days, current calendar month. History starts with this version.
- Bilingual installation guides and copyable ChatGPT/Claude installation prompts; verified author/book links and local-first publication policy.
- 32 unit tests, JavaScript syntax check and English/Russian visual fixture checks passed. Visual fixture uses explicitly synthetic data and omits the real LuCI settings form.
- Monitor mode only; operation/automatic failover remains unavailable. No weekly/monthly device soak or live switch/rollback validation is claimed.
- Versions through alpha9 were installed and measured on the GL-MT6000; this public version has not yet completed device installation/UI validation.


## 0.1.0-alpha9 — подготовлено, установка не подтверждена

- Номер версии в правом верхнем углу страницы; версия агента, Makefile и пакета согласованы.
- Мастер первичного подключения Telegram и отдельная кнопка повторной настройки. Сохранённый токен не подставляется в поле; пустое поле при повторной настройке сохраняет прежний токен.
- Время последней проверки слева в мониторе служб. Неактивные профили без измерения показывают прочерк.
- При обновлении уже зарегистрированного RPC-плагина больше не выполняется reload rpcd, чтобы не завершать сессии LuCI. Первая установка по-прежнему регистрирует новый плагин.
- Проверены синтаксис JavaScript и 28 unit-тестов. Проверка дизайна и мастера на устройстве ещё не выполнена: браузерный инструмент возвращает ERR_BLOCKED_BY_CLIENT при открытии LuCI. Последняя подтверждённая установленная версия — alpha8.

## 0.1.0-alpha8 — 15.10.2026

- Добавлены оформление страницы, карточки подключённых серверов, четыре сводных показателя, SVG-график реальных HTTPS-измерений и адаптация к узкому экрану.
- Настройки перенесены в раскрываемый блок. Неактивные профили отображаются нейтрально, а не как ошибка.
- График показывает последний доступный час; разрывы больше 90 секунд не соединяются. Это HTTPS-задержка, не скорость загрузки.
- Проверки: синтаксис JavaScript, 28 unit-тестов; пакет установлен на роутер. При обновлении выявлено завершение сессии RPC; исправление запланировано в alpha9.

## 0.1.0-alpha7 — 15.10.2026

- Установлено и запущено наблюдение на GL-MT6000, GL.iNet 4.11.0 / OpenWrt 21.02.
- Проверены реальные HTTPS/DNS-пробы трёх подключённых профилей: два OpenVPN и один WireGuard. Всего обнаружено 12 профилей.
- Работает накопление трафика уникальных VPN-интерфейсов; объём текущего месяца неполный, с момента начала наблюдения.
- Добавлены Telegram-отчёты, включение, интервал 5–10080 минут, Chat ID и скрытое поле токена в настройках LuCI. На устройстве проверена отправка при интервале 60 минут.
- Токен не выдаётся в RPC-инвентаризации, статусе, отчёте или ошибке; конфигурация службы получает права 0600. Токен хранится в UCI на роутере, администратор имеет к нему доступ; резервные копии конфигурации также могут его содержать.
- Исправлены каталоги в tar-архиве ipk, обработка rpcd session argument, отсутствие Python time.tzset в сборке OpenWrt и согласованность двух меню LuCI.
- Проверки: 28 локальных unit-тестов, фактическая установка, реальные измерения и отметка успешной отправки Telegram на устройстве.

### Ограничения

- Автоматическое переключение VPN отключено. Не проверены LAN-путь и IPv6. Неактивные профили автоматически не подключаются.
- Интерфейс пока использует таблицы LuCI; оформление и графики локального прототипа не перенесены.
- Telegram отправляет текущий статус и изменения состояния из памяти процесса, а не полную архивную статистику простоев за неделю/месяц. События могут потеряться после перезапуска. Месячный счётчик и агрегаты сохраняются по checkpoint.
- Первый отчёт отправляется при включении; следующие — через заданный интервал от успешной отправки, с точностью до раунда наблюдения. При ошибке повторная попытка через 5 минут; длительное отсутствие сети может задержать доставку.
- Перезагрузка RPC во время установки может потребовать повторного входа в LuCI. Ошибка 403 в старом браузере пока исследуется; IP-бан не подтверждён.

### Промежуточные сборки

- alpha2: проверка RPC после локальной сборки.
- alpha3: исправлены отсутствующие каталоги ipk.
- alpha4: совместимость времени OpenWrt, первый успешный запуск.
- alpha5: Telegram и настройки отчётности.
- alpha6: версия ресурса интерфейса для обхода старого кэша.
- alpha7: согласованы legacy controller и menu.d.
