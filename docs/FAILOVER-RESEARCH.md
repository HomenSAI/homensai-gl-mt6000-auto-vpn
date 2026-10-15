# Переключение и откат / Failover and rollback

## Изученные реализации

1. [mwan3, OpenWrt 21.02 source](https://github.com/openwrt/packages/blob/openwrt-21.02/net/mwan3/files/lib/mwan3/mwan3.sh): резервирование через отдельные таблицы, fwmark/mask, ip rules и пакетную установку правил. Не переносим mwan3 поверх фирменной GL.iNet-маркировки без проверки конфликтов. Эта версия ближе к целевой OpenWrt 21.02, чем инструкции для 24.10.
2. [VPN Guardian architecture](https://github.com/Yakwilik/openwrt-vpn-guardian/blob/main/docs/architecture.md): подготовка и валидация до активации, разделение direct/protected трафика, локального DNS и bootstrap DNS, backup и восстановление runtime после неудачной самопроверки. Это стек Xray/v2rayA/nftables для другой среды; его установку и замену dnsmasq на нашем роутере не выполняли.
3. [GL.iNet dashboard](https://docs.gl-inet.com/router/en/4/interface_guide/vpn_dashboard/): штатное резервирование внутри группы не означает переключение между независимыми группами. При включённом Kill Switch отказ может намеренно блокировать трафик.
4. Сохранённый ранее read-only аудит целевой прошивки: `tunnel-switch.sh` использует собственные PID/noclobber locks, включая общий network-switch lock; hotplug вызывает штатный failover-trigger. `rtp2.sh` обновляет маршруты, DNS и firewall. Его `clean_conntrack` удаляет DNS-состояния по портам 53/служебным портам и вызывает VPN conntrack cleanup. Это не адресная очистка только выбранного клиентского класса. Исходники производителя и сырые дампы не включены в публичный проект; это статические находки, не проверка текущих запущенных workers.

Изучены механизмы; чужой код в новую реализацию не скопирован. Собственный flock не признаётся согласованием со штатными workers. Нельзя захватить их PID-lock нашим процессом и ожидать сотрудничества: штатная проверка владельца может считать такой lock устаревшим.

## Что реализовано в 0.3.0-alpha1

- Нативный монитор публикует `failover_plan` через существующий статус API, без новых RPC-методов и расширения ACL.
- В LuCI выбираются исходный и резервный существующие профили. Планировщик по умолчанию выключен; он только рекомендует, не применяет.
- Нужны три последовательных подтверждённых отказа источника и две свежие успешные HTTPS/DNS-проверки резерва. Устаревшие, будущие, дублирующиеся и неизвестные измерения не считаются подтверждением. Неактивный резерв не запускается.
- Любой план сохраняет `applied=false`, `ready_to_apply=false`, `native_apply=false`. Это не разрешение переключения.
- В `lab/transaction_engine.py` реализован исполняемый Python-контракт транзакции с lock, durable журналом/fsync, дедлайном, проверками владения, откатом и восстановлением. Это стенд с инъекцией адаптера, **не драйвер GL.iNet** и не часть устанавливаемой службы.

## Последовательность будущей живой транзакции

1. Проверить точную прошивку/схему профилей, область изменяемого трафика, специальные правила и независимый LAN-доступ к панели/SSH.
2. Получить доказанное согласование со штатными writers; захватить собственный lock и проверить поколение конфигурации. Произвольное отключение штатных служб не допускается.
3. Сохранить минимальный защищённый snapshot и durable intent. Не копировать VPN-ключи в публичные отчёты.
4. Взвести **независимый** watchdog, способный восстановить состояние при гибели исполнителя. Затем закрыть только изменяемый клиентский класс, сохранив локальное управление. Kill Switch не снимается временно.
5. Применить адаптером изменение с проверкой поколения/владельца; не останавливать общий VPN-интерфейс, который обслуживает специальные правила.
6. Очистить только нужный conntrack-класс по подтверждённой маске/области. Не использовать глобальный flush и не маскировать его эффект обещанием сохранения звонков.
7. Проверить фактический клиентский IPv4-путь, IPv6-путь либо доказанную блокировку IPv6, клиентский DNS, Kill Switch, локальное управление и специальные правила. Проба с роутера недостаточна.
8. Зафиксировать только проверенный результат, открыть защищённый класс и снять watchdog. При отказе восстановить собственное предыдущее поколение и проверить его; чужие более новые изменения не затирать. Непроверенный откат оставляет класс закрытым и требует восстановления; интернет не объявляется восстановленным.

## Почему живое применение всё ещё заблокировано

Нужен настоящий GL.iNet adapter с подтверждёнными worker coordination, независимым watchdog, scoped DNS/conntrack, management path, специальными правилами и IPv6. Native adapter в этой версии не реализован. Неизвестные проверки всегда блокируют применение. Прямой WAN fallback остаётся выключенным и не добавляется неявно.

После адаптера нужны согласованное окно возможного обрыва и проверка с независимого управляющего устройства/сегмента. До этого выполняются только read-only планы и стендовые транзакции. Сессии после смены внешнего IP могут оборваться; откат не возвращает уже потерянные TCP/UDP-сессии.

## Испытания

36 unit-тестов устанавливаемого монитора/пакета. 9 Python-тестов нового транзакционного контракта включают **200 различных сочетаний** отказов этапов, проверок и внешнего writer, отказ записи журнала, дедлайн, конкуренцию apply/recover и повреждённый журнал. Внутри 200 — 60 симулированных crash-сочетаний через исключение BaseException; это **не** реальные SIGKILL роутера или отключения питания. Отдельный старый JS-стенд и его реальные Docker child-process crashes не выдаются за испытание нового GL.iNet-драйвера.

В первом прогоне найден дефект позднего открытия gate при ошибке rollback/open/disarm; исправлен повторным закрытием gate с отдельным исходом UNVERIFIED, если закрытие тоже не подтверждено. Итоговые тесты прошли.

## English summary

Release 0.3.0-alpha1 connects the existing native monitor to a **read-only dry-run planner**. It needs three fresh confirmed source failures and two healthy reserve HTTPS/DNS samples. Unknown/stale/future/duplicate observations and inactive reserves never authorise switching. Plans always report `applied=false`, `ready_to_apply=false`, `native_apply=false`.

The new Python transaction engine under `lab/` is an executable, tested adapter contract: durable intent, independent-watchdog requirement, scoped gate preserving management, ownership checks, client DNS/IPv4/IPv6/Kill Switch/special-rule verification, commit/rollback and recovery. It is **not installed as a native GL.iNet apply driver**. A private mutex does not coordinate stock writers. Newer external changes are not overwritten; unverified rollback never claims restored connectivity. Study references above were used for mechanisms, not code copying.

Live operation remains unavailable until a real adapter and independent recovery path are validated. No real VPN, routing, DNS, firewall or conntrack mutation was performed by these tests. 36 monitor/package tests and 9 transaction tests passed, including 200 synthetic combinations. Real client-session continuity, power loss and IPv6 failover remain unproven.

## Device integration check / Проверка на устройстве

0.3.0-alpha1-1 installed on the reference GL-MT6000 with opkg exit code 0; live status reports agent 0.3.0-alpha1 and `failover_plan.state=DISABLED`, `native_apply=false`. Telegram remained enabled. A temporary UCI configuration test did not complete normally; independent committed-inventory reads confirmed planner disabled and source/target unset, matching the original settings. Enabled-planner end-to-end operation on the real device is therefore not claimed. Recommendation selection is covered by unit/integration fixtures. VPN, route, firewall and DNS settings were not written.
