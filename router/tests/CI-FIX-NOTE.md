# Offline CI failures on integ 1bee6c3e - working note, branch fix/a9-ci-20261107

Handoff note (owner rule 07.11.2026): keep it current until the fix is merged. Base: integ/a9-night-20261107 (090d9f6c,
already holds the T4-A fix, so test_trace_fixes T4-A is not part of this branch). Version stays 2.1.0-alpha9-1.

CI conditions (scripts/offline-ci.ps1): read-only root, --user=65534:65534, --network=none, tmpfs /work and /tmp with
`rw,nosuid,nodev` - Docker adds `noexec` to a --tmpfs unless `exec` is given, so nothing under /tmp can be executed.

## Causes and fixes
1. test_lifecycle_upgrade_recovery.UpgradeOverInterruptedJournal (2 errors, LIFECYCLE-MAINTENANCE-FAILED):
   the maintenance marker (44d63421, plan item 54) is written by lifecycle_guard.main into ROOT/etc/homensai-vpn. ROOT
   is the guard's configurable base (test_lifecycle_guard patches it); these two older tests patched only snapshot and
   control_lock, so main wrote the real /etc/homensai-vpn (passes as root on a writable image, fails on the read-only CI
   root). Product unchanged (it must write the real path on the router). Tests now patch ROOT to the fixture, exclude the
   marker from the byte-identical comparison and assert it instead (install / upgrade; removed after a refusal).
2. test_integrity_faults.SnapshotTest.test_failed_publication_of_the_copy_is_refused_not_made (exit 0, SNAPSHOT-MADE):
   the fake `mv` was a script in a temp dir on PATH. On the noexec /tmp the shell skips the unexecutable fake and runs
   the real mv, so publication succeeded. Not a product fault, not related to BH-02/BH-03 (reproduced: noexec -> FAIL,
   exec -> OK on the same tree). Test now defines `mv() { return 1; }` and sources the tool (it calls mv by name), the
   repository's established pattern for noexec CI (test_server_pick, test_sqm).
3. test_status_server.Signature.test_rpc_list_and_acl_are_unchanged (hash 177abe06... != 80d4063b...):
   the hash was last set in 8d76c90b (F-14 telegram_destination). Diff of `agent.rpc('list')` 8d76c90b -> 090d9f6c:
   one line, pair_manual gained the optional `client_request_id` (F-35, 5c4650ef; BH-07 6333d883 kept it). No new
   method, ACL json unchanged since 8d76c90b, pair_manual is write-ACL only (not in read). Intended and least-privilege;
   hash updated with a comment in the signature log of the test file.

4. Surfaced once router/tests passed (qa stage, never reached on 1bee6c3e):
   - qa/test_fool_backend: monitor_control {'enabled': false} -> MONITOR-ALWAYS-ON flagged VALID-REQUEST-REFUSED. The
     refusal is the owner rule of 07.11 (MONITOR-ALWAYS-NOTE); the oracle now treats only {'enabled': true} as valid.
   - qa/test_p95_wording + qa/test_kalman_wording: docs/CURRENT-STATUS.md line 12 (5a730800) used the forbidden
     'Honest P95' and 'Kalman ... 66 point-PASS'; reworded, same facts, counts left to PRINCIPLES-SCIENCE.

5. Surfaced at the tools stage: tools/tests test_secret_scan.Wiring.test_hook_refuses_a_stale_fingerprint_and_never_bumps
   (6998af31) runs .githooks/pre-commit, which calls `python`; the python311 image has only python3, so calls.txt was
   never written. Without `python` on PATH the test defines python() -> sys.executable in front of the sourced hook.

## Done
- Fixes committed separately on fix/a9-ci-20261107: 66ee2aeb (lifecycle ROOT), 50a7c670 (integrity mv), ee876dac (rpc
  hash), f67c5b70 (fool oracle), 5eb4cdb2 (status wording), d69c2b30 (hook python).

## Tests (source d69c2b30, CI options: read-only root, 65534, no network, noexec tmpfs)
- scripts/offline-ci.ps1 -SkipTlc -RuntimeImage homensai-vpn-python39:night, python311:local: secret/privacy scans,
  router/tests, qa, tools/tests, formal (11 profiles), lab, lua contracts, UI rebuild (not stale) PASS; stops at
  node router/tests/test_approved_ui.js ("main module 615765 B") and test_lazy_help_ui.js ("legacy main module shrank by
  at least 24.1% from alpha51"): page-size bounds, owned by fix/a9-size (not touched here).
- qa/run_offline_ci.py --runtime-only in homensai-vpn-python39:night: CI-RECEIPT result PASS (application 2606 tests,
  30 skipped; qa 575; tools 103; formal 11 profiles / 2018104 states, xfail 0; lab 60; lua 17; ipk
  sha256 f82fe39c...). TLC skipped (tools/formal is another branch).
