<!-- doc-role: current-generated-install -->
# Install, upgrade, roll back or remove: step-by-step guide

[README](../README.md) · [AI installation prompt](AI-INSTALL.en.md) · [Error codes](ERROR_CODES.md) · [Built-in Help](BUILTIN-HELP.en.md#install-guide) · [Emergency](../router-test-kit/EMERGENCY.md) · [Terms](../DISCLAIMER.md) · [Current status](CURRENT-STATUS.md) · [Русский](INSTALL.ru.md)

**License:** [HomenSAI Personal & Commercial Source License v1.0](../LICENSE) — source-available, not open source.

The same text is the built-in Help topic of the application (generated from router/ai_prompt.inc.js by scripts/sync-documentation.py). It is version-neutral: take every file from one release.

You want to install the program, upgrade it, go back to the previous version or remove it yourself, with commands you can copy. Reading it changes nothing.

## Before you start

HomenS.AI Auto VPN is an application for a GL.iNet router. It watches two VPN connections that are already set up on the router and, only after you switch Auto on, moves traffic to the reserve when the primary fails. The `.ipk` file is an application package, not router firmware.

There are two ways. Do it yourself with the numbered steps below, or let an AI agent with a terminal on your computer (Codex, Claude Code) do the steps for you: the last section and the Help topic «Prompt for your AI agent» contain a ready prompt with strict safety rules.

In the commands replace `ROUTER_ADDRESS` with the address you use to open your router admin page, and `VERSION` with the exact version from the release, for example the file name `homensai-auto-vpn_VERSION_all.ipk` becomes the real file name you downloaded. Sections 3 and 4 and the `scp` copy run on your computer (PowerShell on Windows, Terminal on macOS or Linux); all other commands run on the router after `ssh root@ROUTER_ADDRESS` has connected.

## 1. What you need

1. A supported router. Continuous Auto is documented for the GL.iNet GL-MT3000 (Beryl AX) with GL.iNet firmware 4.11.0. On the GL-MT6000 (Flint 2) with 4.11.0 the program installs and monitors, but continuous Auto there is not accepted yet. Other models and firmware are not supported; the package architecture `all` does not make them supported.

2. Two VPN connections already set up in the GL.iNet admin panel → VPN (WireGuard or OpenVPN clients): a primary and a reserve. They must be two different clients; two servers inside one client are not two channels. Monitoring works without them; Auto needs both.

3. At least 20 MiB of free writable flash on the router. About 8 MB of it keeps a verified copy of the installed program for self-repair and for the automatic rollback of a damaged upgrade.

4. Internet on the router, if missing dependencies must be installed from the firmware package lists.

5. A computer with an SSH client: Windows 10/11 (built-in OpenSSH, PowerShell), macOS or Linux (Terminal). Without SSH there is a LuCI upload path with fewer checks (section 6).

6. The router administrator (root) password. You type it yourself only into the hidden password prompt of the terminal or browser, never into a chat or a document.

7. About 30 minutes and a second way into the router while you work, for example a network cable.

## 2. What is checked and what is refused

`01-preflight.sh` only reads: router model, firmware, dependencies, free and writable storage, the program's own state (Auto off, no unsaved changes, no unfinished switch, no own protection table). It saves a fingerprint of the network, firewall and main routes so that the result can be compared later. It writes only into `/tmp/homensai-kit`.

`02-install.sh` refuses when the size or sha256 differs, when the signature or the release chain is wrong, when Auto is on, when the program's own protection table is still present, when the program has unsaved settings changes, or when preflight was not run. It never uses force flags.

The package itself refuses to install or upgrade while Auto runs or a recovery is unfinished (`LIFECYCLE-…` codes). On a board other than GL-MT3000 or GL-MT6000 it does not start its services (`MONITOR-ONLY-DEPLOYMENT`). After installation it checks its own files; damaged files block Auto and, on an upgrade, trigger the automatic rollback described in section 9.

In the program, Start of Auto is refused unless the detected model and firmware are supported, the terms are accepted by you, the router preparation checks pass and two channels are chosen. Choosing a model by hand never bypasses these checks.

## 3. Download and verify the package

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

## 4. Make a backup

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

## 5. Install over SSH (recommended)

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

## 6. Install through the LuCI page (without SSH)

1. Verify the checksum on your computer first (section 3). This path runs neither the preflight nor the signature check; only the package's own install guards run. Prefer SSH when you can.

2. Open the GL.iNet admin panel → System → Advanced Settings and go to LuCI.

3. LuCI → System → Software: press «Update lists…». It downloads the package lists of the firmware's own feeds and installs nothing; it is needed for dependencies.

4. Press «Upload Package…», choose the `.ipk`, upload it, check the name and version in the dialog and press «Install». Do not tick overwrite or force options. Never load the `.ipk` in «Flash new firmware image»: it is not firmware.

5. Read the output. If it shows an error or a code (`LIFECYCLE-…`, `MONITOR-ONLY-DEPLOYMENT`, a missing dependency), stop and look it up in section 12.

6. Open Services → HomenS.AI Auto VPN and press Ctrl+F5. If the page is empty or old, see the Help topic «The page is old, empty or says the monitor is not running».

## 7. First start: wizard and terms

1. Open LuCI → Services → HomenS.AI Auto VPN and press Ctrl+F5 (Cmd+Shift+R on macOS) so the browser loads the new page.

2. The four-step wizard opens: Router (the detected model and readiness lamps; the model cannot be chosen by hand) → Channels (primary and reserve: two different VPN clients from GL.iNet → VPN) → Behaviour (how fast to switch, router load, optional Telegram) → Terms and start.

3. On the last step press «Save without starting» (Auto stays off) or «Accept terms and turn Auto on» («Turn Auto on» when the terms are already accepted). Only you read and accept the terms; no script, helper or AI agent may accept them for you. Acceptance of the same terms version is remembered on the router.

4. Every step has «Skip — open the interface». Skipping never starts Auto and never accepts the terms.

5. Later the pair is changed in Settings → Channels: primary and reserve (Console view: the Channels tab).

## 8. What runs after installation

Monitoring starts at once and always runs: it checks both channels and keeps the history, traffic and response figures. It cannot be turned off (`MONITOR-ALWAYS-ON`); a page that says monitoring is not running shows an error: press «Restore monitoring», and if it does not come back, reinstall the package.

Auto is off until you start it with its switch or the wizard button, and only when the readiness checks pass. Saving settings never starts Auto.

While Auto runs, a failed primary leads to a switch only after the reserve passes its checks; the return follows the rule you chose. A switch can interrupt open connections. Auto changes only the routing order of the two chosen VPN channels and its own protection table; it does not edit Wi-Fi, DHCP, WAN or the VPN profiles.

Auto that you started comes back by itself after a reboot or a power cut, with all its start checks. Stop cancels that.

## 9. Upgrade to a newer version

1. Read the notes of the new release and make a fresh backup (section 4).

2. Turn Auto off on the page and wait until the page shows Auto off and no recovery running; «accepted» or «queued» is not finished yet. The install script refuses while Auto is on.

3. Download and verify the new package and the kit of the same release (section 3), copy them to `/tmp` and run `01-preflight.sh`, `02-install.sh` and `03-verify.sh wait` as in section 5. Settings, the channel pair, the history and the acceptance of the same terms version are kept.

4. While the package operation runs, the page shows `MAINTENANCE-IN-PROGRESS`: Start and the switching buttons are refused, Stop always works.

5. Press Ctrl+F5, check the installed version, then start Auto yourself if you want it.

   ```text
   opkg status homensai-auto-vpn | grep Version
   ```

6. Automatic rollback (packages from 2.1.0-alpha10 on, upcoming; not yet verified on a router): if the new package fails its file self-check during the upgrade, the program restores exactly the previous working version from its verified copy and starts it. Settings, journal and history are not touched; Auto runs again only if you had started it. The page shows `UPGRADE-ROLLED-BACK`: download the package again, verify it and install again. Without a matching copy (`UPGRADE-ROLLBACK-UNAVAILABLE`, `UPGRADE-ROLLBACK-VERSION`, `UPGRADE-ROLLBACK-FAILED`) the service stays off until you install a verified package; less than 8 MB free flash prevents the copy (`INTEGRITY-SNAPSHOT-NO-SPACE`).

## 10. Roll back to the previous version by hand

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

## 11. Remove the program

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

## 12. Messages and codes: what to do

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

## 13. Safety rules

The `.ipk` is an application, not firmware: never load it as firmware and never use a factory reset as a shortcut.

No `opkg --force-…` options, no `opkg upgrade` of all packages, no foreign package feeds.

Work only on the intended router and check its model and address before each change. If your home network depends on a GL-MT6000, do not install there unless you deliberately want to: continuous Auto is not accepted on the MT6000.

Backups contain secrets. Never put passwords, tokens, keys or full configuration files into a chat, a screenshot or a public repository.

Never accept the terms or start Auto on someone else's behalf; AI agents must not do it either.

Do not delete the program's journals or protection tables to get unstuck, and do not reorder VPN rules by guess: use Help and [router-test-kit/EMERGENCY.md](../router-test-kit/EMERGENCY.md).

## 14. Let an AI agent do it

If you do not want to type commands, an AI agent with a terminal on your computer (Codex, Claude Code or similar) can do these steps for you. A plain chat without tools cannot install anything.

Copy the prompt from the Help topic «Prompt for your AI agent» (it has a copy button); the same text is in [AI-INSTALL.en.md](AI-INSTALL.en.md) and [AI-INSTALL.ru.md](AI-INSTALL.ru.md) and at the end of the guide files [INSTALL.en.md](INSTALL.en.md) and [INSTALL.ru.md](INSTALL.ru.md).

The prompt makes the agent ask you first, check read-only before changes, make a backup, verify sha256 and the signature, show every command and wait for your yes before each change. It forbids accepting the terms for you, starting Auto, changing unrelated network or firewall settings and bypassing any refusal.

Stay at the computer: type the router password only into the terminal prompt, answer the agent's questions, and press Accept and Start on the page yourself when you want.

## Ready prompt for Codex or Claude Code

Copy the whole block into an AI agent that has a terminal on your computer. The same text is the Help topic «Prompt for your AI agent» and [AI-INSTALL.en.md](AI-INSTALL.en.md).

```text
Install HomenS.AI Auto VPN on my GL.iNet router for me, safely. You are an AI agent with a terminal on my computer (for example Codex or Claude Code). Run the commands yourself with your tools; I do not want to type commands. Explain every step in plain words and finish with a verified result, not a plan. If you have no terminal (a plain chat), say that you cannot install anything and point me to docs/INSTALL.en.md.

Project: https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn
Read from the chosen release: docs/INSTALL.en.md (the full guide), docs/ERROR_CODES.md, DISCLAIMER.md and the router-test-kit scripts before you run them.

1. FIRST ASK ME (all questions in one message)
- Router model and GL.iNet firmware, if I know them (you will check them yourself anyway).
- How you reach the router: the address I open its admin page with, and whether SSH works with an existing key or I type the root password myself in the terminal prompt. Never ask me to paste a password, key or token into the chat.
- What I want: A) install and monitor (Default: monitor, Auto off.); B) upgrade the installed version; C) roll back to the previous version; D) remove the program.
- Which release: the version I name; otherwise show me the newest releases with their status (pre-release = test build, or stable) and let me choose. Never choose silently.
- A private folder on my computer for the backup, outside any Git repository.

2. STRICT RULES (for every step)
- Show each command and say what it changes before you run it. Read-only checks and copying files to /tmp on the router may then run; every command that changes the router (installing dependencies, installing, upgrading, removing, any settings write) runs only after my explicit yes for that step.
- Read-only first: identify the router before anything else and make sure it is the router I named. Act on no other device. Verify the SSH host key at the first connection and never disable host-key checking; if a known key changed, or two network adapters may reach different devices with the same address, stop and ask.
- Backup before any change, verified readable, stored only in my private folder.
- Verify the package: name, size and sha256 against the .sha256 file of the same release, on my computer and again on the router after copying. Let 02-install.sh check the signature (.ipk.sig) and the release chain (CHAIN.jsonl). Use --allow-unsigned only for a release that has no .sig at all (published before signing), and tell me first. Stop on any mismatch.
- Use only the router-test-kit from the source archive of the same release as the package. Read scripts before running them; never pipe a downloaded script into a shell; never edit their expected values.
- Never accept the terms for me: never call terms_accept, never write terms_version, never tick or press Accept. I read and accept the terms myself on the router page.
- Never start Auto: never press Start or the wizard start button for me, never set native_enabled, never send a start request. Auto is started only by me, if and when I want. Saving settings never starts Auto.
- Never change unrelated settings: network, firewall, DHCP, Wi-Fi, WAN, DNS, VPN profiles, another router, or my computer's network adapters, addresses and routes. No firmware flashing, no factory reset, no reboot without my yes, no firewall flush, no opkg upgrade of everything, no foreign package feeds, no opkg --force flags.
- Stop and ask on any refusal: a STOP: or FAIL line, KIT-UNAVAILABLE, SIGNATURE-*, CHAIN-*, LIFECYCLE-*, MONITOR-ONLY-DEPLOYMENT, UNSUPPORTED-*, UPGRADE-ROLLBACK-* or any unknown code. Show me the exact line, look it up in docs/ERROR_CODES.md or the troubleshooting table of docs/INSTALL.en.md, explain it plainly and propose the smallest documented next step. Never bypass a refusal: no deleting journals or guard tables, no spoofing the model, no editing scripts.
- Secrets: never print, log, save or commit passwords, VPN keys, tokens or full configuration files. A backup archive contains secrets: keep it private.
- Supported routers: continuous Auto is documented for the GL-MT3000 with GL.iNet firmware 4.11.0. On a GL-MT6000 the program installs and monitors, but continuous Auto is not accepted; if my home network depends on that GL-MT6000, ask me before changing it. On another model or firmware stop and explain before installing anything; a chosen model never bypasses the detected hardware and firmware checks.

3. IDENTIFY THE ROUTER (read-only)
Run: ubus call system board; cat /etc/glversion; opkg status homensai-auto-vpn; df -h /overlay; free. Report model (board_name glinet,mt3000-snand = GL-MT3000, glinet,gl-mt6000 = GL-MT6000), firmware, installed version of the program, free space. Compare with what I said; continue only if it is the intended router.

4. BACKUP
Export the router backup into my private folder: on Windows cmd /c "ssh root@ROUTER sysupgrade -b - > router-backup.tar.gz", on Linux or macOS ssh root@ROUTER 'sysupgrade -b -' > router-backup.tar.gz (ROUTER = the verified address). Check it with tar -tzf router-backup.tar.gz. Tell me where it is and that it contains secrets; encrypt it if I have a tool for that. sysupgrade -b only exports, it never flashes.

5. DOWNLOAD AND VERIFY (on my computer)
From the chosen release download homensai-auto-vpn_VERSION_all.ipk, its .sha256, the .ipk.sig and CHAIN.jsonl if the release has them, and the release source archive (it contains router-test-kit). Compute sha256 (Get-FileHash -Algorithm SHA256 on Windows, sha256sum on Linux, shasum -a 256 on macOS), compare it and the size with the .sha256 file and the release notes. For a first signed install compare the release key fingerprints in docs/INSTALL.en.md with the release page.

6. INSTALL (A) OR UPGRADE (B)
For an upgrade first ask me to turn Auto off on the page and wait until the page shows Auto off and no recovery running; ACK or queued is not finished. Copy the package, its .sig and CHAIN.jsonl (if any) and 01-preflight.sh, 02-install.sh, 03-verify.sh, 04-uninstall.sh to /tmp on the router (scp; add -O if scp reports that sftp-server is missing). Check sha256sum on the router again. Run sh /tmp/01-preflight.sh. If only dependency lines fail, show me the missing names and, after my yes, run opkg update and opkg install with only those names from the firmware's own feeds; rerun preflight. Any other FAIL: stop and ask. After my yes run sh /tmp/02-install.sh /tmp/homensai-auto-vpn_VERSION_all.ipk. Then run sh /tmp/03-verify.sh wait and show every line; opkg exit code 0 alone is not success. If the RPC is missing, /etc/init.d/rpcd reload is allowed. If UPGRADE-ROLLED-BACK appears, explain that the previous working version was restored automatically and is running; download again, verify and ask me before retrying.

7. FIRST START (I do it myself)
Tell me to open LuCI, then Services, then HomenS.AI Auto VPN, and press Ctrl+F5. The four-step wizard Router, Channels, Behaviour, Terms and start opens. I choose the primary and reserve VPN (two different clients already set up in GL.iNet VPN) and press Save without starting, or accept the terms and start Auto myself. You may explain each screen but never click for me. Monitoring starts by itself and always runs; Auto stays off until I start it. Testing the path of a real LAN client is not part of installation; such a test must run from an actual device on that LAN and only on my separate request.

8. ROLLBACK (C), REMOVAL (D) AND REPORT
Rollback only on my request: back up, I turn Auto off, run sh /tmp/04-uninstall.sh (settings and history stay), copy the older package with the kit from its own release, run 01-preflight.sh, 02-install.sh (add --allow-downgrade only if it reports CHAIN-DOWNGRADE and I agree) and 03-verify.sh wait. Going back from 2.x to an older line needs the history file step of docs/INSTALL.en.md first. Removal only on my request: I turn Auto off, run sh /tmp/04-uninstall.sh, then confirm with opkg status homensai-auto-vpn; the settings files stay, delete them only if I ask after a backup.
Finally report: router model and firmware, previous and new version, package name, size and sha256, signature result, backup location (path only), every PASS/FAIL line, what you changed, what you did not check, Auto state (off unless I started it), and how to roll back or remove. Never claim a test that you did not run.
```

Synchronized with the application. / Синхронизировано с приложением.
