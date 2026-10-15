# Validation

Target: one GL-MT6000, vendor GL.iNet 4.11.0 / OpenWrt 21.02-SNAPSHOT, LuCI git-22.335.71649-0ecaf74, Python 3.9.15. Development/unit tests: Linux Docker on Windows. Interpreted all-architecture ipk; not an SDK-built firmware image.

Through alpha9: actual opkg installation, discovery of 12 profiles, successful real probes of two active OpenVPN and one WireGuard, accumulated interface traffic and on-device Telegram delivery. Short observations do not establish 24-hour reliability. No LAN/IPv6/automatic failover validation.

0.2.0-alpha2 adds bilingual UI and checkpointed daily activity. Local regressions verify durations/failure episodes, inactive reserves, connections and unknown restart gaps. Device/UI verification status is stated in the release notes; no completed weekly/monthly soak is claimed.

Earlier qa/ stress and fault-injection reports are separate simulation evidence: they did not cut router power, wear real flash or prove native apply/rollback/conntrack/IPv6 failover. Existing profile time does not prove the traffic path. RPC session reset from the installer was fixed in alpha9; responsibility for persistent vendor-browser 403 is not conclusively established.

## 0.2.0-alpha2 · device check 15 Oct 2026

Installed through the authorised native opkg API, exit code 0. Agent reports 0.2.0-alpha2, no service error, three active OpenVPN/WireGuard probes healthy, 12 activity profiles and Telegram enabled at 60 minutes with a confirmed prior delivery. Native apply remains false. No VPN profile, route or firewall was changed. New histogram observation starts now.

33 local tests passed, including binary-font preservation and calendar-day accounting. The branded EN/RU UI/robot/fonts were visually checked in an isolated synthetic fixture; the complete live LuCI settings/wizard rendering was not independently re-verified after the browser-session issue. Do not present fixture images as real router statistics. Original OFL licence whitespace is preserved; project whitespace checks exclude unchanged vendor assets.

Exact live-read model/firmware/LuCI/package evidence: [EN](TESTED-ENVIRONMENT.en.md) · [RU](TESTED-ENVIRONMENT.ru.md) · [JSON snapshot](tested-environment-2026-10-15.json). Captured 15 Oct 2026.


## 2026-10-15 · 0.4.0-alpha8 candidate

52 monitor/package/native-controller unit tests and 9 lab transaction tests pass. Device installed through alpha7; native mode disabled, three active IPv4 HTTPS/DNS probe paths healthy. Software accelerator unloaded; hardware disable not verified. Candidate alpha8 not installed while owner works remotely. Live native switching/guard/rollback not exercised. Baseline soak intermediate checkpoint: 21 cycles, 105 suite runs, 2100 new seeds, 945000 model steps, 37687012 assertions, 420 container child-process crashes; zero failures. Baseline commit 386b4b3 excludes the new native controller. See NATIVE-EXPERIMENTAL.md and WORKLOG.md; do not claim final 14:00 results.

## 2026-10-15 · real alpha10 failover acceptance

90 Python tests passed after semantic anonymous-UCI identity fixes. At 18:21:20–18:22:03 Europe/Berlin, a real client-confirmed transition and return passed. A separate controlled primary-traffic failure at 18:23:37 triggered automatic APPLYING at 18:24:53 and COMMITTED/CLIENT-CONFIRMED at 18:25:20. Fault was removed by its independent timer at 18:26:07; independent rollback completed at 18:27:26. Separate cable checks confirmed original VPN exit/order, DNS, HTTPS and absent guard; Wi-Fi remained available.

The first helper completion reported CLIENT-CHECK-FAILED, so its exit is not marked PASS. Network transition/rollback were verified separately. Alpha11 adds bounded final network retries. This acceptance covers two already connected catch-all profiles and IPv4 client probes; it does not establish arbitrary topologies, production unattended operation, full IPv6 safety or physical power-loss resilience. Full timestamps, causes and fixes: WORKLOG.md.
