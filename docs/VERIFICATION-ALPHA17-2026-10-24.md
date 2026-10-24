<!-- doc-role: versioned-evidence -->
# Weekly latency —0.9.1-alpha17

## Выполнено

Подпись «Просмотр последних7суток», окно1–168часов и правыйползунок для перемещения окна по неделе. «Сейчас» возвращает к текущим данным; при выборе всейнедели перемещатьполноеокно не требуется. Шкала широкого периода показывает даты. История действительно расширена с суток до1–7дней по настройке оператора, максимум10081минутнаязапись/2МиБфайл. Прежние файлыформата1 читаются без сброса; старые удалённые дни не восстанавливаются.

Для большого RPC-пакета полнаянеделя передаётся в rows_json с проверкой количества, размера и структуры; rows сохраняет совместимый суточныйхвост. Метки графика ограничены720наканал, линии и статистика используют сохранённые минутные данные. Неудачные/пропущенные наблюдения не становятся нулём или выдуманным соединением. Управление графиком не меняет маршруты и не запускает пробы.

## Проверка

Точный01b5740d8a8771881d95b26f2922a80d76457581: двеCI774application/112QA,47UI; пропуски сред отмечены.10latency backendtests и расширенныйUI-тест проверяют неделю,1/7дней, прежнийформат, размерыRPC/файла, ползунок на6дней, сохранение окна при polling, Live, codec/count/malformed guards и маркеры.

Реальная изолированнаяOpenWrtVM: raw10081массив дал timeout7; следующийcompact вызов попал в потерянныйRPCобъект4. После явной регистрацииcompact пакет прошёл. Установка с интерактивнымstdin была прервана serial-бюджетом; чтение состояния выявило распакованные файлы при старой opkg-базе. Контролируемое продолжение с закрытымstdin завершилось и подтвердило17/87файлов/прав/свежийRPC/HTTP. Длинныйserial тест также превысил бюджет; отслеживаемое фоновое задание зафиксировало полныйPASS и завершение процесса:10081запись,685748байтнедельныйфайл,707573байтcompactJSON/782815stdout через настоящийubus,1dayprune/no-backfill,восстановленныйstatus/AutoOFF. Все неудачные попытки сохранены. VM штатно выключенаexit0; GL-идентичность/квалификация не подделывалась.

КаноническийIPK832683байт,SHA256`344c60ab5eaa9dc3f8cf1ddb1bddf19500c189dce3d2264d24f1ecff36425102`. MT3000:backup→Stop/install→87файлов/права/RPC/HTTP8080+pinnedHTTPS→обычныйStart/резерв. Новые7dayAPI/UI и старыйcheckpoint проверены; закрытые старые минутные строки сравнены с расшифрованной pre-backup. Настройки/terms1/4speedзаписи сохранены, AutoON/резерв/обаVPNDNS+2HTTPS. Шифрованные копии до/после независимо прочитаны после расшифрования. Синтетические недельные записи никогда не записывались на физическийроутер.

## English and boundaries

True configured1–7day latency retention,1–168hour windows and weekly panning are implemented with legacy checkpoint compatibility, safe compact transport and bounded markers. Exact-source dual-runtimeCI, installed isolatedVM weeklyfile/RPC/persistence/retention tests and physicalMT3000 source/file/API/legacy-preservation/AutoONreserve acceptance passed. [QA](../qa/LATENCY-ALPHA17-2026-10-24.json) · [Physical](../qa/MT3000-ALPHA17-2026-10-24.json).

Old deleted observations cannot be reconstructed; a new seven-day window initially contains only real retained observations. VM fixtures do not certify real seven-day network uptime. Native-browser visuals, independentLAN/IPv6/KillSwitch and physicalpower-loss remain separate. No hostnetwork/mainMT6000 changes, newphysicalspeedtest or trafficfault.

## Publication

Pending actualGitHub/Gitea alpha17prereleases and equal-tree featurebranch save; main/stable0.9.0/older releases unchanged.
