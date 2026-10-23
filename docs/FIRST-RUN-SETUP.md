# First-run setup / Первая настройка — 0.9.0

Agreement → illustrated operating explanation → OK → eight steps. Соглашение с MIT/экспериментальным статусом и подтверждениями показывается до первого принятия; прежнее принятие сохраняется на роутере. Затем два абзаца и три схемы объясняют наблюдение, переход на резерв и возврат. OK открывает мастер, ничего не записывая и не включая Auto.

| Step | What to choose / Что выбрать | Example / Пример |
|---|---|---|
|1 · Language and appearance / Язык и оформление|Keep automatic model detection; choose language, theme, design / Автомодель, язык, тема, оформление|English/Russian immediately; system theme; B Calm / Язык сразу, тема системы, B Спокойный|
|2 · Monitoring / Мониторинг|Probe interval, statistics checkpoint, profile capacity / Интервал, checkpoint, лимит профилей|10 seconds;900 seconds;2 profiles for a selected pair. Keep larger capacity if needed /10с,900с,2профиля для пары|
|3 · Existing VPNs / Существующие VPN|Different saved primary/reserve profiles; trial preferences / Разные основной и резерв, параметры отдельного теста|Your working WireGuard primary and OpenVPN reserve; defer pair if missing / Свои рабочие профили; при отсутствии отложите пару|
|4 · Names/priorities / Названия и приоритеты|Readable labels, channel group, monitoring flags / Понятные имена, группа, наблюдение|Germany primary/reserve; default group; priority10before20. Explicit pair selection still matters /10раньше20; выбор пары задаётся отдельно|
|5 · Recovery / Восстановление|Repeated failures/successes, cooldown, dwell, primary-return policy / Счётчики, пауза, время работы, возврат|3 failures,2 reserve successes,180s cooldown/dwell;3 primary successes and60s stable before return /3сбоя,2успеха резерва,180с,3успеха основного и60с стабильности|
|6 · Speed tests / Тесты скорости|Optional; consumes traffic / Необязательно, расходует трафик|Initially off. Later8 MiB/test,5s,2 streams,128 MiB/day / Сначала выключить; позже8МиБ,5с,2потока,128МиБ/сутки|
|7 · Telegram|Optional; Configure off preserves existing configuration / Configure выключен — прежняя конфигурация сохраняется|Own bot, /start, private token/destination, daily07:00Europe/Berlin / Свой бот и токен, например07:00по Берлину|
|8 · Review / Проверка|Back to correct, Save all settings to commit / Назад для исправления, Сохранить все настройки для записи|Check model/pair/intervals and optional features; then Overview, check VPNs and explicitly start Auto / Проверьте всё, затем Обзор и явный запуск Auto|

Next only navigates the draft; language preview is immediate. Save requires final review and can be refused while Auto/native recovery is active. Stop normally, wait for confirmation and retry from current state rather than bypassing a refusal. A failed/unconfirmed save retains the draft and does not mark completion. Tokens never appear in review or browser persistence.

«Далее» перемещает по черновику. Сохранение не принимает соглашение за пользователя и не включает Auto. Встроенная помощь открывается отдельно, сохраняет исходную вкладку и даёт пояснения/примеры для каждого шага.

The green escape below Cancel/Next opens the dashboard with **existing settings unchanged**. It saves no draft, resets nothing and does not start Auto. Resume through Settings → All application settings. Зелёная кнопка не восстанавливает заводские настройки: остаются текущая конфигурация и сохранённые значения по умолчанию. Редактирование WAN/Wi-Fi/VPN-ключей выполняется на штатных страницах роутера.
