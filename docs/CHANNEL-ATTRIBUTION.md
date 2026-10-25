# Канал в ошибках и статистике / Channel attribution

Для события конкретного VPN сначала показывается роль канала, затем состояние, сервер, протокол и код ошибки. Например: «Основной канал — Ошибка соединения · Германия · WireGuard · VPN-003».

Роли `source` (основной) и `target` (резервный) сохраняются на момент наблюдения из согласованной пары. Протокол и текущие настройки не определяют роль старого события. У восстановления сохраняется собственная роль: она могла измениться после отказа. Живой журнал, сохранённая история и поиск используют общую модель событий; объединение повторов учитывает роль.

Таблицы транзакций используют исходную пару самой транзакции. CSV переключений содержит `source_role` и `target_role` рядом с ID профилей. Серверные строки отчёта и смены состояния также содержат роль. Общие ошибки службы не приписываются одному из каналов. Если старая запись не содержит достаточных доказательств роли, это явно указано; история не переписывается по сегодняшней паре.

For a VPN-specific event, show the channel role first, followed by state, server, protocol and error code. Record the role from the consistent pair at observation time. Never infer an archived role from its protocol or today's settings. Recovery retains its own event-time role. Shared journal rendering, searching and repeat grouping preserve that role.

Transaction tables use the transaction's original pair. Transition CSV includes `source_role` and `target_role`; server and state-change report lines include the role. Service-wide faults stay service-wide. Missing historical evidence is disclosed rather than reconstructed from current configuration.

Визуальные события / Visual events: M (Main) всегда слева, R (Reserve) справа. Направление задаётся сохранённым этапом перехода, не текущей парой. Жёлтые круги и движущаяся стрелка означают неподтверждённый переход. После подтверждения зелёный круг означает выбранный канал, красный — не выбранный (это не отдельная проверка его исправности). Отдельная ошибка помечает только отказавший канал красным без стрелки переключения; восстановление доступности — соответствующий круг зелёным без заявления о маршруте. Учитывается prefers-reduced-motion; подписи доступны без различения цветов.
