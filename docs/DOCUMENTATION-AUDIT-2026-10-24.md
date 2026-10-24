<!-- doc-role: versioned-evidence -->
# Documentation/helper review —24October2026

Candidate **0.9.1-alpha14**, dashboard90/ui62. Alpha14 is now installed and physically verified; [delivery receipt](../qa/MT3000-ALPHA14-2026-10-24.json). Publication is recorded separately.

## Изменения

Перепроверены действующие инструкции, мастер, обучение, встроенная помощь и команды помощников. Исправлены противоречия между router-probed Auto, отдельным LAN-тестом и monitor-only VM; источником профилей остаётся штатный VPN-клиент. Запуск, остановка, восстановление и запрос действия различаются. Старые отчёты оставлены историческими; их прежние разрешения и результаты не выдаются за текущий план.

Четыре промпта и полный справочник помощи RU/EN синхронизируются с исполняемыми исходниками. Убраны потерянные обратные слеши Windows-команд, неверные пути меню, необоснованные обещания возврата на основной и универсального LAN-сертификата. В справке есть адресные подсказки по хранению, контролируемому сбою и совпадающим подсетям. Согласие версии1 и правовые тексты не менялись.

В общем мастере доступны уже поддерживаемые сервером лимиты1–2000 и1–7дней. Проверки отклоняют дробные и выходящие за границы значения. Исправления помощников проверяются на реальном коде с подставными командами; схема не посылает пароль/HTTP при несовпадении интерфейса, аварийный скрипт не фиксирует чужие правки или ошибочную остановку. Это не доказательство отсутствия всех гонок маршрутизации.

## Changes and evidence boundaries

Current installation/help/setup/training/helper instructions were aligned by mode and ownership. Historical records retain their original bodies, versions and limitations; archival labels point to the delivered-state record. Existing normative terms/licences remain unchanged. No historical result is re-certified by reading or reformatting it.

`scripts/sync-documentation.py --check` compares31runtime Help topics per language,458merged code entries, four AI prompts and unchanged full terms references. `qa/audit_documentation.py` reads/inventories all public Markdown/licence notices, checks real local targets outside code examples and checks source/output digests. This is reproducible structural coverage, not a claim that a hosted external model autonomously installed a physical router.

Focused evidence:46NodeUI suites; native helper SelfTest; two native PowerShell regression cases (control route and exact Telegram recipe); three isolated Linux emergency-script cases. Tests use synthetic credentials/responses, no real Telegram messages, host route edits or physical traffic fault.

Immutable source958b73f9b60ee5dba83bf9f184e65820a03099e9 passed both CI runtimes:771application/112QA tests each,46UI primary; complementary skips remain explicit. Canonical IPK829928bytes, SHA25649ffb3e57b288f899c84e77546e7b1a0e26243300765bf5927ef8270ae214342 matches both builds. Final sourcefe3b4927559e426f5741e7a677bccaedeec3590f passed both fullCI runtimes after correcting an install-kit hash mismatch in8984120 (failed run retained). The product IPK remained unchanged. New actualVM install/upgrade/fullsetup/retention/component/emergency checks passed and VM poweredoff exit0. ActualMT3000 updated withAutoON/reserve,87files/modes/servedresources/settings/terms/two encrypted190-entry backups verified.82prompt recipes and remaining external scopes are in [matrix](../qa/OWNER-DOCS-ALPHA14-2026-10-24.json). ActualWindowsCheckOnly refused CLIENT-CABLE-PROBE-ROUTE-MISMATCH without credential/HTTP/settings changes; no externalLAN certification follows. Publication is recorded separately. See [current handoff](handoff/CURRENT.md).
