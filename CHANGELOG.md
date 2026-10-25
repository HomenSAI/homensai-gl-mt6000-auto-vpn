# Changelog

## 0.9.1-alpha22 —25 October2026 / 25 октября2026

Combined13 owner corrections: one cancellable Auto power button, stable language/page navigation, simplified-view top entry/Advanced menu, compact preparation/chart panels, native wizard checkboxes and short diagnostic links.

Общая партия13 правок: единая кнопка Auto с отменой запуска, сохранение страницы при смене языка, вход на верх упрощённой страницы/«Расширенное меню», компактные таблицы и графики, чекбоксы мастера и короткие ссылки журнала.


## 0.9.1-alpha21 —25 October2026 / 25 октября2026

Simplified access now follows confirmed enabled Auto alone, regardless of setup/test markers. Off/unconfirmed Auto has a red shortcut and setup tooltip on hover/focus/tap, dismissible with Escape. A running Auto bypasses the unfinished-wizard entry screen without marking it complete. Missing channel data and handovers render honest card states. Existing Auto start protections unchanged.

Упрощённый интерфейс доступен всегда при включённом Auto независимо от отметок настройки. При выключенном режиме кнопка красная, при наведении/фокусе/тапе показана подсказка. Незавершённый мастер не блокирует вход работающего Auto; его отметки не меняются. Ошибки и переходы каналов отображаются внутри карточки.


## 0.9.1-alpha20 —25 October2026 / 25 октября2026

Added a guarded Simplified interface button beside the page title, with an explicit unavailable reason and click-time revalidation. Fixed the clipped upper-left skip link while retaining keyboard access; completed setup steps keep readable foreground/opacity. No configuration or Auto-mode changes from navigation.

Справа от заголовка добавлена кнопка «Упрощённый интерфейс»: переход только при текущем допуске, иначе показана причина. Исправлена обрезанная ссылка вверху слева; сохранён доступ с клавиатуры и повышена читаемость выполненных шагов. Навигация не меняет Auto или настройки.


## 0.9.1-alpha19 —25 October2026 / 25 октября2026

Selected compact startup card with the original Auto button, primary/reserve identities, measured endpoints/delay and full-menu entry. Current terms, completed setup, current-pair tests and fresh confirmed running Auto are required. Incomplete setup/stale data never become a ready home screen. Explicit deep links and full management remain available. Red is softened50%, green unchanged; button is directly under Auto works.

Выбранная стартовая карточка с исходной кнопкой Auto под состоянием, адресами/задержкой каналов и переходом в полное меню. Допуск только после условий, полного мастера, проверок текущей пары и свежего подтверждения Auto. Красный ослаблен50%, зелёный сохранён. Обновление не отмечает незавершённый мастер выполненным.


## 0.9.1-alpha18 — события и обучение / event explanations and Help learning

«OK» в журнале заменён точным описанием успешной проверки, отдельно от восстановления и переключения. Состояние и событие открывают расшифровку; диагностическая причина имеет отдельную ссылку. Все текущие статические состояния контроллеров покрыты справочником; старые недостающие/противоречивые сведения не превращаются в выдуманный успех. Удержание резерва не выдаётся за остановку общегоAuto, программная команда — за нажатие оператором.

Помощь видна послеНастройки и в спокойном оформлении. В ней встроены8уроков и11вопросов с объяснениями, переходомклюбомувопросу, статистикой/баллами и повтором только ошибок/пропусков с сохранением правильныхответов. Перваяпопытка и текущийрезультат разделены. Обучение не управляет роутером; прежние интерактивные схемы сохранены.

Journal checks, recovery, requests and confirmed transitions now have human descriptions and dictionary links, with separate diagnostic causes. Historical gaps/conflicts never become fabricated switches. Help afterSettings embeds8lessons/11questions, direct navigation, score/firstattempt/attemptstatistics and wrong-only remediation; correct answers and all interactive scenes are retained. Training issues no router-control RPC.


## 0.9.1-alpha17 — семь суток задержек / seven-day latency history

История задержек расширена до7дней по настройке1–7дней; окно1–168часов, правый ползунок «Просмотр последних7суток» перемещает выбранное окно по неделе. Сохраняется прежняя история формата1, без выдуманных старых замеров. Даты видны на широких шкалах, число маркеров ограничено; линии/статистика используют сохранённые минутные данные. Для большого пакета неделя передаётся компактно, прежний суточный хвост оставлен совместимым клиентам.

Latency supports1–168hour windows and panning across the last7days, within configured1–7day storage. Existing format1checkpoints remain valid; deleted days are never reconstructed. Wide axes show dates, markers are bounded and statistics use retained minute samples. Large weeks use compact transport with a legacy daily tail.


## 0.9.1-alpha16 — ширина столбцов истории / saved-history columns

В сохранённой истории «Состояние» расширено до27%, «Событие» сужено до58%, дата занимает15%. Код состояния находится под схемойM/R и не разрывается по дефисам. На узком экране таблица прокручивается горизонтально. Данные, поиск, сортировка, раскрытие и журнал не меняются.

Saved-history State gets27%, Event58%, Date15%. The state code sits below theM/R diagram without breaking inside the code. Narrow screens retain horizontal table scrolling. Data, filtering, sorting, disclosure and live journal behavior are unchanged.


## 0.9.1-alpha15 — запуск теста скорости и график / speed launch and chart

Кнопка запуска доступна для проверки действия и при выключенных тестах. Явное «Включить и запустить» включает ручные измерения с текущими лимитами, оставляет автотесты выключенными и вызывает запуск только после подтверждённого сохранения. Подключённые серверы предварительно отмечены; их можно снять. Повторный запуск при активном задании блокируется, причины отказа показаны рядом. Ниже таблицы — реальные линии скачивания/отдачи, выбор сервера/периода и разрывы вместо нулей при ошибках.

Test speed opens a review even when disabled. Explicit Enable and run confirms saving manual test settings with current limits and auto-new OFF before queueing. Connected servers are initially selected, running jobs prevent duplicate launches, and refusals are visible locally. A server/period chart below the table shows actual download/upload samples with error gaps.


## 0.9.1-alpha14 — documentation and helper review / проверка документации и помощников

Исправлены актуальные руководства установки, справка, четыре промпта RU/EN и мастер. Полная встроенная помощь и справочник кодов формируются из исходников; автоматическая проверка обнаруживает рассинхронизацию. Мастер шага 2 показывает лимит наблюдений и срок хранения. Обучение объясняет роли M/R, историю и конфликт одинаковых адресов роутеров. Условия версии 1 и существующие лицензии сохранены.

LAN-помощник отказывает до отправки пароля/RPC, если маршрут управления ведёт не через выбранный интерфейс. Это проверка маршрута, а не закреплённый HTTP-сокет: последующая смена маршрута остаётся отдельным ограничением. Аварийные скрипты больше не сохраняют незавершённые правки приложения и не меняют сохранённый Auto при ошибке остановки службы. Проверены настоящие скрипты с подставными системными ответами; Telegram-рецепт проверен без отправки запросов.

Current installation guides, Help, four RU/EN prompts and setup are aligned. Full built-in Help and code reference are generated from runtime sources, with drift checks. Setup step 2 exposes observation count and detail-retention controls. Training explains M/R roles, history and overlapping router addresses. Terms version1 and existing licences remain unchanged.

The LAN helper refuses before credential/RPC submission when management uses another interface. It checks routing rather than pinning the HTTP socket; later route changes remain a limitation. Emergency scripts preserve pending app edits and do not change saved Auto after a failed service stop. Actual scripts were exercised with mocked system responses; the Telegram recipe was tested without API requests.

Delivery and complete acceptance require the alpha14 verification report; source changes alone do not update a router or release.


## 0.9.1-alpha13 —2026-10-24

### Русский

- Вся пачка владельца: компактные списки/меню/рекомендации,20строк истории, явные каналы в ошибках, M/R-схемы и сортировка рабочих каналов.
- Настраиваемый живой буфер1–2000 и подробная история1–7дней с реальной очисткой и сохранением общих счётчиков.
- Тест сбоя текущего основного или резерва с проверкой перехода и kernel timeout; legacy LAN-сертификат не требуется для prepared continuous-pair режима.
- Исправлен выбор канонического IPK: закреплённая Linux CI, одинаковыйSHA в Python3.9/3.11, явный gzip level.
- MT3000 установлен, AutoON/резерв и оба VPN подтверждены. Проверки/ограничения — в QA-матрице.

### English

- Complete owner batch: compact lists/navigation/recommendations,20-row history, event-time channel labels, M/R diagrams and working-first monitor rows.
- Configurable live buffer1–2000 and detail retention1–7days with actual pruning and preserved lifetime/monthly counters.
- Current-channel fault tests verify alternate selection and retain kernel timeout, private identity and Stop checks.
- Canonical pinned-Linux package matches Python3.9/3.11 CI; gzip level is explicit.
- Dedicated MT3000 updated; AutoON/reserve and both VPNs verified. See the QA matrix for coverage limits.

## 0.9.1-alpha12 — 2026-10-24

- Основной синий / резервный оранжевый: две серии отказов и явная легенда; старые записи без роли исключены с отдельным архивом.
- Event-time roles from matching configured-pair snapshots rather than transient controller status. Fixed native-state overwrite of outage health; strictly repair the provable prior checkpoint signature.

## 0.9.1-alpha11 — 2026-10-24

### Русский

- Восемь интерактивных учебных схем: запуск/пауза/шаги/сброс; без команд роутеру.
- Исправлены устаревшие требования LAN-теста и советы возврата на основной, пройдены все уроки и викторина RU/EN.
- Обновлены текущие руководства, русский затем английский список изменений и полный индекс документации; опубликован отчёт VM alpha10 с явными ограничениями.

### English

- Eight interactive teaching scenes with playback/pause/steps/reset and no router commands.
- Corrected stale LAN-test and primary-return advice; all lessons and quiz exercised in EN/RU.
- Refreshed current guides, RU-then-EN change notes, complete documentation index and alpha10 VM report with explicit limits.

## 0.9.1-alpha10 — 2026-10-24

- Batch owner UI corrections: compact disclosures, aligned controls, no nullable child text, readable server/channel/protocol and outcome tables.
- Grouped live-state ranges, explicit operator/program/test attribution and transition-time HTTPS delay evidence.
- Hourly failure episodes with retained 1–24h window; preparation before pair selection separated from applied transitions.
- Dual-runtime offline checks pass; native-browser visual acceptance and physical installation remain pending.

## 0.9.0 — 2026-10-23

- Numbered experimental release on main, incorporating the physically checked alpha45 behavior.
- Continuous MT3000 primary/reserve Auto, operator switching while Auto ON, default monitoring and bounded faster startup polling.
- Explicit channel roles, moving/static cards and sidebar lamps; three-level live/stored1–24h graphs; retained viewport/errors and persistent weekly/monthly/lifetime statistics.
- Agreement→illustrated intro→eight-step EN/RU setup/help; bottom unchanged-settings escape and immediate language preview.
- Refreshed public overview, installation/how-to/evidence/roadmap and historical-document context. See [release notes](releases/v0.9.0.md) and [exact release record](docs/RELEASE-0.9.0.md).


## 0.9.0-alpha35 — 2026-10-22

- Explicit prepared-MT3000 continuous Auto starts saved WG/OV profiles, repeatedly fails over and returns after stable recovery; durable ownership and independent Stop/restart recovery.
- Atomic derived process policy synchronization, shared CLI/helper control identity, bounded transition leases and persistent rolling attempt budget.
- Live colored primary/reserve timeline, lightweight read-only RPC, narrow-screen labels and persistent preparation readiness.
- Full dual-runtime681app/107 QA and34UI matrix; real cycles, Start/Stop/startup cancellation, native crash recovery and reboot. Scope/limitations: releases/v0.9.0-alpha35.md.

## 0.9.0-alpha27 — 2026-10-22

- Validated MT6000/MT3000 model choice; actual identity and mismatch rejection.
- Strict MT3000 FW3 native profile, pair-bound derived process policy and journal recovery, asynchronous apply settling.
- Nonce/revision-bound calibration preserving Stop, explicit hosted/external proof scopes and truthful status.
- Route-free Windows witness; kit no longer logs private trial identifiers or copies token-bearing configuration.
- Exact dual-runtime CI and actual MT3000 native Auto/manual/fault/crash/reboot evidence; see releases/v0.9.0-alpha27.md for limits.

## 0.9.0-alpha16-1 - 2026-10-20

B · Calm is the default page design for first entry, terms, onboarding and missing or invalid preferences. Explicit A/C preferences remain available and retain the existing browser/router precedence. The current page is dashboard67, so an older cached dashboard does not hide the new default. Native platform guards and VPN activation behavior are unchanged.

## 0.9.0-alpha9-1 - 2026-10-20 (local candidate)

Crash-recovery continuation: durable emergency Stop with corrupt/unreadable intent, strict recovery journals and lifecycle refusal, restart-safe RELEASE-PENDING, request replay checks and total HTTPS deadlines. Full traffic guards use kernel timeouts and generation-specific element cleanup, so old timers cannot remove replacement guards. Bilingual inline form errors and duplicate-action protection are wired into setup/preferences without delaying emergency Stop. Verified D-drive recovery tooling restores the archived Git bundle and checks its tree/fsck. GL-MT3000 platform inventory and staged test plan prepared; device not yet connected, native switching remains uncertified. Current-source virtual acceptance and hardware certification are recorded separately in the active recovery backlog.

## 0.9.0-alpha6-1 - 2026-10-18 (alpha4 and alpha5 were intermediate automatic bumps, not published)

Telegram report contents are chosen with check boxes in the Telegram wizard (servers, state changes, traffic, traffic since last report, controller state, controller events, monthly totals, gaps; presets Minimum / Standard / Maximum; unset = everything as before; header and ALARM line always sent). Service monitor: lamps sit between the time and the name and are brighter. Recovery group lines are explained below the block. System readiness is now the second menu item after Getting started. Failure codes in server checks, history and Auto steps are links to the error table. Versioning is automatic: VERSION.json records a source fingerprint, scripts/bump-version.py advances the version (and rebuilds the page) whenever the product source changes, a pre-commit hook runs it and qa/test_version_current.py fails CI otherwise, so the version on the pages always follows the code. Every error code on every page links to the error table (linker bug fixed, test for all codes). Recovery statistics are tables. Top button on every page; service monitor aligned left.

## 0.9.0-alpha3-1 - 2026-10-18

Owner decisions and the first full reading pass of the pages. Controller: a damaged switch journal blocks the LAN once and then only the VPN-only guard is used, a rollback that failed twice is given up (Auto stays off, alarm), and both raise a visible alarm (page and Telegram). Auto card: green/red round button and two-state lamp, two-colour Primary/Reserve, Return to primary on a committed reserve, codes of replies as links. New first section Getting started (landing page until all steps are done); speed tests and ranking on one page; plain-language Tests page; failure-test reasons with links; LAN helper explanation, AI prompt and Telegram token help; every emitted code has a row in the error table (states, reasons, families, examples); lamps are glossy and blink; accessibility (skip link, heading focus, visible focus). dashboard66/ui44. Report: docs/FAILURE-ANALYSIS-0.9.0-alpha3.md.

## 0.9.0-alpha2-1 - 2026-10-18

Failure analysis release: a 26-test failure matrix (hangs, timeouts, Stop during a switch, wrong confirmations, broken rollback, supervisor restarts, corrupt journal, malformed exit replies, broken settings writer) and an offline page probe for all designs. Fixes: malformed exit traces become EXIT-TRACE-FAILED instead of ending the supervisor; Stop latches even when router settings cannot be read and always cleans a running fault test (STOP-UNCONFIRMED); hung settings writers answer SETUP-SAVE-UNCONFIRMED; the chosen design survives blocked browser storage; readable marks and details in dark themes and design C. Report: docs/FAILURE-ANALYSIS-0.9.0-alpha2.md. dashboard65/ui43.

## 0.9.0-alpha1-1 - 2026-10-18

New 0.9 line: the three page designs now have their own Overview layouts as in the approved mock-ups (A Control room, B Calm, C Instrument panel) with their own palettes (C is always dark), built from the real router status. Settings > Page design keeps the choice and the "Suits" hints. dashboard64/ui42. UI only; includes alpha22.

## 0.8.0-alpha22-1 - 2026-10-18

Owner attributes (name, device, developer, version/package/page, style) at the bottom of every page in every design; a test fails the build if a design hides them. dashboard63/ui41. UI only; includes alpha21.

## 0.8.0-alpha21-1 - 2026-10-18

Page design A/B/C chosen in Settings > Page design, each with a "Suits" hint; the choice is kept in this browser and opens on every visit. dashboard62/ui40. UI only; includes alpha20.

## 0.8.0-alpha20-1 - 2026-10-18

Live log with blinking lamps; redesigned System readiness; every error code is a link to the error table. dashboard61/ui39. UI only; includes alpha19.

## 0.8.0-alpha19-1 - 2026-10-18

Auto and Monitoring lamps in one row in the sidebar; the Automatic VPN failover block above the Right now card. dashboard60/ui38. UI only; includes alpha18.

## 0.8.0-alpha18-1 - 2026-10-18

Monitoring always on; one speed table; per-server chart colours; daily traffic chart; failure-test codes explained. dashboard59/ui37. Package default enabled=1; otherwise UI only; includes alpha17.

## 0.8.0-alpha17-1 - 2026-10-18

Training below Help; compact Auto lamp. dashboard58/ui36. UI only; includes alpha16.

## 0.8.0-alpha16-1 - 2026-10-18

AI-agent install prompt, error code table, pre-switch check boxes, always-visible Auto state. dashboard57/ui35. UI only; includes alpha15.

## 0.8.0-alpha15-1 - 2026-10-18

Planning codes explained in a table. dashboard56/ui34. UI only; includes alpha14.

## 0.8.0-alpha14-1 - 2026-10-18

Live statistics under the monitor switch. dashboard55/ui33. UI only; includes alpha13.

## 0.8.0-alpha13-1 - 2026-10-17

LAN helper launcher and docs, readable System readiness page, bilingual tables with one text size. dashboard54/ui32. UI and docs only.

## 0.8.0-alpha12-1 - 2026-10-17

Training contents and uniform command style. dashboard53/ui31. UI only; includes alpha11.

## 0.8.0-alpha11-1 - 2026-10-17

Overview clarity. dashboard52/ui30. UI only; includes alpha10.

- Primary/reserve boxes coloured like the Auto traffic light; "Group:" label instead of a bare "Main"; Overview tiles open to explain their numbers.

## 0.8.0-alpha10-1 - 2026-10-17

Version line in the sidebar footer. dashboard51/ui29. UI text only; includes alpha9.

## 0.8.0-alpha9-1 - 2026-10-17

Interactive training, redesigned overview, simple/advanced settings. dashboard50/ui28. Nothing is accepted on the physical router yet.

- Training page (lessons, quiz, score, retry); Overview summary card and "Getting started" checklist; Step 1 / Step 2 wording for the check and Auto.
- Settings split into simple and advanced; per-step guides with examples; monitor service Start/Stop with a three-lamp light; Tests (with speed-test settings) under Advanced.
- Country + protocol labels instead of host names; Channels summary; scroll to top; Telegram help rewritten; HOW-IT-WORKS documents.
- Design layer and light/dark/system theme switch. UI only: no controller, RPC or packaging logic changed except the version strings.

## 0.8.0-alpha8-1 - 2026-10-17

Experimental-software terms: documents, GitHub README and a first-run acceptance screen. dashboard49/ui27.

- DISCLAIMER.md / DISCLAIMER.ru.md: experimental alpha, can interrupt the internet, changes router VPN settings, "AS IS" without warranty (MIT), use at your own risk and responsibility, not legal advice. Banners in README (EN/RU), INSTALL, AI-INSTALL, router-test-kit and LICENSING; install guides updated (first start, test kit).
- First start: a full-page screen with seven points and two required boxes; nothing else renders until the terms version is stored on the router (terms_accept RPC, terms_version/terms_time in the own config). Until then the controller refuses to switch (TERMS-NOT-ACCEPTED) and Auto cannot be started. The terms stay readable on the Help page; a new terms version asks again.

## 0.8.0-alpha7-1 - 2026-10-17

Traffic-light status, simpler interface, safer confirmation. dashboard48/ui26. Includes alpha6 (published) and nothing is accepted on the physical router yet.

- Auto status as a traffic light next to the round button (green watching the primary, yellow switching, orange on the reserve, red needs attention, grey off/no data); the button only starts or stops. The model is tested over 864 controller combinations: green only for a fresh certified watch.
- Interface: five basic pages (Overview, Channels and servers, Statistics, Settings, Help) and a collapsed Advanced group for administrators (Diagnostics, Ranking, Monthly traffic, Service monitor, Events, Readiness). Overview shows the Auto card and four tiles; path and decision details moved to Diagnostics. Per-page subtitles, compact secondary actions, calmer surfaces, shorter plain texts on Statistics, Events and Readiness.
- Confirmation of a LAN transition must now carry the private trial number (never published); the helper sends it, the router verifies it in constant time.
- Telegram token can be deleted (telegram_forget RPC and wizard button), reports are turned off with it.
- Installed identity: package version from opkg is shown with the page build; a page/program/package mismatch is named on the Overview with the fix.
- Ranking shows the number of checks and lists servers with fewer than 20 checks last.
- Endurance harness: host sleep or clock jumps count as gaps; a lost producer is detected without ever signalling the process.
- Documentation: dated-snapshot notes on TESTED-ENVIRONMENT, current procedure on CLIENT-TRIAL, STATE update.

## 0.8.0-alpha6-1 - 2026-10-17

Built-in Help page and the emergency helper shipped with the package. dashboard47/ui25. Includes alpha5 (never published).

- New sidebar page Help / Помощь: 12 topics (no internet, SSH step by step for Windows/Linux/macOS, reserve held, Auto refuses, LAN helper errors, old page, outside change, Telegram, clock, backup, removal, what to send), 21 copyable commands, English and Russian.
- /usr/sbin/homensai-vpn-emergency is installed with the package: show, start, stop-auto, close-journal, remove-guard (no network rule is ever reordered by it).
- A test checks that every helper command named in Help exists in the shipped script.

## 0.8.0-alpha5-1 - 2026-10-17

Findings of the first hardware LAN trial (alpha4) fixed; no physical acceptance of this build is claimed yet. dashboard46/ui24.

- Operator return: "Return to primary" button and native_return RPC leave a held reserve after a fresh check of the primary; a held reserve also returns by itself when the primary has been stable (healthy_primary policy).
- A passed LAN trial now returns on a fresh bound check with bounded retries instead of requiring monitor history, so a trial right after a restart no longer ends held on the reserve.
- An outside change of the router VPN rules no longer holds the LAN: Auto releases its own block and stops. An unverified rollback leaves traffic allowed through VPN tunnels only. A full LAN block has an independent 90-second release timer for its own rule generation.
- Test window options (native_enabled/until/trial) are cleared after return, expiry or abandon.
- Exit address of each connected VPN is shown in the authenticated UI (not in reports, history or exports).
- Plainer state texts (running on the reserve, reserve failing, stopped on the reserve).

## 0.8.0-alpha4-1 - 2026-10-17

All user-visible texts reviewed and rewritten in plain language (router/ui_copy.py, enforced at build time). dashboard45/ui23.

- The Check VPN button is now "Check VPN now" with an explanation: one extra internet check through every connected VPN; the router already repeats it automatically; nothing is switched and no speed is measured.
- Overview, Auto card, failover forecast, setup wizards, recovery rules, monitor and readiness texts rewritten without internal jargon (probe, native, certification, adapter); thresholds are no longer hard-coded in prose.
- English-side wording of the older Russian-source strings polished; Russian wording unchanged there.
- No change to controller, guards, ACL or RPC.

## 0.8.0-alpha3-1 - 2026-10-17

Auto-start flow made explicit and the UI copy made consistent. UI dashboard44/ui23, package 0.8.0-alpha3-1.

- Overview: "Before you can start Auto" checklist (monitor, primary/reserve healthy, session reconnection accepted, router ready, LAN trial passed), showing only the next missing step and the exact router blockers.
- One plain-language, English/Russian explanation for every pre-start controller blocker code (47 codes; a test keeps them in step with native_switch.py/auto_control.py); the Start refusal notice and the Settings page use it.
- Calmer, non-duplicated status text; Telegram shown only as a tile or as an error. Settings: one grouped Setup card (System, Recovery, Monitoring, Telegram, test delivery) above Monitor service and speed tests.
- Recovery wizard reopens a saved preset as that preset, edited values as Custom (audit A35).
- INSTALL/README version references corrected; router-test-kit/ with preflight, install, verify, uninstall and emergency scripts.
- Not changed: native controller, guards, ACL, RPC. No physical-router acceptance is claimed.

## Handoff 1.0.0 - 2026-10-17

- Complete Claude review context and all 50 audit targets; owner-requested STOPPED virtual test checkpoint with independent cleanup.
- Separate application/package/UI and handoff version identities in VERSION.json; documented immutable release policy and read-only agreement validator.
- Application remains 0.8.0-alpha2 / package 0.8.0-alpha2-1. No new product or physical acceptance is claimed.

## 0.8.0-alpha2-1 - 2026-10-17

Checkpoint schema/backup recovery hardening, persistent in-wizard preset feedback and resumable reviewed publication. Virtual/storage/UI evidence and stopped-run limits: releases/v0.8.0-alpha2.md and .claude/handoff/STATE.md.

## 0.8.0-alpha1-4 - 2026-10-17

Readiness/incident reports/recovery presets, actual LuCI dependency/cache fixes and cached readiness RPC. Earlier failed candidates and corrected viewport scope remain documented in releases/v0.8.0-alpha1.md and WORKLOG.

## 0.7.0-alpha10-1 / 0.7.0-alpha9 - 2026-10-17

Sidebar short-window accessibility and trustworthy selected-path colors; see their versioned release notes. Historical validation remains scoped to its recorded source/environment.

## 0.7.0-alpha8-1 - 2026-10-17

Bright raised controls and 18px server lamps; request-correlated DNS/HTTPS checks; explicit Auto/connection/health/traffic states; configured-threshold diagnosis and model quarantine. 329 application + 30 QA tests per runtime and 12 UI suites PASS. Reviewed snapshot published to GitHub main after Gitea verification. Full native hierarchy and physical alpha8 deployment remain pending.


## 0.7.0-alpha6 — complete offline model and UI acceptance

- Pure multi-hop cascade, per-hop/root rollback, stop/restart reconciliation and bounded failure guards; no new native route authorization.
- Freshness-aware colors/selected-first cards, stable sorting/filtering, mobile layouts and complete generated-text English coverage.
- Harden selected primary/reserve wizard validation and single-flight/error handling.
- Fix clock-regression double counting; test calendar/DST boundaries and 200 statistical sequences.
- Shared SDK/IPK payload selection, nested archive privacy guards and exact-SHA Gitea relay.
- 232 application Python tests, 5 QA tests, 8 UI suites, 54 responsive/language checks, 256 cascade series; broader prototype/demo regressions pass. No VM or physical deployment.
- See docs/OFFLINE-COMPLETION.md and qa/ALPHA6-LOCAL-REPORT.json. Native hierarchy/worker/device acceptance remains separate.

## 0.7.0-alpha5 — local recovery/UI candidate

- Observe confirmed reserve failure and require stable primary health plus fresh bound DNS/HTTPS before returning. Keep Stop available in degraded/stale state.
- Use a fresh dashboard26 module address; align package, agent and SDK versions and test their consistency.
- Actual VM LuCI: EN/RU/EN, eight sidebar sections, system/Telegram/recovery wizard cancellation, author website link and version badge.
- 202 Python tests pass in Debian and actual OpenWrt 21.02.7; exact package hash reproduced, network/firewall unchanged. Five Node suites pass.
- Git workflow is saved in primary Gitea. New GitHub publication is withheld pending approval and reconciliation; no physical deployment.
- Full hierarchy, vendor arbitration, inactive activation, IPv6 and device acceptance remain open. See qa/ALPHA5-CHECKPOINT.md.

## 0.7.0-alpha4 — reviewed priorities and bounded operator fault candidate

- Add stale-review-protected priority application, recovery/monitoring wizards, stable primary-return conditions and explicit reserve hold.
- Add certified-trial-only traffic fault/cancel with independent kernel set expiry and watchdog; actual OpenWrt kernel timeout check passed.
- Remove raw-UCI UI writes/token loading; reject numeric/invalid inventory RPC replies and preserve unknown state instead of empty defaults.
- 194 Python tests and five Node suites pass. Full native hierarchy, inactive activation and hardware acceptance remain open; see qa/ALPHA4-CHECKPOINT.md. No physical deployment.


## 0.7.0-alpha3 — raised Auto power control (local UI candidate)

- Router-inspired bevelled power button with halo rings, contact shadow, pressed feedback and Start/Stop captions.
- Confirmed-state semantics retained; green/on, amber/pending, red/error, neutral/off/unknown. Keyboard focus and reduced-motion support.
- Local browser/Auto-state/package checks passed. Not deployed to the physical router.


## 0.7.0-alpha2 — local and virtual OpenWrt acceptance

- Added isolated Docker/QEMU OpenWrt 21.02.7 laboratory, explicit VM-only UCI/RPC/procd acceptance and own-monitor process-recovery tests. No physical GL-MT6000 deployment in this increment.
- Added guarded monitor Start/Stop in Settings. Active, retained, unknown or corrupt native recovery state refuses shutdown; monitor activation never enables Auto.
- Added Telegram calendar wizard, daily WAN/VPN views, read-only hierarchy recommendations, bounded opt-in throughput tests, persistent quotas and monotonic transaction leases.
- Fixed reduced OpenWrt Python timezone compatibility, stale-month selection, aggregated histogram consumption, missing power glyph and retired UI files entering IPK.
- Normalized gzip headers so observed Python 3.9/3.11 package builds match. Diagnostics/work log describe exact failures and fixes.
- Virtual warm reboot remains unconfirmed: both legacy GRUB and alternate direct-kernel attempts stopped at kernel decompression within the test window. Cold startup preserved data. Native GL.iNet switching, IPv6 and hardware power-loss acceptance remain open.
- See qa/OPENWRT-VIRTUAL-REPORT.md for current test counts and limits. This is a development prerelease, not production certification.


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


## 0.1.0-alpha9 — prepared; installation unconfirmed

- Version appears top right; agent, Makefile and package versions agree.
- Added initial Telegram setup wizard and separate reconfiguration button. Stored token is never prefilled; an empty reconfiguration field preserves it.
- Latest probe time appears on the left in service monitor; inactive profiles without measurements show a dash.
- Upgrading an already registered RPC plugin avoids rpcd reload/session expiry. Initial installation still registers the plugin.
- JavaScript syntax and 28 unit tests passed. Device design/wizard check remained pending because the browser returned ERR_BLOCKED_BY_CLIENT on LuCI. Last confirmed installed version was alpha8.

## 0.1.0-alpha8 — 15.10.2026

- Added page styling, connected-server cards, four summary metrics, SVG chart of real HTTPS measurements and responsive layout.
- Moved settings into an expandable panel; inactive profiles display neutrally.
- Chart shows the latest available hour without joining gaps over 90 seconds. Values are HTTPS latency, not download speed.
- JavaScript syntax and 28 unit tests passed; package installed. Upgrade expired an RPC session; fix planned for alpha9.

## 0.1.0-alpha7 — 15.10.2026

- Installed and started monitoring on GL-MT6000, GL.iNet 4.11.0 / OpenWrt 21.02.
- Real HTTPS/DNS probes verified three connected profiles: two OpenVPN and one WireGuard; 12 profiles discovered overall.
- Unique VPN-interface traffic accumulates; the current month is partial, beginning with monitoring.
- Added Telegram reporting, enable flag, interval 5–10080 minutes, Chat ID and hidden token field in LuCI. Device delivery was verified with a 60-minute interval.
- Token is excluded from RPC inventory, status, reports and errors; service configuration is mode 0600. It remains in device UCI accessible to administrator and may be included in configuration backups.
- Fixed IPK tar directories, rpcd session argument handling, missing Python time.tzset on OpenWrt and consistency of both LuCI menus.
- Verified 28 local unit tests, actual installation, real measurements and successful device Telegram delivery status.

### Limitations

- Automatic VPN switching disabled. LAN path and IPv6 unverified. Inactive profiles are not started automatically.
- Interface still uses LuCI tables; local-prototype styling and charts had not been ported.
- Telegram sends current state and in-memory changes, not complete archived weekly/monthly downtime statistics. Events may be lost on restart; monthly counters/aggregates use checkpoints.
- First report sends on enable; subsequent reports follow the configured interval after successful delivery, rounded to an observation cycle. Retry after five minutes on error; network loss can delay delivery.
- RPC reload on installation may require LuCI login again. Old-browser 403 remained under investigation; an IP ban was not confirmed.

### Intermediate builds

- alpha2: RPC check after local build.
- alpha3: fixed missing IPK directories.
- alpha4: OpenWrt time compatibility; first successful startup.
- alpha5: Telegram and reporting settings.
- alpha6: versioned UI resource to avoid stale cache.
- alpha7: aligned legacy controller and menu.d.

## 0.5.0-alpha2
Fix native supervisor startup on router Python without time.tzset using libc fallback. Three regression tests. Device acceptance pending.

## 0.5.0-alpha3
Recognise fresh GL-MT6000 HNAT hook readback; stale/inconsistent responses remain unknown.

## 0.5.0-alpha4
Use before/after kernel-ring evidence for HNAT readback rather than comparing different kernel clocks.

## 0.5.0-alpha5
Handle bounded kernel-ring rollover without reusing stale HNAT evidence.

## 0.5.0-alpha6
Accept timezone-qualified Windows deadline precision on router Python 3.9.

## 0.5.0-alpha7
Use checked private nft batch file on firmware lacking /dev/stdin.

## 0.5.0-alpha8
Format nft batch for OpenWrt nftables 0.9.6; retain syntax check before apply.


## 0.5.0-alpha9
Refresh trial nonce in disabled preflight before evaluating an older latched Stop.


## 0.5.0-alpha10
Use semantic identities for anonymous UCI rules; resolve current names on reorder. Add isolated cable probe mode preserving Wi-Fi connectivity.

## 0.5.0-alpha11
Bound retries for transient final client checks; avoid duplicate trial-pass messages. Real alpha10 trial, automatic failure transition and independent rollback confirmed; original helper final error documented separately.

## 0.5.0-alpha12 — English diagnostics and verified-failover prerelease

- Work log, incident causes/fixes, diagnostic catalogue, validation and historical QA reports are maintained in English with original timestamps and evidence boundaries preserved.
- Telegram-generated report text is English by default; operator-supplied profile/channel names remain unchanged. Six formatter/delivery tests passed; live delivery is governed by the existing configured schedule.
- Fixed language-option selected attributes and version badge in the existing dashboard, with a new resource path to avoid stale browser code. The sidebar 0.6 candidate and complete configuration wizards are not part of this release.
- Clear only this application's Python bytecode cache on update: reproducible source mtimes plus equal file sizes had allowed an older imported version to remain cached. System Python and unrelated caches are retained.
- Native engine scope remains two connected catch-all profiles. Real alpha10 automatic transition/independent rollback passed; previous helper errors and production limits remain documented. Do not treat this prerelease as broad unattended-production acceptance.


## 0.5.0-alpha13 — sidebar interface

- Dark HomenSAI left navigation, light workspace, eight sections and live version badge.
- Author robot/site link; persistent English/Russian language selection.
- Sortable tables, server search, healthy-first cards and polling-safe search focus.
- UI-only release: native switching restrictions and existing settings are unchanged. New Auto mode toggle remains a separate pending change.


## 0.6.0-alpha2 — controlled Auto mode and setup wizards

- Overview power toggle and configured protocol/channel/server diagram follow confirmed controller state. Start resumes only an existing LAN-certified bounded window; Stop remains durable and idempotent. UI intent is atomic and does not enable reboot autostart.
- Three-step system and Telegram-channel wizards, strict own-configuration validation and deliberate test delivery. Existing VPN keys/routes are not edited by setup.
- Correct exec RPC JSON type signatures and reload schema detection. Fix cable helper checks to constrain the intended interface/source address.
- Full unattended failover and expanded inactive-profile hierarchy remain pending; 113 Python tests and 10 UI state invariants pass.


## 0.6.0-alpha3–alpha5 — installed-device setup fixes

- Alpha3 normalizes Lua empty-array tables before first-run setup and moves Auto mode to the top of Overview.
- Alpha4 uses the actual raw UCI named-section creation API and checks the installed writer in an isolated synthetic configuration before enabling Save.
- Alpha5 fixes explicit application ACL coverage for setup and Telegram methods, adds an ACL/RPC contract regression and reloads rpcd registration after upgrade. No wildcard or unrelated-object permissions are added.
