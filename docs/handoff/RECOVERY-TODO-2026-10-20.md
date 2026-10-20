# Current continuation after the 20 October crash

This is the active backlog. Older alpha6/alpha10 and stopped-review documents remain historical evidence. The owner explicitly selected the mobile GL-MT3000 for physical tests and confirmed it is not yet connected. No physical GL-MT6000 writes or tests are authorized. Follow [the staged GL-MT3000 plan](../GL-MT3000-TEST-PLAN.md); actual identity, firmware and bootloader remain unknown.

| Task | Current evidence / acceptance still needed |
| --- | --- |
| Preserve recovery checkpoint | Original 62e4fa9 saved to Gitea and a SHA256-verified source/history/TODO ZIP on D:. Refresh after the final commit and verify bundle restoration. |
| F01 full-block expiry | Kernel timeout set plus independent generation-scoped cleanup. Timer-spawn failure refuses before installation. Actual disposable-VM nft timeout survived cleanup-process loss; old timer preserved a replacement VPN guard. This is not device/LAN acceptance. |
| F02 emergency Stop | Durable global epoch with unreadable policy; malformed requests cannot bypass it or prevent writing Stop. Local regressions pass; device timing remains unverified. |
| F03 recovery integrity | Existing malformed/empty journals refuse. Active transactions require safe recovery identity, finite time and bounded counters. Package lifecycle refuses empty existing journals too. |
| F04 request replay | Return must match current transaction and one-minute validity window; stale/future/missing identities refuse. |
| F05 total HTTPS deadline | Monotonic deadline below buffered response reader; slow-body regression passes. Real-device Stop latency still requires measurement. |
| F06 release recovery | Failed guard removal remains RELEASE-PENDING/BLOCKED across restart; cleanup retries without route writes. Start/monitor shutdown/package lifecycle refuse active recovery; UI keeps a red warning even when intent is off. |
| F07 release identity | Alpha9 hooks/dashboard/fingerprint regenerated; package reproduced with SHA256 fd2e6c09e195cbce8741121e0d84aeb20df5702922dcef322e30686fa5678c2e (648680 bytes). Install-kit pins and publication manifest are checked. Final publication still requires exact-current-commit CI and remote verification. No old-tag replacement. |
| Current-source virtual integration | Independent copy only: actual upgrade 17 checks PASS; hardening/auth/nft 18 PASS; storage 6 PASS; procd monitor-crash recovery PASS (68.85 guest seconds). Two virtual CPUs/512MiB were used after single-CPU contention. Short observation is recorded separately; 12h/current hardware acceptance remains open. Original stopped disks preserved. |
| Inherited fool-proofing helpers | Helper now wired in the generated page: bilingual field validation and keyed duplicate/cooldown handling for system/Telegram setup and monitor/recovery/speed preferences. 27 Node UI suites pass. Emergency Stop remains immediate. This does not claim every legacy RPC action was converted; current-source browser verification remains separate. |
| GL-MT3000 preparation | `00-platform-probe.sh` gathers only allowlisted platform facts, stdout only; local classifier never grants installation or native switching. Read actual device identity/firmware/bootloader and obtain a recoverable backup before installation. |
| Vendor/native acceptance | Cooperative GL.iNet worker arbitration, inactive profiles and native multi-hop remain blocked on a verified adapter and test device. Do not reuse MT6000 board/hash exceptions for MT3000. |
| LAN/device acceptance | Independent client DNS/HTTPS/exit, failed primary/reserve/both, Stop/expiry/crash, IPv6/Kill Switch/special rules and management preservation remain open. |
| Endurance/unattended | No completed current-source long run or hardware reboot/power-loss acceptance. Define unattended policy separately; short local/VM tests cannot close it. |
| Save/publication | Local Git and Gitea first; reviewed exact-tree GitHub snapshot only after exact-source CI/package match. Private bundles/disks/raw logs never become public assets. |

Independent review found and corrected additional cases: stale per-trial Stop must become global when policy is unreadable; a corrupt alarm marker must not crash recovery or repeat a full block; malformed Stop timestamps must fail closed; public status must report unknown rather than crash or claim off. A generation-specific nft set makes old timer cleanup unable to delete a replacement guard.

## Current VM evidence, retained failures

Initial attempt, retained as FAIL: an independent cold-boot disk copy uses a new isolated Docker container with network=none; original stopped containers/disks were not resumed. Alpha8 actual opkg upgrade, version, own config, protected network/firewall and Auto-off checks passed (8 checks), then `fresh-upgraded-agent` failed because RPC did not return within the test window. Later diagnostic reads found the expected fresh alpha8 monitor/procd and RPC object. This initial attempt is not relabelled PASS; the follow-up below records the separate exact-package alpha9 checks.

Follow-up: with own daemons stopped, trivial Python startup decreased from 10.085s to 2.143s and RPC succeeded in 8.656s. A separate two-vCPU/512MiB lab boot completed alpha9 upgrade/RPC/procd acceptance (17 checks), actual negative tests (18), storage adversity (6) and monitor-process recovery. The earlier one-vCPU failure is retained. Test-harness failures were also retained and corrected: wait for procd's asynchronous termination/lock release, and track only session-owned timer shells rather than every subprocess factory call. Neither a corrected harness nor a VM pass certifies real GL.iNet workers, native LAN failover or physical power recovery.

The first ten-persona synthetic browser report had three incomplete/reload cases and is retained. Corrected bounded app/CSS readiness, per-document telemetry and fail-closed CLI were tested; personas 1/3/6 then passed individually (62/80/59 interaction steps, no JS errors/out-of-range values/storms/lags/overflow). This is not a completed 50-persona or hardware UI acceptance matrix.

## Platform inspection procedure (prepared, not executed on hardware)

On the deliberately selected test router, `sh 00-platform-probe.sh > platform.tsv`; retain the report privately. On the PC, `python scripts/classify-platform.py PRIVATE_PLATFORM.tsv` returns BLOCKED or MONITOR-CANDIDATE-REVIEW. Both keep installation unauthorized and native switching refused. Missing dependencies are reported, never installed by the probe. Bootloader version and recovery backup stay UNKNOWN/not obtained until separately verified.

The [official Beryl AX guide](https://docs.gl-inet.com/router/en/4/user_guide/gl-mt3000/), [model firmware download page](https://dl.gl-inet.com/router/mt3000/stable) and [firmware families](https://www.gl-inet.com/en-us/pages/firmware-versions) were consulted on 20 October. These references do not establish the firmware currently installed on the owner's device. Do not flash or assume a bootloader version from a marketing model name.
