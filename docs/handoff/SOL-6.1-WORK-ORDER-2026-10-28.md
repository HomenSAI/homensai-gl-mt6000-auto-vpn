# Work order for Sol 6.1 (high) — HomenS.AI Auto VPN, after 0.9.1-alpha50

> **Кратко (RU).** Шесть задач по итогам разбора проекта (docs/REVIEW-2026-10-28.md), в порядке выполнения:
> 1) выпуск без второго прогона CI; 2) тесты инструментов и стенда в CI, Dockerfile образа, проверка Lua в квитанции;
> 3) проверка каждой правки при сборке страницы; 4) справка и обучение подгружаются только при открытии;
> 5) обновление раз в 10 секунд перестраивает только открытую страницу; 6) новый README и короткий файл передачи.
> Исполнитель делает всё сам: код, тесты, CI, сборку, установку на выделенный MT3000, запуск Auto и публикацию
> (GitHub + Gitea) — по разрешению владельца от 28.10.2026. Старые пакеты остаются в Git (решение владельца).
> Пишите владельцу по-русски, простыми словами.

Owner decisions recorded on 28 Oct 2026:
- Old packages and old page modules **stay in Git** (review item P3 is closed as "keep").
- Sol 6.1 has the same rights as the previous executor: change code, run CI, build, install on the **dedicated GL-MT3000**, start Auto after a successful install, publish to GitHub and the local Gitea, all without asking again — but only after CI PASS, a package hash equal to the CI hash, an encrypted backup before and after, and a passed install verification.
- Second CI run at release: replace it with a **record-commit verification** (Task 1).
- Help and training: **load on demand** (Task 4).

## 0. Before you start

Read, in this order: `CLAUDE.md`, `docs/CURRENT-STATUS.md`, `docs/REVIEW-2026-10-28.md`, `docs/ROADMAP.md`, this file. The private runbook for device work and publication is `private/SOL-6.1-RUNBOOK.local.md` (not in Git, never publish it).

Hard rules (from `CLAUDE.md` and the owner):
- **One executor on the MT3000 at a time.** Before any device step, record yourself in `private/ACTIVE-EXECUTOR.local.json` (owner thread, start time, scope). The previous executor does not touch the router while you hold it. Release it (status `complete-…`, next action) when you finish.
- The primary **MT6000 and the Windows networking are out of scope.** Never touch them.
- Never accept terms for the owner. Auto may be started only by the install procedure after a passed verification (owner authorization above); never start it any other way.
- Preserve failed evidence (move it to a dated `evidence-…-failed-…` folder, never delete). Never force-push, never move or overwrite a published tag or package.
- Never publish anything from `private/`. Secrets never go into files, logs, commits or messages.
- Model selection never bypasses the detected hardware/firmware/readiness checks.

Facts that save time:
- The page that ships is the **hybrid** design: `router/build_sidebar_ui.py` → `router/hybrid_release_patch.py`. `router/minimum_*` sources are tested but **not built**; editing them changes nothing on the router.
- The page is generated: sources `router/*.inc.js` (+ `design_layer.css`, `simple_home.css`, `hybrid_ui.css`) → `router/files/www/luci-static/resources/view/homensai-vpn/dashboardNNN.js` + `uiNN.css`. Run `python router/build_sidebar_ui.py` after every UI change. Since alpha50 CI rebuilds and fails on any difference (`CI-UI-BUILD-STALE`), line endings ignored.
- `python scripts/bump-version.py` bumps the version **and** renames the page module (dashboardNNN/uiNN) and rebuilds. After later edits: `--fingerprint-only`, then `--check`. Then `python scripts/sync-documentation.py`. `docs/CURRENT-STATE.en.md` / `.ru.md` must contain the new version; also update `docs/CURRENT-STATUS.md` (new section on top) and `docs/handoff/CURRENT.md`.
- Tests: `./scripts/test-local.ps1` (full: router tests, qa tests, UI suites, privacy) or `./scripts/test-local.ps1 -CheckCommand '<sh>'` for a subset. UI suites run directly with `node router/tests/<name>.js`. CI: `./scripts/offline-ci.ps1` on a clean HEAD, or `-SourceCommit <full sha>` when untracked files exist. Run CI in the background with output to a log file; it takes 30–40 minutes.
- Windows editing pitfalls: many files are CRLF in the working tree; read bytes, normalise, edit, restore CRLF, and assert each anchor occurs exactly once. Shell heredocs mangle backslashes (`\r\n`, `\.`) — write edit scripts to a file instead.
- Colour rule for every channel lamp and card (owner): green = Auto works on it, yellow = alive and waiting for Auto, grey = waiting for the router answer, red = error. Lamps blink gently by default (reduced motion respected). Owner name, author, version and style stay visible on every page.
- Error codes: every code shown must exist in the catalogue (`router/error_rows_extra.inc.js` + base rows); tests enforce this.

## Task 1 — Release without a second CI run (review P4)

Today: CI on the code commit (30–40 min) → build → record commit (package, `.sha256`, `VERSION.json` sha256, `router-test-kit/02-install.sh` EXPECTED_SHA/SIZE, `releases/vX.md`) → **CI again** on the record commit → publish. The second run only proves that the record commit did not change code.

Change `scripts/publish-reviewed.py` so that publication of a record commit B accepts the CI receipt of its parent code commit A when, and only when:
1. `B^ == A` (direct child), the receipt is a valid dual-runtime PASS for A (`checked_receipt`), and A is an ancestor of the published branch head;
2. `git diff --name-status A B` contains only: `A releases/homensai-auto-vpn_<pkg>_all.ipk`, `A releases/<same>.ipk.sha256`, `A releases/v<version>.md`, `M VERSION.json`, `M router-test-kit/02-install.sh`;
3. in `VERSION.json` only `application.sha256` changed (parse both versions and compare all other keys), and it equals the receipt hash; in `02-install.sh` only the `EXPECTED_SHA=`/`EXPECTED_SIZE=` lines changed and they equal the package hash and byte size;
4. `sha256(releases/<pkg>.ipk)` equals the receipt hash and the `.sha256` file content.

Any other difference → refuse with a catalogued code (e.g. `PUBLICATION-RECORD-SCOPE`) and require a full CI on B as today. Keep the old path (receipt for B itself) working.

Also: give `save-gitea.ps1` its own timeout (30 min) inside `publish-reviewed.py`, so the private wrapper `publish_long.py` is no longer needed; keep the 180 s default for other commands.

Acceptance: unit tests in `qa/` for each refusal (extra file, changed code line, wrong hash, non-child commit, edited notes of an older release) and for the accepted case; one real release published with a single CI run; the release notes say so.

## Task 2 — CI covers tools and lab code; reproducible CI images; Lua proven (review P6)

1. `tools/tests/test_gitflow.py` and any offline-safe `lab/` unit tests never run in CI. Add them to `qa/run_offline_ci.py` (separate `check(...)` calls, counts in the receipt). Lab scripts that need a VM, the router or the network must be skipped explicitly, not silently imported.
2. The 3.11 CI image `local-dev-tools:installed` has no Dockerfile in the repository (the 3.9 image has `qa/runtime-python39/Dockerfile`). Add a pinned Dockerfile next to it (e.g. `qa/runtime-python311/Dockerfile`) that reproduces the tools CI needs (python, node, lua5.1 + lua-cjson as used by tests, tar), and a README line on how to build them offline. Do not change the images CI uses until the new ones pass the full suite with the same package hash.
3. The receipt records `lua_available`, but publication does not check it. Require `lua_available: true` for the non-runtime-only row in `checked_receipt` (and make sure the Lua tests actually ran, e.g. a count of Lua-backed tests in the receipt).

Acceptance: receipt shows tools/lab counts and Lua; publication refuses a receipt without Lua; full CI PASS on both runtimes with an unchanged package hash.

## Task 3 — Every UI build patch is asserted (review P2)

`router/build_sidebar_ui.py` applies ~240 text replacements to the frozen `dashboard16.js`; about 110 use plain `source.replace(...)` and silently do nothing when their anchor disappears. Convert each to `must_replace` (exactly one occurrence) — or, where several occurrences are intended, a helper that asserts the expected count. Same for `simple_home_patch.py` and `hybrid_release_patch.py` (the latter already asserts).

Method: convert in small groups; after each group rebuild and require the generated `dashboardNNN.js` / `uiNN.css` to be **byte-identical** (ignoring line endings) to before. A replacement that no longer matches anything is dead: remove it and note it in the commit message. Do not change behaviour in this task.

Acceptance: no unasserted `source.replace` left that targets the dashboard source (grep in a test); generated page unchanged; full UI suites pass.

## Task 4 — Help and training load on demand (review W5)

The page module is ~1.25 MB (≈370 KB gzipped); help (`help_panel.inc.js` ≈97 KB), training (`learn_panel.inc.js` ≈52 KB, `learn_scenes.inc.js`) and the long error-catalogue texts (`error_rows_extra.inc.js` ≈184 KB, `error_table.inc.js` ≈69 KB) are always loaded.

Goal: the main module carries only what the first screen needs; Help, Training and the full error catalogue load when first opened.
- Use LuCI's own loader (`L.require('homensai-vpn.<name>')` → `/luci-static/resources/homensai-vpn/<name>.js`, a `baseclass.extend({...})` module) or an equivalent that works on GL.iNet 4.11 LuCI. Version the file name per release like the dashboard (e.g. `help125.js`) so browsers never use a stale copy; extend `scripts/bump-version.py` to rename it.
- Keep an **eager code → title map** (code, area, EN/RU title) in the main module: notices, lamps and `errorCodeLink` must keep naming codes without waiting. Only the long cause/remedy texts and the Help/Training bodies move.
- While loading: show "Loading… / Загрузка…"; on failure: a catalogued code (new row, e.g. `UI-HELP-LOAD-FAILED`) with a Retry button; the rest of the page keeps working. Deep links (`help/topic/<id>`, error-code links that open the catalogue at a code) must still land on the right place after loading.
- Package: `router/build_ipk.py` must ship only the current versioned lazy files (like it does for `dashboard*.js` / `ui*.css`), and `scripts/sync-documentation.py` must still generate docs from the sources. Update the private `verify-installed.py` asset list.

Acceptance: main module at least 30 % smaller; tests cover lazy load success, failure + retry, deep link after load, and the code→title map; installed page verified on the MT3000 (open Help, Training, an error link); the owner sees no change except a short first-open delay.

## Task 5 — The 10-second refresh rebuilds only the visible page (review W3/W4)

Today every status poll calls `draw(status)`, which rebuilds all pages; focus and scroll are then restored by helpers (`viewport_state.inc.js`, `restorePageControlFocus`). Since alpha50 a hidden browser tab skips the poll entirely (`hvStatusTick`).

Goal: on each poll rebuild the sidebar status, the Auto control and the **currently shown page** only; mark the other pages stale and rebuild a stale page when it is shown (the `showPage` hooks in `hybrid_release_patch.py` are the entry point). Keep: `pointerHeld` deferral, `lastGoodStatus`, outage drawing with `routerWall()`, `uiRenderFailed`, live chart and speed live timers, the floating Go back/Top buttons, statistics reset buttons (`attachStatsResets`), error-code linkification.

Acceptance: a UI test with a counting fake DOM shows one page rebuilt per poll; switching to a stale page shows fresh data immediately; existing UI suites pass; on the router the page stays responsive (measure time of `draw` before/after in the browser console and report it).

## Task 6 — README and handoff that describe today (review P5)

- `README.md` / `README.ru.md` start with ~20 lines of an old alpha21–25 changelog and contain broken words (e.g. "AutoONconfirmedreserve"). Rewrite both: what the app does, supported hardware (dedicated GL-MT3000; MT6000 continuous mode not accepted), install from the GitHub release, how Auto works in plain words, what is proven and what is not (external LAN, 24-hour soak, power cut, IPv6), links to `docs/CURRENT-STATE.*`, help and error codes. Keep the owner attributes (name, author, HomenS.AI). History goes to the release notes, not the README.
- `docs/handoff/CURRENT.md` is ~190 KB of accumulated sections. Move everything except the newest section into `docs/handoff/HISTORY-2026-10.md` (unchanged text, so evidence is preserved) and keep `CURRENT.md` short: current version, what runs on the MT3000, open work (link to ROADMAP and this order), how to release. Old `NEXT-AI-*` / dated handoff files stay as historical records; do not delete them.
- Run `python scripts/sync-documentation.py`; `qa/audit_documentation.py` and the documentation tests must pass (no broken local links). Documentation-only changes do not need a router reinstall.

## Optional — Task 7: remaining router load (review W1)

Profile the status RPC on the router (the private `rpc-bench.py`; alpha50: status median 1.83 s, page refresh 3.59 s with Auto running) per component (manual/pair controls, channel path, speed status, readiness) and cache or defer what dominates, the way alpha50 cached the history (`read_public(..., cache=RUNTIME/...)`, keyed by file identity). Report numbers before/after.

## Release procedure (each batch)

1. Code + tests → `python router/build_sidebar_ui.py` → `./scripts/test-local.ps1` green.
2. `python scripts/bump-version.py`; update the docs listed in section 0; `sync-documentation.py`; `bump-version.py --fingerprint-only` and `--check`.
3. Commit (message ends with your attribution line), `./scripts/offline-ci.ps1 -SourceCommit <sha>` → PASS.
4. Isolated build of the same commit in the Python 3.9 container; its hash must equal the CI hash (runbook).
5. Record commit: package, `.sha256`, `VERSION.json` sha256, `02-install.sh` EXPECTED_SHA/SIZE, `releases/v<version>.md` (EN + RU, what changed, what is proven, what is not).
6. Device: backup before → stop Auto → snapshot → install → verify → start Auto → backup after → evidence folder (runbook).
7. Publish GitHub + Gitea (runbook); after Task 1 lands, without a second CI run. Push the branch to Gitea.
8. Tell the owner in Russian: what changed, router state, link, what is still open. Update `docs/REVIEW-2026-10-28.md` status columns.

Suggested batches: alpha51 = Tasks 1–3 (process; page bytes unchanged), alpha52 = Tasks 4–5 (UI), then Task 6 as a documentation-only commit (no reinstall), Task 7 if time allows.
