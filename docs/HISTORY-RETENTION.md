# Хранение наблюдений / Observation retention

«Настройки» → «Мониторинг и хранение истории»:

- **Наблюдений в живом журнале: 1–2000.** Например, 100 или 1500. Ограничивается реальный буфер браузера; повторяющиеся подряд состояния по-прежнему объединяются в диапазон времени.
- **Подробная история: 1–7 дней.** Например, 1, 2 или 7. Ограничиваются события отказов/восстановлений, переходы контроллера, пробы, подробные дневные/часовые наблюдения и результаты тестов скорости.

По умолчанию: 2000 наблюдений и 7 дней. Проверка значений действует в интерфейсе и на сервере. Параметры сохраняются в собственной конфигурации приложения; сохранение не запускает Auto и не меняет сеть.

Сокращение срока очищает старые подробности при очередной обработке и сохранении статистики. Очистка результатов скорости проверяется раз в минуту, даже без нового теста. Контрольные точки сохраняются с настроенным интервалом checkpoint. Ограничения числа записей и размера файлов остаются дополнительными пределами: выбранный срок не обещает непрерывную полную историю при любых условиях.

Месячные и общие счётчики сохраняются отдельно. История графиков за сутки остаётся ограничена сутками. Суточные квоты тестов скорости не сбрасываются настройкой истории. Увеличение срока не восстанавливает уже удалённые подробности. Отчёт по более длинному периоду может содержать только доступные подробные наблюдения.

## English

Open **Settings → Monitoring and history retention**. Set **1–2000 live journal observations** and **1–7 days of detailed history**; defaults are 2000 and 7. Both client and server validate these integer settings. They persist in the application's own configuration without starting Auto or changing networking.

The count limits the actual browser buffer. The period limits incident/controller events, probe samples, detailed daily/hourly observations and speed-test results. Cleanup occurs during normal processing/checkpointing; speed-history age cleanup runs once per minute without starting a test. Independent count/byte caps remain in force.

Monthly/lifetime counters remain separate. Day charts stay bounded to 24 hours, and speed-test quota ledgers are not reset by this preference. Increasing retention cannot restore deleted details. Reports covering longer periods may have only partial detail.
