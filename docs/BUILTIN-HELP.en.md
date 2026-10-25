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

<a id="planner-wait"></a>
## Why Auto waits before switching

You want to understand why a single failed check does not immediately switch the channel.

The planner compares consecutive failed checks of the channel in use with consecutive successful checks of the other channel. The configured thresholds help avoid switching because of a brief interruption.

A green observation describes a successful check or an unmet failure threshold. It is not a separate confirmation that Auto is ready or that a route change is allowed.

Auto also considers fresh observations, the selected VPN pair, controller state and the configured return policy. A recommendation alone does not switch traffic.

See Overview for the current Auto state and selected channel. Use Live log for the sequence of decisions and their reasons. If observations are stale, use Check VPN now; it refreshes checks without choosing a channel for you.

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

On Overview check the selected channel and fresh DNS/HTTPS results. A working reserve is a normal state. Select another channel only when its readiness is confirmed; do not return to a failed primary just because it is called primary.

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

A router reboot is a last recovery step when you still control the device. It interrupts connectivity and does not repair a bad VPN configuration. Auto needs an explicit Start afterwards.

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

The selected reserve is working, a return is requested, or Stop retained the reserve.

Check both channel measurements and the selected route on Overview. Being on reserve does not by itself mean an error.

For an intentional return, use Manual channel selection when Primary is confirmed ready and its command is available. If Stop retained the reserve, use the offered Return to primary action and verify its actual result.

Automatic return depends on the saved return policy, fresh primary health and operator hold. Hold-reserve preference does not promise automatic return merely because primary probes succeed.

If neither channel works or a recovery command is refused, read its code and use No internet. Do not change stock VPN profiles while Auto owns a transition.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The router stays on the reserve VPN.
The selected reserve is working, a return is requested, or Stop retained the reserve.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="auto-refuses"></a>
## The Auto button refuses to start

Pressing Start shows a message with a code.

Open System readiness and the current Auto explanation on Overview. Use the exact refused condition; a green dry-run forecast is not a separate permission to start.

Verify the actual model, firmware and saved pair. Model selection does not enable unsupported firmware or turn two profiles of one tunnel into two channels.

Use the persistent-preparation help for acceleration, IPv6, stock workers and routing policy. Inspect before changing anything; one checkbox alone is not evidence that preparation is complete.

Prepared MT3000 router-probed IPv4 Auto uses fresh router evidence without a LAN certificate. A separate client-confirmed trial requires its own LAN helper and certificate. Keep these modes distinct.

Wait for current observations after changing profiles. Repeated Start clicks do not repair an identity, worker or policy mismatch. The Auto power button remains available to stop or cancel startup.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: The Auto button refuses to start.
Pressing Start shows a message with a code.
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

In Settings, open the separate LAN-trial panel and download client-test.ps1 plus start-lan-helper.ps1 into one folder. The optional start-lan-helper.cmd shortcut needs both of those files.

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

After an update, the Overview looks old, shows errors, or the status is stale.

Press Ctrl+F5 to reload without cache, then sign out of LuCI and sign in again (new permissions after an update).

Check the Monitoring indicator on Overview. If the monitor services are stopped, start those services over SSH and wait for a fresh timestamp; this is separate from Auto Start.

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
After an update, the Overview looks old, shows errors, or the status is stale.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="outside-change"></a>
## I changed VPN rules in the GL.iNet panel and Auto stopped

The Overview says the VPN rules were changed by someone else.

Auto refuses to compete with an external policy/profile edit. Read the actual controller phase and cleanup result; do not assume that every refused operation already restored Internet.

Check the current selected pair and the stock VPN configuration. If you intend to edit stock profiles, finish managed Stop/recovery first.

Wait for fresh consistent identities and readiness. Prepared continuous-pair mode can then be started explicitly; a legacy client-confirmed mode needs a new matching trial/certificate after a relevant edit.

Keep failed attempts and unrelated edits. Do not forge a confirmation, erase the journal or remove a foreign firewall table to make a status green.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: I changed VPN rules in the GL.iNet panel and Auto stopped.
The Overview says the VPN rules were changed by someone else.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```

<a id="telegram"></a>
## Telegram reports do not arrive

The Overview shows a Telegram error, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.

Open the official https://t.me/BotFather in Telegram and send /newbot there, not in a terminal. Follow its current instructions.

```text
/newbot
```

BotFather asks for a name (shown in the chat, any text, e.g. “My Router VPN”) and then a username that must end in “bot” (e.g. my_router_vpn_bot).

BotFather provides the bot token. Treat it as a password and paste it only into the dedicated private token field. Do not put it into a browser URL, chat, Git or diagnostic output.

Open your new bot (the link at the end of BotFather’s message, https://t.me/<your_bot_username>) and press Start or send /start. A bot cannot write to you first.

To read chat.id without adding a third-party bot, send /start or a message to your own bot, then use this PowerShell recipe locally. It asks for the token privately and prints only IDs. Do not record a transcript or share raw updates. If another bot program consumes updates, stop and inspect that configuration rather than invent an ID.

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

On the router open Settings → All application settings → step 7 · Telegram, or the Telegram setup shortcut. Enter the token privately and the verified chat ID or channel username, review and save. Configure off preserves the existing Telegram settings.

Press “Test Telegram delivery”. A message should arrive within a few seconds. If a code is shown instead: TELEGRAM-… with “401” or “Unauthorized” means a wrong token; “400”, “chat not found” or “Forbidden” means a wrong Chat ID or you never pressed Start; a timeout means the router has no internet or a wrong clock.

Still nothing? Create the token again in BotFather (/token or /revoke) and enter the new one. Never send the token to anyone, including in a support chat.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Telegram reports do not arrive.
The Overview shows a Telegram error, the test message does not arrive, or you set Telegram up for the first time. You need three things: a bot, its token and the chat ID.
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

Complete normal Stop and verify the actual managed recovery and guard state before removing the package. If Stop retained a reserve or recovery is unconfirmed, resolve the recorded condition first; do not force a return to an unhealthy primary. Then remove normally over SSH.

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

Settings → Monitoring and history retention: choose an integer live buffer from 1 to 2000 and detail retention from 1 to 7 days. Save and verify the values.

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

Open Advanced settings → Tests → Controlled VPN tunnel traffic fault. The current working channel is selected automatically; primary and reserve are both supported.

The router rechecks running Auto, private current-pair identity/policy, both healthy paths and session-loss consent. A preparation explanation means the destructive action has not started. Do not bypass a refusal.

The test temporarily drops IPv4 traffic on that tunnel device, not the VPN process or another server selected by name. It waits for failure thresholds and a fresh confirmed alternate route. Stop test and restore traffic removes the artificial fault early.

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
## First setup: eight steps with examples

Help for the complete setup wizard. Reading it saves nothing.


Before step 1, first-time setup shows the experimental-software agreement and MIT License. Read it, tick the confirmations and accept to continue. Previously accepted terms are remembered on this router. Next comes a short explanation with three diagrams; press OK to open the wizard.


Language and appearance

Keep Automatic detection for the router model. Choose English or Russian; the page translates immediately. Pick a readable theme and layout. Example: automatic model, English, system theme, Calm layout.



Monitoring

The interval controls how often VPN Internet is checked. Example: 10 seconds, checkpoint 900 seconds, profile limit 2 for a selected pair. Checkpoints save statistics to flash. In Settings → Monitoring and history retention, choose 1–2000 live journal observations and 1–7 days of detailed history. Monthly and lifetime counters remain separate; increasing the period cannot restore deleted detail. Keep the current profile limit if you monitor more profiles. During Auto startup the monitor temporarily checks more frequently; saving this step does not start Auto.



Existing VPN profiles and trial preferences

Create and connect VPN profiles in the router VPN panel first. Assign profiles to two distinct client tunnels in the stock VPN app first. The prepared MT3000 uses one WireGuard and one OpenVPN client; either can be primary. The selector lists these configured clients, not every saved server. Names and countries are examples; choose your own working profiles. If either is missing, defer pair setup and return later. Trial duration is in minutes; acknowledge that calls and sessions may reconnect before running a trial. A trial is separate from ordinary Auto startup.



Server names and priorities

Use names you can recognize, for example Germany primary and Germany reserve. The channel field groups related profiles; default is suitable for one pair. Smaller priority numbers come first: for example 10 before 20. Priority does not replace the explicit primary/reserve choices in step 3. Enable monitoring only for profiles you want checked; saving names never connects an inactive VPN.



Recovery rules

Avoid switching after a single failed check. Example: 3 primary failures, 2 successful reserve checks, cooldown 180 seconds and minimum dwell 180 seconds. For automatic primary return: 3 successful primary checks and 60 seconds of stable primary health. Keep a healthy reserve for operator review if you do not want automatic return. Counts are checks, while cooldown and stability are time intervals.



Optional speed tests

Speed tests consume traffic and are not required for initial Auto setup. Below the table two live charts show primary/reserve download (green) and upload (blue), refreshed every second. Channels are tested in sequence and waiting is explicit. The horizontal axis is elapsed seconds; missing data/errors are not zero speed. Completed averages are separate collapsed history. You can leave them disabled at first. An example for later is 8 MiB per test, 5 seconds, 2 streams and a 128 MiB daily budget. Review your traffic allowance before enabling automatic tests for new profiles. Actual usage is limited by the configured budgets.



Optional Telegram reports

You can skip Telegram. Leaving Configure off preserves an existing Telegram configuration. To configure it, create your bot with BotFather, send /start to the bot, enter its token and your destination, then choose the report contents and schedule. Example: a daily report at 07:00 Europe/Berlin. Never share the bot token in screenshots or reports.



Review all settings

Check the model, primary/reserve pair, intervals and optional features. Back lets you correct a value. Save all settings writes the reviewed configuration; Next alone only moves through the draft. If saving is refused while Auto is active, open the dashboard, turn Auto off and return to finish saving. Afterwards open Overview, check the two VPN channels and explicitly start Auto. To skip setup, use the green button below navigation: current router settings remain unchanged, the draft is not saved, and you can resume through Settings → All application settings.



### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: First setup: eight steps with examples.
Help for the complete setup wizard. Reading it saves nothing.
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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

Refresh System readiness and require fresh evidence. A failed or stale check remains unverified even after a successful install command.

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

A preparation row is red or unverified. This is separate from installing application dependencies.

Read the actual model, firmware and fresh preparation table. The current profile is for prepared MT3000/4.11.0. Saved settings and loaded modules alone do not prove runtime readiness.

Before changing acceleration, stock VPN startup or DNS, preserve a verified private backup and the exact original values/files. Establish the specific preparation scope and undo procedure; do not copy another device's commands blindly.

Do not force-unload modules, remove drivers, disable a working DNS owner or alter computer networking. Recheck fresh status after the approved changes. A green preparation table does not start Auto or prove external LAN connectivity. The full operation/undo record is docs/ROUTER-PREPARATION.md in the project repository.

### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Persistent router preparation: inspect before changing.
A preparation row is red or unverified. This is separate from installing application dependencies.
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

<a id="terms"></a>
## Terms of use (experimental software)

What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.



The unchanged versioned terms are reproduced below. Their early test description is historical; current hardware/mode qualification is determined by System readiness and the current guide. Removing the package still requires normal lifecycle/recovery checks.
# Experimental software: terms of use

[Русский](../DISCLAIMER.ru.md)

**HomenS.AI Auto VPN is experimental software (alpha).** Read this before you install or use it. The same text is shown in the program the first time you open it, and Auto cannot be started until you accept it.

1. **It is experimental.** This is an early release. It has been tested only in a limited way, on a GL.iNet GL-MT6000 (firmware 4.11.0) and in a virtual OpenWrt, never on a wide range of devices, firmware versions or networks. It is not production software and must not be treated as such.
2. **It can interrupt your internet.** Switching a VPN route can drop calls, downloads and sessions for seconds or longer. A fault, a bug or an unexpected router state can leave devices on your network without internet until you repair the router by hand. Keep another way to reach the internet and the router, and make a private backup first (see the Help page and `router-test-kit/`).
3. **It changes router settings.** The program reorders your existing VPN rules and can add a temporary firewall rule. It does not edit your VPN keys. You can remove it at any time (`opkg remove homensai-auto-vpn`; see the Help page).
4. **No warranty.** The software is provided "AS IS" under the MIT License, without warranty of any kind, express or implied. The author and contributors are not liable for any damage, loss of data, loss of service, cost or other consequence of installing or using it.
5. **You are responsible.** You install and use it at your own risk. You are responsible for your router, your network, your VPN accounts, for following your VPN provider's terms and for the law that applies to you. Do not use it where an interruption could endanger people or property.
6. **Optional reports.** If you configure Telegram reports, summaries are sent through Telegram's servers with a bot token stored on your router. Nothing is sent unless you configure it.
7. **No promise of support.** Features, behaviour and these terms may change or be withdrawn in later versions; accepting them again may be required.

This text is not legal advice. If you need certainty about your obligations, ask a qualified lawyer.

## How acceptance works

When you open the program in LuCI for the first time, a full-page screen shows these terms. Two boxes must be ticked before the Continue button works. The acceptance (terms version and time) is stored on the router in the program's own configuration. Until it is stored, the controller refuses to switch anything (`TERMS-NOT-ACCEPTED`) and the Start button for Auto is refused. If the terms change, their version number changes and you accept again.

If you do not accept, remove the package and leave your router as it was. Your VPN rules are not changed by the monitor itself.

Terms version: 1.



### Diagnostic prompt

```text
Diagnose this HomenS.AI Auto VPN problem on the specific router I identify: Terms of use (experimental software).
What you accepted on the first screen. The full text is DISCLAIMER.md in the project repository.
Ask only for missing symptoms, target address, operating system and secure tool access. Start read-only: verify actual board/firmware, installed/running version, current monitor/Auto/pair state and fresh evidence relevant to this section. Compare expected behavior with observations and narrow the cause step by step. Use terminal/browser tools yourself when available; otherwise state what you cannot execute and ask for one useful observation at a time.
Do not request secrets in chat or print full configs. This is diagnosis only: no network/firmware/package/settings changes, Auto Start/Stop, fault tests, messages or terms acceptance without a separate repair instruction. Do not bypass refusals. Report facts, hypotheses, exact error codes, checked/unchecked areas and the smallest supported fix; preserve the stopping point.
https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/docs/CURRENT-STATUS.md
```
