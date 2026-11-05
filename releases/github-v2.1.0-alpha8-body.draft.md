<!-- Draft of the GitHub release body for v2.1.0-alpha8. Not published: GitHub publishing is paused by the owner until the signing keys are set up. Fill the package line from releases/v2.1.0-alpha8.md after the record commit. -->

**Pre-release, test build.** Lua line 2.1.0. Changes since 2.1.0-alpha7 / Что изменилось по сравнению с 2.1.0-alpha7 — see the full lists below.

## Changes since 2.1.0-alpha7

- **Approved page:** Simple, Console and the first-run wizard, built exactly from the approved mockups; main module ~512 KB (was 941 KB).
- **Channel-failure detector (HMM, default):** decides when to leave the primary; a planned return needs P(primary healthy) ≥ 0.90 or 300 s of healthy checks. `hmm-fast` and the previous rule stay selectable.
- **Vendor-aborted failover retried in seconds** (5, 10, 20, 40 s) instead of after the 60 s cooldown — on 2.1.0-alpha7 this one case moved traffic after 84.2 s.
- **`rescue_stable`:** faster return when the reserve fails itself; `primary_stable` 120 s by default.
- **Large-packet (MTU) check fixed** for firewall-refused sends; `mtu_check` is in every status pass.
- **Forward resume after a real restart fixed** (2.1.0-alpha7 still lost 129.8 s there).
- **Probe authenticity:** pinned roots, request nonce, `probe_trust` reasons, optional DoH DNS check.
- **Optional Bayesian server pick** (`server_pick_model bayes`, default `simple`).
- **After the owner's Stop** GL manages the tunnels again (autostart and the `vpn-client` start link restored).
- **Formal-model fixes** K1 tail, K2–K5, K9, K11; the formal model is an offline CI gate.
- **Honest P95** in reports and the test history; first honest P95 on the router (2.1.0-alpha7, primary drop, n = 61): detection P95 7.47 s, traffic moved P95 29.8 s.

Verified on the router: the 2.1.0-alpha7 defects these changes fix. Not yet verified on the router: the 2.1.0-alpha8 changes themselves (unit, shared-case, mutation, simulator and formal-model tests pass in both runtimes).

## Что изменилось по сравнению с 2.1.0-alpha7

- **Утверждённая страница:** «Простой», «Пульт» и мастер первого запуска точно по макетам; основной модуль ~512 КБ (было 941 КБ).
- **Детектор сбоя канала (HMM, по умолчанию):** решает, когда уходить с основного; плановый возврат требует P(основной здоров) ≥ 0,90 или 300 с удачных проверок. `hmm-fast` и прежнее правило выбираются.
- **Отменённое вендором переключение повторяется через секунды** (5, 10, 20, 40 с), а не после паузы 60 с — на 2.1.0-alpha7 этот случай дал 84,2 с.
- **`rescue_stable`:** быстрый возврат, когда отказал сам резерв; `primary_stable` 120 с по умолчанию.
- **Исправлена проверка больших пакетов (MTU)**; `mtu_check` есть в каждом проходе статуса.
- **Исправлено доведение переключения после настоящего перезапуска** (на 2.1.0-alpha7 — 129,8 с).
- **Подлинность проверок:** закреплённые корни, одноразовая метка запроса, причины `probe_trust`, необязательный DNS через DoH.
- **Необязательный байесовский выбор сервера** (`server_pick_model bayes`, по умолчанию `simple`).
- **После твоего Stop** туннелями снова управляет GL.
- **Исправления по формальной модели** К1-хвост, К2–К5, К9, К11; модель — проверка офлайн-CI.
- **Честный P95** в отчётах и истории тестов; первый честный P95 на роутере (2.1.0-alpha7, отказ основного, n = 61): обнаружение P95 7,47 с, трафик перешёл P95 29,8 с.

Проверено на роутере: ошибки 2.1.0-alpha7, которые исправляет эта версия. Ещё не проверено на роутере: сами изменения 2.1.0-alpha8.

**Assets:** `homensai-auto-vpn_2.1.0-alpha8-1_all.ipk` + `.sha256`, `TEST-HISTORY.html` (every version and every router test result).

**License:** [HomenSAI Personal & Commercial Source License v1.0](https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE) — source-available, not open source. Contact: info@homensai.com.
