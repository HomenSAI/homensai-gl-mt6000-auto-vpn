# Последние изменения / Latest changes — 24.10.2026

## 0.9.1-alpha25 —25 October2026 / 25 октября2026

All internal training redraws preserve page position: Check answer, Next/Back, lesson/question jumps, contents, results, retry/restart, embedded course toggle and interactive scene controls. A short-lived height floor prevents removal collapse, with only the extra space required to keep a deep viewport when content becomes shorter. Meaningful focus is restored without scrolling; dynamic action guards and scoring remain. Checkbox-only alpha24 behavior retained.

Сохранение позиции распространяется на все внутренние кнопки обучения: проверку ответа, переходы, оглавление, результаты, повтор/перезапуск, сворачивание и интерактивные схемы. Перерисовка сохраняет прокрутку и подходящий фокус; короткий новый блок не обрушает высоту страницы. Проверка ответов и защита от повторных действий сохранены.


## 0.9.1-alpha24 —25 October2026 / 25 октября2026

Training checkbox changes now update selection and Check-answer availability in place, preserving the question, DOM, scroll and focus. Polling restores the exact retained control instead of the first checkbox with identical empty accessibility text. Dynamic disabled guards, scoring, wrong-only retries and stale-action protections remain.

Чекбоксы обучения меняют только выбранные ответы и доступность проверки, без пересоздания вопроса и потери прокрутки/фокуса. При обновлении данных восстанавливается тот же элемент. Проверка ответов, баллы и защита от старых действий сохранены.


## 0.9.1-alpha23 —25 October2026 / 25 октября2026

Real measured speed-test progress now drives two primary/reserve panels with separate download/upload series, one-second lightweight updates, explicit sequential waiting/cancellation/errors, bounded RAM traces and isolated completed history. Route/TLS/quota guards retained.

Графики текущего теста показывают реальные скачивание и отдачу обоих VPN по отдельности, обновляются каждую секунду, явно обозначают ожидание/отмену/ошибку. Старые средние результаты вынесены в отдельную свёрнутую историю. Квоты, проверка маршрутов и TLS сохранены.


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


## Русский

Кандидат **0.9.1-alpha13**, stable **0.9.0** без изменений.

- Списки серверов: первые пять строк и раскрытие; работающий канал выше ожидающего в текущих проверках и мониторе.
- Обзор, сворачиваемая рекомендация задержки, меню «Расширенные настройки» и пояснения стали компактнее.
- Ошибки и восстановления сначала называют основной или резервный канал; роль хранится на момент события. Схема M/R показывает направление и подтверждение перехода.
- Сохранённая история: последние20 строк, раскрытие остальных, поиск/сортировка; отдельная кнопка чтения удалена.
- Настраиваются 1–2000 наблюдений живого журнала и 1–7 дней подробной истории. Реальная очистка сохраняет месячные/общие счётчики; удалённые подробности не восстанавливаются увеличением срока.
- Ограниченный тест сбоя выбирает текущий канал, проверяет переход на другой и снимает искусственную блокировку после подтверждения либо таймаута. Поддерживается prepared continuous-pair Auto без устаревшего требования LAN-сертификата; проверки private state, Stop, identities, health и kernel timeout остаются.
- Старая таблица dry-run условий заменена ссылкой на актуальную готовность; объяснение ожидания планировщика перенесено в помощь.

Проверки и приёмка этой версии фиксируются отдельно в матрице текущей пачки. Старые VM/физические результаты не считаются приёмкой alpha13.

## English

Candidate **0.9.1-alpha13**; stable **0.9.0** unchanged.

- Server lists show five rows with disclosure; working channels precede waiting ones in current checks and the service monitor.
- Overview, collapsed latency recommendations, Advanced settings navigation and explanations are more compact.
- Failures/recoveries identify the event-time primary/reserve role. M/R diagrams show transition direction and confirmation.
- Saved history starts with20 recent rows, expands, searches and sorts; the separate read-history button is removed.
- Configurable live buffer1–2000 and detailed retention1–7days enforce actual cleanup while keeping monthly/lifetime counters. Increasing retention cannot restore deleted detail.
- Bounded fault tests target the actual selected channel and confirm the alternate route before reporting success. Prepared continuous-pair Auto no longer requires a legacy LAN certificate; private-state, identity, health, Stop and kernel-timeout checks remain.
- The obsolete dry-run table links to authoritative readiness; planner-wait explanations live in Help.

This candidate's verification and device acceptance are recorded separately. Earlier evidence does not establish alpha13 acceptance.
