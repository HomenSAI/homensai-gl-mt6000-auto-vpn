# Maintenance marker (plan item 54, audit F-16/F-17) - working note, branch fix/a9-maint-marker-20261107

Handoff note (owner rule 07.11.2026): keep it current until the fix is merged. Base: integ/a9-night-20261107 (5df089ea).

## Findings
- F-16: the lifecycle lock ended before the service stop; a Start (auto_control.start, pair_auto.request,
  lua/control_request.lua start) between the assessment and the stop was accepted.
- F-17: the removal did not wait for the final recovery confirmation: init.d stop only asks procd, the second guard ran
  while the supervisor could still be restoring; native_switch.serve ignored the pair_shutdown result.

## Design
- PERSIST/maintenance.json {action install|upgrade|remove, boot_id, uptime, time, pid}: written by every guard run under
  the control lock BEFORE the assessment (lifecycle_guard.mark_maintenance); any guard refusal removes it; postinst
  removes it before enable/restart (and a trap on every exit); a successful prerm keeps it for the new preinst/postinst.
- Readers: maintenance.py / lua/maintenance.lua (shared cases tests/maintenance_cases.json). Active only in the same
  boot and <= 900 s of uptime since the last write (wall clock only without a boot id). Else stale: blocks nothing.
- init.d start: a stale marker becomes upgrade-result.json MAINTENANCE-INTERRUPTED (red line) and is removed.
- prerm second guard is '<action>-stopped': waits (<= 330 s, outside the lock) until no service process
  (daemon/standby/apply child) is alive, then refuses if RUNTIME/supervisor-shutdown.json says ok != true
  (LIFECYCLE-STOP-UNFINISHED / LIFECYCLE-RECOVERY-UNFINISHED). The first guard deletes an older record.

## Done
- Step 1: maintenance.py + lua/maintenance.lua + shared cases; guard marker + stop wait + shutdown record check;
  hooks (prerm -stopped, postinst trap/rm, rollback rm); init.d stale report. Tests: test_maintenance.py,
  lua/test_maintenance.lua, test_lifecycle_guard.MaintenanceMarkerTests; adjusted test_lifecycle_upgrade_recovery
  (second guard action) and a pre-existing regex bug in test_integrity_faults (LIFECYCLE-UPGRADE-READY matched).

- Step 2: gates -> MAINTENANCE-IN-PROGRESS: auto_control.start (first lock and again before the write),
  pair_auto.request (under its lock), return_request; agent.maintenance_refusal for fault_start (control_reply, also the
  status socket), pair_manual (pair_manual_reply), manual_switch, speed_start; Lua control_request.start (both locks),
  fault_start -> FALLBACK (agent.py refuses), monitor.lua pair_manual/speed_start -> FALLBACK; supervisor tick
  (pair_auto.tick / pair.tick) publishes ARMED reason MAINTENANCE-IN-PROGRESS instead of begin, the Start stays queued.
  Stop is never refused. A running session is not gated (the guard refuses a package operation while Auto runs).
  Tests: test_maintenance_gates.py, lua/test_maintenance_tick.lua, lua/test_control_request.lua (new case).

- Step 3: supervisor-shutdown.json writers: native_switch.shutdown_record(pair_shutdown(...)) at the end of serve,
  lua auto.shutdown (pair.recover()==true). Tests: test_maintenance_gates.ShutdownRecord, lua/test_maintenance_tick.

- Step 4: status.maintenance (agent.py, lua monitor: maintenance.public), page line in integrityBanner
  (MAINTENANCE-IN-PROGRESS active; MAINTENANCE-INTERRUPTED from a stale view or upgrade-result.json), catalogue rows
  RU+EN: MAINTENANCE-IN-PROGRESS / -INTERRUPTED / -CLEAR-FAILED (error_table.inc.js), LIFECYCLE-STOP-UNFINISHED /
  -RECOVERY-UNFINISHED / -MAINTENANCE-FAILED (error_rows_extra.inc.js); regenerated dashboard210.js, help210.js,
  qa/legacy-page, docs (sync-documentation). Tests: test_install_reason_ui.js, test_maintenance_gates.Status.
- BH-01: init.d integrity gate fails closed: an unrestorable damaged tool -> no-auto (INTEGRITY-TOOL-DAMAGED), a crash,
  no answer or an unknown mode -> no-auto (INTEGRITY-TOOL-FAILED), both written to integrity.json (red line);
  start_service maps any other mode to no-auto. Rows INTEGRITY-TOOL-FAILED, INTEGRITY-NO-AUTO, updated
  INTEGRITY-TOOL-DAMAGED. Tests: test_integrity_faults.InitGateTest (crashing/garbled tool, damaged copy).
- BH-02: preinst records the running version (its payload manifest '# version') in PERSIST/upgrade-from; the
  rollback restores the pristine copy only when its manifest version equals it, else UPGRADE-ROLLBACK-UNAVAILABLE
  (log tag UPGRADE-ROLLBACK-VERSION, own row). Tests: UpgradeRollbackTest.test_bh02_*.
- BH-03: postinst embeds the package version (build_ipk passes VERSION; the SDK fragment uses
  $(PKG_VERSION)-$(PKG_RELEASE), no literal in package-hooks.mk). Before the guard it refuses (exit 1,
  UPGRADE-NOT-INSTALLED, nothing touched, the rolled-back version keeps running, upgrade-result.json kept) when
  upgrade-result.json says UPGRADE-ROLLED-BACK from exactly this version and the installed manifest is still the
  version it was rolled back to. opkg install --force-reinstall unpacks the files again and installs normally.
  Tests: UpgradeRollbackTest.test_bh03_*.
  LIMITATION (not verifiable offline): that opkg-lede really re-runs the postinst of an unpacked package on a later
  run, and what it reports, is not verified on a device; the refusal only keeps opkg from marking the package
  installed. After such a rollback opkg still lists the new package (unpacked, its .list and prerm); a removal then
  uses the new package's prerm and file list. Recovery: opkg install --force-reinstall <verified ipk>.

## Next
- All steps and BH-01..03 done. Open: router confirmation of the opkg behaviour after a rollback (BH-03), and a
  full Python discover run on the final tree (only the targeted suites listed below were run).

## Tests
- Step 4: all router/tests/*.js pass except test_lazy_help_ui.js (pre-existing on the base: 'legacy main module shrank
  by at least 24.1%'); sync-documentation --check OK; lua test_monitor*.lua OK; test_lua_monitor, test_lua_monitor_item2,
  test_status_* OK except test_status_server.Signature (pre-existing on the base: rpc list hash).
- Step 3: test_maintenance_gates OK; lua test_auto*.lua, test_hv_core.lua, test_maintenance_tick.lua OK.
- Step 2: test_maintenance_gates test_maintenance test_auto_control test_lua_control_request test_pair_auto (78 OK);
  lua test_maintenance_tick, test_control_request, test_auto_pair, test_maintenance OK.
- Docker homensai-vpn-python39:night: test_maintenance test_lifecycle_guard test_package_lifecycle
  test_lifecycle_upgrade_recovery test_lifecycle_record_parity test_integrity_faults: OK; lua test_maintenance.lua OK.
