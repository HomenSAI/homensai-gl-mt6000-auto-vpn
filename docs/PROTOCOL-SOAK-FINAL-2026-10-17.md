<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Final isolated protocol soak report

Collected: 2026-10-17T01:23:51.015422+02:00 (Europe/Berlin).

## Result

**PASS** — 1335 assertions, 495 cycles; zero failed assertions and zero missing events.
Host start-to-collection interval: 7246.56 seconds. Guest monotonic elapsed: 7200.87 seconds.

Failures were deliberately injected. Zero failed assertions means the expected failure/recovery behavior passed; it does not mean every synthetic server remained available.

## Actual scope

Marked isolated OpenWrt 21.02.7 x86/64 guest inside a Docker network-none QEMU copy. Four real local encrypted tunnels: two WireGuard and two static-key UDP OpenVPN. Generated DNS/TLS endpoints and a standalone namespace selector; no real VPN provider credentials or physical router access.

Producer source SHA256: `94376a1842bab35d37f1d9c67980f0c98cc5062e4a4a4ab88b8fb55d3c3a2513`. Immutable producer was not patched during the run.

## Observed profile checks

| Synthetic server | Selected-path DNS/TLS checks | Standby bound DNS/TLS checks |
| --- | ---: | ---: |
| wga | 123 | 122 |
| wgb | 137 | 115 |
| ova | 122 | 118 |
| ovb | 113 | 140 |

These are counts of verified checks, not connection durations, throughput or production uptime. Standby probes are interface/mark-bound; this does not certify uninterrupted user sessions during switching.

## Repeated fault and restoration assertions

| Assertion | Successful observations |
| --- | ---: |
| failed-primary-DNS-TLS-refused | 20 |
| same-protocol-reserve-healthy | 20 |
| same-protocol-route-switch | 20 |
| cross-protocol-route-switch | 20 |
| restored-primary-bound-healthy | 20 |
| actual-return-and-rollback | 20 |
| DNS-failure-distinct | 20 |
| DNS-fault-reserve-unaffected | 20 |
| kill-switch-blocks-direct-underlay | 20 |
| real-conntrack-TCP-observed | 20 |
| scoped-TCP-cleanup-keeps-UDP | 20 |
| root-network-unchanged-after-faults | 20 |

## Cleanup and preservation

- Producer reports cleanup complete and original root network fingerprint unchanged.
- Independent witness confirms no owned namespaces, child/orphan cohort processes or private test-key files remain.
- Independent root route/rule/network/firewall checkpoint matches before/after.
- Collector reached terminal PASS with exact counters and complete retained-event coverage.

## Corrected defects

1. Cold probe processes imported http.server/mimetypes unnecessarily; a captured traceback showed >20 seconds in import. Moved that dependency into server mode. The later 2-second strict run failed one standby sample at 85 minutes; its DNS/TLS phase was not retained, so its cause remains unknown. Final test budget is explicitly aligned with the application socket timeout of 3 seconds, with detailed raw samples and no retry masking.
2. Slow synthetic endpoint bootstrap was mistaken for transport failure. Added a bounded 60-second readiness barrier before real bound DNS/TLS acceptance.
3. Package builder selected obsolete dashboard28/ui15 while menu referenced the newer interface. Added dynamic selection and validation of menu -> packaged JS -> packaged CSS plus legacy LuCI controller alignment.
4. Inactive/stale cards showed a null interface and historic latency as current. Corrected labels, suppressed invalid current latency and required fresh healthy evidence for current OK counters.
5. Observation/witness helpers needed correction for a hash-prefix typo and absent stat utility. Replaced with derived filenames and minimal built-in os.stat/time. Startup-response timeout was diagnosed read-only; collector was not duplicated.

Earlier failed runs are retained in qa/protocol-*-failed.json and the timestamped WORKLOG. The final pass does not overwrite those failures.

## Package and CI

- Source `e2bb3a7a2603695ba2691b69a48e77ea5d0d54b0`, Python 3.11.2: 309 application tests, 27 QA tests, 11 UI suites, 7 documented skips; result PASS.
- Source `e2bb3a7a2603695ba2691b69a48e77ea5d0d54b0`, Python 3.9.15: 309 application tests, 27 QA tests, 0 UI suites, 0 documented skips; result PASS.
- Package `homensai-auto-vpn_0.7.0-alpha7-12_all.ipk`, SHA256 `1b44c36f27a82501be19bdf0e722658b2b1f5ddf1cc208c3a82cbbb8eed40244`, 456653 bytes; reproducible across both runtime builds.

## Raw-probe accounting

All 1281 raw records matched the frozen scenario in exact order.

- 495 selected-path and 495 standby probes: all successful; no retries in this steady-state phase.
- 60 deliberately negative samples across 20 fault rounds.
- 7 negative samples during bounded primary-restoration waiting; all 20 restorations eventually passed.
- These negative probes are not 67 production outages or 67 failed assertions.
- CSV timestamps are guest wall-clock values; use the host collection times for real-world chronology.

## Not established by this report

- GL-MT6000 ARM firmware/vendor-worker arbitration, actual LAN client switching, power-cut recovery, external provider behavior or WAN-facing security.
- Native full server -> channel -> protocol hierarchy acceptance on GL.iNet.
- No traffic/session continuity, speed or availability guarantee.
- No package was uploaded or installed on the physical router during these tests.
