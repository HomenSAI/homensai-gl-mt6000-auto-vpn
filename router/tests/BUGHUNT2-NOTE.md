# Bug hunt second pass BH2-01..BH2-05 (07.11.2026) - working note

Branch fix/a9-bughunt2-20261107 (base integ/a9-night-20261107 @ c9d2c652). Source: private/bughunt-20261107/FINDINGS-2.md.
BH-04..07 (fix/a9-bughunt-low) and init.d/package_hooks belong to other agents and are not touched here. Version stays
2.1.0-alpha9-1 (bump-version.py --fingerprint-only only). No push, no router.

## Status
- [done, commit 1] BH2-03: any object status reply without rpc_error is a router answer (`uiRouterAnswered`, views.js refreshNow
  and boot), so a SERVICE-STOPPED / SYSTEM-001 reply no longer turns the header grey "Router not answering" after 60 s.
  `monitorDown()` (core.js): the router answered with `error` and the monitor model is `problem` -> it wins over grey:
  main light key `monitor-down`, lamp grey (channel state unknown; the contract keeps red for proven no-internet) with the
  monitor title "ERROR: monitoring is not running", the code and "Restore monitoring"; Auto indicator red ⚠ `monitor-down`
  with the code. A transport failure afterwards sets rpc_error -> grey silence as before.
  Test: tests/test_monitor_error_header_ui.js (SERVICE-STOPPED and SYSTEM-001, RU+EN, 120 s of answers, boot-only reply,
  transport failure stays grey, healthy reply unchanged).
- [done, commit 2] BH2-01/02: inventory.lua reads every numeric option through one strict finite parser `num(raw,frac)`
  (F-46/R2-03 grammar: blanks, a sign, <=9 digits; frac options hmm_theta/hmm_dur_b/return_pg/slider_t also one '.', <=15
  digits) and `clamp(raw,lo,hi,default)`; 'nan', 'inf', '1e999', '0x3c', '1e1', '2.5', '1_0' take the documented default.
  priority: whole 1..1000 else 100 (priority_config rule); onboarding_version >=0. No NaN/Inf can reach cjson.encode.
  native_policy.lua (supervisor) reads the detector options with the same decimal grammar, so page and Auto agree.
  stats_until twins (stats_mode.until / lua/accounting.lua stats.until_time, and inventory.lua) share one grammar:
  digits with an optional fraction (<=12 + <=6); float() had read 'inf'/'1_0'/'1e9', Lua tonumber '0x10'.
  Test: tests/test_inventory_strict_numbers.py (finding vectors, priority, recovery_* == recovery_settings.normalized,
  every numeric option's default, inventory == native_policy detector options, stats_until twins + inventory).
- [done, commit 3] BH2-04: one code for every nesting refusal: rpc_input.py maps the C scanner's RecursionError (~1000 levels)
  to RPC-INPUT-COMPLEXITY, the code Lua (canon nesting limit 64) and both walkers (depth > 64, nodes > 10000) already
  answer. Catalogue: the RPC-INPUT-COMPLEXITY row already reads "too big or too deeply nested"; the RPC-INPUT-DEPTH row is
  kept unchanged for replies of older installed versions (no generated help/doc churn). test_fool_regressions pins
  COMPLEXITY for '['*60000. Test: tests/test_rpc_input_twins.py (16 shared vectors through both decoders).
- [done, commit 4] BH2-05: equal-time outside-change decisions keep the ring (insertion) order in both twins: Lua's
  table.sort compares the ring index (was the alphabetical key), Python's stable sorted() already did; the decision
  recorded last is told as the newest. Only the sort line in telegram.lua outside_notice and a comment in
  telegram_report.py (BH-05 of fix/a9-bughunt-low edits the age lines just above; no overlap). Test:
  tests/test_telegram_outside_ties.py (same ring file through both senders, both recording orders; d.clock=nil so it
  also runs after the BH-05 merge).

## Tests
- Node 24 local: all 125 router/tests/*_ui.js pass except test_lazy_help_ui.js, which fails identically on the base
  c9d2c652 (legacy qa/legacy-page/dashboard.js 957 408 B > the 24.1 % bound 953 642 B since the CSP merge 6130c3f1; the
  legacy page is not touched here). Shipped page 613 091 B: 64 % of legacy (test_approved_ui), under the 49 % alpha51 bound.
- BH2-01/02 (docker homensai-vpn-python39:night): test_inventory_strict_numbers (6, fail on the base), check_inventory.py,
  test_onboarding, test_monitor_deployment, test_native_policy_settings, test_hmm_detector, test_network_advisor,
  test_cusum, test_gl_sensors, test_fast_switch (literal updated to the clamp line), test_setup_detector, test_sqm,
  test_pair_ownership_guards, test_server_pick_bayes, test_native_switch, test_native_control, test_stats_mode,
  test_lua_monitor, test_lua_backend, test_lua_history, test_formal_fixes, test_fool_regressions, test_lua_monitor_item2,
  test_retention_model; lua/test_monitor_accounting, test_native_policy, test_backend, test_diag_cache, test_fast_switch:
  pass. test_probe_target_log.test_documentation_is_present errors only because the runner archive has no docs/.
- BH2-04: test_rpc_input_twins (2, fail on the base), test_fool_regressions, test_rpc_security, lua/test_monitor_rpc: pass.
- BH2-05: test_telegram_outside_ties (Lua case fails on the base), test_telegram_outside, test_outside_change_policy,
  test_telegram_brief, test_telegram_items, test_lua_speed_telegram, test_telegram (PYTHONPATH=lib),
  lua/test_telegram_outside, lua/test_outside_change: pass.

## Commit procedure
`python scripts/bump-version.py --fingerprint-only`, stage VERSION.json, `git -c core.hooksPath=.githooks commit`.
