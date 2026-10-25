# Executed prompt recipes — 23 October 2026

The current Help and installation documents contain 76 English/Russian prompt variants: four installation, two LAN-helper, sixteen component-repair and fifty-four diagnostic variants. Their text hashes and recipe mapping are recorded in [the validation matrix](../qa/OWNER-PROMPT-VALIDATION-2026-10-23.json).

The recipes were executed with actual commands in a newly copied, isolated OpenWrt 21.02.7 x86/64 VM (Python 3.9.16), without Docker networking, host mounts, published ports or privileges. Existing stopped observers were not resumed. This is execution of the instructions as test recipes, **not evidence that ChatGPT, Claude, Sonnet or Opus autonomously interpreted each prompt**.

| Recipe | Observed outcome |
|---|---|
| Baseline and recovery | Actual board/packages/settings inspected; supported configuration export encrypted and independently decrypted/read in memory |
| Release installation | Real 0.9.0 IPK size/SHA verified; ordinary opkg upgrade, live RPC version/freshness and verification kit passed; second installation idempotent |
| Hardware refusal | Real x86 identity preserved; GL hardware/firmware preflight correctly refused. Only the separately documented monitor-only VM path was used, Auto off |
| Eight components, EN/RU | Actual availability checks and ordinary matching-vendor package operations passed; configuration storage separately checked writable |
| Missing dependency repair | lua-cjson actually removed, failed require reproduced, original vendor package signature verified against guest ROM keys, ordinary reinstall/module verification and app restoration passed |
| Setup, EN/RU | Actual onboarding RPC save and UCI readback passed with pair deferred; terms unchanged, Auto off, optional messages/speed tests off |
| All diagnostic topics | Actual read-only board/version/freshness/inventory/readiness inspections passed, configuration hashes unchanged. This did not reproduce every possible topic-specific failure |
| Corrupt artifact | Actual package bytes changed in memory; required SHA gate rejected them before opkg |
| LAN helper | Both files fetched from actual guest HTTP and matched source hashes; real PowerShell SelfTest passed without network calls |

Failed attempts were preserved privately: a missing legacy monitor-only option, read-only VM root despite free capacity, and test-harness mistakes. The lab direct-kernel boot now explicitly requests writable storage. Readiness and prompts independently check writability; they do not automatically remount a production router. This does not resolve the older GRUB warm-reboot issue.

The complete requested acceptance is **PARTIAL**. There is no physical Windows LAN client connected to this VM, no qualified GL.iNet hardware/native Auto switch, no real VPN credentials or Telegram delivery test, and no 24-hour/IPv6/power-loss proof. LAN switching is not claimed. No browser was available through the configured UI tool, so native dropdown clipping, visual layout and actual clipboard interaction remain unverified; DOM/logic tests are separate evidence. These limits cannot be turned into PASS by simulating board identity or network success.

Prompts instruct an agent to report these missing capabilities and stop at the appropriate boundary. Before shipping a claim of complete hardware/client installation, repeat the relevant recipes on the actual supported device/client with verified recovery and the owner's chosen scope.

The final alpha2 candidate also passed exact-source dual-runtime CI (737 application/107 QA per runtime, 44 UI suites), actual ordinary VM installation, 86 installed file/mode comparisons and guest HTTP asset equality. [Candidate evidence](../qa/OWNER-UI-ALPHA2-2026-10-23.json). An initial 10-second verification RPC deadline timed out under emulation; a measured fresh response took 10.09 seconds. Read-only verification with a 45-second transport deadline then passed. The failed attempt remains retained; production safety gates were not changed. Real-file synthetic history tests verified 130 events across pages, seven-day expiry, day-history restart (80,931 bytes) and an optional history-write fault without losing accounting checkpoints. These synthetic timestamps do not mean seven actual days elapsed.
