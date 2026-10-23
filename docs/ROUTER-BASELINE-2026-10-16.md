<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Physical router baseline — 2026-10-16T18:53:54.0327526+02:00

Read-only inspection and private backup only. No router configuration, installation, VPN, route, firewall or service changes; no Windows network changes; no failover trial.

| Item | Observed result |
|---|---|
| Access | SSH authenticated against saved host key; source-bound Ethernet management succeeded |
| Device | GL.iNet GL-MT6000; Linux 5.4.238; OpenWrt 21.02-SNAPSHOT r15812+1095-46b6ee7ffc |
| Application | Installed 0.6.0-alpha5-1; agent 0.6.0-alpha5; monitor/native supervisor processes running; Auto disabled |
| VPN | 12 registered profiles, three active (two OpenVPN, one WireGuard); all three had successful recent router DNS and two HTTPS checks; snapshot age 32.12 seconds |
| Blocker | PROFILE-INACTIVE; configured source inactive, reserve active; diagnostic returns no accepted selection |
| Policy | Two generic rules with Kill Switch, direct-WAN default disabled, global VPN policy enabled, order direction first |
| Acceleration | HNAT config zero and runtime disabled despite loaded module; flow-offload options absent; IPv6 config zero. No leak/offload traffic acceptance claimed |
| Prior recovery | Transaction ROLLED-BACK but native status STOPPED/original_restored=false/PROFILE-INACTIVE. Not proof of restored client Internet |
| Windows | Wi-Fi preferred, Ethernet lower priority; both gateways are this router. Wi-Fi is not independent recovery Internet |
| Cable | Source/interface-bound SSH and DNS PASS; HTTPS returned Windows 10051. Client Internet remains unverified |
| Storage | Overlay 7,509,824 KiB total, 480,244 KiB used, 7,029,580 KiB available (6%); read-only /rom 100% is separate |
| Backup | 10,194,609 bytes, 1,413 members; streamed directly to Windows, tar/gzip parsed; required config/application coverage checked |
| Consistency | Nine critical config files matched live SHA256; initial protected configuration/main-route capture unchanged |

Backup: private/router-readonly-2026-10-16/router-configuration-and-homensai-backup.tar.gz.
SHA256: f7dcb763b14aa0820ba2c656ab341417cf4314949fffb133dc7aa1592ffab4dc.
Includes /etc (VPN/system secrets), own application/LuCI/init and opkg metadata. Ignored by Git; local ACL restricted to owner, SYSTEM and Administrators. Do not publish. This is a configuration/application backup, not firmware/disk image or tested live restore; runtime capture is non-atomic.

Inspection corrections: invalid `ubus call system.board` produced usage output; corrected to `ubus call system board`. Its nonzero remote command result was initially misclassified as authentication failure. Saved host-key file already contained hostname prefix. Direct hook_toggle read returned no text; installed read-only acceleration diagnostic confirmed disabled through kernel status. These corrections changed only local inspection scripts, not router settings.

Next: [prepared bounded test](ROUTER-AUTO-TEST-PLAN-2026-10-16.md). Wait for separate authorisation.
