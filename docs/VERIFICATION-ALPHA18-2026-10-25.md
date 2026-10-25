<!-- doc-role: versioned-evidence -->
# HomenS.AI Auto VPN 0.9.1-alpha18

В «Помощи» сразу после «Настроек» добавлено обучение: 8 уроков с интерактивными схемами и 11 вопросов. Можно переходить к любому уроку или вопросу. Итог показывает текущий результат, правильные ответы с первой попытки и число проверок. Повтор ошибок сохраняет уже правильные ответы. Непройденные вопросы не считаются успешным обучением. Обучение не переключает VPN.

События и состояния получили понятные названия и ссылки на расшифровку. Успешная проверка отделена от восстановления и подтверждённого переключения; причина ошибки открывается отдельно. Недостающие исторические сведения не выдумываются.

Help immediately after Settings now contains 8 interactive lessons and 11 questions, direct question navigation, final scores, first-attempt statistics and wrong/unanswered-only retry. Correct answers remain learned; training never controls the router. Event/state descriptions and diagnostic causes have separate explanation links; successful checks never imply traffic switching.

Exact-source dual-runtime CI passed: 774 application and 112 QA tests per runtime, 50 UI suites in the primary runtime; complementary skips are recorded. MT3000 installation, 87 immutable files/modes, RPC, HTTP and pinned HTTPS verified. Auto ON, confirmed reserve, both VPN DNS/HTTPS healthy; settings, terms, 918 closed legacy latency rows and four speed results retained. Encrypted backups before/after independently decrypted and read (193 entries each).

Native-browser visual acceptance was unavailable. This UI-only update does not replace alpha17's separate VM weekly-storage evidence. Experimental prerelease; stable 0.9.0 unchanged.

## Evidence

Tested product `76498b5db82e8f5fa25f22d946b338c26b39c869`. Canonical IPK: 845457 bytes, SHA256 `f38a7f8926a6e717841af5cac0d13dfda9207fa3e9338bde6f624fc7c88fc81f`.

[QA receipt](../qa/EVENTS-HELP-ALPHA18-2026-10-25.json) · [Physical receipt](../qa/MT3000-ALPHA18-2026-10-25.json) · [English training](TRAINING.en.md) · [Обучение](TRAINING.ru.md).

New regressions cover EN/RU dictionary links for current controller states, check versus switch/recovery semantics, legacy gaps and conflicting records, lazy Help entry, every-question navigation, incomplete scores, wrong-only retry (82% to 100% with first-attempt 9/11 retained), stale actions and no router-control RPC. All 50 UI suites passed. Installed alpha18 source semantics applied to 231 redacted actual events: all 16 observed event types resolve, no detail gaps. This is source/data acceptance, not native-browser clicking.

Physical sequence: verified encrypted backup, normal Stop, install, files/modes/RPC/HTTP/HTTPS, normal Start and reserve restoration. Only expected lifecycle native_trial/native_until settings changed; unrelated options and terms version1 retained. Both VPN DNS/two HTTPS probes passed; no traffic-fault or speed test injected. Gateway127.0.0.2:8080 left running. Host networking and main MT6000 unchanged. Native visuals/external LAN/IPv6/Kill Switch/power-loss remain separate.

Publication follows the verified feature branch; no product changes after exact CI. Main and stable release remain unchanged.

## Published / Опубликовано

[GitHub alpha18](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha18) · [Gitea alpha18](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha18). Actual non-draft prereleases; four assets per service downloaded and SHA256 verified. Canonical source `c6f03ff98ace29f844011929b38620d3ed636a29`, public snapshot `12b716ce8ae9fd4377ec05a1e6044711e9f4b5a3`, identical release tree `a2bdb8680ed1b751269a3fb8cdcaddb43b57d596`. Main and stable 0.9.0 unchanged. Product remains exactly as CI source `76498b5db82e8f5fa25f22d946b338c26b39c869`; this closure changes documentation only.
