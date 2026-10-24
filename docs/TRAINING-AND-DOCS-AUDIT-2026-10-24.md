# Обучение и документация / Training and documentation — 24.10.2026

## Русский

Кандидат alpha11: все8уроков получили векторные учебные схемы. Автоматический прогон прошёл полный путь8уроков и викторину наRU/EN; отдельно проверены play/pause/предыдущий/следующий/сброс/конец/скрытие/удаление старой схемы. RPC запрещён тестовым окружением: учебные действия не вызывают роутер и не меняют готовность. Текстовая последовательность доступна без проигрывания. До финального Git upload кандидат проходит общую изолированную CI.

Исправлены реальные расхождения: универсальное требование LAN-теста в викторине; безусловный возврат на основной при работе на резерве; утверждение, что Auto не запускает выбранные существующие клиенты; неверный номер Telegram в мастере; обещание, что мониторинг ничего не записывает. Разделены обучение/готовность, запрос/подтверждение, роль/протокол и исторические/текущие сведения.

Переписаны основные действующие руководства и входные страницы. Установочные промпты и набор для stable0.9.0 сохранены закреплёнными к этому релизу; обновлён контекст и ссылки на актуальные инструкции. Полный индекс классифицирует все Markdown-файлы, местные ссылки проверены. Датированные отчёты и правовые документы не переписаны под сегодняшние результаты. Русский список последних изменений находится перед английским.

Визуальная приёмка в настоящем браузере не выполнена. DOM/логические тесты не являются screenshot-proof. VM-аудит относится кalpha10; alpha11 не установлен на реальный роутер. Изображения — собственные кодовые SVG и Mermaid, без внешних трекеров/библиотек/битмапов.

## English

Alpha11 adds eight native vector teaching scenes. Automated tests exercise every lesson and the full quiz in both languages, including play/pause/back/next/reset/end/hidden/disposal. The test environment rejects router RPC: teaching cannot change routes/readiness. Text steps remain available without playback.

Corrected stale universal LAN-trial requirement, unconditional primary-return advice, client-start behaviour, Telegram step number and the claim that monitoring writes nothing. Current user guides/entry pages were rewritten; pinned stable installation prompts remain tied to0.9.0 with updated context. The index classifies every Markdown file and local targets are checked. Dated evidence and legal terms retain their historical facts. Latest changes are ordered Russian then English.

Native browser visual acceptance remains pending. Alpha10 VM evidence does not cover physical alpha11 installation. Graphics are code-native SVG/Mermaid with no external libraries or trackers.

[Русское руководство](CURRENT-STATE.ru.md) · [English guide](CURRENT-STATE.en.md) · [Latest changes](LATEST-CHANGES.md) · [Index](DOCUMENTATION-INDEX.md) · [VM audit](handoff/VM-AUDIT-2026-10-24.md)
