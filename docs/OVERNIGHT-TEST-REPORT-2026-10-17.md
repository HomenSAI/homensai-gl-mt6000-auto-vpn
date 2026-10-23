<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Overnight virtual test report - 17 October 2026

Result: **PASS within the virtual/offline scope below. Physical router acceptance is still pending.**

The bounded Windows runner started at 01:45:52 Europe/Berlin and completed at 06:58:25 on 17 October. Its process has exited and its exclusive lock is absent. The marked clone independently reports QMP paused at morning collection. Docker container liveness is not guest CPU liveness.

## Protocol runs

The immutable producer SHA256 is `94376a1842bab35d37f1d9c67980f0c98cc5062e4a4a4ab88b8fb55d3c3a2513`. The isolated network-none QEMU clone used four actual local encrypted tunnels: two WireGuard and two static-key UDP OpenVPN. DNS/TLS endpoints and fault scenarios were synthetic. The selector was the standalone namespace harness, not the GL.iNet native adapter. The two runs repeat the same seeded scenario family; they do not establish new unique scenario coverage.

| Measurement | Run 1 | Run 2 | Total |
| --- | ---: | ---: | ---: |
| Terminal | PASS | PASS | 2 completed |
| Guest monotonic seconds | 7,215.45 | 7,207.10 | 14,422.55 |
| Passed assertions | 1,364 | 1,380 | 2,744 |
| Failed assertions | 0 | 0 | 0 |
| Selected/standby cycles | 501 | 509 | 1,010 |
| Fault/restoration rounds | 21 | 21 | 42 |
| Steady-state selected/standby probes | 1,002 | 1,018 | 2,020 |
| Steady-state probe failures | 0 | 0 | 0 |
| Missing assertion events | 0 | 0 | 0 |
| Raw probe records | 1,306 | 1,318 | 2,624 |
| Deliberately injected negative samples | 63 | 63 | 126 |
| Bounded restoration-wait negative samples | 6 | 2 | 8 |
| Completed primary restorations | 21 | 21 | 42 |
| Independent cleanup | PASS | PASS | PASS |

The 134 negative samples belong to injected faults and bounded restoration waits, not unexplained production outages or failed assertions. Every raw record was classified and reconciled against the scenario and counters. Steady-state probes do not retry to mask failures. Host start-to-capture intervals were 7,236.80 and 7,235.33 seconds; they include observation delay and are not exact producer runtimes. Guest wall timestamps are not used as host chronology.

Independent cleanup found no owned/orphan cohort processes, no owned namespaces and zero private test-key files after either run. The root routes/rules/network/firewall fingerprint remained unchanged.

## Offline checks

Full exact-snapshot CI passed on `28a347a9945d22c2e82135829e2d3377359c5933`: 309 application tests and 30 QA tests per runtime; 11 Node UI suites in the development image. Python 3.9/Lua had zero skips; Python 3.11 control had seven documented Lua skips. Package privacy and reproducibility passed. The unchanged alpha7-12 IPK SHA256 is `1b44c36f27a82501be19bdf0e722658b2b1f5ddf1cc208c3a82cbbb8eed40244`.

After pausing the guest, 23 repetitions passed: nine Python transaction/crash tests, seven Node transaction regressions, and the 200-case / 1,737-assertion fault-model suite per repetition. These are repeated executions of 200 unique model cases, not 4,600 unique scenarios. Families include delays, simulated power/flash/torn-journal failures, RPC, IPv6, conntrack, workers, compound failures and idempotency. They do not represent actual hardware power cuts or physical IPv6 acceptance.

## Errors found and corrected before unattended execution

| Time, Europe/Berlin | Cause or error | Correction and verification |
| --- | --- | --- |
| 17 Oct 01:41 | Repeated launches would reject an existing collector file; fixed-name export could reuse an earlier run's archive. | Collector is identified and validated by its own immutable hash; symlinks rejected; archive/log paths are per run. Three new regression checks and full CI passed. |
| 17 Oct 01:45 | Runner reset consecutive-error count before freshness validation; repeated stale snapshots would remain first errors. Found by code inspection, not an observed stale-data incident. | Reset moved after successful freshness validation. Preparation run cooperatively STOPPED at 102.20 seconds / 22 assertions; independent cleanup PASS. Preserved separately and excluded from all completed totals. Corrected snapshot passed CI before restart. |

No runtime errors were recorded by the corrected overnight runner. The older strict two-second soak failure remains a historical FAIL with unknown precise phase; this successful night does not retrospectively explain or erase it.

## Limits and next step

No physical GL-MT6000 access, upload, installation, VPN/firewall/route changes or provider credentials were used. This report does not certify native vendor-worker arbitration, live LAN client failover, real provider availability/speed, hardware flash/power behavior, or Internet-facing attack resistance. Next acceptance step is a separately authorised physical test window with a LAN witness and verified recovery path.

Reviewed public aggregate evidence: `qa/OVERNIGHT-2026-10-17.json`. Raw receipts, classified CSVs, logs and synthetic archives are retained locally under ignored `private/overnight-20261016T234552Z`; no private key files are published. Local Git/Gitea are saved first. GitHub history/tag conflict remains unresolved; no forced publication or tag overwrite was performed.
