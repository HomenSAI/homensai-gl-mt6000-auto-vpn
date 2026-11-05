<!-- doc-role: current-generated-training -->
# Interactive learning guide

[Help topics](BUILTIN-HELP.en.md) · [Current state](CURRENT-STATUS.md)

Open Help immediately after Settings, then Start or continue training. Lesson and question buttons allow direct navigation. Each question has an explanation before its choices. Check an answer to grade it; unchecked choices receive no credit. The result lists all questions, checked count, current score, first-attempt successes and total checks. Review missed questions retains correct answers and repeats only incorrect/unanswered questions. Scores do not certify router readiness or start Auto.

## 1. What this system is

The application monitors existing OpenVPN/WireGuard clients. Primary and reserve are roles, not protocol names. Configure servers and keys in the stock GL.iNet VPN app.
On the prepared supported MT3000, explicit Auto Start can start the saved pair and select its traffic policy. It recovers after confirmed failure; primary return follows the saved policy and operator preference.

Example: primary fails repeatedly → healthy reserve is confirmed → its route is selected. Return follows policy.

Only a saved, validated pair is managed; no credentials are created.

## 2. Before you start: two ways to connect

Prepare two ways to reach the router: a laptop connected by a LAN cable, and a device on the same router’s Wi-Fi (preferably a separate phone). Verify both reach the intended device before the first tests.
The cable is the reliable path for tests: it does not depend on Wi-Fi. Wi-Fi shows what your family devices will really experience. A second local path can help if the first fails, but does not guarantee access if the router itself is unavailable. Two adapters with the same subnet can reach different routers; do not send credentials until the management path is verified.
Also keep mobile data on your phone: it works even when the router VPN is broken.

Example: laptop on the cable runs the check; the phone on Wi-Fi opens a site to confirm that Wi-Fi users have internet too.

Never test only from one device that you cannot afford to lose.

## 3. First start

On the first visit the first-run wizard opens: Router → Channels → Behaviour → Terms and start. The current terms are shown at its last step (or when you first turn Auto on) until you accept them yourself on this router; training can be opened at any time.
Monitoring runs independently of Auto. «Check now» is next to the Auto switch on Home (Console: Channels tab); the Monitoring service lamp is in Settings → System and diagnostics (Console: System tab). A fresh monitor report is not proof that a client has internet.

A green monitoring lamp means fresh observations; Auto is still turned on separately with its switch.

Grey means waiting for the router, red means a proven failure: open Help ("? Help" in the Simple view; Console: System tab).

## 4. Setup

Wizard step 2 «Channels», later Settings → Channels: primary and reserve (Console: Channels → Change the channel pair): choose two different configured clients. Each choice represents the profile already assigned to that client; two servers of one client are not two independent channels.
To change a VPN server or protocol binding, use the stock VPN page and refresh Auto VPN. Saving the pair changes application metadata; it does not import keys or change server credentials.
How fast to switch, Router load and the optional Telegram reports are wizard step 3 «Behaviour»; speed test parameters are in Settings → Speed test: parameters. Review in step 4 «Terms and start»; Save without starting never starts Auto.

Example: M (main) = Germany · WireGuard; R (reserve) = Netherlands · OpenVPN.

The bot token is a secret. Never post it or send it to anyone.

## 5. Step 1: check the VPNs, Step 2: turn on Auto

On Home (Console: Channels tab) press “Check now”. It tests right away which connected VPNs give internet. Fix problems first.
Step 2: use the readiness list for your actual mode. Prepared-MT3000 router-probed IPv4 Auto checks the two channels on the router; a LAN helper is optional for additional client-path proof. A separate client-confirmed trial requires its own helper. Turn Auto on only when your mode is ready.
What is the LAN helper? A small PowerShell 7 script (plain text, you can read it) that runs on your Windows computer, not on the router. Install PowerShell 7 once, put the two downloaded files in one folder and start the launcher, then choose mode 1 (check only) first:
The Auto switch says whether Auto is on or off. The chip «Traffic here» marks the channel carrying your traffic, «Standing by» the other one. A green channel lamp means the channel works, not independent proof of Internet for every client; yellow means a check or a switch; red means it does not respond; grey means no fresh data. Inspect fresh channel checks for availability.
To choose a route manually, press Switch here on the Primary or Reserve card (Home, or the Channels tab of the Console) when the button is available, then wait for confirmed selection. A queued request is not completion; the status shows the switch until the router confirms it. Manual selection never turns Auto off: Auto keeps watching the chosen channel and moves traffic to the other one if it fails.
Use the Auto switch to request startup or shutdown. Wait for the actual final state. Turning Auto off does not stop monitoring; managed shutdown may restore the original routing/interface settings. If the reserve is retained, press Switch here on the Primary card when the primary works.

Example: “2 of 2 VPNs work” confirms router observations for both paths; it does not certify every LAN client.

Do not turn Auto on when you cannot afford a short interruption (a call, a download).

## 6. Reading the two views

Simple view: Home starts with the status and the Auto switch, then the two channel cards with «Switch here», Events and reasons, Last 24 hours and Tests; Settings holds everything needed rarely. Console view: the status strip with the Auto switch stays on top, and the tabs Channels, Auto, Servers, Log and System show the same readings in more detail. Switch views with ☰ / ▦ next to the language button. A queued command remains pending until the router confirms it.
The channel cards show primary first and reserve second with protocol, server and country where observed and the response (ping by default, or the three-site HTTPS mean); the 6-hour response chart is under Last 24 hours on Home and on the Channels tab of the Console. The Servers tab lists the servers of each channel with their ping (measured while Pick the best server is on). History is kept within the configured 1–7 days. A lower-delay server shown there does not switch the channel by itself.
Events and reasons on Home shows the latest 5 or 20 rows with the filters All, Switches, Problems and My actions; tap a row to read «why». The Log tab of the Console shows 20 rows and the live log; in the Simple view the live log is in Settings → System and diagnostics. Network checks keep their configured cadence. Settings → History and memory selects 1–2000 live log entries and 1–7 days of detail. Your own actions are marked «(you)»; missing historical outcomes are explained, not invented.

One outage may contain many failed checks. The failure chart counts the episode once.

Speed tests are optional and use traffic: Home → Tests → Speed test (Console: Servers tab); parameters in Settings → Speed test: parameters.

## 7. If the internet is gone

Keep access to the router by cable or Wi-Fi and inspect the selected channel, current measurements and the recorded reason. Open Help → “I have no internet”.
Switch manually only when the requested channel is confirmed ready and its action is available. Working on reserve alone is not a reason to force a return to a failed primary. Manual selection never turns Auto off: Auto keeps watching the channel you chose and moves traffic to the other one if it fails.
Use emergency commands only for the documented recovery situation. Start with read-only show; removing the owned guard is a recovery action, not a general internet fix.

Reserve works and primary is failing: keep the working route and diagnose the primary.

Reading with `show` is always safe; run the other commands only when you need to.

## 8. Safety rules

This is experimental software: it can interrupt your internet. You use it at your own risk and keep another way to reach the router.
Never share the router password, the Telegram token, VPN files or backups with anyone, including chats and support. After tests, change the router password if you typed it anywhere.
With Auto off, monitoring still probes and saves statistics; it does not automatically select another route. Training is not readiness certification.

Example: a person asks in a chat for your token “to help”. Do not send it.

You can come back to this training at any time: Settings → Reference → Help and training (Console: System tab → Help, codes, training).

## Questions and answer explanations

### 1. What does the system do when Auto is OFF?

With Auto off, the monitor still checks VPNs and records observations. It does not automatically choose another route.

- [x] Only watches and shows the state of your VPNs
- [ ] Switches to the reserve VPN by itself
- [ ] Creates new VPN profiles

### 2. Which ways to connect should you prepare for the first tests? (several answers)

Keep a verified cable path and a second way to reach the intended router, plus mobile Internet for recovery. Two equal private IPs can identify different routers.

- [x] A laptop on a LAN cable
- [x] A device on Wi-Fi
- [ ] Only one device that you cannot lose
- [x] Mobile data on the phone

### 3. What is the right order to start working?

Read and accept the terms yourself, follow the explanation/setup, choose an existing pair and inspect fresh readiness before explicitly starting Auto.

- [x] Accept the terms, start the monitor, check the VPNs, then turn on Auto
- [ ] Turn on Auto first, check later
- [ ] Skip the terms and start Auto

### 4. What must pass before Auto can be started?

Readiness is mode-specific. Prepared router-probed Auto and a separate client-confirmed LAN trial require different evidence.

- [x] The readiness checks for the selected mode; the helper is mandatory only for a client-confirmed trial
- [ ] A speed test
- [ ] A Telegram message

### 5. What does the status Reserve in use confirm?

The yellow status Reserve in use means the reserve route carries traffic. It does not by itself prove the primary is broken; its card shows its own checks.

- [x] The reserve route is selected; primary health is checked separately
- [ ] Everything is on the primary
- [ ] Auto is off

### 6. Which of these is a secret that you never send to anyone? (several answers)

Passwords, bot tokens, VPN keys and complete backups are secrets. Server country is a display label, not an authentication secret.

- [x] The Telegram bot token
- [x] The router password
- [ ] The country of a VPN server

### 7. The internet is gone. What do you do first?

First inspect the router and fresh checks, then use the Help topic I have no internet. Reflashing and deleting profiles are not first diagnostic steps.

- [x] Open the router page, inspect fresh checks and follow the Help topic I have no internet
- [ ] Flash the router firmware
- [ ] Delete all VPN profiles

### 8. Which command only reads the state and is always safe?

The show command reads the state. Stop-auto can change managed routing during recovery; remove-guard changes the owned traffic block.

- [x] homensai-vpn-emergency show
- [ ] homensai-vpn-emergency stop-auto
- [ ] homensai-vpn-emergency remove-guard

### 9. Can you select a channel while Auto is on?

Available manual controls can choose a verified channel while continuous Auto stays on. A queued command is not yet confirmed traffic selection.

- [x] Yes, when the manual control is available and the target passes its checks; Auto continues observing
- [ ] Always stop Auto before any channel selection
- [ ] Channel selection deletes VPN profiles

### 10. Does a successful channel check prove that traffic switched?

A successful check is an observation of a channel. Route changes have their own requested, pending and confirmed events.

- [x] No. A check and a confirmed route change are separate events
- [ ] Yes, every successful check is a switch
- [ ] A successful check means Auto was enabled by the operator

### 11. Does the VPN protocol decide which channel is primary?

Primary and reserve are roles, not protocol names. The application uses an existing pair and does not invent or import VPN credentials.

- [x] No. Primary and reserve are saved roles of the selected pair; configure server credentials in the stock VPN app
- [ ] WireGuard must always be primary
- [ ] OpenVPN must always be primary
