# Controlled client trial

Candidate 0.5.0-alpha1. Not a production-enable guide. Read TODO-WORKING-SYSTEM.md and NATIVE-EXPERIMENTAL.md first. Owner must authorise a possible outage and neighbouring work must checkpoint/pause before any outage test. Keep an independent management/recovery path.

LuCI shows primary/reserve profile selection, explicit session-loss permission and a helper download. Save the selected profiles first. The helper requires Windows and PowerShell 7 on an independent LAN client. Run `pwsh -NoProfile -File .\client-test.ps1 -CheckOnly` for a read-only readiness check. `-SelfTest` performs input-parser tests without networking. Neither proves real VPN switching.

Only inside the approved trial window, run `pwsh -NoProfile -File .\client-test.ps1 -Until '<ISO time with offset>'`. Enter the router password privately in the local prompt. Never paste it into a chat, save it in the script, or publish logs containing credentials. The helper checks local gateway, configured DNS, absence of an unverified IPv6 default, router DNS and HTTPS. It saves only the project's configuration, checks prerequisites and asks for TEST before starting. Blocked prerequisites must not be bypassed.

The client confirms a transition through a typed authenticated RPC only after router DNS/HTTPS and expected VPN exit match. A successful first trial must restore the original client path. It then monitors within the configured window; cancelling/exiting requests Stop. Missing valid confirmation causes the independent router supervisor to roll back. A failed Stop request is not proof of restoration; use the independent management path and inspect actual state. The UI Stop button queues restoration, it does not instantly certify it.

Stop is stored privately and survives restart. A new explicit trial is required to resume. History is checksummed and bounded; monthly counts are partial since collection began. Backup recovery may lose the newest event. Corrupt history blocks new switching. Counts of controller transitions are not measurements of LAN uptime, bandwidth or router power-loss resilience.

An upgrade introducing native_confirm/native_stop refreshes rpcd registration once. An existing LuCI session may need login again; this is distinct from WAN connectivity. Do not disable authentication to fix a stale session. Existing router packages are retained.

Operational prerequisites: obtain task checkpoints and an authorised test window. Do not bypass HNAT or LAN checks. Enter credentials only locally, verify the selected pair and explicitly accept TEST. Stop requests do not prove restoration; verify the final client path. Later real acceptance is recorded in WORKLOG.md.

If the original source is not freshly verified healthy when a client-confirmed switch ends, the controller retains the reserve policy and reports STOPPED-ON-RESERVE / original_restored=false. This is not a successful restoration of original settings. The helper checks the retained client exit and uses exit code 3 for that partial result; exit code 2 means unverified/failure. Unknown source/backup health never becomes an internet-restored claim. A new explicit trial is required to proceed from the held state.

Cable management + Wi-Fi continuity: use -CableInterface <Ethernet ifIndex>. Only two temporary IPv4 /32 probe routes are created; existing conflicting host routes refuse the test. HTTPS is source-bound, DNS explicitly uses the router, and routes are removed in finally. Default traffic stays on Wi-Fi. This verifies cable probes only, not all application traffic.
