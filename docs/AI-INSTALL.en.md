<!-- doc-role: current-generated-prompt -->
# AI installation prompt

[Installation](INSTALL.en.md) · [Current scope](CURRENT-STATUS.md)

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
