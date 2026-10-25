<!-- doc-role: versioned-evidence -->
# HomenS.AI Auto VPN 0.9.1-alpha19

Выбранная стартовая «Карточка»: исходная кнопка Auto сразу под состоянием, основной канал выше резервного, реальные адреса и задержка. Зелёный сохранён, красный смягчён50%. «Открыть текущее меню» ведёт к полному управлению.

Карточка доступна только после актуального соглашения, завершённого мастера, проверок текущей пары и свежего подтверждения работающего Auto/активного канала. Неполная настройка, очередь команды, переключение, устаревшие данные и неподтверждённый маршрут не выдают готовность. Рабочий резерв разрешён и при отказавшем основном. Прямые ссылки на настройки/тесты/журнал сохраняются; кнопка карточки использует существующее управление Auto.

Selected startup card with the original Auto control under its status, primary/reserve order, observed endpoints/delay and full-menu entry. Current terms, completed setup, current-pair preparation and fresh confirmed running Auto/healthy active path are required. Pending/stale/mismatched evidence never shows a ready card. A healthy reserve remains eligible after primary failure. Red intensity is reduced50%; green unchanged.

Exact-source dual-runtime CI passed: 774 application/112 QA per runtime,52 UI suites in primary (complementary skips recorded). MT3000 install/87files/modes/RPC/HTTP/pinnedHTTPS passed; AutoON/confirmedreserve, both VPN DNS/HTTPS healthy.1545 closed old latency rows, four speed results, settings and terms retained;193-entry encrypted backups before/after independently decrypted/read.

On the actual owner router the initial-wizard completion flags remain false. The correct first entry is therefore the existing setup wizard, until the operator completes it. Upgrade does not set these flags automatically. The card with completed setup was tested against actual current router data with flags changed only in memory, never saved on device. Native-browser visual acceptance was unavailable. Experimental prerelease; stable0.9.0 unchanged.

## Evidence and scope

Tested product `3d759a889c71e771afd1b2747facd8c7539b00af`. Canonical IPK848531bytes SHA256 `d0a79466a8e79afb948f5eeb17bb195d39b5be01e022f84218b02a50ccb715cd`. [QA](../qa/SIMPLE-HOME-ALPHA19-2026-10-25.json) · [Physical](../qa/MT3000-ALPHA19-2026-10-25.json) · [Startup behavior](SIMPLE-HOME-2026-10-25.md).

Source regressions execute real Auto/path/health models and generated entry routing in EN/RU: primary/reserve, wrong pair, missing terms/setup/tests, stale data, pending/transition, click-time validation, original-control forwarding, explicit deep links/full menu and stale-home watchdog. No browser-storage flag grants eligibility. Stop/start/restore reserve were actually executed on MT3000 through normal APIs; not native browser clicks.

Only expected native_trial/native_until lifecycle settings changed; all35 own options retain their other semantics. setup_complete/onboarding_complete remain false. Physical closed latency rows were compared against the independently decrypted pre-update backup;1545 preserved, open minute excluded. Four speed results retained. Encrypted pre/post backups193entries each were independently decrypted/read in memory. No new speed/fault test or fake network observations. No hostnetwork/mainMT6000/firmware changes. Old alpha17 VM storage proof remains separately scoped, no new VM needed for this frontend-only change.

Native-browser visuals were unavailable (empty connected browser inventory). Installed exact bytes, RPC, HTTP8080/pinnedHTTPS and actual-frame model/render proof are verified independently; they are not visual acceptance. ExternalLAN/IPv6/KillSwitch/powerloss remain separate. Current first page is intentionally the existing wizard. Do not report a completed setup or active-card screenshot on the physical device.

Publication follows the verified feature branch; product unchanged after CI. Stable release and main are preserved.

## Publication status

[Gitea alpha19](http://127.0.0.1:8796/localadmin/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha19) is published with four assets downloaded/hash-verified. GitHub feature source/tag is saved (`1332d3158b5fe40c3dbd88d57d2b09a1e3c378c0`), but its release/assets remain pending due to coreAPI quota exhaustion; reset announced10:35Berlin25October2026. Both release trees `ad9ddfb6ddd42392c844aa40acf48665d8aeb151` match. Source/main/stable preserved. Later native Computer Use attempt stopped before app input because browserURL could not be verified; no native visual acceptance claimed.

## GitHub publication completed

https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.1-alpha19 — actual non-draft prerelease, four assets downloaded and SHA256 verified. Gitea published files reverified through their normal release/download URLs. Earlier quota blocker resolved; product/tags unchanged. Native visual limit remains.
