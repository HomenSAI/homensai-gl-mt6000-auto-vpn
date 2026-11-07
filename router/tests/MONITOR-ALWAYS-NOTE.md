# Monitor always on (owner main rule 07.11.2026) - working note

Branch fix/a9-monitor-always-20261107 (base 3461db32). Rule: the monitor ALWAYS runs; it may stop only by error and then
that is an ERROR state. Start (recovery) stays allowed.

## Findings
- procd: init.d `procd_set_param respawn 3600 5 0` (threshold 3600 s, timeout 5 s, retry 0 = unlimited respawn) for
  monitor and native instances. So a crash is respawned forever; the monitor stays off only when start_service returns
  early: config `enabled` != 1, unreadable config, integrity "stopped", wrong board without monitor_only.
- Stop paths: monitor_control RPC (Python agent.py; Lua rpc.lua only FORWARDs it to Python), legacy page button
  (router/legacy_page_build.py line ~161 "Stop monitor"). Native Stop Auto never stops the monitor.

## Steps
1. [done, commit 1] monitor_control.py: stop -> MONITOR-ALWAYS-ON (before lock/files/services), start unchanged. Tests updated
   (test_monitor_control, test_pair_ownership_guards, test_failure_matrix).
2. [done, commit 2] error catalogue rows (error_table.inc.js, error_rows_extra.inc.js, docs/ERROR_CODES.md via sync script),
   retire MONITOR-STOP-AUTO-FIRST / MONITOR-STOP-REQUESTED from the page; test_catalogue_safety_ui.js.
3. [done, commit 2] legacy page Stop-monitor button removal (legacy_page_build.py) ; monitor_panel.inc.js + ui/core.js error state
   when monitor absent (red, fix text, Start monitoring button); Node UI tests.
4. [done, commit 3; rebuild+sync done in commit 2] Lua parity: rpc.lua handle() refuses {enabled=false} with MONITOR-ALWAYS-ON (test in tests/lua/test_monitor_rpc.lua, passes in docker lua5.1) (rpc.lua forward; Lua test that stop code is the same) ; rebuild dashboard (build_sidebar_ui.py),
   sync-documentation.py, size bounds (66 % legacy, 49 % alpha51).

## Tests (docker homensai-vpn-python39:night)
- py: test_monitor_control, test_pair_ownership_guards, test_failure_matrix: pass except 2 Settings tests
  (RPC-RATE-LIMIT, container-only, identical on base).

## Commit procedure (important)
core.hooksPath points at the PRIMARY checkout .githooks whose old hook auto-bumps the version (it did once: alpha10 +
dashboard211; reverted). Commit with `git -c core.hooksPath=.githooks commit` (the worktree hook, check only) after
`python scripts/bump-version.py --fingerprint-only` and staging VERSION.json.
- node: test_catalogue_safety_ui, test_monitor_ui, test_monitor_always_ui (new), test_ui_races_ui, test_approved_ui (64 % legacy, <49 % alpha51) pass locally.

## Final test status (docker python39 image, node 24 local)
- py pass: test_monitor_control (11), test_pair_ownership_guards, test_failure_matrix (except 2 Settings RPC-RATE-LIMIT, same on base),
  test_rpc_security, test_channel_path. Same failures as base/unrelated: test_status_server rpc_list_and_acl, test_setup_config
  pending_delta, test_integrity_faults upgrade-codes (UPGRADE-READY, package hooks, untouched).
- lua: tests/lua/test_monitor_rpc.lua OK (7 tests).
- node: all router/tests/test_*.js pass except known test_lazy_help_ui.js. Page 64 % of legacy (<66), < 49 % of alpha51.
- sync-documentation.py --check OK; bump-version.py --check OK (version stays 2.1.0-alpha9-1, ui dashboard210).

## Not done / open
- init.d start_service still returns silently when main.enabled != 1 (page then shows the red ERROR + Restore button; the
  RPC start sets enabled=1). Making the init script ignore enabled=0 was not changed (install-time semantics, needs owner decision).
- respawn 3600 5 0 = unlimited respawn; no change needed.
