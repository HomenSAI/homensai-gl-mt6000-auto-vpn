# Итог после перезагрузки компьютера —24.10.2026

**Завершено:** MT3000 обновлён доalpha13, Auto включён, трафик подтверждён на резерве, обаVPN прошли DNS/HTTPS. Пакет/файлы/RPC/HTTP/HTTPS и шифрованные резервные копии проверены. Изменения и документация опубликованы в обеих Git-системах; stable0.9.0 сохранён.

[GitHub: настоящий предварительный выпуск](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha13) · [Gitea: настоящий предварительный выпуск](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha13). С каждого сервера обратно скачаны4вложения и проверены SHA256.

Обнаруженное расхождение Windows gzip/zlib устранено выбором канонического Linux-пакета, одинакового в двух CI-средах. Первый60секундный reboot-тест медленной TCG VM не уложился в окно; факт сохранён, повторная ограниченная проверка подтвердила самостоятельный запуск и сохранность настроек. Время наблюдения не является гарантией времени загрузки реального роутера.

Отдельно не подтверждены внешнийLAN/IPv6/KillSwitch и визуальная приёмка физической страницы. Реальный сбой трафика на MT3000 не запускался; готовность нового теста на текущем резерве проверена чтением. Все реализованные сценарии и ограничения ниже и в JSON-матрице.

# HomenS.AI Auto VPN 0.9.1-alpha13

## Русский

Все правки интерфейса владельца собраны в один предварительный выпуск. Первые5серверов и раскрытие остальных;20последних событий; явные основной/резервный в ошибках и восстановлении; M/R-схемы переходов; свёрнутые рекомендации задержки и компактные настройки. Буфер живого журнала1–2000 и подробная история1–7дней реально ограничивают данные, месячные/общие счётчики сохраняются. Тест сбоя выбирает фактически текущий канал и подтверждает другой маршрут до объявления успеха.

Проверки:768backend и108QA в двух CI-средах,46UI-наборов,50моделей хаотичного поведения,18755запросов backend без BAD. Браузерная матрица восстановлена как49завершённых + отдельно повторённый последний сценарий на тех же ресурсах. Настоящая OpenWrt VM: opkg, файлы/права/RPC/HTTP, настройки UCI, неправильные запросы, nft kernel timeout, restart/reboot. Первый60с cold-boot тест VM не уложился в окно; более длинная ограниченная повторная проверка прошла, первый отказ сохранён.

MT3000/4.11.0 обновлён: AutoON, резерв подтверждён, оба VPN прошли DNS/HTTPS;87файлов, HTTP/HTTPS и две шифрованные копии по190записей проверены. Реальный сбой на физическом роутере не запускался; готовность теста текущего резерва проверена чтением. Нет отдельной сертификации внешнего LAN/IPv6/KillSwitch и native-browser visual acceptance. Это alpha, не замена stable0.9.0.

## English

One prerelease combines the owner's UI batch: five-row server disclosures,20-row saved history, event-time primary/reserve labels, M/R diagrams, collapsed latency recommendations and compact navigation. Enforced live buffer1–2000 and detail retention1–7days preserve monthly/lifetime counters. Bounded fault tests select the actual current channel and require confirmed alternate routing before success.

Validation:768application and108QA tests in two runtimes,46UI suites,50synthetic personas,18755backend requests with no BAD result. Browser evidence combines49completed cases with a separately rerun final case against identical frozen assets. Actual OpenWrt VM installation/UCI/files/HTTP, negative RPC, nft expiry, service restart and reboot were checked. The initial60s VM cold-boot window failed; a longer bounded retry passed and the original failure is retained.

Dedicated MT3000/4.11.0 installed: AutoON/reserve, both VPN DNS/HTTPS healthy,87files and served assets verified, independently restored encrypted190-entry pre/post backups. No physical traffic fault was injected. External LAN/IPv6/KillSwitch and native visual acceptance remain unverified. Stable0.9.0 is unchanged.

Package SHA256: `f570634022381f8520b3214786bab207228497eda6589fb81cb5ab5f4fd786a8`.

[Full matrix](../qa/OWNER-BATCH-ALPHA13-2026-10-24.json) · [MT3000 receipt](../qa/MT3000-ALPHA13-2026-10-24.json)
