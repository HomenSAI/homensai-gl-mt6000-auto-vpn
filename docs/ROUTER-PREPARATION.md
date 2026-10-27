<!-- doc-role: current -->
# Persistent router preparation / Постоянная подготовка

## Reviewed buttons / Кнопки с просмотром изменения

The local alpha28 candidate adds a Disable button beside applicable preparation reasons. The first click reads the actual router and shows its model and exact change; Apply is a separate explicit click. RPCs accept only seven fixed action names, never a host, command, UCI key or path. The preparation writer checks real GL-MT3000/GL-MT6000 identity and firmware 4.11.0; this does not extend the supported Auto modes or prove physical acceptance on either model.

| Button / Кнопка | Exact scope / Точное действие |
|---|---|
| WireGuard/OpenVPN startup / Автозапуск WG/OV | Only `network.wgclient1.auto=0` or `network.ovpnclient1.auto=0`; no interface reconnect / Только соответствующий auto=0, без переподключения |
| Stock VPN/SFE boot / Штатный автозапуск VPN/SFE | Remove only reviewed S-links for `vpn-client` or `shortcut-fe`; K-links and running services remain / Удалить только проверенные S-ссылки, сохранить K-ссылки и работающие службы |
| HNAT / Аппаратное ускорение | Save enable=0 and write 0 to a verified active runtime hook; no network/firewall reload or module removal / Сохранить enable=0 и отключить проверенный работающий hook, без перезапуска сети/firewall и удаления модулей |
| Flow offloading / Ускорение firewall | Save both offloading flags=0; keep Auto blocked until a deliberate reboot / Сохранить оба флага=0 и удерживать отказ Auto до отдельной перезагрузки |
| SFE module autoload / Автозагрузка модулей SFE | Preserve the exact known file outside modules.d; no overwrite or forced unloading / Сохранить точный проверенный файл вне modules.d, без перезаписи и принудительной выгрузки |

Before writing, a private checksummed original-value record is durably saved under `/etc/homensai-vpn/preparation-changes/`. Values contain no VPN keys or full configuration export. The writer rejects active Auto, retained pair ownership, pending manual work/UCI edits, changed reviews, unknown bindings and unconfirmed earlier preparation writes. An uncertain write leaves its record for recovery and blocks another blind attempt and Auto. It never restores over a newer external edit.

После подтверждения программа заново читает значение и показывает проверенный результат только для этого действия. Это не означает готовность всех условий и не запускает Auto. Для работающих модулей SFE и действующих потоков firewall может требоваться отдельная перезагрузка; до неё сохраняется явная блокировка Auto, привязанная к текущей загрузке. Кнопка сама не останавливает VPN, не перезапускает службы/роутер и не принимает соглашение за владельца. Ручные ссылки остаются доступны.

## Preparation evidence / Доказательства подготовки

[Current supported scope](CURRENT-STATUS.md) · [Read-only readiness](../router/readiness_panel.inc.js)

The prepared MT3000/4.11.0 controller has specific acceleration, interface ownership, stock-worker, DNS and routing-policy requirements. Installing an architecture-all package or choosing a model does not satisfy them. Preparation is distinct from dependencies and from explicit Auto Start.

```sh
python3 /usr/lib/homensai-vpn/preparation_status.py
```

| Area / Область | Evidence / Что проверять |
|---|---|
| HNAT/SFE | Saved flags and actual runtime ownership; loaded/unloaded alone is not full proof / Флаги и реальное состояние, не только наличие модуля |
| Client ownership | Existing WG/OV bindings, managed startup baseline and protected config / Уже назначенные клиенты и сохранённые исходные флаги |
| Stock services | Current competing workers/locks and preserved boot settings / Текущие службы/блокировки и исходные настройки запуска |
| DNS | Actual listener/upstream owner and native API result / Фактический владелец DNS и результат API |
| Policy | Separate verified general paths, KillSwitch/IPv6 constraints and no unverified direct fallback / Проверенные отдельные политики и ограничения утечек |
| Recovery | Private verified export, actual Stop/rollback and newer-edit preservation / Проверенная копия, восстановление и сохранение новых правок |

Follow only operations applicable to the real device. [Dated MT3000 operations/undo evidence](MT3000-OPERATIONS-2026-10-22.md) is not a universal command recipe. Do not disable a working DNS owner based on another router's case, force-unload modules, remove drivers, replace feeds or change host networking automatically.

Перед подготовкой сохраните и проверьте приватную зашифрованную копию. Отмена восстанавливает только собственные проверенные исходные значения; посторонние новые правки не затираются. Зелёная таблица подготовки не запускает Auto и не доказывает Интернет внешнего LAN-клиента.
