# Последние изменения / Latest changes — 24.10.2026

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
