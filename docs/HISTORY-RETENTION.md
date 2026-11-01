<!-- doc-role: current -->
# Хранение наблюдений / Observation retention

Общий мастер → шаг 2 «Мониторинг» либо «Настройки» → «Мониторинг и хранение истории»:

- **Наблюдений в живом журнале: 1–2000.** Например, 100 или 1500. Ограничивается реальный буфер браузера; повторяющиеся подряд состояния по-прежнему объединяются в диапазон времени.
- **Подробная история: 1–7 дней.** Например, 1, 2 или 7. Ограничиваются события отказов/восстановлений, переходы контроллера, пробы, подробные дневные/часовые наблюдения и результаты тестов скорости.

По умолчанию: 2000 наблюдений и 7 дней. Проверка значений действует в интерфейсе и на сервере. Параметры сохраняются в собственной конфигурации приложения; сохранение не запускает Auto и не меняет сеть.

Сокращение срока очищает старые подробности при очередной обработке и сохранении статистики. Очистка результатов скорости проверяется раз в минуту, даже без нового теста. Контрольные точки сохраняются с настроенным интервалом checkpoint. Ограничения числа записей и размера файлов остаются дополнительными пределами: выбранный срок не обещает непрерывную полную историю при любых условиях.

Месячные и общие счётчики сохраняются отдельно. История переключений за сутки остаётся ограничена сутками. История задержек хранит до7суток по настройке1–7дней, окно1–168часов и ползунок просмотра недели. Суточные квоты тестов скорости не сбрасываются настройкой истории. Увеличение срока не восстанавливает уже удалённые подробности. Отчёт по более длинному периоду может содержать только доступные подробные наблюдения.

Журнал переключений (линия Lua, 2.0.0-alpha21): `native-history.json` — маленькое состояние (итоги, месяцы, дни, последние 100 событий и индекс), каждое событие дописывается одной строкой с контрольной суммой в `native-history.events.jsonl`; страница читает только состояние. Прежний файл при первом переходе сохраняется как `native-history.v1.json`; для отката на старый пакет верните его на место `native-history.json` (события после перехода будут потеряны). Срок хранения статистики в «Расширенные → Сбор статистики» (alpha16): по времени (1–7 дней, 2 недели, месяц) или по объёму (1–32 МБ); параметры `stats_retention_mode`, `stats_retention_days`, `stats_retention_mb`; без них действует прежняя настройка 1–7 дней; графики страницы показывают не больше последней недели.

## English

Use **Setup step 2 → Monitoring** or **Settings → Monitoring and history retention**. Set **1–2000 live journal observations** and **1–7 days of detailed history**; defaults are 2000 and 7. Both client and server validate these integer settings. They persist in the application's own configuration without starting Auto or changing networking.

The count limits the actual browser buffer. The period limits incident/controller events, probe samples, detailed daily/hourly observations and speed-test results. Cleanup occurs during normal processing/checkpointing; speed-history age cleanup runs once per minute without starting a test. Independent count/byte caps remain in force.

Monthly/lifetime counters remain separate. Route charts stay bounded to24hours; latency history supports1–168hours within configured1–7days, and speed-test quota ledgers are not reset by this preference. Increasing retention cannot restore deleted details. Reports covering longer periods may have only partial detail.

The switch history (Lua line, 2.0.0-alpha21) is an append-only journal: `native-history.json` is a small state file (totals, months, days, the last 100 events and an index) and each event appends one checksummed line to `native-history.events.jsonl`; the page reads only the state. The first migration keeps the previous file as `native-history.v1.json`; to roll back to an older package copy it back over `native-history.json` (events recorded after the migration are lost). Statistics retention in Advanced → Statistics collection (alpha16): by time (1-7 days, 2 weeks, 1 month) or by size (1-32 MB); options `stats_retention_mode`, `stats_retention_days`, `stats_retention_mb`; without them the previous 1-7 day setting stays in force; the page's charts still show at most the last week.
