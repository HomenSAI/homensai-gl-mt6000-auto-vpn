<!-- doc-role: current -->
# Separate client-confirmed trial / Отдельный клиентский тест

This document covers the optional **external-LAN bounded trial**, not the normal prepared continuous Auto mode. [LAN helper RU](LAN-HELPER.ru.md) · [EN](LAN-HELPER.en.md) · [Mode overview](HOW-IT-WORKS.en.md).

Непрерывному router-probed режиму подготовленного MT3000 не нужен LAN-сертификат. Отдельный клиентский тест измеряет выбранный Windows-клиент, его DNS/HTTPS/выходной IP и подтверждает конкретную текущую транзакцию. Не запускайте его конкурирующе с непрерывным Auto: сначала завершите штатный Stop/восстановление и проверьте собственные условия клиентского режима.

Use PowerShell7 and the same-release helper. SelfTest is offline. CheckOnly inspects path prerequisites without authentication or Internet probing. ProbeOnly performs actual bound DNS and two HTTPS checks without starting Auto. The full mode authenticates, changes app trial metadata, requires the human TEST confirmation and can switch router traffic within its time bound.

Данные привязаны к интерфейсу/адресу. Путь управления ОС проверяется отдельно до отправки пароля и перед RPC: совпадающий частный IP другого адаптера не доказывает тот же роутер. При конфликте помощник отказывает и не перенастраивает компьютер. Не используйте browser-loopback gateway как реальную LAN-цель.

Confirmations require the current private trial/transaction and fresh matching source/interface/DNS/HTTPS/exit evidence. Never forge them. A returned queued Stop is not restoration. The helper verifies the original client path; if a verified reserve is retained instead, exit3 is partial restoration, not a passed return. Exit2 means refusal/unverified/failure. Exit0 applies only to the selected mode.

The helper changes no PC routes/NIC/DNS/firewall. Management HTTP is unencrypted even on a private LAN; use only the intended trusted management path or HTTPS with a properly trusted certificate. Never globally disable certificate/host-key checks. Private session/configuration/backup data must not be published.

[Emergency recovery](../router-test-kit/EMERGENCY.md) · [Actual tested scopes](TESTED-ENVIRONMENT.en.md).
