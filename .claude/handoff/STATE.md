# State at independent-review handoff

Historical snapshot. Active 20 October state/TODO: ../../docs/handoff/ACTIVE-STATE-2026-10-20.json and ../../docs/handoff/RECOVERY-TODO-2026-10-20.md. Do not substitute this older evidence for the current checkout or device observations.

Recorded 2026-10-17T13:30:29.306937+00:00. This is a checkpoint, not a production-readiness certificate.

## Product and source identities

| Item | Verified value |
| --- | --- |
| Product | HomenSAI Auto VPN |
| Package | 0.8.0-alpha2-1, Architecture all, MIT |
| UI | dashboard43 / ui22; English default, optional Russian; HomenS.AI Style 1.14.3 |
| Package bytes | 470221 |
| Package SHA256 | 8de85658c568d3a2610ba545d263a190e218f5d2ba128a01969678087810c2c8 |
| Product/release source | 8ab8011e85647ed4179f69d02d9ffe7cb9f62af5 |
| Pre-handoff canonical HEAD | 1b0768ffb02810679218434b849e4ebe7f4021f4 |
| Pre-handoff GitHub main | 3d043ecfa9c7963949e09666d6f8f438edacc4e8 |
| Public release tag v0.8.0-alpha2 | 4c6bea35d87dbfda4f9bc46042555b0371d63d77 |
| Release | https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.8.0-alpha2 |

The commit containing this handoff is newer documentation. Derive its actual canonical/public SHA from git log and the publication receipt; do not confuse the two histories or claim a self-referential SHA is embedded here. Runtime/package content is unchanged by this handoff.

## What is implemented and verified locally

- Read-only monitoring of existing router VPN profiles; separate connected/healthy/selected concepts, server/channel/protocol metadata and ranking/statistics.
- Bounded experimental native controller, transaction/lease/recovery checks, LAN client witness helpers and Auto control. Their presence does not certify arbitrary real-device switching.
- Sidebar UI, responsive layout, service/events/readiness pages, setup/recovery/Telegram wizards, reviewed recovery presets, incident details and secret-redacted printable HTML.
- Checkpoint structure/calendar/numeric validation, good-backup preservation and recovery after corrupt current data.
- Reviewed local-first GitHub snapshot/release publishing with durable resume and remote commit/tag/asset verification.
- Exact pre-handoff immutable dual-runtime CI PASS: 341 application + 36 QA tests per runtime; 15 JS UI suites. Python 3.9/Lua zero skips; Python 3.11 control seven Lua skips.
- Virtual alpha2 installation: 17 checks, own settings and protected network/firewall/main routes preserved, monitor fresh, Auto OFF.
- Three actual controlled opkg interruption/recovery stages were performed on the preceding alpha1-4 baseline. They do not prove physical power-loss or arbitrary mid-flash atomicity for alpha2.
- Actual disposable 64KiB tmpfs ENOSPC/corruption tests passed six checks after a retained helper failure.
- Corrected actual LuCI matrix: 60 transitions, ten sections x EN/RU x measured 414x896, 978x808, 1280x300.
- System/recovery wizard actual save/reopen/back/cancel checked on virtual synthetic profiles; Telegram empty-secret-field/missing-token refusal checked without real delivery.
- Downloaded synthetic incident HTML checked; one-page LibreOffice PDF rendered and visually reviewed. Native browser local-file Print was blocked by URL policy and remains unverified.

## Deliberately stopped endurance run

| Field | Final observed value |
| --- | --- |
| State | STOPPED by direct user request, NOT PASS |
| Frozen source | 8ab8011e85647ed4179f69d02d9ffe7cb9f62af5 |
| Started UTC | 2026-10-17T12:29:35.307269+00:00 |
| Finished UTC | 2026-10-17T13:26:07.315079+00:00 |
| Planned duration | 43200 seconds |
| Observed elapsed | 3391.75 seconds |
| Samples / failures / gaps | 57 / 0 / 0 |
| Maximum monitor RSS | 22228992 bytes |
| Independent cleanup | Confirmed; clone paused; producer and watchdog exited |

Zero observed failures during this partial window is not a completed 12-hour pass. The earlier 60-second smoke PASS is separate evidence. All current known project test runners were checked as stopped; Git/Docker infrastructure services remain available.

## Virtual versus physical environment

Virtual acceptance used marked container homensai-vpn-qemu-alpha7: Docker network none, privileged false, no host mounts; OpenWrt 21.02.7 x86/64, kernel 5.4.238, Python 3.9.16, LuCI git-23.093.57360-e98243e. It is a disposable QEMU copy with synthetic inactive profiles and Auto OFF.

Target device is GL.iNet GL-MT6000 / Flint 2. Historical recorded firmware is GL.iNet 4.11.0 / OpenWrt 21.02-SNAPSHOT; see docs/TESTED-ENVIRONMENT.en.md for exact dated package versions. Current physical installed application version, configuration, vendor hashes, connected profiles, client LAN path, acceleration, SSH access and host VPN/network state were NOT freshly verified here. Alpha2 was not installed on the physical device in this local work.

Historical bounded hardware observations must be read with their own timestamps and limits. Generic x86 refusal/model/protocol-namespace tests do not certify GL.iNet workers, full native hierarchy, inactive-provider startup, actual client DNS/Kill Switch/IPv6, acceleration or hardware flash/power behavior.

## Known limitations and retained failures

- Initial synchronous package harness failed after installation; exact original failing subcommand was not retained, cause unknown.
- Early alpha1 actual UI failures found dependency directive ordering and stale hashed LuCI discovery/controller caches; fixed in later package revisions.
- Alpha1-3 acceptance timed out at RPC scan completion; later independent evidence found the correlated scan completed. Original FAIL retained; duplicate readiness subprocess work removed from status RPC.
- Prior alpha1 actual UI receipt measured all rows at 414x896 despite requesting three sizes. The old distinct-size claim was withdrawn; corrected alpha2 receipt measures all six language/size groups. Old receipts are preserved.
- First actual tmpfs helper failed while filling storage; unbuffered writer retry passed. First FAIL retained.
- Guest clocks were aligned after pause-induced drift. This is virtual-fixture maintenance, not a production NTP fix.
- Exact GL-MT6000/firmware-4.11.0 vendor SDK provenance is missing. Existing interpreted ipk reproducibility is not a matched SDK build.
- Isolated local CI exists; activated server-triggered Gitea CI is not verified.
- Several older state/native docs are historical. Prefer this checkpoint, current code and timestamped receipts; investigate disagreements rather than repeating old readiness claims.
