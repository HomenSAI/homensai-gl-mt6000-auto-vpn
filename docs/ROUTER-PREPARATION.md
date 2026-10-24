<!-- doc-role: current -->
# Persistent router preparation / Постоянная подготовка

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
