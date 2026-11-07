# Monitor always started at boot (owner decision 07.11.2026 15:10) - working note

Branch fix/a9-monitor-boot-20261107 (base integ/a9-night-20261107, 76b9c474). Owner: "Monitoring is always started,
regardless of any conditions." Follows MONITOR-ALWAYS-NOTE.md ("Not done": init.d returned silently with enabled != 1).

## Decisions
- init.d start_service opens the `monitor` instance (Lua monitor / Python agent; hv-core only when Auto may run)
  independent of option `enabled`, onboarding/terms, integrity modes normal/no-c/python/no-auto and the maintenance
  marker (maintenance_report only reports). procd respawn stays `3600 5 0` (unlimited).
- `enabled` != 1 (older version's Stop monitor, manual uci, unreadable config): monitor only. The Auto supervisor
  (native instance, hv-core) is NOT started - that gate stays exactly as before. init.d writes
  /var/run/homensai-vpn/service-auto.json {"code":"SERVICE-AUTO-OFF"} (removed at every start), and Start is refused with
  SERVICE-AUTO-OFF in both twins (auto_control.service_auto_blocker, lua/control_request.service_auto_blocker), like
  BH-04's INTEGRITY-AUTO-BLOCKED: no intent queued for a supervisor that does not run, nothing starts Auto later.
- Kept (start nothing): integrity `stopped` - Lua AND Python program files damaged and not restorable; no verified
  program is left, a damaged one would run as root under unlimited respawn and could write wrong state/history.
  Unsupported board without monitor_only=1 - the hardware deployment check (postinst refuses the same; test
  test_sdk_wrapper_cannot_start_instances_after_failed_postinst_with_default_mode); "model selection never bypasses
  detected hardware checks".
- Runtimes: verified that neither agent.py nor lua/monitor.lua / hv_core.lua reads main `enabled`; a static test pins that.
- Page: monitorLightModel no longer uses settings.enabled; fresh data = green whatever the flag. Restore button only
  for a monitor that produces no data. With enabled=0 the page shows a note + "Switch the Auto service on" (the same
  monitor_control start RPC, which sets enabled=1; starts no Auto).

## Steps
1. init.d + this note + init.d shell tests (test_monitor_boot.py, test_monitor_deployment.py).
2. Start refusal SERVICE-AUTO-OFF (Python + Lua parity) + tests + catalogue row.
3. Page/status texts (monitor_panel, ui, legacy settings card) + Node tests; rebuild + sync; fingerprint.

## Status
- step 1 committed: init.d + shell tests (test_monitor_boot 10, test_monitor_deployment) green in Docker; related init tests green (125).
- step 2 committed: Start refused with SERVICE-AUTO-OFF (auto_control.service_auto_blocker + lua control_request), parity test, catalogue row + ERROR_CODES.md; test_auto_control, test_lua_control_request, test_maintenance_gates, test_trace_fixes, lua test_control_request (22) green.
- step 3 committed: page - monitorLightModel ignores settings.enabled (fresh data = green); enabled=false shows a SERVICE-AUTO-OFF note + "Switch the Auto service on" (monitor_control start); new UI Settings + Start modal; legacy settings card button only for explicit enabled=false; Node tests (128 files) green; page 608585 B.
- step 4 committed: docs/CURRENT-STATUS.md + INTEGRITY-MATRIX config row (docs only).

## Integration review items (coordinator 07.11.2026, FINDINGS.md in private/integration-review-20261107)
- IR-01 [done, commit 5]: monitor_control start refused with MAINTENANCE-IN-PROGRESS while the package hooks hold the
  maintenance marker (checked under the control lock; Lua rpc.lua keeps forwarding the start to Python). Page:
  status.maintenance.state==='active' without fresh data = yellow "Package update in progress" (code
  MAINTENANCE-IN-PROGRESS), no Restore button (block, new UI Settings, Start modal), monitorDown() not raised. A stale
  marker is no excuse (red again). Tests: test_monitor_control (2 new), test_monitor_always_ui; lua test_monitor_rpc ok.
- IR-08 [done, commit 6]: a refused NEW preinst (old prerm already stopped the service) starts the installed service
  again (`/etc/init.d/homensai-vpn start || LIFECYCLE-RESTART-FAILED`, only when the init script exists), prints
  LIFECYCLE-REFUSED-PREINST and exits with the guard's code; package-hooks.mk regenerated. Test:
  test_package_lifecycle.test_refused_preinst_starts_the_stopped_service_again.
- Procedure note: never use `git stash` here - the stash list is shared by all worktrees (another agent's stash was
  popped by mistake once and stored back unchanged as d67546cf).

## Final test status (docker homensai-vpn-python39:night, node 24 local)
- Full Python suite at step 3: 2620 tests, 5 failures, all identical on base 76b9c474 (test_failure_matrix.Settings x2
  and test_priority_recovery pending_delta: RPC-RATE-LIMIT, container-only; test_setup_config pending_delta;
  test_status_server rpc_list_and_acl - the CI-hermeticity agent's area). All tests/lua/test_*.lua pass.
- After IR-01/IR-08: test_monitor_control, test_package_lifecycle, test_monitor_deployment, test_monitor_boot,
  test_maintenance, test_maintenance_gates (55) OK; lua test_monitor_rpc OK; all 128 router/tests/test_*.js pass.
- bump-version --check VERSION-CURRENT 2.1.0-alpha9-1; sync-documentation --check OK; dashboard210.js 609 333 B (< 615 658).
