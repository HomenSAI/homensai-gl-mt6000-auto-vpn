<!-- current-release-context:0.9.0 -->
> Historical or versioned reference. [Current release0.9.0 and verified scope](CURRENT-STATUS.md) · [documentation index](DOCUMENTATION-INDEX.md). Versions, paused windows, planned features and device states below describe their recorded time; they are not current installation instructions or new authorization. Original evidence is retained.

# Post-alpha10 virtual acceptance checkpoint

Recorded 2026-10-17T09:22:14.034105+00:00. Scope: marked isolated x86 OpenWrt copy only. Physical router and host networking untouched.

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Installed alpha10 verification | PASS, 15 checks | Actual opkg/runtime; not a second upgrade |
| Downgrade to alpha7-2 | PASS, 12 checks | Actual opkg, own configuration retained |
| Re-upgrade to alpha10-1 | PASS, 17 checks | Package SHA256 87c0cf97517b77d03caa549cc07f42824ae11c61a9b4f64140db0fe2f2171b16 |
| UCI failure injection | PASS, 11 checks | Read-only delta/config writes refused; no duplicate anonymous section |
| Own monitor process crash | PASS | New PID and measurement timestamp after crash required; not Internet recovery |
| Guest warm reboot | PASS | Configuration retained, monitor autostart, new measurements, Auto OFF |
| Actual LuCI desktop/narrow desktop | PASS | Nine pages at 1280x900 and 978x808 |
| Actual LuCI mobile | FAIL | Channels/ranking search content-box width overflows at 414px; correction pending |
| Native start on generic x86 | REFUSED as expected | Unsupported board/vendor and missing client/deadline guards; no real switching certified |

Initial synchronous acceptance harness returned FAIL after package installation; the exact failed subcommand was not retained, so its cause remains unknown. Installation was independently verified. The replacement detached job records exact failed steps and bounded progress. The earlier age-only monitor receipt was preliminary; final crash check requires a post-crash timestamp.

Guest time lagged host by roughly seven hours after a long pause. Only virtual guest clock/RTC were aligned; this is fixture maintenance, not proof of a production NTP fix. Warm reboot does not prove hardware power-loss/flash behavior or repair the original guest GRUB boot path. No connected VPN profiles were measured; zero checked servers is not Internet availability proof. Private raw receipts and disk backup remain excluded from publication.
