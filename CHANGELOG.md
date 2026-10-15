# История изменений

## 0.5.0-alpha1 — persistent history and client trial workflow

- Expiry/stop no longer blindly returns to a failed source: retain the reserve with explicit partial-result status, await actual client stop verification, and preserve committed state over restart.
- Added bounded, checksummed persistent controller history with previous-good backup, monthly counters and deduplication across restart; no transaction tokens, exit IP or kernel logs persisted there.
- Added typed authenticated native_confirm/native_stop RPCs. ACK no longer requires UCI apply, which could restart the waiting supervisor. Stop is durably latched across restart; a new explicit trial nonce is required to resume.
- Added Windows PowerShell 7 LAN helper: gateway/DNS/IPv6 checks, explicit router DNS and HTTPS verification, strict exit match, no-proxy/no-redirect router login, private password input and stop-on-exit. Wrong gateway refuses before login.
- Added EN/RU trial guidance, helper download, restore request, persistent history/monthly counters and explanatory blocker text. Telegram reports use actual controller state and scoped history rather than unconditional disabled text.
- Fixed history gating before releasing the worker, expiry/stop guard cleanup, late error reporting, and fake PID test syscall mocking. 76 Python tests, Lua 5.1 inventory checks and PowerShell SelfTest pass; four own-process history crash boundaries tested.
- Native switching, HNAT verification and positive LAN acceptance remain unverified on the real device. No outage test before neighbouring tasks confirm checkpoint/pause. See TODO-WORKING-SYSTEM.md.


## 0.4.0-alpha8 — experimental native controller candidate

- Added a real, narrowly scoped existing-rule adapter, independent supervisor, checksummed journal, guarded apply/rollback and mandatory external client confirmation. Defaults disabled; production switching not validated.
- Added explicit, bounded acceleration preparation and strict runtime verification. Device alpha7: shortcut_fe unloaded, HNAT disable remains unverified. No force unload or package removal.
- Fixed own-service upgrade restart, late external changes, orphan child cleanup, trial replay and unconfirmed client timeouts. 52 package/monitor/controller tests and 9 lab tests pass.
- Owner remote-work priority: device stays alpha7/monitor with native disabled; alpha8 is not installed. No live VPN switch/guard/rollback test claimed.
- See docs/NATIVE-EXPERIMENTAL.md and docs/WORKLOG.md for actual results, internal alpha1–alpha7 revisions and limits.


## Licensing revision — 2026-10-15

- Selected MIT with author website in the mandatory copyright notice.
- Added project-specific MIT permission for bundled author-owned Style assets; IBM font licences remain unchanged.
- Added licence files for future package builds. Existing release archives and installed router package were not replaced. Runtime version remains 0.3.0-alpha1.


## 0.3.0-alpha1 — read-only failover planning

- Studied mwan3/OpenWrt 21.02, VPN Guardian rollback and the statically audited GL.iNet worker/route/DNS/conntrack paths; no third-party code copied.
- Added native monitor-backed dry-run plans, explicit source/reserve selection, 3-failure/2-success gates and blocking prerequisites; no apply RPC or VPN write path.
- Added an executable Python transaction contract to the lab: durable intent, independent-watchdog prerequisite, scoped gate, ownership checks, verify/commit/rollback/recover. No native GL.iNet adapter is supplied.
- 36 monitor/package tests and 9 transaction tests passed; 200 synthetic combinations include 60 simulated crash cases. Initial late-gate rollback defect was found and fixed. See docs/FAILOVER-RESEARCH.md.
- No live VPN/network/firewall/DNS mutation; operation mode remains unavailable.


## Documentation revision · 15.10.2026

- Added EN/RU passports of the exact router/firmware/LuCI configuration, read live from the device, plus a redacted JSON snapshot.
- Distinguished LuCI base/UI version from metapackage/module versions, and GL.iNet panel Update Time from an unverified firmware build date.
- Recorded actual installed package 0.2.0-alpha2-1 and running agent 0.2.0-alpha2; linked the evidence from README, installation and validation guides.
- Documentation-only change: application/package version and binary unchanged. No serial, device ID, MAC, network addresses, tokens or private profile names published.


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

## 0.5.0-alpha2
Fix native supervisor startup on router Python without time.tzset using libc fallback. Three regression tests. Device acceptance pending.

## 0.5.0-alpha3
Recognise fresh GL-MT6000 HNAT hook readback; stale/inconsistent responses remain unknown.
