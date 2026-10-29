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

The current terms appear until first acceptance on this router. Acceptance is followed by the introduction and the eight-step setup; training can be reopened later.
Monitoring runs independently of Auto. On Overview, monitoring and Check VPN now are inside the top Auto card. A fresh monitor report is not proof that a client has internet.

A green monitoring lamp means fresh observations; Auto still needs an explicit Start.

Grey means waiting for the router, red means a proven failure: open Help.

## 4. Setup

Settings → All application settings → 3 · Existing VPNs: choose two different configured clients. Each choice represents the profile already assigned to that client; two servers of one client are not two independent channels.
To change a VPN server or protocol binding, use the stock VPN page and refresh Auto VPN. Saving the pair changes application metadata; it does not import keys or change server credentials.
Recovery policy is step 5. Speed tests (6) and Telegram (7) are optional. Review in step 8; saving never starts Auto.

Example: M (main) = Germany · WireGuard; R (reserve) = Netherlands · OpenVPN.

The bot token is a secret. Never post it or send it to anyone.

## 5. Step 1: check the VPNs, Step 2: turn on Auto

On Overview press “Step 1 · Check the VPNs now”. It tests right away which connected VPNs give internet. Fix problems first.
Step 2: use the readiness list for your actual mode. Prepared-MT3000 router-probed IPv4 Auto checks the two channels on the router; a LAN helper is optional for additional client-path proof. A separate client-confirmed trial requires its own helper. Start Auto only when your mode is ready.
What is the LAN helper? A small PowerShell 7 script (plain text, you can read it) that runs on your Windows computer, not on the router. Install PowerShell 7 once, put the two downloaded files in one folder and start the launcher, then choose mode 1 (check only) first:
The power button shows Auto ON/OFF. The route title and M/R diagram show the selected channel. Green means this channel carries your traffic, not independent proof of Internet; yellow means alive but not in use (or a short check or switch); red is a proven failure. During a manual switch the destination card blinks green. Inspect fresh channel checks for availability.
To choose a route manually, open Overview → Manual channel selection. Choose Primary or Reserve when its control is available, then wait for confirmed selection. A queued request is not completion; the destination card blinks green during the switch. Manual selection never turns Auto off: Auto keeps watching the chosen channel and moves traffic to the other one if it fails.
Use the large Auto button to request startup or shutdown. Wait for the actual final state. Turning Auto off does not stop monitoring; managed shutdown may restore the original routing/interface settings. A retained-reserve outcome requires its separately offered recovery action.

Example: “2 of 2 VPNs work” confirms router observations for both paths; it does not certify every LAN client.

Do not turn Auto on when you cannot afford a short interruption (a call, a download).

## 6. Reading the pages

Overview starts with Auto and the VPN check. Manual primary/reserve controls follow the collapsed technical and switching-statistics blocks. A queued command remains pending until the router confirms it.
Channels and servers shows primary first and reserve second, server names/IP where observed, the response (ping by default, or the three-site HTTPS mean) and a 1–168h history within configured 1–7-day retention. Other servers and excess table rows expand with a triangle. A lower-delay recommendation does not switch traffic.
The live log groups repeated states into time ranges; its clock updates every second, network checks keep their configured cadence. Events shows the latest 20 rows, with expansion, search and sorting. Setup step 2 or Monitoring settings selects 1–2000 live observations and 1–7 days of detail. M/R identifies primary/reserve and who initiated a transition; missing historical outcomes are explained, not invented.

One outage may contain many failed checks. The failure chart counts the episode once.

Speed tests are optional and use traffic; they live under Advanced settings → Tests.

## 7. If the internet is gone

Keep access to the router by cable or Wi-Fi and inspect the selected channel, current measurements and the recorded reason. Use Help → No internet.
Switch manually only when the requested channel is confirmed ready and its action is available. Working on reserve alone is not a reason to force a return to a failed primary. Manual selection never turns Auto off: Auto keeps watching the channel you chose and moves traffic to the other one if it fails.
Use emergency commands only for the documented recovery situation. Start with read-only show; removing the owned guard is a recovery action, not a general internet fix.

Reserve works and primary is failing: keep the working route and diagnose the primary.

Reading with `show` is always safe; run the other commands only when you need to.

## 8. Safety rules

This is experimental software: it can interrupt your internet. You use it at your own risk and keep another way to reach the router.
Never share the router password, the Telegram token, VPN files or backups with anyone, including chats and support. After tests, change the router password if you typed it anywhere.
With Auto off, monitoring still probes and saves statistics; it does not automatically select another route. Training is not readiness certification.

Example: a person asks in a chat for your token “to help”. Do not send it.

You can come back to this training at any time from the menu.

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

### 5. What does Working on the reserve confirm?

Orange in the Auto status means the reserve route is selected. It does not by itself prove the primary is broken; health is shown separately.

- [x] The reserve route is selected; primary health is checked separately
- [ ] Everything is on the primary
- [ ] Auto is off

### 6. Which of these is a secret that you never send to anyone? (several answers)

Passwords, bot tokens, VPN keys and complete backups are secrets. Server country is a display label, not an authentication secret.

- [x] The Telegram bot token
- [x] The router password
- [ ] The country of a VPN server

### 7. The internet is gone. What do you do first?

First inspect the router and fresh checks, then use the No internet help. Reflashing and deleting profiles are not first diagnostic steps.

- [x] Open the router page, inspect fresh checks and follow No internet Help
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
