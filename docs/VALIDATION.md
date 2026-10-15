# Validation / Испытания

Target: one GL-MT6000, vendor GL.iNet 4.11.0 / OpenWrt 21.02-SNAPSHOT, LuCI git-22.335.71649-0ecaf74, Python 3.9.15. Development/unit tests: Linux Docker on Windows. Interpreted all-architecture ipk; not an SDK-built firmware image.

Through alpha9: actual opkg installation, discovery of 12 profiles, successful real probes of two active OpenVPN and one WireGuard, accumulated interface traffic and on-device Telegram delivery. Short observations do not establish 24-hour reliability. No LAN/IPv6/automatic failover validation.

0.2.0-alpha1 adds bilingual UI and checkpointed daily activity. Local regressions verify durations/failure episodes, inactive reserves, connections and unknown restart gaps. Device/UI verification status is stated in the release notes; no completed weekly/monthly soak is claimed.

Earlier qa/ stress and fault-injection reports are separate simulation evidence: they did not cut router power, wear real flash or prove native apply/rollback/conntrack/IPv6 failover. Existing profile time does not prove the traffic path. RPC session reset from the installer was fixed in alpha9; responsibility for persistent vendor-browser 403 is not conclusively established.
