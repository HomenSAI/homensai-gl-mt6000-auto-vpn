# Virtual OpenWrt acceptance — 2026-10-16

Scope: an actual OpenWrt x86/64 guest kernel running under QEMU TCG inside the isolated `homensai-vpn-qemu` Docker container. No physical GL-MT6000 connection or modification occurred in this work window.

## Environment

- OpenWrt 21.02.7 r16847-f8282da11e, x86/64; kernel 5.4.238; Python 3.9.16.
- QEMU 7.2.22, Debian bookworm, TCG; 256 MiB guest RAM, one emulated CPU. Container limited to 1 GiB / two CPUs.
- Official combined ext4 image SHA256: `39f8e1f629cfe1db985809639c2cd1de88db119544144740d968d0b6784a9d6f`.
- Sources: [official image index](https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/), [OpenWrt QEMU guide](https://openwrt.org/docs/guide-user/virtualization/qemu).
- No privileged container, host networking, TAP, physical-interface bridge or published host ports. Internal QEMU user networks provide LAN management and outbound package downloads.

## Confirmed results

| Check | Result | Boundary |
|---|---|---|
| Official image checksum and actual guest boot | PASS | Generic x86 OpenWrt, not GL.iNet firmware |
| IPK installation and Python preflight | PASS | Package interpreter compatibility |
| Actual RPC object and typed methods | PASS | Wait for asynchronous rpcd readiness |
| Actual isolated UCI writer self-check | PASS | Synthetic temporary configuration |
| 14 UCI/RPC/procd integration checks | PASS | See openwrt-vm-acceptance.json |
| alpha1 → alpha2 update preserves own configuration marker | PASS | Guest-only fixture |
| Start/stop monitor via RPC and actual procd state | PASS | Does not enable native Auto |
| Fresh measurement after monitor start | PASS | Inactive synthetic profiles; actual WAN counters |
| Own monitor SIGKILL / procd replacement / fresh measurements | PASS | 23.45 seconds on guest clock; not an Internet recovery measurement |
| Network/firewall configuration and main IPv4 route unchanged | PASS | Integration and monitor-crash scenarios |
| Python regression suite in OpenWrt | PASS, 169 tests | Final compact-package guest run, including monitor-journal regression |
| Debian local regression suite | PASS, 169 tests | Includes 256 hierarchy combinations inside a parameterized test |
| Auto UI / Telegram wizard / traffic UI regressions | PASS | Mock DOM/RPC |
| Browser EN → RU → reload → EN | PASS | Clearly labelled synthetic local dashboard, not actual LuCI form acceptance |
| Mobile width 390 px | PASS for checked Overview | Document width 375, viewport 390; not every section |
| Legacy disk/GRUB warm reboot | UNCONFIRMED | Timed out; QMP screen remained at kernel decompression, before application start |

The warm-reboot failure is retained. A preserved-disk cold start restored the test configuration and application. Direct loading of the matching checksum-verified official kernel was also tried; its warm reboot likewise failed to return management within 180 host seconds and showed the kernel-decompression stage. Both results are retained in separate JSON reports. No causal claim is made from the `Wrong EFI loader signature` text alone.

## Defects found and corrections

1. Test setup called `time.tzset()` directly, absent from this OpenWrt Python build. The initial guest run reported ten setup errors and skipped the test class dependent on that setup. Added `timezone_compat.refresh_timezone()` using the existing libc fallback and reused it in the agent/tests. The subsequent 165-test guest run passed.
2. A first transfer copied `router` into an already-existing `router-source`, producing a stale nested directory. Corrected the source transfer to copy directory contents and excluded nested copies/pycache. The stale run is not counted as verification of the fix.
3. Long serial commands exceeded BusyBox interactive input limits; the test itself completed, but the final marker was truncated. Updated the helper to write short safely quoted chunks to a private temporary script. Minimal BusyBox lacked base64, so no base64 dependency remains. The 14-check result was verified by reading the generated JSON separately.
4. Initial QEMU management forwarding used a different user-network subnet from the guest LAN. Aligned the isolated management subnet; SSH inside the container then worked. No Windows route was changed.
5. Immediate post-restart RPC queries returned Not found before asynchronous registration. The external-exec mechanism is built into this rpcd; attempting `rpcd-mod-exec` proved that package does not exist in this release. No new runtime dependency was added. Acceptance waits for the actual object.
6. Fresh installation lacked a dedicated monitor lifecycle action. Added authenticated `monitor_control`, restricted to the application's UCI option and init script. Active native transactions/on intent prevent monitor shutdown. An accepted request is explicitly not proof of a running service; integration checks query procd and fresh status.
7. Browser screenshot showed a missing font glyph for the power button. Replaced the character with a CSS-drawn symbol.
8. Builder collected retired dashboard/CSS versions, including local untracked generated files. Restricted packaged UI to the current dashboard25/ui13, preserving history in Git and adding a package regression. Final local IPK: 414714 bytes, SHA256 `976a44f3f4dfab0cb75083b39de0257c71424b19a6a439e6230f1e5f31e6e789`.

## Not certified

No GL.iNet proprietary workers, real VPN sessions, cross-protocol native switching, native executor crash recovery, IPv6 leak protection, hardware acceleration, flash/power-loss behavior or Telegram delivery is certified by this VM. Native Start correctly refuses the unsupported board/vendor environment. Do not bypass those guards to manufacture a passing result.

9. Cross-runtime comparison initially differed despite matching contents/size: Python 3.11 exposed zlib's gzip OS byte while Python 3.9 used 255. Normalized every nested gzip header's OS byte to 255. The rebuilt Debian package matched the independently generated OpenWrt package SHA256 before the final monitor-journal hardening. Reproducibility across arbitrary zlib versions is not guaranteed by this result.
10. Monitor shutdown could encounter a corrupt journal without a structured refusal. Added MONITOR-JOURNAL-UNVERIFIED and refusal for unknown/non-terminal journal phases, retained reserve or closed guard. Added a regression proving no writer/service invocation in that case.


Final verification after journal hardening: 169 Python tests passed in OpenWrt (28.415 guest-reported seconds) and 169 passed in Debian. Both independently built the same 414714-byte IPK with SHA256 `976a44f3f4dfab0cb75083b39de0257c71424b19a6a439e6230f1e5f31e6e789`. All three Node UI suites passed. Guest reinstall retained the own configuration marker; expected opkg conffile-preservation notices and early readiness warnings are retained in the private run transcript rather than treated as failed assertions.
