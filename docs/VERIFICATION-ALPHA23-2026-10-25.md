# HomenS.AI Auto VPN 0.9.1-alpha23

## Русский

Тест скорости теперь передаёт реальные промежуточные замеры. Под таблицей находятся отдельные графики основного и резервного VPN: скачивание зелёным, отдача синим; по горизонтали — секунды. Каждый канал показывает свой сервер, этап и текущие Мбит/с. Каналы тестируются по очереди, ожидающий канал отмечен явно. Старые средние результаты вынесены в свёрнутую историю и не используются как текущая скорость.

Новый read-only RPC speed_live обновляет графики раз в секунду без полного статуса и чтения flash-истории. Ограниченные промежуточные точки хранятся в RAM. Ошибки/отмена/отсутствующее направление не заменяются нулями; запоздавшие ответы и другие задачи не подмешиваются. Существующие квоты, TLS, проверка маршрута и запрет запуска неподключённых профилей сохранены.

Проверки:778application/112QA в каждой из двух изолированных сред,55UI-наборов; дополнительные19Linux-тестов измерителя включают реальные локальные передачи. Первая CI остановилась на не обновлённом ожидаемом read-only списке; проверка дополнена speed_live, пакет не менялся. Успешный точный источник `20ebcfd68f2dba279b96840248f6f579f5e9dfca`.

На выделенном MT3000 установлен alpha23,87файлов/права/RPC/HTTP/HTTPS сверены. Реальный тест обоих VPN прошёл: 6RPC-кадров, 4кадра с точками во время RUNNING. Основной: скачивание4, отдача2точки; резервный: скачивание7, отдача3точки. Все4старых результата сохранены, после проверки6. Зарезервировано8МиБ полезных данных на канал; служебный трафик дополнительно. Тест не менял настройки приложения или сети. Auto оставлен включённым на подтверждённом резерве, оба VPN DNS/HTTPS исправны.1974закрытых прежних строки задержек и соглашение сохранены,193-entry зашифрованные копии до/после независимо прочитаны.

Нативная визуальная проверка браузера не выполнена: реальные данные проверены через настоящий UI-модуль отдельно от GUI. Основной MT6000, сеть компьютера и стабильный0.9.0 не изменены. Это настоящий опубликованный prerelease, не стабильное продвижение.

## English

Speed tests now stream measured interval payload rates into separate primary/reserve panels with download (green), upload (blue), server, phase and elapsed seconds. Channels are measured sequentially with explicit waiting; completed averages are separate collapsed history. Lightweight read-only speed_live polling is single-flight at1s while the test section is active. Bounded RAM traces are job/profile isolated, missing/errors are not zero speed, and existing quota/TLS/device-route guards remain.

Exact dual-runtime CI778application/112QA each and55UI suites passed; complementary skips and the initial stale allowlist-test failure are retained in QA. Actual MT3000 normal upgrade and bounded two-channel speed test passed with real intermediate RPC frames rendered in the actual UI model. Auto remains ON/confirmedreserve; old history/settings/terms preserved. Native browser visuals remain unverified. Canonical855870bytes, SHA256 `5b0c343f390b7040feef4df4285ab212ba69e5f0986114fb5e049e0575416324`.

[QA](../qa/LIVE-SPEED-ALPHA23-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA23-2026-10-25.json)
