# Integration review fixes IR-02..IR-06 - working note, branch fix/a9-intreview-20261107

Handoff note (owner rule 07.11.2026): keep it current until the fix is merged. Base: integ/a9-night-20261107 @ 76b9c474.
Findings: private/integration-review-20261107/FINDINGS.md (IR-01 and IR-08 belong to fix/a9-monitor-boot, IR-07 needs an
owner decision). Version stays 2.1.0-alpha9-1 (fingerprint-only bumps).

## IR-02 verify_gap misses DEGRADED-ON-RESERVE - DONE
- `pair_auto.VERIFY_GAP_STATES` and `lua/pair.lua` `M.VERIFY_GAP_STATES` now include DEGRADED-ON-RESERVE (the held pass on
  the pinned reserve publishes it with a kernel proof since the owner decisions of 07.11).
- The other checks are unchanged: a DEGRADED-ON-RESERVE without a confirmed kernel channel path (journal publications)
  or with a real blocker still publishes BLOCKED.
- Shared cases `verify_gap_cases.json`: the old "a degraded reserve is not kept" case is replaced by 4 IR-02 cases
  (RESERVE-FAILED kept, RESERVE-HEALTH-UNKNOWN kept, no kernel proof -> BLOCKED, real blocker -> BLOCKED). 25 cases.
- Tests: `test_verify_gap.py` 4 OK, `lua/test_verify_gap.lua` 3 OK (docker python39:night, --network none).

## IR-03 boot_resume retries a Start that BH-04 refuses for the whole boot - DONE
- `boot_resume.FINAL` gains INTEGRITY-AUTO-BLOCKED; Lua twin `boot_resume.RETRY` gains `['INTEGRITY-AUTO-BLOCKED']=false`
  (final) and names `['MAINTENANCE-IN-PROGRESS']=true` explicitly (stays a waiting code: a package operation ends
  within the window).
- Tests: `test_boot_resume.py` +2 (final with a fake monotonic clock: one press; maintenance waits then RESUMED),
  `lua/test_boot_resume.lua` +1. Both new tests fail on the base code (checked). Py boot suites 63 OK, Lua 19 OK.
- Process note: `git stash` is shared by all worktrees of the repository; a stash push/pop here swapped contents with
  the parallel fix/a9-monitor-boot worktree for a moment (that agent restored its own tree; this tree was restored
  from the scripted edits). Baseline checks now use a temporary copy, never `git stash`.

## IR-04 marker action reads 'install' during an upgrade - DONE
- `lifecycle_guard.mark_maintenance`: a `prepare` (new preinst/postinst) that finds this boot's live `upgrade` mark
  (`live_upgrade_mark`: same boot_id and at most 900 s of uptime, no boot id -> wall clock -60..900 s; the rules of
  maintenance.classify; a symlink/damaged/other-boot/old mark is a fresh install) keeps action=upgrade. So
  status.maintenance.action and the MAINTENANCE-INTERRUPTED record (clear_stale -> upgrade-result.json) say upgrade.
- `router/package-hooks.mk` regenerated with `python router/package_hooks.py` (generated file; package_hooks.py itself
  is untouched - it belongs to fix/a9-monitor-boot; regenerate again after the merge).
- Tests: new `test_intreview_lifecycle.py` (5; 4 fail on the base code), `test_lifecycle_guard.py` subtest now starts
  each action from a clean marker. Lifecycle/maintenance suites 69 OK.

## IR-05 F-17: a SIGKILLed supervisor passed the second guard - DONE
- `lifecycle_guard.expect_shutdown` replaces `forget_shutdown` in the first prerm guard (check/upgrade): when an Auto
  supervisor daemon is alive (`service_processes(root,supervisors=True)`: native_switch.py / lua/auto.lua /
  lua/hv_core.lua with `daemon`) or /proc is unreadable, it writes `supervisor-shutdown.json` =
  {ok:false, code:LIFECYCLE-RECOVERY-UNFINISHED, expected:true} (O_EXCL|O_NOFOLLOW temp + rename). Only the supervisor's
  own ok:true (native_switch.shutdown_record / lua auto.shutdown, unchanged) replaces it, so a supervisor killed after
  term_timeout leaves ok:false and the -stopped guard refuses LIFECYCLE-RECOVERY-UNFINISHED.
- Without a live supervisor (monitor only: mode no-auto, monitor_only; the hv_core standby; rpcd calls; an apply child)
  nothing is expected and the older record is removed as before, so a monitor-only service never blocks a package
  operation. No new error code (the record code is the existing catalogued LIFECYCLE-RECOVERY-UNFINISHED).
- Residual (fail-closed, documented): hv_core.lua daemon whose Auto task is between runs (RESTARTING, 5 s) or waiting for
  native.lock at the stop does not run auto.shutdown, so the record stays ok:false and that upgrade is refused once.
- `router/package-hooks.mk` regenerated again.
- Tests: `test_intreview_lifecycle.py` KilledSupervisorIsRefused (5; all fail/error on the IR-04 code), Lua
  `test_maintenance_tick.lua` +1 (auto.shutdown replaces the expected record). Lifecycle suites 74 OK, Lua 3 OK.

## IR-06 maintenance twins differ on a symlinked marker - DONE
- `lua/maintenance.lua` `read_marker` now lstat-checks the marker path first (`M.lstat`: nixio.fs.lstat, else sys.lstat;
  replaceable): a symlink (dangling too) or any non-regular file is unreadable -> stale 'invalid', never followed,
  whatever reader the caller passes (monitor runner.read_file, control_request deps.read, pair env.run.fs.read, the
  default read_file of clear-stale). clear_stale reports it (MAINTENANCE-INTERRUPTED, reason invalid, action '') and
  removes the link itself. `maintenance.py` behaviour unchanged (it already refused; docstring now says so).
- Before: Lua followed a symlink to an active marker (MAINTENANCE-IN-PROGRESS) where Python said stale, and a dangling
  link was "none" in Lua but stale in Python.
- Shared cases: `maintenance_cases.json` new "files" section (4: regular active, symlink to an active marker, dangling
  symlink, directory), read from real files by `test_maintenance.py` SharedFiles and `lua/test_maintenance.lua`.
  The Lua test fails on the base code (checked). Python 8 OK, Lua 4 OK.

## Full runs (docker homensai-vpn-python39:night, --network none, branch head 58209c40)
- Lua: every `lua/test_*.lua` OK except `test_sys.lua` 1 of 9 once under load; alone 3/3 OK (known flake, see
  VERIFY-GAP-NOTE.md).
- Python `unittest discover`: 6 failures, all also failing on the base 76b9c474 (checked on the same image) or the same
  test_sys flake: test_failure_matrix.Settings x2, test_priority_recovery pending delta, test_setup_config pending delta
  (RPC-RATE-LIMIT instead of the setup code), test_status_server.Signature (rpc signature hash),
  test_lua_fast_policy [test_sys.lua]. None is touched by IR-02..IR-06.

## Not done here
- IR-01, IR-08 (fix/a9-monitor-boot), IR-07 (owner decision). After merging with fix/a9-monitor-boot regenerate
  `router/package-hooks.mk` (`python router/package_hooks.py`) and re-record the fingerprint.
