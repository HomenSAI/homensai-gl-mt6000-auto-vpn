# GL-MT3000 mobile test target: staged acceptance plan

Prepared 20 October 2026. The owner selected the mobile **GL-MT3000 (Beryl AX)** for physical trials and explicitly confirmed that it is **not yet connected**. All device rows below are **BLOCKED: actual observations missing**. This document records a future procedure; no hardware action has been executed by preparing it.

The original **GL-MT6000 remains untouched**: no package deployment, configuration edits, VPN switching, fault injection, reboot or upstream interruption on that router. Keep the owner's ordinary Internet connection and its management path available throughout the separate test.

## 1. Establish the test device and management path

When the owner connects the GL-MT3000, first identify the physical unit from its label and the device reached through its own LAN management connection. Record any initial setup changes separately; account creation, enabling SSH and setting passwords are writes and are outside the read-only inventory step. Do not assume an address from documentation or connect using the primary router's management address.

Use an isolated test LAN, with a deliberate upstream connection for later tests. Check subnet overlap and the PC's selected interface before reaching either management UI. Keep the PC's work/primary route unchanged. Prefer a separate LAN witness device so changing its test route cannot disconnect the operator. Record the actual management address privately; do not add addresses, credentials, SSIDs, serial numbers or raw configuration to Git.

Prerequisite evidence: physical model, actual board identity, current firmware, test-LAN topology, management access independent of the VPN being tested, and a named operator able to restore the test setup. If any identity or route is ambiguous, stop before package or VPN changes.

## 2. Read-only inventory, then local classification

Use only the prepared [00-platform-probe.sh](../router-test-kit/00-platform-probe.sh) for this step. After deliberately selecting the test device, its stdout can be captured privately on the PC. For an already available, verified SSH connection, stream the script through standard input so that the probe creates no router files; use the SSH tool's normal credentials handling and capture output on the PC. Do not put credentials into a command line or disable host-key verification.

If the reviewed script has already been transferred to the test device, its execution is:

```sh
sh 00-platform-probe.sh
```

The script itself is read-only and stdout-only. Shell redirection to a path on the router would create a file; keep the private report on the PC instead. Installation of dependencies is never part of this probe.

Classify the saved report locally:

```text
python scripts/classify-platform.py PRIVATE_PLATFORM.tsv
```

The report must include all 41 allowlisted observations: board/model, GL.iNet firmware string, OpenWrt version and target, kernel/architecture, package manager and package architectures, Python/Lua/nft versions, tools and installed dependencies, overlay space and memory, bootloader/recovery placeholders, vendor-script hashes and refusal markers. Keep both report and classifier result private. A missing or contradictory prerequisite returns BLOCKED or rejects the report format.

The conservative candidate checks expect `glinet,gl-mt3000`, `mediatek/filogic` and `aarch64`; these expectations are not observations of the owner's device. A different vendor target string or model spelling requires review, never editing the report to obtain a candidate result. `MONITOR-CANDIDATE-REVIEW` means the reported prerequisites can be reviewed further. Both outcomes keep installation unauthorized, bootloader and recovery backup unverified, and native switching refused. SHA256 observations establish the bytes seen, not vendor-adapter certification.

## 3. Firmware, bootloader and recoverable backup gate

Before any package write, collect and review the following evidence for the actual unit:

| Prerequisite | Required evidence | Current status |
| --- | --- | --- |
| Firmware provenance | Observed GL.iNet version/build and OpenWrt family, matching official model download entry, package manager, architecture and dependency compatibility. Save the exact official recovery image and its vendor checksum where available; otherwise record provenance and locally computed SHA256 without calling it vendor-verified. | BLOCKED |
| Bootloader | Exact version and evidence source, where available through a non-destructive information view or an existing boot log. A partition named U-Boot does not establish its version. If unavailable, retain UNKNOWN and obtain a model/firmware-specific recovery assessment before installation. | BLOCKED |
| Private device backup | A supported configuration export, application state/configuration where present, installed-package inventory and actual firmware identity, copied off the router to private PC/D: storage. Store sensitive VPN material separately from public source. Record filenames, sizes and SHA256 without printing secret contents. | BLOCKED |
| Recovery completeness | Verify archive integrity and required entries; document what the export does and does not restore, including credentials, certificates, packages and device-specific data. A configuration export and the project's Git bundle are not full flash or bootloader backups. | BLOCKED |
| Recovery procedure | A reviewed procedure for this exact model/firmware, the correct recovery image, required local cables/access and a way to restore management without the application or test VPN. Demonstrate package/configuration rollback after a future allowed monitor installation; firmware-flash recovery remains separately untested. | BLOCKED |

Do not read/write raw flash, upgrade firmware/bootloader, factory-reset, enter recovery mode or power-cycle merely to fill an evidence field. Consult the official recovery instructions as preparation; executing destructive recovery needs a separate concrete decision. Unknown bootloader/recovery evidence cannot be waived by a green offline test.

## 4. Decide and prepare a separate monitor-only installation

The existing [01-preflight.sh](../router-test-kit/01-preflight.sh) is pinned to **GL-MT6000 / GL.iNet 4.11.0**. The existing [02-install.sh](../router-test-kit/02-install.sh) belongs to that kit and pins its historical package version, size and SHA256. **Do not run these steps on GL-MT3000, reuse their readiness result, or bypass their guards.** `Architecture: all` on an IPK does not prove device compatibility.

After the preceding evidence exists, prepare a separate MT3000 monitor-only procedure against the exact committed source and reproducible package SHA256. Review its package scripts, actual opkg/apk family, dependency availability, storage requirements, LuCI/rpcd integration and rollback before installation. Resolve unsupported firmware/package combinations explicitly; do not force installation or modify board/hash exceptions.

Monitor acceptance requires Auto/native switching disabled before and after install, no owned active fault/guard transaction, management reachable, current package identity and UI assets verified, and independent LAN baseline unchanged. Record actual CPU/memory use and bounded resource observations. If package/configuration rollback cannot be demonstrated safely, stop here. No native GL-MT3000 adapter is certified by this plan.

## 5. Establish the independent LAN witness

Before each trial, record a baseline on a client behind the test GL-MT3000: fresh DNS lookup, fresh HTTPS request with certificate validation, observed exit/path for each available address family, and management reachability from the operator. Define expected exit/path and intentional policy exceptions privately. Record UTC timestamps plus monotonic elapsed time, run ID, source/package SHA256, test policy and the agreed Stop/rollback deadlines before injecting a fault.

The witness must actually traverse the selected test router; verify it has no alternate Wi-Fi, mobile, proxy or other route masking failure. A successful router-local probe, cached DNS answer, dashboard status or already-open connection cannot certify the LAN path. Use bounded requests and independent controlled endpoints. A witness failure means UNKNOWN/BLOCKED for connectivity acceptance and triggers the planned recovery path, not an assumed successful switch.

## 6. Controlled matrix after the applicable gates pass

First collect monitor-only observations during deliberate vendor-UI changes, without granting application switching rights. Automatic switching rows stay BLOCKED until a separately verified MT3000 adapter/firmware profile exists, with worker arbitration, route-generation checks and independent rollback established. Preserve MT6000 guards and existing native refusal meanwhile.

Every row starts from a known baseline, affects only test profiles/traffic, has a finite duration and independent cleanup, and ends with DNS/HTTPS/exit plus management and protected-configuration verification. Agree numeric timing limits before the run; do not invent achieved timings. Restore the baseline between rows rather than combining faults accidentally.

| Trial | Controlled condition | Required observation and recovery |
| --- | --- | --- |
| Primary healthy | Primary and reserve are independently verified before use. | Stable primary LAN DNS/HTTPS/exit; reserve probing does not transfer client traffic or alter the main route. |
| Primary failed | Fail only the selected primary path; keep reserve and management available. | Failure classified correctly; healthy reserve confirmed by witness after any separately authorized switch. Remove fault and verify the agreed primary-return policy. |
| Reserve failed | Fail reserve while primary remains healthy. | Client stays on primary; unusable reserve is not selected. Remove fault and revalidate reserve independently. |
| Both failed | Bound simultaneous failure to the test profiles. | Explicit degraded/blocked state and agreed leak policy; no false success or unintended direct fallback. Restore one path, then both, and verify witness recovery. |
| Flapping / stable return | Alternate bounded primary failures/recovery near the planned thresholds. | Cooldown, minimum dwell, sample freshness and stable-primary criteria prevent oscillation; no stale request or unbounded retry. |
| Stop | Request Stop during each reachable test phase, including pending recovery. | Measure acknowledgement and effective cancellation separately; no later switch from stale work. Pending guard release remains visible until cleanup is verified. |
| Full-block expiry | Use an explicitly bounded owned test fault with an independent cleanup deadline. | Actual nft timeout and independent cleanup remove only the owned fault; verify LAN/management even when the dashboard is unavailable. |
| Process crash / restart | Terminate only the test application's reviewed worker, at a selected recoverable phase. | Durable recovery, stale-generation refusal and bounded owned-rule cleanup survive worker loss; recovery does not depend on its UI. No device reboot or power cut is implied. |
| DNS-only failure | Fail only the chosen DNS test path; keep direct HTTPS control reachable. | DNS failure remains distinct from general Internet/VPN failure; reserve DNS is independently checked and no disallowed resolver leak occurs. |
| IPv6 | Exercise an actually available IPv6 path alongside IPv4, or document its absence. | Fresh IPv6 DNS/HTTPS/exit and route evidence; no direct IPv6 escape during VPN failure. No IPv6 service means SKIPPED/BLOCKED for IPv6 acceptance. |
| Kill Switch | Test the observed vendor policy in its agreed enabled/disabled states on the test router. | Intended non-VPN blocking and management exceptions hold; application cleanup preserves vendor policy and does not silently open direct traffic. |
| Special rules | Exercise identified split-tunnel, domain/device routing, LAN access and other configured exceptions one at a time. | Each client flow follows its declared rule; unrelated clients and management remain unaffected. Restore rules and verify baseline fingerprints. |

This matrix does not authorize hardware power cuts, flash interruption, reboot loops or unattended endurance runs. Those require a separate bounded plan. Manual vendor switching can establish monitor observations; it cannot close the automatic-native-switch acceptance rows.

## 7. Independent rollback and completion record

For each trial, prepare a local recovery control that does not depend on the application, VPN route, dashboard or worker under test. It must remove only that trial's owned fault and restore its known test baseline at the agreed deadline. Validate cleanup independently before the first disruptive row. Do not use broad firewall flushes, reset vendor configuration or change the primary router to recover the test.

Abort the current row if management fails, the witness route is uncertain, an unexpected direct exit appears, state ownership/generation changes, a journal is malformed, or cleanup misses its agreed deadline. Stop further injections, preserve private evidence, use the prevalidated local rollback, and verify DNS/HTTPS/exit, rules, routes, management and package/configuration state before resuming. Failed cleanup remains FAIL/BLOCKED even if Internet later returns.

Record each row as PASS, FAIL, BLOCKED, SKIPPED or UNKNOWN with actual timestamps, duration, package/source identity, witness evidence and before/after state. Keep raw logs, packet captures, configuration exports and device backups private on PC/D:; only reviewed redacted conclusions enter Git/public artifacts. Complete physical acceptance only for rows actually executed on this identified device. Offline/VM results and other-device history remain separate.

## Official references checked during preparation

- [GL.iNet Beryl AX user guide](https://docs.gl-inet.com/router/en/4/user_guide/gl-mt3000/) identifies the model and describes local setup; it does not identify the owner's installed firmware.
- [GL-MT3000 official downloads](https://dl.gl-inet.com/router/mt3000/stable) and [GL.iNet firmware families](https://www.gl-inet.com/en-us/pages/firmware-versions) support review of the observed firmware, not an assumed upgrade.
- [GL.iNet recovery guidance](https://docs.gl-inet.com/router/en/4/faq/debrick/) is a reference for a model-specific recovery assessment, not an instruction to flash now.
- [OpenWrt GL-MT3000 hardware entry](https://openwrt.org/toh/hwdata/gl.inet/gl.inet_gl-mt3000) and [Filogic target source](https://git.openwrt.org/openwrt/openwrt/tree/target/linux/mediatek/filogic/target.mk) support the conservative mediatek/filogic and aarch64 expectations; stock-vendor behavior and the actual device still require observation.
