<!-- doc-role: versioned-evidence -->
# HomenS.AI Auto VPN 0.9.1-alpha20

Справа от заголовка страницы добавлена кнопка «Упрощённый интерфейс». Она открывает стартовую карточку только при полной текущей готовности Auto. Если обязательный шаг не выполнен, под кнопкой показана причина; потеря данных не выдаётся за необходимость пройти настройку заново. Допуск обновляется при поступлении статуса и его устаревании, а также повторно проверяется перед переходом. Навигация не сохраняет настройки и не включает/выключает Auto.

Исправлена обрезанная синяя полоса вверху слева: ссылка «К содержимому» полностью скрыта до фокуса с клавиатуры, затем видна целиком. Текст выполненных шагов больше не полупрозрачный. Шапка переносится на узких экранах.

Added the Simplified interface shortcut beside the page title, with current readiness checks, a visible unavailable reason and click-time revalidation. Navigation never changes configuration or Auto. Fixed the clipped upper-left skip link while retaining keyboard access and made completed setup steps fully readable.

Exact-source dual-runtime CI774application/112QA each/52UI passed; complementary skips recorded. Actual MT3000 install/87files/modes/RPC/HTTP/pinnedHTTPS verified; AutoON/confirmedreserve, bothVPN DNS/HTTPS healthy. Settings/terms,1644closedoldlatency rows and four speed results retained;193-entry encrypted pre/post backups independently decrypted/read. Current unfinished setup markers are preserved, so the shortcut is correctly disabled with an explanation. A ready shortcut was checked against actual data with completed flags only in memory.

Native-browser visual acceptance not performed. Experimental prerelease; main/stable0.9.0 unchanged.

## Evidence

Exact tested source `2ce089091eb6851af8741b604154979a71905eb9`;849731byteIPK SHA256 `8947728ed475072e457bfb90ffdc90d4a62e989eab6c85d3c6ff627f45233bdf`. [QA](../qa/HEADER-ALPHA20-2026-10-25.json) · [MT3000](../qa/MT3000-ALPHA20-2026-10-25.json).

Regression coverage EN/RU: disabled reason, enabled transition, stale-at-click denial, unchanged strict entry gates, actual generated header placement/route handler, full-menu flag reset, lost-RPC explanation and live status updates. Accessibility regression now verifies complete clipping before focus and complete unclipping/fixed placement on focus; it replaces the old brittle top8px expectation that allowed the pictured partial strip. All52UI passed.

Actual physical source/frame: shortcut disabled and explains «Сначала завершите первичную настройку», matching saved setup_complete/onboarding_complete=false. Completed-setup projection enables the same shortcut using actual current pair/health/path data; flags changed only in memory, never on device. No native browser click/layout acceptance is claimed. No new speed/fault test or network observations injected.

NormalStop24.64s/install5.5s/Start63.844s/reserve43.141s. Protected network settings unchanged; only expected own native_trial/native_until lifecycle values changed,35options retained.1644closedlegacy latency rows compared with decrypted pre-backup; open minute excluded. Four speed results retained. Before/after encrypted backups193entries independently decrypted/read. No hostnetwork/mainMT6000/firmware changes. User router gateway remains127.0.0.2:8080; preview64171 separate.

Publication follows verified feature source, no product changes after CI. Stable/main preserved.
