<!-- doc-role: current-generated-prompt -->
# AI LAN helper prompt

[Modes / Режимы](LAN-HELPER.en.md) · [Scope / Область](CLIENT-TRIAL.md)

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

Synchronized with the application. / Синхронизировано с приложением.
