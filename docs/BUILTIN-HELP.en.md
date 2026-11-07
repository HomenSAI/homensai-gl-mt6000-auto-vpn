<!-- doc-role: current-generated-help -->
# Built-in Help: topics and diagnostic prompts

Generated from runtime topics, including readiness recipes, setup guide and diagnostic prompts. / Сформировано из тем приложения, рецептов готовности, помощи мастера и промптов.

[Current state](CURRENT-STATUS.md) · [Installation prompt](AI-INSTALL.en.md) · [Training](TRAINING.en.md)

<a id="ai-prompt"></a>
## Prompt for your AI agent

You would rather let an AI agent install, check and configure everything for you.

[Full installation prompt](AI-INSTALL.en.md)

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Prompt for your AI agent.
You would rather let an AI agent install, check and configure everything for you.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="install-guide"></a>
## Install, upgrade, roll back or remove: step-by-step guide

You want to install the program, upgrade it, go back to the previous version or remove it yourself, with commands you can copy. Reading it changes nothing.

### Before you start

HomenS.AI Auto VPN is an application for a GL.iNet router. It watches two VPN connections that are already set up on the router and, only after you switch Auto on, moves traffic to the reserve when the primary fails. The `.ipk` file is an application package, not router firmware.

There are two ways. Do it yourself with the numbered steps below, or let an AI agent with a terminal on your computer (Codex, Claude Code) do the steps for you: the last section and the Help topic «Prompt for your AI agent» contain a ready prompt with strict safety rules.

In the commands replace `ROUTER_ADDRESS` with the address you use to open your router admin page, and `VERSION` with the exact version from the release, for example the file name `homensai-auto-vpn_VERSION_all.ipk` becomes the real file name you downloaded. Sections 3 and 4 and the `scp` copy run on your computer (PowerShell on Windows, Terminal on macOS or Linux); all other commands run on the router after `ssh root@ROUTER_ADDRESS` has connected.

### 1. What you need

1. A supported router. Continuous Auto is documented for the GL.iNet GL-MT3000 (Beryl AX) with GL.iNet firmware 4.11.0. On the GL-MT6000 (Flint 2) with 4.11.0 the program installs and monitors, but continuous Auto there is not accepted yet. Other models and firmware are not supported; the package architecture `all` does not make them supported.

2. Two VPN connections already set up in the GL.iNet admin panel → VPN (WireGuard or OpenVPN clients): a primary and a reserve. They must be two different clients; two servers inside one client are not two channels. Monitoring works without them; Auto needs both.

3. At least 20 MiB of free writable flash on the router. About 8 MB of it keeps a verified copy of the installed program for self-repair and for the automatic rollback of a damaged upgrade.

4. Internet on the router, if missing dependencies must be installed from the firmware package lists.

5. A computer with an SSH client: Windows 10/11 (built-in OpenSSH, PowerShell), macOS or Linux (Terminal). Without SSH there is a LuCI upload path with fewer checks (section 6).

6. The router administrator (root) password. You type it yourself only into the hidden password prompt of the terminal or browser, never into a chat or a document.

7. About 30 minutes and a second way into the router while you work, for example a network cable.

### 2. What is checked and what is refused

`01-preflight.sh` only reads: router model, firmware, dependencies, free and writable storage, the program's own state (Auto off, no unsaved changes, no unfinished switch, no own protection table). It saves a fingerprint of the network, firewall and main routes so that the result can be compared later. It writes only into `/tmp/homensai-kit`.

`02-install.sh` refuses when the size or sha256 differs, when the signature or the release chain is wrong, when Auto is on, when the program's own protection table is still present, when the program has unsaved settings changes, or when preflight was not run. It never uses force flags.

The package itself refuses to install or upgrade while Auto runs or a recovery is unfinished (`LIFECYCLE-…` codes). On a board other than GL-MT3000 or GL-MT6000 it does not start its services (`MONITOR-ONLY-DEPLOYMENT`). After installation it checks its own files; damaged files block Auto and, on an upgrade, trigger the automatic rollback described in section 9.

In the program, Start of Auto is refused unless the detected model and firmware are supported, the terms are accepted by you, the router preparation checks pass and two channels are chosen. Choosing a model by hand never bypasses these checks.

### 3. Download and verify the package

1. Open the releases page https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/releases and choose one version. «Pre-release» means a test build. Read its notes: what was verified on a router and what was not.

2. From the same release download: the package `homensai-auto-vpn_VERSION_all.ipk`, its `.sha256` file, and, if the release has them, `homensai-auto-vpn_VERSION_all.ipk.sig` and `CHAIN.jsonl`. Also download «Source code (tar.gz)» of the same release: its `router-test-kit` folder holds the install scripts. Never mix files from different versions.

3. Compute the checksum on Windows (PowerShell, in the download folder):

   ```text
   Get-FileHash .\homensai-auto-vpn_VERSION_all.ipk -Algorithm SHA256
   ```

4. On Linux:

   ```text
   sha256sum homensai-auto-vpn_VERSION_all.ipk
   ```

5. On macOS:

   ```text
   shasum -a 256 homensai-auto-vpn_VERSION_all.ipk
   ```

6. The 64-character value must equal the value in the `.sha256` file and in the release notes (PowerShell prints capital letters; that does not matter). Compare the file size too when the notes give it. On any difference delete the file, download it again and do not install it.

7. Signed releases carry `.ipk.sig` and `CHAIN.jsonl`. The router checks both with its own `usign` in section 5 before anything is changed. On a first installation the script trusts the release keys inside the kit, so compare their full fingerprints with the release page. Published fingerprints (03.11.2026): main key `701cdf098a0f849f` → `af551e8dadc9a871670704f85db928788d173773a5770de225098de33d094add`; reserve key `a1c06016584475fa` → `cb110c9917360178de0b0d98d9763c904c80f4417234674214700ff6b58fd0e7`. To compute one from the unpacked source archive (Linux, macOS or Git Bash):

   ```text
   sed -n 2p router/files/etc/homensai-vpn/keys/701cdf098a0f849f | tr -d '\r\n' | sha256sum
   ```

8. Releases published before signing have no `.sig`. Then only the checksum protects the package and the install script needs `--allow-unsigned`. Use that option only for such a release, never to skip a failed check.

### 4. Make a backup

1. Windows (the `cmd /c` wrapper keeps the binary archive intact):

   ```text
   cmd /c "ssh root@ROUTER_ADDRESS sysupgrade -b - > router-backup.tar.gz"
   ```

2. Linux or macOS:

   ```text
   ssh root@ROUTER_ADDRESS 'sysupgrade -b -' > router-backup.tar.gz
   ```

3. Check that the archive opens; the list must show files such as `etc/config/network`:

   ```text
   tar -tzf router-backup.tar.gz
   ```

4. Without SSH: LuCI → System → Backup / Flash Firmware → «Generate archive». Use only the backup button on that page, never its firmware flashing part.

5. `sysupgrade -b` only exports settings; it never flashes. The archive contains passwords and VPN keys: keep it encrypted and private, never in Git, a chat or a public folder.

### 5. Install over SSH (recommended)

1. Connect. At the first connection compare the host key with trusted router information before accepting it; type the password only into the hidden prompt. If a saved key changed, stop and find out why (Help topic «How to connect by SSH»).

   ```text
   ssh root@ROUTER_ADDRESS
   ```

2. On the router, make sure it is the intended router (read-only). `board_name` `glinet,mt3000-snand` means GL-MT3000, `glinet,gl-mt6000` means GL-MT6000; the second command prints the firmware, the third the installed version of the program (nothing for a first installation).

   ```text
   ubus call system board; cat /etc/glversion; opkg status homensai-auto-vpn | grep Version
   ```

3. On your computer, in the folder with the downloads and the unpacked source archive, copy the files into `/tmp` of the router. Leave out `.sig` and `CHAIN.jsonl` if the release has none. If `scp` reports that `sftp-server` is missing, add `-O` right after `scp`. `/tmp` lives in memory and is cleared by a reboot.

   ```text
   scp homensai-auto-vpn_VERSION_all.ipk homensai-auto-vpn_VERSION_all.ipk.sig CHAIN.jsonl router-test-kit/01-preflight.sh router-test-kit/02-install.sh router-test-kit/03-verify.sh router-test-kit/04-uninstall.sh root@ROUTER_ADDRESS:/tmp/
   ```

4. On the router, check the checksum of the copied package again; it must equal the value from section 3.

   ```text
   sha256sum /tmp/homensai-auto-vpn_VERSION_all.ipk
   ```

5. On the router, run the read-only preflight. It ends with `READY to continue` or `NOT READY, fix FAIL lines`.

   ```text
   sh /tmp/01-preflight.sh
   ```

6. If only `dependency … missing` lines fail, refresh the package lists of the firmware's own feeds and install exactly the missing names (the example name is a placeholder). Do not run `opkg upgrade`, do not add other feeds. Then run preflight again. For any other FAIL line see section 12 and do not continue.

   ```text
   opkg update && opkg install lua-cjson
   ```

7. Install. The script checks size, sha256, signature and release chain, makes sure Auto is off, then runs the normal `opkg install` without force flags. For a release published before signing append ` --allow-unsigned`.

   ```text
   sh /tmp/02-install.sh /tmp/homensai-auto-vpn_VERSION_all.ipk
   ```

8. Verify. `wait` gives the monitor up to 90 s for the first sample. Every line should be PASS. An exit code 0 of opkg alone does not prove success.

   ```text
   sh /tmp/03-verify.sh wait
   ```

9. If verification says that `ubus homensai-vpn status` is unavailable, reload the RPC service, then log out of LuCI and log in again.

   ```text
   /etc/init.d/rpcd reload
   ```

### 6. Install through the LuCI page (without SSH)

1. Verify the checksum on your computer first (section 3). This path runs neither the preflight nor the signature check; only the package's own install guards run. Prefer SSH when you can.

2. Open the GL.iNet admin panel → System → Advanced Settings and go to LuCI.

3. LuCI → System → Software: press «Update lists…». It downloads the package lists of the firmware's own feeds and installs nothing; it is needed for dependencies.

4. Press «Upload Package…», choose the `.ipk`, upload it, check the name and version in the dialog and press «Install». Do not tick overwrite or force options. Never load the `.ipk` in «Flash new firmware image»: it is not firmware.

5. Read the output. If it shows an error or a code (`LIFECYCLE-…`, `MONITOR-ONLY-DEPLOYMENT`, a missing dependency), stop and look it up in section 12.

6. Open Services → HomenS.AI Auto VPN and press Ctrl+F5. If the page is empty or old, see the Help topic «The page is old, empty or says the monitor is not running».

### 7. First start: wizard and terms

1. Open LuCI → Services → HomenS.AI Auto VPN and press Ctrl+F5 (Cmd+Shift+R on macOS) so the browser loads the new page.

2. The four-step wizard opens: Router (the detected model and readiness lamps; the model cannot be chosen by hand) → Channels (primary and reserve: two different VPN clients from GL.iNet → VPN) → Behaviour (how fast to switch, router load, optional Telegram) → Terms and start.

3. On the last step press «Save without starting» (Auto stays off) or «Accept terms and turn Auto on» («Turn Auto on» when the terms are already accepted). Only you read and accept the terms; no script, helper or AI agent may accept them for you. Acceptance of the same terms version is remembered on the router.

4. Every step has «Skip — open the interface». Skipping never starts Auto and never accepts the terms.

5. Later the pair is changed in Settings → Channels: primary and reserve (Console view: the Channels tab).

### 8. What runs after installation

Monitoring starts at once and always runs: it checks both channels and keeps the history, traffic and response figures. It cannot be turned off (`MONITOR-ALWAYS-ON`); a page that says monitoring is not running shows an error: press «Restore monitoring», and if it does not come back, reinstall the package.

Auto is off until you start it with its switch or the wizard button, and only when the readiness checks pass. Saving settings never starts Auto.

While Auto runs, a failed primary leads to a switch only after the reserve passes its checks; the return follows the rule you chose. A switch can interrupt open connections. Auto changes only the routing order of the two chosen VPN channels and its own protection table; it does not edit Wi-Fi, DHCP, WAN or the VPN profiles.

Auto that you started comes back by itself after a reboot or a power cut, with all its start checks. Stop cancels that.

### 9. Upgrade to a newer version

1. Read the notes of the new release and make a fresh backup (section 4).

2. Turn Auto off on the page and wait until the page shows Auto off and no recovery running; «accepted» or «queued» is not finished yet. The install script refuses while Auto is on.

3. Download and verify the new package and the kit of the same release (section 3), copy them to `/tmp` and run `01-preflight.sh`, `02-install.sh` and `03-verify.sh wait` as in section 5. Settings, the channel pair, the history and the acceptance of the same terms version are kept.

4. While the package operation runs, the page shows `MAINTENANCE-IN-PROGRESS`: Start and the switching buttons are refused, Stop always works.

5. Press Ctrl+F5, check the installed version, then start Auto yourself if you want it.

   ```text
   opkg status homensai-auto-vpn | grep Version
   ```

6. Automatic rollback (packages from 2.1.0-alpha10 on, upcoming; not yet verified on a router): if the new package fails its file self-check during the upgrade, the program restores exactly the previous working version from its verified copy and starts it. Settings, journal and history are not touched; Auto runs again only if you had started it. The page shows `UPGRADE-ROLLED-BACK`: download the package again, verify it and install again. Without a matching copy (`UPGRADE-ROLLBACK-UNAVAILABLE`, `UPGRADE-ROLLBACK-VERSION`, `UPGRADE-ROLLBACK-FAILED`) the service stays off until you install a verified package; less than 8 MB free flash prevents the copy (`INTEGRITY-SNAPSHOT-NO-SPACE`).

### 10. Roll back to the previous version by hand

1. You need the older package and the source archive of its own release (its kit). Verify the package checksum as in section 3.

2. Make a backup (section 4), turn Auto off on the page and wait until it is off.

3. Only when going back from 2.x to an older line (1.x or 0.9): if the file below exists, restore the old history format first. Events recorded after the change to the new format are lost.

   ```text
   cp /etc/homensai-vpn/native-history.v1.json /etc/homensai-vpn/native-history.json
   ```

4. Remove the current version. Settings and history stay on the router; the script refuses while Auto or the protection table is active.

   ```text
   sh /tmp/04-uninstall.sh
   ```

5. Copy the older package and the scripts of its own kit to `/tmp` (they replace the newer scripts), then run its preflight and install. If a signed kit stops with `CHAIN-DOWNGRADE`, the router remembers a newer release; if you really want to go back, repeat the install command with ` --allow-downgrade` at the end.

   ```text
   sh /tmp/01-preflight.sh && sh /tmp/02-install.sh /tmp/homensai-auto-vpn_OLDVERSION_all.ipk
   ```

6. Verify with the old kit. An older version may show the terms again; you accept them yourself.

   ```text
   sh /tmp/03-verify.sh wait
   ```

### 11. Remove the program

1. Turn Auto off on the page and wait until it is off.

2. Remove only this application (`opkg remove homensai-auto-vpn` does the same without the extra checks). Shared dependencies such as python3 or lua are never removed: other software may need them.

   ```text
   sh /tmp/04-uninstall.sh
   ```

3. opkg can return 0 even when the lifecycle guard refused. Check: an empty result means the package is gone.

   ```text
   opkg status homensai-auto-vpn
   ```

4. Settings and history stay in `/etc/config/homensai_vpn` and `/etc/homensai-vpn` for a later reinstall. Delete them only if you want a clean router and keep a backup: they may hold your Telegram token. This cannot be undone.

   ```text
   rm -f /etc/config/homensai_vpn && rm -rf /etc/homensai-vpn
   ```

5. If the removal is refused, the message says why (for example an unfinished switch). Do not force it: follow the Help topic «I have no internet» and [router-test-kit/EMERGENCY.md](../router-test-kit/EMERGENCY.md).

### 12. Messages and codes: what to do

Messages of the install scripts and the most frequent codes. Every program code has a full explanation in [ERROR_CODES.md](ERROR_CODES.md) and in the app (Settings → Reference); a code on the page opens its explanation with one click.

| Message or code | What to do |
|---|---|
| `STOP: size … / STOP: sha256 …` | The file is damaged or belongs to another version. Download it again from the same release; never edit the expected values in the script. |
| `KIT-UNAVAILABLE` | The scripts belong to a version that was not released (for example a development branch). Use the kit from the source archive of the same release as the package. |
| `run 01-preflight.sh first` | Run `sh /tmp/01-preflight.sh` before the install script. |
| `SIGNATURE-MISSING` | `.ipk.sig` and `CHAIN.jsonl` are not next to the package in `/tmp`. Copy them. `--allow-unsigned` only for a release that has no signature. |
| `SIGNATURE-INVALID, SIGNATURE-KEY-UNTRUSTED, SIGNATURE-KEY-REVOKED` | The package is not signed by a trusted release key. Do not install it; download from the official releases page again and report the case. |
| `SIGNATURE-TOOL-MISSING` | The router has no `usign` (it is part of the stock firmware). Stop and ask for help; do not install other tools to bypass it. |
| `CHAIN-HEAD-MISMATCH` | The package is not the newest entry of that `CHAIN.jsonl`: files of different releases are mixed. Take all files from one release. |
| `CHAIN-DOWNGRADE` | This release is older than the history the router remembers. Only for a deliberate rollback: repeat with `--allow-downgrade` (section 10). |
| `CHAIN-FORK, CHAIN-FORMAT, CHAIN-SEQ-GAP, CHAIN-PREV-MISMATCH, CHAIN-KEY-…` | The release history is damaged or differs from the one installed. Do not install; report it. |
| `native_enabled=1; stop Auto first, LIFECYCLE-STOP-AUTO-FIRST` | Auto is on. Turn it off on the page and wait until it is off, then repeat. |
| `owned nft guard present` | The program's own protection table is still active (a recovery is unfinished). Do not delete it by hand first: follow the Help topic «I have no internet» and [router-test-kit/EMERGENCY.md](../router-test-kit/EMERGENCY.md). |
| `pending uci changes, LIFECYCLE-PENDING-UCI-CHANGES` | The program has unsaved settings changes. Look at them with `uci changes homensai_vpn` and save or discard them deliberately. |
| `LIFECYCLE-RECOVERY-UNFINISHED and other LIFECYCLE-…` | A switch or recovery is not finished. Wait, read the code explanation; never delete journals to get past it. |
| `dependency … missing, DEPENDENCY-…, LIFECYCLE-PYTHON-REQUIRED` | Install the named package from the firmware's own feeds (section 5, step 6). |
| `free writable storage, CONFIG-STORAGE-FREE` | Less than 20 MiB free or the configuration storage is read-only. Free space; never remount or repair the flash by force. |
| `MONITOR-ONLY-DEPLOYMENT` | The board is not a GL-MT3000 or GL-MT6000. This router is not supported. |
| `UNSUPPORTED-BOARD, UNSUPPORTED-FIRMWARE, FIRMWARE-UNKNOWN` | Auto is refused on this model or firmware (switching is verified only with GL.iNet 4.11.0); monitoring keeps working. Choosing a model does not bypass it. |
| `TERMS-NOT-ACCEPTED` | Open the page and accept the terms yourself. |
| `SERVICE-AUTO-OFF` | Press «Switch the Auto service on» in the Monitoring block; this does not start Auto by itself. |
| `MAINTENANCE-IN-PROGRESS, MAINTENANCE-INTERRUPTED` | A package operation is running, or it was interrupted. Wait and reload; after an interruption install the package again. |
| `UPGRADE-ROLLED-BACK, UPGRADE-ROLLBACK-…, UPGRADE-NOT-INSTALLED` | The upgrade was rolled back or could not be finished (section 9). Follow the action of the code in [ERROR_CODES.md](ERROR_CODES.md). |
| `INTEGRITY-TOOL-MISSING, INTEGRITY-NO-AUTO` | The file self-check cannot run, so Auto is not started; the page and monitoring work. Reinstall the same version. |
| `ubus homensai-vpn status unavailable` | Run `/etc/init.d/rpcd reload`, log out of LuCI and log in again. |

### 13. Safety rules

The `.ipk` is an application, not firmware: never load it as firmware and never use a factory reset as a shortcut.

No `opkg --force-…` options, no `opkg upgrade` of all packages, no foreign package feeds.

Work only on the intended router and check its model and address before each change. If your home network depends on a GL-MT6000, do not install there unless you deliberately want to: continuous Auto is not accepted on the MT6000.

Backups contain secrets. Never put passwords, tokens, keys or full configuration files into a chat, a screenshot or a public repository.

Never accept the terms or start Auto on someone else's behalf; AI agents must not do it either.

Do not delete the program's journals or protection tables to get unstuck, and do not reorder VPN rules by guess: use Help and [router-test-kit/EMERGENCY.md](../router-test-kit/EMERGENCY.md).

### 14. Let an AI agent do it

If you do not want to type commands, an AI agent with a terminal on your computer (Codex, Claude Code or similar) can do these steps for you. A plain chat without tools cannot install anything.

Copy the prompt from the Help topic «Prompt for your AI agent» (it has a copy button); the same text is in [AI-INSTALL.en.md](AI-INSTALL.en.md) and [AI-INSTALL.ru.md](AI-INSTALL.ru.md) and at the end of the guide files [INSTALL.en.md](INSTALL.en.md) and [INSTALL.ru.md](INSTALL.ru.md).

The prompt makes the agent ask you first, check read-only before changes, make a backup, verify sha256 and the signature, show every command and wait for your yes before each change. It forbids accepting the terms for you, starting Auto, changing unrelated network or firewall settings and bypassing any refusal.

Stay at the computer: type the router password only into the terminal prompt, answer the agent's questions, and press Accept and Start on the page yourself when you want.

[Installation guide](INSTALL.en.md)

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Install, upgrade, roll back or remove: step-by-step guide.
You want to install the program, upgrade it, go back to the previous version or remove it yourself, with commands you can copy. Reading it changes nothing.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="ai-lan-prompt"></a>
## Prompt for your AI agent: run the LAN helper

You do not want to run the LAN helper by hand: an AI agent that can run commands on your computer does the steps and asks you only for what it must not do itself.


Check the real client path yourself, or give this prompt to ChatGPT/Codex or Claude Code(Sonnet/Opus) with tools on a computer in this LAN. The helper is optional for prepared-MT3000 router-probed IPv4 Auto. A full switching trial is a separate operation.

The prompt forbids the agent to ask for or type your password or the word TEST, and to turn Auto on; it must get your explicit yes before the full trial and stop at the first error. Read it before you paste it; the text below is exactly what is copied.

```text
Help me use the Windows LAN witness for HomenS.AI Auto VPN on the specific router I identify. Do the available technical work with real tools; do not pretend a hosted chat is a client on my LAN.

PARAMETERS
Router application origin/private IP and port: [verified actual value]. Cable interface index: [verified value]. Mode: [SelfTest / CheckOnly by default / ProbeOnly / explicitly authorized full client-confirmed trial]. Requested time/session-loss scope: [fill only for a full trial]. Helper source: the same selected/installed release, not an unrelated mutable script.

SCOPE
Prepared continuous MT3000 router-probed Auto does not require this LAN trial or a LAN certificate. This is an optional separate client witness. A full client-confirmed trial edits application trial settings and can switch router traffic; it must not compete with a running continuous session. First finish its normal Stop/recovery and verify the actual baseline.
Reuse an explicit full-trial authorization already given for this same scope; do not ask again for it. Otherwise prepare a concrete bounded test/undo and ask once before the full mode. The owner enters the password and TEST privately themselves; never type those confirmations for them or accept terms for them.
No computer NIC/DNS/routes/firewall changes, no disabling another VPN, no firmware/feed replacement or resetting budgets. Diagnose refusals rather than inventing a bypass.

1. Verify the intended device and management path, not just a responding private IP. Two adapters can reach different routers with the same address. Check the ordinary management route as well as the explicit cable path before any credential request. Current helpers refuse CLIENT-CONTROL-PATH-MISMATCH; an older release may lack that guard, so do not rely on the filename as proof. A browser loopback gateway is not the real LAN-witness address.
2. Check pwsh -v. PowerShell7 is required; if installation is within my already authorized setup scope, use the official package: winget install --id Microsoft.PowerShell --exact. Otherwise explain the missing dependency and the specific required action.
3. Download client-test.ps1 and start-lan-helper.ps1 from the verified application's own origin at /luci-static/resources/view/homensai-vpn/. Keep them together in one new private folder. Optional start-lan-helper.cmd requires both files. Preserve release/hash/source identity and inspect the script. Do not fetch from the other router merely because its private IP matches.
4. In that folder use: pwsh -NoProfile -File .\client-test.ps1 -SelfTest
For path prerequisites use: pwsh -NoProfile -File .\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly
Replace the example address and index with the verified parameters before running. CheckOnly is not an Internet or switching test and asks for no password.
5. For actual bound DNS/HTTPS without starting Auto use: pwsh -NoProfile -File .\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -ProbeOnly
Again substitute the real parameters. It measures that IPv4 client path, not every app/IPv6. It makes network requests but does not alter router settings.
6. Only for the separately authorized full trial, verify that prior Auto/recovery is complete and the client-trial platform/pair is ready. Run: pwsh -NoProfile -File .\start-lan-helper.ps1
Choose mode3 with a bounded deadline/window. The owner enters the private password and TEST. Management HTTP is not encrypted; use only the intended trusted LAN or HTTPS with a properly trusted certificate. Do not disable certificate validation. Never inspect, print, log or save their password, session, token or full configuration.
7. Wait for the actual final result. A queued Stop is not restoration. Exit0 applies to the selected mode; exit2 is refused/unverified/failure; exit3 means verified retained reserve, not a successful original-path return. Do not tell the owner that continuous Auto is ready merely because CheckOnly or a separate trial ended. Starting continuous Auto is its own requested outcome with current readiness.
8. Report source/version, selected mode/path, exact diagnostic codes, final Auto/channel and verified/unverified areas. Keep original failed attempts, redact addresses/private transaction data from shared output, and save the stopping point. Do not turn recipes, short probes or SelfTest into physical LAN/IPv6/day-long/external-model certification.

```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Prompt for your AI agent: run the LAN helper.
You do not want to run the LAN helper by hand: an AI agent that can run commands on your computer does the steps and asks you only for what it must not do itself.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="probe-boost"></a>
## Probe level and automatic boost: how it works

You want to know exactly when the router checks more often and when it returns to the chosen level.

Probe level 1-5 sets two cadences. Channel health check (is internet working through the VPN): level 1 every 60 s, 2 every 30 s, 3 every 20 s, 4 every 15 s, 5 every 10 s. Three-site response measurement: 300, 120, 60, 45 and 30 s. The probe level is set in Settings → Router load (Console: Auto tab). The ping has its own interval in Router load → How response is measured: once a minute by default, from every 10 s to every 5 min. With the "Previous rule" detector a failure is confirmed after 3 failed health checks in a row, so level 1 confirms in about 3 minutes and level 5 in about 30 s. With the default HMM detector Auto decides by a probability model instead (about 25 s into a long outage); the probe level still sets how often the model receives new evidence.

Automatic boost starts when Auto is running and watching (OBSERVING, COMMITTED or working on the reserve) and the primary or reserve channel fails one health check. From that moment the router checks every 10 s and measures the three-site response every 30 s, whatever level you chose (the ping keeps its own interval). Nothing is switched by the boost itself: it only makes the checks frequent so that a real failure is confirmed in about 30 s.

An episode lasts 10 minutes from the last failed check, but never longer than 20 minutes in total. It ends earlier in effect when its job is done: after Auto switched the channel, or after the failure was confirmed by the detector, further failures no longer extend it.

When the episode ends, the router returns to your level and writes the result to the decision log: switched (Auto changed the channel), failure-confirmed (the channel really failed), false-alarm (one check failed, then the channel worked) or disabled (you turned the boost off). Then there is a 10-minute rest: no new episode starts, and the same channel cannot start one again until it has passed a check. A channel that stays down therefore cannot keep the router at the fast cadence forever.

The decision log lists every level change and every episode: time, level, what happened, which channel and its error code. Open it with the link «Decision log: levels and boost» in Router load → How response is measured, or in the Console on the Log tab. The Router load summary shows the chosen level and «· boost on» when the boost is enabled.

If the router refuses a level change (for example while a switch is running), the settings are not saved and a window shows the code; press Save again after the switch. A manual channel switch does not turn Auto off: Auto keeps watching the channel you chose, so the boost works the same way after a manual switch.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Probe level and automatic boost: how it works.
You want to know exactly when the router checks more often and when it returns to the chosen level.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="response-measurement"></a>
## How the response is measured

You want to know what the response numbers mean and why the reserve is slower.

The method is chosen in Settings → Router load → How response is measured (Console: Auto tab → Router load). Default: ping (ICMP echo to 1.1.1.1, or 8.8.8.8 / 9.9.9.9) through each tunnel: small numbers, almost no router load, best for comparing the channels. Alternative: three websites. The router itself measures through each VPN tunnel, not your computer. Three websites are opened fresh: Google, Cloudflare and Wikipedia. Each time includes the DNS lookup, the TCP connection, the TLS encryption handshake and the complete HTTP headers.

The response shown is the average of the three sites and appears only when all three answered (3/3). A partial result is shown as coverage without an average, so a slow site that timed out cannot make the number look better.

Opening a site needs 5-7 round trips, so the response is several times the ping. Example from the MT3000: WireGuard ping 53 ms gives about 430 ms; OpenVPN over TCP ping 241 ms gives about 2.4 s, because TCP inside TCP waits and resends on any loss and OpenVPN costs more router CPU.

How often: the ping has its own setting, Ping interval, in the same place (Router load → How response is measured): from every 10 s to every 5 min, once a minute by default. More frequent pings give fresher numbers but cost the router a little more CPU and traffic. The ping is sent during a channel check, so it is never more frequent than the checks of the probe level. The three websites follow the probe level in Router load (every 30 s at level 5, every 5 min at level 1, every 30 s during automatic boost). Each channel card shows the last value in ms and how long ago the channel was checked, for example 42 ms, checked 12 s ago; a dash means the router has no value for that channel yet. An old ping is only old: it never means the VPN is down. The response is information only: Auto decides on DNS and HTTPS health checks, not on the response time.

The delay chart and the statistics follow the method you chose; the ping history is kept separately. The option "Measure all methods (comparison)" makes every check also ping the other DNS addresses and open the three websites; the router collects these extra values for comparison, while the page shows the chosen method. Switching still uses only the chosen method.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: How the response is measured.
You want to know what the response numbers mean and why the reserve is slower.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="auto-two-channels"></a>
## How two-channel Auto works

You want to know what Auto does after you turn its switch on and what the router checks.

Auto starts the saved primary and reserve, checks IPv4 DNS/HTTPS, switches after repeated failures and returns after stable recovery according to your settings. The Auto switch is on «Home» in the Simple view and in the top strip of the Console view; you can turn Auto off during startup too. Auto that you turned on comes back by itself after a reboot or power cut, with every start check; turning it off cancels that.

About these checks: two selected VPN channels; the router checks them itself through each tunnel. How often is set by the probe level in Settings → Router load, Console: Auto tab (every 60 s at level 1 down to every 10 s at level 5); a failure is judged by the detector (by default a probability model; "3 failed checks in a row" only in the Previous rule mode).

Lamp colours are the same in both views (Simple and Console). A channel lamp: green — the channel works (the chip "Traffic here" marks the one carrying your traffic, "Standing by" the other); yellow — it is being checked or a switch is under way; red — it does not respond or its tunnel is off (with the code); grey — no fresh data from the router. The big lamp next to the status line shows only the internet: green — there is internet, through the primary or the reserve, with Auto on or off (on the reserve the status says "Works via the reserve": there is no spare channel until the primary is back); yellow — a switch or a check is under way, or Auto is handling a failed channel (at most 60 s); red — there is no internet (both channels fail, the router itself sees no internet, the channel carrying traffic fails while Auto is off, or it still fails 60 s later); grey — no fresh data (?). The Auto switch is a separate indicator: green — Auto is on; red — manual mode, Auto is off (○), or "Auto stopped: recovery needed" (⚠); yellow — Auto is starting or paused for a speed test (the big lamp stays green: the internet works during the test); grey — no fresh data (?). It says its state in words; when Auto is stopped, the line under it names the reason (HELD, BLOCKED) and the code. Both indicators are also in the header of every page: the "Internet" and "Auto" lamps. "Switch here" appears only on the card of the channel that does not carry traffic.

No internet? Open the Help topic "I have no internet" for the recovery steps (Simple view: "? Help" in the top menu; Console: System tab → Help, codes, training).

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: How two-channel Auto works.
You want to know what Auto does after you turn its switch on and what the router checks.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="planner-wait"></a>
## Why Auto waits before switching

You want to understand why a single failed check does not immediately switch the channel.

The planner compares consecutive failed checks of the channel in use with consecutive successful checks of the other channel. The configured thresholds help avoid switching because of a brief interruption.

A green observation describes a successful check or an unmet failure threshold. It is not a separate confirmation that Auto is ready or that a route change is allowed.

Auto also considers fresh observations, the selected VPN pair, controller state and the configured return policy. A recommendation alone does not switch traffic.

The current Auto state and the channel carrying traffic are on Home (Simple view) or the Channels tab (Console). The sequence of decisions and their reasons is in Events and reasons on Home, the Log tab of the Console, and the live log (Settings → System and diagnostics → Live log; Console: Log → Live log). If observations are stale, press Check now; it refreshes checks without choosing a channel for you.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Why Auto waits before switching.
You want to understand why a single failed check does not immediately switch the channel.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="no-internet"></a>
## I have no internet

Devices on your network cannot open sites after Auto ran or after you changed VPN settings.

Keep a working way to reach the router, such as the LAN cable and a phone with mobile data. Confirm that the page belongs to the intended router.

On Home (Console: Channels tab) check which channel carries traffic and whether both channel cards have fresh results. A working reserve is a normal state. Select another channel only when its readiness is confirmed; do not return to a failed primary just because it is called primary.

Read the local emergency summary over SSH. Keep it private until you remove addresses, policy identifiers and private transaction data.

```text
homensai-vpn-emergency show
```

If managed recovery is stuck, stop the application services. This can restore the managed policy/interface baseline and disable the saved Auto flag; it is not a read-only command. Pending application edits must be resolved separately.

```text
homensai-vpn-emergency stop-auto
```

After services have stopped, remove only a verified application-owned traffic guard if it remains. Never delete vendor firewall tables or disable Kill Switch. Verify the resulting route and client Internet.

```text
homensai-vpn-emergency remove-guard
```

If needed, inspect the stock VPN Dashboard. Choose a known working configuration deliberately; do not reorder unrelated rules or import new keys as an emergency shortcut.

A router reboot is a last recovery step when you still control the device. It interrupts connectivity and does not repair a bad VPN configuration. Auto that you turned on comes back by itself after the reboot, with every start check; if you turned Auto off, it stays off.

Once connectivity is restored, start the application services and confirm fresh monitoring. This command alone does not confirm Internet or start continuous Auto.

```text
homensai-vpn-emergency start
```

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: I have no internet.
Devices on your network cannot open sites after Auto ran or after you changed VPN settings.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="ssh"></a>
## How to connect by SSH

You need a command line on the router for the steps in this Help.

Use the real LAN address of the intended router. The address in the examples is a factory default, not an instruction to change your computer or router addresses.

Open a terminal. Windows may provide OpenSSH Client; otherwise use your installed SSH client. Replace the example address with the verified router address.

```text
ssh root@192.168.8.1
```

If Git for Windows supplies your SSH client, its usual executable path is shown below. Use the actual path installed on your computer.

```text
& "C:\Program Files\Git\usr\bin\ssh.exe" root@192.168.8.1
```

At the first connection compare the host-key fingerprint with trusted router information before accepting it. If a saved key changes, stop and establish the device identity; do not disable host-key verification.

Enter the router root password only in the local hidden prompt, or use the already authorized SSH key. Do not paste credentials into chat or command text. The shell prompt can contain your router hostname.

If two adapters lead to different devices with the same private address, resolve which path reaches the target before logging in. The address-conflict topic explains this case.

Leave the SSH shell when finished.

```text
exit
```

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: How to connect by SSH.
You need a command line on the router for the steps in this Help.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="reserve"></a>
## The router stays on the reserve VPN

The reserve carries traffic, you want to return, or turning Auto off left the router on the reserve.

Check both channel cards on Home (Console: Channels tab): which one shows "Traffic here" and whether both have fresh checks. Being on reserve does not by itself mean an error.

For an intentional return, press "Switch here" on the Primary card when the primary is confirmed working and the button is available. A manual switch never turns Auto off: Auto keeps watching the channel you chose and moves traffic to the other one if it fails (there is no separate Resume Auto button). If turning Auto off left the router on the reserve, use the same "Switch here" on the Primary card and verify its actual result.

Automatic return depends on the saved return policy and fresh primary health. The hold-reserve preference keeps a WORKING reserve: it does not return merely because primary probes succeed. If the pinned reserve itself fails (the failure detector and a fresh router probe both say so) while the primary is healthy, Auto rescues the traffic to the primary after the short rescue stability (rescue_stable, default 10 s) under any return policy; an unknown reserve check keeps the hold. After an Auto restart or a package upgrade Auto returns to the primary when it is healthy.

If neither channel works or a recovery command is refused, read its code and use No internet. Do not change stock VPN profiles while Auto owns a transition.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The router stays on the reserve VPN.
The reserve carries traffic, you want to return, or turning Auto off left the router on the reserve.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="auto-refuses"></a>
## The Auto button refuses to start

Turning the Auto switch on shows a message with a code.

Open Router readiness (Settings → System and diagnostics; Console: System tab) and read the Auto status line on Home or in the Console strip. Press the code in the message: its explanation names the exact refused condition. A green dry-run forecast is not a separate permission to start.

Verify the actual model, firmware and saved pair. Model selection does not enable unsupported firmware or turn two profiles of one tunnel into two channels.

Use the persistent-preparation help for acceleration, IPv6, stock workers and routing policy. Inspect before changing anything; one checkbox alone is not evidence that preparation is complete.

Prepared MT3000 router-probed IPv4 Auto uses fresh router evidence without a LAN certificate. A separate client-confirmed trial requires its own LAN helper and certificate. Keep these modes distinct.

Wait for current observations after changing profiles. Turning the switch on again and again does not repair an identity, worker or policy mismatch. The Auto switch remains available to turn Auto off or cancel startup.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The Auto button refuses to start.
Turning the Auto switch on shows a message with a code.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="helper-what"></a>
## What is the LAN helper and how do I start it

You want independent client evidence or a separate bounded LAN-confirmed trial.

The Windows PowerShell helper runs on a separate computer. SelfTest is offline; CheckOnly checks path prerequisites; ProbeOnly sends real bound DNS/HTTPS probes without starting Auto. The full trial changes application trial settings and may switch router traffic.

PowerShell 7 is required. Install the stable Microsoft package if it is missing; this is a computer software installation, not a router command.

```text
winget install --id Microsoft.PowerShell --exact
```

Download client-test.ps1 and start-lan-helper.ps1 into one folder: Settings → System and diagnostics → "Download LAN helper" and the launcher link next to it (Console: System tab → Help, codes, training). The optional start-lan-helper.cmd shortcut needs both of those files.

Run the launcher from that folder and enter the real private router address and the verified cable adapter number. A loopback browser gateway is not a LAN-witness target.

```text
pwsh -NoProfile -File .\start-lan-helper.ps1
```

Start with mode 1. It does not authenticate or change router/network settings and does not prove Internet health. For real DNS/HTTPS without a switching trial use ProbeOnly explicitly.

Choose mode 3 only for an authorized bounded client-confirmed trial. Enter credentials privately and type TEST yourself. Read the final restoration result; queued Stop is not proof that the original client path returned. Finish any continuous Auto session and verify its normal Stop/recovery before starting this separate trial.

The helper does not add/remove routes, change DNS/NIC settings or disable another VPN. A conflicting control route is refused before credentials or a session are sent.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: What is the LAN helper and how do I start it.
You want independent client evidence or a separate bounded LAN-confirmed trial.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="helper"></a>
## The LAN helper fails

client-test.ps1 stops with a code before or during the trial.

Use the real router address and your cable adapter number in this prerequisite check; the example values are not universal.

```text
pwsh -NoProfile -File .\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly
```

Inspect adapter names and addresses without changing them. The cable must reach the intended router rather than another device using the same private subnet.

```text
Get-NetAdapter | Select-Object InterfaceIndex,Name,Status
```

CLIENT-CONTROL-PATH-MISMATCH means the normal management route differs from the selected witness interface. Stop before logging in; establish an unambiguous management path. Do not change computer routing automatically.

CLIENT-CABLE-HTTPS-FAILED or error 10051 can indicate a missing usable route on the selected cable. Inspect IPv4 interface properties; this read-only command does not repair them.

```text
Get-NetIPInterface -AddressFamily IPv4 | Select-Object InterfaceIndex,InterfaceAlias,ConnectionState,IgnoreDefaultRoutes
```

The current helper never creates temporary probe routes. If an old version left routes, identify their owner and a specific approved cleanup; do not delete unrelated routes.

```text
Get-NetRoute -DestinationPrefix 1.1.1.1/32,1.0.0.1/32
```

A computer VPN or DNS protection can conflict with the selected client path. Diagnose ownership first; the helper does not stop those programs. CheckOnly, ProbeOnly and a full trial have different scopes.

Exit 0 is successful completion for the selected mode, not proof of all networks. Exit 2 is refusal/unverified/failure; exit 3 means a verified retained reserve rather than successful original-path restoration.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The LAN helper fails.
client-test.ps1 stops with a code before or during the trial.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="stale"></a>
## The page is old, empty or says the monitor is not running

After an update, the page looks old, shows errors, or the status is stale.

Press Ctrl+F5 to reload without cache, then sign out of LuCI and sign in again (new permissions after an update).

Check the Monitoring service lamp (Settings → System and diagnostics; Console: System tab). If it offers "Restore monitoring", press it; if the monitor services stay stopped, start those services over SSH and wait for a fresh timestamp; this is separate from turning Auto on.

```text
homensai-vpn-emergency start
```

If an update left RPC registration stale, reload rpcd deliberately and sign in again. This restarts the router RPC service and may interrupt management sessions; it is not a read-only inspection.

```text
/etc/init.d/rpcd reload
```

Check that exactly one monitor is running:

```text
ps w | grep homensai-vpn
```

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The page is old, empty or says the monitor is not running.
After an update, the page looks old, shows errors, or the status is stale.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="outside-change"></a>
## I changed VPN rules in the GL.iNet panel and Auto stopped

The page says the VPN rules were changed by someone else.

Auto refuses to compete with an external policy/profile edit. Read the actual controller phase and cleanup result; do not assume that every refused operation already restored Internet.

Check the current selected pair and the stock VPN configuration. If you intend to edit stock profiles, turn Auto off and wait for the managed recovery first.

Wait for fresh consistent identities and readiness. Prepared continuous-pair mode can then be started explicitly; a legacy client-confirmed mode needs a new matching trial/certificate after a relevant edit.

Keep failed attempts and unrelated edits. Do not forge a confirmation, erase the journal or remove a foreign firewall table to make a status green.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: I changed VPN rules in the GL.iNet panel and Auto stopped.
The page says the VPN rules were changed by someone else.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="telegram"></a>
## Telegram reports do not arrive

The page shows a Telegram error code, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.

Open the official https://t.me/BotFather in Telegram and send /newbot there, not in a terminal. Follow its current instructions.

```text
/newbot
```

BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).

BotFather provides the bot token. Treat it as a password and paste it only into the dedicated private token field. Do not put it into a browser URL, chat, Git or diagnostic output.

Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.

Way 1, the simplest: in Telegram open the bot @userinfobot (https://t.me/userinfobot) and press Start. The bot answers with your data; the line Id: 123456789 is your ID. Copy only the digits and paste them into the field Recipient. This is a third-party bot, not ours and not Telegram’s: never send it your token. Your own bot is still needed: open it and press Start once, otherwise Telegram will not let it write to you.

Way 2, without a third-party bot: to read chat.id send /start or a message to your own bot, then use this PowerShell recipe locally. It asks for the token privately and prints only IDs. Do not record a transcript or share raw updates. If another bot program consumes updates, stop and inspect that configuration rather than invent an ID.

```text
$privateKey = Read-Host 'Bot token' -AsSecureString
$botKey = [Net.NetworkCredential]::new('', $privateKey).Password
try {
    $updates = Invoke-RestMethod -Uri ('https://api.telegram.org/bot' + $botKey + '/getUpdates') -TimeoutSec 15 -ErrorAction Stop
    $ids = foreach ($item in $updates.result) {
        foreach ($kind in @('message','channel_post','edited_message','my_chat_member')) {
            if ($null -ne $item.$kind.chat.id) { [string]$item.$kind.chat.id }
        }
    }
    $ids | Sort-Object -Unique
} catch { Write-Output 'CHAT-ID-NOT-READ: check the bot token, a fresh /start and other update consumers.' }
finally { Remove-Variable privateKey,botKey,updates,ids -ErrorAction SilentlyContinue }
```

On the router open Settings → Telegram notifications (Console: System tab → Telegram notifications; in the first-run wizard it is step 3, Behaviour). Tick Send reports, enter the token privately and the verified chat ID or channel username as Recipient, choose when and what to send and press Save. An empty token field keeps the stored token.

Press “Send a test message”. A message should arrive within a few seconds. If a code is shown instead: TELEGRAM-… with “401” or “Unauthorized” means a wrong token; “400”, “chat not found” or “Forbidden” means a wrong Chat ID or you never pressed Start; a timeout means the router has no internet or a wrong clock.

Still nothing? Create the token again in BotFather (/token or /revoke) and enter the new one. Never send the token to anyone, including in a support chat.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Telegram reports do not arrive.
The page shows a Telegram error code, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="clock"></a>
## Dates are wrong, history or statistics are blocked

Codes like CLOCK-001 or HISTORY-001, or events with impossible dates.

The router clock must be correct. GL.iNet panel → System → Time: enable time synchronisation (NTP) and pick your time zone.

Check the clock over SSH:

```text
date
```

After the clock is right, statistics continue by themselves. Gaps are shown as unobserved time and are never filled with invented numbers.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Dates are wrong, history or statistics are blocked.
Codes like CLOCK-001 or HISTORY-001, or events with impossible dates.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="backup"></a>
## Make a backup before changes

Before an update, a LAN trial or any manual repair.

First verify the intended router and SSH host key. Replace the example address. On Windows use binary redirection through cmd so Windows PowerShell does not decode the compressed stream. sysupgrade -b exports a backup; it does not flash firmware.

```text
cmd /c "ssh root@192.168.8.1 sysupgrade -b - > router-backup.tar.gz"
```

On Linux or macOS, redirect the binary export to a private local file. Check the SSH command result and read the archive before using it as recovery evidence.

```text
ssh root@192.168.8.1 'sysupgrade -b -' > router-backup.tar.gz
```

The archive contains secrets and this export is not encrypted by itself. Store it in protected encrypted storage, outside Git, and verify your encryption key and recovery procedure independently. Never upload the raw export or its key.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Make a backup before changes.
Before an update, a LAN trial or any manual repair.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="remove"></a>
## Remove or roll back the program

You want the router without this program, or you need an older version.

Turn Auto off and verify the actual managed recovery and guard state before removing the package. If turning Auto off retained a reserve or recovery is unconfirmed, resolve the recorded condition first; do not force a return to an unhealthy primary. Then remove normally over SSH.

```text
opkg remove homensai-auto-vpn
```

Removal is not a complete data wipe. Preserve a private backup and check the actual conffile/history state before reinstalling; do not rely on unmodified defaults being retained by opkg.

If the removal is refused, the program tells why (for example a transaction is active). Do not force it: first use “I have no internet”.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Remove or roll back the program.
You want the router without this program, or you need an older version.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="report"></a>
## What to send when asking for help

You report a problem and want it solved quickly.

Record the time, installed/running version, selected channel and the exact code. Keep command output local until addresses, policy names, tokens, session values and private transaction data are removed.

```text
homensai-vpn-emergency show
```

Check the installed package version. It can differ from a cached browser page or running process after an interrupted update.

```text
opkg status homensai-auto-vpn | grep Version
```

Read the relevant recent log locally. Share only a reviewed redacted excerpt, not the complete configuration or archive.

```text
logread | grep -i homensai | tail -30
```

Never send passwords, Telegram tokens, cookies, SSH/VPN keys, full backups or private certificate/transaction nonces. A screenshot can contain addresses and identifiers too.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: What to send when asking for help.
You report a problem and want it solved quickly.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="history-retention"></a>
## Journal size and retained history

You want less browser memory or fewer saved observation days.

Settings → History and memory (Console: System tab): set Live log entries from 1 to 2000 and Keep detailed history from 1 to 7 days. These two change with Auto off. Save and verify the values.

The buffer limits browser observations; the period prunes stored details during processing/checkpoints. Monthly/lifetime counters remain separate. Increasing the period cannot restore removed detail.

Events and errors initially shows the latest 20 rows, with a triangle for more. Search and sorting use the downloaded retained snapshot, not just the visible rows.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Journal size and retained history.
You want less browser memory or fewer saved observation days.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="controlled-fault"></a>
## Test a transition from the current channel

You want a deliberate bounded traffic fault and a verified alternate route.

Open the failure test: Home → Tests → Failure test, button "Check that Auto rescues" (Console: Auto tab → "Run failure test"). Auto must be on. The channel carrying traffic is selected automatically; primary and reserve are both supported.

The router rechecks running Auto, private current-pair identity/policy, both healthy paths and session-loss consent. A preparation explanation means the destructive action has not started. Do not bypass a refusal.

The test temporarily drops IPv4 traffic on that tunnel device, not the VPN process or another server selected by name. It waits for failure thresholds and a fresh confirmed alternate route. "Stop and remove fault" removes the artificial fault early.

Only a confirmed route with fresh successful observations is success. A timeout removes the artificial block but is not a passed transition; inspect the reason, cooldown, budget and both channels. Kernel expiry is a safety limit, not proof of Internet.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Test a transition from the current channel.
You want a deliberate bounded traffic fault and a verified alternate route.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="address-conflict"></a>
## The router page opens the wrong device or refuses connection

Two networks use the same private address, or the browser chooses another adapter.

Verify the intended model and the physical management connection first. The same IPv4 address can identify different devices on different adapters; a responding web page is not sufficient identity.

Inspect IPv4 addresses and interface indexes read-only. Do not silently change Wi-Fi, adapter addresses, routes or another router to fix a page.

```text
Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceIndex,InterfaceAlias,IPAddress
```

A separately verified fixed-target local gateway may provide browser access without network-setting changes. It is machine-local and temporary; it does not replace the real LAN router address for a client witness or remove router authentication.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The router page opens the wrong device or refuses connection.
Two networks use the same private address, or the browser chooses another adapter.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="setup-guide"></a>
## First setup: four steps with examples

Help for the first-run wizard (Router → Channels → Behaviour → Terms and start). Reading it saves nothing.


The wizard opens by itself on the first visit: Router → Channels → Behaviour → Terms and start, about 2 minutes. The experimental-software agreement and the license terms (HomenSAI Personal & Commercial Source License v1.0) are shown at the last step; previously accepted terms are remembered on this router and are not asked again. Close the wizard without changes (shown once setup is complete) keeps the router settings as they are. Saving never starts Auto by itself; only the start button of the last step or the Auto switch does. Every step has Skip - open the interface: it closes the wizard, never starts Auto, never accepts the terms for you, and also works while Auto is running or a pair already exists.


Router

The router model, firmware and required parts are detected automatically and shown with lamps (Python, ubus · uci · ip · Lua · rpcd, certificates, settings storage, router preparation). A model cannot be chosen by hand: readiness checks are mandatory. A red row names its code; press it for the explanation. Nothing is changed in this step. Example: GL-MT3000, firmware 4.11.0, all rows green.



Channels

The wizard lists the VPN clients already configured in the GL.iNet panel → VPN, with protocol and response. Choose Primary (used always) and Reserve (used on a failure); they must be two different clients. The prepared MT3000 uses one WireGuard and one OpenVPN client; either can be primary. Missing one? Add a profile in GL.iNet → VPN first and open the wizard again. Example: primary WireGuard Germany, reserve OpenVPN Netherlands.



Behaviour

You can keep the defaults, but they are experimental: selected in simulation and checked by tests on a PC, not validated on hardware (the detection model with threshold 0.8, the 0.90 return condition, the stability times of 120 s and 10 s, the flapping limit of 2 per 60 min, the Fibonacci retry pauses and the check spreading are chosen in simulation and not yet validated on the router; the safe alternative is the Previous rule). How fast to switch: Calm, Normal (default; the model decides when to leave the primary, with the Previous rule 3 failures; 60 s pause, return after 2 checks and 120 s of a stable primary, or 10 s if the reserve itself failed) or Fast; when the primary is healthy again, return automatically or stay on the working reserve; allow a brief drop of calls and downloads: this consent is required to start Auto at all, because every switch can interrupt connections. Router load: probe level 1–5 (Balanced = a check every 20 s) and automatic boost. Telegram is optional: tick Send switch reports, enter the bot token and the recipient. Example: Normal, level 3, Telegram off.



Terms and start

Review the summary: primary, reserve, switching, load and Telegram. If the terms are not accepted yet, read them and tick both boxes yourself; they are never pre-ticked. Save without starting writes the settings and leaves Auto off. Accept terms and turn Auto on (or Turn Auto on, when the terms are already accepted) saves and then starts Auto with its usual readiness checks. Back corrects a value; Next alone saves nothing. Later the same settings are in Settings, and Settings → Language and look → Run the wizard again opens this wizard again (Console: System tab).



### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: First setup: four steps with examples.
Help for the first-run wizard (Router → Channels → Behaviour → Terms and start). Reading it saves nothing.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-PYTHON-39-MINIMUM"></a>
## Python 3.9 or newer: install or repair

A required router check failed or is unknown.


Python 3.9 or newer · PYTHON-39-MINIMUM

Runs the application. Version 3.9 or newer is required; installing an older vendor Python is not a pass.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

```text
opkg install python3
```

Verify the result

```text
python3 --version
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: PYTHON-39-MINIMUM — Python 3.9 or newer.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Runs the application. Version 3.9 or newer is required; installing an older vendor Python is not a pass.
After checking compatibility, install only from this firmware's original vendor feeds. Example: opkg install python3
Verify using: python3 --version
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Python 3.9 or newer: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-DEPENDENCY-UBUS"></a>
## ubus: install or repair

A required router check failed or is unknown.


ubus · DEPENDENCY-UBUS

Connects the application to router services. A missing command and a stopped ubus service need different diagnoses.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

```text
opkg install ubus
```

Verify the result

```text
ubus call system board
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: DEPENDENCY-UBUS — ubus.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Connects the application to router services. A missing command and a stopped ubus service need different diagnoses.
After checking compatibility, install only from this firmware's original vendor feeds. Example: opkg install ubus
Verify using: ubus call system board
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: ubus: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-DEPENDENCY-UCI"></a>
## uci: install or repair

A required router check failed or is unknown.


uci · DEPENDENCY-UCI

Reads and saves router settings. Never delete configuration or reset the router to repair this check.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

```text
opkg install uci
```

Verify the result

```text
command -v uci
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: DEPENDENCY-UCI — uci.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Reads and saves router settings. Never delete configuration or reset the router to repair this check.
After checking compatibility, install only from this firmware's original vendor feeds. Example: opkg install uci
Verify using: command -v uci
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: uci: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-DEPENDENCY-LUA"></a>
## Lua: install or repair

A required router check failed or is unknown.


Lua · DEPENDENCY-LUA

Runs the settings helper. Both the interpreter and its JSON/UCI modules must load.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

```text
opkg install lua lua-cjson libuci-lua
```

Verify the result

```text
lua -e "require('cjson'); require('uci')"
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: DEPENDENCY-LUA — Lua.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Runs the settings helper. Both the interpreter and its JSON/UCI modules must load.
After checking compatibility, install only from this firmware's original vendor feeds. Example: opkg install lua lua-cjson libuci-lua
Verify using: lua -e "require('cjson'); require('uci')"
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Lua: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-DEPENDENCY-IP"></a>
## ip: install or repair

A required router check failed or is unknown.


ip · DEPENDENCY-IP

Inspects interfaces and policy routes. Keep the matching vendor package; do not remove networking packages to force a replacement.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

```text
opkg install ip-full
```

Verify the result

```text
ip -Version
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: DEPENDENCY-IP — ip.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Inspects interfaces and policy routes. Keep the matching vendor package; do not remove networking packages to force a replacement.
After checking compatibility, install only from this firmware's original vendor feeds. Example: opkg install ip-full
Verify using: ip -Version
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: ip: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-RPC-PLUGIN"></a>
## Program plugin: install or repair

A required router check failed or is unknown.


Program plugin · RPC-PLUGIN

Connects this page to the installed application. Check the verified application package and rpcd registration; a Python package alone cannot repair it. Follow the installation prompt for a verified repair, without force flags.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

This needs diagnosis/recovery, not an arbitrary additional package.

Verify the result

```text
ubus -v list homensai-vpn
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: RPC-PLUGIN — Program plugin.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Connects this page to the installed application. Check the verified application package and rpcd registration; a Python package alone cannot repair it. Follow the installation prompt for a verified repair, without force flags.
Verify using: ubus -v list homensai-vpn
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Program plugin: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-CA-BUNDLE"></a>
## Certificates: install or repair

A required router check failed or is unknown.


Certificates · CA-BUNDLE

Supplies trusted certificate authorities for HTTPS. Also check the router clock; never disable TLS verification to make a probe pass.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

```text
opkg install ca-bundle
```

Verify the result

```text
test -s /etc/ssl/certs/ca-certificates.crt
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: CA-BUNDLE — Certificates.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Supplies trusted certificate authorities for HTTPS. Also check the router clock; never disable TLS verification to make a probe pass.
After checking compatibility, install only from this firmware's original vendor feeds. Example: opkg install ca-bundle
Verify using: test -s /etc/ssl/certs/ca-certificates.crt
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Certificates: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="dependency-CONFIG-STORAGE-FREE"></a>
## Writable configuration storage: install or repair

A required router check failed or is unknown.


Writable configuration storage · CONFIG-STORAGE-FREE

Settings need a writable filesystem and at least 1 MiB free; installation preflight separately needs 20 MiB. Read-only storage can have plenty of space but cannot save settings. Diagnose filesystem/recovery first; never automatically remount a production router, delete arbitrary files or reset it.

Install manually

Connect to the correct router, check firmware and free space, preserve a verified private backup. Use only the original matching vendor feeds. Run opkg update only when package lists need refreshing. Never run opkg upgrade or use force.

This needs diagnosis/recovery, not an arbitrary additional package.

Verify the result

```text
df -k /etc/config; cat /proc/mounts
```

Reload the page and reopen Router readiness (Settings → System and diagnostics; Console: System tab); require fresh evidence. A failed or stale check remains unverified even after a successful install command.

Let ChatGPT/Codex or Claude do it

Use an agent with a terminal and router access. This prompt addresses only this check; it does not authorize other network changes.

```text
On the specific router I identify, diagnose and repair this failed application check: CONFIG-STORAGE-FREE — Writable configuration storage.
Start read-only: verify model/firmware, package feeds, actual failure and free space. Preserve a verified private backup. Use existing authorized access; never request secrets in chat.
Purpose: Settings need a writable filesystem and at least 1 MiB free; installation preflight separately needs 20 MiB. Read-only storage can have plenty of space but cannot save settings. Diagnose filesystem/recovery first; never automatically remount a production router, delete arbitrary files or reset it.
Verify using: df -k /etc/config; cat /proc/mounts
Do not use force flags, mass upgrades, foreign feeds, firmware flashing, firewall resets or computer network changes. Do not start Auto or accept terms for me. Reload readiness and verify a fresh result, not only installer exit. Report PASS/FAIL/BLOCKED/UNKNOWN and remaining checks.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/INSTALL.en.md
```


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Writable configuration storage: install or repair.
A required router check failed or is unknown.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="router-preparation"></a>
## Persistent router preparation: inspect before changing

The row Router preparation (acceleration) in Router readiness is not done, or a PREP-… code is red or unverified. This is separate from installing application dependencies.

Read the actual model, firmware and the row Router preparation (acceleration) in Router readiness (Settings → System and diagnostics; Console: System tab); open each PREP-… code shown. The current profile is for prepared MT3000/4.11.0. Saved settings and loaded modules alone do not prove runtime readiness.

Before changing acceleration, stock VPN startup or DNS, preserve a verified private backup and the exact original values/files. Establish the specific preparation scope and undo procedure; do not copy another device's commands blindly.

Do not force-unload modules, remove drivers, disable a working DNS owner or alter computer networking. Recheck fresh status after the approved changes. A green preparation row does not start Auto or prove external LAN connectivity. The full operation/undo record is docs/ROUTER-PREPARATION.md in the project repository.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Persistent router preparation: inspect before changing.
The row Router preparation (acceleration) in Router readiness is not done, or a PREP-… code is red or unverified. This is separate from installing application dependencies.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="diagnose-all"></a>
## Cannot find the cause: complete AI diagnosis

No Help topic explains your symptoms or several parts fail together.


Ask ChatGPT/Codex or Claude to diagnose

The agent needs tools on your computer and router access. Copying runs no commands. Diagnosis does not authorize repairs.

```text
Find why HomenS.AI Auto VPN does not work, even if I cannot identify the right Help topic. Work systematically and perform available diagnostics yourself.

1. Ask for the symptom, expected result, when it began, target router and tool access. Do not ask questions already answered by available evidence.
2. Read project CURRENT-STATUS, installation and Help. Inventory actual model/firmware, installed/running versions, package integrity, services, logs, freshness and storage read-only.
3. Separate monitor errors, missing dependencies, stale UI/RPC, unconfigured pair, tunnel connection, selected traffic route, DNS/HTTPS failure, platform refusal and client-LAN proof. Router probes alone do not prove client internet.
4. Build a short hypothesis list. For each run the smallest read-only test that can support or reject it; retain timestamps/error codes and do not repeat irrelevant tests.
5. Inspect the matching Help topic and copied diagnostic prompt. If tools are unavailable, explain the limit and ask for one safe observation; never invent command output.
6. Produce a concrete minimal repair plan and rollback. Diagnosis does not authorize package/network/DNS/firewall/firmware changes, Auto Start/Stop, fault trials, Telegram messages or terms acceptance. Request the missing repair scope only when the evidence and concrete fix are ready.
7. After an authorized repair, repeat its actual failing check and verify fresh service/UI/configuration state. Preserve failed attempts and unrelated owner settings.
8. Report PASS/FAIL/PARTIAL/BLOCKED/UNKNOWN by area, known causes versus hypotheses, what changed, remaining limits and the next safe step. Never print credentials/full configs or claim a short/router-only test proves24hours/LAN/IPv6/hardware safety.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn
```


### Diagnostic prompt

```text
Find why HomenS.AI Auto VPN does not work, even if I cannot identify the right Help topic. Work systematically and perform available diagnostics yourself.

1. Ask for the symptom, expected result, when it began, target router and tool access. Do not ask questions already answered by available evidence.
2. Read project CURRENT-STATUS, installation and Help. Inventory actual model/firmware, installed/running versions, package integrity, services, logs, freshness and storage read-only.
3. Separate monitor errors, missing dependencies, stale UI/RPC, unconfigured pair, tunnel connection, selected traffic route, DNS/HTTPS failure, platform refusal and client-LAN proof. Router probes alone do not prove client internet.
4. Build a short hypothesis list. For each run the smallest read-only test that can support or reject it; retain timestamps/error codes and do not repeat irrelevant tests.
5. Inspect the matching Help topic and copied diagnostic prompt. If tools are unavailable, explain the limit and ask for one safe observation; never invent command output.
6. Produce a concrete minimal repair plan and rollback. Diagnosis does not authorize package/network/DNS/firewall/firmware changes, Auto Start/Stop, fault trials, Telegram messages or terms acceptance. Request the missing repair scope only when the evidence and concrete fix are ready.
7. After an authorized repair, repeat its actual failing check and verify fresh service/UI/configuration state. Preserve failed attempts and unrelated owner settings.
8. Report PASS/FAIL/PARTIAL/BLOCKED/UNKNOWN by area, known causes versus hypotheses, what changed, remaining limits and the next safe step. Never print credentials/full configs or claim a short/router-only test proves24hours/LAN/IPv6/hardware safety.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn
```

<a id="network-acceleration"></a>
## Auto blocked: hardware and network acceleration

Start reports HNAT, hardware acceleration or PREP-HNAT-CONFIG.

Disable network acceleration
GL.iNet → NETWORK → Network Acceleration

Turn Enable off and click Apply. Selecting Auto, Hardware or Software mode does not disable acceleration. Return here and check readiness again; Auto VPN needs a separate Start. Older firmware calls this menu Hardware Acceleration.
Open settings
GL.iNet instructions

If it is already off but the check still fails, open Router readiness (Settings → System and diagnostics; Console: System tab) and the code of the refusal for the exact failed check. Saved configuration and loaded runtime acceleration are checked separately.


### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Auto blocked: hardware and network acceleration.
Start reports HNAT, hardware acceleration or PREP-HNAT-CONFIG.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="stats-retention"></a>
## How long statistics are kept and how much memory they use

You want charts and rankings to remember more or fewer days, or you worry about flash and memory.

Open Settings → History and memory (in the Expert group; Console: System tab).

Statistics collection: Work keeps only what is needed and saves flash; Diagnostics records in detail for a chosen period (24 h, 72 h, 7 or 14 days) and returns to Work by itself. Keep detailed history: 1 to 7 days; Live log entries: 1 to 2000.

Read the line below the fields: how much RAM and flash the statistics use now and how much flash is free.

Press Save. The history period and the live log change only with Auto off; saving then offers to stop Auto and never starts it again by itself. The router deletes statistics older than the period. Switching and Auto do not depend on this setting. Reset statistics… in the same section clears the counters and charts; old data is archived on the router.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: How long statistics are kept and how much memory they use.
You want charts and rankings to remember more or fewer days, or you worry about flash and memory.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="preparation-buttons"></a>
## Router preparation when Auto is turned on

Router readiness shows «Router preparation (acceleration)» as needed, or turning Auto on reports a PREP-… or PREPARATION-… code.

Where: Settings → System and diagnostics → Router readiness (Console: System tab). The page has no separate Disable buttons: turning the Auto switch on is your consent to the preparation Auto needs, and the router performs it itself before starting.

Each failed check that can be repaired without a router restart is fixed with the same reviewed writer as before: the app first preserves the original value privately, then changes only that setting and reads the result again. No VPN reconnect or automatic reboot occurs.

Startup switches do not stop a running service. SFE module autoload preserves the exact original file; live modules are not forcibly unloaded. Firewall offloading is saved without a firewall reload. When restart is required, Auto refuses with PREPARATION-RESTART-REQUIRED and remains blocked until a separate deliberate router reboot and fresh checks. Firewall flow offloading is not changed automatically: switch it off yourself as its code explains.

An uncertain reply is not success. Keep /etc/homensai-vpn/preparation-changes for recovery and inspect the actual state before another attempt. Unknown firmware, bindings, saved files or active recovery cannot be bypassed by turning Auto on again.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Router preparation when Auto is turned on.
Router readiness shows «Router preparation (acceleration)» as needed, or turning Auto on reports a PREP-… or PREPARATION-… code.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="website-response"></a>
## Three-site response: method and history

You want to understand the single displayed VPN response metric and gaps.

Every selected VPN checks the same three ordinary HTTPS addresses: Google generate_204, Cloudflare cdn-cgi/trace and Wikipedia. Fresh DNS, TCP, TLS and all HTTP response headers are timed. This is not full webpage rendering, ICMP, or the separate technical DNS/HTTPS health probe.

The displayed value is the arithmetic mean only when all three sites pass. A partial check shows coverage and no number; failures and timeouts are never zero and old metrics are never substituted. The value stays fresh for 1.5 × the measurement interval plus 15 seconds (60 s at a 30 s interval, 465 s at the 300 s of probe level 1) and is bound to the VPN generation.

Statistics follow the selected graph window. Mean is weighted by complete three-site cycles; minimum and maximum describe observed minute means. Missing periods and incomplete checks are not filled.

Storage follows the configured1–7 days. Older deleted measurements cannot be restored. Wide views sample markers; lines and statistics use retained measurements. History starts when recording begins and is saved at the configured checkpoint interval.

Quality and ranking use these same complete website cycles. Resetting statistics sets a new counting boundary while preserving graph history. A lower mean is a recommendation, never permission to alter routes or enable Auto. Old event HTTPS measurements remain explicitly technical.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Three-site response: method and history.
You want to understand the single displayed VPN response metric and gaps.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="about-project"></a>
## About the program and the project

You want to know who made this program, why it contains so much science and where its ideas come from.

Why this project has so much mathematics, physics and biology. These experiments exist because the author, Serhii Khomenko, has always loved these sciences, even though they never came easily to him. That is why every idea is tested honestly: compared with the previous method in the simulator and on the router, and only what is really better is kept.

HomenS.AI Auto VPN, author and copyright holder Serhii Khomenko / HomenS.AI (homensai.com). Licence: HomenSAI Personal & Commercial Source License v1.0: source-available, free for private non-commercial use of the unmodified program; the licence text governs. Tested on GL-MT3000 with firmware 4.11.0.

Where the idea comes from. Tuning a threshold from a network's own history is a technique of large systems that ordinary home routers do not have: the phi-accrual failure detector (Cassandra, Akka, Hazelcast), anomaly detection in Amazon CloudWatch and Datadog, cake-autorate (OpenWrt), and TUF and Sigstore for signing releases. We took ideas, not their code.

Honestly: each method is known. In an offline search of open sources we did not find the same combination in one home router, but that does not mean nobody did it, and we claim no academic novelty for any single element. Our evidence is a simulator checked against one test router; samples are small and nothing is peer reviewed.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: About the program and the project.
You want to know who made this program, why it contains so much science and where its ideas come from.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="auto-adaptation"></a>
## Auto-adaptation and the master slider

You want to know how Auto learns your network, what the slider “Fast reaction ↔ No unnecessary switches” does and what the modes Advice, Auto and Manual mean.

The monitor keeps a short diary of your network (failed checks, outage lengths, response by hour, switches and unnecessary switches): about 3 KB a day in memory, saved to flash once a day, 30 days. Every night at 03:30, at the lowest priority, the advisor replays the past days through the same decision code that really runs, for different slider positions, and finds the position with the lowest cost: seconds of downtime plus a 20 s penalty for each unnecessary switch.

Advice (default): the recommendation is shown and you apply it with a button. Auto: the system moves the slider itself, by at most 0.1 at a time and at most once per 20 hours, never during an outage or a switch, and records every change with its reason. Manual: your own values (Custom), the advice is only shown. Auto will become the default for ordinary users only after a 7-day check of the advisor on the MT3000. A suggestion appears only if it saves at least 5 % and the window held at least 5 events; otherwise you see keep or not enough data.

Where: Settings → Auto-adaptation: failure reaction (expert); the Simple view has a card Auto-adaptation with the training. The page shows the chart (downtime per day against unnecessary switches per day), a table of all variables and Fine tuning. Safe limits are checked again by the router. None of this starts Auto.

Not yet verified on the router: the advisor over 7 days, the Auto mode and the slider positions away from the earlier measured ones. The figures shown (downtime, unnecessary switches) are simulator and replay estimates, not measurements.

Recovery time statistics keep an estimate and a guarantee apart. “P95 (estimate)” is the 95th percentile of the recorded sample itself; with fewer than 59 measurements it is shown as ≈P95, and with 19 or fewer it equals the maximum. A separate “P95 upper bound, 95 % confidence” appears only from 59 measurements: with 95 % confidence the true P95 is not above it. The number of measurements n is always shown; an empty value is shown as a dash, never as zero.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Auto-adaptation and the master slider.
You want to know how Auto learns your network, what the slider “Fast reaction ↔ No unnecessary switches” does and what the modes Advice, Auto and Manual mean.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="wan-and-server-keys"></a>
## Router has no internet (WAN-DOWN) and a changed VPN-server key

Auto shows WAN-DOWN or WAN-RECOVERING, or the page reports that a VPN server shows a different key.

WAN-DOWN means the router itself has no internet (not just a tunnel). Before, every check went through the tunnels, so both channels looked bad. Now the router also sends its own check around the VPN and reads the GL firmware verdict. If the evidence says no internet, Auto keeps the current route instead of jumping to the reserve; if the reserve answers, WAN-DOWN is not declared. After the internet returns Auto waits up to 30 s (WAN-RECOVERING) until the primary proves healthy, even when the reserve is healthy.

Other sensors only raise suspicion and never prove a failure: WireGuard events, and a tunnel that sends but receives nothing. The option wan_recover_grace (0 to 120 s, default 30) sets the wait after WAN returns.

Server key pinning: on the first good look the router remembers the key of each VPN server (WireGuard peer key, or the OpenVPN CA fingerprints) by profile and host name. If the same server shows another key, the event SERVER-KEY-CHANGED appears and the page offers Accept new key (Settings → System and diagnostics → Sensors). The default mode only warns; enforce, set over SSH, refuses a move onto the channel until you accept; leaving it stays allowed. A server change inside a provider pool is a new first use, not an alarm.

Not yet verified on the router: a real cut of only the router's uplink, the format of /proc/gl-kmwan/config, and key reading on the real provider profiles.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Router has no internet (WAN-DOWN) and a changed VPN-server key.
Auto shows WAN-DOWN or WAN-RECOVERING, or the page reports that a VPN server shows a different key.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="release-signing"></a>
## Signed releases, release chain and recovery codes

You install a package and want to know how its authenticity is checked, or you are the owner and lost the phone with the one-time code.

Releases are signed with the owner's key (Ed25519, the router's stock usign) and entered in the file releases/CHAIN.jsonl, where each record carries the fingerprint of the previous one: deleting or rewriting history breaks the chain. The router remembers the verified chain and refuses a rollback or a fork (CHAIN-DOWNGRADE, CHAIN-FORK). The record's hash is also anchored in Bitcoin through OpenTimestamps as a public proof of the date; confirmation takes hours.

For a user: compare the package hash and signature as written in the installation guide. The first installation trusts the keys inside the kit, so compare their fingerprints with an independent source (the release page).

For the owner: signing asks for a TOTP code from the phone. Without the phone use one of the 10 one-time recovery codes printed on paper (format XXXX-XXXX-XXXX-XXXX-CCCC; the last four characters catch a typo and a typo does not burn the code). Five wrong codes in a row lock the check for 10 minutes. Secrets can move to a new computer in an encrypted archive in the age format.

Not yet verified: the first installation of a signed package on the MT3000 with real keys (the lab used test keys). TOTP and the key store live in one Windows session, so this is procedural, not absolute, protection.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Signed releases, release chain and recovery codes.
You install a package and want to know how its authenticity is checked, or you are the owner and lost the phone with the one-time code.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="terms"></a>
## Terms of use (experimental software)

What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.



The current versioned operational terms are reproduced below. Their early test description is historical; current hardware/mode qualification is determined by Router readiness and the current guide. Removing the package still requires normal lifecycle/recovery checks.
# Experimental software: operational terms and licensing

[Русский](../DISCLAIMER.ru.md)

**HomenS.AI Auto VPN is experimental software.** Read this before installation or use. A versioned acknowledgement is shown at first run; automatic switching cannot start until the current terms are accepted. These operational terms supplement, and do not replace, the [software LICENSE](../LICENSE).

1. **Experimental and device-specific.** This software is under development, and testing/qualification applies only to the exact configurations documented in the current test and readiness guides. Do not assume that every GL-MT6000, GL-MT3000, firmware revision, or operating mode is qualified.
2. **Possible network interruption.** VPN switching may disconnect calls, downloads, devices or sessions. A bug or unexpected state may require manual recovery. Maintain an independent way to reach the router and internet; check your encrypted backup and recovery procedure before upgrading.
3. **Changes to router settings.** The application can reorder existing VPN routing rules and temporarily adjust firewall rules. It is not GL.iNet firmware. Stop Auto and follow documented recovery/lifecycle steps before upgrading or uninstalling; removal may be refused while a transaction is active.
4. **License and payment.** The current source distribution is governed, where applicable, by the **HomenSAI Personal & Commercial Source License v1.0**. Unmodified personal non-commercial use is free; use by or for any business or organization requires a separate **paid written license**. Code changes, redistribution, resale and integration need the rightsholder's **prior written consent**. Keep the developer notice **Serhii Khomenko — https://homensai.com**. See [LICENSE](../LICENSE), [LICENSING.md](../LICENSING.md), and [commercial licensing](../COMMERCIAL-LICENSING.md). Earlier MIT grants remain valid for earlier covered copies.
5. **No warranty and limitations.** The software is supplied "AS IS" to the maximum extent permitted by applicable law. Use it at your own risk; the license contains the applicable liability limitations and non-excludable exceptions.
6. **User responsibility.** You are responsible for your network, VPN accounts, VPN provider rules, and applicable laws. Never rely on this experimental system where network interruption could threaten life, health or physical safety.
7. **Optional reports.** Telegram reporting, if enabled, sends summaries through Telegram servers with a bot token stored locally. Nothing is sent through Telegram unless you configure this feature.
8. **No guaranteed support.** Support, maintenance, uninterrupted operation and compatibility are not promised. Future releases and operational terms may change; updated terms may require another acknowledgement.

These operational terms do not replace third-party licenses or statutory rights. They are not legal advice.

## How acknowledgement works

On first use, the LuCI screen presents these operational terms and two confirmations. The version/time are stored on the router. Until accepted, Auto switching is refused (`TERMS-NOT-ACCEPTED`). A changed terms version requires acknowledgement again.

Acceptance here does **not** grant Commercial Use, modification or redistribution rights; obtain a separate agreement with the rightsholder first where applicable. If you disagree, do not start Auto, and use the normal documented safe uninstall procedure.

Operational terms version: **2**. License text version: **1.0**.



### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Terms of use (experimental software).
What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```
