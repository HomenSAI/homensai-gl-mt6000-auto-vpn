> Состояние на24.10.2026 / Status24Oct2026: разработка alpha11; public stable0.9.0; physical baseline alpha9; VM evidence alpha10. [Текущее руководство](CURRENT-STATE.ru.md) · [Current guide](CURRENT-STATE.en.md). Pinned release instructions below apply to their stated version; dated evidence is not current hardware certification.

# First-run setup / Первая настройка — 0.9.0

Agreement → illustrated operating explanation → OK → eight steps. Соглашение с MIT/экспериментальным статусом и подтверждениями показывается до первого принятия; прежнее принятие сохраняется на роутере. Затем два абзаца и три схемы объясняют наблюдение, переход на резерв и возврат. OK открывает мастер, ничего не записывая и не включая Auto.

The agreement is not repeated on each visit. Seeing the explanation directly is expected when the current terms have already been accepted on this router. Соглашение не повторяется при каждом входе: если текущие условия уже приняты на этом роутере, сразу открывшееся объяснение работы — нормальное поведение. Принятие для демонстрации повторно не сбрасывается.

| Step | What to choose / Что выбрать | Example / Пример |
|---|---|---|
|1 · Language and appearance / Язык и оформление|Keep automatic model detection; choose language, theme, design / Автомодель, язык, тема, оформление|English/Russian immediately; system theme; B Calm / Язык сразу, тема системы, B Спокойный|
|2 · Monitoring / Мониторинг|Probe interval, statistics checkpoint, profile capacity / Интервал, checkpoint, лимит профилей|10 seconds;900 seconds;2 profiles for a selected pair. Keep larger capacity if needed /10с,900с,2профиля для пары|
|3 · Existing VPNs / Существующие VPN|Two distinct configured VPN clients; assign primary/reserve roles / Два разных настроенных VPN-клиента; назначьте основной и резерв|On prepared MT3000: WireGuard client and OpenVPN client, either may be primary. Select server profiles in stock GL.iNet first / На MT3000: клиент WireGuard и клиент OpenVPN; любой может быть основным. Серверы сначала назначаются клиентам в штатном GL.iNet|
|4 · Names/priorities / Названия и приоритеты|Readable labels, channel group, monitoring flags / Понятные имена, группа, наблюдение|Germany primary/reserve; default group; priority10before20. Explicit pair selection still matters /10раньше20; выбор пары задаётся отдельно|
|5 · Recovery / Восстановление|Repeated failures/successes, cooldown, dwell, primary-return policy / Счётчики, пауза, время работы, возврат|3 failures,2 reserve successes,180s cooldown/dwell;3 primary successes and60s stable before return /3сбоя,2успеха резерва,180с,3успеха основного и60с стабильности|
|6 · Speed tests / Тесты скорости|Optional; consumes traffic / Необязательно, расходует трафик|Initially off. Later8 MiB/test,5s,2 streams,128 MiB/day / Сначала выключить; позже8МиБ,5с,2потока,128МиБ/сутки|
|7 · Telegram|Optional; Configure off preserves existing configuration / Configure выключен — прежняя конфигурация сохраняется|Own bot, /start, private token/destination, daily07:00Europe/Berlin / Свой бот и токен, например07:00по Берлину|
|8 · Review / Проверка|Back to correct, Save all settings to commit / Назад для исправления, Сохранить все настройки для записи|Check model/pair/intervals and optional features; then Overview, check VPNs and explicitly start Auto / Проверьте всё, затем Обзор и явный запуск Auto|

Next only navigates the draft; language preview is immediate. Save requires final review and can be refused while Auto/native recovery is active. Stop normally, wait for confirmation and retry from current state rather than bypassing a refusal. A failed/unconfirmed save retains the draft and does not mark completion. Tokens never appear in review or browser persistence.

«Далее» перемещает по черновику. Сохранение не принимает соглашение за пользователя и не включает Auto. Встроенная помощь открывается отдельно, сохраняет исходную вкладку и даёт пояснения/примеры для каждого шага.

The green escape below Cancel/Next opens the dashboard with **existing settings unchanged**. It saves no draft, resets nothing and does not start Auto. Resume through Settings → All application settings. Зелёная кнопка не восстанавливает заводские настройки: остаются текущая конфигурация и сохранённые значения по умолчанию. Редактирование WAN/Wi-Fi/VPN-ключей выполняется на штатных страницах роутера.

The pair selector lists unique configured protocol/interface bindings, not the full saved-profile catalog. Unassigned or ambiguous profiles are excluded; two profiles of one client are not two channels. Configuration does not require the tunnel to be running, and does not certify health. Saving the pair changes application metadata only. Starting Auto can enable/disable prepared client interfaces and reorder the selected traffic policies; normal Stop restores the managed baseline. It does not edit VPN server addresses, keys, credentials, WAN or Wi-Fi.

В паре выбираются роли уже настроенных клиентов, а не любые серверы из каталога. Неназначенные и неоднозначные профили исключены; два профиля одного клиента не являются двумя каналами. Настроенный клиент может быть остановлен — это не подтверждение его исправности. Сохранение пары меняет только метаданные приложения. При запуске Auto управляет подготовленными интерфейсами и порядком выбранных политик трафика; штатная остановка восстанавливает управляемое исходное состояние. Адреса VPN-серверов, ключи, учётные данные, WAN и Wi-Fi не редактируются. Для смены сервера выберите профиль в штатном VPN-приложении, обновите страницу Auto VPN и дождитесь свежих проверок.

## Обновлённое обучение / Updated training

Восемь уроков и тест знаний доступны на RU/EN. В каждом уроке — учебная SVG-схема с запуском/паузой, шагом назад/вперёд и сбросом. Схема не подключается к роутеру. Вопросы различают router-probed Auto и отдельный клиентский тест; результат обучения не разрешает Auto. Учебные примеры не подменяют свежие измерения или готовность выбранной пары.

All eight lessons include a native vector scene with Play/Pause, Previous/Next step and Reset. They operate only on local teaching state. The quiz distinguishes router-probed Auto from client-confirmed trials. Completion is not readiness certification. [Current RU](CURRENT-STATE.ru.md) · [Current EN](CURRENT-STATE.en.md).
