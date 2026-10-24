# Install with ChatGPT, Codex or Claude

To have an agent install, configure and verify the application, copy the full prompt below into ChatGPT/Codex or Claude Code(Sonnet/Opus) with a local terminal and access to your router. A chat without tools can only explain the steps. Fill in the address and desired outcome; never put passwords/keys in the text.

[Manual installation](INSTALL.en.md) · [Current status](CURRENT-STATUS.md) · [First entry](FIRST-RUN-SETUP.md)

## Copy the complete prompt

```text
Install and verify HomenS.AI Auto VPN on my specific router. Execute the available work yourself, explain results plainly and finish with a verified outcome rather than a plan. Do not ask me to repeat commands you can perform safely.

MY PARAMETERS
Router address/model: [fill in]. Access: [existing SSH/key or secure access request; no secrets here].
Outcome: [install and monitor / install, choose a pair and start Auto]. Default: monitor, Auto off.
Primary VPN: [existing profile or choose together]. Reserve: [a different existing profile or choose together].
Language: English. Do not enable optional Telegram/speed tests without my selection. Backups: private folder outside Git.

SOURCE
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn
Read docs/INSTALL.en.md, CURRENT-STATUS.md, FIRST-RUN-SETUP.md, ROUTER-PREPARATION.md and DISCLAIMER.md. Read scripts before running them.
Release: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases/tag/v0.9.0
Artifact: homensai-auto-vpn_0.9.0-1_all.ipk,769849bytes.
SHA256:7cf93df74cbf72271c93235cdeece7e1e4eaa70fac249bfddeef647af29f287a
Also obtain the matching.ipk.sha256 and release-v0.9.0-verification.json. This is an application, not firmware. Obtain router-test-kit scripts from this same tag, not mutable main. Do not downgrade a newer installed version; report the difference.

VIRTUAL TEST SCOPE ONLY: if the owner explicitly requests the isolated x86/OpenWrt laboratory in lab/openwrt-qemu/README.md and /tmp/HOMENSAI_VIRTUAL_LAB exists, test the package in monitor-only mode with Auto/native off. Preserve the real x86 board identity. Record GL.iNet hardware/firmware preflight gates as unsupported for this VM, not PASS; do not run the GL installation kit past its refusal. After independently checking every non-hardware prerequisite, use ordinary opkg installation in the existing documented monitor-only VM deployment path. Never spoof a board, bypass a native guard, or turn that result into GL.iNet/LAN/Auto certification. This exception does not apply to a real unknown router.
 In that explicitly chosen VM monitor-only scope, check the application's own monitor_only option before upgrading an old release: if absent, set monitor_only=1 with ordinary UCI and verify native_enabled remains0. Do not change network configuration or manufacture hardware readiness.

1. ACCESS AND SCOPE
You need a local terminal and access to the named router. Without tools, explain that a chat cannot install it. Bundle missing address/access questions. Reuse authorized SSH and verify its host key; establish identity for a new/changed key, never disable verification. If SSH is unavailable, offer supported LuCI installation and explain the necessary owner action.
Never request secrets in chat or print/log/commit passwords, VPN keys, tokens or full configuration. Use secure tool input or the owner's own router page. Do not change computer networking/Wi-Fi/adapter addresses/routes, another router, WAN, DHCP or internet-facing management. No flashing, factory reset or unrelated services.

2. READ-ONLY BASELINE
Inspect ubus call system board, /etc/glversion, opkg status homensai-auto-vpn, /overlay space, memory, original feeds and dependencies. Record actual board/model/firmware, installed/running versions, Auto state, selected pair/active channel and any other installer, unfinished transaction/rollback, owned guard or unsaved changes.
Architecture:all and a model selector do not prove compatibility. Current continuous Auto is qualified on a separately prepared GL-MT3000/GL.iNet4.11.0. Current MT6000 continuous mode/arbitrary firmware are not qualified. Never bypass actual platform/readiness refusals.
 Check the configuration filesystem itself (/etc/config, or its mounted overlay), not only free bytes: inspect statvfs/proc mounts and require writable storage. A read-only filesystem can have free space. Stop and diagnose it before settings/package writes; never automatically remount or repair a production filesystem.

3. VERIFIED RECOVERY
Before changes obtain a supported configuration export and needed application settings/history. Encrypt it in a private folder outside Git; protect the key with the OS or a separate secure store. Check archive entries, required files, SHA256 and independent in-memory decrypt/read. Do not persist plaintext secret configuration in the project. Without verified recovery stop installation. A configuration export is not full flash/bootloader recovery.

4. DEPENDENCIES AND ARTIFACT
Check python3,lua,lua-cjson,libuci-lua,ip-full,ubus,rpcd,luci-base,ca-bundle. Install missing dependencies only with ordinary opkg from this firmware's original vendor feeds. No mass opkg upgrade, feed replacement, foreign-release packages or force flags. Check space first; current preflight needs at least20MiB free writable storage. On ABI/signature/dependency conflicts stop dependent writes and explain the cause; do not remove system components to bypass it.
Download IPK/checksum/verification JSON from one HTTPS release. Verify name/size/SHA256 locally and after router transfer. Compare checksum, release evidence and same-tag02-install.sh EXPECTED_SHA/SIZE. Stop on mismatch. Never pipe a downloaded script directly into a shell.

5. INSTALL
For an upgrade issue ordinary Auto Stop and await completed rollback/cleanup; ACK/queued is not completed. Never delete journals/guards or reset attempt budgets to bypass lifecycle checks. Read/run same-tag01-preflight.sh, which writes its report under/tmp. Resolve only permitted failures and rerun. Then use02-install.sh with the verified IPK or documented opkg install /tmp/homensai-auto-vpn_0.9.0-1_all.ipk. Never Flash Firmware; opkg exit0 alone is insufficient.
Run03-verify.sh wait. Verify installed0.9.0-1/live RPC0.9.0, fresh samples, no service errors, one monitor and expected services. Where accessible compare installed file bytes/modes and actually served dashboard/CSS from the selected package with the verified IPK payload. List unperformed checks. Diagnose stale RPC/LuCI cache with the documented procedures rather than claiming success from opkg alone.

6. FIRST ENTRY AND PAIR
Open Services → HomenS.AI Auto VPN, Ctrl+F5. Terms appear only until first acceptance of the current version. I tick the boxes and press Accept myself; never call terms_accept or write terms_version for me. Preserve existing acceptance; skipping the agreement on a later visit is expected.
Next: three-diagram explanation → OK → eight steps: appearance, monitoring, existing VPNs, names/priorities, recovery, speed, Telegram, review. Choose the pair through Settings → All application settings → step3: Existing VPNs. Primary means preferred everyday channel; reserve is a different existing working profile for failure. Show choices before saving. Distinguish saved profile/Connected tunnel/selected traffic route. VPN profiles/keys are created in GL.iNet; never invent them. Without profiles report installed application/pair not configured.
Preserve optional settings without my choice and do not send Telegram tests without my request. You may save authorized reviewed settings with tools; verify with a fresh read, not ACK alone. Save does not accept terms or start Auto. The green escape opens the dashboard with current settings; no draft save, reset or Auto start. Deferral is not completed pair setup.

7. AUTO AND TESTING
Installation and switching readiness differ. Read actual platform preparation and DNS/acceleration/vendor/rollback checks. A model, loaded module or saved flag is not proof. If DNS/acceleration/stock startup needs adjustment, first present exact scope/undo; ordinary installation does not authorize it. Do not disable a working DNS owner based on another router's example or force-unload modules.
If I selected start Auto, the platform is ready and I accepted terms, issue one ordinary Start. Await completed STARTING, confirmed selected channel and fresh DNS+twoHTTPS for both VPNs. Queue acceptance, green controls, interfaces and Connected alone do not prove traffic.
Prepared-MT3000 router-probed-ipv4 mode does not require a continuously running LAN helper. Additional LAN tests measure a real client's route through the router. An agent must run them from an actual device on that LAN; a hosted chat without access is no substitute. Never fabricate confirmation. Switching tests need a specified time/attempt bound, rollback and permission for session interruption; otherwise perform read-only/non-switching checks. Do not change computer networking to bypass binding failures.

8. REPORT
Compare protected settings before/after. Investigate unexpected changes and undo only your own verified edits, preserving newer owner changes. Never flush the whole firewall. Report actual board/firmware, installed/running versions, artifact source/size/hash, dependencies, verified backup/recovery, UI/monitor, pair/active channel, final Auto ON/OFF, changes, unverified areas, page URL and Stop/uninstall/recovery instructions. Separate PASS/FAIL/PARTIAL/BLOCKED/SKIPPED/UNKNOWN. Auto needs explicit Start after restart.
Do not attribute other-version tests to this installation, router probes to LAN proof or short runs to24hours. Do not claim IPv6/currentMT6000continuous-mode/power-cut/unattended acceptance without testing. If blocked, save the precise stopping point and next safe step instead of inventing success.
```

The owner supplies access, personally accepts first-use terms and chooses unresolved preferences. The agent performs the remaining authorized work. Existing terms acceptance is preserved.
