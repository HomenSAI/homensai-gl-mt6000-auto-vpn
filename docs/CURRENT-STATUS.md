## Alpha48 source: one colour rule, fewer texts / Одно правило цветов, меньше текста

- Owner colour rule for every channel lamp and card: green = works in Auto; yellow = alive and waiting to be switched on by Auto (also when Auto is off); grey = waiting for the router's answer (no fresh data, check running, switch pending); red = error, does not work.
- Texts: "Primary/Reserve channel: alive and waiting to be switched on by Auto".
- The Auto card no longer shows "About these checks", the scope sentence, "Help: no internet?" or "How two-channel Auto works"; these are in the Help topic "How two-channel Auto works".
- Removed: "What happens if…", "Last thing that happened", "Why this channel is not available", the selection-pending message.
- Go back floats bottom-right above Top on every page.
- Statistics moved into Advanced settings between Tests and Monthly traffic.

UI only.

Одно правило цветов для всех ламп, лишние тексты убраны или перенесены в «Помощь», плавающая «Вернуться назад», «Статистика» в расширенных настройках.

---

## Alpha47 source: Auto countdown and clearer screens / Обратный отсчёт Auto и понятнее экраны

- The Auto button shows a countdown ring along its inner edge with the seconds left. The expected time is the median of the last five measured starts or stops in this browser; the defaults are 30 s for a start and 10 s for a stop. When the router is slower, the button shows the overrun (+N s) instead of freezing at zero.
- The Overview menu and the Auto lamp open at the top of the Automatic VPN failover card.
- In "Your VPNs" the lamps form one column and the status text is left-aligned in the next column.
- The failure test names the channel as primary or reserve, with the country and protocol.
- The System readiness intro is rewritten in plain words.

UI only.

Обратный отсчёт на кнопке Auto, «Обзор» открывается с блока Auto, ровные столбцы в «Ваши VPN», понятное имя канала в тесте сбоя, простой текст на странице готовности.

---

## Alpha46 source: reset buttons, failure test, Go back / Сброс графиков, тест сбоя, «Вернуться назад»

- Every chart and statistics card (latency, live and 2-hour switching, outage statistics, transition evidence, traffic, speed ranking) has Reset chart. The router saves the old data into a checksummed archive (/etc/homensai-vpn/stats-archive, newest 10 kept) and only then starts measuring from zero. The monitoring agent applies the reset in its own loop. The button reports success only after the router confirms; failures show a catalogued code (STATS-RESET-*).
- The channel failure test is back on the Tests page (it was hidden in the hybrid build).
- Every page ends with "Go back", which returns to the previous page and scroll position. The Auto lamp in the sidebar opens Automatic VPN failover.
- A working spare channel is amber, neither green (in use) nor red (failed).
- RESERVE-ALREADY-FIRST: when the GL priority list already puts the reserve first, Auto keeps running.
- The 2-hour chart shows outages and blocks like the live chart. The latency table shows check losses.
- The status RPC caches the slow diagnostic for 15 s.

Source only until installed.

Кнопка «Сброс графика» на всех графиках и статистике (с архивом), тест сбоя канала снова в «Тестах», «Вернуться назад» внизу страниц, лампа Auto ведёт к блоку Auto, рабочий запасной канал жёлтый.

---

## Alpha45 source: plain wording across the interface / Понятные надписи во всём интерфейсе

Owner-approved rewrite of about 96 confusing labels (jargon such as identity, binding, metadata, planner, path confirmation, external LAN, bare "unknown"/"not confirmed") into plain statements, including error short names. Logic, codes and long help texts unchanged. Source only.

Около 96 непонятных надписей заменены простыми формулировками по согласованию с владельцем.

---

## Alpha44 source: the Auto button sets everything up itself / Кнопка Auto настраивает всё сама

Owner rule: the user presses Auto and does nothing else. Start now repairs failed router preparation that needs no restart (stock VPN boot, VPN autostart flags, hardware acceleration setting, SFE boot) with the same reviewed writer as the preparation buttons: the original value is preserved and the result read back; a restart-only fix still ends in a named refusal. Start refusals and a failed start are shown once in their own window, so the Auto card layout stays the same. A working channel is green everywhere (card and sidebar); with Auto off it reads "Ready for automatic mode". Source only.

Кнопка Auto сама исправляет подготовку роутера, которой не нужна перезагрузка; ошибки запуска показываются отдельным окном; рабочий канал везде зелёный, без Auto — «Готов к работе в автомате».

---

## Alpha43 source: page no longer stops refreshing; defined states everywhere / Страница не зависает

Alpha42 on the router threw "ids is not defined" in the delay panel whenever a channel had no successful check; the exception stopped every refresh, so pages stayed empty, cards showed "Status request failed" and diagnostics showed "unknown". Fixed with a regression test. Owner rule applied: no bare "unknown". Missing data always names its cause and catalogue code (STATUS-REQUEST-FAILED, MONITOR-DATA-STALE, VENDOR-OBSERVATION-PENDING); channel cards say plainly whether the VPN server connection is up and whether your internet goes through the channel; sidebar channel lamps show the real channel state (working green, unreliable or being checked yellow, failing or no data red, grey only when switched off in the router). Source only.

Исправлено исключение панели задержек, из-за которого страница переставала обновляться и показывала «Ошибка получения статуса» и «неизвестно». Отсутствие данных всегда называет причину и код; лампы каналов показывают реальное состояние.

---

## Alpha42 source: Auto recovers by itself, no silent failures / Auto восстанавливается сам

Owner requests after alpha41: renaming a tunnel switched Auto off and it did not return; Start gave no error; "no fresh measurement" and unclear diagnostics wording; the live chart showed an empty line when channels failed; the Auto button should sit level with the traffic light; the Readiness page waited forever; an error link did nothing. Changes: tunnel names no longer count as policy identity; a running session or a Start that meets a change made outside the app archives the old session and adopts the new settings by itself (at most three times in 15 minutes, never while the router is held on the reserve); the status now names the reason of a failed Start (`auto_control.failure`) and the Auto card shows its catalogued code with description and remedy; every channel shows its latest router check result (what failed, when) instead of "no measurement"; all comparisons with router timestamps use one router clock (a PC clock a few seconds behind no longer freezes "Waiting for the router"); plain wording for the router diagnostics with catalogue codes (VENDOR-REASON-UNOBSERVED, PAIR-EXTERNAL-*, PAIR-RECOVERY-REQUIRED, PAIR-READOPTED); the live chart draws "Auto blocked" and "no working channel"; the remedy link navigates inside the app; the Auto button is level with the traffic light; long labels wrap inside their card. Source only: not installed; the MT3000 runs alpha41 with its pair held (PAIR-EXTERNAL-POLICY-CHANGE).

Auto сам принимает настройки, изменённые вне приложения; неудачный запуск показывает код, описание и решение; каналы показывают последнюю проверку; график показывает блокировку и отсутствие рабочих каналов; кнопка Auto вровень со светофором; страница «Готовность» не зависает при отставании часов ПК. Только исходник.

---

## Alpha41 installed: channel reliability indicator / Индикатор надёжности канала

Owner request: say why a channel shows a failure. A channel whose router checks failed in at least 20% of the cycles over the last 5 minutes now reads "Reliability problem: check loss N% (X of Y checks in 5 min)" with the new catalogue code CHANNEL-UNRELIABLE (meaning and remediation in the error table). A connected tunnel that mostly passes now but is unreliable is yellow, not green. The Tests page recommendation is computed from the loss statistics: keep traffic on the channel with lower loss, replace the unreliable server, and name the best measured alternative (at least 20 checks and 95% success) or say that a speed test is needed. This is the measured share of failed checks, not an ICMP packet-loss figure, and it changes no setting or route. Installed on the dedicated MT3000 with Auto ON; Auto switched to the working reserve because the primary lost packets. [Verification](VERIFICATION-ALPHA41-INSTALLED-2026-10-27.md).

Канал, у которого проверки роутера не прошли не менее чем в 20% циклов за 5 минут, теперь подписан «Проблема с надёжностью: потери проверок N% (X из Y за 5 мин)», код CHANNEL-UNRELIABLE описан в таблице ошибок. Рекомендация считается по статистике потерь: держать трафик на канале с меньшими потерями, заменить ненадёжный сервер, назвать лучший измеренный кандидат или предложить тест скорости. Это доля непройденных проверок, не ICMP-потеря пакетов; настройки и маршруты не меняются. Установлено на MT3000, Auto включён.

---

## Alpha39 installed: stopped channel is started / Остановленный канал запускается

Owner-reported defect: the reserve client was enabled but stopped (no boot start), so the GL page showed "Connecting..." forever and Auto stayed BLOCKED as PROFILE-IDENTITY-CHANGED. Auto now starts such a client itself at Start and while running (Stop-fenced, one attempt per 120 s, four per 15 minutes, restored on Stop) and reports an unconnected reserve as the new RESERVE-NOT-CONNECTED blocker with catalogue entry and remediation. Clients the operator disabled are never touched. Alpha37 was installed first and proved the start works (the reserve connected with DNS and HTTPS passing), but the stock client then added gl_wan_like / gl_bwa_* options to a firewall zone, which Auto read as an external configuration change and held the pair (PAIR-EXTERNAL-CONFIG-CHANGE). Failed evidence is preserved privately. Alpha38 ignores exactly those four stock options when comparing the protected firewall and lets Stop undo them with ifdown; it was installed and the first real failover to the reserve then worked, but the stock firmware tidied stopped leftover client sections (ovpnclient1) out of network and dhcp, which Auto read as PAIR-EXTERNAL-NETWORK-CHANGE and held the pair. Alpha39 ignores only stopped (disabled) wgclient/ovpnclient leftovers that are not the selected pair in the network identity and dhcp digest. Installed on the dedicated MT3000 with Auto ON; it automatically switched to the working reserve because the primary lost 71% of packets. [Verification](VERIFICATION-ALPHA39-INSTALLED-2026-10-27.md). Not published.

Исправлена ошибка: резервный клиент был включён, но не запущен, GL-страница вечно показывала «Connecting...», а Auto стоял в BLOCKED. Теперь Auto сам запускает такой клиент (с защитой от Stop, не чаще раза в 120 с и четырёх раз за 15 минут) и показывает неподключённый резерв как RESERVE-NOT-CONNECTED. Отключённые оператором клиенты не трогаются.

---

## Alpha36 installed: Auto operation diagram / Схема работы Auto установлена

Help now contains a responsive diagram of monitoring, switching safeguards and return. It displays router-provided settings, marks unavailable data and respects the selected return policy. Alpha36 is installed on the dedicated MT3000; prior ON Auto restored and both channels passed router checks. [Verification](VERIFICATION-ALPHA36-INSTALLED-2026-10-27.md).

---

## Alpha35 configurable Auto policy installed / Настраиваемые правила Auto установлены

Owner-requested default policy and editable thresholds, times and rolling attempt limit are implemented in one reviewed Settings form. Existing configuration/history are preserved. Dual-runtime CI passed and alpha35 was installed on the dedicated MT3000; prior ON Auto was restored and both channels passed router DNS/HTTPS checks. [Verification](VERIFICATION-ALPHA35-INSTALLED-2026-10-27.md).

---

## Alpha34 installed; sidebar icon verified / Alpha34 установлена

**0.9.1-alpha34-1**, dashboard110/ui82, installed on the dedicated MT3000. Desktop C rail fits the icon-only Advanced control and scrollbar; full localized label/tooltip and keyboard operation remain. A/B and mobile keep their text. Seven C browser cases and four A/B cases passed; exact dual-runtime CI passed. Prior ON Auto restored to RUNNING / OBSERVING with both VPNs healthy. [Verification](VERIFICATION-ALPHA34-INSTALLED-2026-10-26.md) · [Resume](handoff/NEXT-AI-ALPHA34-INSTALLED-2026-10-26.md). Publication verified separately.

---

## Alpha34 source validation checkpoint / Локальная проверка меню C alpha34

Owner requests a usable icon where the Advanced label was clipped by the narrow instrument-panel rail and scrollbar. The desktop C rail is 84 px; the toggle has a keyboard-operable icon, full localized accessible name/tooltip and unchanged expanded-menu behavior. A/B and mobile retain the text. At this earlier checkpoint installation had not yet been performed; see the current alpha34 delivery above.

---

## Alpha33 installed; all requested changes verified / Alpha33 установлена

**0.9.1-alpha33-1**, dashboard109/ui81. Real two-channel speed test confirmed cooperative pause, low daemon CPU and automatic monitor/Auto restoration with unchanged VPNs/config/intent/PIDs. Responsive reference table and truthful partial-connectivity/wait/start diagnostics passed native Chromium checks; actual per-endpoint data now reaches RPC. Auto remains ON / RUNNING / OBSERVING. [Verification and limits](VERIFICATION-ALPHA33-INSTALLED-2026-10-26.md) · [Resume](handoff/NEXT-AI-ALPHA33-INSTALLED-2026-10-26.md). Publication is separately verified by release metadata.

---

## Alpha33 endpoint diagnostics integration / Интеграция диагностики alpha33

Alpha32 is installed with Auto ON and correct HTTP/UI assets. Actual device verification caught endpoint details stripped by the vendor-identity observer. Alpha33 adds bounded nested sanitization, preserves the details for the matching profile and removes them on a rebind; a regression covers the complete observation boundary and secret-field exclusion. Final CI/deployment pending. Speed-test pause remains physically proved on alpha31 and retained unchanged.

---

## Alpha32 combined diagnostics and layout under validation / Общие правки alpha32

Owner's latest requests are included with the physically proved alpha31 speed-test pause: wrapped reference table, partial/zero/unknown HTTPS wording, per-endpoint errors, correlated same-check rows, vendor-operation wait and pending-Start labels. Alpha32 full immutable CI and deployment are pending. Dedicated MT3000 currently runs alpha31; both actual speed tests completed, CPU after quiet-window acknowledgement 11.4%, Auto/monitor restored with same processes/config/intent. [Physical alpha31 checkpoint](../qa/MT3000-ALPHA31-2026-10-26.json).

---

## Alpha31 speed-test pause under validation / Проверяется пауза для теста скорости

Owner-requested cooperative pause of Auto and background monitoring during bounded speed tests. Existing VPNs/routes and prior enablement are retained; monitor resumes first, Auto follows fresh measurement, manual Stop wins. CPU admission occurs after both safe-point acknowledgements. Local focused tests and 63 UI suites passed; immutable full CI, installation and real speed-test proof pending. Actual dedicated MT3000 remains alpha30 with Auto ON.

---

## Alpha30 installed; Auto running / Alpha30 установлена, Auto работает

**0.9.1-alpha30-1**, dashboard106/ui78, installed and read back on the dedicated MT3000. The former expanded interface is restored; new Minimum retained. Actual ordinary Start confirmed RUNNING / OBSERVING with two healthy VPNs, no reconnect, protected settings preserved. Auto remains ON. Dual immutable CI, 63 UI suites and Chromium 4×33 passed. [Device and scope](VERIFICATION-ALPHA30-INSTALLED-2026-10-26.md) · [Resume](handoff/NEXT-AI-HYBRID-ALPHA30-INSTALLED-2026-10-26.md). Publication state is recorded by the linked release metadata; source/device evidence alone is not publication proof.

Исправлены устаревшая привязка резерва, проверка отключённого удалённого интерфейса и бесконечное ожидание Start. На реальном роутере Auto включился; свежие DNS/HTTPS проходят у обоих каналов. Main/stable, MT6000 и сеть Windows сохранены.

---

## Alpha30 fixes physical Start failure / Alpha30 исправляет физический отказ Start

Alpha29 installed and actual HTTP/RPC payload verified. Its ordinary Start failed safely with PAIR-SYSTEM-001 because guard-device discovery queried the removed, disabled ovpnclient1. Existing active VPNs/routes were preserved. Alpha30 skips administratively disabled clients and still blocks missing/malformed enabled client state with GUARD-DEVICE-UNVERIFIED. Full CI, installation and actual Start of alpha30 are pending. No alpha29/30 publication yet.

---

## Alpha29 source in validation / Alpha29 проходит проверку

Owner-directed restoration of the former expanded interface while retaining the new Minimum; terminal Start refusal and selected-client-slot fixes. Native Chromium passed 4×33 synthetic checks and 63 Node UI suites passed. Frozen dual-runtime CI and physical installation/startup are pending. The router still has alpha28 with Auto OFF after ordinary cancellation of the hung request. No GitHub publication has been performed for alpha29.

Возвращён прежний расширенный интерфейс, новый «Минимум» сохранён. Исправлены бесконечное ожидание отказавшего Start и привязка к фактическому второму VPN-клиенту. До физической установки это результат проверки исходника.

---

## Alpha28 installed on dedicated MT3000 / Alpha28 установлена на MT3000

**0.9.1-alpha28-1**, dashboard104/ui76, is installed and read back on the dedicated GL-MT3000. 90 files/modes, actual HTTP assets, fresh RPC/monitor/controller, settings/terms preservation and independently decrypted pre/post backups passed. Both currently enabled VPNs pass router DNS+twoHTTPS probes. Auto remains OFF; no speed/failover/reboot/native-browser acceptance. [Device verification](VERIFICATION-ALPHA28-INSTALLED-2026-10-26.md) · [Resume](handoff/NEXT-AI-ALPHA28-INSTALLED-2026-10-26.md). No publication/main/stable/MT6000/Windows-network change.

С явного согласия владельца прежняя зависшая сессия передана текущей конфигурации с сохранением исходника, без отката VPN. Затем выполнена штатная установка. Для запуска Auto остаются условия пары/политик; подготовка и Auto Start не выполнялись. После Ctrl+F5 роутер показывает новый интерфейс.

---

## Local alpha28 preparation buttons / Локальные кнопки подготовки

Candidate **0.9.1-alpha28-1**, dashboard104/ui76, product source `7ff1b81f`. Seven reviewed preparation actions for verified MT3000/MT6000 firmware 4.11.0; this does not extend Auto compatibility. Dual immutable CI passed 807 app/113 QA per runtime with explicit complementary skips, 62 UI suites and Chromium 4×22 synthetic checks. IPK SHA256 `58610b1c3355668b9a1de8f20c7dc8d7ca802c6860c3d35ca459ce00558a1ab3`. [Report](diagnostics/PREPARATION-BUTTONS-2026-10-26.ru.md) · [Resume](handoff/NEXT-AI-PREPARATION-BUTTONS-2026-10-26.md). Not published or installed; physical settings and main/stable unchanged.

Добавлены кнопки отключения мешающих настроек с обзором, сохранением исходных значений и проверкой результата. Незавершённое восстановление запрещает запись. Кнопки не запускают Auto и не перезагружают роутер; если нужна перезагрузка, это явно показано. Физическая установка не выполнялась.

---

## Local alpha27 channel fixes / Локальные исправления каналов

Candidate **0.9.1-alpha27-1**, dashboard103/ui75, source `601ad227`. Dual immutable Linux CI passed: 787 application / 113 QA tests per runtime with explicit complementary skips, 61 UI suites; Chromium 4×12 synthetic checks passed. Equal IPK SHA256 `dba3827e0e3fdc8c0cc81504cdc4504da0d96da0def3fe670b582f7390d4e54f`. [Fix report](diagnostics/CHANNEL-RECONFIGURATION-FIX-2026-10-26.ru.md) · [Resume](handoff/NEXT-AI-CHANNEL-RECONFIGURATION-2026-10-26.md). Local only; not published or installed. Main/stable and physical device settings unchanged.

Исправлены проверки после удаления/замены каналов, восстановление старой сессии и объяснения отказа Auto. На GL-MT3000 остаётся alpha25: ускорение уже выключено, но подготовка не проходит автозапуск WireGuard/штатного VPN; старая сессия расходится с текущей конфигурацией. Установка и эксплуатационная приёмка alpha27 не выполнялись.

---

## Published Minimum UI alpha26 / Опубликован новый дизайн

[GitHub prerelease](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha26) · [Gitea prerelease](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha26). Package **0.9.1-alpha26-2**; six assets per service independently downloaded and SHA256 verified. Main/stable/latest unchanged. [Verification](VERIFICATION-ALPHA26-2026-10-26.md) · [Resume](handoff/NEXT-AI-MINIMUM-ALPHA26-2026-10-26.md). This release was not installed on the physical MT3000; physical acceptance remains separate.

Релиз нового дизайна опубликован и проверен скачиванием. На физический роутер не устанавливался; сведения о старой alpha25 ниже не являются приёмкой новой версии.

---

## Minimum UI alpha26 — design prerelease candidate / 26.10.2026

Implemented and verified source: **0.9.1-alpha26-2**, dashboard102/ui74. Minimum + five-section Advanced menu. [Release notes](RELEASE-0.9.1-alpha26.md) · [Verification](VERIFICATION-ALPHA26-2026-10-26.md) · [Next agent](handoff/NEXT-AI-MINIMUM-ALPHA26-2026-10-26.md). Exact dual-runtime CI, native Chromium canonical-payload fixtures and actual disposable x86 OpenWrt package/RPC/HTTP checks passed. Publication/readback is a separate delivery receipt. This package has NOT been installed on the physical MT3000; the alpha25 installation records below remain historical device evidence. Stable/main are unchanged.

Реализован и проверен новый дизайн. Это отдельный кандидат prerelease, а не заявление о физической установке или суточной приёмке. Далее — подтверждённая доставка и отдельный разрешённый пилот.

---

## Alpha24 quiz position / Позиция чекбоксов

Internal training buttons preserve scroll and meaningful focus through grading, navigation, results, retries, scenes and Help course toggles. Installed on MT3000; AutoONconfirmedreserve.57UI suites and exact dual-runtime CI passed. [GitHub alpha25](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25) · [Gitea alpha25](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha25) — published; four assets each downloaded and SHA256verified. [Verification](VERIFICATION-ALPHA25-2026-10-25.md). Native browser clicks unverified.

## Alpha24 quiz position / Позиция чекбоксов

Training checkbox selection preserves DOM, question, scroll and focus, including polling. Installed on MT3000; AutoONconfirmedreserve.56UI suites and exact dual-runtime CI passed. [GitHub alpha24](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha24) · [Gitea alpha24](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha24) — published; four assets each downloaded and SHA256verified. [Verification](VERIFICATION-ALPHA24-2026-10-25.md). Native browser clicks unverified.

## Alpha23 live speed / Текущая скорость

Measured download/upload graphs for primary and reserve,1s lightweight updates. Installed and verified with an actual bounded two-VPN test on MT3000; AutoONconfirmedreserve. [GitHub alpha23](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha23) · [Gitea alpha23](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha23) — published; four assets each downloaded and SHA256verified. [Verification](VERIFICATION-ALPHA23-2026-10-25.md). Native browser visual unverified.

## Alpha22 combined owner batch / Общая партия

All13changes installed on dedicated MT3000; AutoONconfirmedreserve.54UI suites and exact dual-runtime CI passed. [GitHub alpha22](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha22) · [Gitea alpha22](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha22) — published; four assets per service downloaded and SHA256verified. [Verification](VERIFICATION-ALPHA22-2026-10-25.md). Native browser visual unverified.

<!-- doc-role: current-delivery-record -->
# Current status / Текущее состояние —25.10.2026

**Alpha21 installed, AutoON/confirmedreserve/bothVPN healthy.** Enabled Auto grants simplified access even with unfinished setup/test markers. OFF/unconfirmed shortcut is red with hover/focus/tap setup tooltip; Escape dismisses it. Actual OFF/ON data cases passed; markers remainfalse and are no longer an access blocker. Native-browser visual NOT_VERIFIED.

**Alpha21 установлена.** Доступ при включённом Auto открыт независимо от мастера. Выключенный режим: красная кнопка и подсказка. Проверены реальные OFF/ON состояния без подмены отметок. [Отчёт](VERIFICATION-ALPHA21-2026-10-25.md) · [QA](../qa/AUTO-ACCESS-ALPHA21-2026-10-25.json) · [Роутер](../qa/MT3000-ALPHA21-2026-10-25.json). [GitHub alpha21](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha21) · [Gitea alpha21](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha21) — published and downloads verified. Stable0.9.0 unchanged.

## Previous alpha20 delivery — earlier stricter access rule superseded

<!-- doc-role: current-delivery-record -->
# Current status / Текущее состояние —25.10.2026

**Alpha20 installed on MT3000, AutoON/confirmedreserve/bothVPN healthy.** Guarded Simplified interface button beside heading, visible unavailable reason, click-time/freshness validation, clipped skip-link fix and readable completed steps. Current setup remains incomplete, so the shortcut explains the missing setup rather than bypassing it. Settings/history/terms retained. Native-browser visual NOT_VERIFIED.

**Alpha20 установлена, Auto включён на резерве.** «Упрощённый интерфейс» расположен справа от заголовка, недостающий шаг указан под кнопкой. Исправлена читаемость. [Отчёт](VERIFICATION-ALPHA20-2026-10-25.md) · [QA](../qa/HEADER-ALPHA20-2026-10-25.json) · [Роутер](../qa/MT3000-ALPHA20-2026-10-25.json). [GitHub alpha20](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha20) · [Gitea alpha20](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha20) — published and downloads verified. Stable0.9.0 unchanged.

## Previous alpha19 delivery

<!-- doc-role: current-delivery-record -->
# Current status / Текущее состояние —25.10.2026

**Alpha19 installed on MT3000, Auto ON / confirmed reserve, both VPN DNS/HTTPS healthy.** Selected startup card is integrated with actual settings, current-pair evidence and freshness. The owner's unfinished setup flags are preserved: first entry is the existing wizard until explicitly completed. Completed-setup card was verified with real data and temporary in-memory flags only. Native-browser visuals NOT_VERIFIED.

**Alpha19 установлена, Auto включён на резерве.** Карточка подключена к реальному состоянию и появляется только после завершённых настройки/проверок. На текущем роутере первым открывается незавершённый мастер. [Отчёт / report](VERIFICATION-ALPHA19-2026-10-25.md) · [QA](../qa/SIMPLE-HOME-ALPHA19-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA19-2026-10-25.json). Alpha19 actual GitHub/Gitea releases and all downloaded assets verified; previous API blocker resolved. Stable0.9.0 unchanged.

## Previous alpha18 delivery

<!-- doc-role: current-delivery-record -->
# Current status / Текущее состояние —25.10.2026

**Alpha18 installed on MT3000, Auto ON / confirmed reserve.** Help after Settings: 8 lessons, 11 questions, direct navigation, scores and wrong-only retry. Meaningful event/state labels open explanations; causes remain separate. Weekly latency and existing data retained. Full dual-runtime CI: 774 app /112 QA each, 50 UI suites. Native-browser visuals not verified.

**Alpha18 установлена, Auto включён / резерв подтверждён.** «Помощь» после «Настроек»: уроки, вопросы, баллы и повтор ошибок. События и состояния открывают расшифровку. [Отчёт / report](VERIFICATION-ALPHA18-2026-10-25.md) · [QA](../qa/EVENTS-HELP-ALPHA18-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA18-2026-10-25.json). [GitHub alpha18](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha18) · [Gitea alpha18](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha18) — published, assets downloaded and verified. Stable 0.9.0 unchanged.

## Previous alpha17 delivery

<!-- doc-role: current-delivery-record -->
# Current status / Текущее состояние —24.10.2026

**0.9.1-alpha17 установлена наMT3000/4.11.0**, AutoON/резерв, обаVPNDNS+2HTTPS. История задержек/ползунки поддерживают1–168часов/7суток по настройке1–7дней. Старые наблюдения/настройки/terms/4speedзаписи сохранены; удалённые дни не выдумываются. [Report17](VERIFICATION-ALPHA17-2026-10-24.md) · [QA](../qa/LATENCY-ALPHA17-2026-10-24.json) · [Physical](../qa/MT3000-ALPHA17-2026-10-24.json).

Alpha17 exact-source dual-runtimeCI774app/112QA each/47UI and installedx86VM10081row weeklyfile/actualRPC test passed; VM poweredoff. Physical source/files/API/legacycheckpoint/settings/terms/backups and AutoONreserve verified. Published and downloaded/hash-verified: [GitHub alpha17](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha17) · [Gitea alpha17](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha17). Details in the report. Native visual/externalLAN/IPv6/KillSwitch scopes remain unverified. Main/stable0.9.0 unchanged.

## Previous alpha16 delivery / предыдущая доставка


**0.9.1-alpha16 установлена наMT3000/4.11.0**: AutoON/резерв, обаVPNDNS+2HTTPS. «Состояние» шире, код под схемойM/R целиком, «Событие» уже.87файлов/прав/RPC/HTTP8080/pinnedHTTPS, настройки/условия,4speedзаписи и193/193encryptedbackups проверены. [Alpha16report](VERIFICATION-ALPHA16-2026-10-24.md) · [QA](../qa/EVENTS-ALPHA16-2026-10-24.json) · [Physical](../qa/MT3000-ALPHA16-2026-10-24.json).

**Alpha16 is installed**, AutoON/confirmedreserve. State/code layout updated; four successful speed samples and manual speed settings retained. Exact-source dual-runtimeCI771app/112QA each/47UI passed after isolating a timing-dependent test fixture; product payload unchanged. Native-browser visual acceptance unavailable; installedCSS/servedbytes verified. Published/download-hash-verified: [GitHub alpha16](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha16) · [Gitea alpha16](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha16). Details are in the report. Main/stable0.9.0 unchanged.

## Previous alpha15 delivery / предыдущая доставка


**0.9.1-alpha15 установлена наMT3000/4.11.0**: AutoВКЛ/подтверждёнрезерв, обаVPNDNS+2HTTPS. Исправлена кнопка теста скорости и добавлен график скачивания/отдачи под серверами. Четыре реальные успешные записи, включаядве после установки. [Отчётalpha15](VERIFICATION-ALPHA15-2026-10-24.md) · [QA](../qa/SPEED-ALPHA15-2026-10-24.json) · [MT3000](../qa/MT3000-ALPHA15-2026-10-24.json).

**0.9.1-alpha15 is installed onMT3000/4.11.0**, AutoON/confirmedreserve, bothVPN DNS+2HTTPS. Speed launch works through explicit review and a measured download/upload chart appears below servers. Exact-source two-runtimeCI771application/112QA each/47UI,87installedfiles/modes/servedHTTP+pinnedHTTPS,settings/terms and independently restored192/193entryencryptedbackups verified. Four actual goodput samples retained. Native-browser visuals were blocked byComputerUse URL identification and are not certified.

[Alpha14 documentation audit](DOCUMENTATION-AUDIT-2026-10-24.md) and its actualx86VM results remain separate historical evidence. Stable0.9.0/main unchanged. Published and downloaded/hash-verified: [GitHub alpha15](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha15) · [Gitea alpha15](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha15). Exact outcomes are in its verification report.

[Русское руководство](CURRENT-STATE.ru.md) · [English guide](CURRENT-STATE.en.md) · [ChangesRU→EN](LATEST-CHANGES.md) · [Local access](LOCAL-ACCESS.md)
