# Native OpenWrt package

Current version: **0.5.0-alpha1**. Monitor mode only; operational automatic failover is unavailable.

[English installation](../docs/INSTALL.en.md) · [Установка](../docs/INSTALL.ru.md) · [Validation](../docs/VALIDATION.md) · [Release history](../CHANGELOG.md)

Build: `python3 router/build_ipk.py releases`. Test: `python3 -m unittest discover -s router/tests -q`.

Native experiment / Нативный эксперимент: see docs/NATIVE-EXPERIMENTAL.md in the repository. Public installation guidance remains MONITOR-only. / Публичная инструкция устанавливает только мониторинг.

[Working-system TODO / План доведения](../docs/TODO-WORKING-SYSTEM.md) · [Client trial / Клиентское испытание](../docs/CLIENT-TRIAL.md). Candidate 0.5.0-alpha1 adds persistent history and a client workflow; positive device acceptance remains pending.
