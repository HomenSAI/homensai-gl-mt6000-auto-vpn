<!-- doc-role: current -->
# Начало работы / Start here

[Русский обзор](README.ru.md) · [English overview](README.md) · [Фактическая версия и приёмка / Version and acceptance](docs/CURRENT-STATUS.md)

1. Выберите один выпуск. Для GL-MT3000 рекомендуется 2.0.0-beta1 (линия Lua, основная с 01.11.2026; [живой тест](docs/OWNER-LIVE-TEST.ru.md)); предыдущий stable — 0.9.0. Пакет, SHA256, описание проверки и установочные скрипты должны относиться к одному тегу. Не понижайте более новую установленную версию.
2. [Установка RU](docs/INSTALL.ru.md) / [Install EN](docs/INSTALL.en.md). Для агента с инструментами — [полный промпт RU](docs/AI-INSTALL.ru.md) / [full prompt EN](docs/AI-INSTALL.en.md).
3. [Первая настройка](docs/FIRST-RUN-SETUP.md): условия → объяснение → восемь шагов → проверка → сохранение. Условия принимает человек. Сохранение не включает Auto.
4. [Быстрый запуск RU](docs/AUTO-QUICKSTART.ru.md) / [Quick start EN](docs/AUTO-QUICKSTART.en.md). Сначала актуальная готовность выбранного режима; затем явный Start.

Prepared continuous Auto manages a saved pair on the qualified MT3000/4.11.0 using router-originated IPv4 evidence. It does not require a LAN certificate. A separate client-confirmed trial uses the Windows helper and its own prerequisites. Architecture `all`, a model selector and training completion do not establish readiness.

Текущая линия разработки — Lua, тестовая сборка 2.0.0-alpha24 (Python 3.9 — основа и запасной уровень, Lua 5.1 — монитор и Auto, модуль C для JSON, быстрое обнаружение по умолчанию). / Current development line: Lua, 2.0.0-alpha24 test build (Python 3.9 base and fallback, Lua 5.1 monitor and Auto, C JSON module, fast detection by default). [Замеры по уровням / Numbers per layer](docs/MEASUREMENTS.ru.md#8-пирамида-выполнения-и-время-переключения) · [Measurements EN](docs/MEASUREMENTS.en.md#8-runtime-pyramid-and-switch-times).

Для сопровождающего: [CURRENT](docs/handoff/CURRENT.md), [ROADMAP](docs/ROADMAP.md), [публикация](docs/PUBLICATION.md), [CI](docs/CI-PRIMARY.md), [реестр документации](docs/DOCUMENTATION-INDEX.md). Старые отчёты/планы/`.claude/handoff` — история, не новые команды или разрешения. Не возобновляйте старые наблюдатели.
