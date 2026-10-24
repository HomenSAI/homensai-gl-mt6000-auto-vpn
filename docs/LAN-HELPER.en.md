<!-- doc-role: current -->
# Windows LAN helper

[Mode contract](CLIENT-TRIAL.md) · [Actual qualification](CURRENT-STATUS.md)

Use the helper from the **same selected release**. Download `client-test.ps1` and `start-lan-helper.ps1` to one folder. Optional `start-lan-helper.cmd` requires both files. PowerShell7 is separate from Windows PowerShell5.1; use `pwsh`.

| Mode | Operation | Does not prove |
|---|---|---|
| `-SelfTest` | Offline parser/provenance/control-route rejection tests | Real network or router traffic |
| `-CheckOnly` | Client interface/route prerequisites, no login or router writes | Internet DNS/HTTPS or a passed switch |
| `-ProbeOnly` | Actual interface-bound router DNS and two HTTPS/exit checks | Switching, every app or IPv6 |
| Full trial | Private login, own trial settings, TEST confirmation, bounded switching and correlated witness | Unattended/day-long/all-device acceptance |

```powershell
pwsh -NoProfile -File .\start-lan-helper.ps1
pwsh -NoProfile -File .\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -CheckOnly
pwsh -NoProfile -File .\client-test.ps1 -Router http://192.168.8.1:8080/ -CableInterface 3 -ProbeOnly
```

Replace the example address/index with the verified real router/interface. The helper does not modify PC routing/NIC/DNS/firewall or disable another VPN. In cable mode data sockets bind to the selected interface/address; management uses the OS route, checked before login and each RPC. A detected mismatch is refused before transmission; this is not a claim that every possible route race is eliminated. A browser loopback gateway is not a valid LAN-witness target.

CheckOnly/ProbeOnly need no password. Full mode asks privately, requires session-loss consent, a distinct eligible pair and a bounded deadline (default from saved trial minutes, maximum4hours). Finish continuous Auto/managed recovery before configuring a separate client trial. Stop requests are verified, not treated as success from ACK alone. Exit0 means the selected mode completed; exit2 is refused/unverified/failure; exit3 is verified retained reserve rather than original-path restoration.

HTTP management is not encrypted: use the intended trusted LAN or HTTPS with a properly trusted certificate. Do not disable TLS validation. Session/token/configuration/exit data stay private. [Recovery](../router-test-kit/EMERGENCY.md).

[Microsoft PowerShell installation](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows).
