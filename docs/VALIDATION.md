# Validation / Испытания

Target: one GL-MT6000, vendor GL.iNet 4.11.0 / OpenWrt 21.02-SNAPSHOT, LuCI git-22.335.71649-0ecaf74, Python 3.9.15. Development/unit tests: Linux Docker on Windows. Interpreted all-architecture ipk; not an SDK-built firmware image.

Through alpha9: actual opkg installation, discovery of 12 profiles, successful real probes of two active OpenVPN and one WireGuard, accumulated interface traffic and on-device Telegram delivery. Short observations do not establish 24-hour reliability. No LAN/IPv6/automatic failover validation.

0.2.0-alpha2 adds bilingual UI and checkpointed daily activity. Local regressions verify durations/failure episodes, inactive reserves, connections and unknown restart gaps. Device/UI verification status is stated in the release notes; no completed weekly/monthly soak is claimed.

Earlier qa/ stress and fault-injection reports are separate simulation evidence: they did not cut router power, wear real flash or prove native apply/rollback/conntrack/IPv6 failover. Existing profile time does not prove the traffic path. RPC session reset from the installer was fixed in alpha9; responsibility for persistent vendor-browser 403 is not conclusively established.

## 0.2.0-alpha2 · device check 15 Oct 2026

Installed through the authorised native opkg API, exit code 0. Agent reports 0.2.0-alpha2, no service error, three active OpenVPN/WireGuard probes healthy, 12 activity profiles and Telegram enabled at 60 minutes with a confirmed prior delivery. Native apply remains false. No VPN profile, route or firewall was changed. New histogram observation starts now.

33 local tests passed, including binary-font preservation and calendar-day accounting. The branded EN/RU UI/robot/fonts were visually checked in an isolated synthetic fixture; the complete live LuCI settings/wizard rendering was not independently re-verified after the browser-session issue. Do not present fixture images as real router statistics. Original OFL licence whitespace is preserved; project whitespace checks exclude unchanged vendor assets.

Exact live-read model/firmware/LuCI/package evidence: [EN](TESTED-ENVIRONMENT.en.md) · [RU](TESTED-ENVIRONMENT.ru.md) · [JSON snapshot](tested-environment-2026-10-15.json). Captured 15 Oct 2026.
