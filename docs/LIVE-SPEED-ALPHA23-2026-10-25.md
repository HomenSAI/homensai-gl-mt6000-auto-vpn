# Текущая скорость двух VPN / Live speed of both VPN channels

## Русский

После выбора подключённых серверов нажмите «Тестировать скорость» и подтвердите существующий расход трафика. Под таблицей расположены два графика: основной VPN слева/сверху, резервный справа/снизу. Для каждого указаны конкретный сервер, этап, скорость скачивания и отдачи в Мбит/с. Скачивание зелёное, отдача синяя; по горизонтали — секунды от начала измерения данного канала.

Измерения выполняются по очереди, чтобы каналы не отнимали пропускную способность друг у друга. Ожидание, подключение, проверка задержки, скачивание, отдача, завершение, отмена и ошибка обозначены явно. Графики получают новые реальные замеры раз в секунду. Скорость точки — полезные тестовые байты за фактически прошедший интервал; это не весь трафик интерфейса. Отсутствующие направления/ошибки не подменяются нулями. Быстрый короткий тест может дать мало точек.

Промежуточные данные находятся только в RAM и ограничены128точками на профиль, максимум8профилей. На flash сохраняются прежние итоговые результаты. После перезагрузки подробный след последнего теста может отсутствовать; он не восстанавливается из средних значений. История завершённых тестов доступна под отдельным закрытым треугольником.

Новый read-only RPC `speed_live` передаёт только ограниченный снимок измерений, без полного статуса/истории/конфигурации. Страница опрашивает его раз в секунду только во время текущего теста и только в разделе тестов. Запросы не перекрываются; чужой/устаревший запуск не заменяет текущий. При потере связи последние значения сохраняются и появляется пояснение. Квоты, маршруты, TLS, отмена и запрет запуска неподключённого VPN сохранены.

## English

Select connected servers, press Test speed and review the existing traffic budget. Two live panels show primary then reserve, with concrete server, phase, download/upload Mbps and elapsed seconds. Download is green and upload blue. Channels are measured in sequence to avoid competing for bandwidth; waiting is explicit.

Points are real transferred test payload per elapsed interval, refreshed once per second, not whole-interface traffic or old completed averages. Missing directions/errors are not zero speed; short fast tests may produce few points. Bounded intermediate traces stay in RAM (128points/profile, eight profiles maximum); existing final averages remain persisted. A reboot may remove the detailed last-test trace, which is never reconstructed from averages. Completed-test history has a separate closed disclosure.

The lightweight read-only speed_live RPC excludes full status/history/configuration. Polling is single-flight and limited to the visible Tests page while a test is active. Job/profile boundaries and monotonically received snapshots prevent stale responses or other servers contaminating a chart. RPC failure retains the last measured values with an explicit notice. Existing quotas, device/mark route binding, TLS verification, cancellation and inactive-profile restrictions remain.

## Verification status

Local Linux tests transfer real bytes through an isolated loopback HTTP server in both directions, plus parallel aggregation, bounded job-bound snapshots and malformed input. UI fixtures verify two panels/four series, waiting, no historical mixing/fake zeros, job ordering, cancellation and RPC recovery. Final exact-source dual-runtime CI and dedicated MT3000 installation/live measurement acceptance passed: six real RPC frames, four running frames with points; both directions on both channels rendered. Publication follows this evidence commit. Native visual proof is separate.
