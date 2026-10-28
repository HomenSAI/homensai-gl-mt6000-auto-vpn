<!-- doc-role: versioned-evidence -->
# Alpha54 running reserve, incomplete Auto acceptance / Alpha54 работает через резерв, приёмка Auto не завершена

Dedicated GL-MT3000, GL.iNet 4.11.0, 28 October 2026. Code `c2df52e16d7ca6327b4e6c3aa08085b3cba070b1`, record `03a17f929fb5129dedfdf3efc80fea454274aa04`; package 956552 bytes, SHA256 `cd60a1d2163ccbeadd81ea96ae3cbadbd14ec545c20e29db296d1a62eed495f3`.

Both CI runtimes passed 1046 application tests without skips, 150 QA tests (2/37 skips), 60 offline lab cases and 13 Lua cases. Full 3.11 also ran 20 tools tests, 77 UI suites and two Node lab suites; runtime-only tools were explicitly skipped. The isolated Python 3.9 build matched. Independent review passed 25 derived-contract cases and 16 recovery cases on each runtime.

Actual guarded recovery used the exact independent pre-alpha53 backup parsed only in RAM by firmware libuci. The old network identity, policy hash and order matched. The old native controller was quiesced; original state and journal were archived and read back. The verified alpha54 shadow code reconciled only the proved stock changes and completed ordinary Stop. Kernel rules, owner configuration files, VPN interfaces, boot state and budget stayed unchanged; only own metadata and the ordinary owned guard cleanup changed. A private wrapper initially refused normal `/etc/config/cellular` and `gl_nas` directories before the recovery helper ran. Its scoped resume rechecked the same package/stage, absent writer and absent descriptor, then passed. All failed evidence was retained.

Installation verified all 97 payload files, protected settings, terms, main routes and actual dashboard129/ui95/help129 resources. Normal Start was accepted: **pair RUNNING, request ON, fresh kernel-verified reserve path, readiness true**, with both VPNs healthy and protected configuration unchanged. This was not an Auto-off or tunnel-connectivity failure.

**Full Auto acceptance remained incomplete; alpha54 was not published.** The controller stayed `DEGRADED-ON-RESERVE / RESERVE-IDENTITY-UNKNOWN` instead of using fresh observations for its return decision. Exact inspection proved that the retained journal was a closed alpha53 activation: its trial and control revision did not belong to the new session. Current profiles were SETTLED, healthy and cross-tunnel READY; only their stored historical `vendor_generation` differed. The terminal activation branch incorrectly treated that historical journal as the current transaction.

The next correction must restrict only the closed activation branch to the current trial/revision, preserve the old journal as evidence, and retain current-session bootstrap and existing COMMITTED/HELD behavior. Physical Start, actual manual switching, final browser/performance acceptance and publication remain separate gates. Functional native UI cases reached 24 PASS, including menus, disclosures, Ping and responsive headers; the browser helper's cleanup was not yet a fully accepted result. Independent LAN-client, full-day, controlled physical-fault, power-cut, IPv6 and MT6000 continuous-mode claims remain separate.

---

Восстановление alpha53 по точной копии и установка alpha54 прошли. Проверены 97 файлов, HTTP/RPC, сохранность настроек и условий. Auto принял запуск: **RUNNING / ON**, действующие правила подтвердили резервный VPN, оба канала проходили проверки. Это не отказ подключения туннелей.

Полную приёмку Auto остановил старый закрытый журнал alpha53. Его trial и revision не совпадали с новым запуском, но контроллер использовал прежний `vendor_generation` при решении о возврате. Текущая пара уже была READY и здорова. Поэтому режим удерживался как `DEGRADED-ON-RESERVE / RESERVE-IDENTITY-UNKNOWN`.

Alpha54 не опубликована. Исправление следующей версии должно отделить закрытый журнал прежнего запуска от текущей сессии, сохранив исторические доказательства и действующие защитные проверки. Функциональные проверки браузера дошли до 24 PASS, но окончательные ручные переключения, браузерная/временная приёмка и выпуск ещё необходимы.
