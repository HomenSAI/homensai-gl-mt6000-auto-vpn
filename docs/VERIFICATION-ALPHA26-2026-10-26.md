<!-- doc-role: versioned-evidence -->
# Minimum UI alpha26 revision 2 — published design prerelease

The owner started revision 3 on 26 October 2026. Coordinator and three fixed agents worked in a separate feature branch with explicit file ownership. Baseline planning commit: `554236d`; prior product: alpha25. The previous uncommitted plans/mockups were archived and read back before implementation.

Final candidate: `0.9.1-alpha26-2`, selected `dashboard102` / `ui74.css`. Tested source: `e2d67b38b235a42b55fa536a4c99cd443a1d59c1`. Package: 866573 bytes, SHA256 `84c9c58f79915681163c8c0fab3f56a976f902dcdfcd0bf3c866a308abadb2d8`. See [machine-readable verification](../qa/MINIMUM-UI-ALPHA26-2026-10-26.json). Evidence/documentation commits may follow this tested source only with unchanged product files/fingerprint.

## Verified development evidence

- Independent frozen Node UI batch: 60/60 PASS before version pinning. Subsequent tests added behavior checks and must be included in final committed CI.
- Stale-Start regression found and fixed: an old OFF screen cannot issue Start after evidence expiry. The actual Auto handler rechecks freshness. Pending Start can be cancelled through the same real Stop element without waiting for redraw.
- Native Chromium runs the complete generated module with synthetic RPC fixtures, no router or external network. Sixteen viewport/language/theme cases passed: 320/375/768/1366 px × EN/RU × light/dark; 19 navigation/visibility/control checks per case. These are browser fixtures, not actual-device acceptance.
- Earlier failed attempts retained: two browser-harness errors (counting a noncommand profile link as Auto control; incorrect fixture call-counter name), and a Chromium window-size limitation corrected using its native headless shell. Failed results were not silently replaced.
- Host Windows Python cannot run Linux `fcntl` application tests. Windows exploratory failures are retained; canonical application/QA evidence must come from the pinned Linux environments.

## Final release-gate evidence

- Exact-source CI: Python 3.11.2 and 3.9.15, 778 application / 112 QA tests in each, 60 UI suites in the primary environment; complementary skips are explicit in the JSON. Both packages have the SHA256 above.
- Actual Chromium canonical-payload matrix: 26 groups × 41 checks = 1066 checks PASS; 320/375/768/1366 px, EN/RU, light/dark, screenshots of every main section. Explicit scan produces one scan request, stays pending until measurement completion and never starts Auto/speed/fault actions.
- Actual disposable x86 OpenWrt: ordinary opkg update through alpha25, preliminary alpha26-1 and final alpha26-2; protected network/firewall/DHCP configurations and terms unchanged, synthetic persistence marker retained, Auto off. Final runtime: 87 immutable files/modes, fresh RPC/inventory and exact HTTP-served module/CSS bytes. The x86 identity was not spoofed.
- Install-kit ZIP read back and compared with canonical scripts/package. Version/documentation/privacy audits must remain PASS at publication.
- Additional real integration finding fixed: the monitor summary shared a CSS class with the scan control; selection now uses the actual action. Independent regression retains the prior-selector FAIL and fixed PASS. Final package revision 2 permits normal upgrade without force-reinstall.

Publication is a separate recorded action with remote tag/asset downloads. Physical MT3000 installation/browser acceptance, external LAN/exit/DNS fault proof, power-loss acceptance and 24-hour soak were NOT performed. This design prerelease is not an operational/stable certification; main/stable and physical router state are outside this delivery.

## Inventory and retained behavior

Old overview → Minimum; channels → selected pair/details; tests/readiness/services → Diagnostics subviews; statistics/traffic → Events subviews; learn → Help/training; initial setup → Settings/setup. One source of Auto command authority. Technical observations, manual channel selection, retained events, speed quotas, statistics exports, validated settings editors and optional training remain reachable. Experimental fault injection is removed from normal operator navigation and retained in test tooling.

Private run evidence: `private/minimum-ui-20261026/`. It contains run deadline/checkpoints, original WIP archive, per-attempt QA/browser logs, model-only and native-browser scope, VM identity and final delivery receipt when completed. Private files are not release assets.

## Publication readback

Published GitHub/Gitea prereleases, six assets each, all SHA256 checked after publication. Canonical tag commit `7e958ed83e90bcf917409c6a933519c86b2b8603`, GitHub tag commit `4693aae997b2f370cc7affbdc270ddfb8382fe72`, identical tree `51d410661cd453d939c59e41f7214f3a8f62fd9b`. Main refs and GitHub stable latest preserved. Temporary Gitea authentication revoked. Independent evidence-readiness review passed 18 cross-checks; publication proof is the separate coordinator readback. Both own QEMU VMs were shut down. Source ZIP restored and verified against all 1200 Git blob identities; the failed Windows-EOL archive attempt remains private and is not the verified archive.
