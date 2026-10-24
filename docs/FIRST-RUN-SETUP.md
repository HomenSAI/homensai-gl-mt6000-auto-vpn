<!-- doc-role: current -->
# Первый запуск / First-run setup

[Текущие версии](CURRENT-STATUS.md) · [RU guide](CURRENT-STATE.ru.md) · [EN guide](CURRENT-STATE.en.md)

Current terms are shown until first acceptance of that **terms version** on this router. The person accepts them; an AI agent must not write `terms_version` or call acceptance for the owner. The accepted state is router-owned, not a disposable browser checkbox. The same accepted version is skipped on later visits.

Затем — объяснение работы, обучение и общий мастер. Обучение можно открыть позже; тест знаний не сертифицирует Auto. Все учебные схемы локальны: запуск/пауза, назад/вперёд, сброс; никаких RPC или VPN-команд.

| Шаг / Step | What is saved / Что сохраняется |
|---|---|
|1 Language/appearance / Язык/оформление|Router defaults/model preference, browser preview distinct / Язык, тема, дизайн, предпочтение модели; это не обход фактической модели|
|2 Monitoring / Мониторинг|Probe/checkpoint/profile limits, read-only planning, live count1–2000/detail days1–7 / Интервалы, лимиты, планирование и хранение|
|3 Existing VPNs / Существующие VPN|Two different configured clients and trial preferences, or explicit deferral / Два разных уже назначенных клиента и параметры теста либо явное откладывание|
|4 Names/priorities / Названия/приоритеты|Own display metadata; `default` is not the primary/reserve role / Имена и приоритеты, без импорта ключей|
|5 Recovery / Восстановление|Repeated-failure/success thresholds, dwell/cooldown, return policy / Пороги, паузы, политика возврата|
|6 Speed / Скорость|Optional bounded tests and quotas / Необязательные тесты и квоты|
|7 Telegram|Optional private token/destination/schedule; Configure off preserves existing state / Необязательная приватная настройка|
|8 Review / Проверка|Review all values and save atomically when lifecycle allows / Проверить всё и сохранить при допустимом состоянии|

Next only navigates. Appearance language previews immediately; a final reviewed save persists router defaults. Cancel keeps a draft in this page only. Reload/closing discards that draft. The dashboard escape preserves current router settings; it is not Save, reset, terms acceptance or Auto Start. A refused/unconfirmed save is not completed setup.

Роли основной/резервный назначаются существующим независимым клиентам. Два сервера одного клиента не являются двумя каналами. Для другого сервера/протокола используйте штатную VPN-панель, затем обновите Auto VPN и дождитесь свежих согласованных наблюдений. Сохранение пары — метаданные; явный подготовленный Start может включить управляемые интерфейсы и выбирать политику. Save не включает Auto.

Existing optional settings are preserved unless selected for change. A setup save does not send Telegram tests. Never expose tokens in review, browser persistence or logs. [Control semantics](CONTROL-AND-SETUP.md) · [Retention](HISTORY-RETENTION.md) · [Mode readiness](HOW-IT-WORKS.en.md).
