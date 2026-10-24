<!-- doc-role: versioned-evidence -->
# Saved-history state column —0.9.1-alpha16

## Изменение

Второй столбец «Состояние» расширен до27%, третий «Событие» сужен до58%, дата/время занимает15%. СхемаM/R выводится отдельным блоком; код состояния под ней не разрывается по дефисам. Таблица имеет минимальную ширину880px и существующую горизонтальную прокрутку на узких экранах. Правила ограничены сохранённой историей; данные событий, поиск, сортировка, раскрытие и живой журнал не изменены.

## Проверка

Существующие event_history_ui/journal_terminal_ui регрессии прошли. ПолнаяCI точногоe7609c981cb108a4fc79439d2b11368c1161e795:771application/112QA в каждой среде,47UI в основной; пропуски указаны в квитанциях. КаноническийIPK831904байт,SHA256`913acd14de698b1898d7333cc20a788c14b75e2abdebc9354054f0d0807989d9`.

Первоначальныйcf165e прогон прошёл; metadata-коммит01207a3 выявил плавающую ошибку тестовогостенда: глобальный fakePopen перехватывал UCI-чтение history_days при истечении5секундного кеша. Изоляция configured_days=7 в этой существующейфикстуре исправленаe7609c9;5сценариев и новый полныйпрогонPASS. Продуктовыйкод/защиты/байтыпакета не менялись; неудачныйпрогон сохранён.

MT3000/4.11.0:193-entryшифрованнаякопия с независимым расшифрованием/чтением →Stop →opkg16 →87файлов/прав/RPC/HTTP8080+pinnedHTTPS →обычныйStart64.672с →резерв41.281с. Установленные правилаCSS проверены чтением и хешами фактически отданныхресурсов. Четыре успешныхзамераскорости/ручныеspeedнастройки/условия1 сохранены. AutoON/подтверждёнрезерв/обаVPNDNS+2HTTPS. После —повторная193-entryшифрованнаякопия с независимойпроверкой. Компьютернаясеть/основнойMT6000 не менялись; новыхсбоев/скоростныхизмерений не запускалось.

## English and limits

The saved-history State column is wider and Event narrower. The route diagram becomes a block before an unbroken state code. Narrow screens use existing horizontal scrolling; event behavior/data are unchanged. Exact-source dual-runtimeCI and installed-file/RPC/served-resource/AutoONreserve/settings/history/encryptedbackup acceptance passed. [QA](../qa/EVENTS-ALPHA16-2026-10-24.json) · [Physical receipt](../qa/MT3000-ALPHA16-2026-10-24.json).

Browser inventory exposed no available apps/tabs. CSS source and served bytes were verified, not a native screenshot or computed-layout acceptance. ExternalLAN/IPv6/KillSwitch remain separately unverified. No newVM claim; historicalalpha14VM evidence retains its version.

## Publication

Published actual non-draft prereleases: [GitHub alpha16](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha16) · [Gitea alpha16](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha16). Four assets/server downloaded andSHA256verified. Canonicaltag/source`ea9685bbf22b98c43380d9c928d9467ac5aacd66`, publictag/source`7161e9f2180ba291ab2fd325eca09d0d1bfc076b`, identicaltree`98f5d61ee2ebf2aa6849e696ceca7d99229e5992`. Main/stable0.9.0/oldtags preserved. Documentation-only closure follows with product unchanged frome7609c9.
