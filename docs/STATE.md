Active 20 October continuation: [recovery TODO](handoff/RECOVERY-TODO-2026-10-20.md) and [checkpoint](handoff/ACTIVE-STATE-2026-10-20.json). All dated state and device claims below are historical.

> **Update 2026-10-17 (evening).** Current application is 0.8.0-alpha7 (see CHANGELOG.md, VERSION.json). Since the review checkpoint below: a first hardware LAN trial was run on the GL-MT6000 with alpha4 (switch to the reserve confirmed from the LAN; return failed because the monitor had too little history; an outside change of VPN rules later closed the LAN until the owner removed the guard by SSH). Fixes: operator return, fresh-check return, release on outside change, private trial number on confirmations, traffic-light status, Help page, simplified navigation. Alpha6 is published on GitHub; alpha7 is local until published. The physical router still runs alpha4 and has not been verified with alpha5-7. The sections below describe the review checkpoint and are otherwise unchanged.

# Project state — stopped Claude review checkpoint, 17 October 2026

Current authoritative handoff: ../.claude/handoff/START-HERE.md and ../.claude/handoff/STATE.md. Root CLAUDE.md imports it for Claude Code.

## Current product

HomenSAI Auto VPN 0.8.0-alpha2-1, dashboard43/ui22, English default with Russian available. Reproducible package: 470221 bytes, SHA256 8de85658c568d3a2610ba545d263a190e218f5d2ba128a01969678087810c2c8. Product/release source 8ab8011e85647ed4179f69d02d9ffe7cb9f62af5. Exact pre-handoff source 1b0768ffb02810679218434b849e4ebe7f4021f4 passed 341 application + 36 QA tests per runtime and 15 JS UI suites; Python 3.9/Lua zero skips, Python 3.11 control seven skips.

## Tests stopped by request

The planned 12-hour virtual monitor run was stopped cooperatively on 2026-10-17T13:26:07Z for independent review. Final state STOPPED, elapsed 3391.75 seconds, 57 observations, zero observed failures/gaps. It is not a completed twelve-hour PASS. Independent cleanup confirmed the marked clone paused; producer/watchdog exited. No new background test or repeated status automation is scheduled. Raw evidence remains private; sanitized final receipt is qa/alpha0802-endurance-stopped.json.

## Evidence and limitations

Virtual alpha2 installation acceptance passed 17 checks. Actual selected-tab LuCI matrix passed 60 transitions at three measured sizes and EN/RU. Disposable tmpfs corruption/ENOSPC tests passed after a retained failed helper attempt. Three controlled opkg lifecycle interruption trials used the previous alpha1-4 baseline, not a physical device. Native browser local-file Print remains unverified; downloaded synthetic HTML/LibreOffice PDF was checked.

Historical recorded target: GL.iNet GL-MT6000/Flint 2, GL.iNet 4.11.0/OpenWrt 21.02-SNAPSHOT. Current physical installation/configuration/acceleration/LAN path is not freshly verified. Alpha2 was not deployed physically in this task. Generic x86/model/protocol-lab success is not actual GL.iNet native cascade or client DNS/Kill Switch/IPv6 proof.

Exact matching vendor SDK and activated server-side Gitea CI remain external prerequisites. Code contains experimental native controls and guards; unattended production is not certified. Read .claude/handoff/ROUTER-READINESS.md before proposing a bounded device test.

## Git workflow

Canonical Windows checkout C:/homensai/homensai-gl-mt6000-auto-vpn, feature/local-completion-alpha6. Save local Git/Gitea first; GitHub gets an identical reviewed tree on the existing public parent. Canonical/public histories and same-named tag mappings differ. Never force, overwrite old tags or push full canonical history publicly.

The fifty-item proposal is preserved for independent audit, not automatically approved implementation: .claude/handoff/TODO-50.md.
