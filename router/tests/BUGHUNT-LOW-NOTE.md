# Bug hunt low findings BH-04..BH-07 (07.11.2026) - working note

Branch fix/a9-bughunt-low-20261107 (base integ/a9-night-20261107 @ 38ed0981). Source: private/bughunt-20261107/FINDINGS.md.
BH-01..03 (init.d, package_hooks.py) belong to another agent and are not touched here. Version stays 2.1.0-alpha9-1
(bump-version.py --fingerprint-only only). No push, no router.

## Status
- [done, commit 1] BH-04: Start refused with INTEGRITY-AUTO-BLOCKED while RUNTIME/integrity.json mode is no-auto or
  stopped (auto_control.integrity_blocker + lua/control_request.integrity_blocker, checked in the first control lock after
  the revision and the speed pause, so trial Start and the programmatic boot resume are refused too; nothing queued, no
  resume marker). No report / other mode / unreadable report: the init gate decides. Catalogue row RU+EN
  (error_table.inc.js -> help210.js, docs/ERROR_CODES.md).
- [done, commit 2] BH-05: outside-change ring items keep 'mono' (monotonic seconds: time.monotonic in Python,
  /proc/uptime via runner.clock in Lua) written by the pair hook (telegram_state.outside_record / pair.lua outside_notice);
  the sender (telegram_report.outside_notice / telegram.outside_notice) ages an item by the monotonic clock when both
  stamps exist and now >= stamp (the ring is RAM, never crosses a boot), else by the wall clock as before. A +10 h NTP
  step no longer drops a fresh HOLD. Key format unchanged.
- [done, commit 3] BH-06: pair_auto.rescue_health / pair.lua M.rescue_health keep the hold_reserve rescue probe result
  per failure episode (session id + reserve id) for RESCUE_PROBE_INTERVAL = 60 monotonic s (Python module memory
  RESCUE_PROBE, Lua env.rescue_probe of the supervisor); tick clears it as soon as the precondition (on reserve,
  hold_reserve, reserve not healthy and failed by the detector) no longer holds. WAN down: one live probe per minute
  instead of one per tick. Comments ("probed once") updated in both twins. Journal path
  (committed_recovery_decision) unchanged (not in the finding).
- [done, commit 4] BH-07: transient refusals (SPEED-BUSY, PAIR-MANUAL-BUSY, PAIR-MANUAL-REQUEST-UNCONFIRMED) are not
  stored for a client_request_id (pair_manual.TRANSIENT_REFUSALS / transient_refusal, Lua manual_request.TRANSIENT /
  transient_refusal), and ledger_find ignores such an entry left by an older version, so Retry with the same id is
  decided afresh. Accepted answers and lasting refusals are still stored and replayed (no double switch). UI
  (ui/actions.js): a refusal with replayed:true shows "Earlier answer to this click" with a "Click again" button that
  sends a fresh id; a non-replayed refusal keeps the old dialog. Page 612040 B (64 % legacy).
- [done, commit 2] secret scan: tests/lua/test_telegram_outside.lua a.key value is now 'FAKEQUJDRA==' (scanner placeholder
  form, still contains QUJDRA so the leak check is unchanged); `secret_scan.py --tree HEAD` passes after this commit.

## Tests (docker homensai-vpn-python39:night, node 24 local)
- BH-04: test_auto_control (IntegrityGateStartTests), test_lua_control_request (parity no-auto/stopped),
  lua/test_control_request.lua (20 tests), test_held_start_handover, test_native_control, test_trial_start: pass.
  Node: test_code_catalogue_ui, test_error_coverage_ui, test_catalogue_safety_ui, test_approved_ui (64 % legacy),
  test_code_links_ui, test_monitor_ui, test_install_reason_ui: pass. sync-documentation.py --check OK.
- BH-05: test_telegram_outside (3 new: clock step +10 h sends; monotonic-old marked; fallback to wall; twin item with
  mono), lua/test_telegram_outside.lua (11 tests, 2 new), test_outside_change_policy, test_telegram (PYTHONPATH),
  test_telegram_brief, test_telegram_items, test_lua_speed_telegram, test_pair_auto, test_lua_auto,
  lua/test_outside_change, test_speed_telegram, test_auto_pair, test_auto_recovery: pass.

- BH-06: test_rescue_no_journal (2 new: 7 ticks -> probes [1,1,1,2,2,2,3] for False and unknown, held reason kept;
  a new session probes afresh), lua/test_rescue_no_journal.lua (3 tests, 1 new, same steps), test_committed_recovery: pass.

- BH-07: test_pair_manual_request_id (3 new: SPEED-BUSY not kept and Retry accepted then replayed; BUSY/UNCONFIRMED
  not kept; an older transient entry ignored), test_pair_manual, test_lua_manual_request, test_manual_control,
  lua/test_manual_request.lua (12 tests, 1 new), lua/test_manual_prewrite.lua; node test_manual_request_id_ui.js
  (2 new blocks); all router/tests/test_*.js pass except test_lazy_help_ui.js (fails on base 38ed0981 too).
- Flaky: lua/test_sys.lua failed once in a full parallel Lua run, passes alone twice (untouched module).

## Commit procedure
`python scripts/bump-version.py --fingerprint-only`, stage VERSION.json, `git -c core.hooksPath=.githooks commit`.
