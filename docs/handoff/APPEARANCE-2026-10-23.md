<!-- documentation-context: archive -->
> Historical or versioned reference. [Current delivered state and verified scope](../CURRENT-STATUS.md) · [documentation index](../DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Language and appearance correction — alpha44

Owner requested three changes to the first setup step. The Emergency Stop button and its explanatory note are absent from Language and appearance; the other setup steps retain their existing behavior. The dashboard/recovery escape has a soft green background. Selecting Russian or English rerenders the first step immediately, including headings, field labels, navigation, attribution and the recovery link language, while retaining the other draft fields. Preview sends no RPC, saves no router preferences and performs no reload. Final reviewed save still persists router defaults.

The stale statement that MT3000 cannot switch channels was removed. Help now distinguishes immediate language preview from the theme/design and router settings applied after final save.

Final product source: `51899335ccc5179613686ab9a1dd5dae6e2db269`. Canonical package: `homensai-auto-vpn_0.9.0-alpha44-1_all.ipk`, 765127 bytes, SHA256 `aabd1cf1839fe1f30538ba9896dddbed3852583e945b3d9ea31f820ffa052d1c`. The earlier alpha44 package ending `dc9a233` was superseded before device installation.

Full immutable-source CI PASS:724 application tests and107 QA tests per Python3.11/3.9 runtime,39 UI suites, complementary environment skips. Actual canonical-IPK generated UI interaction PASS for immediate RU/EN, no first-step Stop, green link, preserved draft, translated recovery link and no write/reload. Local browser screenshot checked layout; this is not an interactive browser test of the router itself.

Installed84 files/modes and protected configurations PASS. Actual HTTPS and HTTP8080 assets match canonical dashboard74.js/ui51.css. Pre-upgrade189-entry configuration export encrypted and decrypt-read verified. No primary MT6000 or Windows network changes.

Final actual Start PASS57.66s with adaptive10→2→10s polling. Owner reserve restored PASS35.78s while Auto stayed ON. Final17:53Berlin snapshot PASS:alpha44, AutoON reserve, both VPN DNS/twoHTTPS healthy, no test faults or temporary full block. Final189-entry encrypted configuration export verified. [Machine evidence](../../qa/MT3000-APPEARANCE44-2026-10-23.json).

No further router action is required. GitHub full-history publication remains separately blocked pending the requested explicit historical-payload approval; this UI update does not imply that approval.
